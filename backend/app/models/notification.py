from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.utils.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False) # e.g., 'registration', 'application', 'upload', 'system'
    is_read = Column(Boolean, default=False)
    target_role = Column(String, nullable=True) # e.g., 'HR', 'ADMIN'
    target_email = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
