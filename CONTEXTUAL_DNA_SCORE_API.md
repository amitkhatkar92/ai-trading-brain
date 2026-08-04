# Contextual DNA Score — API Reference
## MLS Phase 5A.1: CDSEngine

---

## Imports

```python
from market_learning import (
    CDSEngine,
    CDSLibraryResult, DNAContextStatistics,
    ContextualDNAScore, DNAContextContribution, DNAContextEvidence,
    DNAContextSimilarity, DNAContextProfile, DNAContextHistory,
    DNARelevance, ContextStabilityLabel,
    CDSError, CDSInputError,
    # Inputs (unchanged)
    ConsensusLibrary,
    MarketContext,     # from MCIEngine.evaluate()
    MLSConfig,
)
```

---

## CDSEngine

### `__init__(config=None, mci_engine=None)`

```python
engine = CDSEngine()                              # default MLSConfig
engine = CDSEngine(config=MLSConfig(...))          # custom thresholds/weights
engine = CDSEngine(mci_engine=mci)                # reuse pre-warmed MCIEngine
```

When `mci_engine` is provided, it is available for optional context evaluation.
CDSEngine maintains an in-memory context history for historical analogue search.

---

### `evaluate_dna(dna, context, snapshot=None, evaluation_date=None, library_id="") → ContextualDNAScore`

Evaluate contextual relevance of a single `ConsensusDNA`.

| Parameter | Type | Description |
|---|---|---|
| `dna` | `ConsensusDNA` | DNA characteristic to evaluate |
| `context` | `MarketContext` | Current market context (from MCIEngine) |
| `snapshot` | `MarketSnapshot` | Optional — enriches raw evidence capture |
| `evaluation_date` | `str` (ISO) | Optional date override |
| `library_id` | `str` | Source library identifier |

**Returns:** `ContextualDNAScore`

```python
score = engine.evaluate_dna(dna, context, snapshot, "2026-08-04")

print(f"CDS:      {score.cds:.3f}")
print(f"Relevance: {score.relevance.value}")
print(f"Context:  {score.evidence.regime_at_eval} score={score.evidence.context_score_at_eval:.3f}")

for c in score.contributions:
    icon = "+" if c.supporting else "-"
    print(f"  {icon} {c.name:<22}  {c.score:.3f}  ({c.explanation})")
```

---

### `evaluate(library, context, snapshot=None, evaluation_date=None) → List[ContextualDNAScore]`

Evaluate all `INSTITUTIONAL` DNA in the library.

Uses `library.master_consensus` (state == INSTITUTIONAL only).
Context is stored once and shared across all DNA evaluations.

```python
scores = engine.evaluate(library, context, snapshot, "2026-08-04")
print(f"Evaluated {len(scores)} DNA characteristics")
```

---

### `evaluate_library(library, context, snapshot=None, evaluation_date=None) → CDSLibraryResult`

Full library evaluation — returns scores AND aggregate statistics.

```python
result = engine.evaluate_library(library, context, snapshot, "2026-08-04")

print(f"Library:       {result.library_id}")
print(f"Context:       {result.context_id} ({result.context_stability.value})")
print(f"Total DNA:     {result.statistics.total_dna}")
print(f"Highly Relevant: {result.statistics.highly_relevant_count}")
print(f"Most supported: {result.statistics.top_dna_feature} CDS={result.statistics.top_cds:.3f}")
```

---

### `top_supported_dna(results, n=10) → List[ContextualDNAScore]`

Return up to `n` results sorted by CDS descending.

```python
top10 = engine.top_supported_dna(scores, n=10)
for s in top10:
    print(f"{s.feature_name:<20} CDS={s.cds:.3f}  {s.relevance.value}")
```

---

### `least_supported_dna(results, n=10) → List[ContextualDNAScore]`

Return up to `n` results sorted by CDS ascending (weakest first).

---

### `historical_matches(context, top_n=None) → List[DNAContextSimilarity]`

Find historical contexts most similar to the current context.

Uses cosine similarity over the 8-component MCIE score vector.

```python
matches = engine.historical_matches(context, top_n=5)
for m in matches:
    print(f"{m.analogue_date} ({m.regime}) sim={m.similarity_score:.3f}")
    print(f"  Matched: {', '.join(m.matched_dimensions)}")
    print(f"  {m.explanation}")
```

---

### `statistics(results, evaluation_date="", library_id="") → DNAContextStatistics`

Aggregate statistics over a batch of `ContextualDNAScore` results.

```python
stats = engine.statistics(scores, "2026-08-04", library.library_id)
print(f"Highly relevant: {stats.highly_relevant_count}")
print(f"Avg CDS:         {stats.avg_cds:.3f}")
print(f"Most supported:  {stats.top_dna_feature}")
```

