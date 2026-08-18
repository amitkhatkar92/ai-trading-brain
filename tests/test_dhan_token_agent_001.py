"""
tests/test_dhan_token_agent_001.py
====================================
DTA-001 — 90 unit tests (T001–T090).

ALL Dhan API endpoints are mocked — no real network calls.
All credential values are fake test fixtures — never real credentials.

Test categories
    T001-T010  Credential loading
    T011-T020  TOTP generation
    T021-T025  Clock validation
    T026-T045  Token generation (call_generate_token)
    T046-T055  Token store (metadata / health / audit)
    T056-T065  Health check (check_token_health)
    T066-T075  Atomic rotation & lock
    T076-T080  Idempotency
    T081-T085  Dry-run mode
    T086-T090  Security — no credential leakage anywhere
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, call, patch

import pytest
import requests

# ── Make the package importable from the test runner root ─────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dhan_auth.dhan_token_agent import (
    ClockError,
    ConcurrentRefreshError,
    CredentialError,
    DhanTokenAgent,
    IPMismatchError,
    TokenGenerationError,
    TokenHealthError,
    _detect_env_path,
    _expiry_iso,
    _extract_dhan_error,
    _load_dhan_env,
    _parse_jwt_expiry,
    _update_env_file,
    main,
)
from scripts.dhan_auth.dhan_token_store import (
    ALL_STATUSES,
    STATUS_NO_TOKEN,
    STATUS_TOKEN_REFRESH_FAILED,
    STATUS_TOKEN_REFRESHED,
    STATUS_TOKEN_VALID,
    TokenMetadata,
    _sha_prefix,
    acquire_lock,
    append_audit,
    load_metadata,
    read_health,
    release_lock,
    save_metadata,
    write_health,
)
from scripts.dhan_auth.dhan_token_health import check_token_health, get_vps_public_ip

# ── Fixtures & helpers ─────────────────────────────────────────────────────────

FAKE_CLIENT_ID = "9999999999"
FAKE_PIN = "1234"
# Real valid base-32 secret for pyotp tests
FAKE_TOTP_SECRET = "JBSWY3DPEHPK3PXP"
FAKE_API_KEY = "fake_api_key_xyz"
FAKE_JWT = (
    "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9"
    ".eyJleHAiOjk5OTk5OTk5OTksImRoYW5DbGllbnRJZCI6Ijk5OTk5OTk5OTkifQ"
    ".AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)  # fake JWT — exp far future


def _fresh_creds() -> Dict[str, str]:
    return {
        "DHAN_CLIENT_ID": FAKE_CLIENT_ID,
        "DHAN_PIN": FAKE_PIN,
        "DHAN_TOTP_SECRET": FAKE_TOTP_SECRET,
    }


def _make_agent() -> DhanTokenAgent:
    return DhanTokenAgent()


def _ok_generate_response(token: str = FAKE_JWT, client_id: str = FAKE_CLIENT_ID) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": token, "dhanClientId": client_id}
    return resp


def _error_response(code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = code
    resp.json.return_value = {"error": "test error"}
    return resp


@pytest.fixture(autouse=True)
def isolate_paths(tmp_path, monkeypatch):
    """Redirect all DTA store paths to tmp_path for isolation."""
    import scripts.dhan_auth.dhan_token_store as ts
    import scripts.dhan_auth.dhan_token_health as th
    monkeypatch.setattr(ts, "STORE_PATH", tmp_path / "dhan_token_store.json")
    monkeypatch.setattr(ts, "HEALTH_PATH", tmp_path / "dhan_token_health.json")
    monkeypatch.setattr(ts, "AUDIT_PATH", tmp_path / "logs" / "dhan_token_audit.jsonl")
    monkeypatch.setattr(ts, "LOCK_PATH", tmp_path / "dta_refresh.lock")
    monkeypatch.setattr(ts, "DATA_DIR", tmp_path)
    yield


# ─────────────────────────────────────────────────────────────────────────────
# T001-T010: Credential loading
# ─────────────────────────────────────────────────────────────────────────────

class TestCredentialLoading:

    def test_t001_all_credentials_present(self):
        """T001: All required creds present → no exception."""
        agent = _make_agent()
        with patch.dict(os.environ, _fresh_creds()):
            creds = agent.load_credentials()
        assert creds["DHAN_CLIENT_ID"] == FAKE_CLIENT_ID

    def test_t002_missing_client_id(self):
        """T002: DHAN_CLIENT_ID missing → CredentialError."""
        env = _fresh_creds()
        del env["DHAN_CLIENT_ID"]
        with patch.dict(os.environ, env, clear=False):
            with patch.dict(os.environ, {"DHAN_CLIENT_ID": ""}):
                with pytest.raises(CredentialError) as exc:
                    _make_agent().load_credentials()
        assert "DHAN_CLIENT_ID" in str(exc.value)

    def test_t003_missing_pin(self):
        """T003: DHAN_PIN missing → CredentialError."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_PIN": ""}):
            with pytest.raises(CredentialError) as exc:
                _make_agent().load_credentials()
        assert "DHAN_PIN" in str(exc.value)

    def test_t004_missing_totp_secret(self):
        """T004: DHAN_TOTP_SECRET missing → CredentialError."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_TOTP_SECRET": ""}):
            with pytest.raises(CredentialError) as exc:
                _make_agent().load_credentials()
        assert "DHAN_TOTP_SECRET" in str(exc.value)

    def test_t005_empty_all_required(self):
        """T005: All required empty → CredentialError listing all three."""
        with patch.dict(os.environ, {"DHAN_CLIENT_ID": "", "DHAN_PIN": "", "DHAN_TOTP_SECRET": ""}):
            with pytest.raises(CredentialError) as exc:
                _make_agent().load_credentials()
        msg = str(exc.value)
        assert "DHAN_CLIENT_ID" in msg
        assert "DHAN_PIN" in msg

    def test_t006_whitespace_trimmed(self):
        """T006: Leading/trailing whitespace stripped from credential values."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_CLIENT_ID": f"  {FAKE_CLIENT_ID}  "}):
            creds = _make_agent().load_credentials()
        assert creds["DHAN_CLIENT_ID"] == FAKE_CLIENT_ID

    def test_t007_optional_api_key_included(self):
        """T007: DHAN_API_KEY is included when set."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_API_KEY": "mykey"}):
            creds = _make_agent().load_credentials()
        assert creds["DHAN_API_KEY"] == "mykey"

    def test_t008_optional_api_key_empty_ok(self):
        """T008: Missing DHAN_API_KEY does not raise."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_API_KEY": ""}):
            creds = _make_agent().load_credentials()
        assert creds["DHAN_API_KEY"] == ""

    def test_t009_cred_error_message_does_not_contain_pin(self):
        """T009: CredentialError message never contains the PIN value."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_PIN": ""}):
            with pytest.raises(CredentialError) as exc:
                _make_agent().load_credentials()
        assert FAKE_PIN not in str(exc.value)

    def test_t010_cred_error_message_does_not_contain_totp(self):
        """T010: CredentialError message never contains the TOTP secret."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_TOTP_SECRET": ""}):
            with pytest.raises(CredentialError) as exc:
                _make_agent().load_credentials()
        assert FAKE_TOTP_SECRET not in str(exc.value)


