# Market Learning Coordinator — API Reference

**Module:** `market_learning.market_learning_coordinator`  
**Class:** `MarketLearningCoordinator`

---

## Constructor

```python
MarketLearningCoordinator(
    amls:            Optional[AutonomousMarketLearningScheduler] = None,
    dre:             Optional[DNAReinforcementEngine]            = None,
    idr:             Optional[IDRRepository]                     = None,
    pig_adapter:     Optional[PIGTradingAdapter]                 = None,
    learning_engine: Optional[LearningEngine]                    = None,
    config:          Optional[MLCConfig]                         = None,
)
```

All parameters are optional. If `amls`, `dre`, `idr`, or `pig_adapter` are
`None`, their corresponding pipeline stages are skipped with reason `"no_<module>"`.
Passing `None` for all modules is valid for testing — the pipeline runs all six
stages (skipping data-dependent ones) and returns a `LearningRun`.

### Typical production wiring

```python
from market_learning import MarketLearningCoordinator
from market_learning.amls import AutonomousMarketLearningScheduler
from market_learning.dre_engine import DNAReinforcementEngine

amls = AutonomousMarketLearningScheduler(pig_adapter=self.pig_adapter)
dre  = DNAReinforcementEngine()
self.mlc = MarketLearningCoordinator(amls=amls, dre=dre, pig_adapter=self.pig_adapter)
```

---

## Primary API

### `run_learning_pipeline(trades, pig_results) → LearningRun`

Execute the complete six-stage EOD learning pipeline.

```python
run = mlc.run_learning_pipeline(
    trades=closed_trades,       # List[OrderRecord | dict] — today's closed trades
    pig_results=pig_results,    # Dict[str, PlatformIntelligence] — keyed by order_id
)
```

**Always returns** a `LearningRun` even when stages fail. Callers must check
`run.health` or `run.stages_failed` to determine outcome.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `trades` | `List[Any]` | Closed trade records (OrderRecord or dict with `order_id`). Optional — pipeline runs without trades. |
| `pig_results` | `Dict[str, Any]` | Map of `order_id → PlatformIntelligence` for DRE. Trades without a matching PIG result are silently skipped by DRE. |

**Pipeline stages (fixed order):**

| # | Stage | Owner | Skip condition |
|---|---|---|---|
| 1 | `strategy_learning` | `LearningEngine.learn(trades)` | `learning_engine=None` or `strategy_learning_enabled=False` |
| 2 | `amls` | `AMLS.run_pipeline()` | `amls=None` or `amls_enabled=False` |
| 3 | `dna_reinforcement` | `DRE.process_batch(items)` | `dre=None`, `dre_enabled=False`, empty trades, or no PMCI results |
| 4 | `idr_refresh` | `IDRRepository.statistics()` | `idr=None` or `idr_refresh_enabled=False` |
| 5 | `pig_refresh` | `PIGTradingAdapter.reload_library()` | `pig_adapter=None`, `pig_refresh_enabled=False`, or AMLS already refreshed |
| 6 | `summary` | Always runs | Never skipped |

---

## Standalone Stage APIs

### `run_amls() → MLSPipelineRun`

Invoke the AMLS pipeline independently, outside the full EOD pipeline.
Raises `MLCError` if AMLS is not configured.

```python
amls_run = mlc.run_amls()
print(amls_run.state.value, amls_run.total_duration_ms)
```

---

### `run_reinforcement(trades, pig_results) → List[DNAReinforcement]`

Invoke DRE standalone for a list of closed trades.
Raises `MLCError` if DRE is not configured.

```python
reinforcements = mlc.run_reinforcement(
    trades=closed_trades,
    pig_results=pig_results,
)
```

---

## Query API

### `status() → LearningSummary`

Return a summary of the most recently completed pipeline run. Returns a
zero-state summary if no run has been performed.

```python
summary = mlc.status()
print(summary.health.value)          # "HEALTHY" | "DEGRADED"
print(summary.pipeline_healthy)      # True if stages_failed == 0
print(summary.stages_ok)             # count of COMPLETE stages
```

