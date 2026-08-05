# KVA DNA Intelligence

**Issue:** KVA-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  


**Category Score:** 58.6/100  

### Which DNA survived all regimes?

**Answer:** 85 edges have WF consistency ≥ 0.8 and OOS win rate ≥ 60%. Top regime-survivors: EDG_VOLATI_91_EE0004(wf=1.0 oos=1.00); EDG_VOLATI_93_EE0002(wf=0.8 oos=1.00); EDG_VOLATI_94_EE0002(wf=0.8 oos=1.00); EDG_MOMENT_95_EE0004(wf=1.0 oos=1.00); EDG_MOMENT_98_EE0003(wf=0.8 oos=1.00)

### Which DNA disappeared / is decaying?

**Answer:** 132 edges are DECAYING (signals weakening), 125 edges are CANDIDATE (being evaluated). DECAYING edges are DNA patterns that were valid but lost predictive power.

### Which DNA evolved?

**Answer:** IKN records 1 EVOLVED_TO relationships. Total DNA nodes in IKN: 22. DNA evolution tracking is operational through IKN versioning.

### Which DNA contradicts another DNA?

**Answer:** IKN records 1 CONTRADICTED_BY relationships. Edge categories suggest potential contradictions: 9 composite vs 67 volatility edges may operate on opposing regime assumptions.

## DNA Categories

| Category | Count |
|----------|-------|
| momentum_volume | 103 |
| volatility | 67 |
| macro_flow | 60 |
| momentum_trend | 20 |
| composite | 9 |

## Regime-Robust DNA (WF≥0.8, OOS≥60%)

| Edge | OOS Win Rate | WF Consistency | Sharpe | Description |
|------|-------------|----------------|--------|-------------|
| EDG_VOLATI_91_EE0004 | 100.00% | 1.00 | 32.17 | IF pcr > 0.400 AND bb_position > 0.397 AND mom_1d > 0.005 TH |
| EDG_VOLATI_93_EE0002 | 100.00% | 0.80 | 32.17 | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND bb_positio |
| EDG_VOLATI_94_EE0002 | 100.00% | 0.80 | 32.17 | IF sector_flow_count <= 0.300 AND pcr > 0.400 AND bb_positio |
| EDG_MOMENT_95_EE0004 | 100.00% | 1.00 | 47.41 | IF macd_signal_norm > 0.636 AND volume_ratio > 0.486 AND iv_ |
| EDG_MOMENT_98_EE0003 | 100.00% | 0.80 | 47.41 | IF event_count <= 0.100 AND volume_ratio_raw > 1.941 AND gap |
| EDG_MOMENT_90_EE0002 | 100.00% | 1.00 | 34.30 | IF volume_ratio > 0.479 AND gap_pct <= 0.001 AND gap_pct <=  |
| EDG_MOMENT_97_EE0005 | 100.00% | 1.00 | 35.02 | IF volume_ratio > 0.479 AND vix > 0.471 AND macd_signal_norm |
| EDG_MOMENT_100_EE0005 | 100.00% | 1.00 | 62.38 | IF mom_5d > 0.006 AND volume_ratio > 0.506 AND iv_rank <= 0. |
| EDG_MOMENT_96_EE0002 | 100.00% | 1.00 | 47.41 | IF event_count <= 0.100 AND macd_signal_norm > 0.636 AND vol |
| EDG_MOMENT_97_EE0002 | 100.00% | 1.00 | 41.19 | IF event_count <= 0.100 AND macd_signal_norm > 0.636 AND vol |