"""
Supabase Storage utility for resume file management.

Handles uploading, downloading, listing, and deleting resume files
in the Supabase 'resume storage' bucket.
"""

import os
import logging
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Supabase Configuration ─────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "resume storage")

_supabase_client = None


def _get_client():
    """Lazy-initialise and return the Supabase client (service-role)."""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
            )
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase client initialised successfully.")
    return _supabase_client


def _content_type(filename: str) -> str:
    """Return MIME type based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return mime_map.get(ext, "application/octet-stream")


# ── Public API ──────────────────────────────────────────────────────


async def upload_resume(
    file_bytes: bytes,
    original_filename: str,
    candidate_id: Optional[int] = None,
) -> dict:
    """
    Upload a resume file to Supabase Storage.

    Returns dict with:
        - storage_path: the path inside the bucket
        - public_url: the publicly accessible URL
        - filename: the sanitised filename stored
    """
    client = _get_client()

    # Build a unique, collision-free filename
    timestamp = int(time.time())
    safe_name = original_filename.replace(" ", "_")
    if candidate_id is not None:
        storage_path = f"resumes/{candidate_id}/{timestamp}_{safe_name}"
    else:
        storage_path = f"resumes/{timestamp}_{safe_name}"

    mime = _content_type(original_filename)

    try:
        client.storage.from_(SUPABASE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime, "upsert": "true"},
        )

        public_url = client.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)
        logger.info(f"Uploaded resume to Supabase: {storage_path}")

        return {
            "storage_path": storage_path,
            "public_url": public_url,
            "filename": f"{timestamp}_{safe_name}",
        }
    except Exception as e:
        logger.error(f"Supabase upload failed: {e}")
        raise


async def download_resume(storage_path: str) -> bytes:
    """
    Download a resume file from Supabase Storage.

    Returns the raw file bytes.
    """
    client = _get_client()
    try:
        response = client.storage.from_(SUPABASE_BUCKET).download(storage_path)
        logger.info(f"Downloaded resume from Supabase: {storage_path}")
        return response
    except Exception as e:
        logger.error(f"Supabase download failed for {storage_path}: {e}")
        raise


def get_public_url(storage_path: str) -> str:
    """
    Get the public URL for a file in the bucket.
    """
    client = _get_client()
    return client.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)


async def delete_resume(storage_path: str) -> bool:
    """
    Delete a resume file from Supabase Storage.
    """
    client = _get_client()
    try:
        client.storage.from_(SUPABASE_BUCKET).remove([storage_path])
        logger.info(f"Deleted resume from Supabase: {storage_path}")
        return True
    except Exception as e:
        logger.error(f"Supabase delete failed for {storage_path}: {e}")
        return False


async def list_resumes(prefix: str = "resumes/") -> list[dict]:
    """
    List all resume files in the bucket under a given prefix.
    """
    client = _get_client()
    try:
        files = client.storage.from_(SUPABASE_BUCKET).list(prefix)
        logger.info(f"Listed {len(files)} files under '{prefix}'")
        return files
    except Exception as e:
        logger.error(f"Supabase list failed for {prefix}: {e}")
        return []
