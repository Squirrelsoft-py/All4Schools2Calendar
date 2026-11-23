import json
import os
import re

import requests

import a4s_files
from a4s_files import ConfigError, get_filters, get_setting, load_config

CONFIG_FILENAME = a4s_files.CONFIG_FILENAME


class LoginError(Exception):
    """Raised when the login against the school portal fails."""


def normalize_host(url):
    """Normalize a school URL to its bare host name.

    Accepts 'schule.example.org', 'https://schule.example.org' and
    'https://schule.example.org/' and always returns 'schule.example.org'.
    """
    if not url:
        return url
    host = url.strip()
    if "//" in host:
        host = host.split("//", 1)[1]
    host = host.split("/", 1)[0]
    return host.strip()


def is_filtered(subject_name, filters=None):
    """Return True if a lesson is removed by one of the filters.

    The subject name and the filter are compared in lower case and without
    spaces, so the filter "StudioTimes" also matches "Studio Times digitalfrei".
    """
    if not subject_name:
        return False
    if filters is None:
        filters = get_filters()
    normalized = re.sub(r"[^a-z]", "", subject_name.lower())
    for pattern in filters:
        needle = re.sub(r"[^a-z]", "", str(pattern).lower())
        if needle and needle in normalized:
            return True
    return False


def example_credentials():
    """Return the placeholder user name and password of the example template."""
    example = a4s_files.example_path(a4s_files.CONFIG_FILENAME)
    try:
        with open(example, "r", encoding="utf-8") as file:
            section = json.load(file).get("a4s") or {}
        return section.get("username"), section.get("password")
    except (OSError, ValueError):
        return None, None


def resolve_credentials(config=None, path=None, url=None, username=None, password=None, pin=None):
    """Resolve the school credentials.

    Precedence: explicit arguments > environment variables (A4S_URL,
    A4S_USERNAME, A4S_PASSWORD, A4S_PIN) > the "a4s" section of the
    configuration file.
    """
    def from_environment(name):
        """Return an environment variable, an empty value is an error."""
        value = os.environ.get(name)
        if value is not None and value.strip() == "":
            raise ConfigError(
                f"The environment variable {name} is set but empty. In a compose "
                f"file the value has to be in quotes, yaml can cut it off at "
                f"special characters."
            )
        return value

    resolved = {
        "url": url or from_environment("A4S_URL"),
        "username": username or from_environment("A4S_USERNAME"),
        "password": password or from_environment("A4S_PASSWORD"),
        "pin": pin or os.environ.get("A4S_PIN"),
    }

    required = ("url", "username", "password")
    if not all(resolved[key] for key in required):
        if config is None:
            config = load_config(path)
        section = config.get("a4s") or {}
        for key in required:
            if not resolved[key]:
                resolved[key] = section.get(key)
        if not resolved["pin"]:
            resolved["pin"] = section.get("pin")

    missing = [key for key in required if not resolved[key]]
    if missing:
        raise ConfigError(
            "Missing credential(s): " + ", ".join(missing) + ". "
            "Add them to the 'a4s' section of the configuration file or set the "
            "environment variables A4S_URL, A4S_USERNAME and A4S_PASSWORD."
        )

    # The url may be given with or without scheme and trailing slash
    resolved["url"] = normalize_host(resolved["url"])
    if not resolved["url"]:
        raise ConfigError(
            "The 'url' is empty. Use the host name of the school portal only, "
            "e.g. 'schule.louisenlund.de'."
        )

    # The placeholder data of the example file is no login
    example_user, example_password = example_credentials()
    if (example_user and example_password
            and resolved["username"] == example_user
            and resolved["password"] == example_password):
        raise ConfigError(
            "The placeholder credentials of the example file are being used, the "
            "login would fail. Fill in your own data in "
            f"'{a4s_files.config_path(path)}' or in the environment variables."
        )
    return resolved


class Main:
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

    
    def __init__(self, url=None, username=None, password=None, filters=None, config=None, pin=None):
        credentials = resolve_credentials(config=config, url=url, username=username, password=password, pin=pin)
        self.url = credentials["url"]
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.pin = credentials["pin"]
        self.token = None
        # The filters are the subjects that are removed from the timetable
        self.filters = list(filters) if filters is not None else get_filters()
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
                # Skip the lessons that match one of the filters, for example "StudioTimes"
                if not is_filtered(i["SubjectName"], self.filters):
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