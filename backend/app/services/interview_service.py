from fastapi.logger import logger
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from twilio.rest import Client as TwilioClient

from app.schemas.interview_schema import (
    CandidateRescheduleSchema,
    InterviewCreateSchema,
    InterviewUpdateSchema,
)
from app.repositories.interview_repository import InterviewRepository
from app.services.google_calendar_service import (
    create_real_google_event,
    update_real_google_event,
    delete_real_google_event,
    query_freebusy,
    get_real_google_events,
    GoogleCalendarRateLimitError,
    GoogleCalendarTimeoutError,
    _is_rate_limit_error,
    _is_timeout_error,
)
from app.services import email_service

def _populate_candidate_info(interview, app_override=None, interviewer_override=None):
    """Helper to attach candidate details and interviewer info to the interview model."""
    app = interview.__dict__.get("job_application") if hasattr(interview, "__dict__") else None
    if app is None:
        app = app_override
    if app is None:
        try:
            app = getattr(interview, "job_application", None)
        except Exception:
            app = None
    if app:
        setattr(interview, "candidate_name", getattr(app, "candidate_name", None))
        setattr(interview, "candidate_email", getattr(app, "candidate_email", None))
        setattr(interview, "candidate_phone", getattr(app, "phone", None))
        real_job_title = None
        try:
            app_dict = getattr(app, "__dict__", {})
            if "job" in app_dict and app_dict["job"] is not None:
                real_job_title = getattr(app_dict["job"], "job_title", None)
            elif hasattr(app, "job"):
                try:
                    if app.job:
                        real_job_title = getattr(app.job, "job_title", None)
                except Exception:
                    pass
        except Exception:
            pass
        if not real_job_title:
            real_job_title = getattr(app, "job_title", None)
        setattr(interview, "job_title", real_job_title)
        setattr(interview, "job_id", getattr(app, "job_id", None) or getattr(app, "job_description_id", None))

    interviewer = interview.__dict__.get("interviewer") if hasattr(interview, "__dict__") else None
    if interviewer is None:
        interviewer = interviewer_override
    if interviewer is None:
        try:
            interviewer = getattr(interview, "interviewer", None)
        except Exception:
            interviewer = None
    if interviewer:
        setattr(interview, "interviewer_id", interviewer.id)
        setattr(interview, "interviewer_name", interviewer.fullname)
        setattr(interview, "interviewer_email", interviewer.email)
    elif getattr(interview, "interviewer_id", None):
        setattr(interview, "interviewer_id", interview.interviewer_id)
        setattr(interview, "interviewer_name", None)
        setattr(interview, "interviewer_email", None)
    else:
        setattr(interview, "interviewer_id", None)
        setattr(interview, "interviewer_name", None)
        setattr(interview, "interviewer_email", None)
    setattr(interview, "meeting_link", None)
    # Ensure AI Voice notification fields are attached safely
    if not hasattr(interview, "call_status") or interview.call_status is None:
        setattr(interview, "call_status", "PENDING")
    if not hasattr(interview, "call_attempts") or interview.call_attempts is None:
        setattr(interview, "call_attempts", 0)
    if not hasattr(interview, "sms_backup_sent") or interview.sms_backup_sent is None:
        setattr(interview, "sms_backup_sent", False)
    if not hasattr(interview, "call_language") or interview.call_language is None:
        setattr(interview, "call_language", "bilingual")

    end_dt = getattr(interview, "end_time", None) or getattr(interview, "start_time", None)
    status_upper = (getattr(interview, "status", "") or "").upper()
    is_missed = bool(
        status_upper in {"MISSED", "NO_SHOW"}
        or (
            end_dt is not None
            and end_dt.replace(tzinfo=None) < datetime.now()
            and status_upper not in INACTIVE_INTERVIEW_STATUSES
        )
    )
    setattr(interview, "is_missed", is_missed)
    return interview

def send_sms_notification_sync(to_phone: str, message: str):
    provider = os.getenv('AI_CALLER_PROVIDER', 'twilio').lower()
    
    # Priority 1: DIY ADB Provider via connected Android phone (SIM 09771331871)
    if provider == 'adb':
        try:
            from app.services.ai_caller_service import get_connected_adb_device, trigger_adb_sms
            device = get_connected_adb_device()
            if device and to_phone:
                sent = trigger_adb_sms(to_phone, message, device)
                if sent:
                    return True
        except Exception as e:
            print(f"DIY ADB SMS Error: {e}")

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_phone = os.getenv('TWILIO_PHONE_NUMBER', os.getenv('AI_CALLER_PHONE_NUMBER', '09771331871'))
    
    if account_sid and auth_token and from_phone and to_phone:
        try:
            client = TwilioClient(account_sid, auth_token)
            client.messages.create(
                body=message,
                from_=from_phone,
                to=to_phone
            )
            return True
        except Exception as e:
            print(f"Twilio SMS Error: {e}")

    # Fallback to DIY ADB if Twilio failed or wasn't configured
    if provider != 'adb':
        try:
            from app.services.ai_caller_service import get_connected_adb_device, trigger_adb_sms
            device = get_connected_adb_device()
            if device and to_phone:
                return trigger_adb_sms(to_phone, message, device)
        except Exception as e:
            print(f"DIY ADB SMS Error: {e}")

    return False



def _get_valid_credentials(user) -> Optional[str]:
    """
    Return valid google_credentials JSON string.
    If the access token has expired and a refresh_token is present,
    automatically refreshes the token with Google so the calendar stays continuously connected.
    """
    if not user or not getattr(user, "google_credentials", None):
        return None
    try:
        import json
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from app.utils.google_auth import CALENDAR_SCOPES

        creds_data = json.loads(user.google_credentials) if isinstance(user.google_credentials, str) else user.google_credentials
        if not isinstance(creds_data, dict):
            return None

        try:
            creds = Credentials.from_authorized_user_info(creds_data, CALENDAR_SCOPES)
        except Exception:
            token = creds_data.get("token") or creds_data.get("access_token")
            if token:
                creds = Credentials(
                    token=token,
                    refresh_token=creds_data.get("refresh_token"),
                    token_uri=creds_data.get("token_uri"),
                    client_id=creds_data.get("client_id"),
                    client_secret=creds_data.get("client_secret"),
                    scopes=CALENDAR_SCOPES
                )
            else:
                return None
        if not creds:
            return None

        # Auto-refresh expired access token if refresh_token is present
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                user.google_credentials = creds.to_json()
                user.google_access_token = creds.token
                user.google_token_expiry = creds.expiry
                return user.google_credentials
            except Exception as ref_err:
                logger.warning(f"Could not auto-refresh Google credentials: {ref_err}")
                return None

        if creds.valid:
            return user.google_credentials

        return None
    except Exception as e:
        logger.error(f"Error checking credentials: {e}")
        return None


# ── Working-hours constants ────────────────────────────────────────
WORK_START_HOUR = 9   # 9:00 AM
WORK_END_HOUR = 17    # 5:00 PM
BREAK_START_HOUR = 12 # 12:00 PM
BREAK_END_HOUR = 13   # 1:00 PM
# Monday=0 … Friday=4  (Python weekday convention)
WORK_DAYS = {0, 1, 2, 3, 4}
INACTIVE_INTERVIEW_STATUSES = {"CANCELED", "CANCELLED", "COMPLETED", "REJECTED", "NO_SHOW", "MISSED"}


