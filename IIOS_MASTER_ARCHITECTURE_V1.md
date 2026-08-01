# IIOS Master Architecture — Version 1.0

**Document:** IIOS_MASTER_ARCHITECTURE_V1  
**Version:** 1.0.0  
**Date:** 2026-08-01  
**Status:** ENTERPRISE CERTIFIED — Architecture Frozen  
**Repository:** `https://github.com/amitkhatkar92/ai-trading-brain.git`  
**Release Commit:** `9812e2f` (Core Trading Platform) / `2170a8a` (AI Platform F5 docs)

This is the single authoritative reference for IIOS Version 1.0. Where detailed
content exists in a release document, this file references it rather than duplicating it.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Platform Overview](#2-platform-overview)
3. [Core Trading Platform](#3-core-trading-platform)
4. [AI Platform](#4-ai-platform)
5. [Platform Bootstrap](#5-platform-bootstrap)
6. [Certified Architecture](#6-certified-architecture)
7. [Version 1.0 Inventory](#7-version-10-inventory)
8. [Certification History](#8-certification-history)
9. [Versioning Policy](#9-versioning-policy)
10. [Deferred Roadmap](#10-deferred-roadmap)
11. [Operational Guidelines](#11-operational-guidelines)
12. [Final Declaration](#12-final-declaration)

---

## 1. Executive Summary

### Vision

IIOS (Intelligent Investment Operating System) is a production-grade multi-platform
system for automated analysis, decision making, and execution across Indian equity and
derivatives markets. It combines a 17-layer hierarchical trading pipeline with a
10-module AI platform — both governed under a formal certification lifecycle.

### Objectives

- Provide deterministic, auditable, and risk-bounded trading execution
- Provide a production-ready AI capability layer for enterprise integration
- Enforce strict architectural separation between the trading pipeline and the AI platform
- Operate safely in both paper and live modes with minimal operational risk

### Platform Philosophy

**Safety over speed.** Every signal must survive regime detection, backtesting quality
gates, a 5-agent debate, a decision threshold, and a hard kill-switch before execution.

**Architecture over convenience.** No cross-imports. No circular dependencies. Star
topology enforced. Public interfaces versioned and frozen.

**Intentional evolution.** Breaking changes require a formal governance cycle. No
module is modified speculatively. No interface is changed without an explicit version increment.

### Version 1.0 Certification Summary

```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   IIOS VERSION 1.0 — ENTERPRISE CERTIFIED                         ║
║                                                                    ║
║   Core Trading Platform  Version 1.0  Frozen  2026-07-25          ║
║   AI Platform            Version 1.0  Frozen  2026-08-01          ║
║   Platform Bootstrap     Version 1.0  Frozen  2026-08-01          ║
║                                                                    ║
║   Core Tests:   10,855 / 10,855  PASS                             ║
║   AI Tests:      1,796 /  1,796  PASS                             ║
║   Total:        12,651 / 12,651  PASS                             ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 2. Platform Overview

IIOS is organized in four tiers. Each tier has a well-defined responsibility and
depends only on tiers below it.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Tier 4 — Future Enterprise Services (planned; v2.0+)               │
│  Cross-platform event fabric, enterprise integration services        │
├──────────────────────────────────────────────────────────────────────┤
│  Tier 3 — AI Platform                                               │
│  A1–A10: Foundation, Model Management, Prompt & Context,            │
│  Memory & Knowledge, Agent Framework, Collaboration,                │
│  Learning & Evaluation, Governance, Capability, Orchestration       │
│                              │                                       │
│  Tier 2.5 — Platform Bootstrap                                      │
│  IIOSBootstrap, Lifecycle Manager, PlatformRegistry,                │
│  StartupCoordinator, ShutdownCoordinator, HealthCoordinator         │
├──────────────────────────────────────────────────────────────────────┤
│  Tier 2 — Core Trading Platform                                     │
│  C1–C16: 17-layer hierarchical trading pipeline                     │
│  ~3,500+ source files, ~62 agents                                   │
├──────────────────────────────────────────────────────────────────────┤
│  Tier 1 — Infrastructure                                            │
│  Python 3.14 · Docker · VPS · SQLite · yfinance · Dhan API          │
└──────────────────────────────────────────────────────────────────────┘
```

### Dependency Direction

```
AI Platform (A1–A10)
      │
      │  depends on (read-only)
      ▼
Core Trading Platform (C1–C16)    [read-only from AI perspective]
      │
      ▼
Infrastructure
```

The AI Platform never modifies Core Trading Platform state. The Core Trading Platform
does not import from the AI Platform. All cross-tier communication goes through
well-defined gateway interfaces.

---

## 3. Core Trading Platform

**Full detail:** [CORE_TRADING_PLATFORM_V1_RELEASE.md](CORE_TRADING_PLATFORM_V1_RELEASE.md)  
**Audit:** [CORE_TRADING_PLATFORM_ARCHITECTURE_AUDIT_V1.md](CORE_TRADING_PLATFORM_ARCHITECTURE_AUDIT_V1.md)

### Summary

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Freeze Status** | FROZEN |
| **Freeze Date** | 2026-07-25 |
| **Freeze Commit** | `686a06c` |
| **Total Modules** | 16 (C1–C16) |
| **Architecture Generations** | Gen 1 (C1–C5) · Gen 2 (C6–C16) |
| **Regression Tests** | 10,855 PASS |
| **F-Phases Completed** | F1 (8.8/10) · F2 · F3 |

### C1–C5 — Intelligence Foundation (Generation 1)

Pre-standard modules. Domain-engine aggregation pattern. Serve as the intelligence
foundation consumed by the Gen 2 governance layer.

| Module | Package | Responsibility |
|---|---|---|
| **C1** — Market Intelligence | `iios/investment/market/` | Volatility, breadth, correlation, regime, sector, sentiment, liquidity, opportunity |
| **C2** — Company Intelligence | `iios/investment/company/` | Financials, earnings, valuation, growth, governance, fundamentals, quality, profile |
| **C3** — Strategy Intelligence | `iios/investment/strategy/` | Strategy evaluation, portfolio risk, learning, debate, simulation, adaptation |
| **C4** — Decision Intelligence | `iios/investment/decision/` | Evidence, reasoning, confidence, risk, explainability, multi-agent committee |
| **C5** — Portfolio Intelligence | `iios/investment/portfolio/` | Construction, allocation, optimization, diversification, rebalancing, positions |

### C6–C8 — Execution Layer (Generation 2)

Multi-phase composite. Six-layer structure per phase with domain-specific naming.

| Module | Package | Responsibility |
|---|---|---|
| **C6** — Execution Engine | `iios/execution/` | OMS, position management, risk controls, gateway routing, monitoring (~968 files) |
| **C7** — Execution Recovery | `iios/execution/recovery/` | Failover, circuit-breaker, error recovery |
| **C8** — Execution Analytics | `iios/execution/analytics/` | Trade performance analytics, predictive analytics (no M3 — intentional) |

### C9–C16 — Governance & Infrastructure Layer (Generation 2)

Full M1–M6 six-layer standard. All frozen with verified interface contracts.

| Module | Package | Responsibility | Tests |
|---|---|---|---|
| **C9** — Decision Governance | `iios/decision/` | AI decision governance, approval workflows, policy enforcement, audit | ~695 |
| **C10** — Portfolio Governance | `iios/portfolio/` | Allocation constraints, optimization, rebalancing policies | ~917 |
| **C11** — Risk Management | `iios/risk/` | Enterprise risk engine; VaR, CVaR, stress, scenario, 17 engines | ~1,155 |
| **C12** — Market Intelligence (Gen 2) | `iios/market/` | Governed analytics: breadth, correlation, forecasting, 18 engines | ~703 |
| **C13** — AI Supervisor | `iios/supervisor/` | AI governance, audit, compliance, policy enforcement platform-wide | ~1,291 |
| **C14** — Knowledge Management | `iios/knowledge/` | Knowledge graph, entity, ontology, reasoning, search, versioning (251 files) | ~1,000+ |
| **C15** — Enterprise Integration Gateway | `iios/integration/` | External connectors, adapters, protocols, message buses, streaming (583 files) | ~2,000+ |
| **C16** — Enterprise Workflow Gateway | `iios/workflow/` | Workflow orchestration: checkpoint, compensation, parallel, sequential (128 files) | 951 |

### Freeze Status

All 16 modules are **officially frozen at Version 1.0**. Public APIs, snapshot contracts,
exception hierarchies, event contracts, DTOs, enums, and constants are locked.

No changes to C1–C16 are permitted without:
1. A formal version increment decision
2. A new F1–F3 governance cycle covering the affected modules

---

## 4. AI Platform

**Full detail:** [AI_PLATFORM_V1_RELEASE.md](AI_PLATFORM_V1_RELEASE.md)  
**API Manifest:** [PUBLIC_API_MANIFEST_V1.md](PUBLIC_API_MANIFEST_V1.md)

### Summary

| Field | Value |
|---|---|
| **Version** | 1.0.0 |
| **Freeze Status** | FROZEN |
| **Freeze Date** | 2026-08-01 |
| **Freeze Constants** | `FREEZE_VERSION = "1.0.0"`, `FREEZE_DATE = "2026-08-01"` |
| **Modules** | A1–A10 + Platform Bootstrap (11 components) |
| **Tests** | 1,796 PASS |
| **F-Phases Completed** | F0 · F0.1 · F1 · F2 · F3 · F4 · F5 |

### Module Inventory

| ID | Module | Gateway Class | Responsibility |
|---|---|---|---|
| **A1** | `iios.ai.foundation` | `AIFoundationGateway` | AI lifecycle, provider abstraction, event bus, configuration |
| **A2** | `iios.ai.model_management` | `ModelManagementGateway` | Model registry, versioning, routing, capability management, health |
| **A3** | `iios.ai.prompt_context` | `PromptContextGateway` | Prompt template management, context assembly, variable injection |
| **A4** | `iios.ai.memory_knowledge` | `MemoryKnowledgeGateway` | Agent memory (scoped), knowledge base, graph traversal |
| **A5** | `iios.ai.agent_framework` | `AgentFrameworkGateway` | Agent lifecycle, task execution, role assignment, coordination |
| **A6** | `iios.ai.collaboration` | `CollaborationGateway` | Multi-agent debate, consensus, escalation, session management |
| **A7** | `iios.ai.learning_evaluation` | `LearningEvaluationGateway` | Benchmarking, evaluation, adaptive learning, session tracking |
| **A8** | `iios.ai.governance` | `GovernanceGateway` | Policy governance, permissions, audit trail, compliance frameworks |
| **A9** | `iios.ai.capability` | `CapabilityGateway` | Capability registry, skills catalog, connectors, quota management |
| **A10** | `iios.ai.orchestrator` | `OrchestratorGateway` | Workflow orchestration, task scheduling, resource management, recovery |

All 10 gateways are at `VERSION = "1.0.0"`, `STATUS = "stable"`.  
All 10 satisfy `isinstance(gateway, GatewayProtocol)` at runtime.

For full method signatures, see [PUBLIC_API_MANIFEST_V1.md](PUBLIC_API_MANIFEST_V1.md).

### AI Platform Layer Map

```
Layer 0 — Core Trading Platform   (external; read-only)
Layer 1 — AI Foundation           A1 — no AI module dependencies
Layer 2 — AI Capabilities         A2–A9 — each depends on A1 only
Layer 3 — AI Orchestrator         A10 — depends on A1 only
Layer 4 — Platform Bootstrap      iios.ai.platform — coordinates A1–A10
```

---

## 5. Platform Bootstrap

**Package:** `iios.ai.platform`  
**Entry class:** `IIOSBootstrap`  
**Version:** 1.0.0  
**Bootstrap constant:** `BOOTSTRAP_VERSION = "1.0.0"`

The Platform Bootstrap is the coordination layer that starts, stops, health-checks,
and monitors all registered AI platform modules (A1–A10). It never imports from
individual AI modules — all interaction occurs through the duck-typed gateway interface.

### Components

| Component | Class | Responsibility |
|---|---|---|
| **Bootstrap** | `IIOSBootstrap` | Primary entry point; orchestrates full lifecycle via subordinate coordinators |
| **Lifecycle Manager** | `LifecycleCoordinator` | Delegates to startup, shutdown, and health coordinators |
| **Registry** | `PlatformRegistry` | Stores all registered platform instances; enforces unique IDs |
| **Startup** | `StartupCoordinator` | Kahn's topological sort → batch-ordered start; required vs optional failure semantics |
| **Shutdown** | `ShutdownCoordinator` | Best-effort reverse-order stop; exceptions caught and logged; shutdown continues |
| **Health** | `HealthCoordinator` | Per-platform health probe; aggregates to `healthy / degraded / unknown / down` |

### Lifecycle Phases

```
register(gateway, *, depends_on, optional)
      │
      ▼
start()  ←─── StartupCoordinator (Kahn's algorithm, batch-ordered)
      │
      │   REGISTERED → STARTING → RUNNING
      │                         ↘ FAILED (on required failure → dependents blocked)
      ▼
operations  ─── health() polls aggregate status
      │
      ▼
stop()  ←─── ShutdownCoordinator (reverse order, best-effort)
      │
      │   RUNNING → STOPPING → STOPPED
      ▼
restart()  ←─── stop() + start()
```

### Health Model

```
Per-platform:
  RUNNING + health() ok     →  HEALTH_UP
  RUNNING + health() raises →  HEALTH_DEGRADED
  RUNNING + no health()     →  HEALTH_UNKNOWN
  FAILED or STOPPED         →  HEALTH_DOWN

Aggregate:
  any HEALTH_DOWN     →  "down"
  any HEALTH_DEGRADED or HEALTH_UNKNOWN  →  "degraded"
  all HEALTH_UP       →  "healthy"
  no platforms        →  "unknown"
```

### Star Topology — Bootstrap Enforcement

The `StartupCoordinator` uses Kahn's topological algorithm to resolve dependency order
before any gateway is started. Detected cycles raise `CircularDependencyError` before
any `start()` call is made. The resolved order always places A1 (foundation, no
declared dependencies) in Batch 0, and A2–A10 (all depend on A1) in Batch 1.

---

## 6. Certified Architecture

### 6.1 Six-Layer Architecture (M1–M6)

Every AI module (A2–A10) follows the M1–M6 six-layer pattern. A1 is the foundational
primitive and is exempt from M2/M3/M4 (it supplies what those layers depend on).

| Layer | Name | Purpose |
|---|---|---|
| M1 | `lifecycle/` | Re-exports `AILifecycleAwareMixin` from A1 |
| M2 | `engine/` | Primary computation engine (domain-specific directory name in some modules) |
| M3 | `policy/` | Policy and rule application |
| M4 | `core/` | Domain types, exceptions, enumerations |
| M5 | `snapshot/` | Immutable state capture (frozen dataclasses) |
| M6 | `gateway/` | Single public entry point |

The Core Trading Platform (C6–C16) uses the same M1–M6 pattern. C1–C5 predate the
standard and follow a domain-engine aggregation pattern; this is intentional and
architecturally documented.

### 6.2 Dependency Rules

**AI Platform:**
- A2–A10 may import from A1 only
- A2–A10 must never import from each other (zero cross-imports — verified by automated scan)
- The Platform Bootstrap must never import from A1–A10 at module load time
- The Core Trading Platform is read-only from the AI Platform's perspective

**Core Trading Platform:**
- C16 is the infrastructure root; it has zero imports from `iios.investment.*`
- C9–C15 depend on C16 for lifecycle infrastructure
- C1–C5 serve as the intelligence foundation consumed by C6–C16
- No circular dependencies (verified by automated scan)

### 6.3 Gateway Pattern

Every public module exposes exactly one M6 gateway class. The gateway:
- Is the sole import target for external consumers
- Implements the `GatewayProtocol` (`@runtime_checkable Protocol`)
- Inherits `AILifecycleAwareMixin` (start / stop / restart / health / status / snapshot)
- Carries frozen metadata constants: `SYSTEM_ID`, `VERSION`, `MODULE_ID`, `MODULE_NAME`,
  `API_VERSION`, `DESCRIPTION`, `STATUS`

The required protocol surface for all M6 gateways:

```python
class GatewayProtocol(Protocol):
    SYSTEM_ID   : str
    VERSION     : str
    MODULE_ID   : str
    MODULE_NAME : str

    def start(self) -> Any: ...
    def stop(self) -> Any: ...
    def restart(self) -> Any: ...
    def health(self) -> Any: ...
    def status(self) -> Any: ...
    def snapshot(self) -> Any: ...
```

### 6.4 Snapshot Pattern

Snapshots are the read-only state capture mechanism for every module. Rules:

- All snapshots are **frozen dataclasses** (`@dataclass(frozen=True)`)
- All carry a `captured_at: float` timestamp (UNIX epoch)
- Snapshots have **zero imports** from gateway or engine layers (no upward deps)
- Snapshots are the only safe way to pass module state across the platform boundary
- 17 snapshot types are frozen at Version 1.0 (12 domain + 5 platform)

### 6.5 Exception Hierarchy

All platform exceptions follow a single inheritance chain:

```
BaseException
    └── Exception
            └── IIOSError
                    └── AIException  (base for all AI Platform exceptions)
                            ├── AIFoundationException      (A1: AI-000–AI-702)
                            ├── AIModelManagementException (A2: AI-850–AI-999)
                            ├── AIPromptException          (A3: AI-800–AI-849)
                            ├── AIMemoryException          (A4: AI-700–AI-799)
                            ├── AIAgentException           (A5: AI-1000–AI-1099)
                            ├── AICollaborationException   (A6: AI-1100–AI-1199)
                            ├── AIEvaluationException      (A7: AI-1200–AI-1299)
                            ├── AIGovernanceException      (A8: AI-1300–AI-1419)
                            ├── AICapabilityException      (A9: AI-1420–AI-1519)
                            └── AIPlatformException        (A10: AI-1520–AI-1563)
```

232 canonical exception classes. 8 backward-compatible aliases (deprecated, removal
in v2.0). Full hierarchy in [PUBLIC_API_MANIFEST_V1.md](PUBLIC_API_MANIFEST_V1.md).

### 6.6 Versioning Policy

See [Section 9](#9-versioning-policy) for full rules. Summary:

| Change Type | Version Bump | Governance Required |
|---|---|---|
| Bug fix (no interface change) | 1.0.x patch | No |
| New additive method/class | 1.x.0 minor | F3 freeze amendment |
| Breaking interface change | x.0.0 major | Full F1–F5 cycle |

---

## 7. Version 1.0 Inventory

### 7.1 Platform Versions

| Platform | Version | Freeze Date | Commit |
|---|---|---|---|
| IIOS Core Trading Platform | 1.0 | 2026-07-25 | `686a06c` |
| IIOS AI Platform | 1.0.0 | 2026-08-01 | `9812e2f` |
| Platform Bootstrap | 1.0.0 | 2026-08-01 | `9812e2f` |

### 7.2 Certified Modules

| ID | Module | Version | Status |
|---|---|---|---|
| C1–C5 | Core Intelligence Foundation | 1.0 | ✅ Frozen |
| C6–C8 | Core Execution Layer | 1.0 | ✅ Frozen |
| C9–C16 | Core Governance & Infrastructure | 1.0 | ✅ Frozen |
| A1 | AI Foundation | 1.0.0 | ✅ Frozen |
| A2 | Model Management | 1.0.0 | ✅ Frozen |
| A3 | Prompt & Context | 1.0.0 | ✅ Frozen |
| A4 | Memory & Knowledge | 1.0.0 | ✅ Frozen |
| A5 | Agent Framework | 1.0.0 | ✅ Frozen |
| A6 | Collaboration | 1.0.0 | ✅ Frozen |
| A7 | Learning & Evaluation | 1.0.0 | ✅ Frozen |
| A8 | Governance | 1.0.0 | ✅ Frozen |
| A9 | Capability | 1.0.0 | ✅ Frozen |
| A10 | Orchestrator | 1.0.0 | ✅ Frozen |
| P0 | Platform Bootstrap | 1.0.0 | ✅ Frozen |

### 7.3 Public API Surface

| Surface | Count | Reference |
|---|---|---|
| AI gateway public methods | 251 | [PUBLIC_API_MANIFEST_V1.md](PUBLIC_API_MANIFEST_V1.md) §A1–A10 |
| Platform bootstrap methods | ~35 | [PUBLIC_API_MANIFEST_V1.md](PUBLIC_API_MANIFEST_V1.md) §Bootstrap |
| Grand total public methods | ~286 | |
| Gateway metadata constants (per gateway) | 7 | `SYSTEM_ID`, `VERSION`, `MODULE_ID`, `MODULE_NAME`, `API_VERSION`, `DESCRIPTION`, `STATUS` |
| Frozen snapshot types | 17 | 12 domain + 5 platform |
| Canonical exception classes | 232 | AI-000 through AI-1563 |
| Backward-compat exception aliases | 8 | Deprecated — removal in v2.0 |
| `GatewayProtocol` | 1 | `@runtime_checkable Protocol` |
| Platform freeze constants | 3 | `FREEZE_VERSION`, `FREEZE_DATE`, `BOOTSTRAP_VERSION` |
| Core Trading Platform module-scope constants | 1,063+ | Per F3 Core audit |
| Core Trading Platform enums | 396 | Per F3 Core audit |

### 7.4 Test Inventory

| Suite | Tests | Status |
|---|---|---|
| A1–A10 AI module tests | 1,607 | ✅ 1,607 PASS |
| Platform Bootstrap (F0.1) | 107 | ✅ 107 PASS |
| F4 Operational Readiness | 82 | ✅ 82 PASS |
| **AI Platform Total** | **1,796** | **✅ 1,796 PASS** |
| Core Trading Platform (C9–C16) | 10,855 | ✅ 10,855 PASS |
| **Grand Total** | **12,651** | **✅ 12,651 PASS** |

Test command (AI Platform): `.\.venv\Scripts\python.exe -m pytest tests\ai\ -q --tb=short`

### 7.5 Deployment

| Environment | Status |
|---|---|
| Local (Python 3.14.3, Windows) | ✅ All tests passing |
| GitHub `main` branch | ✅ Pushed |
| VPS `root@178.18.252.24` | ✅ Both containers `Up (healthy)` |

---

## 8. Certification History

### Core Trading Platform

| Phase | Name | Score | Decision | Commit |
|---|---|---|---|---|
| **F1** | Architecture Audit | 8.8 / 10 | PASS WITH OBSERVATIONS | `bff57eb` |
| **F2** | Architecture Standardization | — | PASS | `77858a7` |
| **F3** | Interface & Contract Freeze | — | PASS | `686a06c` |

### AI Platform

| Phase | Name | Score | Decision | Commit |
|---|---|---|---|---|
| **F0** | Enterprise Design Review | 7.9 / 10 | CERTIFIED WITH OBSERVATIONS | — |
| **F0.1** | Critical Architecture Resolution | — | COMPLETE | `fdfe6d6` |
| **F1** | Architecture Audit | 8.3 / 10 | PASS WITH OBSERVATIONS | `88e8de3` |
| **F2** | AI Platform Standardization | — | COMPLETE | `729659a` |
| **F3** | Interface & Contract Freeze | — | PASS | `8203fa5` |
| **F4** | Operational Readiness Validation | 9.8 / 10 | READY FOR RELEASE | `9812e2f` |
| **F5** | Release Certification | — | **ENTERPRISE CERTIFIED** | `9812e2f` |

### Phase Summaries (AI Platform)

**F0 — Enterprise Design Review**  
Independent design review. Identified three critical blockers (R-001: no bootstrap,
R-004: no lifecycle mixin, R-007: no health aggregation) plus seven deferred
observations. Score 7.9/10. Authorized conditional proceed to F0.1.

**F0.1 — Critical Architecture Resolution**  
Resolved all three F0 blockers. Delivered `iios.ai.platform` bootstrap with
`IIOSBootstrap`, `PlatformRegistry`, `StartupCoordinator`, `ShutdownCoordinator`,
`HealthCoordinator`, `LifecycleManager`. Added 107 tests. All 1714 tests passing.

**F1 — Architecture Audit**  
Full structural audit. Confirmed star topology (zero cross-imports between A2–A10).
Identified 8 exception namespace collisions (expanded from 5 in F0) and 4 gateways
missing `VERSION` constants. Authorized proceed to F2. Score 8.3/10.

**F2 — AI Platform Standardization**  
Five tasks completed: exception namespace collisions resolved (232 canonical names,
8 deprecated aliases), metadata constants backfilled to all 10 gateways, `taken_at`
→ `captured_at` migration on A2/A3/A4/A5 snapshots, `GatewayProtocol` added,
M2 layer mapping confirmed. Zero architecture changes.

**F3 — Interface & Contract Freeze**  
206 gateway methods + 70 constants + 14 snapshots + ~80 exceptions formally frozen
at Version 1.0.0. Two missing return-type annotations in A7 corrected. All 10
modules declared `__version__ = "1.0.0"`. Platform freeze constants declared.
4 non-blocking observations logged.

**F4 — Operational Readiness Validation**  
82-test suite across 7 dimensions: lifecycle (15), end-to-end (12), recovery (10),
observability (14), backward compatibility (16), performance (8), regression (7).
All 82 pass. Score 9.8/10. Performance thresholds exceeded by ≥100× margin.
1 LOW observation (F4-OBS-001) carried to deferred items.

**F5 — Release Certification**  
Final governance gate. Confirmed all F0–F4 phases complete. Verified 1796/1796 tests.
Zero CRITICAL/HIGH open findings. Published three certification documents:
`AI_PLATFORM_V1_RELEASE.md`, `PUBLIC_API_MANIFEST_V1.md`, `AI_PLATFORM_V1_DEFERRED_ITEMS.md`.
Decision: **ENTERPRISE CERTIFIED**.

---

## 9. Versioning Policy

IIOS Version 1.0 follows strict semantic versioning. All three platforms (Core Trading,
AI, Platform Bootstrap) must be versioned consistently.

### Patch — 1.0.x

Permitted changes:
- Bug fixes that do not alter any public interface signature
- Performance improvements with identical external behavior
- Documentation corrections
- Dependency version updates (compatible)
- New exception subclasses that extend (not replace) existing ones

Not permitted:
- New public methods on any gateway
- New parameters on existing methods
- New snapshot fields
- Removal or rename of any public symbol

Governance: No F-phase required. Fix, test, deploy.

### Minor — 1.x.0

Permitted changes:
- New additive public methods on existing gateways
- New optional parameters with defaults on existing methods
- New snapshot types (additive)
- New exception classes (additive)
- New modules (additive)
- Deprecation warnings on symbols targeted for v2.0 removal

Not permitted:
- Removal of any existing public method, parameter, or type
- Change to any existing method signature

Governance: Requires F3 interface freeze amendment. New methods must be documented
in an updated `PUBLIC_API_MANIFEST_V1.md` before merge.

### Major — 2.x.0

All breaking changes — including:
- Removal of deprecated aliases (BC-001, BC-002)
- Renaming or removing any frozen public symbol
- Changing any method signature
- Changing exception inheritance chain
- Error code renumbering (R-009)
- Architectural evolution (R-006 Platform Event Fabric)

Governance: Full F1–F5 governance cycle required for each affected platform.

---

## 10. Deferred Roadmap

**Full detail:** [AI_PLATFORM_V1_DEFERRED_ITEMS.md](AI_PLATFORM_V1_DEFERRED_ITEMS.md)

11 approved deferred items. All are non-blocking. The platform is certified for
production at Version 1.0.0 without any of these items.

| Target | Items | IDs |
|---|---|---|
| **v1.1** | 5 | R-002, R-003, F3-OBS-001, F3-OBS-003, F4-OBS-001 |
| **v2.0** | 6 | R-006, R-009, F3-OBS-002, F3-OBS-004, BC-001, BC-002 |

Key v1.1 items:
- **R-002** — Advanced Planning Engine (A10 internal upgrade; no API change)
- **R-003** — Persistent Memory cross-session backend (additive; `optional=True`)

Key v2.0 items:
- **BC-001/BC-002** — Remove deprecated exception aliases and `taken_at` properties
- **R-006** — Platform Event Fabric (cross-module eventing without violating star topology)
- **R-009** — Error code renumbering (breaking; requires major version)

---

## 11. Operational Guidelines

### Frozen Architecture

The IIOS Version 1.0 architecture is **frozen**. No module may be modified
speculatively. No public interface may be changed as a side-effect of a bug fix.
No file may be renamed or moved (breaks imports across 17+ layers).

Before touching any file answer:
1. Does this change improve correctness, performance, or architecture?
2. Does it preserve all existing public interfaces?
3. Is it the smallest change that achieves the goal?

If any answer is "no" — do not make the change.

### No Breaking API Changes

The following are **never permitted** in a patch or minor release:
- Removing a public method from any gateway
- Changing a method's parameter list (other than adding optional parameters)
- Changing a return type incompatibly
- Removing any exception class from the hierarchy
- Modifying any frozen snapshot field

### Semantic Versioning

All version bumps must follow the policy in [Section 9](#9-versioning-policy).
The version must be incremented **before** the change is merged. Commits that
change behavior without a version increment are not permitted.

### Backward Compatibility

The 8 deprecated exception aliases (BC-001) and 4 deprecated `taken_at` snapshot
properties (BC-002) are preserved at Version 1.0.x and 1.1.x. They emit
`DeprecationWarning` starting from v1.1. They are removed only in v2.0 with a
documented migration guide.

### Singleton Discipline

The following singletons must never be instantiated twice. Use the getter functions:

```python
get_feed_manager()        # data_feeds.data_feed_manager
get_performance_tracker() # learning_system.strategy_performance_tracker
get_regime_strategy_map() # meta_learning.regime_strategy_map
get_telegram_bot()        # notifications.telegram_bot
get_bus()                 # communication.event_bus
```

### Release Governance

Every code change — however small — must be followed by the mandatory deploy cycle:

```powershell
git add <files>
git commit -m "<message>"
git push origin main
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

Deploy is complete only when **both** containers show `Up … (healthy)`.

### Protected Modules

The following modules are load-bearing and may only be modified with explicit
user instruction:

| Module | Why Protected |
|---|---|
| `risk_guardian/risk_guardian.py` | Kill-switch logic — wrong edit = real money loss |
| `strategy_lab/backtesting_ai.py` | WFT/OOS quality gates are calibrated |
| `validation_engine/` | 6-stage promotion pipeline, thresholds set |
| `strategy_lab/evolved_strategies/` | Earned through evolution — not hand-written |
| `data/` directory | Live SQLite databases and persisted state |
| `data_feeds/dhan_feed.py` | Broker auth and order routing |

---

## 12. Final Declaration

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   IIOS VERSION 1.0 — OFFICIAL RELEASE DECLARATION                   ║
║                                                                      ║
║   ENTERPRISE CERTIFIED                                               ║
║                                                                      ║
║   ✅  Architecture Frozen        2026-08-01                         ║
║   ✅  Core Trading Platform      Version 1.0  Frozen  2026-07-25    ║
║   ✅  AI Platform                Version 1.0  Frozen  2026-08-01    ║
║   ✅  Platform Bootstrap         Version 1.0  Frozen  2026-08-01    ║
║                                                                      ║
║   ✅  Total Tests: 12,651 / 12,651  PASS                            ║
║   ✅  CRITICAL Findings: 0                                           ║
║   ✅  HIGH Findings: 0                                               ║
║   ✅  VPS Deployment: Both containers Up (healthy)                   ║
║                                                                      ║
║   All public interfaces are frozen at this version.                  ║
║   Breaking changes require a major version governance cycle.         ║
║   Semantic versioning applies to all future releases.                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Release Documents

| Document | Purpose |
|---|---|
| [IIOS_MASTER_ARCHITECTURE_V1.md](IIOS_MASTER_ARCHITECTURE_V1.md) | This file — single entry point for IIOS V1.0 |
| [AI_PLATFORM_V1_RELEASE.md](AI_PLATFORM_V1_RELEASE.md) | AI Platform F5 release certification |
| [PUBLIC_API_MANIFEST_V1.md](PUBLIC_API_MANIFEST_V1.md) | Complete frozen public API inventory |
| [AI_PLATFORM_V1_DEFERRED_ITEMS.md](AI_PLATFORM_V1_DEFERRED_ITEMS.md) | 11 approved deferred items |
| [CORE_TRADING_PLATFORM_V1_RELEASE.md](CORE_TRADING_PLATFORM_V1_RELEASE.md) | Core Trading Platform release |
| [AI_PLATFORM_OPERATIONAL_READINESS_REPORT_V1.md](AI_PLATFORM_OPERATIONAL_READINESS_REPORT_V1.md) | F4 validation report |
| [AI_PLATFORM_INTERFACE_FREEZE_REPORT_V1.md](AI_PLATFORM_INTERFACE_FREEZE_REPORT_V1.md) | F3 interface freeze report |
| [AI_PLATFORM_ARCHITECTURE_AUDIT_V1.md](AI_PLATFORM_ARCHITECTURE_AUDIT_V1.md) | F1 architecture audit |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Core Trading Platform internal architecture detail |

---

*IIOS Version 1.0 — Certified 2026-08-01*  
*Architecture frozen. No breaking changes without a formal governance cycle.*
