import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.schemas.hr_schema import (
    HRCreate, HRResponse, HRUpdate,
    ShortlistRosterCreate, ShortlistRosterResponse,
    ShortlistRosterItemCreate, ShortlistRosterItemStageUpdate,
    ShortlistNonShortlistedPreviewRequest, ShortlistPolicyUpdateRequest, ShortlistFinalizeRequest,
    HRCandidateNoteCreate, HRCandidateNoteResponse,
    UniversalSearchResponse, CandidateCompareRequest
)
from app.services import hr_service
from app.services.candidate_comparison_service import compare_candidates_service
from app.services.shortlist_roster_service import (
    create_shortlist_roster,
    get_shortlist_rosters,
    get_shortlist_roster_by_id,
    add_application_to_roster,
    remove_application_from_roster,
    update_roster_item_stage,
    toggle_archive_shortlist_roster,
    delete_shortlist_roster,
    preview_non_shortlisted_for_job,
    update_roster_non_shortlisted_action,
    finalize_shortlist_roster,
)
from app.services.applicant_profile_service import (
    get_applicant_comprehensive_profile,
    add_candidate_hr_note,
    universal_search_hr
)
from app.services.audit_service import record_activity
from app.utils.cache import cache_response, clear_cache_pattern
from app.utils.auth import get_current_user, get_optional_current_user


router = APIRouter(prefix="/hr", tags=["HR Management"])

@router.post("/register")
async def register_hr(hr_in: HRCreate, db: AsyncSession = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Public HR registration is disabled. HR accounts must be created by an Administrator."
    )

@router.get("/candidate-count")
@cache_response("candidate_count", ttl=300)
async def get_candidates_count(db: AsyncSession = Depends(get_db)):
    count = await hr_service.get_total_candidates_count(db)
    return {"count": count}

@router.get("/resume-count")
@cache_response("resume_count", ttl=300)
async def get_resumes_count(db: AsyncSession = Depends(get_db)):
    count = await hr_service.get_total_resumes_count(db)
    return {"count": count}

@router.get("/application-stats")
@cache_response("app_stats", ttl=300)
async def get_app_stats(db: AsyncSession = Depends(get_db)):
    stats = await hr_service.get_application_stats(db)
    return stats

@router.get("/profile/{hr_id}", response_model=HRResponse)
async def get_hr_profile_details(hr_id: int, db: AsyncSession = Depends(get_db)):
    profile = await hr_service.get_hr_profile(db, hr_id)
    if not profile:
        raise HTTPException(status_code=404, detail="HR profile not found")

    screened_count = 0
    job_posts_count = 0
    reports_count = 0
    try:
        from app.models.job_application import JobApplication
        from app.models.job_description import JobDescription
        from app.models.interview import Interview
        from sqlalchemy import select, func

        apps_res = await db.execute(select(func.count(JobApplication.id)))
        screened_count = apps_res.scalar() or 0

        jobs_res = await db.execute(select(func.count(JobDescription.id)).where(JobDescription.is_active == True))
        job_posts_count = jobs_res.scalar() or 0

        interviews_res = await db.execute(select(func.count(Interview.id)))
        reports_count = interviews_res.scalar() or 0
    except Exception as e:
        print(f"Error computing HR profile stats: {e}")

    data = HRResponse.from_orm(profile)
    data.screened_count = screened_count
    data.job_posts_count = job_posts_count
    data.reports_count = reports_count
    return data

@router.put("/profile/{hr_id}", response_model=HRResponse)
async def update_hr_profile_details(hr_id: int, hr_update: HRUpdate, db: AsyncSession = Depends(get_db)):
    try:
        updated_profile = await hr_service.update_hr_profile(db, hr_id, hr_update)
        if not updated_profile:
            raise HTTPException(status_code=404, detail="HR profile not found")
        await clear_cache_pattern(f"hr_profile:*\"hr_id\": {hr_id}*")
        return updated_profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload-profile-image/{hr_id}")
