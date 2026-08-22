# ENGINEERING STANDARDS

## AI Trading Brain / Investment Intelligence Operating System (IIOS)

---

| Attribute | Value |
|---|---|
| **Document Title** | Engineering Standards |
| **Document ID** | ES-2026-001 |
| **Version** | 1.0.0 |
| **Status** | ACTIVE — MANDATORY |
| **Classification** | Internal Engineering Authority |
| **Effective Date** | 2026-07-02 |
| **Parent Document** | AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md |
| **Constitutional Authority** | INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md |
| **Maintained By** | Engineering Architecture under Human Principal supervision |
| **Review Cycle** | Quarterly or on any major platform change |

---

## Authority Statement

This document is the **mandatory engineering constitution** for the AI Trading Brain / Investment Intelligence Operating System (IIOS). It governs every present and future source file, module, service, agent, API, database object, script, test case, deployment artifact, and documentation artifact in this system.

Every engineer, automated process, and AI agent contributing to this system **must comply** with these standards. No exception is valid unless formally recorded in the Engineering Decision Register with documented justification and Human Principal sign-off.

These standards exist to enforce:

- **Consistency** — predictable structure across all 17 layers and 62+ agents
- **Maintainability** — any engineer can navigate, understand, and safely modify any module
- **Reliability** — defects are caught by standards before they reach production
- **Security** — no module can introduce vulnerabilities through non-conformance
- **Observability** — every system behaviour is traceable, measurable, and auditable
- **Long-term sustainability** — the system remains operable and evolvable over years

---

## Scope

These standards apply to ALL artefacts in the workspace:

| Artefact Category | In Scope? | Governing Parts |
|---|---|---|
| Python source modules | YES | II, III, IV, V, VI, VII, VIII |
| Configuration files | YES | II, III, VIII |
| Logging and telemetry | YES | VI |
| Test suites | YES | VII |
| Git history and branches | YES | IX |
| Docker images and containers | YES | III, VIII |
| Database tables, columns, indexes | YES | III |
| Documentation and architecture docs | YES | V |
| Shell scripts and batch files | YES | II, III, IV |
| Environment variables and secrets | YES | III, VIII |
| Deployment artifacts | YES | II, VIII, IX |
| Architecture decision records | YES | V, X |

---

## Table of Contents

| Part | Title | Focus |
|---|---|---|
| I | Engineering Philosophy | Why these standards exist; objectives; principles |
| II | Repository Standards | Structure, ownership, file organisation, dependencies |
| III | Naming Standards | All naming conventions — files, symbols, infrastructure |
| IV | Coding Standards | Principles, error handling, concurrency, performance |
| V | Documentation Standards | Module docs, decision records, changelogs, README |
| VI | Logging Standards | Levels, structure, correlation, retention, audit |
| VII | Testing Standards | Unit, integration, performance, security, coverage |
| VIII | Security Standards | Secrets, auth, encryption, input validation, audit |
| IX | Git Standards | Branches, commits, PRs, tagging, rollback |
| X | Engineering Constitution | 60+ mandatory engineering rules |

---
## PART I — ENGINEERING PHILOSOPHY

### 1.0 Why Engineering Standards Exist

Engineering standards are not bureaucratic obstacles — they are the institutional memory of every hard lesson learned. Without explicit standards, each engineer makes independent local decisions that appear reasonable in isolation but produce systems that are inconsistent, unpredictable, unmaintainable, and ultimately unsafe to operate with real capital.

The AI Trading Brain manages financial decisions that have real monetary consequences. A misnamed environment variable, an undocumented function, an untested code path, or a non-atomic state update can cause the system to submit an order it should not, fail to submit one it should, or prevent a kill-switch from activating in time. Standards are, therefore, not a quality-of-life concern — they are a risk management obligation.

---

### 1.1 Objectives of These Standards

| Objective | Description | Measured By |
|---|---|---|
| **Consistency** | All modules follow the same structural, naming, and behavioural conventions regardless of which layer they belong to | Code review checklist pass rate; naming convention audit score |
| **Maintainability** | Any qualified engineer can understand, modify, or extend any module within 30 minutes of reading it | Time-to-first-safe-edit metric; defect rate attributable to misunderstanding |
| **Scalability** | The system architecture and module interfaces permit adding new agents, strategies, data sources, and brokers without restructuring existing modules | Feature addition time; number of files touched per new feature |
| **Reliability** | The system behaves correctly under all specified conditions, including feed failures, VPS restarts, market volatility spikes, and partial network outages | Mean time between failures; recovery time objective; kill-switch activation accuracy |
| **Security** | No module creates a vulnerability through non-conformant secret handling, input acceptance, output encoding, or dependency management | Vulnerability scan results; secrets exposure incidents; dependency audit findings |
| **Observability** | Every behaviour, decision, error, and performance metric is traceable through logs, telemetry, and the decision record chain | Log coverage ratio; telemetry gap rate; time-to-diagnosis for production incidents |
| **Long-term sustainability** | The system remains operable, evolvable, and understandable after 1 year, 3 years, and 5 years without accumulating technical debt that compromises safety | Technical debt index; documentation coverage; test coverage; coupling metrics |

---

### 1.2 Core Philosophical Principles

These principles underpin every specific standard in this document. When a specific standard is silent on a situation, these principles provide the authoritative guidance.

**Principle P-01: Safety First**
Every engineering decision, when all else is equal, shall choose the option that is safer for capital preservation. An order not sent is better than an order wrongly sent. A cycle skipped is better than a cycle that corrupts state.

**Principle P-02: Explicitness Over Cleverness**
Code that is clearly correct is preferable to code that is cleverly efficient. Cleverness hides bugs. Explicitness exposes them. The AI Trading Brain must be debuggable by a tired engineer at 2am after a market incident.

**Principle P-03: Fail-Safe Defaults**
Every component defaults to the safe state when in doubt. If the risk system cannot be reached, the answer is REJECT. If the kill-switch state is unknown, the answer is BLOCKED. If the decision record is missing, the answer is DO NOT PROCEED.

**Principle P-04: Minimum Surface Area**
Each module exposes the minimum public interface required to fulfil its single responsibility. Private implementation details are kept private. This prevents coupling and reduces the blast radius of any change.

**Principle P-05: Record Before Act**
Every consequential action (trade decision, order submission, kill-switch state change, configuration change, learning update) is recorded in durable storage before the action is taken. The record is the source of truth.

**Principle P-06: Dependency Flows Inward**
Higher-level modules depend on lower-level abstractions. Lower-level modules never import from higher-level modules. The data feed layer never imports from the strategy layer. The orchestrator imports from every layer it coordinates, but no layer imports from the orchestrator.

**Principle P-07: Interfaces Are Contracts**
A public method signature is a promise to every caller. Once published and used, it cannot change without a formal interface version change. Callers must never be surprised by a behavioural change in a dependency they did not modify.

**Principle P-08: Test Drives Confidence**
A component is not complete until it has tests that demonstrate correct behaviour, failure behaviour, and edge-case behaviour. Untested code is unverified speculation.

**Principle P-09: Observability Is Built In**
Observability is not added after the fact. Every module that performs a consequential action logs it at the appropriate level. Every layer records its timing. Every error carries context.

**Principle P-10: Standards Evolve Through Process**
These standards are not immutable. As the system evolves, standards may be updated. But they are updated through a deliberate amendment process — documented, justified, and signed off by the Human Principal — not by individuals making local exceptions.

---

### 1.3 The Engineering Quality Hierarchy

The following hierarchy governs trade-offs. When two qualities conflict, the higher-priority quality wins.

| Priority | Quality | Rationale |
|---|---|---|
| 1 | **Safety** | Capital preservation; no harm from system error |
| 2 | **Correctness** | The system does what it is supposed to do |
| 3 | **Reliability** | The system does it consistently under all conditions |
| 4 | **Security** | The system cannot be misused or exploited |
| 5 | **Observability** | All behaviour is traceable |
| 6 | **Maintainability** | The system can be modified safely |
| 7 | **Performance** | The system does it efficiently |
| 8 | **Simplicity** | The system is as simple as possible |

---

### 1.4 Anti-Goals

These are explicitly excluded from the purpose of these standards:

| Anti-Goal | Reason Excluded |
|---|---|
| Maximising feature velocity at the expense of quality | Defects in a trading system have real monetary cost |
| Enforcing a single "correct" algorithmic approach | Strategy diversity is intentional; standards govern structure, not intelligence |
| Prescribing every implementation detail | Standards govern shape and interface; implementation is the engineer's domain |
| Creating bureaucratic friction for trivial changes | Standards apply proportionally; a 3-line bug fix does not require a design review |
| Preventing all future refactoring | Standards protect interfaces and invariants; internal refactoring within a module is permitted |

---

### 1.5 Standards Enforcement Levels

Not all standards carry the same enforcement weight. The following levels apply:

| Level | Label | Description | Violation Consequence |
|---|---|---|---|
| L1 | **MANDATORY** | Non-negotiable; always applied | Code review failure; deployment blocked |
| L2 | **REQUIRED** | Applied unless formally waived with documented justification | Code review comment; justification on record |
| L3 | **RECOMMENDED** | Best practice; deviation noted and explained | Code review note; no blocking |
| L4 | **ADVISORY** | Guidance only; no enforcement | Informational |

Each standard in this document is tagged with its enforcement level. Where no tag is given, the standard is MANDATORY.

---

### 1.6 Relationship to Governing Documents

| Document | Role | How It Relates |
|---|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority | IIOS governs cognition and behaviour; this document governs engineering execution |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering architecture | Blueprint defines layer structure; this document defines standards within and across layers |
| `ARCHITECTURE.md` | Technical architecture reference | Architecture defines module positions; this document governs how modules are built |
| `copilot-instructions.md` | Operational procedures | Operational procedures for deployment; this document governs development practices |
| `config.py` | Runtime configuration authority | Configuration values; this document governs how configuration is managed |

---
## PART II — REPOSITORY STANDARDS

### 2.0 Overview

Repository structure is not merely a folder convention — it is the physical embodiment of the system's architectural boundaries. A repository that is well-organised communicates ownership, dependencies, and responsibility at a glance. A disorganised repository is a symptom of unclear thinking and produces unclear code.

---

### 2.1 Top-Level Repository Organisation

The workspace root contains exactly the following categories of artefact. No other top-level files or folders are created without a formal decision record.

| Path | Category | Owner Layer | Purpose |
|---|---|---|---|
| `config.py` | Configuration | All layers | Master runtime configuration; single source of truth |
| `main.py` | Entry point | ControlTower | Process entry; scheduler start; signal handling |
| `requirements.txt` | Dependency manifest | All layers | Python package dependencies; pinned versions |
| `Dockerfile` | Container spec | Infrastructure | Build specification for ai-trading-brain container |
| `docker-compose.yml` | Orchestration spec | Infrastructure | Container topology; volume mounts; health checks |
| `ARCHITECTURE.md` | Architecture doc | All | Technical architecture reference |
| `data/` | Runtime data | All | SQLite databases; CSV journals; evolved strategies; logs |
| `global_intelligence/` | Layer 1 module | GlobalIntelligence | Global market data acquisition |
| `market_intelligence/` | Layer 2 module | MarketIntelligence | Regime classification; continuous scan |
| `meta_learning/` | Layer 3 module | MetaLearning | kNN strategy weight prediction |
| `opportunity_engine/` | Layer 4 module | OpportunityEngine | Equity scanner; opportunity scoring |
| `strategy_lab/` | Layer 5 module | StrategyLab | Strategy generation; backtesting; evolution |
| `capital_risk_engine/` | Layer 6 module | CapitalRiskEngine | Position sizing; Kelly fraction |
| `risk_control/` | Layer 7 module | RiskControl | Risk approval; portfolio allocation; stress testing |
| `market_simulation/` | Layer 8 module | MarketSimulation | Monte Carlo; scenario modelling |
| `risk_guardian/` | Layer 9 module | RiskGuardian | Kill-switch; monitoring loop |
| `debate_and_decision/` | Layer 10 module | DebateAndDecision | 5-agent debate; conviction threshold |
| `execution_engine/` | Layer 11 module | ExecutionEngine | Order management; broker adapters |
| `trade_monitoring/` | Layer 12 module | TradeMonitoring | Position monitoring; stop enforcement |
| `learning_system/` | Layer 13 module | LearningSystem | Outcome attribution; lesson extraction |
| `performance_analytics/` | Layer 14 module | PerformanceAnalytics | Drawdown analysis; walk-forward testing |
| `research_lab/` | Layer 15 module | ResearchLab | Strategy promotion gates |
| `validation_engine/` | Layer 16 module | ValidationEngine | 6-stage validation pipeline |
| `system_monitor/` | Layer 17 module | ControlTower | Timing; telemetry; EventBus |
| `orchestrator/` | Coordinator | ControlTower | Scheduler; cycle coordination |
| `data_feeds/` | Infrastructure | All | Feed adapters; feed manager singleton |
| `notifications/` | Infrastructure | ControlTower | Telegram bot; alert delivery |
| `scripts/` | Utilities | Infrastructure | Autostart; setup; maintenance scripts |
| `tests/` | Test suite | All | All test types organised by module |
| `.github/` | CI/CD | Infrastructure | GitHub Actions; skills; deployment workflows |

---

### 2.2 Layer Package Structure Standard

Every layer package must follow this internal structure:

```
<layer_name>/
├── __init__.py              # Public API only — exports the layer's public classes
├── <primary_class>.py       # The layer's primary agent or engine
├── <secondary_class>.py     # Supporting agents (may be multiple)
└── README.md                # Layer summary: responsibility, interfaces, dependencies
```

**Rules:**
- `__init__.py` exports **only** what external layers are permitted to import
- Implementation details are not exported from `__init__.py`
- A layer with more than 8 Python files should be re-evaluated for splitting

---

### 2.3 Folder Ownership Rules

Every folder in the repository has exactly one owning layer. The owning layer is the only layer permitted to modify files in that folder without cross-layer review.

| Folder | Owning Layer | Cross-layer Modification Rule |
|---|---|---|
| `global_intelligence/` | Layer 1 | Layers 2–17 may not add files without Layer 1 owner review |
| `risk_guardian/` | Layer 9 | **PROTECTED** — Human Principal approval required for any change |
| `strategy_lab/evolved_strategies/` | Layer 5 | System-generated only; no manual edits |
| `data/` | All (read); Layer 11 (write journals) | Schema changes require migration plan |
| `config.py` | All | Changes require full regression test cycle |
| `orchestrator/` | Layer 17 | Changes require review of all layer touch-points |
| `tests/` | All | Each module owns its own test subdirectory |

---

### 2.4 File Organisation Standards

| Standard | Rule | Enforcement |
|---|---|---|
| **Single class per file** | Each Python file contains at most one primary class | MANDATORY (L1) |
| **File matches class name** | `order_manager.py` contains `OrderManager` | MANDATORY (L1) |
| **No utility dumping** | `utils.py` files are prohibited; utilities belong in named modules | MANDATORY (L1) |
| **No god files** | No single file exceeds 600 lines | REQUIRED (L2) |
| **Imports at top** | All imports appear at the top of the file, not inside functions | MANDATORY (L1) |
| **No wildcard imports** | `from module import *` is prohibited | MANDATORY (L1) |
| **Alphabetical imports** | Within each import group, names are alphabetically ordered | RECOMMENDED (L3) |
| **Import groups** | Standard library → Third-party → Internal; separated by blank lines | REQUIRED (L2) |
| **Circular imports prohibited** | No two modules may import each other, directly or transitively | MANDATORY (L1) |

---

### 2.5 Maximum File Size Recommendations

| File Type | Soft Limit | Hard Limit | Action When Exceeded |
|---|---|---|---|
| Python module (`.py`) | 400 lines | 600 lines | Split into sub-modules; document rationale if over 600 |
| Configuration file (`config.py`) | 200 lines | 350 lines | Extract section to named config sub-file |
| Test file | 500 lines | 800 lines | Split by test class or feature group |
| Markdown documentation | 3,000 lines | No limit | Add TOC with anchor links for navigation |
| Shell/PowerShell script | 150 lines | 250 lines | Extract functions to shared script library |
| JSON strategy file | 200 lines | 500 lines | Review for over-parameterisation |
| Docker Compose file | 100 lines | 200 lines | Extract service blocks to override files |

---

### 2.6 Module Boundary Rules

Module boundaries are architectural invariants. They define which layers may depend on which.

| Rule | Description | Violation Consequence |
|---|---|---|
| **No skip imports** | A module in Layer N may not import from Layer N+2 or higher | Architecture violation; immediate revert |
| **No reverse imports** | A module in Layer N may not import from Layer N-1 or lower | Architecture violation; immediate revert |
| **Singleton access only** | Singleton objects are accessed via their getter function, never by direct instantiation | Code review failure |
| **Interface not implementation** | Modules depend on public interfaces (exported from `__init__.py`), not on internal classes | Code review failure |
| **Config via config.py** | All runtime parameters are read from `config.py`; modules never read environment variables directly | MANDATORY |
| **Data transfer via objects** | Modules exchange data via defined object types, never via dict, tuple, or raw string | REQUIRED |

---

### 2.7 Dependency Management Rules

| Rule | Detail | Enforcement Level |
|---|---|---|
| **Pin all versions** | `requirements.txt` specifies exact versions (`package==1.2.3`), not ranges | MANDATORY |
| **No unused dependencies** | Every package in `requirements.txt` must be imported in at least one production module | REQUIRED |
| **Dependency audit on add** | Adding a new dependency requires: licence check, security scan, compatibility check | MANDATORY |
| **No transitive dependency reliance** | Only directly declared dependencies are imported; transitive packages are not relied upon | MANDATORY |
| **Separate dev dependencies** | Test-only and tooling packages are kept in `requirements-dev.txt`, not `requirements.txt` | REQUIRED |
| **Review on security advisory** | Any package with a published CVE must be evaluated within 48 hours | MANDATORY |
| **Python version compatibility** | All packages must support the project's declared Python version (3.14+) | MANDATORY |

