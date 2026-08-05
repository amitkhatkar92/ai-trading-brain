# KVA Discovery Intelligence

**Issue:** KVA-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  


**Category Score:** 68.7/100  

### What are the top discoveries (highest confidence / most valuable)?

**Answer:** Top OOS win rate: EDG_VOLATI_91_EE0004(100.00%) — IF pcr > 0.400 AND bb_position > 0.397 AND mom_1d > 0.005 THEN bullish with 92% . Highest Sharpe: EDG_MOMENT_100_EE0005(Sharpe=62.38). Best composite: EDG_MOMENT_86_EE0002(score=6.240).

### Which discoveries are most surprising / novel?

**Answer:** Most surprising discovery: EDG_MOMENT_100_EE0005 (category=momentum_volume, Sharpe=62.38, OOS=100.00%). Description: IF mom_5d > 0.006 AND volume_ratio > 0.506 AND iv_rank <= 0.610 THEN bullish wit

### Which discoveries require more evidence?

**Answer:** 17 edges show high OOS win rate (≥70%) but low support (n<20) — these require more evidence. Total edge library: 259 edges with avg support=78.9.

## Top 20 Discoveries by OOS Win Rate

| Rank | Edge | OOS Win Rate | Sharpe | Support | WF | Category | Description |
|------|------|-------------|--------|---------|----|---------| ------------|
| 1 | EDG_VOLATI_91_EE0004 | 100.00% | 32.17 | 25 | 1.00 | volatility | IF pcr > 0.400 AND bb_position > 0.397 AND mom_1d > 0.005 TH |
| 2 | EDG_VOLATI_93_EE0002 | 100.00% | 32.17 | 25 | 0.80 | volatility | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND bb_positio |
| 3 | EDG_VOLATI_94_EE0002 | 100.00% | 32.17 | 25 | 0.80 | volatility | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND bb_positio |
| 4 | EDG_VOLATI_99_EE0003 | 100.00% | 32.22 | 20 | 0.20 | volatility | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND bb_positio |
| 5 | EDG_MOMENT_95_EE0004 | 100.00% | 47.41 | 21 | 1.00 | momentum_volume | IF macd_signal_norm > 0.636 AND volume_ratio > 0.486 AND iv_ |
| 6 | EDG_MOMENT_98_EE0003 | 100.00% | 47.41 | 26 | 0.80 | momentum_volume | IF event_count <= 0.100 AND volume_ratio_raw > 1.941 AND gap |
| 7 | EDG_MOMENT_98_EE0004 | 100.00% | 47.41 | 28 | 0.60 | momentum_volume | IF volume_ratio > 0.479 AND gap_pct > 0.001 AND volume_ratio |
| 8 | EDG_MOMENT_90_EE0002 | 100.00% | 34.30 | 22 | 1.00 | momentum_volume | IF volume_ratio > 0.479 AND gap_pct <= 0.001 AND gap_pct <=  |
| 9 | EDG_MOMENT_97_EE0005 | 100.00% | 35.02 | 29 | 1.00 | momentum_volume | IF volume_ratio > 0.479 AND vix > 0.471 AND macd_signal_norm |
| 10 | EDG_MOMENT_100_EE0005 | 100.00% | 62.38 | 16 | 1.00 | momentum_volume | IF mom_5d > 0.006 AND volume_ratio > 0.506 AND iv_rank <= 0. |
| 11 | EDG_MOMENT_96_EE0002 | 100.00% | 47.41 | 21 | 1.00 | momentum_volume | IF event_count <= 0.100 AND macd_signal_norm > 0.636 AND vol |
| 12 | EDG_MOMENT_97_EE0002 | 100.00% | 41.19 | 21 | 1.00 | momentum_volume | IF event_count <= 0.100 AND macd_signal_norm > 0.636 AND vol |
| 13 | EDG_MOMENT_95_EE0002 | 100.00% | 47.41 | 21 | 1.00 | momentum_volume | IF macd_signal_norm > 0.636 AND sector_flow_count <= 0.300 A |
| 14 | EDG_MOMENT_97_EE0003 | 100.00% | 47.41 | 21 | 0.80 | momentum_volume | IF event_count <= 0.100 AND macd_signal_norm > 0.636 AND vol |
| 15 | EDG_MOMENT_95_EE0005 | 100.00% | 47.41 | 21 | 1.00 | momentum_volume | IF macd_signal_norm > 0.636 AND volume_ratio_raw > 1.945 AND |
| 16 | EDG_MOMENT_96_EE0004 | 100.00% | 47.41 | 21 | 1.00 | momentum_volume | IF macd_signal_norm > 0.636 AND sector_flow_count <= 0.300 A |
| 17 | EDG_MOMENT_98_EE0002 | 100.00% | 37.28 | 27 | 0.80 | momentum_volume | IF event_count <= 0.100 AND mom_5d > -0.011 AND volume_ratio |
| 18 | EDG_MOMENT_100_EE0004 | 100.00% | 43.00 | 15 | 0.60 | momentum_volume | IF sector_flow_count <= 0.300 AND mom_5d > -0.011 AND regime |
| 19 | EDG_MOMENT_100_EE0003 | 100.00% | 43.00 | 16 | 0.80 | momentum_volume | IF global_bias <= 0.881 AND volume_ratio_raw > 2.012 AND his |
| 20 | EDG_MOMENT_94_EE0001 | 100.00% | 33.64 | 23 | 0.80 | momentum_volume | IF global_bias <= 0.881 AND mom_5d > -0.011 AND regime_score |