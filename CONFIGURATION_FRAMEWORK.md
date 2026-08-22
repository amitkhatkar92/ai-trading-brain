# CONFIGURATION FRAMEWORK
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-CFG-FWK-001
**Version:** 1.0.0
**Status:** AUTHORITATIVE
**Classification:** Architecture Engineering Specification
**Owner:** Architecture Council
**Date:** 2026-07-04

---

## DOCUMENT PURPOSE

This document defines the complete Configuration Framework for the Investment
Intelligence Operating System (IIOS). The Configuration Framework is the single
source of truth for how every configurable aspect of IIOS is managed throughout
its lifecycle.

The Configuration Framework governs configuration management for:
- Core system and infrastructure
- Every engine in the 17-stratum hierarchy
- Every AI agent operating within engines
- Every model and prediction system
- Every strategy and its parameters
- Every workflow and execution pipeline
- Every deployment environment
- Every infrastructure component

This document defines architecture exclusively.
It does not contain source code, API definitions, or database schemas.
It is an engineering specification that defines how configuration works — not
what the configuration values are.

---

## SCOPE

| In Scope | Out of Scope |
|----------|-------------|
| Configuration architecture and design | Actual configuration values |
| Configuration component specifications | Source code implementation |
| Configuration governance framework | Database schemas |
| Configuration lifecycle design | API endpoint definitions |
| Configuration quality standards | Deployment scripts |
| Configuration constitutional rules | Test implementations |
| Configuration readiness certification | UI/Dashboard designs |

---

## TABLE OF CONTENTS

- Part I — Configuration Philosophy
- Part II — Configuration Taxonomy
- Part III — Configuration Architecture
- Part IV — Configuration Hierarchy
- Part V — Configuration Lifecycle
- Part VI — Configuration Services
- Part VII — Configuration Quality Framework
- Part VIII — Configuration Governance
- Part IX — Configuration Constitution
- Part X — Configuration Readiness Checklist
- Supplement A — Configuration Taxonomy Reference
- Supplement B — Configuration Hierarchy Diagrams
- Supplement C — Inheritance Matrix
- Supplement D — Override Matrix
- Supplement E — Governance Decision Records
- Supplement F — Configuration Anti-Patterns
- Supplement G — Operational Runbook
- Supplement H — Comprehensive Glossary

---

# PART I — CONFIGURATION PHILOSOPHY

## 1.1 What Is Configuration?

Configuration is the collection of externalized, runtime-variable properties that
govern the behavior of a system without requiring changes to the system's deployed
code. Configuration exists at the boundary between the static software artifact
(compiled or packaged code) and the dynamic operational environment in which it runs.

In IIOS, configuration is everything that:
- Changes between environments (development, paper trading, live production)
- Changes over time without a code deployment
- Differs between deployment instances
- Can be adjusted by operators without developer involvement
- Controls system behavior without altering system logic

Configuration is NOT:
- Business logic that determines how to compute a value
- Algorithms that process data
- The structure of the data being processed
- Hardwired constraints that are invariants of the system design

The fundamental test for whether something is configuration: **"Could this value
be different in a different context while the system remains correct?"** If yes,
it is configuration. If changing the value would require logic changes to remain
correct, it is code.

---

## 1.2 Configuration vs Code

The distinction between configuration and code is one of the most important
architectural boundaries in IIOS. Misclassifying code as configuration — or
configuration as code — causes deep systemic problems.

### Code Characteristics
- Expresses logic, computation, and transformation
- Describes how to arrive at a result
- Is deterministic given the same inputs
- Changes require a software deployment
- Is versioned in the software version
- Reviewed by engineers for correctness

### Configuration Characteristics
- Expresses values, thresholds, and parameters
- Describes what result is acceptable
- Can change without affecting logic correctness
- Changes do not require software deployment
- Is versioned in the configuration version
- Reviewed by operators and architects for appropriateness

### The Critical Boundary

The kill switch threshold illustrates the boundary clearly. The value "45" for the
VIX kill threshold is configuration: it can be changed to "42" or "50" and the
system remains correct — the logic for checking VIX against a threshold is unchanged.
However, the logic "if VIX exceeds threshold, halt all trading" is code: changing
this logic to "if VIX exceeds threshold, reduce position size" is a code change,
not a configuration change, because it changes what the system does.

### IIOS Configuration-Code Boundary Rules

1. Numeric thresholds that govern decisions are configuration.
2. The logic that applies those thresholds is code.
3. Feature flags (enable/disable behaviors) are configuration.
4. The behaviors themselves are code.
5. Timeout values, retry counts, and interval durations are configuration.
6. The retry and timeout mechanisms are code.
7. Strategy parameters (lookback periods, signal thresholds) are configuration.
8. Strategy logic (how signals are computed from data) is code.
9. Agent weights and scoring biases are configuration.
10. Agent reasoning and argument construction are code.

---

## 1.3 Configuration vs Data

Configuration and operational data are both stored externally from code, but they
serve fundamentally different purposes and are managed differently.

### Configuration Properties
- Governs system behavior
- Changes infrequently (hours to months between changes)
- Applies system-wide or to large subsystems
- Set by humans (operators, architects)
- Version-controlled
- Subject to governance approval
- Has a defined schema

### Data Properties
- Represents observed facts about the world
- Changes continuously (milliseconds to seconds)
- Applies to specific entities (trades, positions, prices)
- Generated by system operation or external feeds
- May or may not be version-controlled
- Generated by automated processes
- Has a defined schema but schema changes separately from data

### The Boundary in IIOS

Market price data is data. The price feed timeout (8 seconds) is configuration.
A trade record is data. The maximum position size (20% of portfolio) is configuration.
A historical backtest result is data. The promotion gate thresholds (win rate >= 50%)
are configuration. A strategy's fitness score is data. The fitness score evaluation
formula weights are configuration.

---

## 1.4 Configuration vs Knowledge

IIOS is a knowledge-intensive system with explicit knowledge representations in
its learning and intelligence subsystems. Knowledge and configuration are distinct.

### Knowledge in IIOS
- The regime-strategy map (which strategies perform in which regimes) — a learned
  knowledge structure that evolves as the system observes market outcomes.
- Strategy fitness scores — knowledge about past performance.
- k-NN model weights for strategy selection — learned knowledge.
- Correlation matrices between global indices and NSE — learned knowledge.

### Configuration in IIOS
- Which knowledge refresh interval to use — configuration.
- The minimum fitness score for a strategy to remain active — configuration.
- The number of nearest neighbors (k) in the k-NN model — a model hyperparameter,
  which is a form of configuration.
- The decay rate for historical fitness records — configuration.

The distinction: knowledge is what the system has learned about the world through
observation and processing. Configuration is what operators have decided about how
the system should behave.

---

## 1.5 Configuration vs Parameters

Parameters are a specific subset of configuration. All parameters are configuration,
but not all configuration is parameters. The distinction matters for governance.

### Model Parameters
Model parameters (also called hyperparameters) are configuration values that
govern the behavior of models and algorithms. They include: learning rates,
window sizes, lookback periods, smoothing factors, regularization coefficients,
confidence thresholds.

Model parameters differ from general configuration in that:
- They are often set through empirical optimization (backtesting, grid search)
  rather than operational judgment.
- They may be updated more frequently as models are retrained.
- Changing them requires model performance validation, not just operational review.
- They may have interactions (changing parameter A requires re-evaluating parameter B).

In IIOS, model parameters are subject to the same governance structure as all
configuration, but with an additional validation requirement: any change to a model
parameter must be accompanied by backtesting evidence supporting the change.

---

## 1.6 Configuration vs Policy

Policy is a higher-level concept than configuration. A policy is a decision rule
governing system behavior. Configuration implements policies.

### The Relationship

Policy: "The system shall halt trading if the VIX exceeds a defined threshold."
Configuration: isk.kill_switch.vix_threshold = 45

Policy: "No single position shall exceed a defined percentage of total portfolio value."
Configuration: isk.position_limits.max_position_size_pct = 0.20

Policy: "Strategies with insufficient performance history shall not be permitted to trade."
Configuration: strategy_governance.min_trade_history = 20

### Policy vs Configuration Governance

Policy changes require Architecture Council approval because they change what the
system is designed to do. Configuration changes within an existing policy require
operational approval because they change how aggressively or conservatively the
policy is applied.

Example: Changing the kill switch threshold from 45 to 40 is a configuration change
within the existing kill switch policy — the policy (halt on VIX threshold) is
unchanged. Changing the kill switch to trigger on a portfolio value threshold instead
of VIX is a policy change requiring Architecture Council review.

---

## 1.7 Configuration vs State

State represents the current operational condition of the system. Configuration
governs how the system behaves. They are distinct:

### State
- Is produced by the system during operation.
- Changes as the system processes data and makes decisions.
- Represents facts about what is currently happening.
- Examples: current positions, current P&L, current VIX value, system health status.

### Configuration
- Is consumed by the system to govern its operation.
- Changes deliberately via a governance process.
- Represents operator decisions about how the system should behave.
- Examples: maximum positions allowed, daily loss limit, VIX kill threshold.

### Why the Distinction Matters

State is monitored. Configuration is governed. State can trigger configuration
changes (a persistent high-VIX regime might prompt an architectural decision to
lower the kill switch threshold), but this is a human governance decision, not
an automated state-to-configuration feedback loop. Automated configuration changes
based on system state are emergency overrides (see the Emergency Override configuration
category in Part II), which have their own governance requirements.

---

## 1.8 Configuration Lifecycle

Configuration has a complete lifecycle from conception to retirement:

`
CONCEPTION
    |
    v
DRAFTING -----> Proposed by operator or architect
    |
    v
VALIDATION -----> Schema validation, range check, consistency check
    |
    v
REVIEW -----> Peer review, security review
    |
    v
APPROVAL -----> Governance approval per category (see Part VIII)
    |
    v
PUBLICATION -----> Published to configuration repository
    |
    v
LOADING -----> Loaded by engines at startup or on dynamic refresh
    |
    v
ACTIVATION -----> Applied to running system (may require restart)
    |
    v
MONITORING -----> Monitored for effect and anomalies
    |
    v
MODIFICATION -----> Back to DRAFTING if change needed
    |             |
    v             v
VERSION        ROLLBACK -----> Previous version reactivated
UPGRADE
    |
    v
DEPRECATION -----> Marked as deprecated, successor identified
    |
    v
RETIREMENT -----> Removed from active configuration set
    |
    v
ARCHIVE -----> Preserved with historical record
`

---

## 1.9 Configuration Ownership

Every configuration item in IIOS has an owner. Ownership determines who can propose
changes, who must review changes, and who is accountable for correctness.

### Ownership Tiers

**Tier 1 — Architecture Council Owned:**
Top-level structural configuration, kill switch thresholds, constitutional configuration
values. Changes require Architecture Council vote. Applies to: system core configuration,
risk constitutional limits, engine lifecycle configuration.

**Tier 2 — Engine Owner Owned:**
Per-engine configuration governing the engine's behavior. Changes require engine
owner approval with Architecture Council notification. Applies to: engine operational
parameters, model hyperparameters, strategy parameters.

**Tier 3 — Operations Owner Owned:**
Deployment and infrastructure configuration. Changes require operations team approval.
Applies to: deployment environments, infrastructure settings, monitoring thresholds.

**Tier 4 — Feature Owner Owned:**
Feature flags and experimental configuration. Changes require feature owner approval.
Applies to: feature flags, A/B test parameters, experimental settings.

---

## 1.10 Configuration Governance

Configuration governance is the framework of processes, approvals, and controls
that ensure configuration changes are safe, traceable, and reversible.

Governance is detailed in Part VIII. The foundational principles are:

1. **No undocumented changes.** Every configuration change is documented with:
   the old value, the new value, the rationale, and the approver.

2. **No unreviewed changes.** Every configuration change is reviewed before
   activation by at least the owner and one other qualified reviewer.

3. **No irreversible changes.** Every configuration change preserves the ability
   to roll back. The previous configuration version is always available.

4. **No surprise changes.** Configuration changes affecting risk limits, kill
   switch thresholds, or decision thresholds are communicated to all stakeholders
   before activation.

5. **No unauthorized changes.** Configuration changes are made only by authorized
   persons acting within their ownership scope.

---

## 1.11 Configuration Hierarchy

IIOS configuration is organized in a strict inheritance hierarchy with 12 levels.
Higher levels provide defaults; lower levels provide overrides. Overrides propagate
downward only — lower levels can override higher levels, but higher levels cannot
override lower levels.

`
LEVEL 1:  Global Defaults  (highest precedence from base, lowest from overrides)
LEVEL 2:  Environment      (development, paper, production)
LEVEL 3:  Platform         (VPS, cloud, local)
LEVEL 4:  Infrastructure   (Docker, OS-level)
LEVEL 5:  Engine           (per-engine defaults)
LEVEL 6:  Workflow         (per-workflow settings)
LEVEL 7:  Strategy         (per-strategy parameters)
LEVEL 8:  Model            (per-model hyperparameters)
LEVEL 9:  Portfolio        (portfolio-level settings)
LEVEL 10: Session          (per-trading-session settings)
LEVEL 11: Runtime          (dynamically adjusted at runtime)
LEVEL 12: Emergency Override (highest override precedence — human safety valve)
`

The complete hierarchy design is detailed in Part IV.

---

## 1.12 Configuration Inheritance

Configuration inheritance is the mechanism by which lower-level configuration
inherits defaults from higher levels while being able to override specific values.

### Inheritance Principles

1. **Default-then-override:** A lower-level configuration starts with all values
   from the higher level and overrides only the values it explicitly specifies.

2. **Complete coverage:** Every configuration value must have a default somewhere
   in the hierarchy such that no engine ever encounters a missing required value.

3. **Override specificity:** The more specific (lower-level) an override, the
   higher its precedence. A per-engine value overrides a global default.

4. **No implicit inheritance gaps:** If a configuration value is consumed at level N
   but not defined at level N or any level above it, this is a configuration gap —
   a structural defect that must be resolved before deployment.

5. **Override traceability:** The effective value of any configuration at any level
   must be traceable to its source: which level defined it, when, and by whom.

---

## 1.13 Configuration Isolation

Configuration isolation ensures that changes to one engine's configuration cannot
unexpectedly affect another engine's behavior.

### Isolation Boundaries

**Hard isolation:** Engine A's configuration cannot be read by Engine B. Each engine
reads only its own configuration namespace and shared system-level configuration.

**Namespace isolation:** Configuration namespaces follow the pattern [engine_name].*.
No engine reads from another engine's namespace.

**Override isolation:** Environment-level overrides are applied per-namespace. An
override targeting isk_guardian.* does not affect execution_engine.*.

**Runtime isolation:** When configuration is dynamically refreshed for one engine,
other engines continue using their current configuration until their own refresh
cycle triggers.

---

## 1.14 Configuration Versioning

Every configuration item, configuration file, and configuration set is versioned.

### Versioning Scheme

**Schema version:** The version of the configuration schema definition. Changing
the schema (adding required keys, removing keys, changing value types) increments
the schema version.

**Value version:** The version of the configuration values for a given schema. Each
committed change to values increments the value version.

**Composite version:** The combination of schema version and value version uniquely
identifies a complete configuration state.

### Version History

All previous versions of all configuration are retained in the configuration
repository. No configuration version is ever deleted. This enables:
- Rollback to any previous configuration state.
- Audit of all changes made over the system's lifetime.
- Forensic analysis of what configuration was active during any past event.

---

*End of Part I*

---

# PART II — CONFIGURATION TAXONOMY

## 2.1 Taxonomy Overview

The IIOS configuration taxonomy organizes all configuration items into 24 categories.
Each category has a defined namespace, ownership tier, governance level, and validation
requirements. The taxonomy is exhaustive — every configuration item in IIOS belongs
to exactly one category.

---

## 2.2 Category 1 — System Configuration (system.*)

**Namespace:** system
**Owner:** Architecture Council (Tier 1)
**Governance:** Highest — Architecture Council approval required
**Volatility:** Very low — changes are rare and significant

System configuration governs the fundamental operating characteristics of the IIOS
platform itself. These settings apply to the entire system and override nothing below
them — they are the root of the configuration tree.

**Sub-categories:**

system.identity — System name, version, instance identifier, deployment region.
These values uniquely identify a running IIOS instance. They are set at deployment
time and do not change during an instance's lifetime.

system.mode — Operating mode (development, paper, production). This is the master
mode switch. Changing this value has the broadest effect of any single configuration
change in IIOS: it switches data feeds, broker adapter, risk limits, and logging verbosity.

system.lifecycle — Startup sequence configuration, shutdown grace period, restart
policy, health check intervals. These govern the system's own lifecycle management.

system.resources — CPU allocation, memory limits, file descriptor limits, thread
pool sizes. Resource configuration prevents runaway resource consumption.

system.telemetry — Global telemetry settings: whether telemetry is enabled, telemetry
endpoint, telemetry flush interval, telemetry retention.

**What belongs here:** Any setting that is singular for the entire deployment and
is not specific to any subsystem.

**What does NOT belong here:** Engine-specific settings, risk-specific settings,
or infrastructure settings.

---

## 2.3 Category 2 — Engine Configuration (engines.[engine_name].*)

**Namespace:** engines.[engine_name]
**Owner:** Engine Owner (Tier 2)
**Governance:** Engine Owner approval with Architecture Council notification
**Volatility:** Low to medium — changes when engine behavior needs tuning

Engine configuration governs the behavior of individual IIOS engines. Each of the
18 engines has its own configuration namespace. Engine configuration is subdivided
into operational settings (how the engine runs) and behavioral settings (what the
engine does).

**Sub-categories:**

engines.[name].operational — Timeout values, retry counts, cache TTLs, thread
counts, queue depths. These govern the engine's resource usage and resilience.

engines.[name].behavioral — Signal thresholds, scoring weights, filtering criteria.
These govern what the engine produces and how it makes decisions within its domain.

engines.[name].integration — Settings governing how the engine connects to external
systems (data feeds, broker APIs) or other engines (event subscriptions, shared cache).

engines.[name].monitoring — Engine-specific latency targets, health check parameters,
alerting thresholds.

engines.[name].governance — Audit logging settings, compliance configuration,
rate limits on engine outputs.

**Per-engine configuration namespaces:**
engines.global_intelligence.*
engines.market_intelligence.*
engines.meta_learning.*
engines.opportunity_engine.*
engines.strategy_lab.*
engines.capital_risk_engine.*
engines.risk_control.*
engines.market_simulation.*
engines.risk_guardian.* [PROTECTED]
engines.debate_and_decision.*
engines.execution_engine.*
engines.trade_monitoring.*
engines.learning_system.*
engines.performance_analytics.*
engines.research_lab.*
engines.validation_engine.*
engines.control_tower.*
engines.orchestrator.* [PROTECTED]

---

## 2.4 Category 3 — Workflow Configuration (workflows.[workflow_name].*)

**Namespace:** workflows.[workflow_name]
**Owner:** Engine Owner of the owning engine (Tier 2)
**Governance:** Engine Owner approval
**Volatility:** Low — workflows are stable once defined

Workflow configuration governs the execution of multi-step processes within engines.
A workflow is a named sequence of steps that transforms inputs into outputs. Workflow
configuration defines which steps execute, in what order, with what parameters, and
under what conditions.

**Sub-categories:**

workflows.[name].execution — Step sequence, step timeouts, step retry policies,
conditional branching logic triggers.

workflows.[name].error_handling — How errors at each step are handled: skip,
retry, abort, compensate.

workflows.[name].observability — Which steps emit events, what metrics are tracked,
how progress is logged.

**Examples of IIOS workflows and their configuration:**

workflows.global_fetch_workflow — Global data collection workflow. Configuration
includes: source priority order, per-source timeout, data validation mode (strict/lenient),
cache update trigger conditions.

workflows.full_decision_cycle — The complete 17-layer decision cycle. Configuration
includes: cycle step sequence, inter-step timeout, cycle abort conditions, partial
cycle behavior (what to do if layer N fails).

workflows.eod_learning_cycle — End-of-day learning workflow. Configuration includes:
which closed trades to include, learning update mode (incremental/batch), fitness
recalculation trigger.

---

## 2.5 Category 4 — Strategy Configuration (strategies.[strategy_id].*)

**Namespace:** strategies.[strategy_id]
**Owner:** Strategy Lab Engine Owner (Tier 2)
**Governance:** Engine Owner approval with backtesting validation
**Volatility:** Medium — parameters adjusted as market conditions evolve

Strategy configuration governs the operational parameters of trading strategies.
A strategy's logic (when to enter, when to exit, how to size) is code. Its parameters
(which lookback window, which threshold) are configuration.

**Sub-categories:**

strategies.[id].entry_parameters — Signal thresholds, confirmation requirements,
market condition filters for trade entry.

strategies.[id].exit_parameters — Stop-loss distance, take-profit target, trailing
stop behavior, time-based exit triggers.

strategies.[id].sizing_parameters — Position sizing formula inputs, maximum position
fraction, scaling factors.

strategies.[id].filter_parameters — Regime filters (strategy active only in specific
regimes), session filters (active only during specific market sessions), event filters.

strategies.[id].governance_parameters — Maximum trades per day, minimum hold period,
cooldown after loss, maximum consecutive losses before auto-disable.

strategies.[id].validation_parameters — Minimum backtest period, minimum trade count
for fitness evaluation, minimum Sharpe ratio for activation.

**Key IIOS strategy governance parameters (constitutional values):**
- Promotion gate: Win rate >= 50%
- Promotion gate: Sharpe ratio > 0.8
- Promotion gate: Maximum drawdown < 15%
- Auto-disable: Three consecutive losses
- Auto-disable: Drawdown exceeds 15%

---

## 2.6 Category 5 — Model Configuration (models.[model_id].*)

**Namespace:** models.[model_id]
**Owner:** Engine Owner of the owning engine (Tier 2)
**Governance:** Engine Owner approval with model validation evidence
**Volatility:** Low to medium — hyperparameters changed when model is retrained

Model configuration governs the hyperparameters of AI/ML models used within IIOS
engines. Model configuration is distinct from model weights (which are learned data,
not configuration) but governs how models are trained and applied.

**Sub-categories:**

models.[id].architecture — Model structure parameters: layer counts, layer sizes,
activation functions, attention mechanism parameters.

models.[id].training — Training hyperparameters: learning rate, batch size, epochs,
regularization strength, optimizer choice.

models.[id].inference — Inference parameters: confidence threshold for predictions,
ensemble voting rules, output post-processing parameters.

models.[id].validation — Model validation requirements: minimum accuracy threshold,
minimum test set size, cross-validation folds.

models.[id].lifecycle — Retraining trigger conditions: minimum data points before
retraining, maximum model age before mandatory retraining, performance degradation
threshold triggering retraining.

**IIOS model catalog:**
models.meta_learning_knn — k-NN strategy weight predictor in the Meta Learning engine.
models.regime_classifier — Market regime classifier in Market Intelligence.
models.opportunity_ranker — Opportunity ranking model in the Opportunity Engine.
models.decision_synthesizer — Decision synthesis model in Debate and Decision.
models.performance_predictor — Forward performance predictor in Research Lab.

---

## 2.7 Category 6 — Portfolio Configuration (portfolio.*)

