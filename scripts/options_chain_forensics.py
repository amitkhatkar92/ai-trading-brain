#!/usr/bin/env python3
"""
options_chain_forensics.py — Phases 1-7 Options Chain Forensic Diagnostic
==========================================================================
Run on BOTH local desktop AND VPS to compare behavior:

    python3 scripts/options_chain_forensics.py

All output uses structured [TAG] lines so results are grep-able.
Compare [Environment].public_ip between local and VPS runs to detect IP blocks.

Phases covered:
    Phase 1 — Raw NSE HTTP probe (no headers, no cookies)
    Phase 2 — Browser emulation (homepage warmup + realistic headers)
    Phase 3 — IP block validation (compare outputs from both environments)
    Phase 4 — Polling frequency audit (feed_audit.csv inter-poll timing)
    Phase 5 — Dhan options entitlement (raw HTTP + SDK call)
    Phase 6 — Endpoint validation (URL variants, auth check)
    Phase 7 — Options chain sanity check (structure, IV, OI, expiry)
"""
from __future__ import annotations

import csv
import json
import os
import socket
import sys
import time
import traceback
from datetime import datetime, date, timedelta
from pathlib import Path

# ── bootstrap .env before any imports ──────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_ENV  = _ROOT / ".env"
if _ENV.exists():
    for _ln in _ENV.read_text(encoding="utf-8").splitlines():
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _, _v = _ln.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

import requests   # noqa: E402 — after env load

# ── formatting helpers ──────────────────────────────────────────────────────

def _tag(label: str, **kv) -> None:
    parts = "  ".join(f"{k}={v!r}" for k, v in kv.items())
    print(f"[{label}] {parts}", flush=True)


def _sep(char="─", n=72) -> None:
    print(char * n, flush=True)


def _section(title: str) -> None:
    print(f"\n{'━' * 72}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'━' * 72}", flush=True)


# ── constants ───────────────────────────────────────────────────────────────

NSE_HOME        = "https://www.nseindia.com/"
NSE_OC_INDICES  = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
NSE_OC_EQUITIES = "https://www.nseindia.com/api/option-chain-equities?symbol=HDFCBANK"
NSE_MARKET_STAT = "https://www.nseindia.com/api/marketStatus"
NSE_ALL_INDICES = "https://www.nseindia.com/api/allIndices"

DHAN_OC_URL_V2  = "https://api.dhan.co/v2/optionchain"
DHAN_OC_URL_V1  = "https://api.dhan.co/optionchain"
DHAN_FUNDS_URL  = "https://api.dhan.co/v2/funds"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Referer":         "https://www.nseindia.com/option-chain",
    "sec-fetch-dest":  "empty",
    "sec-fetch-mode":  "cors",
    "sec-fetch-site":  "same-origin",
    "DNT":             "1",
}


def _nearest_weekly_expiry() -> str:
    """Return nearest Thursday (weekly NIFTY expiry) as YYYY-MM-DD."""
    today = date.today()
    days_ahead = (3 - today.weekday()) % 7   # 3 = Thursday
    if days_ahead == 0 and datetime.now().hour >= 15:
        days_ahead = 7   # today's expiry has passed
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def _safe_json(r: requests.Response):
    try:
        return r.json()
    except Exception:
        return None


# ── Environment header ──────────────────────────────────────────────────────

