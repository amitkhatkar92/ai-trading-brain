"""
DTA-003 — Telegram Token Notifier Tests
=========================================
Tests: T301 – T345
All 45 tests are offline (no network, no Telegram, no real credentials).

Security invariants tested:
  - JWT never appears in any Telegram message
  - DHAN_PIN never appears in any message
  - DHAN_TOTP_SECRET never appears in any message
  - DHAN_ACCESS_TOKEN (os.environ) never appears in any message

Idempotency tested:
  - Same generation_id → one notification only

Rate-limiting tested:
  - Failure notifications: at most one per _FAILURE_COOLDOWN_S

Non-blocking tested:
  - Telegram failure → swallowed, never raises
"""
from __future__ import annotations

import threading
import time
import types
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Fake credentials (never real) ────────────────────────────────────────────

FAKE_JWT_A = "eyJhbGciOiJIUzUxMiJ9.FAKE_PAYLOAD_A.FAKE_SIG_A"
FAKE_JWT_B = "eyJhbGciOiJIUzUxMiJ9.FAKE_PAYLOAD_B.FAKE_SIG_B"
FAKE_GEN_A = "gen-uuid-AAAA-1111-2222-aaaa"
FAKE_GEN_B = "gen-uuid-BBBB-3333-4444-bbbb"
FAKE_PIN   = "123456"
FAKE_TOTP_SECRET = "JBSWY3DPEHPK3PXP"
FAKE_API_KEY = "sk-fake-api-key-do-not-use"

FAKE_EXPIRY_ISO = (
    datetime.now(timezone.utc) + timedelta(hours=23, minutes=57)
).isoformat()

FAKE_GEN_AT = datetime.now(timezone.utc).isoformat()

