# PMCI Context Design
## MLS Phase 5B: Context-Aware PMCI Engine (CA-PMCI)

---

## 1. Purpose

CAPMCIEngine bridges the raw DNA similarity score produced by PMCIEngine with the
live market environment measured by MCIEngine, producing a **Context-Aware PMCI**
(CA-PMCI) score that reflects BOTH institutional Winner DNA AND the current market.

CA-PMCI answers: *"How strong is the DNA evidence for this stock in TODAY's market?"*

It adjusts raw PMCI upward when the market environment amplifies the DNA signal,
and downward when the market environment suppresses it.

---

## 2. Position in the MLS Pipeline

```
Phase 5  — PMCIEngine  → raw_pmci  (DNA similarity, market-blind)
Phase 5A — MCIEngine   → MarketContext (market environment score)
Phase 5B — CAPMCIEngine ◀ HERE
               raw_pmci + context_adjustment = CA-PMCI
```

CA-PMCI **consumes** Phase 5 and Phase 5A outputs.
It is a synthesis layer, not a new data source.

---

## 3. What CA-PMCI Is Not

| Scope | Outside CA-PMCI |
|---|---|
| Raw PMCI computation | Phase 5 (PMCIEngine) — unchanged |
| Market context evaluation | Phase 5A (MCIEngine) — unchanged |
| Feature extraction | Phase 1 (MarketObserver) |
| DNA discovery or consensus | Phases 3 & 4 |
| Trade signals or strategies | ExecutionEngine |
| Modifying DNA, thresholds, ARS | Never |
| Writing to disk | Never |

---

## 4. New Flow

```
Current Stock Observation (MarketObservation)
        ↓
   PMCIEngine.evaluate()          ←─── ConsensusLibrary (DNA)
        ↓  raw_pmci
   CAPMCIEngine._adjust()         ←─── MarketContext (from MCIEngine)
        ↓
   Five Named Context Adjustments
        ↓
   CA-PMCI (ca_pmci)
```

---

## 5. Five Context Adjustment Dimensions

Every CA-PMCI adjustment follows the same formula:

```
adj = (dna_quality + ctx_quality - 1.0) × weight
```

Clamped to `[-ca_pmci_max_single_adj, +ca_pmci_max_single_adj]`.

| # | Name | DNA Source | Context Source | Weight | Max adj |
|---|---|---|---|---|---|
| 1 | `regime_match` | `regime_stability` (PMCI) | `regime_context` (MCIE) | 0.15 | ±0.15 |
| 2 | `volatility_match` | `evidence_strength` (PMCI) | `volatility_context` (MCIE) | 0.10 | ±0.10 |
| 3 | `sector_match` | `sector_stability` (PMCI) | `sector_context` (MCIE) | 0.10 | ±0.10 |
| 4 | `context_stability` | `evidence_strength` (PMCI) | `context.stability` (MCIE) | 0.07 | ±0.07 |
| 5 | `dna_freshness` | `dna_freshness` (PMCI) | `context_score` (MCIE) | 0.05 | ±0.05 |

**Total maximum context adjustment:** ±0.30 (after clamping the sum).

---

## 6. Adjustment Formula in Detail

### Neutral Point

When `dna_quality = 0.5` AND `ctx_quality = 0.5`:
```
adj = (0.5 + 0.5 - 1.0) × weight = 0.0
```
Exactly zero — no adjustment when both are neutral.

### Maximum Reward

When `dna_quality = 1.0` AND `ctx_quality = 1.0`:
```
adj = (1.0 + 1.0 - 1.0) × weight = +weight
```
Full positive adjustment — excellent DNA in excellent context.

### Maximum Penalty

When `dna_quality = 0.0` AND `ctx_quality = 0.0`:
```
adj = (0.0 + 0.0 - 1.0) × weight = -weight
```
Full negative adjustment — poor DNA in poor context.

### Mixed Cases

