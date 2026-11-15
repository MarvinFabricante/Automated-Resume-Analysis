#!/usr/bin/env python3
"""
Development Data Reset Script for Mariwasa Recruitment System.

Resets test applicant data, jobs, rosters, applications, and logs while preserving
HR & Admin accounts, roles, permissions, database schema, and system configurations.

Usage:
    python scripts/reset_dev_data.py [--force-dev]
"""

import os
import sys
import shutil
import sqlite3
import argparse
from datetime import datetime

# Add project root and backend to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

TABLES_TO_CLEAR_ALL = [
    "application_status_history",
    "applicant_profile_access_logs",
    "hr_candidate_notes",
    "shortlist_roster_items",
    "shortlist_rosters",
    "interview_logs",
    "interviews",
    "voice_call_records",
    "job_applications",
    "physical_resumes",
    "resumes",
    "candidates",
    "messages",
    "archived_conversations",
    "notifications",
    "audit_logs",
    "form_templates",
    "password_resets",
    "job_descriptions",
]

PRESERVED_TABLES = [
    "users (HR and Admin accounts preserved)",
    "admins",
    "hr_staffs",
    "system_configs (matching weights, settings)",
]


def check_is_dev_environment(force: bool = False) -> bool:
    """Verifies that the target is a development / test database."""
    if force:
        print("[SAFETY] --force-dev flag provided; proceeding.")
        return True

    env_val = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
    db_url = os.getenv("DATABASE_URL", "")

    # SQLite fallback is always local development
    sqlite_db = os.path.join(BACKEND_DIR, "automated_resume.db")
    if os.path.exists(sqlite_db):
        return True

    if "prod" in env_val or "production" in db_url.lower():
        print(f"[SAFETY ERROR] Production environment detected ({env_val}, {db_url})!")
        print("Aborting. To override on non-production systems, pass --force-dev.")
        sys.exit(1)

    return True


def create_backups() -> list[str]:
    """Creates timestamped backups of all local SQLite databases."""
    backup_dir = os.path.join(ROOT_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    created_backups = []

    # 1. Main database (SQLite)
    main_db = os.path.join(BACKEND_DIR, "automated_resume.db")
    if os.path.exists(main_db):
        backup_file = os.path.join(backup_dir, f"automated_resume_db_{ts}.sqlite")
        shutil.copy2(main_db, backup_file)
        created_backups.append(backup_file)
        print(f"[BACKUP] Main database backed up to: {backup_file}")

    # 2. Feedback database (Phase 3 HITL predictions)
    feedback_db = os.path.join(BACKEND_DIR, "data", "feedback.db")
    if os.path.exists(feedback_db):
        fb_backup = os.path.join(backup_dir, f"feedback_db_{ts}.sqlite")
        shutil.copy2(feedback_db, fb_backup)
        created_backups.append(fb_backup)
        print(f"[BACKUP] Feedback database backed up to: {fb_backup}")

    return created_backups


def get_sqlite_row_counts(db_path: str) -> dict[str, int]:
    """Returns row counts for all tables in SQLite database."""
    counts = {}
    if not os.path.exists(db_path):
        return counts

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]

    for t in tables:
        try:
            if t == "users":
                cnt = cur.execute("SELECT COUNT(*) FROM users WHERE role NOT IN ('HR', 'ADMIN')").fetchone()[0]
                counts["users (candidates)"] = cnt
                hr_cnt = cur.execute("SELECT COUNT(*) FROM users WHERE role IN ('HR', 'ADMIN')").fetchone()[0]
                counts["users (HR/Admin to keep)"] = hr_cnt
            else:
                cnt = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                counts[t] = cnt
        except Exception as e:
            counts[t] = -1

    conn.close()
    return counts


def reset_sqlite_data(db_path: str) -> dict[str, int]:
    """Clears test data from the main SQLite database while keeping HR/Admin."""
    cleared = {}
    if not os.path.exists(db_path):
        return cleared

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Disable foreign keys temporarily during purge for clean order
    cur.execute("PRAGMA foreign_keys = OFF;")

    for table in TABLES_TO_CLEAR_ALL:
        # Check if table exists
        exists = cur.execute(f"SELECT 1 FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
        if exists:
            cnt = cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            cur.execute(f'DELETE FROM "{table}";')
            cleared[table] = cnt

    # Clear only candidate users from users table
    user_cand_cnt = cur.execute("SELECT COUNT(*) FROM users WHERE role NOT IN ('HR', 'ADMIN')").fetchone()[0]
    cur.execute("DELETE FROM users WHERE role NOT IN ('HR', 'ADMIN');")
    cleared["users (candidates)"] = user_cand_cnt

    # Reset SQLite autoincrement sequences for cleared tables
    tables_to_reset_seq = TABLES_TO_CLEAR_ALL
    placeholders = ",".join(f"'{t}'" for t in tables_to_reset_seq)
    try:
        cur.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders});")
    except Exception:
        pass

    conn.commit()
    cur.execute("PRAGMA foreign_keys = ON;")
    conn.close()

    # Vacuum to reclaim space
    conn = sqlite3.connect(db_path)
    conn.execute("VACUUM;")
    conn.close()

    return cleared


