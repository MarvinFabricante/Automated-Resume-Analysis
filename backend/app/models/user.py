from sqlalchemy import *

from app.utils.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    fullname = Column(String, nullable=False) 
    role = Column(String)
    profile_image_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    is_deactivated = Column(Boolean, default=False)
    deactivated_at = Column(DateTime, nullable=True)
    token_version = Column(Integer, default=0, nullable=False)
    is_anonymized = Column(Boolean, default=False)
    anonymized_at = Column(DateTime, nullable=True)
    anonymized_token = Column(String, nullable=True)
    email_hash = Column(String, nullable=True, index=True)
    is_online = Column(Boolean, default=False)
    last_active = Column(DateTime, nullable=True)
    google_credentials = Column(Text, nullable=True)
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    google_token_expiry = Column(DateTime, nullable=True)
    google_linked = Column(Boolean, default=False)

    __mapper_args__ = {
        "polymorphic_on": role,
        "polymorphic_identity": "user"
    }