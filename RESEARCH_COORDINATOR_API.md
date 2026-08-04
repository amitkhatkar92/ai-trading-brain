# ResearchCoordinator API Reference

**IIOS Research Infrastructure — Phase 3A**
**Module:** `autonomous_research.research_coordinator`
**Class:** `ResearchCoordinator`

---

## Constructor

```python
ResearchCoordinator(
    planner=None,
    hypothesis_registry=None,
    evidence_validator=None,
    knowledge_provider=None,
    synthesizer=None,
    idr=None,
    config: RCConfig | None = None,
)
```

All dependencies are optional. Missing dependencies cause the corresponding pipeline stages to be `SKIPPED` instead of `FAILED`.

| Parameter | Type | Description |
|---|---|---|
| `planner` | `StudyPlanner \| None` | Study-plan validator and cost estimator |
| `hypothesis_registry` | `HypothesisRegistry \| None` | Scientific hypothesis store |
| `evidence_validator` | `EvidenceValidator \| None` | Evidence quality gate engine |
| `knowledge_provider` | `KnowledgeProvider \| None` | Read-only knowledge access layer |
| `synthesizer` | `CrossStudySynthesizer \| None` | Cross-study knowledge synthesis engine |
| `idr` | `IDRRepository \| None` | Institutional DNA repository |
| `config` | `RCConfig \| None` | Runtime configuration; defaults to `RCConfig()` |

---

## Public Methods

### `run_research(study_plan) -> ResearchRun`

Execute the full 8-stage research pipeline for an approved study.

```python
run = rc.run_research(approved_plan)
```

**Parameters**
- `study_plan` — An approved `StudyPlan` produced by `StudyPlanner` and authorised by the Scientific Director.

**Returns** — `ResearchRun` with all 8 stage results and a `ResearchTelemetry` record.

**Guarantees**
- Always returns (never raises).
- All 8 stages are attempted; failures in early stages do not abort later stages.
- Stage 8 (`research_report`) always runs.
- History is updated after every call.

---

### `run_study(study_plan) -> ResearchRun`

Semantic alias for `run_research()`. Identical behaviour.

```python
run = rc.run_study(approved_plan)
```

---

### `run_validation(subject_id, subject_type="finding") -> ResearchRun`

Execute only the validation stage for a single subject.

```python
run = rc.run_validation("HYP-001", "hypothesis")
run = rc.run_validation("FND-042", "finding")
```

**Parameters**
- `subject_id` — ID of the hypothesis, finding, or roadmap entry to validate.
- `subject_type` — One of `"hypothesis"`, `"finding"`, or any other subject type string accepted by `EvidenceValidator.validate()`.

**Returns** — `ResearchRun` containing exactly two stages: `validation` + `research_report`.

---

### `status() -> RCStatus`

Return the current operational status of the ResearchCoordinator.

```python
st = rc.status()
print(st.health)                  # ResearchHealth.HEALTHY
print(st.total_runs)              # int
print(st.consecutive_failures)    # int
print(st.planner_available)       # bool
```

**Returns** — `RCStatus` dataclass with health, run counts, component availability flags.

---

### `history(limit=20) -> List[ResearchRun]`

Return the last `limit` ResearchRun records (most recent first).

```python
recent = rc.history(limit=5)
for run in recent:
    print(run.run_id, run.health.value)
```

---

### `statistics() -> Dict[str, Any]`

Return aggregate statistics across all stored runs.

```python
stats = rc.statistics()
print(stats["total_runs"])           # int
print(stats["healthy_runs"])         # int
print(stats["health_rate_pct"])      # float (0.0–100.0)
print(stats["avg_duration_ms"])      # float
print(stats["stages_success_total"]) # int
print(stats["stages_failed_total"])  # int
print(stats["stages_skipped_total"]) # int
```

---

## Data Models

### `ResearchRun`

Complete record of one pipeline execution.

| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | Unique run ID: `rc-{date}-{uuid8}` |
| `study_plan_id` | `str` | ID of the StudyPlan that was executed |
| `study_type` | `str` | Study type string (e.g. `"EDGE_VALIDATION"`) |
| `date` | `str` | Execution date (ISO format) |
| `stages` | `List[ResearchStage]` | All stage results |
| `telemetry` | `ResearchTelemetry \| None` | Machine-readable summary |
| `health` | `ResearchHealth` | Pipeline health enum |

---

### `ResearchStage`

Result of one pipeline stage.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Stage name constant (e.g. `STAGE_VALIDATION`) |
| `state` | `ResearchStageState` | `SUCCESS`, `FAILED`, `SKIPPED`, etc. |
| `start_time` | `str \| None` | ISO-8601 start timestamp |
| `end_time` | `str \| None` | ISO-8601 end timestamp |
| `duration_ms` | `float \| None` | Wall-clock duration in milliseconds |
| `output_summary` | `str` | Human-readable result summary |
| `error` | `str \| None` | Exception message if `FAILED` |
| `meta` | `Dict[str, Any]` | Stage-specific structured metadata |

---

### `ResearchTelemetry`

Machine-readable summary. Key fields:

| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | Matches `ResearchRun.run_id` |
| `stages_success` | `int` | Count of SUCCESS stages |
| `stages_failed` | `int` | Count of FAILED stages |
| `stages_skipped` | `int` | Count of SKIPPED stages |
| `plan_validated` | `bool` | Study Plan stage succeeded |
| `validation_outcome` | `str` | `"PASSED"` / `"FAILED"` / `"N/A"` |
| `evidence_integrated` | `bool` | Evidence written to registry |
| `hypothesis_id` | `str \| None` | Hypothesis the evidence was added to |
| `knowledge_snapshot_taken` | `bool` | Knowledge integration ran |
| `findings_count` | `int` | Findings in knowledge store |
| `synthesis_ran` | `bool` | Cross-study synthesis ran |
| `synthesized_findings` | `int` | Findings synthesized |
| `idr_total_active_dna` | `int` | Active DNA records in IDR |
| `pipeline_healthy` | `bool` | `True` iff `health == HEALTHY` |

Full `to_dict()` is JSON-serialisable.

---

### `RCStatus`

| Field | Type | Description |
|---|---|---|
| `health` | `ResearchHealth` | Current overall health |
| `last_run_id` | `str \| None` | Most recent run_id |
| `consecutive_failures` | `int` | Runs since last HEALTHY run |
| `total_runs` | `int` | Total runs in history |
| `planner_available` | `bool` | StudyPlanner was injected |
| `hypothesis_registry_available` | `bool` | HypothesisRegistry was injected |
| `evidence_validator_available` | `bool` | EvidenceValidator was injected |
| `synthesizer_available` | `bool` | CrossStudySynthesizer was injected |
| `idr_available` | `bool` | IDRRepository was injected |

---

### `ResearchHealth` (enum)

| Value | Meaning |
|---|---|
| `HEALTHY` | All enabled stages completed successfully |
| `DEGRADED` | At least one stage failed; at least one succeeded |
| `FAILED` | All enabled stages failed |
| `NO_DATA` | No runs have been executed yet |

---

### `ResearchStageState` (enum)

`WAITING` | `RUNNING` | `SUCCESS` | `FAILED` | `SKIPPED`

---

## Stage Name Constants

```python
from autonomous_research.rc_models import (
    STAGE_STUDY_PLAN,    # "study_plan"
    STAGE_REPLAY,        # "replay"
    STAGE_VALIDATION,    # "validation"
    STAGE_EVIDENCE,      # "evidence_integration"
    STAGE_KNOWLEDGE,     # "knowledge_integration"
    STAGE_SYNTHESIS,     # "cross_study_synthesis"
    STAGE_REPOSITORY,    # "repository_update"
    STAGE_REPORT,        # "research_report"
    RC_ALL_STAGES,       # List[str] in order
    RC_ALWAYS_RUN,       # frozenset — currently {STAGE_REPORT}
)
```

---

## `RCConfig` Reference

```python
from autonomous_research.rc_config import RCConfig

config = RCConfig(
    history_path="data/ars/rc/history.json",  # JSON run-history store
    max_history_runs=90,                       # eviction limit
    study_plan_enabled=True,
    replay_enabled=True,
    validation_enabled=True,
    evidence_integration_enabled=True,
    knowledge_integration_enabled=True,
    synthesis_enabled=True,
    repository_update_enabled=True,
    dry_run=False,                             # skip all writes when True
)
```

---

## Errors

| Class | Inherits | Usage |
|---|---|---|
| `RCError` | `Exception` | Base error for ResearchCoordinator |
| `RCStageError` | `RCError` | Raised when a stage fails unrecoverably; has `.stage` and `.reason` attributes |

---

## Usage Examples

### Full pipeline

```python
from autonomous_research import ResearchCoordinator, RCConfig
from autonomous_research import StudyPlanner, KnowledgeProvider
from autonomous_research import HypothesisRegistry, EvidenceValidator
from autonomous_research import CrossStudySynthesizer
from market_learning.idr_repository import IDRRepository

planner  = StudyPlanner()
kp       = KnowledgeProvider()
reg      = HypothesisRegistry()
ev       = EvidenceValidator(knowledge_provider=kp)
synth    = CrossStudySynthesizer(knowledge_provider=kp, hypothesis_registry=reg)
idr      = IDRRepository()

rc = ResearchCoordinator(
    planner=planner,
    hypothesis_registry=reg,
    evidence_validator=ev,
    knowledge_provider=kp,
    synthesizer=synth,
    idr=idr,
    config=RCConfig(history_path="data/ars/rc/history.json"),
)

# Scientific Director hands over an approved plan
run = rc.run_research(approved_study_plan)
print(run.health)                      # ResearchHealth.HEALTHY
print(run.telemetry.validation_outcome) # "PASSED"
```

### Validation-only

```python
run = rc.run_validation("HYP-001", "hypothesis")
print(run.telemetry.validation_outcome)
```

### Status check

```python
st = rc.status()
if st.health == ResearchHealth.FAILED:
    alert(f"RC failing: {st.consecutive_failures} consecutive failures")
```

### Package import

```python
from autonomous_research import (
    ResearchCoordinator,
    RCConfig,
    ResearchHealth,
    ResearchRun,
    ResearchStage,
    ResearchStageState,
    ResearchTelemetry,
    RCStatus,
)
```
