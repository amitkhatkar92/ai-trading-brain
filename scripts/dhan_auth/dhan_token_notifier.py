"""
DTA-003 — Dhan Token Telegram Notifier
========================================
Formats and sends metadata-only Telegram notifications for DTA-001/DTA-002
token lifecycle events.

Security invariants (enforced here and asserted in tests):
  - JWT (DHAN_ACCESS_TOKEN) NEVER appears in any message
  - DHAN_PIN               NEVER appears in any message
  - DHAN_TOTP_SECRET       NEVER appears in any message
  - DHAN_API_KEY / secret  NEVER appears in any message
  - generation_id shown as last-8-chars only

Idempotency:
  - One success notification per generation_id
  - Failure notifications rate-limited to one per _FAILURE_COOLDOWN_S (1h)

Failure-safety:
  - All Telegram calls are wrapped; exceptions are silently swallowed
  - A notification failure NEVER stops DTA-001 or DTA-002
"""
from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

# JWT / credential value patterns — anything matching is ALWAYS redacted
_CREDENTIAL_RE = re.compile(
    r"eyJ[A-Za-z0-9_\-]{10,}"     # JWT header prefix
    r"|(?<!\d)\d{6}(?!\d)"         # 6-digit TOTP code
)

_FAILURE_COOLDOWN_S: int = 3600   # send at most one failure alert per hour

# ── Module singleton ──────────────────────────────────────────────────────────

_NOTIFIER_INSTANCE: Optional["DhanTokenNotifier"] = None
_NOTIFIER_LOCK = threading.Lock()


def get_token_notifier() -> "DhanTokenNotifier":
    """Return the process-level DhanTokenNotifier singleton."""
    global _NOTIFIER_INSTANCE
    if _NOTIFIER_INSTANCE is None:
        with _NOTIFIER_LOCK:
            if _NOTIFIER_INSTANCE is None:
                _NOTIFIER_INSTANCE = DhanTokenNotifier()
    return _NOTIFIER_INSTANCE


# ── Formatting helpers ────────────────────────────────────────────────────────

def _short_gen(gen_id: str) -> str:
    """Return last 8 chars of a UUID for safe display (not reversible)."""
    return ("..." + gen_id[-8:]) if len(gen_id) >= 8 else gen_id


def _to_ist(iso: str) -> str:
    """Convert UTC ISO-8601 string to a human-readable IST string."""
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
        return ist.strftime("%H:%M  %d %b %Y  IST")
    except Exception:
        return iso[:19] if iso else "—"


def _remaining(expiry_iso: str) -> str:
    """Format time remaining until expiry as 'Xh Ym'."""
    try:
        exp = datetime.fromisoformat(expiry_iso)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        delta = exp - datetime.now(timezone.utc)
        total_s = int(delta.total_seconds())
        if total_s <= 0:
            return "EXPIRED"
        h, rem = divmod(total_s, 3600)
        m = rem // 60
        return f"{h}h {m}m"
    except Exception:
        return "—"


