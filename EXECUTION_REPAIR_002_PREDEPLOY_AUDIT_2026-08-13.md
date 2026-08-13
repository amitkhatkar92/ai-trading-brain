# EXECUTION_REPAIR_002 — Pre-Deployment Safety Audit
**Date:** 2026-08-13  
**Scope:** Read-only review + testing only  
**Status:** MAPPING_BLOCKED

---

## Safety Footer (applies to this entire document)

```
Production changes:  0
VPS deployment:      0
Real Dhan orders:    0
Dhan write calls:    0
Positions created:   0
```

---

## 1. DHAN SECURITY MAP COVERAGE

### 1.1 Executable symbol universe — complete trace

```
EquityScannerAI._BASE_WATCHLIST (20 symbols)
  + EquityScannerAI._EXTENDED_WATCHLIST (18 symbols)
  + ArbitrageAI.ETF_DATA (2 symbols: NIFTYBEES, BANKBEES)
  ─────────────────────────────────────────────────────
  = 40 candidate symbols that can reach OrderManager.execute()

ArbitrageAI.FUTURES_DATA (2 symbols: NIFTY, BANKNIFTY)
  → DISABLED (_FUTURES_DISABLED = True in arbitrage_ai.py)
  → zero futures signals emitted
```

**Note on `_prepared_watchlist()` (Phase E):** candidates from `CandidateStore`
are only derived from the same `_BASE_WATCHLIST` / `_EXTENDED_WATCHLIST` symbols.
`_live_watchlist()` strips all trailing spaces at line 1255 before creating
watchlist rows; `_identify_setup()` receives already-stripped symbols.  
`TradeSignal.symbol` is therefore the bare, stripped ticker at execution time.

**Note on OptionsOrderManager:** OPTIONS/SPREAD signals are routed to
`options_order_manager.execute()`, which is pure paper/simulation (no `_broker_place`,
no Dhan API calls). Options signals are not affected by EB001/EB002 fix.

### 1.2 Coverage result

```
TOTAL_EXECUTABLE_SYMBOLS:  40
MAPPED_SYMBOLS:            38
UNMAPPED_SYMBOLS:           2   ← NIFTYBEES, BANKBEES
```

### 1.3 Unmapped symbols

| Symbol | Source | Why unmapped | Production risk |
|---|---|---|---|
| `NIFTYBEES` | `ArbitrageAI.ETF_DATA` | ETF fund, no NSE equity ID in DHAN_SECURITY_MAP | ETF arb signal would be blocked at `_broker_place` with `[MISSING_DHAN_MAPPING]`. Retried 3× and discarded. |
| `BANKBEES` | `ArbitrageAI.ETF_DATA` | ETF fund, same | Same as NIFTYBEES |

**Post-fix behavior:** Both NIFTYBEES and BANKBEES reach DecisionEngine (confidence=7.5–8.0,
above 6.5 threshold), pass `risk_control`, and reach `order_manager.execute()`. With
the EB002 fix in place, `_broker_place()` performs the DHAN_SECURITY_MAP lookup, finds
no entry, logs `[MISSING_DHAN_MAPPING]`, and returns `None`. The signal is discarded after
3 retries. **No orphaned position, no unprotected capital. Fail-safe.**

**Pre-fix behavior:** same result — both symbols triggered `TypeError` from wrong kwarg
names → silently discarded. Net effect identical (zero positions created).

**BHEL / PNB status confirmed:**
- Neither is in `_BASE_WATCHLIST` or `_EXTENDED_WATCHLIST` — not part of the
  scanner universe. They cannot currently reach `execute()`.
- Absence from DHAN_SECURITY_MAP is intentional and correct.

### 1.4 Authoritative mapping source

`DHAN_SECURITY_MAP` in `data_feeds/dhan_feed.py` is the **only authoritative
runtime source**. It is:
- Cross-validated against `security_id_list.csv` (Dhan instrument master)
- Version-controlled in the repository
- Used by both the data feed layer (`DhanFeed._lookup()`) and the execution layer
  (`_broker_place()`) post-fix

`security_id_list.csv` (workspace root) is a reference artifact — it is NOT
imported at runtime. Do not use it as the runtime source.

