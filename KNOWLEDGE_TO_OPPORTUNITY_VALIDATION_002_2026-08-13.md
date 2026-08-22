# KNOWLEDGE_TO_OPPORTUNITY_VALIDATION_002
**Date:** 2026-08-13  
**Prepared by:** Copilot — read-only research  
**Scope:** Does existing short DNA improve OPPORTUNITY DISCOVERY (not trading)?  
**Parent studies:** HIGH_RSI_SHORT_VALIDATION_001, SHORT_DNA_STRICT_VARIANT_RESEARCH_001  
**Production changes:** NONE  
**Orders placed:** 0  

---

## ARCHITECTURE PRINCIPLE UNDER TEST

```
MARKET EVENT
    ↓
OPPORTUNITY DISCOVERY  ← this study tests DNA's role here
    ↓
KNOWLEDGE CONFIRMATION
    ↓
OPPORTUNITY RANKING
    ↓
STRATEGY / GOVERNANCE
    ↓
TRADE              ← DNA must NOT bypass this layer
```

**Critical distinction maintained throughout**: a stock that receives a DNA signal is NOT a trade. The DNA layer is evaluated solely on its ability to surface stocks that subsequently become significant market movers. Governance and execution layers remain entirely separate.

---

## Executive Summary

| Item | Value |
|---|---|
| **Overall verdict** | **C — DNA NOT SUFFICIENTLY USEFUL for SHORT opportunity discovery specifically** |
| Opportunity verdict | `DNA_MARGINAL_FOR_OMNIDIRECTIONAL` |
| Trading verdict | `FAIL — already established by VALIDATION_001` |
| Test period | 2021-07-01 – 2025-12-30 (4.5 years, 210 NSE stocks) |
| Total stock-day events | 197,702 |
| Baseline signals | 8,886 (RSI ≥ 67, Range+Volatile, no DNA) |
| DNA signals | 1,423 (RSI ≥ 70, RANGE only, vol_ratio ≥ 1.5×) |
| Loser precision — Baseline | 52.6% |
| Loser precision — DNA | 56.6% (+4.0pp) |
| **Gainer precision — DNA** | **64.4%** (higher than loser precision — critical finding) |
| Avg final return (DNA group) | **+0.594%** (positive — stocks tend UP after DNA signal) |
| DNA loser lift vs baseline | 1.076× |
| BML day coverage | 0/5 significant losers caught on Aug-11 and Aug-13 combined |
| Data leakage | NONE_FOUND (11/11 checks) |

**The DNA filter improves overall mover detection (+4pp) but does NOT specifically improve SHORT-direction opportunity identification. Stocks qualifying the DNA condition are more likely to continue upward (64.4% hit +2% threshold) than to reverse downward (56.6% hit −2% threshold). The vol_ratio ≥ 1.5× condition identifies institutional activity moments — not specifically distribution/topping events.**

---

## Phase 1 — Existing Knowledge Path Trace

### 1.1 Where Short DNA Lives

```
institutional_dna.db                 → data/mls/institutional_dna.db
  table: dna
  row: feature_name="volume_spike"
       direction="SHORT"
       confidence=1.0
       evidence_count=135
       lifecycle="INSTITUTIONAL"
       last_updated=2026-08-05
```

### 1.2 Where DNA is Currently Read

| Component | File | Status |
|---|---|---|
| `_load_loser_dna()` | `production_readiness/ph2_short_dna.py:38` | Reads `institutional_dna.db` |
| `evaluate_short_dna()` | `production_readiness/ph2_short_dna.py:61` | Evaluates features against DNA conditions |
| `get_short_dna_confidence_boost()` | `production_readiness/ph2_short_dna.py:148` | Returns float boost |
| `run_short_dna_audit()` | `production_readiness/ph2_short_dna.py:156` | Generates audit report |

### 1.3 Where DNA is Currently NOT Connected

