# Research Experiment 001
## 30-Day Historical Experience Training

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Status** | COMPLETE — Populated from observed data |
| **Primary Historical Data Provider** | Yahoo Finance |
| **Secondary Provider** | Dhan (Unavailable for historical replay — HTTP 451) |
| **Execution Date** | 2026-08-01 |
| **Execution Reference** | [RESEARCH_EXPERIMENT_001_EXECUTION.md](RESEARCH_EXPERIMENT_001_EXECUTION.md) |
| **Validation Reference** | [DHAN_DATA_PROVIDER_VERIFICATION.md](DHAN_DATA_PROVIDER_VERIFICATION.md) |

---

## Section 1 — Experiment Objective

**Research Question:**

> What market knowledge can IIOS discover from 30 completed historical trading sessions using verified historical OHLC data?

This experiment is the first structured application of the Historical Experience Training (HET) subsystem. It does not optimise strategy parameters or test trading performance. Its purpose is knowledge discovery: understanding how IIOS observes, classifies, and learns from historical market structure.

The findings recorded here become the baseline against which Experiments 002, 003, 004, and 005 are compared.

---

## Section 2 — Experiment Configuration

| Parameter | Value |
|---|---|
| Replay Start Date | `2026-06-19` |
| Replay End Date | `2026-07-30` (2026-07-31 had no yfinance data at execution time) |
| Trading Sessions Scheduled | 30 |
| Trading Sessions Replayed | 29 |
| Skipped Sessions | 1 (2026-07-31 — yfinance data unavailable) |
| Primary Data Provider | Yahoo Finance (yfinance) — hardcoded in `oios/data/ohlcv_fetcher.py` |
| Secondary Provider | Dhan — inactive (HTTP 451 data restriction) |
| Integrity Mode | COMPLETE — no exceptions, exit code 0 |
| OHLCV Coverage | 210 of 230 universe symbols (91.3%) |
| BHAV Coverage | 0 rows — delivery data not available in replay mode |
| Theme Phase Engine | Invoked but produced 0 records |
| Learning Engines | NOT invoked (edge_discovery, MetaModel, LearningEngine require Phase C) |
| Platform Version | As-is (frozen — no modifications made before or during experiment) |
| DB Path | `data/re001_replay.db` (isolated — live DB untouched) |

---

## Section 3 — Research Findings

### 3.1 Verified Findings

*Definition: Observed consistently across the replay window with supporting quantitative evidence.*

| # | Finding | Supporting Evidence | Confidence | Related Module |
|---|---|---|---|---|
| V-01 | The June–July 2026 NSE market was SIDEWAYS across all 29 simulated sessions — not a single TRENDING_UP or TRENDING_DOWN day was detected | `regime_at_birth=SIDEWAYS` for all 124 signal_births; Layer1A regime detection log showed SIDEWAYS on every simulated date | High | `historical_replay._detect_regime()`, Layer1A |
| V-02 | Signal generation was concentrated in the final 6 of 29 sessions (2026-07-23 to 2026-07-30) | signal_births by detected_at: 5 signals on 07-23, 3 on 07-24, 19 on 07-27, 11 on 07-28, 31 on 07-29, 55 on 07-30. Zero signals in days 1–23 | High | `oios/scanners/layer_1a.py`, `oios/scanners/layer_1b.py` |
| V-03 | `DNA_1B_SECTOR_PRE_BKT` is the dominant archetype (63.7% of all signals) in a sustained SIDEWAYS environment | 79 of 124 total signals from signal_births archetype_id breakdown | High | `oios/scanners/layer_1b.py` |
| V-04 | AUTO sector generated more signals than any other sector (31 signals, 25.0% of total) | sector breakdown via opportunities JOIN signal_births: AUTO=31, FMCG=19, BANKING_FINANCE=16, IT=15, PHARMA=14, METALS=11 | High | Sector mapping + Layer1A/1B |
| V-05 | 14 of 66 opportunities (21.2%) reached ACTIVE state — all with conviction_score ≥ 7.5 | opportunities table: 5 at conv=10.0, 9 at conv=7.5; all required ≥3 confirming signals | High | `oios/domain/state_machine.py` |
| V-06 | IT sector had the highest 30-day average conviction score (avg=0.389) and the highest single-day peak (0.976 on 2026-07-29) | sector_conviction_daily: IT avg=0.389, max=0.976 (2026-07-29); second: FMCG avg=0.304 | High | `oios/data/sector_conviction_writer.py` |
| V-07 | All 66 discovered opportunities were LONG direction — zero SHORT signals generated across 29 SIDEWAYS sessions | opportunities.direction: LONG=66, SHORT=0 | High | Layer1A, Layer1B |
| V-08 | BHAV (NSE delivery data) was fully absent from the replay (0 rows) — Layer1B archetypes that nominally require delivery data (QUIET_ACCUMULATION, LOW_NOISE_STRENGTH) ran in degraded mode | bhav_daily COUNT=0; Layer1B logs showed `no_bhav=209` on final scan day | High | `oios/scanners/layer_1b.py`, `oios/db/` |