### 1.5 NIFTYBEES / BANKBEES authoritative IDs

If ETF arb is to be enabled, the authoritative IDs must come from querying the
DhanHQ API or searching `security_id_list.csv`:

| Symbol | Search result in CSV |
|---|---|
| NIFTYBEES | `SEM_CUSTOM_SYMBOL=NIFTYBEES, SEM_SMST_SECURITY_ID=<lookup required>` |
| BANKBEES | `SEM_CUSTOM_SYMBOL=BANKBEES, SEM_SMST_SECURITY_ID=<lookup required>` |

These IDs should be added to `DHAN_SECURITY_MAP` only when ETF arb is re-enabled
with live prices (currently all ETF_DATA is hardcoded static values).

---

## 2. SOFTWARE STOP-LOSS LIFECYCLE — COMPLETE TRACE

```
OrderManager.execute()
  ├── Guard stack (10 guards pass)
  ├── _place_entry_with_retry()
  │     └── _broker_place()  ← EB001+EB002 fix applied
  │           └── DhanBroker.place_order(security_id, exchange_segment, ...)
  │                 └── returns order_id (e.g. "SIM_DHAN_2885_BUY" in sim)
  ├── OrderRecord created:
  │     stop_loss = sig.stop_loss          ← software SL anchor
  │     sl_order_id = ""                  ← DhanBroker has no place_sl_order
  │     status = "open"
  └── returns OrderRecord

MasterOrchestrator._run_full_cycle() / debate loop (line 2705):
  └── self.trade_monitor.register(order)  ← IMMEDIATE on entry success

TradeMonitor.register(order):
  ├── _open_orders[order_id] = order
  ├── _peak_r[order_id] = 0.0
  ├── _ltp_history[order_id] = [entry_price]
  └── _last_good_ltp[order_id] = entry_price

Monitoring loop — every 5 min (scheduler: sched_lib.every(5).minutes):
  └── MasterOrchestrator._five_min_tasks()
        └── monitor_open_positions() → task_queue.submit_to("TradeMonitor")
              └── _do_monitor()
                    ├── Get live prices via MarketDataRouter
                    └── trade_monitor.check_all(live_prices, degraded_symbols)
                          ├── FEED_DEGRADED guard (skip if symbol has no feed)
                          ├── PriceIntegrity gate (SL_SUPPRESSED if price invalid)
                          ├── Paper LIMIT fill simulation (skip until zone_price crossed)
                          ├── _evaluate(order, ltp)
                          │     └── if ltp <= order.stop_loss (long):
                          │           return "close_sl"
                          └── _act(oid, order, ltp, "close_sl")
                                └── order_manager.close_position(oid, ltp, reason="STOP_LOSS")
                                      └── _broker_place(symbol, "SELL", qty, ltp, order_type="MARKET")
                                            ├── DHAN_SECURITY_MAP lookup  ← EB002 fix
                                            └── DhanBroker.place_order(
                                                    security_id=...,
                                                    exchange_segment=...,
                                                    transaction_type="SELL",
                                                    order_type="MARKET"
                                                )
```

**Key fact:** `_act()` calls `order_manager.close_position(oid, ltp, reason=canonical_reason)`.
`close_position()` calls `_broker_place()`. The EB001+EB002 fix applies to the close
path as well as the entry path. One fix covers both.

---

## 3. SL STARTUP LATENCY

```
Entry order placed (trade_monitor.register() called immediately after execute())
       ↓
Position is registered in _open_orders — software SL is ACTIVE from this moment
       ↓
Maximum wait until first SL evaluation: 5 minutes
(sched_lib.every(5).minutes.do(_five_min_tasks) — market hours only)
       ↓
check_all() → _evaluate() → _act() → close_position() → _broker_place(MARKET)
```

**Maximum SL startup latency: 5 minutes (one monitoring cycle)**

The SL protection itself activates on `register()` — but the first price check
(which would fire a close) only occurs at the next 5-minute cycle.

**Worst case:** entry placed at T+0, next monitoring cycle fires at T+5 minutes.
During that 5-minute window, if price moves through the stop-loss, no automatic
close fires until T+5. After T+5 it fires on every subsequent cycle.

