import all4s_lib
import caldav_api
import datetime
import pytz

# Settings, see README.md. The environment variables have the highest priority,
# then the configuration file, then the default.
CALENDAR_NAME = all4s_lib.get_setting("CALDAV_CALENDAR_NAME", "Stundenplan")
INCLUDE_STUDIO_TIMES = all4s_lib.get_setting("A4S_INCLUDE_STUDIO_TIMES", False, cast=bool)
DAYS = all4s_lib.get_setting("A4S_SYNC_DAYS", 31, cast=int)


def main():
    a4s = all4s_lib.Main(return_StudioTimes=INCLUDE_STUDIO_TIMES)

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
    lesson_ids = {}
    if events_in_date_range:
        for i in events_in_date_range:
            a4s_id = i["description"].split("###")
            if len(a4s_id) == 3:
                a4s_id = a4s_id[-2]
            else:
                a4s_id = None
            id_caldav = i["id"]

            if a4s_id != None:
                event_still_in_in_schedule = False
                for a4s_event in data:
                    if a4s_event["Id"] + a4s_event["SubjectName"] + " " + a4s_event["RoomName"] == a4s_id + i["summary"]:
                        event_still_in_in_schedule = True
                        break
                if not event_still_in_in_schedule:
                    # delete event with id_caldav
                    print(f"delete: {id_caldav} {i['summary']}")
                    calendar.delete_event_by_id(id_caldav)
                elif a4s_id in lesson_ids:
                    # a second event for the same lesson, keep only the first one
                    print(f"delete duplicate: {id_caldav} {i['summary']}")
                    calendar.delete_event_by_id(id_caldav)
                else: 
                    lesson_ids[a4s_id] = i["id"]

    print(f"lesson id dictionary (a4s - caldav): {lesson_ids}")


    for event in data:
        if event["Id"] not in lesson_ids:
            if event["AdditionalTeacherNamesString"] != None:
                teacher = event["TeacherName"] + event["AdditionalTeacherNamesString"]
            else:
                teacher = event["TeacherName"]
            
            if event["AdditionalRooms"] != None:
                room = event["RoomName"] + event["AdditionalRooms"]
            else:
                room = event["RoomName"]
            
            description = f'Lehrer: {teacher}\nRaum: {room}\nAnwesend: {event["StudentsPresent"]}\n###{event["Id"]}###'
            title = event["SubjectName"] + " " + event["RoomName"]
            calendar.create_event(title, description, event["Start"], event["End"])


if __name__ == "__main__":
    main()
