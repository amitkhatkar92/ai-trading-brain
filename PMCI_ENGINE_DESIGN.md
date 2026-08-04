# PMCI Engine — Design Document
## MLS Phase 5: Pre-Movement Consensus Intelligence

---

## 1. Purpose

The PMCIEngine measures **how closely a stock's current feature vector resembles institutional Winner DNA** before any price movement occurs.

PMCI is a **read-only similarity score**, not a trade signal.  
It answers the single question: *"Does this stock look like a winner right now?"*

It is the downstream consumer of Phase 4 (DNAConsensusEngine) and the upstream evidence provider for the trading pipeline.

---

## 2. Position in the MLS Pipeline

```
Phase 1 — MarketObserver        → feature vectors (MarketObservation)
Phase 2 — PopulationClassifier  → winner / loser labels
Phase 3 — DNADiscoveryEngine    → winner DNA candidates (ARSFeature)
Phase 4 — DNAConsensusEngine    → validated institutional DNA (ConsensusLibrary)
Phase 5 — PMCIEngine  ◀ HERE   → similarity score (PMCIResult)
```

---

## 3. What PMCI Is Not

| Scope | Outside PMCI |
|---|---|
| Feature extraction | Phase 1 (MarketObserver) |
| Population labelling | Phase 2 (PopulationClassifier) |
| DNA discovery | Phase 3 (DNADiscoveryEngine) |
| DNA consensus building | Phase 4 (DNAConsensusEngine) |
| Trade execution / signalling | ExecutionEngine |
| Persistent state | Nothing — engine is stateless |

---

## 4. Inputs and Outputs

| Item | Type | Description |
|---|---|---|
| `observation` | `MarketObservation` | Current feature vector for one symbol |
| `library` | `ConsensusLibrary` | Phase 4 output; never modified |
| `evaluation_date` | `str` (ISO) | Override date; defaults to observation timestamp |
| `regime` | `str` | Market regime label; stored in result, not used in formula |
| **Returns** | `PMCIResult` | Score, 9 components, breakdown, explanation |

---

## 5. The Nine PMCI Components

Each component is a `[0, 1]` scalar with a weight from `MLSConfig`.

| # | Name | Weight | Meaning |
|---|---|---|---|
| 1 | `winner_match` | `pmci_w_winner = 0.35` | Weighted-average alignment of observed features with WINNERS_HIGHER / WINNERS_LOWER DNA |
| 2 | `loser_match` | `pmci_w_loser = 0.25` (**penalty**) | Complement: `1 - winner_match` when features present; 0 otherwise |
| 3 | `neutral_match` | `pmci_w_neutral = 0.02` | Alignment with NEUTRALS_HIGHER / NEUTRALS_LOWER DNA |
| 4 | `evidence_strength` | `pmci_w_evidence = 0.20` | Mean `consensus_score` of **matched** features only |
| 5 | `regime_stability` | `pmci_w_regime = 0.15` | Mean `regime_consistency` across all present winner DNA features |
| 6 | `sector_stability` | `pmci_w_sector = 0.10` | Mean `sector_consistency` across all present winner DNA features |
| 7 | `confidence_trend` | `pmci_w_trend = 0.07` | Fraction of present winner DNA with improving `confidence_trend` |
| 8 | `dna_freshness` | `pmci_w_freshness = 0.06` | Linear decay freshness of winner DNA features (window = `pmci_freshness_days`) |
| 9 | `knowledge_coverage` | `pmci_w_coverage = 0.05` | `(winner_features_present + neutral_features_present) / total_active_dna` |

**Sum-to-1 constraint:** Components 1, 3–9 sum to 1.0.  
The loser penalty is applied separately after the positive sum.

---

## 6. Scoring Formula

### Feature Alignment

Feature values are assumed to be normalised to `[0, 1]` by Phase 1.

```
_align(value, direction):
    v = clamp(value, 0, 1)
    if WINNERS_HIGHER or NEUTRALS_HIGHER:  return v
    if WINNERS_LOWER  or NEUTRALS_LOWER:   return 1.0 - v
```

### Winner Match (weighted by consensus_score)

For each winner DNA feature present in the observation:

