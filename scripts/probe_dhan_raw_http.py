"""
Phase 3 — Raw Dhan API Protocol Verification
=============================================
Pure requests-based HTTP probe. Zero SDK/router/fallback involvement.

Tests:
  1. Token validation (JWT decode, length, whitespace)
  2. GET /fundlimit            — auth smoke test (simplest endpoint)
  3. POST /marketfeed/ltp     — LTP endpoint
  4. POST /marketfeed/ohlc    — OHLC endpoint
  5. POST /marketfeed/quote   — Full quote endpoint
  6. SDK parity comparison     — same call via dhanhq library

Verdict: prints CASE A (SDK bug) or CASE B (Dhan-side API/token issue)
"""

import os
import sys
import json
import time
import base64
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests not installed — run: pip install requests")

# ── Load credentials from .env ─────────────────────────────────────────────
def load_env(env_path: Path) -> dict:
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env

# Try both container path and relative path
for candidate in [Path("/app/.env"), Path(__file__).parent.parent / ".env"]:
    if candidate.exists():
        _env = load_env(candidate)
        print(f"[ENV] Loaded from: {candidate}")
        break
else:
    _env = {}
    print("[ENV] WARNING: No .env file found — will use environment variables only")

CLIENT_ID    = os.environ.get("DHAN_CLIENT_ID")    or _env.get("DHAN_CLIENT_ID", "")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN") or _env.get("DHAN_ACCESS_TOKEN", "")

# ── Constants ──────────────────────────────────────────────────────────────
BASE_URL = "https://api.dhan.co/v2"

# Test symbols: RELIANCE (NSE_EQ, id=2885) and HDFCBANK (NSE_EQ, id=1333)
TEST_PAYLOAD = {"NSE_EQ": [2885, 1333]}   # securities for ltp/ohlc/quote

# ── Utilities ──────────────────────────────────────────────────────────────

SEP  = "=" * 70
SEP2 = "-" * 50

def hdr(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")

def sub(title: str) -> None:
    print(f"\n{SEP2}\n  {title}\n{SEP2}")

def ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3] + " UTC"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Token Validation
# ══════════════════════════════════════════════════════════════════════════════

hdr("SECTION 1 — Token & Credentials Validation")

if not CLIENT_ID:
    print("  ❌  DHAN_CLIENT_ID   : NOT SET")
else:
    print(f"  ✅  DHAN_CLIENT_ID   : {CLIENT_ID!r}  (len={len(CLIENT_ID)})")

if not ACCESS_TOKEN:
    print("  ❌  DHAN_ACCESS_TOKEN: NOT SET")
    print("\n  FATAL: Cannot proceed without credentials. Exiting.")
    sys.exit(1)

tok = ACCESS_TOKEN

# Whitespace check
has_leading  = tok != tok.lstrip()
has_trailing = tok != tok.rstrip()
has_newline  = "\n" in tok or "\r" in tok
tok_clean    = tok.strip()
print(f"\n  DHAN_ACCESS_TOKEN stats:")
print(f"    raw length    : {len(tok)}")
print(f"    stripped len  : {len(tok_clean)}")
print(f"    has_leading_ws: {has_leading}")
print(f"    has_trailing_ws:{has_trailing}")
print(f"    has_newline   : {has_newline}")
print(f"    first_20      : {tok_clean[:20]!r}")
print(f"    last_20       : {tok_clean[-20:]!r}")

# JWT structure check
parts = tok_clean.split(".")
print(f"\n  JWT parts count : {len(parts)}  ({'valid JWT structure' if len(parts)==3 else 'NOT a standard JWT'})")

