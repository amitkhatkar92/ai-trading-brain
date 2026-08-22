# REPOSITORY ENGINEERING SPECIFICATION
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-REPO-ENG-001
**Version:** 1.0.0
**Status:** AUTHORITATIVE
**Classification:** Engineering Foundation
**Issued:** 2026-07-04
**Maintained By:** Architecture Council

---

> **SCOPE STATEMENT**
>
> This document defines HOW the source code repository for the Investment
> Intelligence Operating System will be engineered. It is not application
> architecture. It is not software implementation. It is not a deployment guide.
> It is the engineering constitution of the repository itself: the standards,
> structures, naming conventions, dependency rules, and governance mechanisms
> that every present and future contributor must follow.
>
> This specification is designed to keep the repository maintainable for 20 or
> more years, across hundreds of modules, thousands of Python files, dozens of
> AI agents, and multiple deployment models including monolithic, microservice,
> and distributed configurations.

---

## TABLE OF CONTENTS

- [Part I — Repository Engineering Philosophy](#part-i)
- [Part II — Repository Structure](#part-ii)
- [Part III — Package Organization](#part-iii)
- [Part IV — Engineering Standards](#part-iv)
- [Part V — Dependency Rules](#part-v)
- [Part VI — Documentation Standards](#part-vi)
- [Part VII — Repository Governance](#part-vii)
- [Part VIII — Repository Constitution](#part-viii)
- [Part IX — Repository Readiness Checklist](#part-ix)
- [Supplement A — Folder Catalog](#supplement-a)
- [Supplement B — Naming Catalog](#supplement-b)
- [Supplement C — Dependency Catalog](#supplement-c)
- [Supplement D — Engineering Anti-Patterns](#supplement-d)
- [Supplement E — Repository Glossary](#supplement-e)

---

## PART I — REPOSITORY ENGINEERING PHILOSOPHY

### 1.1 Why Repository Engineering Matters

A repository is not merely a place to store source files. For a system as complex as
the Investment Intelligence Operating System — with 17 processing layers, 62 agents,
18 engines, and a planned operational life of 20+ years — the repository is itself a
primary engineering artifact. The quality of the repository structure directly determines:

**Discoverability.** A new contributor must be able to navigate to any component
within two minutes of opening the repository for the first time. Poor structure forces
time-consuming exploration that compounds across the lifetime of the project.

**Isolation.** Engines must be independently evolvable. A change to the Risk Engine
must not require any change to the Prediction Engine. Repository structure enforces
this isolation architecturally, before code quality does.

**Dependency safety.** In a system with hundreds of modules, implicit or undocumented
dependencies are guaranteed to create circular imports, unexpected coupling, and
deployment failures. Repository structure makes dependency direction explicit and
enforceable.

**Evolutionary capacity.** The system will evolve from a single-process monolith to
a potential multi-service distributed deployment. Repository structure must accommodate
this evolution without necessitating reorganization. The structure defined in this
document is designed to be valid across all anticipated deployment models.

**Maintenance efficiency.** Over a 20-year horizon, the dominant cost of a software
system is not creation — it is maintenance. Repository structure that is easy to
navigate, clearly bounded, and consistently named reduces maintenance cost dramatically
compared to repository structure that has accreted organically.

**Onboarding velocity.** A well-engineered repository is self-documenting through
its structure. An engineer who has never seen IIOS before should be able to identify
the Risk Engine's source files, its tests, its documentation, and its configuration
without asking anyone.

The repository engineering specification defined in this document is therefore not
optional. It is not a style guide. It is the engineering foundation upon which the
operational longevity of IIOS depends.

---

### 1.2 Core Definitions

The following terms have precise meanings in the context of this specification.
They are not interchangeable.

#### 1.2.1 Repository

A **Repository** is the root of version-controlled source code for one or more
deployable units. IIOS occupies a single repository. The repository contains all
source code, all documentation, all configuration, all tests, and all deployment
artifacts for the entire IIOS system.

The repository is the unit of version control. It has a single root. It has a single
history. It has a single set of access controls.

*What a Repository is NOT:* A repository is not a deployment unit. A repository is
not a runnable artifact. A repository is not a single Python package.

---

#### 1.2.2 Project

A **Project** is a logical grouping of work within a repository, typically corresponding
to a bounded problem domain. IIOS as a whole is a project. Within it, subsystems such
as the Knowledge System or the Risk System may be treated as sub-projects with their
own internal coherence requirements.

Projects are tracked by humans. They are managed with milestones, issues, and goals.
They do not have direct representation in the file system.

*What a Project is NOT:* A project is not a folder. A project is not a Python package.
A project is not a deployment unit.

---

#### 1.2.3 Package

A **Package** is a directory containing Python source files that can be imported as
a unit. In IIOS, every engine, every core subsystem, and every shared library is a
package. Packages have explicit boundaries defined by their __init__.py file.

A package exports a **public interface**: the set of names importable by external
packages. Everything else within the package is private.

*What a Package is NOT:* A package is not the same as a folder. A folder that does
not contain source files is not a package. A package is not the same as a module.

---

#### 1.2.4 Module

A **Module** is a single Python source file (.py). It is the atomic unit of source
organization within a package. A module has a single, clear responsibility. Module
names are lowercase with underscores.

Modules within a package may be private (imported only within the package) or public
(exported through the package's public interface).

*What a Module is NOT:* A module is not a class. A module is not a service. Multiple
related classes may appear in one module. A very large class should not be split across
modules.

---

#### 1.2.5 Engine

An **Engine** is a self-contained processing unit in IIOS that implements one or more
specific intelligence or operational functions. There are 18 engines in IIOS, organized
across 7 strata. Each engine is represented as a top-level package within the engines/
directory of the repository.

An engine:
- Has a well-defined input interface.
- Has a well-defined output interface.
- Has complete internal state management.
- Has no runtime dependency on the internal details of any other engine.
- Is independently testable.
- Is independently deployable in a future microservices configuration.

*What an Engine is NOT:* An engine is not a utility library. An engine is not a shared
service. An engine is not a configuration file.

---

#### 1.2.6 Component

A **Component** is a logical sub-unit within an engine. The Risk Engine, for example,
contains multiple components: the Kill Switch Component, the Budget Component, and the
Portfolio Risk Component. Each component is a separate Python module within the engine
package.

Components are internal to their engine. No external package may import a component
directly. External packages may only import from the engine's public interface.

*What a Component is NOT:* A component is not an independent engine. A component cannot
be deployed independently. A component is not a microservice.

---

#### 1.2.7 Library

A **Library** is a collection of reusable functions, classes, and utilities that serve
multiple engines or subsystems. Libraries live in the shared/ directory and have no
knowledge of specific engines. Libraries are the lowest-level reusable units in IIOS.

Libraries impose no business logic. They provide mechanisms, not policies.

*What a Library is NOT:* A library is not an engine. A library that implements
investment decision logic is not a library — it is a component or an engine.

---

#### 1.2.8 Framework

A **Framework** is a structural scaffolding that engines build upon. The IIOS Base
Engine Framework defines the lifecycle protocol that all engines implement. It is
the template that makes engines interchangeable from the Orchestrator's perspective.

A framework enforces conventions through structure. Unlike a library (which you call),
a framework calls your code at defined lifecycle points.

*What a Framework is NOT:* A framework is not a library. A framework is not
interchangeable with the libraries that implement its lifecycle points.

---

#### 1.2.9 Workspace

A **Workspace** is the development environment in which the repository is opened.
In IIOS, the workspace is the local checkout of the repository plus the active virtual
environment. Workspace configuration (.vscode/, .env) is local and is never
committed to version control.

*What a Workspace is NOT:* A workspace is not a repository. Multiple developers may
have different workspace configurations against the same repository.

---

### 1.3 Long-Term Maintainability

Long-term maintainability — the ability to modify, extend, and operate the system
efficiently for 20+ years — rests on six engineering properties:

**1.3.1 Consistency:** Every developer working in the repository experiences the
same conventions. File names follow the same pattern. Documentation is in the same
place. Tests are structured the same way. Consistency reduces the cognitive load of
every future modification.

**1.3.2 Explicitness:** Dependencies, ownership, and intent are made explicit in the
repository structure, not documented separately or assumed. A developer reading a
directory knows what it does, what it depends on, and who is responsible for it.

**1.3.3 Isolation:** Changes to one engine do not cascade to others. The isolation
is structural (packages with defined public interfaces) and conventional (ownership
rules, review gates).

**1.3.4 Reversibility:** Repository decisions that are wrong can be corrected. The
most maintainable repositories are those where no single early decision permanently
constrains future evolution.

**1.3.5 Proportionality:** Repository structure grows proportionally with system
complexity. There is no over-engineering of structure for features that do not yet
exist, but the structure is defined to accommodate future growth without reorganization.

**1.3.6 Self-documentation:** The repository explains itself through structure,
naming, and embedded documentation. A developer should never need to ask "where does
this go?" — the answer should be evident from existing structure.

---

### 1.4 Scalability Principles

The IIOS repository is designed to scale across three dimensions:

**Horizontal scale (breadth):** The number of engines, agents, and components will
grow. The engines/ directory is designed to accommodate hundreds of engine packages
without reorganization. Engine packages are siblings, not nested.

**Vertical scale (depth):** Each engine will grow in internal complexity. The component
model within each engine accommodates deep internal complexity without exposing it
externally.

**Temporal scale (time):** The system will operate for 20+ years. Decisions made today
must remain valid — or gracefully supersedable — for that full period. This is why
versioning, deprecation, and archive policies are first-class concerns in this document.

---

*End of Part I*

---

## PART II — REPOSITORY STRUCTURE

### 2.1 Root Structure

The root of the IIOS repository contains only the following:

`
ai_trading_brain/
|
|-- docs/
|-- engines/
|-- core/
|-- domain/
|-- shared/
|-- config/
|-- resources/
|-- tests/
|-- scripts/
|-- deployment/
|-- monitoring/
|-- logs/
|-- tools/
|-- experiments/
|-- archive/
|-- examples/
|-- research/
|-- .github/
|-- .venv/
|-- main.py
|-- config.py
|-- requirements.txt
|-- docker-compose.yml
|-- Dockerfile
|-- README.md
|-- ARCHITECTURE.md
|-- CHANGELOG.md
|-- LICENSE
|-- .gitignore
|-- .env.example
`

The root contains no source Python files except main.py (the single system
entry point) and config.py (the single global configuration module).

No other Python files live at the root. Logic that would otherwise appear at the
root belongs in core/, shared/, or an appropriate engine.

---

### 2.2 Top-Level Directory Definitions

---

#### 2.2.1 docs/

**Purpose:** The canonical home for all non-code documentation. Every document
that describes what IIOS is, how it works, how to operate it, and how to develop
it lives under docs/.

**Allowed contents:**
- Markdown files (.md)
- Architecture diagrams (.svg, .png, .drawio)
- Ontology definitions (.md)
- Engineering specifications
- Operational runbooks
- Migration guides
- Design decision records

**Forbidden contents:**
- Python source files
- Configuration files
- Test files
- Build artifacts
- Personal notes
- Draft documents older than 30 days without a DRAFT: prefix

**Ownership:** Architecture Council

**Internal structure:**
`
docs/
|-- architecture/      # Architecture documents (IIOS-*-ARCH-*)
|-- engineering/       # Engineering specifications (IIOS-*-ENG-*)
|-- ontologies/        # Ontology reference documents
|-- operations/        # Operational runbooks and procedures
|-- decisions/         # Architecture Decision Records
|-- migrations/        # Schema and API migration guides
|-- research/          # Literature summaries (completed research)
|-- glossaries/        # Domain and technical glossaries
`

**Naming conventions:**
- Architecture documents: IIOS-[SUBSYSTEM]-ARCH-[NNN].md
- Engineering documents: IIOS-[SUBSYSTEM]-ENG-[NNN].md
- Runbooks: RB-[TOPIC]-[NNN].md
- Decision records: ADR-[NNN]-[short-slug].md

**Growth strategy:** Documents accumulate over time. No document is ever deleted
from the docs/ tree — obsolete documents are moved to docs/archive/ with a
deprecation notice in their header.

---

#### 2.2.2 engines/

**Purpose:** The primary source directory. All 18 IIOS engine packages live here,
plus the Master Orchestrator and any future engines. This is the intelligence and
operational core of the system.

**Allowed contents:**
- One subdirectory per engine, exactly matching the engine's canonical package name
- Each engine subdirectory is a self-contained Python package

**Forbidden contents:**
- Shared utility code (belongs in shared/)
- Cross-engine import chains (engine A must not import from engine B's internals)
- Test files (tests live in 	ests/engines/)
- Configuration files (belong in config/)
- Generic infrastructure code (belongs in core/)

**Ownership:** Each engine has a designated owner from the Architecture Council.
The Orchestrator is owned by the Architecture Council collectively.

**Internal structure (per engine):**
`
engines/[engine_name]/
|-- __init__.py          # Public interface definition
|-- [engine_name].py     # Main engine class
|-- components/          # Internal sub-components
|   |-- __init__.py
|   |-- [component_a].py
|   |-- [component_b].py
|-- models/              # Engine-local data models and types
|   |-- __init__.py
|-- utils/               # Engine-local utilities (not shared)
|   |-- __init__.py
|-- config/              # Engine-local default configuration
|   |-- defaults.py
|-- README.md            # Engine description and interface docs
`

**Naming conventions:**
- Engine package names: [function]_[engine_type] (e.g., isk_engine, knowledge_engine)
- Main engine module: same name as package (e.g., isk_engine/risk_engine.py)
- Component modules: descriptive nouns (e.g., kill_switch.py, udget_manager.py)

**Growth strategy:** New engines are added as new top-level subdirectories.
Engine packages never nest. Engine packages never merge.

---

#### 2.2.3 core/

**Purpose:** Infrastructure and framework code that all engines depend on. The
Base Engine Framework lives here. Lifecycle protocols, engine registration, health
monitoring infrastructure, and the event bus live here.

**Allowed contents:**
- Engine base classes and lifecycle protocols
- Engine registration framework
- Health check infrastructure (not business logic)
- Event bus implementation
- Message routing infrastructure
- Logging framework
- Tracing and telemetry infrastructure
- Error hierarchy definitions

**Forbidden contents:**
- Business logic of any kind
- Investment decision logic
- Market data processing
- Risk calculation logic
- Strategy logic
- Anything domain-specific

**Ownership:** Architecture Council

**Internal structure:**
`
core/
|-- engine/              # Base engine framework
|   |-- base_engine.py
|   |-- lifecycle.py
|   |-- registry.py
|-- events/              # Event bus infrastructure
|   |-- bus.py
|   |-- event.py
|-- health/              # Health check infrastructure
|   |-- health_check.py
|   |-- ohs.py
|-- logging/             # Logging infrastructure
|   |-- logger.py
|   |-- formatters.py
|-- errors/              # Error hierarchy
|   |-- base_errors.py
|-- messaging/           # Inter-engine messaging
|   |-- router.py
|   |-- serializer.py
`

**Why this matters:** core/ is the most change-sensitive directory in the
repository. A breaking change in core/ potentially breaks every engine. Changes
to core/ require Architecture Council review and must be accompanied by a migration
guide. The target is that core/ changes fewer than 10 times per year.

---

#### 2.2.4 domain/

**Purpose:** Domain model definitions — the canonical Python representations of
IIOS's domain entities, value objects, enumerations, and type definitions. These
are pure data definitions with no business logic.

**Allowed contents:**
- Data class definitions for domain entities
- Enumeration types
- Value object definitions
- Type alias definitions
- Constant definitions that are domain-intrinsic (e.g., market hours)
- Validation rules for domain constraints

**Forbidden contents:**
- Business logic
- Database mapping code
- Serialization code (belongs in shared/serialization/)
- Engine-specific subtypes (belong in the engine's models/ directory)

**Ownership:** Architecture Council (changes require review)

**Why separate from engines?** Domain types are shared across all engines. If
domain types lived within an engine, every other engine would have to import from
that engine just to access a common type — creating unwanted coupling. By separating
domain types into their own package, all engines can import types without importing
engine code.

---

#### 2.2.5 shared/

**Purpose:** Shared library code — utilities, helpers, and cross-cutting concerns
that multiple engines use. Unlike core/ (which is infrastructure), shared/
contains reusable application-level utilities.

**Allowed contents:**
- Mathematical utilities
- Statistical functions
- Date/time utilities
- String utilities
- File I/O utilities
- Caching utilities
- Retry and resilience utilities
- Serialization utilities
- Validation utilities
- Formatting utilities

**Forbidden contents:**
- Business logic of any kind
- Engine-specific code
- Infrastructure code (belongs in core/)
- Domain model definitions (belong in domain/)
- Configuration loading code (belongs in config/)

**Rule:** Before adding anything to shared/, verify it is used by at least two
engines. Single-engine utilities belong in that engine's utils/ directory, not in
shared/.

---

#### 2.2.6 config/

**Purpose:** All configuration definitions, configuration loading logic, and
environment-specific configuration templates.

**Allowed contents:**
- Configuration data classes
- Configuration loading and validation logic
- Environment-specific configuration files (.yaml, .json, .toml)
- Configuration template files
- .env.example files
- Default configuration values

**Forbidden contents:**
- Business logic
- Configuration secrets (secrets are in environment variables or a vault, never committed)
- Per-engine configuration defaults (those live in the engine's own config/defaults.py)

**Naming conventions:**
- Configuration modules: [subsystem]_config.py
- Configuration files: [environment].yaml (e.g., production.yaml, paper.yaml)
- Template files: [name].example.yaml

---

#### 2.2.7 resources/

**Purpose:** Non-code static assets used by the system at runtime.

**Allowed contents:**
- Static data files (market calendars, instrument lists, symbol maps)
- ML model files (serialized models, weights)
- Prompt templates
- Report templates
- Dashboard templates
- Icon and image assets (for Streamlit dashboard)

**Forbidden contents:**
- Source code
- Configuration files (belong in config/)
- Generated data (belongs in data/ at runtime)
- Test fixtures (belong in 	ests/fixtures/)

---

#### 2.2.8 tests/

**Purpose:** The canonical home for all test code. Tests mirror the structure of
the source tree.

**Allowed contents:**
- Test modules (files named 	est_*.py or *_test.py)
- Test fixtures (ixtures/ subdirectory)
- Test utilities (utils/ subdirectory)
- Test configuration (conftest.py files)
- Integration test suites
- Performance benchmark scripts

**Forbidden contents:**
- Business logic
- Reusable application code (if test code is reusable it belongs in shared/)
- Generated test output (belongs in data/ or a .gitignore-d temp directory)

**Internal structure:**
`
tests/
|-- unit/
|   |-- engines/         # Unit tests mirroring engines/
|   |-- core/            # Unit tests for core/
|   |-- shared/          # Unit tests for shared/
|   |-- domain/          # Unit tests for domain/
|-- integration/         # Integration tests (cross-engine)
|-- system/              # Full-system end-to-end tests
|-- performance/         # Performance benchmarks
|-- fixtures/            # Shared test fixtures
|-- utils/               # Shared test utilities
|-- conftest.py          # Root pytest configuration
`

**Naming conventions:**
- Test file name mirrors the source file: isk_engine.py → 	est_risk_engine.py
- Test class: TestRiskEngine
- Test method: 	est_[thing_being_tested]_[condition]_[expected_outcome]

---

*End of Part II Section 2.2 (first half)*

#### 2.2.9 scripts/

**Purpose:** Operational and development scripts that support the system but are
not part of the deployed application. These are tools for humans, not for the
running system.

**Allowed contents:**
- Database migration scripts
- Data seeding scripts
- System setup scripts
- Development environment setup scripts
- CI/CD pipeline scripts
- Deployment automation scripts
- Health check scripts
- Backup and restore scripts

**Forbidden contents:**
- Application business logic
- Code that is imported by the application (if it is imported, it belongs elsewhere)
- Hardcoded credentials or secrets

**Naming conventions:**
- Script files: [verb]_[noun].py or [verb]_[noun].sh
- Scripts that affect production: must be prefixed with PROD_ to signal elevated risk
- Scripts that must be run once: suffixed with _once.py

---

#### 2.2.10 deployment/

**Purpose:** All deployment artifacts and deployment configuration for all
deployment models.

**Allowed contents:**
- Dockerfile and docker-compose files
- Kubernetes manifests
- Helm charts
- CI/CD pipeline definitions (GitHub Actions, etc.)
- Infrastructure as Code templates
- Deployment environment configuration templates
- Health check endpoint definitions

**Forbidden contents:**
- Application source code
- Secrets (use environment variables or secret management)
- Large binary artifacts (use an artifact registry)

**Internal structure:**
`
deployment/
|-- docker/            # Docker and compose files
|-- kubernetes/        # K8s manifests (future)
|-- helm/              # Helm charts (future)
|-- ci/                # CI/CD pipeline definitions
|-- scripts/           # Deployment scripts
|-- environments/      # Per-environment configuration
`

---

#### 2.2.11 monitoring/

**Purpose:** All monitoring, observability, and alerting definitions and configurations.

**Allowed contents:**
- Prometheus scrape configurations
- Grafana dashboard definitions (JSON)
- Alert rule definitions
- Log aggregation configurations
- Distributed tracing configurations
- SLO (Service Level Objective) definitions
- On-call runbooks

**Forbidden contents:**
- Application monitoring logic (belongs in core/health/ or engines/monitoring_engine/)
- Application source code

---

#### 2.2.12 logs/

**Purpose:** The runtime log output directory. This directory is created at runtime
and is not committed to version control (excluded via .gitignore).

**Contents (runtime-only):**
- Application log files (rotated daily by default)
- Audit log files
- Error log files
- Performance trace log files

**Naming convention for log files:**
[system].[YYYY-MM-DD].[type].log
Example: iios.2026-07-04.application.log

**Retention policy:** Log files older than 90 days are automatically archived.
Log archives older than 3 years are deleted by scheduled script.

---

#### 2.2.13 tools/

**Purpose:** Development tools, code generators, and analysis utilities that assist
in building and maintaining IIOS.

**Allowed contents:**
- Code generation scripts
- Architecture diagram generators
- Dependency graph analyzers
- Code quality analysis scripts
- Documentation generators
- Repository health check tools

**Forbidden contents:**
- Application code
- Deployment scripts (belong in deployment/scripts/)
- Operational scripts (belong in scripts/)

---

#### 2.2.14 experiments/

**Purpose:** A sandbox area for exploratory work that is not yet ready for
integration into the main system. Experiments are time-boxed and governed.

**Allowed contents:**
- Experimental Python notebooks
- Prototype implementations
- Research scripts
- Model evaluation experiments
- Strategy research experiments

**Rules:**
- Every experiment must have an experiment.md file documenting its hypothesis,
  owner, start date, and planned end date.
- An experiment without an experiment.md is deleted at the next repository
  maintenance cycle.
- Experiments are not imported by application code.
- Experiments older than 90 days without an extension are archived automatically.

**Internal structure:**
`
experiments/
|-- [YYYY-MM]/           # Year-month grouping
|   |-- [experiment-slug]/
|   |   |-- experiment.md
|   |   |-- [experiment files]
`

---

#### 2.2.15 archive/

**Purpose:** Preserved but inactive code, documents, and configurations. Archiving
is reversible. Deletion is permanent. When in doubt, archive, do not delete.

**Contents:**
- Superseded implementations
- Deprecated engines (complete packages)
- Outdated documentation (documents with a successor)
- Deprecated strategies
- Obsolete configuration files

**Rules:**
- Archived content is never imported by active application code.
- Archived content retains its original structure.
- A ARCHIVED.md file is placed in each archived item's directory describing
  why it was archived, when, and what replaced it.

---

#### 2.2.16 examples/

**Purpose:** Runnable, standalone examples that demonstrate how to use IIOS
components, configure engines, or integrate with the system.

**Allowed contents:**
- Self-contained example scripts
- Example configuration files
- Example integration code

**Rules:**
- Examples must work as-is with no modifications.
- Examples must be validated as part of CI (if they import application code).
- Examples are never imported by application code.

---

#### 2.2.17 research/

**Purpose:** Academic papers, market research, quantitative analysis reports,
and literature reviews that inform IIOS development but are not documentation.

**Allowed contents:**
- PDF papers (< 50MB each)
- Research summaries (Markdown)
- Quantitative analysis notebooks
- Backtesting research reports

**Forbidden contents:**
- Application source code
- Deployment artifacts
- Operational data

---

#### 2.2.18 .github/

**Purpose:** GitHub-specific configuration including Actions workflows, issue
templates, PR templates, and Copilot customization.

**Allowed contents:**
- GitHub Actions workflow files (.github/workflows/)
- Issue templates (.github/ISSUE_TEMPLATE/)
- PR templates (.github/PULL_REQUEST_TEMPLATE.md)
- Copilot instructions (.github/copilot-instructions.md)
- Dependabot configuration (.github/dependabot.yml)
- Skills directory (.github/skills/)
- CODEOWNERS file (.github/CODEOWNERS)

---

### 2.3 Root-Level Files

The following files and only these files exist at the repository root:

| File | Purpose |
|------|---------|
| main.py | Single system entry point |
| config.py | Global configuration module |
| equirements.txt | Python dependency declarations |
| equirements-dev.txt | Development-only Python dependencies |
| docker-compose.yml | Local development and production compose |
| Dockerfile | Container build definition |
| README.md | Project overview and quick-start guide |
| ARCHITECTURE.md | Architecture overview (links to docs/) |
| CHANGELOG.md | Version history |
| LICENSE | Software license |
| .gitignore | VCS exclusion patterns |
| .env.example | Template for required environment variables |
| pyproject.toml | Python project metadata and tooling config |
| pytest.ini or setup.cfg | Test runner configuration |
| .pre-commit-config.yaml | Pre-commit hook definitions |

No other files belong at the root.

---

*End of Part II*

---

## PART III — PACKAGE ORGANIZATION

### 3.1 Package Boundary Principles

Package boundaries define the units of encapsulation in the IIOS codebase. The
following principles govern all package boundary decisions.

**Principle 1 — Cohesion.** A package contains things that change together.
If two modules frequently change for the same reasons, they belong in the same package.
If two modules change for different reasons, they should be in different packages.

**Principle 2 — Stability.** Packages that other packages depend on must be more
stable than the packages that depend on them. The dependency goes from volatile to
stable. engines/ packages are relatively volatile. core/ and domain/ are stable.

**Principle 3 — Acyclicity.** The dependency graph between packages must be a
directed acyclic graph (DAG). No package may directly or transitively depend on
itself. Circular dependencies are forbidden without exception.

**Principle 4 — Minimality.** A package's public interface contains the minimum
set of names necessary for its clients. Everything else is internal. This is enforced
by the __init__.py that each package exposes.

---

### 3.2 Dependency Direction

The allowed dependency direction is strictly one-way:

`
engines/
  |
  v
domain/
  |
  v
shared/
  |
  v
core/
`

**The rules:**
- core/ packages may not import from any other application package.
- shared/ packages may import from core/ and domain/ only.
- domain/ packages may import from core/ only (and only its type definitions).
- engines/ packages may import from domain/, shared/, and core/.
- engines/ packages may NOT import from each other's internals.
- Engine-to-engine communication goes through the core/events/ event bus.

**Why this matters:** In a system with 18+ engines and hundreds of shared utilities,
uncontrolled cross-package imports create dependency webs that make isolated testing
impossible, deployment sequencing ambiguous, and microservice extraction prohibitively
complex.

---

### 3.3 Import Rules

**Rule IMPORT-01:** Every module's imports are organized in four blocks, separated
by blank lines:
1. Standard library imports
2. Third-party package imports
3. core/ and shared/ imports
4. Local (same-package) imports

**Rule IMPORT-02:** No wildcard imports (rom module import *) anywhere in the
codebase. Every imported name must be explicit.

**Rule IMPORT-03:** No relative imports that traverse up more than one package level.
Cross-package imports must use full absolute paths.

**Rule IMPORT-04:** Circular imports are forbidden. The CI pipeline validates the
dependency graph on every pull request.

**Rule IMPORT-05:** An engine module must never import from another engine's module
directly. Engine interaction uses the event bus or well-defined interfaces.

**Rule IMPORT-06:** __init__.py defines and documents the public interface.
Anything not explicitly imported in __init__.py is private.

---

### 3.4 Visibility Rules

**Public:** A name is public if it appears in the package's __init__.py. Public
names may be used by any dependent package. Changing a public name requires a
deprecation cycle (see Part VII).

**Protected:** A name is protected if it begins with a single underscore (_name).
Protected names may be used within the same package but not by external packages.

**Private:** A name is private if it begins with double underscore (__name).
Private names are module-internal.

**Internal:** A module is internal if it lives under a components/ or internal/
subdirectory within an engine package. Internal modules are never part of the public
interface regardless of how they name their symbols.

---

### 3.5 Public vs. Private Packages

**Public packages** are packages that appear in __init__.py and are intended for
use by multiple consumers. Every engine's top-level package is public. core/,
shared/, and domain/ are public.

**Private packages** are packages that exist within an engine's directory tree and
serve only that engine. The components/ and utils/ subdirectories within an engine
are private packages. Nothing outside the engine may import from them.

This two-level visibility (engine-level public / internal private) is the mechanism
by which engines can maintain complex internal structure without leaking it.

---

### 3.6 Shared Package Policy

**What qualifies for shared/:**
The utility must be used by at least 2 different engine packages. It must contain
no business logic. It must be testable in complete isolation from any engine.

**What does not qualify:**
If a utility is specific to one domain concept (e.g., option chain parsing), it
does not belong in shared/ even if only one engine uses it. It belongs in
that engine's utils/ directory.

If a utility could reasonably be extracted into an independent Python package on
PyPI, it is a candidate for shared/.

**Change governance for shared/:**
Changes to shared/ utilities that would break callers require a deprecation cycle.
New utilities in shared/ require review to confirm they don't duplicate existing
utilities.

---

### 3.7 Engine Isolation Model

Each engine is an island from an import perspective. The only ways to interact
with a running engine are:

1. Through its public Python interface (for in-process orchestration).
2. Through the event bus (for decoupled notification).
3. Through its REST or gRPC interface (in future microservices deployment).

An engine's internal structure may change completely in a future release, as long as
its public interface is preserved. This is the foundation of independent engine evolution.

---

*End of Part III*

---

## PART IV — ENGINEERING STANDARDS

### 4.1 Folder Naming Standards

**Rule FOLD-01:** All folder names are lowercase_with_underscores. Never use hyphens,
camelCase, PascalCase, or spaces in folder names.

**Rule FOLD-02:** Folder names are descriptive nouns or noun phrases. Verbs in folder
names indicate a process, not a structure — avoid them.

**Rule FOLD-03:** Engine folder names follow the pattern [function]_[engine_type].
Examples: isk_engine/, knowledge_engine/, execution_engine/.

**Rule FOLD-04:** Component folder names within an engine use descriptive nouns.
Examples: components/, models/, utils/.

**Rule FOLD-05:** Test folders mirror the source structure. If source is at
engines/risk_engine/, its unit tests are at 	ests/unit/engines/risk_engine/.

**Rule FOLD-06:** Folders should not contain more than 30 items (files + subdirectories)
before a subdirectory grouping strategy is applied.

**Rule FOLD-07:** Reserved folder names that must not be used for other purposes:
__pycache__/, .git/, .venv/, data/, dist/, uild/.

---

### 4.2 File Naming Standards

**Rule FILE-01:** All Python source file names are lowercase_with_underscores.py.
No exceptions.

**Rule FILE-02:** Test file names are 	est_[module_name].py. Mirror the module
being tested.

**Rule FILE-03:** Module names are singular nouns where possible: engine.py, not
engines.py. Collections are named for the type they contain: event.py, not
events.py.

**Rule FILE-04:** Configuration module names follow: [subsystem]_config.py.

**Rule FILE-05:** No two files in the repository have the same name within the same
directory tree branch. Ambiguous duplicate names are a navigation hazard.

**Rule FILE-06:** __init__.py is the only permitted use of a double-underscore
file prefix. Other dunder file patterns (__main__.py, __version__.py) are
permitted where Python convention requires them.

**Rule FILE-07:** File names do not contain version numbers, dates, or revision
indicators. Version history is in version control, not in file names.
Exception: migration scripts (which are inherently versioned by definition).

**Rule FILE-08:** Temporary files (.tmp, .bak, *.pyc) must appear in .gitignore
and must never be committed to the repository.

---

### 4.3 Markdown File Naming Standards

**Rule MD-01:** All Markdown documentation files use UPPER_SNAKE_CASE.md.
Exception: README.md in any directory.

**Rule MD-02:** Document code prefixes are mandatory for formal architecture and
engineering documents: IIOS-[DOMAIN]-[TYPE]-[NNN].md.

**Rule MD-03:** Architecture documents: IIOS-[DOMAIN]-ARCH-[NNN].md
Engineering documents: IIOS-[DOMAIN]-ENG-[NNN].md
Operations documents: RB-[TOPIC]-[NNN].md
Decision records: ADR-[NNN]-[short-slug].md

**Rule MD-04:** README.md is mandatory in every top-level directory and in every
engine package. It must contain at minimum: purpose, contents summary, owner,
and dependencies.

**Rule MD-05:** Draft documents are prefixed with DRAFT_. A document without this
prefix is considered finalized and authoritative.

---

### 4.4 Python Naming Standards

These standards apply to all Python modules throughout the repository.

**Classes:** PascalCase. Engine classes are named [Function]Engine where
[Function] is a precise description: RiskEngine, KnowledgeEngine.

**Functions:** lowercase_with_underscores. Verb-first naming: compute_risk_budget(),
etch_market_data(), not isk_budget_compute().

**Methods:** Same as functions. Public methods have no leading underscore.
Protected methods have single leading underscore. Private methods have double
leading underscore.

**Constants:** UPPER_SNAKE_CASE. Constants are module-level or class-level.
Never local to a function.

**Variables:** lowercase_with_underscores. Meaningful names. Single-letter
variable names are permitted only in comprehensions and mathematical contexts.

**Type aliases:** PascalCase when exported; _PascalCase when internal.

**Enumerations:** Class name in PascalCase, members in UPPER_SNAKE_CASE.

**Exceptions:** PascalCase with suffix Error for exception types:
RiskBudgetExceededError, EngineNotReadyError.

**Test classes:** TestClassName — prefix Test followed by the class being tested.

**Test methods:** 	est_[thing]_[condition]_[expectation]. Fully descriptive.

---

### 4.5 JSON File Naming Standards

**Rule JSON-01:** All JSON data files use lowercase_with_underscores.json.

**Rule JSON-02:** JSON configuration files: [environment]_config.json.

**Rule JSON-03:** JSON schema files: [type]_schema.json.

**Rule JSON-04:** JSON export/import files used in migrations:
[YYYY-MM-DD]_[description].json.

**Rule JSON-05:** All JSON files in the repository must be valid JSON (validated
by CI). No trailing commas, no comments, no JSONC.

---

### 4.6 YAML File Naming Standards

**Rule YAML-01:** All YAML files use lowercase names with hyphens:
docker-compose.yml, production-config.yaml.

**Rule YAML-02:** YAML files use the .yaml extension (not .yml) except where
the tool requires .yml (e.g., Docker Compose convention).

**Rule YAML-03:** All YAML files in the repository must be valid YAML (validated
by CI). Indentation must be 2 spaces.

**Rule YAML-04:** Sensitive values in YAML files are always environment variable
references, never literal values.

---

### 4.7 Configuration File Standards

**Rule CFG-01:** No hardcoded values. Every environment-specific value (hostnames,
ports, thresholds, credentials) must be configurable through environment variables
or a configuration file.

**Rule CFG-02:** A .env.example file in the root documents every environment
variable the system uses, with a description of its purpose and default value.
This file is committed to version control. The actual .env file is not.

**Rule CFG-03:** Configuration values have a defined precedence order:
1. Environment variables (highest priority)
2. Environment-specific configuration file
3. Default configuration file
4. Hardcoded defaults in code (lowest priority)

**Rule CFG-04:** Configuration is validated at startup. A missing required
configuration value causes startup to fail with a clear error message, not a
runtime crash.

**Rule CFG-05:** Configuration values are read once at startup and cached.
Dynamic re-reading of configuration files is not permitted without explicit
hot-reload infrastructure.

---

### 4.8 Version Numbering Standards

IIOS uses Semantic Versioning (semver) with the format MAJOR.MINOR.PATCH.

**MAJOR:** Incremented when a public interface changes incompatibly. Engine public
interface changes that break existing callers increment MAJOR.

**MINOR:** Incremented when new functionality is added in a backward-compatible
manner. New engines, new capabilities, and new configuration options increment MINOR.

**PATCH:** Incremented when backward-compatible bug fixes are made.

**Pre-release:** Pre-release versions are labeled -alpha.N, -beta.N, or -rc.N.
Pre-release versions must never be deployed to production.

**Engine versioning:** Individual engines maintain their own version in their
__init__.py. Engine versions are independent of the system version, but the
system version is always >= the highest engine version.

**Document versioning:** Documents use the same semver scheme. Document version
appears in the document's header block.

---

*End of Part IV*

---

## PART V — DEPENDENCY RULES

### 5.1 Allowed Dependencies

**Application-internal dependencies (always allowed within rules):**
- engines/[X] → domain/
- engines/[X] → shared/
- engines/[X] → core/
- shared/ → core/
- domain/ → core/ (type definitions only)
- core/ → standard library only

**Third-party dependencies (allowed, governed):**
All third-party dependencies must be:
1. Listed in equirements.txt with a pinned version.
2. Evaluated for security vulnerability history before adoption.
3. Approved via the dependency adoption process (see Rule DEP-07).
4. Vendored or pinned if they are in the critical path.

---

### 5.2 Forbidden Dependencies

**FORBIDDEN-01:** Engine-to-engine direct imports.
No engine package may import from another engine package's modules or components.
Engine A must not do rom engines.risk_engine.components.kill_switch import ...
Permitted only: importing an engine's public interface via the Orchestrator, or
communicating via the event bus.

**FORBIDDEN-02:** core/ importing from shared/ or engines/.
Core infrastructure must have zero dependency on application-level code.

**FORBIDDEN-03:** domain/ importing from shared/ or engines/.
Domain types must be self-contained.

**FORBIDDEN-04:** shared/ importing from engines/.
Shared utilities must have no knowledge of specific engines.

**FORBIDDEN-05:** Circular imports between any two modules.
If A imports B and B imports A, directly or transitively, this is a circular
dependency and must be resolved immediately.

**FORBIDDEN-06:** Import of test utilities in production code.
Nothing in 	ests/ may be imported by anything outside 	ests/.

**FORBIDDEN-07:** Import of experiment code in production code.
Nothing in experiments/ may be imported by application code.

**FORBIDDEN-08:** Direct file system path construction using hardcoded absolute paths.
All file paths are constructed relative to the repository root or the data directory,
using path utilities from shared/.

---

### 5.3 Circular Dependency Prevention

**Prevention mechanism 1 — Structural:** The directory hierarchy (engines → domain
→ shared → core) encodes the allowed dependency direction. An engineer can see at
a glance whether an import direction is valid.

**Prevention mechanism 2 — CI validation:** The CI pipeline runs a dependency graph
validator (	ools/validate_deps.py) on every pull request. Any import that violates
the dependency rules causes the CI check to fail.

**Prevention mechanism 3 — Interface segregation:** When two packages need to
communicate in both directions (which would create a cycle), the communication is
restructured through a shared event type in domain/ or a callback pattern. Direct
bidirectional imports are never permitted.

**Prevention mechanism 4 — Event bus:** Engine-to-engine communication that would
otherwise require direct imports goes through the core/events/ event bus. Event
types are defined in domain/, not in the engine that produces them.

---

### 5.4 Engine Isolation Guarantees

The engine isolation model provides the following guarantees:

**Guarantee EI-01:** An engine can be replaced by a different implementation
without modifying any other engine. Only the Orchestrator's registration and the
engine's __init__.py interface must be preserved.

**Guarantee EI-02:** An engine can be tested in complete isolation by mocking
the event bus and injecting test domain objects. No real engine is required to test
another engine.

**Guarantee EI-03:** An engine can be extracted into an independent microservice
by wrapping its public interface in an HTTP or gRPC adapter. No inter-engine imports
need to change.

**Guarantee EI-04:** Two engines can evolve simultaneously by different developers
without merge conflicts on shared source files, provided both developers respect
the public interface contracts.

---

### 5.5 Shared Library Policy

**Policy SL-01:** A utility enters shared/ only when two distinct engines require it.
One-engine utilities live in that engine's utils/.

**Policy SL-02:** Once a utility is in shared/, its interface is stable. Changing
it requires the same deprecation cycle as any public interface change.

**Policy SL-03:** shared/ utilities are categorized by domain:
`
shared/
|-- math/          # Mathematical utilities
|-- stats/         # Statistical functions
|-- datetime/      # Date and time utilities
|-- io/            # File and network I/O utilities
|-- cache/         # Caching utilities
|-- retry/         # Retry and resilience utilities
|-- serial/        # Serialization utilities
|-- validation/    # Input validation utilities
|-- formatting/    # Output formatting utilities
|-- collections/   # Collection utilities
`

**Policy SL-04:** shared/ utilities have 100% unit test coverage (enforced by CI).

---

### 5.6 Core Dependency Rules

**Rule CORE-01:** Nothing in core/ may be modified without Architecture Council
sign-off and a migration guide.

**Rule CORE-02:** core/ changes are versioned independently from engine versions
and the system version.

**Rule CORE-03:** core/ is designed for a maximum of 5 changes per year. Frequent
changes to core/ indicate a design problem that must be resolved.

**Rule CORE-04:** Every public interface in core/ is documented with a formal
interface specification including: purpose, parameters, return values, exceptions,
and behavioral contracts.

**Rule CORE-05:** core/ tests run in a completely isolated environment with no
external dependencies.

---

*End of Part V*

---

## PART VI — DOCUMENTATION STANDARDS

### 6.1 README Standards

Every directory that contains substantive content must have a README.md file.
The README is the first-contact document: it tells a reader what the directory
contains and how to navigate it.

**Mandatory README sections:**

**Section 1 — Purpose (2-4 sentences):**
What this directory/package contains. Why it exists.

**Section 2 — Contents:**
A brief enumeration of the key files or subdirectories, each with one sentence
of description.

**Section 3 — Owner:**
The person or team responsible for this content.

**Section 4 — Dependencies:**
What this package/directory depends on, and what depends on it.

**Section 5 — Development guide (for engine packages):**
How to run tests for this engine. How to start the engine in isolation.
Key configuration options.

**README freshness rule:** A README that has not been updated in 12 months
while the package it documents has had 5+ commits is considered stale and triggers
a documentation review ticket.

---

### 6.2 Architecture Document Standards

Architecture documents describe the structure of the system: what exists, how things
connect, and why decisions were made.

**Mandatory sections:**
1. Document header (code, version, status, date, owner)
2. Scope statement
3. Context diagram (system in its environment)
4. Structure description (with diagrams)
5. Component catalogue
6. Dependency description
7. Decision rationale (key decisions and their justification)
8. Change history

**Format requirements:**
- Document code: IIOS-[DOMAIN]-ARCH-[NNN]
- Version: semver in document header
- Status: one of DRAFT / REVIEW / AUTHORITATIVE / SUPERSEDED / ARCHIVED
- Diagrams: ASCII diagrams preferred for text portability; .svg files acceptable
- Cross-references: explicit links to related documents

---

### 6.3 Engineering Document Standards

Engineering documents describe HOW the system is built: standards, processes, and
conventions.

**Mandatory sections:**
1. Document header (code, version, status, date, owner)
2. Scope statement (what this document covers and does not cover)
3. Normative statements (requirements that MUST be followed)
4. Rationale for key decisions
5. Examples of correct and incorrect application
6. Change history

**Format requirements:**
- Document code: IIOS-[DOMAIN]-ENG-[NNN]
- Normative language: MUST, MUST NOT, SHOULD, SHOULD NOT, MAY (RFC 2119 sense)
- Requirement identifiers: RULE-[CATEGORY]-[NNN] for traceability

---

### 6.4 API Documentation Standards

API documentation describes the public interfaces of packages and engines.

**Mandatory per public function/class:**
- Purpose (one sentence)
- Parameters (name, type, description, default if applicable)
- Return value (type and description)
- Exceptions that may be raised
- Usage example
- Thread safety statement

**Location:** API documentation lives adjacent to the code it documents, in
docstrings for Python code. Extracted HTML/Markdown documentation is generated
from docstrings by the CI pipeline.

**Completeness requirement:** All public symbols in core/, shared/, and
domain/ must have API documentation. Engine public interfaces must have API
documentation. Engine internal components are encouraged but not required.

---

### 6.5 Design Decision Standards

Design decisions are documented as Architecture Decision Records (ADRs) in
docs/decisions/. An ADR captures a significant architectural decision along
with its context, options considered, rationale, and consequences.

**Mandatory ADR sections:**
1. Title (concise description of the decision)
2. Status (PROPOSED / ACCEPTED / DEPRECATED / SUPERSEDED)
3. Context (the forces that led to this decision)
4. Decision (what was decided)
5. Options considered (alternatives that were evaluated)
6. Rationale (why this option was chosen)
7. Consequences (positive and negative outcomes)
8. Related decisions (links to related ADRs)

**When to create an ADR:**
- Any decision that affects the public interface of a package or engine.
- Any decision that affects the dependency model.
- Any decision that adds a new third-party dependency.
- Any decision about the repository structure itself.
- Any decision that a future maintainer might question and want to understand.

---

### 6.6 Change Log Standards

IIOS maintains a CHANGELOG.md at the repository root, following the
[Keep a Changelog](https://keepachangelog.com) format.

**Change log structure:**
`
## [Unreleased]

## [X.Y.Z] - YYYY-MM-DD
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
`

**Change log rules:**
- Every pull request that modifies application behaviour adds an entry.
- Entries are human-readable, not git commit messages.
- Internal refactors with no behaviour change do not require changelog entries.
- Breaking changes are marked with a [BREAKING] prefix.

---

### 6.7 Migration Guide Standards

When a breaking change is made to a public interface, a migration guide is
required before the change is merged.

**Migration guide template:**
`
# Migration Guide: [Description of Change]
**Version:** [OLD_VERSION] → [NEW_VERSION]
**Scope:** [Which packages/engines are affected]
**Breaking:** [Yes/No]

## What Changed
[Description of the change]

## Why It Changed
[Rationale]

## What You Must Do
[Step-by-step migration instructions]

## Compatibility Period
[How long the old interface will remain available]
`

---

### 6.8 Operational Runbook Standards

Operational runbooks document procedures for operating the system in production.
Runbooks are in docs/operations/.

**Mandatory runbook sections:**
1. Procedure title and identifier
2. Trigger: when to run this procedure
3. Prerequisites: what must be true before starting
4. Steps: numbered, executable steps
5. Verification: how to confirm the procedure succeeded
6. Rollback: how to undo the procedure if it fails
7. Escalation: who to contact if the procedure cannot be completed

**Runbook rules:**
- Every step is executable by an on-call operator who did not write the procedure.
- Runbooks are tested quarterly by having an operator follow them without guidance.
- Outdated runbooks (untested for > 6 months) are flagged in the documentation index.

---

*End of Part VI*

---

## PART VII — REPOSITORY GOVERNANCE

### 7.1 Ownership Model

Every artifact in the repository has a designated owner. Ownership means:
- The owner reviews all proposed changes.
- The owner is accountable for the quality of what they own.
- The owner answers questions about the artifact.
- The owner maintains documentation for the artifact.

**Ownership tiers:**

| Tier | Artifacts | Owner |
|------|-----------|-------|
| Tier 1 — Repository | Entire repository | Architecture Council |
| Tier 2 — Core | core/, domain/, shared/ | Architecture Council |
| Tier 3 — Engine | Individual engine packages | Designated Engine Owner |
| Tier 4 — Component | Sub-packages within engines | Component Owner (may differ from engine) |
| Tier 5 — Document | Individual documents | Document Author |

Ownership is recorded in the CODEOWNERS file and in each subdirectory's README.md.

---

### 7.2 Review Process

**Changes to Tier 1 and 2 artifacts:** Require review and approval from at least
two Architecture Council members. Changes to core/ require a migration guide.

**Changes to Tier 3 artifacts (engines):** Require review from the designated Engine
Owner plus one Architecture Council member for changes that touch the public interface.
Internal-only changes require review from the Engine Owner.

**Changes to Tier 4 artifacts (components):** Require review from the Component Owner.

**Automated checks that must pass before any merge:**
- Dependency graph validation (no circular imports, no forbidden dependencies)
- Test suite (all unit tests pass)
- Coverage threshold (no regression in test coverage)
- Linting (no style violations)
- Type checking (no type errors in typed modules)
- Documentation freshness check (no README with zero updates in the last 12 months
  for a heavily modified package)

---

### 7.3 Branch Strategy

IIOS uses a simplified trunk-based development model.

**main:** The single long-lived branch. Always deployable. Represents the latest
stable state.

**feature/[ticket-id]-[short-description]:** Short-lived feature branches. Merged
to main via pull request. Deleted after merge.

**fix/[ticket-id]-[short-description]:** Short-lived bug fix branches. Merged to
main via pull request. Deleted after merge.

**hotfix/[version]-[description]:** Emergency fix branches for production issues.
Merged to main and tagged immediately. Deleted after merge.

**release/[version]:** Release preparation branches. Created from main when
preparing a release. Merged back to main with a version tag when released.

**Branch naming rules:**
- All lowercase
- Hyphens between words
- Ticket/issue reference included where applicable
- Maximum 60 characters

**Branch protection for main:**
- No direct pushes
- All changes via pull request
- CI must pass before merge
- At least one approval required

---

### 7.4 Versioning Philosophy

IIOS follows the principle of **intentional versioning**: versions are not
auto-incremented by CI. A human decides when to increment each component of the
version and writes a changelog entry to accompany it.

**When MAJOR increments:**
A public interface has changed incompatibly. Callers must update. A migration
guide has been written. A deprecation period of at least 30 days has been
observed (except for security fixes).

**When MINOR increments:**
New capability has been added. Existing callers are unaffected. New optional
parameters, new engine capabilities, new configuration options.

**When PATCH increments:**
A bug was fixed. Behaviour is now correct rather than incorrect. No interface
changed.

**Version is stamped in:**
- pyproject.toml (system-level version)
- Engine's __init__.py (engine-level version)
- Git tag matching the system version (1.2.3)
- Docker image tag

---

### 7.5 Release Policy

**Release cadence:** No fixed cadence. Releases occur when a meaningful set of
changes has accumulated and has been validated.

**Release checklist (abbreviated; see full checklist in docs/operations/):**
1. All CI checks pass on main.
2. CHANGELOG.md updated for the release version.
3. All documentation updated to reflect changes.
4. Version numbers updated in pyproject.toml and relevant __init__.py files.
5. Release candidate deployed to paper trading environment.
6. Paper trading validation for minimum 3 full trading days.
7. Architecture Council sign-off on release.
8. Docker images built, tagged, and pushed to container registry.
9. Git tag created and pushed.
10. Deployment to production.

---

### 7.6 Deprecation Policy

Deprecation is the process by which a public interface is retired in a backward-
compatible manner. IIOS deprecation policy:

**Step 1 — Announcement:** The deprecation is announced in the CHANGELOG.md and
documented in the module's docstring with a Deprecated since version X.Y.Z. Use
[replacement] instead. notice.

**Step 2 — Runtime warning:** The deprecated code emits a DeprecationWarning at
runtime when called.

**Step 3 — Minimum grace period:** 90 days from announcement to removal, for all
internal deprecations. Longer periods for interfaces that external systems depend on.

**Step 4 — Migration guide:** A migration guide is available for the full duration
of the deprecation period.

**Step 5 — Removal:** At the end of the deprecation period, the code is removed in
a MAJOR version increment. The removal is noted in the CHANGELOG.md.

---

### 7.7 Archive Policy

**What gets archived:**
- Superseded implementations
- Engines that have been replaced
- Documentation that has a successor
- Deprecated strategies that have been retired

**Archive procedure:**
1. Move the artifact to the rchive/ directory, preserving internal structure.
2. Create an ARCHIVED.md file in the artifact's new location.
3. Update any inbound references to point to the replacement.
4. Commit the archival as a standalone commit with the message: rchive: [description].

**Archive retention:**
Archived code is retained indefinitely. It is never deleted. It may be referenced
for historical context or for revival if needed.

---

*End of Part VII*

---
## PART VIII — REPOSITORY CONSTITUTION

The Repository Constitution contains 100 engineering rules governing the IIOS
repository. These rules are classified as:

**HARD (H):** Violation causes immediate CI failure. No exceptions.
**SOFT (S):** Violation triggers a warning and requires documented justification to proceed.
**ADVISORY (A):** Best practice. Encouraged. Not automatically enforced.

---

### Category 1: Naming Rules (RULE-NAME-001 through RULE-NAME-020)

**RULE-NAME-001 [H]:** All Python source file names are lowercase with underscores.
No hyphens, no dots (except .py), no camelCase, no PascalCase in file names.

**RULE-NAME-002 [H]:** All folder names are lowercase with underscores. No exceptions,
including in docs/, scripts/, deployment/, and all other directories.

**RULE-NAME-003 [H]:** All Markdown documentation files (except README.md) use
UPPER_SNAKE_CASE naming.

**RULE-NAME-004 [H]:** Engine package names follow the pattern [function]_engine.
If the function is a compound noun, it is joined with underscores:
knowledge_engine, isk_engine, execution_engine.

**RULE-NAME-005 [H]:** Test files are named 	est_[module_being_tested].py. The
test module name mirrors the source module name.

**RULE-NAME-006 [H]:** No file in the repository has the same name as another file
in the same directory.

**RULE-NAME-007 [S]:** Python class names are PascalCase. Exception: single-letter
type aliases and dataclass field types may use PascalCase single letters.

**RULE-NAME-008 [H]:** Python function and method names are lowercase with underscores.
The first word is a verb: compute_, etch_, alidate_, uild_, create_.

**RULE-NAME-009 [H]:** Python constants are UPPER_SNAKE_CASE. They are defined at
module scope or class scope, never inside functions.

**RULE-NAME-010 [H]:** Python exception classes have the Error suffix:
RiskBudgetExceededError, EngineNotReadyError, InvalidOntologyTypeError.

**RULE-NAME-011 [H]:** Python enumeration classes are PascalCase. Enumeration
members are UPPER_SNAKE_CASE.

**RULE-NAME-012 [S]:** YAML files use the .yaml extension. Files that require
.yml by external tool convention (e.g., GitHub Actions) are exempt.

**RULE-NAME-013 [H]:** JSON files use the .json extension and contain valid JSON.
No JSONC, no trailing commas, no comments.

**RULE-NAME-014 [H]:** Configuration variable names in .env and environment
variable references are UPPER_SNAKE_CASE.

**RULE-NAME-015 [H]:** Architecture Decision Records are named ADR-[NNN]-[slug].md
where NNN is a zero-padded three-digit sequence number.

**RULE-NAME-016 [S]:** A module name should be a singular noun or noun phrase where
practical. event.py rather than events.py. engine.py rather than engines.py.

**RULE-NAME-017 [H]:** README.md is the only permitted variant of readme naming.
Not eadme.md, not Readme.md, not READ-ME.md.

**RULE-NAME-018 [A]:** Names should be complete words, not abbreviations. configuration
not cfg. manager not mgr. Exceptions: universally recognized abbreviations
(e.g., http, pi, url, id).

**RULE-NAME-019 [H]:** No numbers at the beginning of a file, folder, or Python
identifier name. Numbers may appear in the middle or at the end.

**RULE-NAME-020 [S]:** Names that begin with _ are reserved for Python convention
uses (protected/private). Do not use _ prefix for names that are publicly exported.

---

### Category 2: Structure Rules (RULE-STRUCT-001 through RULE-STRUCT-020)

**RULE-STRUCT-001 [H]:** Every engine has exactly one top-level directory under
engines/. Engines are not nested within other engines.

**RULE-STRUCT-002 [H]:** Every engine package has an __init__.py that explicitly
defines its public interface. An engine with an empty __init__.py has no public
interface.

**RULE-STRUCT-003 [H]:** Every top-level directory has a README.md.

**RULE-STRUCT-004 [H]:** Application logic does not live at the repository root.
main.py is the only root-level Python file and it contains only the entry point.

**RULE-STRUCT-005 [H]:** Test files do not live inside source packages.
All tests are under 	ests/. Source packages contain no 	est_*.py files.

**RULE-STRUCT-006 [H]:** __pycache__/ directories are not committed to version
control. They appear in .gitignore.

**RULE-STRUCT-007 [H]:** .env files containing real secrets are not committed
to version control. Only .env.example is committed.

**RULE-STRUCT-008 [S]:** A source package should not contain more than 20 Python
modules. If it does, the package may need to be split into sub-packages.

**RULE-STRUCT-009 [H]:** rchive/ items are never imported by active code. An
import from rchive/ causes an immediate CI failure.

**RULE-STRUCT-010 [H]:** experiments/ items are never imported by application code.
An import from experiments/ causes an immediate CI failure.

**RULE-STRUCT-011 [S]:** Every engine's public interface (its __init__.py) exports
no more than 10 names. Larger interfaces indicate insufficient internal encapsulation.

**RULE-STRUCT-012 [H]:** There is exactly one config.py at the repository root.
Engine-specific configuration defaults live in the engine's own config/defaults.py.

**RULE-STRUCT-013 [A]:** Directory depth should not exceed 5 levels from the repository
root. Deep nesting makes navigation slow and import paths unwieldy.

**RULE-STRUCT-014 [H]:** Generated files (compiled assets, build outputs, coverage
reports) are excluded from version control via .gitignore.

**RULE-STRUCT-015 [S]:** Migration scripts are numbered sequentially and dated:
[YYYY-MM-DD]_[NNN]_[description].py.

**RULE-STRUCT-016 [H]:** The deployment/ directory contains only deployment
artifacts. No application source code lives in deployment/.

**RULE-STRUCT-017 [A]:** Engine component directories use the name components/.
Sub-components within a component use descriptive names, not sub_components/.

**RULE-STRUCT-018 [H]:** Log files do not exist in the repository. All log files are
generated at runtime and excluded by .gitignore.

**RULE-STRUCT-019 [S]:** The examples/ directory contains only self-contained
examples. Each example imports only from public package interfaces.

**RULE-STRUCT-020 [H]:** No binary files larger than 50MB are committed to version
control. Large files use Git LFS or an artifact registry.

---

### Category 3: Isolation Rules (RULE-ISO-001 through RULE-ISO-015)

**RULE-ISO-001 [H]:** No engine package imports from the internal modules of
another engine package. Engine-to-engine imports go through public interfaces or
the event bus.

**RULE-ISO-002 [H]:** No shared/ module imports from any engines/ module.
Shared utilities have no knowledge of specific engines.

**RULE-ISO-003 [H]:** No core/ module imports from shared/, domain/, or
engines/ modules. Core infrastructure is self-contained.

**RULE-ISO-004 [H]:** No domain/ module imports from shared/ or engines/.
Domain types depend only on the standard library and core/ type definitions.

**RULE-ISO-005 [H]:** The Master Orchestrator does not implement business logic.
It reads health signals and routes control events. It does not interpret market data.

**RULE-ISO-006 [H]:** No investment decision logic lives in core/ or shared/.
All investment logic belongs in an engine.

**RULE-ISO-007 [H]:** No configuration loading logic lives in an engine module.
Engines receive their configuration via dependency injection at construction time.

**RULE-ISO-008 [S]:** An engine's internal state is not accessible from outside
the engine except through the engine's public interface methods.

**RULE-ISO-009 [H]:** Test isolation: unit tests for engine A do not instantiate
or import engine B. Engine B is mocked if required.

**RULE-ISO-010 [H]:** No shared mutable global state across engines. Each engine
manages its own state. Shared state goes through the event bus or a defined
state store accessed through shared/.

**RULE-ISO-011 [S]:** No engine has a hardcoded reference to another engine's class
name. Engine discovery is through the registry, not hardcoded references.

**RULE-ISO-012 [H]:** No circular imports anywhere in the codebase. CI validates
the complete import graph on every pull request.

**RULE-ISO-013 [A]:** Engine unit tests mock the event bus. This confirms that the
engine can operate correctly regardless of what other engines exist.

**RULE-ISO-014 [H]:** Secrets (API keys, passwords, tokens) are never stored in
source code, configuration files, or documentation. Secrets are in environment
variables or a secrets manager.

**RULE-ISO-015 [S]:** No engine captures a reference to another engine's instance
at construction time. If engine A needs a service from engine B, it requests it
through the registry or event bus at runtime.

---

### Category 4: Dependency Rules (RULE-DEP-001 through RULE-DEP-015)

**RULE-DEP-001 [H]:** All third-party dependencies are declared in equirements.txt
or equirements-dev.txt with pinned versions (package==X.Y.Z).

**RULE-DEP-002 [H]:** No undeclared imports. A package that is not in equirements.txt
must not be imported in production code.

**RULE-DEP-003 [H]:** Development-only dependencies (testing, linting, type checking)
are in equirements-dev.txt, not equirements.txt.

**RULE-DEP-004 [S]:** Before adopting a new third-party dependency, the dependency is
evaluated for: (1) license compatibility, (2) security vulnerability history,
(3) maintenance activity, (4) alternative availability.

**RULE-DEP-005 [H]:** The dependency graph between packages is a DAG. CI enforces this.

**RULE-DEP-006 [H]:** No new dependency is added to core/ or shared/ without
Architecture Council review.

**RULE-DEP-007 [S]:** The transitive dependency count for the full system should not
exceed 150 packages. At 150, a dependency audit is triggered.

**RULE-DEP-008 [H]:** All pinned versions in equirements.txt are tested together.
No untested version combinations exist in the production dependency set.

**RULE-DEP-009 [S]:** Dependencies pinned to pre-release versions (lpha, eta,
c) are not permitted in production equirements.txt.

**RULE-DEP-010 [H]:** No dependency on internal (private, unreleased) packages that
are not in the same repository. All external dependencies come from public package
indices.

**RULE-DEP-011 [A]:** Prefer packages with more than 3 years of maintenance history
for critical path dependencies.

**RULE-DEP-012 [S]:** When upgrading a dependency, the full test suite passes with
the new version before the upgrade is committed.

**RULE-DEP-013 [H]:** Dependency version ranges (>=X, <Y) are only used in
pyproject.toml for library publishing. Application equirements.txt uses exact
pins (==X.Y.Z).

**RULE-DEP-014 [A]:** If a third-party dependency is used in only one location,
evaluate whether it can be eliminated (the functionality is simple enough to implement
directly, or another already-present dependency provides it).

**RULE-DEP-015 [H]:** All third-party dependencies are reviewed for known CVEs using
an automated scanner in CI. A CVE with a CVSS score >= 7.0 blocks merge until resolved.

---

### Category 5: Documentation Rules (RULE-DOC-001 through RULE-DOC-010)

**RULE-DOC-001 [H]:** Every public function, method, and class in core/, shared/,
and domain/ has a docstring.

**RULE-DOC-002 [S]:** Every public function, method, and class in engine public
interfaces has a docstring.

**RULE-DOC-003 [H]:** Every formal architecture and engineering document has a
document code following the IIOS-[DOMAIN]-[TYPE]-[NNN] convention.

**RULE-DOC-004 [H]:** Every ADR is in docs/decisions/ and follows the ADR template.

**RULE-DOC-005 [S]:** Every engine package has a README.md that documents: purpose,
public interface summary, dependencies, and key configuration options.

**RULE-DOC-006 [H]:** Every public interface change has a changelog entry.

**RULE-DOC-007 [S]:** Runbooks are reviewed and re-tested every 6 months.

**RULE-DOC-008 [H]:** Migration guides exist for all breaking changes before the
breaking change is merged.

**RULE-DOC-009 [A]:** Inline comments explain WHY, not WHAT. The code shows what
happens. The comment explains the non-obvious reason.

**RULE-DOC-010 [S]:** Documents that have been superseded contain a visible notice
at the top of the document pointing to the successor document.

---

### Category 6: Versioning Rules (RULE-VER-001 through RULE-VER-005)

**RULE-VER-001 [H]:** The system version follows Semantic Versioning (semver) 2.0.0.
Major.Minor.Patch. Pre-releases are labeled -alpha.N, -beta.N, -rc.N.

**RULE-VER-002 [H]:** Every MAJOR version increment is accompanied by a migration guide.

**RULE-VER-003 [H]:** Version numbers are stamped in pyproject.toml and in the
relevant __init__.py files. Git tags match the pyproject.toml version.

**RULE-VER-004 [S]:** Pre-release versions (-alpha, -beta, -rc) must not be
deployed to production environments.

**RULE-VER-005 [H]:** The CHANGELOG.md is updated before the version tag is created.
A version tag without a corresponding CHANGELOG entry is not permitted.

---

### Category 7: Quality Rules (RULE-QUAL-001 through RULE-QUAL-010)

**RULE-QUAL-001 [H]:** All Python code passes the configured linter (e.g., lake8,
uff) with zero errors. Warnings may be suppressed with documented justification.

**RULE-QUAL-002 [H]:** All Python code passes the configured type checker (e.g.,
mypy) for typed modules. Type errors are not suppressed without justification.

**RULE-QUAL-003 [H]:** Test coverage for core/ and shared/ does not fall below
90%. Coverage regressions block merge.

**RULE-QUAL-004 [S]:** Test coverage for engine public interfaces does not fall below
80%.

**RULE-QUAL-005 [H]:** The full test suite passes on every pull request before merge.
No merge with failing tests.

**RULE-QUAL-006 [S]:** No test is marked @skip or @xfail without a comment
explaining what is being skipped and why, and a linked issue.

**RULE-QUAL-007 [H]:** Security scanning (CVE check) runs on every pull request.
Known critical vulnerabilities block merge.

**RULE-QUAL-008 [A]:** Code complexity (cyclomatic complexity) is monitored. Functions
with complexity > 10 are flagged for refactoring review.

**RULE-QUAL-009 [H]:** No hardcoded credentials, API keys, or passwords in any
committed file. This is checked by a secret scanner in CI.

**RULE-QUAL-010 [S]:** Performance-critical paths have benchmark tests that run in
CI. A performance regression of > 20% in a benchmark fails the check.

---

### Category 8: Maintainability Rules (RULE-MAINT-001 through RULE-MAINT-005)

**RULE-MAINT-001 [S]:** No module exceeds 1,000 lines. Long modules indicate
insufficient decomposition and must be split.

**RULE-MAINT-002 [S]:** No function or method exceeds 80 lines. Long functions
indicate excessive complexity and must be decomposed.

**RULE-MAINT-003 [A]:** Functions have a single return point where practical.
Multiple return statements in complex functions reduce readability.

**RULE-MAINT-004 [H]:** No duplicate code blocks longer than 15 lines across the
codebase. Duplication is detected by CI and must be refactored into shared utilities.

**RULE-MAINT-005 [S]:** Dead code (code that is never called) is removed rather than
commented out. Version control preserves the history.

---

### Category 9: Security Rules (RULE-SEC-001 through RULE-SEC-010)

**RULE-SEC-001 [H]:** No SQL queries are constructed by string concatenation.
Parameterized queries are mandatory.

**RULE-SEC-002 [H]:** All external inputs are validated before use. No engine uses
unvalidated external input in business logic.

**RULE-SEC-003 [H]:** Credentials are managed through environment variables or a
vault. No credential is hardcoded or stored in a configuration file in version control.

**RULE-SEC-004 [H]:** Log output does not contain credentials, API keys, personal
data, or sensitive financial positions. Log sanitization is applied to all output.

**RULE-SEC-005 [S]:** All HTTP communications use TLS 1.2 or higher.

**RULE-SEC-006 [H]:** File paths that include user input are validated against a
whitelist or sanitized to prevent path traversal attacks.

**RULE-SEC-007 [H]:** The Docker image is built from an official, pinned base image.
No latest tags in Dockerfiles.

**RULE-SEC-008 [S]:** Process permissions follow least-privilege. The application
runs as a non-root user in Docker.

**RULE-SEC-009 [H]:** All JSON/YAML parsed from external sources is validated against
a schema before use.

**RULE-SEC-010 [S]:** The application does not expose internal error messages or
stack traces to external systems. Internal errors are logged; external responses
contain only a sanitized error message.

---

### Category 10: Extensibility Rules (RULE-EXT-001 through RULE-EXT-010)

**RULE-EXT-001 [H]:** New engines are added as new packages under engines/. No
existing engine is modified to incorporate new engine functionality.

**RULE-EXT-002 [S]:** Engine lifecycle methods (init, start, stop, health_check) are
defined in the base engine framework and must not be renamed in implementations.

**RULE-EXT-003 [S]:** Every engine implements the standard engine health check protocol
defined in core/health/. Non-standard health checks that bypass the protocol are
not permitted.

**RULE-EXT-004 [H]:** The Master Orchestrator's engine registration mechanism is
data-driven. New engines are registered by adding a configuration entry, not by
modifying Orchestrator source code.

**RULE-EXT-005 [S]:** Domain types are defined independently of the engines that
produce or consume them. A new domain type does not require changes to existing engines.

**RULE-EXT-006 [A]:** Engine implementations should be written to be runtime-replaceable:
the same interface, a different implementation, loaded at startup time.

**RULE-EXT-007 [H]:** Configuration schema is versioned. A configuration schema
change is backward-compatible within the same major version.

**RULE-EXT-008 [S]:** The event bus schema is versioned. New event types are additive.
Existing event types are not renamed or restructured without a deprecation cycle.

**RULE-EXT-009 [H]:** The repository structure defined in Part II of this document
(IIOS-REPO-ENG-001) may only be changed by a new version of this document, not by
individual pull requests.

**RULE-EXT-010 [A]:** New features should be implemented as new components, not as
modifications to existing components, where this is architecturally feasible.

---

*End of Part VIII — Repository Constitution (100 rules total)*

---

## PART IX — REPOSITORY READINESS CHECKLIST

The Repository Readiness Checklist (RRC) certifies that the repository meets the
engineering standards defined in this document. The checklist is evaluated:
- Before the first production deployment.
- After any significant restructuring.
- As part of every major version release.
- Annually as a health check.

### RRC Overview

| Phase | Name | Gate Count | Type |
|-------|------|-----------|------|
| RRC-01 | Foundation Structure | 10 | HARD |
| RRC-02 | Naming Compliance | 8 | HARD |
| RRC-03 | Package Organization | 8 | HARD |
| RRC-04 | Dependency Health | 8 | HARD |
| RRC-05 | Documentation Completeness | 8 | HARD |
| RRC-06 | Test Coverage | 6 | HARD |
| RRC-07 | Security Compliance | 8 | HARD |
| RRC-08 | CI/CD Readiness | 6 | HARD |
| RRC-09 | Governance Readiness | 5 | SOFT |
| RRC-10 | Long-Term Readiness | 5 | SOFT |

**Total:** 72 gates (62 HARD, 10 SOFT)

---

### RRC-01: Foundation Structure (10 HARD gates)

**RRC-01-01 [H]:** Repository root contains exactly the files defined in Section 2.3.
No extra files at the root. No missing files.

**RRC-01-02 [H]:** All top-level directories defined in Section 2.2 exist.
docs/, engines/, core/, domain/, shared/, config/, esources/,
	ests/, scripts/, deployment/, monitoring/, 	ools/, experiments/,
rchive/, examples/, esearch/ all exist.

**RRC-01-03 [H]:** Every top-level directory has a README.md.

**RRC-01-04 [H]:** All 18 IIOS engines have packages under engines/. Each engine
package has an __init__.py and a README.md.

**RRC-01-05 [H]:** 	ests/ mirrors the source tree structure. Every engine with
source code has a corresponding test directory under 	ests/unit/engines/.

**RRC-01-06 [H]:** .gitignore excludes: .env, __pycache__/, *.pyc, .venv/,
data/, logs/, *.egg-info/, dist/, uild/, .coverage, htmlcov/.

**RRC-01-07 [H]:** .env.example exists and documents all environment variables
used by the system.

**RRC-01-08 [H]:** docs/ contains the mandatory subdirectories: rchitecture/,
engineering/, ontologies/, operations/, decisions/.

**RRC-01-09 [H]:** This engineering specification (IIOS-REPO-ENG-001) is present
in docs/engineering/.

**RRC-01-10 [H]:** CHANGELOG.md exists at the repository root and has entries
for all versions that have been tagged.

---

### RRC-02: Naming Compliance (8 HARD gates)

**RRC-02-01 [H]:** No Python file name violates RULE-NAME-001 (all lowercase with
underscores). Automated check passes with zero violations.

**RRC-02-02 [H]:** No folder name violates RULE-NAME-002. Automated check passes
with zero violations.

**RRC-02-03 [H]:** All Markdown documentation files (except README.md) use
UPPER_SNAKE_CASE. Automated check passes.

**RRC-02-04 [H]:** All engine package names follow the [function]_engine pattern.

**RRC-02-05 [H]:** All test files are named 	est_[module].py. Automated check
passes.

**RRC-02-06 [H]:** All Python exception classes have the Error suffix. Static
analysis confirms.

**RRC-02-07 [H]:** All Python enumeration members are UPPER_SNAKE_CASE. Static
analysis confirms.

**RRC-02-08 [H]:** All Python constants (module-level and class-level) are
UPPER_SNAKE_CASE. Static analysis confirms.

---

### RRC-03: Package Organization (8 HARD gates)

**RRC-03-01 [H]:** Every engine package has an __init__.py that explicitly defines
its public interface (non-empty for packages with public consumers).

**RRC-03-02 [H]:** No engine-to-engine direct imports exist. Dependency graph
validator confirms.

**RRC-03-03 [H]:** No shared/ module imports from engines/. Dependency graph
validator confirms.

**RRC-03-04 [H]:** No core/ module imports from shared/, domain/, or engines/.
Dependency graph validator confirms.

**RRC-03-05 [H]:** No circular imports anywhere in the codebase. Dependency graph
validator confirms.

**RRC-03-06 [H]:** No import from rchive/ by active code. Automated scan confirms.

**RRC-03-07 [H]:** No import from experiments/ by application code. Automated scan
confirms.

**RRC-03-08 [H]:** All test files reside under 	ests/, not inside source packages.

---

### RRC-04: Dependency Health (8 HARD gates)

**RRC-04-01 [H]:** equirements.txt uses exact version pins for all dependencies.

**RRC-04-02 [H]:** All packages in equirements.txt are importable from the current
virtual environment.

**RRC-04-03 [H]:** No package in equirements.txt has a known critical CVE (CVSS
>= 7.0).

**RRC-04-04 [H]:** equirements.txt and equirements-dev.txt are separate.
Development tools are not in production requirements.

**RRC-04-05 [H]:** All dependencies are from public package indices (PyPI). No
private or local-only dependencies.

**RRC-04-06 [H]:** No dependency on pre-release packages in equirements.txt.

**RRC-04-07 [H]:** The full set of declared dependencies can be installed cleanly in
a fresh virtual environment without conflicts.

**RRC-04-08 [H]:** All third-party dependencies used in source code appear in
equirements.txt (no hidden imports).

---

### RRC-05: Documentation Completeness (8 HARD gates)

**RRC-05-01 [H]:** Every engine package has a README.md with: purpose, public
interface summary, owner, and dependencies.

**RRC-05-02 [H]:** Every public symbol in core/ has a docstring. Coverage check
confirms 100%.

**RRC-05-03 [H]:** Every public symbol in shared/ has a docstring. Coverage check
confirms 100%.

**RRC-05-04 [H]:** Every public symbol in domain/ has a docstring. Coverage check
confirms 100%.

**RRC-05-05 [H]:** At least one ADR exists for each major architectural decision
made during IIOS development.

**RRC-05-06 [H]:** ARCHITECTURE.md at the repository root exists and links to all
architecture documents in docs/architecture/.

**RRC-05-07 [H]:** A migration guide exists for every breaking change in the CHANGELOG.

**RRC-05-08 [H]:** The CODEOWNERS file exists in .github/ and covers all
top-level directories.

---

### RRC-06: Test Coverage (6 HARD gates)

**RRC-06-01 [H]:** Test coverage for core/ is >= 90%. CI coverage report confirms.

**RRC-06-02 [H]:** Test coverage for shared/ is >= 90%. CI coverage report confirms.

**RRC-06-03 [H]:** Test coverage for domain/ is >= 90%. CI coverage report confirms.

**RRC-06-04 [H]:** At least one unit test exists for every public method in every
engine's public interface.

**RRC-06-05 [H]:** At least one integration test exists that exercises the full
decision cycle through at least 3 engines.

**RRC-06-06 [H]:** All tests pass cleanly with zero failures and zero errors in the
most recent CI run.

---

### RRC-07: Security Compliance (8 HARD gates)

**RRC-07-01 [H]:** Secret scanner confirms zero hardcoded credentials in any
committed file.

**RRC-07-02 [H]:** .env is in .gitignore and has never been committed (git log
check confirms).

**RRC-07-03 [H]:** Dockerfile uses a pinned base image, not latest.

**RRC-07-04 [H]:** Docker container runs as a non-root user.

**RRC-07-05 [H]:** All SQL query construction uses parameterized queries (static
analysis confirms — no string concatenation in SQL contexts).

**RRC-07-06 [H]:** All external input validation is confirmed (static analysis
and integration tests confirm that all external inputs pass through validation logic).

**RRC-07-07 [H]:** All HTTP communications use HTTPS. No HTTP endpoints in
production configuration.

**RRC-07-08 [H]:** Log output sanitization is confirmed (log tests confirm that
no sensitive values appear in log output).

---

### RRC-08: CI/CD Readiness (6 HARD gates)

**RRC-08-01 [H]:** A CI pipeline exists in .github/workflows/ (or equivalent)
that runs on every pull request.

**RRC-08-02 [H]:** The CI pipeline runs: linting, type checking, dependency validation,
security scanning, and the full test suite.

**RRC-08-03 [H]:** The main branch has branch protection enabled: no direct pushes,
CI must pass, at least one approval required.

**RRC-08-04 [H]:** The Docker image builds successfully from the current Dockerfile
and docker-compose.yml.

**RRC-08-05 [H]:** The system starts successfully in paper trading mode using only
the configuration defined in .env.example plus required real environment variables.

**RRC-08-06 [H]:** A deployment script (scripts/deploy.sh or equivalent) exists
that performs a full deploy and validates both containers are healthy.

---

### RRC-09: Governance Readiness (5 SOFT gates)

**RRC-09-01 [S]:** The CODEOWNERS file covers 100% of the repository's top-level
directories, with no unowned areas.

**RRC-09-02 [S]:** Every engine has a designated owner documented in CODEOWNERS
and in the engine's README.md.

**RRC-09-03 [S]:** The deprecation policy has been followed for at least one
completed deprecation cycle (to confirm the process works).

**RRC-09-04 [S]:** The review process defined in Section 7.2 has been documented
in the repository's contribution guide.

**RRC-09-05 [S]:** An archive policy review has been completed, confirming that
all content in rchive/ has an ARCHIVED.md file.

---

### RRC-10: Long-Term Readiness (5 SOFT gates)

**RRC-10-01 [S]:** At least 5 ADRs have been created, covering the most significant
structural decisions.

**RRC-10-02 [S]:** The repository structure has been reviewed against the engineering
specification (this document) within the last 6 months.

**RRC-10-03 [S]:** At least one full onboarding exercise has been performed (a new
developer navigated the repository to a target component within 2 minutes without
assistance) and documented.

**RRC-10-04 [S]:** The dependency count has been reviewed. If > 100 packages,
a rationalization plan is in place.

**RRC-10-05 [S]:** The long-term maintenance plan (ownership transfer, knowledge
documentation) has been reviewed and is current.

---

*End of Part IX*

---
## SUPPLEMENT A — FOLDER CATALOG

This catalog provides a complete reference for every folder in the IIOS repository,
including purpose, allowed contents, forbidden contents, owner, and growth strategy.

---

### A.1 Root Level

| Folder | Purpose | Owner | Key Constraint |
|--------|---------|-------|---------------|
| docs/ | All documentation | Architecture Council | No source code |
| engines/ | All 18+ engine packages | Per-engine owners | No shared utilities |
| core/ | Infrastructure frameworks | Architecture Council | No business logic |
| domain/ | Domain type definitions | Architecture Council | No business logic |
| shared/ | Cross-engine utilities | Architecture Council | No engine knowledge |
| config/ | Configuration definitions | Architecture Council | No secrets |
| esources/ | Static runtime assets | Per-subsystem | No source code |
| 	ests/ | All test code | Per-engine owners | No business logic |
| scripts/ | Operational scripts | Operations Lead | No app imports |
| deployment/ | Deployment artifacts | Operations Lead | No app source |
| monitoring/ | Observability config | Operations Lead | No app source |
| logs/ | Runtime logs (gitignored) | N/A | Runtime only |
| 	ools/ | Dev/build tools | Architecture Council | No app imports |
| experiments/ | Exploratory work | Per-experimenter | Not imported by app |
| rchive/ | Inactive artifacts | Architecture Council | Never imported |
| examples/ | Usage examples | Per-subsystem | Self-contained only |
| esearch/ | Academic and research | Architecture Council | No source code |
| .github/ | GitHub configuration | Architecture Council | GitHub-specific |

---

### A.2 docs/ Subdirectory Catalog

| Folder | Purpose | Naming Convention |
|--------|---------|------------------|
| docs/architecture/ | Architecture documents | IIOS-*-ARCH-*.md |
| docs/engineering/ | Engineering specifications | IIOS-*-ENG-*.md |
| docs/ontologies/ | Ontology reference docs | IIOS-ONT-*.md |
| docs/operations/ | Operational runbooks | RB-*-*.md |
| docs/decisions/ | Architecture Decision Records | ADR-*-*.md |
| docs/migrations/ | Migration guides | MIGRATION-*.md |
| docs/research/ | Completed research summaries | RESEARCH-*.md |
| docs/glossaries/ | Domain and technical glossaries | GLOSSARY-*.md |
| docs/archive/ | Superseded documents | Original name + ARCHIVED header |

---

### A.3 engines/ Subdirectory Catalog

| Engine Package | Stratum | Primary Responsibility |
|----------------|---------|----------------------|
| engines/global_intelligence/ | 1 | Overnight global context |
| engines/market_intelligence/ | 2 | Regime + sector classification |
| engines/meta_learning/ | 3 | Strategy weight predictor |
| engines/opportunity_engine/ | 4 | Equity + options scanner |
| engines/strategy_lab/ | 5 | Strategy evolution + backtesting |
| engines/capital_risk_engine/ | 6 | Position sizing per budget |
| engines/risk_control/ | 7 | Portfolio risk + stress testing |
| engines/market_simulation/ | 8 | Monte Carlo simulation |
| engines/risk_guardian/ | 9 | Kill-switch guardian |
| engines/debate_and_decision/ | 10 | 5-agent debate + scoring |
| engines/execution_engine/ | 11 | Order routing + broker |
| engines/trade_monitoring/ | 12 | Open trade monitoring |
| engines/learning_system/ | 13 | Model learning + adaptation |
| engines/performance_analytics/ | 14 | Drawdown + walk-forward |
| engines/research_lab/ | 15 | Strategy promotion gates |
| engines/validation_engine/ | 16 | 6-stage strategy validation |
| engines/control_tower/ | 17 | Telemetry + dashboard |
| engines/orchestrator/ | Coord | Master Orchestrator |

---

### A.4 core/ Subdirectory Catalog

| Folder | Purpose |
|--------|---------|
| core/engine/ | Base engine class, lifecycle protocol |
| core/events/ | Event bus, event types base class |
| core/health/ | Health check protocol, OHS computation |
| core/logging/ | Structured logging infrastructure |
| core/errors/ | Base error hierarchy |
| core/messaging/ | Message routing infrastructure |
| core/registry/ | Engine registry |
| core/config/ | Configuration loading infrastructure |
| core/tracing/ | Distributed tracing infrastructure |

---

### A.5 shared/ Subdirectory Catalog

| Folder | Purpose | Consumers |
|--------|---------|-----------|
| shared/math/ | Mathematical utilities | Multiple engines |
| shared/stats/ | Statistical functions | Prediction, Risk |
| shared/datetime/ | Date/time utilities | All engines |
| shared/io/ | File and I/O utilities | Multiple engines |
| shared/cache/ | Caching utilities | Knowledge, Global Intelligence |
| shared/retry/ | Retry and resilience utilities | Data feed engines |
| shared/serial/ | Serialization utilities | All engines with persistence |
| shared/validation/ | Input validation | All engines at boundaries |
| shared/formatting/ | Output formatting | Monitoring, Telegram |
| shared/collections/ | Collection utilities | Multiple engines |

---

### A.6 tests/ Subdirectory Catalog

| Folder | Purpose |
|--------|---------|
| 	ests/unit/engines/ | Unit tests mirroring engines/ |
| 	ests/unit/core/ | Unit tests for core/ |
| 	ests/unit/shared/ | Unit tests for shared/ |
| 	ests/unit/domain/ | Unit tests for domain/ |
| 	ests/integration/ | Cross-engine integration tests |
| 	ests/system/ | Full-system end-to-end tests |
| 	ests/performance/ | Performance benchmarks |
| 	ests/fixtures/ | Shared test fixtures |
| 	ests/utils/ | Shared test utilities |

---

*End of Supplement A*

---

## SUPPLEMENT B — NAMING CATALOG

This catalog provides a comprehensive reference for all naming conventions
used throughout the IIOS repository.

---

### B.1 File Naming Quick Reference

| Artifact Type | Convention | Example |
|---------------|-----------|---------|
| Python module | lowercase_underscores.py | isk_engine.py |
| Python test | 	est_[module].py | 	est_risk_engine.py |
| Python config | [subsystem]_config.py | isk_config.py |
| Engine __init__ | __init__.py | __init__.py |
| Architecture doc | UPPER_SNAKE_CASE.md | IIOS_RISK_ENG.md |
| ADR | ADR-NNN-slug.md | ADR-001-engine-isolation.md |
| Runbook | RB-TOPIC-NNN.md | RB-DEPLOY-001.md |
| JSON data | lower_underscores.json | symbol_map.json |
| JSON schema | 	ype_schema.json | event_schema.json |
| YAML config | lower-hyphens.yaml | production-config.yaml |
| Migration | YYYY-MM-DD_NNN_desc.py | 2026-07-04_001_init.py |
| Shell script | erb_noun.sh | deploy_production.sh |
| README | README.md | README.md |

---

### B.2 Python Symbol Naming Quick Reference

| Symbol Type | Convention | Example |
|-------------|-----------|---------|
| Class | PascalCase | RiskEngine |
| Function | lowercase_underscores | compute_risk_budget |
| Method (public) | lowercase_underscores | get_health_status |
| Method (protected) | _lowercase_underscores | _validate_input |
| Method (private) | __lowercase_underscores | __internal_calc |
| Constant (module) | UPPER_SNAKE_CASE | MAX_POSITION_SIZE |
| Constant (class) | UPPER_SNAKE_CASE | DEFAULT_TIMEOUT |
| Variable | lowercase_underscores | isk_budget |
| Parameter | lowercase_underscores | position_size |
| Exception class | PascalCaseError | RiskBudgetError |
| Enumeration | PascalCase | EngineStatus |
| Enum member | UPPER_SNAKE_CASE | HEALTHY |
| Type alias | PascalCase | PositionId |
| Protocol | PascalCase | EngineProtocol |
| Test class | TestPascalCase | TestRiskEngine |
| Test method | 	est_thing_condition_expected | 	est_budget_exceeded_raises |
| Fixture | lowercase_underscores | mock_event_bus |

---

### B.3 Engine Naming Conventions

Engine names follow the pattern [Function]Engine for the class and
[function]_engine for the package directory.

| Engine | Class Name | Package Name |
|--------|-----------|-------------|
| Global Intelligence | GlobalIntelligenceEngine | global_intelligence |
| Market Intelligence | MarketIntelligenceEngine | market_intelligence |
| Meta Learning | MetaLearningEngine | meta_learning |
| Opportunity Engine | OpportunityEngine | opportunity_engine |
| Strategy Lab | StrategyLabEngine | strategy_lab |
| Capital Risk | CapitalRiskEngine | capital_risk_engine |
| Risk Control | RiskControlEngine | isk_control |
| Market Simulation | MarketSimulationEngine | market_simulation |
| Risk Guardian | RiskGuardianEngine | isk_guardian |
| Debate and Decision | DebateAndDecisionEngine | debate_and_decision |
| Execution Engine | ExecutionEngine | execution_engine |
| Trade Monitoring | TradeMonitoringEngine | 	rade_monitoring |
| Learning System | LearningSystemEngine | learning_system |
| Performance Analytics | PerformanceAnalyticsEngine | performance_analytics |
| Research Lab | ResearchLabEngine | esearch_lab |
| Validation Engine | ValidationEngine | alidation_engine |
| Control Tower | ControlTowerEngine | control_tower |
| Orchestrator | MasterOrchestrator | orchestrator |

---

### B.4 Configuration Naming Conventions

Environment variables follow the pattern IIOS_[SUBSYSTEM]_[PARAMETER].

| Variable Type | Pattern | Example |
|---------------|---------|---------|
| System-wide | IIOS_[PARAM] | IIOS_ENV |
| Engine-specific | IIOS_[ENGINE]_[PARAM] | IIOS_RISK_MAX_BUDGET |
| Data feed | IIOS_FEED_[FEED]_[PARAM] | IIOS_FEED_DHAN_TOKEN |
| Broker | IIOS_BROKER_[PARAM] | IIOS_BROKER_PAPER_MODE |
| Telegram | IIOS_TELEGRAM_[PARAM] | IIOS_TELEGRAM_BOT_TOKEN |
| Database | IIOS_DB_[PARAM] | IIOS_DB_PATH |
| Monitoring | IIOS_MONITOR_[PARAM] | IIOS_MONITOR_PORT |

---

### B.5 Event Naming Conventions

Events in the event bus follow the pattern [DOMAIN].[ENTITY].[ACTION].

| Category | Pattern | Example |
|----------|---------|---------|
| Engine lifecycle | ENGINE.[NAME].[STATUS] | ENGINE.RISK.READY |
| Market data | MARKET.[TYPE].[ACTION] | MARKET.PRICE.UPDATED |
| Decision | DECISION.[TYPE].[ACTION] | DECISION.TRADE.APPROVED |
| Risk | RISK.[TYPE].[ACTION] | RISK.BUDGET.CONSUMED |
| System | SYSTEM.[TYPE].[ACTION] | SYSTEM.KILL_SWITCH.TRIGGERED |
| Learning | LEARN.[TYPE].[ACTION] | LEARN.MODEL.UPDATED |

---

### B.6 Database Object Naming Conventions

Tables and indexes follow lowercase_underscores naming.

| Object Type | Pattern | Example |
|-------------|---------|---------|
| Table | [domain]_[entities] | market_prices |
| Index | idx_[table]_[columns] | idx_market_prices_ts |
| View | _[description] | _daily_pnl |
| Sequence | seq_[table]_id | seq_decisions_id |
| Archive table | rc_[original_name] | rc_market_prices |

---

*End of Supplement B*

---

## SUPPLEMENT C — DEPENDENCY CATALOG

This catalog documents all sanctioned inter-package dependencies in the IIOS
repository, plus all sanctioned third-party dependencies.

---

### C.1 Internal Package Dependency Matrix

The following matrix shows the allowed dependency direction between major package
groups. A tick indicates that the source package may import from the target.

| Source \ Target | core | domain | shared | engines | 	ests |
|-----------------|--------|----------|---------|-----------|---------|
| core          | ✓ self | —        | —       | —         | —       |
| domain        | ✓      | ✓ self   | —       | —         | —       |
| shared        | ✓      | ✓        | ✓ self  | —         | —       |
| engines       | ✓      | ✓        | ✓       | — (bus only) | —  |
| 	ests         | ✓      | ✓        | ✓       | ✓ (public only) | ✓ self |
| scripts       | —      | ✓        | ✓       | ✓ (public only) | — |
| examples      | —      | ✓        | ✓       | ✓ (public only) | — |

---

### C.2 Engine Inter-Dependency Protocol

Engines do not import from each other's Python packages. They communicate through:

| Mechanism | When to Use | Implemented In |
|-----------|-------------|---------------|
| Event Bus | Async notification, no response needed | core/events/ |
| Orchestrator Mediation | Sequential workflow step | engines/orchestrator/ |
| Shared Domain Types | Passing data objects between engines | domain/ |
| Registry Query | Discovering engine capabilities at runtime | core/registry/ |

---

### C.3 Third-Party Dependency Catalog (Production)

| Package | Version (pinned) | Purpose | Risk Level |
|---------|-----------------|---------|-----------|
| yfinance | pinned | Market data fallback | MEDIUM (external API) |
| pandas | pinned | Data manipulation | LOW |
| 
umpy | pinned | Numerical computation | LOW |
| sqlalchemy | pinned | Database ORM | LOW |
| equests | pinned | HTTP client | LOW |
| python-telegram-bot | pinned | Telegram integration | MEDIUM (external) |
| streamlit | pinned | Dashboard UI | LOW (dev-facing) |
| schedule | pinned | Task scheduling | LOW |
| pyaes | pinned | Encryption utilities | HIGH (security) |

**Risk Levels:**
- LOW: Stable, widely used, well-maintained, minimal security surface.
- MEDIUM: External API dependency or moderate security surface.
- HIGH: Security-critical; requires additional scrutiny on every upgrade.

---

### C.4 Third-Party Dependency Catalog (Development)

| Package | Purpose |
|---------|---------|
| pytest | Test runner |
| pytest-cov | Coverage measurement |
| pytest-asyncio | Async test support |
| mypy | Static type checking |
| lake8 or uff | Code linting |
| lack | Code formatting |
| isort | Import sorting |
| pre-commit | Pre-commit hook runner |
| andit | Security scanning |
| safety | Dependency CVE scanning |
| mkdocs | Documentation site generation |

---

### C.5 Forbidden Dependency Patterns

| Pattern | Why Forbidden | Alternative |
|---------|--------------|-------------|
| Engine A imports from Engine B's components | Creates coupling | Use event bus |
| shared/ imports from engines/ | Inverts dependency direction | Refactor to domain/ |
| core/ imports from shared/ | Inverts dependency direction | Use stdlib |
| Circular import chain | Prevents isolated testing | Break cycle with interface |
| Import from rchive/ | Dead code path | Remove the import |
| Unpinned version in equirements.txt | Version drift risk | Pin the version |
| Pre-release in production requirements | Stability risk | Use stable release |

---

*End of Supplement C*

---

## SUPPLEMENT D — ENGINEERING ANTI-PATTERNS

Anti-patterns are recurring engineering decisions that seem reasonable but consistently
cause maintenance problems. This supplement documents the anti-patterns most commonly
observed in complex Python systems, with guidance for avoidance.

---

### AP-REPO-01: The Flat Repository

**Description:** All source files live at the repository root or in a single
src/ directory with minimal substructure.

**Why it happens:** Early in a project, there is only a handful of files.
A flat structure seems simpler.

**Why it is harmful:** As the system grows to hundreds of modules, a flat
structure makes it impossible to: determine what depends on what, identify
which files are tests vs. source vs. configuration, enforce isolation, or
navigate efficiently.

**IIOS approach:** Part II of this document defines the mandatory structure
before any code is written.

---

### AP-REPO-02: The God Module

**Description:** One module accumulates more and more functionality until it
contains thousands of lines and is imported by nearly everything.

**Why it happens:** Utility functions are added to an existing module rather
than creating a new one. The module's name is generic enough to accept almost
anything (utils.py, helpers.py).

**Why it is harmful:** The god module has no clear responsibility. It cannot
be tested in isolation. Changing it ripples through the entire codebase. It
becomes a bottleneck for version control.

**IIOS approach:** RULE-STRUCT-008 caps package size. RULE-MAINT-001 caps
module size. shared/ is categorized into specific submodules.

---

### AP-REPO-03: The Implicit Dependency

**Description:** A module imports from another module that was not explicitly
designed to be a dependency. The dependency is not documented and is unknown
to the dependency graph validator.

**Why it happens:** A developer knows that another module happens to have
the function they need, and imports it directly.

**Why it is harmful:** The dependency is invisible until a refactoring breaks
it. It creates invisible coupling between modules that were intended to be
independent.

**IIOS approach:** RULE-DEP-001 through RULE-DEP-008 govern all dependencies.
The CI dependency validator makes all dependencies explicit.

---

### AP-REPO-04: The Configuration Spread

**Description:** Configuration values are scattered throughout the codebase:
some in config.py, some hardcoded in individual modules, some read from
environment variables inline, some in JSON files.

**Why it happens:** Each developer adds configuration where it is most convenient.

**Why it is harmful:** It is impossible to understand all configuration points
without reading the entire codebase. Deployment-specific values are found in
unexpected places. Security vulnerabilities arise when secrets are stored in
unexpected places.

**IIOS approach:** RULE-CFG-01 through RULE-CFG-05 define a single configuration
architecture. All configuration goes through config/.

---

### AP-REPO-05: The Test Vacuum

**Description:** Tests exist but are not maintained. They are skipped, marked
as expected-to-fail, or simply never run.

**Why it happens:** As code changes, tests are not updated. The cost of fixing
the test seems too high. Tests are skipped "temporarily."

**Why it is harmful:** Tests that are not run provide no safety. A large
test suite with 40% passing is worse than a small test suite with 100% passing,
because the false sense of security is dangerous.

**IIOS approach:** RULE-QUAL-005 requires all tests pass on every PR.
RULE-QUAL-006 requires documented justification for any skipped test.

---

### AP-REPO-06: The Undocumented Breaking Change

**Description:** A public interface is changed without documentation, a
changelog entry, or a migration guide.

**Why it happens:** The developer who made the change knows what changed.
They did not consider that other developers and future maintainers do not.

**Why it is harmful:** Consumers of the interface break unexpectedly. The
cause of the breakage is not discoverable from the changelog. Future developers
cannot understand the change history.

**IIOS approach:** RULE-DOC-006 requires every public interface change to have
a changelog entry. RULE-DOC-008 requires migration guides for breaking changes.

---

### AP-REPO-07: The Growing Root

**Description:** The repository root accumulates scripts, analysis files,
temporary outputs, and miscellaneous files over time until it contains dozens
of files.

**Why it happens:** The root is convenient. Temporary scripts are created there
and never moved.

**Why it is harmful:** The root is the entry point to the repository. A cluttered
root creates a bad first impression and makes it impossible to find the actual
entry point.

**IIOS approach:** Section 2.3 defines exactly which files belong at the root.
RULE-STRUCT-004 forbids application logic at the root. The CI checks for files
at the root that are not on the approved list.

---

### AP-REPO-08: The Version Nobody Updates

**Description:** The version number in pyproject.toml never changes. Every
deployed version is  .1.0 or 1.0.0-dev.

**Why it happens:** Versioning feels ceremonial. It takes effort. It seems
unimportant compared to writing features.

**Why it is harmful:** Without version numbers, it is impossible to reason about
compatibility, to communicate breaking changes, to identify deployed versions,
or to write meaningful changelogs.

**IIOS approach:** RULE-VER-001 through RULE-VER-005 define the versioning
policy. RULE-VER-005 requires changelog updates before version tags.

---

### AP-REPO-09: The Orphaned Experiment

**Description:** An experiments/ or 
otebooks/ directory accumulates
years of exploratory work that was never integrated, never cleaned up, and
never documented.

**Why it happens:** Experiments are created quickly and never revisited. The
cost of cleanup is deferred indefinitely.

**Why it is harmful:** The experiments/ directory becomes a noise source.
It is impossible to determine which experiments are relevant. New developers
waste time exploring dead-end experiments that appear significant.

**IIOS approach:** Section 2.2.14 requires every experiment to have an
experiment.md with hypothesis, owner, and planned end date. Experiments
without documentation are deleted at the next maintenance cycle.

---

### AP-REPO-10: The One Engineer Who Knows

**Description:** Critical repository knowledge — how to deploy, how to
run tests, what configuration variables mean — lives only in one engineer's
head.

**Why it happens:** Documentation is deferred. The engineer who built the
system can always answer questions, so written documentation seems unnecessary.

**Why it is harmful:** Engineer departure, illness, or vacation renders the
system unoperatable. Onboarding new engineers takes weeks instead of hours.
The system becomes fragile in proportion to its dependence on undocumented
knowledge.

**IIOS approach:** RRC-10-03 requires a documented onboarding exercise.
RULE-DOC-001 through RULE-DOC-010 mandate comprehensive documentation.
The operational runbook standard (Section 6.8) ensures every procedure
is executable by someone who did not write it.

---

*End of Supplement D*

---

## SUPPLEMENT E — REPOSITORY GLOSSARY

This glossary defines terms used in this engineering specification with their
precise meanings in the IIOS repository context.

---

**ADR (Architecture Decision Record):** A document that captures a significant
architectural or engineering decision, including the context in which it was made,
the alternatives considered, the rationale for the chosen approach, and its
consequences.

**Artifact:** Any file committed to the repository: source code, documentation,
configuration, test, deployment definition, or resource.

**Base Engine Framework:** The core/engine/ package that defines the lifecycle
protocol, registration protocol, and health check protocol that all engines
implement. The framework calls engine code; engines do not call the framework
directly.

**Breaking Change:** A change to a public interface that makes code written for
the previous version of the interface fail with the new version. Breaking changes
require a deprecation cycle or a major version increment.

**Canonical Package Name:** The official Python import path for a package. The
canonical name is used in __init__.py, in documentation, and in dependency
references. It is always lowercase with underscores.

**CODEOWNERS:** A Git repository file that maps files and directories to their
owning teams or individuals. Pull requests affecting owned files require review
from the specified owner.

**Cohesion:** The degree to which the elements of a package belong together.
High cohesion means the package has a single, clear purpose. Low cohesion means
the package contains unrelated elements.

**Component:** A logical sub-unit within an engine. Implemented as a Python module
within the engine's components/ subdirectory. Not independently deployable.

**Coupling:** The degree to which one package depends on the internals of another.
Low coupling means packages depend only on each other's public interfaces. High
coupling means packages reference each other's internal details.

**DAG (Directed Acyclic Graph):** A graph structure with directed edges and no
cycles. The inter-package dependency graph must be a DAG. A cycle in the
dependency graph is a circular dependency.

**Dead Code:** Source code that is never reached by any execution path. Dead code
creates noise, increases cognitive load, and may hide security vulnerabilities.

**Deprecation:** The process of announcing that a public interface will be removed
in a future version, providing a migration path, and allowing a grace period.

**Dependency Direction:** The direction of import relationships between packages.
In IIOS, the allowed direction flows from engines toward core (engines depend on
shared, which depends on core, which depends on the standard library).

**Domain Type:** A data class, enumeration, or value object defined in domain/
that represents a concept in the IIOS business domain. Domain types have no
business logic.

**Engine:** A self-contained processing unit in IIOS. Each of the 18 IIOS engines
is a Python package with a well-defined public interface, internal state management,
and no runtime dependency on another engine's internals.

**Event Bus:** The core/events/ infrastructure through which engines communicate
asynchronously without direct imports.

**Explicit Public Interface:** The set of names in a package's __init__.py.
Everything not in the __init__.py is private to the package.

**Fixture (test):** A test setup component that provides a known, reproducible
state for tests. In pytest, fixtures are functions decorated with @pytest.fixture.

**Framework:** Infrastructure that calls your code at defined lifecycle points,
as opposed to a library that your code calls. The Base Engine Framework is an
example.

**Hard Gate:** A readiness checklist item that, if not satisfied, blocks
certification. Hard gates have no exceptions.

**Library:** A collection of reusable utilities that your code calls. Unlike a
framework, a library has no lifecycle that calls back into your code.

**Module:** A single Python source file. The atomic unit of source organization.

**Ownership:** The accountability relationship between a person/team and a
repository artifact. The owner reviews changes, maintains documentation, and
answers questions about the artifact.

**Package:** A directory of Python source files with an __init__.py that defines
its public interface.

**Protected:** A Python name with a single leading underscore. Intended for use
within the package but not by external consumers.

**Private:** A Python name with double leading underscore. Intended for use only
within the same module.

**Public Interface:** The set of names exported by a package's __init__.py.
Stable. Changes require deprecation.

**Repository:** The version-controlled directory that contains all source code,
documentation, configuration, and artifacts for IIOS.

**Semver:** Semantic Versioning. A version numbering convention: MAJOR.MINOR.PATCH.
See Section 4.8.

**Soft Gate:** A readiness checklist item that, if not satisfied, triggers a warning
and requires documented justification, but does not block certification outright.

**Stability (package):** A package is stable if it changes infrequently. Stable
packages are safe to depend on. Packages in core/ and domain/ must be more
stable than packages in engines/.

**Stratum:** A vertical layer in the IIOS engine hierarchy. There are 7 strata,
from Foundation (1) to Coordination (7). Engines in higher strata depend on
engines in lower strata.

**Test Coverage:** The percentage of source lines exercised by the test suite.
Used as a proxy (not a guarantee) for test completeness.

**Trunk-Based Development:** A version control strategy in which all developers
work in short-lived branches off a single long-lived main branch.

**Type Alias:** A name given to a complex type expression for readability.
PriceId = str, StrategyWeight = float.

**Vendoring:** Copying a third-party library into the repository's source tree
to isolate the application from upstream changes. Used sparingly in IIOS for
critical dependencies.

**Virtual Environment (.venv/):** The isolated Python environment for IIOS.
Never committed to version control. Recreated from equirements.txt.

**Wildcard Import:** rom module import *. Forbidden in IIOS by RULE-IMPORT-02.
Imports all public names from a module, making it impossible to determine where
a name came from.

**Workspace:** The local development environment: the repository checkout plus
the active virtual environment plus any developer-specific tooling configuration.

---

*End of Supplement E*

---

## DOCUMENT METRICS

| Metric | Value |
|--------|-------|
| Document Code | IIOS-REPO-ENG-001 |
| Version | 1.0.0 |
| Status | AUTHORITATIVE |
| Parts | 9 (I through IX) |
| Supplements | 5 (A through E) |
| Constitutional rules | 100 (RULE-NAME, RULE-STRUCT, RULE-ISO, RULE-DEP, RULE-DOC, RULE-VER, RULE-QUAL, RULE-MAINT, RULE-SEC, RULE-EXT) |
| Hard rules | 65 [H] |
| Soft rules | 26 [S] |
| Advisory rules | 9 [A] |
| Readiness gates | 72 (62 HARD, 10 SOFT) |
| Folder definitions | 18 top-level + all subdirectories |
| Anti-patterns | 10 (AP-REPO-01 through AP-REPO-10) |
| Glossary entries | 40+ |
| Naming tables | 6 |
| Dependency tables | 5 |

---

## AMENDMENT HISTORY

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-07-04 | Initial release | Architecture Council |

---

*This document is the authoritative engineering specification for the IIOS repository.*
*All contributions to the repository must comply with the rules defined herein.*
*Questions, clarifications, and amendment proposals are directed to the Architecture Council.*

---

*IIOS-REPO-ENG-001 Version 1.0.0*
*Investment Intelligence Operating System — Repository Engineering Specification*
*Architecture Council — 2026-07-04*
*End of Document.*
---

## EXTENDED SUPPLEMENT — ENGINE PACKAGE SPECIFICATION TEMPLATES

This section provides the canonical template for every engine package in the IIOS
repository. Every engine must conform to this template. Deviations require an ADR.

---

### ES-01: Engine Package Directory Template

`
engines/[engine_name]/
|
|-- __init__.py                    # Public interface (REQUIRED)
|-- [engine_name].py               # Main engine class (REQUIRED)
|-- README.md                      # Engine documentation (REQUIRED)
|
|-- components/                    # Internal components (REQUIRED directory)
|   |-- __init__.py                # Internal re-exports (not public)
|   |-- [component_name].py        # One file per component
|   |-- [component_name_2].py
|
|-- models/                        # Engine-local data models (if needed)
|   |-- __init__.py
|   |-- [model_name].py
|
|-- utils/                         # Engine-local utilities (if needed)
|   |-- __init__.py
|   |-- [utility_name].py
|
|-- config/                        # Engine-local defaults (REQUIRED)
|   |-- __init__.py
|   |-- defaults.py                # Default configuration values
|
|-- data/                          # Engine-local static data (if needed)
|   |-- [static_data_file].json
|
|-- tests/ (NOT here — see tests/unit/engines/[engine_name]/)
`

---

### ES-02: Engine __init__.py Template

The __init__.py defines exactly what is visible to external consumers.

`
# engines/[engine_name]/__init__.py
# Document code: IIOS-ENG-[NNN]
# Version: X.Y.Z
# Owner: [name or team]

# --- Public exports ---
# List every name that external code may import from this engine.
# Names not listed here are private to this engine.

from .[engine_name] import [EngineMainClass]
from .models.[model_module] import [PublicModelType]

# --- Version ---
__version__ = "X.Y.Z"

# --- Public API surface ---
__all__ = [
    "[EngineMainClass]",
    "[PublicModelType]",
]
`

**Rules for __init__.py:**
- Every exported name must be explicitly listed in __all__.
- At most 10 exported names. More than 10 indicates excessive public surface.
- Version is recorded here and in pyproject.toml.
- No business logic in __init__.py.
- No side effects in __init__.py at import time.

---

### ES-03: Engine README.md Template

`markdown
# [Engine Name]

**Document code:** IIOS-ENG-[NNN]
**Package:** engines/[engine_name]
**Version:** X.Y.Z
**Owner:** [name or team]
**Stratum:** [1-17 or "Coordination"]

## Purpose

[2-4 sentences describing what this engine does and why it exists.]

## Public Interface

| Symbol | Type | Description |
|--------|------|-------------|
| [ClassName] | Class | [brief description] |
| [ModelType] | Dataclass | [brief description] |

## Dependencies

### Depends On
- core/engine/ — Base engine framework
- domain/[type] — [description]
- shared/[util] — [description]

### Is Consumed By
- engines/orchestrator/ — lifecycle management
- engines/[other_engine]/ — [description of use]

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| IIOS_[ENGINE]_PARAM | alue | [description] |

## Running in Isolation

[Instructions for running the engine standalone for development/testing.]

## Running Tests

`
pytest tests/unit/engines/[engine_name]/
`

## Key Design Decisions

[1-3 sentences on non-obvious design decisions and why they were made.]

## Change History

| Version | Date | Change |
|---------|------|--------|
| X.Y.Z | YYYY-MM-DD | [description] |
`

---

### ES-04: Engine Main Class Structure

The main engine class structure follows the Base Engine Framework lifecycle protocol.

**Lifecycle methods (mandatory — defined in Base Engine Framework):**
- __init__(self, config: EngineConfig) — Constructor. Receives injected config.
- initialize(self) -> None — Performs initialization. May block.
- start(self) -> None — Begins engine operation.
- stop(self) -> None — Begins orderly shutdown.
- health_check(self) -> HealthStatus — Returns current health status.

**Interface methods (engine-specific):**
- Named according to Python naming conventions.
- Documented with full docstrings.
- Listed in __init__.py if public.
- Not listed in __init__.py if internal.

**State management:**
- All mutable state is instance variables.
- No module-level mutable state shared between engine instances.
- Thread safety is the engine's responsibility where applicable.

---

### ES-05: Engine Test Package Structure

`
tests/unit/engines/[engine_name]/
|-- __init__.py
|-- conftest.py                # Fixtures specific to this engine's tests
|-- test_[engine_name].py      # Tests for the main engine class
|-- test_[component_a].py      # Tests for component A
|-- test_[component_b].py      # Tests for component B
|-- test_integration.py        # Integration test (uses mocks for dependencies)
`

**Testing rules per engine:**
- The main engine class test covers all public interface methods.
- Each component has its own test module.
- All tests use dependency injection; no real external services are called.
- The event bus is mocked in all unit tests.
- Fixtures provide canonical test data for domain types.

---

## EXTENDED SUPPLEMENT — CI/CD PIPELINE SPECIFICATION

This section defines the CI/CD pipeline that enforces the engineering standards
defined in this document.

---

### CI-01: Pull Request Pipeline

Every pull request to main triggers the following checks in order:

**Stage 1 — Code Quality (fast, must pass first)**

| Check | Tool | Threshold | Block? |
|-------|------|-----------|--------|
| Code formatting | black / ruff | Zero diffs | Yes |
| Import ordering | isort | Zero diffs | Yes |
| Linting | flake8 / ruff | Zero errors | Yes |
| Type checking | mypy | Zero errors (typed modules) | Yes |

**Stage 2 — Dependency Validation**

| Check | Tool | Threshold | Block? |
|-------|------|-----------|--------|
| Circular import detection | pydeps / custom | Zero cycles | Yes |
| Forbidden dependency check | custom | Zero violations | Yes |
| Requirements completeness | pip check | Zero missing | Yes |
| Requirements security scan | safety / pip-audit | Zero CVSS>=7 | Yes |

**Stage 3 — Secret Scanning**

| Check | Tool | Threshold | Block? |
|-------|------|-----------|--------|
| Credential scan | detect-secrets / trufflehog | Zero matches | Yes |
| Environment variable check | custom | All secrets use env vars | Yes |

**Stage 4 — Tests**

| Check | Tool | Threshold | Block? |
|-------|------|-----------|--------|
| Unit tests | pytest | 100% pass | Yes |
| Integration tests | pytest | 100% pass | Yes |
| Coverage (core) | pytest-cov | >= 90% | Yes |
| Coverage (shared) | pytest-cov | >= 90% | Yes |
| Coverage (domain) | pytest-cov | >= 90% | Yes |
| Coverage (engine interfaces) | pytest-cov | >= 80% | Warn |

**Stage 5 — Repository Structure Validation**

| Check | Tool | Threshold | Block? |
|-------|------|-----------|--------|
| Root file whitelist | custom | No extra root files | Yes |
| README presence | custom | All dirs have README.md | Warn |
| Naming conventions | custom | Zero violations | Yes |

---

### CI-02: Main Branch Pipeline

Every merge to main (after PR pipeline passes) triggers additional checks:

**Stage 6 — Build Validation**

| Check | Threshold | Block? |
|-------|-----------|--------|
| Docker image builds successfully | Exit 0 | Yes |
| Docker container starts successfully | Health OK | Yes |
| System starts in paper trading mode | Startup completes | Yes |

**Stage 7 — Artifact Publication**

| Action | Condition |
|--------|-----------|
| Docker image pushed to registry | Stage 6 passes |
| Coverage report published | Always |
| Dependency graph published | Always |

---

### CI-03: Release Pipeline

When a version tag X.Y.Z is pushed, the release pipeline runs:

| Stage | Action |
|-------|--------|
| 1 | Full PR pipeline checks |
| 2 | Full main branch pipeline checks |
| 3 | Build production Docker image |
| 4 | Tag and push production Docker image as X.Y.Z and latest |
| 5 | Create GitHub Release with changelog entry |
| 6 | Notify Architecture Council of release |

---

### CI-04: Pre-Commit Hooks

Pre-commit hooks run locally before any commit is finalized. They catch issues
before they reach CI, reducing feedback latency.

**Required pre-commit hooks:**

| Hook | Purpose |
|------|---------|
| lack | Code formatting |
| isort | Import sorting |
| lake8 / uff | Linting |
| 	railing-whitespace | Remove trailing whitespace |
| end-of-file-fixer | Ensure files end with newline |
| check-yaml | YAML syntax validation |
| check-json | JSON syntax validation |
| detect-secrets | Credential scanning |
| check-added-large-files | Block files > 50MB |

**Installation:** pre-commit install from the repository root, run once per
developer environment setup.

---

## EXTENDED SUPPLEMENT — REPOSITORY EVOLUTION STRATEGY

This section documents how the repository is expected to evolve over time,
and the governance process for structural changes.

---

### RE-01: Near-Term Evolution (Year 1)

**Expected changes in Year 1:**
- New agent additions within existing engine packages.
- New components within existing engines.
- New shared utilities as patterns emerge.
- New documentation as the system is operated and understood better.

**What should NOT change in Year 1:**
- The top-level directory structure.
- The dependency direction rules.
- The naming conventions.
- The engine public interfaces (only additive changes).

---

### RE-02: Medium-Term Evolution (Years 2-5)

**Expected changes in Years 2-5:**
- New engines (new rows in the engine catalog).
- New strata (if the system expands into new domains).
- New shared library categories as patterns solidify.
- Possible extraction of one or two engines into microservices (those with
  independent deployment requirements).
- Migration from single-process to multi-process execution for select engines.

**What requires an ADR in Years 2-5:**
- Any new top-level directory.
- Any new engine (to confirm it fits the engine model).
- Any microservice extraction.
- Any change to the Base Engine Framework.

---

### RE-03: Long-Term Evolution (Years 5-20)

**Expected changes in Years 5-20:**
- Full microservices architecture for all engines (each engine deployed independently).
- Multiple data center deployment.
- Multiple market support (global markets, not just NSE).
- New asset class support (equities, derivatives, commodities, crypto).
- New modality support (news, alternative data, sentiment).

**Structural invariants that must survive all evolution:**
1. The dependency direction (engines depend on core, not the reverse).
2. The event bus as the engine communication mechanism.
3. The engine public interface contract (versioned, deprecated, not arbitrarily broken).
4. The naming conventions (because 20 years of code depends on them).
5. The documentation standards (because 20 years of history must be navigable).

---

### RE-04: Repository Structure Amendment Process

The repository structure defined in Part II of this document may only be changed
by an amendment to this document (IIOS-REPO-ENG-001). The amendment process:

**Step 1 — Proposal:** Any contributor may propose a structural amendment by
creating a document PROPOSED_AMENDMENT_IIOS-REPO-ENG-001-[NNN].md in
docs/engineering/.

**Step 2 — Review period:** 30-day review period during which any contributor
may comment. The proposal is shared in the team communication channel.

**Step 3 — Architecture Council decision:** After the review period, the
Architecture Council votes. A two-thirds majority is required for amendment.

**Step 4 — Migration plan:** If approved, a migration plan is created and reviewed.
The migration plan describes how existing code will be moved to comply with the
new structure.

**Step 5 — Implementation:** The migration is implemented in a dedicated branch
and reviewed by two Architecture Council members.

**Step 6 — Document update:** This document is updated with a new version number
and the change is recorded in the Amendment History table.

---

## EXTENDED SUPPLEMENT — SECURITY ENGINEERING SPECIFICATION

The security engineering specification defines the security controls built into
the repository structure and development process.

---

### SE-01: Secret Management Architecture

Secrets never enter the repository. The secret management architecture:

**Layer 1 — Local development:** Secrets in .env file (gitignored). Documented
in .env.example with descriptions and placeholder values.

**Layer 2 — CI/CD:** Secrets in GitHub Actions secrets (or equivalent CI secret
store). Referenced as environment variables in pipeline definitions.

**Layer 3 — Production:** Secrets in environment variables on the host, or in a
vault (HashiCorp Vault, AWS Secrets Manager, etc.).

**What counts as a secret:**
- API keys and tokens (Dhan, Telegram, any data provider)
- Passwords and passphrases
- Database credentials
- Encryption keys
- Private keys (SSH, TLS)

**What does not count as a secret:**
- Default configuration values
- System thresholds (VIX limit, loss limit)
- Public API base URLs
- Feature flags

---

### SE-02: Dependency Security Process

Every third-party dependency is evaluated at adoption time and monitored continuously.

**Adoption evaluation criteria:**
1. License: must be compatible with IIOS's usage model.
2. CVE history: no unpatched critical or high CVEs in the last 12 months.
3. Maintenance: active maintenance with releases in the last 12 months.
4. Adoption: used by a significant number of other projects (reduces supply chain risk).
5. Necessity: the functionality cannot be implemented using existing dependencies.

**Continuous monitoring:**
- safety or pip-audit runs in CI on every PR.
- Weekly automated dependency security scan.
- On discovery of a CVE with CVSS >= 7.0: upgrade or remove within 7 days.
- On discovery of a CVE with CVSS >= 4.0: upgrade or remove within 30 days.

---

### SE-03: Audit Logging Architecture

The audit log captures every sensitive operation for post-incident analysis.

**What is audit-logged:**
- System startup and shutdown events
- Kill switch triggers and resets
- Every investment decision (approve, reject, withdraw)
- Every position open and close
- Every configuration change
- Every override command
- Every governance certification

**Audit log properties:**
- Append-only: no modification or deletion of audit records.
- Structured: JSON format for machine readability.
- Timestamped: UTC timestamps with millisecond precision.
- Sanitized: no credentials, no PII, no full position detail in external logs.

**Audit log location:** logs/audit/ (runtime-generated, gitignored).
**Audit log retention:** 3 years minimum.
**Audit log integrity:** SHA-256 hash chain to detect tampering.

---

### SE-04: Input Validation Architecture

All external inputs are validated before use. External inputs include:

- Market data from data feeds (Dhan, yfinance)
- Telegram commands from users
- Configuration files loaded at startup
- Files loaded from esources/

**Validation layers:**
- **Schema validation:** External data is validated against a defined schema before
  use. Invalid data is rejected and logged.
- **Range validation:** Numerical values are validated against configured ranges.
  A price of 0 or a price 10x the previous price is flagged for review.
- **Type validation:** Values are validated to be of the expected type before use
  in calculations.
- **Sanitization:** String inputs (especially from Telegram commands) are sanitized
  before any system action is taken.

---

### SE-05: Threat Model Summary

IIOS is not a public service. Its attack surface is:

| Threat Vector | Likelihood | Mitigation |
|---------------|-----------|-----------|
| Compromised API token | MEDIUM | Token rotation, minimal permissions |
| Malicious market data | LOW | Range validation, sanity checks |
| Compromised Telegram command | MEDIUM | Command whitelist, user ID validation |
| SQL injection via data | LOW | Parameterized queries (RULE-SEC-001) |
| Container escape | LOW | Non-root user (RULE-SEC-008) |
| Dependency supply chain | MEDIUM | Pinned versions, CVE scanning |
| Credentials in code | LOW | Secret scanning in CI (RULE-SEC-009) |
| Log data leakage | LOW | Log sanitization (RULE-SEC-004) |

---

## EXTENDED SUPPLEMENT — OPERATIONAL ENGINEERING NOTES

These notes supplement the formal specification with operational context
drawn from IIOS's actual deployment and operating experience.

---

### OEN-01: Paper Trading vs. Live Trading Repository Config

The repository supports two primary operational modes, configured via environment
variables. From a repository perspective:

**Paper trading mode:** Uses data/paper_trades.csv for trade journaling.
No real broker credentials are required. The IIOS_BROKER_PAPER_MODE=true
environment variable activates this mode.

**Live trading mode:** Requires real broker credentials (IIOS_FEED_DHAN_TOKEN,
IIOS_BROKER_DHAN_CLIENT_ID). The IIOS_BROKER_PAPER_MODE=false environment
variable activates this mode.

**Engineering implication:** The broker credentials and paper mode flag are the
only significant differences between paper and live configurations from a
repository perspective. Both modes use identical source code paths.

---

### OEN-02: Single-Process vs. Multi-Process Considerations

The current IIOS deployment runs all 18 engines in a single Python process with
cooperative multitasking (the scheduler model). The repository is structured to
accommodate multi-process evolution:

- Each engine is a self-contained package.
- Engine interfaces are defined as Python protocols (contracts without implementation).
- The event bus is designed to be replaceable with a network-capable message broker.
- The config/ system supports per-engine configuration injection.

When multi-process deployment is required, the migration path is:
1. Wrap each engine's public interface in a gRPC or HTTP adapter.
2. Replace in-process event bus with a network message broker (e.g., Redis Streams).
3. Deploy each engine package as an independent container.
4. Keep the Orchestrator as the coordination service.

---

### OEN-03: Windows vs. Linux Path Compatibility

IIOS is developed on Windows (Windows 11) and deployed on Linux (Docker container
on Ubuntu). Engineering rules that support cross-platform compatibility:

- All file paths in source code use pathlib.Path (not string concatenation).
- No hardcoded absolute paths.
- os.sep is never concatenated into paths directly.
- All script line endings are LF (.gitattributes enforces this).
- Docker image uses Linux base, ensuring production behaviour on Linux.

---

### OEN-04: Data Directory vs. Repository

The data/ directory is a runtime directory. It is:
- Created automatically at first startup.
- Populated with SQLite databases, CSV journals, and model files.
- Mounted as a Docker volume (./data:/app/data).
- Excluded from version control.

Engineering implication: source code must never assume data/ is empty, and
must never assume data/ contains any specific files at startup. The startup
procedure validates and creates all required data/ artifacts.

---

### OEN-05: VPS Deployment Notes

IIOS is deployed to a VPS (Virtual Private Server) using Docker Compose.
The deployment engineering:

- docker-compose.yml defines two services: i-trading-brain and 	rading-dashboard.
- Both services must be healthy for the deployment to be considered successful.
- The VPS has a data/ volume that persists across container restarts.
- Container logs are accessible via docker logs [container-name].
- The docker compose build --no-cache flag ensures fresh Python source is used.
- Health checks are defined in Dockerfile using HEALTHCHECK instructions.

---

## DOCUMENT METRICS (UPDATED)

| Metric | Value |
|--------|-------|
| Document Code | IIOS-REPO-ENG-001 |
| Version | 1.0.0 |
| Status | AUTHORITATIVE |
| Total Parts | 9 (I through IX) |
| Total Supplements | 10 (A through E + 5 Extended) |
| Constitutional rules | 100 |
| Hard rules [H] | 65 |
| Soft rules [S] | 26 |
| Advisory rules [A] | 9 |
| Readiness gates | 72 (62 HARD, 10 SOFT) |
| Anti-patterns | 10 |
| Glossary entries | 45+ |
| Security threat vectors | 8 |
| CI/CD pipeline stages | 7 |
| Engine package templates | 5 |
| Named folders defined | 35+ |
| Naming tables | 6 |

---

## EXTENDED SUPPLEMENT — COMPLETE RULE REFERENCE WITH RATIONALE

This supplement provides an extended rationale for every category of rules in the
Repository Constitution. Understanding the rationale helps contributors apply the
rules correctly in edge cases not explicitly covered.

---

### Rationale for Category 1 — Naming Rules

The primary purpose of naming rules is to make the repository self-describing and
navigable. When a developer new to the IIOS codebase sees a file named
isk_engine.py, they immediately know: this is a Python module, it relates to
the risk engine, and it follows IIOS conventions. If naming were inconsistent —
RiskEngine.py, iskengine.py, isk-engine.py, e.py — the developer gains
no information from the name.

**Why lowercase_underscores for Python files?**
Python's own standard library convention. The Python community has converged on this
style. Following it means every Python developer starts with zero cognitive load about
IIOS file naming.

**Why UPPER_SNAKE_CASE for Markdown documents?**
Markdown documents are documentation artifacts, not executable code. The convention
differentiates them visually from Python modules and signals that they are distinct
artifact types. The uppercase convention also makes document names instantly visible
in directory listings.

**Why must exception classes have the Error suffix?**
Python's own built-in exceptions use this convention (ValueError, TypeError,
RuntimeError). IIOS exceptions must be distinguishable from non-exception classes
at a glance. An exception class named RiskBudgetExceeded is ambiguous — is it an
exception, a result type, or a condition? RiskBudgetExceededError is unambiguous.

**Why must constants be at module or class scope?**
Constants defined inside functions are local variables with constant values, not
constants. They cannot be referenced from other functions in the same module without
re-defining them. Constants at module or class scope can be imported, inspected,
and documented. See also the user memory note on the "constant scope bug" pattern.

---

### Rationale for Category 2 — Structure Rules

Structure rules protect the invariant that the repository is navigable and that
artifacts live in predictable locations.

**Why must every directory have a README.md?**
A directory without a README.md is opaque to a developer who hasn't been inside it
before. The README.md converts the directory from a black box to a documented artifact.
The cost of writing a README.md is minutes. The benefit — across dozens of developers
over 20 years — is hours of navigation time saved.

**Why must tests not live inside source packages?**
Tests and source code have different purposes, different contributors, and different
lifecycles. Mixing them creates a cluttered source directory that makes it difficult
to understand what the package actually provides vs. what tests it. Tests are not
part of the package's public surface. A user of the isk_engine package doesn't
need or want the test files to be importable from it.

**Why must the root contain only defined files?**
Over a long-lived project, a repository root accumulates miscellaneous files: analysis
scripts, one-off utilities, experiment notebooks, output files. Each individual addition
seems harmless. Over years, the root becomes a graveyard of forgotten artifacts that
makes the repository feel unmaintained. The whitelist enforces intentionality.

**Why must archive/ items never be imported?**
If archived code is still being imported, it isn't actually archived — it's still in
the dependency chain. The archive policy distinguishes between "we keep this for
historical reference" and "this is still running." If archived code is needed, it must
be re-promoted to the active codebase, with documentation of why.

---

### Rationale for Category 3 — Isolation Rules

Isolation rules exist because the IIOS system has 18 engines that must evolve
independently. Without structural isolation, evolution of one engine creates
cascading changes in others.

**Why must engines not import from each other directly?**
Consider a hypothetical: the isk_engine imports rom engines.knowledge_engine.components.regime_classifier import RegimeClassifier. If the Knowledge Engine is later refactored to rename or restructure egime_classifier.py, the Risk Engine silently breaks. The Risk Engine developer has no indication that Knowledge Engine internals changed, because the change was inside the Knowledge Engine. This coupling is invisible until a runtime failure.

The event bus alternative: the Knowledge Engine emits a REGIME_CLASSIFIED event.
The Risk Engine subscribes to this event. When the Knowledge Engine's internals change,
the event contract remains stable. The Risk Engine never knew or cared about
egime_classifier.py.

**Why must core/ have no business logic?**
core/ is the most stable layer of the repository. It changes rarely, deliberately,
and with broad impact. If business logic enters core/ — even a single business rule —
the governance burden for changes to core/ increases. The separation is absolute
so that governance can be calibrated: changes to core/ require Architecture Council
review precisely because core/ contains no business logic and changes are therefore
almost always structural.

**Why must no global mutable state cross engine boundaries?**
In a system that may eventually be multi-process or distributed, global mutable state
is a deployment blocker. Even in a single-process context, global mutable state creates
invisible coupling: engine A writes to a global, engine B reads it, and neither engine
documents this relationship. Testing engine A requires being careful about its effects
on the global state that engine B reads. This is the "spooky action at a distance"
anti-pattern, and it must not exist in IIOS.

---

### Rationale for Category 4 — Dependency Rules

Dependency rules prevent the most common cause of long-lived software complexity:
the accumulation of undeclared, unmanaged dependencies.

**Why must requirements.txt use exact pins?**
Version ranges (>=X, <Y) create a class of bugs where the application works on the
developer's machine (with version X.3) but fails in production (with version X.7, which
was installed fresh). Exact pins eliminate this class. The cost is that upgrades must
be intentional — but that is the point. Dependency upgrades are maintenance tasks that
deserve attention.

**Why is the transitive dependency count capped at 150?**
Each third-party dependency is a vector for security vulnerabilities, license issues,
and breaking changes. A system with 300 transitive dependencies has 300 potential
sources of failure that are outside the team's control. At 150, a rationalization
review is triggered to ensure the dependency set is still appropriate.

**Why must new core/ and shared/ dependencies have Architecture Council review?**
core/ and shared/ are consumed by all engines. A new dependency in core/ is a
new dependency of every engine in the system. The review ensures that the dependency
is necessary, well-chosen, and consistent with the existing dependency set.

---

### Rationale for Category 5 — Documentation Rules

Documentation rules exist because IIOS has a planned 20-year life. Over 20 years,
the original developers will not always be available. The documentation rules ensure
that the knowledge of how the system works is durably encoded in the repository.

**Why must core/, shared/, and domain/ have 100% docstring coverage?**
These packages form the foundation that all engines build upon. An engine developer
who needs to understand how a shared utility works must not have to read implementation
code to do so. The docstring is the interface specification; the implementation is
the detail. 100% coverage ensures the interface specification is always available.

**Why must every ADR exist for major decisions?**
A common failure mode in long-lived projects: a decision was made years ago, nobody
remembers why, and the system now appears to have an arbitrary constraint. Future
developers either waste time discovering the reason empirically or (worse) remove the
constraint without understanding its consequences. ADRs prevent this. The decision
is permanently available, along with the reasoning. If the reasoning is later invalidated,
the ADR is updated with a "SUPERSEDED BY" notice.

---

### Rationale for Category 7 — Quality Rules

Quality rules define the minimum bar for code that enters the repository.

**Why must all tests pass before merge?**
This is the fundamental invariant of trunk-based development. If main contains
failing tests, every developer's environment is broken. Every developer has to
decide whether a failing test is "known" or "new." This cognitive overhead is
eliminated by requiring zero failures before merge.

**Why is security scanning mandatory?**
A known CVE that could have been detected automatically but wasn't is an organisational
failure, not a technical one. The system is processing real financial transactions. A
compromised dependency could affect financial outputs, expose credentials, or create
regulatory liability. The cost of scanning is zero. The cost of not scanning can be
catastrophic.

---

### Rationale for Category 9 — Security Rules

Security rules in the repository specification reflect OWASP Top 10 principles
applied to the IIOS codebase.

**Why are parameterized queries mandatory? (OWASP A03: Injection)**
String-concatenated SQL queries are the source of SQL injection vulnerabilities.
In IIOS, market data and user inputs (Telegram commands) pass through the system.
Without parameterized queries, a malformed market data value or a crafted Telegram
command could execute arbitrary SQL. The architectural requirement for parameterized
queries eliminates this attack surface.

**Why must all external inputs be validated? (OWASP A03: Injection, A04: Insecure Design)**
IIOS ingests data from multiple external sources: market data APIs, the Telegram
bot interface, configuration files. An attacker who can influence any of these sources
can potentially influence the system's behavior. Input validation is the first line of
defense. For IIOS, the most critical validation is on the Telegram command interface
(which is publicly reachable if the bot token is known) and on market data (which
could contain malformed values).

**Why must Docker run as non-root? (OWASP A05: Security Misconfiguration)**
Running a container as root means that any container escape vulnerability gives the
attacker root access to the host. Running as a non-root user limits the blast radius.
This is a standard security practice with zero performance cost.

**Why is log sanitization required? (OWASP A09: Security Logging and Monitoring Failures)**
Logs are frequently the first artifact examined after a security incident. If logs
contain credentials or sensitive position data, the logs themselves become a security
liability. Log sanitization ensures that the audit trail is useful for security
analysis without exposing sensitive data.

---

## EXTENDED SUPPLEMENT — MIGRATION PATTERNS

This supplement documents common migration patterns that arise when evolving the
IIOS repository.

---

### MP-01: Adding a New Engine

**Trigger:** A new intelligence or operational function is required that does not
fit within an existing engine's responsibility.

**Steps:**
1. Create an ADR (ADR-NNN-new-[engine-name].md) documenting the new engine's
   purpose, rationale, and integration points.
2. Create the engine package directory under engines/[engine_name]/.
3. Create the engine package structure (see ES-01 template).
4. Write the engine's README.md before writing the engine's first line of code.
5. Write the engine's public interface (__init__.py) before implementing it.
6. Register the engine in the Orchestrator's configuration.
7. Create the test package under 	ests/unit/engines/[engine_name]/.
8. Write unit tests for the public interface concurrently with implementation.
9. Update the engine catalog in Supplement A.3.
10. Update the CHANGELOG.md with the new engine.

---

### MP-02: Splitting an Oversized Module

**Trigger:** A module exceeds 1,000 lines (RULE-MAINT-001 violation) or becomes
too broad in responsibility.

**Steps:**
1. Identify the cohesive sub-responsibilities within the module.
2. For each sub-responsibility, define a new module name following naming conventions.
3. Move classes and functions to their respective new modules.
4. Update __init__.py to export from the new modules instead of the old one.
5. If the original module name is in the public interface, keep it as a re-export
   module (imports all from the new modules) for one deprecation cycle.
6. Update all internal references.
7. Confirm all tests still pass.

---

### MP-03: Extracting a Shared Utility

**Trigger:** A utility that was implemented in one engine is needed by a second engine.

**Steps:**
1. Confirm the utility contains no engine-specific business logic.
2. Create the new module in the appropriate shared/[category]/ directory.
3. Copy the utility to shared/[category]/[utility_name].py.
4. Write unit tests in 	ests/unit/shared/[category]/test_[utility_name].py.
5. Update the original engine to import from shared/ instead of its own utils/.
6. Update the second engine to import from shared/.
7. Remove the now-duplicated copy from the first engine's utils/ (or deprecate it
   if it was part of the engine's public interface).
8. Update Supplement C with the new shared utility.

---

### MP-04: Deprecating a Public Interface

**Trigger:** A public method, class, or function must be changed incompatibly.

**Steps:**
1. Create the new interface (new method signature, new class, or new function).
2. Keep the old interface and mark it as deprecated in its docstring:
   Deprecated since version X.Y.Z. Use [new_interface] instead.
3. In the old interface's implementation, emit a DeprecationWarning.
4. Update the CHANGELOG.md with a Deprecated section entry.
5. Announce the deprecation in team channels.
6. After the minimum 90-day grace period, in a MAJOR version increment:
   a. Remove the deprecated code.
   b. Update the CHANGELOG.md with a Removed section entry.
   c. If there was no migration guide, create one now with the removal announcement.

---

### MP-05: Archiving an Engine

**Trigger:** An engine is being replaced by a new implementation, or the functionality
it provided is no longer needed.

**Steps:**
1. Create an ADR documenting why the engine is being archived and what (if anything)
   replaces it.
2. Remove the engine from the Orchestrator's engine registry.
3. Remove any direct dependencies on the engine from configuration files.
4. Move the engine package from engines/[engine_name]/ to
   rchive/engines/[engine_name]/.
5. Create rchive/engines/[engine_name]/ARCHIVED.md documenting: why archived,
   when archived, and what replaces it.
6. Confirm no active code imports from the archived engine (CI check confirms).
7. Update the engine catalog in Supplement A.3.
8. Update the CHANGELOG.md with a Removed section entry.

---

## EXTENDED SUPPLEMENT — TOOLCHAIN SPECIFICATION

This supplement documents the standard toolchain for IIOS development.

---

### TC-01: Python Version

IIOS targets Python 3.11+ for all new code. Python 3.10 support is maintained
for one year after 3.11 becomes the minimum. The active Python version is declared
in:
- pyproject.toml (equires-python = ">=3.11")
- Dockerfile (FROM python:3.11-slim)
- .github/workflows/*.yml (CI Python version matrix)

---

### TC-02: Package Manager

pip with equirements.txt is the standard for production dependency management.
pip-tools (pip-compile) is recommended for maintaining equirements.txt from
a higher-level equirements.in file.

equirements.in — high-level dependencies without versions.
equirements.txt — pinned, fully-resolved dependency set generated by pip-compile.

Developers update equirements.in and run pip-compile to regenerate equirements.txt.

---

### TC-03: Virtual Environment

.venv/ in the repository root, created with python -m venv .venv.
The .venv/ directory is gitignored.

Activation:
- Windows: .venv\Scripts\Activate.ps1
- Linux/Mac: source .venv/bin/activate

---

### TC-04: Code Formatter

**Primary formatter:** lack with default line length of 88.
lack --check . must pass in CI with zero diffs.
Formatting is applied automatically by pre-commit hook.

**Import sorter:** isort configured to be compatible with lack.
isort --check-only . must pass in CI.

---

### TC-05: Linter

**Primary linter:** uff (preferred) or lake8 with standard plugins.
Zero errors required in CI.

Standard rule exclusions (if any) are in pyproject.toml under [tool.ruff] or
.flake8. Rule exclusions require a comment justifying the exclusion.

---

### TC-06: Type Checker

**Primary type checker:** mypy in strict mode for core/, shared/, and
domain/. Standard mode for engines/.

mypy --strict [target] must pass for core, shared, domain.
mypy [target] must pass for engines.

Type: ignore comments are permitted with a mandatory explanation comment.

---

### TC-07: Test Runner

**Primary test runner:** pytest.
Test configuration in pytest.ini or pyproject.toml under [tool.pytest.ini_options].

Standard pytest configuration:
`
testpaths = ["tests"]
addopts = "--strict-markers --tb=short"
`

Coverage configuration uses pytest-cov:
`
addopts = "--cov=engines --cov=core --cov=shared --cov=domain --cov-report=term-missing"
`

---

### TC-08: Security Scanner

**Dependency CVE scanner:** safety or pip-audit.
Runs in CI on every PR. Configuration in .safety-policy.yml or equivalent.

**Secret scanner:** detect-secrets or 	rufflehog.
Runs as a pre-commit hook and in CI.
Secret baseline file: .secrets.baseline.

**Static security analyzer:** andit.
Runs in CI. High-severity findings block merge.

---

### TC-09: Documentation Generator

**Primary doc generator:** mkdocs with mkdocs-material theme.
Documentation site generated from docs/ directory and docstrings.

mkdocs.yml at repository root defines site structure, navigation, and theme.
mkdocs build must succeed in CI.

---

### TC-10: Pre-Commit Framework

**Framework:** pre-commit.
Configuration in .pre-commit-config.yaml at repository root.
Hooks run automatically before every commit after pre-commit install.

Required initial setup (per developer environment):
`
pip install pre-commit
pre-commit install
`

---

## EXTENDED SUPPLEMENT — ARCHITECTURAL PATTERNS FOR IIOS REPOSITORY

This supplement documents architectural patterns specific to the IIOS repository
organization that go beyond the generic engineering rules.

---

### AP-IIOS-01: The Stratum Pattern

IIOS organizes its 18 engines into 7 strata, where higher strata consume services
from lower strata. This stratum organization is reflected in:

**Documentation:** Engine README.md files identify their stratum.
**Engine catalog:** Supplement A.3 lists engines by stratum.
**Dependency direction:** A Stratum 5 engine may consume from Strata 1-4, but never
from Strata 6-7. This constraint is not automatically enforced but is documented in
this specification and reviewed in ADRs for new engines.

**Why the stratum pattern matters for repository organization:**
When debugging a decision cycle, the stratum tells you in which order engines ran.
When adding a new engine, the stratum tells you which engines are potential inputs
and outputs. When reviewing a dependency graph, unexpected cross-stratum dependencies
are flagged for review.

---

### AP-IIOS-02: The Kill Switch Pattern

The Risk Guardian engine (Stratum 9) implements three kill switches:
- Daily loss >= 2%
- VIX > 45
- Strategy drawdown >= 15%

These kill switches are the highest-priority safety controls in IIOS. Their
repository-engineering implication:

**Protected modules:** engines/risk_guardian/ is listed as a protected module
in copilot-instructions.md. Changes require explicit user instruction.
**Test coverage:** The kill switch logic must have >= 95% test coverage (higher than
the general 80% engine requirement).
**Documentation:** Every kill switch condition is documented in both the engine
README and the IIOS Constitution.
**Audit logging:** Every kill switch trigger is audit-logged with full context.

---

### AP-IIOS-03: The Singleton Pattern

IIOS has four designated singletons (see copilot-instructions.md):
- get_performance_tracker()
- get_regime_strategy_map()
- get_telegram_bot()
- get_feed_manager()

Repository-engineering implications:
- Singleton factory functions live in their respective engine packages.
- Singleton instances are never constructed outside their factory function.
- Test code that needs a singleton uses the factory with a test-specific configuration.
- Documentation for each singleton notes that it must not be instantiated twice.

---

### AP-IIOS-04: The Evidence Dossier Pattern

IIOS strategies must maintain an evidence dossier demonstrating their readiness
for deployment. This pattern has repository implications:

**Location:** Evidence dossiers are stored in data/dossiers/ (runtime, not in
repository).
**Template:** The evidence dossier template is in esources/templates/dossier_template.md.
**Validity:** Dossiers older than 30 days are expired and require renewal.
**Review:** The Research Lab engine reviews dossiers against promotion gates.

---

### AP-IIOS-05: The Configuration Injection Pattern

All engines receive their configuration through constructor injection, not through
global reads. This pattern has repository implications:

**No singleton configuration:** There is no global get_config() function that
all engines call. Each engine receives its specific configuration at construction.
**Configuration types:** Each engine defines a configuration dataclass in its
config/defaults.py. The Orchestrator assembles these per-engine configurations
from the global configuration.
**Testing isolation:** Tests can inject test-specific configuration without affecting
other tests.
**Runtime flexibility:** An engine can be reconfigured by constructing a new instance
with a different configuration object.

---

## CLOSING STATEMENT

The Investment Intelligence Operating System will exist for decades. The code written
today will be read, modified, extended, and operated by engineers who have not yet
begun their careers. The engineering standards defined in this document are an
investment in the future: every hour spent enforcing a naming rule, every ADR written
for a non-obvious decision, every test written for an edge case is hours saved by
a future maintainer who needs to understand, trust, and extend this system.

Repository engineering is not overhead. It is the infrastructure of trust that makes
long-lived systems possible.

Every standard in this document was designed with one question in mind:

*Will an engineer in 2046, reading this repository for the first time, be able to*
*navigate it, understand it, and confidently contribute to it?*

If the answer is yes, the standards are working.

---

*IIOS-REPO-ENG-001 Version 1.0.0*
*Investment Intelligence Operating System — Repository Engineering Specification*
*Architecture Council — 2026-07-04*
*End of Document.*
---

## EXTENDED SUPPLEMENT — COMPLETE FOLDER AND FILE INVENTORY

This inventory enumerates every expected folder and file in a fully initialized
IIOS repository, along with its status (REQUIRED or OPTIONAL) and brief purpose.

---

### FI-01: Root Level Files

| File | Status | Purpose |
|------|--------|---------|
| main.py | REQUIRED | Single system entry point |
| config.py | REQUIRED | Global configuration module |
| equirements.txt | REQUIRED | Pinned production Python dependencies |
| equirements-dev.txt | REQUIRED | Pinned development Python dependencies |
| equirements.in | OPTIONAL | High-level dep source for pip-compile |
| docker-compose.yml | REQUIRED | Docker Compose service definitions |
| Dockerfile | REQUIRED | Container build definition |
| README.md | REQUIRED | Project overview and quick-start |
| ARCHITECTURE.md | REQUIRED | Architecture overview with links |
| CHANGELOG.md | REQUIRED | Version history in Keep-a-Changelog format |
| LICENSE | REQUIRED | Software license |
| .gitignore | REQUIRED | VCS exclusion patterns |
| .env.example | REQUIRED | Environment variable documentation template |
| pyproject.toml | REQUIRED | Python project metadata and tool config |
| pytest.ini | OPTIONAL | Pytest config (may be in pyproject.toml) |
| setup.cfg | OPTIONAL | Alternate pytest/tool config |
| .pre-commit-config.yaml | REQUIRED | Pre-commit hook definitions |
| mkdocs.yml | OPTIONAL | Documentation site configuration |
| .secrets.baseline | REQUIRED | detect-secrets baseline |
| .gitattributes | REQUIRED | LF line endings enforcement |

---

### FI-02: docs/ Directory Files

| File | Status | Purpose |
|------|--------|---------|
| docs/README.md | REQUIRED | Documentation index |
| docs/architecture/README.md | REQUIRED | Architecture document index |
| docs/engineering/README.md | REQUIRED | Engineering document index |
| docs/engineering/REPOSITORY_ENGINEERING.md | REQUIRED | This document |
| docs/ontologies/README.md | REQUIRED | Ontology document index |
| docs/operations/README.md | REQUIRED | Operations document index |
| docs/decisions/README.md | REQUIRED | ADR index |
| docs/decisions/ADR-001-engine-isolation.md | REQUIRED | First structural ADR |
| docs/glossaries/README.md | REQUIRED | Glossary index |
| docs/migrations/README.md | OPTIONAL | Migration guide index |

---

### FI-03: engines/ Required Files Per Engine

For each of the 18 engine packages, the following files are REQUIRED:

| File | Purpose |
|------|---------|
| engines/[name]/__init__.py | Public interface |
| engines/[name]/[name].py | Main engine class |
| engines/[name]/README.md | Engine documentation |
| engines/[name]/components/__init__.py | Component package marker |
| engines/[name]/config/__init__.py | Config package marker |
| engines/[name]/config/defaults.py | Default configuration values |

---

### FI-04: core/ Directory Files

| File | Status | Purpose |
|------|--------|---------|
| core/__init__.py | REQUIRED | Core package marker |
| core/README.md | REQUIRED | Core documentation |
| core/engine/__init__.py | REQUIRED | Engine framework package |
| core/engine/base_engine.py | REQUIRED | Abstract base engine |
| core/engine/lifecycle.py | REQUIRED | Lifecycle protocol |
| core/engine/registry.py | REQUIRED | Engine registry |
| core/events/__init__.py | REQUIRED | Events package |
| core/events/bus.py | REQUIRED | Event bus implementation |
| core/events/event.py | REQUIRED | Base event type |
| core/health/__init__.py | REQUIRED | Health package |
| core/health/health_check.py | REQUIRED | Health check protocol |
| core/health/ohs.py | REQUIRED | OHS computation |
| core/logging/__init__.py | REQUIRED | Logging package |
| core/logging/logger.py | REQUIRED | Structured logger |
| core/errors/__init__.py | REQUIRED | Error hierarchy package |
| core/errors/base_errors.py | REQUIRED | Base error types |
| core/registry/__init__.py | REQUIRED | Registry package |
| core/messaging/__init__.py | REQUIRED | Messaging package |
| core/messaging/router.py | REQUIRED | Message router |

---

### FI-05: shared/ Directory Files

| File | Status | Purpose |
|------|--------|---------|
| shared/__init__.py | REQUIRED | Shared package marker |
| shared/README.md | REQUIRED | Shared utilities documentation |
| shared/math/__init__.py | REQUIRED | Math utilities package |
| shared/stats/__init__.py | REQUIRED | Statistics utilities package |
| shared/datetime/__init__.py | REQUIRED | Datetime utilities package |
| shared/io/__init__.py | REQUIRED | I/O utilities package |
| shared/cache/__init__.py | REQUIRED | Cache utilities package |
| shared/retry/__init__.py | REQUIRED | Retry utilities package |
| shared/serial/__init__.py | REQUIRED | Serialization utilities package |
| shared/validation/__init__.py | REQUIRED | Validation utilities package |
| shared/formatting/__init__.py | REQUIRED | Formatting utilities package |
| shared/collections/__init__.py | REQUIRED | Collections utilities package |

---

### FI-06: tests/ Directory Files

| File | Status | Purpose |
|------|--------|---------|
| 	ests/__init__.py | REQUIRED | Test root package marker |
| 	ests/conftest.py | REQUIRED | Root pytest fixtures |
| 	ests/README.md | REQUIRED | Test suite documentation |
| 	ests/unit/__init__.py | REQUIRED | Unit test package marker |
| 	ests/unit/engines/__init__.py | REQUIRED | Engine unit test package |
| 	ests/unit/core/__init__.py | REQUIRED | Core unit test package |
| 	ests/unit/shared/__init__.py | REQUIRED | Shared unit test package |
| 	ests/unit/domain/__init__.py | REQUIRED | Domain unit test package |
| 	ests/integration/__init__.py | REQUIRED | Integration test package |
| 	ests/integration/conftest.py | REQUIRED | Integration test fixtures |
| 	ests/system/__init__.py | OPTIONAL | System test package |
| 	ests/performance/__init__.py | OPTIONAL | Performance test package |
| 	ests/fixtures/__init__.py | REQUIRED | Shared fixtures package |
| 	ests/utils/__init__.py | REQUIRED | Test utilities package |

---

### FI-07: deployment/ Directory Files

| File | Status | Purpose |
|------|--------|---------|
| deployment/README.md | REQUIRED | Deployment documentation |
| deployment/docker/README.md | REQUIRED | Docker deployment notes |
| deployment/ci/README.md | REQUIRED | CI/CD pipeline documentation |
| deployment/environments/production.yaml | REQUIRED | Production environment config |
| deployment/environments/paper.yaml | REQUIRED | Paper trading environment config |
| deployment/environments/development.yaml | OPTIONAL | Development environment config |

---

### FI-08: .github/ Directory Files

| File | Status | Purpose |
|------|--------|---------|
| .github/copilot-instructions.md | REQUIRED | Copilot coding instructions |
| .github/CODEOWNERS | REQUIRED | Repository ownership map |
| .github/PULL_REQUEST_TEMPLATE.md | REQUIRED | PR description template |
| .github/workflows/pr.yml | REQUIRED | Pull request CI workflow |
| .github/workflows/main.yml | REQUIRED | Main branch CI workflow |
| .github/workflows/release.yml | OPTIONAL | Release pipeline workflow |
| .github/ISSUE_TEMPLATE/bug_report.md | OPTIONAL | Bug report template |
| .github/ISSUE_TEMPLATE/feature_request.md | OPTIONAL | Feature request template |

---

## EXTENDED SUPPLEMENT — QUALITY METRICS AND TARGETS

This supplement defines the measurable quality targets for the IIOS repository.
These targets are tracked in CI reports and reviewed monthly.

---

### QM-01: Code Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Lint violations | 0 | uff check . / lake8 . |
| Type errors (core/shared/domain) | 0 | mypy --strict [target] |
| Type errors (engines) | 0 | mypy [target] |
| Cyclomatic complexity > 10 | 0 | adon cc . |
| Duplicate code blocks > 15 lines | 0 | pylint --disable=all --enable=duplicate-code |
| Modules > 1000 lines | 0 | Custom check |
| Functions > 80 lines | 0 | Custom check |

---

### QM-02: Test Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Total test count | >= 500 | pytest --collect-only |
| Test pass rate | 100% | pytest |
| Coverage (core) | >= 90% | pytest-cov |
| Coverage (shared) | >= 90% | pytest-cov |
| Coverage (domain) | >= 90% | pytest-cov |
| Coverage (engine interfaces) | >= 80% | pytest-cov |
| Skipped tests with no justification | 0 | Custom check |
| Tests marked xfail without issue | 0 | Custom check |

---

### QM-03: Documentation Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Directories without README.md | 0 | Custom check |
| Public symbols in core/ without docstrings | 0 | Custom check |
| Public symbols in shared/ without docstrings | 0 | Custom check |
| Engine packages without README.md | 0 | Custom check |
| ADR count for major decisions | >= 5 | Manual review |
| CHANGELOG entries without version | 0 | Custom check |

---

### QM-04: Security Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Hardcoded secrets | 0 | detect-secrets scan |
| Dependencies with CVE CVSS >= 7.0 | 0 | pip-audit |
| Dependencies with CVE CVSS >= 4.0 | 0 (within 30 days) | pip-audit |
| Bandit high-severity findings | 0 | andit -r . |
| Non-root Docker check | PASS | Dockerfile review |
| Pinned Docker base image | PASS | Dockerfile review |

---

### QM-05: Repository Health Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Circular dependencies | 0 | pydeps / custom |
| Forbidden dependency violations | 0 | Custom check |
| Requirements completeness | 100% | pip check |
| Root file count | <= 20 | ls root count |
| Archive items without ARCHIVED.md | 0 | Custom check |
| Experiment items without experiment.md | 0 | Custom check |
| Outdated runbooks (> 6 months untested) | 0 | Date metadata check |

---

## EXTENDED SUPPLEMENT — INTEGRATION WITH IIOS ARCHITECTURE SERIES

This specification (IIOS-REPO-ENG-001) is one document in the IIOS Architecture
Series. Its relationships to other documents in the series are:

---

### IS-01: Dependency on This Document

The following documents depend on standards defined in IIOS-REPO-ENG-001:

| Document | Dependency |
|----------|-----------|
| All engine architecture documents | Engine package structure (ES-01) |
| All ADRs | ADR format (Section 6.5) |
| All operational runbooks | Runbook format (Section 6.8) |
| IIOS-INTEG-ARCH-001 | Engine isolation guarantees (Section 3.7) |
| IIOS-MO-ARCH-001 | Engine registry conventions (Section 3.6) |

---

### IS-02: Documents That Inform This Document

| Document | Contribution |
|----------|-------------|
| copilot-instructions.md | Protected module list, singleton list, deployment steps |
| ARCHITECTURE.md | 17-layer architecture requiring engine isolation |
| IIOS-INTEG-ARCH-001 | Constitutional rules for system behavior |

---

### IS-03: Repository Engineering Series Position

| # | Document | Domain |
|---|----------|--------|
| 1 | IIOS-REPO-ENG-001 | Repository structure and standards |
| 2 | IIOS-CODE-ENG-001 (future) | Code style and implementation standards |
| 3 | IIOS-TEST-ENG-001 (future) | Testing standards |
| 4 | IIOS-DEP-ENG-001 (future) | Deployment engineering standards |
| 5 | IIOS-SEC-ENG-001 (future) | Security engineering standards |

IIOS-REPO-ENG-001 is the foundational document of the Repository Engineering series.
Future documents in the series extend rather than contradict it.

---

## AMENDMENT HISTORY (UPDATED)

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-07-04 | Initial release. Parts I-IX, Supplements A-E, Extended Supplements | Architecture Council |

---

*IIOS-REPO-ENG-001 Version 1.0.0 — Investment Intelligence Operating System*
*Repository Engineering Specification — COMPLETE*
*Architecture Council — 2026-07-04*
*End of Document.*
---

## EXTENDED SUPPLEMENT — ONBOARDING GUIDE FOR NEW CONTRIBUTORS

This guide is for engineers joining the IIOS project for the first time. It assumes
familiarity with Python and Git, but no prior IIOS knowledge.

---

### OG-01: First Steps (Day 1)

**Step 1 — Clone and explore (30 minutes):**
Clone the repository. Open it in VS Code. Read the root-level README.md and
ARCHITECTURE.md. Read this document (docs/engineering/REPOSITORY_ENGINEERING.md).
Do not open any source files yet.

**Step 2 — Navigation exercise (30 minutes):**
Without assistance, find the following in the repository:
- The Risk Guardian engine's main class.
- The test for the Risk Guardian engine's kill switch.
- The ADR that documented the decision to use the event bus for engine communication.
- The runbook for deploying to the VPS.
- The configuration variable for paper trading mode.

If you can find all five within 30 minutes, the repository is navigable. If not,
create a documentation ticket describing what was hard to find.

**Step 3 — Environment setup (1 hour):**
Follow the environment setup instructions in README.md. Run the full test suite.
All tests must pass before you write any code.

---

### OG-02: First Contribution (Week 1)

Your first contribution should be small, well-scoped, and in a part of the codebase
you understand. Suggested first contribution types:
- Add a docstring to an undocumented public function in shared/.
- Add a test for an untested edge case in core/.
- Improve a README.md that is unclear.
- Fix a failing test (if any exist).

Your first PR should be reviewed by the Engine Owner for the relevant package.
The review is not just about code quality — it is a mutual learning exercise.

---

### OG-03: Repository Navigation Reference

| "I want to find..." | "Look in..." |
|---------------------|-------------|
| How the Risk Engine works | engines/risk_control/README.md |
| What makes a strategy valid | engines/research_lab/README.md |
| How engines communicate | core/events/ |
| What configuration options exist | config/ + .env.example |
| How to deploy to VPS | docs/operations/RB-DEPLOY-*.md |
| Why a particular decision was made | docs/decisions/ADR-*.md |
| The system's constitutional rules | IIOS-INTEG-ARCH-001 in docs/architecture/ |
| The repository engineering rules | This document |
| Historical decisions and changes | CHANGELOG.md |

---

### OG-04: Key Contacts (Governance)

| Role | Responsibility |
|------|---------------|
| Architecture Council | Core/domain/shared changes, structural decisions |
| Engine Owners | Individual engine changes |
| Operations Lead | Deployment, monitoring, CI/CD |
| Security Lead | Dependency security, vulnerability response |

Contact information for each role is in .github/CODEOWNERS.

---

*IIOS-REPO-ENG-001 Version 1.0.0 — Onboarding Supplement*

---

## DOCUMENT SUMMARY

**IIOS-REPO-ENG-001** defines the complete engineering specification for the
Investment Intelligence Operating System repository.

The document establishes:
- A 9-part engineering specification covering philosophy through readiness
- 100 constitutional rules (65 HARD, 26 SOFT, 9 ADVISORY)
- 72 readiness certification gates (62 HARD, 10 SOFT)
- 5 core supplements (folder catalog, naming catalog, dependency catalog,
  anti-patterns, glossary)
- 8 extended supplements (engine templates, CI/CD, evolution strategy, security,
  operational notes, complete inventory, quality metrics, architecture series integration)
- 5 IIOS-specific architectural patterns
- 10 engineering anti-patterns to avoid
- An onboarding guide for new contributors

This document is AUTHORITATIVE. All current and future IIOS contributors are
bound by its rules. All amendments require the process defined in Section RE-04.

---

*End of IIOS-REPO-ENG-001.*
---

## EXTENDED SUPPLEMENT — LONG-TERM MAINTENANCE CALENDAR

This supplement defines the recurring maintenance activities required to keep the
IIOS repository in compliance with this engineering specification.

---

### MC-01: Daily Automated Checks (CI — runs automatically)

| Check | Tool | Action on Failure |
|-------|------|-------------------|
| Lint and format | ruff / black | PR blocked |
| Type checking | mypy | PR blocked |
| Security scan | pip-audit / detect-secrets | PR blocked |
| Circular import check | custom | PR blocked |
| Test suite | pytest | PR blocked |
| Docker build | docker build | PR blocked |

---

### MC-02: Weekly Maintenance Activities

| Activity | Owner | Duration |
|----------|-------|---------|
| Dependency security scan review | Security Lead | 30 min |
| New CVE triage (if any flagged) | Security Lead | Variable |
| CI failure rate review | Operations Lead | 15 min |
| Experiment directory review | Architecture Council | 15 min |

---

### MC-03: Monthly Maintenance Activities

| Activity | Owner | Duration |
|----------|-------|---------|
| Repository health metrics review | Architecture Council | 1 hour |
| Stale README review (12+ months without update) | Per-engine owners | Variable |
| Dependency upgrade review | Operations Lead | 2 hours |
| ADR index update (confirm all major decisions documented) | Architecture Council | 30 min |
| Archive review (any new items to archive?) | Architecture Council | 30 min |

---

### MC-04: Quarterly Maintenance Activities

| Activity | Owner | Duration |
|----------|-------|---------|
| Full repository structure audit against this spec | Architecture Council | 4 hours |
| Runbook testing (each runbook executed and validated) | Operations Lead | 1 day |
| Engine owner roster review (any ownership changes?) | Architecture Council | 1 hour |
| Performance benchmark review | Engineering Lead | 2 hours |
| Pre-commit hook update (latest tool versions) | Engineering Lead | 1 hour |

---

### MC-05: Annual Maintenance Activities

| Activity | Owner | Duration |
|----------|-------|---------|
| Full engineering specification review | Architecture Council | 1 day |
| Amendment consideration (any rules outdated?) | Architecture Council | Half day |
| Onboarding exercise (new dev navigates repo) | Architecture Council | 1 hour |
| Long-term plan review (trajectory for next year) | Architecture Council | 2 hours |
| Archive cleanup (confirm archive items are properly annotated) | Architecture Council | 2 hours |
| Deprecation pipeline review (anything overdue for removal?) | Architecture Council | 1 hour |

---

## EXTENDED SUPPLEMENT — CODEOWNERS TEMPLATE

The CODEOWNERS file in .github/ maps repository paths to their owners.
This template shows the structure for a complete IIOS CODEOWNERS file.

`
# IIOS CODEOWNERS
# Format: [path] [owner1] [owner2]
# All paths are relative to the repository root.
# Ordered from least to most specific — last matching pattern wins.

# --- Default: Architecture Council owns everything not explicitly assigned ---
*                           @architecture-council

# --- Core infrastructure: Architecture Council ---
/core/                      @architecture-council
/domain/                    @architecture-council
/shared/                    @architecture-council
/config/                    @architecture-council

# --- Documentation: Architecture Council ---
/docs/                      @architecture-council
/ARCHITECTURE.md            @architecture-council
/CHANGELOG.md               @architecture-council

# --- Deployment and CI: Operations Lead ---
/deployment/                @operations-lead
/monitoring/                @operations-lead
/.github/workflows/         @operations-lead
/Dockerfile                 @operations-lead
/docker-compose.yml         @operations-lead

# --- Individual engines: Per-engine owners ---
/engines/global_intelligence/       @engine-owner-global-intel
/engines/market_intelligence/       @engine-owner-market-intel
/engines/risk_guardian/             @architecture-council
/engines/debate_and_decision/       @engine-owner-debate
/engines/execution_engine/         @engine-owner-execution
/engines/orchestrator/              @architecture-council

# --- Tests: Mirror source ownership ---
/tests/unit/engines/risk_guardian/  @architecture-council

# --- Scripts: Operations Lead ---
/scripts/                   @operations-lead

# --- Security-sensitive files: Architecture Council + Security Lead ---
/requirements.txt           @architecture-council @security-lead
/.pre-commit-config.yaml    @architecture-council @security-lead
/.secrets.baseline          @security-lead
`

**Important:** The CODEOWNERS file takes effect only when branch protection is
configured to require review from CODEOWNERS. This must be set in the repository
settings.

---

*IIOS-REPO-ENG-001 Version 1.0.0*
*Investment Intelligence Operating System — Repository Engineering Specification*
*Architecture Council — 2026-07-04*
*Document Complete.*