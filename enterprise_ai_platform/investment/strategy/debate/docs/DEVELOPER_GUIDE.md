# Developer Guide

## Adding a New Evidence Source

1. Add a value to `EvidenceSource` in `debate_constants.py`
2. Add a protocol method to the appropriate adapter in `evidence_collector.py`
3. Add a parser method `_parse_<source>_data()` in `EvidenceCollector`
4. Update the relevant built-in agent's `_SOURCES` list in `participant_roles.py`
5. Add tests in `test_evidence.py`

## Adding a New Voting Mechanism

1. Add a value to `VotingMechanism` in `debate_constants.py`
2. Add a private `_<mechanism_name>()` method to `VotingEngine`
3. Add a branch in `VotingEngine.compute()` that calls the new method
4. Add tests in `test_consensus.py`

## Adding a New Debate Phase

1. Add a value to `DebatePhase` in `debate_constants.py`
2. Add the transition in `_VALID_TRANSITIONS` in `debate_state.py`
3. Add a `_phase_<name>()` async method in `DebateOrchestrator`
4. Call it from `DebateOrchestrator.run()` in the correct order
5. Update tests in `test_debate_session.py`

## Integration with Decision Layer

The Decision Layer can consume a `DebateReport` to inform its decision:

```python
report = engine.run_debate_sync(context)

# Safe fields to use:
consensus_direction = report.recommendation.consensus_direction
confidence          = report.recommendation.confidence
risk_flags          = report.recommendation.risk_flags

# The Decision Layer independently decides whether to act.
# The debate report is one of many inputs — it is NOT a decision.
```

## Thread Safety Model

| Component | Thread Safety |
|---|---|
| `DebateSession` | `RLock` on all mutations |
| `EvidenceRegistry` | `RLock` on all mutations |
| `ArgumentManager` | `RLock` on all mutations |
| `AgentRegistry` | `RLock` on all mutations |
| `DebateHistory` | `RLock` on all mutations |
| `DebateEventBus` | `Lock` on subscribe/emit |
| `ConsensusStatisticsTracker` | `RLock` on all mutations |
| `StrategyDebateEngine._active_sessions` | `RLock` |
| Async agent tasks | `asyncio.gather` (event-loop isolated) |

## Async Architecture

```
StrategyDebateEngine.run_debate(context)      # asyncio coroutine
  └── DebateOrchestrator.run(session, agents) # asyncio coroutine
        ├── _phase_opening    → asyncio.gather([agent.opening_statement(...) for agent in agents])
        ├── _phase_evidence   → sync collect via EvidenceCollector
        ├── _phase_arguments  → asyncio.gather([agent.generate_arguments(...)])
        ├── _phase_rebuttals  → asyncio.gather([agent.generate_rebuttal(target, ...)])
        ├── _phase_consensus  → asyncio.gather([agent.cast_vote(...)]) → ConsensusEngine.compute()
        └── _phase_final      → asyncio.gather([agent.final_opinion(...)])
```

## Score Conventions

All scores follow the 0–100 convention:
- **Evidence.raw_score**: > 55 bullish, < 45 bearish, 45–55 neutral
- **Argument.confidence**: certainty of the claim
- **ConsensusResult.confidence_score**: quality of the consensus
- **EvidenceScore.weighted_score**: composite quality × reliability × recency × relevance

## Testing Patterns

```python
# Sync test of async agent
import asyncio
agent = TechnicalAnalystAgent()
args  = asyncio.run(agent.generate_arguments(context, registry))

# Fast config for integration tests
config = OrchestratorConfig(
    max_argument_rounds=1,
    agent_timeout_seconds=5.0,
    min_quorum_fraction=0.3,
)
engine = StrategyDebateEngine(config=config)
report = engine.run_debate_sync(context)
```