| Gap | File | Impact |
|---|---|---|
| `_identify_setup()` in equity_scanner_ai.py | Never calls `get_short_dna_confidence_boost()` | DNA boost is computed but unused in signal generation |
| `score_candidate()` in market_scanner.py | No DNA lookup for `overbought_short_watch` bucket | Bucket is labelled but not enriched with knowledge |
| `candidate_store.py` | No DNA-based opportunity watchlist | No separate short-opportunity queue exists |
| `premarket_refiner.py` | `overbought_short_watch` slot defined at 09:00 | Slot exists but no DNA integration |

### 1.4 Existing Opportunity/Watch Concepts

The system already has an **`overbought_short_watch` bucket** in `market_scanner.py:935`:
```python
OVERBOUGHT_RSI_MIN = 65.0  # RSI ≥ 65 → tagged
if rsi >= OVERBOUGHT_RSI_MIN:
    buckets.append("overbought_short_watch")
```

This bucket is **observational only** — it produces no separate scoring track, no DNA enrichment, and no routing to a short opportunity queue. As confirmed by the previous audit:
- 7 stocks had `overbought_short_watch` on Aug-11
- Their scanner scores were **PENALISED** (not boosted) by the RSI deviation from 35–65 range
- Zero Setup 4 signals emerged from these 7 stocks on that day

The `premarket_refiner.py` has a registered slot for `overbought_short_watch` at 09:00 IST — indicating an **architectural intention** that was never implemented. This is the correct insertion point for a DNA-enriched short opportunity layer.

### 1.5 ILC / PGA / CLE Integration Status

From BML-001 and CLE reports: the Institutional Learning Cycle (ILC) currently classifies all universe symbols against top-20 gainers/losers daily, but:
- DNA coverage column in ILC reports shows `0` for all 40 audited symbols on Aug-11
- This is consistent with the IDR being empty on VPS: `"zero DNA coverage — IDR is empty"`
- Short DNA has never been used in any ILC cycle, CLE decision, or PGA ranking

---

## Phase 2 — Opportunity vs Trade Distinction

The following framework is used throughout this study:

| Layer | Function | DNA involvement |
|---|---|---|
| **Market Event** | RSI, volume, price at resistance | Input data |
| **Opportunity Discovery** | "This stock is doing something interesting" | **DNA tested here** |
| **Knowledge Confirmation** | Does DNA corroborate the event? | DNA filter applied |
| **Opportunity Ranking** | Score among competing opportunities | Not tested here |
| **Strategy / Governance** | Does a governed strategy exist for this? | VALIDATION_001: NO |
| **Trade** | Actual order | NEVER from DNA alone |

**Governance wall**: DNA at the Opportunity Discovery layer means: "add this stock to a research watchlist for human or downstream review." It does NOT mean: "generate a trade signal." The strategy and governance layers remain the sole authority for trade decisions.

---

## Phase 3 — Historical Opportunity Test

### 3.1 Methodology

- **Data**: replay.db, 210 NSE equities, 2021-07-01 to 2025-12-30
- **Mover definition**: |daily_return| ≥ 2% on any day within the 5-day forward window (this is the BML "significant mover" threshold — used in existing ILC audits for top-20 analysis)
- **Forward evaluation**: bars[t+1 .. t+5] only. Zero look-ahead.
- **Conservative**: stock prices observed through daily high (gainer) and low (loser) to capture intraday extremes

### 3.2 Four-Way Comparison

| Group | Definition | n signals | Coverage | Loser precision | Gainer precision | Avg final return |
|---|---|---|---|---|---|---|
| **Baseline** | RSI ≥ 67, Range+Volatile, no DNA | 8,886 | 4.5% of events | 52.6% | 57.4% | +0.325% |
| **RSI70+Range (no DNA)** | RSI ≥ 70, Range only, no DNA | 6,476 | 3.3% | 52.8% | 57.0% | +0.379% |
| **DNA (strict variant)** | RSI ≥ 70, Range only, vol_ratio ≥ 1.5× | 1,423 | 0.72% | **56.6%** | **64.4%** | **+0.594%** |

### 3.3 Key Observation on Group Comparisons

