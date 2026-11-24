from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    content: str
    message_type: Optional[str] = "general"  # update, instructions, announcement, reminder, general
    application_id: Optional[int] = None


class MessageResponse(BaseModel):
    id: int
    thread_id: Optional[int] = None
    sender_id: int
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    receiver_id: int
    application_id: Optional[int] = None
    message_type: Optional[str] = "general"
    content: str
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_size: Optional[int] = None
    is_reported: bool = False
    timestamp: datetime
    is_read: bool
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ThreadStartRequest(BaseModel):
    application_id: int
    content: Optional[str] = None
    message_type: Optional[str] = "general"


class ThreadMessageCreate(BaseModel):
    content: str = ""
    message_type: Optional[str] = "general"


class ThreadStatusResponse(BaseModel):
    is_closed: bool = False
    can_reply: bool = True
    reason: Optional[str] = None
    closes_at: Optional[str] = None


class ApplicationThreadSummary(BaseModel):
    id: int
    application_id: int
    job_id: Optional[int] = None
    job_title: str = "Position"
    application_status: str = "Submitted"
    candidate_id: Optional[int] = None
    candidate_name: str = "Applicant"
    candidate_email: Optional[str] = None
    candidate_profile_image_url: Optional[str] = None
    started_by_id: Optional[int] = None
    started_by_name: Optional[str] = None
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    last_sender_name: Optional[str] = None
    last_sender_role: Optional[str] = None
    unread_count: int = 0
    is_closed: bool = False
    can_reply: bool = True
    closure_reason: Optional[str] = None
    closes_at: Optional[str] = None
    is_archived: bool = False
    created_at: Optional[datetime] = None


class ApplicationThreadListResponse(BaseModel):
    threads: List[ApplicationThreadSummary]
    total_unread: int = 0


class ApplicationThreadDetailResponse(BaseModel):
    exists: bool
    thread: Optional[ApplicationThreadSummary] = None
    messages: List[MessageResponse] = []
    thread_status: ThreadStatusResponse


class MessageReportCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class MessageReportResponse(BaseModel):
    id: int
    message_id: int
    thread_id: Optional[int] = None
    status: str
    detail: str


class HRMessageTemplateItem(BaseModel):
    key: str
    label: str
    body: str


class BroadcastMessageCreate(BaseModel):
    content: str
    message_type: Optional[str] = "announcement"  # update, instructions, announcement, reminder, general
    target_group: Optional[str] = "all"  # "all" or "shortlisted"


class BroadcastMessageResponse(BaseModel):
    success: bool
    recipient_count: int
    message: str


class SentMessageRecord(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    receiver_name: str
    receiver_email: str
    application_id: Optional[int] = None
    job_title: Optional[str] = None
    message_type: str
    content: str
    timestamp: datetime
    is_read: bool
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatUser(BaseModel):
    id: int
    fullname: str
    role: str
    profile_image_url: Optional[str] = None
    is_online: Optional[bool] = False
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: Optional[int] = 0
    is_archived: Optional[bool] = False


class ChatContactResponse(BaseModel):
    users: List[ChatUser]


class ArchiveConversationResponse(BaseModel):
    success: bool
    contact_id: int
    is_archived: bool
    message: str


class ArchivedContactsResponse(BaseModel):
    archived_contact_ids: List[int]
