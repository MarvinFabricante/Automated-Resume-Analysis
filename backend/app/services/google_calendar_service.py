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
import socket
import time
from typing import Optional, List, Dict, Any
from googleapiclient.errors import HttpError

from app.utils.google_auth import get_calendar_service as get_google_calendar_service
from app.utils.redis_client import (
    get_sync_redis,
    redis_tx_manager,
    sanitize_payload,
)

logger = logging.getLogger(__name__)


# ── Custom Exceptions for Google Calendar API ─────────────────────────────────

class GoogleCalendarError(Exception):
    """Base exception for Google Calendar operations."""
    pass


class GoogleCalendarRateLimitError(GoogleCalendarError):
    """Raised when Google Calendar API returns 429 or rate limit/quota exceeded."""
    pass


class GoogleCalendarTimeoutError(GoogleCalendarError):
    """Raised when Google Calendar API request times out."""
    pass


def _is_rate_limit_error(err: Exception) -> bool:
    """Check if exception represents a 429 rate limit or quota exceeded error."""
    if isinstance(err, GoogleCalendarRateLimitError):
        return True
    if isinstance(err, HttpError):
        status = getattr(getattr(err, "resp", None), "status", None)
        if status in [429, 403]:
            content = str(getattr(err, "content", "")).lower()
            if status == 429 or "ratelimit" in content or "user_rate_limit" in content or "quota" in content:
                return True
    err_str = str(err).lower()
    return "429" in err_str or "rate limit" in err_str or "quota exceeded" in err_str or "user_rate_limit" in err_str or "too many requests" in err_str


def _is_timeout_error(err: Exception) -> bool:
    """Check if exception represents a network or API timeout."""
    if isinstance(err, GoogleCalendarTimeoutError):
        return True
    if isinstance(err, (TimeoutError, socket.timeout)):
        return True
    err_str = str(err).lower()
    return "timeout" in err_str or "timed out" in err_str or "deadline exceeded" in err_str


def execute_with_retry(
    api_call_fn,
    max_retries: int = 3,
    initial_delay: float = 0.05,
    backoff_factor: float = 2.0,
    operation_name: str = "Google Calendar API call",
):
    """
    Executes a Google Calendar API callable with graceful retry on 429 rate limit or timeout.
    If transient, retries up to max_retries with exponential backoff.
    If retries are exhausted, raises GoogleCalendarRateLimitError or GoogleCalendarTimeoutError.
    """
    delay = initial_delay
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            return api_call_fn()
        except Exception as err:
            last_err = err
            is_429 = _is_rate_limit_error(err)
            is_timeout = _is_timeout_error(err)

            if (is_429 or is_timeout) and attempt < max_retries:
                logger.warning(
                    f"[{operation_name}] Transient error (attempt {attempt}/{max_retries}): {err}. Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)
                delay *= backoff_factor
                continue

            # Retries exhausted or non-retryable error
            if is_429:
                logger.error(f"[{operation_name}] Rate limit (429) exceeded after {attempt} attempts: {err}")
                raise GoogleCalendarRateLimitError(
                    "Google Calendar API rate limit exceeded (429). The interview could not be scheduled. No booking was created. Please try again later."
                ) from err
            elif is_timeout:
                logger.error(f"[{operation_name}] Timeout after {attempt} attempts: {err}")
                raise GoogleCalendarTimeoutError(
                    "Google Calendar API request timed out. The interview could not be scheduled. No booking was created. Please try again later."
                ) from err
            else:
                raise


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

        def _do_insert():
            return service.events().insert(**kwargs).execute()

        created = execute_with_retry(_do_insert, max_retries=3, initial_delay=0.05, operation_name="create_real_google_event")
        redis_tx_manager.commit_transaction_sync(tx_id, created)
        _sync_del_pattern(f"google_cal:events:{_cred_hash(credentials_json)}")
        return created
    except (GoogleCalendarRateLimitError, GoogleCalendarTimeoutError) as err:
        logger.error(f"Google Calendar API rate limit/timeout creating event: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        raise
    except HttpError as err:
        logger.error(f"Google Calendar API Error creating event: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        if _is_rate_limit_error(err):
            raise GoogleCalendarRateLimitError(
                "Google Calendar API rate limit exceeded (429). The interview could not be scheduled. No booking was created. Please try again later."
            ) from err
        raise
    except Exception as err:
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        if _is_timeout_error(err):
            raise GoogleCalendarTimeoutError(
                "Google Calendar API request timed out. The interview could not be scheduled. No booking was created. Please try again later."
            ) from err
        raise


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

        def _do_patch():
            return service.events().patch(
                calendarId=calendar_id or 'primary',
                eventId=event_id,
                body=body,
                sendUpdates='all',
            ).execute()

        updated = execute_with_retry(_do_patch, max_retries=3, initial_delay=0.05, operation_name="update_real_google_event")
        redis_tx_manager.commit_transaction_sync(tx_id, updated)
        _sync_del_pattern(f"google_cal:events:{_cred_hash(credentials_json)}")
        return updated
    except (GoogleCalendarRateLimitError, GoogleCalendarTimeoutError) as err:
        logger.error(f"Google Calendar API rate limit/timeout updating event {event_id}: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        raise
    except HttpError as err:
        logger.error(f"Google Calendar API Error updating event {event_id}: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        if _is_rate_limit_error(err):
            raise GoogleCalendarRateLimitError(
                "Google Calendar API rate limit exceeded (429). The interview could not be updated. Please try again later."
            ) from err
        return None
    except Exception as err:
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        if _is_timeout_error(err):
            raise GoogleCalendarTimeoutError(
                "Google Calendar API request timed out. The interview could not be updated. Please try again later."
            ) from err
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
        def _do_delete():
            return service.events().delete(
                calendarId=calendar_id or 'primary',
                eventId=event_id,
            ).execute()

        execute_with_retry(_do_delete, max_retries=3, initial_delay=0.05, operation_name="delete_real_google_event")
        redis_tx_manager.commit_transaction_sync(tx_id, {"deleted": True})
        _sync_del_pattern(f"google_cal:events:{_cred_hash(credentials_json)}")
        return True
    except HttpError as err:
        status = getattr(getattr(err, "resp", None), "status", None)
        if status == 404:
            # Event already deleted or not found
            redis_tx_manager.commit_transaction_sync(tx_id, {"deleted": True, "already_gone": True})
            return True
        logger.error(f"Google Calendar API Error deleting event: {err}")
        redis_tx_manager.fail_transaction_sync(tx_id, str(err))
        return False
    except Exception as err:
        logger.error(f"Error deleting event {event_id}: {err}")
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
            "timeZone": "Asia/Manila",
            "items": [{"id": e} for e in emails],
        }
        result = service.freebusy().query(body=body).execute()
        cal_data = result.get('calendars', {})
        _sync_set_cache(cache_key, cal_data, ttl=120)
        return cal_data
    except HttpError as err:
        logger.error(f"Google Calendar API Error querying freebusy: {err}")
        return None


import sys
google_calendar_service = sys.modules[__name__]
