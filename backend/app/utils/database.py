import os
import socket
import logging

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def _is_tcp_reachable(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False

def get_database_url():
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "passwordnamin")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "automated_resume_db")
        url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"

    if url.startswith("postgresql") and any(h in url for h in ("@localhost", "@127.0.0.1")):
        port = int(os.getenv("DB_PORT", "5432"))
        if not _is_tcp_reachable("127.0.0.1", port):
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            sqlite_path = os.path.join(backend_dir, "automated_resume.db").replace("\\", "/")
            fallback_url = f"sqlite+aiosqlite:///{sqlite_path}"
            logger.warning(
                f"PostgreSQL is not reachable on 127.0.0.1:{port}; falling back to local SQLite database ({sqlite_path})."
            )
            return fallback_url

    return url

DATABASE_URL = get_database_url()

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "50"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "60"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

if DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        future=True,
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE,
        future=True,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()

async def get_db():
    """
    FastAPI dependency that provides
    a fully async database session
    with proper error handling.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session

        except SQLAlchemyError as e:
            logger.error(f"Database error occurred: {str(e)}")
            await session.rollback()
            raise

        except Exception as e:
            logger.error(f"Unexpected error occurred: {str(e)}")
            await session.rollback()
            raise

        finally:
            await session.close()

async def init_db():
    """
    Create database tables asynchronously.
    Ensures all models are imported so SQLAlchemy can track them.
    """
    try:
        # Import all models here so they register with Base.metadata
        import app.models
        
        logger.info("Initializing database schema...")
        async with engine.begin() as conn:
            # We use run_sync because metadata.create_all is a synchronous method
            await conn.run_sync(Base.metadata.create_all)
            from migrations.add_requirement_confirmations import upgrade as upgrade_requirement_confirmations
            await upgrade_requirement_confirmations(conn)
            from migrations.add_recruitment_lifecycle_rules import upgrade as upgrade_lifecycle_rules
            await upgrade_lifecycle_rules(conn)

            # Auto-migrate newly added columns if they don't exist yet
            def _check_and_add_columns(sync_conn):
                from sqlalchemy import text
                # shortlist_rosters.is_archived
                try:
                    sync_conn.execute(text("ALTER TABLE shortlist_rosters ADD COLUMN is_archived BOOLEAN DEFAULT 0"))
                except Exception:
                    pass
                # job_applications.import_origin
                try:
                    sync_conn.execute(text("ALTER TABLE job_applications ADD COLUMN import_origin VARCHAR"))
                except Exception:
                    pass
                # job_applications.imported_by
                try:
                    sync_conn.execute(text("ALTER TABLE job_applications ADD COLUMN imported_by VARCHAR"))
                except Exception:
                    pass
                # job_applications.user_id
                try:
                    sync_conn.execute(text("ALTER TABLE job_applications ADD COLUMN user_id INTEGER"))
                except Exception:
                    pass
                # job_applications.resume_email
                try:
                    sync_conn.execute(text("ALTER TABLE job_applications ADD COLUMN resume_email VARCHAR"))
                except Exception:
                    pass
                # job_applications.contact_email
                try:
                    sync_conn.execute(text("ALTER TABLE job_applications ADD COLUMN contact_email VARCHAR"))
                except Exception:
                    pass

            await conn.run_sync(_check_and_add_columns)
            
        logger.info("Database schema initialized successfully.")

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error during database initialization: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {str(e)}")
        raise