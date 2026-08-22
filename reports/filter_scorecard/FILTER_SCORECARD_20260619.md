# FILTER SCORECARD

**Generated:** 2026-06-19T09:33:14.173090+00:00
**Governance Dashboard — Evidence-Driven Filter Management**

| Status | Count |
|---|---|
| ✅ KEEP   (≥ 70%) | 3 |
| 🟢 WATCH  (55–70%) | 9 |
| ⚠️ REVIEW (45–55%) | 3 |
| ❌ REMOVE (< 45%) | 4 |
| — COLLECTING (< 10 obs) | 15 |

---

## Full Filter Scorecard

```
Filter                            Accuracy      N        Status  Action
────────────────────────────────────────────────────────────────────────────────

Rejection Filters:
  HIGH_VOL_REGIME                    82.4%     56  ✅       KEEP  Filter is working — no change needed
  LOW_SFT                            78.5%     70  ✅       KEEP  Filter is working — no change needed
  DAILY_LOSS_LIMIT                   66.7%     28  🟢      WATCH  Monitor for 4 more weeks before deciding
  LOW_DECISION_SCORE                 63.8%    110  🟢      WATCH  Monitor for 4 more weeks before deciding
  MAX_POSITIONS                      60.0%     36  🟢      WATCH  Monitor for 4 more weeks before deciding
  LOW_QUALITY_SCORE                  58.8%     84  🟢      WATCH  Monitor for 4 more weeks before deciding
  LOW_CONVICTION                     51.1%     60  ⚠️     REVIEW  Schedule parameter review this week
  MANUAL_OVERRIDE                    50.0%     16  ⚠️     REVIEW  Schedule parameter review this week
  CORRELATED_POSITION                45.7%     44  ⚠️     REVIEW  Schedule parameter review this week

Quality Tier Gates:
  TIER_PREMIUM                       69.6%     46  🟢      WATCH  Monitor for 4 more weeks before deciding
  TIER_HIGH                          64.1%     39  🟢      WATCH  Monitor for 4 more weeks before deciding
  TIER_MEDIUM                        37.5%     48  ❌     REMOVE  Candidate for removal — blocking more winners than losers
  TIER_LOW                           11.8%     17  ❌     REMOVE  Candidate for removal — blocking more winners than losers

News Signal Filters:
  NEWS_TRADE_WAR                    100.0%      2  — COLLECTING  Wait for more data
  NEWS_TAX_POLICY                   100.0%      3  — COLLECTING  Wait for more data
  NEWS_CURRENCY_SHOCK                83.3%      6  — COLLECTING  Wait for more data
  NEWS_INDEX_REBAL                   72.7%     11  ✅       KEEP  Filter is working — no change needed
  NEWS_CORPORATE_ACTION              67.7%     31  🟢      WATCH  Monitor for 4 more weeks before deciding
  NEWS_SANCTIONS                     66.7%      6  — COLLECTING  Wait for more data
  NEWS_EARNINGS                      65.3%     98  🟢      WATCH  Monitor for 4 more weeks before deciding
  NEWS_CRUDE_OIL_SHOCK               62.5%      8  — COLLECTING  Wait for more data
  NEWS_SECTOR_NEWS                   60.0%     40  🟢      WATCH  Monitor for 4 more weeks before deciding
  NEWS_FED_MEETING                   50.0%      6  — COLLECTING  Wait for more data
  NEWS_GEOPOLITICAL_TENSION          50.0%      4  — COLLECTING  Wait for more data
  NEWS_UPGRADE_DOWNGRADE             44.4%     45  ❌     REMOVE  Candidate for removal — blocking more winners than losers
  NEWS_RBI_POLICY                    44.4%     18  ❌     REMOVE  Candidate for removal — blocking more winners than losers
  NEWS_REGULATORY                    40.0%      5  — COLLECTING  Wait for more data
  NEWS_BUDGET                        40.0%      5  — COLLECTING  Wait for more data
  NEWS_ECB_MEETING                   37.5%      8  — COLLECTING  Wait for more data
  NEWS_POLITICAL_EVENT               33.3%      3  — COLLECTING  Wait for more data
  NEWS_ELECTION                      25.0%      4  — COLLECTING  Wait for more data
  NEWS_NATURAL_DISASTER              20.0%      5  — COLLECTING  Wait for more data
  NEWS_WAR                            0.0%      0  — COLLECTING  Wait for more data
  NEWS_BLACK_SWAN                     0.0%      0  — COLLECTING  Wait for more data
```

---

## ❌ Immediate Action — REMOVE Candidates

These filters are blocking more winners than losers.
Consider removing or relaxing until recalibrated.

- **TIER_LOW**  (accuracy=11.8%, n=17)  — Candidate for removal — blocking more winners than losers
- **TIER_MEDIUM**  (accuracy=37.5%, n=48)  — Candidate for removal — blocking more winners than losers
- **NEWS_UPGRADE_DOWNGRADE**  (accuracy=44.4%, n=45)  — Candidate for removal — blocking more winners than losers
- **NEWS_RBI_POLICY**  (accuracy=44.4%, n=18)  — Candidate for removal — blocking more winners than losers

---

## ⚠️ Schedule Review This Week

- **CORRELATED_POSITION**  (accuracy=45.7%, n=44)
- **LOW_CONVICTION**  (accuracy=51.1%, n=60)
- **MANUAL_OVERRIDE**  (accuracy=50.0%, n=16)

---

## Governance Rules

| Accuracy | Status | Rule |
|---|---|---|
| ≥ 70% | ✅ KEEP | Filter is working — no change |
| 55–70% | 🟢 WATCH | Monitor for 4 more weeks |
| 45–55% | ⚠️ REVIEW | Schedule parameter review |
| < 45% | ❌ REMOVE | Candidate for removal |
| < 10 obs | — COLLECTING | Wait for more data |

> A filter's accuracy score is computed from:
> - **Rejection filters:** % of rejected trades that would have lost (correct rejections)
> - **Quality tier gates:** % of trades in that tier that resulted in a WIN
> - **News signal filters:** % of news-tagged trades that resulted in a WIN

---

*Filter Scorecard generated from live audit databases. Accuracy figures update every time the audit modules are re-run.*