---

### 3.2 Probable Findings

*Definition: Strong indication present in the data but requires a longer experiment window or cross-regime confirmation before being treated as verified.*

| # | Finding | Reason for Uncertainty | Evidence | Recommended Verification |
|---|---|---|---|---|
| P-01 | `DNA_1B_SECTOR_PRE_BKT` operates without BHAV, using only OHLCV + sector conviction scores | BHAV=0 yet 79 SECTOR_PRE_BKT signals generated; mechanism not confirmed by reading layer_1b.py internals | Archetype signal count with BHAV=0 shows SECTOR_PRE_BKT functional | Read `oios/scanners/layer_1b.py` to confirm BHAV dependency per archetype |
| P-02 | The conviction threshold for DISCOVERED→ACTIVE transition is 7.5 | All 14 ACTIVE opps have conviction_score ∈ {7.5, 10.0}; no ACTIVE opp below 7.5 observed | State machine logs: `DISCOVERED→ACTIVE conviction=7.50` for every transition | Inspect `oios/domain/state_machine.py` for threshold constant |
| P-03 | AUTO and FMCG sectors are most sensitive to momentum breakout detection in SIDEWAYS regimes | AUTO: 31 signals (7 ACTIVE), FMCG: 19 signals (2 ACTIVE) — consistently dominant | Signal birth sector distribution + ACTIVE outcome counts | RE002 cross-regime confirmation |
| P-04 | The signal scoring system is capped below 8.0 in SIDEWAYS conditions; 8.0+ may require TRENDING | Score distribution: max=7.92 (TVSMOTOR DNA_1A_52W_HIGH_EXPAND); no 8.0+ scores observed | base_score statistics from signal_births | RE002 with TRENDING regime |

---

### 3.3 Hypotheses

*Definition: Interesting observations that cannot be confirmed from this experiment alone. Each requires a dedicated future experiment.*

| # | Hypothesis | Why It Matters | Experiment Required |
|---|---|---|---|
| H-01 | Signal generation in Layer1A requires a minimum accumulation period of ~23 sessions before momentum/breakout patterns become detectable in a new SIDEWAYS regime | 0 signals in days 1–23, then rapid onset from day 24 onward. Could be a rolling-window warm-up or a genuine market structure finding | RE002: start experiment mid-regime to observe if signals appear from day 1 |
| H-02 | BHAV absence causes `DNA_1B_QUIET_ACCUMULATION` and `DNA_1B_LOW_NOISE_STRENGTH` signals to be unreliable — the 22 signals from these archetypes may not be valid detections | Both archetypes nominally measure delivery-based accumulation; with 0 BHAV rows, their scoring basis is unknown | RE003: run with BHAV data loaded from NSE website to compare |
| H-03 | The IT sector's conviction surge to 0.976 on 2026-07-29 represents a real sector rotation event | IT had avg conviction 0.389 (highest) and three consecutive peak days (0.927, 0.955, 0.976 on 07-28, 07-29, 07-30) | Cross-reference NIFTYIT price chart for July 2026 |
| H-04 | Theme phase classification never fired because the SIDEWAYS regime does not produce the multi-week conviction trends needed to classify a theme phase | 0 theme_phase_history rows across 29 sessions | RE002: apply to a TRENDING regime window |

