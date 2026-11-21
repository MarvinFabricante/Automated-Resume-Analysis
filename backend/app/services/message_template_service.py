"""
Notification message template service for Email and SMS notifications.

Provides default detail-rich templates, safe placeholder substitution, and
persistent admin/HR customization backed by SystemConfig (with Redis caching).
"""

import copy
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.system_config_repository import SystemConfigRepository

logger = logging.getLogger(__name__)

TEMPLATE_CONFIG_KEY = "notification_message_templates"
TEMPLATE_CONFIG_CATEGORY = "notification_templates"
COMPANY_NAME = "Mariwasa Siam Ceramics, Inc."

_PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z0-9_]+)\}")

INTERVIEW_PLACEHOLDERS = [
    "candidate_name",
    "candidate_email",
    "job_title",
    "interview_title",
    "date",
    "start_time",
    "end_time",
    "time_range",
    "interviewer_name",
    "interviewer_email",
    "location",
    "meeting_link",
    "location_line",
    "notes",
    "notes_line",
    "reason",
    "reason_line",
    "email_note",
    "company_name",
]

STATUS_PLACEHOLDERS = [
    "candidate_name",
    "job_title",
    "status",
    "notes",
    "company_name",
]

DEFAULT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "interview_scheduled": {
        "key": "interview_scheduled",
        "label": "Interview Scheduled",
        "description": "Sent to candidates via Email & SMS when HR schedules an interview.",
        "supports_sms": True,
        "placeholders": list(INTERVIEW_PLACEHOLDERS),
        "email_subject": "Interview Scheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics",
        "email_message": (
            "We are pleased to inform you that an interview has been scheduled for your application "
            "for the position of {job_title} at {company_name}. Please review the complete schedule "
            "information below and be ready at least 10 minutes before your scheduled time."
        ),
        "sms_message": (
            "Mariwasa HR: Hello {candidate_name}! Your {interview_title} for {job_title} is scheduled on "
            "{date} at {time_range} with {interviewer_name}.{location_line}{notes_line}{email_note} "
            "Please be ready 10 mins early. Thank you!"
        ),
    },
    "interview_rescheduled": {
        "key": "interview_rescheduled",
        "label": "Interview Rescheduled",
        "description": "Sent via Email & SMS when HR moves an interview to a new date or time.",
        "supports_sms": True,
        "placeholders": list(INTERVIEW_PLACEHOLDERS),
        "email_subject": "Rescheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics",
        "email_message": (
            "Please be advised that your interview schedule for the position of {job_title} has been updated. "
            "Below are your new interview details and venue/meeting information."
        ),
        "sms_message": (
            "Mariwasa HR Update: Hello {candidate_name}! Your {interview_title} for {job_title} has been "
            "rescheduled to {date} at {time_range} with {interviewer_name}.{location_line}{notes_line}{email_note} "
            "Thank you!"
        ),
    },
    "interview_canceled": {
        "key": "interview_canceled",
        "label": "Interview Canceled",
        "description": "Sent via Email & SMS when HR cancels a scheduled interview session.",
        "supports_sms": True,
        "placeholders": list(INTERVIEW_PLACEHOLDERS),
        "email_subject": "Canceled: {interview_title} - {job_title} | Mariwasa Siam Ceramics",
        "email_message": (
            "Please be advised that the scheduled interview for the position of {job_title} on {date} "
            "at {time_range} has been canceled. The calendar event has been removed from all participant schedules."
        ),
        "sms_message": (
            "Mariwasa HR Update: Hello {candidate_name}, your {interview_title} for {job_title} scheduled on "
            "{date} at {time_range} has been canceled.{reason_line}{email_note} Thank you."
        ),
    },
    "candidate_rescheduled": {
        "key": "candidate_rescheduled",
        "label": "Candidate Self-Reschedule Confirmation",
        "description": "Sent via Email & SMS after a candidate confirms a rescheduled slot.",
        "supports_sms": True,
        "placeholders": list(INTERVIEW_PLACEHOLDERS),
        "email_subject": "Rescheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics",
        "email_message": (
            "Your interview reschedule for the position of {job_title} has been confirmed for {date} "
            "at {time_range}. Please review your updated schedule details below."
        ),
        "sms_message": (
            "Mariwasa HR Update: Hello {candidate_name}! Your new {interview_title} schedule for {job_title} "
            "on {date} at {time_range} with {interviewer_name} is confirmed.{location_line}{email_note} Thank you!"
        ),
    },
    "application_status_reviewed": {
        "key": "application_status_reviewed",
        "label": "Application Status: Under Review",
        "description": "Email sent when an application moves to Reviewed / Under Review.",
        "supports_sms": False,
        "placeholders": list(STATUS_PLACEHOLDERS),
        "email_subject": "Application Status Update: {job_title} | Mariwasa Siam Ceramics",
        "email_message": (
            "Thank you for applying for the position of {job_title} at {company_name}. "
            "We are pleased to inform you that our Talent Acquisition team has officially reviewed your resume and credentials."
        ),
        "sms_message": "",
    },
    "application_status_shortlisted": {
        "key": "application_status_shortlisted",
        "label": "Application Status: Shortlisted / Accepted",
        "description": "Email sent when an application is shortlisted or accepted.",
        "supports_sms": False,
        "placeholders": list(STATUS_PLACEHOLDERS),
        "email_subject": "Congratulations: Application Shortlisted for {job_title} | Mariwasa Siam Ceramics",
        "email_message": (
            "We are thrilled to inform you that following a comprehensive evaluation of your background and credentials, "
            "your application for the position of {job_title} at {company_name} has been officially accepted and shortlisted!"
        ),
        "sms_message": "",
    },
    "application_status_rejected": {
        "key": "application_status_rejected",
        "label": "Application Status: Not Selected / Rejected",
        "description": "Email sent when an application is marked as Not Selected / Rejected.",
        "supports_sms": False,
        "placeholders": list(STATUS_PLACEHOLDERS),
        "email_subject": "Application Update: {job_title} | Mariwasa Siam Ceramics",
        "email_message": (
            "Thank you for your interest in joining {company_name} and for the time, energy, and dedication "
            "you invested in applying for the position of {job_title}."
        ),
        "sms_message": "",
    },
}