RSI ≥ 70 (without DNA) adds +0.2pp loser precision over RSI ≥ 67. Adding DNA adds +3.8pp on top of that. The majority of improvement comes from the **DNA filter, not the stricter RSI threshold**.

However — and this is the critical finding — the **gainer precision increases MORE than loser precision** when DNA is applied:
- Loser precision increase: +4.0pp (52.6% → 56.6%)
- Gainer precision increase: +7.0pp (57.4% → 64.4%)

**The DNA filter selects high-volatility/high-activity events that move significantly in EITHER direction, with a slight bullish bias.**

---

## Phase 4 — SHORT vs LONG Asymmetry Test

### 4.1 Directional Breakdown

| Metric | Baseline | DNA |
|---|---|---|
| Signals that became losers (−2%+ in 5 days) | 52.6% | 56.6% |
| Signals that became gainers (+2%+ in 5 days) | 57.4% | 64.4% |
| Neither (stayed within ±2%) | 9.3% | 4.9% |
| Avg max loss within 5 days | −2.85% | −3.20% |
| Avg max gain within 5 days | +3.35% | +4.06% |
| Average final return (5-day) | +0.325% | +0.594% |
| Loser lift (DNA/Baseline) | — | 1.076× |

**Critical finding**: DNA-confirmed stocks are nearly as likely to rise 2%+ as to fall 2%+ within 5 days. The net average 5-day return is **positive (+0.594%)** — meaning that stocks at RSI ≥ 70 near resistance with a volume spike tend to **continue upward on average**. This is the same structural reason the SHORT trading strategy fails (momentum continuation beats mean reversion in this dataset).

The "neither" category (stocks staying within ±2%) is very small for DNA signals (4.9% vs 9.3% baseline), confirming that DNA does select volatile/moving stocks — but the direction is not reliably short-favourable.

### 4.2 Did DNA Identify Stocks Before the Move?

Of the 805 DNA signals that preceded a −2%+ drop:
- Average lead time: **2.12 days** before the drop
- Median lead time: **2 days**
- Range: 1–5 days

This means DNA evidence was available 2+ days BEFORE the significant downward move, on average. This is a genuine lead-time advantage. However, this only applies to the 56.6% subset that actually dropped. The remaining 43.4% continued upward or stayed flat.

### 4.3 Pre-Move Coverage vs. Universe

| Metric | Value |
|---|---|
| Total significant loser events in universe (2021–2025) | 112,411 |
| Significant loser events covered by DNA signals | 805 (0.72%) |
| Significant gainer events covered by DNA signals | 917 (0.74%) |
| Baseline loser recall | 4.15% of all loser events |
| DNA loser recall | 0.72% of all loser events |

**The DNA filter has very low RECALL**: it covers only 0.72% of all significant loser events across the universe. The baseline covers 4.15%. This is expected (DNA is restrictive by design), but it means DNA-confirmed signals represent a small fraction of all available opportunities.

---

## Phase 5 — Opportunity Metrics

| Metric | Baseline | DNA | Delta |
|---|---|---|---|
| **Pre-move loser coverage** | 4.15% of all loser events | 0.72% | −3.43pp (expected — DNA is restrictive) |
| **Loser precision** | 52.6% | 56.6% | +4.0pp |
| **Gainer precision** | 57.4% | 64.4% | +7.0pp (HIGHER than loser gain) |
| **False-positive rate** | 47.4% | 43.4% | −4.0pp improvement |
| **Average lead time** | — | 2.12 days | Meaningful |
| **Signal reduction vs baseline** | — | −84% | DNA is highly selective |
| **Average final return** | +0.325% | +0.594% | +0.269% (stocks trend UP) |
| **DNA loser lift vs baseline** | — | 1.076× | Small but consistent |

### 5.1 Precision Interpretation

The loser precision of 56.6% means: for every 100 DNA-confirmed "short opportunity" candidates, approximately **57 will drop ≥2%** within 5 trading days. This is modestly better than random chance among this signal class (baseline: 52.6%).

