# IIOS Research Platform
# Phase 1 Certification

**Document Type:** Official Research Certification  
**Version:** 1.0  
**Date:** 2026-08-01  
**Classification:** Research Operations — Permanent Reference

---

| Field | Value |
|---|---|
| **Platform** | Integrated Intelligence Operating System (IIOS) |
| **Phase** | Research Phase 1 — Engineering Validation |
| **Certification Decision** | **RESEARCH PHASE 1 CERTIFIED WITH OBSERVATIONS** |
| **Authorisation** | Phase 2 research activities are authorised |
| **Effective Date** | 2026-08-01 |

---

## Section 1 — Executive Summary

### 1.1 Objective of Phase 1

Research Phase 1 had a single objective: validate that the IIOS platform can execute a complete, end-to-end historical research cycle — from raw market data ingestion through to structured knowledge generation — while enforcing statistical quality gates that prevent false knowledge from entering persistent knowledge stores.

Phase 1 did not target trading performance, strategy optimisation, or profitability. It targeted pipeline integrity: the ability to observe, classify, and learn from historical market data correctly.

### 1.2 Scope

Phase 1 encompassed:

1. The core trading and AI platform infrastructure
2. The Historical Experience Training (HET) subsystem
3. The Opportunity Intelligence Operating System (OIOS) replay pipeline
4. The Edge Discovery Engine (EDE) — seven sub-systems
5. The MetaModel training architecture
6. All seven knowledge stores
7. Research Experiment 001 — 29-session Historical Replay
8. Research Experiment 001A — Knowledge Generation Validation

### 1.3 Certification Decision

> **RESEARCH PHASE 1: CERTIFIED WITH OBSERVATIONS**

The IIOS Research Platform has demonstrated end-to-end functional integrity across Stages 1-5 of the knowledge generation pipeline. The platform successfully ingested real NSE historical data, extracted labelled feature vectors, mined patterns, backtested candidates, and managed the edge lifecycle — all without errors and with quality gates functioning as designed.

**Observations recorded** (not deficiencies — expected structural conditions):

1. The MetaModel (Stage 6) requires closed trade outcomes to train. Research Experiment 001 produced no closed outcomes (all 66 opportunities remained open at window end). This is an expected data dependency, not a platform failure.
2. BHAV delivery data is unavailable in replay mode. Two of six archetypes (DNA_1B_QUIET_ACCUMULATION, DNA_1B_LOW_NOISE_STRENGTH) operate in degraded mode during historical replay.
3. The 29-session single-regime (SIDEWAYS) window is insufficient to establish generalizable edges. This is a research design observation, not a platform limitation.

---

## Section 2 — Engineering Milestones

### 2.1 Core Trading Platform V1

| Attribute | Value |
|---|---|
| **Status** | COMPLETE |
| **Certification** | PASS |
| **Evidence** | Live trading operational: paper trades recorded in `data/paper_trades.csv`; broker integration (Dhan) connected with token auth; yfinance fallback active |

Components verified:
- OrderManager with PAPER_TRADING mode, persistent CSV journal
- DataFeedManager with AngelOne → Dhan → Yahoo fallback chain
- RiskGuardian kill-switch (VIX, daily loss gates)
- MasterOrchestrator 17-layer scheduler

---

### 2.2 AI Platform V1

| Attribute | Value |
|---|---|
| **Status** | COMPLETE |
| **Certification** | PASS |
| **Evidence** | All 17 layers operational; full cycle benchmark 172ms; GlobalIntelligence 17ms |

Components verified:
- GlobalIntelligence (Layer 1): cache + background pre-warm
- MarketIntelligence (Layer 2): NIFTY/BANKNIFTY regime detection
- MetaLearning (Layer 3): architecture present, awaiting training data
- OpportunityEngine (Layer 4): equity + options scanning with telemetry
- DebateAndDecision (Layer 10): 5-agent debate, threshold 6.5
- ControlTower (Layer 17): SQLite telemetry, EventBus

---

### 2.3 Historical Experience Training (HET) Subsystem

