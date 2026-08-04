# Market Context Intelligence Engine — Design Document
## MLS Phase 5A: Market Context Intelligence Engine (MCIE)

---

## 1. Purpose

MCIEngine evaluates the **current market environment** and converts it into a
scientifically explainable, multi-dimensional context profile.

MCIE answers: *"What is the quality of the market environment right now?"*

It is the **market-awareness layer** for IIOS — reusable by any downstream
component that needs to understand the market before acting.

MCIE **never** predicts, trades, or scores individual stocks.

---

## 2. Position in the MLS Pipeline

```
Phase 1 — MarketObserver        → feature vectors (DailyMarketSnapshot)
Phase 2 — PopulationClassifier  → winner / loser labels
Phase 3 — DNADiscoveryEngine    → winner DNA candidates
Phase 4 — DNAConsensusEngine    → validated institutional DNA (ConsensusLibrary)
Phase 5 — PMCIEngine            → stock similarity to Winner DNA (PMCIResult)
Phase 5A — MCIEngine  ◀ HERE   → market environment quality (MarketContext)
```

MCIE is **parallel to Phase 5**, not sequential. It evaluates the market, not stocks.

---

## 3. What MCIE Is Not

| Scope | Outside MCIE |
|---|---|
| Stock scoring | Phase 5 (PMCIEngine) |
| Feature extraction | Phase 1 (MarketObserver) |
| Population labelling | Phase 2 (PopulationClassifier) |
| DNA discovery | Phase 3 (DNADiscoveryEngine) |
| DNA consensus | Phase 4 (DNAConsensusEngine) |
| Trade execution / signalling | ExecutionEngine |
| Persistent state | Engine is in-memory only |
| Changing DNA, thresholds, or PMCI | Never |

---

## 4. Primary Input

| Field | Source | Used for |
|---|---|---|
| `snapshot.regime` | `MarketSnapshot` | `regime_context` |
| `snapshot.vix` | `MarketSnapshot` | `volatility_context`, `risk_context` |
| `snapshot.market_breadth` | `MarketSnapshot` | `participation_context`, `liquidity_context` |
| `snapshot.pcr` | `MarketSnapshot` | `risk_context` |
| `snapshot.global_sentiment_score` | `MarketSnapshot` | `global_context` |
| `snapshot.global_bias` | `MarketSnapshot` | `global_context` |
| `snapshot.fii_dii` | `MarketSnapshot` | `liquidity_context`, `institutional_context` |
| `snapshot.sector_flows` | `MarketSnapshot` | `sector_context` |

All inputs come from a single `MarketSnapshot` (from `models.market_data`).

---

## 5. The Eight Context Dimensions

Each dimension is independently scored to `[0, 1]` with a weight from `MLSConfig`.

| # | Dimension | Weight | Meaning |
|---|---|---|---|
| 1 | `regime_context` | `mcie_w_regime = 0.20` | Clarity and strength of the current market regime |
| 2 | `volatility_context` | `mcie_w_volatility = 0.15` | VIX-based environment quality (lower VIX = higher score) |
| 3 | `liquidity_context` | `mcie_w_liquidity = 0.15` | Institutional flow + market breadth combined |
| 4 | `participation_context` | `mcie_w_participation = 0.12` | Market breadth: fraction of stocks advancing |
| 5 | `sector_context` | `mcie_w_sector = 0.12` | Fraction of sectors with positive flow |
| 6 | `institutional_context` | `mcie_w_institutional = 0.10` | FII (70%) + DII (30%) net flow quality |
| 7 | `global_context` | `mcie_w_global = 0.10` | Global sentiment score aligned to market direction |
| 8 | `risk_context` | `mcie_w_risk = 0.06` | Combined PCR + VIX risk environment |

**All 8 weights sum to 1.0** — context_score is a proper weighted average.

---

## 6. Scoring Formulas

### Regime Context

| Regime | Score |
|---|---|
| `bull_trend` | 0.90 — strong, clear direction |
| `bear_market` | 0.65 — clear but adverse |
| `range_market` | 0.45 — no clear direction |
| `volatile` | 0.20 — chaotic, rapidly changing |

### Volatility Context (lower VIX = higher score)

| VIX Range | Score |
|---|---|
| ≤ 15 | 0.90 |
| 15 – 20 | 0.70 |
| 20 – 30 | 0.40 |
| 30 – 40 | 0.20 |
| > 40 | 0.05 |

### Liquidity Context

When FII/DII data is absent: `liquidity = market_breadth`

With FII/DII data:
```
flow_score = clamp(0.5 + total_net_crores / 4000)
liquidity  = 0.4 × breadth + 0.6 × flow_score
```

Reference: ±4000 crore/day separates strong inflow (≈1.0) from strong outflow (≈0.0).

### Participation Context

`participation = market_breadth` (direct linear map; 0.0–1.0)

### Sector Context

`sector_context = positive_flow_sectors / total_sectors`

Returns 0.5 when sector_flows is empty (neutral default).

### Institutional Context

```
fii_score = clamp(0.5 + fii_net / 3000)
dii_score = clamp(0.5 + dii_net / 3000)
institutional = 0.70 × fii_score + 0.30 × dii_score
```

Returns 0.5 when FII/DII data is absent.

### Global Context

