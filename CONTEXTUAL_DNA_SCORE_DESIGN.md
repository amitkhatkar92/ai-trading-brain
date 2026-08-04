# Contextual DNA Score — Design
## MLS Phase 5A.1: CDSEngine

---

## 1. Purpose

Contextual DNA Score (CDS) evaluates whether the current market environment
supports or weakens each verified DNA characteristic in the ConsensusLibrary.

CDS answers: *"How relevant is this DNA today?"*

CDS is a **reusable market-context intelligence layer** for the entire IIOS
platform.  Any component can query CDS to understand how well the current
market environment supports any institutional DNA pattern.

### What CDS is NOT

- CDS is **not** a trading score.
- CDS is **not** a prediction.
- CDS **never** changes PMCI scores, DNA, ARS, strategies, or thresholds.

---

## 2. Architecture Position

```
Phase 5   PMCIEngine  — stock similarity to Winner DNA
Phase 5A  MCIEngine   — market environment (8 context dimensions)
Phase 5A.1 CDSEngine ◀ HERE
               For each ConsensusDNA: how well does today's context support it?

Phase 5B  CAPMCIEngine — combines stock PMCI + market context → CA-PMCI
```

CDS reuses:
- **MCIEngine** (Phase 5A) — market context computation
- **DNAConsensusEngine** (Phase 4) — ConsensusLibrary source
- **MLSConfig** — all thresholds

CDS does NOT duplicate any context or DNA logic.

---

## 3. Primary Responsibility

For every `ConsensusDNA` in the library, determine whether today's market
supports it by evaluating **10 named match dimensions**.

---

## 4. Inputs

| Input | Source |
|---|---|
| `ConsensusLibrary` | DNAConsensusEngine (Phase 4) |
| `MarketContext` | MCIEngine.evaluate() (Phase 5A) |
| `MarketSnapshot` | Optional — enriches raw evidence capture |
| `evaluation_date` | ISO date string |

---

## 5. The 10 Match Dimensions

Every CDS is computed as a weighted sum of 10 independent match dimensions:

| # | Name | DNA Source | Context Source | Weight |
|---|---|---|---|---|
| 1 | `regime_match` | `regime_consistency` + `regime_counts` | `regime_context` | 0.20 |
| 2 | `sector_match` | `sector_consistency` | `sector_context` | 0.15 |
| 3 | `volatility_match` | `temporal_stability` | `volatility_context` | 0.15 |
| 4 | `breadth_match` | `feature_persistence` | `participation_context` | 0.12 |
| 5 | `liquidity_match` | `evidence_count` | `liquidity_context` | 0.10 |
| 6 | `institutional_match` | `regime_consistency` | `institutional_context` | 0.10 |
| 7 | `global_match` | `temporal_stability` | `global_context` | 0.08 |
| 8 | `freshness_match` | `last_seen` (age decay) | — | 0.05 |
| 9 | `stability_match` | `replication_frequency` | `context.stability` | 0.03 |
| 10 | `historical_match` | — | cosine similarity search | 0.02 |

**Sum of weights: 1.00**

---

## 6. Dimension Formulas

### Regime Match (weight 0.20)

Regime-agnostic DNA (consistency ≥ 0.80) benefits from any clear regime:
```
score = clamp(0.50 + regime_ctx_score × 0.50)
```

Regime-specific DNA scores by fraction of history in current regime:
```
regime_fraction = regime_counts[current_regime] / sum(regime_counts)
score = clamp(regime_fraction × 0.70 + regime_ctx_score × 0.30)
```

### Volatility Match (weight 0.15)
```
score = clamp(temporal_stability × 0.40 + volatility_ctx_score × 0.60)
```
Stable DNA (high temporal_stability) works in any volatility environment.
Unstable DNA needs low VIX (high volatility_ctx_score) to be reliable.

### Sector Match (weight 0.15)
```
score = clamp(sector_consistency × 0.40 + sector_ctx_score × 0.60)
```

