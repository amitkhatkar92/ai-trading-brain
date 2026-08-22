# STRATEGY ENGINE ARCHITECTURE

**Document Code:** IIOS-STR-ENG-ARCH-001
**System:** Investment Intelligence Operating System (IIOS)
**Version:** 1.0
**Date:** 2026-07-03
**Status:** COMPLETE
**Classification:** IIOS Internal Architecture Reference
**Scope:** Strategy Engine — complete lifecycle management of all IIOS investment strategies

---

## IIOS STACK — STRATEGY ENGINE INTEGRATION

`
IIOS 17-LAYER ARCHITECTURE — STRATEGY ENGINE POSITION
═══════════════════════════════════════════════════════

Layer  1  GlobalIntelligence     → overnight global context (S&P, Nikkei, bonds, FX)
Layer  2  MarketIntelligence     → NIFTY/BANKNIFTY regime, sector, liquidity, events
Layer  3  MetaLearning           → k-NN strategy weight predictor
Layer  4  OpportunityEngine      → equity scanner, options, arbitrage
Layer  5  StrategyLab            ★ STRATEGY ENGINE LAYER ★
           ├── MetaStrategyController
           ├── Strategy Registry + Catalog
           ├── Strategy Builder + Validator
           ├── Backtesting + Simulation
           ├── Optimization + Evolution
           └── Strategy Governance
Layer  6  CapitalRiskEngine      → position sizing per strategy budget
Layer  7  RiskControl            → RiskManagerAI, PortfolioAllocation, StressTest
Layer  8  MarketSimulation       → Monte Carlo, 14 scenarios
Layer  9  RiskGuardian           → final Kill Switch (VIX>45, daily loss>2%)
Layer 10  DebateAndDecision      → 5-agent debate, DecisionEngine (threshold 6.5)
Layer 11  ExecutionEngine        → OrderManager → ZerodhaBroker (sim mode)
Layer 12  TradeMonitoring        → TradeMonitor, StrategyHealthMonitor
Layer 13  LearningSystem         → LearningEngine, StrategyPerformanceTracker
Layer 14  PerformanceAnalytics   → DrawdownAnalyzer, WalkForwardTester
Layer 15  ResearchLab            → promotion gates: WinRate≥50%, Sharpe>0.8, MaxDD<15%
Layer 16  ValidationEngine       → 6-stage: Backtest→WFT→CrossMarket→MC→Sensitivity→Regime
Layer 17  ControlTower           → SQLite telemetry, Streamlit dashboard, EventBus
`

---

## INFORMATION FLOW DIAGRAM

`
STRATEGY ENGINE — INFORMATION FLOW
════════════════════════════════════

INPUTS TO STRATEGY ENGINE
════════════════════════════════════
L1  GlobalIntelligence ──────────── global macro context for strategy regime calibration
L2  MarketIntelligence ──────────── regime signal, sector health, liquidity context
L3  MetaLearning ────────────────── strategy weight predictions per regime
L4  OpportunityEngine ───────────── candidate instruments and opportunities
L13 LearningEngine ──────────────── outcome feedback → strategy parameter refinement
L14 PerformanceAnalytics ────────── drawdown analysis, walk-forward test results
L15 ResearchLab ─────────────────── strategy promotion decisions (WinRate/Sharpe/MaxDD gates)
L16 ValidationEngine ────────────── 6-stage validation pipeline results
Risk Engine (L6, L7, L8, L9) ───── risk budgets, limits, stress test results
Portfolio Engine ────────────────── NAV, allocation budget, constraint set
Knowledge Architecture ──────────── structured market knowledge base
Observation Architecture ────────── historical and real-time observations
Decision Engine (L10) ───────────── feedback on strategy signal quality

OUTPUTS FROM STRATEGY ENGINE
════════════════════════════════════
→ Decision Engine (L10)   validated, governed strategy signals and recommendations
→ Risk Engine (L6/L7)     strategy risk profile, parameter set, historical performance
→ Portfolio Engine        strategy metadata, allocation requirements, constraint needs
→ Learning Engine (L13)   strategy performance attribution for model updates
→ ControlTower (L17)      strategy health dashboard, governance status, version info
→ Telegram Bot            strategy lifecycle notifications (activation, retirement, alerts)
`

---

## TABLE OF CONTENTS

`
PART I    — Strategy Philosophy (Definitions, Types, Frameworks)
PART II   — Strategy Taxonomy (24 strategy categories)
PART III  — Core Components (SC-01 through SC-20)
PART IV   — Strategy Lifecycle (17 stages; state machine; diagrams)
PART V    — Strategy Services (15 services)
PART VI   — Strategy Processing Pipelines (11 pipelines)
PART VII  — Strategy Quality Framework (13 SQD dimensions)
PART VIII — Strategy Governance
PART IX   — Strategy Constitution (110+ rules, 15 categories)
PART X    — Strategy Readiness Checklist

SUPPLEMENT A — Strategy Taxonomy Reference
SUPPLEMENT B — Evaluation Framework
SUPPLEMENT C — Optimization Techniques
SUPPLEMENT D — Version Management
SUPPLEMENT E — Anti-Patterns
SUPPLEMENT F — Operational Runbook
SUPPLEMENT G — Governing Design Records (GDR-STR-001 through GDR-STR-008)
SUPPLEMENT H — Comprehensive Glossary (70+ terms)

APPENDIX — Worked Examples (6)
DOCUMENT SUMMARY
`

---

## PART I — STRATEGY PHILOSOPHY

### 1.0 The Nature of Strategy in an AI Trading System

A strategy is an organized, reproducible method for generating investment decisions. In a sophisticated AI trading system like IIOS, "strategy" occupies a precise position in a hierarchy of abstractions — from raw observation at the bottom to portfolio construction at the top. Understanding this hierarchy is essential to understanding what the Strategy Engine is and is not responsible for.

The central discipline of IIOS is that each layer in the stack handles one level of abstraction. The Strategy Engine is responsible for the strategy level — not lower (not observation, not signal) and not higher (not portfolio allocation, not execution). This boundary discipline is what makes the system comprehensible and improvable.

---

### 1.1 The Twenty-Level Conceptual Hierarchy

**Level 1 — Observation**

An observation is a raw fact about the world at a specific point in time. Observations are atomic, immutable, and uninterpreted. "NIFTY50 closed at 22,405.35 on 2025-11-12 at 15:30 IST" is an observation. Observations have no meaning until they are interpreted. The Observation Architecture manages all observations.

**Level 2 — Measurement**

A measurement is an observation that has been placed on a scale with defined units and a reference point. Price is a measurement. Volume in shares is a measurement. Return percentage is a measurement. Measurements enable comparison across time and instruments.

**Level 3 — Data**

Data is a collection of related measurements organized for storage and retrieval. Raw OHLCV records are data. Data has structure but not yet meaning in a trading context.

**Level 4 — Indicator**

An indicator is a mathematical transformation of raw data designed to expose a specific market characteristic. Indicators are computationally deterministic: the same data always produces the same indicator value. Examples: 20-day Simple Moving Average, 14-day RSI, Bollinger Bands, ATR. Indicators are tools for signal generation; they are not signals themselves.

**Level 5 — Feature**

A feature is an indicator or a derived combination of indicators prepared for consumption by a statistical or machine-learning model. Features are normalized, scaled, and selected for their predictive relationship with future price behavior. The distinction between indicator and feature is the intentional design for machine consumption.

**Level 6 — Signal**

A signal is a directional conclusion derived from one or more indicators or features. A signal is interpreted: it carries a direction (BUY, SELL, NEUTRAL) and typically a confidence level. "RSI < 30 AND price above 200-day MA → BUY signal" is a signal generation rule. A signal is the output of a rule applied to indicators.

**Level 7 — Rule**

A rule is a conditional statement that maps indicator or feature conditions to a signal. Rules are the atomic decision units of a strategy. A single rule is not a strategy — it is one building block. "If 5-day EMA crosses above 20-day EMA, generate BUY signal" is a rule. Rules are explicit, auditable, and testable in isolation.

**Level 8 — Hypothesis**

A hypothesis is a testable proposition about market behavior that, if confirmed, would justify a specific trading strategy. "Indian large-cap stocks that have outperformed NIFTY50 over the prior 3 months tend to continue outperforming over the following month" is a hypothesis. A hypothesis is the intellectual foundation of a strategy. Before a strategy is built, the hypothesis must be stated. After testing, the hypothesis is either supported or refuted.

**Level 9 — Idea**

An idea is a pre-hypothesis intuition about a market inefficiency or behavioral pattern. Ideas are the starting point of strategy development. "Stocks that gap up significantly on earnings with high volume tend to continue higher" is an idea. Ideas must be converted into testable hypotheses before they can become strategies.

**Level 10 — Strategy**

A strategy is a complete, testable, self-contained investment methodology. A strategy specifies: the universe of instruments it applies to; the signal generation rules; the entry conditions; the exit conditions (profit target, stop-loss, time-based); the position sizing method; the regime conditions under which it is active; and the performance expectations. A strategy can be run independently; it does not depend on other strategies for its core logic.

**Level 11 — Model**

A model is a mathematical or statistical representation of market behavior used within a strategy to generate signals or predictions. A model may be an equation (linear regression), a statistical process (ARIMA), or a machine learning model (random forest). A model is a component of a strategy's signal generation apparatus.

**Level 12 — System**

A system is a collection of strategies that are managed together under a unified governance and risk framework. The term "trading system" refers to the complete IIOS operational platform. A system manages multiple strategies simultaneously, with rules for how they interact and compete for capital.

**Level 13 — Optimization**

Optimization is the process of searching the parameter space of a strategy to find the combination that maximizes a defined objective function (e.g., Sharpe ratio, Calmar ratio, or expected return) subject to constraints (e.g., minimum trade frequency, maximum drawdown). Optimization is a component of the Strategy Engine, not the strategy itself.

**Level 14 — Learning**

Learning is the ongoing process of updating strategy parameters or model weights based on observed outcomes. A strategy that learns improves its performance over time as it processes more data. Learning is provided to the Strategy Engine by the Learning Engine (L13) and incorporated through the strategy evolution pipeline.

**Level 15 — Evolution**

Evolution is a higher-order form of learning where the strategy's structure, not just its parameters, changes over time. A strategy evolves when its rules, signal logic, or architectural structure is modified based on sustained performance analysis. Evolution is governed — it requires validation, backtesting, and approval before the evolved version is activated.

**Level 16 — Prediction**

A prediction is a forward-looking output: a directional or quantitative forecast about future price behavior or signal quality. The Prediction Engine (L15 in IIOS) produces predictions; strategies consume predictions as inputs to their signal generation logic.

**Level 17 — Decision**

A decision is the resolved choice to initiate, maintain, or close a position. Decisions are produced by the Decision Engine (L10) based on strategy signals, risk assessments, and portfolio state. Strategies produce signals; the Decision Engine makes decisions. This separation is architecturally critical.

**Level 18 — Execution**

Execution is the market-facing activity of converting a decision into an order and submitting it to the exchange. The Execution Engine (L11) handles execution. Strategies have no knowledge of execution.

**Level 19 — Portfolio**

A portfolio is the collection of all current positions and their associated attributes. Portfolio construction is the discipline of combining multiple strategy outputs into a coherent, risk-managed whole. The Portfolio Engine manages portfolio state. The Strategy Engine informs portfolio construction through its allocation requirements and risk profile descriptions.

**Level 20 — Investment Intelligence**

Investment Intelligence is the highest level: the integrated, continuously improving capability to generate risk-adjusted returns from financial markets. IIOS as a whole represents Investment Intelligence — the combination of all 20 levels working together.

---

### 1.2 Strategy Types — Deep Classification

**Rule-Based Strategy**

A rule-based strategy uses explicit, human-defined conditional logic to generate signals. Rules are deterministic: given the same inputs, the same rules always produce the same outputs. Rule-based strategies are fully explainable — every signal can be traced to a specific rule condition. They are easy to audit and test, but limited by the quality of the rules the designer specifies.

*IIOS Example:* "Enter LONG when price breaks above the 20-day high with volume > 1.5x average. Exit when price falls below the 10-day low or reaches 2x ATR profit target."

**Statistical Strategy**

A statistical strategy uses probability and statistics to identify instruments or conditions where expected returns are favorable. Statistical strategies rely on historical distributions, mean-reversion principles, or correlation structures. They require sufficient historical data and assume that statistical patterns persist.

*IIOS Example:* "Identify stocks with RSI < 25 (oversold by statistical norm) and historical 5-day return after RSI < 25 crossing is positive 73% of the time. Enter on next open."

**Quantitative Strategy**

A quantitative strategy uses mathematical models to generate signals. All quantitative strategies are rule-based at some level, but the distinguishing feature is the heavy use of mathematical formulas, factors, and optimization. Quantitative strategies are typically multi-factor and rely on formal hypothesis testing.

*IIOS Example:* "Compute 5-factor momentum score combining price momentum (3-month), earnings revision momentum, volume growth, relative strength vs sector, and volatility-adjusted return. Enter long top quartile; ignore bottom quartile."

**Machine Learning Strategy**

A machine learning strategy uses ML models (regression, classification, ensemble methods) trained on historical data to generate signals. The strategy's signal logic is not explicitly programmed — it is learned from data. ML strategies require careful attention to overfitting; their performance must be validated on out-of-sample data.

*IIOS Example:* "Random forest classifier trained on 40 technical and fundamental features. Predicts 5-day forward return classification: STRONG_UP, UP, NEUTRAL, DOWN. Enter LONG on STRONG_UP signal with confidence > 0.70."

**Deep Learning Strategy**

A deep learning strategy uses neural networks (LSTM, transformer, convolutional networks) to detect complex, non-linear patterns in market data. Deep learning strategies can process unstructured data (news text, social sentiment) in addition to price data. They require large datasets and significant compute.

**Hybrid Strategy**

A hybrid strategy combines rule-based logic with statistical or ML components. The rules provide structure and explainability; the statistical or ML components provide adaptability. Most mature IIOS strategies are hybrids — they have explicit entry/exit rules but use ML-based regime detection or signal weighting.

**Adaptive Strategy**

An adaptive strategy changes its behavior based on current market conditions, typically by adjusting parameters (e.g., lookback period, stop-loss width) in response to volatility regime or trend strength. Adaptive strategies do not change their core logic — only their parameters.

**Self-Learning Strategy**

A self-learning strategy continuously updates its model weights or parameters based on recent performance, without requiring a separate learning cycle. The strategy learns online. Self-learning strategies must be governed carefully — online learning without oversight can cause parameter drift and strategy degradation.

**Multi-Factor Strategy**

A multi-factor strategy combines multiple independent signals or factors into a composite score. The signals may be technical (momentum, volatility), fundamental (earnings growth, valuation), or macro (regime, sector health). The composite score is more robust than any single factor because uncorrelated factors provide diversification within the strategy.

**Multi-Timeframe Strategy**

A multi-timeframe strategy analyzes the market at multiple time resolutions simultaneously — for example, confirming a daily trend with a weekly trend before entering on an intraday trigger. Multi-timeframe analysis reduces false signals by requiring alignment across timeframes.

**Multi-Asset Strategy**

A multi-asset strategy trades across more than one asset class (e.g., equities and index futures simultaneously). Multi-asset strategies can exploit cross-asset relationships (equities and VIX correlation, sector rotation between defensive and cyclical sectors).

**Multi-Strategy Framework**

A multi-strategy framework is not a single strategy but an architecture for combining multiple strategies into a coherent portfolio. The Strategy Engine is itself a multi-strategy framework — it manages multiple concurrent strategies with defined rules for capital allocation, conflict resolution, and performance attribution.

---

## PART II — STRATEGY TAXONOMY

### 2.0 Taxonomy Design Philosophy

The Strategy Taxonomy provides the controlled vocabulary for all IIOS strategy types. Every strategy registered in the Strategy Engine is assigned a primary taxonomy classification and optional secondary classifications. The taxonomy drives: capital allocation rules (different strategy types have different risk profiles); regime compatibility mapping (which strategy types work in which market regimes); correlation management (strategies of the same type tend to be correlated); and governance review scheduling.

Strategy types are organized into 24 categories. Each category has a defined code (ST-XX), description, typical signal characteristics, regime suitability, and IIOS deployment status.

---

### ST-01 — Trend Following

**Definition:** Trend following strategies identify markets that are moving directionally and enter in the direction of the trend, holding positions as long as the trend continues. The core hypothesis is market momentum persistence: a trend in motion tends to stay in motion longer than random-walk models predict.

**Signal Characteristics:** Entry after trend confirmation (not prediction); wider stops to survive pullbacks; exit on trend reversal signal.

**Typical Metrics:** Win rate often below 50% but payoff ratio > 2.0; right-skewed return distribution; works across multiple timeframes.

**Regime Suitability:** TRENDING_UP (strong), TRENDING_DOWN (short side), VOLATILE (reduced size). Poor in SIDEWAYS regimes.

**IIOS Status:** Primary — core strategy type for NIFTY and large-cap equities.

---

### ST-02 — Momentum

**Definition:** Momentum strategies rank instruments by recent price performance and invest in relative winners while avoiding (or shorting) relative losers. Unlike trend following (which is absolute), momentum is relative: it is about whether an instrument is outperforming its peers, not merely whether it is going up.

**Signal Characteristics:** Lookback period typically 1–12 months with 1-month exclusion (momentum crash avoidance); cross-sectional ranking; rebalancing frequency driven by momentum decay.

**Types:** Price momentum; earnings momentum; estimate revision momentum; fundamental momentum (revenue growth, margin expansion).

**Regime Suitability:** Performs in trending regimes; subject to momentum crashes during sharp reversals (high VIX events).

**IIOS Status:** Primary — the primary alpha source for IIOS equity strategies.

---

### ST-03 — Mean Reversion

**Definition:** Mean reversion strategies bet that prices, indicators, or spreads that have deviated significantly from their historical mean will revert toward that mean. The core hypothesis is that short-term extremes are unsustainable.

**Signal Characteristics:** Entry at extremes (RSI < 25 or > 75; price > 2 standard deviations from moving average); tight stops; multiple small wins; risk of large loss if mean reversion fails.

**Typical Metrics:** High win rate (60–70%); low payoff ratio; left-skewed return distribution. Mean reversion strategies fail catastrophically when a trend breaks out of its historical range.

**Regime Suitability:** SIDEWAYS (strong), VOLATILE (reduced); avoids TRENDING regimes.

**IIOS Status:** Supported — particularly for intraday strategies on liquid large-caps.

---

### ST-04 — Breakout

**Definition:** Breakout strategies enter positions when price breaks through a defined support or resistance level, betting that the breakout signals the start of a new directional move.

**Signal Characteristics:** Entry on close above resistance or below support; volume confirmation often required; false breakout is the primary risk.

**Regime Suitability:** Best in TRENDING and transition regimes; poor in SIDEWAYS where breakouts fail frequently.

**IIOS Status:** Primary — particularly effective for NIFTY futures breakouts at key technical levels.

---

### ST-05 — Pullback

**Definition:** Pullback strategies enter in the direction of the primary trend during temporary retracements, betting that the trend will resume. The entry is better-priced than a breakout entry, with tighter stop placement.

**Signal Characteristics:** Confirm primary trend; wait for retracement to defined level (Fibonacci, moving average, ATR-based); enter on reversal candlestick pattern or indicator divergence.

**Regime Suitability:** TRENDING regimes (primary requirement); requires trend to be intact at the time of pullback.

**IIOS Status:** Primary — combines well with Momentum to provide better entry prices.

---

### ST-06 — Volatility Strategy

**Definition:** Volatility strategies profit from changes in implied or realized volatility, independent of price direction. These include volatility expansion plays (enter before expected volatility spike) and volatility mean reversion (enter when volatility is extreme and expected to normalize).

**Signal Characteristics:** Relies on VIX analysis, India VIX, options implied volatility, ATR levels relative to historical norm.

**IIOS Status:** Supported — primarily used as a risk management overlay and for options strategies.

---

### ST-07 — Market Neutral

**Definition:** Market neutral strategies aim to eliminate market beta exposure by holding offsetting long and short positions of roughly equal market value. The return comes entirely from the spread between the long and short sides.

**Signal Characteristics:** Equal capital in longs and shorts; portfolio beta target near zero; profit from relative performance.

**IIOS Status:** Planned — requires reliable short-selling capability, which depends on IIOS margin account setup.

---

### ST-08 — Statistical Arbitrage

**Definition:** Statistical arbitrage (stat arb) identifies mispricings between related instruments using statistical models, betting that the mispricing will correct. Unlike pure arbitrage, stat arb involves residual risk and requires holding periods.

**Signal Characteristics:** Typically mean-reverting spreads between correlated instruments; entry when spread exceeds X standard deviations; exit at mean.

**IIOS Status:** Planned — pairs trading (ST-09) is the primary implementation pathway.

---

### ST-09 — Pairs Trading

**Definition:** Pairs trading is a form of statistical arbitrage where two historically correlated stocks are traded as a pair: long the underperformer, short the outperformer, betting on convergence.

**Signal Characteristics:** Cointegration test to confirm long-term relationship; z-score of spread for entry/exit; pair correlation monitored for structural breaks.

**IIOS Status:** Planned — target deployment when IIOS has reliable short capability.

---

### ST-10 — Sector Rotation

**Definition:** Sector rotation strategies allocate capital to sectors that are expected to outperform given the current economic regime or market cycle phase, rotating out of sectors expected to underperform.

**Signal Characteristics:** Relative strength of sectors vs benchmark; economic phase indicators; earnings growth trends by sector.

**Regime Suitability:** Works across all regimes; the rotation targets change by regime.

**IIOS Status:** Primary — sector allocation is a key component of IIOS portfolio construction.

---

### ST-11 — Factor Investing

**Definition:** Factor investing systematically tilts the portfolio toward well-documented risk premia or market anomalies: value, momentum, quality, low volatility, size. Each factor represents a systematic, persistent source of excess return.

**Signal Characteristics:** Multi-factor scoring; long-term holding periods; rebalancing at defined intervals; factor exposures monitored against targets.

**IIOS Status:** Supported — multi-factor scoring informs strategy selection and weighting.

---

### ST-12 — Growth Strategy

**Definition:** Growth strategies target companies with above-average earnings growth rates, revenue expansion, and improving margins, betting that high growth justifies premium valuations.

**Signal Characteristics:** EPS growth acceleration; revenue growth trend; margin improvement; PEG ratio; analyst estimate revisions.

**IIOS Status:** Future — requires fundamental data integration beyond current IIOS scope.

---

### ST-13 — Value Strategy

**Definition:** Value strategies target companies trading below their intrinsic value as measured by fundamental metrics (P/E, P/B, P/FCF), betting that the market will eventually correct the mispricing.

**IIOS Status:** Future — requires fundamental data and long-term holding horizon.

---

### ST-14 — Dividend Strategy

**Definition:** Dividend strategies target high-dividend-yield stocks with sustainable payout ratios, combining income generation with capital appreciation.

**IIOS Status:** Future.

---

### ST-15 — Income Strategy

**Definition:** Income strategies generate regular cash flows through dividends, option premium selling, or fixed income instruments.

**IIOS Status:** Future — option premium selling (covered calls, cash-secured puts) is a planned capability.

---

### ST-16 — Macro Strategy

**Definition:** Macro strategies make investment decisions based on analysis of macroeconomic variables: GDP growth, inflation, interest rates, currency movements, geopolitical events. Global macro strategies trade across asset classes.

**Signal Characteristics:** Top-down analysis; low trade frequency; large position sizes; held for weeks to months.

**IIOS Status:** Supported as overlay — GlobalIntelligence (L1) provides macro context that modifies strategy confidence levels.

---

### ST-17 — Event-Driven Strategy

**Definition:** Event-driven strategies profit from corporate events: earnings announcements, mergers and acquisitions, restructurings, regulatory changes, index inclusions/exclusions.

**Signal Characteristics:** Calendar-driven; pre-event positioning; post-event reaction play.

**IIOS Status:** Supported — earnings event analysis is a planned capability.

---

### ST-18 — Sentiment Strategy

**Definition:** Sentiment strategies trade based on the balance of bullish vs bearish investor sentiment, betting on mean reversion when sentiment reaches extremes.

**Signal Characteristics:** Put/call ratio; FII/DII flow data; options implied sentiment; news sentiment.

**IIOS Status:** Supported — sentiment signals from GlobalIntelligence and MarketIntelligence are used as modifiers.

---

### ST-19 — News-Based Strategy

**Definition:** News-based strategies use NLP analysis of news, filings, and announcements to generate trading signals.

**IIOS Status:** Planned — requires NLP integration with news data feeds.

---

### ST-20 — AI-Generated Strategy

**Definition:** AI-generated strategies are designed, optimized, and evolved autonomously by the IIOS AI system. The human defines the objective and constraints; the AI explores the strategy space. AI-generated strategies must still pass all governance gates.

**IIOS Status:** Primary — the Strategy Evolution Engine generates candidate strategies autonomously within defined bounds.

---

### ST-21 — Hybrid Strategy

**Definition:** A hybrid strategy combines components from multiple strategy types. Most mature IIOS strategies are hybrid: they have rule-based structure with ML-based signal weighting and adaptive parameters.

**IIOS Status:** Primary — the target state for all mature IIOS strategies.

---

### ST-22 — Adaptive Strategy

**Definition:** An adaptive strategy continuously adjusts its parameters (lookback periods, thresholds, stop distances) based on current market conditions (volatility regime, trend strength) without changing its core logic.

**IIOS Status:** Primary — regime-adaptive parameter adjustment is built into all IIOS strategy designs.

---

### ST-23 — Portfolio-Level Strategy

**Definition:** A portfolio-level strategy makes decisions about capital allocation across existing strategies rather than generating signals for individual instruments. Portfolio-level strategies manage strategy weights, cash levels, and concentration.

**IIOS Status:** Primary — the Allocation Engine in the Portfolio Engine implements portfolio-level strategy logic.

---

### ST-24 — Execution Strategy

**Definition:** An execution strategy specifies how orders are submitted to minimize market impact and transaction costs. Execution strategies include TWAP, VWAP, and liquidity-seeking algorithms.

**IIOS Status:** Planned — current IIOS uses simple market and limit orders.

---

### 2.1 Taxonomy Summary Table

| Code  | Name                   | Primary Signal      | Regime Fit          | IIOS Status |
|-------|------------------------|---------------------|---------------------|-------------|
| ST-01 | Trend Following        | Direction           | TRENDING            | Primary     |
| ST-02 | Momentum               | Relative strength   | TRENDING            | Primary     |
| ST-03 | Mean Reversion         | Extreme deviation   | SIDEWAYS            | Supported   |
| ST-04 | Breakout               | Level violation     | TRENDING+Transition | Primary     |
| ST-05 | Pullback               | Trend retracement   | TRENDING            | Primary     |
| ST-06 | Volatility             | Vol regime change   | VOLATILE            | Supported   |
| ST-07 | Market Neutral         | Relative value      | Any                 | Planned     |
| ST-08 | Statistical Arb        | Statistical spread  | SIDEWAYS            | Planned     |
| ST-09 | Pairs Trading          | Cointegrated spread | SIDEWAYS            | Planned     |
| ST-10 | Sector Rotation        | Sector strength     | Any                 | Primary     |
| ST-11 | Factor Investing       | Multi-factor score  | Any                 | Supported   |
| ST-12 | Growth                 | EPS acceleration    | TRENDING_UP         | Future      |
| ST-13 | Value                  | Intrinsic discount  | SIDEWAYS/DOWN       | Future      |
| ST-14 | Dividend               | Yield + payout      | Any                 | Future      |
| ST-15 | Income                 | Cash flow yield     | Any                 | Future      |
| ST-16 | Macro                  | Economic regime     | Any (overlay)       | Supported   |
| ST-17 | Event-Driven           | Corporate events    | Any                 | Supported   |
| ST-18 | Sentiment              | Investor psychology | Extreme sentiment   | Supported   |
| ST-19 | News-Based             | NLP news signal     | Any                 | Planned     |
| ST-20 | AI-Generated           | AI exploration      | Any                 | Primary     |
| ST-21 | Hybrid                 | Multi-component     | Adaptive            | Primary     |
| ST-22 | Adaptive               | Regime-calibrated   | Any                 | Primary     |
| ST-23 | Portfolio-Level        | Allocation signal   | Any                 | Primary     |
| ST-24 | Execution              | Cost minimization   | Any                 | Planned     |

---

## PART III — CORE COMPONENTS

### 3.0 Component Architecture Overview

The Strategy Engine is implemented through twenty core components organized into four tiers:

**Tier 1 — Identity and Registry (SC-01 to SC-03):** Components that define, catalog, and store strategy definitions.

**Tier 2 — Development and Validation (SC-04 to SC-09):** Components that build, validate, optimize, simulate, evaluate, and rank strategies.

**Tier 3 — Selection and Evolution (SC-10 to SC-14):** Components that select active strategies, manage evolution, monitor health, and govern retirement.

**Tier 4 — Operations (SC-15 to SC-20):** Components that provide monitoring, governance, audit, analytics, health management, and reporting.

---

