import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from twilio.rest import Client as TwilioClient

from app.schemas.interview_schema import InterviewCreateSchema, InterviewUpdateSchema
from app.repositories.interview_repository import InterviewRepository
from app.services.google_calendar_service import (
    create_real_google_event,
    update_real_google_event,
    delete_real_google_event,
    query_freebusy,
    get_real_google_events,
)

def _populate_candidate_info(interview):
    """Helper to attach candidate details and interviewer info to the interview model."""
    app = getattr(interview, "job_application", None)
    if app:
        setattr(interview, "candidate_name", getattr(app, "candidate_name", None))
        setattr(interview, "candidate_email", getattr(app, "candidate_email", None))
        setattr(interview, "candidate_phone", getattr(app, "phone", None))
        setattr(interview, "job_title", getattr(app, "job_title", None))
        setattr(interview, "job_id", getattr(app, "job_description_id", None))

    interviewer = getattr(interview, "interviewer", None)
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
    return interview

def send_sms_notification_sync(to_phone: str, message: str):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_phone = os.getenv('TWILIO_PHONE_NUMBER')
    
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
            return False
    return False

# ── Working-hours constants ────────────────────────────────────────
WORK_START_HOUR = 8   # 8:00 AM
WORK_END_HOUR = 17    # 5:00 PM
BREAK_START_HOUR = 12 # 12:00 PM
BREAK_END_HOUR = 13   # 1:00 PM
# Monday=0 … Friday=4  (Python weekday convention)
WORK_DAYS = {0, 1, 2, 3, 4}


async def get_available_slots(db: AsyncSession, start_date: datetime, end_date: datetime, user_id: int):
    """
    Finds available 1-hour time slots that satisfy ALL of the following:
      • Falls on a weekday (Monday – Friday).
      • Falls within HR working hours (8:00 AM – 5:00 PM).
      • Not marked busy on the HR's Google Calendar (freebusy).
      • Not occupied by an existing (non-canceled) interview in the DB.
    """
    from app.repositories.auth_repository import AuthRepository
    user = await AuthRepository.get_user_by_id(db, user_id)
    credentials_json = user.google_credentials if user else None

    # Strip timezone info so all comparisons are naive (local time)
    start_date = start_date.replace(tzinfo=None)
    end_date = end_date.replace(tzinfo=None)

    # Pin the loop to the working-hours window for the requested day(s)
    loop_start = start_date.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
    loop_end = end_date.replace(hour=WORK_END_HOUR, minute=0, second=0, microsecond=0)

    # ── Fetch Google Calendar busy periods ───────────────────────
    calendars = None
    if credentials_json:
        # Use the full day range for the freebusy query
        calendars = await asyncio.to_thread(
            query_freebusy,
            credentials_json,
            ["primary"],
            loop_start.isoformat() + 'Z',
            loop_end.isoformat() + 'Z',
        )

    # Collect Google Calendar busy intervals into a flat list
    google_busy: List[tuple] = []
    if calendars:
        for _email, data in calendars.items():
            for busy in data.get('busy', []):
                busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00')).replace(tzinfo=None)
                busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00')).replace(tzinfo=None)
                google_busy.append((busy_start, busy_end))

    # ── Fetch existing DB interviews in the range for this interviewer ─
    db_interviews = await InterviewRepository.get_interviews_in_range(db, loop_start, loop_end, interviewer_id=user_id)
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

    return slots


