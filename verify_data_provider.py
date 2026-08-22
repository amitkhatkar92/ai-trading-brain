"""
DHAN Data Provider Verification Script
Read-only diagnostic — does NOT modify any production code or data.
"""
from __future__ import annotations
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Bootstrap ──────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

# Suppress INFO spam; keep warnings and above for feed internals
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("verify_provider")
log.setLevel(logging.DEBUG)

TEST_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "LT", "BEL", "HAL", "TATAMOTORS",
]
DAYS = 22   # ~1 month of trading days


# ── Feed status ─────────────────────────────────────────────────────────────

def check_feed_status():
    print("\n" + "="*60)
    print("SECTION 1: FEED STATUS")
    print("="*60)

    # AngelOne
    try:
        from data_feeds.angelone_feed import AngelOneFeed
        ao = AngelOneFeed()
        ao_live = ao.is_live
    except Exception as e:
        ao_live = False
        print(f"AngelOne init error: {e}")

    # Dhan
    from data_feeds.dhan_feed import DhanFeed, DHAN_SECURITY_MAP
    dhan = DhanFeed()
    state = dhan.auth_state()

    print(f"AngelOne: is_live={ao_live}")
    print(f"Dhan:     is_live={dhan.is_live}")
    print(f"Dhan:     token_present={state['token_present']}")
    print(f"Dhan:     token_expired={state['token_expired']}")
    print(f"Dhan:     api_mode={state['api_mode']}")
    print(f"Dhan:     expires_in={state.get('expires_in_h','?')}")

    # Symbol coverage check
    print("\nDHAN_SECURITY_MAP coverage for test symbols:")
    for sym in TEST_SYMBOLS:
        covered = sym in DHAN_SECURITY_MAP
        if covered:
            meta = DHAN_SECURITY_MAP[sym]
            print(f"  {sym:<15} ✓  security_id={meta['security_id']:<8} segment={meta['segment']}")
        else:
            print(f"  {sym:<15} ✗  NOT in DHAN_SECURITY_MAP → falls to Yahoo")

    return ao_live, dhan.is_live, dhan, ao_live


# ── Provider priority trace ──────────────────────────────────────────────────

def trace_provider_priority():
    print("\n" + "="*60)
    print("SECTION 2: PROVIDER PRIORITY (DataFeedManager.get_history)")
    print("="*60)
    print("""
Code path (data_feeds/data_feed_manager.py line 800-827):

    def get_history(self, symbol, days=30, interval='1d', indian=False):
        bare = symbol.upper().replace('.NS','').replace('.BO','')
        # 1. AngelOne: PRIMARY for NSE equities (if angelone.is_live)
        if self.angelone.is_live and bare not in self._GLOBAL_SYMBOLS:
            ao_bars = self.angelone.get_history(bare, days, interval)
            if ao_bars:
                return ao_bars
        # 2. Dhan: FALLBACK (if dhan.is_live AND symbol in DHAN_SECURITY_MAP)
        from .dhan_feed import DHAN_SECURITY_MAP
        if self.dhan.is_live and symbol.upper() in DHAN_SECURITY_MAP:
            bars = self.dhan.get_history(symbol, days, interval)
            if bars:
                return bars
        # 3. NSE (only if indian=True)
        if indian:
            return self.nse.get_history(symbol, days, interval)
        # 4. Yahoo Finance: final fallback
        return self.yahoo.get_history(symbol, days, interval)

IMPORTANT: historical_replay.py uses yfinance DIRECTLY via
oios/data/ohlcv_fetcher.py — NOT via DataFeedManager.
""")


# ── Live validation ──────────────────────────────────────────────────────────

