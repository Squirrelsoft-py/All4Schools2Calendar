"""Tests for the access to the school portal, against the local mock server"""

import datetime

import pytest

import all4s_lib


def today():
    """The first day of the period that is asked for"""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def tomorrow():
    """The last day of the period that is asked for"""
    return (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")


def test_login_against_the_mock_server(portal):
    a4s = all4s_lib.Main()
    assert a4s.token == "mock-json-web-token"
    assert a4s.studentID == 4242
    assert a4s.schoolID == 35
    assert a4s.name == "Test User"


def test_login_with_a_wrong_password_fails(portal, monkeypatch):
    monkeypatch.setenv("A4S_PASSWORD", "wrong")
    with pytest.raises(all4s_lib.LoginError) as error:
        all4s_lib.Main()
    assert "Login failed" in str(error.value)


def test_get_schedule_returns_the_lessons(portal):
    a4s = all4s_lib.Main()
    lessons = a4s.get_schedule(formatted=False, start_time=today(), end_time=tomorrow())
    subjects = [lesson["SubjectName"] for lesson in lessons]
    assert "Mathe" in subjects
    assert "Sport" in subjects


def test_the_studio_times_are_filtered(portal):
    a4s = all4s_lib.Main()
    subjects = [lesson["SubjectName"] for lesson
                in a4s.get_schedule(start_time=today(), end_time=tomorrow())]
    assert not any("Studio" in subject for subject in subjects)


def test_the_studio_times_can_be_kept(portal, monkeypatch):
    monkeypatch.setenv("A4S_FILTERS", "")
    a4s = all4s_lib.Main()
    subjects = [lesson["SubjectName"] for lesson
                in a4s.get_schedule(start_time=today(), end_time=tomorrow())]
    assert any("Studio" in subject for subject in subjects)


def test_the_filter_matches_the_spellings():
    assert all4s_lib.is_filtered("StudioTimes Sprachen")
    assert all4s_lib.is_filtered("Studio Times digitalfrei")
    assert all4s_lib.is_filtered("StudioTimes Spezial")
    assert not all4s_lib.is_filtered("Mathe eA")


def test_the_url_is_normalized():
    assert all4s_lib.normalize_url("schule.example.org") == "https://schule.example.org"
    assert all4s_lib.normalize_url("https://schule.example.org/") == "https://schule.example.org"
    assert all4s_lib.normalize_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"


def test_an_empty_password_is_reported(portal, monkeypatch):
    monkeypatch.setenv("A4S_PASSWORD", "")
    with pytest.raises(all4s_lib.ConfigError) as error:
        all4s_lib.resolve_credentials()
    assert "empty" in str(error.value)


def test_the_tests_cannot_reach_the_real_portal():
    """The guard of the fixtures has to stop every request to a real host"""
    import requests

    with pytest.raises(RuntimeError) as error:
        # 192.0.2.1 is reserved for tests and can not be reached
        requests.get("https://192.0.2.1/", timeout=1)
    assert "local mocks" in str(error.value)


def test_the_api_needs_the_token(mock_server):
    """The portal only answers the api calls with the token of the login"""
    import requests

    response = requests.get(f"{mock_server.url}/api/Api/AppUser/GetUserInfo")
    assert response.status_code == 401

    token = requests.post(f"{mock_server.url}/api/Api/Authorization/JwtAuth",
                          json={"Username": "test-user", "Password": "test-password"}).json()
    response = requests.get(f"{mock_server.url}/api/Api/AppUser/GetUserInfo",
                            headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_the_client_sends_the_token(mock_server, portal):
    """The login is enough, the following requests carry the token"""
    all4s_lib.Main().get_schedule(formatted=False)
    assert any(request[0] == "POST" for request in mock_server.requests)


def test_the_portal_only_returns_the_requested_period(mock_server, portal):
    """The mock limits the timetable to the period that was asked for"""
    import requests

    token = requests.post(f"{mock_server.url}/api/Api/Authorization/JwtAuth",
                          json={"Username": "test-user", "Password": "test-password"}).json()
    response = requests.post(f"{mock_server.url}/api/api/Schedule/GetSchedule",
                             json={"from": "2026-01-01", "to": "2026-01-31"},
                             headers={"Authorization": f"Bearer {token}"})
    assert response.json()["lessons"] == []
