import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db
from app.utils.auth import get_current_user, get_optional_current_user
from app.schemas.physical_resume_schema import (
    PhysicalResumeResponse,
    PhysicalResumeListResponse,
    PhysicalResumeUpdate,
    PhysicalResumeStats,
)
from app.services import physical_resume_service
from app.utils.cache import cache_response, clear_cache_pattern

router = APIRouter(prefix="/hr/physical-resumes", tags=["Physical Resume Storage"])


@router.post("/upload", response_model=PhysicalResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_physical_resume(
    file: UploadFile = File(...),
    candidate_name: str = Form(...),
    candidate_email: Optional[str] = Form(None),
    candidate_phone: Optional[str] = Form(None),
    target_job_id: Optional[int] = Form(None),
    target_job_title: Optional[str] = Form(None),
    physical_location: Optional[str] = Form(None),
    submission_date: Optional[str] = Form(None),
    status_val: Optional[str] = Form("RECEIVED"),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Upload and store a physically submitted resume scan with filing location reference.
    """
    hr_id = current_user.get("id") if current_user else None
    form_data = {
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "candidate_phone": candidate_phone,
        "target_job_id": target_job_id,
        "target_job_title": target_job_title,
        "physical_location": physical_location or "General HR Archive",
        "submission_date": submission_date,
        "status": status_val,
        "notes": notes,
    }

    result = await physical_resume_service.store_physical_resume(
        db=db,
        file=file,
        hr_id=hr_id,
        data=form_data
    )

    formatted = await physical_resume_service.get_physical_resume_by_id(db, result.id)
    return formatted


@router.get("/", response_model=PhysicalResumeListResponse)
@cache_response("physical_resumes_list", ttl=60)
async def list_physical_resumes(
    search: Optional[str] = Query(None, description="Search by candidate name, filing reference, email, job, or notes"),
    status: Optional[str] = Query(None, description="Filter by status (RECEIVED, UNDER_REVIEW, SHORTLISTED, HIRED, ARCHIVED)"),
    job_id: Optional[int] = Query(None, description="Filter by target job ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve stored physical resumes with search, filter, and pagination.
    """
    return await physical_resume_service.get_physical_resumes(
        db=db,
        search=search,
        status=status,
        job_id=job_id,
        page=page,
        limit=limit,
    )


@router.get("/stats", response_model=PhysicalResumeStats)
@cache_response("physical_resumes_stats", ttl=120)
async def get_physical_resume_stats(db: AsyncSession = Depends(get_db)):
    """
    Get summary statistics for physical resumes storage.
    """
    return await physical_resume_service.get_physical_resume_stats(db)


@router.get("/{resume_id}", response_model=PhysicalResumeResponse)
async def get_physical_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a single stored physical resume record by ID.
    """
    res = await physical_resume_service.get_physical_resume_by_id(db, resume_id)
    if not res:
        raise HTTPException(status_code=404, detail="Physical resume record not found")
    return res


@router.put("/{resume_id}", response_model=PhysicalResumeResponse)
async def update_physical_resume(
    resume_id: int,
    body: PhysicalResumeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Update details, physical filing location, status, or notes of a physical resume.
    """
    hr_id = current_user.get("id") if current_user else None
    update_data = body.dict(exclude_unset=True)
    updated = await physical_resume_service.update_physical_resume(
        db=db,
        resume_id=resume_id,
        update_data=update_data,
        hr_id=hr_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Physical resume record not found")
    return updated


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_physical_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Permanently delete a physical resume record and its stored file.
    """
    hr_id = current_user.get("id") if current_user else None
    deleted = await physical_resume_service.delete_physical_resume(db, resume_id, hr_id=hr_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Physical resume record not found")
    return None


@router.get("/{resume_id}/view")
async def view_physical_resume_file(resume_id: int, db: AsyncSession = Depends(get_db)):
    """
    Stream resume file with inline Content-Disposition so it can be previewed/viewed directly
    in the browser or an iframe without triggering a file download.
    """
    file_bytes, filename, mime_type = await physical_resume_service.get_physical_resume_file(db, resume_id)
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/{resume_id}/download")
async def download_physical_resume_file(resume_id: int, db: AsyncSession = Depends(get_db)):
    """
    Download resume file with attachment Content-Disposition so user can save the file locally.
    """
    file_bytes, filename, mime_type = await physical_resume_service.get_physical_resume_file(db, resume_id)
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
