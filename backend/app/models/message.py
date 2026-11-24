from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base


class ApplicationThread(Base):
    """
    One HR-started conversation thread per job application (position).
    Only HR or Admin may create a thread or send the first message.
    """
    __tablename__ = "application_threads"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(
        Integer,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    candidate_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    started_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_message_preview = Column(String(300), nullable=True)

    job_application = relationship("JobApplication", foreign_keys=[application_id], lazy="selectin")
    candidate = relationship("User", foreign_keys=[candidate_id], lazy="selectin")
    started_by = relationship("User", foreign_keys=[started_by_id], lazy="selectin")
    messages = relationship(
        "Message",
        back_populates="thread",
        order_by="Message.timestamp",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("application_threads.id", ondelete="CASCADE"), nullable=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(Integer, ForeignKey("job_applications.id", ondelete="SET NULL"), nullable=True, index=True)
    message_type = Column(String, default="general", nullable=True) # update, instructions, announcement, reminder, general
    content = Column(Text, nullable=False)
    attachment_url = Column(String, nullable=True)
    attachment_name = Column(String, nullable=True)
    attachment_type = Column(String, nullable=True)
    attachment_size = Column(Integer, nullable=True)
    is_reported = Column(Boolean, default=False)
    email_digest_sent_at = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", foreign_keys=[sender_id], lazy="selectin")
    receiver = relationship("User", foreign_keys=[receiver_id], lazy="selectin")
    job_application = relationship("JobApplication", foreign_keys=[application_id], lazy="selectin")
    thread = relationship("ApplicationThread", back_populates="messages", foreign_keys=[thread_id])


class MessageReport(Base):
    __tablename__ = "message_reports"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(Integer, ForeignKey("application_threads.id", ondelete="CASCADE"), nullable=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    status = Column(String, default="OPEN", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", foreign_keys=[message_id])
    reporter = relationship("User", foreign_keys=[reporter_id])


class ArchivedConversation(Base):
    __tablename__ = "archived_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    archived_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'contact_id', name='uq_user_contact_archive'),
    )

    user = relationship("User", foreign_keys=[user_id])
    contact = relationship("User", foreign_keys=[contact_id])


class ArchivedThread(Base):
    __tablename__ = "archived_threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(Integer, ForeignKey("application_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    archived_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'thread_id', name='uq_user_thread_archive'),
    )

    user = relationship("User", foreign_keys=[user_id])
    thread = relationship("ApplicationThread", foreign_keys=[thread_id])
