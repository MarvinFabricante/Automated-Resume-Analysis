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
    # Create directory if it doesn't exist
    upload_dir = "uploads/profile_images"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Generate file path
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"candidate_{candidate_id}{file_extension}"
    file_path = os.path.join(upload_dir, file_name)
    
    # Save file
    print(f"Uploading image for candidate {candidate_id}: {file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    print(f"File saved to {file_path}")
    
    # Update database with a cache-busting timestamp
    import time
    image_url = f"http://localhost:8000/{file_path}?t={int(time.time())}"
    print(f"Updating database with image_url: {image_url}")
    await candidate_service.update_candidate_profile(db, candidate_id, CandidateUpdate(profile_image_url=image_url))
    await clear_cache_pattern(f"candidate_profile:*\"candidate_id\": {candidate_id}*")
    print("Database updated successfully")
    
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
