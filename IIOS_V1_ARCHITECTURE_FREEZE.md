# IIOS Platform V1.0 — Architecture Freeze

**Date:** 2026-08-05
**Authority:** Architecture Review Board
**Effective:** Immediately upon tagging `iios-v1.0-certified`

---

## Declaration

The IIOS Platform V1 architecture is hereby **FROZEN**.

No architectural changes, new layers, new coordinators, or new platform-level
interfaces may be introduced without completing Architecture Review 002 (AR-002).

This freeze applies to:
- All 17 trading layers and their inter-layer contracts
- All platform-level public interfaces (see §3)
- The Scientific Director Constitution (`SCIENTIFIC_DIRECTOR_CONSTITUTION.md`)
- The ARS Phase architecture (KP → HR → CSS → GD → RM → EV → SP → RC → SD)
- The MLS pipeline architecture (MO → PC → DDE → DCE → PMCI → MCI → CDS → CAPMCI → AMLS → IDR → PIG)
- All singleton instantiation patterns

---

## 1. What the Freeze Covers

### Frozen: Architecture
The following structural properties cannot change without AR-002:

| Property | Frozen Value |
|---|---|
| Number of trading layers | 17 |
| Layer execution order | L1→L2→…→L17 |
| MLS phase count | 6 phases + AMLS + IDR + PIG (14 components) |
| ARS phase count | Phase 1–3C (10 components) |
| PTUE universe format | `{history_root}/{universe_name}/history.json` |
| Knowledge flow direction | Unidirectional: Observation→DNA→IDR→PIG→Trade→DRE→IDR |
| Scientific governance model | SD observes, reasons, delegates — never executes |
| SD Constitution | Immutable — `SCIENTIFIC_DIRECTOR_CONSTITUTION.md` |

### Frozen: Interfaces

Public interfaces that may not have signatures changed:

```python
# Trading Platform
GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot
SystemMonitor.time_layer(layer_name: str) -> contextmanager
MasterOrchestrator.run_full_cycle() -> None
MasterOrchestrator.start_scheduler() -> None
BaseFeed.get_quote(symbol: str) -> Optional[TickerQuote]
BaseFeed.get_multiple_quotes(symbols: List[str]) -> Dict[str, TickerQuote]
BaseFeed.get_history(symbol, days, interval) -> List[PriceBar]

# MLS
MarketLearningCoordinator.run_learning_pipeline(trades) -> LearningRun
PIGTradingAdapter.evaluate_symbol(symbol, context) -> Optional[PlatformIntelligence]
IDRRepository.save(dna: InstitutionalDNA) -> str
IDRRepository.update(dna_id, confidence, temporal_stability, evidence_count)

# ARS
ResearchCoordinator.run_research(study_plan, ptue) -> ResearchRun
ScientificDirector.daily_review() -> ScientificReview
ScientificDirector.approve_study(plan_id) -> ScientificDecision
ScientificDirector.reject_study(plan_id, reason) -> ScientificDecision

# PTUE
PointInTimeUniverseEngine.get_universe(date, universe_name) -> HistoricalUniverse
PointInTimeUniverseEngine.contains(symbol, date, universe_name) -> bool
PointInTimeUniverseEngine.bootstrap_from_static(universe_name, effective_from) -> Path
```

### Frozen: Singletons

The following singletons must never be instantiated twice:

```python
get_performance_tracker()    # learning_system.strategy_performance_tracker
get_regime_strategy_map()    # meta_learning.regime_strategy_map
get_telegram_bot()           # notifications.telegram_bot
get_feed_manager()           # data_feeds.data_feed_manager
```

### Frozen: Latency Thresholds

```python
LAYER_LATENCY_WARN_MS  = 2_000   # per-layer default
LAYER_LATENCY_CRIT_MS  = 5_000   # per-layer default
LAYER_LATENCY_WARN_OVERRIDES = {"GlobalIntelligence": 5_000}
LAYER_LATENCY_CRIT_OVERRIDES = {"GlobalIntelligence": 12_000}
```

Performance baseline: 172ms full cycle — shall not be regressed.

---

## 2. What is Permitted Without AR-002

