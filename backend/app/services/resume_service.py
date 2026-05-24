import os
import shutil
import time
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.extractors.resume_processor import process_resume
from app.models.resume import Resume
from app.schemas.resume_schema import ResumeCreate, ResumeUpdate
from app.services.notification_service import create_notification
from app.repositories.resume_repository import ResumeRepository

async def parse_resume_file(db: AsyncSession, file: UploadFile) -> dict:
    """
    Saves the uploaded file permanently and parses it using the extractors.
    """
    # Create permanent directory if it doesn't exist
    upload_dir = "uploads/resumes"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_extension = os.path.splitext(file.filename)[1].strip('.')
    # Generate a unique filename to prevent collisions
    timestamp = int(time.time())
    safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
    permanent_file_path = os.path.join(upload_dir, safe_filename)
    
    try:
        # Save uploaded file to permanent location
        print(f"DEBUG: Saving uploaded file to {permanent_file_path}")
        with open(permanent_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process the resume
        print(f"DEBUG: Starting processing for {safe_filename}")
        extracted_data = process_resume(permanent_file_path, file_extension)
        
        if not extracted_data:
            print("DEBUG: process_resume returned empty data (Parsing Failed)")
        else:
            print(f"DEBUG: Successfully extracted data for {extracted_data.get('fullname', 'unknown')}")
            # Add file information to extracted data so it can be saved later
            extracted_data["file_url"] = f"http://localhost:8000/{permanent_file_path}"
            extracted_data["filename"] = safe_filename

        # Trigger notification
        name = extracted_data.get("fullname", "A candidate")
        await create_notification(
            db=db,
            title="Resume Parsed",
            message=f"{name}'s resume has been uploaded and parsed.",
            type="upload"
        )
        
        return extracted_data
        
    except Exception as e:
        import traceback
        print(f"Error in parse_resume_file: {e}")
        traceback.print_exc()
        return {}

async def create_resume(db: AsyncSession, resume_in: ResumeCreate) -> Resume:
    """Create a new resume and trigger notification."""
    resume_data = resume_in.model_dump()
    new_resume = await ResumeRepository.create(db, resume_data)
    
    await create_notification(
        db=db,
        title="Resume Saved",
        message="A candidate saved their parsed resume to their profile.",
        type="upload"
    )
    
    return new_resume

async def get_resume(db: AsyncSession, resume_id: int) -> Resume | None:
    """Get a resume by ID."""
    return await ResumeRepository.get_by_id(db, resume_id)

async def get_resumes_by_candidate(db: AsyncSession, candidate_id: int) -> list[Resume]:
    """Get all resumes for a candidate."""
    return await ResumeRepository.get_by_candidate_id(db, candidate_id)

async def update_resume(db: AsyncSession, resume_id: int, resume_in: ResumeUpdate) -> Resume | None:
    """Update a resume."""
    resume = await ResumeRepository.get_by_id(db, resume_id)
    if not resume:
        return None
        
    update_data = resume_in.model_dump(exclude_unset=True)
    return await ResumeRepository.update(db, resume, update_data)

async def delete_resume(db: AsyncSession, resume_id: int) -> bool:
    """Delete a resume."""
    resume = await ResumeRepository.get_by_id(db, resume_id)
    if not resume:
        return False
        
    await ResumeRepository.delete(db, resume)