However, **64 of those same 100 stocks will also rise ≥2%** at some point in the same window. These numbers are not mutually exclusive (a stock can swing up then down, or vice versa). The net direction is slightly bullish (+0.594% avg 5-day return).

### 5.2 The Directional Problem

For the DNA to be useful as a **SHORT opportunity discovery tool**, the following must hold:
1. DNA-confirmed stocks should drop ≥2% more often than they rise ≥2% — **FAILS** (56.6% < 64.4%)
2. The average 5-day return should be negative — **FAILS** (+0.594% is positive)
3. DNA should show a loser lift significantly above 1.0 — **MARGINAL** (1.076× is barely above random)

For the DNA to be useful as a **GENERAL VOLATILITY/ACTIVITY opportunity detector**, the following holds:
1. DNA signals are more likely to produce significant moves (+2%) in some direction than baseline — **PASSES** (95.1% hit ±2% vs 90.7% baseline)
2. DNA selects genuinely volatile/moving stocks — **PASSES**
3. DNA reduces irrelevant signals by 84% — **PASSES** (but these were already high-quality signals)

---

## Phase 6 — BML Day Validation (2026-08-11 and 2026-08-13)

### 6.1 Data Limitation

The replay.db OHLCV data ends at **2025-12-30**. The BML audit dates (2026-08-11 to 08-13) are beyond the database. Therefore, the historical DNA signal lookup cannot produce results for these specific dates. The DNA signal index for these dates returns zero candidates. This is a data availability gap, not a methodology failure.

### 6.2 Aug-11 Overbought Candidates — DNA Filter Application

The Aug-11 `daily_candidates_20260811.json` contains 7 `overbought_short_watch` candidates:

| Symbol | RSI | Vol_ratio | DNA gate (≥1.5×)? | Aug-13 outcome |
|---|---|---|---|---|
| INDIANB | 67.1 | 1.09 | **REJECTED** | Not in top-20 losers |
| BOSCHLTD | 66.6 | 0.83 | **REJECTED** | Not in top-20 losers |
| NAUKRI | 70.4 | 0.72 | **REJECTED** | Not in top-20 losers |
| DEEPAKNTR | 66.7 | 0.71 | **REJECTED** | Not in top-20 losers |
| PNBHOUSING | 64.2 | 0.65 | **REJECTED** | Not in top-20 losers |
| NESTLEIND | 65.0 | 0.78 | **REJECTED** | Actually a GAINER on Aug-13 (+0.74%) |
| MAZDOCK | 68.6 | 1.12 | **REJECTED** | Not in top-20 losers |

**Observation**: On Aug-11, all 7 overbought candidates had vol_ratio below 1.5×. The DNA filter correctly rejected ALL of them. Notably, NESTLEIND was a top-15 GAINER on Aug-13, confirming the DNA rejection was appropriate.

### 6.3 Aug-13 Top-20 Losers — Pre-Signal Analysis

The 5 significant losers on Aug-13 (≥−2%): EASEMYTRIP (−3.09%), ZYDUSLIFE (−2.71%), HINDALCO (−2.39%), PAGEIND (−2.26%), DIVISLAB (−2.08%).

**None of these were identifiable by DNA on Aug-11 because**:
1. They did not appear in the Aug-11 scanner as overbought candidates (RSI was not ≥67 on Aug-11)
2. They had no volume spike signal on Aug-11
3. Their subsequent drop was driven by Aug-12/13 developments (gap downs, sector weakness), not by pre-existing RSI-overbought conditions

This is a structural insight: the most significant losers on a given day were often **NOT overbought on the prior day** — they were at neutral RSI levels and dropped due to fundamental, macro, or technical breakdown events that the DNA pattern was not designed to capture.

### 6.4 BML Coverage Analysis

| Date | Sig. losers (≤−2%) | DNA caught | Base caught | Coverage |
|---|---|---|---|---|
| 2026-08-11 | 6 | 0 | 0 | 0% |
| 2026-08-13 | 5 | 0 | 0 | 0% |

