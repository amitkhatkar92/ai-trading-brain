# COMPOUND_DNA_REPORT.md

**Study:** RII-001 Phase 5 — Compound DNA Support
**Date:** 2026-08-06
**Generated:** 2026-08-06T11:12:33

## Objective

Re-run compound Winner DNA validation from IRP-002 using the expanded feature database
(now containing `atr_14`). Previously all 9 compound patterns returned INSUFFICIENT_DATA
because atr_14 was absent.

## Test Population

| Metric | Value |
|---|---|
| Records with atr_14 | 202,214 |
| Winner base rate | 0.475 (47.5%) |
| Patterns tested | 9 |
| Lift threshold (VALIDATED) | ≥ 1.20 |
| Lift threshold (PARTIAL) | ≥ 1.05 |

## Pattern Results

| Pattern | Outcome | n_matched | Win Rate | Lift | Original Lift |
|---|---|---|---|---|---|
| W01 | VALIDATED | 90 | 0.678 | 1.4273 | 2.5733 |
| W02 | PARTIAL | 97 | 0.536 | 1.1289 | 3.088 |
| W03 | PARTIAL | 154 | 0.526 | 1.1076 | 2.3394 |
| W04 | VALIDATED | 803 | 0.704 | 1.4817 | 2.6067 |
| W05 | VALIDATED | 2024 | 0.608 | 1.2798 | 1.6631 |
| W06 | PARTIAL | 2487 | 0.565 | 1.1889 | 1.5156 |
| W07 | PARTIAL | 621 | 0.543 | 1.1428 | 1.29 |
| W08 | REJECTED | 6543 | 0.476 | 1.0026 | 1.3721 |
| W09 | REJECTED | 42 | 0.191 | 0.4011 | 1.1484 |

## Summary

| Outcome | Count |
|---|---|
| VALIDATED (lift ≥ 1.20) | 3 |
| PARTIAL (lift ≥ 1.05) | 4 |
| REJECTED (lift < 1.05) | 2 |
| INSUFFICIENT_DATA (n < 5) | 0 |

## Pattern Conditions

### W01 — VALIDATED
- `atr_14 > 0.0289`
- `intra_range <= 0.0432`
- `intra_range <= 0.005`
- `mom_5d > -0.0606`
- `sect_conviction > 0.0507`
- **Lift: 1.4273** (win_rate=0.678, n=90)

### W02 — PARTIAL
- `atr_14 > 0.0289`
- `intra_range <= 0.0432`
- `intra_range > 0.005`
- `close_pos > 0.9868`
- `sect_conviction > 0.5001`
- **Lift: 1.1289** (win_rate=0.536, n=97)

### W03 — PARTIAL
- `atr_14 > 0.0289`
- `intra_range > 0.0432`
- `mom_5d > -0.0651`
- `close_pos > 0.9964`
- `mom_5d > 0.0548`
- **Lift: 1.1076** (win_rate=0.526, n=154)

### W04 — VALIDATED
- `atr_14 > 0.0289`
- `intra_range > 0.0432`
- `mom_5d <= -0.0651`
- `intra_range > 0.0593`
- `sect_part5d <= 0.0516`
- **Lift: 1.4817** (win_rate=0.704, n=803)

### W05 — VALIDATED
- `atr_14 > 0.0289`
- `intra_range > 0.0432`
- `mom_5d <= -0.0651`
- `intra_range > 0.0593`
- `sect_part5d > 0.0516`
- **Lift: 1.2798** (win_rate=0.608, n=2024)

### W06 — PARTIAL
- `atr_14 > 0.0289`
- `intra_range > 0.0432`
- `mom_5d <= -0.0651`
- `intra_range <= 0.0593`
- `avg_conviction > 0.0002`
- **Lift: 1.1889** (win_rate=0.565, n=2487)

### W07 — PARTIAL
- `atr_14 <= 0.0289`
- `intra_range > 0.0242`
- `intra_range > 0.0385`
- `avg_conviction <= 0.172`
- `intra_range > 0.0532`
- **Lift: 1.1428** (win_rate=0.543, n=621)

### W08 — REJECTED
- `atr_14 > 0.0289`
- `intra_range > 0.0432`
- `mom_5d > -0.0651`
- `close_pos <= 0.9964`
- `intra_range > 0.0687`
- **Lift: 1.0026** (win_rate=0.476, n=6543)

### W09 — REJECTED
- `atr_14 > 0.0289`
- `intra_range <= 0.0432`
- `intra_range <= 0.005`
- `mom_5d <= -0.0606`
- **Lift: 0.4011** (win_rate=0.191, n=42)

## Interpretation

Compound DNA patterns use multi-condition rules derived from decision tree analysis.
A lift > 1.20 means the pattern identifies stocks that win 20%+ more often than the base rate.
With atr_14 now present in the expanded feature database, these patterns can be tested for
the first time on the full historical record.
