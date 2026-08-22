# OPS-03A Dataset Remediation Record

**Date:** 2026-06-16  
**Status:** Applied ✅  
**Test Result:** 182 / 182 passed — zero regressions

---

## Problem Statement

The production learning dataset contained two structural defects that made
Win Rate, Expectancy, Profit Factor, and Sharpe impossible to compute:

### Defect 1 — CSV Schema Mismatch

| Item | Value |
|---|---|
| File | `data/paper_trades.csv` |
| Header columns written | **12** (`timestamp … event`) |
| CLOSE row columns written | **15** (adds `exit_price`, `pnl`, `reason`) |
| Effect | `csv.DictReader` sees only the 12 header fields; `exit_price`, `pnl`, `reason` are silently dropped — reason reads as `""` for every close row |
| Outcome | EOD learning reads `reason = ""` → no close event matches any outcome category → Win Rate = 0, Expectancy = undefined |

Root cause: the CSV was first created by a version of the code before `exit_price`,
`pnl`, and `reason` were added to `_JOURNAL_HEADER`. Once a file exists the header
is never rewritten, so all subsequent close rows had three extra columns with no
matching header field.

### Defect 2 — Startup Contamination

| Item | Value |
|---|---|
| Trigger path | `close_all_positions()` → `reason="emergency_close"` |
| When it fires pre-monitoring | SYSTEM_HALT event before first `check_all()` cycle; or drawdown check on stale portfolio |
| Effect | Restored positions closed at `entry_price` (no live LTP yet) — zero-PnL records written to journal |
| Dataset impact | Even if schema is correct, these zero-PnL records pollute the outcome distribution used by Phase D learning |

The `has_live_ltp` flag (set by the `_do_monitor` LTP sync) is the canonical
signal that a position has been through at least one live monitoring cycle.
Before `_do_monitor` first runs, `has_live_ltp = False` for all restored positions.

---

## Changes Applied

### Fix 1 — Archive and Reset Journal

```
data/paper_trades.csv        →  data/paper_trades_legacy.csv  (234 data rows, 12-col header)
data/paper_trades.csv (new)  →  fresh file, 15-col header, 0 data rows
```

New header (15 columns):

```
timestamp, order_id, symbol, direction, quantity, entry_price,
stop_loss, target, strategy, confidence, rr, event,
exit_price, pnl, reason
```

Legacy file is preserved read-only. No rows were modified or deleted.

### Fix 2 — Distinguish Pre-Monitoring Closes

**File:** `execution_engine/order_manager.py`  
**Function:** `close_all_positions()`

```python
# BEFORE
self.close_position(oid, _exit_px, reason="emergency_close")

# AFTER
_was_monitored = _pos is not None and getattr(_pos, "has_live_ltp", False)
_close_reason  = "emergency_close" if _was_monitored else "ORPHAN_CLOSE"
self.close_position(oid, _exit_px, reason=_close_reason)
```

**Behaviour change:**

| Condition | Previous reason | New reason |
|---|---|---|
| Position has `has_live_ltp = True` (saw at least one monitoring cycle) | `emergency_close` | `emergency_close` (unchanged) |
| Position has `has_live_ltp = False` (never monitored this session) | `emergency_close` | **`ORPHAN_CLOSE`** |

`ORPHAN_CLOSE` exits are still written to the journal (for auditability) but are
excluded from the learning dataset by the EOD skip list.

### Fix 3 — Add ORPHAN_CLOSE to EOD Learning Skip List

**File:** `orchestrator/master_orchestrator.py`  
**Function:** `_do_eod_learning()`, `_skip_reasons` set

```python
# ADDED
"ORPHAN_CLOSE",   # closed before first monitoring cycle (never had live LTP)
```

Complete skip list after fix:

| Reason | Excluded | Why |
|---|---|---|
| `emergency_close` | ✅ | System halt; exit at entry_price (synthetic) |
| `close_emergency` | ✅ | TradeMonitor MAE intervention |
| `ORPHAN_CLOSE` | ✅ NEW | Pre-monitoring close; exit at entry_price |
| `REPLACEMENT` | ✅ | Smart-swap leg; not a standalone outcome |
| `SYSTEM_CLEANUP` | ✅ | Manual data-repair tool |
| `SESSION_EXPIRED` + `pnl=0` | ✅ | No real LTP at expiry |
| `SESSION_EXPIRED` + `pnl≠0` | ✅ INCLUDED | Real LTP fetched; genuine carry outcome |
| `close_sl` | ✅ INCLUDED | Stop-loss hit at live price |
| `close_target` | ✅ INCLUDED | Target hit at live price |
| `adaptive_exit` | ✅ INCLUDED | TIME_STALE / EARLY_LOSS at live price |

---

## What Was Not Changed

| Component | Status |
|---|---|
| `_JOURNAL_HEADER` in `order_manager.py` | Unchanged — already 15 columns |
| All other `close_position()` call sites | Unchanged |
| `_do_monitor()` / `check_all()` logic | Unchanged |
| Carry expiry (`SESSION_EXPIRED`) | Unchanged |
| `_restore_from_journal()` | Unchanged |
| All test files | Unchanged |
| Legacy data in `paper_trades_legacy.csv` | Read-only archive, not modified |

---

## Test Results

```
platform win32 — Python 3.14.3, pytest-9.0.2
collected 182 items

tests/oios/           — 168 passed
tests/test_candidate_contract.py — 14 passed

===================== 182 passed in 0.67s =====================
```

---

## Expected Data for Learning Dataset (Going Forward)

For the Phase D learning pipeline to compute valid metrics, the following close
reason categories must appear in `data/paper_trades.csv`:

| Metric | Requires |
|---|---|
| Win Rate | `close_target`, `close_sl`, `adaptive_exit`, `SESSION_EXPIRED` (pnl≠0) |
| Expectancy | All of the above; `pnl` column must be non-zero |
| Profit Factor | Positive `pnl` (wins) + negative `pnl` (losses) |
| Sharpe | Sequence of per-trade returns over time |
| Phase D Learning | Minimum ~50 natural exits across at least 2 regimes |

With the schema fixed (15-col header), `csv.DictReader` will correctly read
`exit_price`, `pnl`, and `reason` from every close row. The first natural exit
that occurs (stop hit, target hit, or adaptive exit during a live monitoring
session) will produce a valid learning record.

---

## Rollback Procedure

### Rollback Fix 1 (journal archive)

```powershell
# Restore legacy journal (discards any new clean data)
Copy-Item data\paper_trades_legacy.csv data\paper_trades.csv -Force
```

### Rollback Fix 2 (order_manager.py)

```python
# Revert close_all_positions() — replace the two new lines with:
self.close_position(oid, _exit_px, reason="emergency_close")
```

### Rollback Fix 3 (master_orchestrator.py)

Remove `"ORPHAN_CLOSE"` from `_skip_reasons` in `_do_eod_learning()`.