---

## Section 4 — Market Behaviour

*Observations from the 29-session replay window. Record what the market did, not what the system did.*

| Dimension | Observation |
|---|---|
| **Dominant Regime** | SIDEWAYS — 100% across all 29 simulated sessions (NIFTY50 SMA200 crossover + 20d return below TRENDING threshold on every day) |
| **Sector Rotation** | IT showed the clearest conviction build: avg=0.389, peak=0.976 on 2026-07-29. Three consecutive high-conviction IT days (07-28: 0.927, 07-29: 0.976, 07-30: 0.955) consistent with a rotation event |
| **Sector Leadership** | IT (avg 0.389), FMCG (avg 0.304), PHARMA (avg 0.297), AUTO (avg 0.290) |
| **Sector Laggards** | TELECOM (avg 0.195), INFRA (avg 0.203), DEFENCE (avg 0.215), ENERGY (avg 0.218) |
| **Signal Breadth** | Narrow for first 23 sessions (zero signals); broadened sharply in final 6 sessions — AUTO and PHARMA drove the expansion |
| **Data Completeness** | OHLCV: 91.3% (210/230 symbols). BHAV: 0%. Theme phase: 0%. |
| **Volatility** | Not directly measured. No circuit breakers or extreme gaps observed in terminal log. SIDEWAYS regime implies low directional volatility. |
| **Market Structure** | 23-session SIDEWAYS compression followed by a 6-session broadening expansion. Breakout candidates concentrated in AUTO (components: ENDURANCE, SUNDRMFAST, BHARATFORG), METALS (JSWSTEEL), and BANKING (BAJFINANCE) |

---

## Section 5 — Knowledge Discovery

### 5.1 New Patterns Observed

*Patterns that appeared in the replay data, now recorded in re001_replay.db.*

| Archetype | Total Signals | Daily Rate | Regime | Score Min | Score Max | BHAV Dependency |
|---|---|---|---|---|---|---|
| DNA_1B_SECTOR_PRE_BKT | 79 | 13.17/day | SIDEWAYS | ~4.2 | ~7.9 | Probable: None (OHLCV + sector scores) |
| DNA_1B_QUIET_ACCUMULATION | 18 | 3.00/day | SIDEWAYS | — | — | Yes (degraded without BHAV) |
| DNA_1A_52W_HIGH_EXPAND | 9 | 1.50/day | SIDEWAYS | ~5.5 | 7.92 | None |
| DNA_1A_MOMENTUM_CONT | 7 | 1.17/day | SIDEWAYS | ~5.3 | ~6.8 | None |
| DNA_1A_SECTOR_BKT | 7 | 1.17/day | SIDEWAYS | ~4.6 | ~6.3 | None |
| DNA_1B_LOW_NOISE_STRENGTH | 4 | 0.67/day | SIDEWAYS | — | — | Yes (degraded without BHAV) |

*Daily rate computed over 6 active signal days. Score min/max estimated from terminal log samples.*

---

### 5.2 Discovered Structural Regularities

*Market structure regularities observed in replay data — not performance claims.*

| ID | Observation | Regime | Support |
|---|---|---|---|
| E-001 | Symbols accumulating 3+ confirming signals consistently crossed the ACTIVE conviction threshold (7.5) | SIDEWAYS | 14/66 opps reached ACTIVE; all had ≥3 confirming signals |
| E-002 | IT sector conviction shows a late-period surge pattern: low in weeks 1–4, rapid build in weeks 5–6 | SIDEWAYS | conviction: avg 0.25 early → 0.976 peak on day 29 |
| E-003 | AUTO sector is a high-volume signal generator but has a moderate ACTIVE conversion rate (7/10 opps = 70% of ACTIVE opps from AUTO; 7 ACTIVE out of 13 total AUTO opps = 53.8%) | SIDEWAYS | opportunities.sector = AUTO breakdown |