**Namespace:** portfolio
**Owner:** Architecture Council (Tier 1) for limits; Engine Owner for preferences
**Governance:** Architecture Council for limits; Engine Owner for preferences
**Volatility:** Low for limits; medium for preferences

Portfolio configuration governs the overall portfolio structure, capital allocation
rules, and diversification requirements.

**Sub-categories:**

portfolio.capital — Total capital allocation, allocation currency, allocation basis
(absolute amount or fraction of total portfolio).

portfolio.limits — Maximum open positions, maximum sector exposure, maximum single-
symbol exposure, maximum strategy concentration.

portfolio.diversification — Minimum instruments in portfolio, minimum sector count,
correlation limits between open positions.

portfolio.rebalancing — Rebalancing trigger conditions, rebalancing frequency,
rebalancing method (immediate, gradual, threshold-triggered).

portfolio.accounting — P&L calculation method (mark-to-market, realized-only),
cost basis method (FIFO, LIFO, average), currency for P&L reporting.

---

## 2.8 Category 7 — Risk Configuration (isk.*)

**Namespace:** isk
**Owner:** Architecture Council (Tier 1) for constitutional limits
**Governance:** Architecture Council for constitutional limits; tightening allowed by Operations
**Volatility:** Very low — risk limits are constitutional constants

Risk configuration is among the most sensitive configuration in IIOS. The constitutional
risk limits (kill switch thresholds) are Architecture Council property and cannot be
relaxed by any lower governance tier. They can only be made more conservative (tighter).

**Sub-categories:**

isk.kill_switch — Kill switch trigger conditions and thresholds. These are
constitutional values:
- VIX threshold: default 45 (India VIX at which all trading halts)
- Daily loss threshold: default 2% of portfolio
- Strategy drawdown threshold: default 15% of strategy allocation

isk.position_sizing — Kelly criterion parameters, maximum position size, minimum
position size, position size rounding rules.

isk.exposure_limits — Maximum gross exposure, maximum net exposure, delta limits,
gamma limits, vega limits (for options strategies).

isk.concentration — Maximum position concentration by symbol, sector, strategy,
and market capitalization tier.

isk.correlation — Maximum allowed correlation between concurrent positions,
diversification requirements, correlation lookback window.

isk.liquidity — Minimum market volume requirements for entry, maximum fraction
of average volume for position size, exit market impact limits.

isk.stress — Stress scenario parameters for pre-trade stress testing: scenario
count, scenario severity, stress test pass threshold.

---

## 2.9 Category 8 — Learning Configuration (learning.*)

**Namespace:** learning
**Owner:** Learning System Engine Owner (Tier 2)
**Governance:** Engine Owner approval with performance validation
**Volatility:** Medium — updated as learning system evolves

Learning configuration governs how the IIOS learning system processes outcomes and
updates its knowledge representations.

**Sub-categories:**

learning.performance_tracking — Win rate calculation window, performance decay
factor, minimum trade sample size for statistical significance.

learning.strategy_management — Auto-disable rules, performance threshold for
auto-disable, re-enable conditions after disable.

learning.regime_mapping — How regime-strategy mappings are updated, minimum
observations per regime, regime map decay rate.

learning.knowledge_retention — How long performance history is retained, how
historical data is weighted vs recent data, data pruning schedule.

learning.feedback_loops — Which outcomes feed back into which models, feedback
delay (real-time vs EOD), feedback aggregation rules.

---

## 2.10 Category 9 — Prediction Configuration (prediction.*)

**Namespace:** prediction
**Owner:** Meta Learning and Research Lab Engine Owners (Tier 2)
**Governance:** Engine Owner approval with backtesting validation
**Volatility:** Low to medium

Prediction configuration governs the IIOS prediction subsystems, including forward
return prediction, regime prediction, and volatility prediction.

**Sub-categories:**

prediction.horizons — Prediction time horizons: intraday, daily, weekly.
prediction.confidence — Confidence threshold for acting on predictions.
prediction.ensemble — Ensemble voting rules when multiple models predict.
prediction.calibration — Calibration check requirements, calibration schedule.
prediction.staleness — Maximum prediction age before it is considered stale.

---

## 2.11 Category 10 — Simulation Configuration (simulation.*)

**Namespace:** simulation
**Owner:** Market Simulation Engine Owner (Tier 2)
**Governance:** Engine Owner approval
**Volatility:** Low

Simulation configuration governs the Monte Carlo simulation and scenario analysis
subsystems.

**Sub-categories:**

simulation.monte_carlo — Simulation count, random seed policy, variance model
parameters, correlation structure parameters.

simulation.scenarios — The 14 defined IIOS scenarios: which scenarios are active,
scenario severity parameters, scenario correlation structure.

simulation.stress_testing — Stress test pass/fail criteria, stress testing schedule,
stress test logging requirements.

simulation.backtesting — Backtesting window, train/test split ratio, walk-forward
window size, optimization approach.

---

## 2.12 Category 11 — Monitoring Configuration (monitoring.*)

**Namespace:** monitoring
**Owner:** Operations Team (Tier 3)
**Governance:** Operations approval
**Volatility:** Medium — adjusted as monitoring needs evolve

Monitoring configuration governs the observability and alerting subsystems.

**Sub-categories:**

monitoring.latency — Per-layer latency WARN and CRITICAL thresholds. The
IIOS baseline: WARN at 2,000ms, CRITICAL at 5,000ms. Override for Global
Intelligence: WARN at 5,000ms, CRITICAL at 12,000ms.

monitoring.health — OHS tier thresholds: OPTIMAL (0.95+), NOMINAL (0.80+),
DEGRADED (0.60+), CRITICAL (0.35+), FAILED (<0.35). These are constitutional values.

monitoring.alerts — Alert routing rules, alert deduplication window, escalation
thresholds.

monitoring.dashboards — Dashboard refresh intervals, widget configurations,
historical data windows for charts.

monitoring.metrics — Which metrics are collected, collection frequency, metric
retention period, metric aggregation rules.

---

## 2.13 Category 12 — Logging Configuration (logging.*)

**Namespace:** logging
**Owner:** Operations Team (Tier 3)
**Governance:** Operations approval
**Volatility:** Low

Logging configuration governs what is logged, at what level, and how logs are stored
and rotated.

**Sub-categories:**

logging.levels — Per-component log levels. The default hierarchy: CRITICAL >
ERROR > WARNING > INFO > DEBUG.

logging.rotation — Log rotation schedule (daily), retention (30 days active),
archive retention (90 days), compression settings.

logging.sanitization — Which patterns are sanitized from logs. All sensitive
patterns are always sanitized regardless of configuration.

logging.structured — Whether structured logging (JSON) is enabled, which fields
are included in structured log records.

logging.remote — Whether logs are shipped to a remote log aggregator, aggregator
endpoint, shipping interval.

---

## 2.14 Category 13 — Security Configuration (security.*)

**Namespace:** security
**Owner:** Architecture Council (Tier 1)
**Governance:** Architecture Council approval with security review
**Volatility:** Very low

Security configuration governs authentication, authorization, encryption, and
secret management. Security configuration is Architecture Council property because
weakening it could compromise the entire system.

**Sub-categories:**

security.authentication — API authentication requirements, token expiry, token
refresh behavior, authentication failure policy.

security.authorization — Role-based access control settings, permission inheritance,
authorization check caching.

security.encryption — Which data stores are encrypted, encryption algorithm selection
(AES-256 for at-rest), key rotation schedule.

security.secrets_management — Secret provider selection, secret rotation policy,
secret scanning schedule, baseline management.

security.audit — Security audit log requirements, audit log retention (minimum 12 months),
audit log integrity checking.

---

## 2.15 Category 14 — Deployment Configuration (deployment.*)

**Namespace:** deployment
**Owner:** Operations Team (Tier 3)
**Governance:** Operations approval with Architecture Council notification for major changes
**Volatility:** Low to medium

Deployment configuration governs how IIOS is packaged, deployed, and run in target
environments.

**Sub-categories:**

deployment.container — Docker image configuration, base image version, container
resource limits, health check definitions.

deployment.orchestration — Docker Compose settings, Kubernetes settings (future),
service discovery settings.

deployment.networking — Port assignments, network policies, TLS configuration,
reverse proxy settings.

deployment.storage — Volume mount points, data directory locations, backup
storage configuration.

deployment.scaling — Horizontal scaling settings (future), replica counts,
load balancing configuration.

---

## 2.16 Category 15 — Infrastructure Configuration (infrastructure.*)

**Namespace:** infrastructure
**Owner:** Operations Team (Tier 3)
**Governance:** Operations approval
**Volatility:** Low

Infrastructure configuration governs the underlying infrastructure on which IIOS
runs: server settings, OS-level configuration, network configuration.

**Sub-categories:**

infrastructure.server — VPS specifications, region, OS version, resource allocation.
infrastructure.database — Database file locations, connection pool sizes, journal mode.
infrastructure.network — DNS settings, firewall rules, VPN configuration.
infrastructure.storage — Disk allocation, backup storage, data retention volumes.

---

## 2.17 Category 16 — Environment Configuration (environment.*)

**Namespace:** environment
**Owner:** Operations Team (Tier 3)
**Governance:** Operations approval
**Volatility:** Low — environment definitions are stable

Environment configuration defines the complete set of settings that differ between
operational environments (development, paper, production).

**Environments in IIOS:**
- development — Local developer workstation. Verbose logging, mock data feeds,
  paper broker, relaxed timeouts.
- paper — Paper trading mode. Production data feeds, paper broker, production
  risk limits, production latency requirements.
- production — Live trading mode. Production data feeds, live broker, production
  risk limits, strict latency requirements.
- 	esting — CI/CD test environment. Mock data feeds, mock broker, accelerated
  timeouts, comprehensive logging.
- ci — CI pipeline environment. Subset of testing environment optimized for
  fast test execution.

---

## 2.18 Category 17 — AI Agent Configuration (gents.[agent_id].*)

**Namespace:** gents.[agent_id]
**Owner:** Engine Owner of the owning engine (Tier 2)
**Governance:** Engine Owner approval
**Volatility:** Medium — agent behavior evolves with system

AI Agent configuration governs the behavior of individual AI agents within IIOS
engines. The Debate and Decision engine's five agents are the primary consumers
of agent configuration.

**Sub-categories:**

gents.[id].persona — Agent role definition, reasoning style, argument biases,
expertise domain.

gents.[id].scoring — How the agent scores trade proposals, scoring weights for
different signal types, confidence calibration.

gents.[id].argument — Maximum argument length, minimum evidence requirement,
structured argument template.

gents.[id].debate — Position change conditions, rebuttal rules, concession
conditions.

**IIOS agent catalog (Debate and Decision engine):**
gents.signal_analysis_agent — Analyzes technical and quantitative signals.
gents.contrarian_agent — Presents the case against the proposed trade.
gents.risk_assessment_agent — Evaluates risk/reward and position sizing.
gents.opportunity_agent — Advocates for the trade opportunity.
gents.synthesis_agent — Synthesizes all arguments into a final score.

---

## 2.19 Category 18 — User Configuration (users.[user_id].*)

**Namespace:** users.[user_id]
**Owner:** User (Tier 4 — self-owned)
**Governance:** Self-approval for display preferences; Owner approval for behavior preferences
**Volatility:** High — users adjust preferences frequently

User configuration governs per-user display and notification preferences for the
Streamlit dashboard and Telegram bot.

**Sub-categories:**

users.[id].notifications — Which events trigger Telegram notifications, notification
frequency limits, notification formatting preferences.

users.[id].dashboard — Dashboard layout preferences, chart time horizons,
color scheme, default view.

users.[id].alerts — Custom alert thresholds (user-defined supplemental alerts
that do not override system alerts).

---

## 2.20 Category 19 — Feature Configuration (eatures.*)

**Namespace:** eatures
**Owner:** Feature Owner (Tier 4)
**Governance:** Feature Owner approval
**Volatility:** High during development; low once stable

Feature configuration (feature flags) enables or disables system capabilities
without code deployment. Feature flags allow gradual rollout, A/B testing, and
safe reversion of new capabilities.

**Feature flag types in IIOS:**

eatures.kill_switches — Flags that disable features (safety-first). A kill
switch feature flag disables a feature when 	rue. Kill switch flags default to
alse (feature enabled).

eatures.experiments — Flags that enable experimental features. Experiment flags
default to alse (feature disabled). Enabled only in specific environments.

eatures.gradual_rollout — Flags that enable features for a percentage of
decision cycles or a specific time window.

**Feature flag lifecycle:** All feature flags have an introduced_version, a
planned_removal_version, and a description. Flags without a removal plan are
reviewed quarterly.

---

## 2.21 Category 20 — Experimental Configuration (experiments.[experiment_id].*)

**Namespace:** experiments.[experiment_id]
**Owner:** Experiment Owner (Tier 4 — researcher or engineer running the experiment)
**Governance:** Self-approval; Architecture Council notified for system-wide experiments
**Volatility:** High — experimental configuration changes frequently during the experiment

Experimental configuration governs time-boxed investigations. Unlike feature flags,
experimental configuration includes the full parameter space being investigated.

**Sub-categories:**

experiments.[id].hypothesis — The question being answered by the experiment.
experiments.[id].parameters — The parameters being varied and their value ranges.
experiments.[id].duration — Experiment start date, planned end date, early stop criteria.
experiments.[id].scope — Which subsystems are affected by the experiment.
experiments.[id].evaluation — How the experiment's success or failure is determined.

---

## 2.22 Category 21 — Emergency Configuration (emergency.*)

**Namespace:** emergency
**Owner:** Architecture Council (Tier 1)
**Governance:** Architecture Council with single-approver override in genuine emergency
**Volatility:** Very low normally; high during active emergency

Emergency configuration provides a controlled mechanism for applying urgent
configuration changes that bypass the normal governance process. Emergency configuration
is the highest-precedence override layer.

**Conditions for emergency configuration:**
- System is experiencing a live trading emergency (unexpected market event, system
  failure, data feed failure).
- The normal governance process cannot be completed in time to prevent harm.
- A human decision-maker with Architecture Council authority authorizes the override.

**Emergency configuration properties:**
- Every emergency override has an explicit expiry time (maximum 24 hours).
- Emergency overrides are logged immediately upon activation.
- Emergency overrides must be reviewed and either replaced with proper configuration
  changes or removed before expiry.
- Emergency configuration cannot relax risk limits below constitutional minimums.
  (Emergency configuration can tighten limits; it cannot loosen them.)

---

## 2.23 Category 22 — Recovery Configuration (ecovery.*)

**Namespace:** ecovery
**Owner:** Operations Team (Tier 3)
**Governance:** Operations approval
**Volatility:** Low — recovery procedures are stable

Recovery configuration governs how IIOS recovers from failures, including process
restarts, data feed failures, broker disconnections, and container failures.

**Sub-categories:**

ecovery.restart — Auto-restart policies, restart delay, maximum restart attempts,
restart escalation procedure.

ecovery.data_feed — Fallback data feed configuration, reconnection policy,
stale data tolerance.

ecovery.broker — Broker reconnection policy, order state reconciliation procedure,
maximum broker disconnect tolerance.

ecovery.state — Checkpoint frequency, checkpoint storage, state reconstruction
procedure on restart.

ecovery.partial_cycle — What to do when a cycle step fails: skip and continue,
abort cycle, use previous cycle's output.

---

## 2.24 Category 23 — Compliance Configuration (compliance.*)

**Namespace:** compliance
**Owner:** Architecture Council (Tier 1)
**Governance:** Architecture Council approval with legal/regulatory review
**Volatility:** Very low — changes driven by regulatory requirements

Compliance configuration governs adherence to applicable trading regulations.

**Sub-categories:**

compliance.position_reporting — Position reporting thresholds, reporting frequency,
reporting format.

compliance.trade_reporting — Trade reporting requirements, audit trail completeness
requirements.

compliance.surveillance — Order-to-trade ratio limits, wash trade prevention,
spoofing prevention parameters.

compliance.data_retention — Regulatory data retention periods (minimum required
by applicable regulation).

---

## 2.25 Category 24 — Governance Configuration (governance.*)

**Namespace:** governance
**Owner:** Architecture Council (Tier 1)
**Governance:** Architecture Council vote
**Volatility:** Very low — governance structure is stable

Governance configuration governs the configuration governance system itself —
the meta-configuration of how configuration is governed.

**Sub-categories:**

governance.approval_tiers — Tier definitions, tier membership, tier approval
requirements (quorum, unanimous, single-approver).

governance.review_schedule — Configuration review frequency by category,
review documentation requirements.

governance.audit — Configuration audit schedule, audit scope, audit documentation.

governance.version_retention — How long configuration history is retained by
category.

---

*End of Part II*

---# PART III — CONFIGURATION ARCHITECTURE

## 3.1 Architecture Overview

The Configuration Architecture defines the complete set of components that implement
the Configuration Framework. These components work together to provide a reliable,
secure, auditable, and highly available configuration management system for IIOS.

`
CONFIGURATION ARCHITECTURE — COMPONENT MAP

[Configuration Repository]
        |
        v
[Configuration Version Manager] <---> [Configuration Audit Manager]
        |
        v
[Configuration Loader]
        |
        v
[Configuration Resolver] <---> [Configuration Cache]
        |
        v
[Configuration Validator]
        |
        v
[Configuration Registry]
        |
        +---> [Configuration Catalog]
        |
        +---> [Configuration Manager] <---> [Configuration Security Manager]
        |                                           |
        |                              [Configuration Monitoring Manager]
        |
        v
[Configuration Health Manager]
        |
[Configuration Analytics Manager] <---> [Configuration Backup Manager]
                                                    |
                                         [Configuration Recovery Manager]
`

All components communicate through defined interfaces. No component reads directly
from another component's internal state.

---

## 3.2 Component 1 — Configuration Registry

### Purpose
The Configuration Registry is the central index of all known configuration items
in IIOS. It maintains the authoritative catalog of every configuration key, its
type, its default value, its owner, its governance tier, and its validation rules.

### Responsibilities
- Maintain the complete set of registered configuration keys (namespace + key name).
- Store the metadata for each key: type, default, required/optional, owner, description.
- Provide the reference for validation (what keys are valid, what types are expected).
- Detect unregistered configuration keys (keys present in config files but not in
  the registry — a potential misconfiguration or injection attempt).
- Detect missing required keys (registered keys that have no value in any level of
  the hierarchy).
- Serve as the reference for schema documentation generation.

### Inputs
- Registration requests from engine initialization (engines register their keys on
  startup).
- Schema definition files (YAML schema definitions from config/ directory).
- Configuration file contents (for gap detection).

### Outputs
- Complete key catalog (list of all registered keys with metadata).
- Validation reference (type and range information for each key).
- Gap reports (missing required keys, unregistered keys present).
- Registry health status.

### Dependencies
- Schema definition files in config/engines/ and config/global_config.py.
- No runtime dependencies on other configuration components (it is initialized first).

### Interactions
- Configuration Validator queries the Registry for type and range information.
- Configuration Manager queries the Registry for ownership information.
- Configuration Catalog reads the Registry for catalog generation.
- Configuration Loader uses the Registry to validate keys being loaded.

### Failure Modes
- **Schema file parse error:** Registry initialization fails. System startup is
  blocked. The error is logged with the specific schema file and line.
- **Key registration conflict:** Two engines attempt to register the same key.
  The conflict is logged, and the second registration is rejected. Startup continues.
- **Missing schema file:** Specific engine's keys are unregistered. The engine is
  warned on startup that its configuration is not validated.

### Recovery Strategy
- On parse error: Fix the schema file and restart. No partial initialization.
- On registration conflict: Trace the two registrations, resolve the naming
  conflict, and restart.
- On missing schema: The engine operates with unvalidated configuration.
  A CRITICAL health alert is raised.

### Monitoring
- Registry initialization time (must complete within 2,000ms of system startup).
- Number of registered keys (tracked over time — sudden changes indicate unexpected
  additions).
- Registration conflict count (target: 0).
- Missing schema file count (target: 0).

### Scalability
The Registry is an in-memory data structure. It scales linearly with the number of
registered keys. At 20,000+ keys across 18 engines, it remains fast (< 1ms lookup).
No scalability concern for IIOS's expected lifetime.

### Extensibility
New engines register their keys on startup. No changes to the Registry component
are needed when new engines are added. The Registry is inherently extensible.

### Engineering Notes
- The Registry must be fully initialized before any other configuration component
  starts. It is the first component initialized in the configuration startup sequence.
- The Registry is read-heavy and write-once (keys are registered at startup and
  do not change at runtime). No locking is needed for reads after initialization.
- The Registry is the authoritative source for documentation generation tools.

---

## 3.3 Component 2 — Configuration Catalog

### Purpose
The Configuration Catalog provides a human-readable, searchable, and documented
view of all configuration items. It is the reference for operators and engineers
who need to understand what configuration is available and what it does.

### Responsibilities
- Generate documentation for every registered configuration key.
- Provide search capability by namespace, key name, owner, and description.
- Display current values alongside documentation (in appropriate security context).
- Generate configuration change history summaries.
- Produce configuration diffs between versions.
- Provide the reference for operator training and onboarding.

### Inputs
- Configuration Registry (for key metadata).
- Configuration Repository (for current and historical values).
- Configuration Audit Manager (for change history).

### Outputs
- Catalog documents (Markdown, HTML) for documentation system integration.
- Search results.
- Configuration diffs.
- Operator-facing value display (with security filtering).

### Dependencies
- Configuration Registry (must be initialized first).
- Configuration Repository (for value retrieval).
- Configuration Audit Manager (for history).

### Interactions
- Read-only access to Registry, Repository, and Audit Manager.
- Generates documentation consumed by docs/ system.
- Consumed by dashboard for configuration viewing.

### Failure Modes
- **Catalog generation failure:** Documentation is stale. The system continues
  operating normally. A warning is raised.
- **Search failure:** Operators cannot search the catalog. The system continues
  operating normally.

### Recovery Strategy
- Catalog generation failures are non-critical. Retry on next scheduled generation.
- Search failures are non-critical. Manual catalog review is available as a fallback.

### Monitoring
- Catalog generation success/failure rate.
- Catalog generation time.
- Number of keys documented vs registered (should be 100%).

### Engineering Notes
- The Catalog is generated periodically (e.g., on every CI run, on every configuration
  change, and on daily schedule). It is not real-time.
- The Catalog does not display secret values. All values from security.* namespace
  are redacted in catalog output.

---

## 3.4 Component 3 — Configuration Manager

### Purpose
The Configuration Manager is the central authority for configuration change
operations. It is the gatekeeper through which all configuration modifications
flow. No configuration change may bypass the Configuration Manager.

### Responsibilities
- Receive configuration change requests from authorized principals.
- Enforce ownership rules (reject changes from principals without appropriate authority).
- Coordinate the validation, approval, and publication pipeline for changes.
- Maintain the change queue for pending approvals.
- Apply approved changes to the Configuration Repository.
- Trigger notification to affected engines after a change is applied.
- Coordinate emergency override application.
- Maintain the change log.

### Inputs
- Configuration change requests (from authorized operators via CLI or API).
- Approval decisions from the governance workflow.
- Emergency override requests (with authorization credential).

### Outputs
- Change acceptance or rejection (with reason).
- Change status updates (pending, approved, rejected, applied).
- Post-change notifications to affected engines.
- Change log entries.

