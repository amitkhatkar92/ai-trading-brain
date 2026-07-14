# Consensus Guide

## Voting Mechanisms

| Mechanism | Description |
|---|---|
| `WEIGHTED_MAJORITY` | Votes weighted by `ParticipantProfile.weight` (default) |
| `SIMPLE_MAJORITY` | Unweighted vote count |
| `SUPERMAJORITY` | Requires 2/3+ in any direction |
| `UNANIMOUS_REQUIRED` | All votes must match |
| `RANKED_CHOICE` | Plurality winner |

## Consensus Levels

| Level | Condition |
|---|---|
| `UNANIMOUS` | 100% agreement |
| `STRONG` | ≥ 75% |
| `MODERATE` | ≥ 60% |
| `WEAK` | ≥ 50% |
| `SPLIT` | < 50% — minority report issued |
| `NO_CONSENSUS` | Quorum not met |

## ConsensusPolicy

```python
from iios.investment.strategy.debate import ConsensusPolicy, VotingMechanism

policy = ConsensusPolicy(
    mechanism=VotingMechanism.WEIGHTED_MAJORITY,
    threshold=0.6,           # fraction required for consensus_reached=True
    require_quorum=True,
    min_quorum=3,            # minimum active votes
    allow_abstention=True,
    minority_threshold=0.3,  # fraction to trigger minority report
)
```

## VoteOutcome Values

| Outcome | Value |
|---|---|
| `STRONG_SUPPORT` | +2 |
| `SUPPORT` | +1 |
| `NEUTRAL` | 0 |
| `OPPOSE` | -1 |
| `STRONG_OPPOSE` | -2 |
| `ABSTAIN` | excluded from computation |

## Confidence Score

```
confidence = agreement_fraction × 80 + volume_bonus
volume_bonus = min(n_votes / (min_quorum × 2), 1.0) × 20
```

Range: 0–100.

## Minority Report

When `len(minority_agents) / n_active ≥ minority_threshold`, a minority report is generated containing:

- `minority_agent_ids` — list of dissenting participant IDs
- `minority_opinions` — final opinions of dissenters (in DebateReport)
- `minority_outcomes` — VoteOutcome values of dissenters

## AgreementMetrics

```python
from iios.investment.strategy.debate import AgreementAnalysis

analysis = AgreementAnalysis()
metrics  = analysis.analyse(votes, session_id="sid")

print(metrics.agreement_fraction)    # 0.0 – 1.0
print(metrics.polarisation_index)    # 0.0 = unanimous, 1.0 = maximally polar
print(metrics.std_deviation)         # stddev of numeric vote values
```
