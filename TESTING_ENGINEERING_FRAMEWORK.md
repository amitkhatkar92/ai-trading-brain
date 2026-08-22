# TESTING ENGINEERING FRAMEWORK
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-TST-ENG-001
**Version:** 1.0.0
**Status:** Active
**Classification:** Architecture Reference — Engineering Specification
**Scope:** All IIOS engines, agents, workflows, integrations, databases, and infrastructure

---

## Document Purpose

This document defines the complete Testing Engineering Framework for the Investment
Intelligence Operating System (IIOS). It specifies how every component, module,
service, pipeline, AI agent, ontology, reasoning engine, decision engine, database,
workflow, and integration will be verified before deployment and monitored continuously
in production.

This is a pure engineering architecture specification. It defines structure, processes,
policies, measurements, and governance. It does not define source code, implementation
language, or tool-specific configuration.

---

## Scope

This framework governs testing of:
- All 18 IIOS engines (GlobalIntelligence through ControlTower).
- All AI debate agents (5 agents in the Debate and Decision engine).
- All strategy evolution pipelines and evolved strategies.
- All data feed integrations (primary: Dhan; fallback: yfinance).
- All broker integrations (paper trading and live trading paths).
- All shared utilities (57 categories, IIOS-SUT-FWK-001).
- All configuration management components.
- All logging, monitoring, and observability infrastructure.
- All databases (SQLite telemetry, paper trades journal, strategy records).
- All scheduled and event-driven workflows.
- All risk and safety mechanisms (kill switch, circuit breakers).

---

## Table of Contents

- Part I: Testing Philosophy (14 sections)
- Part II: Complete Testing Taxonomy (47 categories)
- Part III: Testing Architecture (18 components)
- Part IV: Testing Lifecycle (12 stages)
- Part V: Test Data Framework (13 dataset types)
- Part VI: Coverage Framework (15 dimensions)
- Part VII: Quality Metrics (12 metric categories)
- Part VIII: Testing Governance
- Part IX: Engineering Constitution (110 rules)
- Part X: Readiness Checklist (9 domains)
- Supplement A: Testing Catalog Reference
- Supplement B: Coverage Matrix
- Supplement C: Dataset Catalog
- Supplement D: Certification Matrix
- Supplement E: Failure Taxonomy
- Supplement F: Quality Score Reference
- Supplement G: Testing Anti-Patterns
- Supplement H: Operational Runbook
- Supplement I: Comprehensive Glossary

---

# PART I — TESTING PHILOSOPHY

## 1.1 Purpose of Testing

Testing is the systematic process of verifying that a system does what it is
designed to do, under the conditions it is designed to operate in, and that it
continues to do so as it evolves. In a system that manages real capital in live
markets, testing is not a quality nicety — it is an operational safety requirement.

An IIOS component that has not been tested to a defined standard is an unverified
component. Deploying an unverified component to production creates an unknown,
unbounded risk. The Testing Engineering Framework replaces unknown risk with
measured, bounded, documented risk.

The purposes of testing in IIOS are:
- **Safety verification:** Confirm that safety mechanisms (kill switches, circuit
  breakers, position limits, risk guards) work exactly as specified.
- **Correctness verification:** Confirm that all components produce correct outputs
  for all defined inputs.
- **Integration verification:** Confirm that components work correctly together,
  including under failure and degradation conditions.
- **Regression prevention:** Confirm that changes to one component do not break
  other components.
- **Deployment confidence:** Provide a documented, evidence-based basis for the
  decision to deploy to production.

---

## 1.2 Engineering Quality

Engineering quality is not a single dimension. For IIOS, quality has seven aspects
that testing must address:

**Functional correctness:** The component produces the expected output for every
valid input within its documented contract.

**Safety:** The component's failure modes are known, bounded, and handled. Safety
mechanisms are tested explicitly and at the boundaries they are designed to enforce.

**Performance:** The component meets its latency and throughput requirements under
expected and peak load conditions.

**Reliability:** The component behaves consistently over time and across restarts.
It does not accumulate errors, leak resources, or produce degrading output over time.

**Security:** The component does not introduce exploitable vulnerabilities. It
correctly validates its inputs and does not expose sensitive data.

**Resilience:** The component responds correctly to failures of its dependencies.
It degrades gracefully and recovers automatically where specified.

**Observability:** The component produces the log events, metrics, and health
signals needed to understand its runtime behavior.

All seven quality aspects are addressed by the IIOS Testing Engineering Framework.
A component that passes only some of them is not ready for production.

---

## 1.3 Verification vs Validation

These two concepts are sometimes conflated but represent distinct activities:

**Verification:** "Are we building the component right?" Verification checks that
the implementation conforms to its specification. Unit tests, component tests,
and contract tests are verification activities. They answer: does the code match
what was designed?

**Validation:** "Are we building the right component?" Validation checks that the
specification meets the actual need. Acceptance tests, backtesting validation, and
user acceptance tests are validation activities. They answer: does the design meet
what the system actually needs?

Both are required. A component that is perfectly built to a wrong specification
is not acceptable. A component that is intended to be right but built incorrectly
is not acceptable.

In IIOS:
- **Verification** is primarily performed by the engineering team through automated
  tests, code reviews, and static analysis.
- **Validation** is primarily performed by the trading strategy team through
  backtesting, simulation, and operational observation.

---

## 1.4 Correctness

Correctness is the foundational quality property. A component is correct if it
produces the right output for every input within its documented contract.

**Correctness dimensions for IIOS:**

**Arithmetic correctness:** Financial calculations (P&L, Sharpe ratio, drawdown,
returns) must produce results that are accurate to the defined precision. A strategy
that appears profitable due to a rounding error is not actually profitable.

**Logical correctness:** Decision logic (which trade to approve, which risk check
to apply, which strategy to activate) must produce the expected decision for all
defined inputs.

**State correctness:** Stateful components (position manager, order manager, learning
engine) must maintain correct state across operations, restarts, and failure events.

**Temporal correctness:** Time-dependent logic (market session checks, expiry
calculations, scheduled tasks) must produce correct results for all relevant
times and dates.

**Boundary correctness:** The behavior at boundary conditions (maximum position,
zero price, first trade of day, first day of month) must match the specification.

---

## 1.5 Reliability

Reliability is the probability that a component produces correct results over time.
A component that is correct on Monday but produces wrong results on Friday is not
reliable.

**Reliability threats in IIOS:**

**Memory accumulation:** Components that accumulate state (caches, histories, queues)
may produce different results after 100 hours of operation than after 1 hour. Tests
must include long-run scenarios.

**Calendar edge cases:** Components that behave differently on the last day of the
month, on expiry Fridays, on market holidays, must be tested for exactly those dates.

**Data feed variability:** The output quality of IIOS decisions depends on data
quality. Tests must include scenarios with degraded data feed quality to ensure
reliable behavior under those conditions.

**Concurrency:** Components accessed from multiple threads may exhibit race conditions
that only appear occasionally. Reliability tests include concurrent access scenarios.

---

## 1.6 Determinism

A deterministic component produces the same output for the same input, every time,
regardless of execution order, timing, or external state.

**Why determinism matters for IIOS:**

**Debugging:** A non-deterministic defect is extremely difficult to reproduce and
diagnose. Deterministic components are far easier to debug.

**Testing:** A non-deterministic component cannot be reliably tested. Tests that
sometimes pass and sometimes fail (flaky tests) provide no confidence.

**Reproducibility:** The ability to replay a historical scenario and obtain the
same result is essential for strategy validation and regulatory audit. This requires
deterministic components.

**AI and ML components:** AI components trained on random processes must be testable
with deterministic inputs. Seeded random number generators and frozen model states
enable deterministic testing of AI components.

**Determinism engineering rules for IIOS:**
- All random operations use the Randomization Utility with injectable seeds.
- Time-dependent behavior uses the injectable clock from the Date-Time Utility.
- Tests freeze all non-deterministic inputs before execution.

---

## 1.7 Repeatability

Repeatability is the ability to run the same test multiple times and obtain the
same result. Repeatability requires determinism plus isolation — the test must not
be affected by the results of previous tests.

**Repeatability engineering requirements:**
- Every test starts from a known, clean state.
- Tests do not share mutable state.
- Tests do not depend on execution order.
- Tests clean up all persistent state (files, database records) after execution.
- Test environments are reset between test suites.
- Flaky tests (tests that pass sometimes and fail sometimes) are treated as defects.

**Repeatability monitoring:** The test infrastructure tracks the pass/fail history
of every test. A test that fails more than once in 10 consecutive executions without
a code change is flagged as potentially flaky.

---

## 1.8 Regression Prevention

A regression is a change in behavior — typically a defect introduced by a code
change — that causes a previously passing test to fail. Regression prevention
is one of the highest-value activities of a testing framework.

**IIOS regression prevention mechanisms:**

**Regression test suite:** Every defect that is discovered and fixed must have a
test that would have caught it before the fix. This test becomes a permanent part
of the regression test suite.

**Golden dataset tests:** Tests that compare current output to a previously validated
("golden") output. Any change in output is flagged for review.

**Strategy regression tests:** When a change is made to any engine that could affect
trading decisions, the full historical decision log is replayed and any difference
in decisions is flagged.

**Performance regression tests:** Latency and throughput benchmarks that run with
every deployment. Any regression (p99 latency increases > 20%) is a blocking failure.

---

## 1.9 Risk Reduction

Testing reduces risk. Not testing increases risk. The IIOS Testing Engineering
Framework quantifies the risk reduction provided by testing and ensures that the
highest-risk components receive the most testing attention.

**Risk-stratified testing approach:**

**Critical path components** (those involved in every trading decision) receive
the most comprehensive testing. These include the Decision Engine, Risk Guardian,
Order Manager, and data feed pipeline.

**Safety mechanisms** (kill switch, circuit breakers, position limits) are tested
exhaustively, including adversarial conditions. A safety mechanism that fails at
the exact moment it is needed is worse than no safety mechanism.

**Edge case scenarios** are explicitly identified and tested. The scenarios where
a system is most likely to fail are the scenarios that must be tested most rigorously.

**Risk score for components:** Every IIOS component has a Risk Score (0–10) based
on: financial impact of failure, frequency of use, number of dependencies, and
complexity. Testing depth is proportional to Risk Score.

---

## 1.10 Automation-First Philosophy

Manual testing is not scalable, not repeatable, and not fast enough for IIOS.
The IIOS Testing Engineering Framework adopts an automation-first philosophy:

**Every test that can be automated must be automated.** If a test can be expressed
as a deterministic input-output relationship, it must be automated.

**Manual testing is reserved for exploratory testing and UX validation.** Human
judgment adds value in areas where the expected outcome cannot be fully specified
in advance.

**CI/CD pipeline integration:** Automated tests run on every commit. No change
reaches production without passing the full automated test suite.

**Test maintenance as first-class work:** Writing and maintaining automated tests
is treated as production engineering work, not an optional extra. Test code is
reviewed, version-controlled, and maintained to the same standard as production code.

---

## 1.11 Continuous Quality Assurance

Quality is not assessed at a single point in time (before deployment). Quality is
monitored continuously throughout the IIOS operational lifecycle.

**Continuous quality assurance mechanisms:**

**Production health monitoring:** OHS (Operational Health Score) monitors every
engine in production. A declining OHS triggers investigation before it becomes
a failure.

**Continuous regression detection:** Live trading decisions are compared against
historical patterns. Unexpected divergences trigger review.

**Data quality monitoring:** Data feed output is continuously monitored for
staleness, invalid values, and anomalies.

**Strategy performance monitoring:** Strategy win rates, drawdowns, and Sharpe
ratios are tracked continuously. Declining performance triggers the strategy
governance review process.

**Audit log integrity monitoring:** The audit chain hash is continuously verified.
Any break in the chain triggers immediate investigation.

---

## 1.12 Confidence Engineering

The ultimate purpose of testing is to produce confidence — a quantified, evidence-based
belief that the system will behave correctly in production. Confidence engineering
replaces "I think it works" with "here is the evidence that it works."

**Confidence dimensions:**

**Functional confidence:** Test coverage + defect density provides confidence that
the component implements its specification correctly.

**Performance confidence:** Benchmark results provide confidence that latency and
throughput targets will be met in production.

**Safety confidence:** Adversarial test results provide confidence that safety
mechanisms will work under realistic failure conditions.

**Resilience confidence:** Failure injection test results provide confidence that
the system will recover correctly from dependency failures.

**Certification matrix:** For each IIOS component, the certification matrix shows
which confidence dimensions have been verified and at what level. A component
cannot be certified for production until all required confidence dimensions
show PASS.

---

## 1.13 Investment System Safety

IIOS manages real capital in live markets. This context imposes safety requirements
on the testing framework that do not apply in typical software systems.

**Safety testing priorities for investment systems:**

**Kill switch verification:** The most important safety test in IIOS. The kill switch
must activate reliably under its trigger conditions (VIX > 45, daily loss > 2%)
even when other components are failing. This is tested exhaustively, including
under adverse concurrent conditions.

**Order uniqueness verification:** Duplicate orders can result in double positions.
The order idempotency mechanism must be tested for all failure scenarios where
retry might occur.

**Position reconciliation verification:** Position counts in IIOS must match
broker positions. Any reconciliation failure must be detected and alerted.

**Risk limit enforcement:** All risk limits (maximum position size, maximum daily
exposure, maximum drawdown) must be tested at their exact boundaries.

**Recovery correctness:** After any failure and restart, the system must correctly
reconstruct its state from persistent records without double-counting or omitting
trades.

---

## 1.14 Testing Maturity Model

The IIOS Testing Maturity Model (TMM) defines five levels of testing maturity
for individual components and for the platform as a whole:

**TMM Level 1 — Initial:**
- No automated tests.
- Testing is ad-hoc, manual, and unpredictable.
- No test documentation.

**TMM Level 2 — Managed:**
- Basic unit tests exist.
- Tests are in version control.
- Tests run on CI.

**TMM Level 3 — Defined:**
- Comprehensive unit and integration tests.
- Coverage > 80%.
- Testing process is defined and followed.
- Test results are tracked.

**TMM Level 4 — Measured:**
- Full test coverage across all categories.
- Coverage > 95%.
- Quality metrics are tracked.
- Regression suite is maintained.
- Performance benchmarks run continuously.

**TMM Level 5 — Optimizing:**
- All TMM Level 4 requirements.
- Property-based and mutation testing.
- Continuous quality improvement process.
- Testing drives development (test-first approach).
- Chaos testing and failure injection in production.

**IIOS TMM target:** All PRODUCTION-certified components must be at TMM Level 4.
Critical path and safety components must be at TMM Level 5.

---

*End of Part I*

---

# PART II — COMPLETE TESTING TAXONOMY

## 2.1 Taxonomy Overview

The IIOS Testing Taxonomy defines 47 testing categories organized into 8 functional
groups. Each category addresses a distinct testing concern. Together they provide
comprehensive coverage of the full IIOS system.

---

## 2.2 Group 1 — Structural Testing

### Category 1 — Unit Testing

**Definition:** Testing individual functions or methods in complete isolation from
all external dependencies.

**Purpose in IIOS:** Verify that individual functions in every IIOS engine produce
the correct output for all inputs within their documented contract.

**Scope:** Every public function in every IIOS module.

**Characteristics:**
- Fastest test category (milliseconds per test).
- All dependencies mocked or stubbed.
- Deterministic (no I/O, no time dependency, no network).
- Test isolation: each test function is independent.

**Coverage requirement:** > 95% line, branch, and condition coverage.

**IIOS-specific considerations:**
- Financial calculation functions must include tests for precision edge cases.
- Strategy signal functions must include tests for all defined market regimes.
- Risk check functions must include tests for all defined risk limit boundaries.

---

### Category 2 — Component Testing

**Definition:** Testing a complete component (class or module) including the
interaction between its internal functions, but with all external dependencies
mocked.

**Purpose in IIOS:** Verify that each IIOS engine's internal logic is correct
as a whole, not just function by function.

**Scope:** Each of the 18 IIOS engines as a complete unit.

**Characteristics:**
- Faster than integration tests (seconds per test).
- External dependencies (data feeds, broker API, database) are mocked.
- Internal interactions between functions within the component are exercised.

**IIOS-specific considerations:**
- The debate engine component tests must verify multi-agent deliberation logic.
- The risk guardian component tests must verify all kill switch trigger conditions.
- The order manager component tests must verify idempotency logic.

---

### Category 3 — Module Testing

**Definition:** Testing a complete functional module — a group of related
components that together implement a subsystem capability.

**Purpose in IIOS:** Verify that related components work correctly together
before testing full-system integration.

**Scope:** Each of the 17 IIOS architectural layers as a functional module.

**Characteristics:**
- Some dependencies are real (within the module), some are mocked (outside the module).
- Exercises the complete public interface of the module.

---

### Category 4 — Subsystem Testing

**Definition:** Testing a vertical slice of the system that spans multiple layers.

**Purpose in IIOS:** Verify that specific end-to-end capabilities work correctly.

**Scope examples:**
- The complete data-to-decision pipeline (data feed → market intelligence → decision engine).
- The complete risk management pipeline (position → risk check → risk guardian → order).
- The complete learning pipeline (trade result → performance tracker → strategy update).

---

### Category 5 — System Testing

**Definition:** Testing the complete IIOS system end-to-end with all real components
(no mocks), in a production-equivalent environment.

**Purpose in IIOS:** Verify that the complete IIOS system, as it will be deployed
to production, behaves correctly in all defined scenarios.

**Scope:** The complete 17-layer IIOS system from GlobalIntelligence to ControlTower.

**Characteristics:**
- Slowest test category (minutes to hours per test run).
- Uses real databases, real containers, production-equivalent configuration.
- Uses historical market data replayed at the same rate as live data.
- Requires a production-equivalent test environment.

---

## 2.3 Group 2 — Integration Testing

### Category 6 — Integration Testing

**Definition:** Testing the interactions between two or more components.

**Purpose in IIOS:** Verify that components communicate correctly, data formats
are compatible, and error conditions are handled correctly at integration boundaries.

**Scope:** Every integration point between IIOS components (all message passing,
function calls across module boundaries, database interactions, API calls).

**Characteristics:**
- Real implementations of both sides of each integration.
- Exercises the full request-response cycle including error paths.

---

### Category 7 — Interface Testing

**Definition:** Testing that a component's interface (the contract it offers to
its callers) is correctly implemented.

**Purpose in IIOS:** Verify that published interfaces (function signatures, return
types, exception types) match their specification and are stable.

**IIOS critical interfaces:**
- GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot
- MasterOrchestrator.run_full_cycle() -> None
- BaseFeed.get_quote(symbol: str) -> Optional[TickerQuote]
- BaseFeed.get_history(symbol, days, interval) -> List[PriceBar]
- SystemMonitor.time_layer(layer_name: str) -> contextmanager

These interfaces are tested for signature stability with every commit.

---

### Category 8 — Contract Testing

**Definition:** Testing that the contract between a producer and consumer is honored
by both parties.

**Purpose in IIOS:** Verify that data producers (e.g., data feeds) produce data
in the format that consumers (e.g., market intelligence engine) expect.

**Contract testing scope:**
- Data feed output format (TickerQuote, PriceBar) vs market intelligence input expectations.
- Decision engine output format vs order manager input expectations.
- Strategy output format vs backtesting validation input expectations.
- Telegram bot command format vs notification system input expectations.

---

### Category 9 — Repository Testing

**Definition:** Testing the data persistence layer — the code that reads and
writes to databases.

**Purpose in IIOS:** Verify that all SQLite database operations (read, write,
update, delete, query) produce correct results.

**IIOS databases:**
- SQLite telemetry database (ControlTower).
- Paper trades journal (order_manager).
- Strategy performance records (learning system).
- Evolved strategy definitions (strategy_lab/evolved_strategies).

**Repository test scope:** Every read and write operation, transaction handling,
schema compliance, index usage, query correctness.

---

### Category 10 — Configuration Testing

**Definition:** Testing that the system correctly loads, validates, and applies
configuration.

**Purpose in IIOS:** Verify that every configuration key is correctly loaded from
config.py and YAML files, that defaults are applied when values are absent,
and that invalid configurations produce clear errors.