if len(parts) == 3:
    # Decode header
    try:
        hdr_raw = parts[0] + "=" * (4 - len(parts[0]) % 4)
        hdr_dec = base64.urlsafe_b64decode(hdr_raw)
        try:
            hdr_json = json.loads(hdr_dec)
        except Exception:
            hdr_json = {"raw": hdr_dec.decode("latin-1")}
        print(f"  JWT header      : {hdr_json}")
    except Exception as e:
        print(f"  JWT header decode error: {e}")

    # Decode payload — exp/iat via regex (handles malformed JSON)
    try:
        pay_raw = parts[1] + "=" * (4 - len(parts[1]) % 4)
        pay_bytes = base64.urlsafe_b64decode(pay_raw)
        try:
            pay_json = json.loads(pay_bytes)
            exp = pay_json.get("exp")
            iat = pay_json.get("iat")
            sub_claim = pay_json.get("sub") or pay_json.get("clientId") or pay_json.get("client_id")
        except Exception:
            pay_str = pay_bytes.decode("latin-1")
            exp_m = re.search(r'"exp"\s*:\s*(\d+)', pay_str)
            iat_m = re.search(r'"iat"\s*:\s*(\d+)', pay_str)
            cid_m = re.search(r'"(?:sub|clientId|client_id)"\s*:\s*"([^"]+)"', pay_str)
            exp = int(exp_m.group(1)) if exp_m else None
            iat = int(iat_m.group(1)) if iat_m else None
            sub_claim = cid_m.group(1) if cid_m else None

        now = time.time()
        if iat:
            iat_dt = datetime.fromtimestamp(iat, tz=timezone.utc)
            age_h  = (now - iat) / 3600
            print(f"\n  JWT iat         : {iat}  ({iat_dt.strftime('%Y-%m-%d %H:%M:%S UTC')})  age={age_h:.1f}h")
        if exp:
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            rem_s  = exp - now
            rem_h  = rem_s / 3600
            state  = "VALID ✅" if rem_s > 0 else "EXPIRED ❌"
            print(f"  JWT exp         : {exp}  ({exp_dt.strftime('%Y-%m-%d %H:%M:%S UTC')})  remaining={rem_h:.2f}h  [{state}]")
        if sub_claim:
            print(f"  JWT sub/clientId: {sub_claim!r}")
            if sub_claim != CLIENT_ID:
                print(f"  ⚠️  CLIENT_ID MISMATCH — env={CLIENT_ID!r}  jwt={sub_claim!r}")
            else:
                print(f"  ✅  CLIENT_ID matches JWT sub claim")
    except Exception as e:
        print(f"  JWT payload decode error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Raw HTTP Calls (one function for reuse)
# ══════════════════════════════════════════════════════════════════════════════

def raw_get(path: str, label: str) -> dict:
    """Make raw GET request, print full protocol details, return result dict."""
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "Accept":        "application/json",
        "access-token":  tok_clean,
        "client-id":     CLIENT_ID,
    }
    hdr(f"SECTION — {label}  [{ts()}]")
    print(f"  URL     : GET {url}")
    print(f"  Headers :")
    for k, v in headers.items():
        display = v if k != "access-token" else f"{v[:15]}...{v[-10:]}"
        print(f"    {k}: {display}")

    t0 = time.perf_counter()
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"\n  HTTP status     : {resp.status_code}")
        print(f"  Elapsed         : {elapsed_ms:.0f} ms")
        print(f"  Content-Type    : {resp.headers.get('Content-Type', 'n/a')}")
        print(f"  Response size   : {len(resp.content)} bytes")
        try:
            body = resp.json()
            print(f"  Parsed JSON     : {json.dumps(body, indent=4)}")
        except Exception:
            print(f"  Raw body        : {resp.text[:500]!r}")
            body = {}
        return {"status_code": resp.status_code, "body": body, "ok": resp.status_code == 200}
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"  ❌ Exception after {elapsed_ms:.0f}ms : {e}")
        return {"status_code": None, "body": {}, "ok": False, "error": str(e)}


def raw_post(path: str, payload: dict, label: str) -> dict:
    """Make raw POST request, print full protocol details, return result dict."""
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "Accept":        "application/json",
        "access-token":  tok_clean,
        "client-id":     CLIENT_ID,
    }
    hdr(f"SECTION — {label}  [{ts()}]")
    print(f"  URL     : POST {url}")
    print(f"  Body    : {json.dumps(payload)}")
    print(f"  Headers :")
    for k, v in headers.items():
        display = v if k != "access-token" else f"{v[:15]}...{v[-10:]}"
        print(f"    {k}: {display}")

    t0 = time.perf_counter()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"\n  HTTP status     : {resp.status_code}")
        print(f"  Elapsed         : {elapsed_ms:.0f} ms")
        print(f"  Content-Type    : {resp.headers.get('Content-Type', 'n/a')}")
        print(f"  Response size   : {len(resp.content)} bytes")
        try:
            body = resp.json()
            print(f"  Parsed JSON     : {json.dumps(body, indent=4)}")
        except Exception:
            print(f"  Raw body        : {resp.text[:800]!r}")
            body = {}
        return {"status_code": resp.status_code, "body": body, "ok": resp.status_code == 200}
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"  ❌ Exception after {elapsed_ms:.0f}ms : {e}")
        return {"status_code": None, "body": {}, "ok": False, "error": str(e)}