class AvailableSlotsList(list):
    def __init__(self, *args, message=None, alternative_dates=None, alternative_slots=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message or ""
        self.alternative_dates = alternative_dates or []
        self.alternative_slots = alternative_slots or []


async def get_available_slots(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    user_id: Optional[Union[int, List[int]]] = None,
    manager_id: Optional[int] = None,
    user_ids: Optional[List[int]] = None,
):
    """
    Finds available 1-hour time slots that satisfy ALL of the following:
      • Falls on a weekday (Monday – Friday).
      • Falls within HR working hours (9:00 AM – 5:00 PM).
      • Not marked busy on any participant's Google Calendar (freebusy for HR, Manager, Panelists).
      • Not occupied by an existing (non-canceled) interview in the DB for any participant.
      • Mutually free for all requested participants (HR and Manager).
    """
    from app.repositories.auth_repository import AuthRepository

    # Normalize user/interviewer IDs (HR, manager, panelists)
    target_ids = []
    if user_ids:
        target_ids.extend(user_ids)
    if isinstance(user_id, (list, tuple, set)):
        target_ids.extend(user_id)
    elif user_id is not None:
        target_ids.append(user_id)
    if manager_id is not None and manager_id not in target_ids:
        target_ids.append(manager_id)

    target_ids = list(dict.fromkeys([int(uid) for uid in target_ids if uid is not None]))

    # Strip timezone info so all comparisons are naive (local time)
    start_date = start_date.replace(tzinfo=None)
    end_date = end_date.replace(tzinfo=None)

    # Pin the loop to the working-hours window for the requested day(s)
    loop_start = start_date.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
    loop_end = end_date.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)

    # ── Fetch Google Calendar busy periods for all participants ──
    google_busy: List[tuple] = []
    for uid in target_ids:
        user = await AuthRepository.get_user_by_id_fresh(db, uid)
        credentials_json = _get_valid_credentials(user)
        if credentials_json:
            calendars = await asyncio.to_thread(
                query_freebusy,
                credentials_json,
                ["primary"],
                loop_start.isoformat() + 'Z',
                loop_end.isoformat() + 'Z',
            )
            if calendars:
                for _email, data in calendars.items():
                    for busy in data.get('busy', []):
                        busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00')).replace(tzinfo=None)
                        busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00')).replace(tzinfo=None)
                        google_busy.append((busy_start, busy_end))

    # ── Fetch existing DB interviews in the range for these interviewers ─
    db_interviews = await InterviewRepository.get_interviews_in_range(
        db, loop_start, loop_end, interviewer_id=target_ids if target_ids else None
    )
    db_busy: List[tuple] = [(iv.start_time, iv.end_time) for iv in db_interviews]

    # Merge both busy lists
    all_busy = google_busy + db_busy

    # ── Generate candidate slots & filter ────────────────────────
    slots = []
    current_time = loop_start
    while current_time < loop_end:
        slot_end = current_time + timedelta(hours=1)

        # Skip weekends
        if current_time.weekday() not in WORK_DAYS:
            next_day = current_time + timedelta(days=1)
            current_time = next_day.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
            continue

        # Skip if slot starts before working hours
        if current_time.hour < WORK_START_HOUR:
            current_time = current_time.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
            continue

        # Skip if slot overlaps with break time (12:00 PM - 1:00 PM)
        break_start = current_time.replace(hour=BREAK_START_HOUR, minute=0, second=0, microsecond=0)
        break_end = current_time.replace(hour=BREAK_END_HOUR, minute=0, second=0, microsecond=0)
        if current_time < break_end and slot_end > break_start:
            current_time = break_end
            continue

        # If slot_end exceeds working hours boundary for the day, move to next day
        day_end = current_time.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)
        if slot_end > day_end:
            next_day = current_time + timedelta(days=1)
            current_time = next_day.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
            continue

        # Check against all busy intervals (Google Calendar + DB interviews)
        is_free = True
        for busy_start, busy_end in all_busy:
            if current_time < busy_end and slot_end > busy_start:
                is_free = False
                break

        if is_free:
            slots.append({
                "start_time": current_time,
                "end_time": slot_end
            })

        current_time += timedelta(minutes=30)  # 30-min step for overlapping slot options

    message = None
    alternative_dates = []
    alternative_slots = []

    if not slots:
        # Check upcoming weekdays for alternative dates with available slots
        alt_check_date = loop_end.date() + timedelta(days=1)
        days_checked = 0

        while len(alternative_dates) < 3 and days_checked < 10:
            if alt_check_date.weekday() in WORK_DAYS:
                alt_start = datetime.combine(alt_check_date, datetime.min.time()).replace(hour=WORK_START_HOUR, minute=0, second=0)
                alt_end = datetime.combine(alt_check_date, datetime.min.time()).replace(hour=WORK_END_HOUR, minute=0, second=0)

                # Fetch busy intervals for this alternative day
                alt_google_busy = []
                for uid in target_ids:
                    u = await AuthRepository.get_user_by_id_fresh(db, uid)
                    creds = _get_valid_credentials(u)
                    if creds:
                        cals = await asyncio.to_thread(
                            query_freebusy,
                            creds,
                            ["primary"],
                            alt_start.isoformat() + 'Z',
                            alt_end.isoformat() + 'Z',
                        )
                        if cals:
                            for _em, cdata in cals.items():
                                for b in cdata.get('busy', []):
                                    b_s = datetime.fromisoformat(b['start'].replace('Z', '+00:00')).replace(tzinfo=None)
                                    b_e = datetime.fromisoformat(b['end'].replace('Z', '+00:00')).replace(tzinfo=None)
                                    alt_google_busy.append((b_s, b_e))

                alt_db_ivs = await InterviewRepository.get_interviews_in_range(
                    db, alt_start, alt_end, interviewer_id=target_ids if target_ids else None
                )
                alt_db_busy = [(iv.start_time, iv.end_time) for iv in alt_db_ivs]
                alt_all_busy = alt_google_busy + alt_db_busy

                # Scan slots on this alternative day
                day_slots = []
                curr = alt_start
                while curr < alt_end:
                    s_end = curr + timedelta(hours=1)
                    if s_end.hour > WORK_END_HOUR or (s_end.hour == WORK_END_HOUR and s_end.minute > 0):
                        break

                    b_start = curr.replace(hour=BREAK_START_HOUR, minute=0, second=0)
                    b_end = curr.replace(hour=BREAK_END_HOUR, minute=0, second=0)
                    if curr < b_end and s_end > b_start:
                        curr = b_end
                        continue

                    free = True
                    for bs, be in alt_all_busy:
                        if curr < be and s_end > bs:
                            free = False
                            break

                    if free:
                        day_slots.append({"start_time": curr, "end_time": s_end})
                    curr += timedelta(minutes=30)

                if day_slots:
                    date_str = alt_check_date.isoformat()
                    alternative_dates.append(date_str)
                    alternative_slots.extend(day_slots[:2])

            alt_check_date += timedelta(days=1)
            days_checked += 1

        req_date_str = start_date.strftime("%Y-%m-%d")
        if alternative_dates:
            formatted_alts = ", ".join([datetime.fromisoformat(d).strftime("%A, %b %d, %Y") for d in alternative_dates])
            message = f"The requested date ({req_date_str}) is fully booked. Recommended alternative dates with available slots: {formatted_alts}."
        else:
            message = f"The requested date ({req_date_str}) is fully booked. Please select an alternative date or schedule with another interviewer."

    return AvailableSlotsList(slots, message=message, alternative_dates=alternative_dates, alternative_slots=alternative_slots)


_scheduling_lock: Optional[asyncio.Lock] = None
_scheduling_lock_loop = None


def _get_scheduling_lock() -> asyncio.Lock:
    global _scheduling_lock, _scheduling_lock_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _scheduling_lock is None or _scheduling_lock_loop != current_loop:
        _scheduling_lock = asyncio.Lock()
        _scheduling_lock_loop = current_loop
    return _scheduling_lock


