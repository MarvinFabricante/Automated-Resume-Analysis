from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.utils.database import Base

class HRCandidateNote(Base):
    __tablename__ = "hr_candidate_notes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_email = Column(String, nullable=False, index=True)
    author_email = Column(String, nullable=False)
    author_name = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