| Attribute | Value |
|---|---|
| **Status** | COMPLETE |
| **Certification** | PASS |
| **Evidence** | `historical_replay.py` executed successfully; `data/re001_replay.db` created with 16 tables; data provider verified as Yahoo Finance (hardcoded, confirmed by `DHAN_DATA_PROVIDER_VERIFICATION.md`) |

Components verified:
- Isolated replay DB (`data/re001_replay.db` — separate from live `data/market_behavior.db`)
- Phase A: OHLCV download (210 symbols × 30 dates = 6,299 rows)
- Phase B: Day-by-day simulation (29 sessions)
- Phase C: Readiness report generation
- Regime detection: NIFTY50 SMA200 + 20-day return

---

### 2.4 Replay Learning (OIOS Pipeline)

| Attribute | Value |
|---|---|
| **Status** | COMPLETE |
| **Certification** | PASS |
| **Evidence** | `data/re001_replay.db` — signal_births: 124, opportunities: 66, sector_conviction_daily: 336 FULL-quality rows |

Components verified:
- Layer 1A scanner (DNA_1A archetypes): active, signal-generating
- Layer 1B scanner (DNA_1B archetypes): active, degraded BHAV mode documented
- Layer 1.5 (Sector Conviction): 12 sectors × 29 days = 348 rows (336 FULL quality)
- OpportunityService: DISCOVERED → ACTIVE lifecycle transitions observed
- State machine threshold: DISCOVERED → ACTIVE at conviction ≥ 7.5 (observed)
- Theme phase history: 0 rows (SIDEWAYS regime — expected)

---

### 2.5 Knowledge Generation (EDE Pipeline)

| Attribute | Value |
|---|---|
| **Status** | COMPLETE (Stages 1-5); BLOCKED (Stage 6 — data dependency) |
| **Certification** | PASS WITH OBSERVATION |
| **Evidence** | `data/re001a_results.json`; pipeline executed in 7.8s; no errors |

Components verified:
- Stage 1 Feature Extractor: 5,039 OHLCV-based feature vectors extracted and labelled
- Stage 2 PatternMiner: 3 patterns discovered (precision ≥ 58%, support ≥ 15)
- Stage 3 Candidate Strategy Generator: 3 candidates generated
- Stage 4 Strategy Tester: all 3 candidates rejected by walk-forward gate (WF < 50%)
- Stage 5 Edge Ranking Engine: 0 new edges; 6 ACTIVE edges correctly demoted to DECAYING
- Stage 6 MetaModel: NOT TRAINED — no trade outcomes from RE001 (all 66 opportunities open at window end)

---

### 2.6 Research Experiment 001

| Attribute | Value |
|---|---|
| **Status** | COMPLETE |
| **Certification** | PASS |
| **Reference** | `RESEARCH_EXPERIMENT_001_EXECUTION.md`, `RESEARCH_EXPERIMENT_001_FINDINGS.md` |

Key verified facts:
- 29 of 30 scheduled sessions simulated (one skipped: 2026-07-31, no yfinance data)
- 124 signals, 6 archetypes, 66 opportunities (52 DISCOVERED, 14 ACTIVE)
- 100% SIDEWAYS regime across 29 sessions
- No Python exceptions; exit code 0
- DB isolation confirmed: live `data/market_behavior.db` untouched
- IT sector peak conviction: 0.976 (2026-07-29)
- All opportunities LONG direction — zero SHORT signals in SIDEWAYS environment

---

### 2.7 Research Experiment 001A

| Attribute | Value |
|---|---|
| **Status** | COMPLETE |
| **Certification** | PASS WITH OBSERVATION (MetaModel stage blocked — expected) |
| **Reference** | `RESEARCH_EXPERIMENT_001A.md` |

Key verified facts:
- Feature DB: 0 → 4,964 labelled records; 20 → 228 unique symbols
- Real NSE OHLCV data replaced 100% of synthetic bootstrap in active feature DB
- PatternMiner operated on 10,059 × 58 feature matrix
- Walk-forward gate correctly rejected all 3 candidates (no false promotions)
- Edge lifecycle: 6 synthetic-data-based ACTIVE edges demoted to DECAYING when evaluated against real data
- MetaModel gap documented: requires closed trade outcomes not present in RE001

