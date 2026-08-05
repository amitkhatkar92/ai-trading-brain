# H001 Evidence Report

**Study:** H-CRITICAL-001  
**Hypothesis:** H2026-08-001 — Loser DNA cross-year validation  
**Date:** 2026-08-05  


## Evidence Chain

**Source study:** ars_study_003 (15 loser DNA conditions)  
**Validation study:** ars_study_h001  
**Evidence type:** Cross-year temporal validation  

## Per-Condition Evidence

### `volume_spike > 0.0000`
- Method: edge_lifecycle:DECAYING
- 2025 training: n_met=81, n_negative=17, hit_rate=0.214, avg_return=-0.13435
- 2026 validation: n_met=81, n_negative=19, hit_rate=0.236, avg_return=-0.13435
- Base rate: 0.334  Lift: 0.71x  Stability: 0.909  p-value: 0.000
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `sector_flow_count <= 0.3000`
- Method: feature_match
- 2025 training: n_met=0, n_negative=0, hit_rate=0.000, avg_return=0.00000
- 2026 validation: n_met=0, n_negative=0, hit_rate=0.000, avg_return=0.00000
- Base rate: 0.334  Lift: 0.00x  Stability: 1.000  p-value: 1.000
- **Verdict: INSUFFICIENT_DATA**  (confidence_delta: +0.000)

### `mom_10d > -0.0272`
- Method: edge_lifecycle:CANDIDATE
- 2025 training: n_met=83, n_negative=10, hit_rate=0.133, avg_return=-0.16338
- 2026 validation: n_met=83, n_negative=10, hit_rate=0.133, avg_return=-0.16338
- Base rate: 0.334  Lift: 0.40x  Stability: 1.000  p-value: 0.000
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `sector_strength <= 0.2573`
- Method: edge_lifecycle:DECAYING
- 2025 training: n_met=36, n_negative=3, hit_rate=0.083, avg_return=-0.20646
- 2026 validation: n_met=36, n_negative=3, hit_rate=0.092, avg_return=-0.20646
- Base rate: 0.334  Lift: 0.27x  Stability: 0.909  p-value: 0.000
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `pcr > 0.4002`
- Method: feature_match
- 2025 training: n_met=58, n_negative=18, hit_rate=0.310, avg_return=0.00106
- 2026 validation: n_met=103, n_negative=33, hit_rate=0.320, avg_return=-0.00089
- Base rate: 0.334  Lift: 0.96x  Stability: 0.969  p-value: 0.807
- Cross-regime: {'SIDEWAYS': 0.3333333333333333, 'TRENDING_DOWN': 0.2727272727272727}
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `mom_5d <= -0.0102`
- Method: feature_match
- 2025 training: n_met=49, n_negative=17, hit_rate=0.347, avg_return=0.00101
- 2026 validation: n_met=130, n_negative=44, hit_rate=0.338, avg_return=0.00042
- Base rate: 0.334  Lift: 1.01x  Stability: 0.976  p-value: 0.930
- Cross-regime: {'SIDEWAYS': 0.3068181818181818, 'TRENDING_DOWN': 0.40476190476190477}
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `breadth > 0.6281`
- Method: feature_match
- 2025 training: n_met=0, n_negative=0, hit_rate=0.000, avg_return=0.00000
- 2026 validation: n_met=8, n_negative=4, hit_rate=0.500, avg_return=-0.00708
- Base rate: 0.334  Lift: 1.50x  Stability: 0.000  p-value: 1.000
- **Verdict: INSUFFICIENT_DATA**  (confidence_delta: +0.000)