async def schedule_interview(db: AsyncSession, data: InterviewCreateSchema, user_id: int):
    async with _get_scheduling_lock():
        # 1. Fetch Candidate
        application = await InterviewRepository.get_job_application(db, data.job_application_id)
        if not application:
            raise ValueError("Application not found")

        # ── Application & Candidate Conflict Checks (REQ084 & REQ085) ──────
        # Check whether an active interview already exists for this specific application
        existing_for_app = await InterviewRepository.get_interviews_for_application(db, data.job_application_id)
        active_for_app = [iv for iv in existing_for_app if (iv.status or "").upper() not in INACTIVE_INTERVIEW_STATUSES]
        if active_for_app:
            existing_iv = active_for_app[0]
            raise ValueError(
                f"An active interview is already scheduled for this application (Interview ID: {existing_iv.id})."
            )

        # REQ084: Enforce scheduling conflict detection to prevent overlapping interviews across applications
        req_start = data.start_time.replace(tzinfo=None) if data.start_time.tzinfo else data.start_time
        req_end = data.end_time.replace(tzinfo=None) if data.end_time.tzinfo else data.end_time

        if application.candidate_email:
            cand_all_ivs = await InterviewRepository.get_interviews_for_candidate(db, application.candidate_email)
            for iv in cand_all_ivs:
                if (iv.status or "").upper() not in INACTIVE_INTERVIEW_STATUSES:
                    iv_start = iv.start_time.replace(tzinfo=None) if iv.start_time and iv.start_time.tzinfo else iv.start_time
                    iv_end = iv.end_time.replace(tzinfo=None) if iv.end_time and iv.end_time.tzinfo else iv.end_time
                    if iv_start and iv_end and (req_start < iv_end and req_end > iv_start):
                        raise ValueError(
                            f"Scheduling conflict (REQ084): Candidate already has an interview scheduled that overlaps with this time slot ({iv_start.strftime('%b %d, %Y %I:%M %p')} - {iv_end.strftime('%I:%M %p')})."
                        )

        # Target interviewer: if specified, use that HR account, else fallback to current user_id
        interviewer_id = data.interviewer_id if data.interviewer_id else user_id

        from app.repositories.auth_repository import AuthRepository
        scheduler_user = await AuthRepository.get_user_by_id_fresh(db, user_id)
        interviewer_user = await AuthRepository.get_user_by_id_fresh(db, interviewer_id) if interviewer_id != user_id else scheduler_user
        user = interviewer_user or scheduler_user
        interviewer_name = getattr(interviewer_user, "fullname", None) or "Mariwasa HR Panel"
        scheduler_email = getattr(scheduler_user, "email", None) if scheduler_user else None
        candidate_email = getattr(application, "candidate_email", None)
        candidate_name = getattr(application, "candidate_name", None) or "Candidate"
        candidate_phone = getattr(application, "phone", None)
        credentials_json = _get_valid_credentials(user) or _get_valid_credentials(scheduler_user)

        # Collect distinct panel recipients (assigned interviewer / additional panelists)
        panel_recipients = []
        if interviewer_user and getattr(interviewer_user, "email", None):
            if not scheduler_user or interviewer_user.email != scheduler_user.email:
                panel_recipients.append(interviewer_user)

        if getattr(data, "panelist_ids", None):
            for pid in data.panelist_ids:
                p_user = await AuthRepository.get_user_by_id_fresh(db, pid)
                if p_user and getattr(p_user, "email", None):
                    if p_user.email not in [pr.email for pr in panel_recipients] and (not scheduler_user or p_user.email != scheduler_user.email):
                        panel_recipients.append(p_user)

        # Resolve real target position title safely without triggering lazy-load on detached instance
        job_name = None
        try:
            app_dict = getattr(application, "__dict__", {})
            if "job" in app_dict and app_dict["job"] is not None:
                job_name = getattr(app_dict["job"], "job_title", None)
        except Exception:
            pass

        if not job_name and getattr(application, "job_id", None):
            from app.repositories.job_description_repository import JobDescriptionRepository
            try:
                job_desc = await JobDescriptionRepository.get_by_id(db, application.job_id)
                if job_desc and getattr(job_desc, "job_title", None):
                    job_name = job_desc.job_title
            except Exception:
                pass

        if not job_name:
            job_name = getattr(application, "job_title", None) or "Job Position"

        # 2. Create Interview Record
        start = data.start_time.replace(tzinfo=None)
        end = data.end_time.replace(tzinfo=None)

        # Break time check (12:00 PM – 1:00 PM)
        break_start = start.replace(hour=BREAK_START_HOUR, minute=0, second=0, microsecond=0)
        break_end = start.replace(hour=BREAK_END_HOUR, minute=0, second=0, microsecond=0)
        if start < break_end and end > break_start:
            raise ValueError("Interviews cannot be scheduled during break time (12:00 PM – 1:00 PM).")

        # Double-booking check: verify interviewer is not already booked in this slot
        conflicts = await InterviewRepository.get_interviews_in_range(db, start, end, interviewer_id=interviewer_id)
        if conflicts:
            raise ValueError("The selected time slot conflicts with an existing interview for this HR panelist. Please choose another slot.")

        interview_data = {
            "job_application_id": data.job_application_id,
            "interviewer_id": interviewer_id,
            "title": data.title,
            "description": data.description,
            "start_time": start,
            "end_time": end
        }
        if hasattr(data, "call_language") and data.call_language:
            interview_data["call_language"] = data.call_language
        interview = await InterviewRepository.create_interview(db, interview_data)
        await InterviewRepository.commit_changes(db)

        # Automatically update candidate application status to Interview Scheduled upon booking (Item 1b)
        current_app_status = (getattr(application, "status", None) or "PENDING").upper()
        try:
            from app.services.status_management_service import apply_application_status_change, normalize_status
            from app.models.shortlist_roster import ShortlistRosterItem
            from sqlalchemy import select

            current_norm = normalize_status(application.status)
            if current_norm != "Interview Scheduled":
                await apply_application_status_change(
                    db=db,
                    application=application,
                    new_status="Interview Scheduled",
                    changed_by=getattr(scheduler_user, "email", "HR") if scheduler_user else "HR",
                    change_type="auto",
                    reason=f"auto: interview scheduled for {data.title}",
                    send_email=True
                )

            # Sync with any shortlist roster items for this application
            roster_items_stmt = select(ShortlistRosterItem).where(ShortlistRosterItem.application_id == application.id)
            roster_items_res = await db.execute(roster_items_stmt)
            for r_item in roster_items_res.scalars().all():
                r_item.stage = "Interview Scheduled"
                r_item.updated_at = datetime.utcnow()
            await db.commit()

            await InterviewRepository.add_interview_log(
                db, interview.id, "STATUS_UPDATE", f"Candidate application status automatically updated from {current_app_status} to Interview Scheduled upon scheduling"
            )
            await InterviewRepository.commit_changes(db)
        except Exception as e_status:
            logger.error(f"Error updating application status to Interview Scheduled: {e_status}")

        # 3. Create Google Calendar Event via centralized service if credentials exist
        attendees = []
        if application.candidate_email:
            attendees.append({"email": application.candidate_email})

        # Add HR scheduler to Google Calendar attendees
        if scheduler_user and getattr(scheduler_user, "email", None):
            if scheduler_user.email not in [a["email"] for a in attendees]:
                attendees.append({"email": scheduler_user.email})

        # Add Panelists to Google Calendar attendees
        for p_user in panel_recipients:
            if p_user.email not in [a["email"] for a in attendees]:
                attendees.append({"email": p_user.email})

        if credentials_json:
            try:
                event = await asyncio.to_thread(
                    create_real_google_event,
                    credentials_json,
                    calendar_id='primary',
                    summary=data.title,
                    start_dt=data.start_time.isoformat(),
                    end_dt=data.end_time.isoformat(),
                    description=data.description or '',
                    location='',
                    is_all_day=False,
                    attendees=attendees,
                    create_meet_link=False,
                    interview_id=interview.id,
                )

                if event:
                    interview.google_event_id = event.get('id')
                    interview.meeting_link = None
                    await InterviewRepository.commit_changes(db)
                else:
                    interview.meeting_link = None
                    await InterviewRepository.commit_changes(db)
            except (GoogleCalendarRateLimitError, GoogleCalendarTimeoutError) as e_cal:
                try:
                    await InterviewRepository.delete_interview(db, interview)
                    application.status = current_app_status
                    await db.commit()
                except Exception as comp_err:
                    logger.error(f"Compensation cleanup error: {comp_err}")
                logger.error(f"Google Calendar API rate limit/timeout: {e_cal}. Rolled back interview {interview.id} (no partial booking).")
                raise ValueError(str(e_cal))
            except Exception as e:
                is_429 = _is_rate_limit_error(e)
                is_timeout = _is_timeout_error(e)
                if is_429 or is_timeout:
                    try:
                        await InterviewRepository.delete_interview(db, interview)
                        application.status = current_app_status
                        await db.commit()
                    except Exception as comp_err:
                        logger.error(f"Compensation cleanup error: {comp_err}")
                    msg = (
                        "Google Calendar API rate limit exceeded (429). The interview could not be scheduled. No booking was created. Please try again later."
                        if is_429
                        else "Google Calendar API request timed out. The interview could not be scheduled. No booking was created. Please try again later."
                    )
                    logger.error(f"{msg} Detail: {e}. Rolled back interview {interview.id} (no partial booking).")
                    raise ValueError(msg)
                print(f"Warning: Could not create event on Google Calendar: {e}")
                interview.meeting_link = None
                await InterviewRepository.commit_changes(db)
        else:
            interview.meeting_link = None
            await InterviewRepository.commit_changes(db)

        # 4. Email Invites: Candidate, HR, and Panel
        # (a) Candidate Invite
        if candidate_email:
            try:
                email_sent = await email_service.send_interview_invitation_email(
                    to_email=candidate_email,
                    candidate_name=candidate_name,
                    job_title=job_name,
                    interview_title=data.title,
                    start_time=data.start_time,
                    end_time=data.end_time,
                    interviewer_name=interviewer_name,
                    notes=data.description or ""
                )
                if email_sent:
                    try:
                        await InterviewRepository.add_interview_log(
                            db, interview.id, "EMAIL_SENT", f"Interview invitation email sent to candidate {candidate_email}"
                        )
                        await InterviewRepository.commit_changes(db)
                    except Exception as log_err:
                        await db.rollback()
                        logger.warning(f"Could not persist candidate email log: {log_err}")
            except Exception as e:
                print(f"Warning: Could not send interview invitation email to candidate: {e}")

        # (b) HR Confirmation Invite
        if scheduler_email:
            try:
                email_sent = await email_service.send_interview_invitation_email(
                    to_email=scheduler_email,
                    candidate_name=candidate_name,
                    job_title=job_name,
                    interview_title=f"[HR Confirmation] {data.title}",
                    start_time=data.start_time,
                    end_time=data.end_time,
                    interviewer_name=interviewer_name,
                    notes=f"HR Copy - Scheduled interview for candidate {candidate_name} ({candidate_email or 'N/A'}). Assigned Panelist: {interviewer_name}. Notes: {data.description or 'N/A'}"
                )
                if email_sent:
                    try:
                        await InterviewRepository.add_interview_log(
                            db, interview.id, "EMAIL_SENT", f"Interview confirmation email sent to HR {scheduler_email}"
                        )
                        await InterviewRepository.commit_changes(db)
                    except Exception as log_err:
                        await db.rollback()
                        logger.warning(f"Could not persist HR email log: {log_err}")
            except Exception as e:
                print(f"Warning: Could not send interview confirmation email to HR: {e}")

        # (c) Panel Invite(s)
        for p_user in panel_recipients:
            try:
                p_email = getattr(p_user, "email", None)
                p_name = getattr(p_user, "fullname", None) or "Panelist"
                if p_email:
                    email_sent = await email_service.send_interview_invitation_email(
                        to_email=p_email,
                        candidate_name=candidate_name,
                        job_title=job_name,
                        interview_title=f"[Panel Invite] {data.title}",
                        start_time=data.start_time,
                        end_time=data.end_time,
                        interviewer_name=p_name,
                        notes=f"Panel Interview Assignment - Candidate: {candidate_name} ({candidate_email or 'N/A'}). Job: {job_name}. Notes: {data.description or 'N/A'}"
                    )
                    if email_sent:
                        try:
                            await InterviewRepository.add_interview_log(
                                db, interview.id, "EMAIL_SENT", f"Interview panelist invitation email sent to {p_email}"
                            )
                            await InterviewRepository.commit_changes(db)
                        except Exception as log_err:
                            await db.rollback()
                            logger.warning(f"Could not persist panel email log: {log_err}")
            except Exception as e:
                print(f"Warning: Could not send interview invitation email to panelist: {e}")

        # 5. Send SMS Notification (if phone configured)
        if candidate_phone:
            from app.services.ai_caller_service import format_to_e164
            formatted_phone = format_to_e164(candidate_phone) or candidate_phone
            sched_time_str = data.start_time.strftime('%A, %b %d, %Y at %I:%M %p')
            message = (
                f"Mariwasa HR: Magandang araw, {candidate_name}! Nais naming ipaalam na scheduled na ang "
                f"iyong interview para sa posisyong {job_name} sa {sched_time_str}. Kindly check your email ({candidate_email}) "
                f"para sa meeting link at complete interview details. Maraming salamat and see you!"
            )
            await asyncio.to_thread(send_sms_notification_sync, formatted_phone, message)
            try:
                await InterviewRepository.add_interview_log(
                    db,
                    interview.id,
                    "SMS_SENT",
                    f"SMS interview notification delivered to {formatted_phone}: {message}"
                )
                await InterviewRepository.commit_changes(db)
            except Exception as log_err:
                await db.rollback()
                logger.warning(f"Could not persist SMS log: {log_err}")

        # 6. In-App Notifications
        try:
            from app.services.notification_service import create_notification
            time_str = data.start_time.strftime('%b %d, %Y at %I:%M %p')

            # Dedicated notification for Candidate
            if candidate_email:
                await create_notification(
                    db=db,
                    title="Interview Scheduled 📅",
                    message=f"Your interview for {job_name} has been scheduled on {time_str}.",
                    type="schedule",
                    target_role="CANDIDATE",
                    target_email=candidate_email,
                    sender_role="HR"
                )

            # Operational alert for HR
            await create_notification(
                db=db,
                title="Interview Scheduled",
                message=f"Interview with {candidate_name} for {job_name} scheduled on {time_str}.",
                type="schedule",
                target_role="HR",
                target_email=scheduler_email,
                sender_role="HR"
            )

            # Operational alert for Panelists
            for p_user in panel_recipients:
                p_em = getattr(p_user, "email", None)
                if p_em:
                    await create_notification(
                        db=db,
                        title="Panel Interview Assignment 📅",
                        message=f"You have been assigned as panelist for {candidate_name}'s interview for {job_name} on {time_str}.",
                        type="schedule",
                        target_role="HR",
                        target_email=p_em,
                        sender_role="HR"
                    )
        except Exception as e_notif:
            print(f"Warning: Could not create interview notification: {e_notif}")

        # 7. REQ028: Automatically place voice calls to candidates after interview scheduling
        if candidate_phone:
            try:
                from app.tasks import initiate_interview_call_task
                initiate_interview_call_task.delay(interview.id)
                try:
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "VOICE_CALL_QUEUED", f"Automated AI voice call queued for candidate phone {candidate_phone}"
                    )
                    await InterviewRepository.commit_changes(db)
                except Exception as log_err:
                    await db.rollback()
                    logger.warning(f"Could not persist voice call log: {log_err}")
            except Exception as e_voice:
                logger.warning(f"Celery dispatch notice for interview voice call: {e_voice}. Falling back to background async...")
                try:
                    from app.services.ai_caller_service import initiate_candidate_interview_call
                    asyncio.create_task(initiate_candidate_interview_call(interview.id))
                except Exception as e_direct:
                    logger.error(f"Error queueing automated voice call: {e_direct}")

        # Attach candidate and interviewer attributes for Pydantic response
        fresh_interview = await InterviewRepository.get_interview_by_id(db, interview.id)
        if fresh_interview:
            interview = fresh_interview
        _populate_candidate_info(interview, app_override=application, interviewer_override=user)
        return interview


