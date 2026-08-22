"""
Dhan Minimal Forensic Test
===========================
Isolated direct test of Dhan API behavior.

PURPOSE
-------
Determine whether the Dhan OHLC issue is caused by:
  - VPS IP restriction
  - Container / network filtering
  - Library mismatch
  - Malformed request structure
  - Segment mapping issue
  - Production-layer transformation bug

ISOLATION RULES
---------------
  • Uses ONLY: dhanhq.dhanhq (no production wrappers)
  • No fallback layers, retry layers, transformations, abstractions
  • Raw responses printed exactly as returned
  • Runs identically on Windows and VPS/container

USAGE
-----
  python tools/test_dhan_direct.py

CREDENTIALS (read from environment)
-------------------------------------
  DHAN_CLIENT_ID       — your Dhan client ID
  DHAN_ACCESS_TOKEN    — your current Dhan access token

SECURITIES USED (NSE security IDs)
-------------------------------------
  1333   = HDFC Bank (liquid large-cap)
  11536  = Infosys
  3045   = RELIANCE
  49081  = NIFTY 50 current-week ATM CE (approx, FNO segment)
  13     = NIFTY 50 index (IDX_I segment)
"""

from __future__ import annotations

import os
import platform
import socket
import sys
import time
import traceback

SEP  = "─" * 64
SEP2 = "═" * 64


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def _p(tag: str, **kw) -> None:
    pairs = "  ".join(f"{k}={v}" for k, v in kw.items())
    print(f"[{tag}]  {pairs}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Library & Environment Forensics
# ─────────────────────────────────────────────────────────────────────────────

def print_environment() -> None:
    print(SEP2)
    print("[DhanEnvironment]  System inventory")
    print(SEP2)

    try:
        import importlib.metadata
        dhan_ver = importlib.metadata.version("dhanhq")
    except Exception:
        dhan_ver = "unknown"

    _p("DhanEnvironment",
       dhanhq_version=dhan_ver,
       python=sys.version.replace("\n", " "),
       platform=platform.platform(),
       hostname=socket.gethostname(),
       container_cgroup=_container_tag(),
    )
    print()


def _container_tag() -> str:
    """Best-effort detection of Docker/container environment."""
    try:
        cg = open("/proc/1/cgroup").read()
        if "docker" in cg or "containerd" in cg:
            return "DOCKER"
    except Exception:
        pass
    try:
        open("/.dockerenv")
        return "DOCKER"
    except Exception:
        pass
    return "BARE_HOST"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Network Forensics
# ─────────────────────────────────────────────────────────────────────────────

def print_network_diagnostics() -> None:
    print(SEP)
    print("[DhanNetworkTest]  Connectivity to api.dhan.co")
    print(SEP)

    # Public outbound IP
    try:
        import urllib.request
        t0 = time.monotonic()
        pub_ip = urllib.request.urlopen(
            "https://api.ipify.org", timeout=6
        ).read().decode().strip()
        pub_ip_ms = int((time.monotonic() - t0) * 1000)
        _p("DhanNetworkTest", check="public_ip", ip=pub_ip, latency_ms=pub_ip_ms)
    except Exception as exc:
        _p("DhanNetworkTest", check="public_ip", result=f"FAILED: {exc}")

    # DNS resolution for api.dhan.co
    try:
        t0 = time.monotonic()
        resolved = socket.getaddrinfo("api.dhan.co", 443, socket.AF_INET)
        dns_ms = int((time.monotonic() - t0) * 1000)
        ips = list({r[4][0] for r in resolved})
        _p("DhanNetworkTest", check="dns_api.dhan.co", resolved=ips, latency_ms=dns_ms)
    except Exception as exc:
        _p("DhanNetworkTest", check="dns_api.dhan.co", result=f"FAILED: {exc}")

    # TCP handshake to api.dhan.co:443
    try:
        t0 = time.monotonic()
        s = socket.create_connection(("api.dhan.co", 443), timeout=8)
        tcp_ms = int((time.monotonic() - t0) * 1000)
        s.close()
        _p("DhanNetworkTest", check="tcp_443", result="OPEN", latency_ms=tcp_ms)
    except Exception as exc:
        _p("DhanNetworkTest", check="tcp_443", result=f"FAILED: {exc}")

    # TLS handshake (HTTPS GET to base URL)
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.dhan.co/",
            headers={"User-Agent": "dhan-forensic-test/1.0"},
        )
        t0 = time.monotonic()
        try:
            resp = urllib.request.urlopen(req, timeout=8)
            tls_ms = int((time.monotonic() - t0) * 1000)
            _p("DhanNetworkTest", check="tls_handshake",
               result="SUCCESS", http_status=resp.status, latency_ms=tls_ms)
        except urllib.error.HTTPError as he:
            tls_ms = int((time.monotonic() - t0) * 1000)
            # Any HTTP response (including 401/403/404) means TLS works
            _p("DhanNetworkTest", check="tls_handshake",
               result=f"HTTP_{he.code}_OK", latency_ms=tls_ms,
               note="TLS success — server returned HTTP error as expected for unauthenticated root")
    except Exception as exc:
        _p("DhanNetworkTest", check="tls_handshake", result=f"FAILED: {exc}")

    print()


