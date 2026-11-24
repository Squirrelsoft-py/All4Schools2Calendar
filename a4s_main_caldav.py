import all4s_lib
import caldav_api
import datetime
import pytz

# Settings, see README.md. The environment variables have the highest priority,
# then the configuration file, then the default.
CALENDAR_NAME = all4s_lib.get_setting("CALDAV_CALENDAR_NAME", "Stundenplan")
DAYS = all4s_lib.get_setting("A4S_SYNC_DAYS", 31, cast=int)


def build_title(lesson):
    """Return the title of the calendar event of a lesson"""
    return lesson["SubjectName"] + " " + lesson["RoomName"]


def build_description(lesson):
    """Return the description of the calendar event of a lesson

    The id of the lesson is written behind "###", it is the marker that links
    the event to the lesson.
    """
    if lesson["AdditionalTeacherNamesString"] != None:
        teacher = lesson["TeacherName"] + lesson["AdditionalTeacherNamesString"]
    else:
        teacher = lesson["TeacherName"]

    if lesson["AdditionalRooms"] != None:
        room = lesson["RoomName"] + lesson["AdditionalRooms"]
    else:
        room = lesson["RoomName"]

    return f'Lehrer: {teacher}\nRaum: {room}\nAnwesend: {lesson["StudentsPresent"]}\n###{lesson["Id"]}###'


def same_time(stored, lesson_time):
    """Return True if two ISO times are the same moment"""
    try:
        return datetime.datetime.fromisoformat(stored) == datetime.datetime.fromisoformat(lesson_time)
    except (TypeError, ValueError):
        return stored == lesson_time


def same_text(stored, text):
    """Return True if two texts are the same, ignoring the line endings"""
    if stored is None:
        return False
    return stored.replace("\r\n", "\n").strip() == text.replace("\r\n", "\n").strip()


def main():
    a4s = all4s_lib.Main()

    berlin_tz = pytz.timezone('Europe/Berlin')
    # Start at midnight, otherwise the lessons of today that already started are
    # not found in the calendar and would be created again on every run.
    start_time = datetime.datetime.now(berlin_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time + datetime.timedelta(days=DAYS)
    data = a4s.get_schedule(start_time=start_time.strftime("%Y-%m-%d"), end_time=end_time.strftime("%Y-%m-%d"))
    # print(data)

    print(start_time.isoformat())

    calendar = caldav_api.Main(calendar_name=CALENDAR_NAME, t_start=start_time, t_end=end_time)
    # calendar.delete_events_in_date_range(start_time.isoformat(), end_time.isoformat())
    events_in_date_range = calendar.get_events_in_date_range(start_time.isoformat(), end_time.isoformat())
    # print(events_in_date_range)

    # The id in the description of an event links it to the lesson of the timetable
    lessons_by_id = {lesson["Id"]: lesson for lesson in data}

    lesson_ids = {}
    if events_in_date_range:
        for i in events_in_date_range:
            marker = i["description"].split("###")
            if len(marker) != 3:
                # no marker, the event was not created by this script, leave it alone
                continue
            a4s_id = marker[-2]
            id_caldav = i["id"]

            lesson = lessons_by_id.get(a4s_id)
            if lesson is None:
                # the lesson is not in the timetable any more
                print(f"delete: {id_caldav} {i['summary']}")
                calendar.delete_event_by_id(id_caldav)
                continue

            if a4s_id in lesson_ids:
                # a second event for the same lesson, keep only the first one
                print(f"delete duplicate: {id_caldav} {i['summary']}")
                calendar.delete_event_by_id(id_caldav)
                continue

            lesson_ids[a4s_id] = id_caldav

            # Update the event if the lesson changed, for example a new room or
            # a new time. The event keeps its uid, so the calendar clients
            # keep it and everything that was added to it.
            title = build_title(lesson)
            description = build_description(lesson)
            changed = (
                not same_text(i["summary"], title)
                or not same_time(i["start"]["dateTime"], lesson["Start"])
                or not same_time(i["end"]["dateTime"], lesson["End"])
                or not same_text(i["description"], description)
            )
            if changed:
                calendar.update_event(id_caldav, title, description, lesson["Start"], lesson["End"])

    print(f"lesson id dictionary (a4s - caldav): {lesson_ids}")


    for event in data:
        if event["Id"] not in lesson_ids:
            description = build_description(event)
            title = build_title(event)
            calendar.create_event(title, description, event["Start"], event["End"])


if __name__ == "__main__":
    main()
