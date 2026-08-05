# Loser DNA Report — Study-003

**Issue:** KMP-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  


## Study-003 Overview

- Purpose: Systematic Loser DNA Discovery from 500 labelled feature records
- Date range: 2021-01-01 to 2025-12-30
- Method: Cohen's d separability between loser (return < -0.5%) and winner (return > +0.5%) cohorts
- Governance: confidence ≥ 0.35, lift ≥ 1.2, effect_size ≥ 0.15
- Patterns derived: 15
- IDR loser DNA promoted: 15

## Loser DNA Patterns

| # | Condition | Confidence | Lift | Effect Size | Direction |
|---|-----------|-----------|------|-------------|-----------|
| 1 | `volume_spike > 0.0000` | 1.000 | 2.01 | 0.500 | HIGH |
| 2 | `volume_spike > 0.0000` | 1.000 | 2.01 | 0.500 | HIGH |
| 3 | `volume_spike > 0.0000` | 0.857 | 1.72 | 0.357 | HIGH |
| 4 | `sector_flow_count <= 0.3000` | 0.500 | 1.00 | 0.195 | HIGH |
| 5 | `event_count <= 0.1000` | 0.500 | 1.00 | 0.195 | HIGH |
| 6 | `sector_flow_count <= 0.3000` | 0.500 | 1.00 | 0.195 | HIGH |
| 7 | `event_count <= 0.1000` | 0.500 | 1.00 | 0.195 | HIGH |
| 8 | `sector_flow_count <= 0.3000` | 0.647 | 1.30 | 0.147 | HIGH |
| 9 | `sector_flow_count <= 0.3000` | 0.476 | 0.95 | 0.134 | HIGH |
| 10 | `macd_signal_norm > 0.6361` | 0.625 | 1.25 | 0.125 | HIGH |
| 11 | `sector_flow_count <= 0.3000` | 0.600 | 1.20 | 0.100 | HIGH |
| 12 | `event_count <= 0.1000` | 0.567 | 1.14 | 0.067 | HIGH |
| 13 | `sector_flow_count <= 0.3000` | 0.545 | 1.09 | 0.045 | HIGH |
| 14 | `sector_flow_count <= 0.3000` | 0.545 | 1.09 | 0.045 | HIGH |
| 15 | `sector_flow_count <= 0.3000` | 0.545 | 1.09 | 0.045 | HIGH |

## IDR Loser DNA Records

Total loser DNA in IDR: **15**

| ID | Feature | Direction | Confidence | Effect Size |
|-----|---------|----------|-----------|-------------|
| KMP-L-VOLUME_SPIKE-42C6C9 | volume_spike | SHORT | 1.000 | 0.500 |
| KMP-L-VOLUME_SPIKE-467E7D | volume_spike | SHORT | 1.000 | 0.500 |
| KMP-L-VOLUME_SPIKE-CEF5E6 | volume_spike | SHORT | 0.857 | 0.357 |
| KMP-L-SECTOR_FLOW_-ABB95C | sector_flow_count | SHORT | 0.500 | 0.195 |
| KMP-L-EVENT_COUNT-50AFE6 | event_count | SHORT | 0.500 | 0.195 |
| KMP-L-SECTOR_FLOW_-822E80 | sector_flow_count | SHORT | 0.500 | 0.195 |
| KMP-L-EVENT_COUNT-5DFC92 | event_count | SHORT | 0.500 | 0.195 |
| KMP-L-SECTOR_FLOW_-597F24 | sector_flow_count | SHORT | 0.647 | 0.147 |
| KMP-L-SECTOR_FLOW_-635477 | sector_flow_count | SHORT | 0.476 | 0.134 |
| KMP-L-MACD_SIGNAL_-CD8A8B | macd_signal_norm | SHORT | 0.625 | 0.125 |
| KMP-L-SECTOR_FLOW_-D81E48 | sector_flow_count | SHORT | 0.600 | 0.100 |
| KMP-L-EVENT_COUNT-543F76 | event_count | SHORT | 0.567 | 0.067 |
| KMP-L-SECTOR_FLOW_-1B5918 | sector_flow_count | SHORT | 0.545 | 0.045 |
| KMP-L-SECTOR_FLOW_-F9BBD7 | sector_flow_count | SHORT | 0.545 | 0.045 |
| KMP-L-SECTOR_FLOW_-8EAA00 | sector_flow_count | SHORT | 0.545 | 0.045 |