# ─────────────────────────────────────────────────────────────────────────────
# Credential loading
# ─────────────────────────────────────────────────────────────────────────────

def load_credentials() -> tuple[str, str]:
    client_id    = os.getenv("DHAN_CLIENT_ID", "").strip()
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()

    print(SEP)
    tok_preview = (access_token[:8] + "…" + access_token[-4:]) if len(access_token) > 14 else "?"
    _p("DhanCredentials",
       client_id=client_id or "MISSING",
       access_token_preview=tok_preview,
       token_length=len(access_token),
    )
    print()

    if not client_id or not access_token:
        print("ERROR: DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN environment variables are required.")
        print("       Export them before running this script.")
        sys.exit(1)

    return client_id, access_token


# ─────────────────────────────────────────────────────────────────────────────
# Test runner helper
# ─────────────────────────────────────────────────────────────────────────────

def run_test(label: str, fn) -> dict:
    """Run a single test, print raw result, return classification."""
    print(SEP)
    print(f"TEST {label}")
    print(SEP)

    result = {
        "label":      label,
        "success":    False,
        "http_ok":    False,
        "data_empty": True,
        "error":      None,
        "latency_ms": None,
        "raw":        None,
    }

    try:
        t0 = time.monotonic()
        raw = fn()
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        result["latency_ms"] = elapsed_ms
        result["raw"]        = raw

        _p("DhanDirectTest",
           test=label,
           latency_ms=elapsed_ms,
        )
        print(f"  response type : {type(raw).__name__}")
        if isinstance(raw, dict):
            print(f"  response keys : {list(raw.keys())}")
            print(f"  full response :\n{_indent(str(raw))}")
            # Classification
            status = str(raw.get("status", "")).upper()
            data   = raw.get("data", raw.get("results", None))
            result["http_ok"] = True
            if data is not None:
                non_empty = bool(data)
                result["data_empty"] = not non_empty
                result["success"]    = non_empty
            else:
                # Some responses have data at top level
                keys = [k for k in raw if k not in ("status", "remarks", "errorCode")]
                result["data_empty"] = len(keys) == 0
                result["success"]    = not result["data_empty"]
        else:
            print(f"  raw value : {raw}")
            result["http_ok"]    = raw is not None
            result["data_empty"] = raw is None or (hasattr(raw, "__len__") and len(raw) == 0)
            result["success"]    = not result["data_empty"]

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t0) * 1000) if 't0' in dir() else 0
        result["error"]      = str(exc)
        result["latency_ms"] = elapsed_ms
        _p("DhanDirectTest", test=label, status="EXCEPTION", error=str(exc))
        print(f"  traceback :\n{_indent(traceback.format_exc())}")

    # Quick classification
    cls = _classify(result)
    _p("DhanDirectTest", test=label, classification=cls)
    print()
    return result


