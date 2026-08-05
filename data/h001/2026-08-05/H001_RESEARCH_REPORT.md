# H001 Research Report

**Study:** H-CRITICAL-001  
**Hypothesis:** H2026-08-001 — Loser DNA cross-year validation  
**Date:** 2026-08-05  


## Hypothesis

*Do loser DNA conditions derived from 2025 persist in 2026 and beyond?*

## Dataset

- Total feature records: 500
- Training year (2025): 196 records
- Validation year (2026): 304 records
- Loser DNA conditions tested: 20

## Methodology

1. **Feature-match method**: condition applied directly to feature records; hit rate = P(forward_return < -0.5% | condition met)
2. **Edge-lifecycle method**: for conditions using edge-specific features not in feature records; DECAYING edges = loser condition worsening over time
3. **Statistical test**: Yates-corrected chi-squared on 2×2 contingency table
4. **Cross-year stability**: 1 - |hr_train - hr_valid| / max(hr_train, hr_valid)

## Results Per Condition

| Condition | Method | hr_2025 | hr_2026 | Lift | Stability | Verdict |
|-----------|--------|---------|---------|------|-----------|---------|
| `breadth > 0.6281` | feature_match | 0.000 | 0.500 | 1.50 | 0.00 | ⚠ INSUFFICIENT_DATA |
| `rsi <= 29.6705` | edge_lifecycle | 0.368 | 0.405 | 1.21 | 0.91 | ✔ VALIDATED |
| `mom_5d > -0.0173` | feature_match | 0.272 | 0.369 | 1.11 | 0.74 | ⚠ PARTIALLY_VALIDATED |
| `mom_5d > -0.0115` | feature_match | 0.273 | 0.369 | 1.10 | 0.74 | ⚠ PARTIALLY_VALIDATED |
| `mom_20d <= -0.1299` | edge_lifecycle | 0.360 | 0.360 | 1.08 | 1.00 | ⚠ PARTIALLY_VALIDATED |
| `mom_20d > 0.0310` | edge_lifecycle | 0.360 | 0.360 | 1.08 | 1.00 | ⚠ PARTIALLY_VALIDATED |
| `mom_20d <= 0.0277` | edge_lifecycle | 0.360 | 0.360 | 1.08 | 1.00 | ⚠ PARTIALLY_VALIDATED |
| `event_count <= 0.1000` | feature_match | 0.296 | 0.359 | 1.07 | 0.83 | ⚠ PARTIALLY_VALIDATED |
| `mom_5d <= -0.0084` | feature_match | 0.327 | 0.348 | 1.04 | 0.94 | ⚠ PARTIALLY_VALIDATED |
| `mom_5d <= -0.0102` | feature_match | 0.347 | 0.338 | 1.01 | 0.98 | ⚠ PARTIALLY_VALIDATED |
| `pcr > 0.4002` | feature_match | 0.310 | 0.320 | 0.96 | 0.97 | ✗ REJECTED |
| `rsi_norm <= 0.3977` | edge_lifecycle | 0.222 | 0.244 | 0.73 | 0.91 | ✗ REJECTED |
| `volume_spike > 0.0000` | edge_lifecycle | 0.214 | 0.236 | 0.71 | 0.91 | ✗ REJECTED |
| `volume_ratio_raw <= 1.9447` | edge_lifecycle | 0.148 | 0.133 | 0.40 | 0.90 | ✗ REJECTED |
| `mom_10d > -0.0272` | edge_lifecycle | 0.133 | 0.133 | 0.40 | 1.00 | ✗ REJECTED |
| `mom_10d <= -0.0248` | edge_lifecycle | 0.133 | 0.133 | 0.40 | 1.00 | ✗ REJECTED |
| `sector_strength <= 0.2573` | edge_lifecycle | 0.083 | 0.092 | 0.27 | 0.91 | ✗ REJECTED |
| `sector_flow_count <= 0.3000` | feature_match | 0.000 | 0.000 | 0.00 | 1.00 | ⚠ INSUFFICIENT_DATA |
| `macd_signal_norm > 0.6361` | edge_lifecycle | 0.000 | 0.000 | 0.00 | 1.00 | ✗ REJECTED |
| `bb_position <= -0.6604` | edge_lifecycle | 0.000 | 0.000 | 0.00 | 1.00 | ✗ REJECTED |

## Summary

- Validated: **1**
- Partially validated: **8**
- Rejected: **9**
- Insufficient data: **2**

**Hypothesis Verdict: `PARTIALLY_CONFIRMED`**