---

### 2.8 Repository Cleanliness Standards

| Standard | Rule | Enforcement |
|---|---|---|
| **No committed secrets** | API keys, tokens, passwords, and certificates never appear in any committed file | MANDATORY |
| **No binary files in source** | Compiled bytecode, `.pyc`, `.pyo`, and `.pyd` files are gitignored | MANDATORY |
| **No IDE project files** | `.vscode/settings.json`, `.idea/`, etc. are gitignored (shared launch configs excepted) | REQUIRED |
| **No debug scripts in root** | Temporary debug scripts (`debug_*.py`, `check_*.py`) are cleaned up before merge | REQUIRED |
| **No commented-out production code** | Disabled code is deleted; git history preserves it | REQUIRED |
| **`.gitignore` maintained** | `.gitignore` is reviewed quarterly; all auto-generated paths are covered | REQUIRED |
| **No large data files** | Files > 10 MB are excluded from the repository and stored externally | MANDATORY |

---

### 2.9 Archive Policy

When a module, strategy, or component is decommissioned:

| Step | Action |
|---|---|
| 1 | Tag the commit before removal as `archive/<component-name>-<date>` |
| 2 | Record the removal in the Engineering Decision Register |
| 3 | Remove all imports of the decommissioned component from other modules |
| 4 | Remove the component's test suite |
| 5 | Remove the component's entry from `requirements.txt` if unique |
| 6 | Update `ARCHITECTURE.md` and `copilot-instructions.md` to reflect the removal |
| 7 | Deploy and verify no broken imports in production |

**Archive is never "move to an `archive/` folder" within the active repository.** History lives in git, not in dormant subdirectories.

---

### 2.10 Package Responsibility Matrix

Each package has one and only one primary responsibility. This matrix documents the canonical responsibility and its boundaries.

| Package | Primary Responsibility | What It Must NOT Do |
|---|---|---|
| `data_feeds` | Acquire raw market data from external sources | Parse, interpret, or act on data |
| `global_intelligence` | Produce GlobalSnapshot from raw global data | Make trading decisions |
| `market_intelligence` | Classify market regime and scan sector data | Generate hypotheses |
| `meta_learning` | Weight strategies by regime-outcome learning | Execute trades |
| `opportunity_engine` | Rank instruments by signal strength | Approve or reject hypotheses |
| `strategy_lab` | Generate and evolve trading hypotheses | Assess portfolio risk |
| `capital_risk_engine` | Compute position sizes | Approve orders |
| `risk_control` | Approve or reject hypotheses based on risk | Generate signals |
| `market_simulation` | Simulate portfolio outcomes | Modify live positions |
| `risk_guardian` | Enforce kill-switch conditions | Make trading decisions |
| `debate_and_decision` | Produce conviction-weighted decision records | Submit orders |
| `execution_engine` | Submit and track orders | Assess risk or generate signals |
| `trade_monitoring` | Monitor open positions for stop/target hits | Generate new hypotheses |
| `learning_system` | Extract lessons from outcomes | Modify active positions |
| `performance_analytics` | Analyse historical performance | Make current-cycle decisions |
| `research_lab` | Gate strategy promotion | Execute live strategies |
| `validation_engine` | Run the 6-stage validation pipeline | Approve live orders |
| `system_monitor` | Record timing and emit alerts | Make trading decisions |
| `orchestrator` | Coordinate the cognitive cycle sequence | Implement business logic |
| `notifications` | Deliver alerts to Human Principal | Store state or make decisions |

---
## PART III — NAMING STANDARDS

### 3.0 Overview

Consistent naming is the single most powerful tool for making a codebase comprehensible. When names are inconsistent, engineers must read implementation details to understand intent. When names are consistent, the code explains itself. These naming standards apply without exception to all new artefacts and must be applied retroactively when a file is substantially modified.

**General Naming Principles:**
- Names reveal intent — a name should tell you what something IS or what it DOES, not how it does it
- Names are unambiguous — no two artefacts in the same scope share a name or a name so similar it causes confusion
- Names are pronounceable — abbreviations are avoided except for established domain terms (PnL, VIX, kNN, OOS)
- Names are searchable — single-letter names and generic names (`data`, `result`, `tmp`) are prohibited in module scope

---

### 3.1 Folder and Package Naming

| Context | Convention | Example | Anti-pattern |
|---|---|---|---|
| Layer package folder | `snake_case` | `market_intelligence/` | `MarketIntelligence/`, `market-intelligence/` |
| Sub-package folder | `snake_case` | `strategy_lab/agents/` | `agents-lib/` |
| Test folder | `tests/<package_name>/` | `tests/market_intelligence/` | `test_market_intelligence/` |
| Script folder | `scripts/` (flat; no sub-folders) | `scripts/autostart.bat` | `scripts/windows/autostart.bat` |
| Data folder | `data/` (root) | `data/trading_brain.db` | `data/db/trading_brain.db` |

---

### 3.2 File Naming

| File Type | Convention | Example | Anti-pattern |
|---|---|---|---|
| Python module | `snake_case.py` | `order_manager.py` | `OrderManager.py`, `ordermanager.py` |
| Python entry point | `snake_case.py` | `main.py` | `Main.py`, `run.py` |
| Python test file | `test_<module_name>.py` | `test_order_manager.py` | `OrderManagerTest.py` |
| Configuration | `snake_case.py` or `snake_case.yaml` | `config.py` | `Config.py`, `configuration.yaml` |
| Markdown doc | `UPPER_SNAKE_CASE.md` | `ARCHITECTURE.md` | `architecture.md`, `Architecture.md` |
| Docker file | `Dockerfile` (no extension) | `Dockerfile` | `dockerfile`, `Dockerfile.prod` |
| Compose file | `docker-compose.yml` | `docker-compose.yml` | `DockerCompose.yml` |
| Shell script | `snake_case.sh` or `snake_case.bat` | `autostart.bat` | `AutoStart.bat` |
| JSON strategy | `snake_case.json` | `momentum_breakout_v2.json` | `MomentumBreakout_V2.json` |
| CSV journal | `snake_case.csv` | `paper_trades.csv` | `PaperTrades.csv` |
| SQLite database | `snake_case.db` | `trading_brain.db` | `TradingBrain.db` |
| Log file | `<component>_<date>.log` | `trading_brain_2026-07-02.log` | `log.txt`, `errors.log` |
| Backup file | `<original>_backup_<datetime>.db` | `trading_brain_backup_20260702_163000.db` | `trading_brain.bak` |
| Report file | `<type>_report_<date>.md` | `eod_report_20260702.md` | `report.md` |

---

### 3.3 Python Class Naming

| Class Category | Convention | Example | Anti-pattern |
|---|---|---|---|
| Primary agent class | `PascalCase` + `AI` suffix | `GlobalDataAI`, `RiskManagerAI` | `GlobalData`, `global_data_ai` |
| Engine/controller class | `PascalCase` + `Engine` or `Controller` | `MarketIntelligenceEngine`, `MetaStrategyController` | `market_engine`, `StrategyCtrl` |
| Monitor class | `PascalCase` + `Monitor` | `TradeMonitor`, `MarketMonitor` | `Watcher`, `PositionWatcher` |
| Data object (typed dict / dataclass) | `PascalCase` | `GlobalSnapshot`, `RegimeSignal`, `DecisionRecord` | `global_snapshot`, `REGIME_SIGNAL` |
| Broker adapter | `PascalCase` + `Broker` | `ZerodhaBroker`, `DhanBroker` | `ZerodhaAdapter` |
| Feed adapter | `PascalCase` + `Feed` | `YahooFeed`, `DhanFeed` | `YahooDataSource` |
| Exception class | `PascalCase` + `Error` or `Exception` | `RiskApprovalError`, `FeedTimeoutException` | `RiskException`, `Error1` |
| Enum class | `PascalCase` | `RegimeType`, `OrderStatus`, `AlertSeverity` | `regime_type`, `ORDER_STATUS` |
| Abstract base class | `PascalCase` + `Base` prefix | `BaseFeed`, `BaseAgent` | `FeedInterface`, `AbstractFeed` |

---

### 3.4 Python Function and Method Naming

| Function Category | Convention | Example | Anti-pattern |
|---|---|---|---|
| Public method | `snake_case` verb phrase | `get_quote()`, `fetch()`, `submit()` | `getQuote()`, `Get_Quote()` |
| Private method | `_snake_case` (single underscore) | `_validate_approval()`, `_compute_kelly()` | `__validate()`, `__privateMethod()` |
| Property getter | `snake_case` noun | `@property def conviction_score` | `getConvictionScore()` |
| Boolean method | `is_` or `has_` prefix | `is_market_open()`, `has_valid_quote()` | `check_market()`, `open()` |
| Factory method | `create_` or `from_` prefix | `create_order_record()`, `from_csv_row()` | `make_record()`, `build()` |
| Async method | `snake_case` + `_async` suffix | `fetch_async()` | `asyncFetch()` |
| Generator | `snake_case` + `_iter` suffix | `scan_results_iter()` | `generate_results()` |
| Context manager | `snake_case` | `time_layer()` | `TimerContext()` |
| Singleton getter | `get_<class_name_snake>()` | `get_feed_manager()`, `get_telegram_bot()` | `FeedManager.instance()` |

---

### 3.5 Python Variable Naming

| Variable Category | Convention | Example | Anti-pattern |
|---|---|---|---|
| Local variable | `snake_case` noun | `regime_signal`, `position_size` | `rs`, `pos`, `regimeSignal` |
| Loop variable | `snake_case` (meaningful) | `for strategy_id in active_strategies` | `for i in strategies` |
| Boolean variable | `is_` or `has_` prefix | `is_stale`, `has_approval` | `stale`, `approved_flag` |
| Accumulator | `snake_case` noun | `total_pnl`, `win_count` | `sum`, `counter` |
| Temporary / throwaway | Never single letter (except pure math) | Exception: `for i in range(n)` in numeric loops | `x`, `t`, `d` for domain objects |
| Instance attribute | `self.snake_case` | `self.kill_switch_active` | `self.killSwitchActive` |
| Class constant | `UPPER_SNAKE_CASE` defined at class level | `_DAILY_LOSS_LIMIT = 0.02` | `daily_loss_limit`, `DailyLossLimit` |
| Module-level constant | `UPPER_SNAKE_CASE` | `LAYER_LATENCY_WARN_MS = 2000` | `layer_latency_warn` |
| Type alias | `PascalCase` | `StrategyWeightMap = Dict[str, float]` | `strategy_weight_map_type` |

---

### 3.6 Python Constant Naming Rules (Critical)

Constants are a known source of bugs in this codebase (see patterns.md). These rules are MANDATORY.

| Rule | Detail |
|---|---|
| **Class-level constants use `self.`** | Constants defined as class attributes are ALWAYS accessed as `self.CONSTANT_NAME` inside methods |
| **Module-level constants are bare** | Constants defined at module level (outside any class) are accessed by bare name |
| **No mixed-scope confusion** | Never define a constant at class level and access it as a bare name inside a method |
| **Post-addition audit** | After adding any new constant, grep for all usages and confirm the correct scope access pattern |
| **Prefer module level** | When a constant is used by only one class, prefer module-level to class-level to avoid self. confusion |

---

### 3.7 Enum Naming

| Element | Convention | Example |
|---|---|---|
| Enum class name | `PascalCase` | `RegimeType` |
| Enum member | `UPPER_SNAKE_CASE` | `RegimeType.TRENDING_BULLISH` |
| Enum value | Meaningful string or int | `RegimeType.TRENDING_BULLISH = "TRENDING_BULLISH"` |

---

### 3.8 Environment Variable Naming

| Variable Category | Convention | Example | Anti-pattern |
|---|---|---|---|
| API credentials | `<SERVICE>_API_KEY` | `DHAN_API_KEY` | `dhan_key`, `API_KEY_DHAN` |
| Client identifiers | `<SERVICE>_CLIENT_ID` | `DHAN_CLIENT_ID` | `CLIENT_ID` |
| Bot tokens | `<SERVICE>_BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` | `BOT_TOKEN`, `TELEGRAM_TOKEN` |
| Chat identifiers | `<SERVICE>_CHAT_ID` | `TELEGRAM_CHAT_ID` | `CHAT_ID` |
| Runtime mode flags | `UPPER_SNAKE_CASE` | `PAPER_TRADING`, `VPS_HOSTNAME` | `paper_trading`, `PaperMode` |
| Feature toggles | `FEATURE_<NAME>` | `FEATURE_LIVE_ORDERS` | `ENABLE_LIVE` |
| Port numbers | `<SERVICE>_PORT` | `DASHBOARD_PORT` | `PORT`, `STREAMLIT_PORT` |

---

### 3.9 Configuration Keys (`config.py`)

| Key Category | Convention | Example |
|---|---|---|
| Boolean flags | `UPPER_SNAKE_CASE` | `PAPER_TRADING`, `TELEGRAM_ENABLED` |
| Numeric thresholds | `UPPER_SNAKE_CASE` | `DAILY_LOSS_LIMIT`, `CONVICTION_THRESHOLD` |
| String identifiers | `UPPER_SNAKE_CASE` | `VPS_HOSTNAME`, `DB_PATH` |
| Time durations (seconds) | `<NAME>_INTERVAL_SEC` | `CONTINUOUS_SCAN_INTERVAL_SEC` |
| Rate limits | `<NAME>_RATE` | `MAX_ORDERS_PER_MINUTE_RATE` |
| Lists / collections | `UPPER_SNAKE_CASE` | `EQUITY_UNIVERSE`, `SCHEDULE` |

---

### 3.10 Database Naming

| Object | Convention | Example | Anti-pattern |
|---|---|---|---|
| Table name | `snake_case` (plural) | `decisions`, `orders`, `telemetry_records` | `Decision`, `tbl_orders`, `Orders` |
| Column name | `snake_case` | `decision_id`, `approved_at`, `conviction_score` | `decisionID`, `ApprovedAt` |
| Primary key | `<table_singular>_id` | `decision_id`, `order_id` | `id`, `pk`, `key` |
| Foreign key | `<referenced_table_singular>_id` | `decision_id` (in `orders` table) | `fk_decision`, `decision_ref` |
| Index | `idx_<table>_<column>` | `idx_orders_submitted_at` | `order_index`, `idx1` |
| Unique constraint | `uq_<table>_<columns>` | `uq_orders_order_id` | `unique_constraint` |
| View | `vw_<purpose>` | `vw_daily_performance` | `daily_view`, `performance` |
| Timestamp columns | `<event>_at` (UTC) | `created_at`, `approved_at`, `closed_at` | `timestamp`, `date`, `time` |
| Boolean columns | `is_<state>` | `is_approved`, `is_stale` | `approved`, `stale_flag` |
| Soft delete | `deleted_at` (nullable timestamp) | `deleted_at` | `is_deleted`, `active` |

---

### 3.11 Docker Naming

| Object | Convention | Example | Anti-pattern |
|---|---|---|---|
| Image name | `<project>-<component>` (lowercase, hyphens) | `ai-trading-brain`, `trading-dashboard` | `AiTradingBrain`, `trading_brain_img` |
| Container name | Same as image name | `ai-trading-brain` | `brain`, `container1` |
| Volume name | `<project>-<purpose>` | `trading-data`, `trading-config` | `data`, `vol1` |
| Network name | `<project>-net` | `trading-net` | `default`, `my_network` |
| Service name in compose | Matches container name | `ai-trading-brain` | `brain`, `app` |

---

### 3.12 Git Naming

| Object | Convention | Example | Anti-pattern |
|---|---|---|---|
| Main branch | `main` | `main` | `master`, `trunk` |
| Feature branch | `feature/<short-description>` | `feature/add-vix-kill-threshold` | `feature1`, `johns-fix` |
| Bug fix branch | `fix/<short-description>` | `fix/paper-trade-csv-append` | `bugfix`, `fix1` |
| Hotfix branch | `hotfix/<short-description>` | `hotfix/kill-switch-not-triggering` | `urgent`, `prod-fix` |
| Release branch | `release/<version>` | `release/1.2.0` | `release`, `v1.2` |
| Git tag (release) | `v<major>.<minor>.<patch>` | `v1.2.3` | `release-1.2.3`, `1.2.3` |
| Git tag (archive) | `archive/<component>-<date>` | `archive/legacy-broker-20260301` | `old-broker` |
| Commit message subject | Imperative present tense | `Add VIX kill threshold to RiskGuardian` | `Added VIX threshold`, `fix stuff` |

---

### 3.13 Log File Naming

| Log Type | Convention | Rotation | Example |
|---|---|---|---|
| Main application log | `trading_brain_<YYYY-MM-DD>.log` | Daily | `trading_brain_2026-07-02.log` |
| Error-only log | `trading_brain_errors_<YYYY-MM-DD>.log` | Daily | `trading_brain_errors_2026-07-02.log` |
| Audit log | `audit_<YYYY-MM-DD>.log` | Daily | `audit_2026-07-02.log` |
| Performance log | `perf_<YYYY-MM-DD>.log` | Daily | `perf_2026-07-02.log` |
| Access log (dashboard) | `dashboard_access_<YYYY-MM-DD>.log` | Daily | `dashboard_access_2026-07-02.log` |

---

### 3.14 Report and Backup File Naming

| File Type | Convention | Example |
|---|---|---|
| EOD report | `eod_report_<YYYY-MM-DD>.md` | `eod_report_2026-07-02.md` |
| Strategy performance report | `strategy_performance_<YYYY-MM-DD>.md` | `strategy_performance_2026-07-02.md` |
| Database backup | `<db_name>_backup_<YYYYMMdd_HHmmss>.db` | `trading_brain_backup_20260702_163000.db` |
| Configuration snapshot | `config_snapshot_<YYYYMMdd_HHmmss>.py` | `config_snapshot_20260702_163000.py` |

---
## PART IV — CODING STANDARDS

### 4.0 Overview

