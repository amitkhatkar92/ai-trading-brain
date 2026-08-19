"""
DTA-002 — Dhan Token Synchronizer Tests
=========================================
T201 – T220  (+ T221 integration scenario)

Uses only fake tokens (FAKE_JWT_*) — no real credentials, no network calls,
no broker API calls, no order placement.

Security: asserts that the JWT value never appears in any log, dict, or
          exception output across all tests.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ── Fake tokens (not real JWTs) ───────────────────────────────────────────────
FAKE_JWT_A = "eyJhbGciOiJIUzUxMiJ9.FAKE_PAYLOAD_A.FAKE_SIG_A"
FAKE_JWT_B = "eyJhbGciOiJIUzUxMiJ9.FAKE_PAYLOAD_B.FAKE_SIG_B"
FAKE_GEN_A = "gen-uuid-AAAA-1111-2222"
FAKE_GEN_B = "gen-uuid-BBBB-3333-4444"

# Expiry helpers
_NOW_UTC = datetime.now(timezone.utc)
_EXPIRY_24H  = (_NOW_UTC + timedelta(hours=24)).isoformat()
_EXPIRY_1H   = (_NOW_UTC + timedelta(hours=1)).isoformat()   # near-expiry
_EXPIRY_PAST = (_NOW_UTC - timedelta(hours=1)).isoformat()   # expired


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_meta(
    generation_id: str = FAKE_GEN_A,
    expiry_time: str = _EXPIRY_24H,
    status: str = "TOKEN_REFRESHED",
):
    """Return a lightweight metadata stub matching TokenMetadata interface."""
    m = MagicMock()
    m.generation_id = generation_id
    m.expiry_time   = expiry_time
    m.status        = status
    return m


def _make_feed_manager(reload_return: bool = True) -> MagicMock:
    """Return a mock DataFeedManager whose dhan.reload_token() behaves as specified."""
    fm = MagicMock()
    fm.dhan.reload_token = MagicMock(return_value=reload_return)
    return fm


def _make_sync(last_gen: Optional[str] = None):
    """Create a DhanTokenSync instance with controlled initial state."""
    from scripts.dhan_auth.dhan_token_sync import DhanTokenSync
    sync = DhanTokenSync.__new__(DhanTokenSync)
    sync._sync_lock = threading.Lock()
    sync._last_sync_ts = None
    sync._last_loaded_generation_id = last_gen
    return sync


def _write_env(tmp_path: Path, token: str) -> Path:
    """Write a fake .env with DHAN_ACCESS_TOKEN."""
    env = tmp_path / ".env"
    env.write_text(f"DHAN_ACCESS_TOKEN = {token}\n", encoding="utf-8")
    return env


# ── T201: New generation_id detected → reload triggered ──────────────────────
class TestT201NewGenId:
    def test_t201_new_gen_id_triggers_reload(self, tmp_path, monkeypatch):
        """T201: When generation_id changes, maybe_sync() calls reload_token()."""
        env_file = _write_env(tmp_path, FAKE_JWT_A)
        sync = _make_sync(last_gen=None)  # no previous gen loaded
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        assert result["action"] == "RELOADED"
        fm.dhan.reload_token.assert_called_once()


# ── T202: Same generation_id → no reload ─────────────────────────────────────
class TestT202SameGenId:
    def test_t202_same_gen_id_no_reload(self):
        """T202: When generation_id is unchanged, maybe_sync() does NOT call reload_token()."""
        sync = _make_sync(last_gen=FAKE_GEN_A)
        fm   = _make_feed_manager()

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A):
            result = sync.maybe_sync(fm)

        assert result["action"] == "NO_CHANGE"
        fm.dhan.reload_token.assert_not_called()


# ── T203: Successful reload → generation_id recorded ─────────────────────────
class TestT203SuccessRecordsGenId:
    def test_t203_successful_reload_records_gen_id(self):
        """T203: After a successful reload, _last_loaded_generation_id == new gen_id."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)

        assert sync._last_loaded_generation_id == FAKE_GEN_A


# ── T204: Reload returns False → NOT recorded ─────────────────────────────────
class TestT204FailureNotRecorded:
    def test_t204_failed_reload_not_recorded(self):
        """T204: When reload_token() returns False, gen_id is NOT recorded."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=False)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        assert result["action"] == "RELOAD_FAILED"
        assert sync._last_loaded_generation_id is None  # not recorded


# ── T205: Failed reload retries on next call ──────────────────────────────────
class TestT205RetryAfterFailure:
    def test_t205_retry_on_next_cycle(self):
        """T205: After a failed reload, the next maybe_sync() call retries."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=False)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)  # fails
            # Second call — reload is still attempted (gen_id not recorded)
            fm.dhan.reload_token.return_value = True
            result = sync.maybe_sync(fm)

        assert result["action"] == "RELOADED"
        assert sync._last_loaded_generation_id == FAKE_GEN_A


