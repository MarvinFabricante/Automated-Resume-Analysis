from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.database import Base

class ShortlistRoster(Base):
    __tablename__ = "shortlist_rosters"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    created_by = Column(String, nullable=False) # HR email
    notes = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("JobDescription", lazy="selectin")
    items = relationship("ShortlistRosterItem", back_populates="roster", cascade="all, delete-orphan", lazy="selectin")

class ShortlistRosterItem(Base):
    __tablename__ = "shortlist_roster_items"

    id = Column(Integer, primary_key=True, index=True)
    roster_id = Column(Integer, ForeignKey("shortlist_rosters.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False, index=True)
    stage = Column(String, nullable=False, default="Shortlisted", index=True) # Shortlisted, Interview Scheduled, Interviewed, Passed initial interview, Not selected
    added_by = Column(String, nullable=False) # HR email
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    roster = relationship("ShortlistRoster", back_populates="items")
    application = relationship("JobApplication", lazy="selectin")
