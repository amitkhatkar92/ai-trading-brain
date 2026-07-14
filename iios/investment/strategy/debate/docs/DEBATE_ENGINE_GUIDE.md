# Debate Engine Guide

## Debate Lifecycle

```
INITIALIZATION → OPENING_STATEMENTS → EVIDENCE_COLLECTION →
ARGUMENTS → REBUTTALS → COUNTER_ARGUMENTS →
CONSENSUS_BUILDING → FINAL_OPINIONS → CLOSED
```

Each phase transition is validated by the `DebateStateMachine`. Skipping phases raises `DebateStateError`.

## OrchestratorConfig

```python
from iios.investment.strategy.debate import StrategyDebateEngine, OrchestratorConfig, ConsensusPolicy, VotingMechanism

engine = StrategyDebateEngine(
    config=OrchestratorConfig(
        max_argument_rounds=2,      # how many argument rounds per debate
        enable_rebuttals=True,
        rebuttal_rounds=1,
        agent_timeout_seconds=30.0, # per-agent async timeout
        require_quorum=True,
        min_quorum_fraction=0.5,    # 50% of agents must vote
        consensus_policy=ConsensusPolicy(
            mechanism=VotingMechanism.WEIGHTED_MAJORITY,
            threshold=0.6,
            min_quorum=3,
        ),
    )
)
```

## Async vs Sync

**Async (recommended for async callers)**:
```python
report = await engine.run_debate(context)
reports = await engine.run_debates_batch([ctx1, ctx2, ctx3])
```

**Sync (for non-async callers)**:
```python
report = engine.run_debate_sync(context)
```

The sync wrapper launches the async debate in a separate thread if an event loop is already running.

## Query API

```python
session  = engine.get_session(session_id)
report   = engine.get_report(session_id)
history  = engine.get_history("strat-001")
opinions = engine.get_agent_opinions(session_id, "participant_id")
consensus = engine.get_consensus_report(session_id)
minority  = engine.get_minority_report(session_id)
timeline  = engine.get_debate_timeline(session_id)
ev_sum    = engine.get_evidence_summary(session_id)
active    = engine.active_sessions()
stats     = engine.stats()
```

## Error Handling

- Agent timeout → agent is skipped, debate continues
- Agent exception → logged as warning, skipped
- Quorum not met → `consensus_reached=False` in ConsensusResult
- Total failure → `session.status == FAILED`, report still generated

## Event Subscription

```python
from iios.investment.strategy.debate import DebateEventType

def on_argument(event):
    print(f"New argument: {event.payload}")

engine.event_bus.subscribe(on_argument, DebateEventType.ARGUMENT_SUBMITTED)
```