**IIOS-specific:** Configuration testing must include:
- All 12 schedule slots defined in the SCHEDULE configuration.
- The CONTINUOUS_SCAN_INTERVAL setting.
- All API keys and token references.
- All per-strategy parameter configurations.

---

## 2.4 Group 3 — Data Testing

### Category 11 — Database Testing

**Definition:** Testing the database itself: schema correctness, query performance,
index behavior, and transactional integrity.

**Purpose in IIOS:** Verify that the SQLite databases used by IIOS perform
correctly and maintain integrity under normal and concurrent access conditions.

**Database test scope:**
- Schema validation (all tables and columns match specification).
- Index coverage (all queries use appropriate indexes).
- Transaction correctness (concurrent writes do not corrupt data).
- Database size management (old records are archived or pruned correctly).

---

### Category 12 — Schema Testing

**Definition:** Testing that data structures (database schemas, serialized formats,
configuration schemas) conform to their specification.

**Purpose in IIOS:** Prevent schema drift — the gradual divergence between the
documented schema and the actual schema in production.

**Schema test scope:**
- Database table schemas.
- Configuration YAML schema.
- API response schemas (data feed responses, broker API responses).
- Serialized strategy format (evolved strategy JSON).

---

### Category 13 — Migration Testing

**Definition:** Testing that data migrations (database schema changes, configuration
format changes) execute correctly and produce the expected result.

**Purpose in IIOS:** Ensure that upgrades do not corrupt or lose existing data.

**Migration test requirements:**
- Test on a copy of production data before applying to production.
- Verify row counts before and after migration.
- Verify data integrity of migrated records.
- Verify rollback (the migration can be undone if needed).

---

### Category 14 — Data Integrity Testing

**Definition:** Testing that data remains consistent and correct through storage,
retrieval, and processing operations.

**Purpose in IIOS:** Verify that data is not corrupted, silently truncated, or
incorrectly transformed during storage or retrieval.

**IIOS-specific scope:**
- Paper trades journal integrity (P&L calculations from journal are consistent).
- Audit log chain integrity (hash chain is unbroken).
- Strategy performance record integrity (win rates and Sharpe ratios compute
  correctly from the raw records).
- Position record integrity (position counts and values are consistent).

---

### Category 15 — Ontology Testing

**Definition:** Testing the correctness and consistency of domain ontologies —
the structured representations of domain knowledge used by AI agents.

**Purpose in IIOS:** Verify that the ontological structures used by the AI debate
agents accurately represent the market domain and are internally consistent.

**Ontology test scope:**
- Concept hierarchy correctness.
- Relationship consistency (no contradictory relationships).
- Coverage completeness (all relevant market concepts are represented).
- Ontology evolution (new concepts integrate correctly with existing structure).

---

### Category 16 — Knowledge Testing

**Definition:** Testing the content and quality of knowledge bases used by IIOS
learning and decision components.

**Purpose in IIOS:** Verify that the knowledge accumulated by the Learning Engine
and Knowledge Base is correct, relevant, and properly structured.

**Knowledge test scope:**
- Knowledge entry format compliance.
- Knowledge-to-evidence linkage (every knowledge entry is supported by evidence).
- Knowledge consistency (no contradictory entries).
- Knowledge retrieval correctness (queries return the expected entries).

---

### Category 17 — Relationship Testing

**Definition:** Testing the correctness of relationships between entities in IIOS
data stores and knowledge structures.

**Purpose in IIOS:** Verify that entity relationships (strategy-to-trade,
trade-to-cycle, signal-to-regime, knowledge-to-incident) are correctly maintained.

**Relationship test scope:**
- Referential integrity in databases.
- Knowledge graph relationship correctness.
- Dependency relationship accuracy.
- Time-ordered relationship correctness.

---

## 2.5 Group 4 — Behavioral Testing

### Category 18 — Observation Testing

**Definition:** Testing that the observability outputs of IIOS components —
log events, metrics, health checks, traces — are correctly produced.

**Purpose in IIOS:** Verify that every component produces the monitoring signals
needed to detect failures and diagnose issues in production.

**Observation test scope:**
- Log event correctness (right fields, right levels, right formats).
- Metric completeness (all defined metrics are published).
- Health check responsiveness.
- Trace span correctness.

---

### Category 19 — Event Testing

**Definition:** Testing that IIOS components correctly produce and consume events
through the Event Bus.

**Purpose in IIOS:** Verify that event-driven communication between IIOS components
is correct.

**Event test scope:**
- Event payload format compliance.
- Event ordering guarantees.
- Event delivery reliability.
- Event handler idempotency (handling the same event twice produces the same result).
- Event fan-out (all subscribers receive events when expected).

---

### Category 20 — Decision Testing

**Definition:** Testing the correctness of all decision-making components in IIOS.

**Purpose in IIOS:** Verify that the Decision Engine, MetaLearning engine, and
individual debate agents produce the expected decisions for defined inputs.

**Decision test scope:**
- Debate agent scoring for defined market conditions.
- DecisionEngine threshold logic (score threshold 6.5 for approval).
- MetaLearning strategy weight computation for each market regime.
- Strategy selection logic for defined regime/score combinations.
- Kill switch decision logic.

**Golden dataset testing:** A set of historical scenarios with known correct
decisions. The Decision Engine must produce the same decisions on replay.

---

### Category 21 — Reasoning Testing

**Definition:** Testing the reasoning chains produced by AI reasoning components.

**Purpose in IIOS:** Verify that AI agents produce coherent, logically consistent
reasoning chains that correctly justify their conclusions.

**Reasoning test scope:**
- Reasoning chain completeness (all relevant factors considered).
- Reasoning chain consistency (conclusions follow from premises).
- Regime classification correctness.
- Signal interpretation consistency.

---

### Category 22 — Learning Testing

**Definition:** Testing the learning mechanisms in IIOS — verifying that the
system correctly improves its behavior based on historical experience.

**Purpose in IIOS:** Verify that the Learning Engine and MetaLearning components
correctly update strategy weights and preferences based on trading results.

**Learning test scope:**
- Win rate computation correctness.
- Strategy weight update logic.
- Regime-strategy mapping update correctness.
- Auto-disable logic (strategy disabled at the governance threshold).
- Learning persistence (learned state survives restart).

---

### Category 23 — AI Agent Testing

**Definition:** Testing the behavior of individual AI agents in the IIOS debate
system.

**Purpose in IIOS:** Verify that each AI agent in the 5-agent debate system
produces correct scores and rationales for defined market scenarios.

**Agent test scope (for each of the 5 debate agents):**
- Score range compliance (scores within defined bounds).
- Score direction correctness (higher confidence = higher score for bullish; lower for bearish).
- Rationale completeness.
- Behavior under data quality degradation.
- Behavior under market stress conditions.

---

### Category 24 — Prompt Testing

**Definition:** Testing prompt templates and prompting strategies used by AI
components.

**Purpose in IIOS:** Verify that prompts produce the expected outputs and do not
introduce hallucination, format violations, or dangerous reasoning patterns.

**Prompt test scope:**
- Format compliance (structured output matches expected schema).
- Hallucination detection (outputs reference only provided information).
- Edge case prompts (empty data, extreme values, contradictory signals).
- Consistency testing (same prompt produced consistently).

---

### Category 25 — LLM Evaluation

**Definition:** Testing the quality of language model outputs used in IIOS reasoning.

**Purpose in IIOS:** Verify that LLM outputs meet the quality and safety standards
required for use in financial decisions.

**LLM evaluation scope:**
- Output coherence scoring.
- Factual grounding assessment.
- Safety filtering verification.
- Confidence calibration (stated confidence vs actual accuracy).
- Latency compliance.

---

## 2.6 Group 5 — Strategy and Financial Testing

### Category 26 — Backtesting Validation

**Definition:** Testing the backtesting engine itself — verifying that it correctly
simulates historical strategy performance.

**Purpose in IIOS:** Verify that the backtesting results used to promote strategies
are accurate and free from look-ahead bias, survivorship bias, and computational errors.

**Backtesting validation scope:**
- Look-ahead bias detection (strategy uses only data available at the time of decision).
- Slippage modeling accuracy.
- Transaction cost accuracy.
- Split and dividend adjustment correctness.
- Performance metric computation accuracy (Sharpe ratio, drawdown, win rate).
- Walk-forward testing correctness.

---

### Category 27 — Simulation Testing

**Definition:** Testing the Monte Carlo simulation engine and its output quality.

**Purpose in IIOS:** Verify that the Market Simulation engine (14 scenarios)
produces statistically valid, non-biased simulation outcomes.

**Simulation test scope:**
- Scenario coverage completeness.
- Statistical distribution correctness.
- Simulation reproducibility (seeded runs produce identical results).
- Extreme scenario correctness (crash and bubble scenarios).
- Simulation-to-outcome calibration (historical scenarios match historical outcomes).

---

### Category 28 — Historical Replay Testing

**Definition:** Testing the ability to replay historical market data through the
IIOS decision pipeline and reproduce historical decisions.

**Purpose in IIOS:** Enable regression detection (any change in behavior between
historical and current runs is flagged), and validate that the system would have
made the same decisions in the past.

**Replay test scope:**
- Data feed replay fidelity.
- Timestamp precision in replay.
- Decision reproduction accuracy.
- Performance during replay (real-time replay must complete in real time).

---

### Category 29 — Strategy Testing

**Definition:** Testing individual trading strategies — their signal generation,
parameter sensitivity, and performance characteristics.

**Purpose in IIOS:** Verify that each strategy in the evolved strategy library
produces correct signals and meets its promotion criteria.

**Strategy test scope:**
- Signal generation correctness.
- Parameter boundary behavior.
- Regime compatibility (strategy produces valid signals in its supported regimes).
- Promotion criteria verification (win rate >= 50%, Sharpe > 0.8, max drawdown < 15%).
- Strategy deactivation logic.

---

## 2.7 Group 6 — Performance Testing

### Category 30 — Performance Testing

**Definition:** Testing that all IIOS components meet their latency and throughput
requirements under normal operating conditions.

**Purpose in IIOS:** Verify that the performance baseline is maintained across
all components and that no change introduces a performance regression.

**Performance test scope:**
- Per-engine latency measurement.
- Full cycle latency (target: < 200ms).
- Per-layer latency thresholds:
  - Default WARN: 2,000ms; CRIT: 5,000ms.
  - GlobalIntelligence WARN: 5,000ms; CRIT: 12,000ms.
- Throughput at rated load.
- Cache efficiency.

---

### Category 31 — Load Testing

**Definition:** Testing system behavior under expected sustained load.

**Purpose in IIOS:** Verify that IIOS can process the expected number of trading
cycles per day without degradation.

**Load test scope:**
- Sustained operation for a full trading day (6.25 hours, 09:15–15:30 IST).
- Continuous scan mode at 30-second intervals.
- Telemetry database growth rate.
- Memory usage trend over full-day operation.

---

### Category 32 — Stress Testing

**Definition:** Testing system behavior at and beyond maximum rated load.

**Purpose in IIOS:** Verify that the system fails gracefully (not catastrophically)
when capacity is exceeded.

**Stress test scope:**
- 2x rated cycle frequency.
- 10x data feed event rate.
- Maximum concurrent data feed requests.
- Maximum simultaneous strategy evaluations.

---

### Category 33 — Scalability Testing

**Definition:** Testing that the system can be scaled to handle increased load
without architectural changes.

**Purpose in IIOS:** Verify that IIOS can be scaled by configuration (more
resources, more containers) without code changes.

---

### Category 34 — Concurrency Testing

**Definition:** Testing that components behave correctly when accessed concurrently
from multiple threads.

**Purpose in IIOS:** Verify that thread-safe components produce correct results
under concurrent access and that non-thread-safe components are not accessed
concurrently.

**Concurrency test scope:**
- Order manager concurrent access (prevent duplicate order creation).
- Position manager concurrent access (prevent incorrect position counts).
- Data feed cache concurrent access.
- SQLite database concurrent writes (SQLite serialization verification).

---

### Category 35 — Thread Safety Testing

**Definition:** Testing specifically for thread safety violations: data races,
deadlocks, and atomicity violations.

**Purpose in IIOS:** Systematically detect thread safety defects that would be
non-deterministic in production.

**Thread safety test approach:**
- Run all shared-state access under concurrent load with 10+ threads.
- Use thread sanitizer tooling.
- Detect lock ordering violations (potential deadlocks).
- Detect unsynchronized read-write races on shared variables.

---

### Category 36 — Memory Testing

**Definition:** Testing for memory leaks, excessive memory usage, and memory
corruption.

**Purpose in IIOS:** Verify that IIOS does not accumulate memory over time, which
would cause eventual OOM failures in production.

**Memory test scope:**
- Memory usage at start of trading day.
- Memory usage at end of trading day.
- Memory growth rate (allowable: < 10 MB/hour).
- Cache size compliance (caches remain within configured limits).
- Large data structure cleanup (historical data lists are pruned as designed).

---

### Category 37 — Latency Testing

**Definition:** Detailed measurement and testing of latency for every component
on the critical trading path.

**Purpose in IIOS:** Verify that per-component latency targets are met and that
the full cycle latency budget is not exceeded.

**Current baselines (must not regress):**
- GlobalIntelligence: 17ms.
- MarketIntelligence: 19ms.
- Full cycle: 172ms.

---

## 2.8 Group 7 — Safety and Security Testing

### Category 38 — Security Testing

**Definition:** Testing for security vulnerabilities in all IIOS components.

**Purpose in IIOS:** Verify that IIOS does not expose exploitable vulnerabilities
that could lead to unauthorized access, data theft, or manipulation of trading
decisions.

**Security test scope:**
- Static application security testing (SAST) on all code.
- Dependency vulnerability scanning.
- Configuration security review (no exposed secrets).
- Input validation testing (all external inputs are validated).
- Audit log integrity.
- Authentication security.

---

### Category 39 — Authentication Testing

**Definition:** Testing all authentication mechanisms used by IIOS.

**Purpose in IIOS:** Verify that authentication to the Dhan broker API, Telegram
bot, and any other authenticated service is correctly implemented and that
credential handling is secure.

**Authentication test scope:**
- Token validation correctness.
- Token expiry handling.
- Token refresh logic.
- Credential storage security (never in plaintext, never in code).
- Authentication failure handling.

---

### Category 40 — Authorization Testing

**Definition:** Testing that IIOS correctly enforces access controls.

**Purpose in IIOS:** Verify that Telegram bot commands require appropriate
authorization, and that sensitive operations cannot be performed by unauthorized users.

**Authorization test scope:**
- Telegram command authorization.
- Kill switch lift authorization.
- Configuration change authorization.
- Unauthorized access attempt handling.

---

### Category 41 — Recovery Testing

**Definition:** Testing that IIOS correctly recovers from failures.

**Purpose in IIOS:** Verify that every defined recovery procedure works as
specified, restoring the system to the expected state within the defined RTO.

**Recovery test scope:**
- Container restart recovery (state reconstructed from persistent store).
- Data feed failover (primary to fallback within 90 seconds).
- Database recovery (from backup, with defined RPO).
- Kill switch lift recovery.
- Broker reconnection recovery.
- Order manager restart recovery (position state reconstructed from journal).

---

### Category 42 — Failure Injection Testing

**Definition:** Deliberately injecting failures into IIOS to verify that failure
handling works as specified.

**Purpose in IIOS:** Verify that the system responds correctly to failures that
are difficult to reproduce naturally.

**Failure injection scope:**
- Data feed network failure (injected at the network layer).
- Broker API unavailability (injected response).
- Database corruption (injected file corruption).
- Memory pressure (injected via memory allocation limit).
- Clock skew (injected via the injectable clock utility).
- Partial message delivery (injected by dropping messages).

---

### Category 43 — Chaos Testing

**Definition:** Randomly injecting failures into a production-equivalent environment
to discover failure modes that were not anticipated.

**Purpose in IIOS:** Verify that the system has no undiscovered critical failure
modes by exposing it to random, unexpected failures.

**Chaos test scope:**
- Random container restart.
- Random network partition.
- Random process kill (of specific IIOS engines).
- Random resource exhaustion.

**Chaos testing safety:** Chaos testing is performed only in staging environments,
not in production.

---

### Category 44 — Disaster Recovery Testing

**Definition:** Testing the complete disaster recovery procedure — the ability to
restore full IIOS operation from a backup after a complete system failure.

**Purpose in IIOS:** Verify that the DR procedure works within the defined RTO
(Recovery Time Objective) and RPO (Recovery Point Objective).

**DR test scope:**
- Full VPS rebuild from the deployment kit.
- Database restore from backup.
- Container restart and health verification.
- Full trading cycle execution after DR.
- RTO measurement.

---

### Category 45 — Resilience Testing

**Definition:** Testing the overall resilience of IIOS — its ability to absorb
disruptions and continue operating.

**Purpose in IIOS:** Verify that the designed resilience mechanisms (fallbacks,
circuit breakers, graceful degradation) collectively provide the intended level
of availability.

**Resilience test scope:**
- Multi-component failure scenarios.
- Recovery sequence ordering.
- System behavior during the recovery period (partial availability).

---

## 2.9 Group 8 — Operational Testing

### Category 46 — Operational Testing

**Definition:** Testing that IIOS can be operated effectively by the operations
team — that monitoring, alerting, diagnostics, and control functions work correctly.

**Purpose in IIOS:** Verify that the operators have all the tools they need to
monitor, diagnose, and control IIOS.

**Operational test scope:**
- Dashboard correctness (displayed values match underlying data).
- Alert delivery (alerts arrive at the Telegram bot within the defined SLA).
- Log query capability.
- Diagnostic command correctness (Telegram bot /status, /perf, /learn commands).
- Kill switch command correctness.
- Container health check accuracy.

---

### Category 47 — Acceptance Testing

**Definition:** Testing that IIOS meets the defined acceptance criteria from the
perspective of its intended use.

**Purpose in IIOS:** Verify that IIOS fulfills its mission — operating as a safe,
reliable, improving algorithmic trading system.

**Acceptance criteria:**
- Paper trading completion of 30 consecutive trading days without a system failure.
- All 10 scheduled tasks execute reliably at their defined times.
- Decision quality (decisions are internally consistent and rule-compliant).
- Alert delivery SLA met (CRITICAL alerts within 5 seconds).
- Recovery from all defined failure scenarios within RTO.

---

*End of Part II*

---
# PART III — TESTING ARCHITECTURE

## 3.1 Architecture Overview

The IIOS Testing Architecture is governed by 18 components. These components
manage every aspect of testing: what tests exist, how they are scheduled, what
data they use, how evidence is collected, and how quality is certified.

Together they form a complete testing governance system that ensures tests are
maintained, executed, and used to make deployment decisions.

---

## 3.2 Component 1 — Test Registry

**Purpose:**
The Test Registry is the authoritative catalog of all tests that exist in the
IIOS test suite. It is the single source of truth for test identity, classification,
and status.

**Responsibilities:**
- Accept test registration from test authors.
- Maintain a map from test identity to test metadata.
- Track the current status of each registered test.
- Enforce registration constraints (test IDs are unique).
- Provide test lookup by category, component, coverage type, and status.
- Emit registration and status-change events to the Event Bus.

**Inputs:**
- Test registration requests (test descriptor, category, component under test, coverage type).
- Test status updates (from the Result Manager).
- Test retirement requests.

**Outputs:**
- Test metadata to requesting components.
- Registration and status events to the Event Bus.
- Registry health status to the Monitoring component.

**Interactions:**
- Receives registrations from the Test Manager.
- Provides lookups to the Test Scheduler and Coverage Manager.
- Reports to the Governance Manager.

**Dependencies:**
- Core Utilities.
- Event Bus.
- Logging Helpers.

**Lifecycle:**
The Registry is initialized before any test components. It is the last component
to shut down (after all test results are recorded).

**Failure Modes:**
- Duplicate test registration: rejected. Duplicate test IDs indicate a configuration
  problem that must be resolved.
- Registry unavailable: no tests can be scheduled or executed. This is a CRITICAL
  failure of the test infrastructure.

**Recovery:**
Registry state is rebuilt from test metadata files in the test codebase. All tests
are re-registered during rebuild.

**Monitoring:**
- Metric: total registered tests (gauge).
- Metric: tests by status (REGISTERED, ACTIVE, DISABLED, RETIRED).
- Health: registry responds to health probe.