def print_environment() -> None:
    _sep("═")
    try:
        pub_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        pub_ip = "unavailable"
    _tag("Environment",
         hostname=socket.gethostname(),
         public_ip=pub_ip,
         python=sys.version.split()[0],
         ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    _sep("═")


# ══════════════════════════════════════════════════════════════════════════
# PHASE 1 — RAW NSE HTTP PROBE
# ══════════════════════════════════════════════════════════════════════════

def phase1_nse_raw() -> None:
    _section("PHASE 1: RAW NSE HTTP PROBE (bare requests.get, no headers)")

    probes = [
        ("option_chain_indices",  NSE_OC_INDICES),
        ("option_chain_equities", NSE_OC_EQUITIES),
        ("market_status",         NSE_MARKET_STAT),
    ]
    for label, url in probes:
        try:
            t0 = time.monotonic()
            r  = requests.get(url, timeout=12, allow_redirects=True)
            ms = int((time.monotonic() - t0) * 1000)

            j    = _safe_json(r)
            ct   = r.headers.get("content-type", "")
            redir_chain = [(str(h.status_code), h.url) for h in r.history]

            _tag("NSERawProbe",
                 endpoint=label,
                 status=r.status_code,
                 content_type=ct,
                 body_len=len(r.content),
                 elapsed_ms=ms,
                 redirect_count=len(r.history),
                 redirects=redir_chain,
                 resp_type=type(j).__name__ if j is not None else "non_json",
                 top_keys=(list(j.keys())[:8] if isinstance(j, dict) else None),
                 records_present=("records" in j if isinstance(j, dict) else False),
                 preview=r.text[:250])
        except Exception as e:
            _tag("NSERawProbe", endpoint=label, error=type(e).__name__, detail=str(e)[:200])


# ══════════════════════════════════════════════════════════════════════════
# PHASE 2 — BROWSER EMULATION
# ══════════════════════════════════════════════════════════════════════════

def phase2_nse_browser() -> None:
    _section("PHASE 2: NSE BROWSER EMULATION (homepage warmup + realistic headers)")

    sess = requests.Session()
    sess.headers.update(BROWSER_HEADERS)

    # Step 1 — homepage warmup to acquire NSE session cookies
    try:
        t0 = time.monotonic()
        home = sess.get(NSE_HOME, timeout=15)
        ms1  = int((time.monotonic() - t0) * 1000)
        cookies = dict(sess.cookies)
        _tag("NSEBrowserEmulation",
             step="homepage_warmup",
             status=home.status_code,
             elapsed_ms=ms1,
             cookie_count=len(cookies),
             cookie_names=list(cookies.keys()),
             body_len=len(home.content))
    except Exception as e:
        _tag("NSEBrowserEmulation", step="homepage_warmup",
             error=type(e).__name__, detail=str(e)[:200])
        return

    time.sleep(1.5)  # brief human-like pause

    # Step 2 — options chain with session cookies intact
    chain_probes = [
        ("indices/NIFTY",        NSE_OC_INDICES),
        ("equities/HDFCBANK",    NSE_OC_EQUITIES),
        ("market_status",        NSE_MARKET_STAT),
        ("all_indices",          NSE_ALL_INDICES),
    ]
    for label, url in chain_probes:
        try:
            t0 = time.monotonic()
            r  = sess.get(url, timeout=15)
            ms = int((time.monotonic() - t0) * 1000)
            j  = _safe_json(r)

            records_present = False
            record_count    = 0
            expiry_count    = 0
            if isinstance(j, dict):
                records_present = "records" in j
                if records_present and isinstance(j.get("records"), dict):
                    record_count  = len(j["records"].get("data", []))
                    expiry_count  = len(j["records"].get("expiryDates", []))

            _tag("NSEBrowserEmulation",
                 step="fetch",
                 endpoint=label,
                 status=r.status_code,
                 elapsed_ms=ms,
                 content_type=r.headers.get("content-type", ""),
                 cookie_count=len(dict(sess.cookies)),
                 resp_type=type(j).__name__ if j is not None else "non_json",
                 top_keys=(list(j.keys())[:8] if isinstance(j, dict) else None),
                 records_present=records_present,
                 record_count=record_count,
                 expiry_count=expiry_count,
                 preview=r.text[:250])
        except Exception as e:
            _tag("NSEBrowserEmulation", step="fetch", endpoint=label,
                 error=type(e).__name__, detail=str(e)[:200])
        time.sleep(0.4)


# ══════════════════════════════════════════════════════════════════════════
# PHASE 3 — IP BLOCK VALIDATION (comparison tag)
# ══════════════════════════════════════════════════════════════════════════

def phase3_ip_block() -> None:
    _section("PHASE 3: IP BLOCK VALIDATION (compare across environments)")
    print("  Run this script on BOTH local desktop and VPS.", flush=True)
    print("  Compare [NSERawProbe].status and records_present between the two.", flush=True)
    print("  If local=LIVE + VPS=empty → cloud IP blocked by NSE.", flush=True)
    print("  If both empty → NSE headers/cookie issue (same fix needed everywhere).", flush=True)
    _tag("NSEIPBlockCheck", instruction="diff_phase1_phase2_output_across_environments")


# ══════════════════════════════════════════════════════════════════════════
# PHASE 4 — POLLING FREQUENCY AUDIT
# ══════════════════════════════════════════════════════════════════════════

def phase4_polling_audit() -> None:
    _section("PHASE 4: POLLING FREQUENCY AUDIT (feed_audit.csv)")

    audit_path = _ROOT / "data" / "feed_audit.csv"
    if not audit_path.exists():
        _tag("PollingAudit", result="no_feed_audit_csv", path=str(audit_path))
        return

    try:
        with audit_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        _tag("PollingAudit", error=str(e))
        return

    recent = rows[-120:]   # last 120 rows
    _tag("PollingAudit", total_audit_rows=len(rows), analysing_last=len(recent))

    if len(recent) < 2:
        _tag("PollingAudit", result="insufficient_data")
        return

    # Inter-poll interval distribution
    times = []
    for row in recent:
        try:
            ts_raw = row.get("ts", "")
            times.append(datetime.fromisoformat(ts_raw.replace("Z", "+00:00")))
        except Exception:
            pass

    if len(times) >= 2:
        intervals = [(times[i+1] - times[i]).total_seconds() for i in range(len(times) - 1)]
        intervals  = [x for x in intervals if 0 < x < 3600]   # ignore gaps > 1h (restart)
        if intervals:
            avg_iv = sum(intervals) / len(intervals)
            min_iv = min(intervals)
            max_iv = max(intervals)
            rpm    = round(60.0 / avg_iv, 2) if avg_iv > 0 else "inf"
            _tag("PollingAudit",
                 avg_interval_s=round(avg_iv, 1),
                 min_interval_s=round(min_iv, 1),
                 max_interval_s=round(max_iv, 1),
                 approx_req_per_min=rpm,
                 risk_of_rate_limit=(min_iv < 10))


# ══════════════════════════════════════════════════════════════════════════
# PHASE 5 — DHAN OPTIONS ENTITLEMENT AUDIT
# ══════════════════════════════════════════════════════════════════════════

def phase5_dhan_entitlement() -> None:
    _section("PHASE 5: DHAN OPTIONS ENTITLEMENT AUDIT")

    client_id    = os.getenv("DHAN_CLIENT_ID", "")
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "")

    if not client_id or not access_token:
        _tag("DhanOptionsEntitlement", result="NO_CREDENTIALS",
             client_id_set=bool(client_id), token_set=bool(access_token))
        return

    _tag("DhanOptionsEntitlement", step="credentials_loaded",
         client_id_len=len(client_id), token_prefix=access_token[:8] + "…")

    expiry = _nearest_weekly_expiry()
    _tag("DhanOptionsEntitlement", step="probe_expiry", expiry=expiry)

    dhan_headers = {
        "access-token": access_token,
        "client-id":    client_id,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }

    # ── Raw HTTP probes (bypasses SDK so we see exact HTTP semantics) ─────
    payload_v2 = {
        "underlyingScrip":  13,        # NIFTY security_id
        "underlyingValue":  "IDX_I",   # exchange segment
        "expiryDate":       expiry,
    }

    raw_variants = [
        ("v2_post", "POST", DHAN_OC_URL_V2, payload_v2),
        ("v1_post", "POST", DHAN_OC_URL_V1, payload_v2),
        ("funds_get",  "GET",  DHAN_FUNDS_URL,  None),   # auth sanity check
    ]

    for label, method, url, body in raw_variants:
        try:
            t0 = time.monotonic()
            if method == "POST":
                r = requests.post(url, json=body, headers=dhan_headers, timeout=15)
            else:
                r = requests.get(url, headers=dhan_headers, timeout=15)
            ms = int((time.monotonic() - t0) * 1000)
            j  = _safe_json(r)

            _tag("DhanOptionsEntitlement",
                 variant=label,
                 http_status=r.status_code,
                 elapsed_ms=ms,
                 content_type=r.headers.get("content-type", ""),
                 resp_type=type(j).__name__ if j is not None else "non_json",
                 top_keys=(list(j.keys())[:8] if isinstance(j, dict) else None),
                 status_field=(j.get("status") if isinstance(j, dict) else None),
                 remarks=(j.get("remarks") if isinstance(j, dict) else None),
                 data_type=(type(j.get("data")).__name__ if isinstance(j, dict) else None),
                 preview=str(j)[:300] if j else r.text[:300])
        except Exception as e:
            _tag("DhanOptionsEntitlement", variant=label,
                 error=type(e).__name__, detail=str(e)[:200])

    # ── SDK call (same path as production code) ───────────────────────────
    try:
        from dhanhq import dhanhq as _DhanHQ
        dhan = _DhanHQ(client_id, access_token)
        t0   = time.monotonic()
        sdk_resp = dhan.option_chain(
            under_security_id      = 13,
            under_exchange_segment = "IDX_I",
            expiry                 = expiry,
        )
        ms = int((time.monotonic() - t0) * 1000)
        _tag("DhanOptionsEntitlement",
             step="sdk_call",
             elapsed_ms=ms,
             resp_type=type(sdk_resp).__name__,
             top_keys=(list(sdk_resp.keys())[:8] if isinstance(sdk_resp, dict) else None),
             status_field=(sdk_resp.get("status") if isinstance(sdk_resp, dict) else None),
             remarks=(sdk_resp.get("remarks") if isinstance(sdk_resp, dict) else None),
             preview=str(sdk_resp)[:350])
    except ImportError:
        _tag("DhanOptionsEntitlement", step="sdk_call", result="dhanhq_not_installed")
    except Exception as e:
        _tag("DhanOptionsEntitlement", step="sdk_call",
             error=type(e).__name__, detail=str(e)[:200])


