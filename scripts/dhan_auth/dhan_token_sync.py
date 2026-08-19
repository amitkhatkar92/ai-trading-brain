"""
DTA-002 — Main-Process Dhan Token Synchronizer
================================================
Runs inside the PID-1 trading process (not in a docker exec subprocess).

Periodically compares the DTA-001 generation_id (from token metadata) against
the last generation_id successfully loaded by THIS process.

If the generation_id has changed:
  1. Read the new JWT from .env (never logged)
  2. Call DhanFeed.reload_token() on the live DataFeedManager singleton
  3. If success — record the generation_id as loaded
  4. If failure — do NOT record it; retry on the next scheduled cycle

Security invariants:
  - JWT is NEVER logged, stored in any JSON/CSV, or included in exceptions.
  - Only metadata (generation_id, expiry_time, status) crosses module boundaries.
  - .env is read in-process; the token value is passed directly to reload_token()
    and then deleted from the local scope.

Thread safety:
  - _sync_lock guards maybe_sync() so concurrent callers (scheduler + Telegram
    /token command) never race on token state.

Architecture:
  DTA-001 (docker exec subprocess)
      ↓ writes JWT to /app/.env
      ↓ writes new generation_id to dhan_token_store.json

  DTA-002 (this module — PID-1 trading process)
      ← detects changed generation_id
      ← reads JWT from /app/.env
      → calls feed_manager.dhan.reload_token(jwt)
      → records generation_id as loaded
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# ── Token state constants ─────────────────────────────────────────────────────
TOKEN_HEALTHY         = "TOKEN_HEALTHY"        # valid, ≥2 h remaining
TOKEN_NEAR_EXPIRY     = "TOKEN_NEAR_EXPIRY"    # valid, <2 h remaining
TOKEN_EXPIRED         = "TOKEN_EXPIRED"        # exp < now
TOKEN_REFRESH_FAILED  = "TOKEN_REFRESH_FAILED" # last DTA-001 run failed
TOKEN_UNAVAILABLE     = "TOKEN_UNAVAILABLE"    # no metadata or unreadable expiry

# Mirrors dhan_token_health.TOKEN_EXPIRY_WARN_H — do not invent a new threshold
_NEAR_EXPIRY_HOURS: float = 2.0

# ── Module-level process singleton ───────────────────────────────────────────
_SYNC_INSTANCE: Optional["DhanTokenSync"] = None
_SINGLETON_LOCK = threading.Lock()


def get_token_sync() -> "DhanTokenSync":
    """Return the process-level DhanTokenSync singleton (lazy-created, thread-safe)."""
    global _SYNC_INSTANCE
    if _SYNC_INSTANCE is None:
        with _SINGLETON_LOCK:
            if _SYNC_INSTANCE is None:
                _SYNC_INSTANCE = DhanTokenSync()
    return _SYNC_INSTANCE


# ── Synchronizer ─────────────────────────────────────────────────────────────

class DhanTokenSync:
    """
    DTA-002: Main-process Dhan token lifecycle synchronizer.

    Instantiate once per process via get_token_sync().
    Call maybe_sync(feed_manager) from any periodic task; it is idempotent.
    """

    def __init__(self) -> None:
        self._sync_lock = threading.Lock()
        self._last_sync_ts: Optional[float] = None
        # Pre-populate with the generation_id already loaded at process startup,
        # so the first sync cycle does NOT unnecessarily reload the token.
        self._last_loaded_generation_id: Optional[str] = self._read_current_generation_id()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_token_state(self) -> str:
        """
        Classify token health from metadata only — JWT never needed here.

        Returns one of the TOKEN_* constants defined in this module.
        """
        meta = self._load_meta()
        if meta is None:
            return TOKEN_UNAVAILABLE

        # Import status constant without dragging in the full agent module
        try:
            from scripts.dhan_auth.dhan_token_store import STATUS_TOKEN_REFRESH_FAILED
        except ImportError:
            try:
                from dhan_token_store import STATUS_TOKEN_REFRESH_FAILED  # type: ignore[no-redef]
            except ImportError:
                STATUS_TOKEN_REFRESH_FAILED = "TOKEN_REFRESH_FAILED"

        if meta.status == STATUS_TOKEN_REFRESH_FAILED:
            return TOKEN_REFRESH_FAILED

        if not getattr(meta, "expiry_time", ""):
            return TOKEN_UNAVAILABLE

        try:
            exp = datetime.fromisoformat(meta.expiry_time)
            now = datetime.now(timezone.utc)
            # If expiry has no timezone info, Dhan docs say times are IST (+05:30)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            hours_left = (exp - now).total_seconds() / 3600
        except Exception:
            return TOKEN_UNAVAILABLE

        if hours_left <= 0:
            return TOKEN_EXPIRED
        if hours_left <= _NEAR_EXPIRY_HOURS:
            return TOKEN_NEAR_EXPIRY
        return TOKEN_HEALTHY

    def is_token_safe_for_api(self) -> bool:
        """
        Return True only when the token exists and has not expired.

        Call this before initiating any Dhan API operation.
        Returns False for TOKEN_EXPIRED, TOKEN_UNAVAILABLE, TOKEN_REFRESH_FAILED.
        Returns True for TOKEN_HEALTHY and TOKEN_NEAR_EXPIRY.
        """
        return self.get_token_state() in (TOKEN_HEALTHY, TOKEN_NEAR_EXPIRY)

    def maybe_sync(self, feed_manager: Any) -> Dict[str, Any]:
        """
        Detect a new DTA-001 generation_id and, if changed, hot-swap the token.

        Behaviour:
          - unchanged generation_id → returns {"action": "NO_CHANGE", ...}
          - new generation_id + reload success → records it; returns {"action": "RELOADED"}
          - new generation_id + reload failure → does NOT record; returns {"action": "RELOAD_FAILED"}
            so the next scheduled call retries automatically.

        Args:
            feed_manager: The live DataFeedManager singleton (from get_feed_manager()).
                          Expected: feed_manager.dhan.reload_token(str) -> bool

        Returns:
            Sanitised status dict. NEVER contains the JWT string.

        Thread-safe: uses _sync_lock; concurrent caller skips gracefully.
        """
        if not self._sync_lock.acquire(blocking=False):
            return {"action": "SKIPPED_LOCK_BUSY"}
        try:
            return self._do_sync(feed_manager)
        finally:
            self._sync_lock.release()

    # ── Internal implementation ───────────────────────────────────────────────

    def _do_sync(self, feed_manager: Any) -> Dict[str, Any]:
        self._last_sync_ts = time.monotonic()

        # Step 1: read current generation_id (no JWT)
        current_gen_id = self._read_current_generation_id()
        if current_gen_id is None:
            return {"action": "NO_METADATA"}

        # Step 2: compare against last-loaded
        if current_gen_id == self._last_loaded_generation_id:
            return {"action": "NO_CHANGE", "generation_id": current_gen_id}

        # Step 3: new token available — read from .env (never log)
        new_token = self._read_token_from_env()
        if not new_token:
            return {
                "action": "TOKEN_UNREADABLE",
                "generation_id": current_gen_id,
                "error": "DHAN_ACCESS_TOKEN absent or empty in .env",
            }

        # Step 4: call reload_token() on the ACTUAL live DhanFeed singleton
        try:
            success = feed_manager.dhan.reload_token(new_token)
        except Exception as exc:
            # Never include new_token in the exception report
            return {
                "action": "RELOAD_FAILED",
                "generation_id": current_gen_id,
                "error": f"reload_token raised {type(exc).__name__}",
            }
        finally:
            del new_token  # discard immediately after use

        if not success:
            return {
                "action": "RELOAD_FAILED",
                "generation_id": current_gen_id,
                "error": "reload_token() returned False — DhanFeed reconnect failed",
            }

        # Step 5: success — record as loaded so we don't reload on next cycle
        self._last_loaded_generation_id = current_gen_id
        return {"action": "RELOADED", "generation_id": current_gen_id}

    def _read_current_generation_id(self) -> Optional[str]:
        """Read generation_id from token metadata store. Returns None on any failure."""
        meta = self._load_meta()
        if meta is None:
            return None
        gen_id = getattr(meta, "generation_id", "") or ""
        return gen_id if gen_id else None

    def _load_meta(self):
        """Load TokenMetadata from store. Returns None on failure (never raises)."""
        try:
            from scripts.dhan_auth.dhan_token_store import load_metadata
        except ImportError:
            try:
                from dhan_token_store import load_metadata  # type: ignore[no-redef]
            except ImportError:
                return None
        try:
            return load_metadata()
        except Exception:
            return None

    def _read_token_from_env(self) -> str:
        """
        Parse DHAN_ACCESS_TOKEN from the .env file directly.

        Does NOT use os.environ — the running process may still have the OLD
        token there. Reads the file that DTA-001 just updated.

        Returns the JWT string, or "" if not found.
        NEVER logs or propagates the return value.
        """
        env_path = self._detect_env_path()
        if not env_path.exists():
            return ""
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("DHAN_ACCESS_TOKEN"):
                    # Handles both: "DHAN_ACCESS_TOKEN=val" and "DHAN_ACCESS_TOKEN = val"
                    _, _, val = stripped.partition("=")
                    token = val.strip().strip('"').strip("'")
                    return token
        except Exception:
            pass
        return ""

    def _detect_env_path(self) -> Path:
        """Locate .env — same logic as dhan_token_agent._detect_env_path."""
        explicit = os.getenv("DHAN_ENV_PATH", "").strip()
        if explicit:
            return Path(explicit)
        container_path = Path("/app/.env")
        if container_path.exists() or os.getenv("RUNNING_IN_DOCKER") == "1":
            return container_path
        return Path(__file__).resolve().parent.parent.parent / ".env"
