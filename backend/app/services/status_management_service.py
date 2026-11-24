import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models.job_application import JobApplication
from app.models.status_history import ApplicationStatusHistory
from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
from app.models.candidate_note import HRCandidateNote
from app.models.profile_access_log import ApplicantProfileAccessLog
from app.models.job_description import JobDescription
from app.models.interview import Interview
from app.services.notification_service import create_notification
from app.utils.cache import clear_cache_pattern

logger = logging.getLogger(__name__)

# Config constant per requirement: 8 seconds minimum view duration
MIN_VIEW_DURATION_SECONDS = 8.0

# Canonical status order index
STATUS_RANK = {
    "SUBMITTED": 1,
    "PENDING": 1,
    "UNDER REVIEW": 2,
    "REVIEWED": 2,
    "SCREENED": 2,
    "SHORTLISTED": 3,
    "SHORTLIST": 3,
    "INTERVIEW SCHEDULED": 4,
    "TECHNICAL INTERVIEW": 4,
    "INTERVIEW": 4,
    "INTERVIEWED": 5,
    "ON HOLD": 3,
    "ON_HOLD": 3,
    "NOT SELECTED": 0,
    "NOT_SELECTED": 0,
    "REJECTED": 0,
    "ARCHIVED": 0,
    "WITHDRAWN": 0,
    "WITHDRAWN BY APPLICANT": 0,
    "WITHDRAWN – HIRED ELSEWHERE IN COMPANY": 0,
    "WITHDRAWN - HIRED ELSEWHERE IN COMPANY": 0,
    "WITHDRAWN_HIRED_ELSEWHERE": 0,
    "PASSED INITIAL INTERVIEW": 6,
    "PASSED INITIAL INTERVIEW – ENDORSED FOR NEXT STAGE": 6,
    "PASSED": 6,
    "ACCEPTED": 6,
}

RESOLVED_CANONICAL_STATUSES = {
    "Passed initial interview",
    "Not Selected",
    "Withdrawn by applicant",
    "Withdrawn – hired elsewhere in company",
}

WITHDRAWN_CANONICAL_STATUSES = {
    "Withdrawn by applicant",
    "Withdrawn – hired elsewhere in company",
}


def normalize_status(status: Optional[str]) -> str:
    if not status:
        return "Submitted"
    s = status.strip().upper()
    if s in ("SUBMITTED", "PENDING"):
        return "Submitted"
    if s in ("UNDER REVIEW", "REVIEWED", "SCREENED"):
        return "Under Review"
    if s in ("SHORTLISTED", "SHORTLIST"):
        return "Shortlisted"
    if s in ("INTERVIEW SCHEDULED", "TECHNICAL INTERVIEW", "INTERVIEW"):
        return "Interview Scheduled"
    if s == "INTERVIEWED":
        return "Interviewed"
    if s in ("ON HOLD", "ON_HOLD"):
        return "On Hold"
    if s in ("NOT SELECTED", "NOT_SELECTED", "REJECTED", "ARCHIVED", "PASSED_OVER"):
        return "Not Selected"
    if s in (
        "WITHDRAWN – HIRED ELSEWHERE IN COMPANY",
        "WITHDRAWN - HIRED ELSEWHERE IN COMPANY",
        "WITHDRAWN_HIRED_ELSEWHERE",
    ):
        return "Withdrawn – hired elsewhere in company"
    if s in ("WITHDRAWN", "WITHDRAWN BY APPLICANT"):
        return "Withdrawn by applicant"
    if s in (
        "PASSED INITIAL INTERVIEW",
        "PASSED INITIAL INTERVIEW – ENDORSED FOR NEXT STAGE",
        "PASSED INITIAL INTERVIEW - ENDORSED FOR NEXT STAGE",
        "PASSED",
        "ACCEPTED",
    ):
        return "Passed initial interview"
    return status.title()


def get_status_display_label(status: Optional[str]) -> str:
    norm = normalize_status(status)
    if norm == "Passed initial interview":
        return "Passed Initial Interview – Endorsed for next stage"
    if norm == "Not Selected":
        return "Not selected"
    return norm


def is_resolved_status(status: Optional[str]) -> bool:
    return normalize_status(status) in RESOLVED_CANONICAL_STATUSES


def is_withdrawn_status(status: Optional[str]) -> bool:
    return normalize_status(status) in WITHDRAWN_CANONICAL_STATUSES


def is_passed_status(status: Optional[str]) -> bool:
    return normalize_status(status) == "Passed initial interview"