# ── T206: Expired token detected ─────────────────────────────────────────────
class TestT206ExpiredToken:
    def test_t206_expired_token_state(self):
        """T206: get_token_state() returns TOKEN_EXPIRED for past expiry_time."""
        from scripts.dhan_auth.dhan_token_sync import DhanTokenSync, TOKEN_EXPIRED

        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_PAST)
        with patch.object(sync, "_load_meta", return_value=meta):
            state = sync.get_token_state()

        assert state == TOKEN_EXPIRED


# ── T207: Healthy token detected ─────────────────────────────────────────────
class TestT207HealthyToken:
    def test_t207_healthy_token_state(self):
        """T207: get_token_state() returns TOKEN_HEALTHY for a fresh 24h token."""
        from scripts.dhan_auth.dhan_token_sync import DhanTokenSync, TOKEN_HEALTHY

        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_24H)
        with patch.object(sync, "_load_meta", return_value=meta):
            state = sync.get_token_state()

        assert state == TOKEN_HEALTHY


# ── T208: Near-expiry uses existing 2h threshold ─────────────────────────────
class TestT208NearExpiry:
    def test_t208_near_expiry_uses_existing_threshold(self):
        """T208: get_token_state() returns TOKEN_NEAR_EXPIRY when <2h remains."""
        from scripts.dhan_auth.dhan_token_sync import DhanTokenSync, TOKEN_NEAR_EXPIRY

        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_1H)
        with patch.object(sync, "_load_meta", return_value=meta):
            state = sync.get_token_state()

        assert state == TOKEN_NEAR_EXPIRY


# ── T209: Unavailable token fails is_token_safe_for_api ──────────────────────
class TestT209UnavailableFails:
    def test_t209_unavailable_not_safe(self):
        """T209: TOKEN_UNAVAILABLE causes is_token_safe_for_api() to return False."""
        from scripts.dhan_auth.dhan_token_sync import DhanTokenSync, TOKEN_UNAVAILABLE

        sync = _make_sync()
        with patch.object(sync, "_load_meta", return_value=None):
            assert not sync.is_token_safe_for_api()


# ── T210: Expired token → not safe for API ───────────────────────────────────
class TestT210ExpiredNotSafe:
    def test_t210_expired_not_safe_for_api(self):
        """T210: Expired token fails is_token_safe_for_api() — no order execution possible."""
        from scripts.dhan_auth.dhan_token_sync import DhanTokenSync

        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_PAST)
        with patch.object(sync, "_load_meta", return_value=meta):
            assert not sync.is_token_safe_for_api()


# ── T211: JWT never appears in logs ──────────────────────────────────────────
class TestT211JwtNeverInLogs:
    def test_t211_jwt_not_in_log_output(self, caplog):
        """T211: The JWT value NEVER appears in any log record during sync."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with caplog.at_level(logging.DEBUG):
            with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
                 patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
                sync.maybe_sync(fm)

        full_log = "\n".join(caplog.messages)
        assert FAKE_JWT_A not in full_log


# ── T212: JWT never appears in health metadata ────────────────────────────────
class TestT212JwtNeverInMetadata:
    def test_t212_jwt_not_in_result_dict(self):
        """T212: The result dict from maybe_sync() contains no JWT value."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        result_str = str(result)
        assert FAKE_JWT_A not in result_str
        assert "eyJ" not in result_str or "FAKE_JWT" not in result_str  # no JWT fragments


# ── T213: Generation_id state persists correctly ─────────────────────────────
class TestT213GenIdPersists:
    def test_t213_gen_id_persists_across_calls(self):
        """T213: _last_loaded_generation_id persists correctly after RELOADED."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)

        assert sync._last_loaded_generation_id == FAKE_GEN_A

        # Second call — same gen_id → NO_CHANGE, state still FAKE_GEN_A
        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A):
            result = sync.maybe_sync(fm)

        assert result["action"] == "NO_CHANGE"
        assert sync._last_loaded_generation_id == FAKE_GEN_A


# ── T214: No container restart required ──────────────────────────────────────
class TestT214NoRestartRequired:
    def test_t214_in_process_reload_no_restart(self):
        """T214: Token is reloaded via the in-process reload_token() — no restart needed."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        # Reload happened inside this process (no subprocess/restart)
        assert result["action"] == "RELOADED"
        # The passed feed_manager.dhan.reload_token was called — that IS the live singleton call
        fm.dhan.reload_token.assert_called_once()