**Engineering Notes:**
The Registry is the reference point for test governance. Any test that is not
registered is not managed. Unregistered tests that happen to run are not counted
toward coverage and do not produce certified results.

---

## 3.3 Component 2 — Test Catalog

**Purpose:**
The Test Catalog provides the human-readable, searchable documentation of all
tests — what they test, how they work, and their current quality status.

**Responsibilities:**
- Maintain documentation for each registered test.
- Provide search capability (find tests by component, category, tag, and status).
- Track test quality (flakiness history, recent pass rates).
- Generate catalog reports.
- Detect catalog inconsistencies (documented tests not in Registry).

**Inputs:**
- Test documentation from test authors.
- Test execution history from the Result Manager.
- Registry state.

**Outputs:**
- Test documentation to developers.
- Catalog search results.
- Test quality reports.

**Interactions:**
- Reads from the Test Registry.
- Receives results from the Result Manager.

**Dependencies:**
- Test Registry.
- Result Manager.
- Search Utilities.

**Engineering Notes:**
The Catalog serves as the authoritative reference for understanding what is
tested and why. A test without catalog documentation is considered undocumented
and flags a governance review.

---

## 3.4 Component 3 — Test Manager

**Purpose:**
The Test Manager orchestrates the registration, configuration, and lifecycle of
all tests in the IIOS test suite.

**Responsibilities:**
- Process new test registrations.
- Apply test configuration (timeouts, retry limits, resource budgets).
- Assign tests to test suites.
- Manage test deprecation and retirement.
- Enforce registration policies (required metadata, category assignment).
- Publish test lifecycle events.

**Inputs:**
- New test registrations from test authors.
- Test configuration.
- Lifecycle management requests.

**Outputs:**
- Registered test descriptors to the Test Registry.
- Test suite assignments to the Test Scheduler.
- Lifecycle events to the Event Bus.

**Interactions:**
- Registers tests in the Test Registry.
- Assigns tests to the Test Scheduler.
- Reports governance compliance to the Governance Manager.

**Dependencies:**
- Test Registry.
- Test Scheduler.
- Governance Manager.
- Configuration Loader.

**Failure Modes:**
- Test registration with missing required metadata: rejected with a clear error.
- Test suite assignment conflict: escalated to the Governance Manager.

**Engineering Notes:**
The Test Manager is the gatekeeper for the test registry. Tests that do not meet
registration requirements are not accepted. Every accepted test has a unique ID,
an owner, a component under test, and a category.

---

## 3.5 Component 4 — Test Scheduler

**Purpose:**
The Test Scheduler executes tests at the right times and in the right order,
managing test parallelism, resource conflicts, and scheduling priorities.

**Responsibilities:**
- Execute the scheduled test suite (CI on every commit, nightly for full suites).
- Manage test parallelism (run independent tests concurrently).
- Enforce resource limits (maximum concurrent tests).
- Prioritize test execution (fail-fast tests run first).
- Track schedule adherence (detect overdue tests).
- Coordinate with the Fixture Manager and Dataset Manager before test execution.

**Inputs:**
- Test execution requests (from CI system, nightly schedule, manual triggers).
- Test priority and dependency configurations.
- Resource availability from the Resource Manager.

**Outputs:**
- Test execution results to the Result Manager.
- Schedule adherence reports.
- Resource utilization metrics.

**Interactions:**
- Reads the test list from the Test Registry.
- Requests fixtures from the Fixture Manager.
- Requests datasets from the Dataset Manager.
- Reports results to the Result Manager.

**Dependencies:**
- Test Registry.
- Fixture Manager.
- Dataset Manager.
- Result Manager.
- Scheduling Utilities.

**Lifecycle:**
Active whenever tests are being executed. In CI mode, active for every commit.
In nightly mode, active for the scheduled nightly window.

**Failure Modes:**
- Test timeout: test is terminated and recorded as FAILED.
- Fixture preparation failure: test is skipped and recorded as BLOCKED.
- Resource exhaustion: test is queued and retried when resources are available.

**Engineering Notes:**
The Scheduler implements the fail-fast principle: if early-stage tests (unit tests)
fail, later-stage tests (integration tests) are not executed. This saves time and
directs attention to the root cause.

---

## 3.6 Component 5 — Scenario Manager

**Purpose:**
The Scenario Manager defines, maintains, and provides the test scenarios used
by IIOS behavioral tests.

**Responsibilities:**
- Maintain the library of named test scenarios.
- Provide scenarios to test authors and the Test Scheduler.
- Classify scenarios (normal, edge case, failure, stress, adversarial).
- Track scenario coverage (which scenarios have been tested recently).
- Identify gaps in scenario coverage.

**Inputs:**
- Scenario definitions from test authors and the Architecture Council.
- Scenario coverage reports from the Coverage Manager.

**Outputs:**
- Scenario definitions to requesting tests.
- Scenario coverage gap reports.

**IIOS named scenarios:**
- NORMAL_BULL_MARKET: typical bullish conditions, moderate VIX, strong breadth.
- NORMAL_BEAR_MARKET: typical bearish conditions.
- HIGH_VIX: VIX > 30, approaching kill switch threshold.
- KILL_SWITCH_VIX: VIX > 45, kill switch must activate.
- KILL_SWITCH_LOSS: daily loss exceeds 2%.
- DATA_FEED_FAIL: Dhan feed unavailable, yfinance fallback active.
- BROKER_UNAVAILABLE: broker API unreachable.
- MARKET_HOLIDAY: trading day, but NSE is closed.
- EXPIRY_FRIDAY: weekly options expiry.
- MONTH_END: last trading day of the month.
- CONTAINER_RESTART: system restarts mid-session.
- ZERO_STRATEGIES: all strategies disabled.
- MAXIMUM_POSITIONS: position limit reached.
- AUDIT_CHAIN_BREAK: audit chain integrity violation.

**Engineering Notes:**
Named scenarios ensure that test coverage of important conditions is visible and
trackable. An IIOS deployment that has not been tested against all defined scenarios
is not certified for production.

---

## 3.7 Component 6 — Fixture Manager

**Purpose:**
The Fixture Manager creates, provides, and cleans up test fixtures — the
pre-configured objects and environments that tests need to operate.

**Responsibilities:**
- Maintain the fixture library (reusable pre-configured objects).
- Create fixtures on demand for test execution.
- Provide fixture isolation (each test gets a clean, independent fixture).
- Clean up fixtures after test completion.
- Track fixture usage and performance.
- Manage fixture lifecycle (create, use, reset, destroy).

**Inputs:**
- Fixture requests from the Test Scheduler.
- Fixture definitions from test authors.

**Outputs:**
- Initialized fixture instances to tests.
- Fixture teardown confirmation to the Test Scheduler.

**IIOS fixture types:**
- IIOS engine fixture (a configured, started engine instance).
- Database fixture (an empty or pre-populated test database).
- Data feed fixture (a mock or stub data feed with defined behavior).
- Broker fixture (a mock broker with defined response behavior).
- Market state fixture (a defined market condition for a test scenario).
- Strategy fixture (a pre-configured strategy with defined parameters).

**Failure Modes:**
- Fixture initialization failure: test is blocked. The Fixture Manager reports the
  failure to the Test Scheduler.
- Fixture cleanup failure: resources are leaked. The Fixture Manager escalates to the
  Resource Manager for forced cleanup.

**Engineering Notes:**
Fixture isolation is critical. A fixture that retains state from a previous test
can cause test failures that are impossible to reproduce consistently.

---

## 3.8 Component 7 — Dataset Manager

**Purpose:**
The Dataset Manager manages all test datasets — the data inputs used by IIOS
tests.

**Responsibilities:**
- Maintain the dataset library (13 dataset types, as defined in Part V).
- Provide datasets on demand to the Test Scheduler.
- Track dataset versioning (tests record which dataset version they ran against).
- Manage golden dataset updates.
- Validate dataset integrity (datasets are not corrupted).
- Enforce dataset access controls (live datasets are restricted).

**Inputs:**
- Dataset requests from the Test Scheduler.
- Dataset update requests from the Architecture Council.
- Dataset integrity validation requests.

**Outputs:**
- Dataset instances to requesting tests.
- Dataset versioning records.
- Dataset integrity reports.

**Interactions:**
- Provides datasets to the Test Scheduler.
- Provides dataset version information to the Evidence Manager.
- Reports dataset health to the Monitoring component.

**Dependencies:**
- File Utilities.
- Hashing Utilities (for integrity verification).
- Version Utilities.

**Failure Modes:**
- Dataset integrity check failure: dataset is quarantined. Tests using the dataset
  are blocked until the dataset is restored or replaced.
- Dataset not found: test is blocked. The Test Scheduler is notified.

**Engineering Notes:**
Golden datasets must never be modified without Architecture Council approval.
Any modification to a golden dataset changes the expected test outcomes and requires
a full review cycle.

---

## 3.9 Component 8 — Mock Manager

**Purpose:**
The Mock Manager creates and manages mock implementations of IIOS dependencies
for use in isolated testing.

**Responsibilities:**
- Provide mock implementations for all external dependencies.
- Configure mock behavior (response payloads, delays, error scenarios).
- Verify mock interactions (which functions were called, with what arguments).
- Record mock invocations for test assertion.
- Reset mock state between tests.

**IIOS mock types:**
- Mock data feed (configurable price data, feed failures, staleness).
- Mock broker (configurable order acceptance, rejections, position reports).
- Mock Event Bus (records all events published for assertion).
- Mock Telegram bot (records all alerts sent for assertion).
- Mock clock (injectable timestamp for deterministic time-dependent tests).
- Mock database (in-memory database for fast, isolated repository tests).

**Interactions:**
- Provides mocks to the Fixture Manager (mocks are composed into fixtures).
- Provides interaction records to the Result Manager.

**Engineering Notes:**
Mocks must accurately simulate the behavior of their real counterparts, including
their failure modes. A mock that never fails does not test failure handling.

---

## 3.10 Component 9 — Simulation Manager

**Purpose:**
The Simulation Manager manages the test-mode operation of the IIOS simulation
components (Monte Carlo simulator, market simulator).

**Responsibilities:**
- Provide deterministic simulation configurations for tests.
- Execute simulations with known seeds for reproducible results.
- Compare simulation outputs against known-good results.
- Detect simulation engine regressions (same seed produces different result).

**Inputs:**
- Simulation configuration requests from tests.
- Known-good simulation results (golden datasets).

**Outputs:**
- Deterministic simulation results.
- Regression detection results.

**Dependencies:**
- Randomization Utilities (seeded PRNG).
- Dataset Manager.

**Engineering Notes:**
Simulation regression detection is critical. The Monte Carlo simulation is used
to evaluate strategy risk. If the simulation engine produces different results
for the same inputs, the risk evaluation is unreliable.

---

## 3.11 Component 10 — Replay Manager

**Purpose:**
The Replay Manager manages the historical replay functionality — the ability to
replay historical market data through the IIOS decision pipeline.

**Responsibilities:**
- Manage the replay dataset library.
- Execute historical replay scenarios.
- Compare replay decisions to historical decisions.
- Detect decision regressions (same historical data produces different decisions).
- Manage replay timing (real-time vs accelerated replay).

**Inputs:**
- Replay dataset requests from tests.
- Replay configuration (speed, start/end date, component scope).

**Outputs:**
- Replay decision logs.
- Regression comparison reports.
- Replay performance metrics.

**Interactions:**
- Reads from the Dataset Manager.
- Provides results to the Result Manager and Regression Manager.

**Engineering Notes:**
Replay must be capable of accelerated mode (faster than real-time) for CI/CD usage.
Real-time replay is used for acceptance testing and pre-deployment validation.

---

## 3.12 Component 11 — Coverage Manager

**Purpose:**
The Coverage Manager measures and reports on the coverage provided by the test
suite across all 15 coverage dimensions defined in Part VI.

**Responsibilities:**
- Collect coverage data from test execution.
- Compute coverage scores for all 15 dimensions.
- Identify coverage gaps.
- Track coverage trends over time.
- Block certification when minimum coverage thresholds are not met.

**Inputs:**
- Test execution reports from the Result Manager.
- Component and scenario inventory from the Scenario Manager.

**Outputs:**
- Coverage scores per dimension.
- Coverage gap reports.
- Coverage trend charts.
- Coverage certification status (PASS/FAIL per threshold).

**Interactions:**
- Receives test results from the Result Manager.
- Reports coverage to the Certification Manager.
- Reports gaps to the Governance Manager.

**Dependencies:**
- Test Registry.
- Scenario Manager.
- Result Manager.

**Monitoring:**
- Metric: coverage score per dimension (gauge).
- Alert: any coverage dimension drops below its threshold.

**Engineering Notes:**
Coverage is not just line coverage. A test suite with 100% line coverage but 0%
failure scenario coverage is not adequately tested. All 15 coverage dimensions
are required to be above threshold for production certification.

---

## 3.13 Component 12 — Result Manager

**Purpose:**
The Result Manager collects, stores, and provides access to all test execution
results.

**Responsibilities:**
- Accept test execution results from the Test Scheduler.
- Store results with full metadata (test ID, timestamp, dataset version, duration, pass/fail).
- Compute aggregate metrics (pass rate, failure rate, duration trends).
- Provide result history to the Regression Manager and Certification Manager.
- Detect result anomalies (sudden increase in failures, unexpected pass after
  persistent failure).

**Inputs:**
- Test execution results from the Test Scheduler.
- Result queries from the Certification Manager and Regression Manager.

**Outputs:**
- Test result records.
- Aggregate result metrics.
- Result history reports.

**Interactions:**
- Receives results from the Test Scheduler.
- Provides results to the Regression Manager.
- Provides results to the Certification Manager.
- Provides results to the Evidence Manager.

**Dependencies:**
- Database Utilities.
- Metrics Helpers.

**Lifecycle:**
Active throughout the testing lifecycle. Results are retained for the defined
evidence retention period (minimum 2 years).

**Failure Modes:**
- Result storage failure: results are buffered and retried. If the failure persists,
  the test run is invalidated.

**Engineering Notes:**
Result storage must be atomic. A partial result record (test started but result
not recorded) is treated as a failure, not as "in progress."

---

## 3.14 Component 13 — Evidence Manager

**Purpose:**
The Evidence Manager collects, organizes, and preserves all evidence produced
by test execution, for use in certification and audit.

**Responsibilities:**
- Collect all evidence artifacts from test execution (logs, screenshots, data files).
- Organize evidence by test ID, execution timestamp, and component.
- Sign evidence records (cryptographic hash for integrity).
- Provide evidence access to the Certification Manager.
- Enforce evidence retention policies.
- Produce evidence packages for audit.

**Inputs:**
- Evidence artifacts from the Test Scheduler.
- Evidence queries from the Certification Manager.

**Outputs:**
- Evidence records (with integrity signatures).
- Evidence packages for certification and audit.
- Evidence retention status.

**Interactions:**
- Receives evidence from the Test Scheduler.
- Provides evidence to the Certification Manager.
- Reports to the Governance Manager.

**Dependencies:**
- Hashing Utilities (integrity signing).
- File Utilities.
- Compression Utilities.

**Lifecycle:**
Active throughout the testing and operational lifecycle. Evidence is retained
according to the evidence retention policy.

**Engineering Notes:**
The Evidence Manager uses the same hash-chain integrity mechanism as the audit log.
Every evidence record's integrity can be verified independently.

---

## 3.15 Component 14 — Certification Manager

**Purpose:**
The Certification Manager manages the formal certification of IIOS components
for production deployment.

**Responsibilities:**
- Define certification requirements for each component and certification level.
- Execute the certification evaluation (verify all requirements are met).
- Issue certificates to qualifying components.
- Revoke certificates from components that regress below certification thresholds.
- Maintain the certification registry.
- Coordinate Architecture Council certification reviews.

**Inputs:**
- Certification requests from component owners.
- Coverage reports from the Coverage Manager.
- Result history from the Result Manager.
- Evidence packages from the Evidence Manager.
- Architecture Council certification decisions.

**Outputs:**
- Certification decisions (GRANTED, DENIED, REVOKED).
- Certification registry updates.
- Certification reports.

**Certification levels:**
- EXPERIMENTAL: No requirements. Dev use only.
- TESTABLE: Basic unit tests registered. > 70% coverage.
- INTEGRATION-READY: Full unit tests, integration tests registered. > 85% coverage.
- STAGING-READY: All test categories applicable, all passing. > 90% coverage.
- PRODUCTION-READY: All categories PASS. > 95% coverage. Evidence complete.
  30-day regression history clean. Architecture Council certified.

**Engineering Notes:**
No IIOS component is deployed to production without PRODUCTION-READY certification.
This is an absolute rule. Exceptions require Architecture Council unanimous vote
and are documented as exceptions in the certification registry.

---

## 3.16 Component 15 — Regression Manager

**Purpose:**
The Regression Manager detects, tracks, and manages test regressions.

**Responsibilities:**
- Compare current test results with historical results.
- Detect regressions (previously passing tests that now fail).
- Classify regressions by severity and component.
- Track regression resolution.
- Detect flaky tests (tests that pass and fail without code changes).
- Generate regression reports.

**Inputs:**
- Current test results from the Result Manager.
- Historical test results (stored in the Result Manager database).

**Outputs:**
- Regression detection reports.
- Flaky test reports.
- Regression resolution tracking.

**Interactions:**
- Reads current and historical results from the Result Manager.
- Reports to the Certification Manager (regressions block certification).
- Reports to the Governance Manager.

**Engineering Notes:**
A regression in a safety-critical test (kill switch, position limits) is treated
as a CRITICAL event, not just a test failure. It triggers immediate investigation
and deployment freeze.

---

## 3.17 Component 16 — Quality Manager

**Purpose:**
The Quality Manager tracks and reports the quality of the test suite itself —
not the quality of the components being tested.

**Responsibilities:**
- Track test quality metrics (coverage, flakiness, documentation completeness).
- Compute the Testing Quality Score (TQS).
- Identify quality regressions in the test suite.
- Report quality trends over time.
- Provide quality evidence to the Certification Manager.

**Inputs:**
- Test metadata from the Test Registry.
- Test results from the Result Manager.
- Coverage scores from the Coverage Manager.
- Documentation completeness from the Test Catalog.

**Outputs:**
- Testing Quality Score (TQS).
- Test suite quality reports.
- Quality trend data.

**Engineering Notes:**
A test suite with high coverage but low quality (flaky tests, outdated documentation)
is not trustworthy. The TQS measures the quality of the tests, not just the
quantity of tests.

---

## 3.18 Component 17 — Reporting Manager

**Purpose:**
The Reporting Manager generates all test reporting outputs — dashboards, summary
reports, trend reports, certification reports, and operational reports.

**Responsibilities:**
- Generate CI/CD test summary reports.
- Generate daily and weekly test quality reports.
- Generate certification reports for Architecture Council reviews.
- Generate trend reports (coverage trends, pass rate trends).
- Publish reports to the ControlTower dashboard.

**Inputs:**
- Test results from the Result Manager.
- Coverage data from the Coverage Manager.
- Quality scores from the Quality Manager.
- Certification status from the Certification Manager.

**Outputs:**
- Test summary reports (per commit, per day, per week).
- Certification reports.
- Dashboard data.

**Engineering Notes:**
Reports must be generated within 5 minutes of test completion. A report that is
available 24 hours after the test run is not useful for CI/CD decision-making.

---

## 3.19 Component 18 — Governance Manager

**Purpose:**
The Governance Manager enforces the policies, standards, and rules that govern
all tests and the testing framework.

**Responsibilities:**
- Enforce naming conventions for all tests.
- Enforce documentation requirements.
- Track governance compliance per test and per component.
- Generate governance reports.
- Process governance exceptions.
- Interface with the Architecture Council for governance decisions.

**Inputs:**
- Test metadata from all components.
- Policy definitions from the Architecture Council.
- Compliance check requests.

**Outputs:**
- Governance compliance reports.
- Non-compliance notifications.
- Exception decisions.

**Engineering Notes:**
Governance Manager findings are advisory during development. During the certification
process, governance compliance is mandatory. A component with unresolved governance
violations cannot advance beyond STAGING-READY certification.

---

*End of Part III*

---
# PART IV — TESTING LIFECYCLE

## 4.1 Lifecycle Overview

Every IIOS test follows a defined 12-stage lifecycle from planning through retirement.
The lifecycle ensures that tests are intentionally created, properly maintained,
and eventually retired when no longer needed.

