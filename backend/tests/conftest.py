import asyncio
import pytest
import pytest_asyncio
from unittest.mock import patch
from app.utils.limiter import limiter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import ASGITransport, AsyncClient
from main import app
from app.utils.database import Base, get_db

# Use SQLite in-memory for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(loop_scope="function")
async def test_engine():
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(loop_scope="function")
async def db_session(test_engine):
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture(loop_scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def isolate_rate_limits():
    # Use deterministic per-test memory storage, never the deployment's Redis buckets.
    from limits.storage import MemoryStorage
    from limits.strategies import FixedWindowRateLimiter
    storage = MemoryStorage()
    with patch.object(limiter, '_storage', storage), patch.object(limiter, '_limiter', FixedWindowRateLimiter(storage)):
        yield
