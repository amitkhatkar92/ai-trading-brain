# KVA Feature Intelligence

**Issue:** KVA-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  


**Category Score:** 68.0/100  

### Which features are most predictive of forward returns?

**Answer:** Feature-return correlations computed on 500 samples. Most predictive: cons_up_days(r=-0.073), mom_5d(r=-0.066), sect_part5d(r=-0.053), mom_1d(r=-0.047), intra_range(r=-0.046). Least predictive: global_bias(r=-0.004), regime_volatile(r=0.000), pcr_bullish(r=0.000), sector_flow_count(r=0.000), event_count(r=0.000).

### Which features are stable vs unstable across regimes?

**Answer:** Most stable features across regimes (low variance): regime_volatile(var=0.00000), event_count(var=0.00000), pcr_bullish(var=0.00000), sector_flow_count(var=0.00000), mom_1d(var=0.00001). Most unstable (high variance): regime_range(var=0.22222), regime_bull(var=0.22222), vix_low(var=0.22222), regime_bear(var=0.22222), vix_high(var=0.22222).

### What hidden feature interactions drive edge performance?

**Answer:** 243 edges require 3+ feature interactions. Top interactions: [pcr+bb_position+mom_1d](oos=1.00); [sector_flow_count+pcr+bb_position+mom_1d](oos=1.00); [sector_flow_count+pcr+bb_position+mom_1d](oos=1.00)

## Feature-Return Correlations

(n=500 samples)

| Feature | Correlation | |Direction| Predictive Power |
|---------|-------------|---------|-----------------|
| cons_up_days | -0.0733 | ↓ negative | **MEDIUM** |
| mom_5d | -0.0665 | ↓ negative | **MEDIUM** |
| sect_part5d | -0.0529 | ↓ negative | **MEDIUM** |
| mom_1d | -0.0467 | ↓ negative | **LOW** |
| intra_range | -0.0461 | ↓ negative | **LOW** |
| close_pos | -0.0431 | ↓ negative | **LOW** |
| sect_conviction | -0.0374 | ↓ negative | **LOW** |
| avg_conviction | -0.0260 | ↓ negative | **LOW** |
| breadth | -0.0260 | ↓ negative | **LOW** |
| pcr | -0.0260 | ↓ negative | **LOW** |
| regime_range | 0.0194 | ↑ positive | **LOW** |
| regime_bear | -0.0174 | ↓ negative | **LOW** |
| vix_low | 0.0174 | ↑ positive | **LOW** |
| vix_high | -0.0174 | ↓ negative | **LOW** |
| vol_ratio | -0.0171 | ↓ negative | **LOW** |
| vix | -0.0140 | ↓ negative | **LOW** |
| pcr_neutral | -0.0103 | ↓ negative | **LOW** |
| breadth_weak | 0.0103 | ↑ positive | **LOW** |
| pcr_bearish | 0.0103 | ↑ positive | **LOW** |
| regime_score | 0.0097 | ↑ positive | **LOW** |
| breadth_strong | 0.0081 | ↑ positive | **LOW** |
| regime_bull | -0.0072 | ↓ negative | **LOW** |
| global_bias | -0.0042 | ↓ negative | **LOW** |
| regime_volatile | 0.0000 | ↓ negative | **LOW** |
| pcr_bullish | 0.0000 | ↓ negative | **LOW** |
| sector_flow_count | 0.0000 | ↓ negative | **LOW** |
| event_count | 0.0000 | ↓ negative | **LOW** |

## Feature Appearance in Discovery Conditions

| Feature | Edge Appearances |
|---------|-----------------|
| sector_flow_count | 123 |
| pcr | 104 |
| mom_5d | 100 |
| event_count | 79 |
| volume_ratio_raw | 71 |
| macd_signal_norm | 62 |
| volume_ratio | 40 |
| mom_10d | 39 |
| liquidity_score | 33 |
| bb_position | 30 |
| global_bias | 26 |
| iv_rank | 24 |
| gap_pct | 24 |
| regime_bear | 22 |
| mom_20d | 21 |
| regime_score | 19 |
| breadth | 16 |
| sector_strength | 16 |
| hist_vol_20d | 11 |
| volume_spike | 10 |