async def _validate_interview_time_slot(
    db: AsyncSession,
    interview,
    start: datetime,
    end: datetime,
    interviewer_id: Optional[int],
):
    """Validate weekday, working hours, break window, interviewer conflicts, and candidate conflicts."""
    if start >= end:
        raise ValueError("End time must be after start time.")
    if start.weekday() > 4:
        raise ValueError("Interviews can only be scheduled on weekdays (Monday – Friday).")
    if start.hour < WORK_START_HOUR or end.hour > WORK_END_HOUR or (end.hour == WORK_END_HOUR and end.minute > 0):
        raise ValueError("Interviews must be scheduled within working hours (9:00 AM – 5:00 PM).")

    break_start = start.replace(hour=BREAK_START_HOUR, minute=0, second=0, microsecond=0)
    break_end = start.replace(hour=BREAK_END_HOUR, minute=0, second=0, microsecond=0)
    if start < break_end and end > break_start:
        raise ValueError("Interviews cannot be scheduled during break time (12:00 PM – 1:00 PM).")

    conflicts = await InterviewRepository.get_interviews_in_range_excluding(
        db, start, end, interview.id, interviewer_id=interviewer_id
    )
    if conflicts:
        raise ValueError("The selected time slot conflicts with an existing interview.")

    if interview.job_application_id:
        cand_interviews = await InterviewRepository.get_interviews_for_application(db, interview.job_application_id)
        cand_conflict = [
            iv for iv in cand_interviews
            if iv.id != interview.id
            and (iv.status or "").upper() not in INACTIVE_INTERVIEW_STATUSES
            and iv.start_time < end and iv.end_time > start
        ]
        if cand_conflict:
            raise ValueError("This candidate already has another interview scheduled at the selected time.")


