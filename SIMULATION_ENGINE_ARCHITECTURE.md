# SIMULATION ENGINE ARCHITECTURE

**Document Code:** IIOS-SIM-ENG-ARCH-001
**Series:** IIOS Engine Architecture Series — Document 18
**Status:** FINAL
**Version:** 1.0
**Classification:** Core Architecture Reference
**Scope:** Investment Intelligence Operating System — Simulation Engine

---

## AUTHORITATIVE NOTICE

This document is part of the IIOS Engine Architecture Series. Every design
decision recorded here is consistent with and subordinate to the completed
series documents:
DATABASE, KNOWLEDGE, ENTITY, RELATIONSHIP, EVENT, INFORMATION,
OBSERVATION, EVIDENCE, HYPOTHESIS, REASONING, DECISION, EXECUTION,
LEARNING, PREDICTION, RISK, PORTFOLIO, STRATEGY.

All terminology, layer numbering, component conventions, and
constitutional principles established in those documents are adopted
without modification. This document extends the series by defining the
Simulation Engine — the official virtual market of IIOS.

---

## IIOS ARCHITECTURE STACK

`
IIOS 17-LAYER ARCHITECTURE — SIMULATION ENGINE CONTEXT
═══════════════════════════════════════════════════════

 L1  GlobalIntelligence      — overnight global context
 L2  MarketIntelligence      — regime, sector, liquidity, events
 L3  MetaLearning            — strategy weight predictor
 L4  OpportunityEngine       — equity scanner, options, arbitrage
 L5  StrategyLab             — strategy management, backtesting, evolution
 L6  CapitalRiskEngine       — position sizing per strategy budget
 L7  RiskControl             — RiskManagerAI, PortfolioAllocation, StressTest
 L8  MarketSimulation    ◄── SIMULATION ENGINE LIVES HERE
 L9  RiskGuardian            — final kill-switch
L10  DebateAndDecision       — 5-agent debate, DecisionEngine
L11  ExecutionEngine         — OrderManager, broker integration
L12  TradeMonitoring         — TradeMonitor, StrategyHealthMonitor
L13  LearningSystem          — LearningEngine, PerformanceTracker
L14  PerformanceAnalytics    — DrawdownAnalyzer, WalkForwardTester
L15  ResearchLab             — promotion gates, research pipeline
L16  ValidationEngine        — 6-stage validation pipeline
L17  ControlTower            — SQLite telemetry, Streamlit dashboard, EventBus

 SIMULATION ENGINE (L8) — reads from L1-L7, L13-L14
 SIMULATION ENGINE (L8) — delivers results to L5, L9, L10, L13, L15, L16
 SIMULATION ENGINE (L8) — NEVER writes to production data stores
 SIMULATION ENGINE (L8) — NEVER places live orders
`

---

## SIMULATION ENGINE INFORMATION FLOW

`
SIMULATION ENGINE INFORMATION FLOW
════════════════════════════════════

DATA SOURCES (Read-Only Access)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Historical OHLCV (yfinance / Dhan)
 Options Chain Archives
 Macroeconomic Data (L1 GlobalIntelligence)
 Regime History (L2 MarketIntelligence)
 Strategy Definitions (L5 StrategyLab)
 Risk Rules (L7 RiskControl)
 Trade Outcomes (L13 LearningSystem)
 Performance Analytics (L14 PerformanceAnalytics)

         │
         ▼
┌──────────────────────────────────┐
│      SIMULATION ENGINE (L8)      │
│                                  │
│  Historical Engine               │
│  Monte Carlo Engine              │
│  Stress Testing Engine           │
│  Synthetic Market Generator      │
│  Execution Simulator             │
│  Portfolio Simulator             │
│  Decision Simulator              │
│  Learning Simulator              │
│  Risk Simulator                  │
│  Performance Evaluator           │
└──────────────────────────────────┘
         │
         ▼
RESULT CONSUMERS (Knowledge Delivery)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 L5  StrategyLab            ← backtest results, strategy scores
 L9  RiskGuardian           ← stress test risk signals
 L10 DebateAndDecision      ← simulated scenario outcomes
 L13 LearningSystem         ← learning replay outcomes
 L15 ResearchLab            ← promotion gate evidence
 L16 ValidationEngine       ← 6-stage validation results
 L17 ControlTower           ← simulation telemetry, dashboard
`

---

## TABLE OF CONTENTS

`
PART I    — Simulation Philosophy (Section 1)
PART II   — Simulation Taxonomy (Section 2)
PART III  — Core Components (Section 3)
PART IV   — Simulation Lifecycle (Section 4)
PART V    — Simulation Services (Section 5)
PART VI   — Simulation Processing Pipelines (Section 6)
PART VII  — Simulation Quality Framework (Section 7)
PART VIII — Simulation Governance (Section 8)
PART IX   — Simulation Constitution (Section 9)
PART X    — Simulation Readiness Checklist (Section 10)

SUPPLEMENT A — Taxonomy Reference
SUPPLEMENT B — Scenario Catalog
SUPPLEMENT C — Replay Models
SUPPLEMENT D — Monte Carlo Reference
SUPPLEMENT E — Anti-Patterns
SUPPLEMENT F — Operational Runbook
SUPPLEMENT G — Governing Design Records
SUPPLEMENT H — Comprehensive Glossary

APPENDIX  — Worked Examples (WE-01 through WE-06)
EXTENDED REFERENCES
DOCUMENT SUMMARY
`

---

## PART I — SIMULATION PHILOSOPHY

### 1.1 — What Is Simulation?

Simulation is the creation and operation of an artificial environment that mimics
the behavior of a real system in order to study, test, or validate how that system
would behave under specified conditions. In investment systems, simulation creates
a virtual market — a controlled, isolated environment where strategies, models,
decisions, and learning mechanisms can be tested exhaustively without committing
real capital or placing live orders.

Simulation is not an approximation or a shortcut. It is the primary mechanism by
which IIOS ensures that every component entering live operation has been stress-
tested, validated, and understood. The virtual market of IIOS is not inferior to
the live market — it is more comprehensive, because it can replay historical crises,
generate synthetic extremes that have never occurred, and run thousands of parallel
scenarios in parallel without time constraint.

The central purpose of the IIOS Simulation Engine is to answer one question before
any strategy, model, or decision process touches a live order: "If this had been
running under these conditions, would it have behaved acceptably?" If the answer is
yes — with statistical confidence, across regimes, under stress — it advances toward
production. If the answer is no, it is improved, re-validated, or retired.

---

### 1.2 — Simulation Versus Related Concepts

The following definitions establish precise distinctions between simulation and
the related concepts used throughout IIOS.

---

**Simulation**

The broadest term. Simulation encompasses any process that creates a controlled
artificial environment to evaluate system behavior. Simulation includes historical
replay, paper trading, Monte Carlo analysis, synthetic market generation, scenario
analysis, and stress testing. All other concepts below are specific types of
simulation or specific instruments within simulation.

---

**Backtesting**

Historical simulation applied to a trading strategy. Backtesting replays a specific
period of historical market data and applies a strategy's signal logic to determine
what trades would have been generated, and what the performance of those trades
would have been. Backtesting operates on fixed historical data with known outcomes.
Its primary limitation is that it cannot test for conditions that did not occur in
the historical period. Backtesting is necessary but not sufficient for strategy
validation; it is one stage in the broader simulation process.

---

**Paper Trading**

Real-time simulation in which a strategy generates real signals using live market
data, but all orders are paper orders — recorded in a simulated ledger rather than
submitted to a real broker. Paper trading validates that a strategy's signal logic
operates correctly in real market conditions before the system is risked on real
capital. Paper trading does not validate performance (sample size is too small) but
does validate operational correctness, data feed integration, latency, and edge-case
handling. IIOS paper trading runs on the same execution pathway as live trading,
with one difference: the OrderManager receives a PAPER_TRADING=True flag and routes
orders to a simulated ledger rather than the Dhan broker.

---

**Historical Replay**

The faithful reproduction of a past market session — tick by tick or bar by bar —
as if the simulation system is experiencing it for the first time. Historical replay
is distinguished from backtesting in that replay is a general mechanism for
reproducing market conditions, while backtesting is its specific application to
strategy evaluation. Historical replay is also used for debugging (reproducing an
event that led to unexpected behavior), learning validation (checking that the
LearningEngine would have made the correct updates on a known history), and decision
validation (checking that the DebateAndDecision system would have reached the
correct conclusion on a known outcome).

---

**Forward Testing**

Simulation using data from the current period (not the period used for strategy
development). Forward testing is similar to paper trading but may be applied in
a controlled simulation environment rather than live data. The key characteristic
is that the data being tested against is recent — it was not available when the
strategy was designed or optimized.

---

**Walk-Forward Analysis**

A specific validation technique that divides a historical dataset into consecutive
in-sample and out-of-sample windows, optimizing on the in-sample period and
testing on the out-of-sample period, then stepping forward and repeating. Walk-
forward analysis answers the question: "Does this strategy's optimization generalize
across different time periods?" It is more rigorous than single-period backtesting
because it tests for temporal robustness. Walk-forward analysis is both a simulation
technique and a quality gate in IIOS strategy promotion.

---

**Stress Testing**

A simulation technique that deliberately applies extreme or adverse market
conditions to evaluate whether a strategy, portfolio, or system remains within
acceptable risk bounds under those conditions. Stress tests use either historical
crisis periods (e.g., March 2020, 2008 Global Financial Crisis) or hypothetical
extreme scenarios (e.g., single-day 15% market decline, VIX spike to 80). Stress
testing answers the question: "How bad could it get, and would we survive it?"

---

**Monte Carlo Simulation**

A probabilistic simulation technique that runs many randomized variations of a
scenario to generate a distribution of possible outcomes. In strategy validation,
Monte Carlo simulation randomizes the order of historical trades, adds random noise
to price series, or permutes the historical data to create many alternative
histories. The result is a distribution of performance metrics (Sharpe, MaxDD,
Win Rate) rather than a single point estimate. This distribution reveals the range
of outcomes the strategy might produce — not just the outcomes it happened to
produce on one specific history.

---

**Scenario Analysis**

The evaluation of a system's behavior under a specific, well-defined set of market
conditions. Unlike stress testing (which focuses on extremes) or Monte Carlo
(which randomizes), scenario analysis asks: "What would happen if the market
followed this specific sequence of events?" Scenarios can be historical
(reproduce the 2020 COVID crash) or hypothetical (simulate a 12-month sideways
consolidation followed by a sudden breakout). Scenario analysis is particularly
valuable for decision-making: it reveals how different strategies compare under
the same market conditions.

---

**Synthetic Data Generation**

The creation of artificial market data that has the statistical properties of real
market data but did not actually occur. Synthetic data is generated using statistical
models of market behavior (geometric Brownian motion, jump-diffusion models, regime-
switching models). It is used when historical data is insufficient (small-cap stocks
with limited history), when testing behavior in conditions that have not yet occurred
(testing a strategy in a market crash 5x worse than any historical crash), or when
creating large datasets for machine learning model training.

---

**Digital Twin**

A complete, high-fidelity virtual replica of the live IIOS system. The digital twin
runs in parallel with the live system using the same data feeds and the same decision
logic, but all its outputs (orders, portfolio changes) are virtual. The digital twin
serves as the primary validation environment: any change to the live system is first
validated in the digital twin for a period before being promoted. The Simulation
Engine is the foundational component of the IIOS digital twin.

---

**Virtual Market**

The complete simulation environment of IIOS — encompassing all simulation types,
all scenario definitions, all synthetic data generators, and all performance
evaluation infrastructure. The virtual market is the IIOS Simulation Engine. It
is the official "try before you deploy" environment for all new strategies, models,
and system changes.

---

**Decision Replay**

A specific simulation mode that replays historical decision events through the
DebateAndDecision system (L10) using the same input conditions that existed at the
time of the original decision. Decision replay validates that the decision system is
stable and consistent — that the same inputs produce the same output (determinism
check) — and can reveal whether historical decisions would have been different if
the system had more information or different thresholds.

---

**Risk Replay**

A specific simulation mode that replays historical sessions through the Risk Engine
components (L7 RiskControl, L9 RiskGuardian) to validate that risk rules would have
fired correctly at the right times. Risk replay is used after changes to risk logic
to confirm backward compatibility and to investigate historical near-misses where
a risk rule almost fired but did not.

---

**Portfolio Replay**

A specific simulation mode that replays the portfolio management decisions for a
historical period, allowing the system to test different allocation strategies,
rebalancing rules, and position sizing approaches on the same underlying trade
signals. Portfolio replay answers: "Given the same trade signals, would a different
allocation strategy have produced better results?"

---

**Learning Replay**

A specific simulation mode that replays the LearningSystem's updates for a
historical period, validating that learning mechanisms are working correctly. A
learning replay can reveal whether the LearningEngine was assigning credit
correctly to the signals and strategies that generated profits, and whether its
model updates improved performance over time.

---

### 1.3 — Why Simulation Is Essential Before Production Deployment

A trading system that deploys untested strategies into live markets is not a
sophisticated system — it is a gambling mechanism. IIOS simulation exists to ensure
that every component entering live operation has been subjected to scrutiny far more
rigorous than any single live deployment period could provide. Five arguments
establish why simulation is not optional but foundational.

**Argument 1 — The Scarcity of Live Experience**
Live market data accumulates at one session per day. A strategy that needs 250
sessions of evidence to be statistically evaluated requires one year of live trading.
Simulation compresses this to hours. A strategy can be evaluated across 5 years of
data (1,250 sessions), multiple market regimes, and hundreds of Monte Carlo
variations before it is ever deployed. Simulation turns a year of uncertainty into
an afternoon of evidence.

**Argument 2 — The Irreversibility of Losses**
A strategy that loses 20% in live trading before being identified as flawed has
caused real, irreversible capital loss. Simulation catches the same flaw before
deployment, at zero cost. The asymmetry is profound: simulation costs compute
time; failure in production costs capital that may not be recovered.

**Argument 3 — The Rarity of Market Extremes**
A strategy that performs well in normal markets may be catastrophically vulnerable
to conditions that occur only once per decade. A live deployment cannot wait ten
years to test this. Simulation reproduces extreme historical periods and generates
synthetic extremes beyond historical experience, ensuring that strategies are
evaluated against conditions that rare live deployment would never encounter.

**Argument 4 — Controlled Hypothesis Testing**
Simulation provides the controlled experimental environment that live trading cannot.
In live trading, many variables change simultaneously: market conditions, strategy
parameters, portfolio composition, risk environment. Simulation isolates each
variable, allowing precise measurement of causal relationships. "Did the strategy
perform better because the parameter was changed, or because the market regime
changed?" Simulation can answer this. Live trading cannot.

**Argument 5 — Governance and Accountability**
Every simulated result is a documented record. Every strategy that advances to
production has a complete simulation history: what it was tested against, what
results were achieved, what risks were measured. This creates the governance record
that professional investment management requires.

---

## PART II — SIMULATION TAXONOMY

### 2.1 — Taxonomy Overview

The IIOS Simulation Engine supports 21 distinct simulation types, organized into
five groups: Historical (replay-based), Probabilistic (randomized), Stress-Oriented
(extreme scenario), Operational (real-time analog), and Composite (multi-mode).
Each type has a defined purpose, operational profile, and role within the IIOS
validation and governance framework.

---

### SIMULATION TYPE REFERENCE TABLE

| Code   | Name                       | Group         | Primary Use                              | IIOS Status |
|--------|----------------------------|---------------|------------------------------------------|-------------|
| SIM-01 | Historical Simulation      | Historical    | Strategy backtesting; baseline validation | ACTIVE      |
| SIM-02 | Real-Time Paper Trading    | Operational   | Operational readiness; live signal test   | ACTIVE      |
| SIM-03 | Market Replay              | Historical    | Session-level debugging and auditing      | ACTIVE      |
| SIM-04 | Tick Replay                | Historical    | Intraday execution accuracy testing       | ACTIVE      |
| SIM-05 | Bar Replay                 | Historical    | OHLC-level strategy testing               | ACTIVE      |
| SIM-06 | Scenario Simulation        | Stress        | Defined hypothesis testing                | ACTIVE      |
| SIM-07 | Monte Carlo Simulation     | Probabilistic | Statistical robustness; distribution est.  | ACTIVE      |
| SIM-08 | Bootstrap Simulation       | Probabilistic | Bias-reduced performance estimation       | ACTIVE      |
| SIM-09 | Stress Testing             | Stress        | Extreme condition risk validation         | ACTIVE      |
| SIM-10 | Crash Simulation           | Stress        | Sudden large-move impact assessment       | ACTIVE      |
| SIM-11 | Liquidity Simulation       | Stress        | Market depth impact on execution          | ACTIVE      |
| SIM-12 | Slippage Simulation        | Operational   | Transaction cost accuracy modeling        | ACTIVE      |
| SIM-13 | Latency Simulation         | Operational   | Execution timing impact assessment        | ACTIVE      |
| SIM-14 | Execution Simulation       | Operational   | Order fill modeling                       | ACTIVE      |
| SIM-15 | Portfolio Simulation       | Composite     | Allocation strategy evaluation            | ACTIVE      |
| SIM-16 | Multi-Asset Simulation     | Composite     | Cross-asset correlation behavior          | ACTIVE      |
| SIM-17 | Cross-Market Simulation    | Composite     | Inter-market dependency testing           | ACTIVE      |
| SIM-18 | AI Decision Simulation     | Composite     | Decision system replay and validation     | ACTIVE      |
| SIM-19 | Learning Simulation        | Composite     | Learning mechanism validation             | ACTIVE      |
| SIM-20 | Synthetic Market Simulation| Probabilistic | Beyond-history extreme generation         | ACTIVE      |
| SIM-21 | Hybrid Simulation          | Composite     | Combined multi-mode validation            | ACTIVE      |

---

### 2.2 — Historical Simulation Types

---

**SIM-01 — Historical Simulation**

Definition: The reproduction of a defined historical period using archived market
data to evaluate strategy performance as if the strategy had been running during
that period. Historical simulation is the foundational validation technique of IIOS.

Scope: Any historical period for which complete OHLCV data is available.
Data granularity: Daily bars (standard); intraday bars (15-minute, 5-minute, 1-minute).
Look-ahead bias controls: Data accessed strictly by lookback period — no bar data
from the evaluation period is accessible to the signal generation logic.

Signal timing model: Signals generated using close of bar N; execution priced at
open of bar N+1 (standard model). Alternative: intrabar execution with slippage model.

Transaction cost model: Brokerage 0.03% per side; STT 0.1% on sell; exchange fees
0.00325%; SEBI turnover 0.0001%; slippage 0.05% large-cap / 0.15% mid-cap / 0.30% small-cap.

Performance metrics captured: Total return, CAGR, Sharpe Ratio, Sortino Ratio,
Calmar Ratio, maximum drawdown, average drawdown, win rate, payoff ratio, trade
count, average holding period, regime breakdown, sector breakdown.

IIOS role: Primary engine for strategy backtesting (SP-03 Backtesting Pipeline
in Strategy Engine). The first-line evidence required for strategy promotion.

---

**SIM-02 — Real-Time Paper Trading**

Definition: Real-time signal generation using live market data, with orders routed
to a simulated paper ledger rather than a real broker. All market data feeds are
identical to the live system; only order submission differs.

Purpose: Validate operational correctness of a strategy in live conditions before
committing capital. Paper trading does not validate statistical performance — the
sample size in any single paper trading period is too small for statistical
confidence. It validates integration: data feeds connected correctly, signal
generation running on schedule, position management working, P&L calculations
correct.

Duration before live promotion: Minimum 10 sessions for operational verification;
30 sessions for operational maturity confirmation.

IIOS integration: The OrderManager (L11) receives a PAPER_TRADING=True flag. All
order lifecycle events are identical to live trading; only the final submission
step is redirected to the paper ledger. Paper trade records are stored in
data/paper_trades.csv with full audit trail.

Monitoring: All paper trading monitored by SC-13 Strategy Monitoring Engine in
the Strategy Engine. Alerts fire on the same thresholds as live strategies.

---

**SIM-03 — Market Replay**

Definition: Session-level replay of a specific historical trading session, including
all price action, volume, and news context, executed in chronological order as if
the system were experiencing it in real time.

Purpose: Post-session debugging (what happened and why), auditing (confirm the
system behaved correctly), and training (human operators studying market behavior
in a controlled learning environment).

Granularity: Full session (09:15 IST to 15:30 IST); any subset of a session.
Replay speed: 1x (real-time equivalent), 10x, 100x, or maximum speed.
Pause/inspect: Replay can be paused at any point for inspection of system state.

IIOS role: Used by the Audit Manager (SC-15 in Strategy Engine) for investigating
decisions made during specific historical sessions. Used by the Decision Simulator
for decision replay validation.

---

**SIM-04 — Tick Replay**

Definition: Bar-level replay at the tick or sub-minute level, reproducing the
full intraday price path rather than only the OHLC summary.

Purpose: Required for execution accuracy testing — validating that order fill
models correctly reflect how orders would have been filled given the intraday
price path. Tick replay exposes artifacts in bar-based simulation (e.g., a bar
that opens at 10 and closes at 12 — was the high 15 or 11? Tick data answers this).

Data requirement: L1 tick data or sub-minute bar data. For NIFTY50 instruments:
available from NSE tick data archives.

IIOS role: Used by SIM-12 (Slippage Simulation) and SIM-14 (Execution Simulation)
for high-fidelity fill modeling. Not required for daily bar-based strategies but
essential for intraday strategies with tight stops.

---

**SIM-05 — Bar Replay**

Definition: Replay of OHLCV bar data at the natural bar granularity — daily bars
for daily strategies, hourly bars for hourly strategies. Bar replay is the standard
replay granularity for the majority of IIOS strategy testing.

Purpose: Provide a repeatable, deterministic execution environment for strategy
evaluation. Bar replay is deterministic: the same strategy on the same bar series
produces identical results every time.

Granularity options: 1-day, 4-hour, 1-hour, 30-minute, 15-minute, 5-minute bars.
Primary IIOS granularity: 1-day bars for swing strategies; 15-minute bars for
intraday strategies.

---

### 2.3 — Probabilistic Simulation Types

---

**SIM-07 — Monte Carlo Simulation**

Definition: A family of simulation techniques that use repeated random sampling to
produce distributions of outcomes rather than point estimates. IIOS uses three
Monte Carlo techniques:

(1) Trade Permutation Monte Carlo: Randomizes the order of historical trades and
re-computes performance metrics 500–10,000 times. Produces the distribution of
outcomes that would result from the same set of trades in different orders. Tests
whether good performance was dependent on the specific ordering of profitable and
loss trades, or whether it is robust regardless of order.

(2) Price Series Perturbation Monte Carlo: Adds random noise to the historical
price series (scaled by volatility) and re-runs the full backtest 500 times.
Tests whether the strategy's performance is sensitive to small price variations —
a robust strategy performs well across all perturbations; an overfit strategy
performs well only on the original historical prices.

(3) Synthetic History Monte Carlo: Generates 500 synthetic price series with
the same statistical properties (mean return, volatility, autocorrelation, fat
tails) as the historical series, and runs the full backtest on each. Provides
the most realistic estimate of the distribution of outcomes.

Statistical outputs: P5, P10, P25, P50, P75, P90, P95 for each performance metric.
Required minimum: P10 Sharpe >= 0.5 for strategy promotion.

---

**SIM-08 — Bootstrap Simulation**

Definition: A resampling technique that draws random samples with replacement from
the historical trade record to construct many alternative trade sequences. Bootstrap
simulation is related to Monte Carlo but preserves more of the temporal structure
of the original trade record.

Purpose: Provide an estimate of performance metrics with reduced look-ahead bias
and better statistical confidence than single-pass backtesting.

Block Bootstrap: For strategies with autocorrelated returns (momentum strategies),
block bootstrap draws consecutive blocks of trades (block size = autocorrelation
lag), preserving the temporal dependencies that pure Monte Carlo randomization
destroys.

Minimum samples: 1,000 bootstrap iterations. For strategies with < 100 trades:
2,000 iterations.

---

**SIM-20 — Synthetic Market Simulation**

Definition: Generation of artificial market data with defined statistical properties
that do not require a historical precedent. Synthetic markets can model conditions
that have never occurred in the historical record — extended crises, multi-year
sideways markets, or structural volatility regime changes.

Generation models used by IIOS:

Geometric Brownian Motion (GBM): The baseline model. Models continuous price paths
with constant drift and volatility. Used for simple benchmarking.

Jump-Diffusion Model (Merton): GBM extended with Poisson-distributed jumps.
Captures sudden price gaps that GBM cannot reproduce. Used for crash simulation.

Regime-Switching Model: Market alternates between regime states (e.g., TRENDING,
SIDEWAYS, VOLATILE) with defined transition probabilities. Used for testing regime-
sensitive strategies across many simulated regime sequences.

Heston Stochastic Volatility Model: Models time-varying volatility using a mean-
reverting stochastic process. Captures volatility clustering and the correlation
between price moves and volatility changes.

GARCH Model: Time-series model of conditional volatility — volatility today depends
on yesterday's volatility and yesterday's return. Used for realistic intraday
volatility simulation.

---

### 2.4 — Stress Simulation Types

---

**SIM-09 — Stress Testing**

Definition: Evaluation of strategy and portfolio behavior under extreme adverse
conditions. IIOS maintains a library of named stress scenarios derived from
historical crises and hypothetically constructed extremes.

Historical stress scenarios maintained:
- CRISIS-2020: March 2020 COVID crash (NIFTY -38% in 28 trading days)
- CRISIS-2008: 2008 Global Financial Crisis (NSE data period)
- CRISIS-2015: August 2015 China-led selloff
- CRISIS-INFRA-2022: 2022 infrastructure and rate shock period
- CRISIS-VOL-HIGH: 30-day VIX > 45 scenario
- CRISIS-LIQUIDITY: Market wide circuit breakers activated on 3 consecutive sessions

Hypothetical stress scenarios:
- HYPOTHETICAL-CRASH-15PCT: Single-session 15% decline
- HYPOTHETICAL-CRASH-25PCT: Single-session 25% decline
- HYPOTHETICAL-SIDEWAYS-180D: 180-day zero-return channel
- HYPOTHETICAL-VIX-80: VIX spike to 80 (2x the 2020 peak)
- HYPOTHETICAL-RATE-SHOCK: +300 bps overnight rate increase
- HYPOTHETICAL-CURRENCY-SHOCK: USD/INR +15% in 5 sessions

---

**SIM-10 — Crash Simulation**

Definition: A specialized stress test focused on large, rapid price declines.
Crash simulations test whether position sizing, stop-loss rules, and kill-switch
mechanisms function correctly during sudden market dislocations when normal
market microstructure assumptions (orderly fills, normal slippage) may break down.

Crash fill model: During a crash scenario, slippage is expanded (3–10x normal)
and partial fills are introduced to model real crash market conditions where
liquidity disappears rapidly.

---

**SIM-11 — Liquidity Simulation**

Definition: Simulation of reduced market liquidity conditions, where normal order
fill assumptions are replaced with liquidity-adjusted models. Liquidity simulation
tests whether strategies that work in normal liquidity remain viable when spreads
widen, market depth decreases, and large orders cannot be filled at expected prices.

Liquidity stress factors: Spread widening (2x–20x normal); depth reduction (10%–
90% of normal depth available); fill probability reduction for large orders.

---

### 2.5 — Operational Simulation Types

---

**SIM-12 — Slippage Simulation**

Definition: Modeling of the difference between the expected execution price and
the actual execution price. Slippage is caused by market impact (large orders
moving the market), timing (price moves between order generation and execution),
and bid-ask spread.

IIOS Slippage Models:
- Fixed percentage: 0.05% large-cap; 0.15% mid-cap; 0.30% small-cap (default)
- Volume-adjusted: slippage scales with order size as percentage of daily volume
- Volatility-adjusted: slippage scales with current VIX / average VIX
- Combined model: max(fixed, volume-adjusted, volatility-adjusted)

---

**SIM-13 — Latency Simulation**

Definition: Modeling of the time delays in the signal-to-order pipeline. Latency
simulation tests whether strategies that depend on rapid execution remain profitable
when network, system, or broker delays are introduced.

Latency components modeled: Data feed latency (0–100ms), signal computation
latency (0–50ms), order routing latency (0–200ms), broker acknowledgment latency
(0–500ms).

IIOS note: Because IIOS is primarily a position-based swing trading system (not
a high-frequency system), latency simulation is primarily used to confirm that
strategies are not sensitive to short-term latency variations.

---

**SIM-14 — Execution Simulation**

Definition: Complete modeling of the order lifecycle — from signal generation to
order submission to partial or full fill to settlement. Execution simulation
tests that the order management logic correctly handles all fill scenarios:
immediate full fills, partial fills, price improvement, rejection, timeout.

Order types modeled: Market orders, limit orders, stop-loss orders, bracket orders.
Fill scenarios: Immediate fill; partial fill with remainder; fill at limit when
price improves; rejection due to insufficient funds; timeout/cancellation.

---

### 2.6 — Composite Simulation Types

---

**SIM-15 — Portfolio Simulation**

Definition: Simulation of the complete portfolio — multiple strategies running
simultaneously — to evaluate total portfolio behavior, correlation effects, and
allocation efficiency. Portfolio simulation answers questions that single-strategy
backtesting cannot: How do strategies interact? Does adding a new strategy improve
or degrade risk-adjusted portfolio performance?

---

**SIM-16 — Multi-Asset Simulation**

