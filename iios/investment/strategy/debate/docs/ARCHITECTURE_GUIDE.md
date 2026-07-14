# Architecture Guide

## System Design

```
                        ┌─────────────────────────────────┐
                        │      StrategyDebateEngine        │
                        │  (facade — Task 1 + Task 8)      │
                        └──────────────┬──────────────────-┘
                                       │
                         ┌─────────────▼──────────────┐
                         │     DebateOrchestrator      │
                         │  (async — asyncio.gather)   │
                         └──┬───────┬────────┬────────┘
                            │       │        │
               ┌────────────▼─┐  ┌──▼───┐  ┌▼─────────────┐
               │  Agents (10) │  │Evid- │  │  Consensus   │
               │  (parallel)  │  │ence  │  │  Engine      │
               └──────┬───────┘  │Coll- │  └──────┬───────┘
                      │          │ector │         │
               ┌──────▼───────┐  └──────┘  ┌──────▼───────┐
               │ ArgumentMgr  │            │ VotingEngine  │
               │ RebuttalEng. │            │ AgreementAna. │
               └──────────────┘            └───────────────┘
                                                   │
                         ┌─────────────────────────▼──────────────┐
                         │              DebateReport               │
                         │  ExecutiveSummary + DebateExplanation   │
                         │  RecommendationSummary (NOT a decision) │
                         └─────────────────────────────────────────┘
```

## Key Data Flow

1. **Input**: `DebateContext` (strategy + opportunity + market + pre-loaded evidence)
2. **Session creation**: `DebateSession` (mutable; holds ArgumentManager, EvidenceRegistry, votes)
3. **State machine**: `DebateState` validates all phase transitions
4. **Evidence collection**: `EvidenceCollector` queries IIOS adapters → `EvidenceRegistry`
5. **Agent execution**: each agent independently processes evidence → generates `Argument`s
6. **Rebuttal loop**: agents challenge each other's arguments → `Rebuttal`s
7. **Voting**: all agents cast `Vote`s → `VotingEngine.compute()` → `VotingResult`
8. **Consensus**: `ConsensusEngine.compute()` → `ConsensusResult`
9. **Report**: `build_report()` assembles `DebateReport` from all session data

## Layered Boundaries

```
Layer 10 (DebateAndDecision)
  └── StrategyDebateEngine  ← this package
        ↑ consumes
  Layer 5 (StrategyLab)       via EvidenceCollector adapters
  Layer 2 (MarketIntelligence) via EvidenceCollector adapters
  Layer 7 (RiskControl)       via EvidenceCollector adapters
  Layer 13 (LearningSystem)   via EvidenceCollector adapters
  Layer 17 (ControlTower)     via DebateEventBus
```

## Module Dependency Graph (simplified)

```
debate_constants.py ← (everything depends on this)
  ↓
debate_events.py
debate_context.py
debate_state.py
  ↓
evidence_score.py ← evidence_registry.py ← evidence_validator.py
                              ↓
                    evidence_collector.py
                              ↓
participant_profile.py ← participant_roles.py ← agent_registry.py
  ↓
argument_manager.py
voting_engine.py
  ↓
agreement_analysis.py ← consensus_engine.py ← consensus_statistics.py
  ↓
debate_session.py
  ↓
debate_orchestrator.py
  ↓
recommendation_summary.py ← debate_explanation.py ← executive_summary.py
  ↓
debate_report.py
  ↓
strategy_debate_engine.py
  ↓
__init__.py
```

## Immutability Contract

All result types are **frozen dataclasses**:
- `Argument`, `Rebuttal` — argument records
- `Vote`, `VotingResult` — voting records
- `ConsensusResult` — consensus outcome
- `EvidenceScore` — computed score
- `AgreementMetrics` — agreement analysis
- `ParticipantProfile` — agent profile
- `DebateReport`, `ExecutiveSummary`, `DebateExplanation`, `RecommendationSummary`

Mutable objects (session, registries, stores) are internal to a single debate run and are not returned from the engine API — only frozen reports are.

## Concurrency Model

- Each debate runs in its own `asyncio` coroutine
- Agents within a debate run in parallel via `asyncio.gather(return_exceptions=True)`
- Agent failures are isolated — one failing agent does not abort the debate
- Multiple concurrent debates are safe: each has its own `DebateSession` with its own locks
- The `StrategyDebateEngine` itself is thread-safe for concurrent `run_debate_sync()` calls
