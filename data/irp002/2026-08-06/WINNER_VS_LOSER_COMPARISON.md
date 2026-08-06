# WINNER_VS_LOSER_COMPARISON.md

**Study:** IRP-002 — Symmetric Comparison
**Date:** 2026-08-06

## Identical Methodology Applied

Both sides tested with: feature_match, same years, same thresholds.
edge_lifecycle EXCLUDED from both sides for this comparison.

## Results Comparison

| DNA Type | Condition | Lift | Stability | Verdict |
|---|---|---|---|---|
| WINNER | `intra_range <= 0.0432` | 1.03 | 0.90 | PARTIALLY_VALIDATED |
| WINNER | `mom_5d > -0.0606` | 1.04 | 0.92 | PARTIALLY_VALIDATED |
| WINNER | `sect_conviction > 0.0507` | 1.10 | 0.88 | PARTIALLY_VALIDATED |
| WINNER | `intra_range > 0.005` | 1.07 | 0.86 | PARTIALLY_VALIDATED |
| WINNER | `sect_conviction > 0.5001` | 0.94 | 0.98 | REJECTED |
| WINNER | `mom_5d > -0.0651` | 1.05 | 0.90 | PARTIALLY_VALIDATED |
| WINNER | `sect_part5d > 0.0516` | 1.08 | 0.86 | PARTIALLY_VALIDATED |
| WINNER | `intra_range <= 0.0593` | 1.04 | 0.89 | PARTIALLY_VALIDATED |
| WINNER | `avg_conviction > 0.0002` | 1.07 | 0.87 | PARTIALLY_VALIDATED |
| WINNER | `intra_range > 0.0242` | 1.18 | 0.50 | REJECTED |
| WINNER | `avg_conviction <= 0.172` | 1.29 | 0.86 | PARTIALLY_VALIDATED |
| WINNER | `close_pos <= 0.9964` | 1.05 | 0.88 | PARTIALLY_VALIDATED |
| WINNER | `mom_5d <= -0.0606` | 1.19 | 0.00 | REJECTED |
| LOSER  | `pcr > 0.4002` | 0.96 | 0.97 | REJECTED |
| LOSER  | `mom_5d <= -0.0102` | 1.01 | 0.98 | PARTIALLY_VALIDATED |
| LOSER  | `mom_5d > -0.0115` | 1.10 | 0.74 | PARTIALLY_VALIDATED |
| LOSER  | `event_count <= 0.1000` | 1.07 | 0.83 | PARTIALLY_VALIDATED |
| LOSER  | `mom_5d > -0.0173` | 1.11 | 0.74 | PARTIALLY_VALIDATED |
| LOSER  | `mom_5d <= -0.0084` | 1.04 | 0.94 | PARTIALLY_VALIDATED |

## Summary Statistics

| Metric | Winner DNA | Loser DNA | Delta |
|---|---|---|---|
| Avg Lift (testable) | 1.086 | 1.050 | +0.036 |
| Cross-year survival | 77% | 83% | -6% |
| N testable | 13 | 6 | — |

SE of lift delta: 0.032
Z-score: 1.15 (1.65 = 95% significance)
