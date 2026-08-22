# REJECTION AUDIT REPORT

**Generated:** 2026-06-19T09:14:04.480300+00:00
**Module:** REJECTION_AUDIT_001
**Mode:** Shadow analysis — no live trading
**Total rejections logged:** 504
**Classified (5d follow-through available):** 504

---

## Overall Rejection Accuracy

⚠️ **Accuracy: 64.0%**  |  False Negatives: 36.0%

```
Rejected Trades:           504
Classified:                504
  Correct Rejections:      270   █████████████░░░░░░░  64.0%
  False Rejections:        152   (missed winners)
  Neutral:                  82   (move too small)
```

**Marginal accuracy. Monitor — system may be too aggressive.**

---

## Accuracy by Rejection Reason

| Rejection Reason | Total | Correct | False | Accuracy | Expected | Verdict |
|---|---|---|---|---|---|---|
| LOW_SFT | 70 | 51 | 14 | ✅ 78.5% | 75.0% | 🟢 ON TARGET |
| HIGH_VOL_REGIME | 56 | 42 | 9 | ✅ 82.4% | 72.0% | ✅ OUTPERFORMING |
| LOW_DECISION_SCORE | 110 | 60 | 34 | ⚠️ 63.8% | 65.0% | 🟢 ON TARGET |
| LOW_QUALITY_SCORE | 84 | 40 | 28 | ⚠️ 58.8% | 65.0% | ⚠️ UNDERPERFORMING |
| LOW_CONVICTION | 60 | 24 | 23 | ❌ 51.1% | 60.0% | ⚠️ UNDERPERFORMING |
| CORRELATED_POSITION | 44 | 16 | 19 | ❌ 45.7% | 58.0% | ⚠️ UNDERPERFORMING |
| MAX_POSITIONS | 36 | 18 | 12 | ⚠️ 60.0% | 50.0% | ✅ OUTPERFORMING |
| DAILY_LOSS_LIMIT | 28 | 12 | 6 | ⚠️ 66.7% | 50.0% | ✅ OUTPERFORMING |
| MANUAL_OVERRIDE | 16 | 7 | 7 | ❌ 50.0% | 55.0% | 🟢 ON TARGET |

---

## Accuracy by Quality Tier of Rejected Trade

_High-quality trades being rejected (PREMIUM/HIGH tier) with low accuracy = system too aggressive_

| Quality Tier | Rejected | Correct | False | Accuracy |
|---|---|---|---|---|
| HIGH | 156 | 65 | 61 | ❌ 51.6% |
| MEDIUM | 264 | 165 | 63 | ✅ 72.4% |
| LOW | 84 | 40 | 28 | ⚠️ 58.8% |

> If PREMIUM/HIGH tier rejections show accuracy < 55%, the system is likely using a threshold that is too conservative.

---

## Missed Winners — False Rejection Analysis

**152 trades rejected that would likely have been winners.**

| Metric | Value |
|---|---|
| Missed winner count | 152 |
| Avg quality score of missed | 6.51 |
| Avg 5-day move (favourable) | +5.94% |
| Best missed move | +12.74% |
| Hypothetical total PnL (all rejections) | ₹-720,308 |

> Hypothetical PnL is **negative** — the rejection system is saving money overall.
> The missed winners are outweighed by the losses correctly avoided.

**Missed winners by rejection reason:**

| Reason | Count |
|---|---|
| LOW_DECISION_SCORE | 34 |
| LOW_QUALITY_SCORE | 28 |
| LOW_CONVICTION | 23 |
| CORRELATED_POSITION | 19 |
| LOW_SFT | 14 |
| MAX_POSITIONS | 12 |
| HIGH_VOL_REGIME | 9 |
| MANUAL_OVERRIDE | 7 |
| DAILY_LOSS_LIMIT | 6 |

---

## Conclusion

**Marginal accuracy (64.0%). System is borderline.**

152 trades were rejected but would have been winners.

**Recommended Action:** Review which rejection reasons have lowest accuracy (see table above). Consider relaxing those specific criteria.

---

*Shadow analysis only. No trades placed or modified.*