**This is the existing production schedule. No code defines a shorter interval.**
If a tighter SL guarantee is needed, the scheduler interval must be reduced.
This change is NOT part of the current fix scope.

---

## 4. RESTART SAFETY

### 4.1 Recovery path

```
Container restart
  ↓
MasterOrchestrator.__init__()
  ├── OrderManager()
  │     └── _restore_from_journal()
  │           └── reads data/paper_trades.csv
  │                 ├── finds OPEN rows with SIM_* or real order_ids
  │                 ├── creates OrderRecord for each
  │                 └── adds to _orders{}
  ├── TradeMonitor()
  ├── order_manager.inject_trade_monitor(trade_monitor)
  ├── trade_monitor.inject_order_manager(order_manager)
  ├── for _carry in order_manager.get_open_orders():
  │     └── trade_monitor.register(_carry)   ← positions re-registered for SL monitoring
  └── _post_restore_governance_pass()
        ├── fetch live prices via MarketDataRouter
        ├── trade_monitor.check_all(live_prices)   ← IMMEDIATE SL check on restart
        ├── plausibility check (>50% deviation from entry → RECONCILIATION_SUSPECT alert)
        └── check_and_expire_carries()   ← expire carry positions past EOD cutoff
```

### 4.2 What is recovered

| Data | Persisted? | Recovery mechanism |
|---|---|---|
| OrderRecord (symbol, direction, qty, entry, SL, target) | ✅ `data/paper_trades.csv` (append-only) | `_restore_from_journal()` reads OPEN rows |
| sl_order_id | ✅ CSV column | Restored from CSV (value is `""` for Dhan) |
| stop_loss | ✅ CSV column | Restored verbatim |
| TradeMonitor registration | ❌ in-memory only | Re-registered from restored OrderRecord on startup |
| _peak_r, _ltp_history | ❌ in-memory only | Reset to defaults; adaptive exits may differ slightly from pre-restart state |
| Last good LTP | ❌ in-memory only | Seeded from `entry_price` on register(); first check_all() brings it current |

### 4.3 Restart safety verdict

**SAFE.** After restart, `_restore_from_journal()` recovers all open positions from
the persistent CSV. They are immediately re-registered with TradeMonitor. A
`_post_restore_governance_pass()` fires an immediate `check_all()` before the
5-minute scheduler begins. If price crossed the stop-loss during the restart window,
the first post-restore check fires the close.

**Monitoring gap risk:** If the container restarts while the market is open, the
gap between the last `check_all()` before crash and the first `check_all()` after
restart is bounded by the monitoring blackout detection (`_gap_sec > 10 min` →
`[MonitoringGap]` alert, but no automatic close). The governance pass mitigates
this by running `check_all()` immediately on startup.

---

## 5. TRADEMONITOR FAILURE SCENARIOS

### 5A. TradeMonitor task crashes

**Detection:** `_do_monitor()` is submitted to `TaskQueue("TradeMonitor")`. An
unhandled exception in `_do_monitor()` is caught by the task queue worker. A
`[Monitor] check_all error:` warning is logged.  

**`_check_all_ok`** flag is set to `False` only when `check_all()` raises. Normal
exception in one cycle does NOT crash the scheduler.  

**Consequence:** For that 5-minute cycle, SL is not evaluated. Next cycle will run.  
**Failure mode:** NOT detected in isolation; no automatic recovery action beyond logging.  
**Alert:** `[Monitor] check_all error:` in log only. No Telegram alert for a single-cycle failure.  
**Unprotected position:** Yes, for one cycle (up to 5 minutes). Recovers automatically next cycle.

### 5B. TradeMonitor becomes delayed

**Detection:** `_MONITOR_INTERVAL_SEC = 300`. A gap exceeding `2 × 300 = 600s`
(10 min) triggers `[MonitoringGap]` log warning.  
If gap > 10 min and positions are open during market hours → Telegram alert sent.  
**Consequence:** Positions are unmonitored during gap. SL fires on next successful cycle.

### 5C. Price feed becomes stale

