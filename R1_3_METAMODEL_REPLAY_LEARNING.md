# R1.3 — MetaModel Historical Learning

**Status:** Implemented  
**File Modified:** `simulation_replay/replay_engine.py` (only)  
**Date:** 2026-08

---

## 1. Root Cause

`ReplayOrchestrator._do_eod_learning()` (the replay-specific override added in R1.1) called all production learning APIs except `MetaLearningEngine.record_result()`. The MetaModel therefore:
- Made predictions during replay (Layer 3 of `run_full_cycle()`)  
- Received zero feedback from those predictions
- Accumulated no observations over the replay run
- Produced identical predictions on Day 30 as on Day 1

The production `_do_eod_learning()` in `MasterOrchestrator` includes the Meta-Learning block (line 4110). It was absent from the replay override.

---

## 2. Implementation Summary

Three changes to `simulation_replay/replay_engine.py`:

**1. `__init__`** — added `self._current_replay_date: Optional[str] = None`  
Stores the historical trading date so `_do_eod_learning()` can stamp each `PerformanceRecord` with the correct date rather than `datetime.now()` (= 2026-08-01 for all replay days).

**2. `_close_replay_positions_with_outcomes(day_data)`** — added `self._current_replay_date = str(day_data.date)` at the top  
Set before the close loop so the date is always fresh when `_do_eod_learning()` runs.

**3. `_do_eod_learning()`** — added Meta-Learning feedback block after performance tracking

```python
for trade in trades:
    strategy   = getattr(trade, "strategy", None) or "unknown"
    pnl        = getattr(trade, "pnl",        0.0)
    r_multiple = getattr(trade, "r_multiple",  0.0)
    self.meta_learning.record_result(
        strategy   = strategy,
        snapshot   = None,   # MetaLearningEngine uses _last_snapshot from run_full_cycle
        r_multiple = r_multiple,
        return_pct = pnl / 1_000_000 * 100,
        won        = pnl > 0,
        trade_date = self._current_replay_date,
    )
self.meta_learning.retrain_if_due()
```

API signatures match production exactly. `snapshot=None` is correct — `MetaLearningEngine.record_result()` falls back to its cached `_last_snapshot` from the `predict()` call that ran during Layer 3 of `run_full_cycle()`.

---

## 3. Replay Learning Flow

```
DAY N:
  run_full_cycle()
    └─ Layer 3: MetaLearning
         └─ meta_learning.predict(snapshot, strategies)
              └─ caches snapshot as _last_snapshot

  _close_replay_positions_with_outcomes(day_data)
    ├─ self._current_replay_date = str(day_data.date)  ← historical date
    └─ resolves exits from real OHLC prices (R1.2)

  _do_eod_learning()
    ├─ learning_engine.learn(trades)
    ├─ performance_evaluator / perf_tracker / regime_strategy_map
    │
    ├─ [NEW] meta_learning.record_result(strategy, snapshot=None,
    │         r_multiple, return_pct, won,
    │         trade_date=self._current_replay_date)
    │    └─ adds PerformanceRecord (dated correctly)
    │    └─ TrainingEngine.add_observation() → MetaModel.add(obs)
    │
    ├─ meta_learning.retrain_if_due()
    │    └─ triggers full retrain every 7 calendar days of observations
    │
    └─ edge_discovery.enrich_with_outcomes() + run_discovery_cycle()
```

**What `meta_learning.record_result()` does internally:**
1. `PerformanceDataset.add_from_trade()` — builds `PerformanceRecord` with regime, VIX, breadth etc. extracted from `_last_snapshot`; stamps `trade_date` with actual historical date
2. `FeatureExtractor.extract(snapshot)` → `FeatureVector`
3. `TrainingEngine.add_observation()` → `MetaModel.add(Observation(features, strategy, r_multiple))`
4. k-NN model becomes active once 10 observations are accumulated

**Observation accumulation:**
- Each replay day with N closed trades adds N observations
- After `retrain_if_due()`: if ≥7 days of data have been recorded since last full retrain, `TrainingEngine.force_retrain()` rebuilds the model from the full `PerformanceDataset`
- From Day 2 onwards predictions are influenced by Day 1's outcomes

---

## 4. Validation Results

Expected log lines after running `python simulation_replay/run_replay.py`:

```
[MetaModel] Reached 10 observations — model is now active.
[TrainingEngine] Retrain #1 complete. Records: N | Strategies: M | Model ready: ✅
[MetaLearningEngine] ...
[ReplayIntegrity] Day D PASS — closed=N fed=N labels=K patterns=P
```

`meta_learning.status()` should show increasing `Records=` and `Observations=` counts across days.

---

## 5. Regression Summary

| Component | Risk | Notes |
|---|---|---|
| `MetaModel` | None | Not modified; `add()` is the standard incremental-update path |
| `TrainingEngine` | None | Not modified; `add_observation()` is the standard live-trading path |
| `PerformanceDataset` | None | Not modified; `add_from_trade()` called with same args as production |
| `MasterOrchestrator._do_eod_learning()` | None | Not modified |
| Production live trading | None | `_do_eod_learning()` override is in `ReplayOrchestrator` only |
| Integrity validation | None | `_current_day_trades` unchanged; validator reads same list |
| Feature extraction | None | `FeatureExtractor.extract()` called inside `record_result()` from cached snapshot |

**Date contamination eliminated:** `trade_date=self._current_replay_date` stamps each `PerformanceRecord` with the actual historical date (e.g. `"2026-06-15"`) rather than `str(date.today())` = `"2026-08-01"`. Records are correctly ordered in the dataset.

---

## 6. Remaining Gaps

| Gap | Severity | Ticket |
|---|---|---|
| **MetaModel is not persisted between replay runs** — `MetaModel._obs` lives in memory; closing and rerunning the replay starts from 0 observations. The `PerformanceDataset` IS persisted (via `dataset.save()` called by `retrain_if_due()`), so a re-run that calls `force_retrain()` at startup would recover, but this is not wired automatically. | Low | R1.4 |
| **Survivorship bias** — `NSE_STOCKS` is 33 hardcoded 2026 constituents applied to all historical dates | Medium | R1.5 |
| **EDE symbol universe gap** — `FeatureExtractor.SYMBOL_UNIVERSE` is 20 fixed symbols; equity scanner trades from 33 stocks | Medium | R1.6 |
| **Same-day OHLCV leakage** — today's `day_high`/`day_low` visible to morning scanner | Low | R1.7 |
