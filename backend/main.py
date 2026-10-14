import os
import sys
import logging
from contextlib import asynccontextmanager

# Ensure the backend directory is in sys.path so app.* modules resolve cleanly
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.utils.limiter import limiter
from app.utils.database import engine, Base 
from app.models import *
from app.controllers.auth_controller import router as auth_router
from app.controllers.admin_controller import router as admin_router
from app.controllers.hr_controller import router as hr_router
from app.controllers.candidate_controller import router as candidate_router
from app.controllers.resume_controller import router as resume_router
from app.controllers.job_application_controller import router as job_application_router
from app.controllers.notification_controller import router as notification_router
from app.controllers.job_matching_controller import router as job_matching_router
from app.controllers.chat_controller import router as chat_router
from app.controllers.ai_caller_controller import router as ai_caller_router
from app.controllers.interview_controller import router as interview_router
from app.controllers.system_config_controller import router as system_config_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.15:5173",
]

frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)
    for url in frontend_url.split(","):
        cleaned = url.strip().rstrip("/")
        if cleaned and cleaned not in origins:
            origins.append(cleaned)

for env_name in ("PUBLIC_BASE_URL", "APP_PUBLIC_URL", "FRONTEND_PUBLIC_URL"):
    configured_origin = os.getenv(env_name)
    if configured_origin:
        cleaned = configured_origin.strip().rstrip("/")
        if cleaned and cleaned not in origins:
            origins.append(cleaned)


async def ensure_application_analysis_columns(conn):
    """
    Existing deployments already have job_applications, and create_all() will not
    add new columns. Keep this narrow so the HR applications view does not 500
    before the manual migration has been run.
    """
    columns = {
        "skills_score": "DOUBLE PRECISION",
        "experience_score": "DOUBLE PRECISION",
        "education_score": "DOUBLE PRECISION",
        "resume_url": "VARCHAR",
        "skills_reason": "VARCHAR",
        "experience_reason": "VARCHAR",
        "education_reason": "VARCHAR",
        "matched_skills": "JSON",
        "missing_skills": "JSON",
        "relevant_experience": "VARCHAR",
        "experience_gaps": "VARCHAR",
        "required_degree": "VARCHAR",
        "candidate_degree": "VARCHAR",
        "recommendations": "JSON",
        "ai_summary": "VARCHAR",
        "strengths": "JSON",
        "weaknesses": "JSON",
        "ai_powered": "BOOLEAN DEFAULT FALSE",
    }

    dialect = conn.dialect.name
    for column_name, column_type in columns.items():
        try:
            if dialect == "sqlite":
                existing = await conn.execute(text("PRAGMA table_info(job_applications)"))
                existing_names = {row[1] for row in existing.fetchall()}
                if column_name not in existing_names:
                    sqlite_type = "TEXT" if column_type in ("VARCHAR", "JSON") else column_type
                    await conn.execute(text(f"ALTER TABLE job_applications ADD COLUMN {column_name} {sqlite_type}"))
            else:
                await conn.execute(text(
                    f"ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
                ))
        except Exception as e:
            logger.warning(f"Could not ensure job_applications.{column_name}: {e}")

    # Ensure google_credentials and related fields in users table
    user_columns = {
        "google_credentials": "TEXT",
        "google_access_token": "VARCHAR",
        "google_refresh_token": "VARCHAR",
        "google_token_expiry": "TIMESTAMP",
        "is_online": "BOOLEAN DEFAULT FALSE",
        "last_active": "TIMESTAMP",
    }
    for col_name, col_type in user_columns.items():
        try:
            if dialect == "sqlite":
                existing = await conn.execute(text("PRAGMA table_info(users)"))
                existing_names = {row[1] for row in existing.fetchall()}
                if col_name not in existing_names:
                    sqlite_type = "TEXT" if col_type in ("VARCHAR", "TIMESTAMP") else col_type
                    await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {sqlite_type}"))
            else:
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
        except Exception as e:
            logger.warning(f"Could not ensure users.{col_name}: {e}")


async def ensure_archived_conversations_table(conn):
    """
    Ensure the archived_conversations table exists in PostgreSQL or SQLite.
    """
    try:
        dialect = conn.dialect.name
        if dialect == "sqlite":
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS archived_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    contact_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_user_contact_archive UNIQUE (user_id, contact_id)
                )
            """))
        else:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS archived_conversations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    contact_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT uq_user_contact_archive UNIQUE (user_id, contact_id)
                )
            """))
    except Exception as e:
        logger.warning(f"Could not ensure archived_conversations table: {e}")