async def update_interview(db: AsyncSession, interview_id: int, data: InterviewUpdateSchema, user_id: int, user_role: Optional[str] = None):
    """
    Modify/reschedule an interview and synchronize the update directly with Google Calendar.
    """
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    # Ownership Verification
    is_admin = user_role in ["ADMIN", "SUPERADMIN"] if user_role else False
    is_owner = not interview.interviewer_id or interview.interviewer_id == user_id
    if not is_owner and not is_admin:
        raise PermissionError("You do not have permission to modify this interview. Only the assigned HR interviewer or an administrator can make changes.")

    time_changed = False
    if data.start_time is not None or data.end_time is not None:
        start = (data.start_time or interview.start_time).replace(tzinfo=None)
        end = (data.end_time or interview.end_time).replace(tzinfo=None)
        interviewer_to_check = data.interviewer_id or interview.interviewer_id or user_id
        await _validate_interview_time_slot(db, interview, start, end, interviewer_to_check)

        if start != interview.start_time or end != interview.end_time:
            time_changed = True
        interview.start_time = start
        interview.end_time = end

    if data.title is not None:
        interview.title = data.title
    if data.description is not None:
        interview.description = data.description
    if data.interviewer_id is not None:
        interview.interviewer_id = data.interviewer_id
    if hasattr(data, "call_language") and data.call_language is not None:
        interview.call_language = data.call_language
    if data.status is not None:
        old_status = interview.status
        interview.status = data.status
        if old_status != data.status:
            await InterviewRepository.add_interview_log(db, interview.id, "STATUS_CHANGE", f"Status changed to {data.status}")

    # If cancelling without rescheduling to a new slot, trigger full cancellation workflow
    if data.status == "CANCELED" and not time_changed:
        await InterviewRepository.update_interview(db, interview)
        return await cancel_interview(db, interview.id, user_id=user_id, user_role=user_role, reason=data.description)

    await InterviewRepository.add_interview_log(db, interview.id, "UPDATED", "Interview details modified")
    interview = await InterviewRepository.update_interview(db, interview)

    # Synchronize modification to Google Calendar if linked
    from app.repositories.auth_repository import AuthRepository
    scheduler_user = await AuthRepository.get_user_by_id_fresh(db, user_id)
    interviewer_to_sync = interview.interviewer_id or user_id
    user = await AuthRepository.get_user_by_id_fresh(db, interviewer_to_sync)
    credentials_json = _get_valid_credentials(user)
    if not credentials_json and interviewer_to_sync != user_id:
        user_fallback = await AuthRepository.get_user_by_id_fresh(db, user_id)
        credentials_json = _get_valid_credentials(user_fallback)
    if not credentials_json and scheduler_user:
        credentials_json = _get_valid_credentials(scheduler_user)

    application = await InterviewRepository.get_job_application(db, interview.job_application_id)

    # Collect panel recipients
    panel_recipients = []
    panelist_ids = list(getattr(data, "panelist_ids", None) or [])
    if interview.interviewer_id and interview.interviewer_id not in panelist_ids:
        panelist_ids.append(interview.interviewer_id)

    for pid in panelist_ids:
        p_user = await AuthRepository.get_user_by_id_fresh(db, pid)
        if p_user and getattr(p_user, "email", None):
            if not scheduler_user or p_user.email != getattr(scheduler_user, "email", None):
                panel_recipients.append(p_user)

    if credentials_json:
        if time_changed:
            old_event_id = interview.google_event_id
            if old_event_id:
                try:
                    await asyncio.to_thread(
                        delete_real_google_event,
                        credentials_json=credentials_json,
                        calendar_id="primary",
                        event_id=old_event_id,
                    )
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "CALENDAR_SYNC", f"Removed old Google Calendar event {old_event_id}"
                    )
                except Exception as del_err:
                    print(f"Warning: Could not remove old Google Calendar event {old_event_id}: {del_err}")
                interview.google_event_id = None

            # Create new Google Calendar event for the rescheduled slot with updated attendees
            attendees = []
            if application and getattr(application, "candidate_email", None):
                attendees.append({"email": application.candidate_email})
            if scheduler_user and getattr(scheduler_user, "email", None):
                attendees.append({"email": scheduler_user.email})
            for p_user in panel_recipients:
                if p_user.email not in [a["email"] for a in attendees]:
                    attendees.append({"email": p_user.email})

            try:
                new_event = await asyncio.to_thread(
                    create_real_google_event,
                    credentials_json,
                    calendar_id="primary",
                    summary=interview.title,
                    start_dt=interview.start_time.isoformat(),
                    end_dt=interview.end_time.isoformat(),
                    description=interview.description or "",
                    location="",
                    is_all_day=False,
                    attendees=attendees,
                    create_meet_link=False,
                    interview_id=interview.id,
                )
                if new_event:
                    interview.google_event_id = new_event.get("id")
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "CALENDAR_SYNC", f"Created new Google Calendar event {interview.google_event_id}"
                    )
                    await InterviewRepository.commit_changes(db)
            except Exception as create_err:
                print(f"Warning: Could not create new Google Calendar event: {create_err}")
        elif interview.google_event_id:
            try:
                summary_val = f"[CANCELED] {interview.title}" if interview.status == "CANCELED" else interview.title
                cal_status = "cancelled" if interview.status == "CANCELED" else "confirmed"
                await asyncio.to_thread(
                    update_real_google_event,
                    credentials_json=credentials_json,
                    calendar_id="primary",
                    event_id=interview.google_event_id,
                    summary=summary_val,
                    start_dt=interview.start_time.isoformat(),
                    end_dt=interview.end_time.isoformat(),
                    description=interview.description or "",
                    status=cal_status,
                )
            except Exception as e:
                print(f"Warning: Could not modify Google Calendar event: {e}")

    # If rescheduled time changed, notify candidate, HR, and panel
    if time_changed and application:
        # Resolve real target position title safely without triggering lazy-load on detached instance
        job_name = None
        try:
            app_dict = getattr(application, "__dict__", {})
            if "job" in app_dict and app_dict["job"] is not None:
                job_name = getattr(app_dict["job"], "job_title", None)
        except Exception:
            pass

        if not job_name and getattr(application, "job_id", None):
            from app.repositories.job_description_repository import JobDescriptionRepository
            try:
                job_desc = await JobDescriptionRepository.get_by_id(db, application.job_id)
                if job_desc and getattr(job_desc, "job_title", None):
                    job_name = job_desc.job_title
            except Exception:
                pass

        if not job_name:
            job_name = getattr(application, "job_title", None) or "Job Position"

        interviewer_name = user.fullname if user and getattr(user, 'fullname', None) else "Mariwasa HR Panel"

        # 1. HR Update / Confirmation Email
        if scheduler_user and getattr(scheduler_user, "email", None):
            try:
                email_sent = await email_service.send_interview_rescheduled_email(
                    to_email=scheduler_user.email,
                    candidate_name=application.candidate_name or "Candidate",
                    job_title=job_name,
                    interview_title=f"[HR Update] {interview.title}",
                    start_time=interview.start_time,
                    end_time=interview.end_time,
                    interviewer_name=interviewer_name,
                    notes=f"HR Copy - Rescheduled interview for candidate {application.candidate_name or 'Candidate'} ({application.candidate_email or 'N/A'}). Assigned Interviewer: {interviewer_name}. Notes: {interview.description or 'N/A'}"
                )
                if email_sent:
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "EMAIL_RESCHEDULED", f"Reschedule update email sent to HR {scheduler_user.email}"
                    )
                    await InterviewRepository.commit_changes(db)
            except Exception as e:
                print(f"Warning: Could not send reschedule email to HR: {e}")

        # 2. Panelist Update Email(s)
        for p_user in panel_recipients:
            try:
                email_sent = await email_service.send_interview_rescheduled_email(
                    to_email=p_user.email,
                    candidate_name=application.candidate_name or "Candidate",
                    job_title=job_name,
                    interview_title=f"[Panel Update] {interview.title}",
                    start_time=interview.start_time,
                    end_time=interview.end_time,
                    interviewer_name=p_user.fullname or interviewer_name,
                    notes=f"Panel Interview Rescheduled - Candidate: {application.candidate_name or 'Candidate'} ({application.candidate_email or 'N/A'}). Job: {job_name}. Notes: {interview.description or 'N/A'}"
                )
                if email_sent:
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "EMAIL_RESCHEDULED", f"Reschedule update email sent to panelist {p_user.email}"
                    )
                    await InterviewRepository.commit_changes(db)
            except Exception as e:
                print(f"Warning: Could not send reschedule email to panelist: {e}")

        # 3. Candidate Reschedule Notification Email
        if application.candidate_email:
            try:
                email_sent = await email_service.send_interview_rescheduled_email(
                    to_email=application.candidate_email,
                    candidate_name=application.candidate_name or "Candidate",
                    job_title=job_name,
                    interview_title=interview.title,
                    start_time=interview.start_time,
                    end_time=interview.end_time,
                    interviewer_name=interviewer_name,
                    notes=interview.description or ""
                )
                if email_sent:
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "EMAIL_RESCHEDULED", f"Reschedule notification email sent to {application.candidate_email}"
                    )
                    await InterviewRepository.commit_changes(db)
            except Exception as e:
                print(f"Warning: Could not send reschedule email: {e}")

        # 4. SMS Notification to Candidate
        if application.phone:
            from app.services.ai_caller_service import format_to_e164
            formatted_phone = format_to_e164(application.phone) or application.phone
            sched_time_str = interview.start_time.strftime('%A, %b %d, %Y at %I:%M %p')
            message = (
                f"Mariwasa HR Update: Magandang araw, {application.candidate_name}! Nais naming ipagbigay-alam na na-reschedule ang "
                f"iyong interview para sa posisyong {job_name} sa {sched_time_str}. Pakitingnan ang iyong email ({application.candidate_email}) "
                f"para sa updated calendar invite at complete details. Maraming salamat!"
            )
            await asyncio.to_thread(send_sms_notification_sync, formatted_phone, message)
            try:
                await InterviewRepository.add_interview_log(
                    db,
                    interview.id,
                    "SMS_RESCHEDULED",
                    f"Reschedule SMS notification delivered to {formatted_phone}: {message}"
                )
                await InterviewRepository.commit_changes(db)
            except Exception as log_err:
                await db.rollback()
                logger.warning(f"Could not persist reschedule SMS log: {log_err}")

        # 5. In-App Notifications for Candidate, HR, and Panel
        try:
            from app.services.notification_service import create_notification
            time_str = interview.start_time.strftime('%b %d, %Y at %I:%M %p')

            if application.candidate_email:
                await create_notification(
                    db=db,
                    title="Interview Rescheduled 📅",
                    message=f"Your interview for {job_name} has been rescheduled to {time_str}.",
                    type="schedule",
                    target_role="CANDIDATE",
                    target_email=application.candidate_email,
                    sender_role="HR"
                )

            await create_notification(
                db=db,
                title="Interview Rescheduled",
                message=f"Interview with {application.candidate_name} for {job_name} rescheduled to {time_str}.",
                type="schedule",
                target_role="HR",
                sender_role="HR"
            )

            for p_user in panel_recipients:
                if getattr(p_user, "email", None):
                    await create_notification(
                        db=db,
                        title="Panel Interview Rescheduled 📅",
                        message=f"Panel interview with {application.candidate_name} for {job_name} has been rescheduled to {time_str}.",
                        type="schedule",
                        target_role="PANELIST",
                        target_email=p_user.email,
                        sender_role="HR"
                    )
        except Exception as e_notif:
            print(f"Warning: Could not create interview reschedule notification: {e_notif}")

    _populate_candidate_info(interview, app_override=application, interviewer_override=user)
    return interview


