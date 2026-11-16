"""
Migration script:
1. Uploads existing profile images from uploads/profile_images to Supabase bucket 'profile_images' (path 'profiles/').
2. Uploads existing resume images from uploads/resume_images to Supabase bucket 'resume_images' (path 'resumeimages/').
3. Updates database records (users, candidates, hr, admins, job_applications) where image URLs point to local uploads.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load env
load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.utils.supabase_storage import (
    _get_client,
    _content_type,
    SUPABASE_PROFILE_BUCKET,
    SUPABASE_PROFILE_PATH,
    SUPABASE_RESUME_IMAGES_BUCKET,
    SUPABASE_RESUME_IMAGES_PATH,
)


async def migrate():
    client = _get_client()
    print("--- 1. Migrating Resume Images ---")
    resume_images_dir = "/home/marvin/Documents/automated_resume_analysis/backend/uploads/resume_images"
    resume_image_url_map = {}
    if os.path.exists(resume_images_dir):
        files = os.listdir(resume_images_dir)
        print(f"Found {len(files)} resume images.")
        for f in files:
            file_path = os.path.join(resume_images_dir, f)
            if not os.path.isfile(file_path):
                continue
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
            mime = _content_type(f)
            storage_path = f"{SUPABASE_RESUME_IMAGES_PATH}/{f}"
            try:
                client.storage.from_(SUPABASE_RESUME_IMAGES_BUCKET).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": mime, "upsert": "true"},
                )
                pub_url = client.storage.from_(SUPABASE_RESUME_IMAGES_BUCKET).get_public_url(storage_path)
                resume_image_url_map[f] = pub_url
                print(f"Uploaded: {f} -> {pub_url}")
            except Exception as err:
                print(f"Error uploading {f}: {err}")

    print("\n--- 2. Migrating Profile Images ---")
    profile_images_dir = "/home/marvin/Documents/automated_resume_analysis/backend/uploads/profile_images"
    profile_image_url_map = {}
    if os.path.exists(profile_images_dir):
        files = os.listdir(profile_images_dir)
        print(f"Found {len(files)} profile images.")
        for f in files:
            file_path = os.path.join(profile_images_dir, f)
            if not os.path.isfile(file_path):
                continue
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
            mime = _content_type(f)
            storage_path = f"{SUPABASE_PROFILE_PATH}/{f}"
            try:
                client.storage.from_(SUPABASE_PROFILE_BUCKET).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": mime, "upsert": "true"},
                )
                pub_url = client.storage.from_(SUPABASE_PROFILE_BUCKET).get_public_url(storage_path)
                profile_image_url_map[f] = pub_url
                print(f"Uploaded: {f} -> {pub_url}")
            except Exception as err:
                print(f"Error uploading {f}: {err}")

    print("\n--- 3. Updating Database Records ---")
    load_dotenv()
    db_urls = [
        os.getenv("DATABASE_URL", ""),
        f"postgresql+asyncpg://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', '')}@localhost:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'automated_resume_db')}",
    ]
    engine = None
    for url in db_urls:
        if not url:
            continue
        try:
            test_engine = create_async_engine(url)
            async with test_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            engine = test_engine
            break
        except Exception:
            pass

    if not engine:
        print("Could not connect to database for URL migration.")
        return

    async with engine.begin() as conn:
        # Update job_applications
        res = await conn.execute(text("SELECT id, profile_image_url FROM job_applications WHERE profile_image_url IS NOT NULL"))
        rows = res.fetchall()
        for app_id, curr_url in rows:
            for fname, pub_url in resume_image_url_map.items():
                if fname in curr_url:
                    await conn.execute(
                        text("UPDATE job_applications SET profile_image_url = :url WHERE id = :id"),
                        {"url": pub_url, "id": app_id}
                    )
                    print(f"Updated job_application #{app_id}: {curr_url} -> {pub_url}")
                    break

        # Update users
        res = await conn.execute(text("SELECT id, profile_image_url FROM users WHERE profile_image_url IS NOT NULL"))
        rows = res.fetchall()
        for user_id, curr_url in rows:
            for fname, pub_url in profile_image_url_map.items():
                if fname in curr_url:
                    await conn.execute(
                        text("UPDATE users SET profile_image_url = :url WHERE id = :id"),
                        {"url": pub_url, "id": user_id}
                    )
                    print(f"Updated user #{user_id}: {curr_url} -> {pub_url}")
                    break

    await engine.dispose()
    print("\nMigration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