def is_real_email(email: Optional[str]) -> bool:
    """Return True if email is non-empty and not an internal .local placeholder."""
    clean = (email or "").strip()
    return bool(clean and "@" in clean and not clean.lower().endswith(".local"))


def render_template(template_text: str, context: Dict[str, Any]) -> str:
    """Safely substitute `{key}` placeholders in `template_text` without raising on unknown keys."""
    if not template_text:
        return ""

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        if key in context:
            val = context[key]
            return "" if val is None else str(val)
        return match.group(0)

    rendered = _PLACEHOLDER_PATTERN.sub(_replace, template_text)
    rendered = re.sub(r"[ \t]{2,}", " ", rendered)
    rendered = re.sub(r"\s+([.,!?])", r"\1", rendered)
    return rendered.strip()


def build_interview_template_context(
    *,
    candidate_name: str,
    job_title: str,
    interview_title: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    interviewer_name: Optional[str] = None,
    interviewer_email: Optional[str] = None,
    location: Optional[str] = None,
    meeting_link: Optional[str] = None,
    notes: Optional[str] = None,
    reason: Optional[str] = None,
    candidate_email: Optional[str] = None,
) -> Dict[str, str]:
    """Build a complete placeholder context dictionary for interview emails and SMS messages."""
    formatted_date = start_time.strftime("%A, %b %d, %Y")
    start_str = start_time.strftime("%I:%M %p")
    end_str = end_time.strftime("%I:%M %p") if end_time else ""
    time_range = f"{start_str} - {end_str}" if end_str else start_str

    clean_location = (location or "").strip()
    clean_link = (meeting_link or "").strip()
    clean_notes = (notes or "").strip()
    clean_reason = (reason or "").strip()
    clean_cand_email = (candidate_email or "").strip() if is_real_email(candidate_email) else ""
    interviewer_display = (interviewer_name or "").strip() or "Mariwasa HR Panel"
    interviewer_email_display = (interviewer_email or "").strip()

    if clean_location and clean_link:
        location_line = f" Venue: {clean_location} | Meeting Link: {clean_link}."
    elif clean_link:
        location_line = f" Meeting Link: {clean_link}."
    elif clean_location:
        location_line = f" Venue: {clean_location}."
    else:
        location_line = ""

    if clean_notes:
        trimmed_notes = clean_notes if len(clean_notes) <= 140 else clean_notes[:137] + "..."
        notes_line = f" Notes: {trimmed_notes}."
    else:
        notes_line = ""

    if clean_reason:
        trimmed_reason = clean_reason if len(clean_reason) <= 140 else clean_reason[:137] + "..."
        reason_line = f" Reason: {trimmed_reason}."
    else:
        reason_line = ""

    email_note = f" Full details sent to {clean_cand_email}." if clean_cand_email else ""

    return {
        "candidate_name": (candidate_name or "Candidate").strip(),
        "candidate_email": clean_cand_email,
        "job_title": (job_title or "Position").strip(),
        "interview_title": (interview_title or "Interview").strip(),
        "date": formatted_date,
        "start_time": start_str,
        "end_time": end_str,
        "time_range": time_range,
        "interviewer_name": interviewer_display,
        "interviewer_email": interviewer_email_display,
        "location": clean_location or "To be confirmed by HR",
        "meeting_link": clean_link,
        "location_line": location_line,
        "notes": clean_notes,
        "notes_line": notes_line,
        "reason": clean_reason,
        "reason_line": reason_line,
        "email_note": email_note,
        "company_name": COMPANY_NAME,
    }


