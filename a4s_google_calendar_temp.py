import all4s_lib
import google_calender_api
import datetime
import pytz

a4s = all4s_lib.Main()

berlin_tz = pytz.timezone('Europe/Berlin')
# Start at midnight, otherwise the lessons of today that already started are
# not found in the calendar and would be created again on every run.
start_time = datetime.datetime.now(berlin_tz).replace(hour=0, minute=0, second=0, microsecond=0)
end_time = start_time + datetime.timedelta(days=31)
data = a4s.get_schedule(start_time=start_time.strftime("%Y-%m-%d"), end_time=end_time.strftime("%Y-%m-%d"))
# print(data)

print(start_time.isoformat())

calendar = google_calender_api.Main(calendar_name="Stundenplan")
calendar.delete_events_in_date_range(start_time.isoformat(), end_time.isoformat())


for event in data:
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