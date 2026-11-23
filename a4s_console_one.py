import datetime
import requests

from all4s_lib import LoginError, is_studio_time, resolve_credentials

class a4s_lib:
    @property
    def base_url(self):
        return f"https://{self.url}"

    @property
    def referer(self):
        return f"{self.base_url}/login.html#/login"

    def login(self):
        """Log in against the school portal and return an authenticated session.

        The portal hands out a JSON Web Token: the credentials are posted to
        /api/Api/Authorization/JwtAuth and the returned token is sent with
        every following request as 'Authorization: Bearer <token>'.
        """
        login_url = f"{self.base_url}/api/Api/Authorization/JwtAuth"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": self.referer
        }
        payload = {
            "Username": self.username,
            "Password": self.password,
            "Pin": self.pin or None
        }

        # Start a session
        session = requests.Session()

        # Step 1: POST the credentials and get the token
        try:
            response = session.post(login_url, json=payload, headers=headers)
        except requests.exceptions.RequestException as error:
            raise LoginError(
                f"Could not reach '{login_url}': {error}\n"
                "Check the 'url' in your configuration: it must be the host name of the "
                "school portal only (e.g. 'schule.louisenlund.de'), without 'https://'."
            ) from error

        if response.status_code != 200:
            raise LoginError(
                f"Login failed (status {response.status_code}). Check 'username' and "
                "'password' in your configuration"
                + ("" if self.pin else " and add the 'pin' if your account uses two factor authentication.")
                + f" Response: {response.text[:200]}"
            )

        # Step 2: The body of the response is the token itself
        try:
            token = response.json()
        except ValueError:
            token = response.text.strip()
        if not isinstance(token, str) or not token:
            raise LoginError(f"Login failed, the portal did not return a token: {response.text[:200]}")

        # Step 3: Use the token for every following request
        session.headers.update({"Authorization": f"Bearer {token}"})
        self.token = token
        print("Login succeeded!")
        return session
    

    def get_StudentID(self):
        url_StudentID = f"{self.base_url}/api/Api/AppUser/GetUserInfo"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": self.referer
        }
        payload = {}
        studentID_response = self.session.get(url_StudentID, json=payload, headers=headers).json()
        self.name = studentID_response["userName"]
        # print(studentID_response)
        return studentID_response["crmEntityId"]
    

    def get_SchoolID(self):
        url_SchoolID = f"{self.base_url}/api/Api/AppUser/GetSchoolsForCurrentUser"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": self.referer
        }
        payload = {}
        schoolID_response = self.session.get(url_SchoolID, json=payload, headers=headers).json()
        # print(schoolID_response)
        return schoolID_response[0]["id"]

    
    def __init__(self, url=None, username=None, password=None, return_StudioTimes=False, config=None, pin=None):
        credentials = resolve_credentials(config=config, url=url, username=username, password=password, pin=pin)
        self.url = credentials["url"]
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.pin = credentials["pin"]
        self.token = None
        self.return_studiotimes = return_StudioTimes
        self.name = None
        self.session = self.login()
        self.studentID = self.get_StudentID()
        self.schoolID = self.get_SchoolID()


    
    def get_schedule(self, formatted=True, start_time="2025-02-3", end_time="2025-02-4"):
        """{
        'Id': '1010140', 
        'start': '2025-02-03T16:00:00+01:00', 
        'end': '2025-02-03T16:30:00+01:00', 
        'Comment': None, 
        'InventoryText': None, 
        'BaseLesson_Id': 1010140, 
        'AdditionalLessonIdsString': ',1010140,1011239,1011240,1011241', 
        'Subject_Id': 1069, 
        'SubjectName': 'Gilde', 
        'SubjectDescription': None, 
        'SubjectVisibility': 0, 
        'SubjectColor': '#f1f68b', 
        'Teacher_Id': 1452, 
        'TeacherName': 'Jördis Tirs', 
        'TeacherColor': '#FFFFFF', 
        'AdditionalTeacherNamesString':None, 
        'AdditionalTeacherIdsString': None, 
        'AdditionalClassIdsString': None, 
        'AdditionalClassNamesString': None, 
        'StudentClass_Id': 5551, 
        'StudentClassName': 'First Responder Fortg: Mo 16.0 - 18.00 SJ 24/25', 
        'MainStudentClass_Id': 0, 
        'StudentClassColor': '#FFFFFF', 
        'School_Id': 35, 
        'Room_Id': 180, 
        'RoomName': 'H4.0.Seminar 1', 
        'RoomColor': '#FFFFFF', 
        'AdditionalRooms': None, 
        'AdditionalRoomIdsString': None, 
        'SubId': None, 'SubState': None, 
        'SubAbsId': None, 
        'DocumentationCount': 0, 
        'Keys': None, 
        'IsPublic': False, 
        'StudentsCount': 19, 
        'AbsenceCount': 0, 
        'DispensationCount': 0},"""

        url_schedule = f"{self.base_url}/api/api/Schedule/GetSchedule"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": self.referer
        }
        payload = {
        "schoolId": self.schoolID,
        "studentId": self.studentID,
        "from": start_time,
        "to": end_time,
        "getAbsences": False,
        "getShortNames": False
        }

        schedule_response = self.session.post(url_schedule, json=payload, headers=headers).json()
        schedule_lessons = schedule_response["lessons"]

        if formatted:
            formatted_lessons = []
            for i in schedule_lessons:
                # Only add lessons if it is not a "Studio Times" lesson or if return_studiotimes is True
                if not is_studio_time(i["SubjectName"]) or self.return_studiotimes:
                    # Calculate the number of students present
                    try:
                        students_present = int(i["StudentsCount"]) - int(i["AbsenceCount"]) - int(i["DispensationCount"])
                    except (ValueError, TypeError):
                        students_present = None  # or handle appropriately

                    # Build a dictionary for the formatted lesson
                    lesson = {
                        "SubjectName": i["SubjectName"],
                        "Start": i["start"],
                        "End": i["end"],
                        "RoomName": i["RoomName"],
                        "AdditionalRooms": i["AdditionalRooms"],
                        "TeacherName": i["TeacherName"],
                        "AdditionalTeacherNamesString": i["AdditionalTeacherNamesString"],
                        "StudentsPresent": students_present
                    }
                    
                    # Optionally print the values if you need to debug:
                    # print(i["SubjectName"], ical_start, ical_end, i["RoomName"], i["TeacherName"], students_present)
                    
                    formatted_lessons.append(lesson)
            # simplify formatted lesson
            for i in range(1, len(formatted_lessons)):
                if formatted_lessons[i]["SubjectName"] == formatted_lessons[i - 1]["SubjectName"] and formatted_lessons[i]["Start"] == formatted_lessons[i - 1]["End"]:
                    formatted_lessons[i]["Start"] = formatted_lessons[i-1]["Start"]
                    formatted_lessons[i-1]["DELETE"] = True
            
            formatted_lessons = [lesson for lesson in formatted_lessons if ('DELETE' not in lesson) or (lesson.get('DELETE') is False)]

            return formatted_lessons
        return schedule_lessons


a4s = a4s_lib()

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