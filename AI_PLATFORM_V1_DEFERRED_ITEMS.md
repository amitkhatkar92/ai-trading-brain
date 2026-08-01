# AI Platform Version 1.0 — Deferred Items

**Document:** AI_PLATFORM_V1_DEFERRED_ITEMS  
**Version:** 1.0.0  
**Date:** 2026-08-01  
**Status:** Approved deferred work only — no implementation required

This document records all items explicitly deferred from the Version 1.0 release.
Items are organized by severity and target release. None of these items are release
blockers. All were reviewed and approved as deferred during the F0–F5 governance
lifecycle.

---

## Deferred Item Classification

| Priority | Target | Description |
|---|---|---|
| MEDIUM | v1.1 | Significant feature gap, workaround exists |
| LOW | v1.1 | Minor improvement, current behavior acceptable |
| LOW | v2.0 | Architecture-level change requiring major planning |
| INFO | v2.0 | Informational inconsistency, no operational impact |
| BC | v2.0 | Backward-compat cleanup (never in a patch release) |

---

## Version 1.1 Deferred Items

### R-002 — Advanced Planning Engine

| Field | Value |
|---|---|
| **ID** | R-002 |
| **Source** | F0 Enterprise Design Review |
| **Severity** | MEDIUM |
| **Target** | v1.1 |
| **Module** | A10 — Orchestration |
| **Error Range** | AI-1520 (`AIPlanningException` family) |

**Description:**  
The current `OrchestratorGateway.generate_plan()` produces execution plans from
objective strings using a basic planning algorithm. A dedicated Advanced Planning
Engine with constraint satisfaction, multi-step lookahead, and plan quality scoring
was identified in the F0 review as a medium-term need.

**Current State:**  
`generate_plan()` → `ExecutionPlan` is frozen and functional. The planning algorithm
is internal to A10 and can be upgraded without changing the public API.

**v1.1 Scope:**  
- Upgrade internal planning algorithm (no public API change required)
- Add `PlanQualityScore` to `ExecutionPlan` type (additive)
- Introduce `AIPlanningStrategyError` (new exception, additive)

---

### R-003 — Persistent Memory (Cross-Session)

| Field | Value |
|---|---|
| **ID** | R-003 |
| **Source** | F0 Enterprise Design Review |
| **Severity** | MEDIUM |
| **Target** | v1.1 |
| **Module** | A4 — Memory & Knowledge |
| **Relevant Methods** | `store_memory(scope=MemoryScope.SESSION)` |

**Description:**  
`MemoryKnowledgeGateway` supports `MemoryScope.SESSION` memory entries. Cross-session
memory persistence (e.g., persisting agent observations across restart) was deferred
because it requires a storage backend contract that was not in scope for v1.0.

**Current State:**  
In-process memory storage. `evict_expired_memory()` handles TTL-based eviction. The
`MemoryScope` enum includes scopes beyond SESSION but persistence is runtime-only.

**v1.1 Scope:**  
- Add `MemoryPersistenceBackend` protocol (additive)
- Add optional `backend` parameter to `MemoryKnowledgeGateway.__init__` (backward-compatible default `None`)
- Introduce new `MemoryScope.PERSISTENT` value
- Storage backend implementations are external (not part of the platform public API)

---

### F3-OBS-001 — A2/A3 `.container` Property Exposes Internal DI Root

| Field | Value |
|---|---|
| **ID** | F3-OBS-001 |
| **Source** | F3 Interface & Contract Freeze |
| **Severity** | LOW |
| **Target** | v1.1 |
| **Modules** | A2 — Model Management, A3 — Prompt & Context |

**Description:**  
`ModelManagementGateway.container` and `PromptContextGateway.container` expose the
internal `ModelManagementContainer` and `PromptContextContainer` dependency injection
roots as public `@property` accessors. These were intentional for testing convenience
but expose internal wiring.

**Current State:**  
Properties exist and are documented in `PUBLIC_API_MANIFEST_V1.md` with the
`[F3-OBS-001]` annotation. They are frozen at v1.0 and will not be removed until v1.1
with a formal deprecation warning.

**v1.1 Scope:**  
- Add `@deprecated` warning to `.container` properties on A2 and A3
- v2.0: Remove properties entirely

---

### F3-OBS-003 — A7 `list_sessions()` Loose Return Type

| Field | Value |
|---|---|
| **ID** | F3-OBS-003 |
| **Source** | F3 Interface & Contract Freeze |
| **Severity** | LOW |
| **Target** | v1.1 |
| **Module** | A7 — Learning & Evaluation |
| **Method** | `LearningEvaluationGateway.list_sessions()` |