Definition: Simulation across multiple asset classes (equities, index futures,
options, FX) simultaneously. Multi-asset simulation validates strategies that
depend on inter-asset relationships (e.g., equity-futures basis strategies, option
hedging strategies).

---

**SIM-17 — Cross-Market Simulation**

Definition: Simulation incorporating signals from multiple markets (NSE equities,
BSE, global indices, FX markets) to test strategies that use cross-market signals.

---

**SIM-18 — AI Decision Simulation**

Definition: Replay of historical decision events through the IIOS DebateAndDecision
system (L10) to validate the decision mechanism's consistency, stability, and
quality. AI decision simulation is both a validation technique and a monitoring
technique: it catches regressions in the decision system by comparing replayed
decisions to original decisions.

---

**SIM-19 — Learning Simulation**

Definition: Replay of the learning cycle through the LearningSystem (L13) to
validate that learning mechanisms are functioning correctly. Learning simulation
tests whether the LearningEngine correctly attributed performance to the right
signals, whether model updates improved subsequent performance, and whether the
learning process is stable (not oscillating or diverging).

---

**SIM-21 — Hybrid Simulation**

Definition: A simulation run that combines two or more simulation types in a
single evaluation. The most common hybrid: Historical simulation (SIM-01) combined
with Monte Carlo perturbation (SIM-07) and execution simulation (SIM-14), providing
a combined picture of statistical robustness and realistic execution modeling.

---

### 2.7 — Simulation Type Selection Guide

| Validation Need                          | Primary Type   | Secondary Type  |
|------------------------------------------|----------------|-----------------|
| Strategy backtesting                     | SIM-01         | SIM-07, SIM-08  |
| Operational readiness check              | SIM-02         | SIM-14          |
| Debugging specific session               | SIM-03         | SIM-04          |
| Execution quality validation             | SIM-14         | SIM-12, SIM-04  |
| Statistical robustness                   | SIM-07         | SIM-08          |
| Extreme risk assessment                  | SIM-09         | SIM-10, SIM-11  |
| Portfolio composition evaluation         | SIM-15         | SIM-07          |
| Decision system validation               | SIM-18         | SIM-03          |
| Learning system validation               | SIM-19         | SIM-03          |
| Beyond-history risk assessment           | SIM-20         | SIM-09          |
| Full pre-deployment validation           | SIM-21         | All applicable  |

---

## PART III — CORE COMPONENTS

### 3.1 — Component Architecture Overview

The Simulation Engine is composed of 21 components organized into four tiers.
Each tier serves a distinct architectural function.

`
SIMULATION ENGINE — COMPONENT TIER ARCHITECTURE
════════════════════════════════════════════════

TIER 1 — FOUNDATION (read/write; must be available before any simulation)
  SC-01  Simulation Registry          — master record of all simulation runs
  SC-02  Simulation Catalog           — taxonomy, classification, metadata index
  SC-03  Scenario Manager             — scenario definitions, configurations
  SC-04  Simulation Version Manager   — version history, rollback management

TIER 2 — EXECUTION ENGINES (run simulations)
  SC-05  Replay Engine                — manages all replay-based simulations
  SC-06  Historical Engine            — bar and tick historical simulation
  SC-07  Synthetic Market Generator   — artificial market data production
  SC-08  Monte Carlo Engine           — probabilistic simulation management
  SC-09  Stress Testing Engine        — extreme scenario simulation
  SC-10  Execution Simulator          — order fill modeling
  SC-11  Portfolio Simulator          — multi-strategy portfolio simulation
  SC-12  Decision Simulator           — AI decision replay and validation
  SC-13  Learning Simulator           — learning mechanism replay

TIER 3 — EVALUATION AND RISK
  SC-14  Risk Simulator               — risk rule replay and validation
  SC-15  Performance Evaluator        — metrics computation, quality scoring
  SC-16  Simulation Validator         — result integrity and validity checks

TIER 4 — GOVERNANCE AND INTELLIGENCE
  SC-17  Simulation Analytics Engine  — cross-simulation pattern analysis
  SC-18  Simulation Reporting Engine  — report generation and delivery
  SC-19  Simulation Governance Manager — approval, oversight, compliance
  SC-20  Simulation Audit Manager     — hash-chained audit trail
  SC-21  Simulation Health Manager    — engine-wide health scoring (SEHS)
`

---

### 3.2 — TIER 1 COMPONENTS

---

#### SC-01 — Simulation Registry

**Purpose:** The central authoritative record of every simulation run executed
by the IIOS Simulation Engine. The registry is the single source of truth for
simulation status, results, and history.

**Responsibilities:**
- Assign a unique Simulation Run ID (SRI) to every simulation run
- Record simulation run metadata: type, start time, end time, status, operator
- Track simulation state through its lifecycle (QUEUED, RUNNING, COMPLETE, FAILED, ARCHIVED)
- Maintain index of simulation artifacts stored in SC-03 (Scenario Manager)
- Provide query interface to all other components for simulation history lookup
- Record relationships between simulation runs (e.g., re-runs, follow-on analyses)
- Enforce simulation ID uniqueness and naming conventions

**Inputs:** New simulation run requests from all Tier 2 execution engines.
Lifecycle updates from all active simulations.

**Outputs:** SRI assignments to requesting components. Simulation history queries
answered for any component requesting run status or history.

**Dependencies:** SC-02 Catalog (for taxonomy classification); SC-04 Version Manager
(for version context); persistent storage (SQLite or file-based artifact store).

**Interactions:** All 20 other components interact with SC-01 for registration and
status updates. SC-20 Audit Manager creates corresponding audit records for all
registry events.

**Failure Modes:**
- Registry storage unavailable: all new simulation runs must queue until restored.
- Registry corruption: restore from last checkpoint; replay event log to rebuild state.

**Recovery Strategy:** Registry maintains incremental checkpoints every 100 events.
Event log is append-only; full state reconstruction is possible from event log.

**Monitoring:** SC-21 Health Manager monitors registry query latency (SLA < 10ms),
write latency (SLA < 50ms), and storage utilization.

**Scalability:** Registry is designed for 10,000+ simulation run records. Index-
optimized for symbol, type, date range, and status queries.

**Engineering Notes:** SRI format: SIM-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}.
Example: SIM-MC-20251112-00000001 for the first Monte Carlo run on 2025-11-12.

---

#### SC-02 — Simulation Catalog

**Purpose:** The classification and discovery layer for the Simulation Engine.
The Catalog organizes simulation runs, scenario definitions, and results according
to the taxonomy established in Part II, making them discoverable by type, asset,
date range, and purpose.

**Responsibilities:**
- Maintain taxonomy classification for all simulation types (SIM-01 through SIM-21)
- Provide faceted search across simulations: by type, asset, period, regime, strategy
- Maintain the Scenario Library index (all defined scenarios, organized by type and purpose)
- Track simulation coverage: which strategies have been tested by which simulation types
- Identify simulation coverage gaps: strategies missing required simulation types
- Support simulation comparison: retrieve similar runs for benchmarking

**Inputs:** Registration events from SC-01. Scenario definitions from SC-03.
User queries for simulation discovery.

**Outputs:** Simulation catalog search results. Coverage gap reports. Comparison
sets for result benchmarking.

**Dependencies:** SC-01 Registry; SC-03 Scenario Manager.

**Failure Modes:** Catalog index corruption: rebuild from SC-01 Registry (complete
rebuild possible in < 30 minutes for 10,000 runs).

**Monitoring:** Index rebuild time; search query latency (SLA < 100ms); gap
report generation time.

---

#### SC-03 — Scenario Manager

**Purpose:** The authoritative store and lifecycle manager for all simulation
scenario definitions. A scenario is a complete specification of a simulation run:
the market environment to simulate, the instruments to include, the time period,
the simulation type, and all configuration parameters.

**Responsibilities:**
- Store and version all scenario definitions in a structured, queryable format
- Manage scenario lifecycle: DRAFT, VALIDATED, ACTIVE, DEPRECATED, ARCHIVED
- Validate scenario definitions for internal consistency before activation
- Maintain the Scenario Library: the curated set of approved scenarios available for use
- Track scenario usage: which simulation runs used which scenario definitions
- Enforce scenario naming conventions and versioning
- Provide scenario retrieval to all Tier 2 execution engines
- Manage scenario archives: completed scenario run artifacts stored permanently

**Inputs:** Scenario definition submissions (from operators or automated systems).
Validation requests. Retrieval requests from execution engines.

**Outputs:** Validated scenario definitions. Scenario retrieval responses.
Scenario library catalog updates.

**Scenario Definition Required Fields:**
scenario_id, name, type (SIM-01 through SIM-21), asset_universe, time_period_start,
time_period_end, bar_granularity, regime_filter, transaction_cost_model,
slippage_model, monte_carlo_iterations (if applicable), stress_factor (if applicable),
hypothesis_reference, created_by, approved_by, version.

**Failure Modes:** Scenario definition corruption: restore from version history.
Scenario retrieval failure: cache last-known-good scenario; alert operator.

---

#### SC-04 — Simulation Version Manager

**Purpose:** Tracks version history for all scenario definitions and simulation
configurations, enabling rollback and comparative analysis across versions.

**Responsibilities:**
- Assign version numbers to scenario definitions following MAJOR.MINOR.PATCH convention
- Store version diffs: what changed between versions
- Support rollback to prior scenario version
- Track which simulation runs used which scenario version
- Generate version comparison reports: how do results differ across scenario versions
- Maintain version metadata: change author, change rationale, approval record

**Versioning Trigger:**
MAJOR: Fundamental change to scenario structure (e.g., asset universe change,
time period change, simulation type change).
MINOR: Parameter adjustment (e.g., stress factor change, Monte Carlo iterations).
PATCH: Documentation or metadata correction.

**Failure Modes:** Version storage unavailable: queue version updates; retry. Version
conflict (concurrent edits): sequential lock; last-write-wins with notification.

---

### 3.3 — TIER 2 COMPONENTS — EXECUTION ENGINES

---

#### SC-05 — Replay Engine

**Purpose:** The master orchestrator for all replay-based simulations (SIM-03
Market Replay, SIM-04 Tick Replay, SIM-05 Bar Replay). The Replay Engine manages
the playback mechanism — controlling time, sequencing data events, and delivering
data to consuming components in the correct chronological order.

**Responsibilities:**
- Load historical or synthetic market data for the specified time period and instruments
- Control replay clock: manage simulated time advancing through bars or ticks
- Enforce chronological integrity: no future data is accessible to the strategy or system under test
- Deliver market data events to registered consumers (strategy signal generators,
  decision components, learning components) in the correct sequence
- Support replay speed control: 1x (real-time equivalent), 10x, 100x, max speed
- Support pause and inspection: freeze simulation state at any point for debugging
- Track replay progress and estimated completion time
- Ensure complete isolation: replay environment cannot write to production data stores

**Inputs:** Historical market data from data feeds (yfinance, Dhan archives).
Replay configuration from SC-03 Scenario Manager. Start/stop/pause controls.

**Outputs:** Sequenced market data events to all registered consumers.
Replay progress updates to SC-01 Registry. Completion notification on replay finish.

**Dependencies:** SC-01 Registry; SC-03 Scenario Manager; historical data feeds.
SC-06 Historical Engine (for bar-level data preparation); SC-21 Health Manager.

**Interactions:** Delivers data to SC-12 Decision Simulator, SC-13 Learning
Simulator, SC-14 Risk Simulator. Reports progress to SC-18 Reporting Engine.

**Isolation Guarantee:** The Replay Engine operates in a completely isolated
context. It accesses only read-only copies of historical data. All outputs from
the replay environment are written to simulation-specific result stores, never
to production databases.

**Failure Modes:**
- Data feed unavailable: pause replay; alert; wait for feed restoration.
- Chronological integrity violation (data out of sequence): abort replay; log error; alert.
- Memory exhaustion (very long replay period): checkpoint; resume from checkpoint.

**Recovery Strategy:** Replay checkpoints every 100 bars. On restart, resume from
last checkpoint rather than replaying from the beginning.

**Monitoring:** Replay progress, data delivery latency, memory utilization,
chronological integrity checks.

---

#### SC-06 — Historical Engine

**Purpose:** The primary execution engine for historical simulation (SIM-01).
The Historical Engine applies strategy signal logic to historical bar data,
generating simulated trades and computing performance metrics.

**Responsibilities:**
- Load and validate historical OHLCV data for the specified instruments and period
- Apply the specified strategy's signal logic bar by bar with no look-ahead bias
- Apply the specified transaction cost model (brokerage, STT, exchange fees)
- Apply the specified slippage model to all simulated fills
- Compute the complete performance metric set: Sharpe, Sortino, Calmar, MaxDD,
  Win Rate, Payoff Ratio, trade count, regime breakdown, average holding period
- Execute walk-forward analysis: split data into IS/OOS windows; optimize on IS;
  evaluate on OOS; step forward; repeat
- Compute and record equity curves for all simulation periods
- Store results in SC-03 Scenario Manager artifact store

**Walk-Forward Configuration:**
IS window: 252 sessions (1 year). OOS window: 63 sessions (1 quarter).
Step: 63 sessions (non-overlapping OOS windows). Minimum windows: 4.
Total minimum data requirement: 252 + 4*63 = 504 sessions (approximately 2 years).

**Performance Metric Computation Reference:**
Sharpe Ratio: annualized mean return minus risk-free rate, divided by annualized
return standard deviation. Risk-free rate: RBI repo rate (configurable).
Maximum Drawdown: peak-to-trough decline in NAV, measured over entire simulation period.
Win Rate: number of profitable closed trades divided by total closed trades.
Payoff Ratio: average profit of winning trades divided by average loss of losing trades.
Walk-Forward Efficiency Ratio (WFE): mean OOS Sharpe divided by mean IS Sharpe.

**Inputs:** Strategy definition from L5 StrategyLab. Historical market data.
Scenario parameters from SC-03.

**Outputs:** Full backtest report (performance metrics, equity curve, trade log,
regime analysis). Walk-forward analysis report. All stored in SC-03 artifact store.

**Failure Modes:**
- Data gap > 5 consecutive sessions: flag; if gap is within WFT window, skip window;
  if > 30% of windows affected, abort and report.
- Strategy signal logic error: catch exception; record error; abort run; alert.
- Insufficient data: validate minimum data requirement before starting; reject if not met.

---

#### SC-07 — Synthetic Market Generator

**Purpose:** Generates artificial market data with defined statistical properties
for use in cases where historical data is insufficient, or when testing beyond-
history extreme conditions.

**Responsibilities:**
- Generate synthetic OHLCV price series using the specified statistical model
- Support all generation models: GBM, Jump-Diffusion, Regime-Switching, Heston,
  GARCH
- Calibrate model parameters to match specified target statistics: mean return,
  volatility, autocorrelation, fat-tail coefficient, regime frequency
- Generate multi-asset synthetic series with specified correlation structure
- Store generated series with full parameter provenance (how they were generated)
- Validate statistical properties of generated series against targets
- Support deterministic generation: same seed produces same series (repeatability)

**Statistical Calibration Targets:**
Daily return distribution: mean, standard deviation, skewness, excess kurtosis.
Autocorrelation structure: specified at lags 1, 5, 10, 20 sessions.
Tail behavior: specified as exceedance probability at ±3 standard deviations.
Regime characteristics (for Regime-Switching): regime durations, transition matrix.

**Inputs:** Synthetic market configuration from SC-03 Scenario Manager. Target
statistical parameters. Random seed (for reproducibility).

**Outputs:** Synthetic OHLCV price series (multiple, as specified). Statistical
validation report confirming generated series meets target properties.

**Dependencies:** SC-03 for configuration; SC-15 Performance Evaluator for
statistical validation of generated series.

**Failure Modes:**
- Generated series fails statistical validation: increase iterations; adjust
  generation parameters; alert if repeated failure.
- Calibration target infeasible (e.g., specified kurtosis requires divergent process):
  validate targets before generation; reject infeasible specifications.

---

#### SC-08 — Monte Carlo Engine

**Purpose:** Executes all Monte Carlo simulation types (SIM-07 Monte Carlo,
SIM-08 Bootstrap). Manages the generation of randomized variations, parallel
execution of multiple simulation instances, and aggregation of results into
statistical distributions.

**Responsibilities:**
- Execute trade permutation Monte Carlo: randomize trade order N times;
  recompute performance metrics for each permutation; aggregate into distribution
- Execute price series perturbation Monte Carlo: add random noise to price series
  N times; re-run full historical simulation for each; aggregate
- Execute synthetic history Monte Carlo: generate N synthetic histories using
  SC-07; run full simulation on each; aggregate
- Execute block bootstrap (SIM-08): draw random blocks; construct alternate histories;
  run simulation on each
- Manage parallel execution: distribute simulation instances across available compute
- Aggregate results: compute P5, P10, P25, P50, P75, P90, P95 for all metrics
- Assess statistical significance: compute p-value against null hypothesis
  (strategy has no edge)
- Store full result distributions in SC-03 artifact store

**Parallelization:** Monte Carlo runs are embarrassingly parallel (each iteration
is independent). SC-08 manages a work queue; each iteration is an independent task.
Target: 500 iterations in < 30 minutes.

**Inputs:** Strategy definition; historical trade record (for permutation MC);
historical price series (for perturbation MC); SC-07 synthetic series (for
synthetic MC); scenario configuration from SC-03.

**Outputs:** Distribution report: percentile estimates for all performance metrics.
Significance test results. Full iteration results stored in SC-03.

**Failure Modes:**
- Partial iteration failure: exclude failed iterations; document in results; if >
  10% iterations fail, abort and investigate.
- Memory exhaustion: reduce batch size; checkpoint intermediate aggregates.

---

#### SC-09 — Stress Testing Engine

**Purpose:** Executes all stress simulation types (SIM-09 Stress Testing, SIM-10
Crash Simulation, SIM-11 Liquidity Simulation). The Stress Testing Engine applies
predefined or operator-specified adverse market conditions to evaluate strategy and
portfolio resilience.

**Responsibilities:**
- Maintain the Stress Scenario Library: historical and hypothetical scenarios
- Apply historical crisis data to strategy signal logic with crisis-appropriate
  fill models (expanded slippage, partial fills, circuit breakers)
- Generate hypothetical stress scenarios using SC-07 Synthetic Market Generator
- Execute crash simulation with non-linear fill degradation during large moves
- Execute liquidity stress simulation with depth-adjusted fill models
- Compute stress-specific metrics: maximum stress drawdown, time-to-recovery,
  percentage of capital at risk, kill-switch trigger frequency
- Assess whether risk rules and kill switches fire at the expected thresholds
  during each stress scenario
- Generate stress test report: performance under each scenario; worst-case analysis

**Stress Scenario Application:**
For each stress scenario, the engine: (1) loads the stress period historical data
or generates synthetic stress data; (2) applies the strategy signal logic with
stress fill models; (3) simulates the kill switch behavior (does L9 RiskGuardian
trigger correctly?); (4) computes all standard metrics plus stress-specific metrics.

**Kill Switch Validation:** During every stress simulation, the Stress Testing
Engine explicitly validates that the L9 RiskGuardian kill switch would have triggered
correctly. This is the stress test's most important output for system governance.

**Inputs:** Stress scenario definition from SC-03. Strategy definitions from L5.
Historical crisis data. SC-07 synthetic scenarios (for hypothetical stress tests).

**Outputs:** Stress test report per scenario. Portfolio stress summary.
Kill switch validation results. Results stored in SC-03 artifact store.

**Failure Modes:**
- Historical crisis data unavailable: flag; use synthetic approximation; note in report.
- Kill switch simulation failure: CRITICAL alert; halt stress run; notify operator.

---

#### SC-10 — Execution Simulator

**Purpose:** Models the complete order execution lifecycle (SIM-14 Execution
Simulation) including order routing, fill modeling, partial fills, rejections,
and settlement. The Execution Simulator ensures that strategy backtests reflect
realistic execution conditions.

**Responsibilities:**
- Model market order fills: immediate fill at open of next bar; slippage applied
- Model limit order fills: fill when price reaches limit; partial fill if insufficient volume
- Model stop-loss fills: triggered when bar touches stop price; may fill at gap price
  in volatile conditions
- Model bracket orders: simultaneous stop-loss and take-profit; correct cancellation
  of surviving leg on fill
- Apply slippage model (from SC-12 configuration): fixed, volume-adjusted, or combined
- Apply volume participation limit: order cannot fill more than N% of bar volume
  (default: 10% for large-cap, 5% for mid/small-cap)
- Apply circuit breaker handling: orders cannot fill during circuit breaker periods
- Compute execution quality metrics: average slippage per trade, fill rate, rejection rate
- Apply latency model (SIM-13): introduce fill delays per configuration

**Fill Decision Logic:**
Market orders: fill at open of next bar + slippage; if bar opens with gap beyond
stop, fill at gap price (gap risk).
Limit orders: fill only if bar trades through the limit price; fill price = limit price.
Stop orders: trigger if bar high/low touches stop; fill at stop + slippage or gap price.

**Inputs:** Order events from strategy signal logic (via SC-06 or SC-11). Fill
configuration from SC-03 Scenario Manager. Tick/bar data from SC-05 Replay Engine.

**Outputs:** Fill records for all orders: fill price, fill size, slippage applied,
latency applied, rejection reason (if applicable). Execution quality report.

**Failure Modes:**
- Fill model logic error: validate fill logic against known test cases on startup.
- Volume data unavailable for volume-participation limit: apply fixed participation;
  flag in results.

---

#### SC-11 — Portfolio Simulator

**Purpose:** Simulates the complete portfolio — all active strategies running
simultaneously — to evaluate portfolio-level behavior, correlation effects,
drawdown diversification benefits, and allocation efficiency (SIM-15 Portfolio
Simulation, SIM-16 Multi-Asset, SIM-17 Cross-Market).

**Responsibilities:**
- Run multiple strategy signal generators simultaneously, sharing the same market data
- Apply portfolio-level position sizing: equal risk contribution; volatility targeting;
  maximum capital per strategy
- Track total portfolio exposure: total long + short; sector concentration; beta
- Compute portfolio-level performance metrics: total return, portfolio Sharpe,
  portfolio MaxDD, portfolio win rate, correlation matrix of strategy returns
- Evaluate diversification: portfolio drawdown vs average individual strategy drawdown
  (diversification benefit = reduction in portfolio MaxDD below average individual MaxDD)
- Test portfolio rebalancing rules: periodic equal-weight rebalance; volatility-
  targeted rebalance; performance-weighted rebalance
- Validate that portfolio allocation rules prevent over-concentration in any single
  strategy, sector, or instrument

**Portfolio Simulation Result Metrics:**
Portfolio Sharpe (portfolio-level, not average of strategy Sharpes).
Portfolio MaxDD. Correlation matrix: strategy returns pairwise.
Marginal contribution: each strategy's contribution to portfolio risk (variance).
Maximum simultaneous drawdown: worst session for the portfolio.
Strategy alpha: strategy return minus its beta contribution to the portfolio.

**Inputs:** Strategy definitions for all strategies in the portfolio simulation.
Historical market data for all instruments. Portfolio configuration (allocation
method, rebalancing rules). SC-10 Execution Simulator for fill modeling.

**Outputs:** Portfolio simulation report. Correlation matrix. Diversification
analysis. Allocation efficiency analysis. All stored in SC-03.

**Failure Modes:**
- Strategy signal error: isolate failing strategy; continue simulation with
  remaining strategies; flag in results.
- Correlation matrix computation failure (data quality): use cached matrix; flag in results.

---

#### SC-12 — Decision Simulator

**Purpose:** Replays historical decision events through the DebateAndDecision
system (L10) to validate decision system consistency, detect regressions, and
study how decisions would have differed under alternative configurations
(SIM-18 AI Decision Simulation).

**Responsibilities:**
- Replay historical decision inputs: strategy signals, regime classification,
  risk budget, capital available, at the exact state they were at the time of
  the original decision
- Feed inputs through the current L10 DebateAndDecision logic
- Compare replayed decision output to the original decision:
  (a) determinism check: same inputs produce same output
  (b) regression check: modified system produces acceptable differences
- Support what-if analysis: replay with modified decision thresholds or agent
  weights to evaluate the effect of proposed changes
- Capture decision audit trail: for each replayed decision, record all agent
  votes, confidence levels, debate duration, final recommendation

**Decision Determinism Standard:** Given identical inputs, the Decision Engine
must produce identical outputs on replay. Any non-determinism (random components,
external state dependencies) must be explicitly modeled and justified.

**Inputs:** Historical decision records (from L17 ControlTower audit logs).
Current L10 DebateAndDecision configuration. Replay time range.

**Outputs:** Decision replay report: original decision vs replayed decision.
Determinism test results. What-if analysis results (if requested).
Decision quality analysis: percentage agreement, disagreement analysis.

**Failure Modes:**
- Historical decision records unavailable: alert; cannot proceed without records.
- L10 non-determinism detected: escalate to System Owner; investigate cause.

---

#### SC-13 — Learning Simulator

**Purpose:** Replays the learning cycle through the LearningSystem (L13) to
validate that learning mechanisms are functioning correctly, learning is stable,
and attribution is accurate (SIM-19 Learning Simulation).

**Responsibilities:**
- Replay historical trade outcomes through the LearningEngine
- Validate that attribution logic correctly assigns performance credit to the
  right signals and strategies
- Test learning stability: does the model update process converge, or oscillate?
- Validate learning direction: do model updates improve subsequent performance?
  (Learning replay is used to check that after a loss period, the LearningEngine
  correctly adjusted the model to be more cautious on the pattern that caused losses)
- Simulate alternative learning rates: what would have happened if the learning
  rate was higher or lower?
- Validate that strategy weight adjustments by L3 MetaLearning are directionally
  correct based on the replayed learning history

**Learning Quality Metrics:**
Attribution accuracy: fraction of attribution correctly assigned to profitable signals.
Model update stability: variance of model weight updates per session.
Predictive value of learning: performance improvement in the 20 sessions following
each major model update vs performance before the update.

**Inputs:** Historical trade records from L13 LearningSystem (outcome, signal,
strategy, regime). Learning model snapshots at each historical period.

**Outputs:** Learning replay report: attribution analysis, stability analysis,
predictive value analysis. Recommendations for learning rate or model adjustments.

**Failure Modes:**
- Historical model snapshots unavailable: flag; learning simulation proceeds
  with current model parameters; note limitation in report.

---

#### SC-14 — Risk Simulator

**Purpose:** Replays risk rule logic against historical data to validate that risk
rules fire correctly at the intended thresholds, and to test proposed risk rule
changes before deploying them (SIM-09 in risk validation context).

**Responsibilities:**
- Replay historical market conditions through the risk rule set (L7 RiskControl)
- Validate that all risk rules triggered at the correct thresholds during historical
  periods of high risk (VIX spikes, large drawdowns, correlation breakdowns)
- Validate that the kill switch (L9 RiskGuardian) would have triggered correctly
  during historical crisis scenarios
- Test proposed risk rule changes: what would have happened if the rule had been
  in place during the historical period?
- Compute false positive rate: how many times would the risk rule have triggered
  unnecessarily during normal market conditions?
- Compute false negative rate: how many times would the risk rule have failed to
  trigger during a period that did require intervention?
- Test kill switch calibration: is the VIX > 45 threshold appropriate, or was
  there a better threshold given historical behavior?

**Inputs:** Historical market data (VIX, NIFTY levels, portfolio P&L history).
Current risk rule definitions from L7. Kill switch configuration from L9.
Proposed alternative rule configurations (for testing proposed changes).

**Outputs:** Risk rule validation report. Kill switch calibration report.
False positive and false negative analysis. All stored in SC-03.

**Failure Modes:**
- Historical VIX data unavailable: substitute India VIX; flag in report.
- Risk rule logic error (throws exception): catch; log; abort run; alert.

---

#### SC-15 — Performance Evaluator

**Purpose:** The central metrics computation and quality scoring engine for all
simulation results. The Performance Evaluator computes the complete set of
performance metrics for any simulation result and assigns a Simulation Quality
Score (SimQS) based on the quality framework defined in Part VII.

**Responsibilities:**
- Compute all standard performance metrics: Sharpe, Sortino, Calmar, MaxDD,
  Win Rate, Payoff Ratio, CAGR, Information Ratio, WFE, MAE, MFE, trade count
- Compute regime-conditioned metrics: performance broken down by market regime
- Compute period-conditioned metrics: performance by year, by quarter, by month
- Compute statistical significance: p-value of returns vs null hypothesis
- Compute SimQS: the composite quality score for the simulation result
- Compare result to benchmark (NIFTY50 BM-01): compute alpha, beta, information ratio
- Flag anomalies: unusually high or low performance that may indicate data or
  logic errors requiring investigation before acceptance
- Generate metric summary tables for inclusion in simulation reports

**SimQS Definition:** The Simulation Quality Score measures the quality of the
simulation result itself (not the strategy). A high SimQS indicates that the
result is valid, statistically significant, and trustworthy. A low SimQS indicates
that the result is unreliable or of questionable quality.

**SimQS Dimensions:** Covered in detail in Part VII.

**Inputs:** Simulation results from any Tier 2 execution engine. Benchmark data
(NIFTY50 daily returns). Risk-free rate (RBI repo rate).

**Outputs:** Performance metric report (full metric set). SimQS with dimension
breakdown. Benchmark comparison. Anomaly flags. All stored in SC-03.

**Failure Modes:**
- Insufficient trade count for statistics (< 20 trades): produce partial metrics;
  flag as statistically unreliable; do not compute SimQS.
- Benchmark data unavailable: produce metrics without benchmark comparison; flag.

---

#### SC-16 — Simulation Validator

