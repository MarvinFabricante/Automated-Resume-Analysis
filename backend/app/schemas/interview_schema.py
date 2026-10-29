from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class AvailableSlotsRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    hr_id: Optional[int] = None

    
class InterviewCreateSchema(BaseModel):
    job_application_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    interviewer_id: Optional[int] = None

class InterviewUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    interviewer_id: Optional[int] = None

class VoiceCallRecordResponseSchema(BaseModel):
    id: int
    interview_id: int
    call_sid: Optional[str] = None
    phone_number: str
    attempt_number: int
    status: str
    duration: int = 0
    language: str = "bilingual"
    candidate_verbal_response: Optional[str] = None
    extracted_intent: Optional[str] = None
    notes: Optional[str] = None
    sms_backup_sent: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class InterviewResponseSchema(BaseModel):
    id: int
    job_application_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    google_event_id: Optional[str] = None
    meeting_link: Optional[str] = None
    status: str
    created_at: datetime
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    job_title: Optional[str] = None
    job_id: Optional[int] = None
    interviewer_id: Optional[int] = None
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None
    
    # AI Voice Notification fields
    call_status: Optional[str] = "PENDING"
    call_attempts: Optional[int] = 0
    last_call_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    candidate_response: Optional[str] = None
    call_language: Optional[str] = "bilingual"
    verbal_notes: Optional[str] = None
    sms_backup_sent: Optional[bool] = False
    call_records: Optional[List[VoiceCallRecordResponseSchema]] = []
    
    class Config:
        from_attributes = True

class SimulateVoiceCallRequest(BaseModel):
    outcome: str = "CONFIRMED" # CONFIRMED, RESCHEDULE_REQUESTED, NO_ANSWER, BUSY, FAILED
    spoken_phrase: Optional[str] = None
    language: Optional[str] = "en"

class TimeSlotSchema(BaseModel):
    start_time: datetime
    end_time: datetime

class GoogleCalendarStatusSchema(BaseModel):
    connected: bool
    email: Optional[str] = None
    message: Optional[str] = None

class CalendarFeedResponseSchema(BaseModel):
    interviews: List[InterviewResponseSchema]
    google_events: List[Dict[str, Any]] = []
    google_connected: bool = False
    google_account: Optional[str] = None


