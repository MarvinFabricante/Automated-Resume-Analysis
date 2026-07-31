"""
Google Calendar API service layer.

Provides functions for interacting with real Google Calendar resources
(calendars, events) using the pickle-based OAuth flow from google_auth.
"""

from app.utils.google_auth import get_calendar_service as get_google_calendar_service
from googleapiclient.errors import HttpError


# ── Calendar operations ──────────────────────────────────────────────────────


def get_real_google_calendars(credentials_json: str):
    """Fetch all calendars from the authenticated Google account."""
    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return None
    try:
        calendar_list = service.calendarList().list().execute()
        items = calendar_list.get('items', [])
        results = []
        for item in items:
            results.append({
                "id": item.get('id'),
                "name": item.get('summary', 'Untitled Calendar'),
                "description": item.get('description', ''),
                "time_zone": item.get('timeZone', '(GMT+00:00) Coordinated Universal Time'),
                "owner_name": item.get('summary', 'Google User'),
                "owner_email": item.get('id', 'user@gmail.com'),
                "is_public": item.get('accessRole') == 'reader' or item.get('public', False),
                "public_permission": "See all event details",
                "secret_token": "google_api_authenticated",
                "public_url": f"https://calendar.google.com/calendar/embed?src={item.get('id')}",
                "embed_code": (
                    f'<iframe src="https://calendar.google.com/calendar/embed?src={item.get("id")}" '
                    f'style="border: 0" width="800" height="600" frameborder="0" scrolling="no"></iframe>'
                ),
                "public_ical_url": f"https://calendar.google.com/calendar/ical/{item.get('id')}/public/basic.ics",
                "secret_ical_url": f"https://calendar.google.com/calendar/ical/{item.get('id')}/private/basic.ics",
                "shares": [
                    {
                        "email": f"Access Role: {item.get('accessRole', 'owner')}",
                        "permission": item.get('accessRole', 'owner'),
                    }
                ],
                "labels": [
                    {"id": 1, "name": "Work", "color_hex": "#4285F4"},
                    {"id": 2, "name": "Personal", "color_hex": "#0B8043"},
                ],
                "notifications": {
                    "timed_notification_val": 30,
                    "timed_notification_unit": "minutes",
                    "allday_notification_val": 1,
                    "allday_notification_unit": "days",
                    "allday_notification_time": "17:00",
                    "notify_new_events": "Automatic",
                    "notify_changed_events": "Email",
                    "notify_canceled_events": "Email",
                    "notify_event_responses": "Email",
                    "notify_daily_agenda": "None",
                },
            })
        return results
    except HttpError as err:
        print(f"Google Calendar API Error: {err}")
        return None


def create_real_google_calendar(credentials_json: str, summary: str, description: str = "", time_zone: str = "UTC"):
    """Create a new secondary calendar on the authenticated account."""
    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return None
    try:
        cal_body = {
            'summary': summary,
            'description': description,
            'timeZone': time_zone,
        }
        created = service.calendars().insert(body=cal_body).execute()
        return created
    except HttpError as err:
        print(f"Google Calendar API Error creating calendar: {err}")
        return None


def delete_real_google_calendar(credentials_json: str, calendar_id: str):
    """Delete a calendar from the authenticated account."""
    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return False
    try:
        service.calendars().delete(calendarId=calendar_id).execute()
        return True
    except HttpError as err:
        print(f"Google Calendar API Error deleting calendar: {err}")
        return False


# ── Event operations ─────────────────────────────────────────────────────────


def get_real_google_events(credentials_json: str, calendar_id: str = "primary", max_results: int = 100):
    """List upcoming events from a specific calendar."""
    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return None
    try:
        events_result = service.events().list(
            calendarId=calendar_id or 'primary',
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime',
        ).execute()
        items = events_result.get('items', [])
        formatted = []
        for ev in items:
            start = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date') or ""
            end = ev.get('end', {}).get('dateTime') or ev.get('end', {}).get('date') or ""
            is_all_day = 'date' in ev.get('start', {})

            formatted.append({
                "id": ev.get('id'),
                "calendar_id": calendar_id or 'primary',
                "summary": ev.get('summary', 'Untitled Event'),
                "description": ev.get('description', ''),
                "location": ev.get('location', ''),
                "start_datetime": start,
                "end_datetime": end,
                "is_all_day": is_all_day,
                "label_color": "#4285F4",
                "label_name": "Google Event",
                "status": ev.get('status', 'confirmed').capitalize(),
                "created_at": ev.get('created', ''),
            })
        return formatted
    except HttpError as err:
        print(f"Google Calendar API Error listing events: {err}")
        return None


def create_real_google_event(
    credentials_json: str,
    calendar_id: str,
    summary: str,
    start_dt: str,
    end_dt: str,
    description: str = "",
    location: str = "",
    is_all_day: bool = False,
    attendees: list = None,
    create_meet_link: bool = False,
    interview_id: int = None,
):
    """
    Create a new event on the specified calendar.

    Optionally attaches attendees and a Google Meet conference link
    (used by interview scheduling).
    """
    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return None
    try:
        if is_all_day:
            start_body = {'date': start_dt.split('T')[0]}
            end_body = {'date': end_dt.split('T')[0]}
        else:
            # ensure ISO timezone
            if not start_dt.endswith('Z') and '+' not in start_dt:
                start_dt += 'Z'
            if not end_dt.endswith('Z') and '+' not in end_dt:
                end_dt += 'Z'
            start_body = {'dateTime': start_dt, 'timeZone': 'UTC'}
            end_body = {'dateTime': end_dt, 'timeZone': 'UTC'}

        body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': start_body,
            'end': end_body,
        }

        if attendees:
            body['attendees'] = attendees

        if create_meet_link and interview_id is not None:
            from datetime import datetime as _dt
            body['conferenceData'] = {
                'createRequest': {
                    'requestId': f"interview_{interview_id}_{_dt.now().timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'},
                }
            }

        kwargs = {
            'calendarId': calendar_id or 'primary',
            'body': body,
        }
        if create_meet_link:
            kwargs['conferenceDataVersion'] = 1
        if attendees:
            kwargs['sendUpdates'] = 'all'

        created = service.events().insert(**kwargs).execute()
        return created
    except HttpError as err:
        print(f"Google Calendar API Error creating event: {err}")
        return None


def delete_real_google_event(credentials_json: str, calendar_id: str, event_id: str):
    """Delete a single event from a calendar."""
    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return False
    try:
        service.events().delete(
            calendarId=calendar_id or 'primary',
            eventId=event_id,
        ).execute()
        return True
    except HttpError as err:
        print(f"Google Calendar API Error deleting event: {err}")
        return False


def query_freebusy(credentials_json: str, emails: list, time_min: str, time_max: str):
    """
    Query the freebusy API for a set of email addresses.
    Returns the raw 'calendars' dict from the API response, or None on failure.
    """
    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return None
    try:
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": e} for e in emails],
        }
        result = service.freebusy().query(body=body).execute()
        return result.get('calendars', {})
    except HttpError as err:
        print(f"Google Calendar API Error querying freebusy: {err}")
        return None