def _indent(s: str, n: int = 4) -> str:
    pad = " " * n
    return "\n".join(pad + line for line in s.splitlines())


def _classify(r: dict) -> str:
    if r["error"]:
        return "CASE_3_HTTP_FAILURE"
    if r["http_ok"] and not r["data_empty"]:
        return "CASE_1_SUCCESS_DATA_POPULATED"
    if r["http_ok"] and r["data_empty"]:
        return "CASE_2_SUCCESS_EMPTY_DATA"
    return "CASE_3_HTTP_FAILURE"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Test Matrix
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests(client_id: str, access_token: str) -> list[dict]:
    _mod = __import__("dhanhq")
    _ver = getattr(_mod, "__version__", "")
    # dhanhq < 2.1 : dhanhq(client_id, access_token)
    # dhanhq >= 2.1 : dhanhq(DhanContext(client_id, access_token))
    if hasattr(_mod, "DhanContext"):
        dhan = _mod.dhanhq(_mod.DhanContext(client_id, access_token))
    else:
        dhan = _mod.dhanhq(client_id, access_token)

    results = []

    # ── TEST A — OHLC single equity ───────────────────────────────────────
    results.append(run_test(
        "A — OHLC single equity (HDFC Bank, NSE_EQ, secId=1333)",
        lambda: dhan.ohlc_data(securities={"NSE_EQ": [1333]}),
    ))

    # ── TEST B — Quote / LTP single equity ───────────────────────────────
    results.append(run_test(
        "B — Quote/LTP single equity (HDFC Bank, NSE_EQ, secId=1333)",
        lambda: dhan.quote_data(securities={"NSE_EQ": [1333]}),
    ))

    # ── TEST C — OHLC multiple equities ──────────────────────────────────
    results.append(run_test(
        "C — OHLC multiple equities (HDFC 1333, Infosys 11536, RELIANCE 3045)",
        lambda: dhan.ohlc_data(securities={"NSE_EQ": [1333, 11536, 3045]}),
    ))

    # ── TEST D — OHLC FNO segment ─────────────────────────────────────────
    results.append(run_test(
        "D — OHLC FNO segment (NSE_FNO, secId=49081)",
        lambda: dhan.ohlc_data(securities={"NSE_FNO": [49081]}),
    ))

    # ── TEST E — OHLC Index segment ───────────────────────────────────────
    results.append(run_test(
        "E — OHLC Index (IDX_I, secId=13 = NIFTY 50)",
        lambda: dhan.ohlc_data(securities={"IDX_I": [13]}),
    ))

    # ── TEST F — Quote all segments in one call ───────────────────────────
    results.append(run_test(
        "F — Quote multi-segment (NSE_EQ + IDX_I combined)",
        lambda: dhan.quote_data(securities={"NSE_EQ": [1333], "IDX_I": [13]}),
    ))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — Forensic Conclusion
# ─────────────────────────────────────────────────────────────────────────────

