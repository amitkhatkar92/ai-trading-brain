"""
iios.ai.orchestrator
====================
A10 Enterprise AI Orchestrator.

Provides the executive control plane for the IIOS AI Platform.
Coordinates all other AI Platform modules (A1–A9) without
performing analysis itself.

Responsibilities
----------------
- Accept and decompose objectives
- Generate and validate execution plans
- Orchestrate workflow execution
- Schedule and prioritise tasks
- Coordinate resources and agent allocation
- Recover from failures
- Provide full observability

Error code range: AI-1500 – AI-1599

Six-layer architecture
----------------------
M1  lifecycle/       AILifecycleAwareMixin re-exports
M2  engine/          PlanningEngine, WorkflowManager, Orchestrator
M3  policy/          TaskScheduler, ResourceCoordinator, RecoveryManager
M4  core/            frozen dataclasses + exception hierarchy
M5  snapshot/        point-in-time snapshots
M6  container/       DI root · gateway/ public entry point

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
VERSION = "1.0.0"
