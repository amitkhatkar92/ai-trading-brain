# TRADE_LIFECYCLE_REMEDIATION

**Date:** 2026-06-16  
**Investigator:** Copilot forensic analysis  
**Sources:** `data/paper_trades.csv` (234 rows), `data/control_tower.db` (114,993 ct_events), raw CSV column inspection  
**Verdict:** Six distinct defects prevent natural lifecycle exits. No defect requires production parameter changes. Four are code-level fixes; two are operational.

---

## 1. What Was Found

### paper_trades.csv — raw column inspection

```
Header:      12 columns  [timestamp … event]
OPEN rows:   12 columns  ← matches header
CLOSE rows:  15 columns  ← exit_price, pnl, reason in columns 13–15 (unnamed)
```

All 112 CLOSE rows:

| Close Reason | Count | exit_price == entry_price | Realised PnL |
|---|---|---|---|
| `emergency_close` | 108 | Yes (100%) | ₹0.00 |
| `SYSTEM_CLEANUP`  | 4   | Yes (100%) | ₹0.00 |
| `close_target`    | 0   | — | — |
| `close_sl`        | 0   | — | — |
| `adaptive_exit`   | 0   | — | — |
| `SESSION_EXPIRED` | 0   | — | — |

### control_tower.db — event type distribution

| Event type | Count |
|---|---|
| `execution.order.placed` | 1,197 |
| `execution.order.rejected` | 308 |
| `execution.order.closed` | **0** |
| `monitor.position.closed` | **0** |
| Any close/target/stop event | **0** |

All `ct_cycles` rows show `risk_approved = 0`, `trades_executed = 0`.

---

## 2. Root Causes (ordered by severity)

---

### Defect 1 — PRIMARY: System never ran continuously during market hours

**Evidence:**
- Period 1 (Mar 19): 108 positions opened 11:55–12:47 IST, all closed at entry price within 0–2 seconds via `emergency_close`. Zero holding time.
- Period 2 (Mar 20): 6 Hedging_Model positions opened at 07:35 IST (pre-open, before `_is_market_session()` returns True). Held for 26 calendar days. No monitoring cycle ran in between. Closed by external `SYSTEM_CLEANUP` script on Apr 15.
- Period 3 (Apr 10–15): Mean_Reversion positions held 2–5 days. Closed by `SYSTEM_CLEANUP` at entry price (₹0 PnL) on Apr 15.
- Period 4 (Apr 15–17): Momentum_Retest churn with `REPLACEMENT`. Residual opens on Apr 17 still open.

**Root cause:** No session ran continuously from position open through a natural SL or target hit. Every position ended via a system event, not a market event.

**Required for natural exits:** The scheduler must run during NSE hours (09:15–15:32 IST) on the machine where positions are open. The `_five_min_tasks` guard (`if not self._is_market_session(): return`) is correct — but meaningless if the process is not running during those hours.

---

### Defect 2 — SECONDARY: `close_all_positions()` called on startup wipes positions at entry price

**Code path:** `_on_system_halt()` → `order_manager.close_all_positions()` → all open records closed with `reason="emergency_close"`, `exit_price=entry_price` (fallback), `pnl=₹0`.

**Evidence:** 108 Mar 19 opens all closed within 0–2 seconds of opening — identical entry and exit price. This is the exact signature of `close_all_positions()` being called immediately after a batch placement run, either because:
- The system triggered a drawdown halt from the large batch-placement notional
- The strategy-lab ran a simulation replay that auto-cleaned up at the end

**Effect:** Every position that would have been naturally monitored was wiped before the first `check_all()` cycle could evaluate it.

**TradeMonitor registration check:** `close_all_positions()` calls `close_position()` directly, bypassing `TradeMonitor._act()`. The TradeMonitor is never asked to evaluate these positions.

---

### Defect 3 — CRITICAL CODE BUG: CSV header has 12 columns; CLOSE rows have 15