### `mom_5d > -0.0115`
- Method: feature_match
- 2025 training: n_met=150, n_negative=41, hit_rate=0.273, avg_return=0.00076
- 2026 validation: n_met=179, n_negative=66, hit_rate=0.369, avg_return=-0.00117
- Base rate: 0.334  Lift: 1.10x  Stability: 0.741  p-value: 0.003
- Cross-regime: {'SIDEWAYS': 0.3724137931034483, 'TRENDING_DOWN': 0.35294117647058826}
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `mom_20d <= -0.1299`
- Method: edge_lifecycle:CANDIDATE
- 2025 training: n_met=75, n_negative=27, hit_rate=0.360, avg_return=-0.04701
- 2026 validation: n_met=75, n_negative=27, hit_rate=0.360, avg_return=-0.04701
- Base rate: 0.334  Lift: 1.08x  Stability: 1.000  p-value: 1.000
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `event_count <= 0.1000`
- Method: feature_match
- 2025 training: n_met=196, n_negative=58, hit_rate=0.296, avg_return=0.00080
- 2026 validation: n_met=304, n_negative=109, hit_rate=0.359, avg_return=-0.00042
- Base rate: 0.334  Lift: 1.07x  Stability: 0.825  p-value: 0.000
- Cross-regime: {'SIDEWAYS': 0.34782608695652173, 'TRENDING_DOWN': 0.3918918918918919}
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `mom_5d > -0.0173`
- Method: feature_match
- 2025 training: n_met=158, n_negative=43, hit_rate=0.272, avg_return=0.00094
- 2026 validation: n_met=203, n_negative=75, hit_rate=0.369, avg_return=-0.00118
- Base rate: 0.334  Lift: 1.11x  Stability: 0.737  p-value: 0.001
- Cross-regime: {'SIDEWAYS': 0.3696969696969697, 'TRENDING_DOWN': 0.3684210526315789}
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `macd_signal_norm > 0.6361`
- Method: edge_lifecycle:DECAYING
- 2025 training: n_met=21, n_negative=0, hit_rate=0.000, avg_return=-0.47414
- 2026 validation: n_met=21, n_negative=0, hit_rate=0.000, avg_return=-0.47414
- Base rate: 0.334  Lift: 0.00x  Stability: 1.000  p-value: 0.000
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `volume_ratio_raw <= 1.9447`
- Method: edge_lifecycle:IMPROVING
- 2025 training: n_met=15, n_negative=2, hit_rate=0.148, avg_return=-0.17379
- 2026 validation: n_met=15, n_negative=1, hit_rate=0.133, avg_return=-0.17379
- Base rate: 0.334  Lift: 0.40x  Stability: 0.900  p-value: 0.019
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `mom_10d <= -0.0248`
- Method: edge_lifecycle:CANDIDATE
- 2025 training: n_met=83, n_negative=10, hit_rate=0.133, avg_return=-0.16338
- 2026 validation: n_met=83, n_negative=10, hit_rate=0.133, avg_return=-0.16338
- Base rate: 0.334  Lift: 0.40x  Stability: 1.000  p-value: 0.000
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `mom_20d > 0.0310`
- Method: edge_lifecycle:CANDIDATE
- 2025 training: n_met=75, n_negative=27, hit_rate=0.360, avg_return=-0.04701
- 2026 validation: n_met=75, n_negative=27, hit_rate=0.360, avg_return=-0.04701
- Base rate: 0.334  Lift: 1.08x  Stability: 1.000  p-value: 1.000
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `bb_position <= -0.6604`
- Method: edge_lifecycle:DECAYING
- 2025 training: n_met=25, n_negative=0, hit_rate=0.000, avg_return=-0.32170
- 2026 validation: n_met=25, n_negative=0, hit_rate=0.000, avg_return=-0.32170
- Base rate: 0.334  Lift: 0.00x  Stability: 1.000  p-value: 0.000
- **Verdict: REJECTED**  (confidence_delta: -0.100)

### `rsi <= 29.6705`
- Method: edge_lifecycle:DECAYING
- 2025 training: n_met=19, n_negative=7, hit_rate=0.368, avg_return=-0.06567
- 2026 validation: n_met=19, n_negative=7, hit_rate=0.405, avg_return=-0.06567
- Base rate: 0.334  Lift: 1.21x  Stability: 0.909  p-value: 1.000
- **Verdict: VALIDATED**  (confidence_delta: +0.043)

### `mom_5d <= -0.0084`
- Method: feature_match
- 2025 training: n_met=55, n_negative=18, hit_rate=0.327, avg_return=0.00067
- 2026 validation: n_met=138, n_negative=48, hit_rate=0.348, avg_return=0.00026
- Base rate: 0.334  Lift: 1.04x  Stability: 0.941  p-value: 0.930
- Cross-regime: {'SIDEWAYS': 0.30851063829787234, 'TRENDING_DOWN': 0.4318181818181818}
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `mom_20d <= 0.0277`
- Method: edge_lifecycle:CANDIDATE
- 2025 training: n_met=75, n_negative=27, hit_rate=0.360, avg_return=-0.04701
- 2026 validation: n_met=75, n_negative=27, hit_rate=0.360, avg_return=-0.04701
- Base rate: 0.334  Lift: 1.08x  Stability: 1.000  p-value: 1.000
- **Verdict: PARTIALLY_VALIDATED**  (confidence_delta: +0.030)

### `rsi_norm <= 0.3977`
- Method: edge_lifecycle:DECAYING
- 2025 training: n_met=19, n_negative=4, hit_rate=0.222, avg_return=-0.11762
- 2026 validation: n_met=19, n_negative=4, hit_rate=0.244, avg_return=-0.11762
- Base rate: 0.334  Lift: 0.73x  Stability: 0.909  p-value: 0.127
- **Verdict: REJECTED**  (confidence_delta: -0.100)