**Purpose:** Validates the integrity, completeness, and technical correctness of
simulation results before they are accepted, stored, and used for decision-making.

**Responsibilities:**
- Verify that the simulation ran to completion without errors
- Verify that no look-ahead bias was present in the simulation
- Verify that the transaction cost model was applied correctly to all trades
- Verify that the slippage model was applied consistently
- Check for data quality issues that may have contaminated results (gaps, outliers)
- Verify that the metric computations are internally consistent (e.g., win rate
  is derivable from the trade log)
- Verify that the hash of the input scenario matches the scenario that was executed
  (confirms no configuration change during execution)
- Issue a validation certificate for results that pass all checks

**Validation Checks:**
V-01: Completion check — simulation ran to end; no abrupt termination.
V-02: Look-ahead check — signal logic uses only data available at signal time.
V-03: Cost model check — all trades have transaction costs applied.
V-04: Slippage check — all fills have slippage applied; no zero-slippage fills.
V-05: Trade count plausibility — trade count is within plausible range for the
  strategy type and time period.
V-06: Metric consistency — all metrics computable from trade log; no inconsistencies.
V-07: Input integrity — input scenario hash matches executed scenario configuration.
V-08: Data quality — no data gaps > 3 bars in critical periods; no price outliers
  (> 10 sigma from local average).

**Inputs:** Completed simulation result from any Tier 2 engine. Input scenario
definition. Trade log. Metric summary.

**Outputs:** Validation certificate (PASS / FAIL per check). Validated simulation
result. Invalid results are quarantined — not stored in main artifact store —
until investigated and resolved.

**Failure Modes:**
- Validation check exception: treat as FAIL for that check; continue remaining checks.
- Critical check failure (V-01, V-02): immediately quarantine result; alert operator.

---

### 3.4 — TIER 4 COMPONENTS — GOVERNANCE AND INTELLIGENCE

---

#### SC-17 — Simulation Analytics Engine

**Purpose:** Discovers cross-simulation patterns, tracks performance trends across
multiple simulation runs, identifies systematic biases in simulation results, and
provides the analytical intelligence that makes the Simulation Engine a learning
system rather than a single-use evaluation tool.

**Responsibilities:**
- Aggregate results across multiple simulation runs for the same strategy:
  track how simulated performance evolves over time as the strategy is updated
- Compute cross-simulation comparisons: how does this strategy's simulation result
  compare to all other strategies of the same type?
- Identify systematic biases: strategies that consistently outperform in simulation
  but underperform in live trading (a signal of simulation-to-live gap problems)
- Track simulation-to-live gap: compare simulated performance to subsequent live
  performance for each strategy; flag when the gap exceeds acceptable bounds
- Detect simulation coverage gaps: which strategies are missing required simulation types?
- Generate trend reports: how is the simulation library's overall quality evolving?
- Support simulation portfolio analysis: cross-strategy correlation in simulation results

**Simulation-to-Live Gap Definition:**
The difference between a strategy's simulated Sharpe Ratio and its subsequent
live Sharpe Ratio. Target gap: < 0.30 (live Sharpe within 0.30 of simulated Sharpe).
A gap > 0.50 triggers investigation of the simulation methodology for that strategy type.

**Inputs:** All simulation results from SC-01 Registry. Live performance data from
L13 LearningSystem. Simulation-to-live gap data for all strategies.

**Outputs:** Cross-simulation analysis reports. Simulation-to-live gap report.
Coverage gap report. Trend analysis. All stored and delivered to SC-18 for reporting.

**Failure Modes:**
- Insufficient simulation history (new system): produce partial analysis; flag.

---

#### SC-18 — Simulation Reporting Engine

**Purpose:** Generates all simulation reports, delivers them to operators and the
L17 ControlTower dashboard, and maintains the record of all reports generated.

**Responsibilities:**
- Generate post-simulation reports immediately upon simulation completion
- Generate daily simulation summary reports: all simulations run today; results summary
- Generate weekly simulation dashboard: trend analysis; coverage status; notable results
- Generate monthly simulation quality report: SimQS trends; simulation-to-live gaps;
  methodology review recommendations
- Deliver reports via Telegram (summary alerts) and L17 ControlTower dashboard (full)
- Maintain report archive: all reports stored with full content and metadata
- Generate governance reports: simulation results that require governance review

**Report Types:**
Post-Simulation Report: immediate delivery upon completion; result summary, SimQS,
validation certificate, key metrics, recommendation.
Daily Summary: list of all simulations run; results; any failures; coverage updates.
Weekly Dashboard: trends; simulation-to-live gap updates; notable results.
Monthly Quality Report: full quality analysis; recommendations for methodology updates.
Governance Report: any simulation results requiring operator review or approval.

**Inputs:** Completed simulation results from SC-15 Performance Evaluator.
Validation certificates from SC-16. Analytics from SC-17. SC-20 audit summaries.

**Outputs:** Reports delivered to L17 ControlTower; Telegram notifications; report archive.

---

#### SC-19 — Simulation Governance Manager

**Purpose:** Manages all governance events in the Simulation Engine: simulation
run approvals, result acceptance, methodology changes, compliance monitoring,
and human override tracking.

**Responsibilities:**
- Track all governance events (simulation submissions, results, approvals, overrides)
- Enforce approval workflows for high-consequence simulation types (stress tests
  used for risk calibration require Operations Lead sign-off)
- Record human overrides of automated simulation recommendations
- Ensure compliance: simulations for strategy promotion must use approved scenario
  definitions and standard transaction cost models
- Generate daily governance reports for operator review
- Flag simulations that use non-standard configurations
- Track pending approvals and escalate when overdue

**Approval Workflow:**
Standard simulations (backtesting, Monte Carlo): automated approval if SimQS >= 0.55.
Risk-calibration simulations (stress tests used to set kill switch thresholds):
require Operations Lead review.
Methodology changes (changing transaction cost model, slippage model): require
System Owner approval.

**Inputs:** All simulation events from SC-01 Registry. Governance configuration
(approval thresholds, required approvers).

**Outputs:** Governance records. Approval notifications. Compliance alerts.
Governance reports.

---

#### SC-20 — Simulation Audit Manager

**Purpose:** Maintains the hash-chained audit trail for all Simulation Engine events,
providing tamper detection and a complete, permanent record of all simulation activities.

**Responsibilities:**
- Create an audit record for every governance event in the Simulation Engine
- Chain each audit record with SHA-256 hash of the previous record
- Verify chain integrity on request and on scheduled checks
- Support forensic queries: reconstruct the full history of any simulation run
- Generate hash-chain integrity reports
- Alert immediately if hash chain break is detected

**Audit Record Required Fields:**
audit_id, timestamp, event_type, simulation_id (if applicable), operator_id (if human),
component_id, inputs_hash, outputs_hash, governance_result, previous_record_hash.

**Hash Chain Format:** SHA-256 hash of: audit_id + timestamp + event_type +
simulation_id + operator_id + inputs_hash + outputs_hash + previous_record_hash.

**Integrity Check Schedule:** On every simulation completion; on every governance
event; scheduled check every 60 minutes during market hours.

**Failure Modes:**
- Hash chain break detected: HALT governance operations; alert immediately;
  investigate source (data corruption vs unauthorized modification).

---

#### SC-21 — Simulation Health Manager

**Purpose:** Computes and monitors the Simulation Engine Health Score (SEHS) —
a composite measure of the operational health of all 21 components — and triggers
alerts and operational responses based on health thresholds.

**Responsibilities:**
- Collect health metrics from all 21 components every 60 seconds
- Compute SEHS: weighted average of all component health scores
- Track SEHS trend: is engine health improving, stable, or declining?
- Trigger alerts at configured thresholds: WARNING (SEHS < 0.75), CRITICAL (< 0.55),
  FAILED (< 0.30)
- Recommend operational adjustments when health degrades (e.g., pause new simulation
  submissions when SEHS < NOMINAL)
- Generate health trend reports for daily and weekly reporting
- Perform startup health check: all components must reach NOMINAL before first
  simulation run of the day is accepted

**SEHS Tiers:**
OPTIMAL (0.90–1.00): All systems full capability. All simulation types available.
NOMINAL (0.75–0.89): Normal operation. All simulation types available.
DEGRADED (0.55–0.74): Reduced capability. Non-critical simulation types suspended.
CRITICAL (0.30–0.54): Significant capability loss. Only essential simulations run.
FAILED (0.00–0.29): Engine unavailable. Halt all simulation runs. Alert immediately.

---

## PART IV — SIMULATION LIFECYCLE

### 4.1 — Lifecycle Overview

Every simulation run proceeds through a defined lifecycle from inception to archive.
The lifecycle provides consistent governance, traceability, and quality assurance
for every simulation result produced by the Simulation Engine.

`
SIMULATION LIFECYCLE — STATE DIAGRAM
═════════════════════════════════════

 REQUESTED ──► VALIDATING ──► QUEUED ──► RUNNING
                   │                        │
                   │ (invalid)              │ (error)
                   ▼                        ▼
                REJECTED               FAILED ──► ARCHIVED (failure)
                                           │
                              (success)    │
                                           ▼
                                      COMPLETED ──► VALIDATING RESULT
                                                            │
                                               (invalid)   │   (valid)
                                                  ▼        │    ▼
                                             QUARANTINED   ▼   ACCEPTED
                                                      PENDING REVIEW
                                                           │
                                               (approved)  │
                                                           ▼
                                                       APPROVED ──► ARCHIVED
`

---

### 4.2 — Lifecycle Stage Specifications

---

**SLS-01 — Scenario Definition**

Entry criteria: A simulation need has been identified. This may be triggered by:
(a) a strategy promotion request requiring backtesting, (b) a risk review requiring
stress testing, (c) a routine scheduled simulation, or (d) an operator request.

Activities: Operator or automated system defines the scenario using SC-03 Scenario
Manager. All required fields must be populated. Scenario type is selected from
SIM-01 through SIM-21. Asset universe, time period, and configuration parameters
are specified.

Validation: SC-03 validates scenario internal consistency (e.g., time period
contains sufficient data for the specified simulation type). Scenario is assigned
a scenario_id.

Exit criteria: Scenario definition validated and stored in SC-03 with status DRAFT.

---

**SLS-02 — Environment Preparation**

Entry criteria: Scenario definition in DRAFT status; simulation run requested.

Activities: SC-01 Registry assigns SRI. SC-21 Health Manager confirms SEHS >= NOMINAL.
Required data sources identified and confirmed available. Required compute resources
confirmed available. Simulation environment (isolated, read-only data access) configured.

Exit criteria: SRI assigned; environment confirmed; simulation added to execution queue.

---

**SLS-03 — Data Loading**

Entry criteria: Simulation in QUEUED status; execution has started.

Activities: Historical data loaded for specified instruments and time period.
Data quality validation: check for gaps, outliers, stale prices. Benchmark data
loaded (NIFTY50). Any required synthetic data generated by SC-07.

Exit criteria: All required data loaded and validated. Data quality report attached
to simulation run record.

Failure: If data loading fails or data quality insufficient, simulation transitions
to FAILED. Full data quality report stored. Operator notified.

---

**SLS-04 — Simulation Validation**

Entry criteria: Data loaded successfully.

Activities: Pre-run validation: confirm scenario definition is complete; confirm
data covers the specified time period; confirm strategy or component under test
is available and correctly loaded; confirm transaction cost and slippage
configuration is complete.

Exit criteria: All pre-run checks pass. Simulation transitions to RUNNING.

Failure: Any pre-run check failure → simulation transitions to FAILED.

---

**SLS-05 — Simulation Initialization**

Entry criteria: Validation passed.

Activities: Initialize all execution engine components for this run. Set starting
capital, starting portfolio state, regime state at start of simulation period.
Initialize performance tracking (equity curve, trade log). Initialize execution
simulator with correct fill configuration.

Exit criteria: All components initialized. Clock set to simulation start time.
First data bar loaded. Ready to execute.

---

**SLS-06 — Execution**

Entry criteria: Initialization complete.

Activities: Bar-by-bar (or tick-by-tick) simulation execution. Each bar: load
next data event; evaluate strategy signal logic with data available through
previous bar only; generate signals; submit to execution simulator; process fills;
update portfolio state; record trade events; update performance tracker.

For Monte Carlo: execute N parallel iterations; aggregate results continuously.
For Stress Testing: apply stress fill model during stress period.

Monitoring: SC-21 monitors execution progress; estimated completion time tracked;
errors captured and logged.

Exit criteria: Simulation runs through all specified bars/ticks to the end of the
specified period. Final portfolio state recorded.

Failure: Any unhandled exception: capture state; record error; transition to FAILED.

---

**SLS-07 — Monitoring**

Entry criteria: Simulation running.

Activities: Parallel to execution (SLS-06). SC-21 Health Manager tracks execution
progress, memory utilization, compute resource usage. Alerts if execution is running
significantly longer than expected (> 2x estimated time: WARNING; > 4x: CRITICAL).
Alerts if memory utilization exceeds threshold.

This is a continuous parallel stage, not a sequential stage.

---

**SLS-08 — Metric Collection**

Entry criteria: Execution complete.

Activities: SC-15 Performance Evaluator computes full metric set from the trade log
and equity curve. All standard metrics computed. Benchmark comparison computed.
SimQS computed. Statistical significance computed.

Exit criteria: Full metric set stored in SC-03. SimQS computed and recorded in SC-01.

---

**SLS-09 — Result Analysis**

Entry criteria: Metrics computed.

Activities: SC-16 Simulation Validator runs all 8 validation checks (V-01 through
V-08). If all pass: validation certificate issued; result transitions to ACCEPTED.
If any critical check fails: result transitions to QUARANTINED.
SC-17 Simulation Analytics Engine: compare result to simulation history for this
strategy and type; generate cross-simulation context.

Exit criteria: Validation certificate issued (PASS or FAIL per check). Result
transitions to ACCEPTED or QUARANTINED.

---

**SLS-10 — Learning**

Entry criteria: Result in ACCEPTED status.

Activities: SC-17 Analytics Engine updates simulation-to-live gap tracking if
this is a strategy with live history. Any learning signals derived from the
simulation results are passed to L13 LearningSystem (e.g., simulation confirmed
that a learning model update improved OOS performance). SC-13 Learning Simulator
updates are recorded.

---

**SLS-11 — Approval**

Entry criteria: Result accepted and analyzed.

Activities: SC-19 Governance Manager evaluates whether this simulation result
requires human approval. Standard backtesting results with SimQS >= 0.55: auto-
approved. Stress test results used for kill switch calibration: require Operations
Lead review. Governance record created regardless of approval path.

Exit criteria: Result status = APPROVED. Governance record created.
SC-18 generates post-simulation report and delivers to operator.

---

**SLS-12 — Archive**

Entry criteria: Result approved.

Activities: SC-03 Scenario Manager: compress artifacts; create archive record.
SC-20 Audit Manager: close audit chain for this simulation run; hash chain
integrity verified; terminal hash record created. SC-01 Registry: status updated
to ARCHIVED. SC-18 generates final archive notification.

Terminal state: No exits from ARCHIVED. All simulation artifacts are preserved
permanently.

---

### 4.3 — Lifecycle Timing Reference

| Stage          | Name                   | Expected Duration        | Maximum Duration       |
|----------------|------------------------|--------------------------|------------------------|
| SLS-01         | Scenario Definition    | 5–30 minutes (manual)    | Unbounded (human)      |
| SLS-02         | Environment Prep       | < 30 seconds             | 5 minutes              |
| SLS-03         | Data Loading           | 10–120 seconds           | 10 minutes             |
| SLS-04         | Validation             | < 30 seconds             | 2 minutes              |
| SLS-05         | Initialization         | < 10 seconds             | 1 minute               |
| SLS-06         | Execution (backtest)   | 30–300 seconds           | 2 hours                |
| SLS-06         | Execution (Monte Carlo)| 5–30 minutes             | 3 hours                |
| SLS-06         | Execution (stress test)| 10–60 minutes            | 2 hours                |
| SLS-07         | Monitoring (parallel)  | Concurrent with SLS-06   | Concurrent             |
| SLS-08         | Metric Collection      | 5–60 seconds             | 5 minutes              |
| SLS-09         | Result Analysis        | 10–120 seconds           | 10 minutes             |
| SLS-10         | Learning               | < 60 seconds             | 5 minutes              |
| SLS-11         | Approval (auto)        | < 10 seconds             | 30 minutes (human)     |
| SLS-12         | Archive                | 30–120 seconds           | 15 minutes             |

---

## PART V — SIMULATION SERVICES

### 5.1 — Service Architecture Overview

Simulation Services provide the structured operational interface between the
Simulation Engine components and the rest of IIOS. While components perform the
work, services define the contracts — the inputs, outputs, and behaviors that
consuming systems can rely on.

---

**SS-01 — Replay Service**

Purpose: Provides the interface for requesting and managing all replay-based
simulations (SIM-03, SIM-04, SIM-05). Consuming systems (L5 StrategyLab, L16
ValidationEngine) use the Replay Service to request historical replays without
needing to know which internal component executes them.

Primary interactions: SC-05 Replay Engine; SC-06 Historical Engine; SC-03 Scenario Manager.
Interface: submit_replay(scenario_id, strategy_id) → SRI; get_status(SRI) → status;
get_results(SRI) → result_summary.

---

**SS-02 — Scenario Service**

Purpose: Provides the interface for creating, validating, retrieving, and managing
simulation scenarios. All scenario lifecycle operations flow through this service.

Primary interactions: SC-03 Scenario Manager; SC-04 Version Manager; SC-19 Governance.
Interface: create_scenario(definition) → scenario_id; validate_scenario(scenario_id) → validation_result;
get_scenario(scenario_id) → scenario_definition; list_scenarios(filter) → scenario_list.

---

**SS-03 — Execution Service**

Purpose: Provides the order execution simulation interface for all simulation runs.
Any component that needs to model order fills in a simulation context uses this service.

Primary interactions: SC-10 Execution Simulator; SC-12 Slippage configuration.
Interface: submit_order(order_spec, fill_config) → fill_record; configure_fill_model(params).

---

**SS-04 — Portfolio Service**

Purpose: Provides the portfolio simulation interface for multi-strategy simulation runs.

Primary interactions: SC-11 Portfolio Simulator.
Interface: run_portfolio_simulation(strategy_set, allocation_config, scenario_id) → SRI.

---

**SS-05 — Risk Service**

Purpose: Provides the risk simulation interface for stress testing and risk rule
replay. Used by L7 RiskControl and L9 RiskGuardian for rule calibration.

Primary interactions: SC-09 Stress Testing Engine; SC-14 Risk Simulator.
Interface: run_stress_test(scenario_id, strategy_id) → SRI;
run_risk_replay(time_period, rule_config) → SRI.

---

**SS-06 — Learning Service**

Purpose: Provides the learning simulation interface. Used by L13 LearningSystem
to validate learning mechanisms before deploying updates.

Primary interactions: SC-13 Learning Simulator.
Interface: run_learning_replay(time_period, learning_config) → SRI.

---

**SS-07 — Analytics Service**

Purpose: Provides the analytics interface for simulation result retrieval, cross-
simulation comparison, and simulation-to-live gap analysis.

Primary interactions: SC-17 Simulation Analytics Engine.
Interface: get_result(SRI) → full_result; compare_results(SRI_list) → comparison_report;
get_simulation_to_live_gap(strategy_id) → gap_report.

---

**SS-08 — Reporting Service**

Purpose: Provides the reporting interface for all simulation reports.

Primary interactions: SC-18 Simulation Reporting Engine.
Interface: get_report(report_id) → report; list_reports(filter) → report_list;
request_custom_report(spec) → report_id.

---

**SS-09 — Validation Service**

Purpose: Provides the simulation result validation interface. Used to confirm
simulation integrity before results are accepted for strategy promotion.

Primary interactions: SC-16 Simulation Validator.
Interface: validate_result(SRI) → validation_certificate.

---

**SS-10 — Audit Service**

Purpose: Provides the audit trail interface. Used by all components that need
to record events and by governance to query the audit history.

Primary interactions: SC-20 Simulation Audit Manager.
Interface: record_event(event) → audit_id; get_history(filter) → audit_records;
verify_chain_integrity() → integrity_report.

---

**SS-11 — Governance Service**

Purpose: Provides the governance interface for simulation approvals, compliance
checks, and override management.

Primary interactions: SC-19 Simulation Governance Manager.
Interface: submit_for_approval(SRI) → approval_status; record_override(override_spec);
get_governance_report(date) → governance_report.

---

**SS-12 — Archive Service**

Purpose: Provides the artifact archive interface — writing and reading simulation
result archives.

Primary interactions: SC-03 Scenario Manager (artifact store).
Interface: archive_result(SRI) → archive_id; retrieve_artifact(archive_id, artifact_type) → artifact.

---

**SS-13 — Health Service**

Purpose: Provides the health monitoring interface for all components and external
consumers.

Primary interactions: SC-21 Simulation Health Manager.
Interface: get_sehs() → sehs_score; get_component_health(component_id) → score;
get_health_report() → health_report.

---

**SS-14 — Version Management Service**

Purpose: Provides the version management interface for scenario definitions and
simulation configurations.

Primary interactions: SC-04 Simulation Version Manager.
Interface: create_version(scenario_id, change_spec) → new_version;
rollback(scenario_id, target_version) → rollback_result;
get_version_history(scenario_id) → version_history.

---

## PART VI — SIMULATION PROCESSING PIPELINES

### 6.1 — Pipeline Architecture Overview

The Simulation Engine operates 11 processing pipelines. Each pipeline is a
defined sequence of components that executes a specific simulation or analysis
task. Pipelines are the primary execution pathways — they define exactly how a
simulation request flows through the engine to produce results.

---

### SP-01 — Historical Replay Pipeline

`
HISTORICAL REPLAY PIPELINE
════════════════════════════════════════════════════

 [Trigger] Strategy promotion request OR scheduled backtest
     │
     ▼
 [SC-03] Scenario definition loaded
     │
     ▼
 [SC-02] Simulation type classified as SIM-01 or SIM-05 (bar replay)
     │
     ▼
 [SC-01] SRI assigned; run registered as QUEUED
     │
     ▼
 [SC-21] SEHS check: must be >= NOMINAL
     │
     ▼
 [Data Layer] Historical OHLCV loaded; data quality validated
     │
     ▼
 [SC-05] Replay Engine: time clock initialized; bars sequenced
     │
     ▼
 [SC-06] Historical Engine: bar-by-bar execution
     │   signal logic applied at each bar
     │   fills via SC-10 Execution Simulator
     │   performance tracked continuously
     │
     ▼
 [SC-15] Performance Evaluator: full metric set computed
     │
     ▼
 [SC-16] Simulation Validator: V-01 through V-08
     │
     ├──(PASS)──► [SC-19] Governance: auto-approve if SimQS >= 0.55
     │                  │
     │                  ▼
     │            [SC-18] Report generated; delivered to L17, Telegram
     │                  │
     │                  ▼
     │            [SC-20] Audit chain updated
     │                  │
     │                  ▼
     │            [SC-03] Artifacts archived → ARCHIVED
     │
     └──(FAIL)──► [SC-01] Status = QUARANTINED; operator alert
`

---

### SP-02 — Paper Trading Pipeline

`
PAPER TRADING PIPELINE
════════════════════════════════════════════════════

 [Trigger] Strategy approved and ready for paper trading phase
     │
     ▼
 [SC-03] Paper trading scenario configured:
     │   live data feeds; PAPER_TRADING=True flag; paper ledger initialized
     │
     ▼
 [SC-01] SRI assigned; run registered as RUNNING (continuous)
     │
     ▼
 [Live Data] Real-time market data (same feeds as production)
     │
     ▼
 [L5 StrategyLab] Strategy signal generation: normal live pathway
     │
     ▼
 [L11 OrderManager] PAPER_TRADING=True → orders routed to paper ledger
     │
     ▼
 [SC-10] Execution Simulator: simulated fills recorded
     │
     ▼
 [SC-15] Rolling performance tracked (session P&L, cumulative P&L)
     │
     ▼
 [SC-21] Ongoing health monitoring; alerts if paper trading errors
     │
     ▼
 [End of Session] SC-18 generates daily paper trading report
     │
     ▼
 After minimum 10 sessions:
 [SC-16] Validator: operational checks (not statistical — sample too small)
     │
     ▼
 [SC-19] Governance: paper trading phase approval → strategy may advance to live
`

---

### SP-03 — Monte Carlo Pipeline

`
MONTE CARLO PIPELINE
════════════════════════════════════════════════════

 [Trigger] Strategy passed SP-01 Historical Replay; Monte Carlo required
     │
     ▼
 [SC-03] Monte Carlo scenario loaded: iteration count, perturbation type, seed
     │
     ▼
 [SC-08] Monte Carlo Engine: prepare iteration batch (N iterations)
     │
     ▼
 For each iteration (parallelized):
     │
     ├──[PERMUTATION MC]
     │   Randomize trade order → recompute metrics → store iteration result
     │
     ├──[PERTURBATION MC]
     │   Add random noise to price series → rerun SP-01 → store result
     │
     └──[SYNTHETIC MC]
         SC-07 generates synthetic price series → rerun SP-01 → store result
     │
     ▼
 [SC-08] Aggregate N iteration results:
     │   Compute P5, P10, P25, P50, P75, P90, P95 for all metrics
     │   Compute significance test (p-value vs null hypothesis)
     │
     ▼
 [SC-15] SimQS computed for Monte Carlo result
     │
     ▼
 [SC-16] Validation: check that at least 90% of iterations completed
     │
     ▼
 [SC-19] Governance: Monte Carlo result added to strategy promotion evidence
     │
     ▼
 [SC-18] Monte Carlo report generated → L17, Telegram, strategy promotion dossier
`

---

### SP-04 — Stress Test Pipeline

`
STRESS TEST PIPELINE
════════════════════════════════════════════════════

 [Trigger] Strategy promotion OR periodic risk review OR operator request
     │
     ▼
 [SC-03] Stress scenario library loaded:
     │   Select applicable stress scenarios (e.g., all 6 historical crises)
     │
     ▼
 For each stress scenario:
     │
     ├──[SC-09] Stress Testing Engine:
     │   Load crisis data or generate synthetic crisis (SC-07)
     │   Apply crisis fill model (expanded slippage, partial fills)
     │   Apply circuit breaker simulation
     │   Run strategy signal logic through crisis period
     │
     ├──[SC-14] Risk Simulator:
     │   Confirm kill switch triggers at correct VIX/loss threshold
     │   Validate risk rules fire correctly
     │
     ├──[SC-15] Performance Evaluator:
     │   Stress-period metrics: MaxDD, time-to-recovery, capital at risk
     │
     ▼
 Aggregate all stress scenarios → worst-case analysis
     │
     ▼
 [SC-16] Validation: kill switch fired in all scenarios where it should have
     │
     ▼
 [SC-19] Governance: stress test used for risk calibration → Operations Lead review
     │
     ▼
 [SC-18] Stress test report → L9 RiskGuardian for kill switch calibration input
`

---

### SP-05 — Scenario Pipeline

`
SCENARIO PIPELINE
════════════════════════════════════════════════════

 [Trigger] Defined scenario test request (historical or hypothetical)
     │
     ▼
 [SC-03] Scenario Manager: load scenario definition
     │   Time period; market conditions; instruments; special rules
     │
     ▼
 [SC-05] Replay Engine configured for scenario
     │
     ▼
 [SC-06] or [SC-07] depending on historical vs synthetic:
     │   Historical scenario → SC-06 Historical Engine
     │   Synthetic scenario → SC-07 Synthetic Market Generator feeds SC-06
     │
     ▼
 [SC-10] Execution Simulator (scenario-specific fill model)
     │
     ▼
 [SC-12] Decision Simulator (if decision replay requested)
     │
     ▼
 [SC-15] Full metrics + scenario-specific metrics
     │
     ▼
 [SC-16] Validation
     │
     ▼
 [SC-17] Analytics: compare this scenario result to other scenario results
     │
     ▼
 [SC-18] Scenario report → L17 dashboard; operator delivery
`

---

### SP-06 — Execution Pipeline

`
EXECUTION PIPELINE (embedded in other pipelines)
════════════════════════════════════════════════════

 [Order Event] Strategy signal generates order
     │
     ▼
 [SC-10] Execution Simulator:
     │   Apply fill model (market / limit / stop)
     │   Apply slippage model
     │   Apply volume participation limit
     │   Apply circuit breaker (if active in scenario)
     │   Apply latency (if latency simulation active)
     │
     ▼
 [Fill Record] Fill price, size, slippage, latency, rejection (if any)
     │
     ▼
 [Portfolio State] Update position, cash, exposure
     │
     ▼
 [SC-15] Performance tracker: update equity curve, trade log
`

---

### SP-07 — Decision Pipeline

`
DECISION PIPELINE (AI Decision Simulation)
════════════════════════════════════════════════════

 [Trigger] Decision replay requested (audit or validation)
     │
     ▼
 [SC-12] Decision Simulator:
     │   Load historical decision record from L17 ControlTower logs
     │   Extract original inputs: signals, regime, risk budget, capital
     │
     ▼
 [L10] DebateAndDecision system:
     │   Feed inputs through current decision logic
     │   All 5 debate agents evaluate inputs
     │   Final decision recommendation generated
     │
     ▼
 [SC-12] Compare replayed decision to original:
     │   Determinism check: same inputs → same output?
     │   Regression check: if system was modified, is delta acceptable?
     │
     ▼
 [SC-15] Decision quality metrics: agreement rate, confidence distribution
     │
     ▼
 [SC-18] Decision replay report → L17 dashboard; operator delivery
`

---

