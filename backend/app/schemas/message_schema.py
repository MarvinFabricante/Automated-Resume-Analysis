from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MessageCreate(BaseModel):
    content: str
    message_type: Optional[str] = "general" # update, instructions, announcement, reminder, general
    application_id: Optional[int] = None

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    application_id: Optional[int] = None
    message_type: Optional[str] = "general"
    content: str
    timestamp: datetime
    is_read: bool
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BroadcastMessageCreate(BaseModel):
    content: str
    message_type: Optional[str] = "announcement" # update, instructions, announcement, reminder, general
    target_group: Optional[str] = "all" # "all" or "shortlisted"

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
