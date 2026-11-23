import requests
from bs4 import BeautifulSoup

class Main:
    def login(self):
        # URL of the login page (without the hash fragment)
        login_url = f"https://{self.url}/modules/Login.aspx"

        # Start a session
        session = requests.Session()

        # Step 1: GET the login page to capture the tokens
        response = session.get(login_url)
        if response.status_code != 200:
            raise Exception("Failed to load the login page.")

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract ASP.NET tokens
        viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
        viewstate_generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})["value"]
        event_validation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]

        # Step 2: Build your login data dictionary.
        # Make sure to update 'your_username' and 'your_password' with your actual credentials.
        # Confirm if 'pin' should be empty or have a specific value.
        login_data = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_generator,
            "__EVENTVALIDATION": event_validation,
            "username": self.username,  # Replace with actual username
            "password": self.password,  # Replace with actual password
            "pin": "",                    # Update if a pin is required
            "loginbutton": ""             # Typically, this might be blank as in the HTML
        }

        # Optionally, include headers that mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": login_url
        }

        # Step 3: POST the login data to the same URL
        post_response = session.post(login_url, data=login_data, headers=headers)

        # Step 4: Check the response for a successful login
        # You might need to adjust the condition based on the actual response content after a successful login.
        if "invalidUserNameOrPassword" in post_response.text:
            print("Login failed!")
            exit(401)
        else:
            print("Login likely succeeded!")
            # Optionally, access a protected page to verify:
            protected_url = f"https://{self.url}/api/Api/DashboardSchedule/getAbsencesList?day=2025-02-03&schoolId=35&certIncluded=true&delayIncluded=true"
            protected_response = session.get(protected_url)
            # print(protected_response.text)
        return session
    

    def get_StudentID(self):
        url_StudentID = f"https://{self.url}/api/Api/AppUser/GetUserInfo"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": "https://schule.louisenlund.de/modules/Login.aspx"
        }
        payload = {}
        studentID_response = self.session.get(url_StudentID, json=payload, headers=headers).json()
        self.name = studentID_response["userName"]
        # print(studentID_response)
        return studentID_response["crmEntityId"]
    

    def get_SchoolID(self):
        url_SchoolID = f"https://{self.url}/api/Api/AppUser/GetSchoolsForCurrentUser"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": "https://schule.louisenlund.de/modules/Login.aspx"
        }
        payload = {}
        schoolID_response = self.session.get(url_SchoolID, json=payload, headers=headers).json()
        # print(schoolID_response)
        return schoolID_response[0]["id"]

    
    def __init__(self, url, username, password, return_StudioTimes=False):
        self.url = url
        self.username = username
        self.password = password
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

        url_schedule = f"https://{self.url}/api/api/Schedule/GetSchedule"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": "https://schule.louisenlund.de/modules/Login.aspx"
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
                # Only add lessons if "StudioTimes" is not in the SubjectName or if return_studiotimes is True
                if "StudioTimes" not in i["SubjectName"] or self.return_studiotimes:
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
                        "StudentsPresent": students_present,
                        "Id": i["Id"]
                    }
                    
                    # Optionally print the values if you need to debug:
                    # print(i["SubjectName"], ical_start, ical_end, i["RoomName"], i["TeacherName"], students_present)
                    
                    formatted_lessons.append(lesson)
            
            ## BUG: Sort by time

            # simplify formatted lesson
            for i in range(1, len(formatted_lessons)):
                if formatted_lessons[i]["SubjectName"] == formatted_lessons[i - 1]["SubjectName"] and formatted_lessons[i]["Start"] == formatted_lessons[i - 1]["End"]:
                    formatted_lessons[i]["Start"] = formatted_lessons[i-1]["Start"]
                    formatted_lessons[i-1]["DELETE"] = True
            
            formatted_lessons = [lesson for lesson in formatted_lessons if ('DELETE' not in lesson) or (lesson.get('DELETE') is False)]

            return formatted_lessons
        return schedule_lessons