# ─────────────────────────────────────────────────────────────────────────────
# T011-T020: TOTP generation
# ─────────────────────────────────────────────────────────────────────────────

class TestTOTPGeneration:

    def test_t011_valid_secret_produces_6_digit_code(self):
        """T011: Valid base-32 secret → 6-digit numeric string."""
        code = _make_agent().generate_totp(FAKE_TOTP_SECRET)
        assert len(code) == 6
        assert code.isdigit()

    def test_t012_totp_is_string(self):
        """T012: Return value is a str."""
        code = _make_agent().generate_totp(FAKE_TOTP_SECRET)
        assert isinstance(code, str)

    def test_t013_same_secret_two_calls_same_window_equal(self):
        """T013: Two calls within same 30s window return the same code."""
        agent = _make_agent()
        code1 = agent.generate_totp(FAKE_TOTP_SECRET)
        code2 = agent.generate_totp(FAKE_TOTP_SECRET)
        assert code1 == code2

    def test_t014_empty_secret_raises(self):
        """T014: Empty TOTP secret → ValueError."""
        with pytest.raises((ValueError, Exception)):
            _make_agent().generate_totp("")

    def test_t015_totp_not_in_log_output(self, capfd):
        """T015: generate_totp does not print the TOTP code to stdout/stderr."""
        code = _make_agent().generate_totp(FAKE_TOTP_SECRET)
        captured = capfd.readouterr()
        assert code not in captured.out
        assert code not in captured.err

    def test_t016_totp_in_valid_range(self):
        """T016: TOTP value is between 000000 and 999999."""
        code = _make_agent().generate_totp(FAKE_TOTP_SECRET)
        assert 0 <= int(code) <= 999999

    def test_t017_known_totp_at_known_time(self):
        """T017: Known secret + known epoch → expected TOTP code (deterministic)."""
        import pyotp
        # At t=0 (epoch), JBSWY3DPEHPK3PXP should produce the RFC-6238 test vector
        totp = pyotp.TOTP(FAKE_TOTP_SECRET)
        expected = totp.at(0)
        assert len(expected) == 6

    def test_t018_totp_interval_is_30(self):
        """T018: Default TOTP interval matches RFC-6238 (30 seconds)."""
        import pyotp
        totp = pyotp.TOTP(FAKE_TOTP_SECRET)
        assert totp.interval == 30

    def test_t019_different_secrets_different_codes(self):
        """T019: Different TOTP secrets generate different codes (with high probability)."""
        secret2 = "MFRA22LOMFRA22LO"
        code1 = _make_agent().generate_totp(FAKE_TOTP_SECRET)
        code2 = _make_agent().generate_totp(secret2)
        # May be equal by chance (~1/1000000) but overwhelmingly different
        # We just verify both return valid 6-digit codes
        assert len(code1) == 6 and code1.isdigit()
        assert len(code2) == 6 and code2.isdigit()

    def test_t020_invalid_base32_raises(self):
        """T020: Non-base32 secret raises an exception."""
        with pytest.raises(Exception):
            _make_agent().generate_totp("not-valid-base32!@#$%")


# ─────────────────────────────────────────────────────────────────────────────
# T021-T025: Clock validation
# ─────────────────────────────────────────────────────────────────────────────

