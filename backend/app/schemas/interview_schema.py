from pydantic import BaseModel, Field
from typing import List, Optional
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
    
    class Config:
        from_attributes = True

class TimeSlotSchema(BaseModel):
    start_time: datetime
    end_time: datetime
