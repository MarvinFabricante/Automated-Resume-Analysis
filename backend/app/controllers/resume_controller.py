from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import io

from app.utils.database import get_db
from app.schemas.resume_schema import ResumeCreate, ResumeResponse, ResumeUpdate
from app.services import resume_service
from app.utils.cache import cache_response, clear_cache_pattern


router = APIRouter(prefix="/resumes", tags=["Resumes"])

@router.post("/", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(resume_in: ResumeCreate, db: AsyncSession = Depends(get_db)):
    """
    Store a new resume in the database.
    """
    result = await resume_service.create_resume(db, resume_in)
    await clear_cache_pattern("cand_resumes*")
    await clear_cache_pattern("storage_resumes*")
    return result

@router.get("/{resume_id}", response_model=ResumeResponse)
@cache_response("resume", ttl=600)
async def get_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific resume by ID.
    """
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume

@router.get("/candidate/{candidate_id}", response_model=List[ResumeResponse])
@cache_response("cand_resumes", ttl=600)
async def get_resumes_by_candidate(candidate_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all resumes for a specific candidate.
    """
    return await resume_service.get_resumes_by_candidate(db, candidate_id)

@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(resume_id: int, resume_in: ResumeUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing resume.
    """
    updated_resume = await resume_service.update_resume(db, resume_id, resume_in)
    if not updated_resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    await clear_cache_pattern(f"resume:*resume_id\": {resume_id}*")
    await clear_cache_pattern("cand_resumes*")
    return updated_resume

@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a resume from the database and Supabase Storage.
    """
    success = await resume_service.delete_resume(db, resume_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")
    await clear_cache_pattern(f"resume:*resume_id\": {resume_id}*")
    await clear_cache_pattern("cand_resumes*")
    await clear_cache_pattern("storage_resumes*")
    return None


# ── Supabase Storage Endpoints ──────────────────────────────────────


@router.post("/upload", tags=["Resumes"])
async def upload_resume_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a resume file to Supabase Storage and return the public URL.
    Does NOT parse the file — use /candidate/parse-resume for parsing.
    """
    file_bytes = await file.read()

    try:
        from app.utils.supabase_storage import upload_resume
        result = await upload_resume(
            file_bytes=file_bytes,
            original_filename=file.filename,
        )
        response_data = {
            "message": "Resume uploaded successfully",
            "public_url": result["public_url"],
            "storage_path": result["storage_path"],
            "filename": result["filename"],
        }
        await clear_cache_pattern("storage_resumes*")
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload resume: {str(e)}"
        )


@router.get("/download/{storage_path:path}", tags=["Resumes"])
async def download_resume_file(storage_path: str):
    """
    Download a resume file from Supabase Storage.
    The storage_path should be the path within the bucket (e.g. resumes/1234_file.pdf).
    """
    try:
        from app.utils.supabase_storage import download_resume
        file_bytes = await download_resume(storage_path)

        # Determine content type from filename
        import os
        filename = os.path.basename(storage_path)
        ext = os.path.splitext(filename)[1].lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }
        content_type = mime_map.get(ext, "application/octet-stream")

        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Resume file not found: {str(e)}"
        )


@router.get("/storage/list", tags=["Resumes"])
@cache_response("storage_resumes", ttl=300)
async def list_stored_resumes():
    """
    List all resume files stored in Supabase Storage.
    """
    try:
        from app.utils.supabase_storage import list_resumes, get_public_url
        files = await list_resumes()

        result = []
        for f in files:
            file_info = {
                "name": f.get("name"),
                "id": f.get("id"),
                "created_at": f.get("created_at"),
                "updated_at": f.get("updated_at"),
                "metadata": f.get("metadata"),
            }
            # Add public URL if it's a file (has an id)
            if f.get("id"):
                file_info["public_url"] = get_public_url(f"resumes/{f['name']}")
            result.append(file_info)

        return {"files": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list resumes: {str(e)}"
        )
