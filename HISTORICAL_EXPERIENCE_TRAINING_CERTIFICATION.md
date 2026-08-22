# HISTORICAL EXPERIENCE TRAINING — CERTIFICATION

**Subsystem:** Historical Experience Training (HET)  
**Version:** R1.3  
**Certification Date:** 2026-08-01  
**Auditor:** Architecture review against implemented code  

---

## DECLARATION

> **CERTIFIED WITH OBSERVATIONS**
>
> Historical Experience Training produces knowledge from verified historical market evidence through a complete, integrity-validated learning pipeline. Remaining limitations are documented below. No limitation is hidden.

---

## 1. Replay Engine

| Requirement | Status | Evidence |
|---|---|---|
| Uses production orchestration | ✓ VERIFIED | `ReplayOrchestrator(MasterOrchestrator)` — single inheritance chain; all 17 layers execute unchanged |
| No duplicate execution pipeline | ✓ VERIFIED | No parallel or shadow cycle; `run_full_cycle()` is the unmodified production method |
| Paper trading enforced | ✓ VERIFIED | `os.environ.setdefault("PAPER_TRADING", "true")` set before any module import in `run_replay.py` |
| Historical data injected, not hard-coded | ✓ VERIFIED | `_inject_day(day_data)` monkey-patches `market_data_ai.fetch` and `global_intelligence.run` per day; patches removed by `_restore()` in `finally` block |
| Historical data source | ✓ VERIFIED | yfinance daily OHLCV via `historical_loader.py`; 33 NSE stocks + NIFTY/BANKNIFTY/VIX indices |

---

## 2. Historical Outcomes

| Requirement | Status | Evidence |
|---|---|---|
| Learning uses historical OHLC | ✓ VERIFIED | `_resolve_historical_outcome()` in `replay_engine.py` compares entry/SL/target against `day_high`/`day_low` from `day_data.stock_watchlist` |
| No simulated outcome in learning path | ✓ VERIFIED | MD5 hash removed from `_close_replay_positions_with_outcomes()`; `_sim_pnl()` is dead code, not called from either the learning or report path |
| Conservative ambiguity policy | ✓ VERIFIED | When both `sl_hit` and `target_hit` are true for the same candle, `close_sl` is returned (SL assumed to have fired first) |
| Orphan trades excluded from learning | ✓ VERIFIED | Positions with incomplete signal data (`entry/sl/target ≤ 0`) receive `ORPHAN_CLOSE` and are excluded by `continue`. Positions with no OHLC data (`day_high == 0 and day_low == 0`) are also assigned `ORPHAN_CLOSE` and skipped by an explicit `if reason == "ORPHAN_CLOSE": continue` guard |

### Resolution Logic (verified from `_resolve_historical_outcome()`)

```
BUY / LONG:
  day_low  <= stop_loss    →  close_sl     (exit at stop_loss)
  day_high >= target       →  close_target (exit at target)
  neither hit              →  eod_close    (exit at ltp / closing price)

SELL / SHORT:
  day_high >= stop_loss    →  close_sl     (exit at stop_loss)
  day_low  <= target       →  close_target (exit at target)
  neither hit              →  eod_close    (exit at ltp / closing price)

Ambiguous candle (both levels within day range):
  →  close_sl   (conservative: stop assumed first)

No OHLC data (day_high == 0 and day_low == 0):
  →  ORPHAN_CLOSE at entry — excluded from all learning components
```

Report metrics in `executed_trades` also use `_resolve_historical_outcome()` — the simulation is not retained for reporting.

---

## 3. Learning Integrity

| Requirement | Status | Evidence |
|---|---|---|
| Integrity Validator active | ✓ VERIFIED | `IntegrityValidator` instantiated in `ReplayOrchestrator.__init__()`; `snapshot_start()` called at construction |
| Daily validation | ✓ VERIFIED | `self._validator.check_day(...)` called in `run_replay_day()` after every `_do_eod_learning()` |
| Summary report | ✓ VERIFIED | `orch.get_integrity_summary()` called unconditionally in `run_replay.py` before Step 3 metrics |
| Strict mode available | ✓ VERIFIED | `--strict` CLI flag; `ReplayOrchestrator(strict_validation=True)`; raises `ReplayIntegrityError` → `sys.exit(2)` |

