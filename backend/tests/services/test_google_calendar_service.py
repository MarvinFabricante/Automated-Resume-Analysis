import pytest
from unittest.mock import patch, MagicMock
from app.services import google_calendar_service


@pytest.fixture
def mock_cal_service():
    service = MagicMock()
    with patch("app.services.google_calendar_service.get_google_calendar_service", return_value=(service, None)):
        yield service


def test_get_real_google_calendars(mock_cal_service):
    mock_cal_service.calendarList().list().execute.return_value = {
        "items": [
            {
                "id": "primary",
                "summary": "Work Calendar",
                "description": "Primary calendar",
                "timeZone": "Asia/Manila",
                "accessRole": "owner"
            }
        ]
    }

    calendars = google_calendar_service.get_real_google_calendars('{"fake": "creds_1"}')
    assert calendars is not None
    assert len(calendars) == 1
    assert calendars[0]["id"] == "primary"
    assert calendars[0]["name"] == "Work Calendar"


def test_create_and_delete_real_google_calendar(mock_cal_service):
    mock_cal_service.calendars().insert().execute.return_value = {
        "id": "new_cal_123",
        "summary": "Interviews"
    }
    mock_cal_service.calendars().delete().execute.return_value = {}

    created = google_calendar_service.create_real_google_calendar(
        '{"fake": "creds_2"}',
        summary="Interviews",
        description="Interview events"
    )
    assert created is not None
    assert created["id"] == "new_cal_123"

    deleted = google_calendar_service.delete_real_google_calendar('{"fake": "creds_2"}', "new_cal_123")
    assert deleted is True


def test_get_and_create_real_google_event(mock_cal_service):
    mock_cal_service.events().list().execute.return_value = {
        "items": [
            {
                "id": "event_101",
                "summary": "Technical Interview - John",
                "start": {"dateTime": "2026-10-21T09:00:00Z"},
                "end": {"dateTime": "2026-10-21T10:00:00Z"},
                "status": "confirmed"
            }
        ]
    }
    mock_cal_service.events().insert().execute.return_value = {
        "id": "event_102",
        "summary": "HR Interview"
    }

    events = google_calendar_service.get_real_google_events('{"fake": "creds_3"}', calendar_id="primary")
    assert events is not None
    assert len(events) == 1
    assert events[0]["id"] == "event_101"
    assert events[0]["summary"] == "Technical Interview - John"

    created_ev = google_calendar_service.create_real_google_event(
        '{"fake": "creds_3"}',
        calendar_id="primary",
        summary="HR Interview",
        start_dt="2026-10-22T10:00:00Z",
        end_dt="2026-10-22T11:00:00Z"
    )
    assert created_ev is not None
    assert created_ev["id"] == "event_102"


def test_update_and_delete_real_google_event(mock_cal_service):
    mock_cal_service.events().patch().execute.return_value = {
        "id": "event_102",
        "summary": "Updated HR Interview"
    }
    mock_cal_service.events().delete().execute.return_value = {}

    updated = google_calendar_service.update_real_google_event(
        '{"fake": "creds_4"}',
        calendar_id="primary",
        event_id="event_102",
        summary="Updated HR Interview"
    )
    assert updated is not None
    assert updated["summary"] == "Updated HR Interview"

    deleted = google_calendar_service.delete_real_google_event(
        '{"fake": "creds_4"}',
        calendar_id="primary",
        event_id="event_102"
    )
    assert deleted is True


def test_query_freebusy(mock_cal_service):
    mock_cal_service.freebusy().query().execute.return_value = {
        "calendars": {
            "hr@mariwasa.com": {
                "busy": [
                    {"start": "2026-10-21T08:00:00Z", "end": "2026-10-21T09:00:00Z"}
                ]
            }
        }
    }

    res = google_calendar_service.query_freebusy(
        '{"fake": "creds_5"}',
        emails=["hr@mariwasa.com"],
        time_min="2026-10-21T00:00:00Z",
        time_max="2026-10-21T23:59:59Z"
    )
    assert res is not None
    assert "hr@mariwasa.com" in res
    assert len(res["hr@mariwasa.com"]["busy"]) == 1


def test_service_unavailable_handling():
    with patch("app.services.google_calendar_service.get_google_calendar_service", return_value=(None, None)):
        creds = '{"fake": "creds_none"}'
        assert google_calendar_service.get_real_google_calendars(creds) is None
        assert google_calendar_service.create_real_google_calendar(creds, "Test") is None
        assert google_calendar_service.delete_real_google_calendar(creds, "cal_id") is False
        assert google_calendar_service.get_real_google_events(creds) is None
        assert google_calendar_service.create_real_google_event(creds, "primary", "Test", "2026-10-20", "2026-10-21") is None
        assert google_calendar_service.update_real_google_event(creds, "primary", "ev_id") is None
        assert google_calendar_service.delete_real_google_event(creds, "primary", "ev_id") is False
        assert google_calendar_service.query_freebusy(creds, ["test@example.com"], "2026-10-20", "2026-10-21") is None