**Description:**  
`list_sessions(status: Optional[EvaluationStatus] = None) -> list` returns an
untyped `list` rather than `List[EvaluationSession]`. This is a weak type signal
for static analysis tooling (Pylance, mypy). No runtime impact.

**Current State:**  
Method is frozen as `-> list` per the F3 interface freeze. The actual return value
contains `EvaluationSession` objects.

**v1.1 Scope:**  
- Change return type annotation to `List[EvaluationSession]` (non-breaking — additive specificity)
- This is the only annotation change permitted as a patch in v1.0.x because it is additive and non-breaking

---

### F4-OBS-001 — HealthCoordinator Optional/Required Distinction

| Field | Value |
|---|---|
| **ID** | F4-OBS-001 |
| **Source** | F4 Operational Readiness Validation |
| **Severity** | LOW |
| **Target** | v1.1 |
| **Module** | Platform Bootstrap — `HealthCoordinator` |

**Description:**  
`HealthCoordinator` returns `HEALTH_DOWN` for any platform in FAILED phase,
regardless of whether it was declared `optional=True`. Operators monitoring the
aggregate health string cannot distinguish "optional module down" from "required
module down" without inspecting the per-platform `platforms` sub-dict.

**Current State:**  
The `platforms` dict in `bootstrap.health()` includes `phase` per platform entry.
Consumers requiring the distinction can read `phase` from the per-platform report.

**v1.1 Scope:**  
- Add `"optional": bool` key to per-platform health dict entries in `HealthCoordinator._check_one()`
- No change to aggregate logic
- Additive — no breaking change

---

## Version 2.0 Deferred Items

### R-006 — Platform Event Fabric (Cross-Module Eventing)

| Field | Value |
|---|---|
| **ID** | R-006 |
| **Source** | F0 Enterprise Design Review |
| **Severity** | LOW |
| **Target** | v2.0 |

**Description:**  
Each module (A1–A10) has its own internal event bus (e.g., `AIEventBus` in A1,
`ModelEventBus` in A2, `PromptEventBus` in A3). There is no cross-module event
fabric — modules cannot subscribe to events from other modules without violating
the star-topology isolation rule (A2–A10 depend on A1 only).

**Current State:**  
Module-level event buses are internal. A1's `AIEventBus` is the only shared event
infrastructure. Cross-module event propagation is not supported in v1.0.

**v2.0 Scope:**  
- Design a platform-level `PlatformEventBus` in `iios.ai.platform`
- All module gateways register as publishers/subscribers via the bootstrap
- Preserve star topology: modules never import from each other
- This is a new capability; no v1.0 public APIs change

---

### R-009 — Error Code Range Review & Consolidation

| Field | Value |
|---|---|
| **ID** | R-009 |
| **Source** | F0 Enterprise Design Review |
| **Severity** | LOW |
| **Target** | v2.0 |

**Description:**  
The current error code scheme (AI-000 through AI-1563) has some inconsistencies:
- A2 (AI-850) and A3 (AI-800) have lower codes than A1 (AI-000–AI-702), breaking
  numeric ordering
- A5 (AI-1000) starts with a round number; some ranges have gaps

**Current State:**  
All 232 error codes are frozen at v1.0 and must not change in any v1.x release.
Consumer code catches exceptions by class name, not code, so the inconsistency is
cosmetic.

**v2.0 Scope:**  
- Renumber all error codes to follow module order (A1=100x, A2=200x, A3=300x, ...)
- Requires major version bump because existing code that catches by numeric code would break
- Full backward-compat migration guide required

---

### F3-OBS-002 — Snapshot Factory Naming Inconsistency

| Field | Value |
|---|---|
| **ID** | F3-OBS-002 |
| **Source** | F3 Interface & Contract Freeze |
| **Severity** | INFO |
| **Target** | v2.0 |

**Description:**  
Snapshot types use three different factory/construction patterns across modules:
- `create(...)` — used by most platform types
- `capture(...)` — used by some domain snapshots
- Direct `@dataclass` construction — used by others

The inconsistency is purely internal (snapshot construction is not part of the public
gateway API). `gateway.snapshot()` is the only public call.

**v2.0 Scope:**  
- Standardize all snapshot factories to `create(...)` naming
- Internal change only; no public API impact

---

### F3-OBS-004 — A1 `FoundationSnapshot.timestamp` Naming

| Field | Value |
|---|---|
| **ID** | F3-OBS-004 |
| **Source** | F3 Interface & Contract Freeze |
| **Severity** | INFO |
| **Target** | v2.0 |

