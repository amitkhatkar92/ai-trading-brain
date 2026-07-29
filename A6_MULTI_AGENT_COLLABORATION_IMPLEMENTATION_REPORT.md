# A6 Multi-Agent Collaboration Framework — Implementation Report

**Module:** `iios.ai.collaboration`
**Version:** 1.0.0
**Error code range:** AI-1100 – AI-1199
**Tests:** 120 / 120 passed
**Files created:** 42
**Lines of code:** ~4 800

---

## Overview

A6 implements a complete multi-agent collaboration framework that allows
multiple AI agents (from A5) to debate, vote and reach consensus on trading
decisions.  It follows the M1–M6 six-layer architecture established in A1–A5.

---

## Architecture

```
iios/ai/collaboration/
├── __init__.py                                  module root
├── exceptions/
│   └── collaboration_exceptions.py             22 exception classes (AI-1100–AI-1151)
├── lifecycle/__init__.py                        M1 — A1 lifecycle re-exports
├── core/
│   ├── collaboration_metadata.py               CollaborationStatus, CollaborationType, CollaborationMetadata
│   ├── agent_role_assignment.py                CollaborationRole, AgentRoleAssignment, SPECIALIST_DEFAULT_ROLES
│   ├── participant.py                           ParticipantStatus, Participant
│   ├── collaboration_context.py                CollaborationContext (immutable context for policies)
│   ├── collaboration_result.py                 CollaborationOutcome, CollaborationResult
│   └── __init__.py
├── events/
│   ├── collaboration_events.py                 13 frozen event types + CollaborationEventType enum
│   ├── collaboration_event_bus.py              Thread-safe pub/sub bus
│   └── __init__.py
├── messaging/
│   ├── agent_message.py                        MessageType, MessagePriority, AgentMessage
│   ├── message_metadata.py                     RetryPolicy, MessageMetadata (TTL-aware)
│   ├── message_envelope.py                     DeliveryStatus, MessageEnvelope
│   ├── message_bus.py                          Thread-safe per-session message store
│   ├── message_router.py                       Handler-based envelope dispatch
│   └── __init__.py
├── debate/
│   ├── debate_position.py                      PositionType (FOR/AGAINST/NEUTRAL/ABSTAIN/CUSTOM), DebatePosition
│   ├── debate_round.py                         RoundStatus, DebateRound (immutable closed round)
│   ├── debate_result.py                        DebateResult (dominant position, dissent analysis)
│   ├── debate_session.py                       DebateSession (mutable, open/submit/close round/next round/close)
│   ├── debate_manager.py                       Thread-safe DebateSession registry
│   └── __init__.py
├── consensus/
│   ├── consensus_result.py                     ConsensusOutcome, ConsensusResult
│   ├── consensus_strategy.py                   Abstract ConsensusStrategy + 4 implementations
│   ├── consensus_manager.py                    Strategy dispatcher with pluggable registry
│   └── __init__.py
├── escalation/
│   ├── escalation_rule.py                      EscalationTrigger, EscalationRule
│   ├── escalation_request.py                   EscalationStatus, EscalationRequest (mutable)
│   ├── escalation_decision.py                  EscalationAction, EscalationDecision (immutable)
│   ├── escalation_manager.py                   Thread-safe escalation lifecycle manager
│   └── __init__.py
├── policy/
│   ├── debate_policy.py                        DebatePolicy, DefaultDebatePolicy
│   ├── voting_policy.py                        VotingPolicy, DefaultVotingPolicy
│   ├── participation_policy.py                 ParticipationPolicy, DefaultParticipationPolicy
│   ├── escalation_policy.py                    EscalationPolicy, DefaultEscalationPolicy
│   ├── timeout_policy.py                       TimeoutPolicy, DefaultTimeoutPolicy
│   └── __init__.py
├── session/
│   ├── collaboration_session.py                Central mutable coordinator (status machine)
│   └── __init__.py
├── manager/
│   ├── collaboration_manager.py                Thread-safe session registry + snapshots
│   └── __init__.py
├── snapshot/
│   ├── collaboration_snapshot.py               CollaborationSessionSnapshot, CollaborationFrameworkSnapshot
│   └── __init__.py
├── container/
│   ├── collaboration_container.py              DI root — wires all singletons
│   └── __init__.py
└── gateway/
    ├── collaboration_gateway.py                M6 — CollaborationGateway(AILifecycleAwareMixin)
    └── __init__.py
```

---

## Layer Summary

