# PMCI Engine — API Reference
## MLS Phase 5: Pre-Movement Consensus Intelligence

---

## Imports

```python
from market_learning import (
    PMCIEngine,
    PMCIResult, PMCIComponent, PMCIEvidence, PMCIBreakdown, PMCIStatistics,
    PMCIError, PMCIInputError,
)
```

---

## PMCIEngine

### `__init__(config=None)`

```python
engine = PMCIEngine()                          # default MLSConfig
engine = PMCIEngine(config=MLSConfig(...))     # custom weights / thresholds
```

The engine is stateless and read-only.  It may be shared across threads.

---

### `evaluate(observation, library, evaluation_date=None, regime="unknown") → PMCIResult`

Evaluate one `MarketObservation` against the `ConsensusLibrary`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `observation` | `MarketObservation` | required | Feature vector for one symbol |
| `library` | `ConsensusLibrary` | required | Phase 4 output; never modified |
| `evaluation_date` | `str` (ISO) | `None` → obs timestamp date | Override the evaluation date |
| `regime` | `str` | `"unknown"` | Market regime label (stored, not scored) |

**Returns:** `PMCIResult`

```python
result = engine.evaluate(obs, library, evaluation_date="2026-08-04", regime="bull_trend")
print(result.pmci_score)          # e.g. 0.723
print(result.explanation)         # human-readable summary
```

---

### `evaluate_universe(observations, library, evaluation_date=None, regime="unknown") → List[PMCIResult]`

Evaluate a list of observations against the same library.  
Order of results matches order of input.  Failed evaluations are skipped with a warning.

```python
results = engine.evaluate_universe(obs_list, library, evaluation_date="2026-08-04")
print(f"{len(results)} stocks evaluated")
```

---

### `evaluate_symbol(symbol, snapshot, library, evaluation_date=None) → Optional[PMCIResult]`

Evaluate a named symbol found within a `DailyMarketSnapshot`.

- Returns `None` if the symbol is not present in the snapshot.
- Uses `snapshot.regime` and `snapshot.trading_date` as context.
- `evaluation_date` overrides `snapshot.trading_date` if provided.

```python
result = engine.evaluate_symbol("TCS", snapshot, library)
if result is None:
    print("TCS not in snapshot")
else:
    print(result.pmci_score)
```

---

### `top_matches(results, n=10) → List[PMCIResult]`

Return the top-n results sorted by `pmci_score` descending.  
Returns all results if `len(results) <= n`.

```python
top5 = engine.top_matches(results, n=5)
for r in top5:
    print(r.symbol, r.pmci_score)
```

---

### `statistics(results) → PMCIStatistics`

Compute aggregate statistics over a batch of `PMCIResult` objects.  
Returns safe defaults (zeros, `None` top_symbol) for an empty list.

```python
stats = engine.statistics(results)
print(stats.avg_pmci, stats.high_similarity_count, stats.top_symbol)
```

---

## Data Classes

### `PMCIResult`

```python
@dataclass
class PMCIResult:
    result_id:        str              # "PMC-{sha256[:8]}" — deterministic
    symbol:           str
    evaluation_date:  str              # ISO date
    regime:           str              # stored from input
    pmci_score:       float            # [0, 1]
    components:       List[PMCIComponent]   # always 9 items
    breakdown:        PMCIBreakdown
    confidence:       float            # fraction of INSTITUTIONAL DNA present
    explanation:      str              # human-readable
    library_id:       str              # from ConsensusLibrary
    feature_count:    int              # obs.feature_count
    evaluated_at:     str              # ISO datetime of computation
```

**Methods:**  
- `to_dict() → dict` — JSON-serialisable  
- `from_dict(d) → PMCIResult` — deserialise

---

### `PMCIComponent`

One of the nine scored dimensions.

```python
@dataclass
class PMCIComponent:
    name:           str     # e.g. "winner_match"
    value:          float   # [0, 1]
    weight:         float   # from MLSConfig
    weighted_value: float   # value × weight
    matched_count:  int     # features contributing to this component
    explanation:    str     # human-readable
```