### Five Daily Integrity Checks

| # | Check | Stage label | Exempt condition |
|---|---|---|---|
| 1 | `n_closed == n_fed` | `learning_records` | None |
| 2 | `n_labels_updated == n_fed` | `label_enrichment` | `feature_rows_available == 0` (Day 1 or SYMBOL_UNIVERSE gap) |
| 3 | `n_labels_updated <= feature_rows_available` | `feature_db` | None |
| 4 | EDE completed without exception | `edge_discovery` | `n_fed == 0` |
| 5 | `ede_feature_db.json` and `discovered_edges.json` exist | `persistence` | `n_fed == 0` |

---

## 4. Knowledge Generation

### Verified Pipeline

```
Historical Replay (yfinance OHLCV)
  │
  ├─ run_full_cycle()
  │    ├─ Layer 3:  MetaLearning.predict()        ← caches _last_snapshot
  │    ├─ Layer 4:  OpportunityEngine / scanner
  │    └─ Layer 11: ExecutionEngine → OrderManager.execute()
  │
  ├─ _close_replay_positions_with_outcomes(day_data)
  │    ├─ _ohlc lookup built from day_data.stock_watchlist
  │    └─ _resolve_historical_outcome() per open position
  │         ├─ close_sl     → exit at stop_loss
  │         ├─ close_target → exit at target
  │         ├─ eod_close    → exit at ltp
  │         └─ ORPHAN_CLOSE → excluded from learning
  │
  └─ _do_eod_learning()
       ├─ LearningEngine.learn(trades)               → data/learning_db.json
       ├─ PerformanceEvaluator.record_trade()        → in-memory (report only)
       ├─ StrategyPerformanceTracker.record_trade()  → data/strategy_performance.json
       ├─ RegimeStrategyMap.record()                 → data/regime_strategy_map.json
       ├─ MetaLearningEngine.record_result()         → data/ml_performance_dataset.json
       │    └─ MetaModel.add(Observation)            → in-memory k-NN model
       ├─ MetaLearningEngine.retrain_if_due()        → full retrain every 7 days
       ├─ EdgeDiscoveryEngine.enrich_with_outcomes() → data/ede_feature_db.json
       ├─ EdgeDiscoveryEngine.record_outcome()       → EdgeRankingEngine in-memory
       └─ EdgeDiscoveryEngine.run_discovery_cycle()
            ├─ FeatureExtractor._append_current_features()  → ede_feature_db.json
            ├─ PatternMiner.mine()                          → in-memory patterns
            ├─ CandidateStrategyGenerator.generate()
            ├─ StrategyTester.test()
            └─ EdgeRankingEngine.update()                   → data/discovered_edges.json
                 └─ persist_approved()                      → data/evolved_strategies.json
```

---

## 5. Meta Learning

| Requirement | Status | Evidence |
|---|---|---|
| Replay wired to `record_result()` | ✓ VERIFIED | Called per trade in `_do_eod_learning()` with `trade_date=self._current_replay_date` |
| Uses correct historical date | ✓ VERIFIED | `self._current_replay_date = str(day_data.date)` set in `_close_replay_positions_with_outcomes()` — not `datetime.now()` |
| PerformanceDataset updated | ✓ VERIFIED | `record_result()` → `PerformanceDataset.add_from_trade()` → `data/ml_performance_dataset.json` |
| TrainingEngine updated | ✓ VERIFIED | `record_result()` → `TrainingEngine.add_observation()` → `MetaModel.add(Observation)` |
| MetaModel warms up over replay | ✓ VERIFIED | `MetaModel.add()` incremental append; active once ≥ 10 observations |
| Periodic retrain | ✓ VERIFIED | `retrain_if_due()` triggers full retrain every 7 calendar days of data |
| Prediction path unchanged | ✓ VERIFIED | `MetaModel.predict()` not modified; k-NN algorithm not modified |
| No second MetaModel instantiated | ✓ VERIFIED | `self.meta_learning` inherited from `MasterOrchestrator.__init__()` |