def _merge_with_defaults(saved_overrides: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    merged = copy.deepcopy(DEFAULT_TEMPLATES)
    if not isinstance(saved_overrides, dict):
        return merged

    for key, override in saved_overrides.items():
        if key in merged and isinstance(override, dict):
            for field in ("email_subject", "email_message", "sms_message"):
                if field in override and override[field] is not None:
                    merged[key][field] = str(override[field])
    return merged


async def get_all_templates(db: Optional[AsyncSession] = None) -> Dict[str, Dict[str, Any]]:
    """Retrieve all notification templates merged with persisted SystemConfig overrides."""
    if db is None:
        return copy.deepcopy(DEFAULT_TEMPLATES)

    try:
        cfg = await SystemConfigRepository.get_config_by_key(db, TEMPLATE_CONFIG_KEY)
        if cfg and getattr(cfg, "value", None):
            parsed = json.loads(cfg.value)
            return _merge_with_defaults(parsed)
    except Exception as exc:
        logger.warning(f"Could not load saved notification templates, using defaults: {exc}")

    return copy.deepcopy(DEFAULT_TEMPLATES)


async def get_template(db: Optional[AsyncSession], key: str) -> Dict[str, Any]:
    """Retrieve a single notification template by key, falling back to default."""
    all_templates = await get_all_templates(db)
    if key in all_templates:
        return all_templates[key]
    return copy.deepcopy(DEFAULT_TEMPLATES.get(key, {}))


async def update_templates(
    db: AsyncSession,
    updates: Dict[str, Dict[str, Optional[str]]],
    user_id: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """Persist editable template overrides into SystemConfig."""
    current = await get_all_templates(db)
    overrides_to_save: Dict[str, Dict[str, str]] = {}

    for key, tmpl in current.items():
        patch = updates.get(key) if isinstance(updates, dict) else None
        entry = {
            "email_subject": tmpl.get("email_subject", ""),
            "email_message": tmpl.get("email_message", ""),
            "sms_message": tmpl.get("sms_message", ""),
        }
        if isinstance(patch, dict):
            for field in ("email_subject", "email_message", "sms_message"):
                if field in patch and patch[field] is not None:
                    entry[field] = str(patch[field]).strip()
        overrides_to_save[key] = entry

    await SystemConfigRepository.upsert_config(
        db=db,
        key=TEMPLATE_CONFIG_KEY,
        value=json.dumps(overrides_to_save),
        category=TEMPLATE_CONFIG_CATEGORY,
        description="Customizable Email and SMS notification message templates",
        updated_by=user_id,
    )
    return _merge_with_defaults(overrides_to_save)


async def reset_templates(
    db: AsyncSession,
    template_key: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """Reset one or all notification templates back to system defaults."""
    if template_key and template_key in DEFAULT_TEMPLATES:
        current = await get_all_templates(db)
        current[template_key] = copy.deepcopy(DEFAULT_TEMPLATES[template_key])
        overrides = {
            k: {
                "email_subject": v.get("email_subject", ""),
                "email_message": v.get("email_message", ""),
                "sms_message": v.get("sms_message", ""),
            }
            for k, v in current.items()
        }
        await SystemConfigRepository.upsert_config(
            db=db,
            key=TEMPLATE_CONFIG_KEY,
            value=json.dumps(overrides),
            category=TEMPLATE_CONFIG_CATEGORY,
            description="Customizable Email and SMS notification message templates",
            updated_by=user_id,
        )
        return _merge_with_defaults(overrides)

    await SystemConfigRepository.delete_config(db, TEMPLATE_CONFIG_KEY)
    return copy.deepcopy(DEFAULT_TEMPLATES)
