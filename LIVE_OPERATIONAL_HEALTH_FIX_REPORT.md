# LIVE_OPERATIONAL_HEALTH_FIX_REPORT — FRZ-001

**Date:** 2026-08-11  
**Commit:** `3ecf7f8`  
**Status:** DEPLOYED AND HEALTHY

---

## A. Scheduler — Duplicate Cycle Elimination

### Before
`DEEP_SCAN_SCHEDULE` in `market_intelligence/market_monitor.py` contained:
```
"09:05", "09:10", "09:20",
"10:30", "11:30", "13:00", "14:00", "15:00"   ← overlapped with sched_lib
```
`sched_lib` in `start_scheduler()` ALSO registered 10:30/11:30/13:00/14:00/15:00.  
At each of those 5 times, two independent code paths both fired `run_full_cycle()`:
- sched_lib → `_guarded_cycle()` → `run_full_cycle()` (synchronous, scheduler thread)
- MarketMonitor → `_on_deep_scan()` → `task_queue.submit_to(..., run_full_cycle)` (async)

**Result:** 4 ghost cycles observed today (10:30, 11:30, 13:00, 15:00), each ~14 s apart.

### After
`DEEP_SCAN_SCHEDULE` now contains **only 3 entries**:
```python
DEEP_SCAN_SCHEDULE: List[str] = [
    "09:05",   # market open — regime detection
    "09:10",   # first opportunity scan
    "09:20",   # strategy evaluation
]
```
sched_lib continues to own 10:30/11:30/13:00/14:00/15:00 exclusively.

### Duplicate cycles eliminated
| Slot | Before | After |
|------|--------|-------|
| 09:05–09:20 | MarketMonitor only | MarketMonitor only ✅ |
| 10:30 | MarketMonitor + sched_lib = 2 | sched_lib only = 1 ✅ |
| 11:30 | MarketMonitor + sched_lib = 2 | sched_lib only = 1 ✅ |
| 13:00 | MarketMonitor + sched_lib = 2 | sched_lib only = 1 ✅ |
| 14:00 | MarketMonitor + sched_lib = 2 | sched_lib only = 1 ✅ |
| 15:00 | MarketMonitor + sched_lib = 2 | sched_lib only = 1 ✅ |

### Schedule ownership — post-fix
```
MarketMonitor:  09:05  09:10  09:20  (opening window only)
sched_lib:      09:45  10:30  11:30  13:00  14:00  15:00  (all full cycles)
Zero overlap.
```

**File changed:** `market_intelligence/market_monitor.py`  
**Interfaces changed:** None

---

## B. Journal — Stale OPEN Reconciliation

### Before
`OrderManager._restore_from_journal()` used `_MAX_LOOKBACK_DAYS = 7`:
- Pass 2 skipped rows older than 7 days entirely (`if row_dt < cutoff_dt: continue`)
- Those rows were never restored AND never expired
- `CycleHealthMonitor` read the full CSV and found them, reporting stale=1 every cycle

**HAVELLS status (before):**  
`SIM_HAVELLS_BUY_Q282_P1229.66_1785125710081` (15.0d) — OPEN row with no CLOSE.  
Visible to CycleHealthMonitor. Invisible to OrderManager. Permanent false stale alert.

### After
**Pass 1.9 added** — scans back up to 60 days for unmatched OPEN rows with `SIM_` prefix:
```
_DEEP_ORPHAN_DAYS = 60   # extended scan window for SIM_ orphans
Safety: only SIM_-prefixed order_ids (paper records)
Action: append SESSION_EXPIRED_DEEP_ORPHAN CLOSE row (audit trail preserved)
Idempotent: closed_in_csv is updated before Pass 2; re-runs are no-ops
```

**HAVELLS status (after next restart):**  
`SIM_HAVELLS_BUY_Q282_P1229.66_1785125710081` → receives SESSION_EXPIRED_DEEP_ORPHAN CLOSE.  
CycleHealthMonitor no longer sees an unmatched OPEN. Stale alert eliminated.

### Safety guarantees
- Real Dhan order IDs (non-`SIM_` prefix) are **never** touched
- Original OPEN rows are **preserved** (append-only journal)
- New CLOSE row has `reason=SESSION_EXPIRED_DEEP_ORPHAN` for full auditability
- Idempotent: running twice writes exactly one CLOSE per orphan

**File changed:** `execution_engine/order_manager.py`  
**Interfaces changed:** None (internal only)

---

## C. Dhan — 09:15 Readiness Probe Sequence

### Old sequence (before fix)
```
Container start (e.g. 16:00)
  → connect() called
  → _is_market_open() = False
  → probe deferred (OUTSIDE_MARKET_HOURS)
  → equity_verified = False  (stays False overnight)

09:45 Cycle #1 starts
  → equity_verified still False
  → api_mode = FALLBACK
  → cycle runs on Yahoo Finance

[end of cycle]
  → check_truth_governance() called
  → check_market_open_readiness() fires (>5 min since last probe)
  → _readiness_probe() executes at 09:45:17
  → might fail (e.g. transient Dhan API at open)
  → Cycle #1 was already done in FALLBACK mode
```

