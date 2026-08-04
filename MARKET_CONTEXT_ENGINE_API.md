# Market Context Intelligence Engine — API Reference
## MLS Phase 5A: Market Context Intelligence Engine (MCIE)

---

## Imports

```python
from market_learning import (
    MCIEngine,
    MarketContext, ContextComponent, ContextHistory, ContextDrift, ContextStatistics,
    MCIEError, MCIEInputError,
)
```

---

## MCIEngine

### `__init__(config=None)`

```python
engine = MCIEngine()                          # default MLSConfig
engine = MCIEngine(config=MLSConfig(...))     # custom weights / thresholds
```

The engine maintains an in-memory evaluation history (bounded to `mcie_max_history_size`).
It is **not** thread-safe for concurrent `evaluate()` calls on the same instance.

---

### `evaluate(snapshot, evaluation_date=None) → MarketContext`

Evaluate a `MarketSnapshot` and return a complete `MarketContext`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `snapshot` | `MarketSnapshot` | required | Current market state (from `models.market_data`) |
| `evaluation_date` | `str` (ISO) | `None` → snapshot timestamp date | Override the evaluation date |

**Returns:** `MarketContext`

**Side effects:** Appends result to in-memory history. The snapshot is never modified.

```python
from models.market_data import MarketSnapshot
result = engine.evaluate(snapshot, evaluation_date="2026-08-04")
print(result.context_score)           # e.g. 0.704
print(result.regime)                  # e.g. "bull_trend"
print(result.summary)                 # one-line human-readable description
```

---

### `current_context() → Optional[MarketContext]`

Return the most recently evaluated `MarketContext`, or `None` if no evaluation has been done.

```python
ctx = engine.current_context()
if ctx:
    print(ctx.context_score, ctx.regime)
```

---

### `history() → ContextHistory`

Return a frozen snapshot of the full evaluation history (oldest first).

```python
h = engine.history()
print(len(h.contexts))        # number of evaluations
print(h.latest().context_score)  # most recent score
```

---

### `drift() → Optional[ContextDrift]`

Compute drift between the last two evaluations.

Returns `None` if fewer than two evaluations have been performed.

```python
d = engine.drift()
if d:
    print(d.score_delta)             # +0.15 or -0.22
    print(d.regime_changed)          # True / False
    print(d.drifting_components)     # ["volatility_context", "risk_context"]
    print(d.drift_magnitude)         # 0.25
```

---

### `statistics() → ContextStatistics`

Return aggregate statistics over all evaluations in history.  
Returns safe defaults (zeros, empty strings) when history is empty.

```python
stats = engine.statistics()
print(stats.total_evaluations)       # 42
print(stats.avg_context_score)       # 0.681
print(stats.high_context_count)      # 28
print(stats.regime_distribution)     # {"bull_trend": 25, "range_market": 17}
print(stats.most_volatile_component) # "volatility_context"
```

---

## Data Classes

### `MarketContext`

```python
@dataclass
class MarketContext:
    context_id:      str                    # "MCE-{sha256[:8]}" — deterministic
    evaluation_date: str                    # ISO date
    evaluation_time: str                    # ISO datetime (from snapshot.timestamp)
    regime:          str                    # regime label
    context_score:   float                  # [0, 1] — weighted sum of 8 components
    confidence:      float                  # [0, 1] — data richness
    stability:       float                  # [0, 1] — similarity to prior context
    freshness:       float                  # [0, 1] — always 1.0 (current snapshot)
    components:      List[ContextComponent] # always 8 items
    summary:         str                    # one-line human-readable
    raw_inputs:      Dict[str, Any]         # all source values
```

**Methods:**
- `to_dict() → dict` — JSON-serialisable
- `from_dict(d) → MarketContext` — deserialise

---

### `ContextComponent`

One of the eight scored context dimensions.

```python
@dataclass
class ContextComponent:
    name:           str             # e.g. "regime_context"
    score:          float           # [0, 1]
    weight:         float           # from MLSConfig
    weighted_score: float           # score × weight
    confidence:     float           # [0, 1] — component reliability
    explanation:    str             # one-line description
    evidence:       Dict[str, Any]  # raw inputs that drove this score
```

**Component names (fixed order):**  
`regime_context`, `volatility_context`, `liquidity_context`, `participation_context`,  
`sector_context`, `institutional_context`, `global_context`, `risk_context`

---

### `ContextHistory`

Ordered list of `MarketContext` objects (oldest first).

