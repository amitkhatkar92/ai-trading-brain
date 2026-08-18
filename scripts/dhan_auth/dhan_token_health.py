"""
DTA-001 — Token Health Checker
================================
Validates current token by calling Dhan's profile endpoint.
Also provides VPS public-IP lookup for whitelist verification.

Endpoint:
    GET  https://api.dhan.co/v2/profile
    Headers: access-token: <JWT>, Content-Type: application/json

Health outcomes:
    TOKEN_VALID      — authenticated, client ID matches
    TOKEN_INVALID    — rejected by Dhan (401/403) or bad response
    TOKEN_EXPIRING   — valid but < TOKEN_EXPIRY_WARN_H hours left
    TIMEOUT          — Dhan unreachable within deadline
    NETWORK_ERROR    — low-level connectivity failure
    CLIENT_ID_MISMATCH — profile returned a different dhanClientId
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional, Tuple

import requests

from .dhan_token_store import (
    STATUS_IP_MISMATCH,
    STATUS_TOKEN_INVALID,
    STATUS_TOKEN_VALID,
    append_audit,
    write_health,
)

PROFILE_URL = "https://api.dhan.co/v2/profile"
HTTP_TIMEOUT = 10              # seconds
TOKEN_EXPIRY_WARN_H = 2.0     # mark EXPIRING if < 2 h left


def check_token_health(
    access_token: str,
    client_id: str,
    expiry_unix: Optional[float] = None,
    notifier=None,
) -> Tuple[bool, str]:
    """
    Validate the token against Dhan's profile endpoint.

    Returns (success: bool, outcome: str).
    Never logs or propagates the token value itself.
    """
    if not access_token:
        write_health("NO_TOKEN")
        append_audit("HEALTH_CHECK", "NO_TOKEN", client_id=client_id)
        return False, "NO_TOKEN"

    t0 = time.monotonic()
    try:
        resp = requests.get(
            PROFILE_URL,
            headers={
                "access-token": access_token,
                "Content-Type": "application/json",
            },
            timeout=HTTP_TIMEOUT,
        )
        elapsed = int((time.monotonic() - t0) * 1000)

        if resp.status_code == 200:
            data: dict = resp.json() if resp.text else {}
            resp_client = str(data.get("dhanClientId", "")).strip()
            if resp_client and str(client_id).strip() and resp_client != str(client_id).strip():
                _write_invalid("CLIENT_ID_MISMATCH", client_id, elapsed)
                return False, "CLIENT_ID_MISMATCH"

            # Determine if expiring soon
            status = STATUS_TOKEN_VALID
            if expiry_unix is not None:
                hours_left = (expiry_unix - time.time()) / 3600
                if hours_left < TOKEN_EXPIRY_WARN_H:
                    status = "TOKEN_EXPIRING"

            write_health(status, {
                "client_id": resp_client or str(client_id),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })
            append_audit(
                "HEALTH_CHECK", status,
                client_id=client_id,
                health_check_success=True,
                duration_ms=elapsed,
            )
            _maybe_notify(notifier, status, client_id)
            return True, status

        elif resp.status_code in (401, 403):
            _write_invalid(f"AUTH_FAILED_HTTP_{resp.status_code}", client_id, elapsed)
            return False, f"AUTH_FAILED_HTTP_{resp.status_code}"

        else:
            _write_invalid(f"HTTP_{resp.status_code}", client_id, elapsed)
            return False, f"HTTP_{resp.status_code}"

    except requests.Timeout:
        elapsed = int((time.monotonic() - t0) * 1000)
        _write_invalid("TIMEOUT", client_id, elapsed, error_category="TIMEOUT")
        return False, "TIMEOUT"

    except requests.RequestException as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        _write_invalid("NETWORK_ERROR", client_id, elapsed, error_category="NETWORK_ERROR")
        return False, f"NETWORK_ERROR"


def _write_invalid(reason: str, client_id: str, elapsed: int, error_category: str = "") -> None:
    write_health(STATUS_TOKEN_INVALID, {"reason": reason})
    append_audit(
        "HEALTH_CHECK",
        STATUS_TOKEN_INVALID,
        client_id=client_id,
        health_check_success=False,
        duration_ms=elapsed,
        error_category=error_category or reason,
    )


def _maybe_notify(notifier, status: str, client_id: str) -> None:
    if notifier is None:
        return
    try:
        # Send only metadata — never the token
        notifier.send_alert(
            f"🔑 Dhan token health check: <b>{status}</b>\n"
            f"Client ID: {client_id[:4]}****"
        )
    except Exception:
        pass


def get_vps_public_ip(timeout: int = 5) -> Optional[str]:
    """Fetch current VPS public IP. Returns None on failure."""
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                ip = r.text.strip()
                if ip:
                    return ip
        except Exception:
            continue
    return None


def check_ip_whitelist(expected_ip: str, notifier=None) -> Tuple[Optional[str], str]:
    """
    Fetch current VPS IP and compare against expected_ip.
    Returns (current_ip, status).  Never logs IP in plaintext.
    """
    current = get_vps_public_ip()
    if current is None:
        return None, "IP_FETCH_FAILED"

    if expected_ip and current != expected_ip:
        write_health(STATUS_IP_MISMATCH, {"reason": "ip_whitelist_mismatch"})
        if notifier:
            try:
                notifier.send_alert(
                    "🚨 <b>DHAN_IP_MISMATCH</b> — VPS public IP has changed.\n"
                    "Live order activation BLOCKED until IP is re-whitelisted on Dhan."
                )
            except Exception:
                pass
        return current, STATUS_IP_MISMATCH

    return current, "IP_OK"
