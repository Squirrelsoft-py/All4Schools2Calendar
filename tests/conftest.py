"""Fixtures for the tests.

The tests never talk to the real school portal and never write to a real
calendar, they use the local mocks.
"""

import os
import sys
from urllib.parse import urlparse

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.mock_a4s import MockA4SServer, PASSWORD, USERNAME
from tests.mock_caldav import MockCalDAV


@pytest.fixture(autouse=True)
def block_external_requests(monkeypatch):
    """The tests must never talk to the real portal or to a real calendar.

    Every request that does not go to 127.0.0.1 is refused, so a test that
    forgets the mock fails instead of touching the real services.
    """
    original = requests.Session.request

    def guarded(self, method, url, *args, **kwargs):
        host = urlparse(url).hostname
        if host not in ("127.0.0.1", "localhost"):
            raise RuntimeError(
                f"the tests must not reach '{url}', use the local mocks instead"
            )
        return original(self, method, url, *args, **kwargs)

    monkeypatch.setattr(requests.Session, "request", guarded)


@pytest.fixture
def mock_server():
    """A local server that behaves like the REST API of the school portal"""
    server = MockA4SServer().start()
    yield server
    server.stop()


@pytest.fixture
def mock_calendar(monkeypatch):
    """A local calendar, caldav_api.Main is replaced by it"""
    import a4s_main_caldav
    import caldav_api

    calendar = MockCalDAV()

    def fake_main(*args, **kwargs):
        return calendar

    monkeypatch.setattr(caldav_api, "Main", fake_main)
    monkeypatch.setattr(a4s_main_caldav.caldav_api, "Main", fake_main)
    return calendar


@pytest.fixture
def portal(mock_server, monkeypatch):
    """Point the configuration at the local mock server"""
    monkeypatch.setenv("A4S_URL", mock_server.url)
    monkeypatch.setenv("A4S_USERNAME", USERNAME)
    monkeypatch.setenv("A4S_PASSWORD", PASSWORD)
    monkeypatch.setenv("A4S_PIN", "")
    monkeypatch.setenv("A4S_FILTERS", "StudioTimes")
    monkeypatch.setenv("CALDAV_CALENDAR_NAME", "Stundenplan")
    return mock_server
