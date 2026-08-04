# PMCI Engine — Test Report
## MLS Phase 5: Pre-Movement Consensus Intelligence

**Result: 90/90 tests passed**  
**Date:** 2026-08-04  
**Test file:** `test_pmci_engine.py`  
**Module under test:** `market_learning/pmci_engine.py`, `market_learning/pmci_models.py`

---

## Summary

| Group | Tests | Result |
|---|---|---|
| T01–T05 | MLSConfig Phase 5 defaults | 5/5 ✅ |
| T06–T08 | Engine instantiation and read-only guarantee | 3/3 ✅ |
| T09–T13 | PMCIResult structure | 5/5 ✅ |
| T14–T18 | PMCIComponent structure | 5/5 ✅ |
| T19–T22 | PMCIEvidence structure | 4/4 ✅ |
| T23–T27 | PMCIBreakdown | 5/5 ✅ |
| T28–T33 | `_align()` math | 6/6 ✅ |
| T34–T38 | Winner match computation | 5/5 ✅ |
| T39–T43 | Loser match / contradiction | 5/5 ✅ |
| T44–T48 | Evidence strength | 5/5 ✅ |
| T49–T53 | Regime / sector stability | 5/5 ✅ |
| T54–T58 | DNA freshness | 5/5 ✅ |
| T59–T63 | Knowledge coverage | 5/5 ✅ |
| T64–T68 | `evaluate_universe()` | 5/5 ✅ |
| T69–T73 | `top_matches()` | 5/5 ✅ |
| T74–T78 | `statistics()` | 5/5 ✅ |
| T79–T83 | Explainability | 5/5 ✅ |
| T84–T88 | `evaluate_symbol()` | 5/5 ✅ |
| T89–T90 | Edge cases | 2/2 ✅ |
| **Total** | | **90/90 ✅** |

---

## Test Framework

The suite uses the project-standard `TestRunner` + `TestResult` + `ok()` helper
(no pytest dependency).  Each test is a zero-argument closure that raises on
assertion failure and returns a string result label for display.

---

## Test Groups — Detail

### T01–T05 — MLSConfig Phase 5 defaults

Verify all Phase 5 fields added to `MLSConfig`:

- `pmci_w_winner = 0.35`, `pmci_w_loser = 0.25`
- Positive weights (`w_winner + w_evidence + … + w_neutral`) sum exactly to 1.0
- Freshness window `pmci_freshness_days = 30`, midpoint `pmci_feature_midpoint = 0.50`
- High/low similarity thresholds override via custom config

### T06–T08 — Engine instantiation and read-only guarantee

- `PMCIEngine()` initialises with default config
- `PMCIEngine(config=cfg)` stores the custom config
- `evaluate()` returns the same result when called twice with the same inputs;
  the library's `all_consensus` list is not modified (read-only invariant)

### T09–T13 — PMCIResult structure

- `result_id` starts with `"PMC-"`
- `evaluation_date` equals the supplied date string
- `pmci_score ∈ [0, 1]`
- `len(components) == 9` always
- `explanation` is a non-empty string

### T14–T18 — PMCIComponent structure

- All nine component names are present
- All component values `∈ [0, 1]`
- `weighted_value == value × weight` for all nine components
- Component weights match the `MLSConfig` fields
- All `matched_count ≥ 0`

### T19–T22 — PMCIEvidence structure

- `contribution == alignment × consensus_score` (rounded to 6 dp)
- `is_match = True` when `alignment ≥ 0.50`
- `is_contradiction = True` when `alignment < 0.50`
- Full `to_dict() / from_dict()` round-trip preserves all fields

### T23–T27 — PMCIBreakdown

- `breakdown` is a `PMCIBreakdown` instance
- `coverage_fraction == n_observed / n_active_dna`
- `missing_dna` is sorted alphabetically
- Full `to_dict() / from_dict()` round-trip
- `total_institutional_dna` counts INSTITUTIONAL-state DNA in the library

### T28–T33 — `_align()` math

- `WINNERS_HIGHER, value=0.90` → alignment `0.90`
- `WINNERS_HIGHER, value=0.10` → alignment `0.10`
- `WINNERS_LOWER, value=0.10` → alignment `0.90`
- `WINNERS_LOWER, value=0.90` → alignment `≈0.10`
- `value=0.50` → alignment `0.50` for both HIGHER and LOWER
- `value=5.0` (out-of-range) → clamped to `1.0`

### T34–T38 — Winner match computation