### Breadth Match (weight 0.12)
```
score = clamp(feature_persistence × 0.30 + breadth_ctx_score × 0.70)
```
DNA that appears persistently benefits from wide market participation.

### Liquidity Match (weight 0.10)
```
evidence_proxy = clamp(evidence_count / 50.0)    # saturates at 50 observations
score = clamp(evidence_proxy × 0.30 + liquidity_ctx_score × 0.70)
```

### Institutional Match (weight 0.10)
```
score = clamp(regime_consistency × 0.40 + institutional_ctx_score × 0.60)
```

### Global Match (weight 0.08)
```
score = clamp(temporal_stability × 0.30 + global_ctx_score × 0.70)
```

### Freshness Match (weight 0.05)
```
age_days = (evaluation_date − dna.last_seen).days
score = clamp(1.0 − age_days / cds_freshness_days)
```
Linear decay from 1.0 (today) to 0.0 at `cds_freshness_days` = 30 days.

### Stability Match (weight 0.03)
```
score = clamp(replication_frequency × 0.40 + context.stability × 0.60)
```
Replicating DNA + stable context = reinforced confidence.

### Historical Match (weight 0.02)
```
score = mean(cosine_similarity(current_context_vector, historical_vector_i))
      for top-N most similar past contexts (default 0.5 when no history)
```

---

## 7. CDS Formula

```
CDS = Σ(score_i × weight_i)  for i ∈ 10 dimensions
CDS = clamp(CDS, 0.0, 1.0)
```

---

## 8. DNA Relevance Classification

| Class | Threshold | Meaning |
|---|---|---|
| `HIGHLY_RELEVANT` | CDS ≥ 0.75 | DNA strongly supported by current context |
| `RELEVANT` | CDS ≥ 0.55 | DNA supported by current context |
| `NEUTRAL` | CDS ≥ 0.40 | Context neither supports nor opposes |
| `WEAK` | CDS ≥ 0.25 | Context weakly opposes this DNA |
| `IRRELEVANT` | CDS ≥ 0.10 | Context strongly opposes this DNA |
| `DEPRECATED` | CDS < 0.10 | DNA should not be used in current context |

---

## 9. Context Stability Classification

Based on `(1 − context.stability)` = how much the context has changed:

| Class | Delta threshold | Meaning |
|---|---|---|
| `STABLE` | < 0.05 | Market context almost unchanged |
| `CHANGING` | < 0.15 | Noticeable context shift |
| `RAPIDLY_CHANGING` | < 0.25 | Context shifting quickly |
| `UNSTABLE` | < 0.35 | Context highly unstable |
| `DRIFTING` | ≥ 0.35 | Context has fundamentally changed |

---

## 10. Historical Analogue Search

CDSEngine maintains an in-memory deque of historical context vectors
(up to `cds_max_history_size = 200` entries).

On every `evaluate_dna()` / `evaluate()` call, the current MarketContext
vector is stored (deduplicated by `context_id`).

For each query, the engine searches for historically similar contexts:

```
context_vector = [component.score for component in sorted(context.components)]
for each stored entry:
    similarity = cosine_similarity(current_vector, stored_vector)
    matched_dims = [dim where |current_score - stored_score| < 0.20]
```

The `historical_match` dimension score is the mean cosine similarity of the
top-N analogues (default: 0.5 when no history exists).

### Explainability

Every `DNAContextSimilarity` explains:
- The historical date and regime
- The cosine similarity score
- Which specific dimensions aligned (matched_dimensions)
- A human-readable explanation

---

## 11. Supporting vs Conflicting Dimensions

A dimension is **supporting** if `score ≥ 0.50` and **conflicting** if `score < 0.50`.

```
supporting_dimensions  = [c.name for c in contributions if c.supporting]
conflicting_dimensions = [c.name for c in contributions if not c.supporting]
```

The explanation field prominently lists the top 3 supporting and top 3 conflicting
dimensions, enabling quick human review.

---

## 12. Confidence