`
COMPONENT TIER DIAGRAM
══════════════════════

Tier 1: IDENTITY
SC-01 Strategy Registry     SC-02 Strategy Catalog     SC-03 Strategy Repository

Tier 2: DEVELOPMENT
SC-04 Strategy Builder      SC-05 Strategy Validator   SC-06 Strategy Optimizer
SC-07 Strategy Simulator    SC-08 Strategy Evaluator   SC-09 Strategy Ranking Engine

Tier 3: SELECTION AND EVOLUTION
SC-10 Strategy Selection Engine     SC-11 Strategy Evolution Engine
SC-12 Strategy Retirement Manager   SC-13 Strategy Monitoring Engine

Tier 4: OPERATIONS
SC-14 Strategy Governance Manager   SC-15 Strategy Audit Manager
SC-16 Strategy Analytics Engine     SC-17 Strategy Health Manager
SC-18 Strategy Reporting Manager    SC-19 Strategy Version Manager
SC-20 Strategy Metadata Manager
`

---

### SC-01 — Strategy Registry

**Purpose:** The Strategy Registry is the authoritative master record of every strategy known to IIOS — past, present, and in development. The Registry is the single source of truth for strategy identity. No strategy operates within IIOS without a Registry record.

**Responsibilities:**
- Assign and maintain unique Strategy IDs for all strategies
- Store strategy status (DRAFT, IN_VALIDATION, APPROVED, ACTIVE, SUSPENDED, RETIRED, ARCHIVED)
- Track strategy version history (all versions of every strategy)
- Maintain the canonical strategy definition for each active version
- Support point-in-time reconstruction (what strategy was active on date X?)
- Enforce strategy ID uniqueness across the full strategy lifecycle

**Inputs:** Strategy creation requests from SC-04 Builder; status change requests from SC-12 Retirement Manager and SC-10 Selection Engine; version updates from SC-19 Version Manager.

**Outputs:** Strategy identity records to all components; strategy list to SC-10 Selection Engine; strategy history to SC-15 Audit Manager; strategy metadata to L17 ControlTower.

**Strategy ID Format:** STR-{TYPE_CODE}-{YYYYMMDD}-{SEQ:06d}
Example: STR-MOMENTUM-20251112-000001

**Status Reference Table:**

| Status        | Description                                            |
|---------------|--------------------------------------------------------|
| DRAFT         | Under development; not yet submitted for validation    |
| IN_VALIDATION | Submitted to SC-05 Validator; validation in progress  |
| APPROVED      | Passed all validation; awaiting activation decision   |
| ACTIVE        | Currently deployed; generating signals                 |
| SUSPENDED     | Temporarily halted (Kill Switch, performance issue)    |
| DEPRECATED    | Superseded by newer version; winding down             |
| RETIRED       | Permanently deactivated; no longer generating signals  |
| ARCHIVED      | Historical record only; all records preserved         |

**Dependencies:** SC-19 Version Manager; SC-20 Metadata Manager; SC-15 Audit Manager.

**Failure Mode:** Registry unavailable → no strategy activations or deactivations possible; currently active strategies continue with cached state; human review required.

**Recovery:** Load Registry from persistent storage; validate consistency with active strategy list; reconcile any discrepancies.

---

### SC-02 — Strategy Catalog

**Purpose:** The Strategy Catalog maintains the controlled vocabulary of strategy types, families, and classifications. While the Registry tracks individual strategy instances, the Catalog manages the taxonomy.

**Responsibilities:**
- Maintain all 24 strategy type definitions (ST-01 through ST-24)
- Manage strategy family groupings (e.g., Momentum family = ST-01, ST-02, ST-05)
- Provide taxonomy queries: which strategies belong to this type? what is the current primary strategy for TRENDING_UP regime?
- Enforce taxonomy version discipline: taxonomy changes require governance approval
- Map strategy types to regime compatibility rules
- Map strategy types to typical risk profiles (expected win rate, payoff ratio, drawdown)

**Inputs:** Taxonomy update requests (governance-approved only); strategy type queries from all components.

**Outputs:** Strategy type definitions; type-to-regime mappings; family groupings; risk profile templates.

**Dependencies:** SC-01 Registry; SC-14 Governance Manager.

**Engineering Notes:** The Catalog is read-mostly; writes are rare (taxonomy changes). It is cached aggressively and rarely the bottleneck.

---

### SC-03 — Strategy Repository

**Purpose:** The Strategy Repository is the persistent storage system for all strategy artifacts: parameter sets, signal logic specifications, validation reports, backtesting results, optimization records, performance history, and audit records.

**Responsibilities:**
- Store all strategy artifacts with full version control
- Provide retrieval of any strategy artifact at any historical version
- Maintain integrity of stored artifacts (no silent corruption)
- Support artifact search: find strategies with Sharpe > X in regime Y
- Support bulk export for analysis and governance review
- Maintain artifact retention schedule per governance policy

**Inputs:** Artifacts from all Strategy Engine components; artifact retrieval requests.

**Outputs:** Strategy artifacts to requestors; integrity reports to SC-15 Audit Manager.

**Artifact Types:**
- Strategy Definition: parameter set, signal logic, entry/exit rules
- Validation Report: results from SC-05 Validator
- Backtest Report: results from L16 ValidationEngine backtesting
- Optimization Record: parameter search history and objective function evolution
- Walk-Forward Test Report: out-of-sample performance across time windows
- Regime Performance Record: performance by market regime
- Performance Attribution Report: P&L attribution by instrument, sector, strategy rule

**Dependencies:** SC-19 Version Manager; SC-15 Audit Manager.

---

### SC-04 — Strategy Builder

**Purpose:** The Strategy Builder is the component through which new strategies are designed and configured. It provides the structured framework for specifying a complete strategy definition.

**Responsibilities:**
- Validate completeness of new strategy definitions (all required fields present)
- Enforce strategy naming standards
- Assign initial version number (1.0) to all new strategies
- Coordinate with SC-20 Metadata Manager to populate required metadata
- Submit completed strategy definitions to SC-01 Registry for DRAFT registration
- Validate that the strategy hypothesis is explicitly documented
- Check for taxonomy compliance (strategy is classified in the Catalog)
- Verify that entry rules, exit rules, and position sizing method are all explicitly defined

**Inputs:** Strategy definition from human or AI strategy developer; hypothesis document; parameter specifications; rule definitions.

**Outputs:** Validated strategy definition registered in SC-01 as DRAFT; metadata record in SC-20.

**Required Strategy Definition Fields:**
1. Strategy ID (assigned by SC-01)
2. Strategy Name (human-readable, unique)
3. Strategy Type (from ST-01 through ST-24 taxonomy)
4. Hypothesis Statement (the market inefficiency being exploited)
5. Universe Definition (which instruments this strategy applies to)
6. Signal Generation Rules (indicator logic → signal conditions)
7. Entry Rules (conditions for opening a position)
8. Exit Rules (profit target, stop-loss, time-based, signal reversal)
9. Position Sizing Method (how much capital per trade)
10. Regime Filter (conditions under which the strategy is active)
11. Parameters (all tunable values with initial values and ranges)
12. Performance Expectations (expected win rate, payoff ratio, Sharpe, Max DD)
13. Data Requirements (which data feeds are required)
14. Dependencies (other strategies, signals, or models relied upon)

**Failure Mode:** Incomplete strategy definition → builder rejects; returns validation errors to developer.

---

### SC-05 — Strategy Validator

**Purpose:** The Strategy Validator performs comprehensive technical and logical validation of strategy definitions before they are admitted to the backtesting and optimization pipeline.

**Responsibilities:**
- Validate strategy logical consistency: do entry and exit rules make sense together?
- Verify that all referenced data feeds exist and are available
- Check parameter ranges for plausibility: are all parameter ranges reasonable?
- Validate signal logic for common errors: look-ahead bias, survivorship bias
- Verify that the strategy does not violate any constitutional rules
- Perform basic sanity backtesting (minimum 1-year, out-of-sample)
- Check for obvious overfitting signatures: too many parameters, too few trades
- Validate risk compatibility: does the strategy's expected risk profile fit within IIOS Risk Engine limits?
- Check for strategy duplication: is this strategy substantively identical to an existing strategy?

**Inputs:** DRAFT strategy definition from SC-04; parameter ranges from strategy specification; data feed availability from data layer.

**Outputs:** Validation report (PASS/FAIL with detailed findings); validated strategy definition promoted to IN_VALIDATION status; rejection report if validation fails.

**Validation Gates (all must pass):**

| Gate | Description | Failure Action |
|------|-------------|----------------|
| V-01 | Logical Consistency | Reject to DRAFT; detailed error report |
| V-02 | Data Availability | Reject; list missing data sources |
| V-03 | Parameter Plausibility | Reject; flag implausible ranges |
| V-04 | Look-ahead Bias Check | Reject; identify specific look-ahead violations |
| V-05 | Minimum Trade Frequency | Reject if < 20 trades in sample period |
| V-06 | Constitutional Compliance | Reject if any HARD rule violated |
| V-07 | Risk Compatibility | Reject if expected Max DD > 15% |
| V-08 | Duplication Check | Flag if > 0.90 correlation with existing strategy |

**Failure Mode:** Validation engine unavailable → no new strategies can be promoted; DRAFT strategies queue; alert raised.

---

### SC-06 — Strategy Optimizer

**Purpose:** The Strategy Optimizer searches the parameter space of a validated strategy to find the parameter combination that best maximizes the objective function subject to constraints.

**Responsibilities:**
- Execute parameter optimization using defined optimization algorithms
- Enforce out-of-sample validation at every optimization step (prevents overfitting)
- Track optimization history: all parameter combinations evaluated and their scores
- Apply optimization constraints (minimum trade frequency, maximum drawdown limits)
- Produce the optimized parameter set with full documentation
- Detect and flag parameter instability (optimal parameters that are highly sensitive to small changes)
- Support multiple optimization objectives: Sharpe, Calmar, Sortino, modified Sortino
- Apply walk-forward optimization to validate parameter robustness across time

**Inputs:** Validated strategy definition from SC-05; historical market data; optimization objective and constraints from governance.

**Outputs:** Optimized parameter set with confidence interval; optimization report; parameter stability analysis.

**Supported Optimization Methods:**
- Grid Search: exhaustive search over defined parameter grid; slow but thorough; suitable for few parameters.
- Random Search: random sampling of parameter space; faster than grid for high-dimensional spaces.
- Bayesian Optimization: sequential model-based optimization; efficient for expensive objective functions.
- Walk-Forward Optimization: optimize on in-sample; validate on out-of-sample; roll forward.
- Genetic Algorithm: evolutionary optimization; explores complex parameter interactions.

**Overfitting Protection:**
- Minimum training/test ratio: 70% training, 30% out-of-sample.
- Out-of-sample Sharpe must be > 0.5 x in-sample Sharpe.
- Optimal parameter must not be at the boundary of the search range (boundary solutions are overfitting indicators).
- Monte Carlo permutation test: parameters must outperform randomized data at p < 0.05.

**Failure Mode:** Optimizer produces parameter set that fails out-of-sample → strategy returned to DRAFT with overfitting findings.

---

### SC-07 — Strategy Simulator

**Purpose:** The Strategy Simulator runs realistic full simulations of strategy performance, incorporating transaction costs, slippage, market impact, liquidity constraints, and realistic execution delays.

**Responsibilities:**
- Execute event-driven simulations using historical OHLCV data
- Apply realistic transaction cost models (commission, STT, slippage)
- Simulate order execution delay (next-open execution for EOD strategies)
- Apply liquidity constraints: orders cannot exceed X% of average daily volume
- Produce simulation performance reports (all metrics in the performance catalogue)
- Support Monte Carlo simulation: run N variations of the strategy on perturbed data
- Support regime-stratified simulation: performance in each market regime
- Support stress scenario simulation: performance under defined stress scenarios
- Provide equity curve, drawdown curve, and position history

**Inputs:** Optimized strategy definition from SC-06; historical market data; simulation parameters (start/end date, initial capital, cost model).

**Outputs:** Full simulation report; equity curve; drawdown analysis; regime performance breakdown; Monte Carlo distribution of outcomes.

**Simulation Modes:**
- Standard Simulation: single run with best-estimate costs.
- Monte Carlo Simulation: N runs with randomized entry/exit timing ± 1 bar.
- Regime-Stratified Simulation: separate reports for each market regime.
- Stress Test Simulation: performance during defined crisis scenarios.
- Walk-Forward Simulation: rolling in-sample/out-of-sample to check for parameter decay.

---

### SC-08 — Strategy Evaluator

**Purpose:** The Strategy Evaluator assesses the complete quality profile of a simulated strategy against all promotion criteria. It produces the structured evaluation report that governance uses to decide whether to promote a strategy.

**Responsibilities:**
- Compute all 13 Strategy Quality Dimensions (Part VII) for a given strategy
- Compare performance against all IIOS promotion gates (WinRate, Sharpe, MaxDD)
- Assess strategy originality (does it add genuinely diversified value?)
- Evaluate strategy robustness (stability of results across parameter perturbation)
- Assess strategy regime compatibility (does it work in the intended regimes?)
- Produce the Strategy Quality Score (SQS) for comparison
- Provide written evaluation narrative for governance review
- Flag any conditions that warrant governance attention

**Inputs:** Simulation reports from SC-07; historical performance data; promotion gate thresholds from governance.

**Outputs:** Strategy evaluation report with SQS; pass/fail on all promotion gates; written narrative; recommendation to governance.

**Promotion Gates (all must pass):**

| Gate | Metric          | Minimum Threshold | Description                           |
|------|-----------------|-------------------|---------------------------------------|
| PG-01| Win Rate        | >= 50%            | More than half of trades are profitable|
| PG-02| Sharpe Ratio    | > 0.8             | Adequate risk-adjusted return          |
| PG-03| Max Drawdown    | < 15%             | Acceptable downside risk               |
| PG-04| Trade Count     | >= 50             | Enough trades to be statistically significant |
| PG-05| OOS Performance | Sharpe OOS > 0.5  | Must work out-of-sample                |
| PG-06| Regime Coverage | >= 2 regimes      | Must work in more than one regime      |
| PG-07| Originality     | Corr < 0.80       | Adds diversified value vs existing strategies |

---

### SC-09 — Strategy Ranking Engine

**Purpose:** The Strategy Ranking Engine produces a ranked ordering of all APPROVED and ACTIVE strategies for the Selection Engine to use when deciding which strategies should be activated.

**Responsibilities:**
- Compute composite ranking scores for all eligible strategies
- Maintain real-time performance rankings (updated every session)
- Provide regime-conditional rankings (different rankings for different market regimes)
- Support multi-criterion ranking (by Sharpe, by Calmar, by composite score)
- Track ranking trends: is a strategy's rank improving or deteriorating?
- Alert when a strategy's ranking falls significantly (signal of performance degradation)

**Inputs:** Strategy performance records from L13 Learning Engine; regime signal from L2 MarketIntelligence; evaluation reports from SC-08.

**Outputs:** Strategy ranking list; regime-conditional ranking; ranking trend analysis.

**Ranking Formula:**
Composite Score = w_sr x Sharpe + w_cal x Calmar + w_wr x WinRate + w_pr x PayoffRatio + w_orig x Originality
Default weights: w_sr = 0.35, w_cal = 0.25, w_wr = 0.20, w_pr = 0.15, w_orig = 0.05

Regime multiplier applied: if strategy's historical performance in current regime is above average, multiply composite score by 1.0 to 1.2. If below average, multiply by 0.8 to 1.0.

---

### SC-10 — Strategy Selection Engine

**Purpose:** The Strategy Selection Engine decides which strategies should be active at any given time, drawing on rankings, regime conditions, capital availability, and portfolio constraints.

**Responsibilities:**
- Maintain the active strategy set (which strategies are currently generating signals)
- Evaluate activation candidates: strategies ranked highly by SC-09 for current regime
- Evaluate deactivation candidates: active strategies with deteriorating ranking or poor recent performance
- Coordinate with Portfolio Engine for capital availability check before activation
- Coordinate with Risk Engine for risk budget check before activation
- Enforce maximum concurrent strategy limits
- Enforce strategy family concentration limits (too many momentum strategies at once)
- Handle regime change: activate/deactivate strategies as regime shifts
- Provide selection rationale for all activation and deactivation decisions

**Inputs:** Strategy rankings from SC-09; regime signal from L2; portfolio state from Portfolio Engine; risk budget from L6 CapitalRisk.

**Outputs:** Active strategy set; activation/deactivation decisions with rationale; notifications to L17 ControlTower.

**Selection Rules:**
- Maximum active strategies: 8 (configurable)
- Maximum strategies from same ST type: 3
- New strategy activation requires: Ranking >= Top 20% for current regime; capital available; risk budget available; not correlated > 0.80 with existing active strategy.
- Deactivation triggers: Ranking falls below bottom 40% for 3 consecutive sessions; session drawdown > 3% from this strategy; human override.

---

### SC-11 — Strategy Evolution Engine

**Purpose:** The Strategy Evolution Engine is responsible for improving existing strategies over time by modifying their parameters, signal logic, or structural design based on accumulated performance data.

**Responsibilities:**
- Identify strategies that are candidates for evolution (underperforming but not yet retirement-worthy)
- Propose parameter adjustments based on recent performance data and optimization
- Propose structural modifications (new signal component, changed exit logic) when parameters alone are insufficient
- Coordinate with L13 Learning Engine for outcome data and model updates
- Submit all evolution proposals to governance for approval before implementation
- Maintain complete versioning of every evolution step
- Track evolution outcomes: did the evolved version improve or degrade performance?
- Support rollback: if evolution proves harmful, revert to prior version

**Inputs:** Strategy performance data from L13; evaluation reports from SC-08; governance direction from SC-14; optimization results from SC-06.

**Outputs:** Evolution proposal with rationale; new strategy version registered in SC-01; evolution outcome report.

**Evolution Triggers:**
- Gradual performance decline: Sharpe trend falling for > 10 consecutive sessions
- Regime mismatch: strategy performing well in backtesting but poorly in current live regime
- Learning Engine signal: specific exit rule consistently suboptimal
- Governance-directed: operations team directs evolution based on external insight

**Evolution Types:**
- Parameter Evolution: tune numerical parameters (lookback periods, thresholds, stop distances) while keeping signal logic unchanged.
- Rule Evolution: add, remove, or modify signal rules while keeping the core hypothesis unchanged.
- Model Evolution: replace or retrain the underlying statistical or ML model while keeping entry/exit structure.
- Structural Evolution: substantial redesign of the strategy approach; treated as a new strategy version.

**Overfitting Protection in Evolution:** Same rules as SC-06 Optimizer; evolution must produce out-of-sample improvement.

---

### SC-12 — Strategy Retirement Manager

**Purpose:** The Strategy Retirement Manager governs the formal process of removing strategies from active use, ensuring that retirement decisions are deliberate, documented, and reversible.

**Responsibilities:**
- Monitor strategies for retirement triggers (sustained poor performance, regime obsolescence, Risk Engine disqualification)
- Generate retirement recommendations with supporting evidence
- Coordinate with SC-14 Governance Manager for formal retirement approval
- Execute retirement: transition strategy from ACTIVE to RETIRED status
- Ensure all artifacts are transferred to SC-03 Repository before retirement
- Maintain the complete retirement record for future reference
- Support strategy reactivation from RETIRED status if conditions change

**Retirement Triggers:**

| Trigger | Condition |
|---------|-----------|
| Performance | Win rate < 40% over 30-session rolling; Sharpe < 0 over 60-session rolling |
| Drawdown | Maximum drawdown > 20% since last reset |
| Regime Obsolescence | Strategy only works in a regime that has not occurred in > 90 sessions |
| Model Decay | ML model's predictive power (AUC) has degraded beyond recovery threshold |
| Governance Direction | Operations Lead or System Owner directs retirement |
| Capital Efficiency | Information Ratio consistently < 0 for 90 sessions |

**Retirement Types:**
- Immediate Retirement: strategy suspended and retired in one session (for severe failures or security events).
- Graceful Retirement: strategy enters DEPRECATED state; existing positions closed naturally; retirement upon position closure.
- Scheduled Retirement: retirement planned for a future date; communicated in governance report.

---

### SC-13 — Strategy Monitoring Engine

**Purpose:** The Strategy Monitoring Engine provides continuous real-time and session-level monitoring of all active strategies, generating alerts when thresholds are approached or breached.

**Responsibilities:**
- Monitor all active strategies for performance thresholds
- Track intraday strategy P&L and drawdown
- Monitor signal generation rate: is the strategy generating too few or too many signals?
- Monitor signal quality: are signals leading to profitable trades?
- Monitor regime alignment: is the current regime still compatible with the active strategy?
- Generate graded alerts: WARNING (approaching threshold), ALERT (threshold breached), CRITICAL (governance action required)
- Provide real-time strategy health feed to SC-17 Health Manager and L17 ControlTower

**Monitoring Schedule:**

| Metric                        | Frequency     | Alert Threshold                   |
|-------------------------------|---------------|-----------------------------------|
| Strategy session P&L          | Every 30s     | WARNING at -1%; ALERT at -2%      |
| Signal generation rate        | Every 5m      | WARNING if 0 signals in 60 min    |
| Regime alignment              | Every session | ALERT if regime changed; check    |
| Rolling Sharpe (30-session)   | Daily         | WARNING if < 0.5; ALERT if < 0    |
| Rolling win rate (30-session) | Daily         | WARNING if < 45%; ALERT if < 40%  |
| Parameter drift               | Weekly        | ALERT if parameters at boundary   |

---

### SC-14 — Strategy Governance Manager

**Purpose:** The Strategy Governance Manager orchestrates all governance activities for the Strategy Engine: approval workflows, review cycles, compliance monitoring, and override tracking.

**Responsibilities:**
- Manage strategy promotion approval workflow (DRAFT → APPROVED)
- Manage strategy retirement approval workflow
- Manage evolution approval workflow
- Schedule and track governance review cycles
- Record all human overrides (activation, deactivation, parameter changes)
- Generate governance reports for review
- Enforce dual-approval requirements for high-impact decisions
- Track governance action items to completion

**Approval Workflows:**

| Workflow | Decision Points | Required Approvals |
|----------|-----------------|-------------------|
| New Strategy Promotion | SC-05 gates pass; SC-08 evaluation pass | Operations Lead sign-off |
| Strategy Activation | SC-10 selection; Risk Engine approval | System acknowledges |
| Strategy Retirement | SC-12 recommendation | Operations Lead sign-off |
| Strategy Evolution | SC-11 proposal | Operations Lead sign-off |
| Constitutional Rule Change | Proposed by System Owner | System Owner only |

---

### SC-15 — Strategy Audit Manager

**Purpose:** The Strategy Audit Manager maintains the complete, tamper-proof audit trail for all Strategy Engine state changes and governance decisions.

**Responsibilities:**
- Create audit records for every strategy state transition
- Maintain SHA-256 hash chain for all strategy audit records
- Verify hash chain integrity at session start
- Provide audit queries for governance and compliance
- Support forensic investigation of strategy lifecycle events
- Generate audit integrity reports

**Audit Record Format:**
- audit_id: AUD-STR-{YYYYMMDD}-{SEQ:08d}
- timestamp: ISO 8601 with microsecond precision
- event_type: CREATED, VALIDATED, APPROVED, ACTIVATED, SUSPENDED, RETIRED, EVOLVED, PARAMETER_CHANGED, OVERRIDE
- strategy_id: reference to SC-01 Registry
- component_id: which component created this record
- state_before: complete strategy state before change
- state_after: complete strategy state after change
- operator_id: human operator if override; "SYSTEM" if automated
- rationale: reason for change
- prior_hash: SHA-256 hash of previous audit record
- chain_hash: SHA-256 hash of (this_record + prior_hash)

**Retention:** 7 years for all audit records.

---

### SC-16 — Strategy Analytics Engine

**Purpose:** The Strategy Analytics Engine provides higher-order intelligence about strategy performance trends, inter-strategy relationships, and portfolio-level analytics.

