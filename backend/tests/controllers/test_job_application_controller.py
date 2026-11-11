import pytest
from unittest.mock import patch
from app.models.job_description import JobDescription, JobType


@pytest.fixture
def mock_celery_task():
    with patch("app.tasks.analyze_application_task.delay") as mock_delay:
        yield mock_delay


@pytest.mark.asyncio
async def test_job_application_crud_endpoints(client, db_session, mock_celery_task):
    job = JobDescription(
        job_id="JOB-CTRL-01",
        job_title="Software Architect",
        department="IT",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Architecture and systems design"
    )
    db_session.add(job)
    await db_session.commit()

    # Submit application
    app_payload = {
        "job_id": "JOB-CTRL-01",
        "candidate_name": "Alice Architect",
        "candidate_email": "alice.arch@example.com",
        "phone": "+639112223344",
        "skills": ["Python", "Microservices", "Docker"]
    }
    create_res = await client.post("/applications/", json=app_payload)
    assert create_res.status_code == 201
    data = create_res.json()
    app_id = data["id"]
    assert data["candidate_name"] == "Alice Architect"

    # Get all applications
    all_res = await client.get("/applications/")
    assert all_res.status_code == 200
    assert len(all_res.json()) >= 1

    # Get applications by job
    by_job_res = await client.get(f"/applications/job/{job.id}")
    assert by_job_res.status_code == 200
    assert any(a["id"] == app_id for a in by_job_res.json())

    # Get applications by candidate email
    by_email_res = await client.get("/applications/candidate/alice.arch@example.com")
    assert by_email_res.status_code == 200
    assert any(a["id"] == app_id for a in by_email_res.json())

    # Update status (PATCH)
    status_payload = {"status": "TECHNICAL INTERVIEW"}
    patch_res = await client.patch(f"/applications/{app_id}/status", json=status_payload)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "TECHNICAL INTERVIEW"

    # Delete application (204)
    del_res = await client.delete(f"/applications/{app_id}")
    assert del_res.status_code == 204

    # Delete non-existent
    assert (await client.delete("/applications/999999")).status_code == 404


@pytest.mark.asyncio
async def test_create_application_nonexistent_job(client):
    app_payload = {
        "job_id": "NON-EXISTENT-JOB-999",
        "candidate_name": "Ghost Candidate",
        "candidate_email": "ghost@example.com"
    }
    res = await client.post("/applications/", json=app_payload)
    assert res.status_code == 404
    assert res.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_duplicate_application_controller_block_and_check(client, db_session, mock_celery_task):
    """
    Test Case: TC-RES-016 (Controller Duplicate Submission Handling)
    Verifies that duplicate application for the same role is blocked (409) and check-duplicate endpoint works.
    """
    job = JobDescription(
        job_id="JOB-CTRL-DUP-01",
        job_title="Data Scientist",
        department="Analytics",
        job_type=JobType.FULL_TIME,
        location="Taguig",
        description="Machine learning and statistical analysis"
    )
    db_session.add(job)
    await db_session.commit()

    app_payload = {
        "job_id": "JOB-CTRL-DUP-01",
        "candidate_name": "Clara Scientist",
        "candidate_email": "clara.ds@example.com",
        "phone": "+639998887766",
        "skills": ["Python", "scikit-learn", "Pandas"]
    }

    # Initial check should indicate not duplicate
    chk_res1 = await client.get(f"/applications/check-duplicate?job_id={job.id}&email=clara.ds@example.com")
    assert chk_res1.status_code == 200
    assert chk_res1.json()["is_duplicate"] is False

    # First application succeeds
    res1 = await client.post("/applications/", json=app_payload)
    assert res1.status_code == 201

    # Check duplicate endpoint now indicates duplicate
    chk_res2 = await client.get(f"/applications/check-duplicate?job_id={job.id}&email=clara.ds@example.com")
    assert chk_res2.status_code == 200
    assert chk_res2.json()["is_duplicate"] is True

    # Second application for same role and applicant is blocked by policy (409 Conflict)
    res2 = await client.post("/applications/", json=app_payload)
    assert res2.status_code == 409
    assert "Duplicate application" in res2.json()["detail"]

    # Verify no double records exist in the database
    apps_res = await client.get(f"/applications/job/{job.id}")
    assert apps_res.status_code == 200
    assert len(apps_res.json()) == 1