### SP-08 — Portfolio Pipeline

`
PORTFOLIO PIPELINE (Multi-Strategy Simulation)
════════════════════════════════════════════════════

 [Trigger] Portfolio composition change OR periodic portfolio validation
     │
     ▼
 [SC-11] Portfolio Simulator:
     │   Load all strategy definitions in portfolio simulation
     │   Assign allocation configuration
     │
     ▼
 [SC-05] Replay Engine: shared market data for all strategies
     │
     ▼
 For each bar: all strategies generate signals simultaneously
     │   SC-10 executes all orders with position-size-aware slippage
     │   Portfolio state updated after all fills
     │
     ▼
 [SC-11] Portfolio-level metrics computed:
     │   Portfolio Sharpe, MaxDD, correlation matrix, marginal contribution
     │
     ▼
 [SC-15] SimQS for portfolio simulation result
     │
     ▼
 [SC-18] Portfolio simulation report → L6 CapitalRiskEngine, L7 RiskControl
`

---

### SP-09 — Learning Pipeline

`
LEARNING PIPELINE (Learning System Validation)
════════════════════════════════════════════════════

 [Trigger] L13 LearningSystem proposes model update; validation required
     │
     ▼
 [SC-13] Learning Simulator:
     │   Load historical period for replay
     │   Load original model state at start of period
     │
     ▼
 [SC-05] Replay Engine: historical session-by-session replay
     │
     ▼
 For each session: apply current model; record decisions; apply learning update
     │   Compare to original model decisions at same point in history
     │
     ▼
 [SC-13] Analyze: did learning updates improve subsequent decisions?
     │   Was attribution correct? Was learning stable?
     │
     ▼
 [SC-15] Learning quality metrics: attribution accuracy, model stability
     │
     ▼
 [SC-18] Learning validation report → L13 LearningSystem
`

---

### SP-10 — Reporting Pipeline

`
REPORTING PIPELINE
════════════════════════════════════════════════════

 [Trigger] Simulation completion OR end-of-session OR scheduled (daily/weekly/monthly)
     │
     ▼
 [SC-17] Analytics Engine: gather cross-simulation context
     │
     ▼
 [SC-18] Reporting Engine:
     │   Compile simulation results, validation certificates, analytics
     │   Generate report (type: post-sim, daily, weekly, monthly)
     │   Format for delivery target (Telegram: summary; L17: full)
     │
     ▼
 [SC-20] Record report in audit trail
     │
     ▼
 [Delivery] L17 ControlTower dashboard updated; Telegram notification sent
`

---

### SP-11 — Archive Pipeline

`
ARCHIVE PIPELINE
════════════════════════════════════════════════════

 [Trigger] Simulation result approved; archive requested
     │
     ▼
 [SC-03] Scenario Manager: confirm all artifacts present
     │
     ▼
 [SC-15] Performance Evaluator: confirm metrics report complete
     │
     ▼
 [SC-20] Audit Manager: verify hash chain integrity
     │   Create terminal audit record; close chain
     │
     ▼
 [SC-03] Compress and archive all artifacts
     │   Artifact types: scenario definition, trade log, equity curve,
     │   metrics report, validation certificate, Monte Carlo distributions,
     │   SimQS, governance record, audit chain
     │
     ▼
 [SC-01] Status updated to ARCHIVED
     │
     ▼
 [SC-18] Archive completion notification → operator
`

---

## PART VII — SIMULATION QUALITY FRAMEWORK

### 7.1 — Framework Purpose

The Simulation Quality Framework defines a systematic method for measuring the
trustworthiness of simulation results. A simulation result is only as valuable
as it is reliable. The Simulation Quality Score (SimQS) captures whether a result
is valid, statistically significant, and trustworthy enough to serve as evidence
for strategy promotion or risk calibration decisions.

SimQS is computed by SC-15 Performance Evaluator for every accepted simulation result.

---

### 7.2 — Quality Dimensions

**SimQS Formula:** SimQS = sum of (weight_i x score_i) for all 13 quality dimensions.
All weights sum to 1.00. All dimension scores are in the range 0.0 to 1.0.

---

**SQD-01 — Accuracy (Weight: 0.20)**

Definition: The degree to which the simulation faithfully represents what would
have happened in the real market if the strategy had been running.

Scoring criteria:
1.00: All fills use correct transaction costs and slippage; look-ahead bias
confirmed absent; fill timing is bar-open (correct); no data quality issues.
0.75: Minor data gaps (< 2% of bars) patched with forward-fill; costs correct.
0.50: Some data quality issues; transaction costs applied but slippage estimated.
0.25: Significant data quality issues; costs or timing questionable.
0.00: Known look-ahead bias; costs not applied; fundamental accuracy failure.

Why 0.20 weight: Accuracy is the most fundamental quality dimension. A simulation
that does not accurately represent market behavior cannot be trusted regardless
of how well-designed the strategy appears.

---

**SQD-02 — Statistical Validity (Weight: 0.18)**

Definition: The degree to which the performance metrics are statistically meaningful.

Scoring criteria:
1.00: Trade count >= 100; p-value < 0.01; Monte Carlo P10 Sharpe >= 0.5.
0.75: Trade count 50–99; p-value < 0.05; Monte Carlo P10 Sharpe >= 0.3.
0.50: Trade count 30–49; p-value < 0.10; statistics marginal.
0.25: Trade count 20–29; p-value >= 0.10; statistics unreliable.
0.00: Trade count < 20; statistics not computable.

Why 0.18 weight: Statistical significance is the second most critical quality
dimension. A result with few trades and high p-value cannot support promotion decisions.

---

**SQD-03 — Repeatability (Weight: 0.12)**

Definition: The degree to which the simulation produces the same result when
run again with identical inputs.

Scoring criteria:
1.00: Two independent runs produce byte-identical results.
0.75: Two runs produce numerically equivalent results (< 0.001% difference in metrics).
0.50: Two runs produce similar results (< 1% difference in Sharpe Ratio).
0.25: Two runs produce materially different results (> 1% difference in Sharpe).
0.00: Results are non-deterministic; different results on every run.

Why 0.12 weight: Non-repeatable simulations cannot be trusted. If the result
changes on re-run, it cannot serve as reliable evidence for any decision.

---

**SQD-04 — Reproducibility (Weight: 0.10)**

Definition: The degree to which the simulation result can be reproduced by an
independent evaluator using only the documented scenario definition and publicly
available data.

Scoring criteria:
1.00: Full scenario definition stored; all data sources documented; seed recorded;
  result reproducible by anyone with access to the same data.
0.75: Scenario definition complete; minor undocumented configuration items.
0.50: Partial documentation; some configuration not recorded.
0.25: Significant documentation gaps; result not independently reproducible.
0.00: Scenario definition not stored; result irreproducible.

---

**SQD-05 — Coverage (Weight: 0.10)**

Definition: The breadth of market conditions covered by the simulation.

Scoring criteria:
1.00: Simulation covers >= 5 distinct regime types; >= 3 years of data;
  both trending and mean-reverting market periods covered.
0.75: Covers 3–4 regime types; 2–3 years of data.
0.50: Covers 2 regime types; 1–2 years of data.
0.25: Covers only 1 regime type; < 1 year of data.
0.00: Simulation covers only a single market condition (e.g., strong bull market only).

---

**SQD-06 — Realism (Weight: 0.10)**

Definition: The degree to which the simulation's market model reflects real
market conditions, including transaction costs, liquidity constraints, and
execution limitations.

Scoring criteria:
1.00: Full transaction cost model applied (brokerage + STT + fees + slippage);
  volume participation limits applied; circuit breaker handling modeled.
0.75: Standard transaction costs; slippage applied; no volume participation limit.
0.50: Fixed cost model; no dynamic slippage.
0.25: Partial costs applied.
0.00: Zero-cost simulation; no slippage; not realistic.

---

**SQD-07 — Robustness (Weight: 0.08)**

Definition: The degree to which the simulation result is stable across variations
in parameters, data, and random perturbations.

Scoring criteria:
1.00: Monte Carlo P10 Sharpe >= P50 Sharpe x 0.75; WFE >= 0.70.
0.75: Monte Carlo P10 Sharpe >= P50 Sharpe x 0.60; WFE 0.50–0.70.
0.50: Monte Carlo P10 Sharpe >= P50 Sharpe x 0.40; WFE 0.40–0.50.
0.25: Monte Carlo P10 Sharpe < P50 Sharpe x 0.40; WFE < 0.40.
0.00: P10 Sharpe negative; WFE < 0.25; extreme performance variance.

---

**SQD-08 — Determinism (Weight: 0.06)**

Definition: The degree to which the simulation's outputs are fully determined by
its inputs with no uncontrolled randomness or external state.

Scoring criteria:
1.00: All random components use fixed seeds; no external state dependencies.
0.75: Fixed seeds used but minor external state (e.g., current date used for default period).
0.50: Some random components without fixed seeds; partial determinism.
0.25: Most random components unseded; results vary between runs.
0.00: Fully non-deterministic; cannot reproduce any specific result.

---

**SQD-09 — Performance (Weight: 0.06)**

Definition: The efficiency and speed of the simulation execution.

Scoring criteria:
1.00: Execution time within 80% of SLA.
0.75: Execution time within SLA.
0.50: Execution time 1–2x SLA.
0.25: Execution time 2–4x SLA.
0.00: Execution time > 4x SLA or timed out.

---

**SQD-10 — Scalability (Weight: 0.04)**

Definition: The degree to which the simulation can scale to larger data sets,
more instruments, and higher iteration counts without degrading.

Scoring criteria:
1.00: Successfully ran at 10x standard data volume without degradation.
0.75: Runs at 5x standard volume.
0.50: Runs at standard volume only.
0.25: Shows memory or compute issues at standard volume.
0.00: Cannot complete at standard volume.

---

**SQD-11 — Maintainability (Weight: 0.03)**

Definition: The degree to which the simulation scenario is documented and
maintainable over time.

Scoring criteria:
1.00: Full scenario documentation; hypothesis referenced; all parameters documented;
  version controlled; owner assigned.
0.75: Scenario documented; minor metadata gaps.
0.50: Partial documentation; owner not assigned.
0.25: Minimal documentation.
0.00: No documentation; effectively unmanageable.

---

**SQD-12 — Auditability (Weight: 0.02)**

Definition: The degree to which the simulation's execution history is traceable
and auditable.

Scoring criteria:
1.00: Complete hash-chained audit trail; all events recorded; chain verified.
0.75: Audit trail present; chain not verified.
0.50: Partial audit trail.
0.25: Minimal audit records.
0.00: No audit trail.

---

**SQD-13 — Operational Reliability (Weight: 0.01)**

Definition: The degree to which the simulation ran without operational errors or
exceptions.

Scoring criteria:
1.00: Clean execution; no errors, warnings, or exceptions.
0.75: Minor warnings; no impact on results.
0.50: Some warnings; possible minor result impact.
0.25: Multiple warnings; possible material result impact.
0.00: Errors during execution; result integrity uncertain.

---

### 7.3 — SimQS Tier Table

| Tier         | SimQS Range  | Meaning                          | Action                                |
|--------------|--------------|----------------------------------|---------------------------------------|
| EXCELLENT    | 0.85 – 1.00  | Exceptional result quality       | Full confidence for promotion use     |
| GOOD         | 0.70 – 0.84  | Strong result quality            | Suitable for promotion evidence       |
| ACCEPTABLE   | 0.55 – 0.69  | Adequate quality                 | Usable with awareness of limitations  |
| MARGINAL     | 0.35 – 0.54  | Below acceptable                 | Not suitable for promotion; re-run    |
| FAILED       | 0.00 – 0.34  | Quality failure                  | Reject; investigate; do not use       |

---

### 7.4 — SimQS Response Protocol

EXCELLENT / GOOD: Result is accepted. Auto-approved for standard use. Delivered
to consuming systems.

ACCEPTABLE: Result is accepted with notation. Usable for strategy promotion
only if at least one GOOD or EXCELLENT result for the same strategy exists.
Governance flag: alert operator.

MARGINAL: Result is not accepted for promotion evidence. Governance review required.
Root cause of low quality identified and addressed before re-run.

FAILED: Result quarantined. Cannot be used for any production decision. Root cause
investigation required. Operator notification sent immediately.

---

## PART VIII — SIMULATION GOVERNANCE

### 8.1 — Governance Framework Overview

Simulation governance ensures that simulation results that inform production
decisions (strategy promotion, risk calibration, kill switch thresholds) are
produced correctly, documented completely, and reviewed appropriately. Governance
does not slow down simulation — it creates the accountability framework that
allows simulation results to be trusted.

---

### 8.2 — Ownership Model

**System Owner:** Overall accountability for the Simulation Engine architecture
and constitutional rules. Approves methodology changes.

**Operations Lead:** Day-to-day operational accountability. Reviews stress test
results used for risk calibration. Reviews anomalous simulation outcomes. Reviews
governance reports.

**Component Owner:** Assigned for each of the 21 components. Responsible for
component health, maintenance, and improvement. May be the same person as
Operations Lead for smaller teams.

**Scenario Owner:** The person or process that created a scenario definition.
Responsible for keeping the scenario current, documented, and relevant.

---

### 8.3 — Naming Standards

**Simulation Run ID (SRI) Format:**
SIM-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}

Type codes: HIS (historical), PT (paper trading), MKT (market replay),
TICK (tick replay), BAR (bar replay), SCN (scenario), MC (Monte Carlo),
BS (bootstrap), STR (stress), CRASH (crash), LIQ (liquidity), SLP (slippage),
LAT (latency), EXEC (execution), PRT (portfolio), MA (multi-asset), CM (cross-market),
DEC (decision), LRN (learning), SYN (synthetic), HYB (hybrid).

Example: SIM-MC-20251112-00000047 = 47th Monte Carlo run on 2025-11-12.

**Scenario ID Format:**
SCN-{TYPE_CODE}-{NAME_SLUG}-{YYYYMMDD}-{SEQ:04d}

Example: SCN-STR-COVID2020-20251001-0001 = first version of COVID 2020 stress scenario.

**Report ID Format:**
RPT-SIM-{YYYYMMDD}-{TYPE}-{SEQ:04d}

---

### 8.4 — Scenario Versioning Policy

All scenario definitions are version-controlled following MAJOR.MINOR.PATCH:

MAJOR: Fundamental change — new asset universe, new time period, new simulation type.
MINOR: Parameter adjustment — stress factor, Monte Carlo iterations, cost model update.
PATCH: Documentation or metadata correction.

All versions are preserved. When a scenario is updated, the prior version remains
DEPRECATED (available for rollback) for 90 days; thereafter ARCHIVED.

---

### 8.5 — Approval Workflow

**Standard Backtest (SimQS >= 0.55):** Automated approval. No human review required.

**Standard Backtest (SimQS < 0.55):** Automated flag. Operations Lead review required.
Result not usable for promotion until reviewed.

**Monte Carlo (SimQS >= 0.55):** Automated approval.

**Stress Test (Used for Risk Calibration):** Always requires Operations Lead review.
No stress test result is used for kill switch threshold calibration without
human authorization.

**Methodology Change (transaction cost model, slippage model):** Requires System
Owner approval before first use.

**Non-Standard Scenario (synthetic data for hypothetical extreme):** Requires
Operations Lead approval of the scenario definition before execution.

---

### 8.6 — Review Cycle

**Daily:** SC-18 generates daily simulation summary. Operations Lead reviews.
Outstanding governance items identified.

**Weekly:** Full simulation coverage review. Which strategies have been simulated
in the past week? What are the SimQS trends? Any simulation-to-live gaps
widening?

**Monthly:** Stress scenario library review. Are all historical crisis scenarios
current and applicable? Are hypothetical scenarios calibrated to current market
conditions? Are cost and slippage models accurate?

**Quarterly:** Full methodology review. Is the WFE threshold (0.50) appropriate?
Is the minimum trade count (20) appropriate? Are SimQS dimension weights still
calibrated correctly?

---

### 8.7 — Compliance Framework

**Look-Ahead Bias Compliance:** Every historical simulation result is certified
look-ahead-free by SC-16 Validation (V-02 check). No simulation result without
this certification can be used for strategy promotion.

**Transaction Cost Compliance:** All simulations used for strategy promotion must
apply the standard IIOS transaction cost model. Zero-cost simulations may only
be used for internal research with explicit notation.

**Data Provenance Compliance:** The source of all market data used in a simulation
must be documented. Simulations using undocumented data sources cannot be used
for promotion decisions.

**Audit Trail Compliance:** Every simulation run has a hash-chained audit record.
Any simulation without an audit trail is treated as unverified and cannot be used
for production decisions.

**Reproducibility Compliance:** Every simulation used for a production decision
must be reproducible. Scenario definition, configuration, and data sources must
be documented completely.

---

### 8.8 — Security

**Read-Only Data Access:** The Simulation Engine has read-only access to all
production data stores. No simulation run can write to production databases or
modify production state.

**Order Routing Isolation:** Paper trading orders route to the paper ledger only.
The system enforces this at the OrderManager level; no paper trading order can
reach the Dhan broker integration.

**Artifact Integrity:** All simulation artifacts are protected by checksums.
Any artifact modification is detected on retrieval and flagged as a potential
integrity violation.

**Access Control:** Scenario creation and methodology changes require authenticated
operator authorization. Automated systems cannot create scenarios of type MAJOR
without human authorization.

---

### 8.9 — Retention Policy

All simulation artifacts are retained permanently. There is no deletion policy
for validated simulation results. The rationale: simulation results are the
evidence base for production decisions; destroying them removes the accountability
record. Storage is cheap; accountability is not.

Quarantined results (validation failures) are retained for 180 days; then archived
with a notation that they are quarantined. They are never promoted to the main
artifact store.

---

## PART IX — SIMULATION CONSTITUTION

### 9.1 — Constitutional Framework Overview

The Simulation Constitution establishes the inviolable rules of the IIOS Simulation
Engine. Constitutional rules are categorized as HARD (absolute; cannot be overridden
by any automated process) or SOFT (default behavior; can be modified with explicit
human authorization and governance documentation).

---

### CATEGORY A — SIMULATION IDENTITY RULES (SC-A)

**SC-A-001 [HARD]:** Every simulation run must have a unique Simulation Run ID
(SRI) assigned by SC-01 Registry before execution begins.

**SC-A-002 [HARD]:** Every simulation run must be associated with a validated
scenario definition. No simulation may run without an approved scenario.

**SC-A-003 [HARD]:** The simulation type (SIM-01 through SIM-21) must be
explicitly declared in every scenario definition. No simulation runs with an
unknown or undeclared type.

**SC-A-004 [HARD]:** Every simulation run must record the version of the
scenario definition used. Scenario updates during a run are prohibited.

**SC-A-005 [HARD]:** Every simulation run must record the software version of
the Simulation Engine at execution time.

**SC-A-006 [SOFT]:** Simulation runs should be assigned to a named owner.
Orphan simulations (no named owner) are flagged for review after 7 days.

**SC-A-007 [HARD]:** No simulation run may share an SRI with any other run.
SRI uniqueness is enforced at the registry level; duplicate SRIs are rejected.

---

### CATEGORY B — SCENARIO INTEGRITY RULES (SC-B)

**SC-B-001 [HARD]:** Every scenario definition must pass SC-16 Simulation Validator
pre-run checks before the simulation is allowed to start.

**SC-B-002 [HARD]:** Scenario definitions must not be modified during an active
simulation run. Any change to the scenario during execution constitutes a
constitutional violation; the run is aborted and quarantined.

**SC-B-003 [HARD]:** Every scenario definition must specify its asset universe,
time period, simulation type, bar granularity, and cost model. Incomplete
scenarios are rejected at submission.

**SC-B-004 [HARD]:** Scenarios used for strategy promotion must use the standard
IIOS transaction cost model. Custom cost models are not permitted for promotion
evidence.

**SC-B-005 [SOFT]:** Scenarios should include a reference to the hypothesis being
tested. Scenarios without a hypothesis reference are flagged but not rejected.

**SC-B-006 [HARD]:** Scenario definitions are immutable once a simulation run
has been completed against them. Changes to a used scenario require a version increment.

**SC-B-007 [HARD]:** Synthetic scenarios (scenarios using SC-07 generated data)
must record all generation parameters including the random seed. Unreproducible
synthetic scenarios cannot be used for promotion evidence.

---

### CATEGORY C — REPLAY ACCURACY RULES (SC-C)

**SC-C-001 [HARD]:** All historical simulation runs must enforce strict chronological
order. Data from bar N+1 must never be accessible to the signal logic at bar N.

**SC-C-002 [HARD]:** Look-ahead bias check (V-02) must pass before any simulation
result is accepted. Results with known look-ahead bias are permanently quarantined.

**SC-C-003 [HARD]:** All simulated fills must apply the standard transaction cost
model. Zero-cost fills are prohibited for any simulation used in production decisions.

**SC-C-004 [HARD]:** Slippage must be applied to every simulated fill. Zero-slippage
fills are not permitted for strategy promotion simulations.

**SC-C-005 [HARD]:** Volume participation limits must be applied to all equity
simulations. Orders cannot fill more than the configured percentage of the bar's volume.

**SC-C-006 [SOFT]:** Bar granularity should match the strategy's intended trading
timeframe. Mismatched granularity (e.g., daily bars for an intraday strategy) must
be explicitly justified in the scenario definition.

**SC-C-007 [HARD]:** For all paper trading simulations, orders must route to the
paper ledger only. No mechanism exists for paper trading orders to reach the Dhan
live broker.

**SC-C-008 [HARD]:** Historical data used in simulations must be from an approved
IIOS data source (yfinance, Dhan archive). Data from unapproved sources cannot be
used in promotion evidence simulations.

---

### CATEGORY D — HISTORICAL PRESERVATION RULES (SC-D)

**SC-D-001 [HARD]:** All simulation artifacts from completed and approved simulation
runs are retained permanently. No deletion of approved simulation results.

**SC-D-002 [HARD]:** Simulation artifacts must be archived with hash verification.
Any artifact failing hash check is treated as corrupted and must be re-run.

**SC-D-003 [HARD]:** The complete trade log (every simulated trade with entry,
exit, fill price, size, costs, and slippage) must be retained for every archived
simulation run.

**SC-D-004 [HARD]:** The equity curve (portfolio NAV at every bar) must be
retained for every archived historical or portfolio simulation.

**SC-D-005 [SOFT]:** Run-level metadata (operator, purpose, strategy context) should
be documented for every simulation run. Undocumented runs are flagged monthly.

**SC-D-006 [HARD]:** Simulation results used as evidence for any production decision
(strategy promotion, risk calibration) must be immutably archived before the decision
is recorded. Post-decision modification of simulation evidence is prohibited.

---

### CATEGORY E — SYNTHETIC DATA RULES (SC-E)

**SC-E-001 [HARD]:** All synthetic data generation must record: generation model,
model parameters, random seed, calibration targets, and validation results.
Undocumented synthetic data cannot be used for promotion evidence.

**SC-E-002 [HARD]:** Synthetic data must pass statistical validation (SC-07
generates a validation report confirming the generated series meets stated targets)
before use in simulation.

**SC-E-003 [SOFT]:** Synthetic data simulations should be clearly labeled in all
reports. Results from synthetic data simulations should not be presented alongside
historical simulation results without explicit labeling.

**SC-E-004 [HARD]:** Synthetic data models must not be calibrated on the
out-of-sample period. Calibration uses only the in-sample period.

**SC-E-005 [SOFT]:** At least one scenario in every comprehensive strategy
validation should use real historical data, not synthetic data only.

---

### CATEGORY F — VALIDATION RULES (SC-F)

**SC-F-001 [HARD]:** A simulation result without a validation certificate from
SC-16 Simulation Validator cannot be used for any production decision.

**SC-F-002 [HARD]:** All 8 validation checks (V-01 through V-08) must be applied
to every simulation result. No selective validation is permitted.

**SC-F-003 [HARD]:** A simulation result with a FAILED validation check is
quarantined immediately. Quarantined results cannot be used for production
decisions under any circumstances.

**SC-F-004 [HARD]:** The minimum trade count for statistical metrics is 20 trades.
Simulations with fewer than 20 closed trades do not produce statistical performance
metrics; only descriptive metrics are provided.

**SC-F-005 [HARD]:** Walk-Forward Efficiency Ratio (WFE) must be computed for
every historical simulation with >= 4 walk-forward windows. Simulations with
insufficient data for WFE computation are flagged as having limited validation.

**SC-F-006 [SOFT]:** SimQS below ACCEPTABLE (0.55) should trigger a mandatory
review before the result is delivered to any consuming system.

**SC-F-007 [HARD]:** Results from simulations that experienced unhandled exceptions
during execution are quarantined. Results from simulations that completed with
handled exceptions are flagged and their SimQS is reduced by 0.10.

---

### CATEGORY G — EXECUTION ISOLATION RULES (SC-G)

**SC-G-001 [HARD]:** The Simulation Engine NEVER places live orders. No execution
pathway connects the Simulation Engine to the Dhan broker integration.

**SC-G-002 [HARD]:** The Simulation Engine NEVER writes to production data stores.
All simulation outputs are written to simulation-specific result stores.

**SC-G-003 [HARD]:** The Simulation Engine NEVER modifies production configuration.
No simulation run can change strategy parameters, risk thresholds, or portfolio
allocation rules in the live system.

**SC-G-004 [HARD]:** The paper trading paper ledger is strictly isolated from the
production trade ledger. No mechanism exists for paper trades to appear as real
trades or to affect real portfolio accounting.

**SC-G-005 [HARD]:** All data access from the Simulation Engine is read-only. No
simulation component has write access to any production database.

**SC-G-006 [HARD]:** The Simulation Engine's execution environment is isolated.
Code running in a simulation context cannot invoke production execution pathways.

---

### CATEGORY H — LEARNING RULES (SC-H)

**SC-H-001 [HARD]:** Learning simulation results must not be applied directly
to modify production learning models. Results are delivered as recommendations;
human authorization is required before any production model is updated based
on simulation evidence.

**SC-H-002 [SOFT]:** Learning simulation should be run before any material update
to the L13 LearningSystem is deployed. Simulations confirming the improvement
constitute the deployment evidence.

**SC-H-003 [HARD]:** Attribution analysis from learning simulation must cover
a minimum of 30 sessions and 30 closed trades to be considered statistically
meaningful.

**SC-H-004 [SOFT]:** Learning replay simulations should compare the proposed
model against the current production model on the same historical period to
ensure the new model is directionally better.

---

### CATEGORY I — GOVERNANCE RULES (SC-I)

**SC-I-001 [HARD]:** Every simulation run must create a governance record in
SC-19 Governance Manager. Simulations without governance records are treated
as unverified and cannot be used for production decisions.

**SC-I-002 [HARD]:** Stress test results used for risk calibration must receive
explicit Operations Lead authorization before being applied. Automated stress
test application to risk thresholds is prohibited.

**SC-I-003 [HARD]:** Methodology changes (transaction cost model, slippage model,
WFE threshold) require System Owner authorization. No methodology change takes
effect without System Owner sign-off.

**SC-I-004 [SOFT]:** The Simulation Engine governance report must be reviewed
by the Operations Lead within 24 hours of generation.

**SC-I-005 [HARD]:** All human overrides of automated simulation governance
decisions must be recorded in SC-19 with operator identity, reason, and timestamp.

---

### CATEGORY J — MONITORING RULES (SC-J)

**SC-J-001 [HARD]:** The Simulation Engine must not accept new simulation runs
when SEHS is below CRITICAL (0.30). New submissions are queued until SEHS
recovers to at least DEGRADED (0.55).

**SC-J-002 [SOFT]:** Long-running simulations (> 2x expected duration) should
trigger a WARNING alert to the operator. The operator should investigate or
extend the timeout.

**SC-J-003 [HARD]:** Memory exhaustion during a simulation run must trigger an
orderly shutdown of that run with state checkpointing. Runs cannot be abandoned
without checkpointing.

**SC-J-004 [HARD]:** The Simulation Engine must maintain SC-21 health monitoring
continuously during market hours. Health monitoring cannot be stopped while
simulations are running.

**SC-J-005 [SOFT]:** All active simulations should have estimated completion times
updated every 60 seconds. Stale completion estimates are flagged.

---

### CATEGORY K — AUDITABILITY RULES (SC-K)

**SC-K-001 [HARD]:** Every governance event in the Simulation Engine must be
recorded in SC-20 Audit Manager within 10 seconds of occurrence.

**SC-K-002 [HARD]:** The hash chain maintained by SC-20 must never be broken.
If a break is detected, the Simulation Engine halts governance operations and
alerts the operator immediately.

**SC-K-003 [HARD]:** Audit records are immutable once created. No audit record
may be modified or deleted.

**SC-K-004 [HARD]:** Hash chain integrity must be verified on every simulation
engine startup and every 60 minutes during operation.

**SC-K-005 [SOFT]:** The audit trail for every simulation run should include:
scenario definition hash, execution start time, execution end time, metric hashes,
validation certificate, governance record reference.

---

### CATEGORY L — SECURITY RULES (SC-L)

**SC-L-001 [HARD]:** No external system can trigger a simulation run without
going through the documented SS-01 through SS-14 service interfaces with proper
authentication.

**SC-L-002 [HARD]:** Simulation artifacts must not contain credentials, API keys,
or any sensitive configuration. Artifact contents are inspected before archiving.

**SC-L-003 [HARD]:** Access to the Simulation Engine scenario library is
restricted to authorized personnel and authorized systems.

**SC-L-004 [SOFT]:** Simulation system logs should not contain sensitive market
data (individual trade prices and sizes from live portfolio). Logs contain only
aggregate statistics.