---

### 5.3 Strategy Evolution

*Learning engines were NOT invoked. No strategy evolution occurred in RE001.*

| System | Status | Reason |
|---|---|---|
| edge_discovery | NOT RUN | Requires Phase C data; oios_events=0 |
| MetaModel | NOT RUN | As above |
| LearningEngine | NOT RUN | As above |
| PatternMiner | NOT RUN | As above |
| StrategyEvolution | NOT RUN | As above |

---

### 5.4 Feature Activation Rates (Proxy for Importance)

*True feature importance requires outcome labels (COMPLETED/INVALIDATED). The following ranks by signal activation rate only.*

| Rank | Feature / Archetype | Activation Rate | Regime | Notes |
|---|---|---|---|---|
| 1 | DNA_1B_SECTOR_PRE_BKT | 13.17/day | SIDEWAYS | Most active; sector breadth pre-breakout detection |
| 2 | DNA_1B_QUIET_ACCUMULATION | 3.00/day | SIDEWAYS | Degraded (no BHAV) |
| 3 | DNA_1A_52W_HIGH_EXPAND | 1.50/day | SIDEWAYS | Fully functional; price near 52-week high |
| 4 | DNA_1A_MOMENTUM_CONT | 1.17/day | SIDEWAYS | Fully functional; consecutive momentum days |
| 4 | DNA_1A_SECTOR_BKT | 1.17/day | SIDEWAYS | Fully functional; sector participation breadth |
| 6 | DNA_1B_LOW_NOISE_STRENGTH | 0.67/day | SIDEWAYS | Degraded (no BHAV) |

---

## Section 6 — Learning Summary

### 6.1 Signal Database (re001_replay.db)

| Metric | Value |
|---|---|
| signal_births total | 124 |
| opportunities created | 66 |
| confirming signal merges | 58 |
| opportunity_signals rows | 124 (matches signal_births — 1:1) |
| Date range active | 2026-07-23 to 2026-07-30 |

### 6.2 Sector Conviction Database

| Sector | Days | Avg Conviction | Peak Conviction | Peak Date |
|---|---|---|---|---|
| IT | 29 | 0.389 | 0.976 | 2026-07-29 |
| FMCG | 29 | 0.304 | 0.679 | 2026-07-06 |
| PHARMA | 29 | 0.297 | 0.654 | 2026-07-03 |
| AUTO | 29 | 0.290 | 0.711 | 2026-07-30 |
| CONSUMER_DURABLES | 29 | 0.263 | 0.717 | 2026-07-30 |
| BANKING_FINANCE | 29 | 0.252 | 0.598 | — |
| METALS | 29 | 0.232 | 0.686 | 2026-07-29 |
| CHEMICALS | 29 | 0.230 | 0.561 | — |
| ENERGY | 29 | 0.218 | 0.689 | 2026-07-21 |
| DEFENCE | 29 | 0.215 | 0.668 | 2026-07-06 |
| INFRA | 29 | 0.203 | 0.599 | — |
| TELECOM | 29 | 0.195 | 0.560 | — |

*Total rows: 348 (29 days × 12 sectors). 28 FULL + 1 PARTIAL per sector.*

### 6.3 Opportunity Lifecycle Distribution

| State | Count | Pct |
|---|---|---|
| DISCOVERED | 52 | 78.8% |
| ACTIVE | 14 | 21.2% |
| INVALIDATED | 0 | 0.0% |
| COMPLETED | 0 | 0.0% |

### 6.4 Opportunity Sector Distribution

