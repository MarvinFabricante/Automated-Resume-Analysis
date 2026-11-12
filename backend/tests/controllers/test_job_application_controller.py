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


@pytest.mark.asyncio
async def test_large_dataset_550_applicants_loads_under_3_seconds(client, db_session, mock_celery_task):
    """
    Module: HR Dashboard -> Large Dataset
    Steps: Load 500+ applicants (550 seeded applicants across positions and statuses)
    Expected Result: Dashboard API endpoints load cleanly well within 3 seconds.
    """
    import time
    from datetime import datetime, timedelta
    from app.models.job_application import JobApplication

    jobs = [
        JobDescription(
            job_id=f"JOB-LARGE-{i}",
            job_title=f"Large Dataset Role {i}",
            department=["Operations", "QA", "Engineering"][i % 3],
            job_type=JobType.FULL_TIME,
            location="Laguna",
            description="High volume role",
        )
        for i in range(5)
    ]
    db_session.add_all(jobs)
    await db_session.flush()

    now = datetime.utcnow()
    seeded_apps = [
        JobApplication(
            job_id=jobs[i % 5].id,
            candidate_name=f"Large Applicant {i}",
            candidate_email=f"large_app_{i}@example.com",
            phone="+639171112233",
            location="Batangas",
            job_title=jobs[i % 5].job_title,
            skills=["Quality Control", "Machine Learning", "CAD", f"SkillTag{i % 25}"],
            match_score=float((i * 13) % 101),
            skills_score=72.0,
            experience_score=78.0,
            education_score=80.0,
            relevant_experience="3 years plant production line operation",
            degree="BS Industrial Engineering",
            college="Batangas State University",
            status=["PENDING", "REVIEWED", "ACCEPTED", "REJECTED"][i % 4],
            created_at=now - timedelta(days=i % 20, minutes=i),
        )
        for i in range(550)
    ]
    db_session.add_all(seeded_apps)
    await db_session.commit()

    start_time = time.perf_counter()
    summary_res = await client.get("/applications/?summary=true")
    stats_res = await client.get("/hr/application-stats")
    trends_res = await client.get("/hr/dashboard-trends")
    cand_cnt_res = await client.get("/hr/candidate-count")
    res_cnt_res = await client.get("/hr/resume-count")
    elapsed = time.perf_counter() - start_time

    assert summary_res.status_code == 200
    assert stats_res.status_code == 200
    assert trends_res.status_code == 200
    assert cand_cnt_res.status_code == 200
    assert res_cnt_res.status_code == 200

    summary_rows = summary_res.json()
    assert len(summary_rows) >= 550
    assert elapsed < 3.0, f"HR Dashboard 550-applicant API bundle took {elapsed:.3f}s (>= 3.0s)"

    # Verify full GET /applications/ also runs fast without blocking enrichment
    full_start = time.perf_counter()
    full_res = await client.get("/applications/")
    full_elapsed = time.perf_counter() - full_start
    assert full_res.status_code == 200
    assert len(full_res.json()) >= 550
    assert full_elapsed < 3.0, f"Full /applications/ took {full_elapsed:.3f}s (>= 3.0s)"

    # Verify paginated slice & single-item detail hydration endpoint
    page_res = await client.get("/applications/?summary=true&sort_by=match_desc&limit=20&offset=0")
    assert page_res.status_code == 200
    page_rows = page_res.json()
    assert len(page_rows) == 20
    assert page_rows[0]["match_score"] >= page_rows[-1]["match_score"]

    target_id = page_rows[0]["id"]
    detail_res = await client.get(f"/applications/{target_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == target_id
    assert "work_experiences" in detail
    assert (await client.get("/applications/999999")).status_code == 404


@pytest.mark.asyncio
async def test_archived_job_rejects_new_applications_and_retains_existing(
    client, db_session, mock_celery_task
):
    job = JobDescription(
        job_id="JOB-FILL-ARCHIVE-CTRL",
        job_title="Filled Ceramic Plant Chemist",
        department="Quality Assurance",
        job_type=JobType.FULL_TIME,
        location="Batangas",
        description="Formulate glazes and QA standards.",
        skills_requirements="Chemistry, Glaze Formulation, ISO 9001",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    # Candidate applies and gets hired while posting is active
    app_res = await client.post(
        "/applications/",
        json={
            "job_id": "JOB-FILL-ARCHIVE-CTRL",
            "candidate_name": "Filled Role Hire",
            "candidate_email": "filled.hire@example.com",
            "skills": ["Chemistry", "ISO 9001"],
            "years_experience": 4,
        },
    )
    assert app_res.status_code == 201
    existing_app_id = app_res.json()["id"]

    status_res = await client.patch(
        f"/applications/{existing_app_id}/status",
        json={"status": "ACCEPTED", "notes": "Offer accepted"},
    )
    assert status_res.status_code == 200

    # Admin archives the filled job
    arch_res = await client.patch("/admins/archive-job/JOB-FILL-ARCHIVE-CTRL")
    assert arch_res.status_code == 200
    assert arch_res.json()["is_active"] is False

    # New application submission to the archived job must be rejected
    new_apply_res = await client.post(
        "/applications/",
        json={
            "job_id": "JOB-FILL-ARCHIVE-CTRL",
            "candidate_name": "Blocked New Candidate",
            "candidate_email": "blocked.candidate@example.com",
            "skills": ["Chemistry", "ISO 9001"],
        },
    )
    assert new_apply_res.status_code == 400
    assert "archived" in new_apply_res.json()["detail"].lower()

    # Historical application data remains intact
    job_apps_res = await client.get(f"/applications/job/{job.id}")
    assert job_apps_res.status_code == 200
    assert len(job_apps_res.json()) == 1
    assert job_apps_res.json()[0]["id"] == existing_app_id
    assert job_apps_res.json()[0]["status"] == "ACCEPTED"

    cand_apps_res = await client.get("/applications/candidate/filled.hire@example.com")
    assert cand_apps_res.status_code == 200
    assert len(cand_apps_res.json()) == 1
    assert cand_apps_res.json()[0]["job"]["job_title"] == "Filled Ceramic Plant Chemist"

    single_app_res = await client.get(f"/applications/{existing_app_id}")
    assert single_app_res.status_code == 200
    assert single_app_res.json()["status"] == "ACCEPTED"

