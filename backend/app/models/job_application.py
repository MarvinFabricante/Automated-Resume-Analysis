from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSON, DOUBLE_PRECISION
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import TYPE_CHECKING
from app.utils.database import Base

if TYPE_CHECKING:
    from app.models.job_description import JobDescription

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    
    # Candidate details
    candidate_name = Column(String, nullable=False)
    candidate_email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    
    # Parsed resume and form data
    job_title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    relevance = Column(String, nullable=True)
    degree = Column(String, nullable=True)
    college = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)
    match_score = Column(DOUBLE_PRECISION, nullable=True) # Percentage score 0-100
    skills_score = Column(DOUBLE_PRECISION, nullable=True)
    experience_score = Column(DOUBLE_PRECISION, nullable=True)
    education_score = Column(DOUBLE_PRECISION, nullable=True)
    profile_image_url = Column(String, nullable=True)
    
    # Interpretation / Reasoning
    skills_reason = Column(String, nullable=True)
    experience_reason = Column(String, nullable=True)
    education_reason = Column(String, nullable=True)
    
    status = Column(String, default="PENDING") # PENDING, REVIEWED, REJECTED, ACCEPTED
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("JobDescription", back_populates="applications")