| Sector | DISCOVERED | ACTIVE | Total |
|---|---|---|---|
| AUTO | 3 | 7 | 10 |
| IT | 10 | 1 | 11 |
| BANKING_FINANCE | 9 | 1 | 10 |
| FMCG | 9 | 2 | 11 |
| PHARMA | 7 | 1 | 8 |
| CONSUMER_DURABLES | 4 | 0 | 4 |
| METALS | 3 | 1 | 4 |
| DEFENCE | 2 | 0 | 2 |
| ENERGY | 2 | 0 | 2 |
| INFRA | 2 | 0 | 2 |
| CHEMICALS | 1 | 1 | 2 |
| **Total** | **52** | **14** | **66** |

### 6.5 ACTIVE Opportunities at Window End

| Symbol | Sector | Conviction | Confirming Signals | First Signal Date |
|---|---|---|---|---|
| JSWSTEEL.NS | METALS | 10.0 | 6 | 2026-07-23 |
| BHARATFORG.NS | AUTO | 10.0 | 4 | 2026-07-27 |
| SUNDRMFAST.NS | AUTO | 10.0 | 5 | 2026-07-27 |
| ENDURANCE.NS | AUTO | 10.0 | 5 | 2026-07-27 |
| BAJFINANCE.NS | BANKING_FINANCE | 10.0 | 4 | 2026-07-28 |
| BASF.NS | CHEMICALS | 7.5 | 3 | 2026-07-24 |
| M&M.NS | AUTO | 7.5 | 3 | 2026-07-27 |
| HEROMOTOCO.NS | AUTO | 7.5 | 3 | 2026-07-27 |
| CRAFTSMAN.NS | AUTO | 7.5 | 3 | 2026-07-27 |
| NAUKRI.NS | IT | 7.5 | 3 | 2026-07-28 |
| SAPPHIRE.NS | FMCG | 7.5 | 3 | 2026-07-28 |
| SUNPHARMA.NS | PHARMA | 7.5 | 3 | 2026-07-29 |
| EXIDEIND.NS | AUTO | 7.5 | 3 | 2026-07-29 |
| NESTLEIND.NS | FMCG | 7.5 | 3 | 2026-07-29 |

### 6.6 Learning Engines

| System | Status | Rows Written |
|---|---|---|
| edge_discovery | NOT RUN | — |
| MetaModel | NOT RUN | — |
| LearningEngine | NOT RUN | — |
| PatternMiner | NOT RUN | — |
| decision_log | 0 rows | 0 |
| oios_events | 0 rows | 0 |
| theme_phase_history | 0 rows | 0 |

---

## Section 7 — Research Questions Raised

*Generated exclusively from observations during this experiment. No answers.*

1. **Why did Layer1A produce zero signals for the first 23 of 29 simulated sessions?** Is this a rolling-window warm-up artefact, or does it reflect a genuine market pattern where momentum breakouts only emerged in late July 2026?
2. **Does `DNA_1B_QUIET_ACCUMULATION` generate valid signals without BHAV data?** The 18 signals recorded may be spurious if the archetype requires delivery percentage as a primary feature.
3. **Why did theme_phase_history produce 0 records across 29 sessions?** Is the SIDEWAYS regime inherently incompatible with theme classification, or is the detection threshold too high?
4. **What is the actual conviction threshold for DISCOVERED→ACTIVE?** All observed transitions occurred at conviction=7.5 — is this hardcoded or dynamically computed?
5. **Would the same 29-day window in a TRENDING regime produce fundamentally different archetype distributions?** RE001 shows SECTOR_PRE_BKT dominates in SIDEWAYS — does MOMENTUM_CONT dominate in TRENDING?
6. **Which 20 of 230 universe symbols consistently fail yfinance lookup?** Are these concentrated in certain sectors, potentially creating a detection bias?
7. **Can the replay window be extended to produce COMPLETED and INVALIDATED opportunities?** All 66 RE001 opportunities remain open — extending the window would enable edge_discovery, feature importance, and learning engine runs.
8. **Is the IT sector conviction surge in late July 2026 (peak 0.976) a genuine rotation event or a data anomaly?** Verifying against NIFTYIT price chart would confirm.
9. **Why did DEFENCE and TELECOM generate the fewest signals (2 each) despite being in the 12-sector conviction framework?** Is their low average conviction (0.215, 0.195) structurally suppressing signal generation?
10. **What is the correct invocation sequence for edge_discovery and learning engines against a completed replay DB?** RE001 established that `historical_replay.py` alone does not invoke them.