### Dependencies
- Configuration Registry (for ownership verification).
- Configuration Validator (for pre-change validation).
- Configuration Repository (for applying changes).
- Configuration Audit Manager (for logging all operations).
- Configuration Version Manager (for version management on change).
- Governance workflow (external: approval decisions).

### Interactions
- Primary interaction point for human operators making configuration changes.
- Coordinates with all other components in the change pipeline.
- Notifies engines via the Event Bus when their configuration has changed.

### Failure Modes
- **Change request queue overflow:** New changes are rejected until the queue
  is drained. Operators are notified.
- **Approval workflow failure:** Changes in the approval queue are not processed.
  The approval workflow coordinator is alerted.
- **Repository write failure:** A change is approved but cannot be written.
  The change is retained in the pending queue and retried. An alert is raised.
- **Notification failure:** A change is applied but the affected engine is not
  notified. The engine will receive the change on its next scheduled refresh.

### Recovery Strategy
- Queue overflow: Alert operator, drain queue by reviewing and either approving
  or rejecting pending changes.
- Approval workflow failure: Diagnose the governance workflow, retry pending approvals.
- Repository write failure: Fix the Repository connection, retry the write.
- Notification failure: The engine's next refresh cycle picks up the change.
  No immediate action required.

### Monitoring
- Change request queue depth (alert if > 10 items pending).
- Average time from request to application (target: < 30 minutes for Tier 2 changes,
  < 2 hours for Tier 1 changes).
- Change rejection rate (track to identify configuration issues).
- Emergency override count (target: 0 per month; any emergency override triggers
  a post-mortem).

### Scalability
The Configuration Manager handles a low-volume stream of changes. Configuration
changes are governance-gated and not high-frequency. No scalability concern.

### Engineering Notes
- The Configuration Manager is the only component that may write to the Configuration
  Repository. All other components have read-only access.
- All change operations are idempotent: applying the same change twice has the same
  result as applying it once.
- The Configuration Manager maintains a complete transaction log of all operations,
  not just successful ones. Failed operations are logged with their failure reason.

---

## 3.5 Component 4 — Configuration Validator

### Purpose
The Configuration Validator ensures that configuration values are correct before
they are accepted into the system. Validation catches errors early in the lifecycle
and prevents invalid configuration from causing runtime failures.

### Responsibilities
- Validate configuration values against their schema (type, format, range).
- Validate configuration consistency (no conflicting values within a configuration set).
- Validate configuration completeness (all required keys are present).
- Validate configuration inheritance correctness (overrides are compatible with
  their base definitions).
- Validate security constraints (no secrets in non-secret namespaces, required
  encryption settings present).
- Validate cross-reference integrity (referenced entities exist).
- Provide detailed validation error messages.

### Inputs
- Configuration values to validate (from change requests or file loads).
- Schema definitions from Configuration Registry.
- Cross-reference data (strategy IDs, engine names, environment names).

### Outputs
- Validation pass/fail result.
- Structured validation error report (key, violation type, expected vs actual).
- Validation warning report (non-blocking issues).

### Dependencies
- Configuration Registry (for schema definitions).
- Domain knowledge (for cross-reference validation: valid strategy IDs, engine names).

### Interactions
- Called by Configuration Loader before accepting a configuration file.
- Called by Configuration Manager before accepting a change request.
- Called by CI pipeline for pre-deployment validation.

### Failure Modes
- **Validator crash during validation:** Treated as a validation failure. The
  configuration is rejected. The validator error is logged as a system error.
- **Schema not found for key:** Treated as an unknown key. The unknown key
  is flagged as a validation warning. The key is processed with type-only validation.

### Recovery Strategy
- Validator crash: Fix the validator bug. All pending validations are rejected
  until the validator is restored.
- Missing schema: Register the schema in the Configuration Registry.

### Validation Rule Categories

**Type validation:** Is the value the correct type? (string, integer, float, boolean,
list, map, duration, percentage)

**Range validation:** Is the value within the acceptable range? (minimum, maximum,
enum membership)

**Format validation:** Does the value match the required format? (ISO date, IP address,
URI, cron expression)

**Consistency validation:** Are multiple related values internally consistent?
Example: isk.position_limits.min_position_size_pct must be less than
isk.position_limits.max_position_size_pct.

**Completeness validation:** Are all required values present?

**Security validation:** No secret values in non-secret namespaces. Required
encryption configuration is present in production environment.

**Governance validation:** Proposed changes do not violate constitutional limits
(e.g., production risk limits are not more relaxed than base configuration).

### Monitoring
- Validation success rate (by namespace).
- Most frequent validation error types (track to identify recurring issues).
- Validation time per request (performance).

---

## 3.6 Component 5 — Configuration Loader

### Purpose
The Configuration Loader is responsible for reading configuration from external
storage (files, environment variables, secrets manager) and assembling it into
the in-memory configuration state used by the system.

### Responsibilities
- Read configuration from all source locations in the correct priority order.
- Apply the 12-level hierarchy: read global defaults, then environment overrides,
  then engine-specific overrides, etc.
- Resolve environment variable references in configuration files.
- Handle missing optional files gracefully.
- Fail loudly on missing required files or required keys.
- Provide the initial configuration load at system startup.
- Provide incremental reload for dynamic configuration refresh.

### Inputs
- Configuration files from config/environments/.
- Configuration files from config/engines/.
- Environment variables.
- Secrets from secrets manager (for sensitive values).

### Outputs
- Assembled configuration state (the merged result of all sources).
- Load report (which files were loaded, which environment variables were applied,
  any overrides detected).

### Dependencies
- Configuration Validator (validates before accepting loaded configuration).
- Secrets manager (for secret values).
- File system (for configuration files).

### Source Priority Order (lowest to highest precedence)
`
1. Global defaults (config/environments/base.yaml)
2. Environment file (config/environments/[env_name].yaml)
3. Engine defaults (config/engines/[engine_name]_config.py)
4. Profile overlays (config/profiles/[profile_name].yaml)
5. Environment variables (IIOS_* prefix)
6. Emergency overrides (config/emergency/ if present)
`

### Failure Modes
- **Required configuration file missing:** System startup fails. Clear error
  message identifies the missing file.
- **Required key missing after full load:** System startup fails. Clear error
  message identifies the key and the engine expecting it.
- **Invalid YAML syntax:** File is rejected. System startup fails if it was required.
- **Environment variable type mismatch:** The variable value cannot be coerced
  to the expected type. Startup fails with a clear type error message.
- **Secrets manager unavailable:** Secret-dependent configuration is unavailable.
  If the secret is required (e.g., broker token), the dependent subsystem is
  disabled and an alert is raised.

### Recovery Strategy
- Missing required file: Add the file and restart.
- Missing required key: Add the key to the appropriate configuration file and restart.
- Invalid YAML: Fix the syntax error and restart.
- Secrets manager unavailable: Fix secrets manager connectivity. The fallback
  behavior (paper trading, data feed fallback) activates automatically.

### Monitoring
- Startup load time (how long the initial load takes).
- Number of files loaded.
- Number of environment variable overrides applied.
- Reload trigger frequency (how often dynamic configuration refreshes are triggered).

---

## 3.7 Component 6 — Configuration Resolver

### Purpose
The Configuration Resolver provides the runtime access point for all configuration
reads. When an engine needs a configuration value, it goes through the Resolver.
The Resolver abstracts the configuration hierarchy from the consuming engine.

### Responsibilities
- Provide a simple, type-safe API for configuration reads.
- Resolve the effective value by traversing the hierarchy from most specific to most general.
- Cache resolved values to minimize file system and registry lookups.
- Detect undefined references (engine requesting a key not in the Registry).
- Support dynamic configuration (values that may change during runtime).
- Provide type coercion for values read from environment variables or files.

### Inputs
- Configuration read requests from engines and components.
- Configuration state (from Loader, cached after initial load).
- Dynamic override notifications (from Manager on live changes).

### Outputs
- Resolved configuration values (typed).
- Resolution trace (which level in the hierarchy provided the effective value).

### Dependencies
- Configuration Cache (for performance).
- Configuration Loader (for initial state).
- Configuration Registry (for type information).

### Interactions
- Called by every engine component that needs a configuration value.
- Notified by Configuration Manager when a value changes.
- Reads from Configuration Cache first, falls back to Loader state.

### Failure Modes
- **Key not found:** Raises a ConfigurationKeyNotFoundError. The engine receives
  this error and must handle it (use default, log warning, or fail).
- **Type coercion failure:** Raises a ConfigurationTypeError. The engine must handle
  this error.
- **Cache miss on dynamic value:** Forces a Loader re-read. Acceptable performance
  cost. No functional failure.

### Engineering Notes
- The Resolver must be thread-safe. Multiple engine threads may read configuration
  concurrently. Write operations (cache invalidation, value updates) must not
  corrupt concurrent reads.
- The Resolver provides a "resolution trace" feature: given a key, it returns not
  just the value but which level of the hierarchy provided it. This is invaluable
  for debugging configuration issues.
- The Resolver never blocks. If it cannot resolve a value, it raises immediately
  rather than waiting.

---

## 3.8 Component 7 — Configuration Cache

### Purpose
The Configuration Cache provides high-performance in-memory storage for resolved
configuration values, reducing the overhead of repeated file system and hierarchy
traversal for frequently accessed configuration.

### Responsibilities
- Cache resolved configuration values in memory.
- Expire cached values on change notification from Configuration Manager.
- Expire cached values on TTL expiry for dynamic configuration.
- Provide cache statistics (hit rate, size, eviction rate).
- Implement thread-safe cache operations.

### Inputs
- Resolved values from Configuration Resolver.
- Cache invalidation notifications from Configuration Manager.
- Cache TTL definitions from configuration (meta-configuration).

### Outputs
- Cached values (on hit).
- Cache misses (triggering Resolver re-resolution).
- Cache statistics.

### Cache Strategy
- Static configuration (system, infrastructure, constitutional limits): Indefinite
  cache. Never expire until system restart or explicit invalidation.
- Engine operational configuration: 60-second TTL with change-triggered invalidation.
- Dynamic configuration (feature flags): 10-second TTL.
- Emergency overrides: No cache. Always read directly (ensures emergency changes
  take immediate effect).
- Strategy parameters: Cached until strategy is updated or system restarts.

### Failure Modes
- **Cache memory exhaustion:** Old entries are evicted LRU. Cache continues operating
  with reduced hit rate. Memory monitoring alert triggers.
- **Cache corruption:** The cache is cleared entirely and rebuilt from the Loader
  state. This is a high-cost recovery (cold cache) but correct.

### Monitoring
- Cache hit rate (target: > 95% for static configuration).
- Cache size (monitor for unexpected growth).
- Cache eviction rate (alert if evictions indicate memory pressure).
- Cache invalidation frequency (tracks how often dynamic configuration changes).

---

## 3.9 Component 8 — Configuration Repository

### Purpose
The Configuration Repository is the persistent store for all configuration state,
including current configuration, configuration history, and version metadata. It is
the ground truth for configuration values.

### Responsibilities
- Persist the current configuration state.
- Maintain the complete history of all configuration versions.
- Provide read access to current and historical configuration.
- Implement atomic writes (a configuration change is either fully written or not
  written at all — no partial states).
- Support rollback (restore a previous configuration version atomically).
- Provide configuration export (full or partial configuration dump).

### Inputs
- Configuration write requests from Configuration Manager (exclusively).
- Rollback requests from Configuration Manager.

### Outputs
- Current configuration state (on read).
- Historical configuration state (on historical read).
- Configuration version list.
- Configuration export.

### Dependencies
- Storage layer (file system or database, per deployment).
- No dependencies on other configuration components (it is foundational).

### Persistence Implementation
In IIOS, the Configuration Repository is implemented as a combination of:
- Version-controlled configuration files in the config/ directory (for static
  and environment-level configuration — files committed to git).
- A runtime configuration database in data/databases/config.db (for runtime
  state, dynamic overrides, and version history metadata).

### Failure Modes
- **File system write failure:** Configuration change is rejected. The current
  configuration state is unchanged (write atomicity preserved).
- **Database write failure:** Version history write fails. The configuration value
  is still applied (the value write is separate from the history write). A warning
  is raised: the history may be incomplete.
- **Repository corruption:** Configuration cannot be read. System startup fails.
  Recovery from backup is required.

### Recovery Strategy
- Write failure: Fix the underlying storage issue and retry the write.
- Repository corruption: Restore from the Configuration Backup Manager's most
  recent backup. Apply any changes since the backup from the git history.

### Monitoring
- Write success/failure rate.
- Repository size (track growth over time).
- Backup age (alert if backup is older than 24 hours).
- Read latency (alert if configuration reads are slow, indicating storage issues).

---

## 3.10 Component 9 — Configuration Version Manager

### Purpose
The Configuration Version Manager tracks the evolution of configuration over time.
It assigns version numbers to configuration states, maintains the version lineage,
and provides rollback capability.

### Responsibilities
- Assign version numbers to configuration states on each change.
- Maintain the version lineage (version N was derived from version N-1).
- Tag versions with metadata (timestamp, author, change description, approval record).
- Support rollback to any previous version.
- Support version diff (show what changed between two versions).
- Enforce version retention policy.
- Detect version conflicts (concurrent modifications to the same configuration).

### Version Numbering Scheme

Configuration versions follow a composite scheme:
`
[schema_version].[value_version].[patch]

Examples:
  1.0.0 — Initial configuration, schema version 1.
  1.1.0 — Configuration values updated, schema unchanged.
  2.0.0 — Schema version changed (new required keys added).
  1.1.1 — Patch correction to a value version.
`

Schema version increments when the structure of configuration changes (new required
keys, removed keys, type changes). Value version increments when values change within
the same schema. Patch increments for small corrections.

### Inputs
- Configuration change requests (from Configuration Manager).
- Rollback requests.
- Version query requests.

### Outputs
- Version numbers for new configuration states.
- Version history list.
- Version diff reports.
- Rollback confirmation.

### Failure Modes
- **Version number collision:** Two concurrent changes are assigned the same version.
  The conflict is detected and one change is rejected. The rejected change is
  requeued with a new version number.
- **Version history database failure:** New versions cannot be recorded. Changes
  are still applied (values are persisted), but version history is lost until the
  database is restored. A CRITICAL alert is raised.

### Recovery Strategy
- Version collision: Serialized retry with conflict detection.
- History database failure: Restore from backup, reconstruct recent changes from
  Configuration Manager's change log.

### Monitoring
- Current configuration version (tracked as a telemetry metric).
- Version change frequency (track to identify unusual change patterns).
- Rollback frequency (target: 0 per month; any rollback triggers a review).

---

## 3.11 Component 10 — Configuration Audit Manager

### Purpose
The Configuration Audit Manager provides an immutable, comprehensive record of all
configuration activity. It is the security and compliance record for the configuration
system.

### Responsibilities
- Record every configuration read that accesses sensitive configuration.
- Record every configuration change attempt (approved, rejected, failed).
- Record every configuration approval decision.
- Record every emergency override activation and deactivation.
- Record every rollback operation.
- Provide audit query capability (who changed what, when, and why).
- Ensure audit records are tamper-evident.
- Enforce audit retention policy (minimum 12 months, configurable).

### Audit Record Structure

Each audit record contains:
- Timestamp (ISO 8601 with millisecond precision, UTC)
- Operation type (read, change, approve, reject, rollback, emergency)
- Actor (who performed the operation — system principal or human identifier)
- Subject (which configuration key or namespace was affected)
- Old value (for changes — redacted if from security namespace)
- New value (for changes — redacted if from security namespace)
- Rationale (for changes — the documented reason)
- Authorization reference (approval record identifier)
- Outcome (success, failure, partial)
- System state at time of operation (engine health, trading mode)

### Inputs
- Events from all other configuration components.
- Time (for timestamps).

### Outputs
- Audit records (written to audit store).
- Audit query results.
- Compliance reports.

### Tamper Evidence
Audit records include a hash chain: each record contains the hash of the previous
record. Any modification to historical records breaks the chain and is detectable.
The chain is verified on audit log export.

### Failure Modes
- **Audit store write failure:** The audit record cannot be written. The operation
  is blocked until the audit store is restored. No configuration change proceeds
  without a successful audit record. ("If it's not audited, it didn't happen.")
- **Audit chain corruption:** Detected during export/verification. A full audit
  log integrity report is generated. The point of corruption is identified.

### Recovery Strategy
- Audit store write failure: This is a blocking failure. Fix the audit store.
  The configuration change queue is paused.
- Chain corruption: Investigate who or what modified the audit store. This is a
  security incident. Follow the security incident response procedure.

### Monitoring
- Audit record write latency (target: < 100ms per record).
- Audit chain integrity (verified daily).
- Audit store size (track growth, plan retention archival).
- Unusual access patterns (many reads of sensitive configuration, multiple failed
  change attempts).

---

## 3.12 Component 11 — Configuration Security Manager

### Purpose
The Configuration Security Manager governs the security of the configuration system
itself: protecting sensitive configuration values, enforcing access controls, detecting
configuration-based security violations, and managing secrets.

### Responsibilities
- Classify each configuration key by sensitivity (public, internal, confidential, secret).
- Enforce access controls: only authorized components and principals can read
  configuration at each sensitivity level.
- Manage the integration with the external secrets manager (environment variables,
  secrets vault).
- Detect injection attempts: configuration values that contain code-like patterns,
  unexpected external references, or unusual character sequences.
- Detect sensitive value exposure: configuration values appearing in logs, metrics,
  or dashboard output.
- Enforce encryption requirements for sensitive namespaces.
- Manage key rotation for encrypted configuration.

### Sensitivity Classification

**Public:** Configuration that can be safely logged and displayed. Example: system
version, environment name, log level.

**Internal:** Configuration for internal use. Not logged, not displayed externally,
but not encrypted at rest. Example: timeout values, retry counts, feature flags.

**Confidential:** Configuration that is sensitive but not a credential. Encrypted
at rest, not logged. Example: specific risk thresholds (not for public disclosure).

**Secret:** Configuration containing credentials or keys. Encrypted at rest and
in transit, never logged, accessed only by the component that needs it. Example:
broker tokens, Telegram bot token, encryption keys.

### Inputs
- Sensitivity classifications (from Configuration Registry metadata).
- Configuration access requests (from Configuration Resolver — intercepted for
  access control checking).
- Log output (for sensitive value exposure scanning).

### Outputs
- Access control decisions (allow/deny).
- Security violation alerts.
- Sensitive value exposure reports.
- Encryption status reports.

### Failure Modes
- **Access control failure:** Access is denied until the failure is resolved.
  An alert is raised. The requesting component receives an access denied error.
- **Secrets manager unavailable:** Secret-classified configuration is unavailable.
  Components depending on secrets receive errors. The fall-back behavior
  (paper mode, data feed fallback) activates.
- **Sensitive value exposure detected:** An immediate alert is sent. The exposure
  is logged as a security event. If the exposure is in a log file, the log file
  is quarantined for review.

### Monitoring
- Access control violation count (target: 0).
- Sensitive value exposure detections (target: 0).
- Secret rotation schedule compliance.
- Encryption status of all confidential and secret configuration.

---

## 3.13 Component 12 — Configuration Monitoring Manager

### Purpose
The Configuration Monitoring Manager observes the runtime behavior of the configuration
system and raises alerts when anomalies are detected.

### Responsibilities
- Monitor the health of all configuration components.
- Detect configuration drift (running configuration diverging from committed configuration).
- Detect unusual configuration change patterns.
- Monitor configuration load times and resolver performance.
- Alert on configuration-related failures or anomalies.
- Provide a configuration health summary for the system health dashboard.

### Inputs
- Health reports from all configuration components.
- Configuration change events.
- System telemetry (for detecting configuration-correlated behavior changes).

### Outputs
- Configuration health status (OPTIMAL / NOMINAL / DEGRADED / CRITICAL / FAILED).
- Configuration drift reports.
- Anomaly alerts.
- Health dashboard data.

### Drift Detection
Configuration drift occurs when the running configuration differs from the committed
configuration in the Repository. Drift can occur due to:
- Direct file modification on the server (bypassing the change process).
- Emergency override left active after its expiry.
- Manual editing of environment variables.

Drift is detected by comparing the hash of the loaded configuration against the
hash of the committed configuration. Drift detection runs every 5 minutes.

### Monitoring
- Drift detection frequency (every 5 minutes).
- Current drift status (none, minor, significant, critical).
- Last drift resolution timestamp.
- Configuration health score (OHS-compatible, 0.0 to 1.0).

---

## 3.14 Component 13 — Configuration Health Manager

### Purpose
The Configuration Health Manager implements the OHS (Operational Health Score)
for the configuration subsystem, integrating configuration health into the IIOS
system-wide health monitoring framework.

### Responsibilities
- Compute the configuration OHS score (0.0 to 1.0) on a defined interval.
- Publish the configuration OHS to the Control Tower.
- Enforce health-based behavior: in CRITICAL or FAILED state, restrict configuration
  changes and alert the Architecture Council.
- Integrate configuration health into the system-wide health summary.

### OHS Computation for Configuration

The Configuration OHS is computed from:

| Factor | Weight | Description |
|--------|--------|-------------|
| Registry health | 20% | All schemas registered, no gaps |
| Repository health | 20% | Repository accessible, backup current |
| Validator health | 15% | Validator operational, no failures |
| Loader health | 15% | Last load successful, no parse errors |
| Audit health | 15% | Audit store accessible, chain intact |
| Security health | 15% | No access violations, no drift |

**OHS Tier Thresholds (constitutional — same as system-wide):**
- OPTIMAL: 0.95 and above
- NOMINAL: 0.80 to 0.94
- DEGRADED: 0.60 to 0.79
- CRITICAL: 0.35 to 0.59
- FAILED: below 0.35

### Failure Modes
- Health Manager failure itself: The configuration OHS defaults to DEGRADED (0.70)
  and an alert is raised. The system continues operating with degraded confidence.

---

## 3.15 Component 14 — Configuration Analytics Manager

### Purpose
The Configuration Analytics Manager provides quantitative insight into configuration
patterns, usage, and impact — turning configuration history into actionable intelligence.

### Responsibilities
- Analyze configuration change frequency by namespace and category.
- Correlate configuration changes with system performance changes.
- Identify configuration patterns preceding incidents.
- Track configuration age (how long since each configuration was last reviewed).
- Generate configuration health reports for Architecture Council review.
- Provide trend analysis for configuration evolution.

### Inputs
- Configuration change history from Version Manager.
- System performance metrics from Control Tower.
- Incident records from Audit Manager.

### Outputs
- Configuration analytics reports (daily, weekly, monthly).
- Correlation reports (configuration change X correlated with outcome Y).
- Configuration age reports (configurations not reviewed in > N months).
- Trend charts for configuration evolution.

### Key Analytics

**Change frequency analysis:** Which configuration items change most often?
High-frequency changes may indicate that the configuration level is wrong
(volatile items should be at lower levels of the hierarchy) or that the
system needs better self-adaptation mechanisms.

**Impact analysis:** What system behavior changes followed each configuration
change? This analysis supports evidence-based configuration tuning and helps
identify which configuration items have the most operational impact.

**Age analysis:** Configuration that has not been reviewed in 12+ months is
flagged for review. Configuration that has never been changed may be obsolete
or may have an incorrect default that no one has noticed.

