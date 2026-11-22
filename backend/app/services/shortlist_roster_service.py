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
    record_status_history
)
from app.services.requirement_rules import (
    extract_criterion_status,
    STATUS_MANUAL_REVIEW,
)
from app.services.job_matching_service import (
    calculate_education_match,
    _resolve_education_text,
)

logger = logging.getLogger(__name__)

async def create_shortlist_roster(
    db: AsyncSession,
    job_id: int,
    name: str,
    created_by: str,
    notes: Optional[str] = None,
    application_ids: Optional[List[int]] = None
) -> ShortlistRoster:
    roster = ShortlistRoster(
        job_id=job_id,
        name=name,
        created_by=created_by,
        notes=notes,
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

    await db.refresh(roster)
    return roster

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
        # Load items
        item_stmt = select(ShortlistRosterItem).where(ShortlistRosterItem.roster_id == r.id)
        item_res = await db.execute(item_stmt)
        items = list(item_res.scalars().all())

        counts = {
            "total": len(items),
            "shortlisted": sum(1 for i in items if i.stage == "Shortlisted"),
            "interview_scheduled": sum(1 for i in items if i.stage == "Interview Scheduled"),
            "interviewed": sum(1 for i in items if i.stage == "Interviewed"),
            "passed": sum(1 for i in items if i.stage == "Passed initial interview"),
            "not_selected": sum(1 for i in items if i.stage in ("Not selected", "Not Selected")),
        }

        job_stmt = select(JobDescription).where(JobDescription.id == r.job_id)
        job_res = await db.execute(job_stmt)
        job = job_res.scalar_one_or_none()

        result.append({
            "id": r.id,
            "job_id": r.job_id,
            "job_title": job.job_title if job else "Position",
            "job_department": getattr(job, "department", "General") if job else "General",
            "name": r.name,
            "created_by": r.created_by,
            "notes": r.notes,
            "is_archived": bool(getattr(r, "is_archived", False)),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "total_candidates": counts["total"],
            "shortlisted_count": counts["shortlisted"],
            "interview_scheduled_count": counts["interview_scheduled"],
            "interviewed_count": counts["interviewed"],
            "passed_count": counts["passed"],
            "not_selected_count": counts["not_selected"],
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

    item_stmt = select(ShortlistRosterItem).where(ShortlistRosterItem.roster_id == roster_id)
    item_res = await db.execute(item_stmt)
    items = list(item_res.scalars().all())

    items_data = []
    for item in items:
        app_stmt = select(JobApplication).where(JobApplication.id == item.application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()

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

            app_info = {
                "id": app.id,
                "candidate_name": app.candidate_name or app.candidate_email or "Applicant",
                "candidate_email": app.candidate_email or "",
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
        candidate_email = app.candidate_email if app else ""
        match_score = app.match_score if app else None

        items_data.append({
            "id": item.id,
            "roster_id": item.roster_id,
            "application_id": item.application_id,
            "stage": item.stage,
            "added_by": item.added_by,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
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

    counts = {
        "total": len(items),
        "shortlisted": sum(1 for i in items if i.stage == "Shortlisted"),
        "interview_scheduled": sum(1 for i in items if i.stage == "Interview Scheduled"),
        "interviewed": sum(1 for i in items if i.stage == "Interviewed"),
        "passed": sum(1 for i in items if i.stage == "Passed initial interview"),
        "not_selected": sum(1 for i in items if i.stage in ("Not selected", "Not Selected")),
    }

    return {
        "id": roster.id,
        "job_id": roster.job_id,
        "job_title": job.job_title if job else "Position",
        "job_department": getattr(job, "department", "General") if job else "General",
        "name": roster.name,
        "created_by": roster.created_by,
        "notes": roster.notes,
        "is_archived": bool(getattr(roster, "is_archived", False)),
        "created_at": roster.created_at.isoformat() if roster.created_at else None,
        "updated_at": roster.updated_at.isoformat() if roster.updated_at else None,
        "total_candidates": counts["total"],
        "shortlisted_count": counts["shortlisted"],
        "interview_scheduled_count": counts["interview_scheduled"],
        "interviewed_count": counts["interviewed"],
        "passed_count": counts["passed"],
        "not_selected_count": counts["not_selected"],
        "items": items_data
    }

async def add_application_to_roster(
    db: AsyncSession,
    roster_id: int,
    application_id: int,
    added_by: str
) -> ShortlistRosterItem:
    # Check if already in this roster
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

    item = ShortlistRosterItem(
        roster_id=roster_id,
        application_id=application_id,
        stage="Shortlisted",
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

        if app:
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

    item.stage = stage
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)

    # Sync with application status
    app_stmt = select(JobApplication).where(JobApplication.id == application_id)
    app_res = await db.execute(app_stmt)
    app = app_res.scalar_one_or_none()

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
