import pytest
from app.models.admin import Admin
from app.models.candidate import Candidate
from app.models.hr import HR
from app.utils.auth import hash_password, create_access_token


@pytest.mark.asyncio
async def test_matching_parameters_endpoints(client, db_session):
    admin = Admin(
        fullname="Config Admin",
        email="config_admin@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    db_session.add(admin)
    await db_session.commit()
    admin_id = admin.id

    admin_token = create_access_token({"sub": "config_admin@example.com", "role": "ADMIN", "id": admin_id})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get Matching Parameters
    get_res = await client.get("/system-config/matching", headers=admin_headers)
    assert get_res.status_code == 200
    config_data = get_res.json()
    assert "weights" in config_data
    assert "thresholds" in config_data

    # 2. Update Matching Weights
    weights_payload = {
        "skills_weight": 0.35,
        "experience_weight": 0.25,
        "education_weight": 0.15,
        "certifications_weight": 0.15,
        "location_weight": 0.10
    }
    update_w_res = await client.put(
        "/system-config/matching/weights",
        json=weights_payload,
        headers=admin_headers
    )
    assert update_w_res.status_code == 200
    assert update_w_res.json()["weights"]["skills_weight"] == 0.35

    # 3. Update Matching Thresholds
    thresholds_payload = {
        "minimum_match_score": 60.0,
        "fuzzy_match_threshold": 0.85
    }
    update_t_res = await client.put(
        "/system-config/matching/thresholds",
        json=thresholds_payload,
        headers=admin_headers
    )
    assert update_t_res.status_code == 200
    assert update_t_res.json()["thresholds"]["minimum_match_score"] == 60.0

    # 4. Trigger Recalculate
    recalc_res = await client.post("/system-config/matching/recalculate", headers=admin_headers)
    assert recalc_res.status_code == 200
    assert "updated_applications" in recalc_res.json()


@pytest.mark.asyncio
async def test_system_config_role_management(client, db_session):
    admin = Admin(
        fullname="Role Manager Admin",
        email="role_admin@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    cand = Candidate(
        fullname="Candidate To Promote",
        email="promote_me@example.com",
        password=hash_password("password123"),
        role="CANDIDATE"
    )
    db_session.add_all([admin, cand])
    await db_session.commit()
    admin_id = admin.id
    cand_id = cand.id

    admin_token = create_access_token({"sub": "role_admin@example.com", "role": "ADMIN", "id": admin_id})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get users by role
    users_res = await client.get("/system-config/roles/CANDIDATE", headers=admin_headers)
    assert users_res.status_code == 200
    assert any(u["id"] == cand_id for u in users_res.json())

    # 2. Update role from CANDIDATE to HR
    change_res = await client.patch(
        f"/system-config/users/{cand_id}/role",
        json={"role": "HR"},
        headers=admin_headers
    )
    assert change_res.status_code == 200
    assert change_res.json()["role"] == "HR"

    # 3. Disallow changing own role
    self_role_res = await client.patch(
        f"/system-config/users/{admin_id}/role",
        json={"role": "HR"},
        headers=admin_headers
    )
    assert self_role_res.status_code == 400

    # 4. Disallow invalid role
    invalid_role_res = await client.patch(
        f"/system-config/users/{cand_id}/role",
        json={"role": "SUPERUSER"},
        headers=admin_headers
    )
    assert invalid_role_res.status_code == 400

    # 5. Disallow modifying ADMIN role accounts
    admin_mod_res = await client.patch(
        f"/system-config/users/{admin_id}/role",
        json={"role": "CANDIDATE"},
        headers=admin_headers
    )
    assert admin_mod_res.status_code == 400


@pytest.mark.asyncio
async def test_form_template_crud(client, db_session):
    admin = Admin(
        fullname="Template Admin",
        email="template_admin@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    db_session.add(admin)
    await db_session.commit()
    admin_id = admin.id

    admin_token = create_access_token({"sub": "template_admin@example.com", "role": "ADMIN", "id": admin_id})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. List templates (empty initially or default)
    list_res = await client.get("/system-config/templates", headers=admin_headers)
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)

    # 2. Create form template
    template_payload = {
        "name": "Standard Ceramic Engineering Application",
        "description": "Standard form for engineering candidates",
        "fields": [
            {
                "field_name": "years_of_experience",
                "field_type": "number",
                "label": "Years of Experience",
                "required": True
            },
            {
                "field_name": "specialization",
                "field_type": "text",
                "label": "Engineering Specialization",
                "required": False
            }
        ],
        "is_default": False
    }
    create_res = await client.post(
        "/system-config/templates",
        json=template_payload,
        headers=admin_headers
    )
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["name"] == "Standard Ceramic Engineering Application"
    template_id = created["id"]

    # 3. Update form template
    update_res = await client.put(
        f"/system-config/templates/{template_id}",
        json={"description": "Updated engineering description"},
        headers=admin_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated engineering description"

    # 4. Delete form template
    del_res = await client.delete(
        f"/system-config/templates/{template_id}",
        headers=admin_headers
    )
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_system_performance_and_redis_endpoints(client, db_session):
    admin = Admin(
        fullname="Observability Admin",
        email="observe_admin@example.com",
        password=hash_password("adminpass123"),
        role="ADMIN"
    )
    db_session.add(admin)
    await db_session.commit()
    admin_id = admin.id

    admin_token = create_access_token({"sub": "observe_admin@example.com", "role": "ADMIN", "id": admin_id})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Performance
    perf_res = await client.get("/system-config/performance", headers=admin_headers)
    assert perf_res.status_code == 200
    perf_data = perf_res.json()
    assert "cpu_usage" in perf_data or "system_metrics" in perf_data or isinstance(perf_data, dict)

    # Redis Status
    redis_res = await client.get("/system-config/redis/status")
    assert redis_res.status_code == 200
    assert "redis_available" in redis_res.json()

    # Redis Transactions
    tx_res = await client.get("/system-config/redis/transactions")
    assert tx_res.status_code == 200
    assert "transactions" in tx_res.json()


@pytest.mark.asyncio
async def test_system_config_authorization_guards(client, db_session):
    cand = Candidate(
        fullname="Regular Candidate",
        email="reg_cand@example.com",
        password=hash_password("password123"),
        role="CANDIDATE"
    )
    db_session.add(cand)
    await db_session.commit()
    cand_id = cand.id

    cand_token = create_access_token({"sub": "reg_cand@example.com", "role": "CANDIDATE", "id": cand_id})
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # 1. Unauthenticated request to admin endpoint
    unauth_res = await client.get("/system-config/matching")
    assert unauth_res.status_code == 401

    # 2. Candidate forbidden from accessing admin endpoint
    forbidden_res = await client.get("/system-config/matching", headers=cand_headers)
    assert forbidden_res.status_code == 403