Coding standards govern how source code is written — not what algorithm it implements. The goal is not to produce identical-looking code, but to produce code that any engineer in this project can read, understand, and safely modify. Standards apply at the module, function, and statement level.

---

### 4.1 SOLID Principles Application

| Principle | Full Name | Application in AI Trading Brain |
|---|---|---|
| **S** | Single Responsibility | Each class/module does one thing: `RiskManagerAI` assesses risk; it does not generate signals or submit orders |
| **O** | Open/Closed | Add new functionality via new classes or methods; do not modify working, tested classes to add unrelated features |
| **L** | Liskov Substitution | Feed adapters (`YahooFeed`, `DhanFeed`) are interchangeable through `BaseFeed` without callers noticing the difference |
| **I** | Interface Segregation | `BaseFeed` exposes only `get_quote()`, `get_multiple_quotes()`, `get_history()` — callers are not forced to depend on unused methods |
| **D** | Dependency Inversion | `data_feed_manager` depends on `BaseFeed` abstraction, not on `YahooFeed` directly; new feed adapters plug in without modifying the manager |

---

### 4.2 DRY — Don't Repeat Yourself

| Rule | Detail | Enforcement |
|---|---|---|
| No duplicated business logic | The same business rule (e.g., conviction threshold 6.5) appears in exactly one place (`config.py`) | MANDATORY |
| No copy-paste between modules | If the same 5+ lines appear in two modules, they must be extracted to a shared utility | REQUIRED |
| Configuration values centralised | No threshold, limit, or flag value is hardcoded more than once | MANDATORY |
| No duplicated test setup | Test fixtures and setup code are shared via pytest fixtures, not duplicated | REQUIRED |

---

### 4.3 KISS — Keep It Simple, Straightforward

| Rule | Detail |
|---|---|
| Prefer the simplest correct implementation | If two implementations both pass all tests, choose the shorter, clearer one |
| No pre-emptive abstraction | Do not create abstract base classes, factories, or registries until at least two concrete implementations exist |
| Avoid nested complexity | Functions with cyclomatic complexity > 10 must be refactored into smaller functions |
| Avoid clever one-liners | Readable multi-line code is preferred over a single clever expression that requires thought to parse |
| No over-engineering | Do not build for a future requirement that does not exist today |

---

### 4.4 YAGNI — You Aren't Gonna Need It

| Anti-pattern | What to Do Instead |
|---|---|
| Adding a parameter "for future use" | Add the parameter when the use case exists |
| Creating a plugin architecture when there is one plugin | Use direct code; refactor when the second plugin appears |
| Building a generic framework when there is one use case | Build the specific solution; generalise if a second use case appears |
| Adding configuration options for hypothetical scenarios | Add configuration when the scenario is real |
| Creating a base class for a class that has no subclasses | Create a concrete class; extract base when subclasses appear |

---

### 4.5 Clean Architecture Principles

The AI Trading Brain uses a layered architecture where **outer layers depend on inner layers, never the reverse**.

| Layer Position | May Depend On | May NOT Depend On |
|---|---|---|
| ControlTower (Layer 17) | All layers | Nothing (it orchestrates all) |
| Execution (Layer 11) | Layers 1–10 | Layers 12–17 (except kill-switch from Layer 9) |
| Strategy (Layer 5) | Layers 1–4 | Layers 6–17 |
| Data Feeds (Infrastructure) | External APIs only | Any layer module |
| Configuration (`config.py`) | Python stdlib only | Any layer module |

---

### 4.6 Error Handling Standards

| Rule | Detail | Enforcement Level |
|---|---|---|
| **Catch specific exceptions** | Never catch bare `Exception` unless at the top-level handler | MANDATORY |
| **Never silently swallow exceptions** | Every `except` block logs the exception at WARNING or ERROR level | MANDATORY |
| **Log with context** | `logger.exception("message", extra={"layer": "...", "context": ...})` — not `logger.error(str(e))` | REQUIRED |
| **Fail-safe on catch** | After catching an exception in a critical path, return the safe default (e.g., REJECTED, stale data) | MANDATORY |
| **Re-raise when appropriate** | If a calling layer must know about the exception, re-raise after logging | REQUIRED |
| **Custom exception types** | Domain errors have domain exception classes; never raise generic `ValueError` for business logic errors | REQUIRED |
| **No bare `raise`** | Except when re-raising inside an `except` block; bare `raise` is never used outside `except` | MANDATORY |
| **Exception messages are actionable** | Exception messages tell the engineer what happened AND what they should check | REQUIRED |

**Exception Hierarchy for AI Trading Brain:**

| Exception Class | Parent | When Used |
|---|---|---|
| `TradingBrainError` | `Exception` | Base for all custom exceptions |
| `FeedError` | `TradingBrainError` | Any data feed failure |
| `FeedTimeoutError` | `FeedError` | Feed request exceeded timeout |
| `RiskApprovalError` | `TradingBrainError` | Risk system returned REJECTED unexpectedly |
| `KillSwitchActiveError` | `TradingBrainError` | Order attempted when kill-switch is active |
| `DecisionRecordMissingError` | `TradingBrainError` | Order attempted without corresponding decision record |
| `ConfigValidationError` | `TradingBrainError` | Config.py fails validation at startup |
| `DatabaseError` | `TradingBrainError` | SQLite operation fails |
| `LearningQueueOverflowError` | `TradingBrainError` | Learning queue capacity exceeded |

---

### 4.7 Null and None Handling

| Rule | Detail | Enforcement |
|---|---|---|
| **Explicit None checks** | Use `if x is None` — never `if not x` for objects that may be falsy but not None | MANDATORY |
| **Never pass None for required arguments** | If an argument can be None, the function signature must declare `Optional[T]` | REQUIRED |
| **Document None returns** | If a function can return None, the return type is `Optional[T]` and the docstring explains when None is returned | REQUIRED |
| **No attribute access on potential None** | Check for None before accessing `.attribute` on a value that may be None | MANDATORY |
| **Fail-safe None defaults** | When a None value means "unknown", the system defaults to the safe state (reject, block, stale) | MANDATORY |

---

### 4.8 Configuration Management Standards

| Rule | Detail |
|---|---|
| **Single config file** | All runtime configuration lives in `config.py`; no JSON, YAML, or INI config files |
| **No environment variable reads in modules** | Modules read from `config.py`; `config.py` reads from environment variables at startup |
| **No hardcoded thresholds in modules** | `CONVICTION_THRESHOLD = 6.5` in `config.py`; referenced as `config.CONVICTION_THRESHOLD` |
| **Config loaded at startup** | `config.py` is imported at module import time; no lazy loading |
| **Config validation at startup** | A `validate_config()` function confirms all required keys exist and have valid types/ranges |
| **Config changes require full regression** | After any change to `config.py`, the full integration test suite must pass |
| **Sensitive values in environment** | `config.py` reads secrets from environment variables; never hardcodes them |

---

### 4.9 Resource Management Standards

| Resource | Standard | Detail |
|---|---|---|
| **Database connections** | One connection per thread | Never share SQLite connections across threads; use WAL mode |
| **File handles** | Always use `with` statement | `with open(path, 'a') as f:` — never `f = open(path)` without guaranteed close |
| **Network connections** | Explicit timeout | All outbound network requests have a timeout (default 8 seconds for feeds) |
| **Thread lifecycle** | Daemon threads only for background | All background threads (`daemon=True`); main thread never joins background threads |
| **Memory** | No infinite list accumulation | Bounded queues (`queue.Queue(maxsize=1000)`); rolling windows for time-series data |
| **Locks** | Held for minimum duration | Acquire lock, perform atomic operation, release; never hold lock across I/O |
| **Temporary files** | Use `tempfile` module | Never create temp files in the working directory; clean up in `finally` |

---

### 4.10 Performance Guidelines

| Guideline | Target | Detail |
|---|---|---|
| **Full cognitive cycle** | < 172ms average | Protect this baseline; re-benchmark after every change to the critical path |
| **Single layer timing** | < 2,000ms WARN, < 5,000ms CRIT | Monitored by `SystemMonitor.time_layer()` |
| **Cache hot paths** | < 5ms on cache hit | `GlobalDataAI` and `MarketIntelligenceEngine` cache their results |
| **No blocking in callbacks** | < 1ms | EventBus subscriber callbacks must not perform I/O or computation |
| **Batch external calls** | Use `get_multiple_quotes()` | Never call `get_quote()` in a loop; batch with `get_multiple_quotes()` |
| **Lazy initialisation** | Allowed for non-critical paths | Singletons are eagerly initialised at startup; strategy data may be lazily loaded |
| **No synchronous sleep in main thread** | Prohibited | Use APScheduler for timed delays; `time.sleep()` is prohibited in any non-test code |
| **Profile before optimising** | Required | Never optimise without a measured baseline; optimise the identified bottleneck |

---

### 4.11 Concurrency Standards

| Rule | Detail | Enforcement |
|---|---|---|
| **`threading.Event` for flags** | Binary flags shared across threads use `threading.Event`, not raw booleans | MANDATORY |
| **`threading.Lock` for mutable shared state** | Any dict, list, or object modified by multiple threads is protected by a `Lock` | MANDATORY |
| **Lock acquisition order** | When acquiring multiple locks, always acquire in the same global order to prevent deadlocks | MANDATORY |
| **No lock held across I/O** | Release lock before any file, network, or database operation | MANDATORY |
| **`queue.Queue` for inter-thread communication** | Threads communicate via `queue.Queue`, not via shared lists | REQUIRED |
| **Non-blocking puts** | `queue.Queue.put_nowait()` from main thread; main thread never blocks on queue operations | MANDATORY |
| **Daemon threads for background** | All background threads have `daemon=True` so they exit with the main process | MANDATORY |
| **No thread creation in modules** | Threads are created only by the orchestrator or dedicated monitor classes; not inside business logic | REQUIRED |
| **Thread names for observability** | Every thread is given a meaningful name: `threading.Thread(name="RiskGuardianThread", ...)` | REQUIRED |

---

### 4.12 Thread Safety Checklist

Before submitting any code that introduces shared mutable state, verify:

- [ ] Is the shared object protected by a `threading.Lock` or `threading.RLock`?
- [ ] Is the lock acquired before every read-modify-write operation?
- [ ] Is the lock held for the minimum required duration?
- [ ] Is there no I/O operation while the lock is held?
- [ ] Could this introduce a deadlock with any existing lock? Check acquisition order.
- [ ] If a binary signal is needed, is `threading.Event` used instead of a boolean?
- [ ] If inter-thread data transfer is needed, is `queue.Queue` used?
- [ ] Is the thread named for observability?

---

### 4.13 Input Validation Standards

| Input Source | Validation Rule | Detail |
|---|---|---|
| External market data | Validate at the feed adapter boundary | `data_feed_manager` validates type, range, and completeness before passing to consumers |
| Telegram commands | Validate chat_id before processing | Unknown chat IDs are rejected; no command is processed without identity verification |
| Configuration values | Validate at startup | `validate_config()` checks types and ranges; startup fails on invalid config |
| Evolved strategy JSON | Validate on load | Schema-check all JSON strategy files on startup; reject invalid files |
| CSV trade records | Validate on read | Parse and validate each row; skip malformed rows with WARNING log |
| SQLite query results | Validate before use | Never assume column count or type; use named column access |

---
## PART V — DOCUMENTATION STANDARDS

### 5.0 Overview

Documentation is not an optional afterthought — it is the specification that code must satisfy. Undocumented code is code whose intent is unknown. In a system where understanding intent is the difference between a correct and a catastrophic change, all consequential code must be documented to a mandatory standard.

---

### 5.1 Module-Level Documentation

Every Python module must open with a module docstring. No module is exempt.

**Module docstring required elements:**

| Element | Description | Example |
|---|---|---|
| **Purpose** | One sentence: what this module does | `"""Order management: submits, tracks, and journals all orders."""` |
| **Layer** | Which IIOS layer this module belongs to | `Layer: ExecutionEngine (Layer 11)` |
| **Primary class** | The class exported by this module | `Primary Class: OrderManager` |
| **Key dependencies** | The modules this module directly imports | `Dependencies: config, risk_guardian, data_feeds` |
| **Critical interfaces** | Public methods that must not change signature | `Critical: submit(decision_record, risk_approval_record)` |
| **Threading** | Thread safety characteristics | `Threading: OrderManager._positions_lock protects open_positions dict` |
| **Protected status** | If protected, state the condition | `Protected: Human Principal approval required for kill-switch path changes` |

---

### 5.2 Class-Level Documentation

Every class must have a class docstring at the class definition.

**Class docstring required elements:**

| Element | Description |
|---|---|
| **Responsibility** | Single sentence describing the class's one responsibility |
| **Singleton** | If singleton: state how to access it (getter function name) |
| **State** | List of significant instance variables and what they represent |
| **Thread safety** | Which attributes are protected and by which lock |
| **Lifecycle** | How the class is initialised and (if applicable) shut down |
| **Constitutional articles** | Which IIOS invariants this class directly enforces |

---

### 5.3 Function and Method Documentation

Every public function and every method with non-obvious behaviour must have a docstring.

**Function docstring required elements:**

| Element | Present When | Format |
|---|---|---|
| Summary | Always | One sentence; imperative mood |
| Parameters | Always (if any) | `:param name: description (type)` |
| Returns | Always (if non-void) | `:returns: description (type)` |
| Raises | When exceptions are raised | `:raises ExceptionType: condition` |
| Thread safety | When relevant | `:thread-safe: yes/no — explanation` |
| Side effects | When non-obvious | `:side-effect: writes to CSV / fires EventBus` |
| Timing | For critical-path functions | `:timing: < 5ms on cache hit; < 17ms on fetch` |

**Prohibited docstring patterns:**
- Repeating the function name: `"""get_quote: gets a quote."""` — says nothing new
- Parameter names without descriptions: `""":param symbol:"""` — no type or meaning
- Describing HOW, not WHAT: the docstring describes what the function does, not how

---

### 5.4 Inline Comment Standards

| Rule | Detail |
|---|---|
| **Comment the why, not the what** | Code shows what; comments explain why a non-obvious choice was made |
| **No stale comments** | Comments that no longer match the code must be updated or removed |
| **No commented-out code** | Disabled code is deleted; git history preserves it |
| **No noise comments** | `# increment counter` above `count += 1` adds zero value |
| **Explain every magic number** | Any numeric literal that is not 0 or 1 gets a comment or a named constant |
| **Mark deliberate non-conformance** | `# DELIBERATE: no lock here — single-writer-guaranteed by design` |
| **Mark known limitations** | `# LIMITATION: yfinance rate limit at ~2000 req/hour; batching required` |
| **Mark invariant enforcement** | `# INV-24: kill-switch is inviolable — check before ANY order submission` |

---

### 5.5 Architecture Documentation Standards

Architecture documentation (Markdown files such as ARCHITECTURE.md, ENGINEERING_STANDARDS.md, IIOS) must follow these standards:

| Standard | Rule |
|---|---|
| **Table of Contents** | Every document > 500 lines has a TOC with anchor links |
| **Section numbering** | Sections use decimal numbering: 1.0, 1.1, 2.0, 2.1 |
| **Table for structured data** | Any list of more than 4 related items is presented as a table |
| **Consistent heading levels** | Document title = `#`; Part = `##`; Section = `###`; Sub-section = `####` |
| **Status banner** | Every architecture document opens with a metadata table: title, version, status, date |
| **No passive voice for rules** | Rules use "must", "shall", "is prohibited" — never "should probably consider" |
| **Cross-references** | References to other documents name the document and section explicitly |
| **Version tracking** | Every architecture document has a Document History table |

---

### 5.6 README Standards

Every layer package must contain a `README.md` with the following sections:

| Section | Content |
|---|---|
| **Package Name** | Layer number, name, and one-sentence purpose |
| **Responsibility** | What this package does and what it does NOT do |
| **Primary Exports** | Classes exported from `__init__.py` with brief description |
| **Key Dependencies** | Other packages this package imports |
| **Public Interfaces** | Method signatures that must not change |
| **Threading Model** | Thread this package owns or participates in |
| **Failure Behaviour** | What happens when this package's dependency fails |
| **Constitutional Articles** | IIOS invariants this package enforces |
| **Timing** | Latency budget for this layer |

---

### 5.7 Architecture Decision Record (ADR) Standards

Every significant engineering decision must be recorded as an Architecture Decision Record. Significant decisions include:
- Choosing between two viable architectural approaches
- Deciding to deviate from a stated standard
- Choosing a specific technology, library, or algorithm
- Deciding to protect or deprotect a module
- Introducing a new thread, singleton, or shared state object

**ADR format:**

| Field | Description |
|---|---|
| **Decision ID** | `ED-<sequential-number>` (e.g., ED-025) |
| **Title** | Short descriptive noun phrase |
| **Date** | ISO date (YYYY-MM-DD) |
| **Status** | PROPOSED / ACCEPTED / DEPRECATED / SUPERSEDED |
| **Context** | Why this decision needed to be made |
| **Decision** | What was decided |
| **Alternatives Rejected** | Other options considered and why they were rejected |
| **Rationale** | Full reasoning for the decision |
| **Consequences** | What changes as a result of this decision |
| **Superseded By** | If DEPRECATED/SUPERSEDED: which ADR replaces it |

ADRs are recorded in the Engineering Decision Register in `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md`.

---

### 5.8 Changelog Standards

A `CHANGELOG.md` is maintained at the root of the repository. Every non-trivial commit is recorded with the following format:

```
## [version] — YYYY-MM-DD

### Added
- Description of new feature or capability

### Changed
- Description of changed behaviour

### Fixed
- Description of bug fixed; impact of the bug; how the fix resolves it

### Deprecated
- Description of deprecated behaviour; replacement behaviour

### Removed
- Description of removed code; reason for removal

### Security
- Description of security improvement
```

Each entry must be specific enough that an engineer who was not involved can understand the change from the changelog alone.

---

### 5.9 Release Notes Standards

