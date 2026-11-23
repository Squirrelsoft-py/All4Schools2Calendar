import all4s_lib
import caldav_api
import datetime
import pytz

a4s = all4s_lib.Main(url="schule.louisenlund.de", username="example-user", password="example-password")

berlin_tz = pytz.timezone('Europe/Berlin')
start_time = datetime.datetime.now(berlin_tz)
end_time = start_time + datetime.timedelta(days=31)
data = a4s.get_schedule(start_time=start_time.strftime("%Y-%m-%d"), end_time=end_time.strftime("%Y-%m-%d"))
# print(data)

print(start_time.isoformat())

calendar = caldav_api.Main(calendar_name="Stundenplan", t_start=start_time, t_end=end_time)
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