Neither the DNA filter nor the baseline scanner had any signal-overlap with the significant losers on either audit date. This is consistent with the universe-wide recall finding (0.72%) — the DNA pattern is rare and misses the majority of significant loser events.

---

## Phase 7 — IIOS Philosophy Test

**Question: Does compiled knowledge improve candidate quality beyond raw strategy signals?**

| Layer | Precision | Delta vs previous |
|---|---|---|
| Raw strategy (RSI ≥ 67, no filter) | 52.6% | — |
| Stricter RSI only (RSI ≥ 70, no DNA) | 52.8% | +0.2pp |
| Strategy + Knowledge (DNA filter) | 56.6% | +3.8pp vs RSI-70; +4.0pp vs baseline |

**Compiled knowledge DOES improve precision** — but not in the way intended. The +4.0pp improvement applies equally to upward moves (gainer precision +7.0pp) as to downward moves (loser precision +4.0pp). The DNA filter identifies "stocks that are about to make a big move" rather than "stocks that are about to reverse downward."

This aligns with the theoretical basis of the volume_spike DNA pattern: **institutional volume spikes at overbought levels represent periods of abnormal market activity** — which is directionally ambiguous (could be institutional distribution OR continued momentum buying by large players).

**Conclusion for IIOS philosophy test**: Yes, compiled knowledge improves candidate selection quality (+4pp precision, −84% noise). However, the improvement is not directionally aligned with the SHORT thesis. Knowledge identifies high-activity stocks; governance must supply direction.

---

## Phase 8 — No Production Changes

This study is read-only throughout. No files were modified.

| File | Status |
|---|---|
| `strategy_lab/strategy_generator_ai.py` | NOT MODIFIED |
| `opportunity_engine/market_scanner.py` | NOT MODIFIED |
| `production_readiness/ph2_short_dna.py` | NOT MODIFIED |
| `opportunity_engine/equity_scanner_ai.py` | NOT MODIFIED |
| `strategy_lab/backtesting_ai.py` | NOT MODIFIED |
| `data/strategy_params` | NOT MODIFIED |
| All risk controls and capital allocation | NOT MODIFIED |

---

## Phase 9 — Data Leakage Audit

All 11 checks passed. **DATA_LEAKAGE = NONE_FOUND**

| Check | Result | Notes |
|---|---|---|
| RSI(14) uses closes[0..t] only | ✓ PASS | No future closes |
| vol_ratio uses vols[-3:]/vols[-20:] at date t | ✓ PASS | Past bars only |
| Resistance = 20d rolling HIGH ending at t | ✓ PASS | `highs[-20:]` |
| Forward moves from bars[t+1..t+5] only | ✓ PASS | No same-day or earlier bars |
| Regime uses NIFTY log-returns ending at t | ✓ PASS | Past data only |
| DNA condition (vol_ratio) is structural | ✓ PASS | No outcome data used in DNA condition |
| BML mover outcome uses future bars only | ✓ PASS | bars[idx+1..idx+5] |
| BML Phase-6 data from actual ILC audit files | ✓ PASS | No reconstruction |
| Aug-11 vol_ratios from daily_candidates_20260811.json | ✓ PASS | Live snapshot from that day |
| No future BML ranking used in signal selection | ✓ PASS | Ranking computed post-hoc |
| DNA db dated 2026-08-05 (before study dates) | ✓ PASS | No forward DNA records used |

---

## Phase 10 — Final Verdict and Recommendations

### 10.1 Answering the 7 Governance Questions