---

## Data Classes

### `ContextualDNAScore`

```python
@dataclass
class ContextualDNAScore:
    evaluation_id:               str           # "CDS-{sha256[:8]}" — deterministic
    dna_id:                      str           # ConsensusDNA.consensus_id
    feature_name:                str
    direction:                   str           # SeparationDirection.value
    evaluation_date:             str           # ISO date
    cds:                         float         # [0, 1] overall CDS
    relevance:                   DNARelevance
    contributions:               List[DNAContextContribution]  # always 10
    supporting_dimensions:       List[str]     # contribution names where score >= 0.50
    conflicting_dimensions:      List[str]     # contribution names where score <  0.50
    context_stability_label:     ContextStabilityLabel
    historical_similarity_score: float         # [0, 1]
    historical_matches:          List[DNAContextSimilarity]
    evidence:                    DNAContextEvidence
    explanation:                 str
    confidence:                  float         # [0, 1]
    library_id:                  str
    evaluated_at:                str           # ISO datetime
```

---

### `DNAContextContribution`

One of the 10 named match dimensions.

```python
@dataclass
class DNAContextContribution:
    name:           str             # "regime_match" | "volatility_match" | ...
    score:          float           # [0, 1]
    weight:         float           # configured weight
    weighted_score: float           # score × weight
    supporting:     bool            # True if score >= 0.50
    explanation:    str             # one-line with score value
    evidence:       Dict[str, Any]  # raw source values
```

**Ten fixed names (always present):**
`regime_match`, `volatility_match`, `sector_match`, `breadth_match`,
`liquidity_match`, `institutional_match`, `global_match`,
`freshness_match`, `stability_match`, `historical_match`

---

### `DNAContextEvidence`

Complete reproducibility bundle.

```python
@dataclass
class DNAContextEvidence:
    evaluation_id:              str
    dna_id:                     str
    feature_name:               str
    direction:                  str
    regime_at_eval:             str
    vix_at_eval:                float
    breadth_at_eval:            float
    context_score_at_eval:      float
    context_stability_at_eval:  float
    fii_net_at_eval:            float
    sector_score_at_eval:       float
    global_sentiment_at_eval:   float
    dna_regime_counts:          Dict[str, int]
    dna_evidence_count:         int
    dna_last_seen:              str
    dna_replication_freq:       float
    dna_temporal_stability:     float
    dna_regime_consistency:     float
    dna_sector_consistency:     float
```

---

### `DNAContextSimilarity`

One historical context analogue.

```python
@dataclass
class DNAContextSimilarity:
    analogue_id:        str         # MarketContext.context_id (starts "MCE-")
    analogue_date:      str         # ISO date
    similarity_score:   float       # cosine similarity [0, 1]
    context_score:      float       # historical context quality score
    regime:             str         # historical regime label
    explanation:        str         # why today resembles this context
    matched_dimensions: List[str]   # component names with |delta| < 0.20
```

---

### `DNAContextProfile`

Derived summary from a `ContextualDNAScore`.

```python
profile = DNAContextProfile.from_score(score)

print(profile.regime_affinity)     # {"bull_trend": 0.533, "volatile": 0.067, ...}
print(profile.strong_regimes)      # regimes where fraction >= 0.50
print(profile.weak_regimes)        # regimes where fraction < 0.20
print(profile.top_contribution)    # name of highest weighted_score contribution
print(profile.supporting_count)    # number of supporting dimensions
```

---

### `DNAContextHistory`

CDS trend analysis built from multiple evaluations of the same DNA.

```python
history = DNAContextHistory.from_scores([score_t1, score_t2, score_t3, ...])

print(f"Trend:    {history.cds_trend}")       # "IMPROVING" | "DECLINING" | "STABLE"
print(f"Slope:    {history.cds_trend_slope}") # signed delta per observation period
print(f"Avg CDS:  {history.avg_cds:.3f}")
print(f"Latest:   {history.latest_cds:.3f}")
```

---

### `CDSLibraryResult`

```python
@dataclass
class CDSLibraryResult:
    library_id:        str
    evaluation_date:   str
    scores:            List[ContextualDNAScore]
    statistics:        DNAContextStatistics
    context_id:        str                     # MarketContext.context_id used
    context_stability: ContextStabilityLabel
    evaluated_at:      str
```

---

### `DNAContextStatistics`