Release notes are produced for every tagged release and contain:

| Section | Content |
|---|---|
| **Release Version** | Semantic version (e.g., v1.2.3) |
| **Release Date** | ISO date |
| **Summary** | 2–3 sentence summary of the release |
| **New Capabilities** | User-facing additions in plain language |
| **Bug Fixes** | Issues resolved; brief description of impact |
| **Performance Changes** | Any measured latency or throughput changes |
| **Breaking Changes** | Any change that requires operator action |
| **Deployment Notes** | Special steps required for this release |
| **Rollback Instructions** | How to revert if the release fails |
| **Known Issues** | Any unresolved issues included in the release |

---

### 5.10 Version History Standards

Every architecture document carries a Version History table:

| Version | Date | Author | Changes |
|---|---|---|---|
| `1.0.0` | `YYYY-MM-DD` | Engineering Agent | Initial document |
| `1.0.1` | `YYYY-MM-DD` | Engineering Agent | Added Section 3.7: Enum Naming |
| `1.1.0` | `YYYY-MM-DD` | Engineering Agent | Added Part VI: Logging Standards |

Version numbering follows semantic versioning:
- `MAJOR.MINOR.PATCH`
- MAJOR: structural change or part addition
- MINOR: section addition or significant table update
- PATCH: correction, clarification, or wording improvement

---
## PART VI — LOGGING STANDARDS

### 6.0 Overview

Logging is the primary observability instrument of the AI Trading Brain. When an incident occurs — an order not sent, a kill-switch that did not trigger, a performance regression — logs are the first and often the only diagnostic tool available. Logging standards therefore carry mandatory weight: poor logging means incidents cannot be diagnosed, which means they cannot be resolved.

---

### 6.1 Log Level Definitions

| Level | Numeric | When to Use | Examples |
|---|---|---|---|
| **DEBUG** | 10 | Internal state transitions; cache hits; routine processing; skipped conditions | `"Cycle skipped: market closed guard (20:15 IST)"`, `"GlobalSnapshot cache hit (age=2m3s)"` |
| **INFO** | 20 | Every significant state change; startup/shutdown events; regime changes; decisions; learning updates | `"Regime changed: TRENDING_BULLISH → RANGE_BOUND (confidence=0.79)"`, `"Order submitted: RELIANCE.NS LONG 50 units"` |
| **WARNING** | 30 | Degraded operation; stale data; near-threshold conditions; retried operations; slow layers | `"GlobalSnapshot stale: age=7min, using cached"`, `"Layer MarketIntelligence: 1,850ms (approaching WARN threshold)"` |
| **ERROR** | 40 | Recoverable failure; thread crash with auto-restart; feed failure with fallback; unexpected exception caught | `"Primary feed timeout: falling back to yfinance"`, `"RiskManagerAI raised unexpected RiskApprovalError; returning REJECTED"` |
| **CRITICAL** | 50 | Unrecoverable failure; kill-switch activation; startup failure; guardian thread death | `"Kill-switch ACTIVATED: DayPnL=-2.15% exceeds -2.00% limit"`, `"STARTUP FAILED: ConfigValidationError — DAILY_LOSS_LIMIT not set"` |

**Level usage rules:**
- Do NOT use `WARNING` for normal expected conditions (e.g., market closed at 20:00 is expected — use DEBUG)
- Do NOT use `INFO` for events that occur thousands of times per day (e.g., every tick received — use DEBUG)
- Do NOT use `ERROR` for conditions the system handles gracefully without human action
- ALWAYS use `CRITICAL` for kill-switch activation and guardian thread death

---

### 6.2 Log Structure Standard

All log records are structured with the following mandatory fields. Unstructured plain text log lines are prohibited for INFO and above.

| Field | Key | Type | Example | Required |
|---|---|---|---|---|
| Timestamp (UTC) | `timestamp` | ISO 8601 | `2026-07-02T10:35:42.123Z` | MANDATORY |
| Level | `level` | String | `INFO` | MANDATORY |
| Logger name | `logger` | String | `execution_engine.order_manager` | MANDATORY |
| Message | `message` | String | `Order submitted: RELIANCE.NS LONG` | MANDATORY |
| Layer | `layer` | String | `ExecutionEngine` | MANDATORY |
| Cycle ID | `cycle_id` | UUID | `f4a3b...` | REQUIRED (on cycle events) |
| Decision ID | `decision_id` | UUID | `d7b1c...` | REQUIRED (on order events) |
| Instrument | `instrument` | String | `RELIANCE.NS` | REQUIRED (on trade events) |
| Duration (ms) | `duration_ms` | Integer | `1842` | REQUIRED (on timed events) |
| Thread name | `thread` | String | `RiskGuardianThread` | RECOMMENDED |
| Exception | `exc_info` | Traceback | Full traceback | MANDATORY (on ERROR/CRITICAL with exception) |

**Log format (text):**
```
YYYY-MM-DD HH:MM:SS,mmm | LEVEL | logger.name | message | key=value key=value ...
```

**Log format (JSON for machine parsing):**
```json
{"timestamp": "...", "level": "INFO", "logger": "...", "message": "...", "layer": "...", "cycle_id": "..."}
```

---

### 6.3 Logger Naming Standards

| Context | Logger Name | Example |
|---|---|---|
| Layer primary class | `<package>.<module>` | `execution_engine.order_manager` |
| Sub-component | `<package>.<module>.<component>` | `risk_control.risk_manager_ai.approval` |
| Orchestrator | `orchestrator.master_orchestrator` | `orchestrator.master_orchestrator` |
| Infrastructure | `data_feeds.data_feed_manager` | `data_feeds.data_feed_manager` |
| Startup | `startup` | `startup` |
| Shutdown | `shutdown` | `shutdown` |

**Rule:** Always use `logging.getLogger(__name__)` — never use the root logger (`logging.getLogger()`) in modules.

---

### 6.4 Correlation and Trace IDs

Every cognitive cycle generates a `cycle_id` (UUID). This ID propagates through all events generated within that cycle, enabling full trace reconstruction.

| ID Type | Scope | Format | Propagation Rule |
|---|---|---|---|
| `cycle_id` | One full cognitive cycle (all layers) | UUID4 | Generated at cycle start by orchestrator; passed as argument through all layer calls |
| `decision_id` | One hypothesis decision | UUID4 | Generated by DecisionEngine; stored in SQLite; referenced in OrderRecord |
| `order_id` | One order submission | UUID4 | Generated by OrderManager; stored in SQLite and CSV |
| `learning_event_id` | One learning event | UUID4 | Generated by LearningEngine; stored in SQLite |
| `alert_id` | One system alert | UUID4 | Generated by SystemMonitor; stored in SQLite |

**Rule:** Any log event that is part of a cognitive cycle MUST include the `cycle_id` in its structured fields. This makes it possible to reconstruct the complete sequence of events for any cycle from logs alone.

---

### 6.5 What Must Always Be Logged

The following events MUST be logged at the specified level, regardless of configuration or debug mode:

| Event | Level | Required Fields |
|---|---|---|
| Process startup | INFO | version, mode (paper/live), timestamp |
| Process shutdown (graceful) | INFO | uptime, reason, timestamp |
| Process shutdown (crash) | CRITICAL | exception, traceback, timestamp |
| Kill-switch activation | CRITICAL | trigger_reason, trigger_value, threshold, timestamp |
| Kill-switch deactivation | INFO | authorised_by (human/system), override_command, timestamp |
| Order submitted (paper) | INFO | instrument, direction, size, entry_price, decision_id, cycle_id |
| Order rejected (risk) | INFO | reason, instrument, hypothesis_id, cycle_id |
| Order rejected (kill-switch) | WARNING | instrument, kill_switch_state, cycle_id |
| Regime change | INFO | from_regime, to_regime, confidence, cycle_id |
| Strategy disabled (auto) | WARNING | strategy_id, win_rate, trade_count, threshold |
| Thread crash | ERROR | thread_name, exception, traceback |
| Thread restart | WARNING | thread_name, restart_count |
| Feed failure | ERROR | feed_name, exception, fallback_used |
| Feed staleness | WARNING | feed_name, data_age_seconds, stale_flag |
| Layer WARN threshold breached | WARNING | layer_name, duration_ms, threshold_ms, cycle_id |
| Layer CRIT threshold breached | ERROR | layer_name, duration_ms, threshold_ms, cycle_id |
| Learning update | INFO | strategy_id, old_win_rate, new_win_rate, trade_count |
| Config validation at startup | INFO | all required keys present; any warnings |
| EOD learning complete | INFO | trade_count, strategies_updated, disabled_count |

---

### 6.6 Error and Exception Logging Standards

| Rule | Detail |
|---|---|
| **Always log the full traceback on exceptions** | Use `logger.exception("message")` which auto-includes traceback, not `logger.error(str(e))` |
| **Include context in the message** | `"Feed timeout for symbol {symbol} after {timeout}s"` — not just `"Timeout"` |
| **Log before re-raising** | Log the exception at the point of catch before re-raising to a higher handler |
| **One log entry per exception** | Do not log the same exception at multiple levels as it bubbles up; log at the catch point |
| **Exception chain** | When catching one exception and raising another, use `raise NewException(...) from original_exception` |

---

### 6.7 Audit Logging

Audit logs capture events that have financial, legal, or compliance significance. They are distinct from operational logs.

| Audit Event | Log Level | Where Logged | Retention |
|---|---|---|---|
| Order submitted | INFO | `audit_<date>.log` + SQLite `orders` table | Permanent |
| Kill-switch activation | CRITICAL | `audit_<date>.log` + SQLite `alerts` table | Permanent |
| Kill-switch override | INFO | `audit_<date>.log` + SQLite `alerts` table | Permanent |
| Strategy auto-disabled | WARNING | `audit_<date>.log` + SQLite `strategy_stats` | Permanent |
| Strategy promoted to live | INFO | `audit_<date>.log` | Permanent |
| Configuration change | INFO | `audit_<date>.log` | Permanent |
| Learning belief update | INFO | SQLite `learning_events` | 365 days |
| Telegram command received | INFO | `audit_<date>.log` | 90 days |

**Audit log immutability:** Audit log files are written in append-only mode. No process may overwrite or delete audit log entries. Audit log rotation creates new files; old files are never modified.

---

### 6.8 Performance Logging

Layer timing is recorded by `system_monitor.SystemMonitor.time_layer()` automatically. Individual modules do not need to implement their own timing — they use the context manager.

| Performance Metric | Recorded By | Stored In | Alert Condition |
|---|---|---|---|
| Layer wall-clock time | `SystemMonitor.time_layer()` | SQLite `telemetry` | WARN at 2,000ms; CRIT at 5,000ms |
| Full cycle time | `MasterOrchestrator` | SQLite `telemetry` | WARN at 200ms; CRIT at 500ms |
| Feed response time | Feed adapters | Log (DEBUG) | WARN at 5,000ms; CRIT at 8,000ms (timeout) |
| Learning queue depth | LearningEngine | Log (DEBUG) | WARN at 500 items; CRIT at 900 items |
| Thread heartbeat age | SystemMonitor | Log (DEBUG) | WARN if > 2× expected interval |

---

### 6.9 Security Logging

Events with security implications must be logged separately in the audit log with enhanced detail.

| Security Event | Required Log Fields |
|---|---|
| Telegram command from unknown chat_id | `source_chat_id`, `command`, `rejected=True` |
| Authenticated Telegram override | `chat_id`, `command`, `action_taken`, `authorised_by` |
| Config checksum mismatch at startup | `expected_checksum`, `actual_checksum`, `config_path` |
| Secrets access (startup only) | Environment variable name accessed; value NEVER logged |
| Failed authentication (broker API) | `broker_name`, `error_code`, `timestamp` |

**CRITICAL RULE:** Secret values (API keys, tokens, passwords, certificates) are **NEVER** written to any log, telemetry record, or audit trail. Log the key NAME at most; never the value.

---

### 6.10 Log Retention Policy

| Log Type | Retention Period | Rotation | Archive Action |
|---|---|---|---|
| Operational log (`trading_brain_<date>.log`) | 30 days | Daily | Delete after 30 days |
| Error log (`trading_brain_errors_<date>.log`) | 90 days | Daily | Delete after 90 days |
| Audit log (`audit_<date>.log`) | Permanent | Daily | Move to `data/audit_archive/`; never delete |
| Performance log (`perf_<date>.log`) | 30 days | Daily | Delete after 30 days |
| SQLite telemetry table | 90 days | Pruned weekly | Rows older than 90 days deleted |
| SQLite decisions table | Permanent | Never pruned | Never deleted |
| SQLite orders table | Permanent | Never pruned | Never deleted |
| SQLite learning_events table | 365 days | Pruned monthly | Rows older than 365 days deleted |

---
## PART VII — TESTING STANDARDS

### 7.0 Overview

Tests are the executable specification of the system's behaviour. A test suite that passes is evidence — not proof — that the system works as specified. Tests must be written with the same care and standard as production code. An inadequate test suite is worse than no test suite, because it creates false confidence.

---

### 7.1 Test Suite Organisation

```
tests/
├── unit/
│   ├── global_intelligence/
│   │   └── test_global_data_ai.py
│   ├── market_intelligence/
│   │   └── test_market_intelligence_engine.py
│   ├── risk_guardian/
│   │   └── test_risk_guardian.py
│   ├── execution_engine/
│   │   └── test_order_manager.py
│   └── ... (one folder per package)
├── integration/
│   ├── test_full_cognitive_cycle.py
│   ├── test_kill_switch_path.py
│   ├── test_paper_trade_journal.py
│   └── test_eod_learning_recovery.py
├── performance/
│   ├── test_cycle_timing.py
│   └── test_layer_latency.py
├── security/
│   └── test_authentication.py
└── conftest.py          # Shared fixtures; mock factory functions
```

---

### 7.2 Unit Testing Standards

Unit tests test a single class or function in isolation. All dependencies are mocked.

| Standard | Rule | Enforcement |
|---|---|---|
| **Isolation** | No real network calls, file I/O, or database access in unit tests | MANDATORY |
| **Determinism** | Tests produce the same result on every run on every machine | MANDATORY |
| **One assertion concept per test** | Each test verifies one specific behaviour or outcome | REQUIRED |
| **Descriptive names** | `test_risk_manager_rejects_when_daily_loss_limit_exceeded` — not `test_risk1` | MANDATORY |
| **Arrange-Act-Assert structure** | Every test has a clear setup, action, and assertion section | REQUIRED |
| **No test interdependency** | Tests do not depend on execution order; each sets up its own state | MANDATORY |
| **Fast execution** | Unit tests must complete in < 100ms each | REQUIRED |
| **Cover failure paths** | Every error path has at least one test confirming fail-safe behaviour | MANDATORY |

**Unit test naming convention:**
```
test_<class_or_function>_<scenario>_<expected_outcome>
```
Examples:
- `test_order_manager_submit_when_kill_switch_active_returns_blocked`
- `test_risk_manager_approve_when_size_exceeds_limit_rejects`
- `test_global_data_ai_fetch_on_cache_hit_returns_in_under_5ms`

---

### 7.3 Mandatory Unit Test Cases

The following test cases are MANDATORY regardless of other coverage considerations:

| Test Case | Module | What It Verifies |
|---|---|---|
| Kill-switch gate | `order_manager` | `kill_switch_active.is_set()` → submit returns BLOCKED |
| Risk approval expiry | `order_manager` | Approval older than 30s → submit returns REJECTED |
| DecisionRecord gate | `order_manager` | Missing record → submit returns BLOCKED |
| Paper trade CSV write | `order_manager` | Paper order → row appended to `paper_trades.csv` |
| Conviction threshold | `debate_engine` | Score < 6.5 → SUSPENDED; Score ≥ 6.5 → APPROVED |
| Missing agent vote | `debate_engine` | Unavailable agent → SUSPENDED, not APPROVED |
| Kill-switch VIX trigger | `risk_guardian` | VIX=46 injected → `kill_switch_active.is_set()` = True |
| Kill-switch loss trigger | `risk_guardian` | DayPnL < -2% injected → `kill_switch_active.is_set()` = True |
| Feed timeout | `yahoo_feed` | Timeout=8s enforced in yfinance call |
| Stale flag propagation | `data_feed_manager` | Source exception → stale=True in returned object |
| Singleton identity | `get_feed_manager()` | Two calls return same object (same `id()`) |
| Config validation | `config.py` | Missing required key → `ConfigValidationError` |
| Regime hysteresis | `market_monitor` | Single-scan regime change not committed |
| Auto-disable threshold | `strategy_performance_tracker` | Win rate < 40% over 20 trades → strategy disabled |
| EOD CSV recovery | `master_orchestrator` | Post-restart with CSV trades → non-zero trade count in EOD learning |
| Index symbol routing | `data_feed_manager` | `get_quote("NIFTY")` routes to `^NSEI` without `.NS` suffix |

---

### 7.4 Integration Testing Standards

Integration tests verify that two or more modules work correctly together.

| Standard | Rule |
|---|---|
| **Use real module instances** | Integration tests use real classes, not mocks; only external APIs are mocked |
| **Test the seams** | Integration tests focus on the contract between two modules |
| **Cover the full critical path** | At minimum, one integration test exercises the full cognitive cycle end-to-end |
| **State isolation** | Each integration test starts with a clean state (fresh SQLite, empty CSV) |
| **Realistic data** | Integration tests use realistic market data, not trivial placeholders |
| **Verify side effects** | Integration tests assert that expected records appear in SQLite and CSV, not just return values |

**Mandatory integration test scenarios:**

| Scenario | Modules Involved | Pass Criteria |
|---|---|---|
| Full cognitive cycle (paper mode) | All layers | Cycle completes < 200ms; telemetry row written |
| Kill-switch blocks all orders | risk_guardian + order_manager | VIX trigger → no CSV row written |
| EOD learning recovery | order_manager + learning_engine + orchestrator | Post-restart CSV-sourced trades counted in learning |
| Feed fallback chain | dhan_feed + yahoo_feed + data_feed_manager | Primary exception → yfinance response returned |
| Regime change propagation | market_intelligence + meta_learning + equity_scanner | Regime change → weight update → scan adapts |