---

### `history(limit=20) → List[Dict]`

Return the last `limit` historical runs as dicts, newest first.

```python
for run in mlc.history(limit=10):
    print(run["run_id"], run["health"], run["total_duration_ms"])
```

---

### `statistics() → Dict`

Return aggregate statistics across all runs in history.

```python
stats = mlc.statistics()
# {
#   "total_runs":       int,
#   "healthy_runs":     int,
#   "degraded_runs":    int,
#   "total_trades":     int,
#   "total_reinforced": int,
#   "avg_duration_ms":  float,
#   "last_run_date":    str | None,
# }
```

---

## Output Models

### `LearningRun`

Complete record of one pipeline execution.

| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | `"mlc-YYYY-MM-DD-{uuid8}"` |
| `trading_date` | `str` | `"YYYY-MM-DD"` |
| `started_at` | `str` | ISO datetime |
| `ended_at` | `str` | ISO datetime |
| `total_duration_ms` | `float` | Wall-clock duration |
| `stages` | `List[LearningStage]` | One record per stage |
| `telemetry` | `LearningTelemetry` | Aggregate counters |
| `health` | `LearningHealth` | `HEALTHY` \| `DEGRADED` |
| `stages_ok` | `int` | Count of COMPLETE stages |
| `stages_failed` | `int` | Count of FAILED stages |
| `stages_skipped` | `int` | Count of SKIPPED stages |

---

### `LearningStage`

Per-stage execution record.

| Field | Type | Description |
|---|---|---|
| `stage_type` | `LearningStageType` | Enum value for the stage |
| `name` | `str` | String name |
| `status` | `LearningStageStatus` | `COMPLETE` \| `FAILED` \| `SKIPPED` |
| `started_at` | `str` | ISO datetime |
| `ended_at` | `str` | ISO datetime |
| `duration_ms` | `float` | Stage wall-clock duration |
| `output` | `Dict` | Stage-specific result data |
| `error` | `str \| None` | Error message if FAILED |

---

### `LearningTelemetry`

Aggregate counters collected across all stages.

| Field | Description |
|---|---|
| `strategy_learning_ran` | LearningEngine.learn() was called |
| `trades_processed` | Number of trades passed to strategy learning |
| `amls_ran` | AMLS pipeline ran successfully |
| `dna_updated` | AMLS updated the ConsensusLibrary |
| `amls_duration_ms` | AMLS stage wall-clock time |
| `dre_ran` | DRE batch was processed |
| `dna_reinforced` | Count of active (non-neutral) reinforcements |
| `dre_trades_attempted` | Trades submitted to DRE |
| `repository_updates` | IDR writes from AMLS |
| `idr_total_dna` | Total DNA records in IDR after refresh |
| `gateway_refresh` | PIG library was reloaded |
| `knowledge_generated` | Total IDR + DRE writes this cycle |

---

### `LearningSummary`

Returned by `status()`.

| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | Last run ID |
| `pipeline_healthy` | `bool` | `True` if `stages_failed == 0` |
| `health` | `LearningHealth` | `HEALTHY` \| `DEGRADED` |
| `stages_ok` | `int` | Complete stages |
| `stages_failed` | `int` | Failed stages |
| `total_duration_ms` | `float` | Last run duration |

---

## MLCConfig

```python
@dataclass
class MLCConfig:
    history_path:              str   = "data/mls/mlc/history.json"
    max_history_runs:          int   = 90
    strategy_learning_enabled: bool  = True
    amls_enabled:              bool  = True
    dre_enabled:               bool  = True
    idr_refresh_enabled:       bool  = True
    pig_refresh_enabled:       bool  = True
    dry_run:                   bool  = False
```

Setting any `*_enabled` flag to `False` skips that stage cleanly without
affecting downstream stages.

---

## Exceptions

| Exception | When raised |
|---|---|
| `MLCError` | Base exception |
| `MLCStageError` | Critical stage failure (not currently raised by pipeline; raised only by standalone APIs when module is missing) |

`run_learning_pipeline()` never raises. All stage errors are caught and recorded.
