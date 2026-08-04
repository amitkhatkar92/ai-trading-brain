# Intelligence Duplication Audit
## AR-001 Part 4: Duplicated Logic with KEEP / MERGE / REMOVE Verdicts

**Date:** 2026-08-04

---

## Overview

This document audits every intelligence component where duplication,
overlap, or redundancy has been observed. Each item receives a verdict:

- **KEEP** — Duplication is intentional and serves distinct purposes.
- **MERGE** — Logic should be unified into a single canonical source.
- **REMOVE** — Component is redundant and can be deleted.
- **INTEGRATE** — Component is not duplicated but is isolated and needs wiring.

---

## 1. CorrelationEngine (3 copies) — MERGE

| Instance | Location | Purpose | Lines |
|---|---|---|---|
| A | `global_intelligence/correlation_engine.py` | Macro asset correlations | ~150 |
| B | `capital_risk_engine/correlation_engine.py` | Portfolio correlation sizing | ~120 |
| C | `risk_control/correlation_engine.py` | Risk-level correlation check | ~100 |

**Evidence of duplication:**
All three use Pearson/Spearman correlation on price returns. Core `_rolling_correlation()`
and `_pairwise_matrix()` functions are structurally identical.

**Why MERGE:**
A divergence in correlation formula (e.g., lookback window) across three copies
means portfolio risk checks may use different correlation values than capital sizing.
This is a latent numerical inconsistency.

**Proposed merged location:** `analytics/correlation_engine.py`
- Accepts `CorrelationContext` enum: `MACRO`, `PORTFOLIO`, `RISK`
- Each caller passes its context; same underlying math, same formula

**Migration:** Zero interface change at call sites — wrapper adapters in each package.

---

## 2. Walk-Forward Test (3 implementations) — MERGE split logic only

| Instance | Location | Used By |
|---|---|---|
| WFT-1 | `strategy_lab/backtesting_ai.py` | Strategy evolution fitness |
| WFT-2 | `validation_engine/walkforward_test.py` | 6-stage validation gate |
| WFT-3 | `performance/walk_forward_tester.py` | Performance attribution |

**Evidence of duplication:**
All three implement an in-sample / out-of-sample split. The split ratio and
window logic are independently coded.

**Why not full MERGE:**
Each WFT serves a different master:
- Evolution WFT: fast, approximate, many iterations
- Validation WFT: rigorous, gate-quality, single run
- Performance WFT: attribution-focused, fold-level detail

**Verdict:** **MERGE** the window-split calculation only (IST/OOS boundary dates).
Keep the three evaluation frameworks separate.

---

## 3. Regime Computation — KEEP (with verification)

| Instance | Location | What it does |
|---|---|---|
| MarketRegimeAI | `market_intelligence/market_regime_ai.py` | Canonical regime classification |
| FeatureExtractor | `meta_learning/feature_extractor.py` | Extracts regime as a feature |
| MarketObserver | `market_learning/market_observer.py` | Captures regime observation for MLS |

**Verdict: KEEP.**
These do not duplicate regime computation.  
- `MarketRegimeAI` is the single source of truth (canonical label).
- `FeatureExtractor` should be CONSUMING the MarketRegimeAI output, not recomputing.
- `MarketObserver` records the regime at observation time for MLS temporal tracking.

**Action required:** Verify `FeatureExtractor` reads from `MarketRegimeAI`
rather than recomputing from raw quotes. If it recomputes, that is a bug.

---

## 4. Confidence / Scoring Scales — KEEP with annotation

| Component | Scale | Meaning |
|---|---|---|
| `MultiAgentDebate` | 0–10 | Agent conviction (threshold 6.5) |
| `EquityScannerAI` | 0–1 | Breakout confidence |
| `PMCIEngine` | 0–1 | Pre-movement probability |
| `CDSEngine` | 0–1 | Contextual DNA relevance |
| `CapitalRiskEngine` | 0–1 | Position sizing factor |

**Verdict: KEEP.**
These represent different things and are not duplicates. However:
- PMCI score (0–1) must be mapped to debate conviction (0–10) before combination.
- CDSEngine relevance tier should produce a multiplier for `EquityScannerAI` score.

**Action required:** See R-001 in ARCHITECTURE_RECOMMENDATIONS.md.

---

## 5. Risk Evaluation — KEEP (layered defence)

| Layer | Component | Guard condition |
|---|---|---|
| 6 | `CapitalRiskEngine` | Position size too large |
| 7 | `RiskManagerAI` | Pre-execution approval |
| 7 | `StressTestAI` | Stress scenario failure |
| 8 | `SimulationEngine` | Monte Carlo adverse tail |
| 9 | `FailSafeRiskGuardian` | VIX>45, daily loss >2% |

**Verdict: KEEP.**
These are intentionally redundant for safety. Each layer blocks different
classes of risk. Removing any of them reduces safety depth.

---

## 6. Market Simulation vs Stress Test (2 implementations) — KEEP with clarification

| Component | Location | Method |
|---|---|---|
| `SimulationEngine` | `market_simulation/simulation_engine.py` | Monte Carlo (returns sampling) |
| `StressTestEngine` | `market_simulation/stress_test_engine.py` | 14 deterministic scenarios |
| `StressTestAI` | `risk_control/stress_test_ai.py` | Pre-execution stress check |

**Verdict: KEEP.**
`SimulationEngine` is probabilistic (MC sampling).
`StressTestEngine` is deterministic (14 fixed scenarios).
`StressTestAI` applies stress results to pre-execution veto.
These serve distinct functions, though `StressTestAI` should consume
`StressTestEngine` output rather than re-implementing scenarios.

---

## 7. DNA / Pattern Discovery vs Edge Discovery — INTEGRATE

| Component | Location | What it finds |
|---|---|---|
| `DNADiscoveryEngine` | `market_learning/dna_discovery_engine.py` | Statistical price patterns (DNA) |
| `EdgeDiscoveryEngine` | `edge_discovery/edge_discovery_engine.py` | Exploitable market edges |

**Verdict: INTEGRATE (not duplicates, but isolated from each other).**
DNA = persistent price patterns with statistical backing.
Edge = opportunities discovered via pattern mining.

These should feed each other: discovered edges should be tested against DNA
to verify statistical significance. Neither currently informs the other.

---

## 8. Learning System vs EOD Retrospective — KEEP

| Component | What it does |
|---|---|
| `LearningEngine` | Updates strategy weights based on outcomes |
| `EODRetrospective` | Daily trade review narrative |
| `DailyAISelfEvaluator` | Performance grading (A–F) |
| `ImprovementBacklog` | Issue tracking |

**Verdict: KEEP.**
`LearningEngine` acts. The others observe and record. No duplication.

---

## Summary Table

| Component | Count | Verdict | Priority |
|---|---|---|---|
| CorrelationEngine | 3 | **MERGE** | High |
| WalkForward split logic | 3 | **MERGE** (split logic only) | Medium |
| Regime computation | 3 | **KEEP** (verify FeatureExtractor) | Low |
| Confidence scales | 5 | **KEEP** (add normalisation bridge) | Medium |
| Risk layers | 5 | **KEEP** (defence-in-depth) | None |
| Simulation vs Stress | 3 | **KEEP** (clarify StressTestAI) | Low |
| DNA vs Edge discovery | 2 | **INTEGRATE** | Medium |
| Learning vs Retrospective | 4 | **KEEP** | None |
