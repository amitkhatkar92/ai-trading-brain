# Contextual DNA Score — Test Report
## MLS Phase 5A.1: CDSEngine

**Result: 90/90 tests passed**
**Date:** 2026-08-04
**Test file:** `test_cds_engine.py`
**Modules under test:** `market_learning/cds_engine.py`, `market_learning/cds_models.py`

---

## Summary

| Group | Tests | Result |
|---|---|---|
| T01–T05 | MLSConfig Phase 5A.1 defaults | 5/5 ✅ |
| T06–T08 | CDSEngine instantiation | 3/3 ✅ |
| T09–T13 | ContextualDNAScore structure | 5/5 ✅ |
| T14–T18 | DNAContextContribution structure | 5/5 ✅ |
| T19–T23 | DNAContextEvidence structure | 5/5 ✅ |
| T24–T28 | regime_match dimension | 5/5 ✅ |
| T29–T33 | volatility_match dimension | 5/5 ✅ |
| T34–T38 | sector_match dimension | 5/5 ✅ |
| T39–T43 | breadth_match dimension | 5/5 ✅ |
| T44–T48 | liquidity_match dimension | 5/5 ✅ |
| T49–T53 | institutional_match dimension | 5/5 ✅ |
| T54–T58 | global_match dimension | 5/5 ✅ |
| T59–T63 | freshness_match dimension | 5/5 ✅ |
| T64–T68 | stability_match dimension | 5/5 ✅ |
| T69–T73 | historical_match dimension | 5/5 ✅ |
| T74–T78 | evaluate_dna() full flow | 5/5 ✅ |
| T79–T83 | evaluate() and evaluate_library() | 5/5 ✅ |
| T84–T87 | top/least/statistics | 4/4 ✅ |
| T88–T90 | Edge cases and serialization | 3/3 ✅ |
| **Total** | | **90/90 ✅** |

---

## Test Framework

Same project-standard `TestRunner` + `TestResult` + `ok()` framework used in
Phases 3, 4, 5, 5A, and 5B. No pytest dependency.

---

## Test Groups — Detail

### T01–T05 — MLSConfig Phase 5A.1 defaults

- `cds_w_regime = 0.20` ✓
- `cds_w_sector = 0.15`, `cds_w_volatility = 0.15`, `cds_w_breadth = 0.12` ✓
- All 10 weights sum to exactly 1.0 ✓
- All 5 relevance thresholds correct (0.75/0.55/0.40/0.25/0.10) ✓
- `cds_stable_threshold = 0.05`, `cds_max_history_size = 200`, `cds_freshness_days = 30` ✓

### T06–T08 — Instantiation

- Default init creates MLSConfig, empty history deque ✓
- Custom config stored correctly (`cds_w_regime=0.25`) ✓
- MCIEngine injection preserved (`engine._mci is mci`) ✓

### T09–T13 — ContextualDNAScore structure

- `evaluation_id` starts with `"CDS-"` (confirmed: `CDS-...`) ✓
- Exactly 10 contributions ✓
- `cds ∈ [0, 1]` ✓
- `len(supporting) + len(conflicting) == 10` ✓
- `explanation` non-empty and contains `feature_name` ✓

### T14–T18 — DNAContextContribution structure

- All 10 dimension names present ✓
- All `score ∈ [0, 1]` ✓
- All `weighted_score == score × weight` (within float tolerance) ✓
- `supporting == (score >= 0.50)` for all ✓
- `to_dict() / from_dict()` round-trip preserves all fields ✓

### T19–T23 — DNAContextEvidence structure

- `evidence.evaluation_id` starts with `"CDS-"` ✓
- `dna_id` / `feature_name` / `direction` match input DNA ✓
- `regime_at_eval` matches `context.regime` ✓
- `context_score_at_eval` matches `context.context_score` ✓
- `to_dict() / from_dict()` round-trip ✓

### T24–T28 — regime_match dimension

| Scenario | Score | Result |
|---|---|---|
| Bull DNA (53% in bull_trend) + bull regime ctx=0.90 | 0.6433 | > 0.50 ✓ |
| Bull DNA (7% in volatile) + volatile ctx=0.20 | 0.1067 | < 0.50 ✓ |
| Regime-agnostic (consistency=0.85) + clear regime (0.90) | 0.9500 | > 0.70 ✓ |
| All edge inputs | [0,1] range | ✓ |

Evidence keys confirmed: `regime_context_score`, `dna_regime_counts`, `dna_regime_consistency`

### T29–T33 — volatility_match dimension

