"""A local mock of the CalDAV calendar.

The mock keeps the events in memory and offers the same methods as
caldav_api.Main, so the tests never write to a real calendar.
"""

import copy
import datetime


def event(uid, summary, description, start, end):
    """Build an event like caldav_api.get_events_in_date_range returns it"""
    return {
        "id": uid,
        "caldav_url": f"https://calendar.example.com/{uid}.ics",
        "summary": summary,
        "description": description,
        "start": {"dateTime": start, "timeZone": "Europe/Berlin"},
        "end": {"dateTime": end, "timeZone": "Europe/Berlin"},
    }


def lesson_event(uid, lesson_id, summary=None, start=None, end=None, teacher=None,
                 students=None, room=None):
    """Build the event of a lesson, with the marker that links it to the lesson.

    The description is built like the sync does it, so an unchanged lesson
    produces an unchanged event.
    """
    if summary is None:
        summary = f'{lesson_id["SubjectName"]} {lesson_id["RoomName"]}'
    if teacher is None:
        teacher = lesson_id["TeacherName"] + (lesson_id["AdditionalTeacherNamesString"] or "")
    if room is None:
        room = lesson_id["RoomName"] + (lesson_id["AdditionalRooms"] or "")
    if students is None:
        students = (lesson_id["StudentsCount"] - lesson_id["AbsenceCount"]
                    - lesson_id["DispensationCount"])
    start = start or lesson_id["start"]
    end = end or lesson_id["end"]
    description = (f"Lehrer: {teacher}\nRaum: {room}\nAnwesend: {students}\n"
                   f'###{lesson_id["Id"]}###')
    return event(uid, summary, description, start, end)


class MockCalDAV:
    """An in memory stand in for caldav_api.Main"""

    def __init__(self, events=None):
        self.events = list(events or [])
        self.calls = []

    # --- the api of caldav_api.Main --------------------------------------
    def get_events_in_date_range(self, time_min, time_max):
        self.calls.append(("get_events", time_min, time_max))
        return copy.deepcopy(self.events)

    def create_event(self, name, description, start, end):
        self.calls.append(("create", name, start, end))
        uid = f"new-{len(self.events)}"
        self.events.append(event(uid, name, description, start, end))
        return f"https://calendar.example.com/{uid}.ics"

    def update_event(self, event_id, name, description, start, end):
        self.calls.append(("update", event_id, name, start, end))
        for existing in self.events:
            if existing["id"] == event_id:
                existing["summary"] = name
                existing["description"] = description
                existing["start"] = {"dateTime": start, "timeZone": "Europe/Berlin"}
                existing["end"] = {"dateTime": end, "timeZone": "Europe/Berlin"}
                return existing["caldav_url"]
        raise KeyError(event_id)

    def delete_event_by_id(self, event_id):
        self.calls.append(("delete", event_id))
        self.events = [e for e in self.events if e["id"] != event_id]
        return True

    # --- helpers for the tests -------------------------------------------
    def summaries(self):
        return [e["summary"] for e in self.events]

    def calls_of(self, name):
        return [call for call in self.calls if call[0] == name]

    def reset_calls(self):
        self.calls = []


def today_at(hour, minute=0):
    """Return an ISO time of today, the tests work with the current day"""
    moment = datetime.datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return moment.isoformat()