**Emergency override analysis:** Every emergency override is analyzed post-hoc
to understand why normal governance was insufficient and whether the configuration
should be permanently adjusted.

---

## 3.16 Component 15 — Configuration Backup Manager

### Purpose
The Configuration Backup Manager ensures that the complete configuration state —
including all versions and history — is backed up regularly and can be restored
in case of failure.

### Responsibilities
- Perform scheduled configuration backups (daily full backup, hourly incremental).
- Verify backup integrity on creation.
- Manage backup retention (retain daily backups for 30 days, weekly for 12 months,
  annual for 5 years).
- Provide backup listing and metadata.
- Test backup restore capability (monthly automated restore test to a staging environment).

### Inputs
- Configuration state from Repository.
- Configuration history from Version Manager.
- Backup schedule from backup configuration.

### Outputs
- Backup archives (encrypted, stored in designated backup storage).
- Backup completion reports.
- Backup integrity verification results.
- Restore test results.

### Failure Modes
- **Backup failure:** Alert raised. The next scheduled backup will retry.
  If two consecutive daily backups fail, a CRITICAL alert is raised.
- **Integrity verification failure:** The corrupted backup is marked invalid.
  An alert is raised. The backup is retried.
- **Restore test failure:** CRITICAL alert. Investigate the backup/restore procedure.
  A backup that cannot be restored is not a valid backup.

### Monitoring
- Last backup timestamp (alert if > 25 hours since last successful backup).
- Backup size trend (alert if backup size grows unusually fast).
- Integrity verification success rate (target: 100%).
- Restore test success rate (target: 100%).

---

## 3.17 Component 16 — Configuration Recovery Manager

### Purpose
The Configuration Recovery Manager coordinates the recovery of the configuration
system from failures, including individual component failures and full system
configuration corruption.

### Responsibilities
- Detect configuration system failures requiring recovery.
- Coordinate recovery sequencing (which components to restore in which order).
- Execute recovery from backup when needed.
- Validate the recovered configuration state.
- Resume normal operation after recovery.
- Document the recovery in the audit log.

### Recovery Scenarios

**Scenario 1 — Loader failure at startup:**
Cause: Configuration file parse error or missing required file.
Recovery: Fix the file, restart the Loader. No data loss.

**Scenario 2 — Repository corruption:**
Cause: Storage failure, file system corruption.
Recovery: Restore from the most recent Backup Manager backup. Apply recent
changes from Version Manager history. Validate the restored state.

**Scenario 3 — Audit store corruption:**
Cause: Database corruption, storage failure.
Recovery: Restore from backup. Reconstruct recent records from Manager's change log.
Treat as a security incident and investigate the cause.

**Scenario 4 — Full configuration system failure:**
Cause: Multiple component failures simultaneously.
Recovery: Start with Repository restore from backup. Rebuild Loader from Repository.
Rebuild Registry from schema files. Rebuild Cache from Loader. Validate all components
individually before enabling the full system.

### Inputs
- Failure reports from all configuration components.
- Backup archives from Backup Manager.
- Change logs from Manager and Version Manager.

### Outputs
- Recovery status reports.
- Post-recovery validation results.
- Recovery incident documentation.

### Monitoring
- Recovery event count (target: 0 per month; any recovery triggers a post-mortem).
- Recovery time (from failure detection to full restoration).
- Recovery success rate (target: 100%).

---

*End of Part III*

---

# PART IV — CONFIGURATION HIERARCHY

## 4.1 Hierarchy Overview

The IIOS configuration hierarchy defines the precedence order for configuration
values. The hierarchy has 12 levels. Higher level numbers provide higher override
precedence. The system reads configuration starting at the lowest level (global
defaults) and applies each subsequent level as an override layer.

`
CONFIGURATION HIERARCHY (precedence: higher number = higher override)

Level 12: Emergency Override    [Human safety valve — highest precedence]
     |
Level 11: Runtime               [Dynamically set during operation]
     |
Level 10: Session               [Per-trading-session overrides]
     |
Level 9:  Portfolio             [Portfolio-level settings]
     |
Level 8:  Model                 [Per-model hyperparameters]
     |
Level 7:  Strategy              [Per-strategy parameters]
     |
Level 6:  Workflow              [Per-workflow settings]
     |
Level 5:  Engine                [Per-engine defaults]
     |
Level 4:  Infrastructure        [Infrastructure-level settings]
     |
Level 3:  Platform              [Platform settings (VPS, cloud)]
     |
Level 2:  Environment           [Env-specific overrides (dev/paper/prod)]
     |
Level 1:  Global Defaults       [System-wide base values — lowest precedence]
`

---

## 4.2 Level 1 — Global Defaults

**Source:** config/environments/base.yaml
**Override by:** All higher levels
**Owner:** Architecture Council

Global defaults define the baseline behavior for every configuration item in IIOS.
Every required configuration key must have a default value at this level. If a key
has no value at any higher level, the global default is used.

**Inheritance rule:** Global defaults apply to everything unless overridden at a
more specific level.

**Design principle:** Global defaults should be safe conservative values — the
system should operate safely and correctly with only the global defaults applied,
even if suboptimally.

---

## 4.3 Level 2 — Environment

**Source:** config/environments/[environment_name].yaml
**Override by:** Levels 3–12
**Owner:** Architecture Council (for list of valid environments), Operations (for values)

Environment configuration overrides global defaults for the specific operational
context. The key characteristic of environment configuration is that it represents
the decisions that differ between the development laptop, the paper trading server,
and the live production server.

**Inheritance rule:** Environment-level values override global defaults for the
entire system within that environment.

**IIOS environments:**
`
development.yaml  — Local development: verbose logging, mocks, relaxed timeouts
paper.yaml        — Paper trading: production data, paper broker
production.yaml   — Live trading: live data, live broker, strict risk limits
testing.yaml      — CI testing: mocks, accelerated intervals
ci.yaml           — CI pipeline subset of testing
`

---

## 4.4 Level 3 — Platform

**Source:** config/platforms/[platform_name].yaml
**Override by:** Levels 4–12
**Owner:** Operations Team

Platform configuration captures differences between deployment platforms (VPS-hosted,
cloud-hosted, locally hosted). On IIOS's current architecture (single VPS), this level
is minimal. As the system grows to support cloud deployments, this level will become
more significant.

**Current platform definitions:**
`
vps.yaml    — VPS (178.18.252.24): resource limits, network config
local.yaml  — Developer local machine
cloud.yaml  — Future cloud deployment
`

---

## 4.5 Level 4 — Infrastructure

**Source:** config/infrastructure/[component].yaml
**Override by:** Levels 5–12
**Owner:** Operations Team

Infrastructure configuration captures settings specific to the infrastructure
components: Docker container settings, OS-level configuration, network configuration.

---

## 4.6 Level 5 — Engine

**Source:** config/engines/[engine_name]_config.py (defaults), overridden by
environment-specific engine configs where needed.
**Override by:** Levels 6–12
**Owner:** Engine Owner

Engine configuration is the most granular "first-class" configuration level.
Each of the 18 engines defines its own configuration namespace. Engine defaults
capture the baseline behavior for the engine independent of deployment environment.

**Inheritance at engine level:**
An engine configuration starts with all global defaults, applies the current
environment overrides, applies the current platform overrides, and then applies
its own engine-specific values.

---

## 4.7 Level 6 — Workflow

**Source:** Defined in engine configuration, no separate files.
**Override by:** Levels 7–12
**Owner:** Engine Owner

Workflow configuration captures the execution parameters for specific named workflows
within an engine. Most workflow configuration is part of the engine configuration file
but namespaced to the specific workflow.

---

## 4.8 Level 7 — Strategy

**Source:** config/strategies/[strategy_id].yaml or JSON in strategy registry.
**Override by:** Levels 8–12
**Owner:** Strategy Lab Engine Owner

Strategy configuration provides per-strategy parameter overrides. Each strategy
can have different entry/exit thresholds, sizing parameters, and filter settings.

---

## 4.9 Level 8 — Model

**Source:** config/models/[model_id].yaml or model metadata store.
**Override by:** Levels 9–12
**Owner:** Engine Owner of owning engine

Model hyperparameters are managed at this level. Model configuration is typically
set after empirical optimization and does not change frequently.

---

## 4.10 Level 9 — Portfolio

**Source:** config/portfolio/[portfolio_id].yaml
**Override by:** Levels 10–12
**Owner:** Architecture Council for limits; Operations for preferences

Portfolio-level configuration captures the overall portfolio management settings
that may vary between different portfolio configurations (single-account, multi-account).

---

## 4.11 Level 10 — Session

**Source:** Generated at session start; not stored as files.
**Override by:** Levels 11–12
**Owner:** Orchestrator Engine

Session configuration captures per-trading-session overrides. These are generated
programmatically based on market conditions at session start. Examples:
- Reduced position sizing in high-volatility sessions.
- Tighter stop losses on high-impact event days.
- Reduced maximum positions during expiry week.

Session configuration is ephemeral — it exists for one trading session and is
recalculated at the start of each session.

---

## 4.12 Level 11 — Runtime

**Source:** Generated dynamically during operation.
**Override by:** Level 12 only
**Owner:** Engine owning the runtime configuration

Runtime configuration represents values that are set dynamically during operation
in response to observed conditions. This is the most restricted level of non-emergency
configuration. Runtime configuration changes:
- Must be explicitly designed and documented (no ad-hoc runtime modifications).
- Must have expiry (they cannot persist indefinitely).
- Must be logged with the condition that triggered them.
- Cannot override constitutional values.

Examples:
- Market breadth deteriorates: runtime configuration reduces opportunity engine
  minimum signal threshold temporarily.
- Data feed latency increases: runtime configuration increases timeout values.

---

## 4.13 Level 12 — Emergency Override

**Source:** Applied directly by authorized human via emergency CLI or console.
**Override by:** Nothing — this is the highest precedence level.
**Owner:** Architecture Council member (only Tier 1 owners may invoke emergency overrides)

Emergency overrides are the human safety valve. They allow authorized individuals
to immediately change configuration without going through the normal governance
process. Emergency overrides are used when:
- A live trading emergency requires immediate configuration change.
- The normal governance pipeline cannot be completed in time.
- The system is behaving dangerously and needs immediate correction.

**Emergency override constraints (constitutional, cannot themselves be overridden):**
- Maximum lifetime: 24 hours. An emergency override that has not been replaced
  by a proper configuration change within 24 hours expires automatically.
- Cannot relax risk limits below constitutional minimums.
- Require immediate documentation in the audit log.
- Require post-emergency review within 48 hours.

---

## 4.14 Hierarchy Inheritance Diagram

`
Global Defaults (Level 1)
    |
    |--> ALL keys get their base value here
    |
    v
Environment (Level 2): production
    |
    |--> risk.kill_switch.vix_threshold: unchanged (45)
    |--> system.mode: overridden to "production"
    |--> broker.mode: overridden to "live"
    |--> logging.level: overridden to "INFO"
    |
    v
Platform (Level 3): vps
    |
    |--> infrastructure.server.max_connections: overridden to 100
    |--> infrastructure.network.timeout_ms: overridden to 5000
    |
    v
Engine (Level 5): risk_guardian
    |
    |--> engines.risk_guardian.kill_switch.check_interval_s: overridden to 60
    |--> engines.risk_guardian.monitoring.alert_channel: overridden to "telegram"
    |
    v
Session (Level 10): 2026-07-04 (expiry day)
    |
    |--> portfolio.limits.max_open_positions: overridden to 3 (reduced for expiry)
    |
    v
EFFECTIVE CONFIGURATION:
    risk.kill_switch.vix_threshold = 45          [from Level 1]
    system.mode = "production"                   [from Level 2]
    infrastructure.server.max_connections = 100  [from Level 3]
    engines.risk_guardian.check_interval_s = 60  [from Level 5]
    portfolio.limits.max_open_positions = 3      [from Level 10]
`

---

*End of Part IV*

---# PART V — CONFIGURATION LIFECYCLE

## 5.1 Lifecycle Overview

The Configuration Lifecycle defines the complete journey of a configuration item
from its initial conception through its eventual archival. Understanding the lifecycle
enables correct handling at each stage and provides a governance framework that
ensures every configuration item is properly managed throughout its existence.

`
CONFIGURATION LIFECYCLE DIAGRAM

                    +------------------+
                    |  1. CONCEPTION   |
                    | (Identify need)  |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  2. DRAFTING     |
                    | (Propose value)  |
                    +--------+---------+
                             |
                             v
                    +------------------+       +------------------+
                    |  3. VALIDATION   | ----> |  REJECTED        |
                    | (Schema check)   |       | (Fix and retry)  |
                    +--------+---------+       +------------------+
                             |
                             v
                    +------------------+       +------------------+
                    |  4. REVIEW       | ----> |  NEEDS REVISION  |
                    | (Peer review)    |       | (Back to DRAFT)  |
                    +--------+---------+       +------------------+
                             |
                             v
                    +------------------+       +------------------+
                    |  5. APPROVAL     | ----> |  DENIED          |
                    | (Governance)     |       | (Close request)  |
                    +--------+---------+       +------------------+
                             |
                             v
                    +------------------+
                    |  6. PUBLICATION  |
                    | (Repository)     |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  7. LOADING      |
                    | (Into system)    |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  8. ACTIVATION   |
                    | (Applied live)   |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  9. MONITORING   |<------+
                    | (Track effect)   |       |
                    +--------+---------+       |
                             |                 |
                   OK        |    ANOMALY      |
                   |         +--------+        |
                   |                  v        |
                   |         +------------------+
                   |         | 10. MODIFICATION |
                   |         | (Back to DRAFT)  |
                   |         +------------------+
                   |
                   v
         +------------------+
         | 11. VERSION UPGRADE |
         | (Major schema change)|
         +--------+------------+
                  |
                  v
         +------------------+
         | 12. ROLLBACK     |<--- triggered by emergency or failure
         | (Restore prev)   |
         +--------+---------+
                  |
                  v
         +------------------+
         | 13. DEPRECATION  |
         | (Mark as legacy) |
         +--------+---------+
                  |
                  v
         +------------------+
         | 14. RETIREMENT   |
         | (Remove active)  |
         +--------+---------+
                  |
                  v
         +------------------+
         | 15. ARCHIVE      |
         | (Preserve record)|
         +------------------+
`

---

## 5.2 Stage 1 — Conception

**Description:** The need for a new or changed configuration item is identified.

**Trigger conditions:**
- A new engine capability is being added that requires a tunable parameter.
- Operational experience reveals that a hardcoded value should be configurable.
- A regulatory or compliance requirement introduces a new constraint.
- A performance issue is traced to a configuration value that is suboptimal.
- A new deployment environment requires different behavior.

**Key activities:**
- Document the purpose of the configuration item: what behavior it governs, why
  it needs to be configurable rather than hardcoded, and what range of values is
  expected.
- Identify the correct category (from the taxonomy in Part II).
- Identify the correct level in the hierarchy (Part IV) where this item belongs.
- Identify the owner (from ownership tier rules in Part I).

**Outputs:**
- Configuration proposal document: name, category, hierarchy level, owner, purpose,
  proposed default value, proposed valid range.

---

## 5.3 Stage 2 — Drafting

**Description:** The proposed configuration item is formally specified with all
required metadata.

**Required metadata for a complete configuration draft:**
- Full key name (following naming conventions)
- Data type (string, integer, float, boolean, duration, percentage)
- Default value
- Valid range or enumeration of valid values
- Description (what it governs)
- Owner (which tier and which individual or role)
- Governance tier (which approval level is required)
- Dependencies (other configuration items that interact with this one)
- Consumption point (which engine/component reads this value)
- Production risk level (does changing this value affect live trading?)
- Rollback impact (can this value be rolled back without system restart?)

**Draft format:** A structured YAML document following the schema in
config/templates/config_draft_template.yaml.

**Drafting rules:**
1. A draft with incomplete metadata is rejected at validation (Stage 3).
2. The draft author must have at least Engine Owner authority.
3. Drafts for constitutional configuration (kill switch thresholds, OHS tiers)
   require Architecture Council authorship.

---

## 5.4 Stage 3 — Validation

**Description:** The draft configuration item is validated against all schema rules,
consistency rules, and completeness requirements.

**Validation checks performed:**
- Schema validation: correct data type, value within valid range.
- Format validation: naming convention compliance.
- Completeness validation: all required metadata fields present.
- Consistency validation: no conflicts with existing configuration.
- Inheritance validation: the item's position in the hierarchy is correct.
- Security validation: appropriate sensitivity classification.
- Governance validation: proposed value does not violate constitutional limits.
- Cross-reference validation: all referenced entities exist.

**Validation outcomes:**
- PASS: Draft proceeds to Review.
- FAIL with errors: Draft is returned to drafting with specific error list.
- PASS with warnings: Draft proceeds to Review with warning list attached.

**Automated validation:** The Configuration Validator (Part III, Component 4) runs
all validation checks. The CI pipeline runs validation on every pull request that
modifies configuration files.

---

## 5.5 Stage 4 — Review

**Description:** The validated draft is reviewed by qualified reviewers before
approval.

**Review requirements by governance tier:**

| Tier | Minimum Reviewers | Review Period |
|------|------------------|---------------|
| Tier 1 (Arch Council) | 2 Architecture Council members | 48 hours minimum |
| Tier 2 (Engine Owner) | 1 peer engineer + engine owner | 24 hours minimum |
| Tier 3 (Operations) | 1 operations team member | 8 hours minimum |
| Tier 4 (Feature Owner) | Self-review only | None |

**Review focus areas:**
- Correctness: Is the proposed value appropriate for the use case?
- Safety: Could the change cause unintended behavior in edge cases?
- Completeness: Is the documentation adequate for future maintainers?
- Security: Does the change introduce any security concerns?
- Consistency: Does the change fit well with adjacent configuration?

**Review outcomes:**
- APPROVED FOR APPROVAL: Proceed to Approval stage.
- NEEDS REVISION: Specific changes requested. Return to Drafting.
- REJECTED: Fundamental issue with the proposal. Closed with documented reason.

---

## 5.6 Stage 5 — Approval

**Description:** The reviewed configuration change is formally approved by the
governance authority for its tier.

**Approval authority matrix:**

| Configuration Category | Approving Authority | Approval Mechanism |
|----------------------|--------------------|--------------------|
| system.*, security.*, governance.* | Architecture Council vote | Quorum (>50%) |
| risk.* constitutional limits | Architecture Council vote | Unanimous |
| engines.[name].* | Engine Owner | Single approval |
| deployment.*, infrastructure.* | Operations Lead | Single approval |
| features.* | Feature Owner | Self-approval |
| emergency.* | Any Arch Council member | Single approval (emergency only) |

**Approval record:**
Every approval creates a formal approval record containing: approver identity,
timestamp, configuration version approved, approval decision (approved/denied),
rationale.

**Denial handling:**
A denied configuration change is closed. The proposer is notified with the denial
rationale. A denied change may be re-proposed after addressing the denial reasons.

---

## 5.7 Stage 6 — Publication

**Description:** The approved configuration change is written to the Configuration
Repository, creating a new version.

**Publication activities:**
- Configuration Manager receives the approval record.
- Configuration Manager requests a new version number from Version Manager.
- Configuration Manager writes the new value to the Repository.
- Configuration Manager records the change in the Audit Manager.
- Configuration Manager notifies the Version Manager of the new version.
- Configuration Manager tags the version with the approval record reference.

**Publication atomicity:** The publication operation is atomic. Either the new
value is fully written and the version is recorded, or neither happens. There is
no partial publication state.

**Publication record:** Every publication creates a permanent record linking the
configuration value change to its approval, its author, its version, and its timestamp.

---

## 5.8 Stage 7 — Loading

**Description:** The published configuration is loaded from the Repository into
the running system.

**Loading triggers:**
- **Startup load:** All configuration is loaded from the Repository during system
  initialization. This is the most common loading event.
- **Dynamic reload:** Some configuration categories support live reload without
  system restart. The Configuration Loader performs a targeted reload for the
  affected namespace.
- **Scheduled reload:** Some configuration categories are reloaded on a schedule
  (e.g., feature flags are reloaded every 10 minutes).

**Loading sequence (startup):**
1. Load global defaults (ase.yaml).
2. Load environment file ([env].yaml).
3. Load platform file ([platform].yaml).
4. Load infrastructure files.
5. Load all engine configuration files.
6. Apply environment variable overrides.
7. Load emergency overrides if present.
8. Validate the assembled configuration.
9. Populate the Configuration Cache.
10. Make configuration available to engines via the Resolver.

**Loading failure:** If any required configuration cannot be loaded or fails
validation, the system startup is blocked. No engine initializes until the
configuration system is fully operational.

---

## 5.9 Stage 8 — Activation

**Description:** The loaded configuration is applied to the running system, taking
effect on system behavior.

**Activation types:**

**Immediate activation:** The new configuration value takes effect immediately
upon loading. The running system adopts the new value on the next access.
Applicable to: timeout values, threshold values, feature flags.

**Deferred activation:** The new configuration value takes effect at the next
natural boundary (e.g., next trading session, next cycle, next startup).
Applicable to: strategy parameters (applied at next strategy run), model
hyperparameters (applied at next model inference), session configuration
(applied at next session start).

**Restart-required activation:** The new configuration value requires a system
restart to take effect. The system is flagged for restart.
Applicable to: infrastructure changes, security configuration, structural changes.

**Activation tracking:** When a new configuration value becomes active, the
activation event is logged: timestamp, key, old value, new value, activation type.

---

## 5.10 Stage 9 — Monitoring

**Description:** The active configuration is monitored for effectiveness and anomalies.

**Monitoring dimensions:**

**Correctness monitoring:** Does the system behave as intended with the new
configuration? Are there unexpected side effects? The Configuration Monitoring
Manager tracks correlated behavior changes after configuration activations.

**Drift monitoring:** Has the running configuration diverged from the published
configuration? Drift detection runs every 5 minutes comparing loaded values
against the Repository.

**Impact monitoring:** What measurable impact has the configuration change had?
For risk configuration changes, this means monitoring risk metrics. For
performance configuration changes, this means monitoring latency and throughput.

**Health monitoring:** Is the configuration system itself healthy? Are all components
operating normally? The Configuration Health Manager tracks OHS.

---

## 5.11 Stage 10 — Modification

**Description:** An existing configuration item is changed. This returns to the
Drafting stage with the existing configuration item as the base.

**Modification types:**

**Value modification:** The key and metadata are unchanged; only the value changes.
This is the most common modification. It follows the full lifecycle from Drafting
to Activation.

**Metadata modification:** The description, ownership, or sensitivity classification
is changed. Value unchanged. Requires review and approval at the original tier.

**Schema modification:** The data type, naming, or structure of the configuration
item changes. This is the most impactful modification and requires Architecture
Council review regardless of the item's normal governance tier.

---

## 5.12 Stage 11 — Version Upgrade

**Description:** A significant schema change requires migrating from one configuration
schema version to another.

**Version upgrade triggers:**
- New required configuration keys are added.
- Existing configuration keys are renamed.
- Configuration value types change.
- Configuration items are reorganized across namespaces.