---

### CATEGORY M — COMPLIANCE RULES (SC-M)

**SC-M-001 [HARD]:** No simulation may use data that is known to be unreliable
or sourced from undocumented providers for any simulation result used in a
production decision.

**SC-M-002 [HARD]:** All simulations used as evidence for regulatory reporting
must use standard cost models and must be produced with a reproducibility
certification.

**SC-M-003 [SOFT]:** A model risk documentation file should be maintained for
all statistical and machine learning models used in simulation.

---

### CATEGORY N — HUMAN OVERRIDE RULES (SC-N)

**SC-N-001 [HARD]:** All human overrides of simulation governance recommendations
must be recorded with: operator identity, timestamp, override reason, outcome.

**SC-N-002 [HARD]:** A human operator may stop a running simulation at any time.
All stop actions are recorded. The partial result is not used for any production
decision without explicit human authorization and documentation.

**SC-N-003 [SOFT]:** Human overrides of automated SimQS rejections should
be reviewed in the monthly governance report. A pattern of overriding low-quality
simulation results is a governance concern.

**SC-N-004 [HARD]:** Human operators may approve non-standard scenarios (synthetic
data, unusual time periods). Such approvals must be documented with the operator's
rationale and signed off in the governance record.

---

### CATEGORY O — CONSTITUTIONAL COMPLETENESS RULES (SC-O)

**SC-O-001 [HARD]:** These constitutional rules define the minimum governance
standard for the IIOS Simulation Engine. No simulation type or operating mode is
exempt from the applicable rules.

**SC-O-002 [HARD]:** Any change to these constitutional rules requires System
Owner authorization and must be documented as a Governing Design Record (GDR).
No informal rule exceptions exist.

**SC-O-003 [SOFT]:** The Simulation Engine constitutional rules should be reviewed
annually to ensure they remain current, appropriate, and effective.

**SC-O-004 [HARD]:** In the event of a conflict between two constitutional rules,
the more restrictive interpretation applies until System Owner clarification is
provided.

---

### 9.2 — Rule Count Summary

| Category | Name                     | HARD | SOFT | Total |
|----------|--------------------------|------|------|-------|
| SC-A     | Simulation Identity      |  6   |  1   |   7   |
| SC-B     | Scenario Integrity       |  6   |  1   |   7   |
| SC-C     | Replay Accuracy          |  6   |  2   |   8   |
| SC-D     | Historical Preservation  |  5   |  1   |   6   |
| SC-E     | Synthetic Data           |  3   |  2   |   5   |
| SC-F     | Validation               |  6   |  1   |   7   |
| SC-G     | Execution Isolation      |  6   |  0   |   6   |
| SC-H     | Learning                 |  2   |  2   |   4   |
| SC-I     | Governance               |  4   |  1   |   5   |
| SC-J     | Monitoring               |  3   |  2   |   5   |
| SC-K     | Auditability             |  4   |  1   |   5   |
| SC-L     | Security                 |  3   |  1   |   4   |
| SC-M     | Compliance               |  2   |  1   |   3   |
| SC-N     | Human Override           |  3   |  1   |   4   |
| SC-O     | Constitutional Completeness | 3 |  1   |   4   |
| **Total**|                          | **62** | **18** | **80** |

---

## PART X — SIMULATION READINESS CHECKLIST

### 10.1 — Readiness Framework Overview

The Simulation Readiness Checklist is the formal gate that a new strategy must pass
before advancing from simulation to live deployment, and that a new scenario
configuration must pass before being used for production decisions. The checklist
provides a systematic, auditable confirmation that all required simulation work
has been completed to acceptable quality.

---

### 10.2 — Readiness Phases and Checklist Items

---

**Phase 1 — Historical Data Ready**

1.1 Minimum 2 years of daily OHLCV data available for all strategy instruments.
1.2 Data quality validated: no gaps > 5 consecutive sessions.
1.3 Data source documented (yfinance, Dhan archive, or approved alternative).
1.4 Benchmark data (NIFTY50) available for the full simulation period.
1.5 Any instrument adjustments (splits, dividends) applied consistently.
1.6 Data loaded successfully in SC-06 Historical Engine test run.

Phase 1 Status: ALL 6 items must be CONFIRMED for Phase 1 PASS.

---

**Phase 2 — Scenario Validated**

2.1 Scenario definition complete: all required fields populated.
2.2 Scenario validated by SC-03 Scenario Manager (no internal consistency errors).
2.3 Hypothesis referenced in scenario definition.
2.4 Transaction cost model: standard IIOS model confirmed (SC-B-004).
2.5 Slippage model configured (not zero-slippage).
2.6 Bar granularity matches strategy's intended timeframe.
2.7 Scenario version controlled with documented change history.

Phase 2 Status: Items 2.1, 2.2, 2.4, 2.5 are HARD requirements; 2.3, 2.6, 2.7 SOFT.

---

**Phase 3 — Simulation Environment Ready**

3.1 SC-21 SEHS >= NOMINAL (0.75) confirmed.
3.2 All 21 components health check: no component below CRITICAL (0.30).
3.3 SC-01 Registry accessible; SRI assignment confirmed functional.
3.4 SC-03 Scenario Manager artifact store accessible and writable.
3.5 SC-16 Simulation Validator functional (test validation check confirmed).
3.6 SC-20 Audit Manager hash chain intact; last integrity check passed.
3.7 Compute resources available for expected simulation duration.

Phase 3 Status: ALL 7 items must be CONFIRMED for Phase 3 PASS.

---

**Phase 4 — Replay Successful**

4.1 At least one complete historical simulation (SIM-01) run to completion.
4.2 Walk-forward analysis completed (minimum 4 windows).
4.3 WFE >= 0.50 confirmed.
4.4 SC-16 validation certificate issued (all 8 checks PASS).
4.5 Trade count >= 20 (minimum for statistical metrics).
4.6 Equity curve generated and stored in SC-03.
4.7 Full trade log stored in SC-03.

Phase 4 Status: Items 4.1 through 4.6 are HARD requirements; 4.7 SOFT.

---

**Phase 5 — Monte Carlo Completed**

5.1 Monte Carlo simulation (SIM-07) completed with >= 500 iterations.
5.2 Trade permutation Monte Carlo: P10 Sharpe >= 0.50.
5.3 Price perturbation Monte Carlo completed.
5.4 Statistical significance: p-value < 0.05 against null hypothesis.
5.5 Monte Carlo results stored in SC-03.
5.6 Monte Carlo SimQS >= ACCEPTABLE (0.55).

Phase 5 Status: Items 5.1 through 5.4 are HARD requirements.

---

**Phase 6 — Stress Test Completed**

6.1 At least 3 historical stress scenarios applied (from IIOS Stress Library).
6.2 At least 1 hypothetical stress scenario (synthetic extreme) applied.
6.3 Kill switch behavior validated: L9 RiskGuardian triggers correctly in all
    scenarios where VIX > 45 or daily loss > 2%.
6.4 Maximum stress drawdown documented.
6.5 Stress test report reviewed by Operations Lead (for risk calibration use).
6.6 No scenario produces total capital loss > 50% in a single crash event.

Phase 6 Status: Items 6.1, 6.3, 6.6 are HARD requirements; others SOFT.

---

**Phase 7 — Performance Acceptable**

7.1 Out-of-sample Sharpe Ratio >= 0.80 (PG-02 equivalent for simulation evidence).
7.2 Maximum drawdown <= 15% in out-of-sample periods (PG-03 equivalent).
7.3 Win rate >= 50% across all walk-forward windows (PG-01 equivalent).
7.4 SimQS >= ACCEPTABLE (0.55).
7.5 Regime performance analysis: strategy performs adequately (positive Sharpe)
    in its stated target regime.
7.6 Performance is consistent across walk-forward windows (WFE >= 0.50).

Phase 7 Status: ALL 6 items are HARD requirements.

---

**Phase 8 — Risk Evaluation Complete**

8.1 SC-14 Risk Simulator: confirmed risk rules fire at correct thresholds.
8.2 Portfolio simulation completed (SIM-15): new strategy added to active portfolio;
    portfolio-level MaxDD does not exceed 15% with new strategy included.
8.3 Correlation with active strategies: average pairwise Sharpe correlation < 0.70.
8.4 Maximum single-strategy capital allocation (max_capital_pct) confirmed within limits.
8.5 Risk Engine (L7 RiskControl) approval received for this strategy.
8.6 Kill switch behavior confirmed (Phase 6 item 6.3 plus confirmation from L9).

Phase 8 Status: ALL 6 items are HARD requirements.

---

**Phase 9 — Learning Captured**

9.1 Learning simulation (SIM-19) completed: attribution analysis confirms
    the principal signals are correctly identified as profit contributors.
9.2 Learning stability confirmed: no oscillation in model updates.
9.3 Learning simulation results delivered to L13 LearningSystem.
9.4 L13 LearningSystem acknowledges receipt of simulation learning data.

Phase 9 Status: Items 9.1, 9.3, 9.4 are HARD requirements; 9.2 SOFT.

---

**Phase 10 — Governance Approved**

10.1 SC-19 Governance Manager: all required approvals obtained.
10.2 Simulation evidence dossier complete: SRI references for all required runs.
10.3 SC-20 Audit Manager: audit chain intact for all simulation runs.
10.4 Operations Lead has reviewed simulation summary and acknowledged.
10.5 No outstanding governance flags or unresolved compliance issues.
10.6 Strategy promotion dossier submitted to L15 ResearchLab.

Phase 10 Status: ALL 6 items are HARD requirements.

---

**Phase 11 — Documentation Complete**

11.1 Simulation evidence dossier fully documented with all SRI references.
11.2 Scenario definitions documented with full metadata and hypothesis reference.
11.3 Simulation results summary documented (performance metrics, SimQS, key findings).
11.4 Risk evaluation results documented.
11.5 Any anomalies or concerns from simulation documented with resolutions.
11.6 All documents stored in SC-03 artifact store.

Phase 11 Status: Items 11.1 through 11.4 are HARD requirements.

---

**Phase 12 — Archived Correctly**

12.1 All simulation artifacts compressed and archived in SC-03.
12.2 Hash chain closed for all relevant simulation runs (SC-20).
12.3 Archive index updated in SC-01 Registry.
12.4 Archive integrity verified: checksums confirmed for all artifacts.
12.5 Archive notification delivered to operator.
12.6 Simulation evidence dossier linked to strategy record in L5 StrategyLab.

Phase 12 Status: Items 12.1 through 12.4 are HARD requirements.

---

### 10.3 — Readiness State Machine

`
SIMULATION READINESS STATE MACHINE
═════════════════════════════════════════

Phase 1: Data Ready → PASS
    │
    ▼
Phase 2: Scenario Validated → PASS
    │
    ▼
Phase 3: Environment Ready → PASS
    │
    ▼
Phase 4: Replay Successful → PASS (WFE >= 0.50; SimQS >= 0.55)
    │
    ├──(FAIL)──► INVESTIGATION REQUIRED → return to Phase 1 or 2
    │
    ▼
Phase 5: Monte Carlo → PASS (P10 Sharpe >= 0.50; p-value < 0.05)
    │
    ├──(FAIL)──► STRATEGY REDESIGN or REJECT
    │
    ▼
Phase 6: Stress Test → PASS (kill switch confirmed; no catastrophic loss)
    │
    ├──(FAIL)──► RISK REDESIGN required
    │
    ▼
Phase 7: Performance Acceptable → PASS (all promotion gate equivalents met)
    │
    ├──(FAIL)──► STRATEGY NOT PROMOTABLE → retirement or redesign
    │
    ▼
Phase 8: Risk Evaluation Complete → PASS
    │
    ├──(FAIL)──► RISK ADJUSTMENT required
    │
    ▼
Phase 9: Learning Captured → PASS
    │
    ▼
Phase 10: Governance Approved → PASS
    │
    ├──(FAIL)──► GOVERNANCE RESOLUTION required
    │
    ▼
Phase 11: Documentation → PASS
    │
    ▼
Phase 12: Archive → PASS
    │
    ▼
SIMULATION READINESS CERTIFIED
    │
    ▼
Strategy advances to L15 ResearchLab for final promotion review
`

---

### 10.4 — Readiness Quick Reference Matrix

| Phase | Name                    | HARD Items | SOFT Items | Gate         |
|-------|-------------------------|------------|------------|--------------|
| 1     | Historical Data Ready   | 6          | 0          | All HARD     |
| 2     | Scenario Validated      | 4          | 3          | 4 HARD       |
| 3     | Environment Ready       | 7          | 0          | All HARD     |
| 4     | Replay Successful       | 6          | 1          | 6 HARD       |
| 5     | Monte Carlo Completed   | 4          | 2          | 4 HARD       |
| 6     | Stress Test             | 3          | 3          | 3 HARD       |
| 7     | Performance Acceptable  | 6          | 0          | All HARD     |
| 8     | Risk Evaluation         | 6          | 0          | All HARD     |
| 9     | Learning Captured       | 3          | 1          | 3 HARD       |
| 10    | Governance Approved     | 6          | 0          | All HARD     |
| 11    | Documentation           | 4          | 2          | 4 HARD       |
| 12    | Archived Correctly      | 4          | 2          | 4 HARD       |

Total HARD items: 59. All 59 HARD items must be CONFIRMED for full readiness certification.

---

## SUPPLEMENT A — SIMULATION TAXONOMY REFERENCE

### A.1 — Complete Simulation Type Profiles

| Code   | Name                       | Min Data     | Min Trades | Expected Duration | SimQS Min |
|--------|----------------------------|--------------|------------|-------------------|-----------|
| SIM-01 | Historical Simulation      | 2 years      | 20         | 30–300 sec        | 0.55      |
| SIM-02 | Paper Trading              | N/A (live)   | N/A        | 10+ sessions      | N/A       |
| SIM-03 | Market Replay              | 1 session    | N/A        | 1–60 min          | N/A       |
| SIM-04 | Tick Replay                | 1 session    | N/A        | 5–120 min         | N/A       |
| SIM-05 | Bar Replay                 | 1 session    | N/A        | 1–30 min          | N/A       |
| SIM-06 | Scenario Simulation        | Scenario-dep | 10+        | 5–60 min          | 0.50      |
| SIM-07 | Monte Carlo                | 2 years      | 20+        | 5–30 min          | 0.55      |
| SIM-08 | Bootstrap Simulation       | 2 years      | 50+        | 5–60 min          | 0.55      |
| SIM-09 | Stress Testing             | 1 scenario   | 5+         | 10–60 min         | 0.50      |
| SIM-10 | Crash Simulation           | 1 crisis     | 3+         | 5–30 min          | 0.50      |
| SIM-11 | Liquidity Simulation       | 1 year       | 10+        | 10–30 min         | 0.50      |
| SIM-12 | Slippage Simulation        | 1 year       | 20+        | 5–30 min          | 0.50      |
| SIM-13 | Latency Simulation         | 1 year       | 20+        | 5–30 min          | 0.50      |
| SIM-14 | Execution Simulation       | 1 year       | 20+        | 10–60 min         | 0.55      |
| SIM-15 | Portfolio Simulation       | 2 years      | 50+        | 10–60 min         | 0.55      |
| SIM-16 | Multi-Asset Simulation     | 2 years      | 50+        | 10–60 min         | 0.55      |
| SIM-17 | Cross-Market Simulation    | 2 years      | 30+        | 15–90 min         | 0.55      |
| SIM-18 | AI Decision Simulation     | 30 sessions  | N/A        | 10–60 min         | N/A       |
| SIM-19 | Learning Simulation        | 30 sessions  | 30+        | 10–60 min         | N/A       |
| SIM-20 | Synthetic Market           | N/A (gen.)   | 20+        | 5–120 min         | 0.50      |
| SIM-21 | Hybrid Simulation          | Type-dep     | Type-dep   | Type-dep          | Max(deps) |

### A.2 — Simulation Type to Component Mapping

| Simulation Type | Primary Component | Secondary Components            |
|-----------------|-------------------|---------------------------------|
| SIM-01          | SC-06             | SC-05, SC-10, SC-15, SC-16      |
| SIM-02          | SC-10             | SC-15, SC-21                    |
| SIM-03          | SC-05             | SC-12                           |
| SIM-04          | SC-05             | SC-10, SC-12                    |
| SIM-05          | SC-05, SC-06      | SC-10                           |
| SIM-06          | SC-06, SC-09      | SC-03, SC-07                    |
| SIM-07          | SC-08             | SC-06, SC-07, SC-15             |
| SIM-08          | SC-08             | SC-15                           |
| SIM-09          | SC-09             | SC-14, SC-07, SC-15             |
| SIM-10          | SC-09             | SC-10, SC-14                    |
| SIM-11          | SC-09             | SC-10                           |
| SIM-12          | SC-10             | SC-06                           |
| SIM-13          | SC-10             | SC-06                           |
| SIM-14          | SC-10             | SC-05, SC-06                    |
| SIM-15          | SC-11             | SC-05, SC-06, SC-10, SC-15      |
| SIM-16          | SC-11             | SC-05, SC-06, SC-10             |
| SIM-17          | SC-11             | SC-06, SC-07                    |
| SIM-18          | SC-12             | SC-05, L10                      |
| SIM-19          | SC-13             | SC-05, L13                      |
| SIM-20          | SC-07             | SC-06, SC-08                    |
| SIM-21          | All applicable    | All applicable                  |

---

## SUPPLEMENT B — SCENARIO CATALOG

### B.1 — Standard Scenario Library

The IIOS Simulation Engine maintains a curated Scenario Library — a set of
approved, pre-configured scenarios for common simulation needs. Using library
scenarios ensures consistency, reduces setup time, and allows cross-strategy
comparisons on identical scenarios.

---

**Category 1 — Standard Backtest Scenarios**

**SCN-HIS-LONGTERM-01:** Full historical backtest, NIFTY50 universe, 5 years.
Time period: 5 years prior to current date. Bar granularity: 1-day.
Transaction cost: standard IIOS model. Walk-forward: 4 windows.
Primary use: Standard strategy backtesting for promotion evidence.

**SCN-HIS-MIDTERM-01:** 3-year medium-term backtest, NIFTY50 universe.
Time period: 3 years prior to current date. Primary use: Intermediate validation.

**SCN-HIS-RECENT-01:** 1-year recent performance assessment.
Time period: 1 year prior to current date. Primary use: Recent regime performance check.

**SCN-HIS-MIDCAP-01:** 5-year backtest, NIFTY Midcap 100 universe.
Primary use: Mid-cap strategy validation.

---

**Category 2 — Stress Test Scenarios**

**SCN-STR-COVID2020-01:** March 2020 COVID crash.
Time period: 2020-02-20 to 2020-04-30. Fill model: crash mode (3x slippage).
Primary use: Crash resilience testing.

**SCN-STR-GFC2008-01:** 2008 Global Financial Crisis period.
Time period: 2008-09-01 to 2009-03-31. Primary use: Historic worst-case testing.

**SCN-STR-CHINA2015-01:** August 2015 China selloff.
Time period: 2015-08-01 to 2015-09-30. Primary use: External shock testing.

**SCN-STR-VOLT2022-01:** 2022 high-volatility period (rate shock regime).
Time period: 2022-01-01 to 2022-12-31. Primary use: Rate-change regime testing.

---

**Category 3 — Hypothetical Stress Scenarios**

**SCN-HYP-CRASH15PCT-01:** Hypothetical 15% single-session decline.
Generated by: SC-07 with jump parameter = 0.15 at session 50 of the scenario.
Primary use: Single-event crash resilience.

**SCN-HYP-CRASH25PCT-01:** Hypothetical 25% single-session decline.
Generated by: SC-07 with jump parameter = 0.25 at session 50.
Primary use: Extreme crash resilience; kill switch calibration.

**SCN-HYP-SIDEWAYS180D-01:** 180-day low-volatility sideways market.
Generated by: SC-07 Regime-Switching model in SIDEWAYS regime for 180 sessions.
Primary use: Mean reversion strategy validation; trend-following weakness identification.

**SCN-HYP-VIX80-01:** VIX spike to 80 environment.
Generated by: SC-07 Heston model with elevated volatility parameter for 30 sessions.
Primary use: Extreme volatility regime testing.

**SCN-HYP-RATE300BP-01:** 300 basis point overnight rate increase shock.
Generated by: SC-07 with structural mean return shift for fixed income correlated assets.
Primary use: Rate shock regime testing.

---

**Category 4 — Portfolio Scenarios**

**SCN-PRT-BALANCED-01:** 6-strategy balanced portfolio simulation.
Configuration: Equal weight; monthly rebalance; 5-year period.
Primary use: Standard portfolio composition validation.

**SCN-PRT-CONCENTRATED-01:** 3-strategy concentrated portfolio simulation.
Configuration: 33% equal weight; monthly rebalance.
Primary use: Concentration risk validation.

**SCN-PRT-CORRELATION-01:** Portfolio simulation specifically designed to
measure strategy return correlations under different market regimes.
Primary use: Diversification analysis.

---

**Category 5 — Decision and Learning Scenarios**

**SCN-DEC-REPLAY-30D-01:** 30-session decision replay scenario.
Time period: Most recent 30 completed sessions. Primary use: Routine decision
system stability check.

**SCN-LRN-REPLAY-60D-01:** 60-session learning system replay scenario.
Time period: Most recent 60 completed sessions. Primary use: Learning system
validation before model updates.

---

### B.2 — Scenario Addition Process

Adding a new scenario to the IIOS Scenario Library requires:
1. Draft scenario definition with all required fields populated.
2. SC-03 Scenario Manager validation (internal consistency check).
3. Test run to confirm the scenario executes without errors.
4. Operations Lead review and approval.
5. Version controlled with v1.0 initial version.
6. Added to SC-02 Simulation Catalog for discovery.

---

## SUPPLEMENT C — REPLAY MODELS

### C.1 — Bar Replay Model (Standard)

The standard IIOS replay model for daily strategy simulation.

**Signal Timing:**
- Signals are generated using close prices from session N (and all prior sessions).
- No data from session N+1 is accessible when generating session N's signal.
- Entry orders are executed at the open of session N+1 (next-open execution).

**Exit Timing:**
- Exit signals follow the same rule: exit signal on close of bar N; exit executed
  at open of bar N+1.
- Stop-loss orders are modeled as triggered during session N if the session's
  low (for long stops) or high (for short stops) touches the stop price.
- On stop trigger: fill price = max(stop price, open price next bar) — this
  models the possibility that a stop is touched overnight and opens at a gap.

**Hold Period:**
- Strategies with maximum hold period N sessions: position is closed at open of
  session (entry + N + 1) regardless of current P&L.

---

### C.2 — Intraday Bar Replay Model

Used for strategies operating on 5-minute, 15-minute, or 30-minute bars within
the NSE trading session (09:15 to 15:30 IST).

**Session boundary rules:**
- No position is carried overnight from intraday simulation (unless strategy
  explicitly declares overnight holds).
- The last signal before 15:15 IST is the final entry opportunity; 15:30 close
  enforces all open positions to exit.
- Intraday slippage is typically higher than end-of-day slippage; 15-minute bar
  model uses 0.08% large-cap / 0.20% mid-cap.

---

### C.3 — Tick Replay Model

Used when highest-fidelity execution simulation is required.

**Tick data structure:** Timestamp, Last Trade Price, Volume, Bid, Ask.
**Fill model:** Market orders fill at Ask (buy) or Bid (sell) plus slippage.
  In high-frequency simulation, slippage is a function of order size relative
  to the available Bid/Ask queue depth.
**Gap handling:** If tick data has a gap > 1 minute (e.g., market halt), the
  simulation pauses and resumes; no fictitious ticks are interpolated.

---

### C.4 — Paper Trading Replay Model

Paper trading follows the same signal timing as the live trading system.

**Signal timing:** Signal generated at close of session N (using same data
pipeline as live).
**Execution timing:** Order placed at open of session N+1 via paper OrderManager.
**Fill model:** Market open price + standard slippage model.
**Paper ledger:** Records paper position, paper P&L, paper equity curve in
data/paper_trades.csv. Paper ledger is never mixed with the production
trade ledger.

---

### C.5 — Execution Models Comparison

| Model          | Granularity  | Fill Basis              | Slippage           | Use Case                      |
|----------------|--------------|-------------------------|--------------------|-------------------------------|
| Next-Open      | Daily bar    | Next session open price | Fixed percentage   | Most strategies (default)     |
| Next-Open Tick | Daily + Tick | Open tick + spread      | Spread-based       | High-accuracy daily model     |
| Intrabar       | 15-min bar   | Mid-bar price           | Higher fixed pct   | Intraday strategies           |
| Tick           | Sub-minute   | Bid/Ask + depth model   | Depth-based        | Highest-fidelity execution    |
| VWAP           | Daily bar    | VWAP of next session    | Volume-participation | Large-size strategies       |

---

## SUPPLEMENT D — MONTE CARLO REFERENCE

### D.1 — Monte Carlo Configuration Reference

**Trade Permutation Monte Carlo:**
Minimum iterations: 500.
Standard iterations: 1,000.
Thorough mode: 5,000.
Process: Shuffle trade order using Fisher-Yates algorithm with a fixed seed per
iteration. Recompute metrics for shuffled sequence. No trade characteristics
(P&L, duration) are changed — only order.

Purpose: Tests whether good performance was dependent on the specific timing
of winning and losing trades. A strategy where trades are independent of order
(rare in practice) will show minimal spread between P5 and P95.

---

**Price Perturbation Monte Carlo:**
Minimum iterations: 500.
Standard iterations: 1,000.
Noise scaling: Standard deviation of daily perturbations = 0.3 x daily return
standard deviation of the instrument.
Process: Add Gaussian noise scaled to 0.3 x realized vol to every daily close
price. Recalculate OHLC from perturbed close using daily return ratios.
Re-run full historical simulation on perturbed series.

Purpose: Tests whether the strategy's performance depends on hitting exact
historical prices, or whether it is robust to small price variations.

---

**Synthetic History Monte Carlo:**
Minimum iterations: 200.
Standard iterations: 500.
Generation model: Calibrate GBM or Regime-Switching model to historical data.
Generate N synthetic series with the same calibrated parameters. Run full
historical simulation on each.

Purpose: The most rigorous Monte Carlo test. Tests whether the strategy would
have performed well on many alternative market histories with similar statistical
properties to the actual history.

---

### D.2 — Significance Testing

**Null Hypothesis:** The strategy has no edge. Returns are random.

**Test Method (Permutation Test):**
1. Compute the observed Sharpe Ratio on the actual historical simulation.
2. Run 10,000 trade permutations.
3. Count how many permutations produce a Sharpe Ratio >= the observed Sharpe.
4. p-value = count / 10,000.
5. If p-value < 0.05: strategy has statistically significant edge at the 5% level.
6. If p-value < 0.01: strategy has statistically significant edge at the 1% level.

**Acceptance thresholds:**
p-value < 0.05 required for ACCEPTABLE SimQS contribution to SQD-02.
p-value < 0.01 required for GOOD or EXCELLENT SimQS contribution to SQD-02.

---

### D.3 — Monte Carlo Result Interpretation Guide

| P10 Sharpe vs P50 Sharpe Ratio | Interpretation                                |
|--------------------------------|-----------------------------------------------|
| P10 >= P50 x 0.80              | Highly robust; edge is consistent             |
| P10 >= P50 x 0.60              | Robust; acceptable degradation               |
| P10 >= P50 x 0.40              | Marginal robustness; monitor closely          |
| P10 < P50 x 0.40               | Weak robustness; possible overfitting         |
| P10 < 0                        | High risk of real-world failure               |

---

### D.4 — Bootstrap Simulation Detail

**Block Bootstrap Configuration:**
Block size: determined by autocorrelation analysis. For strategies with
significant autocorrelation at lag k: block size = k + 1. Minimum block
size: 5 sessions. Maximum block size: 21 sessions.

**Process:**
1. Divide the trade sequence into blocks of the configured block size.
2. Sample blocks with replacement until a trade sequence of the same length
   as the original is constructed.
3. Compute performance metrics for the resampled sequence.
4. Repeat 1,000+ times.
5. Compute P5, P10, P50, P90, P95 of resulting metric distribution.

**When to use Block Bootstrap over Trade Permutation MC:**
Strategies with momentum characteristics (where consecutive wins or losses are
correlated) should use block bootstrap rather than pure permutation MC. Pure
permutation destroys the serial correlation structure, underestimating the
strategy's vulnerability to drawdown sequences.

---

## SUPPLEMENT E — SIMULATION ANTI-PATTERNS

### E.1 — Anti-Pattern Framework

Simulation anti-patterns are systematic, recurring failures in simulation design
or interpretation that consistently produce misleading results. Unlike bugs,
anti-patterns are stable dysfunctional practices that must be detected through
methodology reviews and corrected through process discipline.

---

**SMAP-01 — Look-Ahead Contamination**

Definition: Simulation results are inflated because signal logic or data
preparation used information that would not have been available at the time of
the simulated decision.

Detection signals: Simulation performance significantly better than paper trading
performance on the same strategy. SC-16 V-02 check finds data access violations.
Strategy appears to "know" exact turning points.

Root cause: Feature calculation using forward-looking functions (e.g., normalizing
by the maximum of the entire period rather than only the data seen so far); data
split errors where test data accidentally leaks into training.

IIOS response: SC-16 V-02 is the primary defense. Any detected look-ahead results
in permanent quarantine. No workaround; the simulation must be re-run correctly.

---

**SMAP-02 — Survivor Bias**

Definition: Simulation uses only instruments that survived the historical period.
Instruments that went bankrupt, were delisted, or were removed from an index are
excluded, creating an artificially positive result.