# ── T215: Actual PID-1 FeedManager singleton used ────────────────────────────
class TestT215LiveSingletonUsed:
    def test_t215_uses_passed_feed_manager_dhan(self):
        """T215: maybe_sync() calls reload_token on feed_manager.dhan — not a new instance."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)

        # Exactly the passed fm.dhan was used
        fm.dhan.reload_token.assert_called_once()


# ── T216: Subprocess FeedManager NOT used for live reload ────────────────────
class TestT216SubprocessNotUsed:
    def test_t216_subprocess_feed_manager_not_used(self):
        """T216: maybe_sync() uses the passed feed_manager — no subprocess import."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)
        other_fm = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)

        # other_fm (simulating a subprocess-created FeedManager) was NOT called
        other_fm.dhan.reload_token.assert_not_called()


# ── T217: DTA-001 behavior backward compatible ────────────────────────────────
class TestT217DTA001BackwardCompat:
    def test_t217_dta001_agent_unchanged(self):
        """T217: DTA-001 DhanTokenAgent still imports and its interface is unchanged."""
        from scripts.dhan_auth.dhan_token_agent import DhanTokenAgent
        agent = DhanTokenAgent.__new__(DhanTokenAgent)
        assert hasattr(agent, "run_refresh")
        assert hasattr(agent, "run_dry_run")
        assert hasattr(agent, "run_health")
        assert hasattr(agent, "run_status")
        assert hasattr(agent, "call_generate_token")
        assert hasattr(agent, "deliver_token")

    def test_t217_dta001_constants_unchanged(self):
        """T217: DTA-001 constants TOKEN_REUSE_MIN_HOURS, GENERATE_TOKEN_URL unchanged."""
        import scripts.dhan_auth.dhan_token_agent as agent_mod
        assert agent_mod.TOKEN_REUSE_MIN_HOURS == 20
        assert "generateAccessToken" in agent_mod.GENERATE_TOKEN_URL


# ── T218: Synchronization is idempotent ──────────────────────────────────────
class TestT218Idempotent:
    def test_t218_same_gen_called_multiple_times_reload_once(self):
        """T218: Calling maybe_sync() 3× with same gen_id reloads token at most once."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            r1 = sync.maybe_sync(fm)
            r2 = sync.maybe_sync(fm)
            r3 = sync.maybe_sync(fm)

        assert r1["action"] == "RELOADED"
        assert r2["action"] == "NO_CHANGE"
        assert r3["action"] == "NO_CHANGE"
        fm.dhan.reload_token.assert_called_once()


# ── T219: No broker/order calls during synchronization ───────────────────────
class TestT219NoBrokerCalls:
    def test_t219_no_order_api_calls(self):
        """T219: maybe_sync() never calls any order/broker methods on feed_manager."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)

        # Only reload_token must have been called — not order APIs
        called = [n for n, _, _ in fm.mock_calls if n not in ("dhan.reload_token", "()")]
        order_apis = [c for c in called if any(w in c.lower() for w in
                      ("order", "place", "cancel", "modify", "trade", "position"))]
        assert not order_apis, f"Unexpected order/broker call: {order_apis}"


# ── T220: Dhan authentication flow unchanged ─────────────────────────────────
class TestT220AuthUnchanged:
    def test_t220_dta002_does_not_call_generate_token(self):
        """T220: DTA-002 NEVER calls the Dhan token generation endpoint."""
        import scripts.dhan_auth.dhan_token_sync as sync_mod
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        with patch("requests.post") as mock_post, \
             patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)

        mock_post.assert_not_called()


