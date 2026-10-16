import pytest
import io
from unittest.mock import patch, AsyncMock
from app.models.hr import HR
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_hr_public_registration_disabled(client):
    payload = {
        "fullname": "HR Hopeful",
        "email": "hr_hopeful@example.com",
        "password": "password123",
        "company_name": "Mariwasa"
    }
    res = await client.post("/hr/register", json=payload)
    assert res.status_code == 403
    assert "Public HR registration is disabled" in res.json()["detail"]


@pytest.mark.asyncio
async def test_hr_counts_and_stats_endpoints(client, db_session):
    # Candidate count
    cand_res = await client.get("/hr/candidate-count")
    assert cand_res.status_code == 200
    assert "count" in cand_res.json()

    # Resume count
    resume_res = await client.get("/hr/resume-count")
    assert resume_res.status_code == 200
    assert "count" in resume_res.json()

    # Application stats
    stats_res = await client.get("/hr/application-stats")
    assert stats_res.status_code == 200
    assert "pending" in stats_res.json()
    assert "accepted" in stats_res.json()

    # Dashboard trends
    trends_res = await client.get("/hr/dashboard-trends")
    assert trends_res.status_code == 200
    assert "weekly_trends" in trends_res.json()
    assert "department_distribution" in trends_res.json()


@pytest.mark.asyncio
async def test_hr_profile_get_and_update(client, db_session):
    hr = HR(
        fullname="HR Profile Tester",
        email="hr_prof@example.com",
        password=hash_password("password123"),
        role="HR",
        company_name="Mariwasa Siam Ceramics"
    )
    db_session.add(hr)
    await db_session.commit()

    # Get profile
    get_res = await client.get(f"/hr/profile/{hr.id}")
    assert get_res.status_code == 200
    assert get_res.json()["fullname"] == "HR Profile Tester"

    # Non-existent profile
    assert (await client.get("/hr/profile/999999")).status_code == 404

    # Update profile
    update_payload = {
        "fullname": "HR Senior Recruiter",
        "department": "Talent Acquisition",
        "position": "Lead"
    }
    put_res = await client.put(f"/hr/profile/{hr.id}", json=update_payload)
    assert put_res.status_code == 200
    assert put_res.json()["fullname"] == "HR Senior Recruiter"
    assert put_res.json()["position"] == "Lead"


@pytest.mark.asyncio
async def test_hr_upload_profile_image(client, db_session):
    hr = HR(
        fullname="HR Image Tester",
        email="hr_img@example.com",
        password=hash_password("password123"),
        role="HR",
        company_name="Mariwasa"
    )
    db_session.add(hr)
    await db_session.commit()

    files = {"file": ("hr_avatar.png", io.BytesIO(b"fake-image"), "image/png")}
    with patch("app.utils.supabase_storage.upload_profile_image", new_callable=AsyncMock) as mock_sb:
        mock_sb.return_value = {"public_url": "https://example.com/profiles/hr_avatar.png"}

        res = await client.post(f"/hr/upload-profile-image/{hr.id}", files=files)
        assert res.status_code == 200
        assert "image_url" in res.json()
