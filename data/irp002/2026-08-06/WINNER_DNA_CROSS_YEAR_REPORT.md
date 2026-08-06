# WINNER_DNA_CROSS_YEAR_REPORT.md

**Study:** IRP-002 — Winner DNA Cross-Year Validation
**Date:** 2026-08-06
**Source:** study002a (9 patterns, 2021-2025)
**Method:** feature_match ONLY

## Dataset

- KP feature records: 500
- Training year (2025): 196 records
- Validation year (2026): 304 records
- Winner DNA patterns tested: 9

## Individual Condition Results

| Condition | Pattern | hr_2025 | hr_2026 | Lift | Stability | Verdict |
|---|---|---|---|---|---|---|
| `intra_range <= 0.0432` | W01 | 0.311 | 0.345 | 1.03 | 0.90 | PARTIALLY_VALIDATED |
| `intra_range <= 0.005` | W01 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `mom_5d > -0.0606` | W01 | 0.321 | 0.349 | 1.04 | 0.92 | PARTIALLY_VALIDATED |
| `sect_conviction > 0.0507` | W01 | 0.324 | 0.368 | 1.10 | 0.88 | PARTIALLY_VALIDATED |
| `intra_range > 0.005` | W02 | 0.308 | 0.359 | 1.07 | 0.86 | PARTIALLY_VALIDATED |
| `close_pos > 0.9868` | W02 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `sect_conviction > 0.5001` | W02 | 0.323 | 0.317 | 0.94 | 0.98 | REJECTED |
| `intra_range > 0.0432` | W03 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `mom_5d > -0.0651` | W03 | 0.318 | 0.353 | 1.05 | 0.90 | PARTIALLY_VALIDATED |
| `close_pos > 0.9964` | W03 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `mom_5d > 0.0548` | W03 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `mom_5d <= -0.0651` | W04 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `intra_range > 0.0593` | W04 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `sect_part5d <= 0.0516` | W04 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `sect_part5d > 0.0516` | W05 | 0.311 | 0.362 | 1.08 | 0.86 | PARTIALLY_VALIDATED |
| `intra_range <= 0.0593` | W06 | 0.311 | 0.349 | 1.04 | 0.89 | PARTIALLY_VALIDATED |
| `avg_conviction > 0.0002` | W06 | 0.311 | 0.359 | 1.07 | 0.87 | PARTIALLY_VALIDATED |
| `intra_range > 0.0242` | W07 | 0.200 | 0.396 | 1.18 | 0.50 | REJECTED |
| `intra_range > 0.0385` | W07 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `avg_conviction <= 0.172` | W07 | 0.371 | 0.433 | 1.29 | 0.86 | PARTIALLY_VALIDATED |
| `intra_range > 0.0532` | W07 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `close_pos <= 0.9964` | W08 | 0.311 | 0.352 | 1.05 | 0.88 | PARTIALLY_VALIDATED |
| `intra_range > 0.0687` | W08 | 0.000 | 0.000 | 0.00 | 0.00 | INSUFFICIENT_DATA |
| `mom_5d <= -0.0606` | W09 | 0.000 | 0.400 | 1.19 | 0.00 | REJECTED |


**Summary:**
- Validated: 0
- Partially Validated: 10
- Rejected: 3
- Insufficient Data: 11

## Compound Pattern Results (atr_14 excluded)

| Pattern | atr_14 missing | hr_2025 | hr_2026 | Lift | Verdict |
|---|---|---|---|---|---|
| W01 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W02 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W03 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W04 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W05 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W06 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W07 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W08 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |
| W09 | YES | 0.000 | 0.000 | 0.00 | INSUFFICIENT_DATA |


**Note:** All compound patterns are tested WITHOUT `atr_14` (not in feature_db).
Results represent the sub-pattern only. Adding atr_14 > 0.0289 as a filter
would reduce n_train_met and may change verdicts.