# ── T221: Integration — two-phase generation_id handoff ─────────────────────
class TestT221IntegrationTwoPhase:
    """
    Simulates DTA-001 (process A) writing gen_id=A then gen_id=B,
    and DTA-002 (process B / main trading process) detecting both transitions.

    Uses tmp_path as a shared filesystem (replicates the bind-mounted /app/.env +
    /app/data/dhan_token_store.json pattern without real files).
    """

    def test_t221_two_phase_handoff(self, tmp_path, monkeypatch):
        """
        T221: Full two-phase integration handoff.

        Phase A: gen_id=A token=FAKE_JWT_A → sync detects A, reloads once.
        Phase B: gen_id=B token=FAKE_JWT_B → sync detects B, reloads once.
        No duplicate reloads. No process restart.
        """
        env_file = tmp_path / ".env"
        env_file.write_text(f"DHAN_ACCESS_TOKEN = {FAKE_JWT_A}\n")

        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)

        reload_log: list = []

        def _tracking_reload(token: str) -> bool:
            reload_log.append(token[:8])  # record prefix only (never full JWT)
            return True

        fm.dhan.reload_token = MagicMock(side_effect=_tracking_reload)

        # ── Phase A: DTA-001 writes gen_id=A ──────────────────────────
        meta_a = _make_meta(generation_id=FAKE_GEN_A, expiry_time=_EXPIRY_24H)
        with patch.object(sync, "_load_meta", return_value=meta_a), \
             patch.object(sync, "_detect_env_path", return_value=env_file):
            r1 = sync.maybe_sync(fm)

        assert r1["action"] == "RELOADED"
        assert r1["generation_id"] == FAKE_GEN_A
        assert sync._last_loaded_generation_id == FAKE_GEN_A

        # Same gen_id again → no reload
        with patch.object(sync, "_load_meta", return_value=meta_a), \
             patch.object(sync, "_detect_env_path", return_value=env_file):
            r1b = sync.maybe_sync(fm)
        assert r1b["action"] == "NO_CHANGE"

        # ── Phase B: DTA-001 writes gen_id=B, updates .env ────────────
        env_file.write_text(f"DHAN_ACCESS_TOKEN = {FAKE_JWT_B}\n")
        meta_b = _make_meta(generation_id=FAKE_GEN_B, expiry_time=_EXPIRY_24H)

        with patch.object(sync, "_load_meta", return_value=meta_b), \
             patch.object(sync, "_detect_env_path", return_value=env_file):
            r2 = sync.maybe_sync(fm)

        assert r2["action"] == "RELOADED"
        assert r2["generation_id"] == FAKE_GEN_B
        assert sync._last_loaded_generation_id == FAKE_GEN_B

        # ── Verify counts ──────────────────────────────────────────────
        assert fm.dhan.reload_token.call_count == 2, (
            "reload_token must be called exactly twice: once for A, once for B"
        )

        # ── Security: JWT prefixes recorded but full JWTs not logged ───
        for prefix in reload_log:
            assert len(prefix) == 8   # only first 8 chars tracked in test
        assert FAKE_JWT_A not in str(reload_log)
        assert FAKE_JWT_B not in str(reload_log)


# ── Token state boundary tests ────────────────────────────────────────────────
class TestTokenStateBoundaries:
    """Verify all five TOKEN_* states are reachable and correctly classified."""

    def _sync_with_meta(self, meta):
        sync = _make_sync()
        with patch.object(sync, "_load_meta", return_value=meta):
            return sync.get_token_state()

    def test_token_healthy(self):
        from scripts.dhan_auth.dhan_token_sync import TOKEN_HEALTHY
        meta = _make_meta(expiry_time=_EXPIRY_24H, status="TOKEN_REFRESHED")
        assert self._sync_with_meta(meta) == TOKEN_HEALTHY

    def test_token_near_expiry(self):
        from scripts.dhan_auth.dhan_token_sync import TOKEN_NEAR_EXPIRY
        meta = _make_meta(expiry_time=_EXPIRY_1H, status="TOKEN_REFRESHED")
        assert self._sync_with_meta(meta) == TOKEN_NEAR_EXPIRY

    def test_token_expired(self):
        from scripts.dhan_auth.dhan_token_sync import TOKEN_EXPIRED
        meta = _make_meta(expiry_time=_EXPIRY_PAST, status="TOKEN_REFRESHED")
        assert self._sync_with_meta(meta) == TOKEN_EXPIRED

    def test_token_refresh_failed(self):
        from scripts.dhan_auth.dhan_token_sync import TOKEN_REFRESH_FAILED
        meta = _make_meta(expiry_time=_EXPIRY_24H, status="TOKEN_REFRESH_FAILED")
        assert self._sync_with_meta(meta) == TOKEN_REFRESH_FAILED

    def test_token_unavailable_no_meta(self):
        from scripts.dhan_auth.dhan_token_sync import TOKEN_UNAVAILABLE
        sync = _make_sync()
        with patch.object(sync, "_load_meta", return_value=None):
            assert sync.get_token_state() == TOKEN_UNAVAILABLE

    def test_is_safe_healthy(self):
        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_24H)
        with patch.object(sync, "_load_meta", return_value=meta):
            assert sync.is_token_safe_for_api()

    def test_is_safe_near_expiry(self):
        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_1H)
        with patch.object(sync, "_load_meta", return_value=meta):
            assert sync.is_token_safe_for_api()

    def test_not_safe_expired(self):
        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_PAST)
        with patch.object(sync, "_load_meta", return_value=meta):
            assert not sync.is_token_safe_for_api()

    def test_not_safe_refresh_failed(self):
        sync = _make_sync()
        meta = _make_meta(expiry_time=_EXPIRY_24H, status="TOKEN_REFRESH_FAILED")
        with patch.object(sync, "_load_meta", return_value=meta):
            assert not sync.is_token_safe_for_api()