Detection signals: Strategy performs much better in backtest than in paper trading.
Winning rate on historical constituents is much higher than on current constituents.

Root cause: Using the current index composition (e.g., today's NIFTY50) to define
the universe for a historical simulation.

IIOS response: Simulations must use the index composition as it existed at each
historical date. Historical index composition data must be maintained. SC-16 V-08
includes a survivor bias check.

---

**SMAP-03 — Transaction Cost Neglect**

Definition: Simulation applies zero or unrealistically low transaction costs,
making high-frequency strategies appear profitable when they would not be after
real costs.

Detection signals: Strategy has high trade count but mediocre gross performance.
Live performance significantly worse than backtest. High-frequency strategies
appearing highly profitable in simulation.

Root cause: Using zero-cost simulations as preliminary tests and forgetting to
apply costs before reporting results.

IIOS response: SC-B-004 HARD rule: all promotion evidence simulations must use
the standard cost model. SC-16 V-03 confirms costs are applied.

---

**SMAP-04 — Single-Path Overfitting**

Definition: A strategy is optimized and evaluated on a single historical path.
Its parameters are tuned to this specific path, and the result is reported as
evidence of the strategy's quality.

Detection signals: Walk-Forward Efficiency Ratio < 0.40 (very poor generalization).
Monte Carlo P10 Sharpe is far below P50. Strategy is highly sensitive to small
parameter changes.

Root cause: Single-pass backtesting without walk-forward validation; over-reliance
on IS optimization results.

IIOS response: SC-F-005 HARD rule requires WFE computation. Monte Carlo (Phase 5)
is a mandatory readiness gate. Walk-forward analysis is the standard evaluation method.

---

**SMAP-05 — Crisis Blindness**

Definition: Strategy validation uses only normal-market periods, not crisis
periods. The strategy appears robust but has never been tested against its
most important failure modes.

Detection signals: No stress tests in the strategy's simulation history.
Strategy was validated only on 2013–2019 (a mostly calm period) without crisis testing.
Phase 6 (Stress Testing) not completed in readiness checklist.

Root cause: Stress testing is time-consuming and produces uncomfortable results,
so it is skipped. Confirmation bias: evaluators focus on periods where the strategy
performs well.

IIOS response: Phase 6 of the Readiness Checklist is mandatory. SP-04 Stress
Test Pipeline includes at least 3 historical crisis scenarios.

---

**SMAP-06 — Simulation-to-Live Gap Neglect**

Definition: The Simulation Engine has produced results for a strategy, but no
one is tracking whether the simulated performance is being achieved in live trading.
The simulation-to-live gap widens without detection.

Detection signals: SC-17 simulation-to-live gap report shows gaps > 0.50 Sharpe
for multiple strategies. No comparison between simulated and live performance
in governance reports. Simulation results are produced and forgotten.

Root cause: Simulation is treated as a one-time activity rather than a continuous
calibration process. No monitoring of simulation assumptions against live experience.

IIOS response: SC-17 tracks simulation-to-live gap for every active strategy.
Gaps > 0.30 trigger investigation. Monthly governance report includes gap analysis.

---

**SMAP-07 — Determinism Assumption Violation**

Definition: Simulation produces different results on different runs due to
uncontrolled randomness, but users interpret each run as if it were the definitive
result.

Detection signals: SimQS SQD-08 (Determinism) score below 0.75. Re-running
a simulation produces meaningfully different metrics. Random seeds not documented.

Root cause: Random number generators without fixed seeds; external state
dependencies (current date used as default for time periods; live data polled
during historical simulation).

IIOS response: SC-A-005 requires engine version recording. All Monte Carlo
simulations use fixed seeds. SC-16 V-07 input integrity check includes seed verification.

---

**SMAP-08 — Stress Scenario Staleness**

Definition: The IIOS Stress Scenario Library has not been updated to reflect
current market realities. Scenarios calibrated in 2023 do not reflect the market
structure of 2025–2026.

Detection signals: Monthly governance review finds no scenario updates in > 12 months.
New market risks (e.g., emerging regulation, new asset classes) not represented.
Hypothetical scenarios are based on outdated volatility regimes.

Root cause: Scenario maintenance is not a scheduled activity; it is treated as
infrastructure that does not need attention.

IIOS response: Quarterly scenario review (Part VIII Section 8.6). Scenarios
older than 12 months without review are flagged in the governance report.

---

## SUPPLEMENT F — OPERATIONAL RUNBOOK

### F.1 — Pre-Session Startup Sequence

**Timing:** 08:30 IST — 09:00 IST

**Step 1 (08:30) — Health Check:**
SC-21 Health Manager startup check. All 21 components verified. SEHS must be
>= NOMINAL (0.75). Any component below CRITICAL triggers operator alert.

**Step 2 (08:35) — Audit Chain Verification:**
SC-20 Audit Manager verifies hash chain integrity. If chain break detected:
HALT; alert operator immediately. No simulation may run until chain integrity
is restored.

**Step 3 (08:40) — Scenario Library Update Check:**
SC-03 confirms all scenarios in the Standard Library are current. Any scenario
flagged for review (> 12 months since last update) is surfaced in the startup report.

**Step 4 (08:45) — Data Feed Verification:**
Historical data feed connectivity confirmed. If yfinance or Dhan archive unavailable,
alert operator. Running simulations that require today's data is deferred.

**Step 5 (08:50) — Pending Simulation Queue Review:**
SC-01 lists all QUEUED simulations. Priority order: stress tests (risk calibration),
strategy promotion simulations, scheduled routine simulations, research simulations.

**Step 6 (08:55) — Governance Acknowledgment:**
Operations Lead acknowledges prior session governance report. Any outstanding
items resolved or escalated.

**Step 7 (09:00) — Readiness Certification:**
SC-21 SEHS confirmed >= NOMINAL. Startup report delivered to L17 dashboard and Telegram.
Simulation Engine CERTIFIED for the session.

---

### F.2 — Intraday Simulation Management

During market hours (09:15–15:30 IST), the Simulation Engine operates in
background mode — running queued simulations and monitoring paper trading.

**Paper Trading Monitoring (09:15–15:30):**
SC-15 tracks paper trading P&L every 30 minutes. Alerts if paper trading
produces a session loss > 1.5% (WARNING) or > 2.5% (CRITICAL).

**Running Simulation Monitoring:**
SC-21 checks all running simulations every 5 minutes. Progress updated in SC-01.
Alert if any simulation exceeds 2x expected duration.

**Priority Management:**
Strategy promotion simulations (blocking advance to live) are run first.
Research simulations are run in background with lower priority.

**Real-Time Scenario Requests:**
Operator may request ad-hoc simulations during the session. These are queued
and executed based on priority. HARD rule: no ad-hoc simulation interrupts
a running promotion simulation.

---

### F.3 — Post-Session Processing Sequence

**Timing:** 15:30 IST — 16:30 IST

1. **15:30 — Paper Trading Session End:**
SC-15 computes daily paper trading P&L for all paper trading strategies.
Cumulative performance updated.

2. **15:35 — Simulation Completion Check:**
SC-01 confirms all sessions' scheduled simulations have completed or are queued.
Any FAILED simulations identified and queued for operator review.

3. **15:45 — Analytics Update:**
SC-17 Analytics Engine updates simulation-to-live gap for all active strategies.
Any new gaps > 0.30 flagged.

4. **15:50 — Daily Report Generation:**
SC-18 generates daily simulation summary report.
Delivered to L17 ControlTower dashboard and Telegram.

5. **16:00 — Governance Report:**
SC-19 Governance Manager compiles all governance events from today's session.
Governance report delivered.

6. **16:10 — Audit Chain Close:**
SC-20 closes today's audit chain. Creates daily terminal record.
Hash chain integrity verified for all today's records.

7. **16:20 — Archive Processing:**
Any newly approved simulations archived. SC-03 artifact store updated.

8. **16:30 — Health Final:**
SC-21 records end-of-session SEHS. L17 dashboard final update.

---

### F.4 — Incident Response Procedures

**IR-01 — Look-Ahead Bias Detected**

Symptom: SC-16 V-02 check fails on a simulation result.

Immediate action: Result quarantined automatically. Operator notified via Telegram.
Investigation:
  1. Review signal logic for the affected simulation. Identify the data access
     that created look-ahead contamination.
  2. Fix signal logic.
  3. Re-run simulation with corrected logic.
  4. Quarantined result is not deleted but permanently marked as contaminated.

Recovery time target: < 4 hours (identify issue); re-run may take longer.

---

**IR-02 — Hash Chain Integrity Failure**

Symptom: SC-20 detects a break in the audit chain.

Immediate action: HALT all simulation runs. Alert operator. Alert System Owner.
Investigation:
  1. Identify which audit record breaks the chain.
  2. Determine cause: data corruption (storage failure) or unauthorized modification.
  3. If corruption: restore from backup; replay audit events since backup.
  4. If unauthorized modification: CRITICAL security incident. System Owner escalation.

Recovery time target: < 2 hours.

---

**IR-03 — SEHS Below CRITICAL**

Symptom: SC-21 reports SEHS < 0.30.

Immediate action: Halt new simulation submissions. Running simulations may continue
unless the failing components are required for those simulations.
Investigation:
  1. Identify which components are contributing most to SEHS failure.
  2. Component-specific recovery procedures.
  3. Restore components until SEHS >= DEGRADED (0.55) before accepting new submissions.

Recovery time target: < 30 minutes.

---

**IR-04 — Paper Trading Order Routing Failure**

Symptom: Paper trading orders generating errors in SC-10 Execution Simulator.
Orders are not being recorded in the paper ledger.

Immediate action: Pause paper trading for affected strategy. Alert operator.
Investigation:
  1. Confirm PAPER_TRADING flag is set correctly.
  2. Confirm paper ledger is writable.
  3. Review SC-10 execution simulator error logs.

Recovery: Fix routing issue. Re-process missed orders based on historical prices
at the time they should have been filled. Document in governance record.
Recovery time target: < 1 hour.

---

**IR-05 — Simulation Data Feed Failure**

Symptom: Historical data feed unavailable; running simulation cannot load required data.

Immediate action: Running simulation pauses at last checkpoint. New simulations
requiring unavailable data are queued (not aborted).
Investigation:
  1. Determine if yfinance or Dhan archive is the affected source.
  2. Try fallback source.
  3. If no data available: defer simulation; alert operator.

Recovery: Resume from checkpoint when data is available. No simulation is
discarded due to temporary feed failure.
Recovery time target: 30 minutes to 4 hours depending on data feed recovery.

---

**IR-06 — Simulation Result Anomaly**

Symptom: SC-15 Performance Evaluator flags anomalous result: Sharpe Ratio > 5.0
or Win Rate > 90% (possible data error) or MaxDD = 0% (suspect zero-risk result).

Immediate action: Anomalous result flagged automatically by SC-15. Automatic
approval paused. Operator review required.
Investigation:
  1. Review data for the simulation period: any data errors (missing entries,
     extreme outliers)?
  2. Review strategy logic: any logic error that creates artificially good results?
  3. If anomaly is explained and valid: manual approval with documented rationale.
  4. If anomaly is unexplained: quarantine result; fix data or logic; re-run.

---

## SUPPLEMENT G — GOVERNING DESIGN RECORDS

### GDR-SIM-001 — The Simulation Engine Never Places Live Orders

**Decision:** No pathway exists from the Simulation Engine to the Dhan broker
integration or any other live order execution mechanism.

**Context:** The Simulation Engine has complete access to strategy signal logic
and market data. Theoretically, it could route signals to live execution.
Should it?

**Decision Made:** Never. The Simulation Engine is a read-only, evaluation-only
system. Its outputs are knowledge (results, metrics, reports) — never actions.

**Rationale:** The value of simulation derives precisely from its isolation.
A simulation environment that could accidentally place live orders is not a
simulation environment — it is a risk. The architectural isolation is absolute
and enforced at the OrderManager level (PAPER_TRADING=True flag), the data
store level (read-only access), and the audit level (any attempt to invoke
live execution from simulation context triggers an audit alert).

---

### GDR-SIM-002 — The Simulation Engine Never Modifies Production Data

**Decision:** The Simulation Engine has read-only access to all production data
stores. All simulation outputs are written to simulation-specific stores.

**Context:** Could the Simulation Engine write directly to strategy records to
update parameters after optimization?

**Decision Made:** No. All simulation results are delivered as knowledge —
reports, metrics, recommendations. Production systems consume the knowledge and
decide what to change.

**Rationale:** Separating the simulation (what would have happened) from the
decision (what should change) maintains the integrity of both. Production systems
that change their own state based directly on simulation outputs without human
review create a feedback loop that can amplify errors rather than correct them.

---

### GDR-SIM-003 — Look-Ahead Bias Is a HARD Rule Violation

**Decision:** Any simulation result with detected look-ahead bias is permanently
quarantined. There is no remediation pathway that makes a contaminated result
acceptable.

**Context:** Could a look-ahead-contaminated result be corrected by applying a
discount to its metrics?

**Decision Made:** No. A contaminated result is destroyed as evidence.

**Rationale:** Look-ahead bias is not a quantifiable error — its impact depends
on how much future information leaked into the signal, in which direction, and
at which points. There is no reliable way to discount the contamination. The
only correct response is to quarantine the result and re-run correctly.

---

### GDR-SIM-004 — Simulation Results Are Evidence, Not Decisions

**Decision:** Simulation results inform production decisions but never
automatically make them. Human judgment mediates all decisions derived from
simulation evidence, except for clearly bounded automated gates (e.g., if
SimQS >= 0.55, the result is accepted — but the strategy is not promoted
without the full checklist).

**Context:** Should a very high SimQS result auto-promote a strategy?

**Decision Made:** No. Simulation evidence is necessary but not sufficient.
The full 12-phase readiness checklist, risk engine review, and governance
authorization are all required even with perfect SimQS.

**Rationale:** Simulation, however comprehensive, is still a model of reality.
Human judgment provides the final sanity check that models cannot.

---

### GDR-SIM-005 — Paper Trading Is Operational Validation, Not Statistical Validation

**Decision:** Paper trading results are used to confirm that the strategy operates
correctly in live conditions. They are not used as primary statistical evidence
for strategy promotion.

**Context:** Could a strategy with a strong paper trading period (e.g., 60 sessions)
skip the full historical simulation?

**Decision Made:** No. Paper trading evidence supplements but does not replace
historical simulation and Monte Carlo validation.

**Rationale:** 60 sessions of paper trading provides statistically unreliable
performance estimates (too small a sample). More importantly, paper trading
covers only the current market regime, not the range of regimes the strategy will
encounter over its lifetime. Historical simulation across multiple regimes is
irreplaceable.

---

### GDR-SIM-006 — Stress Testing Is Mandatory, Not Optional

**Decision:** Phase 6 of the Readiness Checklist (Stress Testing) is mandatory
for all strategies before live deployment. Stress testing cannot be waived by any
operator.

**Context:** Could stress testing be waived for strategies with strong historical
simulation results?

**Decision Made:** No. Strong historical simulation results say nothing about
behavior in crisis conditions.

**Rationale:** Historical simulations typically use periods that happened to be
available — and most periods are not crisis periods. A strategy can accumulate
strong historical results without having been tested in conditions that matter most
for capital preservation. Stress testing is the systematic antidote to this blind spot.

---

### GDR-SIM-007 — All Simulation Artifacts Are Permanent

**Decision:** Approved simulation artifacts are never deleted.

**Context:** Storage cost of permanent simulation archives.

**Decision Made:** Permanent retention. Storage is provided by the data/ volume;
compression ensures reasonable storage efficiency.

**Rationale:** Simulation results are the evidence base for every production
decision. Deleting them removes the ability to audit historical decisions,
understand why strategies were promoted, and investigate future anomalies. The
governance and accountability value exceeds any storage cost consideration.

---

### GDR-SIM-008 — Monte Carlo Is Required for All Strategy Promotions

**Decision:** Every strategy seeking promotion to APPROVED status must have a
Monte Carlo simulation result with P10 Sharpe >= 0.50. This is Phase 5 of the
Readiness Checklist and a non-waivable gate.

**Context:** Could a strategy with an exceptional historical simulation (Sharpe 2.5)
skip Monte Carlo?

**Decision Made:** No. Monte Carlo tests something the historical simulation cannot:
whether the result depends on the specific historical sequence, or whether it is
robust to alternative sequences.

**Rationale:** A Sharpe of 2.5 in a single-path historical simulation could be
genuine edge, or it could be extreme luck on a specific sequence of events. Monte
Carlo distinguishes the two. A strategy with Sharpe 2.5 but P10 Sharpe -0.2 is a
highly overfit strategy that should not be deployed.

---

## SUPPLEMENT H — COMPREHENSIVE GLOSSARY

### H.1 — Core Simulation Terms

**Backtest:** Historical simulation of a trading strategy on archived market data.
The primary evidence for strategy quality, but not the only evidence required.

**Bar:** A unit of market data summarizing a time period: Open, High, Low, Close,
Volume (OHLCV). Standard IIOS simulation granularity: 1-day bars.

**Benchmark:** Reference index for performance comparison. Primary IIOS benchmark:
NIFTY50 (IIOS code: BM-01).

**Bootstrap Simulation:** Resampling technique that draws blocks of the historical
trade record with replacement to produce many alternative performance estimates.
More conservative than pure trade permutation Monte Carlo for autocorrelated returns.

**Calmar Ratio:** Annualized Return divided by Maximum Drawdown. Measures return
per unit of worst-case loss risk.

**Chronological Integrity:** The guarantee that simulation signal logic at time T
accesses only data available before time T. The foundational requirement preventing
look-ahead bias.

**Conditional Drawdown at Risk (CDaR):** The expected drawdown given that a drawdown
event is occurring. A tail-risk measure that complements maximum drawdown.

**Digital Twin:** A complete virtual replica of the IIOS system, running in parallel
with production using the same logic but routing all outputs to simulation stores.

**Drawdown:** Decline in strategy NAV from a peak to a subsequent trough.
Maximum Drawdown (MaxDD) is the largest such decline in the simulation period.

---

### H.2 — Simulation Engine Component Terms

**SEHS (Simulation Engine Health Score):** Composite health score (0.0–1.0) across
all 21 Simulation Engine components. Tiers: OPTIMAL(0.90+), NOMINAL(0.75-0.89),
DEGRADED(0.55-0.74), CRITICAL(0.30-0.54), FAILED(<0.30).

**SimQS (Simulation Quality Score):** Composite quality score (0.0–1.0) for a
simulation result. Computed from 13 quality dimensions. Tiers: EXCELLENT(0.85+),
GOOD(0.70-0.84), ACCEPTABLE(0.55-0.69), MARGINAL(0.35-0.54), FAILED(<0.35).

**SC-01 (Simulation Registry):** Master record of all simulation runs.

**SC-06 (Historical Engine):** Executes bar-by-bar historical simulations.

**SC-07 (Synthetic Market Generator):** Generates artificial market data.

**SC-08 (Monte Carlo Engine):** Manages probabilistic simulation iterations.

**SC-09 (Stress Testing Engine):** Executes extreme scenario simulations.

**SC-16 (Simulation Validator):** Validates result integrity before acceptance.

**SC-20 (Simulation Audit Manager):** Maintains hash-chained audit trail.

**SC-21 (Simulation Health Manager):** Monitors SEHS across all 21 components.

---

### H.3 — Simulation Process Terms

**Data Granularity:** The time resolution of bar data: 1-day, 1-hour, 15-minute,
5-minute, 1-minute, or tick.

**Equity Curve:** Time series of portfolio net asset value (NAV) at each bar or
session throughout the simulation.

**Execution Slippage:** Difference between the expected execution price and the
actual simulated fill price. Sources: bid-ask spread, market impact, timing.

**Fill Model:** The rule set for determining simulated execution prices, sizes,
and timing. IIOS standard: next-bar open plus slippage.

**Forward Testing:** Testing a strategy using data from the current period —
recent data not used in development.

**Hypothesis:** Documented explanation of why a market inefficiency exists.
Required before strategy registration.

**In-Sample (IS) Period:** Historical data used to develop and optimize a strategy.
The period where the strategy was "trained."

**Information Ratio:** Active return divided by tracking error. Measures consistency
of excess return.

**Jump-Diffusion Model:** Price series generation model that adds Poisson-distributed
sudden price jumps to the standard Brownian motion. Used for crash simulation.

**Kill Switch:** The L9 RiskGuardian mechanism that halts all trading and strategy
signal generation when specified thresholds are breached (VIX > 45, daily loss > 2%).

**Latency:** Time delay between signal generation and order execution. Sources:
data feed latency, compute latency, order routing latency, broker acknowledgment latency.

**Liquidity:** The availability of buyers or sellers at a given price. Low liquidity
increases slippage and may make large orders impossible to execute at expected prices.

**Look-Ahead Bias:** A simulation error where signal logic uses data that would not
have been available at the time of the simulated decision. Results in artificially
inflated performance.

**MAE (Maximum Adverse Excursion):** Worst intraday loss experienced by a trade.
Used for stop-loss placement evaluation.

**MFE (Maximum Favorable Excursion):** Best intraday profit experienced by a trade.
Used for exit timing evaluation.

**Monte Carlo Simulation:** Probabilistic technique using repeated random sampling
to generate distributions of possible outcomes.

**Out-of-Sample (OOS) Period:** Historical data held back from strategy development
and optimization. The "test set" for evaluating generalization.

**Paper Ledger:** Simulation-only trade record where paper trading results are stored.
Completely isolated from the production trade ledger.

**Paper Trading:** Real-time simulation using live data but paper (simulated) orders.

**Payoff Ratio:** Average winning trade / average losing trade.

**Regime:** Market condition classification: TRENDING_UP, TRENDING_DOWN, SIDEWAYS,
VOLATILE, UNCERTAIN. Strategies perform differently in different regimes.

**Scenario:** A complete specification for a simulation run: type, instruments,
time period, cost model, and configuration parameters.

**Sharpe Ratio:** (Return minus Risk-Free Rate) divided by Return Standard Deviation.
Standard IIOS risk-adjusted performance metric.

**Simulation Run ID (SRI):** Unique identifier for a simulation run.
Format: SIM-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}.

**Slippage Model:** Rules for calculating execution price degradation.
IIOS default: fixed percentage (0.05% large-cap, 0.15% mid-cap, 0.30% small-cap).

**Sortino Ratio:** (Return minus Risk-Free Rate) divided by Downside Standard
Deviation. Penalizes only downside volatility.

**Statistical Significance:** The probability that the observed performance results
are not due to random chance. IIOS minimum: p-value < 0.05.

**Stress Scenario:** A defined adverse market condition used to test strategy
resilience. IIOS maintains both historical crisis scenarios and hypothetical extremes.

**Survivor Bias:** Simulation error caused by testing only on instruments that
survived the historical period, excluding bankruptcies and delistings.

**Synthetic Data:** Artificially generated market data with defined statistical
properties. Used when real historical data is insufficient or when testing beyond-
history extremes.

**Transaction Cost:** All costs of executing a trade: brokerage, Securities
Transaction Tax (STT), exchange fees, SEBI turnover fee, and slippage.

**Trade Permutation Monte Carlo:** Monte Carlo technique that randomizes the order
of historical trades to test whether good performance depends on trade timing.

**Walk-Forward Analysis:** Rolling IS/OOS validation technique. Optimize on IS
window; test on OOS window; step forward; repeat. The gold standard for testing
temporal generalization.

**Walk-Forward Efficiency Ratio (WFE):** OOS Sharpe divided by IS Sharpe.
Measures how well optimization generalizes. IIOS minimum: WFE >= 0.50.

**Virtual Market:** The complete IIOS Simulation Engine — the official "try before
you deploy" environment for all production system changes.

---

## APPENDIX — WORKED EXAMPLES

### WE-01 — Standard Strategy Validation: New Momentum Strategy

**Scenario:** A new momentum strategy (STR-MOMENTUM-20251201-000005) has been
approved for simulation evidence by the Strategy Engine. The operator initiates
the full simulation evidence workflow.

**Step 1 — Historical Simulation (SP-01):**
Scenario: SCN-HIS-LONGTERM-01 (5-year NIFTY50 universe).
SC-01 assigns SRI: SIM-HIS-20251201-00000087.
SC-06 Historical Engine runs 5-year walk-forward simulation (4 windows).

Results: IS Sharpe 1.35; OOS Sharpe 0.94; WFE = 0.70 (GOOD).
Win Rate 56%; MaxDD 11%; Trade count: 248 trades.
SC-16 Validation: All 8 checks PASS. Validation certificate issued.
SC-15 SimQS: 0.79 (GOOD).
SC-19 Governance: auto-approved (SimQS >= 0.55).

**Step 2 — Monte Carlo (SP-03):**
SC-08: 1,000 trade permutation + 500 price perturbation iterations.
P10 Sharpe: 0.61 (> 0.50 minimum). P50 Sharpe: 0.89. P95 Sharpe: 1.28.
Statistical significance: p-value = 0.003 (highly significant).
SC-16: 98.5% iterations completed (> 90% minimum). PASS.
SimQS: 0.81 (GOOD).

**Step 3 — Stress Testing (SP-04):**
Scenarios tested: COVID-2020, GFC-2008, CHINA-2015, VOLT-2022.
Plus hypothetical: SCN-HYP-CRASH25PCT-01.
Kill switch validation: In COVID-2020, L9 RiskGuardian simulated trigger at Day 8
(VIX > 45 threshold crossed). MaxDD at trigger: 6.2%. PASS (< 15% limit).
Worst stress scenario: COVID-2020: MaxDD 14.8% (< 15% limit). PASS.
SC-15 Stress SimQS: 0.71 (GOOD).
Operations Lead review: approved.

**Step 4 — Portfolio Simulation (SP-08):**
Portfolio: STR-MOMENTUM-20251201-000005 added to the 5-strategy active portfolio.
Portfolio MaxDD with new strategy: 8.4% (< 15% limit). PASS.
Average pairwise correlation of new strategy with existing: 0.48 (< 0.70 limit). PASS.

**Outcome:**
Phase 7 performance gates: OOS Sharpe 0.94 (>= 0.80 PASS); MaxDD 11% (<= 15% PASS);
Win Rate 56% (>= 50% PASS); WFE 0.70 (>= 0.50 PASS).
All 12 Readiness Checklist phases: PASS. Simulation Readiness CERTIFIED.
Strategy submitted to L15 ResearchLab for final promotion review.

---

### WE-02 — Monte Carlo Reveals Fragile Strategy

**Scenario:** STR-MEANREV-20251001-000002 passes historical simulation (IS Sharpe 1.8;
OOS Sharpe 1.1) but Monte Carlo reveals extreme sensitivity to trade ordering.

**Historical Simulation Result:**
IS Sharpe 1.8; OOS Sharpe 1.1; WFE 0.61. Win Rate 64%; MaxDD 7%.
Appears to be a very strong result. SimQS 0.82 (GOOD).

**Monte Carlo Result (1,000 permutations):**
P50 Sharpe: 1.02.
P10 Sharpe: -0.18. (P10 / P50 = -0.18 / 1.02 = negative!)
P5 Sharpe: -0.45.
Statistical significance: p-value = 0.18 (not significant at 5% level).
SC-08: P10 Sharpe negative; p-value > 0.05. Phase 5 FAIL.

**Interpretation:**
The strategy's high OOS Sharpe occurred during a specific sequence of trades.
In 10% of random orderings, the strategy loses money. The historical sequence
was lucky, not indicative of persistent edge. The strategy is fragile to trade
ordering — a hallmark of overfit strategies.

**Outcome:**
Phase 5 (Monte Carlo) FAIL. SimQS for Monte Carlo result: 0.25 (FAILED tier).
Strategy cannot advance to live. Returned to L5 StrategyLab for redesign.
Governance record: simulation evidence insufficient; strategy not promotable in
current form.

---

### WE-03 — Stress Test Reveals Kill Switch Issue

**Scenario:** STR-BREAKOUT-20251101-000003 passes historical simulation and Monte Carlo.
Stress testing reveals a kill switch calibration problem.

**Historical and Monte Carlo:** PASS. OOS Sharpe 0.87; WFE 0.56; P10 Sharpe 0.51.

**Stress Test Results (COVID-2020 scenario):**
SC-09 runs the COVID-2020 crash scenario. L9 RiskGuardian (simulated) is expected
to trigger when: (a) VIX > 45 OR (b) daily portfolio loss > 2%.

Observation: During the COVID-2020 simulation, VIX exceeded 45 on Day 7 of the
crash. Expected: kill switch triggers; strategy suspended. Actual: kill switch
did not trigger until Day 11 because the VIX data feed used in the simulation was
the India VIX, not the standard VIX reference used in L9's rules. A configuration
mismatch between the simulation and live kill switch configuration.

**Outcome:**
SC-14 Risk Simulator flags kill switch calibration discrepancy. Operations Lead
notified. Investigation reveals the configuration mismatch. Kill switch rules
are updated to use India VIX consistently in both simulation and live systems.
Stress test re-run after fix: kill switch triggers on Day 7. PASS.

This example demonstrates why stress testing is mandatory: it found a kill switch
configuration error that would have resulted in the kill switch failing to trigger
4 days earlier than it should in a real crisis.

---

### WE-04 — SimQS Computation Example

**Scenario:** SimQS computation for SRI SIM-HIS-20251201-00000087.

**Dimension Scores:**