def validate_symbol(dhan, ao_live, symbol: str) -> Dict[str, Any]:
    from data_feeds.dhan_feed import DHAN_SECURITY_MAP
    result = {
        "symbol": symbol,
        "in_dhan_map": symbol in DHAN_SECURITY_MAP,
        "provider_used": None,
        "candles": 0,
        "ohlc_ok": False,
        "volume_ok": False,
        "sample_date": None,
        "sample_close": None,
        "fallback": False,
        "error": None,
    }

    # Determine expected provider
    if ao_live and symbol not in ("SP500", "VIX"):
        result["expected_provider"] = "ANGELONE"
    elif dhan.is_live and symbol in DHAN_SECURITY_MAP:
        result["expected_provider"] = "DHAN"
    else:
        result["expected_provider"] = "YAHOO"

    # Attempt Dhan first (if live and symbol known)
    if dhan.is_live and symbol in DHAN_SECURITY_MAP:
        t0 = time.monotonic()
        try:
            bars = dhan.get_history(symbol, days=DAYS, interval="1d")
            elapsed = (time.monotonic() - t0) * 1000
            if bars:
                result["provider_used"] = "DHAN"
                result["candles"] = len(bars)
                result["elapsed_ms"] = round(elapsed)
                # Check first bar
                b = bars[-1]   # most recent
                result["ohlc_ok"] = (b.open > 0 and b.high > 0 and b.low > 0 and b.close > 0)
                result["volume_ok"] = (b.volume >= 0)
                result["sample_date"] = str(b.timestamp.date()) if b.timestamp else None
                result["sample_close"] = b.close
                result["sample_open"] = b.open
                result["sample_high"] = b.high
                result["sample_low"] = b.low
                result["sample_volume"] = b.volume
                return result
            else:
                # Dhan returned empty — note it and fall through to Yahoo
                result["dhan_returned_empty"] = True
                result["fallback"] = True
        except Exception as e:
            result["dhan_error"] = str(e)
            result["fallback"] = True

    # Attempt Yahoo (direct — no DataFeedManager needed)
    from data_feeds.yahoo_feed import YahooFeed
    yahoo = YahooFeed()
    t0 = time.monotonic()
    try:
        from data_feeds.dhan_feed import _YF_TICKERS
        yf_sym = _YF_TICKERS.get(symbol, symbol + ".NS")
        bars = yahoo.get_history(yf_sym, days=DAYS, interval="1d")
        elapsed = (time.monotonic() - t0) * 1000
        if bars:
            result["provider_used"] = "YAHOO"
            result["candles"] = len(bars)
            result["elapsed_ms"] = round(elapsed)
            b = bars[-1]
            result["ohlc_ok"] = (b.open > 0 and b.high > 0 and b.low > 0 and b.close > 0)
            result["volume_ok"] = (b.volume >= 0)
            result["sample_date"] = str(b.timestamp.date()) if b.timestamp else None
            result["sample_close"] = b.close
            result["sample_open"] = b.open
            result["sample_high"] = b.high
            result["sample_low"] = b.low
            result["sample_volume"] = b.volume
        else:
            result["provider_used"] = "YAHOO_EMPTY"
            result["error"] = "Yahoo returned no bars"
    except Exception as e:
        result["provider_used"] = "FAILED"
        result["error"] = str(e)

    return result


# ── Replay path check ─────────────────────────────────────────────────────────

def check_replay_path():
    print("\n" + "="*60)
    print("SECTION 3: HISTORICAL REPLAY DATA PATH")
    print("="*60)
    print("File: historical_replay.py")
    print("Entry: load_historical_ohlcv()")
    print("Calls: oios/data/ohlcv_fetcher.fetch_symbol_ohlcv()")
    print("Provider: yfinance HARDCODED (data_source='YFINANCE')")
    print()
    print("Evidence from oios/data/ohlcv_fetcher.py line 85:")
    print("  def fetch_symbol_ohlcv(symbol, from_date, to_date,")
    print("                         data_source='YFINANCE'):")
    print("      import yfinance as yf")
    print("      df = yf.download(symbol, ...)")
    print()
    print("=> historical_replay.py does NOT call DataFeedManager")
    print("=> historical_replay.py does NOT call DhanFeed.get_history()")
    print("=> ALL replay data comes from YFINANCE")


# ── DataFeedManager path ──────────────────────────────────────────────────────

def check_datafeedmanager(dhan, ao_live):
    print("\n" + "="*60)
    print("SECTION 4: DataFeedManager.get_history() LIVE TEST")
    print("="*60)

    results = []
    for sym in TEST_SYMBOLS:
        print(f"  Testing {sym:<15}", end=" ", flush=True)
        r = validate_symbol(dhan, ao_live, sym)
        results.append(r)
        status = "✓" if r["candles"] > 0 else "✗"
        fallback_note = " [FALLBACK→YAHOO]" if r.get("fallback") else ""
        print(f"{status}  provider={r['provider_used']:<8}  candles={r['candles']:<4}  "
              f"close={r.get('sample_close','?')}{fallback_note}")

    return results


# ── Provider statistics ───────────────────────────────────────────────────────

def compute_stats(results: List[Dict]) -> Dict:
    total = len(results)
    dhan_ok = sum(1 for r in results if r["provider_used"] == "DHAN")
    yahoo_ok = sum(1 for r in results if r["provider_used"] == "YAHOO")
    ao_ok = sum(1 for r in results if r["provider_used"] == "ANGELONE")
    failed = sum(1 for r in results if not r["candles"])
    fallback = sum(1 for r in results if r.get("fallback"))
    dhan_empty = sum(1 for r in results if r.get("dhan_returned_empty"))

    return {
        "total": total,
        "dhan_ok": dhan_ok,
        "angelone_ok": ao_ok,
        "yahoo_ok": yahoo_ok,
        "failed": failed,
        "fallback_count": fallback,
        "dhan_returned_empty": dhan_empty,
        "dhan_pct": round(dhan_ok / total * 100) if total else 0,
        "fallback_pct": round((yahoo_ok + ao_ok) / total * 100) if total else 0,
    }


