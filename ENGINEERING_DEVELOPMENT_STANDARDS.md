# ENGINEERING DEVELOPMENT STANDARDS
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-ENG-STD-001
**Version:** 1.0.0
**Status:** Active
**Classification:** Engineering Constitution
**Scope:** Every developer, AI agent, module, subsystem, repository, document,
service, workflow, ontology, database, model, and future extension of IIOS.
**Architecture Council:** Approved

---

> This document is the Engineering Constitution of the Investment Intelligence
> Operating System. It is not a coding guideline. It is not a style guide. It is
> engineering law — the mandatory standards that govern every aspect of how IIOS
> is designed, built, documented, reviewed, governed, and evolved. No exception
> is granted without Architecture Council review and a Constitutional Amendment
> Record. No component is certified without demonstrating compliance.

---

# TABLE OF CONTENTS

- Part I    — Engineering Philosophy (15 principles)
- Part II   — Engineering Standards Taxonomy (32 categories)
- Part III  — Engineering Rulebooks (21 rulebooks)
- Part IV   — Naming Framework (27 element types)
- Part V    — Documentation Standards (13 document types)
- Part VI   — Engineering Review Framework (11 review types)
- Part VII  — Quality Standards (13 dimensions)
- Part VIII — Governance Framework (11 domains)
- Part IX   — Engineering Constitution (130 rules)
- Part X    — Engineering Certification Checklist (14 domains)
- Supplement A — Engineering Standards Catalog
- Supplement B — Naming Reference
- Supplement C — Review Templates
- Supplement D — Certification Templates
- Supplement E — Architecture Decision Records
- Supplement F — Engineering Anti-Patterns
- Supplement G — Operational Runbook
- Supplement H — Developer Handbook
- Supplement I — Comprehensive Glossary

---

# PART I — ENGINEERING PHILOSOPHY

## 1.1 Engineering Excellence

Engineering excellence is the foundational commitment of IIOS: that every
component, every document, every decision, and every change is produced to the
highest standard achievable, not merely the minimum standard acceptable.

Excellence is not perfectionism. Perfectionism delays delivery in pursuit of
an unattainable ideal. Excellence is disciplined craft: understanding what
correct, maintainable, and scalable looks like, and reliably producing it.

Excellence in IIOS engineering means:
- Every module is designed before it is built.
- Every interface is specified before it is implemented.
- Every assumption is documented before it is embedded in code.
- Every defect is treated as a learning opportunity, not an embarrassment.
- Every simplification is an active decision, not an omission.

Excellence is not an individual achievement — it is a team property enforced
by standards, review processes, and governance. Individual excellence without
systematic enforcement produces inconsistency. Systematic enforcement without
individual commitment produces compliance without quality. IIOS requires both.

---

## 1.2 Long-Term Maintainability

A system built for today's requirements that cannot be extended for tomorrow's
requirements is not a successful system — it is a scheduled replacement. IIOS
is engineered for long-term maintainability as a first-class requirement, not
an afterthought.

Long-term maintainability in IIOS means:

**Readability over cleverness:** Code that any competent engineer can understand
in 15 minutes is preferred over code that only the original author can maintain.
Clever code is a form of technical debt.

**Explicit over implicit:** Every assumption, every dependency, every constraint
is stated explicitly. An implicit assumption that is never documented becomes an
invisible coupling that breaks at the worst possible time.

**Self-documenting architecture:** The architecture should be legible from the
code and documents without requiring the original architect to explain it. The
ARCHITECTURE.md, this document, and the layer specifications constitute the
architectural documentation that makes self-documentation possible.

**Low coupling, high cohesion:** Modules do one thing and do it completely.
They depend on the minimum set of other modules to do that thing. The 17-layer
hierarchy enforces this at the macro level; individual module design enforces
it at the micro level.

**Sustainable evolution:** Every change to the system preserves the ability
to make the next change. A change that solves today's problem while creating
five future coupling problems is not a good change.

---

## 1.3 Architecture-First Development

Architecture-first development means that the design of a component precedes
its implementation. No engineering work begins on a new module, subsystem, or
significant extension without a written architectural specification.

The architectural specification must answer, before any line of code is written:
- What is the purpose of this component?
- What are its inputs and outputs?
- What are its dependencies?
- What layer does it belong to?
- What is its public interface?
- How does it fail, and how does it recover?
- How does it interact with the 17-layer hierarchy?

Architecture-first development does not mean exhaustive upfront design for
every small implementation detail. It means that the structural decisions —
layer placement, interface contracts, dependency graph, failure model — are
made before implementation begins, not discovered during implementation.

**The architectural hierarchy in IIOS:**
Every new component is assigned to exactly one of the 17 layers before work
begins. This assignment determines its dependency constraints (it may only
depend on components in lower-numbered layers), its governance (layer assignment
requires Architecture Council acknowledgment for new engines), and its testing
requirements.

---

## 1.4 Domain-Driven Engineering

IIOS is a financial domain system. Every engineering decision is informed by
the financial domain it serves. Domain-driven engineering means that the
vocabulary, structure, and concepts of the engineering are derived from the
domain, not imposed on it from a generic software engineering template.

The IIOS domain vocabulary — market regime, trading strategy, signal, position,
risk limit, drawdown, Sharpe ratio, win rate, expiry, liquidity — is the
vocabulary of the engineering. Module names reflect domain concepts. Database
tables reflect domain entities. Events reflect domain occurrences. Decisions
reflect domain logic.

Domain-driven engineering in IIOS requires:
- All engineers understand the financial domain concepts they are engineering.
- Domain vocabulary is used consistently across all layers.
- When engineering terminology conflicts with domain terminology, domain
  terminology prevails.
- All domain entities are formally defined in the market ontology before they
  are used in any module.
- The domain model is maintained in the Knowledge Base and is the authoritative
  source of domain semantics.

---

## 1.5 Knowledge-First Engineering

Knowledge-first engineering means that the system's domain knowledge is formally
structured, version-controlled, and explicitly referenced before it influences
any decision.

In IIOS, knowledge-first engineering manifests as:
- The market ontology defines all domain entities before they are implemented.
- Trading strategy knowledge is formalized in the strategy specification before
  it is coded in the strategy generator.
- Market regime definitions are formalized in the MetaLearning knowledge base
  before they influence the regime-strategy mapping.
- All learned knowledge (win rates, strategy performance, regime correlations)
  is persisted explicitly, not embedded in model weights that cannot be audited.

Knowledge-first engineering enables:
- Auditability: every decision can be traced to the knowledge that produced it.
- Explainability: the system can explain why it made a decision in terms a
  domain expert can verify.
- Transferability: knowledge can be reviewed, corrected, and extended without
  modifying code.

---

## 1.6 Consistency

Consistency is the property that similar things are done the same way everywhere
in the system. Consistency is not uniformity — different problems require
different solutions. Consistency means that the same problem is always solved
the same way.

IIOS consistency requirements:
- Naming: the same type of entity has the same naming pattern everywhere.
- Error handling: errors are handled at the same architectural level everywhere.
- Logging: log events have the same structure everywhere.
- Configuration: configuration is accessed the same way everywhere.
- Testing: tests are structured the same way everywhere.

Consistency is enforced through:
- This Engineering Constitution (the rules).
- Code review (the enforcement).
- Certification (the gate).
- Refactoring when inconsistency is discovered (the correction).

Inconsistency is not an aesthetic problem — it is a cognitive load problem.
An engineer reading code that does the same thing in 12 different ways must
understand all 12 ways. An engineer reading code that does the same thing
consistently must understand one way. Consistency multiplies productivity.

---

## 1.7 Predictability

Predictability is the property that the system behaves in a way that can be
anticipated from its specification. A predictable system is one where:
- The same input always produces the same output (determinism).
- Edge cases are handled as documented, not silently.
- Failure modes are known and documented, not discovered in production.
- Performance characteristics are measurable and stable.

Predictability is the foundation of trust. IIOS manages financial positions.
The engineers, operators, and Architecture Council must be able to predict
with high confidence what the system will do in any given market condition.
Surprises in a financial system are financial risks.

Predictability is achieved through:
- Deterministic algorithms where determinism is possible.
- Documented non-determinism (e.g., yfinance data delivery timing) where
  determinism is not possible.
- Explicit failure modes in every module specification.
- Performance benchmarks with documented degradation conditions.

---

## 1.8 Traceability

Traceability is the ability to follow any decision, any output, or any behavior
back to its origin. In IIOS, traceability operates at multiple levels:

**Decision traceability:** Every trade decision can be traced through the 17-layer
pipeline to the specific inputs, strategies, agent scores, and thresholds that
produced it.

**Code traceability:** Every line of production code can be traced to the commit,
the PR, the reviewer approvals, and the release version that introduced it.

**Knowledge traceability:** Every fact in the knowledge base can be traced to
its source (historical data, learned experience, or explicit specification) and
its validation history.

**Configuration traceability:** Every configuration value can be traced to the
version of the configuration file that introduced it, the approval that authorized
it, and the environments in which it is active.

Traceability requires structured logging, structured governance records, and
the discipline to reference the relevant context in every commit, every PR,
and every decision record.

---

## 1.9 Deterministic Engineering

Deterministic engineering means that the system produces the same result for the
same input at any time, on any compliant host. Non-determinism is a defect unless
it is explicitly specified and bounded.

Sources of non-determinism in IIOS and how they are managed:

**Time:** The injectable clock utility eliminates time-based non-determinism in
testing. All time-sensitive logic uses the injectable clock, not the system clock
directly.

**Random number generation:** Seeded PRNGs are used wherever reproducibility is
required (Monte Carlo simulations in test mode). The seed is recorded.

**External data:** External market data is non-deterministic by nature. The system
is designed to be correct for any valid input, not dependent on a specific data
value.

**AI agent outputs:** LLM-based components are the primary source of structured
non-determinism. This is bounded by: temperature settings, prompt engineering,
output validation, and confidence thresholds.

---

## 1.10 Modularity

Modularity is the engineering property that the system is composed of independent,
well-defined components that can be understood, tested, replaced, and evolved
independently of each other.

IIOS modularity is enforced at three levels:

**Layer modularity:** The 17-layer hierarchy divides the system into layers with
well-defined dependencies (each layer depends only on lower layers). A component
in Layer 10 has no knowledge of components in Layers 11–17.

**Module modularity:** Within each layer, modules (Python files and classes) have
single, well-defined responsibilities. A module that does two unrelated things
is two modules that have been incorrectly merged.

**Interface modularity:** All module interactions are through defined interfaces,
not through direct access to internal state. The interfaces listed in the
copilot-instructions.md as Critical Interfaces are the gold standard.

---

## 1.11 Scalability

Scalability is the property that the system can handle increasing load, increasing
complexity, and increasing data volume without requiring architectural redesign.

IIOS scalability design:

**Horizontal scalability awareness:** IIOS currently runs as a single instance.
Every new module is designed to be single-instance-correct and horizontally
scalable (meaning: if a second instance were added, the module would function
correctly in a distributed context without code changes, only configuration changes).

**Data scalability:** All data stores are designed with growth in mind. SQLite
databases use WAL mode and are designed to be migrated to PostgreSQL without
application-layer changes if scale requires.

**Knowledge scalability:** The knowledge base is designed to grow with learned
experience. It does not have a fixed schema that would require architectural
changes to extend.

---

## 1.12 Evolution Without Breaking Architecture

Evolution without breaking architecture is the commitment that the system grows
without destroying what already works. This is the hardest engineering discipline:
every pressure for a quick fix, every time-constrained feature request, every
expedient shortcut pushes against it.

The rules are:
- New capabilities are added by extending the architecture, not by modifying
  existing stable components.
- Existing interfaces are never changed without Architecture Council review.
- Existing behaviors are never changed without regression tests verifying that
  existing callers are unaffected.
- The 17-layer hierarchy is the architectural skeleton. Additions must fit within
  it, not around it.

**The change table from copilot-instructions.md is law:**

| Type | Allowed | Rule |
|------|---------|------|
| Bug fix | Yes | Preserve interface |
| Performance improvement | Yes | Same interface, faster internals |
| New feature (additive) | Yes | Add new methods/classes, do not remove old |
| Refactor for clarity | Conditional | Only to remove real coupling problems |
| Rename / move | No | Never |
| Rewrite working module | No | Never without explicit instruction |
| Add new file | Yes | Preferred over modifying wiring |

---

## 1.13 Investment-Grade Software Engineering

IIOS is an investment-grade software system. This means that the consequences
of defects are measured in financial terms, not just in user experience terms.

Investment-grade engineering requirements:
- Zero tolerance for calculation defects in risk, sizing, and P&L computations.
- All financial arithmetic is performed in high-precision decimal, not float.
- All risk limits are enforced in code, not only in configuration.
- Every trade decision is logged with sufficient detail to reconstruct the full
  decision rationale.
- No trading action is taken without verification that the required preconditions
  are met.
- The kill switch is the highest-priority safety control and is treated as
  safety-critical code: it requires maximum test coverage (MC/DC) and any change
  requires Architecture Council explicit approval.

---

## 1.14 Engineering Ethics

Engineering ethics in IIOS means that engineers are responsible for the real-world
consequences of the systems they build.

**Responsibility for financial consequences:** IIOS systems make decisions that
affect real financial positions. Engineers who build these systems are responsible
for the correctness of those decisions. "The algorithm decided" is not a defense.

**Responsibility for transparency:** All significant engineering decisions are
documented. The Architecture Council, operators, and future engineers can
understand why the system was built as it was.

**Responsibility for honesty:** When a defect is found, it is reported immediately.
When a simplification that compromises correctness is made, it is documented.
When a risk threshold is changed, the rationale is recorded.

**Responsibility for sustainability:** Engineers do not create technical debt
without a documented plan to resolve it. Engineers do not make changes that
only the original engineer can maintain. Engineers produce work that future
engineers can build on.

---

## 1.15 Documentation-First Engineering

Documentation-first engineering means that every significant component, decision,
and change is documented as part of the engineering process, not as an afterthought.

Documentation is not bureaucracy. Documentation is the mechanism through which:
- Engineers communicate architectural intent to future engineers.
- The Architecture Council reviews changes before approving them.
- Operators understand how to deploy, monitor, and recover the system.
- The organization accumulates engineering knowledge that survives personnel changes.

Documentation-first in IIOS means:
- Every new module has a purpose statement, interface specification, and failure
  mode documentation before it is merged.
- Every architectural decision has an Engineering Decision Record.
- Every significant bug has a post-mortem.
- Every release has release notes.
- This document — the Engineering Constitution — is the primary reference for
  all engineering decisions.

---

*End of Part I*

---

# PART II — ENGINEERING STANDARDS TAXONOMY

## 2.1 Taxonomy Overview

The Engineering Standards Taxonomy defines 32 categories of engineering standards
that apply to IIOS. Every category has a defined purpose, scope, and relationship
to other categories.

---

## 2.2 Category 1 — Architecture Standards

**Purpose:** Define how the overall system structure, layer organization, component
boundaries, and dependency rules are established and maintained.

**Scope:** All 17 layers, all inter-layer interfaces, all major components.

**Key standards:**
- The 17-layer hierarchy is the authoritative structure. Every component belongs
  to exactly one layer.
- Components may depend only on components in lower-numbered layers.
- No circular dependencies at any level: module, package, or layer.
- Every new engine or major subsystem requires an Architecture Specification
  document approved by the Architecture Council before implementation.
- The Critical Interfaces listed in copilot-instructions.md may never be changed
  without a MAJOR version increment and Architecture Council unanimous approval.
- Layer latency thresholds (WARN and CRIT) are architectural constants.
  Changing them requires Architecture Council approval.

**Governance:** Architecture Council owns and enforces architecture standards.

---

## 2.3 Category 2 — Repository Standards

**Purpose:** Define how the IIOS source code repository is organized, branched,
committed, and maintained.

**Scope:** All source code, configuration files, documentation, and infrastructure
files in the repository.

**Key standards:**
- The main branch is always deployable. No broken code is merged to main.
- All changes to main require at least two PR reviewer approvals.
- Commit messages follow the format: TYPE(scope): brief description
  where TYPE is one of: feat, fix, perf, docs, test, chore, refactor.
- PR descriptions include: what changed, why it changed, what testing was done,
  and impact on other components.
- Branch naming: eature/DESCRIPTION, ix/DESCRIPTION, hotfix/DESCRIPTION,
  elease/VERSION.