```python
@dataclass
class DNAContextStatistics:
    evaluation_date:            str
    library_id:                 str
    total_dna:                  int
    highly_relevant_count:      int
    relevant_count:             int
    neutral_count:              int
    weak_count:                 int
    irrelevant_count:           int
    deprecated_count:           int
    avg_cds:                    float
    top_dna_id:                 Optional[str]
    top_dna_feature:            Optional[str]
    top_cds:                    float
    least_dna_id:               Optional[str]
    least_dna_feature:          Optional[str]
    least_cds:                  float
    avg_supporting_dimensions:  float      # avg count of supporting dims per DNA
    avg_historical_similarity:  float
    dominant_context_stability: str        # ContextStabilityLabel.value
```

---

## Enumerations

### `DNARelevance`

| Value | CDS Range |
|---|---|
| `HIGHLY_RELEVANT` | ≥ 0.75 |
| `RELEVANT` | ≥ 0.55 |
| `NEUTRAL` | ≥ 0.40 |
| `WEAK` | ≥ 0.25 |
| `IRRELEVANT` | ≥ 0.10 |
| `DEPRECATED` | < 0.10 |

### `ContextStabilityLabel`

| Value | (1 − stability) |
|---|---|
| `STABLE` | < 0.05 |
| `CHANGING` | < 0.15 |
| `RAPIDLY_CHANGING` | < 0.25 |
| `UNSTABLE` | < 0.35 |
| `DRIFTING` | ≥ 0.35 |

---

## Exceptions

| Exception | Raised when |
|---|---|
| `CDSError` | Base class |
| `CDSInputError` | Invalid input supplied to CDSEngine |

---

## Pure Helper Functions

Importable from `market_learning.cds_engine` for unit testing.

| Function | Signature | Description |
|---|---|---|
| `_clamp` | `(v, lo, hi) → float` | Clamp to [lo, hi] |
| `_mean` | `(xs) → float` | Mean; 0.0 for empty |
| `_make_cds_id` | `(dna_id, date) → str` | Deterministic "CDS-..." ID |
| `_get_ctx_score` | `(context, name) → float` | Extract MCIE component score |
| `_score_regime_match` | `(regime_consistency, regime_fraction, ctx) → float` | Regime dimension |
| `_score_volatility_match` | `(temporal_stability, vol_ctx) → float` | Volatility dimension |
| `_score_sector_match` | `(sector_consistency, sector_ctx) → float` | Sector dimension |
| `_score_breadth_match` | `(feature_persistence, breadth_ctx) → float` | Breadth dimension |
| `_score_liquidity_match` | `(evidence_count, liq_ctx) → float` | Liquidity dimension |
| `_score_institutional_match` | `(regime_consistency, inst_ctx) → float` | Institutional dimension |
| `_score_global_match` | `(temporal_stability, global_ctx) → float` | Global dimension |
| `_score_freshness` | `(last_seen, eval_date, days) → float` | Freshness dimension |
| `_score_stability_match` | `(replication_frequency, stability) → float` | Stability dimension |
| `_cosine_similarity` | `(a, b) → float` | Cosine similarity |
| `_classify_relevance` | `(cds, cfg) → DNARelevance` | Relevance classification |
| `_classify_stability` | `(stability, cfg) → ContextStabilityLabel` | Stability classification |

---

## Backward Compatibility

All existing PMCI, MCIE, and CAPMCIEngine methods remain unchanged.
CDS is a new layer — it does not modify any existing APIs.

---

## Quick-Start Example

```python
from market_learning import CDSEngine, MLSConfig
from market_learning import MCIEngine    # optional: compute context

# 1. Get market context from MCIEngine (Phase 5A)
mci = MCIEngine()
context = mci.evaluate(market_snapshot)

# 2. Create CDSEngine (reuse MCIEngine for history consistency)
engine = CDSEngine(mci_engine=mci)

# 3. Evaluate full library
result = engine.evaluate_library(library, context, market_snapshot, "2026-08-04")

# 4. See top-supported DNA
for score in engine.top_supported_dna(result.scores, n=5):
    print(f"{score.feature_name:<20} CDS={score.cds:.3f}  {score.relevance.value}")
    for c in score.contributions:
        icon = "+" if c.supporting else "-"
        print(f"    {icon} {c.name:<22}  {c.score:.3f}")

# 5. See historical analogues
for match in engine.historical_matches(context, top_n=3):
    print(f"Analogue: {match.analogue_date} ({match.regime}) sim={match.similarity_score:.3f}")

# 6. Serialise
d = result.scores[0].to_dict()
score_back = ContextualDNAScore.from_dict(d)
assert score_back.cds == result.scores[0].cds

# 7. Build DNA profile
profile = DNAContextProfile.from_score(result.scores[0])
print(f"Strong regimes: {profile.strong_regimes}")
print(f"Top contribution: {profile.top_contribution}")
```
