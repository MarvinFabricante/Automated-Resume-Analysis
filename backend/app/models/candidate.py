from sqlalchemy import *
from sqlalchemy.orm import relationship

from app.models.user import User


class Candidate(User):
    __tablename__ = "candidates"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    resume_url = Column(String, nullable=True)
    experience_years = Column(Integer, default=0)
    
    # Profile Fields
    current_job_title = Column(String, nullable=True)
    current_company = Column(String, nullable=True)
    highest_degree = Column(String, nullable=True)
    university = Column(String, nullable=True)
    skills = Column(JSON, nullable=True) # Stored as a list of strings
    
    # Relationships
    resumes = relationship("Resume", back_populates="candidate")

    __mapper_args__ = {
        "polymorphic_identity": "CANDIDATE",
    }