| DNA quality | Context quality | adj sign | Meaning |
|---|---|---|---|
| 0.8 | 0.9 | + | Strong DNA in strong context → reward |
| 0.3 | 0.2 | − | Weak DNA in weak context → penalty |
| 0.8 | 0.2 | ≈ 0 | Good DNA but bad context → small effect |
| 0.3 | 0.9 | small+ | Weak DNA still benefits from good context |

---

## 7. Regime Match Adjustment

**DNA source:** `regime_stability` from PMCIResult — how consistently the DNA has
been observed across different market regimes.

**Context source:** `regime_context` from MarketContext — how clear and strong the
current regime is (BULL=0.90, VOLATILE=0.20).

**Logic:**
- DNA proven across all regimes (high stability) + favorable regime (BULL) → reward
- DNA that only works in one regime (low stability) + adverse regime (VOLATILE) → penalty
- DNA with high stability is regime-agnostic → smaller net adjustment

---

## 8. Volatility Match Adjustment

**DNA source:** `evidence_strength` from PMCIResult — the average consensus_score
of matched Winner DNA features.  Highly evidenced DNA withstands volatility better.

**Context source:** `volatility_context` from MarketContext — VIX-based score
(low VIX = high score = favorable environment).

**Logic:**
- Strongly evidenced DNA + low VIX → reward
- Weakly evidenced DNA + high VIX → penalty

---

## 9. Sector Match Adjustment

**DNA source:** `sector_stability` from PMCIResult — how consistently the DNA has
been observed across different market sectors (sector-agnostic vs sector-specific).

**Context source:** `sector_context` from MarketContext — fraction of sectors
with positive flow (all sectors flowing positive = 1.0).

**Logic:**
- Sector-agnostic DNA + sectors leading broadly → reward
- Sector-specific DNA + sectors lagging → penalty

---

## 10. Context Stability Adjustment

**DNA source:** `evidence_strength` from PMCIResult — confidence proxy.

**Context source:** `MarketContext.stability` — how similar is the current context
to the previous one (0.5 on first evaluation, ≈1.0 for identical consecutive snapshots).

**Logic:**
- Strong DNA in a stable context → reinforce confidence
- Drifting/changing context → reduce certainty, discount the raw score

---

## 11. DNA Freshness Adjustment

**DNA source:** `dna_freshness` from PMCIResult — recency of the DNA evidence
(linear decay over `pmci_freshness_days`=30 days).

**Context source:** `MarketContext.context_score` — overall market quality score.

**Logic:**
- Fresh DNA in a favorable market → amplify signal
- Stale DNA in an adverse market → discount signal

---

## 12. Final CA-PMCI

```python
context_adjustment = clamp(sum(adj_i), -ca_pmci_max_total_adj, +ca_pmci_max_total_adj)
ca_pmci            = clamp(raw_pmci + context_adjustment, 0.0, 1.0)
```

**Range:** Always `[0.0, 1.0]` — guaranteed by clamping.

---

## 13. New Output Components

| Component | Formula | Range | Meaning |
|---|---|---|---|
| `context_match_score` | `0.40×regime_align + 0.35×sector_align + 0.25×vol_align` | [0,1] | Combined DNA×context alignment across 3 dimensions |
| `dna_context_stability` | `mean(regime_q, sector_q, vol_q)` | [0,1] | How consistently DNA works across all context types |
| `dna_regime_match` | `regime_stability` from PMCI | [0,1] | DNA regime consistency |
| `dna_sector_match` | `sector_stability` from PMCI | [0,1] | DNA sector consistency |
| `dna_volatility_match` | `evidence_strength` from PMCI | [0,1] | DNA evidence resilience |
| `dna_freshness_weight` | `dna_freshness` from PMCI | [0,1] | DNA recency weight |
| `context_adjustment_factor` | `0.5 + context_adj / (2 × max_adj)` | [0,1] | Normalized adjustment (0.5 = neutral) |

