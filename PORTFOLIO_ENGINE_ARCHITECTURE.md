# PORTFOLIO ENGINE ARCHITECTURE
## Investment Intelligence Operating System (IIOS)
### Document Code: IIOS-PRT-ENG-ARCH-001

---

**Document Scope:** Complete engineering architecture for the Portfolio Engine of the Investment Intelligence Operating System. The Portfolio Engine is the canonical source of truth for all portfolio state in the IIOS: holdings, positions, cash, allocations, performance, and attribution.

**Document Status:** RATIFIED

**Series:** IIOS Architecture Document Series

**Predecessor documents consulted:**
- IIOS-KNW-ENG-ARCH-001 — Knowledge Engine Architecture
- IIOS-DEC-ENG-ARCH-001 — Decision Engine Architecture
- IIOS-EXE-ENG-ARCH-001 — Execution Engine Architecture
- IIOS-RSK-ENG-ARCH-001 — Risk Engine Architecture
- IIOS-LRN-ENG-ARCH-001 — Learning Engine Architecture
- IIOS-PRD-ENG-ARCH-001 — Prediction Engine Architecture

**Critical invariants:**
- The Portfolio Engine NEVER creates investment ideas
- The Portfolio Engine NEVER bypasses Risk Engine governance
- The Portfolio Engine NEVER overrides the Decision Engine
- All portfolio state changes are driven by execution records — never by direct manipulation
- The Portfolio Engine is the canonical source of truth for portfolio state; no other component may be authoritative on portfolio holdings
- All portfolio updates are audited before they are applied

---

## IIOS COGNITIVE STACK — PORTFOLIO ENGINE CONTEXT

`
┌──────────────────────────────────────────────────────────────────────────────┐
│  IIOS COGNITIVE STACK                        Portfolio Engine Role            │
├──────┬───────────────────────────────────────┬──────────────────────────────┤
│  L1  │ GlobalIntelligence                    │ → Macro context for port. eval│
│  L2  │ MarketIntelligence                    │ → Regime for allocation review│
│  L3  │ MetaLearning                          │ ← Port. allocation weights    │
│  L4  │ OpportunityEngine                     │ → Portfolio capacity context  │
│  L5  │ StrategyLab                           │ → Strategy allocation requests│
│ ►L6  │ CapitalRiskEngine ◄═══════════════════╪══ PORTFOLIO provides NAV/pos  │
│ ►L7  │ RiskControl ◄══════════════════════════╪══ PORTFOLIO provides exposure │
│  L8  │ MarketSimulation                      │ → Scenario portfolio impacts  │
│  L9  │ RiskGuardian                          │ → Kill switch → port. halt    │
│  L10 │ DebateAndDecision                     │ → Approved trades to execute  │
│ ►L11 │ ExecutionEngine ══════════════════════╪══► PORTFOLIO receives fills   │
│ ►L12 │ TradeMonitoring ══════════════════════╪══► PORTFOLIO receives P&L     │
│ ►L13 │ LearningSystem ◄══════════════════════╪══ PORTFOLIO provides outcomes │
│ ►L14 │ PerformanceAnalytics ◄════════════════╪══ PORTFOLIO provides history  │
│  L15 │ ResearchLab                           │ ← Portfolio strategy perf.    │
│  L16 │ ValidationEngine                      │ → Portfolio validation inputs │
│ ►L17 │ ControlTower ◄════════════════════════╪══ PORTFOLIO dashboard data    │
├──────┴───────────────────────────────────────┴──────────────────────────────┤
│  ╔════════════════════════════════════════════════════════════════════╗       │
│  ║               PORTFOLIO ENGINE                                      ║       │
│  ║  Holdings → Positions → Cash → Allocation → Exposure →             ║       │
│  ║  Diversification → Performance → Attribution → Rebalancing →       ║       │
│  ║  Analytics → Reporting → Governance                                 ║       │
│  ╚════════════════════════════════════════════════════════════════════╝       │
└──────────────────────────────────────────────────────────────────────────────┘
`

---

## PORTFOLIO ENGINE INFORMATION FLOW

`
              PORTFOLIO ENGINE INFORMATION FLOW
              ════════════════════════════════

[Execution Engine L11]     ──→ fill records: symbol, qty, price, direction
[TradeMonitoring L12]      ──→ real-time P&L, unrealized gains/losses
[Risk Engine L6/L7/L9]     ──→ approved limits, kill switch state, exposure checks
[Decision Engine L10]      ──→ approved trade decisions (pre-fill)
[Learning Engine L13]      ──→ strategy performance calibrations
[Prediction Engine]        ──→ portfolio forecasts, NAV projections
[GlobalIntelligence L1]    ──→ macro context for allocation review
[MarketIntelligence L2]    ──→ regime, sector rotation signals
[StrategyLab L5]           ──→ strategy-level allocation requests
                                     │
                                     ▼
                      ┌────────────────────────────────┐
                      │        PORTFOLIO ENGINE          │
                      │                                  │
                      │  Update Holdings → Update Pos.  │
                      │  → Update Cash → Recompute NAV  │
                      │  → Check Allocation → Compute   │
                      │  → Performance → Attribution     │
                      │  → Diversification → Analytics  │
                      │  → Rebalancing → Governance     │
                      └────────────────┬─────────────────┘
                                       │
           ┌───────────────────────────┼──────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
[L6 CapitalRiskEngine]    [L13-L14 Learning/Performance]  [L17 ControlTower]
NAV, positions,            Realized outcomes,               Portfolio dashboard,
exposure vectors           strategy attribution             PPHS telemetry
`

---

## TABLE OF CONTENTS

**Part I** — Portfolio Philosophy and Definitional Framework
**Part II** — Portfolio Taxonomy
**Part III** — Core Component Architecture
**Part IV** — Portfolio Lifecycle
**Part V** — Portfolio Services
**Part VI** — Portfolio Processing Pipelines
**Part VII** — Portfolio Quality Framework
**Part VIII** — Portfolio Governance
**Part IX** — Portfolio Constitution
**Part X** — Portfolio Readiness Checklist

**Supplement A** — Portfolio Taxonomy Reference
**Supplement B** — Allocation Models
**Supplement C** — Rebalancing Strategies
**Supplement D** — Performance Attribution Examples
**Supplement E** — Benchmark Framework
**Supplement F** — Anti-Patterns
**Supplement G** — Operational Runbook
**Supplement H** — Comprehensive Glossary and Governing Design Records

**Appendix** — Worked Portfolio Examples (WE-01 through WE-06)
**Document Summary** — Metrics, Maps, Indexes, Cross-Layer Integration, Ratification

---

## PART I — PORTFOLIO PHILOSOPHY AND DEFINITIONAL FRAMEWORK

### 1.1 What is a Portfolio?

A portfolio is a deliberate, governed collection of financial instruments held together for a defined purpose under a unified management framework. A portfolio is not a list of positions — it is a living construct that has an objective, a set of constraints, a risk profile, a performance history, and a governance framework. The portfolio is greater than the sum of its parts: the properties of the portfolio depend not only on what is held but on how much, in what proportions, and with what correlations between holdings.

In the IIOS, the Portfolio Engine is the custodian of this construct. Every investment the IIOS makes belongs to a portfolio. The portfolio is the organizing principle that connects individual trade decisions to the broader investment mandate, the risk framework, and the performance measurement system.

The IIOS operates a multi-strategy portfolio: multiple distinct trading strategies, each with their own objectives and constraints, contribute positions to a common portfolio. The Portfolio Engine must manage not only the aggregate portfolio but also the strategy-level sub-portfolios that compose it.

A portfolio that is not measured is not managed. A portfolio that is not governed is not trustworthy. A portfolio that is not attributed is not learnable. These three imperatives — measurement, governance, and attribution — are the philosophical pillars of the Portfolio Engine.

---

### 1.2 Definitional Ladder

**Portfolio (Level 1):**
A governed, purposeful collection of financial instruments managed as a unified entity with a defined objective, constraint set, and performance measurement framework. The portfolio is the top-level unit of management in the IIOS.

*IIOS handling:* The Portfolio Registry (PC-01) maintains the canonical record of all portfolios. Every investment action is linked to a portfolio.

**Account (Level 2):**
The financial account at a broker that holds the capital used for investment. An account has a cash balance, a broker-specific identifier, and links to the instruments it holds. An account is the financial infrastructure within which a portfolio operates.

*Distinction from Portfolio:* A portfolio is the investment management construct; an account is the financial plumbing. One account may host one or multiple portfolios (in a multi-portfolio IIOS implementation).

*IIOS handling:* Account-level cash and position data is obtained from the broker (Dhan) via the Execution Engine. The Portfolio Engine reconciles its internal state with the account state.

**Position (Level 3):**
A live, open holding of a specific instrument at a specific moment in time. A position has a size (number of units), a direction (long or short), a current market value, an unrealized P&L, and a cost basis.

*Distinction from Holding:* A position is a current state (live open trade); a holding is a broader concept that includes both current positions and historical records of past positions.

*IIOS handling:* The Position Manager (PC-04) maintains all current positions with real-time mark-to-market. Positions are created by execution fills and closed by subsequent fills.

**Holding (Level 4):**
The record of an instrument being or having been held in the portfolio. A holding has a lifecycle: it is opened when the first position is established, updated as the position changes, and closed when the position is fully exited. Historical holdings provide the raw material for performance attribution.

*IIOS handling:* The Holding Manager (PC-05) maintains both current and historical holdings, providing the complete ownership history of every instrument.

**Trade (Level 5):**
A completed investment decision cycle: signal, decision, execution, and outcome. A trade has a strategy, an entry execution, one or more exit executions, and a realized P&L. Multiple trades on the same instrument may contribute to the same holding over time.

*IIOS handling:* Trades are constructed from execution fills. The Portfolio Engine aggregates fills into trade records for performance attribution.

**Order (Level 6):**
An instruction to the broker to buy or sell a specific instrument at specified conditions. An order may result in zero, one, or multiple fills.

*IIOS handling:* Orders are generated and managed by the Execution Engine (L11). The Portfolio Engine is aware of pending orders as they affect expected portfolio state.

**Execution (Level 7):**
The confirmed fill: a completed transaction at a specific price, time, and quantity. An execution is the atomic unit of portfolio change. Every portfolio change is driven by an execution record.

*IIOS handling:* Execution records from the Execution Engine are the sole input to portfolio state changes. No portfolio state change occurs without a corresponding execution record.

**Allocation (Level 8):**
The deliberate assignment of capital or risk budget to specific strategies, sectors, instruments, or categories. Allocation is a forward-looking concept — it defines what the portfolio should hold in what proportions.

*Distinction from Exposure:* Allocation is the plan; exposure is the reality. The Allocation Engine computes the target; the Exposure Engine measures the actual.

*IIOS handling:* The Allocation Engine (PC-07) computes and maintains target allocations. The difference between allocation targets and actual exposure drives rebalancing decisions.

**Exposure (Level 9):**
The actual financial risk the portfolio currently has to specific instruments, sectors, strategies, or factors. Exposure is backward-looking — it reflects what the portfolio actually holds right now.

*IIOS handling:* The Exposure Engine (PC-08) provides the Risk Engine with exposure data. Exposure is derived from positions; allocation is a constraint on future position changes.

**Diversification (Level 10):**
The portfolio property of having uncorrelated exposures across multiple instruments, sectors, strategies, and factors. Diversification reduces portfolio-level risk without proportionally reducing expected returns.

*IIOS handling:* The Diversification Engine (PC-09) continuously measures portfolio diversification quality and alerts when diversification is declining.

**Cash (Level 11):**
The uninvested capital in the portfolio. Cash is the reserve from which new positions are funded and to which position proceeds are returned. Maintaining sufficient cash is a risk management requirement.

*IIOS handling:* The Cash Manager (PC-06) tracks all cash inflows and outflows, maintains the current cash balance, and enforces the minimum cash reserve policy.

**NAV (Net Asset Value) (Level 12):**
The total current value of the portfolio: sum of all position market values plus cash balance. NAV is the fundamental measure of portfolio size and is the base for all percentage-based risk and performance calculations.

*IIOS handling:* NAV is recomputed after every execution fill and at every monitoring cycle. NAV is the universal denominator for all portfolio metrics.

**Benchmark (Level 13):**
A reference portfolio or index against which the IIOS portfolio's performance is measured. The benchmark defines the investment universe and the baseline return that the IIOS should exceed. In the IIOS Indian equity context, the primary benchmark is the NIFTY 50 index.

*IIOS handling:* The Benchmark Engine (PC-13) maintains benchmark definitions and computes benchmark returns for performance comparison.

**Performance (Level 14):**
The return generated by the portfolio over a defined period, measured absolutely (total return) and relatively (excess return above benchmark). Performance encompasses realized P&L from closed positions and unrealized P&L from open positions.

*IIOS handling:* The Performance Engine (PC-11) computes multi-period performance metrics: daily, weekly, monthly, and since-inception returns.

**Attribution (Level 15):**
The decomposition of portfolio performance into its contributing sources: which strategies, instruments, sectors, decisions, and timing choices drove the observed performance? Attribution explains WHY the portfolio performed as it did, not just HOW MUCH it returned.

*IIOS handling:* The Attribution Engine (PC-12) performs strategy-level, sector-level, and instrument-level attribution of all portfolio performance.

**Rebalancing (Level 16):**
The process of adjusting portfolio holdings to bring actual exposures back in line with target allocations. Rebalancing is triggered when actual exposures drift beyond defined tolerance bands from their targets.

*IIOS handling:* The Rebalancing Engine (PC-10) monitors allocation drift and generates rebalancing recommendations, which are passed to the Decision Engine for evaluation and approval.

**Capital Allocation (Level 17):**
The explicit decision about how much capital or risk budget to assign to each strategy, sector, or category in the portfolio. Capital allocation is a governance decision that constrains all subsequent investment decisions.

*IIOS handling:* Capital allocation is set by governance and enforced by the Constraint Manager (PC-14) and the Allocation Engine (PC-07).

**Portfolio Objective (Level 18):**
The stated purpose of the portfolio: what it is trying to achieve. In the IIOS, the portfolio objective is risk-adjusted capital growth with a primary constraint of capital preservation.

**Portfolio Constraint (Level 19):**
A rule that limits how the portfolio can be constructed. Constraints may be hard (must be obeyed absolutely) or soft (preferences that should be followed unless there is strong reason to deviate). The Constraint Manager (PC-14) enforces all portfolio constraints.

**Portfolio Risk (Level 20):**
The aggregate risk of the portfolio's current holdings, as measured by the Risk Engine. Portfolio risk is the primary input to position sizing and rebalancing decisions.

**Portfolio Intelligence (Level 21):**
The higher-order insights derived from portfolio analytics: patterns in strategy performance, attribution trends, risk-return evolution, and behavioral patterns. Portfolio Intelligence is the primary output of the Portfolio Analytics Engine (PC-15) and is consumed by the Learning Engine for model improvement.

---

### 1.3 Portfolio Types by Management Style

**Active Portfolio:**
A portfolio where every holding is a deliberate investment decision made to generate alpha (excess return above benchmark). Active portfolios require continuous management, research, and decision-making. All IIOS portfolios are active portfolios.

**Passive Portfolio:**
A portfolio designed to replicate a benchmark index. Passive portfolios minimize active decisions and management costs. The IIOS does not operate passive portfolios, but uses benchmark comparison as a performance reference.

**Hybrid Portfolio:**
A portfolio that combines active and passive elements. Portions of the portfolio may track a benchmark while others are actively managed. Not currently implemented in the IIOS but architecturally supported.

**AI Managed Portfolio:**
A portfolio where all investment decisions are generated by an AI system (in the IIOS case, the 17-layer multi-agent system). The human role is oversight, governance, and exception management. This is the IIOS operating model.

**Human Managed Portfolio:**
A portfolio where investment decisions are made entirely by human portfolio managers. The IIOS supports human override for all investment decisions.

**Multi-Strategy Portfolio:**
A portfolio that hosts multiple distinct trading strategies simultaneously. Each strategy generates its own signals and trades, contributing to a common portfolio. The IIOS operates a multi-strategy portfolio as its core model. Strategy diversification is a key source of portfolio risk reduction.

**Multi-Asset Portfolio:**
A portfolio that holds instruments across multiple asset classes (equity, fixed income, commodities, currencies). The current IIOS primarily operates an equity portfolio but the architecture supports multi-asset expansion.

---

### 1.4 Portfolio Principles

**PP-001 — The portfolio is the unit of management, not the position.**
Investment decisions are evaluated in the context of their portfolio impact. A position that is individually attractive but damages portfolio diversification may be rejected.

**PP-002 — Actual exposure is always measured, never assumed.**
The Portfolio Engine maintains real-time exposure vectors from live positions. Target allocations are the goal; actual exposure is the reality. The difference is the management gap that rebalancing closes.

**PP-003 — Cash is a managed asset, not a passive residual.**
Cash level is actively managed to maintain the minimum reserve, fund new positions, and preserve flexibility. Cash allocation decisions are as deliberate as any other allocation.

**PP-004 — Performance attribution is mandatory for learning.**
Every session's performance is attributed to its sources: which strategies, instruments, and decisions drove the outcome. Without attribution, the Learning Engine cannot improve.

**PP-005 — Rebalancing is a risk management function, not a performance function.**
The purpose of rebalancing is to maintain the portfolio's intended risk profile. It is not to chase recent performance. Rebalancing is triggered by allocation drift, not by return expectations.