def reset_feedback_db():
    """Clears live prediction evaluations from feedback.db."""
    fb_path = os.path.join(BACKEND_DIR, "data", "feedback.db")
    if not os.path.exists(fb_path):
        return 0

    conn = sqlite3.connect(fb_path)
    cur = conn.cursor()
    cnt = 0
    try:
        exists = cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='application_evaluations'").fetchone()
        if exists:
            cnt = cur.execute("SELECT COUNT(*) FROM application_evaluations").fetchone()[0]
            cur.execute("DELETE FROM application_evaluations;")
            cur.execute("DELETE FROM sqlite_sequence WHERE name='application_evaluations';")
            conn.commit()
            cur.execute("VACUUM;")
    finally:
        conn.close()
    return cnt


def clean_local_uploaded_files() -> int:
    """Removes stored uploaded files from local upload directories."""
    upload_dirs = [
        os.path.join(ROOT_DIR, "uploads", "physical_resumes"),
        os.path.join(ROOT_DIR, "uploads", "resumes"),
        os.path.join(ROOT_DIR, "uploads", "resume_images"),
        os.path.join(BACKEND_DIR, "uploads", "physical_resumes"),
        os.path.join(BACKEND_DIR, "uploads", "resumes"),
        os.path.join(BACKEND_DIR, "uploads", "resume_images"),
        os.path.join(ROOT_DIR, "exports"),
        os.path.join(BACKEND_DIR, "exports"),
    ]

    total_deleted = 0
    for udir in upload_dirs:
        if os.path.exists(udir):
            for fname in os.listdir(udir):
                fpath = os.path.join(udir, fname)
                try:
                    if os.path.isfile(fpath) or os.path.islink(fpath):
                        os.unlink(fpath)
                        total_deleted += 1
                    elif os.path.isdir(fpath):
                        shutil.rmtree(fpath)
                        total_deleted += 1
                except Exception as e:
                    print(f"[WARN] Could not delete {fpath}: {e}")
        else:
            os.makedirs(udir, exist_ok=True)

    print(f"[STORAGE] Cleared {total_deleted} local uploaded/generated files across upload folders.")
    return total_deleted


def clean_supabase_storage():
    """Removes test resumes from Supabase Storage buckets if accessible."""
    sb_url = os.getenv("SUPABASE_URL")
    sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    bucket_name = os.getenv("SUPABASE_BUCKET", "resume storage")

    if not sb_url or not sb_key:
        print("[STORAGE] Supabase credentials not set, skipping remote bucket prune.")
        return

    try:
        from supabase import create_client
        client = create_client(sb_url, sb_key)
        files = client.storage.from_(bucket_name).list("resumes")
        if files:
            paths = [f"resumes/{f['name']}" for f in files if f.get("name") and f['name'] != '.emptyFolderPlaceholder']
            if paths:
                client.storage.from_(bucket_name).remove(paths)
                print(f"[STORAGE] Removed {len(paths)} files from Supabase '{bucket_name}/resumes'.")
    except Exception as e:
        print(f"[STORAGE WARN] Supabase cleanup note: {e}")


def flush_redis_cache():
    """Flushes Redis database 0 (cache, rate limits, queued celery tasks)."""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=2)
        r.ping()
        r.flushdb()
        print("[REDIS] Successfully flushed Redis DB 0 (cache, rate limits, queues).")
    except Exception as e:
        print(f"[REDIS WARN] Could not flush Redis: {e}")


def main():
    parser = argparse.ArgumentParser(description="Reset dev data for Mariwasa Recruitment System")
    parser.add_argument("--force-dev", action="store_true", help="Force run even without dev check")
    args = parser.parse_args()

    print("=" * 65)
    print(" MARIWASA RECRUITMENT SYSTEM - DEVELOPMENT DATA RESET")
    print("=" * 65)

    # 1. Safety Check
    check_is_dev_environment(args.force_dev)

    # 2. Safety Backup
    backups = create_backups()

    # 3. Inspect before counts
    main_db = os.path.join(BACKEND_DIR, "automated_resume.db")
    print("\n[INSPECTION] Table row counts BEFORE reset:")
    before_counts = get_sqlite_row_counts(main_db)
    for tbl, count in sorted(before_counts.items()):
        status = "KEEP" if "keep" in tbl.lower() or tbl in PRESERVED_TABLES else "CLEAR"
        print(f"  • {tbl:<35}: {count:>4} rows  [{status}]")

    # 4. Perform Data Reset
    print("\n[RESETTING] Clearing test tables in a single transaction...")
    cleared = reset_sqlite_data(main_db)
    fb_cleared = reset_feedback_db()
    if fb_cleared:
        cleared["application_evaluations (feedback.db)"] = fb_cleared

    # 5. Clean Uploaded Files
    clean_local_uploaded_files()
    clean_supabase_storage()

    # 6. Flush Redis
    flush_redis_cache()

    # 7. Print Summary
    print("\n" + "=" * 65)
    print(" RESET COMPLETE - SUMMARY")
    print("=" * 65)
    print("Backups Created:")
    for b in backups:
        print(f"  • {b}")

    print("\nRows Cleared:")
    for tbl, cnt in sorted(cleared.items()):
        print(f"  • {tbl:<38}: {cnt:>4} rows removed")

    print("\nPreserved:")
    for p in PRESERVED_TABLES:
        print(f"  ✓ {p}")

    # Verify preserved users
    if os.path.exists(main_db):
        conn = sqlite3.connect(main_db)
        remaining_users = conn.execute("SELECT id, email, role FROM users").fetchall()
        print("\nActive Staff Accounts Remaining in Database:")
        for u in remaining_users:
            print(f"  ✓ User #{u[0]}: {u[1]} ({u[2]})")
        conn.close()

    print("\nReady for seeding jobs via: python scripts/seed_test_jobs.py")
    print("=" * 65)


if __name__ == "__main__":
    main()