def print_conclusion(results: list[dict]) -> None:
    print(SEP2)
    print("[DhanForensicConclusion]")
    print(SEP2)

    # Aggregate
    all_success     = [r for r in results if r["success"]]
    all_empty       = [r for r in results if r["http_ok"] and r["data_empty"] and not r["error"]]
    all_failed      = [r for r in results if r["error"]]
    eq_results      = [r for r in results if "NSE_EQ"  in r["label"]]
    fno_results     = [r for r in results if "NSE_FNO" in r["label"]]
    ohlc_results    = [r for r in results if "OHLC" in r["label"].upper()]
    quote_results   = [r for r in results if "Quote" in r["label"] or "LTP" in r["label"]]

    api_reachable   = any(r["http_ok"] for r in results)
    data_populated  = any(r["success"] for r in results)
    eq_works        = any(r["success"] for r in eq_results)
    fno_works       = any(r["success"] for r in fno_results)
    ohlc_works      = any(r["success"] for r in ohlc_results)
    quote_works     = any(r["success"] for r in quote_results)

    print(f"  api_reachable       : {'✅ YES' if api_reachable  else '❌ NO'}")
    print(f"  data_populated      : {'✅ YES' if data_populated else '❌ NO (all responses empty)'}")
    print(f"  ohlc_data() works   : {'✅ YES' if ohlc_works     else '❌ NO'}")
    print(f"  quote_data() works  : {'✅ YES' if quote_works    else '❌ NO'}")
    print(f"  NSE_EQ segment      : {'✅ YES' if eq_works       else '❌ NO'}")
    print(f"  NSE_FNO segment     : {'✅ YES' if fno_works      else '❌ NO'}")
    print()

    # Per-test summary
    print("  Test summary:")
    for r in results:
        icon = "✅" if r["success"] else ("⚠️" if r["http_ok"] else "❌")
        cls  = _classify(r)
        lat  = f"{r['latency_ms']}ms" if r["latency_ms"] is not None else "?"
        print(f"    {icon}  {r['label'][:55]:<55}  {lat:<8}  {cls}")
    print()

    # Root cause diagnosis
    print("  Probable root cause:")
    if not api_reachable:
        print("    🔴 CASE 3 — Network/Auth failure.")
        print("       API is unreachable. Check: IP firewall, VPS outbound rules,")
        print("       token validity, TLS interception by datacenter.")
        confidence = "HIGH"
    elif api_reachable and not data_populated:
        # All segments empty
        print("    🟡 CASE 2 — HTTP success but all data EMPTY.")
        print("       Most likely: VPS IP not whitelisted by Dhan, or")
        print("       access token lacks data-API entitlement,")
        print("       or Dhan is silently returning empty for non-prod IPs.")
        confidence = "HIGH"
        print()
        print("    ACTION: Compare with Windows result.")
        print("      If Windows returns data and VPS returns empty →")
        print("        → VPS IP restriction (whitelist VPS IP at Dhan portal)")
        print("      If both return empty →")
        print("        → Token entitlement issue (data API not enabled for this token)")
    elif ohlc_works and not quote_works:
        print("    🟡 CASE 4 — Segment-specific: ohlc_data works but quote_data fails.")
        print("       Possible method-level entitlement difference.")
        confidence = "MEDIUM"
    elif quote_works and not ohlc_works:
        print("    🟡 CASE 4 — Segment-specific: quote_data works but ohlc_data fails.")
        print("       Possible ohlc_data API restriction or wrong request structure.")
        confidence = "MEDIUM"
    elif eq_works and not fno_works:
        print("    🟡 CASE 4 — Segment-specific: NSE_EQ works but NSE_FNO fails.")
        print("       FNO data entitlement may not be enabled on this token.")
        confidence = "MEDIUM"
    elif data_populated:
        print("    ✅ CASE 1 — Data populated successfully.")
        print("       API works. Issue is in the production transformation/mapping layer.")
        print("       Check: dhan_feed.py response parsing, symbol→secId mapping,")
        print("       or how the production wrapper processes ohlc_data() output.")
        confidence = "HIGH"
    else:
        print("    ❓ INCONCLUSIVE — Mixed results. Review per-test classification above.")
        confidence = "LOW"

    print()
    print(f"  confidence          : {confidence}")
    print(f"  timestamp_utc       : {_ts()}")
    print(SEP2)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print(SEP2)
    print("  DHAN MINIMAL FORENSIC TEST")
    print(f"  {_ts()}")
    print(SEP2)
    print()

    print_environment()
    print_network_diagnostics()
    client_id, access_token = load_credentials()
    results = run_all_tests(client_id, access_token)
    print_conclusion(results)


if __name__ == "__main__":
    main()
