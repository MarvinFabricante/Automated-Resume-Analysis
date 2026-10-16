import pytest
from app.models.candidate import Candidate


@pytest.mark.asyncio
async def test_resume_crud_endpoints(client, db_session):
    cand = Candidate(
        fullname="Resume Controller Candidate",
        email="resume_ctrl_cand@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add(cand)
    await db_session.commit()

    # Create Resume
    create_payload = {
        "candidate_id": cand.id,
        "filename": "initial_resume.pdf",
        "file_url": "https://example.com/resumes/initial.pdf",
        "parsed_data": {"skills": ["Python", "FastAPI"]}
    }
    create_res = await client.post("/resumes/", json=create_payload)
    assert create_res.status_code == 201
    data = create_res.json()
    resume_id = data["id"]
    assert data["filename"] == "initial_resume.pdf"
    assert data["candidate_id"] == cand.id

    # Get Resume by ID
    get_res = await client.get(f"/resumes/{resume_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == resume_id

    # Get Resumes by Candidate
    by_cand_res = await client.get(f"/resumes/candidate/{cand.id}")
    assert by_cand_res.status_code == 200
    assert len(by_cand_res.json()) >= 1
    assert any(r["id"] == resume_id for r in by_cand_res.json())

    # Update Resume
    update_payload = {
        "filename": "updated_resume.pdf",
        "parsed_data": {"skills": ["Python", "FastAPI", "PostgreSQL"]}
    }
    put_res = await client.put(f"/resumes/{resume_id}", json=update_payload)
    assert put_res.status_code == 200
    assert put_res.json()["filename"] == "updated_resume.pdf"

    # Delete Resume (204)
    del_res = await client.delete(f"/resumes/{resume_id}")
    assert del_res.status_code == 204

    # Verify deleted
    assert (await client.get(f"/resumes/{resume_id}")).status_code == 404