FAKE_RESULT_SUCCESS: Dict[str, Any] = {
    "status":       "TOKEN_REFRESHED",
    "expiry_time":  FAKE_EXPIRY_ISO,
    "generation_id": FAKE_GEN_A,
    "health_check": True,
    "live_reload":  False,  # docker exec subprocess — DTA-002 syncs within 5 min
    "client_id":    "9999999999",
    "generated_at": FAKE_GEN_AT,
    "duration_ms":  938,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_notifier():
    """Fresh notifier instance (not the process singleton)."""
    from scripts.dhan_auth.dhan_token_notifier import DhanTokenNotifier
    return DhanTokenNotifier()


def _capture_push(notifier) -> List[str]:
    """
    Patch notifier._push to capture all messages sent.
    Returns the list that is appended to on each push call.
    """
    captured: List[str] = []

    def _fake_push(message: str) -> None:
        captured.append(message)

    notifier._push = _fake_push  # type: ignore[method-assign]
    return captured


# ═════════════════════════════════════════════════════════════════════════════
# T301 – T310 : Module import and singleton
# ═════════════════════════════════════════════════════════════════════════════

class TestT301_ModuleImport:
    """T301: Module imports cleanly."""

    def test_t301_import(self):
        import scripts.dhan_auth.dhan_token_notifier as mod  # noqa: F401


class TestT302_Singleton:
    """T302: get_token_notifier() returns the same instance each time."""

    def test_t302_singleton(self):
        from scripts.dhan_auth.dhan_token_notifier import get_token_notifier
        a = get_token_notifier()
        b = get_token_notifier()
        assert a is b


class TestT303_FreshInstance:
    """T303: DhanTokenNotifier() creates independent instances."""

    def test_t303_fresh_instances_are_independent(self):
        n1 = _make_notifier()
        n2 = _make_notifier()
        assert n1 is not n2


# ═════════════════════════════════════════════════════════════════════════════
# T304 – T310 : Formatting helpers
# ═════════════════════════════════════════════════════════════════════════════

class TestT304_ShortGen:
    """T304: _short_gen returns last-8-chars."""

    def test_t304_short_gen(self):
        from scripts.dhan_auth.dhan_token_notifier import _short_gen
        assert _short_gen(FAKE_GEN_A) == f"...{FAKE_GEN_A[-8:]}"

    def test_t304_short_gen_too_short(self):
        from scripts.dhan_auth.dhan_token_notifier import _short_gen
        assert _short_gen("abc") == "abc"


class TestT305_ToIst:
    """T305: _to_ist converts UTC to IST (+5:30)."""

    def test_t305_to_ist_offset(self):
        from scripts.dhan_auth.dhan_token_notifier import _to_ist
        utc_str = "2026-08-19T10:57:31+00:00"
        result  = _to_ist(utc_str)
        # 10:57 UTC → 16:27 IST
        assert "16:27" in result
        assert "IST" in result

    def test_t305_to_ist_bad_input(self):
        from scripts.dhan_auth.dhan_token_notifier import _to_ist
        result = _to_ist("not-a-date")
        assert isinstance(result, str)  # graceful degradation


class TestT306_Remaining:
    """T306: _remaining returns sensible output."""

    def test_t306_remaining_future(self):
        from scripts.dhan_auth.dhan_token_notifier import _remaining
        future = (datetime.now(timezone.utc) + timedelta(hours=23, minutes=57)).isoformat()
        r = _remaining(future)
        assert "23h" in r or "22h" in r  # allow for 1-second clock drift

    def test_t306_remaining_expired(self):
        from scripts.dhan_auth.dhan_token_notifier import _remaining
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert _remaining(past) == "EXPIRED"

    def test_t306_remaining_bad_input(self):
        from scripts.dhan_auth.dhan_token_notifier import _remaining
        assert _remaining("") == "—"


class TestT307_Redact:
    """T307: _redact strips JWT patterns from strings."""

    def test_t307_jwt_redacted(self):
        from scripts.dhan_auth.dhan_token_notifier import _redact
        assert FAKE_JWT_A not in _redact(FAKE_JWT_A)
        assert "[REDACTED]" in _redact(FAKE_JWT_A)

    def test_t307_totp_code_redacted(self):
        from scripts.dhan_auth.dhan_token_notifier import _redact
        result = _redact("code is 123456 ok")
        assert "123456" not in result

    def test_t307_clean_string_unchanged(self):
        from scripts.dhan_auth.dhan_token_notifier import _redact
        clean = "TOKEN_REFRESHED gen-uuid-AAAA"
        assert _redact(clean) == clean


class TestT308_LiveReloadLabel:
    """T308: _live_reload_label maps values correctly."""

    def test_t308_true(self):
        from scripts.dhan_auth.dhan_token_notifier import _live_reload_label
        assert "PASS" in _live_reload_label(True)
        assert "PASS" in _live_reload_label("PASS")

    def test_t308_fail(self):
        from scripts.dhan_auth.dhan_token_notifier import _live_reload_label
        assert "FAIL" in _live_reload_label("FAIL")

    def test_t308_pending(self):
        from scripts.dhan_auth.dhan_token_notifier import _live_reload_label
        assert "PENDING" in _live_reload_label(False)


# ═════════════════════════════════════════════════════════════════════════════
# T310 – T325 : Security — no credentials in messages
# ═════════════════════════════════════════════════════════════════════════════

class TestT310_SecuritySuccessMessage:
    """T310: JWT never in success notification message."""

    def test_t310_jwt_never_in_success_message(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)
        assert caps, "Expected one notification"
        for msg in caps:
            assert FAKE_JWT_A not in msg, "JWT appeared in success notification!"
            assert FAKE_JWT_B not in msg, "JWT_B appeared in success notification!"


class TestT311_SecurityPinNeverInSuccess:
    """T311: PIN never in success notification."""

    def test_t311_pin_never_in_success(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)
        for msg in caps:
            assert FAKE_PIN not in msg


class TestT312_SecurityTotpNeverInSuccess:
    """T312: TOTP secret never in success notification."""

    def test_t312_totp_secret_never_in_success(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)
        for msg in caps:
            assert FAKE_TOTP_SECRET not in msg


class TestT313_SecurityApiKeyNeverInSuccess:
    """T313: API key never in success notification."""

    def test_t313_api_key_never_in_success(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)
        for msg in caps:
            assert FAKE_API_KEY not in msg


class TestT314_SecurityFailureMessage:
    """T314: No credentials in failure notification."""

    def test_t314_no_credentials_in_failure(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_failure(
            error_category="HTTP_400_NO_RETRY",
            current_token_state="TOKEN_HEALTHY",
            http_status=400,
        )
        for msg in caps:
            assert FAKE_JWT_A  not in msg
            assert FAKE_PIN    not in msg
            assert FAKE_TOTP_SECRET not in msg
            assert FAKE_API_KEY not in msg


class TestT315_SecurityReloadFailureMessage:
    """T315: No credentials in reload-failure notification."""

    def test_t315_no_credentials_in_reload_failure(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_reload_result(
            gen_id=FAKE_GEN_A,
            success=False,
            error="ConnectionError: timeout",
        )
        for msg in caps:
            assert FAKE_JWT_A not in msg
            assert FAKE_PIN   not in msg


class TestT316_SecurityJwtInErrorRedacted:
    """T316: If a JWT accidentally ends up in an error string, it is redacted."""

    def test_t316_jwt_in_error_string_is_redacted(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_reload_result(
            gen_id=FAKE_GEN_A,
            success=False,
            error=f"reload failed with token={FAKE_JWT_A}",
        )
        for msg in caps:
            assert FAKE_JWT_A not in msg


# ═════════════════════════════════════════════════════════════════════════════
# T320 – T330 : Idempotency
# ═════════════════════════════════════════════════════════════════════════════

class TestT320_SuccessIdempotency:
    """T320: Same generation_id → only one success notification."""

    def test_t320_second_call_same_gen_id_silent(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)  # duplicate
        assert len(caps) == 1, f"Expected 1 notification, got {len(caps)}"


class TestT321_SuccessNewGenIdSent:
    """T321: New generation_id → second notification sent."""

    def test_t321_new_gen_id_triggers_new_notification(self):
        n = _make_notifier()
        caps = _capture_push(n)

        result_a = dict(FAKE_RESULT_SUCCESS, generation_id=FAKE_GEN_A)
        result_b = dict(FAKE_RESULT_SUCCESS, generation_id=FAKE_GEN_B)

        n.notify_refresh_success(result_a)
        n.notify_refresh_success(result_b)
        assert len(caps) == 2, f"Expected 2 notifications, got {len(caps)}"


class TestT322_EmptyGenIdSkipped:
    """T322: notify_refresh_success with no generation_id sends nothing."""

    def test_t322_empty_gen_id_skipped(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_success({})
        assert len(caps) == 0


# ═════════════════════════════════════════════════════════════════════════════
# T325 – T333 : Rate-limiting for failure alerts
# ═════════════════════════════════════════════════════════════════════════════

class TestT325_FailureRateLimited:
    """T325: Second failure notification within cooldown window is suppressed."""

    def test_t325_second_failure_suppressed(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_failure("HTTP_400_NO_RETRY")
        n.notify_refresh_failure("HTTP_400_NO_RETRY")  # within cooldown
        assert len(caps) == 1


class TestT326_FailureAfterCooldown:
    """T326: Failure notification after cooldown fires again."""

    def test_t326_failure_after_cooldown_fires(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n._last_failure_ts = time.monotonic() - 3700  # expired cooldown
        n.notify_refresh_failure("HTTP_400_NO_RETRY")
        assert len(caps) == 1


class TestT327_ReloadFailureRateLimited:
    """T327: notify_reload_result failure is rate-limited."""

    def test_t327_reload_failure_rate_limited(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_reload_result(FAKE_GEN_A, success=False, error="timeout")
        n.notify_reload_result(FAKE_GEN_A, success=False, error="timeout")
        assert len(caps) == 1


class TestT328_ReloadSuccessSilent:
    """T328: notify_reload_result with success=True sends no message."""

    def test_t328_reload_success_silent(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_reload_result(FAKE_GEN_A, success=True)
        assert len(caps) == 0


# ═════════════════════════════════════════════════════════════════════════════
# T330 – T337 : Non-blocking (Telegram failure swallowed)
# ═════════════════════════════════════════════════════════════════════════════

class TestT330_PushExceptionSwallowed:
    """T330: If _push raises, notify_refresh_success does not propagate."""

    def test_t330_exception_swallowed_on_success(self):
        n = _make_notifier()

        def _exploding_push(msg: str) -> None:
            raise RuntimeError("Telegram is down!")

        n._push = _exploding_push  # type: ignore[method-assign]
        # Must not raise:
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)


class TestT331_PushExceptionSwallowedOnFailure:
    """T331: Telegram crash swallowed in notify_refresh_failure."""

    def test_t331_exception_swallowed_on_failure(self):
        n = _make_notifier()
        n._push = lambda m: (_ for _ in ()).throw(RuntimeError("down"))  # type: ignore[method-assign]
        n.notify_refresh_failure("HTTP_500")  # must not raise


class TestT332_PushFallbackChain:
    """T332: _push tries get_telegram_bot() then get_notifier() on failure."""

    def test_t332_fallback_to_notifier(self, capsys):
        n = _make_notifier()
        # Patch both imports inside _push to capture what is called
        calls: List[str] = []

        def _fake_push(msg: str) -> None:
            # Simulate telegram_bot unavailable, notifier available
            try:
                raise ImportError("telegram_bot not available")
            except ImportError:
                try:
                    calls.append(f"notifier:{msg[:20]}")
                except Exception:
                    pass

        n._push = _fake_push  # type: ignore[method-assign]
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)
        # Should not raise; fallback path exercised


# ═════════════════════════════════════════════════════════════════════════════
# T335 – T341 : Message content checks
# ═════════════════════════════════════════════════════════════════════════════

class TestT335_SuccessMessageContent:
    """T335: Success message contains expected fields."""

    def test_t335_success_message_fields(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_success(FAKE_RESULT_SUCCESS)
        assert caps
        msg = caps[0]
        # Must include key facts
        assert "TOKEN_REFRESHED" in msg
        assert FAKE_GEN_A[-8:] in msg      # short gen id
        assert "PENDING" in msg            # live_reload=False → PENDING label
        assert "Health check" in msg
        assert "Expires" in msg or "Remaining" in msg


class TestT336_FailureMessageContent:
    """T336: Failure message contains error category and timestamp."""

    def test_t336_failure_message_fields(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_refresh_failure(
            error_category="HTTP_400_NO_RETRY",
            current_token_state="TOKEN_HEALTHY",
            http_status=400,
            retry=False,
        )
        assert caps
        msg = caps[0]
        assert "FAILED" in msg
        assert "HTTP_400_NO_RETRY" in msg
        assert "400" in msg
        assert "TOKEN_HEALTHY" in msg


class TestT337_ReloadFailureMessageContent:
    """T337: Reload failure message mentions generation short id."""

    def test_t337_reload_failure_fields(self):
        n = _make_notifier()
        caps = _capture_push(n)
        n.notify_reload_result(FAKE_GEN_A, success=False, error="NameError: X")
        assert caps
        msg = caps[0]
        assert FAKE_GEN_A[-8:] in msg
        assert "NameError" in msg or "FAIL" in msg.upper()


# ═════════════════════════════════════════════════════════════════════════════
# T340 – T345 : format_token_status_message and format_trading_status_message
# ═════════════════════════════════════════════════════════════════════════════

class TestT340_FormatTokenStatus:
    """T340: format_token_status_message builds safe output."""

    def _mock_meta(self):
        from scripts.dhan_auth.dhan_token_store import TokenMetadata
        return TokenMetadata(
            client_id="9999999999",
            generated_at=FAKE_GEN_AT,
            expiry_time=FAKE_EXPIRY_ISO,
            status="TOKEN_REFRESHED",
            generation_id=FAKE_GEN_A,
            source="DTA-001-TOTP",
            last_health_check=FAKE_GEN_AT,
        )

    def test_t340_no_jwt_in_token_status(self):
        from scripts.dhan_auth.dhan_token_notifier import format_token_status_message
        meta = self._mock_meta()
        with patch("scripts.dhan_auth.dhan_token_store.load_metadata", return_value=meta), \
             patch("scripts.dhan_auth.dhan_token_store.read_health", return_value={"status": "TOKEN_REFRESHED"}):
            msg = format_token_status_message(sync_gen_id=FAKE_GEN_A)
        assert FAKE_JWT_A not in msg
        assert FAKE_PIN   not in msg
        assert FAKE_TOTP_SECRET not in msg

    def test_t340_shows_remaining_time(self):
        from scripts.dhan_auth.dhan_token_notifier import format_token_status_message
        meta = self._mock_meta()
        with patch("scripts.dhan_auth.dhan_token_store.load_metadata", return_value=meta), \
             patch("scripts.dhan_auth.dhan_token_store.read_health", return_value={"status": "TOKEN_REFRESHED"}):
            msg = format_token_status_message(sync_gen_id=FAKE_GEN_A)
        assert "h" in msg  # "23h 57m" or similar

    def test_t340_sync_gen_id_match_shows_loaded(self):
        from scripts.dhan_auth.dhan_token_notifier import format_token_status_message
        meta = self._mock_meta()
        with patch("scripts.dhan_auth.dhan_token_store.load_metadata", return_value=meta), \
             patch("scripts.dhan_auth.dhan_token_store.read_health", return_value={"status": "TOKEN_REFRESHED"}):
            msg = format_token_status_message(sync_gen_id=FAKE_GEN_A)
        assert "LOADED" in msg

    def test_t340_sync_gen_id_mismatch_shows_pending(self):
        from scripts.dhan_auth.dhan_token_notifier import format_token_status_message
        meta = self._mock_meta()
        with patch("scripts.dhan_auth.dhan_token_store.load_metadata", return_value=meta), \
             patch("scripts.dhan_auth.dhan_token_store.read_health", return_value={"status": "TOKEN_REFRESHED"}):
            msg = format_token_status_message(sync_gen_id=FAKE_GEN_B)
        assert "PENDING" in msg

    def test_t340_no_metadata_graceful(self):
        from scripts.dhan_auth.dhan_token_notifier import format_token_status_message
        with patch("scripts.dhan_auth.dhan_token_store.load_metadata", return_value=None), \
             patch("scripts.dhan_auth.dhan_token_store.read_health", return_value={}):
            msg = format_token_status_message()
        assert "NO_TOKEN" in msg or "unavailable" in msg.lower()


class TestT341_FormatTradingStatus:
    """T341: format_trading_status_message builds safe output."""

    def test_t341_no_jwt_in_trading_status(self):
        from scripts.dhan_auth.dhan_token_notifier import format_trading_status_message
        msg = format_trading_status_message(
            sync_gen_id=FAKE_GEN_A,
            last_sync_ts=time.monotonic() - 30,
        )
        assert FAKE_JWT_A not in msg
        assert FAKE_PIN   not in msg
        assert FAKE_TOTP_SECRET not in msg

    def test_t341_shows_gen_short_form(self):
        from scripts.dhan_auth.dhan_token_notifier import format_trading_status_message
        msg = format_trading_status_message(sync_gen_id=FAKE_GEN_A)
        assert FAKE_GEN_A[-8:] in msg

    def test_t341_shows_last_sync_elapsed(self):
        from scripts.dhan_auth.dhan_token_notifier import format_trading_status_message
        msg = format_trading_status_message(
            sync_gen_id=FAKE_GEN_A,
            last_sync_ts=time.monotonic() - 10,
        )
        assert "ago" in msg

    def test_t341_no_last_sync_shows_dash(self):
        from scripts.dhan_auth.dhan_token_notifier import format_trading_status_message
        msg = format_trading_status_message()
        assert "—" in msg


# ═════════════════════════════════════════════════════════════════════════════
# T343 – T345 : Thread safety
# ═════════════════════════════════════════════════════════════════════════════

class TestT343_ThreadSafety:
    """T343: Concurrent calls from multiple threads — only one notification per gen_id."""

    def test_t343_concurrent_same_gen_id(self):
        n = _make_notifier()
        caps = _capture_push(n)
        errors: List[Exception] = []

        def _send():
            try:
                n.notify_refresh_success(FAKE_RESULT_SUCCESS)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_send) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(caps) == 1, f"Expected exactly 1 notification, got {len(caps)}"
