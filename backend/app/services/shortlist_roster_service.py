import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models.job_application import JobApplication
from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
from app.models.job_description import JobDescription
from app.services.status_management_service import (
    normalize_status,
    apply_application_status_change,
    record_status_history,
    is_withdrawn_status,
    is_resolved_status,
    is_shortlist_eligible_status,
)
from app.models.interview import Interview
from app.services.requirement_rules import (
    extract_criterion_status,
    STATUS_MANUAL_REVIEW,
)
from app.services.job_matching_service import (
    calculate_education_match,
    _resolve_education_text,
)

logger = logging.getLogger(__name__)

VALID_NON_SHORTLISTED_ACTIONS = {
    "keep_under_review",   # Default: Keep them under review until the job is closed
    "notify_on_finalize",  # Notify them as Not Selected when the shortlist is finalized
    "decide_later",        # Decide later (no automatic action on finalize)
}


def _validate_non_shortlisted_action(action: Optional[str]) -> str:
    norm = (action or "keep_under_review").strip().lower()
    if norm not in VALID_NON_SHORTLISTED_ACTIONS:
        raise ValueError(
            f"Invalid non_shortlisted_action '{action}'. "
            f"Allowed values: {', '.join(sorted(VALID_NON_SHORTLISTED_ACTIONS))}."
        )
    return norm