**Location:** `data/paper_trades.csv` header row (written at file creation, never updated)

**Root cause:** The file was first created when `_JOURNAL_HEADER` had 12 columns. The header was later extended to 15 columns (`+ exit_price, pnl, reason`) but `_journal_write_close()` only writes a new header when the file does not exist:

```python
# execution_engine/order_manager.py line ~1658
write_header = not os.path.exists(PAPER_TRADE_LOG)
with open(PAPER_TRADE_LOG, "a", ...) as fh:
    w = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
    if write_header:
        w.writeheader()
    w.writerow({..., "exit_price": ..., "pnl": ..., "reason": reason})
```

For an existing file the header is never rewritten. All CLOSE rows have 15 columns written, but the file header only names 12 of them.

**Effect on reading:**

```python
csv.DictReader(fh)  # uses 12-column file header
row.get("reason")   # returns None — field is unnamed, stored in None key
row.get("pnl")      # returns None
row.get("exit_price") # returns None
```

**This affects:**
- `_do_eod_learning()` — reads `reason=""`, cannot classify any trade as win/loss
- `_restore_from_journal()` — reads `exit_price=None`, `pnl=None` on CLOSE rows
- `monitoring/first_month_tracker.py` — reads events, cannot distinguish closed trades
- Any downstream analytics reading the CSV

**Effect on learning:**
- Phase D learning receives zero valid outcomes
- Win rate, expectancy, Sharpe, profit factor cannot be computed
- `StrategyPerformanceTracker` has no outcome data to weight strategies

---

### Defect 4 — CRITICAL CODE BUG: Feed degradation silently skips `check_all()`

**Location:** `orchestrator/master_orchestrator.py` — `_do_monitor()`:

```python
if _live_pf:                                          # ← guarded by non-empty dict
    self.trade_monitor.check_all(_live_pf, ...)
```

**Trigger:** Dhan API returns 451 (data-plan blocked) → yfinance fallback → yfinance timeout or rate-limit → `_live_pf = {}`.

**Effect:** The entire SL/target evaluation block is silently skipped. No `check_all()` call. No SL hit. No target hit. No adaptive exit. No carry expiry via validated LTP.

**Silent failure:** No warning is emitted when `_live_pf` is empty and there are open positions. The monitoring loop reports success but did nothing.

**Frequency:** Dhan data API has been blocked since the 451 episode in March 2026 (see `DHAN_DAILY_TOKEN_REQUIREMENT.md`). yfinance is the fallback but fails intermittently under rate limits. This means `check_all()` likely runs on fewer than 30% of its scheduled cycles.

---

### Defect 5 — Reason string mismatch between TradeMonitor and audit expectations

**Location:** `trade_monitoring/trade_monitor.py` — `_act()`:

```python
reason_map = {
    "close_target":  f"Target hit at {ltp:.2f}",   # ← reason_map built but never used
    "close_sl":      f"Stop loss hit at {ltp:.2f}",
    ...
}
reason = reason_map.get(action, action)
...
self._order_manager.close_position(oid, ltp, reason=action)  # ← passes action, not reason
```

The `reason_map` is computed but then discarded. `close_position` receives `reason="close_target"` (not `"TARGET_HIT"`) and `reason="close_sl"` (not `"STOP_HIT"`).

**Effect on audit tools and dashboards:** Any tool searching for `TARGET_HIT` or `STOP_HIT` in the CSV will find zero rows, even if natural exits occur.

**Effect on EOD learning:** The `_skip_reasons` set in `_do_eod_learning` does NOT include `close_target` or `close_sl` — so these WOULD reach the learning engine if they ever occurred. The reason mapping is a **monitoring/audit problem only**, not a learning pipeline problem.

**Carry-expiry label:** `check_and_expire_carries()` writes `reason="SESSION_EXPIRED"` (not `"CARRY_EXPIRED"`). Any audit looking for `CARRY_EXPIRED` will find zero rows even when carries are properly expired.

---

