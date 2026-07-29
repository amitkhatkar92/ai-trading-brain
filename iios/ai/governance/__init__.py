"""
iios.ai.governance
===================
A8 – AI Governance Platform

Provides enterprise AI governance, policy enforcement, security, compliance,
auditability, explainability, and operational controls across the entire
IIOS AI Platform.

Six-layer M1–M6 architecture:

  M1 lifecycle/      — A1 lifecycle re-exports
  M2 events/         — Immutable governance events + GovernanceEventBus
  M3 policy/         — PolicyEngine, PolicyRegistry, PolicyRule
  M3 permissions/    — PermissionManager, AccessControl, RolePolicy
  M3 audit/          — AuditManager, AuditRecord, AuditHistory
  M3 explainability/ — ExplainabilityManager, Explanation, DecisionTrace
  M3 compliance/     — ComplianceManager, ComplianceRule, ComplianceReport
  M3 risk/           — GovernanceRiskManager, RiskPolicy, RiskThreshold
  M3 governance/     — GovernanceManager (high-level coordinator)
  M4 core/           — Immutable frozen dataclasses + enums
  M4 exceptions/     — Hierarchy AI-1300 – AI-1399
  M5 snapshot/       — Point-in-time frozen captures
  M6 container/      — Dependency-injection root
  M6 gateway/        — GovernanceGateway (AILifecycleAwareMixin)

Error code range: AI-1300 – AI-1399

A8 AI Governance Platform — Phase 3, Module 8
"""

VERSION = "1.0.0"