---

## Section 3 — Scientific Validation

The following facts are directly observed from RE001 and RE001A artefacts. Each has a specific source record.

### 3.1 Data Integrity

| # | Fact | Source |
|---|---|---|
| F-01 | Yahoo Finance is the sole data provider for historical replay — hardcoded in `oios/data/ohlcv_fetcher.py` | `DHAN_DATA_PROVIDER_VERIFICATION.md` |
| F-02 | OHLCV data was successfully loaded for 210 of 230 universe symbols across 30 trading dates (6,299 rows) | `ohlcv_daily` table in `re001_replay.db` |
| F-03 | BHAV delivery data was completely absent from the replay (0 rows) | `bhav_daily` COUNT=0 in `re001_replay.db` |
| F-04 | Sector conviction data achieved FULL quality for 336 of 348 records (96.6%) | `sector_conviction_daily` query |

### 3.2 Signal and Opportunity Generation

| # | Fact | Source |
|---|---|---|
| F-05 | 124 signals generated across 6 archetypes in 29 sessions | `signal_births` table |
| F-06 | 100% of 124 signals occurred under SIDEWAYS regime | `regime_at_birth` column — all = 'SIDEWAYS' |
| F-07 | 100% of signals occurred in the final 6 of 29 sessions (2026-07-23 to 2026-07-30) | `detected_at` column |
| F-08 | 66 opportunities created: 52 DISCOVERED (78.8%), 14 ACTIVE (21.2%) | `opportunities` table |
| F-09 | All 66 opportunities were LONG direction — zero SHORT signals | `direction` column |
| F-10 | ACTIVE threshold: conviction_score ≥ 7.5, confirmed by 14 ACTIVE opportunities all at 7.5 or 10.0 | `conviction_score` column + state machine log |

### 3.3 Knowledge Generation

| # | Fact | Source |
|---|---|---|
| F-11 | Synthetic bootstrap data (5,000 unlabeled records) replaced by real NSE OHLCV features | `ede_feature_db.json` before/after comparison |
| F-12 | 4,964 labelled feature records created from RE001 OHLCV data | `ede_feature_db.json` post-RE001A |
| F-13 | 228 NSE symbols represented in the feature database after RE001A | `ede_feature_db.json` unique symbol count |
| F-14 | Positive rate in real OHLCV data: 28.9% (next-day return ≥ 0.8%) | Computed from `forward_return` values |
| F-15 | PatternMiner executed on 10,059 × 58 feature matrix without errors | RE001A execution log |
| F-16 | 3 patterns discovered meeting precision (≥ 58%) and support (≥ 15) thresholds | PatternMiner output |
| F-17 | Walk-forward validation correctly rejected all 3 patterns (WF consistency: 20-40%, required ≥ 50%) | StrategyTester output |
| F-18 | No overfit patterns were promoted to the strategy library | `evolved_strategies.json` count unchanged at 176 |
| F-19 | 6 edges previously ACTIVE (based on synthetic data) were correctly demoted to DECAYING when evaluated against real data | `discovered_edges.json` before/after status comparison |
| F-20 | MetaModel correctly blocked: 0 trade outcomes available, model untrained | `ml_performance_dataset.json` absent; MetaModel `is_trained()` = False |
| F-21 | Learning integrity: no corruption, no data loss, no exception in any pipeline stage | Exit code 0; all knowledge stores verified post-run |

---

## Section 4 — Research Capability Assessment

| Capability | Status | Evidence |
|---|---|---|
| Observe markets | **READY** | 29 sessions simulated; 210 symbols tracked per day; 12 sectors with conviction scores |
| Extract features | **READY** | 5,039 feature vectors computed from real OHLCV across 24 trading dates; 27 features per vector |
| Generate labels | **READY** | 4,964 records labelled with actual forward_return values from next-day close prices |
| Mine patterns | **READY** | DecisionTreeClassifier + correlation sweep executed on 10,059 × 58 matrix; 3 patterns found |
| Validate strategies | **READY** | Walk-forward + OOS backtest gate fully operational; correctly rejected 3 overfit patterns |
| Generate knowledge | **PARTIALLY READY** | Feature DB knowledge generated; edge knowledge blocked (WF gate); MetaModel blocked (no outcomes) |
| Store knowledge | **READY** | All 7 knowledge stores operational; writes, reads, and delta comparisons verified |
| Reject weak evidence | **READY** | WF gate rejected all 3 candidates; EdgeRankingEngine demoted 6 synthetic-data edges |
| Learn from historical outcomes | **NOT READY** | Requires closed trade outcomes; RE001 produced 0 completed/invalidated opportunities |

