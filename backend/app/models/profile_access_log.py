from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.utils.database import Base

class ApplicantProfileAccessLog(Base):
    __tablename__ = "applicant_profile_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    applicant_email = Column(String, nullable=False, index=True)
    accessed_by = Column(String, nullable=False, index=True)
    purpose = Column(String, nullable=True, default="Profile Review")
    accessed_at = Column(DateTime, default=datetime.utcnow, index=True)