**Version upgrade procedure:**
1. The new schema is published alongside the old schema.
2. A migration tool converts the old configuration to the new schema.
3. The converted configuration is validated against the new schema.
4. The new schema is activated; the old schema is deprecated.
5. A migration guide is published documenting the changes.
6. The old schema is retired after a defined migration period (minimum 30 days).

**Version upgrade constraints:**
- Both the old and new schemas must be valid simultaneously during the migration period.
- No engine is required to use the new schema until the migration period ends.
- The migration tool must be idempotent.

---

## 5.13 Stage 12 — Rollback

**Description:** A configuration change is reversed, restoring the previous
configuration state.

**Rollback triggers:**
- A configuration change produces unexpected negative effects.
- A configuration change is discovered to be incorrect after activation.
- An emergency situation requires immediate return to previous configuration.

**Rollback types:**

**Single-key rollback:** Restore one configuration key to its previous value.
The most common rollback type.

**Namespace rollback:** Restore all configuration in a namespace to a previous
version. Used when multiple related keys need to be rolled back together.

**Full configuration rollback:** Restore the entire configuration set to a
previous version. Used in catastrophic configuration error scenarios.

**Rollback constraints:**
- Rollback creates a new configuration version (it does not delete history).
- Every rollback is logged in the Audit Manager.
- Rollbacks that restore risk limits to more permissive values require Architecture
  Council approval (same as the original change that tightened them).
- Constitutional limits cannot be rolled back to more permissive values without
  Architecture Council approval.

---

## 5.14 Stage 13 — Deprecation

**Description:** A configuration item is marked as deprecated, signaling that it
will be removed in a future version.

**Deprecation requirements:**
- A deprecation notice is attached to the configuration item in the Registry.
- A successor is identified (the new configuration item or approach that replaces it).
- A deprecation timeline is set (minimum 60 days to retirement).
- All owners of components that consume the deprecated item are notified.
- Documentation is updated to reference the successor.

**Deprecation effects:**
- The deprecated configuration item continues to function normally.
- A WARNING is logged every time the deprecated item is accessed.
- The Configuration Catalog marks the item as deprecated in its documentation.

---

## 5.15 Stage 14 — Retirement

**Description:** A deprecated configuration item is removed from the active
configuration set.