async def schedule_interview(db: AsyncSession, data: InterviewCreateSchema, user_id: int):
    # 1. Fetch Candidate
    application = await InterviewRepository.get_job_application(db, data.job_application_id)
    if not application:
        raise ValueError("Application not found")

    # Target interviewer: if specified, use that HR account, else fallback to current user_id
    interviewer_id = data.interviewer_id if data.interviewer_id else user_id

    from app.repositories.auth_repository import AuthRepository
    user = await AuthRepository.get_user_by_id(db, interviewer_id)
    credentials_json = user.google_credentials if user else None

    # 2. Create Interview Record
    start = data.start_time.replace(tzinfo=None)
    end = data.end_time.replace(tzinfo=None)

    # Break time check (12:00 PM – 1:00 PM)
    break_start = start.replace(hour=BREAK_START_HOUR, minute=0, second=0, microsecond=0)
    break_end = start.replace(hour=BREAK_END_HOUR, minute=0, second=0, microsecond=0)
    if start < break_end and end > break_start:
        raise ValueError("Interviews cannot be scheduled during break time (12:00 PM – 1:00 PM).")

    interview_data = {
        "job_application_id": data.job_application_id,
        "interviewer_id": interviewer_id,
        "title": data.title,
        "description": data.description,
        "start_time": start,
        "end_time": end
    }
    interview = await InterviewRepository.create_interview(db, interview_data)
    interview = await InterviewRepository.update_interview(db, interview)

    # 3. Create Google Calendar Event via centralized service if credentials exist
    attendees = []
    if application.candidate_email:
        attendees.append({"email": application.candidate_email})

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
                create_meet_link=True,
                interview_id=interview.id,
            )

            if event:
                interview.google_event_id = event.get('id')
                # Extract Google Meet link
                conference_data = event.get('conferenceData', {})
                entry_points = conference_data.get('entryPoints', [])
                for ep in entry_points:
                    if ep.get('entryPointType') == 'video':
                        interview.meeting_link = ep.get('uri')
                        break
                await InterviewRepository.commit_changes(db)
        except Exception as e:
            print(f"Warning: Could not create event on Google Calendar: {e}")
    else:
        # Generate a standard meeting link if Google Calendar is not linked
        interview.meeting_link = f"https://meet.google.com/aras-{interview.id}"
        await InterviewRepository.commit_changes(db)

    # 4. Send SMS Notification
    if application.phone:
        message = f"Hi {application.candidate_name}, your interview for {application.job_title} is scheduled on {data.start_time.strftime('%Y-%m-%d %H:%M')}. Link: {interview.meeting_link or 'Sent to email'}."
        sent = await asyncio.to_thread(send_sms_notification_sync, application.phone, message)
        if sent:
            await InterviewRepository.add_interview_log(db, interview.id, "SMS_SENT", "Notification sent to candidate")
            await InterviewRepository.commit_changes(db)

    # 5. Update candidate application status if pending
    if getattr(application, "status", None) == "PENDING":
        application.status = "SCHEDULED"
        await InterviewRepository.commit_changes(db)

    # Attach candidate and interviewer attributes for Pydantic response
    setattr(interview, "job_application", application)
    setattr(interview, "interviewer", user)
    _populate_candidate_info(interview)
    return interview


async def update_interview(db: AsyncSession, interview_id: int, data: InterviewUpdateSchema, user_id: int):
    """
    Modify/reschedule an interview and synchronize the update directly with Google Calendar.
    """
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    time_changed = False
    if data.start_time is not None or data.end_time is not None:
        start = (data.start_time or interview.start_time).replace(tzinfo=None)
        end = (data.end_time or interview.end_time).replace(tzinfo=None)

        # Weekday check (Monday=0 … Friday=4)
        if start.weekday() > 4:
            raise ValueError("Interviews can only be scheduled on weekdays (Monday – Friday).")

        # Working-hours check (8:00 AM – 5:00 PM)
        if start.hour < WORK_START_HOUR or end.hour > WORK_END_HOUR or (end.hour == WORK_END_HOUR and end.minute > 0):
            raise ValueError("Interviews must be scheduled within working hours (8:00 AM – 5:00 PM).")

        # Conflict check against other interviews (excluding self)
        conflicts = await InterviewRepository.get_interviews_in_range_excluding(db, start, end, interview.id)
        if conflicts:
            raise ValueError("The selected time slot conflicts with an existing interview.")

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
    if data.status is not None:
        old_status = interview.status
        interview.status = data.status
        if old_status != data.status:
            await InterviewRepository.add_interview_log(db, interview.id, "STATUS_CHANGE", f"Status changed to {data.status}")

    await InterviewRepository.add_interview_log(db, interview.id, "UPDATED", "Interview details modified")
    interview = await InterviewRepository.update_interview(db, interview)

    # Synchronize modification to Google Calendar if linked
    from app.repositories.auth_repository import AuthRepository
    interviewer_to_sync = interview.interviewer_id or user_id
    user = await AuthRepository.get_user_by_id(db, interviewer_to_sync)
    credentials_json = user.google_credentials if user else None
    if not credentials_json and interviewer_to_sync != user_id:
        user_fallback = await AuthRepository.get_user_by_id(db, user_id)
        credentials_json = user_fallback.google_credentials if user_fallback else None

    if credentials_json and interview.google_event_id:
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

    # If rescheduled time changed, notify candidate via SMS
    application = await InterviewRepository.get_job_application(db, interview.job_application_id)
    if time_changed and application and application.phone:
        message = (
            f"Hi {application.candidate_name}, your interview for {application.job_title} has been rescheduled to "
            f"{interview.start_time.strftime('%Y-%m-%d %H:%M')}. Meeting link: {interview.meeting_link or 'Sent to email'}."
        )
        sent = await asyncio.to_thread(send_sms_notification_sync, application.phone, message)
        if sent:
            await InterviewRepository.add_interview_log(db, interview.id, "SMS_RESCHEDULED", "Reschedule SMS notification sent")
            await InterviewRepository.commit_changes(db)

    setattr(interview, "job_application", application)
    _populate_candidate_info(interview)
    return interview


