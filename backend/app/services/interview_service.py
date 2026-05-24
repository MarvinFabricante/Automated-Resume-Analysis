import os
import asyncio
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from twilio.rest import Client as TwilioClient

from app.models.interview import Interview, InterviewPanelist, InterviewLog
from app.models.job_application import JobApplication
from app.models.user import User
from app.schemas.interview_schema import InterviewCreateSchema

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    """Authenticates and returns the Google Calendar API service."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"Error reading token.json: {e}")

    # If there are no (valid) credentials available, log warning.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                creds = None
        else:
            print("Google Calendar credentials not found or invalid. Skipping Google Calendar integration.")
            return None

        if creds:
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    
    if creds:
        try:
            service = build('calendar', 'v3', credentials=creds)
            return service
        except Exception as e:
            print(f"Error building calendar service: {e}")
            
    return None

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

async def get_available_slots(db: AsyncSession, panelist_ids: List[int], start_date: datetime, end_date: datetime):
    """Finds available time slots based on panelists' Google Calendars."""
    service = await asyncio.to_thread(get_google_calendar_service)
    
    # MOCK GOOGLE CALENDAR SLOTS if service is not configured
    if not service:
        slots = []
        current_time = start_date
        while current_time < end_date:
            slot_end = current_time + timedelta(hours=1)
            # Only mock slots between 9 AM and 5 PM
            if current_time.hour >= 9 and current_time.hour < 17:
                slots.append({
                    "start_time": current_time,
                    "end_time": slot_end
                })
            current_time += timedelta(minutes=30)
        return slots
        
    result = await db.execute(select(User).filter(User.id.in_(panelist_ids)))
    panelists = result.scalars().all()
    emails = [{"id": p.email} for p in panelists if p.email]
    
    if not emails:
        return []

    body = {
        "timeMin": start_date.isoformat() + 'Z',
        "timeMax": end_date.isoformat() + 'Z',
        "items": emails
    }

    try:
        eventsResult = await asyncio.to_thread(
            lambda: service.freebusy().query(body=body).execute()
        )
        calendars = eventsResult.get('calendars', {})
        
        # Simple logic: assume working hours 9 to 5, split by 1 hour slots, check if any panelist is busy
        slots = []
        current_time = start_date
        while current_time < end_date:
            slot_end = current_time + timedelta(hours=1)
            is_free = True
            
            for email, data in calendars.items():
                busy_times = data.get('busy', [])
                for busy in busy_times:
                    busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00')).replace(tzinfo=None)
                    busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00')).replace(tzinfo=None)
                    if (current_time < busy_end and slot_end > busy_start):
                        is_free = False
                        break
                if not is_free:
                    break
            
            if is_free and current_time.hour >= 9 and current_time.hour < 17:
                slots.append({
                    "start_time": current_time,
                    "end_time": slot_end
                })
            
            current_time += timedelta(minutes=30) # 30 min intervals
            
        return slots
    except Exception as e:
        print(f"Calendar API error: {e}")
        return []

async def schedule_interview(db: AsyncSession, data: InterviewCreateSchema):
    # 1. Fetch Candidate and Panelists
    result = await db.execute(select(JobApplication).filter(JobApplication.id == data.job_application_id))
    application = result.scalars().first()
    if not application:
        raise ValueError("Application not found")
        
    p_result = await db.execute(select(User).filter(User.id.in_(data.panelist_ids)))
    panelists = p_result.scalars().all()
    
    # 2. Create Interview Record
    interview = Interview(
        job_application_id=data.job_application_id,
        title=data.title,
        description=data.description,
        start_time=data.start_time,
        end_time=data.end_time
    )
    db.add(interview)
    await db.flush() # flush to get interview.id
    
    for panelist in panelists:
        db.add(InterviewPanelist(interview_id=interview.id, user_id=panelist.id))
        
    await db.commit()
    await db.refresh(interview)
    
    # 3. Create Google Calendar Event
    service = await asyncio.to_thread(get_google_calendar_service)
    if service:
        attendees = [{"email": p.email} for p in panelists if p.email]
        if application.candidate_email:
            attendees.append({"email": application.candidate_email})
            
        event_body = {
            'summary': data.title,
            'description': data.description,
            'start': {
                'dateTime': data.start_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': data.end_time.isoformat() + 'Z',
                'timeZone': 'UTC',
            },
            'attendees': attendees,
            'conferenceData': {
                'createRequest': {
                    'requestId': f"interview_{interview.id}_{datetime.now().timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        
        try:
            event = await asyncio.to_thread(
                lambda: service.events().insert(
                    calendarId='primary', 
                    body=event_body, 
                    conferenceDataVersion=1,
                    sendUpdates='all'
                ).execute()
            )
            
            interview.google_event_id = event.get('id')
            # Extract Google Meet link
            conference_data = event.get('conferenceData', {})
            entry_points = conference_data.get('entryPoints', [])
            for ep in entry_points:
                if ep.get('entryPointType') == 'video':
                    interview.meeting_link = ep.get('uri')
                    break
                    
            await db.commit()
        except Exception as e:
            print(f"Error creating calendar event: {e}")
    else:
        # Mock Google Calendar Integration
        interview.google_event_id = f"mock_event_{interview.id}"
        interview.meeting_link = "https://meet.google.com/mock-link-123"
        await db.commit()
    
    # 4. Send SMS Notification
    if application.phone:
        message = f"Hi {application.candidate_name}, your interview for {application.job_title} is scheduled on {data.start_time.strftime('%Y-%m-%d %H:%M')}. Link: {interview.meeting_link or 'Sent to email'}."
        sent = await asyncio.to_thread(send_sms_notification_sync, application.phone, message)
        if sent:
            db.add(InterviewLog(interview_id=interview.id, log_type="SMS_SENT", details="Notification sent to candidate"))
            await db.commit()

    return interview

async def update_interview_status(db: AsyncSession, interview_id: int, status: str):
    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    interview = result.scalars().first()
    if not interview:
        raise ValueError("Interview not found")
        
    interview.status = status
    db.add(InterviewLog(interview_id=interview.id, log_type="STATUS_CHANGE", details=f"Status changed to {status}"))
    await db.commit()
    await db.refresh(interview)
    return interview

async def get_interviews_for_application(db: AsyncSession, application_id: int):
    result = await db.execute(select(Interview).filter(Interview.job_application_id == application_id))
    return result.scalars().all()