async def create_shortlist_roster(
    db: AsyncSession,
    job_id: int,
    name: str,
    created_by: str,
    notes: Optional[str] = None,
    application_ids: Optional[List[int]] = None,
    non_shortlisted_action: Optional[str] = "keep_under_review",
    finalize: bool = False,
    confirm_notify_non_shortlisted: bool = False,
) -> ShortlistRoster:
    policy = _validate_non_shortlisted_action(non_shortlisted_action)
    if finalize and policy == "notify_on_finalize" and not confirm_notify_non_shortlisted:
        raise ValueError(
            "Explicit confirmation is required before notifying non-shortlisted applicants as Not Selected."
        )

    if application_ids:
        # Validate every application BEFORE creating the roster so withdrawn/resolved apps are rejected cleanly
        for app_id in application_ids:
            app_res = await db.execute(select(JobApplication).where(JobApplication.id == app_id))
            app_obj = app_res.scalar_one_or_none()
            if not app_obj:
                raise ValueError(f"Application #{app_id} not found.")
            if is_withdrawn_status(app_obj.status):
                raise ValueError(
                    f"Cannot add withdrawn application #{app_id} ({app_obj.candidate_name or 'Applicant'}) to a shortlist roster."
                )
            if is_resolved_status(app_obj.status):
                raise ValueError(
                    f"Cannot add application #{app_id} ({app_obj.candidate_name or 'Applicant'}) with status '{normalize_status(app_obj.status)}' to a shortlist roster."
                )

    roster = ShortlistRoster(
        job_id=job_id,
        name=name,
        created_by=created_by,
        notes=notes,
        non_shortlisted_action=policy,
        is_finalized=False,
        finalized_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(roster)
    await db.commit()
    await db.refresh(roster)

    if application_ids:
        for app_id in application_ids:
            await add_application_to_roster(
                db=db,
                roster_id=roster.id,
                application_id=app_id,
                added_by=created_by
            )

    if finalize:
        await finalize_shortlist_roster(
            db=db,
            roster_id=roster.id,
            finalized_by=created_by,
            non_shortlisted_action=policy,
            confirm=confirm_notify_non_shortlisted or (policy != "notify_on_finalize"),
        )

    await db.refresh(roster)
    return roster


async def preview_non_shortlisted_for_job(
    db: AsyncSession,
    job_id: int,
    shortlisted_application_ids: Optional[List[int]] = None,
    roster_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Show how many non-shortlisted applicants would be affected and a preview of the
    Not Selected message before applying. Never applies any change.
    """
    from app.services.job_description_service import get_non_shortlisted_applications_for_job
    from app.services.message_template_service import render_not_selected_preview

    job_res = await db.execute(select(JobDescription).where(JobDescription.id == job_id))
    job = job_res.scalar_one_or_none()
    job_title = job.job_title if job else "Position"

    extra_ids = list(shortlisted_application_ids or [])
    policy = "keep_under_review"
    is_finalized = False

    if roster_id is not None:
        r_res = await db.execute(select(ShortlistRoster).where(ShortlistRoster.id == roster_id))
        roster = r_res.scalar_one_or_none()
        if roster:
            policy = getattr(roster, "non_shortlisted_action", None) or "keep_under_review"
            is_finalized = bool(getattr(roster, "is_finalized", False))

    breakdown = await get_non_shortlisted_applications_for_job(
        db=db,
        job_pk=job_id,
        extra_shortlisted_ids=extra_ids,
    )
    affected = breakdown["affected"]
    sample_name = affected[0].candidate_name if affected else "Applicant Name"
    preview = await render_not_selected_preview(
        db=db,
        job_title=job_title,
        candidate_name=sample_name or "Applicant Name",
    )

    return {
        "job_id": job_id,
        "job_title": job_title,
        "roster_id": roster_id,
        "non_shortlisted_action": policy,
        "is_finalized": is_finalized,
        "affected_count": len(affected),
        "protected_count": breakdown["protected_count"],
        "affected_applications": [
            {
                "id": a.id,
                "candidate_name": a.candidate_name,
                "candidate_email": a.candidate_email,
                "status": a.status,
            }
            for a in affected
        ],
        "message_preview": preview,
    }


async def update_roster_non_shortlisted_action(
    db: AsyncSession,
    roster_id: int,
    non_shortlisted_action: str,
    updated_by: str = "HR",
) -> Dict[str, Any]:
    """Allow changing a roster's non-shortlisted handling choice before finalizing."""
    policy = _validate_non_shortlisted_action(non_shortlisted_action)
    res = await db.execute(select(ShortlistRoster).where(ShortlistRoster.id == roster_id))
    roster = res.scalar_one_or_none()
    if not roster:
        raise LookupError("Shortlist roster not found")
    if getattr(roster, "is_finalized", False):
        raise ValueError("Cannot change non-shortlisted policy after the shortlist has already been finalized.")

    old_policy = getattr(roster, "non_shortlisted_action", "keep_under_review")
    roster.non_shortlisted_action = policy
    roster.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(roster)

    from app.services.audit_service import record_activity
    await record_activity(
        db=db,
        user_id=None,
        action="UPDATE_SHORTLIST_POLICY",
        target=f"Shortlist Roster #{roster.id} ({roster.name})",
        details=f"{updated_by} changed non-shortlisted action from '{old_policy}' to '{policy}'.",
    )

    return {
        "roster_id": roster.id,
        "non_shortlisted_action": roster.non_shortlisted_action,
        "is_finalized": bool(roster.is_finalized),
    }


async def finalize_shortlist_roster(
    db: AsyncSession,
    roster_id: int,
    finalized_by: str = "HR",
    non_shortlisted_action: Optional[str] = None,
    confirm: bool = True,
) -> Dict[str, Any]:
    """
    Finalize a shortlist roster.
    - If non_shortlisted_action == 'notify_on_finalize', requires explicit confirm=True,
      and marks non-shortlisted applications (Submitted / Under Review not in any roster for this job)
      as Not Selected with reason 'Not shortlisted when shortlist was finalized' (idempotent, once only).
    - If 'keep_under_review' (default) or 'decide_later', leaves non-shortlisted applicants untouched.
    """
    from app.services.job_description_service import get_non_shortlisted_applications_for_job
    from app.services.audit_service import record_activity

    res = await db.execute(select(ShortlistRoster).where(ShortlistRoster.id == roster_id))
    roster = res.scalar_one_or_none()
    if not roster:
        raise LookupError("Shortlist roster not found")

    if getattr(roster, "is_finalized", False):
        return {
            "roster_id": roster.id,
            "is_finalized": True,
            "non_shortlisted_action": roster.non_shortlisted_action,
            "notified_count": 0,
            "already_finalized": True,
        }

    policy = _validate_non_shortlisted_action(
        non_shortlisted_action if non_shortlisted_action is not None else getattr(roster, "non_shortlisted_action", "keep_under_review")
    )

    if policy == "notify_on_finalize" and not confirm:
        raise ValueError(
            "Explicit confirmation is required before notifying non-shortlisted applicants as Not Selected."
        )

    now = datetime.utcnow()
    roster.non_shortlisted_action = policy
    roster.is_finalized = True
    roster.finalized_at = now
    roster.updated_at = now
    await db.commit()

    notified_count = 0
    if policy == "notify_on_finalize":
        breakdown = await get_non_shortlisted_applications_for_job(db, roster.job_id)
        for app in breakdown["affected"]:
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Not Selected",
                changed_by=finalized_by,
                change_type="auto",
                reason="Not shortlisted when shortlist was finalized",
                send_email=True,
                send_notification=True,
            )
            notified_count += 1

    await record_activity(
        db=db,
        user_id=None,
        action="FINALIZE_SHORTLIST",
        target=f"Shortlist Roster #{roster.id} ({roster.name})",
        details=(
            f"{finalized_by} finalized shortlist with policy '{policy}'. "
            f"Non-shortlisted applicants notified as Not Selected: {notified_count}."
        ),
    )

    return {
        "roster_id": roster.id,
        "is_finalized": True,
        "finalized_at": now.isoformat(),
        "non_shortlisted_action": policy,
        "notified_count": notified_count,
        "already_finalized": False,
    }

INACTIVE_INTERVIEW_STATUSES = {"CANCELED", "CANCELLED", "COMPLETED", "REJECTED", "NO_SHOW"}


def _derive_effective_roster_stage(
    stored_stage: Optional[str],
    app: Optional[JobApplication],
    has_active_interview: bool = False,
) -> str:
    """
    Compute the canonical roster stage from the application's authoritative status and active interviews
    so roster columns and header counts always match what is actually booked/recorded.
    """
    if not app:
        return stored_stage or "Shortlisted"

    norm = normalize_status(app.status)
    if norm == "Passed initial interview":
        return "Passed initial interview"
    if norm == "Not Selected":
        return "Not selected"
    if norm == "Interviewed":
        return "Interviewed"
    if norm == "Interview Scheduled" or has_active_interview:
        return "Interview Scheduled"
    return "Shortlisted"


async def _get_active_interview_app_ids(db: AsyncSession, app_ids: List[int]) -> set[int]:
    """Return the set of application IDs that currently have an active (non-canceled/non-completed) interview."""
    if not app_ids:
        return set()
    app_id_set = {int(aid) for aid in app_ids}
    iv_res = await db.execute(
        select(Interview).where(
            Interview.status.notin_(list(INACTIVE_INTERVIEW_STATUSES))
        )
    )
    active_ids: set[int] = set()
    for iv in iv_res.scalars().all():
        if iv.job_application_id and int(iv.job_application_id) in app_id_set:
            active_ids.add(int(iv.job_application_id))
        for cid in (getattr(iv, "combined_application_ids", None) or []):
            try:
                cid_int = int(cid)
                if cid_int in app_id_set:
                    active_ids.add(cid_int)
            except (TypeError, ValueError):
                continue
    return active_ids


async def _sync_and_clean_roster_items(
    db: AsyncSession,
    roster: ShortlistRoster,
    job_title: str = "Position",
) -> tuple[List[tuple[ShortlistRosterItem, Optional[JobApplication], str]], List[Dict[str, Any]], Dict[str, int]]:
    """
    Load items for a roster, automatically remove any withdrawn applications with an audit entry,
    sync effective stages from JobApplication.status + active interviews, and return accurate counts.
    """
    item_stmt = select(ShortlistRosterItem).where(ShortlistRosterItem.roster_id == roster.id)
    item_res = await db.execute(item_stmt)
    items = list(item_res.scalars().all())

    app_ids = [i.application_id for i in items if i.application_id is not None]
    apps_by_id: Dict[int, JobApplication] = {}
    if app_ids:
        apps_res = await db.execute(select(JobApplication).where(JobApplication.id.in_(app_ids)))
        for a in apps_res.scalars().all():
            apps_by_id[a.id] = a

    active_iv_app_ids = await _get_active_interview_app_ids(db, app_ids)

    kept: List[tuple[ShortlistRosterItem, Optional[JobApplication], str]] = []
    removed_withdrawn: List[Dict[str, Any]] = []
    dirty = False
    now = datetime.utcnow()

    for item in items:
        app = apps_by_id.get(item.application_id)
        if app and is_withdrawn_status(app.status):
            cand_name = app.candidate_name or app.candidate_email or f"Application #{app.id}"
            status_label = normalize_status(app.status)
            await db.delete(item)
            dirty = True
            notice_msg = (
                f"{cand_name} was automatically removed from roster '{roster.name}' "
                f"because their application is {status_label}."
            )
            removed_withdrawn.append({
                "application_id": app.id,
                "candidate_name": cand_name,
                "status": status_label,
                "roster_id": roster.id,
                "roster_name": roster.name,
                "message": notice_msg,
            })
            try:
                from app.services.audit_service import record_activity
                await record_activity(
                    db=db,
                    user_id=None,
                    action="AUTO_REMOVE_WITHDRAWN_FROM_ROSTER",
                    target=f"Shortlist Roster #{roster.id} ({roster.name})",
                    details=notice_msg,
                )
            except Exception as audit_err:
                logger.warning(f"Could not audit-log auto removal for app {app.id}: {audit_err}")
            continue

        effective_stage = _derive_effective_roster_stage(
            item.stage,
            app,
            has_active_interview=(item.application_id in active_iv_app_ids),
        )
        if item.stage != effective_stage:
            item.stage = effective_stage
            item.updated_at = now
            dirty = True

        kept.append((item, app, effective_stage))

    if dirty:
        await db.commit()

    counts = {
        "total": len(kept),
        "shortlisted": sum(1 for _, _, st in kept if st == "Shortlisted"),
        "interview_scheduled": sum(1 for _, _, st in kept if st == "Interview Scheduled"),
        "interviewed": sum(1 for _, _, st in kept if st == "Interviewed"),
        "passed": sum(1 for _, _, st in kept if st == "Passed initial interview"),
        "not_selected": sum(1 for _, _, st in kept if st in ("Not selected", "Not Selected")),
    }
    return kept, removed_withdrawn, counts


async def get_shortlist_rosters(
    db: AsyncSession,
    job_id: Optional[int] = None,
    archived: Optional[bool] = None
) -> List[Dict[str, Any]]:
    stmt = select(ShortlistRoster).order_by(ShortlistRoster.created_at.desc())
    if job_id:
        stmt = stmt.where(ShortlistRoster.job_id == job_id)
    if archived is True:
        stmt = stmt.where(ShortlistRoster.is_archived == True)
    elif archived is False:
        stmt = stmt.where(or_(ShortlistRoster.is_archived == False, ShortlistRoster.is_archived == None))

    res = await db.execute(stmt)
    rosters = list(res.scalars().all())

    result = []
    for r in rosters:
        job_stmt = select(JobDescription).where(JobDescription.id == r.job_id)
        job_res = await db.execute(job_stmt)
        job = job_res.scalar_one_or_none()
        job_title = job.job_title if job else "Position"

        _, removed_withdrawn, counts = await _sync_and_clean_roster_items(db, r, job_title=job_title)
        cleanup_notice = (
            " ".join(n["message"] for n in removed_withdrawn) if removed_withdrawn else None
        )

        result.append({
            "id": r.id,
            "job_id": r.job_id,
            "job_title": job_title,
            "job_department": getattr(job, "department", "General") if job else "General",
            "name": r.name,
            "created_by": r.created_by,
            "notes": r.notes,
            "is_archived": bool(getattr(r, "is_archived", False)),
            "non_shortlisted_action": getattr(r, "non_shortlisted_action", None) or "keep_under_review",
            "is_finalized": bool(getattr(r, "is_finalized", False)),
            "finalized_at": r.finalized_at.isoformat() if getattr(r, "finalized_at", None) else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "total_candidates": counts["total"],
            "shortlisted_count": counts["shortlisted"],
            "interview_scheduled_count": counts["interview_scheduled"],
            "interviewed_count": counts["interviewed"],
            "passed_count": counts["passed"],
            "not_selected_count": counts["not_selected"],
            "auto_removed_withdrawn": removed_withdrawn,
            "cleanup_notice": cleanup_notice,
        })

    return result

async def get_shortlist_roster_by_id(
    db: AsyncSession,
    roster_id: int
) -> Optional[Dict[str, Any]]:
    stmt = select(ShortlistRoster).where(ShortlistRoster.id == roster_id)
    res = await db.execute(stmt)
    roster = res.scalar_one_or_none()
    if not roster:
        return None

    job_stmt = select(JobDescription).where(JobDescription.id == roster.job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    job_title = job.job_title if job else "Position"

    kept_items, removed_withdrawn, counts = await _sync_and_clean_roster_items(db, roster, job_title=job_title)
    cleanup_notice = (
        " ".join(n["message"] for n in removed_withdrawn) if removed_withdrawn else None
    )

    items_data = []
    for item, app, effective_stage in kept_items:

        app_info = None
        edu_score = None
        edu_reason = None
        edu_status = None
        edu_needs_manual_review = False
        req_deg = getattr(job, "education_requirements", None) if job else None
        cand_deg = None
        highest_att = None
        deg = None

        if app:
            edu_score = app.education_score
            edu_reason = app.education_reason
            req_deg = app.required_degree or req_deg
            cand_deg = app.candidate_degree
            highest_att = getattr(app, "highest_educational_attainment", None)
            deg = getattr(app, "degree", None)
            edu_status = extract_criterion_status(edu_reason)

            # Fallback to shared requirement_rules evaluation if legacy app has no parsed status yet
            if edu_status is None and job is not None:
                cand_edu_text = _resolve_education_text({
                    "education": deg or highest_att,
                    "degree": deg,
                    "highest_degree": highest_att,
                    "highest_educational_attainment": highest_att,
                })
                edu_eval = calculate_education_match(
                    cand_edu_text,
                    job.description or "",
                    education_req=getattr(job, "education_requirements", None),
                    education_entries=getattr(app, "education_entries", None),
                )
                edu_status = edu_eval.get("status")
                edu_reason = edu_reason or edu_eval.get("reason")
                req_deg = req_deg or edu_eval.get("required_education")
                cand_deg = cand_deg or edu_eval.get("candidate_education")
                if edu_score is None:
                    edu_score = round(float(edu_eval.get("score", 0.0)) * 100, 1)

            edu_needs_manual_review = edu_status == STATUS_MANUAL_REVIEW
            skills_status = extract_criterion_status(app.skills_reason)
            exp_status = extract_criterion_status(app.experience_reason)
            certs_status = extract_criterion_status(getattr(app, "certifications_reason", None))

            contact_em = getattr(app, "contact_email", None) or app.candidate_email or ""
            app_info = {
                "id": app.id,
                "user_id": getattr(app, "user_id", None),
                "applicant_id": getattr(app, "user_id", None),
                "candidate_name": app.candidate_name or contact_em or "Applicant",
                "candidate_email": contact_em,
                "contact_email": contact_em,
                "resume_email": getattr(app, "resume_email", None),
                "phone": app.phone,
                "job_title": app.job_title or (job.job_title if job else "Position"),
                "status": app.status,
                "match_score": app.match_score,
                "skills_score": app.skills_score,
                "experience_score": app.experience_score,
                "education_score": edu_score,
                "certifications_score": app.certifications_score,
                "skills_status": skills_status,
                "experience_status": exp_status,
                "education_status": edu_status,
                "certifications_status": certs_status,
                "education_needs_manual_review": edu_needs_manual_review,
                "source": getattr(app, "source", "Online") or "Online",
                "import_origin": getattr(app, "import_origin", None),
                "imported_by": getattr(app, "imported_by", None),
                "skills_reason": app.skills_reason,
                "experience_reason": app.experience_reason,
                "education_reason": edu_reason,
                "certifications_reason": getattr(app, "certifications_reason", None),
                "required_degree": req_deg,
                "candidate_degree": cand_deg,
                "highest_educational_attainment": highest_att,
                "degree": deg,
                "matched_skills": app.matched_skills or [],
                "missing_skills": app.missing_skills or [],
                "strengths": app.strengths or [],
                "weaknesses": app.weaknesses or [],
                "ai_summary": app.ai_summary,
                "resume_url": app.resume_url,
                "created_at": app.created_at.isoformat() if app.created_at else None
            }

        candidate_name = (app.candidate_name if app and app.candidate_name else (app.candidate_email if app else "Applicant"))
        candidate_email = (getattr(app, "contact_email", None) or app.candidate_email) if app else ""
        match_score = app.match_score if app else None

        items_data.append({
            "id": item.id,
            "roster_id": item.roster_id,
            "application_id": item.application_id,
            "user_id": getattr(app, "user_id", None) if app else None,
            "applicant_id": getattr(app, "user_id", None) if app else None,
            "stage": effective_stage,
            "added_by": item.added_by,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "contact_email": candidate_email,
            "resume_email": getattr(app, "resume_email", None) if app else None,
            "match_score": match_score,
            "education_score": edu_score,
            "education_reason": edu_reason,
            "education_status": edu_status,
            "education_needs_manual_review": edu_needs_manual_review,
            "required_degree": req_deg,
            "candidate_degree": cand_deg,
            "highest_educational_attainment": highest_att,
            "degree": deg,
            "source": getattr(app, "source", "Online") if app else "Online",
            "import_origin": getattr(app, "import_origin", None) if app else None,
            "imported_by": getattr(app, "imported_by", None) if app else None,
            "phone": app.phone if app else None,
            "added_at": item.added_at.isoformat() if item.added_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "application": app_info
        })

    return {
        "id": roster.id,
        "job_id": roster.job_id,
        "job_title": job_title,
        "job_department": getattr(job, "department", "General") if job else "General",
        "name": roster.name,
        "created_by": roster.created_by,
        "notes": roster.notes,
        "is_archived": bool(getattr(roster, "is_archived", False)),
        "non_shortlisted_action": getattr(roster, "non_shortlisted_action", None) or "keep_under_review",
        "is_finalized": bool(getattr(roster, "is_finalized", False)),
        "finalized_at": roster.finalized_at.isoformat() if getattr(roster, "finalized_at", None) else None,
        "created_at": roster.created_at.isoformat() if roster.created_at else None,
        "updated_at": roster.updated_at.isoformat() if roster.updated_at else None,
        "total_candidates": counts["total"],
        "shortlisted_count": counts["shortlisted"],
        "interview_scheduled_count": counts["interview_scheduled"],
        "interviewed_count": counts["interviewed"],
        "passed_count": counts["passed"],
        "not_selected_count": counts["not_selected"],
        "auto_removed_withdrawn": removed_withdrawn,
        "cleanup_notice": cleanup_notice,
        "items": items_data
    }

async def add_application_to_roster(
    db: AsyncSession,
    roster_id: int,
    application_id: int,
    added_by: str
) -> ShortlistRosterItem:
    # Validate target application eligibility (reject withdrawn or resolved applications!)
    target_app_res = await db.execute(select(JobApplication).where(JobApplication.id == application_id))
    target_app = target_app_res.scalar_one_or_none()
    if not target_app:
        raise ValueError("Application not found.")
    if is_withdrawn_status(target_app.status):
        raise ValueError("Cannot add a withdrawn application to a shortlist roster.")
    if is_resolved_status(target_app.status):
        raise ValueError(
            f"Cannot add an application with resolved status '{normalize_status(target_app.status)}' to a shortlist roster."
        )

    # Check if already in this roster by application_id
    check_stmt = select(ShortlistRosterItem).where(
        and_(
            ShortlistRosterItem.roster_id == roster_id,
            ShortlistRosterItem.application_id == application_id
        )
    )
    check_res = await db.execute(check_stmt)
    existing = check_res.scalar_one_or_none()
    if existing:
        return existing

    # Also check if another application from the same user_id is already in this roster
    if getattr(target_app, "user_id", None):
        same_user_stmt = (
            select(ShortlistRosterItem)
            .join(JobApplication, ShortlistRosterItem.application_id == JobApplication.id)
            .where(
                and_(
                    ShortlistRosterItem.roster_id == roster_id,
                    JobApplication.user_id == target_app.user_id,
                )
            )
        )
        same_user_res = await db.execute(same_user_stmt)
        existing_same_user = same_user_res.scalars().first()
        if existing_same_user:
            return existing_same_user

    # Derive initial stage so candidates who already have an interview booked appear in Interview Scheduled immediately
    active_iv_ids = await _get_active_interview_app_ids(db, [application_id])
    initial_stage = _derive_effective_roster_stage(
        "Shortlisted",
        target_app,
        has_active_interview=(application_id in active_iv_ids),
    )

    item = ShortlistRosterItem(
        roster_id=roster_id,
        application_id=application_id,
        stage=initial_stage,
        added_by=added_by,
        added_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Status transition rules (Item 1b):
    # If application is still Submitted when added, move it through Under Review to Shortlisted
    # and record both steps in the history.
    app_stmt = select(JobApplication).where(JobApplication.id == application_id)
    app_res = await db.execute(app_stmt)
    app = app_res.scalar_one_or_none()

    if app:
        current_norm = normalize_status(app.status)
        roster_stmt = select(ShortlistRoster).where(ShortlistRoster.id == roster_id)
        r_res = await db.execute(roster_stmt)
        roster_obj = r_res.scalar_one_or_none()
        roster_name = roster_obj.name if roster_obj else "roster"

        if current_norm == "Submitted":
            # 1. Step 1: Submitted -> Under Review
            await record_status_history(
                db=db,
                application_id=app.id,
                old_status="Submitted",
                new_status="Under Review",
                changed_by="auto",
                change_type="auto",
                reason=f"auto: progressed via addition to shortlist roster '{roster_name}'",
                can_undo=False
            )
            # 2. Step 2: Under Review -> Shortlisted
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Shortlisted",
                changed_by=added_by,
                change_type="auto",
                reason=f"auto: added to shortlist roster '{roster_name}'",
                send_email=True
            )
        elif current_norm == "Under Review":
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Shortlisted",
                changed_by=added_by,
                change_type="auto",
                reason=f"auto: added to shortlist roster '{roster_name}'",
                send_email=True
            )
        # If already Shortlisted or higher, leave unchanged (idempotent)

    return item

async def remove_application_from_roster(
    db: AsyncSession,
    roster_id: int,
    application_id: int,
    removed_by: str
) -> bool:
    stmt = select(ShortlistRosterItem).where(
        and_(
            ShortlistRosterItem.roster_id == roster_id,
            ShortlistRosterItem.application_id == application_id
        )
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return False

    await db.delete(item)
    await db.commit()

    # Get roster details to find position
    roster_stmt = select(ShortlistRoster).where(ShortlistRoster.id == roster_id)
    roster_res = await db.execute(roster_stmt)
    roster_obj = roster_res.scalar_one_or_none()

    if roster_obj:
        job_id = roster_obj.job_id
        # Check if applicant is still in ANY other roster for the same position
        other_rosters_stmt = (
            select(ShortlistRosterItem)
            .join(ShortlistRoster, ShortlistRosterItem.roster_id == ShortlistRoster.id)
            .where(
                and_(
                    ShortlistRoster.job_id == job_id,
                    ShortlistRosterItem.application_id == application_id,
                    ShortlistRoster.id != roster_id
                )
            )
        )
        other_res = await db.execute(other_rosters_stmt)
        other_item = other_res.scalar_one_or_none()

        app_stmt = select(JobApplication).where(JobApplication.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()

        if app and not is_withdrawn_status(app.status) and not is_resolved_status(app.status):
            if other_item:
                # Remains Shortlisted because still in another roster for the same position
                logger.info(
                    f"Applicant {application_id} removed from roster {roster_id} but remains Shortlisted in other roster {other_item.roster_id}."
                )
            else:
                # Rule: "removing an applicant from a roster returns that application to Under Review, unless it is still in another roster for the same position, in which case the status stays Shortlisted."
                await apply_application_status_change(
                    db=db,
                    application=app,
                    new_status="Under Review",
                    changed_by=removed_by,
                    change_type="manual",
                    reason=f"manual: removed from shortlist roster '{roster_obj.name}'",
                    send_email=False
                )

    return True

async def update_roster_item_stage(
    db: AsyncSession,
    roster_id: int,
    application_id: int,
    stage: str,
    updated_by: str
) -> Optional[ShortlistRosterItem]:
    stmt = select(ShortlistRosterItem).where(
        and_(
            ShortlistRosterItem.roster_id == roster_id,
            ShortlistRosterItem.application_id == application_id
        )
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return None

    # Sync with application status (guard against withdrawn applications)
    app_stmt = select(JobApplication).where(JobApplication.id == application_id)
    app_res = await db.execute(app_stmt)
    app = app_res.scalar_one_or_none()
    if app and is_withdrawn_status(app.status):
        raise ValueError("Cannot update stage for a withdrawn application.")

    item.stage = stage
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)

    if app:
        if stage == "Interview Scheduled":
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Interview Scheduled",
                changed_by=updated_by,
                change_type="manual",
                reason=f"manual: roster stage set to Interview Scheduled in roster #{roster_id}",
                send_email=True
            )
        elif stage == "Interviewed":
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Interviewed",
                changed_by=updated_by,
                change_type="manual",
                reason=f"manual: initial interview confirmed complete by HR in roster #{roster_id}",
                send_email=True
            )
        elif stage in ("Not selected", "Not Selected"):
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Not Selected",
                changed_by=updated_by,
                change_type="manual",
                reason=f"manual: candidate marked as not selected following initial interview in roster #{roster_id}",
                send_email=True
            )
        elif stage == "Passed initial interview":
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Passed initial interview",
                changed_by=updated_by,
                change_type="manual",
                reason=f"manual: candidate passed initial interview in roster #{roster_id}",
                send_email=True
            )
        elif stage == "Shortlisted":
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Shortlisted",
                changed_by=updated_by,
                change_type="manual",
                reason=f"manual: stage reverted back to Shortlisted in roster #{roster_id}",
                send_email=False
            )

    return item

