from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from datetime import datetime
from app.utils.database import Base


class SystemConfig(Base):
    """
    Stores system-wide configuration parameters that admins can manage
    through the System Configuration panel.
    Each row represents a single config entry identified by a unique `key`.
    """
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)          # JSON-encoded value
    category = Column(String, nullable=False)      # e.g., "matching", "roles", "forms"
    description = Column(String, nullable=True)
    updated_by = Column(Integer, nullable=True)    # admin user_id
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class FormTemplate(Base):
    """
    Stores custom application form templates that admins can attach to jobs.
    """
    __tablename__ = "form_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    fields = Column(JSON, nullable=False, default=list)  # list of field definitions
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
