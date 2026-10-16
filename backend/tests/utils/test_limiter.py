import os
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
import pytest

from app.utils.limiter import limiter, REDIS_URL


def test_limiter_initialization():
    assert isinstance(limiter, Limiter)
    assert limiter.enabled is True
    assert limiter._key_func == get_remote_address
    assert isinstance(REDIS_URL, str)
    assert REDIS_URL.startswith("redis://") or "localhost" in REDIS_URL


@pytest.mark.asyncio
async def test_limiter_rate_limiting_on_route():
    app = FastAPI()
    app.state.limiter = limiter

    path = f"/limited-test-{uuid.uuid4().hex}"

    @app.get(path)
    @limiter.limit("2/minute")
    async def limited_endpoint(request: Request):
        return {"status": "ok"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First request succeeds
        res1 = await client.get(path)
        assert res1.status_code == 200

        # Second request succeeds
        res2 = await client.get(path)
        assert res2.status_code == 200

        # Third request exceeds 2/minute limit -> 429 Too Many Requests
        res3 = await client.get(path)
        assert res3.status_code == 429

