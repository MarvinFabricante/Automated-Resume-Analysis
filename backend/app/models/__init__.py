from app.models.user import User
from app.models.candidate import Candidate
from app.models.hr import HR
from app.models.admin import Admin
from app.models.resume import Resume
from app.models.job_description import JobDescription
from app.models.job_application import JobApplication
from app.models.notification import Notification
from app.models.message import Message, ArchivedConversation
from app.models.audit_log import AuditLog
from app.models.interview import Interview, InterviewLog, VoiceCallRecord
from app.models.system_config import SystemConfig, FormTemplate

__all__ = [
    "User",
    "Candidate",
    "HR",
    "Admin",
    "Resume",
    "JobDescription",
    "JobApplication",
    "Notification",
    "Message",
    "ArchivedConversation",
    "AuditLog",
    "Interview",
    "InterviewLog",
    "VoiceCallRecord",
    "SystemConfig",
    "FormTemplate"
]