---

### 7.5 Regression Testing Standards

Regression tests verify that previously fixed bugs do not reappear.

| Standard | Rule |
|---|---|
| **Bug fix = regression test** | Every bug fix is accompanied by a test that would have caught the bug before the fix |
| **Named for the bug** | Regression test name includes the bug description or ID |
| **Committed with the fix** | Regression test is committed in the same commit as the bug fix |
| **Covers the root cause** | The test covers the actual root cause, not just the surface symptom |

**Known regression tests (must be maintained):**

| Regression | Test Name | What It Catches |
|---|---|---|
| Class-level constant scope bug | `test_order_manager_no_nameError_on_same_zone_pct` | `_SAME_ZONE_PCT` accessed as bare name instead of `self._SAME_ZONE_PCT` |
| Strategy attribute name | `test_orchestrator_eod_learning_uses_strategy_not_strategy_name` | `position_lifecycle_event.strategy_name` → should be `.strategy` |
| Index symbol suffix bug | `test_feed_manager_nifty_routes_to_nsei_without_ns_suffix` | `NIFTY.NS` → should route to `^NSEI` |
| Post-restart zero count | `test_orchestrator_eod_learning_recovers_from_csv_when_memory_empty` | Zero in-memory closed trades but CSV has today's trades |

---

### 7.6 Performance Testing Standards

Performance tests measure and protect timing budgets.

| Test | Metric | Pass Threshold | Run Frequency |
|---|---|---|---|
| Full cognitive cycle timing | Average of 10 runs | < 172ms | On every change to critical path |
| GlobalIntelligence cache hit | Single call (warm cache) | < 5ms | On every change to GlobalDataAI |
| Layer WARN boundary | 10-cycle run | Zero WARN events | On every PR |
| Feed response time | `get_quote()` (live) | < 8,000ms (timeout) | Weekly |
| Kill-switch detection latency | Trigger to `is_set()` | < 100ms | On every change to RiskGuardian |
| Order submission (paper) | From `submit()` to CSV write | < 50ms | On every change to OrderManager |

**Performance test rules:**
- Never merge a change that increases average cycle time by > 10% without a documented justification
- Performance tests are tagged `@pytest.mark.performance` and run separately from unit tests
- Performance test results are stored and compared against the previous baseline

---

### 7.7 Security Testing Standards

| Test Type | Tool / Method | Frequency | Pass Criteria |
|---|---|---|---|
| Dependency vulnerability scan | `pip audit` or `safety check` | On every dependency change | Zero HIGH or CRITICAL CVEs |
| Static analysis | `bandit` | On every PR | Zero HIGH severity findings |
| Secret scanning | `detect-secrets` or git hooks | On every commit | Zero secrets detected in staged files |
| Authentication test | Unit test (Telegram chat_id) | On every change to notifications | Unknown chat_id → command rejected |
| Input validation test | Unit test (feed data) | On every change to data_feeds | Malformed quote → ValidationError, not crash |
| SQL injection test | Integration test | Quarterly | Parameterised queries prevent injection |

---

### 7.8 Test Coverage Expectations

| Coverage Type | Minimum | Target | Measurement Method |
|---|---|---|---|
| Line coverage (unit + integration) | 70% | 85% | `pytest --cov` |
| Branch coverage | 60% | 80% | `pytest --cov --cov-branch` |
| Critical path coverage | 100% | 100% | Manual audit of kill-switch, order submission, approval paths |
| Fail-safe coverage | 100% | 100% | Every fail-safe default has a test |
| New code coverage | 80% | 90% | Enforced by CI pipeline for new files |

**Coverage exemptions (must be documented):**
- Auto-generated code (evolved strategies JSON — not Python)
- Third-party adapter code (broker libraries)
- Debug and maintenance scripts in `scripts/`

---

### 7.9 Mocking Policy

| Category | Mock? | Rule |
|---|---|---|
| External network APIs (broker, yfinance, Telegram) | ALWAYS | Never make real API calls in tests |
| SQLite database | Test-specific file | Use a temporary database file; never use `trading_brain.db` |
| `paper_trades.csv` | Temporary path | Use `tempfile.NamedTemporaryFile`; never modify the production CSV |
| `config.py` values | Patch only what's needed | Use `unittest.mock.patch` for specific config values; do not replace config module |
| `threading.Event` | Real object | Use real `threading.Event`; do not mock atomic state |
| `RiskGuardianAgent.kill_switch_active` | Inject real Event | Tests inject a pre-configured `threading.Event`; do not mock the guardian class |
| Time / datetime | Mock for determinism | `unittest.mock.patch("module.datetime")` for time-dependent logic |

---

### 7.10 Test Quality Checklist

Before any test is merged:

- [ ] Test name describes the scenario and expected outcome
- [ ] Test has exactly one logical assertion (multiple `.assert*` calls are permitted when they verify one concept)
- [ ] All external dependencies are mocked or isolated
- [ ] Test is deterministic — runs identically on every machine
- [ ] Failure message is meaningful — asserts include context messages
- [ ] Test verifies fail-safe behaviour, not only the happy path
- [ ] Regression tests are named after the bug they prevent
- [ ] Performance tests record baseline and comparison

---
## PART VIII — SECURITY STANDARDS

### 8.0 Overview

The AI Trading Brain handles authentication credentials, financial data, and the ability to submit orders. A security vulnerability is not an inconvenience — it is a potential financial loss event. Security standards are MANDATORY at all enforcement levels; no exception is valid without Human Principal sign-off.

---

### 8.1 Secrets Management

| Rule | Detail | Enforcement |
|---|---|---|
| **No secrets in source code** | API keys, tokens, passwords, and certificates are never present in any Python file, config file, or script | MANDATORY |
| **No secrets in git history** | Pre-commit hooks scan staged files for secrets; secrets committed in error require immediate key rotation | MANDATORY |
| **Secrets only from environment** | `config.py` reads secrets using `os.environ.get("KEY_NAME")`; secrets are never hardcoded | MANDATORY |
| **Fail on missing secrets** | If a required secret is not present in the environment at startup, the process exits with `ConfigValidationError` | MANDATORY |
| **Secrets not logged** | No logging statement includes the value of any secret variable; only the key name may be logged | MANDATORY |
| **Rotate on exposure** | If a secret is suspected to have been exposed in any log, commit, or communication, rotate immediately | MANDATORY |
| **Docker secrets** | In Docker deployment, secrets are passed via environment variables or Docker secrets; never via command-line arguments | MANDATORY |

**Secrets inventory (current system):**

| Secret | Environment Variable | Used By | Rotation Trigger |
|---|---|---|---|
| Dhan API key | `DHAN_API_KEY` | `dhan_feed.py` | On expiry or any suspected exposure |
| Dhan client ID | `DHAN_CLIENT_ID` | `dhan_feed.py` | On account change |
| Telegram bot token | `TELEGRAM_BOT_TOKEN` | `telegram_bot.py` | On suspected exposure; annually |
| Telegram chat ID | `TELEGRAM_CHAT_ID` | `telegram_bot.py` | On Human Principal change |

---

### 8.2 Authentication Standards

| Rule | Detail |
|---|---|
| **Telegram chat_id verification** | Every Telegram command handler checks `update.effective_chat.id` against the registered `TELEGRAM_CHAT_ID` before any action |
| **Reject unknown callers** | Any command from an unregistered chat ID is silently ignored and logged at WARNING in the audit log |
| **No shared credentials** | Each deployment environment has its own API credentials; production credentials are never used in development |
| **Broker API auth** | Dhan API authentication uses the stored token; the token is validated before the first order of each session |
| **Auth failure = no action** | If authentication fails for any external service, the operation is abandoned; no degraded-auth operation |
| **No auth bypass** | There is no code path that bypasses the Telegram chat_id check, even for testing; tests use mocked authenticated requests |

---

### 8.3 Authorisation Standards

| Action | Authorisation Required | Who Can Authorise |
|---|---|---|
| Submit order (paper) | `PAPER_TRADING=True` in config; no human auth | System automatic |
| Submit order (live) | All gates pass: RiskApproval, DecisionRecord, kill-switch clear | System automatic (after 90-day gate) |
| Activate kill-switch | Automatic: VIX/loss threshold; or Human via Telegram | System or authenticated Human |
| Deactivate kill-switch | Authenticated Telegram `/override` command only | Human Principal only |
| Change `config.py` | Commit, review, deploy cycle | Engineering + Human Principal |
| Modify protected module | Explicit Human Principal instruction + documented justification | Human Principal only |
| Promote strategy to live | All 6 ValidationEngine stages pass | System automatic after 90-day gate |
| Modify evolved strategies | System-generated only; manual edit prohibited | System only |

---

### 8.4 Input Validation Standards

All data crossing a module boundary from an untrusted source must be validated before use.

| Input Source | Untrusted? | Validation Required |
|---|---|---|
| External market feed data | YES | Type, range, completeness, staleness flag |
| Telegram command arguments | YES | Command syntax; chat_id verification |
| Evolved strategy JSON files | PARTIALLY | Schema validation on load; numeric range checks |
| SQLite query results | NO (trusted source) | Named column access; type assertion |
| CSV trade journal rows | PARTIALLY | Column count; numeric parsing; date format |
| `config.py` values | NO (startup-validated) | Validated at startup by `validate_config()` |

**Validation rules:**

| Validation Type | Rule |
|---|---|
| Type validation | Assert the expected Python type; raise `TypeError` on mismatch |
| Range validation | Assert numeric values are within business-meaningful bounds |
| Completeness | Assert all required fields are present and non-None |
| Format | Validate dates, UUIDs, and symbols against expected patterns |
| Reject on failure | Invalid input is rejected; operation is not attempted with invalid data |
| Log on rejection | Every validation failure is logged at WARNING with the offending value (truncated if large) |

---

### 8.5 Output Encoding Standards

| Output Destination | Encoding Requirement |
|---|---|
| Log files | UTF-8; no binary data; no control characters except newline |
| SQLite database | Parameterised queries only; never string concatenation for SQL |
| CSV journal | UTF-8; values containing commas are quoted per RFC 4180 |
| Telegram messages | Plain text or Markdown; no HTML injection; length-limited to 4096 chars |
| Report files (Markdown) | UTF-8; no executable content |

**SQL injection prevention:**
- All SQLite operations use parameterised queries: `cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))`
- String formatting to build SQL statements is PROHIBITED
- Column names in `ORDER BY` or `GROUP BY` are validated against a whitelist, not taken from user input

---

### 8.6 Encryption Standards

| Data | Encryption Requirement | Method |
|---|---|---|
| SQLite database at rest | RECOMMENDED | SQLCipher or OS-level disk encryption on VPS |
| Log files at rest | RECOMMENDED | OS-level disk encryption on VPS |
| API credentials in transit | REQUIRED | All broker and Telegram API calls use HTTPS/TLS 1.2+ |
| Backup files | RECOMMENDED | Encrypted archive (`gpg` or OS-level) before off-site storage |
| SSH private key | MANDATORY | Key passphrase protected; stored securely |

---

### 8.7 Certificate and Key Handling

| Rule | Detail |
|---|---|
| **TLS verification enabled** | No HTTP requests with `verify=False`; TLS certificate chain is always verified |
| **SSH key protection** | The VPS SSH private key (`~/.ssh/trading_vps`) has a passphrase; never shared |
| **No key in source** | Private keys are never committed to the repository in any form |
| **Certificate expiry monitoring** | TLS certificates for any services are monitored for expiry; renewed before expiry |

---

### 8.8 Dependency Security Standards

| Rule | Detail | Frequency |
|---|---|---|
| **Dependency vulnerability scan** | `pip audit` against all packages in `requirements.txt` | On every PR; weekly in CI |
| **Severity threshold** | HIGH and CRITICAL CVEs block merge until resolved | MANDATORY |
| **MEDIUM CVE policy** | Medium CVEs are evaluated within 7 days; documented decision if not immediately patched | REQUIRED |
| **Transitive vulnerability** | If a transitive dependency has a HIGH/CRITICAL CVE, the direct dependency must be updated or replaced | MANDATORY |
| **Licence compliance** | All dependencies must have an approved licence (MIT, Apache 2.0, BSD); GPL-v2 only is flagged | REQUIRED |

---

### 8.9 Static Code Analysis Standards

| Tool | Purpose | Minimum Standard | When Run |
|---|---|---|---|
| `pylint` | Code quality and error detection | Score ≥ 8.5 per file | On every PR |
| `bandit` | Security vulnerability detection | Zero HIGH severity findings | On every PR |
| `mypy` | Type checking | Zero type errors in critical modules | On every PR (targeted) |
| `detect-secrets` | Secret scanning | Zero secrets detected | On every commit (pre-commit hook) |

---

### 8.10 Audit Compliance Standards

The AI Trading Brain maintains a complete audit trail for all financial decisions and system state changes.

| Audit Requirement | Implementation | Retention |
|---|---|---|
| Every order is traceable to a decision | `order_id` → `decision_id` → `hypothesis_id` → `evidence_set` in SQLite | Permanent |
| Every decision is traceable to debate | `decision_id` → `debate_record_id` → 5 agent votes | Permanent |
| Every kill-switch event is timestamped | CRITICAL log entry + SQLite `alerts` table + Telegram message | Permanent |
| Configuration at time of each order | Config snapshot recorded on startup; orders reference startup config version | Permanent |
| Every learning update is recorded | `learning_event_id` → `trade_id` → `outcome` in SQLite | 365 days |

---
## PART IX — GIT STANDARDS

### 9.0 Overview

Git history is the permanent record of every engineering decision. A clean, readable git history accelerates incident diagnosis, enables safe rollback, and communicates intent to future maintainers. Git standards are therefore not cosmetic — they are operational safety requirements.

---

### 9.1 Branch Strategy

The AI Trading Brain uses a simplified trunk-based branching model with short-lived feature branches.

| Branch | Lifetime | Purpose | Who Creates |
|---|---|---|---|
| `main` | Permanent | Production-ready code; deployable at any commit | Protected; CI only |
| `feature/<name>` | Hours to days | New features or capabilities | Any engineer |
| `fix/<name>` | Hours | Bug fixes for non-urgent issues | Any engineer |
| `hotfix/<name>` | < 4 hours | Urgent production bug requiring immediate deploy | Any engineer |
| `release/<version>` | Days | Release preparation; final testing and documentation | Release manager |

**Branch protection rules for `main`:**
- Direct pushes to `main` are PROHIBITED
- Every merge to `main` requires at least one review (or Human Principal approval)
- Every merge to `main` must pass all CI checks
- `git push --force` to `main` is PROHIBITED under all circumstances

---

### 9.2 Commit Message Format

Commit messages follow the Conventional Commits specification with project-specific extensions.

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Subject line rules:**
- Imperative present tense: `Add`, `Fix`, `Remove`, `Refactor` — never `Added`, `Fixed`, `Removing`
- Maximum 72 characters
- No period at the end
- Capitalise the first letter of the subject

**Type values:**

| Type | When Used | Example |
|---|---|---|
| `feat` | New feature or capability | `feat(risk_guardian): Add VIX kill threshold override config` |
| `fix` | Bug fix | `fix(order_manager): Correct _SAME_ZONE_PCT to self._SAME_ZONE_PCT` |
| `refactor` | Code restructuring without behaviour change | `refactor(meta_learning): Extract kNN training to separate method` |
| `perf` | Performance improvement | `perf(global_intelligence): Add 5-minute cache to GlobalDataAI.fetch` |
| `test` | Test addition or modification | `test(risk_guardian): Add kill-switch VIX trigger regression test` |
| `docs` | Documentation change | `docs(architecture): Add Layer 9 engineering specification` |
| `chore` | Maintenance (deps, config, CI) | `chore(requirements): Pin yfinance to 0.2.43` |
| `security` | Security improvement | `security(telegram_bot): Enforce chat_id verification on all commands` |
| `hotfix` | Emergency production fix | `hotfix(order_manager): Restore kill-switch check removed in d4b3c9` |

**Scope values:** The module or package being changed (`order_manager`, `risk_guardian`, `config`, `all`)

**Body requirements (when present):**
- Separate from subject with one blank line
- Explain WHY the change was made (not what; the diff shows what)
- Reference the invariant, bug, or architectural principle being satisfied
- Maximum 72 characters per line

**Footer requirements:**

| Key | When Required | Example |
|---|---|---|
| `BREAKING CHANGE:` | Any interface change | `BREAKING CHANGE: GlobalDataAI.fetch() now requires force parameter` |
| `Fixes:` | Bug fix with issue number | `Fixes: #47` |
| `ENG-INV:` | When satisfying an engineering invariant | `ENG-INV: ENG-INV-06 (Kill-switch path synchronous)` |
| `Closes:` | When closing a tracked issue | `Closes: #52` |

---

### 9.3 Commit Quality Standards

| Rule | Detail |
|---|---|
| **Atomic commits** | Each commit contains one logical change; do not mix bug fix and refactor in one commit |
| **No "work in progress" commits to main** | WIP commits may exist on feature branches; must be squashed before merge to main |
| **Passing tests before commit** | No commit goes to main unless all tests pass locally first |
| **Descriptive body for complex changes** | Any change with architectural significance must have a commit body explaining the rationale |
| **Reference ADRs** | Commits that implement an architecture decision reference the `ED-<N>` decision ID in the footer |
| **No merge commits on feature branches** | Feature branches are rebased onto `main`, not merged; keeps history linear |
| **No squash of regression tests** | Regression test commits must remain as separate, identifiable commits |

---

### 9.4 Pull Request Requirements

