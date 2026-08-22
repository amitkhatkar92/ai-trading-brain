# R1.1 — Replay Learning Completion

**Status:** Implemented  
**File Modified:** `simulation_replay/replay_engine.py` (only)  
**Date:** 2026-08

---

## Root Cause

`run_replay_day()` ran EOD learning **before** closing positions:

```
run_full_cycle()           # places orders
↓
_do_eod_learning()         # WRONG — TradeMonitor has zero closed trades
↓
close_all_positions()      # too late — learning already ran with empty inputs
```

**Consequence chain:**

1. `close_all_positions()` was called *after* learning → `TradeMonitor._closed_orders` was empty when `_do_eod_learning()` ran.
2. `_do_eod_learning()` CSV recovery was also useless: all positions closed with `reason="ORPHAN_CLOSE"` (exit = entry, PnL = 0) because `has_live_ltp=False` in replay — and ORPHAN_CLOSE is in the CSV skip list.
3. `enrich_with_outcomes()` was never called → all `ede_feature_db.json` rows kept `forward_return = 0.0`.
4. `PatternMiner` trained only on the 600-row synthetic bootstrap → no real edge patterns mined.

**Second issue (cross-day CSV contamination):** All replay days write to `paper_trades.csv` using `datetime.now()` as the timestamp. The production CSV recovery filters by `datetime.now().strftime("%Y-%m-%d")` — Day N's learning would have found all of Days 1…N−1 rows too, and `enrich_with_outcomes()` would have labelled Day N's feature row with Day K's return. The override completely bypasses the CSV path.

---

## Code Changes

### 1 · `__init__` — added `_current_day_trades`

```python
self._current_day_trades: list = []
```

Initialised to `[]` at construction; reset by `_close_replay_positions_with_outcomes()` each day.

---

### 2 · New method `_close_replay_positions_with_outcomes(day_data)` → `int`

Replaces `close_all_positions()` in the replay flow.

Key behaviour:
- Iterates `order_manager.get_open_orders()`.
- Uses same MD5 deterministic seed as `_sim_pnl()`: `hashlib.md5(f"{date}:{symbol}".encode()).hexdigest()[:8]` → 55% win rate.
- Exit price = `target` (win) or `stop_loss` (loss); reason = `close_target` / `close_sl`.
- After `close_position()` sets `rec.pnl`, computes `rec.r_multiple` dynamically (dynamic attr on `@dataclass` without `__slots__`).
- Appends valid closed records to `self._current_day_trades`.
- Calls `risk_manager.update_portfolio_heat(0.0)` (replaces old reset).
- Returns count of records added.

---

### 3 · New method `_do_eod_learning()` — override of `MasterOrchestrator._do_eod_learning`

Uses `self._current_day_trades` directly (no CSV, no date-scoped recovery).

Calls same production APIs, unchanged signatures:
- `self.learning_engine.learn(trades)`
- `self.performance_evaluator.record_trade(...)`
- `self.perf_tracker.record_trade(...)`
- `self.regime_strategy_map.record(...)`
- `self.edge_discovery.enrich_with_outcomes(sym, ret_pct)` — **the critical call**
- `self.edge_discovery.record_outcome(strat, pnl > 0)`
- `self.edge_discovery.run_discovery_cycle(ede_snapshot, publish_event=True)`
- `self.bus.publish(LearningEvent(...))`

---

### 4 · `run_replay_day()` — execution order corrected

Before:

```
run_full_cycle()
_do_eod_learning()          ← wrong order
close_all_positions()
```

After:

```
run_full_cycle()
_close_replay_positions_with_outcomes(day_data)   ← close first
_do_eod_learning()                                ← learn from real outcomes
```

---

## Replay Flow Before

```
Day N:
  run_full_cycle()
    └─ OrderManager places N positions

  _do_eod_learning()   ← runs here
    trades = trade_monitor.get_closed_trades()    → []
    csv_recovery(today)                           → [] (ORPHAN_CLOSE filtered)
    enrich_with_outcomes()                        → never called
    run_discovery_cycle()                         → mines only 600 bootstrap rows
    PatternMiner precision: not better than random

  close_all_positions()
    exit_price = entry_price (has_live_ltp=False) → PnL=0, reason=ORPHAN_CLOSE
    TradeMonitor never updated
```

---

## Replay Flow After

```
Day N:
  run_full_cycle()
    └─ OrderManager places N positions

  _close_replay_positions_with_outcomes(day_data)
    for each open order:
      seed = MD5("{date}:{symbol}")[:8]
      win  = (seed % 100) < 55
      exit = target if win else stop_loss
      close_position(rec.order_id, exit, reason="close_target"|"close_sl")
      rec.pnl set by close_position()
      rec.r_multiple = pnl / (|entry-sl| * qty)
      → appended to _current_day_trades
    risk_manager.update_portfolio_heat(0.0)

  _do_eod_learning()   ← positions already closed, non-zero PnL
    trades = list(_current_day_trades)            → N records, real PnL
    for each trade:
      enrich_with_outcomes(symbol, pnl/entry)     → back-fills forward_return
      record_outcome(strategy, pnl > 0)
    run_discovery_cycle(snapshot)
    PatternMiner: trains on real forward_return labels (non-zero)
    EDE: genuine patterns can be discovered
```

---

## Validation Steps

Run after deployment:

```bash
python simulation_replay/run_replay.py
```

Look for these log lines (each day with at least one trade):

```
[ReplayOrchestrator] EOD close: N position(s) with replay outcomes.
[ReplayOrchestrator] EOD learning: N trade(s).
[ReplayOrchestrator] EDE: <non-empty report>
```

Check artefacts:

| File | Expected |
|---|---|
| `data/ede_feature_db.json` | `forward_return` values ≠ 0.0 for traded symbols |
| `data/discovered_edges.json` | Updated with new patterns |
| Logs | `[EDE] Discovered N patterns.` where N > 0 |

If `forward_return` is still all-zero after replay, check that `run_full_cycle()` produces approved signals (confirm `ORDER_PLACED` events in replay trace).

---

## Regression Summary

| Component | Risk | Notes |
|---|---|---|
| `MasterOrchestrator` | None | Not modified |
| `LearningEngine` | None | Called with same API |
| `EdgeDiscoveryEngine` | None | Called with same API |
| `OrderManager` | None | `close_position()` called with valid args |
| `TradeMonitor` | None | Not used in replay path (expected; no `check_all()` runs) |
| Production trading cycle | None | `_do_eod_learning` override is replay-only (class method on `ReplayOrchestrator`) |
| Per-day heat reset | None | `update_portfolio_heat(0.0)` preserved in new method |

---

## Remaining Gaps (out of scope for R1.1)

| Gap | Severity | Ticket |
|---|---|---|
| **Survivorship bias** — `NSE_STOCKS` in `historical_loader.py` is 33 hardcoded 2026 Nifty 100 members applied to all historical dates | Medium | R1.2 |
| **Same-day OHLCV leakage** — today's high/low/close visible to morning-cycle scanner (intraday granularity limitation) | Low | R1.3 |
| **MetaModel cross-day accumulation** — k-NN MetaLearning accumulates features across replay days; no day boundary reset | Medium | R1.4 |
| **EDE feature synthesis** — `FeatureExtractor` synthesises symbol-level features from regime/VIX/date seed rather than real OHLCV | Medium | R1.5 |
