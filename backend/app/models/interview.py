from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.database import Base

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    job_application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    google_event_id = Column(String, nullable=True)
    meeting_link = Column(String, nullable=True)
    status = Column(String, default="SCHEDULED") # SCHEDULED, COMPLETED, CANCELED, NO_SHOW
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job_application = relationship("JobApplication", backref="interviews")
    panelists = relationship("InterviewPanelist", back_populates="interview", cascade="all, delete-orphan")
    logs = relationship("InterviewLog", back_populates="interview", cascade="all, delete-orphan")


class InterviewPanelist(Base):
    __tablename__ = "interview_panelists"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    interview = relationship("Interview", back_populates="panelists")
    user = relationship("User")


class InterviewLog(Base):
    __tablename__ = "interview_logs"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    log_type = Column(String, nullable=False) # e.g., "SMS_SENT", "EMAIL_SENT", "CALL_LOG", "STATUS_CHANGE"
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="logs")
