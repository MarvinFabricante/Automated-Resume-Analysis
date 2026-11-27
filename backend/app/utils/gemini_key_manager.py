"""
Gemini API Key Manager
----------------------
Domain-agnostic, thread-safe API key pool and failover state machine for Google Gemini.

Design principles:
- Primary-first selection: always prefers the primary eligible key (index 0) by default.
  Does NOT round-robin across healthy keys to circumvent provider rate limits.
- Failover on key-specific failures: switches to the next eligible key when the current
  key encounters invalid/revoked credentials, HTTP 429 rate limits, quota exhaustion,
  or repeated transient failures.
- Project-level quota respect: tracks optional configured or runtime-discovered GCP
  project IDs (`projects/<id>`) so a project-level quota/rate-limit cooldown applies
  to all keys sharing the same project rather than circumventing project limits.
- Exponential backoff & cooldowns: respects server `Retry-After` / `RetryInfo.retryDelay`,
  applies exponential backoff with bounded jitter, and auto-recovers keys once cooldowns expire.
- Secret safety: raw API keys are never logged, repr'd, or exposed in status snapshots.
- Concurrency safety: all state transitions are guarded by a reentrant lock, and in-flight
  concurrency is bounded via a configurable semaphore.
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)


# Patterns that could match Gemini / Google API keys in arbitrary error text
_SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_\-]{15,}"),
    re.compile(r"AQ\.[0-9A-Za-z._\-]{15,}"),
    re.compile(r"([?&](?:api_)?key=)[^&\s\"']+"),
    re.compile(r"(x-goog-api-key['\"]?\s*[:=]\s*['\"]?)[^\s,'\"\}]+", re.IGNORECASE),
)

_PLACEHOLDER_MARKERS = (
    "your_gemini_api_key",
    "your-gemini-api-key",
    "your_api_key",
    "changeme",
    "replace_me",
    "placeholder",
    "example_key",
)


class KeyStatus(str, Enum):
    AVAILABLE = "available"
    COOLDOWN = "cooldown"
    INVALID = "invalid"


def key_fingerprint(api_key: str) -> str:
    """Return a short, non-reversible SHA-256 fingerprint for safe logging and metrics."""
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return digest[:8]


def mask_api_key(api_key: str) -> str:
    """Return a safe, non-sensitive display token for an API key."""
    if not api_key:
        return "<empty>"
    return f"fp:{key_fingerprint(api_key)}"


def sanitize_error_message(
    message: Any,
    known_secrets: Optional[Iterable[str]] = None,
) -> str:
    """Scrub raw API keys and credential patterns from text before logging or raising."""
    text = "" if message is None else str(message)
    if known_secrets:
        for secret in known_secrets:
            if secret and len(secret) >= 6 and secret in text:
                text = text.replace(secret, "[REDACTED_API_KEY]")
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            text = pattern.sub(r"\1[REDACTED_API_KEY]", text)
        else:
            text = pattern.sub("[REDACTED_API_KEY]", text)
    return text


def _is_placeholder_key(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _split_env_list(raw: str) -> List[str]:
    """
    Parse a delimited environment list safely.
    Handles comma/semicolon/newline/whitespace separation, multiline quoted values,
    escaped newline literals (\\n, \\r), trailing commas, and stray spaces/quotes.
    """
    if not raw:
        return []
    normalized = (
        str(raw)
        .replace("\\r", "\n")
        .replace("\\n", "\n")
        .replace("\\t", " ")
    )
    parts = re.split(r"[,;\s]+", normalized)
    cleaned: List[str] = []
    for part in parts:
        token = part.strip().strip('"').strip("'").strip()
        if token:
            cleaned.append(token)
    return cleaned


def load_gemini_api_keys_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Tuple[List[str], List[Optional[str]]]:
    """
    Load ordered, deduplicated Gemini API keys (and optional project tags) from env vars.

    Precedence order (index 0 is ALWAYS the primary key):
      1. GEMINI_API_KEY (explicit primary key, if set)
      2. GEMINI_API_KEYS (comma/semicolon/newline-separated list)
      3. Numbered keys: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... in ascending numeric order

    Optional project mapping:
      - GEMINI_API_KEY_PROJECTS: comma-separated project identifiers corresponding to keys
        (used to enforce shared project-level quota cooldowns).
    """
    source = os.environ if env is None else env
    ordered_candidates: List[str] = []

    primary_single = (source.get("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    if primary_single:
        ordered_candidates.append(primary_single)

    pool_raw = source.get("GEMINI_API_KEYS") or ""
    ordered_candidates.extend(_split_env_list(pool_raw))

    numbered: List[Tuple[int, str]] = []
    for k, v in source.items():
        match = re.fullmatch(r"GEMINI_API_KEY_(\d+)", k.strip())
        if match and v and v.strip():
            numbered.append((int(match.group(1)), v.strip().strip('"').strip("'")))
    for _, val in sorted(numbered, key=lambda item: item[0]):
        ordered_candidates.append(val)

    keys: List[str] = []
    seen: Set[str] = set()
    for candidate in ordered_candidates:
        if _is_placeholder_key(candidate):
            continue
        if candidate not in seen:
            seen.add(candidate)
            keys.append(candidate)

    raw_projects = _split_env_list(source.get("GEMINI_API_KEY_PROJECTS") or "")
    project_ids: List[Optional[str]] = []
    for idx in range(len(keys)):
        proj = raw_projects[idx].strip() if idx < len(raw_projects) and raw_projects[idx].strip() else None
        project_ids.append(proj)

    return keys, project_ids


def _env_float(name: str, default: float, min_val: float = 0.0, env: Optional[Dict[str, str]] = None) -> float:
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(min_val, float(str(raw).strip()))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, min_val: int = 0, env: Optional[Dict[str, str]] = None) -> int:
    source = os.environ if env is None else env
    raw = source.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(min_val, int(str(raw).strip()))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class KeyPoolConfig:
    """Configuration parameters for Gemini key failover, backoff, cooldown, and concurrency."""

    base_cooldown_seconds: float = 15.0
    max_cooldown_seconds: float = 300.0
    quota_cooldown_seconds: float = 900.0
    transient_cooldown_seconds: float = 30.0
    transient_failure_threshold: int = 3
    retry_base_delay_seconds: float = 0.5
    retry_max_delay_seconds: float = 8.0
    max_transient_retries_per_key: int = 2
    max_wait_for_recovery_seconds: float = 5.0
    jitter_ratio: float = 0.2
    max_concurrent_requests: int = 4
    min_request_interval_seconds: float = 0.0
    enable_redis_sync: bool = True

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "KeyPoolConfig":
        source = os.environ if env is None else env
        in_pytest = "PYTEST_CURRENT_TEST" in os.environ
        raw_redis_sync = (source.get("GEMINI_REDIS_COOLDOWN_SYNC") or "").strip().lower()
        if raw_redis_sync in ("true", "1", "yes"):
            redis_sync = True
        elif raw_redis_sync in ("false", "0", "no"):
            redis_sync = False
        else:
            redis_sync = not in_pytest

        return cls(
            base_cooldown_seconds=_env_float("GEMINI_BASE_COOLDOWN_SECONDS", 15.0, 0.1, source),
            max_cooldown_seconds=_env_float("GEMINI_MAX_COOLDOWN_SECONDS", 300.0, 1.0, source),
            quota_cooldown_seconds=_env_float("GEMINI_QUOTA_COOLDOWN_SECONDS", 900.0, 1.0, source),
            transient_cooldown_seconds=_env_float("GEMINI_TRANSIENT_COOLDOWN_SECONDS", 30.0, 0.1, source),
            transient_failure_threshold=_env_int("GEMINI_TRANSIENT_FAILURE_THRESHOLD", 3, 1, source),
            retry_base_delay_seconds=_env_float("GEMINI_RETRY_BASE_DELAY_SECONDS", 0.5, 0.0, source),
            retry_max_delay_seconds=_env_float("GEMINI_RETRY_MAX_DELAY_SECONDS", 8.0, 0.0, source),
            max_transient_retries_per_key=_env_int("GEMINI_MAX_TRANSIENT_RETRIES", 2, 0, source),
            max_wait_for_recovery_seconds=_env_float("GEMINI_MAX_WAIT_FOR_RECOVERY_SECONDS", 5.0, 0.0, source),
            jitter_ratio=min(0.5, _env_float("GEMINI_JITTER_RATIO", 0.2, 0.0, source)),
            max_concurrent_requests=_env_int("GEMINI_MAX_CONCURRENT_REQUESTS", 4, 1, source),
            min_request_interval_seconds=_env_float("GEMINI_MIN_REQUEST_INTERVAL_MS", 0.0, 0.0, source) / 1000.0,
            enable_redis_sync=redis_sync,
        )


@dataclass
class KeyState:
    """Mutable per-key health, cooldown, and usage tracking state (guarded by manager lock)."""

    index: int
    api_key: str = field(repr=False)
    label: str
    is_primary: bool
    project_id: Optional[str] = None
    status: KeyStatus = KeyStatus.AVAILABLE
    cooldown_until: float = 0.0
    cooldown_until_utc: Optional[str] = None
    last_cooldown_started_at: float = -1.0
    consecutive_rate_limits: int = 0
    consecutive_transient_failures: int = 0
    in_flight: int = 0
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    rate_limit_count: int = 0
    quota_exhaustion_count: int = 0
    transient_error_count: int = 0
    invalid_error_count: int = 0
    total_prompt_tokens: int = 0
    total_output_tokens: int = 0
    last_error_category: Optional[str] = None
    last_error_reason: Optional[str] = None
    last_used_at: Optional[str] = None
    last_success_at: Optional[str] = None


class KeyLease:
    """
    Immutable lease returned when a caller acquires an API key for an attempt.
    Its `__repr__` intentionally omits the raw API key to prevent credential leaks.
    """

    __slots__ = (
        "index",
        "label",
        "_api_key",
        "project_id",
        "is_primary",
        "acquired_at",
        "rotated_from_primary",
        "_released",
    )

    def __init__(
        self,
        index: int,
        label: str,
        api_key: str,
        project_id: Optional[str],
        is_primary: bool,
        acquired_at: float,
        rotated_from_primary: bool,
    ) -> None:
        self.index = index
        self.label = label
        self._api_key = api_key
        self.project_id = project_id
        self.is_primary = is_primary
        self.acquired_at = acquired_at
        self.rotated_from_primary = rotated_from_primary
        self._released = False

    @property
    def api_key(self) -> str:
        return self._api_key

    def __repr__(self) -> str:
        return (
            f"KeyLease(index={self.index}, label={self.label!r}, "
            f"is_primary={self.is_primary}, project_id={self.project_id!r})"
        )


class GeminiKeyManager:
    """
    Thread-safe manager for a prioritized pool of Gemini API keys.

    Always selects the primary eligible key (lowest index) by default and automatically
    fails over to the next eligible key when a key becomes unavailable, rate-limited,
    quota-exhausted, or invalid.
    """

    _REDIS_KEY_PREFIX = "gemini:cooldown:key:"
    _REDIS_PROJECT_PREFIX = "gemini:cooldown:project:"

    def __init__(
        self,
        api_keys: Sequence[str],
        config: Optional[KeyPoolConfig] = None,
        project_ids: Optional[Sequence[Optional[str]]] = None,
        clock_fn: Callable[[], float] = time.monotonic,
        rng_fn: Callable[[], float] = random.random,
    ) -> None:
        self._config = config or KeyPoolConfig()
        self._clock = clock_fn
        self._rng = rng_fn
        self._lock = threading.RLock()
        self._concurrency_semaphore = threading.BoundedSemaphore(self._config.max_concurrent_requests)

        # Normalize and deduplicate keys while preserving priority order (index 0 = primary)
        cleaned_entries: List[KeyState] = []
        seen: Set[str] = set()
        for raw_idx, raw_key in enumerate(api_keys):
            key = (raw_key or "").strip()
            if not key or _is_placeholder_key(key) or key in seen:
                continue
            seen.add(key)
            idx = len(cleaned_entries)
            proj = None
            if project_ids and raw_idx < len(project_ids):
                proj = project_ids[raw_idx]
            cleaned_entries.append(
                KeyState(
                    index=idx,
                    api_key=key,
                    label=f"key#{idx + 1} ({mask_api_key(key)})",
                    is_primary=(idx == 0),
                    project_id=proj,
                )
            )

        self._keys: List[KeyState] = cleaned_entries
        self._secret_tuple: Tuple[str, ...] = tuple(entry.api_key for entry in cleaned_entries)
        self._project_cooldowns: Dict[str, float] = {}
        self._last_selected_index: Optional[int] = None
        self._last_dispatch_monotonic: float = 0.0

        # Global aggregate counters
        self._total_requests = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_retries = 0
        self._total_rotations = 0
        self._total_rate_limits = 0
        self._total_quota_exhaustions = 0
        self._total_transient_errors = 0
        self._total_invalid_key_errors = 0

    @classmethod
    def from_env(
        cls,
        env: Optional[Dict[str, str]] = None,
        config: Optional[KeyPoolConfig] = None,
        clock_fn: Callable[[], float] = time.monotonic,
        rng_fn: Callable[[], float] = random.random,
    ) -> "GeminiKeyManager":
        keys, project_ids = load_gemini_api_keys_from_env(env=env)
        cfg = config or KeyPoolConfig.from_env(env=env)
        return cls(
            api_keys=keys,
            config=cfg,
            project_ids=project_ids,
            clock_fn=clock_fn,
            rng_fn=rng_fn,
        )

    @property
    def config(self) -> KeyPoolConfig:
        return self._config

    @property
    def concurrency_semaphore(self) -> threading.BoundedSemaphore:
        return self._concurrency_semaphore

    @property
    def key_count(self) -> int:
        return len(self._keys)

    @property
    def is_configured(self) -> bool:
        return len(self._keys) > 0

    @property
    def known_secrets(self) -> Tuple[str, ...]:
        with self._lock:
            return self._secret_tuple

    def sync_keys(
        self,
        api_keys: Sequence[str],
        project_ids: Optional[Sequence[Optional[str]]] = None,
    ) -> Dict[str, int]:
        """
        Thread-safely synchronize the managed key pool with a refreshed ordered key list.

        - Preserves existing keys' health status, cooldown deadlines, failure streaks,
          discovered project_ids, and usage counters.
        - Immediately registers newly inserted keys as AVAILABLE.
        - Removes keys that are no longer configured.
        - Updates secret-redaction coverage atomically.
        """
        normalized_pairs: List[Tuple[str, Optional[str]]] = []
        seen: Set[str] = set()
        for raw_idx, raw_key in enumerate(api_keys):
            key = (raw_key or "").strip().strip('"').strip("'").strip()
            if not key or _is_placeholder_key(key) or key in seen:
                continue
            seen.add(key)
            proj = None
            if project_ids and raw_idx < len(project_ids):
                raw_p = project_ids[raw_idx]
                proj = raw_p.strip() if isinstance(raw_p, str) and raw_p.strip() else None
            normalized_pairs.append((key, proj))

        with self._lock:
            existing_by_key: Dict[str, KeyState] = {entry.api_key: entry for entry in self._keys}
            old_order = [entry.api_key for entry in self._keys]
            new_order = [pair[0] for pair in normalized_pairs]

            if old_order == new_order:
                # Update explicit project tags if provided without altering order
                for idx, (_, proj) in enumerate(normalized_pairs):
                    if proj and not self._keys[idx].project_id:
                        self._keys[idx].project_id = proj
                return {"added": 0, "removed": 0, "total": len(self._keys)}

            prev_selected_key: Optional[str] = None
            if self._last_selected_index is not None and 0 <= self._last_selected_index < len(self._keys):
                prev_selected_key = self._keys[self._last_selected_index].api_key

            updated_entries: List[KeyState] = []
            added_count = 0
            for idx, (key, proj) in enumerate(normalized_pairs):
                prev = existing_by_key.get(key)
                if prev is not None:
                    prev.index = idx
                    prev.is_primary = (idx == 0)
                    prev.label = f"key#{idx + 1} ({mask_api_key(key)})"
                    if proj and not prev.project_id:
                        prev.project_id = proj
                    updated_entries.append(prev)
                else:
                    added_count += 1
                    updated_entries.append(
                        KeyState(
                            index=idx,
                            api_key=key,
                            label=f"key#{idx + 1} ({mask_api_key(key)})",
                            is_primary=(idx == 0),
                            project_id=proj,
                        )
                    )

            removed_count = sum(1 for k in existing_by_key if k not in seen)
            self._keys = updated_entries
            self._secret_tuple = tuple(entry.api_key for entry in updated_entries)

            if prev_selected_key is not None:
                new_selected = next(
                    (e.index for e in updated_entries if e.api_key == prev_selected_key),
                    None,
                )
                self._last_selected_index = new_selected
            else:
                self._last_selected_index = None

            logger.info(
                "[GeminiKeyManager] Synced API key pool: added=%d, removed=%d, total=%d",
                added_count,
                removed_count,
                len(updated_entries),
            )
            return {"added": added_count, "removed": removed_count, "total": len(updated_entries)}

    def sanitize(self, text: Any) -> str:
        """Scrub any managed API key or Google key pattern from an error or log message."""
        return sanitize_error_message(text, self.known_secrets)

    def compute_retry_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Compute exponential backoff delay with bounded jitter for request retries."""
        base = self._config.retry_base_delay_seconds
        cap = self._config.retry_max_delay_seconds
        delay = min(cap, base * (2 ** max(0, attempt)))
        jitter = delay * self._config.jitter_ratio * self._rng()
        computed = delay + jitter
        if retry_after is not None and retry_after > 0:
            computed = max(computed, min(retry_after, self._config.max_wait_for_recovery_seconds))
        return round(computed, 4)

    def reserve_pacing_delay(self) -> float:
        """
        Enforce optional minimum spacing between outbound requests across threads
        to respect provider RPM quotas smoothly. Returns seconds the caller should wait.
        """
        interval = self._config.min_request_interval_seconds
        if interval <= 0:
            return 0.0
        with self._lock:
            now = self._clock()
            next_slot = max(now, self._last_dispatch_monotonic + interval)
            wait = max(0.0, next_slot - now)
            self._last_dispatch_monotonic = next_slot
            return wait

    def _now_utc_iso(self, offset_seconds: float = 0.0) -> str:
        ts = datetime.now(timezone.utc).timestamp() + offset_seconds
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    def _sync_redis_cooldown_read(self, entry: KeyState, now: float) -> None:
        """Best-effort read of cross-worker cooldown state from Redis."""
        if not self._config.enable_redis_sync:
            return
        try:
            from app.utils.redis_client import get_sync_redis

            client = get_sync_redis()
            fp = key_fingerprint(entry.api_key)
            raw_ttl = client.ttl(f"{self._REDIS_KEY_PREFIX}{fp}")
            if isinstance(raw_ttl, int) and raw_ttl > 0:
                until = now + float(raw_ttl)
                if until > entry.cooldown_until:
                    entry.status = KeyStatus.COOLDOWN
                    entry.cooldown_until = until
                    entry.cooldown_until_utc = self._now_utc_iso(float(raw_ttl))

            if entry.project_id:
                proj_ttl = client.ttl(f"{self._REDIS_PROJECT_PREFIX}{entry.project_id}")
                if isinstance(proj_ttl, int) and proj_ttl > 0:
                    proj_until = now + float(proj_ttl)
                    if proj_until > self._project_cooldowns.get(entry.project_id, 0.0):
                        self._project_cooldowns[entry.project_id] = proj_until
        except Exception:
            # Never allow Redis outages to break in-process failover
            pass

    def _sync_redis_cooldown_write(
        self,
        entry: KeyState,
        cooldown_seconds: float,
        project_id: Optional[str] = None,
    ) -> None:
        """Best-effort broadcast of cooldown state to Redis for multi-worker awareness."""
        if not self._config.enable_redis_sync or cooldown_seconds < 1.0:
            return
        try:
            from app.utils.redis_client import get_sync_redis

            client = get_sync_redis()
            ttl_int = max(1, int(round(cooldown_seconds)))
            fp = key_fingerprint(entry.api_key)
            client.setex(f"{self._REDIS_KEY_PREFIX}{fp}", ttl_int, entry.last_error_category or "cooldown")
            effective_proj = project_id or entry.project_id
            if effective_proj:
                client.setex(f"{self._REDIS_PROJECT_PREFIX}{effective_proj}", ttl_int, "project_cooldown")
        except Exception:
            pass

    def _refresh_entry_state_locked(self, entry: KeyState, now: float) -> None:
        """Auto-recover a key from COOLDOWN once its cooldown deadline has passed."""
        if entry.status == KeyStatus.COOLDOWN and now >= entry.cooldown_until:
            entry.status = KeyStatus.AVAILABLE
            entry.cooldown_until = 0.0
            entry.cooldown_until_utc = None
            logger.info(
                "[GeminiKeyManager] Key %s cooldown expired; returned to AVAILABLE state.",
                entry.label,
            )

    def _is_project_in_cooldown_locked(self, project_id: Optional[str], now: float) -> Tuple[bool, float]:
        if not project_id:
            return False, 0.0
        until = self._project_cooldowns.get(project_id, 0.0)
        if until > now:
            return True, until - now
        if project_id in self._project_cooldowns:
            del self._project_cooldowns[project_id]
        return False, 0.0

    def acquire_key(
        self,
        excluded_indices: Optional[Set[int]] = None,
        operation: str = "generate_content",
    ) -> Optional[KeyLease]:
        """
        Acquire the highest-priority eligible API key (primary key first).

        Skips keys that are INVALID, currently in COOLDOWN, belong to a project currently
        in project-level cooldown, or are already in `excluded_indices`.
        Returns None if no eligible key is available.
        """
        excluded = excluded_indices or set()
        with self._lock:
            if not self._keys:
                return None

            now = self._clock()
            previous_index = self._last_selected_index

            for entry in self._keys:
                if entry.index in excluded:
                    continue
                if entry.status == KeyStatus.INVALID:
                    continue

                self._refresh_entry_state_locked(entry, now)
                if entry.status == KeyStatus.AVAILABLE:
                    self._sync_redis_cooldown_read(entry, now)
                    self._refresh_entry_state_locked(entry, now)

                if entry.status != KeyStatus.AVAILABLE:
                    continue

                proj_blocked, proj_rem = self._is_project_in_cooldown_locked(entry.project_id, now)
                if proj_blocked:
                    logger.debug(
                        "[GeminiKeyManager] Skipping %s for %s because shared project %s is in cooldown (%.1fs remaining).",
                        entry.label,
                        operation,
                        entry.project_id,
                        proj_rem,
                    )
                    continue

                entry.in_flight += 1
                entry.total_requests += 1
                entry.last_used_at = self._now_utc_iso()
                self._total_requests += 1

                rotated = (previous_index is not None and previous_index != entry.index) or (
                    not entry.is_primary and bool(excluded)
                )
                if previous_index is not None and previous_index != entry.index:
                    self._total_rotations += 1
                    prev_label = self._keys[previous_index].label
                    direction = "recovered to primary" if entry.is_primary else "rotated"
                    logger.info(
                        "[GeminiKeyManager] Key %s: %s -> %s (operation=%s)",
                        direction,
                        prev_label,
                        entry.label,
                        operation,
                    )
                self._last_selected_index = entry.index

                return KeyLease(
                    index=entry.index,
                    label=entry.label,
                    api_key=entry.api_key,
                    project_id=entry.project_id,
                    is_primary=entry.is_primary,
                    acquired_at=now,
                    rotated_from_primary=rotated and not entry.is_primary,
                )

            return None

    def release_unused_lease(self, lease: KeyLease) -> None:
        """Release a lease without recording success/failure (e.g., on non-key bad request)."""
        with self._lock:
            if lease._released:
                return
            lease._released = True
            entry = self._keys[lease.index]
            entry.in_flight = max(0, entry.in_flight - 1)

    def record_retry(self) -> None:
        """Increment aggregate retry counter."""
        with self._lock:
            self._total_retries += 1

    def record_success(
        self,
        lease: KeyLease,
        latency_ms: Optional[float] = None,
        model: Optional[str] = None,
        usage: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a leased key call successful and reset its consecutive failure streaks."""
        with self._lock:
            entry = self._keys[lease.index]
            if not lease._released:
                lease._released = True
                entry.in_flight = max(0, entry.in_flight - 1)

            entry.success_count += 1
            entry.consecutive_rate_limits = 0
            entry.consecutive_transient_failures = 0
            entry.last_success_at = self._now_utc_iso()
            if entry.status == KeyStatus.COOLDOWN:
                entry.status = KeyStatus.AVAILABLE
                entry.cooldown_until = 0.0
                entry.cooldown_until_utc = None

            if usage:
                entry.total_prompt_tokens += int(usage.get("promptTokenCount") or 0)
                entry.total_output_tokens += int(usage.get("candidatesTokenCount") or 0)

            self._total_successes += 1

            logger.info(
                "[GeminiKeyManager] Request succeeded with %s (model=%s, latency_ms=%s, total_successes=%d)",
                entry.label,
                model or "unknown",
                f"{latency_ms:.1f}" if latency_ms is not None else "n/a",
                entry.success_count,
            )

    def record_invalid_key(self, lease: KeyLease, reason: str) -> None:
        """Permanently disable a key that failed authentication / authorization checks."""
        safe_reason = self.sanitize(reason)
        with self._lock:
            entry = self._keys[lease.index]
            if not lease._released:
                lease._released = True
                entry.in_flight = max(0, entry.in_flight - 1)

            entry.status = KeyStatus.INVALID
            entry.cooldown_until = 0.0
            entry.cooldown_until_utc = None
            entry.failure_count += 1
            entry.invalid_error_count += 1
            entry.last_error_category = "invalid_key"
            entry.last_error_reason = safe_reason[:300]
            self._total_failures += 1
            self._total_invalid_key_errors += 1

            logger.error(
                "[GeminiKeyManager] Disabled %s as INVALID (reason=%s). Failing over to next eligible key.",
                entry.label,
                safe_reason[:200],
            )

    def record_rate_limit(
        self,
        lease: KeyLease,
        reason: str,
        retry_after: Optional[float] = None,
        is_quota_exhausted: bool = False,
        project_id: Optional[str] = None,
    ) -> float:
        """
        Place a key (and its shared GCP project, if identified) into exponential-backoff cooldown.
        Returns the applied cooldown duration in seconds.
        """
        safe_reason = self.sanitize(reason)
        with self._lock:
            now = self._clock()
            entry = self._keys[lease.index]
            if not lease._released:
                lease._released = True
                entry.in_flight = max(0, entry.in_flight - 1)

            if project_id and not entry.project_id:
                entry.project_id = project_id

            entry.failure_count += 1
            self._total_failures += 1

            if is_quota_exhausted:
                entry.quota_exhaustion_count += 1
                self._total_quota_exhaustions += 1
                category = "quota_exhausted"
            else:
                entry.rate_limit_count += 1
                self._total_rate_limits += 1
                category = "rate_limit"

            # Avoid compounding exponent multiple times for the same concurrent burst
            already_cooled_this_wave = (
                entry.status == KeyStatus.COOLDOWN and entry.last_cooldown_started_at >= lease.acquired_at
            )

            if not already_cooled_this_wave:
                entry.consecutive_rate_limits += 1

            if is_quota_exhausted:
                base_cd = self._config.quota_cooldown_seconds
                computed = base_cd * (1.0 + self._config.jitter_ratio * self._rng())
            else:
                exp_step = max(0, entry.consecutive_rate_limits - 1)
                raw_cd = min(self._config.max_cooldown_seconds, self._config.base_cooldown_seconds * (2 ** exp_step))
                computed = raw_cd + (raw_cd * self._config.jitter_ratio * self._rng())

            if retry_after is not None and retry_after > 0:
                computed = max(computed, float(retry_after))

            new_until = now + computed
            if new_until > entry.cooldown_until:
                entry.cooldown_until = new_until
                entry.cooldown_until_utc = self._now_utc_iso(computed)
                entry.last_cooldown_started_at = now
            entry.status = KeyStatus.COOLDOWN
            entry.last_error_category = category
            entry.last_error_reason = safe_reason[:300]

            effective_project = project_id or entry.project_id
            if effective_project:
                existing_proj_until = self._project_cooldowns.get(effective_project, 0.0)
                if new_until > existing_proj_until:
                    self._project_cooldowns[effective_project] = new_until

            self._sync_redis_cooldown_write(entry, computed, project_id=effective_project)

            logger.warning(
                "[GeminiKeyManager] %s entered COOLDOWN for %.1fs (category=%s, streak=%d, project=%s, reason=%s)",
                entry.label,
                computed,
                category,
                entry.consecutive_rate_limits,
                effective_project or "unscoped",
                safe_reason[:200],
            )
            return computed

    def record_transient_failure(self, lease: KeyLease, reason: str) -> Optional[float]:
        """
        Record a temporary API / network failure (5xx, timeout, connection reset).
        Applies a short cooldown only after `transient_failure_threshold` consecutive errors
        so brief network blips don't unnecessarily bench the primary key.
        Returns cooldown seconds if cooldown was triggered, else None.
        """
        safe_reason = self.sanitize(reason)
        with self._lock:
            now = self._clock()
            entry = self._keys[lease.index]
            if not lease._released:
                lease._released = True
                entry.in_flight = max(0, entry.in_flight - 1)

            entry.failure_count += 1
            entry.transient_error_count += 1
            entry.consecutive_transient_failures += 1
            entry.last_error_category = "transient_error"
            entry.last_error_reason = safe_reason[:300]
            self._total_failures += 1
            self._total_transient_errors += 1

            if entry.consecutive_transient_failures >= self._config.transient_failure_threshold:
                over = entry.consecutive_transient_failures - self._config.transient_failure_threshold
                raw_cd = min(self._config.max_cooldown_seconds, self._config.transient_cooldown_seconds * (2 ** over))
                cooldown = raw_cd + (raw_cd * self._config.jitter_ratio * self._rng())
                new_until = now + cooldown
                if new_until > entry.cooldown_until:
                    entry.cooldown_until = new_until
                    entry.cooldown_until_utc = self._now_utc_iso(cooldown)
                    entry.last_cooldown_started_at = now
                entry.status = KeyStatus.COOLDOWN
                self._sync_redis_cooldown_write(entry, cooldown)
                logger.warning(
                    "[GeminiKeyManager] %s reached %d consecutive transient failures; entering COOLDOWN for %.1fs (reason=%s)",
                    entry.label,
                    entry.consecutive_transient_failures,
                    cooldown,
                    safe_reason[:200],
                )
                return cooldown

            logger.warning(
                "[GeminiKeyManager] Transient error on %s (%d/%d before cooldown; reason=%s)",
                entry.label,
                entry.consecutive_transient_failures,
                self._config.transient_failure_threshold,
                safe_reason[:200],
            )
            return None

    def next_recovery_in_seconds(self) -> Optional[float]:
        """
        Return seconds until the soonest cooled-down key becomes eligible again,
        or 0.0 if a key is currently available, or None if all keys are invalid/unconfigured.
        """
        with self._lock:
            if not self._keys:
                return None

            now = self._clock()
            soonest: Optional[float] = None
            for entry in self._keys:
                if entry.status == KeyStatus.INVALID:
                    continue
                self._refresh_entry_state_locked(entry, now)
                key_wait = max(0.0, entry.cooldown_until - now) if entry.status == KeyStatus.COOLDOWN else 0.0
                proj_blocked, proj_wait = self._is_project_in_cooldown_locked(entry.project_id, now)
                effective_wait = max(key_wait, proj_wait if proj_blocked else 0.0)
                if effective_wait == 0.0:
                    return 0.0
                if soonest is None or effective_wait < soonest:
                    soonest = effective_wait
            return soonest

    def has_eligible_key(self, excluded_indices: Optional[Set[int]] = None) -> bool:
        """Check whether at least one key (not in excluded_indices) is currently eligible."""
        excluded = excluded_indices or set()
        with self._lock:
            now = self._clock()
            for entry in self._keys:
                if entry.index in excluded or entry.status == KeyStatus.INVALID:
                    continue
                self._refresh_entry_state_locked(entry, now)
                if entry.status != KeyStatus.AVAILABLE:
                    continue
                proj_blocked, _ = self._is_project_in_cooldown_locked(entry.project_id, now)
                if not proj_blocked:
                    return True
            return False

    def get_status_snapshot(self) -> Dict[str, Any]:
        """
        Return a non-sensitive diagnostic snapshot of key pool health and usage metrics.
        Safe to expose in Admin observability endpoints and operational logs.
        """
        with self._lock:
            now = self._clock()
            available_count = 0
            cooldown_count = 0
            invalid_count = 0
            active_key_label: Optional[str] = None
            primary_available = False
            keys_summary: List[Dict[str, Any]] = []

            for entry in self._keys:
                self._refresh_entry_state_locked(entry, now)
                proj_blocked, proj_wait = self._is_project_in_cooldown_locked(entry.project_id, now)

                if entry.status == KeyStatus.INVALID:
                    effective_status = KeyStatus.INVALID.value
                    cooldown_remaining = 0.0
                    invalid_count += 1
                elif entry.status == KeyStatus.COOLDOWN or proj_blocked:
                    effective_status = KeyStatus.COOLDOWN.value
                    key_wait = max(0.0, entry.cooldown_until - now) if entry.status == KeyStatus.COOLDOWN else 0.0
                    cooldown_remaining = round(max(key_wait, proj_wait if proj_blocked else 0.0), 2)
                    cooldown_count += 1
                else:
                    effective_status = KeyStatus.AVAILABLE.value
                    cooldown_remaining = 0.0
                    available_count += 1
                    if active_key_label is None:
                        active_key_label = entry.label
                    if entry.is_primary:
                        primary_available = True

                keys_summary.append(
                    {
                        "index": entry.index,
                        "label": entry.label,
                        "is_primary": entry.is_primary,
                        "project_id": entry.project_id,
                        "status": effective_status,
                        "cooldown_remaining_seconds": cooldown_remaining,
                        "cooldown_until_utc": entry.cooldown_until_utc if effective_status == KeyStatus.COOLDOWN.value else None,
                        "in_flight": entry.in_flight,
                        "consecutive_rate_limits": entry.consecutive_rate_limits,
                        "consecutive_transient_failures": entry.consecutive_transient_failures,
                        "total_requests": entry.total_requests,
                        "success_count": entry.success_count,
                        "failure_count": entry.failure_count,
                        "rate_limit_count": entry.rate_limit_count,
                        "quota_exhaustion_count": entry.quota_exhaustion_count,
                        "transient_error_count": entry.transient_error_count,
                        "invalid_error_count": entry.invalid_error_count,
                        "total_prompt_tokens": entry.total_prompt_tokens,
                        "total_output_tokens": entry.total_output_tokens,
                        "last_error_category": entry.last_error_category,
                        "last_used_at": entry.last_used_at,
                        "last_success_at": entry.last_success_at,
                    }
                )

            next_recovery = self.next_recovery_in_seconds()
            if not self._keys:
                pool_health = "unconfigured"
            elif available_count > 0:
                pool_health = "healthy" if primary_available else "failover_active"
            elif cooldown_count > 0:
                pool_health = "cooldown"
            else:
                pool_health = "exhausted"

            return {
                "configured": bool(self._keys),
                "health": pool_health,
                "total_keys": len(self._keys),
                "available_keys": available_count,
                "cooldown_keys": cooldown_count,
                "invalid_keys": invalid_count,
                "primary_key_available": primary_available,
                "active_key_label": active_key_label,
                "next_recovery_in_seconds": round(next_recovery, 2) if next_recovery is not None else None,
                "config": {
                    "base_cooldown_seconds": self._config.base_cooldown_seconds,
                    "max_cooldown_seconds": self._config.max_cooldown_seconds,
                    "quota_cooldown_seconds": self._config.quota_cooldown_seconds,
                    "transient_cooldown_seconds": self._config.transient_cooldown_seconds,
                    "transient_failure_threshold": self._config.transient_failure_threshold,
                    "max_concurrent_requests": self._config.max_concurrent_requests,
                    "max_transient_retries_per_key": self._config.max_transient_retries_per_key,
                },
                "totals": {
                    "requests": self._total_requests,
                    "successes": self._total_successes,
                    "failures": self._total_failures,
                    "retries": self._total_retries,
                    "rotations": self._total_rotations,
                    "rate_limits": self._total_rate_limits,
                    "quota_exhaustions": self._total_quota_exhaustions,
                    "transient_errors": self._total_transient_errors,
                    "invalid_key_errors": self._total_invalid_key_errors,
                },
                "keys": keys_summary,
            }