### New sequence (after fix)
```
Container start (e.g. 16:00)
  → connect() called
  → _is_market_open() = False
  → probe deferred (unchanged — existing safe behavior)

09:15  sched_lib fires _dhan_equity_readiness_probe_0915()
  → Calls DhanFeed._readiness_probe() [READ-ONLY — no orders]
  → If successful: equity_verified = True → LIVE_VERIFIED
  → If failed: equity_verified = False → FALLBACK retained, warning logged

09:45 Cycle #1 starts
  → equity_verified = True (if Dhan was reachable at 09:15)
  → api_mode = LIVE_VERIFIED
  → cycle runs on Dhan live equity feed
```

### Fallback safety
If the 09:15 probe fails:
- `equity_verified` stays False → system uses FALLBACK (Yahoo Finance)
- Yahoo Finance provides `FeedTruthLevel.LIVE` (confirmed today: 100% live, last=41s)
- No simulated data is used
- FeedTruth governance is unaffected
- The probe NEVER places, modifies, or cancels any order

**File changed:** `orchestrator/master_orchestrator.py` (new method + one scheduler line)  
**Interfaces changed:** None

---

## D. Regression Results

| Test suite | Result |
|------------|--------|
| FRZ-001 scheduler tests | **26/26 PASS** |
| FRZ-001 journal tests | **8/8 PASS** |
| FRZ-001 Dhan probe tests | **13/13 PASS** |
| **Total FRZ-001** | **47/47 PASS** |
| Pre-existing test suite failures | 6 (unchanged before and after — confirmed via `git stash` comparison) |
| **Net new failures** | **0** |

Pre-existing failures are in `test_aet.py::TestExecuteAetIntegration` and `test_exit_attribution.py::TestExitAttributionIntegration` — unrelated to this fix, confirmed identical pre/post.

---

## E. Production State

| Component | Value |
|-----------|-------|
| Git commit | `3ecf7f8` |
| LOCAL | `3ecf7f8` ✅ |
| GIT (origin/main) | `3ecf7f8` ✅ |
| VPS | `3ecf7f8` ✅ |
| Container `ai-trading-brain` | Up (healthy) ✅ |
| Container `trading-dashboard` | Up (healthy) ✅ |

Container source verification:
```
DEEP_SCAN_SCHEDULE = ["09:05", "09:10", "09:20"]  ← confirmed via grep
_dhan_equity_readiness_probe_0915 at line 5771    ← confirmed via grep
SESSION_EXPIRED_DEEP_ORPHAN at line 3095           ← confirmed via grep
```

Backup: `data/frz/backups/FRZ001_backup_20260811_161202_bc61215/`

---

## F. Trading Safety

All of the following are **unchanged** from commit `bc61215` to `3ecf7f8`:

| Parameter | Value | Changed? |
|-----------|-------|----------|
| `TOTAL_CAPITAL` | ₹10,000 | No |
| `PAPER_TRADING` | False | No |
| `MAX_RISK_PER_TRADE_PCT` | 0.0025 (0.25%) | No |
| `MIN_RR_RATIO` (R:R) | 2.0 | No |
| `KILL_SWITCH_VIX` | 45.0 | No |
| `MAX_DAILY_LOSS_PCT` | 2.0% | No |
| Mean_Reversion status | DISABLED (EARLY_ABORT_LOW_WR) | No |
| BUY logic | Unchanged | No |
| SHORT logic | Unchanged | No |
| PMCI / CDS / DNA / IKN | Unchanged | No |
| Universe / watchlist | Unchanged | No |
| Capital-share mapping | Unchanged | No |
| Order sizing rules | Unchanged | No |

---

## DEFERRED OBSERVATIONS

The following issues were noticed during investigation but are out of scope for FRZ-001:

1. **GlobalIntelligence latency spikes** — Cycles #3 and #5 showed 13.6s and 13.7s for GlobalIntelligence (exceeds `LAYER_LATENCY_CRIT_OVERRIDES["GlobalIntelligence"] = 12_000`). Cause: yfinance international markets fetch under load. No code path changed in FRZ-001.

2. **NIFTYBEES R:R 0.44** — Structurally unviable signal (would need 69% WR to break even). This is correct governance behavior. The R:R of 0.44 is the actual signal, not a calculation error. Investigating whether the setup geometry can be improved is deferred.

3. **CRE QTY_ZERO pattern** — ₹900 budget per signal vs ₹1,277+ stock prices. This is a structural sizing mismatch that will persist until stock prices fall or capital allocation changes. Deferred as not an operational bug.

4. **`MULTI_SID_REJECTED` pre-market logs** — Dhan's equity `ltp_single`/`quote_data` endpoint sporadically rejects multi-SID batch requests. Not a fix target — FRZ-001 Phase 3 mitigates this by pre-verifying at 09:15 before the first cycle.

---

## Summary

Three surgical operational fixes deployed. Zero trading logic changed. Zero regressions.