| Requirement | Detail |
|---|---|
| **PR title follows commit format** | Same type-scope-subject format as commit messages |
| **Description template** | Every PR includes: what changed, why, which tests cover it, and any deployment considerations |
| **Linked issue** | PRs reference the issue or Engineering Decision they address |
| **Self-reviewed before requesting** | Author reviews the PR diff before requesting review |
| **No unrelated changes** | PRs contain only changes related to their stated purpose |
| **All CI checks pass** | Pylint, tests, security scan, and any other CI jobs must be green |
| **`Files Modified` table updated** | `copilot-instructions.md` Files Modified table is updated in the PR |
| **Timing baseline maintained** | Performance-sensitive changes include before/after timing measurements |

---

### 9.5 Code Review Policy

| Rule | Detail |
|---|---|
| **At least one review before merge** | Every PR to `main` has at least one approved review |
| **Reviewer checks interface preservation** | Reviewer explicitly confirms no critical interface signatures changed |
| **Reviewer checks constants scope** | Reviewer explicitly checks class-level constants are accessed with `self.` |
| **Protected module changes** | Changes to protected modules require Human Principal review (not just engineering review) |
| **Review within 24 hours** | PRs are reviewed within 24 hours of submission during active development |
| **Comments are resolved** | All review comments are either addressed or formally declined with explanation |
| **Reviewer runs tests** | For high-risk changes (kill-switch, order submission, risk approval), reviewer runs tests locally |

**Code review checklist (reviewer):**

- [ ] Interface signatures unchanged (or formally versioned if changed)
- [ ] No class-level constant accessed as bare name inside method
- [ ] No new secret in any string literal
- [ ] All exceptions caught and logged
- [ ] All new shared state has a corresponding lock
- [ ] `Files Modified` table updated in `copilot-instructions.md`
- [ ] Tests cover both the happy path and the failure path
- [ ] No new hardcoded threshold (must be in `config.py`)
- [ ] Layer dependency direction is correct (no skip imports, no reverse imports)
- [ ] Protected modules not modified without documented approval

---

### 9.6 Release Tagging Standards

| Rule | Detail |
|---|---|
| **Semantic versioning** | Tags follow `vMAJOR.MINOR.PATCH` |
| **Tag from `main`** | Releases are always tagged from the `main` branch |
| **Annotated tags** | `git tag -a v1.2.3 -m "Release v1.2.3: description"` — not lightweight tags |
| **Release notes** | Every tag is accompanied by a CHANGELOG entry and release notes |
| **No tag mutation** | Tags are immutable once pushed; if a release must be replaced, a new tag is created |
| **MAJOR increment** | Breaking interface change, architectural overhaul, or multi-layer structural change |
| **MINOR increment** | New capability, new layer, new strategy, new Telegram command |
| **PATCH increment** | Bug fix, performance improvement, documentation update |

---

### 9.7 Hotfix Process

A hotfix is an urgent production fix that cannot wait for the normal PR cycle.

| Step | Action | Time Limit |
|---|---|---|
| 1 | Create `hotfix/<description>` branch from `main` | Immediate |
| 2 | Apply the minimal fix; write or update regression test | < 2 hours |
| 3 | Push branch; request emergency review from at least one engineer | < 30 minutes |
| 4 | Merge to `main` after review (squash merge acceptable) | < 30 minutes after review |
| 5 | Deploy via standard deploy procedure | < 15 minutes |
| 6 | Verify deployment health (all containers healthy; cycle completes) | < 10 minutes |
| 7 | Tag with `PATCH` version increment | Immediate after healthy deploy |
| 8 | Write post-incident note in commit body or separate ADR | Within 24 hours |

**NEVER** skip the regression test step, even in a hotfix. The test is what prevents the bug from returning.

---

### 9.8 Rollback Policy

| Trigger | Rollback Action | Time Target |
|---|---|---|
| Container health check fails after deploy | `git revert HEAD; push; deploy` | < 15 minutes |
| Kill-switch activates immediately after deploy | Assess cause first; revert if deploy-induced | < 10 minutes |
| Unexpected `CRITICAL` log lines after deploy | Revert unless cause is confirmed non-regression | < 15 minutes |
| Performance regression > 20% after deploy | Revert; profile cause before re-attempting | < 15 minutes |

**Rollback is always safer than diagnosis under live conditions.** Revert first; diagnose on the previous stable version.

---

### 9.9 Version Numbering

| Scenario | Version Increment | Example |
|---|---|---|
| Bug fix that does not change any interface | PATCH | `1.2.3 → 1.2.4` |
| New feature that adds capability without breaking existing | MINOR | `1.2.3 → 1.3.0` |
| Any breaking change to a public interface | MAJOR | `1.2.3 → 2.0.0` |
| Architecture document update only | No code increment; doc version increments | `v1.2.3` (code); doc `v1.1.0` |
| New deployment (VPS change, Docker config) | PATCH | `1.2.3 → 1.2.4` |

The version is stored in `config.py` as `VERSION = "1.2.3"` and is logged at every startup.

---
## PART X — ENGINEERING CONSTITUTION

### 10.0 Overview

The Engineering Constitution contains the 65 mandatory engineering rules that govern every artefact produced in the AI Trading Brain / IIOS project. These rules are not guidelines or suggestions. They are MANDATORY (L1). No rule may be violated without a formal waiver recorded in the Engineering Decision Register with Human Principal sign-off.

Rules are organised into eight categories: Architecture, Modules, Safety, State, Observability, Testing, Security, and Process.

---

### 10.1 Category A — Architecture Rules

**A-01: Every module shall have exactly one primary responsibility.**
No module is permitted to perform the duties of two layers. A module that generates signals may not also assess risk. A module that submits orders may not also generate hypotheses. Responsibility boundaries are defined in the Package Responsibility Matrix (Part II, Section 2.10).

**A-02: Dependency shall flow inward — outer layers depend on inner layers, never the reverse.**
A module in Layer N may import from Layer N-1 or lower-numbered layers. It may never import from Layer N+1 or higher-numbered layers. The orchestrator (Layer 17) is the sole exception: it coordinates all layers.

**A-03: No two modules in different layers shall import from each other.**
If Layer 5 imports Layer 3, Layer 3 must not import Layer 5. This is a circular dependency and is prohibited unconditionally.

**A-04: Every singleton shall be accessed exclusively through its designated getter function.**
`get_feed_manager()`, `get_performance_tracker()`, `get_regime_strategy_map()`, and `get_telegram_bot()` are the only valid access points for their respective singletons. Direct class instantiation of a singleton class is prohibited.

**A-05: Every public interface shall be stable once published.**
A public method signature is a contract. Once a method is exported from a module's `__init__.py`, its signature (name, parameters, return type) cannot change without a formal MAJOR version increment and documented BREAKING CHANGE entry in the ADR register.

**A-06: Configuration shall be centralised in exactly one file.**
`config.py` is the sole configuration authority. No module reads environment variables directly. No module maintains its own configuration file. No threshold or parameter is hardcoded in a module.

**A-07: No module shall skip a layer in its dependency chain.**
Layer 10 (Debate) may depend on Layer 9 (RiskGuardian) for the kill-switch state but may not depend on Layer 5 (StrategyLab) for strategy information. That information flows through the orchestrator.

**A-08: Every layer shall be independently runnable for testing purposes.**
A unit test for any layer must be able to run with all adjacent layers mocked. No layer requires another layer to be running in order to instantiate its primary class.

**A-09: The orchestrator shall coordinate, not implement.**
`MasterOrchestrator` calls layer methods in sequence and passes results between them. It does not contain business logic, risk assessment, signal generation, or learning logic.

**A-10: No hardcoded IP addresses, hostnames, or port numbers in source code.**
Infrastructure addresses are configuration values. They change across environments. They must be in `config.py` or environment variables, never in source files.

---

### 10.2 Category B — Module Rules

**B-01: Every Python module shall open with a module-level docstring.**
No module file is exempt. The docstring states the module's purpose, layer, primary class, and critical interfaces.

**B-02: Every public class shall have a class-level docstring.**
The class docstring states the class's single responsibility, singleton access method (if applicable), owned state, and thread safety characteristics.

**B-03: Every public method shall have a function-level docstring.**
The docstring states what the function does (not how), its parameters, return value, and any exceptions it raises.

**B-04: No Python file shall exceed 600 lines.**
A file exceeding this limit is a sign of too much responsibility. The file must be split into smaller modules with clear responsibilities.

**B-05: No function shall exceed 50 lines.**
A function exceeding this limit is a sign of too much complexity. It must be refactored into smaller helper functions.

**B-06: No function shall exceed cyclomatic complexity 10.**
Cyclomatic complexity measures the number of independent paths through a function. Above 10, the function is difficult to test exhaustively. Refactor to reduce branches.

**B-07: No wildcard imports are permitted.**
`from module import *` is prohibited. All imports are explicit: `from module import ClassName, function_name`.

**B-08: All imports shall appear at the top of the file.**
No import statement inside a function, class, or conditional block. The only exception is a circular-import resolution using a local import — which must itself be documented with a comment explaining why.

**B-09: Class-level constants shall always be accessed with `self.` inside methods.**
A constant defined as a class attribute (`_THRESHOLD = 0.02`) is accessed inside instance methods as `self._THRESHOLD`. Accessing it as a bare name (`_THRESHOLD`) inside a method is a scope bug.

**B-10: No single-letter variable names in module scope.**
Single-letter names are permitted only in mathematical loops (`for i in range(n)`) and list comprehensions. All domain objects, configuration values, and intermediate results have meaningful names.

**B-11: No commented-out code shall exist in production modules.**
Code that is disabled is deleted. Git history preserves it. Comments that say "# disabled for now" or "# TODO: remove this" are not permitted in production-committed code.

**B-12: Every broker adapter shall implement `BaseFeed` or `BaseBroker`.**
Adapters for new data sources or brokers are implemented as subclasses of the appropriate abstract base class. This ensures they can be substituted without callers knowing.

---

### 10.3 Category C — Safety Rules

**C-01: Every order submission shall check `kill_switch_active.is_set()` before proceeding.**
The kill-switch check is the first gate in `order_manager.submit()`. No code path reaches the broker call without first checking the kill-switch. This check is synchronous and atomic.

**C-02: Every order submission shall verify the RiskApprovalRecord is valid and not expired.**
A `RiskApprovalRecord` is valid for 30 seconds from `approved_at`. Any submission with an expired approval is rejected. This is not optional; the market can change significantly in 30 seconds.

**C-03: Every order submission shall verify the DecisionRecord exists in SQLite before proceeding.**
The `decision_id` referenced by the order must be present in the `decisions` table before the order is submitted. This enforces the "record before act" constitutional principle.

**C-04: The kill-switch deactivation shall be possible only through authenticated human command.**
`kill_switch_active.clear()` is called only inside the authenticated Telegram `/override` handler. No automated process may clear the kill-switch. No code path in the intelligence or execution layers may clear it.

**C-05: `PAPER_TRADING=True` shall prevent all real broker calls unconditionally.**
When `config.PAPER_TRADING` is True, the `order_manager.submit()` method takes the paper-mode path and never reaches any broker adapter code. This is an explicit conditional check, not a mock.

**C-06: Stop-loss is mandatory for every position.**
No position is opened without a stop-loss level. `risk_manager_ai.approve()` rejects any `PositionSizeRecommendation` that does not include a `stop_price`. There is no exception.

**C-07: The RiskGuardian thread shall monitor at 500ms intervals or faster.**
The guardian poll cycle must not exceed 500ms. Any latency increase to the guardian thread is a safety regression and must be resolved before deployment.

**C-08: Guardian thread death shall automatically activate the kill-switch.**
If the `RiskGuardianThread` exits unexpectedly, the main thread's heartbeat check detects the failure and calls `kill_switch_active.set()` as a fail-safe. There is no "continue trading without guardian" mode.

**C-09: No decision shall be made with stale data above the maximum allowed age.**
`GlobalSnapshot` may not be used if it is older than 10 minutes. At that age, conviction scores must be halved and any resulting hypothesis must be flagged as LOW_CONFIDENCE. Trading halts entirely on GlobalSnapshot age > 30 minutes.

**C-10: Every hypothesis that is suspended shall be discarded, not queued for later.**
A SUSPENDED hypothesis is not re-submitted in a later cycle. A new hypothesis is generated in the next cognitive cycle. Stale hypotheses must not accumulate in any queue.

**C-11: Every position closure shall be recorded in the CSV journal before the monitoring thread moves on.**
The trade journal entry for a position close is written before the monitoring thread marks the position as closed in memory. This ensures the record survives a restart.

**C-12: Drawdown halt shall activate at ≥ 2% daily loss, not below.**
The daily loss limit is `config.DAILY_LOSS_LIMIT`. If this value is changed, a full regression cycle is required. The kill-switch activates when `daily_pnl <= -DAILY_LOSS_LIMIT * portfolio_value`.

---

### 10.4 Category D — State Rules

**D-01: All mutable state shared between threads shall be protected by a `threading.Lock` or `threading.RLock`.**
Unprotected shared state is a race condition. There are no exceptions to this rule for production code.

**D-02: The `kill_switch_active` flag shall be a `threading.Event` object, never a boolean.**
`threading.Event` is atomic and designed for cross-thread signalling. A boolean is not safe across threads in all Python implementations.

**D-03: No lock shall be held across any I/O operation.**
File writes, network calls, and database operations must not occur while a lock is held. Acquire the lock, perform the in-memory operation, release the lock, then perform I/O.

**D-04: No two locks shall ever be acquired in different orders by different threads.**
Lock acquisition must follow a global ordering to prevent deadlocks. The global order is documented in `ENGINEERING_BLUEPRINT.md` Supplement C.

**D-05: Every singleton object shall be initialised exactly once.**
The singleton getter functions (`get_feed_manager()`, etc.) guarantee single-instance access. The underlying class constructor must not be called from anywhere other than its getter function.

**D-06: Database writes for trade records shall use INSERT, never UPDATE.**
Trade records, decision records, and order records are immutable. Corrections are made by inserting a new record with a correction flag, not by modifying the original. This preserves the audit trail.

**D-07: The paper trades CSV journal shall be opened in append mode only.**
`open(path, 'a')` is the only permitted mode for the paper trades CSV. Reading from it for recovery purposes uses `open(path, 'r')`. Writing overwrites (`'w'`) are prohibited.

**D-08: Every shared data structure shall be a bounded container.**
Unbounded queues, lists, or caches that grow without limit will eventually cause memory exhaustion. Every shared accumulator has a defined maximum size and an eviction policy.

**D-09: Config values are read at import time, not at call time.**
`config.DAILY_LOSS_LIMIT` is read when the module is imported. It is not re-read on every call. If a config change is needed, a restart is required. No hot-reload of config values.

**D-10: Every state recovery operation shall be idempotent.**
Running the post-restart state recovery (CSV read, queue drain, position reconciliation) a second time must produce the same state as running it once. Duplicate processing must be detected and skipped.

---

### 10.5 Category E — Observability Rules

**E-01: Every layer execution shall be timed by `SystemMonitor.time_layer()`.**
No layer call in the orchestrator is made without wrapping it in `with system_monitor.time_layer("LayerName"):`. This is not optional.

**E-02: Every significant state change shall be logged at INFO or above.**
Regime changes, order submissions, kill-switch events, strategy disables, and learning updates are INFO events at minimum. They are never logged only at DEBUG.

**E-03: Every error condition shall be logged with full exception context.**
`logger.exception("message")` is used for all exception logging. The bare `logger.error(str(e))` that discards the traceback is prohibited.

**E-04: Cycle IDs shall propagate through all layer calls within a single cognitive cycle.**
The `cycle_id` generated at the start of a cognitive cycle is passed as an argument or thread-local to every subsequent operation in that cycle, and is included in all log structured fields.

**E-05: Every Telegram command received from an authenticated source shall be logged at INFO.**
Commands from unauthenticated sources are logged at WARNING. The audit trail of human commands is permanent.

**E-06: Every kill-switch activation and deactivation is a CRITICAL log event.**
These events are the most significant system events. They must be visible in the log without filtering.

**E-07: Every deployment shall emit a startup banner log entry.**
The startup banner includes: version, mode (paper/live), VPS hostname, timestamp, and the count of active strategies.

**E-08: The SQLite telemetry table shall hold at least 90 days of timing records.**
The pruning job runs weekly and removes records older than 90 days. This ensures 90 days of performance history is always available for diagnosis.

**E-09: Every strategy auto-disable event shall be communicated to the Human Principal via Telegram.**
Auto-disables are not silent background events. The Human Principal receives a WARNING-level Telegram message with the strategy ID, win rate, and trade count.

**E-10: The dashboard shall show the last 10 cycles' average timing.**
The Streamlit dashboard displays a rolling average of the last 10 cognitive cycle durations. This makes performance regressions visible within minutes of deployment.

---

### 10.6 Category F — Testing Rules

**F-01: Every bug fix shall be accompanied by a regression test.**
The regression test is committed in the same commit as the fix. The test must fail before the fix and pass after it.

**F-02: Every critical path shall have 100% test coverage.**
The kill-switch path, order submission path, and risk approval path each have tests for all branching conditions, including timeout, expiry, missing record, and kill-switch-active states.

**F-03: No merge to main shall reduce test coverage below the minimum threshold.**
The minimum line coverage is 70%. CI enforces this gate. Coverage reports are generated and reviewed on every PR.

**F-04: No test shall make real network calls.**
External services (broker APIs, yfinance, Telegram) are always mocked in tests. No test requires network access to pass.

**F-05: No test shall use the production SQLite database.**
Tests create temporary database files using `tempfile` and delete them after each test. The production `trading_brain.db` is never touched by tests.

**F-06: Performance tests shall record and compare against the established baseline.**
Performance tests store timing results in a baseline file. CI compares the current run against the baseline and fails if the regression threshold is exceeded.

**F-07: Every singleton shall have a unit test that verifies single-instance identity.**
`get_feed_manager()` called twice must return the same object. This test catches violations of the singleton pattern.

**F-08: Test names shall be fully descriptive without abbreviation.**
`test_order_manager_submit_when_kill_switch_active_returns_blocked` is correct. `test_submit_ks` is not. Test names are the documentation of the test suite.