# ── Run the 4 raw HTTP tests ───────────────────────────────────────────────

results = {}

results["fundlimit"] = raw_get("/fundlimit", "2 — GET /fundlimit (auth smoke test)")
results["ltp"]       = raw_post("/marketfeed/ltp",   TEST_PAYLOAD, "3 — POST /marketfeed/ltp")
results["ohlc"]      = raw_post("/marketfeed/ohlc",  TEST_PAYLOAD, "4 — POST /marketfeed/ohlc")
results["quote"]     = raw_post("/marketfeed/quote", TEST_PAYLOAD, "5 — POST /marketfeed/quote")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SDK parity comparison
# ══════════════════════════════════════════════════════════════════════════════

hdr(f"SECTION 6 — SDK Parity (dhanhq library)  [{ts()}]")

sdk_result = {}
try:
    import dhanhq as _pkg
    _ver = getattr(_pkg, "__version__", "unknown")
    print(f"  dhanhq version  : {_ver}")

    try:
        from dhanhq import DhanContext, dhanhq as _DhanHQ
        ctx  = DhanContext(CLIENT_ID, tok_clean)
        dhan = _DhanHQ(ctx)
        print("  SDK init        : ✅  DhanContext + dhanhq(ctx) succeeded")
        _ctx_mode = "v2.1+"
    except (ImportError, Exception) as e1:
        print(f"  DhanContext init failed: {e1} — trying v2.0.x direct init")
        from dhanhq import dhanhq as _DhanHQ
        dhan     = _DhanHQ(CLIENT_ID, tok_clean)
        _ctx_mode = "v2.0.x"
        print("  SDK init        : ✅  dhanhq(client_id, token) succeeded")

    # ohlc_data via SDK
    sub("SDK: ohlc_data")
    t0 = time.perf_counter()
    try:
        sdk_resp = dhan.ohlc_data(securities=TEST_PAYLOAD)
        sdk_elapsed = (time.perf_counter() - t0) * 1000
        print(f"  Elapsed         : {sdk_elapsed:.0f} ms")
        print(f"  Response type   : {type(sdk_resp).__name__}")
        print(f"  Response        : {json.dumps(sdk_resp, indent=4) if isinstance(sdk_resp, dict) else repr(sdk_resp)[:500]}")
        sdk_result["ohlc"] = {"ok": isinstance(sdk_resp, dict) and sdk_resp.get("status") != "failure", "body": sdk_resp}
    except Exception as e:
        sdk_elapsed = (time.perf_counter() - t0) * 1000
        print(f"  ❌ Exception after {sdk_elapsed:.0f}ms : {e}")
        sdk_result["ohlc"] = {"ok": False, "error": str(e)}

    # ticker_data (LTP) via SDK
    sub("SDK: ticker_data (LTP)")
    t0 = time.perf_counter()
    try:
        sdk_resp2 = dhan.ticker_data(securities=TEST_PAYLOAD)
        sdk_elapsed2 = (time.perf_counter() - t0) * 1000
        print(f"  Elapsed         : {sdk_elapsed2:.0f} ms")
        print(f"  Response type   : {type(sdk_resp2).__name__}")
        print(f"  Response        : {json.dumps(sdk_resp2, indent=4) if isinstance(sdk_resp2, dict) else repr(sdk_resp2)[:500]}")
        sdk_result["ltp"] = {"ok": isinstance(sdk_resp2, dict) and sdk_resp2.get("status") != "failure", "body": sdk_resp2}
    except Exception as e:
        sdk_elapsed2 = (time.perf_counter() - t0) * 1000
        print(f"  ❌ Exception after {sdk_elapsed2:.0f}ms : {e}")
        sdk_result["ltp"] = {"ok": False, "error": str(e)}