**Description:**  
`FoundationSnapshot` (A1) uses a field named `timestamp` for the capture time.
All other module snapshots (A2–A10) use `captured_at: float`. This is the only
deviation from the platform-standard naming.

**Current State:**  
`FoundationSnapshot.timestamp` is frozen at v1.0. Changing it is a breaking change
to the snapshot contract.

**v2.0 Scope:**  
- Rename `FoundationSnapshot.timestamp` → `captured_at`
- Add deprecated `@property timestamp` wrapping `captured_at` for one release
- Remove `timestamp` property in v2.1+

---

## Version 2.0 — Backward Compatibility Cleanup

### BC-001 — Remove Deprecated Exception Aliases

| Field | Value |
|---|---|
| **ID** | BC-001 |
| **Source** | F2 Standardization |
| **Target** | v2.0 |

**Description:**  
Eight exception aliases were introduced in F2 as backward-compatibility shims for
renamed exceptions. These are deprecated and should be removed in v2.0.

**Aliases to remove:**

| Alias | Points To | Module |
|---|---|---|
| `AIPermissionException` | `AIAgentPermissionException` | A5 |
| `AIPermissionDeniedError` | `AIAgentPermissionDeniedError` | A5 |
| `AIRoleNotFoundError` | `AIAgentRoleNotFoundError` | A5 |
| `AIPolicyException` | `AIAgentPolicyException` | A5 |
| `AIPolicyViolationError` | `AIGovernanceRuleViolationError` | A8 |
| `AITaskNotFoundError` | `AISchedulerTaskNotFoundError` | A10 |
| `AITaskExecutionError` | `AISchedulerTaskExecutionError` | A10 |
| `AIValidationException` | `AIQualityValidationException` | A7 |

**v2.0 Action:**  
- Add `DeprecationWarning` to alias definitions in v1.1
- Remove aliases entirely in v2.0
- Requires documentation of migration path

---

### BC-002 — Remove Deprecated `taken_at` Snapshot Properties

| Field | Value |
|---|---|
| **ID** | BC-002 |
| **Source** | F2 Standardization |
| **Target** | v2.0 |

**Description:**  
Four snapshot classes retain a deprecated `@property taken_at` wrapping `captured_at`.
These were added in F2 to preserve backward compatibility for consumers using the
old field name.

**Properties to remove:**

| Snapshot | Property |
|---|---|
| `ModelManagementSnapshot` | `taken_at` (→ `captured_at`) |
| `PromptContextSnapshot` | `taken_at` (→ `captured_at`) |
| `MemoryKnowledgeSnapshot` | `taken_at` (→ `captured_at`) |
| `AgentFrameworkSnapshot` | `taken_at` (→ `captured_at`) |

**v2.0 Action:**  
- Add `DeprecationWarning` to `taken_at` properties in v1.1
- Remove `taken_at` properties in v2.0

---

## Summary Table

| ID | Source | Description | Severity | Target |
|---|---|---|---|---|
| R-002 | F0 | Advanced Planning Engine | MEDIUM | v1.1 |
| R-003 | F0 | Persistent Memory (cross-session) | MEDIUM | v1.1 |
| F3-OBS-001 | F3 | A2/A3 `.container` property deprecation | LOW | v1.1 |
| F3-OBS-003 | F3 | A7 `list_sessions()` loose return type | LOW | v1.1 |
| F4-OBS-001 | F4 | HealthCoordinator optional/required distinction | LOW | v1.1 |
| R-006 | F0 | Platform Event Fabric | LOW | v2.0 |
| R-009 | F0 | Error Code Range Review | LOW | v2.0 |
| F3-OBS-002 | F3 | Snapshot factory naming inconsistency | INFO | v2.0 |
| F3-OBS-004 | F3 | A1 `FoundationSnapshot.timestamp` naming | INFO | v2.0 |
| BC-001 | F2 | Remove deprecated exception aliases | — | v2.0 |
| BC-002 | F2 | Remove deprecated `taken_at` properties | — | v2.0 |

**Total deferred items: 11**  
**v1.1 items: 5** (R-002, R-003, F3-OBS-001, F3-OBS-003, F4-OBS-001)  
**v2.0 items: 6** (R-006, R-009, F3-OBS-002, F3-OBS-004, BC-001, BC-002)

---

*No deferred item requires implementation before Version 1.0.0 release.*  
*All items are non-blocking. The platform is certified for production at Version 1.0.0.*

*Generated: 2026-08-01 | Governance phase: F5 Release Certification*
