"""
Supabase Storage utility for resume file management with Redis-first architecture.

All file upload and delete transactions are recorded in Redis first before executing
against Supabase Storage. File downloads, URLs, and file lists check Redis first
to eliminate external network latency and ensure smooth application performance.
"""

import os
import logging
import time
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from app.utils.redis_client import (
    redis_tx_manager,
    get_async_redis,
)
from app.utils.cache import (
    get_cache,
    set_cache,
    delete_cache,
    clear_cache_pattern,
)

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


# ── Public Redis-First API ──────────────────────────────────────────


async def upload_resume(
    file_bytes: bytes,
    original_filename: str,
    candidate_id: Optional[int] = None,
) -> dict:
    """
    Upload a resume file using Redis-first architecture:
    1. Transaction is staged in Redis first.
    2. File content and metadata are cached in Redis immediately.
    3. File is persisted to Supabase Storage (source of truth).
    4. Transaction is committed in Redis.
    """
    timestamp = int(time.time())
    safe_name = original_filename.replace(" ", "_")
    if candidate_id is not None:
        storage_path = f"resumes/{candidate_id}/{timestamp}_{safe_name}"
    else:
        storage_path = f"resumes/{timestamp}_{safe_name}"

    mime = _content_type(original_filename)

    # 1. Stage upload transaction in Redis first
    tx_payload = {
        "storage_path": storage_path,
        "filename": original_filename,
        "content_type": mime,
        "candidate_id": candidate_id,
        "size_bytes": len(file_bytes),
    }
    tx_id = await redis_tx_manager.stage_transaction(
        target="supabase_storage",
        action="UPLOAD",
        payload=tx_payload,
    )

    # 2. Pre-cache file bytes and metadata in Redis immediately
    try:
        redis_c = get_async_redis()
        # Cache raw file in Redis (24h TTL)
        await redis_c.setex(f"storage:file:{storage_path}", 86400, file_bytes)
        await set_cache(f"storage:meta:{storage_path}", tx_payload, ttl=86400)
    except Exception as cache_err:
        logger.warning(f"Failed to pre-cache uploaded file in Redis: {cache_err}")

    # 3. Persist to Supabase Storage (source of truth)
    try:
        client = _get_client()
        client.storage.from_(SUPABASE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime, "upsert": "true"},
        )
        public_url = client.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)

        # Cache public URL
        await set_cache(f"storage:url:{storage_path}", public_url, ttl=604800)  # 7 days
        # Invalidate lists
        await clear_cache_pattern("storage:list:")

        # 4. Commit transaction in Redis
        result_meta = {
            "storage_path": storage_path,
            "public_url": public_url,
            "filename": f"{timestamp}_{safe_name}",
        }
        await redis_tx_manager.commit_transaction(tx_id, result_meta)

        logger.info(f"[Redis-First] Uploaded resume to Supabase & cached in Redis: {storage_path}")
        return result_meta
    except Exception as e:
        logger.error(f"[Redis-First] Supabase upload failed for {storage_path}: {e}")
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        raise


async def download_resume(storage_path: str) -> bytes:
    """
    Download a resume file:
    1. Checks Redis cache first for instantaneous delivery.
    2. Falls back to Supabase Storage, caches result in Redis, and returns.
    """
    # 1. Check Redis first
    try:
        redis_c = get_async_redis()
        cached_bytes = await redis_c.get(f"storage:file:{storage_path}")
        if cached_bytes:
            logger.info(f"[Redis-First] Served resume directly from Redis cache: {storage_path}")
            return cached_bytes
    except Exception as cache_err:
        logger.warning(f"Redis lookup failed for {storage_path}: {cache_err}")

    # 2. Fetch from Supabase Storage (source of truth)
    client = _get_client()
    try:
        response = client.storage.from_(SUPABASE_BUCKET).download(storage_path)
        logger.info(f"[Redis-First] Downloaded resume from Supabase: {storage_path}")

        # Populate Redis cache for subsequent fast reads
        try:
            redis_c = get_async_redis()
            await redis_c.setex(f"storage:file:{storage_path}", 86400, response)
        except Exception:
            pass

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
    Delete a resume file using Redis-first architecture:
    1. Stages delete transaction in Redis first.
    2. Evicts from Redis cache.
    3. Deletes from Supabase Storage.
    4. Commits transaction in Redis.
    """
    # 1. Stage transaction in Redis first
    tx_id = await redis_tx_manager.stage_transaction(
        target="supabase_storage",
        action="DELETE",
        payload={"storage_path": storage_path},
    )

    # 2. Evict from Redis cache
    try:
        redis_c = get_async_redis()
        await redis_c.delete(f"storage:file:{storage_path}")
        await delete_cache(f"storage:meta:{storage_path}")
        await delete_cache(f"storage:url:{storage_path}")
        await clear_cache_pattern("storage:list:")
    except Exception as cache_err:
        logger.warning(f"Failed to evict file from Redis: {cache_err}")

    # 3. Delete from Supabase Storage (source of truth)
    client = _get_client()
    try:
        client.storage.from_(SUPABASE_BUCKET).remove([storage_path])
        await redis_tx_manager.commit_transaction(tx_id, {"deleted": True})
        logger.info(f"[Redis-First] Deleted resume from Supabase & Redis: {storage_path}")
        return True
    except Exception as e:
        logger.error(f"Supabase delete failed for {storage_path}: {e}")
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        return False


async def list_resumes(prefix: str = "resumes/") -> list[dict]:
    """
    List all resume files under prefix:
    1. Checks Redis cache first.
    2. On miss, queries Supabase, caches in Redis, and returns.
    """
    cache_key = f"storage:list:{prefix}"
    cached = await get_cache(cache_key)
    if cached is not None:
        logger.debug(f"[Redis-First] Served file list from Redis cache for '{prefix}'")
        return cached

    client = _get_client()
    try:
        files = client.storage.from_(SUPABASE_BUCKET).list(prefix)
        await set_cache(cache_key, files, ttl=600)  # 10 minutes
        logger.info(f"Listed {len(files)} files under '{prefix}' from Supabase and cached in Redis.")
        return files
    except Exception as e:
        logger.error(f"Supabase list failed for {prefix}: {e}")
        return []
