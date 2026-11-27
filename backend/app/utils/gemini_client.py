"""
Thread-Safe Gemini API Client
-----------------------------
Domain-agnostic HTTP client for Google's Gemini REST API (`generativelanguage.googleapis.com`),
built on `httpx` with zero global mutable SDK state.

Key capabilities:
- Passes API keys strictly in the `x-goog-api-key` HTTP header (never in query URLs or logs).
- Full synchronous (`generate_content`) and asynchronous (`agenerate_content`) interfaces.
- Automatic primary-first key failover, exponential backoff, cooldown management, and
  project-level quota awareness via `GeminiKeyManager`.
- Structured classification of HTTP 429 rate limits, daily/hard quota exhaustion, invalid
  credentials (400/401/403), model unavailability (404), transient failures (5xx/timeouts),
  and non-retryable client errors (400/422).
- Safe sanitization of all logged and raised error messages to prevent credential exposure.
"""

from __future__ import annotations

import asyncio
import email.utils
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Set, Tuple

import httpx
from dotenv import dotenv_values, find_dotenv, load_dotenv

from app.utils.gemini_key_manager import (
    GeminiKeyManager,
    KeyPoolConfig,
    load_gemini_api_keys_from_env,
    sanitize_error_message,
)

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite")

_PROJECT_NUM_RE = re.compile(r"\bprojects/(\d{6,})\b")
_PROJECT_SLUG_RE = re.compile(r"^projects/([a-z][a-z0-9\-]{4,30})$")
_RETRY_DELAY_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ms|s|m|h)?\s*$", re.IGNORECASE)

_QUOTA_EXHAUSTED_MARKERS = (
    "perday",
    "per_day",
    "daily",
    "daily limit",
    "monthly limit",
    "requestsperday",
    "tokensperday",
    "free_tier_requests",
    "free tier",
    "limit: 0",
    "quota exceeded for quota metric",
    "spending",
    "spending cap",
    "billing",
    "exceeded your current quota",
)

_PER_MINUTE_MARKERS = (
    "per minute",
    "perminute",
    "per_minute",
    "requests per minute",
    "tokens per minute",
)

_INVALID_KEY_REASONS = {
    "API_KEY_INVALID",
    "API_KEY_EXPIRED",
    "API_KEY_SERVICE_BLOCKED",
    "API_KEY_HTTP_REFERRER_BLOCKED",
    "API_KEY_IP_ADDRESS_BLOCKED",
    "API_KEY_ANDROID_APP_BLOCKED",
    "API_KEY_IOS_APP_BLOCKED",
    "AUTH_ERROR",
}

_INVALID_KEY_MESSAGE_MARKERS = (
    "api key not valid",
    "api_key_invalid",
    "invalid api key",
    "api key expired",
    "api key has expired",
    "unregistered callers",
    "consumer 'api_key:",
    "permission denied",
    "has not been used in project",
    "is disabled",
)

_MODEL_UNAVAILABLE_MARKERS = (
    "is not found",
    "not supported for generatecontent",
    "model not found",
    "invalid model",
    "deprecated",
    "no longer available",
)


# ---------------------------------------------------------------------------
# Typed Error Hierarchy (all messages are automatically sanitized)
# ---------------------------------------------------------------------------

class GeminiError(Exception):
    """Base error raised by GeminiClient. Never includes raw API credentials."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        known_secrets: Optional[Sequence[str]] = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        clean_msg = sanitize_error_message(message, known_secrets)
        super().__init__(clean_msg)


class GeminiConfigurationError(GeminiError):
    """Raised when Gemini integration is disabled or no API keys are configured."""


class GeminiAuthError(GeminiError):
    """Raised when an API key is invalid, expired, revoked, or unauthorized."""


class GeminiRateLimitError(GeminiError):
    """Raised on HTTP 429 or transient RPM/TPM throttling."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = 429,
        error_code: Optional[str] = "RESOURCE_EXHAUSTED",
        retry_after: Optional[float] = None,
        project_id: Optional[str] = None,
        is_quota_exhausted: bool = False,
        known_secrets: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            known_secrets=known_secrets,
        )
        self.retry_after = retry_after
        self.project_id = project_id
        self.is_quota_exhausted = is_quota_exhausted


