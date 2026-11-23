import all4s_lib
import caldav_api
import datetime
import pytz

# a4s = all4s_lib.Main(url="schule.louisenlund.de", username="example-user", password="example-password")

berlin_tz = pytz.timezone('Europe/Berlin')
start_time = datetime.datetime.now(berlin_tz)
end_time = start_time + datetime.timedelta(days=31)
# data = a4s.get_schedule(start_time=start_time.strftime("%Y-%m-%d"), end_time=end_time.strftime("%Y-%m-%d"))
# print(data)

print(start_time.isoformat())

calendar = caldav_api.Main(t_start=start_time, t_end=end_time)