async def create_tables():
    from app.models.user import User
    from app.models.candidate import Candidate
    from app.models.hr import HR
    from app.models.admin import Admin
    from app.models.resume import Resume
    from app.models.job_application import JobApplication
    from app.models.notification import Notification
    from app.models.message import Message, ArchivedConversation
    from app.models.password_reset import PasswordReset
    from app.models.interview import Interview, InterviewLog
    from app.models.system_config import SystemConfig, FormTemplate

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await ensure_application_analysis_columns(conn)
            await ensure_archived_conversations_table(conn)
    except Exception as e:
        logger.debug(f"Table creation notice (concurrent worker init): {e}")


async def seed_demo_data_if_enabled():
    if os.getenv("AUTO_SEED_DEMO_DATA", "false").lower() not in {"1", "true", "yes"}:
        return

    try:
        from seed_demo_data import seed_demo_data  # type: ignore

        await seed_demo_data()
    except Exception as e:
        logger.warning(f"Could not seed demo data: {e}")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    await create_tables()
    await seed_demo_data_if_enabled()

    # Clean up stale user sessions (> 1 hour) and expired Google OAuth credentials on startup
    try:
        from datetime import datetime, timedelta
        async with engine.begin() as conn:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            await conn.execute(
                text("UPDATE users SET is_online = FALSE WHERE is_online = TRUE AND (last_active IS NULL OR last_active < :threshold)"),
                {"threshold": one_hour_ago}
            )
            await conn.execute(
                text("UPDATE users SET google_credentials = NULL, google_access_token = NULL, google_refresh_token = NULL WHERE google_token_expiry IS NOT NULL AND google_token_expiry < :now"),
                {"now": datetime.utcnow()}
            )
    except Exception as e:
        logger.warning(f"Could not clean up stale user sessions on startup: {e}")

    # Initialize Redis-first architecture and cross-worker real-time listeners
    from app.utils.redis_client import is_redis_available, close_redis_pools
    from app.utils.websocket_manager import manager as ws_manager

    if await is_redis_available():
        logger.info("[Redis-First] Redis connection established. Redis-first transaction layer active.")
        await ws_manager.start_redis_listener()
    else:
        logger.warning("[Redis-First] Redis unreachable at startup. Operating with direct source-of-truth fallback.")

    try:
        yield
    finally:
        logger.info("[Shutdown] Cleaning up Redis listeners and connection pools...")
        try:
            await ws_manager.stop_redis_listener()
        except Exception as e:
            logger.debug(f"Error stopping ws_manager listener: {e}")

        try:
            await close_redis_pools()
        except Exception as e:
            logger.debug(f"Error closing Redis pools: {e}")

        try:
            await engine.dispose()
        except Exception as e:
            logger.debug(f"Error disposing database engine: {e}")
        logger.info("[Shutdown] Cleanup completed.")


app = FastAPI(
    title="Fast API",
    description="""
    An AI-powered system for analyzing resumes and providing automated job recommendations.

    ## Features
    * **Authentication**: Secure login and registration.
    * **Resume Analysis**: Extract and process candidate data.
    * **Job Matching**: AI-driven job recommendations based on candidate profiles.
    * **Real-time Notifications**: Updates for job applications and status changes.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "url": "http://127.0.0.1:8000/docs",
    },
    lifespan=lifespan
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*\.trycloudflare\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(hr_router)
app.include_router(candidate_router)
app.include_router(resume_router)
app.include_router(job_application_router)
app.include_router(notification_router)
app.include_router(job_matching_router)
app.include_router(chat_router)
app.include_router(ai_caller_router)
app.include_router(interview_router)
app.include_router(system_config_router)


@app.get("/", tags=["Testing"])
async def root():
    logger.info("API Documentation: http://127.0.0.1:8000/docs")
    return {
        "message": "Automated Resume Analysis with Job Recommendation!",
        "docs_url": "http://127.0.0.1:8000/docs"
    }


# Register alias in sys.modules so any legacy imports of app.main resolve to this module
sys.modules["app.main"] = sys.modules[__name__]


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
