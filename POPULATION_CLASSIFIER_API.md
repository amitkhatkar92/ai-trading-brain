# PopulationClassifier API Reference

**MLS Phase 2 — `market_learning.PopulationClassifier`**

---

## Class: `PopulationClassifier`

```python
class PopulationClassifier:
    def __init__(
        self,
        config:   Optional[MLSConfig] = None,
        data_dir: Optional[Path]      = None,
    ) -> None
```

| Parameter | Default         | Description                                     |
|-----------|-----------------|-------------------------------------------------|
| `config`  | `MLSConfig()`   | All configurable thresholds (see MLSConfig)     |
| `data_dir`| `data/mls/`     | Root directory; `classifications/` is created inside |

---

### `classify(snapshot, outcomes=None) -> ClassificationResult`

Classify every stock in `snapshot` across all 8 dimensions.

```python
result = pc.classify(
    snapshot: DailyMarketSnapshot,
    outcomes: Optional[Dict[str, float]] = None,
) -> ClassificationResult
```

**Parameters:**
- `snapshot` — `DailyMarketSnapshot` from `MarketObserver.capture()`.
- `outcomes` — Optional dict `{symbol: realized_return}`. If `None`,
  `mom_1d` feature is used as a proxy (`outcomes_source="feature_proxy"`).

**Returns:** `ClassificationResult` — persisted atomically to disk.

**Raises:**
- `PopulationClassifierError` — snapshot has no observations.
- `OrphanStockError` — bug guard; any stock without classification.

---

### `load_result(trading_date) -> Optional[ClassificationResult]`

Load a persisted classification result.

```python
result = pc.load_result("2026-08-03")  # returns None if missing
```

---

### `list_results() -> List[str]`

Return all available classification dates as sorted ISO date strings.

```python
dates = pc.list_results()  # ["2026-08-01", "2026-08-03", ...]
```

---

### `statistics(trading_date) -> Optional[PopulationStatistics]`

Return aggregate statistics for a single classification date.

```python
st = pc.statistics("2026-08-03")
# st.population_count       == 27
# st.avg_labels_per_symbol  == 8.0
# st.performance_group_sizes == {"TOP_1PCT": 0, "TOP_5PCT": 1, ...}
```

Returns `None` if no result exists for the date.

---

## Class: `ClassificationResult`

```python
@dataclass
class ClassificationResult:
    result_id:       str                    # MLS-CLS-YYYYMMDD
    trading_date:    str                    # ISO date
    snapshot_id:     str                    # links back to MarketObserver
    universe_size:   int
    populations:     List[Population]
    members:         List[PopulationMember]
    outcomes_source: str                    # "external" | "feature_proxy"
    created_at:      str                    # ISO datetime
```

**Methods:**

```python
result.get_population(label: GroupLabel) -> Optional[Population]
# Returns first population matching label across any classifier type.

result.get_population_by_type(
    classifier_type: ClassifierType, label: GroupLabel
) -> Optional[Population]
# Returns the population for a specific (type, label) pair.

result.get_member(symbol: str) -> Optional[PopulationMember]
# Returns the member record for a symbol, or None.

result.populations_for(symbol: str) -> List[Population]
# Returns all 8 populations that symbol belongs to.

result.to_dict()   -> Dict[str, Any]
result.from_dict() -> ClassificationResult  # classmethod
```

---

## Class: `Population`

```python
@dataclass
class Population:
    population_id:   str           # POP-YYYYMMDD-CLASSIFIERTYPE-GROUPLABEL
    trading_date:    str
    classifier_type: ClassifierType
    label:           GroupLabel
    member_count:    int           # == len(members)
    members:         List[str]     # symbol list
    threshold_value: Optional[float]
    created_at:      str
```

---

## Class: `PopulationMember`

```python
@dataclass
class PopulationMember:
    symbol:                str
    trading_date:          str
    population_ids:        List[str]          # all 8 population_ids
    labels:                List[str]          # all 8 GroupLabel values
    realized_return:       Optional[float]    # return used for perf classification
    classification_values: Dict[str, float]   # key features used
```

`classification_values` always contains:
`realized_return`, `sector_strength`, `liquidity_score`, `hist_vol_5d`,
`volume_ratio_raw`, `rsi`, `mom_5d`, `iv_rank`, `bb_position`.

---

## Class: `PopulationStatistics`

