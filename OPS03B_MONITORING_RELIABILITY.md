# OPS-03B Monitoring Reliability

**Date:** 2026-06-16  
**Status:** Applied ✅  
**Test Result:** 182 / 182 passed — zero regressions

---

## Problem

`_do_monitor()` in `orchestrator/master_orchestrator.py` contained a silent skip:

```python
# BEFORE — silent skip with open positions
if _live_pf:
    self.trade_monitor.check_all(...)
# If _live_pf is empty and open positions exist:
# • check_all() never runs
# • carry-expiry never runs
# • no log entry, no alert, no counter
# • SL and target checks silently missed
```

This path is triggered whenever the price feed returns nothing — Dhan 451 error,
yfinance timeout, batch sanity failure, or post-market empty feed. Each missed cycle
means all open positions go without SL/target evaluation for that 5-minute window.

---

## Changes Applied

### File: `orchestrator/master_orchestrator.py`

**1. New counter in `__init__`:**

```python
# Counts cycles where open positions existed but the price feed was empty.
# Incremented in _do_monitor; reset to 0 on any successful check_all().
self._missed_monitor_cycles: int = 0
```

**2. Detection block inserted between `_live_pf.update(_options_fixed)` and `if _live_pf:`:**

```python
# ── Empty-feed guard ──────────────────────────────────────────────────
_open_trades = self.trade_monitor.get_open_trades()
if not _live_pf and _open_trades:
    self._missed_monitor_cycles += 1
    _affected_syms = sorted({o.symbol for o in _open_trades})
    log.warning(
        "[Monitor] OPEN_POSITIONS_PRESENT_BUT_NO_PRICE_FEED "
        "missed_cycle=%d  open_positions=%d  symbols=%s  ts=%s",
        self._missed_monitor_cycles, len(_open_trades),
        _affected_syms, _now_ts.strftime("%H:%M:%S"),
    )
    # Telegram alert: on first miss, then every 6 cycles (≈ 30 min)
    if self._missed_monitor_cycles == 1 or self._missed_monitor_cycles % 6 == 0:
        get_notifier().send_alert(
            f"[Monitor] No price feed for {len(_open_trades)} open "
            f"position(s) — cycle #{self._missed_monitor_cycles} skipped.\n"
            f"Symbols: {_affected_syms}\n"
            f"Time: {_now_ts.strftime('%H:%M:%S IST')}"
        )
elif _live_pf and self._missed_monitor_cycles > 0:
    # Feed recovered — reset counter
    log.info("[Monitor] Price feed recovered after %d missed cycle(s).",
             self._missed_monitor_cycles)
    self._missed_monitor_cycles = 0
```

---

## Behaviour After Fix

| Condition | Previous | After |
|---|---|---|
| `_live_pf` populated, open positions exist | `check_all()` runs | Unchanged |
| `_live_pf` empty, no open positions | Silent skip | Silent skip (correct — nothing to do) |
| `_live_pf` empty, open positions exist | **Silent skip** | `WARNING [Monitor] OPEN_POSITIONS_PRESENT_BUT_NO_PRICE_FEED` emitted; `missed_monitor_cycles` incremented |
| Feed recovers after miss(es) | No log | `INFO [Monitor] Price feed recovered after N missed cycle(s).` |

**Alert frequency:** First occurrence → immediate Telegram alert. Subsequent misses
→ alert every 6 cycles (≈ 30 minutes) to avoid Telegram spam during extended feed
outages. Counter resets to 0 on any cycle that successfully obtains prices.

**Log tag:** `OPEN_POSITIONS_PRESENT_BUT_NO_PRICE_FEED` — greppable across all log
files and control tower telemetry.

---

## What Was Not Changed

- `check_all()` logic and execution path — unchanged  
- Price-feed acquisition code — unchanged  
- Carry-expiry behaviour — unchanged  
- `_last_monitor_ts` / MonitoringGap detection (FIX #3) — unchanged  
- All test files — unchanged  
