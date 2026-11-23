import all4s_lib
import datetime

# Settings, see README.md
INCLUDE_STUDIO_TIMES = all4s_lib.get_setting("A4S_INCLUDE_STUDIO_TIMES", False, cast=bool)

a4s = all4s_lib.Main(return_StudioTimes=INCLUDE_STUDIO_TIMES)

today = datetime.datetime.now()
tomorrow = today + datetime.timedelta(days=1)
data = a4s.get_schedule(start_time=today.strftime("%Y-%m-%d"), end_time=tomorrow.strftime("%Y-%m-%d"))
# print(data)

for i in data:
    print(i["SubjectName"])
    print(i["Start"])
    print(i["End"])
    print(i["RoomName"])
    print("--------------------")
