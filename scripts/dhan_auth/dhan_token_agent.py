"""
DTA-001 — Dhan Token Agent
============================
Automated daily Dhan access-token generation using Client ID + PIN + TOTP.

Runs inside the ai-trading-brain container (via docker exec or scheduled).

Token flow:
    Credentials (env)
          ↓
    Validate clock
          ↓
    Generate TOTP (RFC-6238)
          ↓
    POST generateAccessToken
          ↓
    Validate response
          ↓
    Health check (GET profile)
          ↓
    Atomic .env update
          ↓
    Hot-reload DhanFeed
          ↓
    Write metadata + audit
          ↓
    Telegram notification

Required environment variables:
    DHAN_CLIENT_ID      — Dhan account / client ID  (not a secret)
    DHAN_PIN            — Dhan login PIN             (SECRET — never log)
    DHAN_TOTP_SECRET    — TOTP seed (base-32)        (SECRET — never log)

Optional environment variables:
    DHAN_API_KEY        — API key passed as header if set
    DHAN_EXPECTED_IP    — Expected VPS IP for whitelist guard
    DHAN_CONTAINER_NAME — Container to hot-reload when running on host (default: ai-trading-brain)
    DHAN_ENV_PATH       — Path to .env file (auto-detected)

CLI modes:
    --refresh   Generate a fresh token (default when no flag given)
    --dry-run   Validate credentials, TOTP, config — no real token call
    --health    Check current token validity — no generation
    --status    Print current metadata — no network calls
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

# DTA internal imports — support both `python -m scripts.dhan_auth.dhan_token_agent`
# (relative imports work) and `python /app/scripts/dhan_auth/dhan_token_agent.py`
# (no parent package; fall back to sys.path injection + absolute imports).
try:
    from .dhan_token_health import check_ip_whitelist, check_token_health
    from .dhan_token_store import (
        STATUS_IP_MISMATCH,
        STATUS_NO_TOKEN,
        STATUS_TOKEN_REFRESH_FAILED,
        STATUS_TOKEN_REFRESHED,
        STATUS_TOKEN_VALID,
        TokenMetadata,
        append_audit,
        acquire_lock,
        load_metadata,
        release_lock,
        save_metadata,
        write_health,
    )
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from dhan_token_health import check_ip_whitelist, check_token_health  # type: ignore[no-redef]
    from dhan_token_store import (  # type: ignore[no-redef]
        STATUS_IP_MISMATCH,
        STATUS_NO_TOKEN,
        STATUS_TOKEN_REFRESH_FAILED,
        STATUS_TOKEN_REFRESHED,
        STATUS_TOKEN_VALID,
        TokenMetadata,
        append_audit,
        acquire_lock,
        load_metadata,
        release_lock,
        save_metadata,
        write_health,
    )

# ── Constants ────────────────────────────────────────────────────────────────

GENERATE_TOKEN_URL = "https://auth.dhan.co/app/generateAccessToken"
HTTP_TIMEOUT_S = 30

MAX_RETRIES = 3        # max extra attempts after first failure
_RETRY_BASE_DELAY_S = 10   # 10 → 20 → 40 seconds
_NO_RETRY_CODES = (400, 401, 403)    # bad request / wrong credentials — no point retrying

TOKEN_REUSE_MIN_HOURS = 20  # skip generation if token has ≥20 h left and is VALID
_CLOCK_MIN_YEAR = 2024
_CLOCK_MAX_YEAR = 2050

# ── Exceptions ────────────────────────────────────────────────────────────────

class CredentialError(RuntimeError):
    """One or more required credentials are missing or empty."""

class ClockError(RuntimeError):
    """System clock fails sanity check."""

class TokenGenerationError(RuntimeError):
    """Dhan token generation endpoint returned an error."""
    def __init__(self, message: str, error_category: str = "UNKNOWN",
                 dhan_detail: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_category = error_category
        self.dhan_detail: Dict[str, Any] = dhan_detail or {}

class TokenHealthError(RuntimeError):
    """Generated token failed the profile health check."""

class ConcurrentRefreshError(RuntimeError):
    """Another refresh is already in progress."""

class IPMismatchError(RuntimeError):
    """VPS public IP does not match the expected Dhan-whitelisted IP."""

# ── Utilities ─────────────────────────────────────────────────────────────────

# Safe fields Dhan returns in error bodies — these are never credential values.
_DHAN_ERROR_FIELD_MAP: Dict[str, str] = {
    "errorCode":     "dhan_error_code",
    "error_code":    "dhan_error_code",
    "code":          "dhan_error_code",
    "errorMessage":  "dhan_error_message",
    "error_message": "dhan_error_message",
    "message":       "dhan_error_message",
    "error":         "dhan_error_message",
    "remarks":       "dhan_remarks",
    "status":        "dhan_status",
    "errorType":     "dhan_error_type",
    "error_type":    "dhan_error_type",
    "httpStatus":    "dhan_http_status_body",
}
# Fields whose names suggest they contain credentials — skip regardless of position.
_SECRET_FIELD_RE = re.compile(
    r"(pin|totp|secret|token|password|access_token|jwt|api.?key)",
    re.IGNORECASE,
)
# Values that look like credentials: 6-digit codes (TOTP) or JWT-like strings.
_CREDENTIAL_VALUE_RE = re.compile(
    r"eyJ[A-Za-z0-9_\-]{10,}|(?<![\d])\d{6}(?![\d])"
)


def _extract_dhan_error(resp: "requests.Response") -> Dict[str, Any]:
    """
    Safely extract diagnostic information from a non-200 Dhan API response.
    Never includes credential values (PIN, TOTP, tokens, secrets).
    """
    detail: Dict[str, Any] = {"http_status": resp.status_code, "retry": False}
    try:
        body = resp.json()
        if isinstance(body, dict):
            for src, dst in _DHAN_ERROR_FIELD_MAP.items():
                if dst in detail:           # already populated by a higher-priority key
                    continue
                if _SECRET_FIELD_RE.search(src):  # skip any field whose name looks secret
                    continue
                val = body.get(src)
                if val is None:
                    continue
                safe = _CREDENTIAL_VALUE_RE.sub("[REDACTED]", str(val))[:300]
                detail[dst] = safe
    except (ValueError, Exception):
        try:
            raw = _CREDENTIAL_VALUE_RE.sub("[REDACTED]", resp.text[:400])
            detail["dhan_raw_response"] = raw
        except Exception:
            detail["dhan_raw_response"] = "[unreadable]"
    return detail


def _detect_env_path() -> Path:
    """Return the .env path to update (container or host)."""
    explicit = os.getenv("DHAN_ENV_PATH", "").strip()
    if explicit:
        return Path(explicit)
    # Inside container
    container_path = Path("/app/.env")
    if container_path.exists() or os.getenv("RUNNING_IN_DOCKER") == "1":
        return container_path
    # Host (relative to this file → project root)
    return Path(__file__).resolve().parent.parent.parent / ".env"


def _load_dhan_env() -> None:
    """
    Populate os.environ from the mounted/local .env file.

    Uses python-dotenv with override=False so any variable already present
    in the process environment (e.g. from 'docker run -e') takes precedence.
    Called before every credential read; safe to call multiple times.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return  # python-dotenv absent; caller must supply env vars directly
    env_path = _detect_env_path()
    if env_path.exists():
        load_dotenv(str(env_path), override=False)


