from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class AvailableSlotsRequest(BaseModel):
    start_date: datetime
    end_date: datetime

    
class InterviewCreateSchema(BaseModel):
    job_application_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime

class InterviewUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None

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
    
    class Config:
        from_attributes = True

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