```
base      = clamp(0.5 + global_sentiment_score / 2)
bias_adj  = { "bullish": +0.05, "neutral": 0.0, "bearish": -0.05 }
global    = clamp(base + bias_adj)
```

### Risk Context

PCR balanced zone `[mcie_pcr_balanced_lo=0.80, mcie_pcr_balanced_hi=1.20]`:
```
if balanced:   pcr_score = 1.0
if pcr < lo:   pcr_score = clamp(pcr / lo)          # call-heavy
if pcr > hi:   pcr_score = clamp(1 - (pcr-hi)/(3-hi))  # put-heavy

risk = clamp(0.5 × pcr_score + 0.5 × volatility_score)
```

### Context Score (final)

```
context_score = clamp(Σ weight_i × score_i, 0.0, 1.0)
```

---

## 7. Context Score Classification

| Threshold | Classification |
|---|---|
| `context_score ≥ 0.65` | High context quality |
| `0.35 < context_score < 0.65` | Normal |
| `context_score ≤ 0.35` | Low context quality |

---

## 8. Confidence

Confidence reflects data richness:
```
confidence = 0.60
           + 0.20 if FII/DII data present
           + 0.20 if sector_flows present
```

Range: [0.60, 1.00].

---

## 9. Stability

Stability measures how similar the current context is to the previous one:
```
stability = clamp(1.0 - mean(|score_i(now) - score_i(prev)|))
```

On the first evaluation: `stability = 0.50` (neutral, no prior context).  
After identical snapshots: `stability = 1.00`.

---

## 10. Context Drift

Drift is computed between the last two consecutive evaluations:

```
score_delta    = context_score(now) - context_score(prev)
regime_changed = (regime(now) != regime(prev))
drifting       = [dim for dim if |score(dim,now) - score(dim,prev)| >= 0.10]
drift_magnitude = mean(|score_i(now) - score_i(prev)|)   # clamped to [0,1]
```

---

## 11. State and History

MCIEngine maintains an in-memory history bounded by `mcie_max_history_size = 100`.
History is never persisted to disk.

State transitions:
- `evaluate()` → computes context, appends to history, returns `MarketContext`
- `current_context()` → latest entry
- `history()` → frozen snapshot of the list
- `drift()` → computed on demand from last two entries
- `statistics()` → computed on demand from full history

---

## 12. Design Invariants

| Invariant | Guarantee |
|---|---|
| Non-mutating | `evaluate()` never modifies the `MarketSnapshot` |
| Bounded score | `context_score ∈ [0.0, 1.0]` always |
| Fixed dimensions | `len(context.components) == 8` always |
| No side effects | Engine never writes to disk, DNA, or PMCI |
| Deterministic ID | Same `(timestamp, date)` → same `context_id` |
| Empty safety | `statistics()` and `drift()` return safe defaults on empty history |

---

## 13. Context ID

```
context_id = "MCE-" + sha256(f"{snapshot.timestamp.isoformat()}::{evaluation_date}")[:8]
```

The same snapshot evaluated on the same date always produces the same `context_id`.

---

## 14. Configuration Summary (`MLSConfig` Phase 5A fields)

```python
# Context dimension weights (sum to 1.0)
mcie_w_regime:               float = 0.20
mcie_w_volatility:           float = 0.15
mcie_w_liquidity:            float = 0.15
mcie_w_participation:        float = 0.12
mcie_w_sector:               float = 0.12
mcie_w_institutional:        float = 0.10
mcie_w_global:               float = 0.10
mcie_w_risk:                 float = 0.06

# VIX scoring thresholds
mcie_vix_low:                float = 15.0
mcie_vix_medium:             float = 20.0
mcie_vix_high:               float = 30.0
mcie_vix_extreme:            float = 40.0

# PCR balanced zone
mcie_pcr_balanced_lo:        float = 0.80
mcie_pcr_balanced_hi:        float = 1.20

# Drift detection
mcie_drift_threshold:        float = 0.10

# Classification thresholds
mcie_high_context_threshold: float = 0.65
mcie_low_context_threshold:  float = 0.35

# History size
mcie_max_history_size:       int   = 100
```

---

## 15. Final Questions (from Specification)

| Question | Answer |
|---|---|
| Can every Context Score be reproduced? | Yes — same `MarketSnapshot` always yields the same score via deterministic formulas |
| Can context drift be explained? | Yes — `ContextDrift.drifting_components` names every dimension that changed ≥ 10% |
| Can MCIE be reused outside PMCI? | Yes — it depends only on `MarketSnapshot` and `MLSConfig`; PMCI is not a dependency |
| Can every component be traced back to MarketSnapshot? | Yes — every `ContextComponent.evidence` contains the raw snapshot fields used |

---

## 16. Module Map

| File | Role |
|---|---|
| `market_learning/mcie_models.py` | Data classes: MarketContext, ContextComponent, ContextHistory, ContextDrift, ContextStatistics; exceptions |
| `market_learning/mcie_engine.py` | MCIEngine class; pure helpers: `_clamp`, `_mean`, `_make_context_id`, `_score_regime`, `_score_volatility`, `_score_liquidity`, `_score_sector`, `_score_institutional`, `_score_global`, `_score_risk` |
| `market_learning/mls_config.py` | MLSConfig Phase 5A fields |
| `market_learning/__init__.py` | Package-level exports |
| `test_mcie_engine.py` | 90-test suite (90/90 pass) |
