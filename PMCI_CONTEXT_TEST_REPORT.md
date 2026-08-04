# PMCI Context Test Report
## MLS Phase 5B: Context-Aware PMCI Engine (CA-PMCI)

**Result: 90/90 tests passed**  
**Date:** 2026-08-04  
**Test file:** `test_ca_pmci_engine.py`  
**Modules under test:** `market_learning/ca_pmci_engine.py`, `market_learning/ca_pmci_models.py`

---

## Summary

| Group | Tests | Result |
|---|---|---|
| T01–T05 | MLSConfig Phase 5B defaults | 5/5 ✅ |
| T06–T08 | CAPMCIEngine instantiation | 3/3 ✅ |
| T09–T13 | CAPMCIResult structure | 5/5 ✅ |
| T14–T18 | ContextAdjustment structure | 5/5 ✅ |
| T19–T22 | evaluate_context() | 4/4 ✅ |
| T23–T27 | `_compute_adj` formula | 5/5 ✅ |
| T28–T32 | volatility_match adjustment | 5/5 ✅ |
| T33–T37 | sector_match adjustment | 5/5 ✅ |
| T38–T42 | context_stability adjustment | 5/5 ✅ |
| T43–T47 | dna_freshness adjustment | 5/5 ✅ |
| T48–T52 | context_adjustment bounds / formula | 5/5 ✅ |
| T53–T57 | context_match_score | 5/5 ✅ |
| T58–T62 | dna_context_stability | 5/5 ✅ |
| T63–T67 | evaluate_with_context() full flow | 5/5 ✅ |
| T68–T72 | evaluate_universe_with_context() | 5/5 ✅ |
| T73–T77 | Backward compatibility | 5/5 ✅ |
| T78–T82 | CA-PMCI favorable/adverse scenarios | 5/5 ✅ |
| T83–T87 | statistics() | 5/5 ✅ |
| T88–T90 | Edge cases and serialisation | 3/3 ✅ |
| **Total** | | **90/90 ✅** |

---

## Test Framework

Same project-standard `TestRunner` + `TestResult` + `ok()` framework used in
Phases 3, 4, 5, and 5A. No pytest dependency.

---

## Test Groups — Detail

### T01–T05 — MLSConfig Phase 5B defaults

- `ca_pmci_w_regime = 0.15` ✓
- `ca_pmci_w_volatility = 0.10`, `ca_pmci_w_sector = 0.10` ✓
- `ca_pmci_w_stability = 0.07`, `ca_pmci_w_freshness = 0.05` ✓
- `ca_pmci_max_single_adj = 0.15`, `ca_pmci_max_total_adj = 0.30` ✓
- `ca_pmci_high_threshold = 0.70`, `ca_pmci_low_threshold = 0.30` ✓

### T06–T08 — Instantiation

- Default init stores MLSConfig
- Custom config stored correctly (`ca_pmci_w_regime=0.20`)
- MCIEngine injected at construction is preserved (`engine._mci is mci`)

### T09–T13 — CAPMCIResult structure

- `result_id` starts with `"CAP-"` (confirmed: `CAP-1b58f7bd`)
- `symbol` and `evaluation_date` match inputs
- `raw_pmci`, `context_score`, `ca_pmci` all in `[0, 1]`
- Exactly 5 `adjustments` entries
- `explanation` is non-empty and contains the stock symbol

### T14–T18 — ContextAdjustment structure

- All 5 adjustment names present: `regime_match`, `volatility_match`, `sector_match`, `context_stability`, `dna_freshness`
- All `delta` values are Python `float`
- All `explanation` strings are non-empty
- All `evidence` dicts are non-empty
- `to_dict() / from_dict()` round-trip preserves all fields

### T19–T22 — evaluate_context()

- Returns `MarketContext` instance
- `context_id` starts with `"MCE-"`
- `context_score ∈ [0, 1]`
- Exactly 8 context components

### T23–T27 — `_compute_adj` formula

Direct formula verification:

| Inputs | Formula | Result |
|---|---|---|
| dna=0.80, ctx=0.90, w=0.15 | (0.80+0.90-1.0)×0.15 | +0.105000 |
| dna=0.30, ctx=0.20, w=0.15 | (0.30+0.20-1.0)×0.15 | −0.075000 |
| dna=0.50, ctx=0.50, w=0.15 | (0.50+0.50-1.0)×0.15 | 0.000000 |
| dna=1.00, ctx=1.00, w=0.15 | capped at cap=0.15 | +0.150000 |
| dna=0.00, ctx=0.00, w=0.15 | capped at cap=0.15 | −0.150000 |

### T28–T32 — volatility_match adjustment

- Low VIX (ctx_vol=0.90) + strong evidence (0.80) → `vol_adj = +0.0700 > 0` ✓
- High VIX (ctx_vol=0.05) + weak evidence (0.20) → `vol_adj = −0.0750 < 0` ✓
- Bounded to `[−0.10, +0.10]` ✓
- Delta in result within bounds ✓
- Evidence dict contains `dna_evidence_strength` and `volatility_context_score` ✓

### T33–T37 — sector_match adjustment

- All-positive sectors (ctx_sector=1.0) + high sector consistency (0.80) → `sector_adj = +0.0800 > 0` ✓
- All-negative sectors (ctx_sector=0.0) + low consistency (0.30) → `sector_adj = −0.0700 < 0` ✓
- Empty sector flows (ctx_sector=0.5) → small positive adj `+0.0300` ✓
- Bounded to `[−0.10, +0.10]` ✓
- Evidence dict contains `dna_sector_stability` and `sector_context_score` ✓

### T38–T42 — context_stability adjustment

- dna_evidence=0.80, stability=0.80 → `stability_adj = +0.0420` ✓
- First evaluation → `context_stability = 0.5` in evidence ✓
- Pre-warmed MCIEngine (same snapshot evaluated twice) → `stability ≈ 1.0000` ✓
- Bounded to `[−0.07, +0.07]` ✓
- Evidence dict contains `dna_evidence_strength` and `context_stability` ✓

### T43–T47 — dna_freshness adjustment

- Fresh DNA (0.967) + favorable context (0.70) → `freshness_adj = +0.0333 > 0` ✓
- Stale DNA (0.0) + adverse context (0.10) → `freshness_adj = −0.0450 < 0` ✓
- Both neutral (0.50, 0.50) → `freshness_adj = 0.000000` ✓
- Bounded to `[−0.05, +0.05]` ✓
- Evidence dict contains `dna_freshness` and `overall_context_score` ✓

### T48–T52 — context_adjustment bounds/formula

- `context_adjustment == clamp(sum(deltas), −0.30, +0.30)` (confirmed: `+0.2595`)
- In all scenarios (bull/adverse/default): `context_adjustment ∈ [−0.30, +0.30]` ✓
- `context_adjustment_factor = 0.5` when `adj = 0` (formula verified) ✓
- `context_adjustment_factor ∈ [0, 1]` for all scenarios ✓
- Positive total adj → `factor > 0.5` (confirmed: bull gives `factor = 1.0000`) ✓

### T53–T57 — context_match_score

- Always in `[0, 1]` ✓
- Favorable (BULL + strong DNA): `context_match_score = 0.8675 > 0.65` ✓
- Good DNA in bull vs poor DNA in adverse: `0.8675 > 0.2587` ✓
- Formula: `0.40×regime_align + 0.35×sector_align + 0.25×vol_align` verified ✓
- Independent of DNA freshness (confirmed: fresh=0.7800, stale=0.7800) ✓

### T58–T62 — dna_context_stability

- `dna_context_stability = mean(regime_q, sector_q, vol_q)` (confirmed: 0.8000) ✓
- Always in `[0, 1]` ✓
- High DNA consistency → `dna_context_stability = 0.8000 > 0.6` ✓
- All three component fields in `[0, 1]` ✓
- Independent of market context (bull=0.8000 = adverse=0.8000) ✓

### T63–T67 — evaluate_with_context() full flow

