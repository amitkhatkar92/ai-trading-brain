# DNADiscoveryEngine — API Reference

**Package:** `market_learning`  
**Module:** `market_learning.dna_discovery_engine`

---

## Quick Start

```python
from market_learning import (
    DNADiscoveryEngine, MLSConfig,
    DiscoveryReport, DNACharacteristic, SeparationDirection,
)

engine = DNADiscoveryEngine()                          # default config + data dir
report = engine.discover(snapshot, classification)     # ← core call

# Query
winner = engine.winner_dna("2026-08-03")
print(winner.characteristics[0].feature_name)
```

---

## Class: `DNADiscoveryEngine`

```python
DNADiscoveryEngine(
    config: Optional[MLSConfig] = None,
    data_dir: Optional[str | Path] = None,
)
```

| Parameter | Default | Description |
|---|---|---|
| `config` | `MLSConfig()` | Configuration object |
| `data_dir` | `data/mls/dna` | Directory for JSON storage |

---

### `discover(snapshot, classification, history=None) → DiscoveryReport`

Main entry point. Thread-safe.

| Parameter | Type | Description |
|---|---|---|
| `snapshot` | `DailyMarketSnapshot` | Phase 1 output — all observations |
| `classification` | `ClassificationResult` | Phase 2 output — population assignments |
| `history` | `List[DiscoveryReport]` | Previous reports for lifecycle tracking |

**Returns:** `DiscoveryReport`  
**Raises:** `InsufficientDataError` if winner or loser group is smaller than `dna_min_group_size`  
**Persists:** `data/mls/dna/dna_YYYY-MM-DD.json`

---

### `winner_dna(trading_date) → Optional[WinnerDNA]`
### `loser_dna(trading_date) → Optional[LoserDNA]`
### `neutral_dna(trading_date) → Optional[NeutralDNA]`

Load a specific DNA profile from disk.

```python
date = "2026-08-03"
w = engine.winner_dna(date)   # WinnerDNA | None
```

---

### `list_characteristics(trading_date=None) → List[DNACharacteristic]`

Return characteristics for a specific date (or all dates if `None`).

```python
all_chars = engine.list_characteristics()           # entire history
today     = engine.list_characteristics("2026-08-03")
```

---

### `list_reports() → List[str]`

Return sorted list of trading dates that have persisted reports.

```python
dates = engine.list_reports()   # ["2026-08-01", "2026-08-02", ...]
```

---

### `load_report(trading_date) → Optional[DiscoveryReport]`

Deserialise a report from disk. Returns `None` if no file exists.

---

### `statistics(trading_date) → Optional[DNAStatistics]`

Convenience summary for a single date.

```python
stats = engine.statistics("2026-08-03")
print(stats.total_characteristics, stats.top_winner_feature)
```

---

## Data Models

### `DiscoveryReport`

| Field | Type | Description |
|---|---|---|
| `report_id` | `str` | `MLS-DNA-YYYYMMDD` |
| `trading_date` | `str` | ISO date |
| `snapshot_id` | `str` | Source snapshot ID |
| `classification_id` | `str` | Source classification ID |
| `winner_dna` | `WinnerDNA` | Winner-group DNA |
| `loser_dna` | `LoserDNA` | Loser-group DNA |
| `neutral_dna` | `NeutralDNA` | Neutral-group DNA |
| `all_characteristics` | `List[DNACharacteristic]` | All filtered characteristics |
| `all_interactions` | `List[DNAInteraction]` | All filtered interactions |
| `regime` | `str` | Market regime label |
| `universe_size` | `int` | Total observations analysed |
| `created_at` | `str` | ISO datetime |

**Methods:**
- `get_characteristic(feature_name) → Optional[DNACharacteristic]`
- `characteristics_by_direction(direction) → List[DNACharacteristic]`
- `to_dict() / from_dict(d)`

---

### `DNACharacteristic`