---

## 4.2 Lifecycle State Diagram

`
PLANNED
   |
   v
PREPARED -----> CANCELLED (test no longer needed before authoring)
   |
   v
AUTHORED ------> (test code written)
   |
   v
REGISTERED ----> (registered in Test Registry)
   |
   v
VALIDATED -----> (basic validation: runs, deterministic, isolated)
   |
   v
ACTIVE ---------> (running in CI or scheduled suite)
   |
   v
MONITORING -----> (continuous pass/fail tracking)
   |          |
   |          v
   |       FLAKY (intermittent failures detected)
   |          |
   |      (fix or retire)
   |
   v
DEPRECATED -----> (component under test being retired)
   |
   v
SUNSET ---------> (wind-down period)
   |
   v
RETIRED --------> (removed from active suite)
`

---

## 4.3 Stage 1 — Planning

**Definition:** Test planning is the deliberate identification of what must be
tested for a component, scenario, or capability before any tests are written.

**Entry Criteria:** A new component, feature, or integration is being developed.
Or an existing component's test coverage has been identified as insufficient.

**Activities:**
- Identify all testing categories applicable to the component.
- Define all scenarios that must be covered.
- Identify the datasets required.
- Identify the mocks and fixtures required.
- Estimate the testing effort.
- Register the planned tests in the Test Registry with PLANNED status.
- Assign each planned test to an owner.

**Exit Criteria:** All planned tests are registered. Owners are assigned. Datasets
and fixtures are identified.

**Planning deliverables:**
- Test plan document (list of planned tests with category, owner, scenario, and dataset).
- Coverage estimate (what coverage will the planned tests provide?).
- Test dependency map (which tests require which fixtures and datasets?).

---

## 4.4 Stage 2 — Preparation

**Definition:** Preparation creates all the infrastructure needed before tests can
be authored: fixtures, datasets, mocks, and environment configurations.

**Entry Criteria:** Test plan approved.

**Activities:**
- Create required test fixtures.
- Acquire or create required datasets.
- Configure required mocks.
- Set up the test environment.
- Verify that all test infrastructure is in place before test authoring begins.

**Exit Criteria:** All planned fixtures, datasets, and mocks are available and verified.

---

## 4.5 Stage 3 — Dataset Selection

**Definition:** Identifying and preparing the specific datasets that will be used
for each test.

**Entry Criteria:** Fixtures and mock infrastructure available.

**Activities:**
- Select the appropriate dataset type for each test (see Part V).
- Verify dataset integrity (hash check).
- Create synthetic datasets where historical data is unavailable.
- Create edge-case datasets for boundary condition tests.
- Register all selected datasets with the Dataset Manager.
- Record dataset version numbers for test reproducibility.

**Exit Criteria:** All required datasets selected, verified, and registered.

---

## 4.6 Stage 4 — Environment Preparation

**Definition:** Preparing the test execution environment to match the required
test conditions.

**Entry Criteria:** Datasets selected.

**Activities:**
- Start test environment containers.
- Apply test-specific configuration.
- Seed databases with required initial state.
- Verify network connectivity between test components.
- Confirm all dependencies are available.
- Run environment health checks.

**Exit Criteria:** Environment health checks pass. All components respond to probes.

---

## 4.7 Stage 5 — Execution

**Definition:** Running the tests against the prepared environment and datasets.

**Entry Criteria:** Environment ready. Fixtures prepared. Datasets available.

**Activities:**
- Execute tests in the determined order (unit first, integration after, system last).
- Collect all test outputs (pass/fail, metrics, log snippets).
- Record test execution timing.
- Monitor resource usage during execution.
- Handle test timeouts (terminate and record as FAILED).
- Track test dependencies (if Test A fails, dependent Tests B and C may be skipped).

**Execution order:**
1. Unit tests (fastest, most isolated).
2. Component tests.
3. Module tests.
4. Integration tests.
5. Subsystem tests.
6. System tests (slowest, most comprehensive).

**Fail-fast rule:** If unit tests fail, do not execute integration tests. Fix
the unit test failures first. This prevents slow integration tests from running
against a clearly broken codebase.

---

## 4.8 Stage 6 — Evidence Collection

**Definition:** Collecting and preserving all artifacts produced during test
execution as evidence of what occurred.

**Entry Criteria:** Test execution complete.

**Activities:**
- Collect test logs (from all components exercised by the test).
- Collect test output files (actual vs expected comparison files).
- Collect performance measurements (latency histograms, throughput measurements).
- Collect coverage reports.
- Collect assertion failure details (what was expected, what was actual).
- Hash all collected evidence for integrity.
- Package evidence under the test run ID.

**Exit Criteria:** All evidence artifacts collected, hashed, and stored in the
Evidence Manager.

---

## 4.9 Stage 7 — Result Validation

**Definition:** Evaluating whether the test results are valid — not just whether
tests passed or failed, but whether the test execution itself was valid.

**Entry Criteria:** Evidence collected.

**Activities:**
- Verify test isolation (tests did not share state).
- Verify determinism (running the same tests again produces the same results).
- Verify timing validity (tests completed within their timeout budgets).
- Verify dataset integrity (datasets used were the expected versions).
- Check for unexpected external side effects (database records created outside
  expected scope).
- Classify any unexpected failures (infrastructure failure vs test failure).

**Exit Criteria:** Results validated. Each result classified as: PASS, FAIL,
BLOCKED, SKIPPED, or INVALID.

---

## 4.10 Stage 8 — Certification

**Definition:** Using the validated test results to make a certification decision
for the component.

**Entry Criteria:** All test results validated. Coverage computed.

**Activities:**
- Verify coverage thresholds are met for all 15 dimensions.
- Verify all required test categories have run.
- Verify no regressions from previous certification.
- Compile the evidence package for the Certification Manager.
- Present the certification package to the Architecture Council (for PRODUCTION level).
- Record the certification decision.

**Exit Criteria:** Certification decision recorded (GRANTED or DENIED).

---

## 4.11 Stage 9 — Regression Recording

**Definition:** Recording the test results as the new regression baseline.

**Entry Criteria:** Certification granted.

**Activities:**
- Record the certified test results as the new regression baseline.
- Update golden datasets if behavior has intentionally changed (requires Architecture
  Council approval).
- Update performance benchmarks if performance has intentionally improved.
- Notify the Regression Manager of the new baseline.

---

## 4.12 Stage 10 — Reporting

**Definition:** Generating and distributing the test reports for the completed
test cycle.

**Entry Criteria:** Regression baseline recorded.

**Activities:**
- Generate the test summary report (per-category pass rates, coverage, regressions).
- Generate the certification report.
- Publish to the ControlTower dashboard.
- Notify stakeholders (via Telegram bot for deployment decisions).
- Archive the report in the Evidence Manager.

---

## 4.13 Stage 11 — Continuous Monitoring

**Definition:** Ongoing monitoring of test results during the operational period
between formal test cycles.

**Entry Criteria:** Component deployed to production.

**Activities:**
- Run the regression smoke test suite daily.
- Monitor production health metrics that correspond to tested behaviors.
- Alert on any new test failure that was not present in the certification baseline.
- Track flakiness (tests that fail intermittently in the daily regression run).
- Track performance metric trends.

**Exit Criteria:** Component is retired or a new version is deployed (which
triggers a new test cycle).

---

## 4.14 Stage 12 — Retirement

**Definition:** Retiring tests that are no longer relevant.

**Entry Criteria:** The component under test is being retired, or the tested
behavior no longer exists.

**Activities:**
- Identify all tests for the retiring component.
- Verify that no other components depend on the test fixtures being retired.
- Deregister tests from the Test Registry.
- Archive test code in version control (do not delete).
- Archive test evidence in the Evidence Manager.

**Exit Criteria:** Tests removed from active execution. Evidence archived.

---

*End of Part IV*

---

# PART V — TEST DATA FRAMEWORK

## 5.1 Test Data Purpose

The quality of tests depends fundamentally on the quality of the data used to
run them. Poorly chosen or poorly maintained test data produces misleading results.
The IIOS Test Data Framework defines 13 dataset types, each serving a specific
testing purpose.

---

## 5.2 Dataset Type 1 — Reference Datasets

**Definition:** Small, manually curated datasets that represent the "known-good"
inputs and outputs for a component. Reference datasets are the foundation for
correctness testing.

**Governance:**
- Created by the component owner.
- Reviewed and approved by the Architecture Council.
- Versioned in source control alongside the component code.
- Changed only with explicit approval (any change requires a full re-certification run).

**Contents:**
- 20–100 input-output pairs per component.
- One row per logical test case (normal, edge, error).
- Comments explaining the purpose of each row.

**IIOS examples:**
- Financial calculation reference: inputs (price history) and expected outputs (Sharpe ratio, drawdown).
- Market session reference: inputs (timestamp) and expected outputs (session type).
- Strategy signal reference: inputs (market indicators) and expected outputs (signal type, strength).

---

## 5.3 Dataset Type 2 — Historical Datasets

**Definition:** Real historical market data from past trading periods, used for
backtesting validation and historical replay testing.

**Governance:**
- Sourced from the data feed providers (Dhan, yfinance).
- Stored in read-only format once acquired.
- Versioned by acquisition date.
- Used in production-equivalent format (same schema as live data).
- Changes require Architecture Council approval.

**Contents:**
- OHLCV (Open, High, Low, Close, Volume) for NIFTY, BANKNIFTY, and tracked symbols.
- Options chain snapshots for backtesting validation.
- VIX historical values.
- Market events (expiry dates, holidays, circuit breaker days).

**Security:** Historical datasets may contain information that could be used to
reverse-engineer IIOS strategy parameters. Access is restricted to authorized
team members.

---

## 5.4 Dataset Type 3 — Synthetic Datasets

**Definition:** Programmatically generated datasets that simulate market conditions
without being tied to historical data. Synthetic datasets can be generated for
scenarios that have not occurred historically.

**Governance:**
- Generated by the simulation components using defined parameters.
- Regenerable from seed values (deterministic generation).
- Documented with the generation parameters.
- Validated for statistical plausibility before use.

**Contents:**
- Synthetically generated OHLCV time series with defined statistical properties.
- Synthetic VIX series with defined volatility regimes.
- Synthetic options chain data.
- Synthetic portfolio evolution data.

**Use cases:** Generating large volumes of test data, testing scenarios not present
in historical data (extreme events), performance testing with controlled data volumes.

---

## 5.5 Dataset Type 4 — Live Datasets

**Definition:** Real-time or recent market data used for acceptance testing and
pre-deployment validation.

**Governance:**
- Collected from live data feeds during defined collection windows.
- Timestamped and signed for integrity.
- Retained for 30 days after collection.
- Access restricted to testing in staging environment only.
- Not used for unit or integration tests (live data changes; tests must be reproducible).

