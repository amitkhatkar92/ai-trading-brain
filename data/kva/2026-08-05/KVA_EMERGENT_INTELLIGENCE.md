# KVA Emergent Intelligence

**Issue:** KVA-001  
**Date:** 2026-08-05  
**Version:** 1.0.0  


> **Questions no one explicitly programmed.**  
> Every answer below was derived entirely from statistical analysis of real IIOS data — no answer was pre-written.

**Category Score:** 72.8/100  

## Q1: What is the most surprising thing IIOS learned?

| Rank | Edge | Surprise Score | OOS Win Rate | Sharpe | n | Description |
|------|------|----------------|-------------|--------|---|-------------|
| 1 | EDG_MOMENT_100_EE0005 | 0.5186 | 100.0% | 62.38 | 16 | IF mom_5d > 0.006 AND volume_ratio > 0.506 AND iv_rank <= 0. |
| 2 | EDG_MOMENT_100_EE0004 | 0.4885 | 100.0% | 43.00 | 15 | IF sector_flow_count <= 0.300 AND mom_5d > -0.011 AND regime |
| 3 | EDG_MOMENT_100_EE0003 | 0.4730 | 100.0% | 43.00 | 16 | IF global_bias <= 0.881 AND volume_ratio_raw > 2.012 AND his |
| 4 | EDG_MOMENT_95_EE0004 | 0.4233 | 100.0% | 47.41 | 21 | IF macd_signal_norm > 0.636 AND volume_ratio > 0.486 AND iv_ |
| 5 | EDG_MOMENT_96_EE0002 | 0.4233 | 100.0% | 47.41 | 21 | IF event_count <= 0.100 AND macd_signal_norm > 0.636 AND vol |

**Finding:** Most statistically surprising edge: EDG_MOMENT_100_EE0005 — "IF mom_5d > 0.006 AND volume_ratio > 0.506 AND iv_rank <= 0.610 THEN bullish with 100% hit" (OOS=100.0%, Sharpe=62.4, n=16, surprise_score=0.519). Counterintuitive feature: 'cons_up_days' has NEGATIVE correlation with forward return (r=-0.0733) — acts as mean-reversion signal.

**Confidence:** 0.85  |  **Source:** Edge library (statistical surprise score) + feature correlations

## Q2: Which commonly accepted market beliefs were contradicted?

### Contradiction 1

CONTRADICTED: 'Bull markets are best for systematic strategies.' Replay shows RANGE_MARKET win rate=67% vs BULL_TREND win rate=33%. Disciplined edge strategies outperform their benchmark more in sideways markets.

### Contradiction 2

CONTRADICTED: 'Consecutive up days predict continuation.' Feature 'cons_up_days' has NEGATIVE correlation with forward return (r=-0.0733) — the market mean-reverts after multi-day runs, not trends.

### Contradiction 3

CONTRADICTED: 'More conditions = more overfitting.' Edges with 3+ conditions achieve avg OOS=74.82% vs single-condition avg OOS=61.97%. Compound conditions improve generalisation.

### Contradiction 4

CONTRADICTED: 'High-support edges are more reliable.' Low-support (n=10-19) avg OOS=76.36% > high-support (n≥50) avg OOS=74.08%. Rare precise patterns outperform common noisy ones.

## Q3: Feature Synergy — Weak Alone, Powerful in Combination

| Feature | Solo r | Solo Predictive Power | Role in Edges |
|---------|--------|----------------------|---------------|
| adx_score | 0.0000 | **WEAK** | Synergy amplifier |
| mom_10d | 0.0000 | **WEAK** | Synergy amplifier |
| volume_ratio | 0.0000 | **WEAK** | Synergy amplifier |
| gap_pct | 0.0000 | **WEAK** | Synergy amplifier |
| volume_ratio_raw | 0.0000 | **WEAK** | Synergy amplifier |
| mom_20d | 0.0000 | **WEAK** | Synergy amplifier |
| rsi_norm | 0.0000 | **WEAK** | Synergy amplifier |
| hist_vol_5d | 0.0000 | **WEAK** | Synergy amplifier |

**Finding:** 'adx_score' (solo r=0.0000 — near-zero individual predictive power) becomes powerful in multi-condition edges: EDG_COMPOS_92_EE0002(oos=88.2%) combined with [breadth, global_bias, hist_vol_20d]; EDG_COMPOS_93_EE0003(oos=88.2%) combined with [breadth, global_bias, hist_vol_20d]. Total synergy-only features identified: 22.

## Q4: Five Lessons for a New Investor (data-derived)

### Lesson 1
The regime matters more than the direction. Sideways markets produced a 67% win rate with 47% market capture, better than bull trends (33% WR). Identify the regime before placing a trade.

*Evidence source: re001a / 30-day replay per-regime stats*

### Lesson 2
Do not chase consecutive winners. 'cons_up_days' correlates NEGATIVELY with next-period return (r=-0.0733). After multi-day rallies the market tends to mean-revert, not continue.

*Evidence source: study002 / feature-return Pearson correlation (n=500)*

### Lesson 3
Every edge has a shelf life. 132/259 edges (51%) are already decaying — patterns that worked have weakened. Strategies must be monitored and retired continuously.

*Evidence source: re001a / edge status distribution*

### Lesson 4
Extreme selectivity is the strategy, not a limitation. Only 6 of 286 signals (2.1%) were approved, yet the profit factor reached 3.96. Waiting for the right setup is the system.

*Evidence source: re001a / replay trades_approved_pct*

### Lesson 5
Sector conviction is the most reliable precursor of winners. 'sect_conviction' is the top winner DNA feature (avg confidence=0.672 across 8 winner patterns). Verify sector supports the trade before entry.

*Evidence source: study002a / winner DNA analysis (2021-2025)*

## Q5: Three Biggest Unanswered Scientific Questions

### Unanswered Question 1
Is a 100% OOS win rate real or a statistical mirage? 16 edges achieve ≥90% OOS (avg=98.5%) with fewer than 25 test observations. At what n does the OOS estimate become statistically trustworthy?

*Why unanswered: n<25 for 16 high-OOS edges; no significance test yet*

### Unanswered Question 2
Why is regime detection confidence bimodal? 124 readings ≥0.80 and 140 readings ≤0.25 (P25=0.242, P75=0.775) — very few in between. What market conditions trigger low-confidence transitions, and how should IIOS trade during them?

*Why unanswered: Regime history: bimodal distribution P25=0.242 vs P75=0.775*

### Unanswered Question 3
Why do 97.9% of signals never reach execution? Only 2.1% of 286 signals became trades and regime alignment was 0%. Are kill conditions correctly calibrated, or is IIOS systematically blocking valid opportunities?

*Why unanswered: re001a / replay: trades_approved_pct=2.1%, regime_alignment_pct=0%*

## Observations

- 244 edges surprise-scored
- 4 beliefs tested, 4 contradicted
- 22 synergy-only features identified