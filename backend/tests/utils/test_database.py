import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from app.utils.database import (
    get_database_url,
    get_db,
    init_db,
    Base,
    engine,
    AsyncSessionLocal,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
)


def test_get_database_url_from_env_postgres_prefix():
    with patch.dict(os.environ, {"DATABASE_URL": "postgres://user:pass@host:5432/db"}, clear=False):
        url = get_database_url()
        assert url.startswith("postgresql+asyncpg://")
        assert "user:pass@host:5432/db" in url


def test_get_database_url_from_env_postgresql_prefix():
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}, clear=False):
        url = get_database_url()
        assert url.startswith("postgresql+asyncpg://")
        assert "user:pass@host:5432/db" in url


def test_get_database_url_from_env_already_asyncpg():
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db"}, clear=False):
        url = get_database_url()
        assert url == "postgresql+asyncpg://user:pass@host:5432/db"


def test_get_database_url_from_env_sqlite():
    with patch.dict(os.environ, {"DATABASE_URL": "sqlite+aiosqlite:///:memory:"}, clear=False):
        url = get_database_url()
        assert url == "sqlite+aiosqlite:///:memory:"


def test_get_database_url_fallback_components():
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "",
            "DB_USER": "myuser",
            "DB_PASSWORD": "mypassword",
            "DB_HOST": "dbhost",
            "DB_PORT": "5433",
            "DB_NAME": "testdb",
        },
        clear=False,
    ):
        url = get_database_url()
        assert url == "postgresql+asyncpg://myuser:mypassword@dbhost:5433/testdb"


def test_database_engine_and_base_configuration():
    assert Base is not None
    assert engine is not None
    assert AsyncSessionLocal is not None
    assert isinstance(DB_POOL_SIZE, int)
    assert isinstance(DB_MAX_OVERFLOW, int)


@pytest.mark.asyncio
async def test_get_db_success():
    mock_session = AsyncMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.utils.database.AsyncSessionLocal", return_value=mock_session_ctx):
        gen = get_db()
        session = await gen.asend(None)
        assert session == mock_session
        with pytest.raises(StopAsyncIteration):
            await gen.asend(None)
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_sqlalchemy_error():
    mock_session = AsyncMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.utils.database.AsyncSessionLocal", return_value=mock_session_ctx):
        gen = get_db()
        session = await gen.asend(None)
        assert session == mock_session

        with pytest.raises(SQLAlchemyError):
            await gen.athrow(SQLAlchemyError("DB connection dropped"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_generic_exception():
    mock_session = AsyncMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.utils.database.AsyncSessionLocal", return_value=mock_session_ctx):
        gen = get_db()
        session = await gen.asend(None)
        assert session == mock_session

        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("Unexpected error"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_db_success():
    mock_conn = AsyncMock()
    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_begin.__aexit__ = AsyncMock(return_value=None)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_begin

    with patch("app.utils.database.engine", mock_engine):
        await init_db()
        mock_conn.run_sync.assert_awaited_once_with(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_init_db_sqlalchemy_error():
    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(side_effect=SQLAlchemyError("Connection refused"))
    mock_begin.__aexit__ = AsyncMock(return_value=None)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_begin

    with patch("app.utils.database.engine", mock_engine):
        with pytest.raises(SQLAlchemyError):
            await init_db()


@pytest.mark.asyncio
async def test_init_db_generic_error():
    mock_begin = MagicMock()
    mock_begin.__aenter__ = AsyncMock(side_effect=Exception("Initialization failed"))
    mock_begin.__aexit__ = AsyncMock(return_value=None)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_begin

    with patch("app.utils.database.engine", mock_engine):
        with pytest.raises(Exception):
            await init_db()
