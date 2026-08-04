# Platform Intelligence Gateway API Reference
## R-001 Phase 1: PlatformIntelligenceGateway Public Interface

**Module:** `market_learning.pig_gateway`  
**Class:** `PlatformIntelligenceGateway`

---

## Instantiation

```python
from market_learning import PlatformIntelligenceGateway

# Default (creates all engines internally)
gw = PlatformIntelligenceGateway()

# Custom config
from market_learning import MLSConfig
config = MLSConfig(pig_high_threshold=0.75)
gw = PlatformIntelligenceGateway(config=config)

# Inject pre-warmed engines (recommended for production)
from market_learning import MCIEngine, PMCIEngine, CDSEngine, CAPMCIEngine
gw = PlatformIntelligenceGateway(
    config=config,
    mci_engine=MCIEngine(config),
    pmci_engine=PMCIEngine(config),
    cds_engine=CDSEngine(config),
    ca_pmci_engine=CAPMCIEngine(config),
)
```

---

## Core Query API

### `evaluate_symbol(symbol, observation, library, market_snapshot, repo, evaluation_date=None) -> PlatformIntelligence`

Evaluate one symbol against the full institutional intelligence stack.

```python
from market_learning import PlatformIntelligenceGateway, IDRRepository
from market_learning.market_observer_models import MarketObservation

gw = PlatformIntelligenceGateway()
intel = gw.evaluate_symbol(
    symbol="RELIANCE",
    observation=observation,      # MarketObservation from Phase 1
    library=library,              # ConsensusLibrary from Phase 4
    market_snapshot=market_snap,  # models.market_data.MarketSnapshot
    repo=idr_repo,                # IDRRepository (R-013)
    evaluation_date="2026-08-04", # optional ISO date override
)

# Primary output fields
print(intel.raw_pmci)               # [0,1] raw PMCI similarity
print(intel.ca_pmci)                # [0,1] context-adjusted PMCI
print(intel.cds_score)              # [0,1] contextual DNA support
print(intel.winner_dna_match)       # [0,1] winner DNA alignment
print(intel.loser_dna_match)        # [0,1] loser DNA presence
print(intel.evidence_count)         # matched DNA features
print(intel.confidence)             # [0,1] blended confidence
print(intel.dna_freshness)          # [0,1] DNA recency
print(intel.dna_drift)              # [0,1] DNA stability (1=drifting)
print(intel.institutional_confidence)  # [0,1] IDR institutional quality

# Market context
print(intel.context_score)          # [0,1] overall market context quality
print(intel.regime)                 # market regime label
print(intel.context_adjustment)     # CA-PMCI adjustment delta (signed)

# CDS summary
print(intel.cds_highly_relevant_count)  # highly relevant DNA count
print(intel.cds_relevant_count)         # relevant DNA count
print(intel.cds_total_dna)              # total evaluated DNA

# Explainability
for ev in intel.evidence:
    print(f"  [{ev.source}] {ev.component} = {ev.value:.3f}: {ev.explanation}")

# Simplified context for trading
rc = intel.recommendation_context
print(rc.winner_alignment)      # "HIGH" | "MEDIUM" | "LOW"
print(rc.context_support)       # "STRONG" | "MODERATE" | "WEAK"
print(rc.intelligence_quality)  # "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT"

# Confidence breakdown
c = intel.platform_confidence
print(f"overall={c.overall:.3f} pmci={c.pmci:.3f} ca={c.ca_pmci:.3f}")
```

**Raises:**
- `PlatformGatewayInputError` — if symbol is empty or any required argument is None

---

### `evaluate_universe(daily_snapshot, library, market_snapshot, repo, evaluation_date=None) -> List[PlatformIntelligence]`

Evaluate all symbols in a DailyMarketSnapshot. Context and CDS are computed once.

```python
results = gw.evaluate_universe(
    daily_snapshot=daily_snap,    # DailyMarketSnapshot (Phase 1)
    library=library,
    market_snapshot=market_snap,
    repo=idr_repo,
)

for intel in results:
    print(f"{intel.symbol}: raw={intel.raw_pmci:.3f} ca={intel.ca_pmci:.3f}")
```

- Failed individual symbols are skipped with a warning (not raised)
- Order of results matches `daily_snapshot.observations` order

**Raises:**
- `PlatformGatewayInputError` — if any required argument is None

---

### `get_context(market_snapshot, evaluation_date=None) -> MarketContext`

Evaluate and return the current market context.

```python
context = gw.get_context(market_snapshot)
print(context.context_score)   # [0,1]
print(context.regime)
print(context.stability)
```

Delegates directly to MCIEngine. Side effect: appends to MCIEngine history.

---

### `get_pmci(observation, library, evaluation_date=None, regime="unknown") -> PMCIResult`

Evaluate and return raw PMCI for one observation.

```python
pmci_result = gw.get_pmci(observation, library, regime="bull_trend")
print(pmci_result.pmci_score)
print(pmci_result.breakdown.matched_dna)
```

Delegates directly to PMCIEngine. Read-only.

---

### `get_cds(library, context, market_snapshot=None, evaluation_date=None) -> CDSLibraryResult`

Evaluate and return CDS for the full library against the current context.

```python
context = gw.get_context(market_snapshot)
cds = gw.get_cds(library, context)
print(cds.statistics.avg_cds)
print(cds.statistics.highly_relevant_count)
```

Delegates directly to CDSEngine. Read-only.

---