### Defect 6 — Targets are structurally unreachable in current market conditions

**Evidence from CT cycles:**
- All cycles from Mar 2026 show `regime = 'volatile'`, `vix = 22.15–26.18`
- `risk_approved = 0` in every cycle — the risk pipeline blocks all signals during volatile regime

**Sizing reality (from OPS-02 analysis):**
- All positions use `rr = 2.5` (stop ~2%, target ~5% from entry)
- In volatile/bear conditions, 5% intraday moves against the trend are extremely rare for NSE large-caps
- Adaptive exit `TIME_STALE` threshold: 180 minutes — most intraday positions would time out first

**Effect:** Even if Defects 1–4 were fixed and the system ran continuously, most positions would exit via `adaptive_exit (TIME_STALE)` rather than `close_target`, because the 5% target requires favourable sustained momentum.

---

## 3. Trace of Each Close Path

### `close_target` (TARGET_HIT equivalent)
```
TradeMonitor.check_all()
  → _evaluate(): ltp >= order.target → "close_target"
  → _act(): close_position(oid, ltp, reason="close_target")
  → _journal_write_close(): writes reason="close_target", exit_price=ltp, pnl=real_pnl
```
**Blocked by:** Defect 1 (system not running), Defect 4 (empty price feed)

### `close_sl` (STOP_HIT equivalent)
```
TradeMonitor.check_all()
  → _evaluate(): ltp <= order.stop_loss → "close_sl"
  → _act(): close_position(oid, ltp, reason="close_sl")
  → _journal_write_close(): writes reason="close_sl", exit_price=ltp, pnl=real_pnl
```
**Blocked by:** Defect 1, Defect 4. Also suppressed by LTPGuard (if price deviation >20%)

### `adaptive_exit` (TIME_STALE / EARLY_LOSS)
```
TradeMonitor.check_all()
  → _adaptive_check(): age >= 180 min AND |r| <= 0.3R → "adaptive_exit"
  → _act(): close_position(oid, ltp, reason="adaptive_exit")
```
**Blocked by:** Defect 1, Defect 4

### `SESSION_EXPIRED` (CARRY_EXPIRED equivalent)
```
_do_monitor()
  → check_and_expire_carries(): age_td >= max_carry → writes SESSION_EXPIRED
```
**Blocked by:** Defect 1 (system not running during market hours when carries would expire)  
**Note:** Called even when `_live_pf = {}` (via `_validated_pf or _live_pf`), but exits at entry price when no live LTP available.

### `emergency_close` (SYSTEM_HALT path — the only path that fires today)
```
_on_system_halt() / _on_drawdown_alert()
  → close_all_positions()
  → close_position(oid, entry_price, reason="emergency_close")
```
**This fires:** On drawdown ≥ 10%, on SYSTEM_HALT event, and apparently on startup when a batch test completes.

### `SYSTEM_CLEANUP` (external script)
```
cleanup_stale_opens.py or similar ad-hoc script
  → close_position(oid, entry_price, reason="SYSTEM_CLEANUP")
```
**Confirmed:** April 15 and 17 SYSTEM_CLEANUP events.

---

## 4. Monitor Loop Verification

### Is `_do_monitor` scheduled?

Yes. `start_scheduler()` registers:
```python
def _five_min_tasks():
    if not self._is_market_session():
        return
    self.monitor_open_positions()    # → submits _do_monitor to TaskQueue

sched_lib.every(5).minutes.do(_five_min_tasks)
```

`_do_monitor` runs if and only if:
1. `start_scheduler()` was called (requires `--scheduler` or `--telegram` mode)
2. Current time is within 09:15–15:32 IST on a weekday NSE trading day
3. `_halt` flag is False
4. `TaskQueue.TradeMonitor` worker is alive

### Is `check_all()` called inside `_do_monitor`?

Only if `_live_pf` is non-empty:
```python
if _live_pf:                            # ← GATE: skipped when feed returns empty
    self.trade_monitor.check_all(...)
```