| Scenario | Score |
|---|---|
| temporal_stability=0.80, vol_ctx=0.80 | 0.8000 |
| temporal_stability=0.30, vol_ctx=0.10 | 0.1800 |
| high_stab=0.95 + low_vol_ctx=0.10 vs low_stab=0.20 + same | 0.440 > 0.140 |

Evidence keys: `volatility_context_score`, `dna_temporal_stability`

### T30–T38 — sector_match, breadth_match

| Scenario | Score |
|---|---|
| sector_consistency=0.90, sector_ctx=0.75 (bull) | 0.8100 |
| bull sector vs adverse sector | 0.650 > 0.310 |
| breadth: high persistence + high ctx | > 0.60 |
| breadth: low ctx | < 0.35 |

### T44–T48 — liquidity_match

- `evidence_count=50` → `evidence_proxy = 1.0` (saturated) — formula verified ✓
- `score_50 == score_51` (saturation confirmed) ✓

### T59–T63 — freshness_match

| Scenario | Score |
|---|---|
| `last_seen="2026-08-03"`, eval `"2026-08-04"` (1 day) | ≥ 0.9667 |
| `last_seen="2026-08-04"`, eval `"2026-08-04"` (today) | 1.0000 |
| `last_seen="2026-07-05"`, eval `"2026-08-04"` (30 days) | 0.0000 |

### T64–T68 — stability_match and ContextStabilityLabel

| context.stability | delta = 1 - stability | Label |
|---|---|---|
| 0.97 | 0.03 | STABLE |
| 0.40 | 0.60 | DRIFTING |

### T69–T73 — historical_match and analogue search

- Fresh engine → `historical_similarity_score = 0.500` ✓
- After storing similar context → `historical_similarity_score > 0.500` ✓
- Empty history → `historical_matches() = []` ✓
- `DNAContextSimilarity.analogue_id` starts with `"MCE-"` ✓
- `matched_dimensions` populated with component names ✓

**Bug found and fixed during development:**
Initial guard `len(self._context_history) < 2` was too strict — prevented finding matches
when exactly 1 historical context existed and current context had a different id.
Fixed to `len(self._context_history) == 0`.

### T74–T78 — evaluate_dna() full flow

- `dna_id` and `feature_name` match input DNA ✓
- `cds ∈ [0, 1]`, `confidence ∈ [0, 1]` ✓
- Standard DNA in bull context: RELEVANT or HIGHLY_RELEVANT ✓
- Strong DNA (high-evidence, regime-agnostic, today): HIGHLY_RELEVANT ✓
- Deterministic: same inputs → same `evaluation_id` ✓
- `snapshot=None`: `vix_at_eval=0.0`, `fii_net_at_eval=0.0` (no crash) ✓

### T79–T83 — evaluate() and evaluate_library()

- 3 INSTITUTIONAL DNA → 3 results ✓
- `evaluate_library()` returns `CDSLibraryResult` with matching scores and statistics ✓
- Empty library → empty list ✓
- All scores share same `evaluation_date` ✓
- `statistics.total_dna == len(scores)` ✓

### T84–T87 — top/least/statistics

- `top_supported_dna()` sorted descending by `cds` ✓
- `least_supported_dna()` sorted ascending by `cds` ✓
- Relevance counts (HIGHLY_RELEVANT + RELEVANT + ... + DEPRECATED) = total_dna ✓
- Empty results → `total_dna=0`, `top_dna_id=None`, `avg_cds=0.0` (no exception) ✓

### T88–T90 — Edge cases and serialization

- `ContextualDNAScore.to_dict()/from_dict()`: all fields preserved ✓
- `DNAContextProfile.from_score()`: valid profile, non-empty `top_contribution` ✓
- `DNAContextHistory.from_scores()`: trend detection (adverse → bull → IMPROVING) ✓

---

## Key Observed Values

| Scenario | CDS | Relevance |
|---|---|---|
| Standard DNA in bull context (default fixture) | ≈ 0.730 | RELEVANT |
| Strong DNA (regime-agnostic, 50 obs, today) in bull | ≈ 0.834 | HIGHLY_RELEVANT |
| Standard DNA in adverse context | ≈ 0.319 | WEAK |
| Context stability = 0.97 | delta = 0.03 | STABLE |
| Context stability = 0.40 | delta = 0.60 | DRIFTING |

---

## Bugs Fixed During Development

| Test | Symptom | Root Cause | Fix |
|---|---|---|---|
| T72, T73 | `len(matches) == 0` when 1 history entry + different current context | Guard `len < 2` too strict — blocked valid 1-entry searches | Changed guard to `len == 0` |

---

## Runtime

All 90 tests complete in **< 100 ms** total (no I/O, no network calls).
