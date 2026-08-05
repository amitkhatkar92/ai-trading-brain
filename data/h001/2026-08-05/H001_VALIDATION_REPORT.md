# H001 Validation Report

**Study:** H-CRITICAL-001  
**Hypothesis:** H2026-08-001 — Loser DNA cross-year validation  
**Date:** 2026-08-05  


## Statistical Validation

### Chi-squared p-values

| Condition | p-value | Significant (p<0.15) |
|-----------|---------|---------------------|
| `volume_spike > 0.0000` | 0.000 | ✔ |
| `sector_flow_count <= 0.3000` | 1.000 | ✗ |
| `mom_10d > -0.0272` | 0.000 | ✔ |
| `sector_strength <= 0.2573` | 0.000 | ✔ |
| `pcr > 0.4002` | 0.807 | ✗ |
| `mom_5d <= -0.0102` | 0.930 | ✗ |
| `breadth > 0.6281` | 1.000 | ✗ |
| `mom_5d > -0.0115` | 0.003 | ✔ |
| `mom_20d <= -0.1299` | 1.000 | ✗ |
| `event_count <= 0.1000` | 0.000 | ✔ |
| `mom_5d > -0.0173` | 0.001 | ✔ |
| `macd_signal_norm > 0.6361` | 0.000 | ✔ |
| `volume_ratio_raw <= 1.9447` | 0.019 | ✔ |
| `mom_10d <= -0.0248` | 0.000 | ✔ |
| `mom_20d > 0.0310` | 1.000 | ✗ |
| `bb_position <= -0.6604` | 0.000 | ✔ |
| `rsi <= 29.6705` | 1.000 | ✗ |
| `mom_5d <= -0.0084` | 0.930 | ✗ |
| `mom_20d <= 0.0277` | 1.000 | ✗ |
| `rsi_norm <= 0.3977` | 0.127 | ✔ |

### Cross-Regime Stability

- **SIDEWAYS**: avg_hit_rate = 0.340 across 6 conditions
- **TRENDING_DOWN**: avg_hit_rate = 0.370 across 6 conditions

### Walk-Forward Consistency

- Training period (2025): in-sample hit rates established
- Validation period (2026): out-of-sample hit rates computed
- Avg cross-year stability: 0.886
- Conditions with stability >= 0.65: 19/20