```
contribution_i  = alignment_i × consensus_score_i
winner_match    = Σ contribution_i  /  Σ consensus_score_i
```

A feature is a **match** if `alignment ≥ 0.50`.  
A feature is a **contradiction** if `alignment < 0.50`.

### PMCI Formula

```
positive = (w_winner   × winner_match
          + w_evidence × evidence_strength
          + w_regime   × regime_stability
          + w_sector   × sector_stability
          + w_trend    × confidence_trend
          + w_freshness× dna_freshness
          + w_coverage × knowledge_coverage
          + w_neutral  × neutral_match)

penalty  = w_loser × loser_match

pmci     = clamp(positive − penalty, 0.0, 1.0)
```

---

## 7. DNA Freshness Decay

DNA freshness uses a linear decay over a configurable window (`pmci_freshness_days = 30`):

```
freshness = 1.0 − (days_since_last_seen / max_days)
freshness = clamp(freshness, 0.0, 1.0)
```

| `days_since_last_seen` | Freshness |
|---|---|
| 0 (same day) | 1.000 |
| 15 | 0.500 |
| 30 | 0.000 |
| > 30 | 0.000 (clamped) |

---

## 8. Meta-Confidence

The `PMCIResult.confidence` field is the fraction of **INSTITUTIONAL-state** DNA features present in the observation.  
Falls back to `knowledge_coverage` when no institutional DNA exists in the library.

---

## 9. PMCI Thresholds

| Threshold | Default | Purpose |
|---|---|---|
| `pmci_high_similarity_threshold` | 0.70 | Candidate for downstream attention |
| `pmci_low_similarity_threshold` | 0.30 | Likely loser-like; low priority |

---

## 10. DNA State Filtering

Only **active** ConsensusState values contribute to PMCI.  
`RETIRED` DNA is permanently excluded.

Active states: `DISCOVERED`, `REPLICATED`, `VERIFIED`, `INSTITUTIONAL`, `WEAKENING`, `DRIFTING`

---

## 11. Result Identity

Every `PMCIResult` has a deterministic `result_id`:

```
result_id = "PMC-" + sha256(f"{symbol}::{evaluation_date}")[:8]
```

The same symbol evaluated on the same date always produces the same ID.

---

## 12. Design Invariants

| Invariant | Guarantee |
|---|---|
| Read-only | `evaluate()` never mutates `library` or `observation` |
| Stateless | Each call is independent; no class-level mutable state |
| Bounded score | `pmci_score ∈ [0.0, 1.0]` always |
| Complement | `winner_match + loser_match = 1.0` when any winner DNA feature is observed |
| 9 components | `len(result.components) == 9` always |
| Empty safety | `evaluate()` with an empty library returns `pmci_score = 0.0` |

---

## 13. Configuration Summary (`MLSConfig` Phase 5 fields)

```python
pmci_w_winner:                  float = 0.35
pmci_w_evidence:                float = 0.20
pmci_w_regime:                  float = 0.15
pmci_w_sector:                  float = 0.10
pmci_w_trend:                   float = 0.07
pmci_w_freshness:               float = 0.06
pmci_w_coverage:                float = 0.05
pmci_w_neutral:                 float = 0.02
pmci_w_loser:                   float = 0.25   # penalty — NOT in sum-to-1
pmci_freshness_days:            int   = 30
pmci_feature_midpoint:          float = 0.50   # match / contradiction boundary
pmci_high_similarity_threshold: float = 0.70
pmci_low_similarity_threshold:  float = 0.30
```

---

## 14. Module Map

| File | Role |
|---|---|
| `market_learning/pmci_models.py` | Data classes: PMCIResult, PMCIComponent, PMCIEvidence, PMCIBreakdown, PMCIStatistics; exceptions |
| `market_learning/pmci_engine.py` | PMCIEngine class; pure helper functions: `_clamp`, `_mean`, `_align`, `_freshness`, `_make_pmci_id` |
| `market_learning/mls_config.py` | MLSConfig Phase 5 fields |
| `market_learning/__init__.py` | Package-level exports for all Phase 5 symbols |
| `test_pmci_engine.py` | 90-test suite (90/90 pass) |
