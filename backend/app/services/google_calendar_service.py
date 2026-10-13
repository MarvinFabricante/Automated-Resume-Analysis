"""
Google Calendar API service layer with Redis-first architecture.

Provides functions for interacting with real Google Calendar resources
(calendars, events) using the pickle-based OAuth flow from google_auth.
All write operations are staged in Redis first before executing against
the Google Calendar API, and read operations check Redis cache first.
"""

import hashlib
import json
import logging
from typing import Optional, List, Dict, Any
from googleapiclient.errors import HttpError

from app.utils.google_auth import get_calendar_service as get_google_calendar_service
from app.utils.redis_client import (
    get_sync_redis,
    redis_tx_manager,
    sanitize_payload,
)

logger = logging.getLogger(__name__)


def _cred_hash(credentials_json: str) -> str:
    """Return a short hash of credentials string for cache partitioning."""
    return hashlib.sha256(credentials_json.encode("utf-8")).hexdigest()[:16]


def _sync_get_cache(key: str) -> Optional[Any]:
    try:
        r = get_sync_redis()
        val = r.get(key)
        if val:
            return json.loads(val.decode("utf-8"))
    except Exception:
        pass
    return None


def _sync_set_cache(key: str, val: Any, ttl: int = 300):
    try:
        r = get_sync_redis()
        r.setex(key, ttl, json.dumps(sanitize_payload(val)).encode("utf-8"))
    except Exception:
        pass


def _sync_del_pattern(pattern: str):
    try:
        r = get_sync_redis()
        clean = pattern.strip("*")
        keys = list(r.scan_iter(match=f"*{clean}*"))
        if keys:
            r.delete(*keys)
    except Exception:
        pass


# ── Calendar operations ──────────────────────────────────────────────────────


def get_real_google_calendars(credentials_json: str):
    """Fetch all calendars from the authenticated Google account with Redis caching."""
    cred_h = _cred_hash(credentials_json)
    cache_key = f"google_cal:list:{cred_h}"
    cached = _sync_get_cache(cache_key)
    if cached is not None:
        return cached

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
        _sync_set_cache(cache_key, results, ttl=300)
        return results
    except HttpError as err:
        logger.error(f"Google Calendar API Error: {err}")
        return None