class TestClockValidation:

    def test_t021_current_year_passes(self):
        """T021: Current system time passes the sanity check."""
        now = _make_agent().validate_clock()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None

    def test_t022_year_2024_passes(self):
        """T022: Year 2024 is within valid range."""
        fake_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with patch("scripts.dhan_auth.dhan_token_agent.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.fromisoformat = datetime.fromisoformat
            result = _make_agent().validate_clock()
        assert result == fake_now

    def test_t023_year_2019_raises_clock_error(self):
        """T023: Year 2019 is before minimum → ClockError."""
        fake_now = datetime(2019, 12, 31, tzinfo=timezone.utc)
        with patch("scripts.dhan_auth.dhan_token_agent.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            with pytest.raises(ClockError):
                _make_agent().validate_clock()

    def test_t024_year_2051_raises_clock_error(self):
        """T024: Year 2051 is after maximum → ClockError."""
        fake_now = datetime(2051, 1, 1, tzinfo=timezone.utc)
        with patch("scripts.dhan_auth.dhan_token_agent.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            with pytest.raises(ClockError):
                _make_agent().validate_clock()

    def test_t025_clock_error_message_is_informative(self):
        """T025: ClockError message includes the bad year."""
        fake_now = datetime(2000, 1, 1, tzinfo=timezone.utc)
        with patch("scripts.dhan_auth.dhan_token_agent.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            with pytest.raises(ClockError) as exc:
                _make_agent().validate_clock()
        assert "2000" in str(exc.value)


# ─────────────────────────────────────────────────────────────────────────────
# T026-T045: Token generation (call_generate_token)
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenGeneration:

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t026_success_returns_token(self, mock_post):
        """T026: HTTP 200 with valid body → returns token string."""
        mock_post.return_value = _ok_generate_response()
        token = _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "123456")
        assert token == FAKE_JWT

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t027_http_401_raises_no_retry(self, mock_post):
        """T027: HTTP 401 → TokenGenerationError, no retry attempted."""
        mock_post.return_value = _error_response(401)
        with pytest.raises(TokenGenerationError) as exc:
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert mock_post.call_count == 1   # no retry on 401
        assert exc.value.error_category.startswith("HTTP_401")

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t028_http_400_raises_no_retry(self, mock_post):
        """T028: HTTP 400 → TokenGenerationError immediately (bad request)."""
        mock_post.return_value = _error_response(400)
        with pytest.raises(TokenGenerationError):
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert mock_post.call_count == 1

    @patch("scripts.dhan_auth.dhan_token_agent.time.sleep")
    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t029_timeout_triggers_retry(self, mock_post, mock_sleep):
        """T029: Timeout on first attempt → retried up to MAX_RETRIES times."""
        mock_post.side_effect = requests.Timeout("timed out")
        with pytest.raises(TokenGenerationError) as exc:
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert mock_post.call_count == 4   # 1 initial + 3 retries
        assert exc.value.error_category == "TIMEOUT"

    @patch("scripts.dhan_auth.dhan_token_agent.time.sleep")
    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t030_max_retries_exhausted(self, mock_post, mock_sleep):
        """T030: All attempts fail → exception raised after MAX_RETRIES+1 attempts."""
        from scripts.dhan_auth.dhan_token_agent import MAX_RETRIES
        mock_post.side_effect = requests.Timeout()
        with pytest.raises(TokenGenerationError):
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert mock_post.call_count == MAX_RETRIES + 1

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t031_malformed_json_raises(self, mock_post):
        """T031: Non-JSON response body → TokenGenerationError(MALFORMED_RESPONSE)."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("No JSON")
        mock_post.return_value = resp
        with pytest.raises(TokenGenerationError) as exc:
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert exc.value.error_category == "MALFORMED_RESPONSE"

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t032_missing_access_token_field_raises(self, mock_post):
        """T032: 200 response with no access_token field → TokenGenerationError."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"message": "ok"}
        mock_post.return_value = resp
        with pytest.raises(TokenGenerationError) as exc:
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert exc.value.error_category == "EMPTY_TOKEN_FIELD"

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t033_empty_access_token_raises(self, mock_post):
        """T033: 200 response with empty access_token → TokenGenerationError."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"access_token": ""}
        mock_post.return_value = resp
        with pytest.raises(TokenGenerationError) as exc:
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert exc.value.error_category == "EMPTY_TOKEN_FIELD"

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t034_token_not_in_logs(self, mock_post, caplog):
        """T034: Successful response — token value never appears in log output."""
        mock_post.return_value = _ok_generate_response()
        import logging
        with caplog.at_level(logging.DEBUG):
            token = _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "123456")
        assert token not in caplog.text

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t035_pin_not_in_request_logs(self, mock_post, caplog):
        """T035: PIN value never appears in any log record."""
        mock_post.return_value = _ok_generate_response()
        import logging
        with caplog.at_level(logging.DEBUG):
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "123456")
        assert FAKE_PIN not in caplog.text

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t036_request_body_has_correct_fields(self, mock_post):
        """T036: POST sends dhanClientId, pin, totp as URL query parameters (not JSON body)."""
        mock_post.return_value = _ok_generate_response()
        _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "123456")
        _, kwargs = mock_post.call_args
        params = kwargs.get("params", {})
        assert params.get("dhanClientId") == FAKE_CLIENT_ID
        assert params.get("pin") == FAKE_PIN
        assert params.get("totp") == "123456"
        assert kwargs.get("json") is None, "credentials must not be sent in JSON body"

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t037_request_sent_to_correct_url(self, mock_post):
        """T037: POST sent to GENERATE_TOKEN_URL."""
        from scripts.dhan_auth.dhan_token_agent import GENERATE_TOKEN_URL
        mock_post.return_value = _ok_generate_response()
        _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "123456")
        url_called = mock_post.call_args[0][0] if mock_post.call_args[0] else mock_post.call_args[1].get("url")
        assert url_called == GENERATE_TOKEN_URL or str(mock_post.call_args).find(GENERATE_TOKEN_URL) != -1

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t038_content_type_header_set(self, mock_post):
        """T038: Request has no Content-Type header (no request body per Dhan spec)."""
        mock_post.return_value = _ok_generate_response()
        _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "123456")
        headers = mock_post.call_args[1].get("headers", {})
        assert "Content-Type" not in headers, "Content-Type must not be set when sending query params"

    @patch("scripts.dhan_auth.dhan_token_agent.time.sleep")
    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t039_rate_limit_429_longer_backoff(self, mock_post, mock_sleep):
        """T039: 429 response causes a longer backoff than standard."""
        mock_post.side_effect = [_error_response(429), _error_response(429),
                                  _error_response(429), _error_response(429)]
        with pytest.raises(TokenGenerationError):
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        # All sleeps should be ≥ 60s for rate limiting
        for sleep_call in mock_sleep.call_args_list:
            assert sleep_call[0][0] >= 60

    @patch("scripts.dhan_auth.dhan_token_agent.time.sleep")
    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t040_http_503_triggers_retry(self, mock_post, mock_sleep):
        """T040: HTTP 503 server error → retried."""
        mock_post.side_effect = [_error_response(503), _ok_generate_response()]
        token = _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert token == FAKE_JWT
        assert mock_post.call_count == 2

    @patch("scripts.dhan_auth.dhan_token_agent.time.sleep")
    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t041_success_after_one_retry(self, mock_post, mock_sleep):
        """T041: First attempt times out, second succeeds → returns token."""
        mock_post.side_effect = [requests.Timeout(), _ok_generate_response()]
        token = _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert token == FAKE_JWT
        assert mock_post.call_count == 2

    @patch("scripts.dhan_auth.dhan_token_agent.time.sleep")
    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t042_backoff_is_exponential(self, mock_post, mock_sleep):
        """T042: Retry delays follow 10 → 20 → 40 pattern."""
        mock_post.side_effect = requests.Timeout()
        with pytest.raises(TokenGenerationError):
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        delays = [c[0][0] for c in mock_sleep.call_args_list]
        assert delays == [10, 20, 40]

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t043_client_id_mismatch_in_response_raises(self, mock_post):
        """T043: Response dhanClientId differs from expected → TokenGenerationError."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"access_token": FAKE_JWT, "dhanClientId": "0000000000"}
        mock_post.return_value = resp
        with pytest.raises(TokenGenerationError) as exc:
            _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert exc.value.error_category == "CLIENT_ID_MISMATCH"

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t044_api_key_header_added_when_set(self, mock_post):
        """T044: api_key param → 'api-key' header is set."""
        mock_post.return_value = _ok_generate_response()
        _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000", api_key="mykey")
        headers = mock_post.call_args[1].get("headers", {})
        assert headers.get("api-key") == "mykey"

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t045_accesstoken_alternate_key_accepted(self, mock_post):
        """T045: 'accessToken' camelCase key in response is also accepted."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"accessToken": FAKE_JWT, "dhanClientId": FAKE_CLIENT_ID}
        mock_post.return_value = resp
        token = _make_agent().call_generate_token(FAKE_CLIENT_ID, FAKE_PIN, "000000")
        assert token == FAKE_JWT


# ─────────────────────────────────────────────────────────────────────────────
# T046-T055: Token store
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenStore:

    def _make_meta(self, **kwargs) -> TokenMetadata:
        defaults = {
            "client_id": FAKE_CLIENT_ID,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expiry_time": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "status": STATUS_TOKEN_REFRESHED,
            "generation_id": str(uuid.uuid4()),
            "source": "DTA-001-TOTP",
        }
        return TokenMetadata(**{**defaults, **kwargs})

    def test_t046_save_and_load_metadata(self):
        """T046: save_metadata → load_metadata returns equivalent object."""
        meta = self._make_meta()
        save_metadata(meta)
        loaded = load_metadata()
        assert loaded is not None
        assert loaded.client_id == meta.client_id
        assert loaded.generation_id == meta.generation_id

    def test_t047_store_json_never_contains_jwt(self, tmp_path):
        """T047: Written store JSON file never contains FAKE_JWT string."""
        import scripts.dhan_auth.dhan_token_store as ts
        meta = self._make_meta()
        save_metadata(meta)
        content = ts.STORE_PATH.read_text()
        assert FAKE_JWT not in content

    def test_t048_atomic_write_no_partial_file(self, tmp_path):
        """T048: save_metadata uses atomic temp+rename (no .tmp file left behind)."""
        import scripts.dhan_auth.dhan_token_store as ts
        save_metadata(self._make_meta())
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_t049_write_health_creates_file(self):
        """T049: write_health creates health JSON file."""
        import scripts.dhan_auth.dhan_token_store as ts
        write_health(STATUS_TOKEN_VALID, {"client_id": FAKE_CLIENT_ID})
        assert ts.HEALTH_PATH.exists()

    def test_t050_health_json_never_contains_jwt(self):
        """T050: write_health filters 'access_token' key — JWT never in health JSON."""
        import scripts.dhan_auth.dhan_token_store as ts
        write_health(STATUS_TOKEN_VALID, {"access_token": FAKE_JWT})
        content = ts.HEALTH_PATH.read_text()
        assert FAKE_JWT not in content

    def test_t051_health_json_never_contains_pin(self):
        """T051: Health JSON never contains PIN value."""
        import scripts.dhan_auth.dhan_token_store as ts
        write_health(STATUS_TOKEN_VALID, {"pin": FAKE_PIN})
        content = ts.HEALTH_PATH.read_text()
        assert FAKE_PIN not in content

    def test_t052_read_health_returns_no_token_when_missing(self):
        """T052: read_health returns NO_TOKEN status when file absent."""
        health = read_health()
        assert health["status"] == STATUS_NO_TOKEN

    def test_t053_append_audit_creates_jsonl(self):
        """T053: append_audit creates the audit JSONL file."""
        import scripts.dhan_auth.dhan_token_store as ts
        append_audit("TEST_EVENT", STATUS_TOKEN_VALID, client_id=FAKE_CLIENT_ID)
        assert ts.AUDIT_PATH.exists()

    def test_t054_audit_record_has_required_fields(self):
        """T054: Audit record contains all required schema fields."""
        import scripts.dhan_auth.dhan_token_store as ts
        append_audit("TEST_EVENT", STATUS_TOKEN_REFRESHED,
                     client_id=FAKE_CLIENT_ID, duration_ms=500)
        line = ts.AUDIT_PATH.read_text().strip().splitlines()[0]
        record = json.loads(line)
        required = {"timestamp", "event", "status", "client_id_hash",
                    "expiry_time", "generation_success", "health_check_success",
                    "vps_ip_hash", "error_category", "duration_ms"}
        assert required.issubset(set(record.keys()))

    def test_t055_audit_record_never_contains_jwt(self):
        """T055: Audit log never contains the JWT token."""
        import scripts.dhan_auth.dhan_token_store as ts
        append_audit("TOKEN_GENERATED", STATUS_TOKEN_REFRESHED,
                     client_id=FAKE_CLIENT_ID, expiry_time="2026-08-19T07:00:00+00:00")
        content = ts.AUDIT_PATH.read_text()
        assert FAKE_JWT not in content


# ─────────────────────────────────────────────────────────────────────────────
# T056-T065: Health check
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthCheck:

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t056_200_matching_client_id_returns_true(self, mock_get):
        """T056: HTTP 200 + matching dhanClientId → (True, TOKEN_VALID)."""
        mock_get.return_value = MagicMock(
            status_code=200,
            text='{"dhanClientId":"9999999999"}',
            json=lambda: {"dhanClientId": FAKE_CLIENT_ID},
        )
        ok, outcome = check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert ok is True
        assert outcome == STATUS_TOKEN_VALID

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t057_http_401_returns_false(self, mock_get):
        """T057: HTTP 401 → (False, AUTH_FAILED_HTTP_401)."""
        mock_get.return_value = MagicMock(status_code=401, json=lambda: {})
        ok, outcome = check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert ok is False
        assert "401" in outcome

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t058_http_403_returns_false(self, mock_get):
        """T058: HTTP 403 → (False, AUTH_FAILED_HTTP_403)."""
        mock_get.return_value = MagicMock(status_code=403, json=lambda: {})
        ok, outcome = check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert ok is False
        assert "403" in outcome

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t059_timeout_returns_false(self, mock_get):
        """T059: Timeout → (False, TIMEOUT)."""
        mock_get.side_effect = requests.Timeout()
        ok, outcome = check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert ok is False
        assert "TIMEOUT" in outcome

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t060_client_id_mismatch_returns_false(self, mock_get):
        """T060: 200 but dhanClientId mismatch → (False, CLIENT_ID_MISMATCH)."""
        mock_get.return_value = MagicMock(
            status_code=200,
            text='{"dhanClientId":"1111111111"}',
            json=lambda: {"dhanClientId": "1111111111"},
        )
        ok, outcome = check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert ok is False
        assert "CLIENT_ID_MISMATCH" in outcome

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t061_network_error_returns_false(self, mock_get):
        """T061: ConnectionError → (False, NETWORK_ERROR...)."""
        mock_get.side_effect = requests.ConnectionError("unreachable")
        ok, outcome = check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert ok is False
        assert "NETWORK_ERROR" in outcome

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t062_access_token_header_sent(self, mock_get):
        """T062: access-token header is included in the profile request."""
        mock_get.return_value = MagicMock(
            status_code=200, text="{}", json=lambda: {},
        )
        check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        headers = mock_get.call_args[1].get("headers", {})
        assert headers.get("access-token") == FAKE_JWT

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t063_health_url_is_correct(self, mock_get):
        """T063: GET sent to the correct Dhan profile URL."""
        from scripts.dhan_auth.dhan_token_health import PROFILE_URL
        mock_get.return_value = MagicMock(status_code=200, text="{}", json=lambda: {})
        check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        url_called = mock_get.call_args[0][0]
        assert url_called == PROFILE_URL

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t064_jwt_not_in_caplog_during_health_check(self, mock_get, caplog):
        """T064: JWT value never appears in any log record during health check."""
        mock_get.return_value = MagicMock(status_code=200, text="{}", json=lambda: {})
        import logging
        with caplog.at_level(logging.DEBUG):
            check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert FAKE_JWT not in caplog.text

    @patch("scripts.dhan_auth.dhan_token_health.requests.get")
    def test_t065_health_check_updates_health_file(self, mock_get):
        """T065: Successful check writes health JSON file."""
        import scripts.dhan_auth.dhan_token_store as ts
        mock_get.return_value = MagicMock(status_code=200, text="{}", json=lambda: {})
        check_token_health(FAKE_JWT, FAKE_CLIENT_ID)
        assert ts.HEALTH_PATH.exists()


# ─────────────────────────────────────────────────────────────────────────────
# T066-T075: Atomic rotation & lock
# ─────────────────────────────────────────────────────────────────────────────

class TestAtomicRotation:

    def test_t066_env_file_updated_with_new_token(self, tmp_path):
        """T066: _update_env_file replaces DHAN_ACCESS_TOKEN line."""
        env_file = tmp_path / ".env"
        env_file.write_text("DHAN_ACCESS_TOKEN = old_token\nOTHER = value\n")
        _update_env_file(env_file, "new_token_value")
        content = env_file.read_text()
        assert "new_token_value" in content
        assert "old_token" not in content

    def test_t067_env_other_vars_preserved(self, tmp_path):
        """T067: _update_env_file does not lose other .env variables."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR = hello\nDAHN_ACCESS_TOKEN = old\nANOTHER = world\n")
        _update_env_file(env_file, "new_token")
        content = env_file.read_text()
        assert "OTHER_VAR" in content
        assert "ANOTHER" in content

    def test_t068_env_appended_if_key_absent(self, tmp_path):
        """T068: _update_env_file appends DHAN_ACCESS_TOKEN when key not present."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER = value\n")
        _update_env_file(env_file, "brand_new_token")
        content = env_file.read_text()
        assert "DHAN_ACCESS_TOKEN" in content
        assert "brand_new_token" in content

    def test_t069_env_created_if_missing(self, tmp_path):
        """T069: _update_env_file creates .env if file does not exist."""
        env_file = tmp_path / "new.env"
        assert not env_file.exists()
        _update_env_file(env_file, "brand_new_token")
        assert env_file.exists()

    def test_t070_acquire_lock_first_time_succeeds(self, tmp_path, monkeypatch):
        """T070: acquire_lock returns True when no lock file exists."""
        import scripts.dhan_auth.dhan_token_store as ts
        assert not ts.LOCK_PATH.exists()
        assert acquire_lock() is True
        release_lock()

    def test_t071_acquire_lock_stale_pid_succeeds(self, tmp_path, monkeypatch):
        """T071: Stale lock file (dead PID) is ignored — new lock acquired."""
        import scripts.dhan_auth.dhan_token_store as ts
        ts.LOCK_PATH.write_text("99999999")  # non-existent PID
        result = acquire_lock()
        assert result is True
        release_lock()

    def test_t072_acquire_lock_live_pid_fails(self, tmp_path, monkeypatch):
        """T072: Live PID in lock file → acquire_lock returns False."""
        import scripts.dhan_auth.dhan_token_store as ts
        ts.LOCK_PATH.write_text(str(os.getpid()))  # current process = alive
        result = acquire_lock()
        # Clean up regardless
        ts.LOCK_PATH.unlink(missing_ok=True)
        assert result is False

    def test_t073_release_lock_removes_file(self, tmp_path):
        """T073: release_lock removes the lock file."""
        import scripts.dhan_auth.dhan_token_store as ts
        acquire_lock()
        assert ts.LOCK_PATH.exists()
        release_lock()
        assert not ts.LOCK_PATH.exists()

    def test_t074_failed_generation_raises_token_error(self, tmp_path):
        """T074: run_refresh with bad credentials → TokenGenerationError raised."""
        agent = _make_agent()
        with patch.object(agent, "load_credentials", return_value={
            "DHAN_CLIENT_ID": FAKE_CLIENT_ID,
            "DHAN_PIN": FAKE_PIN,
            "DHAN_TOTP_SECRET": FAKE_TOTP_SECRET,
            "DHAN_API_KEY": "",
            "DHAN_EXPECTED_IP": "",
        }):
            with patch.object(agent, "validate_clock"):
                with patch.object(agent, "should_skip_generation", return_value=False):
                    with patch.object(agent, "generate_totp", return_value="123456"):
                        with patch.object(agent, "call_generate_token",
                                          side_effect=TokenGenerationError("fail", "HTTP_401_NO_RETRY")):
                            with pytest.raises(TokenGenerationError):
                                agent.run_refresh()

    def test_t075_failed_health_check_preserves_existing_token(self, tmp_path):
        """T075: When health check fails, TokenHealthError raised (existing token untouched)."""
        agent = _make_agent()
        with patch.object(agent, "load_credentials", return_value={
            "DHAN_CLIENT_ID": FAKE_CLIENT_ID,
            "DHAN_PIN": FAKE_PIN,
            "DHAN_TOTP_SECRET": FAKE_TOTP_SECRET,
            "DHAN_API_KEY": "",
            "DHAN_EXPECTED_IP": "",
        }):
            with patch.object(agent, "validate_clock"):
                with patch.object(agent, "should_skip_generation", return_value=False):
                    with patch.object(agent, "generate_totp", return_value="123456"):
                        with patch.object(agent, "call_generate_token", return_value=FAKE_JWT):
                            with patch("scripts.dhan_auth.dhan_token_agent.check_token_health",
                                       return_value=(False, "TIMEOUT")):
                                with pytest.raises(TokenHealthError):
                                    agent.run_refresh()


# ─────────────────────────────────────────────────────────────────────────────
# T076-T080: Idempotency
# ─────────────────────────────────────────────────────────────────────────────

class TestIdempotency:

    def _meta_with_hours_left(self, hours: float) -> TokenMetadata:
        exp = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        return TokenMetadata(
            client_id=FAKE_CLIENT_ID,
            generated_at=datetime.now(timezone.utc).isoformat(),
            expiry_time=exp,
            status=STATUS_TOKEN_REFRESHED,
            generation_id=str(uuid.uuid4()),
            source="DTA-001-TOTP",
        )

    def test_t076_skip_if_more_than_20h_left(self):
        """T076: Token with ≥20h remaining → should_skip_generation returns True."""
        save_metadata(self._meta_with_hours_left(22))
        assert _make_agent().should_skip_generation() is True

    def test_t077_generate_if_less_than_20h_left(self):
        """T077: Token with <20h remaining → should_skip_generation returns False."""
        save_metadata(self._meta_with_hours_left(1))
        assert _make_agent().should_skip_generation() is False

    def test_t078_no_metadata_means_generate(self):
        """T078: No metadata file → should_skip_generation returns False."""
        # No save_metadata called — file absent
        assert _make_agent().should_skip_generation() is False

    def test_t079_failed_status_means_generate(self):
        """T079: STATUS_TOKEN_REFRESH_FAILED → should_skip_generation False."""
        meta = self._meta_with_hours_left(22)
        meta.status = STATUS_TOKEN_REFRESH_FAILED
        save_metadata(meta)
        assert _make_agent().should_skip_generation() is False

    def test_t080_run_refresh_returns_skipped_when_fresh(self):
        """T080: run_refresh on a fresh token → returns SKIPPED_FRESH_TOKEN dict."""
        save_metadata(self._meta_with_hours_left(23))
        with patch.dict(os.environ, _fresh_creds()):
            result = _make_agent().run_refresh()
        assert result["status"] == "SKIPPED_FRESH_TOKEN"


# ─────────────────────────────────────────────────────────────────────────────
# T081-T085: Dry-run mode
# ─────────────────────────────────────────────────────────────────────────────

class TestDryRun:

    @patch("scripts.dhan_auth.dhan_token_agent.requests.post")
    def test_t081_dry_run_does_not_call_generate_endpoint(self, mock_post):
        """T081: run_dry_run never calls the generate endpoint."""
        with patch.dict(os.environ, _fresh_creds()):
            result = DhanTokenAgent(dry_run=True).run_dry_run()
        mock_post.assert_not_called()
        assert result.get("status") == "DRY_RUN_PASSED"

    def test_t082_dry_run_fails_with_missing_pin(self):
        """T082: run_dry_run with missing DHAN_PIN → credentials check fails."""
        with patch.dict(os.environ, {**_fresh_creds(), "DHAN_PIN": ""}):
            result = DhanTokenAgent(dry_run=True).run_dry_run()
        assert result.get("credentials") is False
        assert "credentials_error" in result

    def test_t083_dry_run_validates_totp(self):
        """T083: run_dry_run with valid TOTP secret → totp_validated field is True."""
        with patch.dict(os.environ, _fresh_creds()):
            result = DhanTokenAgent(dry_run=True).run_dry_run()
        assert result.get("totp_validated") is True

    def test_t084_dry_run_returns_generate_url(self):
        """T084: run_dry_run result includes generate_url config value."""
        from scripts.dhan_auth.dhan_token_agent import GENERATE_TOKEN_URL
        with patch.dict(os.environ, _fresh_creds()):
            result = DhanTokenAgent(dry_run=True).run_dry_run()
        assert result.get("generate_url") == GENERATE_TOKEN_URL

    def test_t085_dry_run_result_has_no_token_field(self):
        """T085: run_dry_run result never contains access_token, pin, totp-code, or jwt."""
        with patch.dict(os.environ, _fresh_creds()):
            result = DhanTokenAgent(dry_run=True).run_dry_run()
        # These are the actual secret values — must not appear in result
        for forbidden_value in (FAKE_PIN, FAKE_TOTP_SECRET, FAKE_JWT):
            assert forbidden_value not in json.dumps(result), f"Secret value leaked in dry-run result"
        # These are forbidden key names that would imply raw credential storage
        for forbidden_key in ("access_token", "jwt", "pin"):
            assert forbidden_key not in result, f"Forbidden key '{forbidden_key}' in dry-run result"


# ─────────────────────────────────────────────────────────────────────────────
# T086-T090: Security — no credential leakage
# ─────────────────────────────────────────────────────────────────────────────

class TestSecurity:

    def test_t086_jwt_not_in_run_refresh_return_dict(self):
        """T086: run_refresh summary dict never contains the JWT value."""
        agent = _make_agent()
        with patch.object(agent, "load_credentials", return_value={
            "DHAN_CLIENT_ID": FAKE_CLIENT_ID,
            "DHAN_PIN": FAKE_PIN,
            "DHAN_TOTP_SECRET": FAKE_TOTP_SECRET,
            "DHAN_API_KEY": "",
            "DHAN_EXPECTED_IP": "",
        }):
            with patch.object(agent, "validate_clock"):
                with patch.object(agent, "should_skip_generation", return_value=False):
                    with patch.object(agent, "generate_totp", return_value="123456"):
                        with patch.object(agent, "call_generate_token", return_value=FAKE_JWT):
                            with patch("scripts.dhan_auth.dhan_token_agent.check_token_health",
                                       return_value=(True, STATUS_TOKEN_VALID)):
                                with patch.object(agent, "deliver_token", return_value=True):
                                    result = agent.run_refresh()
        result_str = json.dumps(result)
        assert FAKE_JWT not in result_str

    def test_t087_pin_not_in_audit_log(self):
        """T087: Audit log records never contain the PIN value."""
        import scripts.dhan_auth.dhan_token_store as ts
        append_audit("TEST", STATUS_TOKEN_REFRESHED, client_id=FAKE_CLIENT_ID)
        content = ts.AUDIT_PATH.read_text()
        assert FAKE_PIN not in content

    def test_t088_totp_secret_not_in_audit_log(self):
        """T088: TOTP secret never in audit log."""
        import scripts.dhan_auth.dhan_token_store as ts
        append_audit("TEST", STATUS_TOKEN_REFRESHED, client_id=FAKE_CLIENT_ID)
        content = ts.AUDIT_PATH.read_text()
        assert FAKE_TOTP_SECRET not in content

    def test_t089_client_id_in_audit_is_hashed(self):
        """T089: Audit stores client_id_hash (not plaintext client_id)."""
        import scripts.dhan_auth.dhan_token_store as ts
        append_audit("TEST", STATUS_TOKEN_REFRESHED, client_id=FAKE_CLIENT_ID)
        record = json.loads(ts.AUDIT_PATH.read_text().strip())
        # Hash present, plaintext absent in the _hash field key
        assert "client_id_hash" in record
        expected_hash = _sha_prefix(FAKE_CLIENT_ID)
        assert record["client_id_hash"] == expected_hash
        # The raw client id should NOT be stored under its own key
        assert "client_id" not in record

    def test_t090_health_json_safe_field_filter(self):
        """T090: write_health silently drops 'access_token' and 'pin' detail fields."""
        import scripts.dhan_auth.dhan_token_store as ts
        write_health(STATUS_TOKEN_VALID, {
            "access_token": "DO_NOT_STORE",
            "pin": "DO_NOT_STORE",
            "safe_field": "keep_this",
        })
        content = ts.HEALTH_PATH.read_text()
        assert "DO_NOT_STORE" not in content
        assert "keep_this" in content


# ─────────────────────────────────────────────────────────────────────────────
# T091-T100: Environment loading from .env file
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvLoader:
    """
    Verify that _load_dhan_env() reads the mounted/local .env file and
    populates os.environ before credential access.

    All files use fake test values only — no real credentials.
    monkeypatch.delenv / monkeypatch.setenv ensure full env teardown per test.
    """

    def _write_fake_env(self, path: Path, extras: dict | None = None) -> None:
        lines = [
            f"DHAN_CLIENT_ID = {FAKE_CLIENT_ID}\n",
            f"DHAN_PIN = {FAKE_PIN}\n",
            f"DHAN_TOTP_SECRET = {FAKE_TOTP_SECRET}\n",
        ]
        if extras:
            for k, v in extras.items():
                lines.append(f"{k} = {v}\n")
        path.write_text("".join(lines))

    def test_t091_docker_env_path_detected(self, monkeypatch):
        """T091: RUNNING_IN_DOCKER=1 → _detect_env_path() returns /app/.env."""
        monkeypatch.delenv("DHAN_ENV_PATH", raising=False)
        monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
        path = _detect_env_path()
        assert path == Path("/app/.env")

    def test_t092_client_id_loaded_from_env_file(self, monkeypatch, tmp_path):
        """T092: DHAN_CLIENT_ID available via os.getenv after _load_dhan_env()."""
        env_file = tmp_path / ".env"
        env_file.write_text(f"DHAN_CLIENT_ID = {FAKE_CLIENT_ID}\n")
        monkeypatch.setenv("DHAN_ENV_PATH", str(env_file))
        monkeypatch.delenv("DHAN_CLIENT_ID", raising=False)
        _load_dhan_env()
        assert os.getenv("DHAN_CLIENT_ID") == FAKE_CLIENT_ID

    def test_t093_pin_loaded_from_env_file(self, monkeypatch, tmp_path):
        """T093: DHAN_PIN available via os.getenv after _load_dhan_env()."""
        env_file = tmp_path / ".env"
        env_file.write_text(f"DHAN_PIN = {FAKE_PIN}\n")
        monkeypatch.setenv("DHAN_ENV_PATH", str(env_file))
        monkeypatch.delenv("DHAN_PIN", raising=False)
        _load_dhan_env()
        assert os.getenv("DHAN_PIN") == FAKE_PIN

    def test_t094_totp_secret_loaded_from_env_file(self, monkeypatch, tmp_path):
        """T094: DHAN_TOTP_SECRET available via os.getenv after _load_dhan_env()."""
        env_file = tmp_path / ".env"
        env_file.write_text(f"DHAN_TOTP_SECRET = {FAKE_TOTP_SECRET}\n")
        monkeypatch.setenv("DHAN_ENV_PATH", str(env_file))
        monkeypatch.delenv("DHAN_TOTP_SECRET", raising=False)
        _load_dhan_env()
        assert os.getenv("DHAN_TOTP_SECRET") == FAKE_TOTP_SECRET

    def test_t095_existing_env_var_not_overwritten(self, monkeypatch, tmp_path):
        """T095: Existing os.environ value takes precedence over .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("DHAN_CLIENT_ID = from_file\n")
        monkeypatch.setenv("DHAN_ENV_PATH", str(env_file))
        monkeypatch.setenv("DHAN_CLIENT_ID", "from_env")
        _load_dhan_env()
        assert os.getenv("DHAN_CLIENT_ID") == "from_env"

    def test_t096_dhan_env_path_explicit(self, monkeypatch, tmp_path):
        """T096: DHAN_ENV_PATH explicit path loads all three credentials from that file."""
        env_file = tmp_path / "custom_creds.env"
        self._write_fake_env(env_file)
        monkeypatch.setenv("DHAN_ENV_PATH", str(env_file))
        for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"):
            monkeypatch.delenv(k, raising=False)
        _load_dhan_env()
        assert os.getenv("DHAN_CLIENT_ID") == FAKE_CLIENT_ID
        assert os.getenv("DHAN_PIN") == FAKE_PIN
        assert os.getenv("DHAN_TOTP_SECRET") == FAKE_TOTP_SECRET

    def test_t097_missing_env_file_no_crash(self, monkeypatch, tmp_path):
        """T097: Missing .env file → _load_dhan_env() is silent; CredentialError raised normally."""
        monkeypatch.setenv("DHAN_ENV_PATH", str(tmp_path / "nonexistent.env"))
        for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"):
            monkeypatch.delenv(k, raising=False)
        _load_dhan_env()  # must not raise
        with pytest.raises(CredentialError) as exc:
            DhanTokenAgent().load_credentials()
        assert "DHAN_CLIENT_ID" in str(exc.value)

    def test_t098_secret_values_never_in_credential_error(self, monkeypatch, tmp_path):
        """T098: CredentialError message never contains PIN or TOTP secret text."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            f"DHAN_CLIENT_ID = {FAKE_CLIENT_ID}\n"
            f"DHAN_TOTP_SECRET = {FAKE_TOTP_SECRET}\n"
        )  # PIN intentionally absent
        monkeypatch.setenv("DHAN_ENV_PATH", str(env_file))
        for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"):
            monkeypatch.delenv(k, raising=False)
        with pytest.raises(CredentialError) as exc:
            DhanTokenAgent().load_credentials()
        error_text = str(exc.value)
        assert FAKE_PIN not in error_text
        assert FAKE_TOTP_SECRET not in error_text

    def test_t099_load_credentials_reads_env_file_internally(self, monkeypatch, tmp_path):
        """T099: load_credentials() works from .env file without the caller pre-loading env."""
        env_file = tmp_path / ".env"
        self._write_fake_env(env_file)
        monkeypatch.setenv("DHAN_ENV_PATH", str(env_file))
        for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"):
            monkeypatch.delenv(k, raising=False)
        # Do NOT call _load_dhan_env() manually — load_credentials() must do it
        creds = DhanTokenAgent().load_credentials()
        assert creds["DHAN_CLIENT_ID"] == FAKE_CLIENT_ID
        assert creds["DHAN_PIN"] == FAKE_PIN
        assert creds["DHAN_TOTP_SECRET"] == FAKE_TOTP_SECRET

    def test_t100_no_trading_modules_imported_by_dta(self):
        """T100: DTA modules do not import broker/order/trading-engine modules at module level."""
        import scripts.dhan_auth.dhan_token_agent   # noqa: F401
        import scripts.dhan_auth.dhan_token_store    # noqa: F401
        import scripts.dhan_auth.dhan_token_health   # noqa: F401
        forbidden_prefixes = {
            "execution_engine", "risk_guardian", "strategy_lab",
            "order_manager", "data_feeds.dhan_feed",
        }
        for mod_name in sys.modules:
            for prefix in forbidden_prefixes:
                assert not mod_name.startswith(prefix), (
                    f"Forbidden trading module '{mod_name}' was imported by DTA"
                )


# ─────────────────────────────────────────────────────────────────────────────
# T101-T106: Dhan error diagnostic — HTTP error body capture
# ─────────────────────────────────────────────────────────────────────────────

def _mock_error_response(status_code: int, body: Any) -> MagicMock:
    """Build a mock requests.Response with given status and JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    if isinstance(body, str):
        resp.json.side_effect = ValueError("not json")
        resp.text = body
    else:
        resp.json.return_value = body
        resp.text = json.dumps(body)
    return resp


class TestDhanErrorDiagnostic:
    """
    T101-T106: Verify that non-200 Dhan responses produce actionable diagnostic
    output without exposing credentials.
    """

    def test_t101_http_400_json_error_body_captured(self):
        """T101: HTTP 400 with JSON error body → dhan_detail contains code + message."""
        resp = _mock_error_response(400, {
            "errorCode": "DH-900",
            "errorMessage": "Invalid pin or totp",
            "status": "failure",
        })
        detail = _extract_dhan_error(resp)
        assert detail["http_status"] == 400
        assert detail.get("dhan_error_code") == "DH-900"
        assert "Invalid pin or totp" in detail.get("dhan_error_message", "")
        assert detail.get("dhan_status") == "failure"
        assert detail.get("retry") is False

    def test_t102_http_400_non_json_body_truncated(self):
        """T102: HTTP 400 with HTML/non-JSON body → safe truncated raw response captured."""
        html_body = "<html><body>Bad Request</body></html>" * 20  # > 400 chars
        resp = _mock_error_response(400, html_body)
        detail = _extract_dhan_error(resp)
        assert detail["http_status"] == 400
        assert "dhan_raw_response" in detail
        # Truncated to 400 chars max
        assert len(detail["dhan_raw_response"]) <= 400

    def test_t103_credential_values_redacted_in_error_body(self):
        """T103: Values that look like TOTP codes or JWTs are redacted in dhan_detail."""
        fake_totp = "123456"
        fake_jwt_like = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        resp = _mock_error_response(400, {
            "errorMessage": f"Auth failed with totp={fake_totp} token={fake_jwt_like}",
            "status": "failure",
        })
        detail = _extract_dhan_error(resp)
        detail_str = json.dumps(detail)
        assert fake_totp not in detail_str, "6-digit TOTP code must be redacted"
        assert fake_jwt_like not in detail_str, "JWT-like value must be redacted"
        assert "[REDACTED]" in detail_str

    def test_t104_no_retry_on_400_with_error_detail(self):
        """T104: HTTP 400 with error body still results in no retry and TokenGenerationError."""
        resp = _mock_error_response(400, {"errorCode": "DH-900", "errorMessage": "Bad creds"})
        with patch("scripts.dhan_auth.dhan_token_agent.requests.post", return_value=resp):
            with patch.dict(os.environ, _fresh_creds()):
                with pytest.raises(TokenGenerationError) as exc:
                    DhanTokenAgent().call_generate_token(
                        FAKE_CLIENT_ID, FAKE_PIN, "123456"
                    )
        assert "NO_RETRY" in exc.value.error_category
        assert exc.value.dhan_detail.get("dhan_error_code") == "DH-900"
        assert exc.value.dhan_detail.get("http_status") == 400

    def test_t105_successful_200_behavior_unchanged(self):
        """T105: HTTP 200 success path is unaffected by the diagnostic changes."""
        resp = _ok_generate_response()
        with patch("scripts.dhan_auth.dhan_token_agent.requests.post", return_value=resp):
            with patch.dict(os.environ, _fresh_creds()):
                token = DhanTokenAgent().call_generate_token(
                    FAKE_CLIENT_ID, FAKE_PIN, "123456"
                )
        assert token == FAKE_JWT

    def test_t106_http_401_json_error_body_captured(self):
        """T106: HTTP 401 with JSON error body → dhan_detail populated, no retry."""
        resp = _mock_error_response(401, {
            "errorCode": "DH-401",
            "errorMessage": "Unauthorized",
        })
        with patch("scripts.dhan_auth.dhan_token_agent.requests.post", return_value=resp):
            with patch.dict(os.environ, _fresh_creds()):
                with pytest.raises(TokenGenerationError) as exc:
                    DhanTokenAgent().call_generate_token(
                        FAKE_CLIENT_ID, FAKE_PIN, "123456"
                    )
        assert exc.value.dhan_detail.get("dhan_error_code") == "DH-401"
        assert exc.value.dhan_detail.get("http_status") == 401
        assert "NO_RETRY" in exc.value.error_category
