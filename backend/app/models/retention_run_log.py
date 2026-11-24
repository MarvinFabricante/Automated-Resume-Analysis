from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from app.utils.database import Base


class RetentionRunLog(Base):
    """
    Audit log of every data retention anonymization run (both dry-run and live).
    """
    __tablename__ = "retention_run_logs"

    id = Column(Integer, primary_key=True, index=True)
    dry_run = Column(Boolean, default=True, nullable=False)
    retention_months = Column(Integer, default=12, nullable=False)
    triggered_by = Column(String, default="celery_beat", nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    candidates_evaluated = Column(Integer, default=0, nullable=False)
    candidates_anonymized = Column(Integer, default=0, nullable=False)
    applications_anonymized = Column(Integer, default=0, nullable=False)
    files_deleted = Column(Integer, default=0, nullable=False)
    skipped_active = Column(Integer, default=0, nullable=False)
    status = Column(String, default="SUCCESS", nullable=False)
    details = Column(JSON, nullable=True)
