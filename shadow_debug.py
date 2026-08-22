"""Check shadow audit state and breakout invalidation price quality."""
import sys
import math

# 1. Check shadow module state
from opportunity_engine.delta_refresh_shadow import _SHADOW_HISTORY, get_shadow_audit_summary, PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE
print(f"shadow_mode_flag: {PRE_CYCLE_DELTA_REFRESH_SHADOW_MODE}")
print(f"cycles_recorded_in_this_process: {len(_SHADOW_HISTORY)}")
print(f"summary: {get_shadow_audit_summary()}")

# 2. Check candidate store freshness
from opportunity_engine.candidate_store import CandidateStore, MAX_AGE_HOURS
print(f"MAX_AGE_HOURS: {MAX_AGE_HOURS}")
cands = CandidateStore.read()
print(f"candidates_loaded: {len(cands) if cands else 0}")

# 3. Check PRICE_CACHE state
import opportunity_engine.equity_scanner_ai as sc
print(f"PRICE_CACHE_size: {len(sc._PRICE_CACHE)}")
print(f"RSI_CACHE_size: {len(sc._RSI_CACHE)}")

# 4. Spot-check prices vs stored base_ltp for breakout invalidation quality
if cands:
    issues = []
    for c in cands[:10]:
        sym = c.get("symbol","")
        stored_ltp = float(c.get("base_ltp") or c.get("ltp") or 0)
        live_ltp = float(sc._PRICE_CACHE.get(sym, 0) or 0)
        if stored_ltp > 0 and live_ltp > 0:
            ratio = live_ltp / stored_ltp
            flag = " ⚠️ SUSPICIOUS" if ratio < 0.5 or ratio > 2.0 else ""
            issues.append(f"  {sym}: stored={stored_ltp:.1f} live={live_ltp:.1f} ratio={ratio:.2f}{flag}")
    print("Price quality check (stored vs live):")
    for l in issues:
        print(l)

# 5. Run shadow simulation directly and wait
import time
from opportunity_engine.delta_refresh_shadow import run_shadow_audit
run_shadow_audit("MANUAL_TEST")
time.sleep(2.0)
from opportunity_engine.delta_refresh_shadow import _SHADOW_HISTORY
print(f"cycles_after_manual_run: {len(_SHADOW_HISTORY)}")
if _SHADOW_HISTORY:
    print(f"last_record: {_SHADOW_HISTORY[-1]}")