class GeminiQuotaExhaustedError(GeminiRateLimitError):
    """Raised when daily or hard quota limits are exhausted for a key or project."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = 429,
        error_code: Optional[str] = "QUOTA_EXHAUSTED",
        retry_after: Optional[float] = None,
        project_id: Optional[str] = None,
        known_secrets: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            retry_after=retry_after,
            project_id=project_id,
            is_quota_exhausted=True,
            known_secrets=known_secrets,
        )


class GeminiTransientError(GeminiError):
    """Raised on temporary upstream 5xx responses, timeouts, or network transport failures."""


class GeminiModelUnavailableError(GeminiError):
    """Raised when a configured Gemini model is missing or unsupported."""


class GeminiBadRequestError(GeminiError):
    """Raised on non-retryable 4xx payload errors (never triggers key rotation)."""


class GeminiAllKeysExhaustedError(GeminiError):
    """Raised when every configured Gemini API key is invalid, exhausted, or in cooldown."""

    def __init__(
        self,
        message: str,
        *,
        next_recovery_in_seconds: Optional[float] = None,
        last_error: Optional[Exception] = None,
        known_secrets: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(message, status_code=503, error_code="ALL_KEYS_EXHAUSTED", known_secrets=known_secrets)
        self.next_recovery_in_seconds = next_recovery_in_seconds
        self.last_error = last_error


# ---------------------------------------------------------------------------
# Response Dataclass & Parsing Helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GeminiResponse:
    text: str
    model: str
    key_label: str
    attempts: int
    rotations: int
    latency_ms: float
    finish_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)


def load_gemini_models_from_env(env: Optional[Dict[str, str]] = None) -> List[str]:
    """Load ordered list of candidate Gemini models from environment variables."""
    source = os.environ if env is None else env
    raw = source.get("GEMINI_MODELS") or source.get("GEMINI_MODEL") or ""
    models: List[str] = []
    for item in [m.strip() for m in raw.split(",") if m.strip()]:
        cleaned = item.removeprefix("models/")
        if cleaned and cleaned not in models:
            models.append(cleaned)
    return models or list(DEFAULT_GEMINI_MODELS)


def parse_retry_after_header(value: Optional[str]) -> Optional[float]:
    """Parse HTTP `Retry-After` header (integer/float seconds or RFC HTTP-date)."""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        secs = float(raw)
        return max(0.0, secs)
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = (dt - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, delta)
    except Exception:
        return None


def parse_google_retry_delay(value: Optional[str]) -> Optional[float]:
    """Parse protobuf duration strings such as `'23s'`, `'12.5s'`, `'500ms'`, `'2m'`."""
    if not value or not isinstance(value, str):
        return None
    match = _RETRY_DELAY_RE.match(value)
    if not match:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "s").lower()
    if unit == "ms":
        return max(0.0, amount / 1000.0)
    if unit == "m":
        return max(0.0, amount * 60.0)
    if unit == "h":
        return max(0.0, amount * 3600.0)
    return max(0.0, amount)


def _extract_safe_project_id(candidate: Optional[str]) -> Optional[str]:
    """
    Extract a real GCP project identifier (`projects/<number>` or valid project slug)
    while strictly rejecting raw API keys (`api_key:...`, `AQ.`, `AIza`) or doc URL words.
    """
    if not candidate or not isinstance(candidate, str):
        return None
    text = candidate.strip()
    if not text:
        return None
    lowered = text.lower()
    if "api_key" in lowered or "aiza" in lowered or "aq." in lowered:
        return None

    num_match = _PROJECT_NUM_RE.search(text)
    if num_match:
        return f"projects/{num_match.group(1)}"

    slug_match = _PROJECT_SLUG_RE.fullmatch(text)
    if slug_match and slug_match.group(1) not in {"overview", "billing", "quotas", "google"}:
        return f"projects/{slug_match.group(1)}"

    return None


def _extract_error_metadata(payload: Any) -> Tuple[str, str, Optional[str], Optional[float], Optional[str], List[str]]:
    """
    Extract structured Google API error metadata:
    (status_str, message, reason_code, retry_delay_seconds, project_id, quota_metrics)
    """
    if not isinstance(payload, dict):
        return "", str(payload or ""), None, None, None, []

    err = payload.get("error") if isinstance(payload.get("error"), dict) else payload
    status_str = str(err.get("status") or "").strip()
    message = str(err.get("message") or "").strip()
    reason_code: Optional[str] = None
    retry_delay: Optional[float] = None
    project_id: Optional[str] = None
    quota_metrics: List[str] = []

    details = err.get("details")
    if isinstance(details, list):
        for detail in details:
            if not isinstance(detail, dict):
                continue
            detail_type = str(detail.get("@type") or "")

            if "ErrorInfo" in detail_type or "reason" in detail:
                if detail.get("reason") and not reason_code:
                    reason_code = str(detail["reason"]).strip()
                meta = detail.get("metadata")
                if isinstance(meta, dict):
                    consumer = str(meta.get("consumer") or meta.get("project") or "").strip()
                    if consumer and not project_id:
                        project_id = _extract_safe_project_id(consumer)

            if "RetryInfo" in detail_type or "retryDelay" in detail:
                parsed = parse_google_retry_delay(detail.get("retryDelay"))
                if parsed is not None:
                    retry_delay = max(retry_delay or 0.0, parsed)

            if "QuotaFailure" in detail_type or "violations" in detail:
                violations = detail.get("violations")
                if isinstance(violations, list):
                    for violation in violations:
                        if not isinstance(violation, dict):
                            continue
                        for field_name in ("quotaMetric", "quotaId", "description", "subject"):
                            val = violation.get(field_name)
                            if val:
                                quota_metrics.append(str(val))
                                if not project_id:
                                    project_id = _extract_safe_project_id(str(val))

    if not project_id and message:
        project_id = _extract_safe_project_id(message)

    return status_str, message, reason_code, retry_delay, project_id, quota_metrics


def classify_http_error(
    status_code: int,
    response_body: Any,
    headers: Optional[Dict[str, str]] = None,
    known_secrets: Optional[Sequence[str]] = None,
) -> GeminiError:
    """Classify an HTTP error response from the Gemini API into a typed `GeminiError`."""
    status_str, message, reason_code, detail_retry, project_id, quota_metrics = _extract_error_metadata(response_body)
    hdrs = {k.lower(): v for k, v in (headers or {}).items()}
    header_retry = parse_retry_after_header(hdrs.get("retry-after"))
    retry_after = max(
        [val for val in (header_retry, detail_retry) if val is not None],
        default=None,
    )

    combined_lower = " ".join(
        part.lower() for part in [status_str, message, reason_code or "", *quota_metrics] if part
    )
    base_msg = message or status_str or f"Gemini API returned HTTP {status_code}"

    # 1. Invalid / unauthorized API key errors
    if (
        (reason_code and reason_code.upper() in _INVALID_KEY_REASONS)
        or status_code == 401
        or (status_code in (400, 403) and any(marker in combined_lower for marker in _INVALID_KEY_MESSAGE_MARKERS))
    ):
        return GeminiAuthError(
            f"Gemini API authentication failed (HTTP {status_code}): {base_msg}",
            status_code=status_code,
            error_code=reason_code or status_str or "AUTH_ERROR",
            known_secrets=known_secrets,
        )

    # 2. HTTP 429 or explicit quota exhaustion (also handle 403 quota/billing/spending cap errors)
    if status_code == 429 or status_str.upper() == "RESOURCE_EXHAUSTED" or (
        status_code == 403
        and any(
            marker in combined_lower
            for marker in ("quota", "resource_exhausted", "rate limit", "spending", "billing", "daily limit", "monthly limit")
        )
    ):
        has_hard_quota_marker = any(marker in combined_lower for marker in _QUOTA_EXHAUSTED_MARKERS)
        is_per_minute_only = any(marker in combined_lower for marker in _PER_MINUTE_MARKERS) and not any(
            hard in combined_lower for hard in ("perday", "per_day", "daily", "limit: 0", "spending", "billing")
        )
        is_quota = has_hard_quota_marker and not is_per_minute_only
        if is_quota:
            return GeminiQuotaExhaustedError(
                f"Gemini API quota exhausted (HTTP {status_code}): {base_msg}",
                status_code=status_code,
                error_code=reason_code or "QUOTA_EXHAUSTED",
                retry_after=retry_after,
                project_id=project_id,
                known_secrets=known_secrets,
            )
        return GeminiRateLimitError(
            f"Gemini API rate limited (HTTP {status_code}): {base_msg}",
            status_code=status_code,
            error_code=reason_code or "RATE_LIMITED",
            retry_after=retry_after,
            project_id=project_id,
            is_quota_exhausted=False,
            known_secrets=known_secrets,
        )

    # 3. Remaining 403 errors are permission/access failures for that key
    if status_code == 403:
        return GeminiAuthError(
            f"Gemini API access denied (HTTP 403): {base_msg}",
            status_code=403,
            error_code=reason_code or status_str or "PERMISSION_DENIED",
            known_secrets=known_secrets,
        )

    # 4. Missing or unsupported model (triggers model fallback)
    if status_code == 404 or (
        status_code == 400 and any(marker in combined_lower for marker in _MODEL_UNAVAILABLE_MARKERS)
    ):
        return GeminiModelUnavailableError(
            f"Gemini model unavailable (HTTP {status_code}): {base_msg}",
            status_code=status_code,
            error_code=reason_code or status_str or "MODEL_NOT_FOUND",
            known_secrets=known_secrets,
        )

    # 5. Temporary upstream server / gateway failures
    if status_code in (408, 500, 502, 503, 504):
        return GeminiTransientError(
            f"Gemini API temporary failure (HTTP {status_code}): {base_msg}",
            status_code=status_code,
            error_code=reason_code or status_str or f"HTTP_{status_code}",
            known_secrets=known_secrets,
        )

    # 6. Non-retryable client payload errors (do NOT rotate keys)
    return GeminiBadRequestError(
        f"Gemini API rejected request (HTTP {status_code}): {base_msg}",
        status_code=status_code,
        error_code=reason_code or status_str or f"HTTP_{status_code}",
        known_secrets=known_secrets,
    )


def extract_text_from_response_payload(payload: Dict[str, Any]) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    Extract generated text, finishReason, and usageMetadata from a Gemini generateContent JSON response.
    Skips internal `thought` parts emitted by Gemini 2.5 reasoning models when present.
    """
    usage = payload.get("usageMetadata") if isinstance(payload.get("usageMetadata"), dict) else {}
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        block_reason = None
        prompt_feedback = payload.get("promptFeedback")
        if isinstance(prompt_feedback, dict):
            block_reason = prompt_feedback.get("blockReason")
        return "", block_reason, usage

    first = candidates[0] if isinstance(candidates[0], dict) else {}
    finish_reason = first.get("finishReason")
    content = first.get("content") if isinstance(first.get("content"), dict) else {}
    parts = content.get("parts") if isinstance(content.get("parts"), list) else []

    text_chunks: List[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("thought") is True:
            continue
        text_val = part.get("text")
        if isinstance(text_val, str):
            text_chunks.append(text_val)

    return "".join(text_chunks).strip(), finish_reason, usage


# ---------------------------------------------------------------------------
# GeminiClient (Thread-Safe Sync & Async Client)
# ---------------------------------------------------------------------------

def _discover_env_file() -> Optional[str]:
    """Locate the project `.env` file for optional hot-reload of newly inserted API keys."""
    found = find_dotenv(usecwd=True)
    if found and os.path.isfile(found):
        return os.path.abspath(found)
    candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
    if os.path.isfile(candidate):
        return candidate
    return None


class GeminiClient:
    """
    Production Gemini REST API client with primary-first key failover,
    exponential backoff, cooldown management, and full thread/async concurrency safety.
    """

    def __init__(
        self,
        key_manager: GeminiKeyManager,
        *,
        models: Optional[Sequence[str]] = None,
        api_base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
        default_thinking_budget: Optional[int] = 0,
        sync_client: Optional[httpx.Client] = None,
        async_client: Optional[httpx.AsyncClient] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        async_sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
        env_file_path: Optional[str] = None,
        env_reload_interval_seconds: float = 2.0,
    ) -> None:
        self._key_manager = key_manager
        self._models = list(models) if models else load_gemini_models_from_env()
        self._api_base_url = (api_base_url or os.getenv("GEMINI_API_BASE_URL") or DEFAULT_GEMINI_API_BASE_URL).rstrip("/")
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._default_thinking_budget = default_thinking_budget
        self._sleep = sleep_fn
        self._async_sleep = async_sleep_fn
        self._env_file_path = env_file_path
        self._env_reload_interval_seconds = max(0.0, float(env_reload_interval_seconds))
        self._env_last_mtime: Optional[float] = None
        self._env_last_checked_at: float = 0.0
        self._env_reload_lock = threading.Lock()
        if self._env_file_path and os.path.isfile(self._env_file_path):
            try:
                self._env_last_mtime = os.path.getmtime(self._env_file_path)
            except OSError:
                self._env_last_mtime = None

        self._owns_sync_client = sync_client is None
        self._sync_client = sync_client or httpx.Client(
            timeout=httpx.Timeout(self._timeout_seconds),
            limits=httpx.Limits(
                max_connections=max(20, key_manager.config.max_concurrent_requests * 4),
                max_keepalive_connections=max(10, key_manager.config.max_concurrent_requests * 2),
            ),
        )

        self._async_client: Optional[httpx.AsyncClient] = async_client
        self._owns_async_client = async_client is None
        self._async_clients_by_loop: Dict[int, httpx.AsyncClient] = {}
        self._async_semaphores_by_loop: Dict[int, asyncio.Semaphore] = {}
        self._client_lock = threading.Lock()

    @classmethod
    def from_env(
        cls,
        env: Optional[Dict[str, str]] = None,
        env_file_path: Optional[str] = None,
    ) -> "GeminiClient":
        discovered_env_file = env_file_path
        if env is None and discovered_env_file is None:
            discovered_env_file = _discover_env_file()

        if env is None and discovered_env_file and os.path.isfile(discovered_env_file):
            file_vals = {k: (v or "") for k, v in dotenv_values(discovered_env_file).items() if v is not None}
            source = {**os.environ, **file_vals}
        else:
            source = os.environ if env is None else env

        key_manager = GeminiKeyManager.from_env(env=source)
        timeout = float(source.get("GEMINI_TIMEOUT_SECONDS") or 30.0)
        raw_budget = source.get("GEMINI_THINKING_BUDGET")
        thinking_budget: Optional[int] = 0
        if raw_budget is not None and str(raw_budget).strip() != "":
            if str(raw_budget).strip().lower() == "none":
                thinking_budget = None
            else:
                try:
                    thinking_budget = max(0, int(str(raw_budget).strip()))
                except ValueError:
                    thinking_budget = 0
        return cls(
            key_manager=key_manager,
            models=load_gemini_models_from_env(env=source),
            api_base_url=source.get("GEMINI_API_BASE_URL") or DEFAULT_GEMINI_API_BASE_URL,
            timeout_seconds=timeout,
            default_thinking_budget=thinking_budget,
            env_file_path=discovered_env_file if env is None else env_file_path,
        )

    def refresh_keys_if_env_changed(self, force: bool = False) -> bool:
        """
        Hot-sync newly inserted or edited Gemini API keys from `.env` whenever the file's
        modification time changes, preserving existing keys' cooldown/invalid states.
        Returns True if the key pool changed.
        """
        if not self._env_file_path:
            return False

        now = time.monotonic()
        with self._env_reload_lock:
            if not force and (now - self._env_last_checked_at) < self._env_reload_interval_seconds:
                return False
            self._env_last_checked_at = now

            try:
                mtime = os.path.getmtime(self._env_file_path)
            except OSError:
                return False

            if self._env_last_mtime is not None and mtime == self._env_last_mtime:
                return False

            try:
                file_vals = {
                    k: (v or "")
                    for k, v in dotenv_values(self._env_file_path).items()
                    if v is not None
                }
                merged_env = {**os.environ, **file_vals}
                new_keys, new_projects = load_gemini_api_keys_from_env(env=merged_env)
                summary = self._key_manager.sync_keys(new_keys, project_ids=new_projects)
                self._env_last_mtime = mtime
                return bool(summary.get("added") or summary.get("removed"))
            except Exception as exc:
                logger.warning("[GeminiClient] Failed hot-reloading keys from .env: %s", self._key_manager.sanitize(exc))
                return False

    @property
    def key_manager(self) -> GeminiKeyManager:
        return self._key_manager

    @property
    def models(self) -> List[str]:
        return list(self._models)

    @property
    def is_available(self) -> bool:
        return self._key_manager.is_configured

    def get_status(self) -> Dict[str, Any]:
        self.refresh_keys_if_env_changed()
        snapshot = self._key_manager.get_status_snapshot()
        snapshot["models"] = list(self._models)
        snapshot["api_base_url"] = self._api_base_url
        snapshot["timeout_seconds"] = self._timeout_seconds
        return snapshot

    def _endpoint_url(self, model_name: str) -> str:
        clean_model = model_name.strip().removeprefix("models/")
        return f"{self._api_base_url}/models/{clean_model}:generateContent"

    def _build_payload(
        self,
        *,
        prompt: str,
        model_name: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 4096,
        response_mime_type: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        include_thinking_config: bool = True,
    ) -> Dict[str, Any]:
        gen_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
        if response_mime_type:
            gen_config["responseMimeType"] = response_mime_type

        effective_budget = self._default_thinking_budget if thinking_budget is None else thinking_budget
        model_lower = model_name.lower()
        if (
            include_thinking_config
            and effective_budget is not None
            and ("2.5" in model_lower or "gemini-3" in model_lower)
        ):
            gen_config["thinkingConfig"] = {"thinkingBudget": int(effective_budget)}

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": gen_config,
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}],
            }
        return payload

    def _parse_response_or_raise(self, response: httpx.Response, model_name: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise classify_http_error(
                status_code=response.status_code,
                response_body=body,
                headers=dict(response.headers),
                known_secrets=self._key_manager.known_secrets,
            )

        try:
            payload = response.json()
        except Exception as exc:
            raise GeminiTransientError(
                f"Gemini returned invalid JSON payload for model {model_name}: {exc}",
                status_code=response.status_code,
                known_secrets=self._key_manager.known_secrets,
            ) from exc

        text, finish_reason, usage = extract_text_from_response_payload(payload)
        if not text:
            raise GeminiTransientError(
                f"Gemini returned empty response for model {model_name} (finishReason={finish_reason})",
                status_code=response.status_code,
                error_code=str(finish_reason or "EMPTY_RESPONSE"),
                known_secrets=self._key_manager.known_secrets,
            )
        return text, finish_reason, usage

    def _classify_transport_error(self, exc: Exception, model_name: str) -> GeminiError:
        if isinstance(exc, GeminiError):
            return exc
        if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
            return GeminiTransientError(
                f"Gemini network/transport error on {model_name}: {type(exc).__name__}: {exc}",
                error_code=type(exc).__name__,
                known_secrets=self._key_manager.known_secrets,
            )
        return GeminiTransientError(
            f"Unexpected error calling Gemini model {model_name}: {type(exc).__name__}: {exc}",
            error_code=type(exc).__name__,
            known_secrets=self._key_manager.known_secrets,
        )

    def _get_async_resources(self) -> Tuple[httpx.AsyncClient, asyncio.Semaphore]:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
        with self._client_lock:
            sem = self._async_semaphores_by_loop.get(loop_id)
            if sem is None:
                sem = asyncio.Semaphore(self._key_manager.config.max_concurrent_requests)
                self._async_semaphores_by_loop[loop_id] = sem

            if self._async_client is not None:
                return self._async_client, sem

            client = self._async_clients_by_loop.get(loop_id)
            if client is None or client.is_closed:
                client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout_seconds),
                    limits=httpx.Limits(
                        max_connections=max(20, self._key_manager.config.max_concurrent_requests * 4),
                        max_keepalive_connections=max(10, self._key_manager.config.max_concurrent_requests * 2),
                    ),
                )
                self._async_clients_by_loop[loop_id] = client
            return client, sem

    def generate_content(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 4096,
        response_mime_type: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        models: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        operation_name: str = "generate_content",
    ) -> GeminiResponse:
        """
        Synchronously invoke Gemini `generateContent` with automatic primary-first key failover,
        exponential backoff, cooldown enforcement, and model fallback.
        """
        self.refresh_keys_if_env_changed()
        if not self._key_manager.is_configured:
            raise GeminiConfigurationError(
                "Gemini API is not configured (no valid GEMINI_API_KEYS/GEMINI_API_KEY found)."
            )

        candidate_models = list(models) if models else list(self._models)
        if not candidate_models:
            candidate_models = list(DEFAULT_GEMINI_MODELS)

        last_error: Optional[Exception] = None
        total_attempts = 0
        rotations_this_call = 0
        first_key_index: Optional[int] = None
        waited_for_recovery = False
        reloaded_env_this_call = False
        effective_timeout = timeout if timeout is not None else self._timeout_seconds

        for model_name in candidate_models:
            tried_key_indices: Set[int] = set()
            include_thinking = True

            while True:
                lease = self._key_manager.acquire_key(
                    excluded_indices=tried_key_indices,
                    operation=operation_name,
                )

                if lease is None:
                    # If .env was updated with fresh API keys while keys were exhausted, sync immediately
                    if not reloaded_env_this_call and self.refresh_keys_if_env_changed(force=True):
                        reloaded_env_this_call = True
                        tried_key_indices.clear()
                        continue

                    # Check whether a brief recovery wait is appropriate when all keys are cooled down
                    next_wait = self._key_manager.next_recovery_in_seconds()
                    if (
                        not waited_for_recovery
                        and next_wait is not None
                        and 0.0 < next_wait <= self._key_manager.config.max_wait_for_recovery_seconds
                    ):
                        waited_for_recovery = True
                        tried_key_indices.clear()
                        self._key_manager.record_retry()
                        logger.info(
                            "[GeminiClient] All keys temporarily in cooldown; waiting %.2fs for recovery (operation=%s)",
                            next_wait,
                            operation_name,
                        )
                        self._sleep(next_wait)
                        continue
                    break

                if first_key_index is None:
                    first_key_index = lease.index
                elif lease.index != first_key_index:
                    rotations_this_call += 1

                max_transient = self._key_manager.config.max_transient_retries_per_key
                transient_attempt = 0
                move_to_next_model = False

                while True:
                    total_attempts += 1
                    pacing_wait = self._key_manager.reserve_pacing_delay()
                    if pacing_wait > 0:
                        self._sleep(pacing_wait)

                    payload = self._build_payload(
                        prompt=prompt,
                        model_name=model_name,
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        response_mime_type=response_mime_type,
                        thinking_budget=thinking_budget,
                        include_thinking_config=include_thinking,
                    )
                    headers = {
                        "Content-Type": "application/json",
                        "x-goog-api-key": lease.api_key,
                    }
                    url = self._endpoint_url(model_name)

                    t0 = time.monotonic()
                    try:
                        with self._key_manager.concurrency_semaphore:
                            resp = self._sync_client.post(
                                url,
                                json=payload,
                                headers=headers,
                                timeout=effective_timeout,
                            )
                        text, finish_reason, usage = self._parse_response_or_raise(resp, model_name)
                        latency_ms = (time.monotonic() - t0) * 1000.0
                        self._key_manager.record_success(
                            lease,
                            latency_ms=latency_ms,
                            model=model_name,
                            usage=usage,
                        )
                        return GeminiResponse(
                            text=text,
                            model=model_name,
                            key_label=lease.label,
                            attempts=total_attempts,
                            rotations=rotations_this_call,
                            latency_ms=round(latency_ms, 2),
                            finish_reason=finish_reason,
                            usage=usage,
                        )

                    except Exception as raw_exc:
                        err = self._classify_transport_error(raw_exc, model_name)
                        last_error = err

                        # Compatibility fallback if a model rejects thinkingConfig
                        if (
                            isinstance(err, GeminiBadRequestError)
                            and include_thinking
                            and "thinking" in str(err).lower()
                        ):
                            include_thinking = False
                            self._key_manager.record_retry()
                            logger.info(
                                "[GeminiClient] Model %s rejected thinkingConfig; retrying without it.",
                                model_name,
                            )
                            continue

                        if isinstance(err, GeminiAuthError):
                            self._key_manager.record_invalid_key(lease, str(err))
                            tried_key_indices.add(lease.index)
                            if self._key_manager.has_eligible_key(tried_key_indices):
                                self._key_manager.record_retry()
                            break

                        if isinstance(err, GeminiRateLimitError):
                            self._key_manager.record_rate_limit(
                                lease,
                                reason=str(err),
                                retry_after=err.retry_after,
                                is_quota_exhausted=err.is_quota_exhausted,
                                project_id=err.project_id,
                            )
                            tried_key_indices.add(lease.index)
                            if self._key_manager.has_eligible_key(tried_key_indices):
                                self._key_manager.record_retry()
                                logger.info(
                                    "[GeminiClient] Rotating away from %s after %s (operation=%s)",
                                    lease.label,
                                    "quota_exhausted" if err.is_quota_exhausted else "rate_limit",
                                    operation_name,
                                )
                            break

                        if isinstance(err, GeminiModelUnavailableError):
                            self._key_manager.release_unused_lease(lease)
                            logger.warning(
                                "[GeminiClient] Model %s unavailable (%s); trying next configured model.",
                                model_name,
                                str(err),
                            )
                            move_to_next_model = True
                            break

                        if isinstance(err, GeminiBadRequestError):
                            self._key_manager.release_unused_lease(lease)
                            logger.error(
                                "[GeminiClient] Non-retryable bad request on %s (operation=%s): %s",
                                model_name,
                                operation_name,
                                str(err),
                            )
                            raise err

                        # Transient upstream failure (5xx / timeout / connection error)
                        if transient_attempt < max_transient:
                            delay = self._key_manager.compute_retry_delay(transient_attempt)
                            transient_attempt += 1
                            self._key_manager.record_retry()
                            logger.warning(
                                "[GeminiClient] Transient failure on %s with %s (retry %d/%d in %.2fs): %s",
                                model_name,
                                lease.label,
                                transient_attempt,
                                max_transient,
                                delay,
                                str(err),
                            )
                            self._sleep(delay)
                            continue

                        self._key_manager.record_transient_failure(lease, str(err))
                        tried_key_indices.add(lease.index)
                        if self._key_manager.has_eligible_key(tried_key_indices):
                            self._key_manager.record_retry()
                            delay = self._key_manager.compute_retry_delay(0)
                            if delay > 0:
                                self._sleep(delay)
                        break

                if move_to_next_model:
                    break

            # If the loop broke solely because a model was unavailable, continue to next model.
            # If all keys are unavailable/exhausted, stop immediately instead of retrying models.
            if not isinstance(last_error, GeminiModelUnavailableError):
                break

        next_recovery = self._key_manager.next_recovery_in_seconds()
        if isinstance(last_error, GeminiModelUnavailableError):
            raise last_error

        raise GeminiAllKeysExhaustedError(
            f"All Gemini API keys are currently unavailable or exhausted for operation '{operation_name}'. "
            f"Next recovery in {round(next_recovery, 1)}s."
            if next_recovery is not None
            else f"All Gemini API keys are unavailable or invalid for operation '{operation_name}'.",
            next_recovery_in_seconds=next_recovery,
            last_error=last_error,
            known_secrets=self._key_manager.known_secrets,
        )

    async def agenerate_content(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 4096,
        response_mime_type: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        models: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        operation_name: str = "generate_content",
    ) -> GeminiResponse:
        """
        Asynchronously invoke Gemini `generateContent` without blocking the event loop,
        using the same thread-safe `GeminiKeyManager` state machine.
        """
        self.refresh_keys_if_env_changed()
        if not self._key_manager.is_configured:
            raise GeminiConfigurationError(
                "Gemini API is not configured (no valid GEMINI_API_KEYS/GEMINI_API_KEY found)."
            )

        candidate_models = list(models) if models else list(self._models)
        if not candidate_models:
            candidate_models = list(DEFAULT_GEMINI_MODELS)

        async_client, async_sem = self._get_async_resources()
        last_error: Optional[Exception] = None
        total_attempts = 0
        rotations_this_call = 0
        first_key_index: Optional[int] = None
        waited_for_recovery = False
        reloaded_env_this_call = False
        effective_timeout = timeout if timeout is not None else self._timeout_seconds

        for model_name in candidate_models:
            tried_key_indices: Set[int] = set()
            include_thinking = True

            while True:
                lease = self._key_manager.acquire_key(
                    excluded_indices=tried_key_indices,
                    operation=operation_name,
                )

                if lease is None:
                    if not reloaded_env_this_call and self.refresh_keys_if_env_changed(force=True):
                        reloaded_env_this_call = True
                        tried_key_indices.clear()
                        continue

                    next_wait = self._key_manager.next_recovery_in_seconds()
                    if (
                        not waited_for_recovery
                        and next_wait is not None
                        and 0.0 < next_wait <= self._key_manager.config.max_wait_for_recovery_seconds
                    ):
                        waited_for_recovery = True
                        tried_key_indices.clear()
                        self._key_manager.record_retry()
                        logger.info(
                            "[GeminiClient] All keys temporarily in cooldown; async waiting %.2fs for recovery (operation=%s)",
                            next_wait,
                            operation_name,
                        )
                        await self._async_sleep(next_wait)
                        continue
                    break

                if first_key_index is None:
                    first_key_index = lease.index
                elif lease.index != first_key_index:
                    rotations_this_call += 1

                max_transient = self._key_manager.config.max_transient_retries_per_key
                transient_attempt = 0
                move_to_next_model = False

                while True:
                    total_attempts += 1
                    pacing_wait = self._key_manager.reserve_pacing_delay()
                    if pacing_wait > 0:
                        await self._async_sleep(pacing_wait)

                    payload = self._build_payload(
                        prompt=prompt,
                        model_name=model_name,
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        response_mime_type=response_mime_type,
                        thinking_budget=thinking_budget,
                        include_thinking_config=include_thinking,
                    )
                    headers = {
                        "Content-Type": "application/json",
                        "x-goog-api-key": lease.api_key,
                    }
                    url = self._endpoint_url(model_name)

                    t0 = time.monotonic()
                    try:
                        async with async_sem:
                            resp = await async_client.post(
                                url,
                                json=payload,
                                headers=headers,
                                timeout=effective_timeout,
                            )
                        text, finish_reason, usage = self._parse_response_or_raise(resp, model_name)
                        latency_ms = (time.monotonic() - t0) * 1000.0
                        self._key_manager.record_success(
                            lease,
                            latency_ms=latency_ms,
                            model=model_name,
                            usage=usage,
                        )
                        return GeminiResponse(
                            text=text,
                            model=model_name,
                            key_label=lease.label,
                            attempts=total_attempts,
                            rotations=rotations_this_call,
                            latency_ms=round(latency_ms, 2),
                            finish_reason=finish_reason,
                            usage=usage,
                        )

                    except Exception as raw_exc:
                        err = self._classify_transport_error(raw_exc, model_name)
                        last_error = err

                        if (
                            isinstance(err, GeminiBadRequestError)
                            and include_thinking
                            and "thinking" in str(err).lower()
                        ):
                            include_thinking = False
                            self._key_manager.record_retry()
                            continue

                        if isinstance(err, GeminiAuthError):
                            self._key_manager.record_invalid_key(lease, str(err))
                            tried_key_indices.add(lease.index)
                            if self._key_manager.has_eligible_key(tried_key_indices):
                                self._key_manager.record_retry()
                            break

                        if isinstance(err, GeminiRateLimitError):
                            self._key_manager.record_rate_limit(
                                lease,
                                reason=str(err),
                                retry_after=err.retry_after,
                                is_quota_exhausted=err.is_quota_exhausted,
                                project_id=err.project_id,
                            )
                            tried_key_indices.add(lease.index)
                            if self._key_manager.has_eligible_key(tried_key_indices):
                                self._key_manager.record_retry()
                            break

                        if isinstance(err, GeminiModelUnavailableError):
                            self._key_manager.release_unused_lease(lease)
                            move_to_next_model = True
                            break

                        if isinstance(err, GeminiBadRequestError):
                            self._key_manager.release_unused_lease(lease)
                            raise err

                        if transient_attempt < max_transient:
                            delay = self._key_manager.compute_retry_delay(transient_attempt)
                            transient_attempt += 1
                            self._key_manager.record_retry()
                            await self._async_sleep(delay)
                            continue

                        self._key_manager.record_transient_failure(lease, str(err))
                        tried_key_indices.add(lease.index)
                        if self._key_manager.has_eligible_key(tried_key_indices):
                            self._key_manager.record_retry()
                            delay = self._key_manager.compute_retry_delay(0)
                            if delay > 0:
                                await self._async_sleep(delay)
                        break

                if move_to_next_model:
                    break

            if not isinstance(last_error, GeminiModelUnavailableError):
                break

        next_recovery = self._key_manager.next_recovery_in_seconds()
        if isinstance(last_error, GeminiModelUnavailableError):
            raise last_error

        raise GeminiAllKeysExhaustedError(
            f"All Gemini API keys are currently unavailable or exhausted for operation '{operation_name}'. "
            f"Next recovery in {round(next_recovery, 1)}s."
            if next_recovery is not None
            else f"All Gemini API keys are unavailable or invalid for operation '{operation_name}'.",
            next_recovery_in_seconds=next_recovery,
            last_error=last_error,
            known_secrets=self._key_manager.known_secrets,
        )

    def close(self) -> None:
        """Close owned synchronous HTTP connection pools."""
        if self._owns_sync_client and self._sync_client is not None:
            try:
                self._sync_client.close()
            except Exception:
                pass

    async def aclose(self) -> None:
        """Close owned synchronous and asynchronous HTTP connection pools."""
        self.close()
        with self._client_lock:
            clients = list(self._async_clients_by_loop.values())
            self._async_clients_by_loop.clear()
            self._async_semaphores_by_loop.clear()
        for client in clients:
            try:
                if not client.is_closed:
                    await client.aclose()
            except Exception:
                pass
        if self._owns_async_client and self._async_client is not None:
            try:
                if not self._async_client.is_closed:
                    await self._async_client.aclose()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Process-Wide Singleton Accessors (Thread-Safe)
