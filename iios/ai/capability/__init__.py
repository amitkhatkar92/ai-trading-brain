"""
iios.ai.capability
===================
A9 Enterprise Capability Platform.

Provides a unified capability framework that enables AI agents to securely
discover, register, authorise, and execute capabilities.

A capability may represent:
  - Tool
  - Skill
  - External Service / Connector
  - Knowledge Source
  - Execution Environment
  - Workflow Action

Error code range: AI-1400 – AI-1499

Six-layer architecture
----------------------
M1  lifecycle/    AILifecycleAwareMixin re-exports
M2  engine/       CapabilityExecutor + request/response types
M3  policy/       permissions, policies, quota, audit
M4  core/         frozen dataclasses + exception hierarchy
M5  snapshot/     point-in-time snapshots
M6  container/    DI root · gateway/ public entry point

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
VERSION = "1.0.0"
