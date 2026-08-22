# NEWS AUDIT REPORT

**Generated:** 2026-06-19T09:33:07.505548+00:00
**Module:** NEWS_AUDIT_001
**Mode:** Shadow analysis — no live trading
**Total observations:** 576
**Observations with outcomes:** 308

---

## News Type Impact Summary

| News Type | Observations | WR% | Avg Move | Dir Accuracy | Strategy Impact | Verdict |
|---|---|---|---|---|---|---|
| TRADE_WAR | 10 | ✅ 100.0% | -2.03% | 0.0% | HIGH | — INSUFFICIENT_DATA |
| TAX_POLICY | 8 | ✅ 100.0% | -0.15% | 0.0% | HIGH | — INSUFFICIENT_DATA |
| CURRENCY_SHOCK | 12 | ✅ 83.3% | -1.39% | 0.0% | HIGH | 🟢 MODERATE_SIGNAL |
| INDEX_REBAL | 24 | ✅ 72.7% | +0.29% | 0.0% | MEDIUM | 🟢 MODERATE_SIGNAL |
| CORPORATE_ACTION | 60 | ✅ 67.7% | +0.60% | 0.0% | MEDIUM | 🟢 MODERATE_SIGNAL |
| SANCTIONS | 8 | ✅ 66.7% | -2.40% | 0.0% | HIGH | 🟢 MODERATE_SIGNAL |
| EARNINGS | 130 | ✅ 65.3% | +0.49% | 0.0% | HIGH | 🟢 MODERATE_SIGNAL |
| CRUDE_OIL_SHOCK | 16 | 🟢 62.5% | -1.63% | 0.0% | HIGH | 🟢 MODERATE_SIGNAL |
| SECTOR_NEWS | 80 | 🟢 60.0% | -0.50% | 0.0% | MEDIUM | 🟢 MODERATE_SIGNAL |
| FED_MEETING | 16 | 🟢 50.0% | +0.15% | 0.0% | MEDIUM | ⚠️ WEAK_SIGNAL |
| GEOPOLITICAL_TENSION | 16 | 🟢 50.0% | -2.07% | 0.0% | HIGH | — INSUFFICIENT_DATA |
| UPGRADE_DOWNGRADE | 100 | ⚠️ 44.4% | -0.22% | 0.0% | LOW | ❌ NO_SIGNAL |
| RBI_POLICY | 24 | ⚠️ 44.4% | -0.03% | 0.0% | MEDIUM | ❌ NO_SIGNAL |
| REGULATORY | 16 | ⚠️ 40.0% | -0.39% | 0.0% | MEDIUM | ❌ NO_SIGNAL |
| BUDGET | 8 | ⚠️ 40.0% | -0.57% | 0.0% | HIGH | ❌ NO_SIGNAL |
| ECB_MEETING | 16 | ❌ 37.5% | +0.58% | 0.0% | LOW | ❌ NO_SIGNAL |
| POLITICAL_EVENT | 12 | ❌ 33.3% | -0.55% | 0.0% | MEDIUM | — INSUFFICIENT_DATA |
| ELECTION | 6 | ❌ 25.0% | -0.42% | 0.0% | HIGH | — INSUFFICIENT_DATA |
| NATURAL_DISASTER | 8 | ❌ 20.0% | -1.96% | 0.0% | MEDIUM | ❌ NO_SIGNAL |

---

## Top 5 Positive Catalysts

_(News types with highest win rates — prioritise trading when these occur)_

### #1 CURRENCY_SHOCK
- **Win Rate:** 83.3%  (5/6 trades)
- **Avg 5-day move:** -1.39%
- **Direction Accuracy:** 0.0%
- **Note:** INR > 85 → FII outflows, broad selloff. DXY rally → EM pressure. IT exports benefit from weak INR.

### #2 INDEX_REBAL
- **Win Rate:** 72.7%  (8/11 trades)
- **Avg 5-day move:** +0.29%
- **Direction Accuracy:** 0.0%
- **Note:** Inclusions bid, exclusions sold. Predictable but short-lived.

### #3 CORPORATE_ACTION
- **Win Rate:** 67.7%  (21/31 trades)
- **Avg 5-day move:** +0.60%
- **Direction Accuracy:** 0.0%
- **Note:** Buybacks are reliably bullish. Bonus/split → sentiment bid.

### #4 SANCTIONS
- **Win Rate:** 66.7%  (4/6 trades)
- **Avg 5-day move:** -2.40%
- **Direction Accuracy:** 0.0%
- **Note:** Target-country assets fall sharply. Counter-party sectors (energy, metals) bid.

### #5 EARNINGS
- **Win Rate:** 65.3%  (64/98 trades)
- **Avg 5-day move:** +0.49%
- **Direction Accuracy:** 0.0%
- **Note:** Strongest single-stock catalyst. Avoid SHORT strategies pre-earnings.

---

## No-Signal News Types

_(These news types show no predictive value for trade outcomes)_

| News Type | Recommendation |
|---|---|
| FED_MEETING | Consider ignoring in trade filters — no edge found |
| UPGRADE_DOWNGRADE | Consider ignoring in trade filters — no edge found |
| RBI_POLICY | Consider ignoring in trade filters — no edge found |
| REGULATORY | Consider ignoring in trade filters — no edge found |
| NATURAL_DISASTER | Consider ignoring in trade filters — no edge found |
| ECB_MEETING | Consider ignoring in trade filters — no edge found |
| BUDGET | Consider ignoring in trade filters — no edge found |

> **Action:** Do NOT use these event types as trade signals.
> Continue tracking for at least 50 more observations before removing from system.

---

## Questions Answered

| Question | Answer |
|---|---|
| Do EARNINGS matter? | PARTIAL — WR=65.3%, direction accuracy=0.0% |
| Do CORPORATE ACTIONS matter? | PARTIAL — WR=67.7%, direction accuracy=0.0% |
| Do ANALYST calls matter? | NO — WR=44.4%, direction accuracy=0.0% |
| Does SECTOR NEWS matter? | PARTIAL — WR=60.0%, direction accuracy=0.0% |
| Do RBI decisions matter? | NO — WR=44.4%, direction accuracy=0.0% |
| Do Fed meetings matter? | PARTIAL — WR=50.0%, direction accuracy=0.0% |
| Does ECB meeting matter? | NO — WR=37.5%, direction accuracy=0.0% |
| Does BUDGET matter? | NO — WR=40.0%, direction accuracy=0.0% |
| Does TAX POLICY matter? | INSUFFICIENT DATA |
| Do ELECTIONS matter? | INSUFFICIENT DATA |
| Do POLITICAL EVENTS matter? | INSUFFICIENT DATA |
| Does WAR matter? | INSUFFICIENT DATA |
| Does GEOPOLITICAL TENSION matter? | INSUFFICIENT DATA |
| Do SANCTIONS matter? | PARTIAL — WR=66.7%, direction accuracy=0.0% |
| Does TRADE WAR matter? | INSUFFICIENT DATA |
| Do CRUDE OIL SHOCKS matter? | PARTIAL — WR=62.5%, direction accuracy=0.0% |
| Do CURRENCY SHOCKS matter? | PARTIAL — WR=83.3%, direction accuracy=0.0% |
| Are BLACK SWAN events tradeable? | INSUFFICIENT DATA |

---

## Conclusion

**7 news type(s) show no signal:** FED_MEETING, UPGRADE_DOWNGRADE, RBI_POLICY, REGULATORY, NATURAL_DISASTER, ECB_MEETING, BUDGET

These events are noise. Consider removing them from the decision pipeline.

---

*Shadow analysis only. No trades placed or modified.*