- Returns `CAPMCIResult` instance ✓
- `raw_pmci = 0.723000` matches standalone `PMCIEngine.evaluate()` exactly ✓
- `ca_pmci = 0.982533 = clamp(0.7230 + 0.2595)` ✓
- Inputs (observation, library, snapshot) not mutated ✓
- `result_id` deterministic: same inputs → same `CAP-1b58f7bd` ✓

### T68–T72 — evaluate_universe_with_context()

- Returns list of same length as input (5 observations → 5 results) ✓
- All results share the same `context_id` (evaluated once, shared) ✓
- Empty-feature observation: no crash, returns valid `CAPMCIResult` ✓
- Empty input list → empty result list ✓
- All results use the same `evaluation_date` override ✓

### T73–T77 — Backward compatibility

- `PMCIEngine.evaluate()` still returns `PMCIResult` with `result_id="PMC-..."` ✓
- `PMCIEngine.evaluate_universe()` returns 3 `PMCIResult` unchanged ✓
- `PMCIEngine.statistics().total_symbols` correct ✓
- `CAPMCIResult.pmci_result` is a full `PMCIResult` starting with `"PMC-"` ✓
- Embedded PMCIResult has `symbol="TEST"`, `feature_count=2`, `len(components)=9` ✓

### T78–T82 — Favorable/adverse CA-PMCI

- Bull context + good DNA: `raw=0.7230 → ca=1.0000 (+0.3000)` — ca > raw ✓
- Adverse context + weak DNA: `raw=0.4330 → ca=0.2977 (−0.1353)` — ca ≤ raw ✓
- `ca_pmci ∈ [0, 1]` for all 5 scenarios ✓
- Max favorable DNA in best market: `adj = +0.3000` (hits cap) ✓
- Worst DNA in worst market: `adj = −0.3000` (hits cap) ✓

### T83–T87 — statistics()

- `total_symbols = 5` ✓
- Bull context: `avg_raw = 0.6230 → avg_ca = 0.9230` (ca > raw) ✓
- `most_improved_symbol = "GOOD"` (highest alignment features) ✓
- `most_degraded_symbol = "WORST"` (anti-aligned features + adverse context) ✓
- Empty results → all zeros, all `None`, no exception ✓

### T88–T90 — Edge cases and serialisation

- Empty library: `ca_pmci = 0.0`, returns valid `CAPMCIResult` (no crash) ✓
- `context_adjustment_factor = 0.5` when `adj = 0` (formula verified algebraically) ✓
- Full `to_dict() / from_dict()` round-trip: all fields preserved ✓

---

## Observed CA-PMCI Values

| Scenario | raw_pmci | context_adj | ca_pmci | Notes |
|---|---|---|---|---|
| Default (BULL, VIX=15, no FII) | 0.723 | +0.260 | 0.983 | Standard favorable |
| Bull (BULL, VIX=10, FII+2000) | 0.723 | +0.300 | 1.000 | Hits max cap |
| Adverse (VOLATILE, VIX=50) | 0.433 | −0.135 | 0.298 | Mixed DNA |
| Max favorable DNA + bull | 0.900+ | +0.300 | 1.000 | All-excellent |
| Worst DNA + adverse | 0.000 | −0.300 | 0.000 | All-poor |

---

## Bugs Fixed During Development

| Test | Symptom | Root Cause | Fix |
|---|---|---|---|
| T49, T51–T55, T59, T62, T78–T79 | `TypeError: SectorFlow.__init__() got an unexpected keyword argument 'name'` | Fixture used `name=` instead of `sector_name=` | Changed to `SectorFlow(sector_name=..., rank=...)` |
| T49, T51–T55, T59, T62, T78–T79 | `TypeError: FIIDIIData.__init__() got an unexpected keyword argument 'fii_net'` | `fii_net` is a computed property, not a constructor arg | Changed to `FIIDIIData(date=..., fii_buy=..., fii_sell=...)` |

---

## Runtime

All 90 tests complete in **< 50 ms** total (no I/O, no network calls).