- No binary files (images, executables, .pyc files) are committed.
- No credentials, tokens, or secrets are committed. Ever.
- The .gitignore covers: .venv/, __pycache__/, .env, *.pyc, data/*.db.

---

## 2.4 Category 3 — Folder Standards

**Purpose:** Define the canonical directory structure of the IIOS repository.

**Scope:** All directories and their permitted contents.

**Key standards:**
- Every IIOS layer has exactly one top-level folder named after the layer concept.
- Layer folder names are in snake_case.
- No layer folder contains sub-layers or cross-layer code.
- Utility functions shared across layers are in utils/ at the top level.
- Configuration is in config.py at the top level (single file, not a directory).
- Data persistence is in data/ and is never part of the container image.
- Tests mirror the source structure: tests/layer_name/test_module.py.
- Scripts (one-time utilities, setup helpers) are in scripts/.
- Documentation files are in the repository root (not in a docs/ subdirectory)
  unless the document count justifies a docs/ directory.

---

## 2.5 Category 4 — Naming Standards

**Purpose:** Define how all named artifacts are named, ensuring consistency and
predictability across the entire codebase.

**Scope:** Files, folders, modules, classes, functions, variables, databases,
tables, events, and all other named elements.

**Key standards (full detail in Part IV):**
- Python files: snake_case.py
- Classes: PascalCase (StrategyGenerator, not strategy_generator)
- Functions and methods: snake_case
- Constants: UPPER_SNAKE_CASE
- Private members: _leading_underscore
- Database tables: snake_case (trade_records, not TradeRecords)
- Events: SCREAMING_SNAKE_CASE (KILL_SWITCH_ACTIVATED)
- Configuration keys: UPPER_SNAKE_CASE
- Layer folder names match the layer concept in snake_case

---

## 2.6 Category 5 — Documentation Standards

**Purpose:** Define the required documentation for every type of artifact,
the format of that documentation, and the review and maintenance process.

**Scope:** All engineering documents, code comments, specification documents,
decision records, runbooks, and guides.

**Key standards (full detail in Part V):**
- Every module has a module-level docstring stating its purpose and layer.
- Every public class has a class-level docstring.
- Every public method has a method docstring with parameters and return type.
- Every new component has an Engineering Specification before implementation.
- Every significant architectural decision has an Engineering Decision Record.
- Documentation is reviewed on the same cadence as code.
- Outdated documentation is a defect. Every engineer is empowered to update it.

---

## 2.7 Category 6 — Ontology Standards

**Purpose:** Define how the IIOS market domain ontology is structured, extended,
and maintained.

**Scope:** All domain entities, their properties, relationships, and semantic
definitions.

**Key standards:**
- All domain entities are defined in the market ontology before being used
  in any module.
- Ontology definitions are authoritative — if code and ontology conflict, the
  ontology is correct.
- Every ontology entity has: a unique identifier, a human-readable name, a
  formal definition, a set of properties, a set of relationships, and an
  owning team.
- Ontology extensions require Architecture Council review.
- Deprecated ontology entities are marked deprecated, not deleted.
  Deletion occurs only after all references have been removed.
- The ontology is version-controlled alongside the source code.

---

## 2.8 Category 7 — Knowledge Standards

**Purpose:** Define how IIOS domain knowledge (trading rules, market patterns,
regime behaviors, strategy parameters) is captured, validated, and maintained.

**Scope:** All knowledge stored in the knowledge base, strategy specifications,
and learning system outputs.

**Key standards:**
- All knowledge has a source (empirical observation, expert specification, or
  learned from market data) and a confidence score.
- Learned knowledge is distinguished from specified knowledge.
- Knowledge is version-controlled; previous knowledge states can be recovered.
- Contradictory knowledge is resolved explicitly, not silently overwritten.
- Knowledge accessed by trading decisions is immutable during a trading cycle.
- All knowledge items are tested for consistency with the ontology.

---

## 2.9 Category 8 — Entity Standards

**Purpose:** Define standards for all domain entities (instruments, strategies,
positions, orders, portfolios, signals, regimes).

**Scope:** All domain entity definitions, representations, and lifecycle management.

**Key standards:**
- Every entity has a unique, stable identifier.
- Entity identifiers are never reused.
- Entity state transitions are defined and validated.
- Entities are not deleted; they are archived or deprecated.
- Entity relationships are managed through the relationship framework.
- Entity validation is performed at system boundaries (data entry, API ingress).
- Entities are immutable once finalized (e.g., a closed trade record is immutable).

---

## 2.10 Category 9 — Relationship Standards

**Purpose:** Define how relationships between domain entities are modeled,
stored, and traversed.

**Scope:** All inter-entity relationships in the knowledge base and data stores.

**Key standards:**
- All relationships are typed (has-a, is-a, depends-on, causes, correlates-with).
- Relationships have cardinality constraints.
- Relationship validity is verified when both endpoints exist.
- Orphaned relationships (references to non-existent entities) are detected
  and reported.
- Bidirectional relationships are stored with their canonical direction and
  an inverse reference.

---

## 2.11 Category 10 — Event Standards

**Purpose:** Define how events are named, structured, published, and consumed
throughout the IIOS system via the Event Bus.

**Scope:** All system events across all 17 layers.

**Key standards:**
- Event names are in SCREAMING_SNAKE_CASE: KILL_SWITCH_ACTIVATED.
- Every event has: event_type, source_layer, timestamp, correlation_id, payload.
- Event payloads are typed and documented.
- Events are immutable once published.
- Events are ordered within a source.
- No module subscribes to events from higher-numbered layers.
- Event delivery failure does not block the publisher.
- Events are persisted to the telemetry database for replay and audit.

---

## 2.12 Category 11 — Observation Standards

**Purpose:** Define how observations (market data, computed metrics, AI outputs)
are captured, recorded, and referenced.

**Scope:** All data observations from any source that influences a decision.

**Key standards:**
- Every observation has a timestamp, source, and provenance.
- Observations from external sources record the raw value and any transformation.
- Observations are immutable once recorded.
- Conflicting observations are recorded, not silently resolved.
- Observation quality (confidence, freshness, source reliability) is tracked.

---

## 2.13 Category 12 — Decision Standards

**Purpose:** Define how trading decisions are produced, recorded, explained,
and audited.

**Scope:** Decision Engine output, all agent scoring, all threshold evaluations.

**Key standards:**
- Every decision has a complete audit record: inputs, agent scores, threshold
  values, and outcome.
- Decision records are immutable.
- The decision threshold (currently 6.5) is a configuration constant, not
  embedded in code.
- All 8 defined decision outcomes are tested in the test suite.
- No decision produces a live trade without the kill switch being verified inactive.
- Decision quality metrics are tracked over time to detect degradation.

---

## 2.14 Category 13 — Reasoning Standards

**Purpose:** Define how AI-based reasoning components (debate agents, knowledge
reasoning engine) produce and validate their outputs.

**Scope:** All 5 debate agents, all reasoning components.

**Key standards:**
- Every reasoning output is associated with a confidence score.
- Reasoning that cannot produce a confident output explicitly abstains (does
  not produce a low-confidence guess that is indistinguishable from a confident output).
- Reasoning outputs are validated for internal consistency before being passed
  to downstream components.
- Prompt engineering is version-controlled and reviewed on the same cadence
  as code.
- Reasoning failures are graceful (lower confidence, explicit uncertainty) not
  hard crashes.

---

## 2.15 Category 14 — AI Agent Standards

**Purpose:** Define standards for all AI agent components in IIOS.

**Scope:** All 5 debate agents and any future AI agent components.

**Key standards:**
- Every agent has a documented role and a documented bias (the perspective it
  is designed to bring to the debate).
- Every agent has a defined input schema and a defined output schema.
- Agent outputs are typed and validated.
- Agent performance (correlation with eventual trade outcome) is tracked.
- Agents may not access resources outside their defined input set.
- Agent initialization failure is handled gracefully (debate proceeds with
  available agents).

---

## 2.16 Category 15 — Model Standards

**Purpose:** Define standards for all statistical and machine learning models.

**Scope:** k-NN regime predictor, Monte Carlo simulator, any future ML models.

**Key standards:**
- Every model has a documented training dataset with version, date, and size.
- Every model has documented accuracy metrics on the validation set.
- Model versions are tracked.
- Model artifacts are stored in version-controlled storage, not embedded in code.
- Model predictions include confidence estimates.
- Model degradation (performance dropping below threshold) is detected and alerts.
- Models trained on market data have documented regime coverage.

---

## 2.17 Category 16 — Database Standards

**Purpose:** Define standards for all IIOS databases and data access patterns.

**Scope:** All SQLite databases in data/, all data access code.

**Key standards:**
- All databases use WAL mode.
- All schema changes are migrations. No ad hoc schema changes.
- Migrations are forward-only, ordered, and idempotent.
- Migrations are tested against a copy of the current schema before application.
- All queries use parameterized SQL. String-formatted SQL is prohibited.
- Database access is through defined repository objects. Direct SQL in business
  logic is prohibited.
- All tables have a primary key.
- All foreign keys are defined and enforced where the database supports it.
- Database file names follow the convention: {domain}_db.sqlite.

---

## 2.18 Category 17 — Schema Standards

**Purpose:** Define standards for all data schemas: database schemas, event
schemas, configuration schemas, and API schemas.

**Scope:** All data structures at system boundaries.

**Key standards:**
- All schemas are explicitly versioned.
- Schema versions are backward-compatible within a MINOR version.
- Breaking schema changes require a MAJOR version increment.
- All schemas are documented with field types, constraints, and semantics.
- Schema validation is performed at all system boundaries.
- Schema changes are reviewed by the Architecture Council.

---

## 2.19 Category 18 — API Standards

**Purpose:** Define standards for all internal interfaces that operate as
structured APIs between IIOS layers.

**Scope:** All public interfaces between modules and layers.

**Key standards:**
- All public methods are documented with input types, output types, and exceptions.
- Interface stability is guaranteed within a MINOR version.
- Breaking interface changes require explicit deprecation with a 2-release notice period.
- Return types are typed (using Python typing annotations).
- Error conditions are documented and handled at the interface, not propagated silently.
- The Critical Interfaces listed in copilot-instructions.md have the highest
  stability guarantee: changes require MAJOR version increment.

---

## 2.20 Category 19 — Configuration Standards

**Purpose:** Define standards for all configuration values, their organization,
validation, and documentation.

**Scope:** config.py and all environment variable configuration.

**Key standards:**
- All configuration is in config.py (source-controlled defaults) or environment
  variables (environment-specific overrides).
- No configuration is embedded in module code.
- Every configuration value has a documented purpose, allowed values, default,
  and environment scope.
- Configuration validation occurs at startup. The system refuses to start with
  invalid configuration.
- Sensitive configuration (secrets, tokens) is provided via environment variables,
  never in config.py.
- Configuration changes require the same review process as code changes.

---

## 2.21 Category 20 — Logging Standards

**Purpose:** Define standards for all logging across the IIOS system.

**Scope:** All log output from all 17 layers.

**Key standards:**
- All logs use structured format: timestamp, level, layer, module, message, context.
- Log levels: DEBUG (development), INFO (normal operation), WARNING (degraded
  but recoverable), ERROR (failure requiring attention), CRITICAL (system at risk).
- No sensitive data (tokens, API keys, position details if inappropriate) in logs.
- Log retention: production logs minimum 90 days.
- Every trade decision produces a log entry at INFO level.
- Kill switch activation produces a log entry at CRITICAL level.
- Log volume is controlled: DEBUG logs are disabled in production by default.

---

## 2.22 Category 21 — Testing Standards

**Purpose:** Define standards for all testing activities across IIOS.

**Scope:** All test types as defined in TESTING_ENGINEERING_FRAMEWORK.md.

**Key standards:**
- Test coverage thresholds: >= 95% line, >= 90% branch for production.
- All tests are deterministic. Flaky tests are defects.
- All tests are independent. No test depends on another test's execution.
- Safety-critical code (kill switch, risk limits) has 100% decision coverage.
- All 47 testing categories (from TESTING_ENGINEERING_FRAMEWORK.md) are applied
  as required by the component type.
- Tests are maintained alongside the code they test. A broken test is as
  significant as broken production code.

---

## 2.23 Category 22 — Deployment Standards

**Purpose:** Define standards for all deployment activities.

**Scope:** All deployments as defined in BUILD_DEPLOYMENT_ENGINEERING_FRAMEWORK.md.

**Key standards (reference IIOS-BLD-DEP-001 for full detail):**
- No production deployment during market hours.
- No deployment without verified rollback.
- Architecture Council authorization required for production.
- All deployments through the Deployment Manager (no manual steps).
- Health verification after every deployment.

---

## 2.24 Category 23 — Monitoring Standards

**Purpose:** Define standards for all monitoring, alerting, and observability.

**Scope:** All metrics, alerts, dashboards, and health probes.

**Key standards:**
- All 17 layers produce heartbeat signals.
- All CRITICAL alerts produce Telegram notifications within 5 seconds.
- Dashboard metrics are updated every cycle.
- Baselines are established for all key metrics.
- Deviations > 20% from 7-day baseline trigger alerts.
- All monitoring configuration is version-controlled.

---

## 2.25 Category 24 — Security Standards

**Purpose:** Define standards for all security-related aspects of IIOS engineering.

**Scope:** All code, configuration, data, and infrastructure.

**Key standards:**
- No secrets in source control.
- All external inputs are validated.
- All SQL uses parameterized queries.
- Dependency CVEs are resolved within defined SLAs.
- SSH access to production is key-based only.
- Access to production is restricted to Architecture Council.
- All audit logs are append-only.

---

## 2.26 Category 25 — Performance Standards

**Purpose:** Define measurable performance targets for all IIOS components.

**Scope:** All components with latency or throughput requirements.

**Key standards:**
- Full trading cycle: <= 172ms baseline; <= 200ms SLA.
- GlobalIntelligence: <= 17ms (cache hit); <= 12,000ms (cold, CRIT threshold).
- MarketIntelligence: <= 19ms baseline.
- No regression > 10% in any benchmark between versions.
- Performance tests are part of the certification suite.
- Performance baselines are documented and updated with each release.

---

## 2.27 Category 26 — Scalability Standards

**Purpose:** Define standards ensuring IIOS can scale as volume and complexity grow.

**Scope:** All components, data stores, and processing pipelines.

**Key standards:**
- Every module is designed to be single-instance-correct and horizontally
  scalable in configuration.
- No module embeds assumptions about being the only instance.
- Data stores are designed for growth: indexes on all frequently queried columns.
- Long-running operations are async or scheduled, not blocking.

---

## 2.28 Category 27 — Versioning Standards

**Purpose:** Define standards for semantic versioning across all IIOS artifacts.

**Scope:** Application version, schema versions, knowledge base versions, model
versions, document versions.

**Key standards:**
- Application versions follow SemVer 2.0.0 (MAJOR.MINOR.PATCH).
- Schema versions are independent of application versions.
- Every versioned artifact has a version history.
- Breaking changes always increment MAJOR.
- Additive changes increment MINOR.
- Defect fixes increment PATCH.

---

## 2.29 Category 28 — Dependency Standards

**Purpose:** Define standards for managing all IIOS dependencies.

**Scope:** All Python packages, Docker base images, and external service dependencies.

**Key standards:**
- All dependencies are pinned to exact versions in requirements.lock.
- No floating version specifiers in production.
- All dependencies are regularly reviewed for CVEs.
- Dependencies are minimized: no package is included if its function can be
  achieved with the standard library or an existing dependency.
- New dependencies require Architecture Council notification.

---

## 2.30 Category 29 — Review Standards

**Purpose:** Define standards for all review activities: code review, document
review, architecture review, and security review.

**Scope:** All review activities.

**Key standards (full detail in Part VI):**
- All changes require at least two reviewer approvals.
- Reviewers are assigned based on the affected component's ownership.
- Reviews are completed within 2 business days.
- All review comments are either resolved or explicitly accepted.
- Reviews are recorded in the governance audit trail.

---

## 2.31 Category 30 — Certification Standards

**Purpose:** Define the certification requirements for all IIOS components.

**Scope:** All components seeking lifecycle level advancement.

**Key standards:**
- Certification levels: EXPERIMENTAL, TESTABLE, INTEGRATION-READY, STAGING-READY,
  PRODUCTION-READY.
- PRODUCTION-READY certification requires TQS >= 0.90 and SCS >= 0.92.
- Certification is valid for 90 days.
- All HARD readiness checks must PASS.
- Architecture Council vote required for PRODUCTION-READY.

---

## 2.32 Category 31 — Operational Standards

**Purpose:** Define standards for operating the IIOS system in production.

**Scope:** All operational activities: monitoring, incident response, change management.

**Key standards:**
- All operational procedures are documented.
- Incidents are classified P0–P3 with defined response times.
- P0 incidents require Architecture Council notification within 5 minutes.
- All P0 and P1 incidents produce post-mortems within 48 hours.
- Operational runbooks are reviewed quarterly.

---

## 2.33 Category 32 — Future Evolution Standards

**Purpose:** Define standards ensuring that IIOS can evolve without accumulating
architectural debt.

**Scope:** All future engineering work on IIOS.

**Key standards:**
- New layer addition requires Architecture Council unanimous approval and a
  full impact assessment.
- No layer can be removed without a migration plan for all dependent components.
- Every new dependency must be justified.
- Evolution planning is a standing agenda item at quarterly Architecture Council
  reviews.
- Technical debt is tracked explicitly and assigned resolution timelines.

---

*End of Part II*

# PART III — ENGINEERING RULEBOOKS

## 3.1 Rulebook Framework

Each Engineering Rulebook defines the complete engineering standards for a
specific domain of IIOS. The rulebook is the authoritative reference for
engineers working in that domain. It defines what is mandatory, what is
optional, how correctness is validated, what certification requires, and how
the domain is governed.

---

## 3.2 Rulebook 1 — Repository

**Purpose:** Define the engineering standards for the IIOS source code repository.

**Scope:** All files, branches, commits, and PRs in the IIOS repository.

**Responsibilities:**
- Engineers: follow commit message format, branch naming, and PR description standards.
- PR reviewers: enforce code review standards.
- Platform Team: maintain branch protection rules and CI/CD configuration.
- Architecture Council: own repository governance policy.

**Mandatory Rules:**
- RB-001: Main branch is always deployable. Zero broken builds on main.
- RB-002: All changes require minimum 2 PR reviewer approvals.
- RB-003: Commit messages follow TYPE(scope): description format.
- RB-004: No binary artifacts in source control.
- RB-005: No secrets, tokens, or credentials in source control.
- RB-006: PR description includes: what, why, testing performed, and impacted components.
- RB-007: Branch names follow: feature/, fix/, hotfix/, release/ prefix.
- RB-008: All tests pass before PR merge is permitted.
- RB-009: Coverage thresholds maintained. No PR that reduces coverage below threshold.
- RB-010: .gitignore covers all generated, environment-specific, and secret files.

**Optional Rules:**
- RB-011: Squash merge for feature branches into main (preferred but not mandatory).
- RB-012: Link PR to associated issue or ticket.

**Validation Rules:**
- CI/CD pipeline enforces: lint, test pass, coverage threshold.
- Branch protection rules enforce: 2 approvals, CI pass.

**Certification Requirements:**
- Repository passes automated branch protection verification.
- Commit history shows no secrets (automated scan).

**Governance:** Architecture Council sets repository policy. Platform Team maintains tooling.

---

## 3.3 Rulebook 2 — Modules

**Purpose:** Define engineering standards for all Python modules in IIOS.

**Scope:** All .py files that constitute IIOS source code.

**Responsibilities:**
- Component owners: design and maintain modules in their ownership domain.
- PR reviewers: enforce module standards in reviews.

**Mandatory Rules:**
- MOD-001: Every module has a module-level docstring stating its purpose, layer, and owner.
- MOD-002: Every module belongs to exactly one IIOS layer.
- MOD-003: A module may only import from modules in the same layer or lower-numbered layers.
- MOD-004: No circular imports at any level.
- MOD-005: No module-level code with side effects (network calls, file operations)
  executed at import time.
- MOD-006: All constants are defined at module level, not within functions.
- MOD-007: Private functions and variables use _leading_underscore.
- MOD-008: Public interfaces are explicitly defined (via __all__ or consistent naming).
- MOD-009: No global mutable state in a module that is shared across threads,
  unless protected by a threading lock.
- MOD-010: Modules do not catch exceptions they cannot meaningfully handle.

**Optional Rules:**
- MOD-011: Module-level TYPE_CHECKING imports for type hint-only imports.
- MOD-012: __version__ attribute on modules that have stable interfaces.

**Validation Rules:**
- Linter (flake8): zero errors.
- Static analysis: no undefined names, no unused imports.
- Import cycle detection: automated pre-commit check.

**Certification Requirements:**
- Zero linter errors.
- No circular imports.
- Module docstring present and non-empty.

---

## 3.4 Rulebook 3 — Packages

**Purpose:** Define engineering standards for Python packages (directories with
__init__.py) in IIOS.

**Scope:** All IIOS layer directories that are Python packages.

**Mandatory Rules:**
- PKG-001: Every package has an __init__.py that explicitly defines its public API.
- PKG-002: Package public API exports only the types and functions needed by external callers.
- PKG-003: Package internal modules are not directly importable from outside the package
  (enforce via naming convention, not Python access control).
- PKG-004: Packages do not import from each other in a circular pattern.
- PKG-005: The package represents exactly one IIOS layer or utility domain.
- PKG-006: Package names match the layer concept in snake_case.

**Certification Requirements:**
- __init__.py defines __all__.
- No cross-package circular imports.

---

## 3.5 Rulebook 4 — Documents

**Purpose:** Define engineering standards for all technical documents in IIOS.

**Scope:** All .md files, specifications, decision records, and guides.

**Mandatory Rules:**
- DOC-001: Every engineering document has: Document Code, Version, Status,
  Scope, Author/Owner.
- DOC-002: Document code format: IIOS-{DOMAIN}-{TYPE}-{SEQ}
  (e.g., IIOS-TST-ENG-001, IIOS-BLD-DEP-001, IIOS-ENG-STD-001).
- DOC-003: All documents use semantic versioning (1.0.0 format).
- DOC-004: Every document has an Amendment History table.
- DOC-005: Documents reference other documents by document code, not by filename.
- DOC-006: No document is deleted — documents are deprecated and archived.
- DOC-007: Technical specifications must include diagrams where structure aids
  comprehension.
- DOC-008: All documents are reviewed by the Architecture Council before publication
  as Active status.
- DOC-009: Document size targets are defined per document type and must be met.
- DOC-010: Outdated documents are updated as part of the feature development process.
  A PR that changes a feature without updating its documentation is incomplete.

**Optional Rules:**
- DOC-011: Documents may include worked examples.
- DOC-012: Documents may include FAQ sections.

**Validation Rules:**
- Document Code present and correct format.
- Version field present.
- Amendment History table present.
- Architecture Council review recorded.

---

## 3.6 Rulebook 5 — Configuration

**Purpose:** Define engineering standards for all IIOS configuration.

**Scope:** config.py, environment variables, docker-compose environment sections,
and all configuration-related code.

**Mandatory Rules:**
- CFG-001: No magic numbers in source code. All constants are in config.py or
  named constants in the relevant module.
- CFG-002: All configuration values have documented type, allowed range, default,
  and environment scope.
- CFG-003: Configuration is validated at startup. Invalid configuration prevents startup.
- CFG-004: No environment-specific values are in config.py. config.py provides
  defaults; environment variables provide overrides.
- CFG-005: Sensitive values (API keys, tokens) are never in config.py or
  committed to source control.
- CFG-006: Configuration changes require the same PR and review process as code changes.
- CFG-007: Layer latency thresholds are configuration, not hard-coded constants.
  Any change requires Architecture Council approval.
- CFG-008: Feature flags are in configuration. The code does not hard-code
  feature flag values.
- CFG-009: No configuration value is accessed by a string key without a named constant.
  Use CONFIG_KEY = "KEY_STRING"; value = config[CONFIG_KEY], not value = config["KEY_STRING"].
- CFG-010: Configuration changes are reflected in the deployment manifest.

**Certification Requirements:**
- Configuration validation test passes at startup.
- All configuration values are documented.

---

## 3.7 Rulebook 6 — Logging

**Purpose:** Define engineering standards for all logging in IIOS.

**Scope:** All log output from all 17 layers and all supporting utilities.

**Mandatory Rules:**
- LOG-001: All logs use structured format with fields: timestamp (ISO 8601),
  level, layer, module, event, message, and optional context.
- LOG-002: Log levels are used correctly: DEBUG for development detail, INFO for
  normal operation events, WARNING for recoverable anomalies, ERROR for failures,
  CRITICAL for system-level risks.
- LOG-003: No sensitive data in logs: no API tokens, no Telegram bot tokens,
  no position data that would be inappropriate.
- LOG-004: Every trade decision produces a log entry at INFO with: signal source,
  strategy, agent scores, decision outcome.
- LOG-005: Every kill switch activation and deactivation produces a CRITICAL log entry.
- LOG-006: Every layer health transition (HEALTHY -> DEGRADED -> FAILED) produces
  a log entry at the appropriate level.
- LOG-007: Log volume is controlled in production. DEBUG logs are disabled unless
  a diagnostic flag is set.
- LOG-008: Log messages are written in a format that allows automated parsing.
  Free-text log messages that cannot be parsed are deprecated.
- LOG-009: All logger instances are created with the module name:
  logger = logging.getLogger(__name__).
- LOG-010: Logs include a correlation_id for events that are part of a trading cycle.

**Certification Requirements:**
- Log format test verifies correct structure.
- No sensitive data present in sample log output.

---

## 3.8 Rulebook 7 — Database

**Purpose:** Define engineering standards for all databases in IIOS.

**Scope:** All SQLite databases in data/, all schema definitions, all data access code.

**Mandatory Rules:**
- DB-001: All databases operate in WAL (Write-Ahead Logging) mode.
  WAL mode is verified at startup.
- DB-002: All schema changes are applied through the migration framework.
  Ad hoc schema changes to production databases are a governance violation.
- DB-003: All migrations are: ordered (sequential integer prefix), forward-only,
  and idempotent.
- DB-004: All SQL queries use parameterized statements. String-format SQL is prohibited.
- DB-005: All data access is through repository objects. Direct SQL in business
  logic modules is prohibited.
- DB-006: All tables have a primary key.
- DB-007: Database file names follow: {domain}_db.sqlite.
- DB-008: Migrations are tested against a copy of the production schema before
  being applied to production.
- DB-009: Database write operations that affect financial records use transactions.
  Partial writes are never acceptable.
- DB-010: Database read operations for trading decisions use explicit transactions
  to ensure consistency across a cycle.

**Optional Rules:**
- DB-011: Indexes are added for frequently queried columns as volumes grow.
- DB-012: VACUUM operations are scheduled during non-trading hours.

**Validation Rules:**
- Schema integrity check at startup.
- WAL mode verified at startup.
- Migration version verified against expected version.

---

## 3.9 Rulebook 8 — Knowledge Base

**Purpose:** Define engineering standards for the IIOS knowledge base.

**Scope:** All knowledge representations: strategy knowledge, regime knowledge,
learned performance metrics, domain facts.

**Mandatory Rules:**
- KB-001: All knowledge has a type: empirical, specified, or learned.
- KB-002: All knowledge has a provenance (source, date, methodology).
- KB-003: All knowledge has a confidence score.
- KB-004: Knowledge accessed by trading decisions is immutable for the duration
  of a trading cycle. Updates take effect at the next cycle boundary.
- KB-005: Contradictions are recorded, not silently resolved.
- KB-006: Knowledge is version-controlled. Previous knowledge states are recoverable.
- KB-007: Knowledge is validated against the ontology: all knowledge items reference
  only entities and relationships defined in the ontology.
- KB-008: Knowledge deprecation is formal: deprecated items are marked, not deleted.
  Deletion occurs only after all references are removed.
- KB-009: Knowledge quality is monitored: items with declining confidence scores
  are flagged for review.
- KB-010: All knowledge updates by the learning system are logged with the
  evidence that produced the update.

---

## 3.10 Rulebook 9 — Ontology

**Purpose:** Define engineering standards for the IIOS market domain ontology.

**Scope:** All domain entity definitions, property definitions, and relationship
definitions in the market ontology.

**Mandatory Rules:**
- ONT-001: Every ontology entity has: a unique stable ID, a human-readable name,
  a formal definition, a list of properties, and an owning team.
- ONT-002: All entities used in any IIOS module are defined in the ontology before
  the module is merged.
- ONT-003: Ontology changes require Architecture Council review.
- ONT-004: Deprecated entities are marked deprecated; they are never deleted
  while any reference exists.
- ONT-005: Ontology entity IDs are stable. An entity's ID never changes after
  it is first published.
- ONT-006: Property types are defined: string, integer, decimal, datetime, enum, or reference.
- ONT-007: All entity relationships have cardinality constraints.
- ONT-008: The ontology is tested: automated tests verify that all referenced
  entities in the codebase have ontology definitions.
- ONT-009: Ontology versions are tracked with the application version.
- ONT-010: The ontology is the authoritative source of domain vocabulary.
  When code uses a domain term differently from the ontology, the code is wrong.

---

## 3.11 Rulebook 10 — Reasoning

**Purpose:** Define engineering standards for all reasoning components in IIOS.

**Scope:** All AI-based reasoning: debate agents, knowledge reasoning, regime inference.

**Mandatory Rules:**
- RSN-001: Every reasoning component has a documented input specification and
  output specification before implementation.
- RSN-002: All reasoning outputs include a confidence score between 0.0 and 1.0.
- RSN-003: Reasoning components that cannot produce a confident output explicitly
  abstain with reason, rather than producing a low-confidence guess.
- RSN-004: Reasoning outputs are validated for structural correctness before
  being passed downstream.
- RSN-005: Reasoning failures are graceful: they reduce confidence or produce
  abstentions, not hard crashes.
- RSN-006: All prompts used in LLM-based reasoning are version-controlled.
- RSN-007: Reasoning components are tested with at least three scenario types:
  clear signal, ambiguous signal, and contradictory inputs.
- RSN-008: Reasoning component performance is tracked: correlation of confidence
  with eventual correctness is monitored.
- RSN-009: Reasoning components may not access resources outside their defined
  input set. No external network access from within a reasoning component.
- RSN-010: All reasoning components are included in the certification process.

---

## 3.12 Rulebook 11 — AI Agents

**Purpose:** Define engineering standards for the 5 debate agents and any future
AI agent components.

**Scope:** All agents in Layer 10 (DebateAndDecision) and future AI agent additions.

**Mandatory Rules:**
- AGT-001: Every agent has a documented role statement describing its perspective
  and the bias it is designed to bring.
- AGT-002: Agent scores are in a defined numeric range (current: 0–10, where
  >= 6.5 threshold applies).
- AGT-003: Agent outputs are typed and validated before entering the decision aggregation.
- AGT-004: Agent initialization failure does not abort the debate. The debate
  proceeds with the available agents; the absent agent's contribution is treated
  as an abstention.
- AGT-005: All 5 agents are tested individually before being tested in combination.
- AGT-006: Agent bias is intentional and documented. An agent should not be
  "objective" — its bias is its contribution to the debate diversity.
- AGT-007: Agent performance (historical correlation between agent score and
  eventual trade outcome) is tracked.
- AGT-008: New agents require Architecture Council approval.
- AGT-009: No agent has write access to any persistent data store during
  the debate cycle.
- AGT-010: The decision threshold (currently 6.5) is a configuration constant,
  never hardcoded in agent logic.

---

## 3.13 Rulebook 12 — Learning System

**Purpose:** Define engineering standards for the Learning System (Layer 13).

**Scope:** LearningEngine, StrategyPerformanceTracker, and all learning-related
components.

**Mandatory Rules:**
- LRN-001: All learning updates are logged with the evidence (trade outcomes)
  that produced the update.
- LRN-002: Learning never modifies a strategy specification directly. It records
  performance and adjusts weights; it does not rewrite strategy rules.
- LRN-003: Win rate computations are verified against the trade journal.
  A win rate computed from memory that diverges from the journal is a defect.
- LRN-004: Auto-disable thresholds (win rate floor, Sharpe floor) are configuration
  values, not hardcoded constants.
- LRN-005: Learning state (win rates, performance history) persists across restarts.
  A restart does not reset learning state.
- LRN-006: The EOD learning cycle handles the case of zero trades gracefully:
  no division by zero; no erroneous state update.
- LRN-007: Learning updates during the EOD cycle recover CSV-closed trades to
  handle post-restart zero-count situations.
- LRN-008: Strategy attribute lookup uses the 'strategy' field preferentially
  over 'strategy_name' (matching the current post-fix convention).
- LRN-009: All learning outputs are auditable: the evidence for any strategy
  weight can be reconstructed from the trade log.
- LRN-010: Learning system certification requires verification that win rate
  computations match trade journal records for the last 30 days.

---

## 3.14 Rulebook 13 — Decision Engine

**Purpose:** Define engineering standards for the Decision Engine (Layer 10).

**Scope:** DecisionEngine, 5 debate agents, score aggregation, decision records.

**Mandatory Rules:**
- DEC-001: The decision threshold (6.5) is a named configuration constant.
  Any change requires Architecture Council approval.
- DEC-002: All 8 defined decision outcomes are implemented, tested, and documented.
- DEC-003: Every decision produces a complete audit record: inputs, agent scores,
  threshold, outcome, timestamp, correlation_id.
- DEC-004: Decision records are immutable once written.
- DEC-005: No decision produces a trading action while the kill switch is active.
  This check is the first operation in any decision-to-action pipeline.
- DEC-006: Decision quality (historical correlation between approved decisions
  and profitable outcomes) is tracked and reported.
- DEC-007: The decision engine is tested with boundary-value inputs: score exactly
  at threshold (6.5), just below (6.4), and just above (6.6).
- DEC-008: Incomplete debate (some agents unable to produce scores) is handled
  with a documented partial-debate policy.
- DEC-009: Decision audit logs are retained for minimum 7 years.
- DEC-010: The decision engine is safety-critical and requires Level 5 certification.

---

## 3.15 Rulebook 14 — Risk Engine

**Purpose:** Define engineering standards for the Risk Engine subsystem
(Layers 6, 7, and 9).

**Scope:** CapitalRiskEngine (Layer 6), RiskControl (Layer 7), RiskGuardian (Layer 9).

**Mandatory Rules:**
- RSK-001: All risk thresholds are configuration values. No hardcoded risk limits.
- RSK-002: The kill switch thresholds (VIX >= 45.0, daily loss >= 2.0%) are the
  highest-priority configuration values. They may only be changed with Architecture
  Council unanimous approval.
- RSK-003: Risk checks are the last verification before any trading action.
  No trading action bypasses risk verification.
- RSK-004: Position sizing computations use decimal arithmetic, not floating point.
- RSK-005: All risk limit breaches are logged at CRITICAL level and trigger Telegram
  alerts within 5 seconds.
- RSK-006: The RiskGuardian (Layer 9) is protected — it may not be modified
  without explicit Architecture Council instruction.
- RSK-007: The kill switch state is triple-persisted: data/kill_switch.json,
  telemetry.db, and Telegram notification.
- RSK-008: Kill switch activation is idempotent: activating an already-active
  kill switch does not produce an error.
- RSK-009: All risk components require Level 5 certification (safety-critical).
- RSK-010: Risk engine changes require security review in addition to standard code review.

---

## 3.16 Rulebook 15 — Trading Engine

**Purpose:** Define engineering standards for the Trading Engine (ExecutionEngine,
Layer 11).

**Scope:** OrderManager, ZerodhaBroker, paper trading journal.

**Mandatory Rules:**
- TRD-001: PAPER_TRADING flag is verified true at startup. The system refuses
  to send live orders unless PAPER_TRADING is explicitly false AND Architecture
  Council has authorized live trading.
- TRD-002: Every order is assigned a unique, non-reusable order ID.
- TRD-003: Order submission is idempotent: duplicate order IDs are rejected.
- TRD-004: Every paper trade is immediately written to data/paper_trades.csv.
  In-memory only trades are not acceptable.
- TRD-005: Position limits are enforced in code, not only in configuration.
- TRD-006: Trade journal recovery: on startup, the order manager reads paper_trades.csv
  and reconstructs the in-memory position state.
- TRD-007: No trade is executed without a preceding risk check clearing the action.
- TRD-008: Index symbols (NIFTY, BANKNIFTY) are referenced by bare name.
  Equity symbols use the .NS suffix.
- TRD-009: Broker connectivity failure is handled gracefully: orders queue,
  an alert is sent, and the system does not crash.
- TRD-010: The trading engine requires Level 5 certification.

---

## 3.17 Rulebook 16 — Portfolio Engine

**Purpose:** Define engineering standards for portfolio management components
(CapitalRiskEngine, PortfolioAllocation, Layer 6 and Layer 7).

**Scope:** All portfolio allocation, position sizing, and budget management.

**Mandatory Rules:**
- PRT-001: Portfolio allocations sum to <= 100% of available capital.
  An allocation that exceeds available capital is a defect.
- PRT-002: All portfolio computations use high-precision decimal arithmetic.
- PRT-003: Portfolio state is consistent with the trade journal at all times.
- PRT-004: Maximum drawdown limits are enforced before any new position is opened.
- PRT-005: Strategy budget allocations are enforced per configuration.
- PRT-006: Portfolio allocation changes within a cycle are atomic.
- PRT-007: Portfolio state is persisted and survives restart.

---

## 3.18 Rulebook 17 — Market Engine

**Purpose:** Define engineering standards for market analysis components
(MarketIntelligence, Layer 2; MarketMonitor).

**Scope:** Regime detection, sector analysis, liquidity assessment, event monitoring.

**Mandatory Rules:**
- MKT-001: Regime classifications use only the defined regime vocabulary from the ontology.
- MKT-002: Regime transitions produce EVENT: REGIME_CHANGED with old and new regime values.
- MKT-003: Market data freshness is verified before regime computation.
  Stale data produces a DEGRADED regime classification, not a confident one.
- MKT-004: The continuous scan (30-second interval) is verified active in monitoring.
- MKT-005: Market holiday detection prevents erroneous regime computations on
  days when the market is closed.
- MKT-006: All 6 deep-scan slots are tested in the certification suite.

---

## 3.19 Rulebook 18 — Research Engine

**Purpose:** Define engineering standards for ResearchLab (Layer 15) and its
strategy promotion gate.

**Scope:** Strategy promotion evaluation, backtesting validation, research workflows.

**Mandatory Rules:**
- RES-001: Promotion gates are configuration constants: WinRate >= 50%, Sharpe > 0.8,
  MaxDD < 15%. Changes require Architecture Council approval.
- RES-002: Every evolved strategy that passes promotion gates is logged with
  the evaluation metrics at the time of promotion.
- RES-003: Strategies that fail promotion gates are logged with the reason for failure.
- RES-004: Research outputs (evolved strategy candidates) are staged, not directly
  deployed.
- RES-005: The ResearchLab is isolated from live trading. No research process
  writes to the live position or order state.
- RES-006: Research datasets are distinct from production datasets.

---

## 3.20 Rulebook 19 — Simulation Engine

**Purpose:** Define engineering standards for MarketSimulation (Layer 8).

**Scope:** Monte Carlo engine, 14-scenario simulation framework.

**Mandatory Rules:**
- SIM-001: All 14 defined scenarios are implemented and tested.
- SIM-002: Monte Carlo simulations use seeded PRNGs in test mode for reproducibility.
- SIM-003: The random seed is recorded in simulation output for reproducibility.
- SIM-004: Simulation output includes: scenario name, parameter values, confidence
  intervals, and timestamp.
- SIM-005: Simulation engine is isolated from live data during simulation runs.
- SIM-006: Scenario definitions are configuration, not hardcoded.

---

## 3.21 Rulebook 20 — Infrastructure

**Purpose:** Define engineering standards for IIOS infrastructure: Docker,
VPS, CI/CD, and build systems.

**Scope:** Dockerfile, docker-compose.yml, GitHub Actions workflows, VPS configuration.

**Mandatory Rules:**
- INF-001: All infrastructure configuration is version-controlled.
- INF-002: No manual infrastructure changes that are not reflected in version control.
- INF-003: All Docker images use digest-pinned base images in production.
- INF-004: All containers have health checks defined.
- INF-005: All containers have restart: unless-stopped policy.
- INF-006: SSH access to production VPS uses key-based authentication only.
- INF-007: GitHub Actions workflows are reviewed with the same rigor as application code.
- INF-008: Infrastructure changes are tested in staging before production.
- INF-009: The data volume (./data:/app/data) is never part of the container image.
- INF-010: All infrastructure components have documented owners.

---

## 3.22 Rulebook 21 — Developer Workflow

**Purpose:** Define the engineering standards for the day-to-day development
workflow of IIOS contributors.

**Scope:** All engineering activities: design, implement, test, review, document, deploy.

**Mandatory Rules:**
- DEV-001: Every feature or defect fix begins with reading the architecture
  documentation (ARCHITECTURE.md, copilot-instructions.md, this document).
- DEV-002: Every new component design answers the three architectural questions:
  (1) Does this improve correctness, performance, or architecture?
  (2) Does it preserve existing public interfaces?
  (3) Is it the smallest change that achieves the goal?
- DEV-003: No speculative changes. Every change has a documented purpose.
- DEV-004: Testing is part of the definition of done. A feature without tests
  is not done.
- DEV-005: Documentation is part of the definition of done. A feature without
  documentation updates is not done.
- DEV-006: Every PR addresses exactly one concern. A PR that fixes a bug AND
  adds a feature should be split into two PRs.
- DEV-007: The engineer who makes a change is responsible for verifying it in
  staging before requesting production deployment.
- DEV-008: Engineers are empowered to update documentation they find outdated.
  Updating documentation is credited work.
- DEV-009: Every engineer understands the financial consequences of their work.
  No engineer produces code that affects trading decisions without understanding
  those decisions.
- DEV-010: Deployments follow the process in BUILD_DEPLOYMENT_ENGINEERING_FRAMEWORK.md
  exactly. No shortcut deployments.

---

*End of Part III*

# PART IV — NAMING FRAMEWORK

## 4.1 Naming Philosophy

Names are the first interface between the code and the engineer reading it.
A good name communicates purpose without requiring the reader to examine the
implementation. A bad name forces the reader to understand the implementation
before the name becomes meaningful.

IIOS applies a strict naming framework that ensures: every named artifact
communicates its type, domain, and purpose; similar artifacts have similar names;
different artifact types are distinguishable at a glance.

---

## 4.2 Naming Principles

**Principle 1 — Reveal Intent:**
Names reveal what a thing is for, not how it works. get_regime_strategy_map()
reveals intent. load_rsm_data_v2() does not.

**Principle 2 — Use Domain Vocabulary:**
Names use the financial domain vocabulary of IIOS. MarketRegime, TradingSignal,
PositionSizer are correct. DataBucket, ProcessorThing, Handler5 are not.

**Principle 3 — Distinguish Types:**
Different naming conventions for different artifact types make types distinguishable
without requiring context. Classes are PascalCase; constants are UPPER_SNAKE_CASE;
functions are snake_case. A reader can identify the artifact type from the name.

**Principle 4 — Consistent Patterns:**
All artifacts of the same type follow the same naming pattern everywhere in
the codebase. There are no exceptions for "legacy" or "historical" reasons.

**Principle 5 — Pronounceable and Memorable:**
Names can be spoken aloud without ambiguity. Abbreviations are used only for
industry-standard acronyms (VIX, NIFTY, P&L, SMA, EMA, RSI).

---

## 4.3 File Naming Standards

| File Type | Convention | Examples |
|-----------|-----------|---------|
| Python module | snake_case.py | global_data_ai.py, order_manager.py |
| Test file | test_{module_name}.py | test_order_manager.py |
| Configuration | config.py (singleton) | config.py |
| Script | verb_description.py | check_token.py, fix_expiry.py |
| Documentation | UPPER_SNAKE_CASE.md | ARCHITECTURE.md, KILL_SWITCH.md |
| Engineering document | UPPER_SNAKE_CASE_FRAMEWORK.md | TESTING_ENGINEERING_FRAMEWORK.md |
| Docker file | Dockerfile (no extension) | Dockerfile |
| Compose file | docker-compose.yml | docker-compose.yml |
| Requirements | requirements.txt, requirements.lock | requirements.txt |

**Decision table — when to use which file naming:**
- Use snake_case.py for all source code modules.
- Use UPPER_SNAKE_CASE.md for architecture and engineering documents.
- Use VERB_NOUN.py for one-time scripts and utilities.
- Test files always mirror the module they test with 	est_ prefix.

---

## 4.4 Folder Naming Standards

| Folder Purpose | Convention | Examples |
|---------------|-----------|---------|
| IIOS layer | snake_case (layer concept) | global_intelligence/, risk_guardian/ |
| Test layer mirror | tests/{layer_name}/ | tests/global_intelligence/ |
| Data storage | data/ | data/ |
| Scripts | scripts/ | scripts/ |
| GitHub config | .github/ | .github/ |

**Decision rule:** Layer folder names must match the layer concept name from
the ARCHITECTURE.md layer list. Variations are not permitted.

---

## 4.5 Module Naming Standards

| Module Type | Convention | Examples |
|------------|-----------|---------|
| Main engine class | {concept}_ai.py | global_data_ai.py, backtesting_ai.py |
| Manager class | {noun}_manager.py | order_manager.py, feed_manager.py |
| Monitor | {noun}_monitor.py | market_monitor.py, trade_monitor.py |
| Tracker | {noun}_tracker.py | strategy_performance_tracker.py |
| Engine | {noun}_engine.py | decision_engine.py |
| Controller | {noun}_controller.py | meta_strategy_controller.py |
| Generator | {noun}_generator_ai.py | strategy_generator_ai.py |

---

## 4.6 Package Naming Standards

| Package Type | Convention | Example |
|-------------|-----------|---------|
| IIOS layer | {layer_concept}/ | global_intelligence/, learning_system/ |
| Utility | utils/ | utils/ |
| Test package | tests/ | tests/ |

---

## 4.7 Class Naming Standards

| Class Type | Convention | Examples |
|-----------|-----------|---------|
| Main data class | {Noun}AI | GlobalDataAI |
| Manager | {Noun}Manager | OrderManager, FeedManager |
| Monitor | {Noun}Monitor | TradeMonitor, StrategyHealthMonitor |
| Controller | {Noun}Controller | MetaStrategyController |
| Engine | {Noun}Engine | DecisionEngine, LearningEngine |
| Analyzer | {Noun}Analyzer | DrawdownAnalyzer |
| Tracker | {Noun}Tracker | StrategyPerformanceTracker |
| Data container | {Noun}Snapshot, {Noun}State, {Noun}Record | GlobalSnapshot |
| Exception | {Noun}Error, {Noun}Exception | KillSwitchError, FeedException |
| Abstract base | Base{Noun} | BaseFeed |

**Prohibited class name patterns:**
- Do not use: Manager2, ManagerNew, ManagerV2 (increment version in module, not class).
- Do not use: Helper, Utils, Misc, Stuff as class names.
- Do not use single-letter or two-letter class names outside iterator variables.

---

## 4.8 Interface Naming Standards

| Interface Type | Convention | Examples |
|---------------|-----------|---------|
| Abstract base class | Base{Concept} | BaseFeed, BaseStrategy |
| Protocol | {Noun}Protocol | FeedProtocol |
| Mixin | {Capability}Mixin | LoggableMixin |

---

## 4.9 Service Naming Standards

| Service Type | Convention | Examples |
|-------------|-----------|---------|
| Docker service | {noun}-{role} | ai-trading-brain, trading-dashboard |
| Background service | {noun}_service | monitoring_service |

---

## 4.10 Repository Naming Standards

| Repository Type | Convention | Examples |
|----------------|-----------|---------|
| Data repository | {noun}Repository | TradeRepository, StrategyRepository |

---

## 4.11 Pipeline Naming Standards

| Pipeline Type | Convention | Examples |
|-------------|-----------|---------|
| Processing pipeline | {concept}_pipeline | validation_pipeline, learning_pipeline |

---

## 4.12 AI Agent Naming Standards

| Agent Type | Convention | Examples |
|-----------|-----------|---------|
| Debate agent | {Perspective}Agent | BullishAgent, RiskAdverseAgent |
| Analysis agent | {Domain}AnalysisAgent | TechnicalAnalysisAgent |

**Rule:** Agent names must communicate the agent's perspective or bias, not
its implementation mechanism. An agent named "LLMAgent4" is not acceptable.

---

## 4.13 Database Naming Standards

| Database Element | Convention | Examples |
|-----------------|-----------|---------|
| Database file | {domain}_db.sqlite | telemetry_db.sqlite, trades_db.sqlite |
| Table name | snake_case | trade_records, strategy_performance |
| Column name | snake_case | strategy_name, win_rate, created_at |
| Primary key | id | id |
| Foreign key | {referenced_table}_id | strategy_id, trade_id |
| Index | idx_{table}_{column} | idx_trades_strategy_id |
| Junction table | {table1}_{table2} | strategy_regime |
| Timestamp column | created_at, updated_at | created_at |

---

## 4.14 Schema Naming Standards

| Schema Element | Convention | Example |
|---------------|-----------|---------|
| Schema name | {Domain}Schema | TradeSchema, RegimeSchema |
| Schema version field | schema_version | schema_version |
| Schema file | {domain}_schema.json | trade_schema.json |

---

## 4.15 Event Naming Standards

| Event Type | Convention | Examples |
|-----------|-----------|---------|
| State change | {NOUN}_{PAST_TENSE_VERB} | KILL_SWITCH_ACTIVATED, REGIME_CHANGED |
| Action completed | {NOUN}_{VERB}D | ORDER_PLACED, STRATEGY_DISABLED |
| System event | SYSTEM_{EVENT} | SYSTEM_STARTUP, SYSTEM_SHUTDOWN |
| Alert event | ALERT_{NOUN}_{CONDITION} | ALERT_LATENCY_EXCEEDED |
| Data event | DATA_{NOUN}_{ACTION} | DATA_FEED_FAILED, DATA_FEED_RESTORED |

**Rule:** Event names must be in SCREAMING_SNAKE_CASE. Event names are permanent;
once published in a release, they cannot be renamed.

---

## 4.16 Observation Naming Standards

| Observation Type | Convention | Examples |
|-----------------|-----------|---------|
| Market observation | {MARKET}_{METRIC} | NIFTY_CLOSE, VIX_VALUE |
| Computed metric | {LAYER}_{METRIC} | MI_REGIME_SCORE, SL_WIN_RATE |

---

## 4.17 Knowledge Object Naming Standards

| Knowledge Object | Convention | Examples |
|-----------------|-----------|---------|
| Regime type | {ADJECTIVE}_REGIME | BULL_REGIME, BEAR_REGIME |
| Strategy type | {NOUN}_{APPROACH}_STRATEGY | MOMENTUM_BREAKOUT_STRATEGY |
| Market phase | {PHASE}_PHASE | TRENDING_PHASE, RANGING_PHASE |

---

## 4.18 Model Naming Standards

| Model Type | Convention | Examples |
|-----------|-----------|---------|
| Model file | {type}_{version}.pkl | knn_model_v2.pkl |
| Model class | {Type}Model | KNNRegimeModel |
| Model artifact | {model}_{date}_{version} | regime_knn_20260101_v1 |

---

## 4.19 Strategy Naming Standards

| Strategy Element | Convention | Examples |
|-----------------|-----------|---------|
| Strategy name | {APPROACH}_{MARKET}_{TYPE} | MOMENTUM_BULL_LONG |
| Strategy file | {approach}_{market}_{type}.json | momentum_bull_long.json |
| Strategy class | {Approach}{Market}Strategy | MomentumBullStrategy |

---

## 4.20 Configuration Naming Standards

| Config Element | Convention | Examples |
|---------------|-----------|---------|
| Config key | UPPER_SNAKE_CASE | PAPER_TRADING, LAYER_LATENCY_WARN_MS |
| Environment variable | IIOS_{UPPER_SNAKE_CASE} | IIOS_PAPER_TRADING |
| Feature flag | ENABLE_{FEATURE} | ENABLE_LIVE_TRADING, ENABLE_DHAN_FEED |

---

## 4.21 Logging Naming Standards

| Log Element | Convention | Examples |
|-----------|-----------|---------|
| Logger name | module __name__ | global_intelligence.global_data_ai |
| Log event type | {CATEGORY}_{VERB} | TRADE_PLACED, FEED_FAILED |
| Correlation ID | cycle_{timestamp}_{sequence} | cycle_20260705_143000_001 |

---

## 4.22 Metric Naming Standards

| Metric Type | Convention | Examples |
|-----------|-----------|---------|
| Latency metric | {layer}_{operation}_latency_ms | gi_fetch_latency_ms |
| Rate metric | {noun}_{event}_rate | trade_win_rate |
| Count metric | {noun}_{event}_count | strategy_active_count |
| Score metric | {system}_{dimension}_score | tqs_score, scs_score |

---

## 4.23 Report Naming Standards

| Report Type | Convention | Examples |
|-----------|-----------|---------|
| Daily report | {date}_{type}_report | 20260705_eod_report |
| Performance report | {period}_{metric}_report | weekly_pnl_report |
| Engineering report | {document_code}_{type} | IIOS-TST-ENG-001_status |

---

## 4.24 Document Naming Standards

| Document Type | Convention | Examples |
|-------------|-----------|---------|
| Engineering framework | {TOPIC}_FRAMEWORK.md | TESTING_ENGINEERING_FRAMEWORK.md |
| Architecture document | ARCHITECTURE.md | ARCHITECTURE.md |
| Status report | {TOPIC}_STATUS.md | DEPLOYMENT_STATUS.md |
| Decision record | {CODE}_EDR_{YEAR}.md | IIOS-BLD-001-EDR-2026.md |
| Runbook | {TOPIC}_RUNBOOK.md | INCIDENT_RUNBOOK.md |

---

## 4.25 Version Name Standards

| Version Element | Convention | Examples |
|----------------|-----------|---------|
| Application version | MAJOR.MINOR.PATCH | 1.2.3 |
| Pre-release | version-rc.N | 1.2.0-rc.1 |
| LTS designation | version-lts | 1.0.0-lts |
| Schema version | S.MAJOR.MINOR | S.1.2 |
| Model version | v{N} | v1, v2 |
| Document version | MAJOR.MINOR.PATCH | 1.0.0 |

---

## 4.26 Identifier Standards

| Identifier Type | Convention | Examples |
|----------------|-----------|---------|
| Trade ID | TRADE-{YYYYMMDD}-{SEQ} | TRADE-20260705-001 |
| Order ID | ORD-{YYYYMMDD}-{SEQ} | ORD-20260705-042 |
| Cycle ID | CYC-{TIMESTAMP} | CYC-20260705143000 |
| Build ID | BLD-{YYYYMMDD}-{PIPELINE}-{NUM} | BLD-20260705-CI-001 |
| Event ID | EVT-{LAYER}-{TIMESTAMP}-{SEQ} | EVT-10-20260705143001-001 |
| Document Code | IIOS-{DOM}-{TYPE}-{SEQ} | IIOS-ENG-STD-001 |
| Correlation ID | {CYCLE_ID}-{SEQ} | CYC-20260705143000-007 |

---

## 4.27 Naming Decision Table

| Question | If YES | If NO |
|---------|--------|-------|
| Is this a Python class? | PascalCase | Not a class |
| Is this a Python function or method? | snake_case | Not a function |
| Is this a constant or configuration key? | UPPER_SNAKE_CASE | Not a constant |
| Is this a private member? | _leading_underscore | Public member |
| Is this a database table? | snake_case | Not a DB table |
| Is this a system event? | SCREAMING_SNAKE_CASE | Not an event |
| Is this a file? | snake_case.py (code) / UPPER_SNAKE_CASE.md (doc) | — |
| Is this a Docker service? | kebab-case | Not a Docker service |
| Does this name use a domain term? | Keep the domain term | Add a domain term |

---

*End of Part IV*

---

# PART V — DOCUMENTATION STANDARDS

## 5.1 Documentation Philosophy

Documentation in IIOS is an engineering artifact with the same quality standards
as code. A module without documentation is incomplete. A document that is
outdated is a defect. A decision without a decision record is an invisible
assumption.

The documentation hierarchy:
1. Engineering Constitution (this document) — law.
2. Architecture documents — structural specification.
3. Engineering frameworks — domain standards (testing, deployment, exceptions, etc.).
4. Component specifications — per-component detail.
5. Engineering Decision Records — rationale for major decisions.
6. Runbooks — operational procedures.
7. Developer guides — practical how-to references.

---

## 5.2 Document Type 1 — Architecture Documents

**Purpose:** Define the structural architecture of IIOS: layers, components,
interfaces, and dependencies.

**Primary example:** ARCHITECTURE.md

**Required sections:**
- Layer list (all 17 layers with numbers and descriptions)
- Component diagram
- Dependency rules
- Critical interfaces with signatures
- Performance baselines
- Key singletons

**Size target:** 5,000–15,000 bytes (architectural documents are concise).

**Review:** Architecture Council approval required before any change is published.

**Update trigger:** Any change to the layer hierarchy, any new engine, any
change to Critical Interfaces.

---

## 5.3 Document Type 2 — Engineering Frameworks

**Purpose:** Comprehensive engineering specifications for major cross-cutting
concerns.

**Examples:** TESTING_ENGINEERING_FRAMEWORK.md, BUILD_DEPLOYMENT_ENGINEERING_FRAMEWORK.md,
EXCEPTION_AND_FAILURE_FRAMEWORK.md, SHARED_UTILITIES_FRAMEWORK.md, this document.

**Required sections:**
- Document header (Code, Version, Status)
- Table of Contents
- Philosophy (Part I)
- Taxonomy (Part II)
- Architecture/Rulebooks (Part III or IV)
- Standards/Rules (subsequent parts)
- Engineering Constitution (rules)
- Readiness Checklist
- Supplements
- Document Metrics
- Amendment History

**Size target:** 180,000–250,000 bytes / 3,500–5,000 lines.

**Review:** Architecture Council approval required.

**Update trigger:** Quarterly review; any major engineering change.

---

## 5.4 Document Type 3 — Knowledge Documents

**Purpose:** Capture domain knowledge: market regime definitions, strategy
specifications, risk model descriptions.

**Required sections:**
- Knowledge item type (empirical/specified/learned)
- Domain entity references (to ontology)
- Knowledge content
- Confidence score
- Provenance
- Version history
- Validation results

**Review:** Domain expert + Architecture Council.

---

## 5.5 Document Type 4 — Engineering Decision Records (EDR)

**Purpose:** Record every significant architectural and engineering decision
with its rationale, alternatives considered, and long-term implications.

**Required fields:**
- EDR Code (IIOS-{DOMAIN}-EDR-{SEQ})
- Decision title
- Context (problem being solved)
- Decision made
- Rationale
- Alternatives considered and why rejected
- Consequences (positive and negative)
- Date
- Author
- Status (Active / Superseded / Deprecated)

**Size target:** 200–1,000 words per EDR.

**Review:** Architecture Council review for all EDRs before Active status.

**Permanence:** EDRs are permanent. They are superseded but never deleted.

---

## 5.6 Document Type 5 — Runbooks

**Purpose:** Operational procedures for the production system: deployment, rollback,
incident response, disaster recovery.

**Required sections for each procedure:**
- Trigger condition
- Pre-conditions
- Step-by-step procedure (numbered)
- Expected outcomes at each step
- Failure handling per step
- Completion criteria
- Post-procedure actions

**Review:** Platform Team + Architecture Council review.

**Testing:** Runbooks are tested at least quarterly by executing the procedure
in staging.

---

## 5.7 Document Type 6 — Component Specifications

**Purpose:** Define the engineering specification of a specific IIOS engine
or module.

**Required sections:**
- Purpose
- Layer assignment
- Inputs (typed)
- Outputs (typed)
- Dependencies
- Lifecycle
- Failure modes (exhaustive list)
- Recovery procedures
- Configuration parameters
- Monitoring
- Testing requirements
- Certification level required

**Review:** Component owner + Architecture Council.

---

## 5.8 Document Type 7 — Developer Documentation (Module Docstrings)

**Purpose:** In-code documentation explaining the purpose, interface, and
behavior of every public class and function.

**Required for every public module:**
- Module-level docstring: purpose, layer, owner.

**Required for every public class:**
- Class purpose and responsibility.

**Required for every public method:**
- Parameters: name, type, description.
- Returns: type and description.
- Raises: exception types that can be raised.
- Side effects if any.

**Review:** PR reviewers enforce in code review.

---

## 5.9 Document Type 8 — Operational Documentation

**Purpose:** Documentation for operators managing the production system.

**Includes:** Deployment guides, monitoring guides, alert response guides,
configuration guides.

**Review:** Platform Team + Operations Team.

**Update trigger:** Any change to the production system that affects operations.

---

## 5.10 Document Type 9 — Research Documentation

**Purpose:** Document research activities in the Research Lab (Layer 15):
strategy evolution campaigns, backtesting experiments, market studies.

**Required sections:**
- Research question
- Methodology
- Dataset used (version)
- Results
- Conclusions
- Promotion decision (promoted / not promoted, with rationale)

---

## 5.11 Document Type 10 — Release Notes

**Purpose:** Human-readable summary of every production release.

**Required sections:**
- Version and date
- Summary of changes
- New capabilities
- Defects resolved
- Performance changes
- Breaking changes (if any)
- Migration notes
- Known issues

**Review:** Architecture Council before publication.

---

## 5.12 Document Type 11 — Version History

**Purpose:** Cumulative record of all version changes.

**Format:** Table with Version, Date, Type (MAJOR/MINOR/PATCH/HOTFIX), and Summary.

**Location:** Every major engineering document includes an Amendment History table.

---

## 5.13 Document Type 12 — Glossary

**Purpose:** Define all technical and domain terms used in IIOS engineering.

**Requirements:**
- Every document that introduces new terms includes a glossary.
- The master glossary (Supplement I of this document) is the authoritative reference.
- Glossary terms are linked from their first appearance in each document.
- Contradictory definitions between documents are a defect.

---

## 5.14 Document Type 13 — Document Lifecycle

**Lifecycle stages:**
1. DRAFT — in preparation, not yet reviewed.
2. REVIEW — under Architecture Council review.
3. ACTIVE — approved and current.
4. DEPRECATED — superseded; still applicable but has a successor.
5. ARCHIVED — no longer applicable; retained for reference.

**Lifecycle rules:**
- No document goes from DRAFT to ACTIVE without Architecture Council review.
- DEPRECATED documents remain accessible but are prominently marked.
- ARCHIVED documents are retained permanently.
- Every document transition is recorded in the governance audit trail.

---

*End of Part V*

---

# PART VI — ENGINEERING REVIEW FRAMEWORK

## 6.1 Review Philosophy

Reviews in IIOS are not gatekeeping exercises — they are quality multipliers.
A well-conducted review catches defects that the author missed, improves clarity,
verifies compliance with standards, and transfers knowledge between team members.

Reviews are collaborative, not adversarial. Reviewer comments are constructive.
Authors treat review comments as opportunities to improve, not as criticism.
The standard for a review is: "After this review, is the change better than
it was before?" Not: "Has the reviewer demonstrated their authority?"

---

## 6.2 Review Type 1 — Architecture Review

**Trigger:** Any new layer, engine, or major subsystem; any change to the 17-layer
hierarchy; any change to Critical Interfaces.

**Reviewers:** Architecture Council (full).

**Format:** Structured review meeting with evidence package.

**Evidence package includes:**
- Proposed architecture diagram.
- Dependency impact analysis (which layers are affected).
- Interface specification.
- Performance impact assessment.
- Failure mode analysis.
- Test strategy.

**Outcomes:** Approved / Approved with conditions / Rejected.

**Timeline:** Minimum 5 business days for review.

---

## 6.3 Review Type 2 — Code Review Principles

**Trigger:** All code changes via PR.

**Reviewers:** Minimum 2, including at least one with relevant domain knowledge.

**Review checklist:**
- Correctness: does the code do what it says it does?
- Standards: does the code follow all applicable rulebooks?
- Tests: are tests present and meaningful?
- Performance: are there latency regressions?
- Security: are there OWASP Top 10 vulnerabilities?
- Documentation: is documentation updated?
- Dependencies: are new imports justified?
- Interface stability: are existing interfaces preserved?

**Timeline:** 2 business days maximum.

**Comment resolution:** All comments are resolved (either addressed or explicitly
accepted with documented rationale) before merge.

---

## 6.4 Review Type 3 — Document Review

**Trigger:** New engineering documents; significant updates to existing documents.

**Reviewers:** Architecture Council; relevant domain experts.

**Review checklist:**
- Document Code, Version, Status present.
- All required sections present.
- Technical accuracy verified.
- References to other documents correct.
- Amendment History updated.
- Size target met.

**Timeline:** 3 business days.

---

## 6.5 Review Type 4 — Knowledge Review

**Trigger:** Changes to the knowledge base; new domain facts; learning system
updates exceeding defined thresholds.

**Reviewers:** Domain expert + Architecture Council representative.

**Review checklist:**
- Knowledge source documented.
- Confidence score appropriate.
- Consistency with existing knowledge verified.
- Ontology consistency verified.

---

## 6.6 Review Type 5 — Ontology Review

**Trigger:** Any change to the market domain ontology: new entities, modified
properties, new relationships.

**Reviewers:** Architecture Council.

**Review checklist:**
- Entity ID stability (existing IDs unchanged).
- Backward compatibility of property changes.
- Consistency with existing entities.
- All references to new entities documented.

---

## 6.7 Review Type 6 — Security Review

**Trigger:** Any change touching authentication, authorization, data access,
external API integration, or the risk/trading engine.

**Reviewers:** Security Team + Architecture Council.

**Review checklist:**
- OWASP Top 10 vulnerabilities.
- No secrets in code.
- All SQL parameterized.
- External inputs validated.
- Privilege escalation paths.
- Dependency CVEs.

---

## 6.8 Review Type 7 — Performance Review

**Trigger:** Any change on the critical trading cycle path; any change to
components with latency thresholds.

**Reviewers:** Platform Team + component owner.

**Review checklist:**
- Benchmark results compared to baseline.
- No regression > 10% on any benchmark.
- GlobalIntelligence latency <= 17ms (cache hit).
- Full cycle <= 200ms.

---

## 6.9 Review Type 8 — Operational Review

**Trigger:** Before each production deployment; after each P0/P1 incident.

**Reviewers:** Platform Team + Architecture Council.

**Review checklist:**
- Deployment runbook current.
- Rollback procedure verified.
- Monitoring and alerting configured.
- Health checks defined.
- Post-deployment verification plan ready.

---

## 6.10 Review Type 9 — Release Review

**Trigger:** Before every production release.

**Reviewers:** Architecture Council (all members).

**Review checklist:**
- All release gates PASS.
- Release notes complete.
- Rollback verified in staging.
- Change list complete.
- Known issues documented.
- Architecture Council unanimously approves.

---

## 6.11 Review Type 10 — Certification Review

**Trigger:** Any component seeking lifecycle level advancement to PRODUCTION-READY.

**Reviewers:** Architecture Council (all members) + component owner.

**Review checklist:**
- TQS >= 0.90.
- SCS >= 0.92.
- All HARD readiness checks PASS.
- Evidence package complete.
- 30-day stability period completed.
- Security review complete.

---

## 6.12 Review Type 11 — Continuous Improvement Review

**Trigger:** Quarterly.

**Reviewers:** Architecture Council.

**Review subjects:**
- Engineering standards effectiveness.
- Defect trends.
- Performance trends.
- Documentation currency.
- Process improvements identified from incidents.
- Engineering debt tracking.

**Outcomes:** Action items with owners and target dates.

---

*End of Part VI*

# PART VII — QUALITY STANDARDS

## 7.1 Quality Framework Overview

Quality in IIOS is not subjective. It is measurable. Every quality dimension
has defined thresholds, measurement methods, and governance processes. A component
that does not meet its quality thresholds is not production-ready.

Quality is measured at two levels: component quality (how well a specific engine
meets its standards) and system quality (how well the integrated 17-layer system
performs as a whole).

---

## 7.2 Quality Dimension 1 — Maintainability

**Definition:** The ease with which the system can be modified to correct defects,
improve performance, or adapt to changed requirements.

**Metrics:**
- Mean time to implement a defect fix: target <= 4 hours for P2, <= 1 hour for P1.
- Cyclomatic complexity: no function exceeds 15. Average module complexity <= 8.
- Code duplication: < 5% duplicated code across all modules.
- Dependency count per module: <= 5 direct dependencies.

**Measurement:** Static analysis tools run in CI pipeline.

**Threshold for PRODUCTION-READY:** All metrics within threshold.

---

## 7.3 Quality Dimension 2 — Reliability

**Definition:** The probability that the system operates correctly over a
defined time period under defined conditions.

**Metrics:**
- System uptime during market hours: >= 99.5%.
- Mean cycles without error per session: target >= 1000.
- Error rate per cycle: < 0.1%.
- Unhandled exception rate: 0 (all exceptions are handled and logged).

**Measurement:** ControlTower telemetry; daily health report.

**Threshold for PRODUCTION-READY:** Uptime >= 99.5%; unhandled exceptions = 0.

---

## 7.4 Quality Dimension 3 — Availability

**Definition:** The proportion of time the system is operational and accessible
for its intended function.

**Metrics:**
- Production availability: >= 99.5% during market hours.
- Maximum planned downtime per month: < 45 minutes.
- Maximum unplanned downtime per incident: < 30 minutes.
- Restart recovery time: < 60 seconds.

**Measurement:** Docker health check history; uptime monitoring.

---

## 7.5 Quality Dimension 4 — Performance

**Definition:** The responsiveness and throughput of the system under expected
and peak conditions.

**Metrics:**
- Full trading cycle latency: <= 172ms baseline; <= 200ms SLA.
- GlobalIntelligence latency (cache hit): <= 17ms p99.
- MarketIntelligence latency: <= 19ms p99.
- No benchmark regression > 10% between releases.
- Memory usage: stable over 8-hour trading session (< 5% growth).

**Measurement:** SystemMonitor timing; benchmark suite in CI.

**Threshold for PRODUCTION-READY:** All latency baselines met; no regression > 10%.

---

## 7.6 Quality Dimension 5 — Security

**Definition:** The resistance of the system to unauthorized access, data
exposure, and malicious manipulation.

**Metrics:**
- CVEs at CRITICAL severity: 0 unresolved.
- CVEs at HIGH severity: 0 unresolved.
- OWASP Top 10 vulnerabilities: 0.
- Secrets in repository: 0 (automated scan).
- Parameterized SQL usage: 100%.

**Measurement:** Automated security scan in CI; dependency CVE scan.

**Threshold for PRODUCTION-READY:** All security metrics at 0 violations.

---

## 7.7 Quality Dimension 6 — Documentation Quality

**Definition:** The completeness, accuracy, and currency of all engineering
and operational documentation.

**Metrics:**
- Modules with complete docstrings: >= 95%.
- Engineering frameworks reviewed in last 12 months: 100%.
- Runbooks tested in last 90 days: 100%.
- Engineering Decision Records for significant decisions: >= 95%.
- Outdated document defects: 0 at release time.

**Measurement:** Documentation coverage scan; quarterly documentation review.

---

## 7.8 Quality Dimension 7 — Knowledge Quality

**Definition:** The accuracy, currency, and consistency of the knowledge base.

**Metrics:**
- Knowledge items with documented provenance: 100%.
- Knowledge items consistent with ontology: 100%.
- Knowledge contradictions unresolved: 0.
- Knowledge items not updated in > 90 days: tracked and reviewed.

**Measurement:** Knowledge base integrity check (automated).

---

## 7.9 Quality Dimension 8 — Architecture Quality

**Definition:** The adherence to the 17-layer architecture and the engineering
principles defined in Part I.

**Metrics:**
- Layer violations (cross-layer imports going up): 0.
- Circular dependencies: 0.
- Critical Interface signature changes (without MAJOR version): 0.
- Modules without layer assignment: 0.

**Measurement:** Import analysis in CI pipeline.

---

## 7.10 Quality Dimension 9 — Consistency

**Definition:** The uniformity of engineering practices across all components.

**Metrics:**
- Naming violations detected by linter: 0 at merge.
- Configuration accessed without named constants: 0.
- Log entries not in structured format: 0.
- Database queries not using parameterized SQL: 0.

**Measurement:** Automated linting and static analysis.

---

## 7.11 Quality Dimension 10 — Scalability

**Definition:** The ability of the system to handle growth without architectural changes.

**Metrics:**
- Any module with hardcoded instance count assumptions: 0.
- Database tables without indexes on frequently queried columns: flagged.
- Synchronous operations that could block the trading cycle: 0.

**Measurement:** Architectural review; code review.

---

## 7.12 Quality Dimension 11 — Extensibility

**Definition:** The ease with which new capabilities can be added without
modifying existing working components.

**Metrics:**
- New features requiring modification of protected modules: 0 (without explicit instruction).
- New agent addition requiring changes to existing agents: 0.
- New strategy type requiring changes to execution engine: 0.

**Measurement:** Architectural review at feature design time.

---

## 7.13 Quality Dimension 12 — Operational Readiness

**Definition:** The degree to which the system can be operated and recovered
by qualified engineers without requiring the original authors.

**Metrics:**
- Runbooks covering all common failure scenarios: 100%.
- Operators who can execute deployment without assistance: >= 2.
- Mean time to diagnosis for P1 incidents: <= 15 minutes.
- Monitoring coverage of all 17 layers: 100%.

**Measurement:** Quarterly operational drill; incident metrics.

---

## 7.14 Quality Dimension 13 — Engineering Maturity

**Definition:** The level of process sophistication and discipline in the
engineering organization.

**Metric — Engineering Maturity Model (EMM):**

`
Level 1 — INITIAL
  Description: Processes are ad hoc and reactive.
  Indicators: No standards document; no review process; testing is informal.

Level 2 — MANAGED
  Description: Processes are planned and tracked.
  Indicators: Review process exists; basic testing; some documentation.

Level 3 — DEFINED
  Description: Processes are formally defined and documented.
  Indicators: This document exists; review types defined; testing framework.

Level 4 — QUANTITATIVELY MANAGED
  Description: Processes are measured and controlled.
  Indicators: Quality metrics tracked; thresholds enforced; baselines maintained.

Level 5 — OPTIMIZING
  Description: Processes are continuously improving.
  Indicators: Quarterly reviews; improvement actions tracked; predictive quality.
`

**IIOS Target:** Level 4, progressing to Level 5.

**Measurement:** Quarterly Engineering Maturity Assessment.

---

*End of Part VII*

---

# PART VIII — GOVERNANCE FRAMEWORK

## 8.1 Governance Philosophy

Governance in IIOS exists to ensure that the system is built, operated, and
evolved in a disciplined, auditable, and sustainable way. Governance is not
bureaucracy — it is the mechanism through which architectural intent is preserved
across personnel changes, time pressure, and organizational evolution.

Governance operates at three levels: ownership (who is responsible), authority
(who can approve), and accountability (who is answerable for outcomes).

---

## 8.2 Governance Domain 1 — Ownership

**Engineering ownership model:**

| Component | Owner | Governance Level |
|---------|-------|----------------|
| 17-layer architecture | Architecture Council | Full |
| Individual engines | Designated team | Component |
| Protected modules | Architecture Council | Full |
| Critical interfaces | Architecture Council | Full |
| Knowledge base | Knowledge Engineering team | Domain |
| Market ontology | Architecture Council | Full |
| Test suite | Testing Team | Testing |
| Infrastructure | Platform Team | Infrastructure |
| Security | Security Team | Security |
| Deployment | Platform Team + Council | Joint |

**Ownership transfer:** Component ownership can be transferred with Architecture
Council approval and documented handoff.

---

## 8.3 Governance Domain 2 — Review Authority

| Decision Type | Authority | Vote Required |
|-------------|---------|--------------|
| Architecture change | Architecture Council | Unanimous |
| New engine | Architecture Council | Unanimous |
| Production deployment | Architecture Council | Unanimous |
| Interface change | Architecture Council | Unanimous |
| Feature merge to main | PR reviewers | 2 approvals |
| Security exception | Security Team | + 1 Council |
| LTS designation | Architecture Council | Unanimous |
| Emergency release | Council chair + 1 | Majority |
| DR activation | Architecture Council | Majority |
| Knowledge base update | Domain owner | + 1 Council |
| Ontology change | Architecture Council | Unanimous |
| Test standard change | Testing Team | + 1 Council |

---

## 8.4 Governance Domain 3 — Approval Workflow

**Standard approval workflow:**
1. Engineer submits change with documentation.
2. Automated checks run (CI/CD).
3. Domain owner reviews.
4. Required reviewers review.
5. All comments resolved.
6. Required approvals granted.
7. Change merged or deployed.

**Architecture Council approval workflow (for architectural changes):**
1. Proposal submitted with evidence package.
2. 5-day review period.
3. Architecture Council meeting (all members).
4. Vote recorded.
5. Decision and rationale recorded in EDR.
6. Approval or rejection communicated.

---

## 8.5 Governance Domain 4 — Version Governance

- Version numbers are assigned by the Version Manager.
- Released versions are immutable.
- MAJOR version changes require unanimous Architecture Council approval.
- LTS designations are Architecture Council decisions.
- Version history is permanent and never truncated.
- Breaking changes are announced 2 releases in advance.

---

## 8.6 Governance Domain 5 — Architecture Governance

**Architectural constants (require unanimous Council for change):**
- Layer count (currently 17).
- Layer order and dependency rules.
- Kill switch thresholds (VIX >= 45.0, daily loss >= 2.0%).
- Decision threshold (6.5).
- Performance baselines (172ms full cycle, 17ms GlobalIntelligence).
- Promotion gate thresholds (WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%).

**Architectural evolution process:**
1. Proposal with architectural impact assessment.
2. Architecture Council review.
3. Engineering Decision Record created.
4. Unanimous approval.
5. Implementation.
6. Validation in staging for minimum 14 days.
7. Production deployment per standard process.

---

## 8.7 Governance Domain 6 — Knowledge Governance

- All knowledge changes are reviewed by the domain owner.
- Knowledge that directly influences trading decisions requires Architecture
  Council awareness.
- Learned knowledge updates exceeding a confidence score change of > 0.2 in
  any strategy require Architecture Council notification.
- Knowledge contradictions are escalated to the domain owner within 24 hours.

---

## 8.8 Governance Domain 7 — Repository Governance

- Main branch is protected. No direct commits; only reviewed PRs.
- Release branches are protected after cut.
- Tags are protected; only the Version Manager creates release tags.
- No force-push to any shared branch.
- Repository settings are reviewed quarterly.

---

## 8.9 Governance Domain 8 — Quality Governance

- Quality metrics are reviewed quarterly.
- Any quality metric below threshold triggers an improvement plan.
- Improvement plans have owners, timelines, and Architecture Council tracking.
- Quality thresholds may not be lowered without Architecture Council approval
  and a documented rationale.

---

## 8.10 Governance Domain 9 — Audit Process

**Audit events (all recorded in governance audit trail):**
- Every production deployment.
- Every rollback.
- Every Architecture Council decision.
- Every kill switch activation/deactivation.
- Every security exception.
- Every configuration change.
- Every feature flag change.
- Every certification decision.
- Every version release.

**Audit trail properties:**
- Append-only.
- Retained for minimum 7 years.
- Accessible by Architecture Council.
- Reviewed quarterly for completeness.

---

## 8.11 Governance Domain 10 — Compliance

- All trading activity records retained for 7 years (regulatory requirement).
- All deployment audit records retained for 7 years.
- Security scans performed at every release.
- CVE resolution SLAs enforced.
- SEBI regulations compliance verified annually.

---

## 8.12 Governance Domain 11 — Continuous Evolution

**Quarterly governance activities:**
- Engineering standards review (this document).
- Quality metrics review.
- Incident analysis and learning.
- Process improvement action tracking.
- Architecture evolution discussion.
- Engineering debt review.

**Annual activities:**
- Full document review for all Active engineering frameworks.
- Regulatory compliance review.
- Engineering maturity assessment.
- Strategic architecture planning.

---

*End of Part VIII*

---

# PART IX — ENGINEERING CONSTITUTION

## 9.1 Preamble

The Engineering Constitution defines 130 binding engineering rules that govern
every aspect of IIOS development, documentation, review, governance, and evolution.
These rules are not guidelines. They are engineering law. Violations are governance
defects requiring remediation. Exceptions require Constitutional Amendment Records.

The rules are organized into 16 categories:
- ARC: Architecture (001–010)
- DOC: Documentation (011–020)
- KNW: Knowledge (021–027)
- REP: Repository (028–035)
- MOD: Modules and Packages (036–044)
- NAM: Naming (045–055)
- DEP: Dependencies (056–062)
- QUA: Quality (063–072)
- SEC: Security (073–080)
- PER: Performance (081–087)
- SCA: Scalability (088–092)
- REV: Reviews (093–100)
- GOV: Governance (101–110)
- CER: Certification (111–117)
- EVO: Evolution (118–126)
- SUS: Long-term Sustainability (127–130)

---

## 9.2 Architecture Rules (ARC)

**ARC-001:** The IIOS 17-layer hierarchy is the authoritative system structure.
Every component belongs to exactly one layer. Layerless components do not exist.

**ARC-002:** A component may depend only on components in the same layer or
in lower-numbered layers. Upward dependencies are architectural violations.

**ARC-003:** No circular dependencies exist at any level: module, package, or layer.

**ARC-004:** The Critical Interfaces listed in copilot-instructions.md may not
be changed without MAJOR version increment and Architecture Council unanimous vote.

**ARC-005:** New engines or subsystems require an Architecture Specification
document approved by the Architecture Council before any implementation begins.

**ARC-006:** Layer latency thresholds are architectural constants.
GlobalIntelligence WARN: 5,000ms; CRIT: 12,000ms. Default WARN: 2,000ms; CRIT: 5,000ms.
Changes require Architecture Council approval.

**ARC-007:** The kill switch (RiskGuardian, Layer 9) is architecturally isolated.
No component in Layers 1–8 can deactivate the kill switch.

**ARC-008:** All singleton instances are created through their defined getter
functions. Direct instantiation of singletons is prohibited.

**ARC-009:** No module embeds knowledge of the full 17-layer cycle. Every module
knows only its own responsibilities and the interfaces of layers it depends on.

**ARC-010:** Architecture diagrams in engineering documents are maintained in
sync with the implemented architecture. An outdated diagram is a documentation defect.

---

## 9.3 Documentation Rules (DOC)

**DOC-011:** Every engineering document has: Document Code, Version, Status, Scope, Owner.

**DOC-012:** Document codes follow the format: IIOS-{DOMAIN}-{TYPE}-{SEQ}.

**DOC-013:** No document advances from DRAFT to ACTIVE without Architecture Council review.

**DOC-014:** All documents are versioned with SemVer 2.0.0. Version history is maintained.

**DOC-015:** Documents are never deleted. They are deprecated or archived.

**DOC-016:** Every significant architectural decision has an Engineering Decision Record.

**DOC-017:** Engineering Decision Records are permanent. They may be superseded
but never deleted.

**DOC-018:** Every module has a module-level docstring stating its purpose and layer.

**DOC-019:** Every public class has a class docstring. Every public method has
a method docstring with parameters, return type, and exceptions.

**DOC-020:** Outdated documentation is a defect. Engineers are empowered and
expected to update documentation they find outdated.

---

## 9.4 Knowledge Rules (KNW)

**KNW-021:** All knowledge has a type (empirical, specified, or learned) and a provenance.

**KNW-022:** All knowledge has a confidence score. Knowledge without a confidence
score is not valid for trading decisions.

**KNW-023:** Knowledge accessed by trading decisions is immutable during a cycle.

**KNW-024:** Contradictory knowledge items are recorded and escalated. They are
never silently resolved by overwriting.

**KNW-025:** Knowledge is version-controlled. Previous knowledge states are recoverable.

**KNW-026:** All knowledge is consistent with the market ontology. Knowledge
referencing undefined entities is invalid.

**KNW-027:** Knowledge deprecation is formal: items are marked deprecated and
deleted only when all references are removed.

---

## 9.5 Repository Rules (REP)

**REP-028:** The main branch is always deployable. No broken builds on main.

**REP-029:** All changes to main require minimum 2 PR reviewer approvals.

**REP-030:** Commit messages follow TYPE(scope): description format. Invalid
commit messages are rejected by the CI pipeline.

**REP-031:** No binary artifacts, no secrets, no tokens, no credentials in source control.

**REP-032:** No PR merges with failing tests.

**REP-033:** No PR merges with test coverage below threshold.

**REP-034:** Branch names follow the defined naming convention.

**REP-035:** The .gitignore is maintained and reviewed quarterly.

---

## 9.6 Module and Package Rules (MOD)

**MOD-036:** Every module has exactly one layer assignment.

**MOD-037:** No module has cross-layer imports going upward.

**MOD-038:** No module has circular imports.

**MOD-039:** No module-level code with side effects executes at import time.

**MOD-040:** All constants are at module level or in config.py.

**MOD-041:** Private members use _leading_underscore.

**MOD-042:** No global mutable state shared across threads without a threading lock.

**MOD-043:** Modules do not catch exceptions they cannot meaningfully handle.

**MOD-044:** Every package has an __init__.py that defines its public API.

---

## 9.7 Naming Rules (NAM)

**NAM-045:** All Python classes use PascalCase.

**NAM-046:** All Python functions and methods use snake_case.

**NAM-047:** All Python constants and configuration keys use UPPER_SNAKE_CASE.

**NAM-048:** All private class members use _leading_underscore.

**NAM-049:** All database table names use snake_case.

**NAM-050:** All system events use SCREAMING_SNAKE_CASE.

**NAM-051:** All Docker services use kebab-case.

**NAM-052:** All engineering documents use UPPER_SNAKE_CASE.md.

**NAM-053:** All Python modules use snake_case.py.

**NAM-054:** Names reveal intent. Names that require reading the implementation
to understand are naming defects.

**NAM-055:** Abbreviations are used only for industry-standard terms (VIX, NIFTY,
P&L, SMA, EMA, RSI). Arbitrary abbreviations are prohibited.

---

## 9.8 Dependency Rules (DEP)

**DEP-056:** All production dependencies are pinned to exact versions in requirements.lock.

**DEP-057:** No floating version specifiers (>=, ~=, ^) in requirements.lock.

**DEP-058:** All dependencies are vulnerability-scanned before use.

**DEP-059:** CVEs at CRITICAL or HIGH severity are resolved before the next release.

**DEP-060:** New dependencies require justification in the PR description.

**DEP-061:** Dependencies are minimized. No package is included if standard
library or existing dependencies suffice.

**DEP-062:** Docker base images use digest-pinned references in production.

---

## 9.9 Quality Rules (QUA)

**QUA-063:** Test coverage meets thresholds: >= 95% line, >= 90% branch for production code.

**QUA-064:** All tests are deterministic. Flaky tests are defects requiring resolution within 14 days.

**QUA-065:** All tests are independent. No test depends on another test's state.

**QUA-066:** Safety-critical code (kill switch, risk limits) has 100% decision coverage (MC/DC).

**QUA-067:** All functions have cyclomatic complexity <= 15.

**QUA-068:** Code duplication is < 5% across the codebase.

**QUA-069:** All public modules have complete docstrings (module, class, method level).

**QUA-070:** No unhandled exceptions in production. All exceptions are caught,
logged, and handled at the appropriate architectural level.

**QUA-071:** All financial arithmetic uses high-precision decimal, not float.

**QUA-072:** Performance benchmarks are maintained and no release regresses > 10%.

---

## 9.10 Security Rules (SEC)

**SEC-073:** No secrets, tokens, credentials, or API keys are committed to source control.

**SEC-074:** All SQL queries use parameterized statements. String-formatted SQL
is prohibited.

**SEC-075:** All external inputs are validated at system boundaries.

**SEC-076:** All dependencies are scanned for CVEs at build time.

**SEC-077:** OWASP Top 10 vulnerabilities are addressed before any release.

**SEC-078:** SSH access to production uses key-based authentication only.

**SEC-079:** Access to production is restricted to Architecture Council members.

**SEC-080:** All audit logs are append-only. No log record is modified or deleted
within its retention period.

---

## 9.11 Performance Rules (PER)

**PER-081:** Full trading cycle latency must not exceed 200ms p99 in production.

**PER-082:** GlobalIntelligence fetch (cache hit) must not exceed 17ms p99.

**PER-083:** MarketIntelligence cycle must not exceed 19ms p99.

**PER-084:** No release regresses any performance benchmark by more than 10%.

**PER-085:** Memory usage is stable over a full trading session. Memory growth > 5% over
8 hours is a reliability defect.

**PER-086:** All performance baselines are documented and updated with each release.

**PER-087:** Performance tests are part of the release certification suite.

---

## 9.12 Scalability Rules (SCA)

**SCA-088:** No module embeds assumptions about being the only running instance.

**SCA-089:** No synchronous blocking operation exists on the critical trading path
beyond the defined latency budget.

**SCA-090:** All database tables have appropriate indexes for frequent queries.

**SCA-091:** All long-running operations are async or scheduled, not blocking.

**SCA-092:** Data stores are designed for volume growth without architectural changes.

---

## 9.13 Review Rules (REV)

**REV-093:** All changes to the main branch require minimum 2 PR reviewer approvals.

**REV-094:** Reviews are completed within 2 business days.

**REV-095:** All review comments are resolved before merge.

**REV-096:** Architectural changes require Architecture Council review.

**REV-097:** Security-impacting changes require Security Team review.

**REV-098:** Performance-impacting changes on the critical path require a
benchmark comparison before merge.

**REV-099:** Document reviews require at least one reviewer with domain expertise.

**REV-100:** Review decisions are recorded. "LGTM" without engagement with
the change is not an acceptable review.

---

## 9.14 Governance Rules (GOV)

**GOV-101:** Architecture Council approval is required for all PRODUCTION deployments.

**GOV-102:** The governance audit trail is append-only and retained for 7 years.

**GOV-103:** Every governance policy change requires Architecture Council approval
and an Engineering Decision Record.

**GOV-104:** Quarterly governance reviews are mandatory.

**GOV-105:** Emergency processes bypass the minimum required governance steps.
Bypassed steps are executed post-emergency and recorded.

**GOV-106:** All deployment authorization is written. Verbal authorization is
not valid.

**GOV-107:** Governance violations are recorded and tracked to resolution.
Unresolved violations older than 30 days are escalated to Architecture Council.

**GOV-108:** The Architecture Council is the final governance authority.

**GOV-109:** Architectural constants may only be changed by Architecture Council
unanimous vote.

**GOV-110:** All regulatory compliance records are retained for 7 years.

---

## 9.15 Certification Rules (CER)

**CER-111:** PRODUCTION-READY certification requires TQS >= 0.90 and SCS >= 0.92.

**CER-112:** Certification is valid for 90 days. Recertification is required
after the validity period.

**CER-113:** All HARD readiness checks must PASS for PRODUCTION-READY certification.

**CER-114:** Architecture Council unanimous vote is required for PRODUCTION-READY certification.

**CER-115:** Certification evidence is retained permanently.

**CER-116:** Safety-critical components (RiskGuardian, ExecutionEngine, DecisionEngine)
require security review as part of certification.

**CER-117:** Certification records are immutable once issued.

---

## 9.16 Evolution Rules (EVO)

**EVO-118:** New IIOS layers require Architecture Council unanimous approval.

**EVO-119:** The layer count (currently 17) triggers a MAJOR version increment if changed.

**EVO-120:** Additive changes are always preferred over modifying existing components.

**EVO-121:** Protected modules (risk_guardian, backtesting_ai, validation_engine,
evolved_strategies) are never modified without explicit instruction.

**EVO-122:** No component is renamed or moved without Architecture Council approval.

**EVO-123:** Technical debt is tracked explicitly. Debt items have owners and timelines.

**EVO-124:** Evolution planning is a standing item at quarterly Architecture Council reviews.

**EVO-125:** Every new dependency must be justified in the change that introduces it.

**EVO-126:** The Engineering Constitution is reviewed annually and amended as required.

---

## 9.17 Long-Term Sustainability Rules (SUS)

**SUS-127:** No change is made that only the original engineer can maintain.
Every change produces work that future engineers can understand, modify, and extend.

**SUS-128:** Documentation is updated as part of the same PR as the change.
Documentation debt is not acceptable.

**SUS-129:** Engineering knowledge is transferred. Any capability that only one
person understands is a sustainability risk requiring documentation and knowledge sharing.

**SUS-130:** The IIOS engineering system is itself engineered: it has specifications,
tests, reviews, and governance. The engineering process is not exempt from
engineering discipline.

---

*End of Part IX*

# PART X — CERTIFICATION CHECKLIST

## 10.1 Certification Framework Overview

The IIOS Certification Checklist is the formal readiness gate that every
component must pass before it receives PRODUCTION-READY certification.
The checklist covers 14 domains. Each domain has HARD checks (must pass)
and SOFT checks (strong preference; exceptions require Architecture Council
notation). A component that fails any HARD check is NOT PRODUCTION-READY.

**Certification Scoring:**
- TQS (Test Quality Score): fraction of test quality checks passed.
- SCS (System Certification Score): weighted fraction of all checks passed.
- PRODUCTION-READY threshold: TQS >= 0.90 AND SCS >= 0.92.

---

## 10.2 Domain 1 — Architecture Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| Layer assignment documented | HARD | Component has a documented layer |
| No upward cross-layer imports | HARD | Import analysis clean |
| No circular dependencies | HARD | Static analysis clean |
| Critical interfaces unchanged | HARD | Signature comparison passes |
| Architecture spec exists | HARD | Document in repository |
| Layer diagram up to date | SOFT | Diagram matches implementation |
| EDR exists for significant decisions | SOFT | Decision recorded |
| Singleton pattern used correctly | HARD | No duplicate instantiation |

---

## 10.3 Domain 2 — Repository Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| No secrets in repository | HARD | Automated secret scan passes |
| No binary artifacts | HARD | File type scan passes |
| Commit history clean | HARD | No merge commits to main without PR |
| .gitignore covers generated files | HARD | .gitignore review passes |
| Branch naming convention | SOFT | All active branches follow convention |
| Main branch protected | HARD | Branch protection rules active |
| Release tags created correctly | HARD | SemVer format verified |
| README accurate | SOFT | README reviewed within 90 days |

---

## 10.4 Domain 3 — Documentation Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| Module docstrings complete | HARD | >= 95% modules have docstrings |
| Class docstrings complete | HARD | >= 95% public classes have docstrings |
| Method docstrings complete | SOFT | >= 90% public methods have docstrings |
| Engineering framework exists | HARD | Domain framework document exists |
| Framework reviewed within 12 months | HARD | Review date recorded |
| All EDRs current | SOFT | No pending EDR decisions |
| Runbooks exist for all components | HARD | Runbook coverage >= 90% |
| Runbooks tested within 90 days | HARD | Test records exist |

---

## 10.5 Domain 4 — Knowledge Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| All knowledge has provenance | HARD | Provenance field present |
| All knowledge has confidence score | HARD | Score field present |
| No contradictions unresolved | HARD | Contradiction count = 0 |
| Knowledge consistent with ontology | HARD | Consistency check passes |
| Knowledge version history exists | HARD | History accessible |
| Knowledge tested in cycle integration | SOFT | Integration test covers knowledge access |
| Knowledge access is read-only during cycle | HARD | Threading analysis confirms isolation |

---

## 10.6 Domain 5 — Ontology Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| Ontology is published | HARD | Ontology document exists |
| Ontology version documented | HARD | Version in document header |
| Ontology reviewed by Council | HARD | Review record exists |
| No undefined entities in knowledge | HARD | Entity reference check passes |
| No undefined relationships in knowledge | HARD | Relationship reference check passes |
| Ontology changes tracked in EDR | SOFT | EDR for significant changes |
| Ontology aligns with SEBI classifications | HARD | Regulatory alignment reviewed |

---

## 10.7 Domain 6 — Configuration Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| All config accessed via named constants | HARD | Grep for magic numbers passes |
| No secrets in config files | HARD | Secret scan passes |
| Config validated at startup | HARD | Startup validation exists |
| Config change process documented | SOFT | Change process in runbook |
| Environment-specific config documented | HARD | Per-environment config documented |
| Config rollback process exists | SOFT | Rollback documented |

---

## 10.8 Domain 7 — Security Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| No CVEs at CRITICAL severity | HARD | Scan clean |
| No CVEs at HIGH severity | HARD | Scan clean |
| OWASP Top 10 addressed | HARD | Assessment passes |
| All SQL is parameterized | HARD | Code scan passes |
| All external inputs validated | HARD | Boundary validation present |
| Audit log is append-only | HARD | Log implementation reviewed |
| SSH key-based auth only | HARD | Server config verified |
| Secrets managed via secrets manager | HARD | No inline secrets |

---

## 10.9 Domain 8 — Performance Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| Full cycle <= 200ms p99 | HARD | Benchmark passes |
| GlobalIntelligence <= 17ms p99 | HARD | Benchmark passes |
| MarketIntelligence <= 19ms p99 | HARD | Benchmark passes |
| No benchmark regression > 10% | HARD | Comparison passes |
| Memory stable over 8h session | HARD | Memory profile passes |
| Baseline documented | HARD | Baseline record exists |
| Benchmark suite in CI | HARD | CI includes benchmarks |

---

## 10.10 Domain 9 — Quality Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| Line coverage >= 95% | HARD | Coverage report passes |
| Branch coverage >= 90% | HARD | Coverage report passes |
| Safety-critical code 100% MC/DC | HARD | Decision coverage report passes |
| No function complexity > 15 | HARD | Static analysis passes |
| Duplication < 5% | HARD | Duplication scan passes |
| No unhandled exceptions | HARD | Log analysis shows 0 unhandled |
| Financial arithmetic uses decimal | HARD | Code scan passes |
| TQS >= 0.90 | HARD | Score computed |

---

## 10.11 Domain 10 — Testing Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| All unit tests pass | HARD | Test run passes |
| All integration tests pass | HARD | Test run passes |
| All performance tests pass | HARD | Test run passes |
| All security tests pass | HARD | Test run passes |
| Regression suite passes | HARD | Test run passes |
| Tests are deterministic | HARD | No flaky tests in 30 days |
| Tests are independent | HARD | Test isolation verified |
| Test environment mirrors production | SOFT | Config parity reviewed |

---

## 10.12 Domain 11 — Deployment Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| CI/CD pipeline documented | HARD | Pipeline document exists |
| Rollback procedure documented | HARD | Runbook entry exists |
| Zero-downtime deployment verified | SOFT | Process reviewed |
| Docker images build clean | HARD | Build produces no errors |
| Docker health checks pass | HARD | Both containers healthy |
| Environment variable management documented | HARD | Documentation exists |
| Deployment approval workflow followed | HARD | Authorization record exists |
| Deployment smoke tests exist | HARD | Smoke test suite exists |

---

## 10.13 Domain 12 — Operations Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| All 17 layers monitored | HARD | Monitoring coverage verified |
| Alerting configured | HARD | Alert rules active |
| Incident response runbook exists | HARD | Runbook exists |
| DR plan exists and tested | HARD | DR test record exists |
| On-call process documented | SOFT | Process documented |
| Log retention configured | HARD | Retention policy active |
| Backup policy documented | HARD | Backup policy exists |
| Backup restoration tested | HARD | Test record exists |

---

## 10.14 Domain 13 — Governance Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| Architecture Council approval obtained | HARD | Approval record exists |
| All review comments resolved | HARD | PR shows 0 unresolved |
| Audit trail current | HARD | Audit trail reviewed |
| Governance violations resolved | HARD | Violation tracker shows 0 open |
| Compliance records current | HARD | Compliance review current |
| Engineering constitution violations: 0 | HARD | Constitution check passes |
| Quarterly review conducted | SOFT | Review record within 90 days |

---

## 10.15 Domain 14 — Future Readiness Certification

| Check | Type | Pass Criterion |
|-------|------|---------------|
| Engineering debt tracked | HARD | Debt register exists |
| Debt items have owners | HARD | Owner assigned to each item |
| Evolution roadmap documented | SOFT | Roadmap exists |
| No orphaned components | HARD | All components have owners |
| No undocumented assumptions | HARD | Assumption register clean |
| Technical risk register exists | SOFT | Risk register reviewed |
| Knowledge transfer complete | HARD | No single-person critical knowledge |

---

## 10.16 Certification Maturity Matrix

`
MATURITY   SCS Range   TQS Range   Meaning
--------   ---------   ---------   -------------------------------------------
LEVEL 1    < 0.70      < 0.70      NOT CERTIFIABLE — significant gaps
LEVEL 2    0.70–0.79   0.70–0.79   CANDIDATE — active remediation required
LEVEL 3    0.80–0.89   0.80–0.89   CONDITIONAL — exceptions documented
LEVEL 4    0.90–0.94   0.90–0.94   CERTIFIED — standard production ready
LEVEL 5    0.95–1.00   0.95–1.00   EXCELLENCE — benchmark for all components
`

**Target:** All production IIOS components at Maturity Level 4 or above.
**Aspirational:** All safety-critical components at Maturity Level 5.

---

*End of Part X*

---

# SUPPLEMENT A — ENGINEERING STANDARDS CATALOG

## A.1 Standards Reference Table

This supplement catalogs all 32 engineering standard categories defined in
Part II with their document owners and review cycles.

| Category | Code | Owner | Review Cycle | Current Version |
|----------|------|-------|--------------|----------------|
| Architecture Standards | ARC | Architecture Council | Annual | 1.0.0 |
| Repository Standards | REP | Platform Team | Semi-annual | 1.0.0 |
| Folder Structure Standards | FST | Architecture Council | Annual | 1.0.0 |
| Naming Standards | NAM | Architecture Council | Annual | 1.0.0 |
| Documentation Standards | DOC | Engineering Leads | Quarterly | 1.0.0 |
| Ontology Standards | ONT | Architecture Council | Annual | 1.0.0 |
| Knowledge Standards | KNW | Knowledge Engineering | Semi-annual | 1.0.0 |
| Entity Standards | ENT | Knowledge Engineering | Annual | 1.0.0 |
| Relationship Standards | REL | Knowledge Engineering | Annual | 1.0.0 |
| Event Standards | EVT | Architecture Council | Annual | 1.0.0 |
| Observation Standards | OBS | Data Engineering | Annual | 1.0.0 |
| Decision Standards | DEC | Architecture Council | Annual | 1.0.0 |
| Reasoning Standards | RSN | Architecture Council | Annual | 1.0.0 |
| AI Agent Standards | AIA | Architecture Council | Semi-annual | 1.0.0 |
| Model Standards | MDL | Research Team | Semi-annual | 1.0.0 |
| Database Standards | DBS | Platform Team | Annual | 1.0.0 |
| Schema Standards | SCH | Platform Team | Annual | 1.0.0 |
| API Standards | API | Architecture Council | Annual | 1.0.0 |
| Configuration Standards | CFG | Platform Team | Semi-annual | 1.0.0 |
| Logging Standards | LOG | Platform Team | Semi-annual | 1.0.0 |
| Testing Standards | TST | Testing Team | Quarterly | 1.0.0 |
| Deployment Standards | DEP | Platform Team | Semi-annual | 1.0.0 |
| Monitoring Standards | MON | Platform Team | Semi-annual | 1.0.0 |
| Security Standards | SEC | Security Team | Quarterly | 1.0.0 |
| Performance Standards | PER | Architecture Council | Semi-annual | 1.0.0 |
| Scalability Standards | SCA | Architecture Council | Annual | 1.0.0 |
| Versioning Standards | VER | Version Manager | Annual | 1.0.0 |
| Dependency Standards | DPD | Platform Team | Quarterly | 1.0.0 |
| Review Standards | REV | Architecture Council | Annual | 1.0.0 |
| Certification Standards | CER | Architecture Council | Annual | 1.0.0 |
| Operational Standards | OPS | Platform Team | Semi-annual | 1.0.0 |
| Future Evolution Standards | FUT | Architecture Council | Annual | 1.0.0 |

---

## A.2 Document Family Catalog

| Document Code | Title | Status | Version |
|--------------|-------|--------|---------|
| IIOS-ENG-STD-001 | Engineering Development Standards | ACTIVE | 1.0.0 |
| IIOS-TST-FRM-001 | Testing Engineering Framework | ACTIVE | 1.0.0 |
| IIOS-BLD-DEP-001 | Build and Deployment Engineering Framework | ACTIVE | 1.0.0 |
| IIOS-EXC-FRM-001 | Exception and Failure Framework | ACTIVE | 1.0.0 |
| IIOS-UTL-FRM-001 | Shared Utilities Framework | ACTIVE | 1.0.0 |
| IIOS-ARC-001 | Architecture Overview | ACTIVE | 1.0.0 |
| IIOS-OPS-RUN-001 | Operational Runbook | ACTIVE | 1.0.0 |
| IIOS-SEC-001 | Security Framework | PLANNED | — |
| IIOS-ONT-001 | Market Ontology | PLANNED | — |
| IIOS-KNW-001 | Knowledge Engineering Framework | PLANNED | — |
| IIOS-MON-001 | Monitoring and Observability Framework | PLANNED | — |
| IIOS-DRP-001 | Disaster Recovery Plan | PLANNED | — |

---

*End of Supplement A*

---

# SUPPLEMENT B — NAMING REFERENCE

## B.1 Quick Reference Card

`
PYTHON
  Class                      PascalCase              RiskGuardian
  Function / Method          snake_case              calculate_position_size()
  Module                     snake_case.py           order_manager.py
  Constant (module-level)    UPPER_SNAKE_CASE        MAX_POSITION_PCT
  Private attribute          _leading_underscore     _internal_state
  Parameter                  snake_case              instrument_id

DATABASE
  Table                      snake_case              strategy_performance
  Column                     snake_case              win_rate_pct
  Index                      idx_{table}_{columns}   idx_trades_symbol_date
  View                       vw_{name}               vw_active_positions

EVENTS
  System event               SCREAMING_SNAKE_CASE    CYCLE_STARTED
  Domain event               SCREAMING_SNAKE_CASE    TRADE_EXECUTED

DOCKER
  Service name               kebab-case              ai-trading-brain
  Volume name                kebab-case              trading-data

FILES
  Python module              snake_case.py
  Configuration              snake_case.yaml
  Engineering document       UPPER_SNAKE_CASE.md

BRANCHES
  Feature                    feature/{issue}-{desc}
  Bug fix                    fix/{issue}-{desc}
  Release                    release/{version}
  Hotfix                     hotfix/{version}-{desc}

VERSIONS
  Stable release             vMAJOR.MINOR.PATCH
  Pre-release                vMAJOR.MINOR.PATCH-beta.N
  Release candidate          vMAJOR.MINOR.PATCH-rc.N
`

---

## B.2 Prohibited Naming Patterns

| Pattern | Why Prohibited | Correct Alternative |
|---------|---------------|-------------------|
| temp, tmp, tmp1 | Lacks intent | Name by actual purpose |
| data, info, obj | Too generic | Name by specific entity |
| mgr, ctrl, util | Abbreviation without clarity | manager, controller, utils |
| processIt(), doThing() | Action without object | processTradeSignal(), executeOrder() |
| flag, val, n, x | Single-letter or vague | is_active, win_rate, count, price |
| class1, MyClass2 | Index-based names | Name by role and responsibility |

---

*End of Supplement B*

---

# SUPPLEMENT C — REVIEW TEMPLATES

## C.1 Architecture Review Template

`
ARCHITECTURE REVIEW RECORD
--------------------------
Review ID: ARR-{YYYY}-{SEQ}
Date: {date}
Component: {component name}
Layer: {layer number and name}
Reviewers: {names}

CHECKLIST:
[ ] Layer assignment is correct and documented
[ ] No upward cross-layer imports
[ ] No circular dependencies
[ ] Critical interfaces respected
[ ] Architecture spec exists
[ ] Singleton pattern correct
[ ] EDR exists for significant decisions

FINDINGS:
{List all findings with severity: BLOCKER | MAJOR | MINOR}

DECISION:
[ ] APPROVED   [ ] APPROVED WITH CONDITIONS   [ ] REJECTED

Conditions (if applicable): {conditions}

Signatures:
Reviewer 1: _________________   Date: _______
Reviewer 2: _________________   Date: _______
Council Chair: ______________   Date: _______
`

---

## C.2 Code Review Template

`
CODE REVIEW RECORD
------------------
PR Number: {number}
Date: {date}
Author: {author}
Reviewers: {names}
Component: {component}

CHECKLIST:
[ ] Naming conventions followed
[ ] No upward cross-layer imports
[ ] All exceptions handled
[ ] Tests included
[ ] Documentation updated
[ ] No secrets or magic numbers
[ ] SQL parameterized
[ ] Financial arithmetic uses decimal
[ ] Performance impact considered
[ ] Security impact considered

FINDINGS:
{List all comments with status: OPEN | RESOLVED}

DECISION:
[ ] APPROVED   [ ] CHANGES REQUESTED   [ ] REJECTED

Reviewer 1: _________________   Date: _______
Reviewer 2: _________________   Date: _______
`

---

## C.3 Document Review Template

`
DOCUMENT REVIEW RECORD
----------------------
Review ID: DRR-{YYYY}-{SEQ}
Date: {date}
Document: {document code and title}
Version reviewed: {version}
Reviewers: {names}

CHECKLIST:
[ ] Document code and title correct
[ ] Version header complete
[ ] Scope accurately described
[ ] Content technically accurate
[ ] Examples correct
[ ] No outdated references
[ ] Consistent with other active documents

FINDINGS:
{List all findings}

DECISION:
[ ] APPROVED   [ ] APPROVED WITH REVISIONS   [ ] RETURNED FOR REVISION

Reviewer: _________________   Date: _______
`

---

*End of Supplement C*

---

# SUPPLEMENT D — CERTIFICATION TEMPLATES

## D.1 Component Certification Record Template

`
COMPONENT CERTIFICATION RECORD
-------------------------------
CCR ID: CCR-{YYYY}-{SEQ}
Date: {date}
Component: {component name}
Layer: {layer number and name}
Version: {version}

CERTIFICATION SCORES:
  TQS (Test Quality Score):          {score}   [PASS / FAIL: >= 0.90]
  SCS (System Certification Score):  {score}   [PASS / FAIL: >= 0.92]

HARD CHECKS: {count passed} / {count total}
SOFT CHECKS: {count passed} / {count total}

OUTSTANDING EXCEPTIONS:
{List any SOFT check exceptions with Architecture Council notation}

CERTIFICATION DECISION:
  [ ] PRODUCTION-READY (TQS >= 0.90 AND SCS >= 0.92, all HARD checks passed)
  [ ] CONDITIONAL (exceptions documented)
  [ ] NOT CERTIFIABLE (remediation required)

Architecture Council Vote:
  Member 1: _________________ APPROVE / REJECT   Date: _______
  Member 2: _________________ APPROVE / REJECT   Date: _______
  Member 3: _________________ APPROVE / REJECT   Date: _______

Result: UNANIMOUS APPROVAL / REJECTED

Certification Valid Until: {date + 90 days}
`

---

## D.2 Release Certification Record Template

`
RELEASE CERTIFICATION RECORD
-----------------------------
RCR ID: RCR-{YYYY}-{SEQ}
Date: {date}
Release Version: {version}
Release Type: MAJOR / MINOR / PATCH / HOTFIX

COMPONENTS CERTIFIED:
{list of component CCR IDs}

RELEASE READINESS GATES:
[ ] All component certifications PRODUCTION-READY
[ ] Regression suite passes
[ ] Performance benchmarks pass (no regression > 10%)
[ ] Security scans clean
[ ] Breaking change documentation (if MAJOR)
[ ] Migration guide (if applicable)
[ ] Rollback plan documented

RELEASE AUTHORIZATION:
  Authorized by: _________________   Date: _______
  Architecture Council Chair: _________________   Date: _______

Deployment Window: {date and time}
Rollback Deadline: {date and time}
`

---

*End of Supplement D*

---

# SUPPLEMENT E — ARCHITECTURE DECISION RECORDS

## E.1 EDR Format

`
ENGINEERING DECISION RECORD
----------------------------
EDR ID: EDR-{YYYY}-{SEQ}
Date: {date}
Status: PROPOSED | ACCEPTED | SUPERSEDED | DEPRECATED
Superseded By: {EDR ID if superseded}

Title: {concise decision title}

Context:
{What situation required a decision? What constraints existed?
What options were considered?}

Decision:
{What was decided?}

Rationale:
{Why was this decision made? What evidence or reasoning supports it?}

Consequences:
POSITIVE: {what improves or becomes easier}
NEGATIVE: {what becomes harder or more complex}
NEUTRAL: {what changes without clear positive/negative}

Alternatives Rejected:
{Alternative 1}: {reason rejected}
{Alternative 2}: {reason rejected}

Council Vote: UNANIMOUS / MAJORITY (N for, M against)
Date of Vote: {date}
`

---

## E.2 EDR-2024-001 — 17-Layer Hierarchical Architecture

`
EDR ID: EDR-2024-001
Date: 2024-01-01
Status: ACCEPTED

Title: Adopt 17-layer hierarchical multi-agent architecture for IIOS

Context:
IIOS requires a system that can: gather global and market intelligence,
apply machine learning for strategy selection, manage risk at multiple levels,
execute trades with formal debate-based decision making, and continuously learn.
Multiple architectural patterns were considered.

Decision:
Adopt a 17-layer hierarchical architecture where each layer has a single
well-defined responsibility, and data flows strictly downward from global
context (Layer 1) to execution (Layer 11) and then upward through monitoring
and learning (Layers 12–14) and validation (Layers 15–16) to control (Layer 17).

Rationale:
The hierarchical model enables: (1) isolated testing of each layer,
(2) clear ownership and responsibility, (3) predictable data flow,
(4) kill switch placement at Layer 9 protecting all execution layers,
(5) monitoring and learning without coupling to trading logic.

Consequences:
POSITIVE: Testable, maintainable, extensible, auditable.
NEGATIVE: More boilerplate; inter-layer interfaces must be designed carefully.

Council Vote: UNANIMOUS
`

---

## E.3 EDR-2024-002 — Debate-Based Decision Engine

`
EDR ID: EDR-2024-002
Date: 2024-01-01
Status: ACCEPTED

Title: Adopt 5-agent debate with threshold 6.5 for trading decisions

Context:
Trading decisions require balancing multiple perspectives: momentum, value,
risk, and market structure. Single-agent decisions have known failure modes.
Committee-based decisions with threshold voting were evaluated.

Decision:
Implement a 5-agent debate at Layer 10 (DebateAndDecision). Each agent
scores a trade independently from 0–10. Trades proceed only when the
aggregated score exceeds 6.5. No agent can unilaterally approve or block.

Rationale:
Five agents provides sufficient diversity. Threshold 6.5 was calibrated
against backtests to balance trade frequency (not too conservative) with
quality (not too permissive). The debate format surfaces disagreements
and forces explicit reasoning.

Consequences:
POSITIVE: Higher quality decisions; auditable reasoning; no single point of failure.
NEGATIVE: Debate adds latency; all 5 agents must be maintained.

Council Vote: UNANIMOUS
`

---

## E.4 EDR-2024-003 — VIX Kill Switch Threshold

`
EDR ID: EDR-2024-003
Date: 2024-01-01
Status: ACCEPTED

Title: Set RiskGuardian kill switch at VIX >= 45.0 and daily loss >= 2.0%

Context:
Automated trading systems require hard stop conditions. Without explicit
thresholds, risk management relies entirely on position-level stops, which
may not be sufficient in extreme market conditions.

Decision:
RiskGuardian (Layer 9) halts all new trade execution when: VIX >= 45.0 OR
daily portfolio loss >= 2.0%. Existing positions are not force-closed by the
kill switch but no new positions are opened.

Rationale:
VIX 45.0 represents extreme market stress (above 99th percentile historically).
2.0% daily loss is a circuit breaker that preserves capital for recovery.
Both thresholds are independently sufficient to trigger the kill switch.

Consequences:
POSITIVE: Capital protection in extreme conditions.
NEGATIVE: May miss recovery opportunities immediately after a spike.

Council Vote: UNANIMOUS
`

---

## E.5 EDR-2024-004 — Strategy Promotion Gates

`
EDR ID: EDR-2024-004
Date: 2024-01-01
Status: ACCEPTED

Title: Set ResearchLab promotion gates: WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%

Context:
The strategy evolution system generates many candidate strategies. Without
formal promotion gates, low-quality strategies could reach production.

Decision:
A strategy is promoted from research to production only when all three
gates pass simultaneously: WinRate >= 50%, Sharpe Ratio > 0.8, MaxDD < 15%.
Strategies must pass a 6-stage ValidationEngine pipeline before promotion.

Rationale:
The three metrics are complementary. WinRate prevents pure tail-risk strategies.
Sharpe ensures risk-adjusted returns. MaxDD limits drawdown risk. The combination
filters for consistently profitable strategies with controlled risk.

Council Vote: UNANIMOUS
`

---

*End of Supplement E*

---

# SUPPLEMENT F — ENGINEERING ANTI-PATTERNS

## F.1 Anti-Pattern Catalog

Anti-patterns are recurring engineering mistakes that create technical debt,
fragility, or failure risk. All are prohibited in IIOS. Engineers discovering
an anti-pattern in existing code should raise a defect ticket.

---

### F.1.1 Layer Leakage

**Description:** A higher-numbered layer imports from a lower-numbered layer's
internal implementation rather than its public interface, or a lower-numbered
layer imports from a higher-numbered layer.

**Example:** MarketIntelligence (Layer 2) importing from ExecutionEngine (Layer 11).

**Risk:** Creates coupling that makes layers untestable in isolation, and
prevents changes to lower layers without cascading updates upward.

**Remedy:** Only import from lower layers through their defined public interfaces.
Layer 1 has no dependencies; each layer depends only on layers below it.

---

### F.1.2 Singleton Escape

**Description:** A singleton is instantiated directly (via constructor call)
rather than through its defined getter function, resulting in multiple instances
of what should be a unique object.

**Example:** 	racker = StrategyPerformanceTracker() instead of get_performance_tracker().

**Risk:** State divergence between instances; inconsistent data; race conditions.

**Remedy:** All singletons are accessed only through their getter functions.
Constructor calls are forbidden at call sites.

---

### F.1.3 Silent Failure

**Description:** An exception is caught and swallowed without logging, and
the system continues as if the operation succeeded.

**Example:** 	ry: fetch_data() except Exception: pass

**Risk:** Errors are invisible; incorrect state propagates; diagnosis is impossible.

**Remedy:** All caught exceptions must be logged at minimum WARNING level.
Exceptions that affect correctness must be propagated or handled explicitly.

---

### F.1.4 Magic Number Trading

**Description:** Numeric thresholds or constants embedded directly in business
logic rather than named constants in config.py.

**Example:** if vix > 45: stop_trading() instead of if vix > VIX_KILL_THRESHOLD.

**Risk:** Thresholds become invisible; changes require code modifications;
the same value is duplicated across files and diverges.

**Remedy:** All trading-significant constants live in config.py with
UPPER_SNAKE_CASE names. Business logic references only the constant name.

---

### F.1.5 Float Financial Arithmetic

**Description:** Using Python float for financial calculations involving currency,
percentages, or position sizing.

**Example:** pnl = trades * 0.1 (float multiplication).

**Risk:** IEEE 754 floating point errors accumulate. A small error in position
sizing compounds over thousands of trades into material reporting inaccuracies.

**Remedy:** All financial arithmetic uses Python's decimal.Decimal with
ROUND_HALF_UP rounding. float is only permitted for non-financial computations.

---

### F.1.6 Unparameterized SQL

**Description:** SQL queries assembled by string formatting or concatenation
with user-provided or externally-sourced values.

**Example:** cursor.execute(f"SELECT * FROM trades WHERE symbol='{symbol}'")

**Risk:** SQL injection. Attacker-controlled values can modify query logic,
extract confidential data, or destroy data.

**Remedy:** All SQL uses parameterized queries. The query and parameters are
always separate. This is a HARD security rule; violations are blocker defects.

---

### F.1.7 Scope Blindness (Class-Level Constants)

**Description:** A constant defined as a class attribute is referenced as a
bare name inside an instance method, causing a NameError at runtime.

**Example:** _SAME_ZONE_PCT = 0.02 at class level, then used as
if diff < _SAME_ZONE_PCT inside a method instead of self._SAME_ZONE_PCT.

**Risk:** Crashes in production only when the specific code path is exercised.
Earlier guards may prevent the path from being reached in testing, hiding the bug.

**Remedy:** All constants defined at class level must be accessed as self.CONSTANT
inside instance methods. After adding any class-level constant, grep all usages
immediately to confirm no bare references exist.

---

### F.1.8 Speculative Generality

**Description:** Adding abstraction, extension points, or configuration for
scenarios that do not yet exist and may never exist.

**Example:** Building a plugin system for data feeds when only one feed type
exists and no other is planned.

**Risk:** Increases complexity and maintenance burden for no current benefit.
Abstractions built for speculated futures are often wrong when the future arrives.

**Remedy:** Build for the current requirement. When extensibility genuinely becomes
necessary, refactor then. The IIOS principle: add, don't rewrite.

---

*End of Supplement F*

---

# SUPPLEMENT G — OPERATIONAL RUNBOOK

## G.1 Runbook Purpose and Scope

This supplement provides operational procedures for the five most common
IIOS operational scenarios. Full runbooks for each layer and subsystem
are maintained in the operational documentation collection.

---

## G.2 Scenario 1 — Production Container Not Starting

**Symptom:** docker compose ps shows container in Restarting or Exited state.

**Step 1:** Check container logs.
`
docker logs ai-trading-brain --tail 100
`

**Step 2:** Identify error. Common causes:
- Import error in modified Python module.
- Missing environment variable.
- Port conflict.
- SQLite database locked.

**Step 3:** If import error: fix the Python error, rebuild, redeploy.
`
docker compose build --no-cache
docker compose down
docker compose up -d
sleep 8
docker compose ps
`

**Step 4:** If environment variable: add to docker-compose.yml or .env file.

**Step 5:** If database locked: stop all containers, then restart.

**Resolution criterion:** Both containers show Up ... (healthy).

---

## G.3 Scenario 2 — Kill Switch Activated

**Symptom:** System logs show KILL_SWITCH_ACTIVATED. No new trades executing.

**Step 1:** Identify trigger.
`
docker logs ai-trading-brain | grep KILL_SWITCH
`

Common triggers: VIX >= 45.0 or daily loss >= 2.0%.

**Step 2:** Assess market conditions. Do not deactivate until trigger condition resolves.

**Step 3:** Monitor existing positions. Kill switch does not close existing positions.

**Step 4:** When trigger condition resolves (VIX drops, daily loss recovered,
or next trading day), kill switch deactivates automatically.

**Step 5:** Verify normal cycle resumes.
`
docker logs ai-trading-brain --tail 50
`

**Architecture Council notification:** Required within 30 minutes of kill switch activation.

---

## G.4 Scenario 3 — Dhan API 451 Error

**Symptom:** Data feed logs show 451 Unavailable For Legal Reasons from Dhan API.

**Step 1:** System automatically falls back to yfinance. Verify fallback active:
`
docker logs ai-trading-brain | grep -i "yfinance\|fallback"
`

**Step 2:** Check Dhan token validity:
`
python check_dhan_token.py
`

**Step 3:** If token expired, refresh via Dhan OAuth flow. See DHAN_OAUTH_SETUP.md.

**Step 4:** After token refresh, restart the container to reload credentials.

**Note:** During Dhan outage, yfinance provides sufficient data for paper trading.
Live trading with yfinance as sole data source requires Architecture Council review.

---

## G.5 Scenario 4 — Telegram Bot Not Responding

**Symptom:** Telegram commands sent to bot produce no response.

**Step 1:** Check Telegram bot process:
`
docker logs ai-trading-brain | grep -i telegram
`

**Step 2:** Verify bot token:
`
docker logs ai-trading-brain | grep -i "token\|bot.*started"
`

**Step 3:** Check bot rate limiting. Telegram limits bots to 30 messages/second.
If flooded: wait 60 seconds.

**Step 4:** If bot process crashed: restart container.

**Step 5:** Test with /status command after restart.

---

## G.6 Scenario 5 — High Cycle Latency

**Symptom:** SystemMonitor logs show LATENCY_WARN or LATENCY_CRIT for a layer.

**Step 1:** Identify the slow layer from logs.
`
docker logs ai-trading-brain | grep "LATENCY"
`

**Step 2:** For GlobalIntelligence (warn > 5000ms, crit > 12000ms):
Check network connectivity to data sources. Check cache health.

**Step 3:** For other layers (warn > 2000ms, crit > 5000ms):
Check if cycle aborted. If CRIT, cycle is aborted by SystemMonitor.

**Step 4:** For sustained latency: profile the slow layer.
Add timing logs. Identify the slow operation. Optimize or bypass.

**Step 5:** If issue persists across 3 consecutive cycles:
Architecture Council notification required.

---

*End of Supplement G*

---

# SUPPLEMENT H — DEVELOPER HANDBOOK

## H.1 Quick Start for New Engineers

**Day 1:**
1. Read ARCHITECTURE.md (complete, not skimming).
2. Read this document, Part I (Engineering Philosophy).
3. Set up local development environment following DEPLOYMENT_GUIDE.md.
4. Run the full test suite and confirm it passes.
5. Read the Engineering Constitution (Part IX).

**Day 2:**
1. Read the Engineering Decision Records in Supplement E.
2. Trace one full trading cycle through the codebase.
3. Read the layer you will be working in first.
4. Shadow your first code review before submitting one.

**Day 3:**
1. Make a small, low-risk change with full test coverage.
2. Submit a PR following all conventions.
3. Respond to all review comments within 24 hours.

---

## H.2 Daily Development Workflow

**Before you start:**
1. Pull latest main: git pull origin main
2. Create a feature branch: git checkout -b feature/{issue}-{description}
3. Confirm the test suite passes on main before branching.

**During development:**
1. Write tests first or alongside code (not after).
2. Run the linter before every commit: lake8 --max-complexity 15
3. Run the test suite for affected modules after every meaningful change.
4. Update documentation in the same commit as the code change.
5. Check for bare $variablename patterns if writing PowerShell content.

**Before submitting a PR:**
1. Run the full test suite.
2. Confirm coverage meets thresholds.
3. Run security scan: andit -r .
4. Run dependency scan: safety check
5. Confirm no secrets in staged changes.
6. Write a meaningful PR description: what changed, why, how tested.

**PR title format:** TYPE(scope): Short description
Types: feat, fix, perf, docs, test, chore, refactor, security.

---

## H.3 Common Patterns

**Accessing configuration:**
`python
from config import SOME_CONFIG_CONSTANT
# Never: if value > 45  (magic number)
# Always: if value > VIX_KILL_THRESHOLD  (named constant)
`

**Singleton access:**
`python
from learning_system.strategy_performance_tracker import get_performance_tracker
tracker = get_performance_tracker()
# Never: tracker = StrategyPerformanceTracker()  (direct instantiation)
`

**Class-level constants (avoid scope blindness):**
`python
class OrderManager:
    _SAME_ZONE_PCT = 0.02  # class attribute
    def check_zone(self, diff):
        if diff < self._SAME_ZONE_PCT:  # ALWAYS: self.
            pass
`

**Financial arithmetic:**
`python
from decimal import Decimal, ROUND_HALF_UP
pnl = Decimal("100.50") * Decimal("2")
rounded = pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
# Never: pnl = 100.50 * 2  (float)
`

**Parameterized SQL:**
`python
cursor.execute(
    "SELECT * FROM trades WHERE symbol = ? AND date >= ?",
    (symbol, start_date)
)
# Never: cursor.execute(f"SELECT ... WHERE symbol='{symbol}'")
`

**Structured logging:**
`python
import logging
logger = logging.getLogger(__name__)
logger.info("Trade executed: symbol=%s qty=%d price=%s", symbol, qty, price)
# Never: print("Trade executed:", symbol)
`

---

## H.4 What to Do When Uncertain

1. **Uncertain about architecture impact:** Stop. Read the relevant sections
   of ARCHITECTURE.md and this document. Ask the Architecture Council.
   Do not guess on architectural decisions.

2. **Uncertain about a protected module:** Do not modify it. Create a new
   module that wraps or extends it. Protected modules are protected for reasons
   that may not be obvious from the code.

3. **Uncertain about naming:** Follow the Naming Framework (Part IV).
   When in doubt, name by intent and responsibility, not by implementation.

4. **Uncertain about whether to create a new file vs. edit existing:**
   The IIOS principle is: prefer adding over modifying. If you can add a new
   module that is imported by existing code, do that. Only modify existing
   code when you cannot achieve the goal any other way.

5. **Uncertain about performance impact:** Measure first. Write a benchmark.
   Submit the benchmark comparison in your PR. Do not guess performance.

---

*End of Supplement H*

---

# SUPPLEMENT I — COMPREHENSIVE GLOSSARY

| Term | Definition |
|------|-----------|
| Agent | An autonomous decision-making component within one of the 17 IIOS layers. |
| Architecture Council | The governance body with final authority over all architectural decisions. |
| Architectural Constant | A value or threshold that is part of the architectural specification and may not change without Architecture Council unanimous approval. |
| Backtesting | The process of evaluating a strategy's historical performance against recorded price data. |
| Baseline | A measured, recorded performance metric against which future measurements are compared. |
| Branch Coverage | The fraction of all code branches (if/else, switch) exercised by a test suite. |
| Certification | The formal determination that a component is PRODUCTION-READY. |
| CircuitBreaker | A pattern that halts operations when a failure threshold is reached, preventing cascading failures. |
| Confidence Score | A numeric (0.0–1.0) value indicating the reliability of a knowledge item. |
| Constitution Rule | One of 130 binding engineering rules in Part IX of this document. |
| Critical Interface | A function or class signature that may not be changed without a MAJOR version increment and Architecture Council approval. |
| Cyclomatic Complexity | A measure of the number of independent paths through a function. IIOS limit: 15. |
| Daily Loss Threshold | The maximum permitted daily portfolio loss (2.0%) before the kill switch activates. |
| Debate Engine | The 5-agent deliberation system at Layer 10 that scores and approves trades. |
| Decision Score | The aggregated score from the 5 debate agents. Threshold for trade approval: 6.5. |
| EDR | Engineering Decision Record. A permanent record of a significant architectural decision. |
| EMM | Engineering Maturity Model. A 5-level scale measuring process sophistication. |
| Engineering Constitution | The 130 binding rules in Part IX governing all IIOS engineering activity. |
| Engineering Debt | Shortcuts, workarounds, or suboptimal decisions that reduce long-term quality. |
| Evolution | The intentional, governed process of improving or extending IIOS. |
| Feature Flag | A configuration-controlled mechanism to enable or disable features without deployment. |
| Feed Manager | The singleton data feed manager that routes data requests to Dhan or yfinance. |
| Governance Defect | A violation of the Engineering Constitution or governance process. |
| HARD Check | A certification check that must pass for PRODUCTION-READY certification. |
| Hotfix | An emergency patch release to address a critical production defect. |
| IIOS | Investment Intelligence Operating System. The full name of this system. |
| Kill Switch | The RiskGuardian (Layer 9) mechanism that halts new trade execution when thresholds are exceeded. |
| Knowledge Base | The persistent store of empirical, specified, and learned knowledge used in trading decisions. |
| LTS | Long-Term Support. A release with an extended maintenance commitment. |
| MaxDD | Maximum Drawdown. The largest peak-to-trough decline. Promotion gate: < 15%. |
| MC/DC | Modified Condition/Decision Coverage. Required for safety-critical code. |
| Ontology | The formal specification of entities, relationships, events, and vocabulary in the market domain. |
| Paper Trading | Simulated trading using real market data but no real money. |
| Parameterized SQL | SQL queries where parameters are passed separately, preventing injection. |
| Promotion Gate | The set of criteria a strategy must meet to advance from research to production. |
| Protected Module | A module that may not be modified without explicit user instruction. |
| Provenance | The documented origin and basis of a knowledge item. |
| RCR | Release Certification Record. The formal release readiness documentation. |
| Regime | A market condition classification (trending, ranging, volatile, etc.) used for strategy selection. |
| Repository | The source code repository managed under Git version control. |
| ResearchLab | Layer 15. The engine responsible for strategy research, evolution, and promotion gating. |
| RiskGuardian | Layer 9. The kill-switch layer that halts trading in extreme conditions. |
| Rollback | The process of reverting a production deployment to a known-good prior version. |
| SCS | System Certification Score. The weighted fraction of certification checks passed. |
| SEBI | Securities and Exchange Board of India. The regulatory authority for Indian securities markets. |
| Sharpe Ratio | A measure of risk-adjusted return. Promotion gate: > 0.8. |
| Singleton | A class with exactly one instance, accessed through a defined getter function. |
| SOFT Check | A certification check where exceptions may be noted with Architecture Council approval. |
| SemVer | Semantic Versioning 2.0.0. The versioning scheme used for all IIOS releases. |
| Strategy | A parameterized trading algorithm that generates buy/sell signals. |
| TQS | Test Quality Score. The fraction of test quality checks passed. Threshold: >= 0.90. |
| Traceability | The ability to trace any system behavior to its source in the architecture, code, or knowledge. |
| ValidationEngine | Layer 16. The 6-stage pipeline (Backtest, WFT, CrossMarket, MC, Sensitivity, Regime) for strategy validation. |
| VIX | Volatility Index. When >= 45.0, the kill switch activates. |
| Walk-Forward Testing | A validation method that tests a strategy on out-of-sample data following its training period. |
| WinRate | The fraction of trades that are profitable. Promotion gate: >= 50%. |
| Zero-Downtime Deployment | A deployment process that keeps the system operational throughout the deployment. |

---

*End of Supplement I*

---

# DOCUMENT METRICS

| Metric | Value |
|--------|-------|
| Document Code | IIOS-ENG-STD-001 |
| Document Title | Engineering Development Standards |
| Version | 1.0.0 |
| Status | ACTIVE |
| Parts | 10 |
| Supplements | 9 (A through I) |
| Engineering Philosophy Principles | 15 |
| Standards Taxonomy Categories | 32 |
| Rulebooks | 21 |
| Naming Element Types | 27 |
| Documentation Types | 13 |
| Review Types | 11 |
| Quality Dimensions | 13 |
| Governance Domains | 11 |
| Constitution Rules | 130 |
| Certification Domains | 14 |
| Engineering Anti-Patterns | 8 |
| Glossary Terms | 50+ |
| Architecture Council Approval | Required for ACTIVE status |

---

# AMENDMENT HISTORY

| Version | Date | Type | Description | Author |
|---------|------|------|-------------|--------|
| 0.1.0 | 2024-01-01 | INITIAL | Document created | Architecture Council |
| 0.2.0 | 2024-01-15 | MINOR | Engineering Constitution first draft | Architecture Council |
| 0.3.0 | 2024-02-01 | MINOR | Supplements A-F added | Engineering Leads |
| 0.4.0 | 2024-02-15 | MINOR | Supplements G-I added | Engineering Leads |
| 0.5.0 | 2024-03-01 | MINOR | Governance Framework added | Architecture Council |
| 1.0.0 | 2024-03-15 | MAJOR | Full document approved and activated | Architecture Council |

---

# CLOSING STATEMENT

This Engineering Development Standards document (IIOS-ENG-STD-001) is the
engineering foundation of the Investment Intelligence Operating System.

It defines not what the system does — ARCHITECTURE.md defines that — but
how the system is built, how it is reasoned about, how it is tested,
how it is evolved, and how it is governed.

Every line of code, every document, every knowledge item, every configuration
value, every review, and every deployment decision in IIOS is governed by
these standards. They are not aspirational. They are the engineering law of
this system.

The Engineering Constitution in Part IX codifies 130 specific rules. These
rules are designed to produce a system that is: correct by construction,
maintainable by future engineers who were not there at the beginning,
auditable by regulators and oversight bodies, resilient under market stress,
and sustainable over a multi-decade operating horizon.

Investment intelligence systems that operate in financial markets carry
responsibilities beyond those of ordinary software. A bug in a web application
causes user frustration. A bug in IIOS can cause financial loss. A governance
failure in IIOS can cause regulatory consequence. A latency regression in IIOS
can cause missed risk controls. The standards in this document exist because
these consequences are real and the engineering discipline to prevent them
must be equally real.

The Architecture Council ratifies this document as the authoritative Engineering
Constitution of IIOS. It enters effect upon ratification and governs all
present and future development activity.

Document Code: IIOS-ENG-STD-001
Version: 1.0.0
Status: ACTIVE
Effective: Upon Architecture Council unanimous ratification

---

*END OF DOCUMENT — IIOS-ENG-STD-001 — ENGINEERING DEVELOPMENT STANDARDS v1.0.0*

---

# SUPPLEMENT J — PER-LAYER ENGINEERING SPECIFICATIONS

## J.1 Purpose

This supplement documents the specific engineering requirements for each of the
17 IIOS layers. Every layer has distinct responsibilities, interfaces, latency
requirements, and testing obligations. These specifications are authoritative
and supplement the Architecture Overview (IIOS-ARC-001).

---

## J.2 Layer 1 — GlobalIntelligence

**Purpose:** Gather overnight global market context including S&P 500, Nikkei,
Nifty futures, bonds, and FX rates. Provide a GlobalSnapshot to all downstream layers.

**Owner:** Architecture Council

**Primary Class:** GlobalDataAI

**Critical Interface:**
`
GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot
`

**Performance Specification:**
- Cache hit (within 5-minute window): <= 17ms p99
- Cache miss (full network fetch): <= 5,000ms WARN; <= 12,000ms CRIT (abort cycle)
- Background pre-warm thread: refreshes cache every 4 minutes

**Engineering Requirements:**
- GlobalSnapshot is immutable once created. No layer may modify it.
- Cache is invalidated only by TTL or force=True.
- Background pre-warm thread must not block the main cycle thread.
- All fetch errors must be logged and the previous snapshot used as fallback.
- Snapshot includes provenance timestamp to allow downstream staleness detection.

**Testing Requirements:**
- Unit: cache hit/miss behavior; force=True invalidation.
- Integration: downstream layers receive GlobalSnapshot.
- Performance: cache hit <= 17ms, verified in benchmark suite.
- Resilience: network failure returns cached snapshot gracefully.

---

## J.3 Layer 2 — MarketIntelligence

**Purpose:** Assess NIFTY and BANKNIFTY regime, sector rotation, liquidity
conditions, and scheduled market events.

**Owner:** Market Engineering Team

**Primary Class:** MarketIntelligenceEngine

**Performance Specification:**
- Deep cycle latency: <= 19ms p99
- Continuous scan interval: 30 seconds

**Engineering Requirements:**
- Regime classification must be one of the 6 defined regimes (trending_up,
  trending_down, ranging, volatile, breakout, consolidating).
- Regime changes are events emitted to the EventBus.
- All 6 deep-scan slots must complete within the continuous scan interval.
- Index symbols (NIFTY, BANKNIFTY) use bare names; .NS suffix is not appended.
- MarketMonitor runs on its own scheduler thread independent of the main cycle.

**Testing Requirements:**
- Unit: regime classification logic; sector rotation signals.
- Integration: regime events received by Layer 3 MetaLearning.
- Performance: <= 19ms per deep cycle.
- Edge case: market closed periods, holiday handling.

---

## J.4 Layer 3 — MetaLearning

**Purpose:** Predict strategy weights for the current market regime using k-NN
learning on historical regime-performance data.

**Owner:** Research Engineering Team

**Primary Class:** MetaStrategyController

**Critical Singleton:** get_regime_strategy_map()

**Engineering Requirements:**
- k-NN model is retrained nightly during the post-market learning cycle.
- Strategy weights are normalized so they sum to 1.0.
- Weight updates are atomic: no partial updates visible to downstream layers.
- Regime-to-strategy map is written via get_regime_strategy_map(), not directly.

**Testing Requirements:**
- Unit: weight normalization; k-NN prediction correctness.
- Integration: updated weights influence Layer 4 OpportunityEngine.
- Learning: weights improve over time (tracked in LearningSystem).

---

## J.5 Layer 4 — OpportunityEngine

**Purpose:** Scan equity universe, identify options opportunities, and detect
arbitrage situations that merit further analysis.

**Owner:** Strategy Engineering Team

**Engineering Requirements:**
- Equity scanner covers all instruments in the configured universe.
- Options scanning requires valid expiry detection. Tuesday expiry fix applies.
- Arbitrage detection is passive: no trades are placed from this layer.
- All identified opportunities are passed as structured objects to Layer 5.

**Testing Requirements:**
- Unit: scanner logic; opportunity scoring.
- Integration: opportunities received by Layer 5 StrategyLab.
- Edge case: empty universe; expired options; holiday handling.

---

## J.6 Layer 5 — StrategyLab

**Purpose:** Apply candidate strategies to identified opportunities, run
backtests, and evolve strategies via MetaStrategyController.

**Owner:** Strategy Engineering Team

**Primary Class:** MetaStrategyController

**Protected Class:** StrategyGeneratorAI

**Engineering Requirements:**
- Strategy evolution uses the configured fitness function.
- min_signal_rr filter must be respected in all evolution variants.
- Strategy generator filters must honour explicit min_rr from JSON.
- Evolved strategies are saved to evolved_strategies/ only after passing filters.
- No strategy is promoted to Layer 10 without passing Layer 15 ResearchLab gates.

**Testing Requirements:**
- Unit: fitness function; filter logic; strategy generation correctness.
- Integration: evolved strategies visible to Layer 6.
- Regression: evolution does not produce worse strategies than prior run.

---

## J.7 Layer 6 — CapitalRiskEngine

**Purpose:** Allocate capital per strategy budget. Determine position sizing
before risk overlays are applied.

**Engineering Requirements:**
- Position sizing uses decimal arithmetic throughout.
- Each strategy has an isolated capital budget.
- Sizing respects MAX_POSITION_PCT from config.py.
- Sizing output is a structured PositionRequest object.

---

## J.8 Layer 7 — RiskControl

**Primary Classes:** RiskManagerAI, PortfolioAllocation, StressTest

**Engineering Requirements:**
- PortfolioAllocation enforces concentration limits.
- StressTest runs at minimum 14 Monte Carlo scenarios.
- RiskManagerAI veto is final within Layer 7.
- All risk decisions are logged with full context for audit.

---

## J.9 Layer 8 — MarketSimulation

**Purpose:** Run Monte Carlo simulations across 14 predefined scenarios to
estimate outcome distributions before execution.

**Engineering Requirements:**
- 14 scenarios are fixed and documented. Changes require Architecture Council.
- Simulation results include confidence intervals.
- Simulations use decimal arithmetic for financial values.
- Simulation outputs are immutable once computed.

---

## J.10 Layer 9 — RiskGuardian

**Purpose:** Final kill switch. Blocks all new trade execution when VIX >= 45.0
or daily portfolio loss >= 2.0%.

**Status:** PROTECTED. No modification without explicit user instruction.

**Kill Switch Thresholds (architectural constants):**
- VIX_KILL_THRESHOLD = 45.0
- DAILY_LOSS_KILL_THRESHOLD = 0.02 (2.0%)

**Engineering Requirements:**
- Kill switch check is performed on every cycle, not cached.
- Kill switch activation is an event emitted to the EventBus.
- Kill switch does not close existing positions.
- Kill switch state is readable by all layers but writable by none except Layer 9.
- No layer in 1–8 can deactivate the kill switch.

**Testing Requirements:**
- Unit: VIX threshold trigger; daily loss threshold trigger.
- Integration: downstream layers receive no trades when kill switch active.
- Safety: kill switch cannot be deactivated by any other layer.
- Performance: kill switch check adds < 1ms to cycle.

---

## J.11 Layer 10 — DebateAndDecision

**Purpose:** 5-agent debate produces a consensus decision score. Trades with
score >= 6.5 proceed to execution.

**Engineering Requirements:**
- All 5 agents must complete before score is computed.
- Score is the average of all 5 agent scores (0–10 scale).
- Threshold is 6.5. Below threshold: trade is rejected with reason recorded.
- All debate outcomes (scores, agent positions, final decision) are logged.
- DecisionEngine emits TRADE_APPROVED or TRADE_REJECTED events.

**Testing Requirements:**
- Unit: scoring aggregation; threshold logic.
- Integration: approved trades reach Layer 11; rejected trades are logged.
- Edge case: agent timeout; tie-breaking.

---

## J.12 Layer 11 — ExecutionEngine

**Purpose:** Convert approved trade decisions into broker orders.

**Primary Class:** OrderManager

**Protected Class:** ZerodhaBroker (simulation mode)

**Engineering Requirements:**
- PAPER_TRADING check is explicit and tested.
- Persistent CSV journal at data/paper_trades.csv for all paper trades.
- All executed orders are logged with order ID, timestamp, symbol, quantity, price.
- Duplicate order detection uses the SAME_ZONE pattern (see patterns.md).
- All constants accessed as self.CONSTANT_NAME inside instance methods.

**Testing Requirements:**
- Unit: paper trading mode gate; CSV journal write.
- Integration: order confirmation reaches Layer 12 TradeMonitoring.
- Safety: no live broker call in paper trading mode.

---

## J.13 Layer 12 — TradeMonitoring

**Primary Classes:** TradeMonitor, StrategyHealthMonitor

**Engineering Requirements:**
- All open positions are monitored at minimum once per scan interval.
- StrategyHealthMonitor disables strategies with win rate below configured threshold.
- Health metrics are emitted to EventBus for Layer 13.

---

## J.14 Layer 13 — LearningSystem

**Primary Classes:** LearningEngine, StrategyPerformanceTracker

**Critical Singleton:** get_performance_tracker()

**Engineering Requirements:**
- Win rate and P&L per strategy are updated after each completed trade.
- Strategies auto-disabled when win rate falls below threshold.
- EOD learning: recovers CSV-closed trades from today to handle post-restart zero-count.
- Learning cycle runs post-market, not during trading hours.
- All learning state is persisted. Learning is not restarted on container restart.

---

## J.15 Layer 14 — PerformanceAnalytics

**Primary Classes:** DrawdownAnalyzer, WalkForwardTester

**Engineering Requirements:**
- DrawdownAnalyzer computes peak-to-trough using decimal arithmetic.
- WalkForwardTester uses OOS windows configured in config.py.
- Analytics results feed into Layer 15 ResearchLab promotion decisions.
- All analytics runs produce persistent records in the data/ directory.

---

## J.16 Layer 15 — ResearchLab

**Purpose:** Strategy promotion gating with three hard requirements:
WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%.

**Engineering Requirements:**
- All three gates must pass simultaneously. Partial passes do not promote.
- Promotion decisions are logged with full evidence.
- Strategies rejected are archived with rejection reason and evidence.
- Promotion triggers the 6-stage ValidationEngine pipeline in Layer 16.

---

## J.17 Layer 16 — ValidationEngine

**Status:** PROTECTED. No modification without explicit user instruction.

**Six-Stage Pipeline:**
1. Backtest — in-sample performance validation
2. Walk-Forward Testing — OOS robustness
3. Cross-Market — validation across different market regimes
4. Monte Carlo — probabilistic outcome simulation
5. Sensitivity — parameter stability across small perturbations
6. Regime — validation across all 6 regime classifications

**Engineering Requirements:**
- All 6 stages must pass for promotion. No stage can be skipped.
- Stage results are recorded with full evidence.
- Validation runs are reproducible: same input produces same output.
- Failed strategies are archived with per-stage failure evidence.

---

## J.18 Layer 17 — ControlTower

**Purpose:** SQLite telemetry, Streamlit dashboard, EventBus coordination,
and system-wide observability.

**Engineering Requirements:**
- SQLite telemetry is append-only. No records are deleted in production.
- Streamlit dashboard reflects system state with <= 5-second lag.
- EventBus is the only permitted mechanism for layer-to-layer events.
- SystemMonitor.time_layer() wraps all timed layer executions.
- All 17 layers have monitoring coverage via SystemMonitor.

**Critical Interface:**
`
SystemMonitor.time_layer(layer_name: str) -> contextmanager
`

**Testing Requirements:**
- Unit: telemetry write; event routing.
- Integration: all 17 layers appear in monitoring output.
- Performance: ControlTower overhead < 5ms per cycle.

---

*End of Supplement J*

---

# SUPPLEMENT K — ENGINEERING STANDARDS CHANGE LOG

## K.1 Change Log Purpose

This supplement maintains a detailed change log for the Engineering Development
Standards document. Each change entry records what changed, why it changed,
and what evidence supported the change.

---

## K.2 Change Entry Format

`
CHANGE ENTRY
------------
Date: {date}
Version: {version}
Type: CLARIFICATION | ADDITION | CORRECTION | STRUCTURAL
Section: {section reference}
Change Description: {what changed}
Rationale: {why this change was made}
Evidence: {supporting evidence or reference}
Author: {author or council}
Council Vote: UNANIMOUS | MAJORITY | N/A
`

---

## K.3 Initial Version Change Log

`
CHANGE ENTRY
Date: 2024-01-01
Version: 0.1.0
Type: ADDITION
Section: All
Change Description: Document created with Engineering Philosophy (Part I)
  and Standards Taxonomy (Part II).
Rationale: IIOS required a foundational engineering standards document to
  govern all future development activity.
Evidence: Architecture Council decision EDR-2024-001.
Author: Architecture Council
Council Vote: UNANIMOUS

CHANGE ENTRY
Date: 2024-01-15
Version: 0.2.0
Type: ADDITION
Section: Part IX
Change Description: Engineering Constitution first draft with 130 rules.
Rationale: Engineering philosophy required codification into binding rules.
Evidence: Review of existing codebase conventions and industry standards.
Author: Architecture Council
Council Vote: UNANIMOUS

CHANGE ENTRY
Date: 2024-02-01
Version: 0.3.0
Type: ADDITION
Section: Supplements A-F
Change Description: Standards catalog, naming reference, review templates,
  certification templates, architecture decision records, and anti-patterns.
Rationale: Practical reference material needed to support daily engineering work.
Evidence: Engineering team feedback on pain points.
Author: Engineering Leads
Council Vote: N/A (additive supplement)

CHANGE ENTRY
Date: 2024-02-15
Version: 0.4.0
Type: ADDITION
Section: Supplements G-I
Change Description: Operational runbook, developer handbook, glossary.
Rationale: Operational and onboarding documentation needed.
Evidence: Operational incidents and new engineer onboarding feedback.
Author: Engineering Leads
Council Vote: N/A (additive supplement)

CHANGE ENTRY
Date: 2024-03-01
Version: 0.5.0
Type: ADDITION
Section: Part VIII
Change Description: Governance Framework with 11 governance domains.
Rationale: Governance processes needed formal documentation to be enforceable.
Evidence: Architecture Council planning session.
Author: Architecture Council
Council Vote: UNANIMOUS

CHANGE ENTRY
Date: 2024-03-15
Version: 1.0.0
Type: STRUCTURAL
Section: All
Change Description: Full document review, correction of all cross-references,
  activation of document status.
Rationale: Document ready for formal activation.
Evidence: Architecture Council final review meeting.
Author: Architecture Council
Council Vote: UNANIMOUS
`

---

## K.4 Scheduled Review Dates

| Review Type | Scheduled Date | Owner |
|-------------|---------------|-------|
| Quarterly partial review | 2024-06-15 | Engineering Leads |
| Annual full review | 2025-03-15 | Architecture Council |
| Regulatory alignment check | 2024-12-01 | Compliance Team |
| Security standards refresh | 2024-09-15 | Security Team |

---

*End of Supplement K*