@pytest.mark.asyncio
async def test_new_application_updates_hr_dashboard_counts_list_and_invalidates_caches(
    client, db_session, mock_celery_task
):
    from unittest.mock import AsyncMock

    job = JobDescription(
        job_id="JOB-HR-RT-01",
        job_title="Production Planner",
        department="Planning",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Coordinate factory production schedules.",
    )
    db_session.add(job)
    await db_session.commit()

    before_stats = (await client.get("/hr/application-stats")).json()
    before_resumes = (await client.get("/hr/resume-count")).json()
    before_apps = (await client.get("/applications/")).json()

    cleared_patterns = []

    async def capture_clear(pattern: str):
        cleared_patterns.append(pattern)

    with patch("app.utils.cache.clear_cache_pattern", side_effect=capture_clear), \
         patch("app.services.notification_service.manager.broadcast", new_callable=AsyncMock) as mock_ws:
        create_res = await client.post(
            "/applications/",
            json={
                "job_id": "JOB-HR-RT-01",
                "candidate_name": "Realtime Applicant",
                "candidate_email": "realtime.app@example.com",
                "skills": ["Scheduling", "SAP"],
                "years_experience": 3,
            },
        )
        assert create_res.status_code == 201
        created_id = create_res.json()["id"]

    # Real-time WebSocket broadcast must target HR on new application
    assert any(
        call.kwargs.get("target_role") == "HR" and '"application"' in call.args[0]
        for call in mock_ws.await_args_list
    )

    # Repository + controller invalidation must cover all HR dashboard stat/list patterns
    for expected_pattern in (
        "all_apps",
        "job_apps",
        "cand_apps",
        "app_stats",
        "candidate_count",
        "resume_count",
        "dashboard_trends",
        "hr:stats",
    ):
        assert expected_pattern in cleared_patterns

    after_stats = (await client.get("/hr/application-stats")).json()
    after_resumes = (await client.get("/hr/resume-count")).json()
    after_trends = (await client.get("/hr/dashboard-trends")).json()
    after_apps = (await client.get("/applications/")).json()

    assert after_stats["pending"] == before_stats["pending"] + 1
    assert after_stats["total"] == before_stats["total"] + 1
    assert after_resumes["count"] == before_resumes["count"] + 1
    assert len(after_apps) == len(before_apps) + 1
    assert after_apps[0]["id"] == created_id
    assert any(
        d["label"] == "Planning" and d["value"] >= 1
        for d in after_trends["department_distribution"]
    )


@pytest.mark.asyncio
async def test_filter_by_position_and_sort_by_score_and_date(
    client, db_session, mock_celery_task
):
    from datetime import datetime, timedelta
    from app.models.job_application import JobApplication

    j_ops = JobDescription(
        job_id="JOB-FS-1",
        job_title="Forklift Operator",
        department="Logistics",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Forklift operations",
    )
    j_eng = JobDescription(
        job_id="JOB-FS-2",
        job_title="Process Engineer",
        department="Engineering",
        job_type=JobType.FULL_TIME,
        location="Laguna",
        description="Process improvements",
    )
    db_session.add_all([j_ops, j_eng])
    await db_session.flush()

    now = datetime.utcnow()
    apps = [
        JobApplication(
            job_id=j_ops.id,
            candidate_name="Ops Tie Earlier",
            candidate_email="ops1@example.com",
            match_score=80.0,
            created_at=now - timedelta(days=2),
        ),
        JobApplication(
            job_id=j_ops.id,
            candidate_name="Ops Top Score",
            candidate_email="ops2@example.com",
            match_score=95.0,
            created_at=now - timedelta(days=3),
        ),
        JobApplication(
            job_id=j_ops.id,
            candidate_name="Ops Tie Newer",
            candidate_email="ops3@example.com",
            match_score=80.0,
            created_at=now - timedelta(days=1),
        ),
        JobApplication(
            job_id=j_eng.id,
            candidate_name="Other Position",
            candidate_email="eng1@example.com",
            match_score=99.0,
            created_at=now,
        ),
    ]
    db_session.add_all(apps)
    await db_session.commit()

    # Filter by position + sort by score descending (tiebroken by newest date)
    by_score = (await client.get("/applications/?position=Forklift%20Operator&sort_by=match_desc")).json()
    assert [a["candidate_name"] for a in by_score] == [
        "Ops Top Score",
        "Ops Tie Newer",
        "Ops Tie Earlier",
    ]

    # Filter by position + sort by newest date descending
    by_date_desc = (await client.get("/applications/?position=Forklift%20Operator&sort_by=date_desc")).json()
    assert [a["candidate_name"] for a in by_date_desc] == [
        "Ops Tie Newer",
        "Ops Tie Earlier",
        "Ops Top Score",
    ]

    # Filter by position + sort by oldest date ascending
    by_date_asc = (await client.get("/applications/?position=Forklift%20Operator&sort_by=date_asc")).json()
    assert [a["candidate_name"] for a in by_date_asc] == [
        "Ops Top Score",
        "Ops Tie Earlier",
        "Ops Tie Newer",
    ]

