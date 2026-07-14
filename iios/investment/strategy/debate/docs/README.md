# Institutional Multi-Agent Strategy Debate Engine

## Overview

The **Strategy Debate Engine** simulates an institutional investment committee where multiple independent AI agents evaluate the same opportunity, debate supporting and opposing evidence, challenge assumptions, resolve disagreements, and publish an explainable report.

> ⚠️ **THIS ENGINE DOES NOT MAKE TRADING DECISIONS.**  
> The Decision Layer remains the **only component** authorised to issue Buy/Sell/Hold decisions.

## Quick Start

```python
from iios.investment.strategy.debate import (
    StrategyDebateEngine,
    DebateContext,
    StrategyDebateInput,
    OpportunityDebateInput,
    MarketSnapshot,
)

# Build context
context = DebateContext(
    strategy=StrategyDebateInput(
        strategy_id="strat-001",
        strategy_name="NIFTY Breakout",
        category="momentum",
        direction="BUY",
        min_rr=2.0,
        max_loss_pct=2.0,
    ),
    opportunity=OpportunityDebateInput(
        opportunity_id="opp-001",
        symbol="RELIANCE",
        asset_class="equity",
        entry_price=2450.0,
        target_price=2550.0,
        stop_price=2400.0,
    ),
    market=MarketSnapshot(regime="bullish", vix=14.5, sector="energy"),
)

# Run debate (sync)
engine = StrategyDebateEngine()
report = engine.run_debate_sync(context)

print(report.executive_summary.one_liner)
print(report.recommendation.consensus_direction)
```

## Package Structure

```
iios/investment/strategy/debate/
├── debate_constants.py        # All enumerations
├── debate_events.py           # Event bus (DebateEventBus)
├── debate_context.py          # DebateContext dataclass
├── debate_state.py            # State machine
├── debate_session.py          # DebateSession (central mutable object)
├── debate_history.py          # DebateHistory store
├── participant_profile.py     # ParticipantProfile + DEFAULT_WEIGHTS
├── participant_roles.py       # BaseDebateAgent + 10 built-in agents
├── agent_registry.py          # AgentRegistry + create_default_registry()
├── argument_manager.py        # Argument, Rebuttal, ArgumentManager
├── evidence_score.py          # EvidenceScore + scoring logic
├── evidence_validator.py      # EvidenceValidator
├── evidence_registry.py       # Evidence, EvidenceRegistry
├── evidence_collector.py      # EvidenceCollector + protocol adapters
├── voting_engine.py           # Vote, VotingEngine, VotingResult
├── agreement_analysis.py      # AgreementAnalysis, AgreementMetrics
├── consensus_statistics.py    # ConsensusStatisticsTracker
├── consensus_engine.py        # ConsensusEngine, ConsensusPolicy, ConsensusResult
├── recommendation_summary.py  # RecommendationSummary (NOT a decision)
├── debate_explanation.py      # DebateExplanation
├── executive_summary.py       # ExecutiveSummary
├── debate_report.py           # DebateReport (full immutable report)
├── debate_orchestrator.py     # DebateOrchestrator (async, asyncio.gather)
├── strategy_debate_engine.py  # StrategyDebateEngine (main facade)
└── __init__.py                # Public API
```

## Key Invariants

| Invariant | How Enforced |
|---|---|
| Never issues Buy/Sell/Hold | No decision-type fields in DebateReport |
| Never executes trades | No broker/order imports |
| Agent independence | Each agent filters its own evidence, no shared state |
| Auditability | All arguments, votes, evidence are immutable frozen dataclasses |
| Thread safety | All mutable stores use `threading.RLock` |
| Reproducibility | All inputs captured in `DebateContext`; results deterministic given same inputs |

## Tests

```bash
python -m pytest tests/unit/investment/strategy/debate/ -x -q
```

140 tests — session, participants, arguments, evidence, consensus, reports, engine.

## Documentation

- [DEBATE_ENGINE_GUIDE.md](DEBATE_ENGINE_GUIDE.md) — Engine lifecycle and configuration
- [EVIDENCE_GUIDE.md](EVIDENCE_GUIDE.md) — Evidence scoring and collection
- [CONSENSUS_GUIDE.md](CONSENSUS_GUIDE.md) — Voting mechanisms and consensus policy
- [AGENT_GUIDE.md](AGENT_GUIDE.md) — Built-in agents and custom agent authoring
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — Extension and integration guide
- [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) — System design and data flow
