import pytest
from app.repositories import candidate_repository
from app.models.candidate import Candidate
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_candidate_repo_crud(db_session):
    cand_data = {
        "fullname": "Candidate Repo Test",
        "email": "cand_repo@example.com",
        "password": hash_password("pass123"),
        "role": "CANDIDATE",
        "phone": "09123456789",
        "location": "Makati City"
    }

    # 1. Create candidate
    candidate = await candidate_repository.create(db_session, cand_data)
    assert candidate.id is not None
    assert candidate.email == "cand_repo@example.com"
    cand_id = candidate.id

    # 2. Get by id
    fetched = await candidate_repository.get_by_id(db_session, cand_id)
    assert fetched is not None
    assert fetched.fullname == "Candidate Repo Test"

    # 3. Update candidate
    updated = await candidate_repository.update(db_session, fetched, {
        "fullname": "Candidate Repo Updated",
        "location": "Taguig City"
    })
    assert updated.fullname == "Candidate Repo Updated"
    assert updated.location == "Taguig City"

    # Verify persistent state
    re_fetched = await candidate_repository.get_by_id(db_session, cand_id)
    assert re_fetched.fullname == "Candidate Repo Updated"
