# FEATURE_HISTORY_REPORT.md

**Study:** RII-001 Phase 2 — Historical Feature Expansion
**Date:** 2026-08-06
**Generated:** 2026-08-06T11:12:31

## Objective

Expand the feature database from 5,000 records (2025–2026 only) to 205,274
records spanning 2021–2026, with `atr_14` backfilled throughout.

## Expansion Summary

| Metric | Before | After |
|---|---|---|
| Total records | 5,000 | 205,274 |
| Records with `atr_14` | 0 | 202,214 |
| `atr_14` coverage | 0% | 98% |
| Year span | 2025–2026 | 2021–2026 |
| Symbols covered | 41 | 229 |
| Target (2,000+ with atr_14) | — | ✅ MET |

## Year Distribution

| Year | Records | % of Total |
|---|---|---|
| 2021 | 46,462 | 22% |
| 2022 | 51,333 | 25% |
| 2023 | 51,065 | 24% |
| 2024 | 51,414 | 25% |
| 2025 | 1,960 | 0% |
| 2026 | 3,040 | 1% |

## Sector Distribution (Top 10)

| Sector | Records |
|---|---|
| BANKING_FINANCE | 28,682 |
| PHARMA | 18,729 |
| INFRA | 18,729 |
| CONSUMER_DURABLES | 18,183 |
| CHEMICALS | 17,622 |
| FMCG | 17,318 |
| AUTO | 16,968 |
| IT | 16,819 |
| ENERGY | 15,568 |
| METALS | 15,103 |

## Regime Distribution

| Regime | Records |
|---|---|
| SIDEWAYS | 132,734 |
| TRENDING_UP | 52,919 |
| TRENDING_DOWN | 19,601 |
| None | 20 |

## Forward Return Label Distribution

| Label | Count | Rate |
|---|---|---|
| Winner (fr > +0.5%) | 97,176 | 47% |
| Loser  (fr < -0.5%) | 84,898 | 41% |
| Neutral | 23,200 | 11% |

## Temporal Integrity

All forward returns computed strictly from in-sample OHLCV data.
2021–2024 records use 5-day forward returns from `replay.db`.
No lookahead contamination. Source tagged as `S001_REPLAY_DB`.

## Data Source

| Source | Records |
|---|---|
| `S001_REPLAY_DB` (new 2021–2024) | 200,274 |
| `S002_OHLCV` (existing 2025–2026) | 5,000 |

## atr_14 Backfill

- Existing records backfilled: 1,940
- New records with atr_14: 200,274
- Total records with atr_14: 202,214
