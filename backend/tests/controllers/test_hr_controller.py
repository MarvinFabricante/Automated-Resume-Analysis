import csv
import fitz
import pytest
import io
from unittest.mock import patch, AsyncMock
from app.models.hr import HR
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication
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
    assert "position_distribution" in trends_res.json()
    assert "skills_distribution" in trends_res.json()
    assert "average_score" in trends_res.json()


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


@pytest.mark.asyncio
async def test_hr_export_csv_and_pdf_match_seeded_data(client, db_session):
    j1 = JobDescription(
        job_id="JOB-EXP-1",
        job_title="Export Position Alpha",
        department="Operations",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Operate kiln",
    )
    j2 = JobDescription(
        job_id="JOB-EXP-2",
        job_title="Export Position Beta",
        department="QA",
        job_type=JobType.FULL_TIME,
        location="Bulacan",
        description="Quality inspection",
    )
    db_session.add_all([j1, j2])
    await db_session.flush()

    db_session.add_all([
        JobApplication(
            job_id=j1.id,
            candidate_name="Export Alice",
            candidate_email="export_alice@example.com",
            match_score=90.0,
            skills=["ExportSkillX", "ExportSkillY"],
            status="PENDING",
        ),
        JobApplication(
            job_id=j1.id,
            candidate_name="Export Bob",
            candidate_email="export_bob@example.com",
            match_score=80.0,
            skills=["ExportSkillX", "ExportSkillY"],
            status="REVIEWED",
        ),
        JobApplication(
            job_id=j2.id,
            candidate_name="Export Cara",
            candidate_email="export_cara@example.com",
            match_score=60.0,
            skills=["ExportSkillX"],
            status="ACCEPTED",
        ),
    ])
    await db_session.commit()

    stats_res = await client.get("/hr/application-stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()

    trends_res = await client.get("/hr/dashboard-trends")
    assert trends_res.status_code == 200
    trends = trends_res.json()

    # Verify CSV export
    csv_res = await client.get("/hr/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "attachment;" in csv_res.headers.get("content-disposition", "")
    assert ".csv" in csv_res.headers.get("content-disposition", "")

    csv_text = csv_res.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(csv_text)))
    flat_csv = "\n".join(",".join(r) for r in rows)
    assert "DASHBOARD ANALYTICS SUMMARY" in flat_csv
    assert "APPLICANTS PER POSITION" in flat_csv
    assert "SKILLS DISTRIBUTION" in flat_csv
    assert "APPLICANT DATA" in flat_csv

    kv_summary = {r[0]: r[1] for r in rows if len(r) >= 2}
    assert str(kv_summary["Total Applications"]) == str(stats["total"])
    assert kv_summary["Overall Average Score"] == f"{stats['average_score']}%"

    pos_rows = {r[0]: r for r in rows if len(r) == 4 and r[0] in ("Export Position Alpha", "Export Position Beta")}
    assert pos_rows["Export Position Alpha"][1] == "2"
    assert pos_rows["Export Position Alpha"][3] == "85.0%"
    assert pos_rows["Export Position Beta"][1] == "1"
    assert pos_rows["Export Position Beta"][3] == "60.0%"

    assert trends["total_applications"] == stats["total"]
    assert "Export Alice" in flat_csv
    assert "Export Bob" in flat_csv
    assert "Export Cara" in flat_csv
    assert "ExportSkillX" in flat_csv
    assert "ExportSkillY" in flat_csv

    # Verify PDF export opens cleanly and matches screen analytics & applicants
    pdf_res = await client.get("/hr/export/pdf")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers.get("content-type", "")
    assert "attachment;" in pdf_res.headers.get("content-disposition", "")
    assert ".pdf" in pdf_res.headers.get("content-disposition", "")
    assert pdf_res.content.startswith(b"%PDF-")

    doc = fitz.open(stream=pdf_res.content, filetype="pdf")
    assert len(doc) >= 1
    pdf_text = "\n".join(page.get_text() for page in doc)
    assert "MARIWASA ARAS - HR Dashboard Analytics & Applicant Report" in pdf_text
    assert f"Total Applications: {stats['total']}" in pdf_text
    assert f"Average Score: {stats['average_score']}%" in pdf_text
    assert "Export Position Alpha: 2 applicant(s)" in pdf_text
    assert "Export Position Beta: 1 applicant(s)" in pdf_text
    assert "ExportSkillX: 3 applicant(s)" in pdf_text
    assert "ExportSkillY: 2 applicant(s)" in pdf_text
    assert "Export Alice" in pdf_text
    assert "Export Bob" in pdf_text
    assert "Export Cara" in pdf_text
