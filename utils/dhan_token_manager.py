"""
Dhan Token Manager
==================

Dynamic token lifecycle management with file watching and expiration alerts.

Features:
  ✓ Load token from config/api_tokens.json
  ✓ Watch for token changes (auto-reload)
  ✓ Detect expired/stale tokens
  ✓ Alert system when tokens expire
  ✓ Fallback to environment variables if file token unavailable

Usage:
  from utils.dhan_token_manager import get_dhan_token, watch_token_file_start

  # Load token initially
  token = get_dhan_token()

  # Optionally start watcher for auto-reload
  watch_token_file_start()

  # Later, token will auto-update if config/api_tokens.json changes
  token = get_dhan_token()  # Returns latest token
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import atexit

from utils import get_logger

log = get_logger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TOKEN_FILE = CONFIG_DIR / "api_tokens.json"

# Global state
_current_token: Optional[str] = None
_last_load_time: Optional[datetime] = None
_file_watcher_thread: Optional[threading.Thread] = None
_watcher_should_stop = threading.Event()
_token_lock = threading.Lock()

# Token expiration settings
# CRITICAL: Dhan tokens are DAILY SESSION tokens, NOT 30-day tokens
# Each trading day requires a NEW token at market open (09:15 IST)
# Token expires at end of trading session (16:51 UTC)
TOKEN_TTL_DAYS = 1     # Dhan tokens valid for 1 day only (daily session)
TOKEN_WARN_MINUTES = 10  # Warn 10 mins before market close (16:51 UTC)
TOKEN_WARN_DAYS = 0    # Deprecat ed - use minutes for daily tokens


def get_dhan_token() -> Optional[str]:
    """
    Get the current Dhan access token.

    Priority:
      1. Captured token from OAuth (config/api_tokens.json)
      2. Environment variable (DHAN_ACCESS_TOKEN)
      3. None if nothing available

    Returns:
        str: Access token if available, None otherwise
    """
    global _current_token, _last_load_time

    with _token_lock:
        # Try to load from config file first (OAuth-captured)
        token = _load_token_from_file()
        if token:
            _current_token = token
            _last_load_time = datetime.utcnow()
            return token

        # Fallback to environment variable
        token = os.getenv("DHAN_ACCESS_TOKEN", "")
        if token:
            log.debug(
                "Using Dhan token from environment variable "
                "(not from OAuth capture)"
            )
            return token

        log.warning("No Dhan access token available (file or env)")
        return None


def _load_token_from_file() -> Optional[str]:
    """
    Load token from config/api_tokens.json.

    Supports two formats:
    
    NEW FORMAT (access_token with 30-day expiry):
      {
        "access_token": "JWT_TOKEN",
        "client_id": "2603183256",
        "captured_at": "2026-03-18T11:09:00Z",
        "expires_at": "2026-04-17T11:09:00Z",
        "ttl_days": 30,
        "status": "active"
      }

    OLD FORMAT (authorization code):
      {
        "dhan_request_code": "CODE_VALUE",
        "captured_at": "2026-03-18T11:09:00Z",
        "status": "captured"
      }

    Returns:
        str: Token value if valid, None if expired or missing
    """
    if not TOKEN_FILE.exists():
        return None

    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)

        # Try new format first (access_token)
        token = data.get("access_token")
        token_type = "access_token (NEW)"
        
        # Fallback to old format (dhan_request_code)
        if not token:
            token = data.get("dhan_request_code")
            token_type = "authorization_code (OLD)"

        if not token:
            log.warning(f"Token file exists but no token found")
            return None

        # Check if token is expired by expires_at field (if present)
        expires_at_str = data.get("expires_at")
        token_type_field = data.get("token_type", "Bearer")  # Can be "Bearer" or "DAILY_SESSION"
        
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                now = datetime.utcnow()
                
                # Check if token is expired
                if now > expires_at:
                    days_expired = (now - expires_at).days
                    hours_expired = (now - expires_at).total_seconds() / 3600
                    log.error(
                        f"❌ Token EXPIRED {hours_expired:.1f} hours ago "
                        f"[was: {expires_at.isoformat()}]"
                    )
                    _emit_token_expiration_alert(expires_at, hours_expired)
                    return None
                
                # For DAILY_SESSION tokens: check if expiring soon (< 10 mins)
                if token_type_field == "DAILY_SESSION":
                    seconds_left = (expires_at - now).total_seconds()
                    minutes_left = seconds_left / 60
                    if minutes_left < TOKEN_WARN_MINUTES:
                        log.warning(
                            f"⚠️  DAILY token expiring SOON ({minutes_left:.0f} mins) - "
                            f"daily refresh required"
                        )
                    elif seconds_left < 3600:  # Less than 1 hour
                        log.info(
                            f"ℹ️  DAILY token valid for {minutes_left:.0f} more minutes"
                        )
                else:
                    # For regular Bearer tokens: check if refresh needed (< 3 days left)
                    days_left = (expires_at - now).total_seconds() / (24 * 3600)
                    if days_left < TOKEN_WARN_DAYS:
                        log.warning(
                            f"⚠️  Token expiring soon ({days_left:.1f} days left) - "
                            f"recommend refresh"
                        )

            except Exception as e:
                log.debug(f"Could not parse expires_at timestamp: {e}")

        # Fallback: check age from captured_at for old format
        elif data.get("captured_at"):
            try:
                captured_at = datetime.fromisoformat(
                    data["captured_at"].replace("Z", "+00:00")
                )
                age_days = (datetime.utcnow() - captured_at).days
                
                if age_days > TOKEN_TTL_DAYS:
                    log.warning(
                        f"Token expired (age: {age_days} days > {TOKEN_TTL_DAYS} TTL)"
                    )
                    _emit_token_expiration_alert(captured_at, age_days)
                    return None
                
                if age_days > (TOKEN_TTL_DAYS - TOKEN_WARN_DAYS):
                    days_left = TOKEN_TTL_DAYS - age_days
                    log.warning(
                        f"⚠️  Token expiring soon ({days_left} days remaining)"
                    )

            except Exception as e:
                log.debug(f"Could not parse captured_at timestamp: {e}")

        log.info(f"✅ Dhan token loaded from config/api_tokens.json [{token_type}]")
        return token

    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in token file: {e}")
        return None
    except Exception as e:
        log.error(f"Failed to load token from file: {e}")
        return None


def load_token() -> Optional[str]:
    """Alias for get_dhan_token()."""
    return get_dhan_token()


def _emit_token_expiration_alert(captured_at: datetime, age_days: int):
    """Emit alert when token expires."""
    log.critical(
        f"🚨 DHAN TOKEN EXPIRED 🚨 | "
        f"Captured: {captured_at.isoformat()} | "
        f"Age: {age_days} days | "
        f"Action: Re-login to Dhan browser to capture new token"
    )

    # Send Telegram alert if configured
    try:
        from notifications.telegram_bot import send_alert
        send_alert(
            severity="CRITICAL",
            title="Dhan Token Expired",
            message=f"Token captured {age_days} days ago has expired. "
                    f"Please login to Dhan to capture new token."
        )
    except Exception as e:
        log.debug(f"Telegram alert failed (optional): {e}")


def watch_token_file_start(poll_interval: int = 30):
    """
    Start background thread to watch for token file changes.

    When config/api_tokens.json changes, automatically reloads token.
    Detects expirations and emits alerts.

    Args:
        poll_interval: Check frequency in seconds (default 30s)
    """
    global _file_watcher_thread

    if _file_watcher_thread and _file_watcher_thread.is_alive():
        log.debug("Token file watcher already running")
        return

    _watcher_should_stop.clear()

    _file_watcher_thread = threading.Thread(
        target=_watch_token_file_loop,
        args=(poll_interval,),
        daemon=True,
        name="DhanTokenFileWatcher"
    )
    _file_watcher_thread.start()
    log.info(f"✓ Token file watcher started (poll={poll_interval}s)")

    # Ensure cleanup on exit
    atexit.register(watch_token_file_stop)


def _watch_token_file_loop(poll_interval: int):
    """Background loop to monitor token file."""
    last_mtime = None
    last_token = None

    while not _watcher_should_stop.is_set():
        try:
            if TOKEN_FILE.exists():
                current_mtime = TOKEN_FILE.stat().st_mtime

                # File was modified
                if last_mtime and current_mtime > last_mtime:
                    log.info("Token file changed, reloading...")
                    new_token = get_dhan_token()
                    
                    if new_token != last_token:
                        log.info(
                            f"✓ Token updated from file "
                            f"[{new_token[:10]}...{new_token[-5:]}]"
                        )
                        last_token = new_token

                last_mtime = current_mtime

        except Exception as e:
            log.debug(f"Token file watcher error: {e}")

        # Sleep with interruptible wait
        _watcher_should_stop.wait(timeout=poll_interval)


def watch_token_file_stop():
    """Stop the token file watcher thread."""
    global _file_watcher_thread

    _watcher_should_stop.set()

    if _file_watcher_thread and _file_watcher_thread.is_alive():
        _file_watcher_thread.join(timeout=5)
        log.info("Token file watcher stopped")


def get_token_status() -> Dict[str, Any]:
    """
    Get current token status for monitoring.

    Returns:
        dict: Status information about current token
    """
    token = get_dhan_token()
    captured_at = None

    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE) as f:
                data = json.load(f)
                captured_at = data.get("captured_at")
        except Exception:
            pass

    age_days = None
    if captured_at:
        try:
            dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            age_days = (datetime.utcnow() - dt).days
        except Exception:
            pass

    return {
        "has_token": bool(token),
        "source": "file" if TOKEN_FILE.exists() else "env",
        "captured_at": captured_at,
        "age_days": age_days,
        "expires_in_days": TOKEN_TTL_DAYS - (age_days or 0),
        "status_file": str(TOKEN_FILE),
        "watcher_running": _file_watcher_thread and _file_watcher_thread.is_alive(),
    }