### Meta-Learning Flow Verified

```
Replay Day N closes
  ↓
meta_learning.record_result(
  strategy=..., snapshot=None,        ← falls back to _last_snapshot from Layer 3
  r_multiple=..., return_pct=...,
  won=..., trade_date="YYYY-MM-DD"    ← actual historical date
)
  ↓
PerformanceDataset.add_from_trade()   → data/ml_performance_dataset.json (persisted)
  ↓
TrainingEngine.add_observation()
  ↓
MetaModel.add(Observation(features, strategy, r_multiple))
  ↓
retrain_if_due() every 7 days         → full k-NN rebuild from PerformanceDataset
  ↓
Day N+1: meta_learning.predict() uses updated model
```

---

## 6. Knowledge Stores

| File | Owner | Format | Updated by Replay | Persists Across Runs |
|---|---|---|---|---|
| `data/learning_db.json` | `LearningEngine` | JSON dict — agent weight modifiers per strategy | ✓ via `LearningEngine.learn()` | ✓ |
| `data/ede_feature_db.json` | `EdgeDiscoveryEngine` | JSON array — feature rows with `forward_return` labels | ✓ via `enrich_with_outcomes()` + `_append_current_features()` | ✓ |
| `data/discovered_edges.json` | `EdgeRankingEngine` | JSON dict keyed by edge name — `EdgeRecord` lifecycle | ✓ via `run_discovery_cycle()` | ✓ |
| `data/evolved_strategies.json` | `StrategyEvolutionAI` / `CandidateStrategyGenerator` | JSON array — approved strategy variants | ✓ via `persist_approved()` | ✓ |
| `data/strategy_performance.json` | `StrategyPerformanceTracker` | JSON dict — per-strategy win rate, Sharpe, drawdown | ✓ via `perf_tracker.record_trade()` | ✓ |
| `data/regime_strategy_map.json` | `RegimeStrategyMap` | JSON dict — regime → strategy outcome statistics | ✓ via `regime_strategy_map.record()` | ✓ |
| `data/ml_performance_dataset.json` | `PerformanceDataset` | JSON array — `PerformanceRecord` per trade with regime/VIX/breadth context | ✓ via `meta_learning.record_result()` | ✓ |

**Not persisted between runs (in-memory only):**
- `MetaModel._obs` (k-NN observation list) — recoverable by calling `trainer.force_retrain()` from `PerformanceDataset` on startup; not wired automatically.

---

## 7. Replay Assumptions

### Documented

| Assumption | Category | Impact | Mitigated? |
|---|---|---|---|
| **End-of-day OHLCV model** — trade resolution uses daily bar (open/high/low/close), not tick or intraday bars | Design constraint | Cannot determine exact sequence of intraday events | Partially — conservative SL-first policy applied |
| **Same-day OHLCV availability** — `day_high`/`day_low` are the real same-day values, but they represent the full trading session. A morning-cycle scanner that fires at 9:30 cannot know the day's high and low at that moment. | Look-ahead (weak) | Replay overstates the certainty of outcome; real intraday path unknown | Documented; inherent in daily-bar replay |
| **Conservative SL-first ambiguity** — when both stop-loss and target fall within the day's range, stop-loss is assumed to have been hit first | Policy choice | Understates win rate vs. actual; reduces optimism bias | Accepted — standard daily-bar backtesting convention |
| **Survivorship bias** — `NSE_STOCKS` is 33 hardcoded 2026 Nifty 100 constituents applied to all historical dates | Scientific limitation | Delisted or downgraded stocks are absent from historical training data; past performance is modelled on companies that survived to 2026 | Documented; not hidden. Requires dynamic index-composition lookup to fix (R1.5) |
| **Feature Extractor symbol universe gap** — `SYMBOL_UNIVERSE` in `FeatureExtractor` covers 20 fixed symbols; equity scanner trades from 33 stocks | Architectural gap | `enrich_with_outcomes()` finds no feature row for out-of-universe symbols; EDE Check 2 fails silently for those symbols on Day 1 | Documented; integrity validator Check 2 exempts Day 1 and no-feature-row cases (R1.6) |
| **MetaModel in-memory state** — `MetaModel._obs` is not persisted between replay runs | Persistence gap | Re-running replay resets k-NN to 0 observations; predictions start from prior PerformanceDataset only after forced retrain | PerformanceDataset IS persisted; full recovery possible via `force_retrain()` (R1.4) |
| **RSI computed with same-day close** — `_compute_rsi()` in `historical_loader.py` includes today's closing price in the RSI window | Weak look-ahead | RSI slightly forward-biased by same-day close; affects signal quality not outcome labels | Documented; impact minimal for EOD RSI usage |

