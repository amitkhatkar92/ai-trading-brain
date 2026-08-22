# TRADE QUALITY AUDIT REPORT

**Generated:** 2026-06-19T09:02:25.360647+00:00
**Module:** TRADE_QUALITY_AUDIT_001
**Mode:** Shadow analysis — no live trading
**Total trades logged:** 150
**Closed trades analysed:** 150

---

## Win vs Loss — Score Comparison

**✅ QUALITY PREDICTS OUTCOME**  |  Quality Edge: `+1.09` pts  |  N = 77 wins, 73 losses

```
Winning Trades

  Avg Quality Score   = 7.9  ████████████░░░
  Avg Decision Score  = 8.1  ████████████░░░
  Avg Technical Score = 7.9  ████████████░░░
  Avg Macro Score     = 7.7  ████████████░░░
  SFT = HIGH rate     = 66.2%

Losing Trades

  Avg Quality Score   = 6.8  ██████████░░░░░
  Avg Decision Score  = 6.9  ██████████░░░░░
  Avg Technical Score = 7.0  ██████████░░░░░
  Avg Macro Score     = 6.6  ██████████░░░░░
  SFT = HIGH rate     = 38.4%
```

---

## Quality Tier → Win Rate

| Tier | Trades | Closed | WR% | Avg PnL | Expected WR |
|---|---|---|---|---|---|
| PREMIUM | 46 | 46 | 69.6% (-10.4% vs expected) | ₹14,671 | 80% |
| HIGH | 39 | 39 | 64.1% (+1.1% vs expected) | ₹7,694 | 63% |
| MEDIUM | 48 | 48 | 37.5% (-0.5% vs expected) | ₹-3,294 | 38% |
| LOW | 17 | 17 | 11.8% (-8.2% vs expected) | ₹-15,346 | 20% |

---

## Performance by Market Regime

| Regime | Trades | WR% | Avg Quality Score |
|---|---|---|---|
| BEAR | 19 | 73.7% | 8.07 |
| BULL | 50 | 44.0% | 7.19 |
| HIGH_VOL | 23 | 60.9% | 7.23 |
| RANGING | 58 | 46.6% | 7.34 |

---

## High-Conviction vs Normal Trades

High-conviction = quality_score ≥ 7.5 AND margin > 0.5

| Type | Trades | WR% | Avg PnL |
|---|---|---|---|
| High-Conviction | 71 | 70.4% | ₹12,792 |
| Normal | 79 | 34.2% | ₹-4,460 |

---

## Low-Quality Wins — False Negatives
_Scored < 6.5 but still won. May indicate missing signal sources._

| Symbol | Strategy | Quality | Decision | PnL |
|---|---|---|---|---|
| WIPRO | Options_IronCondor | 4.95 | 4.56 | ₹5,438 |
| RELIANCE | Equity_Momentum | 5.07 | 5.64 | ₹9,117 |
| DRREDDY | Equity_MeanReversion | 6.08 | 5.84 | ₹14,081 |
| SBIN | Equity_MeanReversion | 6.30 | 5.86 | ₹12,173 |
| RELIANCE | Options_IronCondor | 6.31 | 6.68 | ₹18,174 |

---

## High-Quality Losses — Probe for System Error
_Scored ≥ 7.5 but still lost. Review for slippage, news shock, or scoring error._

| Symbol | Strategy | Quality | Decision | PnL |
|---|---|---|---|---|
| TATASTEEL | Options_BullPutSpread | 9.27 | 9.73 | ₹-10,900 |
| HINDALCO | Equity_Breakout | 9.04 | 9.53 | ₹-5,499 |
| SBIN | Options_IronCondor | 9.04 | 9.51 | ₹-10,185 |
| HINDALCO | Options_IronCondor | 8.84 | 8.54 | ₹-9,206 |
| INFY | Equity_Momentum | 8.54 | 8.65 | ₹-11,881 |

---

## Conclusion

Quality scoring is **working**.

A 1.09-point quality gap separates winning trades (avg 7.9) from losing trades (avg 6.8).

**Recommended Action:** Raise minimum quality gate to 7.0+.
Filter any trade with quality_score < 6.5.
Prioritise HIGH-SFT symbols.

---

*Shadow analysis only. No trades placed or modified.*