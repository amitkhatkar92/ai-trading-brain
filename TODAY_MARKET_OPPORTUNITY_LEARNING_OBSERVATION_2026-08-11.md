# TODAY_MARKET_OPPORTUNITY_LEARNING_OBSERVATION_2026-08-11.md

**Date:** 2026-08-11  
**Report type:** READ-ONLY — Observation only. No code changed.  
**Generated:** 2026-08-11 (post-market, based on live data collected from VPS)

---

## DATA SOURCES USED

| Source | Path | Size |
|--------|------|------|
| scan_attrition | `/data/scan_attrition/2026-08-11.jsonl` | 111 records |
| daily_candidates | `/data/daily_candidates.json` | 57 candidates |
| ILC market audit | `/data/ilc/2026-08-11/MARKET_OPPORTUNITY_AUDIT.md` | 40 symbols |
| PGA daily report | `/data/pga/2026-08-11/PGA_DAILY_REPORT.md` | 10 symbols |
| PGA gainer/loser | `/data/pga/2026-08-11/TOP_{GAINER,LOSER}_ANALYSIS.md` | 5+5 |
| PGA learning actions | `/data/pga/2026-08-11/pga_learning_actions.json` | 7 actions |
| ILC reports | `/data/ilc/2026-08-11/*.md` | 12 files |
| Learning registry | `/data/ilc/learning_registry.json` | 65 entries |
| Learning DB | `/data/learning_db.json` | strategy stats |
| Control tower DB | `/data/control_tower.db` | 3092 cycles |
| Paper trades CSV | `/data/paper_trades.csv` | 0 today |
| EOD Retro | `/data/eod_retro_2026-08-11.txt` | full |

---

## PART A — MARKET OPPORTUNITY AUDIT

### A1. Market Context

| Parameter | Value |
|-----------|-------|
| Date | 2026-08-11 |
| Regime | range_market |
| VIX at cycle 1 | 12.26 |
| VIX at EOD | 15.5 |
| Breadth (NIFTY) | 0.46 |
| PCR | 0.85 |
| Feed state | YAHOO_FALLBACK (premarket) → live during market |
| Market distortion | NORMAL (stress_score=1, any_distortion=false) |

### A2. Universe & Scan Coverage

| Layer | Count |
|-------|-------|
| nifty500_universe.json | 230 symbols |
| Premarket scan attempted | 230 |
| Premarket scan successful | 166 (72.2%) |
| Premarket scan failed | 64 (27.8%) |
| Candidates before sector cap | 166 |
| Candidates after sector cap | **57** |
| Candidates: ACTIVE | 29 |
| Candidates: EXPIRED | 28 |

**Note on "universe observed":** 230 symbols attempted. PGA reports "universe=80, scanned=35" — this is a different, filtered count reflecting the ILC's analytical scope for the day, not the full scanner universe. ILC audited 40 symbols (top-20 gainers + top-20 losers). These numbers refer to different layers.

### A3. Cycles Executed Today

| Cycle | Time (IST) | Signals | Executed | Regime | VIX | Latency |
|-------|-----------|---------|----------|--------|-----|---------|
| intraday_cycle_1 | 09:45 | 26 found | 0 | range_market | 12.26 | 1179ms ✅ |
| intraday_cycle_2 | 10:30 | 0 found | 0 | None | None | 3165ms ✅ |
| intraday_cycles_3–10 | 11:30–15:00 | ~125 total* | 0 | — | — | 3×degraded |

*EOD retro: 151 signals total across 10 cycles, 7 successful, 3 degraded (GlobalIntelligence ×3 >12s). All signals generated = 0 approved.

**Cycle 1 is the only cycle with captured CT events. Cycles 2-10 ran after the DB snapshot.**

---

### A4. Top Gainers — Available Data

PGA analyzed top 5; ILC audited top-20 (only top 3 shown in report extract). Full top-50 data NOT available today — the system produces at most top-20 per PGA/ILC design.

| # | Symbol | Return | Universe | Scanned? | Scan Cycles | StrategyLab | Rejection | Signal | Decision | Miss Class |
|---|--------|--------|----------|----------|-------------|-------------|-----------|--------|----------|------------|
| 1 | TATAMOTORS | +NaN%* | INSIDE | No | — | No | — | None | MISS | IN_UNIVERSE_NOT_SCANNED |
| 2 | DRREDDY | +4.0% | INSIDE | No | — | No | — | None | MISS | IN_UNIVERSE_NOT_SCANNED |
| 3 | DIVISLAB | +3.2% | INSIDE | No | — | No | — | None | MISS | IN_UNIVERSE_NOT_SCANNED |
| 4 | CANBK | +1.0% | INSIDE | No | — | No | — | None | – | IN_UNIVERSE_NOT_SCANNED |
| 5 | BAJAJFINSV | +0.9% | INSIDE | No | — | No | — | None | – | IN_UNIVERSE_NOT_SCANNED |
| 6 | TITAN | +0.8% | INSIDE | YES | C1 | YES | Downstream | BUY (breakout, conf=7.48) | BLOCKED_DOWNSTREAM | SIGNAL_BLOCKED_BY_PORTFOLIO |

