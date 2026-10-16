import pytest
from app.repositories import resume_repository
from app.models.candidate import Candidate
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_resume_repo_lifecycle(db_session):
    cand = Candidate(
        fullname="Resume Owner",
        email="repo_resume_owner@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE"
    )
    db_session.add(cand)
    await db_session.commit()
    cand_id = cand.id

    # 1. Create resume
    resume_data = {
        "candidate_id": cand_id,
        "filename": "owner_cv.pdf",
        "file_url": "https://storage.example.com/owner_cv.pdf",
        "parsed_data": {"skills": ["Python", "SQL"], "experience_years": 3}
    }
    created = await resume_repository.create(db_session, resume_data)
    assert created.id is not None
    assert created.filename == "owner_cv.pdf"
    res_id = created.id

    # 2. Get by ID
    by_id = await resume_repository.get_by_id(db_session, res_id)
    assert by_id is not None
    assert by_id.id == res_id

    # 3. Get by candidate ID
    by_cand = await resume_repository.get_by_candidate_id(db_session, cand_id)
    assert len(by_cand) >= 1
    assert any(r.id == res_id for r in by_cand)

    # 4. Update resume
    updated = await resume_repository.update(db_session, by_id, {
        "filename": "owner_cv_v2.pdf",
        "parsed_data": {"skills": ["Python", "SQL", "Docker"], "experience_years": 4}
    })
    assert updated.filename == "owner_cv_v2.pdf"
    assert "Docker" in updated.parsed_data["skills"]

    # 5. Delete resume
    await resume_repository.delete(db_session, updated)
    assert await resume_repository.get_by_id(db_session, res_id) is None