**F-09: Every thread safety rule shall have a corresponding concurrency test.**
For each shared mutable object, there is a test that confirms concurrent access from two threads does not corrupt the state.

**F-10: Security tests shall run on every PR.**
`bandit`, `pip audit`, and `detect-secrets` are CI pipeline jobs that run on every PR. A single HIGH finding blocks merge.

---

### 10.7 Category G — Security Rules

**G-01: No secret shall ever appear in source code, configuration files, or git history.**
This is an unconditional rule. Any discovered violation requires immediate key rotation regardless of whether the secret was exposed externally.

**G-02: Every Telegram command shall verify the sender's chat_id before any action.**
The chat_id verification is the first line of every Telegram command handler. It is not optional and not bypassable in tests.

**G-03: All external HTTP requests shall use TLS with certificate verification enabled.**
`verify=False` in any HTTP request is prohibited. The cost of a man-in-the-middle attack on market data or broker communication is unacceptable.

**G-04: All SQLite queries shall use parameterised statements.**
String concatenation to build SQL is a SQL injection vulnerability. All queries use `?` placeholders.

**G-05: Dependencies shall be scanned for known vulnerabilities on every change.**
`pip audit` runs in CI. A HIGH or CRITICAL CVE blocks the PR until the dependency is updated or a waiver is formally recorded.

**G-06: Every authentication failure shall be logged in the audit log.**
Failed broker authentication, failed Telegram verification, and failed config validation each produce an audit log entry with timestamp and relevant context.

**G-07: Encrypted connections are used for all communications with external services.**
Broker APIs, Telegram API, VPS SSH: all use encrypted channels. Unencrypted channels are prohibited.

**G-08: The VPS SSH private key shall be passphrase-protected.**
The SSH key for the VPS is not a bare private key. It has a passphrase. Loss of the key without the passphrase does not grant VPS access.

---

### 10.8 Category H — Process Rules

**H-01: Every code change shall be deployed to the VPS before the engineering task is considered complete.**
Local-only changes represent a split-brain state. The deploy cycle (commit → push → SSH pull → build → restart → verify) is mandatory after every production change.

**H-02: The deploy is complete only when both Docker containers are healthy.**
`docker compose ps` must show both containers as `Up ... (healthy)`. A deploy where one container is not healthy is an incomplete deploy.

**H-03: Every protected module modification shall have explicit Human Principal authorisation on record.**
`risk_guardian.py`, `backtesting_ai.py`, `validation_engine/`, and `evolved_strategies/` are protected. Changes require documented approval, not just code review.

**H-04: The `Files Modified` table in `copilot-instructions.md` shall be updated for every production file change.**
This table is the running log of all production changes. It must be kept current.

**H-05: No force-push to `main`.**
`git push --force` to the main branch is prohibited unconditionally. If a commit must be undone, use `git revert`. History is immutable.

**H-06: Every architectural decision shall be recorded as an ADR.**
The Engineering Decision Register (in `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md`) is updated whenever a significant architectural decision is made.

**H-07: Every post-incident diagnosis shall produce a written post-incident note.**
After any production incident (kill-switch activation, unexpected crash, incorrect order, data quality failure), a written note is produced within 24 hours. It documents: what happened, the root cause, the fix applied, and the regression test added.

**H-08: Quarterly engineering review shall audit compliance with these standards.**
Every quarter, a review assesses: naming convention compliance, test coverage, dependency security, documentation completeness, and performance baseline adherence. Findings are documented and tracked to resolution.

**H-09: No engineering standard shall be violated for reasons of speed alone.**
Time pressure is not a justification for standards violation. If a change cannot be made in compliance with standards, the timeline must be extended, not the standards lowered.

**H-10: Every new thread added to the system shall be registered in the Thread Registry.**
The Thread Registry in `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` Supplement C.1 must be updated whenever a new thread is introduced.

---

### 10.9 Engineering Constitution — Reference Table

| Rule ID | Category | Rule Summary | Enforcement |
|---|---|---|---|
| A-01 | Architecture | One primary responsibility per module | MANDATORY |
| A-02 | Architecture | Dependency flows inward | MANDATORY |
| A-03 | Architecture | No circular imports between layers | MANDATORY |
| A-04 | Architecture | Singletons via getter functions only | MANDATORY |
| A-05 | Architecture | Public interfaces are stable once published | MANDATORY |
| A-06 | Architecture | Configuration centralised in config.py | MANDATORY |
| A-07 | Architecture | No layer-skipping imports | MANDATORY |
| A-08 | Architecture | Every layer independently testable | MANDATORY |
| A-09 | Architecture | Orchestrator coordinates, does not implement | MANDATORY |
| A-10 | Architecture | No hardcoded infrastructure addresses | MANDATORY |
| B-01 | Modules | Module-level docstring required | MANDATORY |
| B-02 | Modules | Class-level docstring required | MANDATORY |
| B-03 | Modules | Public method docstring required | MANDATORY |
| B-04 | Modules | No file exceeds 600 lines | REQUIRED |
| B-05 | Modules | No function exceeds 50 lines | REQUIRED |
| B-06 | Modules | Cyclomatic complexity ≤ 10 | REQUIRED |
| B-07 | Modules | No wildcard imports | MANDATORY |
| B-08 | Modules | All imports at top of file | MANDATORY |
| B-09 | Modules | Class constants accessed with self. | MANDATORY |
| B-10 | Modules | No single-letter names in module scope | MANDATORY |
| B-11 | Modules | No commented-out code in production | REQUIRED |
| B-12 | Modules | Adapters implement base classes | REQUIRED |
| C-01 | Safety | Kill-switch checked before every order | MANDATORY |
| C-02 | Safety | RiskApproval validity verified before order | MANDATORY |
| C-03 | Safety | DecisionRecord verified before order | MANDATORY |
| C-04 | Safety | Kill-switch cleared by human only | MANDATORY |
| C-05 | Safety | PAPER_TRADING prevents all broker calls | MANDATORY |
| C-06 | Safety | Stop-loss mandatory for every position | MANDATORY |
| C-07 | Safety | Guardian polls at ≤ 500ms interval | MANDATORY |
| C-08 | Safety | Guardian death activates kill-switch | MANDATORY |
| C-09 | Safety | Stale data above maximum age halts trading | MANDATORY |
| C-10 | Safety | Suspended hypotheses discarded immediately | MANDATORY |
| C-11 | Safety | Position closure recorded before state update | MANDATORY |
| C-12 | Safety | Drawdown halt at ≥ 2% daily loss | MANDATORY |
| D-01 | State | Shared mutable state protected by Lock | MANDATORY |
| D-02 | State | Kill-switch is threading.Event | MANDATORY |
| D-03 | State | No lock held across I/O | MANDATORY |
| D-04 | State | Consistent lock acquisition order | MANDATORY |
| D-05 | State | Singletons initialised exactly once | MANDATORY |
| D-06 | State | Trade records INSERT-only | MANDATORY |
| D-07 | State | CSV journal append-only | MANDATORY |
| D-08 | State | All shared structures are bounded | REQUIRED |
| D-09 | State | Config read at import time | REQUIRED |
| D-10 | State | State recovery is idempotent | REQUIRED |
| E-01 | Observability | Every layer timed by SystemMonitor | MANDATORY |
| E-02 | Observability | Significant state changes logged at INFO+ | MANDATORY |
| E-03 | Observability | Exceptions logged with full traceback | MANDATORY |
| E-04 | Observability | Cycle IDs propagate through all calls | REQUIRED |
| E-05 | Observability | Telegram commands logged at INFO | REQUIRED |
| E-06 | Observability | Kill-switch events logged at CRITICAL | MANDATORY |
| E-07 | Observability | Startup banner logged at INFO | REQUIRED |
| E-08 | Observability | Telemetry retained for 90 days minimum | REQUIRED |
| E-09 | Observability | Auto-disable notified via Telegram | REQUIRED |
| E-10 | Observability | Dashboard shows rolling cycle timing | RECOMMENDED |
| F-01 | Testing | Every bug fix has a regression test | MANDATORY |
| F-02 | Testing | Critical paths have 100% test coverage | MANDATORY |
| F-03 | Testing | Merge to main never reduces coverage below 70% | REQUIRED |
| F-04 | Testing | Tests never make real network calls | MANDATORY |
| F-05 | Testing | Tests never use production database | MANDATORY |
| F-06 | Testing | Performance tests compare against baseline | REQUIRED |
| F-07 | Testing | Singletons tested for single-instance identity | REQUIRED |
| F-08 | Testing | Test names are fully descriptive | MANDATORY |
| F-09 | Testing | Thread safety verified by concurrency tests | REQUIRED |
| F-10 | Testing | Security tests run on every PR | MANDATORY |
| G-01 | Security | No secrets in source code or git history | MANDATORY |
| G-02 | Security | Telegram commands verify chat_id first | MANDATORY |
| G-03 | Security | All HTTP uses TLS with cert verification | MANDATORY |
| G-04 | Security | All SQLite queries parameterised | MANDATORY |
| G-05 | Security | Dependency CVE scan on every change | MANDATORY |
| G-06 | Security | Authentication failures logged to audit | REQUIRED |
| G-07 | Security | All external comms use encrypted channels | MANDATORY |
| G-08 | Security | VPS SSH key passphrase-protected | MANDATORY |
| H-01 | Process | Deploy to VPS before task is complete | MANDATORY |
| H-02 | Process | Deploy complete only when both containers healthy | MANDATORY |
| H-03 | Process | Protected module changes need HPA approval | MANDATORY |
| H-04 | Process | Files Modified table kept current | MANDATORY |
| H-05 | Process | No force-push to main | MANDATORY |
| H-06 | Process | Architectural decisions recorded as ADRs | REQUIRED |
| H-07 | Process | Post-incident notes written within 24 hours | REQUIRED |
| H-08 | Process | Quarterly engineering compliance review | REQUIRED |
| H-09 | Process | Standards not violated for speed | MANDATORY |
| H-10 | Process | New threads registered in Thread Registry | MANDATORY |

---
## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document Parts | 10 (Parts I–X) |
| Engineering Constitution Rules | 70 (A-01 to H-10) |
| Naming Standard Tables | 14 (Sections 3.1–3.14) |
| Rule Categories | 8 (Architecture, Modules, Safety, State, Observability, Testing, Security, Process) |
| Mandatory Unit Test Cases | 16 (Section 7.3) |
| Mandatory Regression Tests | 4 (Section 7.5) |
| Mandatory Integration Scenarios | 5 (Section 7.4) |
| Security Audit Events | 5 (Section 8.10) |
| Secrets in Inventory | 4 (Section 8.1) |
| Enforcement Levels | 4 (L1 MANDATORY to L4 ADVISORY) |
| Git Branch Types | 5 (main, feature, fix, hotfix, release) |
| Commit Types | 8 (feat, fix, refactor, perf, test, docs, chore, security, hotfix) |
| Performance Benchmarks | 6 (Section 7.6) |
| Log Retention Policies | 8 (Section 6.10) |

---

### Standards Compliance Checklist (Master)

Before any production deployment, confirm all of the following:

**Architecture**
- [ ] No circular imports between any two modules
- [ ] No reverse layer dependency (lower layer imports higher layer)
- [ ] No singleton instantiated directly — all via getter functions
- [ ] All configuration values in `config.py`; no hardcoded thresholds

**Modules**
- [ ] Every modified Python file has a module docstring
- [ ] Every public class has a class docstring
- [ ] Every public method has a function docstring
- [ ] No file exceeds 600 lines; no function exceeds 50 lines
- [ ] All class-level constants accessed with `self.` inside methods
- [ ] No wildcard imports; all imports at top of file

**Safety**
- [ ] Kill-switch check is first gate in `order_manager.submit()`
- [ ] RiskApproval expiry check present in `order_manager.submit()`
- [ ] DecisionRecord existence check present before order submission
- [ ] `PAPER_TRADING` check prevents broker calls when True
- [ ] Stop-loss mandatory: `risk_manager_ai` rejects without stop_price

**State**
- [ ] All shared mutable state has a corresponding `threading.Lock`
- [ ] No lock held across any I/O operation
- [ ] CSV journal opened in append mode only
- [ ] Trade records inserted only — never updated or deleted

**Observability**
- [ ] All layer calls wrapped in `system_monitor.time_layer()`
- [ ] All exceptions logged with `logger.exception()` (full traceback)
- [ ] Cycle ID propagated through all layer calls
- [ ] Kill-switch events logged at CRITICAL

**Testing**
- [ ] All 16 mandatory unit test cases pass
- [ ] All 5 mandatory integration test scenarios pass
- [ ] No test makes real network calls
- [ ] No test uses production database
- [ ] Test coverage ≥ 70% (measured by `pytest --cov`)
- [ ] Security scan clean (`bandit` zero HIGH; `pip audit` zero HIGH/CRITICAL)

**Security**
- [ ] No secrets in any committed file
- [ ] All SQL queries parameterised (no string concatenation)
- [ ] All HTTP requests use TLS with `verify=True` (default)
- [ ] Telegram chat_id verified in every command handler

**Process**
- [ ] `Files Modified` table updated in `copilot-instructions.md`
- [ ] VPS deploy executed: `git push`, SSH pull, `docker compose build --no-cache`, `docker compose up -d`
- [ ] Both containers `Up ... (healthy)` in `docker compose ps`
- [ ] No ERROR or CRITICAL in `docker logs ai-trading-brain --tail 50`
- [ ] `/status` Telegram command returns HEALTHY

---

### Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | 2026-07-02 | Engineering Architecture Agent | Initial complete document — all 10 Parts |

---

### Governing Documents

| Document | Role |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority — governs all behaviour |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Parent document — engineering architecture |
| `ARCHITECTURE.md` | Technical architecture reference |
| `copilot-instructions.md` | Operational procedures — deployment and change log |
| `ENGINEERING_STANDARDS.md` | **This document** — engineering constitution for development |

---

*Engineering Standards — Version 1.0.0*
*Classification: Internal Engineering Authority — MANDATORY*
*Effective: 2026-07-02*
*Governed by: Investment Intelligence Operating System (Constitutional Authority)*
*Maintained by: Engineering Architecture Agent under Human Principal supervision*
*Next Review: 2026-10-02 (Quarterly)*

---

## SUPPLEMENT A — CODING STYLE REFERENCE

### A.1 Python Code Style

The AI Trading Brain follows PEP 8 with the following project-specific extensions. All style rules are enforced by `pylint`.

| Style Rule | Standard | Example Compliant | Example Non-Compliant |
|---|---|---|---|
| Line length | 100 characters maximum | `result = self.risk_manager.approve(rec)` | Line of 120+ chars |
| Indentation | 4 spaces (no tabs) | `    def fetch(self):` | `  def fetch(self):` (2 spaces) |
| Blank lines between functions | 2 blank lines at module level | `\n\ndef next_function():` | 1 blank line |
| Blank lines between methods | 1 blank line | `\n    def second_method(self):` | No blank line |
| String quotes | Double quotes preferred | `"GlobalSnapshot"` | `'GlobalSnapshot'` (acceptable but less consistent) |
| F-strings for formatting | Always | `f"Symbol: {symbol}, Price: {price}"` | `"Symbol: " + symbol` |
| Type annotations | Required for public methods | `def fetch(self, force: bool = False) -> GlobalSnapshot:` | `def fetch(self, force=False):` |
| Trailing whitespace | Never | `    return result` | `    return result   ` |
| Comparison to None | `is None` / `is not None` | `if result is None:` | `if result == None:` |
| Comparison to bool | `if flag:` / `if not flag:` | `if is_stale:` | `if is_stale == True:` |

---

### A.2 Import Organisation Style

Imports are organised in three groups, separated by blank lines, in the following order:

```
# Group 1: Python standard library
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

# Group 2: Third-party packages
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler

# Group 3: Internal project modules
import config
from data_feeds.data_feed_manager import get_feed_manager
from system_monitor.system_monitor import SystemMonitor
```

Within each group, imports are sorted alphabetically by module name.

---

### A.3 Class Structure Style

Classes are structured in the following canonical order:

| Position | Element | Example |
|---|---|---|
| 1 | Class docstring | `"""Order management: submits and tracks orders."""` |
| 2 | Class-level constants | `_APPROVAL_VALIDITY_SECONDS = 30` |
| 3 | `__init__` method | `def __init__(self, ...):` |
| 4 | Public properties | `@property def conviction_score(self):` |
| 5 | Primary public methods | `def submit(self, decision_record, risk_approval):` |
| 6 | Secondary public methods | `def close_position(self, position_id):` |
| 7 | Private helper methods | `def _validate_approval(self, record):` |
| 8 | Class-level utilities | `@classmethod def from_config(cls):` |

---

### A.4 Dataclass and Typed Object Style

All data transfer objects (DTOs) that cross module boundaries use `dataclass` or typed namedtuple:

| Rule | Detail |
|---|---|
| Use `@dataclass` for mutable transfer objects | `@dataclass class RegimeSignal:` |
| Use `@dataclass(frozen=True)` for immutable transfer objects | `@dataclass(frozen=True) class GlobalSnapshot:` |
| All fields have type annotations | `confidence: float` — not just `confidence` |
| All fields with defaults follow required fields | Python dataclass ordering rule |
| `__post_init__` validates invariants | Validate ranges and required combinations on creation |
| Use `field(default_factory=...)` for mutable defaults | `evidence_set: List[str] = field(default_factory=list)` |

---

### A.5 Context Manager Style

Context managers are used for all resource acquisition:

| Resource | Context Manager | Example |
|---|---|---|
| File handles | `with open(path, 'a') as f:` | Always; never `f = open(path)` |
| Database connections | `with sqlite3.connect(db_path) as conn:` | Always |
| Layer timing | `with system_monitor.time_layer("LayerName"):` | All layer calls |
| Threading locks | `with self._positions_lock:` | All lock acquisitions |
| Temporary files | `with tempfile.NamedTemporaryFile() as tmp:` | All temp file usage |