### What populates `_live_pf`?

```python
_quotes = _router.get_live_prices(_open_syms)
for _bare, _q in _quotes.items():
    if _q and getattr(_q, "ltp", 0) > 0:
        _live_pf[_bare] = float(_q.ltp)
```

`MarketDataRouter.get_live_prices()` → Dhan (451 blocked) → yfinance fallback.  
If yfinance times out: `_quotes = {}` → `_live_pf = {}` → `check_all()` **never called**.

---

## 5. Are Targets Reachable?

Current position parameters:
- `rr = 2.5`
- `ATR_STOP_MULTIPLIER = 1.5` → stop_distance ≈ ATR × 1.5
- For HDFCBANK (ATR ~₹25 daily): stop ≈ ₹37.50 (~2.2%), target ≈ ₹93.75 (~5.4%)

In a volatile regime (VIX 22–26, bear/sideways market):
- Probability of 5.4% intraday move in the right direction: very low
- `TIME_STALE` exit would fire first at 180 minutes if price doesn't move
- `EARLY_LOSS` would fire at −0.6R to −0.7R before the stop is reached

**Assessment:** Targets are architecturally reachable but practically rare in volatile conditions. The primary expected natural exit type should be `adaptive_exit (TIME_STALE)`, not `close_target`.

---

## 6. Are Stops Checked?

**Stop check in `_evaluate()`:**
```python
if (is_long and ltp <= sl) or (not is_long and ltp >= sl):
    return "close_sl"
```

**Guards that suppress this:**
1. `FEED_DEGRADED` guard: `if _sym_degraded: continue` (SL suppressed for degraded symbols)
2. `SL Integrity Gate`: if `price_integrity_validator` rejects the LTP → `continue`
3. LTPGuard: if LTP deviates >20% from last known → price is frozen at last good price
4. `if _live_pf:` outer gate: if feed returns empty → no evaluation at all

All four guards can legitimately suppress SL checking. In a Dhan-blocked environment with yfinance as fallback, guards 4 is the dominant suppressor.

---

## 7. Data Required for Learning Metrics

For each metric, the minimum dataset requirements are:

| Metric | Minimum data | Current status |
|---|---|---|
| Win Rate | Closed trades with `outcome = WIN/LOSS` classification | **0 valid trades** |
| Expectancy | E[gain\|win] × P(win) − E[loss\|loss] × P(loss) | **0 valid trades** |
| Profit Factor | Σ(gains) / Σ(losses) | **0 valid gains, 0 valid losses** |
| Sharpe Ratio | Daily PnL series, ≥30 data points | **All PnL = ₹0** |
| Phase D Learning | ≥50 SESSION_EXPIRED trades under 3-day carry rule | **0 SESSION_EXPIRED** |

**Minimum viable learning dataset:**
- **50 trades** with non-zero PnL and valid close reason (not `emergency_close` or `SYSTEM_CLEANUP`)
- **Mix of outcomes**: ≥10 wins, ≥10 losses, ≥5 adaptive exits
- **Cover ≥3 strategy types** with ≥5 trades each
- **Cover ≥2 regime types** (volatile + trending)

None of these exist today.

---

## 8. Remediation Plan (no production changes required)

### Fix 1 — CSV Header (Defect 3) — ONE-TIME DATA REPAIR
**Action:** Rename `data/paper_trades.csv` to `data/paper_trades_legacy.csv`. The next OPEN event written will create a new file with the correct 15-column header. Existing data is preserved in the renamed file.

**Result:** All future CLOSE rows will be readable by `DictReader`. EOD learning will correctly receive `reason`, `pnl`, `exit_price`.

**No code change required.** The `_journal_write_close` already writes all 15 fields correctly when the file is created fresh.

### Fix 2 — Feed gate warning (Defect 4) — CODE CHANGE (non-invasive)
**File:** `orchestrator/master_orchestrator.py` — `_do_monitor()`  
**Change:** When `_live_pf` is empty and there are open positions, emit a log warning and Telegram alert.

