from pydantic import BaseModel
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    is_read: bool
    target_role: str | None = None
    target_email: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