# ---------------------------------------------------------------------------

_singleton_lock = threading.Lock()
_default_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Return the lazily initialized, thread-safe process-wide GeminiClient."""
    global _default_client
    if _default_client is not None:
        return _default_client
    with _singleton_lock:
        if _default_client is None:
            _default_client = GeminiClient.from_env()
            status = _default_client.get_status()
            if status["configured"]:
                logger.info(
                    "[GeminiClient] Initialized key pool with %d key(s); primary=%s; models=%s",
                    status["total_keys"],
                    status["active_key_label"],
                    status["models"],
                )
            else:
                logger.warning(
                    "[GeminiClient] No valid Gemini API keys configured (GEMINI_API_KEYS/GEMINI_API_KEY). "
                    "Gemini features will fall back to local NLP."
                )
        return _default_client


def reload_gemini_client(client: Optional[GeminiClient] = None) -> GeminiClient:
    """Replace or re-initialize the singleton GeminiClient (useful for testing or env reloads)."""
    global _default_client
    with _singleton_lock:
        old = _default_client
        _default_client = client if client is not None else GeminiClient.from_env()
    if old is not None and old is not _default_client:
        old.close()
    return _default_client


async def close_gemini_client() -> None:
    """Close and release the process-wide GeminiClient during application shutdown."""
    global _default_client
    with _singleton_lock:
        client = _default_client
        _default_client = None
    if client is not None:
        await client.aclose()