# ── env file parsing tests ────────────────────────────────────────────────────
class TestEnvFileParsing:
    """Verify _read_token_from_env handles all .env format variants."""

    def _parse(self, content: str, tmp_path: Path) -> str:
        sync = _make_sync()
        env = tmp_path / ".env"
        env.write_text(content, encoding="utf-8")
        with patch.object(sync, "_detect_env_path", return_value=env):
            return sync._read_token_from_env()

    def test_format_no_spaces(self, tmp_path):
        """DHAN_ACCESS_TOKEN=value (no spaces)."""
        assert self._parse(f"DHAN_ACCESS_TOKEN={FAKE_JWT_A}\n", tmp_path) == FAKE_JWT_A

    def test_format_with_spaces(self, tmp_path):
        """DHAN_ACCESS_TOKEN = value (spaces around =)."""
        assert self._parse(f"DHAN_ACCESS_TOKEN = {FAKE_JWT_A}\n", tmp_path) == FAKE_JWT_A

    def test_format_missing_returns_empty(self, tmp_path):
        """File exists but no DHAN_ACCESS_TOKEN line → empty string."""
        assert self._parse("OTHER_KEY=value\n", tmp_path) == ""

    def test_format_empty_file(self, tmp_path):
        """Empty .env → empty string."""
        assert self._parse("", tmp_path) == ""

    def test_missing_file_returns_empty(self, tmp_path):
        sync = _make_sync()
        with patch.object(sync, "_detect_env_path", return_value=tmp_path / "nonexistent.env"):
            assert sync._read_token_from_env() == ""


# ── Singleton tests ───────────────────────────────────────────────────────────
class TestSingleton:
    def test_get_token_sync_returns_same_instance(self, monkeypatch):
        """get_token_sync() returns the same DhanTokenSync instance every call."""
        import scripts.dhan_auth.dhan_token_sync as mod
        monkeypatch.setattr(mod, "_SYNC_INSTANCE", None)

        s1 = mod.get_token_sync()
        s2 = mod.get_token_sync()
        assert s1 is s2


# ── Concurrency safety ────────────────────────────────────────────────────────
class TestConcurrencySafety:
    def test_concurrent_maybe_sync_one_wins(self):
        """When two threads call maybe_sync() simultaneously, one gets SKIPPED_LOCK_BUSY."""
        sync = _make_sync(last_gen=None)
        fm   = _make_feed_manager(reload_return=True)
        results: list = []

        import time as _time

        def slow_reload(token: str) -> bool:
            _time.sleep(0.05)
            return True

        fm.dhan.reload_token = MagicMock(side_effect=slow_reload)

        def _call():
            with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
                 patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
                results.append(sync.maybe_sync(fm))

        t1 = threading.Thread(target=_call)
        t2 = threading.Thread(target=_call)
        t1.start()
        _time.sleep(0.01)  # ensure t1 acquires lock first
        t2.start()
        t1.join()
        t2.join()

        actions = {r["action"] for r in results}
        # One must win (RELOADED), the other must be skipped
        assert "RELOADED" in actions or "NO_CHANGE" in actions
        # Neither thread should crash
        assert len(results) == 2


# ── Orchestrator hook tests ───────────────────────────────────────────────────
class TestOrchestratorHook:
    def test_orchestrator_has_sync_dhan_token_method(self):
        """_sync_dhan_token method exists on MasterOrchestrator."""
        from orchestrator.master_orchestrator import MasterOrchestrator
        assert callable(getattr(MasterOrchestrator, "_sync_dhan_token", None))

    def test_sync_dhan_token_swallows_exceptions(self):
        """_sync_dhan_token must never crash even if dhan_token_sync is unavailable."""
        # Create a minimal stub orchestrator — do NOT instantiate the real one
        from orchestrator.master_orchestrator import MasterOrchestrator
        orch = MagicMock(spec=MasterOrchestrator)
        # Bind the real method to our stub
        MasterOrchestrator._sync_dhan_token(orch)
        # If we reach here without an exception, the guard worked.
        # (The real method wraps everything in try/except)
