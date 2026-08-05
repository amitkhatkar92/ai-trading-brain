# IIOS Platform V1.0 — Release Notes

**Release Date:** 2026-08-05
**Tag:** `iios-v1.0-certified`
**Base Commit:** `1f78e95`

---

## Overview

IIOS V1.0 is the first certified release of the Investment Intelligence Operating System —
a 17-layer hierarchical multi-agent trading platform for Indian equity and derivatives
markets (NSE). V1.0 closes all P0 architectural gaps identified in Architecture Review 001
and introduces the full scientific governance stack for self-directed, auditable, and
scientifically rigorous continuous learning.

---

## What Was Built in V1

### Trading Platform Foundation (Pre-V1)

The 17-layer trading pipeline was operational before the V1 build cycle:

- Layer 1–17 pipeline from GlobalIntelligence to ControlTower
- ~62 AI agents operating in strict top-down sequence
- Three independent risk layers (L6 CapitalRiskEngine, L7 RiskControl, L9 RiskGuardian)
- 5-agent debate + DecisionEngine (threshold 6.5)
- Paper trading via OrderManager, Dhan broker (yfinance fallback)
- Streamlit Control Tower dashboard

Performance baseline locked: **172ms full cycle, HEALTHY**.

---

### V1 Build Cycle — Delivered Components

#### Architecture Review 001 (AR-001)
**Commit:** `306d150`

Complete architectural assessment of the platform. 15 documents.
Identified P0-001 through P0-004 and R-001 through R-007.

---

#### R-013 — Institutional DNA Repository (IDR)
**Commit:** `3f553cc` | Tests: 90/90

Persistent, versioned, auditable store for institutional DNA.

- `market_learning/idr_repository.py` — SQLite WAL, single-writer lock, version history
- `market_learning/idr_models.py` — `InstitutionalDNA`, `DNARevision`, `DNAEvidence`, `DNAContext`
- Every update creates a new version — history is never overwritten
- `audit_log` table records every write with operator, reason, timestamp
- Resolves: P0-002

---

#### R-001 Phase 1 — Platform Intelligence Gateway
**Commit:** `553bfdb` | Tests: 90/90

Single entry point to the institutional intelligence stack.

- `market_learning/pig_gateway.py` — `PIGTradingAdapter`, `PlatformIntelligence`
- `market_learning/pig_models.py` — all PIG output models
- Graceful fallback: returns `None` when library is empty
- Agent weight bounded at 0.08 (≤ weakest existing debate agent)

---

#### R-001 Phase 2 — PIG Integration into Trading Pipeline
**Commit:** `d294faa` | Tests: 115/115

PIG wired into both Opportunity Engine and Decision Engine.

- `pig_enrich_signals()` at `master_orchestrator.py:1583` — confidence boost from CDS relevance
- `pig_build_vote()` at `master_orchestrator.py:2539` — `InstitutionalDNAAI` vote in MultiAgentDebate
- `[PIGExplainability]` 7-field structured log at every evaluation
- Resolves: P0-001 (AR-001 FAIL verdict on Knowledge Flow)

---

#### MLS Phase 6 — Autonomous Market Learning Scheduler (AMLS)
**Commit:** `bdb79e7` | Tests: 125/125

Full daily automation of the MLS pipeline.

7-stage pipeline (EOD):
1. `MarketObserver.capture()` → DailyMarketSnapshot
2. `PopulationClassifier.classify()` → ClassificationResult
3. `DNADiscoveryEngine.discover()` → DiscoveryReport
4. `DNAConsensusEngine.update()` → ConsensusLibrary
5. `IDRRepository.save()` → `institutional_dna.db`
6. `PIGTradingAdapter.reload_library()` → refreshed PIG
7. Report generation → `data/mls/amls/reports/`

---

#### O-001 — AMLS Activation in Production
**Commit:** `ee99c3b`

`self.amls.run_pipeline()` wired into `_do_eod_learning()`.
`AMLS_ENABLED = True` in `config.py`.
Resolves: P0-003

---

#### O-002 — DNA Reinforcement Engine (DRE)
**Commit:** `ebb8dc9` | Tests: 200/200

Trade outcomes feed back into DNA confidence in IDR.

- `market_learning/dre_engine.py` — `DNAReinforcementEngine`
- `market_learning/dre_models.py` — `DNAReinforcement`, `ReinforcementType`, `OutcomeQuality`
- Safety caps: `max_single_trade_delta=0.05`, `min_idr_evidence_count=10`
- Writes to IDR via `idr.update(confidence, temporal_stability, evidence_count)`
- History: `data/mls/dre/history.json`

---

#### MarketLearningCoordinator (MLC)
**Commit:** `01b305c` | Tests: 160/160

Single coordinator for all market-learning activities.

6-stage daily pipeline:
1. Strategy learning (existing LearningEngine)
2. AMLS (MLS 7-stage)
3. DNA Reinforcement (DRE)
4. IDR Refresh
5. PIG Refresh
6. Summary

`_do_eod_learning()` now contains one call: `mlc.run_learning_pipeline(trades=trades)`.
Resolves: P0-004 (DRE wired via MLC Stage 3).

---

#### ARS Phase 1 — Knowledge Foundation
**Commits:** `e0bd0a3`, `04f4d0d`, `baee98d` | Tests: 35 + 40 + 40

- `KnowledgeProvider` — reads studies, findings, edges from disk (35 tests)
- `HypothesisRegistry` — full lifecycle PROPOSED→UNDER_REVIEW→CONFIRMED→ARCHIVED (40 tests)
- `CrossStudySynthesizer` — cross-study consensus, contradiction detection (40 tests)

---