async def upload_hr_profile_image(
    hr_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    image_url = None

    # 1. Upload to Supabase Storage (bucket: profile_images, path: profiles/)
    try:
        from app.utils.supabase_storage import upload_profile_image as sb_upload_profile_image
        result = await sb_upload_profile_image(
            file_bytes=file_bytes,
            original_filename=file.filename or f"hr_{hr_id}.png",
            user_role="hr",
            user_id=hr_id,
        )
        image_url = result["public_url"]
        print(f"Uploaded HR {hr_id} profile image to Supabase: {image_url}")
    except Exception as e:
        print(f"Supabase HR profile upload failed, falling back to local: {e}")
        upload_dir = "uploads/profile_images"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_extension = os.path.splitext(file.filename or "")[1] or ".png"
        file_name = f"hr_{hr_id}{file_extension}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        import time
        image_url = f"/{file_path}?t={int(time.time())}"

    await hr_service.update_hr_profile(db, hr_id, HRUpdate(profile_image_url=image_url))
    await clear_cache_pattern(f"hr_profile:*\"hr_id\": {hr_id}*")
    return {"image_url": image_url}
    


@router.get("/dashboard-trends")
@cache_response("dashboard_trends", ttl=300)
async def get_dashboard_trends_endpoint(db: AsyncSession = Depends(get_db)):
    return await hr_service.get_dashboard_trends(db)


@router.get("/export/csv")
async def export_hr_dashboard_csv(db: AsyncSession = Depends(get_db)):
    """Export HR Dashboard analytics summary and applicant records as a CSV file."""
    from datetime import datetime
    from app.utils.hr_export import generate_hr_csv_bytes

    export_data = await hr_service.build_hr_dashboard_export_data(db)
    csv_bytes = generate_hr_csv_bytes(export_data)
    date_tag = datetime.utcnow().strftime("%Y-%m-%d")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="Mariwasa_HR_Recruitment_Report_{date_tag}.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/export/pdf")
async def export_hr_dashboard_pdf(db: AsyncSession = Depends(get_db)):
    """Export HR Dashboard analytics summary and applicant records as a PDF file."""
    from datetime import datetime
    from app.utils.hr_export import generate_hr_pdf_bytes

    export_data = await hr_service.build_hr_dashboard_export_data(db)
    pdf_bytes = generate_hr_pdf_bytes(export_data)
    date_tag = datetime.utcnow().strftime("%Y-%m-%d")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Mariwasa_HR_Recruitment_Report_{date_tag}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/interviewers")
async def get_hr_interviewers(db: AsyncSession = Depends(get_db)):
    """Fetch all active HR interviewers/panelists with their details and live Google Calendar status."""
    from sqlalchemy import text
    from app.utils.google_auth import is_google_credentials_expired
    query = text("""
        SELECT u.id, u.fullname, u.email, u.profile_image_url, 
               u.google_credentials,
               h.company_name, h.department, h.position
        FROM users u
        LEFT JOIN hr_staffs h ON h.id = u.id
        WHERE u.role = 'HR' AND u.is_archived = false
        ORDER BY u.fullname ASC
    """)
    result = await db.execute(query)
    rows = result.fetchall()
    return [
        {
            "id": r.id,
            "fullname": r.fullname,
            "email": r.email,
            "profile_image_url": r.profile_image_url,
            "has_google_calendar": bool(
                r.google_credentials
                and "calendar" in r.google_credentials
                and not is_google_credentials_expired(r.google_credentials)
            ),
            "company_name": r.company_name or "Mariwasa Siam Ceramics, Inc.",
            "department": r.department or "Human Resources",
            "position": r.position or "HR Specialist",
        }
        for r in rows
    ]


# ─── SHORTLIST ROSTERS (Item 2c, 2d, 2e) ────────────────────────────────────