async def toggle_archive_shortlist_roster(
    db: AsyncSession,
    roster_id: int,
    archived: bool,
    updated_by: str = "HR"
) -> Optional[Dict[str, Any]]:
    stmt = select(ShortlistRoster).where(ShortlistRoster.id == roster_id)
    res = await db.execute(stmt)
    roster = res.scalar_one_or_none()
    if not roster:
        return None
    roster.is_archived = archived
    roster.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(roster)
    return {
        "id": roster.id,
        "name": roster.name,
        "is_archived": bool(roster.is_archived),
        "message": f"Roster '{roster.name}' {'archived' if archived else 'unarchived'} successfully."
    }

async def delete_shortlist_roster(
    db: AsyncSession,
    roster_id: int,
    deleted_by: str = "HR"
) -> bool:
    stmt = select(ShortlistRoster).where(ShortlistRoster.id == roster_id)
    res = await db.execute(stmt)
    roster = res.scalar_one_or_none()
    if not roster:
        return False

    job_id = roster.job_id
    roster_name = roster.name

    # Get items to apply removal rule
    item_stmt = select(ShortlistRosterItem).where(ShortlistRosterItem.roster_id == roster_id)
    item_res = await db.execute(item_stmt)
    items = list(item_res.scalars().all())

    for item in items:
        app_id = item.application_id
        # Check if in any other roster for the same position
        other_stmt = (
            select(ShortlistRosterItem)
            .join(ShortlistRoster, ShortlistRosterItem.roster_id == ShortlistRoster.id)
            .where(
                and_(
                    ShortlistRoster.job_id == job_id,
                    ShortlistRosterItem.application_id == app_id,
                    ShortlistRoster.id != roster_id
                )
            )
        )
        other_res = await db.execute(other_stmt)
        other_item = other_res.scalar_one_or_none()

        if not other_item:
            # Check application status; if Shortlisted, return to Under Review
            app_stmt = select(JobApplication).where(JobApplication.id == app_id)
            app_res = await db.execute(app_stmt)
            app = app_res.scalar_one_or_none()
            if app and normalize_status(app.status) == "Shortlisted":
                await apply_application_status_change(
                    db=db,
                    application=app,
                    new_status="Under Review",
                    changed_by=deleted_by,
                    change_type="manual",
                    reason=f"manual: roster '{roster_name}' was deleted",
                    send_email=False
                )

    await db.delete(roster)
    await db.commit()
    return True
