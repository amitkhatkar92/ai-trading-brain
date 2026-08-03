# Market Learning System — Phase 1: MarketObserver API Reference

**Package:** `market_learning`  
**Module:** `market_learning.market_observer`  
**Status:** IMPLEMENTED — 61/61 tests passing

---

## MarketObserver

```python
class MarketObserver:
    def __init__(
        self,
        config: Optional[MLSConfig] = None,
        data_dir: Optional[Path] = None,
    ) -> None
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `MLSConfig` | `MLSConfig()` | All algorithm thresholds |
| `data_dir` | `Path` | `data/mls/` | Root storage directory |

**Thread safety:** All public methods are safe for concurrent use.

---

### `capture(snapshot, symbols=None) -> DailyMarketSnapshot`

Capture the complete market state into an immutable daily snapshot.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `snapshot` | `MarketSnapshot` | Market state. `snapshot.timestamp` MUST be ≤ 09:15 IST. |
| `symbols` | `Optional[List[str]]` | Symbol subset. `None` → `FeatureExtractor.SYMBOL_UNIVERSE` (20 symbols). |

**Returns:** `DailyMarketSnapshot` — persisted atomically to `data/mls/snapshots/snapshot_{date}.json`

**Raises**

| Exception | Condition |
|-----------|-----------|
| `TemporalContractViolation` | `snapshot.timestamp.time() > time(9, 15, 0)` IST |
| `MarketObserverError` | `len(symbols_extracted) < MLSConfig.min_universe_size` |

**Example**

```python
from market_learning import MarketObserver
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from datetime import datetime

mo       = MarketObserver()
snapshot = MarketSnapshot(
    timestamp=datetime(2026, 8, 3, 9, 10),
    indices={},
    regime=RegimeLabel.BULL_TREND,
    volatility=VolatilityLevel.MEDIUM,
    vix=15.0,
    market_breadth=0.6,
    pcr=0.9,
    global_sentiment_score=0.3,
)
daily = mo.capture(snapshot, symbols=["RELIANCE", "TCS", "INFY"])

print(daily.snapshot_id)       # MLS-SNAP-20260803
print(daily.universe_size)     # 3
print(daily.feature_timestamp) # 2026-08-03T09:10:00
```

---

### `load_snapshot(trading_date) -> Optional[DailyMarketSnapshot]`

Load a previously captured snapshot by ISO trading date.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `trading_date` | `str` | ISO date, e.g. `"2026-08-03"` |

**Returns:** `DailyMarketSnapshot` if found, `None` if no snapshot exists for that date.

**Example**

```python
snap = mo.load_snapshot("2026-08-03")
if snap is not None:
    obs = snap.get_observation("RELIANCE")
    print(obs.features["mom_5d"])
```

---

### `list_snapshots() -> List[str]`

Return all available snapshot dates as sorted ISO strings.

**Returns:** `List[str]` — ISO date strings, ascending order.

**Example**

```python
dates = mo.list_snapshots()
# ["2026-07-28", "2026-07-29", ..., "2026-08-03"]
```

---

### `statistics() -> ObservationStatistics`

Return aggregate statistics across all stored snapshots.

**Returns:** `ObservationStatistics`

**Example**

```python
stats = mo.statistics()
print(stats.total_snapshots)              # 20
print(stats.avg_universe_size)            # 20.0
print(stats.regimes_observed)             # ["bear_market", "bull_trend"]
print(stats.temporal_violations_detected) # 0
```

---

## MLSConfig

```python
@dataclass
class MLSConfig:
    feature_deadline_hour:             int   = 9
    feature_deadline_minute:           int   = 15
    feature_deadline_second:           int   = 0
    min_universe_size:                 int   = 10
    min_group_size:                    int   = 30
    min_effect_size:                   float = 0.50
    max_p_value:                       float = 0.05
    min_consistency_pct_weekly:        float = 60.0
    min_consistency_pct_monthly:       float = 60.0
    min_consistency_pct_quarterly:     float = 50.0
    min_regime_count:                  int   = 2
    min_sector_count:                  int   = 3
    min_oos_consistency_pct:           float = 0.50
    max_contradiction_ratio:           float = 0.20
    confidence_consistency_weight:     float = 0.50
    confidence_effect_size_weight:     float = 0.30
    confidence_significance_weight:    float = 0.20
    new_char_lookback_days:            int   = 5
    retirement_days:                   int   = 20
    weekly_window_days:                int   = 5
    monthly_window_days:               int   = 20
    quarterly_window_days:             int   = 60
    snapshot_retention_days:           int   = 90

    def config_hash(self) -> str: ...