async def delete_interview(db: AsyncSession, interview_id: int, user_id: int, user_role: Optional[str] = None):
    """
    Delete an interview and delete its corresponding event from Google Calendar.
    """
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    # Ownership Verification
    is_admin = user_role in ["ADMIN", "SUPERADMIN"] if user_role else False
    is_owner = not interview.interviewer_id or interview.interviewer_id == user_id
    if not is_owner and not is_admin:
        raise PermissionError("You do not have permission to delete this interview. Only the assigned HR interviewer or an administrator can make changes.")

    from app.repositories.auth_repository import AuthRepository
    interviewer_to_sync = interview.interviewer_id or user_id
    user = await AuthRepository.get_user_by_id_fresh(db, interviewer_to_sync)
    credentials_json = _get_valid_credentials(user)
    if not credentials_json and interviewer_to_sync != user_id:
        user_fallback = await AuthRepository.get_user_by_id_fresh(db, user_id)
        credentials_json = _get_valid_credentials(user_fallback)

    if credentials_json and interview.google_event_id:
        try:
            await asyncio.to_thread(
                delete_real_google_event,
                credentials_json=credentials_json,
                calendar_id="primary",
                event_id=interview.google_event_id,
            )
        except Exception as e:
            print(f"Warning: Could not delete Google Calendar event: {e}")

    await InterviewRepository.delete_interview(db, interview)
    return True


async def get_all_interviews(db: AsyncSession):
    """Fetch all interviews for the scheduling module."""
    interviews = await InterviewRepository.get_all_interviews(db)
    return [_populate_candidate_info(iv) for iv in interviews]


async def get_calendar_feed(db: AsyncSession, user_id: int, time_min: str = None, time_max: str = None, hr_id: Optional[int] = None):
    """
    Unified calendar feed:
      1. Returns all database interviews with candidate information.
      2. If Google Calendar is linked, retrieves events and syncs modifications from Google Calendar back to DB.
      3. Returns non-interview external Google Calendar events so HR has unified visibility.
    """
    from app.repositories.auth_repository import AuthRepository
    sync_user_id = hr_id if hr_id else user_id
    user = await AuthRepository.get_user_by_id_fresh(db, sync_user_id)
    credentials_json = _get_valid_credentials(user)
    if credentials_json and user:
        try:
            await db.commit()
        except Exception:
            pass

    # Fetch DB interviews
    db_interviews = await InterviewRepository.get_all_interviews(db)
    if hr_id:
        db_interviews = [iv for iv in db_interviews if iv.interviewer_id == hr_id]

    interviews_map = {iv.google_event_id: iv for iv in db_interviews if iv.google_event_id}

    google_events = []
    if credentials_json:
        try:
            raw_events = await asyncio.to_thread(
                get_real_google_events,
                credentials_json=credentials_json,
                calendar_id="primary",
                max_results=150,
                time_min=time_min,
                time_max=time_max,
            )
            if raw_events:
                for ev in raw_events:
                    ev_id = ev.get("id")
                    if ev_id in interviews_map:
                        # Match: Check if modified on Google Calendar directly
                        linked_iv = interviews_map[ev_id]
                        g_start_str = ev.get("start_datetime")
                        g_end_str = ev.get("end_datetime")

                        if g_start_str and g_end_str:
                            try:
                                clean_start = g_start_str.replace("Z", "+00:00")
                                clean_end = g_end_str.replace("Z", "+00:00")
                                dt_start = datetime.fromisoformat(clean_start).replace(tzinfo=None)
                                dt_end = datetime.fromisoformat(clean_end).replace(tzinfo=None)

                                has_time_diff = abs((dt_start - linked_iv.start_time).total_seconds()) > 60
                                if has_time_diff:
                                    linked_iv.start_time = dt_start
                                    linked_iv.end_time = dt_end
                                    await InterviewRepository.add_interview_log(
                                        db, linked_iv.id, "GOOGLE_SYNC", f"Synchronized time update from Google Calendar ({dt_start})"
                                    )
                                    await InterviewRepository.commit_changes(db)
                            except Exception as parse_err:
                                print(f"Error parsing date during sync: {parse_err}")
                    else:
                        # External Google Calendar event
                        google_events.append(ev)
        except Exception as e:
            print(f"Warning: Could not fetch Google Calendar events: {e}")

    formatted_interviews = [_populate_candidate_info(iv) for iv in db_interviews]
    return {
        "interviews": formatted_interviews,
        "google_events": google_events,
        "google_connected": bool(credentials_json),
        "google_account": user.email if user and credentials_json else None,
    }