# ══════════════════════════════════════════════════════════════════════════
# PHASE 6 — ENDPOINT VALIDATION
# ══════════════════════════════════════════════════════════════════════════

def phase6_endpoint_validation() -> None:
    _section("PHASE 6: ENDPOINT VALIDATION (URL variants + parameter audit)")

    expiry = _nearest_weekly_expiry()

    # ── NSE endpoint variants ─────────────────────────────────────────────
    sess = requests.Session()
    sess.headers.update(BROWSER_HEADERS)
    try:
        sess.get(NSE_HOME, timeout=12)
        time.sleep(1.5)
    except Exception:
        pass

    nse_variants = [
        ("standard_indices_NIFTY",      NSE_OC_INDICES),
        ("nifty50_name_variant",         "https://www.nseindia.com/api/option-chain-indices?symbol=Nifty+50"),
        ("banknifty_variant",            "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY+BANK"),
        ("equities_HDFCBANK",            NSE_OC_EQUITIES),
        ("market_status",                NSE_MARKET_STAT),
        ("all_indices",                  NSE_ALL_INDICES),
    ]
    for label, url in nse_variants:
        try:
            r = sess.get(url, timeout=12)
            j = _safe_json(r)
            _tag("NSEEndpointValidation",
                 variant=label,
                 status=r.status_code,
                 content_type=r.headers.get("content-type", ""),
                 resp_type=type(j).__name__ if j is not None else "non_json",
                 top_keys=(list(j.keys())[:6] if isinstance(j, dict) else None),
                 body_len=len(r.content),
                 records_present=("records" in j if isinstance(j, dict) else False))
        except Exception as e:
            _tag("NSEEndpointValidation", variant=label,
                 error=type(e).__name__, detail=str(e)[:150])
        time.sleep(0.35)

    # ── nsepython internals probe ─────────────────────────────────────────
    try:
        import nsepython as _nse
        _tag("NSEEndpointValidation", step="nsepython_version",
             version=getattr(_nse, "__version__", "unknown"),
             module_file=getattr(_nse, "__file__", "unknown"))
        # nsepython.nsefetch is the raw gateway — call it directly
        raw = _nse.nsefetch(NSE_OC_INDICES)
        _tag("NSEEndpointValidation",
             step="nsepython_direct_call",
             resp_type=type(raw).__name__,
             top_keys=(list(raw.keys())[:8] if isinstance(raw, dict) else None),
             records_present=("records" in raw if isinstance(raw, dict) else False),
             preview=str(raw)[:200])
    except ImportError:
        _tag("NSEEndpointValidation", step="nsepython_direct_call", result="not_installed")
    except Exception as e:
        _tag("NSEEndpointValidation", step="nsepython_direct_call",
             error=type(e).__name__, detail=str(e)[:200])

    # ── Dhan endpoint variants ────────────────────────────────────────────
    client_id    = os.getenv("DHAN_CLIENT_ID", "")
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
    if not (client_id and access_token):
        _tag("DhanEndpointValidation", result="no_credentials_skip")
        return

    dhan_headers = {
        "access-token": access_token,
        "client-id":    client_id,
        "Content-Type": "application/json",
        "Accept":       "application/json",
    }
    payload_base = {"underlyingScrip": 13, "underlyingValue": "IDX_I", "expiryDate": expiry}

    dhan_variants = [
        ("v2_nifty",          "POST", DHAN_OC_URL_V2, payload_base),
        ("v1_nifty",          "POST", DHAN_OC_URL_V1, payload_base),
        # Alternate payload key names (API sometimes changes between SDK versions)
        ("v2_alt_keys",       "POST", DHAN_OC_URL_V2,
         {"UnderlyingScrip": 13, "UnderlyingExchange": "IDX_I", "ExpiryDate": expiry}),
        ("v2_banknifty",      "POST", DHAN_OC_URL_V2,
         {"underlyingScrip": 25, "underlyingValue": "IDX_I", "expiryDate": expiry}),
        ("funds_auth_check",  "GET",  DHAN_FUNDS_URL, None),
    ]
    for label, method, url, body in dhan_variants:
        try:
            t0 = time.monotonic()
            if method == "POST":
                r = requests.post(url, json=body, headers=dhan_headers, timeout=12)
            else:
                r = requests.get(url, headers=dhan_headers, timeout=12)
            ms = int((time.monotonic() - t0) * 1000)
            j  = _safe_json(r)
            _tag("DhanEndpointValidation",
                 variant=label,
                 http_status=r.status_code,
                 elapsed_ms=ms,
                 resp_type=type(j).__name__ if j is not None else "non_json",
                 top_keys=(list(j.keys())[:6] if isinstance(j, dict) else None),
                 status_field=(j.get("status") if isinstance(j, dict) else None),
                 remarks=(j.get("remarks") if isinstance(j, dict) else None),
                 preview=str(j)[:250] if j else r.text[:250])
        except Exception as e:
            _tag("DhanEndpointValidation", variant=label,
                 error=type(e).__name__, detail=str(e)[:150])


