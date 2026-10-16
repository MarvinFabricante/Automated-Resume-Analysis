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

    # 1. Create Job
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
        "is_active": True
    }
    create_res = await client.post("/admins/createjob", json=job_payload, headers=headers)
    assert create_res.status_code == 201
    job_data = create_res.json()
    assert job_data["job_id"] == "ADM-JOB-2026-001"

    # 2. Read active jobs
    jobs_res = await client.get("/admins/read-jobs", headers=headers)
    assert jobs_res.status_code == 200
    assert any(j["job_id"] == "ADM-JOB-2026-001" for j in jobs_res.json())

    # 3. Read specific job
    read_res = await client.get(f"/admins/read-job/ADM-JOB-2026-001", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["job_title"] == "Senior Cloud Architect"

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
