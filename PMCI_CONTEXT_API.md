# PMCI Context API Reference
## MLS Phase 5B: Context-Aware PMCI Engine (CA-PMCI)

---

## Imports

```python
from market_learning import (
    CAPMCIEngine,
    CAPMCIResult, CAPMCIStatistics, ContextAdjustment,
    CAPMCIError, CAPMCIInputError,
    # Phase 5 (unchanged)
    PMCIEngine, PMCIResult,
    # Phase 5A (unchanged)
    MCIEngine, MarketContext,
)
```

---

## CAPMCIEngine

### `__init__(config=None, mci_engine=None)`

```python
engine = CAPMCIEngine()                             # default MLSConfig
engine = CAPMCIEngine(config=MLSConfig(...))         # custom thresholds/weights
engine = CAPMCIEngine(mci_engine=mci)               # reuse pre-warmed MCIEngine
```

When `mci_engine` is provided, it is reused for all `evaluate_context()` calls
(preserving drift/stability history). Otherwise a fresh `MCIEngine` is created
per call — suitable for stateless use.

---

### `evaluate_context(snapshot) → MarketContext`

Evaluate the current market context from a `MarketSnapshot`.

Returns a `MarketContext` (identical to `MCIEngine.evaluate(snapshot)`).

```python
from models.market_data import MarketSnapshot
ctx = engine.evaluate_context(snapshot)
print(ctx.context_score)    # e.g. 0.704
print(ctx.regime)           # e.g. "bull_trend"
```

---

### `evaluate_with_context(observation, library, snapshot, evaluation_date=None) → CAPMCIResult`

Full CA-PMCI evaluation for one stock.

| Parameter | Type | Description |
|---|---|---|
| `observation` | `MarketObservation` | Pre-move feature vector for one symbol |
| `library` | `ConsensusLibrary` | Institutional DNA knowledge base (Phase 4) |
| `snapshot` | `MarketSnapshot` | Current market snapshot (from `models.market_data`) |
| `evaluation_date` | `str` (ISO) | Optional date override |

**Returns:** `CAPMCIResult`

**Side effects:** None — inputs never modified.

```python
result = engine.evaluate_with_context(observation, library, snapshot)

print(f"Raw PMCI:    {result.raw_pmci:.3f}")
print(f"Context:     {result.context_score:.3f}")
print(f"Adjustment:  {result.context_adjustment:+.4f}")
print(f"CA-PMCI:     {result.ca_pmci:.3f}")

# Individual adjustments with explanations
for adj in result.adjustments:
    print(f"  {adj.name:<22} {adj.delta:+.4f}  {adj.explanation}")
```

**Output example:**
```
Raw PMCI:    0.830
Context:     0.704
Adjustment:  +0.0500
CA-PMCI:     0.880

  regime_match           +0.0400  Bull regime favours this DNA (+0.0400)
  volatility_match       +0.0300  Low VIX supports this DNA (+0.0300)
  sector_match           -0.0200  Sector currently lagging — penalises this DNA (-0.0200)
  context_stability      +0.0200  Context stable — reinforces confidence (+0.0200)
  dna_freshness          +0.0100  DNA fresh in favorable context — amplifies weight (+0.0100)
```

---

### `evaluate_universe_with_context(observations, library, snapshot, evaluation_date=None) → List[CAPMCIResult]`

Batch CA-PMCI for all stocks in a universe.

The market context is computed **once** and shared across all evaluations
(efficient: `O(1)` MCIE evaluations regardless of universe size).

```python
results = engine.evaluate_universe_with_context(
    observations, library, snapshot, "2026-08-04"
)

# Sort by CA-PMCI descending
top10 = sorted(results, key=lambda r: r.ca_pmci, reverse=True)[:10]
for r in top10:
    print(f"{r.symbol:<12} raw={r.raw_pmci:.3f} "
          f"adj={r.context_adjustment:+.4f} ca={r.ca_pmci:.3f}")
```

---

### `statistics(results) → CAPMCIStatistics`

Aggregate statistics for a batch of `CAPMCIResult` objects.

```python
stats = engine.statistics(results)
print(stats.total_symbols)          # 47
print(stats.avg_raw_pmci)           # 0.520
print(stats.avg_ca_pmci)            # 0.618  (bull context: avg ca > avg raw)
print(stats.avg_context_adjustment) # +0.098
print(stats.most_improved_symbol)   # "TATASTEEL"
print(stats.most_degraded_symbol)   # "HINDPETRO"
```

---

## Data Classes

### `CAPMCIResult`