def _update_env_file(env_path: Path, new_token: str) -> None:
    """
    Replace DHAN_ACCESS_TOKEN in .env with the new value.
    Uses direct write (no atomic rename) to support bind-mounted volumes.
    Never logs the token value.
    """
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("DHAN_ACCESS_TOKEN"):
                lines[i] = f"DHAN_ACCESS_TOKEN = {new_token}\n"
                updated = True
                break
        if not updated:
            lines.append(f"DHAN_ACCESS_TOKEN = {new_token}\n")
        env_path.write_text("".join(lines), encoding="utf-8")
    else:
        env_path.write_text(f"DHAN_ACCESS_TOKEN = {new_token}\n", encoding="utf-8")


def _hot_reload_feed(new_token: str) -> bool:
    """
    Call DhanFeed.reload_token() on the running singleton.
    Only works when running inside the container process.
    Returns True on success.
    """
    try:
        from data_feeds import get_feed_manager
        fm = get_feed_manager()
        return fm.dhan.reload_token(new_token)
    except Exception:
        return False


def _parse_jwt_expiry(token: str) -> Optional[float]:
    """Extract Unix exp claim from JWT payload without verifying signature."""
    try:
        import base64
        import re
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        raw = base64.urlsafe_b64decode(part)
        try:
            claims = json.loads(raw)
            return float(claims["exp"])
        except Exception:
            m = re.search(rb'"exp"\s*:\s*(\d+)', raw)
            return float(m.group(1)) if m else None
    except Exception:
        return None