| Dimension               | Weight | Score | Contribution |
|-------------------------|--------|-------|--------------|
| SQD-01 Accuracy         | 0.20   | 0.95  | 0.190        |
| SQD-02 Statistical Val. | 0.18   | 0.88  | 0.158        |
| SQD-03 Repeatability    | 0.12   | 1.00  | 0.120        |
| SQD-04 Reproducibility  | 0.10   | 0.90  | 0.090        |
| SQD-05 Coverage         | 0.10   | 0.85  | 0.085        |
| SQD-06 Realism          | 0.10   | 1.00  | 0.100        |
| SQD-07 Robustness       | 0.08   | 0.75  | 0.060        |
| SQD-08 Determinism      | 0.06   | 1.00  | 0.060        |
| SQD-09 Performance      | 0.06   | 0.85  | 0.051        |
| SQD-10 Scalability      | 0.04   | 0.75  | 0.030        |
| SQD-11 Maintainability  | 0.03   | 1.00  | 0.030        |
| SQD-12 Auditability     | 0.02   | 1.00  | 0.020        |
| SQD-13 Op Reliability   | 0.01   | 1.00  | 0.010        |

**SimQS = 1.004 (capped at 1.00) = 1.00 — EXCELLENT tier**

Note: SQD-07 Robustness scored 0.75 (GOOD not EXCELLENT) because WFE was 0.70
(in the 0.50-0.70 range, not above 0.70). This is expected and acceptable for
a GOOD-tier robustness score.

---

### WE-05 — Paper Trading Validation

**Scenario:** STR-FACTOR-20251001-000001 has passed all historical simulation gates
and is entering paper trading (Phase 4, operational readiness confirmation).

**Paper trading period:** Sessions 1–30 (first 30 live sessions after approval).

**Paper trading results — Session 1–10 (operational check):**
Signal generation: correct (signals generating on schedule).
Order routing: correct (all orders routing to paper ledger).
Position management: correct (positions opening and closing as expected).
P&L calculation: verified against manual calculation on 3 spot checks.
Data feed: confirmed correct (no stale prices detected).

Session 1–10 verdict: OPERATIONAL PASS.

**Paper trading results — Session 11–30 (performance monitoring, not statistical gate):**
Paper P&L: +1.8% over 20 sessions (not statistically meaningful but directionally positive).
No operational errors.

**Outcome:** Operational readiness CONFIRMED. Strategy advances to live status.
Note: The 1.8% paper return is recorded but not used as promotion evidence —
20 sessions is too small for statistical evaluation. The historical simulation
evidence (Sharpe 0.87, WFE 0.56) remains the primary performance evidence.

---

### WE-06 — Decision Replay Validation

**Scenario:** L10 DebateAndDecision system has undergone a configuration change
(agent weight adjustment). SC-12 Decision Simulator runs a decision replay to
confirm the change does not create a regression.

**Setup:**
Replay period: last 45 trading sessions.
Original decisions: loaded from L17 ControlTower audit logs.
Replayed through: updated L10 configuration.

**Determinism Check:**
For all 45 sessions in the prior configuration (before the weight change):
12 BUY decisions; 8 SELL decisions; 25 NEUTRAL decisions.

With the updated configuration applied to the same 45 sessions:
11 BUY decisions; 9 SELL decisions; 25 NEUTRAL decisions.

Change: 2 sessions shifted from BUY to SELL. This is within the acceptable range
for a weight adjustment (configuration change was specifically designed to make
the system slightly more cautious in trending markets).

**Quality Assessment:**
The 2 sessions that changed from BUY to SELL were sessions where the original
BUY decision had marginal confidence (0.61 and 0.63 on the 0.50–1.00 scale).
The updated configuration correctly identifies these as near-the-threshold cases
where reduced confidence justifies a more cautious call.

**Outcome:** Decision replay PASS. No regression. Configuration change approved.
Governance record created. L17 ControlTower updated with new configuration.

---

## DOCUMENT SUMMARY

### Document Metrics

| Metric                          | Value                                     |
|---------------------------------|-------------------------------------------|
| Document Code                   | IIOS-SIM-ENG-ARCH-001                     |
| Architecture Series             | IIOS Engine Architecture Series           |
| Document Number                 | 18 of 18                                  |
| Status                          | FINAL                                     |
| Parts Covered                   | I — X                                     |
| Supplements Covered             | A — H                                     |
| Appendix                        | 6 Worked Examples                         |
| Simulation Types Defined        | 21 (SIM-01 through SIM-21)                |
| Components Defined              | 21 (SC-01 through SC-21)                  |
| Lifecycle Stages                | 12 (SLS-01 through SLS-12)                |
| Simulation Services             | 14 (SS-01 through SS-14)                  |
| Processing Pipelines            | 11 (SP-01 through SP-11)                  |
| Quality Dimensions (SQD)        | 13 (SQD-01 through SQD-13)                |
| Constitutional Rule Categories  | 15 (SC-A through SC-O)                    |
| Constitutional Rules Total      | 80 (62 HARD, 18 SOFT)                     |
| Readiness Phases                | 12 phases; 59 HARD gate items             |
| Anti-Patterns Catalogued        | 8 (SMAP-01 through SMAP-08)               |
| Governing Design Records        | 8 (GDR-SIM-001 through GDR-SIM-008)       |
| Incident Response Procedures    | 6 (IR-01 through IR-06)                   |
| Stress Scenarios in Library     | 10 (6 historical + 4 hypothetical)        |
| Worked Examples                 | 6 (WE-01 through WE-06)                   |
| Glossary Terms                  | 60+                                       |

---

### Parts Summary

| Part | Title                          | Contents                                                   |
|------|--------------------------------|------------------------------------------------------------|
| I    | Simulation Philosophy          | 16 definitions; 5 arguments for simulation primacy         |
| II   | Simulation Taxonomy            | 21 types (SIM-01–SIM-21) with full profiles                |
| III  | Core Components                | 21 components; 4-tier architecture; full spec per component |
| IV   | Simulation Lifecycle           | 12 stages; state diagram; timing table                     |
| V    | Simulation Services            | 14 services (SS-01–SS-14) with interface descriptions       |
| VI   | Processing Pipelines           | 11 pipelines (SP-01–SP-11) with ASCII flow diagrams         |
| VII  | Quality Framework              | 13 SQD dimensions; SimQS formula; tier table               |
| VIII | Governance                     | Ownership; naming; versioning; approval; compliance        |
| IX   | Simulation Constitution        | 80 rules; 15 categories; HARD/SOFT classification          |
| X    | Readiness Checklist            | 12 phases; 59 HARD items; readiness state machine          |

---

### Supplements Summary

| Supplement | Title                    | Contents                                                    |
|------------|--------------------------|-------------------------------------------------------------|
| A          | Taxonomy Reference       | Full type profiles; component mapping; selection guide      |
| B          | Scenario Catalog         | 15 standard scenarios; addition process                     |
| C          | Replay Models            | 5 replay models; comparison table; fill decision logic      |
| D          | Monte Carlo Reference    | 3 MC techniques; significance testing; bootstrap detail     |
| E          | Anti-Patterns            | 8 anti-patterns; detection signals; IIOS responses          |
| F          | Operational Runbook      | Startup; intraday; post-session; 6 incident procedures      |
| G          | Governing Design Records | GDR-SIM-001 through GDR-SIM-008                             |
| H          | Comprehensive Glossary   | 60+ terms in 3 categories                                   |

---

### SimQS Quick Reference

**SimQS = sum of (weight_i x score_i) for all 13 dimensions**

| Dimension               | Weight |
|-------------------------|--------|
| SQD-01 Accuracy         | 0.20   |
| SQD-02 Statistical Val. | 0.18   |
| SQD-03 Repeatability    | 0.12   |
| SQD-04 Reproducibility  | 0.10   |
| SQD-05 Coverage         | 0.10   |
| SQD-06 Realism          | 0.10   |
| SQD-07 Robustness       | 0.08   |
| SQD-08 Determinism      | 0.06   |
| SQD-09 Performance      | 0.06   |
| SQD-10 Scalability      | 0.04   |
| SQD-11 Maintainability  | 0.03   |
| SQD-12 Auditability     | 0.02   |
| SQD-13 Op Reliability   | 0.01   |

**SimQS Tiers:**
EXCELLENT (0.85+) | GOOD (0.70-0.84) | ACCEPTABLE (0.55-0.69) | MARGINAL (0.35-0.54) | FAILED (<0.35)

---

### SEHS Quick Reference

**SEHS = Weighted average of 21 component health scores**

| Tier     | SEHS Range   | Operational Impact                                 |
|----------|--------------|----------------------------------------------------|
| OPTIMAL  | 0.90 – 1.00  | All simulation types available                     |
| NOMINAL  | 0.75 – 0.89  | All simulation types available; minor limits       |
| DEGRADED | 0.55 – 0.74  | Non-critical types suspended; essential runs only  |
| CRITICAL | 0.30 – 0.54  | Essential simulations only; escalate               |
| FAILED   | 0.00 – 0.29  | Halt all simulations; alert immediately            |

---

### Promotion Evidence Requirements Quick Reference

For a strategy to receive Simulation Readiness Certification:

| Required Simulation | Minimum Quality  | Gate                          |
|--------------------|------------------|-------------------------------|
| Historical (SIM-01) | SimQS >= 0.55    | Phase 4; WFE >= 0.50          |
| Monte Carlo (SIM-07)| P10 Sharpe >= 0.50; p < 0.05 | Phase 5          |
| Stress Test (SIM-09)| Kill switch confirmed | Phase 6                  |
| Portfolio (SIM-15)  | Portfolio MaxDD <= 15% | Phase 8              |
| Paper Trading (SIM-02)| Operational clean | Phase 4 (after live decision) |

All of the above must be in the simulation evidence dossier before the strategy
is submitted to L15 ResearchLab for promotion.

---

### Cross-Layer Integration Summary

| IIOS Layer              | Simulation Engine Interaction                             | Direction            |
|-------------------------|-----------------------------------------------------------|----------------------|
| L1 GlobalIntelligence   | Market context data for scenario calibration              | L1 → Sim Eng         |
| L2 MarketIntelligence   | Regime history for historical simulation                  | L2 → Sim Eng         |
| L3 MetaLearning         | Strategy weight history for learning replay               | L3 → Sim Eng         |
| L5 StrategyLab          | Strategy definitions for simulation; results consumed     | L5 ↔ Sim Eng         |
| L7 RiskControl          | Risk rules for risk replay; stress test results delivered | Sim Eng ↔ L7         |
| L9 RiskGuardian         | Kill switch thresholds calibrated via stress tests        | Sim Eng → L9         |
| L10 DebateAndDecision   | Decision replay inputs; results delivered                 | Sim Eng ↔ L10        |
| L11 ExecutionEngine     | Paper trading integrates via OrderManager (PAPER=True)    | Sim Eng → L11 paper  |
| L13 LearningSystem      | Trade outcomes for learning replay; results delivered     | Sim Eng ↔ L13        |
| L14 PerformanceAnalytics| Historical performance data for simulation context        | L14 → Sim Eng        |
| L15 ResearchLab         | Simulation evidence dossier delivered for promotion       | Sim Eng → L15        |
| L16 ValidationEngine    | Simulation results for 6-stage validation pipeline        | Sim Eng → L16        |
| L17 ControlTower        | SEHS, simulation reports, governance reports delivered    | Sim Eng → L17        |

---

### Component to Tier Mapping

**Tier 1 — Foundation:**
SC-01 Registry, SC-02 Catalog, SC-03 Scenario Manager, SC-04 Version Manager

**Tier 2 — Execution Engines:**
SC-05 Replay Engine, SC-06 Historical Engine, SC-07 Synthetic Market Generator,
SC-08 Monte Carlo Engine, SC-09 Stress Testing Engine, SC-10 Execution Simulator,
SC-11 Portfolio Simulator, SC-12 Decision Simulator, SC-13 Learning Simulator

**Tier 3 — Evaluation and Risk:**
SC-14 Risk Simulator, SC-15 Performance Evaluator, SC-16 Simulation Validator

**Tier 4 — Governance and Intelligence:**
SC-17 Analytics Engine, SC-18 Reporting Engine, SC-19 Governance Manager,
SC-20 Audit Manager, SC-21 Health Manager

---

### Service Level Agreements (SLAs)

| Operation                              | SLA Target         | Critical Threshold   |
|----------------------------------------|--------------------|----------------------|
| Simulation Run ID assignment           | < 1 second         | < 5 seconds          |
| Registry lookup                        | < 10ms             | < 50ms               |
| Scenario retrieval                     | < 100ms            | < 500ms              |
| Standard backtest (2-year daily)       | < 5 minutes        | < 15 minutes         |
| Walk-forward optimization (4 windows)  | < 15 minutes       | < 45 minutes         |
| Monte Carlo (1,000 iterations)         | < 30 minutes       | < 2 hours            |
| Stress test (1 scenario)               | < 60 minutes       | < 3 hours            |
| Portfolio simulation (5 strategies)    | < 60 minutes       | < 3 hours            |
| SimQS computation                      | < 30 seconds       | < 5 minutes          |
| Post-simulation report generation      | < 2 minutes        | < 10 minutes         |
| Audit record creation                  | < 10 seconds       | < 60 seconds         |
| SEHS computation                       | < 5 seconds        | < 30 seconds         |
| Simulation archive                     | < 5 minutes        | < 30 minutes         |
| Hash chain integrity check             | < 30 seconds       | < 5 minutes          |

---

### Error Taxonomy Quick Reference

| Code   | Category                     | Response                                     |
|--------|------------------------------|----------------------------------------------|
| SE-001 | Look-ahead bias detected     | Quarantine result; re-run correctly          |
| SE-002 | Hash chain break             | HALT; alert; investigate                     |
| SE-003 | Data feed unavailable        | Pause; retry; queue for retry                |
| SE-004 | Validation check failure     | Quarantine result; alert                     |
| SE-005 | Simulation timeout           | Checkpoint; retry; alert                     |
| SE-006 | Memory exhaustion            | Checkpoint; reduce batch; retry              |
| SE-007 | Artifact write failure       | Retry 3x; alert if persists                  |
| SE-008 | Paper order routing failure  | Pause paper trading; investigate; alert      |
| SE-009 | SimQS below FAILED tier      | Quarantine; mandatory review before use      |
| SE-010 | SEHS below CRITICAL          | Suspend new submissions; emergency mode      |
| SE-011 | Kill switch sim failure      | CRITICAL alert; halt stress run; escalate    |
| SE-012 | Monte Carlo > 10% fail       | Abort run; investigate failure mode          |
| SE-013 | Anomalous result flagged     | Hold for operator review; do not auto-approve |
| SE-014 | Survivor bias detected       | Flag result; check instrument universe       |
| SE-015 | Governance record failure    | Retry 3x; HALT if persistent                 |

---

### Constitutional Rule Quick Reference

**8 Absolute Prohibitions (selection of most critical HARD rules):**
1. The Simulation Engine NEVER places live orders (SC-G-001)
2. The Simulation Engine NEVER writes to production data stores (SC-G-002)
3. No simulation result with look-ahead bias can be used for decisions (SC-C-002)
4. All promotion simulations must use the standard cost model (SC-B-004)
5. A simulation result without a validation certificate cannot be used (SC-F-001)
6. Paper trading orders route to paper ledger ONLY (SC-C-007)
7. Audit records are immutable once created (SC-K-003)
8. All human overrides are recorded with identity, reason, and timestamp (SC-N-001)

---

### Architectural Impact Statement

The Simulation Engine occupies Layer 8 of the IIOS architecture and constitutes
the primary quality gate through which all strategies, decision systems, and
learning mechanisms must pass before live deployment. Without the Simulation Engine,
IIOS would be deploying untested components into live trading — a fundamentally
unsafe practice that historical evidence from trading system failures consistently
validates as catastrophic.

Three architectural principles define the Simulation Engine:

**1. Comprehensive Isolation.** The Simulation Engine is architecturally isolated
from all production actions. It cannot place live orders; it cannot modify
production data; it cannot alter configuration. This isolation is the foundation
of its trustworthiness as an evaluator. A simulation environment that can affect
production is not a simulation environment.

**2. Evidence Before Commitment.** No strategy enters production without documented
simulation evidence. The 12-phase Readiness Checklist, the 59 HARD gate items, and
the 8 mandatory simulation types ensure that every promotion decision has a
substantial, auditable evidence base.

**3. Continuous Calibration.** The Simulation Engine is not a one-time gate — it
is a continuous calibration mechanism. Simulation-to-live gap tracking, periodic
stress scenario updates, and learning simulation ensure that the virtual market
stays calibrated to the live market. When the simulation-to-live gap widens, the
engine signals that the simulation methodology needs updating — a form of
meta-learning that makes IIOS progressively more accurate as it accumulates
operational experience.

These three principles, together with the 80 constitutional rules and 8 Governing
Design Records, create a Simulation Engine that functions not merely as a testing
harness, but as the institutional quality consciousness of the IIOS system.

---

## EXTENDED REFERENCE — DETAILED COMPONENT SPECIFICATIONS

### Extended Component Profiles: Tier 2 Execution Engines Continued

The following provides extended operational detail for Tier 2 components,
supplementing the core definitions in Part III.

---

#### SC-09 Extended — Stress Testing Engine Scenario Application

**Crisis Fill Model Detail:**

During a crash simulation (SIM-10), the Execution Simulator (SC-10) applies
the Crisis Fill Model instead of the standard model:

Slippage scale factors by crisis severity:
- Normal conditions: 1.0x (standard slippage)
- Moderate stress (VIX 25–35): 1.5x slippage
- High stress (VIX 35–45): 2.5x slippage
- Extreme stress (VIX > 45): 4.0x slippage
- Crash day (single-session move > 5%): 6.0x–10.0x slippage depending on move size

Partial fill probability by stress level:
- Normal: 0% partial fills for standard-size orders
- High stress: 15% probability of partial fill on any order
- Extreme stress: 35% probability of partial fill
- Crash day: 60% probability of partial fill; remaining quantity fills at next session

Circuit breaker simulation:
- If simulated session decline reaches 10%: 45-minute circuit breaker applied
  (no fills during breaker; limit order queue cleared)
- If simulated session decline reaches 15%: session halt for remainder of day

**Liquidity Stress Model Detail (SIM-11):**

Normal liquidity: order fills at next-open + standard slippage.
Liquidity stress factor applied as multiplier to volume participation constraint:
- Mild liquidity stress: volume participation limit reduced to 5% (from 10%)
- Moderate: 3%
- Severe: 1%
- Illiquid: 0.5% (for mid-cap) or 0.2% (for small-cap)

Large orders in liquidity-stressed conditions must be executed across multiple
bars, accepting a higher aggregate slippage due to market impact.

---

#### SC-08 Extended — Monte Carlo Engine Result Quality Framework

**Convergence Testing:**

After every 100 Monte Carlo iterations, SC-08 checks whether the result has
converged. Convergence criterion: the P50 Sharpe Ratio changes by < 0.005
between consecutive 100-iteration batches. If converged before reaching the
target iteration count, the run may terminate early.

Early termination: if converged after 300 iterations (target 500), the run
terminates at 300 and reports the final distribution with a notation that
convergence was reached at 300/500 iterations.

**Confidence Intervals:**

For each percentile estimate (P5, P10, P50, P90, P95), SC-08 computes a 95%
confidence interval (bootstrap confidence interval over the MC iteration results).
Narrow confidence intervals indicate that the percentile estimate is stable;
wide confidence intervals suggest more iterations would improve precision.

Confidence interval reported as: P10 Sharpe = 0.61 ± 0.04 (95% CI: 0.57 – 0.65).

**Extreme Value Detection:**

MC iterations that produce extreme outlier results (Sharpe > 5.0 or < -3.0)
are flagged and investigated. Common causes: data errors in the iteration's
synthetic series; numerical issues with the metric computation. If > 1% of
iterations are extreme outliers, the run is investigated before acceptance.

---

#### SC-11 Extended — Portfolio Simulator Allocation Methods

**Method 1 — Equal Weight:**
All active strategies receive equal capital allocation.
Rebalancing: at the start of each simulation session.
Pro: simple; no performance-chasing bias.
Con: ignores strategy volatility (a high-volatility strategy is riskier
per unit of capital than a low-volatility strategy at equal weight).

**Method 2 — Equal Risk Contribution (Risk Parity):**
Capital allocated so each strategy contributes equally to portfolio volatility.
Allocation(i) proportional to 1 / Volatility(i).
Rebalancing: monthly (session 21).
Pro: strategies contribute equally to risk regardless of return volatility.
Con: lower-return low-volatility strategies may receive excess capital.

**Method 3 — Volatility Targeting:**
Each strategy's allocation is set to achieve a target annual volatility.
If target portfolio volatility is 10% and strategy i has annual volatility 20%,
then strategy i is allocated 50% of its "slot" (10% / 20% = 0.50 scale).

**Method 4 — Sharpe-Weighted:**
Capital weighted by rolling 60-session Sharpe Ratio.
Higher-Sharpe strategies receive more capital; lower-Sharpe receive less.
Rebalancing: monthly.
Pro: performance-sensitive allocation. Con: may concentrate in recently lucky
strategies; incorporates recency bias.

**IIOS Default:** Equal Risk Contribution (Method 2). Configured in scenario
definition for each portfolio simulation.

---

#### SC-12 Extended — Decision Simulator Determinism Standards

**Determinism Definition for IIOS:**

The Decision Simulator (SC-12) enforces the following determinism standard:
given identical inputs at identical timestamps, L10 DebateAndDecision must
produce an identical final recommendation.

**Non-Determinism Sources to Control:**
1. Random number generation: any randomness in agent decision logic must use
   a fixed seed for replay purposes. The seed is recorded in the decision log.
2. Floating-point non-determinism: floating-point operations may produce
   slightly different results on different hardware. SC-12 normalizes
   floating-point results to 6 decimal places before comparison.
3. External state: if L10 fetches live market data during replay (it should
   use the replayed historical data instead), results will differ. SC-12
   confirms that all data access during replay uses archived data.
4. Timing-dependent logic: any logic that uses wall-clock time must use
   the simulated replay clock, not the real-time clock.

**Acceptable Non-Determinism:**
None. Any non-determinism detected by SC-12 is reported as a CRITICAL finding
requiring investigation. Non-deterministic decision systems cannot be trusted
for consistent production behavior.

---

#### SC-13 Extended — Learning Simulator Attribution Methods

**Attribution Framework:**

SC-13 Learning Simulator uses three attribution methods to evaluate learning quality.

**Method 1 — Return Attribution:**
For each closed trade, attribute the trade's P&L to the signals that contributed
to the entry decision. If a trade was initiated by Signal A (RSI oversold), Signal B
(volume confirmation), and Signal C (regime alignment), the attribution weights
the contribution of each signal based on its confidence score at the time of entry.

Attribution check: the highest-confidence signal at entry should have the highest
correlation with trade outcome. If a low-confidence signal systematically has higher
attribution than a high-confidence signal, the confidence scoring is miscalibrated.

**Method 2 — Rolling Attribution:**
Compute rolling 20-session attribution for each signal type. Plot attribution
over time. A well-functioning learning system should show that high-attribution
signals maintain positive attribution, while low-attribution signals are
gradually down-weighted.

**Method 3 — Counterfactual Attribution:**
For each trade, compute what the outcome would have been if the dominant signal
had been absent (counterfactual: entry not taken). This provides a direct
measure of the signal's marginal contribution.

---

### Extended Reference — Simulation Data Quality Standards

The quality of simulation results depends directly on the quality of market
data used. The following standards govern data quality acceptance.

**Minimum Data Requirements:**

Daily OHLCV data for equity simulations:
- Minimum history: 504 sessions (2 years) for walk-forward analysis.
- Recommended: 1,260 sessions (5 years) for comprehensive regime coverage.
- Required completeness: >= 98% of sessions present (no more than 2% missing bars).
- Price plausibility: no daily return exceeding ±25% without news verification.

Intraday bar data:
- Minimum history: 252 sessions (1 year) for intraday strategies.
- Required completeness: >= 95% of intraday bars present.
- Session boundary: first bar >= 09:15 IST; last bar <= 15:30 IST.

Tick data (for SIM-04):
- Required: all trades for each session.
- No gaps > 5 minutes during standard market hours (except during circuit breakers).

**Gap Handling Policy:**

If a single session is missing: forward-fill from previous session's close.
If 2–5 consecutive sessions are missing: flag in data quality report; use forward-fill;
note that simulation results in this window may be slightly degraded.
If > 5 consecutive sessions missing: do not use forward-fill; exclude these sessions
from walk-forward windows; flag in data quality report and SimQS computation.
If > 10% of all sessions missing: abort simulation; report data quality failure.

**Price Outlier Detection:**

Z-score filter: flag any daily return where |return| > 5 sigma (relative to
rolling 252-session average return and standard deviation).
On outlier detection: investigate whether this is a real event (news-driven;
retain) or a data error (e.g., incorrect dividend adjustment; correct).
Data errors confirmed as such: correct in-place; document correction in simulation
artifact; record correction in data quality report.

---

### Extended Reference — Simulation Monitoring Dashboard Specification

SC-21 Health Manager produces real-time monitoring data for the L17 ControlTower
dashboard. The following specifies the complete set of data points published.

**Engine Status Panel:**
- SEHS: current score and tier (color-coded: green/yellow/orange/red)
- SEHS trend: 5-session rolling (arrow indicator: up/flat/down)
- Active simulation runs: count; each with SRI, type, progress percentage,
  estimated completion
- Queued simulations: count; pending queue with priority order
- Failed simulations today: count; list with brief failure reason

**Component Health Panel:**
- 21-component health grid (4 tiers × 5-6 components per row)
- Each component: health score, tier color, last check time
- Components with health changes in the last 30 minutes: highlighted
- Any component below CRITICAL: red alert banner

**Simulation Results Panel:**
- Today's completed simulations: list with SRI, type, SimQS, pass/fail
- SimQS distribution: mini histogram of today's results
- Any quarantined results: highlighted with reason

**Paper Trading Panel:**
- All active paper trading strategies: name, session P&L, cumulative P&L
- Paper trading alerts: any strategies with P&L below WARNING threshold
- Paper trading operational checks: data feed status, order routing status

**Audit and Governance Panel:**
- Hash chain status: last verified time, integrity status
- Governance events today: count by category
- Pending approvals: list with age (how long waiting)
- Override count today

---

### Extended Reference — Simulation-to-Live Gap Tracking

SC-17 Analytics Engine maintains the simulation-to-live gap for every active
strategy. This section provides the detailed specification for gap tracking.

**Gap Definition:**
Simulation-to-Live Gap = Simulated OOS Sharpe (from promotion evidence) minus
Live Sharpe (from L13 LearningSystem, rolling 63-session).

**Acceptable Gaps:**
Gap < 0.20: acceptable; simulation accurately predicts live performance.
Gap 0.20–0.30: monitoring flag; simulation may be slightly optimistic.
Gap 0.30–0.50: investigation trigger; simulation significantly overstates performance.
Gap > 0.50: critical; simulation methodology review required.

**Response by Gap Level:**
Gap < 0.20: no action.
Gap 0.20–0.30: noted in weekly report; monitored.
Gap 0.30–0.50: SC-17 generates investigation report; Operations Lead reviews.
Gap > 0.50: Operations Lead + System Owner review; simulation methodology for
  this strategy type under investigation; no new strategies of this type are
  promoted until the gap cause is identified and resolved.

**Root Causes of Large Gaps:**
1. Survivor bias in historical simulation (not using historical index composition).
2. Transaction costs underestimated (especially for intraday strategies).
3. Slippage model too optimistic for the instrument's actual liquidity.
4. Overfitting in the historical simulation period used for promotion evidence.
5. Market regime shift (strategy was validated in a regime that is no longer current).

**Tracking Period:**
Gap tracking begins when a strategy enters live operation (first live session).
Initial gap: assessed after 30 live sessions. Updated monthly thereafter.
Maximum tracking period: unlimited (gap tracked for lifetime of active strategy).

---

### Extended Reference — Simulation Engine Component Interaction Matrix

The following details which components interact during each major simulation type.

**During SIM-01 (Historical Simulation):**
Primary: SC-06. Secondary: SC-05 (for replay), SC-10 (for fills), SC-15 (metrics),
SC-16 (validation). Supporting: SC-01 (registry), SC-03 (artifacts), SC-20 (audit),
SC-21 (health monitoring).

**During SIM-07 (Monte Carlo):**
Primary: SC-08. Secondary: SC-06 (for per-iteration simulations), SC-07 (for
synthetic series), SC-15 (per-iteration metrics + distribution computation).
Supporting: SC-01, SC-03, SC-20, SC-21.

**During SIM-09 (Stress Testing):**
Primary: SC-09. Secondary: SC-14 (risk rule validation), SC-10 (crisis fill model),
SC-07 (synthetic stress scenarios), SC-15 (stress metrics).
Supporting: SC-01, SC-03, SC-20, SC-21.

**During SIM-02 (Paper Trading):**
Primary: SC-10. Integrates with: L11 OrderManager (PAPER_TRADING flag); L5 StrategyLab
(strategy signal generation). Secondary: SC-15 (rolling performance), SC-21 (monitoring).
Supporting: SC-01, SC-03, SC-20.

**During SIM-15 (Portfolio Simulation):**
Primary: SC-11. Secondary: SC-06 (per-strategy simulations), SC-10 (execution),
SC-15 (portfolio metrics). Supporting: SC-01, SC-03, SC-20, SC-21.

**During SIM-18 (AI Decision Simulation):**
Primary: SC-12. Integrates with: L10 DebateAndDecision (for replay). Secondary:
SC-05 (replay data), SC-15 (decision quality metrics). Supporting: SC-01, SC-20.