The following work can proceed under SD + RC governance:

| Type | Permitted | Governance |
|---|---|---|
| **Research** | New strategy discovery, new market phenomena studies, DNA library growth | RC approves (Class A) or SD approves (Class B) |
| **Knowledge** | New constituent history records, evidence addition, hypothesis lifecycle | SD daily_review governance |
| **Performance** | Latency improvements, telemetry improvements, diagnostic coverage | SHM evidence gate |
| **Bug fixes** | Preserve interface, fix behaviour | Direct (reversible) |
| **New universe indices** | Add `data/ars/ptue/{NEW_INDEX}/history.json` | PTUE bootstrap_from_static() |
| **Configuration tuning** | Thresholds, schedule times, enabled flags | Operator + telemetry evidence |

---

## 3. What Requires AR-002

| Change | Why AR-002 Required |
|---|---|
| Decompose `master_orchestrator.py` (R-002) | Changes all 17-layer inter-layer contracts |
| Merge CorrelationEngine (R-003) | Changes shared service interface; affects L1, L6, L7 |
| Async NIFTY500 scan (R-004) | Changes L4 execution model |
| SQLite consolidation 14→4 (R-005) | Schema migration; affects all knowledge stores |
| New trading layer (L18+) | Extends 17-layer pipeline |
| New debate agent (6th) | Changes MultiAgentDebate scoring model |
| New kill-switch condition | Risk Guardian modification — real money implications |
| New risk tier | Changes L6/L7/L9 inter-tier contracts |
| SD constitutional amendment | Scientific governance model change |
| New broker integration | New execution path for real capital |

---

## 4. Protected Modules

These modules cannot be modified without explicit operator instruction and AR-002 approval:

| Module | Reason |
|---|---|
| `risk_guardian/risk_guardian.py` | Kill-switch — wrong edit = real capital loss |
| `strategy_lab/backtesting_ai.py` | WFT/OOS quality gates are calibrated |
| `validation_engine/` | 6-stage promotion pipeline, thresholds set |
| `strategy_lab/evolved_strategies/` | Earned through evolution — not hand-written |
| `SCIENTIFIC_DIRECTOR_CONSTITUTION.md` | Foundation of scientific governance |
| `data/` directory | Live SQLite databases + persisted state |
| `data_feeds/dhan_feed.py` | Broker auth + order routing |

---

## 5. Architecture Review 002 — Trigger Conditions

AR-002 should be initiated when any of the following is true:

1. Live capital deployment is being considered
2. Symbol universe expands beyond NIFTY500 (e.g., SENSEX, mid-cap)
3. Multi-country operation is planned
4. Trading volume exceeds 50 positions/day (scan latency will regress)
5. New broker with significantly different API surface is integrated
6. The `master_orchestrator.py` decomposition (R-002) is ready to begin
7. Any P0 item emerges that is not addressable within the current architecture

---

## 6. Deferred Item Register

Items deferred from V1, to be re-evaluated at AR-002:

| Ref | Item | Priority | Re-evaluate When |
|---|---|---|---|
| R-002 | Decompose MasterOrchestrator | P1 | When symbol universe > 500 or AR-002 |
| R-003 | Merge CorrelationEngine | P2 | AR-002 |
| R-004 | Async NIFTY500 scan | P2 | When scan latency > 5s consistently |
| R-005 | SQLite consolidation | P2 | AR-002 |
| R-007 | Evolution/simulation seeds | P3 | AR-002 |
| O-ADD-003 | Per-trade PMCI persistence | MEDIUM | After 100+ live trades accumulate |
| Regime-aware governance | Strategy disable by regime | — | After 30–50 trades/regime |
| Carry Phase C | Live carry extension decisions | — | After 50 SESSION_EXPIRED trades |

---

## 7. Commit Baseline

The V1 architecture is frozen at the following commit:

```
1f78e95 — feat: R-006 Point-in-Time Universe Engine (PTUE)
2026-08-05
```

No architectural change may be made to code committed before this point
without AR-002 approval.

---

*Architecture Freeze issued: 2026-08-05*
*Effective until: Architecture Review 002*