- All features high → `winner_match = 1.0`
- All features low → `winner_match = 0.0`
- Mixed 50 / 50 → `winner_match ≈ 0.50`
- Weighted by `consensus_score`: high-score feature dominates
- No matching features in observation → `winner_match = 0.0`

### T39–T43 — Loser match / contradiction

- `winner_match + loser_match == 1.0` (exact complement) when features present
- Perfect winner observation → `loser_match = 0.0`
- Perfect loser observation → `loser_match = 1.0`
- Loser penalty lowers PMCI relative to a winner observation
- No observable winner DNA features → `loser_match = 0.0`

### T44–T48 — Evidence strength

- High-score DNA (score=0.95) → `evidence_strength ≈ 0.95`
- Low-score DNA (score=0.20) → `evidence_strength ≈ 0.20`
- No matched features → `evidence_strength = 0.0`
- Conflicting feature does **not** contribute to `evidence_strength` (matched-only)
- Higher evidence_strength produces higher PMCI score

### T49–T53 — Regime / sector stability

- `regime_stability` = mean `regime_consistency` across all present winner DNA
- `sector_stability` = mean `sector_consistency` across all present winner DNA
- Both zero when no winner DNA features are in the observation
- Conflicting features **are** included in stability (all present winner DNA counts)
- Higher stability values produce higher PMCI score

### T54–T58 — DNA freshness

- `last_seen == as_of` → freshness `1.0`
- `last_seen = as_of − 30d` → freshness `0.0`
- `last_seen = as_of − 15d` → freshness `0.5`
- Linear decay: `f(10d) ≈ 2 × f(20d)` (within 1e-6)
- Fresh (same-day) DNA produces `dna_freshness ≈ 1.0` in `PMCIResult`

### T59–T63 — Knowledge coverage

- All active DNA features present in observation → `coverage = 1.0`
- No active DNA features present → `coverage = 0.0`
- 1-of-3 features present → `coverage ≈ 0.3333`
- Full coverage produces higher PMCI than partial coverage (equal alignment)
- NEUTRALS_* DNA counts toward coverage (`knowledge_coverage` includes neutral)

### T64–T68 — `evaluate_universe()`

- Returns one result per observation; length matches input
- Each result carries the correct symbol
- Results are independent (different observations produce different scores)
- Empty observation list → empty result list
- All results in the batch share the same `library_id`

### T69–T73 — `top_matches()`

- Results are sorted by `pmci_score` descending
- `top_matches(n=5)` returns exactly 5 results from a larger pool
- The first result has the highest score
- Returns all results when `n ≥ len(results)`
- Empty input → empty output

### T74–T78 — `statistics()`

- `total_symbols` equals the number of results
- `avg_pmci` is the arithmetic mean of all scores
- `high_similarity_count` counts scores ≥ `pmci_high_similarity_threshold`
- `top_symbol` is the symbol with the highest score
- Empty input returns safe defaults (zeros, `top_symbol=None`)

### T79–T83 — Explainability

- `matched_dna` is sorted by `contribution` descending
- Conflicting DNA features appear in `breakdown.conflicting_dna`
- `missing_dna` is sorted alphabetically
- `explanation` string contains the symbol name
- `explanation` string mentions the number of matched features

### T84–T88 — `evaluate_symbol()`

- Returns `None` for a symbol absent from the snapshot
- Returns a `PMCIResult` for a symbol present in the snapshot
- `evaluation_date` equals `snapshot.trading_date`
- `regime` is taken from `snapshot.regime`
- Produces the same `pmci_score` as `evaluate()` called with the same arguments

### T89–T90 — Edge cases

- `RETIRED`-state DNA is excluded from all components (score unaffected by retired features)
- Empty library (no DNA) → `pmci_score = 0.0`, all 9 components present

---

## Bugs Fixed During Development

| Test | Symptom | Root Cause | Fix |
|---|---|---|---|
| T62 | `hi=0.738 < lo=0.743` | Test used different alignments (0.80 vs 0.70) making partial-coverage obs have higher winner_match; tiny coverage weight (0.05) was insufficient to overcome the alignment gap | Changed test to use equal alignments (0.90/0.90) so only coverage differs |
| T68 | `TypeError: _winner_library() got unexpected keyword argument 'date'` | Test called `_winner_library(date=...)` but helper has no `date` parameter | Changed to `_make_library([...], date="2026-08-03")` |

---

## Runtime

All 90 tests complete in **< 5 ms** total (no I/O, no subprocess calls).