**Use cases:** Acceptance testing (the system handles today's real market data),
pre-deployment validation, operational monitoring benchmarks.

---

## 5.6 Dataset Type 5 — Replay Datasets

**Definition:** Snapshots of historical market data formatted specifically for the
historical replay pipeline — with the exact format, timing, and metadata that
the replay pipeline expects.

**Governance:**
- Derived from Historical Datasets but formatted for the replay system.
- Validated by running a known scenario and comparing the output to the historical record.
- Versioned alongside the replay pipeline version.

**Contents:**
- Market data events with exact timestamps.
- Data feed response packets in the exact format produced by the live feed.
- Event ordering markers.

---

## 5.7 Dataset Type 6 — Benchmark Datasets

**Definition:** Standardized datasets used for performance measurement, enabling
comparison across releases.

**Governance:**
- Fixed at the start of each major version.
- Never modified (any modification changes the benchmark, making comparisons invalid).
- Accompanied by defined performance targets.
- Stored separately from other datasets to prevent accidental modification.

**Contents:**
- Standard-size inputs for latency benchmarking (e.g., a 1-year price history).
- Large inputs for throughput benchmarking.
- Concurrent access patterns for concurrency benchmarking.

---

## 5.8 Dataset Type 7 — Training Datasets

**Definition:** Historical datasets used to train and calibrate AI components
(MetaLearning, K-NN strategy weight predictor).

**Governance:**
- Split from the full historical dataset (training/validation/test split).
- Never used for validation or test evaluation (data leakage prevention).
- Documented with the split date range.
- Architecture Council approval required to change the split.

**Contents:**
- Feature vectors for all historical trading sessions.
- Regime labels for each session.
- Strategy performance outcomes for each session.

---

## 5.9 Dataset Type 8 — Validation Datasets

**Definition:** Held-out historical datasets used to evaluate the generalization
of trained AI models — never seen during training.

**Governance:**
- Strictly separated from Training Datasets (no overlap in time period).
- Used only for evaluation, never for training.
- The separation boundary is fixed and documented.

**Contents:**
- Same format as Training Datasets but from a different time period.

---

## 5.10 Dataset Type 9 — Golden Datasets

**Definition:** Datasets paired with known-correct outputs, used to detect output
regressions. A golden dataset test fails if the system produces a different output
than the golden output.

**Governance:**
- Created by running the system on reference inputs and manually reviewing the outputs.
- Approved by the Architecture Council before being designated golden.
- Stored in version control with hash integrity.
- Updated only when behavior intentionally changes (requires full Architecture Council review).
- Treated as test evidence (any golden dataset change is an auditable event).

**Contents:**
- Input dataset + expected output dataset pairs.
- One golden set per component, covering all major operational scenarios.

**IIOS golden examples:**
- Decision Engine golden: 50 historical market scenarios with expected decision outcomes.
- Risk Guardian golden: 20 kill switch trigger scenarios with expected responses.
- Strategy generator golden: 10 regime descriptions with expected strategy parameters.

---

## 5.11 Dataset Type 10 — Edge-Case Datasets

**Definition:** Datasets specifically designed to exercise boundary conditions and
edge cases in IIOS components.

**Governance:**
- Created by test authors and reviewed by the component owner.
- Documented with the specific edge case each row exercises.
- Added to incrementally as new edge cases are discovered.

**Contents:**
- Inputs at exact boundary values (VIX = 45.0, daily loss = 2.0%).
- Empty inputs (no trades, no strategies, no data).
- Minimum and maximum values for all numeric inputs.
- Inputs designed to trigger known difficult code paths.
- Dates at special boundaries (first day of month, last day, expiry Friday).

---

## 5.12 Dataset Type 11 — Failure Datasets

**Definition:** Datasets that represent failure conditions — invalid inputs, error
responses, and exceptional conditions that the system must handle correctly.

**Governance:**
- Created by test authors for failure scenario testing.
- Each entry documents the specific failure it represents.
- Reviewed by the component owner.

**Contents:**
- Invalid price data (negative prices, zero prices, impossibly large prices).
- Malformed API responses (missing fields, wrong types, truncated responses).
- Data feed error responses.
- Broker rejection messages.
- Authentication failure scenarios.

---

## 5.13 Dataset Type 12 — Corrupted Datasets

**Definition:** Datasets that represent corrupted data storage — damaged database
files, incomplete records, and integrity violations.

**Governance:**
- Created by the testing team specifically for recovery and data integrity tests.
- Clearly marked as corrupted (cannot be confused with production data).
- Stored separately from all other datasets.
- Access restricted to data integrity and recovery test contexts only.

**Contents:**
- Database files with deliberately corrupted records.
- JSON files with missing or invalid fields.
- CSV files with missing columns or inconsistent row lengths.
- Log files with hash chain breaks.

---

## 5.14 Dataset Type 13 — Certification Datasets

**Definition:** The official datasets used for certification test runs. These are
the datasets against which the certification evidence is collected.

**Governance:**
- Composed of selections from the other dataset types.
- Fixed for each certification level.
- Changes to certification datasets require Architecture Council approval.
- All certification runs must use the current certification dataset (no substitution).

**Contents:**
- The reference dataset for the component.
- The golden dataset for the component.
- The edge-case dataset for the component.
- The failure dataset for the component.
- The benchmark dataset for performance certification.

---

*End of Part V*

---

# PART VI — COVERAGE FRAMEWORK

## 6.1 Coverage Overview

Coverage measures how comprehensively the test suite exercises IIOS. IIOS defines
15 coverage dimensions, reflecting the breadth of its architecture. Traditional
code coverage is necessary but insufficient — a system that manages capital requires
coverage of decisions, scenarios, risks, and operational paths in addition to code.

---

## 6.2 Coverage Score and Aggregation

Each coverage dimension has a score from 0.0 to 1.0, measured by the Coverage Manager.

**System Coverage Score (SCS):**
`
SCS = (Code Coverage       x 0.10)
    + (Module Coverage     x 0.08)
    + (Service Coverage    x 0.07)
    + (Workflow Coverage   x 0.07)
    + (Ontology Coverage   x 0.05)
    + (Knowledge Coverage  x 0.05)
    + (Reasoning Coverage  x 0.07)
    + (Decision Coverage   x 0.10)
    + (Risk Coverage       x 0.10)
    + (Event Coverage      x 0.05)
    + (Observation Coverage x 0.05)
    + (Relationship Coverage x 0.04)
    + (Data Coverage       x 0.06)
    + (Scenario Coverage   x 0.07)
    + (Operational Coverage x 0.04)
= 0.0 to 1.0
`

**SCS thresholds:**
- PRODUCTION certification: SCS >= 0.92
- STAGING-READY: SCS >= 0.82
- INTEGRATION-READY: SCS >= 0.70

---

## 6.3 Dimension 1 — Code Coverage

**Definition:** The percentage of lines, branches, and conditions in the IIOS
codebase that are executed by at least one test.

**Measurement methodology:**
- Line coverage: fraction of executable lines executed.
- Branch coverage: fraction of conditional branches (both true and false) exercised.
- Condition coverage: fraction of Boolean sub-expressions exercised in both directions.
- MC/DC (Modified Condition/Decision Coverage) for safety-critical components.

**Targets:**
- Unit tests: > 95% line, > 90% branch.
- Overall suite: > 95% line, > 90% branch, > 85% condition.
- Safety-critical components (risk guardian, kill switch): > 98% MC/DC.

**Score 1.0:** > 98% line coverage, > 95% branch, > 90% condition.
**Score 0.5:** > 85% line, > 80% branch.
**Score 0.0:** < 70% line coverage.

---

## 6.4 Dimension 2 — Module Coverage

**Definition:** The percentage of IIOS modules (engines) that have at least the
minimum required tests registered and passing.

**Measurement methodology:**
- Count of modules with registered unit tests.
- Count of modules with registered component tests.
- Count of modules with registered integration tests.
- Score = modules with all three / total modules.

**IIOS module count:** 18 engines.

**Target:** All 18 engines must have unit, component, and integration tests.
Score 1.0 = all 18 covered.

---

## 6.5 Dimension 3 — Service Coverage

**Definition:** The percentage of public service interfaces exposed by IIOS engines
that are covered by at least one test.

**Measurement methodology:**
- Enumerate all public interface methods across all 18 engines.
- Count those exercised by at least one registered test.
- Score = covered / total.

**Target:** > 95% of public interface methods covered.

---

## 6.6 Dimension 4 — Workflow Coverage

**Definition:** The percentage of defined IIOS workflows that have been tested
end-to-end.

**IIOS workflows:**
1. Morning initialization workflow.
2. Regular trading cycle workflow.
3. Continuous market scan workflow.
4. Strategy evolution workflow.
5. EOD learning workflow.
6. Kill switch activation workflow.
7. Kill switch lift workflow.
8. Data feed failover workflow.
9. Broker reconnection workflow.
10. Container restart recovery workflow.
11. Audit log rotation workflow.
12. Strategy promotion workflow.

**Target:** All 12 workflows tested. Score 1.0 = all 12 passing.

---

## 6.7 Dimension 5 — Ontology Coverage

**Definition:** The percentage of domain concepts in the IIOS market ontology
that are exercised by at least one ontology test.

**Measurement methodology:**
- Count of concepts in the market ontology.
- Count exercised by ontology tests.
- Score = covered / total.

**Target:** > 90% of ontology concepts covered.

---

## 6.8 Dimension 6 — Knowledge Coverage

**Definition:** The percentage of knowledge base entry types and knowledge
retrieval patterns exercised by at least one knowledge test.

**Measurement methodology:**
- Count of knowledge entry types.
- Count of knowledge retrieval patterns.
- Score = covered types + covered patterns / (total types + total patterns).

**Target:** > 85% of knowledge types and patterns covered.

---

## 6.9 Dimension 7 — Reasoning Coverage

**Definition:** The percentage of defined reasoning paths in the AI agents
that have been tested with at least one test case.

**Measurement methodology:**
- Define the reasoning paths for each of the 5 debate agents.
- Count the paths exercised by tests.
- Score = covered paths / total paths.

**Target:** > 90% of agent reasoning paths covered.

---

## 6.10 Dimension 8 — Decision Coverage

**Definition:** The percentage of defined decision outcomes that the Decision
Engine can produce, exercised by at least one test.

**Decision outcomes:**
- APPROVE (score >= 6.5).
- REJECT (score < 6.5).
- REJECT_RISK_LIMIT (risk check failed).
- REJECT_KILL_SWITCH (kill switch active).
- REJECT_NO_STRATEGIES (no eligible strategies).
- REJECT_DATA_QUALITY (data quality insufficient).
- REJECT_CIRCUIT_BREAKER (circuit breaker open).
- DEFER (score in uncertain range, defer to next cycle).

**Target:** All 8 decision outcomes tested with at least 5 scenarios each.

---

## 6.11 Dimension 9 — Risk Coverage

**Definition:** The percentage of defined risk conditions and limits exercised
by at least one test.

**Risk conditions to cover:**
- VIX at 44 (approaching kill switch).
- VIX at 45 (kill switch triggers).
- VIX at 46 (kill switch already active, re-check).
- Daily loss at 1.9% (approaching limit).
- Daily loss at exactly 2.0% (kill switch triggers).
- Maximum position count reached.
- Maximum position size reached.
- Maximum exposure per symbol reached.
- Stress test failure.
- OHS below threshold.

**Target:** All defined risk conditions covered. Score 1.0 = all covered and passing.

---

## 6.12 Dimension 10 — Event Coverage

**Definition:** The percentage of defined Event Bus events produced by IIOS
that are verified by at least one test.

**Measurement methodology:**
- Enumerate all event types published to the Event Bus.
- Count those verified (published + correctly received) by at least one test.
- Score = covered / total.

**Target:** > 90% of defined event types covered.

---

## 6.13 Dimension 11 — Observation Coverage

**Definition:** The percentage of defined observability outputs (metrics, log
event types, health checks) that are verified by at least one test.

**Measurement methodology:**
- Enumerate all defined metrics, log event types, and health check endpoints.
- Count those verified by observation tests.
- Score = covered / total.

**Target:** > 85% of observability outputs covered.

---

## 6.14 Dimension 12 — Relationship Coverage

**Definition:** The percentage of defined entity relationships in IIOS data
stores that are verified by at least one test.

**Target:** > 85% of defined relationships covered.

---

## 6.15 Dimension 13 — Data Coverage

**Definition:** The percentage of the defined input space for each component
covered by the test data.

**Measurement methodology:**
- Partition the input space into equivalence classes (normal, boundary, error).
- Count the equivalence classes covered by at least one test.
- Score = covered classes / total classes.

**Target:** All equivalence classes with at least one representative test.
Score 1.0 = complete equivalence class coverage.

---

## 6.16 Dimension 14 — Scenario Coverage

**Definition:** The percentage of the named IIOS scenarios (defined in the Scenario
Manager, Section 3.6) exercised by at least one test.

**IIOS named scenario count:** 14 (listed in Section 3.6).

**Target:** All 14 named scenarios covered and passing. Score 1.0 = all 14 PASS.

---

## 6.17 Dimension 15 — Operational Coverage

**Definition:** The percentage of defined operational procedures (from the operational
runbooks) that have been tested end-to-end.

**Measurement methodology:**
- Enumerate all operational procedures in the runbooks.
- Count those that have been tested (either in recovery tests or operational tests).
- Score = tested / total.

**Target:** > 80% of operational procedures tested.

---

*End of Part VI*

---
# PART VII — QUALITY METRICS

## 7.1 Testing Quality Metrics Purpose

Quality metrics for testing measure the effectiveness of the test suite, not
just the health of the components being tested. A comprehensive metric system
enables the Architecture Council to make data-driven decisions about testing
investment and component deployment readiness.

---

## 7.2 Testing Quality Score (TQS)

The Testing Quality Score aggregates 12 metric categories into a single composite
score representing the overall quality of testing for a component.

**TQS formula:**
`
TQS = (Pass Rate          x 0.12)
    + (Failure Rate       x 0.08)
    + (Coverage Score     x 0.15)
    + (Reliability Score  x 0.12)
    + (Repeatability Scr  x 0.08)
    + (Determinism Scr    x 0.08)
    + (Recovery Score     x 0.10)
    + (Performance Score  x 0.08)
    + (Security Score     x 0.08)
    + (Op. Readiness      x 0.05)
    + (Certification Scr  x 0.04)
    + (Testing Maturity   x 0.02)
= 0.0 to 1.0
`

**TQS thresholds:**
- PRODUCTION certification: TQS >= 0.90
- STAGING-READY: TQS >= 0.80
- INTEGRATION-READY: TQS >= 0.65

---

## 7.3 Metric 1 — Pass Rate

**Definition:** The percentage of tests that pass in the most recent complete test run.

**Formula:** Pass Rate = (PASS count / Total count) x 1.0

**Measurement frequency:** Per test run (continuous in CI/CD, daily in scheduled suite).

**Target:**
- All test categories: Pass Rate = 1.0 (100%) for PRODUCTION certification.
- STAGING-READY: Pass Rate >= 0.98 (no more than 2% failure in the last 30 days).

**Score 1.0:** 100% pass in the last 5 consecutive runs.
**Score 0.5:** >= 95% pass rate.
**Score 0.0:** < 90% pass rate.

**Breakdown by category:**
- Safety tests (kill switch, risk limits): 100% required. Any failure is CRITICAL.
- Unit tests: 100% required.
- Integration tests: 98% required.
- System tests: 95% required.
- Chaos tests: 85% required (chaos tests are intentionally adversarial).

---

## 7.4 Metric 2 — Failure Rate

**Definition:** The rate at which new test failures are introduced per unit of
code change.

**Formula:** Failure Rate = New failures introduced / Total commits (rolling 30 days)

**Target:** < 0.05 new failures per commit (less than 1 failure per 20 commits).

**Score 1.0:** 0 new failures per commit over the last 30 days.
**Score 0.5:** < 0.10 failures per commit.
**Score 0.0:** > 0.20 failures per commit.

**Interpretation:** A high failure rate indicates either poor code quality or
inadequate test maintenance. Both indicate a systemic problem.

---

## 7.5 Metric 3 — Coverage Score

**Definition:** The System Coverage Score (SCS) as defined in Part VI.

**Formula:** SCS as computed from the 15 coverage dimensions.

**Target:** SCS >= 0.92 for PRODUCTION certification.

**Score 1.0:** SCS >= 0.95.
**Score 0.5:** SCS >= 0.80.
**Score 0.0:** SCS < 0.70.

**Tracking:** Coverage trends over the last 90 days are tracked. A declining
coverage trend (coverage decreasing with new code additions) triggers a governance review.

---

## 7.6 Metric 4 — Reliability Score

**Definition:** The consistency of test pass/fail results over time — specifically,
the absence of tests that produce incorrect or inconsistent results.

**Formula:**
`
Reliability = 1.0 - (Flaky test count / Total test count)
`

**Flaky test definition:** A test that has produced both PASS and FAIL results in
the last 10 consecutive executions with no intervening code change.

**Target:** Reliability Score >= 0.99 (at most 1% of tests are flaky).

**Score 1.0:** Zero flaky tests.
**Score 0.5:** < 2% flaky tests.
**Score 0.0:** > 5% flaky tests.

**Flaky test handling:** Flaky tests are logged in the Quality Manager. Each
flaky test has an owner and a resolution deadline of 14 days. A flaky test
that is not resolved within 14 days is disabled until fixed.

---

## 7.7 Metric 5 — Repeatability Score

**Definition:** The percentage of tests that produce the same result when run
multiple times in sequence on the same codebase without changes.

**Formula:**
`
Repeatability = Tests producing identical results in 5 consecutive runs / Total tests
`

**Target:** Repeatability Score >= 0.99.

**Score 1.0:** 100% repeatability in 5 consecutive runs.
**Score 0.5:** >= 97% repeatability.
**Score 0.0:** < 95% repeatability.

**Repeatability verification:** The CI/CD system runs the full test suite twice
per commit and compares results. Discrepancies are flagged for investigation.

---

## 7.8 Metric 6 — Determinism Score

**Definition:** The percentage of tests that produce the same result given the
same input, regardless of system state or execution timing.

**Formula:**
`
Determinism = Tests that pass determinism verification / Total tests requiring determinism
`

**Determinism verification:** Run the test with identical inputs on different
systems, at different times, and in different execution orders. A deterministic
test produces the same result in all cases.

**Target:** Determinism Score = 1.0 (100% of tests that should be deterministic are deterministic).

**Score 1.0:** All applicable tests deterministic.
**Score 0.5:** >= 98% deterministic.
**Score 0.0:** < 95% deterministic.

---

## 7.9 Metric 7 — Recovery Score

**Definition:** The percentage of defined recovery scenarios that have been
successfully tested (the system recovers as specified within the defined RTO).

**Formula:**
`
Recovery Score = Recovery scenarios PASS / Total defined recovery scenarios
`

**IIOS recovery scenarios (partial list):**
- Container restart recovery.
- Data feed failover to yfinance.
- Broker reconnection.
- Kill switch lift.
- Database recovery from backup.
- Order manager state reconstruction from journal.

**Target:** Recovery Score = 1.0 (all recovery scenarios pass).

**Score 1.0:** All recovery scenarios PASS within defined RTO.
**Score 0.5:** >= 80% of recovery scenarios PASS.
**Score 0.0:** < 70% of recovery scenarios PASS.

---

## 7.10 Metric 8 — Performance Score

**Definition:** The percentage of defined performance benchmarks that are met
by the current version.

**Formula:**
`
Performance Score = Benchmarks MET / Total benchmarks
`

**Key IIOS benchmarks:**
- GlobalIntelligence latency: <= 17ms (current baseline).
- MarketIntelligence latency: <= 19ms.
- Full cycle latency: <= 172ms.
- Data feed request latency: <= 500ms.
- Decision Engine latency: <= 50ms.
- Order Manager latency: <= 100ms.

**Target:** Performance Score = 1.0 (all benchmarks met).

**Score 1.0:** All benchmarks met with >= 10% headroom.
**Score 0.5:** All benchmarks met (within tolerance).
**Score 0.0:** Any benchmark missed.

**Performance regression rule:** If any performance benchmark regresses from the
previous baseline by more than 20%, the deployment is blocked until the regression
is investigated and either fixed or the new baseline is approved.

---

## 7.11 Metric 9 — Security Score

**Definition:** The composite security testing score — the percentage of security
test categories that produce clean results.

**Formula:**
`
Security Score = Security test categories PASS / Total security test categories
`

**Security test categories:**
- Static analysis: zero HIGH or CRITICAL findings.
- Dependency vulnerability scan: zero CRITICAL vulnerabilities.
- Authentication tests: all PASS.
- Authorization tests: all PASS.
- Input validation tests: all PASS.
- Injection prevention tests: all PASS.
- Audit integrity tests: all PASS.

**Target:** Security Score = 1.0. Any security test category FAIL blocks PRODUCTION certification.

**Score 1.0:** All security test categories PASS.
**Score 0.0:** Any security test category FAIL (there is no acceptable partial pass for security).

---

## 7.12 Metric 10 — Operational Readiness

**Definition:** The percentage of defined operational procedures that have been
validated by operational tests.

**Formula:**
`
Op. Readiness = Operational procedures tested / Total defined operational procedures
`

**Target:** Op. Readiness >= 0.90 for PRODUCTION certification.

**Score 1.0:** All operational procedures tested and passing.
**Score 0.5:** >= 80% of operational procedures tested and passing.
**Score 0.0:** < 70% of operational procedures tested.

---

## 7.13 Metric 11 — Certification Score

**Definition:** The percentage of certification requirements that have been met.

**Formula:**
`
Certification Score = Requirements MET / Total certification requirements
`

This score tracks progress toward certification, not the certification decision
itself. The certification decision is a binary outcome (GRANTED or DENIED).

**Target:** Certification Score = 1.0 before certification is requested.

---

## 7.14 Metric 12 — Testing Maturity

**Definition:** The Testing Maturity Model (TMM) level achieved by the test suite
for the component, normalized to 0.0–1.0.

**Formula:**
`
Testing Maturity = TMM Level / 5.0
`

**Target:** TMM Level 4 (score 0.80) for PRODUCTION certification. TMM Level 5
(score 1.0) for safety-critical components.

---

*End of Part VII*

---

# PART VIII — TESTING GOVERNANCE

## 8.1 Governance Purpose

Testing governance ensures that the testing framework is consistently applied,
that tests are maintained to a defined standard, and that testing decisions
are made with appropriate oversight.

---

## 8.2 Testing Standards

All IIOS tests must meet the following minimum standards:

**Registration standard:** Every test has a unique ID, a registered owner, a
category, a component under test, and a test purpose statement.

**Naming standard:** Test IDs follow the format:
[COMPONENT]-[CATEGORY]-[SEQUENCE] where COMPONENT is the IIOS engine abbreviation,
CATEGORY is the testing category (e.g., UNIT, INT, PERF), and SEQUENCE is a
three-digit number.

Examples:
- GI-UNIT-001: GlobalIntelligence unit test 001.
- RG-SEC-003: Risk Guardian security test 003.
- DEC-PERF-002: Decision Engine performance test 002.

**Documentation standard:** Every test has documentation covering: purpose,
scenario tested, dataset used, expected result, and known limitations.

**Isolation standard:** Every test starts from a known, clean state and cleans
up after itself.

**Determinism standard:** Every test that can be deterministic must be deterministic.
Random inputs must be seeded.

---

## 8.3 Approval Workflow

**New test registration:** Any engineer can register a new test. The test is
accepted with PENDING status. The component owner approves the test for ACTIVE status.

**Test retirement:** Proposed by the test owner. Approved by the component owner
and the Architecture Council representative for the affected layer.

**Golden dataset update:** Proposed by the component owner. Requires Architecture
Council approval. The Architecture Council must review the diff between old and
new golden outputs.

**Coverage threshold change:** Only the Architecture Council can change coverage
thresholds. Changes require a formal vote.

**Certification decision:** The Certification Manager compiles the evidence. The
Architecture Council makes the PRODUCTION certification decision.

---

## 8.4 Certification Workflow

**Step 1 — Pre-certification preparation:**
- Component owner verifies all required tests are registered and ACTIVE.
- Coverage Manager runs coverage analysis.
- Quality Manager computes TQS.
- Evidence Manager packages all recent test evidence.

**Step 2 — Certification request:**
- Component owner submits certification request to the Certification Manager.
- Certification Manager verifies all HARD checklist items are PASS.
- Certification Manager reports TQS and SCS.

**Step 3 — Architecture Council review:**
- Certification package presented at Architecture Council meeting.
- Council reviews: TQS, SCS, coverage gaps, recent failures, security findings.
- Council votes (simple majority for STAGING-READY, unanimous for PRODUCTION).

**Step 4 — Certification decision:**
- GRANTED: component certified for the target level. Evidence signed and stored.
- DENIED: deficiencies documented. Component owner must address before re-applying.
- CONDITIONAL: certified with conditions (specific items must be resolved within 30 days).

---

## 8.5 Documentation Standards

**Test documentation requirements:**
- Test ID and name.
- Component under test.
- Testing category.
- Scenario description.
- Dataset reference (type and version).
- Preconditions.
- Expected outcome.
- Actual outcome (recorded at execution time).
- Pass/fail criteria.
- Known limitations.
- Owner.
- Creation date, last modified date.

**Evidence documentation requirements:**
- Test run ID.
- Execution timestamp.
- Environment specification.
- Dataset versions used.
- All test results (per-test pass/fail, timing).
- Coverage measurement results.
- All collected artifacts (log excerpts, comparison files, performance measurements).
- Evidence integrity hash.

---

## 8.6 Evidence Retention

Evidence retention is a compliance requirement, not just an operational convenience.
IIOS testing evidence may be required for regulatory review, incident investigation,
or dispute resolution.

**Retention periods:**
- Unit and component test evidence: 6 months.
- Integration and system test evidence: 1 year.
- Certification evidence: 3 years (minimum).
- Security test evidence: 3 years.
- Performance benchmark evidence: 2 years.
- Golden dataset test evidence: Retained for as long as the golden dataset exists.

**Evidence integrity:** All evidence is stored with a cryptographic integrity hash.
The Evidence Manager verifies integrity at the time of storage and during any retrieval.

---

## 8.7 Review Process

**Daily:** Test infrastructure team reviews CI test results. Any new failures
are triaged within 24 hours.

**Weekly:** Component owners review their component's test pass rates and coverage.
Flaky tests identified this week are assigned to developers for resolution.

**Monthly:** Architecture Council reviews:
- TQS and SCS trends for all components.
- Coverage gaps report.
- Open governance violations.
- Certification requests and decisions.
- Evidence retention compliance.

**Quarterly:** Full framework review:
- Coverage threshold review.
- Dataset currency review (are datasets still representative?).
- Scenario coverage review (are all important scenarios defined?).
- Test category completeness review.

---

## 8.8 Audit Process

The testing framework itself is auditable. The following audit trails are maintained:

- All certification decisions (with evidence package reference).
- All golden dataset changes (with before/after comparison and approver).
- All coverage threshold changes (with justification and approver).
- All test retirements (with justification).
- All flaky test reports and their resolution.
- All governance exception decisions.

The audit trail is maintained in the Evidence Manager with the same integrity
guarantees as other evidence.

---

## 8.9 Ownership

**Architecture Council:** Owns the testing framework governance. Defines and maintains
coverage thresholds. Makes certification decisions. Approves golden dataset changes.

**Component Owners:** Own the tests for their respective IIOS engines. Responsible
for test quality, documentation, and coverage within their component.

**Platform Team:** Owns the testing infrastructure (the 18 framework components).
Responsible for CI/CD pipeline maintenance and test execution reliability.

**Security Team:** Owns all security-category tests. Reviews all authentication and
authorization test evidence as part of the certification process.

**Testing Champion:** A designated individual (Architecture Council member) who
advocates for testing quality across all components and tracks the overall TQS.

---

## 8.10 Continuous Improvement

The testing framework is continuously improved based on:

- **Defect escape analysis:** When a defect reaches production that should have
  been caught by tests, the framework is updated to prevent future escapes.
- **Post-incident reviews:** Every production incident includes a testing review:
  what test would have caught this? That test is added to the suite.
- **Developer experience feedback:** Friction in writing or running tests is
  addressed. If tests are painful to write, they will not be written.
- **Coverage gap analysis:** Regular review of coverage gaps leads to new tests.
- **Framework performance review:** Slow tests are optimized. A test suite that
  takes hours to run is a test suite that is not run frequently enough.

---

*End of Part VIII*

---

# PART IX — ENGINEERING CONSTITUTION

## 9.1 Constitution Purpose

The Engineering Constitution for the IIOS Testing Engineering Framework defines
110 binding rules across 12 categories. These rules apply to all IIOS tests,
test infrastructure, and testing practices.

Rules are identified by code: TST-[CATEGORY]-[NUMBER].

---

## 9.2 Category 1 — Correctness (TST-COR)

**TST-COR-001:** Every test must have exactly one defined expected outcome. A
test with multiple possible expected outcomes is a test of undefined behavior.

**TST-COR-002:** Tests must use specific, verifiable assertions. Assertions that
check "something changed" without specifying what is expected to change are
insufficient.

**TST-COR-003:** All financial calculation tests must verify results to the
defined precision. A test that accepts any value within 10% of expected is not
a correctness test.

**TST-COR-004:** Tests for boundary conditions must test the exact boundary value,
one below, and one above. Testing only "near" the boundary is insufficient.

**TST-COR-005:** Decision tests must verify both the decision outcome and its
rationale. A correct decision for the wrong reason is a defect.

**TST-COR-006:** Tests for error conditions must verify that the correct error type
and message are produced, not just that "some error occurred."

**TST-COR-007:** Tests for stateful components must verify the state after the
operation, not just the return value.

**TST-COR-008:** Golden dataset tests must be run on every commit to the component
under test. Skipping golden dataset tests in CI is a governance violation.

---

## 9.3 Category 2 — Repeatability (TST-REP)

**TST-REP-001:** Every test must produce the same result when run multiple times
without intervening code changes.

**TST-REP-002:** Tests must not share mutable state. Each test gets its own
completely independent fixture.

**TST-REP-003:** Tests must not depend on execution order. Running tests in any
order must produce the same results.

**TST-REP-004:** Tests must clean up all persistent state (database records,
files, open connections) after execution, even if the test fails.

**TST-REP-005:** Tests that require random behavior must seed the PRNG with a
fixed value. The seed must be recorded in the test evidence.

**TST-REP-006:** Tests that require time-dependent behavior must use the injectable
clock from the Date-Time Utility. The injected time must be recorded in the test evidence.

**TST-REP-007:** Flaky tests (tests that fail without a code change) are defects
and must be fixed within 14 days. Flaky tests are disabled until fixed.

**TST-REP-008:** Tests that are known to be environment-dependent must clearly
document those dependencies and must not be run in environments that do not
satisfy them.

---

## 9.4 Category 3 — Automation (TST-AUTO)

**TST-AUTO-001:** Every test that can be automated must be automated. Manual tests
are only permitted for exploratory testing and UX validation.

**TST-AUTO-002:** All automated tests run in CI/CD on every commit. No commit
reaches production without passing the full automated test suite.

**TST-AUTO-003:** Tests must not require manual steps to execute. A test that
requires a developer to click a button or type a value mid-execution is not automated.

**TST-AUTO-004:** Test environments are provisioned and deprovisioned automatically.
Tests must not depend on a manually configured environment.

**TST-AUTO-005:** Test results are automatically published to the Reporting Manager.
Manual result recording is not permitted.

**TST-AUTO-006:** The fail-fast principle is enforced automatically: if unit tests
fail, integration tests do not run.

**TST-AUTO-007:** Performance benchmarks run automatically as part of every deployment.
No manual benchmark execution is required.

**TST-AUTO-008:** Coverage analysis runs automatically after every test execution.
Coverage reports are automatically published to the Reporting Manager.

**TST-AUTO-009:** Evidence collection is automated. Manual evidence collection is
not permitted (it is not auditable).

---

## 9.5 Category 4 — Regression (TST-REG)

**TST-REG-001:** Every defect that is discovered and fixed must have a regression
test that would have prevented it. The regression test is added before the fix
is considered complete.

**TST-REG-002:** The regression test suite runs on every commit.

**TST-REG-003:** A regression (a previously passing test that now fails) is a
CRITICAL CI/CD failure. The commit that caused the regression is blocked from merging.

**TST-REG-004:** Safety-critical regressions (kill switch, position limits) trigger
an immediate deployment freeze. No deployments until the regression is resolved.

**TST-REG-005:** Golden dataset results are the canonical regression baseline.
Any change in golden dataset output must be reviewed before accepting.

**TST-REG-006:** Performance regressions (p99 latency increase > 20%) are blocking.
They must be investigated and resolved before deployment.

**TST-REG-007:** Regression test suite completion time is monitored. If the suite
takes longer to run than the defined budget (30 minutes for unit + component,
2 hours for full suite), it is optimized.

---

## 9.6 Category 5 — Certification (TST-CERT)

**TST-CERT-001:** No component is deployed to production without PRODUCTION-READY
certification. This is an absolute rule without exceptions.

**TST-CERT-002:** Certification evidence must be cryptographically signed.
Unsigned evidence is not accepted for certification.

**TST-CERT-003:** Certification decisions are made by the Architecture Council,
not by individual component owners.

**TST-CERT-004:** Certification evidence must include the dataset versions used.
A certification that does not identify its datasets cannot be reproduced and
is therefore invalid.

**TST-CERT-005:** Conditional certifications must have a defined resolution date.
Conditions that are not resolved by the specified date cause the certification
to be revoked.

**TST-CERT-006:** Certification is per-version. A new major version requires
a new certification. Minor and patch versions require a recertification check
(re-run affected tests; no full Architecture Council review unless HARD checks fail).

**TST-CERT-007:** Production certifications are valid for 90 days. After 90 days,
the component must pass a recertification check (run the full test suite; verify
no regressions; confirm evidence is current).

---

## 9.7 Category 6 — Coverage (TST-COV)

**TST-COV-001:** Coverage thresholds are minimum requirements, not targets.
Achieving the minimum threshold is the floor, not the ceiling.

**TST-COV-002:** All 15 coverage dimensions must be measured for every PRODUCTION
certification. Measuring only code coverage is insufficient.

**TST-COV-003:** A coverage dimension that drops below its minimum threshold is
a blocking certification failure.

**TST-COV-004:** Coverage trends are monitored over 90 days. A declining coverage
trend triggers a governance review, even if the current coverage is above threshold.

**TST-COV-005:** Decision Coverage and Risk Coverage (Dimensions 8 and 9) must
reach 1.0 for safety-critical components. Partial coverage of risk conditions
is not acceptable.

**TST-COV-006:** Adding new scenarios to the Scenario Manager without adding
corresponding tests is a governance violation.

**TST-COV-007:** Coverage that is achieved by tests that do not actually verify
correctness (tests without assertions) is not counted.

**TST-COV-008:** Scenario coverage requires that the scenario be tested at the
system level, not just at the unit test level.

---

## 9.8 Category 7 — Security (TST-SEC)

**TST-SEC-001:** All security test categories must produce PASS before PRODUCTION
certification. There are no acceptable partial passes for security.

**TST-SEC-002:** Security tests run on every commit, not just at certification time.

**TST-SEC-003:** Static analysis security scanning is automated and must complete
within the CI pipeline time budget.

**TST-SEC-004:** Dependency vulnerability scanning runs daily and on every build
that modifies dependencies.

**TST-SEC-005:** Security test evidence is retained for the full evidence retention
period (3 years).

**TST-SEC-006:** Security tests include injection attempt tests: SQL injection
(if applicable), log injection, path traversal, and XML injection.

**TST-SEC-007:** Authentication tests include token expiry, token refresh, and
authentication failure handling.

**TST-SEC-008:** Authorization tests include every defined access boundary: Telegram
command authorization, kill switch lift authorization, and configuration change
authorization.

**TST-SEC-009:** Audit log integrity tests must verify the full hash chain, not
just the most recent record.

**TST-SEC-010:** Any new security finding (from static analysis, dependency scan,
or security test) produces an alert to the Security Team within 1 hour of detection.

---

## 9.9 Category 8 — Performance (TST-PERF)

**TST-PERF-001:** Performance benchmarks are defined before a component reaches
STAGING-READY certification. Benchmarks are not defined retroactively.

**TST-PERF-002:** Benchmarks test p99 latency, not just mean latency. The tail
latency matters for trading cycle timing.

**TST-PERF-003:** Performance tests run under realistic concurrency, not in
single-threaded isolation.

**TST-PERF-004:** The performance test environment must match the production
environment specification. Performance tests on underprovisioned hardware produce
misleading results.

**TST-PERF-005:** Memory growth is measured and bounded during performance tests.
Unbounded memory growth is a performance defect.

**TST-PERF-006:** Performance tests include a warm-up phase. Cold-start latency
is measured separately from steady-state latency.

**TST-PERF-007:** Load tests run for the duration of a full trading day (6.25 hours).
Short load tests do not reveal memory leaks or gradual performance degradation.

**TST-PERF-008:** The full-cycle latency target (172ms) is tested as a system-level
performance test, not as an estimate from per-component benchmarks.

---

## 9.10 Category 9 — Evidence (TST-EVD)

**TST-EVD-001:** All test evidence must be collected automatically. Manually
assembled evidence packages are not accepted for certification.

**TST-EVD-002:** Evidence must include the complete test execution log, not just
the summary.

**TST-EVD-003:** Evidence must record the exact dataset version used. A certification
that cannot identify its datasets cannot be reproduced.

**TST-EVD-004:** Evidence is immutable after collection. Evidence that can be
modified after collection is not trustworthy.

**TST-EVD-005:** Evidence must include the environment specification (container
version, configuration hash, dependency versions).

**TST-EVD-006:** Performance evidence must include raw timing data (not just
averages), enabling retrospective analysis.

**TST-EVD-007:** Evidence packages are compressed and archived. The archive is
accessible for the full retention period without degradation.

---

## 9.11 Category 10 — Documentation (TST-DOC)

**TST-DOC-001:** Every test has documentation covering: purpose, scenario, dataset,
expected outcome, and pass criteria.

**TST-DOC-002:** Test documentation is updated when test behavior changes. A test
with outdated documentation is a governance violation.

**TST-DOC-003:** Regression tests must document the defect they prevent: the defect ID,
description, and the fix that was applied.

**TST-DOC-004:** Dataset documentation must explain the source, collection date, and
intended use of each dataset.

**TST-DOC-005:** Coverage gap documentation must explain why a gap exists (if
intentional) or assign an owner to close the gap (if unintentional).

**TST-DOC-006:** The testing framework's own documentation is maintained to the same
standard as the components it governs. An undocumented test framework is not
trustworthy.

---

## 9.12 Category 11 — Governance (TST-GOV)

**TST-GOV-001:** All tests must be registered. Unregistered tests are not managed,
not counted toward coverage, and do not produce certified evidence.

**TST-GOV-002:** Every test has an identified owner. Tests without owners within
30 days are retired.

**TST-GOV-003:** Coverage thresholds cannot be reduced without an Architecture Council
formal vote and documented justification.

**TST-GOV-004:** Golden dataset changes are auditable events. Every change to a
golden dataset is recorded with the before and after state.

**TST-GOV-005:** Governance exceptions (deviations from any TST rule) require
Architecture Council approval and are recorded in the governance audit trail.

**TST-GOV-006:** The testing framework itself (the 18 components) is subject to
the same governance standards. Each framework component has an owner, documentation,
and tests.

**TST-GOV-007:** Evidence tampering (modifying evidence after collection) is a
security incident and is investigated as such.

---

## 9.13 Category 12 — Continuous Testing (TST-CONT)

**TST-CONT-001:** The regression smoke test suite runs daily in production.
Any new failure triggers an immediate alert.

**TST-CONT-002:** Production health metrics that correspond to tested behaviors
are monitored continuously. A declining metric is treated as a potential test failure.

**TST-CONT-003:** New defect reports (from production incidents) trigger test
creation within 48 hours. The test is added to the regression suite within 72 hours.

**TST-CONT-004:** Coverage is measured continuously, not only at certification time.
Coverage reports are available at any time.

**TST-CONT-005:** Test suite execution time is monitored. A test suite that is
too slow to run on every commit will be run less frequently, reducing quality.

**TST-CONT-006:** Chaos testing runs monthly in the staging environment. Results
are reviewed by the Architecture Council.

**TST-CONT-007:** The TQS is reported weekly to the Architecture Council. Declining
TQS trends are addressed within one sprint.

**TST-CONT-008:** After every production incident, a testing review is conducted:
what test would have detected this? The test is added within 72 hours.

---

*End of Part IX*

---
# PART X — READINESS CHECKLIST

## 10.1 Readiness Framework

The Readiness Checklist is the formal evaluation gate for IIOS component
certification. Each check is classified as HARD (blocking) or SOFT (advisory).

---

## 10.2 Domain 1 — Environment Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 1.1 | Test environment provisioned | HARD | CI/CD environment running and verified |
| 1.2 | Production-equivalent configuration | HARD | Test environment matches production specification |
| 1.3 | Isolation verified | HARD | Test environment cannot reach production systems |
| 1.4 | Resource limits configured | HARD | CPU, memory, disk limits match production |
| 1.5 | Network policies applied | HARD | Network access restricted as in production |
| 1.6 | Container health checks passing | HARD | All containers in test environment are healthy |
| 1.7 | Data feeds connected (mock) | HARD | Mock data feeds responding correctly |
| 1.8 | Broker mock configured | HARD | Mock broker responding with defined behavior |
| 1.9 | Database seeded | HARD | Test databases in required initial state |
| 1.10 | Clock injectable | HARD | Date-Time Utility injectable clock confirmed working |

---

## 10.3 Domain 2 — Dataset Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 2.1 | Reference datasets present | HARD | All reference datasets in Dataset Manager |
| 2.2 | Historical datasets present | HARD | Required historical date ranges available |
| 2.3 | Golden datasets present | HARD | Golden datasets for all components |
| 2.4 | Edge-case datasets present | HARD | Edge-case datasets covering all boundaries |
| 2.5 | Failure datasets present | HARD | All failure scenarios have datasets |
| 2.6 | Dataset integrity verified | HARD | All dataset hashes verified |
| 2.7 | Dataset versions recorded | HARD | All dataset versions documented |
| 2.8 | Synthetic datasets validated | SOFT | Synthetic datasets are statistically plausible |
| 2.9 | Certification datasets compiled | HARD | Certification datasets assembled and locked |
| 2.10 | Dataset access controls applied | HARD | Live datasets restricted to authorized contexts |

---

## 10.4 Domain 3 — Test Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 3.1 | All tests registered | HARD | No unregistered tests in the suite |
| 3.2 | All tests have owners | HARD | Every test has an identified owner |
| 3.3 | All tests have documentation | HARD | All required documentation fields present |
| 3.4 | No flaky tests | HARD | Zero flaky tests in the suite |
| 3.5 | No blocked tests | HARD | Zero tests in BLOCKED status without justification |
| 3.6 | All test categories covered | HARD | All applicable test categories have tests |
| 3.7 | Safety tests registered | HARD | Kill switch, risk limit tests all registered |
| 3.8 | All 14 scenarios covered | HARD | All named scenarios have at least one test |
| 3.9 | Regression suite current | HARD | Regression suite includes all recent defect tests |
| 3.10 | Test execution time within budget | SOFT | Unit+component suite runs in < 30 minutes |

---

## 10.5 Domain 4 — Coverage Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 4.1 | Code coverage >= threshold | HARD | >= 95% line, >= 90% branch |
| 4.2 | Module coverage = 1.0 | HARD | All 18 engines covered |
| 4.3 | Service coverage >= 0.95 | HARD | >= 95% of public interfaces covered |
| 4.4 | Workflow coverage = 1.0 | HARD | All 12 workflows tested |
| 4.5 | Decision coverage = 1.0 | HARD | All 8 decision outcomes tested |
| 4.6 | Risk coverage = 1.0 | HARD | All defined risk conditions tested |
| 4.7 | Scenario coverage = 1.0 | HARD | All 14 named scenarios tested |
| 4.8 | SCS >= 0.92 | HARD | System Coverage Score above threshold |
| 4.9 | Coverage trends documented | SOFT | Coverage trends for last 90 days recorded |
| 4.10 | Coverage gap justifications | SOFT | All gaps below threshold have documented justification |

---

## 10.6 Domain 5 — Evidence Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 5.1 | All evidence collected | HARD | Evidence package complete for all test categories |
| 5.2 | Evidence integrity hashed | HARD | All evidence items have integrity hashes |
| 5.3 | Evidence signed | HARD | Evidence package signed by Evidence Manager |
| 5.4 | Dataset versions in evidence | HARD | All evidence records include dataset versions |
| 5.5 | Environment spec in evidence | HARD | Evidence includes full environment specification |
| 5.6 | Timing data in evidence | HARD | Raw timing data included for performance tests |
| 5.7 | Security evidence present | HARD | SAST results, dependency scan results included |
| 5.8 | Golden test evidence present | HARD | Evidence from all golden dataset tests included |
| 5.9 | Evidence retention confirmed | HARD | Evidence storage meets retention period requirements |
| 5.10 | Evidence access restricted | HARD | Evidence accessible only to authorized roles |

---

## 10.7 Domain 6 — Regression Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 6.1 | Regression baseline set | HARD | Previous certified results set as baseline |
| 6.2 | No open regressions | HARD | Zero tests failing that passed in baseline |
| 6.3 | Performance baseline set | HARD | Performance benchmarks from previous version recorded |
| 6.4 | No performance regressions | HARD | No benchmark regresses > 20% from baseline |
| 6.5 | Golden dataset baseline current | HARD | Golden outputs from current version verified |
| 6.6 | Regression run history clean | HARD | No regressions in last 5 regression runs |
| 6.7 | Regression suite documented | SOFT | Each regression test references its source defect |
| 6.8 | Safety regression alert confirmed | HARD | Kill switch regression alert was tested and works |

---

## 10.8 Domain 7 — Certification Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 7.1 | TQS >= threshold | HARD | TQS >= 0.90 for PRODUCTION |
| 7.2 | SCS >= threshold | HARD | SCS >= 0.92 for PRODUCTION |
| 7.3 | All HARD checks PASS | HARD | Zero HARD check failures |
| 7.4 | SOFT check plan in place | HARD | All SOFT failures have owner and target date |
| 7.5 | Architecture Council review scheduled | HARD | Review meeting date confirmed |
| 7.6 | Evidence package assembled | HARD | Complete evidence package submitted |
| 7.7 | 30-day stability verified | HARD | PRODUCTION: 30 days in STAGING-READY with no incidents |
| 7.8 | Security review complete | HARD | Security Team has reviewed and signed off |
| 7.9 | Component owner acceptance | HARD | Owner has formally accepted all responsibilities |
| 7.10 | Prior certification issues resolved | HARD | All conditions from prior certifications closed |

---

## 10.9 Domain 8 — Operational Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 8.1 | Health checks verified | HARD | All components respond to health probes |
| 8.2 | Monitoring alerts configured | HARD | All alert rules defined and tested |
| 8.3 | Dashboard verified | HARD | All dashboard values match underlying data |
| 8.4 | Log format verified | HARD | All log events in correct structured format |
| 8.5 | Recovery tests passed | HARD | All recovery scenarios tested and passing |
| 8.6 | Operational procedures documented | SOFT | Runbook covers all common failure scenarios |
| 8.7 | Alert delivery tested | HARD | Telegram alerts delivered within 5-second SLA |
| 8.8 | Kill switch test passed | HARD | Kill switch activation tested in staging |
| 8.9 | Container restart test passed | HARD | Restart recovery tested with no data loss |
| 8.10 | Operations team briefed | SOFT | Operations team has reviewed the runbook |

---

## 10.10 Domain 9 — Deployment Ready

| # | Check | Type | Criteria |
|---|-------|------|---------|
| 9.1 | Deployment package complete | HARD | All deployment artifacts present |
| 9.2 | Rollback plan documented | HARD | Rollback procedure documented and tested |
| 9.3 | Deployment checklist prepared | HARD | Step-by-step deployment checklist ready |
| 9.4 | Change notification sent | HARD | All consuming components notified of changes |
| 9.5 | Feature flags configured | SOFT | Feature flags set for progressive rollout |
| 9.6 | Post-deployment verification plan | HARD | Post-deployment smoke test plan documented |
| 9.7 | Monitoring alert thresholds confirmed | HARD | Production thresholds match staging-verified values |
| 9.8 | CI/CD pipeline verified | HARD | Deployment pipeline passes dry run |
| 9.9 | Architecture Council sign-off | HARD | Written approval from Architecture Council |
| 9.10 | Evidence archive confirmed | HARD | All certification evidence archived before deployment |

---

## 10.11 Testing Certification Matrix

`
LEVEL               PASS ALL  SCS   TQS   COV   STAB    SEC    COUNCIL
                    HARD CHK  MIN   MIN   MIN   PERIOD  REVIEW VOTE

EXPERIMENTAL        No        0.30  0.30  50%   None    No     Ack
TESTABLE            No        0.50  0.50  70%   None    No     Ack
INTEGRATION-READY   Yes       0.70  0.65  85%   None    No     Approve
STAGING-READY       Yes       0.82  0.80  90%   7 days  Layer3 Approve
PRODUCTION-READY    Yes       0.92  0.90  95%   30 days Always Vote
`

---

*End of Part X*

---

# SUPPLEMENT A — TESTING CATALOG REFERENCE

## A.1 All 47 Testing Categories

| # | Category | Group | Primary Owner | Applies To |
|---|---------|-------|---------------|------------|
| 1 | Unit Testing | Structural | Component Owners | All modules |
| 2 | Component Testing | Structural | Component Owners | All engines |
| 3 | Module Testing | Structural | Component Owners | All layers |
| 4 | Subsystem Testing | Structural | Architecture Council | All pipelines |
| 5 | System Testing | Structural | Platform Team | Full IIOS |
| 6 | Integration Testing | Integration | Component Owners | All boundaries |
| 7 | Interface Testing | Integration | Architecture Council | Critical interfaces |
| 8 | Contract Testing | Integration | Component Owners | Data contracts |
| 9 | Repository Testing | Integration | Platform Team | All databases |
| 10 | Configuration Testing | Integration | Platform Team | config.py, YAMLs |
| 11 | Database Testing | Data | Platform Team | All SQLite DBs |
| 12 | Schema Testing | Data | Platform Team | All schemas |
| 13 | Migration Testing | Data | Platform Team | All migrations |
| 14 | Data Integrity Testing | Data | Platform Team | All data stores |
| 15 | Ontology Testing | Data | Engine Owners | Market ontology |
| 16 | Knowledge Testing | Data | Engine Owners | Knowledge base |
| 17 | Relationship Testing | Data | Platform Team | All entity relationships |
| 18 | Observation Testing | Behavioral | Platform Team | All engines |
| 19 | Event Testing | Behavioral | Platform Team | Event Bus |
| 20 | Decision Testing | Behavioral | Engine Owners | Decision Engine |
| 21 | Reasoning Testing | Behavioral | Engine Owners | AI agents |
| 22 | Learning Testing | Behavioral | Engine Owners | Learning Engine |
| 23 | AI Agent Testing | Behavioral | Engine Owners | 5 debate agents |
| 24 | Prompt Testing | Behavioral | Engine Owners | LLM prompts |
| 25 | LLM Evaluation | Behavioral | Engine Owners | LLM outputs |
| 26 | Backtesting Validation | Financial | Engine Owners | Backtesting engine |
| 27 | Simulation Testing | Financial | Engine Owners | Monte Carlo engine |
| 28 | Historical Replay Testing | Financial | Platform Team | Replay pipeline |
| 29 | Strategy Testing | Financial | Engine Owners | Strategy library |
| 30 | Performance Testing | Performance | Platform Team | All components |
| 31 | Load Testing | Performance | Platform Team | Full system |
| 32 | Stress Testing | Performance | Platform Team | Full system |
| 33 | Scalability Testing | Performance | Architecture Council | Full system |
| 34 | Concurrency Testing | Performance | Platform Team | Shared-state components |
| 35 | Thread Safety Testing | Performance | Platform Team | Thread-safe components |
| 36 | Memory Testing | Performance | Platform Team | All long-running |
| 37 | Latency Testing | Performance | Platform Team | Critical path |
| 38 | Security Testing | Security | Security Team | All components |
| 39 | Authentication Testing | Security | Security Team | Auth components |
| 40 | Authorization Testing | Security | Security Team | Access control |
| 41 | Recovery Testing | Security | Platform Team | All recovery paths |
| 42 | Failure Injection Testing | Security | Platform Team | All components |
| 43 | Chaos Testing | Security | Platform Team | Staging only |
| 44 | Disaster Recovery Testing | Security | Platform Team | Full system |
| 45 | Resilience Testing | Security | Platform Team | Full system |
| 46 | Operational Testing | Operational | Operations Team | Control systems |
| 47 | Acceptance Testing | Operational | Architecture Council | Full system |

---

# SUPPLEMENT B — COVERAGE MATRIX

## B.1 Coverage Requirements by Certification Level

| Coverage Dimension | STAGING-READY | PRODUCTION-READY | Safety-Critical |
|-------------------|---------------|-----------------|----------------|
| Code Coverage | >= 0.85 | >= 0.95 | >= 0.98 (MC/DC) |
| Module Coverage | >= 0.90 | = 1.00 | = 1.00 |
| Service Coverage | >= 0.85 | >= 0.95 | = 1.00 |
| Workflow Coverage | >= 0.80 | = 1.00 | = 1.00 |
| Ontology Coverage | >= 0.70 | >= 0.90 | N/A |
| Knowledge Coverage | >= 0.70 | >= 0.85 | N/A |
| Reasoning Coverage | >= 0.75 | >= 0.90 | N/A |
| Decision Coverage | >= 0.90 | = 1.00 | = 1.00 |
| Risk Coverage | >= 0.90 | = 1.00 | = 1.00 |
| Event Coverage | >= 0.80 | >= 0.90 | N/A |
| Observation Coverage | >= 0.75 | >= 0.85 | N/A |
| Relationship Coverage | >= 0.75 | >= 0.85 | N/A |
| Data Coverage | >= 0.80 | >= 0.90 | = 1.00 |
| Scenario Coverage | >= 0.90 | = 1.00 | = 1.00 |
| Operational Coverage | >= 0.70 | >= 0.80 | N/A |

---

# SUPPLEMENT C — DATASET CATALOG

## C.1 Dataset Summary

| # | Type | Usage | Governance Tier | Access Level |
|---|------|-------|----------------|-------------|
| 1 | Reference | Correctness testing | Owner + Council | Dev and Test |
| 2 | Historical | Backtesting, replay | Council | Test only |
| 3 | Synthetic | Volume, scenario | Owner | Dev and Test |
| 4 | Live | Acceptance testing | Council | Test (staging) only |
| 5 | Replay | Historical replay | Platform Team | Test only |
| 6 | Benchmark | Performance testing | Council | Test (fixed) |
| 7 | Training | Model training | Council | AI team only |
| 8 | Validation | Model evaluation | Council | AI team only |
| 9 | Golden | Regression testing | Council | Test (locked) |
| 10 | Edge-case | Boundary testing | Owner | Dev and Test |
| 11 | Failure | Error scenario testing | Owner | Dev and Test |
| 12 | Corrupted | Recovery testing | Platform Team | Test only |
| 13 | Certification | Certification runs | Council | Test (locked) |

---

# SUPPLEMENT D — CERTIFICATION MATRIX

## D.1 Component Certification Status Template

| Component | Current Level | TQS | SCS | Last Certified | Expiry | Owner |
|-----------|--------------|-----|-----|----------------|--------|-------|
| GlobalIntelligence | [Status] | [Score] | [Score] | [Date] | [Date] | GI Team |
| MarketIntelligence | [Status] | [Score] | [Score] | [Date] | [Date] | MI Team |
| MetaLearning | [Status] | [Score] | [Score] | [Date] | [Date] | ML Team |
| OpportunityEngine | [Status] | [Score] | [Score] | [Date] | [Date] | OE Team |
| StrategyLab | [Status] | [Score] | [Score] | [Date] | [Date] | SL Team |
| CapitalRiskEngine | [Status] | [Score] | [Score] | [Date] | [Date] | CRE Team |
| RiskControl | [Status] | [Score] | [Score] | [Date] | [Date] | RC Team |
| MarketSimulation | [Status] | [Score] | [Score] | [Date] | [Date] | SIM Team |
| RiskGuardian | [Status] | [Score] | [Score] | [Date] | [Date] | Council |
| DebateAndDecision | [Status] | [Score] | [Score] | [Date] | [Date] | DEC Team |
| ExecutionEngine | [Status] | [Score] | [Score] | [Date] | [Date] | EX Team |
| TradeMonitoring | [Status] | [Score] | [Score] | [Date] | [Date] | TM Team |
| LearningSystem | [Status] | [Score] | [Score] | [Date] | [Date] | LS Team |
| PerformanceAnalytics | [Status] | [Score] | [Score] | [Date] | [Date] | PA Team |
| ResearchLab | [Status] | [Score] | [Score] | [Date] | [Date] | RL Team |
| ValidationEngine | [Status] | [Score] | [Score] | [Date] | [Date] | VE Team |
| ControlTower | [Status] | [Score] | [Score] | [Date] | [Date] | CT Team |

---

# SUPPLEMENT E — FAILURE TAXONOMY

## E.1 Test Failure Classification

| Class | Code | Description | Response Time | Blocking |
|-------|------|-------------|---------------|---------|
| Safety failure | TST-FAIL-SAFETY | Kill switch or risk limit test fails | Immediate | Yes — deploy freeze |
| Security failure | TST-FAIL-SEC | Any security test category fails | 4 hours | Yes — deploy blocked |
| Performance regression | TST-FAIL-PERF | Benchmark regresses > 20% | 24 hours | Yes — deploy blocked |
| Golden dataset mismatch | TST-FAIL-GOLDEN | Output changed from golden | 24 hours | Yes — review required |
| Regression | TST-FAIL-REG | Previously passing test now fails | 24 hours | Yes — fix required |
| Coverage deficit | TST-FAIL-COV | Coverage drops below threshold | 48 hours | Yes for cert |
| Flaky test | TST-FAIL-FLAKY | Test passes and fails intermittently | 14 days | No (disabled) |
| Infrastructure failure | TST-FAIL-INFRA | Test environment failure, not code | 2 hours | No |
| Blocked test | TST-FAIL-BLOCK | Test cannot run (missing dependency) | 48 hours | No |
| Documentation missing | TST-FAIL-DOC | Test lacks required documentation | 30 days | For cert only |

---

# SUPPLEMENT F — QUALITY SCORE REFERENCE

## F.1 TQS Score Bands

| TQS Band | Description | Certification Eligibility |
|----------|-------------|--------------------------|
| 0.95 – 1.00 | Exceptional | PRODUCTION-READY eligible |
| 0.90 – 0.94 | Production-grade | PRODUCTION-READY eligible |
| 0.80 – 0.89 | Staging-grade | STAGING-READY eligible |
| 0.65 – 0.79 | Integration-grade | INTEGRATION-READY eligible |
| 0.50 – 0.64 | Testable | TESTABLE eligible |
| < 0.50 | Below standard | EXPERIMENTAL only |

## F.2 Metric Score Impact on TQS

Any of the following produces an automatic TQS floor:
- Pass Rate < 1.0 for safety tests: TQS capped at 0.80.
- Security Score < 1.0: TQS capped at 0.80.
- Performance Score < 1.0: TQS capped at 0.88.
- Decision Coverage < 1.0 for safety-critical components: TQS capped at 0.82.

---

# SUPPLEMENT G — TESTING ANTI-PATTERNS

## G.1 Eight Testing Anti-Patterns

### Anti-Pattern 1 — Testing Only the Happy Path

**Description:** Tests exercise only the normal, expected success path. Error
conditions, boundary values, and exceptional inputs are not tested.

**Problem:** The most defect-prone code is the error-handling code. Code that
handles unexpected inputs is exercised only in production, where defects are most
costly.

**Correct approach:** Every test suite explicitly includes: normal case, boundary
cases, error cases, and exceptional cases.

---

### Anti-Pattern 2 — Fragile Tests

**Description:** Tests are tightly coupled to the implementation — testing
internal details rather than observable behavior.

**Problem:** Any refactoring of the implementation breaks the tests, even when
the behavior is unchanged. Developers avoid refactoring to avoid breaking tests.

**Correct approach:** Tests verify observable behavior (inputs and outputs), not
implementation details.

---

### Anti-Pattern 3 — Test Without Assertions

**Description:** A test runs the code but does not assert anything. If the code
runs without throwing an exception, the test passes.

**Problem:** The test provides no coverage of correctness. It only verifies that
the code does not crash. It counts toward code coverage metrics but provides no
quality assurance.

**Correct approach:** Every test has at least one explicit assertion that verifies
the expected output.

---

### Anti-Pattern 4 — Non-Deterministic Test

**Description:** Tests use system time, random numbers, or shared global state,
producing different results on different runs.

**Problem:** Non-deterministic tests are not reproducible. A passing test today
may fail tomorrow for no apparent reason.

**Correct approach:** All time-dependent behavior uses the injectable clock. All
random behavior uses the seeded PRNG. All global state is reset before each test.

---

### Anti-Pattern 5 — Ignoring Flaky Tests

**Description:** Tests that fail intermittently are marked as "skip if flaky" or
disabled without investigation.

**Problem:** Flaky tests indicate real non-determinism in the code being tested.
Ignoring them allows the underlying non-determinism to persist.

**Correct approach:** Flaky tests are treated as defects. The root cause is
investigated and resolved within 14 days.

---

### Anti-Pattern 6 — Slow Unit Tests

**Description:** Unit tests are slow because they perform I/O operations (database
reads, file reads, network calls).

**Problem:** Slow tests are not run frequently. Tests that take 10 minutes to run
are run once a day at best, reducing their value for continuous quality assurance.

**Correct approach:** Unit tests are fast (milliseconds each). Any test that
performs I/O is an integration test, not a unit test, and is classified accordingly.

---

### Anti-Pattern 7 — Coverage Inflation

**Description:** Tests are written specifically to achieve a high code coverage
number without actually testing meaningful behavior.

**Problem:** High coverage with no meaningful assertions produces a false sense
of quality. The coverage metric shows green while the component is untested.

**Correct approach:** Coverage is measured alongside assertion quality. Tests
without meaningful assertions are flagged.

---

### Anti-Pattern 8 — Missing Recovery Tests

**Description:** Tests cover normal operation thoroughly but do not test recovery
from failures.

**Problem:** Systems fail in production, not in tests. A system that has never
been tested recovering from a database failure will fail uncontrollably when the
database fails in production.

**Correct approach:** Every defined recovery path has at least one test that
verifies the system recovers correctly within the specified RTO.

---

# SUPPLEMENT H — OPERATIONAL RUNBOOK

## H.1 Common Testing Operational Scenarios

### Scenario 1 — CI Pipeline Test Failure

**Indicators:** CI/CD build fails. New test failures detected that were not present
in the previous run.

**Operator Actions:**
1. Identify the failing tests from the CI report.
2. Classify: safety failure, regression, new defect, or infrastructure issue.
3. If safety failure: immediate notification to Architecture Council. Deploy freeze.
4. If regression: identify the commit that introduced the regression. Revert if needed.
5. If new defect: assign to component owner. Create a defect ticket.
6. If infrastructure: the Platform Team investigates the test environment.
7. Update the TQS after resolution.

---

### Scenario 2 — Golden Dataset Mismatch

**Indicators:** Golden dataset test fails. Output has changed from the expected
golden output.

**Operator Actions:**
1. Determine whether the behavior change was intentional (deliberate change in
   component behavior) or unintentional (regression).
2. If unintentional: treat as a regression. Find and fix the cause.
3. If intentional: Architecture Council must review the diff. If the new behavior
   is correct, the golden dataset is updated with approval.
4. Do not update the golden dataset without Architecture Council approval.
5. Record the decision in the governance audit trail.

---

### Scenario 3 — Coverage Drop Below Threshold

**Indicators:** Coverage Manager reports a coverage dimension dropped below threshold.
TQS drops.

**Operator Actions:**
1. Identify which coverage dimension dropped and by how much.
2. Identify the code changes that caused the drop (new code without corresponding tests).
3. Assign the coverage gap to the component owner for immediate action.
4. Block the next certification run until coverage is restored.
5. Review whether the new code is safety-critical (which requires immediate coverage).

---

### Scenario 4 — Flaky Test Discovery

**Indicators:** Regression Manager reports a test producing inconsistent results
across consecutive runs without code changes.

**Operator Actions:**
1. Disable the flaky test immediately (to prevent CI noise).
2. Assign the flaky test to its owner.
3. The owner investigates the root cause (usually non-deterministic inputs or
   shared mutable state).
4. The test is fixed and re-enabled within 14 days.
5. If the root cause is in the component code (not just the test), a defect is
   also created for the component.

---

### Scenario 5 — Certification Denied

**Indicators:** Architecture Council denies PRODUCTION-READY certification.
Component cannot be deployed to production.

**Operator Actions:**
1. Review the certification denial report. List all deficiencies.
2. Assign each deficiency to the responsible team.
3. Set a target date for re-application based on deficiency resolution timelines.
4. Address all HARD check failures first.
5. Rerun the full certification test suite after all deficiencies are addressed.
6. Resubmit the certification package to the Architecture Council.

---

# SUPPLEMENT I — COMPREHENSIVE GLOSSARY

| Term | Definition |
|------|-----------|
| Acceptance Testing | Testing that IIOS meets its defined acceptance criteria from the user perspective. |
| Architecture Council | Governing body that makes PRODUCTION certification decisions and owns the test framework. |
| Assertion | A statement in a test that verifies an expected condition; required in every test. |
| Backtesting Validation | Testing the correctness of the backtesting engine itself. |
| Benchmark | A standardized performance measurement used to detect performance regressions. |
| Certification | Formal declaration that a component meets defined testing standards for a lifecycle level. |
| Certification Dataset | The locked dataset used for certification runs. Cannot be modified without Council approval. |
| Chaos Testing | Randomly injecting failures to discover unanticipated failure modes. |
| CI/CD | Continuous Integration / Continuous Deployment — the automated pipeline for building and testing. |
| Component Testing | Testing a complete engine in isolation from external dependencies. |
| Contract Testing | Testing that data contracts between producers and consumers are honored by both parties. |
| Coverage Manager | Framework component measuring all 15 coverage dimensions. |
| Dataset Manager | Framework component managing all 13 test dataset types. |
| Decision Coverage | Coverage of all defined decision outcomes in the Decision Engine. |
| Determinism | Property of a test that produces the same result for the same input, every time. |
| Evidence Manager | Framework component collecting and preserving all test evidence. |
| Failure Injection Testing | Deliberately injecting failures to verify that failure handling works. |
| Fixture Manager | Framework component creating and managing test fixtures. |
| Flaky Test | A test that produces inconsistent results without code changes. Treated as a defect. |
| Fail Fast | Principle of stopping test execution early when a fundamental failure is detected. |
| Failure Rate | Rate at which new test failures are introduced per commit. |
| Golden Dataset | A dataset paired with known-correct outputs; used for regression detection. |
| HARD check | A readiness checklist item that is blocking. The component cannot advance without PASS. |
| Historical Dataset | Real historical market data used for backtesting and replay testing. |
| Integration Testing | Testing the interaction between two or more components. |
| Interface Testing | Testing that a component's published interface is correctly implemented and stable. |
| Kill Switch | Safety mechanism that halts trading when VIX > 45 or daily loss > 2%. |
| Latency Testing | Detailed measurement of latency for every component on the critical path. |
| Learning Testing | Testing that the learning engine correctly improves behavior from experience. |
| Load Testing | Testing system behavior under expected sustained load. |
| MC/DC | Modified Condition/Decision Coverage — required for safety-critical components. |
| Mock Manager | Framework component providing mock implementations of external dependencies. |
| Module Coverage | The percentage of IIOS engines that have all required test types registered. |
| Ontology Testing | Testing the correctness and consistency of the market domain ontology. |
| Pass Rate | Percentage of tests that passed in the most recent complete test run. |
| Performance Testing | Testing that components meet latency and throughput requirements. |
| Regression | A previously passing test that now fails — typically due to a code change. |
| Regression Manager | Framework component detecting and tracking test regressions. |
| Repeatability | The ability to run the same test multiple times and obtain the same result. |
| Replay Manager | Framework component managing historical data replay for decision regression testing. |
| Result Manager | Framework component collecting and storing all test execution results. |
| Risk Coverage | Coverage of all defined risk conditions and limits in the Risk Guardian. |
| Scenario Coverage | The percentage of named IIOS scenarios exercised by the test suite. |
| Scenario Manager | Framework component defining and providing the 14 named IIOS test scenarios. |
| SCS | System Coverage Score — weighted composite of all 15 coverage dimension scores. |
| Security Score | Composite of all security test category results. Partial pass is not acceptable. |
| SOFT check | A readiness checklist item that is advisory; must be resolved within 30 days. |
| Stress Testing | Testing system behavior at and beyond maximum rated load. |
| System Testing | Testing the complete IIOS system end-to-end in a production-equivalent environment. |
| Test Catalog | Human-readable, searchable documentation of all tests. |
| Test Manager | Framework component managing test registration and lifecycle. |
| Test Registry | Authoritative catalog of all registered IIOS tests. |
| Test Scheduler | Framework component executing tests at the right times and in the right order. |
| TMM | Testing Maturity Model — five levels from Initial (1) to Optimizing (5). |
| TQS | Testing Quality Score — weighted composite of 12 testing quality metrics. |
| Unit Testing | Testing individual functions in complete isolation from external dependencies. |
| Validation | Verifying that the specification meets the actual need ("building the right thing"). |
| Verification | Verifying that the implementation conforms to its specification ("building it right"). |

---

# DOCUMENT METRICS

| Attribute | Value |
|-----------|-------|
| Document Code | IIOS-TST-ENG-001 |
| Framework Version | 1.0.0 |
| Document Status | Active |
| Total Parts | 10 |
| Total Supplements | 9 (A through I) |
| Total Testing Categories | 47 |
| Total Framework Components | 18 |
| Total Testing Groups | 8 |
| Total Lifecycle Stages | 12 |
| Total Dataset Types | 13 |
| Total Coverage Dimensions | 15 |
| Total Quality Metric Categories | 12 |
| Total Constitution Rules | 110 |
| Total Readiness Checks | 79 HARD + 11 SOFT = 90 total |
| Total Certification Levels | 6 |
| Total Named Scenarios | 14 |
| Total Failure Classes | 10 |
| Total Anti-Patterns | 8 |
| Total Operational Scenarios | 5 |
| Total Glossary Entries | 52 |

---

# AMENDMENT HISTORY

| Version | Date | Author | Change Description |
|---------|------|--------|-------------------|
| 1.0.0 | 2026-07-04 | Architecture Council | Initial publication |

---

# CLOSING STATEMENT

This document — the Testing Engineering Framework for the Investment Intelligence
Operating System (IIOS), bearing document code IIOS-TST-ENG-001 — is the complete,
authoritative specification for how every component, module, service, pipeline,
AI agent, reasoning engine, decision engine, database, workflow, and integration
of IIOS is verified before deployment and monitored continuously in production.

The framework rests on a foundational understanding: in a system that manages
real capital in live markets, every component's correctness is a financial safety
requirement. Untested components are unknown risks. Tested components are measured
risks. The purpose of this framework is to transform unknown risk into measured,
documented, and bounded risk.

The 47 testing categories provide comprehensive coverage. The 18 architecture
components provide the infrastructure. The 12-stage lifecycle ensures every test
is born intentionally and maintained throughout its useful life. The 15 coverage
dimensions ensure that no aspect of the system is left unexamined. The 110-rule
Engineering Constitution provides the law. The 90-check readiness certification
provides the proof.

No component reaches production without evidence. No evidence is accepted without
integrity. No certification is granted without the Architecture Council's review.
No kill switch is deployed without exhaustive adversarial testing.

This is how IIOS earns the right to operate with real capital.

---

*IIOS-TST-ENG-001 / Version 1.0.0 / Status: Active*
*Testing Engineering Framework — Investment Intelligence Operating System*
*Architecture Council Approved*

---

# EXTENDED SUPPLEMENT — IIOS COMPONENT TEST SPECIFICATIONS

## EX.1 Purpose

This extended supplement provides detailed test specifications for each of the
18 IIOS engines. For every engine, this section defines: the required test
categories, the minimum test counts per category, the critical scenarios that
must be covered, and the specific certification requirements.

---

## EX.2 Layer 1 — GlobalIntelligence Engine

**Engine Code:** GI
**Risk Score:** 8/10 (failure degrades all subsequent layers)
**TMM Target:** Level 4

**Required test categories:**
- Unit Testing: minimum 40 tests.
- Component Testing: minimum 15 tests.
- Integration Testing: minimum 10 tests.
- Performance Testing: minimum 5 benchmark scenarios.
- Recovery Testing: minimum 3 scenarios.
- Configuration Testing: minimum 5 tests.

**Critical scenarios that must be covered:**
- Normal market open (standard data available from all global sources).
- Data source unavailable (one or more of S&P, Nikkei, bonds, FX unavailable).
- 5-minute cache hit (fetch returns cached data without network call).
- Background pre-warm thread populates cache before market open.
- Force-refresh mode (cache is bypassed when force=True).
- Stale data detection (cache returns stale data; freshness check triggers refresh).
- All 7 global market sources unavailable simultaneously (graceful degradation).

**Performance requirements:**
- Cached fetch: <= 5ms p99.
- Non-cached fetch: <= 17ms p99 (current baseline, must not regress).
- Background pre-warm completion: <= 12,000ms (CRIT threshold).

**Certification note:** GlobalIntelligence must achieve PRODUCTION-READY status
before any engine in Layer 2 can be certified at PRODUCTION-READY.

---

## EX.3 Layer 2 — MarketIntelligence Engine

**Engine Code:** MI
**Risk Score:** 8/10 (regime mis-classification affects all strategy selection)
**TMM Target:** Level 4

**Required test categories:**
- Unit Testing: minimum 50 tests.
- Component Testing: minimum 20 tests.
- Integration Testing: minimum 15 tests (with GlobalIntelligence).
- Decision Testing: minimum 10 regime classification tests.
- Performance Testing: minimum 5 benchmark scenarios.

**Critical scenarios that must be covered:**
- NIFTY trending up, breadth positive, low VIX (bull regime).
- NIFTY trending down, breadth negative, elevated VIX (bear regime).
- VIX spike (regime transition detection).
- Range-bound market (consolidation regime).
- Expiry week liquidity changes.
- Market breadth indicator computation from multiple inputs.
- Sector rotation detection.
- Liquidity regime classification.
- Market holiday handling (no data expected).
- Continuous scan mode (30-second interval validation).

**Performance requirements:**
- Full analysis cycle: <= 19ms p99 (current baseline).
- Continuous scan: must complete within 30-second window.

---

## EX.4 Layer 3 — MetaLearning Engine

**Engine Code:** ML
**Risk Score:** 7/10 (incorrect strategy weights degrade decision quality)
**TMM Target:** Level 4

**Required test categories:**
- Unit Testing: minimum 35 tests.
- Component Testing: minimum 12 tests.
- Learning Testing: minimum 15 tests.
- Integration Testing: minimum 8 tests.
- Performance Testing: minimum 3 benchmark scenarios.

**Critical scenarios that must be covered:**
- K-NN prediction for all 5 defined market regimes.
- Strategy weight update after profitable trade.
- Strategy weight update after unprofitable trade.
- Cold start (no historical data; default weights applied).
- Regime transition (weights shift when regime changes).
- Strategy weight persistence across restart.
- Strategy weight convergence (weights stabilize with sufficient data).

---

## EX.5 Layer 4 — OpportunityEngine

**Engine Code:** OE
**Risk Score:** 6/10
**TMM Target:** Level 3

**Required test categories:**
- Unit Testing: minimum 40 tests.
- Component Testing: minimum 15 tests.
- Integration Testing: minimum 10 tests.
- Strategy Testing: minimum 20 equity scan scenarios.

**Critical scenarios that must be covered:**
- Equity scanner finds candidates above threshold.
- Equity scanner finds no candidates (market regime not suitable).
- Options opportunity detection.
- Arbitrage detection.
- Symbol normalization (NIFTY → bare; stocks → .NS suffix applied).
- Scanner with degraded data feed (fallback behavior).

---

## EX.6 Layer 5 — StrategyLab

**Engine Code:** SL
**Risk Score:** 8/10 (incorrect strategy selection directly affects trade quality)
**TMM Target:** Level 5 (safety-critical)

**Required test categories:**
- Unit Testing: minimum 60 tests.
- Component Testing: minimum 20 tests.
- Strategy Testing: minimum 30 scenarios.
- Backtesting Validation: minimum 10 scenarios.
- Integration Testing: minimum 12 tests.
- Performance Testing: minimum 5 benchmark scenarios.

**Critical scenarios that must be covered:**
- MetaStrategyController selects appropriate strategy for each regime.
- Evolved strategy loaded with correct parameters from JSON.
- Strategy with min_signal_rr filtering applied correctly.
- Strategy filtered by OHS threshold (disabled strategies not selected).
- Walk-forward testing validation.
- Strategy evolution producing valid offspring.
- Promotion gate enforcement (WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%).
- Strategy with no active strategies (graceful handling).

**Certification note:** StrategyLab requires security review in addition to standard
certification because evolved strategy JSON files are loaded from disk and could
in theory be tampered with.

---

## EX.7 Layer 6 — CapitalRiskEngine

**Engine Code:** CRE
**Risk Score:** 9/10 (incorrect position sizing creates direct financial risk)
**TMM Target:** Level 5 (safety-critical)

**Required test categories:**
- Unit Testing: minimum 50 tests.
- Component Testing: minimum 15 tests.
- Integration Testing: minimum 10 tests.
- Security Testing: minimum 5 tests.

**Critical scenarios that must be covered:**
- Position sizing at normal allocation.
- Position sizing at maximum allocation (position limit reached exactly).
- Position sizing rejected (over limit).
- Portfolio allocation across multiple strategies.
- Capital allocation with different strategy budget fractions.
- Position sizing with zero available capital.
- Allocation with one strategy active vs multiple strategies active.

---

## EX.8 Layer 7 — RiskControl

**Engine Code:** RC
**Risk Score:** 9/10 (risk control failures create direct financial exposure)
**TMM Target:** Level 5 (safety-critical)

**Required test categories:**
- Unit Testing: minimum 60 tests.
- Component Testing: minimum 20 tests.
- Integration Testing: minimum 15 tests.
- Security Testing: minimum 5 tests.

**Critical scenarios that must be covered:**
- Portfolio allocation within all risk limits.
- Portfolio allocation at maximum drawdown limit exactly.
- Portfolio allocation exceeds stress test threshold.
- Stress test failure (Monte Carlo VaR exceeds limit).
- Portfolio rebalancing under changing market conditions.
- Risk check cascade (multiple risk conditions simultaneously).

---

## EX.9 Layer 9 — RiskGuardian

**Engine Code:** RG
**Risk Score:** 10/10 (kill switch failure is the highest possible risk)
**TMM Target:** Level 5 (safety-critical, mandatory MC/DC coverage)

**Required test categories:**
- Unit Testing: minimum 80 tests (most comprehensive in the system).
- Component Testing: minimum 25 tests.
- Integration Testing: minimum 20 tests.
- Security Testing: minimum 10 tests.
- Failure Injection Testing: minimum 15 scenarios.
- Concurrency Testing: minimum 5 scenarios.

**Critical scenarios that must be covered (all 15 are HARD requirements):**
1. VIX exactly at 45.0 (kill switch triggers).
2. VIX at 44.9 (kill switch does not trigger).
3. VIX at 45.1 (kill switch triggers).
4. Daily loss exactly at 2.0% (kill switch triggers).
5. Daily loss at 1.99% (kill switch does not trigger).
6. Daily loss at 2.01% (kill switch triggers).
7. Kill switch is already active (re-trigger is idempotent).
8. Kill switch trigger while another engine is failing.
9. Kill switch trigger under concurrent access from multiple threads.
10. Kill switch state persists across restart.
11. Kill switch lift by authorized operator.
12. Kill switch lift attempt by unauthorized caller (rejected).
13. Kill switch state triple-persistence (all three persistence locations are checked).
14. Kill switch trigger when database is unavailable (alert still sent).
15. Kill switch trigger when Telegram bot is unavailable (system still halts).

**Coverage requirement:** MC/DC coverage for all Boolean conditions in the kill switch
trigger logic.

---

## EX.10 Layer 10 — DebateAndDecision

**Engine Code:** DEC
**Risk Score:** 9/10 (decision quality directly determines trade quality)
**TMM Target:** Level 5

**Required test categories:**
- Unit Testing: minimum 50 tests.
- Component Testing: minimum 20 tests.
- Decision Testing: minimum 20 scenarios.
- AI Agent Testing: minimum 10 tests per agent (50 total).
- Integration Testing: minimum 15 tests.
- Performance Testing: minimum 5 benchmark scenarios.

**Critical scenarios that must be covered:**
- All 8 decision outcomes (as defined in Coverage Dimension 8).
- Score exactly at threshold 6.5 (APPROVE boundary test).
- Score at 6.4 (REJECT — just below threshold).
- Score at 6.6 (APPROVE — just above threshold).
- Debate with incomplete data (some agents cannot produce scores).
- Debate with conflicting agent scores (test consensus algorithm).
- Decision with active kill switch (always REJECT_KILL_SWITCH regardless of score).

---

## EX.11 Layer 11 — ExecutionEngine

**Engine Code:** EX
**Risk Score:** 10/10 (execution errors create direct financial consequences)
**TMM Target:** Level 5 (safety-critical)

**Required test categories:**
- Unit Testing: minimum 60 tests.
- Component Testing: minimum 20 tests.
- Integration Testing: minimum 20 tests.
- Security Testing: minimum 10 tests.
- Concurrency Testing: minimum 10 scenarios.

**Critical scenarios that must be covered:**
- Paper trading order placed and journaled correctly.
- Order idempotency (same order ID submitted twice; second is rejected).
- Broker rejection handling (order rejected by broker).
- Broker unavailable (circuit breaker activates).
- PAPER_TRADING flag is true (no live orders are sent).
- PAPER_TRADING flag is false (live orders are sent to broker).
- Order manager restart with existing journal (state reconstructed correctly).
- Position count after restart matches journal records.
- Concurrent order placement (race condition prevention).
- Maximum position limit enforcement.

---

## EX.12 Layer 13 — LearningSystem

**Engine Code:** LS
**Risk Score:** 7/10
**TMM Target:** Level 4

**Required test categories:**
- Unit Testing: minimum 45 tests.
- Component Testing: minimum 15 tests.
- Learning Testing: minimum 20 tests.
- Integration Testing: minimum 10 tests.

**Critical scenarios that must be covered:**
- Win rate computation from trade history.
- Auto-disable at win rate governance threshold.
- Win rate computation across multiple trading days.
- EOD learning cycle with zero trades (graceful handling).
- EOD learning cycle recovery (recovering CSV-closed trades from today).
- Strategy attribute lookup (strategy field over strategy_name).
- Performance tracker persistence (state survives restart).

---

## EX.13 Layer 17 — ControlTower

**Engine Code:** CT
**Risk Score:** 7/10 (monitoring failure is not directly a financial risk but is
an operational risk — problems go undetected)
**TMM Target:** Level 4

**Required test categories:**
- Unit Testing: minimum 30 tests.
- Component Testing: minimum 10 tests.
- Integration Testing: minimum 15 tests.
- Observation Testing: minimum 20 tests.
- Operational Testing: minimum 15 tests.

**Critical scenarios that must be covered:**
- Streamlit dashboard receives and displays correct data.
- SQLite telemetry database writes correct records.
- Event Bus delivers events to all subscribers.
- EventBus handles subscriber failure (failed subscriber does not block other subscribers).
- Dashboard value accuracy (all displayed values match underlying data).
- Telegram alert delivery (all 13 command types tested).
- /status command returns correct IIOS state.
- /perf command returns current performance metrics.
- /learn command returns learning system state.

---

## EX.14 Cross-Cutting Test Requirements

### EX.14.1 Event Bus Integration Tests

The Event Bus is used by all 18 engines. The following cross-cutting integration
tests are required:

- All engines publish their defined lifecycle events when lifecycle transitions occur.
- All engines receive events from their registered subscriptions.
- Event ordering is preserved for same-source events.
- Failed subscriber does not prevent event delivery to other subscribers.
- High event volume (stress test: 1,000 events per second) does not cause event loss.

### EX.14.2 Shared State Tests

Components that share state (position manager, kill switch state, performance tracker)
require tests that verify concurrent access safety:

- Concurrent reads produce consistent results.
- Concurrent writes do not produce partial states.
- Write-read ordering is correct (a write followed immediately by a read returns
  the written value).

### EX.14.3 Data Feed Failover Integration Tests

The data feed failover path is critical for operational continuity:

- Test 1: Dhan feed becomes unavailable; yfinance activates within 90 seconds.
- Test 2: yfinance is active; Dhan becomes available; system switches back.
- Test 3: Both feeds unavailable; system enters safe mode.
- Test 4: Feed recovery after safe mode; system resumes normal operation.

### EX.14.4 Full Pipeline End-to-End Tests

The following end-to-end tests span the full 17-layer pipeline:

- **Happy path:** Normal market conditions → approved trade → paper order placed.
- **Kill switch path:** VIX > 45 → kill switch activates → all orders blocked.
- **Data degradation path:** Feed quality degrades → decision quality degradation
  signal → appropriate action taken.
- **Recovery path:** Container restart → state reconstruction → first cycle after
  restart produces correct decisions.
- **Strategy evolution path:** New strategy evolved → passes promotion gates →
  enters active strategy pool.

---

*End of Extended Supplement*

---
---

# EXTENDED SUPPLEMENT 2 — TESTING ENGINEERING DECISION RECORDS

## ED.1 Framework Design Decisions

| Record ID | Decision | Rationale | Date |
|-----------|---------|-----------|------|
| TST-EDR-001 | 47 testing categories | Full spectrum from unit to chaos; no single category provides adequate confidence | Inception |
| TST-EDR-002 | 15 coverage dimensions | Code coverage alone is insufficient; decision, risk, and scenario coverage are essential for capital-managing systems | Inception |
| TST-EDR-003 | Automated evidence collection | Manual evidence can be fabricated; automated evidence with integrity hashing is auditable | Inception |
| TST-EDR-004 | Golden dataset changes require Council vote | A changed golden dataset changes what is considered correct; this is an architectural decision | Inception |
| TST-EDR-005 | 90-day certification validity | Stale certifications do not reflect current system state; 90-day cycle ensures freshness | Inception |
| TST-EDR-006 | Safety test failure triggers deploy freeze | The cost of deploying a broken safety mechanism is unbounded; no deployment is worth that risk | Inception |
| TST-EDR-007 | Flaky test resolution within 14 days | A flaky test indicates real non-determinism; ignoring it allows the defect to persist | Inception |
| TST-EDR-008 | Kill switch has 15 mandatory test scenarios | Adversarial coverage: the kill switch must work in every conceivable failure condition | Inception |
| TST-EDR-009 | Full-day load test required | Memory leaks and performance degradation only manifest after hours; short tests hide them | Inception |
| TST-EDR-010 | Post-incident test creation within 72 hours | Defect escapes must produce permanent regression tests; the lesson must be encoded | Inception |

---

## ED.2 Coverage Dimension Weighting Rationale

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Code Coverage | 0.10 | Necessary but insufficient; lower weight reflects this |
| Decision Coverage | 0.10 | Every bad trade starts with a bad decision; high weight |
| Risk Coverage | 0.10 | Risk failures are financial; equal weight to decision coverage |
| Reliability Score | 0.12 | Unreliable tests provide no confidence; test reliability is primary |
| Coverage Score | 0.15 | Breadth of coverage is the most important single dimension |
| Pass Rate | 0.12 | Failing tests are open defects; high weight |
| Recovery Score | 0.10 | Systems fail; recovery must be tested as rigorously as normal operation |
| Security Score | 0.08 | Security failures are binary; partial security is no security |

---

## ED.3 IIOS-Specific Testing Constraints

The following constraints apply to IIOS testing specifically due to its financial
domain and live trading context:

**C1 — No Live Market Testing:**
Tests never execute against live market data in real time. All market data is
historical, replay, or synthetic. This prevents tests from creating accidental
live orders or consuming live data quotas.

**C2 — Paper Trading Always Active in Test:**
All execution-layer tests run with PAPER_TRADING=True. No test ever sends a live
order, even if the test is running in a staging environment.

**C3 — Position State Isolation:**
Position and order state is completely isolated between test runs. A test that
creates a paper position must remove it as part of cleanup. No test position
persists to the next test run.

**C4 — Kill Switch State Reset:**
The kill switch state is reset to inactive at the start of every test run.
A test that activates the kill switch must deactivate it during cleanup.

**C5 — Financial Arithmetic Precision:**
All tests involving financial calculations verify results to at least 4 decimal
places. Floating-point comparison tolerance is explicitly set per test.

**C6 — Market Hours Awareness:**
Tests that are sensitive to market hours (market session checks, scheduling)
use the injectable clock and a defined test timestamp. Tests do not depend on
the actual system clock for market session logic.

**C7 — Audit Trail Isolation:**
Audit log records created during testing are written to a separate test audit
log, never to the production audit log. Test audit logs are cleared after each
test run.

**C8 — Strategy Library Isolation:**
Tests that modify the evolved strategy library (strategy_lab/evolved_strategies)
operate on a copy of the library. The production strategy library is never
modified by any test.

---

*IIOS-TST-ENG-001 / Version 1.0.0 — Amendment: Extended Supplements Added*