async def get_google_calendar_status(db: AsyncSession, user_id: int):
    from app.repositories.auth_repository import AuthRepository
    user = await AuthRepository.get_user_by_id_fresh(db, user_id)
    if not user or not user.google_credentials:
        return {
            "connected": False,
            "email": None,
            "message": "Google Calendar is not connected. Connect your Google account to sync schedules."
        }
    valid_creds = _get_valid_credentials(user)
    if not valid_creds:
        return {
            "connected": False,
            "email": user.email,
            "expired": True,
            "message": "Google Calendar connection expired or revoked. Please reconnect your account."
        }
    try:
        await db.commit()
    except Exception:
        pass
    return {
        "connected": True,
        "email": user.email,
        "message": "Google Calendar is connected and synchronizing."
    }


async def get_calendar_events(db: AsyncSession, user_id: int):
    from app.repositories.auth_repository import AuthRepository
    user = await AuthRepository.get_user_by_id_fresh(db, user_id)
    credentials_json = _get_valid_credentials(user)
    
    if credentials_json:
        events = await asyncio.to_thread(
            get_real_google_events,
            credentials_json,
            calendar_id="primary",
            max_results=50
        )
        return events or []
    return []


async def cancel_interview(
    db: AsyncSession,
    interview_id: int,
    user_id: int,
    user_role: Optional[str] = None,
    reason: Optional[str] = None,
    panelist_ids: Optional[List[int]] = None
):
    """
    Cancel an interview:
    1. Remove corresponding Google Calendar event from all participant calendars.
    2. Notify participants (candidate, HR interviewer, panel).
    3. Update interview status to CANCELED.
    """
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    # Ownership Verification
    is_admin = user_role in ["ADMIN", "SUPERADMIN"] if user_role else False
    is_owner = not interview.interviewer_id or interview.interviewer_id == user_id
    if not is_owner and not is_admin:
        raise PermissionError("You do not have permission to cancel this interview. Only the assigned HR interviewer or an administrator can make changes.")

    # 1. Update status to CANCELED
    interview.status = "CANCELED"
    await InterviewRepository.add_interview_log(db, interview.id, "STATUS_CHANGE", "Status changed to CANCELED")
    await InterviewRepository.commit_changes(db)

    # 2. Synchronize removal to Google Calendar
    from app.repositories.auth_repository import AuthRepository
    scheduler_user = await AuthRepository.get_user_by_id_fresh(db, user_id)
    interviewer_to_sync = interview.interviewer_id or user_id
    user = await AuthRepository.get_user_by_id_fresh(db, interviewer_to_sync)
    credentials_json = _get_valid_credentials(user)
    if not credentials_json and interviewer_to_sync != user_id:
        user_fallback = await AuthRepository.get_user_by_id_fresh(db, user_id)
        credentials_json = _get_valid_credentials(user_fallback)
    if not credentials_json and scheduler_user:
        credentials_json = _get_valid_credentials(scheduler_user)

    old_event_id = interview.google_event_id
    if credentials_json and old_event_id:
        try:
            await asyncio.to_thread(
                delete_real_google_event,
                credentials_json=credentials_json,
                calendar_id="primary",
                event_id=old_event_id,
            )
            await InterviewRepository.add_interview_log(
                db, interview.id, "CALENDAR_SYNC", f"Removed Google Calendar event {old_event_id} due to cancellation"
            )
        except Exception as e:
            print(f"Warning: Could not remove Google Calendar event on cancellation: {e}")
        interview.google_event_id = None
        await InterviewRepository.commit_changes(db)

    # 3. Notify participants
    application = await InterviewRepository.get_job_application(db, interview.job_application_id)
    if application:
        job_name = None
        try:
            app_dict = getattr(application, "__dict__", {})
            if "job" in app_dict and app_dict["job"] is not None:
                job_name = getattr(app_dict["job"], "job_title", None)
        except Exception:
            pass

        if not job_name and getattr(application, "job_id", None):
            from app.repositories.job_description_repository import JobDescriptionRepository
            try:
                job_desc = await JobDescriptionRepository.get_by_id(db, application.job_id)
                if job_desc and getattr(job_desc, "job_title", None):
                    job_name = job_desc.job_title
            except Exception:
                pass

        if not job_name:
            job_name = getattr(application, "job_title", None) or "Job Position"

        interviewer_name = user.fullname if user and getattr(user, "fullname", None) else "Mariwasa HR Panel"

        panel_recipients = []
        for pid in (panelist_ids or []):
            p_user = await AuthRepository.get_user_by_id_fresh(db, pid)
            if p_user and getattr(p_user, "email", None):
                if not scheduler_user or p_user.email != getattr(scheduler_user, "email", None):
                    panel_recipients.append(p_user)

        if interview.interviewer_id and interview.interviewer_id != user_id:
            p_user = await AuthRepository.get_user_by_id_fresh(db, interview.interviewer_id)
            if p_user and getattr(p_user, "email", None):
                if p_user.email not in [p.email for p in panel_recipients]:
                    panel_recipients.append(p_user)

        # Also inspect interview logs to discover all previously notified panel members
        try:
            import re
            from sqlalchemy import select
            from app.models.interview import InterviewLog
            logs_res = await db.execute(select(InterviewLog).filter(InterviewLog.interview_id == interview.id))
            logs = logs_res.scalars().all()
            if not logs:
                logs = getattr(interview, "logs", []) or []
            for log in logs:
                details = getattr(log, "details", "") or ""
                if "panelist" in details.lower() and "@" in details:
                    emails_found = re.findall(r"[\w\.-]+@[\w\.-]+", details)
                    for em in emails_found:
                        if scheduler_user and em == getattr(scheduler_user, "email", None):
                            continue
                        if application and em == getattr(application, "candidate_email", None):
                            continue
                        if em not in [p.email for p in panel_recipients]:
                            found_user = await AuthRepository.get_user_by_email(db, em)
                            if found_user:
                                panel_recipients.append(found_user)
                            else:
                                class PanelObj:
                                    def __init__(self, email_val):
                                        self.email = email_val
                                        self.fullname = "Panel Interviewer"
                                panel_recipients.append(PanelObj(em))
        except Exception:
            pass

        # (a) HR Notification
        if scheduler_user and getattr(scheduler_user, "email", None):
            try:
                email_sent = await email_service.send_interview_cancellation_email(
                    to_email=scheduler_user.email,
                    candidate_name=application.candidate_name or "Candidate",
                    job_title=job_name,
                    interview_title=f"[HR Update] {interview.title}",
                    start_time=interview.start_time,
                    interviewer_name=interviewer_name,
                    reason=reason or "Interview cancelled by HR."
                )
                if email_sent:
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "EMAIL_CANCELED", f"Cancellation email sent to HR {scheduler_user.email}"
                    )
                    await InterviewRepository.commit_changes(db)
            except Exception as e:
                print(f"Warning: Could not send cancellation email to HR: {e}")

        # (b) Panelist Notification
        for p_user in panel_recipients:
            try:
                email_sent = await email_service.send_interview_cancellation_email(
                    to_email=p_user.email,
                    candidate_name=application.candidate_name or "Candidate",
                    job_title=job_name,
                    interview_title=f"[Panel Update] {interview.title}",
                    start_time=interview.start_time,
                    interviewer_name=p_user.fullname or interviewer_name,
                    reason=reason or "Interview cancelled."
                )
                if email_sent:
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "EMAIL_CANCELED", f"Cancellation email sent to panelist {p_user.email}"
                    )
                    await InterviewRepository.commit_changes(db)
            except Exception as e:
                print(f"Warning: Could not send cancellation email to panelist: {e}")

        # (c) Candidate Notification (Email + SMS)
        if application.candidate_email:
            try:
                email_sent = await email_service.send_interview_cancellation_email(
                    to_email=application.candidate_email,
                    candidate_name=application.candidate_name or "Candidate",
                    job_title=job_name,
                    interview_title=interview.title,
                    start_time=interview.start_time,
                    interviewer_name=interviewer_name,
                    reason=reason or "Interview has been cancelled."
                )
                if email_sent:
                    await InterviewRepository.add_interview_log(
                        db, interview.id, "EMAIL_CANCELED", f"Cancellation email sent to candidate {application.candidate_email}"
                    )
                    await InterviewRepository.commit_changes(db)
            except Exception as e:
                print(f"Warning: Could not send cancellation email to candidate: {e}")

        if application.phone:
            from app.services.ai_caller_service import format_to_e164
            formatted_phone = format_to_e164(application.phone) or application.phone
            message = (
                f"Mariwasa HR Update: Magandang araw, {application.candidate_name}! Nais naming ipaalam na kinansela ang "
                f"iyong interview para sa posisyong {job_name}. Pakitingnan ang iyong email ({application.candidate_email}) "
                f"para sa karagdagang impormasyon. Maraming salamat."
            )
            await asyncio.to_thread(send_sms_notification_sync, formatted_phone, message)
            try:
                await InterviewRepository.add_interview_log(
                    db,
                    interview.id,
                    "SMS_CANCELED",
                    f"Cancellation SMS notification delivered to {formatted_phone}: {message}"
                )
                await InterviewRepository.commit_changes(db)
            except Exception as log_err:
                await db.rollback()
                logger.warning(f"Could not persist cancel SMS log: {log_err}")

        # (d) In-App Notifications
        try:
            from app.services.notification_service import create_notification
            time_str = interview.start_time.strftime('%b %d, %Y at %I:%M %p')

            if application.candidate_email:
                await create_notification(
                    db=db,
                    title="Interview Canceled ❌",
                    message=f"Your interview for {job_name} originally scheduled for {time_str} has been canceled.",
                    type="schedule",
                    target_role="CANDIDATE",
                    target_email=application.candidate_email,
                    sender_role="HR"
                )

            await create_notification(
                db=db,
                title="Interview Canceled",
                message=f"Interview with {application.candidate_name} for {job_name} has been canceled.",
                type="schedule",
                target_role="HR",
                sender_role="HR"
            )

            for p_user in panel_recipients:
                if getattr(p_user, "email", None):
                    await create_notification(
                        db=db,
                        title="Panel Interview Canceled ❌",
                        message=f"Panel interview with {application.candidate_name} for {job_name} on {time_str} has been canceled.",
                        type="schedule",
                        target_role="PANELIST",
                        target_email=p_user.email,
                        sender_role="HR"
                    )
        except Exception as e_notif:
            print(f"Warning: Could not create interview cancellation notification: {e_notif}")

    return _populate_candidate_info(interview, app_override=application, interviewer_override=user)


