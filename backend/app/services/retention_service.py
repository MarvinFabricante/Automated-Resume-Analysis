"""
Data retention, anonymization, and repeat-applicant hash utilities.

Retention policy:
  - Deactivated accounts are counted from `users.deactivated_at`.
  - Resolved applications (for active accounts or standalone applications) are
    counted from `job_applications.resolved_at` (fallback: `updated_at` / `created_at`).
  - Anyone with at least one active application is NEVER purged or anonymized.
  - Personal identifiers (name, email, phone, address, resume files, extracted text,
    personal data in form answers & messages) are scrubbed, while statistical/audit
    records (job_id, dates, status history, decision, match/component scores, weights)
    are preserved under a stable anonymous token (e.g. "Anonymized applicant #A1B2C3")
    and a salted one-way email hash for repeat-applicant detection.
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib.parse import unquote, urlparse

from sqlalchemy import func, or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.candidate_note import HRCandidateNote
from app.models.job_application import JobApplication
from app.models.message import Message, ApplicationThread, MessageReport
from app.models.resume import Resume
from app.models.retention_run_log import RetentionRunLog
from app.models.user import User

logger = logging.getLogger(__name__)

# Statuses that represent a resolved (non-active) application
RESOLVED_STATUS_SET: Set[str] = {
    "PASSED INITIAL INTERVIEW",
    "PASSED INITIAL INTERVIEW – ENDORSED FOR NEXT STAGE",
    "PASSED INITIAL INTERVIEW - ENDORSED FOR NEXT STAGE",
    "PASSED",
    "ACCEPTED",
    "NOT SELECTED",
    "NOT_SELECTED",
    "REJECTED",
    "PASSED_OVER",
    "ARCHIVED",
    "WITHDRAWN",
    "WITHDRAWN BY APPLICANT",
    "WITHDRAWN – HIRED ELSEWHERE IN COMPANY",
    "WITHDRAWN - HIRED ELSEWHERE IN COMPANY",
    "WITHDRAWN_HIRED_ELSEWHERE",
    "HIRED",
    "OFFER_ACCEPTED",
    "CLOSED",
}

WITHDRAWN_STATUS_SET: Set[str] = {
    "WITHDRAWN",
    "WITHDRAWN BY APPLICANT",
    "WITHDRAWN – HIRED ELSEWHERE IN COMPANY",
    "WITHDRAWN - HIRED ELSEWHERE IN COMPANY",
    "WITHDRAWN_HIRED_ELSEWHERE",
}


def is_application_resolved(status_value: Optional[str]) -> bool:
    norm = (status_value or "").strip().upper()
    return norm in RESOLVED_STATUS_SET


def is_application_active(status_value: Optional[str]) -> bool:
    return not is_application_resolved(status_value)


def normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def compute_email_hash(email: Optional[str]) -> Optional[str]:
    """Salted one-way HMAC-SHA256 hash of trimmed lowercase email."""
    clean = normalize_email(email)
    if not clean:
        return None
    salt = (
        os.getenv("EMAIL_HASH_SALT")
        or os.getenv("SECRET_KEY")
        or "mariwasa-recruitment-default-salt"
    )
    return hmac.new(salt.encode("utf-8"), clean.encode("utf-8"), hashlib.sha256).hexdigest()


def make_anonymous_token(seed_key: str) -> str:
    """Stable deterministic anonymous token, e.g. 'Anonymized applicant #A1B2C3'."""
    digest = hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:6].upper()
    return f"Anonymized applicant #{digest}"


async def delete_stored_file(file_ref: Optional[str], *, strict: bool = False) -> bool:
    """
    Remove a stored resume/profile file from local disk and/or Supabase Storage.
    Returns True if a file was deleted (or confirmed removed), False if nothing to delete.
    """
    if not file_ref or not isinstance(file_ref, str):
        return False

    cleaned = file_ref.strip()
    if not cleaned:
        return False

    deleted = False

    # Strip query strings (e.g. ?t=12345)
    parsed = urlparse(cleaned)
    raw_path = unquote(parsed.path or cleaned)

    # 1. Local filesystem check (absolute path, relative path, or under backend/uploads)
    candidate_paths: List[str] = []
    if cleaned.startswith("/") and os.path.isfile(cleaned):
        candidate_paths.append(cleaned)
    rel_no_leading = raw_path.lstrip("/")
    if rel_no_leading:
        candidate_paths.append(rel_no_leading)
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidate_paths.append(os.path.join(backend_dir, rel_no_leading))

    for local_path in candidate_paths:
        try:
            if local_path and os.path.isfile(local_path):
                os.remove(local_path)
                deleted = True
                logger.info(f"[Retention] Deleted local file: {local_path}")
                break
        except Exception as exc:
            logger.warning(f"[Retention] Could not delete local file {local_path}: {exc}")
            if strict:
                raise ValueError("We couldn't remove an old file. Please try again before starting fresh.") from exc

    # 2. Supabase Storage check (URL contains /storage/v1/object/ or looks like resumes/...)
    try:
        storage_path = None
        if "/storage/v1/object/" in cleaned:
            after = cleaned.split("/storage/v1/object/", 1)[1]
            # Format: public/<bucket>/<path> or <bucket>/<path>
            parts = after.split("/", 2)
            if parts[0] == "public" and len(parts) == 3:
                storage_path = unquote(parts[2].split("?", 1)[0])
            elif len(parts) >= 2:
                storage_path = unquote(parts[-1].split("?", 1)[0])
        elif cleaned.startswith("resumes/"):
            storage_path = cleaned

        if storage_path and os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            from app.utils.supabase_storage import delete_resume as sb_delete_resume
            if await sb_delete_resume(storage_path):
                deleted = True
            elif strict:
                raise ValueError("Old file removal could not be confirmed.")
        elif storage_path and not deleted and strict:
            raise ValueError("Old file storage is unavailable.")
    except Exception as exc:
        logger.warning(f"[Retention] Could not delete remote storage file {cleaned}: {exc}")
        if strict:
            raise ValueError("We couldn't remove an old file. Please try again before starting fresh.") from exc

    return deleted


async def user_has_active_application(
    db: AsyncSession,
    user_id: int,
    email: Optional[str] = None,
) -> bool:
    """Return True if the user has at least one active (non-resolved) application."""
    conditions = [JobApplication.user_id == user_id]
    norm_email = normalize_email(email)
    if norm_email:
        conditions.append(func.lower(JobApplication.candidate_email) == norm_email)

    res = await db.execute(select(JobApplication.status).where(or_(*conditions)))
    for (st,) in res.fetchall():
        if is_application_active(st):
            return True
    return False


async def _anonymize_single_application(
    db: AsyncSession,
    app: JobApplication,
    anon_token: str,
    email_hash_val: Optional[str],
    now: datetime,
    dry_run: bool = False,
    strict_files: bool = False,
) -> int:
    """
    Anonymize a single JobApplication while preserving audit & statistical fields:
    job_id, job_title, dates, status, status_history, scores, applied_weights.
    Returns count of deleted files.
    """
    files_deleted = 0
    if getattr(app, "is_anonymized", False):
        return 0

    if dry_run:
        return 1 if app.resume_url else 0

    if app.resume_url:
        if await delete_stored_file(app.resume_url, strict=strict_files):
            files_deleted += 1

    if app.profile_image_url:
        if await delete_stored_file(app.profile_image_url, strict=strict_files):
            files_deleted += 1

    # Preserve hash before scrubbing email
    computed_hash = email_hash_val or app.email_hash or compute_email_hash(
        app.candidate_email or app.contact_email or app.resume_email
    )

    app.candidate_name = anon_token
    app.candidate_email = f"{anon_token.lower().replace(' ', '_').replace('#', '')}@anonymized.local"
    app.resume_email = None
    app.contact_email = None
    app.phone = None
    app.location = None
    app.profile_image_url = None
    app.resume_url = None
    app.company = None
    app.college = None
    app.relevance = None
    app.skills = []
    app.degree = None
    app.certifications = None
    app.clarification_responses = None
    app.work_experiences = None
    app.education_entries = None
    app.matched_skills = None
    app.missing_skills = None
    app.relevant_experience = None
    app.experience_gaps = None
    app.candidate_degree = None
    app.candidate_certifications = None
    app.ai_summary = "[Anonymized per data retention policy]"
    app.strengths = None
    app.weaknesses = None
    app.recommendations = None
    app.hr_shortlist_notes = None
    app.review_flag_reason = None
    app.skills_reason = None
    app.experience_reason = None
    app.education_reason = None
    app.certifications_reason = None
    app.requirement_evaluations = None
    app.highest_educational_attainment = None
    app.hold_reason = None
    app.is_anonymized = True
    app.anonymized_token = anon_token
    app.email_hash = computed_hash
    app.messaging_closed_at = app.messaging_closed_at or now

    # Preserve state changes and dates, but remove applicant identifiers and free text.
    from app.models.status_history import ApplicationStatusHistory
    from app.models.interview import Interview, InterviewLog, VoiceCallRecord
    histories = await db.execute(select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app.id))
    for history in histories.scalars().all():
        if compute_email_hash(history.changed_by) == computed_hash:
            history.changed_by = anon_token
        history.reason = "[Anonymized per data retention policy]"
        history.can_undo = False
    interviews = await db.execute(select(Interview).where(Interview.job_application_id == app.id))
    for interview in interviews.scalars().all():
        interview.title = "Interview with anonymized applicant"
        interview.description = None
        interview.instructions = None
        interview.verbal_notes = None
        logs = await db.execute(select(InterviewLog).where(InterviewLog.interview_id == interview.id))
        for log in logs.scalars().all():
            log.details = "[Anonymized per data retention policy]"
        calls = await db.execute(select(VoiceCallRecord).where(VoiceCallRecord.interview_id == interview.id))
        for call in calls.scalars().all():
            call.phone_number = "[anonymized]"
            call.candidate_verbal_response = None
            call.notes = None
            call.call_sid = None

    # Scrub application thread messages, attachments, previews, and reports per retention rules
    thread_res = await db.execute(
        select(ApplicationThread).where(ApplicationThread.application_id == app.id)
    )
    thread = thread_res.scalar_one_or_none()
    if thread:
        thread.last_message_preview = "[Anonymized per data retention policy]"
        rep_res = await db.execute(select(MessageReport).where(MessageReport.thread_id == thread.id))
        for rep in rep_res.scalars().all():
            rep.reason = "[Anonymized per data retention policy]"

    app_msgs_res = await db.execute(
        select(Message).where(
            or_(
                Message.application_id == app.id,
                Message.thread_id == thread.id if thread else False,
            )
        )
    )
    for msg in app_msgs_res.scalars().all():
        if getattr(msg, "attachment_url", None):
            if await delete_stored_file(msg.attachment_url, strict=strict_files):
                files_deleted += 1
        msg.content = "[Anonymized per data retention policy]"
        msg.attachment_url = None
        msg.attachment_name = None
        msg.attachment_type = None
        msg.attachment_size = None

    return files_deleted


async def anonymize_user_and_records(
    db: AsyncSession,
    user: User,
    dry_run: bool = False,
    force_skip_active_check: bool = False,
    strict_files: bool = False,
) -> Dict[str, Any]:
    """
    Anonymize a user account and all associated applications, resumes, messages, and HR notes.
    Used by both the retention job AND the fresh-start-before-purge registration flow.
    """
    was_deactivated = bool(user.is_deactivated)
    if not dry_run:
        # Recovery and retention must never resurrect a concurrently purged account.
        await db.execute(select(User.id).where(User.id == user.id).with_for_update())
        await db.refresh(user)
        if was_deactivated and not user.is_deactivated:
            return {"anonymized": False, "skipped_already_anonymized": False,
                    "skipped_active": True, "applications_anonymized": 0, "files_deleted": 0}
    now = datetime.utcnow()
    if getattr(user, "is_anonymized", False):
        return {
            "anonymized": False,
            "skipped_already_anonymized": True,
            "skipped_active": False,
            "applications_anonymized": 0,
            "files_deleted": 0,
        }

    if not force_skip_active_check:
        if await user_has_active_application(db, user.id, user.email):
            return {
                "anonymized": False,
                "skipped_already_anonymized": False,
                "skipped_active": True,
                "applications_anonymized": 0,
                "files_deleted": 0,
            }

    norm_email = normalize_email(user.email)
    email_hash_val = user.email_hash or compute_email_hash(norm_email)
    anon_token = user.anonymized_token or make_anonymous_token(f"user:{user.id}:{email_hash_val or user.id}")

    # Find all applications belonging to this user
    app_conditions = [JobApplication.user_id == user.id]
    if norm_email:
        app_conditions.append(func.lower(JobApplication.candidate_email) == norm_email)
    apps_res = await db.execute(select(JobApplication).where(or_(*app_conditions)))
    apps = list(apps_res.scalars().all())

    # Find all resumes belonging to this user
    resumes_res = await db.execute(select(Resume).where(Resume.candidate_id == user.id))
    resumes = list(resumes_res.scalars().all())

    files_deleted = 0
    apps_anonymized = 0

    for app in apps:
        if not getattr(app, "is_anonymized", False):
            files_deleted += await _anonymize_single_application(
                db, app, anon_token, email_hash_val, now, dry_run=dry_run, strict_files=strict_files
            )
            apps_anonymized += 1

    if dry_run:
        for r in resumes:
            if r.file_url:
                files_deleted += 1
        if user.profile_image_url:
            files_deleted += 1
        return {
            "anonymized": True,
            "skipped_already_anonymized": False,
            "skipped_active": False,
            "applications_anonymized": apps_anonymized,
            "files_deleted": files_deleted,
            "anonymized_token": anon_token,
        }

    # Delete resume files & scrub resume extracted text/metadata
    for r in resumes:
        if r.file_url:
            if await delete_stored_file(r.file_url, strict=strict_files):
                files_deleted += 1
        r.filename = "[anonymized]"
        r.file_url = None
        r.parsed_data = None

    # Delete profile image file if stored
    if user.profile_image_url:
        if await delete_stored_file(user.profile_image_url, strict=strict_files):
            files_deleted += 1

    # Scrub candidate subclass profile PII
    cand_res = await db.execute(select(Candidate).where(Candidate.id == user.id))
    cand = cand_res.scalar_one_or_none()
    if cand:
        if cand.resume_url:
            if await delete_stored_file(cand.resume_url, strict=strict_files):
                files_deleted += 1
        cand.resume_url = None
        cand.current_job_title = None
        cand.current_company = None
        cand.highest_degree = None
        cand.university = None
        cand.skills = None
        cand.bio = None
        cand.phone = None
        cand.location = None

    # Scrub personal data in messages sent or received by this user
    msg_res = await db.execute(
        select(Message).where(or_(Message.sender_id == user.id, Message.receiver_id == user.id))
    )
    for msg in msg_res.scalars().all():
        if getattr(msg, "attachment_url", None):
            if await delete_stored_file(msg.attachment_url, strict=strict_files):
                files_deleted += 1
        msg.content = "[Anonymized per data retention policy]"
        msg.attachment_url = None
        msg.attachment_name = None
        msg.attachment_type = None
        msg.attachment_size = None

    # Scrub previews on threads owned by this user and any message reports
    user_threads_res = await db.execute(
        select(ApplicationThread).where(ApplicationThread.candidate_id == user.id)
    )
    for thr in user_threads_res.scalars().all():
        thr.last_message_preview = "[Anonymized per data retention policy]"

    user_reports_res = await db.execute(
        select(MessageReport).where(MessageReport.reporter_id == user.id)
    )
    for rep in user_reports_res.scalars().all():
        rep.reason = "[Anonymized per data retention policy]"

    # Scrub HR candidate notes containing PII
    if norm_email:
        notes_res = await db.execute(
            select(HRCandidateNote).where(func.lower(HRCandidateNote.candidate_email) == norm_email)
        )
        for note in notes_res.scalars().all():
            note.candidate_email = f"{anon_token.lower().replace(' ', '_').replace('#', '')}@anonymized.local"
            note.content = "[Anonymized per data retention policy]"

    from app.models.audit_log import AuditLog
    from app.models.notification import Notification
    from app.models.account_otp import AccountOTP
    from app.models.password_reset import PasswordReset
    from app.utils.auth import hash_password
    import secrets

    notices = await db.execute(select(Notification).where(or_(
        func.lower(func.trim(Notification.target_email)) == norm_email,
        Notification.message.contains(user.email, autoescape=True),
        Notification.message == f"{user.fullname} has joined the platform.",
    )))
    for notice in notices.scalars().all():
        notice.target_email = None
        notice.title = "Anonymized applicant activity"
        notice.message = "[Anonymized per data retention policy]"

    logs = await db.execute(select(AuditLog).where(or_(
        AuditLog.user_id == user.id,
        AuditLog.target.contains(user.email, autoescape=True),
        AuditLog.details.contains(user.email, autoescape=True),
        AuditLog.target.in_([f"Application ID: {app.id}" for app in apps]),
    )))
    for log in logs.scalars().all():
        log.target = anon_token
        log.details = "[Anonymized per data retention policy]"
        log.ip_address = None
    await db.execute(delete(AccountOTP).where(func.lower(func.trim(AccountOTP.email)) == norm_email))
    from app.utils.cache import delete_cache, clear_cache_pattern
    resets = await db.execute(select(PasswordReset).where(func.lower(func.trim(PasswordReset.email)) == norm_email))
    for reset in resets.scalars().all():
        await delete_cache(f"pwd_reset:{reset.token}")
        await db.delete(reset)
    await delete_cache(f"candidate:id:{user.id}")
    await clear_cache_pattern("candidate_profile:")
    await clear_cache_pattern("applicant_profile:")
    user.password = hash_password(secrets.token_urlsafe(48))

    # Scrub User PII and release the email address for potential fresh re-registration
    anon_slug = anon_token.lower().replace(" ", "_").replace("#", "")
    user.fullname = anon_token
    user.email = f"{anon_slug}_{user.id}@anonymized.local"
    user.phone = None
    user.location = None
    user.bio = None
    user.profile_image_url = None
    user.google_credentials = None
    user.google_access_token = None
    user.google_refresh_token = None
    user.google_token_expiry = None
    user.google_linked = False
    user.is_deactivated = True
    user.deactivated_at = user.deactivated_at or now
    user.is_archived = True
    user.is_online = False
    user.token_version = (user.token_version or 0) + 1
    user.is_anonymized = True
    user.anonymized_at = now
    user.anonymized_token = anon_token
    user.email_hash = email_hash_val

    return {
        "anonymized": True,
        "skipped_already_anonymized": False,
        "skipped_active": False,
        "applications_anonymized": apps_anonymized,
        "files_deleted": files_deleted,
        "anonymized_token": anon_token,
    }


async def run_retention_anonymization(
    db: AsyncSession,
    dry_run: bool = True,
    retention_months: Optional[int] = None,
    triggered_by: str = "manual",
) -> RetentionRunLog:
    """
    Execute the retention anonymization job (supports dry-run mode and is idempotent).
    - Counts retention from `users.deactivated_at` for deactivated accounts,
      and from `job_applications.resolved_at` (fallback: updated_at / created_at)
      for resolved applications.
    - NEVER purges/anonymizes any user who still has an active application.
    - Always records a RetentionRunLog row.
    """
    from app.services.system_config_service import system_config_service

    if retention_months is None:
        retention_months = await system_config_service.get_retention_months(db)

    now = datetime.utcnow()
    # Approximate calendar months safely (30 days * months, or exact relativedelta if available)
    cutoff = now - timedelta(days=int(retention_months) * 30)

    started_at = now
    candidates_evaluated = 0
    candidates_anonymized = 0
    applications_anonymized = 0
    files_deleted = 0
    skipped_active = 0
    processed_user_ids: Set[int] = set()
    details_list: List[Dict[str, Any]] = []

    try:
        # 1. Deactivated candidate accounts past the retention window (counted from deactivated_at)
        deactivated_res = await db.execute(
            select(User).where(
                User.role == "CANDIDATE",
                User.is_deactivated == True,
                User.is_anonymized == False,
                User.deactivated_at.isnot(None),
                User.deactivated_at <= cutoff,
            )
        )
        deactivated_users = list(deactivated_res.scalars().all())

        for u in deactivated_users:
            candidates_evaluated += 1
            processed_user_ids.add(u.id)
            res = await anonymize_user_and_records(db, u, dry_run=dry_run)
            if res["skipped_active"]:
                skipped_active += 1
                details_list.append({"user_id": u.id, "action": "skipped_active"})
            elif res["anonymized"]:
                candidates_anonymized += 1
                applications_anonymized += res["applications_anonymized"]
                files_deleted += res["files_deleted"]
                details_list.append({
                    "user_id": u.id,
                    "action": "would_anonymize" if dry_run else "anonymized",
                    "token": res.get("anonymized_token"),
                    "applications": res["applications_anonymized"],
                })

        # 2. Resolved applications past the retention window (counted from resolved_at / decision date)
        apps_res = await db.execute(
            select(JobApplication).where(
                JobApplication.is_anonymized == False,
            )
        )
        all_non_anon_apps = list(apps_res.scalars().all())

        # Group by owner (user_id or normalized email) so we never anonymize someone with an active app
        active_user_ids: Set[int] = set()
        active_emails: Set[str] = set()
        for app in all_non_anon_apps:
            if is_application_active(app.status):
                if app.user_id:
                    active_user_ids.add(app.user_id)
                norm = normalize_email(app.candidate_email)
                if norm:
                    active_emails.add(norm)

        for app in all_non_anon_apps:
            if not is_application_resolved(app.status):
                continue
            decision_date = app.resolved_at or app.updated_at or app.created_at
            if not decision_date or decision_date > cutoff:
                continue

            norm = normalize_email(app.candidate_email)
            if (app.user_id and app.user_id in processed_user_ids):
                continue

            # Never purge someone who currently has an active application
            if (app.user_id and app.user_id in active_user_ids) or (norm and norm in active_emails):
                skipped_active += 1
                details_list.append({"application_id": app.id, "action": "skipped_active"})
                continue

            candidates_evaluated += 1
            email_hash_val = app.email_hash or compute_email_hash(norm)
            anon_token = app.anonymized_token or make_anonymous_token(
                f"app:{app.user_id or norm or app.id}"
            )
            f_del = await _anonymize_single_application(
                db, app, anon_token, email_hash_val, now, dry_run=dry_run
            )
            applications_anonymized += 1
            files_deleted += f_del
            details_list.append({
                "application_id": app.id,
                "action": "would_anonymize" if dry_run else "anonymized",
                "token": anon_token,
            })

        run_log = RetentionRunLog(
            dry_run=dry_run,
            retention_months=int(retention_months),
            triggered_by=triggered_by,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            candidates_evaluated=candidates_evaluated,
            candidates_anonymized=candidates_anonymized,
            applications_anonymized=applications_anonymized,
            files_deleted=files_deleted,
            skipped_active=skipped_active,
            status="COMPLETED",
            details={"cutoff": cutoff.isoformat(), "items": details_list[:200]},
        )
        db.add(run_log)
        await db.commit()
        await db.refresh(run_log)
        return run_log

    except Exception as exc:
        logger.error(f"[Retention] Run failed: {exc}", exc_info=True)
        await db.rollback()
        fail_log = RetentionRunLog(
            dry_run=dry_run,
            retention_months=int(retention_months),
            triggered_by=triggered_by,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            status="FAILED",
            details={"error": str(exc)},
        )
        db.add(fail_log)
        await db.commit()
        await db.refresh(fail_log)
        return fail_log


async def has_previous_anonymized_application(
    db: AsyncSession,
    email: Optional[str],
    exclude_user_id: Optional[int] = None,
) -> bool:
    """
    Detect repeat applicants purely from the salted one-way email_hash on
    anonymized applications or anonymized user records — without exposing any PII.
    """
    ehash = compute_email_hash(email)
    if not ehash:
        return False

    app_q = select(JobApplication.id).where(
        JobApplication.email_hash == ehash,
        JobApplication.is_anonymized == True,
    ).limit(1)
    if (await db.execute(app_q)).first() is not None:
        return True

    user_conditions = [
        User.email_hash == ehash,
        User.is_anonymized == True,
    ]
    if exclude_user_id is not None:
        user_conditions.append(User.id != exclude_user_id)
    user_q = select(User.id).where(*user_conditions).limit(1)
    return (await db.execute(user_q)).first() is not None


async def get_retention_run_logs(db: AsyncSession, limit: int = 25) -> List[RetentionRunLog]:
    res = await db.execute(
        select(RetentionRunLog).order_by(RetentionRunLog.started_at.desc()).limit(limit)
    )
    return list(res.scalars().all())
