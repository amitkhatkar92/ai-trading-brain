"""
DTA-001 — Token Metadata Store
================================
Stores token STATUS and METADATA only.

The actual JWT lives exclusively in .env — it never appears in any JSON file,
CSV, report, log line, Telegram message, or Git-tracked file.

Persistent paths (all inside the data/ bind-mount on VPS):
    data/dhan_token_store.json     — token lifecycle metadata
    data/dhan_token_health.json    — current health status (consumed by broker init)
    data/logs/dhan_token_audit.jsonl — append-only audit trail
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ── Paths ────────────────────────────────────────────────────────────────────

# Support both in-container (/app/data) and standalone usage
_APP_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = _APP_ROOT / "data"

STORE_PATH = DATA_DIR / "dhan_token_store.json"
HEALTH_PATH = DATA_DIR / "dhan_token_health.json"
AUDIT_PATH = DATA_DIR / "logs" / "dhan_token_audit.jsonl"
LOCK_PATH = Path("/tmp/dta_refresh.lock")

# ── Status constants ─────────────────────────────────────────────────────────

STATUS_NO_TOKEN = "NO_TOKEN"
STATUS_TOKEN_VALID = "TOKEN_VALID"
STATUS_TOKEN_EXPIRING = "TOKEN_EXPIRING"     # < 2 h remaining
STATUS_TOKEN_REFRESHED = "TOKEN_REFRESHED"
STATUS_TOKEN_REFRESH_FAILED = "TOKEN_REFRESH_FAILED"
STATUS_TOKEN_INVALID = "TOKEN_INVALID"
STATUS_IP_MISMATCH = "DHAN_IP_MISMATCH"

ALL_STATUSES = frozenset({
    STATUS_NO_TOKEN,
    STATUS_TOKEN_VALID,
    STATUS_TOKEN_EXPIRING,
    STATUS_TOKEN_REFRESHED,
    STATUS_TOKEN_REFRESH_FAILED,
    STATUS_TOKEN_INVALID,
    STATUS_IP_MISMATCH,
})

# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class TokenMetadata:
    client_id: str                     # plaintext — not a secret
    generated_at: str                  # ISO-8601 UTC
    expiry_time: str                   # ISO-8601 UTC
    status: str                        # one of ALL_STATUSES
    generation_id: str                 # UUID for correlation
    source: str                        # "DTA-001-TOTP"
    last_health_check: Optional[str] = None   # ISO-8601 UTC or None
    error_category: str = ""

# ── Internal helpers ─────────────────────────────────────────────────────────

def _sha_prefix(value: str) -> str:
    """Return first 16 hex chars of SHA-256 — enough for audit correlation, not reversible."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)

# ── Public API ───────────────────────────────────────────────────────────────

def save_metadata(meta: TokenMetadata) -> None:
    """Persist token metadata. Never contains the JWT itself."""
    _atomic_write(STORE_PATH, json.dumps(asdict(meta), indent=2))


def load_metadata() -> Optional[TokenMetadata]:
    """Load most recent metadata, or None if not found/corrupt."""
    if not STORE_PATH.exists():
        return None
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        return TokenMetadata(**data)
    except Exception:
        return None


def write_health(status: str, detail: Optional[Dict[str, Any]] = None) -> None:
    """Write health JSON. Never contains the JWT, PIN, TOTP, or API secret."""
    if status not in ALL_STATUSES:
        raise ValueError(f"Unknown health status: {status!r}")
    payload: Dict[str, Any] = {
        "status": status,
        "timestamp": _now_iso(),
    }
    if detail:
        # Strip any accidentally included secret fields before writing
        safe = {k: v for k, v in detail.items()
                if k not in ("access_token", "token", "jwt", "pin", "totp",
                             "totp_secret", "api_secret", "api_key")}
        payload.update(safe)
    _atomic_write(HEALTH_PATH, json.dumps(payload, indent=2))


def read_health() -> Dict[str, Any]:
    """Read current health status. Safe to call at any time."""
    if not HEALTH_PATH.exists():
        return {"status": STATUS_NO_TOKEN, "timestamp": _now_iso()}
    try:
        return json.loads(HEALTH_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"status": STATUS_TOKEN_INVALID, "timestamp": _now_iso()}


def append_audit(
    event: str,
    status: str,
    *,
    client_id: str = "",
    expiry_time: str = "",
    generation_success: bool = False,
    health_check_success: bool = False,
    vps_ip: str = "",
    error_category: str = "",
    duration_ms: int = 0,
) -> None:
    """
    Append one record to the audit trail.

    NEVER includes: access_token, pin, totp, api_secret.
    Hashes: client_id, vps_ip (for correlation without exposure).
    """
    record = {
        "timestamp": _now_iso(),
        "event": event,
        "status": status,
        "client_id_hash": _sha_prefix(client_id) if client_id else "",
        "expiry_time": expiry_time,
        "generation_success": generation_success,
        "health_check_success": health_check_success,
        "vps_ip_hash": _sha_prefix(vps_ip) if vps_ip else "",
        "error_category": error_category,
        "duration_ms": duration_ms,
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── Lock helpers ─────────────────────────────────────────────────────────────

def _is_pid_alive(pid: int) -> bool:
    """Cross-platform process existence check.

    POSIX: os.kill(pid, 0) is standard for checking process existence.
    Windows: os.kill(pid, 0) sends CTRL_C_EVENT (=0) to the process, which
    raises KeyboardInterrupt in the current process.  Use ctypes instead.
    """
    import sys
    if sys.platform == "win32":
        import ctypes
        PROCESS_QUERY_INFORMATION = 0x0400
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong(0)
        alive = bool(
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            and code.value == STILL_ACTIVE
        )
        ctypes.windll.kernel32.CloseHandle(handle)
        return alive
    else:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False


def acquire_lock() -> bool:
    """Return True if refresh lock acquired; False if another refresh is running."""
    try:
        if LOCK_PATH.exists():
            try:
                pid = int(LOCK_PATH.read_text().strip())
                if _is_pid_alive(pid):
                    return False   # process alive — lock held
            except (ValueError, OSError):
                pass               # stale lock — take it over
        LOCK_PATH.write_text(str(os.getpid()))
        return True
    except Exception:
        return True  # fail open (don't block on unexpected filesystem errors)


def release_lock() -> None:
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass
