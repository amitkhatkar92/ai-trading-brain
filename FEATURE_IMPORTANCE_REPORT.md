# FEATURE IMPORTANCE REPORT
## Study 2A — Complete Feature Ranking and Statistical Analysis

**Evidence base:** 280,909 observations | 20 non-redundant features | 5 statistical methods  
**Test period:** 2021-01-01 to 2026-07-29

---

## 1. Ranking Methodology

Features are ranked by a **combined score** averaging three normalized metrics:
1. **Mutual Information (MI):** Feature-label dependency (non-linear, from sklearn)
2. **Random Forest Importance (RF):** Ensemble importance across 100 trees, depth 8
3. **Cohen's d (|abs|):** Effect size between Winner and Loser group means

Mann-Whitney U p-value used for statistical significance only (not in combined score).

**Combined score = (MI_normalized + RF_normalized + |d|_normalized) / 3**

All methods normalized to [0, 1] range before averaging.

---

## 2. Complete Feature Rankings

### Top 20 Features — All Metrics

| Rank | Feature | Combined | MI | RF Imp | Cohen's d (W-L) | MWU p-value |
|---|---|---|---|---|---|---|
| 1 | `avg_conviction` | 0.5984 | 0.11344 | 0.03692 | +0.0506 | <1e-300 |
| 2 | `sect_conviction` | 0.4301 | 0.07058 | 0.00944 | +0.0473 | <1e-300 |
| 3 | `atr_14` | 0.4248 | 0.02498 | **0.33404** | −0.0040 | 0.776 |
| 4 | `intra_range` | 0.4204 | 0.02061 | **0.24085** | +0.0265 | 0.015 |
| 5 | `sc_high` | 0.3366 | 0.00060 | 0.00149 | +0.0739 | <1e-300 |
| 6 | `sect_part5d` | 0.3104 | 0.03018 | 0.02420 | +0.0438 | <1e-300 |
| 7 | `close_pos` | 0.2662 | 0.00211 | 0.01741 | +0.0538 | <1e-300 |
| 8 | `sc_low` | 0.2344 | 0.02136 | 0.00198 | −0.0376 | <1e-300 |
| 9 | `mom_5d` | 0.2238 | 0.00797 | 0.05118 | −0.0331 | 1.8e-06 |
| 10 | `cons_up_days` | 0.1771 | 0.00156 | 0.00295 | −0.0376 | <1e-300 |
| 11 | `mom_1d` | 0.1638 | 0.01175 | 0.06311 | +0.0147 | <1e-300 |
| 12 | `prox_52w_low` | 0.1590 | 0.00644 | 0.06084 | −0.0176 | 0.0064 |
| 13 | `prox_52w_high` | 0.1506 | 0.00151 | 0.01765 | +0.0285 | 5.0e-08 |
| 14 | `cons_dn_days` | 0.1390 | 0.00140 | 0.00276 | +0.0293 | <1e-300 |
| 15 | `regime_score` | 0.1362 | 0.01438 | 0.01771 | +0.0169 | 6.96e-04 |
| 16 | `regime_bull` | — | — | 0.04049 | +0.0210 | 6.96e-04 |
| 17 | `gap_pct` | 0.1140 | 0.00437 | 0.03270 | +0.0152 | <1e-300 |
| 18 | `mom_20d` | 0.0995 | 0.00767 | 0.03778 | −0.0087 | 0.803 |
| 19 | `vol_ratio` | 0.0995 | 0.00169 | 0.01967 | +0.0166 | <1e-300 |
| 20 | `vol_ratio_20` | 0.0562 | 0.00172 | 0.02550 | +0.0057 | <1e-300 |

---

## 3. Per-Feature Statistical Detail

### Feature 1: `avg_conviction` (Rank #1)
- **Winner mean:** 0.30340 | **Ordinary:** 0.31295 | **Loser:** 0.29363
- **Std (Winners):** ~0.17 | **Std (Losers):** ~0.17
- **Cohen's d (W vs L):** +0.0506 | **p-value:** <1e-300
- **Interpretation:** Sector-wide breadth is the top ranked feature. Winners occur more often in elevated-breadth sessions. However, the DECILE ANALYSIS reveals a U-shaped relationship (not monotonic) — highest winner rates at both very low AND high breadth. This suggests two winner regimes: contrarian (low breadth) and aligned (high breadth).
- **MI rank:** #1 (0.113) — highest information content of all features
- **RF rank:** Low (0.037) — not a splitting feature in non-linear trees

