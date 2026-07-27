# IIOS AI Platform — Phase 3 Architecture Specification

**Document Type:** Architecture Specification  
**Phase:** 3 — AI Platform  
**Status:** PROPOSED — Awaiting Implementation  
**Date:** 2026-07-27  
**Predecessor:** IIOS Core Trading Platform V1.0 (FROZEN, commit `348b0a4`)  
**Author:** AI Architecture Design Agent  

---

## Table of Contents

1. [Vision](#1-vision)
2. [Design Principles](#2-design-principles)
3. [Relationship to Core Platform](#3-relationship-to-core-platform)
4. [Proposed Modules](#4-proposed-modules)
5. [Standard Architecture](#5-standard-architecture)
6. [Dependency Rules](#6-dependency-rules)
7. [Development Roadmap](#7-development-roadmap)
8. [Version Strategy](#8-version-strategy)
9. [Success Criteria](#9-success-criteria)
10. [Next Step](#10-next-step)

---

## 1. Vision

### 1.1 Purpose

The IIOS AI Platform is an enterprise artificial intelligence layer built on top of the frozen IIOS Core Trading Platform. It provides systematic, governed, and explainable intelligence capabilities that augment the decision-making processes already established in the Core Platform.

The Core Trading Platform governs trading: risk management, portfolio governance, market surveillance, decision orchestration, order execution, and enterprise integration are fully realised in C1–C16. Those sixteen modules are complete and frozen.

The AI Platform does not replace or extend that logic. It adds a new capability dimension: the ability to reason, learn, remember, collaborate, and explain — using modern AI techniques — in a way that feeds structured intelligence back into the Core Platform through its published M6 gateway interfaces.

### 1.2 What the AI Platform Is

- An **intelligence amplifier** that augments the Core Platform's analytical engines with generative reasoning, semantic retrieval, multi-agent debate, and adaptive learning
- A **provider-independent AI layer** that abstracts over any combination of language models, embedding models, and reasoning engines
- An **enterprise-grade AI governance system** that enforces safety, fairness, auditability, and explainability on every AI-generated output before it reaches a trading decision
- An **orchestration platform** that sequences AI workflows and integrates their outputs with the C16 Workflow Gateway

### 1.3 What the AI Platform Is Not

- It is **not** a trading engine. Trade decisions remain the sole responsibility of the Core Trading Platform.
- It is **not** a replacement for any C1–C16 module. It consumes their services; it does not reimplement them.
- It is **not** a model training platform. It manages, routes, evaluates, and governs models; training infrastructure is out of scope for V1.0.
- It is **not** permitted to modify Core Platform internals. All interaction occurs exclusively through frozen M6 gateway APIs.

### 1.4 How It Extends the Core Platform Without Modifying It

The Core Platform exposes eight frozen M6 gateway interfaces (C9–C16) and sixteen completed intelligence modules (C1–C8). The AI Platform treats every one of these as an immutable external service.

```
AI Platform modules  ──▶  Core Platform M6 Gateways  ──▶  Core Platform internals
(A1–A10)                  (C9/C10/C11/C12/C13/C14/C15/C16)     (M1–M5, frozen)
```

AI Platform modules subscribe to Core Platform events, query snapshots, and submit requests — all through the defined gateway contracts. No AI module holds a reference to any Core Platform class below the M6 layer. This ensures that the Core Platform can evolve (under its versioning policy) without breaking the AI Platform, and vice versa.

---

## 2. Design Principles

### P-01 — Modular

Each AI capability is encapsulated in an independent module (A1–A10) with explicit boundaries, a defined public interface, and no shared mutable state across module boundaries. Modules may be deployed, tested, upgraded, or replaced independently.

### P-02 — AI-First

Every module is designed with AI-native concerns as primary: token budgets, latency-sensitive model calls, non-determinism, prompt versioning, model fallback, and semantic search are first-class architectural concerns — not afterthoughts.

### P-03 — Provider Independent

No module hardcodes a dependency on a specific model provider (OpenAI, Anthropic, Google, local models, etc.). All model calls pass through the A2 Model Management gateway. A provider can be swapped without changing any consumer module.

### P-04 — Model Independent

Model architectures, context window sizes, tokenisation schemes, and capability levels vary. No module assumes a specific model size or capability. Capability requirements are declared as abstract contracts; A2 resolves the appropriate model at runtime.

### P-05 — Event Driven

Modules communicate through events wherever latency allows. The AI Platform's internal event bus decouples producers from consumers. AI workflow state changes, model completions, agent decisions, and governance verdicts are all published as events, enabling asynchronous composition and observability.

### P-06 — Service Oriented

Every module exposes its capabilities as discrete services with well-defined request/response contracts. Consumers do not reach into a module's internals. All inter-module communication flows through published M6 gateway interfaces, mirroring the Core Platform pattern.

### P-07 — Extensible

New model providers, new tool implementations, new agent reasoning strategies, and new governance policies are added by registering new implementations against existing interfaces — not by modifying core module code. Every module provides a registry-based extension mechanism.

### P-08 — Testable

Every module must achieve deterministic behaviour under test through mock-able model provider interfaces, seedable random sources, and time-injectable clocks. No AI module may have untestable non-determinism at the business logic level. Model responses in test environments are always mocked.

### P-09 — Observable

Every AI operation produces structured telemetry: latency, token usage, model selection, confidence scores, reasoning steps, tool calls, and governance verdicts. All telemetry is emitted as structured events compatible with the Core Platform's existing observability infrastructure (C17 Control Tower pattern).

### P-10 — Secure

AI inputs and outputs are treated as untrusted until validated. Prompt injection is defended against at the A3 (Prompt & Context) layer. Model outputs are sanitised before use. All tool executions run in sandboxed contexts. Credentials, API keys, and model endpoints are never embedded in prompts or logs.

### P-11 — Explainable

Every AI-generated recommendation, decision support output, or risk signal must carry a structured explanation: which model was used, what context was provided, what reasoning steps were followed, and what governance checks were applied. Explanations are first-class outputs, not optional metadata.

### P-12 — Backward Compatible

AI Platform versioning follows the same policy as the Core Platform. Public gateway interfaces, DTO structures, event schemas, and enum values are frozen at each version boundary. New capabilities are additive. No breaking changes without a version increment.

### P-13 — No Dependency on Implementation Details

AI modules never import from below the M6 gateway layer of any Core Platform module. AI modules never import implementation classes, internal factories, or private session managers from each other below the M6 layer. All coupling is through declared, versioned contracts.

---

## 3. Relationship to Core Platform

### 3.1 Core Platform Status

The IIOS Core Trading Platform is frozen at Version 1.0 (commit `348b0a4`). Its architecture, public interfaces, contracts, package structure, class names, method signatures, and enum values are immutable under the V1.0 policy. No Phase 3 work may change any Core Platform file.

### 3.2 Consumption Model

The AI Platform consumes Core Platform services exclusively through M6 gateway APIs:

| Core Module | Gateway Package | What the AI Platform Consumes |
|---|---|---|
| C9 Decision Governance | `iios.decision.integration` | Decision request submission, decision snapshots, governance events |
| C10 Portfolio Governance | `iios.portfolio.integration` | Portfolio state snapshots, allocation constraints, rebalancing events |
| C11 Risk Management | `iios.risk.integration` | Risk assessments, scenario outputs, risk event streams |
| C12 Market Governance | `iios.market.integration` | Market regime snapshots, analytics outputs, market events |
| C13 AI Supervisor | `iios.supervisor.integration` | Governance policy enforcement, audit events, supervision snapshots |
| C14 Knowledge Management | `iios.knowledge.integration` | Knowledge retrieval, entity resolution, ontology queries |
| C15 Enterprise Integration | `iios.integration.gateway` | External data feeds, provider connections, pipeline results |
| C16 Workflow Gateway | `iios.workflow.gateway` | Workflow submission, orchestration status, workflow events |

Additionally, the AI Platform reads intelligence outputs from Gen 1 modules (C1–C5) through whatever integration interfaces those modules expose. No AI module reaches into `iios.investment.*` internals.

### 3.3 Dependency Direction

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Platform (A1–A10)                     │
│                                                             │
│   All dependencies point DOWNWARD to Core Platform M6s     │
│   No Core Platform module depends on any AI module         │
└───────────────────────┬─────────────────────────────────────┘
                        │ (consumes via frozen M6 gateways only)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          Core Trading Platform V1.0 (FROZEN)                │
│                     C1 – C16                                │
└─────────────────────────────────────────────────────────────┘
```

No reverse dependency is permitted. A Core Platform module must never import from any AI Platform module. This rule enforces that the Core Platform remains independently deployable and testable without the AI Platform present.

### 3.4 Prohibited Patterns

| Pattern | Reason |
|---|---|
| `from iios.decision.engine import ...` | Below M6 — internal implementation |
| `from iios.risk.lifecycle import ...` | Below M6 — internal implementation |
| `from iios.workflow.orchestration import ...` | Below M6 — internal implementation |
| Modifying any file in `iios/` (C1–C16) | Violates V1.0 freeze |
| Subclassing any Core Platform engine class | Creates tight coupling below M6 |
| Calling `_private` methods on any gateway | Bypasses contract layer |

### 3.5 Permitted Patterns

| Pattern | Reason |
|---|---|
| `from iios.decision.integration import DecisionIntegrationGateway` | Correct — M6 public interface |
| `from iios.risk.integration import RiskIntegrationGateway` | Correct — M6 public interface |
| `from iios.knowledge.integration import KnowledgeIntegrationGateway` | Correct — M6 public interface |
| Subscribing to M6 gateway events | Correct — event-driven consumption |
| Submitting requests through M6 request DTOs | Correct — contract-based interaction |
| Reading M5 snapshots returned by M6 gateways | Correct — immutable, frozen contracts |

---

## 4. Proposed Modules

The AI Platform consists of ten modules, designated A1 through A10, each following the standard M1–M6 six-layer architecture defined in Section 5.

---

### A1 — AI Foundation

**Package (proposed):** `iios/ai/foundation/`

#### Purpose

AI Foundation is the base infrastructure layer for the entire AI Platform. It provides the abstract interfaces, base classes, shared data types, common exceptions, constants, and provider adapters that every higher AI module depends on. Nothing in the AI Platform should be built without A1.

#### Responsibilities

- Define the abstract `AIProvider` interface that all model providers implement
- Define the abstract `AIRequest` / `AIResponse` base DTOs used by all AI operations
- Provide token budget management utilities (counting, enforcement, windowing)
- Provide rate limiter and retry logic for model API calls
- Define the AI Platform's base exception hierarchy rooted at `AIError`
- Provide the `AILifecycleAwareMixin` that all AI module engines inherit
- Provide shared serialisation and deserialisation utilities for AI content types
- Expose the `AIEventBus` base for AI-native event dispatch

#### Key Capabilities

| Capability | Description |
|---|---|
| Provider abstraction | `AIProvider` abstract interface with `complete()`, `embed()`, `tokenise()` |
| Token management | Context window enforcement, truncation strategies, budget accounting |
| Rate limiting | Token-per-minute and request-per-minute limiters per provider |
| Retry logic | Exponential back-off with jitter for transient provider failures |
| Base exceptions | `AIError`, `AIProviderError`, `AITimeoutError`, `AITokenBudgetError` |
| Structured logging | AI-aware log formatter with model, tokens, latency fields |
| Lifecycle mixin | `AILifecycleAwareMixin` — standard M1 state machine for all AI engines |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios.common.logging` | Consumes | Core Platform shared infrastructure |
| `iios.common.errors` | Consumes | Core Platform shared infrastructure |
| No other AI modules | — | A1 is the foundation; it depends on nothing within the AI Platform |

---

### A2 — Model Management

**Package (proposed):** `iios/ai/model_management/`

#### Purpose

Model Management is the registry, router, and lifecycle manager for all AI models used by the platform. It decouples every AI module from the identity and location of specific models. Consumers declare capability requirements; A2 resolves the appropriate model, manages its availability, and routes requests.

#### Responsibilities

- Maintain a registry of available model providers and their capabilities
- Route AI requests to appropriate models based on declared requirements (capability, latency, cost, context window)
- Manage model versioning and version pinning for deterministic replay
- Implement fallback chains: if a primary model is unavailable, route to the next viable alternative
- Track model usage metrics: token consumption, latency distribution, error rates
- Provide circuit-breaker logic per model endpoint
- Enable A/B routing for model evaluation experiments (coordinated with A7)

#### Key Capabilities

| Capability | Description |
|---|---|
| Model registry | Central registry of all provider/model combinations with capability metadata |
| Capability routing | Route requests by declared capability: `REASONING`, `EMBEDDING`, `SUMMARISATION`, `CODE`, `STRUCTURED_OUTPUT` |
| Fallback chains | Ordered fallback: primary → secondary → fallback; configurable per capability class |
| Version pinning | Pin a workflow to a specific model version for reproducibility |
| Circuit breaker | Per-model circuit breaker with configurable thresholds and recovery periods |
| Usage telemetry | Structured events: model selected, tokens used, latency, error type |
| Cost accounting | Token and monetary cost accumulation per request, session, and workflow |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| No Core Platform modules | — | A2 does not query trading state |

---

### A3 — Prompt & Context Platform

**Package (proposed):** `iios/ai/prompt_context/`

#### Purpose

The Prompt & Context Platform governs how AI requests are constructed. It provides versioned prompt templates, dynamic context assembly, retrieval-augmented context injection, prompt safety validation, and structured output schema enforcement. All AI modules that need to call a model construct their requests through A3.

#### Responsibilities

- Maintain a versioned library of prompt templates
- Assemble context windows from multiple sources: Core Platform snapshots, memory (A4), tool results (A9), and inline data
- Enforce context window budgets and apply truncation or summarisation strategies when limits are approached
- Validate prompts for injection patterns before dispatch
- Apply structured output schemas and validate model responses against declared shapes
- Version-control prompts: a prompt change is treated as a code change with a version identifier
- Support multi-turn conversation context management

#### Key Capabilities

| Capability | Description |
|---|---|
| Template registry | Versioned prompt templates with variable substitution and role assignment |
| Context assembly | Structured context builder: system / user / assistant / tool segments |
| Budget enforcement | Hard token ceiling per layer; soft budget triggers summarisation |
| Injection defence | Regex + semantic filters detect and reject prompt injection attempts |
| Schema enforcement | Pydantic-compatible output schemas; model response validated before return |
| Multi-turn management | Rolling window for conversation history; configurable retention policy |
| Prompt versioning | Each template has a semantic version; outputs carry the template version used |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/model_management/` (A2) | Consumes | AI Platform — M6 gateway |
| `iios.knowledge.integration` (C14) | Consumes | Core Platform — M6 gateway (retrieval-augmented context) |

---

### A4 — Memory & Knowledge Platform

**Package (proposed):** `iios/ai/memory/`

#### Purpose

The Memory & Knowledge Platform provides AI agents and workflows with persistent, queryable memory across sessions. It manages four memory tiers — working memory, episodic memory, semantic memory, and procedural memory — and integrates with the Core Platform's C14 Knowledge Management module for durable knowledge storage.

#### Responsibilities

- Maintain working memory: short-lived, within-session context for active agents
- Maintain episodic memory: structured records of past AI operations, decisions, and outcomes
- Maintain semantic memory: embedding-indexed facts, summaries, and retrieved knowledge
- Maintain procedural memory: recorded reasoning patterns, successful strategies, and learned heuristics
- Provide vector-similarity retrieval for semantic search across all memory tiers
- Persist long-term memory to C14 Knowledge Management (via M6 gateway)
- Expire, prune, and consolidate memory according to configurable retention policies
- Provide memory provenance: every memory item carries a source, timestamp, and confidence score

#### Key Capabilities

| Capability | Description |
|---|---|
| Working memory | Scoped per agent session; cleared on session end |
| Episodic memory | Append-only log of past AI actions with structured outcome records |
| Semantic memory | Embedding-indexed retrieval; top-k similarity search |
| Procedural memory | Learned patterns stored as versioned heuristic records |
| Memory consolidation | Periodic background job: compress episodic → semantic, prune stale entries |
| Provenance tracking | Source, model version, retrieval score, timestamp per memory item |
| Memory governance | Retention limits, privacy controls, data classification per memory tier |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/model_management/` (A2) | Consumes | AI Platform — M6 gateway (embedding models) |
| `iios/ai/prompt_context/` (A3) | Consumes | AI Platform — M6 gateway (summarisation for consolidation) |
| `iios.knowledge.integration` (C14) | Consumes | Core Platform — M6 gateway (durable storage) |

---

### A5 — AI Agent Framework

**Package (proposed):** `iios/ai/agent/`

#### Purpose

The AI Agent Framework defines the standard for a single intelligent agent within the IIOS AI Platform. An agent is an autonomous unit that perceives its environment through Core Platform snapshots, reasons using model calls, selects and executes tools, updates its memory, and produces structured outputs — all within a governed lifecycle.

#### Responsibilities

- Define the standard `AIAgent` base class with a governed lifecycle (CREATED → INITIALIZED → IDLE → THINKING → ACTING → WAITING → COMPLETED → FAILED)
- Implement reasoning loop patterns: ReAct (Reason + Act), Chain-of-Thought, Tree-of-Thought, and Plan-and-Execute
- Provide structured tool invocation with pre- and post-execution validation (via A9)
- Manage agent session context: goal, constraints, history, and current reasoning state
- Enforce agent-level resource budgets: maximum steps, token limit, time limit, tool call limit
- Emit structured reasoning traces that satisfy A8 governance requirements
- Support agent specialisation through role definitions and capability declarations
- Provide deterministic agent replay for debugging and audit

#### Key Capabilities

| Capability | Description |
|---|---|
| Standard agent lifecycle | State machine with governed transitions; lifecycle events emitted at each transition |
| Reasoning patterns | ReAct, CoT, ToT, Plan-and-Execute — selectable per agent type |
| Tool invocation | Structured tool call with schema validation pre/post execution |
| Resource budgets | Hard limits on steps, tokens, wall-time, and tool calls per agent run |
| Reasoning trace | Structured log of every thought, action, observation, and conclusion |
| Goal management | Explicit goal declaration; success/failure criteria evaluated after each step |
| Agent registry | Named, versioned agent type registry for instantiation by A6 and A10 |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/model_management/` (A2) | Consumes | AI Platform — M6 gateway |
| `iios/ai/prompt_context/` (A3) | Consumes | AI Platform — M6 gateway |
| `iios/ai/memory/` (A4) | Consumes | AI Platform — M6 gateway |
| `iios/ai/tool_skill/` (A9) | Consumes | AI Platform — M6 gateway |
| `iios.decision.integration` (C9) | Consumes | Core Platform — M6 gateway (decision context) |
| `iios.risk.integration` (C11) | Consumes | Core Platform — M6 gateway (risk context) |
| `iios.market.integration` (C12) | Consumes | Core Platform — M6 gateway (market context) |

---

### A6 — Multi-Agent Collaboration

**Package (proposed):** `iios/ai/collaboration/`

#### Purpose

Multi-Agent Collaboration governs the interaction of multiple AI agents working toward a shared goal. It implements structured collaboration patterns — debate, consensus, delegation, and parallel investigation — and produces aggregated outputs that represent the collective intelligence of the agent ensemble.

#### Responsibilities

- Coordinate ensembles of A5 agents toward a shared objective
- Implement structured debate: agents present positions, challenge each other's reasoning, and converge on a consensus
- Implement delegated sub-task patterns: a coordinator agent breaks a goal into sub-goals and assigns them to specialist agents
- Implement parallel investigation: multiple agents independently analyse the same problem, results are reconciled
- Manage shared collaboration context: what every agent in the ensemble has access to
- Resolve conflicts between agent outputs using configurable resolution strategies (majority, confidence-weighted, arbitrated)
- Enforce collaboration budgets: total token spend, time limit, and iteration count for the ensemble
- Emit structured collaboration summaries consumable by A8 governance and A10 orchestration

#### Key Capabilities

| Capability | Description |
|---|---|
| Debate protocol | Multi-round structured debate with position, challenge, and synthesis phases |
| Consensus engine | Configurable consensus strategies: majority vote, confidence-weighted aggregation, arbitrator agent |
| Delegation graph | Directed task decomposition graph; coordinator assigns and monitors sub-agents |
| Shared context | Controlled shared memory scope for the collaboration session |
| Conflict resolution | Structured disagreement records with resolution outcome and reasoning |
| Ensemble budgets | Hard limits on total tokens and wall-time for the collaboration session |
| Collaboration trace | Full structured log of every agent's contribution for A8 auditability |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/agent/` (A5) | Consumes | AI Platform — M6 gateway |
| `iios/ai/memory/` (A4) | Consumes | AI Platform — M6 gateway (shared session context) |
| `iios.decision.integration` (C9) | Consumes | Core Platform — M6 gateway (decision context for ensemble) |

---

### A7 — Learning & Evaluation

**Package (proposed):** `iios/ai/learning/`

#### Purpose

Learning & Evaluation provides the systematic measurement, evaluation, and continuous improvement infrastructure for all AI Platform modules. It tracks the quality of model outputs, agent reasoning, and collaboration outcomes over time, and provides the data necessary to trigger model upgrades, prompt revisions, or agent configuration changes.

#### Responsibilities

- Evaluate model outputs against ground truth, human feedback, and reference outputs using standard metrics (BLEU, ROUGE, BERTScore, LLM-as-judge)
- Track agent performance over time: goal completion rate, reasoning quality, tool call accuracy, token efficiency
- Track collaboration outcomes: consensus quality, dissent frequency, arbitration rate
- Provide experiment management: A/B comparisons between prompt versions, model versions, or agent configurations
- Generate performance reports and trend analyses consumed by A8 governance
- Detect quality degradation and emit alerts through the AI Platform event bus
- Integrate with A2 Model Management to inform model routing decisions based on empirical quality data
- Integrate with C13 AI Supervisor for governance-level performance reporting

#### Key Capabilities

| Capability | Description |
|---|---|
| Output evaluation | LLM-as-judge, reference-based, and rubric-based evaluation pipelines |
| Agent performance tracking | Per-agent, per-run metrics: goal completion, steps, tokens, tool accuracy |
| Experiment management | Controlled A/B comparison with statistical significance tracking |
| Quality degradation alerts | Threshold-based alerts when metric trends cross defined boundaries |
| Improvement recommendations | Structured suggestions: swap model, revise prompt, adjust agent parameters |
| Performance dashboards | Snapshot-compatible performance summaries for observability systems |
| Ground truth management | Versioned reference dataset management for evaluation |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/model_management/` (A2) | Consumes | AI Platform — M6 gateway (model metadata) |
| `iios/ai/agent/` (A5) | Consumes | AI Platform — M6 gateway (agent traces) |
| `iios/ai/collaboration/` (A6) | Consumes | AI Platform — M6 gateway (collaboration summaries) |
| `iios.supervisor.integration` (C13) | Consumes | Core Platform — M6 gateway (governance reporting) |

---

### A8 — AI Governance

**Package (proposed):** `iios/ai/governance/`

#### Purpose

AI Governance is the safety, compliance, and accountability layer of the AI Platform. Every AI output that may influence a trading decision must pass through A8 before it reaches any Core Platform gateway. A8 enforces content safety policies, detects bias and hallucination, applies regulatory compliance checks, logs complete audit trails, and produces the explainability reports required by enterprise risk standards.

#### Responsibilities

- Define and enforce AI safety policies as structured, versioned governance rules
- Apply content safety filters to all AI outputs (harmful content, confidential data exposure, factual contradiction)
- Detect and flag hallucination indicators in model outputs
- Detect and flag potential bias in AI reasoning traces and recommendations
- Maintain a complete, tamper-evident audit log of every AI operation: input, model, output, governance verdict
- Generate structured explainability reports: reasoning chain, evidence sources, confidence, governance outcome
- Enforce compliance rules mapped to regulatory requirements
- Integrate with C13 AI Supervisor (M6 gateway) to escalate governance violations for human review
- Provide a governance verdict DTO that wraps every AI output before it can be submitted to a Core Platform gateway

#### Key Capabilities

| Capability | Description |
|---|---|
| Safety policy engine | Versioned policy rules applied to every AI output pre-submission |
| Content safety filters | Multi-layer filter: regex → embedding-based → LLM judge |
| Hallucination detection | Factual consistency check: AI claim vs. Core Platform snapshot data |
| Bias detection | Statistical and semantic bias indicators in reasoning traces |
| Audit log | Append-only, tamper-evident structured log of every AI operation |
| Explainability report | Structured output: model, prompt version, reasoning steps, evidence, verdict |
| Governance verdict DTO | Frozen dataclass wrapping every AI output; contains `approved`, `confidence`, `explanation`, `policy_violations` |
| Escalation path | Violations above threshold forwarded to C13 AI Supervisor via M6 gateway |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/agent/` (A5) | Consumes | AI Platform — M6 gateway (reasoning traces) |
| `iios/ai/collaboration/` (A6) | Consumes | AI Platform — M6 gateway (collaboration traces) |
| `iios/ai/learning/` (A7) | Consumes | AI Platform — M6 gateway (quality metrics) |
| `iios.supervisor.integration` (C13) | Consumes | Core Platform — M6 gateway (governance escalation) |
| `iios.risk.integration` (C11) | Consumes | Core Platform — M6 gateway (risk context for compliance checks) |
| `iios.decision.integration` (C9) | Consumes | Core Platform — M6 gateway (decision context for hallucination checks) |

---

### A9 — Tool & Skill Platform

**Package (proposed):** `iios/ai/tool_skill/`

#### Purpose

The Tool & Skill Platform defines and manages the complete catalogue of capabilities that AI agents can invoke. A tool is a discrete, schema-defined callable action. A skill is a composed sequence of tools that implements a higher-level capability. A9 provides the registry, execution sandbox, schema validation, result caching, and capability discovery infrastructure that A5 agents use when acting.

#### Responsibilities

- Maintain a versioned registry of all available tools and skills
- Define the standard `Tool` interface: `name`, `description`, `input_schema`, `output_schema`, `execute()`
- Provide sandboxed tool execution with resource limits (CPU, memory, time) and isolation from Core Platform internals
- Validate tool inputs against declared schemas before execution
- Validate tool outputs against declared schemas before returning to the agent
- Cache deterministic tool results to avoid redundant calls
- Provide capability discovery: agents query the registry for tools matching a declared capability requirement
- Enable skill composition: a skill declares an ordered sequence of tool calls with data flow between them
- Emit structured tool execution events for A8 governance and observability

#### Key Capabilities

| Capability | Description |
|---|---|
| Tool registry | Versioned, named tool catalogue with schema-defined inputs and outputs |
| Skill registry | Composed tool sequences with named data flow; re-usable across agents |
| Sandboxed execution | Resource-limited, isolated execution context per tool call |
| Schema validation | Pre/post validation of every tool invocation against declared schemas |
| Capability discovery | Semantic search over tool descriptions for agent self-assembly of plans |
| Deterministic caching | Content-addressed cache for idempotent tool results |
| Execution telemetry | Structured event per tool call: tool name, inputs hash, latency, success/error |

#### Standard Built-in Tool Categories

| Category | Examples |
|---|---|
| Core Platform readers | Risk snapshot reader, Market regime reader, Portfolio state reader, Decision history reader |
| Knowledge tools | Knowledge entity lookup, semantic search, ontology traversal (via C14 M6) |
| Data transformation | JSON transformer, time-series aggregator, statistical summariser |
| Calculation tools | Percentage change, volatility calculation, correlation computation |
| Formatting tools | Report formatter, table generator, markdown renderer |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/model_management/` (A2) | Consumes | AI Platform — M6 gateway (for LLM-based tools) |
| `iios.risk.integration` (C11) | Consumes | Core Platform — M6 gateway (risk reader tools) |
| `iios.market.integration` (C12) | Consumes | Core Platform — M6 gateway (market reader tools) |
| `iios.portfolio.integration` (C10) | Consumes | Core Platform — M6 gateway (portfolio reader tools) |
| `iios.knowledge.integration` (C14) | Consumes | Core Platform — M6 gateway (knowledge tools) |

---

### A10 — AI Orchestration

**Package (proposed):** `iios/ai/orchestration/`

#### Purpose

AI Orchestration is the top-level coordination layer of the AI Platform. It composes A1–A9 capabilities into end-to-end AI workflows, schedules their execution, manages resource allocation across the platform, and integrates with the Core Platform's C16 Workflow Gateway to submit structured AI outputs into the Core trading workflow. A10 is the single point of entry for all external consumers of the AI Platform.

#### Responsibilities

- Define and execute AI workflows: ordered pipelines of agent invocations, collaboration sessions, evaluations, and governance checks
- Schedule AI workflow execution in response to Core Platform events (market open, risk breach, decision request)
- Manage platform-level resource allocation: token budgets, model quota, concurrent agent limits
- Integrate with C16 Workflow Gateway (M6) to inject AI-generated workflow steps into the Core trading workflow
- Provide an AI Platform-level status, health, and metrics summary
- Implement AI workflow versioning: a change to workflow composition creates a new version
- Coordinate with A8 AI Governance to ensure all workflow outputs are approved before submission to Core Platform gateways
- Provide the AI Platform's single public entry-point gateway (A10 M6) for all external consumers

#### Key Capabilities

| Capability | Description |
|---|---|
| Workflow definition | Declarative AI workflow DSL: sequential, parallel, conditional, loop constructs |
| Event-triggered execution | Subscribe to Core Platform M6 events; trigger AI workflows on market/risk/decision events |
| Resource scheduler | Platform-wide token quota manager; concurrent workflow limiter |
| Governance gate | Every workflow output passes A8 governance before submission to Core Platform |
| Workflow versioning | Named, versioned workflow definitions; version is carried in all telemetry |
| Status and health | Live status of all active AI workflows, model utilisation, queue depths |
| Core Platform integration | Submit approved AI outputs to C16 Workflow Gateway M6 via standard request DTOs |

#### Dependencies

| Dependency | Direction | Type |
|---|---|---|
| `iios/ai/foundation/` (A1) | Consumes | AI Platform — M6 gateway |
| `iios/ai/model_management/` (A2) | Consumes | AI Platform — M6 gateway |
| `iios/ai/prompt_context/` (A3) | Consumes | AI Platform — M6 gateway |
| `iios/ai/memory/` (A4) | Consumes | AI Platform — M6 gateway |
| `iios/ai/agent/` (A5) | Consumes | AI Platform — M6 gateway |
| `iios/ai/collaboration/` (A6) | Consumes | AI Platform — M6 gateway |
| `iios/ai/learning/` (A7) | Consumes | AI Platform — M6 gateway |
| `iios/ai/governance/` (A8) | Consumes | AI Platform — M6 gateway (mandatory governance gate) |
| `iios/ai/tool_skill/` (A9) | Consumes | AI Platform — M6 gateway |
| `iios.workflow.gateway` (C16) | Consumes | Core Platform — M6 gateway (workflow submission) |
| `iios.integration.gateway` (C15) | Consumes | Core Platform — M6 gateway (external data ingestion) |
| `iios.decision.integration` (C9) | Consumes | Core Platform — M6 gateway (decision workflow triggers) |

---

## 5. Standard Architecture

Every AI Platform module (A1–A10) must implement the same six-layer M1–M6 standard established by the Core Platform Gen 2 modules (C9–C16). This ensures consistent lifecycle management, governance integration, observability, and interface contracts across the entire AI Platform.

```
┌─────────────────────────────────────────────────────────────────┐
│  M6 — Gateway                                                   │
│  The single public entry point. External consumers call only    │
│  this layer. All other layers are private to the module.        │
├─────────────────────────────────────────────────────────────────┤
│  M5 — Snapshot                                                  │
│  Immutable point-in-time state captures. All snapshot classes   │
│  are frozen dataclasses. No business logic. No engine deps.     │
├─────────────────────────────────────────────────────────────────┤
│  M4 — Core Framework                                            │
│  The domain-specific computational heart of the module. Named   │
│  for its domain (e.g. reasoning/, evaluation/, routing/).       │
├─────────────────────────────────────────────────────────────────┤
│  M3 — Policy Framework                                          │
│  Governance, rules, and constraints applied to engine behaviour. │
│  Policies are versioned, testable, and independently deployable.│
├─────────────────────────────────────────────────────────────────┤
│  M2 — Engine                                                    │
│  Stateful engine coordinating M3, M4, and M1. Processes         │
│  requests, applies policies, updates state, emits events.       │
├─────────────────────────────────────────────────────────────────┤
│  M1 — Lifecycle                                                 │
│  Manages module state: CREATED → INITIALIZED → RUNNING →       │
│  PAUSED → STOPPED. Health, heartbeat, and event history.        │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

#### M1 — Lifecycle

- Manages the module's operational state machine
- States: `CREATED`, `INITIALIZED`, `RUNNING`, `PAUSED`, `STOPPING`, `STOPPED`, `FAILED`
- Provides `health()`, `status()`, `heartbeat()`, and `lifecycle_event_history()`
- All modules inherit `AILifecycleAwareMixin` defined in A1 Foundation
- Lifecycle events are frozen dataclasses emitted to the AI Platform event bus
- **Package name convention:** `lifecycle/`

#### M2 — Engine

- Stateful processing core of the module
- Receives requests, coordinates M3 policy application and M4 framework execution
- Manages active sessions, concurrent request queues, and internal caches
- Emits structured engine events to the module event bus
- Provides statistics: request count, success rate, latency percentiles
- **Package name convention:** `engine/`

#### M3 — Policy Framework

- Defines versioned governance rules applied by the M2 engine
- Policies are declarative, independently testable, and composable
- Policy chain: ordered application of N policies to an engine request
- Policy violation produces a structured verdict DTO — it does not raise an exception by default
- Policies may be enabled/disabled at runtime through the M6 gateway
- **Package name convention:** `policies/`

#### M4 — Core Framework

- Domain-specific computation: reasoning algorithms, model routing logic, memory retrieval, tool execution
- Receives inputs from M2 engine; returns structured results
- No direct model calls — model calls are submitted through the A2 Model Management M6 gateway
- No direct Core Platform calls — Core Platform queries are submitted through the appropriate M6 gateways
- All output types are frozen dataclasses
- **Package name convention:** domain-specific (e.g., `reasoning/`, `routing/`, `retrieval/`, `evaluation/`)

#### M5 — Snapshot

- Provides point-in-time immutable captures of module state
- All snapshot classes are `@dataclass(frozen=True)`
- No business logic, no engine references, no gateway references
- Snapshot builders may import only from `iios.common.logging`
- Snapshots are the only M5 output exposed through the M6 gateway
- **Package name convention:** `snapshot/`

#### M6 — Gateway

- The **only** layer that external consumers may import or call
- Exposes: `initialize()`, `start()`, `stop()`, `restart()`, `health()`, `status()`, `statistics()`, `snapshot()`, `history()`, `validate()`, `submit()`, `query()`
- Domain-specific methods may be added (additive only)
- All request types are frozen `Request` dataclasses
- All response types are frozen `Response` dataclasses
- Gateway enforces that no caller bypasses M1–M5 directly
- **Package name convention:** `gateway/`

### Per-Module Layer Name Proposals

| Module | M1 | M2 | M3 | M4 | M5 | M6 |
|---|---|---|---|---|---|---|
| A1 Foundation | `lifecycle/` | `engine/` | `policies/` | `adapters/` | `snapshot/` | `gateway/` |
| A2 Model Mgmt | `lifecycle/` | `engine/` | `policies/` | `routing/` | `snapshot/` | `gateway/` |
| A3 Prompt/Context | `lifecycle/` | `engine/` | `policies/` | `assembly/` | `snapshot/` | `gateway/` |
| A4 Memory | `lifecycle/` | `engine/` | `policies/` | `retrieval/` | `snapshot/` | `gateway/` |
| A5 Agent | `lifecycle/` | `engine/` | `policies/` | `reasoning/` | `snapshot/` | `gateway/` |
| A6 Collaboration | `lifecycle/` | `engine/` | `policies/` | `coordination/` | `snapshot/` | `gateway/` |
| A7 Learning | `lifecycle/` | `engine/` | `policies/` | `evaluation/` | `snapshot/` | `gateway/` |
| A8 Governance | `lifecycle/` | `engine/` | `policies/` | `enforcement/` | `snapshot/` | `gateway/` |
| A9 Tool/Skill | `lifecycle/` | `engine/` | `policies/` | `execution/` | `snapshot/` | `gateway/` |
| A10 Orchestration | `lifecycle/` | `engine/` | `policies/` | `pipeline/` | `snapshot/` | `gateway/` |

---

## 6. Dependency Rules

### 6.1 Intra-Layer Rules (within a module)

| Rule | Description |
|---|---|
| **R-IL-01** | M1 Lifecycle has no dependencies on M2–M6 within its own module |
| **R-IL-02** | M2 Engine depends on M1 and M3 and M4 within its own module |
| **R-IL-03** | M3 Policies depend on M1 only; never on M2, M4, M5, or M6 |
| **R-IL-04** | M4 Core Framework depends on M1 and M3 only; never on M2, M5, or M6 |
| **R-IL-05** | M5 Snapshot has no dependencies on M1–M4 or M6 within its own module |
| **R-IL-06** | M6 Gateway depends on all inner layers (M1–M5) through lazy imports; it imports from none except through controlled factory patterns |

```
M6 → (via factory) → M5, M4, M3, M2, M1
M2 → M1, M3, M4
M3 → M1
M4 → M1, M3
M5 → (none within module)
M1 → (none within module)
```

### 6.2 Inter-Module Rules (across AI Platform modules)

| Rule | Description |
|---|---|
| **R-IM-01** | An AI module may only depend on AI modules with a lower module number (A1 < A2 < ... < A10) with the exception of A9 (Tool/Skill) which is a peer dependency of A5 |
| **R-IM-02** | All inter-module calls cross the M6 gateway boundary — no AI module imports below M6 of another AI module |
| **R-IM-03** | A1 Foundation has no dependencies on any other AI module |
| **R-IM-04** | No circular dependencies across AI modules at any layer |

### 6.3 AI Platform → Core Platform Rules

| Rule | Description |
|---|---|
| **R-CP-01** | AI modules consume Core Platform services only through M6 gateway imports |
| **R-CP-02** | No AI module imports from below M6 of any Core Platform module |
| **R-CP-03** | No AI module modifies any Core Platform file |
| **R-CP-04** | No AI module subclasses any Core Platform engine, policy, or snapshot class |
| **R-CP-05** | AI modules submit structured request DTOs to Core Platform M6 gateways; they never reach into internal factory or session classes |
| **R-CP-06** | AI modules read Core Platform state only through M5 snapshot responses from M6 gateways; never by direct database access or file read |

### 6.4 Core Platform → AI Platform Rules

| Rule | Description |
|---|---|
| **R-PA-01** | No Core Platform module (C1–C16) imports from any AI Platform module |
| **R-PA-02** | The Core Platform is independently deployable without the AI Platform present |
| **R-PA-03** | AI Platform failure does not cause Core Platform failure |

### 6.5 Snapshot Rules

| Rule | Description |
|---|---|
| **R-SN-01** | All snapshot classes are `@dataclass(frozen=True)` |
| **R-SN-02** | No snapshot class contains mutable fields (no `dict`, `list`, or `set` without an explicit frozen wrapper) |
| **R-SN-03** | No snapshot class contains business logic methods |
| **R-SN-04** | No snapshot class imports from M2, M4, or M6 of its own module |

### 6.6 Visualisation

```
A10 Orchestration
 ├── A9 Tool/Skill    ──────────────────────────────┐
 ├── A8 Governance                                  │
 ├── A7 Learning      ──────────────────────────────┤
 ├── A6 Collaboration                               │
 ├── A5 Agent    ─────────────────────────────────┐ │
 ├── A4 Memory                                    │ │
 ├── A3 Prompt/Context                            │ │
 ├── A2 Model Mgmt                                │ │
 └── A1 Foundation ◀── (all modules depend here) ─┘ ┘

All ──▶ Core Platform M6 gateways (C9–C16)
        ↓
   Core Platform internals (frozen, untouched)
```

---

## 7. Development Roadmap

The recommended implementation order follows the dependency graph strictly: a module is implemented only after all its dependencies are complete and passing their test baselines.

```
A1 — AI Foundation
 │
 └──▶  A2 — Model Management
        │
        └──▶  A3 — Prompt & Context Platform
               │
               └──▶  A9 — Tool & Skill Platform  ◀──── (peer to A5, needed before agents)
                      │
                      └──▶  A4 — Memory & Knowledge Platform
                             │
                             └──▶  A5 — AI Agent Framework
                                    │
                                    └──▶  A6 — Multi-Agent Collaboration
                                           │
                                           ├──▶  A7 — Learning & Evaluation
                                           │
                                           └──▶  A8 — AI Governance
                                                  │
                                                  └──▶  A10 — AI Orchestration
```

### Rationale for This Order

**A1 first:** Every other module imports from A1. It must be stable before any downstream module is written. A1 has zero AI module dependencies — it can be built and fully tested in isolation.

**A2 second:** Model Management is the next hard dependency. A3, A4, A5, A7, and A9 all require model calls routed through A2. Building A2 before those consumers forces the provider abstraction to be designed correctly from the start, not retrofitted later.

**A3 third:** Prompt & Context is needed by agents (A5) and by A9 tools that use language models. Building A3 before those consumers ensures the context assembly contract is stable before it is consumed.

**A9 fourth:** Tools are needed by agents. Building the tool registry and execution sandbox before the agent framework ensures that A5 can be built against a stable tool interface rather than an unstable in-progress one.

**A4 fifth:** Memory is needed by agents (A5) and collaboration (A6). Building memory before agents ensures the memory contract is stable. Memory also exercises the C14 Knowledge M6 gateway integration, validating the Core Platform consumption pattern early.

**A5 sixth:** The agent framework is the first module that combines all previous capabilities (A1–A4, A9). It is also the most complex single-agent component. A5 must be stable before multi-agent collaboration can be designed meaningfully.

**A6 seventh:** Collaboration is built on top of individual agents. Building it after A5 is a hard requirement.

**A7 eighth:** Learning & Evaluation can only be meaningfully designed after there are agents (A5) and collaborations (A6) producing outputs to evaluate. It consumes traces from A5 and A6.

**A8 ninth:** Governance is built last among the capability modules because it wraps outputs from agents (A5), collaborations (A6), and uses evaluation data from A7. Building governance before those consumers would produce an under-specified policy surface.

**A10 last:** Orchestration composes everything. It cannot be meaningfully designed or implemented until all A1–A9 modules are complete and stable. A10 is the integration test of the entire AI Platform.

---

## 8. Version Strategy

The AI Platform will follow the identical freeze process used by the Core Trading Platform:

```
Phase 3.F1 — Architecture Audit
      │
      ▼
Phase 3.F2 — Architecture Standardization
      │
      ▼
Phase 3.F3 — Interface & Contract Freeze
      │
      ▼
IIOS AI Platform — Version 1.0 (FROZEN)
```

### Phase 3.F1 — Architecture Audit

After all A1–A10 modules are implemented, a read-only architecture inspection is performed:

- All ten modules inspected for M1–M6 compliance
- Dependency rule violations identified
- Naming consistency verified
- Any correctable violations fixed; informational observations documented
- Architecture scored and a pass/fail verdict issued

### Phase 3.F2 — Architecture Standardization

Confirmatory phase after F1:

- Standard architecture confirmed across all ten modules
- No circular dependencies verified by static analysis
- Correct M6 gateway usage confirmed (no below-gateway imports from other modules or from Core Platform)
- A1 `AILifecycleAwareMixin` usage confirmed across A2–A10

### Phase 3.F3 — Interface & Contract Freeze

All eight public contract surfaces audited across A1–A10:

- Public API method signatures (M6 gateways)
- Snapshot contract audit (all frozen, no engine/gateway deps)
- Configuration contracts (no hardcoded provider keys, no magic numbers)
- Exception hierarchy (`AIError` inheritance)
- Event contracts (all `*Event` payloads frozen, `*EventBus` mutable)
- DTO contracts (all Request/Response frozen)
- Enums and constants (no duplicates)
- Backward compatibility (all M6 layers import cleanly, all `__all__` defined)

### IIOS AI Platform Version 1.0

Upon F3 PASS:

- Official version freeze document generated
- Commit tagged as `ai-platform-v1.0`
- Both platform layers (Core + AI) are independently versioned and frozen
- Combined system declared: IIOS Trading Intelligence System V1.0

### Versioning Principles

| Principle | Description |
|---|---|
| Semantic versioning | Major.Minor.Patch for the AI Platform independent of Core Platform version |
| Breaking change = major bump | Any public interface change requires a major version increment |
| Additive change = minor bump | New methods, new DTOs, new enum members: minor increment |
| Bug/security/perf = patch | Fixes that preserve all contracts: patch increment |
| Independent versioning | Core Platform V1.x and AI Platform V1.x evolve independently under their respective policies |

---

## 9. Success Criteria

Phase 3 is complete when all of the following criteria are satisfied:

### 9.1 Implementation Completeness

| Criterion | Requirement |
|---|---|
| All modules implemented | A1–A10 all exist with complete M1–M6 layer structures |
| No placeholder layers | Every M1–M6 layer contains working implementation, not stub files |
| All M6 gateways operational | Every module's M6 gateway can be instantiated and responds to `health()` and `status()` |

### 9.2 Test Coverage

| Criterion | Requirement |
|---|---|
| Unit tests per module | Each module has a full unit test suite following the Core Platform pattern |
| Regression baseline | A defined count of passing tests that must not decrease (analogous to Core Platform's 10,855) |
| No test regression | Addition of any AI module must not reduce the Core Platform's 10,855 baseline |
| Contract tests | Every M6 gateway has contract tests validating request/response frozen structure |

### 9.3 Architecture Compliance

| Criterion | Requirement |
|---|---|
| M1–M6 standard | Every module complies with the standard six-layer architecture |
| Dependency rules | All dependency rules R-IL-01 through R-PA-03 pass static analysis |
| No Core Platform modification | Zero changes to any file under `iios/` C1–C16 packages |
| No below-M6 imports | No AI module contains an import from below M6 of any Core or AI module |

### 9.4 Freeze Phases

| Criterion | Requirement |
|---|---|
| F1 PASS | Architecture audit passes with score ≥ 8.0/10 |
| F2 PASS | Standardisation confirmed with zero circular dependencies |
| F3 PASS | All contract surfaces frozen and verified |

### 9.5 Integration

| Criterion | Requirement |
|---|---|
| Core Platform isolation | Core Platform remains independently deployable without any AI module |
| A10 → C16 integration | A10 can submit an approved AI workflow step to C16 Workflow Gateway and receive a valid response |
| A8 governance gate | No AI output reaches a Core Platform M6 gateway without an A8 governance verdict |
| End-to-end trace | A single AI workflow produces a complete, structured trace from A10 through A1 to a Core Platform gateway |

### 9.6 Observability and Operations

| Criterion | Requirement |
|---|---|
| Health endpoints | Every AI module responds to `health()` with a structured health DTO |
| Structured telemetry | Every AI operation emits structured events with latency, model, tokens, and outcome |
| Deployment | All AI modules deploy successfully to the existing Docker Compose environment |
| Both containers healthy | `docker compose ps` shows both `ai-trading-brain` and `trading-dashboard` containers as `Up (healthy)` after AI Platform is added |

---

## 10. Next Step

### Recommendation: Begin with A1 — AI Foundation

**The first implementation module is A1 — AI Foundation.**

#### Justification

1. **Hard dependency of all other modules.** Every module in the AI Platform (A2–A10) imports from A1. If A1 is designed or implemented incorrectly, the error propagates to all nine downstream modules. Building A1 first allows the entire platform's shared contracts to be established and validated before any consumer module is written.

2. **Zero external dependencies.** A1 depends only on `iios.common.logging` and `iios.common.errors` from the Core Platform — both of which are shared infrastructure with no business logic. A1 can be built, tested, and frozen entirely without touching or waiting for any other AI module.

3. **Forces the right design decisions early.** The `AIProvider` abstract interface, `AIRequest`/`AIResponse` base DTOs, `AIError` exception hierarchy, token management utilities, and `AILifecycleAwareMixin` are platform-wide contracts. Designing them first — and testing them in isolation — ensures that the decisions made in A1 are intentional rather than accidentally inherited from a specific model provider's SDK.

4. **Validates the M1–M6 pattern in an AI context.** A1 is the first opportunity to confirm that the Core Platform's Gen 2 M1–M6 architecture pattern translates cleanly to an AI module. Lessons learned in A1 shape the approach for A2–A10, before any complex dependencies exist.

5. **Establishes the test pattern.** A1 can be tested with zero mocking overhead (no model calls, no Core Platform integration). Writing a complete unit test suite for A1 establishes the test conventions (fixture structure, coverage requirements, contract test patterns) that all subsequent AI modules will follow.

#### A1 Entry Criteria

Before implementing A1:

- [ ] This architecture document is reviewed and accepted
- [ ] The proposed package root `iios/ai/` is confirmed as the AI Platform package root
- [ ] The proposed `AILifecycleAwareMixin` is confirmed as the correct inheritance pattern
- [ ] The `AIProvider` abstract interface surface is agreed upon
- [ ] The base exception hierarchy (`AIError` → `AIProviderError`, `AITimeoutError`, `AITokenBudgetError`) is confirmed

#### A1 Exit Criteria

A1 is complete and A2 may begin when:

- [ ] All M1–M6 layers exist under `iios/ai/foundation/`
- [ ] `AIProvider` abstract interface is implemented and tested
- [ ] `AILifecycleAwareMixin` is implemented and tested
- [ ] Base exception hierarchy is complete
- [ ] Token management utilities are complete
- [ ] Rate limiter and retry logic are complete
- [ ] A1 M6 gateway responds to all standard lifecycle calls
- [ ] Full unit test suite passes
- [ ] No import from any AI module other than `iios.common.*`

---

## Appendix A — Module Summary

| Module | Package | Purpose | Key Dependency |
|---|---|---|---|
| A1 | `iios/ai/foundation/` | Base infrastructure, provider abstraction, shared types | `iios.common.*` only |
| A2 | `iios/ai/model_management/` | Model registry, routing, fallback, circuit breaker | A1 |
| A3 | `iios/ai/prompt_context/` | Prompt templates, context assembly, injection defence | A1, A2, C14 |
| A4 | `iios/ai/memory/` | Working/episodic/semantic/procedural memory | A1, A2, A3, C14 |
| A5 | `iios/ai/agent/` | Single agent lifecycle, reasoning loops, tool invocation | A1–A4, A9, C9, C11, C12 |
| A6 | `iios/ai/collaboration/` | Multi-agent debate, consensus, delegation | A1, A4, A5, C9 |
| A7 | `iios/ai/learning/` | Output evaluation, performance tracking, experiments | A1, A2, A5, A6, C13 |
| A8 | `iios/ai/governance/` | Safety, bias detection, audit, explainability | A1, A5, A6, A7, C9, C11, C13 |
| A9 | `iios/ai/tool_skill/` | Tool registry, sandboxed execution, skill composition | A1, A2, C10, C11, C12, C14 |
| A10 | `iios/ai/orchestration/` | AI workflow orchestration, Core Platform integration | A1–A9, C9, C15, C16 |

---

## Appendix B — Package Root Proposal

```
iios/
├── ai/                          ← AI Platform root (NEW — Phase 3)
│   ├── foundation/              ← A1
│   │   ├── lifecycle/
│   │   ├── engine/
│   │   ├── policies/
│   │   ├── adapters/
│   │   ├── snapshot/
│   │   └── gateway/
│   ├── model_management/        ← A2
│   │   ├── lifecycle/
│   │   ├── engine/
│   │   ├── policies/
│   │   ├── routing/
│   │   ├── snapshot/
│   │   └── gateway/
│   ├── prompt_context/          ← A3
│   ├── memory/                  ← A4
│   ├── agent/                   ← A5
│   ├── collaboration/           ← A6
│   ├── learning/                ← A7
│   ├── governance/              ← A8
│   ├── tool_skill/              ← A9
│   └── orchestration/           ← A10
│
├── workflow/                    ← C16 (FROZEN)
├── integration/                 ← C15 (FROZEN)
├── supervisor/                  ← C13 (FROZEN)
├── knowledge/                   ← C14 (FROZEN)
├── ...                          ← C1–C12 (FROZEN)
└── common/                      ← Shared infrastructure (FROZEN)
```

The AI Platform lives entirely within `iios/ai/`. It introduces no new files into any existing `iios/` sub-directory.

---

*Phase 3 Architecture Specification complete. This document is the authoritative blueprint for the IIOS AI Platform implementation.*  
*No source code, packages, or classes have been created. No Core Platform files have been modified.*
