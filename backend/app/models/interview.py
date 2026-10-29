from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.database import Base

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    job_application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False)
    interviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    google_event_id = Column(String, nullable=True)
    meeting_link = Column(String, nullable=True)
    status = Column(String, default="SCHEDULED") # SCHEDULED, CONFIRMED, RESCHEDULE_REQUESTED, COMPLETED, CANCELED, NO_SHOW
    
    # AI Voice Notification tracking (REQ028 - REQ034)
    call_status = Column(String, default="PENDING") # PENDING, IN_PROGRESS, CONFIRMED, RESCHEDULE_REQUESTED, RETRY_SCHEDULED, UNREACHABLE, FAILED, SMS_BACKUP_SENT
    call_attempts = Column(Integer, default=0) # 0 to 3 attempts
    last_call_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    candidate_response = Column(String, nullable=True) # CONFIRMED, RESCHEDULE_REQUESTED, NO_ANSWER
    call_language = Column(String, default="bilingual") # en, fil, bilingual
    verbal_notes = Column(Text, nullable=True) # Spoken words or AI transcription
    sms_backup_sent = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job_application = relationship("JobApplication", backref="interviews", lazy="selectin")
    interviewer = relationship("User", foreign_keys=[interviewer_id], lazy="selectin")
    logs = relationship("InterviewLog", back_populates="interview", cascade="all, delete-orphan", lazy="selectin", order_by="InterviewLog.id.desc()")
    call_records = relationship("VoiceCallRecord", back_populates="interview", cascade="all, delete-orphan", lazy="selectin", order_by="VoiceCallRecord.id.desc()")


class InterviewLog(Base):
    __tablename__ = "interview_logs"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    log_type = Column(String, nullable=False) # e.g., "SMS_SENT", "EMAIL_SENT", "VOICE_CALL_ATTEMPT", "VOICE_CALL_CONFIRMED", "VOICE_CALL_RESCHEDULE", "SMS_BACKUP_SENT", "STATUS_CHANGE"
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="logs")


class VoiceCallRecord(Base):
    __tablename__ = "voice_call_records"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    call_sid = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    attempt_number = Column(Integer, default=1) # 1, 2, 3
    status = Column(String, default="INITIATED") # INITIATED, RINGING, ANSWERED, COMPLETED, BUSY, NO_ANSWER, FAILED
    duration = Column(Integer, default=0) # duration in seconds
    language = Column(String, default="bilingual") # en, fil, bilingual
    candidate_verbal_response = Column(Text, nullable=True) # Full transcript / spoken phrase
    extracted_intent = Column(String, nullable=True) # CONFIRMED, RESCHEDULE_REQUESTED, UNANSWERED, FAILED, BUSY
    notes = Column(Text, nullable=True)
    sms_backup_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="call_records")

