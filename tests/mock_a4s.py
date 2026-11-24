"""A local mock of the All4Schools API.

The server runs on 127.0.0.1 and serves the same endpoints as the school
portal, so the tests never touch the real portal.
"""

import datetime
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

USERNAME = "test-user"
PASSWORD = "test-password"
TOKEN = "mock-json-web-token"
SCHOOL_ID = 35
STUDENT_ID = 4242


def lesson(id, subject, room, start, end, teacher="Frau Test", students=20,
           additional_teacher=None, additional_room=None):
    """Build a lesson like the school portal returns it"""
    return {
        "Id": id,
        "BaseLesson_Id": id,
        "AdditionalLessonIdsString": None,
        "AdditionalTeacherNamesString": additional_teacher,
        "AdditionalRooms": additional_room,
        "SubjectName": subject,
        "RoomName": room,
        "TeacherName": teacher,
        "StudentsCount": students,
        "AbsenceCount": 0,
        "DispensationCount": 0,
        "SubId": None,
        "SubState": None,
        "SubAbsId": None,
        "start": start,
        "end": end,
    }


def sample_lessons(date=None):
    """Build a timetable for a day, the times are relative to that day"""
    if date is None:
        date = datetime.date.today()
    if isinstance(date, str):
        try:
            date = datetime.date.fromisoformat(date)
        except ValueError:
            date = datetime.date.today()

    def at(hour, minute=0):
        moment = datetime.datetime.combine(date, datetime.time(hour, minute))
        return moment.isoformat()

    return [
        lesson("1001", "Mathe", "H1.1", at(8), at(9)),
        lesson("1002", "Sport", "HS1", at(10), at(11, 30), teacher="Herr Test"),
        lesson("1003", "StudioTimes Sprachen", "H2.1.Lernstudio", at(12), at(13)),
        lesson("1004", "Studio Times digitalfrei", "H3.1.Seminar 3", at(12), at(13)),
        lesson("1005", "Gilde", "KuK", at(19, 30), at(20, 30),
               additional_teacher=", Herr Test"),
        lesson("1006", "Physik", "H3.1", at(16), at(17), students=25),
    ]


class MockA4SServer:
    """A local server that behaves like the REST API of the school portal

    It behaves like the real portal in the points that matter for the tests:
    the credentials are checked, the api calls need the token and the
    timetable is limited to the requested period.
    """

    def __init__(self, lessons=None):
        self.lessons = lessons
        self.requests = []

    # --- the api ---------------------------------------------------------
    def handle_login(self, body):
        if body.get("Username") != USERNAME or body.get("Password") != PASSWORD:
            return 401, {"Message": "invalidUserNameOrPassword"}
        return 200, TOKEN

    def handle_schedule(self, body):
        lessons = self.lessons if self.lessons is not None else sample_lessons()

        # the portal only returns the lessons of the requested period
        start = body.get("from")
        end = body.get("to")
        if start and end:
            lessons = [lesson for lesson in lessons
                       if start <= lesson["start"][:10] <= end]

        return 200, {"lessons": lessons}

    # --- the server ------------------------------------------------------
    def start(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _read(self):
                length = int(self.headers.get("Content-Length") or 0)
                if not length:
                    return {}
                try:
                    return json.loads(self.rfile.read(length))
                except ValueError:
                    return {}

            def _reply(self, status, payload):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _authorized(self):
                """The api calls need the token of the login"""
                return self.headers.get("Authorization") == f"Bearer {TOKEN}"

            def do_POST(self):
                body = self._read()
                server.requests.append(("POST", self.path, body))

                if self.path.endswith("/api/Api/Authorization/JwtAuth"):
                    status, payload = server.handle_login(body)
                elif not self._authorized():
                    status, payload = 401, {"Message": "no valid token"}
                elif self.path.endswith("/api/api/Schedule/GetSchedule"):
                    status, payload = server.handle_schedule(body)
                else:
                    status, payload = 404, {"Message": "not found"}
                self._reply(status, payload)

            def do_GET(self):
                server.requests.append(("GET", self.path, None))

                if not self._authorized():
                    self._reply(401, {"Message": "no valid token"})
                elif self.path.endswith("/api/Api/AppUser/GetUserInfo"):
                    self._reply(200, {"userName": "Test User", "crmEntityId": STUDENT_ID})
                elif self.path.endswith("/api/Api/AppUser/GetSchoolsForCurrentUser"):
                    self._reply(200, [{"id": SCHOOL_ID, "name": "Test Schule"}])
                else:
                    self._reply(404, {"Message": "not found"})

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    @property
    def url(self):
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"