except Exception as e:
    print(f"  ❌ SDK import/init failed: {e}")
    sdk_result = {"init_error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Diagnostic Report
# ══════════════════════════════════════════════════════════════════════════════

hdr(f"SECTION 7 — DIAGNOSTIC REPORT  [{ts()}]")

def status_icon(result: dict) -> str:
    sc = result.get("status_code")
    if sc == 200:
        return "✅ 200 OK"
    elif sc == 401:
        return "❌ 401 AUTH FAILED"
    elif sc == 403:
        return "❌ 403 FORBIDDEN"
    elif sc == 429:
        return "⚠️ 429 RATE LIMITED"
    elif sc == 451:
        return "⚠️ 451 BLOCKED"
    elif sc is None:
        return f"❌ EXCEPTION: {result.get('error', 'unknown')}"
    else:
        return f"⚠️ HTTP {sc}"

print("\n  Raw HTTP Results:")
print(f"    GET  /fundlimit          : {status_icon(results['fundlimit'])}")
print(f"    POST /marketfeed/ltp     : {status_icon(results['ltp'])}")
print(f"    POST /marketfeed/ohlc    : {status_icon(results['ohlc'])}")
print(f"    POST /marketfeed/quote   : {status_icon(results['quote'])}")

raw_any_ok  = any(r.get("ok") for r in results.values())
raw_all_401 = all(
    r.get("status_code") in (401, 403, 451)
    for r in results.values()
    if r.get("status_code") is not None
)
raw_all_fail = not raw_any_ok

print("\n  SDK Results:")
for k, v in sdk_result.items():
    if k == "init_error":
        print(f"    SDK init                 : ❌ {v}")
    else:
        sdk_ok = v.get("ok", False)
        print(f"    SDK {k:<20}     : {'✅ SUCCESS' if sdk_ok else '❌ FAILURE'}")

sdk_any_ok = any(v.get("ok") for k, v in sdk_result.items() if k != "init_error")

print("\n" + SEP)

if raw_any_ok:
    print("""
  VERDICT: CASE A — RAW REQUESTS SUCCEED
  =======================================
  Raw HTTP calls work but SDK/integration is broken.

  Root cause: SDK abstraction layer is corrupting headers,
  payload format, or auth parameters before the request leaves
  the process.

  Action required:
    1. Inspect dhanhq library version installed on VPS
    2. Compare request headers sent by SDK vs raw requests
    3. Check DhanContext constructor — may be building wrong auth header
    4. Possible fix: pin dhanhq to a specific version or monkey-patch headers
""")
elif raw_all_401 and not raw_any_ok:
    print("""
  VERDICT: CASE B — AUTH REJECTED BY DHAN (HTTP 401)
  ====================================================
  Raw requests fail identically to SDK.

  This is definitively a Dhan-side auth/API issue, NOT a
  deployment or SDK integration problem.

  Possible root causes (in order of likelihood):
    1. TOKEN EXPIRED — JWT exp has passed. Generate fresh token.
    2. TOKEN MISMATCH — token was generated for a different client_id.
    3. DATA SUBSCRIPTION lapsed — marketfeed requires active subscription.
    4. IP WHITELIST — Dhan may have blocked VPS IP (rare but possible).
    5. ACCOUNT ISSUE — broker-side restriction on API access.

  Action required:
    → Login to Dhan portal, generate a new token, send:
      /token <new_token>  via Telegram to hot-swap into runtime.
    → Or: verify data API subscription status in Dhan account settings.
""")
elif not raw_any_ok:
    raw_codes = {k: v.get("status_code") for k, v in results.items()}
    print(f"""
  VERDICT: CASE B (variant) — ALL RAW REQUESTS FAIL
  ===================================================
  HTTP status codes: {raw_codes}

  All raw endpoints failing. Examine status codes above for exact cause.
""")

print(SEP)
print(f"\n  Report generated at: {datetime.now(timezone.utc).isoformat()}")
print(f"  CLIENT_ID used     : {CLIENT_ID!r}")
print(f"  Token first 20 ch  : {tok_clean[:20]!r}")
print(f"  Token last 20 ch   : {tok_clean[-20:]!r}")
print(f"  Token length       : {len(tok_clean)}")