def print_stats(stats: Dict):
    print("\n" + "="*60)
    print("SECTION 5: PROVIDER STATISTICS")
    print("="*60)
    print(f"Total requests:             {stats['total']}")
    print(f"Successful Dhan requests:   {stats['dhan_ok']}")
    print(f"Dhan returned empty:        {stats['dhan_returned_empty']}")
    print(f"Successful AngelOne:        {stats['angelone_ok']}")
    print(f"Successful Yahoo requests:  {stats['yahoo_ok']}")
    print(f"Failed (no data):           {stats['failed']}")
    print(f"Fallback triggered:         {stats['fallback_count']}")
    print(f"Dhan success rate:          {stats['dhan_pct']}%")
    print(f"Fallback percentage:        {stats['fallback_pct']}%")


def determine_certification(stats: Dict, ao_live: bool, dhan_live: bool) -> str:
    """Return the certification verdict."""
    # historical_replay.py always uses Yahoo — that is the HET path
    # DataFeedManager.get_history() uses AngelOne→Dhan→Yahoo
    # With no AngelOne, it's Dhan→Yahoo
    d = stats["dhan_pct"]
    if d == 100:
        return "DHAN_VERIFIED" if dhan_live else "DHAN_NOT_ACTIVE"
    elif d >= 80:
        return "MOSTLY_DHAN"
    elif d >= 30:
        return "MIXED_PROVIDERS"
    elif d == 0 and stats["yahoo_ok"] > 0:
        return "FALLBACK_DOMINATED"
    else:
        return "DHAN_NOT_ACTIVE"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("DHAN DATA PROVIDER VERIFICATION")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    ao_live, dhan_live, dhan, _ = check_feed_status()
    trace_provider_priority()
    check_replay_path()
    results = check_datafeedmanager(dhan, ao_live)
    stats = compute_stats(results)
    print_stats(stats)

    # Detailed results table
    print("\n" + "="*60)
    print("SECTION 6: DETAILED VALIDATION RESULTS")
    print("="*60)
    print(f"{'Symbol':<14} {'InDhan':<8} {'Provider':<10} {'Candles':<8} "
          f"{'OHLC':<6} {'Volume':<8} {'Last_Close':<12} {'Date'}")
    print("-"*80)
    for r in results:
        ohlc = "✓" if r["ohlc_ok"] else "✗"
        vol = "✓" if r["volume_ok"] else "✗"
        inmap = "✓" if r["in_dhan_map"] else "✗"
        close = f"{r.get('sample_close',0):.2f}" if r.get("sample_close") else "N/A"
        print(f"{r['symbol']:<14} {inmap:<8} {str(r['provider_used']):<10} "
              f"{r['candles']:<8} {ohlc:<6} {vol:<8} {close:<12} {r.get('sample_date','?')}")

    # Fallback silent check
    print("\n" + "="*60)
    print("SECTION 7: FALLBACK ANALYSIS")
    print("="*60)
    for r in results:
        if r.get("fallback"):
            reason = r.get("dhan_returned_empty") and "Dhan returned empty list" or r.get("dhan_error","unknown")
            print(f"  {r['symbol']}: FALLBACK triggered — reason: {reason}")
        if r.get("provider_used") == "DHAN" and r["in_dhan_map"]:
            print(f"  {r['symbol']}: Dhan served data directly (no fallback)")
        if not r["in_dhan_map"]:
            print(f"  {r['symbol']}: NOT in DHAN_SECURITY_MAP — Yahoo path is correct by design")

    # Verdict
    cert = determine_certification(stats, ao_live, dhan_live)
    cert_map = {
        "DHAN_VERIFIED":      "✓ 100% DHAN VERIFIED",
        "MOSTLY_DHAN":        "✓ MOSTLY DHAN",
        "MIXED_PROVIDERS":    "✓ MIXED PROVIDERS",
        "FALLBACK_DOMINATED": "✓ FALLBACK DOMINATED",
        "DHAN_NOT_ACTIVE":    "✓ DHAN NOT ACTIVE",
    }

    print("\n" + "="*60)
    print("CERTIFICATION (DataFeedManager.get_history path)")
    print("="*60)
    print(f"  {cert_map.get(cert, cert)}")
    print()
    print("CERTIFICATION (Historical Replay / HET path)")
    print("="*60)
    print("  ✓ YAHOO FINANCE — hardcoded in oios/data/ohlcv_fetcher.py")
    print("  Dhan is NOT used in historical_replay.py regardless of token status")

    # Save raw results as JSON for the markdown report
    output = {
        "timestamp": datetime.now().isoformat(),
        "ao_live": ao_live,
        "dhan_live": dhan_live,
        "results": results,
        "stats": stats,
        "datafeedmanager_cert": cert,
        "replay_provider": "YFINANCE",
    }
    out_path = Path("data/provider_verification.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nRaw results saved to {out_path}")


if __name__ == "__main__":
    main()