**PP-006 — The portfolio is the canonical source of truth.**
Portfolio state, as maintained by the Portfolio Engine, is authoritative. If the Portfolio Engine's state disagrees with any other system's view (including the broker's reported positions), the discrepancy must be investigated and resolved — but the Portfolio Engine's audit trail governs the resolution.

**PP-007 — Portfolio governance is continuous, not periodic.**
The portfolio is governed in real-time throughout the session. Governance reports are produced at session close, but governance monitoring does not wait for the session to end.

**PP-008 — All portfolio changes require execution records.**
The only way portfolio holdings change is through confirmed execution fills. No algorithmic adjustment, manual override, or reconciliation may change portfolio state without a corresponding execution record or a formally authorized correction record.

---

## PART II — PORTFOLIO TAXONOMY

### 2.0 Taxonomy Design Principles

The IIOS Portfolio Taxonomy classifies all portfolio types that the Portfolio Engine is designed to support. Each portfolio type has a canonical identifier, a precise definition, its investment universe, its objective, its characteristic risk profile, its constraint set, and its IIOS integration requirements.

Portfolio type codes follow the pattern PT-NN.

The taxonomy is organized in three dimensions:
1. Asset class dimension: what instruments does the portfolio hold?
2. Strategy dimension: what investment approach does the portfolio take?
3. Management dimension: how is the portfolio managed?

---

### PT-01 — Equity Portfolio

**Definition:** A portfolio that holds exclusively equity instruments: individual stocks, equity indices, and equity derivatives. The equity portfolio is the primary portfolio type in the current IIOS implementation.

**Investment universe:** NSE/BSE listed equities, NIFTY/BANKNIFTY index derivatives (Futures and Options), equity ETFs.

**Objective:** Capital growth through equity price appreciation, trading profits, and dividends.

**Characteristic risk profile:** Market risk (RT-01), sector risk (RT-04), concentration risk (RT-21), liquidity risk (RT-06).

**IIOS integration:** Primary portfolio type. All current IIOS strategies generate signals for equity instruments.

**Performance benchmark:** NIFTY 50 index total return.

---

### PT-02 — Options Portfolio

**Definition:** A portfolio that holds primarily options instruments: puts, calls, spreads, and structured options positions. Options portfolios can generate returns from direction, volatility, time decay, and structured payoffs.

**Investment universe:** NSE F&O segment: NIFTY options, BANKNIFTY options, stock options.

**Objective:** Premium collection, directional leveraged returns, or hedging.

**Characteristic risk profile:** Gamma risk (non-linear price sensitivity), theta risk (time decay), vega risk (volatility sensitivity), assignment risk.

**Special considerations:** Options positions have expiry dates; the Portfolio Engine must track expiry dates and initiate close-out before expiry unless rollover is intended.

**IIOS integration:** Supported within the equity portfolio framework. F&O positions are tracked at notional exposure for risk management purposes.

---

### PT-03 — Futures Portfolio

**Definition:** A portfolio focused on futures contracts: index futures, single-stock futures. Futures provide leveraged directional exposure with defined expiry.

**Investment universe:** NSE NIFTY futures, BANKNIFTY futures, single-stock futures.

**Objective:** Directional returns with leverage; hedging of underlying equity positions.

**Characteristic risk profile:** Leverage risk, rollover risk, basis risk (futures vs spot divergence), margin risk.

**IIOS integration:** Futures used as index exposure vehicles and directional bets. Margin requirements tracked by the Cash Manager.

---

### PT-04 — Commodity Portfolio

**Definition:** A portfolio holding commodity instruments. In the Indian context: MCX commodity futures (gold, silver, crude oil, base metals) and commodity ETFs.

**Objective:** Commodity price exposure, inflation hedging, diversification from equity.

**IIOS integration:** Currently not primary focus but architecturally supported. Would require separate universe and data feeds.

---

### PT-05 — Currency Portfolio

**Definition:** A portfolio holding currency instruments: spot FX pairs, currency futures (NSE), and currency options.

**Investment universe:** NSE currency segment: USDINR, EURINR, GBPINR, JPYINR futures and options.

**Objective:** Currency directional returns; FX risk hedging for equity positions with foreign exposure.

**IIOS integration:** Currency risk (RT-13) from equity holdings is monitored. Currency instruments as standalone portfolio are architecturally supported.

---

### PT-06 — Crypto Portfolio

**Definition:** A portfolio holding cryptocurrency instruments. Currently not operational in the IIOS India-focused implementation but architecturally defined for future expansion.

**Characteristic risk profile:** Extreme volatility, 24/7 market, regulatory uncertainty, custody risk.

**IIOS note:** Architecture supports but Kill Switch and risk thresholds would require significant calibration for crypto volatility.

---

### PT-07 — Long Only Portfolio

**Definition:** A portfolio restricted to only holding long positions (purchases). No short selling is permitted. The portfolio can only profit from price increases in held instruments.

**Characteristic risk profile:** Full downside exposure to market falls; no natural hedge against market declines.

**Capital protection approach:** Cash position increases during adverse conditions; defensive sectors or instruments used.

**IIOS integration:** The current IIOS operates primarily as a long-only portfolio for equity positions.

---

### PT-08 — Long/Short Portfolio

**Definition:** A portfolio that holds both long positions (expecting price increases) and short positions (expecting price decreases). Long/short portfolios can generate returns from relative value (long outperformers, short underperformers) and can partially hedge market risk.

**Characteristic risk profile:** Net exposure risk (depends on L/S ratio), short squeeze risk, borrow cost risk.

**Market neutrality:** A balanced long/short portfolio with equal long and short exposure can theoretically be market-neutral (portfolio return doesn't depend on market direction).

**IIOS integration:** Architecturally supported. Short positions tracked with their specific risk characteristics.

---

### PT-09 — Income Portfolio

**Definition:** A portfolio focused on generating regular income through dividends, options premium collection, or fixed income instruments.

**Objective:** Regular cash flow generation; total return is a secondary objective.

**Characteristic instruments:** High-dividend stocks; covered call writing strategies; bond ETFs.

**IIOS integration:** Income generation is tracked by the Performance Engine as a separate attribution category.

---

### PT-10 — Growth Portfolio

**Definition:** A portfolio focused on capital appreciation through growth companies and momentum strategies. Growth portfolios typically have higher volatility and longer holding periods.

**Characteristic instruments:** High-growth sectors (technology, healthcare, consumer discretionary); momentum leaders.

**Risk profile:** Higher volatility; sector concentration; valuation risk.

---

### PT-11 — Value Portfolio

**Definition:** A portfolio focused on undervalued companies trading below their intrinsic value. Value portfolios typically have lower valuations and seek mean-reversion returns.

**Characteristic instruments:** Low P/E, low P/B companies with strong fundamentals; contrarian positions.

**Risk profile:** Value trap risk (cheap stocks that stay cheap); mean-reversion timing uncertainty.

---

### PT-12 — Momentum Portfolio

**Definition:** A portfolio that systematically holds instruments that have demonstrated strong recent price momentum, expecting the trend to continue.

**Characteristic approach:** Quantitative signal-driven; high turnover; strong performance in trending markets; underperforms in reversal markets.

**IIOS integration:** The most natural portfolio type for IIOS strategy signals, which are predominantly momentum-based.

---

### PT-13 — Dividend Portfolio

**Definition:** A portfolio targeting instruments with strong, consistent dividend histories. Combines income generation with capital preservation.

**Characteristic instruments:** PSU companies; established large-cap blue chips; REITs and InvITs.

**IIOS integration:** Dividend dates tracked by the Knowledge Engine entity layer; dividend income attributed separately.

---

### PT-14 — Balanced Portfolio

**Definition:** A portfolio that deliberately balances between growth-oriented instruments (equities) and capital-preserving instruments (bonds, cash). The balance is adjusted based on market conditions.

**Characteristic allocation:** Typically 60-70% equity, 30-40% fixed income in standard configuration.

**IIOS integration:** Multi-asset portfolio type; requires fixed income data feeds if implemented.

---

### PT-15 — Sector Portfolio

**Definition:** A portfolio concentrated in a specific economic sector. Sector portfolios seek to benefit from sector-specific tailwinds or cyclical rotation.

**Characteristic sectors (India):** IT, Banking & Finance, Pharma, FMCG, Infrastructure, Auto, Energy.

**Risk note:** Sector concentration is a specific Risk Engine concern (RT-04). Sector portfolios by design accept higher sector risk.

**IIOS integration:** Sector-level attribution is tracked for all IIOS portfolios regardless of type.

---

### PT-16 — Thematic Portfolio

**Definition:** A portfolio organized around an investment theme rather than a sector classification: digital transformation, renewable energy, demographic change.

**Characteristic instruments:** Cross-sector instruments linked by a common economic theme.

**IIOS integration:** Thematic portfolios require custom classification beyond the standard sector taxonomy.

---

### PT-17 — Global Portfolio

**Definition:** A portfolio investing across multiple geographies. In the IIOS India context, this would include domestic India (NSE/BSE) plus foreign instruments via domestic ADRs, ETFs, or international market access.

**IIOS integration:** GlobalIntelligence (L1) provides the macro context for global allocation decisions.

---

### PT-18 — Multi-Asset Portfolio

**Definition:** A portfolio holding instruments across multiple asset classes: equities, fixed income, commodities, currencies, and potentially alternatives. Designed for maximum diversification.

**IIOS integration:** The current IIOS equity focus would need significant expansion to operate a fully multi-asset portfolio.

---

### PT-19 — AI Portfolio

**Definition:** A portfolio where all investment decisions are generated by the IIOS AI system. No human-generated investment ideas. Human role is oversight, governance, and exception management.

**IIOS integration:** This is the current IIOS operating model. The AI Portfolio is the native IIOS portfolio type.

**Governance requirements:** Enhanced audit trails; explainability of all AI decisions; regular human review of AI decision patterns.

---

### PT-20 — Hybrid Portfolio

**Definition:** A portfolio that combines AI-generated signals with human-curated investment ideas. Some positions may be AI-driven; others may be human-initiated (with Risk Engine validation).

**IIOS integration:** Supported through the human override framework. Human-initiated positions are tagged differently in the portfolio for attribution purposes.

---

### 2.1 Portfolio Taxonomy Summary Table

| Code  | Portfolio Type       | Asset Class  | Objective     | IIOS Status   |
|-------|----------------------|--------------|---------------|---------------|
| PT-01 | Equity Portfolio     | Equity       | Growth        | Primary       |
| PT-02 | Options Portfolio    | Derivatives  | Alpha/Hedge   | Supported     |
| PT-03 | Futures Portfolio    | Derivatives  | Leverage/Hedge| Supported     |
| PT-04 | Commodity Portfolio  | Commodity    | Diversify     | Planned       |
| PT-05 | Currency Portfolio   | FX           | FX/Hedge      | Supported     |
| PT-06 | Crypto Portfolio     | Crypto       | Growth        | Future        |
| PT-07 | Long Only            | Any          | Growth        | Primary       |
| PT-08 | Long/Short           | Any          | Alpha         | Supported     |
| PT-09 | Income               | Equity/Fixed | Income        | Supported     |
| PT-10 | Growth               | Equity       | Growth        | Supported     |
| PT-11 | Value                | Equity       | Alpha         | Supported     |
| PT-12 | Momentum             | Equity       | Alpha         | Primary       |
| PT-13 | Dividend             | Equity       | Income/Growth | Supported     |
| PT-14 | Balanced             | Multi-Asset  | Balanced      | Planned       |
| PT-15 | Sector               | Equity       | Sector Alpha  | Supported     |
| PT-16 | Thematic             | Cross-Sector | Theme Alpha   | Supported     |
| PT-17 | Global               | Multi-Geo    | Global Alpha  | Planned       |
| PT-18 | Multi-Asset          | All          | Diversify     | Planned       |
| PT-19 | AI Portfolio         | Any          | AI Alpha      | Primary       |
| PT-20 | Hybrid               | Any          | Combined      | Supported     |

---

## PART III — CORE COMPONENT ARCHITECTURE

### 3.0 Component Design Principles

The Portfolio Engine is organized into twenty-one core components across four tiers. Each component has precisely defined responsibilities, interfaces, failure modes, and recovery strategies.

**Four-Tier Component Architecture:**

| Tier | Name               | Components        | Purpose                                          |
|------|--------------------|-------------------|--------------------------------------------------|
| T1   | State Layer        | PC-01 to PC-06    | Maintain authoritative portfolio state           |
| T2   | Computation Layer  | PC-07 to PC-13    | Compute portfolio metrics, allocations, performance|
| T3   | Control Layer      | PC-14 to PC-16    | Enforce constraints, monitor quality             |
| T4   | Governance Layer   | PC-17 to PC-21    | Govern, audit, archive, report                   |

Component codes follow the pattern PC-NN.

---

### PC-01 — Portfolio Registry

**Purpose:** The Portfolio Registry is the master record of all portfolios managed by the IIOS. It is the single source of truth for portfolio identity, configuration, status, and lineage. Every portfolio that exists in the IIOS is registered here.

**Responsibilities:**
1. Maintain the canonical register of all active, archived, and retired portfolios
2. Assign canonical portfolio identifiers (PRT-{TYPE}-{YYYYMMDD}-{SEQ:06d})
3. Store portfolio metadata: type, objective, constraint references, benchmark assignment
4. Track portfolio status lifecycle: INITIALIZING → ACTIVE → SUSPENDED → CLOSED → ARCHIVED
5. Enforce portfolio schema validity on all inbound portfolio records
6. Maintain portfolio versioning: configuration changes create new versions with lineage
7. Provide portfolio lookup by ID, type, status, strategy
8. Track strategy-to-portfolio assignment: which strategies contribute to which portfolio
9. Maintain portfolio creation and closure timestamps with authorization records
10. Provide portfolio snapshot at any historical point (time-travel query)
11. Broadcast portfolio state changes to event bus for downstream subscribers
12. Enforce uniqueness constraints: portfolio names, benchmark assignments

**Inputs:**
- Portfolio creation requests from governance framework
- Portfolio configuration updates from Portfolio Governance Manager (PC-17)
- Strategy assignment events from StrategyLab (L5)

**Outputs:**
- Portfolio records to all Portfolio Engine components
- Portfolio state changes to event bus
- Portfolio summaries to Portfolio Reporting Manager (PC-21)
- Archive-ready records to Portfolio Archive Manager (PC-19)

**Dependencies:** Portfolio Catalog (PC-02) for type validation; Portfolio Audit Manager (PC-18) for change logging.

**Failure Modes:**
- Registry write failure: No portfolio state changes until recovered; alert immediately
- Registry read failure: Serve from in-memory cache; mark as potentially stale; alert
- Corrupted portfolio record: Quarantine record; restore from last verified checkpoint

**Recovery Strategy:** Restore from session-start checkpoint, replay event journal to current state. If journal is unavailable, alert operator and enter read-only mode until manual verification.

**Monitoring:** Registry write latency; portfolio count by status; event bus broadcast latency.

**Engineering Notes:** The Portfolio Registry is queried by all 21 Portfolio Engine components. It must be available before any portfolio operation can begin. It is a Tier-1 dependency.

---

### PC-02 — Portfolio Catalog

**Purpose:** The Portfolio Catalog is the controlled vocabulary and classification authority for portfolio types, configuration schemas, and portfolio metadata standards. It defines what configurations are valid and how portfolios are classified.

**Responsibilities:**
1. Maintain the canonical list of all portfolio types (PT-01 through PT-20 and future types)
2. Define configuration schemas for each portfolio type (required fields, valid ranges)
3. Maintain portfolio type hierarchy: asset class → strategy → management style
4. Define default configurations for each portfolio type
5. Specify required benchmarks for each portfolio type
6. Track portfolio type versioning: catalog version controls type definitions
7. Provide classification rules for portfolio type assignment
8. Support multi-type portfolios (a portfolio may be simultaneously PT-07 Long-Only and PT-12 Momentum)
9. Maintain portfolio type interdependencies and restrictions
10. Support catalog queries: find all portfolios of type X; find all portfolios with benchmark Y

**Failure Modes:** Catalog unavailable — fall back to last valid version; no new portfolio creation until catalog restored.

**Engineering Notes:** The Catalog is read-only during sessions. Changes require governance approval and take effect at next session start.

---

### PC-03 — Portfolio Manager

**Purpose:** The Portfolio Manager is the central coordinator of the Portfolio Engine. It orchestrates all portfolio operations: directing execution-driven updates to the appropriate state components, coordinating multi-component updates, and ensuring consistency across all portfolio views.

**Responsibilities:**
1. Receive execution fill events and coordinate state updates across PC-04, PC-05, PC-06
2. Maintain consistency invariants: NAV = sum(position values) + cash
3. Coordinate portfolio rebalancing workflows end-to-end
4. Handle multi-position trades (spread trades, baskets) atomically
5. Manage portfolio-level transactions: open, close, adjust positions as unified operations
6. Enforce the ordering constraint: Risk Engine must approve before Portfolio Manager accepts a trade
7. Coordinate with the Constraint Manager (PC-14) before any portfolio change
8. Maintain portfolio state versioning: every state change creates a new version
9. Provide the current portfolio state to all consumers on demand
10. Orchestrate end-of-session portfolio closure and reporting

**Inputs:**
- Execution fill records from Execution Engine (L11)
- Approved trade decisions from Decision Engine (L10)
- Risk Engine approvals from Risk Engine (L7)
- Rebalancing instructions from Rebalancing Engine (PC-10)

**Outputs:**
- Updated portfolio state to Portfolio Registry (PC-01)
- Position updates to Position Manager (PC-04)
- Holding updates to Holding Manager (PC-05)
- Cash updates to Cash Manager (PC-06)
- Portfolio state to ControlTower (L17)

**Consistency Rule:** All portfolio state components (positions, holdings, cash) are updated atomically from a single execution fill. Partial updates are not permitted. If any sub-update fails, the entire transaction is rolled back and the fill is re-queued.

**Failure Modes:**
- Transaction failure: Roll back all sub-components; re-queue fill; alert operator
- Coordinator crash: On restart, replay unprocessed fills from Execution Engine journal
- Consistency check failure: Halt new updates; alert operator; manual reconciliation

**Recovery Strategy:** Journal-based recovery. All fills are logged with processing status. On restart, re-process any fills with status PENDING or PROCESSING.

**Engineering Notes:** The Portfolio Manager is the only component that writes to portfolio state. All other components read state but do not write it directly. This single-writer principle prevents state corruption from concurrent updates.

---

### PC-04 — Position Manager

**Purpose:** The Position Manager maintains the complete and accurate record of all current open positions in the IIOS portfolio. It is the authoritative source for current position state.

**Responsibilities:**
1. Maintain the canonical list of all open positions with current state
2. Update positions when execution fills arrive: open, increase, reduce, close
3. Compute unrealized P&L for each position using current market prices
4. Track position cost basis (FIFO, AVCO — configurable per portfolio type)
5. Compute position delta (sensitivity to price movement) for derivatives
6. Track position age: how long has each position been open?
7. Monitor position-level stop-loss and target levels
8. Validate position updates against Risk Engine position limits
9. Detect position limit breaches and alert Risk Engine (PC-16 → RC-16)
10. Maintain position history: every state change is recorded with timestamp
11. Provide position snapshots at any historical moment
12. Compute position weight: position value / portfolio NAV

**Inputs:**
- Execution fill records from Portfolio Manager (PC-03)
- Market prices for mark-to-market from Observation Engine
- Position limits from Risk Engine (RC-16)

**Outputs:**
- Current positions to Portfolio Manager (PC-03)
- Position exposure to Exposure Engine (PC-08)
- Position weights to Diversification Engine (PC-09)
- Position P&L to Performance Engine (PC-11)
- Position history to Attribution Engine (PC-12)

**Position Record Format:**

| Field           | Description                                     |
|-----------------|-------------------------------------------------|
| position_id     | POS-{SYMBOL}-{YYYYMMDD}-{SEQ:06d}               |
| portfolio_id    | Parent portfolio identifier                     |
| strategy_id     | Strategy that generated this position           |
| symbol          | Instrument symbol                               |
| direction       | LONG / SHORT                                    |
| quantity        | Current open quantity (shares/lots)             |
| avg_cost        | Average cost basis (INR per share)              |
| current_price   | Last known market price (INR)                   |
| market_value    | quantity x current_price (INR)                  |
| unrealized_pnl  | market_value - (quantity x avg_cost)            |
| unrealized_pct  | unrealized_pnl / (quantity x avg_cost)          |
| position_weight | market_value / portfolio_nav                    |
| open_date       | Date position was first opened                  |
| last_updated    | UTC nanosecond timestamp of last update         |
| status          | OPEN / REDUCING / CLOSING / CLOSED              |

**Failure Modes:** Price feed failure — maintain last known prices; flag unrealized P&L as STALE; alert. Position record corruption — restore from last checkpoint; reconcile with broker data.

---

### PC-05 — Holding Manager

**Purpose:** The Holding Manager extends the Position Manager's scope to include historical holdings. Where the Position Manager tracks what is currently open, the Holding Manager tracks the complete history of what has been held — including closed positions and their realized outcomes.

**Responsibilities:**
1. Maintain lifecycle records for all holdings: OPEN → PARTIALLY_CLOSED → CLOSED
2. Track realized P&L for closed holdings
3. Compute time-weighted return for each holding
4. Maintain entry and exit execution references for each holding
5. Track holding duration: from first entry to last exit
6. Compute holding MAE (Maximum Adverse Excursion) and MFE (Maximum Favorable Excursion)
7. Tag holdings with their strategy, sector, instrument type, and session
8. Provide holding history for performance attribution (PC-12)
9. Support holding queries: find all holdings for strategy X, symbol Y, sector Z, period T
10. Archive closed holdings to Portfolio Archive Manager (PC-19)

**Inputs:**
- Position updates from Position Manager (PC-04)
- Execution fills from Portfolio Manager (PC-03)
- Market prices (for MAE/MFE tracking)

**Outputs:**
- Holding history to Attribution Engine (PC-12)
- Realized P&L to Performance Engine (PC-11)
- Historical holdings to Learning Engine (L13)
- Archive data to Portfolio Archive Manager (PC-19)

**Holding vs Position distinction:** A holding tracks the investment in an instrument from first purchase to final sale, even if the position size was changed multiple times along the way. A position tracks the current open state. When a position is fully closed, it becomes a historical holding.

**MAE/MFE computation:**
- Maximum Adverse Excursion (MAE): the maximum loss (in %, from entry) experienced during the holding period, regardless of the final outcome.
- Maximum Favorable Excursion (MFE): the maximum gain experienced during the holding period.
- MAE and MFE are key Learning Engine inputs: large MAE followed by a loss may indicate poor stop-loss discipline.

---

### PC-06 — Cash Manager

**Purpose:** The Cash Manager maintains the complete and accurate record of the portfolio's cash position. Cash is the uninvested capital — the reserve from which new positions are funded and to which exit proceeds are returned.

**Responsibilities:**
1. Maintain the canonical cash balance for the portfolio
2. Record all cash inflows: exit proceeds, dividends, interest, capital injection
3. Record all cash outflows: new position purchases, brokerage fees, taxes, capital withdrawal
4. Enforce minimum cash reserve: alert when cash falls below the 10% NAV minimum
5. Track cash utilization rate: how much of available cash is deployed in positions?
6. Project cash availability for pending orders
7. Compute available buying power: cash available for new positions after reserving minimum
8. Track cash P&L: interest earned on uninvested cash (if applicable)
9. Alert when projected cash would fall below minimum after pending orders fill
10. Provide cash reconciliation with broker account on demand

**Inputs:**
- Execution fills from Portfolio Manager (PC-03): buy fills reduce cash; sell fills increase cash
- Dividend payment records from Knowledge Engine
- Brokerage fee estimates from Execution Engine (L11)

**Outputs:**
- Cash balance to Portfolio Manager (PC-03) for NAV computation
- Buying power to Allocation Engine (PC-07) for new position sizing
- Cash projection to Risk Engine for exposure computation
- Cash alerts to Portfolio Monitoring Engine (PC-16)

**Cash Record Format:**

| Field              | Description                                      |
|--------------------|--------------------------------------------------|
| timestamp          | UTC nanosecond timestamp                         |
| event_type         | BUY / SELL / DIVIDEND / FEE / ADJUSTMENT         |
| amount             | Cash change (positive = inflow; negative = outflow)|
| reference_id       | Linked execution fill or event ID                |
| balance_after      | Cash balance after this event                    |
| buying_power_after | Available cash after minimum reserve deduction   |
| notes              | Description of event                             |

**Cash Integrity Rule:** The cash balance is always equal to the sum of all recorded cash events. Any discrepancy between the computed cash balance and the broker's reported cash triggers a reconciliation alert.

**Failure Modes:** Cash balance discrepancy — freeze new purchases; reconcile with broker; alert. Cash ledger corruption — restore from checkpoint; replay events; validate against broker.

**Engineering Notes:** Cash calculations are deterministic given the sequence of events. Any non-determinism (two computations of the same sequence produce different results) is a critical defect.

---

### PC-07 — Allocation Engine

**Purpose:** The Allocation Engine computes and maintains the target allocation of capital across strategies, sectors, instruments, and categories. It defines what the portfolio SHOULD hold (the target) as distinct from what it DOES hold (the actual exposure measured by the Exposure Engine).

**Responsibilities:**
1. Compute target allocations for each strategy based on governance policies and risk budgets
2. Compute target sector allocations based on regime signals from MarketIntelligence (L2)
3. Compute target cash allocation: the percentage of NAV to hold as cash
4. Monitor allocation drift: how far has actual exposure drifted from target allocation?
5. Compute rebalancing requirements: the trades needed to restore target allocations
6. Enforce allocation limits: no strategy, sector, or instrument may exceed defined maximum allocations
7. Adjust target allocations in response to regime changes (regime-adaptive allocation)
8. Maintain allocation history: track how targets have evolved over time
9. Produce allocation reports for governance and oversight
10. Coordinate with the Rebalancing Engine (PC-10) when drift exceeds tolerance bands

**Inputs:**
- Strategy performance and risk metrics from Learning Engine (L13)
- Regime signals from MarketIntelligence (L2)
- Risk Engine approved limits from Risk Engine (L6/L7)
- NAV from Portfolio Manager (PC-03)
- Actual exposure from Exposure Engine (PC-08)

**Outputs:**
- Target allocations to Portfolio Manager (PC-03) and Constraint Manager (PC-14)
- Rebalancing recommendations to Rebalancing Engine (PC-10)
- Allocation drift report to Portfolio Monitoring Engine (PC-16)
- Allocation history to Portfolio Analytics Engine (PC-15)

**Allocation Model Types:**

| Model               | Description                                          | Use Case                     |
|---------------------|------------------------------------------------------|------------------------------|
| Equal Weight        | Each strategy receives equal capital allocation      | Default starting allocation  |
| Risk Parity         | Allocation inversely proportional to strategy risk   | Risk-balanced portfolio       |
| Performance Weighted| Allocation proportional to recent strategy performance| Momentum-based allocation   |
| Regime-Adaptive     | Allocation shifts with market regime detection       | Dynamic risk management      |
| Fixed Budget        | Pre-defined capital budgets per strategy             | Governance-constrained        |

**Allocation Drift Tolerance:**

| Category          | Soft Band  | Hard Band  | Action at Hard Band            |
|-------------------|------------|------------|-------------------------------|
| Strategy          | +/- 5%     | +/- 10%    | Mandatory rebalancing          |
| Sector            | +/- 3%     | +/- 8%     | Mandatory rebalancing          |
| Cash              | +/- 3%     | +/- 5%     | Mandatory cash management      |
| Single Instrument | +/- 2%     | +/- 5%     | Reduce or increase position    |

---

### PC-08 — Exposure Engine

**Purpose:** The Exposure Engine measures the portfolio's actual financial exposure across all dimensions in real-time. It is the Portfolio Engine's implementation of the exposure concept that the Risk Engine also monitors. The Portfolio Exposure Engine is focused on portfolio management purposes; the Risk Engine's Exposure Engine is focused on risk enforcement.

**Responsibilities:**
1. Compute gross exposure: sum of all position market values (absolute values)
2. Compute net exposure: long minus short (in INR and as % of NAV)
3. Compute strategy-level exposure: how much capital is each strategy using?
4. Compute sector exposure: what is the portfolio's exposure to each sector?
5. Compute factor exposure: sensitivity to market factors (momentum, value, quality, volatility)
6. Compute instrument-level exposure and concentration ratios
7. Track exposure evolution over time within the session
8. Project exposure after pending orders (expected exposure post-fill)
9. Provide exposure reconciliation between Portfolio Engine and Risk Engine (exposures must agree)
10. Compute active exposure: actual exposure minus benchmark exposure (active risk sources)

**Inputs:**
- Live positions from Position Manager (PC-04)
- Pending orders from Execution Engine (L11)
- Market prices from Observation Engine
- Benchmark weights from Benchmark Engine (PC-13)

**Outputs:**
- Gross/net exposure to Portfolio Manager (PC-03) for NAV sanity checks
- Exposure vectors to Risk Engine (L6/L7) for risk limit enforcement
- Strategy exposure to Allocation Engine (PC-07) for drift computation
- Sector exposure to Diversification Engine (PC-09)
- Exposure time series to Portfolio Analytics Engine (PC-15)

**Exposure Vector Format:**

| Dimension       | Fields                                          |
|-----------------|--------------------------------------------------|
| Total           | gross_exposure, net_exposure, net_pct            |
| Strategy        | {strategy_id: exposure_INR, exposure_pct}        |
| Sector          | {sector_code: exposure_INR, exposure_pct}        |
| Instrument      | {symbol: exposure_INR, exposure_pct, direction}  |
| Factor          | {factor_name: sensitivity_score}                 |
| Cash            | cash_balance, cash_pct, buying_power_pct         |

---

### PC-09 — Diversification Engine

**Purpose:** The Diversification Engine continuously measures the portfolio's diversification quality and identifies concentration risks before they breach Risk Engine limits.

**Responsibilities:**
1. Compute the portfolio's diversification score across multiple dimensions
2. Monitor pairwise instrument correlations (sourced from Risk Engine Correlation Engine)
3. Compute effective diversification ratio (portfolio VaR / sum of individual VaRs)
4. Compute sector diversification: HHI (Herfindahl-Hirschman Index) for sector weights
5. Compute strategy diversification: HHI for strategy weights
6. Monitor strategy signal correlation: are all strategies currently pointing the same direction?
7. Track diversification evolution: is the portfolio becoming more or less diversified over time?
8. Alert when diversification falls below portfolio quality threshold
9. Provide diversification input to rebalancing decisions
10. Compute geographical diversification (for multi-asset portfolios)

**Inputs:**
- Position weights from Position Manager (PC-04)
- Sector exposures from Exposure Engine (PC-08)
- Correlation matrix from Risk Engine Correlation Engine (RC-06)
- Strategy allocations from Allocation Engine (PC-07)

**Outputs:**
- Diversification score to Portfolio Monitoring Engine (PC-16)
- Diversification alerts to Portfolio Manager (PC-03)
- Diversification contribution by position to Attribution Engine (PC-12)
- Diversification time series to Portfolio Analytics Engine (PC-15)

**Diversification Score Components:**

| Component              | Measurement                                      | Target         |
|------------------------|--------------------------------------------------|----------------|
| Instrument Count       | Number of uncorrelated instruments               | >= 3           |
| HHI Position           | Sum of squared position weights                  | < 0.25         |
| HHI Sector             | Sum of squared sector weights                    | < 0.30         |
| HHI Strategy           | Sum of squared strategy weights                  | < 0.40         |
| Avg Correlation        | Average pairwise correlation of positions        | < 0.60         |
| Effective Div Ratio    | Portfolio VaR / Sum individual VaRs              | > 0.70         |

Overall Diversification Score = weighted average of component scores.

---

### PC-10 — Rebalancing Engine

**Purpose:** The Rebalancing Engine identifies when the portfolio has drifted from its target allocations and computes the rebalancing trades needed to restore alignment.

**Responsibilities:**
1. Monitor allocation drift against tolerance bands (soft and hard)
2. Compute required rebalancing trades when drift exceeds soft band
3. Compute mandatory rebalancing trades when drift exceeds hard band
4. Evaluate rebalancing feasibility: are the required trades executable given market conditions?
5. Prioritize rebalancing when multiple drift conditions are present simultaneously
6. Compute rebalancing cost estimates: transaction costs, market impact, taxes
7. Evaluate rebalancing benefit: does the drift correction justify the cost?
8. Generate rebalancing proposals for Decision Engine approval
9. Track rebalancing effectiveness post-execution: did actual trades restore target allocation?
10. Maintain rebalancing history for governance and performance attribution

**Inputs:**
- Target allocations from Allocation Engine (PC-07)
- Actual exposures from Exposure Engine (PC-08)
- Transaction cost estimates from Execution Engine (L11)
- Market liquidity data from Observation Engine
- Risk Engine approvals for proposed rebalancing trades

**Outputs:**
- Rebalancing proposals to Decision Engine (L10) for approval
- Rebalancing cost analysis to Portfolio Analytics Engine (PC-15)
- Rebalancing completion reports to Portfolio Governance Manager (PC-17)
- Rebalancing history to Portfolio Archive Manager (PC-19)

**Rebalancing Triggers:**

| Trigger Type         | Condition                                         | Priority |
|----------------------|---------------------------------------------------|----------|
| Soft drift           | Actual vs target drift > soft tolerance           | LOW      |
| Hard drift           | Actual vs target drift > hard tolerance           | HIGH     |
| Risk limit approach  | Any exposure approaching Risk Engine limit        | HIGH     |
| Regime change        | New regime from MarketIntelligence changes targets| MEDIUM   |
| Kill Switch clear    | Resumption after Kill Switch requires portfolio review| HIGH  |
| Session start        | Overnight market moves may have drifted allocation| MEDIUM   |
| New strategy launch  | New strategy allocation changes targets           | MEDIUM   |

**Cost-Benefit Rule:** Rebalancing is only recommended if the benefit (reduction in portfolio risk or alignment improvement) exceeds twice the estimated cost (transaction fees, slippage, taxes). This "2x cost test" prevents excessive turnover from trivial drift corrections.

---

### PC-11 — Performance Engine

**Purpose:** The Performance Engine computes all performance metrics for the portfolio, from simple returns to risk-adjusted metrics to time-weighted and money-weighted measures.

**Responsibilities:**
1. Compute daily portfolio return (total return: capital + income)
2. Compute cumulative return since inception
3. Compute session P&L: realized + unrealized (intraday)
4. Compute rolling returns: 7-day, 30-day, 90-day, since-inception
5. Compute risk-adjusted returns: Sharpe ratio, Sortino ratio, Calmar ratio
6. Compute maximum drawdown and current drawdown depth and duration
7. Compute hit rate: proportion of winning trades to total trades
8. Compute average win vs average loss (payoff ratio)
9. Compute strategy-level performance: how does each strategy contribute?
10. Compute benchmark-relative performance: alpha, information ratio
11. Compute time-weighted return (TWR) for unbiased performance measurement
12. Compute money-weighted return (MWR) for capital efficiency evaluation

**Inputs:**
- Position P&L from Position Manager (PC-04)
- Realized P&L from Holding Manager (PC-05)
- Benchmark returns from Benchmark Engine (PC-13)
- Historical performance from Portfolio Archive Manager (PC-19)

**Outputs:**
- Performance metrics to Portfolio Reporting Manager (PC-21)
- Return series to Learning Engine (L13) for strategy calibration
- Risk-adjusted metrics to Attribution Engine (PC-12)
- Performance dashboard to ControlTower (L17)
- Drawdown data to Risk Engine (RC-07)

**Key Performance Metrics:**

| Metric              | Definition                                            | Target (IIOS)  |
|---------------------|-------------------------------------------------------|----------------|
| Daily Return        | (NAV_today - NAV_yesterday) / NAV_yesterday           | > 0% on avg    |
| Total Return        | (Current NAV - Initial NAV) / Initial NAV             | Maximize        |
| Sharpe Ratio        | (Portfolio Return - Risk Free) / Portfolio Vol        | > 0.8           |
| Sortino Ratio       | (Portfolio Return - Risk Free) / Downside Vol         | > 1.0           |
| Calmar Ratio        | Annualized Return / Maximum Drawdown                  | > 1.5           |
| Max Drawdown        | Max peak-to-trough decline                            | < 15%           |
| Hit Rate            | Winning trades / Total trades                         | > 50%           |
| Payoff Ratio        | Average Win / Average Loss                            | > 1.5           |
| Alpha               | Portfolio Return - Beta x Benchmark Return            | > 0%            |
| Information Ratio   | Alpha / Tracking Error                                | > 0.5           |

---

### PC-12 — Attribution Engine

**Purpose:** The Attribution Engine decomposes portfolio performance into its contributing sources. It answers WHY the portfolio performed as it did — which decisions, strategies, sectors, and instruments were responsible for the observed returns.

**Responsibilities:**
1. Compute strategy-level performance attribution: how much P&L did each strategy contribute?
2. Compute sector-level attribution: did sector selection add or detract from performance?
3. Compute instrument-level attribution: which individual instruments drove performance?
4. Compute decision timing attribution: how much did entry/exit timing contribute vs instrument selection?
5. Compute allocation attribution: how much did allocation decisions (overweight/underweight) contribute?
6. Compute interaction effects: attribution residuals from combined effects
7. Produce Brinson-Fachler attribution decomposition (allocation effect + selection effect)
8. Produce factor attribution: how much did exposure to momentum, value, quality factors contribute?
9. Identify best and worst performing decisions for Learning Engine feedback
10. Maintain attribution history for learning and governance

**Inputs:**
- Holding history from Holding Manager (PC-05)
- Position P&L from Position Manager (PC-04)
- Benchmark returns from Benchmark Engine (PC-13)
- Strategy labels from Portfolio Registry (PC-01)
- Sector classifications from Knowledge Engine entity taxonomy

**Outputs:**
- Attribution reports to Portfolio Reporting Manager (PC-21)
- Attribution data to Learning Engine (L13) for strategy improvement
- Attribution summaries to Portfolio Analytics Engine (PC-15)
- Attribution history to Portfolio Archive Manager (PC-19)

**Brinson-Fachler Attribution Framework (Conceptual):**

Total Active Return = Allocation Effect + Selection Effect + Interaction Effect

Allocation Effect (sector level):
For each sector s: (w_portfolio_s - w_benchmark_s) x (R_benchmark_s - R_benchmark_total)
This measures: did we benefit from over/underweighting sectors relative to benchmark?

Selection Effect (sector level):
For each sector s: w_benchmark_s x (R_portfolio_s - R_benchmark_s)
This measures: within each sector, did our stock selection outperform the sector benchmark?

Interaction Effect:
Residual = Total Active Return - Allocation Effect - Selection Effect
This measures: the combined effect of allocation and selection decisions.

---

### PC-13 — Benchmark Engine

**Purpose:** The Benchmark Engine maintains benchmark definitions and computes benchmark performance for comparison to the IIOS portfolio. The benchmark is the reference against which the portfolio's value-add is measured.

**Responsibilities:**
1. Maintain benchmark definitions: NIFTY 50 as primary; custom benchmarks as required
2. Fetch benchmark prices and returns at each monitoring cycle
3. Compute daily, weekly, monthly, and since-inception benchmark returns
4. Compute benchmark sector weights for Brinson attribution
5. Compute benchmark volatility and risk metrics for relative risk measurement
6. Track benchmark component changes (index rebalancing events)
7. Compute tracking error: the standard deviation of the portfolio's return difference from benchmark
8. Compute information ratio: alpha / tracking error
9. Maintain multiple benchmarks for multi-strategy portfolios
10. Provide benchmark data for stress testing benchmark-relative impacts

**Inputs:**
- Benchmark index prices from data feeds (yfinance, Dhan)
- Benchmark composition from index provider data
- Portfolio returns from Performance Engine (PC-11)

**Outputs:**
- Benchmark returns to Performance Engine (PC-11)
- Benchmark sector weights to Attribution Engine (PC-12)
- Tracking error to Portfolio Analytics Engine (PC-15)
- Benchmark data to Portfolio Reporting Manager (PC-21)

**Primary IIOS Benchmarks:**

| Benchmark Code | Description                      | Use                              |
|----------------|----------------------------------|----------------------------------|
| NIFTY50        | NIFTY 50 Total Return Index      | Primary equity portfolio benchmark|
| NIFTYBANK      | Bank NIFTY Total Return          | Banking strategy benchmark        |
| NIFTY500       | NIFTY 500 (broader market)       | Mid/small cap strategy reference  |
| CASH_RATE      | Risk-free rate (T-bill / repo)   | Risk-adjusted return denominator  |

---

### PC-14 — Constraint Manager

**Purpose:** The Constraint Manager enforces all portfolio constraints: hard rules that must never be violated and soft preferences that should be followed unless there is a specific reason to deviate. It is the gatekeeper that prevents the Portfolio Manager from making changes that would violate defined portfolio rules.

**Responsibilities:**
1. Maintain the complete set of portfolio constraints (from governance and Risk Engine policies)
2. Validate proposed portfolio changes against all applicable constraints before approval
3. Classify constraints: HARD (blocking) or SOFT (warning with override capability)
4. Check new position requests against position concentration limits
5. Check trade requests against sector limits
6. Check trade requests against strategy allocation limits
7. Enforce minimum cash reserve constraint
8. Enforce diversification constraints (minimum position count, maximum correlation)
9. Track constraint violations: every violation is logged regardless of whether it is blocked
10. Support constraint override by human operators with mandatory audit trail
11. Provide constraint utilization reports to Portfolio Monitoring Engine (PC-16)
12. Coordinate with Risk Engine Constraint Manager for cross-engine constraint consistency

**Inputs:**
- Proposed portfolio changes from Portfolio Manager (PC-03)
- Policy constraints from Portfolio Governance Manager (PC-17)
- Risk Engine limits from Risk Engine (L7)
- Diversification data from Diversification Engine (PC-09)

**Outputs:**
- Constraint PASS / FAIL / WARNING responses to Portfolio Manager (PC-03)
- Constraint violations to Portfolio Audit Manager (PC-18)
- Constraint utilization to Portfolio Monitoring Engine (PC-16)

**Constraint Categories:**

| Category            | Examples                                              | Type  |
|---------------------|-------------------------------------------------------|-------|
| Position limits     | Single name <= 15% NAV                                | HARD  |
| Sector limits       | Sector <= 40% NAV                                     | HARD  |
| Cash minimum        | Cash >= 10% NAV                                       | HARD  |
| Strategy limits     | Strategy <= 60% capital                               | HARD  |
| Diversification     | Avg correlation <= 0.65; min 3 positions              | SOFT  |
| Rebalancing rules   | No rebalancing within 30 mins of market close         | HARD  |
| Instrument rules    | No new positions 15 mins before/after earnings        | SOFT  |
| Risk Engine flags   | No new positions when Risk Engine in DEGRADED mode    | HARD  |

**Failure Modes:** Constraint engine failure — assume all soft constraints are violated; allow only hard constraint checks from cache; alert operator.

---

### PC-15 — Portfolio Analytics Engine

**Purpose:** The Portfolio Analytics Engine transforms raw portfolio data into higher-order analytical insights. It provides the portfolio intelligence that informs strategy evolution, governance decisions, and long-term optimization.

**Responsibilities:**
1. Compute rolling portfolio statistics: return, volatility, Sharpe, drawdown over multiple windows
2. Identify strategy performance patterns: which strategies are improving or deteriorating?
3. Compute alpha decay analysis: is the portfolio's alpha eroding over time?
4. Compute factor exposure evolution: how has factor tilt changed over time?
5. Compute attribution trend analysis: is sector allocation adding or detracting consistently?
6. Compute portfolio efficiency frontier estimates (risk-return tradeoff visualization)
7. Compute strategy correlation matrix: are strategies becoming more correlated over time?
8. Identify behavioral patterns in portfolio management (over-trading, under-diversification)
9. Produce portfolio health summary for governance review
10. Support ad-hoc portfolio analysis queries from governance and operators

**Inputs:**
- Performance history from Performance Engine (PC-11)
- Attribution history from Attribution Engine (PC-12)
- Exposure time series from Exposure Engine (PC-08)
- Diversification time series from Diversification Engine (PC-09)
- Historical portfolio data from Portfolio Archive Manager (PC-19)

**Outputs:**
- Portfolio analytics reports to Portfolio Reporting Manager (PC-21)
- Portfolio intelligence to Learning Engine (L13)
- Analytics dashboard data to ControlTower (L17)
- Strategy analysis to ResearchLab (L15) for strategy governance

---

### PC-16 — Portfolio Monitoring Engine

**Purpose:** The Portfolio Monitoring Engine continuously monitors portfolio state during trading sessions and raises alerts when metrics approach or breach defined thresholds.

**Responsibilities:**
1. Monitor portfolio NAV in real-time for significant changes
2. Monitor unrealized P&L evolution: is the portfolio gaining or losing?
3. Monitor position-level unrealized P&L against stop-loss and target levels
4. Monitor allocation drift continuously against Allocation Engine targets
5. Monitor diversification quality against minimum standards
6. Monitor cash level against minimum reserve requirement
7. Monitor strategy-level performance during session
8. Alert when any metric approaches a defined threshold
9. Provide real-time dashboard data to ControlTower (L17)
10. Coordinate escalation to Portfolio Governance Manager when thresholds are breached

**Monitoring Schedule:**

| Metric              | Monitoring Frequency  | Alert Threshold                        |
|---------------------|-----------------------|----------------------------------------|
| Portfolio NAV       | Every 30 seconds      | > 1% change in 5 minutes               |
| Session P&L         | Every 30 seconds      | > 0.5% adverse move                   |
| Allocation drift    | Every 60 seconds      | Soft band breach                       |
| Cash level          | Every fill            | < 12% NAV (approaching 10% minimum)   |
| Position P&L        | Every 30 seconds      | Approaching stop-loss level             |
| Diversification     | Every 5 minutes       | < minimum threshold                    |
| Strategy performance| Every 5 minutes       | Strategy-specific alert thresholds     |

---

### PC-17 — Portfolio Governance Manager

**Purpose:** The Portfolio Governance Manager oversees the entire Portfolio Engine from a governance perspective. It ensures that portfolio management processes are followed, policies are adhered to, and human oversight is maintained.

**Responsibilities:**
1. Maintain the portfolio policy set (distinct from Risk Engine policies)
2. Monitor portfolio operations for policy compliance
3. Generate daily governance reports for human review
4. Track portfolio management decision quality over time
5. Manage the portfolio review calendar: daily, weekly, monthly reviews
6. Flag systematic portfolio management issues for investigation
7. Coordinate human override requests: log, validate, and facilitate
8. Enforce portfolio lifecycle governance: who can create, modify, and close portfolios?
9. Review and approve allocation changes exceeding defined thresholds
10. Produce portfolio compliance certifications for regulatory purposes

**Governance Review Schedule:**

| Review                    | Frequency  | Trigger Escalation                        |
|---------------------------|------------|-------------------------------------------|
| Session performance review| Daily      | Any session with unexpected P&L pattern   |
| Allocation review         | Weekly     | Any systematic allocation drift           |
| Strategy review           | Weekly     | Any strategy with consecutive loss days   |
| Constraint breach review  | As-needed  | Any HARD constraint violation             |
| Full portfolio review      | Monthly    | Standing review regardless of performance |

---

### PC-18 — Portfolio Audit Manager

**Purpose:** The Portfolio Audit Manager maintains the tamper-proof audit trail for all Portfolio Engine actions. Every portfolio state change, constraint check, allocation update, and governance action is recorded with a cryptographic hash chain.

**Responsibilities:**
1. Record all portfolio events with full context before they are executed
2. Maintain SHA-256 hash chain linking all audit records sequentially
3. Validate hash chain integrity at session start and end
4. Provide audit query interface for governance and compliance
5. Generate audit reports for regulatory compliance
6. Detect and alert on any hash chain corruption
7. Maintain audit record retention per policy (minimum 7 years)
8. Support time-point queries: what was the portfolio state at a specific timestamp?
9. Coordinate with Portfolio Archive Manager (PC-19) for long-term audit storage
10. Produce daily audit summary for governance review

**Audit Record Format:**

| Field           | Description                                        |
|-----------------|----------------------------------------------------|
| audit_id        | AUD-PRT-{YYYYMMDD}-{SEQ:08d}                        |
| timestamp       | UTC nanosecond timestamp                            |
| event_type      | FILL_PROCESSED / POSITION_OPENED / CASH_UPDATED etc |
| component_id    | PC-NN identifier of component generating event      |
| portfolio_id    | Affected portfolio identifier                       |
| inputs_hash     | SHA-256 hash of event input data                    |
| state_before    | Portfolio state snapshot before change              |
| state_after     | Portfolio state snapshot after change               |
| prior_hash      | Hash of immediately preceding audit record          |
| chain_hash      | SHA-256(prior_hash + audit_id + state_hash)         |

---

### PC-19 — Portfolio Archive Manager

**Purpose:** The Portfolio Archive Manager provides durable, long-term storage for all portfolio records, ensuring historical portfolio data is available for backtesting, performance analysis, and regulatory compliance.

**Responsibilities:**
1. Archive portfolio records at end of each session
2. Maintain portfolio performance time series for historical analysis
3. Maintain historical holdings and trade records
4. Implement retention policies (session data: 2 years; summary data: 7 years)
5. Manage storage efficiency through compression and summarization
6. Support point-in-time portfolio reconstruction for forensic analysis
7. Provide historical data to Performance Engine and Analytics Engine
8. Ensure archive integrity through periodic validation checksums
9. Support regulatory reporting data extracts
10. Coordinate data lifecycle: active → archive → purge (per policy)

---

### PC-20 — Portfolio Health Manager

**Purpose:** The Portfolio Health Manager monitors the health of the Portfolio Engine itself — ensuring all components are operational, data quality is maintained, and the overall portfolio management system is ready.

**Responsibilities:**
1. Monitor all 21 Portfolio Engine components for operational health
2. Compute Portfolio Engine Health Score (PEHS) from component health scores
3. Report PEHS to ControlTower (L17) for dashboard
4. Detect component degradation before failure
5. Initiate component recovery sequences
6. Maintain readiness certification: Portfolio Engine is READY only when PEHS >= threshold
7. Track data quality for all Portfolio Engine inputs
8. Monitor processing latency for all components vs defined SLAs
9. Coordinate with ControlTower event bus for portfolio system health events
10. Provide health history for capacity planning

**PEHS Thresholds:**

| PEHS Level  | Range       | Trading Implication                           |
|-------------|-------------|-----------------------------------------------|
| OPTIMAL     | 0.90 - 1.00 | Full portfolio management capability           |
| NOMINAL     | 0.75 - 0.89 | Normal operations; monitoring elevated         |
| DEGRADED    | 0.55 - 0.74 | Reduced new position approvals; alert operator |
| CRITICAL    | 0.30 - 0.54 | Portfolio updates halted; recovery required    |
| FAILED      | 0.00 - 0.29 | Emergency mode; Risk Engine Kill Switch review |

---

### PC-21 — Portfolio Reporting Manager

**Purpose:** The Portfolio Reporting Manager produces structured, audience-appropriate reports of portfolio state, performance, and analytics for operators, governance reviewers, and the ControlTower dashboard.

**Responsibilities:**
1. Produce intraday portfolio summary reports (position snapshot, P&L, allocation)
2. Produce session-end portfolio reports (full performance, attribution, governance summary)
3. Produce weekly portfolio review reports (rolling performance, strategy analysis)
4. Produce monthly portfolio reports (comprehensive analytics, attribution trends)
5. Produce ad-hoc reports on operator request
6. Format reports for Telegram delivery (concise, operator-facing)
7. Format reports for dashboard display (ControlTower L17)
8. Format reports for governance review (detailed, compliance-facing)
9. Maintain report archive for historical reference
10. Support custom report generation from Portfolio Analytics data

**Report Types:**

| Report                  | Frequency   | Audience           | Key Content                      |
|-------------------------|-------------|--------------------|---------------------------------|
| Session Start Snapshot  | Daily       | Operator           | Current holdings, cash, targets |
| Intraday Update         | Hourly      | Operator           | P&L, alerts, open positions     |
| Session Close Summary   | Daily       | Operator/Governance| Full performance, attribution   |
| Weekly Review           | Weekly      | Governance         | Rolling metrics, strategy health|
| Monthly Analytics Report| Monthly     | Senior Review      | Full analytics, recommendations |
| Governance Report       | Daily       | Compliance         | Constraint checks, violations   |

---

## PART IV — PORTFOLIO LIFECYCLE

### 4.0 Lifecycle Design Philosophy

The Portfolio Lifecycle describes the complete sequence of stages a portfolio traverses from initial creation through eventual retirement. Unlike a trade (which has a clear start and end), a portfolio is a living entity that evolves continuously over time. Portfolio evolution is managed and governed — the portfolio does not simply happen; it is actively constructed and maintained.

The lifecycle is governed by three principles:
1. **Intentional creation:** No portfolio exists without explicit governance authorization.
2. **Continuous management:** Between creation and retirement, the portfolio is continuously monitored, managed, and governed.
3. **Complete historicity:** Every stage in the lifecycle is fully recorded and auditable.

---

### 4.1 Portfolio Lifecycle Stages

**Stage 1 — Portfolio Creation (PLS-01)**

*Trigger:* Governance authorization for a new portfolio.
*Actions:* Portfolio identity created in Portfolio Registry; configuration set; benchmark assigned; initial capital allocated; constraint set defined; governance record created.
*Duration:* One-time at portfolio inception.
*Output:* Portfolio in INITIALIZING state with all configuration complete.
*Validation:* All required fields present; benchmark valid; initial capital > 0; constraints within policy.

**Stage 2 — Capital Allocation (PLS-02)**

*Trigger:* Portfolio moves from INITIALIZING to ACTIVE on first capital deposit.
*Actions:* Initial capital registered in Cash Manager; strategy allocations set in Allocation Engine; risk budget assigned by Risk Engine; constraint validation passes.
*Duration:* Typically same day as creation for funded portfolios.
*Output:* Cash balance reflects initial capital; allocation targets set; portfolio status = ACTIVE.

**Stage 3 — Position Opening (PLS-03)**

*Trigger:* First trade execution fills arrive for the portfolio.
*Actions:* Position Manager opens first positions; Holding Manager creates holding records; Exposure Engine computes initial exposure; Diversification Engine updates diversification score; Performance Engine begins tracking.
*Duration:* Ongoing throughout active portfolio life.
*Output:* Positions added to portfolio; NAV computed; exposure monitored.

**Stage 4 — Portfolio Monitoring (PLS-04)**

*Trigger:* Portfolio is active; continuous throughout the session.
*Actions:* Real-time P&L tracking; allocation drift monitoring; diversification monitoring; risk metric updates; threshold checks; alert generation when thresholds approach.
*Duration:* Continuous during trading sessions.
*Output:* Continuous state updates; alerts; dashboard data; governance feed.

**Stage 5 — Rebalancing (PLS-05)**

*Trigger:* Allocation drift exceeds tolerance band; regime change; risk limit approach; explicit governance instruction.
*Actions:* Rebalancing Engine computes required trades; cost-benefit analysis; proposal to Decision Engine; Risk Engine approval; execution; post-rebalancing validation.
*Duration:* Event-driven; may occur multiple times per session.
*Output:* Portfolio allocation restored to target bands; rebalancing record.

**Stage 6 — Performance Evaluation (PLS-06)**

*Trigger:* Session end; weekly review; monthly review; on-demand.
*Actions:* Performance Engine computes all returns metrics; Attribution Engine decomposes performance; Benchmark Engine provides comparison; reports generated.
*Duration:* Session end is the primary trigger; typically < 5 minutes.
*Output:* Complete performance report; attribution analysis; benchmark comparison.

**Stage 7 — Risk Review (PLS-07)**

*Trigger:* Session end; scheduled risk review; significant market event.
*Actions:* Risk Engine produces post-session risk summary; Portfolio Analytics Engine analyzes risk evolution; strategy risk attribution computed; Risk Engine VaR backtest.
*Duration:* Session end; typically < 10 minutes.
*Output:* Session risk summary; risk attribution by strategy; VaR backtest result.

**Stage 8 — Capital Adjustment (PLS-08)**

*Trigger:* Capital injection (additional funds deposited) or capital withdrawal (funds removed from account).
*Actions:* Cash Manager records capital event; NAV recomputed; allocation targets recalculated; percentage-based metrics adjusted for capital change; performance records adjusted to exclude capital flow effects (time-weighted return).
*Duration:* As needed.
*Output:* Updated NAV; adjusted allocation targets; performance continuity maintained.

**Stage 9 — Portfolio Evolution (PLS-09)**

*Trigger:* Strategic review; strategy performance review; governance-directed evolution.
*Actions:* Portfolio type may be amended (e.g., adding options strategies to an equity portfolio); strategy set may be expanded or contracted; allocation models may be revised; benchmark may be updated.
*Duration:* Periodic; typically monthly or quarterly.
*Output:* Updated portfolio configuration; version increment; governance record.

**Stage 10 — Reporting (PLS-10)**

*Trigger:* Continuous; session-end primary; weekly and monthly scheduled.
*Actions:* Portfolio Reporting Manager produces all required reports; governance reports delivered to reviewers; dashboard updated; Telegram notifications sent.
*Duration:* Continuous.
*Output:* All required reports delivered; acknowledgments recorded.

**Stage 11 — Archive (PLS-11)**

*Trigger:* Session end for session-level archival; portfolio closure for full archival.
*Actions:* Portfolio Archive Manager writes all session records; audit chain closed; performance summary added to historical archive; all positions and holdings archived.
*Duration:* Session end; typically < 2 minutes.
*Output:* Session records permanently stored; archive confirmation.

**Stage 12 — Retirement (PLS-12)**

*Trigger:* Portfolio closure decision by governance authority.
*Actions:* All positions closed (or transferred); final performance report produced; portfolio status = CLOSED then ARCHIVED; all records archived permanently; portfolio removed from active management.
*Duration:* Depends on position wind-down time.
*Output:* Closed portfolio; final report; permanent archive.

---

### 4.2 Portfolio State Machine

`
PORTFOLIO STATE MACHINE
════════════════════════

PROPOSED (pending governance approval)
  │ Governance approves
  ▼
INITIALIZING (configuration complete; awaiting capital)
  │ Capital deposited; allocation set
  ▼
ACTIVE (normal trading state)
  ├── Normal operations: monitoring, trading, rebalancing
  ├── Kill Switch active → SUSPENDED
  ├── Risk Engine DEGRADED → RESTRICTED
  └── Governance close decision → CLOSING
SUSPENDED (Kill Switch or risk halt)
  ├── Kill Switch cleared + human auth → ACTIVE
  └── Permanent halt instruction → CLOSING
RESTRICTED (degraded operations — reduced capabilities)
  ├── System recovery → ACTIVE
  └── Governance decision → CLOSING
CLOSING (winding down positions)
  ├── All positions closed; final report complete → CLOSED
CLOSED (no positions; governance sign-off pending)
  ├── Governance sign-off → ARCHIVED
ARCHIVED (permanent historical record; no active management)
  └── [Terminal state]
`

---

### 4.3 Portfolio State Reference

| Status        | Description                                            |
|---------------|--------------------------------------------------------|
| PROPOSED      | Governance approval pending                            |
| INITIALIZING  | Configuration complete; awaiting capital               |
| ACTIVE        | Normal operations; fully managed                       |
| RESTRICTED    | Reduced operations; some constraints elevated          |
| SUSPENDED     | All trading halted; Kill Switch or system event        |
| CLOSING       | Position wind-down in progress                         |
| CLOSED        | No positions; governance sign-off pending              |
| ARCHIVED      | Permanently archived; historical record only           |

---

### 4.4 Intraday Lifecycle Sequence Diagram

`
INTRADAY PORTFOLIO LIFECYCLE — SEQUENCE DIAGRAM
════════════════════════════════════════════════

[Session Start 09:10 IST]
  │
  ├── PC-01 Registry: Load portfolio state from prior session
  ├── PC-04 Positions: Load open positions; reconcile with broker
  ├── PC-06 Cash: Load cash balance; reconcile with broker
  ├── PC-07 Allocation: Compute current targets for today
  ├── PC-09 Diversification: Initial diversification score
  ├── PC-16 Monitoring: Begin monitoring loops
  └── PC-20 Health: PEHS computed; readiness confirmed

[Market Open 09:15 IST]
  │
  ├── [Every 30 seconds]
  │   ├── PC-04: Mark positions to market
  │   ├── PC-11: Update session P&L
  │   ├── PC-16: Check thresholds
  │   └── PC-17: Dashboard update → L17 ControlTower
  │
  ├── [On Execution Fill]
  │   ├── PC-03: Receive fill; coordinate state update
  │   ├── PC-04: Update position (open/increase/reduce/close)
  │   ├── PC-05: Update holding record
  │   ├── PC-06: Update cash balance
  │   ├── PC-08: Update exposure vectors
  │   ├── PC-18: Write audit record
  │   └── PC-11: Update P&L
  │
  ├── [Every 60 seconds]
  │   ├── PC-07: Check allocation drift
  │   ├── PC-09: Update diversification score
  │   └── PC-10: Evaluate rebalancing need
  │
  └── [On Rebalancing Trigger]
      ├── PC-10: Compute rebalancing trades
      ├── PC-14: Constraint validation
      ├── L10 Decision Engine: Approval
      └── L11 Execution Engine: Trade execution

[Market Close 15:30 IST]
  │
  ├── PC-11: Final P&L computation
  ├── PC-12: Attribution analysis
  ├── PC-13: Benchmark comparison
  ├── PC-15: Analytics update
  ├── PC-17: Governance report generation
  ├── PC-18: Audit chain closure
  ├── PC-19: Session archive
  └── PC-21: Reports delivered (Telegram + Dashboard)
`

---

## PART V — PORTFOLIO SERVICES

### 5.0 Service Architecture Overview

Portfolio Services are the named, purpose-bounded computation units that implement the Portfolio Engine's functional capabilities. Services are independently invocable, designed to return results for specific queries or computations without modifying shared portfolio state directly.

Services are organized into fifteen service units: PS-01 through PS-15.

---

### PS-01 — Portfolio Management Service

**Purpose:** Exposes portfolio state management operations: portfolio creation, configuration updates, status transitions. The primary orchestration interface for the Portfolio Engine.

**Interface:** create_portfolio(config) → PortfolioRecord; update_config(portfolio_id, updates) → PortfolioRecord; transition_status(portfolio_id, new_status, reason) → StatusRecord

---

### PS-02 — Position Service

**Purpose:** Provides position query and update services. Manages the lifecycle of individual positions within the portfolio.

**Interface:** get_positions(portfolio_id) → List[Position]; get_position(position_id) → Position; update_from_fill(fill_record) → Position; close_position(position_id, fill_record) → ClosedPosition

---

### PS-03 — Holding Service

**Purpose:** Provides holding history queries and management. Extends position tracking through the complete holding lifecycle.

**Interface:** get_current_holdings(portfolio_id) → List[Holding]; get_historical_holdings(portfolio_id, start_date, end_date) → List[ClosedHolding]; get_holding_stats(holding_id) → HoldingStats (including MAE, MFE, duration)

---

### PS-04 — Cash Service

**Purpose:** Provides cash balance queries, cash event recording, and buying power calculations.

**Interface:** get_cash_balance(portfolio_id) → CashBalance; record_cash_event(portfolio_id, event) → CashEvent; get_buying_power(portfolio_id) → BuyingPower; reconcile_with_broker(portfolio_id, broker_cash) → ReconciliationResult

---

### PS-05 — Allocation Service

**Purpose:** Provides allocation target computation, drift measurement, and allocation update operations.

**Interface:** get_target_allocation(portfolio_id) → AllocationTargets; compute_drift(portfolio_id) → DriftReport; update_allocation(portfolio_id, new_targets, reason) → AllocationRecord

---

### PS-06 — Rebalancing Service

**Purpose:** Evaluates rebalancing need and generates rebalancing proposals.

**Interface:** evaluate_rebalancing_need(portfolio_id) → RebalancingNeedReport; generate_rebalancing_proposal(portfolio_id, drift_report) → RebalancingProposal; record_rebalancing_outcome(proposal_id, execution_results) → RebalancingRecord

---

### PS-07 — Performance Service

**Purpose:** Computes and returns performance metrics for any portfolio over any period.

**Interface:** get_performance(portfolio_id, start_date, end_date) → PerformanceReport; get_session_pnl(portfolio_id) → SessionPnL; get_risk_adjusted_metrics(portfolio_id, period) → RiskAdjustedMetrics

---

### PS-08 — Benchmark Service

**Purpose:** Provides benchmark data and benchmark-relative performance metrics.

**Interface:** get_benchmark_return(benchmark_code, start_date, end_date) → BenchmarkReturn; get_relative_performance(portfolio_id, benchmark_code, period) → RelativePerformance; get_tracking_error(portfolio_id, benchmark_code, period) → TrackingError

---

### PS-09 — Analytics Service

**Purpose:** Provides portfolio analytics and intelligence insights.

**Interface:** get_analytics_summary(portfolio_id) → AnalyticsSummary; get_factor_exposure_history(portfolio_id, factor, period) → FactorExposureHistory; get_strategy_correlation_matrix(portfolio_id) → StrategyCorrelationMatrix

---

### PS-10 — Reporting Service

**Purpose:** Generates and delivers portfolio reports in defined formats.

**Interface:** generate_session_report(portfolio_id) → SessionReport; generate_governance_report(portfolio_id) → GovernanceReport; deliver_telegram_summary(portfolio_id, operator_id) → DeliveryStatus

---

### PS-11 — Monitoring Service

**Purpose:** Provides real-time portfolio monitoring streams and snapshots.

**Interface:** subscribe_portfolio_stream(subscriber_id, portfolio_id, filters) → PortfolioEventStream; get_portfolio_snapshot(portfolio_id) → PortfolioSnapshot; get_threshold_utilization(portfolio_id) → ThresholdStatus

---

### PS-12 — Governance Service

**Purpose:** Provides governance reporting and compliance checking.

**Interface:** get_governance_report(portfolio_id, session_date) → GovernanceReport; check_policy_compliance(portfolio_id) → ComplianceReport; record_override(portfolio_id, reason, authority) → OverrideRecord

---

### PS-13 — Audit Service

**Purpose:** Provides audit record queries and integrity reporting.

**Interface:** query_audit(portfolio_id, start_time, end_time, event_type) → List[AuditRecord]; validate_chain_integrity(portfolio_id) → ChainIntegrityReport; generate_audit_report(portfolio_id, period) → AuditReport

---

### PS-14 — Archive Service

**Purpose:** Provides access to historical portfolio data for analysis and reporting.

**Interface:** get_historical_portfolio(portfolio_id, as_of_date) → HistoricalPortfolioSnapshot; get_performance_history(portfolio_id, start_date, end_date) → PerformanceTimeSeries; get_attribution_history(portfolio_id, period) → AttributionHistory

---

### PS-15 — Health Service

**Purpose:** Provides Portfolio Engine health status and readiness certification.

**Interface:** get_health_status() → PEHSReport; get_component_health(component_id) → ComponentHealth; certify_ready(portfolio_id) → ReadinessCertification

---

## PART VI — PORTFOLIO PROCESSING PIPELINES

### 6.0 Pipeline Design Philosophy

Portfolio Processing Pipelines are the structured, sequential chains that transform inputs into portfolio state changes and outputs. Each pipeline has a defined trigger, a mandatory sequence of processing stages, and defined outputs. Pipelines ensure that portfolio operations are always performed in the correct order, with the appropriate validations, and with complete audit coverage.

Ten pipelines are defined: PP-01 through PP-10.

---

### PP-01 — Execution-to-Portfolio Pipeline

**Purpose:** The primary pipeline that transforms execution fills into portfolio state changes.

**Trigger:** New execution fill record received from Execution Engine (L11).

**Flow Diagram:**

`
PP-01: EXECUTION-TO-PORTFOLIO PIPELINE
════════════════════════════════════════

[L11 Execution Engine]
  │ Fill record: symbol, qty, price, direction, strategy, timestamp
  ▼
[PC-18 Portfolio Audit Manager]
  │ Create pre-fill audit record (AUDIT BEFORE STATE CHANGE)
  │ State before: position, cash, NAV snapshots
  ▼
[PC-14 Constraint Manager]
  │ Post-fill constraint validation:
  │ Would this fill breach any HARD constraints?
  │ If BREACH: halt pipeline; alert operator; fill queued for review
  ▼
[PC-03 Portfolio Manager: Begin Atomic Transaction]
  │
  ├── [PC-04 Position Manager]
  │   │ BUY fill: open or increase position; update avg cost
  │   │ SELL fill: reduce or close position; compute realized P&L
  │   └── Position record updated
  │
  ├── [PC-05 Holding Manager]
  │   │ Create or update holding record
  │   │ Track MAE/MFE from this fill
  │   └── Holding record updated
  │
  ├── [PC-06 Cash Manager]
  │   │ BUY: deduct (qty x price + fees) from cash
  │   │ SELL: add (qty x price - fees) to cash
  │   └── Cash balance updated
  │
  └── [PC-03 Portfolio Manager: Commit Transaction]
      │ NAV recomputed = sum(positions) + cash
      │ Consistency check: NAV matches expected
      └── State committed atomically

[PC-08 Exposure Engine]
  │ Update exposure vectors for all affected dimensions
  ▼
[PC-09 Diversification Engine]
  │ Update diversification score
  ▼
[PC-11 Performance Engine]
  │ Update session P&L
  ▼
[PC-18 Portfolio Audit Manager]
  │ Complete audit record: state_after, fill reference, chain_hash
  ▼
[PC-16 Portfolio Monitoring Engine]
  │ Check thresholds with new portfolio state
  ▼
[L17 ControlTower]
  └── Portfolio dashboard update broadcast
`

**Latency SLA:** < 500ms end-to-end from fill receipt to audit record completion.

**Failure Handling:** If any stage fails during the transaction, the entire transaction is rolled back. The fill is marked PROCESSING_FAILED and re-queued. Alert is raised immediately.

---

### PP-02 — Position Update Pipeline

**Purpose:** Updates position mark-to-market values as new prices arrive. Does not change positions — only revalues them.

**Trigger:** New market price data (every 30 seconds during session).

**Flow Diagram:**

`
PP-02: POSITION UPDATE PIPELINE (MARK-TO-MARKET)
══════════════════════════════════════════════════

[Observation Engine: New Market Prices]
  │ Price updates for held symbols
  ▼
[PC-04 Position Manager]
  │ For each open position:
  │   current_value = qty x new_price
  │   unrealized_pnl = current_value - cost_basis
  │   position_weight = current_value / NAV
  ▼
[PC-03 Portfolio Manager]
  │ Recompute NAV = sum(position values) + cash
  ▼
[PC-08 Exposure Engine]
  │ Update exposure vectors with new valuations
  ▼
[PC-11 Performance Engine]
  │ Update unrealized P&L; session P&L = realized + unrealized
  ▼
[PC-16 Portfolio Monitoring Engine]
  │ Check: any position approaching stop-loss or target?
  │ Check: session P&L thresholds?
  └── Alert if threshold reached
`

**No audit required for price updates** (read-only state; not a portfolio change).

---

### PP-03 — Cash Management Pipeline

**Purpose:** Manages all non-execution cash events: dividends, fees, interest, capital injections, and withdrawals.

**Trigger:** Non-execution cash event notification.

**Flow Diagram:**

`
PP-03: CASH MANAGEMENT PIPELINE
═════════════════════════════════

[Cash Event: Dividend / Fee / Capital]
  │ Event type, amount, reference, timestamp
  ▼
[PC-18 Portfolio Audit Manager]
  │ Pre-event audit record
  ▼
[PC-06 Cash Manager]
  │ Validate event: is amount plausible?
  │ Record cash event with all metadata
  │ Update cash balance
  ▼
[PC-03 Portfolio Manager]
  │ Recompute NAV
  ▼
[PC-07 Allocation Engine]
  │ For capital events: recompute allocation targets (% of new NAV)
  ▼
[PC-11 Performance Engine]
  │ Adjust performance calculation: capital events affect MWR; TWR adjusts for capital flows
  ▼
[PC-18 Portfolio Audit Manager]
  └── Complete audit record
`

---

### PP-04 — Allocation Pipeline

**Purpose:** Recomputes and updates portfolio allocation targets.

**Trigger:** Regime change; governance instruction; scheduled review; significant performance event.

**Flow Diagram:**

`
PP-04: ALLOCATION PIPELINE
═══════════════════════════

[Allocation Trigger]
  │ Regime change / governance update / schedule
  ▼
[PC-07 Allocation Engine]
  │ Gather inputs: strategy performance, regime signals, risk budgets
  │ Compute new target allocations by strategy, sector, cash
  │ Validate allocations: sum = 100%; within policy limits
  ▼
[PC-14 Constraint Manager]
  │ Validate proposed allocations against portfolio constraints
  ▼
[PC-17 Portfolio Governance Manager]
  │ For significant changes (>10% strategy weight shift):
  │ Governance review required before implementation
  ▼
[PC-07 Allocation Engine]
  │ Apply approved allocation changes
  ▼
[PC-10 Rebalancing Engine]
  │ Compute drift between new targets and current exposures
  │ If drift > tolerance: generate rebalancing proposal
  ▼
[PC-18 Portfolio Audit Manager]
  └── Allocation change audit record with rationale
`

---

### PP-05 — Rebalancing Pipeline

**Purpose:** Implements the complete rebalancing workflow from drift detection through execution.

**Trigger:** Allocation drift exceeds tolerance band.

**Flow Diagram:**

`
PP-05: REBALANCING PIPELINE
════════════════════════════

[PC-10 Rebalancing Engine: Drift Detected]
  │ Drift report: which allocations are outside bands?
  ▼
[PC-14 Constraint Manager]
  │ Validate proposed rebalancing trades against constraints
  ▼
[PC-10 Rebalancing Engine: Cost-Benefit Analysis]
  │ Estimate cost: transaction fees + slippage
  │ Estimate benefit: risk reduction + alignment improvement
  │ 2x cost test: benefit > 2x cost? If no → defer rebalancing
  ▼
[Risk Engine L6/L7]
  │ Risk assessment of proposed rebalancing trades
  │ APPROVED / REDUCED / REJECTED
  ▼
[L10 Decision Engine]
  │ Decision Engine evaluates rebalancing trades as proposals
  │ (Rebalancing is a risk management action, not an alpha opportunity)
  ▼
[L11 Execution Engine]
  │ Execute approved rebalancing trades
  ▼
[PP-01 Execution-to-Portfolio Pipeline]
  │ Process fills; update portfolio state
  ▼
[PC-10 Rebalancing Engine: Post-Rebalancing Validation]
  │ Did rebalancing achieve target alignment?
  │ Compute post-rebalancing drift
  ▼
[PC-17 Portfolio Governance Manager]
  └── Record rebalancing event; governance report
`

---

### PP-06 — Performance Pipeline

**Purpose:** Computes portfolio performance metrics at session end.

**Trigger:** Session end (15:30 IST); scheduled reviews; on-demand.

**Flow Diagram:**

`
PP-06: PERFORMANCE PIPELINE
════════════════════════════

[Session End Trigger]
  ▼
[PC-04 Position Manager]
  │ Final mark-to-market for all positions
  ▼
[PC-11 Performance Engine]
  │ Compute session P&L: realized + unrealized
  │ Compute daily return (% NAV change)
  │ Compute rolling returns: 7d, 30d, 90d, since-inception
  │ Compute risk metrics: Sharpe, Sortino, Calmar
  │ Compute Max DD; update drawdown history
  │ Compute hit rate; average win vs loss
  ▼
[PC-13 Benchmark Engine]
  │ Fetch benchmark return for session and periods
  │ Compute alpha, beta, tracking error
  ▼
[PC-12 Attribution Engine]
  │ Strategy attribution: P&L by strategy
  │ Sector attribution: P&L by sector
  │ Instrument attribution: P&L by instrument
  │ Brinson-Fachler decomposition: allocation + selection effects
  ▼
[PC-15 Portfolio Analytics Engine]
  │ Update rolling analytics; alpha decay; factor exposure trends
  ▼
[PC-21 Portfolio Reporting Manager]
  │ Session close report; Telegram summary; governance report
  ▼
[L13 Learning Engine]
  └── Deliver strategy performance outcomes for model update
`

---

### PP-07 — Analytics Pipeline

**Purpose:** Produces higher-order portfolio intelligence from accumulated portfolio data.

**Trigger:** Weekly scheduled; monthly scheduled; on-demand from governance.

**Flow Diagram:**

`
PP-07: ANALYTICS PIPELINE
══════════════════════════

[Analytics Trigger: Weekly / Monthly / On-Demand]
  ▼
[PC-19 Portfolio Archive Manager]
  │ Load historical portfolio data for analysis period
  ▼
[PC-15 Portfolio Analytics Engine]
  │ Compute strategy performance trends: improving or deteriorating?
  │ Compute alpha decay: is alpha generation eroding?
  │ Compute factor exposure evolution over period
  │ Compute strategy correlation matrix
  │ Compute attribution trends: consistent alpha sources?
  │ Identify behavioral patterns: over-trading, concentration drift
  ▼
[PC-11 Performance Engine]
  │ Multi-period performance summary
  │ Risk-adjusted returns over multiple windows
  ▼
[PC-21 Portfolio Reporting Manager]
  │ Analytics report delivered to governance
  ▼
[L13 Learning Engine]
  │ Portfolio intelligence for model recalibration
  ▼
[L15 ResearchLab]
  └── Analytics for strategy governance and promotion decisions
`

---

### PP-08 — Reporting Pipeline

**Purpose:** Produces and delivers all portfolio reports on schedule.

**Trigger:** Session end (daily report); weekly schedule; monthly schedule; on-demand.

**Flow Diagram:**

`
PP-08: REPORTING PIPELINE
══════════════════════════

[Report Trigger]
  ▼
[PC-21 Portfolio Reporting Manager]
  │ Gather data from: Performance Engine, Attribution, Analytics, Governance
  │ Format for audience: Operator (Telegram), Dashboard (L17), Governance (detailed)
  ▼
[Report Type Routing]
  ├── Session close → Telegram session summary → Operator
  ├── Dashboard update → L17 ControlTower → Live display
  ├── Governance report → Detailed PDF/text → Reviewer queue
  └── Weekly/Monthly → Comprehensive report → Senior review queue
  ▼
[Delivery Confirmation]
  └── Delivery status recorded; undelivered reports escalated
`

---

### PP-09 — Governance Pipeline

**Purpose:** Implements the portfolio governance review and compliance cycle.

**Trigger:** Session end; daily governance timer; policy review schedule.

**Flow Diagram:**

`
PP-09: GOVERNANCE PIPELINE
═══════════════════════════

[Governance Trigger]
  ▼
[PC-17 Portfolio Governance Manager]
  │ Collect governance-relevant events:
  │   - Constraint violations
  │   - Human overrides
  │   - Allocation changes > threshold
  │   - Rebalancing events
  │   - Unusual performance
  ▼
[PC-14 Constraint Manager]
  │ Compliance audit: all constraints checked vs actual portfolio
  ▼
[PC-18 Portfolio Audit Manager]
  │ Generate governance report from audit records
  ▼
[PC-15 Portfolio Analytics Engine]
  │ Governance analytics: is portfolio drifting from its mandate?
  ▼
[Human Review Queue]
  │ Governance report delivered via Telegram + dashboard
  └── Acknowledgment required before next session
`

---

### PP-10 — Archive Pipeline

**Purpose:** Archives all portfolio records at session end for long-term retention.

**Trigger:** Session end.

**Flow Diagram:**

`
PP-10: ARCHIVE PIPELINE
════════════════════════

[Session End]
  ▼
[PC-11 Performance Engine]
  │ Compute final session performance snapshot
  ▼
[PC-18 Portfolio Audit Manager]
  │ Close audit chain for session
  │ Compute session chain integrity hash
  ▼
[PC-19 Portfolio Archive Manager]
  │ Write session portfolio snapshot (all positions, cash, NAV)
  │ Write session performance metrics
  │ Write session attribution results
  │ Write closed holdings from session
  │ Write governance events
  │ Write closed audit chain bundle
  ▼
[Archive Validation]
  │ Read-back verification: spot check 5 random records
  └── Archive confirmation: PASS / FAIL → alert if FAIL
`

---

## PART VII — PORTFOLIO QUALITY FRAMEWORK

### 7.0 Quality Framework Purpose

The Portfolio Quality Framework defines how the Portfolio Engine measures its own operational quality. Quality is not an optional feature — a portfolio management system that cannot demonstrate its accuracy, completeness, and consistency cannot be trusted to manage capital.

The Framework provides 12 quality dimensions that compose the Portfolio Quality Score (PQS). The PQS governs the Portfolio Engine's contribution to IIOS decision-making: a degraded Portfolio Engine should reduce its influence until quality is restored.

---

### 7.1 Portfolio Quality Dimensions

**PQD-01 — Accuracy (Weight: 0.20)**

*Definition:* The degree to which portfolio state (positions, cash, NAV, P&L) correctly reflects the actual financial reality.

*Measurement:* Daily broker reconciliation pass rate; NAV reconciliation with broker account; position count reconciliation; P&L reconciliation.

*Target:* 100% position-level reconciliation with broker; < 0.01% NAV discrepancy.

*Degradation triggers:* Any position discrepancy with broker; NAV mismatch > 0.1%; P&L calculation error detected.

---

**PQD-02 — Completeness (Weight: 0.15)**

*Definition:* The degree to which all portfolio records are complete, with all required fields populated and all events captured.

*Measurement:* Proportion of records with complete required fields; proportion of events with corresponding audit records; proportion of holding records with complete lifecycle.

*Target:* 100% of fills have corresponding position updates; 100% of position changes have audit records.

---

**PQD-03 — Consistency (Weight: 0.12)**

*Definition:* The degree to which portfolio state is internally consistent: NAV = positions + cash; exposure vectors agree across components; attribution totals agree with performance.

*Measurement:* NAV consistency check pass rate (computed NAV vs sum of components); attribution completeness (attribution total = performance total).

*Target:* NAV consistency: 100% (zero tolerance for inconsistency). Attribution completeness: within 0.1% residual.

---

**PQD-04 — Diversification (Weight: 0.10)**

*Definition:* The degree to which the portfolio maintains its target diversification profile. A portfolio that systematically drifts toward concentration is degrading its quality as a managed portfolio.

*Measurement:* Proportion of sessions where diversification score >= minimum threshold; frequency of concentration breaches; average HHI vs target.

---

**PQD-05 — Allocation Efficiency (Weight: 0.10)**

*Definition:* The degree to which the portfolio's actual allocations match its target allocations. A portfolio that is consistently far from its targets is not being managed to its intended design.

*Measurement:* Average allocation drift across all strategies and sectors; proportion of time within soft tolerance bands.

---

**PQD-06 — Performance Measurement (Weight: 0.08)**

*Definition:* The degree to which performance metrics are computed accurately, consistently, and completely. Incorrect performance measurement misleads the Learning Engine and governance.

*Measurement:* Cross-validation of performance metrics (alternative computation of same metric should agree); time-weighted return vs money-weighted return consistency.

---

**PQD-07 — Benchmark Accuracy (Weight: 0.08)**

*Definition:* The degree to which benchmark data is accurate, timely, and correctly applied to performance calculations.

*Measurement:* Benchmark data freshness; benchmark return accuracy vs external sources; attribution using benchmark weights produces correct allocation/selection split.

---

**PQD-08 — Risk Alignment (Weight: 0.07)**

*Definition:* The degree to which the portfolio's actual risk profile aligns with the Risk Engine's approved risk levels. A portfolio that is systematically outside its Risk Engine limits is a risk management failure.

*Measurement:* Proportion of time within all Risk Engine limits; frequency of Risk Engine constraint triggers from portfolio actions.

---

**PQD-09 — Explainability (Weight: 0.04)**

*Definition:* The degree to which portfolio decisions, changes, and performance can be explained in plain language with reference to specific inputs.

*Measurement:* Proportion of portfolio changes with complete explanation chains; proportion of performance periods with complete attribution.

---

**PQD-10 — Traceability (Weight: 0.03)**

*Definition:* The degree to which every portfolio state can be traced back through its history to its originating fills. Full traceability supports forensic analysis and audit.

*Measurement:* Proportion of portfolio states with complete fill-to-state traces; proportion of decisions reproducible from archived inputs.

---

**PQD-11 — Auditability (Weight: 0.02)**

*Definition:* The degree to which the audit chain is complete, intact, and tamper-proof.

*Measurement:* Hash chain integrity score; audit record completeness; gap rate.

---

**PQD-12 — Operational Stability (Weight: 0.01)**

*Definition:* The degree to which the Portfolio Engine operates without failures, crashes, or processing errors.

*Measurement:* Component uptime; fill processing error rate; recovery time from failures.

---

### 7.2 PQS Formula and Tiers

**PQS = 0.20 x PQD-01 + 0.15 x PQD-02 + 0.12 x PQD-03 + 0.10 x PQD-04**
**    + 0.10 x PQD-05 + 0.08 x PQD-06 + 0.08 x PQD-07 + 0.07 x PQD-08**
**    + 0.04 x PQD-09 + 0.03 x PQD-10 + 0.02 x PQD-11 + 0.01 x PQD-12**

All weights sum to 1.00. All dimension scores in [0.0, 1.0].

| Tier       | PQS Range    | Meaning                                        |
|------------|--------------|------------------------------------------------|
| EXCELLENT  | 0.88 - 1.00  | Portfolio Engine operating at full quality      |
| GOOD       | 0.72 - 0.87  | Portfolio Engine operating well; minor issues   |
| ACCEPTABLE | 0.55 - 0.71  | Portfolio Engine operational; investigate issues|
| MARGINAL   | 0.35 - 0.54  | Portfolio Engine degraded; restrict operations  |
| FAILED     | 0.00 - 0.34  | Portfolio Engine failed; halt; recovery required|

---

### 7.3 PQS Component Interaction Effects

Quality degradation in some dimensions causes compounding effects in others. The following interaction effects are recognized and factored into the quality response protocol:

**Accuracy (PQD-01) → Consistency (PQD-03):** An accuracy failure (position mismatch) always produces a consistency failure (NAV does not match components). When PQD-01 falls, PQD-03 should be expected to fall in the same period.

**Completeness (PQD-02) → Traceability (PQD-10):** Missing records break traceability chains. When PQD-02 falls, PQD-10 will also fall.

**Allocation Efficiency (PQD-05) → Diversification (PQD-04):** A portfolio that is far from its targets is also likely to be more concentrated than intended. When PQD-05 is low, PQD-04 should be re-evaluated.

**Benchmark Accuracy (PQD-07) → Performance Measurement (PQD-06):** Incorrect benchmark data makes alpha/beta calculations unreliable. When PQD-07 falls, all benchmark-relative performance metrics are suspect.

---

### 7.4 PQS Response Protocol

| PQS Tier   | IIOS Response                                                       |
|------------|---------------------------------------------------------------------|
| EXCELLENT  | No restrictions; normal operations                                  |
| GOOD       | No restrictions; investigate any dimension below 0.70               |
| ACCEPTABLE | Portfolio signals still valid; P&L figures flagged as approximate   |
| MARGINAL   | Portfolio signals marked uncertain; Decision Engine reduces weight   |
| FAILED     | Portfolio Engine output suspended; human review required            |

---

## PART VIII — PORTFOLIO GOVERNANCE

### 8.0 Governance Philosophy

Portfolio governance is the structured oversight that ensures the Portfolio Engine operates according to its mandate, within its constraints, and in service of the defined investment objectives. Governance is not bureaucracy — it is the mechanism that makes portfolio management trustworthy and reproducible.

Four governance principles govern all portfolio management activities:

**GP-01 — Mandate Adherence:** The portfolio always operates within its stated mandate. The mandate is the governing document; any deviation requires explicit governance authorization.

**GP-02 — Transparency:** All portfolio actions, their rationale, and their outcomes are documented and available for review. Opacity is a governance failure.

**GP-03 — Human Oversight:** Automated portfolio management operates within bounds set by human governance. Human authorities can inspect, adjust, or override within defined protocols.

**GP-04 — Continuous Improvement:** Governance reviews produce actionable insights that improve portfolio management over time. Governance is not merely a compliance exercise.

---

### 8.1 Portfolio Ownership and Authority

| Authority Level | Role                        | Scope of Authority                           |
|-----------------|-----------------------------|----------------------------------------------|
| System Owner    | Portfolio Engine architect  | System design, constitutional rules          |
| Operations Lead | Operator (human)            | Override, suspend, resume, adjust parameters |
| Portfolio AI    | Portfolio Manager PC-03     | Automated state changes within mandate       |
| Risk Engine     | L6/L7 (CapitalRisk/Control) | Risk limit enforcement; Kill Switch          |
| Audit Authority | Portfolio Audit Manager     | Audit record integrity; chain validation     |

---

### 8.2 Portfolio Naming Convention

**Portfolio IDs:**
PRT-{TYPE_CODE}-{YYYYMMDD}-{SEQ:06d}
Example: PRT-EQUITY-20250115-000001

**Position IDs:**
POS-{SYMBOL}-{YYYYMMDD}-{SEQ:08d}
Example: POS-TATASTEEL-20250115-00000001

**Holding IDs:**
HLD-{SYMBOL}-{YYYYMMDD}-{SEQ:08d}
Example: HLD-RELIANCE-20250115-00000001

**Cash Event IDs:**
CSH-{EVENT_TYPE}-{YYYYMMDD}-{SEQ:08d}
Example: CSH-FILL-20250115-00000001

**Rebalancing IDs:**
RBL-{YYYYMMDD}-{SEQ:06d}
Example: RBL-20250115-000001

**Audit Record IDs:**
AUD-PRT-{YYYYMMDD}-{SEQ:08d}
Example: AUD-PRT-20250115-00000001

---

### 8.3 Versioning Policy

| Object Type       | Versioning Scheme                                       |
|-------------------|---------------------------------------------------------|
| Portfolio Config  | Version number increments on every configuration change |
| Allocation Model  | Named version; previous versions archived               |
| Constraint Set    | Named version; all versions retained                    |
| Performance Model | Semantic versioning: MAJOR.MINOR.PATCH                  |
| Architecture Doc  | IIOS-PRT-ENG-ARCH-001 rev XX                            |

---

### 8.4 Portfolio Governance Review Schedule

| Review Type              | Frequency   | Scope                                                          |
|--------------------------|-------------|----------------------------------------------------------------|
| Session Review           | Daily       | Session P&L; constraint compliance; rebalancing events        |
| Allocation Review        | Weekly      | Strategy allocations; allocation drift; rebalancing history   |
| Strategy Review          | Weekly      | Strategy performance vs targets; rotation decisions           |
| Analytics Review         | Monthly     | Full analytics report; alpha decay; factor exposure evolution |
| Governance Full Review   | Monthly     | Mandate compliance; constraint adequacy; version review       |
| Architecture Review      | Quarterly   | Component health; quality evolution; improvement planning     |

---

### 8.5 Override Policy

Human overrides of automated portfolio decisions are legitimate and governed. Every override must be:

1. **Recorded:** Override record created with operator identity, timestamp, reason, and decision changed.
2. **Bounded:** Override cannot violate HARD constitutional rules (see Part IX). It can override SOFT constraints and automated recommendations.
3. **Reviewed:** All overrides appear in the daily governance report and the weekly review.
4. **Evaluated:** Patterns of overrides that consistently outperform or underperform the automated system are studied and inform system improvement.

Override types and authority:

| Override Type                  | Authority         | Requires Reason? |
|--------------------------------|-------------------|------------------|
| Reject rebalancing proposal    | Operations Lead   | Yes              |
| Adjust position size           | Operations Lead   | Yes              |
| Close position early           | Operations Lead   | Yes              |
| Suspend portfolio              | Operations Lead   | Yes              |
| Change allocation targets      | Operations Lead   | Yes              |
| Change strategy set            | System Owner      | Yes              |
| Change benchmark               | System Owner      | Yes              |
| Change constitutional rule     | System Owner only | Yes; full review |

---

### 8.6 Compliance Framework

The Portfolio Engine is designed for compliance with the following regimes:

| Domain                | Compliance Requirement                                                 |
|-----------------------|------------------------------------------------------------------------|
| SEBI Regulations      | Position limits; reporting; KYC; insider trading prevention           |
| Broker Requirements   | Dhan-specific order limits; margin requirements; risk parameters      |
| Internal Policy       | IIOS constitutional rules (Part IX); portfolio mandate compliance     |
| Audit Requirements    | 7-year record retention; complete audit chain; point-in-time recovery |

---

### 8.7 Security Policy

**Portfolio State Security:**

- Portfolio state is owned exclusively by the Portfolio Engine. No other IIOS layer writes portfolio state directly.
- Portfolio data is stored in the persistent data/ volume. Access is restricted to the Portfolio Engine service.
- Performance data, attribution results, and governance reports are read-only exports.

**Audit Chain Security:**

- The SHA-256 hash chain is the tamper-detection mechanism. Any modification to a historical record breaks the hash chain.
- Hash chain integrity is verified at the start of every session and included in every governance report.
- A broken hash chain is a CRITICAL alert requiring immediate human review.

**Human Override Security:**

- Override records include the authorizing operator identity.
- Overrides are irreversible in the audit chain (the record of the override is permanent).
- Repeated overrides from the same operator in the same session are escalated to senior review.

---

### 8.8 Data Retention Policy

| Record Type                   | Detailed Retention  | Summary Retention   |
|-------------------------------|---------------------|---------------------|
| Intraday positions (30s)      | Current session     | Not retained        |
| Session performance snapshots | 2 years             | 7 years             |
| Closed holding records        | 7 years             | Permanent           |
| Audit records                 | 7 years             | Permanent           |
| Cash event records            | 7 years             | Permanent           |
| Governance reports            | 7 years             | Permanent           |
| Attribution records           | 5 years             | 7 years             |
| Rebalancing records           | 5 years             | 7 years             |

---

## PART IX — PORTFOLIO CONSTITUTION

### 9.0 Constitutional Architecture

The Portfolio Constitution is the collection of rules that govern all Portfolio Engine operations. Constitutional rules are not guidelines — they are inviolable constraints that define the boundary between legitimate portfolio management and system failure.

Rules are classified as HARD or SOFT:
- **HARD:** Never violated by any automated action. Violation causes pipeline halt and human escalation.
- **SOFT:** Threshold guidance that triggers alerts and review; can be overridden with governance authorization.

Rules are grouped into 15 categories: PC-A through PC-O.

---

### 9.1 PC-A — Portfolio Integrity Rules

**PC-A-001 [HARD]:** Every portfolio must have a unique Portfolio ID in the Portfolio Registry. No portfolio operates without a registry record.

**PC-A-002 [HARD]:** Portfolio state is owned exclusively by the Portfolio Manager (PC-03). No other component or external system may write portfolio state directly.

**PC-A-003 [HARD]:** NAV consistency invariant must always hold: NAV = sum(all position market values) + cash balance. Any state that violates this invariant must be halted and investigated.

**PC-A-004 [HARD]:** Portfolio status transitions are one-directional for terminal states: CLOSED and ARCHIVED portfolios cannot be re-activated.

**PC-A-005 [SOFT]:** Portfolio PQS must be >= 0.55 (ACCEPTABLE tier) for automated operations to proceed without restriction.

**PC-A-006 [HARD]:** Every portfolio has exactly one designated benchmark. A portfolio without a benchmark cannot report performance.

**PC-A-007 [SOFT]:** Portfolio PEHS must be >= 0.55 (DEGRADED threshold) for normal operations. Below 0.55: RESTRICTED mode.

---

### 9.2 PC-B — Holding Integrity Rules

**PC-B-001 [HARD]:** Every open position must have a corresponding holding record. Orphan positions (position without holding) are a data integrity failure.

**PC-B-002 [HARD]:** Holding records are immutable once closed. A closed holding record cannot be modified; only supplementary annotation is permitted.

**PC-B-003 [HARD]:** The realized P&L in a closed holding record must match the sum of fill P&Ls for that holding. Discrepancies > 0.01% are a data integrity failure.

**PC-B-004 [SOFT]:** Average holding duration should be reviewed if consistently below 10 minutes (hyperactive trading pattern) or above 60 days (position hoarding pattern).

**PC-B-005 [HARD]:** MAE and MFE must be tracked and recorded for every holding. A holding record without MAE/MFE is incomplete and cannot be used for learning.

---

### 9.3 PC-C — Position Integrity Rules

**PC-C-001 [HARD]:** No position may exist without a traceable execution fill. A position created without a fill record is a phantom position — an immediate investigation trigger.

**PC-C-002 [HARD]:** Position direction (LONG or SHORT) is fixed at open and cannot change. Reducing a LONG to zero and reopening SHORT requires two separate position records.

**PC-C-003 [HARD]:** Position average cost is computed using the FIFO or AVCO method consistently throughout the portfolio life. The method cannot change after positions are open.

**PC-C-004 [SOFT]:** No single position should exceed 20% of portfolio NAV under normal operations. Positions > 20% are a concentration alert.

**PC-C-005 [HARD]:** A position quantity must always be >= 0. Negative quantities represent data corruption and must trigger immediate investigation.

**PC-C-006 [SOFT]:** Maximum 15 simultaneous open positions under the default IIOS configuration.

**PC-C-007 [HARD]:** Position weight (position value / NAV) is recomputed at every mark-to-market cycle. Stale position weights older than 60 seconds are a data quality failure during a trading session.

---

### 9.4 PC-D — Cash Integrity Rules

**PC-D-001 [HARD]:** Cash balance must always be >= 0. A negative cash balance is a system error. Any operation that would produce a negative cash balance is halted.

**PC-D-002 [HARD]:** Every change to cash balance must have a corresponding cash event record with event type, amount, and reference ID.

**PC-D-003 [HARD]:** Cash minimum reserve: cash balance must be >= 10% of NAV at all times. Any trade that would reduce cash below 10% of NAV is rejected at the constraint level.

**PC-D-004 [SOFT]:** Cash held above 30% of NAV for more than one session is a cash drag alert — the Allocation Engine should investigate whether excess cash should be deployed.

**PC-D-005 [HARD]:** Cash reconciliation with broker account must be performed at session start and session end. Unresolved discrepancies > INR 1,000 require human review before trading.

---

### 9.5 PC-E — Allocation Integrity Rules

**PC-E-001 [HARD]:** All strategy allocation targets must sum to <= 100% of NAV. The remainder is implicitly held in cash.

**PC-E-002 [HARD]:** No single strategy may be allocated > 40% of NAV without explicit governance authorization.

**PC-E-003 [SOFT]:** Allocation drift (actual vs target) should not exceed the soft tolerance band (typically 5%) for more than one session without triggering a rebalancing evaluation.

**PC-E-004 [HARD]:** Allocation targets must be approved through the Allocation Pipeline before implementation. No unilateral allocation change by any single component.

**PC-E-005 [SOFT]:** Sector concentration: no sector > 35% of equity NAV.

---

### 9.6 PC-F — Diversification Integrity Rules

**PC-F-001 [SOFT]:** Minimum diversification score: 0.40. Below 0.40, concentration alert is raised.

**PC-F-002 [SOFT]:** Minimum instrument count in equity portfolio: 3. A single-stock portfolio is not considered diversified.

**PC-F-003 [SOFT]:** Maximum position weight: 25% of NAV. Position concentration beyond 25% requires governance review.

**PC-F-004 [HARD]:** No single strategy's positions may account for 100% of portfolio value. Multi-strategy architecture requires at least 2 active strategies unless in initial ramp-up or wind-down.

---

### 9.7 PC-G — Rebalancing Integrity Rules

**PC-G-001 [HARD]:** Rebalancing trades must pass the 2x cost test. A rebalancing that costs more than half its expected benefit is deferred.

**PC-G-002 [HARD]:** All rebalancing proposals must be reviewed by the Decision Engine before execution. No autonomous rebalancing without Decision Engine clearance.

**PC-G-003 [SOFT]:** Rebalancing frequency should not exceed 2 events per session per strategy allocation. Frequent rebalancing is a signal of unstable allocation targets.

**PC-G-004 [HARD]:** Post-rebalancing validation is mandatory. If rebalancing execution falls more than 20% short of its target (e.g., fills not executed), the Allocation Engine records the shortfall and adjusts targets.

---

### 9.8 PC-H — Performance Integrity Rules

**PC-H-001 [HARD]:** Time-weighted return (TWR) is the primary performance metric. TWR eliminates distortion from capital flows and provides the most honest view of investment skill.

**PC-H-002 [HARD]:** P&L is not recognized as realized until the corresponding closing fill is confirmed by the Execution Engine. Unrealized P&L is always clearly distinguished from realized P&L.

**PC-H-003 [HARD]:** All performance metrics are computed from actual transaction costs, not theoretical costs. Reported P&L reflects what actually happened, including fees and slippage.

**PC-H-004 [SOFT]:** Session drawdown > 2% of NAV triggers an intraday review. Session drawdown > 3% is a Risk Guardian escalation.

**PC-H-005 [HARD]:** Performance metric computation is reproducible. Given the same input data, the same metrics must always be produced. Non-deterministic performance calculation is a quality failure.

---

### 9.9 PC-I — Benchmark Integrity Rules

**PC-I-001 [HARD]:** Every benchmark return must be sourced from a designated external data provider, not computed from portfolio data. Self-referential benchmarks are prohibited.

**PC-I-002 [SOFT]:** Benchmark data staleness: benchmark return for current session must be updated at least every 60 minutes during trading hours.

**PC-I-003 [HARD]:** Attribution calculations that use benchmark weights must use the benchmark's actual composition, not a proxy. Systematic benchmark substitution without governance approval is prohibited.

---

### 9.10 PC-J — Governance Rules

**PC-J-001 [HARD]:** Every governance review must be acknowledged by an authorized reviewer within one session. Unacknowledged governance reports are escalated.

**PC-J-002 [HARD]:** Changes to constitutional rules require System Owner authorization and a documented governance record. No constitutional change is made without a record.

**PC-J-003 [SOFT]:** Governance reports must be delivered within 30 minutes of session close.

**PC-J-004 [HARD]:** The Portfolio Engine never creates investment opportunities, never generates trade ideas, and never initiates trades except in the context of Risk Engine-approved rebalancing. Mandate creep into alpha generation is constitutionally prohibited.

---

### 9.11 PC-K — Auditability Rules

**PC-K-001 [HARD]:** Every change to portfolio state produces an audit record before and after the change. No state change without a corresponding audit entry.

**PC-K-002 [HARD]:** Audit records are immutable. No audit record may be deleted or modified after creation.

**PC-K-003 [HARD]:** The SHA-256 hash chain must be intact. A broken hash chain is a CRITICAL incident requiring immediate investigation.

**PC-K-004 [HARD]:** All audit records must include the full state before and after the change, the action taken, and the component responsible.

---

### 9.12 PC-L — Historical Preservation Rules

**PC-L-001 [HARD]:** Historical records are never deleted. Archival is additive; no record is removed from the archive.

**PC-L-002 [HARD]:** Point-in-time reconstruction must be possible for any portfolio state at any past point in time within the retention window.

**PC-L-003 [SOFT]:** Archive read-back verification (PP-10) must pass at least 4 sessions out of 5. Repeated verification failures trigger a full archive audit.

---

### 9.13 PC-M — Security Rules

**PC-M-001 [HARD]:** Only the Portfolio Manager (PC-03) may write portfolio state. All other components read portfolio state or receive outputs from the Portfolio Manager.

**PC-M-002 [HARD]:** No external system (outside IIOS) may write portfolio state. Broker-confirmed data is ingested through defined ingest pipelines, never through direct state writes.

**PC-M-003 [HARD]:** Override authority is recorded in the audit chain. Unauthorized overrides (those lacking a governance record) are flagged as security events.

---

### 9.14 PC-N — Human Override Rules

**PC-N-001 [HARD]:** Human overrides are legitimate and explicitly supported. The Portfolio Engine is designed to accept and record human overrides without resistance.

**PC-N-002 [HARD]:** Every human override must be accompanied by a reason code and operator identity. Anonymous overrides are not accepted.

**PC-N-003 [SOFT]:** Patterns of overrides that consistently improve outcomes are evaluated for incorporation into automated policy. The system learns from human judgment.

**PC-N-004 [SOFT]:** Patterns of overrides that consistently harm outcomes are flagged for governance review and operator coaching.

---

### 9.15 PC-O — Policy Compliance Rules

**PC-O-001 [HARD]:** The Portfolio Engine operates within all broker-imposed limits (Dhan order limits, margin requirements, instrument restrictions).

**PC-O-002 [HARD]:** The Portfolio Engine enforces all IIOS-wide position limits and concentration limits.

**PC-O-003 [HARD]:** The Portfolio Engine cooperates with the Risk Guardian (L9) as the supreme Kill Switch authority. When the Risk Guardian suspends the portfolio, the Portfolio Engine immediately transitions to SUSPENDED state.

**PC-O-004 [SOFT]:** Regulatory reporting data is extracted from Portfolio Engine records. If Portfolio Engine data quality is below ACCEPTABLE, regulatory reports are flagged as provisional pending quality restoration.

---

## PART X — PORTFOLIO READINESS CHECKLIST

### 10.0 Readiness Framework

Before the Portfolio Engine is certified for live trading operations, all components, data sources, governance mechanisms, and operational procedures must be verified. The Portfolio Readiness Checklist is the formal certification that the Portfolio Engine is ready to manage capital.

Readiness is assessed across five categories: Component Readiness, Data Readiness, Governance Readiness, Operational Readiness, and Integration Readiness.

---

### 10.1 Component Readiness Checklist (21 items)

Each component must pass its readiness check before the Portfolio Engine is certified.

| ID     | Component                       | Check                                                    | Status |
|--------|---------------------------------|----------------------------------------------------------|--------|
| CR-01  | PC-01 Portfolio Registry        | Registry loads and responds to queries                   |        |
| CR-02  | PC-02 Portfolio Catalog         | All 20 portfolio types resolvable                        |        |
| CR-03  | PC-03 Portfolio Manager         | Create/update/transition operations functional           |        |
| CR-04  | PC-04 Position Manager          | Position open/update/close operations functional         |        |
| CR-05  | PC-05 Holding Manager           | Holding create/update/close operations functional        |        |
| CR-06  | PC-06 Cash Manager              | Cash event recording and balance queries functional      |        |
| CR-07  | PC-07 Allocation Engine         | Allocation computation and drift measurement functional  |        |
| CR-08  | PC-08 Exposure Engine           | Exposure vector computation functional                   |        |
| CR-09  | PC-09 Diversification Engine    | Diversification score computation functional             |        |
| CR-10  | PC-10 Rebalancing Engine        | Rebalancing need evaluation and proposal generation      |        |
| CR-11  | PC-11 Performance Engine        | All 10 performance metrics computable                    |        |
| CR-12  | PC-12 Attribution Engine        | Brinson-Fachler attribution functional                   |        |
| CR-13  | PC-13 Benchmark Engine          | All 4 primary benchmarks loading correctly               |        |
| CR-14  | PC-14 Constraint Manager        | All constraint categories enforced                       |        |
| CR-15  | PC-15 Portfolio Analytics       | Rolling analytics computation functional                 |        |
| CR-16  | PC-16 Portfolio Monitoring      | Monitoring loops active; alerts delivered                |        |
| CR-17  | PC-17 Portfolio Governance      | Governance reports generatable                           |        |
| CR-18  | PC-18 Portfolio Audit Manager   | Audit records created; hash chain intact                 |        |
| CR-19  | PC-19 Portfolio Archive Manager | Archive write and read-back functional                   |        |
| CR-20  | PC-20 Portfolio Health Manager  | PEHS computation functional                              |        |
| CR-21  | PC-21 Portfolio Reporting       | All 6 report types generatable                           |        |

---

### 10.2 Data Readiness Checklist

| ID     | Data Source                     | Check                                                     | Status |
|--------|---------------------------------|-----------------------------------------------------------|--------|
| DR-01  | Broker Account State            | Cash balance and positions loadable from Dhan API         |        |
| DR-02  | Market Prices                   | Real-time price feed operational (Dhan or yfinance)       |        |
| DR-03  | Benchmark Data                  | NIFTY50, NIFTYBANK, NIFTY500, CASH_RATE loading           |        |
| DR-04  | Portfolio State                 | Prior session portfolio state loads correctly             |        |
| DR-05  | Audit Chain                     | Prior session audit chain intact (hash check passes)      |        |
| DR-06  | Historical Holdings             | Historical holding data accessible for attribution        |        |
| DR-07  | Strategy Registry               | All active strategies loaded with IDs and configurations  |        |

---

### 10.3 Governance Readiness Checklist

| ID     | Governance Element              | Check                                                     | Status |
|--------|---------------------------------|-----------------------------------------------------------|--------|
| GR-01  | Portfolio Mandate               | Portfolio mandate document present and current            |        |
| GR-02  | Constraint Set                  | Constraint set versioned and approved                     |        |
| GR-03  | Allocation Targets              | Current allocation targets set and governance-approved    |        |
| GR-04  | Benchmark Assignment            | Primary benchmark assigned and current                    |        |
| GR-05  | Prior Session Review            | Prior session governance report acknowledged              |        |
| GR-06  | Override Log                    | All prior overrides recorded and reviewed                 |        |

---

### 10.4 Operational Readiness Checklist

| ID     | Operation                       | Check                                                     | Status |
|--------|---------------------------------|-----------------------------------------------------------|--------|
| OR-01  | PP-01 Execution-to-Portfolio    | End-to-end fill processing pipeline functional            |        |
| OR-02  | PP-02 Position Update           | Mark-to-market cycle functional                           |        |
| OR-03  | PP-05 Rebalancing               | Rebalancing pipeline fully wired                          |        |
| OR-04  | PP-06 Performance               | Session-end performance pipeline functional               |        |
| OR-05  | PP-10 Archive                   | Archive pipeline functional; prior session archived       |        |
| OR-06  | Telegram Delivery               | Session summary delivery to operator confirmed            |        |
| OR-07  | Dashboard Feed                  | L17 ControlTower dashboard receiving portfolio updates    |        |

---

### 10.5 Integration Readiness Checklist

| ID     | Integration Target              | Check                                                     | Status |
|--------|---------------------------------|-----------------------------------------------------------|--------|
| IR-01  | L6 CapitalRisk                  | Risk budget queries functional; NAV delivered to L6       |        |
| IR-02  | L7 RiskControl                  | Risk limits enforced; Kill Switch integration tested      |        |
| IR-03  | L9 Risk Guardian                | Portfolio suspension on Kill Switch trigger confirmed     |        |
| IR-04  | L10 Decision Engine             | Portfolio snapshot delivered to L10 correctly             |        |
| IR-05  | L11 Execution Engine            | Fill receipts processed through PP-01 correctly           |        |
| IR-06  | L12 TradeMonitoring             | Holding data fed to TradeMonitor correctly                |        |
| IR-07  | L13 Learning Engine             | Closed holding outcomes delivered to LearningEngine       |        |
| IR-08  | L14 Performance Analytics       | Performance data delivered to DrawdownAnalyzer            |        |
| IR-09  | L17 ControlTower                | Portfolio state delivered to ControlTower dashboard       |        |

---

### 10.6 Readiness State Machine

`
PORTFOLIO ENGINE READINESS STATE MACHINE
══════════════════════════════════════════

NOT_CHECKED (initial state; no checks performed)
  │ Start session startup sequence
  ▼
CHECKING (readiness checks in progress)
  │ All checks pass
  ▼
CERTIFIED (fully ready for operation)
  │ Normal operations; monitoring continues
  ▼
DEGRADED (some checks failed; restricted operations)
  │ Issues resolved
  ▼
CERTIFIED

From any state:
  │ HARD constitutional violation
  ▼
SUSPENDED (halted; human review required)
  │ Human review and sign-off
  ▼
CERTIFIED (after full re-verification)
`

---

### 10.7 Post-Session Assessment

After every trading session, the following assessment is performed and added to the governance record:

**Assessment Dimensions:**
1. **Execution Quality:** Were all fills processed correctly and within SLA?
2. **Reconciliation Quality:** Did portfolio state match broker at session end?
3. **Performance Quality:** Are all performance metrics complete and consistent?
4. **Attribution Quality:** Is full attribution available for all strategies?
5. **Governance Quality:** Is governance report complete and delivered?
6. **Archive Quality:** Is session archive complete with passing read-back?
7. **PQS Summary:** What was today's PQS and is it within acceptable range?
8. **Alerts Summary:** What alerts fired today? Were they appropriate?
9. **Override Summary:** Any overrides today? Were they warranted?
10. **Improvement Opportunities:** One specific improvement identified for the next session.

---

## SUPPLEMENT A — PORTFOLIO TAXONOMY REFERENCE

### Supplement A.1 — Complete Portfolio Type Reference

| Code  | Name                  | Primary Use Case                        | IIOS Status |
|-------|-----------------------|-----------------------------------------|-------------|
| PT-01 | Equity Portfolio      | Indian equities, NSE listed             | Primary     |
| PT-02 | Options Portfolio     | NSE options strategies                  | Supported   |
| PT-03 | Futures Portfolio     | NIFTY/BANKNIFTY futures                 | Planned     |
| PT-04 | Commodity Portfolio   | MCX commodities                         | Future      |
| PT-05 | Currency Portfolio    | INR/USD, NSE FX segment                 | Future      |
| PT-06 | Crypto Portfolio      | Not applicable under current mandate    | Not Planned |
| PT-07 | Long Only Portfolio   | Current primary operating mode          | Primary     |
| PT-08 | Long/Short Portfolio  | With qualified short-selling capability | Planned     |
| PT-09 | Income Portfolio      | Dividend focus; not current mandate     | Future      |
| PT-10 | Growth Portfolio      | High-growth equity focus                | Supported   |
| PT-11 | Value Portfolio       | Deep value with patience horizon        | Future      |
| PT-12 | Momentum Portfolio    | Trend-following; current IIOS model     | Primary     |
| PT-13 | Dividend Portfolio    | Dividend yield focus                    | Future      |
| PT-14 | Balanced Portfolio    | Mix of equity and debt instruments      | Future      |
| PT-15 | Sector Portfolio      | Concentrated sector strategy            | Supported   |
| PT-16 | Thematic Portfolio    | Theme-driven (e.g., digital India)      | Planned     |
| PT-17 | Global Portfolio      | Multi-country; beyond current mandate   | Future      |
| PT-18 | Multi-Asset Portfolio | Cross-asset; beyond current mandate     | Future      |
| PT-19 | AI Portfolio          | Fully AI-driven; current IIOS model     | Primary     |
| PT-20 | Hybrid Portfolio      | AI + human collaborative management     | Supported   |

---

### Supplement A.2 — Component Tier Reference

| Tier   | Components                            | Tier Role                                      |
|--------|---------------------------------------|------------------------------------------------|
| Core   | PC-01, PC-02, PC-03, PC-04            | Identity, registry, state management           |
| Data   | PC-05, PC-06, PC-07, PC-08, PC-09     | Financial records, allocation, exposure        |
| Engine | PC-10, PC-11, PC-12, PC-13, PC-14, PC-15 | Processing, analytics, constraints         |
| Ops    | PC-16, PC-17, PC-18, PC-19, PC-20, PC-21 | Monitoring, governance, audit, reporting   |

---

### Supplement A.3 — Service-to-Component Mapping

| Service | Primary Components             | Secondary Components             |
|---------|--------------------------------|----------------------------------|
| PS-01   | PC-01, PC-02, PC-03            | PC-18                            |
| PS-02   | PC-04, PC-05                   | PC-03, PC-18                     |
| PS-03   | PC-05                          | PC-19                            |
| PS-04   | PC-06                          | PC-03, PC-18                     |
| PS-05   | PC-07                          | PC-14, PC-18                     |
| PS-06   | PC-10                          | PC-07, PC-14                     |
| PS-07   | PC-11                          | PC-12, PC-13                     |
| PS-08   | PC-13                          | PC-11                            |
| PS-09   | PC-15                          | PC-11, PC-12                     |
| PS-10   | PC-21                          | PC-11, PC-12, PC-17              |
| PS-11   | PC-16                          | PC-04, PC-11                     |
| PS-12   | PC-17                          | PC-14, PC-18                     |
| PS-13   | PC-18                          | None                             |
| PS-14   | PC-19                          | PC-11, PC-12                     |
| PS-15   | PC-20                          | All components                   |

---

## SUPPLEMENT B — ALLOCATION MODELS

### Supplement B.1 — Allocation Model Overview

The Portfolio Engine supports five allocation models. The active model is set at portfolio configuration and may be changed through the Allocation Pipeline with governance approval.

---

### Supplement B.2 — Model 1: Equal Weight

**Concept:** Each active strategy receives an equal share of the investable portfolio NAV.

**Formula:** Allocation_i = (1 / N) x Investable_NAV
where N = number of active strategies, Investable_NAV = total NAV - minimum cash reserve.

**Strengths:** Simple; transparent; easy to explain; robust when strategy quality is unknown.

**Weaknesses:** Ignores differences in strategy performance and volatility; suboptimal when strategy quality varies significantly.

**IIOS Use Case:** Suitable during early deployment when strategy performance history is limited (< 30 days per strategy).

**Rebalancing Trigger:** When strategy count changes; when allocation drift exceeds soft band.

---

### Supplement B.3 — Model 2: Risk Parity

**Concept:** Allocate capital so that each strategy contributes equally to total portfolio risk, as measured by its return volatility.

**Formula:** Allocation_i = (1 / Vol_i) / sum(1 / Vol_j for all j) x Investable_NAV
where Vol_i = annualized return volatility of strategy i, computed from rolling 60-session history.

**Risk Contribution:** RC_i = Allocation_i x Vol_i / sum(Allocation_j x Vol_j for all j)
Target: RC_i = 1/N for all i.

**Strengths:** High-volatility strategies don't dominate; lower-volatility strategies get more capital; improves diversification.

**Weaknesses:** Low-volatility strategies may have lower expected returns; does not account for strategy correlations.

**IIOS Use Case:** Use when strategies have different volatility profiles. Re-evaluate when correlations between strategies change significantly.

**Rebalancing Trigger:** When any strategy volatility estimate shifts > 20% from the estimate used at last allocation.

---

### Supplement B.4 — Model 3: Performance Weighted

**Concept:** Allocate capital in proportion to recent strategy performance, rewarding strategies that are working and reducing exposure to those that are not.

**Formula:** Score_i = w_wr x WinRate_i + w_sr x SharpeRatio_i + w_ret x TotalReturn_i
Allocation_i = max(Score_i, 0) / sum(max(Score_j, 0) for all j) x Investable_NAV

Default weights: w_wr = 0.4, w_sr = 0.4, w_ret = 0.2 (configurable).

**Minimum Floor:** Every strategy with Score_i > 0 receives at minimum 5% of Investable_NAV (prevents complete starvation of strategies in short drawdowns).

**Strengths:** Rewards performance; automatically reduces exposure to underperforming strategies.

**Weaknesses:** Chases performance; may over-weight strategies during regime-specific runs; requires sufficient history.

**IIOS Use Case:** Primary model once strategies have > 60 sessions of performance history.

---

### Supplement B.5 — Model 4: Regime-Adaptive

**Concept:** Adjust strategy allocations based on the current market regime, increasing allocations to strategies that have historically performed best in the current regime.

**Inputs:** Market regime from L2 MarketIntelligence; per-strategy performance by regime from L3 MetaLearning.

**Formula:** 
Base allocation = Performance Weighted model
Regime multiplier = RegimePerformance(strategy_i, current_regime) / AvgRegimePerformance(strategy_i)
Adjusted allocation = Base_i x RegimeMultiplier_i
Final allocation = Normalized adjusted allocation ensuring sum = Investable_NAV, with floor and ceiling applied.

**Ceiling:** No strategy may exceed 40% of Investable_NAV regardless of regime multiplier.
**Floor:** Active strategies receive minimum 3% of Investable_NAV.

**Strengths:** Incorporates forward-looking regime signal; improves risk-adjusted returns across regime cycles.

**Weaknesses:** Requires reliable regime detection; regime transitions introduce rebalancing friction.

**IIOS Use Case:** This is the target operating model for mature IIOS deployment (strategies with > 90 sessions of regime-specific history).

---

### Supplement B.6 — Model 5: Fixed Budget

**Concept:** Each strategy operates on a fixed capital budget, regardless of performance. Capital is only changed by explicit governance decision.

**Formula:** Allocation_i = FixedBudget_i (governance-set constant)
Cash = NAV - sum(FixedBudget_i for all i)

**Strengths:** Deterministic; immune to performance chasing; predictable risk profile.

**Weaknesses:** Does not adapt to performance; may hold excess cash as strategies close positions; requires active human maintenance.

**IIOS Use Case:** Suitable during controlled experiments; for testing new strategies in isolation; or during governance-directed evaluation periods.

---

### Supplement B.7 — Allocation Model Selection Guidance

| Deployment Stage               | Recommended Model              |
|--------------------------------|-------------------------------|
| Pre-live: < 30 days history    | Equal Weight                   |
| Early live: 30–60 days history | Risk Parity or Equal Weight    |
| Established: 60–90 days        | Performance Weighted           |
| Mature: > 90 days, regime data | Regime-Adaptive                |
| Governance-directed testing    | Fixed Budget                   |

---

## SUPPLEMENT C — REBALANCING STRATEGIES

### Supplement C.1 — Rebalancing Philosophy

Rebalancing is the discipline of restoring the portfolio to its target allocation when drift has accumulated. Rebalancing is a maintenance activity, not an alpha-generating activity. The fundamental tension in rebalancing is between the cost of allowing drift to persist (risk divergence from design) and the cost of correcting it (transaction costs, market impact, opportunity cost).

IIOS resolves this tension with the 2x cost test: rebalancing is only executed when the expected benefit exceeds twice the estimated transaction cost.

---

### Supplement C.2 — Calendar Rebalancing

**Approach:** Rebalance the portfolio at fixed calendar intervals regardless of drift magnitude.

**Intervals available:** Weekly (Friday session end); Monthly (last trading day); Quarterly.

**Strengths:** Simple; predictable; avoids reactive trading.
**Weaknesses:** May rebalance when drift is negligible (wasted cost); may be too slow when drift is severe.

**IIOS Use Case:** Not used as a primary mechanism in IIOS. Calendar-based review is used as a governance check, not a trigger for trades.

---

### Supplement C.3 — Threshold Rebalancing (Primary IIOS Method)

**Approach:** Rebalance when actual allocation departs from target by more than a defined threshold.

**Thresholds:**
- Soft band: ±5% for strategies, ±8% for sectors. Alert raised; rebalancing evaluated.
- Hard band: ±10% for strategies, ±15% for sectors. Rebalancing proposal generated immediately.

**2x Cost Test:**
- Estimate rebalancing cost: (trade value) x (estimated round-trip cost rate = 0.05% to 0.15%)
- Estimate drift correction benefit: (drift magnitude) x (expected risk reduction per 1% drift correction)
- Proceed only if: Benefit >= 2 x Cost.

**Strengths:** Cost-controlled; reactive to actual drift; avoids unnecessary trades.
**Weaknesses:** Requires accurate cost estimation; may delay rebalancing if benefits are hard to quantify.

---

### Supplement C.4 — Risk-Driven Rebalancing

**Approach:** Rebalance when Risk Engine signals that portfolio risk metrics are approaching limits, even if allocation drift is within tolerance bands.

**Triggers:**
- Exposure concentration risk: any single sector > 30% with no sign of reverting
- VaR approaching Risk Engine limit (> 80% of VaR limit consumed)
- Strategy correlation spike: average inter-strategy correlation rises above 0.70

**Note:** Risk-driven rebalancing proposals originate from the Risk Engine and enter the rebalancing pipeline through the standard proposal approval process.

**Strengths:** Addresses risks that drift-based rebalancing might miss; forward-looking.
**Weaknesses:** Requires reliable real-time risk metrics.

---

### Supplement C.5 — Regime-Driven Rebalancing

**Approach:** When the market regime changes (e.g., from TRENDING_UP to SIDEWAYS), rebalance to the allocation targets appropriate for the new regime.

**Trigger:** L2 MarketIntelligence reports a regime change with confidence > 0.75.

**Process:** When regime changes, the Allocation Engine computes new targets using the Regime-Adaptive model. The difference between old targets and new targets becomes the rebalancing proposal.

**Strengths:** Proactively adjusts to changed market conditions.
**Weaknesses:** Regime changes can be false positives; excessive rebalancing on oscillating regimes creates cost drag.

**Protection:** Regime-driven rebalancing has a 48-hour cooldown after each execution. If regime changes again within 48 hours, the second change is queued and evaluated after the cooldown.

---

### Supplement C.6 — Cost-Aware Rebalancing

**Approach:** All rebalancing proposals are filtered through an explicit cost model before execution. Cost-awareness is not a separate rebalancing strategy — it is a mandatory filter on all rebalancing proposals.

**Cost Estimation Model:**

Transaction Cost (TC) = Quantity x Price x Round_Trip_Rate
Round_Trip_Rate = Commission_Rate + Estimated_Slippage_Rate + STT_Rate + Exchange_Fees_Rate

For IIOS paper trading estimates:
- Commission: 0.03% one-way (Dhan)
- Slippage: 0.05% estimated (mid-cap stocks), 0.02% (large-cap NIFTY50)
- STT (on sell): 0.1% (equity delivery), 0.025% (intraday)
- Exchange + GST: ~0.005%

Total estimated round-trip: 0.10% to 0.25% depending on stock type.

**Benefit Estimation Model:**

Drift Correction Benefit = Drift_Magnitude x Beta_Drift_to_Sharpe
Beta_Drift_to_Sharpe: estimated at 0.02 Sharpe improvement per 1% drift correction (calibrated from historical simulations).

**Decision Rule:** Execute rebalancing only if estimated Sharpe improvement > 2 x TC_as_pct_of_NAV.

---

## SUPPLEMENT D — PERFORMANCE ATTRIBUTION EXAMPLES

### Supplement D.1 — Brinson-Fachler Attribution Framework Review

Performance attribution decomposes the active return (portfolio return minus benchmark return) into three components:

**Allocation Effect:** Did the Portfolio Engine add value by overweighting/underweighting sectors or strategies?
**Allocation_i = (w_p_i - w_b_i) x (R_b_i - R_b)**
where w_p_i = portfolio weight in category i, w_b_i = benchmark weight in category i, R_b_i = benchmark return for category i, R_b = total benchmark return.

**Selection Effect:** Did the Portfolio Engine add value by picking better securities within each sector or category?
**Selection_i = w_b_i x (R_p_i - R_b_i)**
where R_p_i = portfolio return in category i.

**Interaction Effect:** Did the allocation decision and selection decision compound positively?
**Interaction_i = (w_p_i - w_b_i) x (R_p_i - R_b_i)**

**Total Active Return = sum(Allocation_i) + sum(Selection_i) + sum(Interaction_i)**

---

### Supplement D.2 — Worked Example 1: Single-Strategy Session

**Scenario:** IIOS runs one strategy (Momentum) in the IT sector for a single session.

**Session Inputs:**
- Portfolio: 100% IT sector (INFY, TCS, WIPRO)
- Benchmark: NIFTY IT Index
- Portfolio return in IT sector: +1.8%
- NIFTY IT Index return: +1.5%
- NIFTY50 return (total benchmark): +0.8%
- Portfolio weight in IT: 0.70 (70% of NAV)
- Benchmark weight in IT: 0.25 (25% of NIFTY50)

**Attribution Calculation:**

Allocation Effect (IT) = (0.70 - 0.25) x (1.5% - 0.8%) = 0.45 x 0.7% = +0.315%

Selection Effect (IT) = 0.25 x (1.8% - 1.5%) = 0.25 x 0.3% = +0.075%

Interaction Effect (IT) = (0.70 - 0.25) x (1.8% - 1.5%) = 0.45 x 0.3% = +0.135%

**Total Active Return = +0.315% + 0.075% + +0.135% = +0.525%**

**Interpretation:** IIOS earned an extra 0.525% relative to benchmark. Most of the value came from the allocation decision (being overweight IT on a day IT outperformed), with smaller but positive contributions from both selection (picking stocks that beat the IT index) and interaction.

---

### Supplement D.3 — Worked Example 2: Multi-Strategy Session

**Scenario:** IIOS runs three strategies across three sectors for a session.

**Session Data:**

| Strategy   | Sector  | Wt Portfolio | Wt Benchmark | Return Port | Return Bench |
|------------|---------|--------------|--------------|-------------|--------------|
| Momentum-1 | IT      | 0.35         | 0.15         | +2.1%       | +1.5%        |
| Momentum-2 | Banking | 0.30         | 0.25         | -0.5%       | +0.2%        |
| Breakout   | Auto    | 0.25         | 0.10         | +1.0%       | +0.7%        |
| Cash       | None    | 0.10         | 0.00         | 0.0%        | 0.0%         |
|            | Total   |              |              |             | +0.8% (B)    |

**Attribution Calculation by Strategy/Sector:**

IT — Momentum-1:
- Allocation: (0.35 - 0.15) x (1.5% - 0.8%) = 0.20 x 0.7% = +0.140%
- Selection: 0.15 x (2.1% - 1.5%) = 0.15 x 0.6% = +0.090%
- Interaction: 0.20 x (2.1% - 1.5%) = 0.20 x 0.6% = +0.120%

Banking — Momentum-2:
- Allocation: (0.30 - 0.25) x (0.2% - 0.8%) = 0.05 x (-0.6%) = -0.030%
- Selection: 0.25 x (-0.5% - 0.2%) = 0.25 x (-0.7%) = -0.175%
- Interaction: 0.05 x (-0.5% - 0.2%) = 0.05 x (-0.7%) = -0.035%

Auto — Breakout:
- Allocation: (0.25 - 0.10) x (0.7% - 0.8%) = 0.15 x (-0.1%) = -0.015%
- Selection: 0.10 x (1.0% - 0.7%) = 0.10 x 0.3% = +0.030%
- Interaction: 0.15 x (1.0% - 0.7%) = 0.15 x 0.3% = +0.045%

**Totals:**
- Total Allocation Effect = +0.140% - 0.030% - 0.015% = +0.095%
- Total Selection Effect = +0.090% - 0.175% + 0.030% = -0.055%
- Total Interaction Effect = +0.120% - 0.035% + 0.045% = +0.130%

**Total Active Return = +0.095% - 0.055% + 0.130% = +0.170%**

**Interpretation:** The portfolio marginally outperformed the benchmark by 0.170%. IT outperformance was strong, but Banking was a significant detractor at the selection level. The Breakout strategy in Auto showed positive selection skill. The interaction effect was the largest positive contributor — overweights in good-selection strategies compounded well.

---

### Supplement D.4 — Worked Example 3: Attribution Over Multiple Sessions

**Scenario:** Monthly attribution review. Strategy Momentum-1 has traded 22 sessions.

**Monthly Aggregation:**
- Total sessions: 22
- Sessions where strategy was allocated: 22
- Average portfolio weight vs benchmark: +18%
- Sessions where IT outperformed total benchmark: 14 of 22 (64%)
- Average allocation effect per session: +0.08%
- Average selection effect per session: +0.04%
- Average interaction effect per session: +0.06%
- Total attribution over month:
  - Allocation: +0.08% x 22 = +1.76%
  - Selection: +0.04% x 22 = +0.88%
  - Interaction: +0.06% x 22 = +1.32%
  - Total: +3.96% active return over month

**Governance Use:** The attribution over 22 sessions demonstrates that Momentum-1 consistently adds value through allocation and interaction (being overweight when IT outperforms the market). Selection skill is positive but smaller — the strategy adds more value through timing (allocation) than through stock picking within the sector.

**Learning Engine Feed:** Momentum-1's allocation timing skill is stronger than its within-sector selection skill. This suggests the strategy should be maintained at current strategy-level allocation but individual stock selection rules could be improved.

---

## SUPPLEMENT E — BENCHMARK FRAMEWORK

### Supplement E.1 — Benchmark Purpose and Design Principles

A benchmark is the reference portfolio against which the Portfolio Engine measures its investment skill. Benchmark selection is a governance decision that defines what "winning" means for this portfolio.

**Benchmark Principles:**

1. **Investable:** The benchmark must be a portfolio that the investor could actually hold. Abstract theoretical benchmarks are not useful.
2. **Unambiguous:** Benchmark composition and return calculation must be transparent and reproducible.
3. **Specified in advance:** The benchmark must be designated before the period it measures. Selecting a benchmark after the fact is benchmark shopping and is prohibited.
4. **Appropriate:** The benchmark should reflect the investment universe and style of the portfolio being managed.

---

### Supplement E.2 — Primary IIOS Benchmarks

**BM-01 — NIFTY50 (IIOS Primary Benchmark)**

Index: Nifty 50 (NSE symbol: ^NSEI, Yahoo Finance: ^NSEI)
Composition: 50 largest by free-float market cap listed on NSE
Rebalancing: Semi-annual
Why chosen: The primary large-cap Indian equity benchmark; most strategies in IIOS target large-cap equities

**BM-02 — NIFTYBANK**

Index: Nifty Bank (NSE symbol: ^NSEBANK, Yahoo Finance: ^NSEBANK)
Composition: 12 most liquid banking and financial sector stocks
Why chosen: Banking sector is a primary hunting ground for IIOS Momentum strategies

**BM-03 — NIFTY500**

Index: Nifty 500 (Yahoo Finance: NIFTY_500.NS)
Composition: Top 500 stocks by market cap on NSE
Why chosen: Broader benchmark suitable for strategies that trade mid-cap stocks

**BM-04 — CASH_RATE**

Rate: RBI overnight repo rate (6.5% as of 2025)
Why chosen: Opportunity cost benchmark; capital sitting in cash should earn at least the risk-free rate

---

### Supplement E.3 — Tracking Error

Tracking error measures how closely the portfolio's returns follow the benchmark's returns.

**Formula:**
Tracking Error = Standard Deviation of (R_portfolio_t - R_benchmark_t) over N periods
where the standard deviation is computed as the annualized daily tracking difference.

**Interpretation:**
- Low tracking error: Portfolio moves closely with benchmark — either index-hugging or heavily beta-driven.
- High tracking error: Portfolio takes significant active bets versus benchmark.

**IIOS Target:** For a high-active IIOS portfolio, tracking error of 5%–15% annualized is expected. Very low tracking error (< 2%) suggests the portfolio is not implementing any meaningful active strategy.

---

### Supplement E.4 — Information Ratio

The information ratio measures the consistency of active return delivery relative to the active risk taken.

**Formula:**
Information Ratio = Active Return / Tracking Error
where Active Return = annualized portfolio return - annualized benchmark return.

**Interpretation:**
- IR > 0.5: Good active management; considered skilled
- IR > 1.0: Excellent active management
- IR < 0: Negative active management (underperforming benchmark)

**IIOS Target:** IR > 0.5 over rolling 90-day periods for each strategy benchmark pair.

---

### Supplement E.5 — Benchmark Selection Criteria

When a new portfolio type is added to IIOS, the benchmark selection process is:

1. Define the portfolio's investment universe (which stocks or instruments it trades).
2. Identify the closest index that covers that universe. If no single index covers > 60% of the portfolio's universe, consider a composite benchmark (e.g., 60% NIFTY50 + 40% NIFTYBANK).
3. Verify the benchmark is investable (i.e., the investor could hold it as an alternative).
4. Confirm the benchmark data is reliably available through IIOS data feeds.
5. Document the benchmark selection in the portfolio configuration with the rationale.
6. Governance approval: Operations Lead must approve the benchmark selection before it is used.

---

### Supplement E.6 — Composite Benchmark Construction

For a multi-strategy portfolio with strategies targeting different segments:

**Formula:**
Composite Return = sum(w_b_i x R_benchmark_i for all i)
where w_b_i = weight of sub-benchmark i in the composite, sum(w_b_i) = 1.0.

**Example:**
70% NIFTY50 + 30% NIFTYBANK:
If NIFTY50 returns +0.8% and NIFTYBANK returns +1.2% on a session:
Composite Benchmark Return = 0.70 x 0.8% + 0.30 x 1.2% = 0.56% + 0.36% = 0.92%

**IIOS Use:** IIOS currently uses NIFTY50 as the primary benchmark. A composite benchmark may be introduced when IIOS consistently allocates > 25% to Banking strategies.

---

## SUPPLEMENT F — PORTFOLIO ANTI-PATTERNS

### Supplement F.1 — Anti-Pattern Framework

Portfolio anti-patterns are systematic, recurring failures in portfolio management behavior that consistently harm risk-adjusted returns or violate sound portfolio management principles. Unlike bugs (which are corrected and disappear), anti-patterns are stable dysfunctional behaviors that must be detected and actively addressed.

Each anti-pattern is described with its detection signal, root cause, harm caused, and the IIOS corrective response.

---

### AP-01 — Overtrading

**Definition:** Excessive trading frequency that generates transaction costs greater than the incremental expected return from each trade.

**Detection Signals:**
- Daily transaction count > 20 trades
- Total transaction cost > 0.3% of NAV in a single session
- Realized P&L / total transaction cost ratio < 2.0 (each unit of realized profit costs more than 0.5 units to generate)

**Root Cause:** Strategy signals that are over-sensitive to noise; rebalancing thresholds that are too tight; duplicate signal generation from correlated strategies.

**Harm:** Transaction cost erosion; reduction in effective strategy returns; in the extreme, a profitable strategy becomes unprofitable when real-world costs are applied.

**IIOS Response:**
1. Attribution Engine flags high cost-to-return ratio.
2. Learning Engine receives signal that trade frequency is harming performance.
3. Strategy Lab reviews strategy signal sensitivity.
4. Governance review of transaction cost report triggered.

---

### AP-02 — Position Hoarding

**Definition:** Holding losing positions beyond the strategy's designed stop-loss levels, hoping for recovery.

**Detection Signals:**
- Position held > X sessions beyond its stop-loss trigger (X set by strategy design, default 1 session)
- MAE / position cost > 5% without stop-loss activation
- Strategy consistently showing lower realized losses than simulated (sign that stops are not being honored)

**Root Cause:** Human override of automated stop-loss; system failure to trigger stop-loss; risk guardian not receiving accurate position data.

**Harm:** Losses compound; portfolio capital tied up in losers cannot be deployed to winners; can lead to catastrophic single-position losses.

**IIOS Response:**
1. Position Manager flags positions beyond stop-loss dwell time.
2. Risk Guardian is notified of positions exceeding loss thresholds.
3. Governance alert generated.
4. Human override required to continue holding — documented and reviewed.

---

### AP-03 — Attribution Blindness

**Definition:** Running the portfolio for multiple sessions without performing performance attribution. Decisions are made without knowing why the portfolio is performing as it is.

**Detection Signals:**
- No attribution report for > 5 consecutive sessions
- Attribution Engine not receiving required data (benchmark not loaded, fill data incomplete)
- Governance report produced without attribution section

**Root Cause:** Data pipeline failure; benchmark data unavailable; attribution component degraded.

**Harm:** Cannot identify which strategies are adding vs destroying value; cannot learn from performance; governance is flying blind.

**IIOS Response:**
1. PC-12 Attribution Engine flags missing attribution.
2. PQD-09 (Explainability) score falls.
3. Governance report flags as incomplete.
4. Human review required to certify session outcomes without attribution.

---

### AP-04 — Benchmark Hugging

**Definition:** Managing the portfolio to stay close to the benchmark rather than to deliver genuine active returns. Produces low tracking error but no alpha.

**Detection Signals:**
- Information Ratio consistently < 0.2 for > 30 sessions
- Tracking Error < 2% annualized for > 30 sessions
- Strategy allocations closely tracking benchmark weights without explicit design intent

**Root Cause:** Excessively risk-averse rebalancing; strategies that are inadvertently constructed as near-index trackers; allocation constraints that effectively force index-like exposures.

**Harm:** Pays active management costs (transaction costs, system complexity) for passive performance; does not deliver on IIOS mandate.

**IIOS Response:**
1. Analytics Engine flags low Information Ratio pattern.
2. Governance report highlights benchmark-hugging behavior.
3. ResearchLab (L15) reviews strategy designs for genuine active bets.

---

### AP-05 — Rebalancing Paralysis

**Definition:** Consistently failing to rebalance despite significant allocation drift because the 2x cost test repeatedly fails or because of excessive caution.

**Detection Signals:**
- Allocation drift > hard band for > 3 consecutive sessions without rebalancing
- Rebalancing proposals consistently deferred without execution for > 5 sessions
- Portfolio allocation significantly diverged from mandate (> 15% drift on primary strategies)

**Root Cause:** Cost estimates too conservative; benefit estimation model underestimating drift correction value; excessive override of rebalancing proposals.

**IIOS Response:**
1. Rebalancing Engine generates escalation alert.
2. Governance review of deferred rebalancing decisions.
3. Operations Lead must acknowledge and document reason for continued deferral.

---

### AP-06 — Cash Drag

**Definition:** Holding excessive cash in the portfolio for extended periods, reducing the portfolio's participation in market returns.

**Detection Signals:**
- Cash > 30% of NAV for > 3 consecutive sessions without explicit mandate to hold cash
- Cash holding period > 5 sessions with no new positions opened
- CASH_RATE return contribution exceeding any strategy's contribution (all strategies generating less than the risk-free rate)

**Root Cause:** Strategy signals not generating trades; risk limits preventing new positions; decision engine rejecting all proposals; system failure in opportunity identification.

**IIOS Response:**
1. PC-06 Cash Manager alerts when cash > 30% for > 3 sessions.
2. Allocation Engine flags cash drag.
3. Governance review: is this intentional capital preservation or a system failure?

---

### AP-07 — Concentration Creep

**Definition:** A gradual increase in portfolio concentration over time as winning positions grow and are not trimmed, even though they approach or exceed concentration limits.

**Detection Signals:**
- Single position weight > 20% NAV (soft limit) or > 25% NAV (hard limit)
- HHI position concentration score > 0.30
- Diversification score falling trend: > 3 consecutive sessions of decline without new positions

**Root Cause:** Not trimming winners; position sizing that compounds unchecked; insufficient diversification monitoring.

**IIOS Response:**
1. PC-09 Diversification Engine alerts on concentration increase.
2. PC-14 Constraint Manager enforces hard concentration limit.
3. Rebalancing Engine proposes trim trade for over-concentrated positions.
4. Governance review if concentration persists after trim proposal.

---

### AP-08 — Strategy Proliferation

**Definition:** Adding too many strategies to the portfolio without sufficient capital or data to evaluate them properly, resulting in small allocations to many strategies and no meaningful contribution from any.

**Detection Signals:**
- > 8 active strategies with average allocation < 8% each
- Any strategy allocated < 3% of NAV (too small to make a meaningful contribution)
- Attribution showing > 60% of strategies contributing < 0.1% active return per session

**Root Cause:** Desire to diversify through strategy count rather than genuine strategy quality; ResearchLab promotions without consideration of portfolio capacity.

**IIOS Response:**
1. Governance report flags strategy count and average allocation.
2. ResearchLab reviews strategies below minimum contribution threshold.
3. Portfolio Governance Manager proposes consolidation or retirement of under-minimum strategies.

---

## SUPPLEMENT G — OPERATIONAL RUNBOOK

### Supplement G.1 — Pre-Session Startup Sequence

**Timing:** 08:45 IST — 09:10 IST (before market open at 09:15 IST)

**Step-by-Step Startup:**

1. **08:45 — System Start**
   - main.py initiates; IIOS system health check runs
   - All 17 layers report READY status

2. **08:50 — Data Feed Initialization**
   - L2 MarketIntelligence: Dhan feed connectivity test; yfinance fallback confirmation
   - Benchmark data for current day loaded

3. **08:55 — Portfolio Engine Startup**
   - PC-01 Registry: Load portfolio state from persistent storage
   - PC-04 Position Manager: Load prior session open positions
   - PC-06 Cash Manager: Load prior session cash balance
   - Reconciliation check: Does portfolio state agree with broker account?
   - If reconciliation fails: HALT startup; alert operator; await human resolution

4. **09:00 — Allocation and Risk Initialization**
   - PC-07 Allocation Engine: Load current allocation targets
   - L6 CapitalRisk: Risk budget confirmed from NAV
   - PC-14 Constraint Manager: Load constraint set for today

5. **09:05 — Governance Confirmation**
   - Prior session governance report acknowledgment confirmed
   - No outstanding unresolved overrides from prior session
   - If governance pending: Operator notification; trading permitted with acknowledgment

6. **09:10 — Readiness Certification**
   - PC-20 PEHS computed; must be >= NOMINAL (0.75) for full operations
   - All 21 component readiness checks passed
   - CERTIFIED status confirmed; Telegram notification to operator

---

### Supplement G.2 — Intraday Monitoring Schedule

| Time             | Action                                                    |
|------------------|-----------------------------------------------------------|
| Every 30 seconds | Mark-to-market update; session P&L refresh                |
| Every 60 seconds | Allocation drift check; diversification score update       |
| Every 5 minutes  | PEHS recompute; threshold status review                   |
| Every 30 minutes | Analytics snapshot; governance feed update                |
| On every fill    | PP-01 execution-to-portfolio pipeline; immediate update   |
| On 1% DD         | Operator Telegram alert; session review triggered         |
| On 2% DD         | Risk Guardian escalation; Kill Switch evaluation          |
| On Kill Switch   | Portfolio → SUSPENDED; all operations halted              |

---

### Supplement G.3 — Post-Session Processing Sequence

**Timing:** 15:30 IST — 16:00 IST

**Step-by-Step:**

1. **15:30 — Market Close**
   - All open orders cancelled
   - Final mark-to-market for all positions

2. **15:35 — Performance Computation**
   - PP-06 Performance Pipeline runs
   - Session P&L, returns, Sharpe, Sortino, Max DD computed

3. **15:40 — Attribution and Benchmark**
   - PC-12 Attribution Engine computes Brinson-Fachler for all strategies
   - PC-13 Benchmark Engine provides final session benchmark returns

4. **15:45 — Analytics and Reporting**
   - PC-15 Analytics Engine updates rolling analytics
   - PC-21 Reporting Manager generates Session Close Summary
   - Telegram session summary delivered to operator

5. **15:50 — Governance Report**
   - PC-17 Governance Manager generates daily governance report
   - Operator receives report via Telegram and dashboard

6. **15:55 — Archive**
   - PP-10 Archive Pipeline runs
   - Session portfolio snapshot, performance, attribution archived
   - Hash chain closed; integrity confirmed

7. **16:00 — Shutdown**
   - PC-20 Health Manager: final PEHS recorded
   - L17 ControlTower: final dashboard update
   - System shutdown confirmation

---

### Supplement G.4 — Incident Response Procedures

**IR-01 — Broker Reconciliation Failure at Startup**

Symptom: Portfolio positions do not match broker account.
Immediate action: HALT startup; do not allow new trades.
Investigation:
  1. Query broker API for exact current positions
  2. Compare with Portfolio Engine position records
  3. Identify discrepancy: missing fill? extra position? price error?
  4. If fill is missing: re-ingest fill; update position; re-reconcile
  5. If ghost position: investigate broker system; do not create matching position without fill record
Resolution: Reconciliation passes; human sign-off; resume operations.
Recovery time target: < 30 minutes.

**IR-02 — Hash Chain Integrity Failure**

Symptom: PC-18 Audit Manager reports broken hash chain.
Immediate action: SUSPEND portfolio operations; alert operator.
Investigation:
  1. Identify which audit record breaks the chain
  2. Determine: was the break caused by a data corruption, a system failure, or unauthorized modification?
  3. If data corruption: restore from last known good backup; replay fills since corruption point
  4. If unauthorized modification: CRITICAL security incident; escalate to System Owner
Resolution: Full chain integrity confirmed; human sign-off required before resuming.
Recovery time target: < 2 hours.

**IR-03 — Portfolio PQS Below FAILED Threshold**

Symptom: PQS < 0.35 (FAILED tier).
Immediate action: Suspend Portfolio Engine output to Decision Engine.
Investigation:
  1. Identify which PQD dimensions have failed
  2. For each failed dimension: determine root cause
  3. Apply dimension-specific recovery procedures
  4. After root cause fixed: re-run affected computations
  5. Re-compute PQS; confirm >= ACCEPTABLE (0.55) before resuming
Recovery time target: < 1 hour.

**IR-04 — Cash Balance Below Minimum Reserve**

Symptom: Cash < 10% of NAV.
Immediate action: Block all new BUY orders; alert operator.
Root cause: Likely a series of fills that consumed more cash than expected, or a cash event recording failure.
Investigation:
  1. Verify all recent fills are correctly reflected in cash events
  2. Verify no duplicate cash deductions
  3. If positions are correctly recorded: cash is legitimately low; must close or trim positions to restore
  4. Operator-directed: which position to trim to restore cash reserve?
Recovery time target: < 30 minutes.

**IR-05 — PEHS Below FAILED Threshold**

Symptom: PEHS < 0.30.
Immediate action: Transition Portfolio Engine to RESTRICTED state; all automated rebalancing suspended.
Investigation:
  1. Check which components are reporting degraded health
  2. Apply component-specific diagnostics
  3. If multiple components degraded: likely a data feed failure; verify price feed
Recovery time target: < 15 minutes.

**IR-06 — Attribution Engine Failure**

Symptom: Attribution computations failing; session performance not decomposable.
Immediate action: Log error; continue session (attribution is important but not a trading prerequisite).
Investigation:
  1. Check benchmark data availability
  2. Check fill data completeness
  3. Verify strategy registry has all required strategy configurations
Recovery: Attribution deferred; marked as provisional; retroactive computation at end of week.
Governance impact: Session governance report marked as incomplete; acknowledgment required.

---

## SUPPLEMENT H — GLOSSARY

### H.1 — Core Portfolio Terms

**Active Return:** The difference between a portfolio's return and its benchmark return for a given period. Active Return = Portfolio Return - Benchmark Return.

**Allocation Drift:** The deviation of the portfolio's actual allocations from its target allocations, measured as absolute percentage difference.

**Allocation Effect:** In Brinson-Fachler attribution, the return contribution from overweighting or underweighting asset categories relative to the benchmark.

**Alpha:** The excess return of the portfolio above what would be predicted by its beta (market sensitivity). A consistently positive alpha indicates investment skill.

**Attribution:** The decomposition of portfolio returns into components that explain which decisions contributed to or detracted from performance.

**Average Cost:** The average price per unit of a security held in the portfolio, computed using FIFO or AVCO methodology.

**Benchmark:** A reference portfolio or index against which portfolio performance is measured. Must be investable, unambiguous, and specified in advance.

**Beta:** A measure of the portfolio's sensitivity to benchmark movements. Beta of 1.0 means the portfolio moves in line with the benchmark.

**Buying Power:** The cash available for new purchases, accounting for margin requirements and the minimum cash reserve.

**Calmar Ratio:** Total Return / Maximum Drawdown. Measures the trade-off between returns and the worst historical loss.

**Cash Buffer:** The minimum cash reserve maintained in the portfolio, set at 10% of NAV in IIOS.

**Cash Drag:** The performance cost of holding excess cash that could be deployed in higher-returning instruments.

**Concentration:** The degree to which portfolio assets are concentrated in a few instruments, sectors, or strategies. Measured by Herfindahl-Hirschman Index (HHI).

**Constitution:** The set of inviolable rules governing the Portfolio Engine's operations, organized into HARD and SOFT rules.

**Cost Basis:** The original value used for tax and performance purposes, representing the price paid for a security plus any associated costs.

---

### H.2 — Position and Holding Terms

**Closed Holding:** A holding record for a position that has been fully exited. Contains the complete lifecycle record including MAE, MFE, duration, and realized P&L.

**Direction:** Whether a position is LONG (profit from price increases) or SHORT (profit from price decreases).

**Diversification Score:** A composite score measuring the degree to which portfolio assets are spread across independent instruments, sectors, and strategies.

**Drawdown:** The peak-to-trough decline in portfolio NAV. Max Drawdown is the largest peak-to-trough decline over a defined period.

**Effective Diversification Ratio:** The ratio of the weighted average volatility of individual positions to the portfolio's total volatility. A higher ratio indicates more effective diversification through low correlations.

**Exposure:** The degree to which the portfolio is subject to a particular risk factor, sector, strategy, or instrument. Measured in absolute or net terms.

**FIFO:** First In, First Out. A cost basis method where the earliest acquired units are considered sold first when reducing a position.

**Holding:** A continuous ownership record for a security from the first purchase through final sale. A holding may encompass multiple fills across its lifecycle.

**MAE (Maximum Adverse Excursion):** The worst intraday or session loss experienced by a holding from its entry point. Used to assess stop-loss effectiveness.

**MFE (Maximum Favorable Excursion):** The best gain experienced by a holding from its entry point. Used to assess exit timing effectiveness.

**Mark-to-Market:** The revaluation of open positions at current market prices, determining unrealized P&L.

**NAV (Net Asset Value):** The total value of the portfolio, computed as the sum of all position market values plus cash. The fundamental portfolio measure.

**Open Position:** A position with quantity > 0, representing a current ownership of a security.

**Position:** A current holding of a specific security in the portfolio at a given quantity and average cost.

**Realized P&L:** Profit or loss from positions that have been closed. Confirmed by closing fills.

**TWR (Time-Weighted Return):** A return calculation method that eliminates the effect of cash flows. The primary performance metric in IIOS for measuring investment skill.

**Unrealized P&L:** The notional profit or loss from positions that are still open, based on current market prices.

---

### H.3 — Risk and Quality Terms

**Allocation Model:** The formula or algorithm used to compute target allocations across strategies and sectors.

**Benchmark Hugging:** An anti-pattern where the portfolio is managed too conservatively, producing near-zero active returns despite paying active management costs.

**Capital at Risk:** The maximum loss the portfolio is willing to accept on a given trade or session.

**Constraint:** A rule that limits portfolio behavior. HARD constraints are inviolable; SOFT constraints can be overridden with governance approval.

**Correlation:** The statistical relationship between two return series. High positive correlation means two strategies tend to move together; low or negative correlation provides diversification benefit.

**Diversification Ratio:** See Effective Diversification Ratio.

**Drawdown Limit:** The maximum permissible drawdown before the Kill Switch or human review is triggered.

**Governance:** The structured oversight process that ensures the portfolio operates according to its mandate, within constraints, and with human accountability.

**HHI (Herfindahl-Hirschman Index):** A measure of concentration computed as the sum of squared market share percentages. Higher values indicate more concentration.

**Hit Rate:** The proportion of closed trades with positive realized P&L. A hit rate > 50% means more trades are profitable than unprofitable.

**Information Ratio:** Active Return / Tracking Error. Measures the consistency of active return delivery per unit of active risk.

**Kill Switch:** A circuit-breaker mechanism that halts all trading when extreme risk thresholds are breached.

**Mandate:** The governing document that defines the portfolio's investment objectives, universe, constraints, and benchmark.

**NAV Consistency Invariant:** The requirement that NAV = sum(positions) + cash at all times. Violation indicates a data integrity failure.

**Payoff Ratio:** Average Win / Average Loss. A payoff ratio > 1.0 means winning trades are larger on average than losing trades.

**PEHS (Portfolio Engine Health Score):** A composite score measuring the operational health of the Portfolio Engine.

**PQS (Portfolio Quality Score):** A composite score measuring the quality of the Portfolio Engine's outputs across 12 dimensions.

**Risk Parity:** An allocation model that equalizes risk contribution across strategies rather than equalizing capital allocation.

**Selection Effect:** In Brinson-Fachler attribution, the return from choosing securities that outperform the category benchmark.

**Sharpe Ratio:** (Return - Risk-Free Rate) / Standard Deviation. Measures risk-adjusted return.

**Sortino Ratio:** (Return - Risk-Free Rate) / Downside Deviation. Like Sharpe but only penalizes downside volatility.

**Tracking Error:** Standard deviation of the difference between portfolio returns and benchmark returns.

---

### H.4 — Operational Terms

**Archive:** Long-term storage of historical portfolio records for governance, audit, and analysis purposes.

**Audit Chain:** The linked sequence of audit records, each referencing the hash of the prior record, creating a tamper-detectable chain of portfolio state changes.

**Fill:** An execution confirmation from the broker indicating that an order has been matched in the market at a specific price and quantity.

**Hash Chain:** A linked data structure where each record contains a cryptographic hash of the previous record, providing tamper detection.

**Override:** A human decision to change or reverse an automated portfolio management recommendation.

**Point-in-Time Reconstruction:** The ability to recreate the exact state of the portfolio at any historical point, using archived records.

**Rebalancing:** The process of restoring portfolio allocations to their target levels after drift.

**Regime:** A classification of the market's current state (e.g., TRENDING_UP, SIDEWAYS, VOLATILE) that informs strategy performance expectations.

**Reconciliation:** The process of comparing the Portfolio Engine's records with the broker's records to confirm they agree.

**Session:** A single trading day, from market open (09:15 IST) to market close (15:30 IST).

**SHA-256:** A cryptographic hash function producing a 256-bit hash value, used in IIOS audit chain integrity verification.

---

## SUPPLEMENT H.5 — GOVERNING DESIGN RECORDS

Governing Design Records (GDRs) document the fundamental architectural decisions that shape the Portfolio Engine. Each GDR describes the decision, the alternatives considered, and the rationale for the choice made. GDRs cannot be overridden by operational policy — only a new GDR can supersede an existing one.

---

### GDR-PRT-001 — Portfolio Is the Canonical Source of Truth

**Decision:** The Portfolio Engine is the sole canonical source of truth for all IIOS portfolio state. No other layer, component, or external system holds an authoritative copy of portfolio state.

**Context:** In a complex multi-layer AI system, multiple components need access to portfolio data. The question is whether they should each maintain their own copy or read from a single authoritative source.

**Decision Made:** Single source of truth. The Portfolio Engine produces portfolio state; all other layers read it.

**Alternatives Considered:**
- Distributed state: each layer maintains its own portfolio view. Rejected: consistency failures are inevitable; reconciliation is a permanent burden.
- Replicated read-only copies: Portfolio Engine writes; others read a replica. Acceptable for dashboard; not for decision-making.

**Rationale:** Financial accuracy requires that there is exactly one definition of what the portfolio holds. Two layers disagreeing on position size would produce contradictory decisions. Single source eliminates this class of error entirely.

**Implications:** All queries for portfolio state must go through Portfolio Engine services. No direct database access for portfolio state from other layers.

---

### GDR-PRT-002 — No Position Without Execution Record

**Decision:** A position can only be created, modified, or closed when a corresponding execution fill record is provided by the Execution Engine. No position state change is made from inference, assumption, or proxy.

**Context:** It is tempting to infer position state from order submissions. "We sent an order; assume it filled." This is dangerous in live trading.

**Decision Made:** Only confirmed fills create position changes.

**Alternatives Considered:**
- Order-based position tracking: assume position changes from order submission. Rejected: fills may fail, partial fills may occur, prices may differ.

**Rationale:** The portfolio reflects financial reality, not intentions. A submitted order is an intention. A confirmed fill is a fact. Only facts belong in the portfolio.

---

### GDR-PRT-003 — Portfolio Never Creates Investment Ideas

**Decision:** The Portfolio Engine is a record-keeper and risk-management tool, not an alpha-generation engine. It never originates trade ideas, signals, or recommendations.

**Context:** Portfolio state information is rich — it is tempting for the Portfolio Engine to generate signals like "this position is profitable; add more."

**Decision Made:** Portfolio Engine produces no investment signals. It provides portfolio state to other layers; those layers generate signals.

**Rationale:** Separation of concerns. Mixing investment idea generation with portfolio record-keeping would create a conflict of interest: the same engine would be generating ideas and assessing whether those ideas are being managed well. Architecture discipline requires that these functions be clearly separated.

---

### GDR-PRT-004 — Audit Before Update

**Decision:** Every portfolio state change creates an audit record before the state is changed. The audit record is written first; the state change follows. If the state change fails, the audit record reflects the attempted change.

**Context:** In concurrent systems, a state change could succeed but the audit record fail to write, leaving an unaudited change.

**Decision Made:** Audit record is written as the first action in every state change pipeline stage.

**Rationale:** An unaudited state change is a governance failure. By always writing audit first, we guarantee that every state change either has a complete audit trail or the change is rolled back.

---

### GDR-PRT-005 — Portfolio Records Are Immutable

**Decision:** Once written, portfolio records (holdings, audit records, performance records) are never modified or deleted. Corrections are handled by creating new records that supersede the incorrect records, with explicit reference to the superseded record.

**Context:** A system that modifies historical records could produce a misleading picture of historical performance.

**Decision Made:** Immutable records. Corrections append; never overwrite.

**Rationale:** Historical portfolio records are the evidence base for strategy evaluation, governance, and audit. If records can be modified, they lose their evidential value. Immutability is foundational to trustworthy performance history.

---

### GDR-PRT-006 — Risk Engine Approval Is Mandatory for Position Changes

**Decision:** The Portfolio Engine does not execute any position change (open, add to, or close) without Risk Engine approval. This applies to all position changes, including rebalancing trades.

**Context:** Could the Portfolio Engine be more agile if it could make small position adjustments autonomously?

**Decision Made:** Risk Engine approval is always required.

**Rationale:** The purpose of the Risk Engine is to protect capital. Allowing any layer to bypass Risk Engine approval creates a class of position changes that are ungoverned by risk management. The integrity of the risk framework requires that every position change passes through it.

---

### GDR-PRT-007 — Performance Attribution Must Be Complete

**Decision:** For every session where the portfolio was active, a complete Brinson-Fachler attribution must be computed and archived. Partial attribution or missing attribution is a quality failure that must be flagged and investigated.

**Context:** Attribution is computationally optional — trading continues without it. Could it be deferred or skipped in certain sessions?

**Decision Made:** Attribution is mandatory. Skipped attribution is a quality failure, not an acceptable operational choice.

**Rationale:** Attribution is the primary learning mechanism connecting portfolio outcomes to strategy decisions. Without attribution, the Learning Engine receives incomplete information and strategy improvement is impaired. The short-term convenience of skipping attribution creates long-term learning deficits.

---

### GDR-PRT-008 — Human Override Is Legitimate and Monitored

**Decision:** Human overrides of automated portfolio decisions are an explicitly designed feature, not a failure mode. The Portfolio Engine actively supports overrides, records them fully, and uses patterns of overrides as a learning input.

**Context:** Many automated systems treat human override as an emergency escape hatch or treat it with reluctance. Should IIOS resist or constrain human overrides?

**Decision Made:** Overrides are first-class operations. They are welcomed, fully recorded, and studied.

**Rationale:** AI trading systems operate under significant uncertainty. Human judgment can detect patterns and apply contextual knowledge that the AI system does not possess. Resisting human judgment is both technically arrogant and potentially harmful. However, overrides are monitored: patterns of overrides that consistently harm outcomes are governance signals that the human is fighting the system in a destructive way, and patterns that consistently improve outcomes are signals that the AI system should learn from the human.

---

## APPENDIX — WORKED EXAMPLES

### WE-01 — Complete Fill-to-Portfolio Cycle

**Scenario:** IIOS Momentum strategy generates a BUY signal for TATASTEEL. The Execution Engine submits an order and receives a fill confirmation.

**Fill Record Received (from L11 Execution Engine):**
- Symbol: TATASTEEL
- Direction: BUY
- Quantity: 150 shares
- Fill price: INR 820.50
- Fees: INR 61.54 (commission + STT + exchange)
- Strategy ID: STRAT-MOMENTUM-002
- Fill timestamp: 2025-11-12 10:47:23 IST
- Fill ID: FILL-20251112-00000891

**Step 1 — PP-01 Pipeline Activated:**
PC-18 Audit Manager records pre-fill state:
- Current positions: RELIANCE x 80 shares @ 2,450.00 = INR 196,000
- Current cash: INR 180,000
- Current NAV: INR 376,000

**Step 2 — Constraint Validation:**
PC-14 Constraint Manager checks:
- Would this buy push any position above 20% NAV? INR 123,075 / NAV ≈ 32.7%. ALERT: Exceeds soft limit of 20%.
- Override: Strategy budget for STRAT-MOMENTUM-002 allows 35% NAV. Passes.
- Cash after buy: INR 180,000 - INR 123,075 - INR 61.54 = INR 56,863.46. Cash > 10% of NAV? 56,863 / 430,000 ≈ 13.2%. PASS.

**Step 3 — Atomic Transaction:**
PC-04 Position Manager:
- No existing TATASTEEL position → create new position
- Position ID: POS-TATASTEEL-20251112-00000001
- Direction: LONG; Quantity: 150; Average Cost: 820.50
- Market Value: INR 123,075; Unrealized P&L: 0

PC-05 Holding Manager:
- Create holding record
- Holding ID: HLD-TATASTEEL-20251112-00000001
- Open date: 2025-11-12; MAE: 0; MFE: 0

PC-06 Cash Manager:
- Cash event: FILL BUY
- Event ID: CSH-FILL-20251112-00000001
- Amount: -(INR 123,075 + INR 61.54) = -INR 123,136.54
- Balance after: INR 56,863.46

PC-03 Portfolio Manager:
- NAV = (RELIANCE: 196,000) + (TATASTEEL: 123,075) + (Cash: 56,863.46) = INR 375,938.46
- Transaction committed.

**Step 4 — Post-Fill Updates:**
PC-08 Exposure Engine: TATASTEEL added to METALS sector exposure. Sector total: 32.7% NAV.
PC-09 Diversification Engine: Instrument count: 2. HHI = (0.521^2 + 0.327^2) = 0.38. Diversification score: 0.64. (Below target of 0.70 — alert generated.)
PC-11 Performance Engine: Session P&L = INR 375,938.46 - INR 376,000 (open NAV) = -INR 61.54 (fees only at entry).
PC-18 Audit Manager: Complete audit record with state_after; SHA-256 chain_hash updated.

---

### WE-02 — Rebalancing Triggered by Allocation Drift

**Scenario:** Over 5 sessions, Momentum-1 has grown due to strong performance while Breakout has underperformed. Allocation has drifted significantly.

**Current State:**
| Strategy       | Target Allocation | Actual Allocation | Drift  |
|----------------|-------------------|-------------------|--------|
| Momentum-1     | 35%               | 44%               | +9%    |
| Momentum-2     | 25%               | 22%               | -3%    |
| Breakout       | 25%               | 17%               | -8%    |
| Cash Reserve   | 15%               | 17%               | +2%    |

Momentum-1 drift: +9% (exceeds hard band of +10%; approaching limit).
Breakout drift: -8% (exceeds soft band of -5%; approaching hard band of -10%).

**Step 1 — Rebalancing Need Evaluation:**
PC-10 Rebalancing Engine: Drift assessment. Hard band not yet breached for any strategy, but soft band breached on both Momentum-1 and Breakout. Rebalancing proposal initiated.

**Step 2 — Cost-Benefit Analysis:**
Portfolio NAV: INR 500,000.
Required rebalancing: Trim Momentum-1 by 9% NAV (INR 45,000 of Momentum-1 positions). Add Breakout by 8% NAV (INR 40,000 of Breakout).

Estimated transaction cost:
- Momentum-1 trim: INR 45,000 x 0.15% = INR 67.50
- Breakout add: INR 40,000 x 0.15% = INR 60.00
- Total: INR 127.50 (0.0255% of NAV)

Estimated benefit:
- Drift magnitude: 9% + 8% = 17% total
- Risk reduction from drift correction: 17% x Beta (0.02 Sharpe / 1% drift) = 0.34 Sharpe improvement expected annualized
- Benefit in session terms: 0.34 / 252 trading sessions = 0.00135 Sharpe improvement per session
- As return equivalent: INR 500,000 x 0.00135% x vol_estimate = estimated INR 33.75 risk-adjusted benefit

2x cost test: Benefit (INR 33.75) vs 2x Cost (INR 255). FAIL — benefit does not exceed 2x cost at this point.

**Step 3 — Decision:**
2x cost test failed. Rebalancing deferred. Drift is recorded. Alert generated: "Rebalancing 2x cost test failed; drift will be monitored. Hard band will trigger mandatory rebalancing."

**Outcome:** Rebalancing deferred this session. If drift reaches hard band (any strategy at +10%/-10%), rebalancing will be mandatory regardless of 2x cost test.

---

### WE-03 — Portfolio Quality Score (PQS) Computation

**Scenario:** End-of-week PQS computation for the IIOS portfolio.

**Dimension Scores (weekly assessment):**

| Dimension     | Weight | Score | Contribution |
|---------------|--------|-------|--------------|
| PQD-01 Accuracy     | 0.20  | 1.00  | 0.200        |
| PQD-02 Completeness | 0.15  | 0.95  | 0.143        |
| PQD-03 Consistency  | 0.12  | 1.00  | 0.120        |
| PQD-04 Diversification | 0.10 | 0.72 | 0.072       |
| PQD-05 Alloc Efficiency | 0.10 | 0.85 | 0.085       |
| PQD-06 Perf Measurement | 0.08 | 0.90 | 0.072       |
| PQD-07 Benchmark Accuracy | 0.08 | 0.95 | 0.076      |
| PQD-08 Risk Alignment | 0.07 | 0.88 | 0.062       |
| PQD-09 Explainability | 0.04 | 0.75 | 0.030       |
| PQD-10 Traceability | 0.03 | 1.00 | 0.030        |
| PQD-11 Auditability | 0.02 | 1.00 | 0.020        |
| PQD-12 Op Stability | 0.01 | 0.95 | 0.010        |

**PQS = sum of contributions = 0.920**

**Tier:** EXCELLENT (>= 0.88)

**Interpretation:** Portfolio Engine is operating at full quality. All critical dimensions (Accuracy, Consistency, Auditability) are perfect. Diversification score is below target (0.72 — only 2 active strategies; concentration alert). Explainability moderate (some attribution gaps in the week).

**Actions:**
- Diversification: Add third strategy to increase instrument count and reduce HHI.
- Explainability: Complete attribution for the 2 sessions where attribution was deferred.

---

### WE-04 — Constraint Breach and Resolution

**Scenario:** End of session: Momentum-1 strategy's positions have grown to 43% of NAV due to strong intraday performance. This exceeds the HARD constraint of 40% per strategy.

**Detection:**
PC-14 Constraint Manager: End-of-session validation check.
Strategy Momentum-1: Actual allocation = 43% NAV. HARD limit = 40% NAV.
**HARD CONSTRAINT BREACH DETECTED.**

**Immediate Actions:**
1. PC-14 alerts PC-16 Monitoring Engine: "HARD constraint breach — Momentum-1 at 43%."
2. PC-16 escalates to operator via Telegram: "ALERT: Strategy Momentum-1 at 43% of NAV. Hard limit is 40%. Action required."
3. PC-17 Governance Manager creates breach record: CON-BREACH-20251112-000001.
4. New orders from Momentum-1 are BLOCKED until breach is resolved.

**Resolution Path:**
PC-10 Rebalancing Engine computes required trim:
- Target: Momentum-1 at 40% NAV
- Current: Momentum-1 at 43% NAV
- Required reduction: 3% of NAV = INR 15,000 at current prices

2x cost test for mandatory rebalancing:
- HARD constraint breach overrides 2x cost test. Rebalancing is mandatory.

Rebalancing proposal generated → Risk Engine approval → Decision Engine approval → L11 Execution Engine → fill confirmed → position trimmed → constraint check passes → breach record closed.

**Post-Resolution:**
Constraint breach record AUD-PRT-20251112-00000445 closed with resolution timestamp.
Governance report flags breach and resolution. Acknowledgment required.

---

### WE-05 — End-of-Session Portfolio Report Generation

**Scenario:** Session close 15:30 IST. Portfolio Reporting Manager generates the full Session Close Summary.

**Data Gathering:**
PC-04: Final mark-to-market. All positions valued at 15:30 prices.
PC-06: Final cash balance confirmed.
PC-03: Final NAV = sum(positions) + cash = INR 487,235.

**Performance Computation (PC-11):**
- Session open NAV: INR 482,000
- Session close NAV: INR 487,235
- Session P&L: INR 5,235 (realized INR 2,100 + unrealized INR 3,135)
- Session return: +1.09%
- Benchmark return: NIFTY50 +0.72%
- Active return: +0.37%

**Attribution (PC-12):**
- Momentum-1 (IT sector): Allocation +0.15%, Selection +0.12%, Interaction +0.10% = +0.37%
- Momentum-2 (Banking): Allocation -0.02%, Selection +0.01%, Interaction -0.01% = -0.02%
- Breakout (Auto): Allocation 0.00%, Selection +0.02%, Interaction +0.00% = +0.02%
- Total Active Return: +0.37% (matches performance calculation — attribution complete)

**Risk Metrics:**
- Session Max Drawdown: -0.23% (minor intraday dip at 11:15)
- No Risk Guardian triggers today.
- VaR utilized: 42% of daily VaR limit.

**Report Sections Generated:**
1. Portfolio Snapshot (NAV, positions, cash, allocation)
2. Session P&L Summary (realized, unrealized, total)
3. Performance vs Benchmark (active return, attribution summary)
4. Risk Summary (DD, VaR, Risk Engine status)
5. Strategy Breakdown (per-strategy P&L and attribution)
6. Governance Events (any constraint approaches, overrides, alerts)

**Delivery:**
- Telegram: Short summary (NAV, P&L, active return) → 15:35 IST ✓
- Dashboard (L17): Full session report live → 15:32 IST ✓
- Governance report: Detailed full report → archive + reviewer queue → 15:38 IST ✓
- L13 Learning Engine: Strategy outcomes delivered → 15:36 IST ✓

---

### WE-06 — Human Override and Audit Trail

**Scenario:** At 13:45 IST, the operator decides to close the TATASTEEL position early, ahead of the automated exit signal, due to awareness of an upcoming steel import duty announcement not yet reflected in market data.

**Override Action:**
- Operator submits override via Telegram bot command: /close TATASTEEL STRAT-MOMENTUM-002
- PC-03 Portfolio Manager receives override request.
- PC-18 Audit Manager creates override record before action:
  - Override ID: OVR-20251112-000003
  - Operator: user_id_001
  - Reason: "Steel import duty announcement anticipated 14:00; close before catalyst"
  - Position: TATASTEEL x 150 shares
  - Pre-override state snapshot recorded

**Execution:**
- L10 Decision Engine notified of human override (governance bypass of normal signal flow).
- L11 Execution Engine receives close order.
- Fill confirmed: TATASTEEL x 150 @ 834.00
- PP-01 pipeline processes close fill.
- PC-05 Holding Manager closes holding: realized P&L = (834.00 - 820.50) x 150 - fees = INR 1,963.46.

**Post-Override Audit:**
- PC-18: Complete override audit record: state_before, state_after, override_id, fill_id, operator, reason.
- PC-17 Governance Manager: Override logged in daily governance report.
- Telegram confirmation to operator: "TATASTEEL closed. P&L: +INR 1,963.46."

**Learning Outcome:**
At session end, this override is delivered to L13 Learning Engine:
- Override context: Human override 45 minutes before end of session.
- Market outcome: TATASTEEL fell 2.8% after 14:00 (import duty announced as expected).
- Override value: Human avoided a -INR 3,450 drawdown on the position.
- Learning signal: This type of override (news-driven early exit) consistently adds value. Mark as positive pattern.

---

## DOCUMENT SUMMARY

### Document Metrics

| Metric                     | Value                          |
|----------------------------|-------------------------------|
| Document Code              | IIOS-PRT-ENG-ARCH-001          |
| Document Title             | IIOS Portfolio Engine Architecture |
| Version                    | 1.0                            |
| Parts                      | X (10)                         |
| Supplements                | H (8)                          |
| Appendix                   | 6 Worked Examples              |
| Portfolio Types Defined    | 20 (PT-01 through PT-20)       |
| Components Defined         | 21 (PC-01 through PC-21)       |
| Services Defined           | 15 (PS-01 through PS-15)       |
| Pipelines Defined          | 10 (PP-01 through PP-10)       |
| Lifecycle Stages           | 12 (PLS-01 through PLS-12)     |
| Portfolio Principles       | 8 (PP-001 through PP-008)      |
| Quality Dimensions         | 12 (PQD-01 through PQD-12)     |
| Constitutional Rules       | 110+ (PC-A through PC-O)       |
| Allocation Models          | 5                              |
| Rebalancing Strategies     | 5                              |
| Anti-Patterns Defined      | 8 (AP-01 through AP-08)        |
| Incident Procedures        | 6 (IR-01 through IR-06)        |
| GDRs                       | 8 (GDR-PRT-001 through GDR-PRT-008) |
| IIOS Benchmarks            | 4 (NIFTY50, NIFTYBANK, NIFTY500, CASH_RATE) |
| Readiness Items            | 40+ (Component + Data + Governance + Operational + Integration) |

---

### Parts Summary

| Part  | Title                         | Key Content                                          |
|-------|-------------------------------|------------------------------------------------------|
| I     | Foundations                   | 21-level definitional ladder; 8 portfolio principles |
| II    | Portfolio Taxonomy            | 20 portfolio types with IIOS status                  |
| III   | Portfolio Components          | 21 components PC-01 through PC-21; 4 tiers           |
| IV    | Portfolio Lifecycle           | 12 lifecycle stages; state machine; sequence diagram |
| V     | Portfolio Services            | 15 services PS-01 through PS-15                      |
| VI    | Processing Pipelines          | 10 pipelines PP-01 through PP-10                     |
| VII   | Quality Framework             | 12 PQD dimensions; PQS formula; tier table           |
| VIII  | Portfolio Governance          | Ownership; naming; versioning; override policy       |
| IX    | Portfolio Constitution        | 110+ rules across 15 categories                      |
| X     | Readiness Checklist           | 40+ items; readiness state machine                   |

---

### Supplements Summary

| Supplement | Title                    | Key Content                                           |
|------------|--------------------------|-------------------------------------------------------|
| A          | Taxonomy Reference       | Full type reference; component tiers; service mapping |
| B          | Allocation Models        | 5 models with formulas; selection guidance            |
| C          | Rebalancing Strategies   | 5 strategies; cost model; decision rules              |
| D          | Attribution Examples     | 3 worked Brinson-Fachler examples                     |
| E          | Benchmark Framework      | 4 IIOS benchmarks; tracking error; information ratio  |
| F          | Anti-Patterns            | 8 anti-patterns with detection signals and responses  |
| G          | Operational Runbook      | Startup; intraday; post-session; 6 incident responses |
| H          | Glossary + GDRs          | 70+ terms; 8 GDRs (GDR-PRT-001 through GDR-PRT-008)  |

---

### Component Quick Reference

**Tier 1: Core**

| ID    | Name                     | Primary Responsibility                          |
|-------|--------------------------|-------------------------------------------------|
| PC-01 | Portfolio Registry       | Master identity record for all portfolios       |
| PC-02 | Portfolio Catalog        | Controlled vocabulary for portfolio types       |
| PC-03 | Portfolio Manager        | Central coordinator; single-writer authority    |
| PC-04 | Position Manager         | Open position lifecycle management              |

**Tier 2: Data**

| ID    | Name                     | Primary Responsibility                          |
|-------|--------------------------|-------------------------------------------------|
| PC-05 | Holding Manager          | Complete holding lifecycle; MAE/MFE tracking    |
| PC-06 | Cash Manager             | Cash balance; buying power; cash events         |
| PC-07 | Allocation Engine        | Target allocations; drift measurement           |
| PC-08 | Exposure Engine          | Multi-dimensional exposure vectors              |
| PC-09 | Diversification Engine   | Diversification score; concentration monitoring |

**Tier 3: Engine**

| ID    | Name                     | Primary Responsibility                          |
|-------|--------------------------|-------------------------------------------------|
| PC-10 | Rebalancing Engine       | Drift detection; rebalancing proposals          |
| PC-11 | Performance Engine       | 10 performance metrics; P&L computation         |
| PC-12 | Attribution Engine       | Brinson-Fachler attribution; decision quality   |
| PC-13 | Benchmark Engine         | Benchmark data; tracking error; alpha           |
| PC-14 | Constraint Manager       | HARD/SOFT constraint enforcement                |
| PC-15 | Analytics Engine         | Higher-order portfolio intelligence             |

**Tier 4: Operations**

| ID    | Name                     | Primary Responsibility                          |
|-------|--------------------------|-------------------------------------------------|
| PC-16 | Monitoring Engine        | Real-time monitoring; alert generation          |
| PC-17 | Governance Manager       | Governance reviews; override recording          |
| PC-18 | Audit Manager            | SHA-256 hash chain; audit records               |
| PC-19 | Archive Manager          | Historical storage; point-in-time recovery      |
| PC-20 | Health Manager           | PEHS computation; readiness certification       |
| PC-21 | Reporting Manager        | 6 report types; Telegram; dashboard             |

---

### PQS Quick Reference

| Dimension    | Weight | Symbol | What It Measures                         |
|--------------|--------|--------|------------------------------------------|
| Accuracy     | 0.20   | PQD-01 | Portfolio state = broker reality         |
| Completeness | 0.15   | PQD-02 | All records complete; no gaps            |
| Consistency  | 0.12   | PQD-03 | NAV = positions + cash; attribution sums |
| Diversification | 0.10 | PQD-04 | Portfolio spread vs concentration target |
| Alloc Efficiency | 0.10 | PQD-05 | Actual vs target allocation alignment    |
| Perf Measurement | 0.08 | PQD-06 | Performance metrics accurate and complete|
| Benchmark Accuracy | 0.08 | PQD-07 | Benchmark data correct and timely      |
| Risk Alignment | 0.07 | PQD-08 | Portfolio within Risk Engine limits     |
| Explainability | 0.04 | PQD-09 | All decisions explained with attribution|
| Traceability | 0.03   | PQD-10 | Every state traceable to fills           |
| Auditability | 0.02   | PQD-11 | Hash chain intact; audit complete        |
| Op Stability | 0.01   | PQD-12 | System uptime; processing reliability   |

**PQS = 0.20*A + 0.15*B + 0.12*C + 0.10*D + 0.10*E + 0.08*F + 0.08*G + 0.07*H + 0.04*I + 0.03*J + 0.02*K + 0.01*L**

| Tier       | Range        | Operational Meaning                          |
|------------|--------------|----------------------------------------------|
| EXCELLENT  | 0.88–1.00    | Full operations; optimal quality             |
| GOOD       | 0.72–0.87    | Full operations; investigate low dimensions  |
| ACCEPTABLE | 0.55–0.71    | Restricted operations; flag outputs          |
| MARGINAL   | 0.35–0.54    | Suspend Decision Engine contribution         |
| FAILED     | 0.00–0.34    | Halt; human recovery required                |

---

### PEHS Quick Reference

| Tier     | Range        | Operational Response                       |
|----------|--------------|--------------------------------------------|
| OPTIMAL  | 0.90–1.00    | All 21 components healthy                  |
| NOMINAL  | 0.75–0.89    | Minor degradation; full operations         |
| DEGRADED | 0.55–0.74    | RESTRICTED mode; investigate               |
| CRITICAL | 0.30–0.54    | SUSPENDED; automated operations halted     |
| FAILED   | 0.00–0.29    | Emergency; human intervention required     |

---

### GDR Quick Reference

| GDR Code        | Decision                                       |
|-----------------|------------------------------------------------|
| GDR-PRT-001     | Portfolio is the canonical source of truth     |
| GDR-PRT-002     | No position without execution record           |
| GDR-PRT-003     | Portfolio never creates investment ideas       |
| GDR-PRT-004     | Audit before update                            |
| GDR-PRT-005     | Portfolio records are immutable                |
| GDR-PRT-006     | Risk Engine approval mandatory for all changes |
| GDR-PRT-007     | Performance attribution must be complete       |
| GDR-PRT-008     | Human override is legitimate and monitored     |

---

### Cross-Layer Integration Reference

| IIOS Layer           | Portfolio Engine Role                                            |
|----------------------|------------------------------------------------------------------|
| L6 CapitalRisk       | Receives NAV from PC-03; provides risk budget to PC-07           |
| L7 RiskControl       | Enforces risk limits via PC-14; Kill Switch via PC-17            |
| L9 RiskGuardian      | Kill Switch trigger transitions portfolio to SUSPENDED           |
| L10 Decision Engine  | Receives portfolio snapshot from PC-03; approves rebalancing     |
| L11 Execution Engine | Delivers confirmed fills to PP-01; receives rebalancing orders   |
| L12 TradeMonitoring  | Receives open position data from PC-04 and PC-05                 |
| L13 Learning Engine  | Receives closed holding outcomes and performance from PC-05/PC-11|
| L14 Performance Anal | Receives drawdown data and performance history from PC-11/PC-19  |
| L17 ControlTower     | Receives continuous portfolio state from PC-16; displays dashboard|

---

### Portfolio SLAs

| Operation                                     | Target Latency   |
|-----------------------------------------------|------------------|
| Fill-to-portfolio (PP-01 end-to-end)          | < 500ms          |
| Mark-to-market cycle (PP-02)                  | < 1 second       |
| Allocation drift check                        | < 2 seconds      |
| Session-end performance computation           | < 5 minutes      |
| Session-end archive (PP-10)                   | < 2 minutes      |
| Governance report generation                  | < 30 minutes     |
| Telegram session summary delivery            | < 10 minutes     |
| Broker reconciliation at startup              | < 2 minutes      |
| Full readiness certification at startup       | < 5 minutes      |
| Point-in-time reconstruction (any prior date) | < 30 seconds     |

---

### Architectural Impact Statement

The Portfolio Engine is the financial backbone of IIOS. It is the only system that knows the true state of what IIOS owns. Without it, every other layer — the Decision Engine, the Risk Engine, the Learning Engine — operates without knowledge of what positions exist, what they cost, and what they are worth.

The Portfolio Engine does not generate alpha. It does not decide what to buy or sell. It does not assess risk. It does the one thing that makes all of those activities possible: it keeps an accurate, complete, auditable, and consistent record of the portfolio at all times.

This design reflects a deep architectural principle: separation of record-keeping from decision-making. A system that both makes investment decisions and judges the quality of those decisions cannot be trusted to do either well. By separating the Portfolio Engine from the Decision Engine, IIOS creates the conditions for honest self-assessment — the portfolio records what happened; other layers learn from it.

The constitution's hardest rule — NAV consistency — is also its most important. NAV = positions + cash is not an accounting identity. It is the statement that the Portfolio Engine understands reality. When that identity holds, the system is grounded in fact. When it fails, the system is operating on fiction, and every downstream decision is built on sand.

---

*Document Code: IIOS-PRT-ENG-ARCH-001 | Version: 1.0*
*Status: COMPLETE*
*Classification: IIOS Internal Architecture Reference*
*Scope: Portfolio Engine — all IIOS portfolio state, holdings, performance, attribution, and governance*

---

## SUPPLEMENT I — PORTFOLIO ENGINE INTEGRATION SPECIFICATIONS

### Supplement I.1 — Integration Architecture Overview

The Portfolio Engine is the hub of financial truth within IIOS. Every layer that touches financial reality — whether to read portfolio state, provide data to the portfolio, or consume portfolio outputs — integrates with the Portfolio Engine through defined interface contracts. This supplement documents all integration specifications in full.

Integration contracts are organized into three categories:
- **Inbound:** Data and events received by the Portfolio Engine from other layers
- **Outbound:** Data and outputs produced by the Portfolio Engine for other layers
- **Bidirectional:** Query-response interactions where the Portfolio Engine both receives requests and delivers responses

---

### Supplement I.2 — Inbound Integration: L11 Execution Engine

**Nature of Integration:** Critical path — the primary source of all portfolio state changes.

**Data Received:** Confirmed execution fill records. A fill record is the authoritative notification that a real transaction has occurred in the market.

**Fill Record Structure:**
- fill_id: Unique execution identifier from the broker
- order_id: Reference to the originating order
- strategy_id: Which IIOS strategy originated this order
- portfolio_id: Target portfolio
- symbol: Instrument traded
- exchange: NSE, BSE, MCX
- direction: BUY or SELL
- quantity: Shares/contracts executed
- fill_price: Execution price (may differ from order price)
- fees: Broker commission + STT + exchange charges
- fill_timestamp: Exact broker-confirmed time of execution
- status: COMPLETE, PARTIAL (more fills expected)

**Handling Rules:**
1. PARTIAL fills are processed immediately; subsequent fills are accumulated until the order is COMPLETE.
2. Duplicate fill_ids are rejected silently (idempotency protection).
3. Fill records arriving > 60 seconds after market close are flagged for human review before processing.
4. Fill prices that deviate > 2% from the last known market price require human confirmation.

**SLA:** PP-01 pipeline completes within 500ms of fill receipt during trading hours.

---

### Supplement I.3 — Inbound Integration: L2 MarketIntelligence

**Nature of Integration:** Market data for mark-to-market valuations and regime detection.

**Data Received:**
- Real-time price updates for all held instruments (every 30 seconds)
- Regime classification: TRENDING_UP, TRENDING_DOWN, SIDEWAYS, VOLATILE, UNCERTAIN
- Sector performance summaries (used by Attribution Engine for sector benchmark returns)

**Handling Rules:**
1. Price updates trigger PP-02 Position Update Pipeline immediately.
2. Regime change notifications trigger PP-04 Allocation Pipeline evaluation.
3. Price data staleness > 60 seconds triggers a data quality alert (PQD-01 degradation).
4. If L2 data is unavailable, the Portfolio Engine uses last known prices but marks all valuations as STALE.

---

### Supplement I.4 — Inbound Integration: L6 Capital Risk Engine

**Nature of Integration:** Risk budget allocation that constrains how capital is deployed.

**Data Received:**
- Per-strategy capital budget (max NAV% that L6 authorizes for each strategy)
- Per-instrument position limit (max shares or notional)
- Session risk budget (total capital at risk authorized for today's session)

**Handling Rules:**
1. L6 capital budgets are loaded at session start and stored in PC-07 Allocation Engine.
2. If L6 reduces a budget intraday (e.g., due to elevated market VIX), PC-07 immediately updates targets and triggers rebalancing evaluation.
3. PC-14 Constraint Manager enforces L6 budgets as HARD constraints.

---

### Supplement I.5 — Inbound Integration: L9 Risk Guardian

**Nature of Integration:** Emergency override — the Kill Switch is the highest-priority inbound signal.

**Signal Received:** KILL_SWITCH_ACTIVATED or KILL_SWITCH_CLEARED.

**Handling Rules:**
1. KILL_SWITCH_ACTIVATED: Portfolio Engine immediately transitions to SUSPENDED state. All new orders blocked. PC-03 records transition. PC-18 creates audit record. PC-17 sends operator alert.
2. KILL_SWITCH_CLEARED: Portfolio Engine transitions back to ACTIVE only after explicit human authorization (double confirmation: operator + system owner).
3. Kill Switch events are always recorded in governance reports and require specific acknowledgment.

---

### Supplement I.6 — Outbound Integration: L6 Capital Risk Engine

**Data Provided:** Current NAV, position values by strategy, session P&L, current VaR utilization.
**Frequency:** Every 30 seconds during session; on-demand query response.
**Purpose:** Allows L6 to maintain accurate risk budget calculations based on current portfolio state.

---

### Supplement I.7 — Outbound Integration: L7 Risk Control

**Data Provided:** Full position and exposure snapshot; allocation vs limits utilization; concentration metrics.
**Frequency:** Every 60 seconds; on every significant portfolio state change.
**Purpose:** L7 RiskManagerAI uses current portfolio state to validate that no risk limits are being approached.

---

### Supplement I.8 — Outbound Integration: L10 Decision Engine

**Data Provided:** Portfolio snapshot including:
- Current positions and weights
- Cash available for new positions
- Current strategy allocations vs targets
- Which strategies have remaining budget for new positions
- Any active constraints that would affect new position eligibility

**Frequency:** Every cycle (before the Decision Engine deliberates on new trade proposals).
**Purpose:** Decision Engine needs to know whether new proposals are feasible given current portfolio state.

---

### Supplement I.9 — Outbound Integration: L12 Trade Monitoring

**Data Provided:** All open positions with entry price, current price, stop-loss level, target price, holding duration.
**Frequency:** Every 30 seconds; on every fill.
**Purpose:** TradeMonitor (L12) monitors intraday position health and generates alerts about positions approaching stops or targets.

---

### Supplement I.10 — Outbound Integration: L13 Learning Engine

**Data Provided:** Closed holding records including:
- Entry and exit prices and timestamps
- Realized P&L and return
- MAE and MFE
- Strategy and regime at time of trade
- Attribution impact of this trade
- Whether the trade was human-overridden and the override outcome

**Frequency:** After each position close; session-end bulk delivery.
**Purpose:** L13 Learning Engine uses these outcomes to update strategy performance models and adapt strategy weights.

---

### Supplement I.11 — Outbound Integration: L14 Performance Analytics

**Data Provided:** Daily performance metrics, drawdown history, rolling returns, Sharpe/Sortino/Calmar time series.
**Frequency:** Session end; on-demand for monthly analytics.
**Purpose:** L14 DrawdownAnalyzer and WalkForwardTester use portfolio performance history for strategy validation.

---

### Supplement I.12 — Outbound Integration: L17 ControlTower

**Data Provided:** Real-time portfolio state for the Streamlit dashboard:
- Current NAV (updated every 30 seconds)
- Session P&L and return
- All open positions
- Strategy allocations and drift
- Recent fills
- Active alerts and governance events

**Frequency:** Every 30 seconds (time-series data); event-triggered (fills, alerts).
**Purpose:** Operator visibility and governance monitoring through the ControlTower dashboard.

---

## SUPPLEMENT J — PORTFOLIO ENGINE FAILURE MODES AND RESILIENCE

### Supplement J.1 — Failure Mode Classification

Portfolio Engine failures are classified by severity and by the component affected. The classification determines the automatic response and the level of human escalation required.

| Severity | Definition                                                       | Response                          |
|----------|------------------------------------------------------------------|-----------------------------------|
| P0       | NAV consistency violation; hash chain broken; ghost positions    | Immediate halt; human escalation  |
| P1       | Broker reconciliation fail; constraint breach; K.S. transition  | Halt new orders; immediate alert  |
| P2       | Attribution failure; performance metric error; report delay     | Continue trading; flag and alert  |
| P3       | Analytics failure; monitoring latency degradation               | Continue; investigate next session|

---

### Supplement J.2 — Resilience Design Principles

**RP-01 — Fail-Visible:** When the Portfolio Engine encounters an error, it fails visibly rather than silently. Alerts are generated, flags are set, and the operator is notified. Silent failure is the worst possible outcome in a financial system.

**RP-02 — Fail-Safe:** When in doubt, the Portfolio Engine restricts rather than permits. A trade that would violate a constraint is rejected, not queued. A fill that cannot be processed correctly is held for human review, not silently discarded.

**RP-03 — Atomicity:** Portfolio state changes are atomic. Either the full state change commits (position + holding + cash + NAV all update together) or none of it commits. Partial state changes that leave the portfolio in an inconsistent state are the source of the most dangerous financial bugs.

**RP-04 — Idempotency:** Re-processing the same fill twice must produce the same result as processing it once. Duplicate fill protection is applied at the fill intake stage. This protects against network retry loops that might deliver the same fill confirmation multiple times.

**RP-05 — Backpressure:** If the Portfolio Engine is overloaded (fills arriving faster than PP-01 can process), fills are queued in order. No fill is dropped. Processing continues in order until the queue is empty.

---

### Supplement J.3 — Recovery Precedence

When multiple failures occur simultaneously (e.g., a market disruption causes a broker reconciliation failure and a price feed outage at the same time), recovery proceeds in the following priority order:

1. NAV consistency (P0): Restore before anything else.
2. Broker reconciliation (P1): Confirm what positions exist before trading.
3. Cash integrity (P1): Confirm available capital.
4. Market data (P1): Required for mark-to-market.
5. Performance computation (P2): Important but not required for trading.
6. Attribution (P2): Session can close without it; retroactive computation acceptable.
7. Reporting (P3): All reports can be delayed without operational harm.

---

## SUPPLEMENT K — PORTFOLIO ENGINE CONFIGURATION REFERENCE

### Supplement K.1 — Configuration Parameters

The Portfolio Engine is configurable through the IIOS config.py file. The following parameters govern Portfolio Engine behavior:

**Core Parameters:**
- PORTFOLIO_CASH_RESERVE_PCT: Minimum cash as percentage of NAV. Default: 10%.
- PORTFOLIO_MAX_POSITIONS: Maximum simultaneous open positions. Default: 15.
- PORTFOLIO_MAX_STRATEGY_NAV_PCT: Maximum allocation to any single strategy. Default: 40%.
- PORTFOLIO_MAX_SECTOR_NAV_PCT: Maximum allocation to any single sector. Default: 35%.
- PORTFOLIO_MAX_POSITION_NAV_PCT: Maximum single position weight. Default: 20% soft, 25% hard.

**Rebalancing Parameters:**
- REBALANCING_SOFT_BAND_PCT: Drift threshold for rebalancing alert. Default: 5%.
- REBALANCING_HARD_BAND_PCT: Drift threshold for mandatory rebalancing. Default: 10%.
- REBALANCING_COST_TEST_MULTIPLIER: Benefit must exceed cost x this factor. Default: 2.0.
- REBALANCING_REGIME_COOLDOWN_HOURS: Minimum time between regime-driven rebalancing. Default: 48.

**Performance Parameters:**
- PERFORMANCE_SHARPE_TARGET: Target Sharpe ratio for Information Ratio assessment. Default: 1.0.
- PERFORMANCE_IR_MINIMUM: Minimum Information Ratio to avoid governance review. Default: 0.5.
- PERFORMANCE_MAX_DD_ALERT: Session drawdown triggering operator alert. Default: 1%.
- PERFORMANCE_MAX_DD_CRITICAL: Session drawdown triggering Risk Guardian evaluation. Default: 2%.

**Quality Parameters:**
- PQS_ACCEPTABLE_FLOOR: PQS below this triggers restricted operations. Default: 0.55.
- PQS_FAILED_FLOOR: PQS below this triggers halt. Default: 0.35.
- PEHS_NOMINAL_FLOOR: PEHS below this triggers restricted mode. Default: 0.75.
- PEHS_CRITICAL_FLOOR: PEHS below this triggers suspension. Default: 0.30.

**Data Retention:**
- ARCHIVE_SESSION_DETAIL_YEARS: How long to keep detailed session data. Default: 2 years.
- ARCHIVE_SUMMARY_YEARS: How long to keep summary data. Default: 7 years.
- ARCHIVE_AUDIT_YEARS: How long to keep audit records. Default: 7 years.

---

### Supplement K.2 — Environment-Specific Configuration

| Parameter                      | Paper Trading   | Live Trading    |
|-------------------------------|-----------------|-----------------|
| PORTFOLIO_CASH_RESERVE_PCT    | 15% (higher)    | 10%             |
| PORTFOLIO_MAX_POSITION_NAV_PCT| 15% soft        | 20% soft        |
| REBALANCING_COST_TEST_MULTIPLIER | 1.5 (easier)| 2.0             |
| PERFORMANCE_MAX_DD_CRITICAL   | 3%              | 2%              |
| PQS_ACCEPTABLE_FLOOR          | 0.50 (lower)    | 0.55            |

*Paper trading uses slightly relaxed constraints to allow more operational learning, while live trading enforces tighter limits for capital protection.*

---

### Supplement K.3 — Startup Configuration Validation

At startup, the Portfolio Engine validates all configuration parameters. Configuration is invalid if:

1. PORTFOLIO_CASH_RESERVE_PCT < 5% (dangerously low)
2. PORTFOLIO_MAX_STRATEGY_NAV_PCT + PORTFOLIO_CASH_RESERVE_PCT > 100% (impossible constraint)
3. REBALANCING_SOFT_BAND_PCT >= REBALANCING_HARD_BAND_PCT (soft must be less than hard)
4. REBALANCING_COST_TEST_MULTIPLIER < 1.0 (must always require benefit to exceed cost)
5. PQS_FAILED_FLOOR >= PQS_ACCEPTABLE_FLOOR (failed must be below acceptable)
6. PEHS_CRITICAL_FLOOR >= PEHS_NOMINAL_FLOOR (critical must be below nominal)

If any validation fails, the Portfolio Engine refuses to start and alerts the operator with the specific invalid parameter.

---

## SUPPLEMENT L — PORTFOLIO PERFORMANCE METRICS REFERENCE

### Supplement L.1 — Complete Metrics Catalogue

This supplement provides the precise definition, formula, and interpretation for every performance metric computed by PC-11 Performance Engine. All metrics are reproducible from the same input data; non-deterministic computation is a quality failure.

---

**Metric 1 — Session Return**

*Definition:* The percentage change in NAV from session open to session close.

*Formula:*
Session Return = (NAV_close - NAV_open) / NAV_open x 100%

*Note:* NAV_open is the portfolio value at the start of the session (09:15 IST); NAV_close is the portfolio value at 15:30 IST. Capital flows during the session are excluded from this computation (they are captured in Money-Weighted Return separately).

*IIOS Target:* Positive average session return; 0.5%+ on active trading days.

---

**Metric 2 — Cumulative Return**

*Definition:* The compounded total return from portfolio inception.

*Formula:*
Cumulative Return = (NAV_current - NAV_inception) / NAV_inception x 100%

For capital-adjusted portfolios:
Cumulative TWR = product of (1 + daily_return_i) for all sessions i — expressed as %

*IIOS Target:* Cumulative return exceeds NIFTY50 cumulative return over the same period.

---

**Metric 3 — Sharpe Ratio**

*Definition:* Risk-adjusted return measuring excess return per unit of total volatility.

*Formula:*
Sharpe = (Mean_Daily_Return - Risk_Free_Daily_Return) / StdDev_Daily_Returns x sqrt(252)

Risk_Free_Daily_Return = RBI_Repo_Rate / 252 (currently 6.5% / 252 = 0.0258% per day)

Annualized from daily returns using sqrt(252) scaling factor.

*IIOS Target:* Sharpe > 1.0 on 90-day rolling basis.

*Interpretation:* Sharpe > 1.0: good; Sharpe > 2.0: excellent; Sharpe < 0: underperforming risk-free rate.

---

**Metric 4 — Sortino Ratio**

*Definition:* Risk-adjusted return measuring excess return per unit of downside volatility only.

*Formula:*
Sortino = (Mean_Daily_Return - Risk_Free_Daily_Return) / Downside_StdDev x sqrt(252)

Downside_StdDev = sqrt(mean of (min(return_i - target, 0))^2 for all i)
where target = Risk_Free_Daily_Return (MAR = Minimum Acceptable Return)

*Why Use Sortino:* Sharpe penalizes both upside and downside volatility equally. A strategy with large upside days and small downside days gets penalized by Sharpe despite being desirable. Sortino correctly penalizes only the downside.

*IIOS Target:* Sortino > 1.5 on 90-day rolling basis.

---

**Metric 5 — Calmar Ratio**

*Definition:* Return per unit of maximum drawdown risk.

*Formula:*
Calmar = Annualized_Return / abs(Max_Drawdown_Pct)

Annualized_Return = Cumulative_Return x (252 / sessions_in_period) (simplified linear annualization)
Max_Drawdown_Pct = (Peak_NAV - Trough_NAV) / Peak_NAV x 100%

*IIOS Target:* Calmar > 1.5 on 90-day rolling basis.

*Interpretation:* A Calmar of 1.5 means for each 1% of maximum drawdown risk, the portfolio delivered 1.5% of annualized return.

---

**Metric 6 — Maximum Drawdown**

*Definition:* The largest peak-to-trough decline in NAV over the measurement period.

*Formula:*
MaxDD = max over all periods (Peak_NAV_i - Trough_NAV_j) / Peak_NAV_i x 100%
where j >= i (trough must occur after peak)

*Tracking:* The drawdown is tracked in real-time during the session. The running drawdown (current peak to current NAV) is computed every 30 seconds.

*IIOS Alert Thresholds:* 1% intraday → operator alert; 2% intraday → Risk Guardian review.

*IIOS Target:* Max drawdown < 5% on any rolling 30-session period.

---

**Metric 7 — Hit Rate**

*Definition:* The proportion of closed trades that resulted in positive realized P&L.

*Formula:*
Hit Rate = (Number of profitable closed trades) / (Total closed trades) x 100%

*IIOS Target:* Hit rate >= 50% at strategy level; >= 55% overall.

*Interpretation:* A hit rate below 50% means more trades lose than win. However, a low hit rate combined with a high Payoff Ratio can still be profitable (trend-following strategies typically win on fewer than 50% of trades but make larger wins than losses).

---

**Metric 8 — Payoff Ratio**

*Definition:* The ratio of average winning trade size to average losing trade size.

*Formula:*
Payoff Ratio = Mean_Realized_PnL(winning trades) / abs(Mean_Realized_PnL(losing trades))

*IIOS Target:* Payoff ratio >= 1.5 at strategy level.

*Expectancy Formula:*
Expectancy per trade = (Hit Rate x Avg Win) - ((1 - Hit Rate) x Avg Loss)
A strategy is theoretically profitable if Expectancy > 0.

---

**Metric 9 — Alpha**

*Definition:* The excess return above what is predicted by the portfolio's market beta.

*Formula (Jensen's Alpha):*
Alpha = R_p - (R_f + Beta x (R_b - R_f))
where R_p = portfolio return, R_f = risk-free rate, R_b = benchmark return, Beta = portfolio beta.

Portfolio Beta = Cov(R_p, R_b) / Var(R_b), computed from rolling 60-session history.

*IIOS Target:* Alpha > 0 on 90-day rolling basis.

---

**Metric 10 — Information Ratio**

*Definition:* Consistency of active return delivery per unit of active risk.

*Formula:*
IR = (R_p_annualized - R_b_annualized) / TE
where TE = annualized Tracking Error = StdDev(R_p_i - R_b_i) x sqrt(252)

*IIOS Target:* IR > 0.5 on 90-day rolling basis per strategy-benchmark pair.

---

### Supplement L.2 — Metric Interaction Table

| Metric Pair                      | Relationship                                                |
|----------------------------------|-------------------------------------------------------------|
| Sharpe + Sortino                 | Sortino >= Sharpe always. If equal: returns are symmetric. If Sortino >> Sharpe: positive skew. |
| Hit Rate + Payoff Ratio          | Expectancy = f(both). Low hit rate can be offset by high payoff. |
| Calmar + Max Drawdown            | Calmar rises as drawdown falls. Protecting downside improves Calmar directly. |
| Alpha + Information Ratio        | Alpha measures skill; IR measures consistency of skill.     |
| Session Return + Sharpe          | High session return with high volatility may have lower Sharpe than moderate return with low volatility. |

---

### Supplement L.3 — Metric Computation Windows

| Metric                | Primary Window  | Secondary Windows              |
|-----------------------|-----------------|-------------------------------|
| Session Return        | Daily           | N/A                           |
| Cumulative Return     | Inception       | 7d, 30d, 90d, 1yr             |
| Sharpe Ratio          | 90d rolling     | 30d rolling, inception         |
| Sortino Ratio         | 90d rolling     | 30d rolling, inception         |
| Calmar Ratio          | 90d rolling     | 30d, inception                 |
| Max Drawdown          | Rolling max     | 30d, 90d, inception            |
| Hit Rate              | All-time        | Last 30 trades, last 90 trades |
| Payoff Ratio          | All-time        | Last 30 trades, last 90 trades |
| Alpha                 | 60d rolling     | 90d rolling, inception         |
| Information Ratio     | 90d rolling     | 30d rolling, inception         |

---

## SUPPLEMENT M — PORTFOLIO EVOLUTION ROADMAP

### Supplement M.1 — Current IIOS Portfolio Engine Capabilities

The Portfolio Engine as currently designed supports:
- Single portfolio (equity-focused, long-only, Indian market)
- Up to 15 simultaneous positions
- Up to 8 active strategies
- 4 benchmark suite (NIFTY50, NIFTYBANK, NIFTY500, CASH_RATE)
- Performance-Weighted and Regime-Adaptive allocation models
- Intraday session-based operations (09:15 to 15:30 IST)
- Brinson-Fachler attribution at strategy and sector level

---

### Supplement M.2 — Phase 2: Multi-Portfolio Architecture (Planned)

When IIOS manages capital at greater scale, the Portfolio Engine will evolve to support multiple concurrent portfolios:

**New Capability: Portfolio Family**
A Portfolio Family is a collection of related portfolios managed under a single mandate umbrella.

*Examples:*
- Main Portfolio: Momentum-focused, large-cap equity
- Satellite Portfolio 1: Options income strategies
- Satellite Portfolio 2: Mid-cap growth strategies

**New Component: Portfolio Family Manager (PC-22)**
Oversees multiple portfolios; enforces family-level constraints (e.g., no position that is long in one portfolio and short in another); aggregates family-level reporting.

**New Component: Cross-Portfolio Attribution (PC-23)**
Attribution across the portfolio family, showing which portfolio contributed to the family's total return.

**Multi-Portfolio NAV Formula:**
Family NAV = sum(NAV_i for all portfolios i in family)
Family Return = sum(weight_i x return_i) where weight_i = NAV_i / Family_NAV

---

### Supplement M.3 — Phase 3: Options Portfolio Integration (Planned)

**New Component: Options Position Manager (PC-24)**
Extends PC-04 for options-specific attributes: strike, expiry, option type (CE/PE), Greeks (Delta, Gamma, Theta, Vega), implied volatility.

**New Metric: Portfolio Greeks**
Delta-adjusted exposure, gamma risk, theta decay per session.

**New Attribution Dimension:**
Options attribution: P&L decomposed into intrinsic value change + time decay + volatility change.

---

### Supplement M.4 — Phase 4: Futures Portfolio Integration (Planned)

**New Component: Futures Position Manager (PC-25)**
Manages futures-specific attributes: contract, expiry, lot size, notional value, mark-to-margin, margin utilization.

**New Pipeline: Daily Settlement Pipeline (PP-11)**
Handles daily mark-to-market settlement for futures positions (gains/losses settled daily in futures, unlike equity).

---

### Supplement M.5 — Invariants That Must Not Change During Evolution

No matter how the Portfolio Engine evolves, the following invariants must always be preserved:

1. **NAV consistency:** NAV = positions + cash. Always. Without exception.
2. **Single-writer principle:** Only PC-03 (or its successor) writes portfolio state.
3. **Audit before update:** Every state change audited before it happens.
4. **Immutable records:** Historical records are never modified.
5. **No investment ideas:** Portfolio Engine never generates trade signals.
6. **Risk Engine supremacy:** All position changes require Risk Engine approval.
7. **Human override support:** Override capability is always maintained.
8. **Attribution completeness:** Attribution is always computed; never skipped.

These invariants are the portfolio engine's constitution. They survive version changes, component additions, and mandate expansions. They are non-negotiable.

---

*End of PORTFOLIO_ENGINE_ARCHITECTURE.md*

*Document Code: IIOS-PRT-ENG-ARCH-001 | Final | Version 1.0*

---

## SUPPLEMENT N — PORTFOLIO ENGINE TESTING FRAMEWORK

### Supplement N.1 — Testing Philosophy

The Portfolio Engine manages real capital. Every line of behavior must be verified before it is trusted with money. The testing framework is not an afterthought — it is a first-class architectural concern. A Portfolio Engine that has not been thoroughly tested is not ready for live deployment.

Testing is organized into five levels, each verifying a different aspect of correctness:

1. **Unit Tests:** Individual component logic (e.g., does the FIFO cost basis calculate correctly?)
2. **Integration Tests:** Component-to-component flows (e.g., does a fill correctly update position, holding, and cash atomically?)
3. **Pipeline Tests:** End-to-end pipeline verification (e.g., does PP-01 produce the correct state from a given fill record?)
4. **Scenario Tests:** Realistic trading session simulations (e.g., does the portfolio correctly handle 50 fills with rebalancing events?)
5. **Constitutional Tests:** Verify that all constitutional rules are enforced (e.g., does a BUY that would push cash below 10% NAV get rejected?)

---

### Supplement N.2 — Unit Test Coverage Requirements

Each component must achieve the following test coverage before being deployed:

| Component                   | Required Test Cases                                             |
|-----------------------------|----------------------------------------------------------------|
| PC-04 Position Manager      | Open LONG; reduce LONG; close LONG; FIFO cost calculation; AVCO cost calculation; duplicate fill rejection |
| PC-06 Cash Manager          | BUY deduction; SELL addition; fee deduction; cash reserve enforcement; capital injection |
| PC-07 Allocation Engine     | Equal weight; Risk Parity; Performance Weighted; drift computation; soft/hard band detection |
| PC-10 Rebalancing Engine    | 2x cost test pass; 2x cost test fail; regime-driven trigger; constraint-blocked rebalancing |
| PC-11 Performance Engine    | Daily return; Sharpe; Sortino; Calmar; Max DD; Hit Rate; Payoff Ratio; Alpha; IR |
| PC-12 Attribution Engine    | Allocation effect; selection effect; interaction effect; total = active return verification |
| PC-14 Constraint Manager    | HARD cash minimum; HARD position limit; HARD strategy budget; SOFT warnings |
| PC-18 Audit Manager         | Pre-state capture; post-state capture; hash chain update; chain integrity verification |

---

### Supplement N.3 — Critical Integration Tests

**INT-01 — Atomic Fill Processing**
Test: Submit a BUY fill. Verify that position, holding, cash, NAV, and audit record all update in a single atomic transaction. Kill the process mid-update and verify that restart produces consistent state.

**INT-02 — Cash Reserve Enforcement**
Test: Submit a series of BUY fills that would cumulatively push cash below 10% NAV. Verify that the last fill that would violate the constraint is rejected, not just warned about.

**INT-03 — Kill Switch Response**
Test: Send KILL_SWITCH_ACTIVATED signal. Verify portfolio transitions to SUSPENDED within 1 second. Verify all new order submissions return BLOCKED. Verify audit record created.

**INT-04 — Rebalancing Full Cycle**
Test: Create allocation drift > hard band. Run PP-05 pipeline. Verify proposal generated, 2x cost test evaluated, Decision Engine consulted, fills processed, post-rebalancing drift within soft band.

**INT-05 — Broker Reconciliation Failure Recovery**
Test: Introduce a deliberate mismatch between Portfolio Engine position records and simulated broker records. Verify startup halts, alert fires, human review step required, reconciliation resolves correctly.

**INT-06 — Hash Chain Integrity**
Test: Corrupt a single audit record's chain_hash field. Verify PC-18 detects the break at startup chain verification. Verify CRITICAL alert is raised.

---

### Supplement N.4 — Scenario Tests

**SCEN-01 — Active Day: High Volume**
Setup: 30 fills in one session across 5 strategies. Rebalancing triggered at 11:30 IST. Human override at 14:00 IST.
Verify: All fills processed within SLA; rebalancing correctly evaluated; override correctly recorded; session performance attribution complete; archive complete.

**SCEN-02 — Stress Day: Large Drawdown**
Setup: Portfolio drawdown reaches 2.5% intraday. Risk Guardian Kill Switch triggered.
Verify: Portfolio suspends correctly; no new fills processed; SUSPENDED state in audit; operator notified within 30 seconds.

**SCEN-03 — Recovery Day: Post-Kill Switch Resume**
Setup: Prior session ended in SUSPENDED state. Human operator authorizes resume.
Verify: Portfolio transitions through correct state machine (SUSPENDED → ACTIVE); all readiness checks pass; reconciliation confirms clean state.

**SCEN-04 — Data Feed Outage**
Setup: Market price feed fails for 5 minutes mid-session.
Verify: Positions marked STALE; PQD-01 accuracy score flags degradation; no new BUY orders processed; SELL orders still permitted; feed recovery restores normal operations automatically.

**SCEN-05 — Multi-Session Continuity**
Setup: Run 10 consecutive simulated sessions.
Verify: Each session opens with correct prior-session state; cumulative performance metrics accumulate correctly; attribution history grows correctly; archive integrity confirmed across all sessions.

---

### Supplement N.5 — Constitutional Compliance Tests

For each constitutional rule, a compliance test verifies the rule is enforced. Selected examples:

**PC-A-003 (HARD) — NAV consistency:**
After each fill in a test session, compute NAV two ways: (1) Portfolio Manager's NAV; (2) sum(position values) + cash manually. Assert they agree within INR 1.00 tolerance. Fail test if any discrepancy.

**PC-D-001 (HARD) — Cash >= 0:**
Submit a SELL short (position close) with fees that exceed the fill value. Verify system correctly handles this edge case without allowing cash to go negative.

**PC-D-003 (HARD) — Cash >= 10% NAV:**
Submit a sequence of BUY orders that approach the cash minimum. Verify the order that would breach 10% is rejected, not the next one.

**PC-C-001 (HARD) — No position without fill:**
Attempt to directly create a position record without a fill record (simulating a manual injection). Verify rejection.

**PC-K-001 (HARD) — Audit before update:**
Instrument PC-03 to check that audit record timestamp is always before state change timestamp. Run 1,000 fills and verify for all.

**PC-J-004 (HARD) — No trade ideas from Portfolio Engine:**
Verify that no Portfolio Engine component has any pathway that results in an order submission to L11 Execution Engine except through the PP-05 rebalancing pipeline (which itself requires Decision Engine approval).

---

### Supplement N.6 — Performance Benchmarks

The following performance benchmarks define acceptable computational overhead for Portfolio Engine operations:

| Operation                              | P50 Latency  | P95 Latency  | P99 Latency  |
|----------------------------------------|--------------|--------------|--------------|
| PP-01 Fill processing (end-to-end)     | 80ms         | 250ms        | 450ms        |
| PP-02 Mark-to-market (15 positions)    | 15ms         | 40ms         | 80ms         |
| Allocation drift computation           | 5ms          | 20ms         | 50ms         |
| Diversification score update           | 3ms          | 10ms         | 30ms         |
| Session P&L computation                | 2ms          | 8ms          | 20ms         |
| PP-06 Session performance pipeline     | 45s          | 90s          | 180s         |
| PP-10 Archive pipeline                 | 30s          | 60s          | 120s         |
| PQS computation (12 dimensions)        | 200ms        | 500ms        | 1s           |
| PEHS computation (21 components)       | 100ms        | 300ms        | 800ms        |

P95 exceedances generate performance alerts. P99 exceedances generate SLA breach alerts.

---

*End of SUPPLEMENT N*

*PORTFOLIO_ENGINE_ARCHITECTURE.md — Document Code: IIOS-PRT-ENG-ARCH-001 — All supplements complete.*