**Detection:** `check_all()` receives `degraded_symbols` from `MarketDataRouter`.
If a symbol is in `degraded_symbols`, the `FEED_DEGRADED` guard **suppresses all
SL/adaptive evaluation** for that symbol for that cycle. `[TradeMonitor] FEED_DEGRADED`
is logged.  
`DataGuard` detects price unchanged for `_DATAGAURD_STALE_CYCLES = 6` consecutive
cycles → `[DataGuard] Stale price detected` warning.  
The `SL Integrity Gate` also validates price via `PriceIntegrityValidator`. If price
fails validation → `[ExecutionIntegrity] SL_SUPPRESSED` logged; SL not fired.  
**Failure mode:** Stale price detection is defensive — SL is suppressed (position stays open)
rather than firing a false close. Correct behavior for a stale feed.

### 5D. Container restart

See Section 4. Position recovered and immediately monitored.

### 5E. Dhan feed temporarily unavailable

**Detection:** `MarketDataRouter` falls back to Yahoo/cache. If all sources fail →
symbol is added to `degraded_symbols` → `FEED_DEGRADED` guard suppresses SL for
that cycle.  
**Consequence:** Same as 5C. SL suppressed (conservative). Position remains open.
On next cycle, if feed recovers, monitoring resumes.  
**Unprotected position:** No — position is monitored but SL is not triggered without
a valid price. Manual override possible via Telegram `/positions` command.

---

## 6. CLOSE PATH VERIFICATION (broker-spy)

Close path confirmed by `test_execution_boundary_002.py::test_F` and `test_G` (run with mock broker):

```
TradeMonitor._act("close_sl")
  └── order_manager.close_position(oid, ltp, reason="STOP_LOSS")
        └── _broker_place(symbol="RELIANCE", direction="SELL", qty=1,
                          price=ltp, order_type="MARKET")
              ├── DHAN_SECURITY_MAP lookup: "RELIANCE" → security_id="2885", segment="NSE_EQ"
              └── DhanBroker.place_order(
                      security_id="2885",
                      exchange_segment="NSE_EQ",
                      transaction_type="SELL",
                      quantity=1,
                      price=<ltp>,
                      order_type="MARKET"
                  )
```

**Exactly one close request.** Entry: 1 broker call (test_F). Retry scenario: 3 max (test_J).  
Both tested with mock broker spy — `_REAL_DHAN_WRITE_CALLED` sentinel confirms real
API never reached.

---

## 7. TEST RESULTS

### 7.1 Execution boundary tests (fresh process — no stub contamination)

| Suite | Tests | Result |
|---|---|---|
| `test_execution_boundary_001.py` | 15 | ✅ 15/15 PASS |
| `test_execution_boundary_002.py` | 16 | ✅ 16/16 PASS |

### 7.2 Regression suites (fresh process)

| Suite | Tests | Result |
|---|---|---|
| `tests/test_frz001_journal.py` | 8 | ✅ 8/8 PASS |
| `tests/test_frz001_dhan_probe.py` | 13 | ✅ 13/13 PASS |
| `tests/test_cle.py` | 34 | ✅ 34/34 PASS |
| `tests/test_governance_window.py` | 22 | ✅ 21/22 PASS — 1 pre-existing failure |
| `tests/test_orj001.py` | 11 | ✅ 11/11 PASS |

**Pre-existing failure:** `test_0910_logs_execution_window_block` — confirmed pre-existing
via `git stash` + baseline run (fails identically without EB001/EB002 fix).

### 7.3 Combined-session note

Running all test files in a single `pytest` invocation causes 26 failures
(boundary tests affected by `sys.modules` stubs from FRZ/CLE/governance tests).  
Root cause: stub-heavy test files register fake modules globally without cleanup.  
This is a pre-existing infrastructure limitation of the test suite — not caused
by the EB001/EB002 fix.  
**Both groups pass cleanly in separate invocations (confirmed above).**

### 7.4 No dedicated TradeMonitor or DhanBroker test files found

`grep tests/ -r "trade_monitor"` — no matching test file discovered.
TradeMonitor behavior is verified via:
- `test_execution_boundary_002.py::test_F` (SL architecture)
- `test_execution_boundary_002.py::test_G` (entry + SL-None)
- `test_execution_boundary_002.py::test_J` (close path retries)

