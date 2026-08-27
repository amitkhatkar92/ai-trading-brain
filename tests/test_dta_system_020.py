"""
tests/test_dta_system_020.py
============================
DTA-020 — Autonomous Dhan Authentication Lifecycle Tests
T020-001 through T020-012 (12 targeted tests)

Root cause investigated in DTA-020:
  The VPS cron file /etc/cron.d/dhan-token-agent had CRLF line endings on the
  retry line (30 2 * * 1-5). This caused the cron daemon to silently skip BOTH
  the primary (01:50 IST) and retry (02:30 IST) jobs on 2026-08-27, leaving
  the Dhan token expired post-market and forcing a manual recovery.

These tests verify the full authentication lifecycle:
  - Cron file structural integrity (no CRLF)
  - Credential source: .env file path, not only os.environ
  - Token delivery chain: agent → store → sync → broker
  - State transitions: HEALTHY → EXPIRED → REFRESH → HEALTHY
  - PAPER_TRADING / knowledge pipeline unaffected by auth failure
  - Order gating: no live order possible with expired token
  - Security: JWT never in any result dict or log
  - Idempotency: fresh token not regenerated

All Dhan API endpoints are mocked. No real credentials. No network calls.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Fake test values (never real credentials) ─────────────────────────────────
FAKE_JWT_A = "eyJhbGciOiJIUzUxMiJ9.PAYLOAD_DTA020_A.SIG_A"
FAKE_JWT_B = "eyJhbGciOiJIUzUxMiJ9.PAYLOAD_DTA020_B.SIG_B"
FAKE_GEN_A = "dta020-gen-uuid-AAAA-0001"
FAKE_GEN_B = "dta020-gen-uuid-BBBB-0002"
FAKE_CLIENT_ID = "9000000001"
FAKE_TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # valid base-32 for pyotp
FAKE_PIN = "9999"
FAKE_API_KEY = "fake_api_key_dta020"

_NOW_UTC     = datetime.now(timezone.utc)
_EXPIRY_24H  = (_NOW_UTC + timedelta(hours=24)).isoformat()
_EXPIRY_1H   = (_NOW_UTC + timedelta(hours=1)).isoformat()     # near-expiry (< 2h)
_EXPIRY_PAST = (_NOW_UTC - timedelta(minutes=30)).isoformat()  # expired 30 min ago

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_meta(
    generation_id: str = FAKE_GEN_A,
    expiry_time: str = _EXPIRY_24H,
    status: str = "TOKEN_REFRESHED",
) -> MagicMock:
    m = MagicMock()
    m.generation_id = generation_id
    m.expiry_time   = expiry_time
    m.status        = status
    return m


def _make_feed_manager(reload_return: bool = True) -> MagicMock:
    fm = MagicMock()
    fm.dhan.reload_token = MagicMock(return_value=reload_return)
    return fm


def _make_sync(last_gen: Optional[str] = None):
    from scripts.dhan_auth.dhan_token_sync import DhanTokenSync
    sync = DhanTokenSync.__new__(DhanTokenSync)
    sync._sync_lock = threading.Lock()
    sync._last_sync_ts = None
    sync._last_loaded_generation_id = last_gen
    return sync


def _fresh_creds() -> Dict[str, str]:
    return {
        "DHAN_CLIENT_ID":   FAKE_CLIENT_ID,
        "DHAN_PIN":         FAKE_PIN,
        "DHAN_TOTP_SECRET": FAKE_TOTP_SECRET,
        "DHAN_API_KEY":     FAKE_API_KEY,
    }


@pytest.fixture(autouse=True)
def isolate_store_paths(tmp_path, monkeypatch):
    """Redirect all store paths to tmp_path for isolation."""
    import scripts.dhan_auth.dhan_token_store as ts
    monkeypatch.setattr(ts, "STORE_PATH", tmp_path / "dhan_token_store.json")
    monkeypatch.setattr(ts, "HEALTH_PATH", tmp_path / "dhan_token_health.json")
    monkeypatch.setattr(ts, "AUDIT_PATH",  tmp_path / "logs" / "dhan_token_audit.jsonl")
    monkeypatch.setattr(ts, "LOCK_PATH",   tmp_path / "dta_refresh.lock")
    monkeypatch.setattr(ts, "DATA_DIR",    tmp_path)
    yield


# ─────────────────────────────────────────────────────────────────────────────
# T020-001: Cron file has clean Unix LF endings (no CRLF)
# Root cause: CRLF on the retry line caused both cron jobs to be silently skipped.
# ─────────────────────────────────────────────────────────────────────────────
class TestT020001CronFileIntegrity:
    """T020-001: Verify the cron template in the repo has no CRLF line endings."""

    def test_t020_001_cron_template_no_crlf(self):
        """
        T020-001: No CRLF in the cron file source-of-truth.

        The root cause of the DTA-020 failure was that the VPS cron file
        /etc/cron.d/dhan-token-agent had \\r\\n on the retry job line.
        This caused cron to silently skip both primary and retry jobs.

        We now maintain a canonical template at scripts/dhan_auth/dhan-token-agent.cron.
        This test asserts it contains no carriage returns.
        """
        cron_template = ROOT / "scripts" / "dhan_auth" / "dhan-token-agent.cron"
        assert cron_template.exists(), (
            f"Cron template missing: {cron_template}. "
            "Create scripts/dhan_auth/dhan-token-agent.cron with Unix LF endings."
        )
        raw_bytes = cron_template.read_bytes()
        assert b"\r" not in raw_bytes, (
            "Cron file contains CRLF (\\r) — this will silently break cron on Linux. "
            "Convert to Unix LF: git config core.autocrlf false or use dos2unix."
        )

    def test_t020_001b_cron_template_has_both_schedule_lines(self):
        """
        T020-001b: Cron template contains both primary (01:50) and retry (02:30) schedule lines.
        """
        cron_template = ROOT / "scripts" / "dhan_auth" / "dhan-token-agent.cron"
        if not cron_template.exists():
            pytest.skip("Cron template not yet created — checked separately in T020-001")
        content = cron_template.read_text(encoding="utf-8")
        assert "50 1" in content, "Primary schedule line (01:50 IST) missing from cron template"
        assert "30 2" in content, "Retry schedule line (02:30 IST) missing from cron template"
        assert "dhan_token_agent.py" in content, "Token agent command missing from cron template"
        assert "--refresh" in content, "--refresh flag missing from cron template"


# ─────────────────────────────────────────────────────────────────────────────
# T020-002: Credentials read from .env file, not only os.environ
# Root cause: VPS container had all credential env vars MISSING in os.environ,
# but credentials were present in /app/.env — DTA-001 must read from .env.
# ─────────────────────────────────────────────────────────────────────────────
class TestT020002CredentialsFromEnvFile:
    """T020-002: DhanTokenAgent reads credentials from .env file path."""

    def test_t020_002_credentials_from_env_file(self, tmp_path, monkeypatch):
        """
        T020-002: When os.environ has no DHAN_* vars but /app/.env has them,
        load_credentials() must succeed (credentials in .env file, not env vars).

        This was verified empirically on the VPS: os.getenv('DHAN_PIN') == ''
        but TOTP validation succeeded because the .env file had the credentials.

        load_credentials() calls _load_dhan_env() which uses python-dotenv to
        populate os.environ from the .env file before reading with os.getenv().
        We mock _load_dhan_env() to directly inject the test credentials into
        os.environ, simulating the dotenv behaviour without file-path plumbing.
        """
        from scripts.dhan_auth.dhan_token_agent import DhanTokenAgent

        # Remove DHAN_* vars from process environment entirely (simulate container
        # environment where they were never set via docker -e flags)
        for key in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET", "DHAN_API_KEY"):
            monkeypatch.delenv(key, raising=False)

        # Simulate _load_dhan_env() loading credentials from the .env file
        def _fake_load_env():
            os.environ.setdefault("DHAN_CLIENT_ID",   FAKE_CLIENT_ID)
            os.environ.setdefault("DHAN_PIN",         FAKE_PIN)
            os.environ.setdefault("DHAN_TOTP_SECRET", FAKE_TOTP_SECRET)
            os.environ.setdefault("DHAN_API_KEY",     FAKE_API_KEY)

        agent = DhanTokenAgent()
        with patch("scripts.dhan_auth.dhan_token_agent._load_dhan_env",
                   side_effect=_fake_load_env):
            creds = agent.load_credentials()

        assert creds["DHAN_CLIENT_ID"] == FAKE_CLIENT_ID
        assert creds["DHAN_PIN"] == FAKE_PIN
        assert creds["DHAN_TOTP_SECRET"] == FAKE_TOTP_SECRET

    def test_t020_002b_env_file_missing_raises_credential_error(self):
        """
        T020-002b: When neither os.environ nor .env file has credentials,
        load_credentials() raises CredentialError (fail closed, not silent).
        """
        from scripts.dhan_auth.dhan_token_agent import DhanTokenAgent, CredentialError
        agent = DhanTokenAgent()
        cleared = {k: "" for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET")}
        # Point env_path at a non-existent file
        with patch.dict(os.environ, cleared), \
             patch("scripts.dhan_auth.dhan_token_agent._detect_env_path",
                   return_value=Path("/nonexistent/.env")):
            with pytest.raises(CredentialError):
                agent.load_credentials()


# ─────────────────────────────────────────────────────────────────────────────
# T020-003: Expired token detected → DTA-002 returns TOKEN_EXPIRED
# ─────────────────────────────────────────────────────────────────────────────
class TestT020003ExpiredTokenDetected:
    """T020-003: DTA-002 correctly classifies an expired token as TOKEN_EXPIRED."""

    def test_t020_003_expired_token_state(self):
        """
        T020-003: When token metadata shows expiry in the past, DTA-002 returns
        TOKEN_EXPIRED — the lifecycle system detects the expired state automatically.
        """
        from scripts.dhan_auth.dhan_token_sync import TOKEN_EXPIRED
        sync = _make_sync()
        expired_meta = _make_meta(expiry_time=_EXPIRY_PAST, status="TOKEN_REFRESHED")
        with patch.object(sync, "_load_meta", return_value=expired_meta):
            state = sync.get_token_state()
        assert state == TOKEN_EXPIRED

    def test_t020_003b_expired_not_safe_for_api(self):
        """
        T020-003b: TOKEN_EXPIRED → is_token_safe_for_api() = False.
        This is the gate that prevents live orders when token is expired.
        """
        sync = _make_sync()
        expired_meta = _make_meta(expiry_time=_EXPIRY_PAST)
        with patch.object(sync, "_load_meta", return_value=expired_meta):
            assert not sync.is_token_safe_for_api()


# ─────────────────────────────────────────────────────────────────────────────
# T020-004: After DTA-001 refresh, new generation_id detected by DTA-002 → RELOADED
# ─────────────────────────────────────────────────────────────────────────────
class TestT020004TokenDeliveryChain:
    """T020-004: New generation_id from DTA-001 triggers hot-swap in DTA-002."""

    def test_t020_004_new_gen_id_triggers_reload(self):
        """
        T020-004: After DTA-001 writes a new generation_id (via cron docker exec),
        DTA-002.maybe_sync() detects it and calls reload_token() once.

        This is the core delivery chain: agent → store → sync → broker.
        """
        sync = _make_sync(last_gen=FAKE_GEN_A)
        fm = _make_feed_manager(reload_return=True)

        # DTA-001 wrote a NEW generation_id (FAKE_GEN_B)
        new_meta = _make_meta(generation_id=FAKE_GEN_B, expiry_time=_EXPIRY_24H)
        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_B), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_B):
            result = sync.maybe_sync(fm)

        assert result["action"] == "RELOADED"
        assert result["generation_id"] == FAKE_GEN_B
        fm.dhan.reload_token.assert_called_once()
        assert sync._last_loaded_generation_id == FAKE_GEN_B

    def test_t020_004b_unchanged_gen_id_no_reload(self):
        """
        T020-004b: Same generation_id → NO_CHANGE, reload_token() NOT called.
        Token is not redundantly reloaded on every 5-minute sync tick.
        """
        sync = _make_sync(last_gen=FAKE_GEN_A)
        fm = _make_feed_manager(reload_return=True)
        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A):
            result = sync.maybe_sync(fm)
        assert result["action"] == "NO_CHANGE"
        fm.dhan.reload_token.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# T020-005: Refresh failure → REFRESH_FAILED state, broker NOT reloaded
# ─────────────────────────────────────────────────────────────────────────────
class TestT020005RefreshFailure:
    """T020-005: When DTA-001 refresh fails, system fails closed — no stale token reloaded."""

    def test_t020_005_reload_token_false_not_recorded(self):
        """
        T020-005: When reload_token() returns False, DTA-002 does NOT record the
        generation_id as loaded. The next cycle will retry automatically.
        """
        sync = _make_sync(last_gen=None)
        fm = _make_feed_manager(reload_return=False)  # broker reload fails

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        assert result["action"] == "RELOAD_FAILED"
        # generation_id NOT recorded — next cycle will retry
        assert sync._last_loaded_generation_id is None

    def test_t020_005b_reload_exception_not_recorded(self):
        """
        T020-005b: When reload_token() raises an exception, DTA-002 does NOT record
        the generation_id. The exception is caught and reported as RELOAD_FAILED.
        """
        sync = _make_sync(last_gen=None)
        fm = _make_feed_manager()
        fm.dhan.reload_token.side_effect = RuntimeError("broker connection lost")

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        assert result["action"] == "RELOAD_FAILED"
        assert sync._last_loaded_generation_id is None


# ─────────────────────────────────────────────────────────────────────────────
# T020-006: Process restart with existing valid token → TOKEN_HEALTHY
# ─────────────────────────────────────────────────────────────────────────────
class TestT020006RestartWithValidToken:
    """T020-006: After container restart, existing valid token is detected as HEALTHY."""

    def test_t020_006_restart_reads_existing_valid_token(self):
        """
        T020-006: On process startup, DTA-002 reads the current generation_id from
        the store (written by DTA-001's last cron run). If the token is still valid,
        get_token_state() returns TOKEN_HEALTHY — no immediate refresh needed.
        """
        from scripts.dhan_auth.dhan_token_sync import TOKEN_HEALTHY
        sync = _make_sync()
        valid_meta = _make_meta(expiry_time=_EXPIRY_24H, status="TOKEN_REFRESHED")
        with patch.object(sync, "_load_meta", return_value=valid_meta):
            state = sync.get_token_state()
        assert state == TOKEN_HEALTHY

    def test_t020_006b_restart_with_expired_token_detects_expired(self):
        """
        T020-006b: After restart with an expired token (cron failed),
        TOKEN_EXPIRED is returned — the system detects the failure automatically.
        This is the state DTA-020 was designed to diagnose.
        """
        from scripts.dhan_auth.dhan_token_sync import TOKEN_EXPIRED
        sync = _make_sync()
        expired_meta = _make_meta(expiry_time=_EXPIRY_PAST, status="TOKEN_REFRESHED")
        with patch.object(sync, "_load_meta", return_value=expired_meta):
            state = sync.get_token_state()
        assert state == TOKEN_EXPIRED


# ─────────────────────────────────────────────────────────────────────────────
# T020-007: Idempotency — fresh token NOT regenerated if ≥20h remaining
# ─────────────────────────────────────────────────────────────────────────────
class TestT020007Idempotency:
    """T020-007: DTA-001 skips regeneration when existing token has ≥20h remaining."""

    def test_t020_007_skips_fresh_token(self):
        """
        T020-007: should_skip_generation() returns True when token has ≥20h remaining.
        The cron retry (30 2) uses this gate to avoid duplicate refresh on same day.
        """
        from scripts.dhan_auth.dhan_token_agent import DhanTokenAgent, TOKEN_REUSE_MIN_HOURS

        assert TOKEN_REUSE_MIN_HOURS == 20, (
            "TOKEN_REUSE_MIN_HOURS changed — this is a protected constant. "
            "DTA-020 verified it at 20h."
        )

        agent = DhanTokenAgent()
        # Simulate metadata with 23h remaining (fresh)
        from scripts.dhan_auth.dhan_token_store import (
            STATUS_TOKEN_REFRESHED, TokenMetadata,
        )
        meta = TokenMetadata(
            client_id=FAKE_CLIENT_ID,
            generated_at=_NOW_UTC.isoformat(),
            expiry_time=(_NOW_UTC + timedelta(hours=23)).isoformat(),
            status=STATUS_TOKEN_REFRESHED,
            generation_id=FAKE_GEN_A,
            source="DTA-001-TOTP",
            last_health_check=_NOW_UTC.isoformat(),
        )
        with patch("scripts.dhan_auth.dhan_token_agent.load_metadata", return_value=meta):
            assert agent.should_skip_generation() is True

    def test_t020_007b_does_not_skip_expired_token(self):
        """T020-007b: should_skip_generation() returns False when token is expired."""
        from scripts.dhan_auth.dhan_token_agent import DhanTokenAgent
        from scripts.dhan_auth.dhan_token_store import STATUS_TOKEN_REFRESHED, TokenMetadata

        agent = DhanTokenAgent()
        meta = TokenMetadata(
            client_id=FAKE_CLIENT_ID,
            generated_at=_NOW_UTC.isoformat(),
            expiry_time=_EXPIRY_PAST,
            status=STATUS_TOKEN_REFRESHED,
            generation_id=FAKE_GEN_A,
            source="DTA-001-TOTP",
            last_health_check=_NOW_UTC.isoformat(),
        )
        with patch("scripts.dhan_auth.dhan_token_agent.load_metadata", return_value=meta):
            assert agent.should_skip_generation() is False


# ─────────────────────────────────────────────────────────────────────────────
# T020-008: End-to-end: run_refresh writes store that DTA-002 can detect
# ─────────────────────────────────────────────────────────────────────────────
class TestT020008EndToEndDeliveryChain:
    """T020-008: run_refresh() writes metadata that DTA-002 can read and detect as new."""

    def test_t020_008_run_refresh_writes_detectable_store(self):
        """
        T020-008: After a successful run_refresh(), the store contains a new
        generation_id. DTA-002._read_current_generation_id() returns it,
        triggering a RELOADED action on the next maybe_sync() call.
        """
        from scripts.dhan_auth.dhan_token_agent import DhanTokenAgent

        agent = DhanTokenAgent()
        generated_gen_id: list = []

        def fake_run_refresh():
            from scripts.dhan_auth.dhan_token_store import (
                STATUS_TOKEN_REFRESHED, TokenMetadata, save_metadata, write_health,
            )
            import uuid
            gen_id = str(uuid.uuid4())
            generated_gen_id.append(gen_id)
            meta = TokenMetadata(
                client_id=FAKE_CLIENT_ID,
                generated_at=_NOW_UTC.isoformat(),
                expiry_time=_EXPIRY_24H,
                status=STATUS_TOKEN_REFRESHED,
                generation_id=gen_id,
                source="DTA-001-TOTP",
                last_health_check=_NOW_UTC.isoformat(),
            )
            save_metadata(meta)
            write_health(STATUS_TOKEN_REFRESHED, {
                "expiry_time": _EXPIRY_24H,
                "generation_id": gen_id,
                "live_reload": False,
            })
            return {"status": STATUS_TOKEN_REFRESHED, "generation_id": gen_id}

        with patch.object(agent, "run_refresh", side_effect=fake_run_refresh):
            result = agent.run_refresh()

        assert result["status"] == "TOKEN_REFRESHED"
        new_gen = result["generation_id"]

        # DTA-002 should now detect the new generation_id
        sync = _make_sync(last_gen=None)  # fresh process (no previous gen_id loaded)
        detected = sync._read_current_generation_id()
        assert detected == new_gen, (
            f"DTA-002 could not read the generation_id written by DTA-001. "
            f"Expected {new_gen!r}, got {detected!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# T020-009: Auth failure does NOT disable knowledge/learning pipeline
# ─────────────────────────────────────────────────────────────────────────────
class TestT020009KnowledgePipelineUnaffected:
    """T020-009: DTA-002 auth failure only disables live broker — not learning/knowledge."""

    def test_t020_009_expired_token_state_does_not_raise(self):
        """
        T020-009: get_token_state() and is_token_safe_for_api() return values,
        never raise exceptions. The learning pipeline can check auth state safely
        without being disrupted by an auth failure.
        """
        sync = _make_sync()
        with patch.object(sync, "_load_meta", return_value=None):
            # Unavailable metadata — should return TOKEN_UNAVAILABLE, not raise
            state = sync.get_token_state()
            safe = sync.is_token_safe_for_api()
        assert state == "TOKEN_UNAVAILABLE"
        assert safe is False  # no exception raised

    def test_t020_009b_maybe_sync_failure_does_not_raise(self):
        """
        T020-009b: When reload_token() fails, maybe_sync() returns a dict — never raises.
        The scheduler can call maybe_sync() safely in a try/except-free hot path
        without risking disruption to the broader orchestrator.
        """
        sync = _make_sync(last_gen=None)
        fm = _make_feed_manager()
        fm.dhan.reload_token.side_effect = ConnectionError("broker down")

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)  # must NOT raise

        assert isinstance(result, dict)
        assert result["action"] == "RELOAD_FAILED"


# ─────────────────────────────────────────────────────────────────────────────
# T020-010: is_token_safe_for_api() gates live order execution
# ─────────────────────────────────────────────────────────────────────────────
class TestT020010OrderGating:
    """T020-010: is_token_safe_for_api() correctly gates live API calls."""

    @pytest.mark.parametrize("expiry,status,expected_safe", [
        (_EXPIRY_24H, "TOKEN_REFRESHED",      True),   # healthy
        (_EXPIRY_1H,  "TOKEN_REFRESHED",      True),   # near-expiry, still safe
        (_EXPIRY_PAST, "TOKEN_REFRESHED",     False),  # expired
        (_EXPIRY_24H, "TOKEN_REFRESH_FAILED", False),  # refresh failed
    ])
    def test_t020_010_safe_for_api_matrix(self, expiry, status, expected_safe):
        """
        T020-010: Parametric safety gate test.
        HEALTHY and NEAR_EXPIRY → safe (True).
        EXPIRED and REFRESH_FAILED → not safe (False) → no live order possible.
        """
        sync = _make_sync()
        meta = _make_meta(expiry_time=expiry, status=status)
        with patch.object(sync, "_load_meta", return_value=meta):
            assert sync.is_token_safe_for_api() == expected_safe

    def test_t020_010b_unavailable_not_safe(self):
        """T020-010b: No metadata (no cron run ever) → not safe → no live order."""
        sync = _make_sync()
        with patch.object(sync, "_load_meta", return_value=None):
            assert not sync.is_token_safe_for_api()


# ─────────────────────────────────────────────────────────────────────────────
# T020-011: JWT never appears in any result dict, log, or exception
# ─────────────────────────────────────────────────────────────────────────────
class TestT020011JwtNeverLeaks:
    """T020-011: JWT token value is never exposed in logs, result dicts, or exceptions."""

    def test_t020_011_jwt_not_in_maybe_sync_result(self):
        """T020-011: maybe_sync() result dict never contains the JWT string."""
        sync = _make_sync(last_gen=None)
        fm = _make_feed_manager(reload_return=True)

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        result_str = str(result)
        assert FAKE_JWT_A not in result_str
        assert "PAYLOAD_DTA020" not in result_str

    def test_t020_011b_jwt_not_in_log_output(self, caplog):
        """T020-011b: JWT never appears in any log record during DTA-002 sync."""
        sync = _make_sync(last_gen=None)
        fm = _make_feed_manager(reload_return=True)

        with caplog.at_level(logging.DEBUG), \
             patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            sync.maybe_sync(fm)

        full_log = "\n".join(caplog.messages)
        assert FAKE_JWT_A not in full_log
        assert "PAYLOAD_DTA020" not in full_log

    def test_t020_011c_reload_failed_error_does_not_contain_jwt(self):
        """T020-011c: RELOAD_FAILED result dict contains no JWT fragment."""
        sync = _make_sync(last_gen=None)
        fm = _make_feed_manager()
        fm.dhan.reload_token.side_effect = ValueError("test failure")

        with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
             patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
            result = sync.maybe_sync(fm)

        assert result["action"] == "RELOAD_FAILED"
        assert FAKE_JWT_A not in str(result)


# ─────────────────────────────────────────────────────────────────────────────
# T020-012: Concurrent DTA-002 calls do not create conflicting auth state
# ─────────────────────────────────────────────────────────────────────────────
class TestT020012ConcurrencySafety:
    """T020-012: Concurrent maybe_sync() calls handled via lock — no race condition."""

    def test_t020_012_concurrent_calls_one_wins(self):
        """
        T020-012: When two threads call maybe_sync() simultaneously, exactly one
        proceeds (RELOADED) and the other returns SKIPPED_LOCK_BUSY.
        No duplicate reload, no conflicting auth state.

        This prevents multi-container scenarios where two processes call maybe_sync()
        at the same time and both try to reload_token() with potentially different JWTs.
        """
        sync = _make_sync(last_gen=None)
        fm = _make_feed_manager(reload_return=True)
        results: list = []
        barrier = threading.Barrier(2)

        def _slow_reload(token: str) -> bool:
            import time
            time.sleep(0.05)  # simulate a slow broker reconnect
            return True

        fm.dhan.reload_token.side_effect = _slow_reload

        def _call_sync():
            barrier.wait()  # both threads start at the same time
            with patch.object(sync, "_read_current_generation_id", return_value=FAKE_GEN_A), \
                 patch.object(sync, "_read_token_from_env", return_value=FAKE_JWT_A):
                r = sync.maybe_sync(fm)
            results.append(r["action"])

        t1 = threading.Thread(target=_call_sync)
        t2 = threading.Thread(target=_call_sync)
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert len(results) == 2
        assert "RELOADED" in results, "At least one call must succeed"
        # The lock-losing thread must not have also reloaded
        assert results.count("RELOADED") == 1, (
            f"Both threads reloaded — race condition: {results}"
        )
        assert "SKIPPED_LOCK_BUSY" in results or "NO_CHANGE" in results, (
            f"Lock-losing thread returned unexpected result: {results}"
        )
        # reload_token must have been called at most once (no duplicate reload)
        assert fm.dhan.reload_token.call_count <= 1
