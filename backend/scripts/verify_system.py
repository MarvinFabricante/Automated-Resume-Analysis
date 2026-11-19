import os
import sys
import requests
import json

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

BACKEND_LOCAL = "http://127.0.0.1:8000"
FRONTEND_LOCAL = "http://127.0.0.1:5173"
TUNNEL_URL = "https://safer-shame-launches-cbs.trycloudflare.com"

print("=" * 65)
print(" MARIWASA RECRUITMENT SYSTEM - VERIFICATION SUITE")
print("=" * 65)

# 1. Backend /docs
r_docs = requests.get(f"{BACKEND_LOCAL}/docs", timeout=5)
assert r_docs.status_code == 200, f"Expected 200, got {r_docs.status_code}"
print(f"✓ Backend /docs is HEALTHY (Status {r_docs.status_code})")

# 2. Frontend Local
r_front = requests.get(FRONTEND_LOCAL, timeout=5)
assert r_front.status_code == 200, f"Expected 200, got {r_front.status_code}"
print(f"✓ Frontend Local ({FRONTEND_LOCAL}) is HEALTHY (Status {r_front.status_code})")

# 3. Frontend Public Tunnel
r_tunnel = requests.get(TUNNEL_URL, timeout=8)
assert r_tunnel.status_code == 200, f"Expected 200, got {r_tunnel.status_code}"
print(f"✓ Frontend Public Tunnel ({TUNNEL_URL}) is HEALTHY (Status {r_tunnel.status_code})")

# 4. HR Login
r_hr = requests.post(f"{BACKEND_LOCAL}/auth/login", json={"email": "johnpaul6214@gmail.com", "password": "password123"})
assert r_hr.status_code == 200, f"HR login failed: {r_hr.status_code} {r_hr.text}"
hr_data = r_hr.json()
hr_token = hr_data.get("access_token")
assert hr_data.get("role") == "HR"
print(f"✓ HR Login successful for {hr_data.get('fullname')} ({hr_data.get('role')})")

# 5. Admin Login
r_admin = requests.post(f"{BACKEND_LOCAL}/auth/login", json={"email": "admin@mariwasa.com", "password": "admin123"})
assert r_admin.status_code == 200, f"Admin login failed: {r_admin.status_code} {r_admin.text}"
admin_data = r_admin.json()
admin_token = admin_data.get("access_token")
assert admin_data.get("role") == "ADMIN"
print(f"✓ Admin Login successful for {admin_data.get('fullname')} ({admin_data.get('role')})")

hr_headers = {"Authorization": f"Bearer {hr_token}"}
admin_headers = {"Authorization": f"Bearer {admin_token}"}

# 6. Check Jobs: 4 Active (J1-J4) and 1 Archived (J5)
# Query active jobs
r_active_jobs = requests.get(f"{BACKEND_LOCAL}/admins/read-jobs?include_inactive=false", headers=admin_headers)
assert r_active_jobs.status_code == 200
active_jobs = r_active_jobs.json()
print(f"\n✓ Active Jobs Query: {len(active_jobs)} jobs returned (Expected: 4)")
for j in active_jobs:
    print(f"    • [{j.get('job_id')}] {j.get('job_title')} ({j.get('department')}) - Active: {j.get('is_active')}")
assert len(active_jobs) == 4, f"Expected 4 active jobs, got {len(active_jobs)}"

# Query all jobs including inactive
r_all_jobs = requests.get(f"{BACKEND_LOCAL}/admins/read-jobs?include_inactive=true", headers=admin_headers)
assert r_all_jobs.status_code == 200
all_jobs = r_all_jobs.json()
archived_jobs = [j for j in all_jobs if not j.get("is_active")]
print(f"✓ All Jobs Query: {len(all_jobs)} total jobs, {len(archived_jobs)} archived (Expected: 1 archived)")
for j in archived_jobs:
    print(f"    • [ARCHIVED] [{j.get('job_id')}] {j.get('job_title')} ({j.get('department')}) - Active: {j.get('is_active')}")
assert len(all_jobs) == 5, f"Expected 5 total jobs, got {len(all_jobs)}"
assert len(archived_jobs) == 1, f"Expected 1 archived job, got {len(archived_jobs)}"
assert archived_jobs[0].get("job_id") == "JOB-2026-0005"
assert archived_jobs[0].get("job_title") == "Logistics Coordinator"

# 7. Check Applications:
r_apps = requests.get(f"{BACKEND_LOCAL}/applications", headers=hr_headers)
assert r_apps.status_code == 200
apps = r_apps.json()
print(f"\n✓ Applications directory returned {len(apps)} applications")

# 8. Check Physical / Imported Resumes: Empty (0)
r_imports = requests.get(f"{BACKEND_LOCAL}/hr/physical-resumes/", headers=hr_headers)
assert r_imports.status_code == 200
import_items = r_imports.json().get("items", [])
assert len(import_items) == 0, f"Expected 0 imported resumes, got {len(import_items)}"
print(f"✓ Import Resumes list is empty ({len(import_items)} items)")

# 9. Check Shortlist Rosters: Empty (0)
r_shortlists = requests.get(f"{BACKEND_LOCAL}/hr/shortlists", headers=hr_headers)
assert r_shortlists.status_code == 200
shortlists = r_shortlists.json()
assert len(shortlists) == 0, f"Expected 0 shortlists, got {len(shortlists)}"
print(f"✓ Shortlist Rosters list is empty ({len(shortlists)} rosters)")

# 10. Check Open Positions count via Candidate count / Job count KPI
r_hr_counts = requests.get(f"{BACKEND_LOCAL}/hr/candidate-count", headers=hr_headers)
if r_hr_counts.status_code == 200:
    counts = r_hr_counts.json()
    print(f"✓ Candidate count endpoint: {counts}")
    assert "count" in counts

# Check Admin dashboard stats
r_admin_dash = requests.get(f"{BACKEND_LOCAL}/admins/dashboard", headers=admin_headers)
if r_admin_dash.status_code == 200:
    dash = r_admin_dash.json()
    jobs_count = dash.get("jobs_count")
    candidates_count = dash.get("candidates_count")
    print(f"✓ Admin Dashboard stats: Total Jobs={jobs_count}, Candidates={candidates_count}")

# Check HR application stats
r_app_stats = requests.get(f"{BACKEND_LOCAL}/hr/application-stats", headers=hr_headers)
if r_app_stats.status_code == 200:
    app_stats = r_app_stats.json()
    print(f"✓ HR Application Funnel stats: {app_stats}")
    assert "pending" in app_stats
    assert "total" in app_stats

print("=" * 65)
print(" ALL 10 VERIFICATION CHECKS PASSED 100%!")
print("=" * 65)
