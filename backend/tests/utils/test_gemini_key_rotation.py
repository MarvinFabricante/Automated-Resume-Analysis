"""
Comprehensive test suite for Gemini API integration, primary-first key rotation,
error handling, exponential backoff, cooldown recovery, project-level quota respect,
concurrency/thread safety, secret redaction, graceful fallback, and admin status API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from unittest.mock import patch

import httpx
import pytest

from app.models.job_description import JobDescription, JobType
from app.services import ai_analysis_service, gemini_service, job_matching_service
from app.utils.auth import create_access_token
from app.utils.gemini_client import (
    GeminiAllKeysExhaustedError,
    GeminiAuthError,
    GeminiBadRequestError,
    GeminiClient,
    GeminiConfigurationError,
    GeminiModelUnavailableError,
    GeminiQuotaExhaustedError,
    GeminiRateLimitError,
    GeminiTransientError,
    classify_http_error,
    reload_gemini_client,
)
from app.utils.gemini_key_manager import (
    GeminiKeyManager,
    KeyPoolConfig,
    KeyStatus,
    load_gemini_api_keys_from_env,
    sanitize_error_message,
)


FAKE_KEYS = [
    "AQ.TestPrimaryKey000000000000000000000000000000001",
    "AQ.TestBackupKey0000000000000000000000000000000002",
    "AQ.TestTertiaryKey00000000000000000000000000000003",
]


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self._now = start
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            return self._now

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._now += seconds


def _ok_gemini_json(text: str = '{"ok": true}', prompt_tokens: int = 12, output_tokens: int = 8) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": text}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": prompt_tokens,
                "candidatesTokenCount": output_tokens,
                "totalTokenCount": prompt_tokens + output_tokens,
            },
        },
    )


def _error_response(
    status_code: int,
    *,
    status_str: str = "ERROR",
    message: str = "Error",
    details: list | None = None,
    headers: dict | None = None,
) -> httpx.Response:
    body: Dict = {"error": {"code": status_code, "message": message, "status": status_str}}
    if details is not None:
        body["error"]["details"] = details
    return httpx.Response(status_code, json=body, headers=headers or {})


def _make_client(
    handler,
    *,
    keys: List[str] | None = None,
    project_ids: List[str | None] | None = None,
    config: KeyPoolConfig | None = None,
    clock: FakeClock | None = None,
    models: List[str] | None = None,
    sleeps: List[float] | None = None,
) -> tuple[GeminiClient, FakeClock, List[float]]:
    clk = clock or FakeClock()
    sleep_log = sleeps if sleeps is not None else []

    def _fake_sleep(secs: float) -> None:
        sleep_log.append(secs)
        clk.advance(secs)

    async def _fake_async_sleep(secs: float) -> None:
        sleep_log.append(secs)
        clk.advance(secs)

    cfg = config or KeyPoolConfig(
        base_cooldown_seconds=10.0,
        max_cooldown_seconds=120.0,
        quota_cooldown_seconds=600.0,
        transient_cooldown_seconds=20.0,
        transient_failure_threshold=2,
        retry_base_delay_seconds=0.5,
        retry_max_delay_seconds=4.0,
        max_transient_retries_per_key=2,
        max_wait_for_recovery_seconds=3.0,
        jitter_ratio=0.0,
        max_concurrent_requests=4,
        enable_redis_sync=False,
    )
    mgr = GeminiKeyManager(
        api_keys=FAKE_KEYS if keys is None else keys,
        config=cfg,
        project_ids=project_ids,
        clock_fn=clk,
        rng_fn=lambda: 0.0,
    )
    transport = httpx.MockTransport(handler)
    sync_http = httpx.Client(transport=transport)
    async_http = httpx.AsyncClient(transport=transport)
    client = GeminiClient(
        key_manager=mgr,
        models=models or ["gemini-2.5-flash", "gemini-2.5-flash-lite"],
        sync_client=sync_http,
        async_client=async_http,
        sleep_fn=_fake_sleep,
        async_sleep_fn=_fake_async_sleep,
    )
    return client, clk, sleep_log


# ---------------------------------------------------------------------------
# 1. Environment Key Loading & Primary-First Ordering
# ---------------------------------------------------------------------------

def test_load_keys_from_env_precedence_and_deduplication():
    env = {
        "GEMINI_API_KEY": FAKE_KEYS[0],
        "GEMINI_API_KEYS": f"your_gemini_api_keys, {FAKE_KEYS[1]}, {FAKE_KEYS[0]}",
        "GEMINI_API_KEY_2": FAKE_KEYS[2],
        "GEMINI_API_KEY_1": FAKE_KEYS[1],
        "GEMINI_API_KEY_PROJECTS": "proj-alpha, proj-beta, proj-gamma",
    }
    keys, projects = load_gemini_api_keys_from_env(env)
    assert keys == FAKE_KEYS
    assert projects == ["proj-alpha", "proj-beta", "proj-gamma"]


def test_primary_key_used_by_default_without_unnecessary_rotation():
    used_keys: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        # API key must ONLY be sent in header, never in URL query string
        assert "key=" not in str(request.url)
        used_keys.append(request.headers["x-goog-api-key"])
        return _ok_gemini_json('{"answer": "ok"}')

    client, _, _ = _make_client(handler)
    for _ in range(5):
        resp = client.generate_content("Hello")
        assert resp.text == '{"answer": "ok"}'
        assert resp.rotations == 0

    assert used_keys == [FAKE_KEYS[0]] * 5
    status = client.get_status()
    assert status["health"] == "healthy"
    assert status["primary_key_available"] is True
    assert status["totals"]["rotations"] == 0
    assert status["totals"]["successes"] == 5


# ---------------------------------------------------------------------------
# 2. Error Classification & Failover Scenarios
# ---------------------------------------------------------------------------

def test_failover_on_http_429_respects_retry_after_and_exponential_backoff():
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        calls.append(key)
        if key == FAKE_KEYS[0]:
            return _error_response(
                429,
                status_str="RESOURCE_EXHAUSTED",
                message="Rate limit exceeded for requests per minute",
                details=[{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "25s"}],
                headers={"Retry-After": "18"},
            )
        return _ok_gemini_json('{"ok": "from_backup"}')

    client, clk, _ = _make_client(handler)

    # First request: key#1 returns 429 -> rotates to key#2 seamlessly
    resp1 = client.generate_content("Test prompt")
    assert resp1.text == '{"ok": "from_backup"}'
    assert resp1.rotations == 1
    assert calls == [FAKE_KEYS[0], FAKE_KEYS[1]]

    # key#1 must be in cooldown for at least max(base=10s, Retry-After=18s, RetryInfo=25s) == 25s
    snap = client.get_status()
    assert snap["health"] == "failover_active"
    assert snap["keys"][0]["status"] == KeyStatus.COOLDOWN.value
    assert 24.0 <= snap["keys"][0]["cooldown_remaining_seconds"] <= 26.0
    assert snap["keys"][1]["status"] == KeyStatus.AVAILABLE.value

    # Subsequent request while key#1 is cooled down goes directly to key#2 without touching key#1
    resp2 = client.generate_content("Second prompt")
    assert resp2.text == '{"ok": "from_backup"}'
    assert calls == [FAKE_KEYS[0], FAKE_KEYS[1], FAKE_KEYS[1]]

    # Advance clock past 25s -> key#1 automatically recovers and is tried first again!
    clk.advance(26.0)
    resp3 = client.generate_content("Third prompt")
    assert resp3.text == '{"ok": "from_backup"}'
    # key#1 tried again -> 429 again -> consecutive_rate_limits=2 -> exp backoff 10 * 2^1 = 20s, server RetryInfo=25s -> 25s
    assert calls[-2:] == [FAKE_KEYS[0], FAKE_KEYS[1]]
    assert client.get_status()["keys"][0]["consecutive_rate_limits"] == 2


def test_exponential_backoff_doubles_cooldown_on_repeated_429_and_resets_on_success():
    fail_primary = True

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        if key == FAKE_KEYS[0] and fail_primary:
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="Too many requests")
        return _ok_gemini_json('{"ok": true}')

    client, clk, _ = _make_client(handler)

    # 1st 429: cooldown = 10s
    client.generate_content("req1")
    assert client.get_status()["keys"][0]["cooldown_remaining_seconds"] == pytest.approx(10.0, abs=0.2)

    # Recover & hit 2nd 429: cooldown = 20s
    clk.advance(11.0)
    client.generate_content("req2")
    assert client.get_status()["keys"][0]["cooldown_remaining_seconds"] == pytest.approx(20.0, abs=0.2)

    # Recover & hit 3rd 429: cooldown = 40s
    clk.advance(21.0)
    client.generate_content("req3")
    assert client.get_status()["keys"][0]["cooldown_remaining_seconds"] == pytest.approx(40.0, abs=0.2)

    # Recover & succeed on primary -> consecutive streak resets to 0
    clk.advance(41.0)
    fail_primary = False
    resp = client.generate_content("req4")
    assert "key#1" in resp.key_label
    assert client.get_status()["keys"][0]["consecutive_rate_limits"] == 0
    assert client.get_status()["primary_key_available"] is True


def test_quota_exhaustion_applies_longer_quota_cooldown_and_rotates():
    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        if key == FAKE_KEYS[0]:
            return _error_response(
                429,
                status_str="RESOURCE_EXHAUSTED",
                message="You exceeded your current quota for GenerateRequestsPerDay.",
                details=[
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [{"quotaMetric": "generativelanguage.googleapis.com/generate_requests_per_day"}],
                    }
                ],
            )
        return _ok_gemini_json('{"ok": "key2"}')

    client, _, _ = _make_client(handler)
    resp = client.generate_content("quota test")
    assert resp.text == '{"ok": "key2"}'
    snap = client.get_status()
    assert snap["keys"][0]["status"] == KeyStatus.COOLDOWN.value
    assert snap["keys"][0]["cooldown_remaining_seconds"] == pytest.approx(600.0, abs=1.0)
    assert snap["keys"][0]["quota_exhaustion_count"] == 1
    assert snap["totals"]["quota_exhaustions"] == 1


def test_invalid_api_key_permanently_disabled_and_immediate_failover():
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        calls.append(key)
        if key == FAKE_KEYS[0]:
            return _error_response(
                400,
                status_str="INVALID_ARGUMENT",
                message="API key not valid. Please pass a valid API key.",
                details=[{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "API_KEY_INVALID"}],
            )
        if key == FAKE_KEYS[1]:
            return _error_response(401, status_str="UNAUTHENTICATED", message="Invalid credentials")
        return _ok_gemini_json('{"ok": "key3"}')

    client, clk, _ = _make_client(handler)
    resp = client.generate_content("auth test")
    assert resp.text == '{"ok": "key3"}'
    assert calls == [FAKE_KEYS[0], FAKE_KEYS[1], FAKE_KEYS[2]]

    # Even after advancing time dramatically, INVALID keys are never retried
    clk.advance(10_000.0)
    resp2 = client.generate_content("auth test 2")
    assert resp2.text == '{"ok": "key3"}'
    assert calls == [FAKE_KEYS[0], FAKE_KEYS[1], FAKE_KEYS[2], FAKE_KEYS[2]]

    snap = client.get_status()
    assert snap["invalid_keys"] == 2
    assert snap["available_keys"] == 1
    assert snap["keys"][0]["status"] == KeyStatus.INVALID.value
    assert snap["keys"][1]["status"] == KeyStatus.INVALID.value
    assert snap["keys"][2]["status"] == KeyStatus.AVAILABLE.value


def test_temporary_5xx_retries_with_backoff_then_recovers_or_fails_over():
    attempts_by_key: Dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        attempts_by_key[key] = attempts_by_key.get(key, 0) + 1
        # Key#1 fails 503 twice, succeeds on 3rd attempt (2nd retry)
        if key == FAKE_KEYS[0] and attempts_by_key[key] <= 2:
            return _error_response(503, status_str="UNAVAILABLE", message="Service temporarily overloaded")
        return _ok_gemini_json('{"ok": "recovered_after_retry"}')

    client, _, sleeps = _make_client(handler)
    resp = client.generate_content("transient recovery")
    assert resp.text == '{"ok": "recovered_after_retry"}'
    assert "key#1" in resp.key_label
    assert resp.attempts == 3
    assert resp.rotations == 0
    # Backoff delays: 0.5s then 1.0s
    assert sleeps == [0.5, 1.0]

    # Now test persistent timeout on key#1 -> fails over to key#2
    attempts_by_key.clear()

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        attempts_by_key[key] = attempts_by_key.get(key, 0) + 1
        if key == FAKE_KEYS[0]:
            raise httpx.ReadTimeout("Simulated read timeout")
        return _ok_gemini_json('{"ok": "backup_after_timeout"}')

    client2, _, _ = _make_client(timeout_handler)
    resp2 = client2.generate_content("timeout failover")
    assert resp2.text == '{"ok": "backup_after_timeout"}'
    assert "key#2" in resp2.key_label
    assert attempts_by_key[FAKE_KEYS[0]] == 3  # 1 initial + 2 transient retries
    assert attempts_by_key[FAKE_KEYS[1]] == 1


def test_non_retryable_bad_request_does_not_rotate_or_penalize_key():
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers["x-goog-api-key"])
        return _error_response(400, status_str="INVALID_ARGUMENT", message="Prompt exceeds maximum context size")

    client, _, _ = _make_client(handler)
    with pytest.raises(GeminiBadRequestError):
        client.generate_content("oversized payload")

    assert calls == [FAKE_KEYS[0]]
    snap = client.get_status()
    assert snap["keys"][0]["status"] == KeyStatus.AVAILABLE.value
    assert snap["keys"][0]["in_flight"] == 0
    assert snap["totals"]["rotations"] == 0


def test_model_unavailable_falls_back_to_secondary_model():
    requested_urls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if "gemini-2.5-flash:" in str(request.url):
            return _error_response(404, status_str="NOT_FOUND", message="Model gemini-2.5-flash is not found")
        return _ok_gemini_json('{"ok": "lite_model"}')

    client, _, _ = _make_client(handler, models=["gemini-2.5-flash", "gemini-2.5-flash-lite"])
    resp = client.generate_content("model fallback test")
    assert resp.model == "gemini-2.5-flash-lite"
    assert resp.text == '{"ok": "lite_model"}'
    assert len(requested_urls) == 2
    assert client.get_status()["keys"][0]["status"] == KeyStatus.AVAILABLE.value


# ---------------------------------------------------------------------------
# 3. Project-Level Quota Respect (Anti-Circumvention)
# ---------------------------------------------------------------------------

def test_project_level_quota_cooldown_skips_same_project_keys_and_fails_over_to_other_project():
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        calls.append(key)
        if key == FAKE_KEYS[0]:
            return _error_response(
                429,
                status_str="RESOURCE_EXHAUSTED",
                message="Quota exceeded for projects/111111111",
                details=[
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": "RATE_LIMIT_EXCEEDED",
                        "metadata": {"consumer": "projects/111111111"},
                    }
                ],
            )
        return _ok_gemini_json('{"ok": "distinct_project"}')

    # key#1 and key#2 share the same GCP project; key#3 is on a separate project
    client, _, _ = _make_client(
        handler,
        project_ids=["projects/111111111", "projects/111111111", "projects/222222222"],
    )
    resp = client.generate_content("project quota test")
    assert resp.text == '{"ok": "distinct_project"}'
    # Key#2 MUST be skipped because it shares projects/111111111; jumps straight to key#3!
    assert calls == [FAKE_KEYS[0], FAKE_KEYS[2]]
    snap = client.get_status()
    assert snap["keys"][0]["status"] == KeyStatus.COOLDOWN.value
    assert snap["keys"][1]["status"] == KeyStatus.COOLDOWN.value
    assert snap["keys"][2]["status"] == KeyStatus.AVAILABLE.value


# ---------------------------------------------------------------------------
# 4. All Keys Exhausted & Graceful End-to-End Fallback
# ---------------------------------------------------------------------------

def test_all_keys_exhausted_raises_cleanly_and_falls_back_to_nlp():
    def handler(request: httpx.Request) -> httpx.Response:
        return _error_response(
            429,
            status_str="RESOURCE_EXHAUSTED",
            message="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )

    client, _, _ = _make_client(handler)
    with pytest.raises(GeminiAllKeysExhaustedError) as exc_info:
        client.generate_content("all exhausted")
    assert exc_info.value.next_recovery_in_seconds is not None
    assert exc_info.value.next_recovery_in_seconds >= 59.0

    # Verify ai_analysis_service & job_matching_service fall back gracefully to NLP
    prev_client = reload_gemini_client(client)
    try:
        resume_data = {
            "fullname": "Maria Santos",
            "skills": "Python, FastAPI, PostgreSQL",
            "experience": "Senior Backend Developer at Acme Corp (3 years)",
            "years_experience": 3,
            "highest_degree": "Bachelor of Science in Computer Science",
            "location": "Makati, Metro Manila",
        }
        job_data = {
            "job_title": "Backend Engineer",
            "description": "Build FastAPI and PostgreSQL APIs in Python.",
            "skills_requirements": "Python, FastAPI, PostgreSQL",
            "experience_requirements": "2 years",
            "education_requirements": "Bachelor's Degree",
        }

        with patch.dict("os.environ", {"GEMINI_ENABLED": "true"}):
            match_res = ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)
            assert match_res is not None
            assert match_res["model_used"] == "nlp"
            assert match_res["ai_powered"] is False
            assert match_res["fallback_used"] is True
            assert match_res["ai_match_score"] > 0

            comp_res = ai_analysis_service.compare_candidates_with_fallback(
                job_data,
                [
                    {"candidate_name": "Maria Santos", **resume_data},
                    {"candidate_name": "Juan Cruz", "skills": "Excel", "years_experience": 1},
                ],
            )
            assert comp_res is not None
            assert comp_res["model_used"] == "nlp"
            assert comp_res["ai_powered"] is False
            assert len(comp_res["ranked_candidates"]) == 2

            job_obj = JobDescription(
                job_id="JOB-FB-01",
                job_title="Backend Engineer",
                department="Engineering",
                job_type=JobType.FULL_TIME,
                location="Remote",
                description=job_data["description"],
                skills_requirements=job_data["skills_requirements"],
                experience_requirements="2 years",
                education_requirements="Bachelor's Degree",
            )
            scored = job_matching_service.calculate_match_score(resume_data, job_obj, use_ai=True, log_prediction=False)
            assert scored["ai_powered"] is False
            assert scored["model_used"] == "nlp"
            assert scored["match_percentage"] > 0
    finally:
        reload_gemini_client(prev_client)


def test_short_recovery_cooldown_waits_and_recovers_transparently():
    attempt_num = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_num
        attempt_num += 1
        if attempt_num == 1:
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="Brief burst", headers={"Retry-After": "1"})
        return _ok_gemini_json('{"ok": "recovered_after_wait"}')

    cfg = KeyPoolConfig(
        base_cooldown_seconds=1.0,
        max_cooldown_seconds=10.0,
        max_wait_for_recovery_seconds=3.0,
        jitter_ratio=0.0,
        enable_redis_sync=False,
    )
    client, _, sleeps = _make_client(handler, keys=[FAKE_KEYS[0]], config=cfg)
    resp = client.generate_content("brief wait recovery")
    assert resp.text == '{"ok": "recovered_after_wait"}'
    assert any(s >= 0.9 for s in sleeps)


# ---------------------------------------------------------------------------
# 5. Thread Safety & Concurrency (Sync Threads + Async Gather)
# ---------------------------------------------------------------------------

def test_concurrent_multithreaded_requests_with_failover_are_thread_safe():
    counter_lock = threading.Lock()
    key1_hits = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal key1_hits
        key = request.headers["x-goog-api-key"]
        if key == FAKE_KEYS[0]:
            with counter_lock:
                key1_hits += 1
                hit = key1_hits
            if hit >= 3:
                return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="Rate limited")
            return _ok_gemini_json('{"served_by": "key1"}')
        if key == FAKE_KEYS[1]:
            return _error_response(401, status_str="UNAUTHENTICATED", message="Revoked backup key")
        return _ok_gemini_json('{"served_by": "key3"}')

    client, _, _ = _make_client(handler)

    def worker(idx: int) -> str:
        resp = client.generate_content(f"concurrent request {idx}", operation_name="concurrency_test")
        return resp.text

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(worker, range(24)))

    assert len(results) == 24
    assert all(r in ('{"served_by": "key1"}', '{"served_by": "key3"}') for r in results)

    snap = client.get_status()
    # Zero leaked in-flight counters across all keys
    assert all(k["in_flight"] == 0 for k in snap["keys"])
    assert snap["totals"]["successes"] == 24
    assert snap["totals"]["requests"] == snap["totals"]["successes"] + snap["totals"]["failures"]
    assert snap["keys"][1]["status"] == KeyStatus.INVALID.value
    assert snap["keys"][2]["success_count"] > 0


@pytest.mark.asyncio
async def test_concurrent_async_requests_with_failover():
    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        if key == FAKE_KEYS[0]:
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="Async rate limit")
        return _ok_gemini_json('{"async_ok": true}')

    client, _, _ = _make_client(handler)
    tasks = [client.agenerate_content(f"async prompt {i}") for i in range(15)]
    responses = await asyncio.gather(*tasks)

    assert len(responses) == 15
    assert all(r.text == '{"async_ok": true}' for r in responses)
    snap = client.get_status()
    assert all(k["in_flight"] == 0 for k in snap["keys"])
    assert snap["totals"]["successes"] == 15
    await client.aclose()


# ---------------------------------------------------------------------------
# 6. Secret Redaction & Logging Safety
# ---------------------------------------------------------------------------

def test_raw_api_keys_never_leak_in_logs_exceptions_or_status(caplog):
    leaked_secret = FAKE_KEYS[0]
    ai_studio_secret = "AIzaSyFAKE_SUPER_SECRET_KEY_VALUE_123456789"

    def handler(request: httpx.Request) -> httpx.Response:
        return _error_response(
            401,
            status_str="UNAUTHENTICATED",
            message=f"Rejected credential {leaked_secret} and ?key={ai_studio_secret}",
        )

    client, _, _ = _make_client(handler, keys=[leaked_secret, ai_studio_secret])

    # Lease repr must never reveal raw key
    lease = client.key_manager.acquire_key()
    assert lease is not None
    assert leaked_secret not in repr(lease)
    client.key_manager.release_unused_lease(lease)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(GeminiAllKeysExhaustedError) as exc_info:
            client.generate_content("secret redaction test")

    err_text = str(exc_info.value)
    assert leaked_secret not in err_text
    assert ai_studio_secret not in err_text

    # Check status snapshot JSON contains zero raw keys
    snap_json = json.dumps(client.get_status())
    assert leaked_secret not in snap_json
    assert ai_studio_secret not in snap_json

    # Check all emitted log records contain zero raw keys
    full_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert leaked_secret not in full_logs
    assert ai_studio_secret not in full_logs

    # Direct sanitizer check
    sanitized = sanitize_error_message(
        f"GET https://example.com?key={ai_studio_secret} header x-goog-api-key: {leaked_secret}",
        [leaked_secret, ai_studio_secret],
    )
    assert leaked_secret not in sanitized
    assert ai_studio_secret not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


# ---------------------------------------------------------------------------
# 7. End-to-End Blended Match Analysis & Admin Status Endpoint
# ---------------------------------------------------------------------------

def test_end_to_end_gemini_blended_scoring_with_mocked_transport():
    gemini_payload = json.dumps(
        {
            "ai_match_score": 90,
            "match_level": "High Match",
            "skills_score": 92,
            "skills_explanation": "Strong alignment with Python, FastAPI, and PostgreSQL.",
            "experience_score": 88,
            "experience_explanation": "Directly relevant backend engineering roles.",
            "relevance_level": "Highly Relevant",
            "transferable_skills": ["API Design", "Testing"],
            "education_score": 95,
            "education_explanation": "BS Computer Science meets the degree requirement.",
            "certifications_score": 100,
            "certification_explanation": "No mandatory certifications required.",
            "strengths": ["Strong Python & FastAPI background", "3 years relevant backend work"],
            "weaknesses": ["No Kubernetes experience listed"],
            "ai_summary": "Candidate is a strong technical match for the Backend Engineer opening.",
            "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
            "missing_skills": ["Kubernetes"],
            "recommendations": ["Probe distributed systems scaling experience in technical interview."],
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["x-goog-api-key"] == FAKE_KEYS[0]:
            # Simulate primary key rate-limit failover to secondary key
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="RPM limit hit")
        return _ok_gemini_json(gemini_payload)

    client, _, _ = _make_client(handler)
    prev_client = reload_gemini_client(client)
    try:
        resume_data = {
            "fullname": "Elena Reyes",
            "skills": "Python, FastAPI, PostgreSQL",
            "experience": "Backend Software Engineer at TechCorp - Built FastAPI REST services and PostgreSQL databases",
            "years_experience": 3,
            "highest_degree": "Bachelor of Science in Computer Science",
            "education": "Bachelor of Science in Computer Science",
        }
        job_data = {
            "job_title": "Backend Engineer",
            "department": "Engineering",
            "description": "Develop Python FastAPI APIs and PostgreSQL data pipelines.",
            "skills_requirements": "Python, FastAPI, PostgreSQL",
            "experience_requirements": "2 years",
            "education_requirements": "Bachelor's Degree",
            "certifications_requirements": "None",
        }

        with patch.dict("os.environ", {"GEMINI_ENABLED": "true"}):
            res = ai_analysis_service.analyze_match_with_fallback(resume_data, job_data)
            assert res is not None
            assert res["model_used"] == "gemini"
            assert res["ai_powered"] is True
            assert res["fallback_used"] is False
            assert res["gemini_model"] == "gemini-2.5-flash"
            assert res["ai_match_score"] >= 80.0
            assert "strong technical match" in res["ai_summary"].lower()
            # Deterministic structural fields must still be preserved
            assert "completeness_score" in res
            assert "applied_weights" in res
            assert "requirement_evaluations" in res

            # Direct calculate_match_score(..., use_ai=True) should also work
            scored = job_matching_service.calculate_match_score(resume_data, job_data, use_ai=True, log_prediction=False)
            assert scored["ai_powered"] is True
            assert scored["model_used"] == "gemini"
            assert scored["match_percentage"] >= 80.0
    finally:
        reload_gemini_client(prev_client)


@pytest.mark.asyncio
async def test_admin_gemini_status_endpoint_requires_admin_and_hides_secrets(client):
    mock_client, _, _ = _make_client(lambda req: _ok_gemini_json())
    prev_client = reload_gemini_client(mock_client)
    try:
        # Unauthenticated rejected
        unauth = await client.get("/system-config/gemini/status")
        assert unauth.status_code in (401, 403)

        # Non-admin (HR) rejected
        hr_token = create_access_token({"sub": "hr@test.com", "role": "HR", "id": 10})
        hr_res = await client.get(
            "/system-config/gemini/status",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert hr_res.status_code == 403

        # Admin allowed & receives safe metrics with zero raw keys
        admin_token = create_access_token({"sub": "admin@test.com", "role": "ADMIN", "id": 1})
        admin_res = await client.get(
            "/system-config/gemini/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_res.status_code == 200
        body = admin_res.json()
        assert body["configured"] is True
        assert body["total_keys"] == 3
        assert body["available_keys"] == 3
        assert body["primary_key_available"] is True
        assert body["health"] == "healthy"

        raw_text = json.dumps(body)
        for secret in FAKE_KEYS:
            assert secret not in raw_text
    finally:
        reload_gemini_client(prev_client)


def test_unconfigured_client_raises_configuration_error():
    client, _, _ = _make_client(lambda req: _ok_gemini_json(), keys=[])
    assert client.is_available is False
    assert client.get_status()["health"] == "unconfigured"
    with pytest.raises(GeminiConfigurationError):
        client.generate_content("hello")


def test_http_error_classifier_covers_all_required_error_categories():
    assert isinstance(classify_http_error(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "RPM limit"}}), GeminiRateLimitError)
    assert isinstance(
        classify_http_error(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "GenerateRequestsPerDay exceeded"}}),
        GeminiQuotaExhaustedError,
    )
    assert isinstance(
        classify_http_error(400, {"error": {"message": "API key not valid", "details": [{"reason": "API_KEY_INVALID"}]}}),
        GeminiAuthError,
    )
    assert isinstance(classify_http_error(401, {"error": {"message": "Unauthenticated"}}), GeminiAuthError)
    assert isinstance(classify_http_error(403, {"error": {"message": "API_KEY_SERVICE_BLOCKED"}}), GeminiAuthError)
    assert isinstance(classify_http_error(404, {"error": {"message": "Model not found"}}), GeminiModelUnavailableError)
    assert isinstance(classify_http_error(500, {"error": {"message": "Internal error"}}), GeminiTransientError)
    assert isinstance(classify_http_error(503, {"error": {"message": "Service unavailable"}}), GeminiTransientError)
    assert isinstance(classify_http_error(400, {"error": {"message": "Invalid JSON schema"}}), GeminiBadRequestError)
    assert isinstance(
        classify_http_error(403, {"error": {"message": "Your project has exceeded its spending cap"}}),
        GeminiQuotaExhaustedError,
    )


def test_multiline_quoted_spaces_and_escaped_newlines_in_gemini_api_keys():
    five_keys = [
        "AQ.TestAccountKey000000000000000000000000000000001",
        "AQ.TestAccountKey000000000000000000000000000000002",
        "AQ.TestAccountKey000000000000000000000000000000003",
        "AQ.TestAccountKey000000000000000000000000000000004",
        "AQ.TestAccountKey000000000000000000000000000000005",
    ]
    # Simulate multiline quoted .env string with trailing newline, spaces, quotes, and trailing comma
    messy_raw = f'"{five_keys[0]}, {five_keys[1]},  "{five_keys[2]}" , {five_keys[3]}, {five_keys[4]}\\n,\n"'
    loaded, _ = load_gemini_api_keys_from_env({"GEMINI_API_KEYS": messy_raw})
    assert loaded == five_keys
    assert all(not any(ch.isspace() for ch in k) and '"' not in k and "'" not in k for k in loaded)


def test_five_account_keys_rotate_all_the_way_to_fifth_key_on_limits():
    five_keys = [f"AQ.AccountKeyPool00000000000000000000000000000000{i}" for i in range(1, 6)]
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        calls.append(key)
        if key == five_keys[0]:
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="RPM limit exceeded")
        if key == five_keys[1]:
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="GenerateRequestsPerDay exceeded")
        if key == five_keys[2]:
            return _error_response(403, status_str="PERMISSION_DENIED", message="Account spending cap reached")
        if key == five_keys[3]:
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="Resource has been exhausted")
        return _ok_gemini_json('{"served_by": "account_5"}')

    client, _, _ = _make_client(handler, keys=five_keys)
    resp = client.generate_content("cascade through 5 accounts")
    assert resp.text == '{"served_by": "account_5"}'
    assert "key#5" in resp.key_label
    assert calls == five_keys

    # Next request goes straight to key#5 without re-hitting exhausted keys #1..#4
    resp2 = client.generate_content("second request stays on healthy key#5")
    assert resp2.text == '{"served_by": "account_5"}'
    assert calls == five_keys + [five_keys[4]]


def test_hot_reload_newly_inserted_key_in_env_file_preserves_existing_cooldowns(tmp_path):
    env_file = tmp_path / ".env"
    key1 = "AQ.InitialKeyOne0000000000000000000000000000000001"
    key2 = "AQ.InitialKeyTwo0000000000000000000000000000000002"
    key3 = "AQ.NewlyInserted0000000000000000000000000000000003"
    env_file.write_text(f'GEMINI_API_KEYS="{key1}, {key2}\n"\n', encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        if key in (key1, key2):
            return _error_response(429, status_str="RESOURCE_EXHAUSTED", message="Daily quota exceeded")
        return _ok_gemini_json('{"served_by": "new_key_3"}')

    client, _, _ = _make_client(handler, keys=[key1, key2])
    client._env_file_path = str(env_file)
    client._env_last_mtime = env_file.stat().st_mtime - 10.0  # ensure next check detects update
    client._env_reload_interval_seconds = 0.0

    # First, key1 & key2 are both exhausted
    client._env_last_mtime = env_file.stat().st_mtime
    with pytest.raises(GeminiAllKeysExhaustedError):
        client.generate_content("before inserting key3")
    assert client.get_status()["cooldown_keys"] == 2

    # User edits .env and inserts key3 (with multiline closing quote!)
    env_file.write_text(f'GEMINI_API_KEYS="{key1}, {key2}, {key3}\n"\n', encoding="utf-8")
    # Bump mtime explicitly so fast filesystems always register a change
    import os
    new_mtime = env_file.stat().st_mtime + 5.0
    os.utime(env_file, (new_mtime, new_mtime))

    # Next request automatically hot-syncs key3 while keeping key1 & key2 in cooldown!
    resp = client.generate_content("after inserting key3")
    assert resp.text == '{"served_by": "new_key_3"}'
    assert "key#3" in resp.key_label
    snap = client.get_status()
    assert snap["total_keys"] == 3
    assert snap["cooldown_keys"] == 2
    assert snap["available_keys"] == 1
    assert key3 not in json.dumps(snap)


def test_error_info_api_key_consumer_never_stored_as_project_id():
    secret = FAKE_KEYS[0]
    err = classify_http_error(
        429,
        {
            "error": {
                "status": "RESOURCE_EXHAUSTED",
                "message": f"Quota exceeded for api_key:{secret}",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": "RATE_LIMIT_EXCEEDED",
                        "metadata": {"consumer": f"api_key:{secret}"},
                    }
                ],
            }
        },
        known_secrets=[secret],
    )
    assert isinstance(err, GeminiRateLimitError)
    assert err.project_id is None
    assert secret not in str(err)

