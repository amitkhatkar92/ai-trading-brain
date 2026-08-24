"""
R-02: Dhan Static IP Verification
Calls DhanLogin.get_ip() via the dhanhq SDK (exactly as the application would),
using the current DTA-001 token.
READ-ONLY — no state is modified.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


_VPS_EXPECTED_IP = "178.18.252.24"


def _load_credentials() -> Tuple[str, str]:
    """Return (access_token, client_id) from environment."""
    token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
    client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
    return token, client_id


def call_getip_sdk(access_token: str, client_id: str) -> Dict[str, Any]:
    """
    Call DhanLogin.get_ip() via the dhanhq SDK.
    Returns the SDK wrapper dict: {status, remarks, data}.
    Raises RuntimeError if the SDK is not available.
    """
    from dhanhq.auth import DhanLogin  # noqa: PLC0415
    login = DhanLogin(client_id)
    return login.get_ip(access_token)


def verify_ip(
    raw: Union[Dict[str, Any], List[Any]],
    expected_ip: str = _VPS_EXPECTED_IP,
) -> Dict[str, Any]:
    """
    Classify an SDK or raw getIP response.

    Handles:
      - SDK wrapper:  {"status": "success", "data": [...]}
      - Direct dict:  {"primaryIP": "...", ...}
      - Dhan error:   [{"status": "ERROR", "message": "..."}]
                      or {"status": "ERROR", "message": "..."}

    Returns a result dict with keys:
      verdict, primary_ip, secondary_ip,
      modify_date_primary, modify_date_secondary,
      expected_ip, match, reason, api_status
    """
    # Unwrap SDK envelope if present
    data: Union[Dict, List, None] = raw
    if isinstance(raw, dict) and "data" in raw:
        data = raw["data"]

    # Unwrap a single-element list
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        data = data[0]

    # Detect Dhan application-level error (even inside HTTP 200)
    if isinstance(data, dict) and data.get("status") in ("ERROR", "error"):
        msg = str(data.get("message", "Dhan returned an error from /ip/getIP"))
        return {
            "verdict": "RED",
            "primary_ip": None,
            "secondary_ip": None,
            "modify_date_primary": None,
            "modify_date_secondary": None,
            "expected_ip": expected_ip,
            "match": False,
            "match_type": None,
            "reason": f"Dhan API error: {msg}",
            "api_status": "ERROR",
        }

    if not isinstance(data, dict):
        return {
            "verdict": "RED",
            "primary_ip": None,
            "secondary_ip": None,
            "modify_date_primary": None,
            "modify_date_secondary": None,
            "expected_ip": expected_ip,
            "match": False,
            "match_type": None,
            "reason": f"Unexpected response type: {type(data).__name__}",
            "api_status": "UNKNOWN_SHAPE",
        }

    primary = (data.get("primaryIP") or "").strip()
    secondary = (data.get("secondaryIP") or "").strip()
    modify_primary = data.get("modifyDatePrimary") or ""
    modify_secondary = data.get("modifyDateSecondary") or ""

    is_primary = bool(primary) and (primary == expected_ip)
    is_secondary = bool(secondary) and (secondary == expected_ip)
    is_green = is_primary or is_secondary

    match_type = (
        "PRIMARY" if is_primary
        else "SECONDARY" if is_secondary
        else None
    )
    return {
        "verdict": "GREEN" if is_green else "RED",
        "primary_ip": primary or None,
        "secondary_ip": secondary or None,
        "modify_date_primary": modify_primary or None,
        "modify_date_secondary": modify_secondary or None,
        "expected_ip": expected_ip,
        "match": is_green,
        "match_type": match_type,
        "reason": (
            f"VPS IP matched as {match_type}"
            if is_green
            else f"primaryIP={primary!r} secondaryIP={secondary!r} — neither matches expected={expected_ip!r}"
            if (primary or secondary)
            else "primaryIP and secondaryIP both absent or empty in response"
        ),
        "api_status": "OK",
    }


def run_r02_check() -> int:
    """Run the full R-02 check. Returns 0 on GREEN, 1 on RED."""
    # Load env (container path; fallback for local runs)
    env_path = "/app/.env"
    if os.path.exists(env_path):
        from dotenv import load_dotenv  # noqa: PLC0415
        load_dotenv(env_path, override=True)

    token, client_id = _load_credentials()
    if not token:
        print("[R-02] FAIL: DHAN_ACCESS_TOKEN not present")
        return 1
    if not client_id:
        print("[R-02] FAIL: DHAN_CLIENT_ID not present")
        return 1

    print(f"[R-02] Token present (len={len(token)}), client_id={client_id[:4]}****")
    print("[R-02] Calling DhanLogin.get_ip() via SDK ...")

    try:
        raw = call_getip_sdk(token, client_id)
    except Exception as exc:
        print(f"[R-02] SDK call FAILED: {exc}")
        return 1

    result = verify_ip(raw)

    print()
    print("=" * 60)
    print("  R-02 IP VERIFICATION RESULT")
    print("=" * 60)
    print(f"  Verdict:              {result['verdict']}")
    print(f"  Match type:           {result.get('match_type') or 'NONE'}")
    print(f"  primaryIP:            {result['primary_ip']}")
    print(f"  secondaryIP:          {result['secondary_ip']}")
    print(f"  modifyDatePrimary:    {result['modify_date_primary']}")
    print(f"  modifyDateSecondary:  {result['modify_date_secondary']}")
    print(f"  Expected VPS IP:      {result['expected_ip']}")
    print(f"  API status:           {result['api_status']}")
    print(f"  Reason:               {result['reason']}")
    print("=" * 60)

    return 0 if result["verdict"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(run_r02_check())
