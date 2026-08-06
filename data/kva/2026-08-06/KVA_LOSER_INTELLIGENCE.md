# KVA Loser Intelligence

**Issue:** KVA-001  
**Date:** 2026-08-06  
**Version:** 1.0.0  


**Category Score:** 74.8/100  

### Why do stocks underperform?

**Answer:** 51 loser DNA records from 2 studies. Top conditions: mom_5d(n=22), sector_flow_count(n=17), mom_20d(n=17), volume_spike(n=7), event_count(n=7)

**Confidence:** 0.80  
**Score:** 79.0/100

### What DNA consistently predicts failure?

**Answer:** 5 edges show OOS win rate < 40%. Worst: volume_spike > 0.000 → 59% hit rate. IDR loser DNA reinforces these failure conditions: 15 records.

**Confidence:** 0.85  
**Score:** 77.2/100

### Which loser DNA survived all years?

**Answer:** IDR loser DNA: 15 records from Study-003 (2021-2025). Cross-year validation pending — KMP Hypothesis H-CRITICAL-001. Earliest loser DNA covers 5-year period (2021-2025). Statistical derivation: 51 patterns analysed.

**Confidence:** 0.70  
**Score:** 68.1/100

## Gap Assessment

- Loser DNA records: **36** (critically insufficient)
- Action required: systematic loser study using HKAP underperformer cohort
- Without loser knowledge, IIOS cannot reason about asymmetric risk

## Failing Edges (OOS Win Rate < 50%)

| Edge | OOS Win Rate | Precision | Description |
|------|-------------|-----------|-------------|
| EDG_MOMENT_59_>0.000 | 0.00% | 59.42% | volume_spike > 0.000 → 59% hit rate |
| EDG_MOMENT_62_>0.000 | 0.00% | 62.12% | volume_spike > 0.000 → 62% hit rate |
| EDG_MOMENT_60_>0.000 | 14.29% | 60.24% | volume_spike > 0.000 → 60% hit rate |
| EDG_MACRO__86_EE0001 | 35.29% | 86.86% | IF sector_flow_count <= 0.300 AND mom_10d > -0.027 AND secto |
| EDG_MOMENT_59_EE0003 | 37.50% | 59.08% | IF macd_signal_norm > 0.636 AND volume_ratio_raw <= 1.945 AN |
| EDG_MACRO__93_EE0000 | 40.00% | 93.51% | IF sector_flow_count <= 0.300 AND bb_position <= -0.660 AND  |
| EDG_MOMENT_96_EE0000 | 43.33% | 96.43% | IF event_count <= 0.100 AND mom_5d <= -0.008 AND mom_20d <=  |
| EDG_VOLATI_88_EE0001 | 45.45% | 88.84% | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND mom_5d <=  |
| EDG_VOLATI_89_EE0001 | 45.45% | 89.12% | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND mom_5d <=  |
| EDG_VOLATI_90_EE0001 | 45.45% | 90.09% | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND mom_5d <=  |