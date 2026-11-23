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
    "NOT SELECTED": 0,
    "REJECTED": 0,
    "ARCHIVED": 0,
    "PASSED INITIAL INTERVIEW": 6,
    "ACCEPTED": 6,
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
    if s in ("NOT SELECTED", "REJECTED", "ARCHIVED", "PASSED_OVER"):
        return "Not Selected"
    if s in ("PASSED INITIAL INTERVIEW", "ACCEPTED"):
        return "Passed initial interview"
    return status.title()

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
    send_email: bool = True
) -> JobApplication:
    old_raw = application.status
    old_norm = normalize_status(old_raw)
    new_norm = normalize_status(new_status)

    if old_norm == new_norm:
        return application

    # Save to application
    application.status = new_norm.upper()
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
        can_undo=(change_type == "auto")
    )

    # Dispatch email only once per distinct status change (always to account login email when linked)
    if send_email and (getattr(application, "user_id", None) or application.candidate_email):
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
        if target_email:
            try:
                from app.services.email_service import send_application_status_update_email
                job_title = getattr(application, "job_title", "Position")
                if application.job and getattr(application.job, "job_title", None):
                    job_title = application.job.job_title

                await send_application_status_update_email(
                    to_email=target_email,
                    candidate_name=application.candidate_name or "Candidate",
                    job_title=job_title,
                    new_status=new_norm,
                    previous_status=old_norm,
                    notes=reason,
                    db=db,
                )
            except Exception as e:
                logger.warning(f"Could not send status email to {target_email}: {e}")

    # Invalidate cache
    try:
        await clear_cache_pattern("job_applications*")
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