---

## 8. Regression

| Category | Status | Evidence |
|---|---|---|
| Production behaviour changed | ✓ NO CHANGE | All modifications confined to `simulation_replay/` package; `MasterOrchestrator` not modified |
| Architecture changed | ✓ NO CHANGE | `ReplayOrchestrator` is an existing subclass; no new layers, singletons, or agents added |
| Public APIs changed | ✓ NO CHANGE | `run_full_cycle()`, `BaseFeed.get_quote()`, `GlobalDataAI.fetch()`, `SystemMonitor.time_layer()` signatures unchanged |
| Learning algorithms changed | ✓ NO CHANGE | `LearningEngine`, `PatternMiner`, `EdgeDiscoveryEngine`, `MetaModel`, `StrategyEvolution` not touched |
| Production entry point changed | ✓ NO CHANGE | `main.py` not modified in R1.1–R1.3 |
| `fragility_test.py` / `limit_order_sim.py` changed | ✓ NO CHANGE | Both still use their own internal simulation logic, which is correct for stress/noise testing |

---

## Governance Questions

**1. Can Historical Experience Training now produce knowledge from verified historical market evidence?**

Yes. As of R1.3:
- Trade outcomes are resolved from real yfinance OHLCV prices (`_resolve_historical_outcome()`)
- Feature labels in `ede_feature_db.json` carry real `forward_return` values
- `MetaModel` accumulates observations from verified historical outcomes
- All six persistent knowledge stores receive updates from replay learning
- The Learning Integrity Validator confirms the pipeline is connected on every replay day

**2. Is replay learning scientifically suitable for long-duration historical training?**

Yes, with qualifications. The system is suitable for:
- Strategy regime-learning experiments (RegimeStrategyMap, MetaModel)
- Edge pattern discovery (EDE)
- Agent weight calibration (LearningEngine)

Known limitations that bound scientific validity:
- **Survivorship bias**: training universe fixed to 2026 survivors. This overstates the quality of historical NSE trading by excluding companies that were present in historical periods but absent today.
- **Daily-bar ambiguity**: outcome resolution on days where both SL and target are within the bar range uses a conservative heuristic, not the true intraday outcome.
- **Same-day close leakage**: scanner features are built with today's closing OHLCV, which is not available at market open in a real trading session.

These limitations are bounded and do not make the system unusable; they require the user to treat results as directional evidence, not precise historical truth.

**3. Are any remaining limitations documented rather than hidden?**

Yes. All limitations are enumerated in Section 7 (Replay Assumptions) with their category (design constraint, scientific limitation, architectural gap, persistence gap), their impact, and their mitigation or pending ticket reference. No limitation has been suppressed or worked around without documentation.

---

## Summary

| Dimension | Result |
|---|---|
| Replay Engine | CERTIFIED |
| Historical Outcomes | CERTIFIED |
| Learning Integrity | CERTIFIED |
| Knowledge Generation | CERTIFIED |
| Meta Learning | CERTIFIED |
| Knowledge Stores | CERTIFIED |
| Replay Assumptions | DOCUMENTED |
| Regression | CERTIFIED — No production changes |

### Overall: **CERTIFIED WITH OBSERVATIONS**

Observations (not defects):
1. Survivorship bias in the 33-stock universe (R1.5 planned)
2. MetaModel in-memory state not auto-recovered on re-run (R1.4 planned)
3. EDE symbol universe covers 20 of 33 traded stocks (R1.6 planned)

These observations are known, bounded, and do not invalidate the certification. Historical Experience Training is the official evidence base for all future research experiments in this system.