Where:
```
regime_align = (dna_regime_match + ctx_regime_score) / 2
sector_align = (dna_sector_match + ctx_sector_score) / 2
vol_align    = (dna_volatility_match + ctx_vol_score) / 2
```

---

## 14. Confidence

CA-PMCI confidence blends PMCI and MCIE confidence equally:

```python
confidence = clamp((pmci_result.confidence + market_context.confidence) / 2)
```

PMCI confidence: fraction of INSTITUTIONAL DNA features present in the observation.  
MCIE confidence: 0.60 + 0.20 (if FII data) + 0.20 (if sector data).

---

## 15. Explainability

The `explanation` field contains the full narrative:

```
CA-PMCI=0.880 for TATASTEEL on 2026-08-04.
Raw PMCI=0.830, context_score=0.704, context_adjustment=+0.0500.
Adjustments: [Bull regime favours this DNA (+0.0400) |
              Low VIX supports this DNA (+0.0300) |
              Sector currently lagging — penalises this DNA (-0.0200) |
              Context stable — reinforces confidence (+0.0200) |
              DNA fresh in favorable context — amplifies weight (+0.0100)].
```

Every adjustment includes the signed delta and is traced back to its source
values in `ContextAdjustment.evidence`.

---

## 16. Backward Compatibility

**Existing API is fully preserved.** All existing PMCI API methods continue to work
unchanged in `PMCIEngine`:
- `evaluate(observation, library, ...)`
- `evaluate_universe(...)`
- `evaluate_symbol(...)`
- `top_matches(...)`
- `statistics(...)`

New API added in `CAPMCIEngine`:
- `evaluate_context(snapshot)` — evaluate market context only
- `evaluate_with_context(observation, library, snapshot, ...)` — full CA-PMCI
- `evaluate_universe_with_context(observations, library, snapshot, ...)` — batch
- `statistics(results)` — CA-PMCI batch statistics

---

## 17. Design Invariants

| Invariant | Guarantee |
|---|---|
| Non-mutating | `evaluate_with_context()` never modifies observation, library, or snapshot |
| Bounded score | `ca_pmci ∈ [0.0, 1.0]` always |
| Bounded adjustment | `context_adjustment ∈ [-0.30, +0.30]` always |
| Fixed adjustments | `len(adjustments) == 5` always |
| Neutral point | Both DNA and context at 0.5 → zero adjustment |
| Deterministic ID | Same `(symbol, date)` → same `result_id` |
| Empty safety | Empty library returns valid result with `ca_pmci = 0.0` |

---

## 18. Configuration Summary (`MLSConfig` Phase 5B fields)

```python
# Context adjustment weights (max contribution per dimension = ±weight)
ca_pmci_w_regime:       float = 0.15
ca_pmci_w_volatility:   float = 0.10
ca_pmci_w_sector:       float = 0.10
ca_pmci_w_stability:    float = 0.07
ca_pmci_w_freshness:    float = 0.05

# Adjustment bounds
ca_pmci_max_single_adj: float = 0.15   # per-adjustment clamp
ca_pmci_max_total_adj:  float = 0.30   # total adjustment clamp

# Classification
ca_pmci_high_threshold: float = 0.70   # CA-PMCI ≥ this → high similarity
ca_pmci_low_threshold:  float = 0.30   # CA-PMCI ≤ this → low similarity
```

---

## 19. Module Map

| File | Role |
|---|---|
| `market_learning/ca_pmci_models.py` | Data classes: CAPMCIResult, CAPMCIStatistics, ContextAdjustment; exceptions |
| `market_learning/ca_pmci_engine.py` | CAPMCIEngine class; pure helpers: `_clamp`, `_mean`, `_make_ca_pmci_id`, `_extract_component`, `_get_context_score`, `_compute_adj` |
| `market_learning/mls_config.py` | MLSConfig Phase 5B fields |
| `market_learning/__init__.py` | Package-level exports |
| `test_ca_pmci_engine.py` | 90-test suite (90/90 pass) |