---

## SUPPLEMENT B — STANDARD OPERATING PROCEDURES

### B.1 Adding a New Module

When adding a new Python module to an existing package:

| Step | Action | Verify |
|---|---|---|
| 1 | Confirm the new module fits within the package's declared responsibility | Package Responsibility Matrix (Part II, 2.10) |
| 2 | Create the module file with `snake_case.py` name | Naming Standards (Part III, 3.2) |
| 3 | Write the module docstring (mandatory) | Documentation Standards (Part V, 5.1) |
| 4 | Implement the primary class with class docstring | Documentation Standards (Part V, 5.2) |
| 5 | Export the class from the package `__init__.py` | Repository Standards (Part II, 2.2) |
| 6 | Write unit tests in `tests/unit/<package>/test_<module>.py` | Testing Standards (Part VII, 7.2) |
| 7 | Update the package `README.md` | Documentation Standards (Part V, 5.6) |
| 8 | Add new dependencies to `requirements.txt` (if any) | Repository Standards (Part II, 2.7) |
| 9 | Update `Files Modified` table in `copilot-instructions.md` | Process Rules (Part X, H-04) |
| 10 | Deploy and verify | Deployment Rules (Part X, H-01, H-02) |

---

### B.2 Adding a New Configuration Value

| Step | Action |
|---|---|
| 1 | Add the value to `config.py` with `UPPER_SNAKE_CASE` name and an inline comment explaining its purpose |
| 2 | Add validation in `validate_config()`: check type, range, and that the value is present |
| 3 | Reference only from modules via `config.VALUE_NAME` — never hardcode the value in a module |
| 4 | Update the Configuration Keys table in `copilot-instructions.md` if the value is a key operational parameter |
| 5 | Run the full test suite (config change may affect module behaviour) |
| 6 | Deploy |

---

### B.3 Adding a New Thread

| Step | Action |
|---|---|
| 1 | Record the decision to add a thread as an ADR (architectural decision) |
| 2 | Assign the thread a name (`threading.Thread(name="NewThread", ...)`) |
| 3 | Set `daemon=True` unless the thread must complete before process exit |
| 4 | Register the thread in the Thread Registry (`AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` Supplement C.1) |
| 5 | Add a heartbeat mechanism and corresponding heartbeat check in the monitoring system |
| 6 | Add the thread to the Shared State Inventory if it accesses any shared data structure |
| 7 | Write a concurrency test confirming the thread is safe under concurrent access |
| 8 | Verify the deadlock prevention analysis is still complete (no new deadlock cycle introduced) |

---

### B.4 Responding to a Dependency CVE

| CVE Severity | Response Time | Required Action |
|---|---|---|
| CRITICAL | Immediate (same day) | Update or replace the dependency; deploy fix; document |
| HIGH | Within 48 hours | Update or replace; deploy fix; document |
| MEDIUM | Within 7 days | Evaluate; update or document risk acceptance |
| LOW | Within 30 days | Evaluate; document disposition |

**CVE response procedure:**
1. Identify the affected package and CVE
2. Check if the vulnerable code path is reachable in this system
3. If reachable: update to a patched version; if no patch: replace the library or implement a workaround
4. Run full test suite to confirm no regression
5. Record the CVE response in the commit message (`security:` type)
6. Deploy

---

### B.5 Post-Incident Engineering Checklist

After any production incident, complete this checklist within 24 hours:

- [ ] Incident description written (what happened; when; impact)
- [ ] Root cause identified (not "human error" — what in the system allowed the error)
- [ ] Timeline reconstructed from logs (`cycle_id` trace if available)
- [ ] Immediate fix documented
- [ ] Regression test added that would have caught the issue
- [ ] Standards review: which standard was missing or violated?
- [ ] Standards update if the existing standards did not cover this case
- [ ] Knowledge shared with Human Principal via Telegram or document

---

## SUPPLEMENT C — STANDARDS APPLICABILITY MATRIX

### C.1 Part Applicability by Artefact Type

| Artefact Type | Part I | Part II | Part III | Part IV | Part V | Part VI | Part VII | Part VIII | Part IX | Part X |
|---|---|---|---|---|---|---|---|---|---|---|
| Python production module | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Python test module | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ |
| Configuration file | ✓ | ✓ | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ |
| Shell/PowerShell script | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ |
| Docker image/compose | ✓ | ✓ | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ |
| Markdown documentation | ✓ | — | ✓ | — | ✓ | — | — | — | ✓ | ✓ |
| SQLite database | ✓ | — | ✓ | — | — | — | — | ✓ | — | ✓ |
| JSON strategy file | ✓ | ✓ | ✓ | — | ✓ | — | — | ✓ | — | ✓ |
| CSV journal file | ✓ | ✓ | ✓ | — | — | — | — | ✓ | — | ✓ |
| Git commits and branches | ✓ | — | ✓ | — | — | — | — | — | ✓ | ✓ |
| Log files | ✓ | — | ✓ | — | — | ✓ | — | ✓ | — | ✓ |
| Environment variables | ✓ | — | ✓ | — | — | — | — | ✓ | — | ✓ |

---

### C.2 Enforcement Level Summary

| Level | Label | Count of Rules at This Level | Action on Violation |
|---|---|---|---|
| L1 | MANDATORY | 52 rules | Code review failure; deployment blocked |
| L2 | REQUIRED | 15 rules | Code review comment; waiver required |
| L3 | RECOMMENDED | 3 rules | Code review note; no blocking |
| L4 | ADVISORY | 0 rules | Informational only |

---

---

## SUPPLEMENT D — COMPLETE NAMING QUICK REFERENCE

### D.1 Master Naming Table

This table provides the definitive at-a-glance naming reference for every category of artefact in the system.

| Artefact | Convention | Example | Key Rule |
|---|---|---|---|
| **FOLDERS** | | | |
| Layer package | `snake_case/` | `market_intelligence/` | Matches layer name |
| Test folder | `tests/<package>/` | `tests/risk_control/` | Mirrors source structure |
| Scripts folder | `scripts/` (flat) | `scripts/autostart.bat` | No sub-folders |
| Data folder | `data/` (flat) | `data/trading_brain.db` | No sub-folders |
| **FILES** | | | |
| Python module | `snake_case.py` | `order_manager.py` | File name = primary class name (snake) |
| Python test | `test_<module>.py` | `test_order_manager.py` | Prefix with `test_` |
| Config | `snake_case.py` | `config.py` | Single file |
| Markdown doc | `UPPER_SNAKE.md` | `ARCHITECTURE.md` | All caps |
| JSON strategy | `snake_case.json` | `momentum_breakout_v2.json` | Version in name |
| Log file | `<component>_<date>.log` | `trading_brain_2026-07-02.log` | ISO date |
| Backup | `<name>_backup_<datetime>` | `trading_brain_backup_20260702.db` | Datetime in filename |
| **PYTHON SYMBOLS** | | | |
| Class | `PascalCase` | `OrderManager` | Descriptive noun |
| Agent class | `PascalCase` + `AI` | `RiskManagerAI` | AI suffix for agents |
| Engine class | `PascalCase` + `Engine` | `DebateEngine` | Engine suffix |
| Monitor class | `PascalCase` + `Monitor` | `TradeMonitor` | Monitor suffix |
| Exception class | `PascalCase` + `Error` | `FeedTimeoutError` | Error suffix |
| Enum class | `PascalCase` | `RegimeType` | Category noun |
| Enum member | `UPPER_SNAKE_CASE` | `RegimeType.TRENDING_BULLISH` | Meaningful value |
| Public method | `snake_case()` verb | `get_quote()`, `submit()` | Verb phrase |
| Private method | `_snake_case()` | `_validate_approval()` | Single underscore |
| Boolean method | `is_` / `has_` prefix | `is_market_open()` | Question form |
| Factory method | `create_` / `from_` | `create_order_record()` | Action prefix |
| Singleton getter | `get_<class_snake>()` | `get_feed_manager()` | `get_` prefix |
| Local variable | `snake_case` noun | `regime_signal` | Meaningful noun |
| Boolean variable | `is_` / `has_` prefix | `is_stale`, `has_approval` | Question form |
| Class constant | `_UPPER_SNAKE` | `_APPROVAL_VALIDITY_SECONDS` | Underscore prefix |
| Module constant | `UPPER_SNAKE` | `LAYER_LATENCY_WARN_MS` | No underscore prefix |
| Type alias | `PascalCase` | `StrategyWeightMap` | Descriptive |
| **INFRASTRUCTURE** | | | |
| Environment variable | `UPPER_SNAKE_CASE` | `DHAN_API_KEY` | Service prefix |
| Config key | `UPPER_SNAKE_CASE` | `DAILY_LOSS_LIMIT` | Topic prefix |
| Docker image | `<project>-<component>` | `ai-trading-brain` | Lowercase, hyphens |
| Docker container | Same as image | `ai-trading-brain` | Matches image |
| Docker volume | `<project>-<purpose>` | `trading-data` | Hyphens |
| **DATABASE** | | | |
| Table | `snake_case` (plural) | `decisions`, `orders` | Plural noun |
| Column | `snake_case` | `decision_id`, `approved_at` | Descriptive |
| Primary key | `<singular_table>_id` | `order_id` | Table name + `_id` |
| Foreign key | `<referenced_table>_id` | `decision_id` (in orders) | Referenced table + `_id` |
| Index | `idx_<table>_<column>` | `idx_orders_submitted_at` | `idx_` prefix |
| Timestamp | `<event>_at` (UTC) | `created_at`, `closed_at` | Event + `_at` |
| Boolean column | `is_<state>` | `is_approved` | `is_` prefix |
| **GIT** | | | |
| Main branch | `main` | `main` | Fixed name |
| Feature branch | `feature/<desc>` | `feature/add-vix-threshold` | Lowercase, hyphens |
| Fix branch | `fix/<desc>` | `fix/paper-trade-journal` | Lowercase, hyphens |
| Hotfix branch | `hotfix/<desc>` | `hotfix/kill-switch-timing` | Lowercase, hyphens |
| Release tag | `v<M>.<m>.<p>` | `v1.2.3` | Semantic version |
| Archive tag | `archive/<name>-<date>` | `archive/legacy-broker-20260301` | Descriptive |
| **LOGGING** | | | |
| Logger name | `<package>.<module>` | `execution_engine.order_manager` | Package.module |
| Log file (app) | `<component>_<date>.log` | `trading_brain_2026-07-02.log` | Daily rotation |
| Log file (audit) | `audit_<date>.log` | `audit_2026-07-02.log` | Permanent retention |
| Correlation ID | `cycle_id` | UUID4 | Per-cycle |
| Decision ID | `decision_id` | UUID4 | Per-decision |

---

### D.2 Naming Anti-Pattern Reference

This table documents naming anti-patterns observed or likely in this codebase and the correct replacement.

| Anti-Pattern | Example | Why Wrong | Correct Pattern |
|---|---|---|---|
| Generic names | `data`, `result`, `tmp`, `obj` | No indication of what the data represents | `regime_signal`, `approval_record`, `scan_result` |
| Abbreviations without context | `rs`, `om`, `am`, `rr` | Unpronounceable; meaning not obvious from code | `regime_signal`, `order_manager`, `approval_record`, `reward_risk_ratio` |
| Mixed case module names | `OrderManager.py` | Python convention is snake_case for files | `order_manager.py` |
| CamelCase methods | `getQuote()`, `submitOrder()` | Python convention is snake_case | `get_quote()`, `submit_order()` |
| Bare name for class constant | `_THRESHOLD` (inside method) | Scope bug — accesses name from enclosing scope | `self._THRESHOLD` |
| `utils.py` or `helpers.py` | `utils.py` with 15 unrelated functions | Violates single responsibility | Split into named modules: `time_utils.py`, `symbol_utils.py` |
| Numbered names | `feed1`, `agent2`, `handler3` | No semantic content | `yahoo_feed`, `bull_agent`, `risk_handler` |
| Negative boolean names | `not_stale`, `not_approved` | Double negatives are confusing | `is_fresh`, `is_approved` |
| `type` or `class` as variable name | `type = "BULLISH"` | Shadows built-in | `regime_type`, `position_class` |
| Database columns as `id` only | `id` as primary key | Ambiguous in joins | `order_id`, `decision_id` |
| Hardcoded path in variable name | `HARDCODED_DB_PATH = "/app/data/..."` | Embedded in name suggests config | `DB_PATH = config.DB_PATH` |

---

## SUPPLEMENT E — STANDARDS AMENDMENT PROCEDURE

### E.1 When Standards May Be Amended

Standards in this document may be amended when:
- A standard is found to be practically unenforceable in the current system
- A new architectural pattern is adopted that requires a new standard
- A standard conflicts with a higher-priority constitutional article
- Operational experience demonstrates the standard produces unintended negative outcomes
- A quarterly review identifies a gap in coverage

Standards may NOT be amended because:
- An individual engineer finds a standard inconvenient for a specific implementation
- Time pressure makes compliance difficult
- A third-party tool does not natively support the standard

---

### E.2 Amendment Process

| Step | Action | Owner | Record |
|---|---|---|---|
| 1 | Draft the proposed amendment with: what changes, why, what the alternative is, and what the risk is | Any engineer | Proposal document |
| 2 | Record the proposal as an ADR in ENGINEERING_BLUEPRINT.md | Author | ADR entry |
| 3 | Engineering review: confirm the amendment does not violate IIOS constitutional articles | Engineering | Review comment in ADR |
| 4 | Human Principal sign-off | Human Principal | Written approval |
| 5 | Update this document (`ENGINEERING_STANDARDS.md`) with the amendment | Author | Commit with `docs:` type |
| 6 | Update the Version History table | Author | Minor version increment |
| 7 | Notify all active engineers of the change | Author | Telegram or written notice |

---

### E.3 Emergency Waiver Process

When a standard must be temporarily violated to address a production emergency:

| Step | Action |
|---|---|
| 1 | Document the violation and the reason in the commit message |
| 2 | Record the waiver in the Engineering Decision Register with `status: TEMPORARY` |
| 3 | Create a follow-up issue to resolve the non-conformance within 5 business days |
| 4 | Notify Human Principal of the emergency waiver |
| 5 | Resolve the non-conformance within the 5-day window; close the issue |

No emergency waiver may remain open for more than 5 business days. After 5 days, it becomes a violation.

---

## SUPPLEMENT F — GLOSSARY OF ENGINEERING TERMS

This glossary defines terms used throughout this document and the broader AI Trading Brain engineering vocabulary.

| Term | Definition |
|---|---|
| **ADR** | Architecture Decision Record — a structured document recording a significant engineering decision, its context, alternatives rejected, and rationale |
| **Agent** | An autonomous AI component within the IIOS that performs a specific analytical or decision-making function |
| **Atomic** | An operation that completes as a single indivisible unit; either fully completes or does not occur |
| **Conviction** | A numeric score (1.0–10.0) representing the aggregate confidence of all 5 debate agents in a trading hypothesis |
| **Critical path** | The sequence of operations that determines the total duration of a cognitive cycle |
| **Cyclomatic complexity** | A measure of the number of independent paths through a function; higher = harder to test and maintain |
| **Daemon thread** | A background thread that exits when the main process exits; Python: `threading.Thread(daemon=True)` |
| **DTO** | Data Transfer Object — a typed object used to pass structured data between modules |
| **EOD** | End of Day — scheduled post-market processing: learning, reporting, strategy health assessment |
| **Evolved strategy** | A trading strategy that emerged through the genetic/evolutionary algorithm in StrategyLab |
| **Fail-safe** | A system design where failures result in the safe state (e.g., orders blocked) rather than an unsafe state |
| **Feed adapter** | A concrete implementation of `BaseFeed` that acquires market data from a specific source |
| **GlobalSnapshot** | The primary output of GlobalIntelligence Layer 1: a structured object capturing the state of global markets |
| **Guardian** | The `RiskGuardianAgent` — the highest-priority monitoring thread responsible for kill-switch enforcement |
| **Hypothesis** | A proposed trade: instrument, direction, entry, stop, and target; produced by MetaStrategyController |
| **IIOS** | Investment Intelligence Operating System — the supreme constitutional document governing all AI Trading Brain behaviour |
| **Invariant** | A condition that must always be true; violation of an invariant is a system defect |
| **Kelly fraction** | A position sizing formula derived from win rate and reward-to-risk ratio; used by CapitalRiskEngine |
| **Kill-switch** | A `threading.Event` flag that, when set, blocks all order submissions; activated by RiskGuardian |
| **kNN** | k-Nearest Neighbours — the machine learning algorithm used by MetaLearning to predict strategy weights |
| **Layer** | One of the 17 IIOS operational layers; each has a defined position in the cognitive hierarchy |
| **Module** | A Python file containing a class or set of related functions; the basic unit of code organisation |
| **OOS** | Out-of-Sample — the portion of historical data reserved for validation, not used in strategy training |
| **Package** | A Python directory containing an `__init__.py`; corresponds to one layer or infrastructure component |
| **Paper trading** | A simulation mode where all orders are recorded in a CSV journal but no real broker calls are made |
| **Protected module** | A module where changes require explicit Human Principal approval before any modification |
| **Regime** | A classified market condition (e.g., TRENDING_BULLISH, RANGE_BOUND); used to select appropriate strategies |
| **Singleton** | A class that has exactly one instance; accessed via a getter function, never instantiated directly |
| **Staleness** | A data quality flag indicating that a cached value is older than its permitted maximum age |
| **Stop-loss** | A mandatory price level at which a position is automatically closed to limit losses |
| **Thread safety** | The property of code that remains correct when executed concurrently by multiple threads |
| **VIX** | Volatility Index — a market-derived measure of expected near-term volatility; above 45 triggers the kill-switch |
| **Walk-forward test** | A validation technique that tests strategy performance on successive OOS windows |
| **WAL mode** | Write-Ahead Logging — an SQLite mode that allows concurrent reads and serialised writes; required |