def _esc(text: str) -> str:
    """HTML-escape for Telegram HTML parse mode."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _redact(text: str) -> str:
    """Remove any accidental credential fragments from a string."""
    return _CREDENTIAL_RE.sub("[REDACTED]", str(text))


def _live_reload_label(live_reload: Any) -> str:
    """Map live_reload value (bool/str) to a human label."""
    if live_reload is True or live_reload == "PASS":
        return "✅ PASS"
    if live_reload == "FAIL":
        return "❌ FAIL"
    # False from docker exec subprocess means DTA-002 will sync shortly
    return "⏳ PENDING  (DTA-002 syncs within 5 min)"


# ── Notifier class ────────────────────────────────────────────────────────────

class DhanTokenNotifier:
    """
    Idempotent, credential-safe Telegram notification for DTA-001/DTA-002 events.
    Use get_token_notifier() to obtain the process singleton.
    """

    def __init__(self) -> None:
        self._last_notified_gen_id: Optional[str] = None
        self._last_failure_ts: float = 0.0
        self._lock = threading.Lock()

    # ── Success notification ──────────────────────────────────────────────────

    def notify_refresh_success(self, result: Dict[str, Any]) -> None:
        """
        Send one Telegram notification per generation_id after TOKEN_REFRESHED.

        Args:
            result: The dict returned by DhanTokenAgent.run_refresh().
                    Must NOT contain the JWT — it is a metadata-only dict.
        """
        gen_id = str(result.get("generation_id", ""))
        if not gen_id:
            return

        with self._lock:
            if gen_id == self._last_notified_gen_id:
                return  # already sent for this generation
            self._last_notified_gen_id = gen_id

        expiry_iso = result.get("expiry_time", "")
        health_ok  = result.get("health_check", False)
        live_reload = result.get("live_reload", False)
        generated_at = result.get("generated_at") or datetime.now(timezone.utc).isoformat()

        msg = (
            "✅ <b>DHAN TOKEN REFRESHED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status:       TOKEN_REFRESHED\n"
            f"Generation:   <code>{_esc(_short_gen(gen_id))}</code>\n"
            f"Generated:    {_esc(_to_ist(generated_at))}\n"
            f"Expires:      {_esc(_to_ist(expiry_iso))}\n"
            f"Remaining:    {_esc(_remaining(expiry_iso))}\n"
            f"Health check: {'✅ PASS' if health_ok else '❌ FAIL'}\n"
            f"Live reload:  {_live_reload_label(live_reload)}"
        )
        try:
            self._push(msg)
        except Exception:
            pass

    def notify_reload_result(self, gen_id: str, success: bool, error: str = "") -> None:
        """
        Called by DTA-002 when the main-process reload completes.
        Sends a brief follow-up ONLY if the reload failed (success is silent).
        """
        if success:
            return  # no extra message on clean reload
        if not gen_id:
            return
        with self._lock:
            now = time.monotonic()
            if now - self._last_failure_ts < _FAILURE_COOLDOWN_S:
                return
            self._last_failure_ts = now

        safe_error = _esc(_redact(error[:120]))
        msg = (
            "⚠️ <b>DTA-002: Live Reload Failed</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"Generation:  <code>{_esc(_short_gen(gen_id))}</code>\n"
            f"Error:       {safe_error}\n"
            "DTA-002 will retry automatically on the next 5-min cycle."
        )
        try:
            self._push(msg)
        except Exception:
            pass

    # ── Failure notification ──────────────────────────────────────────────────

    def notify_refresh_failure(
        self,
        error_category: str,
        current_token_state: str = "",
        http_status: Optional[int] = None,
        retry: bool = False,
    ) -> None:
        """
        Send a rate-limited (1/h) Telegram alert when DTA-001 refresh fails.
        NEVER includes credentials, JWT, PIN, TOTP, or API keys.
        """
        with self._lock:
            now = time.monotonic()
            if now - self._last_failure_ts < _FAILURE_COOLDOWN_S:
                return
            self._last_failure_ts = now

        safe_cat = _esc(_redact(error_category[:80]))
        safe_state = _esc(current_token_state[:40]) if current_token_state else "unknown"
        http_line = f"HTTP status:    {http_status}\n" if http_status else ""
        retry_label = "Yes — server error, will retry" if retry else "No — credentials rejected"

        msg = (
            "🔴 <b>DHAN TOKEN REFRESH FAILED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"{http_line}"
            f"Error:          {safe_cat}\n"
            f"Retry:          {_esc(retry_label)}\n"
            f"Token state:    {safe_state}\n"
            f"Time:           {_esc(_to_ist(datetime.now(timezone.utc).isoformat()))}\n"
            "Run <code>--status</code> on the VPS for details."
        )
        try:
            self._push(msg)
        except Exception:
            pass

    # ── Push helper ───────────────────────────────────────────────────────────

    def _push(self, message: str) -> None:
        """Fire-and-forget Telegram push. Swallows all exceptions."""
        try:
            from notifications.telegram_bot import get_telegram_bot
            get_telegram_bot().push(message)
        except Exception:
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().send_alert(message)
            except Exception:
                pass  # notification failure must never affect trading or token refresh


# ── Format helpers (exported for /token_status and /trading_status commands) ──

def format_token_status_message(sync_gen_id: Optional[str] = None) -> str:
    """
    Build a /token_status reply from DTA-001 metadata + DTA-002 sync state.
    Never includes JWT, PIN, TOTP, or API keys.
    """
    try:
        from scripts.dhan_auth.dhan_token_store import load_metadata, read_health
    except ImportError:
        try:
            from dhan_token_store import load_metadata, read_health  # type: ignore[no-redef]
        except ImportError:
            return "⚠️ Token store unavailable."

    meta   = load_metadata()
    health = read_health()

    if meta is None:
        return (
            "🔑 <b>Dhan Token Status</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Status:  NO_TOKEN\n"
            "No token metadata found. Run <code>--refresh</code> on the VPS."
        )

    gen_id      = meta.generation_id or ""
    expiry_iso  = meta.expiry_time   or ""
    gen_at      = meta.generated_at  or ""
    status      = meta.status        or "UNKNOWN"
    rem         = _remaining(expiry_iso)
    health_ok   = health.get("status") not in ("TOKEN_REFRESH_FAILED", "NO_TOKEN")
    live_reload = health.get("live_reload", None)

    # Determine if DTA-002 has loaded this generation into PID-1
    if sync_gen_id and sync_gen_id == gen_id:
        sync_label = f"✅ LOADED  (gen ...{gen_id[-8:]})"
    elif sync_gen_id:
        sync_label = f"⏳ PENDING  (PID-1 has gen ...{sync_gen_id[-8:]})"
    else:
        sync_label = "⏳ PENDING"

    return (
        "🔑 <b>Dhan Token Status</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"Status:       {_esc(status)}\n"
        f"Generation:   <code>{_esc(_short_gen(gen_id))}</code>\n"
        f"Generated:    {_esc(_to_ist(gen_at))}\n"
        f"Expires:      {_esc(_to_ist(expiry_iso))}\n"
        f"Remaining:    {_esc(rem)}\n"
        f"Health:       {'✅ OK' if health_ok else '❌ FAILED'}\n"
        f"PID-1 sync:   {_esc(sync_label)}"
    )


def format_trading_status_message(
    sync_gen_id: Optional[str] = None,
    last_sync_ts: Optional[float] = None,
) -> str:
    """
    Build a /trading_status reply.
    Never includes JWT, PIN, TOTP, or API keys.
    """
    # Token state
    try:
        from scripts.dhan_auth.dhan_token_sync import get_token_sync
        token_state = get_token_sync().get_token_state()
    except Exception:
        token_state = "UNKNOWN"

    # Token metadata for remaining time
    rem = "—"
    try:
        from scripts.dhan_auth.dhan_token_store import load_metadata
        meta = load_metadata()
        if meta and meta.expiry_time:
            rem = _remaining(meta.expiry_time)
    except Exception:
        pass

    # Dhan feed status
    dhan_live_label = "unknown"
    try:
        from data_feeds import get_feed_manager
        dhan_live_label = "✅ LIVE" if get_feed_manager().dhan.is_live else "⚡ SIM"
    except Exception:
        pass

    # Paper/live mode
    mode_label = "PAPER"
    try:
        import config as _cfg
        mode_label = "PAPER" if getattr(_cfg, "PAPER_TRADING", True) else "LIVE"
    except Exception:
        pass

    # Last sync timestamp
    last_sync_label = "—"
    if last_sync_ts is not None:
        elapsed = int(time.monotonic() - last_sync_ts)
        last_sync_label = f"{elapsed}s ago"

    sync_label = f"...{sync_gen_id[-8:]}" if sync_gen_id and len(sync_gen_id) >= 8 else (sync_gen_id or "none")

    return (
        "📊 <b>Trading Status</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"Engine:       ▶ RUNNING ({_esc(mode_label)})\n"
        f"Token state:  {_esc(token_state)}  ({_esc(rem)} remaining)\n"
        f"PID-1 sync:   {_esc(sync_label)}\n"
        f"Last sync:    {_esc(last_sync_label)}\n"
        f"Dhan feed:    {_esc(dhan_live_label)}\n"
        "Broker calls: 0\n"
        "Orders:       0"
    )