| Question | Answer |
|---|---|
| 1. Does existing short DNA improve opportunity discovery? | **MARGINAL YES** — +4pp loser precision, −84% signal volume |
| 2. Does it identify significant losers before they move? | **PARTIAL** — 56.6% of DNA signals precede −2%+ drops (vs 52.6% baseline); but same signals also precede +2%+ rises 64.4% of the time |
| 3. Does it identify them earlier than the scanner? | **NOT APPLICABLE** — DNA fires at same time as scanner (same RSI/price triggers); no temporal lead over scanner |
| 4. Does it reduce false positives? | **YES** — FPR reduced 47.4% → 43.4% (−4pp); 84% signal volume reduction |
| 5. Does it add incremental information beyond the scanner? | **YES FOR VOLATILITY, NOT FOR DIRECTION** — DNA identifies high-activity moments but not specifically SHORT-direction moments |
| 6. Is evidence strong enough to justify connecting DNA to OPPORTUNITY layer? | **INSUFFICIENT** — gainer rate (64.4%) exceeds loser rate (56.6%); net 5-day return is positive; BML audit days showed 0% coverage |
| 7. Is evidence strong enough to justify connecting DNA to TRADING layer? | **NO** — already established as FAIL by VALIDATION_001 and STRICT_VARIANT study |

### 10.2 Final Verdict

**Verdict: C — DNA not sufficiently useful for SHORT-specific opportunity discovery**

The volume_spike SHORT DNA condition (vol_ratio ≥ 1.5×) is:
- ✅ A genuine filter for high-activity events (+4pp precision, −84% noise)
- ✅ Associated with significant moves in SOME direction (95.1% hit ±2% vs 90.7% baseline)
- ✅ Provides early identification (avg 2.12 days before the move)
- ❌ NOT specifically predictive of downward moves (gainer rate 64.4% > loser rate 56.6%)
- ❌ Net average return is POSITIVE (+0.594%) — contradicts SHORT thesis
- ❌ Only 0.72% recall of all loser events — misses 99.3% of significant losses
- ❌ Zero coverage of the actual BML audit days (2026-08-11, 2026-08-13)

The label "SHORT" in `institutional_dna.db` reflects the INTENDED application of this pattern, not an empirically validated directional bias. The volume_spike feature itself is directionally neutral.

### 10.3 What DNA Is Actually Measuring

Volume spikes at RSI ≥ 70 represent **abnormal institutional activity at overbought levels**. This can mean:
- Institutional distribution (selling into retail momentum) → leads to reversal (SHORT correct)
- Institutional accumulation (breaking out through resistance with conviction) → leads to continuation (SHORT wrong)
- Retail FOMO buying with institutional participation → continuation then reversal (timing-dependent)

Without additional context (order flow direction, sector alignment, event catalyst), the volume spike is equally consistent with bullish continuation and bearish reversal. This explains both the elevated loser precision (56.6%) AND the even-more-elevated gainer precision (64.4%).

### 10.4 Recommendations

**DO NOT** connect DNA to the trading pipeline (confirmed across 3 studies).

**Regarding the opportunity layer**:

| Action | Grade | Rationale |
|---|---|---|
| Connect DNA to `overbought_short_watch` bucket enrichment as a volatility/watchlist flag | **B** | Adds genuine value for high-activity identification, with explicit label "VOLATILE_WATCH" (not "SHORT_WATCH") |
| Use DNA to build a "high-activity alert" watchlist (both directions) | **B** | DNA identifies stocks likely to make significant moves — useful for discretionary review |
| Use DNA as a SHORT-specific opportunity filter | **D** | Evidence contradicts directional bias; gainer rate exceeds loser rate |
| Register DNA-flagged stocks directly in any trading pipeline | **F** | Explicitly prohibited by VALIDATION_001 and STRICT_VARIANT verdicts |

**If the development team wishes to pursue a meaningful short-opportunity discovery capability, the following additional evidence is required**:
1. A directional enrichment layer beyond vol_ratio (e.g., sector breadth turning negative, options put/call ratio, earnings risk)
2. Regime conditioning beyond RANGE_MARKET/VOLATILE (e.g., specific post-earnings or macro shock conditions)
3. A minimum of 3 governance-passing walk-forward folds in OOS data before any opportunity-layer connection

---

## Appendix A — Temporal Precision Breakdown (DNA Group)