@router.post("/shortlists/preview-non-shortlisted")
async def preview_shortlist_non_shortlisted(
    payload: ShortlistNonShortlistedPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Preview affected non-shortlisted applicant count and rendered message before applying."""
    return await preview_non_shortlisted_for_job(
        db=db,
        job_id=payload.job_id,
        shortlisted_application_ids=payload.shortlisted_application_ids,
        roster_id=payload.roster_id,
    )


@router.post("/shortlists", response_model=ShortlistRosterResponse, status_code=status.HTTP_201_CREATED)
async def create_new_shortlist_roster(
    roster_in: ShortlistRosterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Create a new named shortlist roster with a saved non-shortlisted handling choice."""
    hr_email = (current_user.get("sub") or current_user.get("email") if current_user else None) or "HR"
    try:
        roster = await create_shortlist_roster(
            db=db,
            job_id=roster_in.job_id,
            name=roster_in.name,
            created_by=hr_email,
            notes=roster_in.notes,
            application_ids=roster_in.application_ids,
            non_shortlisted_action=roster_in.non_shortlisted_action,
            finalize=bool(roster_in.finalize),
            confirm_notify_non_shortlisted=bool(roster_in.confirm_notify_non_shortlisted),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    details = await get_shortlist_roster_by_id(db, roster.id)
    return details


@router.get("/shortlists/{roster_id}/finalize-preview")
async def get_roster_finalize_preview(
    roster_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Preview affected non-shortlisted applicants and rendered message for an existing roster."""
    roster = await get_shortlist_roster_by_id(db, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Shortlist roster not found")
    return await preview_non_shortlisted_for_job(
        db=db,
        job_id=roster["job_id"],
        roster_id=roster_id,
    )


@router.patch("/shortlists/{roster_id}/non-shortlisted-policy")
async def change_roster_non_shortlisted_policy(
    roster_id: int,
    payload: ShortlistPolicyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Update the non-shortlisted handling choice for a roster before finalizing."""
    hr_email = (current_user.get("sub") or current_user.get("email") if current_user else None) or "HR"
    try:
        return await update_roster_non_shortlisted_action(
            db=db,
            roster_id=roster_id,
            non_shortlisted_action=payload.non_shortlisted_action,
            updated_by=hr_email,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/shortlists/{roster_id}/finalize")
async def finalize_roster_endpoint(
    roster_id: int,
    payload: ShortlistFinalizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Finalize a shortlist roster and apply its confirmed non-shortlisted policy."""
    hr_email = (current_user.get("sub") or current_user.get("email") if current_user else None) or "HR"
    try:
        return await finalize_shortlist_roster(
            db=db,
            roster_id=roster_id,
            finalized_by=hr_email,
            non_shortlisted_action=payload.non_shortlisted_action,
            confirm=payload.confirm,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/shortlists")
async def list_shortlist_rosters(
    job_id: Optional[int] = None,
    archived: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all shortlist rosters with counts per stage and progress."""
    rosters = await get_shortlist_rosters(db=db, job_id=job_id, archived=archived)
    return rosters


@router.get("/shortlists/{roster_id}")
async def get_single_shortlist_roster(
    roster_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get single shortlist roster with applicant items and stages."""
    roster = await get_shortlist_roster_by_id(db=db, roster_id=roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Shortlist roster not found")
    return roster


@router.post("/shortlists/{roster_id}/items")
async def add_candidate_to_roster(
    roster_id: int,
    item_in: ShortlistRosterItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Add an applicant to an existing shortlist roster (moves status to Shortlisted)."""
    hr_email = (current_user.get("email") if current_user else None) or "HR"
    item = await add_application_to_roster(
        db=db,
        roster_id=roster_id,
        application_id=item_in.application_id,
        added_by=hr_email
    )
    return {"success": True, "item_id": item.id, "roster_id": roster_id}


@router.delete("/shortlists/{roster_id}/items/{application_id}")
async def remove_candidate_from_roster(
    roster_id: int,
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Remove an applicant from a roster.
    Returns status to Under Review unless still in another roster for the same position.
    """
    hr_email = (current_user.get("email") if current_user else None) or "HR"
    success = await remove_application_from_roster(
        db=db,
        roster_id=roster_id,
        application_id=application_id,
        removed_by=hr_email
    )
    if not success:
        raise HTTPException(status_code=404, detail="Applicant not found in this roster")
    return {"success": True, "message": "Applicant removed from roster"}


@router.patch("/shortlists/{roster_id}/items/{application_id}/stage")
async def update_roster_stage(
    roster_id: int,
    application_id: int,
    stage_update: ShortlistRosterItemStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Update applicant stage inside a roster (e.g. Interviewed, Passed initial interview, Not selected)."""
    hr_email = (current_user.get("email") if current_user else None) or "HR"
    item = await update_roster_item_stage(
        db=db,
        roster_id=roster_id,
        application_id=application_id,
        stage=stage_update.stage,
        updated_by=hr_email
    )
    if not item:
        raise HTTPException(status_code=404, detail="Applicant not found in this roster")
    return {"success": True, "stage": item.stage}


@router.patch("/shortlists/{roster_id}/archive")
async def archive_or_unarchive_shortlist_roster(
    roster_id: int,
    archived: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Archive or restore a shortlist roster."""
    hr_email = (current_user.get("email") if current_user else None) or "HR"
    result = await toggle_archive_shortlist_roster(db=db, roster_id=roster_id, archived=archived, updated_by=hr_email)
    if not result:
        raise HTTPException(status_code=404, detail="Shortlist roster not found")
    return result


@router.delete("/shortlists/{roster_id}")
async def delete_single_shortlist_roster(
    roster_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Delete a shortlist roster and restore unshared candidates to Under Review."""
    hr_email = (current_user.get("email") if current_user else None) or "HR"
    success = await delete_shortlist_roster(db=db, roster_id=roster_id, deleted_by=hr_email)
    if not success:
        raise HTTPException(status_code=404, detail="Shortlist roster not found")
    return {"success": True, "message": "Shortlist roster deleted successfully"}


# ─── UNIVERSAL SEARCH FOR HR (Item 4) ───────────────────────────────────────

@router.get("/universal-search", response_model=UniversalSearchResponse)
async def hr_universal_search(
    q: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Universal search across Applicants, Jobs, and Shortlists."""
    results = await universal_search_hr(db=db, query=q)
    return results


# ─── APPLICANT PROFILE FOR INTERVIEWS (Item 5) ───────────────────────────────

@router.get("/applicant-profile/{email}")
async def get_applicant_profile(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Complete applicant profile view for interviews:
    Contact, all applications, interview schedules & history, notes, call logs.
    Includes Data Privacy Act access logging.
    """
    hr_email = (current_user.get("email") if current_user else None) or "HR"
    profile = await get_applicant_comprehensive_profile(
        db=db,
        email=email,
        accessed_by=hr_email
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Applicant not found")
    return profile


@router.post("/applicant-profile/{email}/notes", response_model=HRCandidateNoteResponse)
async def add_applicant_note(
    email: str,
    note_in: HRCandidateNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """Add HR notes on an applicant's profile."""
    hr_email = (current_user.get("email") if current_user else None) or "HR"
    hr_name = current_user.get("fullname") if current_user else "HR Specialist"
    note = await add_candidate_hr_note(
        db=db,
        candidate_email=email,
        author_email=hr_email,
        author_name=hr_name,
        content=note_in.content
    )
    return note


@router.post("/compare")
async def compare_candidates(
    req: CandidateCompareRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Compare multiple candidates for HR evaluation.
    Enforces that each candidate is a unique individual (rejects duplicates with 422).
    Re-scores all candidates against the selected reference position and identifies transferable skills.
    """
    return await compare_candidates_service(
        db=db,
        application_ids=req.application_ids,
        reference_job_id=req.reference_job_id
    )



