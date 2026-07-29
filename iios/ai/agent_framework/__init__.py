"""
iios.ai.agent_framework
=======================
A5 — AI Agent Framework

Six-layer architecture:
    M1 Lifecycle    — re-exports A1 lifecycle primitives
    M2 Engine       — AgentTask, AgentExecutionContext, AgentExecutionEngine, AgentResult
    M3 Policy       — ExecutionPolicy, PermissionPolicy, CapabilityPolicy
    M4 Core         — AgentSpec, AgentIdentity, AgentMetadata, AgentCapabilities,
                       AgentConfiguration, AgentPermissions, AgentHealth, AgentMetrics
    M5 Snapshot     — AgentSnapshot, AgentFrameworkSnapshot
    M6 Gateway      — AgentFrameworkGateway (single public entry point)

Dependency rule: A5 imports from A1–A4 only.
                 A5 never imports from iios.investment.

Error-code range: AI-1000 – AI-1099

A5 AI Agent Framework — Phase 3, Module 5
"""
VERSION = "1.0.0"