```

`config_hash()` returns a 16-character hex string (SHA-256[:16]) of the
canonical JSON representation of the config. Stored in every
`ObservationMetadata.mls_config_hash`.

---

## DailyMarketSnapshot

```python
@dataclass
class DailyMarketSnapshot:
    snapshot_id:       str                    # "MLS-SNAP-YYYYMMDD"
    trading_date:      str                    # ISO date
    feature_timestamp: str                    # ISO datetime <= 09:15 IST
    regime:            str                    # e.g. "bull_trend"
    volatility:        str                    # e.g. "medium"
    vix:               float
    pcr:               float
    breadth:           float
    global_bias:       float
    universe_size:     int
    symbols:           List[str]
    observations:      List[MarketObservation]
    metadata:          ObservationMetadata
    created_at:        str                    # ISO datetime

    def get_observation(self, symbol: str) -> Optional[MarketObservation]: ...
    def to_dict(self) -> Dict[str, Any]: ...

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DailyMarketSnapshot: ...
```

---

## MarketObservation

```python
@dataclass
class MarketObservation:
    symbol:            str                # NSE ticker
    feature_timestamp: str                # ISO datetime <= 09:15 IST
    features:          Dict[str, float]   # 51 features
    feature_count:     int                # len(features)

    def to_dict(self) -> Dict[str, Any]: ...

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MarketObservation: ...
```

---

## ObservationMetadata

```python
@dataclass
class ObservationMetadata:
    run_id:                     str        # "MLS-OBS-YYYYMMDD-HHMMSS"
    trading_date:               str
    capture_time:               str        # wall clock start, ISO datetime
    universe_size:              int
    feature_count:              int        # features per symbol
    snapshot_id:                str
    temporal_contract_verified: bool       # always True (violations rejected)
    regime:                     str
    volatility:                 str
    vix:                        float
    pcr:                        float
    breadth:                    float
    global_bias:                float
    mls_config_hash:            str        # sha256[:16] of MLSConfig
    warnings:                   List[str]

    def to_dict(self) -> Dict[str, Any]: ...

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ObservationMetadata: ...
```

---

## ObservationStatistics

```python
@dataclass
class ObservationStatistics:
    total_snapshots:              int
    date_range_start:             Optional[str]   # ISO date or None
    date_range_end:               Optional[str]   # ISO date or None
    total_observations:           int             # sum of universe_size
    avg_universe_size:            float
    avg_feature_count:            float
    regimes_observed:             List[str]        # deduplicated, sorted
    temporal_violations_detected: int             # session-level

    def to_dict(self) -> Dict[str, Any]: ...
```

---

## Exceptions

| Exception | Inherits | Raised When |
|-----------|----------|-------------|
| `TemporalContractViolation` | `Exception` | `snapshot.timestamp > 09:15 IST` |
| `MarketObserverError` | `Exception` | Universe too small, general errors |
| `SnapshotNotFoundError` | `MarketObserverError` | Load by date fails (not raised by default API — caller checks for `None`) |

---

## Package Imports

```python
from market_learning import (
    MarketObserver,
    MLSConfig,
    DailyMarketSnapshot,
    MarketObservation,
    ObservationMetadata,
    ObservationStatistics,
    TemporalContractViolation,
    MarketObserverError,
    SnapshotNotFoundError,
)
```