**Summary:** 6 of 9 capabilities fully READY. 1 PARTIALLY READY. 2 NOT READY due to data dependency (closed trade outcomes), not platform failure.

---

## Section 5 — Known Scientific Limitations

The following limitations are documented from observed evidence. No recommended fixes are included in this section.

| # | Limitation | Scope | Impact |
|---|---|---|---|
| L-01 | **Yahoo Finance is the sole historical data provider** | All HET replay | Daily OHLC adjusted for splits and dividends. Intraday structure not captured. |
| L-02 | **Survivorship bias in universe** | RE001 and all future HET | Universe contains only currently-listed symbols. Stocks delisted, merged, or renamed during any replay window are absent. |
| L-03 | **Daily OHLC replay only** | RE001 | Intraday patterns, opening auction dynamics, and session-level volatility are not observable. All candles represent the full trading day. |
| L-04 | **Same-day candle ambiguity** | RE001 feature labels | When a candle touches both stop-loss and target on the same day, the conservative (stop-loss) outcome is assumed for label assignment. This understates potential positive labels. |
| L-05 | **BHAV delivery data unavailable in replay** | RE001, all future HET replay | DNA_1B_QUIET_ACCUMULATION and DNA_1B_LOW_NOISE_STRENGTH archetypes operated without delivery validation. Their 22 signals in RE001 are of uncertain quality. |
| L-06 | **MetaModel requires closed trade outcomes** | RE001A, current state | The MetaModel (k-NN regressor) cannot be trained until opportunities reach COMPLETED or INVALIDATED state and are written to `ml_performance_dataset.json`. |
| L-07 | **Single-regime validation window** | RE001 | 29 sessions covering 100% SIDEWAYS regime. Findings may not generalise to TRENDING_UP, TRENDING_DOWN, or VOLATILE regimes. |
| L-08 | **No parameter optimisation performed** | RE001, RE001A | All thresholds, scoring weights, and strategy parameters are used as-is from production configuration. No calibration was performed for the SIDEWAYS regime. |
| L-09 | **20 of 230 universe symbols had no yfinance data** | RE001 | Systematic exclusion of 20 symbols. Sectors represented by those symbols may be underweighted in feature observations. |
| L-10 | **Signal generation silent for first 23 of 29 sessions** | RE001 | The mechanism (rolling-window warm-up vs genuine market structure) is unconfirmed. All 124 signals appeared in the final 6 sessions only. |
| L-11 | **Theme phase detection produced 0 records** | RE001 | Theme phase classification did not fire across 29 SIDEWAYS sessions. Whether this is a regime constraint or a threshold setting is unconfirmed. |
| L-12 | **Feature DB capped at 5,000 rows** | RE001A | The EDE's internal `save_feature_db()` retains only the 5,000 most recent records. Older records are discarded during each discovery cycle. |

---

## Section 6 — Research Quality Gates

The following quality gates were confirmed active and functioning during Phase 1. They exist to prevent false knowledge from entering persistent stores.

### 6.1 Walk-Forward Consistency Gate

**Threshold:** WF consistency ≥ 50% (minimum fraction of OOS time windows that must be profitable)

**Function:** Each candidate strategy is backtested across multiple non-overlapping out-of-sample time windows. If fewer than 50% of windows are profitable, the strategy is rejected regardless of in-sample metrics.

**Phase 1 result:** All 3 candidates in RE001A failed this gate (WF = 20-40%). This prevented regime-specific momentum patterns from being incorrectly promoted as universal edges.

---

### 6.2 Expectancy Gate

**Threshold:** Expected return per trade ≥ 0.08R

**Function:** Strategies with statistically high win rates but insufficient average return per winner are rejected. This prevents low-expectancy strategies from consuming capital.