**Component names (fixed order):**  
`winner_match`, `loser_match`, `neutral_match`, `evidence_strength`,  
`regime_stability`, `sector_stability`, `confidence_trend`,  
`dna_freshness`, `knowledge_coverage`

---

### `PMCIEvidence`

One DNA feature evaluated against the observation.

```python
@dataclass
class PMCIEvidence:
    feature_name:     str
    direction:        str     # SeparationDirection.value
    stock_value:      float   # raw feature value from observation
    alignment:        float   # [0, 1] — from _align()
    consensus_score:  float   # from ConsensusDNA
    evidence_count:   int
    last_seen:        str     # ISO date
    consensus_state:  str     # ConsensusState.value
    contribution:     float   # alignment × consensus_score
    is_match:         bool    # alignment >= 0.50
    is_contradiction: bool    # alignment < 0.50
```

---

### `PMCIBreakdown`

Full DNA audit for one evaluation.

```python
@dataclass
class PMCIBreakdown:
    matched_dna:           List[PMCIEvidence]  # sorted by contribution desc
    missing_dna:           List[str]           # sorted alphabetically
    conflicting_dna:       List[PMCIEvidence]  # features that contradict winner DNA
    neutral_dna:           List[PMCIEvidence]  # NEUTRALS_* DNA
    total_institutional_dna: int               # count of INSTITUTIONAL DNA in library
    coverage_fraction:     float               # [0, 1]
```

---

### `PMCIStatistics`

Aggregate across a batch evaluation.

```python
@dataclass
class PMCIStatistics:
    evaluation_date:       str
    total_symbols:         int
    avg_pmci:              float
    max_pmci:              float
    min_pmci:              float
    high_similarity_count: int     # pmci_score >= pmci_high_similarity_threshold
    low_similarity_count:  int     # pmci_score <= pmci_low_similarity_threshold
    avg_winner_match:      float
    avg_loser_match:       float
    avg_coverage:          float
    top_symbol:            Optional[str]
    top_pmci:              float
```

---

## Exceptions

| Exception | Raised when |
|---|---|
| `PMCIError` | Base class for all PMCI errors |
| `PMCIInputError` | Invalid or incompatible inputs passed to evaluate |

---

## Pure Helper Functions

These functions are importable directly from `market_learning.pmci_engine` for testing.

| Function | Signature | Description |
|---|---|---|
| `_clamp` | `(v, lo=0.0, hi=1.0) → float` | Clamp to `[lo, hi]` |
| `_mean` | `(xs: List[float]) → float` | Mean; 0.0 for empty list |
| `_align` | `(value, direction: SeparationDirection) → float` | Feature alignment to winner direction |
| `_freshness` | `(last_seen, as_of, max_days) → float` | Linear decay freshness |
| `_make_pmci_id` | `(symbol, evaluation_date) → str` | Deterministic result ID |

---

## Quick-Start Example

```python
from market_learning import PMCIEngine, MLSConfig

engine = PMCIEngine()

# After Phase 4 produces a ConsensusLibrary and Phase 1 produces observations:
results = engine.evaluate_universe(today_observations, consensus_library,
                                   evaluation_date="2026-08-04",
                                   regime="bull_trend")

top = engine.top_matches(results, n=20)
stats = engine.statistics(results)

print(f"Evaluated {stats.total_symbols} stocks")
print(f"High similarity: {stats.high_similarity_count}")
print(f"Top match: {stats.top_symbol} → PMCI={stats.top_pmci:.3f}")

for r in top[:3]:
    matched = [e.feature_name for e in r.breakdown.matched_dna]
    print(f"  {r.symbol}: pmci={r.pmci_score:.3f}  matched={matched}")
```

---

## Serialisation

Every result can be serialised and deserialised without loss:

```python
d = result.to_dict()          # → dict (JSON-safe)
r = PMCIResult.from_dict(d)   # → PMCIResult
assert r.pmci_score == result.pmci_score
```