```python
@dataclass
class PopulationStatistics:
    trading_date:            str
    universe_size:           int
    population_count:        int           # always 27 for full classification
    classifier_types_used:   List[str]     # 8 values
    avg_labels_per_symbol:   float         # always 8.0
    max_labels_per_symbol:   int           # always 8
    min_labels_per_symbol:   int           # always 8
    performance_group_sizes: Dict[str, int]
    outcomes_source:         str
```

---

## Enum: `ClassifierType`

```python
class ClassifierType(str, Enum):
    PERFORMANCE       = "PERFORMANCE"
    SECTOR            = "SECTOR"
    REGIME            = "REGIME"
    LIQUIDITY         = "LIQUIDITY"
    VOLATILITY        = "VOLATILITY"
    MARKET_CAP        = "MARKET_CAP"
    VOLUME_EXPANSION  = "VOLUME_EXPANSION"
    RELATIVE_STRENGTH = "RELATIVE_STRENGTH"
```

---

## Enum: `GroupLabel` (selected values)

| Label              | ClassifierType    | Condition                                |
|--------------------|-------------------|------------------------------------------|
| `TOP_1PCT`         | PERFORMANCE       | Top 1% by return (floor)                 |
| `TOP_5PCT`         | PERFORMANCE       | [n1, n5) exclusive                        |
| `TOP_10PCT`        | PERFORMANCE       | [n5, n10) exclusive                       |
| `NEUTRAL`          | PERFORMANCE       | Middle bracket                           |
| `BOTTOM_10PCT`     | PERFORMANCE       | [n-bn10, n-bn5) exclusive                |
| `BOTTOM_5PCT`      | PERFORMANCE       | [n-bn5, n-bn1) exclusive                 |
| `BOTTOM_1PCT`      | PERFORMANCE       | Bottom 1% by return (floor)              |
| `SECTOR_WINNER`    | SECTOR            | sector_strength >= 0.65                  |
| `SECTOR_LOSER`     | SECTOR            | sector_strength <= 0.35                  |
| `SECTOR_NEUTRAL`   | SECTOR            | Otherwise                                |
| `REGIME_ALIGNED`   | REGIME            | Moving with current regime               |
| `REGIME_DIVERGENT` | REGIME            | Moving against current regime            |
| `HIGH_LIQUIDITY`   | LIQUIDITY         | liquidity_score >= 0.70                  |
| `HIGH_VOLATILITY`  | VOLATILITY        | hist_vol_5d >= 0.20                      |
| `LARGE_CAP`        | MARKET_CAP        | liquidity_score >= 0.70 (proxy)          |
| `VOLUME_EXPANDING` | VOLUME_EXPANSION  | volume_ratio_raw >= 1.50                 |
| `RS_STRONG`        | RELATIVE_STRENGTH | rsi >= 65.0                              |

Full list: see `GroupLabel` enum in `population_classifier_models.py`.

---

## Exceptions

```python
class PopulationClassifierError(Exception): ...
# Base exception. Raised for empty snapshot.

class ClassificationNotFoundError(PopulationClassifierError): ...
# No classification result exists for the requested date.

class OrphanStockError(PopulationClassifierError): ...
# Bug guard: a stock was not assigned to any population.
```

---

## Usage Example

```python
from market_learning import (
    MarketObserver, PopulationClassifier, MLSConfig,
    ClassifierType, GroupLabel,
)
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from datetime import datetime

# Phase 1: capture
mo   = MarketObserver()
snap = mo.capture(MarketSnapshot(
    timestamp=datetime(2026, 8, 3, 9, 10),
    regime=RegimeLabel.BULL_TREND,
    volatility=VolatilityLevel.MEDIUM,
    vix=15.0, market_breadth=0.6, pcr=0.9, global_sentiment_score=0.3,
    indices={},
))

# Phase 2: classify
pc     = PopulationClassifier()
result = pc.classify(snap)

# Query top performers
top5 = result.get_population_by_type(ClassifierType.PERFORMANCE, GroupLabel.TOP_5PCT)
print("Top 5%:", top5.members)

# Query all dimensions for a single stock
reliance_pops = result.populations_for("RELIANCE")
for p in reliance_pops:
    print(f"  {p.classifier_type.value}: {p.label.value}")

# With external outcomes (e.g., after market close)
outcomes = {"RELIANCE": 0.023, "TCS": -0.011, ...}
result2  = pc.classify(snap, outcomes=outcomes)

# Statistics
stats = pc.statistics("2026-08-03")
print(f"Populations: {stats.population_count}")   # 27
print(f"Avg labels:  {stats.avg_labels_per_symbol}")  # 8.0
```