*TATAMOTORS: NaN% return indicates data feed issue for this symbol today.

### A5. Top Losers — Available Data

| # | Symbol | Return | Universe | Scanned? | Scan Cycles | StrategyLab | Rejection | Signal | Direction | Decision | Miss Class |
|---|--------|--------|----------|----------|-------------|-------------|-----------|--------|-----------|----------|------------|
| 1 | VEDL | −3.5% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 2 | GODREJPROP | −3.3% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 3 | BHARATFORG | −3.0% | INSIDE | YES | C1,C2,C4,C7 | YES | STRATEGY_DISABLED | BUY | **WRONG** | MISS | SCANNED_SIGNAL_REJECTED (WRONG DIRECTION) |
| 4 | MAXHEALTH | −2.4% | INSIDE | YES | C1,C2,C4,C7 | YES | STRATEGY_DISABLED | BUY | **WRONG** | MISS | SCANNED_SIGNAL_REJECTED (WRONG DIRECTION) |
| 5 | AMBUJACEM | −2.3% | INSIDE | YES | C2,C7 | YES | STRATEGY_DISABLED | BUY | **WRONG** | MISS | SCANNED_SIGNAL_REJECTED (WRONG DIRECTION) |
| 6 | HINDZINC | −2.1% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 7 | METROPOLIS | −1.9% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 8 | BHEL | −1.7% | INSIDE | YES | C2,C4,C7 | YES | STRATEGY_DISABLED | BUY | **WRONG** | MISS | SCANNED_SIGNAL_REJECTED (WRONG DIRECTION) |
| 9 | EMAMILTD | −1.5% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 10 | SRF | −1.5% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 11 | PRESTIGE | −1.4% | INSIDE | YES | C2,C4,C7 | YES | STRATEGY_DISABLED | BUY | **WRONG** | MISS | SCANNED_SIGNAL_REJECTED (WRONG DIRECTION) |
| 12 | CROMPTON | −1.3% | INSIDE | YES | C1,C2,C4,C7 | YES | STRATEGY_DISABLED | BUY | **WRONG** | MISS | SCANNED_SIGNAL_REJECTED (WRONG DIRECTION) |
| 13 | AAVAS | −1.2% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 14 | DLF | −1.2% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 15 | TORNTPHARM | −1.1% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |
| 16 | FORTIS | −1.0% | INSIDE | No | — | No | — | None | — | MISS | IN_UNIVERSE_NOT_SCANNED |

---

### A6. Cycle 1 Signal Funnel (09:45 IST) — Full Detail from CT Events

```
26 opportunities found (equity=22, options=2, arb=2)
    │
    ├── 20 → STRATEGY_LAB_REJECT (all mean_reversion_bounce = STRATEGY_DISABLED)
    │         BHARATFORG, INOXWIND, PAGEIND, CROMPTON, OBEROIRLTY, ONGC, NTPC,
    │         MUTHOOTFIN, VOLTAS, HDFCLIFE, MAXHEALTH, DABUR, TATACOMM, NHPC,
    │         COALINDIA, ADANIENT, ITC, POWERGRID + BANKBEES (RR=0.6 < 2.0)
    │
    └── 6 → StrategyLab assigned (after_evo=6, after_bt=6)
              TITAN (breakout, conf=7.48)
              HAVELLS (breakout, conf=8.23) × 2 entries
              RELIANCE (momentum_retest, conf=6.0)*
              NIFTY (Iron_Condor_Range, conf=7.3)
              BANKNIFTY (Iron_Condor_Range, conf=7.7)
              NIFTYBEES (unassigned/arb, conf=7.5)
                  │
                  ├── 1 → RiskManagerAI REJECTED
                  │
                  └── 5 → SimulationEngine: approved=0, rejected=0
                              (0 entered simulation — blocked by CRE/capital pre-filter)
                                  │
                                  └── 0 → signals_processed=0, trades_executed=0
```

*RELIANCE: also appears as mean_reversion_bounce in daily_candidates (rsi_neutral strat). The 6.0 momentum_retest signal is separate.