| Layer | Components | Responsibility |
|-------|------------|---------------|
| M1 Lifecycle | `lifecycle/__init__.py` | Re-exports A1 primitives |
| M2 Events | `events/` | 13 event types, thread-safe pub/sub bus |
| M2 Messaging | `messaging/` | AgentMessage, MessageBus, MessageRouter |
| M3 Debate | `debate/` | Position submission, rounds, DebateResult |
| M3 Consensus | `consensus/` | 4 strategies, pluggable registry |
| M3 Escalation | `escalation/` | Trigger → request → decision lifecycle |
| M4 Core | `core/` | Metadata, roles, participants, context, result |
| M4 Policy | `policy/` | 5 abstract + default policy implementations |
| M5 Snapshot | `snapshot/` | Point-in-time frozen captures |
| M5 Session | `session/` | Mutable central coordinator (status machine) |
| M5 Manager | `manager/` | Session registry + framework snapshot |
| M6 Container | `container/` | DI root |
| M6 Gateway | `gateway/` | Single public entry-point (AILifecycleAwareMixin) |

---

## Key Design Decisions

### 1. Separation of DebateSession and ConsensusManager

Debate (submit arguments, multi-round) and consensus calculation (vote
aggregation, strategy dispatch) are separate concerns.  A session can run
through multiple debate rounds, then move to a voting phase, and only then
calculate consensus.

### 2. PositionType reused for votes

`DebatePosition` with `round_number=0` is reused to represent final votes.
This avoids a separate Vote class while keeping all position data unified
for consensus strategies.

### 3. Pluggable ConsensusStrategy

Four built-in strategies are registered by name:

| Name | Algorithm |
|------|-----------|
| `majority` | > 50% decisive votes win |
| `weighted` | participant.weight-weighted sum > 50% wins |
| `unanimous` | all decisive votes must agree |
| `confidence` | majority + mean confidence ≥ 0.7 |

Custom strategies can be registered at runtime via `ConsensusManager.register_strategy()`.

### 4. CollaborationSession status machine

```
CREATED → OPEN → DEBATING → VOTING → CONSENSUS_REACHED / CONSENSUS_FAILED
                                   ↘ ESCALATED → CLOSED
                                   ↘ FAILED
```

### 5. Thread safety

All mutable registries (`MessageBus`, `DebateManager`, `EscalationManager`,
`CollaborationManager`) use `threading.RLock`.  The `CollaborationSession`
itself uses an `RLock` to serialise state transitions.

---

## Consensus Strategies Detail

### MajorityVoteStrategy
- Counts decisive positions (FOR / AGAINST / CUSTOM)
- Winner needs > 50% of decisive votes
- Returns `MAJORITY_VOTE` outcome on success
- Returns `TIE` if top position tied

### WeightedVoteStrategy
- Sums `Participant.weight` per position_type
- Winner needs > 50% of total weight
- Supports asymmetric agent authority (e.g. RiskAgent weight 2.0)

### UnanimousStrategy
- All decisive votes must be the same position_type
- Returns `REACHED` on full agreement
- Returns `FAILED` on any dissent

### ConfidenceThresholdStrategy
- Runs majority vote first
- Winner's mean self-reported confidence must reach threshold (default 0.7)
- Returns `THRESHOLD_NOT_MET` if confidence too low

---

## Exception Hierarchy

```
AIException (A1, AI-000)
└── AICollaborationException               AI-1100
    ├── AICollaborationSessionNotFoundError        AI-1101
    ├── AICollaborationSessionAlreadyExistsError   AI-1102
    ├── AICollaborationSessionClosedError          AI-1103
    ├── AICollaborationParticipantNotFoundError    AI-1104
    ├── AICollaborationParticipantAlreadyExistsError AI-1105
    ├── AICollaborationValidationError             AI-1106
    ├── AIMessageException                         AI-1110
    │   ├── AIMessageNotFoundError                 AI-1111
    │   └── AIMessageRoutingError                  AI-1112
    ├── AIDebateException                          AI-1120
    │   ├── AIDebateNotFoundError                  AI-1121
    │   ├── AIDebateAlreadyClosedError              AI-1122
    │   └── AIDebateRoundError                     AI-1123
    ├── AIConsensusException                       AI-1130
    │   ├── AIConsensusFailedError                 AI-1131
    │   └── AIConsensusTimeoutError                AI-1132
    ├── AIEscalationException                      AI-1140
    │   ├── AIEscalationNotFoundError              AI-1141
    │   └── AIEscalationPolicyViolationError       AI-1142
    └── AICollaborationPolicyException             AI-1150
        └── AICollaborationPolicyViolationError    AI-1151
```

