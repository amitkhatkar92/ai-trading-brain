# Agent Guide

## Built-in Agents

| Agent Class | Role | Default Weight | Primary Evidence Source |
|---|---|---|---|
| `TechnicalAnalystAgent` | `TECHNICAL_ANALYST` | 1.5 | `TECHNICAL_ANALYSIS` |
| `FundamentalAnalystAgent` | `FUNDAMENTAL_ANALYST` | 1.5 | `FUNDAMENTAL_ANALYSIS` |
| `MarketIntelligenceAgent` | `MARKET_INTELLIGENCE` | 1.3 | `MARKET_INTELLIGENCE` |
| `CompanyIntelligenceAgent` | `COMPANY_INTELLIGENCE` | 1.2 | `COMPANY_INTELLIGENCE` |
| `MacroAnalystAgent` | `MACRO_ANALYST` | 1.8 | `MACRO_ANALYSIS` |
| `RiskAnalystAgent` | `RISK_ANALYST` | 2.0 | `RISK_INTELLIGENCE` |
| `PortfolioAnalystAgent` | `PORTFOLIO_ANALYST` | 1.2 | `STRATEGY_INTELLIGENCE` |
| `ExecutionAnalystAgent` | `EXECUTION_ANALYST` | 1.0 | `EXECUTION_ANALYSIS` |
| `SentimentAnalystAgent` | `SENTIMENT_ANALYST` | 0.8 | `SENTIMENT_ANALYSIS` |
| `StrategyLearningAgent` | `STRATEGY_LEARNING` | 1.4 | `LEARNING_ENGINE`, `HISTORICAL_RESULTS` |

## Agent Independence

Each built-in agent:
1. Receives only the `DebateContext` and `EvidenceRegistry` — no shared mutable state
2. Filters evidence by its own `_SOURCES` list
3. Applies role-specific scoring thresholds
4. Generates arguments independently of other agents' arguments

## Argument Generation Logic

All built-in agents follow this pattern:

```
average_score = mean(weighted_score for evidence in relevant_evidence)
if average_score >= threshold_high → ArgumentType.SUPPORTING
if average_score <= threshold_low  → ArgumentType.OPPOSING
else                               → no argument generated (neutral evidence)
```

Confidence = `min(avg_score × factor, 90.0)`  — never reaches 100 on single-source evidence.

## Creating a Custom Agent

```python
from iios.investment.strategy.debate import (
    BaseDebateAgent, ParticipantRole, ArgumentType,
    make_argument, make_vote, VoteOutcome, build_profile,
)
from typing import List, Optional

class SectorRotationAgent(BaseDebateAgent):

    def __init__(self):
        profile = build_profile(
            role=ParticipantRole.CUSTOM,
            display_name="Sector Rotation Specialist",
            weight=1.3,
            expertise_areas=["sector_rotation", "momentum"],
        )
        super().__init__(profile)

    @property
    def role(self):
        return ParticipantRole.CUSTOM

    async def opening_statement(self, context, registry):
        return [make_argument(
            context.context_id, self.participant_id, self.role,
            ArgumentType.NEUTRAL,
            claim="Sector rotation analysis pending",
            reasoning="Awaiting full evidence collection.",
            confidence=50.0,
        )]

    async def generate_arguments(self, context, registry, round_num=1):
        # your custom logic here
        return []

    async def generate_rebuttal(self, target, context, registry):
        return None

    async def cast_vote(self, context, arguments, registry):
        from iios.investment.strategy.debate import make_vote
        return make_vote(
            context.context_id, self.participant_id, self.role,
            VoteOutcome.NEUTRAL, 50.0, "Neutral pending full analysis.", self.weight,
        )

    async def final_opinion(self, context, consensus):
        return "Sector Rotation: Analysis complete."
```

## Registering a Custom Agent

```python
engine = StrategyDebateEngine()
engine.register_agent(SectorRotationAgent())
```

## Agent Weights

Weights affect `WEIGHTED_MAJORITY` voting. The `RiskAnalystAgent` has the highest default weight (2.0) reflecting the system's risk-first philosophy.

To override weights:

```python
from iios.investment.strategy.debate import build_profile, RiskAnalystAgent

agent = RiskAnalystAgent(build_profile(ParticipantRole.RISK_ANALYST, weight=1.0))
```
