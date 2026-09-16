import os
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

def get_database_url():
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "passwordnamin")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "automated_resume_db")
    
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"

DATABASE_URL = get_database_url()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
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
            
        logger.info("Database schema initialized successfully.")

    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error during database initialization: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {str(e)}")
        raise