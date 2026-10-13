from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Request
import shutil
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.utils.database import get_db
from app.schemas.candidate_schema import CandidateCreate, CandidateResponse, CandidateUpdate
from app.services import candidate_service, resume_service
from app.utils.limiter import limiter
from app.utils.cache import cache_response, clear_cache_pattern, delete_cache


router = APIRouter(prefix="/candidate", tags=["Candidates"])



@router.get("/profile/{candidate_id}", response_model=CandidateResponse)
@cache_response("candidate_profile", ttl=1800)
async def get_profile(candidate_id: int, db: AsyncSession = Depends(get_db)):
    profile = await candidate_service.get_candidate_profile(db, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return profile

@router.put("/profile/{candidate_id}", response_model=CandidateResponse)
async def update_profile(candidate_id: int, profile_in: CandidateUpdate, db: AsyncSession = Depends(get_db)):
    updated_profile = await candidate_service.update_candidate_profile(db, candidate_id, profile_in)
    if updated_profile:
        await clear_cache_pattern(f"candidate_profile:*\"candidate_id\": {candidate_id}*")
    if not updated_profile:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return updated_profile

@router.post("/upload-profile-image/{candidate_id}")
async def upload_profile_image(
    candidate_id: int,
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
            original_filename=file.filename or f"candidate_{candidate_id}.png",
            user_role="candidate",
            user_id=candidate_id,
        )
        image_url = result["public_url"]
        print(f"Uploaded candidate {candidate_id} profile image to Supabase: {image_url}")
    except Exception as e:
        print(f"Supabase profile upload failed, falling back to local: {e}")
        upload_dir = "uploads/profile_images"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_extension = os.path.splitext(file.filename or "")[1] or ".png"
        file_name = f"candidate_{candidate_id}{file_extension}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        import time
        image_url = f"/{file_path}?t={int(time.time())}"

    # Update database and clear cache
    await candidate_service.update_candidate_profile(db, candidate_id, CandidateUpdate(profile_image_url=image_url))
    await clear_cache_pattern(f"candidate_profile:*\"candidate_id\": {candidate_id}*")
    return {"image_url": image_url}


@router.post("/register", response_model=CandidateResponse, status_code=status.HTTP_200_OK)
async def register_candidate(
    candidate_in: CandidateCreate, 
    db: AsyncSession = Depends(get_db)
):
    try:
        return await candidate_service.create_candidate_profile(db, candidate_in)
        
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    except Exception as e:
        await db.rollback()
        print(f"Registration Error: {str(e)}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating your account."
        )



@router.post("/parse-resume", tags=["Candidates"])
@limiter.limit("5/minute")
async def parse_resume(request: Request, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Test endpoint to parse an uploaded resume and return extracted data.
    """
    extracted_data = await resume_service.parse_resume_file(db, file)
    if not extracted_data:
        raise HTTPException(status_code=400, detail="Failed to parse resume or unsupported file type.")
    
    # Invalidate HR stats cache
    await delete_cache("resume_count:{}")
    await delete_cache("app_stats:{}")
    
    return extracted_data