---

## Test Coverage

| Class | Tests | Description |
|-------|-------|-------------|
| `TestExceptions` | 22 | All error codes verified via `error_code` attribute |
| `TestLifecycleReExports` | 1 | M1 imports |
| `TestCollaborationMetadata` | 3 | Factory, UUID, status helpers |
| `TestAgentRoleAssignment` | 3 | can_vote, can_debate, specialist map |
| `TestParticipant` | 2 | with_status, can_vote |
| `TestCollaborationContext` | 2 | create, active_participant_count |
| `TestCollaborationResult` | 2 | consensus factory, failed factory |
| `TestCollaborationEvents` | 6 | All 13 event types |
| `TestCollaborationEventBus` | 5 | subscribe/publish/unsubscribe/error isolation/clear |
| `TestAgentMessage` | 3 | direct, broadcast, metadata |
| `TestMessageMetadata` | 2 | TTL expiry |
| `TestMessageBus` | 3 | send/history filter/clear |
| `TestMessageRouter` | 2 | route/unregister |
| `TestDebatePosition` | 3 | create, confidence clamp, is_decisive |
| `TestDebateSession` | 6 | submit, next round, close, post-close error, double-close |
| `TestDebateResult` | 2 | dominant FOR, tie → no dominant |
| `TestDebateManager` | 3 | create/get, missing raises, remove |
| `TestMajorityVoteStrategy` | 2 | majority wins, no decisive fails |
| `TestWeightedVoteStrategy` | 1 | weighted wins |
| `TestUnanimousStrategy` | 2 | success, failure |
| `TestConfidenceThresholdStrategy` | 2 | above/below threshold |
| `TestConsensusManager` | 2 | unknown strategy raises, register custom |
| `TestEscalationRequest` | 2 | create, update_status |
| `TestEscalationDecision` | 1 | create |
| `TestEscalationManager` | 3 | create/resolve, terminal re-resolve raises, missing raises |
| `TestPolicies` | 7 | All 5 default policies |
| `TestSnapshots` | 2 | session + framework snapshot |
| `TestCollaborationSession` | 7 | invite, duplicate, message, full debate+vote, escalate, close, context |
| `TestCollaborationManager` | 5 | create/get, missing raises, count, session snap, framework snap |
| `TestCollaborationGateway` | 11 | start/stop, health, create, invite, full cycle, snapshot, list, escalate, msg, pre-start error, status |
| `TestEndToEndIntegration` | 3 | 5-agent debate→consensus, tie→escalation, event bus full-cycle |
| **Total** | **120** | **120/120 passed** |

---

## Public Gateway API

```python
from iios.ai.collaboration.gateway import CollaborationGateway
from iios.ai.collaboration.core.agent_role_assignment import CollaborationRole
from iios.ai.collaboration.debate.debate_position import PositionType

gw = CollaborationGateway()
gw.start()

# Create session
sid = gw.create_collaboration("NIFTY direction", created_by="orchestrator")

# Invite agents
gw.invite_agent(sid, "ma", "MarketAnalyst", "MarketAnalystAgent", CollaborationRole.ANALYST)
gw.invite_agent(sid, "ra", "RiskAnalyst",   "RiskAnalystAgent",   CollaborationRole.CHALLENGER)

# Debate
gw.start_debate(sid)
gw.submit_argument(sid, "ma", PositionType.FOR,     "RSI oversold + momentum")
gw.submit_argument(sid, "ra", PositionType.AGAINST, "VIX elevated")
gw.next_round(sid)
gw.submit_argument(sid, "ma", PositionType.FOR, "Breakout confirmed")
gw.close_debate(sid)

# Vote and consensus
gw.vote(sid, "ma", PositionType.FOR,     0.85)
gw.vote(sid, "ra", PositionType.AGAINST, 0.60)
consensus = gw.calculate_consensus(sid, "majority")

# Close
final = gw.close_session(sid)

# Observability
health = gw.health()
snap   = gw.get_session_snapshot(sid)
```

---

## Cumulative Test Baseline

| Module | Tests |
|--------|-------|
| A1 Foundation | 264 |
| A2 Model Management | 93 |
| A3 Prompt & Context | 80 |
| A4 Memory & Knowledge | 132 |
| A5 Agent Framework | 215 |
| **A6 Collaboration** | **120** |
| **Total** | **904** |

All 904 tests pass.

---

## Status

**COMPLETE — FROZEN**

This module is now part of the protected architecture.
Do not modify without explicit instruction.
