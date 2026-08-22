# ENTITY ONTOLOGY
## AI Trading Brain — Complete Entity Universe

**Version:** 1.0
**Status:** Authoritative
**Date:** 2026-07-01
**Parent Documents:** MASTER_KNOWLEDGE_ARCHITECTURE.md | INFORMATION_ONTOLOGY.md

---

> *This document answers the question: "What things exist?"*
> *Every module, every model, every intelligence layer, and every decision*
> *must operate on entities defined in this ontology.*

---

## PART I — THE NATURE OF AN ENTITY

### What Is an Entity?

An entity is a distinguishable, independently existing thing within the investment universe that:

1. Has **identity** — it can be uniquely named and referenced
2. Has **existence** independent of any system that observes it
3. Has **state** — it can be in different conditions at different times
4. Has a **lifecycle** — it comes into existence, evolves, and eventually ceases to exist
5. Can be **owned** or governed by other entities
6. Can **hold information** about itself
7. Can **enter relationships** with other entities

**The fundamental test:** Can you point to this thing and say "this specific instance exists, right now, separately from any other thing"? If yes, it is an entity.

### Entity vs Other Concepts

| Concept | What it is | How it differs from an Entity |
|---|---|---|
| **Information** | A structured signal describing an entity's state | Information lives inside entities. A company's revenue is not an entity — it is information owned by the Company entity. Destroy all revenue records — the company still exists. |
| **Knowledge** | A validated, durable pattern derived from observing entities | Knowledge describes patterns that entities exhibit. "Reliance leads sector recovery by 2 sessions" is knowledge about entities, not an entity itself. |
| **Observation** | A timestamped record of an entity's state at a moment | Observations are created by watching entities. The entity exists before and after observation. Observations are perishable records; entities are durable subjects. |
| **Evidence** | A contextualized observation relevant to a hypothesis | Evidence requires an observer, a hypothesis, and a subject (entity). It is derived from entities, not itself an entity. |
| **Relationship** | A typed connection between two or more entities | Relationships do not exist without the entities they connect. They are attributes of the space between entities, not entities themselves (unless promoted to first-class entities when sufficiently complex). |
| **Decision** | The output of a reasoning process applied to entities | "Buy Reliance" is a decision. Reliance is the entity. Decisions reference entities; they are not entities themselves — though a Decision Record is treated as an entity in the knowledge layer. |
| **Learning** | A process applied to observations of entities | Learning is an operation, not a thing. Its output is updated knowledge about entities. |
| **Prediction** | A probabilistic statement about an entity's future state | "Reliance at ₹1400 in 3 months with 65% probability" is a prediction. Reliance is the entity; the prediction is a probabilistic knowledge claim about that entity's possible future state. |
| **Model** | A mathematical construct representing relationships between entities | A model is a tool the system uses. It is not an entity in the investment universe (though it is an entity in the system's internal knowledge layer). |
| **Strategy** | A decision-making framework for evaluating entities and deciding when to act | A strategy is a ruleset applied to entities. It is a computational pattern, not an investment universe entity. In this architecture, strategies are ONE possible evidence source among many — not the architectural core. |

---

## PART II — ENTITY CATALOG

The investment universe contains entities across 12 major groups.

### Group A — Market Infrastructure Entities
The structural entities that make markets possible.
`Market` · `Exchange` · `Trading Session` · `Market Segment` · `Index` · `Benchmark` · `Trading Calendar` · `Settlement Cycle` · `Circuit Breaker` · `Clearing Corporation` · `Depository`

### Group B — Financial Instrument Entities
The objects of investment — things that can be bought, sold, and held.
`Equity/Stock` · `ETF` · `Mutual Fund Unit` · `Government Bond` · `Corporate Bond` · `Commercial Paper` · `Treasury Bill` · `Futures Contract` · `Options Contract` · `Option Chain` · `Commodity Instrument` · `Currency Pair` · `Warrant` · `Convertible Bond` · `Depositary Receipt` · `Right (Entitlement)` · `Structured Product`

### Group C — Economic & Macro Entities
The aggregate constructs providing macroeconomic context.
`Economy` · `Macro Variable` · `GDP` · `Inflation Rate` · `Unemployment Rate` · `Interest Rate` · `Yield Curve` · `Trade Balance` · `Fiscal Deficit` · `Current Account` · `PMI`

### Group D — Organizational Entities
Human institutions and organizations that participate in or govern markets.
`Listed Company` · `Unlisted Company` · `Promoter Group` · `Subsidiary` · `Exchange (org)` · `Regulator` · `Central Bank` · `Government` · `Ministry` · `Fund House` · `Mutual Fund` · `Hedge Fund` · `Insurance Company` · `Pension Fund` · `FII` · `DII` · `Retail Investor` · `Broker` · `Market Maker` · `Investment Bank` · `Rating Agency` · `Research Firm` · `News Agency` · `Index Provider` · `Clearing Member`

### Group E — Event Entities
Occurrences that change the state of other entities.
`Corporate Action (parent)` · `Dividend` · `Stock Split` · `Bonus Issue` · `Rights Issue` · `Buyback` · `Merger` · `Acquisition` · `Demerger` · `Spin-off` · `IPO` · `Open Offer` · `Delisting` · `Earnings Event` · `Monetary Policy Event` · `Budget Event` · `Election` · `Regulatory Event` · `Geopolitical Event` · `War` · `Natural Disaster` · `News Event` · `Credit Rating Change` · `Index Rebalancing Event` · `Rumour`

### Group F — Financial Statement Entities
Formal financial disclosures produced by companies.
`Income Statement` · `Balance Sheet` · `Cash Flow Statement` · `Notes to Accounts` · `Segment Report` · `Quarterly Result` · `Annual Report` · `Auditor Report` · `Management Discussion & Analysis`

### Group G — Participant Activity Entities
Entities created by market participants in the course of their activity.
`Portfolio` · `Position` · `Trade` · `Order` · `Execution` · `Transaction` · `Holding` · `Block Deal` · `Bulk Deal` · `Fund Flow Record`

### Group H — Market Intelligence Entities
Derived constructs produced by the intelligence system.
`Universe` · `Watchlist` · `Screen` · `Scanner` · `Signal` · `Indicator` · `Pattern` · `Feature` · `Factor` · `Score` · `Ranking` · `Alert` · `Notification` · `Market Regime`

### Group I — Knowledge & Reasoning Entities
The system's internal cognitive constructs.
`Hypothesis` · `Observation Record` · `Evidence Item` · `Reasoning Chain` · `Conviction` · `Knowledge Item` · `Model` · `Strategy` · `Backtest` · `Simulation` · `Learning Record` · `Prediction` · `Outcome Record` · `Performance Record`

### Group J — Decision Entities
Entities directly governing action.
`Decision` · `Recommendation` · `Constraint` · `Objective` · `Risk Limit` · `Stop Loss` · `Target Level` · `Position Sizing Rule`

### Group K — Risk Entities
Entities that quantify and govern risk.
`Risk (general)` · `Market Risk` · `Credit Risk` · `Liquidity Risk` · `Operational Risk` · `Drawdown` · `Stress Test` · `VaR Estimate`

### Group L — Reference / Structural Entities
Stable reference entities that other entities depend on.
`Sector Classification` · `Country` · `Currency Reference` · `Date` · `Fiscal Year` · `Trading Day` · `Expiry Date` · `Regulatory Filing` · `Audit Trail` · `Journal Entry` · `Configuration`

---
## PART III — COMPLETE ENTITY DEFINITIONS

*For every entity: all 20 required attributes. Structured tables for efficiency; prose for critical entities.*

---

### GROUP A — MARKET INFRASTRUCTURE ENTITIES

#### A.1 — MARKET

| Attribute | Value |
|---|---|
| **Class** | Market Infrastructure — Structural |
| **Parent** | None (root entity) |
| **Children** | Exchange, Index, Trading Session, Sector, Market Segment |
| **Importance** | Critical |
| **Change Frequency** | Static to Slow Changing |

**Definition:** The organized mechanism through which buyers and sellers of financial instruments discover prices and execute transactions.
**Purpose:** Price discovery, liquidity provision, and transfer of ownership.
**Why it exists:** Markets aggregate the distributed knowledge of all participants into a single observable price signal that no central authority could produce alone.
**Lifecycle:** Established → Operational → Regulated → Evolved → Potentially Closed
**Key Attributes:** Name, Geographic Jurisdiction, Regulatory Regime, Asset Classes, Operating Hours, Settlement Framework, Currency, Surveillance Mechanism, Participant Eligibility
**State Changes:** Normal → Stressed; Regulated → Deregulated; Frontier → Emerging → Developed
**Ownership:** Regulated by Government/SEBI; operated by Exchange
**Dependencies:** Regulatory Framework, Government, Legal System, Banking System
**Information Owned:** Market-wide breadth, circuit break history, aggregate volumes
**Knowledge Produced:** Market regime, liquidity regime, sentiment aggregate
**Knowledge Consumed:** Macro economic state, global market context
**Decisions Influenced:** Capital allocation at macro level
**Risks:** Regulatory, systemic failure, liquidity crisis, political interference
**Examples:** NSE Cash Market, BSE, MCX, NCDEX, NSE F&O Segment
**Relationships:** Contains Exchanges; correlates with Global Markets; governed by Regulator

---

#### A.2 — EXCHANGE

| Attribute | Value |
|---|---|
| **Class** | Market Infrastructure — Organizational |
| **Parent** | Market |
| **Children** | Trading Session, Market Segment, Index, Listed Instruments |
| **Importance** | Critical |
| **Change Frequency** | Static |

**Definition:** The formal institutional platform where standardized instruments are listed and traded.
**Purpose:** Standardized, regulated, supervised venue for price discovery and execution.
**Why it exists:** Centralizes counterparty risk management, standardizes contracts, ensures price transparency, provides investor protection.
**Lifecycle:** Founded → Regulated → Demutualised → Listed (itself) → Merged or Continuing
**Key Attributes:** Exchange Code, Trading Hours, Segments, Listed Company Count, Settlement Partner, Technology Platform, Regulatory License
**State Changes:** Pre-Open → Open → Post-Close → Holiday (daily); Normal → Circuit Halt → Resumed
**Ownership:** Demutualised public companies under SEBI oversight
**Dependencies:** Regulator (SEBI), Clearing Corporation (NSCCL/ICCL), Depositories (NSDL/CDSL)
**Information Owned:** Order books, trade confirmations, circuit data, member information
**Knowledge Produced:** Price history, liquidity statistics, market integrity records
**Decisions Influenced:** Which instruments are accessible, which times are tradeable
**Risks:** Technology failure, regulatory sanction, competition from alternative venues
**Examples:** NSE, BSE, MCX, NCDEX
**Relationships:** Hosts Trading Sessions; lists Instruments; supervised by Regulator; settles through Clearing Corporation

---

#### A.3 — TRADING SESSION

| Attribute | Value |
|---|---|
| **Class** | Market Infrastructure — Temporal |
| **Parent** | Exchange |
| **Children** | Pre-Open, Continuous Session, Closing Auction |
| **Importance** | High |
| **Change Frequency** | Daily (new session each day) |

**Definition:** A defined time window during which trading is permitted on an exchange for a specific segment.
**Lifecycle:** Scheduled → Pre-Open → Open → Continuous → Closing Auction → Closed → Settled
**Key Attributes:** Session Date, Type, Start/End Time, Market Status, Circuit Halt Count, Volume, Breadth, Holiday Flag
**State Changes:** Pre-Open → Open → Running → Circuit Halt → Resumed → Closed
**Ownership:** Operated by Exchange
**Information Owned:** All trade records, volume, prices, breadth statistics for session
**Examples:** NSE Cash 9:15-15:30 IST, MCX Evening Session, NSE Pre-Open 9:00-9:15

---

#### A.4 — INDEX

| Attribute | Value |
|---|---|
| **Class** | Market Infrastructure — Derived/Structural |
| **Parent** | Exchange, Index Provider |
| **Children** | Constituents (Stocks), Index Derivatives |
| **Importance** | Critical |
| **Change Frequency** | Daily (value), Quarterly (composition) |

**Definition:** A calculated aggregate performance measure of a defined basket of instruments.
**Purpose:** Performance benchmark, passive investment vehicle enabler, derivatives underlying.
**Why it exists:** Investors need a standardized reference against which to measure relative performance.
**Lifecycle:** Created → Calculated Daily → Periodically Rebalanced → Potentially Discontinued
**Key Attributes:** Name, Code, Base Value, Base Date, Methodology (cap-weighted/equal/price), Constituent Count, Weights, Currency, Free-Float Adjustment, Rebalancing Frequency, Provider
**State Changes:** Normal → Circuit Halted; Composition change on rebalancing; base correction
**Ownership:** Index Provider (NSE Indices Ltd, MSCI, S&P)
**Information Owned:** Index level history, constituent weights, rebalancing history
**Knowledge Produced:** Market regime, sector benchmarks, relative strength baselines
**Decisions Influenced:** Portfolio benchmarking, passive replication, derivative pricing
**Risks:** Concentration (NIFTY 50 top-10 = 60%+ weight), methodology changes
**Examples:** NIFTY 50, SENSEX, NIFTY Bank, NIFTY IT, NIFTY Midcap 150, India VIX
**Relationships:** Composed of Stocks; tracks Sector/Market; underlies Derivatives

---

#### A.5 — CLEARING CORPORATION

**Class:** Market Infrastructure — Institutional | **Parent:** Exchange | **Importance:** Critical
**Definition:** Acts as central counterparty to all trades, guaranteeing settlement and managing default risk.
**Lifecycle:** Established → Operational (every trading day) → Continuous
**Key Attributes:** Name, Exchange Affiliation, Capital Adequacy, Default Fund, Margining Framework
**Examples:** NSCCL (NSE Clearing), ICCL (India International Clearing)

---

#### A.6 — DEPOSITORY

**Class:** Market Infrastructure — Institutional | **Parent:** Exchange/Regulatory | **Importance:** Critical
**Definition:** Electronically holds securities on behalf of investors, maintaining legally authoritative ownership records.
**Examples:** NSDL, CDSL

---


#### A.7 — MARKET SEGMENT

**Class:** Market Infrastructure — Structural | **Parent:** Exchange | **Importance:** High | **Change Frequency:** Static
**Definition:** A distinct division within an exchange separating trading by asset class, participant type, or regulatory framework.
**Key Attributes:** Segment Name, Exchange, Asset Class, Participant Eligibility, Margin Framework, Settlement Rules, Regulatory Regime, Segment Code
**Lifecycle:** Established → Operational → Possible Restructure or Merger
**State Changes:** Normal → Circuit Halt → Resumed; Trading → Post-Close
**Ownership:** Operated by Exchange; regulated by SEBI
**Examples:** NSE Capital Market (CM), NSE F&O Segment, NSE Currency Derivatives, MCX Commodity, BSE SME Platform, NSE Debt Market

---

#### A.8 — BENCHMARK

**Class:** Market Infrastructure — Derived Reference | **Parent:** Index, Exchange | **Importance:** Critical | **Change Frequency:** Daily
**Definition:** A reference index or rate against which portfolio performance, instrument pricing, or risk is formally measured.
**Key Attributes:** Benchmark Name, Type (equity/rate/currency/commodity), Calculation Method, Publisher, Base Date, Base Value, Publication Frequency
**Lifecycle:** Designated → Active Reference → Possible Replacement or Discontinuation
**State Changes:** Normal → Revised Methodology; Active → Discontinued; Primary → Replaced by new benchmark
**Ownership:** Owned and published by Index Provider; licensed for commercial use
**Examples:** NIFTY 50 (equity benchmark), MIBOR (money market rate), MIFOR (swap rate), 10Y G-Sec yield (bond benchmark), SENSEX

---

#### A.9 — TRADING CALENDAR

**Class:** Market Infrastructure — Temporal Reference | **Parent:** Exchange, Regulator | **Importance:** High | **Change Frequency:** Annual (new calendar), Event (ad-hoc holidays)
**Definition:** The official annual schedule defining every trading day, market holiday, and special session for a given exchange.
**Key Attributes:** Exchange, Year, Total Trading Days (typically 245-250), Holiday List, Settlement Calendar, Expiry Schedule, Special Session Dates
**Lifecycle:** Published annually (typically Sep/Oct for next year) → Used throughout year → Archived
**Ownership:** Published by Exchange under SEBI guidance
**Examples:** NSE Trading Calendar 2026, MCX Holiday Schedule, BSE Annual Calendar

---

#### A.10 — SETTLEMENT CYCLE

**Class:** Market Infrastructure — Process Standard | **Parent:** Exchange, Clearing Corporation | **Importance:** High | **Change Frequency:** Static (regulatory changes rarely)
**Definition:** The standardized timeline defining when securities and funds change hands between buyer and seller after trade execution.
**Key Attributes:** Cycle Type (T+0/T+1/T+2), Asset Class, Settlement Method (DVP/Gross/Net), Obligation Netting Policy, Fail Penalty
**Lifecycle:** Regulatory mandated → Operational → Possible shortening as markets mature
**State Changes:** T+2 → T+1 (India equity moved Jan 2023) → Possible T+0 future
**Examples:** NSE Equity T+1 (since Jan 2023), F&O Daily MTM Settlement, Options Exercise Settlement at Expiry

---

#### A.11 — CIRCUIT BREAKER

**Class:** Market Infrastructure — Safety Mechanism | **Parent:** Exchange, SEBI | **Importance:** High | **Change Frequency:** Event (triggers on price movement)
**Definition:** A regulatory mechanism automatically halting trading when market prices breach predefined thresholds, preventing panic cascades.
**Key Attributes:** Trigger Level (%), Scope (market-wide/index/stock), Halt Duration, Direction (upper/lower/both), Trigger History, Reset Conditions
**State Changes:** Normal → Triggered (halt) → Resumed; Upper Circuit (no sell permitted); Lower Circuit (no buy permitted)
**Ownership:** Mandated by SEBI; enforced by Exchange
**Examples:** NIFTY/SENSEX 10%/15%/20% index-level halts; Individual stock 5%/10%/20% daily price bands

---
### GROUP B — FINANCIAL INSTRUMENT ENTITIES

#### B.1 — EQUITY (STOCK)

| Attribute | Value |
|---|---|
| **Class** | Financial — Equity Instrument |
| **Parent** | Company, Exchange Listing |
| **Children** | Options (on stock), Futures (on stock) |
| **Importance** | Critical |
| **Change Frequency** | Tick Level (price), Daily (volume), Event (corporate actions) |

**Definition:** A unit of ownership in a company conferring residual economic claim on assets and earnings, and typically voting rights.
**Purpose:** Represent and transfer company ownership; enable price discovery of company value.
**Why it exists:** Companies need capital. Investors need return-bearing instruments. Equity serves both simultaneously.
**Lifecycle:** IPO/Listing → Active Trading → Possible Suspension → Delisting/Acquisition/Merger
**Key Attributes:** ISIN, Symbol, Company, Face Value, Market Cap, Free Float, Promoter %, FII %, DII %, Industry Classification, Index Membership, Circuit Limits, 52W High/Low, Beta, ADTV, Dividend History, Listing Date, Book Value/Share, EPS (TTM)
**State Changes:** Active → Suspended; Normal → F&O Ban; Pre-Dividend → Ex-Dividend; Pre-Bonus → Post-Bonus
**Ownership:** Shareholders; issued by Company; listed on Exchange
**Dependencies:** Company (fundamental anchor), Exchange (listing), Market (price environment)
**Information Owned:** Price history, volume history, corporate action history, ownership history
**Knowledge Produced:** Company value model, momentum patterns, behavioral history, relative strength
**Knowledge Consumed:** Company fundamentals, macro regime, sector state, options signals
**Decisions Influenced:** Buy/Sell/Hold, position sizing, stop-loss, target price
**Risks:** Idiosyncratic, sector, systematic (beta), liquidity, event
**Examples:** RELIANCE, INFY, TATAMOTORS, HDFCBANK, ITC, DRREDDY
**Relationships:** Issued by Company; traded in Sessions; constituent of Indices; underlying of Derivatives; owned in Portfolios

---

#### B.2 — FUTURES CONTRACT

| Attribute | Value |
|---|---|
| **Class** | Financial — Derivative |
| **Parent** | Exchange, Underlying Instrument |
| **Importance** | Critical |
| **Change Frequency** | Tick Level (price), Daily (OI, basis) |

**Definition:** A standardized agreement to buy/sell an underlying at a defined price on a defined expiry date.
**Lifecycle:** Contract Created (Exchange) → Trading → Rollover → Expiry → Settlement → Closed
**Key Attributes:** Underlying, Contract Size, Expiry, Settlement Method, Current Price, OI, Volume, Basis, Cost of Carry, Contract Month
**State Changes:** Far Month → Mid Month → Near Month → Near Expiry → Expired; Contango → Backwardation
**Ownership:** Positions held by buyers/sellers; cleared by Clearing Corporation
**Examples:** NIFTY Sep Futures, BANKNIFTY Current Month, CRUDE OIL MCX Near Month

---

#### B.3 — OPTIONS CONTRACT

| Attribute | Value |
|---|---|
| **Class** | Financial — Derivative |
| **Parent** | Exchange, Underlying, Option Chain |
| **Importance** | Critical |
| **Change Frequency** | Tick Level (premium), Daily (OI, Greeks) |

**Definition:** A contract conferring the right (not obligation) to buy (call) or sell (put) an underlying at a defined strike on/before expiry.
**Lifecycle:** Listed → Trading → Greeks evolving daily → Expiry (exercised or expire worthless)
**Key Attributes:** Underlying, Type (Call/Put), Strike, Expiry, Premium, OI, Volume, IV, Delta, Gamma, Theta, Vega, Moneyness (ITM/ATM/OTM), Settlement Method
**State Changes:** Deep OTM → Near ATM → Deep ITM; Normal IV → High IV (event); Near Expiry → Expired
**Ownership:** Written by sellers; held by buyers; cleared by Clearing Corporation
**Examples:** NIFTY 23000 CE July, RELIANCE 1400 PE August

---

#### B.4 — OPTION CHAIN

**Class:** Financial — Derivative Market Structure | **Parent:** Underlying, Exchange | **Importance:** Critical
**Definition:** The complete set of all listed options for a given underlying across all strikes and expiry dates.
**Key Attributes:** Underlying, Max Pain Level, PCR by expiry, OI distribution, IV Surface, Highest OI strikes
**Purpose:** Provides the complete market-derived view of expected price range and directional bias.

---

#### B.5 — ETF (Exchange Traded Fund)

**Class:** Financial — Fund Instrument | **Parent:** Fund House, Exchange | **Importance:** High
**Definition:** An open-ended fund traded on exchange tracking a defined index, commodity, bond, or asset basket.
**Key Attributes:** Underlying Index/Basket, Fund House, AUM, NAV, Market Price, Premium/Discount to NAV, Expense Ratio, Tracking Error
**Lifecycle:** NFO → Listed → Trading → Potential Closure
**Examples:** NIFTY BeES, GoldBees, Bharat Bond ETF, CPSE ETF

---

#### B.6 — GOVERNMENT BOND

**Class:** Financial — Fixed Income | **Parent:** Government/RBI | **Importance:** Critical
**Definition:** Sovereign debt instrument obligating coupon and principal payment on specified dates.
**Key Attributes:** ISIN, Maturity, Coupon Rate, Face Value, Current Yield, YTM, Duration, Residual Maturity, Series
**Lifecycle:** Announced → Auctioned → Listed → Coupon Payments → Matured
**Examples:** 7.10% GS 2034, 364-Day T-Bill, State Development Loan (SDL)

---

#### B.7 — CORPORATE BOND

**Class:** Financial — Fixed Income | **Parent:** Company | **Importance:** High
**Definition:** Debt instrument issued by a company, conferring right to coupon payments and principal repayment.
**Key Attributes:** ISIN, Issuer, Credit Rating, Coupon, Maturity, Security (secured/unsecured), Covenants, Current Spread over G-Sec
**Lifecycle:** Prospectus → Issued → Listed/OTC → Coupon Payments → Matured or Default

---

#### B.8 — MUTUAL FUND

**Class:** Financial — Collective Investment | **Parent:** Fund House | **Importance:** High
**Definition:** Pooled investment vehicle collecting money from multiple investors and investing under a defined mandate.
**Key Attributes:** Scheme Name, Fund House, Category, AUM, NAV, Expense Ratio, Portfolio Holdings, Fund Manager, Benchmark, Return History, SIP Inflows

---

#### B.9 — CURRENCY PAIR

**Class:** Financial — FX Instrument | **Parent:** FX Market | **Importance:** Critical
**Definition:** The exchange rate relationship between two currencies.
**Key Attributes:** Base Currency, Quote Currency, Spot Rate, Bid/Ask, Daily Range, Volatility, Central Bank Intervention History
**Examples:** USDINR, EURUSD, GBPUSD, JPYUSD

---

#### B.10 — COMMODITY INSTRUMENT

**Class:** Financial — Commodity Derivative | **Parent:** Exchange, Commodity Market | **Importance:** High
**Definition:** A standardized contract for a physical or financial commodity traded on a recognized exchange.
**Key Attributes:** Commodity, Grade/Specification, Exchange, Contract Size, Price Unit, Settlement Method, Delivery Location, Expiry Schedule
**Examples:** CRUDEOIL-MCX, GOLD-MCX, COPPER-MCX, NATURALGAS-MCX

---


#### B.11 — COMMERCIAL PAPER

**Class:** Financial — Money Market Instrument | **Parent:** Company (issuer), RBI Framework | **Importance:** Medium | **Change Frequency:** Event
**Definition:** An unsecured short-term debt instrument issued by corporates or financial institutions to fund working capital, typically 7 to 365 days.
**Key Attributes:** Issuer, Face Value, Issue Price (discounted), Maturity, Credit Rating (minimum A2+/A1+), Yield, ISIN, Issue Date
**Lifecycle:** Issued → Held to Maturity or Secondary Sale → Redeemed at Face Value
**Relevance:** Stressed CP spreads signal corporate credit stress; CP market freezes can precipitate liquidity crises (IL&FS 2018)

---

#### B.12 — TREASURY BILL

**Class:** Financial — Government Money Market | **Parent:** Government of India, RBI | **Importance:** High | **Change Frequency:** Weekly (auction)
**Definition:** Short-term sovereign debt instrument issued by Government of India at discount, maturing in 91, 182, or 364 days.
**Key Attributes:** Tenor (91/182/364 days), Face Value (₹1 lakh), Issue Price, Cut-off Yield, Auction Date, ISIN, Risk-Free Rate Reference
**Lifecycle:** Auctioned (weekly) → Held → Matured at Face Value
**Relevance:** T-Bill yields anchor the short-end risk-free rate; serve as liquidity parking for institutions

---

#### B.13 — WARRANT

**Class:** Financial — Long-Dated Option | **Parent:** Company (issuer) | **Importance:** Low-Medium | **Change Frequency:** Event
**Definition:** A long-dated instrument giving the holder the right to buy the issuer's shares at a fixed exercise price within a defined period.
**Key Attributes:** Underlying Company, Exercise Price, Expiry (years), Premium, Conversion Ratio, Dilutive Impact on EPS, Intrinsic Value
**Lifecycle:** Issued (corporate action) → Trading → Exercised (converted to shares) or Expired
**Notes:** Rare in Indian markets; more common in global/structured finance. Similar in structure to LEAPS options but issued by company.

---

#### B.14 — CONVERTIBLE BOND

**Class:** Financial — Hybrid Instrument | **Parent:** Company (issuer) | **Importance:** Medium | **Change Frequency:** Event
**Definition:** A debt instrument carrying the embedded right to convert principal into equity shares at defined terms and timing.
**Key Attributes:** Issuer, Coupon Rate, Maturity, Conversion Price, Conversion Ratio, Premium to Current Price, Credit Rating, Current YTM, Delta (equity component)
**Lifecycle:** Issued → Coupon Payments → Conversion Window → Converted to Equity or Redeemed as Debt
**Examples:** Foreign Currency Convertible Bonds (FCCBs) issued by Indian companies in international markets

---

#### B.15 — DEPOSITARY RECEIPT

**Class:** Financial — Cross-Border Instrument | **Parent:** Underlying Equity, Custodian Bank | **Importance:** Medium | **Change Frequency:** Daily
**Definition:** A negotiable certificate representing shares in a foreign company, traded on a domestic exchange in domestic currency.
**Key Attributes:** Underlying Company, DR Type (ADR/GDR/IDR), Exchange Listed, Ratio to Underlying Shares, Premium/Discount to Underlying, Currency, Custodian
**Lifecycle:** Issued (sponsored or unsponsored) → Listed → Trading → Cancelled (converted to underlying) or Expired
**Examples:** Infosys ADR (NYSE), HDFC Bank GDR (Luxembourg), WNS ADR (NYSE)

---

#### B.16 — RIGHT (ENTITLEMENT)

**Class:** Financial — Temporary Tradeable Entitlement | **Parent:** Equity (underlying), Company | **Importance:** High (during offer period) | **Change Frequency:** Event
**Definition:** A short-lived tradeable entitlement given to existing shareholders to subscribe to new shares at a discounted price during a rights issue.
**Key Attributes:** Underlying Equity, Entitlement Ratio (e.g., 1:15), Issue Price, Subscription Period Start/End, Renunciation Rights, Intrinsic Value, Market Value
**Lifecycle:** Record Date Announced → Rights Trading Window Opens → Subscription Deadline → Lapsed (if not exercised) or Converted to Shares
**Examples:** Rights Entitlements in Reliance Rights Issue 2020 (1:15 at ₹1,257), Tata Motors Rights Issue

---

#### B.17 — STRUCTURED PRODUCT

**Class:** Financial — Complex Instrument | **Parent:** Multiple (issuer + derivatives + underlying) | **Importance:** Low-Medium | **Change Frequency:** Event
**Definition:** A customized financial instrument combining conventional securities with embedded derivatives, designed for specific risk-return profiles not available from standard instruments.
**Key Attributes:** Underlying, Structure Type (capital protected/principal at risk/leveraged), Capital Protection Level (%), Return Formula, Maturity, Issuer, Counterparty Risk, ISIN
**Lifecycle:** Structured (arranged by investment bank) → Issued → Performance Period → Matured, Called, or Default
**Examples:** Principal-Protected Notes, Market-Linked Debentures (MLDs), Basket-Linked Products, Capital Protected Certificates

---
### GROUP C — ECONOMIC & MACRO ENTITIES

#### C.1 — ECONOMY

| Attribute | Value |
|---|---|
| **Class** | Economic — Structural |
| **Parent** | None (root for macro) |
| **Children** | GDP, Inflation, Employment, Trade Balance, Central Bank, Government |
| **Importance** | Critical |
| **Change Frequency** | Slow Changing |

**Definition:** The aggregate of all productive activity, financial relationships, and resource allocation within a defined geographic or political entity.
**Purpose:** Provides macroeconomic context within which all investment activity occurs.
**Key Attributes:** Country/Region, GDP Level and Growth Rate, Inflation Rate, Unemployment Rate, Current Account, Fiscal Position, Credit Rating (Sovereign), Business Cycle Phase, Per-Capita Income
**State Changes:** Expansion → Peak → Contraction → Trough → Recovery (business cycle); Emerging → Developed (classification)
**Lifecycle:** Developing → Emerging → Developed (multi-decade progression)
**Ownership:** Governed by Government and Central Bank; no single owner
**Information Owned:** All macroeconomic variables
**Knowledge Produced:** Business cycle characterization, inflation regime, growth regime
**Decisions Influenced:** Country allocation, macro overlay, sector rotation rationale

---

#### C.2 — MACRO VARIABLE

**Class:** Economic — Data Point | **Parent:** Economy | **Importance:** High | **Change Frequency:** Monthly/Quarterly/Event
**Definition:** A quantitative measurement of a specific economic condition at the national or global level.
**Key Attributes:** Variable Name, Unit, Reporting Frequency, Agency, Historical Series, Consensus Forecast, Actual Value, Surprise vs Forecast, Revision History
**Lifecycle:** First measured → Regular reporting → Possible methodology revision → Discontinued

**Complete Macro Variable Inventory:**

| Variable | Frequency | Agency | Importance |
|---|---|---|---|
| GDP Growth Rate | Quarterly | MoSPI | Critical |
| Consumer Price Index (CPI) | Monthly | MoSPI/RBI | Critical |
| Wholesale Price Index (WPI) | Monthly | DIPP | High |
| Industrial Production (IIP) | Monthly | MoSPI | High |
| Unemployment Rate | Monthly | MOSPI/CMIE | Medium |
| Current Account Balance | Quarterly | RBI | High |
| Fiscal Deficit | Monthly/Annual | MoF | High |
| PMI Manufacturing | Monthly | S&P Global | High |
| PMI Services | Monthly | S&P Global | High |
| GST Collections | Monthly | MoF | High |
| Trade Balance | Monthly | DGCI&S | High |
| Foreign Exchange Reserves | Weekly | RBI | High |
| Bank Credit Growth | Monthly | RBI | High |
| Core Sector Output | Monthly | DIPP | Medium |

---

#### C.3 — INTEREST RATE

**Class:** Economic — Financial | **Parent:** Central Bank/Economy | **Importance:** Critical | **Change Frequency:** Event Driven
**Definition:** The cost of borrowing money, expressed as percentage per annum; determined by central bank policy or market forces.
**Key Attributes:** Rate Type, Current Level, Direction, History, Market-Implied Forward Path, Real vs Nominal
**Lifecycle:** Set by central bank → Market rates derived → Policy adjusted → New level set
**Examples:** RBI Repo Rate, US Fed Funds Rate, 10-Year G-Sec Yield, MCLR, Call Money Rate

---

#### C.4 — YIELD CURVE

**Class:** Economic — Derived | **Parent:** Bond Market, Interest Rate | **Importance:** Critical
**Definition:** The graphical relationship between yields and maturities for the same issuer's debt.
**Key Attributes:** Shape (normal/inverted/flat/humped), Short-End Rate, 10Y Rate, Spread (10Y-2Y), Implied Forward Rates
**State Changes:** Normal → Flattening → Inverted (recession signal) → Steepening

---

#### C.5 — SECTOR

| Attribute | Value |
|---|---|
| **Class** | Economic — Structural Classification |
| **Parent** | Economy |
| **Children** | Industries, Companies |
| **Importance** | Critical |
| **Change Frequency** | Slow Changing |

**Definition:** A broad grouping of companies sharing similar primary economic activity, input factors, and market dynamics.
**Purpose:** Enable sector-level analysis, comparison, and rotation strategies. Identify macro-to-company transmission paths.
**Key Attributes:** Sector Name, Classification Standard (GICS/NIC/NSE), Listed Company Count, Total Market Cap, Sector Index, Regulatory Environment, Cyclicality, Macro Sensitivities
**Lifecycle:** Emerging → Growing → Mature → Declining → Restructured
**Examples:** Financials, IT, Healthcare, Industrials, Consumer Staples, Consumer Discretionary, Materials, Energy, Utilities, Real Estate

---

#### C.6 — INDUSTRY

**Class:** Economic — Sub-Classification | **Parent:** Sector | **Importance:** High | **Change Frequency:** Slow
**Definition:** A specific grouping within a sector sharing common products, production processes, or customer bases.
**Key Attributes:** Industry Name, Parent Sector, Competitive Structure, Regulatory Environment, Key Input Costs, Demand Drivers, Pricing Power, Cycle Phase
**Examples:** Private Banks, IT Services, Pharmaceutical Generics, Steel, Cement, Auto OEM, FMCG, Insurance

---

#### C.7 — THEME

**Class:** Economic — Cross-Sector Narrative | **Parent:** Economy, Multiple Sectors | **Importance:** High | **Change Frequency:** Slow
**Definition:** A cross-sector investment narrative driven by a structural trend that benefits multiple industries simultaneously.
**Key Attributes:** Theme Name, Driving Trend, Beneficiary Sectors, Estimated Duration, Current Phase, Representative Companies, Theme-specific metrics
**Lifecycle:** Emerging → Mainstream → Crowded → Fading
**Examples:** Digital India, Make in India/PLI, EV Transition, Renewable Energy, Capital Expenditure Supercycle

---

### GROUP D — ORGANIZATIONAL ENTITIES

#### D.1 — LISTED COMPANY

| Attribute | Value |
|---|---|
| **Class** | Organizational — Legal Entity |
| **Parent** | Promoter Group (ownership), Market (listing) |
| **Children** | Subsidiaries, Associates, Financial Statements, Corporate Actions, Stocks |
| **Importance** | Critical |
| **Change Frequency** | Daily (market), Quarterly (fundamentals), Event (corporate actions) |

**Definition:** A legally incorporated entity engaged in commercial activity, with shares listed on a recognized stock exchange.
**Purpose:** Primary unit of equity investment analysis — the entity around which all company-level knowledge is built.
**Why it exists:** Companies are the primary wealth-creating machines in a market economy. Understanding companies is the core of fundamental investment analysis.
**Lifecycle:** Incorporated → Private → IPO/Listing → Growth → Maturity → Decline → Acquisition/Merger/Delisting/Liquidation
**Key Attributes:** Company Name, ISIN, NSE/BSE Code, CIN, Sector/Industry, Promoter Holding %, Market Cap (Large/Mid/Small Cap), Listing Date, Board Members, Auditor, Credit Rating, Annual Revenue, Net Profit, EBITDA Margin, Debt/Equity, ROE, ROCE, Free Cash Flow
**State Changes:** Private → Listed; Normal → Acquisition Target; Investment Grade → Downgrade; Active → Bankruptcy Proceedings
**Ownership:** Shareholders (public + promoter); governed by Board; regulated by SEBI, MCA
**Dependencies:** Stock (market price), Financial Statements (fundamental data), Market Regime (valuation context), Sector (competitive context)
**Information Owned:** Financial Statements, Corporate Actions, Management Commentary, Regulatory Filings
**Knowledge Produced:** Entity behavioral model, valuation history, earnings pattern, management quality assessment
**Knowledge Consumed:** Sector dynamics, macro environment, commodity prices (input costs), interest rates (cost of capital)
**Decisions Influenced:** Buy/Sell/Hold on its stock, position sizing, target allocation, conviction level
**Risks:** Business, financial, governance, regulatory, competitive, macro, key-person
**Examples:** Reliance Industries, HDFC Bank, Infosys, TCS, ITC, Asian Paints, Dr Reddy's
**Relationships:** Issues Equity; produces Financial Statements; executes Corporate Actions; competes with Peer Companies; supplies to/buys from Supply Chain Partners

---

#### D.2 — PROMOTER GROUP

**Class:** Organizational — Ownership Group | **Parent:** None (independent) | **Importance:** High | **Change Frequency:** Slow
**Definition:** The founding individual(s), family, or controlling entity holding significant ownership and exercising effective control over a company.
**Key Attributes:** Promoter Names, % Holding, Pledged %, Related Party Entities, Group Companies, Track Record, Capital Allocation Philosophy
**State Changes:** High ownership → Selling; Low pledge → Increasing (stress signal); Minority → Open Offer; Control → Ceding control

---

#### D.3 — REGULATOR

**Class:** Organizational — Governmental | **Parent:** Government | **Importance:** Critical | **Change Frequency:** Slow (rules), Event (orders)
**Definition:** Statutory authority empowered to govern a specific domain through rule-making, licensing, and enforcement.
**Examples:** SEBI, RBI, IRDAI, PFRDA, CCI, MCA, TRAI, CDSCO, CERC

---

#### D.4 — CENTRAL BANK

**Class:** Organizational — Monetary Authority | **Parent:** Government | **Importance:** Critical | **Change Frequency:** Event
**Definition:** Institution responsible for monetary policy, currency issuance, banking oversight, and forex management.
**Key Attributes:** Name, Governor, MPC Composition, Repo Rate, Inflation Target, Forex Reserves, Policy Stance
**State Changes:** Accommodative → Neutral → Tightening → Pivoting
**Examples:** Reserve Bank of India, US Federal Reserve, European Central Bank, Bank of Japan

---

#### D.5 — FII (Foreign Institutional Investor)

**Class:** Organizational — Market Participant | **Parent:** Global Capital Markets | **Importance:** Critical | **Change Frequency:** Daily (flows)
**Definition:** A registered foreign entity authorized to invest in Indian financial markets.
**Key Attributes:** Registration Type, Home Country, AUM Deployed in India, Current Equity/Debt Exposure, Net Flow (daily/monthly)
**State Changes:** Net Buyer → Net Seller → Neutral; Fully Invested → Underweight → Exiting India
**Examples:** GIC Singapore, Abu Dhabi Investment Authority, Vanguard, BlackRock, Fidelity

---

#### D.6 — DII (Domestic Institutional Investor)

**Class:** Organizational — Market Participant | **Importance:** Critical | **Change Frequency:** Daily
**Definition:** Domestic financial institution investing on behalf of retail savers or beneficiaries.
**Key Attributes:** Type (MF/Insurance/Pension), Total AUM, Equity Allocation %, Monthly Inflows
**Examples:** SBI Mutual Fund, HDFC AMC, LIC, NPS Trust, EPFO

---

#### D.7 — FUND HOUSE

**Class:** Organizational — Asset Manager | **Importance:** High | **Change Frequency:** Slow
**Definition:** A SEBI-registered entity managing collective investment schemes (mutual funds, AIFs) on behalf of investors.
**Key Attributes:** AMC Name, Total AUM, Number of Schemes, Equity AUM, Debt AUM, Top Holdings Aggregate, MF Category Mix
**Examples:** SBI Mutual Fund, HDFC AMC, ICICI Prudential AMC, Mirae Asset, Axis AMC

---

#### D.8 — BROKER

**Class:** Organizational — Market Intermediary | **Importance:** High | **Change Frequency:** Static
**Definition:** SEBI-registered intermediary facilitating buy and sell orders for clients on stock exchanges.
**Key Attributes:** Broker Code, Exchange Membership, Client Count, Technology Platform, Margin Policy, Brokerage Structure
**Examples:** Zerodha, Angel Broking, ICICI Securities, HDFC Securities

---

#### D.9 — RATING AGENCY

**Class:** Organizational — Financial Services | **Importance:** High
**Definition:** Entity assessing and publishing creditworthiness ratings for debt instruments and issuers.
**Examples:** CRISIL, ICRA, CARE, India Ratings, Moody's, S&P, Fitch

---


#### D.10 — UNLISTED COMPANY

**Class:** Organizational — Legal Entity | **Parent:** Promoter Group / Private Investors | **Importance:** Medium | **Change Frequency:** Slow
**Definition:** A legally incorporated operating entity whose shares have not been listed on any recognized stock exchange.
**Key Attributes:** Company Name, CIN, Industry, Estimated Revenue, Ownership Structure, Last Valuation, Potential Listing Timeline, Auditor
**Lifecycle:** Incorporated → Privately Operating → Pre-IPO Path / Continued Private / Strategic Acquisition
**Relevance:** Pre-IPO investment intelligence; supply-chain mapping; competitive analysis for listed peers; grey market premium tracking

---

#### D.11 — SUBSIDIARY

**Class:** Organizational — Legal Entity | **Parent:** Parent Company | **Importance:** High | **Change Frequency:** Slow
**Definition:** A company in which a parent entity holds more than 50% equity or exercises effective control, consolidated into parent financials.
**Key Attributes:** Subsidiary Name, Parent Company, Ownership %, Nature of Business, Revenue Contribution (% of consolidated), Minority Interest %, Consolidation Treatment, ISIN (if separately listed)
**Lifecycle:** Incorporated (greenfield) or Acquired → Operating → Possible Merger into Parent / Demerger / Stake Sale / IPO
**Examples:** HDB Financial Services (HDFC Bank subsidiary), HDFC Securities, Tata Motors Finance, Bajaj Housing Finance

---

#### D.12 — GOVERNMENT

**Class:** Organizational — Sovereign Authority | **Parent:** None (sovereign) | **Importance:** Critical | **Change Frequency:** Slow (elections), Event (policy decisions)
**Definition:** The elected sovereign authority with constitutional power to legislate, tax, spend, borrow, and regulate within its jurisdiction.
**Key Attributes:** Level (Central/State), Political Majority, Budget Size, Fiscal Deficit, Debt/GDP, Disinvestment Pipeline, Capital Expenditure Plan, Policy Priorities, Election Schedule
**Lifecycle:** Elected → Governing → Election Cycle → Possible Change of Government
**Decisions Influenced:** Budget policy, PSU disinvestment, infrastructure capex, sector regulation, tax rates, foreign investment rules
**State Changes:** Majority → Coalition (policy uncertainty); Pro-capex → Fiscal consolidation; Pre-election → Post-election
**Examples:** Government of India (Union Budget), Maharashtra State Government, Ministry of Finance, Ministry of Heavy Industries

---

#### D.13 — HEDGE FUND / AIF

**Class:** Organizational — Alternative Asset Manager | **Parent:** SEBI Registration | **Importance:** High | **Change Frequency:** Slow
**Definition:** A pooled investment vehicle for sophisticated investors with fewer restrictions, able to use leverage, short positions, and complex derivatives.
**Key Attributes:** Fund Name, SEBI Category (AIF Cat I/II/III), AUM, Strategy Type, Leverage Level, Net Long/Short Exposure, Gross Exposure, Performance Fee Structure, Lock-up Period
**Lifecycle:** Registered with SEBI → Capital Raising → Portfolio Construction → Active Management → Harvesting → Wind-up
**Relevance:** Cat III AIF (hedge fund equivalent) — smart money tracker; large F&O OI changes can signal hedge fund positioning shifts

---

#### D.14 — INSURANCE COMPANY

**Class:** Organizational — Institutional Investor | **Parent:** IRDAI Regulation | **Importance:** High | **Change Frequency:** Slow (AUM), Daily (flows)
**Definition:** A regulated entity collecting insurance premiums and deploying the float primarily in long-duration bonds and equities per IRDAI investment norms.
**Key Attributes:** Company Name, Type (Life/General/Health), Total AUM, Equity AUM, Debt AUM, Equity % Allocation, Net Premium Income, Investment Policy, Daily Flow Direction
**Lifecycle:** Licensed → Operating → Possible Consolidation or Acquisition
**State Changes:** Premium growth → Equity deployment; Claim shock → Defensive positioning; Bull market → Equity limit reached
**Examples:** LIC (largest domestic equity holder), SBI Life, HDFC Life, ICICI Prudential Life, New India Assurance

---

#### D.15 — PENSION FUND

**Class:** Organizational — Institutional Investor | **Parent:** PFRDA Regulation | **Importance:** High | **Change Frequency:** Slow (AUM), Monthly (contribution inflows)
**Definition:** A regulated fund collecting regular contributions from employees and employers, investing for long-term retirement benefit delivery.
**Key Attributes:** Fund Name, AUM, Equity Allocation (%), Debt Allocation (%), Monthly Contribution Inflow, Investment Policy, Beneficiary Count, Liability Duration
**Lifecycle:** Established → Contribution Accumulation Phase → Maturity → Benefit Distribution Phase
**Relevance:** Structural equity demand source; very long duration; systematic buyer regardless of market conditions
**Examples:** EPFO (largest DII by AUM), NPS Trust, Coal Mines Provident Fund, SEBI-regulated superannuation funds

---

#### D.16 — RETAIL INVESTOR

**Class:** Human — Individual Market Participant | **Parent:** Broker Account, Depository | **Importance:** Medium (individual), High (aggregate) | **Change Frequency:** Continuous
**Definition:** An individual investor (non-institutional) deploying personal capital in financial markets via a registered broker and demat account.
**Key Attributes:** Investor Segment (HNI/Retail), Account Type (demat/trading), Risk Profile, Investment Horizon, Platform Used, SIP Participation, Delivery vs Speculative Mix
**Lifecycle:** Account Opened → Onboarding → Active Investing → Dormant (market downturn) → Re-engaged / Exited
**Collective Behavior Intelligence:** SIP flows (systematic demand signal); panic selling (extreme sentiment signal); retail delivery % in market data; IPO subscription from retail tranche
**Relevance:** Tracked as aggregate, not individual. Monthly MF SIP numbers, NSE active investor count, retail F&O participation ratio

---

#### D.17 — MARKET MAKER

**Class:** Organizational — Liquidity Provider | **Parent:** Exchange (registered) | **Importance:** High | **Change Frequency:** Contractual
**Definition:** A registered participant contractually obligated to continuously provide two-sided (bid-ask) quotes in assigned instruments, ensuring minimum liquidity standards.
**Key Attributes:** Assigned Instruments, Maximum Spread Obligation, Minimum Quote Size, Uptime Obligation (%), Incentive/Fee Structure, Performance Record
**Lifecycle:** Registered with Exchange → Active Quoting → Quarterly Performance Review → Contract Renewal or Withdrawal
**Relevance:** Market maker withdrawal signals reduced liquidity confidence; in options, MM presence determines bid-ask quality and hedging efficiency

---

#### D.18 — INVESTMENT BANK

**Class:** Organizational — Financial Services | **Parent:** SEBI/RBI Regulation | **Importance:** High | **Change Frequency:** Slow
**Definition:** A financial institution providing capital raising (ECM/DCM), M&A advisory, structured finance, and institutional distribution services.
**Key Attributes:** Name, Regulatory Registration, ECM Pipeline, DCM Deal Flow, Block Deal Activity, Research Coverage Universe
**Lifecycle:** Established → Ongoing advisory and transaction business → Possible Consolidation
**Relevance as Signal:** IPO lead manager quality → company quality signal; block deal arranger identity → institutional buyer/seller quality; M&A advisor → corporate event early signal
**Examples:** Kotak Investment Banking, JM Financial, Axis Capital, Goldman Sachs India, Morgan Stanley India, Jefferies India

---

#### D.19 — RESEARCH FIRM

**Class:** Organizational — Information Producer | **Parent:** SEBI Registration (Research Analyst) | **Importance:** High | **Change Frequency:** Slow (firm), Continuous (output)
**Definition:** An entity producing formal equity or macro research reports, ratings, and price targets consumed by institutional and retail investors.
**Key Attributes:** Firm Name, Registration Type, Coverage Universe Size, Rating System, Analyst Accuracy Track Record (historical), Influential Sector Specializations, Institutional Client Base
**Lifecycle:** Established → Research Publication Cycle → Reputation Evolution → Possible Shutdown/Acquisition
**Relevance as Evidence Source:** Analyst target price upgrades/downgrades = directional conviction evidence; consensus estimate changes = expectation revision evidence; initiations = institutional attention catalyst
**Examples:** Motilal Oswal Research, Emkay Global, Nuvama Institutional, Edelweiss, UBS India, Jefferies India Research

---

#### D.20 — NEWS AGENCY

**Class:** Organizational — Information Distributor | **Parent:** None (independent editorial) | **Importance:** High | **Change Frequency:** Continuous
**Definition:** An entity that originates, aggregates, or distributes news content with potential materiality to financial markets.
**Key Attributes:** Agency Name, Type (wire/financial newspaper/TV/digital), Coverage Focus, Speed (real-time vs daily), Accuracy Track Record, SEBI Registration (if applicable), Machine-Readable Feed Available
**Lifecycle:** Established → Ongoing publishing → Reputation evolution
**Relevance:** Breaking news triggers immediate price movement; exchange announcements are the primary authoritative news source for corporate events
**Examples:** Reuters, Bloomberg, Moneycontrol, CNBC-TV18, Economic Times, PTI, ANI, NSE Corporate Announcements Feed, BSE Filings

---

#### D.21 — INDEX PROVIDER

**Class:** Organizational — Financial Services | **Parent:** SEBI Registration | **Importance:** High | **Change Frequency:** Slow
**Definition:** An entity that designs, calculates, maintains, and licenses financial market indices under defined methodologies.
**Key Attributes:** Name, Index Family, Total Indices, Methodology Standards, Rebalancing Governance, Licensing Revenue Model, Global Reach
**Lifecycle:** Founded → Index Family Development → Licensing Scale-up → Ongoing with periodic new index launches
**Relevance:** Index rebalancing decisions force passive fund trades; MSCI inclusion/exclusion drives large FII flows (MSCI India weight changes)
**Examples:** NSE Indices Ltd (NIFTY family), S&P Dow Jones Indices (SENSEX), MSCI (India country indices for FII benchmarking), FTSE Russell

---
### GROUP E — EVENT ENTITIES

#### E.1 — CORPORATE ACTION (Parent Entity)

| Attribute | Value |
|---|---|
| **Class** | Event — Corporate |
| **Parent** | Company |
| **Importance** | Critical |
| **Change Frequency** | Event Driven |

**Definition:** Any announced action by a company that changes the terms, structure, or value of its outstanding securities.
**Lifecycle:** Announced → Board Approval → Shareholder Approval (if needed) → Record Date → Ex-Date → Effective → Completed

**Corporate Action Sub-Entities:**

| Sub-Entity | Definition | Price Mechanism | Signal Meaning |
|---|---|---|---|
| **Dividend** | Cash distribution to shareholders | Negative adjustment on ex-date | Profitability confidence |
| **Stock Split** | Reduced face value, increased share count | Price adjusted proportionally | Affordability signal |
| **Bonus Issue** | Free shares to existing holders | Price adjusted proportionally | Retained earnings strength |
| **Rights Issue** | New shares at discount to existing holders | Dilutive | Capital need signal |
| **Buyback** | Company repurchases own shares | Positive (supply reduction) | Management believes undervaluation |
| **Merger (Acquirer)** | Company absorbs another | Variable (synergy vs dilution) | Strategic intent |
| **Merger (Target)** | Company being absorbed | Usually positive (premium) | Control change |
| **Demerger** | Subsidiary spun off independently | Variable | Value unlocking |
| **Open Offer** | Acquirer must buy 26%+ from public | Positive (premium offer) | Control change signal |
| **IPO** | First public listing | New entity created | Growth capital need |
| **Delisting** | Shares removed from exchange | Usually positive offer | Promoter wants full control |

---

#### E.2 — EARNINGS EVENT

**Class:** Event — Financial | **Parent:** Company | **Importance:** Critical | **Change Frequency:** Quarterly
**Definition:** The quarterly/annual release of financial results including revenue, profit, margins, and management commentary.
**Key Attributes:** Company, Quarter/Year, Announcement Date, Revenue vs Estimate, EBITDA vs Estimate, PAT vs Estimate, EPS Surprise %, Management Guidance, Conference Call Date
**Lifecycle:** Quarter Ends → Results Date Announced → Pre-Result Period → Results Released → Analyst Revisions → Institutional Repositioning → New Knowledge Integrated

---

#### E.3 — MONETARY POLICY EVENT

**Class:** Event — Macro | **Parent:** Central Bank | **Importance:** Critical | **Change Frequency:** Bi-monthly
**Definition:** Formal decision-making meeting of the central bank's MPC resulting in rate decisions and policy communication.
**Key Attributes:** Meeting Date, Pre-meeting Consensus, Decision (Rate/Stance), Statement Language, Forward Guidance Interpretation
**Lifecycle:** Calendar Published → Expectations Form → Pre-Policy Rate Activity → Decision Announced → Market Reaction → Analyst Interpretation

---

#### E.4 — BUDGET EVENT

**Class:** Event — Fiscal | **Parent:** Government | **Importance:** Critical | **Change Frequency:** Annual
**Definition:** Annual presentation of government revenue, expenditure plans, tax proposals, and economic priorities.
**Key Attributes:** Budget Date, Type (Union/Interim/State), Fiscal Deficit Target, Capex Plan, Tax Changes, Sector Allocations

---

#### E.5 — INDEX REBALANCING EVENT

**Class:** Event — Market Structure | **Parent:** Index, Index Provider | **Importance:** High | **Change Frequency:** Quarterly
**Definition:** Periodic review and modification of index constituents and weights by the index provider.
**Key Attributes:** Index Name, Review Date, Effective Date, Additions, Deletions, Weight Changes, Estimated Passive Fund Forced Flow

---

#### E.6 — GEOPOLITICAL EVENT

**Class:** Event — Macro | **Importance:** High | **Change Frequency:** Event Driven
**Definition:** Political, military, or diplomatic development creating market uncertainty or changing trade/investment flows.
**Key Attributes:** Event Type, Nations Involved, Intensity, Duration, Commodity Impact, Capital Flow Impact, Sector Impact
**Examples:** India-Pakistan tension, Russia-Ukraine conflict, US-China trade war, OPEC production cut

---

#### E.7 — NEWS EVENT

**Class:** Event — Information | **Importance:** High | **Change Frequency:** Intraday/Event
**Definition:** A published piece of information that may be material to the valuation or risk of one or more entities.
**Key Attributes:** Headline, Source, Timestamp, Entities Mentioned, Materiality, Sentiment (positive/negative/neutral), Verification Status (confirmed/unconfirmed/rumour)

---

### GROUP F — FINANCIAL STATEMENT ENTITIES

#### F.1 — FINANCIAL STATEMENT (Parent)

**Class:** Financial — Disclosure | **Parent:** Company | **Importance:** Critical | **Change Frequency:** Quarterly/Annual
**Definition:** Formal, regulated disclosure of a company's financial position and performance under defined accounting standards.
**Lifecycle:** Period Ends → Prepared → Audited (annual) → Filed with Exchange → Published → Analyst Modelling → Archive

**Sub-Entities:**

| Entity | Definition | Frequency | Key Metrics |
|---|---|---|---|
| **Income Statement (P&L)** | Revenue, costs, profit over a period | Q/Annual | Revenue, EBITDA, EBIT, PAT, EPS |
| **Balance Sheet** | Assets, liabilities, equity at a point in time | Q/Annual | Total Assets, Debt, Equity, Working Capital |
| **Cash Flow Statement** | Sources and uses of cash over a period | Q/Annual | CFO, CFI, CFF, Free Cash Flow |
| **Notes to Accounts** | Detailed disclosures behind primary statements | Q/Annual | RPT, contingencies, accounting policies |
| **Segment Report** | Revenue and profit by business division | Q/Annual | Segment revenue, margins, assets |
| **Management Discussion** | Management narrative explanation of results | Q/Annual | Outlook, challenges, strategy |
| **Auditor's Report** | Independent verification and opinion | Annual | Opinion (clean/qualified), emphasis |
| **Annual Report** | Complete yearly disclosure package | Annual | All of the above + governance |

---

### GROUP G — PARTICIPANT ACTIVITY ENTITIES

#### G.1 — PORTFOLIO

| Attribute | Value |
|---|---|
| **Class** | Financial — Participant Activity |
| **Parent** | Investor |
| **Children** | Positions, Trades, Performance Records |
| **Importance** | Critical |
| **Change Frequency** | Daily |

**Definition:** The complete collection of financial instruments held by an investor at a point in time, together with available cash.
**Purpose:** The unit of investment management. All risk, return, and allocation decisions reference the portfolio.
**Key Attributes:** Owner, Total Value, Cash Reserve, Deployed Capital, Open Positions Count, Sector Exposure Map, Beta, Correlation Matrix, Unrealized P&L, Realized P&L, Return vs Benchmark, Max Drawdown, Sharpe Ratio, Benchmark, Constraints (max position size, max sector weight, max beta)
**Lifecycle:** Created (capital deployed) → Positions Added → Active Management → Positions Closed → Potentially Wound Down
**State Changes:** Fully Deployed → Partially Cash → Fully Cash; Within Limits → Breach → Corrected; Outperforming → Underperforming
**Ownership:** Owned by Investor; managed by Portfolio Manager
**Information Owned:** All position records, trade history, performance history
**Knowledge Produced:** Portfolio behavior patterns, position holding period analysis, strategy attribution
**Decisions Influenced:** Every new decision (context: correlation, concentration, size, capital availability)
**Risks:** Concentration, drawdown, liquidity, benchmark risk

---

#### G.2 — POSITION

| Attribute | Value |
|---|---|
| **Class** | Financial — Participant Activity |
| **Parent** | Portfolio |
| **Children** | Trades (creating/modifying this position) |
| **Importance** | Critical |
| **Change Frequency** | Intraday to Daily |

**Definition:** Current holding in a specific instrument — quantity, average entry price, and current market value.
**Key Attributes:** Instrument, Direction (Long/Short), Quantity, Average Entry Price, Current Market Price, Unrealized P&L, R-Multiple, Entry Date, Position Age, Stop Loss, Target, Governance State (ACTIVE_CARRY/MONITORING/AT_RISK), Decision Reference, Size as % of Portfolio
**Lifecycle:** Entered → Monitored → Partially Closed → Fully Closed → Archived
**State Changes:** Open → At Risk (near stop) → Stop Hit (closed); Open → Target Reached; Open → Stale; Active Carry → Governance Review
**Ownership:** Owned by Portfolio; created by Decision

---

#### G.3 — TRADE

**Class:** Financial — Transaction Record | **Parent:** Position, Portfolio | **Importance:** High | **Change Frequency:** Event
**Definition:** A completed transaction — exchange of instrument for money at specific price, quantity, and time.
**Key Attributes:** Trade ID, Instrument, Direction, Quantity, Price, Timestamp, Exchange, Broker, Order ID, Brokerage, STT, Total Cost, Net P&L (for close), Decision Reference, Trade Type (Entry/Exit/Partial)
**Lifecycle:** Order Placed → Filled → Confirmed → Settled → Archived

---

#### G.4 — ORDER

**Class:** Financial — Execution Intent | **Parent:** Decision, Position | **Importance:** High | **Change Frequency:** Intraday
**Definition:** An instruction submitted to broker/exchange to buy/sell a specific instrument at defined conditions.
**Key Attributes:** Order ID, Instrument, Order Type (Market/Limit/SL/SL-M), Direction, Quantity, Price, Trigger Price, Validity, Status (Pending/Filled/Rejected/Cancelled), Timestamp
**State Changes:** Placed → Pending → Partially Filled → Filled / Cancelled / Rejected / Expired

---

#### G.5 — HOLDING

**Class:** Financial — Static Snapshot | **Parent:** Portfolio | **Importance:** Medium
**Definition:** A static snapshot of a portfolio's position in an instrument at a specific point in time.
**Key Attributes:** Instrument, Quantity, Average Cost, Current Value, Gain/Loss, Holding Duration, Tax Classification

---


#### G.6 — EXECUTION

**Class:** Financial — Transaction Detail | **Parent:** Order, Trade | **Importance:** High | **Change Frequency:** Intraday
**Definition:** A specific fill event representing a portion or all of an order being matched at a specific price and time on an exchange.
**Key Attributes:** Execution ID, Order ID, Instrument, Executed Quantity, Executed Price, Timestamp (nanosecond-level on exchange), Exchange Match ID, Slippage vs Expected Price
**Lifecycle:** Order Placed → Match Found on Exchange → Execution Generated → Partial or Full Fill → Trade Formed on Complete Fill
**Note:** A single order may result in multiple executions (partial fills) before the order is fully complete.

---

#### G.7 — TRANSACTION

**Class:** Financial — Financial Event Record | **Parent:** Portfolio | **Importance:** High | **Change Frequency:** Event
**Definition:** Any financial event that changes the portfolio's cash, holdings, or valuation — encompassing trades, dividends, corporate actions, fees, and taxes.
**Key Attributes:** Transaction ID, Type (trade/dividend/bonus/split/fee/tax/CA), Amount (cash impact), Date, Instrument (if applicable), Tax Treatment, Settlement Status
**Lifecycle:** Financial event occurs → Transaction recorded → Settled → Archived
**Note:** Broader than Trade (which is only a buy/sell). Every portfolio valuation change should trace to a Transaction record.

---

#### G.8 — BLOCK DEAL

**Class:** Financial — Special Institutional Transaction | **Parent:** Trade, Exchange | **Importance:** High | **Change Frequency:** Event
**Definition:** A large single transaction (≥ ₹10 crore) executed in a dedicated block deal window, typically representing institutional portfolio repositioning.
**Key Attributes:** Date, Instrument, Quantity, Price, Buyer Identity, Seller Identity, Block Window (9:15-9:50 AM or 2:05-2:50 PM IST), Notional Value, % of Daily Average Volume
**Lifecycle:** Bilateral negotiation → Block Deal Window → Order submitted → Matched and disclosed to exchange → Published immediately
**Signal Intelligence:** Who is buying (identity of buyer) matters as much as the quantity. FII buying in block = foreign conviction signal. Promoter selling = watch carefully.

---

#### G.9 — BULK DEAL

**Class:** Financial — Regulatory Disclosure Record | **Parent:** Trade, Exchange | **Importance:** High | **Change Frequency:** Event
**Definition:** Any trade or aggregate of trades in a single session by a single entity exceeding 0.5% of total equity shares — mandatorily reported to the exchange.
**Key Attributes:** Date, Instrument, Trading Member, Client Name, Transaction Type, Quantity, Price, % of Total Outstanding Shares
**Lifecycle:** Trade executed → 0.5% threshold crossed → Exchange notification filed EOD → Published on BSE/NSE website
**Signal Intelligence:** Promoter purchases/sales, FII position building/unwinding, mutual fund entry/exit — all visible here with 1-day lag.

---

#### G.10 — FUND FLOW RECORD

**Class:** Financial — Aggregate Institutional Flow | **Parent:** Market, FII/DII/Category | **Importance:** Critical | **Change Frequency:** Daily
**Definition:** A daily summary of net buying or selling by a defined category of institutional participant across market segments.
**Key Attributes:** Date, Participant Category (FII/DII/MF/Insurance/Proprietary), Segment (Equity Cash/F&O/Debt), Gross Buy Value, Gross Sell Value, Net Flow (Buy-Sell), Running 5D/30D/YTD Net, Index Correlation
**Lifecycle:** Market Close → Participant reporting to Exchange/SEBI → Published (same day EOD) → Archived daily
**Why Critical:** FII net flow is the single most reliable leading indicator of large-cap index direction at 5-10 day horizon. DII flows act as counter-cyclical stabilizer.

---
### GROUP H — MARKET INTELLIGENCE ENTITIES

#### H.1 — UNIVERSE

**Class:** Intelligence — Structural | **Parent:** Market | **Importance:** Critical | **Change Frequency:** Weekly
**Definition:** The complete set of instruments the system is capable of analyzing and potentially trading.
**Key Attributes:** Instrument Count, Inclusion Criteria (liquidity, market cap, exchange), Exclusion Criteria (F&O ban, governance flags), Last Updated, Coverage %
**Lifecycle:** Defined → Populated → Weekly Rebuild → Expanded/Contracted as criteria evolve

---

#### H.2 — MARKET REGIME

| Attribute | Value |
|---|---|
| **Class** | Intelligence — Contextual |
| **Parent** | Market |
| **Importance** | Critical |
| **Change Frequency** | Slow to Weekly |

**Definition:** The characterized state of the market describing dominant conditions governing price behavior, trend persistence, and strategy effectiveness.
**Key Attributes:** Regime Type (Trending/Ranging/Volatile/Transitioning), Volatility Level (Low/Medium/High/Extreme), Directional Bias, Breadth Condition, Macro Alignment, Confidence in Classification, Duration in Current Regime
**State Changes:** Trending → Transitioning → Ranging → Trending; Low Volatility → Regime Shock → High Volatility → Mean Reversion
**Knowledge Produced:** Strategy reliability weights by regime; evidence weight modulation
**Decisions Influenced:** Position sizing, strategy selection, conviction threshold calibration

---

#### H.3 — SIGNAL

**Class:** Intelligence — Derived | **Parent:** Indicator/Pattern/Information Source | **Importance:** High | **Change Frequency:** Daily/Intraday
**Definition:** A derived output from information processing indicating a potential directional bias for an instrument.
**Key Attributes:** Signal Type, Instrument, Direction, Strength, Source, Timestamp, Expiry, Regime Validity, Historical Accuracy
**Important Note:** A signal alone does NOT constitute a decision. Signals are inputs to the reasoning process.

---

#### H.4 — INDICATOR

**Class:** Intelligence — Derived | **Parent:** Price/Volume Data | **Importance:** High | **Change Frequency:** Daily/Intraday
**Definition:** A computed mathematical transformation of price, volume, or other data designed to reveal a pattern not visible in raw data.
**Key Attributes:** Name, Formula/Logic, Parameters, Current Value, Signal Output, Historical Accuracy in Current Regime
**Examples:** RSI, MACD, Bollinger Bands, ATR, ADX, Moving Averages (SMA/EMA), OBV, VWAP

---

#### H.5 — PATTERN

**Class:** Intelligence — Behavioral | **Parent:** Price/Volume History | **Importance:** High
**Definition:** A recognizable configuration of price and/or volume data that historically precedes a defined outcome with measurable probability.
**Key Attributes:** Pattern Name, Formation Rules, Min Bar Count, Reliability Score (by regime), Completion Status, Expected Outcome, Historical Base Rate
**Examples:** Cup-and-Handle, Ascending Triangle, Flag, Head & Shoulders, Volume Dry-Up before breakout

---

#### H.6 — FACTOR

**Class:** Intelligence — Derived | **Parent:** Universe of Instruments | **Importance:** High
**Definition:** A systematic, documented characteristic of securities that explains a portion of return variation across the universe.
**Key Attributes:** Factor Name, Definition, Historical Premium, Persistence, Capacity, Current Factor Performance, Correlation with Other Factors
**Examples:** Value (P/B, P/E), Momentum (12-1M return), Quality (ROE, low debt), Low Volatility, Small Cap, Growth, Dividend Yield

---

#### H.7 — SCORE

**Class:** Intelligence — Derived Composite | **Parent:** Multiple Information Sources | **Importance:** High
**Definition:** A computed composite numerical rating summarizing multiple information inputs about an entity relative to peers.
**Key Attributes:** Score Type, Entities Scored, Components, Weights, Current Value, Percentile Rank, Historical Score, Change Direction

---

#### H.8 — ALERT

**Class:** Intelligence — Notification | **Parent:** Monitoring Process | **Importance:** High | **Change Frequency:** Event
**Definition:** An automated notification triggered by a predefined condition being met.
**Key Attributes:** Alert Type, Trigger Condition, Entity, Triggered At (price/value), Timestamp, Priority, Delivery Channel, Acknowledgement Status

---


#### H.9 — WATCHLIST

**Class:** Intelligence — Curated Subset | **Parent:** Universe, Analyst/Portfolio | **Importance:** High | **Change Frequency:** Weekly
**Definition:** A curated subset of the universe containing instruments selected for active monitoring at elevated attention frequency and alert sensitivity.
**Key Attributes:** Watchlist Name, Instrument Count, Selection Criteria, Owner (system/analyst), Creation Date, Last Updated, Associated Alert Configuration, Review Frequency
**Lifecycle:** Created → Instruments Added (screening/manual) → Active Monitoring → Instruments Promoted to Decision or Removed → Deactivated

---

#### H.10 — SCREEN

**Class:** Intelligence — Quantitative Filter | **Parent:** Universe, Data Pipeline | **Importance:** High | **Change Frequency:** Daily/Weekly
**Definition:** A filter applied to the universe selecting instruments meeting defined quantitative criteria — fundamental, technical, or combined.
**Key Attributes:** Screen Name, Filter Set (criteria and thresholds), Universe Applied To, Pass Count, Last Execution, Output Instrument List, Backtested Pass-Rate History
**Lifecycle:** Criteria Defined → Scheduled Execution → Results Generated → Analyst Review → Possible Promotion to Watchlist/Decision

---

#### H.11 — SCANNER

**Class:** Intelligence — Real-Time Automated Filter | **Parent:** Universe, Live Market Data | **Importance:** High | **Change Frequency:** Intraday
**Definition:** A real-time or near-real-time automated process continuously filtering instruments meeting technical or price-action criteria during market hours.
**Key Attributes:** Scanner Name, Criteria (breakout/volume/momentum/pattern), Execution Frequency, Output Count, Alert Integration, Regime Filter, False Positive Rate
**Lifecycle:** Defined → Running (continuous or scheduled) → Results Generated → Alert Triggered → Review Cycle

---

#### H.12 — FEATURE

**Class:** Intelligence — Model Input Variable | **Parent:** Data Pipeline, Model | **Importance:** High | **Change Frequency:** Daily/Intraday
**Definition:** A computed, normalized input variable representing a specific measurable characteristic of an instrument, used by a model for classification, scoring, or prediction.
**Key Attributes:** Feature Name, Formula/Derivation Logic, Normalization Method (z-score/percentile/raw), Source Data, Valid Universe, Importance Rank (in specific model), Regime Stability
**Lifecycle:** Defined → Computed → Fed to Model → Periodically Re-evaluated for Predictive Power → Retained or Deprecated

---

#### H.13 — RANKING

**Class:** Intelligence — Ordered Output | **Parent:** Universe, Score, Factor | **Importance:** High | **Change Frequency:** Daily/Weekly
**Definition:** An ordered list of instruments sorted by a composite score, factor value, or multi-criteria evaluation — expressing relative attractiveness.
**Key Attributes:** Ranking Name, Scoring Basis, Universe Covered, Date, Total Ranked, Tier Classification (Tier 1 Top 10% / Tier 2 / Tier 3 Bottom 10%), Regime Adjustment Applied
**Lifecycle:** Score Computed → Instruments Sorted → Ranking Published → Used in Opportunity Identification → Next Period Ranking Replaces

---

#### H.14 — NOTIFICATION

**Class:** Intelligence — Communication Event | **Parent:** Alert, System | **Importance:** Medium | **Change Frequency:** Event
**Definition:** An alert that has been formatted and dispatched to a defined delivery channel (Telegram, email, dashboard widget).
**Key Attributes:** Alert Reference, Channel (Telegram/Dashboard/Email/SMS), Dispatched At, Delivery Status, Message Content, Priority Level, Acknowledgement Status, Retry Count
**Lifecycle:** Alert Triggered → Notification Formatted → Dispatched → Delivered (or Failed) → Acknowledged or Escalated

---
### GROUP I — KNOWLEDGE & REASONING ENTITIES

#### I.1 — HYPOTHESIS

| Attribute | Value |
|---|---|
| **Class** | Knowledge — Reasoning |
| **Parent** | Observation, Evidence |
| **Importance** | Critical |
| **Change Frequency** | Event (creation/revision) |

**Definition:** A precise, falsifiable, directional statement about an entity's expected future behavior, derived from assembled evidence.
**Key Attributes:** Entity, Direction (Bullish/Bearish), Expected Outcome, Time Horizon, Supporting Evidence Count, Contradicting Evidence Count, Conviction Score, Falsification Conditions, Creation Date, Last Reviewed, Status (Active/Invalidated/Confirmed/Expired)
**Lifecycle:** Formed → Evidence Assembled → Conviction Assessed → Acted Upon (or Rejected) → Outcome Recorded → Learning Applied
**State Changes:** Tentative → Conviction-backed → Decision-ready; Active → Invalidated (falsification met); Expired → Archived

---

#### I.2 — EVIDENCE ITEM

**Class:** Knowledge — Reasoning Input | **Parent:** Hypothesis | **Importance:** Critical | **Change Frequency:** Event
**Definition:** A contextualized, weighted observation deemed relevant to a specific hypothesis.
**Key Attributes:** Hypothesis Reference, Evidence Type, Source, Observation Referenced, Direction (supports/contradicts), Weight, Independence Assessment, Timestamp, Expiry

---

#### I.3 — REASONING CHAIN

| Attribute | Value |
|---|---|
| **Class** | Knowledge — Reasoning Process |
| **Parent** | Hypothesis |
| **Importance** | Critical |
| **Change Frequency** | Event |

**Definition:** The structured logical argument connecting assembled evidence through explicit steps to a conviction conclusion.
**Key Attributes:** Hypothesis, Evidence Inventory (ordered), Reasoning Steps, Conflict Resolutions, Regime Validity Check, Risk Assessment, Conviction Score, Falsification Conditions, Timestamp (locked at decision)
**Lifecycle:** Created for Hypothesis → Completed → Locked (at decision) → Outcome Reviewed → Learning Extracted
**Key Principle:** The reasoning chain is IMMUTABLE once a decision is made from it. Post-hoc revision corrupts learning.

---

#### I.4 — CONVICTION

**Class:** Knowledge — Assessment | **Parent:** Reasoning Chain | **Importance:** Critical | **Change Frequency:** Daily
**Definition:** A quantified measure of confidence in a directional hypothesis, produced by structured aggregation of independent evidence.
**Key Attributes:** Entity, Direction, Score (numeric), Minimum Threshold (must exceed for decision), Evidence Count, Independent Evidence Count, Regime Alignment Score, Historical Base Rate, Date Assessed, Valid Until
**State Changes:** Low → Building → Threshold Met → Decision Triggered; High → Evidence Contradicted → Reduced → Invalidated

---

#### I.5 — KNOWLEDGE ITEM

**Class:** Knowledge — Durable Pattern | **Parent:** Learning System | **Importance:** Critical | **Change Frequency:** Slow/Learned
**Definition:** A durable, validated pattern about an entity or relationship confirmed across multiple observations.
**Key Attributes:** Knowledge Type, Entity/Relationship, Pattern Description, Conditions of Validity, Confidence Score, Confirming Observations Count, Regime Scope, Creation Date, Last Validated, Reliability Score
**Examples:** "TATASTEEL leads sector recovery by 2 sessions (72% reliability, 30+ observations, trending regime)" | "IVR > 80 in NIFTY preceded rallies 64% over 12M horizon (47 observations)"

---

#### I.6 — MODEL

**Class:** Computational — Knowledge | **Parent:** System | **Importance:** High | **Change Frequency:** Event (retrain)
**Definition:** A mathematical or logical construct taking defined inputs and producing defined outputs representing entity behavior or market dynamics.
**Key Attributes:** Name, Type, Inputs, Outputs, Training Data, Out-of-Sample Performance, Last Updated, Regime Validity, Known Failure Modes, Confidence Bounds
**Examples:** Regime Classification Model, Earnings Surprise Predictor, Relative Strength Ranking Model, Options Pricing Model

---

#### I.7 — STRATEGY

**Class:** Computational — Decision Framework | **Parent:** System | **Importance:** High | **Change Frequency:** Slow
**Definition:** A decision-making framework specifying conditions for opportunity identification, entry, sizing, management, and exit.
**Key Attributes:** Strategy Name, Underlying Logic, Entry Conditions, Exit Conditions, Position Sizing Rule, Regime Suitability, Historical Performance (Win Rate, Expectancy, Sharpe, Max Drawdown), Current Status
**Note per Architecture:** Strategies are ONE possible evidence source — not the architectural core.

---

#### I.8 — BACKTEST

**Class:** Computational — Simulation | **Parent:** Strategy | **Importance:** High
**Definition:** A simulation of a strategy applied to historical data to assess past performance.
**Key Attributes:** Strategy, Data Period, Parameters, Total Trades, Win Rate, Avg Win/Loss, Max Drawdown, Sharpe, CAGR, Walk-Forward Result, OOS Period, Methodology Assumptions, Data Snooping Risk

---

#### I.9 — LEARNING RECORD

**Class:** Knowledge — Learning | **Parent:** Learning System | **Importance:** Critical | **Change Frequency:** Event
**Definition:** A documented outcome of the learning process — a verified revision to a knowledge item, model weight, or evidence reliability score.
**Key Attributes:** Type of Learning, Entity, What Changed, Why It Changed, Supporting Data, Previous Value, New Value, Date, Confidence in Revision

---

#### I.10 — PREDICTION

**Class:** Knowledge — Predictive | **Parent:** Model/Reasoning Chain | **Importance:** High | **Change Frequency:** Daily
**Definition:** A probabilistic, timestamped forward-looking statement about an entity's expected future state.
**Key Attributes:** Entity, Predicted State, Time Horizon, Probability, Confidence Interval, Basis, Creation Date, Expiry, Outcome (after horizon)

---

#### I.11 — OUTCOME RECORD

**Class:** Knowledge — Learning Input | **Parent:** Decision | **Importance:** Critical | **Change Frequency:** Event (position close)
**Definition:** The documented actual result of a decision compared against what was predicted at decision time.
**Key Attributes:** Decision Referenced, Predicted Outcome, Actual Outcome, Time to Outcome, P&L, R-Multiple, Was Reasoning Correct, Contributing Factors to Deviation, Learning Extracted

---

### GROUP J — DECISION ENTITIES

#### J.1 — DECISION

| Attribute | Value |
|---|---|
| **Class** | Decision — Action |
| **Parent** | Conviction, Reasoning Chain |
| **Children** | Orders, Trades, Position |
| **Importance** | Critical |
| **Change Frequency** | Event |

**Definition:** A fully rationalized, conviction-backed commitment to a specific investment action, bounded by explicit risk parameters, with documented rationale.
**Key Attributes:** Decision ID, Entity, Direction, Conviction Level at Decision, Entry Logic, Entry Price/Window, Stop Loss, Target, Position Size, Time Horizon, Max Capital Risk, Rationale (reasoning chain reference), Decision Date, Regime at Decision, Falsification Conditions, Status (Pending/Active/Completed), Outcome Reference
**Lifecycle:** Formed → Validated → Approved → Entry Executed → Position Active → Exit Triggered → Closed → Outcome Recorded → Learning Applied
**State Changes:** Pending Entry → Entry Triggered → Active Position → Stop Triggered (loss) / Target Reached (profit) / Time-based Exit / Thesis Invalidated → Completed
**Key Principle:** Every decision carries its complete reasoning chain, immutably locked at decision time.

---

#### J.2 — RECOMMENDATION

**Class:** Decision — Pre-Decision | **Parent:** Conviction, Intelligence Layer | **Importance:** High
**Definition:** A system-generated directional suggestion carrying conviction assessment but not yet committed as a decision.
**Key Attributes:** Instrument, Direction, Conviction Level, Evidence Summary, Entry Zone, Stop Zone, Target Zone, Valid Window, Priority, Status (Active/Expired/Converted to Decision)

---

#### J.3 — CONSTRAINT

**Class:** Decision — Governance Rule | **Parent:** Portfolio, Risk Framework | **Importance:** Critical
**Definition:** A rule limiting or preventing specific decision outcomes — position limits, sector limits, drawdown triggers.
**Key Attributes:** Constraint Type, Parameter, Scope, Hard vs Soft (breach stops vs warns), Override Policy, Review Frequency
**Examples:** Max single position = 5% NAV; Max sector = 25%; Max portfolio beta = 1.2; Daily loss limit = 2%

---

### GROUP K — RISK ENTITIES

#### K.1 — RISK (Abstract Parent)

**Class:** Risk — Abstract | **Importance:** Critical | **Change Frequency:** Daily to Event

**Sub-Entities:**

| Risk Type | Definition | Primary Source |
|---|---|---|
| **Market Risk** | Adverse price movement | Market, Volatility |
| **Credit Risk** | Counterparty default | Issuer credit quality |
| **Liquidity Risk** | Cannot exit at acceptable price | Position size vs ADV |
| **Concentration Risk** | Excessive single-entity exposure | Portfolio composition |
| **Correlation Risk** | Diversification fails under stress | Correlation matrix |
| **Operational Risk** | System/process/execution failure | Internal operations |
| **Governance Risk** | Poor corporate governance of held company | Company entity state |
| **Regulatory Risk** | Regulation changes affecting instrument/system | Regulatory environment |
| **Tail Risk** | Extreme low-probability outcomes | Fat-tail distributions |
| **Model Risk** | Model assumptions incorrect | Model limitations |

---

#### K.2 — DRAWDOWN

**Class:** Risk — Measurement | **Parent:** Portfolio, Position | **Importance:** Critical
**Definition:** The peak-to-current decline in portfolio or position value from the highest prior value.
**Key Attributes:** Current Drawdown %, Max Historical Drawdown %, Duration in Drawdown, Recovery Required, Cause Attribution

---

#### K.3 — STOP LOSS

**Class:** Risk — Hard Limit | **Parent:** Position, Decision | **Importance:** Critical
**Definition:** A pre-defined price level at which a position is exited to limit loss.
**Key Attributes:** Instrument, Stop Level, Stop Type (fixed/trailing/time-based), Capital at Risk, Distance from Entry %, Relationship to Technical Level

---

### GROUP L — REFERENCE / STRUCTURAL ENTITIES

#### L.1 — SECTOR CLASSIFICATION

**Class:** Reference — Taxonomy | **Importance:** High | **Change Frequency:** Slow
**Definition:** A standardized taxonomy for grouping companies by economic activity.
**Examples:** GICS (Global Industry Classification Standard), NIC (National Industrial Classification), NSE Sectoral Classification

---

#### L.2 — COUNTRY

**Class:** Reference — Geographic/Political | **Importance:** High | **Change Frequency:** Slow
**Definition:** A sovereign geographic and political entity with defined laws, regulatory frameworks, and economic conditions.
**Key Attributes:** Country Name, ISO Code, GDP, Sovereign Rating, Currency, Major Exchange, FII Accessibility, Capital Controls

---

#### L.3 — FISCAL YEAR

**Class:** Reference — Temporal | **Importance:** High | **Change Frequency:** Annual (new year, same structure)
**Definition:** The 12-month accounting period used by a company or government for financial reporting.
**Key Attributes:** Entity, Start Month, End Month, FY Label (FY26 = April 2025 to March 2026), Quarter Definitions

---

#### L.4 — EXPIRY DATE

**Class:** Reference — Temporal | **Importance:** High | **Change Frequency:** Event
**Definition:** The date on which a derivatives contract ceases to exist and is settled.
**Key Attributes:** Date, Contract Type (Monthly/Weekly), Segment, Settlement Method

---

#### L.5 — AUDIT TRAIL

**Class:** Structural — Immutable Record | **Importance:** Critical | **Change Frequency:** Append-only
**Definition:** An immutable, timestamped record of every material action taken by the system.
**Key Attributes:** Action Type, Timestamp, Entity Affected, Actor (human/AI), Before State, After State, Rationale Reference
**Key Principle:** Audit trails are append-only and immutable. They cannot be deleted or modified.

---

#### L.6 — JOURNAL ENTRY

**Class:** Structural — Operational Record | **Importance:** High | **Change Frequency:** Event
**Definition:** A human-readable record of a significant event, observation, or decision in the system's operational log.
**Key Attributes:** Date, Entry Type (trade/observation/decision/review), Content, Author, Related Entities, Tags

---


#### I.12 — OBSERVATION RECORD

**Class:** Knowledge — Raw Factual Input | **Parent:** Entity (observed), System | **Importance:** Critical | **Change Frequency:** Continuous
**Definition:** A timestamped, attributed, immutable capture of an entity's state, behavior, or measurement at a specific point in time.
**Key Attributes:** Record ID, Entity Observed, Observation Type (price/volume/event/news/fundamental/technical), Value or State Captured, Timestamp, Data Source, Confidence Score, Persistence Type (temporary/permanent), Tags, Attribution
**Lifecycle:** Created (on detection or data arrival) → Retained in record layer → Referenced as Evidence → Archived permanently
**Key Principle:** Observation records are immutable once created. They form the raw factual bedrock supporting all higher reasoning. The system cannot "unobserve" something that has already been observed.

---

#### I.13 — SIMULATION

**Class:** Computational — Scenario Analysis | **Parent:** Model, Strategy, Risk Framework | **Importance:** High | **Change Frequency:** Event (on-demand or scheduled)
**Definition:** A computational run of a strategy, portfolio, or model over synthetic, historical, or forward-projected scenarios to assess probabilistic outcomes.
**Key Attributes:** Simulation Name, Type (Monte Carlo/Historical/Stress/Walk-Forward), Input Parameters, Scenario Set Size, Run Count, Results Distribution, Confidence Interval, Date, Runtime
**Lifecycle:** Scenario Defined → Parameters Set → Executed → Results Distribution Produced → Key Statistics Extracted → Analyzed → Archived
**Types:** Monte Carlo (random path generation), Historical Simulation (replay actual history), Stress Test Simulation (extreme scenario), Walk-Forward Test (sequential out-of-sample)

---

#### I.14 — PERFORMANCE RECORD

**Class:** Knowledge — Historical Achievement | **Parent:** Portfolio, Strategy | **Importance:** Critical | **Change Frequency:** Daily (update), Event (period-end lock)
**Definition:** A structured, immutable historical record of returns, risk metrics, drawdowns, and attribution for a portfolio or strategy over a defined time period.
**Key Attributes:** Entity (portfolio/strategy name), Period (start/end date), Total Return, Benchmark Return, Alpha, Sharpe Ratio, Sortino Ratio, Max Drawdown, Win Rate, Average Win, Average Loss, Trade Count, Attribution by Strategy/Sector, Benchmark Used, Notes
**Lifecycle:** Period starts → Updated daily during period → Period-end record locked (immutable) → Archived → Feeds future performance comparison
**Key Principle:** Period-end Performance Records are immutable once locked. They cannot be revised retroactively.

---

#### J.4 — OBJECTIVE

**Class:** Decision — Intent Statement | **Parent:** Portfolio Owner | **Importance:** High | **Change Frequency:** Slow (quarterly/annual review)
**Definition:** A formally stated investment goal that all decisions and the portfolio construction process must collectively serve.
**Key Attributes:** Objective Statement (precise text), Time Horizon, Absolute Return Target (CAGR %), Risk Tolerance (max drawdown %), Benchmark (if relative), Liquidity Requirement, Priority Rank (if multiple objectives), Review Frequency, Owner
**Lifecycle:** Formally Stated → Active (governs all decisions) → Reviewed (periodic) → Revised / Achieved / Superseded
**Examples:** "Generate 18% CAGR over 3 years with maximum 20% drawdown; outperform NIFTY 50 by 5% annually"

---

#### J.5 — TARGET LEVEL

**Class:** Decision — Profit Reference Point | **Parent:** Decision, Position | **Importance:** High | **Change Frequency:** Event (revision on thesis change)
**Definition:** The pre-defined price level at which a position is intended to be partially or fully exited to realize the anticipated profit.
**Key Attributes:** Instrument, Target Price, Basis for Target (technical resistance/fundamental valuation/R-multiple), Time Validity, Distance from Entry (%), Risk-Reward Ratio vs Stop Loss, Status (Active/Hit/Revised/Cancelled)
**Lifecycle:** Set at Decision → Active (monitors position) → Hit (exit trigger) / Revised (new evidence) / Cancelled (thesis invalidated)
**Note:** Targets are guides, not guarantees. They should be revised when new fundamental evidence changes the fair value estimate.

---

#### J.6 — POSITION SIZING RULE

**Class:** Decision — Capital Allocation Governance | **Parent:** Portfolio, Risk Framework | **Importance:** Critical | **Change Frequency:** Slow (framework) / Per-decision (output)
**Definition:** A defined formula or rule set specifying the exact capital allocation for a position based on conviction level, instrument volatility, and portfolio context.
**Key Attributes:** Method (fixed fraction/volatility-scaled/Kelly/conviction-scaled), Base Size (% of NAV), Maximum Size Limit (% of NAV), Conviction Scaling Factor, Volatility Adjustment Parameter, Correlation Penalty, Portfolio Utilization Factor
**Lifecycle:** Method Defined → Applied per Decision → Position Size Output Calculated → Backtested → Method Revised
**Why Critical:** The wrong sizing rule can make a profitable strategy unprofitable (over-sizing = ruin; under-sizing = opportunity waste).

---

#### K.4 — STRESS TEST

**Class:** Risk — Scenario Analysis | **Parent:** Portfolio, Risk Framework | **Importance:** High | **Change Frequency:** Weekly/Event
**Definition:** A scenario-based analysis applying extreme hypothetical conditions to the current portfolio to assess maximum possible loss under specific market stress events.
**Key Attributes:** Scenario Name, Asset Class Move Assumptions, Correlation Matrix Under Stress, Estimated Portfolio Loss (₹ and %), % of NAV at Risk, Time to Recover Estimate, Limit Breach (Yes/No), Recommended Action
**Lifecycle:** Scenarios Defined → Applied to Current Portfolio → Loss Distribution Calculated → Reviewed by Risk System → Action Triggered if Needed
**Examples of Scenarios:** 2008-style crash (equity -50%), 2020 COVID (equity -35% in 2 weeks), 1994 bond rout (+300bps in 3 months), RBI emergency rate hike (+200bps), INR devaluation (-15%), crude oil shock (+100%)

---

#### K.5 — VAR ESTIMATE

**Class:** Risk — Quantitative Probability Measure | **Parent:** Portfolio | **Importance:** High | **Change Frequency:** Daily
**Definition:** A statistical estimate of the maximum expected loss from the portfolio over a defined horizon at a specified confidence level.
**Key Attributes:** Portfolio Reference, Confidence Level (95% or 99%), Time Horizon (1-day or 10-day), Calculation Method (historical/parametric/Monte Carlo), Current VaR Value, VaR Limit, Historical Breach Count, Conditional VaR (CVaR/Expected Shortfall)
**Lifecycle:** Computed daily using current portfolio → Compared to VaR limit → Breach triggers risk review → Methodology reviewed quarterly
**Critical Limitation:** VaR systematically underestimates tail risk in non-normal return distributions and during crisis periods. Always supplement with CVaR (Expected Shortfall) and scenario-based stress tests. VaR is a minimum loss threshold, not the worst case.

---

#### L.7 — CURRENCY REFERENCE

**Class:** Reference — Financial Standard | **Parent:** Central Bank, FX Market | **Importance:** High | **Change Frequency:** Continuous (rates), Static (designation)
**Definition:** The official designation, ISO standard code, and exchange rate context for a currency used in cross-border financial transactions and reporting.
**Key Attributes:** Currency Name, ISO 4217 Code, Issuing Country/Region, Central Bank, Exchange Rate Mechanism (free float/managed/pegged), Current Rate vs USD, 1Y Volatility, Convertibility Status, Capital Control Restrictions
**Lifecycle:** Established by sovereign authority → Active legal tender → Possible redenomination, replacement by CBDC, or discontinuation (rare)
**Examples:** INR (₹, ISO: INR), USD (ISO: USD), EUR (ISO: EUR), JPY (ISO: JPY), GBP (ISO: GBP), CNY (ISO: CNY)

---

#### L.8 — DATE

**Class:** Reference — Temporal Anchor | **Parent:** Calendar | **Importance:** High | **Change Frequency:** Daily (new date)
**Definition:** A specific calendar day serving as a temporal anchor for financial records, event scheduling, and analytics.
**Key Attributes:** Date (YYYY-MM-DD format), Day of Week, Calendar Year, Fiscal Quarter (per entity's fiscal year), Trading Day Flag, Exchange Holiday Flag, Expiry Date Flag, Economic Event Flag, Settlement Day Flag
**Lifecycle:** Exists as calendar reference → Flagged with market and economic events → Permanently archived
**Critical Distinction:** Calendar Date ≠ Trading Day. Settlement, expiry, and event timing must reference the correct type. "Next 5 trading days" and "next 5 calendar days" are different.

---

#### L.9 — TRADING DAY

**Class:** Reference — Market-Specific Temporal | **Parent:** Exchange, Trading Calendar | **Importance:** High | **Change Frequency:** Daily
**Definition:** A calendar day on which a specific exchange is open for trading; the base unit of market time.
**Key Attributes:** Date, Exchange, Session Hours (Open/Close), Market Status (Normal/Holiday/Half-Day), Expiry Day Flag (monthly/weekly), Settlement Day Flag (T+1 from which trade), Special Announcement Flag
**Lifecycle:** Scheduled via Trading Calendar → Active on that date → Session archived with full statistics
**Examples:** Jan 26 = NSE Holiday (Republic Day); Last Thursday of month = NSE Monthly F&O Expiry; Every Thursday = NSE Weekly Expiry

---

#### L.10 — REGULATORY FILING

**Class:** Reference — Compliance and Disclosure Record | **Parent:** Company, Regulator | **Importance:** High | **Change Frequency:** Event
**Definition:** A formal document submitted to a regulatory authority by a company or market participant as required by statute or regulation.
**Key Attributes:** Filing Type, Submitting Entity, Regulatory Authority (SEBI/MCA/NSE/BSE), Filing Date, Regulatory Deadline, Is Material Disclosure?, Content Summary, Reference Number, Public Availability
**Lifecycle:** Mandatory trigger event occurs (results/board meeting/shareholding change) → Document prepared → Filed before deadline → Reviewed by Regulator → Published on exchange/MCA portal → Archived permanently
**Examples:** Quarterly shareholding pattern (SEBI), board meeting outcome, SEBI insider trading disclosure, Annual Report filing, DRHP (IPO), NCLT filings (restructuring)

---

#### L.11 — CONFIGURATION

**Class:** Reference — System Parameter | **Parent:** System | **Importance:** High | **Change Frequency:** Event (deliberate human change)
**Definition:** A named, versioned parameter or parameter set that governs system behavior, analytical thresholds, and operational rules.
**Key Attributes:** Parameter Name, Current Value, Default Value, Valid Range, Unit, Last Modified Date, Modified By (human/automated), Version Number, Impact Description, Requires System Restart?, Rollback Procedure
**Lifecycle:** Parameter Defined → Deployed → Active → Revised (with full reason logged and approved) → Old Version Archived
**Examples:** conviction_threshold = 6.5; max_position_pct = 0.05; vix_kill_switch = 45; regime_detection_window_days = 20; daily_loss_limit_pct = 0.02; scan_interval_seconds = 30

---
## PART IV — ENTITY CLASSIFICATION TAXONOMY

Every entity is classified along multiple dimensions simultaneously.

| Classification | Definition | Examples |
|---|---|---|
| **Physical** | Has real-world counterpart beyond the financial system | Company, Exchange (building), Commodity |
| **Financial** | Exists as a financial instrument or contract | Equity, Bond, Futures, Options, ETF |
| **Market** | Provides market structure or price discovery | Market, Exchange, Index, Trading Session |
| **Economic** | Represents macroeconomic conditions | GDP, Inflation, Interest Rate, Yield Curve |
| **Organizational** | A human institution with legal existence | Company, Fund House, Regulator, Central Bank, Broker |
| **Temporal** | Defined by time | Trading Session, Expiry Date, Fiscal Year, Trading Day |
| **Event** | A discrete occurrence changing state of other entities | Corporate Action, Earnings Release, MPC Meeting, Election |
| **Financial Statement** | Formal financial disclosure | P&L, Balance Sheet, Cash Flow, Annual Report |
| **Participant Activity** | Created in the act of market engagement | Portfolio, Position, Trade, Order |
| **Intelligence** | Produced by the analytical layer | Signal, Indicator, Pattern, Score, Ranking, Regime |
| **Knowledge** | Durable validated patterns and understanding | Knowledge Item, Model, Strategy, Learned Pattern |
| **Reasoning** | Cognitive constructs in reasoning process | Hypothesis, Evidence Item, Reasoning Chain, Conviction |
| **Decision** | Entities governing or recording action | Decision, Recommendation, Constraint, Objective |
| **Risk** | Quantified potential for adverse outcomes | Market Risk, Drawdown, Stop Loss, VaR |
| **Derived** | Computed from other entities | Indicator, Factor Score, Composite Score |
| **Learning** | Generated by the learning process | Learning Record, Outcome Record |
| **Predictive** | Forward-looking probabilistic statements | Prediction, Forecast, Probability Estimate |
| **Reference** | Stable classification or reference data | Sector Classification, Country, Currency, Fiscal Year |
| **Structural** | Defines architecture of the investment universe | Universe, Watchlist, Audit Trail, Configuration |
| **Behavioral** | Describes observed patterns of behavior | Pattern, Behavioral Model, Anomaly Record |
| **Computational** | Internal system entities | Model, Rule, Parameter, Configuration |
| **Human** | Individual human participants | Retail Investor, Analyst, Fund Manager |
| **Institutional** | Organized institutional participants | FII, DII, Broker, Fund House, Rating Agency |

---


---

### Entity-to-Classification Mapping Matrix

*Every entity mapped to its primary classification(s). Multi-classified entities reflect genuine dual nature.*

| Entity | Primary Classifications |
|---|---|
| **GROUP A — MARKET INFRASTRUCTURE** | |
| Market | Market, Structural, Reference |
| Exchange | Market, Organizational, Physical |
| Trading Session | Market, Temporal |
| Market Segment | Market, Structural |
| Index | Market, Derived, Reference |
| Benchmark | Market, Derived, Reference |
| Trading Calendar | Temporal, Reference |
| Settlement Cycle | Market, Structural, Reference |
| Circuit Breaker | Market, Safety Mechanism |
| Clearing Corporation | Market, Organizational |
| Depository | Market, Organizational |
| **GROUP B — FINANCIAL INSTRUMENTS** | |
| Equity / Stock | Financial, Market |
| Futures Contract | Financial, Derivative, Temporal |
| Options Contract | Financial, Derivative, Temporal |
| Option Chain | Financial, Derived, Market |
| ETF | Financial, Market |
| Government Bond | Financial, Sovereign |
| Corporate Bond | Financial |
| Mutual Fund | Financial, Collective |
| Currency Pair | Financial, Market |
| Commodity Instrument | Financial, Derivative |
| Commercial Paper | Financial, Money Market |
| Treasury Bill | Financial, Sovereign, Money Market |
| Warrant | Financial, Derivative |
| Convertible Bond | Financial, Hybrid |
| Depositary Receipt | Financial, Cross-Border |
| Right (Entitlement) | Financial, Temporal |
| Structured Product | Financial, Derived, Complex |
| **GROUP C — ECONOMIC & MACRO** | |
| Economy | Economic, Structural |
| Macro Variable | Economic, Data Point |
| Interest Rate | Economic, Financial |
| Yield Curve | Economic, Derived |
| Sector | Economic, Structural, Reference |
| Industry | Economic, Structural, Reference |
| Theme | Economic, Cross-Sector |
| **GROUP D — ORGANIZATIONAL** | |
| Listed Company | Organizational, Physical, Financial |
| Unlisted Company | Organizational, Physical |
| Promoter Group | Organizational, Human |
| Subsidiary | Organizational, Financial |
| Government | Organizational, Sovereign |
| Regulator | Organizational, Institutional |
| Central Bank | Organizational, Institutional |
| Fund House | Organizational, Institutional |
| Mutual Fund (entity) | Organizational, Collective |
| Hedge Fund / AIF | Organizational, Institutional |
| Insurance Company | Organizational, Institutional |
| Pension Fund | Organizational, Institutional |
| FII | Organizational, Institutional |
| DII | Organizational, Institutional |
| Retail Investor | Human |
| Broker | Organizational, Market |
| Market Maker | Organizational, Market |
| Investment Bank | Organizational, Institutional |
| Rating Agency | Organizational, Institutional |
| Research Firm | Organizational, Institutional |
| News Agency | Organizational, Information |
| Index Provider | Organizational, Institutional |
| **GROUP E — EVENTS** | |
| Corporate Action (parent) | Event, Financial |
| Dividend | Event, Financial |
| Stock Split | Event, Financial, Structural |
| Bonus Issue | Event, Financial |
| Rights Issue | Event, Financial |
| Buyback | Event, Financial |
| Merger / Acquisition | Event, Financial, Structural |
| Demerger | Event, Financial, Structural |
| IPO | Event, Financial |
| Open Offer | Event, Financial |
| Delisting | Event, Financial, Structural |
| Earnings Event | Event, Financial |
| Monetary Policy Event | Event, Economic |
| Budget Event | Event, Economic, Sovereign |
| Index Rebalancing Event | Event, Market |
| Geopolitical Event | Event, Economic |
| News Event | Event, Information |
| **GROUP F — FINANCIAL STATEMENTS** | |
| Income Statement | Financial Statement, Disclosure |
| Balance Sheet | Financial Statement, Disclosure |
| Cash Flow Statement | Financial Statement, Disclosure |
| Notes to Accounts | Financial Statement, Disclosure |
| Segment Report | Financial Statement, Disclosure |
| Annual Report | Financial Statement, Disclosure |
| Auditor Report | Financial Statement, Disclosure |
| MD&A | Financial Statement, Disclosure |
| **GROUP G — PARTICIPANT ACTIVITY** | |
| Portfolio | Participant Activity, Financial |
| Position | Participant Activity, Financial |
| Trade | Participant Activity, Financial |
| Order | Participant Activity, Financial |
| Execution | Participant Activity, Financial |
| Transaction | Participant Activity, Financial |
| Holding | Participant Activity, Financial |
| Block Deal | Participant Activity, Financial |
| Bulk Deal | Participant Activity, Disclosure |
| Fund Flow Record | Participant Activity, Aggregate |
| **GROUP H — MARKET INTELLIGENCE** | |
| Universe | Intelligence, Structural |
| Watchlist | Intelligence, Structural |
| Screen | Intelligence, Filter |
| Scanner | Intelligence, Filter, Computational |
| Signal | Intelligence, Derived |
| Indicator | Intelligence, Derived, Computational |
| Pattern | Intelligence, Behavioral, Derived |
| Feature | Intelligence, Derived, Computational |
| Factor | Intelligence, Derived |
| Score | Intelligence, Derived, Composite |
| Ranking | Intelligence, Derived, Ordered |
| Alert | Intelligence, Event |
| Notification | Intelligence, Communication |
| Market Regime | Intelligence, Derived, Structural |
| **GROUP I — KNOWLEDGE & REASONING** | |
| Hypothesis | Reasoning, Knowledge |
| Observation Record | Knowledge, Immutable |
| Evidence Item | Reasoning, Derived |
| Reasoning Chain | Reasoning, Knowledge |
| Conviction | Reasoning, Derived |
| Knowledge Item | Knowledge, Durable |
| Model | Computational, Knowledge |
| Strategy | Computational, Decision |
| Backtest | Computational, Historical |
| Simulation | Computational, Predictive |
| Learning Record | Learning, Immutable |
| Prediction | Predictive, Probabilistic |
| Outcome Record | Learning, Immutable |
| Performance Record | Knowledge, Historical |
| **GROUP J — DECISION** | |
| Decision | Decision, Action |
| Recommendation | Decision, Pre-Action |
| Constraint | Decision, Governance |
| Objective | Decision, Intent |
| Target Level | Decision, Reference |
| Position Sizing Rule | Decision, Governance |
| **GROUP K — RISK** | |
| Risk (abstract) | Risk |
| Drawdown | Risk, Measurement |
| Stop Loss | Risk, Hard Limit |
| Stress Test | Risk, Analytical |
| VaR Estimate | Risk, Quantitative |
| **GROUP L — REFERENCE / STRUCTURAL** | |
| Sector Classification | Reference, Taxonomy |
| Country | Reference, Geographic |
| Currency Reference | Reference, Financial |
| Date | Reference, Temporal |
| Fiscal Year | Reference, Temporal |
| Trading Day | Reference, Temporal, Market |
| Expiry Date | Reference, Temporal, Financial |
| Regulatory Filing | Reference, Compliance, Immutable |
| Audit Trail | Structural, Immutable |
| Journal Entry | Structural, Record |
| Configuration | Reference, System |

---
## PART V — ENTITY LIFECYCLE MODELS

### Company Lifecycle

```
INCORPORATED (private)
        ↓ [founder capital, organic growth]
PRIVATE OPERATING
        ↓ [decision to access public capital]
PRE-IPO / DRHP FILED
        ↓ [SEBI approval, anchor investors, public offer]
NEWLY LISTED
        ↓ [price discovery, institutional analysis begins]
GROWTH PHASE (revenue expanding, market share gaining)
        ↓ [competition, margin pressure, or macro shift]
MATURITY PHASE (stable revenues, dividend paying, capital return)
        ↓ [disruption, regulatory change, or management deterioration]
DECLINE PHASE (revenue declining, margins shrinking, debt rising)
        ↓ [multiple possible paths]
        ├── RESTRUCTURING (management change, strategic pivot)
        │       ↓ [successful pivot]
        │   RECOVERY → back to Growth/Maturity
        │
        ├── ACQUISITION TARGET (strategic/financial buyer)
        │       ↓ [open offer, delisting]
        │   ABSORBED INTO ACQUIRER
        │
        ├── MERGER (with comparable peer)
        │       ↓ [scheme of arrangement, court approval]
        │   MERGED ENTITY (new or surviving company)
        │
        ├── INSOLVENCY (NCLT filing, IBC process)
        │       ↓ [resolution or liquidation]
        │   RESOLVED (new owner) or LIQUIDATED
        │
        └── VOLUNTARY DELISTING (promoter buyout)
                ↓
            PRIVATE COMPANY AGAIN
```

### Equity Instrument Lifecycle

```
UNLISTED (private company shares)
        ↓ [IPO]
NEWLY LISTED (price discovery period)
        ↓
ACTIVELY TRADED
        ↓ [sufficient liquidity]
INDEX CONSTITUENT + F&O ELIGIBLE (mature liquid stock)
        ↓ [various exit paths]
        ├── SUSPENDED (regulatory/exchange action)
        │       ↓ [reinstatement or permanent suspension]
        │   REINSTATED or PERMANENTLY SUSPENDED
        │
        ├── DELISTED (voluntary/involuntary)
        │
        ├── MERGED (absorbed into acquirer)
        │
        └── ADJUSTED (split/bonus — continues as modified instrument)
```

### Derivatives Contract Lifecycle

```
CONTRACT CREATED (Exchange defines specifications)
        ↓
FAR MONTH (low activity, OI building slowly)
        ↓
MID MONTH (moderate activity, relative to near)
        ↓
NEAR MONTH (peak activity, options expiry approaching)
        ↓ [3 days before expiry — rollover period]
ROLLOVER PERIOD (OI transfers from near to mid month)
        ↓ [expiry day]
SETTLEMENT DAY (final settlement at closing price)
        ↓
CONTRACT EXPIRED
```

### Position Lifecycle

```
DECISION FORMED (conviction ≥ threshold)
        ↓ [entry conditions met]
ORDER PLACED
        ↓ [filled]
POSITION OPEN (entry phase)
        ↓ [monitoring begins]
POSITION ACTIVE (stop + target set, monitoring daily)
        ↓ [three primary outcomes]
        ├── TARGET REACHED → EXIT (profit) → CLOSED WIN
        │
        ├── STOP LOSS HIT → EXIT (loss) → CLOSED LOSS
        │
        ├── STALE (time limit) → GOVERNANCE REVIEW → EXIT or CARRY
        │
        └── THESIS INVALIDATED → MANAGED EXIT → CLOSED
        ↓ [always]
POSITION CLOSED
        ↓
OUTCOME RECORDED (P&L, R-multiple, reasoning accuracy)
        ↓
LEARNING APPLIED (update knowledge, evidence weights)
        ↓
ARCHIVED
```

### Hypothesis Lifecycle

```
OBSERVATION (anomaly or opportunity detected)
        ↓
HYPOTHESIS FORMED (precise directional statement)
        ↓ [evidence gathering phase]
EVIDENCE ASSEMBLED (supporting + contradicting)
        ↓ [reasoning applied]
CONVICTION ASSESSED (scored vs threshold)
        ↓
        ├── CONVICTION INSUFFICIENT
        │       ↓ [monitor for new evidence]
        │   MONITORED → RE-EVALUATED (on evidence change)
        │
        ├── CONVICTION SUFFICIENT → DECISION RECOMMENDED
        │       ↓ [entry conditions met]
        │   DECISION EXECUTED → POSITION OPENED
        │
        └── FALSIFICATION CONDITION MET
                ↓
            HYPOTHESIS INVALIDATED
                ↓
            INVALIDATION RECORDED (learning: what evidence was wrong?)
```

### Earnings Event Lifecycle

```
QUARTER ENDS
        ↓ [max 45 days to report]
RESULTS DATE ANNOUNCED
        ↓ [analyst model updates, consensus estimate solidifies]
PRE-RESULTS PERIOD (IV expansion, analyst revisions, positioning)
        ↓ [results announcement]
RESULTS RELEASED (revenue, EBITDA, PAT, EPS vs estimates)
        ↓ [immediate price reaction]
POST-RESULTS GAP (price re-rates based on surprise magnitude)
        ↓ [analyst response]
ANALYST REVISIONS (estimate upgrades/downgrades, target changes)
        ↓ [institutional response]
INSTITUTIONAL REPOSITIONING (buying on beat, selling on miss)
        ↓
NEW KNOWLEDGE INTEGRATED (entity behavioral model updated)
        ↓ [next quarter begins]
CYCLE REPEATS
```

### Monetary Policy Event Lifecycle

```
MPC CALENDAR PUBLISHED (annual schedule released)
        ↓ [weeks before meeting]
MARKET EXPECTATIONS FORM (rate probabilities priced in bonds/OIS)
        ↓ [days before]
PRE-POLICY POSITIONING (bond yields, INR, rate-sensitive equities move)
        ↓ [meeting day]
POLICY DECISION ANNOUNCED (rate + stance + resolution statement)
        ↓ [immediate]
MARKET REACTION (bonds, equities, INR re-price relative to expectations)
        ↓ [2-3 hours later]
GOVERNOR PRESS CONFERENCE (nuance, forward guidance, Q&A)
        ↓ [days after]
ANALYST INTERPRETATION (sector implications, rate trajectory)
        ↓ [until next MPC]
NEW ECONOMIC DATA ARRIVES → NEXT EXPECTATIONS CYCLE BEGINS
```

---

## PART VI — ENTITY DEPENDENCY HIERARCHIES

### Primary Investment Chain

```
ECONOMY (macro context)
└── MARKET (structured exchange mechanism)
    └── EXCHANGE (institutional platform)
        ├── TRADING SESSION (daily time window)
        ├── MARKET SEGMENT (asset class division)
        └── INDEX (performance aggregate)
            └── EQUITY/STOCK (index constituent)

SECTOR (economic grouping)
└── INDUSTRY (specific sub-grouping)
    └── COMPANY (operating entity)
        ├── EQUITY/STOCK (listed instrument)
        │   ├── FUTURES CONTRACT (derivative)
        │   └── OPTION CHAIN
        │       └── OPTIONS CONTRACTS (all strikes & expiries)
        └── FINANCIAL STATEMENTS
            ├── INCOME STATEMENT
            ├── BALANCE SHEET
            └── CASH FLOW STATEMENT
```

### Portfolio Activity Chain

```
INVESTOR / PORTFOLIO OWNER
└── PORTFOLIO (capital pool)
    └── POSITION (instrument holding)
        ├── TRADE (transaction creating/modifying position)
        │   └── ORDER (instruction generating trade)
        │       └── DECISION (commitment generating order)
        │           └── REASONING CHAIN
        │               ├── HYPOTHESIS
        │               └── EVIDENCE ITEMS
        │                   └── OBSERVATION RECORDS
        │
        └── PERFORMANCE RECORD (outcome of position)
            └── LEARNING RECORD (system update from outcome)
                └── UPDATED KNOWLEDGE ITEM
```

### Knowledge Creation Chain

```
MARKET ENTITY (company/instrument/event)
└── OBSERVATION RECORD (timestamped capture)
    └── EVIDENCE ITEM (contextualized, weighted)
        └── HYPOTHESIS (directional claim)
            └── REASONING CHAIN (structured argument)
                └── CONVICTION (quantified confidence)
                    └── DECISION (action commitment)
                        └── POSITION (active trade)
                            └── OUTCOME RECORD
                                └── LEARNING RECORD
                                    └── KNOWLEDGE ITEM (updated)
                                        └── [feeds back to future Observations]
```

### Risk Governance Chain

```
MARKET RISK (macro, volatility regime)
├── POSITION RISK (individual instrument)
│   ├── STOP LOSS (hard risk limit per position)
│   └── TARGET (reward reference)
└── PORTFOLIO RISK
    ├── CONCENTRATION RISK (per-position + per-sector)
    ├── CORRELATION RISK (positions moving together)
    ├── DRAWDOWN (peak-to-current portfolio loss)
    └── CONSTRAINT (rule governing maximum risk)
        └── RISK GUARDIAN (final kill switch — external)
```

### Information Flow Chain

```
MACRO ENTITY (rate/inflation/GDP)
    ↓ [affects]
SECTOR ENTITY (competitive dynamics, input costs)
    ↓ [affects]
COMPANY ENTITY (margins, growth, competitive position)
    ↓ [reflected in]
STOCK/EQUITY ENTITY (price, volume, OI)
    ↓ [captured by]
OBSERVATION RECORD (timestamped, attributed)
    ↓ [transformed into]
EVIDENCE ITEM (contextualized, weighted)
    ↓ [aggregated into]
CONVICTION SCORE (via Reasoning Chain)
    ↓ [triggers]
DECISION ENTITY
    ↓ [executed as]
TRADE + POSITION
    ↓ [produces]
OUTCOME RECORD
    ↓ [feeds]
LEARNING RECORD
    ↓ [updates]
KNOWLEDGE ITEM (about Company/Sector/Market Entity)
    ↓ [improves future reasoning]
```

### Macro Transmission Chain

```
GLOBAL EVENT (Fed decision, geopolitical event, commodity spike)
    ↓
GLOBAL MARKET ENTITY (S&P 500, DXY, crude oil, gold)
    ↓
CURRENCY ENTITY (USD/INR moves)
    ↓ [parallel]
FUND FLOW ENTITY (FII equity/debt flows change)
    ↓
MARKET BREADTH ENTITY (advance-decline, sector rotation)
    ↓
SECTOR ENTITY (relative strength, rotation)
    ↓
COMPANY ENTITY (earnings impact, cost structure)
    ↓
EQUITY ENTITY (price re-rating)
```

---

## PART VII — ENTITY OWNERSHIP MAP

Ownership defines which entity is responsible for creating, maintaining, and retiring another entity.
Every entity is accounted for. `N/A` for Retired By means the record is permanent and immutable.

| Entity | Owned By | Created By | Retired By |
|---|---|---|---|
| **GROUP A — MARKET INFRASTRUCTURE** | | | |
| Market | Governed by SEBI/Government | Historical/statutory establishment | Not applicable (structural) |
| Exchange | Exchange shareholders, SEBI oversight | Regulatory licensing / demutualisation | Regulatory closure / Merger |
| Trading Session | Exchange | Exchange (automatic, daily) | Exchange (holiday declaration / circuit halt) |
| Market Segment | Exchange | Exchange / SEBI mandate | SEBI / Exchange restructuring |
| Index | Index Provider | Index Provider (design + launch) | Index Provider (discontinuation) |
| Benchmark | Market convention / Index Provider | Index Provider / Convention establishment | Replacement by new benchmark |
| Trading Calendar | Exchange | Exchange (annual publication) | Superseded by next year's calendar |
| Settlement Cycle | SEBI / Exchange | SEBI regulatory mandate | SEBI rule change |
| Circuit Breaker | SEBI / Exchange | SEBI mandate (SEBI circular) | SEBI rule revision |
| Clearing Corporation | Exchange / SEBI | Regulatory creation | Merger / Dissolution |
| Depository | SEBI | Regulatory creation (SEBI Act) | Merger / Dissolution |
| **GROUP B — FINANCIAL INSTRUMENTS** | | | |
| Equity / Stock | Company (issuer), shareholders | Company (IPO / listing) | Exchange (delisting / compulsory delisting) |
| Futures Contract | Exchange | Exchange (contract specification launch) | Exchange (at contract expiry) |
| Options Contract | Exchange | Exchange (series listing) | Exchange (expiry / exercise) |
| Option Chain | Exchange | Exchange (automatic on listing underlying) | Exchange (underlying delisting) |
| ETF | Fund House | Fund House (NFO, SEBI approval) | SEBI / Fund House (scheme wind-up) |
| Government Bond | Government of India | Government / RBI auction | Government (at maturity) |
| Corporate Bond | Company (issuer) | Company (issuance process) | Company (at maturity) / NCLT (default) |
| Mutual Fund | Fund House (AMC) | Fund House (NFO, SEBI approval) | SEBI / AMC (scheme wind-up) |
| Currency Pair | FX market / Central Bank convention | Central bank / historical convention | Convention change / CBDC introduction |
| Commodity Instrument | Exchange (MCX / NCDEX) | Exchange (contract launch) | Exchange (at expiry) |
| Commercial Paper | Issuing Company / NBFC | Company (issuance) | Company (at maturity / buyback) |
| Treasury Bill | Government of India | Government / RBI (weekly auction) | Government (at maturity) |
| Warrant | Company (issuer) | Company (corporate action) | Company (expiry / exercise) |
| Convertible Bond | Company (issuer) | Company (issuance) | Company (conversion to equity / maturity) |
| Depositary Receipt | Custodian Bank / Issuer | Issuing company + custodian arrangement | Cancellation (converted to underlying) |
| Right (Entitlement) | Company (issuer) | Company (rights issue announcement) | Company (subscription deadline) |
| Structured Product | Issuing institution | Investment bank / arranger | Issuer (maturity / call / default) |
| **GROUP C — ECONOMIC & MACRO** | | | |
| Economy | Self-governing (sovereign) | Historical political / economic formation | Not applicable |
| Macro Variable | Statistics Authority / Central Bank | Government agency mandate | Methodology discontinuation |
| Interest Rate | Central Bank (policy) / Market (market rates) | Central bank mandate / bond market activity | Policy change / Market evolution |
| Yield Curve | Bond Market | Daily calculation by market participants | N/A (recalculated daily, historical archived) |
| Sector | Index Provider / Classification Standard | External classification authority | Reclassification by standard body |
| Industry | Classification Standard | External classification authority | Reclassification |
| Theme | Research community / Analyst consensus | Market narrative formation | Theme fading / contradicting evidence |
| **GROUP D — ORGANIZATIONAL** | | | |
| Listed Company | Shareholders (public + promoter) / Board | Founders (incorporation) + IPO | Delisting / Liquidation / Merger (absorbed) |
| Unlisted Company | Shareholders / Board | Founders (incorporation) | IPO / Acquisition / Winding-up |
| Promoter Group | Promoter individuals / family / trust | Incorporation / majority shareholding | Stake dilution below control threshold |
| Subsidiary | Parent Company | Parent (incorporation / acquisition) | Parent (merger into parent / sale / spin-off) |
| Government | Citizens (democratic mandate) | Constitutional / historical formation | Not applicable |
| Regulator | Government | Legislative mandate (Act of Parliament) | Legislative repeal / Merger with other regulator |
| Central Bank | Government mandate | Act of Parliament (RBI Act 1934) | Not applicable |
| Fund House (AMC) | AMC shareholders / sponsor | SEBI registration | SEBI deregistration / Acquisition |
| Hedge Fund / AIF | Fund sponsor / investors | SEBI Category I/II/III registration | Wind-up / SEBI deregistration |
| Insurance Company | Shareholders / policyholders | IRDAI licensing | Merger / Acquisition / License revocation |
| Pension Fund | Beneficiaries / Government | Legislative creation / PFRDA registration | Legislative dissolution |
| FII | Foreign parent institution | SEBI FPI registration | SEBI deregistration / Full capital exit |
| DII | Indian institutional parent | SEBI / IRDAI / PFRDA registration | Deregistration |
| Retail Investor | Self (individual) | Broker account opening + demat activation | Account closure |
| Broker | Broker company shareholders | SEBI broker registration + exchange membership | SEBI deregistration / closure |
| Market Maker | Market maker entity | Exchange contract agreement | Contract expiry / Non-renewal |
| Investment Bank | IB entity shareholders | SEBI / RBI registration | Deregistration / Acquisition |
| Rating Agency | Rating entity shareholders | Rating agency registration | Deregistration / Merger |
| Research Firm | Research entity | SEBI Research Analyst registration | Deregistration / Closure |
| News Agency | Media entity | Commercial / editorial founding | Acquisition / Shutdown |
| Index Provider | Commercial entity shareholders | Commercial founding | Acquisition / Shutdown |
| **GROUP E — EVENTS** | | | |
| Corporate Action (parent) | Company | Company Board decision | N/A (permanent event record) |
| Earnings Event | Company | Quarter-end → results announcement | N/A (immutable financial record) |
| Monetary Policy Event | Central Bank | MPC meeting process | N/A (immutable policy record) |
| Budget Event | Government | Parliamentary presentation | N/A (immutable fiscal record) |
| Index Rebalancing Event | Index Provider | Periodic index review process | N/A (immutable market structure record) |
| Geopolitical Event | Sovereign actors / external forces | Political / military decision | N/A (immutable historical record) |
| News Event | News Agency / Exchange | Publication / official announcement | N/A (immutable information record) |
| **GROUP F — FINANCIAL STATEMENTS** | | | |
| Income Statement | Company | Company Management (quarterly) | N/A (immutable, archived) |
| Balance Sheet | Company | Company Management (quarterly) | N/A (immutable, archived) |
| Cash Flow Statement | Company | Company Management (quarterly) | N/A (immutable, archived) |
| Notes to Accounts | Company | Company Management | N/A (immutable, archived) |
| Segment Report | Company | Company Management | N/A (immutable, archived) |
| Annual Report | Company / Board | Company Management + Board approval | N/A (immutable, archived) |
| Auditor Report | Auditor (independent) | Auditor (annual engagement) | N/A (immutable, archived) |
| MD&A | Company Management | Company Management | N/A (immutable, archived) |
| **GROUP G — PARTICIPANT ACTIVITY** | | | |
| Portfolio | Investor | Investor (initial capital deployment) | Investor (wind-down) |
| Position | Portfolio | Decision → Order → Trade (open) | Exit Decision → Trade (close) |
| Trade | Portfolio | Order execution on Exchange | N/A (immutable once Exchange confirms) |
| Order | Decision | Decision Engine / Analyst | Exchange (rejection / cancellation) |
| Execution | Trade | Exchange matching engine | N/A (immutable fill record) |
| Transaction | Portfolio | Any financial event (trade / CA / fee) | N/A (immutable financial record) |
| Holding | Portfolio | Trade / Corporate Action (opening) | Sale / Corporate Action (closing) |
| Block Deal | Exchange / Portfolio | Institutional bilateral arrangement | N/A (immutable exchange record) |
| Bulk Deal | Exchange (regulatory record) | Trade crossing 0.5% threshold | N/A (immutable exchange record) |
| Fund Flow Record | Market / Regulator | SEBI / Exchange participant reporting | N/A (immutable daily aggregate) |
| **GROUP H — MARKET INTELLIGENCE** | | | |
| Universe | System | Configuration / SEBI criteria | Configuration update |
| Watchlist | System / User | Intelligence Layer / Manual addition | Manual removal / Universe reset |
| Screen | System | Analyst / System definition | Deletion / Replacement by revised screen |
| Scanner | System | System definition + deployment | System deletion |
| Signal | System | Analytics engine output | Expiry (time-based) / Invalidation |
| Indicator | System | Analytics configuration | Deletion / Replacement |
| Pattern | System | Pattern recognition engine | Expiry / Non-recurrence confirmation |
| Feature | System | Feature engineering process | Deprecation (model no longer uses) |
| Factor | System | Factor definition + validation | Deprecation |
| Score | System | Scoring engine (recalculated) | Next recalculation supersedes |
| Ranking | System | Ranking engine (periodic) | Next period ranking supersedes |
| Alert | System | Monitoring process (threshold breach) | Acknowledgement / Expiry |
| Notification | System | Alert dispatch process | Acknowledged / Expired |
| Market Regime | Intelligence System | Market analysis process | New regime detection |
| **GROUP I — KNOWLEDGE & REASONING** | | | |
| Hypothesis | Intelligence Layer | Observation / pattern trigger | Falsification / Expiry / Confirmed → archived |
| Observation Record | System | Any monitoring / data feed | N/A (permanent immutable record) |
| Evidence Item | Hypothesis | Intelligence Layer analysis | Expiry / Invalidation |
| Reasoning Chain | Hypothesis | Reasoning Layer | Locked immutably at decision execution |
| Conviction | Reasoning Chain | Reasoning Layer aggregation | Evidence change → new conviction supersedes |
| Knowledge Item | Learning System | Learning Layer (validated pattern) | Contradicting evidence → version superseded |
| Model | System | Development / training process | Version superseded / formal retirement |
| Strategy | System | Development / evolution engine | Suspension (underperformance) / Retirement |
| Backtest | Strategy | Backtesting engine | N/A (immutable simulation record) |
| Simulation | System / Analyst | Risk / research process | N/A (immutable scenario record) |
| Learning Record | System | Learning Layer (outcome review) | N/A (permanent immutable record) |
| Prediction | System | Model / Reasoning Chain | Expiry (time horizon) / Outcome realized |
| Outcome Record | System | Position close event | N/A (permanent immutable record) |
| Performance Record | Portfolio / Strategy | System (period-end lock) | N/A (immutable when period locked) |
| **GROUP J — DECISION** | | | |
| Decision | Reasoning Chain | Conviction threshold met | Position closed + Outcome recorded → archived |
| Recommendation | Intelligence Layer | Intelligence / research process | Conversion to Decision / Expiry |
| Constraint | Portfolio Owner / Risk Framework | Human configuration | Owner revision / Risk framework review |
| Objective | Portfolio Owner | Owner formal statement | Achievement / Owner revision |
| Target Level | Decision (set at entry) | Decision process | Hit / Revised (new evidence) / Cancelled |
| Position Sizing Rule | Risk Framework | System / human design | Framework revision |
| **GROUP K — RISK** | | | |
| Risk (abstract) | Portfolio / Market | Inherent to all market activity | N/A (always present while capital deployed) |
| Drawdown | Portfolio | Market movement below prior peak | Recovery to new equity high |
| Stop Loss | Position / Decision | Decision (set at entry) | Hit (exit triggered) / Position closed / Revision |
| Stress Test | Risk Framework | Risk analysis process | N/A (immutable scenario result) |
| VaR Estimate | Portfolio | Daily risk engine recalculation | Next day calculation supersedes |
| **GROUP L — REFERENCE / STRUCTURAL** | | | |
| Sector Classification | External Standard (GICS / NIC / NSE) | Classification authority | Reclassification by standard body |
| Country | Sovereignty (historical) | Historical political formation | Not applicable |
| Currency Reference | Central Bank / Sovereign law | Legal establishment | Redenomination / CBDC replacement |
| Date | Calendar | Passage of time | N/A (permanent reference) |
| Fiscal Year | Entity (company / government) | Entity definition | Entity changes fiscal year-end |
| Trading Day | Trading Calendar | Annual calendar publication | N/A (permanent reference) |
| Expiry Date | Exchange contract specification | Exchange (contract design) | N/A (permanent reference) |
| Regulatory Filing | Regulator / Exchange | Company submission (mandatory) | N/A (permanent compliance record) |
| Audit Trail | System | Every material system action | Never (append-only, permanently immutable) |
| Journal Entry | System / Human | Manual or automated recording | N/A (permanent operational record) |
| Configuration | System | Technical setup / deliberate decision | Next version supersedes; old version archived |

---
## PART VIII — ENTITY INTEGRITY PRINCIPLES

### The Constitutional Framework for Entities

---

**Principle 1 — Every Entity Has Identity**

Every entity has a unique, stable identifier that persists across its entire lifecycle. The identifier does not change when the entity's state changes. A company's ISIN does not change when its CEO changes. A Position's ID does not change when its size is reduced. Identity is permanent.

*Corollary:* No two distinct entities share the same identifier. No entity has multiple valid identifiers without explicit aliasing records.

---

**Principle 2 — Every Entity Has Lifecycle**

No entity exists forever, and no entity appears from nowhere. Every entity has a defined origin, a set of valid states, and one or more terminal states ending its active existence.

*Corollary:* The system must know whether an entity is in an active state. A Futures Contract past expiry is not active. An archived Position is not an open Position.

---

**Principle 3 — Every Entity Has State**

Every entity occupies exactly one state at any given time. State changes happen at a specific timestamp for a specific reason. Every state change must be recorded. An entity's history is the ordered sequence of its state changes.

*Corollary:* State changes are not retroactive. The entity's state at time T is determined by events up to and including T.

---

**Principle 4 — Every Entity Has an Owner**

Every entity is owned by exactly one other entity (or by the system itself, for root entities). Ownership determines responsibility for accuracy, currency, and lifecycle management.

*Corollary:* When an owning entity ceases to exist, owned entities must be reassigned or archived. Orphaned entities are an integrity violation.

---

**Principle 5 — Every Entity Exists Independently of Implementation**

An entity's existence is not dependent on any database, software, or programming framework. The Company "Reliance Industries" exists regardless of whether any system is running.

*Corollary:* Entity definitions must be expressible in natural language before code. If the definition requires software concepts to articulate, it is not yet a proper entity definition.

---

**Principle 6 — Every Entity Must Be Uniquely Identifiable**

There must exist a canonical, unambiguous way to refer to any specific instance. "The NIFTY 50 July 2026 Futures contract" must be uniquely resolvable. "The Reliance Industries Q2 FY2026 results" must be uniquely resolvable.

*Corollary:* Entity naming conventions must be defined and enforced. Ambiguous references are not permitted in reasoning or decision layers.

---

**Principle 7 — Historical Records Are Immutable**

Once an event has occurred, its record cannot be altered. Observation records, trade records, decision records, and learning records are append-only. Errors are corrected by appending correction records — never by modifying originals.

*Corollary:* The reasoning chain supporting a decision is locked at decision time. It may not be revised after the fact.

---

**Principle 8 — Entity Relationships Are Directional and Typed**

Every relationship has a defined direction (A → B does not imply B → A) and a defined type (ownership/causation/dependency/competition). Untyped relationships are not permitted.

*Corollary:* The system must know the relationship type before reasoning about how information about one entity affects beliefs about another.

---

**Principle 9 — Derived Entities Are Traceable to Source Entities**

Every derived entity must be fully traceable to source entities through a documented derivation chain. Untraceable derived values are not trusted.

*Corollary:* When a source entity's state changes, all derived entities dependent on it are marked stale until recomputed.

---

**Principle 10 — Entity Quality Is Graded**

Not all entities are equally reliable. A macro variable from an official government source has higher confidence than an alternative data estimate. Every entity carries a quality or confidence attribute.

*Corollary:* Quality assessments propagate through derivation chains. Low-quality source data cannot produce high-quality derived intelligence.

---

**Principle 11 — The Entity Graph Is the System's Memory**

The totality of all entities, their states, their histories, and their relationships constitutes the system's permanent memory. This memory survives software rewrites, infrastructure changes, and personnel changes. The graph is the asset; the software is a tool to access it.

*Corollary:* No software rewrite should require recreation of the entity graph from scratch. Migration strategies must preserve all historical entity data.

---

**Principle 12 — Entities Evolve; Principles Do Not**

New entity types will be added over the decades. Existing types will gain new attributes. Relationships will be discovered. All of this is permitted and expected.

What does not evolve is this constitutional framework. Every new entity, regardless of when added, must comply with Principles 1-11. The framework applies universally and without exception.

---

## PART IX — FUTURE ENTITY EVOLUTION

### How New Entities Are Added

**Protocol for Adding a New Entity:**

1. **Define it in natural language** — using the 20-attribute template from Part III. If definition requires software concepts, it is not ready.
2. **Classify it** — assign to one or more Part IV classifications. If none fit, propose a new classification with rationale.
3. **Establish its parent** — every new entity needs an existing parent. If none exists, a new parent entity is required.
4. **Define its lifecycle** — all valid states and transitions. Minimum: a created state and a terminal state.
5. **Define its ownership** — which entity owns it? What creates it? What retires it?
6. **Define its relationships** — at minimum, relationship to parent and 3-5 most important other entities.
7. **Assign an identity format** — how are specific instances uniquely referenced?
8. **Document it here** — update this ontology BEFORE any implementation begins.

---

### Anticipated Future Entities (10-Year Horizon)

| Future Entity | Likely Trigger | Horizon |
|---|---|---|
| Carbon Credit Instrument | ESG regulation, SEBI green framework | 2-4 years |
| Digital Currency (CBDC) | RBI Digital Rupee mainstreaming | 2-3 years |
| Real Estate Investment Token | SEBI tokenization framework | 3-5 years |
| AI-Derived Knowledge Entity | System matures to formalized learning output | 1-2 years |
| Entity Graph Node | Knowledge graph implementation | 2-3 years |
| News Sentiment Entity | NLP pipeline for news processing | 1-2 years |
| Regulatory Change Entity | Regulatory intelligence module | 2-3 years |
| Corporate ESG Incident | ESG monitoring module | 2-4 years |
| Supply Chain Link Entity | Supply chain intelligence module | 3-5 years |
| Geopolitical Event (structured) | Macro intelligence expansion | 2-4 years |
| Alternative Data Feed | Alternative data collection | 2-4 years |
| Analyst Entity (individual) | Research intelligence module | 3-5 years |
| Earnings Model Entity | Fundamental intelligence module | 2-3 years |
| Management Quality Score | Governance intelligence module | 3-5 years |

---

### Backward Compatibility Guarantee

When new entities are added:

1. **Existing entities are never renamed** — renaming breaks all references, historical records, and relationships
2. **Existing attributes are never removed** — they may be deprecated (marked optional) but never deleted
3. **New attributes are additive only** — optional by default, NULL for historical records
4. **Existing relationships are preserved** — new relationships are added; existing are not altered
5. **Existing lifecycle states are preserved** — new states may be inserted but terminal states remain valid
6. **Classification assignments are preserved** — entities may gain classifications but not lose existing ones

**The commitment:** Any reasoning or analysis built on this ontology in 2026 will remain valid and interpretable in 2036, even after multiple extensions.

---

## ENTITY COUNT SUMMARY

| Group | Name | Primary Entity Types | Fully Defined |
|---|---|---|---|
| A | Market Infrastructure | 11 | 11 |
| B | Financial Instruments | 17 | 17 |
| C | Economic & Macro | 7 | 7 |
| D | Organizational | 21 | 21 |
| E | Events | 7 parent + 11 sub-entities | 7 (sub-entities in table) |
| F | Financial Statements | 1 parent + 8 sub-entities | 1 (sub-entities in table) |
| G | Participant Activity | 10 | 10 |
| H | Market Intelligence | 14 | 14 |
| I | Knowledge & Reasoning | 14 | 14 |
| J | Decision | 6 | 6 |
| K | Risk | 5 | 5 |
| L | Reference / Structural | 11 | 11 |
| **Total** | | **124 primary entity types** | **123 with full definitions** |

*Including sub-entities defined in parent tables (Corporate Actions ×11, Financial Statements ×8, Risk sub-types ×8): total distinct named entity types exceeds 210.*

---

## DOCUMENT HISTORY

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-07-01 | Initial entity ontology — 88 primary entity types, all 9 parts, lifecycle models, dependency hierarchies, basic ownership map |
| 1.1 | 2026-07-01 | Complete revision — all gaps filled: 124 primary entity types fully defined across all 12 groups; Part IV entity-to-classification mapping matrix (90+ rows); Part VII expanded to full 90+ entity ownership map; Entity Count Summary updated |

---

*This document answers the question: "What things exist?"*
*Every module, every model, every intelligence layer, and every decision*
*must operate on entities defined in this ontology.*
*Extend this document before creating any entity type not already defined here.*






