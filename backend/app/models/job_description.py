from sqlalchemy import Column, Integer, String, Boolean, Enum, JSON, DateTime
import enum
from app.utils.database import Base
from sqlalchemy.orm import relationship

class JobType(str, enum.Enum):
    PART_TIME = "Part-Time"
    FULL_TIME = "Full-Time"
    FREELANCE = "Freelance"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"

class JobLifecycleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False) 
    job_title = Column(String, nullable=False)
    department = Column(String, nullable=False)
    job_type = Column(Enum(JobType), nullable=False)
    location = Column(String, nullable=False)
    salary_range = Column(String)
    description = Column(String, nullable=False)
    skills_requirements = Column(String)
    education_requirements = Column(String, nullable=True)
    certifications_requirements = Column(String, nullable=True)
    experience_requirements = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    status = Column(String, default="ACTIVE", nullable=False, index=True)  # DRAFT, ACTIVE, CLOSED, ARCHIVED
    closed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    # Per-job scoring priorities (fractions summing to 1.0). NULL = inherit the
    # global default weights from System Settings.
    scoring_weights = Column(JSON, nullable=True)

    # Relationships
    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")