async def update_interview_status(db: AsyncSession, interview_id: int, status: str, user_id: Optional[int] = None, user_role: Optional[str] = None):
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    # Ownership Verification
    if user_id is not None:
        is_admin = user_role in ["ADMIN", "SUPERADMIN"] if user_role else False
        is_owner = not interview.interviewer_id or interview.interviewer_id == user_id
        if not is_owner and not is_admin:
            raise PermissionError("You do not have permission to change the status of this interview. Only the assigned HR interviewer or an administrator can make changes.")

    if status == "CANCELED":
        return await cancel_interview(db, interview_id, user_id=user_id or (interview.interviewer_id or 0), user_role=user_role)

    interview.status = status
    await InterviewRepository.add_interview_log(db, interview.id, "STATUS_CHANGE", f"Status changed to {status}")
    updated = await InterviewRepository.update_interview(db, interview)
    return _populate_candidate_info(updated)


async def candidate_reschedule_interview(
    db: AsyncSession,
    interview_id: int,
    data: CandidateRescheduleSchema,
    candidate_email: Optional[str],
):
    """
    Allow the candidate who owns the interview's application to reschedule a missed
    or active interview into an available slot on the interviewer's calendar.
    """
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    application = await InterviewRepository.get_job_application(db, interview.job_application_id)
    if not application or not candidate_email or (application.candidate_email or "").strip().lower() != candidate_email.strip().lower():
        raise PermissionError("You do not have permission to reschedule this interview.")

    status_upper = (interview.status or "").upper()
    if status_upper in {"COMPLETED", "CANCELED", "CANCELLED"}:
        raise ValueError("Completed or canceled interviews cannot be rescheduled.")

    start = data.start_time.replace(tzinfo=None)
    end = data.end_time.replace(tzinfo=None)
    if start <= datetime.now():
        raise ValueError("Cannot reschedule an interview to a past date or time.")

    await _validate_interview_time_slot(db, interview, start, end, interview.interviewer_id)

    # Also verify against interviewer's Google Calendar / available slots for that day
    if interview.interviewer_id:
        day_start = start.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
        day_end = start.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)
        free_slots = await get_available_slots(db, day_start, day_end, user_ids=[interview.interviewer_id])
        if not any(
            s["start_time"] <= start and s["end_time"] >= end
            for s in (free_slots or [])
        ):
            raise ValueError("The selected time is not available on the interviewer's schedule.")

    old_time_str = interview.start_time.strftime("%b %d, %Y at %I:%M %p") if interview.start_time else "previous slot"
    interview.start_time = start
    interview.end_time = end
    interview.status = "SCHEDULED"
    interview.candidate_response = "CONFIRMED"

    reason_note = f" (Reason: {data.reason.strip()})" if data.reason and data.reason.strip() else ""
    await InterviewRepository.add_interview_log(
        db,
        interview.id,
        "CANDIDATE_RESCHEDULED",
        f"Candidate rescheduled from {old_time_str} to {start.strftime('%b %d, %Y at %I:%M %p')}{reason_note}",
    )
    interview = await InterviewRepository.update_interview(db, interview)

    from app.repositories.auth_repository import AuthRepository
    interviewer_user = (
        await AuthRepository.get_user_by_id_fresh(db, interview.interviewer_id)
        if interview.interviewer_id
        else None
    )
    interviewer_name = interviewer_user.fullname if interviewer_user and getattr(interviewer_user, "fullname", None) else "Mariwasa HR Panel"
    credentials_json = _get_valid_credentials(interviewer_user) if interviewer_user else None

    if credentials_json and interview.google_event_id:
        try:
            await asyncio.to_thread(
                update_real_google_event,
                credentials_json=credentials_json,
                calendar_id="primary",
                event_id=interview.google_event_id,
                summary=interview.title,
                start_dt=interview.start_time.isoformat(),
                end_dt=interview.end_time.isoformat(),
                description=interview.description or "",
                status="confirmed",
            )
        except Exception as cal_err:
            logger.warning(f"Could not sync candidate reschedule to Google Calendar: {cal_err}")

    job_name = getattr(application, "job_title", None) or "Job Position"
    time_str = interview.start_time.strftime("%b %d, %Y at %I:%M %p")
    try:
        from app.services.notification_service import create_notification
        await create_notification(
            db=db,
            title="Interview Rescheduled by Candidate",
            message=f"{application.candidate_name} rescheduled their interview for {job_name} to {time_str}{reason_note}.",
            type="schedule",
            target_role="HR",
            target_email=interviewer_user.email if interviewer_user else None,
            sender_role="CANDIDATE",
        )
    except Exception as notif_err:
        logger.warning(f"Could not create candidate reschedule notification: {notif_err}")

    if interviewer_user and getattr(interviewer_user, "email", None):
        try:
            await email_service.send_interview_rescheduled_email(
                to_email=interviewer_user.email,
                candidate_name=application.candidate_name or "Candidate",
                job_title=job_name,
                interview_title=f"[Candidate Rescheduled] {interview.title}",
                start_time=interview.start_time,
                end_time=interview.end_time,
                interviewer_name=interviewer_name,
                notes=f"Candidate rescheduled from {old_time_str}.{reason_note}",
            )
        except Exception as email_err:
            logger.warning(f"Could not send reschedule email to interviewer: {email_err}")

    _populate_candidate_info(interview, app_override=application, interviewer_override=interviewer_user)
    return interview


async def get_interviews_for_application(db: AsyncSession, application_id: int):
    interviews = await InterviewRepository.get_interviews_for_application(db, application_id)
    return [_populate_candidate_info(iv) for iv in interviews]

async def get_interviews_for_candidate(db: AsyncSession, email: str):
    interviews = await InterviewRepository.get_interviews_for_candidate(db, email)
    return [_populate_candidate_info(iv) for iv in interviews]

import sys
interview_service = sys.modules[__name__]