---

## 8. FINAL DEPLOYMENT CLASSIFICATION

### Verdict: **MAPPING_BLOCKED**

**Condition:** `NIFTYBEES` and `BANKBEES` (symbols from `ArbitrageAI.ETF_DATA`) can
reach `OrderManager.execute()` during a full production cycle and have no entry in
`DHAN_SECURITY_MAP`. With the EB002 fix, both are blocked at the mapping layer with
`[MISSING_DHAN_MAPPING]` — no capital at risk, no unprotected positions.

**However**, the task definition requires:

> READY_FOR_DEPLOYMENT — only if every executable symbol has an authoritative mapping

NIFTYBEES and BANKBEES are executable symbols (they pass DecisionEngine) but lack
authoritative Dhan mappings. Until either:
a) Their Dhan `security_id` values are added to `DHAN_SECURITY_MAP`, or  
b) `ArbitrageAI._etf_nav_arb()` is explicitly disabled (as `_futures_basis_arb()` is)

the coverage gap exists.

**All other conditions are met:**

| Condition | Status |
|---|---|
| Entry path correct (EB001 + EB002 fix) | ✅ VERIFIED — security_id, exchange_segment, correct kwargs |
| Close path correct (same _broker_place) | ✅ VERIFIED — broker-spy test_F, test_G |
| 38 scanner symbols mapped | ✅ VERIFIED — 38/38 in DHAN_SECURITY_MAP |
| Symbol stripping (trailing spaces) | ✅ VERIFIED — _live_watchlist() strips at line 1255 |
| Software SL lifecycle understood | ✅ VERIFIED — TradeMonitor.register() immediate, check_all() ≤5 min |
| SL startup latency documented | ✅ ≤5 minutes (one monitoring cycle) |
| Restart safety | ✅ SAFE — _restore_from_journal() + re-register + _post_restore_governance_pass() |
| TradeMonitor failure behavior | ✅ DOCUMENTED — degraded feed suppresses SL (conservative); crashes recover next cycle |
| All relevant regression tests pass | ✅ in separate invocations |
| Real Dhan orders | ✅ 0 |
| VPS deployment | ✅ 0 |

---

## 9. RESOLUTION PATH TO READY_FOR_DEPLOYMENT

**Option A (recommended):** Disable ETF arb path until live price data is integrated  
Add to `arbitrage_ai.py`:
```python
_ETF_ARB_DISABLED: bool = True   # static prices not refreshed; no real arb
```
And in `_etf_nav_arb()`: `if _ETF_ARB_DISABLED: return []`.  
Then TOTAL_EXECUTABLE_SYMBOLS = 38, all mapped. Classification → `READY_FOR_DEPLOYMENT`.

**Option B:** Add NIFTYBEES and BANKBEES to DHAN_SECURITY_MAP with IDs from
`security_id_list.csv` (cross-validated).  
Then all 40 symbols are mapped. Classification → `READY_FOR_DEPLOYMENT`.

**Do not implement either option without explicit user instruction.**

---

## 10. REMAINING KNOWN RISKS (post-deployment)

1. **stop_loss=0.0 gap:** execute() does not validate stop_loss > 0. A signal with
   stop_loss=0 creates an effectively unprotected position (TradeMonitor never fires
   close_sl for positive LTP). DecisionEngine upstream should prevent this.
   Pre-existing gap, not introduced by EB001/EB002.

2. **SL startup window:** Up to 5 minutes between entry and first SL price check.
   During this window, price can exceed the stop-loss without automatic close.

3. **TradeMonitor must be running:** Software SL depends on the monitoring loop.
   If TaskQueue("TradeMonitor") is starved or the worker thread crashes silently,
   positions are unmonitored. Detected only via [MonitoringGap] log after 10+ min gap.

4. **LIMIT fill simulation:** In paper mode, `_broker_place()` returns a SIM_* order_id
   immediately. TradeMonitor waits for LTP to cross `zone_price` before evaluating
   SL/target. Until fill is confirmed, the position shows LIMIT_PENDING. This is
   intentional behavior, not a gap.
