# IIOS AI Platform — Phase 3 Architecture Review

**Document Type:** Architecture Review  
**Review Target:** `PHASE3_AI_PLATFORM_ARCHITECTURE.md`  
**Phase:** 3 — AI Platform  
**Date:** 2026-07-27  
**Reviewer:** AI Architecture Review Agent  
**Predecessor Reviews:** F1 (`bff57eb`), F2 (`77858a7`), F3 (`686a06c`) — Core Platform  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Module Review](#2-module-review)
3. [Dependency Review](#3-dependency-review)
4. [Layer Review](#4-layer-review)
5. [Enterprise Design Assessment](#5-enterprise-design-assessment)
6. [Risks and Recommendations](#6-risks-and-recommendations)
7. [Final Architecture Score](#7-final-architecture-score)
8. [Final Result](#8-final-result)

---

## 1. Executive Summary

The Phase 3 AI Platform architecture specification proposes a ten-module enterprise AI layer (A1–A10) that consumes the frozen Core Trading Platform V1.0 exclusively through published M6 gateway interfaces. The architecture inherits the Core Platform's proven M1–M6 six-layer standard and extends it with AI-native concerns: provider abstraction, token management, prompt governance, multi-tier memory, agent reasoning, multi-agent collaboration, learning, governance, tool execution, and top-level orchestration.

**Overall assessment:** The architecture is coherent, well-structured, and correctly isolated from the Core Platform. The dependency graph is acyclic, the module boundaries are justified, and the governance architecture (A8) is appropriately positioned as a mandatory gate between AI outputs and Core Platform gateways.

**Seven observations** are documented below. None require a redesign. Two require clarification before A1 implementation begins. Five are recommendations to strengthen the specification before the full build commences. All are addressable through targeted additions to the existing document.

| Category | Count |
|---|---|
| Blocking issues | 0 |
| Clarifications required before A1 | 2 |
| Recommendations (strengthen spec) | 5 |
| Informational observations | 3 |

---

## 2. Module Review

### 2.1 A1 — AI Foundation

**Verdict: ✅ PASS**

Responsibilities are correctly scoped to infrastructure concerns: provider abstraction, base DTOs, exception hierarchy, token management, rate limiting, retry, lifecycle mixin, and event bus base. All are platform-wide and appropriately housed in A1.

**Observation (informational):** A1 includes both *infrastructure* concerns (rate limiting, retry, logging) and *framework* concerns (`AILifecycleAwareMixin`). This dual role is intentional and acceptable for a foundation module — the lifecycle mixin must be in A1 so all other modules can inherit without creating inter-module imports at the M1 level. No change required.

**Observation (informational):** The `AIEventBus` base class is declared in A1. This is correct — every module's internal event bus inherits from it. However, the architecture does not define a *cross-module* AI Platform event bus. The mechanism by which A2 receives quality-routing recommendations from A7 (see Section 3) should be documented as an A1-owned AI Platform event bus, not a per-module bus. This is addressed under O-002.

### 2.2 A2 — Model Management

**Verdict: ✅ PASS WITH OBSERVATION**

Responsibilities are cleanly scoped: registry, routing, versioning, fallback chains, circuit breakers, usage telemetry, and cost accounting. These are all model-management concerns with no overlap into other modules.

**Observation (clarification — see O-001):** Section 4 states A2 enables "A/B routing for model evaluation experiments (coordinated with A7)." A7 depends on A2. If A2 also calls A7 to receive routing decisions, this creates a circular dependency. The dependency table for A2 does not list A7, implying the coordination is event-driven (A7 publishes routing recommendations; A2 consumes them through the platform event bus). This assumption must be made explicit in the specification before implementation begins.

### 2.3 A3 — Prompt & Context Platform

**Verdict: ✅ PASS WITH CLARIFICATION**

Responsibilities are clearly scoped: template management, context assembly, budget enforcement, injection defence, schema validation, multi-turn management, and prompt versioning.

**Observation (clarification — see O-002):** The responsibilities section states A3 assembles context "from multiple sources: Core Platform snapshots, memory (A4), tool results (A9), and inline data." However, A3's dependency table lists only A1, A2, and C14 — it does not list A4 or A9. If A3 pulls directly from A4 or A9, this creates a circular dependency: A4 depends on A3; A9 depends on A1/A2 only but A5 depends on both A3 and A9. The correct interpretation — that A3 receives pre-fetched context blocks as *parameters* rather than pulling them from A4/A9 directly — must be made explicit. A3 is a context *assembler*, not a context *fetcher*.

### 2.4 A4 — Memory & Knowledge Platform

**Verdict: ✅ PASS WITH OBSERVATION**

Four-tier memory (working, episodic, semantic, procedural) is a standard and comprehensive AI memory model. The integration with C14 Knowledge for durable storage is correctly positioned through the M6 gateway.

**Observation (risk — see R-003):** The semantic memory tier requires a vector similarity search capability. The specification delegates durable storage to C14 Knowledge (M6 gateway) but does not specify whether C14's gateway exposes vector search APIs sufficient for AI agent memory retrieval. C14 was designed for the Core Platform's knowledge management, not as an AI vector store. A4's M4 retrieval layer must clarify whether it maintains an embedded vector index internally (e.g., as part of its own M4 `retrieval/` framework) and uses C14 only for persistence, or whether it assumes C14 exposes a sufficiently capable vector search interface.

### 2.5 A5 — AI Agent Framework

**Verdict: ✅ PASS**

Responsibilities are well-scoped to single-agent concerns: lifecycle state machine, reasoning loops (ReAct, CoT, ToT, Plan-and-Execute), tool invocation, resource budgets, reasoning traces, goal management, and agent registry. The reasoning patterns are the correct ones for enterprise AI.

The A5 dependency on A9 (Tool/Skill, higher-numbered) is explicitly documented as an exception to the module ordering rule, and the implementation roadmap correctly builds A9 before A5 to respect the actual dependency direction. This is sound.

### 2.6 A6 — Multi-Agent Collaboration

**Verdict: ✅ PASS**

Responsibilities are correctly scoped to multi-agent coordination: debate, consensus, delegation, parallel investigation, conflict resolution, and ensemble budgets. No overlap with A5 (single agent) or A10 (workflow orchestration).

**Observation (informational):** A6 lists only C9 (Decision Governance) as a Core Platform dependency. During a collaboration session analysing a trading scenario, agents within the ensemble already have access to C9, C11, and C12 through their individual A5 instances. A6 does not need to independently access those gateways — it consumes aggregate agent outputs. This is architecturally clean and correct. No change required.

### 2.7 A7 — Learning & Evaluation

**Verdict: ✅ PASS WITH OBSERVATION**

Responsibilities are correctly scoped: output evaluation, agent performance tracking, experiment management, quality degradation detection, improvement recommendations, and ground truth management.

**Observation (gap — see O-003):** A7 manages "versioned reference dataset management for evaluation" and must persist evaluation results over time. The module's dependency table does not include C14 Knowledge or any persistent storage. All other persistence-heavy AI modules (A4) route to C14 via M6 gateway. A7 should either declare a C14 dependency for evaluation dataset and result persistence, or explicitly state that it maintains its own storage within its M4 `evaluation/` layer with a documented retention policy.

### 2.8 A8 — AI Governance

**Verdict: ✅ PASS**

The governance architecture is comprehensive and correctly positioned. The `GovernanceVerdictDTO` as a mandatory wrapper on every AI output before Core Platform submission is an excellent architectural pattern — it makes governance enforcement structurally impossible to bypass, not just a convention.

**Observation (risk — see R-001):** The content safety pipeline includes "regex → embedding-based → LLM judge" as three sequential layers. The LLM-judge step adds model latency and token cost to every AI output. For time-sensitive trading scenarios this will be a measurable latency concern. The specification should define a tiered governance policy (fast-path vs. full-path) configurable per output type or urgency level.

### 2.9 A9 — Tool & Skill Platform

**Verdict: ✅ PASS**

Responsibilities are cleanly scoped: tool registry, skill registry, sandboxed execution, schema validation, capability discovery, result caching, and telemetry. The built-in tool categories (Core Platform readers, knowledge tools, data transformation, calculation, formatting) are appropriate and complete for V1.0.

**Observation (informational):** A9 sandboxes tool execution with "resource limits (CPU, memory, time) and isolation from Core Platform internals." The mechanism for this isolation is an implementation concern, not an architecture concern, and is correctly left to the implementation phase. However, the specification should note that Core Platform reader tools (which call C10/C11/C12/C14 M6 gateways) execute in a controlled context where the M6 gateway references are injected at sandbox construction time, not imported freely inside tool execution code.

### 2.10 A10 — AI Orchestration

**Verdict: ✅ PASS WITH OBSERVATION**

Responsibilities are correctly scoped to top-level orchestration: workflow definition, event-triggered execution, resource scheduling, governance gating, workflow versioning, status/health, and Core Platform integration.

**Observation (risk — see R-002):** The specification describes A10 as providing a "declarative AI workflow DSL." Designing and implementing a DSL (even a simple one) is a non-trivial undertaking that can introduce significant complexity and scope creep. A workflow *configuration schema* (structured YAML or JSON with a formal schema definition) achieves the same goal with far lower implementation risk. The relationship between A10's workflow definition format and C16's existing workflow primitives (checkpoint, compensation, conditional, parallel, sequential engines) should also be clarified — A10 should compose to C16 primitives, not replace them.

### 2.11 Overlap and Missing Capability Assessment

**No functional overlap detected** between any pair of modules. The responsibility boundaries are clean:
- Model identity/routing: A2 only
- Prompt construction: A3 only
- Memory storage/retrieval: A4 only
- Single-agent reasoning: A5 only
- Multi-agent coordination: A6 only
- Evaluation and learning: A7 only
- Governance and safety: A8 only
- Tool execution: A9 only
- Workflow orchestration: A10 only

**One missing enterprise AI capability identified:**

**Configuration Management** is not explicitly addressed. Provider API keys, model endpoint URLs, token budget limits, rate limits, and governance thresholds are configuration data. The success criteria note "no hardcoded provider keys" but do not define where this configuration lives or how it propagates to modules at runtime. This should be addressed in A1 Foundation as a structured `AIConfiguration` and `AIConfigurationProvider` (see O-004).

---

## 3. Dependency Review

### 3.1 Explicit Dependency Graph

The complete dependency graph derived from all ten module dependency tables:

```
A1:  iios.common.logging, iios.common.errors
A2:  A1
A3:  A1, A2, C14
A4:  A1, A2, A3, C14
A5:  A1, A2, A3, A4, A9, C9, C11, C12
A6:  A1, A4, A5, C9
A7:  A1, A2, A5, A6, C13
A8:  A1, A5, A6, A7, C9, C11, C13
A9:  A1, A2, C10, C11, C12, C14
A10: A1, A2, A3, A4, A5, A6, A7, A8, A9, C9, C15, C16
```

### 3.2 Circular Dependency Check

**Result: No circular dependencies detected in the explicit dependency tables.**

Topological ordering of AI modules (all satisfied):

```
Level 0: A1
Level 1: A2
Level 2: A3, A9   ← A9 depends only on A1, A2; A3 depends on A1, A2, C14
Level 3: A4       ← depends on A1, A2, A3
Level 4: A5       ← depends on A1–A4, A9
Level 5: A6       ← depends on A1, A4, A5
Level 6: A7       ← depends on A1, A2, A5, A6
Level 7: A8       ← depends on A1, A5, A6, A7
Level 8: A10      ← depends on A1–A9
```

No module appears at a level lower than its declared dependency.

### 3.3 A9 Peer Dependency Exception

A5 (level 4) depends on A9 (level 2). The module number of A9 is higher (9 > 5) but its dependency level is lower (2 < 4). Rule R-IM-01 explicitly documents this as the single authorised exception. The implementation roadmap correctly builds A9 before A5. This is sound.

### 3.4 A2/A7 Coordination — Potential Implicit Cycle

**Observation O-001 (clarification required):**

The A2 specification states it "enables A/B routing for model evaluation experiments (coordinated with A7)." A7 depends on A2. If A2 were to call A7 to receive routing recommendations, this would create a cycle:

```
A2 → A7 → A2  (CIRCULAR — PROHIBITED)
```

A2's dependency table does not list A7, correctly implying this is event-driven:

```
A7 publishes routing recommendations → AI Platform event bus → A2 subscribes
```

This is the correct and safe design. However, the current specification does not make this explicit — it only says "coordinated with." Before A2 implementation begins, the specification must state explicitly: *A2 receives model quality feedback from A7 exclusively through the AI Platform event bus. A2 never calls A7's M6 gateway.*

### 3.5 A3 Context Sources — Potential Implicit Cycle

**Observation O-002 (clarification required):**

A3 describes assembling context from "memory (A4), tool results (A9)." A4 depends on A3, creating the potential cycle:

```
A3 → A4 → A3  (CIRCULAR — PROHIBITED)
A3 → A9 → ...  (A9 does not depend on A3, but A5 depends on both A3 and A9)
```

A3's dependency table correctly excludes A4 and A9. The intent is that A3 receives pre-fetched data *as parameters*:

```python
# CORRECT: Context assembly receives data as parameters
context = context_assembler.build(
    snapshot=risk_snapshot,        # fetched by caller before A3 call
    memory_items=memory_results,   # fetched by A4 before A3 call
    tool_outputs=tool_results,     # fetched by A9 before A3 call
)

# PROHIBITED: Context assembly fetching its own data
context = context_assembler.build(goal=goal)  # A3 would need to call A4/A9 internally
```

The specification must state this explicitly in the A3 responsibilities section to prevent implementers from introducing the circular dependency.

### 3.6 Dependency Direction — AI Platform → Core Platform

**Result: ✅ All 19 dependency rules (R-IL-01 through R-PA-03) are consistent with the specification.**

Every Core Platform dependency listed in the module tables references an M6 gateway package:
- `iios.decision.integration` (C9) ✅
- `iios.portfolio.integration` (C10) ✅
- `iios.risk.integration` (C11) ✅
- `iios.market.integration` (C12) ✅
- `iios.supervisor.integration` (C13) ✅
- `iios.knowledge.integration` (C14) ✅
- `iios.integration.gateway` (C15) ✅
- `iios.workflow.gateway` (C16) ✅

No Core Platform module is listed as depending on any AI module. The isolation is correctly specified.

---

## 4. Layer Review

### 4.1 M1–M6 Appropriateness for AI Modules

The six-layer standard established by Core Platform Gen 2 (C9–C16) is appropriate for all ten AI modules. The pattern enforces:

- **Lifecycle isolation** — every module has a predictable operational state machine
- **Policy separation** — governance rules are independently versioned and testable, not hardcoded in engine logic
- **Snapshot immutability** — point-in-time state is captured in frozen dataclasses, enabling deterministic replay
- **Gateway encapsulation** — no consumer reaches into module internals

All ten modules have AI-specific domain work that maps naturally to M4:

| Module | M4 Layer | Domain Work |
|---|---|---|
| A1 | `adapters/` | Provider-specific API adapters |
| A2 | `routing/` | Capability routing, fallback chains |
| A3 | `assembly/` | Context window construction |
| A4 | `retrieval/` | Vector similarity search, memory consolidation |
| A5 | `reasoning/` | ReAct/CoT/ToT/Plan-and-Execute loops |
| A6 | `coordination/` | Debate protocol, consensus strategies |
| A7 | `evaluation/` | LLM-as-judge, metrics computation |
| A8 | `enforcement/` | Safety filters, hallucination detection |
| A9 | `execution/` | Sandboxed tool invocation |
| A10 | `pipeline/` | Workflow sequencing, resource scheduling |

M4 names are correctly domain-specific (consistent with Core Platform precedent, where C9 uses `optimization/`, C11 uses `assessment/`, C13 uses `governance/`).

### 4.2 M3 Policy Fit for AI Modules

M3 is particularly important for AI modules. The policy surface for each module is well-motivated:

| Module | Example M3 Policies |
|---|---|
| A2 | Model routing policy (when to use fallback, circuit-breaker thresholds) |
| A3 | Injection defence policy, context size policy |
| A5 | Agent resource budget policy, tool allowlist policy |
| A6 | Debate round limit policy, consensus threshold policy |
| A8 | Content safety policy, hallucination threshold policy |
| A10 | Concurrent workflow policy, token quota policy |

A1 Foundation has the least natural M3 scope, but provider selection policies (e.g., regional provider routing, provider exclusion lists) are valid M3 candidates.

### 4.3 A1 M2 Engine — Lightweight But Necessary

A1's M2 engine is thinner than those in A2–A10. Its engine role is to coordinate the lifecycle of provider adapter registrations and manage the platform-wide AI event bus. This is lighter than a risk or portfolio engine but is not empty — provider registration, health monitoring of provider connections, and event bus management are valid engine responsibilities.

### 4.4 Async Execution Consideration

**Observation (informational):** The M2 engine layer in the Core Platform was designed for synchronous or thread-pool-based execution. AI modules will routinely make non-blocking model API calls (HTTP with streaming responses), which requires an async execution model. The specification does not prescribe a concurrency model, which is appropriate at the architecture level. However, the A1 Foundation engine layer should be designed with `async/await` native support from the start, as retrofitting async into a synchronous engine is expensive. This is an implementation guidance note, not an architecture defect.

### 4.5 M5 Snapshot Scope for AI Modules

AI modules produce richer state than Core Platform modules (active agents, reasoning traces, model usage counters). The M5 snapshot layer must capture this state in frozen dataclasses. Examples:

| Module | Snapshot Contents |
|---|---|
| A2 | Active model registrations, circuit-breaker states, usage counters by model |
| A5 | Agent state, goal, last reasoning step, tool call history, budget consumption |
| A6 | Active collaboration sessions, agent ensemble state, consensus progress |
| A8 | Recent governance verdicts, violation counts, pending escalations |

All of these are compatible with `@dataclass(frozen=True)` (using `tuple` instead of `list` for sequences). No architectural issue.

### 4.6 Layer Consistency Verdict

**✅ The M1–M6 standard is appropriate, feasible, and consistently applied across all ten proposed AI modules.** No module requires deviation from the standard. The module-specific M4 names are well-chosen and follow the Core Platform precedent of domain-specific layer naming.

---

## 5. Enterprise Design Assessment

### 5.1 Modularity — ✅ STRONG

Ten modules with explicit, non-overlapping responsibilities. Registry-based extension mechanisms throughout (provider registry in A2, tool registry in A9, agent registry in A5, policy registries in every M3 layer). Modules may be deployed, upgraded, or replaced independently.

### 5.2 Scalability — ✅ STRONG

Each module has independent lifecycle management, allowing horizontal scaling at the module level. A2's circuit-breaker and rate-limiter provide resilience against provider saturation. A10's resource scheduler manages platform-wide token quotas and concurrent workflow limits. No shared global state identified that would prevent scaling.

### 5.3 Extensibility — ✅ STRONG

The registry pattern (P-07) is consistently applied. New model providers are registered against `AIProvider`; new tools are registered in A9's tool registry; new governance policies are added to A8's policy chain without modifying core logic. This is the correct open/closed implementation.

### 5.4 Maintainability — ✅ STRONG

Consistent M1–M6 pattern across all ten modules means a developer familiar with one module can navigate any other. Dependency rules are explicit and numbered (R-IL-01 through R-PA-03), enabling automated enforcement. The `governance/` prefix in `iios/ai/` isolates AI Platform code from Core Platform code at the filesystem level.

### 5.5 Provider Independence — ✅ STRONG

The `AIProvider` abstract interface in A1 with all model routing through A2 is the correct implementation of P-03/P-04. No module below A2 should hold a direct provider reference — this is correctly enforced by the M6 boundary rule.

### 5.6 Security — ✅ STRONG

Prompt injection defence at A3 (the construction point), sandboxed execution at A9 (the execution point), and governance filtering at A8 (the output point) create a three-layer security perimeter. The prohibition on embedding credentials in prompts is explicitly stated in P-10.

**One gap (O-004):** Configuration management for provider credentials is not explicitly defined. Without a structured `AIConfiguration` provider in A1, implementers may embed credentials in environment-variable reads scattered across modules, making rotation and auditing difficult.

### 5.7 Observability — ✅ STRONG

Structured telemetry declared at every operation point (P-09): model selection, token usage, tool calls, governance verdicts, agent state transitions. All emitted as events through the AI Platform event bus, compatible with the Core Platform's observability infrastructure.

### 5.8 Explainability — ✅ STRONG

A8's `GovernanceVerdictDTO` as a mandatory first-class output is an excellent design choice. Reasoning traces from A5 are structured outputs, not log text. Prompt versioning in A3 ensures every output can be traced back to the exact template that produced it. This is enterprise-grade explainability.

### 5.9 Testability — ✅ STRONG

The `AIProvider` interface is mock-able (P-08). Seedable random sources and injectable clocks are called out explicitly. Model responses in tests are always mocked. The M6 gateway boundary provides natural mock injection points.

### 5.10 Future Extensibility — ✅ STRONG

The architecture is designed for the decade, not just for the immediate implementation. The A/B experiment infrastructure (A7), the model fallback chain (A2), and the modular governance policy registry (A8) all support evolution without redesign. The version strategy mirrors the Core Platform's proven F1→F2→F3→V1.0 freeze cycle.

### 5.11 Resilience — ⚠️ PARTIAL

Resilience is partially addressed: circuit breakers in A2, retry logic in A1. However, the architecture does not define behaviour when **all** model providers are unavailable simultaneously. Should the AI Platform:
(a) Queue AI workflow requests until providers recover,
(b) Return structured "degraded" responses indicating AI unavailability, or
(c) Pass control back to the Core Platform which continues operating without AI augmentation?

Option (c) is architecturally the most correct given that the Core Platform must be independently operational (R-PA-02/R-PA-03). The spec should document the AI Platform's degraded-mode behaviour explicitly (see O-005).

### 5.12 Summary Scorecard

| Principle | Score | Notes |
|---|---|---|
| Modularity | 10/10 | Clean boundaries, single responsibility per module |
| Scalability | 9/10 | Strong; no cross-module shared state identified |
| Extensibility | 9/10 | Registry pattern throughout |
| Maintainability | 9/10 | Consistent M1–M6; numbered dependency rules |
| Provider Independence | 10/10 | All routing through A2; AIProvider abstraction |
| Model Independence | 10/10 | Capability-based routing; no model assumptions |
| Security | 9/10 | Three-layer perimeter; minor config gap |
| Observability | 9/10 | Structured telemetry throughout |
| Explainability | 10/10 | Governance DTO; reasoning traces; prompt versioning |
| Testability | 9/10 | Mock-able provider; injectable dependencies |
| Resilience | 7/10 | Circuit breakers present; all-down scenario not defined |
| Future Extensibility | 9/10 | Proven freeze cycle; registry-based growth |

---

## 6. Risks and Recommendations

### R-001 — A8 Governance Gate Latency (Medium Risk)

**Risk:** A8's content safety pipeline is defined as "regex → embedding-based → LLM judge" applied to every AI output before Core Platform submission. The LLM-judge step adds model latency (typically 500ms–2s) and token cost to every operation. In time-sensitive trading scenarios — particularly intraday event-driven AI workflows triggered by market or risk events — this latency may be unacceptable.

**Recommendation:** Define a tiered governance policy in A8's M3 policy layer:

| Tier | Filters Applied | Use Case |
|---|---|---|
| FAST | Regex only | Low-risk, time-critical outputs (market summaries) |
| STANDARD | Regex + embedding | Standard AI recommendations |
| FULL | Regex + embedding + LLM judge | High-risk outputs (decision support, risk escalations) |

The governance tier is declared in the request DTO by the calling module (A5/A6/A10). A8's M3 policy engine determines the minimum required tier based on output classification. No module may self-declare a lower tier than the policy minimum.

---

### R-002 — A10 Workflow DSL Scope Risk (Medium Risk)

**Risk:** The specification defines A10 as providing a "declarative AI workflow DSL." Implementing a domain-specific language — even a minimal one — is a significant engineering undertaking. DSLs attract scope creep, require their own parser/validator, and create a maintenance burden (syntax changes, debugging tooling).

Additionally, C16 Workflow Gateway already provides a complete workflow engine (checkpoint, compensation, conditional, parallel, sequential, retry, timeout engines). A10 designing a parallel workflow representation risks duplicating C16 concepts.

**Recommendation:** Scope A10's workflow definition as a **structured workflow configuration schema** (JSON/YAML with a formal schema, not a DSL):

- AI workflows are defined as validated configuration objects, not parsed language constructs
- A10's M4 `pipeline/` layer compiles AI workflow configurations into C16 `WorkflowRequest` DTOs
- C16's workflow engine executes the result; A10 does not reimplement workflow execution
- This leverages the frozen C16 infrastructure rather than running a parallel workflow system

This reduces A10's implementation scope by 30–40% while delivering the same orchestration capability.

---

### R-003 — A4 Vector Storage Specification Gap (Medium Risk)

**Risk:** A4 Memory requires vector similarity search for semantic memory retrieval. The specification routes durable storage to C14 Knowledge (M6 gateway), but C14 was designed for the Core Platform's structured knowledge management, not as a vector database for AI agent memory. C14's M6 gateway may not expose vector-search APIs. If it does not, A4 would require an additional vector store dependency that is not documented.

**Recommendation:** Explicitly specify A4's vector storage strategy in the architecture:

**Option A (preferred):** A4's M4 `retrieval/` layer maintains an embedded vector index (e.g., in-process FAISS or equivalent) for fast similarity search. C14 Knowledge is used only for long-term persistence of serialised embeddings and memory metadata. This keeps A4 self-contained and does not require C14 to expose vector search capabilities.

**Option B:** If C14's M6 gateway is extended (under the Core Platform's additive versioning policy) to expose vector search, A4 can delegate entirely to C14. This requires a formal additive enhancement to C14's M6 gateway (permitted under V1.0 policy).

One of these options must be selected before A4 implementation begins.

---

### O-001 — A2/A7 Event Coordination Must Be Made Explicit (Clarification Required)

**Finding:** A2's specification states it "enables A/B routing for model evaluation experiments (coordinated with A7)." A7 depends on A2. If A2 also calls A7, a circular dependency results. A2's dependency table correctly excludes A7, implying event-driven coordination.

**Required addition to the specification:** Add the following to A2's responsibilities section:

> *A2 receives model quality feedback and routing recommendations from A7 exclusively through the AI Platform event bus. A2 never calls A7's M6 gateway. The coordination is: A7 publishes `ModelRoutingRecommendationEvent`; A2's engine subscribes and adjusts routing weights accordingly. This is a one-way push model — A7 produces, A2 consumes.*

---

### O-002 — A3 Context Assembly Is Parameter-Based, Not Pull-Based (Clarification Required)

**Finding:** A3 describes assembling context from "memory (A4), tool results (A9)." A3's dependency table excludes A4 and A9. The correct design (context data passed as parameters) must be stated explicitly to prevent implementers from introducing a circular import.

**Required addition to the specification:** Add the following to A3's responsibilities section:

> *A3 is a context assembler, not a context fetcher. All source data (memory items, tool outputs, Core Platform snapshots) is passed into A3's context assembly interface as pre-fetched, structured parameters by the calling module (A5, A6, or A10). A3 does not import from A4 or A9. The caller is responsible for fetching data from the appropriate modules before invoking A3.*

---

### O-003 — A7 Persistence Strategy Not Defined (Recommendation)

**Finding:** A7 manages versioned reference datasets and historical performance records over time. No persistent storage dependency is listed in A7's dependency table.

**Recommendation:** Either:
(a) Add `iios.knowledge.integration` (C14) as an A7 dependency for evaluation dataset and result persistence, consistent with the approach used by A4; or  
(b) Explicitly state that A7 maintains its own storage within its M4 `evaluation/` layer with a documented file-based or embedded-database retention strategy.

Either approach is architecturally valid. The decision must be documented before A7 implementation begins.

---

### O-004 — Configuration Management Not Addressed (Recommendation)

**Finding:** The architecture specifies "no hardcoded provider keys" in success criteria but does not define where provider credentials, model endpoint URLs, token budget limits, and rate limit configurations are managed, loaded, or distributed to modules at runtime.

**Recommendation:** Add an `AIConfiguration` capability to A1 Foundation:

- `AIConfiguration` — a frozen dataclass holding platform-wide AI configuration
- `AIConfigurationProvider` — an abstract interface for loading configuration (from environment, secrets manager, config file, etc.)
- Configuration is injected into each module's M6 gateway at initialisation time
- No module reads environment variables or file paths directly — all configuration flows through A1's `AIConfigurationProvider`

This ensures credential rotation, environment-specific overrides, and configuration auditing are centralised and testable.

---

### O-005 — Degraded-Mode Behaviour Not Defined (Recommendation)

**Finding:** The architecture defines circuit-breaker behaviour per model in A2, but does not specify the AI Platform's behaviour when all model providers are unavailable simultaneously or when A2's circuit breakers are all open.

**Recommendation:** Add a degraded-mode policy to A10 Orchestration and A2 Model Management:

> *When no model provider is available (all circuit breakers open or all providers returning errors), the AI Platform enters DEGRADED mode:*  
> *— A10 halts new AI workflow submissions and returns a structured `AIUnavailableResponse` to callers*  
> *— Active AI workflows are checkpointed and suspended (not failed)*  
> *— The AI Platform emits an `AIPlatformDegradedEvent` to all subscribed components*  
> *— The Core Platform continues operating without AI augmentation (per R-PA-02/R-PA-03)*  
> *— When at least one provider recovers, A2 emits an `AIPlatformRestoredEvent` and A10 resumes suspended workflows*

This is consistent with the Core Platform's resilience model (C7 Execution Recovery) and with R-PA-03 ("AI Platform failure does not cause Core Platform failure").

---

### Summary of All Observations

| ID | Type | Module(s) | Action Required |
|---|---|---|---|
| O-001 | Clarification | A2, A7 | Add explicit event-driven coordination statement to A2 spec before A2 implementation |
| O-002 | Clarification | A3 | Add explicit "parameter-based, not pull-based" statement to A3 spec before A3 implementation |
| R-001 | Risk | A8 | Define tiered governance policy (FAST/STANDARD/FULL) in A8 M3 spec |
| R-002 | Risk | A10 | Replace "DSL" with "workflow configuration schema"; define compilation to C16 primitives |
| R-003 | Risk | A4 | Specify vector storage strategy (embedded index vs. C14 extension) before A4 implementation |
| O-003 | Recommendation | A7 | Specify persistence strategy for evaluation datasets and results |
| O-004 | Recommendation | A1 | Add `AIConfiguration` / `AIConfigurationProvider` to A1 Foundation spec |
| O-005 | Recommendation | A2, A10 | Define degraded-mode behaviour when all providers unavailable |

All eight observations are addressable through targeted additions to the existing specification document. None require architectural redesign.

---

## 7. Final Architecture Score

| Dimension | Score | Notes |
|---|---|---|
| Module Design | 9.0 / 10 | Clear boundaries, well-motivated responsibilities |
| Dependency Architecture | 9.0 / 10 | Acyclic graph; two implicit assumptions need documentation |
| Layer Consistency | 9.5 / 10 | M1–M6 correctly applied across all 10 modules |
| Enterprise Principles | 9.0 / 10 | 11/12 principles strong; resilience partially addressed |
| Implementation Roadmap | 9.5 / 10 | Optimal order; well-reasoned |
| Risk Awareness | 8.0 / 10 | Major risks identifiable; not all mitigated in spec |
| Completeness | 8.5 / 10 | One missing capability (config management); one spec gap (vector storage) |
| Core Platform Isolation | 10.0 / 10 | Clean consumption model; no prohibited patterns |
| **Overall** | **9.1 / 10** | |

---

## 8. Final Result

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   IIOS AI Platform — Phase 3 Architecture Review                ║
║                                                                  ║
║   Result:  PASS WITH MINOR OBSERVATIONS                         ║
║                                                                  ║
║   Score:   9.1 / 10                                             ║
║                                                                  ║
║   Blocking issues:               0                              ║
║   Clarifications before A1:      2  (O-001, O-002)             ║
║   Recommendations before build:  5  (R-001, R-002, R-003,      ║
║                                      O-003, O-004, O-005)       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Verdict Justification

The architecture is fundamentally sound. The ten modules are well-designed with non-overlapping responsibilities, the dependency graph is provably acyclic, the M1–M6 standard is correctly extended to an AI context, and the Core Platform isolation is architecturally rigorous. The governance architecture (A8) and the Core Platform consumption model (M6-only access) are particularly strong.

The two clarifications (O-001, O-002) must be added to the specification before A1 implementation begins to prevent circular dependency introduction during coding. They are straightforward documentation additions, not design changes.

The five recommendations (R-001, R-002, R-003, O-003, O-004, O-005) strengthen implementation guidance before the full A2–A10 build commences. They do not block A1 implementation.

### Recommended Next Action

1. Add observations O-001 and O-002 to `PHASE3_AI_PLATFORM_ARCHITECTURE.md` (targeted additions to A2 and A3 responsibility sections)
2. Add recommendations R-001, R-002, R-003, O-003, O-004, O-005 to the specification (targeted additions to A1, A4, A7, A8, A10 sections)
3. Upon incorporation: declare the architecture **APPROVED** and proceed with A1 — AI Foundation implementation

---

*Architecture review complete. No source code generated. No existing files modified.*  
*The IIOS AI Platform architecture is ready for approval and implementation upon incorporation of the above observations.*
