# FEATURE_VOCABULARY_REPORT.md

**Study:** RII-001 Phase 1 — Feature Vocabulary Expansion
**Date:** 2026-08-06
**Generated:** 2026-08-06T11:12:26

## Objective

Verify that every feature used by Winner DNA, Loser DNA, Contextual DNA, and Compound DNA
patterns exists inside the feature database (ede_feature_db.json).

## Database Summary

| Metric | Value |
|---|---|
| Total records in feature_db | 5,000 |
| Total unique feature keys | 58 |
| DNA vocabulary size | 17 |
| DNA features PRESENT | 16/17 |
| DNA features MISSING | 1/17 |

## DNA Feature Presence Analysis

| Feature | Present in DB | Records with Value | Coverage |
|---|---|---|---|
| `atr_14` | ❌ MISSING | 0 | 0% |
| `intra_range` | ✅ | 4,980 | 99% |
| `mom_5d` | ✅ | 5,000 | 100% |
| `close_pos` | ✅ | 4,980 | 99% |
| `sect_conviction` | ✅ | 4,980 | 99% |
| `sect_part5d` | ✅ | 4,980 | 99% |
| `avg_conviction` | ✅ | 4,980 | 99% |
| `mom_1d` | ✅ | 5,000 | 100% |
| `mom_10d` | ✅ | 20 | 0% |
| `mom_20d` | ✅ | 20 | 0% |
| `vol_ratio` | ✅ | 4,980 | 99% |
| `cons_up_days` | ✅ | 4,980 | 99% |
| `breadth` | ✅ | 5,000 | 100% |
| `sector_flow_count` | ✅ | 5,000 | 100% |
| `sector_strength` | ✅ | 20 | 0% |
| `volume_spike` | ✅ | 20 | 0% |
| `pcr` | ✅ | 5,000 | 100% |

## Critical Finding: atr_14 Completely Absent

`atr_14` (14-period Average True Range as % of close) is present in **0/5,000** records.

This is the highest-importance feature in the IIOS knowledge base:
- Random Forest importance rank: **#1** (importance = 0.334)
- Required by **all 9 compound Winner DNA patterns** (W01–W09)
- IRP-002 was forced to classify all compound patterns as INSUFFICIENT_DATA

### Root Cause

`atr_14` requires the previous 14 trading days of high/low/close data to compute.
The feature database was populated without including this computation.
The OHLCV data required is available in `replay.db` (256,268 rows, 2021–2025).

## All Feature Keys Found in Database

```
adx_score
avg_conviction
bb_lower
bb_position
bb_upper
breadth
breadth_strong
breadth_weak
close_pos
cons_up_days
event_count
gap_down
gap_pct
gap_up
global_bias
hist_vol_20d
hist_vol_5d
intra_range
iv_low
iv_rank
iv_spike
liquidity_score
macd_bear
macd_bull
macd_signal_norm
mom_10d
mom_1d
mom_20d
mom_5d
mom_positive
pcr
pcr_bearish
pcr_bullish
pcr_neutral
regime_bear
regime_bull
regime_range
regime_score
regime_volatile
rsi
rsi_neutral
rsi_norm
rsi_overbought
rsi_oversold
sect_conviction
sect_part5d
sector_flow_count
sector_strength
strong_trend
vix
vix_high
vix_low
vol_compression
vol_ratio
vol_score
volume_ratio
volume_ratio_raw
volume_spike
```

## Action Required

Phase 2 will:
1. Backfill `atr_14` for all 5,000 existing records where OHLCV data is available.
2. Expand the database to cover 2021–2024 with full feature computation.
3. Target: 2,000+ records with `atr_14` present.
