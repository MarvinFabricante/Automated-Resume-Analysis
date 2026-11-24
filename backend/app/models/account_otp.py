from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.utils.database import Base


class AccountOTP(Base):
    """
    Stores one-time verification codes (6-digit, 10-minute expiry, limited attempts)
    for account reactivation and account deletion confirmation.
    """
    __tablename__ = "account_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    purpose = Column(String, nullable=False, index=True)  # "reactivate" | "delete_account"
    code_hash = Column(String, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