```
evidence_conf = clamp(dna.evidence_count / 20.0)
confidence    = clamp((context.confidence + evidence_conf) / 2.0)
```

- `context.confidence`: MCIE data richness (0.60 base, +0.20 FII, +0.20 sectors)
- `evidence_conf`: saturates at 20 observations (institutional threshold)

---

## 13. New Objects

| Object | Purpose |
|---|---|
| `ContextualDNAScore` | Main result: CDS + 10 contributions + relevance + history |
| `DNAContextContribution` | One match dimension score with evidence and explanation |
| `DNAContextEvidence` | Complete raw evidence for one CDS evaluation |
| `DNAContextSimilarity` | One historical context analogue (cosine similarity) |
| `DNAContextProfile` | Derived regime affinity and supporting count summary |
| `DNAContextHistory` | Trend analysis over multiple CDS evaluations for one DNA |
| `CDSLibraryResult` | Full library evaluation: scores + statistics |
| `DNAContextStatistics` | Aggregate counts and averages for a batch |
| `DNARelevance` | Enum: HIGHLY_RELEVANT → DEPRECATED |
| `ContextStabilityLabel` | Enum: STABLE → DRIFTING |
| `CDSError` | Base exception |
| `CDSInputError` | Invalid input exception |

---

## 14. Query API

```python
engine = CDSEngine(config, mci_engine)

# Single DNA
score  = engine.evaluate_dna(dna, context, snapshot, evaluation_date, library_id)

# Full library (INSTITUTIONAL DNA only)
scores = engine.evaluate(library, context, snapshot, evaluation_date)

# Library with statistics
result = engine.evaluate_library(library, context, snapshot, evaluation_date)

# Ranking
top    = engine.top_supported_dna(scores, n=10)
least  = engine.least_supported_dna(scores, n=10)

# Historical analogues
matches = engine.historical_matches(context, top_n=5)

# Aggregate statistics
stats  = engine.statistics(scores, evaluation_date, library_id)
```

---

## 15. Reproducibility

| Invariant | Guarantee |
|---|---|
| Deterministic ID | Same `(dna_id, evaluation_date)` → same `evaluation_id` ("CDS-{sha256[:8]}") |
| Non-mutating | Never modifies inputs |
| Bounded score | CDS ∈ [0.0, 1.0] always |
| Fixed contributions | `len(contributions) == 10` always |
| Supporting + conflicting == 10 | Always |

---

## 16. Configuration Summary (`MLSConfig` Phase 5A.1 fields)

```python
# CDS dimension weights — must sum to 1.0
cds_w_regime:         float = 0.20
cds_w_sector:         float = 0.15
cds_w_volatility:     float = 0.15
cds_w_breadth:        float = 0.12
cds_w_liquidity:      float = 0.10
cds_w_institutional:  float = 0.10
cds_w_global:         float = 0.08
cds_w_freshness:      float = 0.05
cds_w_stability:      float = 0.03
cds_w_historical:     float = 0.02

# Relevance thresholds
cds_highly_relevant:  float = 0.75
cds_relevant:         float = 0.55
cds_neutral:          float = 0.40
cds_weak:             float = 0.25
cds_irrelevant:       float = 0.10

# Operational
cds_freshness_days:   int   = 30
cds_max_history_size: int   = 200
cds_top_analogues:    int   = 5

# Context stability thresholds (1 - context.stability)
cds_stable_threshold:            float = 0.05
cds_changing_threshold:          float = 0.15
cds_rapidly_changing_threshold:  float = 0.25
cds_unstable_threshold:          float = 0.35
```

---

## 17. Module Map

| File | Role |
|---|---|
| `market_learning/cds_engine.py` | CDSEngine class; pure helpers (all directly importable) |
| `market_learning/cds_models.py` | All data classes, enums, and exceptions |
| `market_learning/mls_config.py` | Phase 5A.1 config fields |
| `market_learning/__init__.py` | Package-level exports |
| `test_cds_engine.py` | 90-test suite (90/90 pass) |