| Field | Type | Description |
|---|---|---|
| `char_id` | `str` | `DNA-{sha256[:8]}` — deterministic per (feature, direction) |
| `feature_name` | `str` | Feature identifier |
| `feature_type` | `FeatureType` | BINARY / ORDINAL / CONTINUOUS |
| `direction` | `SeparationDirection` | Which group has higher values |
| `effect_size` | `float` | Signed Cohen's d |
| `effect_abs` | `float` | |Cohen's d| |
| `confidence` | `float` | 0–1 weighted score |
| `lifecycle` | `DNALifecycle` | DISCOVERED → … → STABLE/WEAKENING |
| `trading_date` | `str` | ISO date |
| `regime` | `str` | Market regime |
| `evidence` | `FeatureEvidence` | Full statistical evidence |
| `first_seen` | `str` | Earliest date this characteristic was found |
| `last_seen` | `str` | Same as `trading_date` |
| `occurrence_count` | `int` | Times seen across history |

---

### `FeatureEvidence`

| Field | Type |
|---|---|
| `winner_mean`, `winner_std` | `float` |
| `loser_mean`, `loser_std` | `float` |
| `effect_size`, `effect_abs` | `float` |
| `direction` | `SeparationDirection` |
| `ci_low`, `ci_high` | `float` — bootstrap 95 % CI |
| `spearman_corr` | `float` |
| `n_winners`, `n_losers` | `int` |

---

### `DNAInteraction`

| Field | Type | Description |
|---|---|---|
| `interaction_id` | `str` | `INT-{sha256[:8]}` |
| `features` | `List[str]` | Two feature names |
| `joint_effect` | `float` | Cohen's d of combined signal |
| `max_individual` | `float` | Stronger of the two individual effects |
| `amplification` | `float` | `abs(joint) / max_individual − 1` |
| `trading_date` | `str` | |
| `regime` | `str` | |

---

### DNA Profiles

All three profiles share a common structure:

| Field | Type |
|---|---|
| `date` | `str` |
| `characteristics` | `List[DNACharacteristic]` (direction-filtered) |
| `interactions` | `List[DNAInteraction]` |
| `population_ids` | `List[str]` |
| `n_members` | `int` |
| `regime` | `str` |

- **`WinnerDNA`** — characteristics with `WINNERS_HIGHER` direction
- **`LoserDNA`** — characteristics with `WINNERS_LOWER` direction
- **`NeutralDNA`** — characteristics with `NEUTRALS_HIGHER` / `NEUTRALS_LOWER`

---

## Enumerations

### `DNALifecycle`
```python
DISCOVERED  # first time seen
REPLICATED  # seen on 1 previous date
VERIFIED    # seen on 2–3 previous dates
STABLE      # seen on 4+ dates, effect not declining
WEAKENING   # 4+ occurrences but effect has dropped > 30 % over last 3
RETIRED     # reserved for future manual retirement
```

### `SeparationDirection`
```python
WINNERS_HIGHER   # winner feature value > loser feature value
WINNERS_LOWER    # winner feature value < loser feature value
NEUTRALS_HIGHER  # neutral feature value > extreme feature value
NEUTRALS_LOWER   # neutral feature value < extreme feature value
```

### `FeatureType`
```python
BINARY      # all values in {0.0, 1.0}
ORDINAL     # ≤ 5 unique integer values
CONTINUOUS  # everything else
```

---

## Exceptions

| Exception | When raised |
|---|---|
| `DNADiscoveryError` | Base class for all engine errors |
| `InsufficientDataError` | Winner or loser group < `dna_min_group_size` |
| `DiscoveryNotFoundError` | Report not found (raised by future consumers; load methods return `None`) |

---

## Module-Level Statistical Functions

These functions are importable directly for testing or downstream use:

```python
from market_learning.dna_discovery_engine import (
    _cohen_d, _spearman, _bootstrap_ci,
    _detect_feature_type, _zscore_pooled,
)
```

| Function | Signature | Notes |
|---|---|---|
| `_cohen_d` | `(a, b) → float` | Returns ±1000 sentinel for zero pooled variance |
| `_spearman` | `(a, b) → float` | Returns 0.0 for n<3 or constant input |
| `_bootstrap_ci` | `(a, b, n_boot, seed=42) → (float, float)` | 95 % percentile CI on Cohen's d |
| `_detect_feature_type` | `(values) → FeatureType` | Auto-detect from unique values |
| `_zscore_pooled` | `(vals_a, vals_b) → (List, List)` | Pooled z-score normalisation |
