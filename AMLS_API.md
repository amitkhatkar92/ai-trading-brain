# AMLS API Reference

**Module:** `market_learning.amls`  
**Class:** `AutonomousMarketLearningScheduler`  
**Phase:** MLS Phase 6  

---

## Constructor

```python
AutonomousMarketLearningScheduler(
    config:      Optional[AMLSConfig]   = None,
    mls_config:  Optional[MLSConfig]    = None,
    data_dir:    Optional[Path]         = None,
    observer:    Optional[Any]          = None,   # MarketObserver
    classifier:  Optional[Any]          = None,   # PopulationClassifier
    discovery:   Optional[Any]          = None,   # DNADiscoveryEngine
    consensus:   Optional[Any]          = None,   # DNAConsensusEngine
    idr:         Optional[Any]          = None,   # IDRRepository
    pig_adapter: Optional[Any]          = None,   # PIGTradingAdapter (optional)
)
```

All six MLS modules are injectable for testing.  Default constructors
create live instances pointing to `data/mls/`.

---

## Pipeline Execution

### `run_pipeline()`

```python
def run_pipeline(
    self,
    market_snapshot: Optional[Any]   = None,
    date:            Optional[date]  = None,
    force:           bool            = False,
) -> MLSPipelineRun
```

Execute the complete 7-stage MLS pipeline.

| Parameter | Description |
|-----------|-------------|
| `market_snapshot` | Pre-move `MarketSnapshot` (timestamp ≤ 09:15 IST). If None, Stage 1 loads today's snapshot from disk. |
| `date` | Trading date. Defaults to today. |
| `force` | Skip all calendar checks (weekend/holiday detection). |

**Returns:** `MLSPipelineRun` — always returned, never raises.

**State transitions:**

| Condition | Returned state |
|-----------|---------------|
| Non-trading day (no force) | `SKIPPED` |
| All 6 substantive stages pass | `SUCCESS` |
| Some stages pass, some fail | `PARTIAL` |
| All non-skipped stages fail | `FAILED` |

---

### `run_stage()`

```python
def run_stage(
    self,
    stage_name: str,
    context:    Optional[Dict[str, Any]] = None,
) -> PipelineStage
```

Execute a single named stage independently.

Each stage loads its required inputs from disk if not provided in `context`.

| `stage_name` | Required context keys |
|---|---|
| `"snapshot_capture"` | `"market_snapshot"` (optional) |
| `"population_classify"` | `"dms"` (optional — loads from disk if absent) |
| `"dna_discover"` | `"dms"`, `"classification"` (optional — loads from disk) |
| `"dna_consensus"` | `"report"` (optional — loads from disk) |
| `"idr_sync"` | `"library"` (optional — loads master_library()) |
| `"pig_refresh"` | none |
| `"generate_report"` | Not supported (returns SKIPPED) |

**Returns:** `PipelineStage` — never raises.

---

## Query API

### `pipeline_status()`

```python
def pipeline_status(self) -> PipelineState
```

Returns the state of the current or last run.  `WAITING` if no runs exist.

---

### `last_run()`

```python
def last_run(self) -> Optional[MLSPipelineRun]
```

Returns the most recent pipeline run, or `None` if no runs exist.

---

### `history()`

```python
def history(self, days: int = 30) -> List[MLSPipelineRun]
```

Returns pipeline runs for the last `days` days, newest first.

---

### `statistics()`

```python
def statistics(self) -> PipelineStatistics
```

Computes aggregate statistics from all available run history.

---

### `health_check()`

```python
def health_check(self) -> PipelineHealth
```

Returns a comprehensive health diagnostic.  Checks:
- Today's snapshot on disk
- ConsensusLibrary non-empty
- IDR accessible
- PIG adapter loaded
- Last run state
- Days since last successful run

---

### `is_trading_day()`

```python
def is_trading_day(self, date_str: Optional[str] = None) -> bool
```

Returns `True` if the given date (default: today, YYYY-MM-DD) is a
trading day — i.e., not a weekend and not in `AMLSConfig.holidays`.

---

## Data Models

### `PipelineState` (enum)

```python
class PipelineState(str, Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED  = "FAILED"
    SKIPPED = "SKIPPED"
    PARTIAL = "PARTIAL"
```

### `PipelineStage`

```python
@dataclass
class PipelineStage:
    name:           str
    state:          PipelineState
    start_time:     Optional[str]    # ISO datetime
    end_time:       Optional[str]    # ISO datetime
    duration_ms:    Optional[float]
    retry_count:    int
    output_summary: str
    failure:        Optional[PipelineFailure]
```

### `PipelineFailure`

```python
@dataclass
class PipelineFailure:
    stage_name:        str
    error_type:        str
    error_message:     str
    retries_attempted: int
    timestamp:         str    # ISO datetime
```

### `MLSPipelineRun`