# ══════════════════════════════════════════════════════════════════════════
# PHASE 7 — OPTIONS CHAIN SANITY CHECK
# ══════════════════════════════════════════════════════════════════════════

def phase7_chain_sanity() -> None:
    _section("PHASE 7: OPTIONS CHAIN SANITY CHECK (structure, IV, OI, freshness)")

    # Best effort: browser-emulated NIFTY chain
    sess = requests.Session()
    sess.headers.update(BROWSER_HEADERS)
    try:
        sess.get(NSE_HOME, timeout=15)
        time.sleep(2.0)
    except Exception as e:
        _tag("OptionsChainSanity", symbol="NIFTY", result="homepage_warmup_failed", error=str(e))

    j = None
    for label, url in [("indices/NIFTY", NSE_OC_INDICES), ("equities/HDFCBANK", NSE_OC_EQUITIES)]:
        try:
            r = sess.get(url, timeout=15)
            j = _safe_json(r)
            if not isinstance(j, dict) or "records" not in j:
                _tag("OptionsChainSanity",
                     source="NSE_browser", endpoint=label,
                     result="NO_RECORDS",
                     http_status=r.status_code,
                     resp_type=type(j).__name__ if j is not None else "non_json",
                     top_keys=(list(j.keys())[:8] if isinstance(j, dict) else None),
                     preview=r.text[:200])
                j = None
                time.sleep(0.5)
                continue

            records      = j["records"]
            data         = records.get("data", [])
            expiry_dates = records.get("expiryDates", [])
            timestamp    = records.get("timestamp", "unknown")
            spot         = j.get("filtered", {}).get("underlying", {}).get("lastPrice") or j.get("records", {}).get("underlyingValue")

            ce_rows = [d for d in data if d.get("CE")]
            pe_rows = [d for d in data if d.get("PE")]
            iv_vals = [d["CE"].get("impliedVolatility", 0) for d in ce_rows if d.get("CE")]
            oi_vals = [d["CE"].get("openInterest", 0)     for d in ce_rows if d.get("CE")]

            _tag("OptionsChainSanity",
                 source="NSE_browser", endpoint=label,
                 result="LIVE",
                 http_status=r.status_code,
                 strikes=len(data),
                 ce_count=len(ce_rows),
                 pe_count=len(pe_rows),
                 expiry_count=len(expiry_dates),
                 nearest_expiry=(expiry_dates[0] if expiry_dates else None),
                 timestamp=timestamp,
                 spot=spot,
                 iv_present=any(v > 0 for v in iv_vals),
                 sample_iv=(round(iv_vals[0], 2) if iv_vals else None),
                 oi_present=any(v > 0 for v in oi_vals),
                 sample_oi=(oi_vals[0] if oi_vals else None))
            break  # success — no need for equities probe
        except Exception as e:
            _tag("OptionsChainSanity", source="NSE_browser", endpoint=label,
                 error=type(e).__name__, detail=str(e)[:200])
        time.sleep(0.5)

    # Try via nsepython too (compare with raw)
    try:
        import nsepython as _nse
        raw_nse = _nse.nsefetch(NSE_OC_INDICES)
        records = raw_nse.get("records", {}) if isinstance(raw_nse, dict) else {}
        data    = records.get("data", [])
        _tag("OptionsChainSanity",
             source="nsepython",
             resp_type=type(raw_nse).__name__,
             records_present=bool(data),
             record_count=len(data),
             preview=str(raw_nse)[:200])
    except ImportError:
        _tag("OptionsChainSanity", source="nsepython", result="not_installed")
    except Exception as e:
        _tag("OptionsChainSanity", source="nsepython",
             error=type(e).__name__, detail=str(e)[:200])


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print_environment()

    phase1_nse_raw()
    phase2_nse_browser()
    phase3_ip_block()
    phase4_polling_audit()
    phase5_dhan_entitlement()
    phase6_endpoint_validation()
    phase7_chain_sanity()

    _sep("═")
    print("[ForensicDiagnostic] All phases complete.", flush=True)
    print("[ForensicDiagnostic] Grep for [NSERawProbe], [NSEBrowserEmulation],", flush=True)
    print("[ForensicDiagnostic] [DhanOptionsEntitlement], [OptionsChainSanity].", flush=True)
    _sep("═")