async def record_status_history(
    db: AsyncSession,
    application_id: int,
    old_status: Optional[str],
    new_status: str,
    changed_by: str = "auto",
    change_type: str = "auto",
    reason: Optional[str] = None,
    can_undo: bool = True
) -> ApplicationStatusHistory:
    history = ApplicationStatusHistory(
        application_id=application_id,
        old_status=normalize_status(old_status) if old_status else None,
        new_status=normalize_status(new_status),
        changed_by=changed_by,
        change_type=change_type,
        reason=reason,
        can_undo=can_undo,
        created_at=datetime.utcnow()
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history

async def get_application_history(db: AsyncSession, application_id: int) -> List[ApplicationStatusHistory]:
    stmt = (
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application_id)
        .order_by(ApplicationStatusHistory.created_at.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def apply_application_status_change(
    db: AsyncSession,
    application: JobApplication,
    new_status: str,
    changed_by: str = "auto",
    change_type: str = "auto",
    reason: Optional[str] = None,
    send_email: bool = True,
    send_notification: bool = True,
    custom_email_subject: Optional[str] = None,
    custom_email_message: Optional[str] = None,
) -> JobApplication:
    old_raw = application.status
    old_norm = normalize_status(old_raw)
    new_norm = normalize_status(new_status)

    if old_norm == new_norm:
        return application

    now = datetime.utcnow()
    # Save to application
    application.status = new_norm.upper()
    if new_norm in RESOLVED_CANONICAL_STATUSES:
        application.resolved_at = now
    else:
        # If resumed or reverted back to an active stage, clear resolved_at
        application.resolved_at = None

    if new_norm in WITHDRAWN_CANONICAL_STATUSES:
        application.messaging_closed_at = now

    if new_norm == "On Hold" and reason:
        application.hold_reason = reason
    elif new_norm != "On Hold":
        application.hold_reason = None

    await db.commit()
    await db.refresh(application)

    # Record history
    await record_status_history(
        db=db,
        application_id=application.id,
        old_status=old_norm,
        new_status=new_norm,
        changed_by=changed_by,
        change_type=change_type,
        reason=reason,
        can_undo=(change_type == "auto" and new_norm == "Under Review"),
    )

    # Resolve recipient email and job title safely without triggering lazy-load MissingGreenlet
    target_email = application.candidate_email
    if getattr(application, "user_id", None):
        try:
            from app.models.user import User
            u_res = await db.execute(select(User.email).where(User.id == application.user_id))
            acc_email = u_res.scalar_one_or_none()
            if acc_email:
                target_email = acc_email.strip()
        except Exception:
            pass

    job_title = getattr(application, "job_title", None) or "Position"
    try:
        loaded_job = getattr(application, "__dict__", {}).get("job")
        if loaded_job and getattr(loaded_job, "job_title", None):
            job_title = loaded_job.job_title
        elif application.job_id:
            j_res = await db.execute(
                select(JobDescription.job_title).where(JobDescription.id == application.job_id)
            )
            fetched_title = j_res.scalar_one_or_none()
            if fetched_title:
                job_title = fetched_title
    except Exception:
        pass

    # Send in-system notification to applicant once per distinct status change
    if send_notification and target_email:
        try:
            display_label = get_status_display_label(new_norm)
            if new_norm == "Passed initial interview":
                notif_title = "Passed Initial Interview – Endorsed for next stage"
                notif_msg = (
                    f"Congratulations! Your application for {job_title} passed the initial interview and has been endorsed for the next stage. "
                    "HR will contact you outside the system for the next steps."
                )
            elif new_norm == "Not Selected":
                notif_title = f"Application Update: {job_title}"
                reason_suffix = f" ({reason})" if reason else ""
                notif_msg = (
                    f"Your application for {job_title} was marked as Not selected{reason_suffix}. "
                    "Your feedback report remains viewable in your portal."
                )
            elif new_norm == "On Hold":
                notif_title = f"Application Placed On Hold: {job_title}"
                notif_msg = (
                    f"Your application for {job_title} has been placed On Hold"
                    + (f": {reason}" if reason else ". HR will keep you updated.")
                )
            elif new_norm in WITHDRAWN_CANONICAL_STATUSES:
                notif_title = f"Application Withdrawn: {job_title}"
                notif_msg = (
                    f"Your application for {job_title} is now '{display_label}'."
                    + (f" Reason: {reason}." if reason else "")
                )
            else:
                notif_title = f"Application Status Updated: {display_label}"
                notif_msg = f"Your application for {job_title} has moved from {old_norm} to {display_label}."

            await create_notification(
                db=db,
                title=notif_title,
                message=notif_msg,
                type="status_update",
                target_role="CANDIDATE",
                target_email=target_email,
                sender_role="SYSTEM" if change_type == "auto" else "HR",
            )
        except Exception as exc:
            logger.warning(f"Could not create in-app notification for {target_email}: {exc}")

    # Dispatch email only once per distinct status change (always to account login email when linked)
    if send_email and target_email:
        try:
            from app.services.email_service import send_application_status_update_email
            await send_application_status_update_email(
                to_email=target_email,
                candidate_name=application.candidate_name or "Candidate",
                job_title=job_title,
                new_status=new_norm,
                previous_status=old_norm,
                notes=reason,
                custom_subject=custom_email_subject,
                custom_message=custom_email_message,
                db=db,
            )
        except Exception as e:
            logger.warning(f"Could not send status email to {target_email}: {e}")

    # Invalidate cache
    try:
        await clear_cache_pattern("job_applications*")
        await clear_cache_pattern("all_apps*")
        await clear_cache_pattern("job_apps*")
    except Exception:
        pass

    return application

async def handle_application_viewed_event(
    db: AsyncSession,
    application_id: int,
    view_duration_seconds: float,
    visible_focused: bool,
    engaged: bool,
    user_email: str = "HR"
) -> Dict[str, Any]:
    """
    Automatic Status Update: Submitted -> Under Review
    Validates:
    - View stayed open >= 8 seconds
    - Tab was visible and focused
    - At least one sign of engagement occurred
    - Only moves forward from Submitted; does NOT overwrite Shortlisted, Interviewed, etc.
    """
    stmt = select(JobApplication).where(JobApplication.id == application_id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        logger.warning(f"[AutoStatus] App #{application_id} viewed event rejected: reason=not_found")
        return {
            "success": False,
            "changed": False,
            "reason": "not_found",
            "message": f"Application #{application_id} not found"
        }

    current_norm = normalize_status(app.status)

    # Validation of the view event
    if view_duration_seconds < MIN_VIEW_DURATION_SECONDS:
        logger.info(f"[AutoStatus] App #{application_id} viewed event: changed=False, reason=too_short ({view_duration_seconds:.1f}s < {MIN_VIEW_DURATION_SECONDS}s)")
        return {
            "success": False,
            "changed": False,
            "reason": "too_short",
            "status": current_norm,
            "message": f"View duration {view_duration_seconds:.1f}s is less than required {MIN_VIEW_DURATION_SECONDS}s"
        }

    if not visible_focused:
        logger.info(f"[AutoStatus] App #{application_id} viewed event: changed=False, reason=not_visible")
        return {
            "success": False,
            "changed": False,
            "reason": "not_visible",
            "status": current_norm,
            "message": "View ignored: browser tab was not active/focused"
        }

    if not engaged:
        logger.info(f"[AutoStatus] App #{application_id} viewed event: changed=False, reason=no_engagement")
        return {
            "success": False,
            "changed": False,
            "reason": "no_engagement",
            "status": current_norm,
            "message": "View ignored: no user interaction or engagement detected"
        }

    # Only automatic change allowed here is Submitted -> Under Review
    if current_norm == "Submitted":
        updated_app = await apply_application_status_change(
            db=db,
            application=app,
            new_status="Under Review",
            changed_by=user_email,
            change_type="auto",
            reason="auto: viewed full application details",
            send_email=True
        )
        logger.info(f"[AutoStatus] App #{application_id} auto-updated: Submitted -> Under Review, reason=ok")
        return {
            "success": True,
            "changed": True,
            "reason": "ok",
            "old_status": "Submitted",
            "new_status": "Under Review",
            "application_id": application_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    # Idempotent: already at or past Under Review
    logger.info(f"[AutoStatus] App #{application_id} viewed event: changed=False, reason=already_later_status (current: '{current_norm}')")
    return {
        "success": True,
        "changed": False,
        "reason": "already_later_status",
        "status": current_norm,
        "message": f"Application is already at status '{current_norm}' (cannot be demoted)"
    }

async def undo_auto_status_change(
    db: AsyncSession,
    application_id: int,
    user_email: str = "HR"
) -> Dict[str, Any]:
    """
    Allows HR to undo the last automatic status change.
    """
    stmt = (
        select(ApplicationStatusHistory)
        .where(
            and_(
                ApplicationStatusHistory.application_id == application_id,
                ApplicationStatusHistory.change_type == "auto",
                ApplicationStatusHistory.can_undo == True
            )
        )
        .order_by(ApplicationStatusHistory.created_at.desc())
    )
    res = await db.execute(stmt)
    last_auto = res.scalar_one_or_none()

    if not last_auto or not last_auto.old_status:
        return {"success": False, "message": "No undoable automatic status change found"}

    app_stmt = select(JobApplication).where(JobApplication.id == application_id)
    app_res = await db.execute(app_stmt)
    app = app_res.scalar_one_or_none()
    if not app:
        return {"success": False, "message": "Application not found"}

    target_status = last_auto.old_status
    last_auto.can_undo = False
    await db.commit()

    await apply_application_status_change(
        db=db,
        application=app,
        new_status=target_status,
        changed_by=user_email,
        change_type="undo",
        reason=f"manual undo: reverted {last_auto.new_status} back to {target_status}",
        send_email=False
    )

    return {
        "success": True,
        "reverted_to": target_status,
        "application_id": application_id
    }