async def delete_interview(db: AsyncSession, interview_id: int, user_id: int):
    """
    Delete an interview and delete its corresponding event from Google Calendar.
    """
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    from app.repositories.auth_repository import AuthRepository
    interviewer_to_sync = interview.interviewer_id or user_id
    user = await AuthRepository.get_user_by_id(db, interviewer_to_sync)
    credentials_json = user.google_credentials if user else None
    if not credentials_json and interviewer_to_sync != user_id:
        user_fallback = await AuthRepository.get_user_by_id(db, user_id)
        credentials_json = user_fallback.google_credentials if user_fallback else None

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
    user = await AuthRepository.get_user_by_id(db, sync_user_id)
    credentials_json = user.google_credentials if user else None

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
    user = await AuthRepository.get_user_by_id(db, user_id)
    if not user or not user.google_credentials:
        return {
            "connected": False,
            "email": None,
            "message": "Google Calendar is not connected. Connect your Google account to sync schedules."
        }
    return {
        "connected": True,
        "email": user.email,
        "message": "Google Calendar is connected and synchronizing."
    }


async def get_calendar_events(db: AsyncSession, user_id: int):
    from app.repositories.auth_repository import AuthRepository
    user = await AuthRepository.get_user_by_id(db, user_id)
    credentials_json = user.google_credentials if user else None
    
    if credentials_json:
        events = await asyncio.to_thread(
            get_real_google_events,
            credentials_json,
            calendar_id="primary",
            max_results=50
        )
        return events or []
    return []


async def update_interview_status(db: AsyncSession, interview_id: int, status: str):
    interview = await InterviewRepository.get_interview_by_id(db, interview_id)
    if not interview:
        raise ValueError("Interview not found")

    interview.status = status
    await InterviewRepository.add_interview_log(db, interview.id, "STATUS_CHANGE", f"Status changed to {status}")
    updated = await InterviewRepository.update_interview(db, interview)
    return _populate_candidate_info(updated)


async def get_interviews_for_application(db: AsyncSession, application_id: int):
    interviews = await InterviewRepository.get_interviews_for_application(db, application_id)
    return [_populate_candidate_info(iv) for iv in interviews]

async def get_interviews_for_candidate(db: AsyncSession, email: str):
    interviews = await InterviewRepository.get_interviews_for_candidate(db, email)
    return [_populate_candidate_info(iv) for iv in interviews]

class InterviewService:
    WORK_START_HOUR = WORK_START_HOUR
    WORK_END_HOUR = WORK_END_HOUR
    WORK_DAYS = WORK_DAYS

    get_available_slots = staticmethod(get_available_slots)
    schedule_interview = staticmethod(schedule_interview)
    update_interview = staticmethod(update_interview)
    delete_interview = staticmethod(delete_interview)
    get_all_interviews = staticmethod(get_all_interviews)
    get_calendar_feed = staticmethod(get_calendar_feed)
    get_google_calendar_status = staticmethod(get_google_calendar_status)
    get_calendar_events = staticmethod(get_calendar_events)
    update_interview_status = staticmethod(update_interview_status)
    get_interviews_for_application = staticmethod(get_interviews_for_application)
    get_interviews_for_candidate = staticmethod(get_interviews_for_candidate)


interview_service = InterviewService()