**Retirement requirements:**
- The deprecation period (minimum 60 days) has elapsed.
- All consuming components have migrated to the successor.
- The CI pipeline confirms no consuming code references the retired key.
- Architecture Council approval is obtained (regardless of the item's original tier).

**Retirement effects:**
- The configuration key is removed from the active Registry.
- The configuration key is removed from all configuration files.
- Accessing the retired key raises a ConfigurationRetiredKeyError.
- The key's history is moved to the archive but is not deleted.

---

## 5.16 Stage 15 — Archive

**Description:** The retired configuration item and its complete history are preserved
in the archive for future reference.

**Archive contents for each retired item:**
- Complete change history (all versions, values, approvals).
- Retirement record (who approved retirement, when, why).
- Reference to the successor configuration item.
- Any relevant context about the item's operational history.

**Archive access:** Archived configuration history is readable but not modifiable.
It is retained indefinitely (no expiry).

---

*End of Part V*

---

# PART VI — CONFIGURATION SERVICES

## 6.1 Service Architecture Overview

Configuration Services provide the operational interface between the Configuration
Architecture (components) and the engines that consume configuration. Where the
Architecture components define the internal workings of the configuration system,
the Services define how external consumers interact with configuration.

---

## 6.2 Service 1 — Validation Service

### Service Purpose
Provide configuration validation as a callable service available to CI pipelines,
pre-deployment scripts, and runtime validation requests.

### Service Interface
- alidate_file(path) -> ValidationResult — Validate a configuration file.
- alidate_key(key, value) -> ValidationResult — Validate a single key-value pair.
- alidate_namespace(namespace, values) -> ValidationResult — Validate all values
  in a namespace.
- alidate_full_config(config_set) -> ValidationResult — Validate a complete
  configuration set.
- get_validation_rules(key) -> ValidationRules — Return the validation rules for
  a key.

### Consumers
- CI/CD pipeline (pre-deployment validation)
- Configuration Manager (before accepting changes)
- Configuration Loader (before activating loaded configuration)
- Operators (on-demand validation via CLI)

### Service Level
- Response time target: < 1 second per file, < 100ms per key.
- Availability target: 99.9% during market hours.
- Error rate target: 0% false negatives (every genuine violation is caught).

---

## 6.3 Service 2 — Loading Service

### Service Purpose
Provide configuration loading as a callable service for engine initialization and
dynamic configuration refresh.

### Service Interface
- load_all() -> ConfigurationState — Load all configuration from all sources.
- load_namespace(namespace) -> NamespaceConfig — Load configuration for a specific
  namespace.
- eload_namespace(namespace) -> NamespaceConfig — Reload a namespace from storage.
- get_source_report() -> LoadReport — Report which sources contributed to the
  current configuration.

### Consumers
- Orchestrator (at system startup)
- Individual engines (at engine initialization)
- Configuration Manager (after a change is applied)

### Service Level
- Startup load time: < 2,000ms for full configuration load.
- Namespace reload time: < 500ms per namespace.

---

## 6.4 Service 3 — Caching Service

### Service Purpose
Provide a managed configuration cache that improves read performance and supports
cache invalidation on change.

### Service Interface
- get(key) -> Optional[ConfigValue] — Get a value from cache (None on miss).
- set(key, value, ttl) — Store a value in cache with TTL.
- invalidate(key) — Invalidate a single key.
- invalidate_namespace(namespace) — Invalidate all keys in a namespace.
- clear() — Clear entire cache (used on emergency reset).
- get_stats() -> CacheStats — Get cache hit rate, size, eviction statistics.

### Cache TTL Policy by Namespace

| Namespace | TTL | Invalidation Trigger |
|-----------|-----|---------------------|
| system.* | Indefinite | System restart only |
| isk.* constitutional | Indefinite | Restart or Architecture Council change |
| engines.[name].* | 60 seconds | On configuration change notification |
| eatures.* | 10 seconds | On feature flag change |
| emergency.* | No cache | Always read direct |
| sessions.* | Session duration | On session end |
| monitoring.* | 30 seconds | On monitoring config change |

---

## 6.5 Service 4 — Resolution Service

### Service Purpose
Provide the primary runtime interface for engines to read configuration values.
The Resolution Service is the most frequently called configuration service.

### Service Interface
- get_str(key, default=None) -> str — Get a string configuration value.
- get_int(key, default=None) -> int — Get an integer configuration value.
- get_float(key, default=None) -> float — Get a float configuration value.
- get_bool(key, default=None) -> bool — Get a boolean configuration value.
- get_duration_ms(key, default=None) -> int — Get a duration as milliseconds.
- get_pct(key, default=None) -> float — Get a percentage as a fraction (0.0–1.0).
- get_list(key, default=None) -> list — Get a list configuration value.
- get_namespace(namespace) -> dict — Get all key-value pairs in a namespace.
- 	race(key) -> ResolutionTrace — Get the resolution trace showing which level
  in the hierarchy provided the effective value.

### Performance Requirements
- Per-key resolution (cache hit): < 1ms
- Per-key resolution (cache miss, from Loader state): < 10ms
- Namespace resolution (all keys): < 50ms

### Error Handling Contract
- Key not found AND no default provided: Raise ConfigurationKeyNotFoundError.
- Key not found WITH default provided: Return default, log DEBUG.
- Type coercion failure: Raise ConfigurationTypeError.
- Security access denied: Raise ConfigurationAccessDeniedError.

---

## 6.6 Service 5 — Monitoring Service

### Service Purpose
Provide configuration health monitoring and alerting as a service integrated with
the IIOS Control Tower.

### Service Interface
- get_health() -> ConfigurationOHS — Current configuration OHS score and tier.
- get_drift_status() -> DriftStatus — Current drift detection result.
- get_component_health() -> dict — Per-component health status.
- subscribe_alerts(callback) — Subscribe to configuration health alerts.
- get_metrics() -> ConfigurationMetrics — Full metrics snapshot.

### Alert Types
- CONFIG_DRIFT_DETECTED — Running configuration differs from committed.
- CONFIG_COMPONENT_FAILED — A configuration component is unhealthy.
- CONFIG_SCHEMA_ERROR — Schema validation is failing.
- CONFIG_BACKUP_OVERDUE — Backup has not completed within SLA.
- CONFIG_EMERGENCY_ACTIVE — An emergency override is currently active.
- CONFIG_AUDIT_CHAIN_BROKEN — Audit log chain integrity failure detected.

---

## 6.7 Service 6 — Audit Service

### Service Purpose
Provide access to the configuration audit trail for compliance, security, and
forensic analysis.

### Service Interface
- query_changes(namespace=None, actor=None, from_ts=None, to_ts=None) -> [AuditRecord]
  — Query the audit log with filters.
- get_change_history(key) -> [AuditRecord] — Get the complete change history
  for a specific key.
- get_emergency_overrides(from_ts, to_ts) -> [AuditRecord] — Get all emergency
  override events in a time range.
- erify_chain() -> ChainVerificationResult — Verify the tamper-evident chain
  of audit records.
- export_audit(from_ts, to_ts, format) -> AuditExport — Export audit records
  in the requested format.

### Access Control
- Full audit read: Architecture Council members only.
- Own-namespace audit read: Engine owners for their namespaces.
- Emergency override audit: Architecture Council only.
- Compliance export: Designated compliance officer.

---

## 6.8 Service 7 — Backup Service

### Service Purpose
Provide backup and restore capabilities for configuration, integrated with the
Configuration Backup Manager.

### Service Interface
- ackup_now(scope='full') -> BackupResult — Trigger an immediate backup.
- list_backups() -> [BackupMetadata] — List all available backups.
- erify_backup(backup_id) -> VerificationResult — Verify a specific backup's
  integrity.
- estore(backup_id, scope='full') -> RestoreResult — Restore from a backup.
- get_backup_status() -> BackupStatus — Get current backup health status.

---

## 6.9 Service 8 — Recovery Service

### Service Purpose
Provide coordinated recovery from configuration system failures.

### Service Interface
- initiate_recovery(scenario) -> RecoveryPlan — Generate a recovery plan for
  a given failure scenario.
- execute_recovery(plan) -> RecoveryResult — Execute a recovery plan.
- get_recovery_status() -> RecoveryStatus — Get current recovery status.
- alidate_post_recovery() -> ValidationResult — Validate the system state after
  recovery.

### Recovery Scenarios Handled
- LOADER_FAILURE — Configuration Loader cannot load configuration.
- REPOSITORY_CORRUPTION — Configuration Repository is corrupt.
- AUDIT_CORRUPTION — Audit log is corrupt.
- CACHE_CORRUPTION — Configuration Cache has invalid data.
- FULL_CONFIG_FAILURE — Complete configuration system failure.

---

## 6.10 Service 9 — Security Service

### Service Purpose
Provide configuration security enforcement and secret management.

### Service Interface
- classify(key) -> Sensitivity — Get the sensitivity classification for a key.
- check_access(principal, key, operation) -> AccessDecision — Check access rights.
- scan_for_secrets(config_data) -> [SecretFinding] — Scan configuration for
  inadvertently committed secrets.
- otate_secret(key) -> RotationResult — Trigger secret rotation for a secret
  configuration value.
- get_encryption_status() -> EncryptionStatus — Check encryption status of
  all sensitive configuration.

---

## 6.11 Service 10 — Version Service

### Service Purpose
Provide version management operations for configuration.

### Service Interface
- get_current_version() -> ConfigVersion — Get the current configuration version.
- list_versions(namespace=None) -> [ConfigVersion] — List all configuration
  versions.
- get_version_diff(v1, v2) -> VersionDiff — Compute the diff between two
  configuration versions.
- ollback_to(version_id) -> RollbackResult — Roll back to a specific version.
- 	ag_version(version_id, tag) -> TagResult — Apply a descriptive tag to a version.
- get_version_at_time(timestamp) -> ConfigVersion — Get the configuration version
  that was active at a specific timestamp.

### Critical capability: get_version_at_time
This capability enables post-incident forensic analysis: "What configuration was
active when the incident occurred?" By reconstructing the exact configuration state
at any point in time, forensic investigators can determine if configuration contributed
to an incident.

---

## 6.12 Service 11 — Health Service

### Service Purpose
Provide the OHS health interface for configuration as part of the system-wide health
framework.

### Service Interface
- get_ohs() -> float — Current OHS score (0.0 to 1.0).
- get_ohs_tier() -> OHSTier — Current OHS tier (OPTIMAL/NOMINAL/DEGRADED/CRITICAL/FAILED).
- get_health_breakdown() -> HealthBreakdown — Per-component health scores.
- get_health_history(hours=24) -> [HealthRecord] — Historical OHS data.
- 	rigger_health_check() -> HealthResult — Force an immediate health check.

---

## 6.13 Service 12 — Analytics Service

### Service Purpose
Provide configuration analytics and trend reporting.

### Service Interface
- get_change_frequency(namespace, days=30) -> FrequencyReport — Change frequency
  for a namespace over N days.
- get_impact_analysis(change_id) -> ImpactReport — Correlate a configuration
  change with system behavior changes.
- get_age_report() -> AgeReport — Report on configuration items not recently
  reviewed.
- get_emergency_override_report(days=90) -> EmergencyReport — Summary of
  emergency overrides.
- get_health_trend(days=30) -> HealthTrend — Configuration health trend.

---

*End of Part VI*

---

# PART VII — CONFIGURATION QUALITY FRAMEWORK

## 7.1 Quality Framework Overview

The Configuration Quality Framework defines the dimensions of configuration quality
in IIOS and the standards, measurements, and remediation procedures for each dimension.
High-quality configuration is the foundation of reliable, predictable system behavior.

A quality configuration is one that is correct in all environments, consistent
across all components, complete for all requirements, traceable to its source,
maintainable over time, version-controlled, secure, reliable, available when needed,
scalable as the system grows, auditable for compliance, recoverable after failures,
and operationally stable throughout its lifecycle.

---

## 7.2 Dimension 1 — Correctness

**Definition:** Every configuration value is correct for its intended purpose.
A correct value produces the intended behavior when the system applies it.

**Correctness standards:**
- Every configuration value must be within its valid range.
- Configuration for risk limits must be at or tighter than baseline constitutional values.
- Strategy parameters must be consistent with backtesting evidence.
- Timeout values must be achievable under normal network conditions.
- Threshold values must have empirical or theoretical basis.

**Correctness measurement:**
- Schema validation pass rate (target: 100%).
- Production incidents attributable to incorrect configuration (target: 0).
- Number of emergency rollbacks due to incorrect values (target: 0).

**Correctness remediation:**
- Pre-deployment validation enforces type and range correctness.
- Governance review enforces empirical and operational correctness.
- Monitoring detects correctness failures at runtime.
- Rollback restores correct state when incorrect configuration is discovered post-activation.

---

## 7.3 Dimension 2 — Consistency

**Definition:** All configuration values are internally consistent. No configuration
value conflicts with any other configuration value.

**Consistency standards:**
- Related configuration values must be logically compatible.
  (min_position_size < max_position_size)
- Configuration at lower hierarchy levels must be compatible with the constraints
  at higher levels.
  (engine timeout < system-level circuit breaker timeout)
- Environment-specific overrides must not introduce inconsistencies not present
  in the base configuration.

**Consistency measurement:**
- Consistency validation failures in CI (target: 0 failures per week).
- Configuration inconsistencies detected by Configuration Monitor (target: 0).

**Consistency remediation:**
- Consistency rules are codified in the Configuration Validator.
- Consistency rules are documented in the configuration schema.
- Consistency failures are caught at the Validation stage of the lifecycle.

---

## 7.4 Dimension 3 — Completeness

**Definition:** All required configuration is present and all optional configuration
that has been explicitly designed is populated.

**Completeness standards:**
- Every required key in the Registry has a value at some level of the hierarchy.
- No engine encounters a missing required configuration value at runtime.
- All mandatory documentation fields are populated for every configuration item.

**Completeness measurement:**
- Missing required key count at startup (target: 0).
- Documentation completeness score (target: 100% of keys have description and owner).
- Orphaned keys count (keys present in files but not registered — target: 0).

---

## 7.5 Dimension 4 — Traceability

**Definition:** Every configuration value can be traced to its source: where it came
from, who set it, when, why, and with whose approval.

**Traceability standards:**
- Every configuration change has an author, timestamp, and approval record.
- The Resolution Service can provide a trace for every key showing which level of
  the hierarchy provided the effective value.
- Every emergency override is immediately documented with full context.

**Traceability measurement:**
- Percentage of configuration changes with complete audit records (target: 100%).
- Resolution trace availability (target: 100% of keys have traceable source).
- Emergency override documentation completeness (target: 100% within 1 hour of activation).

---

## 7.6 Dimension 5 — Maintainability

**Definition:** Configuration can be understood, modified, and evolved by engineers
and operators without specialized knowledge of the configuration system internals.

**Maintainability standards:**
- Every configuration key has a description that a competent engineer can understand.
- Naming conventions are consistent and predictable (namespaced, snake_case).
- Configuration documentation is kept current with configuration changes.
- Complex inter-dependencies between configuration items are explicitly documented.

**Maintainability measurement:**
- Time to understand a new configuration item (operator survey, target: < 10 minutes).
- Documentation staleness rate (configuration items with documentation last updated
  more than 6 months ago — target: 0 for active items).

---

## 7.7 Dimension 6 — Version Integrity

**Definition:** The configuration version history is complete, correct, and provides
a reliable record of all changes.

**Version integrity standards:**
- Every change creates a new version.
- Version numbers are monotonically increasing.
- No version is deleted (version history is immutable).
- The version at any past timestamp can be reconstructed.

**Version integrity measurement:**
- Version continuity check (no gaps in version sequence — target: no gaps).
- Historical reconstruction success rate (target: 100% for any timestamp).

---

## 7.8 Dimension 7 — Security

**Definition:** Configuration is secure: sensitive values are protected, access is
controlled, and the configuration system cannot be used as an attack vector.

**Security standards:**
- All secret-classified configuration is encrypted at rest and in transit.
- No sensitive configuration values appear in logs, metrics, or dashboard output.
- Configuration access is controlled by the Security Manager.
- The configuration system detects and rejects injection attempts.

**Security measurement:**
- Secret exposure incidents (target: 0).
- Access control violations (target: 0).
- Secret scanner findings in committed files (target: 0).
- Audit chain integrity score (target: 100%).

---

## 7.9 Dimension 8 — Reliability

**Definition:** Configuration is reliably available and reliably applied. The system
behaves predictably based on its configuration.

**Reliability standards:**
- Configuration is loaded correctly on every startup (no startup failures due to
  configuration errors in production).
- Configuration changes are applied within the defined activation time.
- Configuration rollback succeeds 100% of the time.

**Reliability measurement:**
- Configuration-related startup failure rate (target: 0 in production).
- Configuration change application failure rate (target: < 0.1%).
- Rollback success rate (target: 100%).

---

## 7.10 Dimension 9 — Availability

**Definition:** The configuration system is available whenever the IIOS system is
operating. Configuration reads never block the trading system.

**Availability standards:**
- Configuration Resolution Service is available 99.99% of market hours.
- A configuration system failure does not halt the trading system (last known
  good configuration is used).
- Configuration changes can be queued when the system is unavailable and applied
  when it recovers.

**Last Known Good Configuration:**
If the configuration system becomes unavailable during operation (not at startup),
engines continue using the last successfully loaded configuration. This "last known
good" mode is a safety feature preventing configuration system failures from halting
trading. Last known good mode is logged as DEGRADED health.

---

## 7.11 Dimension 10 — Scalability

**Definition:** The configuration system scales with the growth of IIOS without
requiring architectural changes.

**Scalability standards:**
- Configuration lookup performance does not degrade as the number of keys grows.
- The configuration system handles 100+ engines without architectural modification.
- Configuration history does not grow unboundedly (retention policy controls size).

**Growth projections:**
- Year 1: ~2,000 configuration keys across 18 engines.
- Year 5: ~5,000 configuration keys across 28 engines.
- Year 10: ~10,000 configuration keys across 50 engines.
The in-memory Registry scales linearly to 10,000+ keys without performance concern.

---

## 7.12 Dimension 11 — Auditability

**Definition:** The configuration audit trail provides a complete, tamper-evident
record of all configuration activity that satisfies compliance and governance requirements.

**Auditability standards:**
- All configuration changes are logged with full context.
- The audit log is tamper-evident (hash chain).
- Audit records are retained for minimum 12 months.
- The audit trail can answer: "What was the configuration when event X occurred?"

---

## 7.13 Dimension 12 — Recovery Capability

**Definition:** The configuration system can recover from any failure mode within
defined recovery time objectives.

**Recovery time objectives:**
- Loader failure: < 5 minutes to recovery.
- Repository corruption: < 30 minutes to recovery from backup.
- Full configuration system failure: < 60 minutes to recovery.
- Audit store corruption: < 120 minutes to recovery (non-blocking — system continues
  with degraded audit capability).

---

## 7.14 Dimension 13 — Operational Stability

**Definition:** The configuration system does not introduce instability into the
trading system's operations. Configuration changes are applied safely.

**Stability standards:**
- No configuration change causes system downtime unless explicitly designed to
  (restart-required changes are scheduled for non-market hours).
- Configuration validation prevents the most common configuration errors from
  reaching production.
- Rollback capability provides a rapid escape from configuration-caused instability.
- Emergency overrides provide the ultimate stability valve.

**Change blackout windows:**
Configuration changes affecting trading behavior are blocked during market hours
(09:15–15:30 IST) unless designated as emergency changes. This prevents inadvertent
configuration changes from affecting live trading sessions.

---

*End of Part VII*

---# PART VIII — CONFIGURATION GOVERNANCE

## 8.1 Governance Overview

Configuration Governance is the system of ownership, approval, review, change
management, versioning, audit, compliance, security, retention, and continuous
improvement that ensures the IIOS configuration system is managed with the rigor
appropriate to a system making real trading decisions.

The principles of IIOS configuration governance:

1. **Authority matches responsibility.** Those who bear consequences for configuration
   decisions have the authority to make them — but within defined scope. The Architecture
   Council bears ultimate responsibility for the system's behavior and has ultimate
   authority over constitutional configuration.

2. **Governance is proportionate to risk.** A change to a timeout value for a data
   feed query requires less governance overhead than a change to the kill switch
   threshold. The governance tier system implements proportionate oversight.

3. **The audit trail is inviolable.** Every configuration change is permanently
   recorded. The record cannot be altered, deleted, or bypassed. This is the
   foundation of accountability.

4. **Change is possible but not easy.** Constitutional configuration changes are
   deliberately difficult. Operational configuration changes are straightforward
   but documented. This asymmetry prevents casual changes to consequential settings
   while enabling efficient operational management.

---

## 8.2 Ownership Framework

### Tier 1 — Architecture Council

**Members:** 2–4 senior engineers with system-wide design authority.
**Configuration scope:** Constitutional configuration, cross-cutting infrastructure,
security, and governance configuration.
**Approval mechanism:** Vote (majority or unanimous, per the approval matrix).
**Response time:** 48 hours for non-emergency changes.

**Owned configuration categories:**
- system.* — System identity and lifecycle.
- isk.kill_switch.* — Kill switch constitutional parameters.
- monitoring.health.* — OHS tier thresholds.
- security.* — All security configuration.
- governance.* — Governance framework configuration.
- compliance.* — Compliance configuration.
- environment.* — Environment definitions.

**Tier 1 change constraints:**
- Kill switch threshold changes cannot be made more permissive than the constitutional
  floor (VIX < 45, daily loss > 2%, drawdown > 15%).
- OHS tier threshold changes require unanimous Architecture Council vote.
- Security configuration changes require Security Council review (external).

---

### Tier 2 — Engine Owners

**Members:** One designated owner per engine (18 owners for 18 engines).
**Configuration scope:** Per-engine operational and behavioral configuration,
strategy parameters, model hyperparameters.
**Approval mechanism:** Single owner approval (with peer review).
**Response time:** 24 hours for non-emergency changes.

**Owned configuration categories:**
- engines.[name].* — All per-engine configuration.
- strategies.[id].* — Strategy parameters (for strategies in their engine).
- models.[id].* — Model hyperparameters (for models in their engine).
- workflows.[name].* — Workflow configuration (for workflows in their engine).
- gents.[id].* — Agent configuration (for agents in their engine).

**Tier 2 change constraints:**
- Engine configuration cannot override constitutional risk limits.
- Strategy parameter changes must be accompanied by backtesting evidence.
- Model hyperparameter changes must be accompanied by model validation evidence.
- Engine timeout values cannot be set higher than the system-level circuit breaker.

---

### Tier 3 — Operations Team

**Members:** Designated operations team (1–3 members).
**Configuration scope:** Deployment, infrastructure, monitoring, logging.
**Approval mechanism:** Single operations team member approval.
**Response time:** 8 hours for non-emergency changes.

**Owned configuration categories:**
- deployment.* — Container and deployment configuration.
- infrastructure.* — Infrastructure configuration.
- monitoring.* — Monitoring and alerting configuration (non-constitutional parts).
- logging.* — Logging configuration.
- ecovery.* — Recovery configuration.

**Tier 3 change constraints:**
- Production deployment configuration changes require Architecture Council notification.
- Infrastructure changes affecting security (network, storage encryption) require
  Architecture Council review.

---

### Tier 4 — Feature Owners

**Members:** Any engineer responsible for a feature.
**Configuration scope:** Feature flags, experimental configuration, user preferences.
**Approval mechanism:** Self-approval for feature flags; peer review for experiments.
**Response time:** Immediate for feature flags; 24 hours for experiments.

**Owned configuration categories:**
- eatures.* — Feature flags.
- experiments.[id].* — Experimental configuration.
- users.[id].* — User preferences.

**Tier 4 constraints:**
- Feature flags affecting risk behavior (e.g., disabling risk checks) require
  Architecture Council approval.
- Experimental configuration may not be applied in production without Architecture
  Council notification.

---

## 8.3 Approval Workflow

The approval workflow governs the process from configuration change proposal to
activation.

`
APPROVAL WORKFLOW DIAGRAM

PROPOSER submits change request
         |
         v
Configuration Manager receives request
         |
         v
Automated pre-check:
  - Proposer has authority for this namespace?  YES/NO
  - Value passes schema validation?             YES/NO
  - Value passes consistency validation?        YES/NO
         |
    All pass?
    YES |
         v
Review assignment (per governance tier)
         |
         v
Reviewer evaluates change:
  - Technical correctness
  - Operational safety
  - Documentation completeness
         |
    Approved?
    YES |
         v
Approval authority decision (per tier):
  - Tier 1: Architecture Council vote
  - Tier 2: Engine Owner single approval
  - Tier 3: Operations Lead single approval
  - Tier 4: Self-approval
         |
    Approved?
    YES |
         v
Configuration Manager applies change:
  - Write to Repository
  - Record in Audit Manager
  - Assign new Version
  - Notify affected engines
         |
         v
Change monitoring:
  - Track system behavior after activation
  - Alert if anomalies detected
  - Ready for rollback if needed
`

---

## 8.4 Change Management

### Change Categories

**Routine change:** A configuration change within normal operational parameters,
with no risk limit modification, following the standard approval workflow.
- Example: Adjusting a data feed timeout from 8s to 10s.
- Process: Draft → Validate → Review (24h) → Engine Owner approval → Apply.

**Significant change:** A configuration change that affects system-wide behavior,
risk limits within constitutional boundaries, or cross-engine interactions.
- Example: Reducing the decision score threshold from 6.5 to 6.0.
- Process: Draft → Validate → Architecture Council review (48h) → Vote → Apply.

**Constitutional change:** A configuration change to constitutional values (kill
switch thresholds, OHS tier definitions, governance framework configuration).
- Example: Modifying the VIX kill switch threshold.
- Process: Draft → Architecture Council review (72h minimum) → Unanimous vote
  (or quorum for non-constitutional limits) → Apply.

**Emergency change:** An urgent configuration change required during a live
trading emergency.
- Process: Any Tier 1 member authorization → Immediate Apply →
  Documentation within 1 hour → Post-emergency review within 48 hours.

**Scheduled change:** A configuration change planned in advance for a specific
activation time (e.g., before market open, during planned maintenance window).
- Process: Any tier's standard workflow → Mark as scheduled with activation
  time → Automatic activation at scheduled time.

### Change Blackout Windows

| Window | Duration | What is blocked |
|--------|----------|----------------|
| Market hours | 09:15–15:30 IST | All trading-affecting changes |
| Pre-open | 09:00–09:15 IST | Risk configuration changes |
| Expiry days | Full day | Strategy configuration changes |
| System maintenance | Announced in advance | All changes |

**Exception:** Emergency changes bypass all blackout windows. Emergency changes
during market hours require immediate Architecture Council notification.

---

## 8.5 Version Control

Configuration version control is separate from (but complementary to) the source
code version control.

### Configuration Version Control vs Source Code Version Control

| Aspect | Configuration VC | Source Code VC |
|--------|-----------------|----------------|
| Repository | Configuration Repository + git | Git |
| Version scheme | [schema].[value].[patch] | MAJOR.MINOR.PATCH |
| Branching | Single active branch | Feature branches |
| History | Permanent, immutable | Commits may be squashed |
| Rollback | Any version, immediate | Via revert commit |
| Audit | Configuration Audit Manager | Git commit history |

### Configuration Version Tagging

Key versions are tagged with descriptive labels:
- 1.0.0-initial — Initial production configuration.
- 1.2.0-kill-switch-tightened — Kill switch threshold tightened to 42.
- 2.0.0-schema-upgrade — Major schema version upgrade.
- 2.1.0-q2-strategy-rebalance — Quarterly strategy parameter rebalance.

Tags are immutable once created.

---

## 8.6 Review Cycle

Configuration is reviewed on a regular schedule independent of change requests.

### Scheduled Review Calendar

| Review Type | Frequency | Scope | Performed By |
|------------|-----------|-------|-------------|
| Configuration correctness review | Monthly | All Tier 2 configuration | Engine Owners |
| Constitutional limits review | Quarterly | All Tier 1 configuration | Architecture Council |
| Security configuration review | Quarterly | All security.* | Security owner |
| Feature flag cleanup review | Quarterly | All features.* | Feature Owners |
| Emergency override post-mortem | Within 48h of override | Override specifically | Architecture Council |
| Full configuration audit | Annually | All configuration | Architecture Council + external |
| Compliance configuration review | Annually | compliance.* | Compliance officer |

---

## 8.7 Audit Process

### Audit Trail Requirements

The configuration audit trail must answer:
1. What configuration changes were made in a given time period?
2. Who made each change and with whose approval?
3. What configuration was active during a specific operational event?
4. Are there any unauthorized configuration changes?
5. Have all emergency overrides been properly documented and resolved?

### Audit Record Completeness

An audit trail is complete if and only if:
- Every change (approved, rejected, attempted) has a record.
- Every record has: timestamp, actor, key, old value, new value, rationale, approver.
- Every emergency override has a separate record with activation and deactivation timestamps.
- The tamper-evident chain is intact.
- Records are retained for the required period.

### Audit Review Schedule

| Audit Activity | Frequency | Reviewer |
|---------------|-----------|----------|
| Change frequency analysis | Weekly (automated) | Monitoring Manager |
| Access pattern analysis | Weekly (automated) | Security Manager |
| Emergency override review | On occurrence + quarterly | Architecture Council |
| Full audit log verification | Monthly | Architecture Council |
| External audit preparation | Annually | Compliance officer |

---

## 8.8 Compliance Framework

### Regulatory Context

IIOS operates as an automated trading system in Indian equity markets. The applicable
compliance framework includes:

- SEBI (Securities and Exchange Board of India) algorithmic trading regulations.
- NSE and BSE exchange compliance requirements for automated order systems.
- Internal IIOS compliance policies.

### Compliance Configuration Requirements

1. **Audit trail retention:** Minimum 5 years for configuration affecting order generation.

2. **Kill switch documentation:** Kill switch configuration and any changes must be
   documented with the regulatory rationale.

3. **Surveillance configuration:** Configuration for wash trade prevention, spoofing
   prevention, and order-to-trade ratio enforcement must be compliant with SEBI
   circular requirements.

4. **Change management documentation:** Evidence of configuration governance processes
   must be available for regulatory inspection.

5. **Emergency override documentation:** Any emergency override affecting order generation
   must be documented within 24 hours with: the trigger, the response, the authorization,
   and the resolution.

---

## 8.9 Security Framework

### Configuration Security Principles

1. **Least privilege access.** Each component reads only the configuration namespaces
   it requires. No component has write access to the Configuration Repository
   except the Configuration Manager.

2. **Defense in depth.** Multiple layers protect sensitive configuration: encryption
   at rest, encryption in transit, access control, secret scanning, and audit logging.

3. **Separation of secrets.** Credentials and tokens are never in committed files.
   They are managed separately via environment variables or a secrets manager.

4. **Immutable audit.** The audit trail cannot be modified by any component or
   operator. This prevents covering up unauthorized changes.

5. **Secret rotation.** Secrets are rotated on schedule and on suspected compromise.
   The rotation schedule is defined in security.secrets_management.*.

---

## 8.10 Retention Policy

### Retention by Configuration Category

| Category | Active Retention | Archive Retention | Total |
|----------|-----------------|-------------------|-------|
| Constitutional (risk, governance, security) | Indefinite | Indefinite | Permanent |
| Engine operational | 5 years active | Indefinite archive | Permanent |
| Strategy parameters | 3 years active | 10 years archive | 13 years |
| Model hyperparameters | 3 years active | 10 years archive | 13 years |
| Feature flags | Duration of feature | 3 years after retirement | Variable |
| Emergency overrides | 1 year active | Indefinite | Permanent |
| Audit records | 12 months immediate | 5 years archive | 6+ years |
| User preferences | Active user account | 2 years after account close | Variable |

---

## 8.11 Continuous Improvement

### Improvement Process

The configuration governance framework itself is reviewed and improved on a defined
schedule.

**Quarterly improvement review:**
- Review the frequency of validation failures (are there patterns indicating
  missing validation rules?).
- Review the frequency of emergency overrides (can they be reduced with better
  normal-process support?).
- Review the approval cycle times (are governance processes creating bottlenecks?).
- Review configuration anti-pattern detections (are new anti-patterns emerging?).

**Annual framework review:**
- Full review of the Configuration Constitution (Part IX) against actual configuration
  issues encountered.
- Assessment of whether governance tiers are correctly calibrated.
- Assessment of whether the hierarchy is serving its purpose.
- Identification of any new configuration categories needed.

**Improvement record:** All framework changes are recorded in the Governance Decision
Records (Supplement E) and in the Amendment History of this document.

---

*End of Part VIII*

---

# PART IX — CONFIGURATION CONSTITUTION

## 9.1 Constitution Overview

The Configuration Constitution contains 110 engineering rules governing the complete
configuration lifecycle in IIOS. Rules are classified:

**[H] — HARD:** Automatically enforced by CI or the configuration system. Violation
blocks change acceptance or deployment.

**[S] — SOFT:** Warning triggered. Requires documented justification to proceed.

**[A] — ADVISORY:** Best practice. Encouraged but not enforced.

---

## Category 1 — Identity Rules (CFG-ID-001 through CFG-ID-010)

**CFG-ID-001 [H]:** Every configuration key has a fully qualified name following
the pattern [namespace].[sub_namespace].[key_name]. Bare key names without
namespaces are forbidden.

**CFG-ID-002 [H]:** Configuration key names use snake_case throughout. No camelCase,
PascalCase, kebab-case, or SCREAMING_SNAKE_CASE in key names.

**CFG-ID-003 [H]:** Configuration namespaces correspond to a defined category in
Part II. Namespaces outside the defined taxonomy require Architecture Council approval.

**CFG-ID-004 [H]:** Every configuration key is registered in the Configuration
Registry before it is used. Unregistered keys in configuration files trigger a
validation warning. Unregistered keys consumed by code trigger a validation error.

**CFG-ID-005 [H]:** Every configuration key has exactly one owner. Ownership is
documented in the Configuration Registry metadata.

**CFG-ID-006 [S]:** Configuration keys have descriptive names that reveal their
purpose. Abbreviations are used only for universally understood terms.

**CFG-ID-007 [H]:** Configuration keys for the same logical concept use the same
name across all namespaces. If isk.kill_switch.vix_threshold is the pattern,
there should not also be engines.risk_guardian.vix_limit for the same concept.

**CFG-ID-008 [H]:** The emergency namespace is reserved exclusively for emergency
override configuration. No non-emergency configuration uses this namespace.

**CFG-ID-009 [S]:** Configuration key names that include 	emp, 	est, old,

ew, 2, or similar version-suffix conventions are prohibited. Configuration
is versioned by the version management system, not by key name variations.

**CFG-ID-010 [A]:** Configuration key names are chosen to be meaningful to a person
encountering the key for the first time, without requiring knowledge of the system
internals.

---

## Category 2 — Naming Rules (CFG-NAME-001 through CFG-NAME-010)

**CFG-NAME-001 [H]:** The namespace component is the engine name (snake_case,
matching the engine package name) for engine configuration, or the category name
for system-level configuration.

**CFG-NAME-002 [H]:** Boolean configuration keys begin with an enabling prefix:
enable_, disable_, llow_, equire_, or is_. Examples: eatures.enable_ml_scoring,
isk.require_pre_trade_check.

**CFG-NAME-003 [H]:** Timeout configuration keys end with _ms (milliseconds),
_s (seconds), or _min (minutes) to make the unit explicit. A timeout key
without a unit suffix is a naming violation.

**CFG-NAME-004 [H]:** Percentage configuration keys end with _pct to make the
representation explicit (value is a decimal fraction: 0.02 = 2%). A percentage
key without _pct suffix is a naming violation.

**CFG-NAME-005 [H]:** Count configuration keys end with _count or _max or
_min to indicate they are integer counts. Examples: isk.position_limits.max_open_positions_count.

**CFG-NAME-006 [S]:** Path configuration keys end with _path for file paths
and _dir for directory paths.

**CFG-NAME-007 [H]:** Environment variable names for configuration override are
prefixed with IIOS_ and use the key path with dots replaced by underscores and
in UPPER_CASE. Example: isk.kill_switch.vix_threshold → IIOS_RISK_KILL_SWITCH_VIX_THRESHOLD.

**CFG-NAME-008 [S]:** Configuration keys in the isk.* namespace that govern
constitutional limits include constitutional in their name to make their protected
status explicit.

**CFG-NAME-009 [H]:** A configuration key name may not be the same as a Python
keyword, built-in function name, or reserved word in the IIOS domain vocabulary.

**CFG-NAME-010 [A]:** Configuration key names are reviewed for naming consistency
with existing keys in the same namespace when a new key is added.

---

## Category 3 — Validation Rules (CFG-VAL-001 through CFG-VAL-015)

**CFG-VAL-001 [H]:** Every configuration key in the Registry has a defined data
type. Typeless keys are not permitted.

**CFG-VAL-002 [H]:** Every configuration key in the Registry has a defined valid
range or enumeration of valid values. Keys without range definitions are validated
for type only.

**CFG-VAL-003 [H]:** Configuration is validated before it is loaded into any engine.
An engine that reads unvalidated configuration is a design violation.

**CFG-VAL-004 [H]:** Configuration validation runs as part of every CI pipeline
check. A CI pipeline that does not validate configuration is incomplete.

**CFG-VAL-005 [H]:** Risk limit configuration cannot be set to values more permissive
than the constitutional floor values. This validation rule cannot be overridden by
any operator.

**CFG-VAL-006 [H]:** Production environment configuration is validated against an
additional set of production-safety rules: risk limits must be at or tighter than
base, logging must not be DEBUG, broker mode must be verified.

**CFG-VAL-007 [S]:** Configuration consistency validation checks that related
values are logically compatible. Consistency rules are documented in the schema.

**CFG-VAL-008 [H]:** Configuration completeness validation confirms that no required
key is missing before the system is allowed to start.

**CFG-VAL-009 [H]:** Configuration cross-reference validation confirms that any
configuration value that references another entity (engine name, strategy ID, model ID)
references an entity that actually exists.

**CFG-VAL-010 [H]:** Configuration security validation confirms that no secret
values appear in non-secret namespaces and no plaintext credentials appear in any
configuration file.

**CFG-VAL-011 [S]:** Warning validation identifies configuration values at the
extremes of their valid range, flagging them for human review.

**CFG-VAL-012 [H]:** Configuration schema version validation confirms that the
loaded configuration files are compatible with the current schema version.

**CFG-VAL-013 [H]:** Emergency override configuration is validated immediately
upon entry (before the override is applied). An invalid emergency override is
rejected with a clear error. The validation for emergency overrides is intentionally
minimal — only type and constitutional floor checks — to avoid blocking urgent response.

**CFG-VAL-014 [S]:** Validation rules themselves are version-controlled and audited.
A change to a validation rule that allows previously-invalid configuration is a
governance event requiring Architecture Council review.

**CFG-VAL-015 [H]:** Validation results are always logged. A validation event
(pass or fail) is never silent.

---

## Category 4 — Inheritance Rules (CFG-INH-001 through CFG-INH-010)

**CFG-INH-001 [H]:** The 12-level hierarchy (Part IV) is the only inheritance
mechanism. Ad-hoc inheritance (one engine reading another engine's configuration
as its default) is forbidden.

**CFG-INH-002 [H]:** Lower hierarchy levels override higher levels for the same
key. Higher levels provide defaults; lower levels provide specifics.

**CFG-INH-003 [H]:** Every required key must have a default at the Global Defaults
level (Level 1). No required key may depend on an environment-level default for
its baseline value.

**CFG-INH-004 [H]:** Inheritance does not cross namespace boundaries. A value in
isk.kill_switch.* cannot be inherited by engines.risk_guardian.*. They are
always two distinct keys even if they happen to have the same value.

**CFG-INH-005 [S]:** Configuration at a lower level of the hierarchy should not
re-specify values that are already correct from a higher level. Redundant specifications
increase maintenance cost.

**CFG-INH-006 [H]:** The Resolution Service's 	race() function must be able to
identify which level of the hierarchy provided any effective configuration value.
A configuration value that cannot be traced is a structural defect.

**CFG-INH-007 [H]:** When an environment-level override is applied, it overrides
the entire key value, not a sub-field of a nested structure. Partial overrides of
complex values are not supported at environment level.

**CFG-INH-008 [S]:** Configuration inheritance chains of more than 4 levels for
a single key are reviewed for simplification. Deep inheritance chains increase
debugging complexity.

**CFG-INH-009 [H]:** Emergency overrides are always at the top of the hierarchy.
No component may override an active emergency override except another emergency
override or an Architecture Council-approved change.

**CFG-INH-010 [A]:** Configuration inheritance is documented in the Configuration
Catalog for every key that has values defined at multiple levels.

---

## Category 5 — Isolation Rules (CFG-ISO-001 through CFG-ISO-010)

**CFG-ISO-001 [H]:** Engine A does not read configuration from Engine B's namespace.
Each engine reads only its own namespace and system-level namespaces.

**CFG-ISO-002 [H]:** Configuration namespaces do not share keys. A key name within
engines.risk_guardian.* exists nowhere else. Uniqueness is enforced by the Registry.

**CFG-ISO-003 [H]:** Configuration changes in one namespace do not automatically
affect other namespaces. Side effects across namespaces are explicit, documented,
and approved.

**CFG-ISO-004 [S]:** When a configuration change is expected to affect multiple
engine namespaces, the change is described as a coordinated change and all affected
namespaces are updated atomically.

**CFG-ISO-005 [H]:** Session configuration (Level 10) is isolated per trading session.
Session configuration from one session does not bleed into the next session.

**CFG-ISO-006 [H]:** Runtime configuration (Level 11) is isolated per engine. An
engine's runtime adjustment of configuration does not affect other engines.

**CFG-ISO-007 [S]:** Test environment configuration is completely isolated from
production configuration. No production configuration value appears in the test
environment without explicit documentation.

**CFG-ISO-008 [H]:** Experimental configuration is isolated from production
configuration. An experimental configuration item cannot affect the production
trading system without Architecture Council approval.

**CFG-ISO-009 [H]:** Emergency configuration is isolated in the emergency.*
namespace and does not persist after its expiry time.

**CFG-ISO-010 [A]:** Configuration for different deployment environments is stored
in separate files (production.yaml, paper.yaml, development.yaml) rather than
conditional blocks within a single file.

---

## Category 6 — Override Rules (CFG-OVR-001 through CFG-OVR-010)

**CFG-OVR-001 [H]:** Every override at every level is traceable to its source.
The Resolution Service must be able to explain why any given value has its effective
value.

**CFG-OVR-002 [H]:** A lower hierarchy level can make risk limits more conservative
(tighter). It cannot make them more permissive than the immediately higher level's
value.

**CFG-OVR-003 [H]:** The production.yaml environment file cannot set risk limits
more permissive than ase.yaml. This is a validation-enforced constitutional constraint.

**CFG-OVR-004 [H]:** Environment variable overrides (Level 5 in source priority)
are always logged when applied. Silent overrides are a security concern.

**CFG-OVR-005 [S]:** A namespace with more than 10 overrides at a given level
relative to the level above is reviewed. Excessive overrides may indicate the
default is wrong or the inheritance structure is mismatched.

**CFG-OVR-006 [H]:** Emergency overrides automatically expire after their declared
expiry time. There is no mechanism to extend an active emergency override — a new
override must be created.

**CFG-OVR-007 [H]:** Runtime overrides (Level 11) are not persisted to the
Repository. They exist only in memory and are lost on restart.

**CFG-OVR-008 [S]:** Configuration profiles (e.g., aggressive trading, conservative
trading) that override risk limits are reviewed quarterly to confirm they remain
appropriate.

**CFG-OVR-009 [H]:** No automated process may apply an emergency override without
human authorization. Emergency overrides are always human-initiated.

**CFG-OVR-010 [A]:** When an override is applied, the expected behavioral change
is documented alongside the override. This enables post-hoc verification that the
override had its intended effect.

---

## Category 7 — Versioning Rules (CFG-VER-001 through CFG-VER-010)

**CFG-VER-001 [H]:** Every configuration change creates a new version. Version-less
changes are prohibited.

**CFG-VER-002 [H]:** Configuration versions are monotonically increasing. Version
numbers are never reused.

**CFG-VER-003 [H]:** The complete history of all configuration versions is retained
indefinitely. No version is deleted.

**CFG-VER-004 [H]:** Every configuration version is tagged with: author, timestamp,
change description, and approval reference.

**CFG-VER-005 [H]:** A rollback creates a new version (pointing to the restored values),
not a deletion of the version being rolled back from. The rolled-back version remains
in history.

**CFG-VER-006 [S]:** Configuration versions that represent significant operational
changes (kill switch threshold changes, strategy parameter rebalances) are tagged
with descriptive labels.

**CFG-VER-007 [H]:** Schema version increments are backwards-compatible within a
MINOR version. A schema MAJOR version increment indicates a breaking change requiring
migration.

**CFG-VER-008 [S]:** Configuration version diffs are reviewed for each release to
confirm only intended changes are included.

**CFG-VER-009 [H]:** The Configuration Version Manager and source code Version Control
system (git) are kept synchronized: every source code version tag has a corresponding
configuration version tag.

**CFG-VER-010 [A]:** Configuration version history is summarized in the CHANGELOG.md
alongside source code changes, providing a unified view of system evolution.

---

## Category 8 — Security Rules (CFG-SEC-001 through CFG-SEC-010)

**CFG-SEC-001 [H]:** No secret-classified configuration value (credentials, tokens,
encryption keys) appears in any committed file.

**CFG-SEC-002 [H]:** The secret scanner runs on every pull request and on every direct
push to the main branch.

**CFG-SEC-003 [H]:** All secret-classified configuration is encrypted at rest.

**CFG-SEC-004 [H]:** Secret-classified configuration is never logged, never displayed
in dashboards, and never included in error messages.

**CFG-SEC-005 [H]:** Access to security-classified configuration (confidential and secret)
is logged by the Audit Manager. All access is traceable.

**CFG-SEC-006 [H]:** Configuration access control is enforced: each component may
read only the namespaces it is authorized for. Authorization is defined in CODEOWNERS.

**CFG-SEC-007 [S]:** Secret rotation is performed on schedule and documented in the
audit log.

**CFG-SEC-008 [H]:** Configuration values in non-secret namespaces are scanned for
pattern-matching known secret formats (API key patterns, token patterns). Matches are
treated as violations.

**CFG-SEC-009 [H]:** The emergency configuration pathway has its own access control.
Only Architecture Council members may activate emergency overrides.

**CFG-SEC-010 [H]:** Configuration that affects order generation (risk limits, broker
mode, kill switch thresholds) has enhanced access logging: every read of these values
during market hours is logged.

---

## Category 9 — Auditability Rules (CFG-AUD-001 through CFG-AUD-010)

**CFG-AUD-001 [H]:** Every configuration change is logged in the Audit Manager before
the change is applied. "Apply then audit" is prohibited.

**CFG-AUD-002 [H]:** Audit records are immutable once written. No mechanism exists
to modify or delete an audit record.

**CFG-AUD-003 [H]:** The audit log uses a hash chain. Every audit record includes the
hash of the previous record. Chain breaks indicate tampering.

**CFG-AUD-004 [H]:** Audit log integrity is verified daily. A broken chain triggers
an immediate security alert.

**CFG-AUD-005 [H]:** Every emergency override activation creates an audit record
within 60 seconds of activation. Delayed audit records for emergency overrides are
a governance violation.

**CFG-AUD-006 [S]:** The audit log provides a complete answer to: "What configuration
was active at time T?" for any T in the system's history.

**CFG-AUD-007 [H]:** Audit records are retained for minimum 12 months in immediately
accessible storage, and for minimum 5 years in archive storage.

**CFG-AUD-008 [S]:** The audit log is reviewed weekly (automated) for unusual access
patterns: high-frequency reads of risk configuration, multiple failed change attempts,
access outside of business hours.

**CFG-AUD-009 [H]:** Rejected configuration changes are audited with the same
completeness as approved changes. The reason for rejection is part of the audit record.

**CFG-AUD-010 [H]:** The audit system is monitored by the Configuration Health Manager.
An unavailable audit system blocks new configuration changes.

---

## Category 10 — Recovery Rules (CFG-REC-001 through CFG-REC-010)

**CFG-REC-001 [H]:** Every configuration has a rollback path. A configuration item
with no rollback path is not permitted.

**CFG-REC-002 [H]:** Configuration backups are taken daily. The system cannot go
live without confirming a successful initial backup.

**CFG-REC-003 [H]:** Every backup is verified for integrity at creation time. An
unverified backup is treated as invalid.

**CFG-REC-004 [H]:** Backup restore is tested monthly. A backup that cannot be
restored is not a valid backup.

**CFG-REC-005 [S]:** Recovery time from a backup must be < 30 minutes for full
configuration restore. If the restore process takes longer, the recovery procedure
is reviewed and optimized.

**CFG-REC-006 [H]:** The last known good configuration is always available. Engines
continue with cached configuration if the configuration system fails during operation.

**CFG-REC-007 [H]:** A configuration recovery event triggers a post-mortem within
48 hours. The post-mortem documents the failure mode, the recovery steps, and the
prevention measures.

**CFG-REC-008 [S]:** Recovery procedures are documented in docs/operations/ and
tested quarterly.

**CFG-REC-009 [H]:** Configuration recovery is performed in the correct component
order (Registry first, then Loader, then Resolver, then all other components).
Out-of-order recovery creates inconsistent state.

**CFG-REC-010 [A]:** Post-recovery, a full configuration validation is run before
the system is declared healthy.

---

## Category 11 — Compliance Rules (CFG-CMP-001 through CFG-CMP-010)

**CFG-CMP-001 [H]:** Configuration affecting automated order generation is retained
for a minimum of 5 years.

**CFG-CMP-002 [H]:** Kill switch configuration and any changes to it are documented
with regulatory rationale.

**CFG-CMP-003 [H]:** The configuration system can produce an audit export in a format
suitable for regulatory inspection.

**CFG-CMP-004 [S]:** Configuration for surveillance (wash trade prevention, spoofing
prevention) is reviewed annually against applicable regulations.

**CFG-CMP-005 [H]:** No configuration change that disables or weakens a surveillance
or compliance mechanism is permitted without Architecture Council approval.

**CFG-CMP-006 [S]:** Compliance configuration is reviewed by the designated compliance
officer before production deployment.

**CFG-CMP-007 [H]:** Emergency overrides affecting compliance configuration are
specifically documented with their compliance impact assessed.

**CFG-CMP-008 [S]:** Configuration changes following a regulatory update are
reviewed by the compliance officer within 30 days of the regulatory change.

**CFG-CMP-009 [H]:** Configuration retention policy is itself configuration (not
hardcoded) to allow adaptation to regulatory changes without code deployment.

**CFG-CMP-010 [A]:** Configuration documentation includes compliance annotations
where specific values are required or constrained by regulation.

---

## Category 12 — Governance Rules (CFG-GOV-001 through CFG-GOV-010)

**CFG-GOV-001 [H]:** No configuration change is applied without passing through
the Configuration Manager. Direct file edits on the server are a governance violation.

**CFG-GOV-002 [H]:** Every configuration change has a documented rationale. "No
reason" or "housekeeping" without further detail is not an acceptable rationale.

**CFG-GOV-003 [H]:** Configuration governance tiers are proportionate to risk.
The Architecture Council does not govern routine operational configuration, and
Feature Owners do not govern constitutional configuration.

**CFG-GOV-004 [H]:** The governance process for constitutional changes includes a
minimum deliberation period (48 hours for significant changes, 72 hours for constitutional).

**CFG-GOV-005 [S]:** Configuration governance decisions are documented in the
Governance Decision Records (Supplement E).

**CFG-GOV-006 [H]:** No single person may both propose and approve a configuration
change (except Tier 4 feature flag self-approval). Every change has a separate
proposer and approver.

**CFG-GOV-007 [H]:** The configuration governance framework is itself subject to
governance. Changes to governance rules require Architecture Council vote.

**CFG-GOV-008 [S]:** Governance decision records are reviewed annually to identify
patterns and improve the governance process.

**CFG-GOV-009 [H]:** A configuration change that is applied without the required
approvals is treated as an incident. A post-mortem is conducted and the governance
gap is closed.

**CFG-GOV-010 [A]:** Governance overhead is minimized for low-risk configuration
while being thorough for high-risk configuration. The governance tier system is
calibrated annually.

---

## Category 13 — Human Override Rules (CFG-HUM-001 through CFG-HUM-010)

**CFG-HUM-001 [H]:** The system cannot prevent an authorized human from overriding
any configuration, including risk limits, via the emergency override mechanism.
This is an intentional safety property: the human safety valve is always available.

**CFG-HUM-002 [H]:** Human emergency overrides are logged immediately, completely,
and immutably. The human authority cannot prevent the audit.

**CFG-HUM-003 [H]:** Emergency override capability is accessible without network
dependency on any external service. An operator with direct server access can always
apply an emergency override.

**CFG-HUM-004 [S]:** Emergency override interfaces are tested quarterly to confirm
they function under system degradation conditions.

**CFG-HUM-005 [H]:** The emergency override mechanism cannot itself be disabled by
configuration. It is hardwired as a permanent capability.

**CFG-HUM-006 [H]:** Emergency overrides that relax risk limits below constitutional
minimums require the authorization of at least 2 Architecture Council members.

**CFG-HUM-007 [S]:** Every activation of the emergency override triggers a
requirement for a post-mortem. Post-mortems are not optional.

**CFG-HUM-008 [H]:** The system provides a current active configuration summary
to any authorized operator on demand. An operator cannot be unaware of the current
effective configuration.

**CFG-HUM-009 [S]:** Configuration override notifications are sent to all Architecture
Council members when a Tier 1 change is applied. No Tier 1 change is invisible to
the governance body.

**CFG-HUM-010 [A]:** Configuration override tooling is designed for use under stress.
An operator dealing with a live emergency can apply a critical configuration override
in fewer than 60 seconds.

---

*End of Part IX — Configuration Constitution (110 rules)*

---# PART X — CONFIGURATION READINESS CHECKLIST

## 10.1 Readiness Overview

The Configuration Readiness Checklist confirms that the IIOS configuration system
is ready for production deployment. All HARD checks must pass. SOFT checks must pass
or have documented justifications. A system that fails the readiness checklist is
not permitted to operate with live orders.

The checklist is organized into 10 domains. Each domain has a defined minimum pass
threshold. The overall readiness certification requires all 10 domains to pass.

---

## 10.2 Domain 1 — Global Configuration Ready

**Purpose:** Confirm all system-level and global configuration is correct and complete.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-01-01 | HARD | config/environments/base.yaml exists and parses without error |
| CRD-01-02 | HARD | All required keys in the Registry have defaults in base.yaml |
| CRD-01-03 | HARD | system.mode is set correctly for the target environment |
| CRD-01-04 | HARD | Constitutional risk limits are set and within required range |
| CRD-01-05 | HARD | OHS tier thresholds match constitutional definitions |
| CRD-01-06 | HARD | Governance configuration is complete and valid |
| CRD-01-07 | SOFT | Configuration version is tagged with the deployment version |
| CRD-01-08 | SOFT | base.yaml has been reviewed within the last 90 days |
| CRD-01-09 | HARD | No orphaned keys (keys in file not in Registry) |
| CRD-01-10 | HARD | No required keys missing (Registry keys with no values) |

**Domain pass threshold:** All 7 HARD checks pass, at least 1 of 2 SOFT checks pass.

---

## 10.3 Domain 2 — Environment Ready

**Purpose:** Confirm environment-specific configuration is correct for the target environment.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-02-01 | HARD | Target environment file exists (production.yaml / paper.yaml) |
| CRD-02-02 | HARD | system.mode matches target environment name |
| CRD-02-03 | HARD | Production risk limits are not more permissive than base |
| CRD-02-04 | HARD | Broker mode is correct for environment (live for production) |
| CRD-02-05 | HARD | Data feed configuration is correct for environment |
| CRD-02-06 | HARD | Logging level is appropriate (INFO or WARNING for production) |
| CRD-02-07 | HARD | No development-only settings are active in production |
| CRD-02-08 | SOFT | Environment file has been reviewed for this deployment |
| CRD-02-09 | HARD | .env file is not committed; .env.example is current |
| CRD-02-10 | HARD | All environment variables documented in .env.example are provided |

**Domain pass threshold:** All 8 HARD checks pass, SOFT check documented if not passing.

---

## 10.4 Domain 3 — Engine Configuration Ready

**Purpose:** Confirm all 18 engine configurations are present, valid, and appropriate.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-03-01 | HARD | All 18 engine configuration files exist |
| CRD-03-02 | HARD | All engine configurations validate against their schemas |
| CRD-03-03 | HARD | risk_guardian configuration is at constitutional limits or tighter |
| CRD-03-04 | HARD | execution_engine broker mode matches system broker mode |
| CRD-03-05 | HARD | orchestrator cycle intervals are within defined valid ranges |
| CRD-03-06 | HARD | All engine timeout values are achievable under normal network conditions |
| CRD-03-07 | SOFT | All engine configurations have been reviewed by their owners |
| CRD-03-08 | HARD | No engine configuration references another engine's namespace |
| CRD-03-09 | HARD | learning_system performance thresholds are consistent with promotion gates |
| CRD-03-10 | SOFT | Engine configuration documentation is current |

**Domain pass threshold:** All 8 HARD checks pass.

---

## 10.5 Domain 4 — Validation Passed

**Purpose:** Confirm all validation passes with no blocking errors.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-04-01 | HARD | Schema validation: all files pass without errors |
| CRD-04-02 | HARD | Type validation: all values match defined types |
| CRD-04-03 | HARD | Range validation: all values within valid ranges |
| CRD-04-04 | HARD | Consistency validation: no conflicting values |
| CRD-04-05 | HARD | Completeness validation: no missing required values |
| CRD-04-06 | HARD | Security validation: no secrets in committed files |
| CRD-04-07 | HARD | Governance validation: no constitutional limit violations |
| CRD-04-08 | HARD | Cross-reference validation: all referenced entities exist |
| CRD-04-09 | SOFT | Warning validation: no extreme-range values without justification |
| CRD-04-10 | HARD | CI validation pipeline reports all checks PASS |

**Domain pass threshold:** All 9 HARD checks pass.

---

## 10.6 Domain 5 — Security Approved

**Purpose:** Confirm the configuration system's security posture is correct.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-05-01 | HARD | Secret scanner reports zero findings in all configuration files |
| CRD-05-02 | HARD | All secret-classified configuration is stored outside committed files |
| CRD-05-03 | HARD | Encryption is enabled for all confidential and secret configuration |
| CRD-05-04 | HARD | Access control configuration is in place for all namespaces |
| CRD-05-05 | HARD | Audit log is operational and accepting records |
| CRD-05-06 | HARD | Audit chain is intact (verified) |
| CRD-05-07 | SOFT | Security configuration has been reviewed by the security owner |
| CRD-05-08 | HARD | No orphaned secrets (secrets in manager not referenced in configuration) |
| CRD-05-09 | HARD | Secret rotation schedule is defined for all secret-classified items |
| CRD-05-10 | SOFT | Security review findings from last 90 days have been addressed |

**Domain pass threshold:** All 8 HARD checks pass.

---

## 10.7 Domain 6 — Recovery Verified

**Purpose:** Confirm that recovery capabilities are operational and tested.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-06-01 | HARD | At least one successful configuration backup exists |
| CRD-06-02 | HARD | Most recent backup integrity verification passed |
| CRD-06-03 | HARD | Backup restore test has been performed within the last 30 days |
| CRD-06-04 | HARD | Restore test was successful |
| CRD-06-05 | HARD | Emergency override mechanism is functional (tested) |
| CRD-06-06 | HARD | Rollback procedure is documented and tested |
| CRD-06-07 | SOFT | Recovery runbook is current and reviewed |
| CRD-06-08 | HARD | Recovery from the primary failure scenarios is documented |
| CRD-06-09 | HARD | Last known good configuration mechanism is in place |
| CRD-06-10 | SOFT | Recovery time estimates are within acceptable targets |

**Domain pass threshold:** All 8 HARD checks pass.

---

## 10.8 Domain 7 — Audit Ready

**Purpose:** Confirm the configuration audit trail is complete, operational, and compliant.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-07-01 | HARD | Audit log is operational and recording events |
| CRD-07-02 | HARD | Audit chain integrity check passed |
| CRD-07-03 | HARD | Audit record format complies with the defined schema |
| CRD-07-04 | HARD | Audit log retention is configured per retention policy |
| CRD-07-05 | HARD | Audit access control is in place |
| CRD-07-06 | HARD | All recent configuration changes have complete audit records |
| CRD-07-07 | SOFT | Audit export functionality is tested |
| CRD-07-08 | HARD | No audit gaps in the last 30 days of records |
| CRD-07-09 | SOFT | Audit compliance check confirms regulatory requirements are met |
| CRD-07-10 | HARD | Audit system monitoring is in place with alerts configured |

**Domain pass threshold:** All 8 HARD checks pass.

---

## 10.9 Domain 8 — Documentation Complete

**Purpose:** Confirm configuration documentation is complete and current.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-08-01 | SOFT | All configuration keys in the Registry have descriptions |
| CRD-08-02 | SOFT | All configuration keys in the Registry have owner assignments |
| CRD-08-03 | HARD | This Configuration Framework document is current |
| CRD-08-04 | SOFT | .env.example documents all environment variables |
| CRD-08-05 | SOFT | Configuration Catalog is generated and current |
| CRD-08-06 | SOFT | Recovery runbooks reference current configuration |
| CRD-08-07 | SOFT | Architecture Council has reviewed documentation within 90 days |
| CRD-08-08 | HARD | No configuration items are undocumented and in active use |
| CRD-08-09 | SOFT | Configuration change history in CHANGELOG.md is current |
| CRD-08-10 | SOFT | Training materials reference current configuration structure |

**Domain pass threshold:** All 2 HARD checks pass, at least 5 of 8 SOFT checks pass.

---

## 10.10 Domain 9 — Operationally Ready

**Purpose:** Confirm the configuration system is ready for live operational use.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-09-01 | HARD | Configuration Health Manager reports OPTIMAL or NOMINAL |
| CRD-09-02 | HARD | No drift detected between running and committed configuration |
| CRD-09-03 | HARD | No active emergency overrides (or documented justification) |
| CRD-09-04 | HARD | Configuration Monitoring Service is operational and alerting |
| CRD-09-05 | HARD | Configuration Load completes without errors on clean start |
| CRD-09-06 | HARD | Configuration Resolution Service responds within latency target |
| CRD-09-07 | SOFT | Change management queue has no stale pending changes |
| CRD-09-08 | HARD | All engine configurations load and validate at engine startup |
| CRD-09-09 | SOFT | Operator responsible for configuration is aware of current state |
| CRD-09-10 | HARD | Configuration blackout window policy is enforced for market hours |

**Domain pass threshold:** All 8 HARD checks pass.

---

## 10.11 Domain 10 — Archived Correctly

**Purpose:** Confirm that retired and deprecated configuration is properly archived.

| Check | Classification | Criterion |
|-------|---------------|-----------|
| CRD-10-01 | HARD | No retired keys are referenced by active code |
| CRD-10-02 | SOFT | All deprecated keys have documented successors |
| CRD-10-03 | HARD | All retired keys have archive records |
| CRD-10-04 | SOFT | Deprecated key warnings are monitored |
| CRD-10-05 | HARD | Archive records have complete metadata |
| CRD-10-06 | SOFT | Archive is reviewed for cleanup quarterly |
| CRD-10-07 | SOFT | Deprecated keys have planned retirement dates |
| CRD-10-08 | HARD | No configuration files reference archived keys as active |
| CRD-10-09 | SOFT | Archive access is tested and documented |
| CRD-10-10 | HARD | Retired keys cannot be accidentally re-used (Registry enforcement) |

**Domain pass threshold:** All 5 HARD checks pass.

---

## 10.12 Certification Matrix

The Certification Matrix summarizes the readiness requirements across all 10 domains.

| Domain | HARD Checks | SOFT Checks | HARD Required | SOFT Required | Status |
|--------|-------------|-------------|---------------|---------------|--------|
| 1 — Global Config | 7 | 3 | All 7 | 1 of 3 | [ ] |
| 2 — Environment | 8 | 2 | All 8 | Documented | [ ] |
| 3 — Engine Config | 8 | 2 | All 8 | Best effort | [ ] |
| 4 — Validation | 9 | 1 | All 9 | Documented | [ ] |
| 5 — Security | 8 | 2 | All 8 | Best effort | [ ] |
| 6 — Recovery | 8 | 2 | All 8 | Best effort | [ ] |
| 7 — Audit | 8 | 2 | All 8 | Best effort | [ ] |
| 8 — Documentation | 2 | 8 | All 2 | 5 of 8 | [ ] |
| 9 — Operational | 8 | 2 | All 8 | Best effort | [ ] |
| 10 — Archived | 5 | 5 | All 5 | Best effort | [ ] |
| **TOTAL** | **71** | **29** | **71/71** | **Majority** | |

**Certification result:** PASS (all 71 HARD checks pass) or FAIL (any HARD check fails).

**Certification signatories:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Architecture Council Lead | | | |
| Operations Lead | | | |
| Security Owner | | | |
| Compliance Officer | | | |

---

*End of Part X*

---

# SUPPLEMENT A — CONFIGURATION TAXONOMY REFERENCE

## A.1 Complete Taxonomy Table

| Code | Category | Namespace | Owner Tier | Governance | Volatility |
|------|----------|-----------|-----------|-----------|------------|
| CFG-01 | System | system.* | T1 | AC Vote | Very Low |
| CFG-02 | Engine | engines.[n].* | T2 | Owner | Low |
| CFG-03 | Workflow | workflows.[n].* | T2 | Owner | Low |
| CFG-04 | Strategy | strategies.[id].* | T2 | Owner + BT | Medium |
| CFG-05 | Model | models.[id].* | T2 | Owner + MV | Low-Med |
| CFG-06 | Portfolio | portfolio.* | T1/T2 | Mixed | Low |
| CFG-07 | Risk | isk.* | T1 | AC Unanimous | Very Low |
| CFG-08 | Learning | learning.* | T2 | Owner | Medium |
| CFG-09 | Prediction | prediction.* | T2 | Owner + BT | Low-Med |
| CFG-10 | Simulation | simulation.* | T2 | Owner | Low |
| CFG-11 | Monitoring | monitoring.* | T3 | Ops | Medium |
| CFG-12 | Logging | logging.* | T3 | Ops | Low |
| CFG-13 | Security | security.* | T1 | AC + SecRev | Very Low |
| CFG-14 | Deployment | deployment.* | T3 | Ops + T1 notif | Low-Med |
| CFG-15 | Infrastructure | infrastructure.* | T3 | Ops | Low |
| CFG-16 | Environment | environment.* | T3 | Ops | Low |
| CFG-17 | AI Agent | gents.[id].* | T2 | Owner | Medium |
| CFG-18 | User | users.[id].* | T4 | Self | High |
| CFG-19 | Feature | eatures.* | T4 | Self | High |
| CFG-20 | Experimental | experiments.[id].* | T4 | Self + T1 notif | High |
| CFG-21 | Emergency | emergency.* | T1 | T1 Single | Very Low (normal) |
| CFG-22 | Recovery | ecovery.* | T3 | Ops | Low |
| CFG-23 | Compliance | compliance.* | T1 | AC + Legal | Very Low |
| CFG-24 | Governance | governance.* | T1 | AC Vote | Very Low |

**Key:** T1=Architecture Council, T2=Engine Owner, T3=Operations, T4=Feature Owner.
BT=Backtesting evidence required, MV=Model validation required, SecRev=Security review.

---

## A.2 Constitutional Configuration Items

The following configuration items are constitutional — their lower bounds cannot be
relaxed below the defined floor, regardless of governance tier:

| Item | Namespace | Constitutional Floor | Rationale |
|------|-----------|---------------------|-----------|
| VIX kill threshold | isk.kill_switch.vix_threshold | 45 | Market panic protection |
| Daily loss limit | isk.kill_switch.daily_loss_pct | 2% of portfolio | Capital preservation |
| Strategy drawdown | isk.kill_switch.strategy_drawdown_pct | 15% | Strategy viability |
| Decision threshold | decision.threshold | 6.5 (scale 0–10) | Trade quality gate |
| OHS OPTIMAL threshold | monitoring.health.ohs_optimal | 0.95 | Health definition |
| OHS NOMINAL threshold | monitoring.health.ohs_nominal | 0.80 | Health definition |
| OHS DEGRADED threshold | monitoring.health.ohs_degraded | 0.60 | Health definition |
| OHS CRITICAL threshold | monitoring.health.ohs_critical | 0.35 | Health definition |
| Win rate gate | esearch_lab.promotion.min_win_rate | 50% | Strategy quality |
| Sharpe gate | esearch_lab.promotion.min_sharpe | 0.8 | Strategy quality |
| Drawdown gate | esearch_lab.promotion.max_drawdown_pct | 15% | Strategy quality |

---

# SUPPLEMENT B — CONFIGURATION HIERARCHY DIAGRAMS

## B.1 Full Hierarchy Precedence Diagram

`
CONFIGURATION RESOLUTION ORDER

When engine needs value for key K:

1. Check Level 12 (Emergency Override)
   |-- emergency.[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

2. Check Level 11 (Runtime)
   |-- runtime_overrides.[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

3. Check Level 10 (Session)
   |-- session.[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

4. Check Level 9 (Portfolio)
   |-- portfolio.[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

5. Check Level 8 (Model)
   |-- models.[model_id].[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

6. Check Level 7 (Strategy)
   |-- strategies.[strategy_id].[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

7. Check Level 6 (Workflow)
   |-- workflows.[workflow_id].[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

8. Check Level 5 (Engine)
   |-- engines.[engine_name].[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

9. Check Level 4 (Infrastructure)
   |-- infrastructure.[key K exists?] → USE THIS VALUE (stop)
   |-- No → continue

10. Check Level 3 (Platform)
    |-- platforms.[platform].[key K exists?] → USE THIS VALUE (stop)
    |-- No → continue

11. Check Level 2 (Environment)
    |-- environments.[env].[key K exists?] → USE THIS VALUE (stop)
    |-- No → continue

12. Check Level 1 (Global Defaults)
    |-- base.[key K exists?] → USE THIS VALUE (stop)
    |-- No → ConfigurationKeyNotFoundError
`

---

## B.2 Inheritance Flow by Configuration Category

`
RISK CONFIGURATION INHERITANCE

base.yaml
  risk.kill_switch.vix_threshold = 45        ← constitutional floor defined here
           |
           | (inherited → can only be tightened)
           v
production.yaml
  risk.kill_switch.vix_threshold = 42        ← overridden to tighter value (valid)
           |
           | (inherited → can only be tightened further)
           v
engines.risk_guardian.kill_switch.check_interval_s = 60  ← engine-level operational config
           |
           | (runtime adjustment possible within session only)
           v
session config (expiry week)
  risk.position_limits.max_open_positions = 3  ← session-level tightening
`

`
FEATURE FLAG INHERITANCE

base.yaml
  features.enable_ml_scoring = true         ← default enabled
           |
           | (environment may override)
           v
testing.yaml
  features.enable_ml_scoring = false        ← disabled in testing (use simpler path)
           |
           | (feature owner may deploy runtime override)
           v
runtime: feature_owner deploys
  features.enable_ml_scoring = true         ← re-enabled for A/B test
  (expires after 1 hour)
`

---

# SUPPLEMENT C — INHERITANCE MATRIX

## C.1 What Levels Each Configuration Category Spans

| Category | L1 Global | L2 Env | L3 Platform | L4 Infra | L5 Engine | L6 Workflow | L7 Strategy | L8 Model | L9 Portfolio | L10 Session | L11 Runtime | L12 Emergency |
|----------|-----------|--------|-------------|---------|-----------|-------------|-------------|---------|------------|------------|------------|--------------|
| System | ALWAYS | ALWAYS | Sometimes | Never | Never | Never | Never | Never | Never | Never | Never | Possible |
| Engine | ALWAYS | ALWAYS | Sometimes | Sometimes | ALWAYS | Sometimes | Never | Never | Never | Sometimes | Sometimes | Possible |
| Workflow | ALWAYS | Sometimes | Never | Never | ALWAYS | ALWAYS | Never | Never | Never | Sometimes | Sometimes | Possible |
| Strategy | ALWAYS | Sometimes | Never | Never | Sometimes | Never | ALWAYS | Never | Sometimes | Sometimes | Sometimes | Possible |
| Model | ALWAYS | Never | Never | Never | Sometimes | Never | Never | ALWAYS | Never | Never | Never | Possible |
| Portfolio | ALWAYS | ALWAYS | Never | Never | Never | Never | Never | Never | ALWAYS | Sometimes | Sometimes | Possible |
| Risk | ALWAYS | ALWAYS | Never | Never | Sometimes | Never | Never | Never | Sometimes | Sometimes | Sometimes | Possible (tighten only) |
| Emergency | Never | Never | Never | Never | Never | Never | Never | Never | Never | Never | Never | ALWAYS |

**Key:** ALWAYS = defined at this level, Sometimes = may be defined, Never = not applicable.

---

# SUPPLEMENT D — OVERRIDE MATRIX

## D.1 Who Can Override Whom

| Override Target | Tier 1 AC | Tier 2 Owner | Tier 3 Ops | Tier 4 Feature |
|----------------|-----------|-------------|-----------|----------------|
| system.* | YES | No | No | No |
| risk.* constitutional | YES (unanimous) | No | No | No |
| engines.[name].* | YES | Own engines only | No | No |
| deployment.* | YES | No | YES | No |
| features.* | YES | YES (own features) | No | YES (own features) |
| emergency.* | YES | No | No | No |
| users.[id].* | YES | No | No | YES (own account) |
| monitoring.* | YES | No | YES | No |

## D.2 Override Restrictions Matrix

| Override Type | Permitted Directions | Forbidden Directions |
|--------------|---------------------|---------------------|
| Risk limits | Only tighten (lower thresholds) | Cannot relax (raise thresholds) without T1 unanimous |
| OHS thresholds | Only adjust with T1 unanimous | Cannot be changed by any single approver |
| Emergency overrides | Any direction from authorized principal | Cannot be applied by non-T1 members |
| Session overrides | Only tighten risk | Cannot relax beyond L5 engine defaults |
| Runtime overrides | Within L5 bounds | Cannot exceed L5 engine configuration |

---

# SUPPLEMENT E — GOVERNANCE DECISION RECORDS

## E.1 Template for Governance Decision Records

Every significant governance decision about configuration is recorded in this supplement.

`
GOVERNANCE DECISION RECORD

GDR Number:    GDR-[NNN]
Date:          YYYY-MM-DD
Decision Type: Constitutional | Significant | Routine | Framework
Configuration: [namespace.key or description]

Decision:
[What was decided]

Context:
[Why this decision was needed]

Options Considered:
1. [Option A] — Pros/Cons
2. [Option B] — Pros/Cons
3. [Option C] — Pros/Cons

Chosen Option: [X]
Rationale: [Why this option was chosen]

Approvers:
- [Name] (Architecture Council): APPROVED / DENIED
- [Name] (Architecture Council): APPROVED / DENIED

Effective Date: YYYY-MM-DD
Review Date: YYYY-MM-DD (when to review this decision)

Related ADRs: [List of Architecture Decision Records if applicable]
Related Configuration Keys: [List of affected keys]
`

## E.2 Initial Governance Decision Records

**GDR-001 — Kill Switch Threshold Definitions**

| Field | Value |
|-------|-------|
| GDR Number | GDR-001 |
| Date | 2026-07-04 |
| Decision Type | Constitutional |
| Configuration | risk.kill_switch.* |

**Decision:** Establish the three kill switch conditions and their default thresholds
as constitutional configuration:
- VIX threshold: 45 (India VIX)
- Daily loss limit: 2% of portfolio
- Strategy drawdown limit: 15%

**Rationale:** These thresholds represent the conservative floor for risk management
in the IIOS system. The VIX threshold of 45 represents extreme market stress
(historical INDIA VIX during market crises has rarely exceeded 40 except during
the most severe events). The 2% daily loss limit prevents a single bad day from
causing significant capital impairment. The 15% strategy drawdown limit triggers
strategy review before a strategy can cause significant damage.

---

**GDR-002 — Decision Threshold Definition**

| Field | Value |
|-------|-------|
| GDR Number | GDR-002 |
| Date | 2026-07-04 |
| Decision Type | Constitutional |
| Configuration | decision.threshold |

**Decision:** Establish the decision score threshold of 6.5 (on a 0–10 scale) as
the minimum score required for an approved trade decision.

**Rationale:** The 5-agent debate produces a synthetic score. A threshold of 6.5
represents a position "above center" on the scale — the debate needs to produce
a positive outcome, not merely a neutral one, to approve a trade. Values below
6.5 are neutral-to-negative and should not result in a trade. The threshold
balances trade frequency (lower = more trades, higher opportunity cost) against
trade quality (lower threshold = lower quality floor).

---

# SUPPLEMENT F — CONFIGURATION ANTI-PATTERNS

## F.1 Anti-Pattern 1 — Hardcoded Constants Masquerading as Configuration

**Description:** A configuration value is documented as "configurable" but is
actually a hardcoded constant in the source code. The configuration file has the
value, but the code ignores it and uses its own hardcoded version.

**Harm:** Operators believe they can adjust behavior via configuration, but
configuration changes have no effect. This creates a dangerous false sense of control.

**Detection:** The CI pipeline includes a test that changes a configuration value
and confirms the system's behavior changes accordingly.

**Prevention:** Every configuration key must have a test that verifies: changing
the value in configuration produces the expected behavior change in the system.

---

## F.2 Anti-Pattern 2 — Configuration as Code

**Description:** Logic is embedded in configuration files. YAML files contain
conditional expressions, template variables, or script fragments. Configuration
becomes a programming language.

**Harm:** The predictability and auditability of configuration is lost. The
configuration system must now execute code, not just resolve values. Security
vulnerabilities are introduced.

**Prevention:** Configuration values are scalars, lists, or maps of scalars.
No logic, no conditionals, no expressions. If logic is needed, it belongs in code
that reads configuration, not in the configuration itself.

---

## F.3 Anti-Pattern 3 — The God Namespace

**Description:** All configuration is placed in a single namespace (e.g., pp.*)
without sub-namespacing. All 2,000 keys are at the same level.

**Harm:** Namespace isolation is impossible. Engine owners cannot be assigned
ownership of specific configuration areas. Access control becomes all-or-nothing.
Finding a relevant key requires search, not navigation.

**Prevention:** Configuration is always namespaced by category and engine as defined
in the taxonomy. Flat configuration is rejected by the Registry.

---

## F.4 Anti-Pattern 4 — The Volatile Default

**Description:** A configuration default in base.yaml is set to a value that is
only appropriate for the development environment (verbose logging, disabled risk
checks, mock data feeds). Production environments "forget" to override it.

**Harm:** When a new environment is added, or when an override is accidentally removed,
the system silently adopts the unsafe development default.

**Prevention:** Defaults are always the conservative production-appropriate value.
Development environments explicitly override to more permissive values. The validation
rule confirms that production never has development defaults.

---

## F.5 Anti-Pattern 5 — The Secret in the File

**Description:** An API token, password, or encryption key appears in a committed
configuration file. Often introduced as a "convenient default" or during debugging.

**Harm:** Credentials are permanently embedded in git history, even after removal.
All systems with repository access have been compromised.

**Prevention:** Secret scanner on every commit. .env.example documents the variable
names without values. Secrets are provided only via environment variables or secrets
manager, never via committed files.

---

## F.6 Anti-Pattern 6 — The Undead Override

**Description:** An emergency override is applied, resolves the emergency, but is
never removed. It sits in the emergency namespace indefinitely, silently overriding
production configuration.

**Harm:** Operators believe the production configuration is X, but the effective
configuration is Y (the old emergency override). System behavior is unexpectedly
different from what configuration files suggest.

**Prevention:** Emergency overrides have mandatory expiry times. The configuration
monitoring system alerts when an emergency override is approaching its expiry without
a permanent replacement in place.

---

## F.7 Anti-Pattern 7 — Configuration Drift

**Description:** Someone directly edits the configuration file on the production
server (bypassing the Configuration Manager), or sets an environment variable
without documenting it. The running configuration diverges from the committed
configuration.

**Harm:** What is committed does not reflect what is running. Reproducing an issue
or doing a forensic analysis is impossible. A new deployment restores committed
configuration, silently changing the running behavior back.

**Prevention:** Drift detection runs every 5 minutes. Any drift triggers an alert.
All changes go through the Configuration Manager. Direct server file edits are
treated as a governance incident.

---

## F.8 Anti-Pattern 8 — The Undocumented Key

**Description:** A configuration key is added to the code and the configuration file
but never registered in the Registry and never documented. It works but no one knows
what it does or who is responsible for it.

**Harm:** Operator onboarding is impaired. The key may be changed by someone who
does not understand its effect. The key is never reviewed because no one knows it exists.

**Prevention:** The CI pipeline checks that all keys consumed by code are registered
in the Registry. Unregistered consumed keys fail CI.

---

## F.9 Anti-Pattern 9 — The Cascading Dependency

**Description:** Configuration item A's valid range depends on configuration item B's
value, which depends on item C's value. The dependency chain is not documented. When
item C is changed, items A and B become invalid, but validation does not catch this
because the dependency is implicit.

**Harm:** Invalid configuration reaches production. System behavior is subtly wrong
in ways that may not be immediately detectable.

**Prevention:** All configuration dependencies are explicit: documented in the schema
and enforced by consistency validation rules.

---

## F.10 Anti-Pattern 10 — The Never-Retired Flag

**Description:** Feature flags accumulate over time. Flags for features that have
been fully released (no longer experimental) are never removed. The feature flag
registry grows to hundreds of entries.

**Harm:** The configuration system becomes harder to understand. Operator cognitive
load increases. The feature flags become a de facto second configuration layer that
is not properly governed.

**Prevention:** Feature flags have mandatory planned removal dates. The quarterly
flag cleanup review retires flags for features that have been fully released. CI
alerts when a flag has exceeded its planned removal date.

---

# SUPPLEMENT G — OPERATIONAL RUNBOOK

## G.1 Runbook 1 — Applying a Routine Configuration Change

**When to use:** Any Tier 2 or Tier 3 configuration change that does not affect
risk limits, kill switch thresholds, or constitutional values.

**Prerequisites:**
- Proposer has appropriate ownership authority.
- Change is not during a market hours blackout window.
- Change rationale is documented.

**Steps:**

1. Draft the change using the configuration draft template.
   - Document: key name, old value, new value, rationale, affected engines.

2. Run validation locally: python tools/validate_config.py --check-change [key] [new_value]
   - Confirm: PASS with no errors.

3. Submit the change request via the Configuration Manager.
   - Review queue: python tools/config_manager.py submit-change [draft_file]

4. Assign reviewers per governance tier requirements.

5. Reviewers evaluate and approve or request revision.

6. On approval, the Configuration Manager applies the change.

7. Verify the change took effect: python tools/config_manager.py get-effective-value [key]

8. Monitor for 30 minutes after activation for unexpected behavior.

9. Document the change in CHANGELOG.md.

---

## G.2 Runbook 2 — Applying an Emergency Configuration Override

**When to use:** Live trading emergency requiring immediate configuration change.
The system is behaving dangerously or incorrectly and normal governance cannot be
completed in time.

**Prerequisites:**
- Architecture Council member authorization.
- Clear understanding of what change is needed and why.

**Steps:**

1. **Immediately:** Identify the specific configuration key to change and the target value.

2. **Within 30 seconds:** Apply the emergency override:
   python tools/config_manager.py emergency-override [key] [value] --expiry [hours] --reason "[brief reason]"

3. **Within 60 seconds:** Confirm the override is active:
   python tools/config_manager.py get-effective-value [key]
   Confirm the value matches the emergency override.

4. **Within 5 minutes:** Notify all Architecture Council members:
   - What key was overridden
   - Old value and new value
   - Reason for emergency
   - Your name and timestamp

5. **While override is active:** Monitor system behavior to confirm the override
   has the intended effect.

6. **Within 48 hours:** Either:
   (a) Apply a proper governance-approved change to make the override permanent, OR
   (b) Remove the override if the emergency has resolved and the original value is appropriate.

7. **Within 48 hours:** Conduct and document the post-emergency review.

---

## G.3 Runbook 3 — Rolling Back a Configuration Change

**When to use:** A recently applied configuration change has caused unexpected
behavior and needs to be reversed.

**Steps:**

1. Identify the problematic configuration key(s) and the version to roll back to:
   python tools/config_manager.py list-versions [namespace]

2. Confirm the rollback target version has the correct value:
   python tools/config_manager.py show-version [version_id] [key]

3. Apply the rollback (requires owner or emergency authorization):
   python tools/config_manager.py rollback [version_id] [key|namespace|full]

4. Confirm the rollback was applied:
   python tools/config_manager.py get-effective-value [key]

5. Monitor system behavior to confirm the rollback resolved the issue.

6. Document the rollback in the Audit Manager (automatic) and in CHANGELOG.md.

7. Investigate the root cause of the problematic change and prevent recurrence.

---

## G.4 Runbook 4 — Recovering Configuration from Backup

**When to use:** Configuration Repository is corrupted and the system cannot load
configuration.

**Steps:**

1. Stop the IIOS system (prevent further state corruption):
   docker compose down

2. List available backups:
   python tools/config_manager.py list-backups

3. Select the most recent verified backup:
   python tools/config_manager.py show-backup [backup_id]

4. Restore from backup (to a staging location first):
   python tools/config_manager.py restore-backup [backup_id] --target /tmp/config_restore

5. Validate the restored configuration:
   python tools/validate_config.py --config-dir /tmp/config_restore

6. If validation passes, apply the restore:
   python tools/config_manager.py restore-backup [backup_id] --apply

7. Apply any changes since the backup from git history:
   git log --oneline [backup_timestamp]..HEAD -- config/
   Apply each change that occurred after the backup.

8. Restart the system:
   docker compose up -d

9. Confirm configuration loaded correctly:
   docker logs ai-trading-brain | grep "Configuration loaded"

10. Document the recovery in the Audit Manager and file a post-mortem.

---

# SUPPLEMENT H — COMPREHENSIVE GLOSSARY

**Activation:** The moment a loaded configuration value begins affecting system behavior.

**Audit Chain:** The hash-linked sequence of audit log records that provides tamper
evidence. Each record contains the hash of the previous record.

**Canonical Default:** The base.yaml definition of a configuration key's default value.
All other levels of the hierarchy override this starting point.

**Configuration Drift:** The state where running configuration differs from committed
configuration, due to direct edits, expired emergency overrides, or manual environment
variable overrides.

**Configuration Gap:** A required configuration key that has no value at any level
of the hierarchy. Causes startup failure.

**Configuration Repository:** The persistent store of all configuration state and
history. In IIOS: config/ files in git + data/databases/config.db for runtime state.

**Configuration Snapshot:** A point-in-time capture of all effective configuration
values, annotated with their hierarchy source.

**Constitutional Configuration:** Configuration items whose lower bounds are defined
as system invariants that cannot be relaxed below the constitutional floor.

**Dead Configuration:** A configuration key that is defined in configuration files
but is never read by any engine. Detected by import analysis. Removed by retirement.

**Effective Value:** The value that the Configuration Resolver returns for a key —
the result of applying all hierarchy levels in order.

**Emergency Override:** A configuration change applied outside the normal governance
process by an authorized Architecture Council member in response to an emergency.

**Feature Flag:** A boolean configuration item that enables or disables a system
capability. Managed under eatures.* namespace.

**Governance Tier:** One of four authorization levels (Architecture Council, Engine
Owner, Operations, Feature Owner) that determines who can approve configuration
changes in a given namespace.

**Hierarchy Level:** One of the 12 levels in the IIOS configuration hierarchy, each
with a defined precedence. Higher levels override lower levels.

**Inheritance:** The mechanism by which configuration values defined at a higher
hierarchy level provide defaults for lower levels.

**Key Retirement:** The formal process of removing a configuration key from the active
Registry, preceded by a deprecation period.

**Last Known Good Configuration:** The most recently loaded valid configuration state
that is retained in memory for use if the configuration system becomes unavailable.

**Namespace:** A dot-separated prefix in a configuration key name that identifies the
category and sub-category. Example: isk.kill_switch.*.

**Orphaned Key:** A configuration key present in a configuration file but not
registered in the Registry. Treated as an unknown key.

**Override:** A configuration value at a lower hierarchy level that replaces the
default from a higher level.

**Policy:** A high-level system rule that configuration implements. A policy defines
what the system does; configuration governs how aggressively it does it.

**Registry:** The in-memory catalog of all registered configuration keys with their
metadata (type, range, owner, description).

**Resolution Trace:** The output of the Resolver's 	race() function, showing
which hierarchy level provided the effective value for a given key.

**Schema Version:** The version of the configuration schema definition. Increments
when the structure of configuration changes (new required keys, type changes).

**Secret:** A configuration value containing credentials, tokens, or keys that must
never appear in logs, displays, or committed files.

**Sensitivity Classification:** The security classification of a configuration item:
Public, Internal, Confidential, or Secret.

**Value Version:** The version of the configuration values for a given schema.
Increments whenever values are changed within a schema version.

**Volatile Configuration:** Configuration that changes frequently. Volatile configuration
is placed at the appropriate hierarchy level to minimize the impact of each change.

---

## DOCUMENT METRICS

| Metric | Value |
|--------|-------|
| Document Code | IIOS-CFG-FWK-001 |
| Version | 1.0.0 |
| Status | AUTHORITATIVE |
| Parts | 10 (I through X) |
| Supplements | 8 (A through H) |
| Configuration categories | 24 |
| Hierarchy levels | 12 |
| Constitutional rules | 110 [HARD/SOFT/ADVISORY] |
| Readiness checks | 100 [71 HARD, 29 SOFT] |
| Anti-patterns | 10 |
| Runbooks | 4 |
| Glossary entries | 35+ |

---

## AMENDMENT HISTORY

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-07-04 | Initial release | Architecture Council |

---

*IIOS-CFG-FWK-001 Version 1.0.0*
*Investment Intelligence Operating System — Configuration Framework*
*Architecture Council — 2026-07-04*
*Status: AUTHORITATIVE*
*End of Document.*