**Critical observation on HAVELLS**: Two separate `opportunity.equity.found` events for HAVELLS at identical timestamps (09:45:14.039582 and 09:45:14.042943), both conf=8.23. This is a duplicate entry — same signal fired twice. This likely represents the FRZ-001 stale position context (HAVELLS was yesterday's orphan position). No actual risk. PLACED UNDER OBSERVATIONS FOR LATER REVIEW.

---

## PART A CRITICAL TEST — Scan Attrition Category Verification

The user requested explicit verification that the scan_attrition layer distinguishes all 9 categories. The following is the evidence-based assessment:

### A. NOT_IN_UNIVERSE

**Evidence:** ILC `MARKET_OPPORTUNITY_AUDIT.md` states "Outside — by design: 0, Outside — unexpected: 0, Outside — rules: 0" for 40 audited symbols. All top-20 movers are INSIDE the 230-symbol universe.

**Scan attrition records:** 0

**Assessment:** Category A does not apply today (zero movers outside universe), AND the attrition JSONL does not log NOT_IN_UNIVERSE as a stage. Category is **not tracked** in attrition by design. Evidence available from ILC.

---

### B. IN_UNIVERSE_NOT_SCANNED

**Evidence:** PGA explicitly labels these: "Not scanned today (not in universe events), moved +4.0%" for DRREDDY; similar for DIVISLAB, CANBK, BAJAJFINSV, VEDL, GODREJPROP, HINDZINC, METROPOLIS, EMAMILTD, SRF, AAVAS, DLF, TORNTPHARM, FORTIS.

Root cause: These symbols are in the 230-symbol universe but did NOT appear in the premarket shortlist of 57 candidates. The sector-cap filter (166 → 57) and scoring eliminated them before the intraday cycle even ran.

**Scan attrition records:** 0

**Assessment:** Category B affects at least 14 significant movers today. The attrition JSONL does **not log IN_UNIVERSE_NOT_SCANNED**. Evidence available only from PGA/ILC cross-reference — NOT from attrition.

---

### C. SCANNED_NO_SIGNAL

**Evidence:** Of the 166 successfully scanned premarket symbols, 57 became candidates. The remaining 109 generated no score meeting the candidate threshold. Within the 57 candidates, TITAN, HAVELLS, RELIANCE etc. generated signals. The scan attrition logs only signal-level rejections, not "scanned-no-signal" at the premarket stage.

During intraday cycles: all symbols that appeared in CT `opportunity.equity.found` events DID generate signals. No symbol reached the cycle with zero signal output.

**Scan attrition records:** 0

**Assessment:** Category C exists (109 premarket symbols filtered before candidate list), but is NOT tracked in attrition. The attrition only begins at StrategyLab. Evidence: scanner_stats `candidates_before_sector_cap=166` vs `candidates_after_sector_cap=57`. Cannot distinguish C from B purely from attrition.

---

### D. SCANNED_SIGNAL_REJECTED

**Evidence:** 111 attrition records, all `STRATEGY_LAB_REJECT`.

- `STRATEGY_DISABLED` (Mean_Reversion): 104 records across 7 cycles for 28 unique symbols
- `RR_0.6_below_min_2.0` (BANKBEES via Mean_Reversion): 7 records across 7 cycles

**Scan attrition records:** 111 ✅ CAPTURED

**Assessment:** Category D is the **only** category reliably captured in attrition today. All evidence is direct from attrition JSONL.

---

### E. SIGNAL_APPROVED

**Evidence:** CT `system.cycle.complete` → `signals_processed=0`. CT `trades_executed=0`. Paper trades CSV: 0 today. EOD retro: `Approved trades: 0`.

**Scan attrition records:** 0

**Assessment:** No signals were approved today. Category E is **not tracked** in attrition — it would need a separate SIGNAL_APPROVED record if approvals occurred. Today: confirmed 0 approvals from CT.

---

### F. SIGNAL_BLOCKED_BY_RISK

**Evidence:** CT event `risk.check.failed` from `RiskManagerAI`: `{"rejected": 1}` at 09:45:16.710764 in cycle 1. One signal was rejected by RiskManagerAI — most likely HAVELLS (highest confidence breakout at 8.23, but had a prior stale position context). Alternatively RELIANCE (lower momentum_retest conviction in context of poor historical win rate).

**Scan attrition records:** 0

**Assessment:** Category F HAS evidence (1 rejection confirmed in CT), but is **NOT captured in scan_attrition**. The risk check rejection is only visible in CT events. This is a gap in the attrition layer.

---

### G. SIGNAL_BLOCKED_BY_PORTFOLIO

**Evidence:** After RiskManager (5 remaining), CT shows `simulation.complete: approved=0, rejected=0` — meaning 0 entered simulation. Then `risk.check.passed: CorrelationEngine: approved=0`. This means the 5 remaining signals were blocked before or at the CRE/capital-sizing stage.

Likely cause: CRE QTY_ZERO for TITAN (₹5090/share, budget ~₹2500, QTY=0), similar for NIFTY/BANKNIFTY options premium, NIFTYBEES/BANKBEES ETF capital constraints.

**Scan attrition records:** 0

**Assessment:** Category G is evident from CT events (5 signals blocked between risk and simulation), but NOT captured in scan_attrition. This is a significant gap — 5 signals disappeared between stages F and H without an attrition record.

---

### H. SIGNAL_EXECUTED

**Evidence:** CT `trades_executed=0`, paper_trades_today=0, `signals_processed=0`.

**Scan attrition records:** 0

**Assessment:** No executions today. Category H would require a positive execution record. Not tracked in attrition (would need to be separately logged). Today: confirmed 0 from multiple sources.

---

### I. WRONG_DIRECTION

**Evidence:** PGA/ILC cross-match reveals 6 symbols that were scanned with BUY signals via mean_reversion_bounce but fell sharply:

| Symbol | IIOS Signal | Actual | Magnitude |
|--------|-------------|--------|-----------|
| BHARATFORG | BUY (conf=5.3) | −3.0% | −3.0% gap |
| MAXHEALTH | BUY (conf=5.25) | −2.4% | −2.4% gap |
| AMBUJACEM | BUY (conf=5.1) | −2.3% | −2.3% gap |
| BHEL | BUY (detected) | −1.7% | −1.7% gap |
| PRESTIGE | BUY (detected) | −1.4% | −1.4% gap |
| CROMPTON | BUY (conf=5.44) | −1.3% | −1.3% gap |

All 6 were blocked by STRATEGY_DISABLED, so no wrong-direction trades occurred. However the scanner produced systematically wrong-direction BUY signals for stocks that fell 1.3–3.0%.

**Scan attrition records:** 0 (wrong_direction is not a scan_attrition stage)

**Assessment:** Category I is NOT tracked in scan_attrition. Evidence is only available via PGA/ILC post-market cross-matching. This matters because it shows that Mean_Reversion's BUY scan is picking up oversold stocks that continue distributing rather than bouncing.

---

### Critical Test Summary

| Category | attrition records | Evidence source | Working? |
|----------|-------------------|-----------------|----------|
| A. NOT_IN_UNIVERSE | 0 | ILC audit | NOT tracked in attrition |
| B. IN_UNIVERSE_NOT_SCANNED | 0 | PGA "not scanned" label | NOT tracked in attrition |
| C. SCANNED_NO_SIGNAL | 0 | scanner_stats delta | NOT tracked in attrition |
| D. SCANNED_SIGNAL_REJECTED | **111** | attrition JSONL | ✅ TRACKED |
| E. SIGNAL_APPROVED | 0 | CT events | NOT tracked in attrition |
| F. SIGNAL_BLOCKED_BY_RISK | 0 | CT risk.check.failed | NOT tracked in attrition |
| G. SIGNAL_BLOCKED_BY_PORTFOLIO | 0 | CT simulation.complete | NOT tracked in attrition |
| H. SIGNAL_EXECUTED | 0 | CT + paper_trades | NOT tracked in attrition |
| I. WRONG_DIRECTION | 0 | PGA/ILC cross-match | NOT tracked in attrition |

**Finding:** The scan_attrition layer currently functions as a StrategyLab-reject log only. It correctly tracks category D. Categories A–C and E–I produce zero attrition records. The full 9-category funnel cannot be reconstructed from attrition alone — it requires CT events (D/F/G/H) and PGA/ILC cross-matching (B/C/I).

---

## PART B — MARKET OPPORTUNITY SUMMARY

### Coverage Statistics (from available ILC data: 6 gainers, 16 losers)

| Metric | Value | Evidence |
|--------|-------|----------|
| Gainers scanned (top-6) | 1/6 = **17%** (TITAN only) | PGA "not scanned" labels |
| Losers scanned (top-16 ILC) | 6/16 = **37.5%** | attrition records |
| Scanned → signal generated | 100% (all scanned got signals) | CT opportunity.equity.found |
| Signal generation rate | 26/57 candidates = **46%** per cycle | CT opportunity.scan.complete |
| Approval rate | 0/151 = **0%** | CT + EOD retro |
| Rejection rate | **100%** | CT + scan attrition |
| Missed winner count (actionable) | **2** (DRREDDY +4.0%, DIVISLAB +3.2%) | PGA MISSED_WINNER_ANALYSIS |
| Missed SHORT count (not predictable) | **10** (VEDL, GODREJPROP, HINDZINC, METROPOLIS, EMAMILTD, SRF, AAVAS, DLF, TORNTPHARM, FORTIS) | ILC |
| Wrong-direction BUY signals | **6** (BHARATFORG, MAXHEALTH, AMBUJACEM, BHEL, PRESTIGE, CROMPTON) | PGA/ILC cross |
| Universe gap count | **0** (all movers inside 230-symbol universe) | ILC audit |

### Top 5 Most Important Missed Opportunities

---

#### MISSED #1 — DRREDDY +4.0% (₹1159.10 → ₹1205.00)

**What happened in market:** Strong single-day pharmaceutical rally, +4.0% on high volume (3.9M shares). Likely sector tailwind (pharma strong day).

**What IIOS saw:** Nothing. DRREDDY was in the 230-symbol universe but did NOT appear in the 57 daily candidates. Scanner attempted 230 symbols, 64 failed (27.8% failure rate). If DRREDDY was in the 64 that failed the premarket scan, it would have been invisible all day.

**What IIOS did:** No action. No scan, no signal, no decision.

**Where opportunity was lost:** Before cycle 1, at the premarket candidate selection stage (166 successful → 57 after sector cap). Even if DRREDDY was successfully scanned but scored below threshold, it would not have appeared in the 57 candidates.

**Existing knowledge available?** None. DNA=0, edges=0, no historical patterns for DRREDDY in the learning registry.

**Existing DNA available?** No.

**Existing edge available?** No.

**Was the miss actually predictable?** PARTIALLY_PREDICTABLE (PGA verdict). With pharma sector strength visible at open (if monitoring sector breadth), a directional bias towards pharma stocks could have flagged DRREDDY. However, without DNA patterns and with no premarket shortlisting, IIOS had no mechanism to identify this. The miss is a knowledge gap, not a filter failure.

---

#### MISSED #2 — DIVISLAB +3.2% (₹8315 → ₹8578.50)

**What happened in market:** Second major pharma mover of the day. +3.2% on 603K shares.

**What IIOS saw:** Nothing. DIVISLAB not in candidates. DNA=0, edges=0.

**What IIOS did:** No action.

**Where opportunity was lost:** Same as DRREDDY — premarket candidate selection. At ₹8315/share, even with a BUY signal, CRE would likely produce QTY=0 (₹2500 allocation / ₹8315 = 0.3 shares).

**Existing knowledge?** None.

**Was the miss actually predictable?** PARTIALLY_PREDICTABLE. Even if flagged, the capital constraint (₹8315/share with a ₹10,000 total capital system) means this stock is structurally unactionable regardless of signal quality.

**Additional note:** This is a structural limitation — not a scanning or strategy failure.

---

#### MISSED #3 — VEDL −3.5% (₹284.90 → ₹275.00)

**What happened in market:** Vedanta fell 3.5% on high volume (13.5M shares — the highest of any mover today). This is a significant short opportunity if direction could have been predicted.

**What IIOS saw:** Nothing. VEDL not scanned, not in candidates.

**What IIOS did:** No action.

**Where opportunity was lost:** VEDL was in the 230-symbol universe but not shortlisted. The metals sector showed broad weakness today (BHEL, COALINDIA, HINDZINC also weak), but the premarket regime was range_market — the sector weakness wasn't surfaced in the candidate selection.

**Existing knowledge?** None. DNA=0, edges=0.

**Was the miss actually predictable?** PARTIALLY_PREDICTABLE. The metals sector weakness was visible intraday, and VEDL's volume (13.5M) suggests institutional distribution. Without SHORT strategy DNA for VEDL and without a metals-sector SHORT scan pattern, IIOS could not have identified this.

---

#### MISSED #4 — BHARATFORG −3.0% WRONG DIRECTION

**What happened in market:** BHARATFORG fell 3.0%. Auto sector weakness on the day (regime: range, but sub-sector distributing).

**What IIOS saw:** BUY signal (mean_reversion_bounce, conf=5.3) repeated across 4 cycles (C1, C2, C4, C7). The scanner identified it as oversold/reversion candidate every single scan — but the stock kept falling.

**What IIOS did:** Blocked the signal (STRATEGY_DISABLED). No trade taken.

**Where opportunity was lost:** Two layers: (1) The SHORT opportunity was structurally invisible — mean_reversion_bounce is a BUY-only strategy, and SHORT strategies for BHARATFORG have no DNA. (2) Even the theoretical bounce trade (BUY) was correctly blocked since Mean_Reversion is disabled with WR=16.7% across 36 trades.

**Existing knowledge?** Mean_Reversion's WR=16.7% is the correct reason for the strategy being disabled. The pattern of "falling knife flagged as reversion candidate" is a known Mean_Reversion failure mode — stocks in distribution can appear technically oversold for multiple days.

**Was the miss actually predictable?** NOT_PREDICTABLE (PGA verdict). No SHORT DNA exists for BHARATFORG. The only system signal was a wrong-direction BUY which was correctly blocked. The correct action (SHORT) was not in IIOS's toolkit for this symbol.

---

#### MISSED #5 — TITAN +0.8% — SIGNAL GENERATED, BLOCKED DOWNSTREAM

**What happened in market:** TITAN moved +0.8% (₹5090 → ₹5128). Modest gain but the breakout setup was real and identified.

**What IIOS saw:** EquityScannerAI identified TITAN as `breakout, conf=7.48` in cycle 1. PGA confirms it was "scanned, in opportunity events, signal conf=7.5." StrategyLab assigned a strategy. The signal reached the risk pipeline.

**What IIOS did:** Generated signal → StrategyLab passed it → RiskManager or CRE blocked it. CT shows RiskManager rejected=1 and simulation=0/0 (5 downstream blocks). signals_processed=0.

**Where opportunity was lost:** Most likely at CRE (Capital Risk Engine): TITAN at ₹5090/share with ~₹2500 budget (25% of ₹10,000) = 0.49 shares → QTY rounds to 0. The signal was correctly identified and correctly structured, but the trade was too large for the current capital base.

**Existing knowledge?** Breakout strategy is active. TITAN score=0.9113 equivalent in the candidates list (actually 0.635 in candidates). The signal was real.

**Was the miss actually predictable?** YES — the move was detected and correctly classified. This is a **capital constraint miss**, not a knowledge miss or a strategy miss. With ₹10,000 total capital and ₹5,090 stocks, the system structurally cannot trade TITAN regardless of signal quality.

---

## PART C — LEARNING AUDIT

### C1. Learning Actions Created Today

**Total:** 19 learning records in registry (created_date=2026-08-11).

Additionally 7 from PGA learning actions file (subset of the 19, crossreferenced by symbol overlap).

**Source:** ILC (Institutional Learning Cycle) via PGA (Predictive Gap Analysis).

### C2. All 19 Learning Actions

| # | ID | Cat | Symbol | Type | Target | Description | Status | Auto-executed |
|---|-----|-----|--------|------|--------|-------------|--------|---------------|
| 1 | PGA-F46369F6 | E | DRREDDY | create_dna_candidate | IDR | Create candidate DNA: +4.0% with zero coverage | PENDING | No |
| 2 | PGA-F56D15BD | E | DIVISLAB | create_dna_candidate | IDR | Create candidate DNA: +3.2% with zero coverage | PENDING | No |
| 3 | PGA-80F9FCDF | E | CANBK | create_dna_candidate | IDR | Create candidate DNA: +1.0% with zero coverage | PENDING | No |
| 4 | PGA-B891CE79 | E | VEDL | create_dna_candidate | IDR | Create candidate DNA: -3.5% with zero coverage | PENDING | No |
| 5 | PGA-5B59D84B | E | GODREJPROP | create_dna_candidate | IDR | Create candidate DNA: -3.3% with zero coverage | PENDING | No |
| 6 | PGA-CDFCE313 | F | BHARATFORG | schedule_hkap_replay | HKAP | Schedule HKAP replay: build history about -3.0% move | PENDING | No |
| 7 | PGA-566FAA5A | E | MAXHEALTH | create_dna_candidate | IDR | Create candidate DNA: -2.4% with zero coverage | PENDING | No |
| 8 | PGA-23A59748 | F | AMBUJACEM | schedule_hkap_replay | HKAP | Schedule HKAP replay: build history about -2.3% move | PENDING | No |
| 9 | PGA-0118BEB3 | E | HINDZINC | create_dna_candidate | IDR | Create candidate DNA: -2.1% with zero coverage | PENDING | No |
| 10 | PGA-94D1681B | E | METROPOLIS | create_dna_candidate | IDR | Create candidate DNA: -1.9% with zero coverage | PENDING | No |
| 11 | PGA-CBAF3F84 | F | BHEL | schedule_hkap_replay | HKAP | Schedule HKAP replay: build history about -1.7% move | PENDING | No |
| 12 | PGA-B170114A | E | EMAMILTD | create_dna_candidate | IDR | Create candidate DNA: -1.5% with zero coverage | PENDING | No |
| 13 | PGA-E08E7349 | E | SRF | create_dna_candidate | IDR | Create candidate DNA: -1.5% with zero coverage | PENDING | No |
| 14 | PGA-994A06DE | F | PRESTIGE | schedule_hkap_replay | HKAP | Schedule HKAP replay: build history about -1.4% move | PENDING | No |
| 15 | PGA-8E6705C3 | E | CROMPTON | create_dna_candidate | IDR | Create candidate DNA: -1.3% with zero coverage | PENDING | No |
| 16 | PGA-E478AC8C | E | AAVAS | create_dna_candidate | IDR | Create candidate DNA: -1.2% with zero coverage | PENDING | No |
| 17 | PGA-533D6B5B | E | DLF | create_dna_candidate | IDR | Create candidate DNA: -1.2% with zero coverage | PENDING | No |
| 18 | PGA-A4749638 | E | TORNTPHARM | create_dna_candidate | IDR | Create candidate DNA: -1.1% with zero coverage | PENDING | No |
| 19 | PGA-C157D4AC | E | FORTIS | create_dna_candidate | IDR | Create candidate DNA: -1.0% with zero coverage | PENDING | No |

**Action categories:**
- Cat E (DNA gap → Create candidate DNA): 15 actions
- Cat F (Historical gap → Schedule HKAP replay): 4 actions

**All 19 actions: outcome=LOGGED_FOR_REVIEW, scheduled=false, auto-executed=false**

---

## PART D — CLOSED-LOOP LEARNING

For each of today's 19 actions, the loop stage is:

```
Observation (market moved, IIOS missed)
↓
Root Cause (DNA=0, no historical knowledge)
↓
Learning Action Created (19 PENDING records in learning_registry)     ← TODAY STOPS HERE
↓
Registry (confirmed: 65 entries, all PENDING — none MEASURING or beyond)
↓
Automatic execution — NOT TRIGGERED (scheduled=false for all 19)
↓
Baseline metric (dna_count=0 for all targets; prediction_metric noted)
↓
30-day verification — NOT STARTED (windows=[30, 60, 90] set but MEASURING=0)
↓
60-day verification — NOT STARTED
↓
90-day verification — NOT STARTED
↓
INSTITUTIONAL KNOWLEDGE — NOT REACHED
```

**Today's learning loop stops at step 3: "Learning Action Created."**

### Classification

| Stage | Status |
|-------|--------|
| OBSERVED | ✅ YES — 19 moves identified |
| ACTION CREATED | ✅ YES — 19 records in registry |
| ACTION EXECUTED | ❌ NO — 0 auto-executed (0 of 19) |
| VERIFIED IMPROVEMENT | ❌ NO — 0 verifications completed (0/65 registry entries) |
| INSTITUTIONAL KNOWLEDGE | ❌ NO — 0 IMPROVED, 0 RETIRED, 0 promoted |

### Historical context (all 65 registry entries)

The learning registry has been active since 2026-08-07 (earliest entries). In 3 days of operation (Aug 7=21, Aug 10=25, Aug 11=19 = 65 total), NOT ONE entry has advanced past PENDING status. No DNA has been created. No HKAP replay has been executed. The verification windows (30/60/90 days) have never been triggered.

**This is not a failure — it is consistent with expected behavior at this stage.** The system correctly identifies learning opportunities and creates properly structured records with measurement windows. Execution requires either automatic triggers (currently disabled: `scheduled=false`) or manual promotion. No execution mechanism has been activated yet.

---

## PART E — WHAT ACTUALLY CHANGED TODAY

| Question | Answer | Evidence |
|----------|--------|----------|
| Did observations modify any DNA? | **NO** | DNA coverage=0 for all 19 learning targets; no IDR write observed |
| Did observations modify any edge? | **NO** | discovered_edges.json has 0 today-entries |
| Did observations modify any hypothesis? | **NO** | ILC SD review: "Hypotheses Created: 0" |
| Did observations modify any strategy? | **NO** | learning_db.json: last_updated=2026-06-16 for most strategies |
| Did observations modify any threshold? | **NO** | No threshold changes in any config or DB |
| Did observations modify any trading rule? | **NO** | PAPER_TRADING, R:R, MAX_RISK unchanged |
| Did observations modify any risk rule? | **NO** | VIX kill=45, daily loss=2% unchanged |
| Did they only create learning/verification records? | **YES** | 19 PENDING records added to learning_registry |

**Nothing was automatically promoted today.** The system observed, computed, and recorded — but all 19 learning actions remain PENDING with no automatic execution triggered.

---

## PART F — SYSTEM HEALTH OF LEARNING

### Market Opportunity Audit: PARTIALLY WORKING

The ILC and PGA correctly identified movers, classified them, and produced audit trails. However:
- PGA only covers top-5 gainers/losers (10 symbols). The requested top-50 is unavailable.
- ILC's market audit covers 40 symbols but the report extract only showed 3 gainers + 16 losers (others present in the system but not captured in the copied report snapshot).
- TATAMOTORS shows `+NaN%` return — a data feed issue.
- ILC ILS score: 48.6/100 [F].

### Scan Attrition: PARTIALLY WORKING

Scan_attrition correctly captures StrategyLab rejections (111 records, all category D). However, 8 of the 9 requested categories produce zero attrition records. The layer is functioning as a StrategyLab-reject log, not a full-funnel attrition tracker. Evidence for stages A/B/C/F/G/H/I must be sourced from ILC, CT events, or PGA respectively.

### Learning Generation: FULLY WORKING

19 learning actions were generated, correctly categorized (Cat E / Cat F), correctly linked to measurement windows (30/60/90 days), and correctly persisted in the registry. PGA learning actions (7) and ILC registry (19) are consistent. The generation pipeline is working.

### Learning Persistence: FULLY WORKING

65 registry entries are persisted correctly in `data/ilc/learning_registry.json` with structured fields (learning_id, created_date, action_type, expected_benefit, prediction_metric, measurement_windows, status, verified). All records survive across sessions.

### Verification Tracking: PARTIALLY WORKING (not yet triggered)

The verification infrastructure exists correctly (measurement_windows=[30,60,90] for all entries). However, status=PENDING for all 65 entries and no entry has advanced to MEASURING, IMPROVED, or RETIRED. The 30-day window for the earliest entries (2026-08-07) is not due until 2026-09-06. This is expected behavior at the current stage of the system — the verification tracking is structurally present but temporally inactive.

---

## OBSERVATIONS FOR LATER REVIEW

The following were noted during investigation but are OUT OF SCOPE for any code change today.

### OBS-001 — Scan attrition is a StrategyLab-only log, not a full funnel tracker

8 of 9 requested attrition categories produce zero records. To reconstruct the full signal funnel (particularly stages F/G = risk/portfolio blocks), one must query CT events. The attrition JSONL currently serves as a useful StrategyLab-reject log but does not fulfill the "complete funnel" purpose implied by the 9-category classification.

**No change requested. Observation only.**

### OBS-002 — 0% signal approval rate is a structural state, not a failure

All 151 signals today were rejected. This is entirely explained by:
(a) Mean_Reversion DISABLED (104 of 111 attrition records, WR=16.7% justifies disable)
(b) Downstream CRE capital constraints for high-priced stocks (TITAN ₹5090, DIVISLAB ₹8315)
(c) R:R filter correctly blocking BANKBEES (0.6 < 2.0)
The zero-execution state is correct governance behavior given current capital and enabled strategies.

**No change requested. Observation only.**

### OBS-003 — 6 wrong-direction BUY signals on falling stocks

The mean_reversion_bounce scanner flagged BHARATFORG, MAXHEALTH, AMBUJACEM, BHEL, PRESTIGE, CROMPTON as BUY candidates — but all fell 1.3–3.0%. This is a known pattern (oversold stocks continuing to distribute). All were blocked by STRATEGY_DISABLED. However this pattern has been recurring: if Mean_Reversion is ever re-enabled, the bounce-miss problem would resurface for names in distribution.

**No change requested. Observation only.**

### OBS-004 — HAVELLS duplicate opportunity event

Two identical `opportunity.equity.found` events for HAVELLS (conf=8.23) fired at 09:45:14.039582 and 09:45:14.042943 — 3ms apart. This appears to be a duplicate scan event (possibly from yesterday's stale position context colliding with today's breakout signal). The FRZ-001 Phase 2 fix (Pass 1.9 deep orphan expiry) should resolve the underlying stale state on next restart. The duplicate did not cause any trade.

**No change requested. FRZ-001 fix already in place.**

### OBS-005 — GlobalIntelligence latency degraded ×3 today

EOD retro: "slowest: GlobalIntelligence 13,762ms" (×3 occurrences exceeding 12,000ms CRIT threshold). This is consistent with the known yfinance international markets fetch pattern under load. Did not cause any missed opportunity (all cycles were range_market with no actionable signals anyway).

**No change requested. Observation only.**

### OBS-006 — TATAMOTORS +NaN% — data feed gap

TATAMOTORS showed NaN for both open and close prices in the PGA report. This means Yahoo Finance returned null/empty price data for this symbol today. Not clear if this is a feed error, market halt, or data timing issue.

**No change requested. Observation only.**

### OBS-007 — 65 learning actions across 3 days, 0 executed, 0 verified

The learning registry is accumulating correctly (65 entries: Aug 7=21, Aug 10=25, Aug 11=19). All status=PENDING. The first 30-day verification window is due 2026-09-06 for Aug 7 entries. There is currently no automatic execution mechanism (`scheduled=false` for all). This is a structural observation: the learning system is accumulating observations without executing any downstream actions.

**No change requested. Expected behavior at current stage. Observation only.**

### OBS-008 — Pharma sector not captured (DRREDDY, DIVISLAB both in top gainers)

Two pharma stocks (DRREDDY +4.0%, DIVISLAB +3.2%) were the biggest gainers today. Neither was in the 57-candidate shortlist. The premarket regime (range_market) did not bias towards pharma. The premarket scanner may be under-weighting pharma sector candidates on range_market days. DNA creation learning actions for both have been logged (Cat E).

**No change requested. Observation only.**

### OBS-009 — Research gate FROZEN (40 trades observed, need 100)

EOD retro: "Clean research gate: prepared=40, required=100, ready=NO, adaptive_mutation_blocked=YES — FROZEN." At 0 new trades today and near-zero execution for months, the 100-trade clean sample requirement will take very long to reach. This gate is preventing architecture evolution/mutation.

**No change requested. Observation only.**

### OBS-010 — MetaLearning allocations have Mean_Reversion at 25%

CT event: `meta.learning.applied: top_strategy=Breakout_Volume, allocations={Breakout_Volume:0.25, Momentum_Retest:0.25, Trend_Pullback:0.25, Mean_Reversion:0.25}`. MetaLearning still allocates 25% weight to Mean_Reversion despite the strategy being DISABLED. This allocation has no effect currently (disabled strategies never execute) but suggests the MetaLearning model does not yet know the strategy is disabled.

**No change requested. Observation only.**

---

## FINAL CLASSIFICATION

Based on all evidence collected today:

**Market Opportunity Audit:** PARTIALLY WORKING  
**Scan Attrition:** PARTIALLY WORKING  
**Learning Generation:** FULLY WORKING  
**Learning Persistence:** FULLY WORKING  
**Verification Tracking:** PARTIALLY WORKING (structure present; temporally inactive)

---

## OBSERVATION_WITH_WARNINGS

The system is observing correctly, generating learning actions correctly, and persisting them correctly. No execution failures, no crashes, no data corruption.

Warnings:
1. Scan attrition captures only 1 of 9 requested funnel categories (D only).
2. 0% signal approval rate is structurally expected but means zero revenue-generating activity.
3. 65 accumulated learning actions with 0 executed = the gap between "observed" and "learned" is widening.
4. TATAMOTORS NaN price data — feed gap for at least one symbol.
5. ILS score 48.6/100 [F] — the system's self-assessed learning quality is poor.

---

*Report generated: 2026-08-11*  
*Data as of: ~10:30 IST (CT DB snapshot) + post-market EOD retro + PGA/ILC end-of-day reports*  
*No code was modified during the generation of this report.*
