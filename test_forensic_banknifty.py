"""
BANKNIFTY Forensic Test Script — 5-Test Battery
================================================
Tests 1–5: raw HTTP vs SDK parity, multi-expiry matrix, JSON snapshots, diff, network path.

Deploy and run inside Docker container:
  scp -i ~/.ssh/trading_vps test_forensic_banknifty.py root@178.18.252.24:/tmp/
  ssh -i ~/.ssh/trading_vps root@178.18.252.24 "docker cp /tmp/test_forensic_banknifty.py ai-trading-brain:/tmp/ && docker exec ai-trading-brain python /tmp/test_forensic_banknifty.py 2>&1"
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import socket
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "/app")

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("forensic")

# ── Output directory ────────────────────────────────────────────────────────
FORENSICS_DIR = pathlib.Path("/tmp/forensics")
FORENSICS_DIR.mkdir(parents=True, exist_ok=True)

# ── Credentials ─────────────────────────────────────────────────────────────
try:
    import config as cfg
    CLIENT_ID    = str(cfg.DHAN_CLIENT_ID)
    ACCESS_TOKEN = cfg.DHAN_ACCESS_TOKEN
except Exception as _ce:
    # Fall back to environment variables
    CLIENT_ID    = os.getenv("DHAN_CLIENT_ID", "")
    ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

if not CLIENT_ID or not ACCESS_TOKEN:
    log.error("[Forensic] Missing credentials — set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN")
    sys.exit(1)

log.info("[Forensic] Credentials loaded: client_id=%s  token_sfx=%s",
         CLIENT_ID, ACCESS_TOKEN[-8:])

# ── Constants ───────────────────────────────────────────────────────────────
BASE_URL = "https://api.dhan.co/v2"

# Exact headers the SDK uses (from dhanhq.py line 1078–1082)
SDK_HEADERS = {
    "Accept":        "application/json",
    "Content-Type":  "application/json",
    "access-token":  ACCESS_TOKEN,
    "client-id":     CLIENT_ID,
}

SYMBOLS: List[Dict[str, Any]] = [
    {"name": "NIFTY",     "security_id": 13},
    {"name": "BANKNIFTY", "security_id": 25},
]

SEGMENT = "IDX_I"

# ── Helper ──────────────────────────────────────────────────────────────────

def _save_json(name: str, data: Any) -> pathlib.Path:
    path = FORENSICS_DIR / f"{name}.json"
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return path
    except Exception as e:
        log.warning("[Forensic] Could not save %s: %s", path, e)
        return path


def _raw_post(url: str, payload: dict, headers: dict, timeout: int = 12) -> Tuple[int, dict, float]:
    """Make a raw POST and return (http_status, parsed_body, latency_ms)."""
    t0 = time.perf_counter()
    r  = requests.post(url, json=payload, headers=headers, timeout=timeout)
    latency_ms = (time.perf_counter() - t0) * 1000
    try:
        body = r.json()
    except Exception:
        body = {"_raw_text": r.text[:500]}
    return r.status_code, body, latency_ms


def _get_structure(obj: Any, depth: int = 0) -> Any:
    """Recursively describe the type structure of a dict/list."""
    if depth > 3:
        return type(obj).__name__
    if isinstance(obj, dict):
        return {k: _get_structure(v, depth + 1) for k, v in list(obj.items())[:10]}
    if isinstance(obj, list):
        return [_get_structure(obj[0], depth + 1)] if obj else []
    return type(obj).__name__


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Raw HTTP vs SDK: exact header/payload parity on SAME expiry
# ══════════════════════════════════════════════════════════════════════════════
log.info("\n" + "=" * 70)
log.info("[Test1] RAW HTTP vs SDK — exact payload parity")
log.info("=" * 70)

try:
    from dhanhq import dhanhq as _DhanHQ
    try:
        from dhanhq import DhanContext
        _ctx  = DhanContext(CLIENT_ID, ACCESS_TOKEN)
        _dhan = _DhanHQ(_ctx)
    except ImportError:
        _dhan = _DhanHQ(CLIENT_ID, ACCESS_TOKEN)

    log.info("[DhanSDKParity] SDK object id=%d  type=%s",
             id(_dhan), type(_dhan).__name__)

    # Use the first available expiry (works for today or any day)
    # We'll use next-month expiry which is likely safe for both
    TODAY = datetime.now().strftime("%Y-%m-%d")
    YEAR  = datetime.now().year
    MONTH = datetime.now().month

    # Build plausible near-month expiry (Dhan expiry_list will correct it)
    import calendar
    def _last_tuesday_of_month(y: int, m: int) -> str:
        last_day = calendar.monthrange(y, m)[1]
        for d in range(last_day, last_day - 7, -1):
            if datetime(y, m, d).weekday() == 1:  # Tuesday
                return f"{y}-{m:02d}-{d:02d}"
        return f"{y}-{m:02d}-25"

    # Try to get live expiry list first
    expiry_map: Dict[str, List[str]] = {}
    for sym in SYMBOLS:
        try:
            el = _dhan.expiry_list(
                under_security_id=sym["security_id"],
                under_exchange_segment=SEGMENT,
            )
            if isinstance(el, dict) and el.get("status") == "success":
                inner = el.get("data", {})
                dates = inner.get("data", []) if isinstance(inner, dict) else []
                expiry_map[sym["name"]] = [str(d) for d in dates[:4]]
                log.info("[DhanExpiryMatrix] symbol=%s  expiry_list_ok  dates=%s",
                         sym["name"], expiry_map[sym["name"]])
            else:
                raise ValueError(f"expiry_list non-success: {el}")
        except Exception as exc:
            # fallback to manual expiry
            expiry_map[sym["name"]] = [
                _last_tuesday_of_month(YEAR, MONTH),
                _last_tuesday_of_month(YEAR, MONTH % 12 + 1 if MONTH < 12 else 1),
            ]
            log.warning("[DhanExpiryMatrix] symbol=%s  expiry_list FAILED (%s)  "
                        "fallback=%s", sym["name"], exc, expiry_map[sym["name"]])

    # Test 1 — For each symbol, call SDK AND raw HTTP with identical payload
    url_opchain = f"{BASE_URL}/optionchain"
    t1_results = {}

    for sym in SYMBOLS:
        name   = sym["name"]
        sid    = sym["security_id"]
        expiry = expiry_map.get(name, [TODAY])[0]

        payload = {
            "UnderlyingScrip": sid,
            "UnderlyingSeg":   SEGMENT,
            "Expiry":          expiry,
        }

        log.info("[Test1] symbol=%s  expiry=%s  payload=%r", name, expiry, payload)

        # SDK call
        t0 = time.perf_counter()
        try:
            sdk_resp = _dhan.option_chain(
                under_security_id=sid,
                under_exchange_segment=SEGMENT,
                expiry=expiry,
            )
            sdk_latency = int((time.perf_counter() - t0) * 1000)
            sdk_status = sdk_resp.get("status", "?") if isinstance(sdk_resp, dict) else "N/A"
            sdk_remarks = sdk_resp.get("remarks") if isinstance(sdk_resp, dict) else None
        except Exception as e:
            sdk_resp    = {"_exc": str(e)}
            sdk_latency = int((time.perf_counter() - t0) * 1000)
            sdk_status  = "EXCEPTION"
            sdk_remarks = str(e)

        # Raw HTTP call (exact same headers as SDK, built from source inspection)
        try:
            raw_status, raw_body, raw_latency = _raw_post(url_opchain, payload, SDK_HEADERS)
        except Exception as e:
            raw_status = -1
            raw_body   = {"_exc": str(e)}
            raw_latency = 0.0

        raw_api_status = raw_body.get("status", "?") if isinstance(raw_body, dict) else "N/A"
        raw_remarks    = raw_body.get("remarks") if isinstance(raw_body, dict) else None

        log.info(
            "[DhanSDKParity] symbol=%-12s  expiry=%s\n"
            "  SDK:  http=SDK  status=%-10s  remarks=%r  latency=%dms\n"
            "  RAW:  http=%-3d  status=%-10s  remarks=%r  latency=%dms\n"
            "  PARITY: sdk_match_raw=%s",
            name, expiry,
            sdk_status, sdk_remarks, sdk_latency,
            raw_status, raw_api_status, raw_remarks, int(raw_latency),
            sdk_status == raw_api_status,
        )

        # Save snapshots
        snap_name = f"{name.lower()}_{expiry}"
        _save_json(f"{snap_name}_sdk",        sdk_resp)
        _save_json(f"{snap_name}_raw",        raw_body)

        t1_results[name] = {
            "expiry":       expiry,
            "sdk_status":   sdk_status,
            "raw_status":   raw_api_status,
            "sdk_latency":  sdk_latency,
            "raw_latency":  int(raw_latency),
            "parity_match": sdk_status == raw_api_status,
        }

except Exception as exc:
    log.exception("[Test1] Fatal: %s", exc)
    t1_results = {}

# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Exact Payload Replay: Dhan support-spec payload verbatim
# ══════════════════════════════════════════════════════════════════════════════
log.info("\n" + "=" * 70)
log.info("[Test2] EXACT PAYLOAD REPLAY — Dhan support spec")
log.info("=" * 70)

t2_results = {}
for sym in SYMBOLS:
    name = sym["name"]
    sid  = sym["security_id"]

    # Try the expiries we fetched in test 1
    expiries_to_test = expiry_map.get(name, [])
    if not expiries_to_test:
        log.warning("[Test2] No expiries for %s — skipping", name)
        continue

    # Test current expiry and next expiry explicitly
    for expiry in expiries_to_test[:2]:
        payload = {
            "UnderlyingScrip": sid,
            "UnderlyingSeg":   SEGMENT,
            "Expiry":          expiry,
        }
        try:
            http_code, body, latency = _raw_post(BASE_URL + "/optionchain", payload, SDK_HEADERS)
            api_status = body.get("status", "?") if isinstance(body, dict) else "?"
            remarks    = body.get("remarks") if isinstance(body, dict) else None
            log.info(
                "[DhanRawRequest] symbol=%-12s  expiry=%s  sid=%d  payload=%r",
                name, expiry, sid, payload,
            )
            log.info(
                "[DhanRawResponse] symbol=%-12s  expiry=%s  http=%d  "
                "api_status=%s  remarks=%r  latency=%dms",
                name, expiry, http_code, api_status, remarks, int(latency),
            )
            _save_json(f"t2_{name.lower()}_{expiry}_raw", body)
            t2_results[f"{name}_{expiry}"] = {
                "http_code":  http_code,
                "api_status": api_status,
                "remarks":    remarks,
                "latency_ms": int(latency),
            }
        except Exception as e:
            log.warning("[Test2] %s %s: %r", name, expiry, e)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Multi-Expiry Matrix: both symbols × first 3 live expiries (SDK)
# ══════════════════════════════════════════════════════════════════════════════
log.info("\n" + "=" * 70)
log.info("[Test3] MULTI-EXPIRY MATRIX — SDK path, all available expiries")
log.info("=" * 70)

t3_results = {}
for sym in SYMBOLS:
    name    = sym["name"]
    sid     = sym["security_id"]
    expiries = expiry_map.get(name, [])

    for expiry in expiries[:3]:
        t0 = time.perf_counter()
        try:
            resp = _dhan.option_chain(
                under_security_id=sid,
                under_exchange_segment=SEGMENT,
                expiry=expiry,
            )
            latency = int((time.perf_counter() - t0) * 1000)
            status  = resp.get("status", "?") if isinstance(resp, dict) else "?"
            remarks = resp.get("remarks") if isinstance(resp, dict) else None
            data    = resp.get("data") if isinstance(resp, dict) else None

            # Count strikes on success
            strike_count = 0
            if isinstance(data, dict):
                strike_count = len(data.get("data", []))

            log.info(
                "[DhanExpiryMatrix] symbol=%-12s  expiry=%s  status=%-10s  "
                "strikes=%d  remarks=%r  latency=%dms",
                name, expiry, status, strike_count, remarks, latency,
            )
            _save_json(f"t3_{name.lower()}_{expiry}_sdk", resp)
            t3_results[f"{name}_{expiry}"] = {
                "status":       status,
                "strike_count": strike_count,
                "latency_ms":   latency,
            }
        except Exception as e:
            latency = int((time.perf_counter() - t0) * 1000)
            log.warning("[DhanExpiryMatrix] symbol=%s  expiry=%s  exc=%r", name, expiry, e)
            t3_results[f"{name}_{expiry}"] = {"status": "EXCEPTION", "exc": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — JSON Snapshot Structural Diff: NIFTY success vs BANKNIFTY failure
# ══════════════════════════════════════════════════════════════════════════════
log.info("\n" + "=" * 70)
log.info("[Test4] JSON SNAPSHOT DIFF — NIFTY success vs BANKNIFTY failure")
log.info("=" * 70)

def _find_best_snapshot(symbol: str) -> Optional[dict]:
    """Load the best available snapshot for a symbol — prefer SDK success."""
    # Look for sdk snapshots (test 1 or test 3)
    candidates = list(FORENSICS_DIR.glob(f"{symbol.lower()}_*_sdk.json")) + \
                 list(FORENSICS_DIR.glob(f"t3_{symbol.lower()}_*_sdk.json"))
    for path in sorted(candidates):
        try:
            with path.open() as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("status") == "success":
                log.info("[Test4] Using success snapshot: %s", path.name)
                return data
        except Exception:
            pass
    # Fall back to any snapshot
    for path in sorted(candidates):
        try:
            with path.open() as f:
                return json.load(f)
        except Exception:
            pass
    return None

def _find_failure_snapshot(symbol: str) -> Optional[dict]:
    """Load a failure/non-success snapshot for a symbol."""
    candidates = list(FORENSICS_DIR.glob(f"{symbol.lower()}_*_sdk.json")) + \
                 list(FORENSICS_DIR.glob(f"t3_{symbol.lower()}_*_sdk.json"))
    for path in sorted(candidates):
        try:
            with path.open() as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("status") != "success":
                log.info("[Test4] Using failure snapshot: %s", path.name)
                return data
        except Exception:
            pass
    return None

nifty_snap = _find_best_snapshot("NIFTY")
bnk_snap   = _find_failure_snapshot("BANKNIFTY") or _find_best_snapshot("BANKNIFTY")

if nifty_snap and bnk_snap:
    nifty_keys = sorted(nifty_snap.keys())
    bnk_keys   = sorted(bnk_snap.keys())
    log.info("[DhanForensicDiff] NIFTY top-level keys:     %s", nifty_keys)
    log.info("[DhanForensicDiff] BANKNIFTY top-level keys: %s", bnk_keys)
    log.info("[DhanForensicDiff] NIFTY status:     %r", nifty_snap.get("status"))
    log.info("[DhanForensicDiff] BANKNIFTY status: %r", bnk_snap.get("status"))
    log.info("[DhanForensicDiff] NIFTY remarks:     %r", nifty_snap.get("remarks"))
    log.info("[DhanForensicDiff] BANKNIFTY remarks: %r", bnk_snap.get("remarks"))

    nifty_struct = _get_structure(nifty_snap)
    bnk_struct   = _get_structure(bnk_snap)
    log.info("[DhanForensicDiff] NIFTY structure:\n%s",
             json.dumps(nifty_struct, indent=2))
    log.info("[DhanForensicDiff] BANKNIFTY structure:\n%s",
             json.dumps(bnk_struct, indent=2))

    # Key-by-key diff
    all_keys = set(nifty_keys) | set(bnk_keys)
    for key in sorted(all_keys):
        nifty_val = nifty_snap.get(key, "<MISSING>")
        bnk_val   = bnk_snap.get(key, "<MISSING>")
        match = nifty_val == bnk_val
        if not match or key in ("status", "remarks"):
            log.info(
                "[DhanForensicDiff] key=%-12s  NIFTY=%-40r  BANKNIFTY=%-40r  match=%s",
                key, str(nifty_val)[:40], str(bnk_val)[:40], match,
            )

    _save_json("t4_nifty_best", nifty_snap)
    _save_json("t4_banknifty_best", bnk_snap)
else:
    log.warning("[Test4] Could not load snapshots for diff — skipping")


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Network Path: DNS resolution + TLS handshake timing
# ══════════════════════════════════════════════════════════════════════════════
log.info("\n" + "=" * 70)
log.info("[Test5] NETWORK PATH — DNS + TLS + first-byte latency")
log.info("=" * 70)

api_host = "api.dhan.co"
try:
    t0 = time.perf_counter()
    ip = socket.gethostbyname(api_host)
    dns_ms = int((time.perf_counter() - t0) * 1000)
    log.info("[DhanNetworkPath] DNS resolution: %s → %s  latency=%dms", api_host, ip, dns_ms)
except Exception as e:
    log.warning("[DhanNetworkPath] DNS failed: %s", e)
    ip = "?"

# TLS + TCP handshake
try:
    import ssl
    ctx = ssl.create_default_context()
    t0 = time.perf_counter()
    with socket.create_connection((api_host, 443), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=api_host) as ssock:
            tls_ms = int((time.perf_counter() - t0) * 1000)
            cipher = ssock.cipher()
    log.info("[DhanNetworkPath] TLS handshake latency=%dms  ip=%s  cipher=%s",
             tls_ms, ip, cipher[0] if cipher else "?")
except Exception as e:
    log.warning("[DhanNetworkPath] TLS probe failed: %s", e)

# NIFTY first-byte vs BANKNIFTY first-byte from same session
http_sess = requests.Session()
fb_results = {}
for sym in SYMBOLS:
    name   = sym["name"]
    sid    = sym["security_id"]
    expiry = expiry_map.get(name, [""])[0] if expiry_map.get(name) else ""
    if not expiry:
        continue
    payload = {"UnderlyingScrip": sid, "UnderlyingSeg": SEGMENT, "Expiry": expiry}
    try:
        t0 = time.perf_counter()
        resp = http_sess.post(
            f"{BASE_URL}/optionchain",
            json=payload,
            headers=SDK_HEADERS,
            timeout=12,
        )
        total_ms = int((time.perf_counter() - t0) * 1000)
        elapsed_ms = int(resp.elapsed.total_seconds() * 1000)
        api_status = resp.json().get("status", "?") if resp.content else "?"
        log.info(
            "[DhanNetworkPath] symbol=%-12s  total_ms=%d  elapsed_ms=%d  "
            "http=%d  api_status=%s  expiry=%s",
            name, total_ms, elapsed_ms, resp.status_code, api_status, expiry,
        )
        fb_results[name] = {"total_ms": total_ms, "elapsed_ms": elapsed_ms,
                            "http_status": resp.status_code, "api_status": api_status}
    except Exception as e:
        log.warning("[DhanNetworkPath] symbol=%s: %r", name, e)
http_sess.close()


# ══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
log.info("\n" + "=" * 70)
log.info("[ForensicSummary] COMPLETE RESULTS")
log.info("=" * 70)

log.info("[ForensicSummary] Test 1 — SDK vs Raw HTTP parity:")
for sym_name, r in t1_results.items():
    log.info("  %-12s  expiry=%-10s  SDK=%-10s  RAW=%-10s  parity=%s  sdk_ms=%d  raw_ms=%d",
             sym_name, r.get("expiry","?"),
             r.get("sdk_status","?"), r.get("raw_status","?"),
             r.get("parity_match","?"),
             r.get("sdk_latency", 0), r.get("raw_latency", 0))

log.info("[ForensicSummary] Test 3 — Multi-expiry matrix:")
for key, r in t3_results.items():
    sym_name, expiry = key.rsplit("_", 1)
    log.info("  %-18s  expiry=%-10s  status=%-10s  strikes=%-4s  latency=%sms",
             sym_name, expiry,
             r.get("status","?"), r.get("strike_count","?"), r.get("latency_ms","?"))

log.info("[ForensicSummary] Snapshots saved to: %s", FORENSICS_DIR)
for f in sorted(FORENSICS_DIR.glob("*.json")):
    size = f.stat().st_size
    log.info("  %-50s  %d bytes", f.name, size)

_save_json("forensic_summary", {
    "timestamp": datetime.now().isoformat(),
    "client_id": CLIENT_ID,
    "token_sfx": ACCESS_TOKEN[-8:] if ACCESS_TOKEN else "?",
    "test1_parity": t1_results,
    "test2_raw":    t2_results,
    "test3_matrix": t3_results,
    "test5_network": fb_results,
})
log.info("[ForensicSummary] DONE — summary at %s/forensic_summary.json", FORENSICS_DIR)
