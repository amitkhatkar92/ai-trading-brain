# AI Platform Version 1.0 — Public API Manifest

**Document:** PUBLIC_API_MANIFEST_V1  
**Version:** 1.0.0  
**Freeze Date:** 2026-08-01  
**Status:** FROZEN — No breaking changes without version increment

All items in this manifest are part of the frozen public surface of AI Platform
Version 1.0.0. Refer to `AI_PLATFORM_V1_RELEASE.md` for certification details.

---

## Contents

1. [Platform Bootstrap](#1-platform-bootstrap)
2. [A1 — AI Foundation](#2-a1--ai-foundation)
3. [A2 — Model Management](#3-a2--model-management)
4. [A3 — Prompt & Context](#4-a3--prompt--context)
5. [A4 — Memory & Knowledge](#5-a4--memory--knowledge)
6. [A5 — Agent Framework](#6-a5--agent-framework)
7. [A6 — Collaboration](#7-a6--collaboration)
8. [A7 — Learning & Evaluation](#8-a7--learning--evaluation)
9. [A8 — Governance](#9-a8--governance)
10. [A9 — Capability Management](#10-a9--capability-management)
11. [A10 — Orchestration](#11-a10--orchestration)
12. [Snapshot Contracts](#12-snapshot-contracts)
13. [Exception Hierarchy](#13-exception-hierarchy)
14. [Protocols](#14-protocols)
15. [Summary Counts](#15-summary-counts)

---

## 1. Platform Bootstrap

**Package:** `iios.ai.platform`  
**Version:** 1.0.0  
**Resolves:** Enterprise Design Review R-001

### 1.1 IIOSBootstrap

```python
class IIOSBootstrap:
    VERSION: str = "1.0.0"

    def register(self, descriptor: PlatformDescriptor, gateway: Any = None) -> None
    def deregister(self, platform_id: str) -> None
    def start(self) -> PlatformStatus
    def stop(self) -> PlatformStatus
    def restart(self) -> PlatformStatus
    def health(self) -> Dict[str, Any]   # {"aggregate": str, "platforms": Dict}
    def status(self) -> PlatformStatus

    @property
    def is_running(self) -> bool
    @property
    def platform_count(self) -> int
```

### 1.2 PlatformRegistry

```python
class PlatformRegistry:
    def register(self, descriptor: PlatformDescriptor, gateway: Any = None) -> None
    def deregister(self, platform_id: str) -> None
    def get_descriptor(self, platform_id: str) -> PlatformDescriptor
    def get_gateway(self, platform_id: str) -> Any
    def get_phase(self, platform_id: str) -> PlatformPhase
    def set_phase(self, platform_id: str, phase: PlatformPhase) -> None
    def is_registered(self, platform_id: str) -> bool
    def list_ids(self) -> List[str]
    def list_all(self) -> List[Tuple[PlatformDescriptor, PlatformPhase]]
    def all_phases(self) -> Dict[str, PlatformPhase]
```

### 1.3 StartupCoordinator

```python
class StartupCoordinator:
    def resolve_startup_order(self) -> StartupOrder
    def start_all(self) -> List[PlatformStartupResult]
```

### 1.4 ShutdownCoordinator

```python
class ShutdownCoordinator:
    def stop_all(self) -> List[PlatformStartupResult]
```

### 1.5 HealthCoordinator

```python
class HealthCoordinator:
    def check_all(self) -> Dict[str, Dict[str, Any]]
    def aggregate_status(self) -> str   # "healthy" | "degraded" | "down" | "unknown"
    def build_platform_status(self) -> PlatformStatus

HEALTH_HEALTHY  = "healthy"
HEALTH_DEGRADED = "degraded"
HEALTH_UNKNOWN  = "unknown"
HEALTH_DOWN     = "down"
```

### 1.6 PlatformLifecycleManager

```python
class PlatformLifecycleManager:
    def start_all(self) -> List[PlatformStartupResult]
    def stop_all(self) -> List[PlatformStartupResult]
    def start_platform(self, platform_id: str) -> PlatformStartupResult
    def stop_platform(self, platform_id: str) -> PlatformStartupResult
    def restart_platform(self, platform_id: str) -> PlatformStartupResult
    def status(self) -> PlatformStatus
    def health(self) -> Dict[str, Any]
```

### 1.7 Data Types

```python
@dataclass(frozen=True)
class PlatformDescriptor:
    platform_id:  str
    name:         str
    version:      str
    dependencies: FrozenSet[str]
    priority:     int
    optional:     bool
    metadata:     FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(cls, platform_id, *, name="", version="1.0.0",
               dependencies=frozenset(), priority=100, optional=False,
               **metadata) -> PlatformDescriptor

@dataclass(frozen=True)
class PlatformDependency:
    dependent_id:  str
    dependency_id: str

@dataclass(frozen=True)
class PlatformStartupResult:
    platform_id: str
    phase:       PlatformPhase
    elapsed_ms:  float
    error:       Optional[str]

    @property def succeeded(self) -> bool
    @property def failed(self) -> bool
    @classmethod def success(cls, platform_id, elapsed_ms) -> PlatformStartupResult
    @classmethod def failure(cls, platform_id, elapsed_ms, error) -> PlatformStartupResult
    @classmethod def stopped(cls, platform_id, elapsed_ms) -> PlatformStartupResult

@dataclass(frozen=True)
class PlatformStatus:
    snapshot_id:       str
    captured_at:       float
    total_platforms:   int
    running_platforms: int
    failed_platforms:  int
    stopped_platforms: int
    platform_phases:   FrozenSet[Tuple[str, str]]
    startup_results:   Tuple[PlatformStartupResult, ...]

    @property def is_fully_operational(self) -> bool
    @classmethod def create(cls, phases, results) -> PlatformStatus

@dataclass(frozen=True)
class StartupOrder:
    batches:        Tuple[Tuple[str, ...], ...]
    platform_count: int
    def flat_order(self) -> Tuple[str, ...]

class PlatformPhase(str, Enum):
    REGISTERED = "registered"
    STARTING   = "starting"
    RUNNING    = "running"
    STOPPING   = "stopping"
    STOPPED    = "stopped"
    FAILED     = "failed"
    def is_terminal(self) -> bool
    def is_active(self) -> bool
```

### 1.8 Errors

```python
class PlatformRegistryError(RuntimeError): ...
class CircularDependencyError(RuntimeError): ...
```

### 1.9 Module Constants

```python
# iios.ai.platform
__version__    = "1.0.0"
__status__     = "implemented"
__resolves__   = "R-001"
FREEZE_VERSION = "1.0.0"
FREEZE_DATE    = "2026-08-01"

# iios.ai.platform.iios_bootstrap
BOOTSTRAP_VERSION = "1.0.0"
```

---

## 2. A1 — AI Foundation

**Package:** `iios.ai.foundation`  
**Gateway:** `AIFoundationGateway` (`iios.ai.foundation.gateway.ai_foundation_gateway`)  
**MODULE_ID:** A1 | **SYSTEM_ID:** `iios:ai:foundation:gateway`

### 2.1 Gateway Methods

```python
class AIFoundationGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:foundation:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A1"
    MODULE_NAME : str = "AI Foundation"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "AI Platform foundation — lifecycle management, provider abstraction, events, configuration"
    STATUS      : str = "stable"

    # Lifecycle (from AILifecycleAwareMixin)
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Provider management
    def register_provider(self, provider: AIProvider) -> None
    def deregister_provider(self, provider_id: str) -> None

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def statistics(self) -> Dict[str, Any]
    def snapshot(self) -> FoundationSnapshot

    # Metrics
    def record_request(self, *, error: bool = False) -> None

    # Properties
    @property def event_bus(self) -> AIEventBus
    @property def configuration(self) -> Optional[AIConfiguration]
    @property def provider_registry(self) -> AIProviderRegistry
```

---

## 3. A2 — Model Management

**Package:** `iios.ai.model_management`  
**Gateway:** `ModelManagementGateway`  
**MODULE_ID:** A2 | **SYSTEM_ID:** `iios:ai:model_management:gateway`

### 3.1 Gateway Methods

```python
class ModelManagementGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:model_management:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A2"
    MODULE_NAME : str = "Model Management"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "AI model registry, routing, capability management and health monitoring"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Model registry
    def register_model(self, name: str, category: ModelCategory,
                       capabilities: FrozenSet[ModelCapabilityType], *,
                       tier: ModelTier = ..., provider_id: str = "",
                       description: str = "", tags: Tuple[str, ...] = (),
                       owner: str = "", context_window: int = 4_096,
                       max_output_tokens: int = 1_024,
                       parameters_billions: float = 0.0) -> AIModel
    def remove_model(self, model_id: str) -> None
    def enable_model(self, model_id: str) -> None
    def disable_model(self, model_id: str) -> None
    def get_model(self, model_id: str) -> AIModel
    def find_model(self, name: str) -> Optional[AIModel]
    def list_models(self, *, category: Optional[ModelCategory] = None,
                    capability: Optional[ModelCapabilityType] = None,
                    tier: Optional[ModelTier] = None,
                    enabled_only: bool = False) -> List[AIModel]

    # Version management
    def add_version(self, model_id: str, capabilities: FrozenSet[ModelCapabilityType],
                    *, context_window: int = 4_096, max_output_tokens: int = 1_024,
                    parameters_billions: float = 0.0, activate: bool = True) -> AIModelVersion
    def activate_version(self, model_id: str, version_id: str) -> AIModelVersion
    def rollback(self, model_id: str, version_id: str) -> AIModelVersion
    def version_history(self, model_id: str) -> List[AIModelVersion]

    # Capabilities & routing
    def list_capabilities(self) -> List[ModelCapabilityType]
    def route_request(self, context: RoutingContext) -> RoutingDecision

    # Health monitoring
    def get_health(self, model_id: str) -> HealthReport
    def record_success(self, model_id: str) -> None
    def record_failure(self, model_id: str) -> None
    def all_health(self) -> Dict[str, HealthReport]

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> ModelManagementSnapshot

    # Properties
    @property def event_bus(self) -> ModelEventBus
    @property def container(self) -> ModelManagementContainer   # [F3-OBS-001]
```

---

## 4. A3 — Prompt & Context

**Package:** `iios.ai.prompt_context`  
**Gateway:** `PromptContextGateway`  
**MODULE_ID:** A3 | **SYSTEM_ID:** `iios:ai:prompt_context:gateway`

### 4.1 Gateway Methods

```python
class PromptContextGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:prompt_context:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A3"
    MODULE_NAME : str = "Prompt & Context"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "Prompt template management, context assembly and validation"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Template registry
    def register_prompt(self, name: str, category: PromptCategory,
                        template_text: str, *, description: str = "",
                        tags: Tuple[str, ...] = (), owner: str = "",
                        variables: Tuple[str, ...] = (),
                        changed_by: str = "system") -> PromptTemplate
    def remove_prompt(self, prompt_id: str) -> None
    def enable_prompt(self, prompt_id: str) -> None
    def disable_prompt(self, prompt_id: str) -> None
    def get_prompt(self, prompt_id: str) -> PromptTemplate
    def find_prompt_by_name(self, name: str) -> Optional[PromptTemplate]
    def list_templates(self, *, category: Optional[PromptCategory] = None,
                       tag: Optional[str] = None,
                       enabled_only: bool = False) -> List[PromptTemplate]

    # Version management
    def add_version(self, prompt_id: str, template_text: str,
                    *, variables: Tuple[str, ...] = (), changed_by: str = "system",
                    reason: str = "", activate: bool = True) -> PromptVersion
    def activate_version(self, prompt_id: str, version_id: str) -> PromptVersion
    def rollback(self, prompt_id: str, version_id: str) -> PromptVersion
    def version_history(self, prompt_id: str) -> List[PromptVersion]

    # Context & composition
    def build_context(self, session_id: str, module_id: str,
                      *, max_tokens: Optional[int] = None,
                      trace_id: str = "") -> ContextBuilder
    def compose_prompt(self, prompt_id: str, variables: Dict[str, Any],
                       *, context: Optional[AssembledContext] = None) -> PromptResult
    def validate_prompt(self, prompt_id: str,
                        variables: Optional[Dict[str, Any]] = None) -> ValidationResult
    def validate_context(self, context: AssembledContext) -> ValidationResult

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> PromptContextSnapshot

    # Properties
    @property def event_bus(self) -> PromptEventBus
    @property def container(self) -> PromptContextContainer   # [F3-OBS-001]
```

---

## 5. A4 — Memory & Knowledge

**Package:** `iios.ai.memory_knowledge`  
**Gateway:** `MemoryKnowledgeGateway`  
**MODULE_ID:** A4 | **SYSTEM_ID:** `iios:ai:memory_knowledge:gateway`

### 5.1 Gateway Methods

```python
class MemoryKnowledgeGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:memory_knowledge:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A4"
    MODULE_NAME : str = "Memory & Knowledge"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "Agent memory storage and knowledge base management"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Memory
    def store_memory(self, content: Any, scope: MemoryScope = MemoryScope.SESSION,
                     owner_id: str = "system", tags: FrozenSet[str] = frozenset(),
                     expires_at: Optional[float] = None, source: str = "",
                     *, entry_id: Optional[str] = None) -> MemoryEntry
    def retrieve_memory(self, entry_id: str) -> MemoryEntry
    def update_memory(self, entry_id: str, new_content: Any) -> MemoryEntry
    def delete_memory(self, entry_id: str) -> None
    def list_memory(self, *, scope: Optional[MemoryScope] = None,
                    owner_id: Optional[str] = None,
                    tags: Optional[FrozenSet[str]] = None) -> List[MemoryEntry]
    def evict_expired_memory(self) -> int

    # Knowledge base
    def add_knowledge(self, title: str, content: Any,
                      category: KnowledgeCategory = KnowledgeCategory.DOCUMENT,
                      tags: FrozenSet[str] = frozenset(), author: str = "system",
                      source: str = "", language: str = "en",
                      collection_id: Optional[str] = None,
                      *, item_id: Optional[str] = None) -> KnowledgeItem
    def remove_knowledge(self, item_id: str) -> None
    def update_knowledge(self, item_id: str, new_content: Any) -> KnowledgeItem
    def get_knowledge(self, item_id: str) -> KnowledgeItem
    def search_knowledge(self, query: str, top_k: int = 10,
                         category: Optional[KnowledgeCategory] = None,
                         tags: Optional[FrozenSet[str]] = None) -> List[KnowledgeItem]
    def list_knowledge(self, *, category: Optional[KnowledgeCategory] = None,
                       tags: Optional[FrozenSet[str]] = None) -> List[KnowledgeItem]
    def retrieve(self, request: RetrievalRequest) -> RetrievalResult

    # Collections
    def create_collection(self, name: str, category: KnowledgeCategory,
                          description: str = "", tags: FrozenSet[str] = frozenset(),
                          *, collection_id: Optional[str] = None) -> KnowledgeCollection
    def list_collections(self) -> List[KnowledgeCollection]

    # Knowledge graph
    def add_graph_node(self, node: KnowledgeNode) -> None
    def add_graph_relationship(self, rel: KnowledgeRelationship) -> None
    def get_graph_node(self, node_id: str) -> Optional[KnowledgeNode]
    def shortest_path(self, start_id: str, end_id: str) -> Optional[KnowledgePath]
    def traverse_graph(self, start_id: str, max_depth: int = 3) -> List[KnowledgeNode]

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> MemoryKnowledgeSnapshot
```

---

## 6. A5 — Agent Framework

**Package:** `iios.ai.agent_framework`  
**Gateway:** `AgentFrameworkGateway`  
**MODULE_ID:** A5 | **SYSTEM_ID:** `iios:ai:agent_framework:gateway`

### 6.1 Gateway Methods

```python
class AgentFrameworkGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:agent_framework:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A5"
    MODULE_NAME : str = "Agent Framework"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "AI agent lifecycle, task execution and coordination framework"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Agent registry
    def register_agent(self, agent: BaseAIAgent) -> AgentDescriptor
    def create_and_register(self, spec: AgentSpec) -> BaseAIAgent
    def find_agent(self, agent_id: str) -> BaseAIAgent
    def list_agents(self) -> List[AgentDescriptor]
    def find_agents_by_capability(self, capability_type: CapabilityType) -> List[AgentDescriptor]

    # Agent lifecycle
    def start_agent(self, agent_id: str) -> None
    def stop_agent(self, agent_id: str) -> None
    def suspend_agent(self, agent_id: str) -> None
    def resume_agent(self, agent_id: str) -> None

    # Task execution
    def assign_task(self, task: AgentTask) -> AgentResult

    # Monitoring
    def get_agent_health(self, agent_id: str) -> AgentHealth
    def get_agent_metrics(self, agent_id: str) -> AgentMetrics

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> AgentFrameworkSnapshot
```

---

## 7. A6 — Collaboration

**Package:** `iios.ai.collaboration`  
**Gateway:** `CollaborationGateway`  
**MODULE_ID:** A6 | **SYSTEM_ID:** `iios:ai:collaboration:gateway`

### 7.1 Gateway Methods

```python
class CollaborationGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:collaboration:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A6"
    MODULE_NAME : str = "Collaboration Framework"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "Multi-agent debate, consensus and collaboration coordination"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Session management
    def create_collaboration(self, topic: str,
                             collaboration_type: CollaborationType = CollaborationType.DEBATE,
                             created_by: str = "system", **kwargs) -> str
    def close_session(self, session_id: str) -> CollaborationResult
    def invite_agent(self, session_id: str, agent_id: str, agent_name: str,
                     agent_type: str, role: CollaborationRole,
                     weight: float = 1.0) -> Participant

    # Debate
    def start_debate(self, session_id: str) -> None
    def submit_argument(self, session_id: str, agent_id: str,
                        position_type: PositionType, argument: str = "",
                        evidence: FrozenSet[str] = frozenset(),
                        confidence: float = 1.0,
                        responds_to: Optional[str] = None) -> DebatePosition
    def next_round(self, session_id: str) -> None
    def close_debate(self, session_id: str) -> DebateResult
    def vote(self, session_id: str, agent_id: str,
             position_type: PositionType, confidence: float = 1.0) -> DebatePosition
    def calculate_consensus(self, session_id: str,
                            strategy: str = "majority") -> ConsensusResult

    # Messaging
    def send_message(self, session_id: str, sender_id: str, recipient_id: str,
                     content: Any,
                     message_type: MessageType = MessageType.DIRECT) -> AgentMessage
    def broadcast_message(self, session_id: str, sender_id: str,
                          content: Any) -> AgentMessage

    # Escalation
    def escalate(self, session_id: str, trigger: EscalationTrigger,
                 reason: str, requested_by: str = "system") -> EscalationRequest

    # Observability
    def get_session_snapshot(self, session_id: str) -> CollaborationSessionSnapshot
    def list_sessions(self) -> List[CollaborationSessionSnapshot]
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> CollaborationFrameworkSnapshot
```

---

## 8. A7 — Learning & Evaluation

**Package:** `iios.ai.learning_evaluation`  
**Gateway:** `LearningEvaluationGateway`  
**MODULE_ID:** A7 | **SYSTEM_ID:** `iios:ai:learning_evaluation:gateway`

### 8.1 Gateway Methods

```python
class LearningEvaluationGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:learning_evaluation:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A7"
    MODULE_NAME : str = "Learning & Evaluation"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "Model evaluation, quality benchmarking and adaptive learning"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Evaluation sessions
    def create_session(self, metadata: EvaluationMetadata) -> EvaluationSession
    def evaluate(self, session_id: str, request: EvaluationRequest,
                 evaluator_fn: Callable[[EvaluationRequest], EvaluationResult]) -> EvaluationResult
    def complete_session(self, session_id: str) -> None
    def get_session(self, session_id: str) -> EvaluationSession
    def list_sessions(self, status: Optional[EvaluationStatus] = None) -> list  # [F3-OBS-003]

    # Benchmarking
    def register_suite(self, suite: BenchmarkSuite) -> None
    def benchmark(self, suite_id: str, evaluator_fn: Callable,
                  pass_threshold: float = 0.6) -> BenchmarkResult
    def list_benchmarks(self) -> List[BenchmarkSuite]

    # Learning & feedback
    def record_learning(self, source_id: str, category: LearningCategory,
                        observation: Any, signal: float = 0.0,
                        session_id: Optional[str] = None,
                        **metadata: Any) -> LearningRecord
    def submit_feedback(self, target_id: str, submitted_by: str,
                        feedback_type: FeedbackType, content: Any,
                        sentiment: FeedbackSentiment = FeedbackSentiment.NEUTRAL,
                        rating: Optional[float] = None,
                        **metadata: Any) -> FeedbackRecord
    def generate_report(self, source_id: str) -> List[ImprovementRecommendation]
    def assess_quality(self, target_id: str, session_id: str,
                       content: Any) -> Tuple[QualityScore, ValidationReport]

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> LearningEvaluationFrameworkSnapshot
```

---

## 9. A8 — Governance

**Package:** `iios.ai.governance`  
**Gateway:** `GovernanceGateway`  
**MODULE_ID:** A8 | **SYSTEM_ID:** `iios:ai:governance:gateway`

### 9.1 Gateway Methods

```python
class GovernanceGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:governance:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A8"
    MODULE_NAME : str = "Governance"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "Policy governance, permission enforcement and audit logging"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Policy
    def evaluate_policy(self, context: GovernanceContext,
                        risk_context: Optional[Dict[str, float]] = None,
                        explain: bool = True) -> GovernanceDecision
    def register_policy(self, policy: GovernancePolicy) -> None
    def deregister_policy(self, policy_id: str) -> None
    def list_policies(self) -> List[GovernancePolicy]
    def list_violations(self, limit: int = 100) -> List[PolicyViolation]
    def evaluate_policy_only(self, context: GovernanceContext) -> GovernanceDecision

    # Access control
    def authorize(self, principal_id: str, capability: str) -> None
    def is_authorized(self, principal_id: str, capability: str) -> bool
    def assign_role(self, principal_id: str, role_name: str) -> None
    def revoke_role(self, principal_id: str, role_name: str) -> None
    def create_role(self, role: RolePolicy) -> None
    def list_roles(self) -> List[RolePolicy]
    def add_restriction(self, restriction: CapabilityRestriction) -> None

    # Audit
    def record_audit(self, event_type: AuditEventType, subject_id: str,
                     principal_id: str, action: str, resource: str, outcome: str,
                     notes: str = "", **context: Any) -> AuditRecord
    def query_audit(self, subject_id: Optional[str] = None,
                    event_type: Optional[AuditEventType] = None,
                    since: Optional[float] = None, limit: int = 500) -> List[AuditRecord]
    def generate_audit_report(self, subject_id: str) -> AuditReport
    def verify_audit_integrity(self) -> bool

    # Explainability
    def generate_explanation(self, decision: GovernanceDecision,
                             subject_id: str, **kwargs: Any) -> Explanation
    def get_explanation(self, explanation_id: str) -> Explanation
    def explanations_for_decision(self, decision_id: str) -> List[Explanation]

    # Compliance
    def check_compliance(self, subject_id: str, subject: Any,
                         framework: Optional[ComplianceFramework] = None,
                         raise_on_blocking: bool = False) -> ComplianceReport
    def add_compliance_rule(self, rule: ComplianceRule) -> None
    def list_compliance_rules(self) -> List[ComplianceRule]

    # Risk
    def add_risk_policy(self, policy: RiskPolicy) -> None
    def evaluate_risk(self, subject_id: str, risk_context: Dict[str, float],
                      raise_on_exceed: bool = False) -> List[RiskViolation]
    def list_risk_violations(self, subject_id: Optional[str] = None) -> List[RiskViolation]

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> GovernanceFrameworkSnapshot
```

---

## 10. A9 — Capability Management

**Package:** `iios.ai.capability`  
**Gateway:** `CapabilityGateway`  
**MODULE_ID:** A9 | **SYSTEM_ID:** `iios:ai:capability:gateway`

### 10.1 Gateway Methods

```python
class CapabilityGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:capability:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A9"
    MODULE_NAME : str = "Capability Management"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "AI capability registry, skill management and quota enforcement"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Capability registry
    def register_capability(self, descriptor: CapabilityDescriptor) -> None
    def deregister_capability(self, capability_id: str) -> None
    def find_capability(self, capability_id: str) -> Optional[CapabilityDescriptor]
    def get_capability(self, capability_id: str) -> CapabilityDescriptor
    def list_capabilities(self, capability_type: Optional[CapabilityType] = None,
                          category: Optional[CapabilityCategory] = None,
                          tags: Optional[FrozenSet[str]] = None,
                          active_only: bool = False) -> List[CapabilityDescriptor]
    def enable_capability(self, capability_id: str) -> None
    def disable_capability(self, capability_id: str) -> None
    def register_handler(self, capability_id: str,
                         handler: Callable[[Dict[str, Any]], Any]) -> None
    def execute_capability(self, request: CapabilityRequest) -> CapabilityResponse

    # Authorization
    def authorize_capability(self, principal_id: str, capability_id: str) -> bool
    def is_authorized(self, principal_id: str, capability_id: str) -> bool
    def grant_permission(self, permission: CapabilityPermission) -> None
    def revoke_permission(self, principal_id: str, capability_id: str) -> None
    def list_permissions(self, principal_id: str) -> List[CapabilityPermission]
    def create_role(self, role: CapabilityRole) -> None
    def assign_role(self, principal_id: str, role_name: str) -> None
    def revoke_role(self, principal_id: str, role_name: str) -> None
    def list_roles(self) -> List[CapabilityRole]

    # Policy
    def add_policy(self, policy: CapabilityPolicy) -> None
    def remove_policy(self, policy_id: str) -> None
    def evaluate_policy(self, principal_id: str, capability_id: str) -> bool
    def list_policies(self) -> List[CapabilityPolicy]

    # Quota
    def set_quota(self, principal_id: str, capability_id: str,
                  max_per_hour: int = 0, max_per_day: int = 0) -> None
    def check_quota(self, principal_id: str, capability_id: str) -> bool
    def get_usage(self, principal_id: str, capability_id: str) -> Dict[str, int]

    # Connectors
    def register_connector(self, connector: BaseConnector) -> None
    def get_connector(self, connector_id: str) -> BaseConnector
    def list_connectors(self, connector_type: Optional[ConnectorType] = None) -> List[BaseConnector]

    # Skills
    def register_skill(self, skill: BaseSkill) -> None
    def get_skill(self, skill_id: str) -> BaseSkill
    def list_skills(self, category: Optional[SkillCategory] = None) -> List[BaseSkill]

    # Audit
    def query_audit(self, principal_id: Optional[str] = None,
                    capability_id: Optional[str] = None,
                    since: Optional[float] = None, limit: int = 500) -> list
    def audit_report(self, principal_id: str) -> CapabilityAuditReport

    # Observability
    def health(self) -> Dict[str, Any]
    def status(self) -> Dict[str, Any]
    def snapshot(self) -> CapabilitySystemSnapshot
```

---

## 11. A10 — Orchestration

**Package:** `iios.ai.orchestrator`  
**Gateway:** `OrchestratorGateway`  
**MODULE_ID:** A10 | **SYSTEM_ID:** `iios:ai:orchestrator:gateway`

### 11.1 Gateway Methods

```python
class OrchestratorGateway(AILifecycleAwareMixin):
    SYSTEM_ID   : str = "iios:ai:orchestrator:gateway"
    VERSION     : str = "1.0.0"
    MODULE_ID   : str = "A10"
    MODULE_NAME : str = "Orchestration"
    API_VERSION : str = "v1"
    DESCRIPTION : str = "Workflow orchestration, task scheduling and execution coordination"
    STATUS      : str = "stable"

    # Lifecycle
    def start(self) -> None
    def stop(self) -> None
    def restart(self) -> None

    # Objective & session
    def register_step_handler(self, action: str,
                              handler_fn: Callable[[Dict], Any]) -> None
    def submit_objective(self, objective: str, principal_id: str,
                         **metadata: str) -> str
    def get_session(self, session_id: str) -> OrchestrationSession
    def get_execution_status(self, session_id: str) -> Dict
    def cancel_session(self, session_id: str) -> None

    # Planning
    def generate_plan(self, session_id: str) -> ExecutionPlan
    def execute_plan(self, session_id: str) -> OrchestrationResult
    def replan(self, session_id: str, failed_step_id: str) -> ExecutionPlan

    # Workflows
    def register_workflow(self, definition: WorkflowDefinition) -> None
    def start_workflow(self, workflow_id: str, objective: str,
                       principal_id: str) -> str
    def pause_workflow(self, instance_id: str) -> None
    def resume_workflow(self, instance_id: str) -> None
    def cancel_workflow(self, instance_id: str) -> None
    def execute_workflow_step(self, instance_id: str, step_id: str) -> Any
    def get_workflow_state(self, instance_id: str) -> WorkflowState
    def list_workflows(self) -> List[WorkflowDefinition]

    # Task scheduling
    def register_task_handler(self, action: str,
                               handler_fn: Callable[[Dict], Any]) -> None
    def schedule_task(self, task: ScheduledTask) -> str
    def cancel_task(self, task_id: str) -> None
    def run_pending_tasks(self) -> List[str]

    # Resource management
    def register_agent(self, agent_id: str, capabilities: FrozenSet[str],
                       max_concurrent: int = 1) -> None
    def allocate_agent(self, capability_id: str) -> str
    def release_agent(self, agent_id: str) -> None
    def reserve_resource(self, capability_id: str, requester_id: str,
                         **metadata: Any) -> ResourceReservation
    def release_resource(self, capability_id: str) -> None

    # Recovery
    def register_recovery_strategy(self, strategy: RecoveryStrategy) -> None
    def recover(self, session_id: str, failed_step_id: str,
                error: Exception) -> bool
    def register_rollback(self, session_id: str, step_id: str,
                          rollback_fn: Callable) -> None

    # Observability
    def get_progress(self, session_id: str) -> float
    def get_metrics(self, session_id: str) -> ExecutionMetrics
    def get_timeline(self, session_id: str) -> Timeline
    def health(self) -> Dict
    def status(self) -> Dict
    def snapshot(self) -> OrchestratorSnapshot
```

---

## 12. Snapshot Contracts

All snapshots are **immutable frozen dataclasses** with `captured_at: float`.

### 12.1 Domain Snapshots (12 types)

| Module | Class | Location |
|---|---|---|
| A1 | `FoundationSnapshot` | `iios.ai.foundation.snapshot.foundation_snapshot` |
| A2 | `ModelManagementSnapshot` | `iios.ai.model_management.snapshot.model_management_snapshot` |
| A3 | `PromptContextSnapshot` | `iios.ai.prompt_context.snapshot.prompt_context_snapshot` |
| A4 | `MemoryKnowledgeSnapshot` | `iios.ai.memory_knowledge.snapshot.memory_knowledge_snapshot` |
| A5 | `AgentFrameworkSnapshot` | `iios.ai.agent_framework.snapshot.agent_snapshot` |
| A6 | `CollaborationFrameworkSnapshot` | `iios.ai.collaboration.snapshot.collaboration_snapshot` |
| A6 | `CollaborationSessionSnapshot` | `iios.ai.collaboration.snapshot.collaboration_snapshot` |
| A7 | `LearningEvaluationFrameworkSnapshot` | `iios.ai.learning_evaluation.snapshot.learning_evaluation_snapshot` |
| A7 | `EvaluationSessionSnapshot` | `iios.ai.learning_evaluation.snapshot.learning_evaluation_snapshot` |
| A8 | `GovernanceFrameworkSnapshot` | `iios.ai.governance.snapshot.governance_snapshot` |
| A9 | `CapabilitySystemSnapshot` | `iios.ai.capability.snapshot.capability_snapshot` |
| A10 | `OrchestratorSnapshot` | `iios.ai.orchestrator.snapshot.orchestrator_snapshot` |

### 12.2 Platform Data Types (5 types)

| Class | Location |
|---|---|
| `PlatformStatus` | `iios.ai.platform.platform_types` |
| `PlatformStartupResult` | `iios.ai.platform.platform_types` |
| `PlatformDescriptor` | `iios.ai.platform.platform_types` |
| `PlatformDependency` | `iios.ai.platform.platform_types` |
| `StartupOrder` | `iios.ai.platform.platform_types` |

### 12.3 Deprecated Snapshot Aliases (4 properties — removal in v2.0)

These snapshots retain a deprecated `@property taken_at` wrapping `captured_at`:

| Snapshot | Deprecated Property | Canonical Field |
|---|---|---|
| `ModelManagementSnapshot` | `taken_at` | `captured_at` |
| `PromptContextSnapshot` | `taken_at` | `captured_at` |
| `MemoryKnowledgeSnapshot` | `taken_at` | `captured_at` |
| `AgentFrameworkSnapshot` | `taken_at` | `captured_at` |

**Note:** A1 `FoundationSnapshot` uses `timestamp` instead of `captured_at`. Alignment
deferred to v2.0 (F3-OBS-004).

---

## 13. Exception Hierarchy

All exceptions extend `AIException → IIOSError`. Error codes are frozen.

### 13.1 A1 Foundation (AI-000 – AI-702)

| Class | Code | Base |
|---|---|---|
| `AIException` | AI-000 | `IIOSError` |
| `AIConfigurationException` | AI-100 | `AIException` |
| `AIMissingConfigurationException` | AI-101 | `AIConfigurationException` |
| `AIInvalidConfigurationException` | AI-102 | `AIConfigurationException` |
| `AISessionException` | AI-200 | `AIException` |
| `AISessionNotFoundError` | AI-201 | `AISessionException` |
| `AISessionExpiredError` | AI-202 | `AISessionException` |
| `AISessionLimitError` | AI-203 | `AISessionException` |
| `AISessionStateError` | AI-204 | `AISessionException` |
| `AIContextException` | AI-300 | `AIException` |
| `AIContextTooLargeError` | AI-301 | `AIContextException` |
| `AIContextValidationError` | AI-302 | `AIContextException` |
| `AIContextBuildError` | AI-303 | `AIContextException` |
| `AIRequestException` | AI-400 | `AIException` |
| `AIRequestValidationError` | AI-401 | `AIRequestException` |
| `AIRequestTimeoutError` | AI-402 | `AIRequestException` |
| `AIRequestCancelledError` | AI-403 | `AIRequestException` |
| `AIProviderException` | AI-500 | `AIException` |
| `AIProviderNotAvailableError` | AI-501 | `AIProviderException` |
| `AIProviderAuthError` | AI-502 | `AIProviderException` |
| `AIProviderRateLimitError` | AI-503 | `AIProviderException` |
| `AIProviderCapabilityError` | AI-504 | `AIProviderException` |
| `AIExecutionException` | AI-600 | `AIException` |
| `AIPipelineError` | AI-601 | `AIExecutionException` |
| `AIPipelineStageError` | AI-602 | `AIExecutionException` |
| `AIExecutionTimeoutError` | AI-603 | `AIExecutionException` |
| `AIValidationException` | AI-700 | `AIException` |
| `AIResponseValidationError` | AI-701 | `AIValidationException` |
| `AIPolicyViolationError` | AI-702 | `AIValidationException` |

### 13.2 A2 Model Management (AI-850 – AI-880)

| Class | Code | Base |
|---|---|---|
| `AIModelException` | AI-850 | `AIException` |
| `AIModelNotFoundError` | AI-851 | `AIModelException` |
| `AIModelAlreadyExistsError` | AI-852 | `AIModelException` |
| `AIModelVersionError` | AI-853 | `AIModelException` |
| `AIModelDisabledError` | AI-854 | `AIModelException` |
| `AIModelValidationError` | AI-855 | `AIModelException` |
| `AIRoutingException` | AI-860 | `AIModelException` |
| `AINoModelAvailableError` | AI-861 | `AIRoutingException` |
| `AIRoutingFailedError` | AI-862 | `AIRoutingException` |
| `AIFailoverExhaustedError` | AI-863 | `AIRoutingException` |
| `AIHealthException` | AI-870 | `AIModelException` |
| `AIModelUnhealthyError` | AI-871 | `AIHealthException` |
| `AIModelConfigurationError` | AI-875 | `AIModelException` |
| `AIModelPolicyViolationError` | AI-880 | `AIModelException` |

### 13.3 A3 Prompt & Context (AI-800 – AI-830)

| Class | Code | Base |
|---|---|---|
| `AIPromptException` | AI-800 | `AIException` |
| `AIPromptNotFoundError` | AI-801 | `AIPromptException` |
| `AIPromptAlreadyExistsError` | AI-802 | `AIPromptException` |
| `AIPromptVersionError` | AI-803 | `AIPromptException` |
| `AIPromptDisabledError` | AI-804 | `AIPromptException` |
| `AIPromptValidationError` | AI-805 | `AIPromptException` |
| `AIContextAssemblyException` | AI-810 | `AIException` |
| `AIContextIncompleteError` | AI-811 | `AIContextAssemblyException` |
| `AIContextBudgetExceededError` | AI-812 | `AIContextAssemblyException` |
| `AIVariableException` | AI-820 | `AIException` |
| `AIMissingVariableError` | AI-821 | `AIVariableException` |
| `AIInvalidVariableError` | AI-822 | `AIVariableException` |
| `AIPromptPolicyViolationError` | AI-830 | `AIException` |

### 13.4 A4 Memory & Knowledge (AI-900 – AI-950)

| Class | Code | Base |
|---|---|---|
| `AIMemoryException` | AI-900 | `AIException` |
| `AIMemoryNotFoundError` | AI-901 | `AIMemoryException` |
| `AIMemoryAlreadyExistsError` | AI-902 | `AIMemoryException` |
| `AIMemoryExpiredError` | AI-903 | `AIMemoryException` |
| `AIMemoryStorageError` | AI-904 | `AIMemoryException` |
| `AIMemoryCapacityError` | AI-905 | `AIMemoryException` |
| `AIKnowledgeException` | AI-910 | `AIException` |
| `AIKnowledgeNotFoundError` | AI-911 | `AIKnowledgeException` |
| `AIKnowledgeAlreadyExistsError` | AI-912 | `AIKnowledgeException` |
| `AIKnowledgeValidationError` | AI-913 | `AIKnowledgeException` |
| `AIRetrievalException` | AI-920 | `AIException` |
| `AIRetrievalFailedError` | AI-921 | `AIRetrievalException` |
| `AINoResultsError` | AI-922 | `AIRetrievalException` |
| `AIVectorStoreException` | AI-930 | `AIException` |
| `AIVectorStoreNotReadyError` | AI-931 | `AIVectorStoreException` |
| `AIEmbeddingServiceException` | AI-940 | `AIException` |
| `AIMemoryPolicyViolationError` | AI-950 | `AIException` |

### 13.5 A5 Agent Framework (AI-1000 – AI-1061)

| Class | Code | Base | Alias |
|---|---|---|---|
| `AIAgentException` | AI-1000 | `AIException` | |
| `AIAgentNotFoundError` | AI-1001 | `AIAgentException` | |
| `AIAgentAlreadyExistsError` | AI-1002 | `AIAgentException` | |
| `AIAgentNotRunningError` | AI-1003 | `AIAgentException` | |
| `AIAgentAlreadyRunningError` | AI-1004 | `AIAgentException` | |
| `AIAgentValidationError` | AI-1005 | `AIAgentException` | |
| `AITaskException` | AI-1010 | `AIAgentException` | |
| `AITaskNotFoundError` | AI-1011 | `AITaskException` | |
| `AITaskExecutionError` | AI-1012 | `AITaskException` | |
| `AITaskTimeoutError` | AI-1013 | `AITaskException` | |
| `AICapabilityException` | AI-1020 | `AIAgentException` | |
| `AICapabilityNotFoundError` | AI-1021 | `AICapabilityException` | |
| `AICapabilityNotPermittedError` | AI-1022 | `AICapabilityException` | |
| `AIRegistryException` | AI-1030 | `AIAgentException` | |
| `AIRegistrationFailedError` | AI-1031 | `AIRegistryException` | |
| `AIAgentPermissionException` | AI-1040 | `AIAgentException` | |
| `AIAgentPermissionDeniedError` | AI-1041 | `AIAgentPermissionException` | |
| `AIPermissionNotFoundError` | AI-1042 | `AIAgentPermissionException` | |
| `AIRoleException` | AI-1050 | `AIAgentException` | |
| `AIAgentRoleNotFoundError` | AI-1051 | `AIRoleException` | |
| `AIAgentPolicyException` | AI-1060 | `AIAgentException` | |
| `AIAgentPolicyViolationError` | AI-1061 | `AIAgentPolicyException` | |
| `AIPermissionException` *(alias)* | AI-1040 | — | → `AIAgentPermissionException` |
| `AIPermissionDeniedError` *(alias)* | AI-1041 | — | → `AIAgentPermissionDeniedError` |
| `AIRoleNotFoundError` *(alias)* | AI-1051 | — | → `AIAgentRoleNotFoundError` |
| `AIPolicyException` *(alias)* | AI-1060 | — | → `AIAgentPolicyException` |

### 13.6 A6 Collaboration (AI-1100 – AI-1151)

| Class | Code | Base |
|---|---|---|
| `AICollaborationException` | AI-1100 | `AIException` |
| `AICollaborationSessionNotFoundError` | AI-1101 | `AICollaborationException` |
| `AICollaborationSessionAlreadyExistsError` | AI-1102 | `AICollaborationException` |
| `AICollaborationSessionClosedError` | AI-1103 | `AICollaborationException` |
| `AICollaborationParticipantNotFoundError` | AI-1104 | `AICollaborationException` |
| `AICollaborationParticipantAlreadyExistsError` | AI-1105 | `AICollaborationException` |
| `AICollaborationValidationError` | AI-1106 | `AICollaborationException` |
| `AIMessageException` | AI-1110 | `AICollaborationException` |
| `AIMessageNotFoundError` | AI-1111 | `AIMessageException` |
| `AIMessageRoutingError` | AI-1112 | `AIMessageException` |
| `AIDebateException` | AI-1120 | `AICollaborationException` |
| `AIDebateNotFoundError` | AI-1121 | `AIDebateException` |
| `AIDebateAlreadyClosedError` | AI-1122 | `AIDebateException` |
| `AIDebateRoundError` | AI-1123 | `AIDebateException` |
| `AIConsensusException` | AI-1130 | `AICollaborationException` |
| `AIConsensusFailedError` | AI-1131 | `AIConsensusException` |
| `AIConsensusTimeoutError` | AI-1132 | `AIConsensusException` |
| `AIEscalationException` | AI-1140 | `AICollaborationException` |
| `AIEscalationNotFoundError` | AI-1141 | `AIEscalationException` |
| `AIEscalationPolicyViolationError` | AI-1142 | `AIEscalationException` |
| `AICollaborationPolicyException` | AI-1150 | `AICollaborationException` |
| `AICollaborationPolicyViolationError` | AI-1151 | `AICollaborationPolicyException` |

### 13.7 A7 Learning & Evaluation (AI-1200 – AI-1251)

| Class | Code | Base | Alias |
|---|---|---|---|
| `AILearningEvaluationException` | AI-1200 | `AIException` | |
| `AIEvaluationSessionNotFoundError` | AI-1201 | `AILearningEvaluationException` | |
| `AIEvaluationSessionAlreadyExistsError` | AI-1202 | `AILearningEvaluationException` | |
| `AIEvaluationSessionClosedError` | AI-1203 | `AILearningEvaluationException` | |
| `AIEvaluationRequestNotFoundError` | AI-1204 | `AILearningEvaluationException` | |
| `AIEvaluationValidationError` | AI-1205 | `AILearningEvaluationException` | |
| `AIBenchmarkException` | AI-1210 | `AILearningEvaluationException` | |
| `AIBenchmarkNotFoundError` | AI-1211 | `AIBenchmarkException` | |
| `AIBenchmarkSuiteNotFoundError` | AI-1212 | `AIBenchmarkException` | |
| `AIBenchmarkAlreadyRunningError` | AI-1213 | `AIBenchmarkException` | |
| `AIBenchmarkScenarioError` | AI-1214 | `AIBenchmarkException` | |
| `AILearningException` | AI-1220 | `AILearningEvaluationException` | |
| `AILearningRecordNotFoundError` | AI-1221 | `AILearningException` | |
| `AIFeedbackException` | AI-1222 | `AILearningException` | |
| `AIImprovementException` | AI-1223 | `AILearningException` | |
| `AIQualityException` | AI-1230 | `AILearningEvaluationException` | |
| `AIQualityRuleViolationError` | AI-1231 | `AIQualityException` | |
| `AIQualityAssessmentError` | AI-1232 | `AIQualityException` | |
| `AIQualityValidationException` | AI-1233 | `AIQualityException` | |
| `AIMetricsException` | AI-1240 | `AILearningEvaluationException` | |
| `AIMetricsCalculationError` | AI-1241 | `AIMetricsException` | |
| `AILearningEvaluationPolicyException` | AI-1250 | `AILearningEvaluationException` | |
| `AILearningEvaluationPolicyViolationError` | AI-1251 | `AILearningEvaluationPolicyException` | |
| `AIValidationException` *(alias)* | AI-1233 | — | → `AIQualityValidationException` |

### 13.8 A8 Governance (AI-1300 – AI-1371)

| Class | Code | Base | Alias |
|---|---|---|---|
| `AIGovernanceException` | AI-1300 | `AIException` | |
| `AIPolicyException` | AI-1310 | `AIGovernanceException` | |
| `AIPolicyNotFoundError` | AI-1311 | `AIPolicyException` | |
| `AIPolicyAlreadyExistsError` | AI-1312 | `AIPolicyException` | |
| `AIGovernanceRuleViolationError` | AI-1313 | `AIPolicyException` | |
| `AIPolicyEvaluationError` | AI-1314 | `AIPolicyException` | |
| `AIPolicyConflictError` | AI-1315 | `AIPolicyException` | |
| `AIPermissionException` | AI-1320 | `AIGovernanceException` | |
| `AIPermissionDeniedError` | AI-1321 | `AIPermissionException` | |
| `AIRoleNotFoundError` | AI-1322 | `AIPermissionException` | |
| `AIRoleAlreadyExistsError` | AI-1323 | `AIPermissionException` | |
| `AICapabilityRestrictionError` | AI-1324 | `AIPermissionException` | |
| `AIAuditException` | AI-1330 | `AIGovernanceException` | |
| `AIAuditRecordNotFoundError` | AI-1331 | `AIAuditException` | |
| `AIAuditReportError` | AI-1332 | `AIAuditException` | |
| `AIExplainabilityException` | AI-1340 | `AIGovernanceException` | |
| `AIExplanationNotFoundError` | AI-1341 | `AIExplainabilityException` | |
| `AIDecisionTraceError` | AI-1342 | `AIExplainabilityException` | |
| `AIComplianceException` | AI-1350 | `AIGovernanceException` | |
| `AIComplianceRuleNotFoundError` | AI-1351 | `AIComplianceException` | |
| `AIComplianceViolationError` | AI-1352 | `AIComplianceException` | |
| `AIComplianceReportError` | AI-1353 | `AIComplianceException` | |
| `AIRiskGovernanceException` | AI-1360 | `AIGovernanceException` | |
| `AIRiskThresholdExceededError` | AI-1361 | `AIRiskGovernanceException` | |
| `AIRiskPolicyNotFoundError` | AI-1362 | `AIRiskGovernanceException` | |
| `AIEscalationRequiredError` | AI-1363 | `AIRiskGovernanceException` | |
| `AIGovernancePolicyException` | AI-1370 | `AIGovernanceException` | |
| `AIGovernancePolicyViolationError` | AI-1371 | `AIGovernancePolicyException` | |
| `AIPolicyViolationError` *(alias)* | AI-1313 | — | → `AIGovernanceRuleViolationError` |

### 13.9 A9 Capability (AI-1400 – AI-1450)

| Class | Code | Base |
|---|---|---|
| `AICapabilityException` | AI-1400 | `AIException` |
| `AICapabilityNotFoundError` | AI-1401 | `AICapabilityException` |
| `AICapabilityAlreadyExistsError` | AI-1402 | `AICapabilityException` |
| `AICapabilityDisabledError` | AI-1403 | `AICapabilityException` |
| `AICapabilityVersionError` | AI-1404 | `AICapabilityException` |
| `AICapabilityRegistrationError` | AI-1405 | `AICapabilityException` |
| `AICapabilityExecutionException` | AI-1410 | `AICapabilityException` |
| `AICapabilityTimeoutError` | AI-1411 | `AICapabilityExecutionException` |
| `AICapabilityRetryExhaustedError` | AI-1412 | `AICapabilityExecutionException` |
| `AICapabilityValidationError` | AI-1413 | `AICapabilityExecutionException` |
| `AICapabilityResultError` | AI-1414 | `AICapabilityExecutionException` |
| `AICapabilityAuthorizationException` | AI-1420 | `AICapabilityException` |
| `AICapabilityPermissionDeniedError` | AI-1421 | `AICapabilityAuthorizationException` |
| `AICapabilityPolicyViolationError` | AI-1422 | `AICapabilityAuthorizationException` |
| `AICapabilityQuotaExceededError` | AI-1423 | `AICapabilityAuthorizationException` |
| `AICapabilityRateLimitError` | AI-1424 | `AICapabilityAuthorizationException` |
| `AIConnectorException` | AI-1430 | `AICapabilityException` |
| `AIConnectorNotFoundError` | AI-1431 | `AIConnectorException` |
| `AIConnectorConnectionError` | AI-1432 | `AIConnectorException` |
| `AIConnectorTimeoutError` | AI-1433 | `AIConnectorException` |
| `AISkillException` | AI-1440 | `AICapabilityException` |
| `AISkillNotFoundError` | AI-1441 | `AISkillException` |
| `AISkillExecutionError` | AI-1442 | `AISkillException` |
| `AICapabilityAuditException` | AI-1450 | `AICapabilityException` |

### 13.10 A10 Orchestration (AI-1500 – AI-1563)

| Class | Code | Base | Alias |
|---|---|---|---|
| `AIOrchestrationException` | AI-1500 | `AIException` | |
| `AIObjectiveException` | AI-1510 | `AIOrchestrationException` | |
| `AIObjectiveNotFoundError` | AI-1511 | `AIObjectiveException` | |
| `AIObjectiveAlreadyExistsError` | AI-1512 | `AIObjectiveException` | |
| `AIObjectiveValidationError` | AI-1513 | `AIObjectiveException` | |
| `AIPlanningException` | AI-1520 | `AIOrchestrationException` | |
| `AIPlanNotFoundError` | AI-1521 | `AIPlanningException` | |
| `AIPlanGenerationError` | AI-1522 | `AIPlanningException` | |
| `AIPlanDependencyError` | AI-1523 | `AIPlanningException` | |
| `AIReplanningError` | AI-1524 | `AIPlanningException` | |
| `AIWorkflowException` | AI-1530 | `AIOrchestrationException` | |
| `AIWorkflowNotFoundError` | AI-1531 | `AIWorkflowException` | |
| `AIWorkflowAlreadyExistsError` | AI-1532 | `AIWorkflowException` | |
| `AIWorkflowStateError` | AI-1533 | `AIWorkflowException` | |
| `AIWorkflowExecutionError` | AI-1534 | `AIWorkflowException` | |
| `AIWorkflowTimeoutError` | AI-1535 | `AIWorkflowException` | |
| `AITaskSchedulerException` | AI-1540 | `AIOrchestrationException` | |
| `AISchedulerTaskNotFoundError` | AI-1541 | `AITaskSchedulerException` | |
| `AITaskQueueFullError` | AI-1542 | `AITaskSchedulerException` | |
| `AITaskDependencyError` | AI-1543 | `AITaskSchedulerException` | |
| `AISchedulerTaskExecutionError` | AI-1544 | `AITaskSchedulerException` | |
| `AIResourceException` | AI-1550 | `AIOrchestrationException` | |
| `AIAgentNotAvailableError` | AI-1551 | `AIResourceException` | |
| `AIResourceExhaustedError` | AI-1552 | `AIResourceException` | |
| `AIAllocationConflictError` | AI-1553 | `AIResourceException` | |
| `AIRecoveryException` | AI-1560 | `AIOrchestrationException` | |
| `AIRecoveryFailedError` | AI-1561 | `AIRecoveryException` | |
| `AIRollbackFailedError` | AI-1562 | `AIRecoveryException` | |
| `AIMaxRetriesExceededError` | AI-1563 | `AIRecoveryException` | |
| `AITaskNotFoundError` *(alias)* | AI-1541 | — | → `AISchedulerTaskNotFoundError` |
| `AITaskExecutionError` *(alias)* | AI-1544 | — | → `AISchedulerTaskExecutionError` |

### 13.11 Platform Bootstrap Errors

| Class | Base |
|---|---|
| `PlatformRegistryError` | `RuntimeError` |
| `CircularDependencyError` | `RuntimeError` |

---

## 14. Protocols

### 14.1 GatewayProtocol

```python
# iios.ai.platform.gateway_protocol
@runtime_checkable
class GatewayProtocol(Protocol):
    """Structural Protocol satisfied by every IIOS AI Platform M6 gateway."""

    # Required class-level metadata (verified at runtime in Python 3.12+)
    SYSTEM_ID  : str
    VERSION    : str
    MODULE_ID  : str
    MODULE_NAME: str

    # Required lifecycle methods
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def restart(self) -> None: ...

    # Required observability methods
    def health(self) -> Dict[str, Any]: ...
    def status(self) -> Dict[str, Any]: ...
    def snapshot(self) -> Any: ...
```

Runtime satisfaction confirmed for all 10 gateways (F4, `test_gateway_protocol_satisfied_by_compliant_mock`).

---

## 15. Summary Counts

| Category | Count |
|---|---|
| Modules (A1–A10 + Platform Bootstrap) | 11 |
| Gateway classes | 10 |
| Platform Bootstrap classes | 6 |
| **Total public gateway methods** | **251** |
| Platform Bootstrap public methods | ~35 |
| **Grand total public methods** | **~286** |
| Snapshot types (domain) | 12 |
| Platform data types | 5 |
| **Total frozen data types** | **17** |
| Canonical exception classes | 232 |
| Backward-compat exception aliases | 8 |
| Deprecated snapshot aliases (`taken_at`) | 4 |
| **Total exception classes incl. aliases** | **240** |
| Error code range | AI-000 – AI-1563 |
| Protocols (`GatewayProtocol`) | 1 |
| Tests (total) | 1,796 |
| Test pass rate | 100% |

---

*Public API Manifest frozen at Version 1.0.0 — 2026-08-01*  
*Breaking changes require a formal semantic version increment.*
