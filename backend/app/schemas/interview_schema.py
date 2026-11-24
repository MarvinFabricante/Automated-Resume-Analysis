from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any, Dict, Literal
from datetime import datetime

class AvailableSlotsRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    hr_id: Optional[int] = None
    manager_id: Optional[int] = None
    user_ids: Optional[List[int]] = None
    interviewer_ids: Optional[List[int]] = None
    panelist_ids: Optional[List[int]] = None

    
class InterviewCreateSchema(BaseModel):
    job_application_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    interviewer_id: Optional[int] = None
    panelist_ids: Optional[List[int]] = None
    call_language: Optional[str] = "bilingual"
    interview_type: Optional[Literal["Onsite", "Online"]] = None
    instructions: Optional[str] = None
    platform: Optional[Literal["Google Meet", "Zoom", "Microsoft Teams", "Other"]] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    custom_email_subject: Optional[str] = None
    custom_email_message: Optional[str] = None
    custom_sms_message: Optional[str] = None
    combined_application_ids: Optional[List[int]] = None

    @model_validator(mode="after")
    def validate_venue(self):
        from app.services.interview_details import validate_interview_details
        if self.interview_type is not None or self.location or self.meeting_link:
            self.interview_type = self.interview_type or ("Online" if self.meeting_link else "Onsite")
            validate_interview_details(self.interview_type, self.location, self.meeting_link)
        return self


class InterviewUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    interviewer_id: Optional[int] = None
    call_language: Optional[str] = None
    panelist_ids: Optional[List[int]] = None
    interview_type: Optional[Literal["Onsite", "Online"]] = None
    instructions: Optional[str] = None
    platform: Optional[Literal["Google Meet", "Zoom", "Microsoft Teams", "Other"]] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    custom_email_subject: Optional[str] = None
    custom_email_message: Optional[str] = None
    custom_sms_message: Optional[str] = None
    combined_application_ids: Optional[List[int]] = None


class InterviewCancelSchema(BaseModel):
    reason: Optional[str] = None
    custom_email_subject: Optional[str] = None
    custom_email_message: Optional[str] = None
    custom_sms_message: Optional[str] = None
    combined_application_ids: Optional[List[int]] = None


class CandidateRescheduleSchema(BaseModel):
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None

class InterviewLogResponseSchema(BaseModel):
    id: int
    interview_id: int
    log_type: str
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

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
    location: Optional[str] = None
    interview_type: Optional[str] = "Not specified"
    instructions: Optional[str] = None
    platform: Optional[str] = None
    candidate_user_id: Optional[int] = None
    status: str
    is_missed: Optional[bool] = False
    created_at: datetime
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    job_title: Optional[str] = None
    job_id: Optional[int] = None
    interviewer_id: Optional[int] = None
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None
    is_combined: Optional[bool] = False
    combined_application_ids: Optional[List[int]] = None
    combined_positions: Optional[List[Dict[str, Any]]] = None
    
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
    logs: Optional[List[InterviewLogResponseSchema]] = []
    
    class Config:
        from_attributes = True

class SimulateVoiceCallRequest(BaseModel):
    outcome: str = "CONFIRMED" # CONFIRMED, RESCHEDULE_REQUESTED, NO_ANSWER, BUSY, FAILED
    spoken_phrase: Optional[str] = None
    language: Optional[str] = "en"

class TimeSlotSchema(BaseModel):
    start_time: datetime
    end_time: datetime

class AvailableSlotsResponseSchema(BaseModel):
    slots: List[TimeSlotSchema] = []
    message: Optional[str] = None
    alternative_dates: List[str] = []
    alternative_slots: List[TimeSlotSchema] = []

class GoogleCalendarStatusSchema(BaseModel):
    connected: bool
    email: Optional[str] = None
    message: Optional[str] = None

class CalendarFeedResponseSchema(BaseModel):
    interviews: List[InterviewResponseSchema]
    google_events: List[Dict[str, Any]] = []
    google_connected: bool = False
    google_account: Optional[str] = None