```python
@dataclass
class ContextHistory:
    contexts: List[MarketContext]

    def latest(self) -> Optional[MarketContext]: ...
    def to_dict(self)  -> Dict[str, Any]: ...
```

---

### `ContextDrift`

Measured change between two consecutive evaluations.

```python
@dataclass
class ContextDrift:
    from_date:           str        # ISO date of older context
    to_date:             str        # ISO date of newer context
    score_delta:         float      # context_score(new) − context_score(old)
    regime_changed:      bool       # True if regime label changed
    drifting_components: List[str]  # names of components that changed ≥ 0.10
    drift_magnitude:     float      # mean absolute component delta [0, 1]
    explanation:         str        # human-readable drift summary
```

---

### `ContextStatistics`

Aggregate statistics over a batch of `MarketContext` evaluations.

```python
@dataclass
class ContextStatistics:
    evaluation_date:        str
    total_evaluations:      int
    avg_context_score:      float
    max_context_score:      float
    min_context_score:      float
    avg_confidence:         float
    avg_stability:          float
    most_volatile_component: str             # component with highest score range
    regime_distribution:    Dict[str, int]   # regime → count
    high_context_count:     int              # score ≥ mcie_high_context_threshold
    low_context_count:      int              # score ≤ mcie_low_context_threshold
```

---

## Exceptions

| Exception | Raised when |
|---|---|
| `MCIEError` | Base class for all MCIE errors |
| `MCIEInputError` | Invalid or incompatible input passed to MCIEngine |

---

## Pure Helper Functions

Importable directly from `market_learning.mcie_engine` for unit testing.

| Function | Signature | Description |
|---|---|---|
| `_clamp` | `(v, lo=0.0, hi=1.0) → float` | Clamp to `[lo, hi]` |
| `_mean` | `(xs: List[float]) → float` | Mean; 0.0 for empty list |
| `_make_context_id` | `(timestamp_iso, evaluation_date) → str` | Deterministic context ID |
| `_score_regime` | `(regime_str) → float` | Regime clarity score |
| `_score_volatility` | `(vix, vix_low, vix_med, vix_high, vix_extreme) → float` | VIX-based score |
| `_score_liquidity` | `(breadth, fii_dii) → float` | Liquidity from flows + breadth |
| `_score_sector` | `(sector_flows) → float` | Fraction of positive sectors |
| `_score_institutional` | `(fii_dii) → float` | FII/DII institutional score |
| `_score_global` | `(global_sentiment_score, global_bias) → float` | Global context score |
| `_score_risk` | `(pcr, vix, pcr_lo, pcr_hi, …) → float` | Combined PCR+VIX risk score |

---

## Quick-Start Example

```python
from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from market_learning import MCIEngine
from datetime import datetime

engine = MCIEngine()

# Build or receive a MarketSnapshot from the trading pipeline
snapshot = MarketSnapshot(
    timestamp=datetime(2026, 8, 4, 9, 0),
    indices={},
    regime=RegimeLabel.BULL_TREND,
    volatility=VolatilityLevel.LOW,
    vix=14.5,
    market_breadth=0.72,
    pcr=0.95,
    global_sentiment_score=0.30,
    global_bias="bullish",
)

# Evaluate once
ctx = engine.evaluate(snapshot)
print(f"Context score: {ctx.context_score:.3f}")     # e.g. 0.780
print(f"Confidence:    {ctx.confidence:.0%}")         # e.g. 60%
print(f"Stability:     {ctx.stability:.0%}")          # 50% on first call

# Components
for comp in ctx.components:
    print(f"  {comp.name:<25} {comp.score:.3f}  (w={comp.weight})")

# Statistics after multiple evaluations
for snap in daily_snapshots:
    engine.evaluate(snap)

stats = engine.statistics()
print(f"Avg score: {stats.avg_context_score:.3f}")
print(f"High days: {stats.high_context_count}")
print(f"Top regime: {max(stats.regime_distribution, key=stats.regime_distribution.get)}")

# Drift detection
d = engine.drift()
if d and d.regime_changed:
    print(f"Regime changed! Drifting: {d.drifting_components}")
```

---

## Serialisation

```python
d   = ctx.to_dict()               # → dict (JSON-safe)
ctx2 = MarketContext.from_dict(d)  # → MarketContext
assert ctx2.context_score == ctx.context_score

d2  = drift.to_dict()
d3  = ContextDrift.from_dict(d2)
assert d3.drift_magnitude == drift.drift_magnitude
```