def create_real_google_calendar(credentials_json: str, summary: str, description: str = "", time_zone: str = "UTC"):
    """Create a new secondary calendar on the authenticated account (Redis-first)."""
    tx_id = redis_tx_manager.stage_transaction_sync(
        target="google_calendar",
        action="CREATE_CALENDAR",
        payload={"summary": summary, "description": description, "time_zone": time_zone},
    )

    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        redis_tx_manager.fail_transaction_sync(tx_id, "Google service unavailable")
        return None
    try:
        cal_body = {
            'summary': summary,
            'description': description,
            'timeZone': time_zone,
        }
        created = service.calendars().insert(body=cal_body).execute()
        redis_tx_manager.commit_transaction_sync(tx_id, created)
        _sync_del_pattern(f"google_cal:list:{_cred_hash(credentials_json)}")
        return created
    except HttpError as err:
        logger.error(f"Google Calendar API Error creating calendar: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        return None


def delete_real_google_calendar(credentials_json: str, calendar_id: str):
    """Delete a calendar from the authenticated account (Redis-first)."""
    tx_id = redis_tx_manager.stage_transaction_sync(
        target="google_calendar",
        action="DELETE_CALENDAR",
        payload={"calendar_id": calendar_id},
    )

    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        redis_tx_manager.fail_transaction_sync(tx_id, "Google service unavailable")
        return False
    try:
        service.calendars().delete(calendarId=calendar_id).execute()
        redis_tx_manager.commit_transaction_sync(tx_id, {"deleted": True})
        _sync_del_pattern(f"google_cal:list:{_cred_hash(credentials_json)}")
        return True
    except HttpError as err:
        logger.error(f"Google Calendar API Error deleting calendar: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        return False


# ── Event operations ─────────────────────────────────────────────────────────


def get_real_google_events(
    credentials_json: str,
    calendar_id: str = "primary",
    max_results: int = 150,
    time_min: str = None,
    time_max: str = None,
):
    """List events from a specific calendar with Redis caching."""
    cred_h = _cred_hash(credentials_json)
    cache_key = f"google_cal:events:{cred_h}:{calendar_id}:{time_min}:{time_max}:{max_results}"
    cached = _sync_get_cache(cache_key)
    if cached is not None:
        return cached

    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        return None
    try:
        kwargs = {
            "calendarId": calendar_id or 'primary',
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            kwargs["timeMin"] = time_min
        if time_max:
            kwargs["timeMax"] = time_max

        events_result = service.events().list(**kwargs).execute()
        events = events_result.get('items', [])
        formatted = []
        for ev in events:
            start_info = ev.get('start', {})
            end_info = ev.get('end', {})
            is_all_day = 'date' in start_info
            start = start_info.get('dateTime') or start_info.get('date', '')
            end = end_info.get('dateTime') or end_info.get('date', '')

            formatted.append({
                "id": ev.get('id'),
                "calendar_id": calendar_id,
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
                "html_link": ev.get('htmlLink', ''),
                "meet_link": "",
            })
        _sync_set_cache(cache_key, formatted, ttl=180)
        return formatted
    except HttpError as err:
        logger.error(f"Google Calendar API Error listing events: {err}")
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
    """Create a new event on Google Calendar (Redis-first)."""
    tx_id = redis_tx_manager.stage_transaction_sync(
        target="google_calendar",
        action="CREATE_EVENT",
        payload={
            "calendar_id": calendar_id,
            "summary": summary,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "interview_id": interview_id,
        },
    )

    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        redis_tx_manager.fail_transaction_sync(tx_id, "Google service unavailable")
        return None
    try:
        body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {'date': start_dt} if is_all_day else {'dateTime': start_dt},
            'end': {'date': end_dt} if is_all_day else {'dateTime': end_dt},
        }

        if attendees:
            body['attendees'] = attendees

        kwargs = {
            'calendarId': calendar_id or 'primary',
            'body': body,
        }
        if attendees:
            kwargs['sendUpdates'] = 'all'

        created = service.events().insert(**kwargs).execute()
        redis_tx_manager.commit_transaction_sync(tx_id, created)
        _sync_del_pattern(f"google_cal:events:{_cred_hash(credentials_json)}")
        return created
    except HttpError as err:
        logger.error(f"Google Calendar API Error creating event: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        return None


def update_real_google_event(
    credentials_json: str,
    calendar_id: str,
    event_id: str,
    summary: str = None,
    start_dt: str = None,
    end_dt: str = None,
    description: str = None,
    location: str = None,
    status: str = None,
):
    """Update an existing event on Google Calendar (Redis-first)."""
    tx_id = redis_tx_manager.stage_transaction_sync(
        target="google_calendar",
        action="UPDATE_EVENT",
        payload={
            "calendar_id": calendar_id,
            "event_id": event_id,
            "summary": summary,
            "start_dt": start_dt,
            "end_dt": end_dt,
        },
    )

    service, _ = get_google_calendar_service(credentials_json)
    if not service or not event_id:
        redis_tx_manager.fail_transaction_sync(tx_id, "Google service unavailable or missing event_id")
        return None
    try:
        body = {}
        if summary is not None:
            body['summary'] = summary
        if description is not None:
            body['description'] = description
        if location is not None:
            body['location'] = location
        if status is not None:
            body['status'] = status.lower()
        if start_dt:
            body['start'] = {'dateTime': start_dt}
        if end_dt:
            body['end'] = {'dateTime': end_dt}

        updated = service.events().patch(
            calendarId=calendar_id or 'primary',
            eventId=event_id,
            body=body,
            sendUpdates='all',
        ).execute()
        redis_tx_manager.commit_transaction_sync(tx_id, updated)
        _sync_del_pattern(f"google_cal:events:{_cred_hash(credentials_json)}")
        return updated
    except HttpError as err:
        logger.error(f"Google Calendar API Error updating event {event_id}: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        return None


def get_single_google_event(credentials_json: str, calendar_id: str, event_id: str):
    """Fetch a single event by ID with Redis caching."""
    cred_h = _cred_hash(credentials_json)
    cache_key = f"google_cal:event:{cred_h}:{calendar_id}:{event_id}"
    cached = _sync_get_cache(cache_key)
    if cached is not None:
        return cached

    service, _ = get_google_calendar_service(credentials_json)
    if not service or not event_id:
        return None
    try:
        ev = service.events().get(
            calendarId=calendar_id or 'primary',
            eventId=event_id,
        ).execute()
        _sync_set_cache(cache_key, ev, ttl=300)
        return ev
    except HttpError as err:
        logger.error(f"Google Calendar API Error fetching event {event_id}: {err}")
        return None


def delete_real_google_event(credentials_json: str, calendar_id: str, event_id: str):
    """Delete a single event from a calendar (Redis-first)."""
    tx_id = redis_tx_manager.stage_transaction_sync(
        target="google_calendar",
        action="DELETE_EVENT",
        payload={"calendar_id": calendar_id, "event_id": event_id},
    )

    service, _ = get_google_calendar_service(credentials_json)
    if not service:
        redis_tx_manager.fail_transaction_sync(tx_id, "Google service unavailable")
        return False
    try:
        service.events().delete(
            calendarId=calendar_id or 'primary',
            eventId=event_id,
        ).execute()
        redis_tx_manager.commit_transaction_sync(tx_id, {"deleted": True})
        _sync_del_pattern(f"google_cal:events:{_cred_hash(credentials_json)}")
        return True
    except HttpError as err:
        logger.error(f"Google Calendar API Error deleting event: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        return False


def query_freebusy(credentials_json: str, emails: list, time_min: str, time_max: str):
    """Query freebusy API with Redis caching."""
    cred_h = _cred_hash(credentials_json)
    emails_str = ",".join(sorted(emails or []))
    cache_key = f"google_cal:freebusy:{cred_h}:{emails_str}:{time_min}:{time_max}"
    cached = _sync_get_cache(cache_key)
    if cached is not None:
        return cached

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
        cal_data = result.get('calendars', {})
        _sync_set_cache(cache_key, cal_data, ttl=120)
        return cal_data
    except HttpError as err:
        logger.error(f"Google Calendar API Error querying freebusy: {err}")
        return None
