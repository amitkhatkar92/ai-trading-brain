# DATA_QUALITY_SCORE.md

**SFR ID:** sfr-20260810-04c43829
**Date:** 2026-08-10
**Generated:** 2026-08-10T16:37:48

---

## Scientific Data Readiness Score

| Score | Classification |
|---|---|
| **5.8 / 100** | **INSUFFICIENT** |

Classification scale:
- EXCELLENT: ≥ 85
- GOOD:      ≥ 70
- ADEQUATE:  ≥ 55
- LIMITED:   ≥ 40
- INSUFFICIENT: < 40

---

## Dimension Scores

| # | Dimension | Score | Raw Value | Unit | Threshold | Status |
|---|---|---|---|---|---|---|
| 1 | overall_completeness | 0.0/10 | 0 | records | 0.8 | FAIL |
| 2 | feature_completeness | 0.0/10 | 0 | records_with_atr_14 | 2000 | FAIL |
| 3 | historical_completeness | 0.0/10 | 0 | years | 4 | FAIL |
| 4 | temporal_completeness | 0.0/10 | 999 | avg_gap_days | 30 | FAIL |
| 5 | sector_completeness | 0.0/10 | 0 | sectors | 5 | FAIL |
| 6 | regime_completeness | 0.0/10 | 0 | regimes | 2 | FAIL |
| 7 | direction_completeness | 0.0/10 | 0.0 | sell_fraction | 0.1 | FAIL |
| 8 | compound_completeness | 0.0/10 | 0 | atr14_records_for_compound_testing | 2000 | FAIL |
| 9 | missing_feature_coverage | 0.0/10 | 17 | missing_dna_features | 0 | FAIL |
| 10 | evidence_confidence | 8.3/10 | 0.5 | mean_confidence | 0.6 | MARGINAL |
| 11 | statistical_power | 0.0/10 | 0 | total_feature_records | 2000 | FAIL |

## Detailed Findings

### ❌ overall_completeness
- **Finding:** No feature records.
- **Recommendation:** Run Phase 2 feature expansion.

### ❌ feature_completeness
- **Finding:** Records with atr_14: 0/0 (N/A)
- **Recommendation:** Run rii001.py Phase 2 to backfill atr_14 from replay.db.

### ❌ historical_completeness
- **Finding:** Coverage: N/A (0 years)
- **Recommendation:** Expand historical data to cover 4+ years using replay.db.

### ❌ temporal_completeness
- **Finding:** Fewer than 2 dated records.
- **Recommendation:** Add more feature records.

### ❌ sector_completeness
- **Finding:** Distinct sectors with evidence: 0
- **Recommendation:** Add symbols from 5 more sectors to the universe.

### ❌ regime_completeness
- **Finding:** Distinct regimes: 0 ()
- **Recommendation:** Ensure feature records span multiple market regimes (TRENDING, SIDEWAYS, VOLATILE).

### ❌ direction_completeness
- **Finding:** Edges: BUY=0, SELL=0 (0.0% SELL)
- **Recommendation:** Initiate SELL-side DNA Discovery program (H-SELL-001).

### ❌ compound_completeness
- **Finding:** Compound DNA testable: 0 records with atr_14
- **Recommendation:** Backfill atr_14 using replay.db OHLCV data (see rii001.py).

### ❌ missing_feature_coverage
- **Finding:** Missing DNA features: ['atr_14', 'intra_range', 'mom_5d', 'close_pos', 'sect_conviction', 'sect_part5d', 'avg_conviction', 'mom_1d', 'mom_10d', 'mom_20d', 'vol_ratio', 'cons_up_days', 'breadth', 'sector_flow_count', 'sector_strength', 'volume_spike', 'pcr']
- **Recommendation:** Add ['atr_14', 'intra_range', 'mom_5d', 'close_pos', 'sect_conviction', 'sect_part5d', 'avg_conviction', 'mom_1d', 'mom_10d', 'mom_20d', 'vol_ratio', 'cons_up_days', 'breadth', 'sector_flow_count', 'sector_strength', 'volume_spike', 'pcr'] to feature computation pipeline.

### ⚠️ evidence_confidence
- **Finding:** Mean study confidence: 0.500 (0 studies)
- **Recommendation:** Increase replication studies to raise confidence above 0.60.

### ❌ statistical_power
- **Finding:** Total feature records: 0 (need ≥2,000)
- **Recommendation:** Expand historical feature records using replay.db.

## Identified Weaknesses

- No feature records.
- Records with atr_14: 0/0 (N/A)
- Coverage: N/A (0 years)
- Fewer than 2 dated records.
- Distinct sectors with evidence: 0
- Distinct regimes: 0 ()
- Edges: BUY=0, SELL=0 (0.0% SELL)
- Compound DNA testable: 0 records with atr_14
- Missing DNA features: ['atr_14', 'intra_range', 'mom_5d', 'close_pos', 'sect_conviction', 'sect_part5d', 'avg_conviction', 'mom_1d', 'mom_10d', 'mom_20d', 'vol_ratio', 'cons_up_days', 'breadth', 'sector_flow_count', 'sector_strength', 'volume_spike', 'pcr']
- Total feature records: 0 (need ≥2,000)

## Recommended Infrastructure Improvements

1. Run Phase 2 feature expansion.
1. Run rii001.py Phase 2 to backfill atr_14 from replay.db.
1. Expand historical data to cover 4+ years using replay.db.
1. Add more feature records.
1. Add symbols from 5 more sectors to the universe.
1. Ensure feature records span multiple market regimes (TRENDING, SIDEWAYS, VOLATILE).
1. Initiate SELL-side DNA Discovery program (H-SELL-001).
1. Backfill atr_14 using replay.db OHLCV data (see rii001.py).
1. Add ['atr_14', 'intra_range', 'mom_5d', 'close_pos', 'sect_conviction', 'sect_part5d', 'avg_conviction', 'mom_1d', 'mom_10d', 'mom_20d', 'vol_ratio', 'cons_up_days', 'breadth', 'sector_flow_count', 'sector_strength', 'volume_spike', 'pcr'] to feature computation pipeline.
1. Increase replication studies to raise confidence above 0.60.
1. Expand historical feature records using replay.db.