| Period | n | Losers | Loser Precision | Consistent? |
|---|---|---|---|---|
| 2021-H2 | 116 | 65 | 56.0% | ✅ |
| 2022-H1 | 67 | 47 | **70.1%** | ✅ |
| 2022-H2 | 174 | 107 | 61.5% | ✅ |
| 2023-H1 | 183 | 101 | 55.2% | ✅ |
| 2023-H2 | 342 | 175 | 51.2% | ⚠️ borderline |
| 2024-H1 | 153 | 95 | 62.1% | ✅ |
| 2024-H2 | 149 | 90 | 60.4% | ✅ |
| 2025-H1 | 78 | 47 | 60.3% | ✅ |
| 2025-H2 | 161 | 78 | **48.4%** | ❌ |

Loser precision is above 50% in 8 of 9 periods. However, 2025-H2 (48.4%) is the most recent period — showing the strategy's directional weakness is worsening in the most recent data. The high 2022-H1 result (70.1%) corresponds to the Russia-Ukraine correction period — a macro bear shock that amplified mean reversion at overbought levels. This type of correlated market event inflates DNA performance in specific periods.

## Appendix B — Study Chain

| Document | Date | Verdict |
|---|---|---|
| KNOWLEDGE_TO_OPPORTUNITY_AUDIT_001_2026-08-13.md | 2026-08-13 | F-2 (routing gap), F-3 (DNA disconnected) identified |
| SHORT_OPPORTUNITY_PRE_IMPLEMENTATION_AUDIT_001_2026-08-13.md | 2026-08-13 | F-2/F-3 confirmed; backtest prerequisite set |
| HIGH_RSI_SHORT_VALIDATION_001_2026-08-13.md | 2026-08-13 | FAIL — original strategy |
| SHORT_DNA_STRICT_VARIANT_RESEARCH_001_2026-08-13.md | 2026-08-13 | FAIL — strict variant; OOS promising but n=38 |
| **KNOWLEDGE_TO_OPPORTUNITY_VALIDATION_002_2026-08-13.md** | **2026-08-13** | **C — DNA not sufficiently directional for SHORT** |

## Appendix C — Output Files

| File | Status |
|---|---|
| `data/ktov002_result.json` | Generated — machine-readable |

---

```
[KNOWLEDGE_TO_OPPORTUNITY_VALIDATION_002]

Universe coverage:          100% (210 active NSE stocks)
Scanner coverage:           8,886 stock-days baseline (overbought signals)
DNA opportunity coverage:   1,423 stock-days (0.72% of all events)
Incremental DNA coverage:   −84% signal reduction vs baseline
Pre-move recall:            0.72% of all significant loser events
Opportunity precision:      56.6% (vs 52.6% baseline) — +4.0pp
False-positive rate:        43.4% (vs 47.4% baseline) — −4.0pp improvement
Average lead time:          2.12 days before ≥2% drop (n=805)

Gainer capture:             64.4% of DNA signals became ≥+2% gainers
Loser capture:              56.6% of DNA signals became ≥−2% losers
NOTE: Gainer rate > Loser rate — directional bias is BULLISH not BEARISH

Scanner-only precision:     52.6%
Scanner + DNA precision:    56.6% (+4.0pp)

DNA incremental value:
  For loser precision:    YES (+4.0pp)
  For direction (SHORT):  NO (gainer rate exceeds loser rate by 7.8pp)
  For avg final return:   NO (stocks trend UP on average: +0.594%)

Data leakage:
  NONE_FOUND (11/11 checks)

Opportunity-layer recommendation:
  INSUFFICIENT_EVIDENCE for SHORT-specific opportunity connection.
  DNA identifies high-VOLATILITY events, not specifically SHORT-favourable reversals.
  Connecting DNA to a generic "high-activity watch" with explicit bidirectional
  labelling is Grade B. Connecting to a SHORT opportunity queue is Grade D.

Trading-layer recommendation:
  FAIL — do not activate high_rsi_short.
  Confirmed across: VALIDATION_001, STRICT_VARIANT, and this study.
  Do not register, route, or enable in any production pipeline.

Production changes:
  NONE

Orders:
  0
```

---

*This document is read-only research. No production code was modified.*  
*Study ID: KNOWLEDGE_TO_OPPORTUNITY_VALIDATION_002*  
*Executed: 2026-08-13*
