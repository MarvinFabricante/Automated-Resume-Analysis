import pytest
import io
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_register_and_get_candidate_profile(client):
    reg_payload = {
        "fullname": "Candidate API User",
        "email": "cand_api@example.com",
        "password": "password123",
        "experience_years": 2
    }
    reg_res = await client.post("/candidate/register", json=reg_payload)
    assert reg_res.status_code == 200
    data = reg_res.json()
    cand_id = data["id"]
    assert data["fullname"] == "Candidate API User"
    assert data["email"] == "cand_api@example.com"

    # Get profile
    get_res = await client.get(f"/candidate/profile/{cand_id}")
    assert get_res.status_code == 200
    profile_data = get_res.json()
    assert profile_data["id"] == cand_id
    assert profile_data["email"] == "cand_api@example.com"
    assert "applications_count" in profile_data


@pytest.mark.asyncio
async def test_get_nonexistent_candidate_profile(client):
    res = await client.get("/candidate/profile/999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Candidate not found"


@pytest.mark.asyncio
async def test_update_candidate_profile(client):
    reg_payload = {
        "fullname": "Candidate Before Update",
        "email": "cand_update@example.com",
        "password": "password123"
    }
    reg_res = await client.post("/candidate/register", json=reg_payload)
    cand_id = reg_res.json()["id"]

    update_payload = {
        "fullname": "Candidate After Update",
        "location": "Makati City",
        "bio": "Experienced engineer"
    }
    put_res = await client.put(f"/candidate/profile/{cand_id}", json=update_payload)
    assert put_res.status_code == 200
    assert put_res.json()["fullname"] == "Candidate After Update"
    assert put_res.json()["location"] == "Makati City"


@pytest.mark.asyncio
async def test_upload_candidate_profile_image(client):
    reg_payload = {
        "fullname": "Photo User",
        "email": "photo_cand@example.com",
        "password": "password123"
    }
    reg_res = await client.post("/candidate/register", json=reg_payload)
    cand_id = reg_res.json()["id"]

    file_bytes = b"fake-png-content"
    files = {"file": ("avatar.png", io.BytesIO(file_bytes), "image/png")}

    with patch("app.utils.supabase_storage.upload_profile_image", new_callable=AsyncMock) as mock_sb:
        mock_sb.return_value = {"public_url": "https://example.com/profiles/avatar.png"}

        res = await client.post(f"/candidate/upload-profile-image/{cand_id}", files=files)
        assert res.status_code == 200
        assert "image_url" in res.json()


@pytest.mark.asyncio
async def test_parse_resume_endpoint(client):
    files = {"file": ("sample_resume.pdf", io.BytesIO(b"dummy pdf bytes"), "application/pdf")}
    mock_extracted = {
        "fullname": "Parsed Candidate",
        "email": "parsed@example.com",
        "skills": ["Python", "FastAPI"],
        "education": "BS CS",
        "experience": "2 yrs"
    }

    with patch("app.services.resume_service.parse_resume_file", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = mock_extracted
        res = await client.post("/candidate/parse-resume", files=files)
        assert res.status_code == 200
        assert res.json()["fullname"] == "Parsed Candidate"