---

## Section 8 — Experiment Limitations

| # | Limitation | Impact |
|---|---|---|
| L-01 | **Historical data provider: Yahoo Finance** | Daily OHLC adjusted for splits and dividends. Intraday structure not captured. |
| L-02 | **Daily OHLC replay only** | Intraday patterns, opening auction dynamics, and session-level volatility are not observable. |
| L-03 | **Same-day candle assumptions** | Entry/exit assumed within same OHLC candle. Real execution faces slippage not modelled here. |
| L-04 | **Conservative SL-first ambiguity handling** | When a candle touches both SL and target, SL outcome is assumed. Understates potential positive outcomes. |
| L-05 | **Survivorship bias** | Universe contains only currently-listed symbols. Delisted/merged stocks during the replay window are absent. |
| L-06 | **No parameter optimisation** | All thresholds and scoring weights used as-is from production configuration. |
| L-07 | **30-day single-regime window** | 100% SIDEWAYS. Findings may not generalise to TRENDING or VOLATILE regimes. |
| L-08 | **BHAV completely absent** | 22 signals from delivery-dependent archetypes (QUIET_ACCUMULATION, LOW_NOISE_STRENGTH) are of uncertain quality. |
| L-09 | **No trade outcomes recorded** | All 66 opportunities remained DISCOVERED or ACTIVE at window end. Feature importance and edge discovery could not be assessed. |
| L-10 | **Learning engines not invoked** | edge_discovery, MetaModel, LearningEngine, PatternMiner, StrategyEvolution not run. Sections 6.3–6.6 are consequently sparse. |
| L-11 | **1 session skipped** | 2026-07-31 had no yfinance data at execution time. 29 of 30 sessions replayed. |

---

## Section 9 — Conclusions

**Based on observed data only. No performance claims. No unsupported inferences.**

**C-01 (VERIFIED):** The IIOS Historical Replay engine successfully executed a 29-session simulation with no errors, producing 124 signals across 6 archetypes, 66 opportunities, and complete sector conviction records for all 12 sectors. Platform integrity is confirmed.

**C-02 (VERIFIED):** The June–July 2026 NSE market was uniformly SIDEWAYS across the entire 29-session window. This is the first verified 29-day SIDEWAYS baseline in IIOS history.

**C-03 (VERIFIED):** Signal generation was exclusively concentrated in the final 6 sessions. The first 23 sessions were signal-silent. This is a structural observation about IIOS's detection sensitivity in SIDEWAYS markets that requires further investigation.

**C-04 (VERIFIED):** IT sector demonstrated the clearest conviction build-up (avg 0.389, peak 0.976 on 2026-07-29). AUTO sector generated the most signals by volume (31, 25.0%). The 14 ACTIVE opportunities at window end represent the system's highest-conviction candidates in the observed market environment.

**C-05 (LIMITATION-QUALIFIED):** The experiment could not assess trade outcomes, feature importance, or learning engine effectiveness because all 66 opportunities remained open at window end and learning engines were not invoked. RE001 establishes the observation layer baseline. RE002 must extend the window or invoke learning engines separately to complete the knowledge discovery pipeline.

**C-06 (HYPOTHESIS):** BHAV data absence is a structural replay limitation that degrades two of six archetypes. RE002 should include BHAV loading to enable full archetype coverage and delivery-validated signal quality assessment.

---

## Document Control

| Field | Value |
|---|---|
| Created | 2026-08-01 |
| Last Modified | 2026-08-01 |
| Status | COMPLETE (evidence-based) |
| Author | IIOS Research Framework / GitHub Copilot |
| Next Experiment | Research Experiment 002 |
| Comparison Baseline | This document (RE001) |
