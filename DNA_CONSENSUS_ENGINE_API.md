# DNAConsensusEngine — API Reference (MLS Phase 4)

## Import

```python
from market_learning import DNAConsensusEngine
from market_learning.dna_consensus_models import (
    ConsensusLevel, ConsensusLibrary, ConsensusDNA, ConsensusState,
    ConfidenceEvolution, DriftReport, DNAStability, ConsensusStatistics,
    DriftType, DNAConsensusError, ConsensusLibraryNotFoundError,
)
```

---

## Class `DNAConsensusEngine`

### Constructor

```python
DNAConsensusEngine(
    config:   Optional[MLSConfig] = None,
    data_dir: Optional[str | Path] = None,
)
```

| Parameter | Default | Description |
|---|---|---|
| `config` | `MLSConfig()` | Phase 4 configuration block |
| `data_dir` | `data/mls/consensus/` | Directory for `library.json` |

---

### `update(report) → ConsensusLibrary`

Merge a daily `DiscoveryReport` into the consensus library.

- **Thread-safe** (internal `threading.Lock`).
- **Idempotent** per `trading_date` — duplicate calls for the same date are silently no-ops.
- Triggers the retirement sweep for features absent ≥ `consensus_retirement_absent_days` days.
- Atomically persists the updated library to disk.

```python
lib = engine.update(discovery_report)
```

---

### `master_library() → ConsensusLibrary`

Return the full consensus library as persisted on disk.  Read-only.

```python
lib = engine.master_library()
print(lib.master_consensus)   # list of INSTITUTIONAL ConsensusDNA
```

---

### `confidence_history(feature_name, direction=None, level=ConsensusLevel.WEEKLY) → List[ConfidenceEvolution]`

Return the confidence trend for a feature.

| Parameter | Default | Description |
|---|---|---|
| `feature_name` | required | e.g. `"rsi"` |
| `direction` | `None` | `"WINNERS_HIGHER"` / `"WINNERS_LOWER"` / `None` (all) |
| `level` | `WEEKLY` | Window filter — see `ConsensusLevel` |

**`ConsensusLevel` window sizes:**

| Level | Window (days) |
|---|---|
| `DAILY` | 1 |
| `WEEKLY` | 7 |
| `MONTHLY` | 20 |
| `QUARTERLY` | 60 |
| `YEARLY` | 252 |
| `MASTER` | all observations |

**`ConfidenceEvolution` fields:**

| Field | Type | Description |
|---|---|---|
| `feature_name` | str | Feature identifier |
| `direction` | str | `SeparationDirection.value` |
| `level` | `ConsensusLevel` | Window used |
| `points` | `List[ConfidencePoint]` | Chronological confidence observations |
| `trend_slope` | float | OLS slope of confidence values |
| `trend_direction` | str | `"IMPROVING"` / `"STABLE"` / `"DECLINING"` |
| `window_days` | int | Number of observation days used |

---

### `drift_report(feature_name=None, direction=None) → List[DriftReport]`

Return drift reports, optionally filtered.

```python
reports = engine.drift_report(feature_name="rsi")
```

**`DriftReport` fields:**

| Field | Type | Description |
|---|---|---|
| `drift_report_id` | str | `DRF-{sha256[:8]}` |
| `feature_name` | str | Feature identifier |
| `direction` | str | Direction string |
| `trading_date` | str | Date this report was built |
| `drifts` | `List[DriftMeasurement]` | One per `DriftType` |
| `max_drift` | float | Maximum drift magnitude across all types |
| `has_significant_drift` | bool | `True` if any drift ≥ threshold |

**`DriftType` values:** `STATISTICAL`, `REGIME`, `TEMPORAL`, `FEATURE`

---

### `stable_dna() → List[ConsensusDNA]`

Return ConsensusDNA entries that pass all three stability thresholds:
- `replication_frequency >= consensus_stability_min_rep_freq`
- `temporal_stability >= consensus_stability_min_temporal`
- `regime_consistency >= consensus_stability_min_regime`

---

### `retired_dna() → List[ConsensusDNA]`

Return all ConsensusDNA with `consensus_state == RETIRED`.

---

### `statistics() → ConsensusStatistics`

Return aggregate statistics from the current library.

**`ConsensusStatistics` fields:**

| Field | Type |
|---|---|
| `as_of_date` | str |
| `total_consensus_dna` | int |
| `institutional_count` | int |
| `weakening_count` | int |
| `drifting_count` | int |
| `retired_count` | int |
| `avg_consensus_score` | float |
| `avg_replication_freq` | float |
| `top_institutional_feature` | Optional[str] |

---

## Model: `ConsensusDNA`

| Field | Type | Description |
|---|---|---|
| `consensus_id` | str | `CON-{sha256[:8]}` of `feature::direction` |
| `feature_name` | str | Feature identifier |
| `direction` | `SeparationDirection` | Enum value |
| `consensus_state` | `ConsensusState` | Current lifecycle state |
| `consensus_score` | float | Weighted score in [0, 1] |
| `replication_frequency` | float | `count / elapsed_days` |
| `evidence_count` | int | Number of distinct trading dates observed |
| `temporal_stability` | float | 1 − CV of effect_abs |
| `regime_consistency` | float | `distinct_regimes / 5` |
| `sector_consistency` | float | Same as regime_consistency (Phase 4) |
| `confidence_trend` | float | OLS slope of confidence time-series |
| `feature_persistence` | float | Fraction of window days with an observation |
| `first_seen` | str | ISO date — immutable after creation |
| `last_seen` | str | ISO date — updated on every merge |
| `all_observations` | `List[Dict]` | Sorted by date, each has `date/effect_abs/confidence/regime` |
| `regime_counts` | `Dict[str, int]` | Count per named regime |
| `level` | `ConsensusLevel` | Derived from `consensus_state` |

**`ConsensusState` values:**
`DISCOVERED → REPLICATED → VERIFIED → INSTITUTIONAL → WEAKENING / DRIFTING → RETIRED`

---

## Model: `ConsensusLibrary`

| Field | Type |
|---|---|
| `library_id` | str (`MLS-LIB-YYYYMMDD`) |
| `as_of_date` | str |
| `all_consensus` | `List[ConsensusDNA]` (sorted by score desc) |
| `master_consensus` | `List[ConsensusDNA]` (INSTITUTIONAL only) |
| `drift_reports` | `List[DriftReport]` |
| `statistics` | `ConsensusStatistics` |

Both `ConsensusLibrary` and `ConsensusDNA` support `.to_dict()` / `.from_dict()` for JSON round-tripping.

---

## Exceptions

| Exception | When raised |
|---|---|
| `DNAConsensusError` | Base exception for consensus engine errors |
| `ConsensusLibraryNotFoundError` | Subclass — library file missing when required |

---

## Typical Usage

```python
from market_learning import DNAConsensusEngine, MLSConfig
from market_learning.dna_consensus_models import ConsensusLevel

cfg = MLSConfig()
engine = DNAConsensusEngine(config=cfg)

# After each daily DNADiscoveryEngine.discover() call:
lib = engine.update(discovery_report)

# Query
for cdna in lib.master_consensus:
    print(cdna.feature_name, cdna.consensus_score)

# Trend analysis
evolutions = engine.confidence_history("rsi", level=ConsensusLevel.WEEKLY)

# Drift alerts
for report in engine.drift_report():
    if report.has_significant_drift:
        print(f"Drift detected: {report.feature_name} max={report.max_drift:.2f}")
```
