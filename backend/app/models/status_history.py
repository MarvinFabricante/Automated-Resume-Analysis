from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from datetime import datetime
from app.utils.database import Base

class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False, index=True)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False, index=True)
    changed_by = Column(String, nullable=False, default="auto") # user email or 'auto'
    change_type = Column(String, nullable=False, default="auto") # 'auto', 'manual', 'undo'
    reason = Column(String, nullable=True) # e.g. 'auto: viewed', 'auto: added to roster', 'manual'
    can_undo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
