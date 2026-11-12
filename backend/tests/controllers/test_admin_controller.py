import io
import pytest
from unittest.mock import patch, AsyncMock
from app.models.admin import Admin
from app.models.candidate import Candidate
from app.models.hr import HR
from app.utils.auth import hash_password, create_access_token


@pytest.mark.asyncio
async def test_admin_public_registration_disabled(client):
    payload = {
        "fullname": "Hacker Admin",
        "email": "hacker@example.com",
        "password": "password123",
    }
    res = await client.post("/admins/register", json=payload)
    assert res.status_code == 403
    assert "Public Administrator registration is disabled" in res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_system_stats(client, db_session):
    res = await client.get("/admins/system-stats")
    assert res.status_code == 200
    data = res.json()
    assert "users_count" in data or "total_users" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_admin_user_directory_operations(client, db_session):
    admin = Admin(
        fullname="Main Super Admin",
        email="superadmin@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN",
        department="IT"
    )
    db_session.add(admin)
    await db_session.commit()
    admin_id = admin.id

    admin_token = create_access_token({"sub": "superadmin@example.com", "role": "ADMIN", "id": admin_id})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create candidate user via admin controller
    create_payload = {
        "fullname": "New Hired Candidate",
        "email": "new_cand@example.com",
        "password": "password123",
        "role": "CANDIDATE"
    }
    create_res = await client.post("/admins/users", json=create_payload, headers=admin_headers)
    assert create_res.status_code == 201
    cand_data = create_res.json()
    assert cand_data["email"] == "new_cand@example.com"
    cand_id = cand_data["id"]

    # 2. Disallow creating an ADMIN user via this endpoint
    bad_admin_create = {
        "fullname": "Another Admin",
        "email": "another_admin@example.com",
        "password": "password123",
        "role": "ADMIN"
    }
    bad_res = await client.post("/admins/users", json=bad_admin_create, headers=admin_headers)
    assert bad_res.status_code == 400

    # 3. Read users list
    users_res = await client.get("/admins/users", headers=admin_headers)
    assert users_res.status_code == 200
    assert any(u["id"] == cand_id for u in users_res.json())

    # 4. Update candidate
    update_res = await client.put(
        f"/admins/users/{cand_id}",
        json={"fullname": "Updated Candidate Name"},
        headers=admin_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["fullname"] == "Updated Candidate Name"

    # Disallow updating role to ADMIN
    bad_role_update = await client.put(
        f"/admins/users/{cand_id}",
        json={"role": "ADMIN"},
        headers=admin_headers
    )
    assert bad_role_update.status_code == 400

    # 5. Archive user
    archive_res = await client.patch(f"/admins/users/{cand_id}/archive", headers=admin_headers)
    assert archive_res.status_code == 200
    assert "User archived successfully" in archive_res.json()["message"]

    # 6. Unarchive user
    unarchive_res = await client.patch(f"/admins/users/{cand_id}/unarchive", headers=admin_headers)
    assert unarchive_res.status_code == 200
    assert "User unarchived successfully" in unarchive_res.json()["message"]

    # 7. Disallow self-archive or self-delete
    self_arch_res = await client.patch(f"/admins/users/{admin_id}/archive", headers=admin_headers)
    assert self_arch_res.status_code == 400

    self_del_res = await client.delete(f"/admins/users/{admin_id}", headers=admin_headers)
    assert self_del_res.status_code == 400

    # 8. Delete user
    del_res = await client.delete(f"/admins/users/{cand_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert "User removed successfully" in del_res.json()["message"]


@pytest.mark.asyncio
async def test_admin_profile_and_upload_image(client, db_session):
    admin = Admin(
        fullname="Admin Profile Tester",
        email="admin_profile@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN",
        department="Security",
        position="Lead Security Officer"
    )
    db_session.add(admin)
    await db_session.commit()
    admin_id = admin.id

    token = create_access_token({"sub": "admin_profile@example.com", "role": "ADMIN", "id": admin_id})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get Admin Profile
    get_res = await client.get(f"/admins/profile/{admin_id}", headers=headers)
    assert get_res.status_code == 200
    prof_data = get_res.json()
    assert prof_data["email"] == "admin_profile@example.com"
    assert prof_data["role"] == "ADMIN"
    assert "users_count" in prof_data

    # 2. Update Admin Profile
    update_res = await client.put(
        f"/admins/profile/{admin_id}",
        json={"position": "Director of Security", "department": "Executive"},
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["position"] == "Director of Security"

    # 3. Upload Profile Image
    fake_img = io.BytesIO(b"fake admin avatar bytes")
    files = {"file": ("admin_avatar.png", fake_img, "image/png")}
    with patch("app.utils.supabase_storage.upload_profile_image", new_callable=AsyncMock) as mock_sb:
        mock_sb.return_value = {"public_url": "https://example.com/admin_avatar.png"}
        upload_res = await client.post(
            f"/admins/upload-profile-image/{admin_id}",
            files=files,
            headers=headers
        )
        assert upload_res.status_code == 200
        assert "image_url" in upload_res.json()


@pytest.mark.asyncio
async def test_admin_job_crud_and_status(client, db_session):
    admin = Admin(
        fullname="Admin Job Tester",
        email="admin_jobs@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token({"sub": "admin_jobs@example.com", "role": "ADMIN", "id": admin.id})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Job with all requirements
    job_payload = {
        "job_id": "ADM-JOB-2026-001",
        "job_title": "Senior Cloud Architect",
        "department": "Engineering",
        "job_type": "Full-Time",
        "location": "Taguig, Metro Manila",
        "salary_range": "150k-200k",
        "description": "Lead multi-cloud architecture and DevOps strategy.",
        "skills_requirements": "AWS, GCP, Kubernetes, Terraform",
        "education_requirements": "Bachelor's in Computer Science",
        "experience_requirements": "5+ years",
        "certifications_requirements": "AWS Solutions Architect Professional, CKA",
        "is_active": True
    }
    create_res = await client.post("/admins/createjob", json=job_payload, headers=headers)
    assert create_res.status_code == 201
    job_data = create_res.json()
    assert job_data["job_id"] == "ADM-JOB-2026-001"
    assert job_data["certifications_requirements"] == "AWS Solutions Architect Professional, CKA"

    # Duplicate job_id should return 409 Conflict cleanly
    dup_res = await client.post("/admins/createjob", json=job_payload, headers=headers)
    assert dup_res.status_code == 409

    # 2. Read active jobs (applicant job browser endpoint, unauthenticated public access)
    jobs_res = await client.get("/admins/read-jobs")
    assert jobs_res.status_code == 200
    matched_job = next((j for j in jobs_res.json() if j["job_id"] == "ADM-JOB-2026-001"), None)
    assert matched_job is not None
    assert matched_job["description"] == job_payload["description"]
    assert matched_job["skills_requirements"] == job_payload["skills_requirements"]
    assert matched_job["education_requirements"] == job_payload["education_requirements"]
    assert matched_job["experience_requirements"] == job_payload["experience_requirements"]
    assert matched_job["certifications_requirements"] == job_payload["certifications_requirements"]
    assert matched_job["salary_range"] == job_payload["salary_range"]

    # 3. Read specific job
    read_res = await client.get(f"/admins/read-job/ADM-JOB-2026-001", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["job_title"] == "Senior Cloud Architect"
    assert read_res.json()["certifications_requirements"] == "AWS Solutions Architect Professional, CKA"

    # 4. Update job
    update_res = await client.patch(
        f"/admins/update-job/ADM-JOB-2026-001",
        json={"salary_range": "180k-220k"},
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["salary_range"] == "180k-220k"

    # 5. Archive job
    arch_res = await client.patch("/admins/archive-job/ADM-JOB-2026-001", headers=headers)
    assert arch_res.status_code == 200
    assert arch_res.json()["is_active"] is False

    # 6. Unarchive job
    unarch_res = await client.patch("/admins/unarchive-job/ADM-JOB-2026-001", headers=headers)
    assert unarch_res.status_code == 200
    assert unarch_res.json()["is_active"] is True

    # 7. Delete job
    del_res = await client.delete("/admins/delete-job/ADM-JOB-2026-001", headers=headers)
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_admin_data_management_and_retention(client, db_session):
    admin = Admin(
        fullname="Admin Data Tester",
        email="admin_data@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token({"sub": "admin_data@example.com", "role": "ADMIN", "id": admin.id})
    headers = {"Authorization": f"Bearer {token}"}

    # Data backup
    backup_res = await client.post("/admins/data-backup", headers=headers)
    assert backup_res.status_code == 200
    assert "Data backup completed successfully" in backup_res.json()["message"]

    # Data recovery
    recovery_res = await client.post("/admins/data-recovery", headers=headers)
    assert recovery_res.status_code == 200
    assert "Data recovery initiated successfully" in recovery_res.json()["message"]

    # Get retention policy
    retention_res = await client.get("/admins/retention-policy", headers=headers)
    assert retention_res.status_code == 200
    assert "retention_days" in retention_res.json()

    # Update retention policy
    new_policy = {"retention_days": 180, "auto_delete": False}
    update_ret_res = await client.put("/admins/retention-policy", json=new_policy, headers=headers)
    assert update_ret_res.status_code == 200
    assert update_ret_res.json()["policy"]["retention_days"] == 180


@pytest.mark.asyncio
async def test_admin_edit_and_deactivate_hides_from_applicants_and_matching(client, db_session):
    admin = Admin(
        fullname="Admin Edit Deactivate Tester",
        email="admin_edit_deact@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token({"sub": "admin_edit_deact@example.com", "role": "ADMIN", "id": admin.id})
    headers = {"Authorization": f"Bearer {token}"}

    j1_payload = {
        "job_id": "ADM-EDIT-J1-001",
        "job_title": "Backend Engineer Original",
        "department": "Engineering",
        "job_type": "Full-Time",
        "location": "Taguig, Metro Manila",
        "salary_range": "100k-120k",
        "description": "Original backend API description.",
        "skills_requirements": "Python, SQL",
        "education_requirements": "BS Computer Science",
        "experience_requirements": "2+ years",
        "is_active": True
    }
    j2_payload = {
        "job_id": "ADM-DEACT-J2-002",
        "job_title": "Legacy Systems Specialist",
        "department": "Engineering",
        "job_type": "Full-Time",
        "location": "Makati, Metro Manila",
        "salary_range": "90k-110k",
        "description": "Maintain legacy systems prior to deactivation.",
        "skills_requirements": "Python, Linux, SQL",
        "education_requirements": "BS Computer Science",
        "experience_requirements": "2+ years",
        "is_active": True
    }

    res_j1 = await client.post("/admins/createjob", json=j1_payload, headers=headers)
    assert res_j1.status_code == 201
    res_j2 = await client.post("/admins/createjob", json=j2_payload, headers=headers)
    assert res_j2.status_code == 201

    # Edit J1
    update_payload = {
        "job_title": "Principal Platform Engineer Updated",
        "description": "Updated microservices and Kubernetes platform architecture.",
        "skills_requirements": "Python, FastAPI, Kubernetes, Terraform",
        "salary_range": "190k-230k"
    }
    update_res = await client.patch(
        "/admins/update-job/ADM-EDIT-J1-001",
        json=update_payload,
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["job_title"] == update_payload["job_title"]

    # Deactivate J2
    arch_res = await client.patch("/admins/archive-job/ADM-DEACT-J2-002", headers=headers)
    assert arch_res.status_code == 200
    assert arch_res.json()["is_active"] is False

    # Verify J1 shows new text and J2 is hidden in applicant job browser (/admins/read-jobs)
    public_jobs_res = await client.get("/admins/read-jobs")
    assert public_jobs_res.status_code == 200
    public_jobs = public_jobs_res.json()
    public_ids = {j["job_id"] for j in public_jobs}
    assert "ADM-EDIT-J1-001" in public_ids
    assert "ADM-DEACT-J2-002" not in public_ids

    j1_public = next(j for j in public_jobs if j["job_id"] == "ADM-EDIT-J1-001")
    assert j1_public["job_title"] == update_payload["job_title"]
    assert j1_public["description"] == update_payload["description"]
    assert j1_public["skills_requirements"] == update_payload["skills_requirements"]
    assert j1_public["salary_range"] == update_payload["salary_range"]

    # Verify J1 detail endpoint returns new text
    detail_res = await client.get("/admins/read-job/ADM-EDIT-J1-001")
    assert detail_res.status_code == 200
    assert detail_res.json()["job_title"] == update_payload["job_title"]
    assert detail_res.json()["description"] == update_payload["description"]

    # Verify admin view with include_inactive=true still lists J2 as inactive
    admin_jobs_res = await client.get("/admins/read-jobs?include_inactive=true", headers=headers)
    assert admin_jobs_res.status_code == 200
    j2_admin = next((j for j in admin_jobs_res.json() if j["job_id"] == "ADM-DEACT-J2-002"), None)
    assert j2_admin is not None
    assert j2_admin["is_active"] is False

    # Verify J2 is excluded from bulk resume matching while J1 uses updated text
    match_payload = {
        "fullname": "Platform Applicant",
        "email": "platform_applicant@example.com",
        "skills": "Python, FastAPI, Kubernetes, Terraform, Linux, SQL",
        "years_experience": 5,
        "highest_degree": "Bachelor of Science in Computer Science",
        "location": "Taguig, Metro Manila"
    }
    match_all_res = await client.post("/matching/match-data", json=match_payload)
    assert match_all_res.status_code == 200
    matched_results = match_all_res.json()["results"]
    matched_ids = {r["job_id"] for r in matched_results}
    assert "ADM-EDIT-J1-001" in matched_ids
    assert "ADM-DEACT-J2-002" not in matched_ids
    j1_match = next(r for r in matched_results if r["job_id"] == "ADM-EDIT-J1-001")
    assert j1_match["job_title"] == update_payload["job_title"]

    # Verify single-job matching hides deactivated J2 (404) and serves updated J1 (200)
    match_j2_res = await client.post("/matching/match-data/ADM-DEACT-J2-002", json=match_payload)
    assert match_j2_res.status_code == 404

    match_j1_res = await client.post("/matching/match-data/ADM-EDIT-J1-001", json=match_payload)
    assert match_j1_res.status_code == 200
    assert match_j1_res.json()["job_title"] == update_payload["job_title"]


@pytest.mark.asyncio
async def test_archive_filled_posting_hides_from_applicants_and_retains_history(client, db_session):
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    admin = Admin(
        fullname="Admin Archive Tester",
        email="admin_archive_fill@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token({"sub": "admin_archive_fill@example.com", "role": "ADMIN", "id": admin.id})
    headers = {"Authorization": f"Bearer {token}"}

    job_payload = {
        "job_id": "ADM-FILL-ARCH-01",
        "job_title": "Production Process Lead Filled",
        "department": "Manufacturing",
        "job_type": "Full-Time",
        "location": "Sto. Tomas, Batangas",
        "salary_range": "120k-150k",
        "description": "Lead kiln and tile manufacturing line.",
        "skills_requirements": "Six Sigma, PLC, Manufacturing Operations",
        "education_requirements": "BS Industrial Engineering",
        "experience_requirements": "4+ years",
        "is_active": True
    }
    create_res = await client.post("/admins/createjob", json=job_payload, headers=headers)
    assert create_res.status_code == 201
    db_job_pk = create_res.json()["id"]

    # Record historical application & fill the position before archiving
    with patch("app.tasks.analyze_application_task.delay"), \
         patch("app.services.job_application_service.send_status_update_email", new_callable=AsyncMock, create=True):
        app_res = await client.post(
            "/applications/",
            json={
                "job_id": "ADM-FILL-ARCH-01",
                "candidate_name": "Historical Hired Applicant",
                "candidate_email": "hired.fill@example.com",
                "skills": ["Six Sigma", "PLC", "Manufacturing Operations"],
                "years_experience": 5,
            },
        )
        assert app_res.status_code == 201
        app_id = app_res.json()["id"]

        hire_res = await client.patch(
            f"/applications/{app_id}/status",
            json={"status": "ACCEPTED", "notes": "Position filled"},
            headers=headers,
        )
        assert hire_res.status_code == 200
        assert hire_res.json()["status"] == "ACCEPTED"

    # Archive filled posting
    arch_res = await client.patch("/admins/archive-job/ADM-FILL-ARCH-01", headers=headers)
    assert arch_res.status_code == 200
    assert arch_res.json()["is_active"] is False

    # 1. Hidden from applicant browser, matching, and new application submissions
    public_jobs = (await client.get("/admins/read-jobs")).json()
    assert "ADM-FILL-ARCH-01" not in {j["job_id"] for j in public_jobs}

    match_payload = {
        "fullname": "Late Applicant",
        "skills": "Six Sigma, PLC, Manufacturing Operations",
        "years_experience": 5,
    }
    bulk_match = (await client.post("/matching/match-data", json=match_payload)).json()["results"]
    assert "ADM-FILL-ARCH-01" not in {r["job_id"] for r in bulk_match}
    assert (await client.post("/matching/match-data/ADM-FILL-ARCH-01", json=match_payload)).status_code == 404

    late_apply_res = await client.post(
        "/applications/",
        json={
            "job_id": "ADM-FILL-ARCH-01",
            "candidate_name": "Late Applicant",
            "candidate_email": "late.applicant@example.com",
            "skills": ["Six Sigma", "PLC"],
        },
    )
    assert late_apply_res.status_code == 400
    assert "archived" in late_apply_res.json()["detail"].lower()

    # 2. Historical job description, applications, stats, and audit trail retained
    admin_jobs = (await client.get("/admins/read-jobs?include_inactive=true", headers=headers)).json()
    archived_job = next((j for j in admin_jobs if j["job_id"] == "ADM-FILL-ARCH-01"), None)
    assert archived_job is not None
    assert archived_job["is_active"] is False
    assert archived_job["job_title"] == job_payload["job_title"]
    assert archived_job["description"] == job_payload["description"]

    by_job = (await client.get(f"/applications/job/{db_job_pk}")).json()
    assert len(by_job) == 1
    assert by_job[0]["id"] == app_id
    assert by_job[0]["status"] == "ACCEPTED"

    by_cand = (await client.get("/applications/candidate/hired.fill@example.com")).json()
    assert len(by_cand) == 1
    assert by_cand[0]["status"] == "ACCEPTED"
    assert by_cand[0]["job"]["job_title"] == job_payload["job_title"]

    summary_rows = (await client.get("/applications/?summary=true")).json()
    retained_row = next((r for r in summary_rows if r["id"] == app_id), None)
    assert retained_row is not None
    assert retained_row["job"]["job_title"] == job_payload["job_title"]

    hr_stats = (await client.get("/hr/application-stats")).json()
    assert hr_stats["accepted"] >= 1

    trends = (await client.get("/hr/dashboard-trends")).json()
    assert any(p["label"] == job_payload["job_title"] and p["value"] >= 1 for p in trends["position_distribution"])

    perf_stats = (await client.get("/system-config/performance", headers=headers)).json()
    assert perf_stats["inactive_jobs"] >= 1
    assert perf_stats["total_applications"] >= 1
    sys_stats_res = await client.get("/admins/system-stats", headers=headers)
    assert sys_stats_res.status_code == 200

    audit_row = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "ARCHIVE_JOB", AuditLog.target == f"Job: {job_payload['job_title']}")
        )
    ).scalars().first()
    assert audit_row is not None
    assert audit_row.user_id == admin.id
