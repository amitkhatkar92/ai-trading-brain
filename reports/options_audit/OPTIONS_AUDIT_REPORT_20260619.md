# OPTIONS AUDIT REPORT

**Generated:** 2026-06-19T08:48:36.779969+00:00
**Mode:** Analysis only — no live trading, no execution influence

---

## Strategy Ranking (Overall)

| Rank | Strategy | Trades | WR% | PF | Total PnL | Best Regime | Worst Regime |
|---|---|---|---|---|---|---|---|
| 1 | **BULL_PUT_SPREAD** | 148 | 70.3% | 1.74 | ₹267,559 | TRENDING | HIGH_VOL |
| 2 | **LONG_STRADDLE** | 104 | 28.9% | 0.94 | ₹-51,817 | HIGH_VOL | TRENDING |
| 3 | **BEAR_CALL_SPREAD** | 136 | 58.1% | 0.81 | ₹-110,379 | RANGING | HIGH_VOL |
| 4 | **PROTECTIVE_PUT** | 48 | 12.5% | 0.74 | ₹-90,074 | HIGH_VOL | RANGING |
| 5 | **IRON_CONDOR** | 170 | 64.7% | 0.71 | ₹-313,567 | RANGING | HIGH_VOL |
| 6 | **SHORT_STRANGLE** | 240 | 67.5% | 0.66 | ₹-735,632 | RANGING | HIGH_VOL |
| 7 | **LONG_STRANGLE** | 92 | 21.7% | 0.64 | ₹-352,042 | HIGH_VOL | RANGING |
| 8 | **COVERED_CALL** | 180 | 73.9% | 0.64 | ₹-313,857 | RANGING | HIGH_VOL |
| 9 | **IRON_BUTTERFLY** | 120 | 60.0% | 0.61 | ₹-288,620 | RANGING | HIGH_VOL |
| 10 | **SHORT_STRADDLE** | 96 | 62.5% | 0.37 | ₹-869,662 | RANGING | HIGH_VOL |

---

## Top 3 Strategy Deep-Dive

### #1 BULL_PUT_SPREAD
- **Profit Factor:** 1.74
- **Win Rate:** 70.3%
- **Trades:** 148
- **Total PnL:** ₹267,559
- **Best Regime:** TRENDING
- **Worst Regime:** HIGH_VOL

### #2 LONG_STRADDLE
- **Profit Factor:** 0.94
- **Win Rate:** 28.9%
- **Trades:** 104
- **Total PnL:** ₹-51,817
- **Best Regime:** HIGH_VOL
- **Worst Regime:** TRENDING

### #3 BEAR_CALL_SPREAD
- **Profit Factor:** 0.81
- **Win Rate:** 58.1%
- **Trades:** 136
- **Total PnL:** ₹-110,379
- **Best Regime:** RANGING
- **Worst Regime:** HIGH_VOL

---

## Strategy × Regime Performance

| Strategy | RANGING PF | TRENDING PF | HIGH_VOL PF | Best Regime |
|---| --- | --- | --- | --- |
| SHORT_STRANGLE | 1.98 | 0.50 | 0.10 | **RANGING** |
| IRON_CONDOR | 2.20 | 0.39 | 0.09 | **RANGING** |
| BULL_PUT_SPREAD | 2.06 | 3.07 | 0.34 | **TRENDING** |
| BEAR_CALL_SPREAD | 1.47 | 0.50 | 0.42 | **RANGING** |
| LONG_STRADDLE | 0.91 | 0.84 | 1.36 | **HIGH_VOL** |
| LONG_STRANGLE | 0.44 | 0.92 | 1.02 | **HIGH_VOL** |
| SHORT_STRADDLE | 1.65 | 0.21 | 0.05 | **RANGING** |
| IRON_BUTTERFLY | 1.39 | 0.45 | 0.13 | **RANGING** |
| COVERED_CALL | 1.10 | 0.64 | 0.13 | **RANGING** |
| PROTECTIVE_PUT | 0.41 | 1.12 | 2.85 | **HIGH_VOL** |

---

## Strategy × VIX Bucket Performance

| Strategy | LOW PF | MEDIUM PF | HIGH PF | EXTREME PF | Best VIX |
|---| --- | --- | --- | --- | --- |
| SHORT_STRANGLE | 0.92 | 1.26 | 0.09 | 0.14 | **MEDIUM** |
| IRON_CONDOR | 1.08 | 1.25 | 0.19 | 0.06 | **MEDIUM** |
| BULL_PUT_SPREAD | 3.60 | 1.93 | 0.80 | 0.39 | **LOW** |
| BEAR_CALL_SPREAD | 0.82 | 0.85 | 0.83 | 0.40 | **MEDIUM** |
| LONG_STRADDLE | 0.49 | 1.14 | 1.92 | 0.00 | **HIGH** |
| LONG_STRANGLE | 0.43 | 0.61 | 0.74 | 1.62 | **EXTREME** |
| SHORT_STRADDLE | 0.99 | 0.60 | 0.09 | 0.02 | **LOW** |
| IRON_BUTTERFLY | 0.70 | 0.95 | 0.27 | 0.09 | **MEDIUM** |
| COVERED_CALL | 0.81 | 1.00 | 0.40 | 0.08 | **MEDIUM** |
| PROTECTIVE_PUT | 0.00 | 0.79 | 4.85 | 0.05 | **HIGH** |

---

## Market VIX Profile (Historical)

| Metric | Value |
|---|---|
| Period | 2024-01-02 → 2026-06-18 |
| Mean VIX | 14.5 |
| Median VIX | 13.9 |
| Min / Max | 9.15 / 27.89 |
| % Days LOW (<15) | 66.9% |
| % Days MEDIUM (15-20) | 26.2% |
| % Days HIGH (20-28) | 6.8% |
| % Days EXTREME (>28) | 0.0% |
| Dominant Bucket | **LOW** |

---

## Regime-Based Recommendations

| Regime | Preferred Strategies | Avoid |
|---|---|---|
| RANGING | SHORT_STRANGLE, IRON_CONDOR, IRON_BUTTERFLY | LONG_STRADDLE, LONG_STRANGLE, PROTECTIVE_PUT |
| TRENDING | BULL_PUT_SPREAD, BEAR_CALL_SPREAD, COVERED_CALL | SHORT_STRANGLE, IRON_BUTTERFLY |
| HIGH_VOL | LONG_STRADDLE, LONG_STRANGLE, BULL_PUT_SPREAD | SHORT_STRANGLE, SHORT_STRADDLE, COVERED_CALL |

---

## Recommendation Summary

```
OPTIONS AUDIT REPORT

Strategy Ranking

1. BULL_PUT_SPREAD
   PF: 1.74

2. LONG_STRADDLE
   PF: 0.94

3. BEAR_CALL_SPREAD
   PF: 0.81

Best Regime:  TRENDING
Worst Regime: HIGH_VOL

Recommendation:
Use BULL_PUT_SPREAD when VIX < 20 and market is TRENDING.
Switch to LONG_STRADDLE when VIX > 22 (HIGH_VOL regime).
Avoid SHORT_STRADDLE / SHORT_STRANGLE when VIX > 22.
```

---

*Analysis only. No trades have been placed.*