```python
@dataclass
class MLSPipelineRun:
    run_id:            str
    trading_date:      str             # YYYY-MM-DD
    state:             PipelineState
    stages:            List[PipelineStage]
    started_at:        Optional[str]
    ended_at:          Optional[str]
    total_duration_ms: Optional[float]
    telemetry:         Optional[PipelineTelemetry]

    def get_stage(self, name: str) -> Optional[PipelineStage]: ...
    def failed_stages(self) -> List[PipelineStage]: ...
    def successful_stages(self) -> List[PipelineStage]: ...
```

### `PipelineTelemetry`

```python
@dataclass
class PipelineTelemetry:
    run_id:              str
    trading_date:        str
    start_time:          str
    end_time:            str
    total_duration_ms:   float
    pipeline_state:      str       # PipelineState.value
    success:             bool
    stages_success:      int
    stages_failed:       int
    stages_skipped:      int
    total_retry_count:   int
    knowledge_generated: bool      # True if DNA characteristics discovered
    dna_updated:         bool      # True if ConsensusLibrary refreshed
    repository_writes:   int       # IDR.save() calls completed
    gateway_refreshed:   bool      # PIGTradingAdapter.reload_library() called
    failures:            List[PipelineFailure]
```

### `PipelineStatistics`

```python
@dataclass
class PipelineStatistics:
    total_runs:          int
    successful_runs:     int
    failed_runs:         int
    partial_runs:        int
    skipped_runs:        int
    avg_duration_ms:     float
    total_dna_updates:   int
    total_idr_writes:    int
    total_retries:       int
    success_rate:        float    # successful / (total - skipped)
    last_successful_run: Optional[str]   # YYYY-MM-DD
    last_failed_run:     Optional[str]   # YYYY-MM-DD
```

### `PipelineHealth`

```python
@dataclass
class PipelineHealth:
    healthy:              bool
    issues:               List[str]
    pipeline_state:       str
    last_run_date:        Optional[str]
    last_success_date:    Optional[str]
    days_since_success:   Optional[int]
    missing_snapshot:     bool
    missing_dna:          bool
    repository_ok:        bool
    gateway_ok:           bool
    pipeline_interrupted: bool
```

---

## Configuration — `AMLSConfig`

```python
@dataclass
class AMLSConfig:
    # Execution window times (HH:MM, IST)
    snapshot_time:       str   = "09:15"
    classify_time:       str   = "15:35"
    discover_time:       str   = "15:38"
    consensus_time:      str   = "15:41"
    idr_sync_time:       str   = "15:43"
    pig_refresh_time:    str   = "15:44"
    report_time:         str   = "15:45"

    # Retry policy
    max_retries:         int   = 2
    retry_delay_s:       float = 10.0   # doubles per attempt

    # Stage timeout (0.0 = disabled)
    stage_timeout_s:     float = 300.0

    # History
    history_days:        int   = 90

    # Calendar
    skip_weekends:       bool  = True
    force_run:           bool  = False
    holidays:            List[str] = [...]  # NSE FY2026-27 defaults

    # Snapshot fallback
    load_snapshot_from_disk: bool = True
```

---

## Stage Name Constants

```python
from market_learning import (
    STAGE_SNAPSHOT,    # "snapshot_capture"
    STAGE_CLASSIFY,    # "population_classify"
    STAGE_DISCOVER,    # "dna_discover"
    STAGE_CONSENSUS,   # "dna_consensus"
    STAGE_IDR_SYNC,    # "idr_sync"
    STAGE_PIG_REFRESH, # "pig_refresh"
    STAGE_REPORT,      # "generate_report"
    ALL_STAGES,        # ordered list of all 7 stage names
)
```

---

## Usage Examples

### Full pipeline (orchestrator integration)

```python
from market_learning import AutonomousMarketLearningScheduler, AMLSConfig

# In MasterOrchestrator.__init__:
self.amls = AutonomousMarketLearningScheduler(
    pig_adapter=self.pig_adapter,  # hot-reload after DNA update
)

# In MasterOrchestrator._do_eod_learning() at ~16:45:
run = self.amls.run_pipeline()
log.info("[AMLS] state=%s duration_ms=%.0f dna_updated=%s",
         run.state.value,
         run.total_duration_ms or 0,
         run.telemetry.dna_updated if run.telemetry else False)
```

### With live 09:15 snapshot

```python
# At 09:15, orchestrator has a live MarketSnapshot:
run = self.amls.run_pipeline(market_snapshot=self._last_snapshot)
```

### Single stage re-run

```python
# Re-run IDR sync after a transient DB failure:
stage = amls.run_stage("idr_sync")
print(stage.state, stage.output_summary)
```

### Health monitoring

```python
health = amls.health_check()
if not health.healthy:
    for issue in health.issues:
        log.warning("[AMLS Health] %s", issue)
```

### Custom holiday calendar

```python
amls = AutonomousMarketLearningScheduler(
    config=AMLSConfig(
        holidays=["2027-01-26", "2027-03-25", ...],  # FY2027 holidays
    )
)
```