**Responsibilities:**
- Compute strategy alpha decay curves (how does a strategy's alpha erode over time?)
- Compute strategy correlation matrix (inter-strategy return correlations)
- Identify performance clustering (strategies that always succeed or fail together)
- Detect regime-specific performance patterns
- Identify overfitting signatures in live performance
- Produce strategy effectiveness reports for governance
- Analyze the collective performance of the active strategy set

**Outputs:** Strategy correlation matrix; alpha decay analysis; regime performance attribution; strategy cluster analysis.

---

### SC-17 — Strategy Health Manager

**Purpose:** The Strategy Health Manager computes the Strategy Engine Health Score (SEHS) — a composite measure of the operational health of the entire Strategy Engine.

**Responsibilities:**
- Compute SEHS from 20 component health scores
- Identify components that are degrading overall health
- Provide per-component health status
- Certify Strategy Engine readiness at session start
- Alert when SEHS falls below tier thresholds

**SEHS Tiers:**

| Tier     | Score Range | Response                                     |
|----------|-------------|----------------------------------------------|
| OPTIMAL  | 0.90–1.00   | All components healthy; full operations      |
| NOMINAL  | 0.75–0.89   | Minor issues; full operations                |
| DEGRADED | 0.55–0.74   | Some components impaired; restricted ops     |
| CRITICAL | 0.30–0.54   | Multiple failures; automated ops suspended   |
| FAILED   | 0.00–0.29   | Engine failure; human intervention required  |

---

### SC-18 — Strategy Reporting Manager

**Purpose:** The Strategy Reporting Manager produces all strategy-level reports for operators, governance reviewers, and connected systems.

**Report Types:**

| Report                   | Frequency   | Audience            | Content                                  |
|--------------------------|-------------|---------------------|------------------------------------------|
| Session Strategy Summary | Daily       | Operator (Telegram) | Active strategies; signal count; P&L     |
| Strategy Performance     | Daily       | Dashboard (L17)     | All metrics per active strategy          |
| Governance Report        | Daily       | Reviewer queue      | Events, overrides, alerts                |
| Weekly Evolution Review  | Weekly      | Operations Lead     | Parameter drift; evolution candidates    |
| Monthly Portfolio Report | Monthly     | System Owner        | Full analytics; governance compliance    |
| Retirement Report        | On event    | Governance          | Retirement rationale and outcome         |

---

### SC-19 — Strategy Version Manager

**Purpose:** The Strategy Version Manager maintains the complete versioning history of every strategy definition, ensuring that any prior version can be retrieved and that version increments follow the defined scheme.

**Versioning Scheme:** MAJOR.MINOR.PATCH
- MAJOR: Structural evolution (new rule logic, changed hypothesis, new model)
- MINOR: Parameter optimization (same logic, different parameter values)
- PATCH: Documentation or metadata correction (no behavioral change)

**Responsibilities:**
- Assign version numbers at each evolution step
- Store complete strategy definition for each version
- Support diff between versions: what changed between v1.2 and v2.0?
- Support rollback: revert to any prior version with full audit
- Enforce version increment rules (MAJOR must go through governance)

---

### SC-20 — Strategy Metadata Manager

**Purpose:** The Strategy Metadata Manager maintains all descriptive metadata about strategies that does not constitute the core strategy definition but is essential for governance, search, and operations.

**Metadata Fields:**
- Creator: who designed this strategy (human name or "IIOS-AI")
- Creation Date: when was this strategy first registered
- Primary Type: taxonomy code (ST-01 through ST-24)
- Secondary Types: other applicable taxonomy codes
- Target Regime: which market regimes this strategy is designed for
- Instrument Universe: which symbols or universe screens apply
- Data Requirements: which data feeds are required
- Dependencies: other strategies or models this strategy depends on
- Tags: free-text searchable tags for governance and search
- Review Schedule: when is the next scheduled governance review
- Owner: who is the human accountable for this strategy
- Related Strategies: strategies that are conceptually related or evolved from each other

---

## PART IV — STRATEGY LIFECYCLE

### 4.0 Lifecycle Design Philosophy

The Strategy Lifecycle defines the complete journey a strategy takes from its first inception as an idea through active deployment, continuous improvement, and eventual retirement. The lifecycle is governed — no stage is skipped, no transition is informal. Every stage transition is audited.

The lifecycle is designed to maximize strategy quality at each gate while minimizing the time from idea to deployment. Gates are not bureaucratic obstacles — they are quality filters that prevent poorly designed strategies from consuming capital.

---

### 4.1 Lifecycle Stages

**Stage 1 — Idea Generation (SLS-01)**

*Trigger:* Human operator insight; AI pattern discovery from L4 OpportunityEngine; market regime shift suggesting new opportunity; Learning Engine signal that a new approach might address an existing strategy's weakness.

*Actions:* Idea is documented in structured format. Hypothesis is stated explicitly. Supporting evidence (historical observations, market logic) is noted. Idea is reviewed against existing strategy catalog to check for duplication.

*Output:* Idea record in SC-03 Repository with status IDEA. Not yet registered in SC-01 (no ID assigned until submitted as DRAFT strategy).

*Duration:* Variable; typically 1 day to 1 week.

---

**Stage 2 — Research (SLS-02)**

*Trigger:* Idea accepted for research by operator or AI research process.

*Actions:* Historical data analysis to test the core hypothesis. Preliminary signal analysis. Literature/pattern review. Market microstructure analysis. Regime compatibility assessment. Risk profile estimation.

*Output:* Research report: hypothesis supported / partially supported / not supported. If supported: proceed to Hypothesis Formation. If not supported: return to Idea pool or abandon.

---

**Stage 3 — Hypothesis Formation (SLS-03)**

*Trigger:* Research report supports the core idea.

*Actions:* Hypothesis is formalized: specific, testable, falsifiable. Null hypothesis is stated. Test criteria defined (what Sharpe, win rate, drawdown would confirm the hypothesis?). Regime applicability defined. Universe defined.

*Output:* Formal hypothesis document attached to idea record.

---

**Stage 4 — Strategy Design (SLS-04)**

*Trigger:* Formal hypothesis approved for strategy development.

*Actions:* SC-04 Strategy Builder engaged. Entry rules designed. Exit rules designed (profit target, stop-loss, time-based). Position sizing method selected. Parameters defined with ranges. Signal generation logic specified. Regime filter specified.

*Output:* Complete strategy definition registered as DRAFT in SC-01. ID assigned.

---

**Stage 5 — Validation (SLS-05)**

*Trigger:* DRAFT strategy submitted to SC-05 Validator.

*Actions:* All 8 validation gates checked. Logical consistency, data availability, look-ahead bias scan, parameter plausibility, constitutional compliance, risk compatibility, originality check.

*Output:* PASS → strategy promoted to IN_VALIDATION status. FAIL → returned to DRAFT with detailed error report.

---

**Stage 6 — Backtesting (SLS-06)**

*Trigger:* Strategy passes SC-05 validation.

*Actions:* L16 ValidationEngine runs full 6-stage validation pipeline: Backtest → Walk-Forward Test → Cross-Market Test → Monte Carlo → Sensitivity → Regime. SC-07 Simulator runs all simulation modes.

*Output:* Comprehensive backtest report; equity curve; drawdown analysis; regime-stratified performance. If all gates pass: proceed to Optimization. If any gate fails: return to Design or Validation.

---

**Stage 7 — Simulation (SLS-07)**

*Trigger:* Backtesting complete; strategy passes all backtesting gates.

*Actions:* SC-07 runs realistic simulations including transaction costs, slippage, liquidity constraints. Monte Carlo simulation to assess distribution of outcomes. Stress testing against defined crisis scenarios.

*Output:* Simulation report; expected performance range (P10, P50, P90 Sharpe outcomes); stress test results.

---

**Stage 8 — Optimization (SLS-08)**

*Trigger:* Simulation reports produced.

*Actions:* SC-06 Optimizer runs parameter search using walk-forward optimization. Overfitting protection applied at every step. Optimal parameter set identified. Parameter stability analysis produced.

*Output:* Optimized strategy definition; optimization report; parameter sensitivity curves. If parameter is unstable → strategy returned to Design for structural review.

---

**Stage 9 — Approval (SLS-09)**

*Trigger:* Optimization complete; SC-08 Evaluator produces evaluation report.

*Actions:* SC-08 evaluation against all promotion gates. SC-14 Governance Manager convenes approval review. Operations Lead reviews evaluation report. If approved: strategy promoted to APPROVED status.

*Output:* Strategy in APPROVED status in SC-01 Registry. Ready for Selection Engine consideration.

---

**Stage 10 — Registration (SLS-10)**

*Trigger:* Strategy reaches APPROVED status.

*Actions:* Full strategy definition committed to SC-03 Repository. SC-20 Metadata Manager populates complete metadata. SC-19 Version Manager assigns version 1.0. SC-16 Analytics Engine adds strategy to analytics tracking universe.

*Output:* Fully registered, versioned strategy with complete metadata. Listed by SC-09 Ranking Engine for future selection consideration.

---

**Stage 11 — Activation (SLS-11)**

*Trigger:* SC-10 Selection Engine identifies the strategy as a candidate for the current regime and capital is available.

*Actions:* Risk Engine (L6) confirms risk budget; Portfolio Engine confirms capital allocation; SC-10 selects strategy; strategy status → ACTIVE; SC-13 Monitoring Engine begins monitoring; L17 ControlTower notified; operator Telegram notification.

*Output:* Strategy in ACTIVE status; signal generation begins; performance tracking begins in L13.

---

**Stage 12 — Monitoring (SLS-12)**

*Trigger:* Strategy is ACTIVE.

*Actions:* SC-13 monitors all metrics every 30 seconds (P&L) and daily (Sharpe, win rate). SC-09 updates rankings. L13 Learning Engine tracks outcomes. Alerts generated as needed.

*Duration:* Continuous for all active strategies.

---

**Stage 13 — Learning (SLS-13)**

*Trigger:* Each closed trade delivers outcome data to L13 Learning Engine.

*Actions:* L13 Learning Engine processes outcome data. Win rate, average win, average loss, regime-specific performance updated. Strategy Performance Tracker updates per-strategy statistics. Insights fed back to SC-11 Evolution Engine.

*Output:* Updated performance statistics; learning signals for evolution evaluation.

---

**Stage 14 — Evolution (SLS-14)**

*Trigger:* Learning signals suggest parameter adjustment is warranted; or performance trend triggers evolution evaluation.

*Actions:* SC-11 Evolution Engine proposes parameter or structural changes. SC-06 Optimizer validates proposed changes (must improve out-of-sample). SC-14 Governance approves. SC-19 Version Manager increments version. New version activated; old version DEPRECATED.

*Output:* New strategy version in ACTIVE status; prior version in DEPRECATED status (kept for rollback).

---

**Stage 15 — Version Upgrade (SLS-15)**

*Trigger:* Structural evolution that warrants a MAJOR version increment.

*Actions:* New version treated as a new strategy in some respects — re-validation, re-backtesting. SC-08 re-evaluates. SC-14 approves. Prior version DEPRECATED. New version activated.

*Output:* New major version registered; complete new validation package in SC-03.

---

**Stage 16 — Retirement (SLS-16)**

*Trigger:* SC-12 Retirement Manager identifies retirement trigger; or governance-directed retirement.

*Actions:* SC-14 Governance approves retirement. Strategy transitions ACTIVE → DEPRECATED → RETIRED (or immediate RETIRED for urgent cases). Existing positions closed gracefully (by Execution Engine, not Strategy Engine). Full retirement report produced.

*Output:* Strategy in RETIRED status; complete retirement record.

---

**Stage 17 — Archive (SLS-17)**

*Trigger:* Strategy has been RETIRED and all positions are closed.

*Actions:* SC-03 Repository confirms all artifacts are stored. SC-15 Audit Manager confirms hash chain integrity. Strategy status → ARCHIVED. SC-01 Registry maintains record permanently (ARCHIVED is terminal; cannot be changed).

*Output:* Strategy in ARCHIVED status; permanent historical record preserved.

---

### 4.2 Strategy State Machine

`
STRATEGY STATE MACHINE
════════════════════════

IDEA (pre-registration concept)
  │ Research completed; hypothesis formed
  ▼
DRAFT (registered in SC-01; under development)
  │ Passes SC-05 validation
  ▼
IN_VALIDATION (validation in progress)
  │ Backtesting + simulation + optimization complete
  │ SC-08 evaluation → all promotion gates pass
  ▼
APPROVED (ready for selection)
  │ SC-10 Selection Engine selects; capital available
  ▼
ACTIVE (generating signals; deployed)
  ├── Evolution approved → DEPRECATED (old) + ACTIVE (new version)
  ├── Performance trigger → SUSPENDED
  ├── Kill Switch → SUSPENDED
  └── Retirement approved → DEPRECATED
SUSPENDED (halted; not generating signals)
  ├── Issue resolved + human authorization → ACTIVE
  └── Retirement decision → DEPRECATED
DEPRECATED (superseded; winding down positions)
  │ All positions closed
  ▼
RETIRED (no longer deployed; no positions)
  │ Artifacts confirmed in repository
  ▼
ARCHIVED (permanent historical record)
  └── [Terminal state — cannot be changed]
`

---

### 4.3 Lifecycle Timing Reference

| Stage        | Typical Duration     | Bottleneck                           |
|--------------|----------------------|--------------------------------------|
| Idea → Draft | 1–5 days             | Research quality; hypothesis clarity |
| Validation   | Hours (automated)    | Data availability                    |
| Backtesting  | Hours (automated)    | Compute for Monte Carlo              |
| Optimization | Hours–1 day          | Optimization compute                 |
| Approval     | 1–3 days             | Human governance availability        |
| Activation   | Minutes (automated)  | Capital and risk budget availability |
| Active Life  | 30 days – 2 years    | Strategy performance                 |
| Evolution    | Days (per cycle)     | Validation and governance            |
| Retirement   | Minutes–1 week       | Position wind-down                   |

---

### 4.4 Full Lifecycle Sequence Diagram

`
STRATEGY FULL LIFECYCLE — SEQUENCE DIAGRAM
═══════════════════════════════════════════

[Human/AI]          [Strategy Engine]         [External Layers]
    │                     │                          │
    │ Submit idea          │                          │
    ├────────────────────► │                          │
    │                     │ Research                 │
    │                     ├──────────────────────────►│ L1 GlobalIntelligence
    │                     ◄──────────────────────────┤ Historical context
    │                     │                          │
    │                     │ Build + Validate          │
    │                     ├─[SC-04]─[SC-05]──────────►│ L16 ValidationEngine
    │                     ◄──────────────────────────┤ Validation result
    │                     │                          │
    │                     │ Backtest + Simulate       │
    │                     ├─[SC-07]──────────────────►│ Historical data
    │                     ◄──────────────────────────┤ Simulation report
    │                     │                          │
    │                     │ Optimize                 │
    │                     ├─[SC-06]──────────────────►│ Walk-forward data
    │                     ◄──────────────────────────┤ Optimal params
    │                     │                          │
    │ Governance review    │                          │
    ◄────────────────────── ─[SC-08]─[SC-14]          │
    │ Approve              │                          │
    ├────────────────────► │                          │
    │                     │ Register + Activate       │
    │                     ├─[SC-01]─[SC-10]──────────►│ L6 Risk budget
    │                     ◄──────────────────────────┤ Budget confirmed
    │                     │ ACTIVE                    │
    │                     ├─[SC-13]──────────────────►│ L13 Learning feed
    │                     │ (continuous monitoring)   │
    │                     │                          │
    │                     │ Evolution cycle           │
    │                     ├─[SC-11]─[SC-06]──────────►│ Performance data
    │ Approve evolution    │                          │
    ◄────────────────────── ─[SC-14]                  │
    │ Approve              │                          │
    ├────────────────────► │ New version activated     │
    │                     │                          │
    │                     │ Retirement evaluation     │
    │                     ├─[SC-12]──────────────────►│
    │ Approve retirement   │                          │
    ◄────────────────────── ─[SC-14]                  │
    │ Approve              │                          │
    ├────────────────────► │ RETIRED → ARCHIVED        │
    │                     │                          │
`

---

## PART V — STRATEGY SERVICES

### 5.0 Service Architecture Overview

Strategy Services are the named, purpose-bounded computation units that expose Strategy Engine functionality. Each service has a defined interface and can be called independently.

---

### SS-01 — Registration Service

**Purpose:** Manages the complete strategy registration workflow from DRAFT creation to APPROVED status.
**Interface:** register_strategy(definition) → StrategyRecord; update_draft(strategy_id, changes) → StrategyRecord; submit_for_validation(strategy_id) → ValidationRecord.

---

### SS-02 — Validation Service

**Purpose:** Executes all validation gates against a submitted strategy definition.
**Interface:** validate_strategy(strategy_id) → ValidationReport; get_validation_status(strategy_id) → ValidationStatus; resubmit_after_fix(strategy_id, changes) → ValidationReport.

---

### SS-03 — Optimization Service

**Purpose:** Executes parameter optimization for a validated strategy.
**Interface:** optimize_strategy(strategy_id, objective, constraints) → OptimizationReport; get_optimization_status(strategy_id) → OptimizationStatus; retrieve_optimal_params(strategy_id) → ParameterSet.

---

### SS-04 — Simulation Service

**Purpose:** Runs simulation modes for a strategy under realistic conditions.
**Interface:** run_simulation(strategy_id, config) → SimulationReport; run_monte_carlo(strategy_id, n_runs) → MonteCarloReport; run_stress_test(strategy_id, scenario_id) → StressReport.

---

### SS-05 — Evaluation Service

**Purpose:** Produces the comprehensive evaluation report for governance review.
**Interface:** evaluate_strategy(strategy_id) → EvaluationReport; check_promotion_gates(strategy_id) → GateCheckReport; get_sqs(strategy_id) → Float.

---

### SS-06 — Selection Service

**Purpose:** Manages the active strategy set, including activation and deactivation.
**Interface:** get_active_strategies() → List[StrategyRecord]; evaluate_activation_candidates(regime) → List[ActivationCandidate]; activate_strategy(strategy_id, reason) → ActivationRecord; deactivate_strategy(strategy_id, reason) → DeactivationRecord.

---

### SS-07 — Monitoring Service

**Purpose:** Provides real-time monitoring streams and snapshots for all active strategies.
**Interface:** subscribe_strategy_stream(subscriber_id, filters) → StrategyEventStream; get_strategy_snapshot(strategy_id) → StrategySnapshot; get_alerts() → List[Alert].

---

### SS-08 — Evolution Service

**Purpose:** Manages the strategy evolution workflow.
**Interface:** evaluate_evolution_need(strategy_id) → EvolutionNeedReport; propose_evolution(strategy_id) → EvolutionProposal; apply_evolution(proposal_id, approval) → NewStrategyVersion.

---

### SS-09 — Governance Service

**Purpose:** Manages governance workflows, approvals, and compliance.
**Interface:** submit_approval_request(workflow_type, strategy_id, context) → ApprovalRequest; approve(request_id, authority) → ApprovalRecord; get_governance_report(session_date) → GovernanceReport.

---

### SS-10 — Audit Service

**Purpose:** Provides audit record queries and integrity verification.
**Interface:** query_audit(strategy_id, start_time, end_time) → List[AuditRecord]; validate_chain_integrity(strategy_id) → ChainReport; generate_audit_report(strategy_id, period) → AuditReport.

---

### SS-11 — Analytics Service

**Purpose:** Provides strategy analytics intelligence.
**Interface:** get_strategy_analytics(strategy_id, period) → AnalyticsReport; get_correlation_matrix() → CorrelationMatrix; get_alpha_decay(strategy_id) → AlphaDecayCurve.

---

### SS-12 — Reporting Service

**Purpose:** Produces and delivers all strategy reports.
**Interface:** generate_session_report() → SessionReport; generate_governance_report(session_date) → GovernanceReport; deliver_telegram_summary(operator_id) → DeliveryStatus.

---

### SS-13 — Archive Service

**Purpose:** Provides access to historical strategy artifacts and performance data.
**Interface:** get_strategy_history(strategy_id) → StrategyHistory; get_performance_history(strategy_id, period) → PerformanceTimeSeries; get_archived_strategy(strategy_id, version) → StrategyDefinition.

---

### SS-14 — Health Service

**Purpose:** Provides Strategy Engine health status and readiness certification.
**Interface:** get_sehs() → SEHSReport; get_component_health(component_id) → ComponentHealth; certify_ready() → ReadinessCertification.

---

### SS-15 — Version Management Service

**Purpose:** Manages strategy versioning and rollback operations.
**Interface:** get_version_history(strategy_id) → List[VersionRecord]; get_version(strategy_id, version) → StrategyDefinition; rollback(strategy_id, target_version, reason) → RollbackRecord.

---

## PART VI — STRATEGY PROCESSING PIPELINES

### 6.0 Pipeline Design Philosophy

Strategy Processing Pipelines are the structured, sequential processing chains that transform inputs into strategy state changes and outputs. Each pipeline has a defined trigger, a mandatory sequence of processing stages, and defined outputs.

Eleven pipelines are defined: SP-01 through SP-11.

---

### SP-01 — Research Pipeline

**Purpose:** Transforms a raw idea into a validated hypothesis and preliminary research report.

**Trigger:** New strategy idea submitted.

**Flow Diagram:**

`
SP-01: RESEARCH PIPELINE
═════════════════════════

[New Idea Submission]
  │ Idea document: hypothesis, market logic, evidence
  ▼
[SC-02 Strategy Catalog]
  │ Duplication check: does this idea overlap with existing strategies > 80%?
  │ If duplicate → return with reference to existing strategy
  ▼
[SC-20 Metadata Manager]
  │ Assign idea record; assign researcher; set review date
  ▼
[L1 GlobalIntelligence + L2 MarketIntelligence]
  │ Provide historical regime and macro context for hypothesis testing
  ▼
[Historical Data Analysis]
  │ Preliminary signal analysis: does the proposed signal show any predictive power?
  │ Minimum test: 2-year historical data; >= 30 signal occurrences
  ▼
[Research Report Generation]
  │ Hypothesis: SUPPORTED / PARTIALLY_SUPPORTED / NOT_SUPPORTED
  │ Evidence summary; next steps recommendation
  ▼
[SC-03 Strategy Repository]
  └── Research report stored; idea status updated
`

---

### SP-02 — Validation Pipeline

**Purpose:** Validates a DRAFT strategy definition through all 8 validation gates.

**Trigger:** DRAFT strategy submitted to SC-05 Validator.

**Flow Diagram:**

`
SP-02: VALIDATION PIPELINE
═══════════════════════════

[DRAFT Strategy from SC-04 Builder]
  ▼
[V-01: Logical Consistency Check]
  │ Do entry and exit rules form a coherent investment logic?
  │ Can the strategy ever generate a signal given its rules?
  │ FAIL → reject to DRAFT with error report
  ▼
[V-02: Data Availability Check]
  │ Are all referenced data feeds available and reliable?
  │ FAIL → reject; list missing sources
  ▼
[V-03: Parameter Plausibility Check]
  │ Are parameter values and ranges within plausible bounds?
  │ (e.g., lookback period 1–500 days is plausible; 1–2 is not)
  │ FAIL → reject with specific parameter issues
  ▼
[V-04: Look-Ahead Bias Scan]
  │ Does any signal calculation use data that would not have been
  │ available at the signal generation time?
  │ FAIL → reject; identify specific violations
  ▼
[V-05: Trade Frequency Check]
  │ Preliminary simulation: does strategy generate >= 20 trades in 2-year sample?
  │ FAIL → strategy is too infrequent; return to design
  ▼
[V-06: Constitutional Compliance]
  │ Does strategy violate any HARD constitutional rule?
  │ FAIL → reject immediately; cite violated rule
  ▼
[V-07: Risk Compatibility]
  │ Does preliminary risk profile fit within IIOS Risk Engine limits?
  │ Expected Max DD < 15%? Expected position size within limits?
  │ FAIL → reject; risk profile too aggressive
  ▼
[V-08: Originality Check]
  │ Correlation with existing strategies: < 0.80 required
  │ FAIL → strategy too similar to existing; merger or differentiation required
  ▼
[Validation PASS]
  │ Strategy promoted to IN_VALIDATION
  └── Validation report stored in SC-03
`

---

### SP-03 — Backtesting Pipeline

**Purpose:** Runs comprehensive historical testing through the L16 ValidationEngine's 6-stage pipeline.

**Trigger:** Strategy passes SP-02 Validation Pipeline.

**Flow Diagram:**

`
SP-03: BACKTESTING PIPELINE
════════════════════════════

[IN_VALIDATION Strategy]
  ▼
[Stage 1: Backtest]
  │ L16 ValidationEngine: full backtest on historical data
  │ Minimum period: 5 years; minimum 100 trades
  │ Produce: equity curve, drawdown, all 10 performance metrics
  ▼
[Stage 2: Walk-Forward Test (WFT)]
  │ L16: rolling in-sample / out-of-sample validation
  │ 70/30 split; roll forward quarterly
  │ OOS Sharpe must be > 0.5 x IS Sharpe
  ▼
[Stage 3: Cross-Market Test]
  │ Test strategy on multiple instruments / time periods
  │ Confirms strategy logic is not data-mined to a specific period
  ▼
[Stage 4: Monte Carlo Simulation]
  │ SC-07: N=500 runs with randomized timing ± 1 bar
  │ P10 Sharpe must be > 0.3 (bottom 10th percentile acceptable)
  ▼
[Stage 5: Sensitivity Analysis]
  │ Perturb each parameter ± 20% from optimal
  │ Sharpe must not degrade > 50% on any perturbation
  │ (Tests parameter stability — not overfitting to exact optimal)
  ▼
[Stage 6: Regime Analysis]
  │ Performance stratified by market regime
  │ Must be positive in at least 2 of 5 regimes
  ▼
[Backtesting PASS]
  │ Strategy proceeds to Optimization
  └── Full backtesting report package stored in SC-03
`

---

### SP-04 — Optimization Pipeline

**Purpose:** Finds the optimal parameter set for a validated, backtested strategy.

**Trigger:** Strategy passes SP-03 Backtesting Pipeline.

**Flow Diagram:**

`
SP-04: OPTIMIZATION PIPELINE
══════════════════════════════

[Validated Strategy with Initial Parameters]
  ▼
[SC-06 Optimizer: Parameter Grid Definition]
  │ Define search space for each tunable parameter
  │ Validate that search space is within plausible bounds
  ▼
[Algorithm Selection]
  │ Parameters <= 5: Grid Search or Bayesian Optimization
  │ Parameters 6–15: Bayesian Optimization or Genetic Algorithm
  │ Parameters > 15: Genetic Algorithm with regularization
  ▼
[Walk-Forward Optimization Loop]
  │ For each optimization window:
  │   - Optimize on in-sample (70%)
  │   - Validate on out-of-sample (30%)
  │   - Record IS and OOS objective scores
  │ Roll forward; repeat
  ▼
[Overfitting Detection]
  │ OOS degradation > 50% of IS → overfitting signal
  │ Optimal at parameter boundary → overfitting signal
  │ Monte Carlo permutation test p < 0.05 required
  ▼
[Parameter Stability Analysis]
  │ Perturb optimal parameters ± 10%, ± 20%
  │ Plot parameter surface: smooth surface = stable; jagged = overfitting
  ▼
[Optimization PASS]
  │ Optimal parameter set selected; documented
  └── Optimization report stored in SC-03
`

---

### SP-05 — Selection Pipeline

**Purpose:** Evaluates candidate strategies for activation in the current market environment.

**Trigger:** Session start; regime change; active strategy deactivation creates capital availability.

**Flow Diagram:**

`
SP-05: SELECTION PIPELINE
══════════════════════════

[Trigger: Session Start / Regime Change / Capital Available]
  ▼
[SC-09 Ranking Engine: Current Rankings]
  │ Compute composite scores for all APPROVED strategies
  │ Apply regime multiplier for current regime
  │ Sort by composite score descending
  ▼
[Active Strategy Set Review]
  │ Which currently active strategies should be deactivated?
  │ Check: ranking still > bottom 40%? performance ok? regime still compatible?
  ▼
[Candidate Identification]
  │ Top-ranked APPROVED strategies not currently active
  │ Filter: compatible with current regime?
  │ Filter: correlation with existing active strategies < 0.80?
  ▼
[Capital and Risk Check]
  │ Portfolio Engine: is capital available for a new strategy?
  │ L6 CapitalRisk: is risk budget available?
  ▼
[Strategy Family Concentration Check]
  │ Would adding this strategy exceed the family limit (3 per ST type)?
  ▼
[Activation Decision]
  │ All checks pass → activate strategy
  │ SC-15 Audit record; L17 notification; Telegram alert
  └── SC-13 Monitoring begins for new strategy
`

---

### SP-06 — Monitoring Pipeline

**Purpose:** Provides continuous monitoring of all active strategies.

**Trigger:** Continuous during trading sessions; session-end batch.

**Flow Diagram:**

`
SP-06: MONITORING PIPELINE
═══════════════════════════

[Every 30 Seconds: Active Session]
  ├── SC-13: Update session P&L per strategy
  ├── SC-13: Check session drawdown thresholds
  └── SC-17: Update SEHS component for Monitoring Engine

[Every 5 Minutes]
  ├── SC-13: Check signal generation rate
  └── SC-13: Regime alignment check

[Daily: Session End]
  ├── SC-09: Update rankings based on today's outcomes
  ├── SC-13: Compute rolling metrics (30-session Sharpe, win rate)
  ├── SC-18: Generate session strategy summary report
  └── SC-16: Analytics update

[Alert Generation]
  │ WARNING: approaching threshold → logged; dashboard update
  │ ALERT: threshold breached → Telegram notification
  └── CRITICAL: governance action required → immediate escalation
`

---

### SP-07 — Learning Pipeline

**Purpose:** Processes strategy performance outcomes through the Learning Engine for model and parameter updates.

**Trigger:** Each closed trade; session end.

**Flow Diagram:**

`
SP-07: LEARNING PIPELINE
═════════════════════════

[Closed Trade Outcome from L12 TradeMonitoring]
  │ Entry price, exit price, P&L, strategy, regime, MAE, MFE
  ▼
[L13 LearningEngine]
  │ Update win rate and payoff ratio for strategy
  │ Update regime-specific performance record
  │ Detect performance regime: improving / stable / declining
  ▼
[L14 PerformanceAnalytics]
  │ DrawdownAnalyzer: update strategy drawdown profile
  │ WalkForwardTester: update OOS performance validation
  ▼
[SC-09 Ranking Engine]
  │ Rankings updated with new performance data
  ▼
[SC-11 Evolution Engine]
  │ Check: does learning signal warrant evolution proposal?
  │ Declining performance + specific exit rule failure → evolution candidate
  ▼
[SC-03 Repository]
  └── Learning outcomes stored; version history updated
`

---

### SP-08 — Evolution Pipeline

**Purpose:** Implements the full strategy evolution workflow from trigger to new version activation.

**Trigger:** SC-11 Evolution Engine detects evolution trigger.

**Flow Diagram:**

`
SP-08: EVOLUTION PIPELINE
══════════════════════════

[Evolution Trigger]
  │ Performance decline; learning signal; governance direction
  ▼
[SC-11 Evolution Engine: Diagnosis]
  │ Is decline from parameter drift? → Parameter evolution
  │ Is decline from rule weakness? → Rule evolution
  │ Is decline structural? → Major version evolution
  ▼
[SC-06 Optimizer: Evolution Optimization]
  │ Optimize proposed changes on recent data + OOS validation
  │ OOS must improve vs current version
  ▼
[SC-08 Evaluator: Comparative Evaluation]
  │ New version vs current version on all metrics
  │ New version must improve by >= 10% on primary metric
  ▼
[SC-14 Governance: Evolution Approval]
  │ Operations Lead reviews proposal
  │ Approve / Reject / Request more evidence
  ▼
[SC-19 Version Manager: Version Increment]
  │ MINOR version for parameter evolution
  │ MAJOR version for structural evolution
  ▼
[SC-10 Selection Engine]
  │ Old version → DEPRECATED
  └── New version → ACTIVE
`

---

### SP-09 — Governance Pipeline

**Purpose:** Implements the governance review and compliance cycle for all Strategy Engine activities.

**Trigger:** Session end; approval request; governance schedule.

**Flow Diagram:**

`
SP-09: GOVERNANCE PIPELINE
═══════════════════════════

[Session End / Governance Trigger]
  ▼
[SC-14 Governance Manager: Event Collection]
  │ Collect: strategy state transitions, overrides, alerts, evolution events
  ▼
[SC-15 Audit Manager: Audit Report]
  │ Generate audit summary for the session
  ▼
[SC-12 Retirement Manager: Retirement Evaluation]
  │ Check all active strategies against retirement triggers
  ▼
[SC-18 Reporting Manager: Governance Report]
  │ Generate full governance report
  │ Deliver via Telegram and dashboard
  ▼
[Human Review Queue]
  │ Items requiring human acknowledgment flagged
  └── Acknowledgment tracked; unacknowledged items escalated
`

---

### SP-10 — Reporting Pipeline

**Purpose:** Produces and delivers all strategy reports on schedule.

**Trigger:** Session end (primary); weekly and monthly schedule; on-demand.

**Flow Diagram:**

`
SP-10: REPORTING PIPELINE
══════════════════════════

[Report Trigger]
  ▼
[SC-18 Reporting Manager: Data Gathering]
  │ From: SC-09 Rankings; SC-13 Monitoring; SC-16 Analytics; SC-14 Governance
  ▼
[Report Assembly]
  ├── Session report: active strategies, P&L, signal count
  ├── Governance report: events, overrides, alerts
  ├── Analytics report: rankings, correlation, alpha decay
  └── Status report: SEHS, component health
  ▼
[Delivery]
  ├── Telegram: operator summary (< 10 min post-session)
  ├── Dashboard: full report (L17 ControlTower)
  └── Governance queue: detailed report (reviewer acknowledgment required)
`

---

### SP-11 — Archive Pipeline

**Purpose:** Archives all strategy records at session end and upon strategy retirement.

**Trigger:** Session end; strategy retirement.

**Flow Diagram:**

`
SP-11: ARCHIVE PIPELINE
════════════════════════

[Archive Trigger]
  ▼
[SC-03 Repository: Session Artifact Commit]
  │ Write session performance records for all active strategies
  │ Write monitoring event log
  │ Write governance events
  ▼
[SC-15 Audit Manager: Chain Closure]
  │ Close session audit chain
  │ Compute session chain integrity hash
  ▼
[Archive Validation]
  │ Read-back verification: 5 random records checked
  │ PASS: archive confirmation
  └── FAIL: immediate alert; archive integrity investigation
`

---

## PART VII — STRATEGY QUALITY FRAMEWORK

### 7.0 Quality Framework Purpose

The Strategy Quality Framework defines how the Strategy Engine measures the quality of strategies and of the Strategy Engine itself. Quality is not subjective — it is computed from defined metrics and dimensions.

The Framework defines 13 Strategy Quality Dimensions (SQD) that compose the Strategy Quality Score (SQS). Every strategy has an SQS that reflects its current measured quality. The SQS governs whether a strategy is eligible for activation, triggers evolution, or faces retirement.

---

### 7.1 Strategy Quality Dimensions

**SQD-01 — Correctness (Weight: 0.18)**

*Definition:* The degree to which the strategy's signals and rules correctly implement the stated hypothesis. A strategy is correct if it actually does what it claims to do.

*Measurement:* Signal-to-outcome correlation; does the signal predict the direction claimed? Back-tested accuracy on signal direction.

*Target:* Signal accuracy >= 55% (significantly above random for a directional signal).

---

**SQD-02 — Robustness (Weight: 0.15)**

*Definition:* The degree to which the strategy's performance is stable across parameter perturbations, time periods, and market conditions. A robust strategy does not depend on finding the perfect parameter setting.

*Measurement:* Performance degradation under ±20% parameter perturbation; OOS Sharpe / IS Sharpe ratio; regime performance variance.

*Target:* OOS Sharpe >= 0.5 x IS Sharpe; performance degradation < 30% under parameter perturbation.

---

**SQD-03 — Consistency (Weight: 0.12)**

*Definition:* The degree to which the strategy delivers consistent performance across sessions and periods, rather than having a few exceptional periods that mask poor average behavior.

*Measurement:* Standard deviation of rolling 30-session Sharpe; proportion of sessions with positive return; consistency score = 1 - (StdDev Sharpe / Mean Sharpe).

*Target:* Positive sessions >= 55%; consistency score >= 0.60.

---

**SQD-04 — Generalization (Weight: 0.10)**

*Definition:* The degree to which the strategy performs well on unseen data. Generalization is the antidote to overfitting.

*Measurement:* Walk-forward test OOS/IS ratio; Monte Carlo P10 Sharpe; cross-period performance.

*Target:* WFT OOS/IS ratio >= 0.50; Monte Carlo P10 Sharpe >= 0.30.

---

**SQD-05 — Adaptability (Weight: 0.10)**

*Definition:* The degree to which the strategy adapts successfully to changing market conditions. A highly adaptable strategy performs across multiple regimes.

*Measurement:* Proportion of market regimes in which the strategy is profitable; performance stability across regime transitions.

*Target:* Profitable in >= 3 of 5 regimes; performance standard deviation across regimes < 1.5x.

---

**SQD-06 — Stability (Weight: 0.08)**

*Definition:* The degree to which the strategy's parameters and structure remain appropriate over time without requiring frequent evolution.

*Measurement:* Parameter drift rate (how often do optimal parameters shift significantly?); strategy version increment frequency; evolution cycle length.

*Target:* Parameter recalibration no more frequent than quarterly for a stable strategy.

---

**SQD-07 — Explainability (Weight: 0.08)**

*Definition:* The degree to which the strategy's signals, decisions, and outcomes can be explained in plain language with reference to its rules and the market conditions at the time.

*Measurement:* Is every signal traceable to a specific rule? Is every rule traceable to a specific hypothesis? Completeness of explanation chain.

*Target:* 100% of signals traceable to rules; 100% of rules traceable to hypothesis.

---

**SQD-08 — Profitability (Weight: 0.08)**

*Definition:* The degree to which the strategy generates positive risk-adjusted returns net of all transaction costs.

*Measurement:* Sharpe ratio (primary); net P&L after all costs; Information Ratio vs benchmark.

*Target:* Sharpe > 0.8; net positive P&L over any 30-session rolling period.

---

**SQD-09 — Risk Efficiency (Weight: 0.07)**

*Definition:* The degree to which the strategy efficiently uses its risk budget to generate returns. A risk-efficient strategy generates more return per unit of risk than an inefficient one.

*Measurement:* Calmar ratio (return / max drawdown); Sortino ratio; capital efficiency (P&L per unit of capital deployed).

*Target:* Calmar > 1.0; Sortino > 1.5.

---

**SQD-10 — Scalability (Weight: 0.05)**

*Definition:* The degree to which the strategy can be scaled to larger capital allocations without significant performance degradation due to market impact.

*Measurement:* Performance at 1x, 2x, 5x capital (simulated); liquidity utilization rate.

*Target:* Performance at 2x capital within 20% of 1x performance.

---

**SQD-11 — Maintainability (Weight: 0.03)**

*Definition:* The degree to which the strategy can be maintained, monitored, and governed efficiently over time.

*Measurement:* Governance overhead (hours per month); documentation completeness; monitoring complexity.

*Target:* Strategy documentation fully complete; no custom monitoring requirements beyond standard SC-13 monitoring.

---

**SQD-12 — Auditability (Weight: 0.02)**

*Definition:* The degree to which every strategy state, decision, and evolution step is fully auditable.

*Measurement:* Audit chain completeness; proportion of state changes with complete audit records.

*Target:* 100% audit coverage; hash chain intact.

---

**SQD-13 — Operational Reliability (Weight: 0.02)**

*Definition:* The degree to which the strategy operates without system errors, crashes, or processing failures.

*Measurement:* Signal generation error rate; exception rate during strategy execution; recovery time.

*Target:* Signal generation error rate < 0.1%; recovery time < 2 minutes for any processing error.

---

### 7.2 SQS Formula and Tiers

**SQS = 0.18*C + 0.15*R + 0.12*Co + 0.10*G + 0.10*A + 0.08*St + 0.08*E + 0.08*P + 0.07*RE + 0.05*Sc + 0.03*M + 0.02*Au + 0.02*Op**

where: C=Correctness, R=Robustness, Co=Consistency, G=Generalization, A=Adaptability, St=Stability, E=Explainability, P=Profitability, RE=Risk Efficiency, Sc=Scalability, M=Maintainability, Au=Auditability, Op=Operational Reliability

All weights sum to 1.00. All dimension scores in [0.0, 1.0].

| Tier       | SQS Range    | Meaning                                                     |
|------------|--------------|-------------------------------------------------------------|
| EXCELLENT  | 0.85–1.00    | Strategy at peak quality; eligible for increased allocation |
| GOOD       | 0.70–0.84    | Strategy performing well; no action required                |
| ACCEPTABLE | 0.55–0.69    | Strategy functional; monitor closely                        |
| MARGINAL   | 0.35–0.54    | Strategy degraded; evolution review triggered               |
| FAILED     | 0.00–0.34    | Strategy failing; retirement candidate                      |

---

### 7.3 SQS Response Protocol

| SQS Tier   | IIOS Response                                                          |
|------------|------------------------------------------------------------------------|
| EXCELLENT  | No restrictions; consider increased allocation                         |
| GOOD       | No restrictions; standard monitoring                                   |
| ACCEPTABLE | Monitoring heightened; investigate any dimension below 0.55            |
| MARGINAL   | Evolution review mandatory within 5 sessions; reduced allocation       |
| FAILED     | Immediate retirement evaluation; deactivation pending review           |

---

### 7.4 Strategy Quality Interaction Effects

**Correctness (SQD-01) → Profitability (SQD-08):** A strategy with poor signal accuracy cannot be profitable without an extreme payoff ratio. When SQD-01 falls below 0.50, SQD-08 should be expected to degrade.

**Robustness (SQD-02) → Consistency (SQD-03):** A non-robust strategy has highly variable performance. When SQD-02 is low, SQD-03 is likely to be low as well.

**Generalization (SQD-04) → Stability (SQD-06):** A strategy that generalizes well does not need frequent recalibration. When SQD-04 is high, SQD-06 should be high.

**Adaptability (SQD-05) → Profitability (SQD-08):** In a multi-regime market, only adaptive strategies maintain profitability across regime changes.

---

## PART VIII — STRATEGY GOVERNANCE

### 8.0 Governance Philosophy

Strategy governance is the structured oversight that ensures the Strategy Engine operates according to its mandate: to produce validated, risk-governed investment strategies that the Decision Engine can trust. Governance is the mechanism that keeps the creative energy of strategy development aligned with the discipline of investment management.

Four governance principles apply:

**SGP-01 — Quality Gates:** Every strategy passes through explicitly defined quality gates before deployment. No strategy bypasses the gates for speed.

**SGP-02 — Version Discipline:** Every change to a strategy is versioned, documented, and reversible. The strategy's history is the evidence base for future decisions.

**SGP-03 — Human Accountability:** Every strategy in production has a designated human accountable for it. AI governance supplements but does not replace human accountability.

**SGP-04 — Learning from History:** Strategy performance history is preserved and studied. Governance decisions improve over time as historical evidence accumulates.

---

### 8.1 Strategy Ownership and Authority

| Authority Level   | Role                         | Scope of Authority                               |
|-------------------|------------------------------|--------------------------------------------------|
| System Owner      | IIOS architect               | Constitutional rules; major version changes      |
| Operations Lead   | Human operator               | Activation, deactivation, evolution approval     |
| Strategy AI       | SC-10 Selection Engine       | Automated selection within defined rules         |
| Risk Engine       | L6/L7                        | Risk budget enforcement; Kill Switch             |
| Audit Authority   | SC-15 Audit Manager          | Audit chain integrity                            |

---

### 8.2 Strategy Naming Standard

**Strategy ID:** STR-{TYPE_CODE}-{YYYYMMDD}-{SEQ:06d}
Example: STR-MOMENTUM-20251112-000001

**Strategy Name:** Must be unique; human-readable; describe the core approach.
Format: {Approach}-{Universe/Sector}-{Signal}-v{Version}
Example: Momentum-LargeCap-CrossSectional-v2.1

**Parameter Set ID:** PRM-{STR_ID}-v{VERSION}
Example: PRM-STR-MOMENTUM-20251112-000001-v2.1

**Backtest Report ID:** BKT-{STR_ID}-{YYYYMMDD}-{SEQ:04d}

**Optimization Record ID:** OPT-{STR_ID}-{YYYYMMDD}-{SEQ:04d}

---

### 8.3 Strategy Versioning Policy

| Change Type                              | Version Increment | Governance Required |
|------------------------------------------|-------------------|---------------------|
| Parameter adjustment (same logic)        | MINOR (1.0 → 1.1) | Operations Lead     |
| Signal rule modification (same hypothesis) | MAJOR (1.x → 2.0) | System Owner review |
| New model component added                | MAJOR             | System Owner review |
| Documentation / metadata correction     | PATCH (1.1 → 1.1.1)| No approval needed |
| Hypothesis change                        | New strategy (v1.0) | Full validation   |

---

### 8.4 Governance Review Schedule

| Review Type               | Frequency   | Scope                                                         |
|---------------------------|-------------|---------------------------------------------------------------|
| Session Review            | Daily       | Active strategies; alerts; signal quality                     |
| Strategy Performance Review | Weekly    | Rolling metrics; rankings; evolution candidates               |
| Evolution Review          | Weekly      | Strategies with declining SQS; evolution proposals           |
| Portfolio Review          | Monthly     | Active strategy set composition; allocation adequacy          |
| Architecture Review       | Quarterly   | Component health; quality evolution; improvement planning     |
| Constitutional Review     | Annually    | Are constitutional rules still appropriate?                   |

---

### 8.5 Override Policy

Every human override of an automated strategy decision must be:

1. **Identified:** operator identity required.
2. **Documented:** reason code required.
3. **Recorded:** audit record created with override ID.
4. **Reviewed:** override appears in governance report within 24 hours.
5. **Evaluated:** patterns of overrides analyzed monthly.

**Override Types:**

| Override Type                    | Authority Level   | Audit Required? |
|----------------------------------|-------------------|-----------------|
| Activate specific strategy       | Operations Lead   | Yes             |
| Deactivate specific strategy     | Operations Lead   | Yes             |
| Change strategy parameter        | Operations Lead   | Yes             |
| Override selection recommendation| Operations Lead   | Yes             |
| Change allocation for strategy   | Operations Lead   | Yes             |
| Change constitutional rule       | System Owner only | Yes, formal GDR |

---

### 8.6 Compliance Framework

| Domain             | Compliance Requirement                                                     |
|--------------------|----------------------------------------------------------------------------|
| SEBI Regulations   | Strategy must not implement illegal trading techniques (front-running, etc.)|
| Broker Requirements| Strategy signals must respect Dhan order type and size limits              |
| IIOS Constitution  | Strategy must comply with all HARD constitutional rules at all times       |
| Audit Requirements | 7-year audit record retention; complete hash chain; reproducible history  |

---

### 8.7 Security Policy

- Strategy definitions are owned by the Strategy Engine. No external system writes strategy state directly.
- Strategy source code and parameter sets are confidential; access restricted to authorized components.
- The hash chain provides tamper detection for all audit records.
- Human override records include operator identity and are non-deletable.

---

### 8.8 Data Retention Policy

| Record Type                  | Detailed Retention | Summary Retention |
|------------------------------|--------------------|-------------------|
| Strategy definitions         | All versions, 7 years | Permanent      |
| Backtest reports             | 7 years            | Permanent         |
| Optimization records         | 5 years            | 7 years           |
| Performance records          | 5 years            | 7 years           |
| Governance reports           | 7 years            | Permanent         |
| Audit records                | 7 years            | Permanent         |
| Retired strategy artifacts   | 7 years full       | Permanent summary |

---

## PART IX — STRATEGY CONSTITUTION

### 9.0 Constitutional Architecture

The Strategy Constitution is the collection of inviolable rules that govern all Strategy Engine operations. Constitutional rules exist at two levels:
- **HARD:** Never violated by any automated action. Violation causes pipeline halt and human escalation.
- **SOFT:** Threshold guidance that triggers alerts and review; can be overridden with governance authorization.

Rules are organized into 15 categories: SC-A through SC-O.

---

### 9.1 SC-A — Strategy Identity Rules

**SC-A-001 [HARD]:** Every strategy must have a unique Strategy ID in the Registry. No strategy operates without a Registry record.

**SC-A-002 [HARD]:** Strategy names must be unique across all strategies in all statuses. A name used by a RETIRED strategy may not be reused without explicit governance approval.

**SC-A-003 [HARD]:** Every strategy must have an explicitly documented hypothesis. A strategy without a hypothesis cannot be registered.

**SC-A-004 [HARD]:** Every strategy must have an assigned taxonomy classification (ST-01 through ST-24). Unclassified strategies are not admissible.

**SC-A-005 [SOFT]:** Every strategy should have a designated human owner accountable for its performance. Ownerless strategies are flagged in governance reports.

**SC-A-006 [HARD]:** Strategy IDs are permanent and never reassigned. A retired strategy's ID is retired with it.

**SC-A-007 [SOFT]:** Strategy metadata must be complete and accurate. Incomplete metadata is a quality flag (SQD-11 maintainability impact).

---

### 9.2 SC-B — Strategy Validation Rules

**SC-B-001 [HARD]:** Every strategy must pass all 8 validation gates (V-01 through V-08) before being promoted from DRAFT to IN_VALIDATION. No gate may be skipped.

**SC-B-002 [HARD]:** A strategy with look-ahead bias detected in validation (V-04) is rejected immediately. Look-ahead bias produces strategies that appear to work in backtesting but cannot work in live trading.

**SC-B-003 [HARD]:** A strategy that violates any HARD constitutional rule is rejected at validation (V-06). Constitutional rules may not be waived for individual strategies.

**SC-B-004 [SOFT]:** A strategy that fails the originality check (V-08 — correlation > 0.80 with existing strategy) should either be differentiated from the existing strategy or merged into it, rather than registered as a separate strategy.

**SC-B-005 [HARD]:** Validation reports are stored permanently in the Repository. No strategy may be re-validated without a new validation report that supersedes the prior one.

**SC-B-006 [SOFT]:** Strategies that barely pass validation gates (e.g., just above minimum thresholds) should be noted in the evaluation report and monitored more closely after activation.

---

### 9.3 SC-C — Strategy Quality Rules

**SC-C-001 [HARD]:** Every strategy must achieve SQS >= 0.55 (ACCEPTABLE tier) to be eligible for activation.

**SC-C-002 [SOFT]:** Every active strategy should maintain SQS >= 0.55. If SQS falls below 0.55 for > 3 consecutive sessions, evolution review is mandatory.

**SC-C-003 [HARD]:** A strategy with SQS < 0.35 (FAILED tier) is immediately suspended pending retirement evaluation.

**SC-C-004 [HARD]:** All 13 SQD dimensions must have assigned scores before SQS is computed. A strategy with missing dimension scores cannot be ranked or selected.

**SC-C-005 [SOFT]:** Critical dimensions (SQD-01 Correctness, SQD-02 Robustness, SQD-04 Generalization) should each be >= 0.55 individually, even if the overall SQS passes. A strategy with a critical dimension failure needs focused attention.

---

### 9.4 SC-D — Optimization Rules

**SC-D-001 [HARD]:** No strategy is deployed with parameters optimized only on in-sample data. Out-of-sample validation is mandatory for all optimized parameters.

**SC-D-002 [HARD]:** The out-of-sample Sharpe must be >= 0.5 x in-sample Sharpe. A greater than 50% degradation out-of-sample is treated as overfitting.

**SC-D-003 [HARD]:** Optimal parameters must not be at the boundary of the search range. Boundary-optimal parameters indicate that the search range was too narrow or that the strategy is overfitting to the extremes.

**SC-D-004 [HARD]:** Monte Carlo permutation test must confirm that strategy performance is statistically significant (p < 0.05 against randomized data).

**SC-D-005 [SOFT]:** Parameter sensitivity curves should be smooth (performance degrades gradually with parameter perturbation). Jagged sensitivity curves indicate overfitting.

**SC-D-006 [SOFT]:** Optimization should be rerun whenever the strategy has been live for > 90 sessions, to check whether optimal parameters have drifted from their original values.

---

### 9.5 SC-E — Learning Rules

**SC-E-001 [HARD]:** Learning outcome data (closed trade results) must be delivered to L13 Learning Engine within 30 seconds of trade close. Delayed learning data is a quality failure.

**SC-E-002 [HARD]:** Parameter changes from learning must be versioned. No learning-driven parameter update occurs without a version increment.

**SC-E-003 [SOFT]:** The Learning Engine's parameter suggestions must be evaluated by SC-06 Optimizer and SC-08 Evaluator before application. Unevaluated learning updates are not applied.

**SC-E-004 [HARD]:** Online learning (real-time parameter adjustment without human oversight) is prohibited in IIOS. All learning-driven changes go through the SP-08 Evolution Pipeline.

**SC-E-005 [SOFT]:** Learning data must be stratified by regime. Learning that is not regime-aware may produce parameters that are optimal for the current regime but harmful in other regimes.

---

### 9.6 SC-F — Evolution Rules

**SC-F-001 [HARD]:** Every evolution proposal must demonstrate out-of-sample improvement before governance approval. An evolution that does not improve OOS performance is not approved.

**SC-F-002 [HARD]:** Every evolution produces a new version. No in-place mutation of an active strategy's logic occurs without version increment.

**SC-F-003 [HARD]:** The prior version is retained in DEPRECATED status for >= 30 sessions after the new version is activated. If the new version proves inferior, rollback is possible.

**SC-F-004 [SOFT]:** A strategy should not be evolved more than twice in a 30-session rolling window. Frequent evolution signals design instability and may indicate the hypothesis is flawed.

**SC-F-005 [HARD]:** MAJOR version evolution (structural change) requires re-running the full Backtesting Pipeline (SP-03) and re-evaluation by SC-08. It is equivalent to developing a new strategy.

**SC-F-006 [SOFT]:** A strategy that has required > 5 MAJOR version evolutions in 2 years should be evaluated for hypothesis retirement — the underlying premise may be fundamentally flawed.

---

### 9.7 SC-G — Version Control Rules

**SC-G-001 [HARD]:** Every strategy version is stored in SC-03 Repository permanently. Version deletion is prohibited.

**SC-G-002 [HARD]:** The version number scheme (MAJOR.MINOR.PATCH) is strictly enforced. Version number regression (e.g., going from 2.0 back to 1.5) is prohibited.

**SC-G-003 [HARD]:** Every version increment is accompanied by a diff record describing exactly what changed between versions.

**SC-G-004 [HARD]:** Rollback is permitted but must be governed: rollback requires human authorization and is recorded in the audit chain.

**SC-G-005 [SOFT]:** Patch increments (documentation only) do not require governance approval, but they are recorded in the version history.

---

### 9.8 SC-H — Governance Rules

**SC-H-001 [HARD]:** The Strategy Engine NEVER creates investment ideas autonomously and submits them directly to the Decision Engine without passing through the full lifecycle (Validation → Backtesting → Optimization → Approval). No shortcut bypasses governance.

**SC-H-002 [HARD]:** The Strategy Engine NEVER executes trades. Trade execution is exclusively the responsibility of L11 Execution Engine, triggered only by L10 Decision Engine decisions. The Strategy Engine provides signals; it does not act on them.

**SC-H-003 [HARD]:** The Strategy Engine NEVER bypasses the Risk Engine. All strategy signals are subject to Risk Engine governance before reaching the Decision Engine.

**SC-H-004 [HARD]:** The Strategy Engine NEVER overrides portfolio constraints. Portfolio constraints from the Portfolio Engine are enforced at the Strategy Engine level.

**SC-H-005 [SOFT]:** Every governance review must be acknowledged within 2 sessions. Unacknowledged governance reports escalate.

**SC-H-006 [HARD]:** Changes to constitutional rules require System Owner authorization and a new Governing Design Record. No constitutional modification without formal GDR.

**SC-H-007 [SOFT]:** Governance reports must be delivered within 60 minutes of session close.

---

### 9.9 SC-I — Monitoring Rules

**SC-I-001 [HARD]:** All active strategies are monitored continuously during trading sessions. Monitoring cannot be disabled for any active strategy.

**SC-I-002 [HARD]:** A WARNING alert must not be suppressed or ignored for more than one session without a documented response.

**SC-I-003 [HARD]:** A CRITICAL alert must trigger immediate human notification and review.

**SC-I-004 [SOFT]:** Monitoring thresholds should be reviewed quarterly. Thresholds that consistently produce false alarms should be adjusted through governance.

**SC-I-005 [HARD]:** If SC-13 Monitoring Engine fails, all active strategies are placed in restricted status until monitoring is restored.

---

### 9.10 SC-J — Auditability Rules

**SC-J-001 [HARD]:** Every strategy state transition produces an audit record before and after the transition. No state change without audit.

**SC-J-002 [HARD]:** Audit records are immutable. No audit record is deleted or modified after creation.

**SC-J-003 [HARD]:** The SHA-256 hash chain is the tamper-detection mechanism. A broken chain is a CRITICAL security event.

**SC-J-004 [HARD]:** Hash chain integrity is verified at session start and included in every governance report.

---

### 9.11 SC-K — Historical Preservation Rules

**SC-K-001 [HARD]:** Historical strategy records are never deleted. All versions, reports, and artifacts are preserved for the full retention period.

**SC-K-002 [HARD]:** Point-in-time reconstruction must be possible: the exact strategy state and parameter set at any historical date must be recoverable.

**SC-K-003 [SOFT]:** Archive read-back verification passes at least 4 of every 5 sessions. Repeated failures trigger full archive audit.

---

### 9.12 SC-L — Security Rules

**SC-L-001 [HARD]:** Strategy definitions and parameter sets are confidential. Access is restricted to authorized Strategy Engine components and authorized human operators.

**SC-L-002 [HARD]:** No external system (outside IIOS) may write strategy state. Strategy definitions are always authored inside IIOS.

**SC-L-003 [HARD]:** Unauthorized modifications to strategy definitions are treated as security events and trigger immediate investigation.

---

### 9.13 SC-M — Human Override Rules

**SC-M-001 [HARD]:** Human overrides are legitimate and explicitly supported. The Strategy Engine does not resist or penalize human overrides.

**SC-M-002 [HARD]:** Every override is accompanied by operator identity, timestamp, and reason. Anonymous overrides are rejected.

**SC-M-003 [SOFT]:** Override patterns that consistently harm outcomes are flagged for governance review and operator coaching.

**SC-M-004 [SOFT]:** Override patterns that consistently improve outcomes are studied for incorporation into automated policy.

---

### 9.14 SC-N — Compliance Rules

**SC-N-001 [HARD]:** No strategy may implement or recommend any activity that violates SEBI regulations or applicable Indian securities law.

**SC-N-002 [HARD]:** Strategy signals must respect all broker-imposed limits (Dhan order size, instrument restrictions).

**SC-N-003 [HARD]:** The Strategy Engine cooperates with the Risk Guardian (L9) as the supreme Kill Switch authority. When the Kill Switch activates, all strategy signal generation halts immediately.

---

### 9.15 SC-O — Constitutional Completeness Rules

**SC-O-001 [HARD]:** The Strategy Constitution is always complete and current. Any IIOS system change that affects strategy behavior requires a constitutional review.

**SC-O-002 [HARD]:** Every HARD rule has a defined escalation path: who is notified if it is violated? What is the recovery procedure?

**SC-O-003 [SOFT]:** Annually, the Strategy Constitution is reviewed in its entirety to confirm that all rules remain appropriate for the current IIOS operating environment.

---

## PART X — STRATEGY READINESS CHECKLIST

### 10.0 Readiness Framework

Before the Strategy Engine is certified for live strategy deployment, all components, data sources, governance mechanisms, and operational procedures must be verified. The Strategy Readiness Checklist is the formal certification that a strategy is ready to generate live signals.

Readiness is assessed at two levels: (1) Strategy Engine readiness (is the engine itself operational?); (2) Individual strategy readiness (is this specific strategy ready to be activated?).

---

### 10.1 Strategy Engine Component Readiness (20 items)

| ID     | Component                     | Check                                                     | Status |
|--------|-------------------------------|-----------------------------------------------------------|--------|
| ER-01  | SC-01 Strategy Registry       | Registry loads; all strategies in correct status          |        |
| ER-02  | SC-02 Strategy Catalog        | All 24 taxonomy types resolvable                         |        |
| ER-03  | SC-03 Strategy Repository     | Repository accessible; read-back passes                  |        |
| ER-04  | SC-04 Strategy Builder        | Builder functional; required fields enforced             |        |
| ER-05  | SC-05 Strategy Validator      | All 8 gates operational                                  |        |
| ER-06  | SC-06 Strategy Optimizer      | Optimization algorithms available; walk-forward ready    |        |
| ER-07  | SC-07 Strategy Simulator      | Simulation modes functional; cost model loaded           |        |
| ER-08  | SC-08 Strategy Evaluator      | All 7 promotion gates checking correctly                 |        |
| ER-09  | SC-09 Ranking Engine          | Rankings computable; regime multiplier active            |        |
| ER-10  | SC-10 Selection Engine        | Selection logic active; capital and risk checks wired    |        |
| ER-11  | SC-11 Evolution Engine        | Evolution triggers monitoring; proposal workflow ready   |        |
| ER-12  | SC-12 Retirement Manager      | Retirement triggers monitoring                           |        |
| ER-13  | SC-13 Monitoring Engine       | Monitoring loops active; alert delivery confirmed        |        |
| ER-14  | SC-14 Governance Manager      | Approval workflows functional; governance report ready   |        |
| ER-15  | SC-15 Audit Manager           | Hash chain intact; audit record creation confirmed       |        |
| ER-16  | SC-16 Analytics Engine        | Analytics computable; correlation matrix updated         |        |
| ER-17  | SC-17 Health Manager          | SEHS computable; component health reporting             |        |
| ER-18  | SC-18 Reporting Manager       | All 6 report types generatable; delivery confirmed      |        |
| ER-19  | SC-19 Version Manager         | Version history queryable; rollback functional          |        |
| ER-20  | SC-20 Metadata Manager        | All metadata fields populated; queries functional       |        |

---

### 10.2 Individual Strategy Readiness — By Phase

**Phase 1: Research Complete**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| RC-01  | Hypothesis document present and explicitly stated               |        |
| RC-02  | Supporting evidence cited (historical data analysis)            |        |
| RC-03  | Instrument universe defined and available                       |        |
| RC-04  | Data requirements identified and feeds confirmed available      |        |
| RC-05  | No duplicate of existing strategy (duplication check passed)    |        |

**Phase 2: Validation Passed**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| VL-01  | V-01 Logical Consistency: PASS                                  |        |
| VL-02  | V-02 Data Availability: PASS                                    |        |
| VL-03  | V-03 Parameter Plausibility: PASS                               |        |
| VL-04  | V-04 Look-Ahead Bias Check: PASS (zero violations)             |        |
| VL-05  | V-05 Minimum Trade Frequency: PASS (>= 20 trades in sample)    |        |
| VL-06  | V-06 Constitutional Compliance: PASS (no HARD rule violation)  |        |
| VL-07  | V-07 Risk Compatibility: PASS (expected MaxDD < 15%)           |        |
| VL-08  | V-08 Originality Check: PASS (correlation < 0.80)              |        |

**Phase 3: Backtesting Approved**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| BT-01  | Backtest: Win Rate >= 50%; Sharpe > 0.8; MaxDD < 15%           |        |
| BT-02  | Walk-Forward Test: OOS Sharpe >= 0.5 x IS Sharpe              |        |
| BT-03  | Cross-Market Test: consistent across multiple instruments/periods|       |
| BT-04  | Monte Carlo: P10 Sharpe >= 0.30                                 |        |
| BT-05  | Sensitivity: performance degradation < 50% under ± 20% perturbation|    |
| BT-06  | Regime Analysis: profitable in >= 2 of 5 regimes              |        |
| BT-07  | Trade count: >= 50 trades in backtest period                   |        |
| BT-08  | Backtest report complete and stored in Repository              |        |

**Phase 4: Simulation Passed**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| SM-01  | Standard simulation with realistic costs: net positive Sharpe  |        |
| SM-02  | Monte Carlo simulation: acceptable distribution of outcomes    |        |
| SM-03  | Stress test simulation: no catastrophic failure in scenarios   |        |
| SM-04  | Liquidity simulation: strategy workable within volume limits   |        |

**Phase 5: Optimization Completed**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| OP-01  | Optimization completed using walk-forward methodology          |        |
| OP-02  | OOS degradation < 50% (no overfitting)                         |        |
| OP-03  | Optimal parameters not at boundary of search range            |        |
| OP-04  | Monte Carlo permutation test p < 0.05                          |        |
| OP-05  | Parameter sensitivity curves smooth (no jagged instability)    |        |
| OP-06  | Optimization report complete and stored in Repository         |        |

**Phase 6: Risk Approved**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| RA-01  | L6 CapitalRisk: strategy fits within available risk budget     |        |
| RA-02  | L7 RiskControl: expected position size within portfolio limits |        |
| RA-03  | L9 RiskGuardian: no Kill Switch conditions would be triggered by this strategy|  |
| RA-04  | Strategy max position size within portfolio concentration limits|       |

**Phase 7: Portfolio Compatible**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| PC-01  | Capital available in Portfolio Engine for this strategy        |        |
| PC-02  | Adding strategy does not breach any portfolio HARD constraints |        |
| PC-03  | Strategy correlation with active strategies < 0.80            |        |
| PC-04  | Strategy family limit not exceeded (< 3 per ST type)          |        |

**Phase 8: Governance Approved**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| GA-01  | SC-08 Evaluation: all 7 promotion gates passed                 |        |
| GA-02  | SC-14 Governance Manager: approval request submitted          |        |
| GA-03  | Operations Lead: reviewed evaluation report                    |        |
| GA-04  | Approval granted and recorded in audit chain                  |        |
| GA-05  | Strategy status promoted to APPROVED in SC-01 Registry        |        |

**Phase 9: Documentation Complete**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| DC-01  | Hypothesis document: complete and current                      |        |
| DC-02  | Strategy definition: all 14 required fields populated          |        |
| DC-03  | Validation report: complete and stored                         |        |
| DC-04  | Backtest report: complete and stored                           |        |
| DC-05  | Optimization report: complete and stored                       |        |
| DC-06  | Metadata: all fields populated including owner and review date |        |
| DC-07  | Version history: version 1.0 registered correctly             |        |

**Phase 10: Monitoring Ready**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| MR-01  | SC-13 monitoring configuration set for this strategy           |        |
| MR-02  | Alert thresholds configured                                    |        |
| MR-03  | Dashboard reporting configured for this strategy              |        |
| MR-04  | Telegram notifications configured for this strategy           |        |

**Phase 11: Operationally Ready**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| OR-01  | Strategy Engine SEHS >= NOMINAL (0.75) at session start        |        |
| OR-02  | Required data feeds confirmed available                         |        |
| OR-03  | Strategy activation confirmed in SC-01 (status = ACTIVE)       |        |
| OR-04  | L17 ControlTower dashboard updated with new strategy           |        |
| OR-05  | Operator Telegram notification of activation delivered         |        |

**Phase 12: Archived Correctly (for RETIRED strategies)**

| ID     | Check                                                            | Status |
|--------|------------------------------------------------------------------|--------|
| AR-01  | All artifacts in SC-03 Repository confirmed                    |        |
| AR-02  | Retirement report complete and stored                          |        |
| AR-03  | Audit chain for strategy lifecycle intact and closed          |        |
| AR-04  | Strategy status = ARCHIVED in SC-01 Registry                  |        |
| AR-05  | Archive read-back verification passed                          |        |

---

### 10.3 Readiness State Machine

`
STRATEGY READINESS STATE MACHINE
══════════════════════════════════

NOT_CHECKED → CHECKING → all phases pass → CERTIFIED
                                                  │ Normal operations
                                                  ▼
                                             [Monitor continuously]
                                                  │ Issue detected
                                                  ▼
                                         DEGRADED (some checks failed)
                                                  │ Issues resolved
                                                  ▼
                                             RE_CERTIFY
                                                  │
                                         [Re-run affected checks]
                                                  │ All pass
                                                  ▼
                                             CERTIFIED
`

---

## SUPPLEMENT A — STRATEGY TAXONOMY REFERENCE

### Supplement A.1 — Complete Type Reference

| Code  | Name               | Primary Signal      | Regime           | IIOS Status | Min History |
|-------|--------------------|---------------------|------------------|-------------|-------------|
| ST-01 | Trend Following    | Direction           | TRENDING         | Primary     | 90 sessions |
| ST-02 | Momentum           | Relative strength   | TRENDING         | Primary     | 60 sessions |
| ST-03 | Mean Reversion     | Extreme deviation   | SIDEWAYS         | Supported   | 60 sessions |
| ST-04 | Breakout           | Level violation     | TRENDING+Trans   | Primary     | 60 sessions |
| ST-05 | Pullback           | Trend retracement   | TRENDING         | Primary     | 60 sessions |
| ST-06 | Volatility         | Vol regime change   | VOLATILE         | Supported   | 90 sessions |
| ST-07 | Market Neutral     | Relative value      | Any              | Planned     | 120 sessions|
| ST-08 | Stat Arb           | Statistical spread  | SIDEWAYS         | Planned     | 120 sessions|
| ST-09 | Pairs Trading      | Cointegrated spread | SIDEWAYS         | Planned     | 120 sessions|
| ST-10 | Sector Rotation    | Sector strength     | Any              | Primary     | 60 sessions |
| ST-11 | Factor Investing   | Multi-factor score  | Any              | Supported   | 90 sessions |
| ST-12 | Growth             | EPS acceleration    | TRENDING_UP      | Future      | N/A         |
| ST-13 | Value              | Intrinsic discount  | SIDEWAYS/DOWN    | Future      | N/A         |
| ST-14 | Dividend           | Yield + payout      | Any              | Future      | N/A         |
| ST-15 | Income             | Cash flow yield     | Any              | Future      | N/A         |
| ST-16 | Macro              | Economic regime     | Any (overlay)    | Supported   | 30 sessions |
| ST-17 | Event-Driven       | Corporate events    | Any              | Supported   | 30 events   |
| ST-18 | Sentiment          | Investor sentiment  | Extreme          | Supported   | 60 sessions |
| ST-19 | News-Based         | NLP news signal     | Any              | Planned     | N/A         |
| ST-20 | AI-Generated       | AI-learned signal   | Any              | Primary     | 90 sessions |
| ST-21 | Hybrid             | Multi-component     | Adaptive         | Primary     | 90 sessions |
| ST-22 | Adaptive           | Regime-calibrated   | Any              | Primary     | 90 sessions |
| ST-23 | Portfolio-Level    | Allocation signal   | Any              | Primary     | 30 sessions |
| ST-24 | Execution          | Cost minimization   | Any              | Planned     | N/A         |

---

### Supplement A.2 — Component Tier Reference

| Tier   | Components                       | Tier Role                                     |
|--------|----------------------------------|-----------------------------------------------|
| 1 — Identity | SC-01, SC-02, SC-03        | Registry, catalog, repository                 |
| 2 — Development | SC-04, SC-05, SC-06, SC-07, SC-08, SC-09 | Build, validate, optimize, simulate, evaluate, rank |
| 3 — Selection + Evolution | SC-10, SC-11, SC-12, SC-13 | Select, evolve, retire, monitor       |
| 4 — Operations | SC-14, SC-15, SC-16, SC-17, SC-18, SC-19, SC-20 | Governance, audit, analytics, health, reporting, version, metadata |

---

### Supplement A.3 — Service-to-Component Mapping

| Service | Primary Components         | Secondary Components              |
|---------|---------------------------|-----------------------------------|
| SS-01   | SC-04, SC-01, SC-20       | SC-15                             |
| SS-02   | SC-05                     | SC-01, SC-15                      |
| SS-03   | SC-06                     | SC-07, SC-08                      |
| SS-04   | SC-07                     | SC-06                             |
| SS-05   | SC-08                     | SC-09, SC-14                      |
| SS-06   | SC-10                     | SC-09, SC-01                      |
| SS-07   | SC-13                     | SC-17                             |
| SS-08   | SC-11                     | SC-06, SC-14                      |
| SS-09   | SC-14                     | SC-15                             |
| SS-10   | SC-15                     | SC-03                             |
| SS-11   | SC-16                     | SC-09, SC-08                      |
| SS-12   | SC-18                     | All components                    |
| SS-13   | SC-03                     | SC-19                             |
| SS-14   | SC-17                     | All components                    |
| SS-15   | SC-19                     | SC-03, SC-01                      |

---

## SUPPLEMENT B — EVALUATION FRAMEWORK

### Supplement B.1 — Promotion Gate Detail

**PG-01 — Win Rate >= 50%**

The win rate measures the proportion of closed trades with positive realized P&L. The 50% floor is the minimum required to establish that the strategy is genuinely profitable. However, win rate alone is insufficient: a strategy with 51% win rate and payoff ratio of 0.5 is unprofitable. Win rate must be evaluated together with payoff ratio.

*Calculation:* Win Rate = (profitable trades) / (total closed trades)
*Measurement period:* Minimum 50 trades from backtesting
*Note:* Trend-following strategies (ST-01, ST-04) often have win rates of 40–50% but survive due to high payoff ratios. These strategies require the payoff ratio gate to compensate.

**PG-02 — Sharpe Ratio > 0.8**

The Sharpe ratio gate ensures that the strategy earns adequate risk-adjusted returns. A Sharpe of 0.8 is a relatively modest threshold — it confirms the strategy generates meaningful excess return per unit of volatility.

*Calculation:* Sharpe = (annualized return - risk-free rate) / annualized volatility
*Measurement period:* Full backtest period (minimum 5 years, 100+ trades)
*OOS requirement:* Out-of-sample Sharpe must be > 0.5 x in-sample Sharpe (minimum 0.4)

**PG-03 — Max Drawdown < 15%**

Maximum drawdown caps the downside risk. A strategy with MaxDD > 15% is too risky for the IIOS capital allocation framework. This gate protects the portfolio from a single strategy's catastrophic loss.

*Calculation:* MaxDD = max (peak - trough) / peak over the full backtest period
*Note:* This is the backtest MaxDD. Live MaxDD may be different. This gate filters obviously risky strategies.

**PG-04 — Trade Count >= 50**

A minimum of 50 trades is required for statistical significance. With fewer trades, performance metrics have wide confidence intervals and cannot be trusted. This gate prevents strategies from passing all gates purely by luck on a small sample.

**PG-05 — OOS Performance (Sharpe OOS > 0.5)**

Out-of-sample performance confirms that the strategy is not overfitting. OOS Sharpe > 0.5 ensures the strategy has real predictive power, not just in-sample curve fitting.

**PG-06 — Regime Coverage >= 2 Regimes**

A strategy that only works in one regime provides narrow coverage and is vulnerable to regime change. Requiring profitability in at least 2 of 5 regimes ensures reasonable robustness.

**PG-07 — Originality (Correlation < 0.80 with Existing)**

Correlated strategies waste capital allocation. If two strategies have return correlation > 0.80, they effectively provide the same exposure. This gate prevents the portfolio from becoming over-concentrated in a single approach dressed in different clothes.

---

## SUPPLEMENT C — OPTIMIZATION TECHNIQUES

### Supplement C.1 — Optimization Philosophy

Strategy optimization is the process of finding the best parameter values for a given strategy design. Optimization is necessary because strategies have tunable parameters (lookback periods, threshold values, stop distances) and the best values are not known a priori.

The central danger in optimization is overfitting: finding parameters that perform perfectly on historical data but fail on new data because the model has memorized noise. IIOS addresses overfitting through three mechanisms: walk-forward optimization (test on data not used in training), Monte Carlo permutation testing (test against randomized data), and parameter stability analysis (prefer smooth, robust parameter landscapes over sharp optima).

---

### Supplement C.2 — Grid Search

**Description:** Systematic evaluation of every combination of parameters within a defined grid.

**When to use:** Few parameters (< 5); when exhaustive search is feasible.

**Strengths:** Comprehensive; no risk of missing the global optimum within the grid; easy to visualize.

**Weaknesses:** Computationally expensive with many parameters (curse of dimensionality); time grows exponentially with number of parameters.

**Grid Resolution Guidance:** Lookback periods: step size = 5 days. RSI thresholds: step size = 5 units. ATR multiples: step size = 0.25. Starting too fine (step = 1) risks overfitting to the grid; too coarse misses the optimal region.

---

### Supplement C.3 — Random Search

**Description:** Sample parameter combinations randomly from the defined search space.

**When to use:** More than 5 parameters; when grid search is too slow.

**Strengths:** Faster than grid for high-dimensional spaces; often finds near-optimal solutions with many fewer evaluations; easy to parallelize.

**Weaknesses:** Does not guarantee finding the global optimum; may miss narrow regions of high performance.

**IIOS Usage:** Used as the first pass for strategies with > 5 parameters, followed by Bayesian refinement around the best regions found.

---

### Supplement C.4 — Bayesian Optimization

**Description:** Uses a probabilistic surrogate model (typically Gaussian Process) to predict the objective function and select the next evaluation point that maximizes information gain.

**When to use:** Expensive objective function; 5–15 parameters; want to minimize number of evaluations.

**Strengths:** Sample-efficient; adapts to the shape of the objective function; balances exploration and exploitation.

**Weaknesses:** Overhead of maintaining the surrogate model; less effective in very high dimensions.

**IIOS Usage:** Primary optimization algorithm for strategies with 5–15 tunable parameters.

---

### Supplement C.5 — Walk-Forward Optimization

**Description:** The standard framework for validating optimization results. The data is split into consecutive in-sample and out-of-sample windows; optimization is performed on the in-sample period and validated on the out-of-sample period.

**Walk-Forward Configuration for IIOS:**
- In-sample window: 365 days (1 year)
- Out-of-sample window: 90 days (1 quarter)
- Step forward: 90 days (non-overlapping OOS windows)
- Minimum windows: 4 (total data minimum: 405 days + 90 days = ~2 years)

**Evaluation Criterion:** OOS Sharpe across all OOS windows must be > 0.5 x average IS Sharpe. If this criterion fails, the strategy is flagged for overfitting review.

**Walk-Forward Efficiency Ratio:** WFE = Mean OOS Sharpe / Mean IS Sharpe. WFE >= 0.50 = acceptable; >= 0.70 = good; >= 0.90 = excellent.

---

### Supplement C.6 — Genetic Algorithm Optimization

**Description:** Evolutionary search algorithm inspired by natural selection. A population of parameter sets evolves over generations, with higher-fitness (higher Sharpe) sets more likely to reproduce.

**When to use:** Complex search space with many local optima; > 15 parameters; when interactions between parameters are important.

**IIOS Application:**
- Population size: 100 parameter sets
- Generations: 50–200 (until convergence)
- Crossover rate: 0.70
- Mutation rate: 0.05
- Selection: tournament selection (prevents premature convergence)
- Fitness function: walk-forward out-of-sample Sharpe

**Overfitting protection in GA:** All fitness evaluations use walk-forward OOS Sharpe (not IS Sharpe). This prevents the GA from evolving toward in-sample perfect fits.

---

### Supplement C.7 — Parameter Stability Analysis

After optimization produces an optimal parameter set, stability analysis confirms that the optimum is robust.

**Perturbation Test:**
For each parameter p_i in the optimal set:
1. Increase p_i by 10%: record objective score.
2. Increase p_i by 20%: record objective score.
3. Decrease p_i by 10%: record objective score.
4. Decrease p_i by 20%: record objective score.

**Stability Criterion:** Objective score under ±20% perturbation must not fall below 50% of the optimal score.

**Visualization:** Plot objective score vs parameter value for each parameter. A smooth, unimodal curve indicates stability. A jagged, multi-modal curve indicates overfitting to a narrow parameter range.

---

### Supplement C.8 — Objective Function Selection

The choice of objective function determines what the optimizer maximizes. Different objective functions produce different types of strategies.

| Objective        | Maximizes                | Best For                                   |
|------------------|--------------------------|--------------------------------------------|
| Sharpe Ratio     | Risk-adjusted return     | Most strategies; balanced risk/return      |
| Calmar Ratio     | Return per max drawdown  | Strategies where drawdown control is critical |
| Sortino Ratio    | Return per downside vol  | Strategies where upside vol is acceptable  |
| Modified Sortino | Sortino with min trade count | When trade frequency matters          |
| Expectancy       | Average return per trade | High-frequency or scalping strategies      |
| Custom Composite | Weighted combination     | When multiple criteria are important       |

IIOS Default: Sharpe Ratio for standard strategies; Calmar Ratio for strategies in high-volatility regimes.

---

## SUPPLEMENT D — VERSION MANAGEMENT

### Supplement D.1 — Version Management Philosophy

Strategy version management is the discipline of tracking every change made to a strategy's definition, parameters, or model. Version management serves three purposes: (1) providing a complete history of how a strategy evolved; (2) enabling rollback when a new version performs worse than the previous one; (3) creating the evidence base for governance reviews of strategy evolution decisions.

---

### Supplement D.2 — Version Numbering Scheme

**Format:** MAJOR.MINOR.PATCH

**MAJOR:** Incremented for structural changes — changes to the strategy's core hypothesis, signal logic, or model architecture. A MAJOR change requires full re-validation (SP-02), re-backtesting (SP-03), and re-optimization (SP-04). MAJOR increments require System Owner review.

**MINOR:** Incremented for parameter optimization changes — the same signal logic with different parameter values. MINOR changes require re-optimization (SP-04) and SC-08 re-evaluation. MINOR increments require Operations Lead approval.

**PATCH:** Incremented for documentation, metadata, or annotation corrections that do not change the strategy's behavior. PATCH increments require no special approval but are recorded in version history.

**Examples:**
- v1.0: Initial strategy registration
- v1.1: Parameter optimization after 90 sessions (lookback 20 → 18, threshold 0.30 → 0.28)
- v1.2: Second parameter optimization cycle (stop distance adjusted)
- v2.0: New signal component added (regime filter using L2 MarketIntelligence signal)
- v2.1: Parameter re-optimization for v2.0 structure
- v2.1.1: Documentation correction (no behavioral change)

---

### Supplement D.3 — Version Lifecycle

`
VERSION LIFECYCLE DIAGRAM
══════════════════════════

Strategy v1.0 → ACTIVE
  │ 90 sessions; performance declining
  │ SC-11 evolution → parameter update
  ▼
Strategy v1.0 → DEPRECATED
Strategy v1.1 → ACTIVE (MINOR bump)

  │ v1.1 active; structural improvement proposed
  │ Full re-validation cycle
  ▼
Strategy v1.1 → DEPRECATED
Strategy v2.0 → ACTIVE (MAJOR bump; full re-validation)

  │ v2.0 poor performance; rollback decision
  ▼
Strategy v2.0 → DEPRECATED
Strategy v1.1 → RE-ACTIVATED (rollback with audit)

  │ Eventually retired
  ▼
Strategy all versions → RETIRED → ARCHIVED
`

---

### Supplement D.4 — Version Diff Record

Every MINOR or MAJOR version increment is accompanied by a version diff record:

- prior_version: the version being superseded
- new_version: the new version number
- change_type: PARAMETER_OPTIMIZATION / RULE_MODIFICATION / MODEL_UPDATE / STRUCTURAL_CHANGE
- parameters_changed: list of changed parameters with old and new values
- rules_changed: description of any rule logic changes
- rationale: why this change was made (performance data, learning signal, governance direction)
- expected_improvement: what improvement is expected (on which metric, by how much)
- validation_report: reference to the new backtest/optimization report

---

### Supplement D.5 — Rollback Procedure

Rollback is the procedure for reverting a strategy from its current version to a prior version. Rollback is legitimate and explicitly supported.

**Rollback Triggers:**
- New version performing significantly worse than prior version after >= 10 live sessions
- New version triggering unexpected risk events
- Governance-directed rollback

**Rollback Process:**
1. Operations Lead requests rollback via SS-15 Version Management Service
2. SC-14 Governance Manager creates rollback request
3. Risk Engine confirms rollback strategy (prior version) is still within risk limits
4. SC-15 Audit Manager creates rollback audit record
5. SC-01 Registry: new version → DEPRECATED; prior version → ACTIVE
6. SC-13 Monitoring: update thresholds to prior version's profile
7. Telegram notification to operator

**Post-Rollback:** The reason for the rollback is studied. The failed new version's artifacts are retained for analysis. A root-cause analysis is conducted and documented.

---

## SUPPLEMENT E — STRATEGY ANTI-PATTERNS

### Supplement E.1 — Anti-Pattern Framework

Strategy anti-patterns are systematic, recurring failures in strategy design or management that consistently harm performance or violate sound investment principles. Unlike bugs, anti-patterns are stable dysfunctional behaviors that must be detected through monitoring and analytics.

---

### SAP-01 — In-Sample Overfitting

**Definition:** A strategy whose backtest performance is significantly better than live performance because its parameters are tuned too precisely to historical data.

**Detection Signals:**
- OOS Sharpe / IS Sharpe < 0.4 (> 60% degradation out-of-sample)
- Strategy performs well in backtesting but poorly in first 30 live sessions
- Many parameters relative to trade count (> 1 parameter per 10 trades)

**Root Cause:** Optimization without walk-forward validation; too many parameters; insufficient data.

**IIOS Response:** SC-06 Optimizer flagged; re-optimization with stricter WFE constraint; reduction in parameter count.

---

### SAP-02 — Hypothesis Abandonment

**Definition:** A strategy that has been evolved so many times that its current form no longer reflects the original hypothesis. The strategy has drifted away from its conceptual foundation.

**Detection Signals:**
- > 4 MAJOR version increments in 2 years
- Signal logic no longer traceable to the original hypothesis
- Strategy behaves in ways inconsistent with the hypothesized market inefficiency

**Root Cause:** Short-term performance optimization without conceptual grounding; multiple small fixes that collectively change the strategy's nature.

**IIOS Response:** Hypothesis review; if original hypothesis is no longer reflected, retire and start fresh.

---

### SAP-03 — Regime Blindness

**Definition:** A strategy deployed in a regime for which it was not designed, because regime detection failed or was bypassed.

**Detection Signals:**
- Strategy active in a regime where its historical performance is negative
- SC-13 Monitoring: regime alignment check fails but strategy is not deactivated
- Strategy performing well historically but failing consistently in live deployment

**Root Cause:** Regime filter not implemented; regime detector misclassifying; override of automated regime deactivation.

**IIOS Response:** Regime filter review; SC-10 Selection Engine regime compatibility check enforced.

---

### SAP-04 — Strategy Hoarding

**Definition:** Keeping too many strategies in the APPROVED or ACTIVE state, spreading capital across strategies that add minimal marginal value.

**Detection Signals:**
- > 8 active strategies with average allocation < 8% each
- Analytics showing > 50% of active strategies have negative attribution contribution
- Strategy correlation matrix showing average correlation > 0.65 across active set

**Root Cause:** Failure to retire underperforming strategies; excessive optimism about strategy recovery.

**IIOS Response:** SC-12 Retirement Manager reviews all active strategies < SQS 0.55; cull strategies not meeting minimum allocation threshold.

---

### SAP-05 — Parameter Drift Blindness

**Definition:** A strategy's optimal parameters have drifted significantly from their calibrated values, but the system has not detected this because monitoring is not tracking parameter stability.

**Detection Signals:**
- Strategy performance declining gradually over > 60 sessions
- Last optimization more than 90 sessions ago
- SQD-06 Stability score falling

**Root Cause:** Optimization not scheduled; monitoring not tracking parameter drift signals.

**IIOS Response:** SC-11 Evolution Engine evaluates parameters; re-optimization triggered.

---

### SAP-06 — Evolution Without Validation

**Definition:** A strategy is evolved (parameters or rules changed) without re-running the validation, backtesting, and optimization pipeline.

**Detection Signals:**
- New version deployed without new backtest report in SC-03
- Version increment without corresponding optimization report
- Governance approval without evaluation report

**Root Cause:** Governance bypass; urgency overriding process.

**IIOS Response:** HARD rule violation (SC-F-001). Immediate rollback. Governance review.

---

### SAP-07 — Orphan Strategies

**Definition:** Strategies that are registered in SC-01 but have no active owner, no recent governance review, and no active monitoring.

**Detection Signals:**
- SC-20 Metadata: owner field empty or departed team member
- SC-14 Governance: no review in > 30 sessions
- SC-13 Monitoring: no monitoring alerts processed (monitoring not running)

**Root Cause:** Team member departure; strategy created for testing and never assigned; governance gap.

**IIOS Response:** Monthly scan for orphan strategies; assign owner or retire.

---

### SAP-08 — Performance Attribution Blindness

**Definition:** Active strategies do not have current attribution — it is unknown which rules and signals are contributing to performance and which are detracting.

**Detection Signals:**
- SC-16 Analytics: no attribution report in > 10 sessions for an active strategy
- SQD-07 Explainability score falling below 0.55
- Governance report incomplete attribution section

**Root Cause:** Attribution pipeline failure; data feed issue; engineering gap.

**IIOS Response:** SP-07 Learning Pipeline and attribution components investigated; attribution restored; retroactive computation for missed sessions.

---

## SUPPLEMENT F — OPERATIONAL RUNBOOK

### Supplement F.1 — Pre-Session Startup Sequence

**Timing:** 08:45 IST — 09:10 IST

**Step-by-Step Strategy Engine Startup:**

1. **08:45 — Engine Startup**
   - SC-17 Health Manager: compute SEHS; must be >= NOMINAL (0.75) for full operations
   - SC-15 Audit Manager: verify hash chain integrity for all active strategies
   - If hash chain broken: HALT; alert operator; human review required

2. **08:50 — Strategy Registry Load**
   - SC-01 Registry: load all ACTIVE strategies
   - SC-02 Catalog: verify taxonomy lookups functional
   - SC-03 Repository: confirm artifact access

3. **08:55 — Monitoring Initialization**
   - SC-13 Monitoring Engine: initialize monitoring loops for all active strategies
   - Configure alert thresholds per active strategy profiles
   - Confirm alert delivery to operator (Telegram) and dashboard (L17)

4. **09:00 — Regime and Selection Sync**
   - L2 MarketIntelligence: load current regime signal
   - SC-09 Ranking Engine: compute session-start rankings with current regime
   - SC-10 Selection Engine: evaluate active strategy set vs current regime
   - If regime changed: run SP-05 Selection Pipeline

5. **09:05 — Governance Confirmation**
   - SC-14 Governance Manager: confirm prior session governance report acknowledged
   - No outstanding unresolved override audit items
   - Active strategy count within configured limits

6. **09:10 — Readiness Certification**
   - SC-17: all 20 component readiness checks passed
   - SEHS >= NOMINAL confirmed
   - CERTIFIED status; Telegram notification to operator

---

### Supplement F.2 — Intraday Monitoring Schedule

| Time              | Action                                                          |
|-------------------|-----------------------------------------------------------------|
| Every 30 seconds  | SC-13: session P&L per strategy; drawdown check                 |
| Every 5 minutes   | SC-13: signal generation rate; regime alignment check           |
| On each signal    | SC-13: signal validity check; constitutional compliance         |
| On Kill Switch    | SC-10: ALL strategy signal generation halts; status → SUSPENDED |
| On regime change  | SC-10: evaluate active strategy set; run SP-05 Selection        |
| On ALERT          | SC-18: Telegram notification to operator                        |
| On CRITICAL       | SC-14: governance escalation; human review required             |

---

### Supplement F.3 — Post-Session Processing Sequence

**Timing:** 15:30 IST — 16:15 IST

1. **15:30 — Signal Generation Stop**
   - SC-13: confirm all signal generation halted for the session

2. **15:35 — Performance Update**
   - L13 Learning Engine receives all closed trade outcomes
   - SC-09 Ranking Engine updates rankings with today's results

3. **15:40 — Evolution Evaluation**
   - SC-11 Evolution Engine: check all active strategies against evolution triggers
   - Flag candidates for evolution review

4. **15:45 — Retirement Evaluation**
   - SC-12 Retirement Manager: check all active strategies against retirement triggers
   - Generate retirement recommendations if thresholds met

5. **15:50 — Analytics Update**
   - SC-16 Analytics Engine: update rolling analytics, correlation matrix, alpha decay

6. **15:55 — Governance Report Generation**
   - SC-14: collect governance events for the session
   - SC-18: generate Session Strategy Summary and Governance Report
   - Deliver via Telegram and dashboard

7. **16:00 — Archive**
   - SP-11 Archive Pipeline: session performance records for all active strategies
   - SC-15: close session audit chain; confirm integrity

8. **16:10 — Health Final**
   - SC-17: final SEHS recorded for session
   - L17 ControlTower: final dashboard update

---

### Supplement F.4 — Incident Response Procedures

**IR-01 — Strategy Signal Quality Failure**

Symptom: Active strategy generating signals that consistently fail to lead to profitable trades (signal accuracy < 45% over 10 consecutive sessions).

Immediate action: SC-13 raises ALERT; notify operator.
Investigation:
  1. Check regime: has the market regime changed from the strategy's intended regime?
  2. Check data feed: is the strategy receiving correct market data?
  3. Check signal logic: has any data feed change broken the signal calculation?
  4. If regime issue: SC-10 evaluates deactivation for the mismatched regime.
  5. If data issue: fix data feed; re-evaluate last N signals.

Resolution: Strategy deactivated if regime incompatible; data feed fixed if data issue.

**IR-02 — SEHS Below FAILED Threshold**

Symptom: SC-17 Health Manager reports SEHS < 0.30.

Immediate action: Strategy Engine enters CRITICAL state; all automated operations (new activations, evolutions) suspended.

Investigation:
  1. Identify which components are contributing to SEHS failure.
  2. Diagnose each failed component.
  3. Apply component-specific recovery.

Recovery time target: < 30 minutes.

**IR-03 — Hash Chain Integrity Failure**

Symptom: SC-15 Audit Manager reports broken hash chain for a strategy.

Immediate action: HALT engine; alert operator.
Investigation:
  1. Identify which audit record breaks the chain.
  2. Determine: data corruption or unauthorized modification?
  3. If corruption: restore from last good backup; replay events.
  4. If unauthorized modification: CRITICAL security incident; System Owner escalation.

Recovery time target: < 2 hours.

**IR-04 — Strategy Validation Pipeline Failure**

Symptom: SC-05 Validator is unavailable; no new strategies can be validated.

Immediate action: Halt all new strategy submissions; currently active strategies unaffected.
Investigation:
  1. Check data feeds used by validation (historical data availability).
  2. Check SC-06 Optimizer (used in V-07 risk compatibility check).

Recovery time target: < 30 minutes; active strategies continue normally.

**IR-05 — Kill Switch Activation — Strategy Engine Response**

Symptom: L9 Risk Guardian activates Kill Switch.

Immediate action:
  1. SC-10 Selection Engine: all active strategies receive SUSPENDED signal.
  2. SC-13 Monitoring Engine: monitoring continues but all signal generation halted.
  3. SC-14 Governance Manager: Kill Switch activation recorded in governance report.
  4. SC-18 Reporting Manager: operator Telegram alert sent immediately.

Resumption:
  1. Kill Switch cleared by Risk Guardian.
  2. Human operator authorization required (double confirmation).
  3. SC-17 SEHS re-evaluated; must be >= NOMINAL.
  4. SC-10 re-evaluates active strategy set for current regime.
  5. Strategies re-activated in priority order per SC-09 rankings.

**IR-06 — Strategy Repository Unavailable**

Symptom: SC-03 Repository not responding; artifact reads failing.

Immediate action: Active strategies continue with cached definitions; no new validations, backtesting, or archive operations.
Investigation: Storage system check; restore from backup if needed.
Recovery time target: < 60 minutes; active strategies unaffected if using cached state.

---

## SUPPLEMENT G — GOVERNING DESIGN RECORDS

### GDR-STR-001 — Strategy Engine Is a Quality Filter, Not a Trading System

**Decision:** The Strategy Engine's primary purpose is to ensure that only high-quality, validated strategies reach the Decision Engine. It is a quality assurance system, not a signal generation system.

**Context:** The Strategy Engine has access to all market data and could theoretically generate signals directly. Should it do so?

**Decision Made:** No. The Strategy Engine validates and manages strategies. Signal generation is the responsibility of the active strategies themselves. The Strategy Engine governs the strategies; the strategies generate signals.

**Rationale:** Mixing quality assurance with signal generation creates a conflict of interest. The same component that creates the signals would also be judging their quality. Separation of concerns produces more trustworthy quality assessment.

---

### GDR-STR-002 — The Strategy Engine Never Executes Trades

**Decision:** The Strategy Engine has no pathway to the Execution Engine (L11). Strategy signals are delivered to the Decision Engine (L10); the Decision Engine decides; the Execution Engine acts. The Strategy Engine's responsibility ends at the signal.

**Rationale:** Trade execution involves real financial transactions. Keeping the Strategy Engine isolated from execution means that a strategy logic error can never accidentally trigger a trade — the Decision Engine and Risk Engine act as required intermediate filters.

---

### GDR-STR-003 — Every Strategy Has a Hypothesis

**Decision:** A strategy without an explicitly documented hypothesis cannot be registered. The hypothesis is the intellectual foundation of the strategy.

**Context:** Could a purely AI-generated strategy operate without a human-interpretable hypothesis?

**Decision Made:** Even AI-generated strategies must have a stated hypothesis. The AI may discover the hypothesis through pattern recognition, but a human-interpretable description must be documented.

**Rationale:** A strategy without a stated hypothesis cannot be evaluated for regime changes, cannot be evolved intelligently, and cannot be explained to governance. The hypothesis is also the warning system: if the market condition that made the hypothesis true no longer exists, the strategy should be retired.

---

### GDR-STR-004 — Out-of-Sample Validation Is Non-Negotiable

**Decision:** No strategy is deployed without out-of-sample validation. In-sample-only performance is treated as hypothetical, not real.

**Context:** Out-of-sample testing takes time and compute. Could it be waived for "obviously good" strategies?

**Decision Made:** Never waived. OOS validation is a HARD rule (SC-D-001).

**Rationale:** The history of trading strategy research is filled with strategies that performed brilliantly in backtesting and failed in live trading because they were overfit to historical data. OOS validation is the single most important protection against this failure mode.

---

### GDR-STR-005 — Evolution Must Improve Out-of-Sample Performance

**Decision:** Strategy evolution is only approved if it improves out-of-sample performance. An evolution that improves in-sample performance but hurts OOS performance is rejected.

**Rationale:** Evolution is valuable only if it makes the strategy better in live trading. In-sample improvement that does not extend to OOS is evidence of overfitting. Evolution that creates overfitting makes the strategy worse, not better.

---

### GDR-STR-006 — Prior Versions Are Preserved for Rollback

**Decision:** When a strategy is evolved to a new version, the prior version is kept in DEPRECATED state for at least 30 sessions. This enables rollback if the new version underperforms.

**Rationale:** New strategy versions may underperform despite passing all quality gates. Having the prior version available for rollback provides a safety net that allows rapid recovery from a failed evolution.

---

### GDR-STR-007 — Human Override Is Legitimate and Studied

**Decision:** Human overrides of automated strategy decisions (activation, deactivation, parameter changes) are first-class operations. They are welcomed, recorded, and studied as learning signals.

**Context:** Should the system resist human overrides to prevent poor decisions?

**Decision Made:** No resistance. Overrides are recorded and studied, not prevented.

**Rationale:** The Strategy Engine operates under significant uncertainty. Human operators often have contextual knowledge that the AI system lacks. Resisting legitimate human judgment is dangerous. However, recording and analyzing overrides provides feedback that improves the automated system over time.

---

### GDR-STR-008 — The Strategy Engine Never Bypasses Risk Engine Governance

**Decision:** Every strategy signal is subject to Risk Engine governance before reaching the Decision Engine. No pathway exists for strategy signals to bypass the Risk Engine.

**Context:** Could the Strategy Engine send signals directly to the Decision Engine for "high-confidence" situations?

**Decision Made:** Never. All signals route through the Risk Engine.

**Rationale:** The Risk Engine protects capital. High-confidence signals from the Strategy Engine may still be dangerous: the strategy might be operating in an unusual market condition, or the Risk Engine may have information (portfolio-level risk) that the Strategy Engine does not. Bypassing the Risk Engine for any reason creates an uncontrolled risk pathway.

---

## SUPPLEMENT H — COMPREHENSIVE GLOSSARY

### H.1 — Strategy Architecture Terms

**Active Strategy:** A strategy currently deployed in IIOS, generating signals, and contributing to portfolio decisions. Active strategies are monitored by SC-13 and tracked by L13 Learning Engine.

**Alpha:** The excess return of a strategy above what is explained by market beta. Alpha represents the investment skill or edge of a strategy.

**Alpha Decay:** The gradual erosion of a strategy's edge over time, as the market inefficiency being exploited becomes less pronounced. All strategies experience some alpha decay; the rate of decay determines how frequently evolution is required.

**Backtesting:** The process of testing a strategy's signal logic against historical market data to evaluate how it would have performed in the past. IIOS backtesting uses realistic transaction costs and avoids look-ahead bias.

**Benchmark:** A reference index against which a strategy's performance is measured. The primary IIOS benchmark is NIFTY50 (BM-01).

**Calmar Ratio:** Annualized Return / Maximum Drawdown. Measures the return per unit of worst-case drawdown risk.

**Cointegration:** A statistical relationship between two price series where the spread between them is mean-reverting over time. Cointegration is the foundation of pairs trading strategies.

**Constitutional Rule:** An inviolable rule governing Strategy Engine operations. HARD rules cannot be violated by any automated action; SOFT rules provide guidance that can be overridden with governance authorization.

**Dead Strategy:** An informal term for a strategy that has been retired but whose hypothesis was sound — it may be reactivatable in the right market environment. Distinguished from a truly failed strategy where the hypothesis was wrong.

**Drawdown:** The decline in strategy NAV from its peak to its lowest subsequent point. Maximum Drawdown (MaxDD) is the largest such decline over a defined period.

**Evolution:** The process of improving a strategy over time by changing its parameters or structure. Evolution is governed — it requires validation and approval before the evolved version is activated.

---

### H.2 — Signal and Model Terms

**Feature:** An indicator or derived combination of indicators prepared for consumption by a machine learning model. Features are normalized, scaled, and selected for predictive value.

**Hypothesis:** A testable proposition about market behavior that, if confirmed, justifies a trading strategy. Every IIOS strategy must have an explicitly documented hypothesis.

**Idea:** A pre-hypothesis intuition about a market inefficiency. Ideas are the starting point of strategy development.

**Indicator:** A mathematical transformation of raw price or volume data designed to expose a market characteristic. Examples: RSI, Moving Average, ATR, MACD.

**In-Sample (IS):** The historical data period used to train and optimize a strategy. In-sample performance measures how well the strategy was fit to the training data.

**Information Ratio:** Active Return / Tracking Error. Measures the consistency of excess return delivery per unit of active risk.

**Look-Ahead Bias:** A validation error where the signal calculation uses data that would not have been available at the time the signal was generated. Look-ahead bias makes backtest results unrealistically favorable.

**MAE (Maximum Adverse Excursion):** The worst intraday loss experienced by a trade from its entry point. Used to evaluate stop-loss placement.

**MFE (Maximum Favorable Excursion):** The best profit experienced by a trade from its entry point. Used to evaluate exit timing.

**Monte Carlo Simulation:** Running many randomized versions of a simulation to understand the distribution of possible outcomes. Used in IIOS to test strategy robustness under randomized conditions.

**Out-of-Sample (OOS):** Historical data that was held back from the training and optimization process. OOS performance measures how well the strategy generalizes to new data.

**Overfitting:** Optimizing a strategy's parameters so precisely to historical data that the strategy has memorized noise rather than learned the underlying signal. Overfit strategies fail on new data.

**Payoff Ratio:** Average Win / Average Loss. A payoff ratio > 1.0 means winning trades are larger than losing trades.

**Regime:** A classification of the market's current condition: TRENDING_UP, TRENDING_DOWN, SIDEWAYS, VOLATILE, UNCERTAIN. Strategy performance varies significantly by regime.

**Regime Filter:** A condition in a strategy definition that specifies which market regimes the strategy is active in. A Momentum strategy might have a regime filter: active only in TRENDING regimes.

**Rule:** A conditional statement mapping indicator conditions to a signal (BUY, SELL, NEUTRAL).

**Sharpe Ratio:** (Return - Risk-Free Rate) / Standard Deviation of Returns. Measures risk-adjusted return.

**Signal:** A directional conclusion derived from one or more indicators: BUY, SELL, or NEUTRAL, typically with a confidence level.

**Sortino Ratio:** (Return - Risk-Free Rate) / Downside Standard Deviation. Like Sharpe but penalizes only downside volatility.

**Spread:** The difference between two related prices (e.g., two correlated stocks). In pairs trading, the spread is monitored for mean-reversion opportunities.

**Strategy:** A complete, self-contained investment methodology specifying entry conditions, exit conditions, position sizing, and regime applicability.

**Strategy Quality Score (SQS):** A composite score from 0.0 to 1.0 measuring the quality of a strategy across 13 dimensions. Governs eligibility for activation and triggers for evolution.

---

### H.3 — Lifecycle and Operations Terms

**Activation:** The transition of a strategy from APPROVED to ACTIVE status, enabling it to generate signals for the current session.

**APPROVED Status:** A strategy that has passed all validation, backtesting, optimization, and governance gates. Ready for activation by the Selection Engine.

**ARCHIVED Status:** The terminal state of a retired strategy. All records are preserved permanently.

**DRAFT Status:** A strategy under development, registered in SC-01 but not yet submitted for validation.

**Evolution Pipeline (SP-08):** The processing pipeline that implements the full strategy evolution workflow from trigger detection to new version activation.

**Governing Design Record (GDR):** A formal document recording a fundamental architectural decision for the Strategy Engine, including alternatives considered and rationale for the choice made.

**Governance Report:** A daily report produced by SC-18 summarizing all strategy lifecycle events, overrides, alerts, and compliance status.

**Hash Chain:** A linked sequence of audit records where each record contains the SHA-256 hash of the previous record, providing tamper detection for the audit history.

**IN_VALIDATION Status:** A strategy that has passed SC-05 validation and is undergoing the full backtesting and optimization pipeline.

**Lifecycle Stage:** One of 17 defined stages in the Strategy Lifecycle, from Idea Generation (SLS-01) through Archive (SLS-17).

**Override:** A human decision to change or reverse an automated strategy management recommendation. All overrides are recorded with operator identity and reason.

**Promotion Gate:** A defined threshold that a strategy must meet before being promoted to APPROVED status. IIOS has 7 promotion gates (PG-01 through PG-07).

**Readiness Certification:** The formal confirmation by SC-17 Health Manager that the Strategy Engine and a specific strategy are ready for live operations.

**Retired Strategy:** A strategy in RETIRED status — no longer generating signals. All positions have been closed; all artifacts are preserved.

**Rollback:** The process of reverting a strategy from a newer version to a prior version. Requires governance authorization and is fully audited.

**Selection Engine (SC-10):** The component responsible for deciding which strategies are active at any given time, based on rankings, regime conditions, and capital availability.

**SEHS (Strategy Engine Health Score):** A composite score measuring the operational health of the entire Strategy Engine across all 20 components.

**SUSPENDED Status:** A strategy temporarily halted due to a Kill Switch activation or risk event. Can be reactivated with human authorization.

**Version Manager (SC-19):** The component responsible for maintaining strategy version history and supporting rollback operations.

**Walk-Forward Efficiency Ratio (WFE):** OOS Sharpe / IS Sharpe. Measures the degree to which in-sample performance extends to out-of-sample. WFE >= 0.50 is required for strategy deployment.

**Walk-Forward Test (WFT):** A rolling in-sample/out-of-sample validation that tests whether a strategy performs consistently across different time periods, not just the one it was optimized on.

---

## APPENDIX — WORKED EXAMPLES

### WE-01 — New Strategy: Idea to Active Status

**Scenario:** IIOS operator observes that Indian large-cap stocks often exhibit strong momentum continuation after breaking out of multi-week ranges with above-average volume. A new strategy is designed to capture this pattern.

**Idea Generation (SLS-01):**
Idea document: "Large-cap breakout with volume confirmation — stocks breaking above 4-week resistance with volume > 1.5x 20-day average tend to continue higher."

**Research (SLS-02):**
Historical scan: 2020–2024, NIFTY50 stocks. Breakout events with volume confirmation: 847 instances. 5-day forward return after signal: positive 62% of the time. Average win: +2.1%; average loss: -0.8%. Preliminary Sharpe: 1.42. Hypothesis SUPPORTED.

**Strategy Design (SLS-04):**
- Signal: price breaks above 20-day high with volume > 1.5x 20-day volume average
- Entry: next session open
- Exit: price closes below 10-day low OR +3% target OR session 10 (time stop)
- Position sizing: equal weight per signal
- Regime filter: TRENDING_UP, TRENDING_DOWN_MODERATE (breakouts can occur in both)
- Parameters: lookback period (10–30 days), volume multiplier (1.2–2.0), stop (8–15 days)

**SC-04 Builder:** All 14 required fields populated. DRAFT registered. ID assigned: STR-BREAKOUT-20251112-000003

**SC-05 Validation (SLS-05):**
- V-01: PASS (entry and exit rules coherent)
- V-02: PASS (all required data available)
- V-03: PASS (parameters within plausible ranges)
- V-04: PASS (no look-ahead bias detected)
- V-05: PASS (preliminary scan shows 847 trades > 20 minimum)
- V-06: PASS (no constitutional violations)
- V-07: PASS (preliminary Max DD estimate 9%)
- V-08: PASS (correlation 0.61 with existing STR-BREAKOUT-20250801-000002 — different enough)

Strategy promoted to IN_VALIDATION.

**Backtesting (SLS-06):**
Walk-Forward Test: IS Sharpe 1.42; OOS Sharpe 0.98. WFE = 0.69 (GOOD). Monte Carlo P10 Sharpe = 0.51. Regime analysis: TRENDING_UP +1.3 Sharpe; TRENDING_DOWN_MODERATE +0.6 Sharpe; SIDEWAYS -0.3 Sharpe (excluded by regime filter — correct).

All 6 backtesting stages: PASS.

**Optimization (SLS-08):**
Bayesian optimization (3 parameters). Optimal: lookback 18 days, volume multiplier 1.6x, time stop 8 days. OOS degradation with ±20%: 18%. PASS. Parameters not at boundary. Monte Carlo permutation p = 0.009 < 0.05. PASS.

**Approval (SLS-09):**
SC-08 Evaluation: SQS = 0.81 (GOOD). All 7 promotion gates: PASS. SC-14 Governance: approval request submitted. Operations Lead reviews. APPROVED. Status: APPROVED.

**Activation (SLS-11):**
Session start: SC-09 ranks strategy #2 for TRENDING_UP regime. Capital available. Risk budget available. SC-10 activates. Status: ACTIVE. L17 updated. Telegram notification sent.

---

### WE-02 — Strategy Evolution: Parameter Optimization

**Scenario:** STR-MOMENTUM-20250115-000001 (v1.0) has been live for 95 sessions. Rolling 30-session Sharpe has declined from 1.2 to 0.7. SC-11 Evolution Engine detects evolution trigger.

**Evolution Trigger:** Gradual performance decline: rolling Sharpe fell from 1.2 to 0.7 over 30 sessions (40% decline). SC-11 flags for parameter evolution.

**Diagnosis:** Performance decline coincides with a change in typical gap duration on NIFTY — the market has been opening with larger gaps, making the 18-day lookback period slightly stale. Parameter evolution (not structural change) is appropriate.

**SC-06 Optimizer:** Walk-forward re-optimization on most recent 180 sessions. Optimal lookback shifts from 18 to 15 days; volume multiplier shifts from 1.6x to 1.7x. OOS Sharpe for new params: 0.94. OOS Sharpe for old params on same period: 0.68. New params improve OOS by 38%.

**SC-08 Evaluator:** Comparative evaluation. New version (v1.1) OOS Sharpe 0.94 vs current (v1.0) OOS Sharpe 0.68. Improvement: +38%. Exceeds 10% minimum. PASS.

**Governance:** SC-14 submits approval request. Operations Lead reviews. MINOR version — no structural change. APPROVED.

**SC-19 Version Manager:** Version v1.1 registered. Diff record: lookback 18 → 15 days; volume multiplier 1.6x → 1.7x.

**SC-10 Selection Engine:** v1.0 → DEPRECATED. v1.1 → ACTIVE. Telegram notification.

**30-Session Validation:** v1.1 rolling Sharpe after 30 sessions: 1.05. Improvement confirmed. Deprecation of v1.0 maintained.

---

### WE-03 — Strategy Retirement

**Scenario:** STR-MEANREV-20240801-000002 (a mean reversion strategy) has been in declining performance for 75 sessions. SC-12 Retirement Manager evaluates.

**Retirement Trigger Assessment:**
- Win rate: 43% over 30-session rolling (< 40% threshold approached). WARNING raised 10 sessions ago.
- Rolling Sharpe (60-session): -0.15 (< 0 trigger). ALERT.
- Regime check: SIDEWAYS regime (the strategy's target) has not occurred in 60 sessions — market has been TRENDING.

**SC-12 Recommendation:** Retirement recommended. Evidence: sustained negative Sharpe; target regime absent for 60 sessions; no evolution path that would fix regime absence.

**SC-14 Governance:** Retirement request submitted. Governance report generated with full evidence. Operations Lead reviews. Approves graceful retirement.

**Retirement Execution:**
- Strategy status: ACTIVE → DEPRECATED (graceful retirement; no forced position close)
- SC-13: monitoring continues until all positions naturally close
- After last position closes: DEPRECATED → RETIRED
- SC-18: retirement report generated
- SC-15: audit chain closed; retirement recorded

**Archive (SLS-17):**
SC-03 Repository: all artifacts confirmed. SC-15: hash chain integrity verified. Status: RETIRED → ARCHIVED.

---

### WE-04 — Constitutional Rule Enforcement

**Scenario:** An automated evolution proposal attempts to deploy a new strategy version (v2.0) without completing the SP-03 Backtesting Pipeline (structural evolution without re-backtesting).

**Rule Violated:** SC-F-001 [HARD]: Every evolution proposal must demonstrate out-of-sample improvement before governance approval. SC-F-005 [HARD]: MAJOR version evolution requires running the full Backtesting Pipeline.

**Detection:** SC-14 Governance Manager checks evolution proposal. Backtest report for v2.0 missing from SC-03 Repository. Constitutional violation detected.

**Immediate Action:** SC-14 rejects the evolution proposal. HARD rule violation recorded in audit chain. SC-15: audit record created with violation ID: CON-VIOL-STR-20251112-000001.

**Escalation:** Operations Lead notified via Telegram. System cannot proceed with v2.0 activation until full SP-03 Backtesting Pipeline is completed for v2.0.

**Resolution:** SP-03 runs for v2.0. Backtesting report stored in SC-03. Evolution proposal resubmitted with complete backtest package. Governance approval granted. v2.0 activated.

---

### WE-05 — Strategy Quality Score Assessment

**Scenario:** End-of-week SQS assessment for STR-MOMENTUM-20251112-000001 (v1.1).

**Dimension Scores:**

| Dimension          | Weight | Score | Contribution |
|--------------------|--------|-------|--------------|
| SQD-01 Correctness     | 0.18  | 0.82  | 0.148        |
| SQD-02 Robustness      | 0.15  | 0.76  | 0.114        |
| SQD-03 Consistency     | 0.12  | 0.71  | 0.085        |
| SQD-04 Generalization  | 0.10  | 0.80  | 0.080        |
| SQD-05 Adaptability    | 0.10  | 0.88  | 0.088        |
| SQD-06 Stability       | 0.08  | 0.85  | 0.068        |
| SQD-07 Explainability  | 0.08  | 1.00  | 0.080        |
| SQD-08 Profitability   | 0.08  | 0.79  | 0.063        |
| SQD-09 Risk Efficiency | 0.07  | 0.90  | 0.063        |
| SQD-10 Scalability     | 0.05  | 0.75  | 0.038        |
| SQD-11 Maintainability | 0.03  | 1.00  | 0.030        |
| SQD-12 Auditability    | 0.02  | 1.00  | 0.020        |
| SQD-13 Op Reliability  | 0.02  | 0.95  | 0.019        |

**SQS = 0.895 — EXCELLENT tier**

**Interpretation:** Strong performance across all dimensions. Adaptability (0.88) is particularly high — the strategy's regime filter is working well. Consistency (0.71) is the lowest dimension — some session variance. No actions required; standard monitoring.

---

### WE-06 — Human Override with Governance Tracking

**Scenario:** Operations Lead overrides the SC-10 Selection Engine's decision to activate STR-MEANREV-20251112-000004, because the operator expects a period of strong trending behavior that would be hostile to mean reversion.

**Override Action:**
- Operator issues override via Telegram: /deactivate-candidate STR-MEANREV-20251112-000004
- Reason: "Anticipating strong TRENDING regime for next 5 sessions based on earnings season calendar — mean reversion strategies not appropriate."

**SC-14 Governance Manager:**
Override recorded: OVR-STR-20251112-000007
- Operator: user_id_001
- Target strategy: STR-MEANREV-20251112-000004
- Override type: PREVENT_ACTIVATION
- Reason: operator-provided text
- Audit record: created

**Outcome — 5 Sessions Later:**
Market was indeed strongly trending. Mean reversion strategies across the active set had negative returns. SC-16 Analytics: operator's override prevented estimated -0.8% drawdown contribution from this strategy.

**Learning:**
SC-14 Governance: override pattern flagged as BENEFICIAL. Override and outcome recorded for monthly override analysis.

---

## DOCUMENT SUMMARY

### Document Metrics

| Metric                         | Value                           |
|--------------------------------|---------------------------------|
| Document Code                  | IIOS-STR-ENG-ARCH-001           |
| Architecture Series            | IIOS Engine Architecture Series |
| Document Number                | 17 of 17                        |
| Status                         | FINAL                           |
| Parts Covered                  | I — X                           |
| Supplements Covered            | A — H                           |
| Appendix                       | 6 Worked Examples               |
| Strategy Types Defined         | 24 (ST-01 through ST-24)        |
| Components Defined             | 20 (SC-01 through SC-20)        |
| Lifecycle Stages               | 17 (SLS-01 through SLS-17)      |
| Strategy Services              | 15 (SS-01 through SS-15)        |
| Processing Pipelines           | 11 (SP-01 through SP-11)        |
| Quality Dimensions (SQD)       | 13 (SQD-01 through SQD-13)      |
| Constitutional Rule Categories | 15 (SC-A through SC-O)          |
| Promotion Gates                | 7 (PG-01 through PG-07)         |
| Anti-Patterns Catalogued       | 8 (SAP-01 through SAP-08)       |
| Governing Design Records       | 8 (GDR-STR-001 through GDR-STR-008) |
| Incident Response Procedures   | 6 (IR-01 through IR-06)         |
| Worked Examples                | 6 (WE-01 through WE-06)         |
| Glossary Terms                 | 70+                             |

---

### Parts Summary

| Part | Title                       | Contents                                               |
|------|-----------------------------|--------------------------------------------------------|
| I    | Strategy Philosophy         | 20-level hierarchy; investment intelligence; 12 strategy paradigms |
| II   | Strategy Taxonomy           | 24 strategy types (ST-01 through ST-24) with full profiles |
| III  | Component Architecture      | 20 components (SC-01 through SC-20); 4-tier organization |
| IV   | Strategy Lifecycle          | 17 stages; state machine; sequence diagram; timing table |
| V    | Strategy Services           | 15 services (SS-01 through SS-15); interface descriptions |
| VI   | Strategy Pipelines          | 11 pipelines (SP-01 through SP-11); full ASCII flow diagrams |
| VII  | Quality Evaluation System   | 13 SQD dimensions; SQS formula; tier table; response protocol |
| VIII | Governance Framework        | Ownership; standards; versioning; review; compliance; security |
| IX   | Strategy Constitution       | 15 rule categories; 110+ rules; HARD/SOFT classification |
| X    | Strategy Readiness Checklist | 12 phases; 60+ items; Readiness State Machine            |

---

### Supplements Summary

| Supplement | Title                           | Contents                                                         |
|------------|---------------------------------|------------------------------------------------------------------|
| A          | Reference Tables                | Taxonomy reference; component tiers; service-component mapping   |
| B          | Evaluation Framework            | All 7 promotion gates (PG-01 through PG-07) with full detail     |
| C          | Optimization Techniques         | Grid, Random, Bayesian, Walk-Forward, Genetic Algorithm, Stability Analysis |
| D          | Version Management              | MAJOR.MINOR.PATCH scheme; lifecycle; diff records; rollback      |
| E          | Anti-Patterns Catalogue         | SAP-01 through SAP-08; detection signals; IIOS responses         |
| F          | Operational Runbook             | Pre-session; intraday; post-session; 6 incident response procedures |
| G          | Governing Design Records        | GDR-STR-001 through GDR-STR-008                                  |
| H          | Comprehensive Glossary          | 70+ terms in 3 categories                                        |

---

### SQS Quick Reference

**Formula:** SQS = sum of (weight_i x score_i) for all 13 dimensions

**Tiers:**

| Tier         | SQS Range  | Meaning                         | Action                          |
|--------------|------------|---------------------------------|---------------------------------|
| EXCELLENT    | 0.85 – 1.00 | Exceptional quality             | Maintain; priority allocation   |
| GOOD         | 0.70 – 0.84 | Strong quality                  | Maintain; standard monitoring   |
| ACCEPTABLE   | 0.55 – 0.69 | Adequate quality                | Monitor closely; improvement plan |
| MARGINAL     | 0.35 – 0.54 | Below acceptable                | Mandatory improvement; flag for evolution |
| FAILED       | 0.00 – 0.34 | Quality failure                 | Governance review; suspension   |

**SQS Dimension Weights (descending):**
1. SQD-01 Correctness: 0.18
2. SQD-02 Robustness: 0.15
3. SQD-03 Consistency: 0.12
4. SQD-04 Generalization: 0.10
5. SQD-05 Adaptability: 0.10
6. SQD-06 Stability: 0.08
7. SQD-07 Explainability: 0.08
8. SQD-08 Profitability: 0.08
9. SQD-09 Risk Efficiency: 0.07
10. SQD-10 Scalability: 0.05
11. SQD-11 Maintainability: 0.03
12. SQD-12 Auditability: 0.02
13. SQD-13 Operational Reliability: 0.02

---

### Promotion Gates Quick Reference

| Gate  | Criterion                  | Threshold          | Type  |
|-------|----------------------------|--------------------|-------|
| PG-01 | Win Rate                   | >= 50%             | HARD  |
| PG-02 | Out-of-Sample Sharpe       | >= 0.8             | HARD  |
| PG-03 | Maximum Drawdown           | <= 15%             | HARD  |
| PG-04 | Walk-Forward Efficiency    | >= 0.50            | HARD  |
| PG-05 | Strategy Quality Score     | >= 0.55 (ACCEPTABLE) | HARD |
| PG-06 | Risk Engine Approval       | Approved           | HARD  |
| PG-07 | Governance Authorization   | Authorized         | HARD  |

All 7 gates must pass. Partial approval does not exist.

---

### Component to Tier Mapping

**Tier 1 — Foundation (immutable during cycle):**
SC-01 Registry, SC-02 Catalog, SC-03 Repository, SC-04 Builder, SC-19 Version Manager, SC-20 Metadata Manager

**Tier 2 — Validation and Development:**
SC-05 Validator, SC-06 Optimizer, SC-07 Simulator, SC-08 Evaluator

**Tier 3 — Active Operations:**
SC-09 Ranking Engine, SC-10 Selection Engine, SC-11 Evolution Engine, SC-12 Retirement Manager, SC-13 Monitoring Engine

**Tier 4 — Governance and Intelligence:**
SC-14 Governance Manager, SC-15 Audit Manager, SC-16 Analytics Engine, SC-17 Health Manager, SC-18 Reporting Manager

---

### Pipeline to Stage Mapping

| Pipeline  | Name                  | Lifecycle Stages It Services                   |
|-----------|-----------------------|------------------------------------------------|
| SP-01     | Research Pipeline     | SLS-02, SLS-03                                 |
| SP-02     | Validation Pipeline   | SLS-05                                         |
| SP-03     | Backtesting Pipeline  | SLS-06                                         |
| SP-04     | Optimization Pipeline | SLS-08                                         |
| SP-05     | Selection Pipeline    | SLS-10, SLS-11                                 |
| SP-06     | Monitoring Pipeline   | SLS-12 (ongoing)                               |
| SP-07     | Learning Pipeline     | SLS-13                                         |
| SP-08     | Evolution Pipeline    | SLS-14                                         |
| SP-09     | Governance Pipeline   | All stages (cross-cutting)                     |
| SP-10     | Reporting Pipeline    | End-of-session, weekly, monthly                |
| SP-11     | Archive Pipeline      | SLS-16, SLS-17                                 |

---

### SEHS Health Tiers Quick Reference

| Tier         | SEHS Range  | Meaning                          | Action                            |
|--------------|-------------|----------------------------------|-----------------------------------|
| OPTIMAL      | 0.90 – 1.00 | Full capability                  | All operations proceed normally   |
| NOMINAL      | 0.75 – 0.89 | Normal operations                | Monitor; investigate low components |
| DEGRADED     | 0.55 – 0.74 | Reduced capability               | Review which components affected  |
| CRITICAL     | 0.30 – 0.54 | Significant capability loss      | Suspend non-critical operations   |
| FAILED       | 0.00 – 0.29 | Unable to operate                | Halt; alert operator; emergency   |

---

### Cross-Layer Integration Summary

| IIOS Layer                    | Strategy Engine Interaction                                      | Direction         |
|-------------------------------|------------------------------------------------------------------|-------------------|
| L2 MarketIntelligence         | Regime signal consumed by SC-09, SC-10                          | L2 → Strategy Eng |
| L3 MetaLearning               | k-NN weight predictions consumed by SC-09 Ranking Engine        | L3 → Strategy Eng |
| L4 OpportunityEngine          | Opportunity set provided to SC-10 Selection Engine              | L4 → Strategy Eng |
| L6 CapitalRiskEngine          | Capital budget per strategy consumed by SC-10                   | L6 → Strategy Eng |
| L7 RiskControl                | Portfolio risk constraints consumed by SC-10                    | L7 → Strategy Eng |
| L9 RiskGuardian               | Kill Switch status consumed by SC-10; governs all activation    | L9 → Strategy Eng |
| L10 DebateAndDecision         | Strategy signals delivered to L10 by active strategies         | Strategy Eng → L10 |
| L13 LearningSystem            | Trade outcomes delivered by L13; consumed by SC-11, SC-12       | L13 → Strategy Eng |
| L14 PerformanceAnalytics      | Performance analytics consumed by SC-16, SC-08                  | L14 → Strategy Eng |
| L15 ResearchLab               | Promotion decisions consumed by SC-05 (final gate)             | L15 → Strategy Eng |
| L17 ControlTower              | SEHS, health, governance reports delivered to L17               | Strategy Eng → L17 |

---

### Service-Layer Interaction Table

| Service    | Name                          | Primary Layer Interaction       |
|------------|-------------------------------|----------------------------------|
| SS-01      | Strategy Research Service     | L1 GlobalIntelligence data       |
| SS-02      | Strategy Hypothesis Service   | L15 ResearchLab                  |
| SS-03      | Strategy Design Service       | Internal (SC-04 Builder)         |
| SS-04      | Strategy Validation Service   | L6 CapitalRiskEngine             |
| SS-05      | Strategy Backtesting Service  | Historical data (L2 via feeds)   |
| SS-06      | Strategy Optimization Service | Walk-forward data                |
| SS-07      | Strategy Approval Service     | L15 ResearchLab; L7 RiskControl  |
| SS-08      | Strategy Selection Service    | L9 RiskGuardian; L3 MetaLearning |
| SS-09      | Strategy Monitoring Service   | L13 LearningSystem               |
| SS-10      | Strategy Learning Service     | L13 LearningSystem               |
| SS-11      | Strategy Evolution Service    | L14 PerformanceAnalytics         |
| SS-12      | Strategy Retirement Service   | SC-08, SC-09                     |
| SS-13      | Strategy Governance Service   | L17 ControlTower                 |
| SS-14      | Strategy Audit Service        | L17 ControlTower                 |
| SS-15      | Version Management Service    | SC-03 Repository; L17 ControlTower |

---

### Service Level Agreements (SLAs)

| Operation                             | SLA Target       | Critical Threshold   |
|---------------------------------------|------------------|----------------------|
| Strategy Registry lookup              | < 10ms           | < 50ms               |
| Signal generation (single strategy)   | < 50ms           | < 200ms              |
| Strategy validation (full run)        | < 60 seconds     | < 5 minutes          |
| Backtest (per year of data)           | < 90 seconds     | < 5 minutes          |
| Walk-Forward Optimization (full)      | < 15 minutes     | < 45 minutes         |
| SQS computation                       | < 5 seconds      | < 30 seconds         |
| Evolution pipeline (full cycle)       | < 20 minutes     | < 1 hour             |
| Daily governance report generation    | < 30 seconds     | < 2 minutes          |
| Audit chain verification              | < 5 seconds      | < 30 seconds         |
| SEHS computation                      | < 2 seconds      | < 10 seconds         |
| Strategy retirement (graceful)        | < 5 minutes      | < 15 minutes         |
| Rollback execution                    | < 2 minutes      | < 10 minutes         |

---

### Architectural Impact Statement

The Strategy Engine occupies the central quality assurance role in the IIOS architecture. Every trade executed by IIOS originates from a strategy that the Strategy Engine validated, optimized, and governs. The quality of the Strategy Engine's decisions — which strategies deserve active status, when they should evolve, and when they should retire — directly determines the long-term performance and risk profile of the entire IIOS system.

Three principles define the Strategy Engine's architecture:

**1. Separation of Quality Assurance from Execution.** The Strategy Engine never executes trades. It evaluates and manages the instruments of trade generation (strategies) but is isolated from the act of trading. This separation ensures that quality judgment is never contaminated by execution urgency.

**2. Evidence Before Action.** Every lifecycle transition in the Strategy Engine is supported by documented evidence: backtests before approval, attribution data before evolution, governance records before override. No automated action bypasses the evidence requirement.

**3. Permanent Institutional Memory.** The hash-chained audit system, the version history, and the permanent archive ensure that the Strategy Engine's decisions accumulate into a growing body of institutional knowledge. Each strategy's history — successes, failures, evolutions — is permanently available for analysis, not discarded.

These three principles, together with the 8 Governing Design Records and the 110+ constitutional rules, create a Strategy Engine that is not merely a tool for finding trading opportunities, but a system of investment governance with the rigor and accountability standards expected of a professional investment operation.

---

### QUICK-START REFERENCE CARD

**Strategy ID Format:** STR-{TYPE_CODE}-{YYYYMMDD}-{SEQ:06d}
**Example:** STR-MOMENTUM-20251112-000001

**Version Format:** MAJOR.MINOR.PATCH
**MAJOR:** Structural change (full re-validation required)
**MINOR:** Parameter change (re-optimization required)
**PATCH:** Documentation only (no approval required)

**Strategy Statuses (in lifecycle order):**
IDEA → RESEARCH → DRAFT → IN_VALIDATION → APPROVED → ACTIVE → DEPRECATED → RETIRED → ARCHIVED
Also: SUSPENDED (Kill Switch hold; resumes after authorization)

**SQS = sum(weight_i x score_i) across 13 SQD dimensions**
EXCELLENT(0.85+) / GOOD(0.70-0.84) / ACCEPTABLE(0.55-0.69) / MARGINAL(0.35-0.54) / FAILED(<0.35)

**SEHS = composite health of all 20 components**
OPTIMAL(0.90+) / NOMINAL(0.75-0.89) / DEGRADED(0.55-0.74) / CRITICAL(0.30-0.54) / FAILED(<0.30)

**WFE = OOS Sharpe / IS Sharpe — minimum 0.50 required for deployment**

**Promotion Gates (all 7 must pass):**
PG-01 WinRate >= 50% / PG-02 OOS Sharpe >= 0.8 / PG-03 MaxDD <= 15%
PG-04 WFE >= 0.50 / PG-05 SQS >= 0.55 / PG-06 Risk Approved / PG-07 Governance Authorized

**Absolute Prohibitions (HARD rules):**
1. No strategy executes trades (GDR-STR-002)
2. No strategy bypasses the validation pipeline (SC-B-001)
3. No strategy registered without a hypothesis (SC-A-003)
4. No structural evolution without SP-03 Backtesting Pipeline (SC-F-001)
5. No strategy signals bypass the Risk Engine (GDR-STR-008)
6. No backtest with look-ahead bias (SC-D-002)
7. All audit records are immutable (SC-L-001)
8. All human overrides are recorded (SC-N-001)

**Document:** IIOS-STR-ENG-ARCH-001 | Version: 1.0 | Status: FINAL
**Prepared for:** IIOS Strategy Engine Architecture Series
**Document series authority:** IIOS Architecture Board

---

## EXTENDED REFERENCE — LIFECYCLE STAGE DETAIL

### Lifecycle Stage Reference: Complete Per-Stage Specification

The following provides complete operational specification for each of the 17 lifecycle stages. This section supplements Part IV by providing granular entry/exit criteria, responsible components, and failure modes for each stage.

---

**SLS-01 — Idea Generation**

Entry criteria: None (always open).
Responsible: Human operator, L1 GlobalIntelligence, L2 MarketIntelligence.
Activities: Observe market anomaly; describe potential inefficiency; draft idea in natural language.
Minimum content: description, hypothesized inefficiency, market type, asset class, initial regime assumption.
Exit to SLS-02 criteria: Idea document with all minimum fields completed; operator judgment that idea warrants research.
Failure modes: Idea too vague to research; asset class not supported by IIOS; idea already covered by existing strategy with SQS >= 0.70 (duplicate creation risk).

---

**SLS-02 — Research**

Entry criteria: Idea document complete; SC-04 Builder has assigned preliminary ID.
Responsible: SC-16 Analytics Engine; SS-01 Strategy Research Service.
Activities: Historical scan of the proposed anomaly; statistical significance testing; literature review of similar strategies; regime distribution analysis.
Required outputs: Historical occurrence count (> 20 required); preliminary win rate; preliminary Sharpe estimate; regime distribution of historical events.
Exit to SLS-03 criteria: Preliminary win rate > 45%; preliminary Sharpe estimate > 0.5; hypothesis confirmed as testable.
Failure modes: Insufficient historical events (< 20); anomaly not statistically significant; market microstructure prevents implementation (bid-ask spread absorbs edge); data unavailable for proposed signals.

---

**SLS-03 — Hypothesis Formulation**

Entry criteria: Research report with positive preliminary results.
Responsible: Human operator; SC-04 Builder; SS-02 Strategy Hypothesis Service.
Activities: Formalize the hypothesis; document the market inefficiency as a testable proposition; specify expected signal conditions; identify regime conditions where hypothesis is expected to hold.
Hypothesis document format: Formal proposition (IF market_condition THEN price_effect expected WITHIN timeframe); specification of when hypothesis is expected to fail; references to supporting research.
Exit to SLS-04 criteria: Hypothesis approved by Operations Lead; formal proposition document complete.
Failure modes: Hypothesis too vague to formalize; hypothesis contradicted by research data; hypothesis not aligned with any supportable market mechanism.

---

**SLS-04 — Strategy Design**

Entry criteria: Formal hypothesis document approved.
Responsible: Human operator; SC-04 Builder.
Activities: Design full strategy specification; define all rules (entry, exit, position sizing); specify parameters with ranges for optimization; specify regime filter; complete all 14 required fields.
14 required strategy fields: strategy_id, type, hypothesis_id, entry_rules, exit_rules, position_sizing_method, regime_filter, supported_timeframes, supported_asset_classes, max_capital_pct, max_corr_active_portfolio, parameter_ranges, version, status.
Exit to SLS-05 criteria: All 14 fields complete; parameter ranges plausible; SC-04 Builder validation pass.
Failure modes: Missing required fields; parameter ranges outside plausible bounds; entry/exit rules contradictory; strategy too similar to existing APPROVED strategies (correlation > 0.80).

---

**SLS-05 — Validation**

Entry criteria: Strategy specification complete; submitted to SC-05 Validator.
Responsible: SC-05 Validator; SS-04 Strategy Validation Service.
Activities: 8-stage sequential validation (V-01 through V-08 as documented in Part III SC-05).
Exit to SLS-06 criteria: All 8 validation checks PASS; status updated to IN_VALIDATION.
Failure modes: Any single check fails; data unavailable; constitutional violation detected; correlation too high with existing strategies.

---

**SLS-06 — Backtesting**

Entry criteria: SC-05 Validator PASS; status IN_VALIDATION.
Responsible: SC-07 Simulator; SS-05 Strategy Backtesting Service; SP-03 Backtesting Pipeline.
Activities: 6-stage SP-03 pipeline run; walk-forward testing (4+ windows); Monte Carlo testing (500 simulations); transaction cost analysis.
Required outputs: Full backtest report stored in SC-03 Repository; WFE calculated; Win Rate, Sharpe, MaxDD for each WFT window; Monte Carlo P5, P10, P50, P90, P95 results.
Exit to SLS-07 (Optional Review) or SLS-08 (Optimization): Backtest complete; results stored; operator reviews results.
Failure modes: Insufficient historical data; data feed errors during backtesting; all WFT windows fail; Monte Carlo shows catastrophic downside (P10 Sharpe < 0); backtest reveals look-ahead bias.

---

**SLS-07 — Review (optional)**

Entry criteria: Backtest results available.
Responsible: Human operator; Operations Lead.
Activities: Human review of backtest results; judgment on whether to proceed to optimization, modify design, or terminate.
Exit criteria: Decision to proceed to SLS-08 Optimization, or return to SLS-04 Design for modification.
This stage has no automated component. It is a human judgment gate.

---

**SLS-08 — Optimization**

Entry criteria: Backtest results reviewed; decision to proceed.
Responsible: SC-06 Optimizer; SS-06 Strategy Optimization Service; SP-04 Optimization Pipeline.
Activities: Choose objective function; select optimization algorithm; run with walk-forward constraint; parameter stability analysis; store optimal parameter set with evidence.
Walk-Forward Optimization constraint: All fitness evaluations use OOS Sharpe only.
Exit to SLS-09 criteria: Optimal parameters found; WFE >= 0.50; parameter stability analysis PASS; optimization report stored in SC-03 Repository.
Failure modes: All parameter combinations produce WFE < 0.50 (fundamental overfitting problem); optimization diverges; data feed unavailable; parameters at boundary after optimization (signals range is wrong).

---

**SLS-09 — Approval**

Entry criteria: Optimization complete; evaluation report ready.
Responsible: SC-08 Evaluator; SC-14 Governance Manager; SC-15 Audit Manager; L15 ResearchLab; L7 RiskControl.
Activities: SC-08 computes SQS; evaluates all 7 promotion gates; L15 ResearchLab review; Risk Engine approval; Governance Manager authorization.
Exit to SLS-10 criteria: All 7 promotion gates PASS; SQS >= 0.55; Risk Engine approval received; Governance authorization recorded.
Failure modes: Any promotion gate fails; Risk Engine rejects on portfolio-level grounds; Governance declines due to strategy concentration or compliance concerns.

---

**SLS-10 — Staging**

Entry criteria: Strategy APPROVED; capital available in budget.
Responsible: SC-10 Selection Engine; SS-08 Strategy Selection Service.
Activities: SC-09 ranks strategy vs all approved strategies for current regime; SC-10 evaluates whether capital is available; configuration loaded for monitoring; dry run (paper signals) to verify operational readiness.
Exit to SLS-11 criteria: Rank sufficient for allocation; capital available; paper signal dry run successful.
Failure modes: Rank too low (capital fully allocated to higher-ranked strategies); regime incompatible at staging time; data feed dry run failures.

---

**SLS-11 — Active**

Entry criteria: Staging complete; SC-10 activation decision.
Responsible: SC-10 Selection Engine; SC-13 Monitoring Engine; active strategies themselves.
Activities: Signal generation each session; performance tracking by SC-13; learning updates from L13; SQS updated regularly; health checks every 5 minutes.
Exit triggers: Kill Switch → SUSPENDED; sustained underperformance → SLS-14 Evolution; retirement criteria met → SLS-16 Retirement.
Failure modes: Data feed outage (handled by degraded mode); signal generation error (circuit breaker halts signals; monitoring alert); regime change (SC-10 may deactivate).

---

**SLS-12 — Learning Phase**

Entry criteria: Strategy ACTIVE with >= 10 live closed trades.
Responsible: L13 LearningSystem; SC-11 Evolution Engine; SP-07 Learning Pipeline.
Activities: Trade outcome attribution; parameter drift signals; model update (if applicable); evolution candidates identified.
This is an ongoing state, not a sequential stage. A strategy can be simultaneously ACTIVE (SLS-11) and in learning phase (SLS-12).
Exit criteria: No formal exit — learning continues for as long as the strategy is active.
Failure modes: Attribution pipeline unavailable; insufficient trades for statistical significance; data quality issues corrupting learning signal.

---

**SLS-13 — Suspended**

Entry criteria: Kill Switch activation; Risk Engine suspension order; governance suspension.
Responsible: SC-10 Selection Engine; SC-13 Monitoring Engine.
Activities: Signal generation halted; monitoring continues; open positions managed to completion by Execution Engine; strategy awaits reactivation authorization.
Exit to SLS-11 criteria: Kill Switch cleared; human operator provides double authorization; SC-17 SEHS >= NOMINAL; SC-10 re-evaluates regime.
Exit to SLS-14 criteria: Governance decides suspended strategy should be evolved before reactivation.
Exit to SLS-16 criteria: Governance decides suspended strategy should be retired.
Failure modes: None — suspension is itself a safety state.

---

**SLS-14 — Evolution Phase**

Entry criteria: SC-11 Evolution trigger; governance approval for evolution.
Responsible: SC-11 Evolution Engine; SC-06 Optimizer; SP-08 Evolution Pipeline.
Activities: Evolution type determination (PARAMETER or STRUCTURAL); run full SP-08 pipeline; create new version; comparative evaluation; governance approval for new version.
Exit to SLS-11 criteria (evolved version ACTIVE): Evolution PASS; new version SQS > old version SQS; governance approved.
Exit to SLS-16 criteria: Evolution attempts fail (WFE < 0.50 on evolved versions); no improvement path found; governance determines retirement is correct.
Failure modes: No parameter combination improves OOS performance; structural evolution exceeds MAJOR bump; data insufficient for evolution evaluation.

---

**SLS-15 — Under Review**

Entry criteria: Governance-directed review; unusual performance event; operator concern.
Responsible: SC-14 Governance Manager; human Operations Lead.
Activities: Full strategy review; all signals paused; deep-dive analytics; investigation of anomalous behavior; determination of root cause.
Exit criteria: Resolution of the review — continue, evolve, or retire.
Failure modes: Root cause undiagnosable; data integrity issues that cannot be resolved.

---

**SLS-16 — Retirement**

Entry criteria: Retirement trigger met; SC-12 recommendation accepted; governance approved.
Responsible: SC-12 Retirement Manager; SC-14 Governance Manager; SP-11 Archive Pipeline.
Activities: Signal generation halted; open positions managed to natural close; retirement report generated; artifacts prepared for archive.
Exit to SLS-17 criteria: All positions closed; retirement report complete; hash chain integrity confirmed.
Failure modes: Positions cannot be closed (illiquid market); archive pipeline unavailable.

---

**SLS-17 — Archive**

Entry criteria: All positions closed; retirement complete.
Responsible: SC-03 Repository; SC-15 Audit Manager; SP-11 Archive Pipeline.
Activities: All artifacts compressed; hash chain closed; immutable archive created; record index updated; storage confirmed.
Terminal state: No exits from ARCHIVED. Strategy remains in archive permanently.
Failure modes: Storage unavailable (recovery: retry; if persistent, manual archive to secondary).

---

## EXTENDED REFERENCE — GOVERNANCE OPERATIONS DETAIL

### Governance Event Taxonomy

All events processed by SC-14 Governance Manager fall into one of the following categories:

| Category        | Event Examples                                                      |
|-----------------|---------------------------------------------------------------------|
| LIFECYCLE       | Strategy registration; validation result; approval; activation; retirement; archive |
| EVOLUTION       | Evolution trigger; evolution proposal; evolution approval; new version activation |
| OVERRIDE        | Human deactivation; human activation; parameter override; override reversal |
| COMPLIANCE      | Constitutional rule violation attempt; compliance check result; regulatory event |
| AUDIT           | Hash chain verification; audit record creation; integrity check result |
| HEALTH          | SEHS computation; component health alert; SEHS tier change           |
| PERFORMANCE     | SQS tier change; promotion gate failure; retirement threshold breach  |
| SECURITY        | Unauthorized modification attempt; access control event; system access |

Each event record contains: event_id, category, timestamp, strategy_id (if applicable), responsible_component, outcome, operator_id (if human action), constitutional_rule_references, next_required_action (if any).

---

### Governance Report Structure

The daily governance report produced by SC-18 Reporting Manager has the following structure:

**Section 1 — Executive Summary:**
- Session date and market conditions
- Active strategy count; any activations or deactivations in the session
- Kill Switch status
- SEHS at session start and end
- Any CRITICAL events

**Section 2 — Strategy Performance:**
- SQS for all active strategies (current vs prior session)
- Any strategies with SQS change > 0.05 (flagged for attention)
- Rolling performance metrics (Sharpe 30-day; Win Rate 30-day; MaxDD 30-day)

**Section 3 — Lifecycle Events:**
- Any strategy state changes during the session
- New strategies in validation or backtesting
- Strategies approaching evolution or retirement thresholds

**Section 4 — Override Log:**
- Any human overrides during the session
- Outcome tracking for prior-session overrides

**Section 5 — Constitutional Compliance:**
- Any HARD rule violation attempts (even if blocked)
- SOFT rule override applications

**Section 6 — Health Report:**
- SEHS breakdown by component
- Any component health alerts

**Section 7 — Upcoming Actions:**
- Strategies scheduled for optimization review
- Strategies scheduled for governance review
- Upcoming compliance obligations

---

### Override Review Protocol

Every human override is tracked through the following protocol:

**T+0:** Override executed; audit record created; Telegram notification sent.

**T+1 session:** First follow-up: SC-16 computes performance comparison — how did the overridden decision compare to what the automated system would have done?

**T+5 sessions:** SC-14 formal override review: what was the outcome? Did the operator's judgment improve or degrade results?

**T+30 sessions (monthly):** Statistical override review: across all overrides in the past 30 sessions, what is the hit rate? Are human overrides adding value or reducing performance? Monthly governance report includes override analytics.

**Outcome coding:**
- BENEFICIAL: override demonstrably avoided a loss or captured a gain
- NEUTRAL: outcome did not differ meaningfully from automated recommendation
- DETRIMENTAL: override led to worse outcome than automated recommendation
- INDETERMINATE: insufficient data to evaluate

This protocol is not about blame — it is about learning. Both beneficial and detrimental overrides generate learning signals that improve the automated system over time.

---

### Compliance Framework

The Strategy Engine operates under the following compliance obligations:

**1. Regulatory Compliance:**
Strategy signals must be consistent with permitted trading activities. Strategies that generate signals for prohibited instruments or prohibited trading patterns (e.g., wash trading, front-running signals) are immediately rejected by SC-05 Validation.

**2. Operational Risk Compliance:**
Maximum position sizes, maximum daily loss limits, and maximum leverage are enforced by L7 RiskControl and L9 RiskGuardian. The Strategy Engine respects these limits as non-negotiable constraints; it never generates signals that, if acted upon, would create a regulatory capital breach.

**3. Record Keeping Compliance:**
All strategy records, backtest results, optimization reports, governance decisions, and audit chains are retained permanently. Retention is not time-limited. Records are immutable after creation. This creates a permanent audit trail for any review.

**4. Model Risk Compliance:**
All machine learning and statistical models used in strategy signal generation are documented with their training data, training period, performance characteristics, and known limitations. No undocumented model is deployed in an active strategy.

**5. Conflict of Interest Compliance:**
The Strategy Engine is designed so that quality assessment (SC-08 Evaluator, SQS computation) is performed by separate components from strategy creation (SC-04 Builder) and activation (SC-10 Selection Engine). No single component both creates and evaluates a strategy.

---

## EXTENDED REFERENCE — STRATEGY TYPE DEPLOYMENT MATRIX

The following matrix maps the 24 strategy types to their optimal regime conditions, typical performance characteristics, and current IIOS deployment priorities.

| Type  | Name                       | Optimal Regimes         | Typical Sharpe Range | Typical MaxDD Range | IIOS Priority |
|-------|----------------------------|-------------------------|----------------------|---------------------|---------------|
| ST-01 | Trend Following            | TRENDING                | 0.8 – 1.8            | 10% – 20%           | HIGH          |
| ST-02 | Mean Reversion             | SIDEWAYS                | 0.6 – 1.4            | 8% – 15%            | HIGH          |
| ST-03 | Momentum                   | TRENDING                | 0.7 – 1.5            | 12% – 22%           | HIGH          |
| ST-04 | Breakout                   | TRENDING (early)        | 0.7 – 1.6            | 10% – 18%           | HIGH          |
| ST-05 | Pairs Trading              | SIDEWAYS                | 0.6 – 1.3            | 5% – 12%            | MEDIUM        |
| ST-06 | Statistical Arbitrage      | ALL                     | 0.5 – 1.2            | 5% – 10%            | MEDIUM        |
| ST-07 | Factor-Based               | ALL                     | 0.6 – 1.4            | 8% – 15%            | HIGH          |
| ST-08 | Event-Driven               | EVENT                   | 0.8 – 2.0            | 10% – 20%           | MEDIUM        |
| ST-09 | Volatility                 | VOLATILE                | 0.5 – 1.1            | 8% – 18%            | MEDIUM        |
| ST-10 | Option Strategies          | VOLATILE / SIDEWAYS     | 0.6 – 1.5            | 8% – 15%            | MEDIUM        |
| ST-11 | Index Arbitrage            | ALL                     | 0.5 – 0.9            | 3% – 8%             | LOW           |
| ST-12 | Seasonal / Calendar        | SEASONAL                | 0.5 – 1.0            | 6% – 12%            | LOW           |
| ST-13 | Regime-Switching           | TRANSITION              | 0.7 – 1.4            | 8% – 15%            | MEDIUM        |
| ST-14 | Machine Learning Signal    | ALL (adaptive)          | 0.6 – 1.6            | 8% – 18%            | HIGH          |
| ST-15 | Deep Learning              | ALL (adaptive)          | 0.5 – 1.5            | 10% – 20%           | MEDIUM        |
| ST-16 | Hybrid Rule + ML           | ALL                     | 0.7 – 1.7            | 8% – 16%            | HIGH          |
| ST-17 | Multi-Timeframe            | TRENDING                | 0.8 – 1.6            | 8% – 15%            | HIGH          |
| ST-18 | Multi-Asset Correlation    | CRISIS / TRANSITION     | 0.5 – 1.2            | 8% – 18%            | MEDIUM        |
| ST-19 | Carry                      | LOW VOLATILITY          | 0.5 – 1.0            | 5% – 12%            | LOW           |
| ST-20 | Relative Value             | SIDEWAYS                | 0.5 – 1.2            | 5% – 10%            | MEDIUM        |
| ST-21 | Market Making              | HIGH LIQUIDITY          | 0.4 – 0.8            | 3% – 8%             | LOW           |
| ST-22 | Execution Algorithm        | ALL                     | N/A (cost reduction) | N/A                 | SUPPORT       |
| ST-23 | Sentiment-Based            | ALL                     | 0.5 – 1.3            | 10% – 20%           | MEDIUM        |
| ST-24 | Alternative Data           | ALL (alpha generation)  | 0.6 – 1.5            | 8% – 18%            | MEDIUM        |

---

## EXTENDED REFERENCE — COMPONENT INTERACTION MATRIX

### Component Data Flow Summary

The following matrix documents which components receive data from which other components, creating a clear picture of the Strategy Engine's internal information architecture.

**SC-01 Registry** receives from: SC-04 (new registrations), SC-05 (validation results), SC-14 (governance decisions). Provides to: all 19 other components (strategy definitions; status).

**SC-02 Catalog** receives from: SC-04 (taxonomy assignments). Provides to: SC-05, SC-08, SC-09, SC-10, SC-16 (taxonomy lookups).

**SC-03 Repository** receives from: SC-06 (optimization reports), SC-07 (backtest artifacts), SC-08 (evaluation reports), SC-11 (evolution artifacts). Provides to: SC-05, SC-06, SC-07, SC-08, SC-11, SC-16 (historical artifacts).

**SC-04 Builder** receives from: human operator; SS-03. Provides to: SC-01 (new strategy records).

**SC-05 Validator** receives from: SC-01 (strategy definition), SC-02 (taxonomy), L6 (risk constraints). Provides to: SC-01 (validation result).

**SC-06 Optimizer** receives from: SC-05 (validated parameters), SC-03 (historical data), historical data feeds. Provides to: SC-03 (optimization reports), SC-07 (optimal parameters for simulation).

**SC-07 Simulator** receives from: SC-06 (optimal parameters), historical data feeds. Provides to: SC-03 (backtest artifacts), SC-08 (simulation results).

**SC-08 Evaluator** receives from: SC-07 (simulation results), SC-06 (optimization reports), L14 (performance analytics). Provides to: SC-09 (SQS, rankings input), SC-14 (approval recommendations).

**SC-09 Ranking Engine** receives from: SC-08 (SQS), L2 (regime), L3 (k-NN weights). Provides to: SC-10 (strategy rankings).

**SC-10 Selection Engine** receives from: SC-09 (rankings), L6 (capital), L7 (risk), L9 (Kill Switch), L4 (opportunities). Provides to: SC-01 (activation/deactivation), active strategies (activation signals).

**SC-11 Evolution Engine** receives from: L13 (trade outcomes), SC-13 (alerts), SC-16 (analytics). Provides to: SC-06 (evolution optimization request), SC-14 (evolution proposals).

**SC-12 Retirement Manager** receives from: SC-16 (analytics), SC-13 (alerts), SC-08 (SQS). Provides to: SC-14 (retirement recommendations), SC-10 (deactivation requests).

**SC-13 Monitoring Engine** receives from: SC-01 (active strategies), L13 (trade outcomes), market data. Provides to: SC-11 (performance alerts), SC-12 (threshold alerts), SC-14 (governance events), L17 (monitoring data).

**SC-14 Governance Manager** receives from: all components (governance events). Provides to: SC-01 (state changes), SC-15 (audit requests), SC-18 (governance report data).

**SC-15 Audit Manager** receives from: all components (audit events). Provides to: SC-14 (audit chain), SC-18 (audit summaries).

**SC-16 Analytics Engine** receives from: SC-13 (performance data), L14 (analytics). Provides to: SC-08, SC-11, SC-12, SC-18 (analytics data).

**SC-17 Health Manager** receives from: all 20 components (health signals). Provides to: SC-14 (health events), L17 (SEHS dashboard).

**SC-18 Reporting Manager** receives from: SC-14, SC-15, SC-16, SC-17 (report data). Provides to: L17 (reports), operator (Telegram notifications).

**SC-19 Version Manager** receives from: SC-11 (new versions), SC-14 (rollback requests). Provides to: SC-01 (version updates), SC-03 (version artifacts).

**SC-20 Metadata Manager** receives from: all components (metadata updates). Provides to: all components (metadata lookups), SC-18 (metadata for reports).

---

## EXTENDED REFERENCE — PIPELINE EXECUTION SPECIFICATIONS

### Pipeline Execution Configuration

The following provides operational configuration detail for each of the 11 Strategy Processing Pipelines, supplementing the ASCII flow diagrams in Part VI.

---

**SP-01 — Strategy Research Pipeline**

Execution context: On-demand, triggered by new idea submission.
Parallelization: Multiple research pipelines may run concurrently (different ideas).
Resource requirements: Historical data access for scan period; moderate compute for statistical tests.
Timeout: 4 hours (most research completes in < 1 hour; 4-hour cap prevents runaway scans).
Error handling: If data feed unavailable, queue research task; retry every 30 minutes for up to 24 hours.
Outputs persisted: Research report in SC-03 Repository; preliminary ID in SC-01 Registry (IDEA status).

---

**SP-02 — Strategy Validation Pipeline**

Execution context: On-demand, triggered by design completion and submission.
Parallelization: One validation per strategy (sequential within strategy; parallel across strategies).
Timeout per stage: V-01 through V-06 = 30 seconds each; V-07 = 2 minutes; V-08 = 1 minute.
Total pipeline timeout: 10 minutes.
Error handling: Timeout on any stage = FAIL for that stage; validation result = FAIL; reason recorded.
Constitutional check: V-06 must never be bypassed; if V-06 throws exception, treat as FAIL, not error.

---

**SP-03 — Backtesting Pipeline**

Execution context: On-demand, post-validation.
Parallelization: Walk-forward windows can be computed in parallel.
Data requirements: Minimum 2 years of clean historical data; maximum 10 years.
Timeout: 2 hours for full WFT (4+ windows); 15 minutes per window.
Transaction cost model: Brokerage: 0.03% per side; Securities Transaction Tax: 0.1% on sell; Exchange fees: 0.00325% per trade; SEBI turnover fee: 0.0001%. All applied to every backtest trade.
Slippage model: Default = 0.05% per side for large-cap NIFTY stocks; 0.15% for mid-cap; 0.30% for small-cap.
Anti-look-ahead check: Data is accessed only with a 1-session lag (no current session data at signal generation time).
Outputs persisted: Backtest report, WFT summary, MC simulation results in SC-03 Repository.

---

**SP-04 — Optimization Pipeline**

Execution context: On-demand (initial deployment) and scheduled (periodic re-optimization).
Parallelization: Bayesian optimization: sequential (surrogate model is shared). GA: population evaluations can be parallelized.
Optimization data window: In-sample = most recent 365 days; out-of-sample = most recent 90 days (held back from IS).
Maximum evaluations: Grid Search = bounded by grid size; Bayesian = 200 evaluations maximum; GA = 100 population x 100 generations = 10,000 evaluations maximum.
Timeout: 3 hours (captures > 99% of optimization runs).
Outputs persisted: Optimal parameter set; optimization report; objective function landscape; parameter sensitivity analysis — all in SC-03 Repository.

---

**SP-05 — Selection Pipeline**

Execution context: Session start (every trading day at 09:00); on regime change.
Parallelization: Strategy rankings computed in parallel across all approved strategies.
Selection algorithm: Ranked by SQS; adjusted by k-NN regime weights from L3; filtered by Kill Switch; filtered by capital availability; filtered by regime compatibility.
Maximum active strategies: Configurable (default: 6); minimum for diversification: 3.
Capital allocation: Equal risk contribution per active strategy, subject to max_capital_pct per strategy.
Timeout: 5 minutes (session start must complete before 09:10 IST).
Outputs: Active strategy set update in SC-01 Registry.

---

**SP-06 — Monitoring Pipeline**

Execution context: Continuous during market hours (09:15 IST to 15:30 IST).
Parallelization: Each active strategy monitored in an independent monitoring thread.
Monitoring intervals: P&L and drawdown: every 30 seconds. Signal rate: every 5 minutes. Regime alignment: every 5 minutes. Hash chain integrity: every 30 minutes.
Alert thresholds (defaults): P&L session loss > 1.5%: WARNING. P&L session loss > 2.5%: CRITICAL. Max drawdown > 10%: WARNING. Max drawdown > 15%: CRITICAL (potential retirement trigger).
Signal generation rate: expected minimum 1 signal per 5 sessions; if no signal for 10 sessions, flag for investigation.
Timeout: No timeout (continuous process); auto-restart on exception with 30-second cooldown.
Outputs: Real-time monitoring data to L17 ControlTower dashboard; alerts via Telegram.

---

**SP-07 — Learning Pipeline**

Execution context: Post-session (15:35 IST daily) and on-demand for attribution updates.
Parallelization: Attribution per strategy computed in parallel.
Attribution granularity: Per signal, per rule, per regime window. Attribution answer: which signals contributed most to performance? Which rules generated profitable vs loss trades?
Minimum trade count for reliable attribution: 20 closed trades. Below this threshold, attribution is recorded but flagged as preliminary (insufficient data).
Timeout: 30 minutes for daily post-session learning.
Learning signal delivery: SC-11 Evolution Engine receives evolution candidates. SC-12 Retirement Manager receives performance summaries.
Outputs: Attribution reports in SC-03 Repository; strategy performance records in L13 database.

---

**SP-08 — Evolution Pipeline**

Execution context: Triggered by evolution recommendation from SC-11.
Parallelization: One active evolution per strategy at a time (prevents conflicting evolution proposals).
Evolution authorization: Operations Lead approval required before SP-08 starts for MINOR bump; System Owner approval required for MAJOR bump.
Full pipeline: Trigger → Diagnosis → Type determination (PARAMETER / STRUCTURAL) → Re-optimization (SP-04) → Comparative evaluation (SC-08) → Governance approval (SC-14) → New version activation (SC-10).
Rollback window: Prior version kept in DEPRECATED status for 30 sessions minimum.
Timeout: 24 hours (must complete within one trading day or be requeued).
Outputs: New version in SC-01 Registry; version diff record in SC-19; evolution report in SC-03.

---

**SP-09 — Governance Pipeline**

Execution context: Continuous (all lifecycle events generate governance records).
Parallelization: Individual event records written in parallel; daily report is sequential.
Governance record SLA: All governance events recorded within 5 seconds of occurrence.
Hash chain update: New audit record appended within 10 seconds of governance record creation.
Daily report generation: 16:00 IST daily (post-session processing complete).
Timeout: No timeout (continuous); report generation: 2-minute timeout.
Outputs: Governance records in SC-14 database; daily report delivered to L17 and Telegram.

---

**SP-10 — Reporting Pipeline**

Execution context: End-of-session (16:00 IST daily); weekly (Fridays); monthly (last Friday of month).
Session report: All active strategies; SQS changes; lifecycle events; overrides; Kill Switch status.
Weekly report: 5-session performance summary; evolution and retirement activity; governance compliance; SQS trends.
Monthly report: 22-session performance; attribution analysis; override effectiveness analysis; strategy portfolio health; upcoming reviews.
Timeout: 5 minutes for session report; 15 minutes for weekly; 30 minutes for monthly.
Delivery: L17 ControlTower dashboard; Telegram for session summaries and critical items.

---

**SP-11 — Archive Pipeline**

Execution context: Triggered by SC-12 retirement completion.
Parallelization: One archive pipeline per retiring strategy; multiple strategies can archive in parallel.
Archive verification: All artifact checksums verified before archive confirmation.
Hash chain closure: SC-15 creates terminal hash record; chain is marked CLOSED.
Archive format: Compressed markdown and structured data; human-readable without specialized tools.
Retention: Permanent. No deletion policy.
Timeout: 30 minutes per strategy.
Outputs: Archived package in SC-03 persistent storage; archive index updated; retirement notification to L17 and Telegram.

---

## EXTENDED REFERENCE — SIGNAL CONTRACT

### Strategy Signal Specification

Every signal generated by an active strategy must conform to the following contract before it is delivered to the Decision Engine (L10).

**Required Signal Fields:**
- signal_id: UUID, unique per signal
- strategy_id: the generating strategy's full ID
- strategy_version: current version of the strategy
- timestamp: precise ISO 8601 timestamp of signal generation
- symbol: the target instrument
- direction: BUY | SELL | NEUTRAL
- confidence: float 0.0 to 1.0
- regime_at_signal: the regime classification active when the signal was generated
- signal_horizon: expected holding period (1-session, 1-week, 1-month)
- entry_conditions: snapshot of the indicator values that triggered the signal
- invalidation_conditions: conditions that would make the signal invalid
- session_number: count of live sessions this strategy has been active

**Signal Validity Rules:**
1. No signal with confidence < 0.35 is delivered (below minimum decision threshold).
2. No signal for an instrument not in the strategy's supported_asset_classes.
3. No signal generated if the strategy's regime_filter does not include the current regime.
4. No signal generated if the Kill Switch is active.
5. All signals are constitutional-compliance-checked by SC-05 before delivery to L10.

**Signal Delivery:**
Signals are delivered via the L17 ControlTower EventBus to L10 DebateAndDecision. The Strategy Engine is the producer; L10 is the consumer. No direct communication channel exists between the Strategy Engine and L11 ExecutionEngine.

---

## EXTENDED REFERENCE — ERROR AND EXCEPTION TAXONOMY

### Strategy Engine Error Categories

The following taxonomy covers all major error and exception types in the Strategy Engine, with standard responses for each.

| Error Code | Category                   | Description                                                       | Standard Response                                      |
|------------|----------------------------|-------------------------------------------------------------------|--------------------------------------------------------|
| SE-001     | Data Feed Unavailable      | Historical or real-time data feed is unresponsive                 | Degrade gracefully; retry 3x; alert if persists        |
| SE-002     | Registry Corruption        | SC-01 Registry data is inconsistent                               | HALT; alert; restore from backup                       |
| SE-003     | Hash Chain Break           | SC-15 detects broken audit chain                                  | HALT; alert; human review required                     |
| SE-004     | Validation Timeout         | SC-05 validation stage exceeds timeout                            | Record FAIL for that stage; continue validation        |
| SE-005     | Optimization Divergence    | SC-06 optimization fails to converge                              | Retry with different algorithm; if 3 failures, record FAIL and alert |
| SE-006     | Backtest Data Gap          | Historical data has gaps > 5 days                                 | Flag gap; if gap in WFT window, skip that window; if > 30% of windows have gaps, FAIL backtest |
| SE-007     | Signal Generation Error    | Active strategy throws exception during signal generation         | Circuit breaker: halt signals; alert operator; attempt restart after 5 minutes |
| SE-008     | Kill Switch Protocol Error | Kill Switch activation/deactivation fails to propagate correctly  | CRITICAL; HALT all signal generation; alert immediately |
| SE-009     | Archive Write Failure      | SP-11 cannot write to archive storage                             | Retry 3x; if persistent, queue for manual archive      |
| SE-010     | Component Health Failure   | SC-17 detects component health < 0.30                             | Alert; if SEHS falls below CRITICAL, suspend operations |
| SE-011     | Governance Record Write Failure | SC-14 cannot write governance record                        | Retry 3x; if persistent, HALT operations (governance integrity at risk) |
| SE-012     | Version Conflict           | SC-19 detects version numbering conflict                          | HALT evolution; alert; human review required           |
| SE-013     | Constitutional Violation Attempt | SC-14 detects HARD rule violation attempt by automated process | BLOCK; record; alert; escalate to System Owner     |
| SE-014     | Memory / Resource Exhaustion | Processing pipeline runs out of memory                          | Checkpoint; retry with reduced data window; alert      |
| SE-015     | Correlation Matrix Failure | SC-16 cannot compute correlation matrix (data quality issue)      | Use cached matrix (max 1-session stale); alert if cache > 1 session old |

---

## EXTENDED REFERENCE — STRATEGY MONITORING DASHBOARD SPECIFICATION

### SC-13 Monitoring Dashboard Data Points

SC-13 Monitoring Engine produces a real-time data stream for the L17 ControlTower dashboard. The following data points are published continuously during market hours:

**Per-Strategy Data:**
- Current status (ACTIVE / SUSPENDED / DEPRECATED)
- Session P&L (INR and %)
- Cumulative live P&L since activation
- Current open positions count and total exposure
- Signals generated this session (total / BUY / SELL / NEUTRAL)
- Signal acceptance rate by L10 DebateAndDecision
- Current SQS and tier
- Regime alignment status (IN / OUT of target regime)
- Sessions since last evolution
- Sessions since last optimization

**Portfolio-Level Data:**
- Active strategy count (current vs maximum configured)
- Portfolio-level correlation: average pairwise correlation of active strategies
- Portfolio P&L total for the session
- Portfolio P&L by strategy contribution
- Kill Switch status (INACTIVE / ACTIVE)
- SEHS current value and tier

**Alert Status Panel:**
- Current active alerts (by severity: CRITICAL / WARNING / INFO)
- Alert history for current session
- Outstanding unacknowledged alerts

**Governance Panel:**
- Governance events today
- Override count today
- Any constitutional violations attempted (blocked)
- Upcoming governance review dates

**Health Panel:**
- All 20 component health scores in a 4-tier grid
- Components with health changes in the last 30 minutes
- SEHS trend (5-session rolling)

---

## EXTENDED REFERENCE — STRATEGY HEALTH INDICATORS

### Health Indicator Reference — Full 20-Component Scoring Guide

SC-17 Health Manager computes an individual health score for each component on a scale of 0.0 to 1.0. The following specifies the scoring criteria for each of the 20 components.

**SC-01 Strategy Registry Health:**
1.00 = all records accessible; registry responsive; no corruption detected.
0.75 = minor performance degradation (queries > 5ms average).
0.50 = some records returning errors; partial access.
0.25 = registry largely unavailable; < 50% of records accessible.
0.00 = complete registry failure; no records accessible.

**SC-02 Strategy Catalog Health:**
1.00 = all taxonomy lookups successful; catalog consistent with registry.
0.75 = minor lookup latency issues (> 10ms average).
0.50 = some taxonomy categories returning inconsistent results.
0.25 = > 30% of taxonomy lookups failing.
0.00 = catalog complete failure; taxonomy unavailable.

**SC-03 Strategy Repository Health:**
1.00 = all artifact reads/writes successful; storage accessible; checksums valid.
0.75 = minor latency issues on artifact reads.
0.50 = some artifacts returning read errors; write operations slow.
0.25 = > 30% of artifact operations failing.
0.00 = repository unavailable; no artifacts accessible.

**SC-04 Strategy Builder Health:**
1.00 = builder accepting strategy definitions; validation logic operational.
0.75 = minor validation delays.
0.50 = some field validation checks failing; builder partially operational.
0.25 = > 50% of builder operations failing.
0.00 = builder completely unavailable.

**SC-05 Strategy Validator Health:**
1.00 = all 8 validation checks operational; validation completing within SLA.
0.75 = V-07 or V-08 showing elevated latency (> 60 seconds).
0.50 = one or two validation checks degraded; validation completing with workarounds.
0.25 = > 3 validation checks unavailable; validation pipeline broken.
0.00 = validator completely unavailable; no strategy can be validated.

**SC-06 Optimizer Health:**
1.00 = optimization algorithms operational; walk-forward constraint active; convergence within SLA.
0.75 = elevated optimization times (> 4 hours for standard run).
0.50 = one optimization algorithm unavailable; fallback in use.
0.25 = all algorithms degraded; optimization severely delayed.
0.00 = optimizer unavailable; no optimization possible.

**SC-07 Simulator Health:**
1.00 = simulation runs completing within SLA; transaction cost model applied; no data gaps.
0.75 = some data feed delays affecting simulation completion time.
0.50 = data gaps affecting some WFT windows; partial results.
0.25 = > 50% of simulation windows failing due to data issues.
0.00 = simulator unavailable; backtesting not possible.

**SC-08 Evaluator Health:**
1.00 = SQS computation completing within SLA; all 13 dimensions active; promotion gate checks operational.
0.75 = one or two SQD dimensions unavailable; SQS estimated with partial data.
0.50 = SQS computation degraded; > 3 dimensions unavailable.
0.25 = SQS computation severely degraded; SQS estimate unreliable.
0.00 = evaluator unavailable; no quality scoring possible.

**SC-09 Ranking Engine Health:**
1.00 = all rankings computing correctly; regime weights from L3 received; rankings updated at session start.
0.75 = L3 regime weights unavailable; using cached weights (< 1 session stale).
0.50 = rankings computed without L3 input; regime weighting absent.
0.25 = ranking computation severely degraded.
0.00 = ranking engine unavailable; selection cannot be performed.

**SC-10 Selection Engine Health:**
1.00 = active strategy set correctly managed; Kill Switch propagating correctly; capital constraints applied.
0.75 = selection process delayed (> 5 minutes at session start).
0.50 = capital constraints unavailable; selection proceeding without full constraints.
0.25 = selection engine severely degraded; incorrect strategy set possible.
0.00 = selection engine unavailable; active strategy set cannot be managed.

**SC-11 Evolution Engine Health:**
1.00 = evolution triggers monitoring correctly; evolution pipeline available; no evolutions overdue.
0.75 = evolution assessment delayed (non-critical; can queue).
0.50 = evolution pipeline partially available; some evolution types unavailable.
0.25 = evolution engine largely unavailable; evolutions queuing.
0.00 = evolution engine unavailable; no evolution possible.

**SC-12 Retirement Manager Health:**
1.00 = retirement triggers monitoring correctly; retirement pipeline available.
0.75 = retirement assessment delayed (non-critical).
0.50 = retirement pipeline partially available.
0.25 = retirement manager largely unavailable.
0.00 = retirement manager unavailable; strategies may not be retiring when they should.

**SC-13 Monitoring Engine Health:**
1.00 = all active strategies monitored; all alert thresholds active; monitoring intervals met.
0.75 = monitoring intervals slightly delayed (> 45 seconds for 30-second checks).
0.50 = one or more active strategies not monitored; partial coverage.
0.25 = > 50% of active strategies not receiving monitoring coverage.
0.00 = monitoring engine unavailable; strategies operating unmonitored (CRITICAL condition).

**SC-14 Governance Manager Health:**
1.00 = all governance events recorded within SLA; daily report generating correctly.
0.75 = governance record latency elevated (> 10 seconds).
0.50 = some governance events not recording; daily report may be incomplete.
0.25 = governance records failing > 30% of the time.
0.00 = governance unavailable; constitutional compliance cannot be enforced (CRITICAL condition; halt operations).

**SC-15 Audit Manager Health:**
1.00 = hash chain intact; all audit records writing within SLA; integrity checks passing.
0.75 = audit record latency elevated.
0.50 = audit records writing but hash chain updates delayed.
0.25 = audit records failing to write.
0.00 = audit manager unavailable or hash chain broken (CRITICAL; halt and investigate).

**SC-16 Analytics Engine Health:**
1.00 = all analytics computing on schedule; attribution available; correlation matrix current.
0.75 = analytics delayed; correlation matrix slightly stale (1 session).
0.50 = some analytics unavailable; attribution partially available.
0.25 = analytics severely degraded.
0.00 = analytics engine unavailable.

**SC-17 Health Manager Health (self-assessment):**
1.00 = all 20 components health scores computed; SEHS current; alerts generating correctly.
0.75 = health computation slightly delayed.
0.50 = some component health scores unavailable; SEHS estimated.
0.25 = SEHS computation severely degraded.
0.00 = health manager unavailable (self-referential failure; use fallback alert).

**SC-18 Reporting Manager Health:**
1.00 = all reports generating on schedule; Telegram delivery operational; L17 dashboard updates live.
0.75 = report delivery delayed.
0.50 = some reports failing; Telegram or dashboard delivery unavailable.
0.25 = most reporting unavailable.
0.00 = reporting manager unavailable.

**SC-19 Version Manager Health:**
1.00 = version history current; rollback capability operational; no version conflicts.
0.75 = version history slightly delayed.
0.50 = some version operations failing; rollback may be unavailable.
0.25 = version manager largely unavailable.
0.00 = version manager unavailable; no rollback possible (CRITICAL during evolution).

**SC-20 Metadata Manager Health:**
1.00 = all metadata lookups successful; metadata current for all active strategies.
0.75 = metadata latency elevated.
0.50 = some metadata unavailable; reports may have gaps.
0.25 = metadata severely degraded.
0.00 = metadata manager unavailable.

---

### SEHS Computation Formula

SEHS = weighted average of all 20 component health scores.

Default weights are equal (0.05 per component). SC-17 can apply elevated weights to critical path components that are required for the core trading function:

| Component        | Default Weight | Critical Path Weight |
|------------------|---------------|----------------------|
| SC-01 Registry   | 0.05          | 0.08 (critical path) |
| SC-13 Monitoring | 0.05          | 0.08 (critical path) |
| SC-14 Governance | 0.05          | 0.08 (critical path) |
| SC-15 Audit      | 0.05          | 0.07 (critical path) |
| SC-10 Selection  | 0.05          | 0.07 (critical path) |
| Other 15 comps   | 0.05 each     | 0.04 each (20 * 0.05 - sum of elevated = balance) |

The critical path weighting ensures that failure in the highest-consequence components has a larger impact on the SEHS, making the overall health score more sensitive to the conditions that matter most for trading operations.

---

## FINAL STATEMENT

IIOS-STR-ENG-ARCH-001 is a complete, stand-alone specification for the IIOS Strategy Engine. Together with the other 16 documents in the IIOS Engine Architecture Series, it defines the full architectural framework for a professional-grade, multi-layer, AI-assisted investment intelligence and trading system.

The Strategy Engine, as specified in this document, is the quality assurance heart of the IIOS trading system. Without it — without its validation pipelines, its quality scoring, its constitutional rules, its versioned evolution management, and its permanent audit chain — the system would be fast but fragile: generating signals efficiently while accumulating hidden technical debt in the form of overfit strategies, decaying edges, and unattributed performance.

With it, the system builds something more durable: an inventory of strategies that are validated, understood, monitored, and governed — each with a documented hypothesis, a chain of evidence supporting its deployment, a permanent record of its decisions, and a clear process for its retirement when its time has come.

The document and the architecture it describes are living references. Each new strategy deployed, each evolution approved, each retirement executed, and each human override studied adds to the institutional knowledge base. The system becomes more capable not by changing its architecture, but by accumulating experience within the architecture — which is itself the highest expression of the investment intelligence vision at the heart of IIOS.

---

*End of IIOS-STR-ENG-ARCH-001 — Strategy Engine Architecture*
*Document Code: IIOS-STR-ENG-ARCH-001 | Version: 1.0 | Status: FINAL*


---

## DOCUMENT REVISION HISTORY

| Version | Date       | Author         | Change Description                               |
|---------|------------|----------------|--------------------------------------------------|
| 0.1     | 2025-01-01 | Architecture   | Initial draft — Parts I-V                        |
| 0.5     | 2025-03-01 | Architecture   | Parts VI-X added; Supplements A-C                |
| 0.9     | 2025-08-01 | Architecture   | Supplements D-H added; Appendix added            |
| 1.0     | 2025-11-12 | Architecture   | FINAL — all sections complete; audit passed      |

---

*IIOS-STR-ENG-ARCH-001 — FINAL — All rights reserved.*
*This document is part of the IIOS Engine Architecture Series.*
*Series documents: DATABASE, KNOWLEDGE, ENTITY, RELATIONSHIP, EVENT, INFORMATION, OBSERVATION, EVIDENCE, HYPOTHESIS, REASONING, DECISION, EXECUTION, LEARNING, PREDICTION, RISK, PORTFOLIO, STRATEGY*