#### ARS Phase 2 — Research Governance
**Commits:** `63cd900`, `9014138`, `a1df1bd`, `8c7f6ae` | Tests: 50 + 52 + 61 + 69

- `GapDetector` — 10 rules: DATA, EVIDENCE, REGIME, TEMPORAL, VALIDATION gaps (50 tests)
- `RoadmapManager` — prioritised research roadmap with severity tracking (52 tests)
- `EvidenceValidator` — 9 quality gates for hypothesis advancement (61 tests)
- `StudyPlanner` — study plan creation with dataset requirements (69 tests)

---

#### ARS Phase 3A — ResearchCoordinator
**Commit:** `3e6aed6` | Tests: 190/190

8-stage research pipeline orchestrator:

1. study_plan — load and validate plan
2. replay — run historical replay
3. validation — run validation engine
4. evidence — extract evidence for hypotheses
5. knowledge — update KnowledgeProvider
6. synthesis — cross-study synthesis
7. repository — persist to IDR
8. report — generate research report

PTUE-integrated: historical universe injected into replay stage.

---

#### ARS Phase 3B — Scientific Director Constitution
**Commit:** `2768259`

Constitutional document defining all governing principles of the Scientific Director.
Frozen. Cannot be modified without Architecture Review.

Key constraints:
- SD SHALL NOT execute scientific work
- SD SHALL ONLY observe, reason, prioritize, delegate, review
- SD has no access to broker, order manager, or execution engine
- Every decision must have rationale, delegation target, expected outcome

---

#### ARS Phase 3C — Scientific Director
**Commit:** `aba322d` | Tests: 301/301

Apex scientific authority of IIOS.

Query API:
- `daily_review()` — observe all components, generate hypotheses, auto-approve Class A plans
- `weekly_review()` — all daily + CrossStudySynthesizer state
- `monthly_review()` — all weekly + IDR state
- `evaluate_platform()` — full platform health review
- `approve_study(plan_id)` — Class A: auto-delegate to RC; Class B: human escalation
- `reject_study(plan_id, reason)` — documented rejection
- `roadmap()` — prioritised research roadmap
- `status()` — current health and last review state

ScientificJournal: append-only audit log of all reviews and decisions.

---

#### R-006 — Point-in-Time Universe Engine (PTUE)
**Commit:** `1f78e95` | Tests: 156/156

Eliminates survivorship bias from all historical learning.

- `autonomous_research/ptue.py` — `PointInTimeUniverseEngine`
- `autonomous_research/ptue_models.py` — all data models, error types, constants
- `autonomous_research/ptue_config.py` — `PTUEConfig`
- Seed data: `data/ars/ptue/NIFTY500/history.json`, `NIFTY50`, `NIFTY100` (from 2020-01-01)
- Query API: `get_universe(date)`, `contains(symbol, date)`, `history(symbol)`, `coverage()`, `statistics()`
- Maintenance API: `bootstrap_from_static()`, `add_constituent()`, `remove_constituent()`
- Thread-safe: `threading.RLock()`
- Graceful fallback: static JSON with explicit `is_fallback=True`, `coverage=0.5`
- [PTUEFallback] warning logged on every fallback activation

---

## Test Coverage — Complete V1 Platform

| Component | Tests |
|---|---|
| MarketObserver | 61 |
| PopulationClassifier | 73 |
| DNADiscoveryEngine | 83 |
| DNAConsensusEngine | 90 |
| PMCIEngine | 90 |
| MCIEngine | 90 |
| CDSEngine | 90 |
| CAPMCIEngine | 90 |
| IDRRepository | 90 |
| PIG Gateway | 90 |
| PIG Integration | 115 |
| AMLS | 125 |
| DNAReinforcementEngine | 200 |
| MarketLearningCoordinator | 160 |
| KnowledgeProvider | 35 |
| HypothesisRegistry | 40 |
| CrossStudySynthesizer | 40 |
| GapDetector | 50 |
| RoadmapManager | 52 |
| EvidenceValidator | 61 |
| StudyPlanner | 69 |
| ResearchCoordinator | 190 |
| ScientificDirector | 301 |
| PTUE | 156 |
| **TOTAL** | **2,441** |

**Pass rate: 100% (2,441 / 2,441)**

---

## Known Deferred Items (V2 Backlog)

| Item | Classification | Justification |
|---|---|---|
| Full MasterOrchestrator decomposition (R-002) | V2 Architecture | Learning + research already delegated; remaining requires AR-002 |
| Merge CorrelationEngine (R-003) | V2 Architecture | No correctness risk at current scale |
| Async NIFTY500 scan (R-004) | Performance | 172ms within budget; upgrade when symbols > 1000 |
| SQLite consolidation 14→4 (R-005) | V2 Architecture | Requires schema migration plan |
| `EVOLUTION_SEED` / `SIMULATION_SEED` (R-007) | Research | Reproducibility improvement only |
| Per-trade PMCI persistence (O-ADD-003) | Performance | DRE wiring complete; self-resolves as trades accumulate |
| Regime-aware strategy governance | Research | 30–50 trades per regime required first |
| Carry Phase C live decisions | Research | 50 SESSION_EXPIRED evidence gate by design |

---

## Platform Interfaces Locked at V1

The following interfaces are locked. Signatures cannot change without AR-002.

```python
GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot
SystemMonitor.time_layer(layer_name: str) -> contextmanager
MasterOrchestrator.run_full_cycle() -> None
MasterOrchestrator.start_scheduler() -> None
BaseFeed.get_quote(symbol: str) -> Optional[TickerQuote]
BaseFeed.get_multiple_quotes(symbols: List[str]) -> Dict[str, TickerQuote]
BaseFeed.get_history(symbol, days, interval) -> List[PriceBar]
```

---

*IIOS Platform V1.0 released: 2026-08-05*
