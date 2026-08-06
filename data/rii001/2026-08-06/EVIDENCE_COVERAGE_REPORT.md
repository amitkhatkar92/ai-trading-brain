# EVIDENCE_COVERAGE_REPORT.md

**Study:** RII-001 Phase 3 — Evidence Coverage Audit
**Date:** 2026-08-06
**Generated:** 2026-08-06T11:12:32

## Objective

Measure evidence coverage per year, sector, regime, market condition, feature, and direction.
Identify coverage gaps.

## Overall Coverage Summary

| Dimension | Coverage | Count |
|---|---|---|
| Total records | — | 205,274 |
| Year span | 2021 – 2026 | 6 years |
| Unique sectors | — | 12 |
| Unique regimes | — | 3 |
| Features with data | — | 59 |
| Target year span (≥4) | ✅ | 6/4 |
| Target sectors (≥5) | ✅ | 12/5 |
| Target regimes (≥2) | ✅ | 3/2 |

## Year × Record Count

| Year | Records | % |
|---|---|---|
| 2021 | 46,462 | 22% |
| 2022 | 51,333 | 25% |
| 2023 | 51,065 | 24% |
| 2024 | 51,414 | 25% |
| 2025 | 1,960 | 0% |
| 2026 | 3,040 | 1% |

## Year × Sector Coverage Matrix

| Year | AUTO | BANKING_FI | CHEMICALS | CONSUMER_D | DEFENCE | ENERGY | FMCG | INFRA |
|---|---|---|---|---|---|---|---|---|
| 2021 | 3921 | 6767 | 4078 | 3920 | 2389 | 3744 | 3761 | 4446 |
| 2022 | 4216 | 7192 | 4464 | 4458 | 2968 | 3968 | 4235 | 4712 |
| 2023 | 4165 | 7105 | 4410 | 4410 | 3045 | 3920 | 4410 | 4655 |
| 2024 | 4182 | 7134 | 4428 | 4428 | 3198 | 3936 | 4428 | 4674 |
| 2025 | 196 | 196 | 98 | 392 | 0 | 0 | 196 | 98 |
| 2026 | 288 | 288 | 144 | 575 | 0 | 0 | 288 | 144 |

## Year × Regime Coverage

| Year | SIDEWAYS | TRENDING_DOWN | TRENDING_UP |
|---|---|---|---|
| 2021 | 27870 | 2842 | 15750 |
| 2022 | 27723 | 11178 | 12432 |
| 2023 | 37519 | 624 | 12922 |
| 2024 | 35739 | 4180 | 11495 |
| 2025 | 1640 | 0 | 320 |
| 2026 | 2243 | 777 | 0 |

## Feature Presence Rates (DNA Features)

| Feature | Records | Coverage | Status |
|---|---|---|---|
| `atr_14` | 202,214 | 98% | ✅ |
| `intra_range` | 205,254 | 99% | ✅ |
| `mom_5d` | 205,274 | 100% | ✅ |
| `close_pos` | 205,073 | 99% | ✅ |
| `sect_conviction` | 199,774 | 97% | ✅ |
| `sect_part5d` | 199,774 | 97% | ✅ |
| `avg_conviction` | 205,254 | 99% | ✅ |
| `mom_1d` | 205,274 | 100% | ✅ |
| `mom_10d` | 200,294 | 97% | ✅ |
| `mom_20d` | 199,040 | 96% | ✅ |
| `vol_ratio` | 204,000 | 99% | ✅ |
| `cons_up_days` | 205,254 | 99% | ✅ |
| `breadth` | 205,274 | 100% | ✅ |
| `sector_flow_count` | 5,000 | 2% | ✅ |
| `sector_strength` | 20 | 0% | ⚠️ PARTIAL |
| `volume_spike` | 20 | 0% | ⚠️ PARTIAL |
| `pcr` | 5,000 | 2% | ✅ |

## Coverage Gap Identification

- Feature gap: `sector_strength` has only 20 records (need 2000+)
- Feature gap: `volume_spike` has only 20 records (need 2000+)
