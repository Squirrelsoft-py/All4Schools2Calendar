"""Tests for the sync, against the local mock server and the mock calendar"""

import a4s_main_caldav
from tests.mock_a4s import sample_lessons
from tests.mock_caldav import MockCalDAV, event, lesson_event, today_at


def lesson_from_sample(number):
    """Return one of the lessons of the sample timetable"""
    return sample_lessons()[number]


def event_of(mock_calendar, lesson_id):
    """Return the event of a lesson"""
    for existing in mock_calendar.events:
        if f"###{lesson_id}###" in existing["description"]:
            return existing
    return None


def test_the_lessons_are_written_into_the_calendar(portal, mock_calendar):
    a4s_main_caldav.main()

    # five lessons, the two studio times are filtered
    assert len(mock_calendar.events) == 4
    assert "Mathe H1.1" in mock_calendar.summaries()
    assert not any("Studio" in summary for summary in mock_calendar.summaries())


def test_the_sync_is_idempotent(portal, mock_calendar):
    a4s_main_caldav.main()
    mock_calendar.reset_calls()

    a4s_main_caldav.main()

    # the second run only reads, it does not change anything
    assert mock_calendar.calls_of("create") == []
    assert mock_calendar.calls_of("update") == []
    assert mock_calendar.calls_of("delete") == []


def test_a_lesson_that_is_gone_is_deleted(portal, mock_calendar):
    lesson = lesson_from_sample(0)
    # the marker of the event points to a lesson that is not in the timetable
    gone = dict(lesson, Id="9999")
    mock_calendar.events = [lesson_event("e1", gone)]

    a4s_main_caldav.main()

    assert event_of(mock_calendar, "9999") is None
    assert len(mock_calendar.calls_of("delete")) == 1


def test_a_changed_room_is_updated_in_place(portal, mock_calendar):
    lesson = lesson_from_sample(0)
    # the event still has the old room
    mock_calendar.events = [lesson_event("e1", lesson, summary="Mathe H2.2", room="H2.2")]

    a4s_main_caldav.main()

    assert len(mock_calendar.calls_of("update")) == 1
    assert len(mock_calendar.calls_of("delete")) == 0
    assert event_of(mock_calendar, lesson["Id"])["id"] == "e1"
    assert event_of(mock_calendar, lesson["Id"])["summary"] == "Mathe H1.1"


def test_a_changed_time_is_updated_in_place(portal, mock_calendar):
    lesson = lesson_from_sample(0)
    mock_calendar.events = [lesson_event("e1", lesson, start=today_at(3), end=today_at(4))]

    a4s_main_caldav.main()

    assert len(mock_calendar.calls_of("update")) == 1
    assert event_of(mock_calendar, lesson["Id"])["start"]["dateTime"] == lesson["start"]


def test_a_changed_teacher_is_updated_in_place(portal, mock_calendar):
    lesson = lesson_from_sample(0)
    mock_calendar.events = [lesson_event("e1", lesson, teacher="Niemand")]

    a4s_main_caldav.main()

    assert len(mock_calendar.calls_of("update")) == 1
    assert "Frau Test" in event_of(mock_calendar, lesson["Id"])["description"]


def test_a_duplicate_is_deleted(portal, mock_calendar):
    lesson = lesson_from_sample(0)
    mock_calendar.events = [lesson_event("e1", lesson), lesson_event("e2", lesson)]

    a4s_main_caldav.main()

    assert len(mock_calendar.calls_of("delete")) == 1
    remaining = [e["id"] for e in mock_calendar.events
                 if f"###{lesson['Id']}###" in e["description"]]
    assert remaining == ["e1"]


def test_an_event_without_a_marker_is_kept(portal, mock_calendar):
    handmade = event("e9", "Orchesterprobe", "von Hand angelegt",
                     today_at(18), today_at(19))
    mock_calendar.events = [handmade]

    a4s_main_caldav.main()

    assert "Orchesterprobe" in mock_calendar.summaries()
    assert not mock_calendar.calls_of("delete")