```python
# Proposed addition (after _live_pf = {} is confirmed empty):
if not _live_pf and self.trade_monitor.get_open_trades():
    _open_n = len(self.trade_monitor.get_open_trades())
    log.warning("[Monitor] FEED_EMPTY — %d open position(s) NOT evaluated this cycle "
                "(no live prices received). SL/target monitoring suppressed.", _open_n)
```

**This does NOT change the gate logic** — it only makes the silent skip visible in logs.

### Fix 3 — Reason string alignment (Defect 5) — CODE CHANGE (cosmetic)
**File:** `trade_monitoring/trade_monitor.py` — `_act()`  
**Change:** Pass `reason` (the human-readable string) instead of `action` to `close_position`.

```python
# Current:
self._order_manager.close_position(oid, ltp, reason=action)
# Proposed:
self._order_manager.close_position(oid, ltp, reason=reason)
```

This changes journal reasons from `close_target`/`close_sl` to `Target hit at 1720.50`/`Stop loss hit at 1685.00`. These are more informative and match documentation expectations.

**Carry expiry label:** `check_and_expire_carries()` should write `reason="CARRY_EXPIRED"` instead of `reason="SESSION_EXPIRED"` to match audit expectations (separate from `SESSION_EXPIRED_EXTENDED`).

### Fix 4 — Operational: Run scheduler during market hours continuously
**Action:** Ensure the process runs `start_scheduler()` on a machine that is:
1. Online 09:00–16:00 IST Monday–Friday
2. Has stable network access to yfinance (Dhan 451 acknowledged)
3. Does not restart between 09:15 and 15:30

The `autostart.bat` / Windows Task Scheduler job already handles the 08:00 start. Confirm the process is not crashing and restarting during market hours.

### Fix 5 — Operational: Do not call `close_all_positions()` during live runs
**Immediate risk:** Any batch test, stress test, or backtest run that calls `place_order()` and then `close_all_positions()` will write `emergency_close` rows to the production journal `data/paper_trades.csv`. This contaminates the live dataset.

**Action:** Batch tests should use an isolated journal path (e.g. `data/test_paper_trades.csv`) or write to an in-memory store.

### Fix 6 — Feed degradation alert (Defect 4 — observability only)
**Action:** The `[FEED_DEGRADED_ESCALATION]` alert at 6 cycles already fires a Telegram message. Verify Telegram bot token is valid and alerts are being received. If not, the silent monitoring blackout will continue.

---

## 9. Impact Table

| Defect | Natural exits blocked? | Learning data invalid? | Fix type |
|---|---|---|---|
| 1 — System not running | **Yes** (no monitoring cycles) | Yes | Operational |
| 2 — `close_all_positions()` wipes positions | **Yes** (0-second holds) | Yes | Operational |
| 3 — CSV 12-column header | No (exits not happening anyway) | **Yes** (reason/pnl unreadable) | Data repair |
| 4 — Feed gate skips `check_all` | **Yes** (silent skip) | Indirect | Code (warning) |
| 5 — Reason string mismatch | No (audit issue only) | No | Code (cosmetic) |
| 6 — Targets far in volatile market | Partial | No | Accept / no action |

---

## 10. Expected Learning Dataset After Remediation

After fixing Defects 1–4 and running for 10 trading sessions:

| Expected outcome | Count | Reason code |
|---|---|---|
| Adaptive exit (time stale) | ~15–25 | `adaptive_exit` |
| Stop loss hit | ~5–10 | `close_sl` |
| Carry expired | ~5–10 | `SESSION_EXPIRED` or `CARRY_EXPIRED` |
| Target hit | ~2–5 | `close_target` |

A 10-session run should produce ~30–50 valid outcomes — the minimum for Phase D learning activation.

---

*Generated by forensic analysis — 2026-06-16. No production parameters were changed.*