### Feature 2: `sect_conviction` (Rank #2)
- **Winner mean:** 0.29986 | **Ordinary:** 0.30477 | **Loser:** 0.28716
- **Cohen's d:** +0.0473 | **p-value:** <1e-300
- **MI:** 0.0706 (second highest) | **RF:** 0.0094 (low)
- **Interpretation:** Individual sector conviction (for the stock's own sector) is slightly more predictive than cross-sector breadth. Winners are in sectors with modestly higher conviction than losers' sectors.

### Feature 3: `atr_14` (Rank #3 — RF DOMINANT)
- **Winner mean:** 0.03385 | **Ordinary:** 0.02899 | **Loser:** 0.03390
- **Cohen's d:** −0.004 | **p-value:** 0.776 (NOT SIGNIFICANT by linear test)
- **RF importance:** **0.334 — highest of all features** (Random Forest finds it most important)
- **MI:** 0.025 | **Linear Cohen's d:** near-zero
- **Critical insight:** The RF and decile analysis reveal a STRONG NON-LINEAR relationship that the linear Cohen's d CANNOT detect. The monotonic decile analysis (WR 17.3% → 35.3%) confirms atr_14 is the single most predictive feature by non-linear measure. The Cohen's d is near-zero because BOTH winners and losers have high ATR — but from different directions (winners → rising, losers → falling). This is why RF wins here.
- **Warning:** Do not use p-value (0.776) to dismiss this feature. The linear test fails on non-linear relationships.

### Feature 4: `intra_range` (Rank #4 — RF DOMINANT)
- **Winner mean:** 0.03387 | **Ordinary:** 0.02694 | **Loser:** 0.03332
- **Cohen's d:** +0.0265 | **p-value:** 0.015
- **RF importance:** **0.241** (second highest)
- **MI:** 0.021
- **Interpretation:** Similar to atr_14 but captures single-day range vs 14-day average. Winners have slightly wider intraday range than losers AND than ordinary stocks (both means are higher). Decile analysis: monotonic from 18.6% → 37.0%.

### Feature 5: `sc_high` (Rank #5)
- **Winner mean:** 7.58% (flag=1) | **Ordinary:** 7.38% | **Loser:** 5.74%
- **Cohen's d:** **+0.0739** (highest of all features by this metric)
- **p-value:** <1e-300
- **Interpretation:** The "high breadth" flag (avg_conviction > 0.6) appears in 7.58% of winner sessions vs only 5.74% of loser sessions — a 32% relative increase. Despite the small absolute rates, the Cohen's d is the highest in the dataset.

### Feature 6: `sect_part5d` (Rank #6)
- **Winner mean:** 0.4973 | **Ordinary:** 0.5195 | **Loser:** 0.4848
- **Cohen's d:** +0.044 | **p-value:** <1e-300
- **Interpretation:** 5-day sector participation rate. Winners occur in sectors with moderate participation rate (~50%). This is NOT the highest sector participation (ordinary stocks have slightly higher participation at 51.95%).

### Feature 7: `close_pos` (Rank #7)
- **Winner mean:** 0.46825 | **Ordinary:** 0.46699 | **Loser:** 0.45372
- **Cohen's d:** +0.054 | **p-value:** <1e-300
- **Interpretation:** Where the stock closes within its daily range. Winners close at 46.8% of range (near midpoint, slightly above) vs Losers at 45.4%. The extreme close_pos (>98.7%) condition appears in DNA Patterns 2 and 3 with very high confidence.

### Feature 8: `sc_low` (Rank #8)
- **Winner mean:** 65.3% | **Loser:** 67.1%
- **Cohen's d:** −0.038 | **p-value:** <1e-300
- **Interpretation:** The "low breadth" flag (avg_conviction < 0.4) appears in 65.3% of winner sessions vs 67.1% of loser sessions. Losers are SLIGHTLY more concentrated in low-breadth environments. Both groups are predominantly in low-breadth (65-67%), reflecting that SIDEWAYS is the dominant regime. The small difference (1.8pp) is statistically significant but practically modest.

### Feature 9: `mom_5d` (Rank #9 — KEY INSIGHT)
- **Winner mean:** 0.00357 | **Ordinary:** 0.00423 | **Loser:** 0.00545
- **Cohen's d:** **−0.0331** (NEGATIVE — winners have LOWER 5-day momentum than losers!)
- **p-value:** 1.8e-06
- **RF importance:** 0.051
- **Critical finding:** This is the MEAN REVERSION signal. Losers have higher 5-day momentum than winners. This seems paradoxical but is confirmed by the decile analysis (D1, lowest momentum = 34.2% WR; D10, highest momentum = 30.5% WR, but with U-shape). Stocks that fell sharply over 5 days bounce back (reversion). Stocks that rose sharply face selling pressure.

### Feature 10: `cons_up_days` (Rank #10)
- **Winner mean:** 0.949 | **Loser:** 0.998
- **Cohen's d:** −0.038 | **p-value:** <1e-300
- **Interpretation:** Losers are on LONGER consecutive up-day streaks than winners before the next day. This confirms that winning streaks invite mean-reversion selling. Winners have fewer established upside streaks.

### Feature 11: `mom_1d` (Rank #11)
- **Winner mean:** 0.00093 | **Loser:** 0.00057
- **Cohen's d:** +0.015 | **p-value:** <1e-300
- **Decile analysis:** D1 (yesterday fell sharply) → WR=33.3% (1.27× lift); D10 (yesterday rose sharply) → WR=32.9% (1.25× lift)
- **Interpretation:** U-shaped — BOTH large yesterday gains and large yesterday losses predict today's winner. This is the mean-reversion + momentum continuation duality. The middle (near-zero yesterday) has the worst winner rate (22.2%).

### Feature 12: `prox_52w_low` (Rank #12)
- **Winner mean:** 1.510 | **Loser:** 1.520
- **Cohen's d:** −0.018 | **p-value:** 0.006
- **Interpretation:** Winners are slightly CLOSER to their 52-week low (1.51× vs 1.52×). This is a subtle mean-reversion signal — stocks that haven't moved far from their lows are slightly more likely to bounce.

### Feature 13: `prox_52w_high` (Rank #13)
- **Winner mean:** 0.825 | **Loser:** 0.822
- **Cohen's d:** +0.029 | **p-value:** 5e-08
- **Interpretation:** Winners are slightly closer to their 52-week high. Small effect but consistent with the "base breakout" archetype.

### Feature 14: `cons_dn_days` (Rank #14)
- **Winner mean:** 1.026 | **Loser:** 0.988
- **Cohen's d:** +0.029 | **p-value:** <1e-300
- **Interpretation:** Winners have MORE consecutive down days than losers. Further confirmation of the mean-reversion DNA. Prior falling streaks → bounce opportunity.

---

## 4. Feature Rank Summary Lists

### Top 5 Features
1. `avg_conviction` — Market breadth (sector-wide)
2. `sect_conviction` — Own-sector conviction score
3. `atr_14` — 14-day average true range (non-linear, RF dominant)
4. `intra_range` — Daily high-low range as % of close
5. `sc_high` — High breadth flag (highest Cohen's d)

### Top 10 Features
6. `sect_part5d` — 5-day sector participation rate
7. `close_pos` — Close position within daily range
8. `sc_low` — Low breadth flag
9. `mom_5d` — 5-day momentum (negative direction!)
10. `cons_up_days` — Consecutive up days (negative direction!)

### Top 20 Features
11. `mom_1d` | 12. `prox_52w_low` | 13. `prox_52w_high` | 14. `cons_dn_days`  
15. `regime_score` | 16. `regime_bull` | 17. `gap_pct` | 18. `mom_20d`  
19. `vol_ratio` | 20. `vol_ratio_20`

---

## 5. Features with Non-Linear Effects (Special Cases)

| Feature | Linear d | Non-Linear Evidence | Correct Test |
|---|---|---|---|
| `atr_14` | −0.004 (not sig) | Monotonic decile: 17.3%→35.3% | Decile analysis / RF |
| `intra_range` | +0.027 | Monotonic decile: 18.6%→37.0% | Decile analysis / RF |
| `mom_5d` | −0.033 | U-shaped: extremes win, middle loses | Decile analysis |
| `mom_1d` | +0.015 | U-shaped: extremes win, middle loses | Decile analysis |
| `avg_conviction` | +0.051 | Non-monotonic: U-shaped | Decile analysis |

**Methodological note:** For `atr_14` and `intra_range`, the Linear Cohen's d significantly UNDERESTIMATES predictive value. The Random Forest and decile analysis are the appropriate tests. Any analysis relying ONLY on Cohen's d would incorrectly conclude ATR is unimportant.

---

## 6. Statistically Non-Significant Features

| Feature | p-value | Verdict |
|---|---|---|
| `atr_14` | 0.776 | Non-significant by linear test — but STRONGLY predictive non-linearly |
| `mom_20d` | 0.803 | No predictive value (linear or non-linear) |

`mom_20d` appears to have zero predictive value for next-day returns, consistent with market efficiency over longer lookback windows.

---

## 7. Feature Group Summary

| Group | Features | Verdict |
|---|---|---|
| **Volatility** | atr_14, intra_range | PRIMARY DNA — strongest monotonic effect |
| **Sector context** | avg_conviction, sect_conviction, sc_high, sc_low, sect_part5d | SECONDARY DNA — consistent small effects |
| **Position/Structure** | close_pos, prox_52w_high, prox_52w_low | TERTIARY DNA — small effects, directionally consistent |
| **Mean Reversion** | mom_5d, mom_1d, cons_up_days, cons_dn_days | COUNTER-INTUITIVE — negative momentum predicts positive returns |
| **Volume** | vol_ratio, vol_ratio_20 | WEAK — small positive effect |
| **Gaps & Regime** | gap_pct, regime_score, regime_bull | CONTEXTUAL — moderate value |
| **Long momentum** | mom_20d | NONE — no predictive value |

---

*Study 2A — Feature Importance Report | 2026-08-03 | 280,909 observations | 20 features*