**During SIM-19 (Learning Simulation):**
Primary: SC-13. Integrates with: L13 LearningSystem. Secondary: SC-05 (replay data),
SC-15 (learning quality metrics). Supporting: SC-01, SC-20.

---

### Extended Reference — Full Pipeline Configuration Specifications

**SP-01 Historical Replay Pipeline — Execution Configuration:**
Walk-forward parameters: IS=252d, OOS=63d, step=63d, min windows=4.
Transaction cost: brokerage 0.03% per side; STT 0.1% sell; exchange 0.00325%;
SEBI 0.0001%. Slippage: large-cap 0.05%; mid-cap 0.15%; small-cap 0.30%.
Volume participation: max 10% large-cap; 5% mid-cap; 3% small-cap.
Performance metrics computed: all standard metrics plus regime breakdown,
year-by-year performance, maximum consecutive loss sequence, recovery time analysis.

**SP-03 Monte Carlo Pipeline — Execution Configuration:**
Default type: Trade Permutation + Price Perturbation (both run for every strategy).
Iterations: 1,000 for trade permutation; 500 for price perturbation.
Synthetic MC: run on request or for strategies with < 3 years historical data.
Significance test: 10,000-iteration permutation test for p-value computation.
Parallelization: independent iterations distributed across available threads.
Result storage: full distribution (all N iteration results) stored in SC-03;
summary statistics (percentiles) stored in SC-15 result record.

**SP-04 Stress Test Pipeline — Execution Configuration:**
Required scenarios for standard validation: COVID-2020, GFC-2008, CHINA-2015 (minimum 3).
Recommended: all 6 historical scenarios.
Mandatory hypothetical: SCN-HYP-CRASH25PCT-01 (kill switch validation).
Fill model: crisis fill model activated for all historical crash scenarios.
Kill switch simulation: SC-14 validates L9 RiskGuardian behavior in all scenarios.
Special metric: time-to-recovery (sessions from MaxDD trough to full recovery of losses).

**SP-08 Portfolio Pipeline — Execution Configuration:**
Default allocation: Equal Risk Contribution.
Rebalancing: monthly (every 21 sessions).
Correlation calculation: rolling 63-session Pearson correlation of daily returns.
Diversification metric: portfolio MaxDD / average individual strategy MaxDD.
Marginal contribution: Euler decomposition of portfolio variance.

---

## EXTENDED REFERENCE — GOVERNANCE OPERATIONS DETAIL

### Extended Governance Operations

#### Simulation Event Taxonomy

All events in the Simulation Engine are classified using this taxonomy.
The classification determines which governance record is created and the
notification recipients.

**Category A — Simulation Lifecycle Events:**
- A1 Simulation Submitted: new simulation run entered queue.
- A2 Simulation Started: run begins execution.
- A3 Simulation Paused: run paused (user action or resource constraint).
- A4 Simulation Resumed: paused run resumed.
- A5 Simulation Completed: run finishes normally; result record created.
- A6 Simulation Failed: run terminates with error; error record created.
- A7 Simulation Abandoned: run explicitly cancelled by authorized user.
- A8 Simulation Archived: result archived following retention schedule.

**Category B — Quality Events:**
- B1 SimQS Computed: new SimQS score generated for a result.
- B2 SimQS Downgrade: an existing result's SimQS drops on recalculation.
- B3 Result Quarantined: a result is quarantined due to quality concern.
- B4 Result Restored: a quarantined result cleared after investigation.
- B5 SEHS State Change: SEHS crosses a tier boundary.
- B6 Gap Alert: simulation-to-live gap exceeds threshold.

**Category C — Governance Events:**
- C1 Scenario Added: new scenario added to catalog.
- C2 Scenario Modified: existing scenario definition updated.
- C3 Scenario Retired: scenario marked as retired (no longer used for new runs).
- C4 Parameter Override: simulation parameter manually overridden.
- C5 Approval Granted: governance approval given for a simulation or result.
- C6 Approval Denied: governance approval denied; reason recorded.
- C7 Human Override: authorized human override of simulation recommendation.

**Category D — Constitutional Events:**
- D1 Hard Rule Violation Detected: a HARD constitutional rule violation found.
- D2 Soft Rule Violation Detected: a SOFT constitutional rule deviation noted.
- D3 Look-Ahead Contamination: look-ahead bias confirmed in a result.
- D4 Production Data Write Attempt: attempt to write to production data (critical).
- D5 Live Order Attempt: attempt to place a live order from simulation context.

Category D events are the most severe. D4 and D5 events trigger immediate
system halt and escalation to System Owner, regardless of time of day.

---

#### Approval Workflow Detail

**When is approval required?**

1. New standard backtest runs: no approval required (operational simulation).
2. New scenario addition: requires approval from System Owner.
3. Scenario modification: requires approval from two authorized approvers.
4. Human override of simulation result: requires approver + System Owner.
5. Quarantine release: requires Operations Lead + System Owner.
6. Stress scenario library modification: requires System Owner.
7. Constitutional rule change: requires System Owner + senior architect.
8. SimQS threshold change: requires System Owner.
9. WFT parameter change (IS/OOS/step window lengths): requires System Owner.

**Approval Response Time SLAs:**
Standard operational approvals: within 1 business day.
Emergency approvals (blocking a live strategy deployment): within 4 business hours.
System Owner override (blocking a critical safety decision): within 1 business hour.

---

#### Override Review Protocol

When a human override of a simulation result is authorized:

1. Override is requested by the designated operator.
2. The request must include: the simulation run ID; the specific decision being
   overridden; the stated reason for the override; the operator's identification.
3. The approver reviews the reason and the simulation result.
4. If approved: override record is created (immutable); simulation result is tagged
   with override flag; all downstream uses of this result inherit the override flag.
5. All downstream decisions that rely on overridden simulation results are themselves
   flagged as override-dependent.
6. Monthly review: all overrides from the preceding month are reviewed by the
   System Owner. Systematic override patterns (e.g., the same type of result is
   overridden repeatedly) trigger a review of whether the simulation methodology
   has a systematic calibration issue.

**Override Prohibited For:**
- Constitutional HARD rule violations (a result with look-ahead bias cannot be
  overridden — it must be discarded and re-run correctly).
- Kill switch simulation failures (a strategy that fails the kill switch stress test
  cannot receive an override to bypass the promotion gate).

---

#### Compliance Framework

**Data Privacy:**
Simulation artifacts contain no personally identifiable information (PII).
However, they may contain UCIC's proprietary trading strategies and parameters,
which are classified as CONFIDENTIAL.

Artifact access: restricted to authorized IIOS users. No external sharing without
explicit approval from System Owner.

**Audit Requirements:**
All simulation activities are logged and auditable. The audit log is immutable.
Audit log retention: minimum 7 years (matching financial record requirements).

**Conflict of Interest:**
No individual who has a financial interest in a specific strategy outcome may
authorize a simulation override for that strategy's simulation. Operations Lead
escalates any potential conflict of interest to System Owner.

---

### Extended Reference — Detailed Stress Scenario Profiles

The following provides detailed profiles for all stress scenarios in the library.

**SCN-HST-COVID2020-01 — COVID-19 Market Crash (Feb–Mar 2020):**
Period: 2020-02-20 to 2020-03-23. Total NIFTY decline: -38% over 23 sessions.
Maximum single-session decline: -13.15% (March 23, 2020).
INDIA VIX peak: 83.6.
Post-crash recovery: V-shape; full recovery by July 2020 (70 sessions).
Crisis fill model: slippage 6x on sessions with > 5% decline.
Target: validate that the strategy does not generate a maximum drawdown
exceeding 20% in this scenario, and that the kill switch halts trading
before maximum loss exceeds the DD threshold.

**SCN-HST-GFC2008-01 — Global Financial Crisis (Oct–Nov 2008):**
Period: 2008-10-01 to 2008-11-28. Total NIFTY decline: -42% over 40 sessions.
Maximum single-session decline: -11.6% (October 24, 2008 — Black Friday India).
INDIA VIX peak: estimated 68.0 (INDIA VIX launched 2009; GFC proxy used).
Post-crash recovery: slow; full recovery to pre-GFC levels took 3 years.
Crisis fill model: slippage 8x on the two worst sessions.
Target: validates strategy behavior in a prolonged bear market.

**SCN-HST-CHINA2015-01 — China Circuit Breaker Crisis (Jan 2016):**
Period: 2016-01-04 to 2016-01-21. Total NIFTY decline: -8% over 14 sessions.
Characterized by sustained selling pressure without a single catastrophic session.
Crisis fill model: slippage 2x throughout the period.
Target: validates strategy in a sustained but moderate bear environment.

**SCN-HST-DEMONET2016-01 — India Demonetization (Nov 2016):**
Period: 2016-11-08 to 2016-12-01. Total NIFTY decline: -9% following surprise announcement.
Characterized by structural uncertainty; mixed sector impact.
Target: validates that the strategy does not develop excessive exposure to
policy-sensitive sectors (banking, real estate) during uncertainty periods.

**SCN-HST-COVID2ND2021-01 — India Second COVID Wave (Apr–May 2021):**
Period: 2021-04-15 to 2021-05-18. Total NIFTY decline: -9% in 5 weeks.
Healthcare sector significant outperformance.
Target: validates sector rotation behavior and concentration risk.

**SCN-HST-RUSSIAUKR2022-01 — Russia-Ukraine War Market Impact (Feb 2022):**
Period: 2022-02-24 to 2022-03-08. Total NIFTY decline: -6% in 9 sessions.
Commodity sector significant impact; oil price spike.
Target: validates currency and commodity risk behavior.

**SCN-HYP-CRASH25PCT-01 — Hypothetical 25% Single-Month Crash:**
Constructed scenario: NIFTY declines 25% over 22 sessions (1 month).
This is more severe than any observed Indian market crash in recent history.
Purpose: kill switch validation. The strategy MUST trigger L9 RiskGuardian's
kill switch before losses exceed the maximum loss threshold.
HARD gate: any strategy that fails this scenario is NOT eligible for promotion,
regardless of all other simulation results.

**SCN-HYP-RATE-HIKE-200BP-01 — Hypothetical 200bps Rate Hike:**
Constructed scenario: surprise 200bps rate hike by RBI in single announcement.
Sector impact: significant negative for rate-sensitive sectors (banking, real estate,
consumer durables). Positive for financial sector short plays.
Purpose: validates portfolio behavior in a macro rate shock.

**SCN-HYP-CIRCUIT-BREAK-01 — Market Circuit Breaker Simulation:**
Constructed scenario: 10% circuit breaker triggered at market open on Day 1;
45-minute halt; resumed; 15% breaker triggered at Day 2 open; full-day halt.
Purpose: validates order management behavior during circuit breaker halts.
CRITICAL check: all open orders must be correctly handled (not partially filled
against unavailable liquidity) during the breaker period.

**SCN-HYP-LIQUIDITY-CRISIS-01 — Hypothetical Liquidity Crisis:**
Constructed scenario: market-wide liquidity dries up; volume drops to 20% of
normal; bid-ask spreads widen to 5x normal for mid-caps; 10x for small-caps.
Large-cap bid-ask spreads widen to 2x normal.
Purpose: validates that strategies with small- and mid-cap exposure correctly
account for execution cost escalation in illiquid conditions.

---

### Extended Reference — Strategy Type to Simulation Requirements Matrix

Different strategy types require different simulation configurations. This matrix
maps strategy type to the minimum required simulation suite for promotion.

**Type 1 — Daily Bar Equity Momentum:**
Required: SIM-01 (3+ year daily, WFT with 4+ windows), SIM-07 (1,000 iterations),
SIM-09 (6 historical + crash25pct), SIM-15 (equal risk contribution).
Slippage: large-cap 0.05%; mid-cap 0.15%.
Minimum SimQS: 0.55. Minimum WFE: 0.50.

**Type 2 — Intraday Trend Following:**
Required: SIM-01 (1+ year intraday, WFT with 4+ windows), SIM-04 (tick replay
for exit execution validation), SIM-07 (500 iterations), SIM-09 (crash + liquidity).
Slippage: large-cap 0.10% (intraday bid-ask wider than EOD).
Minimum SimQS: 0.60 (higher bar due to transaction cost sensitivity).

**Type 3 — Mean Reversion (Short-term):**
Required: SIM-01 (2+ year daily, WFT), SIM-07 (1,000 iterations), SIM-09 (all),
SIM-12 (decision replay for entry timing sensitivity check).
Special check: mean reversion strategies must show positive OOS performance after
transaction costs; cost-only profitable simulations are rejected.

**Type 4 — Options Strategies:**
Required: SIM-01 (options pricing enabled), SIM-08 (volatility surface evolution
via SC-07 Heston model), SIM-09 (all scenarios with implied vol spike model),
SIM-14 (risk rule validation for delta/gamma/vega limits).
Special requirement: delta neutralization simulation with SC-10.
Minimum SimQS: 0.65 (highest bar due to model complexity).

**Type 5 — Portfolio of Multiple Strategies:**
Required: SIM-15 (mandatory; no portfolio deployment without portfolio simulation),
SIM-07 (correlated Monte Carlo with portfolio return inputs), SIM-09 (all scenarios
at portfolio level). Per-strategy requirements: same as individual strategy type.
Additional metric: portfolio diversification ratio >= 1.2 (portfolio return variance
must be less than 80% of the average individual strategy variance).

**Type 6 — Index / Basket Arbitrage:**
Required: SIM-01 (with both legs simulated simultaneously), SIM-07,
SIM-11 (liquidity stress for both legs), SIM-09.
Special check: both legs must fill within the same simulated session for the
strategy's mean-reversion assumption to hold; if one leg regularly fails to fill,
the strategy's premises are invalidated.

---

### Extended Reference — Multi-Asset Correlation Modeling

SC-11 Portfolio Simulator uses the following approach to model asset correlations.

**Static Correlation:**
Base correlation computed from 252-session rolling Pearson correlation matrix
across all strategies in the portfolio. Used as the default.

**Dynamic Correlation (Stress Regimes):**
During stress simulation, correlations are shifted to reflect the historical
observation that correlations tend to increase (converge toward 1.0) during
market crises ("the correlation curse").

Crisis correlation adjustment:
- All pairwise correlations increased by 0.20 during high-stress scenarios.
- If adjusted correlation exceeds 0.95, capped at 0.95.
- Adjustment magnitude configurable per scenario.

**De Prado's Hierarchical Risk Parity (for advanced allocation):**
SC-11 supports an HRP allocation method using hierarchical clustering of the
correlation matrix. This clusters similar strategies together and avoids
concentration in highly correlated clusters.

HRP steps:
1. Compute correlation matrix.
2. Convert to distance matrix.
3. Hierarchical cluster linkage (Ward's method).
4. Recursive bisection for capital allocation (allocates less capital to larger clusters).

HRP is available as Method 5 (Portfolio Simulator configuration option).

---

### Extended Reference — Learning Simulation Calibration Protocol

Learning simulation (SIM-19) requires periodic recalibration of its attribution
models to ensure that the simulation remains predictive of actual learning behavior.

**Monthly Calibration:**
Each month, SC-13 checks whether the learning predictions from the preceding
month's learning simulations matched actual observed learning outcomes (as
captured by L13 LearningSystem).

Calibration metric: Prediction Accuracy = fraction of attribution predictions
where the predicted top-contributing signal for a session also had the highest
actual live attribution score for that session.

Calibration target: >= 0.65 (65% accuracy). If below target, the attribution
model weights are recalibrated using the preceding 3 months of actual attribution data.

**Quarterly Review:**
Full review of learning simulation methodology. Check for:
1. Has the signal set changed (new signals added, old signals removed)?
2. Has the regime definition changed (new regimes added)?
3. Has the strategy set significantly expanded or contracted?

If any of the above: trigger a full learning simulation model update.

---

### Extended Reference — Simulation Infrastructure Requirements

**Storage Requirements:**
Each simulation run generates artifacts. Storage estimates by simulation type:

| Simulation Type                    | Estimated Artifact Size       |
|------------------------------------|-------------------------------|
| Standard backtest (SIM-01)         | 50KB – 200KB                  |
| Walk-forward simulation (SIM-06)   | 200KB – 1MB                   |
| Monte Carlo (SIM-07, 1000 iter.)   | 5MB – 20MB                    |
| Stress test (SIM-09, all scenarios)| 2MB – 8MB                     |
| Portfolio simulation (SIM-15)      | 200KB – 2MB                   |
| Decision replay (SIM-18, 30 days)  | 100KB – 500KB                 |
| Full promotion evidence dossier    | 15MB – 50MB per strategy      |

Annual growth estimate: approximately 2–5 GB per year of active operations.
Storage is archival: never deleted (GDR-SIM-007).

**Computational Requirements:**
Monte Carlo (1,000 iterations) is the most computationally demanding operation.
Target wall-clock time: < 30 minutes on a 4-core system.
Parallelization: each iteration is independent; parallelized across available CPU cores.

Stress test (all 10 scenarios): target < 90 minutes on a 4-core system.

Historical simulation (SIM-01, 3-year daily): typically < 5 minutes (single-threaded).

---

## DOCUMENT REVISION HISTORY

| Version | Date       | Author        | Summary of Changes                               |
|---------|------------|---------------|--------------------------------------------------|
| 0.1     | 2025-01-01 | IIOS Arch Team| Initial draft — Parts I–IV                       |
| 0.2     | 2025-02-01 | IIOS Arch Team| Added Parts V–VII; first SimQS formula           |
| 0.3     | 2025-03-01 | IIOS Arch Team| Added Parts VIII–X; Governance framework         |
| 0.4     | 2025-04-01 | IIOS Arch Team| Added Supplements A–D; stress scenario library   |
| 0.5     | 2025-05-01 | IIOS Arch Team| Added Supplements E–H; GDRs; worked examples     |
| 0.6     | 2025-06-01 | IIOS Arch Team| Extended component profiles; monitoring dashboard|
| 0.7     | 2025-07-01 | IIOS Arch Team| Strategy matrix; correlation modeling; calbn.    |
| 1.0     | 2025-08-01 | IIOS Arch Team| FINAL — full document review; all sections closed|

---

## SIMULATION ENGINE QUICK-START REFERENCE CARD

This one-page reference summarizes the most-used simulation concepts. Print and
pin at the workstation. For full specifications, refer to the relevant section
of this document.

---

### Simulation Run ID (SRI) Format

    SIM-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}

Example: SIM-HIST-20250801-00000001

---

### Scenario ID Format

    SCN-{TYPE_CODE}-{NAME_SLUG}-{YYYYMMDD}-{SEQ:04d}

Example: SCN-HST-COVID2020-20200101-0001

---

### Minimum Simulation Suite for Strategy Promotion

1. SIM-01 Historical Backtest: SimQS >= 0.55; WFE >= 0.50
2. SIM-07 Monte Carlo: P10 Sharpe >= 0.50; p-value < 0.05
3. SIM-09 Stress Test: SCN-HYP-CRASH25PCT-01 MUST PASS (kill switch fires)
4. SIM-15 Portfolio: portfolio MaxDD <= 15% (if joining multi-strategy portfolio)

All 4 must be documented in the strategy's simulation evidence dossier before
submission to L15 ResearchLab.

---

### SimQS Tiers

| SimQS    | Tier        | Promotion Eligible? |
|----------|-------------|---------------------|
| 0.85+    | EXCELLENT   | Yes                 |
| 0.70–0.84| GOOD        | Yes                 |
| 0.55–0.69| ACCEPTABLE  | Yes (minimum)       |
| 0.35–0.54| MARGINAL    | No                  |
| < 0.35   | FAILED      | No; quarantine      |

---

### SEHS Tiers

| SEHS     | Tier     | Action                            |
|----------|----------|-----------------------------------|
| 0.90+    | OPTIMAL  | All sim types available            |
| 0.75–0.89| NOMINAL  | All sim types; minor limits        |
| 0.55–0.74| DEGRADED | Essential sims only                |
| 0.30–0.54| CRITICAL | Escalate; essential sims only      |
| < 0.30   | FAILED   | Halt all; alert System Owner       |

---

### 5 Things You Must Never Do

1. NEVER run a live order from simulation context.
2. NEVER write to a production data store from simulation context.
3. NEVER use a result with confirmed look-ahead bias.
4. NEVER promote a strategy that failed SCN-HYP-CRASH25PCT-01.
5. NEVER delete simulation artifacts (retention is permanent per GDR-SIM-007).

---

### Transaction Cost Model (Standard)

    Total cost per side = brokerage (0.03%) + STT (0.1% sell) + exchange (0.00325%) + SEBI (0.0001%) + slippage

Slippage: large-cap 0.05% / mid-cap 0.15% / small-cap 0.30%.
Volume participation: max 10% large-cap / 5% mid-cap / 3% small-cap.

---

### Walk-Forward Parameters (Default)

In-Sample: 252 sessions | Out-of-Sample: 63 sessions | Step: 63 sessions | Min Windows: 4

WFE = mean(OOS Sharpe) / mean(IS Sharpe). Target WFE >= 0.50.

---

### Simulation-to-Live Gap Response

| Gap          | Action                                                          |
|--------------|-----------------------------------------------------------------|
| < 0.20       | No action                                                       |
| 0.20 – 0.30  | Monitor; include in weekly report                               |
| 0.30 – 0.50  | Investigation report; Operations Lead review                    |
| > 0.50       | System Owner review; no new promotions of this type until resolved|

---

### Emergency Contacts

Category D constitutional events (live order attempt / production write attempt):
Alert System Owner immediately, regardless of time of day.

SEHS FAILED: Alert Operations Lead; halt new simulation submissions.

---

## FINAL ARCHITECTURAL STATEMENT

The IIOS Simulation Engine is not a passive testing harness. It is the active
institutional quality consciousness of the entire IIOS trading system.

Every strategy that enters live deployment has passed through the simulation
engine's evidence requirements. Every decision system that operates in
production has had its decision logic replayed and verified for determinism.
Every kill switch threshold has been tested against a scenario designed to trigger
it. Every learning update has been traced back to the trades that informed it.

This is the meaning of "simulation primacy": the simulation evidence is the
foundation on which live trading rests. No live deployment exists without it.

The engine achieves this through three design commitments:
- Comprehensive isolation from production systems (no live orders; no production writes).
- Immutable audit chain (no result can be silently altered or deleted).
- Evidence-first culture (promotion gates require documented simulation evidence, not assertion).

Together, these commitments make IIOS a system where confidence in live
performance is earned through systematic evidence, not assumed through optimism.

---

**Document Code:** IIOS-SIM-ENG-ARCH-001
**Series:** IIOS Engine Architecture Series — Document 18 of 18
**Status:** FINAL
**Version:** 1.0

*This document is the definitive architectural specification for the IIOS Simulation Engine.
All implementation decisions within the Simulation Engine must be consistent with
the principles, constraints, and rules defined herein. In the event of a conflict
between this document and any implementation, this document takes precedence.*

---

*End of SIMULATION_ENGINE_ARCHITECTURE.md*

---

## SUPPLEMENT I — SIMULATION ENGINE INTEGRATION PATTERNS

This supplement describes the standard integration patterns between the Simulation
Engine and the other IIOS layers. Each pattern is a named, repeatable interaction
that the system uses during normal operations.

---

### Pattern SIP-01 — Strategy Submission and Validation

**Trigger:** L5 StrategyLab produces a candidate strategy and requests promotion evaluation.

**Sequence:**
1. L5 submits strategy definition to SC-03 Scenario Manager.
2. SC-03 creates a simulation evidence dossier with a new dossier ID.
3. SC-03 schedules the mandatory simulation suite (SIM-01, SIM-07, SIM-09 minimum).
4. SC-06 Historical Engine executes walk-forward simulation; result delivered to SC-15.
5. SC-08 Monte Carlo Engine executes trade permutation; result delivered to SC-15.
6. SC-09 Stress Testing Engine executes standard library; result delivered to SC-14 and SC-15.
7. SC-15 Performance Evaluator computes SimQS for each result; summary delivered to SC-19.
8. SC-19 Governance Manager reviews dossier; applies readiness checklist; assigns Simulation Readiness Certificate if all gates pass.
9. L15 ResearchLab receives the dossier and certificate for promotion decision.

**Outcome:** Promotion evidence dossier in SC-03; Simulation Readiness Certificate in SC-19.

---

### Pattern SIP-02 — Paper Trading Integration

**Trigger:** An approved strategy enters paper trading phase (L5 decision).

**Sequence:**
1. SC-10 Execution Simulator activates paper trading mode for the strategy.
2. L11 OrderManager receives trade signals with PAPER_TRADING=True.
3. L11 routes paper orders to the paper ledger (not the live broker).
4. SC-15 monitors paper trading performance session by session.
5. If paper P&L falls below the WARNING threshold (configurable per strategy),
   SC-21 raises an alert; Operations Lead reviews.
6. After the configured paper trading duration (default 63 sessions),
   SC-19 prepares a paper trading validation report.
7. L5 StrategyLab uses the report for the live deployment decision.

**Invariant:** Paper orders NEVER reach the live broker (HARD rule SC-C-007).

---

### Pattern SIP-03 — Kill Switch Calibration

**Trigger:** L9 RiskGuardian requests kill switch threshold validation
(periodic; or when a threshold is being updated).

**Sequence:**
1. SC-09 Stress Testing Engine runs SCN-HYP-CRASH25PCT-01.
2. During the simulation, SC-14 monitors whether L9 kill switch conditions would trigger.
3. If the kill switch fires before losses reach the MaxDD threshold: PASS.
4. If the kill switch does NOT fire: FAIL — L9 thresholds need recalibration.
5. Result delivered to SC-19; L9 team notified.

**Outcome:** Kill switch validation certificate; or recalibration request.

---

### Pattern SIP-04 — Learning System Replay

**Trigger:** L13 LearningSystem requests a replay of the past N sessions to
re-evaluate attribution.

**Sequence:**
1. SC-05 Replay Engine retrieves archived historical data for the replay period.
2. SC-12 Decision Simulator replays L10 decisions for each session.
3. SC-13 Learning Simulator replays L13 learning updates for each session.
4. SC-13 computes attribution accuracy (actual vs. predicted top signal).
5. If attribution accuracy < 0.65: recalibration alert delivered to L13.
6. Full replay report delivered to L13 and SC-19.

---

### Pattern SIP-05 — Portfolio Rebalancing Evaluation

**Trigger:** L7 RiskControl requests a portfolio simulation before a rebalancing decision.

**Sequence:**
1. SC-11 Portfolio Simulator receives the proposed rebalancing plan.
2. SC-11 simulates the rebalanced portfolio over the last 252 sessions.
3. SC-11 computes marginal risk contribution change from the rebalancing.
4. SC-11 runs the rebalanced portfolio through the stress scenario library.
5. If any new risk concentration is detected: alert raised; L7 reviews.
6. If stress results acceptable: portfolio simulation result delivered to L7 as evidence.

---

### Simulation Engine Operational Health Events

The following events are automatically monitored by SC-21 Health Manager
and reported to L17 ControlTower telemetry at every session boundary.

| Health Event                              | Normal Frequency     | Alert if...                    |
|-------------------------------------------|----------------------|--------------------------------|
| Active simulation count                   | 0–3 (standard hours) | > 10 concurrent                |
| Simulation queue depth                    | 0–5                  | > 20 queued                    |
| Average SimQS for today's results         | >= 0.60              | < 0.50                         |
| SEHS computed                             | Every 30 minutes     | SEHS crosses tier boundary     |
| Hash chain checked                        | Every 4 hours        | Any integrity failure          |
| Gap monitoring check                      | Daily (post-session) | Any gap > 0.30 detected        |
| Artifact storage used vs. quota           | Daily                | > 80% of quota used            |
| Pending governance approvals              | Daily                | Any approval > 2 days old      |
| Last successful audit log entry           | Every 1 hour         | No entry in > 2 hours          |

---

## SUPPLEMENT J — NAMING CONVENTIONS REFERENCE

All identifiers in the Simulation Engine follow strict naming conventions.
This supplement consolidates all naming rules in one place.

| Identifier Type        | Format                                            | Example                              |
|------------------------|---------------------------------------------------|--------------------------------------|
| Simulation Run ID (SRI)| SIM-{TYPE}-{YYYYMMDD}-{SEQ:08d}                   | SIM-HIST-20250801-00000001           |
| Scenario ID            | SCN-{TYPE}-{SLUG}-{YYYYMMDD}-{SEQ:04d}            | SCN-HST-COVID2020-20200101-0001      |
| Component ID           | SC-{NN}                                           | SC-06                                |
| Service ID             | SS-{NN}                                           | SS-03                                |
| Pipeline ID            | SP-{NN}                                           | SP-03                                |
| Lifecycle Stage ID     | SLS-{NN}                                          | SLS-07                               |
| Quality Dimension ID   | SQD-{NN}                                          | SQD-01                               |
| Anti-Pattern ID        | SMAP-{NN}                                         | SMAP-03                              |
| GDR ID                 | GDR-SIM-{NNN}                                     | GDR-SIM-004                          |
| Error Code             | SE-{NNN}                                          | SE-007                               |
| Dossier ID             | DOS-{STRATEGY_CODE}-{YYYYMMDD}                    | DOS-RSI-MOM-20250801                 |
| Certificate ID         | CERT-SIM-{STRATEGY_CODE}-{YYYYMMDD}               | CERT-SIM-RSI-MOM-20250801            |
| Override Record ID     | OVR-{SRI}-{YYYYMMDD}-{SEQ:04d}                    | OVR-SIM-HIST-20250801-00000001-0001  |

---

*End of Supplement J — Naming Conventions Reference*
