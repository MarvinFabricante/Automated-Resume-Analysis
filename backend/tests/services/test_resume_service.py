import io
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import UploadFile
from app.services import resume_service
from app.schemas.resume_schema import ResumeCreate, ResumeUpdate
from app.models.candidate import Candidate


@pytest.mark.asyncio
async def test_parse_resume_file(db_session):
    dummy_bytes = b"Dummy PDF content for resume parser test"
    upload_file = UploadFile(
        filename="John_Doe_Resume.pdf",
        file=io.BytesIO(dummy_bytes)
    )

    mock_extracted = {
        "fullname": "John Doe",
        "email": "johndoe@example.com",
        "phone": "+639123456789",
        "skills": ["Python", "FastAPI"],
        "education": "BS Information Technology",
        "experience": "2 years experience"
    }

    with patch("app.services.resume_service.process_resume", return_value=mock_extracted), \
         patch("app.utils.supabase_storage.upload_resume", new_callable=AsyncMock) as mock_sb_upload:
        
        mock_sb_upload.return_value = {
            "public_url": "https://supabase.co/storage/v1/object/public/resume%20storage/resumes/123_John_Doe_Resume.pdf",
            "storage_path": "resumes/123_John_Doe_Resume.pdf"
        }

        result = await resume_service.parse_resume_file(db_session, upload_file)
        assert result is not None
        assert result["fullname"] == "John Doe"
        assert result["email"] == "johndoe@example.com"
        assert "file_url" in result
        assert "supabase" in result["file_url"]


@pytest.mark.asyncio
async def test_create_and_get_resume(db_session):
    cand = Candidate(
        fullname="Resume Owner",
        email="resume_owner@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add(cand)
    await db_session.flush()

    resume_in = ResumeCreate(
        candidate_id=cand.id,
        filename="owner_resume.pdf",
        file_url="https://example.com/owner_resume.pdf",
        parsed_data={"skills": ["Python", "SQL"]}
    )

    created = await resume_service.create_resume(db_session, resume_in)
    assert created.id is not None
    assert created.filename == "owner_resume.pdf"
    assert created.candidate_id == cand.id

    # Fetch by ID
    fetched = await resume_service.get_resume(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id

    # Fetch by candidate
    cand_resumes = await resume_service.get_resumes_by_candidate(db_session, cand.id)
    assert len(cand_resumes) >= 1
    assert any(r.id == created.id for r in cand_resumes)


@pytest.mark.asyncio
async def test_update_and_delete_resume(db_session):
    cand = Candidate(
        fullname="Resume Updater",
        email="resume_updater@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add(cand)
    await db_session.flush()

    resume_in = ResumeCreate(
        candidate_id=cand.id,
        filename="v1.pdf",
        file_url="https://example.com/v1.pdf",
        parsed_data={"version": 1}
    )
    created = await resume_service.create_resume(db_session, resume_in)

    # Update
    update_in = ResumeUpdate(
        filename="v2.pdf",
        parsed_data={"version": 2}
    )
    updated = await resume_service.update_resume(db_session, created.id, update_in)
    assert updated is not None
    assert updated.filename == "v2.pdf"
    assert updated.parsed_data["version"] == 2

    # Update non-existent
    assert await resume_service.update_resume(db_session, 999999, update_in) is None

    # Delete
    deleted = await resume_service.delete_resume(db_session, created.id)
    assert deleted is True

    # Delete non-existent
    assert await resume_service.delete_resume(db_session, 999999) is False