def _expiry_iso(token: str) -> str:
    """Return ISO-8601 UTC expiry from JWT, or empty string on failure."""
    exp = _parse_jwt_expiry(token)
    if exp is None:
        return ""
    return datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()


# ── Main agent ────────────────────────────────────────────────────────────────

class DhanTokenAgent:
    """
    Orchestrates the full DTA-001 token lifecycle.
    Instantiate once per run; it is NOT a long-lived singleton.
    """

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run
        self._log: list = []         # lightweight structured log; no external dep needed

    # ── Credential loading ────────────────────────────────────────────────────

    def load_credentials(self) -> Dict[str, str]:
        """
        Load credentials from environment variables (populated from .env if needed).
        Raises CredentialError if any required variable is missing.
        Never returns PIN, TOTP secret, or API secret in logs.
        """
        _load_dhan_env()  # ensure .env is loaded before any os.getenv() call
        required = ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET")
        missing = []
        creds: Dict[str, str] = {}
        for key in required:
            val = os.getenv(key, "").strip()
            if not val:
                missing.append(key)
            else:
                creds[key] = val
        if missing:
            raise CredentialError(f"Missing required credentials: {', '.join(missing)}")

        # Optional
        creds["DHAN_API_KEY"] = os.getenv("DHAN_API_KEY", "").strip()
        creds["DHAN_EXPECTED_IP"] = os.getenv("DHAN_EXPECTED_IP", "").strip()
        return creds

    # ── Clock validation ──────────────────────────────────────────────────────

    def validate_clock(self) -> datetime:
        """
        Verify system time is plausible. Raises ClockError if year is outside
        [_CLOCK_MIN_YEAR, _CLOCK_MAX_YEAR].  TOTP depends on accurate time.
        """
        now = datetime.now(timezone.utc)
        if not (_CLOCK_MIN_YEAR <= now.year <= _CLOCK_MAX_YEAR):
            raise ClockError(
                f"System clock year {now.year} looks wrong "
                f"(expected {_CLOCK_MIN_YEAR}–{_CLOCK_MAX_YEAR}). "
                "Ensure VPS time is NTP-synced."
            )
        return now

    # ── TOTP ──────────────────────────────────────────────────────────────────

    def generate_totp(self, totp_secret: str) -> str:
        """
        Generate current RFC-6238 6-digit TOTP code.
        NEVER logged — callers must not store or print the return value.
        """
        try:
            import pyotp
        except ImportError:
            raise RuntimeError("pyotp is not installed. Run: pip install pyotp>=2.9.0")

        if not totp_secret:
            raise ValueError("TOTP secret must not be empty.")

        try:
            totp = pyotp.TOTP(totp_secret)
            code = totp.now()
        except Exception as exc:
            raise ValueError(f"TOTP generation failed: {exc}") from exc

        if not isinstance(code, str) or not code.isdigit() or len(code) != 6:
            raise ValueError(f"TOTP produced unexpected format (len={len(code)})")
        # Code is intentionally NOT logged here.
        return code

    # ── Token generation ──────────────────────────────────────────────────────

    def call_generate_token(
        self,
        client_id: str,
        pin: str,
        totp: str,
        api_key: str = "",
    ) -> str:
        """
        POST to Dhan generateAccessToken endpoint.
        Returns the new JWT access token.
        NEVER logs token, pin, or totp.
        Uses bounded retries with exponential backoff.
        """
        # Dhan API: all three fields are URL query parameters — no request body.
        params = {"dhanClientId": client_id, "pin": pin, "totp": totp}
        headers: Dict[str, str] = {}
        if api_key:
            headers["api-key"] = api_key

        last_exc: Optional[Exception] = None
        last_category = "UNKNOWN"

        for attempt in range(1, MAX_RETRIES + 2):  # attempts 1 … MAX_RETRIES+1
            t0 = time.monotonic()
            try:
                resp = requests.post(
                    GENERATE_TOKEN_URL,
                    params=params,
                    headers=headers,
                    timeout=HTTP_TIMEOUT_S,
                )
                elapsed = int((time.monotonic() - t0) * 1000)

                if resp.status_code == 200:
                    return self._parse_token_response(resp, client_id)

                # Always extract Dhan's error body for diagnostics (no credentials inside).
                dhan_detail = _extract_dhan_error(resp)

                # Determine if we should retry
                if resp.status_code in _NO_RETRY_CODES:
                    last_category = f"HTTP_{resp.status_code}_NO_RETRY"
                    raise TokenGenerationError(
                        f"Authentication failure HTTP {resp.status_code}. "
                        "Check DHAN_CLIENT_ID, DHAN_PIN, and DHAN_TOTP_SECRET.",
                        error_category=last_category,
                        dhan_detail=dhan_detail,
                    )

                if resp.status_code == 429:
                    last_category = "RATE_LIMITED"
                elif resp.status_code >= 500:
                    last_category = f"HTTP_{resp.status_code}_SERVER"
                else:
                    last_category = f"HTTP_{resp.status_code}"

                last_exc = TokenGenerationError(
                    f"HTTP {resp.status_code} from token endpoint.",
                    error_category=last_category,
                    dhan_detail=dhan_detail,
                )

            except requests.Timeout:
                last_exc = TokenGenerationError(
                    f"Timeout after {HTTP_TIMEOUT_S}s on attempt {attempt}.",
                    error_category="TIMEOUT",
                )
                last_category = "TIMEOUT"
            except TokenGenerationError:
                raise   # no-retry codes bubble immediately
            except requests.RequestException as exc:
                last_exc = TokenGenerationError(
                    f"Network error on attempt {attempt}: {type(exc).__name__}",
                    error_category="NETWORK_ERROR",
                )
                last_category = "NETWORK_ERROR"

            if attempt <= MAX_RETRIES:
                delay = _RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
                if last_category == "RATE_LIMITED":
                    delay = max(delay, 60)
                time.sleep(delay)

        raise last_exc or TokenGenerationError("Token generation failed.", last_category)

    def _parse_token_response(self, resp: requests.Response, expected_client_id: str) -> str:
        """Extract and validate access_token from a 200 response."""
        try:
            data = resp.json()
        except ValueError:
            raise TokenGenerationError(
                "Malformed JSON in token response.", error_category="MALFORMED_RESPONSE"
            )

        # Accept multiple possible key names
        token = (
            data.get("access_token")
            or data.get("accessToken")
            or data.get("token")
            or ""
        ).strip()

        if not token:
            raise TokenGenerationError(
                "Token response did not contain access_token field.",
                error_category="EMPTY_TOKEN_FIELD",
            )
        if len(token) < 20:
            raise TokenGenerationError(
                "Received token is implausibly short.",
                error_category="INVALID_TOKEN_LENGTH",
            )

        # Verify client ID if returned
        resp_client = str(data.get("dhanClientId", "")).strip()
        if resp_client and str(expected_client_id).strip() and resp_client != str(expected_client_id).strip():
            raise TokenGenerationError(
                "Response dhanClientId does not match expected client ID.",
                error_category="CLIENT_ID_MISMATCH",
            )

        # Token intentionally not logged
        return token

    # ── Idempotency check ─────────────────────────────────────────────────────

    def should_skip_generation(self) -> bool:
        """
        Return True if the current token is fresh enough that generation
        is unnecessary. Based on metadata only — no network call.
        """
        meta = load_metadata()
        if meta is None:
            return False
        if meta.status not in (STATUS_TOKEN_VALID, STATUS_TOKEN_REFRESHED):
            return False
        try:
            exp = datetime.fromisoformat(meta.expiry_time)
            hours_left = (exp - datetime.now(timezone.utc)).total_seconds() / 3600
            return hours_left >= TOKEN_REUSE_MIN_HOURS
        except Exception:
            return False

    # ── .env update + hot-reload ──────────────────────────────────────────────

    def deliver_token(self, new_token: str) -> bool:
        """
        Write token to .env and hot-reload the running DhanFeed.
        Returns True if live reload succeeded, False if only .env was updated.
        """
        env_path = _detect_env_path()
        _update_env_file(env_path, new_token)
        # Attempt live hot-reload (works when running inside container process)
        return _hot_reload_feed(new_token)

    # ── Main workflows ────────────────────────────────────────────────────────

    def run_refresh(self) -> Dict[str, Any]:
        """
        Full token generation flow.

        Returns a summary dict that NEVER contains the JWT.
        Preserves the existing token on any failure.
        """
        if not acquire_lock():
            raise ConcurrentRefreshError(
                "Another DTA refresh is already running. Skipping."
            )

        t_start = time.monotonic()
        generation_id = str(uuid.uuid4())
        client_id = ""

        try:
            # ── 1. Credentials
            creds = self.load_credentials()
            client_id = creds["DHAN_CLIENT_ID"]

            # ── 2. Clock
            self.validate_clock()

            # ── 3. Idempotency
            if self.should_skip_generation():
                meta = load_metadata()
                return {
                    "status": "SKIPPED_FRESH_TOKEN",
                    "reason": f"token has ≥{TOKEN_REUSE_MIN_HOURS}h remaining",
                    "expiry_time": meta.expiry_time if meta else "",
                    "client_id": client_id,
                }

            # ── 4. IP whitelist check
            expected_ip = creds.get("DHAN_EXPECTED_IP", "")
            if expected_ip:
                current_ip, ip_status = check_ip_whitelist(expected_ip)
                if ip_status == STATUS_IP_MISMATCH:
                    append_audit(
                        "IP_CHECK", STATUS_IP_MISMATCH,
                        client_id=client_id,
                        vps_ip=current_ip or "",
                        error_category="IP_MISMATCH",
                    )
                    raise IPMismatchError(
                        "VPS IP does not match DHAN_EXPECTED_IP. "
                        "Live order activation is blocked. "
                        "Re-whitelist the new IP on Dhan portal first."
                    )

            # ── 5. TOTP — generated but NEVER stored
            totp_code = self.generate_totp(creds["DHAN_TOTP_SECRET"])

            # ── 6. Generate token
            t_gen = time.monotonic()
            new_token = self.call_generate_token(
                client_id=client_id,
                pin=creds["DHAN_PIN"],
                totp=totp_code,
                api_key=creds.get("DHAN_API_KEY", ""),
            )
            gen_ms = int((time.monotonic() - t_gen) * 1000)
            del totp_code  # discard TOTP immediately after use

            # ── 7. Health check new token
            expiry_unix = _parse_jwt_expiry(new_token)
            ok, health_outcome = check_token_health(new_token, client_id, expiry_unix)
            if not ok:
                append_audit(
                    "GENERATION", STATUS_TOKEN_REFRESH_FAILED,
                    client_id=client_id,
                    generation_success=True,
                    health_check_success=False,
                    error_category=health_outcome,
                    duration_ms=int((time.monotonic() - t_start) * 1000),
                )
                write_health(STATUS_TOKEN_REFRESH_FAILED, {"reason": health_outcome})
                raise TokenHealthError(
                    f"New token failed profile health check: {health_outcome}. "
                    "Existing token preserved."
                )

            # ── 8. Atomic delivery (old token preserved if this fails)
            expiry_iso = _expiry_iso(new_token)
            live_reload = self.deliver_token(new_token)
            del new_token  # discard token after delivery

            # ── 9. Persist metadata
            meta = TokenMetadata(
                client_id=client_id,
                generated_at=datetime.now(timezone.utc).isoformat(),
                expiry_time=expiry_iso,
                status=STATUS_TOKEN_REFRESHED,
                generation_id=generation_id,
                source="DTA-001-TOTP",
                last_health_check=datetime.now(timezone.utc).isoformat(),
            )
            save_metadata(meta)
            write_health(STATUS_TOKEN_REFRESHED, {
                "expiry_time": expiry_iso,
                "generation_id": generation_id,
                "live_reload": live_reload,
            })
            append_audit(
                "GENERATION", STATUS_TOKEN_REFRESHED,
                client_id=client_id,
                expiry_time=expiry_iso,
                generation_success=True,
                health_check_success=True,
                duration_ms=int((time.monotonic() - t_start) * 1000),
            )

            return {
                "status": STATUS_TOKEN_REFRESHED,
                "expiry_time": expiry_iso,
                "generation_id": generation_id,
                "health_check": True,
                "live_reload": live_reload,
                "client_id": client_id,
                "duration_ms": int((time.monotonic() - t_start) * 1000),
            }

        except (CredentialError, ClockError, IPMismatchError, ConcurrentRefreshError):
            raise
        except (TokenGenerationError, TokenHealthError) as exc:
            append_audit(
                "GENERATION", STATUS_TOKEN_REFRESH_FAILED,
                client_id=client_id,
                generation_success=False,
                error_category=getattr(exc, "error_category", "UNKNOWN"),
                duration_ms=int((time.monotonic() - t_start) * 1000),
            )
            write_health(STATUS_TOKEN_REFRESH_FAILED, {
                "error_category": getattr(exc, "error_category", "UNKNOWN")
            })
            raise
        finally:
            release_lock()

    def run_dry_run(self) -> Dict[str, Any]:
        """
        Validate credentials, clock, TOTP, and config.
        Does NOT call the generateAccessToken endpoint.
        """
        results: Dict[str, Any] = {
            "mode": "DRY_RUN",
            "credentials": False,
            "clock": False,
            "totp": False,
            "config": False,
        }
        # Credentials
        try:
            creds = self.load_credentials()
            results["credentials"] = True
            results["client_id"] = creds["DHAN_CLIENT_ID"]
        except CredentialError as exc:
            results["credentials_error"] = str(exc)
            return results

        # Clock
        try:
            now = self.validate_clock()
            results["clock"] = True
            results["utc_now"] = now.isoformat()
        except ClockError as exc:
            results["clock_error"] = str(exc)
            return results

        # TOTP (generate but don't expose the code)
        try:
            code = self.generate_totp(creds["DHAN_TOTP_SECRET"])
            results["totp_validated"] = bool(code and len(code) == 6)
            del code  # discard
        except Exception as exc:
            results["totp_error"] = str(exc)
            return results

        # Config
        env_path = _detect_env_path()
        results["env_path"] = str(env_path)
        results["env_path_exists"] = env_path.exists()
        results["generate_url"] = GENERATE_TOKEN_URL
        results["config"] = True
        results["status"] = "DRY_RUN_PASSED"
        return results

    def run_health(self) -> Dict[str, Any]:
        """
        Check current token validity against Dhan profile endpoint.
        Does NOT generate a new token.
        """
        client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
        access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
        meta = load_metadata()

        if not access_token:
            write_health(STATUS_NO_TOKEN)
            return {"status": STATUS_NO_TOKEN, "metadata": None}

        expiry_unix: Optional[float] = None
        if meta:
            try:
                exp = datetime.fromisoformat(meta.expiry_time)
                expiry_unix = exp.timestamp()
            except Exception:
                pass

        ok, outcome = check_token_health(access_token, client_id, expiry_unix)
        return {
            "status": outcome,
            "health_ok": ok,
            "metadata": {
                "generated_at": meta.generated_at if meta else None,
                "expiry_time": meta.expiry_time if meta else None,
                "source": meta.source if meta else None,
            },
        }

    def run_status(self) -> Dict[str, Any]:
        """
        Return current metadata without any network calls or token exposure.
        """
        health = read_health()
        meta = load_metadata()
        token_present = bool(os.getenv("DHAN_ACCESS_TOKEN", "").strip())

        result: Dict[str, Any] = {
            "health": health.get("status", STATUS_NO_TOKEN),
            "token_present_in_env": token_present,
        }
        if meta:
            result["generated_at"] = meta.generated_at
            result["expiry_time"] = meta.expiry_time
            result["source"] = meta.source
            result["client_id"] = meta.client_id
            result["generation_id"] = meta.generation_id
            if meta.expiry_time:
                try:
                    exp = datetime.fromisoformat(meta.expiry_time)
                    hours_left = (exp - datetime.now(timezone.utc)).total_seconds() / 3600
                    result["hours_remaining"] = round(hours_left, 1)
                    result["is_expired"] = hours_left <= 0
                except Exception:
                    pass
        return result