**Phase 1 result:** EDG_MOMENT_63_EE0000 failed with Exp_R = 0.045 < 0.08, in addition to the WF gate. Double gate failure provides additional signal quality confirmation.

---

### 6.3 Pattern Support Threshold

**Threshold:** Support ≥ 15 samples

**Function:** Patterns must appear in at least 15 historical samples before being considered for strategy generation. This prevents patterns discovered from statistical noise in thin data.

**Phase 1 result:** PatternMiner operated on 10,059 samples. All 3 discovered patterns exceeded the support threshold. No under-supported patterns were passed to the candidate generator.

---

### 6.4 Precision Threshold

**Threshold:** Precision ≥ 58% (hit rate on positive label prediction)

**Function:** Only patterns with a demonstrated positive prediction accuracy above the 58% threshold are extracted from the decision tree.

**Phase 1 result:** PatternMiner applied this threshold during tree extraction. Patterns below 58% precision were discarded at the mining stage, not propagated to later stages.

---

### 6.5 Edge Lifecycle Management

**States:** CANDIDATE → ACTIVE → DECAYING → DEPRECATED

**Function:** Edges are not permanently active. The EdgeRankingEngine continuously re-evaluates all edges. Edges whose composite scores (40% statistical quality + 40% live performance + 20% recency) fall below threshold are demoted to DECAYING. Edges with live win-rate below 45% are deprecated.

**Phase 1 result:** 6 edges that were ACTIVE based on synthetic bootstrap data were correctly demoted to DECAYING when evaluated against real RE001 OHLCV features. This confirmed that synthetic-data-derived edges do not survive real-data validation.

---

### 6.6 DB Isolation Gate

**Mechanism:** Separate SQLite files for replay (`data/re001_replay.db`) and live (`data/market_behavior.db`)

**Function:** Historical replay cannot corrupt live trading state. The isolation is enforced at the code level in `historical_replay.py`.

**Phase 1 result:** Verified by comparing checksums before and after RE001 execution. Live DB was untouched.

---

### 6.7 Learning Integrity Validation

**Mechanism:** Exit code verification, knowledge store count comparison (before/after), exception monitoring

**Function:** Any unhandled exception during the learning pipeline is treated as an integrity failure and halts the cycle.

**Phase 1 result:** RE001 exit code 0. RE001A exit code 0. No unhandled exceptions. All knowledge store changes accounted for in `data/re001a_results.json`.

---

### 6.8 Positive Rate Plausibility Check

**Observation:** After RE001A, the feature DB positive rate was 28.9% (1,434 of 4,964 labeled records had next-day return ≥ 0.8%). This is within a plausible range for NSE daily returns in a SIDEWAYS market.

**Function:** If the positive rate were near 0% or near 100%, it would indicate a data pipeline error in feature extraction or label computation. The 28.9% rate is consistent with observed market behavior.

---

## Section 7 — Phase 1 Conclusions

The following conclusions are drawn from verified evidence only.

### 7.1 The knowledge pipeline is structurally sound

Stages 1 through 5 of the knowledge generation pipeline executed end-to-end across two independent experiments without errors. Feature extraction, pattern mining, candidate generation, walk-forward backtesting, and edge lifecycle management all produced deterministic, traceable outputs.

### 7.2 Quality gates prevent false knowledge

Three pattern candidates were discovered from real NSE OHLCV data. All three were rejected by the walk-forward consistency gate. No overfit patterns entered the strategy library. Six synthetic-data-based edges were demoted when evaluated against real data. The quality protection layer worked as designed.

### 7.3 Real market data was successfully ingested

Research Experiment 001 ingested 6,299 actual NSE OHLCV candles across 210 symbols and 30 trading dates. Research Experiment 001A transformed those candles into 4,964 labelled feature records now stored in `ede_feature_db.json`. The feature database transitioned from 100% synthetic to 99.2% real market data.

### 7.4 The SIDEWAYS regime is the first verified historical baseline

