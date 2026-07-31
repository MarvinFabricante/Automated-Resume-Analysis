import os
import asyncio
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from twilio.rest import Client as TwilioClient

from app.schemas.interview_schema import InterviewCreateSchema
from app.repositories.interview_repository import InterviewRepository
from app.services.google_calendar_service import (
    create_real_google_event,
    query_freebusy,
    get_real_google_events,
)

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

class InterviewService:
    # ── Working-hours constants ────────────────────────────────────────
    WORK_START_HOUR = 8   # 8:00 AM
    WORK_END_HOUR = 17    # 5:00 PM
    # Monday=0 … Friday=4  (Python weekday convention)
    WORK_DAYS = {0, 1, 2, 3, 4}

    async def get_available_slots(self, db: AsyncSession, start_date: datetime, end_date: datetime, user_id: int):
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
        loop_start = start_date.replace(hour=self.WORK_START_HOUR, minute=0, second=0, microsecond=0)
        loop_end = end_date.replace(hour=self.WORK_END_HOUR, minute=0, second=0, microsecond=0)

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

        # ── Fetch existing DB interviews in the range ────────────────
        db_interviews = await InterviewRepository.get_interviews_in_range(db, loop_start, loop_end)
        db_busy: List[tuple] = [(iv.start_time, iv.end_time) for iv in db_interviews]

        # Merge both busy lists
        all_busy = google_busy + db_busy

        # ── Generate candidate slots & filter ────────────────────────
        slots = []
        current_time = loop_start
        while current_time < loop_end:
            slot_end = current_time + timedelta(hours=1)

            # Skip weekends
            if current_time.weekday() not in self.WORK_DAYS:
                next_day = current_time + timedelta(days=1)
                current_time = next_day.replace(hour=self.WORK_START_HOUR, minute=0, second=0, microsecond=0)
                continue

            # Skip if slot starts before working hours
            if current_time.hour < self.WORK_START_HOUR:
                current_time = current_time.replace(hour=self.WORK_START_HOUR, minute=0, second=0, microsecond=0)
                continue

            # If slot_end exceeds working hours boundary for the day, move to next day
            day_end = current_time.replace(hour=self.WORK_END_HOUR, minute=0, second=0, microsecond=0)
            if slot_end > day_end:
                next_day = current_time + timedelta(days=1)
                current_time = next_day.replace(hour=self.WORK_START_HOUR, minute=0, second=0, microsecond=0)
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

    async def schedule_interview(self, db: AsyncSession, data: InterviewCreateSchema, user_id: int):
        # 1. Fetch Candidate
        application = await InterviewRepository.get_job_application(db, data.job_application_id)
        if not application:
            raise ValueError("Application not found")

        from app.repositories.auth_repository import AuthRepository
        user = await AuthRepository.get_user_by_id(db, user_id)
        credentials_json = user.google_credentials if user else None


        # 2. Create Interview Record
        interview_data = {
            "job_application_id": data.job_application_id,
            "title": data.title,
            "description": data.description,
            "start_time": data.start_time.replace(tzinfo=None),
            "end_time": data.end_time.replace(tzinfo=None)
        }
        interview = await InterviewRepository.create_interview(db, interview_data)


        interview = await InterviewRepository.update_interview(db, interview)

        # 3. Create Google Calendar Event via centralized service
        attendees = []
        if application.candidate_email:
            attendees.append({"email": application.candidate_email})

        if not credentials_json:
            raise ValueError("Ensure HR's Google Calendar is connected.")

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
        else:
            raise ValueError("Failed to create Google Calendar event. Ensure HR's Google Calendar is connected.")

        # 4. Send SMS Notification
        if application.phone:
            message = f"Hi {application.candidate_name}, your interview for {application.job_title} is scheduled on {data.start_time.strftime('%Y-%m-%d %H:%M')}. Link: {interview.meeting_link or 'Sent to email'}."
            sent = await asyncio.to_thread(send_sms_notification_sync, application.phone, message)
            if sent:
                await InterviewRepository.add_interview_log(db, interview.id, "SMS_SENT", "Notification sent to candidate")
                await InterviewRepository.commit_changes(db)

        return interview

    async def get_calendar_events(self, db: AsyncSession, user_id: int):
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

    async def update_interview_status(self, db: AsyncSession, interview_id: int, status: str):
        interview = await InterviewRepository.get_interview_by_id(db, interview_id)
        if not interview:
            raise ValueError("Interview not found")

        interview.status = status
        await InterviewRepository.add_interview_log(db, interview.id, "STATUS_CHANGE", f"Status changed to {status}")
        return await InterviewRepository.update_interview(db, interview)
        return interview

    async def get_interviews_for_application(self, db: AsyncSession, application_id: int):
        return await InterviewRepository.get_interviews_for_application(db, application_id)


interview_service = InterviewService()


async def get_available_slots(db: AsyncSession, start_date: datetime, end_date: datetime, user_id: int):
    return await interview_service.get_available_slots(db, start_date, end_date, user_id)


async def schedule_interview(db: AsyncSession, data: InterviewCreateSchema, user_id: int):
    return await interview_service.schedule_interview(db, data, user_id)

async def get_calendar_events(db: AsyncSession, user_id: int):
    return await interview_service.get_calendar_events(db, user_id)

async def update_interview_status(db: AsyncSession, interview_id: int, status: str):
    return await interview_service.update_interview_status(db, interview_id, status)


async def get_interviews_for_application(db: AsyncSession, application_id: int):
    return await interview_service.get_interviews_for_application(db, application_id)
