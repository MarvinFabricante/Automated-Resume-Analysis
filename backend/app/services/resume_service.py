import os
import shutil
import time
import tempfile
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.extractors.resume_processor import process_resume
from app.models.resume import Resume
from app.schemas.resume_schema import ResumeCreate, ResumeUpdate
from app.services.notification_service import create_notification
from app.repositories.resume_repository import ResumeRepository

import logging
logger = logging.getLogger(__name__)


class ResumeService:
    async def parse_resume_file(self, db: AsyncSession, file: UploadFile) -> dict:
        """
        Saves the uploaded file to Supabase Storage and parses it using the extractors.
        Falls back to local storage if Supabase is unavailable.
        """
        file_extension = os.path.splitext(file.filename)[1].strip('.')
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"

        # Read file bytes for Supabase upload
        file_bytes = await file.read()
        await file.seek(0)  # Reset file pointer for potential local processing

        # Write to a temporary file for the resume processor (it needs a file path)
        tmp_dir = tempfile.mkdtemp()
        tmp_file_path = os.path.join(tmp_dir, safe_filename)

        try:
            with open(tmp_file_path, "wb") as buffer:
                buffer.write(file_bytes)

            # Process / parse the resume from the temp file
            logger.info(f"Processing resume: {safe_filename}")
            extracted_data = process_resume(tmp_file_path, file_extension)

            if not extracted_data:
                logger.warning("process_resume returned empty data (Parsing Failed)")
            else:
                logger.info(f"Successfully extracted data for {extracted_data.get('fullname', 'unknown')}")

            # Upload to Supabase Storage
            supabase_url = None
            storage_path = None
            try:
                from app.utils.supabase_storage import upload_resume
                result = await upload_resume(
                    file_bytes=file_bytes,
                    original_filename=file.filename,
                )
                supabase_url = result["public_url"]
                storage_path = result["storage_path"]
                logger.info(f"Resume uploaded to Supabase: {supabase_url}")
            except Exception as e:
                logger.warning(f"Supabase upload failed, falling back to local: {e}")
                # Fallback: save locally
                upload_dir = "uploads/resumes"
                os.makedirs(upload_dir, exist_ok=True)
                permanent_path = os.path.join(upload_dir, safe_filename)
                with open(permanent_path, "wb") as f:
                    f.write(file_bytes)
                supabase_url = f"http://localhost:8000/{permanent_path}"

            if extracted_data:
                extracted_data["file_url"] = supabase_url
                extracted_data["filename"] = safe_filename
                if storage_path:
                    extracted_data["storage_path"] = storage_path

            # Trigger notification
            name = extracted_data.get("fullname", "A candidate") if extracted_data else "A candidate"
            await create_notification(
                db=db,
                title="Resume Parsed",
                message=f"{name}'s resume has been uploaded and parsed.",
                type="upload"
            )

            return extracted_data or {}

        except Exception as e:
            import traceback
            logger.error(f"Error in parse_resume_file: {e}")
            traceback.print_exc()
            return {}
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
                os.rmdir(tmp_dir)
            except OSError:
                pass

    async def create_resume(self, db: AsyncSession, resume_in: ResumeCreate) -> Resume:
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

    async def get_resume(self, db: AsyncSession, resume_id: int) -> Resume | None:
        """Get a resume by ID."""
        return await ResumeRepository.get_by_id(db, resume_id)

    async def get_resumes_by_candidate(self, db: AsyncSession, candidate_id: int) -> list[Resume]:
        """Get all resumes for a candidate."""
        return await ResumeRepository.get_by_candidate_id(db, candidate_id)

    async def update_resume(self, db: AsyncSession, resume_id: int, resume_in: ResumeUpdate) -> Resume | None:
        """Update a resume."""
        resume = await ResumeRepository.get_by_id(db, resume_id)
        if not resume:
            return None

        update_data = resume_in.model_dump(exclude_unset=True)
        return await ResumeRepository.update(db, resume, update_data)

    async def delete_resume(self, db: AsyncSession, resume_id: int) -> bool:
        """Delete a resume and its file from Supabase Storage."""
        resume = await ResumeRepository.get_by_id(db, resume_id)
        if not resume:
            return False

        # Try to delete from Supabase if the URL is a Supabase URL
        if resume.file_url and "supabase" in (resume.file_url or ""):
            try:
                from app.utils.supabase_storage import delete_resume as sb_delete
                # Extract storage path from the URL
                # URL format: https://<ref>.supabase.co/storage/v1/object/public/<bucket>/<path>
                url = resume.file_url
                bucket_marker = "/object/public/resume%20storage/"
                if bucket_marker in url:
                    storage_path = url.split(bucket_marker, 1)[1].split("?")[0]
                    await sb_delete(storage_path)
                    logger.info(f"Deleted resume file from Supabase: {storage_path}")
            except Exception as e:
                logger.warning(f"Failed to delete resume from Supabase: {e}")

        await ResumeRepository.delete(db, resume)
        return True


resume_service = ResumeService()


async def parse_resume_file(db: AsyncSession, file: UploadFile) -> dict:
    return await resume_service.parse_resume_file(db, file)


async def create_resume(db: AsyncSession, resume_in: ResumeCreate) -> Resume:
    return await resume_service.create_resume(db, resume_in)


async def get_resume(db: AsyncSession, resume_id: int) -> Resume | None:
    return await resume_service.get_resume(db, resume_id)


async def get_resumes_by_candidate(db: AsyncSession, candidate_id: int) -> list[Resume]:
    return await resume_service.get_resumes_by_candidate(db, candidate_id)


async def update_resume(db: AsyncSession, resume_id: int, resume_in: ResumeUpdate) -> Resume | None:
    return await resume_service.update_resume(db, resume_id, resume_in)


async def delete_resume(db: AsyncSession, resume_id: int) -> bool:
    return await resume_service.delete_resume(db, resume_id)
