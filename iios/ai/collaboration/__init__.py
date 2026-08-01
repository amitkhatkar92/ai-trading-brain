"""
iios.ai.collaboration
=====================
A6 — Multi-Agent Collaboration Framework

Six-layer architecture:
    M1 Lifecycle    — re-exports A1 lifecycle primitives
    M2 Engine       — DebateSession, ConsensusManager, EscalationManager, MessageBus
    M3 Policy       — DebatePolicy, VotingPolicy, ParticipationPolicy,
                       EscalationPolicy, TimeoutPolicy
    M4 Core         — CollaborationMetadata, CollaborationContext, CollaborationResult,
                       Participant, AgentRoleAssignment + messaging + debate + consensus
    M5 Snapshot     — CollaborationSessionSnapshot, CollaborationFrameworkSnapshot
    M6 Gateway      — CollaborationGateway (single public entry point)

Dependency rule: A6 imports from A1–A5 only.
                 A6 never imports from iios.investment.

Error-code range: AI-1100 – AI-1199

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
VERSION = "1.0.0"

__version__ = "1.0.0"