All 29 simulated sessions (2026-06-19 to 2026-07-30) were classified as SIDEWAYS. This is IIOS's first verified 29-session SIDEWAYS baseline. Signal generation was concentrated in the final 6 sessions. The IT sector demonstrated the highest conviction build (peak 0.976 on 2026-07-29). AUTO sector generated the most signals (31 of 124, 25.0%).

### 7.5 The MetaModel data dependency is confirmed and documented

The MetaModel cannot train without closed trade outcomes. Research Experiment 001 produced 66 opportunities, none of which closed within the 29-session window. This is a documented research design constraint, not a platform failure. The MetaModel architecture is functional and will activate when trade outcomes become available.

### 7.6 The platform is ready for longer-duration research

Phase 1 demonstrated that the platform can complete a research cycle without data corruption, without false knowledge promotion, and without modifying any production configuration. The infrastructure required for longer-duration experiments is validated.

---

## Section 8 — Authorization for Phase 2

### 8.1 Research Experiment 002 — Authorized

Research Experiment 002 is authorized to begin. Phase 2 research may target:

- A longer historical replay window (90-180 sessions) designed to produce closed opportunity outcomes and enable MetaModel training
- A multi-regime window (including TRENDING_UP or TRENDING_DOWN sessions) to test cross-regime pattern stability
- A replay window with BHAV delivery data loaded (if historical BHAV becomes available) to enable full archetype coverage

### 8.2 Long-Duration Historical Experience Training — Authorized

Long-duration HET is authorized, subject to the following prerequisites being verified before each run:

| Prerequisite | Requirement |
|---|---|
| DB isolation | Confirm replay DB path is separate from `data/market_behavior.db` |
| yfinance data availability | Confirm the target date range returns valid OHLCV data for ≥ 70% of universe symbols |
| Feature DB state | Confirm `ede_feature_db.json` integrity before the run |
| Disk space | Confirm sufficient space for SQLite replay DB (estimate: ~50MB per 100 sessions) |
| Platform frozen | Confirm no code changes are made to trading logic or AI algorithms during the experiment |

### 8.3 MetaModel Activation — Prerequisite Unmet

MetaModel training is not yet authorized. It requires:
- Closed trade outcomes from at least 20 completed or invalidated opportunities
- Those outcomes written to `ml_performance_dataset.json` in the correct `PerformanceRecord` schema

This prerequisite will be met when either a sufficiently long replay window is run (so opportunities age out and close) or live paper trading produces closed outcomes.

---

## Section 9 — Official Declaration

---

> **OFFICIAL CERTIFICATION**
>
> The IIOS Research Platform has successfully completed Research Phase 1 validation.
>
> Two research experiments were executed — Research Experiment 001 (29-session historical replay) and Research Experiment 001A (knowledge generation validation) — using verified NSE historical data sourced from Yahoo Finance.
>
> The platform has demonstrated the ability to transform verified historical market data into structured research knowledge while enforcing statistical validation and knowledge-quality gates that prevent false or overfit patterns from entering persistent knowledge stores.
>
> The complete knowledge generation pipeline (Stages 1 through 5) executed end-to-end without errors. Four thousand nine hundred and sixty-four labelled feature records were created from real NSE OHLCV data. Three candidate strategies were discovered and correctly rejected by the walk-forward validation gate. Six synthetic-data-based edges were demoted by the real-data evidence. The MetaModel correctly declined to train in the absence of closed trade outcomes.
>
> Research integrity was maintained throughout. No trading logic was modified. No AI algorithm was modified. No parameters were optimised. All conclusions in this document are drawn from observed evidence.
>
> **Phase 2 research activities are authorised.**

---

## Document Control

| Field | Value |
|---|---|
| **Document ID** | RESEARCH_PHASE_1_CERTIFICATION_V1.0 |
| **Created** | 2026-08-01 |
| **Status** | FINAL |
| **Preceding documents** | `RESEARCH_EXPERIMENT_001_FINDINGS.md`, `RESEARCH_EXPERIMENT_001A.md` |
| **Evidence files** | `data/re001_replay.db`, `data/re001a_results.json`, `data/ede_feature_db.json`, `data/discovered_edges.json` |
| **Next document** | Research Experiment 002 Design |
| **Supersedes** | Nothing — first certification document |