```python
@dataclass
class CAPMCIResult:
    result_id:       str     # "CAP-{sha256[:8]}" — deterministic per (symbol, date)
    symbol:          str
    evaluation_date: str     # ISO date

    # Raw PMCI
    raw_pmci:        float   # PMCIResult.pmci_score [0, 1]

    # Market context
    context_score:   float   # MarketContext.context_score [0, 1]
    context_id:      str     # MarketContext.context_id ("MCE-...")
    regime:          str     # current market regime label

    # New context components (all [0, 1])
    context_match_score:       float  # 0.40×regime + 0.35×sector + 0.25×vol alignment
    dna_context_stability:     float  # mean(regime_q, sector_q, vol_q)
    dna_regime_match:          float  # DNA regime_consistency from PMCI
    dna_sector_match:          float  # DNA sector_consistency from PMCI
    dna_volatility_match:      float  # DNA evidence_strength (resilience proxy)
    dna_freshness_weight:      float  # DNA recency from PMCI
    context_adjustment_factor: float  # [0,1]: 0.5=neutral, >0.5=net positive

    # Five named adjustments
    adjustments:        List[ContextAdjustment]  # always 5
    context_adjustment: float  # sum of deltas, clamped to ±0.30

    # Final
    ca_pmci:     float  # clamp(raw_pmci + context_adjustment, 0, 1)
    confidence:  float  # (pmci_confidence + mcie_confidence) / 2
    explanation: str    # full narrative including all adjustments

    # Source references
    pmci_result:   PMCIResult  # original full PMCIResult (preserved)
    library_id:    str
    feature_count: int
    evaluated_at:  str         # ISO datetime
```

---

### `ContextAdjustment`

One of the five named context adjustments.

```python
@dataclass
class ContextAdjustment:
    name:        str             # "regime_match" | "volatility_match" | ...
    delta:       float           # signed adjustment (+= reward, -= penalty)
    explanation: str             # one-line description with delta value
    evidence:    Dict[str, Any]  # source values used to compute this delta
```

**Five names (fixed order):**  
`regime_match`, `volatility_match`, `sector_match`, `context_stability`, `dna_freshness`

---

### `CAPMCIStatistics`

```python
@dataclass
class CAPMCIStatistics:
    evaluation_date:        str
    total_symbols:          int
    avg_raw_pmci:           float   # mean before context adjustment
    avg_ca_pmci:            float   # mean after context adjustment
    avg_context_adjustment: float   # mean of context_adjustment values
    avg_context_score:      float   # mean of MarketContext scores
    high_ca_pmci_count:     int     # ca_pmci ≥ ca_pmci_high_threshold
    low_ca_pmci_count:      int     # ca_pmci ≤ ca_pmci_low_threshold
    top_symbol:             Optional[str]   # highest ca_pmci
    top_ca_pmci:            float
    most_improved_symbol:   Optional[str]   # largest positive context_adjustment
    most_degraded_symbol:   Optional[str]   # most negative context_adjustment
```

---

## Exceptions

| Exception | Raised when |
|---|---|
| `CAPMCIError` | Base class for all CA-PMCI errors |
| `CAPMCIInputError` | Invalid input supplied to CAPMCIEngine |

---

## Pure Helper Functions

Importable from `market_learning.ca_pmci_engine` for unit testing.

| Function | Signature | Description |
|---|---|---|
| `_clamp` | `(v, lo=0.0, hi=1.0) → float` | Clamp to [lo, hi] |
| `_mean` | `(xs) → float` | Mean; 0.0 for empty list |
| `_make_ca_pmci_id` | `(symbol, evaluation_date) → str` | Deterministic CA-PMCI ID |
| `_extract_component` | `(result: PMCIResult, name: str) → float` | Extract PMCI component value |
| `_get_context_score` | `(context: MarketContext, name: str) → float` | Extract MCIE context score |
| `_compute_adj` | `(dna_quality, ctx_quality, weight, cap) → float` | One adjustment delta |

---

## Backward Compatibility

All existing `PMCIEngine` methods remain unchanged and fully operational:

```python
# Still works exactly as before — not affected by Phase 5B
raw = PMCIEngine(config).evaluate(observation, library, evaluation_date)
results = PMCIEngine(config).evaluate_universe(observations, library)
stats = PMCIEngine(config).statistics(results)
```

---

## Quick-Start Example

```python
from market_learning import CAPMCIEngine, MLSConfig

engine = CAPMCIEngine()

# Single stock evaluation
result = engine.evaluate_with_context(
    observation=observation,
    library=library,
    snapshot=market_snapshot,
    evaluation_date="2026-08-04",
)

print(f"Symbol:           {result.symbol}")
print(f"Raw PMCI:         {result.raw_pmci:.3f}")
print(f"Context:          {result.context_score:.3f}  ({result.regime})")
print(f"Context Adj:      {result.context_adjustment:+.4f}")
print(f"CA-PMCI:          {result.ca_pmci:.3f}")
print(f"Confidence:       {result.confidence:.0%}")
print()

# Detailed adjustment breakdown
print("Context adjustments:")
for adj in result.adjustments:
    print(f"  {adj.name:<22}  {adj.delta:+.4f}  {adj.explanation}")

# Batch universe evaluation
results = engine.evaluate_universe_with_context(
    observations, library, market_snapshot
)
stats = engine.statistics(results)
print(f"\nUniverse: {stats.total_symbols} stocks")
print(f"Avg raw PMCI:  {stats.avg_raw_pmci:.3f}")
print(f"Avg CA-PMCI:   {stats.avg_ca_pmci:.3f}")
print(f"Most improved: {stats.most_improved_symbol}")

# Serialisation
d = result.to_dict()
result2 = CAPMCIResult.from_dict(d)
assert result2.ca_pmci == result.ca_pmci
```
