import os
import time
import tempfile
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc

from app.models.physical_resume import PhysicalResume
from app.models.job_description import JobDescription
from app.models.user import User
from app.services.audit_service import record_activity
from app.services.notification_service import create_notification
from app.utils.cache import clear_cache_pattern

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".webp"}

def _format_size(size_bytes: Optional[int]) -> str:
    if not size_bytes:
        return "Unknown size"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def _get_mime_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "application/octet-stream")


async def store_physical_resume(
    db: AsyncSession,
    file: UploadFile,
    hr_id: Optional[int],
    data: Dict[str, Any]
) -> PhysicalResume:
    """
    Stores a physically submitted resume:
    1. Saves file to disk (uploads/physical_resumes/) & Supabase Storage (if configured).
    2. Runs resume text extraction if PDF/DOCX to index skills/data.
    3. Records physical filing details (cabinet/box, submission date, notes).
    4. Audits & sends notifications.
    """
    orig_filename = file.filename or "physical_resume.pdf"
    ext = os.path.splitext(orig_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed types: PDF, DOCX, DOC, PNG, JPG, JPEG, WEBP."
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    mime_type = _get_mime_type(orig_filename)
    timestamp = int(time.time())
    safe_name = f"{timestamp}_{orig_filename.replace(' ', '_')}"

    # 1. Save locally to uploads/physical_resumes/
    upload_dir = "uploads/physical_resumes"
    os.makedirs(upload_dir, exist_ok=True)
    local_file_path = os.path.join(upload_dir, safe_name)
    with open(local_file_path, "wb") as f:
        f.write(file_bytes)

    local_url = f"/{local_file_path}"
    file_url = local_url
    storage_path = None

    # 2. Try Supabase Storage upload if available
    try:
        from app.utils.supabase_storage import upload_resume
        sb_result = await upload_resume(
            file_bytes=file_bytes,
            original_filename=f"physical_{orig_filename}",
        )
        if sb_result and "public_url" in sb_result:
            file_url = sb_result["public_url"]
            storage_path = sb_result.get("storage_path")
            logger.info(f"Physical resume uploaded to Supabase Storage: {file_url}")
    except Exception as sb_err:
        logger.warning(f"Supabase upload skipped/failed for physical resume, using local storage: {sb_err}")

    # 3. Optional auto-parse for text & skills extraction
    parsed_data = None
    if ext in {".pdf", ".docx", ".doc"}:
        try:
            from app.extractors.resume_processor import process_resume
            tmp_dir = tempfile.mkdtemp()
            tmp_path = os.path.join(tmp_dir, safe_name)
            with open(tmp_path, "wb") as tmp_f:
                tmp_f.write(file_bytes)
            extracted = process_resume(tmp_path, ext.strip("."))
            if extracted:
                parsed_data = extracted
                logger.info(f"Auto-extracted data from physical resume: {list(extracted.keys())}")
        except Exception as parse_err:
            logger.debug(f"Auto-parsing physical resume skipped: {parse_err}")

    # Resolve target job title if job_id provided
    target_job_id = data.get("target_job_id")
    target_job_title = data.get("target_job_title")
    if target_job_id and not target_job_title:
        try:
            job_stmt = select(JobDescription.job_title).where(JobDescription.id == int(target_job_id))
            job_res = await db.execute(job_stmt)
            job_row = job_res.scalar_one_or_none()
            if job_row:
                target_job_title = job_row
        except Exception as e:
            logger.warning(f"Error fetching job title for ID {target_job_id}: {e}")

    # Parse submission date
    submission_date = data.get("submission_date")
    if isinstance(submission_date, str):
        try:
            submission_date = datetime.fromisoformat(submission_date.replace("Z", "+00:00"))
        except Exception:
            submission_date = datetime.utcnow()
    elif not submission_date:
        submission_date = datetime.utcnow()

    # 4. Create PhysicalResume DB record
    physical_resume = PhysicalResume(
        hr_id=hr_id,
        candidate_name=data.get("candidate_name", "").strip(),
        candidate_email=data.get("candidate_email", "").strip() or None,
        candidate_phone=data.get("candidate_phone", "").strip() or None,
        target_job_id=int(target_job_id) if target_job_id else None,
        target_job_title=target_job_title,
        physical_location=data.get("physical_location", "").strip() or "General HR Archive",
        submission_date=submission_date,
        filename=orig_filename,
        file_url=file_url,
        storage_path=storage_path,
        file_size=file_size,
        file_type=mime_type,
        status=data.get("status") or "RECEIVED",
        notes=data.get("notes", "").strip() or None,
        parsed_data=parsed_data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(physical_resume)
    await db.commit()
    await db.refresh(physical_resume)

    # 5. Record activity and send notification
    try:
        await record_activity(
            db=db,
            user_id=hr_id,
            action="STORE_PHYSICAL_RESUME",
            target=f"PhysicalResume #{physical_resume.id}",
            details=f"Stored hard-copy resume for {physical_resume.candidate_name}. Filing reference: {physical_resume.physical_location}"
        )
        await create_notification(
            db=db,
            title="Physical Resume Stored",
            message=f"Hard-copy resume for {physical_resume.candidate_name} archived in {physical_resume.physical_location}.",
            type="physical_resume",
            target_role="HR",
            sender_role="HR"
        )
    except Exception as log_err:
        logger.warning(f"Failed to record activity or notification for physical resume: {log_err}")

    await clear_cache_pattern("physical_resumes*")
    return physical_resume


async def get_physical_resumes(
    db: AsyncSession,
    search: Optional[str] = None,
    status: Optional[str] = None,
    job_id: Optional[int] = None,
    page: int = 1,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Lists physical resumes with search, filter, and pagination.
    """
    stmt = select(PhysicalResume)

    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                PhysicalResume.candidate_name.ilike(search_term),
                PhysicalResume.candidate_email.ilike(search_term),
                PhysicalResume.candidate_phone.ilike(search_term),
                PhysicalResume.physical_location.ilike(search_term),
                PhysicalResume.target_job_title.ilike(search_term),
                PhysicalResume.notes.ilike(search_term),
                PhysicalResume.filename.ilike(search_term),
            )
        )

    if status and status.upper() != "ALL":
        stmt = stmt.where(PhysicalResume.status == status.upper())

    if job_id:
        stmt = stmt.where(PhysicalResume.target_job_id == job_id)

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count_res = await db.execute(count_stmt)
    total_count = total_count_res.scalar() or 0

    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.order_by(desc(PhysicalResume.created_at)).offset(offset).limit(limit)

    result = await db.execute(stmt)
    items = result.scalars().all()

    # Format items
    formatted_items = []
    for item in items:
        hr_name = None
        if item.hr_staff:
            hr_name = item.hr_staff.fullname

        formatted_items.append({
            "id": item.id,
            "hr_id": item.hr_id,
            "hr_name": hr_name,
            "candidate_name": item.candidate_name,
            "candidate_email": item.candidate_email,
            "candidate_phone": item.candidate_phone,
            "target_job_id": item.target_job_id,
            "target_job_title": item.target_job_title or (item.target_job.job_title if item.target_job else None),
            "physical_location": item.physical_location,
            "submission_date": item.submission_date,
            "filename": item.filename,
            "file_url": item.file_url,
            "storage_path": item.storage_path,
            "file_size": item.file_size,
            "formatted_file_size": _format_size(item.file_size),
            "file_type": item.file_type,
            "status": item.status,
            "notes": item.notes,
            "parsed_data": item.parsed_data,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        })

    total_pages = max(1, (total_count + limit - 1) // limit)

    return {
        "items": formatted_items,
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


async def get_physical_resume_by_id(db: AsyncSession, resume_id: int) -> Optional[Dict[str, Any]]:
    stmt = select(PhysicalResume).where(PhysicalResume.id == resume_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return None

    hr_name = item.hr_staff.fullname if item.hr_staff else None

    return {
        "id": item.id,
        "hr_id": item.hr_id,
        "hr_name": hr_name,
        "candidate_name": item.candidate_name,
        "candidate_email": item.candidate_email,
        "candidate_phone": item.candidate_phone,
        "target_job_id": item.target_job_id,
        "target_job_title": item.target_job_title or (item.target_job.job_title if item.target_job else None),
        "physical_location": item.physical_location,
        "submission_date": item.submission_date,
        "filename": item.filename,
        "file_url": item.file_url,
        "storage_path": item.storage_path,
        "file_size": item.file_size,
        "formatted_file_size": _format_size(item.file_size),
        "file_type": item.file_type,
        "status": item.status,
        "notes": item.notes,
        "parsed_data": item.parsed_data,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


async def update_physical_resume(
    db: AsyncSession,
    resume_id: int,
    update_data: Dict[str, Any],
    hr_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    stmt = select(PhysicalResume).where(PhysicalResume.id == resume_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return None

    if "candidate_name" in update_data and update_data["candidate_name"]:
        item.candidate_name = update_data["candidate_name"].strip()
    if "candidate_email" in update_data:
        item.candidate_email = update_data["candidate_email"].strip() if update_data["candidate_email"] else None
    if "candidate_phone" in update_data:
        item.candidate_phone = update_data["candidate_phone"].strip() if update_data["candidate_phone"] else None
    if "target_job_id" in update_data:
        item.target_job_id = int(update_data["target_job_id"]) if update_data["target_job_id"] else None
    if "target_job_title" in update_data:
        item.target_job_title = update_data["target_job_title"]
    if "physical_location" in update_data and update_data["physical_location"]:
        item.physical_location = update_data["physical_location"].strip()
    if "status" in update_data and update_data["status"]:
        item.status = update_data["status"].upper()
    if "notes" in update_data:
        item.notes = update_data["notes"]
    if "submission_date" in update_data and update_data["submission_date"]:
        sd = update_data["submission_date"]
        if isinstance(sd, str):
            try:
                item.submission_date = datetime.fromisoformat(sd.replace("Z", "+00:00"))
            except Exception:
                pass
        elif isinstance(sd, datetime):
            item.submission_date = sd

    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)

    try:
        await record_activity(
            db=db,
            user_id=hr_id,
            action="UPDATE_PHYSICAL_RESUME",
            target=f"PhysicalResume #{item.id}",
            details=f"Updated details for physical resume of {item.candidate_name} (Status: {item.status})"
        )
    except Exception:
        pass

    await clear_cache_pattern("physical_resumes*")
    return await get_physical_resume_by_id(db, resume_id)


async def delete_physical_resume(db: AsyncSession, resume_id: int, hr_id: Optional[int] = None) -> bool:
    stmt = select(PhysicalResume).where(PhysicalResume.id == resume_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return False

    candidate_name = item.candidate_name
    file_url = item.file_url

    # Delete local file if it exists
    if file_url and file_url.startswith("/uploads/"):
        rel_path = file_url.lstrip("/")
        if os.path.exists(rel_path):
            try:
                os.remove(rel_path)
            except Exception as e:
                logger.warning(f"Could not remove local file {rel_path}: {e}")

    # Delete Supabase storage file if present
    if item.storage_path:
        try:
            from app.utils.supabase_storage import delete_resume
            await delete_resume(item.storage_path)
        except Exception as sb_e:
            logger.debug(f"Supabase delete skipped/failed: {sb_e}")

    await db.delete(item)
    await db.commit()

    try:
        await record_activity(
            db=db,
            user_id=hr_id,
            action="DELETE_PHYSICAL_RESUME",
            target=f"PhysicalResume #{resume_id}",
            details=f"Permanently removed physical resume record for {candidate_name}"
        )
    except Exception:
        pass

    await clear_cache_pattern("physical_resumes*")
    return True


async def get_physical_resume_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    Returns aggregated stats for physical resumes storage:
    total count, counts by status, received this week, received this month, top jobs.
    """
    total_res = await db.execute(select(func.count(PhysicalResume.id)))
    total_stored = total_res.scalar() or 0

    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    month_res = await db.execute(
        select(func.count(PhysicalResume.id)).where(PhysicalResume.created_at >= month_ago)
    )
    received_this_month = month_res.scalar() or 0

    week_res = await db.execute(
        select(func.count(PhysicalResume.id)).where(PhysicalResume.created_at >= week_ago)
    )
    received_this_week = week_res.scalar() or 0

    # Counts by status
    status_stmt = select(PhysicalResume.status, func.count(PhysicalResume.id)).group_by(PhysicalResume.status)
    status_res = await db.execute(status_stmt)
    status_counts = {row[0]: row[1] for row in status_res.fetchall()}

    # Top positions
    jobs_stmt = (
        select(PhysicalResume.target_job_title, func.count(PhysicalResume.id))
        .where(PhysicalResume.target_job_title.isnot(None))
        .group_by(PhysicalResume.target_job_title)
        .order_by(desc(func.count(PhysicalResume.id)))
        .limit(5)
    )
    jobs_res = await db.execute(jobs_stmt)
    top_jobs = [{"job_title": row[0], "count": row[1]} for row in jobs_res.fetchall()]

    return {
        "total_stored": total_stored,
        "received_this_month": received_this_month,
        "received_this_week": received_this_week,
        "status_counts": status_counts,
        "top_departments_or_jobs": top_jobs,
    }


async def get_physical_resume_file(db: AsyncSession, resume_id: int) -> Tuple[bytes, str, str]:
    """
    Returns (file_bytes, filename, mime_type) for inline viewing or attachment downloading.
    """
    stmt = select(PhysicalResume).where(PhysicalResume.id == resume_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Physical resume not found")

    filename = item.filename
    mime_type = item.file_type or _get_mime_type(filename)

    # 1. Check local file path
    if item.file_url:
        local_path = item.file_url.split("?")[0].lstrip("/")
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read(), filename, mime_type

    # 2. Check Supabase download if storage_path is recorded
    if item.storage_path:
        try:
            from app.utils.supabase_storage import download_resume
            file_bytes = await download_resume(item.storage_path)
            return file_bytes, filename, mime_type
        except Exception as e:
            logger.warning(f"Could not download from Supabase: {e}")

    # 3. Check public URL HTTP fetch as fallback
    if item.file_url and item.file_url.startswith("http"):
        try:
            import urllib.request
            req = urllib.request.Request(item.file_url, headers={"User-Agent": "MariwasaARAS/1.0"})
            with urllib.request.urlopen(req) as resp:
                return resp.read(), filename, mime_type
        except Exception as e:
            logger.warning(f"HTTP fallback download failed: {e}")

    raise HTTPException(status_code=404, detail="Physical resume document file could not be retrieved.")