### `statistics(results) -> PlatformGatewayStatistics`

Return aggregate statistics for a batch of PlatformIntelligence results.

```python
results = gw.evaluate_universe(...)
stats = gw.statistics(results)

print(stats.total_symbols)
print(stats.avg_ca_pmci)
print(stats.avg_confidence)
print(stats.high_quality_count)   # ca_pmci >= pig_high_threshold
print(stats.top_symbol)
print(stats.regime)
```

Returns `PlatformGatewayStatistics.empty()` if `results` is empty.

---

## Output Models

### `PlatformIntelligence`

The primary output of `evaluate_symbol()`.

| Field | Type | Source |
|---|---|---|
| `result_id` | str | PIG-{sha256[:8]} deterministic |
| `symbol` | str | input |
| `evaluation_date` | str | ISO date |
| `evaluated_at` | str | ISO datetime wall-clock |
| `raw_pmci` | float | PMCIEngine |
| `ca_pmci` | float | CAPMCIEngine |
| `cds_score` | float | CDSEngine avg_cds |
| `winner_dna_match` | float | PMCI winner_match component |
| `loser_dna_match` | float | PMCI loser_match component |
| `evidence_count` | int | PMCI matched_dna count |
| `confidence` | float | blended from 4 sources |
| `dna_freshness` | float | PMCI dna_freshness component |
| `dna_drift` | float | 1 - CA-PMCI dna_context_stability |
| `institutional_confidence` | float | IDR statistics avg_confidence |
| `context_score` | float | MCIEngine |
| `regime` | str | MCIEngine |
| `context_adjustment` | float | CAPMCIEngine (signed delta) |
| `cds_highly_relevant_count` | int | CDSEngine |
| `cds_relevant_count` | int | CDSEngine |
| `cds_total_dna` | int | CDSEngine |
| `evidence` | List[PlatformEvidence] | 11 items covering all fields |
| `platform_confidence` | PlatformConfidence | 4-way confidence breakdown |
| `recommendation_context` | PlatformRecommendationContext | simplified for trading |
| `explanation` | str | full narrative |
| `pmci_result` | PMCIResult | original PMCI result |
| `ca_pmci_result` | CAPMCIResult | original CA-PMCI result |
| `market_context` | MarketContext | original context |

---

### `PlatformEvidence`

One traceable item explaining a single output score.

| Field | Type | Notes |
|---|---|---|
| `source` | str | "PMCI" \| "CA-PMCI" \| "CDS" \| "IDR" \| "MCIE" |
| `component` | str | named component within the source |
| `value` | float | the score value |
| `explanation` | str | one-line human-readable |
| `raw` | Dict[str, Any] | original inputs from source |

Evidence items cover these 11 components:
`raw_pmci`, `ca_pmci`, `cds_score`, `winner_dna_match`, `loser_dna_match`,
`evidence_count`, `context_score`, `dna_freshness`, `dna_drift`,
`institutional_confidence`, `context_adjustment`

---

### `PlatformConfidence`

Confidence breakdown by source.

| Field | Formula |
|---|---|
| `overall` | 0.40×pmci + 0.35×ca_pmci + 0.15×context + 0.10×institutional |
| `pmci` | PMCIResult.confidence |
| `ca_pmci` | CAPMCIResult.confidence |
| `context` | MarketContext.confidence |
| `institutional` | IDR statistics avg_confidence |

---

### `PlatformRecommendationContext`

Simplified intelligence summary for trading module consumption.

| Field | Values |
|---|---|
| `winner_alignment` | "HIGH" / "MEDIUM" / "LOW" |
| `context_support` | "STRONG" / "MODERATE" / "WEAK" |
| `intelligence_quality` | "HIGH" / "MEDIUM" / "LOW" / "INSUFFICIENT" |
| `raw_pmci` | float [0,1] |
| `ca_pmci` | float [0,1] |
| `confidence` | float [0,1] |
| `institutional_confidence` | float [0,1] |

---

### `PlatformGatewayStatistics`

Aggregate stats over a universe evaluation batch.

| Field | Notes |
|---|---|
| `total_symbols` | count |
| `avg_raw_pmci` | mean raw PMCI across all symbols |
| `avg_ca_pmci` | mean CA-PMCI |
| `avg_confidence` | mean confidence |
| `avg_cds_score` | mean CDS (shared across all symbols) |
| `avg_evidence_count` | mean matched DNA features per symbol |
| `high_quality_count` | ca_pmci >= pig_high_threshold (0.70) |
| `low_quality_count` | ca_pmci <= pig_low_threshold (0.30) |
| `top_symbol` | symbol with highest ca_pmci |
| `top_ca_pmci` | ca_pmci of top symbol |
| `context_score` | market context score (shared) |
| `regime` | market regime label |

---

## Exceptions

| Exception | When raised |
|---|---|
| `PlatformGatewayError` | Base class for all PIG errors |
| `PlatformGatewayInputError` | Invalid input (None, empty string) |
| `PlatformGatewaySymbolNotFoundError` | Symbol absent from DailyMarketSnapshot |

---

## Config Fields (MLSConfig)

| Field | Default | Description |
|---|---|---|
| `pig_high_threshold` | 0.70 | CA-PMCI >= this -> HIGH quality signal |
| `pig_medium_threshold` | 0.45 | CA-PMCI >= this -> MEDIUM quality signal |
| `pig_low_threshold` | 0.30 | CA-PMCI <= this -> LOW quality signal |