# ── Telegram helper (non-critical — never blocks on failure) ─────────────────

def _notify(status: str, detail: str, client_id: str) -> None:
    """Send metadata-only Telegram notification. Never sends token, PIN, or TOTP."""
    try:
        from notifications.notifier_manager import get_notifier
        notifier = get_notifier()
        client_display = f"{str(client_id)[:4]}****" if client_id else "unknown"
        notifier.send_alert(
            f"🔑 DTA-001 token event: <b>{status}</b>\n"
            f"Client: {client_display}\n"
            f"{detail}"
        )
    except Exception:
        pass  # Telegram is best-effort; never fail refresh due to notification error


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> int:
    _load_dhan_env()  # load .env before argparse reads any DHAN_* vars
    parser = argparse.ArgumentParser(
        prog="dhan_token_agent",
        description="DTA-001 — Dhan access-token automation",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--refresh", action="store_true", default=False,
                       help="Generate a fresh token (default)")
    group.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="Validate config/TOTP without calling Dhan API")
    group.add_argument("--health", action="store_true",
                       help="Check current token validity")
    group.add_argument("--status", action="store_true",
                       help="Show metadata and health status (no network)")
    args = parser.parse_args()

    agent = DhanTokenAgent(dry_run=args.dry_run)
    client_id = os.getenv("DHAN_CLIENT_ID", "")

    try:
        if args.dry_run:
            result = agent.run_dry_run()
            _print_safe(result)
            return 0 if result.get("status") == "DRY_RUN_PASSED" else 1

        if args.health:
            result = agent.run_health()
            _print_safe(result)
            return 0 if result.get("health_ok") else 1

        if args.status:
            result = agent.run_status()
            _print_safe(result)
            return 0

        # Default: --refresh
        result = agent.run_refresh()
        _notify(result["status"], f"Expires: {result.get('expiry_time', 'unknown')}", client_id)
        _print_safe(result)
        return 0

    except CredentialError as exc:
        print(f"[DTA-001] CREDENTIAL_ERROR: {exc}", file=sys.stderr)
        _notify(STATUS_TOKEN_REFRESH_FAILED, "Credential error — check env vars", client_id)
        return 2
    except ClockError as exc:
        print(f"[DTA-001] CLOCK_ERROR: {exc}", file=sys.stderr)
        return 2
    except ConcurrentRefreshError as exc:
        print(f"[DTA-001] CONCURRENT_REFRESH: {exc}", file=sys.stderr)
        return 0  # not an error — another refresh is handling it
    except IPMismatchError as exc:
        print(f"[DTA-001] IP_MISMATCH: {exc}", file=sys.stderr)
        return 2
    except (TokenGenerationError, TokenHealthError) as exc:
        print(f"[DTA-001] {type(exc).__name__}: {exc}", file=sys.stderr)
        if isinstance(exc, TokenGenerationError) and exc.dhan_detail:
            print(json.dumps(exc.dhan_detail, indent=2), file=sys.stderr)
        _notify(STATUS_TOKEN_REFRESH_FAILED, f"Error: {type(exc).__name__}", client_id)
        return 1
    except Exception as exc:
        print(f"[DTA-001] UNEXPECTED_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def _print_safe(result: Dict[str, Any]) -> None:
    """Print result dict as JSON, scrubbing any accidental secret fields."""
    safe = {k: v for k, v in result.items()
            if k not in ("access_token", "token", "jwt", "pin", "totp")}
    print(json.dumps(safe, indent=2))


if __name__ == "__main__":
    sys.exit(main())
