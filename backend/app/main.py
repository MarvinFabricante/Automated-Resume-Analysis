from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.utils.limiter import limiter
from app.utils.database import engine, Base 
from sqlalchemy import text
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

import os
import logging

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",

    "http://localhost:3000",
    "http://127.0.0.1:3000",

    "http://192.168.1.15:5173",
]

frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackendApplication:
    def __init__(self):
        self.app = FastAPI(
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
            }
        )

    def create_app(self) -> FastAPI:
        self.configure_rate_limiting()
        self.configure_middleware()
        self.configure_static_files()
        self.include_routers()
        self.register_events()
        self.register_routes()
        return self.app

    def configure_rate_limiting(self):
        self.app.state.limiter = limiter
        self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    def configure_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def configure_static_files(self):
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
        self.app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    def include_routers(self):
        self.app.include_router(auth_router)
        self.app.include_router(admin_router)
        self.app.include_router(hr_router)
        self.app.include_router(candidate_router)
        self.app.include_router(resume_router)
        self.app.include_router(job_application_router)
        self.app.include_router(notification_router)
        self.app.include_router(job_matching_router)
        self.app.include_router(chat_router)
        self.app.include_router(ai_caller_router)
        self.app.include_router(interview_router)
        self.app.include_router(system_config_router)

    def register_events(self):
        self.app.on_event("startup")(self.startup)

    def register_routes(self):
        self.app.get("/", tags=["Testing"])(self.root)

    async def create_tables(self):
        from app.models.user import User
        from app.models.candidate import Candidate
        from app.models.hr import HR
        from app.models.admin import Admin
        from app.models.resume import Resume
        from app.models.job_application import JobApplication
        from app.models.notification import Notification
        from app.models.message import Message
        from app.models.password_reset import PasswordReset
        from app.models.interview import Interview, InterviewLog
        from app.models.system_config import SystemConfig, FormTemplate

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self.ensure_application_analysis_columns(conn)

    async def ensure_application_analysis_columns(self, conn):
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

        # Ensure google_credentials in users table
        try:
            if dialect == "sqlite":
                existing = await conn.execute(text("PRAGMA table_info(users)"))
                existing_names = {row[1] for row in existing.fetchall()}
                if "google_credentials" not in existing_names:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN google_credentials TEXT"))
            else:
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_credentials TEXT"))
        except Exception as e:
            logger.warning(f"Could not ensure users.google_credentials: {e}")

    async def startup(self):
        await self.create_tables()

    async def root(self):
        logger.info("API Documentation: http://127.0.0.1:8000/docs")
        return {
            "message": "Automated Resume Analysis with Job Recommendation!",
            "docs_url": "http://127.0.0.1:8000/docs"
        }


backend_application = BackendApplication()
app = backend_application.create_app()


async def create_tables():
    return await backend_application.create_tables()


async def ensure_application_analysis_columns(conn):
    return await backend_application.ensure_application_analysis_columns(conn)


async def startup():
    return await backend_application.startup()


async def root():
    return await backend_application.root()

# SHIFT NA BS ECE