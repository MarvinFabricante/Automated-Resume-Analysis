from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.database import Base

class PhysicalResume(Base):
    __tablename__ = "physical_resumes"

    id = Column(Integer, primary_key=True, index=True)
    hr_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    candidate_name = Column(String, nullable=False, index=True)
    candidate_email = Column(String, nullable=True, index=True)
    candidate_phone = Column(String, nullable=True)
    target_job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    target_job_title = Column(String, nullable=True)
    physical_location = Column(String, nullable=True)  # e.g., "Cabinet A - Shelf 2 - Folder 12"
    submission_date = Column(DateTime, default=datetime.utcnow, nullable=True)
    filename = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    storage_path = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes
    file_type = Column(String, nullable=True)  # e.g., "application/pdf", "image/jpeg"
    status = Column(String, default="RECEIVED")  # RECEIVED, UNDER_REVIEW, SHORTLISTED, HIRED, ARCHIVED
    notes = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    target_job = relationship("JobDescription", foreign_keys=[target_job_id], lazy="selectin")
    hr_staff = relationship("User", foreign_keys=[hr_id], lazy="selectin")
