# EVENT ONTOLOGY
## AI Trading Brain — Complete Event Universe

**Version:** 1.0
**Status:** Authoritative
**Date:** 2026-07-01
**Parent Documents:** MASTER_KNOWLEDGE_ARCHITECTURE.md | INFORMATION_ONTOLOGY.md | ENTITY_ONTOLOGY.md | RELATIONSHIP_ONTOLOGY.md

---

> *This document answers the question: "What changes the state of entities?"*
> *Every event that can occur in the investment universe — named, defined, governed.*
> *Every state transition requires an event. Every event is immutable. Every event is timestamped.*

---

## PART I — THE NATURE OF EVENTS

### What Is an Event?

An event is a discrete, timestamped, immutable occurrence that causes one or more entity instances to transition from one state to another — producing information, altering relationships, generating evidence, and potentially triggering further events.

Events are the AGENTS OF CHANGE in the investment universe. Without events, the universe is static. Every observable difference in an entity's state — every change in a stock's price, every policy decision, every earnings report, every market regime shift — is caused by an event.

**The Constitutional Definition:**
An event is a discrete, irreversible, timestamped occurrence that:
1. Happens at a specific point in time (or within a bounded time window)
2. Causes at least one entity to change state
3. Produces information about that state change
4. Is recorded permanently and immutably in the event log
5. May trigger zero or more subsequent events
6. Cannot be undone, only superseded by later events

---

### The Six-Test Definition

An occurrence qualifies as an Event if and only if:

1. **It is discrete** — it can be identified as a distinct, bounded occurrence with a beginning and an end
2. **It is timestamped** — it occurred at a specific, verifiable point in time
3. **It changes state** — at least one entity transitions from one observable state to another
4. **It is immutable** — once it occurred, it cannot be un-occurred; only subsequent events can alter the new state
5. **It has a cause** — every event has an antecedent cause, even if that cause is another event
6. **It produces information** — it makes previously unknown facts knowable

If all six conditions are met, it is an event.

---

### What Is NOT an Event

| Concept | What It Is | Why It Is Not an Event |
|---|---|---|
| **Entity** | An independently existing thing | Entities are the objects that events act upon. An entity does not occur — it exists. |
| **Information** | A structured signal about an entity's state | Information is produced by events; it is not the event itself. The fact "HDFC Bank stock is at ₹1,850" is information. The event "HDFC Bank stock crossed ₹1,850 for the first time" is an event. |
| **Observation** | A timestamped record of an entity's state | An observation records a state; it does not cause a state change. Observing the price is not the event; the price crossing the threshold is the event. |
| **Evidence** | A weighted observation pointing to a hypothesis | Evidence is an interpretation of historical events. The evidence is not the event. |
| **Relationship** | A typed connection between entities | Relationships connect entities structurally. A new relationship is created by an event (IPO creates the ISSUES relationship), but the relationship is not itself the event. |
| **Knowledge** | A validated, durable pattern | Knowledge is derived from the history of events. "Markets tend to fall 3 months after yield curve inversion" is knowledge derived from past event patterns, not an event. |
| **Decision** | An action commitment produced by reasoning | A decision is a special type of event in the AI/System domain. But in general, decisions are outputs of the reasoning process triggered by events. |
| **Action** | The physical execution of a decision | An action is the consequence of a decision event. Submitting an order is an action. Order submission is an event. |
| **Outcome** | The final realized result of an event or sequence | An outcome is the terminus of an event chain — the observed state after all effects propagate. |
| **State** | The current condition of an entity at a point in time | State is what events change. State is the before and after; the event is the transition. |
| **State Change** | The difference between two states of an entity | A state change is the effect of an event — it is evidence that an event occurred. But the change itself is not the event. |
| **Condition** | A persistent configuration of circumstances | A condition is a sustained state, not a discrete occurrence. A bear market is a condition; the day it began is an event. |
| **Trend** | A sustained directional movement | A trend is a sequence of states, not a single event. The trend reversal point is an event. |
| **Pattern** | A recurring sequence of states or events | A pattern is a meta-observation about event sequences, not an event itself. |
| **Process** | A sustained, continuous set of activities | A process has duration; events are discrete. A regulatory audit is a process; the audit finding is an event. |

---

### Why Events Exist

**Events are why knowledge decays.** Every piece of knowledge in the investment universe has a validity window. That window closes when a superseding event occurs. "Reliance is in a bullish trend" was true until the trend-break event occurred. Events are what make staleness possible — and staleness is the primary enemy of investment intelligence.

**Events are why positions must be monitored.** A position opened at time T is subject to every event that affects its underlying entity from T forward. Without event monitoring, positions cannot be managed.

**Events are why the market is non-stationary.** Statistical relationships — correlations, beta, lead-lag structures — change over time because structural events change the mechanisms that create those relationships.

**Events are what the system exists to anticipate, process, and respond to.** The entire AI Trading Brain is an event-processing machine: it anticipates events (via predictions), processes events (via reasoning), and responds to events (via decisions).

---

### Why Events Are Immutable

Events are permanently and irreversibly fixed in time. The Reliance Industries Q4 FY26 earnings announcement occurred on a specific date. That cannot change. The RBI's October 2026 rate cut occurred. It cannot be un-occurred. Only subsequent events can alter the state that the original event created.

**Immutability enables:**
- Reliable audit trails — every decision can be traced to the events that caused it
- Historical backtesting — simulating the system's behavior by replaying the historical event stream
- Point-in-time queries — reconstructing the exact knowledge state at any historical moment
- Accountability — identifying which event caused which decision and why

**The Event Ledger is the ground truth.** The event log is the most authoritative record in the system. When the system's beliefs are inconsistent with the event log, the event log wins.

---

### Why Events Are Timestamped

Every event must carry a timestamp for:
- **Causality ordering** — cause must precede effect
- **Staleness tracking** — knowledge derived from an event degrades with time
- **Sequencing** — when two events occur nearly simultaneously, the ordering matters
- **Lag calculation** — measuring the time between cause and effect events
- **Calendar intelligence** — identifying recurring patterns in event timing
- **Regulatory compliance** — audit requirements demand precise timestamps

Events carry multiple timestamps:
- **Occurred At** — when the real-world event happened
- **Discovered At** — when the system learned of the event
- **Processed At** — when the system completed reasoning about the event
- **Expired At** — when the event's direct effects were superseded (optional)

The gap between Occurred At and Discovered At is the **information delay** — a source of competitive advantage or disadvantage.

---

### The Event-Entity-State Triad

The relationship between events, entities, and states is the fundamental unit of change in the investment universe:

```
BEFORE STATE ─────── EVENT ─────── AFTER STATE
                        │
                        ▼
              Information Produced
              Relationships Changed
              Knowledge Updated
              New Events Triggered
```

No event exists without affecting at least one entity. No state change exists without an event causing it. Information is the record of that transition. This triad is the atomic unit of change in the investment knowledge graph.

---

### Event Versus Adjacent Concepts — Precision Table

| Question | Correct Answer |
|---|---|
| "Is a stock price rising an event?" | No — the rise is a state transition. The specific price CROSSING a defined threshold (resistance level, 52-week high, circuit limit) is an event. |
| "Is a recession an event?" | No — a recession is a condition. The GDP contraction that begins a recession is an event. The first negative GDP print is an event. The recession itself is a sustained state. |
| "Is FII selling an event?" | Yes — a discrete session of net FII selling above a threshold is an event. Sustained FII selling is a condition. |
| "Is a bull market an event?" | No — a bull market is a regime (condition). The breakout that begins the bull market is an event. |
| "Is earnings season an event?" | No — earnings season is a period. Each company's results release is an event. |
| "Is a strategy being deployed an event?" | Yes — the first activation of a strategy by the AI system is an event (STRATEGY_ACTIVATED). |
| "Is a model being updated an event?" | Yes — model parameter update is an event (MODEL_UPDATED). |
| "Is an alert firing an event?" | Yes — threshold crossing triggering an alert is an event (ALERT_TRIGGERED). |

---

## PART II — COMPLETE EVENT UNIVERSE

*The complete catalog of event classes. 300+ event types organized into 14 major groups.*
*Brief descriptions here; full 20-attribute definitions in Part III for critical events.*

---

### Group A — Corporate Events

*Events caused by decisions, disclosures, or actions of listed or unlisted companies.*

#### A.1 — Earnings and Financial Results

| Event | Code | Brief Description |
|---|---|---|
| Quarterly Results Release | A.1.01 | Company publishes Q1/Q2/Q3/Q4 financial results on exchange |
| Annual Results Release | A.1.02 | Company publishes full-year audited results |
| Earnings Beat | A.1.03 | Reported EPS/revenue exceeds consensus estimate by defined threshold |
| Earnings Miss | A.1.04 | Reported EPS/revenue falls short of consensus estimate by defined threshold |
| Earnings In-Line | A.1.05 | Reported results within acceptable variance of consensus |
| Revenue Guidance Upgrade | A.1.06 | Management increases forward revenue projection |
| Revenue Guidance Downgrade | A.1.07 | Management cuts forward revenue projection |
| Margin Expansion | A.1.08 | EBITDA/net margin improves materially vs prior period |
| Margin Compression | A.1.09 | EBITDA/net margin deteriorates materially vs prior period |
| Revenue Acceleration | A.1.10 | Sequential and YoY revenue growth rate increases |
| Revenue Deceleration | A.1.11 | Sequential and YoY revenue growth rate falls |
| Earnings Restatement | A.1.12 | Company revises previously published financials (can be upward or downward) |
| Profit Warning | A.1.13 | Pre-results announcement that earnings will miss expectations significantly |
| Exceptional Item | A.1.14 | One-time large gain or charge materially affecting reported profits |
| Working Capital Deterioration | A.1.15 | Days Sales Outstanding or Days Inventory Outstanding increase significantly |
| Debt-to-Equity Increase | A.1.16 | Company's leverage ratio rises above defined threshold |
| Free Cash Flow Negative | A.1.17 | Company reports negative FCF for the quarter/year |
| Cash Flow Inflection | A.1.18 | Company transitions from negative to positive FCF or vice versa |
| Impairment Charge | A.1.19 | Company writes down value of asset due to impairment |
| Goodwill Write-Down | A.1.20 | Company impairs goodwill from past acquisition |

#### A.2 — Dividend Events

| Event | Code | Brief Description |
|---|---|---|
| Dividend Declaration | A.2.01 | Board announces dividend amount and record date |
| Interim Dividend | A.2.02 | Dividend paid before year-end financial results |
| Final Dividend | A.2.03 | Dividend declared after full-year results |
| Special Dividend | A.2.04 | One-time extraordinary dividend outside normal cycle |
| Dividend Cut | A.2.05 | Company reduces dividend below prior period |
| Dividend Suspension | A.2.06 | Company stops paying dividend indefinitely |
| Dividend Reinstatement | A.2.07 | Company resumes dividend after suspension |
| Ex-Dividend Date | A.2.08 | Date after which new buyers are not entitled to declared dividend |
| Record Date | A.2.09 | Date on which shareholder register is reviewed for dividend eligibility |
| Dividend Payout | A.2.10 | Actual cash transfer to shareholders |
| Dividend Yield Threshold Cross | A.2.11 | Company's yield crosses institutional minimum (e.g., 2%) making it eligible for income funds |

#### A.3 — Capital Structure Events

| Event | Code | Brief Description |
|---|---|---|
| Bonus Issue | A.3.01 | Company issues additional shares to existing shareholders at no cost (reduces per-share price) |
| Stock Split | A.3.02 | Company divides existing shares into multiple shares (reduces face value) |
| Stock Consolidation | A.3.03 | Company merges multiple shares into fewer shares |
| Rights Issue | A.3.04 | Company offers existing shareholders right to buy additional shares at discount |
| Rights Renunciation | A.3.05 | Shareholder sells/transfers their rights entitlement |
| QIP (Qualified Institutional Placement) | A.3.06 | Company raises capital by issuing shares to qualified institutional buyers |
| Preferential Allotment | A.3.07 | Company issues shares to specific investors at a defined price |
| ESOP Grant | A.3.08 | Company grants employee stock options |
| ESOP Exercise | A.3.09 | Employee exercises stock option converting to equity shares |
| Buyback Announcement | A.3.10 | Company announces intention to repurchase own shares from market |
| Buyback Completion | A.3.11 | Company completes the buyback program |
| Buyback Cancellation | A.3.12 | Company cancels announced buyback before completion |
| Face Value Change | A.3.13 | Company changes nominal face value of share |
| Share Capital Reduction | A.3.14 | Company reduces paid-up capital through defined mechanism |
| Warrant Conversion | A.3.15 | Warrant holder converts warrant to equity share |
| Convertible Bond Conversion | A.3.16 | Bondholder exercises conversion option |
| Debt Restructuring | A.3.17 | Company renegotiates terms of outstanding debt |
| Debt Prepayment | A.3.18 | Company repays debt ahead of schedule |
| Bond Maturity | A.3.19 | Corporate bond reaches maturity date |
| Commercial Paper Maturity | A.3.20 | CP reaches 30/60/90-day maturity |

#### A.4 — Corporate Action Events

| Event | Code | Brief Description |
|---|---|---|
| Merger Announcement | A.4.01 | Two companies announce intent to merge |
| Merger Completion | A.4.02 | Regulatory approval received; merger legally effective |
| Merger Cancellation | A.4.03 | Announced merger abandoned |
| Acquisition Announcement | A.4.04 | Company announces intent to acquire another entity |
| Acquisition Completion | A.4.05 | Acquisition closes; target becomes subsidiary |
| Divestiture Announcement | A.4.06 | Company announces sale of subsidiary or business unit |
| Divestiture Completion | A.4.07 | Sale closes; entity separated |
| Spin-Off Announcement | A.4.08 | Parent announces separation of subsidiary into standalone company |
| Spin-Off Completion | A.4.09 | Subsidiary lists independently |
| Demerger | A.4.10 | Company splits into two or more listed entities |
| Open Offer Announcement | A.4.11 | Acquirer announces open offer to public shareholders at premium |
| Delisting Announcement | A.4.12 | Company announces intention to delist from exchange |
| Voluntary Delisting | A.4.13 | Company successfully delists following SEBI process |
| Compulsory Delisting | A.4.14 | Exchange forces delisting due to non-compliance |
| Suspension of Trading | A.4.15 | Exchange suspends trading in stock due to query/investigation |
| Relisting | A.4.16 | Previously delisted stock resumes trading |
| Name Change | A.4.17 | Company changes its registered name |
| Ticker Change | A.4.18 | Exchange symbol changes |
| Category Change | A.4.19 | Stock reclassified in exchange category (e.g., T2T to normal) |

#### A.5 — Management and Governance Events

| Event | Code | Brief Description |
|---|---|---|
| CEO Appointment | A.5.01 | New Chief Executive Officer begins role |
| CEO Resignation | A.5.02 | Sitting CEO announces departure |
| CEO Retirement | A.5.03 | Planned transition at end of tenure |
| CFO Change | A.5.04 | New Chief Financial Officer appointment or departure |
| MD/Whole-Time Director Change | A.5.05 | Managing Director or Whole-Time Director appointment or departure |
| Board Director Appointment | A.5.06 | New director joins board |
| Board Director Resignation | A.5.07 | Director resigns from board |
| Independent Director Change | A.5.08 | Change in independent director composition |
| Auditor Change | A.5.09 | Company appoints new statutory auditor |
| Auditor Resignation | A.5.10 | Sitting auditor resigns — highly negative governance signal |
| Promoter Shareholding Increase | A.5.11 | Promoter group increases stake through market purchase |
| Promoter Shareholding Decrease | A.5.12 | Promoter group sells shares |
| Promoter Pledge Creation | A.5.13 | Promoter pledges shares as collateral |
| Promoter Pledge Increase | A.5.14 | Pledge percentage increases — increasing financial stress signal |
| Promoter Pledge Release | A.5.15 | Pledge released — positive signal |
| Promoter Pledge Invocation | A.5.16 | Lender invokes pledge due to margin call — severe negative event |
| AGM (Annual General Meeting) | A.5.17 | Annual shareholder meeting occurs |
| EGM (Extraordinary General Meeting) | A.5.18 | Special shareholder meeting called for specific resolution |
| Resolution Passed | A.5.19 | Specific resolution approved at AGM/EGM |
| Resolution Rejected | A.5.20 | Specific resolution voted down at AGM/EGM |
| Whistleblower Complaint | A.5.21 | Material whistleblower allegation filed against company |
| Fraud Allegation | A.5.22 | Serious fraud or accounting manipulation alleged |
| Regulatory Investigation Initiated | A.5.23 | SEBI/ED/CBI begins formal investigation of company |
| Regulatory Order | A.5.24 | Regulator issues order (show cause, penalty, ban) |
| Court Judgment | A.5.25 | Court delivers judgment materially affecting company |

#### A.6 — Credit and Rating Events

| Event | Code | Brief Description |
|---|---|---|
| Credit Rating Upgrade | A.6.01 | Rating agency raises issuer or instrument rating |
| Credit Rating Downgrade | A.6.02 | Rating agency lowers issuer or instrument rating |
| Rating Watch Positive | A.6.03 | Rating placed on watch with positive implications |
| Rating Watch Negative | A.6.04 | Rating placed on watch with negative implications — pre-downgrade signal |
| Rating Outlook Change | A.6.05 | Outlook changed to Positive/Negative/Stable |
| Rating Withdrawal | A.6.06 | Rating agency withdraws rating at issuer request or due to lack of information |
| Rating Assignment | A.6.07 | New instrument receives first-time rating |
| Credit Default | A.6.08 | Company fails to pay interest or principal on debt |
| NCLT Admission | A.6.09 | Company admitted to National Company Law Tribunal insolvency process |
| NCLT Resolution Plan Approved | A.6.10 | Insolvency resolution plan accepted |
| NCLT Liquidation Ordered | A.6.11 | NCLT orders company liquidation |
| NPA Classification | A.6.12 | Bank classifies loan to company as Non-Performing Asset |
| OTS (One-Time Settlement) | A.6.13 | Company settles debt at discount |
| SDR (Strategic Debt Restructuring) | A.6.14 | Banks convert debt to equity under restructuring |

#### A.7 — Disclosure and Communication Events

| Event | Code | Brief Description |
|---|---|---|
| Exchange Filing | A.7.01 | Company files disclosure on BSE/NSE (any category) |
| DRHP Filing | A.7.02 | Draft Red Herring Prospectus filed for IPO |
| Prospectus Filing | A.7.03 | Final prospectus filed ahead of IPO |
| IPO Opening | A.7.04 | IPO subscription opens to investors |
| IPO Closing | A.7.05 | Subscription window closes |
| IPO Allotment | A.7.06 | Shares allotted to applicants |
| IPO Listing | A.7.07 | Stock begins trading on exchange for first time |
| Investor/Analyst Day | A.7.08 | Company hosts formal investor presentation event |
| Earnings Conference Call | A.7.09 | Management hosts post-results analyst call |
| Analyst Meet | A.7.10 | One-on-one or group meeting between management and analysts |
| Press Release | A.7.11 | Company publishes press release on material development |
| Investor Presentation Upload | A.7.12 | Updated investor presentation published on exchange |
| Corporate Website Update | A.7.13 | Material update to company corporate website |
| Annual Report Publication | A.7.14 | Full annual report published and available |
| Guidance Given | A.7.15 | Management provides quantitative forward-looking guidance |
| Guidance Maintained | A.7.16 | Management reaffirms existing guidance |
| Guidance Withdrawn | A.7.17 | Management withdraws previously given guidance (high uncertainty signal) |

---

### Group B — Market Structure Events

*Events produced by the mechanics of markets, exchanges, and instruments.*

#### B.1 — Price Events

| Event | Code | Brief Description |
|---|---|---|
| 52-Week High | B.1.01 | Stock reaches highest price in rolling 52-week period |
| 52-Week Low | B.1.02 | Stock reaches lowest price in rolling 52-week period |
| All-Time High | B.1.03 | Stock reaches highest ever recorded price |
| All-Time Low | B.1.04 | Stock reaches lowest ever recorded price |
| Gap Up Open | B.1.05 | Stock opens significantly above previous day's close |
| Gap Down Open | B.1.06 | Stock opens significantly below previous day's close |
| Upper Circuit Hit | B.1.07 | Stock reaches maximum allowed daily price increase |
| Lower Circuit Hit | B.1.08 | Stock reaches maximum allowed daily price decline |
| Circuit Limit Change | B.1.09 | Exchange changes circuit filter percentage for a stock |
| Resistance Break | B.1.10 | Price closes above a defined technical resistance level |
| Support Break | B.1.11 | Price closes below a defined technical support level |
| Trend Line Break | B.1.12 | Price breaks established trend line |
| Moving Average Crossover | B.1.13 | Shorter-period MA crosses above/below longer-period MA |
| Bollinger Band Expansion | B.1.14 | Bands widen indicating volatility increase |
| Bollinger Band Squeeze | B.1.15 | Bands narrow indicating volatility compression before move |
| ATH Breakout | B.1.16 | Price breaks all-time high — high-conviction bullish event |
| VWAP Cross | B.1.17 | Price crosses VWAP intraday — signals institutional sentiment shift |
| Round Number Level Cross | B.1.18 | Price crosses psychologically significant round number |

#### B.2 — Volume Events

| Event | Code | Brief Description |
|---|---|---|
| Volume Explosion | B.2.01 | Daily volume exceeds N× (e.g., 5×) average daily volume |
| Climax Volume | B.2.02 | Extremely high volume on extreme price day — potential exhaustion |
| Volume Dry-Up | B.2.03 | Volume drops to multi-month low — potential consolidation end |
| Unusual Volume Alert | B.2.04 | Volume above threshold without obvious corporate news |
| Block Deal | B.2.05 | Large institutional transaction executed on exchange |
| Bulk Deal | B.2.06 | Transaction exceeding 0.5% of company shares in a session |
| Off-Market Transfer | B.2.07 | Large shares transferred off exchange — insider activity signal |
| Delivery Volume Spike | B.2.08 | Delivery percentage spikes — signals genuine accumulation or distribution |
| Low Delivery Volume | B.2.09 | Delivery percentage very low — intraday speculative trading signal |

#### B.3 — Derivatives and Options Events

| Event | Code | Brief Description |
|---|---|---|
| Open Interest Build-Up | B.3.01 | OI increases significantly — new money entering |
| Open Interest Unwinding | B.3.02 | OI decreases significantly — positions being closed |
| Short Build-Up | B.3.03 | OI increases + price falls — fresh short positions |
| Short Covering | B.3.04 | OI decreases + price rises — shorts being closed |
| Long Build-Up | B.3.05 | OI increases + price rises — fresh long positions |
| Long Unwinding | B.3.06 | OI decreases + price falls — longs being closed |
| PCR Extreme | B.3.07 | Put-Call Ratio reaches extreme (very high = bearish sentiment; very low = bullish) |
| Max Pain Level Approach | B.3.08 | Price approaches maximum pain level ahead of expiry |
| Options Expiry | B.3.09 | Weekly/monthly options expiry occurs |
| Futures Expiry | B.3.10 | Monthly futures contract expires |
| Rollover Event | B.3.11 | Significant open interest rolls from near to far month |
| Gamma Squeeze | B.3.12 | Rapid price appreciation forces options dealers to delta-hedge by buying |
| IV Spike | B.3.13 | Implied volatility rises sharply — fear or event anticipation signal |
| IV Crush | B.3.14 | Implied volatility collapses after anticipated event (post-results) |
| Options Chain Distortion | B.3.15 | Unusual skew or smile distortion in options chain |
| Cost of Carry Change | B.3.16 | Basis between spot and futures changes materially |

#### B.4 — Market-Wide Events

| Event | Code | Brief Description |
|---|---|---|
| Market Open | B.4.01 | Exchange opens for trading session |
| Market Close | B.4.02 | Exchange closes for trading session |
| Pre-Market Session | B.4.03 | Pre-open call auction session |
| Market Holiday | B.4.04 | Exchange closed for listed holiday |
| Trading Halt | B.4.05 | Exchange halts trading across market (index circuit) |
| Trading Resumption | B.4.06 | Trading resumes after halt |
| NIFTY 50 Correction | B.4.07 | NIFTY falls 10%+ from recent peak |
| NIFTY 50 Bear Market | B.4.08 | NIFTY falls 20%+ from recent peak |
| Market Breadth Collapse | B.4.09 | Advance-Decline ratio falls to extreme level (< 0.2) |
| Market Breadth Surge | B.4.10 | Advance-Decline ratio rises to extreme level (> 4.0) |
| Sector Rotation Event | B.4.11 | Capital flows shift visibly between sectors over defined period |
| Broad Market Rally | B.4.12 | >80% of NIFTY stocks rise in same session |
| Broad Market Sell-Off | B.4.13 | >80% of NIFTY stocks fall in same session |
| Flash Crash | B.4.14 | Sudden extreme market decline followed by rapid recovery |
| Market Circuit Breaker L1 | B.4.15 | NIFTY falls 10% — 45-minute halt |
| Market Circuit Breaker L2 | B.4.16 | NIFTY falls 15% — 1-hour 45-minute halt |
| Market Circuit Breaker L3 | B.4.17 | NIFTY falls 20% — trading halted for remainder of day |
| India VIX Spike | B.4.18 | India VIX rises above defined threshold (e.g., 30, 40) |
| India VIX Collapse | B.4.19 | India VIX falls sharply from elevated level |
| New 52-Week High Breadth Surge | B.4.20 | Large number of stocks simultaneously reaching new 52-week highs |

#### B.5 — Index Events

| Event | Code | Brief Description |
|---|---|---|
| Index Rebalancing | B.5.01 | Periodic reconstitution of index components |
| Index Inclusion | B.5.02 | Stock added to index — passive fund buying triggered |
| Index Exclusion | B.5.03 | Stock removed from index — passive fund selling triggered |
| Index Weight Change | B.5.04 | Free-float adjustment changes a constituent's weight |
| New Index Launch | B.5.05 | Exchange or provider launches new index product |
| Index Composition Review | B.5.06 | Periodic review of index eligibility criteria |
| MSCI Weight Change | B.5.07 | MSCI changes India/stock weight in EM index — global fund flow trigger |
| MSCI Inclusion | B.5.08 | Stock/market added to MSCI index |
| MSCI Exclusion | B.5.09 | Stock/market removed from MSCI index |
| FTSE Russell Rebalancing | B.5.10 | FTSE Russell index rebalancing affecting Indian components |

#### B.6 — Liquidity Events

| Event | Code | Brief Description |
|---|---|---|
| Liquidity Shock | B.6.01 | Sudden severe reduction in market-wide or stock-specific liquidity |
| Bid-Ask Spread Explosion | B.6.02 | Spread widens dramatically indicating liquidity withdrawal |
| Market Maker Withdrawal | B.6.03 | Primary liquidity providers step back from market |
| ETF Arbitrage Disruption | B.6.04 | ETF price deviates significantly from NAV |
| Trade Settlement Failure | B.6.05 | Settlement fail in clearing system |
| Margin Call Event | B.6.06 | Broker issues margin call requiring immediate collateral |
| Forced Liquidation | B.6.07 | Margin shortfall causes broker to forcibly sell client positions |
| Repo Market Stress | B.6.08 | Overnight repo rates spike indicating funding stress |
| Credit Market Freeze | B.6.09 | Corporate bond market illiquid; no buyers at par |

---

### Group C — Macro-Economic Events

*Events produced by national and global macroeconomic dynamics.*

#### C.1 — Indian Macro Data Events

| Event | Code | Brief Description |
|---|---|---|
| GDP Growth Release | C.1.01 | Government publishes quarterly GDP growth estimate |
| GDP Revision | C.1.02 | Previously published GDP figure revised upward or downward |
| CPI Release | C.1.03 | Consumer Price Index inflation data published |
| WPI Release | C.1.04 | Wholesale Price Index data published |
| Core CPI Release | C.1.05 | CPI excluding food and fuel published |
| Food Inflation Spike | C.1.06 | Food price component of CPI rises to elevated level |
| IIP Release | C.1.07 | Index of Industrial Production data published |
| PMI Manufacturing Release | C.1.08 | Manufacturing Purchasing Managers Index published |
| PMI Services Release | C.1.09 | Services PMI published |
| PMI Composite Release | C.1.10 | Composite PMI (manufacturing + services) published |
| Current Account Data | C.1.11 | Current account balance published |
| Trade Balance Data | C.1.12 | Merchandise trade deficit/surplus published |
| Fiscal Deficit Data | C.1.13 | Government fiscal deficit data published |
| GST Collection | C.1.14 | Monthly GST revenue data published |
| Auto Sales Data | C.1.15 | Monthly vehicle sales data by Society of Indian Automobile Manufacturers |
| Power Consumption Data | C.1.16 | Monthly electricity demand data published |
| Credit Growth Data | C.1.17 | RBI publishes bank credit growth figures |
| Deposit Growth Data | C.1.18 | RBI publishes bank deposit growth figures |
| FX Reserves Data | C.1.19 | RBI publishes weekly forex reserves level |
| INR Rate Movement | C.1.20 | INR crosses defined threshold vs USD/EUR/GBP |

#### C.2 — Indian Monetary Policy Events

| Event | Code | Brief Description |
|---|---|---|
| RBI MPC Meeting | C.2.01 | Monetary Policy Committee convenes |
| Repo Rate Cut | C.2.02 | RBI reduces policy repo rate |
| Repo Rate Hike | C.2.03 | RBI increases policy repo rate |
| Repo Rate Hold | C.2.04 | RBI maintains repo rate unchanged |
| CRR Change | C.2.05 | Cash Reserve Ratio changed — affects bank liquidity |
| SLR Change | C.2.06 | Statutory Liquidity Ratio changed |
| Reverse Repo Rate Change | C.2.07 | Rate at which banks park funds with RBI changes |
| MSF Rate Change | C.2.08 | Marginal Standing Facility rate changes |
| MCLR Change | C.2.09 | Marginal Cost of Funds-Based Lending Rate changes |
| RBI Stance Change | C.2.10 | MPC changes policy stance (accommodative/neutral/withdrawal) |
| OMO Purchase | C.2.11 | RBI buys government bonds (injecting liquidity) |
| OMO Sale | C.2.12 | RBI sells government bonds (withdrawing liquidity) |
| VRR Auction | C.2.13 | Variable Rate Repo auction — short-term liquidity management |
| Currency Intervention | C.2.14 | RBI intervenes in FX market to manage INR rate |
| G-Sec Auction | C.2.15 | Government conducts weekly bond auction |
| T-Bill Auction | C.2.16 | Government sells short-term treasury bills |
| RBI Policy Statement | C.2.17 | Governor reads policy statement with forward guidance |
| RBI Circular | C.2.18 | RBI issues regulatory circular affecting banking sector |
| Banking Regulation Change | C.2.19 | RBI changes banking sector rules (NBFC, priority sector, etc.) |

#### C.3 — Indian Fiscal Policy Events

| Event | Code | Brief Description |
|---|---|---|
| Union Budget | C.3.01 | Annual Union Budget presented in Parliament |
| Budget Announcement — Tax Change | C.3.02 | Direct or indirect tax rate change announced in budget |
| Budget Announcement — Sector Allocation | C.3.03 | Budget allocates/reduces funds for specific sector |
| Mid-Year Economic Review | C.3.04 | Government publishes mid-year fiscal review |
| Supplementary Demands for Grants | C.3.05 | Additional budget allocations sought |
| Divestment Announcement | C.3.06 | Government announces public sector stake sale |
| Divestment Completion | C.3.07 | Government completes stake sale in PSU |
| Production-Linked Incentive Scheme | C.3.08 | New PLI scheme announced for sector |
| Infrastructure Project Announcement | C.3.09 | Major government infrastructure project announced |
| Tax Collection Milestone | C.3.10 | Government announces record direct/indirect tax collection |

#### C.4 — Global Macro Events

| Event | Code | Brief Description |
|---|---|---|
| US Federal Reserve Meeting | C.4.01 | FOMC meeting and decision |
| Fed Rate Cut | C.4.02 | US Fed reduces federal funds rate |
| Fed Rate Hike | C.4.03 | US Fed increases federal funds rate |
| Fed QE Announcement | C.4.04 | Fed announces quantitative easing program |
| Fed QT Announcement | C.4.05 | Fed announces quantitative tightening (balance sheet reduction) |
| US CPI Release | C.4.06 | US inflation data published — major global market mover |
| US PCE Release | C.4.07 | Personal Consumption Expenditure price index (Fed's preferred measure) |
| US Jobs Report | C.4.08 | Non-Farm Payrolls and unemployment rate published |
| US GDP Release | C.4.09 | US quarterly GDP growth published |
| US Yield Curve Inversion | C.4.10 | 2-year/10-year spread turns negative |
| US Yield Curve Normalization | C.4.11 | Inverted yield curve returns to positive slope |
| ECB Rate Decision | C.4.12 | European Central Bank rate decision |
| Bank of Japan Decision | C.4.13 | BOJ rate and yield curve control decision |
| China PMI Release | C.4.14 | Chinese manufacturing PMI — global growth indicator |
| China GDP Release | C.4.15 | Chinese quarterly GDP |
| Global PMI Flash | C.4.16 | JPMorgan Global Composite PMI flash estimate |
| G7/G20 Meeting | C.4.17 | Major economy leaders meet — potential policy statements |
| IMF Growth Forecast | C.4.18 | IMF publishes World Economic Outlook |
| World Bank Report | C.4.19 | World Bank publishes major India or global economic assessment |

#### C.5 — Commodity Events

| Event | Code | Brief Description |
|---|---|---|
| Crude Oil Spike | C.5.01 | Brent/WTI crude oil rises sharply (>5% in session or to threshold) |
| Crude Oil Crash | C.5.02 | Crude oil price falls sharply |
| OPEC Production Decision | C.5.03 | OPEC+ agrees to increase or decrease production quotas |
| Gold Price Breakout | C.5.04 | Gold crosses key resistance level |
| Gold Price Breakdown | C.5.05 | Gold breaks support level |
| Natural Gas Spike | C.5.06 | Natural gas price spike affecting energy-intensive industry |
| Base Metal Rally | C.5.07 | Copper/Aluminium/Zinc rally — global growth signal |
| Base Metal Sell-Off | C.5.08 | Base metals fall — global recession signal |
| Agricultural Commodity Price Move | C.5.09 | Key crop price (wheat, soybean, sugar) moves significantly |
| MCX Commodity Circuit | C.5.10 | MCX commodity hits circuit limit |
| Commodity Inventory Data | C.5.11 | US EIA oil inventory data published |

---

### Group D — Geopolitical Events

*Events caused by political, military, diplomatic, or social forces.*

#### D.1 — Political Events

| Event | Code | Brief Description |
|---|---|---|
| National Election Announcement | D.1.01 | Election Commission announces general election dates |
| National Election Result | D.1.02 | General election results declared |
| State Election Result | D.1.03 | State Assembly election results |
| Government Formation | D.1.04 | New government takes office |
| Coalition Collapse | D.1.05 | Ruling coalition loses majority |
| Cabinet Reshuffle | D.1.06 | Significant changes in Cabinet ministerial portfolios |
| Finance Minister Change | D.1.07 | New Finance Minister appointed |
| RBI Governor Change | D.1.08 | New RBI Governor appointed — potential policy change signal |
| SEBI Chairman Change | D.1.09 | New SEBI Chairman appointed |
| Policy Announcement | D.1.10 | Government announces major economic policy shift |
| Nationalization Announcement | D.1.11 | Government announces nationalization of private sector entity |
| Privatization Announcement | D.1.12 | Government announces privatization of state enterprise |
| Retrospective Tax Imposition | D.1.13 | Government imposes tax with retrospective effect |
| Retrospective Tax Removal | D.1.14 | Government removes retrospective tax provision |
| Trade Policy Change | D.1.15 | Import duty or export policy changes materially |
| FDI Policy Change | D.1.16 | Foreign direct investment rules amended |
| FEMA Regulation Change | D.1.17 | Foreign Exchange Management Act rules amended |

#### D.2 — Military and Conflict Events

| Event | Code | Brief Description |
|---|---|---|
| War Declaration | D.2.01 | Nation declares war |
| Military Strike | D.2.02 | Military action taken against target |
| Ceasefire Announcement | D.2.03 | Parties agree to stop military action |
| Border Conflict Escalation | D.2.04 | Existing border dispute intensifies materially |
| Nuclear Tension Event | D.2.05 | Nuclear threat or test by nation-state |
| Terrorist Attack | D.2.06 | Significant terrorist event in financial hub or politically sensitive location |
| Cyber Attack on Infrastructure | D.2.07 | Major cyber attack on power grid, banking system, or exchange |
| Coup or Government Overthrow | D.2.08 | Government overthrown or coup attempt in major economy |

#### D.3 — Sanctions and Trade Events

| Event | Code | Brief Description |
|---|---|---|
| US Sanctions Announcement | D.3.01 | US imposes sanctions on country or entity |
| US Sanctions Removal | D.3.02 | US lifts sanctions |
| Trade War Escalation | D.3.03 | Major economy imposes tariffs in trade dispute |
| Trade War De-escalation | D.3.04 | Trade war tariffs reduced or negotiations begin |
| Trade Deal Signed | D.3.05 | Bilateral or multilateral trade agreement executed |
| Export Ban | D.3.06 | Country bans export of strategic commodity |
| Import Restriction | D.3.07 | Country imposes import quota or ban |
| Supply Chain Disruption Event | D.3.08 | Major supply chain route disrupted (Suez, Panama, etc.) |

#### D.4 — Natural and Climate Events

| Event | Code | Brief Description |
|---|---|---|
| Monsoon Onset | D.4.01 | India monsoon season begins (date relative to normal) |
| Monsoon Deficiency | D.4.02 | IMD declares monsoon deficiency >10% below normal |
| Monsoon Excess | D.4.03 | IMD declares monsoon excess |
| Drought Declaration | D.4.04 | Government declares drought in significant agricultural region |
| Flood Event | D.4.05 | Major flood disrupts economic activity in significant region |
| Cyclone Landfall | D.4.06 | Cyclone makes landfall at economic hub or port |
| Earthquake | D.4.07 | Major earthquake in economically significant location |
| Heatwave | D.4.08 | Extreme heat event disrupting labor productivity or power demand |
| Crop Failure | D.4.09 | Major crop fails in key agricultural belt |
| Rabi/Kharif Crop Estimate | D.4.10 | Government publishes advance crop production estimate |

#### D.5 — Pandemic and Health Events

| Event | Code | Brief Description |
|---|---|---|
| Pandemic Declaration | D.5.01 | WHO declares pandemic |
| Lockdown Announcement | D.5.02 | Government announces lockdown affecting economic activity |
| Lockdown Lifting | D.5.03 | Lockdown restrictions removed or eased |
| Vaccine Approval | D.5.04 | Regulatory body approves vaccine — economic normalcy signal |
| New Variant Discovery | D.5.05 | New pathogen variant detected raising concern |
| Mass Casualty Event | D.5.06 | Large-scale health event causing workforce disruption |

---

### Group E — Flow Events

*Events caused by capital movements across funds, institutions, and borders.*

#### E.1 — Foreign Institutional Flow Events

| Event | Code | Brief Description |
|---|---|---|
| FII Net Buyer Day | E.1.01 | FIIs are net buyers in Indian equities for the session |
| FII Net Seller Day | E.1.02 | FIIs are net sellers in Indian equities for the session |
| FII Single-Day Record Buy | E.1.03 | FII purchase exceeds historical daily record |
| FII Single-Day Record Sell | E.1.04 | FII sale exceeds historical daily record |
| FII Sustained Outflow | E.1.05 | FIIs net sellers for N consecutive sessions (e.g., 5+) |
| FII Sustained Inflow | E.1.06 | FIIs net buyers for N consecutive sessions |
| FII Cumulative Threshold | E.1.07 | FII flows reach defined cumulative threshold (e.g., ₹10,000 cr monthly) |
| FII Derivative Net Short | E.1.08 | FII net short in index futures exceeds threshold |
| FII Derivative Net Long | E.1.09 | FII net long in index futures — bullish signal |
| FPI Category Change | E.1.10 | FPI reclassification under SEBI regulations |

#### E.2 — Domestic Institutional Flow Events

| Event | Code | Brief Description |
|---|---|---|
| DII Net Buyer Day | E.2.01 | DIIs are net buyers in Indian equities |
| DII Net Seller Day | E.2.02 | DIIs are net sellers |
| MF SIP Inflow Record | E.2.03 | Monthly SIP collection sets new record |
| MF AUM Milestone | E.2.04 | Mutual fund industry AUM crosses new milestone |
| MF Net Redemption | E.2.05 | Mutual fund sees net redemptions exceeding gross inflows |
| MF Equity Inflow | E.2.06 | Mutual fund monthly equity category inflow data published |
| LIC Bulk Buy | E.2.07 | LIC identified as buyer of large equity stake |
| EPFO Equity Investment | E.2.08 | EPFO announces increased equity allocation |
| Insurance Fund Reallocation | E.2.09 | Major insurance company changes equity allocation |

#### E.3 — ETF and Index Flow Events

| Event | Code | Brief Description |
|---|---|---|
| ETF Creation | E.3.01 | Market maker creates new ETF units (inflow) |
| ETF Redemption | E.3.02 | Market maker redeems ETF units (outflow) |
| ETF AUM Surge | E.3.03 | Specific ETF AUM increases sharply |
| Passive Fund Rebalancing | E.3.04 | Passive fund adjusts holdings to match index changes |
| Global EM ETF Flow | E.3.05 | Significant inflow/outflow in global Emerging Markets ETFs |
| India-Focused ETF Flow | E.3.06 | Inflow/outflow specifically in India-focused ETFs |
| Smart Beta Factor Rotation | E.3.07 | Factor ETFs (value, momentum, quality) see rotation |

---

### Group F — Regulatory and Legal Events

*Events caused by regulatory authorities, courts, and legal processes.*

#### F.1 — SEBI Events

| Event | Code | Brief Description |
|---|---|---|
| SEBI Circular | F.1.01 | SEBI publishes regulatory circular affecting market participants |
| SEBI Consultation Paper | F.1.02 | SEBI issues discussion paper seeking public comment |
| SEBI Final Regulation | F.1.03 | SEBI finalizes and implements new regulation |
| SEBI Enforcement Action | F.1.04 | SEBI imposes penalty, ban, or disgorgement on entity |
| SEBI Insider Trading Case | F.1.05 | SEBI files insider trading case against individuals |
| SEBI Takeover Code Trigger | F.1.06 | Acquisition triggers mandatory open offer under Takeover Code |
| SEBI Margin Rule Change | F.1.07 | SEBI changes margin requirements for derivatives |
| SEBI Position Limit Change | F.1.08 | SEBI changes position limits for F&O |
| F&O Ban | F.1.09 | Stock enters F&O ban period (OI exceeds 95% of MWPL) |
| F&O Ban Lifted | F.1.10 | Stock exits F&O ban period |
| SEBI Board Meeting | F.1.11 | SEBI board convenes and issues decisions |
| New Product Approval | F.1.12 | SEBI approves new financial product |

#### F.2 — Other Regulatory Events

| Event | Code | Brief Description |
|---|---|---|
| CCI Approval | F.2.01 | Competition Commission approves merger/acquisition |
| CCI Rejection | F.2.02 | Competition Commission blocks merger/acquisition |
| CCI Investigation | F.2.03 | CCI initiates anti-competition investigation |
| NCLT Order | F.2.04 | National Company Law Tribunal issues order |
| NCLAT Order | F.2.05 | NCLT Appellate Tribunal issues order |
| Supreme Court Judgment | F.2.06 | Supreme Court delivers judgment affecting listed company |
| High Court Judgment | F.2.07 | High Court judgment affecting company |
| SAT Order | F.2.08 | Securities Appellate Tribunal order on SEBI matter |
| MCA Regulatory Change | F.2.09 | Ministry of Corporate Affairs amends Companies Act provisions |
| PFRDA Rule Change | F.2.10 | Pension fund regulatory change |
| IRDAI Rule Change | F.2.11 | Insurance regulatory change |
| Environmental Clearance | F.2.12 | Major project receives/loses environmental clearance |
| GST Rate Change | F.2.13 | GST Council changes rate for sector/product |
| Income Tax Rule Change | F.2.14 | Income tax rules change materially affecting sector |
| LTCG Tax Change | F.2.15 | Long-term capital gains tax rules change — affects investment behavior |

---

### Group G — News, Information, and Sentiment Events

*Events caused by information becoming publicly available.*

#### G.1 — News Events

| Event | Code | Brief Description |
|---|---|---|
| Breaking News Event | G.1.01 | High-impact news breaks during market hours |
| Pre-Market News Event | G.1.02 | Material news published before market opens |
| After-Hours News Event | G.1.03 | Material news published after market closes |
| Media Report — Positive | G.1.04 | Major media outlet publishes favorable report on company |
| Media Report — Negative | G.1.05 | Major media outlet publishes unfavorable report on company |
| Investigative Journalism Report | G.1.06 | In-depth investigative piece published (high impact on governance stocks) |
| Rumor Initiation | G.1.07 | Market rumor begins circulating |
| Rumor Confirmation | G.1.08 | Rumor confirmed by authoritative source |
| Rumor Denial | G.1.09 | Authoritative source denies rumor |
| Denial Disbelieved | G.1.10 | Market continues pricing in rumor despite denial |

#### G.2 — Analyst Events

| Event | Code | Brief Description |
|---|---|---|
| Analyst Initiation of Coverage | G.2.01 | Analyst begins covering stock for first time |
| Analyst Upgrade | G.2.02 | Rating raised (e.g., Neutral → Buy; Sell → Neutral) |
| Analyst Downgrade | G.2.03 | Rating reduced (e.g., Buy → Neutral; Neutral → Sell) |
| Target Price Increase | G.2.04 | Analyst raises price target |
| Target Price Decrease | G.2.05 | Analyst reduces price target |
| Target Price Breach | G.2.06 | Stock price reaches analyst's target — model update needed |
| Consensus Estimate Change | G.2.07 | Bloomberg/Reuters consensus estimate changes materially |
| EPS Estimate Revision | G.2.08 | Forward EPS estimates revised across broker community |
| Analyst Consensus Shift | G.2.09 | Majority of analysts shift to same direction simultaneously |
| Sector Theme Initiation | G.2.10 | Analyst publishes first sector-level thematic note |

#### G.3 — Sentiment Events

| Event | Code | Brief Description |
|---|---|---|
| Social Media Trend | G.3.01 | Stock name or sector trends on Twitter/Reddit/social media |
| Viral Video/Post | G.3.02 | Video or post about company goes viral |
| Meme Stock Event | G.3.03 | Stock targeted by retail social media community |
| Sentiment Extreme — Euphoria | G.3.04 | All sentiment indicators simultaneously at maximum bullish reading |
| Sentiment Extreme — Panic | G.3.05 | All sentiment indicators simultaneously at maximum bearish reading |
| Fear Index Threshold | G.3.06 | India VIX crosses defined fear threshold |
| Greed Index Threshold | G.3.07 | Composite market greed indicator crosses extreme level |
| Retail Investor Surge | G.3.08 | New demat account openings spike sharply |
| Options Premium Collapse | G.3.09 | Put premiums collapse despite price not rallying (complacency signal) |

---

### Group H — Alternative Data Events

*Events derived from non-traditional, non-financial data sources.*

| Event | Code | Brief Description |
|---|---|---|
| Satellite Image — Factory Activity | H.1.01 | Satellite data shows change in factory/industrial site activity |
| Satellite Image — Parking Lot | H.1.02 | Retail parking lot occupancy changes (consumer demand signal) |
| Shipping Traffic Data | H.1.03 | Port or shipping traffic data shows material change |
| Container Price Change | H.1.04 | Container freight index moves significantly |
| Air Freight Data | H.1.05 | Air cargo volumes change materially |
| Google Trends Spike | H.1.06 | Google search volumes for company/product spike |
| App Download Ranking Change | H.1.07 | Mobile app downloads rank changes significantly |
| Credit Card Spend Data | H.1.08 | Aggregated credit card spend data released |
| E-Commerce Sales Data | H.1.09 | E-commerce platforms release sales data |
| Job Posting Data | H.1.10 | LinkedIn/Naukri job posting volume changes signal company expansion/contraction |
| Patent Filing | H.1.11 | Company files material new patent |
| Regulatory Filing Keyword | H.1.12 | NLP detects unusual keyword in SEBI/BSE filing |
| Conference Transcript Analysis | H.1.13 | NLP analysis of earnings call reveals sentiment change |
| Management Tone Change | H.1.14 | NLP detects change in management communication tone |
| Supply Chain Signal | H.1.15 | Supplier/distributor data signals change in order flow |
| Footfall Data | H.1.16 | Physical retail footfall data changes materially |
| Utility Consumption | H.1.17 | Electricity/gas consumption data changes for industrial company |
| Weather Impact Data | H.1.18 | Weather events correlate with sector demand change |
| Agricultural Yield Forecast | H.1.19 | Crop yield forecast revised by meteorological agencies |
| Crop Sowing Area | H.1.20 | Agriculture Ministry publishes sowing area vs normal |

---

### Group I — AI and System Events

*Events generated internally by the AI Trading Brain system.*

#### I.1 — Model Events

| Event | Code | Brief Description |
|---|---|---|
| Model Training Completed | I.1.01 | A model finishes training cycle on new data |
| Model Validated | I.1.02 | Model passes out-of-sample validation gates |
| Model Deployed | I.1.03 | New model version activated for live use |
| Model Retrained | I.1.04 | Existing model retrained on updated dataset |
| Model Degradation Detected | I.1.05 | Model performance drops below threshold — retraining triggered |
| Model Parameters Updated | I.1.06 | Model parameters updated via incremental learning |
| Model Retired | I.1.07 | Old model version decommissioned |
| Ensemble Updated | I.1.08 | Ensemble composition or weights changed |
| Feature Importance Change | I.1.09 | Feature importance scores change materially in model update |
| Model Anomaly Detected | I.1.10 | Model produces anomalous output outside expected range |

#### I.2 — Learning Events

| Event | Code | Brief Description |
|---|---|---|
| Learning Cycle Completed | I.2.01 | Daily/weekly learning cycle finishes |
| Knowledge Item Created | I.2.02 | New validated knowledge item added to knowledge base |
| Knowledge Item Updated | I.2.03 | Existing knowledge item refreshed with new evidence |
| Knowledge Item Invalidated | I.2.04 | Knowledge item marked invalid by superseding event |
| Evidence Weight Updated | I.2.05 | Signal reliability score updated based on recent performance |
| Strategy Win Rate Updated | I.2.06 | Strategy historical win rate recalculated |
| Strategy Disabled | I.2.07 | Strategy auto-disabled due to performance threshold breach |
| Strategy Promoted | I.2.08 | Simulated strategy promoted to active deployment |
| Strategy Demoted | I.2.09 | Active strategy demoted due to underperformance |
| Learning Record Archived | I.2.10 | Historical learning record archived for reference |

#### I.3 — Signal and Decision Events

| Event | Code | Brief Description |
|---|---|---|
| Signal Generated | I.3.01 | Technical or fundamental signal produced |
| Signal Confirmed | I.3.02 | Signal confirmed by independent corroborating signal |
| Signal Expired | I.3.03 | Signal passes validity window without confirmation |
| Hypothesis Created | I.3.04 | New hypothesis formed by reasoning engine |
| Hypothesis Validated | I.3.05 | Hypothesis passes validation threshold |
| Hypothesis Invalidated | I.3.06 | Hypothesis invalidated by contradicting evidence |
| Conviction Threshold Crossed | I.3.07 | Conviction score crosses 6.5 threshold — decision zone entered |
| Decision Created | I.3.08 | Decision engine creates formal buy/sell/hold decision |
| Decision Approved | I.3.09 | Risk Guardian approves decision |
| Decision Rejected | I.3.10 | Risk Guardian rejects decision — kill switch or risk limit |
| Decision Executed | I.3.11 | Order submitted to broker |
| Decision Expired | I.3.12 | Decision not executed within validity window |

#### I.4 — Risk and Alert Events

| Event | Code | Brief Description |
|---|---|---|
| Kill Switch Activated | I.4.01 | Kill switch fires — all new positions blocked |
| Kill Switch Deactivated | I.4.02 | Kill switch condition resolved — system returns to normal |
| VIX Kill Switch | I.4.03 | India VIX exceeds 45 — kill switch triggered |
| Daily Loss Limit Hit | I.4.04 | Daily loss exceeds 2% of portfolio NAV — trading halted |
| Position Stop Loss Hit | I.4.05 | Individual position reaches stop loss level |
| Position Target Hit | I.4.06 | Individual position reaches profit target |
| Portfolio Drawdown Alert | I.4.07 | Portfolio drawdown exceeds defined threshold |
| Risk Limit Breach | I.4.08 | Any defined risk metric exceeds its limit |
| Correlation Alert | I.4.09 | Portfolio correlation rises above diversification threshold |
| Concentration Alert | I.4.10 | Sector or stock concentration exceeds limit |
| Margin Adequacy Alert | I.4.11 | Available margin falls below safe buffer |
| System Cycle Completed | I.4.12 | Full analysis cycle finishes successfully |
| System Cycle Failed | I.4.13 | System cycle terminates with error |
| Data Feed Failure | I.4.14 | Market data feed becomes unavailable |
| Data Feed Restored | I.4.15 | Market data feed restored after interruption |
| Latency Breach | I.4.16 | Layer execution time exceeds critical threshold |
| Audit Trail Written | I.4.17 | Complete audit record written for completed cycle |
| Telegram Notification Sent | I.4.18 | Telegram alert dispatched to operator |
| Backtest Completed | I.4.19 | Backtest run finishes — results available |
| Walk-Forward Test Completed | I.4.20 | Walk-forward test cycle completed |

---

### Group J — Lifecycle and Calendar Events

*Events defined by the passage of time and scheduled milestones.*

| Event | Code | Brief Description |
|---|---|---|
| Trading Day Start | J.1.01 | New trading day begins |
| Trading Day End | J.1.02 | Trading day closes |
| Month End | J.1.03 | Calendar month end — rebalancing, reporting events cluster |
| Quarter End | J.1.04 | Financial quarter ends — earnings season begins |
| Financial Year End | J.1.05 | Indian financial year ends (March 31) |
| New Financial Year Start | J.1.06 | April 1 — new tax, policy, and budget parameters effective |
| Options Expiry Week | J.1.07 | Week containing weekly options expiry |
| Settlement Day | J.1.08 | T+1 settlement obligations fall due |
| Index Review Announcement | J.1.09 | Index provider announces upcoming rebalancing decisions |
| Earnings Season Start | J.1.10 | Major companies begin reporting quarterly results |
| Earnings Season Peak | J.1.11 | Peak of results announcements |
| Earnings Season End | J.1.12 | Last major company reports for the quarter |
| AGM Season | J.1.13 | Annual General Meeting season (post-Q4 results, April-June) |
| Budget Day | J.1.14 | Union Budget presentation day |
| Fed Meeting Week | J.1.15 | Week of FOMC meeting — global risk positioning event |
| MPC Meeting Week | J.1.16 | Week of RBI MPC meeting — rate sensitive positioning event |
| G7/G20 Summit | J.1.17 | Major global economic summit |
| MSCI Rebalancing Date | J.1.18 | Scheduled MSCI rebalancing effective date |
| Circuit Expiry Assessment | J.1.19 | Exchange assesses and potentially changes circuit limits |
| Lease/Concession Expiry | J.1.20 | Major business concession or license expiry |

---

### Group K — Social and Behavioral Events

*Events driven by collective human psychology and behavior.*

| Event | Code | Brief Description |
|---|---|---|
| Panic Selling Event | K.1.01 | Irrational mass selling driven by fear |
| FOMO-Driven Rally | K.1.02 | Price rise accelerated by Fear of Missing Out |
| Margin Call Cascade | K.1.03 | Sequential margin calls force selling across multiple accounts |
| Short Squeeze | K.1.04 | Heavily shorted stock rises sharply forcing short covering |
| Dead Cat Bounce | K.1.05 | Brief recovery in a falling stock before resuming decline |
| Capitulation Event | K.1.06 | Final wave of forced selling — often marks a bottom |
| Narrative Shift | K.1.07 | Dominant market narrative changes (e.g., "soft landing" to "recession") |
| Regime Change Recognition | K.1.08 | Market consensus recognizes a new market regime |
| Consensus Trade Crowding | K.1.09 | Too many participants in the same trade (crowded trade risk) |
| Smart Money Divergence | K.1.10 | Institutional behavior diverges materially from retail behavior |

---

### Group L — Environmental, Social, and Governance (ESG) Events

| Event | Code | Brief Description |
|---|---|---|
| ESG Rating Change | L.1.01 | Company receives new ESG rating or existing rating revised |
| Carbon Emission Disclosure | L.1.02 | Company publishes carbon footprint data |
| Environmental Violation | L.1.03 | Company cited for environmental regulation breach |
| BRSR Publication | L.1.04 | Business Responsibility and Sustainability Report published |
| Social Controversy | L.1.05 | Company embroiled in social controversy (labor, community) |
| Supply Chain ESG Event | L.1.06 | Supplier ESG violation affects company reputation |
| Board Diversity Milestone | L.1.07 | Company crosses board gender diversity threshold |
| Executive Pay Controversy | L.1.08 | Excessive executive compensation creates governance concern |
| Environmental Clearance Event | L.1.09 | Project receives or loses environmental clearance |
| ESG-Driven Fund Exclusion | L.1.10 | ESG fund excludes company from universe |

---

### Group M — Global Contagion and Cross-Market Events

*Events where stress in one market transmits to another.*

| Event | Code | Brief Description |
|---|---|---|
| Global Risk-Off Event | M.1.01 | Investors globally move to safe havens — EM equities sell off |
| Global Risk-On Event | M.1.02 | Risk appetite returns — EM equities and high-beta assets rally |
| Asian Contagion | M.1.03 | Financial stress originating in Asian market spreads to India |
| EM Currency Crisis | M.1.04 | Emerging market currency crisis creates contagion to India |
| US Market Sell-Off | M.1.05 | Major US equity sell-off (>2% DJIA/S&P) — India follow-through expected |
| European Sovereign Crisis | M.1.06 | European sovereign debt stress creates global risk-off |
| Credit Contagion Event | M.1.07 | Credit market stress spreads to equity market |
| DXY Breakout | M.1.08 | US Dollar Index breaks key level — strong impact on EM |
| DXY Breakdown | M.1.09 | USD weakens materially — positive for EM flows |
| Carry Trade Unwinding | M.1.10 | Yen carry trade or similar unwind creates EM volatility |

---

### Group N — Composite and Multi-Source Events

*Events that are themselves combinations of simpler events.*

| Event | Code | Brief Description |
|---|---|---|
| Black Swan Event | N.1.01 | Extreme, unprecedented, high-impact event outside normal probability distributions |
| Compound Crisis | N.1.02 | Multiple crisis events occurring simultaneously or in rapid succession |
| Perfect Storm | N.1.03 | Multiple negative factors aligning simultaneously (pandemic + rate hike + geopolitical) |
| Catalyst Cluster | N.1.04 | Multiple positive events aligning (earnings beat + upgrade + inclusion + sector rally) |
| Earnings Cycle Inflection | N.1.05 | Broad market earnings revision cycle reverses direction |
| Macro-Micro Alignment | N.1.06 | Macro environment aligns with individual company thesis simultaneously |
| Technical-Fundamental Convergence | N.1.07 | Technical breakout and fundamental catalyst occur together |
| Synchronized Sector Rally | N.1.08 | Multiple sectors rally simultaneously with high breadth |
| Multi-Asset Contagion | N.1.09 | Stress simultaneously in equities, bonds, currencies, and commodities |
| Liquidity-Solvency Crisis Transition | N.1.10 | Liquidity crisis transitions to solvency crisis (systemic escalation) |


---

## PART III — COMPLETE EVENT DEFINITIONS

*For every critical event: 20+ attributes. Organized by category. Full prose and table treatment.*

---

### EVT-001 — QUARTERLY RESULTS RELEASE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-001 / A.1.01 |
| **Name** | Quarterly Results Release |
| **Definition** | A company publishes its quarterly financial results (P&L, Balance Sheet, Cash Flow Statement) on the stock exchange platform within the SEBI-mandated timeframe after the quarter end |
| **Why It Exists** | Quarterly results are the primary mechanism by which company performance is transmitted to market participants. They are the most significant recurring source of fundamental information in the investment universe. |
| **Trigger** | Passage of 45 days from quarter end (SEBI mandated deadline); voluntary early publication |
| **Preconditions** | Quarter must have ended; board meeting must have approved the accounts; statutory and secretarial filings must be current |
| **Source** | Listed Company, BSE/NSE Exchange Filing System |
| **Affected Entities** | The reporting company's equity, all derivative instruments, analyst models, institutional portfolios holding the stock, sector peers |
| **Information Produced** | Revenue, EBITDA, PAT, EPS, margins, balance sheet metrics, cash flow statement, segment performance |
| **Knowledge Produced** | Whether earnings trend is accelerating, decelerating, or inflecting; management quality signals from disclosed numbers; sector health signal |
| **State Changes** | Company entity: financial metrics updated; Analyst models: estimates revised; Hypothesis entities: supported, weakened, or invalidated; Conviction scores: recalculated |
| **Typical Duration** | Instantaneous (publication event); effects propagate over 1-5 trading sessions |
| **Severity** | Critical — every quarter is a potential thesis confirmation or invalidation |
| **Probability** | Certain (4 times per year per company) |
| **Frequency** | 4× per year per listed company; thousands of events each earnings season |
| **Dependencies** | Board meeting approval; accounting completion; auditor review (for annual) |
| **Relationships** | ANNOUNCES → Earnings; EXPLAINS → Stock price movement; SUPPORTS or INVALIDATES → Existing hypothesis; TRIGGERS → Analyst estimate revision, Knowledge item update |
| **Lifecycle** | Filed → Published → Processed by system → Evidence assembled → Conviction updated → Decision reviewed |
| **Examples** | HDFC Bank Q3 FY26 Results: PAT ₹17,820 cr (beat estimate of ₹16,500 cr by 8%); Margin expansion 40bps — triggered bullish conviction update |
| **Risks** | Restatement risk; accounting manipulation; cherry-picked reporting periods; exceptional items obscuring underlying performance |
| **Importance** | Critical |

---

### EVT-002 — EARNINGS BEAT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-002 / A.1.03 |
| **Name** | Earnings Beat |
| **Definition** | The company's reported EPS, Revenue, or EBITDA exceeds the median consensus estimate by a defined material threshold (typically ≥5% for revenue, ≥7% for EPS) |
| **Why It Exists** | The gap between expectation and reality is the single most powerful short-term driver of stock price movement. An earnings beat signals that fundamental reality is better than the market priced in. |
| **Trigger** | Publication of quarterly results with actuals exceeding threshold above consensus |
| **Preconditions** | Consensus estimate must exist; results must be published; beat threshold must be defined and documented |
| **Source** | Derived event: calculated by comparing A.1.01 output against analyst consensus |
| **Affected Entities** | Stock (price), Options chain (IV crush, price rise), Analyst models (estimate revision), Hypothesis entities (confirmation/strengthening) |
| **Information Produced** | Beat magnitude (₹ and %); which metrics beat (revenue, EBITDA, PAT); quality of beat (recurring vs exceptional) |
| **Knowledge Produced** | Earnings momentum signal; management credibility signal; competitive position improvement signal |
| **State Changes** | Stock entity: price expected to gap up; Conviction entity: score increases; Hypothesis entity: CONFIRMED or STRENGTHENED |
| **Typical Duration** | Event is instantaneous; market impact lasts 1-10 sessions depending on beat quality |
| **Severity** | High (1-5% price move typically); Critical if large beat (>15%) |
| **Probability** | Roughly 50-55% historically (slight upward analyst bias means companies beat more often than miss) |
| **Frequency** | Per company: 4× per year; across market: ~2,000 events per earnings season |
| **Dependencies** | Consensus estimate quality; absence of exceptional items inflating the beat |
| **Relationships** | CONFIRMS → Bullish hypothesis; STRENGTHENS → Upward trend conviction; TRIGGERS → Analyst upgrade, Target price increase; CAUSES → Gap up open |
| **Lifecycle** | Results published → Beat detected → Signal generated → Evidence weight added → Conviction threshold checked → Decision reviewed |
| **Examples** | Infosys Q2 FY26: Revenue ₹40,986 cr vs estimate ₹39,500 cr (+3.8%); EPS ₹23.4 vs estimate ₹21.8 (+7.3%) — triggered BUY decision at conviction 7.1 |
| **Risks** | Beat driven by one-time items; management sand-bagging (lowering estimates before results); currency tailwind masking underlying weakness |
| **Importance** | Critical |

---

### EVT-003 — EARNINGS MISS

| Attribute | Value |
|---|---|
| **Event Code** | EVT-003 / A.1.04 |
| **Name** | Earnings Miss |
| **Definition** | The company's reported EPS, Revenue, or EBITDA falls short of the median consensus estimate by a defined material threshold |
| **Why It Exists** | Earnings misses reveal that underlying business performance is weaker than priced in. The severity of the miss and the quality of the accompanying guidance determines whether it is a temporary setback or a thesis-invalidating event. |
| **Trigger** | Publication of quarterly results with actuals below threshold below consensus |
| **Preconditions** | Consensus estimate must exist; results published |
| **Source** | Derived: comparison of A.1.01 output against analyst consensus |
| **Affected Entities** | Stock (price), Options (IV spike pre-results; IV crush post-results if guidance is maintained), Analyst models, Hypothesis entities |
| **Information Produced** | Miss magnitude; specific metric that missed; management explanation; guidance direction |
| **Knowledge Produced** | Business deterioration signal; management credibility challenge; sector health signal (does peer also miss?) |
| **State Changes** | Stock: price expected to gap down; Conviction: score decreases; Hypothesis: WEAKENED or INVALIDATED |
| **Typical Duration** | Instantaneous event; impact persists until next results or guidance event |
| **Severity** | High to Critical depending on miss magnitude and guidance |
| **Probability** | ~45% (complementary to earnings beat probability) |
| **Frequency** | ~1,800 events per earnings season |
| **Dependencies** | Quality of consensus; whether guidance is given for future quarters |
| **Relationships** | WEAKENS or INVALIDATES → Bullish hypothesis; SUPPORTS → Bearish hypothesis; TRIGGERS → Analyst downgrade, Target price cut; CAUSES → Gap down open |
| **Lifecycle** | Results published → Miss detected → Signal generated → Contradicting evidence added → Conviction threshold recalculated → Position reviewed |
| **Examples** | TATAMOTORS Q1 FY26: EBITDA margin 7.8% vs estimate 9.2% — miss invalidated "margin recovery" hypothesis; triggered EXIT decision |
| **Risks** | Management explanation may be credible; miss driven by accounting change not operations; sector-wide miss reduces severity |
| **Importance** | Critical |

---

### EVT-004 — PROFIT WARNING

| Attribute | Value |
|---|---|
| **Event Code** | EVT-004 / A.1.13 |
| **Name** | Profit Warning |
| **Definition** | Management proactively announces before the scheduled results date that upcoming quarterly earnings will materially miss consensus expectations, typically by >10% |
| **Why It Exists** | Regulatory and ethical requirement to disclose price-sensitive information immediately when it becomes known — regardless of whether the results date has arrived. Demonstrates management transparency, though the underlying news is negative. |
| **Trigger** | Management determination that reported results will miss significantly; SEBI disclosure obligation activated |
| **Preconditions** | Quarter must be substantially complete; management must have reasonable estimate of outcome; event must be material enough to warrant disclosure |
| **Source** | Management of listed company |
| **Affected Entities** | Stock (typically -5% to -20% gap down); bonds; analyst models; hypothesis entities; any portfolio holding the stock |
| **Information Produced** | Revised earnings guidance; reason for deterioration; whether it is one-time or recurring |
| **Knowledge Produced** | Severe negative signal; management credibility assessment; business model risk revelation |
| **State Changes** | Stock: immediate sharp price decline; Hypothesis: INVALIDATED; Conviction for long position: collapses below exit threshold |
| **Typical Duration** | Instantaneous announcement; impact persists for 1-4 weeks until full results |
| **Severity** | Critical — among the most negative events in the corporate calendar |
| **Probability** | Low (2-5% of reporting periods per company) but high impact |
| **Frequency** | ~50-100 events per quarter across listed universe |
| **Dependencies** | Materiality threshold; SEBI disclosure rules |
| **Relationships** | INVALIDATES → Bullish hypothesis; CONFIRMS → Bearish hypothesis; TRIGGERS → Exit decision, Stop loss review; TRANSMITS_TO → Sector peers (fear of contagion) |
| **Lifecycle** | Problem identified by management → Board approved disclosure → Exchange filing → System alert → Conviction collapse → Exit decision |
| **Examples** | Company X files exchange intimation: "Expected PAT for Q3 FY26 to be 35% below consensus due to raw material cost spike and factory disruption" |
| **Risks** | Over-reaction (if miss is one-time); market pricing in permanent damage from temporary event |
| **Importance** | Critical |

---

### EVT-005 — PROMOTER PLEDGE INVOCATION

| Attribute | Value |
|---|---|
| **Event Code** | EVT-005 / A.5.16 |
| **Name** | Promoter Pledge Invocation |
| **Definition** | A lender invokes pledged promoter shares — converting pledged collateral to owned shares — due to promoter's failure to meet margin call or loan obligation. The lender sells these shares in the market. |
| **Why It Exists** | Pledge invocation reveals that promoter is facing acute financial stress sufficient to cause collateral foreclosure. It is one of the most negative governance events, signaling extreme distress. |
| **Trigger** | Promoter fails to restore margin on pledged loan when stock price falls below trigger level |
| **Preconditions** | Pledges must exist; stock price must have fallen below lender's trigger level; promoter must have failed to deposit additional margin |
| **Source** | SEBI Disclosure via BSE/NSE exchange filing |
| **Affected Entities** | Company equity (forced selling pressure); promoter shareholding entity; lending institution; all investors in the stock |
| **Information Produced** | Quantity of shares invoked; lender name; remaining pledge percentage; implied promoter financial stress |
| **Knowledge Produced** | Extreme governance distress signal; implicit view that promoter believes stock will recover (or has no choice); company debt structure risk |
| **State Changes** | Promoter shareholding entity: % ownership decreases; Market: selling pressure increases; Conviction for long: drops to critical level |
| **Typical Duration** | Invocation event is instantaneous; selling pressure cascades over days-weeks |
| **Severity** | Critical |
| **Probability** | Low (rare event), but conditional probability rises sharply when pledge > 30% and stock has fallen 25%+ |
| **Frequency** | Cluster events during market downturns; isolated events during company-specific crises |
| **Dependencies** | Pledge existence; stock price decline; lender action |
| **Relationships** | CAUSES → Forced selling cascade; INVALIDATES → Management credibility hypothesis; TRIGGERS → Kill switch assessment; TRANSMITS_TO → Sector peers (fear) |
| **Lifecycle** | Pledge trigger breached → Margin call issued → Promoter fails to respond → Lender invokes → SEBI disclosure filed → System alert → Conviction collapse → Position exit |
| **Examples** | Zee Entertainment (2019): Essel Group pledged shares invoked when stock fell 70%; created panic selling spiral |
| **Risks** | False positive: legitimate pledge management vs. distress; lender cooperation with promoter creating orderly unwinding |
| **Importance** | Critical |

---

### EVT-006 — RBI REPO RATE DECISION

| Attribute | Value |
|---|---|
| **Event Code** | EVT-006 / C.2.02-C.2.04 |
| **Name** | RBI Repo Rate Decision |
| **Definition** | The Reserve Bank of India's Monetary Policy Committee announces its decision on the policy repo rate at the conclusion of a bi-monthly MPC meeting |
| **Why It Exists** | The repo rate is the anchor of the Indian financial system's cost of capital. Every borrowing rate, lending rate, bond yield, and equity valuation is connected to the repo rate through transmission mechanisms. |
| **Trigger** | Scheduled bi-monthly MPC meeting concluding; Governor reading the policy statement |
| **Preconditions** | MPC meeting must have convened and concluded; 6 members must have voted; majority determines decision |
| **Source** | Reserve Bank of India (RBI) |
| **Affected Entities** | All bonds (yield change immediate); all equities (via cost of capital); INR (currency impact); all rate-sensitive stocks (banks, NBFCs, real estate, auto) |
| **Information Produced** | New repo rate level; vote count; policy stance; inflation and GDP projections; forward guidance |
| **Knowledge Produced** | Rate cycle direction; RBI's assessment of growth-inflation trade-off; transmission timeline to economy |
| **State Changes** | Bond entity: yield adjusts immediately; MCLR entity: changes within 1 month; Real estate sector entity: affordability metric changes |
| **Typical Duration** | Announcement is instantaneous; first-order effects within minutes; second-order effects over 1-3 months |
| **Severity** | Critical — affects ALL assets simultaneously |
| **Probability** | Certain (scheduled 6× per year) but direction is uncertain |
| **Frequency** | 6× per year |
| **Dependencies** | CPI trajectory; GDP growth; global central bank actions (Fed); INR stability |
| **Relationships** | CAUSES → MCLR change; TRANSMITS_TO → Bond yields, Equity valuations, INR; INFLUENCES → Bank NIM, NBFC borrowing cost, Real estate demand; TRIGGERS → Sector rotation event |
| **Lifecycle** | MPC meets (2-3 days) → Decision taken → Statement released → Governor press conference → Markets react → Transmission to economy over weeks-months |
| **Examples** | RBI October 2026 MPC: Rate cut 25bps to 6.25%; accommodative stance maintained; triggered rally in rate-sensitive stocks (real estate +4%, NBFCs +3%) |
| **Risks** | Market may have already priced in decision (no reaction); surprise decision in either direction creates outsized move |
| **Importance** | Critical |

---

### EVT-007 — MERGER ANNOUNCEMENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-007 / A.4.01 |
| **Name** | Merger Announcement |
| **Definition** | Two companies publicly announce their intent to merge into a single entity, specifying the merger ratio (shares of acquiring entity per share of target) and expected completion timeline |
| **Why It Exists** | Mergers fundamentally alter the identity and structure of two entities. The announcement event is when the market prices in the probability, terms, and synergy potential of the proposed merger. |
| **Trigger** | Board of both companies approving the merger and filing exchange disclosure |
| **Preconditions** | Board approval; due diligence completion; merger structure defined; SEBI Takeover Code compliance; exchange disclosure |
| **Source** | Both merging companies via BSE/NSE exchange filing |
| **Affected Entities** | Both company equities; all derivatives on both; all portfolios holding either; sector peers (competitive landscape change) |
| **Information Produced** | Merger ratio; implied premium (for target); combined entity structure; expected synergies; regulatory approvals required |
| **Knowledge Produced** | Value creation or destruction probability; synergy feasibility; management quality (ability to integrate); sector consolidation signal |
| **State Changes** | Target entity: price typically jumps to near merger price; Acquirer entity: price may fall (dilution risk) or rise (synergy confidence); Sector entity: competitive dynamics change |
| **Typical Duration** | Announcement is instant; merger process typically 6-18 months |
| **Severity** | Critical for both companies; High for sector |
| **Probability** | Low (rare for any specific company pair) but multiple across market |
| **Frequency** | ~20-50 material merger announcements per year in Indian markets |
| **Dependencies** | CCI approval; NCLT approval; shareholder approval; SEBI compliance |
| **Relationships** | TRIGGERS → Open offer (if applicable); CAUSES → Arbitrage opportunity; INFLUENCES → Sector competitive dynamics; SUPERSEDES → Both companies' independent strategies |
| **Lifecycle** | Board approval → Exchange announcement → Shareholder vote → CCI/NCLT/SEBI approval → Merger effective date → Share exchange |
| **Examples** | HDFC Bank-HDFC Ltd merger 2022: announced March 2022; 18-month process; created world's 4th largest bank by market cap |
| **Risks** | Regulatory rejection; shareholder opposition; integration failure; synergy disappointment |
| **Importance** | Critical |

---

### EVT-008 — INDEX INCLUSION

| Attribute | Value |
|---|---|
| **Event Code** | EVT-008 / B.5.02 |
| **Name** | Index Inclusion |
| **Definition** | A stock is officially added to a major index (NIFTY 50, NIFTY Bank, NIFTY Midcap 150, MSCI India, etc.) as part of a periodic rebalancing, requiring all index-tracking funds to buy the stock in defined proportions |
| **Why It Exists** | Index inclusion creates a mandatory, price-insensitive buying demand that is entirely mechanical and predictable. This creates a temporary but powerful demand-supply imbalance. |
| **Trigger** | Index provider's periodic review committee decision; stock meeting eligibility criteria |
| **Preconditions** | Stock must meet free-float, liquidity, and market cap criteria; current constituent must have been excluded |
| **Source** | NSE Indices, BSE Indices, MSCI, FTSE Russell |
| **Affected Entities** | Newly included stock; all index-tracking ETFs; all passive funds; removed stock (which faces selling); other borderline inclusion candidates |
| **Information Produced** | Weight in index; effective date; estimated demand from passive funds |
| **Knowledge Produced** | Institutional validation (meeting index criteria); passive demand estimate; liquidity improvement signal |
| **State Changes** | Stock entity: price typically rises 5-15% post-announcement; Passive fund entities: portfolio allocation changed; Related ETFs: composition updated |
| **Typical Duration** | Announcement to effective date: ~4-6 weeks (for NIFTY); MSCI: ~3 months between announcement and effective date |
| **Severity** | High for included stock; potentially Critical for MSCI inclusion (global fund flows) |
| **Probability** | Low for any specific stock; 1-3 inclusions per NIFTY review |
| **Frequency** | NIFTY 50: 2× per year; MSCI: 2× per year |
| **Dependencies** | Free-float calculation; liquidity history; market cap ranking |
| **Relationships** | TRIGGERS → Mandatory passive fund buying; CAUSES → Temporary demand-supply imbalance; INFLUENCES → Stock liquidity permanently; SIGNALS → Institutional recognition event |
| **Lifecycle** | NSE circular announced → Effective date approaches → ETF rebalancing executes → Price settles → New weight in all index-tracking products |
| **Examples** | Adani Enterprises NIFTY 50 inclusion 2022: ~₹2,500 crore estimated passive demand created; stock rallied 12% in 2 weeks post-announcement |
| **Risks** | Pre-inclusion rally leaving no post-inclusion return; reverse on exclusion |
| **Importance** | Critical |

---

### EVT-009 — CREDIT RATING DOWNGRADE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-009 / A.6.02 |
| **Name** | Credit Rating Downgrade |
| **Definition** | A credit rating agency officially lowers the credit rating of an issuer or specific instrument — reflecting deterioration in assessed creditworthiness |
| **Why It Exists** | Credit ratings determine the borrowing cost and investability of debt instruments. A downgrade triggers mandatory institutional selling (if an instrument falls below investment grade), increases borrowing costs, and signals business deterioration. |
| **Trigger** | Rating committee decision following periodic review or triggered by a specific negative event |
| **Preconditions** | Rating review must have been conducted; negative factors must exceed threshold for downgrade |
| **Source** | CRISIL, ICRA, CARE, India Ratings (domestic); Moody's, S&P, Fitch (international) |
| **Affected Entities** | Company equity; all outstanding bonds; commercial paper; bank loan portfolios; all debt fund portfolios holding the instrument |
| **Information Produced** | New rating; reasons for downgrade; outlook (stable/negative); specific metrics driving the decision |
| **Knowledge Produced** | Credit quality deterioration signal; management execution failure signal; industry stress signal (if widespread downgrades) |
| **State Changes** | Bond/CP entity: yield increases immediately (price falls); Equity entity: sentiment negative; Debt fund entities: position must be reviewed for mandate compliance |
| **Typical Duration** | Instantaneous announcement; market impact within sessions; refinancing impact over weeks-months |
| **Severity** | Critical for below-investment-grade; High for within investment grade |
| **Probability** | Low per instrument per year; conditional probability rises with deteriorating financials |
| **Frequency** | ~200-500 downgrades per year across rated universe |
| **Dependencies** | Financial metric triggers; management credibility; sector conditions |
| **Relationships** | WEAKENS → Debt serviceability hypothesis; INVALIDATES → Investment grade thesis; TRIGGERS → Institutional forced selling (if falls below BBB-/Baa3); TRANSMITS_TO → Higher borrowing cost |
| **Lifecycle** | Negative watch/outlook placed → Review triggered → Rating committee meets → Downgrade announced → Market reprices → Issuer must disclose → Refinancing plans reviewed |
| **Examples** | ILFS: CRISIL downgraded from AA+ to D in September 2018 — triggered ₹1 lakh crore NBFC crisis |
| **Risks** | Rating lag — agencies often downgrade after problems are visible in market prices; notch vs. cliff-edge impact |
| **Importance** | Critical |

---

### EVT-010 — IPO LISTING

| Attribute | Value |
|---|---|
| **Event Code** | EVT-010 / A.7.07 |
| **Name** | IPO Listing |
| **Definition** | A company's shares begin trading on a stock exchange for the first time, following the completion of the Initial Public Offering process |
| **Why It Exists** | Listing converts a private company into a public one, enabling price discovery, liquidity, and access to institutional capital. The listing event is when the market's first independent price opinion is revealed. |
| **Trigger** | SEBI clearance of prospectus + successful IPO subscription + exchange approval of listing application |
| **Preconditions** | DRHP filed and cleared; subscription window opened and closed; allotment completed; exchange listing approval granted |
| **Source** | The listing company; BSE/NSE |
| **Affected Entities** | New equity entity created; investor portfolios (IPO allottees have new position); competitor entities (new public comparable created) |
| **Information Produced** | IPO price; listing price; listing day range; subscription level (oversubscription ratio); allotment details |
| **Knowledge Produced** | Market's initial value judgment; demand quality (QIB vs HNI vs Retail subscription ratio); comparable valuation benchmarks |
| **State Changes** | New stock entity: transitions from private to publicly traded; Market entity: new constituent added to investable universe |
| **Typical Duration** | Listing day event is one trading session; price discovery continues for weeks |
| **Severity** | High — creates new entity in system |
| **Probability** | Depends on market conditions (more IPOs in bull markets) |
| **Frequency** | ~80-150 main board IPOs per year in India |
| **Dependencies** | SEBI approval; market conditions; subscription levels |
| **Relationships** | CREATES → New equity entity; INITIATES → LISTED_ON relationship; ENABLES → All derivative relationships on the stock |
| **Lifecycle** | DRHP filing → SEBI approval → Roadshow → Subscription → Allotment → Listing |
| **Examples** | LIC IPO listing May 2022: Listed at ₹872 vs IPO price ₹949 (-8.1%); largest IPO in Indian history |
| **Risks** | Listing below IPO price damages retail investor confidence; grey market premium may not predict listing performance |
| **Importance** | Critical (new entity creation) |

---

### EVT-011 — INDIA VIX SPIKE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-011 / B.4.18 |
| **Name** | India VIX Spike |
| **Definition** | India VIX — the measure of expected 30-day volatility derived from NIFTY options prices — rises sharply above a defined threshold (30 = elevated fear; 40 = crisis mode; 45 = kill switch level) |
| **Why It Exists** | Options prices reflect collective market fear. When traders pay high premiums for puts (protection), VIX rises. VIX spikes are real-time signals of market stress, fear, and the potential for extreme price moves. |
| **Trigger** | Options market participants collectively paying elevated premiums — driven by fear of large adverse price moves |
| **Preconditions** | NIFTY options must be actively traded; fear event or uncertainty must be in the market |
| **Source** | NSE Options pricing (NIFTY Near-Term and Next-Term contracts) |
| **Affected Entities** | All NIFTY options (pricing); all equity positions (exit signals); system kill switch entity; strategy selection |
| **Information Produced** | VIX level; rate of rise; comparative level vs historical |
| **Knowledge Produced** | Collective market fear quantification; probability distribution widening; potential for extreme moves |
| **State Changes** | Kill switch entity: activated at VIX > 45; Strategy selection: shifts to defensive; Position sizing: reduced |
| **Typical Duration** | VIX spikes are sharp (hours to days); elevated VIX periods last weeks-months |
| **Severity** | Critical (when > 45); High (when 30-45); Moderate (when 20-30) |
| **Probability** | VIX > 30: ~5-8% of trading days historically; VIX > 40: ~2%; VIX > 45: <1% |
| **Frequency** | Significant spikes: ~2-5 per year; extreme spikes: ~0.5 per year |
| **Dependencies** | Underlying NIFTY price stability; macroeconomic events; FII positioning |
| **Relationships** | TRIGGERS → Kill switch (at >45); INFLUENCES → Options premiums; SIGNALS → Risk-off positioning; CORRELATES_WITH → FII selling |
| **Lifecycle** | Fear catalyst occurs → Options put buying surges → VIX rises → System detects threshold → Kill switch evaluated → Defensive mode activated |
| **Examples** | COVID-19 lockdown March 2020: India VIX touched 86 — highest ever; NIFTY fell 38%; system kill switch would have fired at 45 |
| **Risks** | VIX can stay elevated while markets stabilize (VIX is a leading indicator, but timing is uncertain) |
| **Importance** | Critical (system safety mechanism trigger) |

---

### EVT-012 — MARKET CIRCUIT BREAKER

| Attribute | Value |
|---|---|
| **Event Code** | EVT-012 / B.4.15-B.4.17 |
| **Name** | Market Circuit Breaker |
| **Definition** | The exchange imposes a trading halt across the entire market when the NIFTY 50 falls by 10% (Level 1 — 45 min halt), 15% (Level 2 — 1 hr 45 min halt), or 20% (Level 3 — entire day halt) |
| **Why It Exists** | Circuit breakers prevent panic cascade selling from accelerating into a complete market failure. They provide a structured pause for rationality to reassert itself. |
| **Trigger** | NIFTY 50 price falling below defined threshold from previous day's close (10%, 15%, 20%) |
| **Preconditions** | NIFTY 50 must have fallen to trigger level during trading hours |
| **Source** | NSE/BSE automated circuit breaker mechanism |
| **Affected Entities** | All listed equities (trading halted); all derivatives (trading halted); all pending orders (cancelled or held); all portfolios (positions cannot be reduced) |
| **Information Produced** | Trigger level; time of halt; expected resumption time; resumption price band |
| **Knowledge Produced** | Extreme market stress signal; systemic risk event confirmed; historical rarity of event |
| **State Changes** | Exchange entity: trading suspended; All position entities: cannot be closed; Panic-selling process: interrupted |
| **Typical Duration** | L1: 45 minutes; L2: 1 hour 45 minutes; L3: remainder of trading day |
| **Severity** | Critical — represents rare extreme market event |
| **Probability** | L1: ~5 events since 2001; L2: ~2 events; L3: 0 events in India |
| **Frequency** | Extremely rare — approximately 1 L1 event per 3-5 years |
| **Dependencies** | Severe market shock; no countervailing buyer support |
| **Relationships** | TRIGGERS → Regulatory review; CAUSES → Liquidity freeze; SIGNALS → Systemic risk; ACTIVATES → System kill switch |
| **Lifecycle** | NIFTY drops 10% → Automated halt → Exchange notifies participants → Halt period → Resumption → Continued trading (or further halt if losses continue) |
| **Examples** | March 13, 2020: NSE triggered L1 circuit breaker as NIFTY fell 10% due to COVID-19 panic |
| **Risks** | Gap-down on resumption if selling pressure persists; illiquidity trap during halt |
| **Importance** | Critical |

---

### EVT-013 — FII SUSTAINED OUTFLOW

| Attribute | Value |
|---|---|
| **Event Code** | EVT-013 / E.1.05 |
| **Name** | FII Sustained Outflow |
| **Definition** | Foreign Institutional Investors are net sellers of Indian equities for N consecutive trading sessions (threshold: typically 5+ consecutive net sell days or cumulative outflow exceeding ₹5,000 crore) |
| **Why It Exists** | FII flows are the single largest source of foreign capital in Indian equities. Sustained outflows indicate a structural shift in foreign allocation away from India — driven by global risk-off, currency concerns, or India-specific issues. |
| **Trigger** | N consecutive net sell days by FII category; or defined cumulative threshold breached |
| **Preconditions** | FII data must be available from exchange (published daily); threshold parameters defined |
| **Source** | NSE/BSE daily FII/FPI flow data |
| **Affected Entities** | NIFTY 50 (direct); high-FII-owned stocks (disproportionate impact); INR (selling pressure); DXY relationship |
| **Information Produced** | Cumulative net flow; daily flow trend; FII derivative positioning change; sectors most affected |
| **Knowledge Produced** | Global risk appetite for India; India's relative attractiveness vs. other EM; FII conviction level |
| **State Changes** | Market entity: selling pressure sustained; INR entity: depreciating pressure; High-FII-holding stocks: elevated selling pressure |
| **Typical Duration** | Event is a multi-day pattern; cumulates over 1-4 weeks typically |
| **Severity** | High (> ₹5,000 cr); Critical (> ₹20,000 cr sustained) |
| **Probability** | ~20% of trading months historically show sustained outflows |
| **Frequency** | 3-5 significant outflow periods per year |
| **Dependencies** | Global risk-off; USD strength; India-specific negative events; EM reallocation |
| **Relationships** | TRANSMITS_TO → NIFTY level, INR depreciation; CAUSES → Selling pressure on high-FII stocks; INFLUENCES → DII counter-buying strength; CORRELATES_WITH → DXY strength |
| **Lifecycle** | Global catalyst → FII allocation review → Systematic selling begins → N-day threshold crossed → System alert → Defensive adjustment |
| **Examples** | Jan-Mar 2022: FII sold ₹1.06 lakh crore net equity — largest outflow in history; NIFTY fell 15% |
| **Risks** | DII counter-buying can absorb FII selling (NIFTY resilience); outflow driven by global factor unrelated to India fundamentals |
| **Importance** | Critical |

---

### EVT-014 — US FEDERAL RESERVE RATE DECISION

| Attribute | Value |
|---|---|
| **Event Code** | EVT-014 / C.4.01-C.4.03 |
| **Name** | US Federal Reserve Rate Decision |
| **Definition** | The US Federal Reserve's Federal Open Market Committee (FOMC) announces its decision on the federal funds rate — the most influential single financial event in global markets |
| **Why It Exists** | The US dollar is the global reserve currency and the Fed funds rate is the global risk-free rate benchmark. Every asset class, every country's bond yield, every currency exchange rate, and every equity valuation globally is connected to the Fed funds rate. |
| **Trigger** | Scheduled FOMC meeting (8× per year) concluding |
| **Preconditions** | 12 FOMC members must have met; majority vote on rate decision |
| **Source** | US Federal Reserve |
| **Affected Entities** | Globally: all bond markets; all equity markets; all currency markets; all commodity markets; specifically India: NIFTY, INR, FII flows, RBI policy decisions |
| **Information Produced** | New rate level; dot plot (rate projections); Powell press conference tone; forward guidance |
| **Knowledge Produced** | Global interest rate cycle direction; USD outlook; global liquidity conditions |
| **State Changes** | Global bond yields: reprice immediately; USD: strengthens on hike; EM equities: typically sell off on hike cycle; All global financial entities: recalibrate based on new rate |
| **Typical Duration** | Instantaneous announcement; full global repricing over 1-5 sessions |
| **Severity** | Critical (global impact) |
| **Probability** | Certain (8× per year); direction uncertain |
| **Frequency** | 8× per year |
| **Dependencies** | US CPI, PCE; US jobs market; Fed mandate (inflation + employment) |
| **Relationships** | TRANSMITS_TO → DXY, Global bonds, EM currencies, FII flows to India; INFLUENCES → RBI MPC decision; CAUSES → EM capital flow shift; CORRELATES_WITH → India VIX |
| **Lifecycle** | Pre-meeting data → Fed communication → FOMC decision → Press conference → Global market reaction → EM specific reaction (India 1-2 sessions lag) |
| **Examples** | Fed March 2022 rate hike cycle start: 75bps hike in June 2022 triggered ₹50,000 cr FII outflow from India; NIFTY fell 12% over 3 months |
| **Risks** | Market over-reacts to known information; "buy the rumor sell the news" dynamic |
| **Importance** | Critical |

---

### EVT-015 — KILL SWITCH ACTIVATED

| Attribute | Value |
|---|---|
| **Event Code** | EVT-015 / I.4.01 |
| **Name** | Kill Switch Activated |
| **Definition** | The AI Trading Brain's risk guardian activates the system-wide kill switch — blocking all new position entries and requiring position review — due to a defined crisis condition being met |
| **Why It Exists** | The kill switch is the ultimate safety mechanism. When market conditions reach defined extreme levels, the system's ability to reason reliably is compromised, and protective action is mandatory. |
| **Trigger** | Any of: India VIX > 45; Daily portfolio loss > 2% NAV; Market circuit breaker L1 triggered; Manual operator override |
| **Preconditions** | Kill switch condition must be actively monitored; trigger condition must be verified (not a data error) |
| **Source** | RiskGuardian layer (Layer 9) of AI Trading Brain |
| **Affected Entities** | All pending decisions; all in-process signal chains; system cycle behavior; operator notification |
| **Information Produced** | Which condition triggered; trigger level vs threshold; system status |
| **Knowledge Produced** | System is in protective mode; no new directional exposure to be added |
| **State Changes** | System entity: mode changes to DEFENSIVE; Decision queue: cleared of pending buy decisions; Telegram: alert sent to operator |
| **Typical Duration** | Active until kill switch condition resolves; typically hours to days |
| **Severity** | Critical — highest priority system event |
| **Probability** | Per kill switch condition (VIX > 45: <1% of trading days) |
| **Frequency** | Designed to be rare; fires approximately 2-4 times per year under normal market conditions |
| **Dependencies** | Kill switch conditions must be met; data feed must be reliable |
| **Relationships** | OVERRIDES → All pending buy decisions; TRIGGERS → Operator notification; ACTIVATES → Defensive portfolio stance |
| **Lifecycle** | Condition monitored → Threshold breached → Kill switch fires → Operator alerted → System locks new entries → Condition resolves → Kill switch deactivated |
| **Examples** | March 2020 COVID crash: India VIX > 45 for 8 consecutive sessions — system would have blocked all new longs; saved from 38% NIFTY fall |
| **Risks** | False trigger on data error (spike in VIX due to data feed issue); missing recovery if kill switch stays active too long |
| **Importance** | Critical |

---

### EVT-016 — UNION BUDGET

| Attribute | Value |
|---|---|
| **Event Code** | EVT-016 / C.3.01 |
| **Name** | Union Budget |
| **Definition** | The annual presentation of India's central government budget in Parliament by the Finance Minister — detailing revenue estimates, expenditure plans, fiscal deficit targets, tax changes, and sector allocations for the coming financial year |
| **Why It Exists** | The Union Budget is the single most comprehensive policy event in India's economic calendar. It changes tax rates, sector allocations, investment priorities, and regulatory frameworks — affecting every entity in the investment universe simultaneously. |
| **Trigger** | Parliamentary calendar; traditionally first Tuesday of February |
| **Preconditions** | Government must be in power; Finance Ministry must have completed consultation process |
| **Source** | Government of India, Ministry of Finance |
| **Affected Entities** | All sectors (budget allocations change); all tax-paying entities; all stock valuations (tax changes); bond market (fiscal deficit target); INR |
| **Information Produced** | Revenue estimates; expenditure plans; fiscal deficit; capex target; sector allocations; tax rate changes |
| **Knowledge Produced** | Government fiscal priorities; growth vs. deficit trade-off; political economy signals; investment themes for the year |
| **State Changes** | Tax-impacted sectors: immediate repricing; High-government-spend sectors: opportunity signals; Fiscal deficit: affects bond yield expectations |
| **Typical Duration** | Instantaneous presentation; market digestion period of 1-2 weeks |
| **Severity** | Critical — annual sector-defining event |
| **Probability** | Certain (annual) |
| **Frequency** | 1× per year |
| **Dependencies** | Government stability; fiscal space; global economic conditions |
| **Relationships** | TRIGGERS → Sector rotation; CAUSES → Tax-driven demand/supply shifts; INFLUENCES → Capital allocation across sectors; SIGNALS → Government economic priorities for FY |
| **Lifecycle** | Pre-budget speculation → Budget presentation → Immediate reaction → Sector analysis → 1-week digestion → Portfolio repositioning |
| **Examples** | Budget FY24: Capital gains tax rate change announced — triggered immediate market volatility; Infrastructure allocation record ₹11.1 lakh crore — positive for capital goods, cement |
| **Risks** | Political constraints leading to populist budget; short-term fiscal measures without structural reforms |
| **Importance** | Critical |

---

### EVT-017 — SECTOR ROTATION EVENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-017 / B.4.11 |
| **Name** | Sector Rotation Event |
| **Definition** | Measurable, sustained capital movement from one sector cluster to another — visible in relative price performance, volume data, and derivative positioning over a defined multi-session period |
| **Why It Exists** | Capital in equity markets is not static — it allocates toward sectors where growth expectations improve and away from sectors where they deteriorate. Detecting rotation early is among the highest-value activities in investment intelligence. |
| **Trigger** | Definable catalyst (earnings, macro data, policy) causing re-rating of one sector relative to another |
| **Preconditions** | Catalyst must be present; relative performance divergence must exceed threshold; confirmation over multiple sessions required |
| **Source** | Derived event: detected by system monitoring sector indices and flows |
| **Affected Entities** | Sectors rotating out (selling pressure); sectors rotating into (buying pressure); all portfolios with sector exposure |
| **Information Produced** | Which sectors are gaining/losing allocation; magnitude of rotation; catalyst identification; duration so far |
| **Knowledge Produced** | Market's current sector preference; economic cycle position; risk appetite level |
| **State Changes** | Sector entities: relative performance changes; Portfolio entities: sector weights must be reviewed; Strategy entities: sector-agnostic strategies may need adjustment |
| **Typical Duration** | Rotation events last weeks to months |
| **Severity** | High |
| **Probability** | Certain (sector rotation is a permanent feature of equity markets) |
| **Frequency** | 3-5 major rotation events per year |
| **Dependencies** | Economic cycle; earnings cycle; monetary policy cycle; global capital flows |
| **Relationships** | TRIGGERED_BY → Rate changes, earnings surprises, macro data; AFFECTS → All sector entities simultaneously; SIGNALS → Economic cycle position |
| **Lifecycle** | Catalyst event → Early mover rotation → Confirmation over sessions → Broader market recognition → Momentum builds → Rotation matures → Next rotation begins |
| **Examples** | 2021: IT sector rotation-in post-COVID (global digital spend surge); 2022: IT rotation-out (rate hikes compress valuation); 2023: Capital goods rotation-in (government capex cycle) |
| **Risks** | False rotation signal; rotation driven by technical factors (index rebalancing) not fundamentals |
| **Importance** | Critical |

---

### EVT-018 — GLOBAL RISK-OFF EVENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-018 / M.1.01 |
| **Name** | Global Risk-Off Event |
| **Definition** | A macro or geopolitical shock causes a broad, coordinated global movement of capital from risk assets (equities, EM currencies, commodities) to safe-haven assets (USD, JPY, Gold, US Treasuries) |
| **Why It Exists** | Global capital is connected. A shock in one part of the world creates defensive positioning everywhere. Understanding and detecting risk-off events early is critical because India, as an emerging market, is disproportionately affected. |
| **Trigger** | Major unexpected negative event: war, financial crisis, pandemic, political shock, Fed hawkish surprise |
| **Preconditions** | Event must be of sufficient magnitude to override normal asset return correlations |
| **Source** | Global macroeconomic/geopolitical environment |
| **Affected Entities** | Global equities (sell-off); EM currencies (depreciation); Gold (rally); USD (strengthens); FII flows to India (reversal) |
| **Information Produced** | Magnitude of global equity decline; USD/JPY movement; VIX (US and India) spike; gold rally magnitude |
| **Knowledge Produced** | Severity of global risk aversion; India's correlation to global risk in this event; expected FII response |
| **State Changes** | All risk asset entities: repricing; Portfolio entity: defensive posture required; System entity: heightened monitoring mode |
| **Typical Duration** | Initial shock: hours to days; sustained risk-off: weeks to months |
| **Severity** | Critical (when accompanied by >5% global equity decline) |
| **Probability** | ~4-6 significant risk-off events per year globally |
| **Frequency** | 4-6× per year |
| **Dependencies** | Surprise element; severity of triggering event; global system fragility |
| **Relationships** | TRANSMITS_TO → India equities, INR, FII flows; CAUSES → India VIX spike; TRIGGERS → Defensive positioning; INFLUENCES → RBI decision urgency |
| **Lifecycle** | Shock event → Safe haven buying → EM sell-off → India VIX spike → FII selling India → NIFTY falls → Stabilization → Recovery (timing uncertain) |
| **Examples** | COVID March 2020: NIFTY -38%; Russia-Ukraine Feb 2022: NIFTY -15%; Fed rate hike cycle 2022: NIFTY -16% |
| **Risks** | India may decouple from global risk-off; DII support limits downside |
| **Importance** | Critical |

---

### EVT-019 — LEARNING CYCLE COMPLETED

| Attribute | Value |
|---|---|
| **Event Code** | EVT-019 / I.2.01 |
| **Name** | Learning Cycle Completed |
| **Definition** | The AI Trading Brain completes its daily/weekly learning cycle — updating strategy performance metrics, refreshing evidence weights, creating/updating knowledge items, and retraining models where required |
| **Why It Exists** | Learning is what converts experience into intelligence. Without the learning cycle, the system's knowledge base would decay as market conditions evolve. The learning event is the mechanism by which the system improves over time. |
| **Trigger** | Scheduled: end of trading day (daily cycle); end of week (weekly deep cycle) |
| **Preconditions** | Sufficient new data must exist; learning system must have access to outcome records |
| **Source** | AI Trading Brain Learning System (Layer 13) |
| **Affected Entities** | All strategy entities (performance updated); all evidence weight entities (accuracy updated); all knowledge items (staleness checked); model entities (parameters updated) |
| **Information Produced** | Strategy win rates for period; evidence type accuracy statistics; knowledge items created/retired; model performance metrics |
| **Knowledge Produced** | Which strategies performed above/below threshold; which signal types proved reliable; what market conditions existed in the period |
| **State Changes** | Strategy entities: win rate updated; evidence weight entities: reliability score updated; knowledge base: expanded with new validated items |
| **Typical Duration** | ~15-60 minutes for daily cycle; ~2-4 hours for weekly cycle |
| **Severity** | High (system evolution event) |
| **Probability** | Certain (scheduled) |
| **Frequency** | Daily + weekly deep cycle |
| **Dependencies** | Completed trade records; market data for the period; system availability |
| **Relationships** | UPDATES → All strategy performance entities; CREATES or UPDATES → Knowledge items; TRIGGERS → Model retraining if degradation detected; PRODUCES → Learning record |
| **Lifecycle** | Cycle scheduled → Data collected → Strategies evaluated → Evidence weights updated → Knowledge base updated → Models checked → Report generated → Operator notified |
| **Examples** | Daily learning: Momentum strategy win rate for week = 67% (above 50% threshold — strategy maintained); TATASTEEL lead-bellwether signal accuracy = 71% — weight increased |
| **Risks** | Learning from noise (overfitting to recent regime); insufficient sample in short cycles |
| **Importance** | Critical (system evolution mechanism) |

---

### EVT-020 — CONVICTION THRESHOLD CROSSED

| Attribute | Value |
|---|---|
| **Event Code** | EVT-020 / I.3.07 |
| **Name** | Conviction Threshold Crossed |
| **Definition** | The aggregated evidence score for a hypothesis crosses the 6.5/10 threshold, moving from "under analysis" to "decision zone" — triggering the decision engine to evaluate whether to act |
| **Why It Exists** | The conviction threshold is the bridge between analysis and action. Without a defined threshold, the system either acts too early (low conviction, high error) or too late (analysis paralysis). The threshold event is the moment analysis converts to decision. |
| **Trigger** | Evidence assembly produces a weighted score ≥ 6.5; or new corroborating evidence pushes existing score above threshold |
| **Preconditions** | Hypothesis must exist; sufficient evidence items must be assembled; scoring algorithm must be calibrated |
| **Source** | AI Trading Brain Debate and Decision layer (Layer 10) |
| **Affected Entities** | The hypothesis entity; the decision entity (created); the strategy entity; the portfolio entity (potential change) |
| **Information Produced** | Conviction score; evidence composition; bull case/bear case balance; dissenting agents' views |
| **Knowledge Produced** | Analysis has crossed the threshold of actionability; the burden of proof for action is met |
| **State Changes** | Hypothesis entity: transitions from ANALYSIS to DECISION phase; Decision entity: created and queued; Risk Guardian: consulted |
| **Typical Duration** | Instantaneous crossing; decision process typically 5-30 minutes |
| **Severity** | High — creates potential position change |
| **Probability** | Approximately 20-40 threshold crossings per day across all monitored hypotheses |
| **Frequency** | Multiple per cycle |
| **Dependencies** | Evidence quality; scoring algorithm calibration; threshold setting |
| **Relationships** | TRIGGERS → Decision creation; ACTIVATES → Risk Guardian review; PRODUCES → Trade recommendation |
| **Lifecycle** | Evidence accumulates → Scoring computes → Threshold crossed → Decision engine activated → Risk Guardian consulted → Decision approved or rejected → Execution or hold |
| **Examples** | TATASTEEL hypothesis: Technical breakout (weight 0.8) + Earnings beat (weight 1.2) + Sector momentum (weight 0.9) + FII buying (weight 0.7) = 3.6 of 4-factor max → Conviction 7.2 → Threshold crossed → BUY decision created |
| **Risks** | Threshold may be set too low (too many trades) or too high (analysis paralysis); correlated evidence items inflate apparent conviction |
| **Importance** | Critical |

---

### EVT-021 — SHORT COVERING

| Attribute | Value |
|---|---|
| **Event Code** | EVT-021 / B.3.04 |
| **Name** | Short Covering |
| **Definition** | A measurable reduction in short open interest accompanied by a rising price — indicating that traders who were short (expecting price to fall) are closing their positions by buying back |
| **Why It Exists** | Short covering creates a self-reinforcing price rise: as shorts cover (buy), price rises; rising price forces more shorts to cover; creating a momentum event. Detecting short covering early provides entry opportunity. |
| **Trigger** | OI decreases by defined threshold (e.g., 10%+) while price rises by defined threshold (e.g., 2%+) in a session |
| **Preconditions** | Significant short OI must pre-exist; price must have been declining for shorts to be in the money; catalyst must emerge |
| **Source** | Derived: OI data + price data from NSE F&O |
| **Affected Entities** | The stock/index entity; all short position holders; derivatives chain |
| **Information Produced** | OI decrease quantity; price rise magnitude; remaining short OI; implied further covering potential |
| **Knowledge Produced** | Negative catalysts for the stock have reduced; short sellers are conceding; remaining shorts are vulnerable to squeeze |
| **State Changes** | Stock entity: price rising; OI entity: decreasing; Short position entities: being closed |
| **Typical Duration** | Single session to 3-5 sessions depending on catalyst and remaining OI |
| **Severity** | Moderate to High (can produce 5-15% move in concentrated short positions) |
| **Probability** | Moderate — occurs after periods of sustained short build-up |
| **Frequency** | Multiple per week across the F&O universe |
| **Dependencies** | Existing short OI; positive catalyst; sufficient liquidity |
| **Relationships** | TRIGGERS → Price momentum; SIGNALS → Negative thesis collapse; CREATES → Long entry opportunity |
| **Lifecycle** | Short position built → Negative thesis → Catalyst reversal → Shorts cover (buy) → Price rises → More covering forced → OI normalizes |
| **Examples** | TATAMOTORS Jan 2024: High short OI + JLR quarterly beat → massive short covering → 8% single-day rise |
| **Risks** | Dead cat bounce: price rises temporarily then continues declining; covering may be partial |
| **Importance** | High |

---

### EVT-022 — OPEN INTEREST BUILD-UP

| Attribute | Value |
|---|---|
| **Event Code** | EVT-022 / B.3.01 |
| **Name** | Open Interest Build-Up |
| **Definition** | Futures or options open interest increases significantly in a defined period, indicating new money entering the derivatives market in a specific direction |
| **Why It Exists** | Open interest is the measure of outstanding derivative contracts. When OI builds with rising price, it indicates bullish conviction with fresh buying (not just short covering). When OI builds with falling price, it indicates bearish conviction with fresh short building. |
| **Trigger** | OI increases by defined threshold (e.g., 15%+ in a week) without proportional decrease |
| **Preconditions** | Derivative contract must exist on the stock/index; liquidity must be sufficient |
| **Source** | NSE F&O OI data |
| **Affected Entities** | The underlying equity; derivatives chain; portfolio exposure levels |
| **Information Produced** | OI level; OI change; price direction (determines bullish vs bearish interpretation) |
| **Knowledge Produced** | Fresh money conviction signal; directional positioning confidence |
| **State Changes** | Derivatives entity: OI position updated; Risk entity: exposure concentration monitored |
| **Typical Duration** | Build-up occurs over days to weeks |
| **Severity** | Moderate to High |
| **Frequency** | Multiple per day across F&O universe |
| **Dependencies** | New money entering; confidence in directional thesis |
| **Relationships** | SIGNALS → Conviction in direction; CREATES → Squeeze risk (if OI very high); CORRELATES_WITH → Price momentum |
| **Lifecycle** | Fresh money enters → OI increases → System detects build-up → Direction assessed → Signal generated |
| **Examples** | NIFTY pre-election 2024: OI in Calls (bullish) builds massively → market anticipating political stability → large pre-election rally |
| **Risks** | OI build-up can be two-sided (simultaneous long and short adding) — direction must be confirmed by price |
| **Importance** | High |

---

### EVT-023 — GEOPOLITICAL ESCALATION

| Attribute | Value |
|---|---|
| **Event Code** | EVT-023 / D.2.01-D.2.08 |
| **Name** | Geopolitical Escalation |
| **Definition** | A sudden increase in geopolitical tensions — war, military strike, sanctions, border conflict — that materially increases global uncertainty and creates risk-off positioning in financial markets |
| **Why It Exists** | Geopolitical risk is a permanent feature of the investment universe. When geopolitical events escalate unexpectedly, they disrupt supply chains, increase commodity prices, alter FX flows, and trigger risk-off positioning globally. |
| **Trigger** | Military action, sanctions announcement, nuclear threat, or significant diplomatic breakdown |
| **Preconditions** | Baseline geopolitical tension must exist; escalation must represent material increase in risk |
| **Source** | Global news, government announcements, military reports |
| **Affected Entities** | Defense sector equities; commodity entities (oil, gold); FX entities; bond entities; EM equities globally |
| **Information Produced** | Nature of event; involved parties; severity; affected trade routes/resources |
| **Knowledge Produced** | Affected sectors and supply chains; global risk-off probability; inflation risk from disruption |
| **State Changes** | Affected sector entities: repricing; Global risk entities: elevated; Portfolio defensive assets: increased weight |
| **Typical Duration** | Initial shock: hours to days; lasting effect: weeks to months |
| **Severity** | Critical (nuclear threat, major war); High (regional conflict, sanctions) |
| **Frequency** | Several per year at various severity levels |
| **Dependencies** | Surprise element; economic interconnectedness of affected parties |
| **Relationships** | TRANSMITS_TO → Oil price, Safe haven assets, EM capital flows; CAUSES → Inflation risk; TRIGGERS → Risk-off positioning |
| **Lifecycle** | Escalation event → News breaks → Global markets react → India impact assessed → Portfolio adjustment |
| **Examples** | Russia-Ukraine war Feb 2022: Oil spike, European equities -15%, India NIFTY -12% over 3 months; FII sold ₹41,000 crore |
| **Risks** | Markets may quickly price in and recover; India may be less affected than other markets |
| **Importance** | Critical |

---

### EVT-024 — MODEL DEGRADATION DETECTED

| Attribute | Value |
|---|---|
| **Event Code** | EVT-024 / I.1.05 |
| **Name** | Model Degradation Detected |
| **Definition** | An AI/ML model used by the system produces predictions that perform below a defined accuracy threshold for a defined period — triggering automatic retraining initiation |
| **Why It Exists** | Models degrade when market regimes shift. A model trained on trending market data produces poor signals in ranging markets. Without automated degradation detection, the system would continue using outdated models, producing low-quality decisions. |
| **Trigger** | Model accuracy drops below threshold for N consecutive evaluations; or rolling accuracy falls below threshold |
| **Preconditions** | Model must be live; evaluation framework must be active; outcome data must be available |
| **Source** | AI Trading Brain Learning System evaluation module |
| **Affected Entities** | The specific model entity; all signals derived from that model; strategies dependent on model outputs |
| **Information Produced** | Current accuracy vs. threshold; recent miss patterns; proposed retraining schedule |
| **Knowledge Produced** | Current regime may have shifted; model assumptions may no longer hold |
| **State Changes** | Model entity: status → DEGRADING; Dependent signals: confidence reduced; Retraining: scheduled |
| **Typical Duration** | Detection is instantaneous; retraining takes 15-60 minutes |
| **Severity** | High |
| **Frequency** | ~5-10 model degradation events per year per model |
| **Dependencies** | Sufficient out-of-sample outcomes; evaluation framework calibration |
| **Relationships** | TRIGGERS → Model retraining; REDUCES → Confidence in model-derived signals; ALERTS → System operator |
| **Lifecycle** | Accuracy monitored → Threshold breach detected → Degradation alert → Retraining queued → Retrained on recent data → Validated → Redeployed |
| **Examples** | Momentum regime model: after market turns ranging, rolling 30-day accuracy drops from 72% to 51% → degradation detected → retrained on recent data → accuracy returns to 68% |
| **Risks** | False positive degradation during temporary regime shift that reverses; overfitting in retraining |
| **Importance** | High |

---

### EVT-025 — BOND AUCTION

| Attribute | Value |
|---|---|
| **Event Code** | EVT-025 / C.2.15 |
| **Name** | Government Securities (G-Sec) Auction |
| **Definition** | The Government of India, through the RBI, conducts a weekly auction to sell government bonds to primary dealers — establishing the market price (yield) for government paper at the prevailing demand |
| **Why It Exists** | G-Sec auctions are the primary funding mechanism for government spending. The auction results (particularly the cut-off yield) reveal market demand for government debt and signal the direction of long-term interest rates. |
| **Trigger** | Weekly scheduled auction (typically Fridays); or special notification auctions |
| **Preconditions** | Government must have borrowing need; RBI must have issued auction notification |
| **Source** | RBI on behalf of Government of India |
| **Affected Entities** | All bond prices (benchmark setting); bank bond portfolios; insurance company portfolios; bond fund NAVs |
| **Information Produced** | Auction cut-off yield; bid-to-cover ratio (demand gauge); deviation from current market yield |
| **Knowledge Produced** | Market's view of long-term interest rates; government borrowing program acceptance; bond supply absorption capacity |
| **State Changes** | Bond yield entities: repriced based on cut-off; Bank HTM portfolios: new position added; Market benchmark: updated |
| **Typical Duration** | Auction process: 2-3 hours; market impact: rest of session |
| **Severity** | High (weekly market mover for bond market) |
| **Frequency** | Weekly (~52× per year) |
| **Dependencies** | Government borrowing program; RBI liquidity conditions; global yields |
| **Relationships** | SETS → Benchmark yield; INFLUENCES → Bank NIM, Equity valuations (via discount rate); TRANSMITS_TO → All bond prices |
| **Lifecycle** | Notification → Bid submission (primary dealers) → Auction cut-off set → Results announced → Market repricing |
| **Examples** | 10-year G-Sec cut-off: 7.25% (above market 7.18%) → bearish signal; bid-to-cover 1.2 (weak demand) → negative for rates |
| **Risks** | Devolvement (when bids insufficient — RBI absorbs unsold bonds): negative signal for fiscal credibility |
| **Importance** | High |


---

### EVT-026 — STRATEGY PROMOTED TO LIVE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-026 / I.2.08 |
| **Name** | Strategy Promoted to Live |
| **Definition** | A simulated or backtested strategy passes all validation gates (win rate ≥50%, Sharpe ratio >0.8, max drawdown <15%, walk-forward test passing) and is promoted to active deployment in the live portfolio |
| **Why It Exists** | Strategy promotion is the highest-value event in the AI system lifecycle. It represents successful completion of the research-to-deployment pipeline and addition of a new source of alpha. |
| **Trigger** | Strategy passes all 6 validation stages: Backtest → Walk-Forward Test → Cross-Market → Monte Carlo → Sensitivity → Regime |
| **Preconditions** | Backtest completed with minimum 3 years data; WFT passing; all promotion gates met |
| **Source** | AI Trading Brain Validation Engine (Layer 16) |
| **Affected Entities** | The strategy entity (status change); portfolio entity (new strategy allocation); ResearchLab entity (pipeline updated) |
| **Information Produced** | Strategy parameters; validation results; promotion date; initial capital allocation |
| **Knowledge Produced** | New alpha source validated; specific market conditions where strategy is expected to work |
| **State Changes** | Strategy entity: status → LIVE; Portfolio entity: new strategy component; ResearchLab: pipeline updated |
| **Typical Duration** | Promotion event is instantaneous; strategy deployment is gradual (capital allocated over first week) |
| **Severity** | High (system evolution event) |
| **Frequency** | ~4-8 promotions per year |
| **Dependencies** | All validation gates met; sufficient simulated track record |
| **Relationships** | VALIDATES → Strategy performance claims; TRIGGERS → Capital allocation; CREATES → New decision-producing pathway |
| **Lifecycle** | Research generates strategy → Backtest → WFT → Full validation → Promotion gate → LIVE deployment |
| **Examples** | Sector momentum strategy (3-month): Backtest Sharpe 1.2, WFT Sharpe 0.92, MaxDD 8.4% — promoted to live with 15% portfolio allocation |
| **Risks** | Regime change immediately post-promotion; overfitting not caught by validation |
| **Importance** | High |

---

### EVT-027 — STRATEGY DISABLED

| Attribute | Value |
|---|---|
| **Event Code** | EVT-027 / I.2.07 |
| **Name** | Strategy Disabled |
| **Definition** | An active trading strategy is automatically disabled because its rolling performance falls below defined minimum thresholds — removing it from active signal generation |
| **Why It Exists** | Markets change. A strategy that worked in 2022 may not work in 2025. Auto-disabling prevents the system from persisting with strategies that are no longer generating alpha — protecting capital and maintaining system quality. |
| **Trigger** | Rolling win rate drops below 40% for 20+ trades; or Sharpe below 0.3 for 3 months; or max drawdown exceeds 15% |
| **Preconditions** | Strategy must be live; sufficient recent trades for evaluation |
| **Source** | Learning System (Layer 13) performance monitor |
| **Affected Entities** | The strategy entity; portfolio capital allocation; active signal queue |
| **Information Produced** | Strategy performance metrics; reason for disabling; last performance period |
| **Knowledge Produced** | Market regime is no longer favorable for this strategy; timing for potential re-deployment |
| **State Changes** | Strategy entity: status → DISABLED; Portfolio: capital freed from that strategy allocation |
| **Typical Duration** | Instantaneous; capital reallocation over next cycle |
| **Severity** | High |
| **Frequency** | ~4-6 per year |
| **Dependencies** | Sufficient live trade history; evaluation thresholds calibrated |
| **Relationships** | CAUSED_BY → Strategy performance deterioration; TRIGGERS → Capital reallocation; PRODUCES → Learning record |
| **Lifecycle** | Performance monitored → Threshold breached → Auto-disable → Operator notified → Strategy enters remediation or permanent archive |
| **Examples** | Mean-reversion strategy: win rate dropped to 38% over 25 trades during strong trending market → auto-disabled → re-evaluated in next regime |
| **Importance** | High |

---

### EVT-028 — BREAKOUT EVENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-028 / B.1.10 |
| **Name** | Breakout Event |
| **Definition** | A stock or index price closes above a significant resistance level — on elevated volume — that had rejected multiple prior attempts, creating a change in market structure |
| **Why It Exists** | Resistance levels represent price zones where sellers have previously overwhelmed buyers. A successful breakout above resistance means the balance of supply and demand has shifted — sellers have been exhausted, and buyers have taken control. |
| **Trigger** | Daily close above defined resistance; volume > 1.5× 20-day average; close within top 20% of day's range |
| **Preconditions** | Defined resistance level must exist (minimum 2 prior tests); volume confirmation required |
| **Source** | Derived: price data analysis by technical system |
| **Affected Entities** | The stock/index entity; all pending technical hypotheses; conviction scores |
| **Information Produced** | Breakout level; volume vs. average; close position within range; number of prior resistance tests |
| **Knowledge Produced** | Market structure has shifted; prior resistance now becomes support; momentum likely to follow |
| **State Changes** | Technical structure entity: support-resistance levels reset; Hypothesis entity: CONFIRMED; Signal entity: entry signal generated |
| **Typical Duration** | Event is session-based; validity typically 10-20 sessions |
| **Severity** | High |
| **Frequency** | Multiple per week across the universe |
| **Dependencies** | Volume confirmation; prior resistance quality; broader market conditions |
| **Relationships** | CONFIRMS → Bullish hypothesis; TRIGGERS → Entry signal; SUPPORTS → Momentum thesis |
| **Lifecycle** | Resistance identified → Multiple rejections → Consolidation → Breakout session → Volume confirmation → Signal generated → Entry decision |
| **Examples** | TATASTEEL: Broke 6-month resistance at ₹165 on 3× average volume; prior 4 tests rejected → system generated BUY signal; conviction 6.8 |
| **Risks** | False breakout (closes back below resistance next session); low volume breakout |
| **Importance** | High |

---

### EVT-029 — NATURAL DISASTER EVENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-029 / D.4.04-D.4.09 |
| **Name** | Natural Disaster Event |
| **Definition** | A significant natural event (cyclone, earthquake, flood, drought) causing measurable economic disruption to a specific geographic region or sector |
| **Why It Exists** | Natural disasters create sudden, unexpected disruptions to supply chains, agricultural output, infrastructure, and human capital — with immediate and lasting effects on specific sectors and companies. |
| **Trigger** | Occurrence of event above defined damage threshold; government declaration |
| **Preconditions** | Event must occur; damage must be above materiality threshold |
| **Source** | Government agencies, IMD, media |
| **Affected Entities** | Insurance companies; agriculture sector; logistics; power sector; FMCG; regional companies |
| **Information Produced** | Geographic scope; estimated damage; affected industries; recovery timeline |
| **Knowledge Produced** | Sector impact map; insurance claims expectation; government relief spending signal |
| **State Changes** | Affected sector entities: earnings estimates revised; Insurance entities: claims liability increased |
| **Typical Duration** | Event: hours to days; economic impact: weeks to quarters |
| **Severity** | Variable (cyclone in major port: Critical; local flood: Moderate) |
| **Frequency** | Multiple per year in India (cyclone season, monsoon floods, etc.) |
| **Dependencies** | Geographic scope; sector concentration in affected area |
| **Relationships** | CAUSES → Supply disruption; INFLUENCES → Agricultural output estimates; TRIGGERS → Government spending event |
| **Lifecycle** | Event → Damage assessment → Sector impact mapped → Insurance claims estimated → Government relief announced → Recovery path |
| **Examples** | Cyclone Biparjoy June 2023: Gujarat coast; cement, chemicals, power sector disrupted; Ambuja, UltraTech saw 1-2 week production halt |
| **Importance** | Variable (context-dependent) |

---

### EVT-030 — BUYBACK ANNOUNCEMENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-030 / A.3.10 |
| **Name** | Buyback Announcement |
| **Definition** | A company announces a plan to repurchase its own shares from the open market or via tender offer, at a premium to the current market price, reducing the float |
| **Why It Exists** | Buybacks signal management's belief that the stock is undervalued. They return capital to shareholders, reduce shares outstanding (boosting EPS), and demonstrate confidence in future cash flows. |
| **Trigger** | Board approval and exchange filing |
| **Preconditions** | Company must have excess cash; board approval; SEBI compliance |
| **Source** | Company exchange filing |
| **Affected Entities** | Stock entity (price accretive); EPS entity (increases as shares reduce); Float entity (decreases) |
| **Information Produced** | Buyback size; price or price range; buyback period; method (open market vs tender) |
| **Knowledge Produced** | Management's confidence in company value; capital allocation discipline; expected EPS accretion |
| **State Changes** | Stock entity: price support from buyback; Float entity: reduces; EPS entity: improves |
| **Typical Duration** | Announcement to completion: 3-12 months |
| **Severity** | Moderate to High (depending on size relative to market cap) |
| **Frequency** | ~30-60 buyback announcements per year in India |
| **Dependencies** | Excess cash; management confidence; regulatory compliance |
| **Relationships** | SIGNALS → Undervaluation belief by management; CAUSES → EPS accretion; TRIGGERS → Price support |
| **Lifecycle** | Board approves → Exchange filing → Open market buyback begins → Monthly disclosure → Completion |
| **Examples** | Infosys buyback FY26: ₹10,000 crore at ₹2,000 cap price (10% premium) — accretive to EPS; stock traded near buyback price providing floor |
| **Importance** | High |

---

### EVT-031 — ELECTION RESULT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-031 / D.1.02 |
| **Name** | National Election Result |
| **Definition** | India's national or state election results are declared, determining which party/coalition forms the government and the resulting economic policy direction |
| **Why It Exists** | Elections determine the government, which determines fiscal policy, tax policy, sector allocations, and regulatory stance. The combination of: (a) which party wins, (b) the size of majority, and (c) market expectations determines market reaction. |
| **Trigger** | Election Commission of India declares results after vote counting |
| **Preconditions** | Election must have been conducted; counting completed |
| **Source** | Election Commission of India |
| **Affected Entities** | All sectors (policy-sensitive); PSU equities; defense; infrastructure; fiscal deficit entity; currency entity |
| **Information Produced** | Winning party/coalition; seat count; majority strength; policy implications |
| **Knowledge Produced** | Economic policy direction for next 5 years; sector winners and losers; fiscal stance |
| **State Changes** | Policy environment entity: updated; PSU sector: repriced based on divestment prospects; Capex cycle: outlook revised |
| **Typical Duration** | Result day is instantaneous; market digestion 1-2 weeks; policy realization 3-6 months |
| **Severity** | Critical |
| **Probability** | Certain (every 5 years for general election) |
| **Frequency** | General: 5-year cycle; State: multiple per year |
| **Dependencies** | Polling accuracy; coalition dynamics; economic conditions at time of election |
| **Relationships** | DETERMINES → Policy environment; CAUSES → Sector rotation; TRIGGERS → Capital reallocation |
| **Lifecycle** | Exit polls → Opening of counting → Trend clear → Final result → Government formation → Policy announcements |
| **Examples** | General Election 2024: Modi government returns with reduced majority → NIFTY initially sold off 4% on uncertainty → recovered → settled flat as policy continuity confirmed |
| **Importance** | Critical |

---

### EVT-032 — MANAGEMENT CHANGE (CEO/MD)

| Attribute | Value |
|---|---|
| **Event Code** | EVT-032 / A.5.01-A.5.02 |
| **Name** | CEO/MD Change |
| **Definition** | The Chief Executive Officer or Managing Director of a listed company leaves (resignation or retirement) and/or a new CEO/MD is appointed |
| **Why It Exists** | The CEO is the single most important person in a company's success. Management changes signal strategy shifts, potential governance issues, or phase transitions in company lifecycle. Unexpected CEO departures are among the highest-severity unexpected company events. |
| **Trigger** | Board decision; regulatory filing requirement (material price-sensitive information) |
| **Preconditions** | Board must approve change; filing mandatory before market opens |
| **Source** | Company via BSE/NSE exchange filing |
| **Affected Entities** | Company equity; all analyst models (leadership premium built into valuation); hypothesis entities |
| **Information Produced** | Departing CEO name; new CEO name; reason for change; effective date; transition plan |
| **Knowledge Produced** | Strategy continuity or change signal; governance health signal; industry talent signal |
| **State Changes** | Management quality entity: re-assessed; Company hypothesis: reviewed |
| **Typical Duration** | Announcement instantaneous; strategic impact over 6-24 months |
| **Severity** | High to Critical (unexpected departure); Moderate (planned transition) |
| **Frequency** | ~50-100 material CEO changes per year among large-cap/mid-cap universe |
| **Dependencies** | Board decision; regulatory requirements |
| **Relationships** | TRIGGERS → Analyst estimate revision; INFLUENCES → Governance quality assessment; SIGNALS → Strategy shift potential |
| **Lifecycle** | Board decision → Exchange disclosure → Transition period → New CEO takes charge → Strategy reviewed |
| **Examples** | Infosys CEO change 2014: Narayana Murthy's return; Infosys CEO Vishal Sikka resignation 2017 — stock fell 10% in a day on governance concern |
| **Importance** | High |

---

### EVT-033 — VOLUME EXPLOSION

| Attribute | Value |
|---|---|
| **Event Code** | EVT-033 / B.2.01 |
| **Name** | Volume Explosion |
| **Definition** | A stock's daily trading volume exceeds a defined multiple (typically 5×) of its 20-day average daily volume, indicating extraordinary market interest or institutional activity |
| **Why It Exists** | Volume is the fuel of price moves. Extraordinary volume indicates extraordinary interest — institutional buying or selling, corporate information leak, or the beginning of a major trend change. Volume explosion is one of the highest-information density price events. |
| **Trigger** | Real-time volume monitoring detects threshold breach during session |
| **Preconditions** | Stock must have established average volume baseline; threshold defined (e.g., 5× ADV) |
| **Source** | Derived: real-time exchange volume data vs. 20-day average |
| **Affected Entities** | The stock entity; options chain; analyst interest; hypothesis entities |
| **Information Produced** | Volume multiple; price direction; delivery percentage; identification of buying/selling blocks |
| **Knowledge Produced** | Unusual institutional activity; potential information advantage by some party; or technical significance of level being tested |
| **State Changes** | Stock entity: elevated visibility; Alert entity: triggered; Signal entity: generated |
| **Typical Duration** | Session-based event; significance persists for 1-5 sessions |
| **Severity** | High |
| **Frequency** | Multiple per day across the universe |
| **Dependencies** | No concurrent corporate news (if no news, mystery volume is more significant) |
| **Relationships** | CONFIRMS → Breakout validity; SIGNALS → Institutional activity; TRIGGERS → Alert and investigation |
| **Lifecycle** | Volume threshold crossed → Alert generated → System assesses context (news vs no news) → Signal generated or dismissed |
| **Examples** | RELIANCE: Volume 8× average on day of acquisition news — informed trading signal before formal announcement |
| **Risks** | Operator error creating one-time spike; index rebalancing creating artificial volume |
| **Importance** | High |

---

### EVT-034 — INSIDER TRADING CASE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-034 / F.1.05 |
| **Name** | SEBI Insider Trading Case |
| **Definition** | SEBI formally files or concludes an insider trading investigation against individuals associated with a listed company |
| **Why It Exists** | Insider trading cases reveal governance failure and management trust issues. They also indicate that unusual trading before corporate events (like acquisitions) was based on privileged information. |
| **Trigger** | SEBI investigation completion; order passed against individuals |
| **Preconditions** | SEBI must have identified suspicious trading pattern; investigation completed |
| **Source** | SEBI enforcement division |
| **Affected Entities** | Company equity; management credibility entity; regulatory relationship entities |
| **Information Produced** | Names of accused; evidence summary; penalty imposed; company connection |
| **Knowledge Produced** | Governance quality degraded; insider information culture signal |
| **State Changes** | Management quality entity: severely downgraded; Governance entity: negative |
| **Typical Duration** | Investigation: months to years; announcement: instantaneous |
| **Severity** | High |
| **Frequency** | ~15-25 enforcement actions per year |
| **Relationships** | TRIGGERS → Analyst downgrade; WEAKENS → Investment thesis; SIGNALS → Governance failure |
| **Examples** | Infosys co-founder relative case; Nifty information leakage cases |
| **Importance** | High |

---

### EVT-035 — MONSOON DEFICIENCY

| Attribute | Value |
|---|---|
| **Event Code** | EVT-035 / D.4.02 |
| **Name** | Monsoon Deficiency |
| **Definition** | India Meteorological Department declares that total monsoon rainfall is more than 10% below the Long Period Average — indicating potential agricultural disruption and rural economic stress |
| **Why It Exists** | India's economy is substantially dependent on agriculture. Monsoon deficiency reduces crop output, increases food inflation, reduces rural consumer spending, and triggers government welfare spending. It affects FMCG, tractors, two-wheelers, microfinance, and rural banking. |
| **Trigger** | IMD declaration; cumulative rainfall data through monsoon season |
| **Preconditions** | Monsoon season must have progressed sufficiently for projection to be reliable |
| **Source** | India Meteorological Department |
| **Affected Entities** | Agricultural commodity prices; FMCG sector; two-wheelers; tractors; microfinance; government food subsidy entity |
| **Information Produced** | Deficiency percentage; geographic distribution; affected crop types |
| **Knowledge Produced** | Rural demand outlook; food inflation risk; government spending trigger |
| **State Changes** | Rural demand entities: downward revision; Food inflation entity: upward risk; FMCG volume growth: downward revision |
| **Typical Duration** | Seasonal event; effects persist through 2 quarters |
| **Severity** | High (if >15% deficiency); Moderate (10-15%) |
| **Frequency** | Significant deficiency: ~1 in 5 years; any level of deficiency: common |
| **Dependencies** | El Niño/La Niña conditions; geographical distribution of rainfall |
| **Relationships** | CAUSES → Food inflation spike; TRIGGERS → RBI rate hold; INFLUENCES → Rural FMCG demand |
| **Lifecycle** | Monsoon onset → Progress tracking → IMD midseason update → Deficiency declaration → Sector impact assessment |
| **Examples** | 2023 monsoon deficiency: El Niño-driven; IMD -5% national (uneven — south India -15%); FMCG rural growth weakened 2 quarters |
| **Importance** | High |

---

### EVT-036 — NEW 52-WEEK HIGH

| Attribute | Value |
|---|---|
| **Event Code** | EVT-036 / B.1.01 |
| **Name** | 52-Week High |
| **Definition** | A stock reaches the highest price it has traded in the rolling 52-week period — a key technical and fundamental milestone |
| **Why It Exists** | New 52-week highs indicate momentum, trend confirmation, and — if accompanied by improving fundamentals — business improvement. Stocks making new 52-week highs consistently outperform the broader market in the subsequent 6-12 months (momentum effect). |
| **Trigger** | Intraday price exceeds the rolling 52-week highest price |
| **Preconditions** | 52 weeks of price history must exist |
| **Source** | Exchange price data |
| **Affected Entities** | The stock entity; technical hypothesis entities; watchlist entities |
| **Information Produced** | New 52-week high price; volume confirmation; fundamental context |
| **Knowledge Produced** | Momentum signal; trend health indicator; institutional buying confirmation |
| **State Changes** | Technical structure entity: prior resistance removed; Signal entity: potential entry signal |
| **Typical Duration** | Event instantaneous; significance persists for days to weeks |
| **Severity** | High |
| **Frequency** | Multiple per day across the universe |
| **Relationships** | SUPPORTS → Bullish thesis; CONFIRMS → Momentum; TRIGGERS → Watchlist alert |
| **Examples** | NIFTY 50 new all-time high October 2024 at 26,277 — confirmed bull market continuation signal |
| **Importance** | High |

---

### EVT-037 — SEBI CIRCULAR

| Attribute | Value |
|---|---|
| **Event Code** | EVT-037 / F.1.01 |
| **Name** | SEBI Circular |
| **Definition** | SEBI publishes an official regulatory circular that changes market rules, participant obligations, product specifications, or compliance requirements |
| **Why It Exists** | SEBI is India's primary securities market regulator. Its circulars are legally binding on all market participants. Circulars can change F&O margin rules, delivery obligations, IPO processes, disclosure norms — fundamentally altering market structure. |
| **Trigger** | SEBI policy decision; consultation paper outcome |
| **Preconditions** | SEBI board or department decision must be taken |
| **Source** | SEBI |
| **Affected Entities** | Depending on topic: all brokers; all listed companies; all mutual funds; derivatives market |
| **Information Produced** | Rule change; effective date; compliance requirement |
| **Knowledge Produced** | Market structure change; compliance cost or opportunity; potential market impact |
| **State Changes** | Regulatory relationship entities: updated; Market structure entity: potentially changed |
| **Typical Duration** | Announcement instantaneous; implementation over weeks to months |
| **Severity** | Variable (margin rule: Critical; disclosure format: Low) |
| **Frequency** | ~50-100 circulars per year |
| **Relationships** | MANDATES → Compliance action; CHANGES → Market structure; TRIGGERS → Participant adaptation |
| **Examples** | SEBI Enhanced Margin Framework 2021: Increased F&O margin requirements → reduced retail speculative activity by 40%; options premium collection changed |
| **Importance** | High |

---

### EVT-038 — EARNINGS CONFERENCE CALL

| Attribute | Value |
|---|---|
| **Event Code** | EVT-038 / A.7.09 |
| **Name** | Earnings Conference Call |
| **Definition** | Company management hosts a post-results conference call with analysts and institutional investors, providing context for the reported numbers, answering questions, and potentially giving forward guidance |
| **Why It Exists** | Numbers alone are incomplete. The management call provides: the story behind the numbers, forward guidance, management tone (optimism/concern), and answers to analyst probing — all of which carry substantial information value beyond what the financial statements reveal. |
| **Trigger** | Quarterly/annual results published; management schedules call |
| **Preconditions** | Results must be published; management must agree to hold call |
| **Source** | Company management |
| **Affected Entities** | Company equity; analyst models; hypothesis entities; institutional investor decisions |
| **Information Produced** | Forward guidance (quantitative or qualitative); management's attribution of results; competitive commentary; capital allocation plans |
| **Knowledge Produced** | Management quality assessment; forward earnings probability; risk factors highlighted |
| **State Changes** | Hypothesis entities: updated based on guidance; Conviction: revised post-call |
| **Typical Duration** | 45-90 minutes |
| **Severity** | High |
| **Frequency** | 4× per year per company |
| **Relationships** | PROVIDES_CONTEXT_FOR → Results event; UPDATES → Analyst models; TRIGGERS → Rating changes |
| **Examples** | HDFC Bank Q3 FY26 call: Management guides for sustained 15% loan growth; NIM pressure temporary — triggered conviction upgrade from 6.1 to 7.3 |
| **Importance** | High |

---

### EVT-039 — DATA FEED FAILURE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-039 / I.4.14 |
| **Name** | Data Feed Failure |
| **Definition** | The system's market data feed (Dhan API, Yahoo Finance fallback, or other source) becomes unavailable or produces clearly erroneous data — preventing real-time price and market data from reaching the analysis engine |
| **Why It Exists** | All real-time analysis depends on data feed integrity. A data feed failure creates a safety-critical condition where the system must stop making decisions based on stale or absent data. |
| **Trigger** | Connection timeout; HTTP error from data provider; data quality check failure |
| **Preconditions** | System must be in active monitoring mode |
| **Source** | AI Trading Brain data feed monitoring module |
| **Affected Entities** | All entities requiring real-time price data; system cycle execution; pending decisions |
| **Information Produced** | Which feed failed; duration; fallback activated; data staleness level |
| **Knowledge Produced** | System is operating with incomplete information; decisions based on stale data are invalid |
| **State Changes** | System mode: degraded; pending decisions: suspended; fallback feed: activated if available |
| **Typical Duration** | Seconds to hours depending on provider issue |
| **Severity** | High (safety-critical) |
| **Frequency** | ~5-15 significant incidents per year |
| **Dependencies** | Internet connectivity; data provider uptime; API rate limits |
| **Relationships** | TRIGGERS → Fallback activation; SUSPENDS → Real-time decisions; ALERTS → Operator |
| **Lifecycle** | Feed normal → Timeout/error detected → Alert generated → Fallback activated → Operator notified → Resolution → Feed restored → Normal operation |
| **Examples** | Dhan API 451 error (blocked data endpoint): system auto-falls back to yfinance; operator alerted; 8-minute gap in live data |
| **Importance** | Critical (system safety) |

---

### EVT-040 — CREDIT CONTAGION EVENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-040 / M.1.07 |
| **Name** | Credit Contagion Event |
| **Definition** | A credit market stress event (rating downgrade, default, NPA classification) in one entity propagates to create stress in related entities — triggering a chain reaction through financial interconnections |
| **Why It Exists** | Financial system participants are interconnected. When one major credit event occurs, lenders to the defaulted entity face losses; those lenders may restrict credit to similar entities; credit availability tightens sector-wide; equity prices fall on earnings risk. |
| **Trigger** | Material credit event (default or severe downgrade) in a systemically connected entity |
| **Preconditions** | Significant credit interconnection must exist; event must be large enough to trigger systemic fear |
| **Source** | Credit market; rating agencies; banking disclosures |
| **Affected Entities** | All lenders to the defaulted entity; sector peers; mutual funds with exposure; NBFCs with similar business models |
| **Information Produced** | Default size; interconnection map; mutual fund exposure; bank exposure |
| **Knowledge Produced** | Systemic risk quantification; contagion probability; sector-wide credit risk |
| **State Changes** | Sector entities: credit risk premium increases; NBFC/bank entities: exposure disclosed; MF entities: NAV impact |
| **Typical Duration** | Cascades over days to weeks |
| **Severity** | Critical |
| **Frequency** | Major events: ~1-2 per year; minor: more frequent |
| **Relationships** | CASCADES_INTO → Sector credit freeze; TRANSMITS_TO → Banking sector; TRIGGERS → Regulatory intervention |
| **Examples** | IL&FS September 2018: ₹91,000 crore default → NBFC credit freeze → mutual fund redemptions → Franklin Templeton crisis 2020 |
| **Importance** | Critical |

---

### EVT-041 — VOLATILITY REGIME CHANGE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-041 |
| **Name** | Volatility Regime Change |
| **Definition** | The market transitions from a low-volatility to high-volatility regime (or vice versa), as detected by India VIX crossing a regime boundary and sustained for defined sessions |
| **Why It Exists** | Strategy performance is regime-dependent. Momentum strategies work in low-volatility trending regimes; defensive strategies work in high-volatility regimes. Detecting regime change early allows strategy adjustment before performance degrades. |
| **Trigger** | VIX sustained above/below regime boundary (e.g., VIX > 25 for 5 consecutive sessions = high volatility regime) |
| **Preconditions** | Regime classification model must be operational; VIX data must be current |
| **Source** | AI Trading Brain regime classification engine |
| **Affected Entities** | All active strategies (performance changes); all hypothesis confidence levels; position sizing |
| **Information Produced** | New regime; previous regime; transition date; expected strategy performance in new regime |
| **Knowledge Produced** | Market structure has changed; strategy weights must be adjusted; risk parameters must be recalibrated |
| **State Changes** | Market regime entity: updated; Strategy weights: adjusted; Position sizing: recalibrated |
| **Severity** | High |
| **Frequency** | ~4-8 major regime transitions per year |
| **Relationships** | TRIGGERS → Strategy reweighting; ACTIVATES → Defensive mode (if high-vol); UPDATES → Regime-specific evidence weights |
| **Lifecycle** | VIX data → Regime model evaluates → Boundary sustained → Transition event → Strategy engine updated → Position sizing recalibrated |
| **Importance** | Critical |

---

### EVT-042 — ANNUAL GENERAL MEETING

| Attribute | Value |
|---|---|
| **Event Code** | EVT-042 / A.5.17 |
| **Name** | Annual General Meeting |
| **Definition** | The mandatory annual shareholder meeting where the company presents annual results, elects directors, seeks approval for auditor appointment, dividend, and any other material resolutions |
| **Why It Exists** | The AGM is the formal annual governance event where management is accountable to shareholders. Material resolutions (acquisitions, fund-raising, management compensation) are voted on. |
| **Trigger** | Annual requirement; must be held within 6 months of financial year end |
| **Source** | Company |
| **Affected Entities** | Company equity; management authority entities; governance quality entity |
| **Information Produced** | Resolutions passed/rejected; management commentary; shareholder questions and answers |
| **State Changes** | Governance entity: annual update; Director entities: reconfirmed or changed |
| **Severity** | Variable |
| **Frequency** | Annual (per company) |
| **Importance** | Moderate |

---

### EVT-043 — OPTION CHAIN IV CRUSH

| Attribute | Value |
|---|---|
| **Event Code** | EVT-043 / B.3.14 |
| **Name** | Implied Volatility Crush |
| **Definition** | Implied volatility in options prices collapses sharply — typically after a scheduled event (earnings, policy decision) resolves uncertainty — dramatically reducing options premium |
| **Why It Exists** | Options premiums build in anticipation of uncertainty events. Once the event occurs, the uncertainty is resolved and IV collapses. Traders who sell options before events profit from the IV crush; those who buy options are hurt. |
| **Trigger** | Scheduled event resolves (results published, RBI decision made); or unexpected calm period |
| **Source** | NSE options market pricing |
| **Affected Entities** | All options on the stock/index; options strategy entities; IV-based signals |
| **Information Produced** | Pre-event vs post-event IV level; IV percentile; premium collapse magnitude |
| **Knowledge Produced** | Options market was pricing significant uncertainty; that uncertainty is now resolved |
| **State Changes** | Options chain entity: premiums decline; strategy performance: varies by position (sellers benefit) |
| **Severity** | Moderate to High (for options traders) |
| **Frequency** | Post-every-results, post-every-policy-event — multiple per week market-wide |
| **Relationships** | FOLLOWS → Scheduled event resolution; CAUSES → Options premium collapse |
| **Importance** | High (options strategies) |

---

### EVT-044 — INTERNATIONAL TRADE DEAL

| Attribute | Value |
|---|---|
| **Event Code** | EVT-044 / D.3.05 |
| **Name** | International Trade Deal Signed |
| **Definition** | India signs a bilateral or multilateral free trade agreement (FTA) or trade enhancement agreement with a significant trading partner, reducing tariffs and opening market access |
| **Why It Exists** | Trade deals reshape export opportunities and competitive threats. An FTA with the EU or UK opens massive new markets for Indian exporters (IT, pharmaceuticals, textiles) while potentially threatening import-competing sectors (auto, chemicals). |
| **Trigger** | Government signing ceremony; formal ratification |
| **Source** | Ministry of Commerce, Government of India |
| **Affected Entities** | Export-oriented companies; import-competing companies; currency entity (trade balance change) |
| **Information Produced** | Products/sectors covered; tariff reduction schedule; effective date |
| **Knowledge Produced** | Long-term sector reshaping; company-level competitive position change |
| **State Changes** | Sector entities: competitive dynamics changed; Export company entities: margin improvement potential |
| **Severity** | High |
| **Frequency** | Rare (1-3 major FTAs per decade) |
| **Relationships** | RESHAPES → Sector competitive dynamics; INFLUENCES → Export company earnings; AFFECTS → Currency |
| **Importance** | High |

---

### EVT-045 — BLOCK DEAL

| Attribute | Value |
|---|---|
| **Event Code** | EVT-045 / B.2.05 |
| **Name** | Block Deal |
| **Definition** | A large institutional transaction executed in a single session on the exchange's block deal window — representing sale/purchase of more than 500,000 shares or ₹10 crore |
| **Why It Exists** | Block deals reveal large institutional conviction — either massive accumulation (bullish) or large-scale distribution (bearish). The counterparty identity (buyer/seller) determines the signal direction. |
| **Trigger** | Large institution trades exceeding block deal threshold |
| **Source** | BSE/NSE block deal window; exchange disclosure |
| **Affected Entities** | The stock; institutional shareholding pattern; price |
| **Information Produced** | Buyer/seller names; quantity; price; as % of outstanding shares |
| **Knowledge Produced** | Smart money direction for this stock; institutional conviction level |
| **State Changes** | Shareholding entity: changes; price: potential impact depending on liquidity |
| **Severity** | High |
| **Frequency** | Multiple per day across universe |
| **Relationships** | SIGNALS → Institutional direction; TRIGGERS → Research investigation |
| **Examples** | GQG Partners buys TATAMOTORS through block deal: signals global investor confidence |
| **Importance** | High |

---

### EVT-046 — FISCAL DEFICIT MILESTONE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-046 / C.1.13 |
| **Name** | Fiscal Deficit Milestone |
| **Definition** | The Government publishes fiscal deficit data showing that cumulative deficit has crossed a defined milestone (e.g., 60% of annual target exhausted in first half of year) |
| **Why It Exists** | Fiscal discipline signals are critical for bond market and currency stability. High fiscal deficit triggers higher government borrowing, pushes up yields, and can weaken the INR. It also signals limited space for additional fiscal stimulus. |
| **Trigger** | Controller General of Accounts publishes monthly data |
| **Source** | Ministry of Finance |
| **Affected Entities** | G-Sec yields; INR; bond market; RBI policy space |
| **Information Produced** | Actual deficit vs target; revenue shortfall or overrun; expenditure pattern |
| **Knowledge Produced** | Fiscal policy trajectory; bond supply risk; RBI constraint |
| **State Changes** | Bond yield entity: upward pressure; INR entity: potential weakness |
| **Severity** | Moderate to High |
| **Frequency** | Monthly data; milestone crossings: 3-4 per year |
| **Importance** | High |

---

### EVT-047 — PROMOTER SHAREHOLDING CHANGE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-047 / A.5.11-A.5.12 |
| **Name** | Promoter Shareholding Change |
| **Definition** | The promoter group's percentage ownership of the company changes materially — disclosed via SEBI quarterly shareholding pattern |
| **Why It Exists** | Promoter buying is the strongest possible insider signal — the people who know the company best are buying more. Promoter selling (creeping) without corporate announcements is a concern signal. |
| **Trigger** | Quarterly shareholding filing; SEBI disclosure obligations |
| **Source** | Company via BSE/NSE |
| **Affected Entities** | Company equity; governance entity; investor sentiment |
| **Information Produced** | New promoter holding %; change from prior quarter; method (open market buy, preferential allotment) |
| **Knowledge Produced** | Management confidence signal; potential governance concern (if unexplained selling) |
| **State Changes** | Ownership entity: updated; Confidence signal: generated |
| **Severity** | High (>1% change); Moderate (<0.5%) |
| **Frequency** | Quarterly disclosure cycle |
| **Importance** | High |

---

### EVT-048 — RECORD DATE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-048 / A.2.09 |
| **Name** | Record Date |
| **Definition** | The date on which the register of shareholders is examined to determine eligibility for corporate benefits — dividends, bonus shares, rights issue, or any other distribution |
| **Why It Exists** | The record date is a structural settlement event that determines entitlement. Shares bought on or after the ex-date do not carry the entitlement. This creates predictable price adjustments on ex-date. |
| **Trigger** | Company board decision on dividend/bonus/rights record date |
| **Source** | Company filing |
| **Affected Entities** | All shareholders on that date; company equity price; derivatives settlement |
| **Information Produced** | Exact record date; nature of entitlement; ex-date (one business day before record date under T+1 settlement) |
| **Knowledge Produced** | Entitlement calendar; price adjustment expected on ex-date |
| **State Changes** | Shareholder registry: snapshot taken; Price entity: dividend-adjusted on ex-date |
| **Severity** | Moderate (routine); High (for large special dividends) |
| **Frequency** | Multiple per year per company |
| **Importance** | High (calendar event) |

---

### EVT-049 — ETF CREATION EVENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-049 / E.3.01 |
| **Name** | ETF Creation Event |
| **Definition** | Authorized participants create new ETF units by delivering a basket of underlying securities to the fund — increasing AUM and requiring the ETF to hold proportional weights in all constituents |
| **Why It Exists** | ETF creation events are driven by institutional demand for ETF units. Large creation events signal significant inflows into passive products — creating predictable buying of index constituents. |
| **Trigger** | Authorized participant submits creation request |
| **Source** | ETF fund house; NSE/BSE |
| **Affected Entities** | ETF entity (AUM increases); all constituent stocks (buying pressure); index entity |
| **Information Produced** | Creation unit size; implied constituent buying; ETF premium/discount before creation |
| **Knowledge Produced** | Passive demand increase; flow dynamics for ETF basket constituents |
| **State Changes** | ETF entity: AUM and units outstanding increase; Constituent entities: demand increases proportionally |
| **Severity** | Variable (large creation: High) |
| **Frequency** | Daily for active ETFs |
| **Importance** | Moderate |

---

### EVT-050 — GOVERNMENT POLICY ANNOUNCEMENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-050 / D.1.10 |
| **Name** | Major Government Policy Announcement |
| **Definition** | Government announces a significant economic policy — production-linked incentive scheme, sector reform, divestment, or strategic initiative — outside the budget context |
| **Why It Exists** | Policy announcements outside the budget are often the most market-moving — they are unscheduled and therefore carry surprise premium. PLI schemes, GST rate changes, sector deregulation, or regulatory reform can fundamentally alter a sector's economics. |
| **Trigger** | Cabinet decision; Ministry announcement |
| **Source** | Government Ministries; Cabinet Committee on Economic Affairs |
| **Affected Entities** | Target sector companies; input suppliers; competing sectors |
| **Information Produced** | Policy nature; sectors affected; financial incentive quantum; implementation timeline |
| **Knowledge Produced** | Sector investment attractiveness change; earnings model revision trigger |
| **State Changes** | Sector entity: policy environment updated; Company entities: earnings model revision required |
| **Severity** | Critical (major reforms) to Moderate (sector-specific) |
| **Frequency** | ~20-50 significant policy events per year |
| **Relationships** | TRIGGERS → Sector rotation; CAUSES → Analyst estimate revision; INFLUENCES → Long-term sector growth |
| **Examples** | PLI for semiconductor manufacturing announced 2021: triggered electronics sector re-rating; PLI for pharma: triggered pharma manufacturing investment cycle |
| **Importance** | Critical |

---

### EVT-051 — PANIC SELLING EVENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-051 / K.1.01 |
| **Name** | Panic Selling Event |
| **Definition** | A sudden, irrational, fear-driven mass selling of equities — disconnected from fundamental values — typically occurring after a shocking negative event overwhelms rational assessment |
| **Why It Exists** | Panic selling is both a threat (to existing positions) and an opportunity (prices decouple from value temporarily). Detecting panic selling allows the system to either protect positions or identify high-conviction entry points at depressed prices. |
| **Trigger** | Severe negative shock event; margin call cascade; institutional risk limit breach |
| **Source** | Market behavior; detected via multiple simultaneous signals: VIX spike, AD ratio collapse, volume explosion, circuit breakers |
| **Affected Entities** | All equity entities simultaneously; portfolio entities; margin entities |
| **Information Produced** | Magnitude of fall; breadth of decline; VIX level; global context |
| **Knowledge Produced** | Market is pricing fear, not value; forced selling is disconnecting prices from fundamentals |
| **State Changes** | All equity entity prices: declining; Kill switch: potentially activated; System mode: defensive |
| **Severity** | Critical |
| **Frequency** | ~2-4 per year (at varying severity) |
| **Dependencies** | Shock event; leverage in system; liquidity |
| **Relationships** | TRIGGERS → Kill switch; CREATES → Value opportunities; CAUSES → System defensive mode |
| **Lifecycle** | Shock → Initial sell-off → Margin calls → Forced selling → Panic cascade → Capitulation → Potential recovery |
| **Importance** | Critical |

---

### EVT-052 — ANALYST UPGRADE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-052 / G.2.02 |
| **Name** | Analyst Upgrade |
| **Definition** | A brokerage analyst raises their investment rating on a stock — typically from Neutral or Sell to Buy — representing a change in their fundamental or valuation assessment |
| **Why It Exists** | Analyst upgrades, when accompanied by new evidence (earnings beat, management change, sector re-rating), act as a signal amplifier — bringing institutional investor attention to the upgrade thesis. |
| **Trigger** | Analyst's change of view on fundamental or valuation basis |
| **Source** | Brokerage research department |
| **Affected Entities** | Stock entity; analyst model entity; hypothesis entities |
| **Information Produced** | New rating; old rating; new price target; key thesis change |
| **Knowledge Produced** | Professional analysis change; institutional recommendation change; earnings model revision |
| **State Changes** | Analyst consensus entity: shifts; Hypothesis: corroborating evidence added |
| **Severity** | Moderate (individual analyst); High (consensus shift across multiple analysts) |
| **Frequency** | Multiple per day across universe |
| **Relationships** | CORROBORATES → Bullish hypothesis; TRIGGERS → Institutional investor review; SUPPORTS → Conviction increase |
| **Importance** | Moderate to High |

---

### EVT-053 — REGULATORY INVESTIGATION INITIATED

| Attribute | Value |
|---|---|
| **Event Code** | EVT-053 / A.5.23 |
| **Name** | Regulatory Investigation Initiated |
| **Definition** | SEBI, ED, CBI, or other regulatory body formally begins an investigation of a listed company or its promoters |
| **Why It Exists** | Regulatory investigations reveal governance risk and potentially fraudulent activity. They can last years and overhang the stock price throughout. Early detection allows risk management. |
| **Trigger** | Regulatory order; news report (SEBI rarely announces investigations at initiation); whistleblower disclosure |
| **Source** | SEBI; Enforcement Directorate; CBI; news |
| **Affected Entities** | Company equity; management; existing investors; promoters |
| **Information Produced** | Nature of investigation; regulatory body; specific allegations |
| **Knowledge Produced** | Governance risk elevated; management credibility compromised; legal liability potential |
| **State Changes** | Governance entity: severely downgraded; Investment hypothesis: must be reviewed |
| **Severity** | Critical |
| **Relationships** | INVALIDATES → Management credibility thesis; TRIGGERS → Exit review |
| **Importance** | Critical |

---

### EVT-054 — SHORT SQUEEZE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-054 / K.1.04 |
| **Name** | Short Squeeze |
| **Definition** | A heavily shorted stock rises rapidly — forcing short sellers to cover losses by buying — which further accelerates the rise in a self-reinforcing feedback loop |
| **Why It Exists** | Short squeezes create some of the largest and fastest price moves in financial markets. They occur when too many participants have the same bearish thesis simultaneously, and a positive catalyst forces a sudden reversal. |
| **Trigger** | Heavily shorted stock + positive catalyst (earnings beat, M&A, short-seller retraction) |
| **Preconditions** | High short interest (>20% of float shorted); positive surprise catalyst |
| **Source** | Market behavior; detected via OI change + price rise pattern |
| **Affected Entities** | The heavily shorted stock; short position holders; options chain |
| **Information Produced** | Short interest level; covering pace; price rise magnitude; estimated remaining short exposure |
| **Knowledge Produced** | Short thesis is failing; painful squeeze likely to continue until shorts exhausted |
| **State Changes** | Stock entity: price rises dramatically; Short position entities: losses mounting; OI entity: declining |
| **Severity** | High to Critical (50-200% moves possible in extreme squeezes) |
| **Frequency** | ~5-20 significant squeezes per year |
| **Relationships** | CAUSES → Rapid price appreciation; FORCES → Short covering; TRIGGERS → Entry signal (early recognition) |
| **Examples** | Gamestop 2021 (US); Adani short-seller crisis 2023: attempted squeeze by institutional holders |
| **Importance** | High |

---

### EVT-055 — RIGHTS ISSUE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-055 / A.3.04 |
| **Name** | Rights Issue |
| **Definition** | A company offers its existing shareholders the right to buy additional shares at a defined price (usually at a discount to market) in a defined ratio — as a means of raising fresh capital |
| **Why It Exists** | Rights issues raise capital while giving existing shareholders proportional priority. The discount provides economic incentive; the dilution is a cost. Management credibility and use of proceeds determine whether it is a positive or negative event. |
| **Trigger** | Board approval; SEBI filing |
| **Source** | Company; SEBI |
| **Affected Entities** | Existing shareholders (right/obligation to maintain holding); company equity (potential dilution); entitlement security (new temporary entity created) |
| **Information Produced** | Rights ratio (e.g., 1 new share per 5 held); issue price; record date; subscription period |
| **Knowledge Produced** | Capital need assessment; dilution quantum; management confidence in recovery |
| **State Changes** | Share capital entity: increases on completion; Price entity: adjusts for dilution |
| **Severity** | High |
| **Frequency** | ~10-30 rights issues per year |
| **Importance** | High |

---

### EVT-056 — GOVERNMENT DIVESTMENT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-056 / C.3.06-C.3.07 |
| **Name** | Government Divestment Completion |
| **Definition** | Government of India completes sale of a stake in a Public Sector Undertaking through OFS (Offer for Sale), strategic sale, or exchange |
| **Why It Exists** | Divestment changes PSU ownership structure, potentially reducing government interference and improving efficiency. Large divestments also affect market supply (adding float) and fiscal arithmetic. |
| **Trigger** | Government decision; OFS announcement on exchange |
| **Source** | DIPAM (Department of Investment and Public Asset Management) |
| **Affected Entities** | PSU equity (additional float); government fiscal entity; sector competitive dynamics |
| **Information Produced** | Stake sold %; price; buyer; government's remaining stake |
| **Knowledge Produced** | Government commitment to PSU reform; fiscal management signal; PSU governance improvement signal |
| **State Changes** | Shareholding entity: government % reduced; Float entity: increased |
| **Severity** | High |
| **Frequency** | ~5-10 significant divestments per year |
| **Importance** | High |

---

### EVT-057 — MCLR CHANGE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-057 / C.2.09 |
| **Name** | MCLR (Marginal Cost of Funds-Based Lending Rate) Change |
| **Definition** | Banks change their MCLR — the minimum rate at which they lend to borrowers — following changes in their cost of funds (primarily driven by RBI repo rate changes) |
| **Why It Exists** | MCLR is the transmission mechanism between RBI policy rates and actual borrowing costs in the economy. When MCLR changes, all floating rate loans (home loans, auto loans, corporate loans) reset — directly affecting consumer EMIs and corporate finance costs. |
| **Trigger** | RBI repo rate change; change in bank cost of funds; monthly MCLR review |
| **Source** | Individual banks (each bank sets its own MCLR) |
| **Affected Entities** | All floating rate borrowers (corporates, home loan borrowers); bank NIM entity; real estate sector; auto sector; NBFC entity |
| **Information Produced** | New MCLR level; effective date; change from previous MCLR |
| **Knowledge Produced** | Transmission of RBI policy; credit demand impact; sector-level affordability change |
| **State Changes** | Borrowing cost entity: updated; Consumer EMI entity: adjusted; Corporate interest cost entity: changes |
| **Severity** | High |
| **Frequency** | Monthly review; actual change: ~3-5 per year |
| **Importance** | High |

---

### EVT-058 — COMMODITY PRICE SPIKE

| Attribute | Value |
|---|---|
| **Event Code** | EVT-058 / C.5.01 |
| **Name** | Commodity Price Spike |
| **Definition** | A key commodity (crude oil, natural gas, steel, copper, aluminium) rises sharply by a defined threshold (>5% in a session or >20% over a month) — creating input cost pressure or revenue opportunity depending on the entity |
| **Why It Exists** | India is a significant commodity importer (oil, coal, gold) and a significant commodity producer (steel, aluminium). Commodity price changes directly affect manufacturing margins, trade balance, inflation, and the INR. |
| **Trigger** | Supply disruption; demand surge; geopolitical event; OPEC decision |
| **Source** | Global commodity markets; MCX |
| **Affected Entities** | Oil-dependent sectors (airlines, auto, FMCG, paint, chemical); commodity producers (positive for steel/aluminium); trade balance; INR; inflation entity |
| **Information Produced** | Commodity; price level; change magnitude; cause; duration expectation |
| **Knowledge Produced** | Input cost pressure quantum; margin compression risk; inflation passthrough probability |
| **State Changes** | Sector margin entities: revised; Inflation entity: updated; RBI decision space: affected |
| **Severity** | High |
| **Frequency** | Multiple per year |
| **Relationships** | TRANSMITS_TO → Sector margins; CAUSES → Inflation risk; TRIGGERS → RBI concern |
| **Importance** | High |

---

### EVT-059 — NEW KNOWLEDGE ITEM CREATED

| Attribute | Value |
|---|---|
| **Event Code** | EVT-059 / I.2.02 |
| **Name** | Knowledge Item Created |
| **Definition** | The AI system's learning engine creates a new validated knowledge item — a pattern or relationship that has been confirmed across sufficient observations to be considered reliable |
| **Why It Exists** | Knowledge accumulation is the fundamental competitive advantage of an AI trading system. Each validated knowledge item is a reusable insight that improves future decisions. |
| **Trigger** | Pattern observation threshold met; validation process completed |
| **Source** | AI Trading Brain Learning System |
| **Affected Entities** | Knowledge base entity; strategy entities that can use the new pattern |
| **Information Produced** | Knowledge content; confidence level; applicable conditions; evidence count |
| **Knowledge Produced** | New validated pattern available for use in reasoning chains |
| **State Changes** | Knowledge base entity: expanded; Evidence weighting: new signal type added |
| **Severity** | High (system evolution) |
| **Frequency** | ~5-20 new knowledge items per week |
| **Relationships** | ENRICHES → Knowledge base; IMPROVES → Future reasoning quality |
| **Importance** | High |

---

### EVT-060 — POSITION STOP LOSS HIT

| Attribute | Value |
|---|---|
| **Event Code** | EVT-060 / I.4.05 |
| **Name** | Position Stop Loss Hit |
| **Definition** | An active trading position reaches its pre-defined stop loss price level — triggering immediate exit order submission to limit further loss |
| **Why It Exists** | Stop losses are the most important risk management mechanism. They enforce discipline — converting unlimited loss risk to defined maximum loss. The stop loss hit event is the system's explicit acknowledgment that the thesis is not working. |
| **Trigger** | Live price crosses below (long) or above (short) the pre-defined stop loss level |
| **Preconditions** | Position must be open; stop loss must be defined; live price monitoring must be active |
| **Source** | AI Trading Brain Trade Monitor (Layer 12) |
| **Affected Entities** | The position entity (status → CLOSED); portfolio entity (capital freed); learning entity (outcome recorded) |
| **Information Produced** | Exit price; loss amount (₹ and %); thesis invalidation reason; learning record created |
| **Knowledge Produced** | Thesis was wrong; strategy performs a loss trade; learning event triggered |
| **State Changes** | Position entity: CLOSED; Portfolio: capital returned; Loss account: updated |
| **Severity** | High |
| **Frequency** | ~30-50% of trades result in stop loss exits |
| **Dependencies** | Live price data; order management system availability |
| **Relationships** | TRIGGERS → Exit order; CREATES → Learning record; UPDATES → Strategy win rate |
| **Lifecycle** | Position open → Stop loss set → Price declines → Stop loss price reached → Exit order submitted → Position closed → Loss recorded → Learning event |
| **Examples** | TATAMOTORS long: Entry ₹920; Stop loss ₹880; Price falls to ₹879.50 → Exit triggered; Loss ₹40.50/share; Learning record: "auto sector thesis invalidated by margin data" |
| **Importance** | Critical |


---

## PART IV — EVENT TAXONOMY

*Multiple classification frameworks for every event in the ontology.*

---

### Taxonomy Dimension 1 — By Scheduling

| Class | Definition | Examples |
|---|---|---|
| **Scheduled** | Event occurs at a pre-announced, known date and time | RBI MPC meeting; Quarterly results; AGM; Budget; NIFTY rebalancing; Options expiry |
| **Semi-Scheduled** | Event occurs in a known window but exact date uncertain | Analyst estimates (updated periodically); Rating reviews (annual review known, exact date unknown) |
| **Unscheduled** | Event can occur at any time without advance notice | Earnings beat/miss; Merger announcement; CEO resignation; Natural disaster; Geopolitical event; Regulatory investigation |
| **Recurring but Irregular** | Event repeats periodically but with variable timing | RBI OMO operations; Government bond auctions (weekly but size varies) |

---

### Taxonomy Dimension 2 — By Expectedness

| Class | Definition | Examples |
|---|---|---|
| **Fully Expected** | Market anticipates and prices event before it occurs | Quarterly results (date known, direction uncertain); Monthly SIP data; Weekly G-Sec auction |
| **Partially Expected** | Market anticipates direction but not magnitude | Earnings beat (positive expected but size uncertain); Rate cut (direction known, pace uncertain) |
| **Unexpected** | Event caught market by surprise | Profit warning; Promoter pledge invocation; Pandemic; Military conflict; Flash crash |
| **Expected but Wrong Direction** | Market anticipated event but realized opposite direction | "Consensus expected rate cut; RBI held" — creates outsized reaction |

---

### Taxonomy Dimension 3 — By Certainty

| Class | Definition | Examples |
|---|---|---|
| **Deterministic** | Event outcome is mechanistically certain | Options expiry settlement; Dividend payout (on declared amount); Ex-date price adjustment |
| **High-Probability** | Historical precedent makes outcome highly likely | NIFTY 50 Index inclusion following eligibility; Rating downgrade after NPA classification |
| **Probabilistic** | Outcome follows a probability distribution | Earnings beat/miss; Election result; Market reaction to known event |
| **Stochastic** | Event magnitude is random within defined bounds | Daily price movement; VIX level on given day |
| **Unknown-Unknown** | Unforeseeable in both occurrence and magnitude | Black swan events; genuine paradigm shifts |

---

### Taxonomy Dimension 4 — By Origin

| Class | Definition | Examples |
|---|---|---|
| **Internal** | Generated within the AI system itself | Signal generated; Decision created; Kill switch; Learning completed; Model retrained |
| **Corporate** | Generated by a specific listed company | Earnings; Dividend; Merger; CEO change; Rating change |
| **Market-Generated** | Emergent from collective market participant behavior | Breakout; Short squeeze; Panic selling; Sector rotation; Liquidity shock |
| **Regulatory** | Generated by regulatory authority | SEBI circular; RBI policy; SEBI enforcement; GST rate change |
| **Macroeconomic** | Generated by national/global economic dynamics | GDP release; Inflation data; Fed decision; Budget |
| **Geopolitical** | Generated by political, military, or diplomatic forces | War; Election; Sanctions; Trade deal |
| **Natural** | Generated by natural forces | Monsoon; Earthquake; Cyclone; Crop failure |
| **Behavioral** | Emergent from collective human psychology | Panic; Euphoria; Narrative shift; Meme stock |

---

### Taxonomy Dimension 5 — By Scope

| Class | Definition | Examples |
|---|---|---|
| **Global** | Affects financial systems worldwide | US Fed decision; Global pandemic; Oil price spike |
| **Multi-Country** | Affects multiple countries simultaneously | MSCI rebalancing; EM currency crisis; Trade war |
| **National** | Affects India as a whole | RBI rate decision; Union Budget; General election |
| **Sectoral** | Affects one sector primarily | Sector-specific regulation; Commodity price change (affects cost-intensive sector) |
| **Company-Specific** | Affects one company primarily | Earnings; CEO change; Merger; Buyback |
| **Portfolio-Specific** | Affects the AI system's specific portfolio | Stop loss hit; Position target reached; Kill switch |
| **Instrument-Specific** | Affects one instrument | Options expiry; Bond maturity; Futures rollover |

---

### Taxonomy Dimension 6 — By Duration of Impact

| Class | Definition | Examples |
|---|---|---|
| **Instantaneous** | Effect fully resolved within minutes to hours | Options expiry; Circuit breaker trigger; Data feed failure |
| **Session** | Effect primarily within the trading session | Volume explosion; Circuit hit; Breakout |
| **Multi-Session** | Effect persists over several trading sessions | Earnings beat/miss; CEO change; Credit rating downgrade |
| **Weeks** | Effect lasts 1-4 weeks | Sector rotation; Index rebalancing; Election result |
| **Quarters** | Effect lasts 1-3 quarters | Budget policy change; Major merger; Commodity cycle |
| **Multi-Year** | Effect shapes entity trajectory for years | Structural regulatory change; Paradigm shift; Technology disruption |
| **Permanent** | Effect is irreversible | Company default; Delisting; Landmark regulatory change |

---

### Taxonomy Dimension 7 — By Reversibility

| Class | Definition | Examples |
|---|---|---|
| **Irreversible** | Once it occurs, the state it created cannot be undone | Corporate bankruptcy; Delisting; Executed trade; Historical data release |
| **Partly Reversible** | State can be changed by future events but original event remains | Rating downgrade can be followed by upgrade; CEO resignation followed by new appointment |
| **Apparently Reversible** | Effect appears to resolve but original event is permanently recorded | Trade deal annulled; Dividend suspended |

---

### Taxonomy Dimension 8 — By Information Content

| Class | Definition | Examples |
|---|---|---|
| **High Information** | Event resolves significant uncertainty | Earnings actual vs estimate; Election result; RBI decision (when surprise) |
| **Medium Information** | Event provides useful new data | Shareholding pattern; MF flow data; G-Sec auction results |
| **Low Information** | Event confirms what was already known | Routine monthly data in line with expectations; Scheduled event with pre-leaked outcome |
| **Noise** | Event has no genuine information content | Routine corporate filing with no material content |

---

### Taxonomy Dimension 9 — By Market Impact

| Class | Definition | Examples |
|---|---|---|
| **Market-Moving** | Directly causes measurable price movement | RBI rate decision; Earnings surprise; Index inclusion/exclusion; Fed decision |
| **Signal-Generating** | Generates signals used in reasoning but doesn't directly move price | PMI data; Promoter shareholding change; Learning cycle completion |
| **Systemic** | Affects entire market structure | Market circuit breaker; Kill switch activation; Exchange halt |
| **Monitoring** | Alerts system to developing situation | VIX threshold crossing; FII outflow accumulation; Technical alert |

---

### Taxonomy Dimension 10 — By Velocity

| Class | Definition | Examples |
|---|---|---|
| **Flash** | Effect realized within seconds to minutes | Flash crash; Circuit trigger; Algorithm-driven breakout |
| **Fast** | Effect realized within one session | Earnings announcement; RBI policy |
| **Moderate** | Effect realized over days | Short squeeze; Credit contagion; Geopolitical |
| **Slow** | Effect accumulates over weeks to months | Sector rotation; ESG re-rating; Monsoon impact on agriculture |
| **Latent** | Effect is building but not yet visible | Debt accumulation; Governance degradation; Technology disruption early stage |

---

### Taxonomy Dimension 11 — By Number of Entities Affected

| Class | Definition | Examples |
|---|---|---|
| **Singular** | Affects exactly one entity | Stop loss hit; Record date; Strategy disabled |
| **Dyadic** | Primarily affects two entities | Merger (two companies); Arbitrage (two prices) |
| **Sectoral** | Affects all entities in a sector | Sector-specific regulation; Commodity change |
| **Market-Wide** | Affects all entities simultaneously | Market circuit breaker; Budget; Fed decision |
| **Cascade** | Starts with one entity and propagates | Credit contagion; Margin call cascade |

---

### Taxonomy Dimension 12 — By Predictability of Timing

| Class | Definition | Examples |
|---|---|---|
| **Exact-Time Known** | Precise timing is public knowledge | Options expiry (last Thursday of month); G-Sec auction (Friday); Budget (February 1) |
| **Window Known** | Approximate window is known | Earnings season (45 days post-quarter end); Index rebalancing (March/September) |
| **Sequence Known** | Event follows another known event | Analyst estimate revision follows earnings; Market reaction follows RBI decision |
| **Unknown Timing** | No advance knowledge of when | Merger announcement; Profit warning; Natural disaster; Geopolitical event |

---

### Taxonomy Dimension 13 — By AI System Response Type

| Class | Definition | System Response |
|---|---|---|
| **Action-Triggering** | Directly triggers a trade decision | Stop loss hit; Conviction threshold; Kill switch |
| **Model-Updating** | Triggers model or parameter update | Learning cycle; Model degradation; New knowledge item |
| **Alert-Generating** | Creates monitoring alert | VIX threshold; FII outflow; Breakout detection |
| **Context-Setting** | Changes the context for future decisions | Regime change; Budget; Policy announcement |
| **Audit-Recording** | Must be permanently recorded for audit | Every trade; Every cycle; Every decision |

---

## PART V — EVENT LIFECYCLES

*Lifecycle models for major event categories — showing how events are born, evolve, and resolve.*

---

### Lifecycle 1 — Corporate Earnings Event

```
ANTICIPATION PHASE
│
├── Consensus estimate formation (weeks before results)
├── Pre-earnings signal buildup (options IV rises)
├── Analyst note publications
└── Management road show (if any)
        │
        ▼
ANNOUNCEMENT PHASE
│
├── Results published on exchange (T)
├── Conference call (T or T+1)
├── Initial market reaction (T, intraday)
└── Analyst revisions begin (T to T+3)
        │
        ▼
ANALYSIS PHASE
│
├── Detailed number parsing (T+0 to T+1)
├── Management guidance evaluation (T+1)
├── Peer comparisons (T+1 to T+3)
└── Thesis confirmation or revision
        │
        ▼
INTEGRATION PHASE
│
├── Analyst price target updates (T+1 to T+5)
├── Institutional portfolio adjustments (T+3 to T+10)
├── Next quarter estimate formation begins
└── Stock settles at new equilibrium
        │
        ▼
LEARNING PHASE
│
├── System records outcome vs prediction
├── Evidence weights updated
├── Strategy win rate updated
└── New knowledge items created if pattern confirmed
```

---

### Lifecycle 2 — RBI Monetary Policy Event

```
PRE-EVENT PHASE (2-4 weeks before MPC)
│
├── CPI and GDP data analyzed
├── Economist forecasts form consensus
├── Market prices in expected decision
├── Options IV on rate-sensitive stocks rises
└── Bond market positioning begins
        │
        ▼
MPC MEETING PHASE (3 days)
│
├── Day 1-2: MPC deliberates (confidential)
├── Day 3: Governor reads statement
├── Vote tally published (6-0 to 4-2)
└── Press conference and forward guidance
        │
        ▼
IMMEDIATE REACTION PHASE (minutes to hours)
│
├── Bond yields reprice instantly
├── Rate-sensitive stocks react (banks, NBFCs, real estate)
├── INR adjusts
└── Equity index net effect (rate cut = positive for multiples)
        │
        ▼
TRANSMISSION PHASE (weeks to months)
│
├── Banks announce MCLR changes
├── Home loan EMIs adjust
├── Corporate borrowing costs change
├── Consumer demand responds
└── GDP and inflation transmission completes
        │
        ▼
SYSTEM LEARNING
│
├── Rate cycle knowledge updated
├── Rate sensitivity model recalibrated
└── Next MPC prediction model refreshed
```

---

### Lifecycle 3 — Rumour Event

```
RUMOUR INCEPTION
│
├── Information begins circulating (usually in trading community)
├── Appears on social media / WhatsApp groups
├── No authoritative confirmation
└── Price begins moving anomalously
        │
        ▼
RUMOUR AMPLIFICATION
│
├── Media picks up (often speculative)
├── Volume increases (informed/speculative trading)
├── Options OI builds (event anticipation)
└── System detects unusual volume/movement signal
        │
        ▼
RESOLUTION — FORK
│
├── CONFIRMATION PATH:
│   ├── Authoritative announcement confirms rumour
│   ├── Price adjusts to confirmed level
│   └── Learning event: prior signal was valid leading indicator
│
└── DENIAL PATH:
    ├── Authoritative denial published
    ├── Price may partially retrace
    ├── Or: denial disbelieved (price stays elevated — market suspects truth)
    └── Learning event: denial credibility assessed
        │
        ▼
SYSTEM HANDLING
│
├── Rumor classified: UNVERIFIED
├── Price movement marked as: RUMOUR_DRIVEN (not fundamental)
└── Thesis not updated until confirmation
```

---

### Lifecycle 4 — Market Regime Change Event

```
PRECONDITIONS
│
├── Prior regime has been in place (minimum 20 sessions)
├── Regime model has classified current state
└── Parameters defining regime are continuously monitored
        │
        ▼
TRANSITION SIGNALS
│
├── VIX crosses regime boundary
├── AD ratio deteriorates persistently
├── Volume pattern changes
└── Price action changes character (trending → choppy)
        │
        ▼
REGIME RECLASSIFICATION
│
├── Model detects boundary sustained for N sessions
├── Transition event fires
├── New regime assigned
└── All strategies get regime-adjusted weights
        │
        ▼
ADAPTATION PHASE
│
├── Position sizing recalibrated
├── Stop-loss widths adjusted (wider in high-vol regimes)
├── Strategy weights adjusted (momentum reduced; mean-reversion increased)
└── Evidence interpretation adjusts (same signal may have different meaning)
        │
        ▼
NEW STEADY STATE
│
└── System operates in new regime until next transition
```

---

### Lifecycle 5 — AI Signal-to-Decision Event Chain

```
MARKET DATA ARRIVES
│
├── Price update received
├── Volume update received
├── OI update received
└── News/data event received
        │
        ▼
INDICATOR CALCULATION
│
├── Technical indicators computed
├── Statistical measures updated
└── Anomaly detection run
        │
        ▼
SIGNAL GENERATION
│
├── Signal criteria evaluated
├── Signal fired if criteria met
└── Signal logged with timestamp
        │
        ▼
EVIDENCE ASSEMBLY
│
├── Signal added to hypothesis evidence set
├── Existing evidence checked for staleness
├── Evidence weighted by signal type accuracy
└── Total conviction score calculated
        │
        ▼
CONVICTION THRESHOLD EVALUATION
│
├── Score < 5.0: No action; continue monitoring
├── Score 5.0-6.5: Watch status; intensify monitoring
└── Score ≥ 6.5: THRESHOLD CROSSED → Decision phase
        │
        ▼
DEBATE AND DECISION PHASE
│
├── 5 AI agents debate (bull, bear, risk, macro, technical)
├── Devil's advocate challenges thesis
├── Risk Guardian assesses: kill switch? Limits?
└── Decision approved or rejected
        │
        ▼
EXECUTION
│
├── Order created with size, type, price
├── Order submitted to broker
└── Position created
        │
        ▼
MONITORING
│
├── Stop loss and target monitored continuously
├── Thesis validity monitored
└── Exit triggered by target, stop, or invalidation
        │
        ▼
LEARNING
│
├── Outcome recorded
├── Strategy performance updated
└── Knowledge item created or updated
```

---

### Lifecycle 6 — Black Swan Event

```
PRE-EVENT STATE
│
├── Normal conditions
├── System operating in baseline regime
└── No anticipation of extreme event
        │
        ▼
EVENT OCCURS (without warning)
│
├── COVID-19 pandemic declaration
├── Nuclear threat
├── Major financial institution failure
└── Unexpected geopolitical shock
        │
        ▼
IMMEDIATE IMPACT
│
├── Market gaps down severely
├── VIX spikes to extreme (45+)
├── Kill switch activates immediately
├── Circuit breakers may trigger
└── Liquidity disappears
        │
        ▼
UNCERTAINTY PHASE
│
├── Information is fragmentary
├── Contradictory news cycles
├── Extreme volatility (both up and down)
└── System remains in defensive mode
        │
        ▼
ASSESSMENT PHASE
│
├── Damage scope becomes clearer
├── Policy response anticipated/announced
├── System evaluates: structural vs temporary?
└── First recovery signals appear
        │
        ▼
RECOVERY OR STRUCTURAL CHANGE
│
├── V-shape recovery (if temporary event): COVID March 2020
│   └── System: re-enters market as kill switch clears
└── Structural change (if permanent): new regime established
    └── System: all models retrained on post-event data
```

---

### Lifecycle 7 — Learning Event

```
TRADE CLOSES (by target, stop loss, or time)
│
├── Exit price recorded
├── Entry price recalled
└── PnL calculated
        │
        ▼
OUTCOME CLASSIFICATION
│
├── WIN: Return > 0
├── LOSS: Return < 0
└── BREAKEVEN: Return within ±0.5%
        │
        ▼
LEARNING RECORD CREATION
│
├── Strategy: which strategy generated this trade
├── Market regime at time of entry
├── Evidence items that supported entry
├── Contradicting evidence (if any)
└── What actually happened vs what was predicted
        │
        ▼
METRICS UPDATE
│
├── Strategy win rate recalculated
├── Strategy average return recalculated
├── Evidence weight updated for each signal type used
└── Regime-specific performance tracked separately
        │
        ▼
KNOWLEDGE SYNTHESIS
│
├── Pattern confirmed: knowledge item reinforced
├── Pattern failed: knowledge item weakened or retired
└── New pattern discovered: knowledge item created
        │
        ▼
MODEL UPDATE
│
├── If degradation detected: retrain
└── If performance good: maintain
```

---

### Lifecycle 8 — Corporate Action (Bonus/Split) Event

```
BOARD DECISION
│
└── Board approves bonus issue or stock split
        │
        ▼
EXCHANGE FILING
│
├── BSE/NSE filing with terms
├── Record date announced
└── Ex-date derived (one day before record date under T+1)
        │
        ▼
MARKET ANTICIPATION
│
├── Stock may rally on announcement (positive signal)
└── Options chain adjusts to post-split strikes
        │
        ▼
EX-DATE
│
├── Stock opens at adjusted price (split-adjusted)
├── EPS, PE ratios recalculated on new base
└── Index constituent weight recalculated
        │
        ▼
RECORD DATE
│
└── Shareholder registry snapshot taken
        │
        ▼
ALLOTMENT
│
├── New shares credited to demat accounts
└── No change in economic value — only per-share price changes
        │
        ▼
SYSTEM UPDATE
│
├── Historical price series adjusted for split
├── Technical levels recalculated on split-adjusted basis
└── Knowledge items with price levels updated
```

---

### Lifecycle 9 — Alert Event

```
CONDITION DEFINED
│
├── Alert condition set: "VIX > 30"
└── Monitoring frequency: every 5 minutes
        │
        ▼
CONTINUOUS MONITORING
│
└── Each data cycle checks condition
        │
        ▼
THRESHOLD APPROACHED
│
├── System notes: approaching threshold (early warning)
└── Heightened monitoring frequency
        │
        ▼
THRESHOLD CROSSED
│
├── Alert fires
├── Alert logged with timestamp
└── Severity classified
        │
        ▼
NOTIFICATION
│
├── Telegram message sent to operator
├── Dashboard flag raised
└── Action queue populated
        │
        ▼
RESOLUTION
│
├── Operator acknowledges
├── System evaluates: automatic response or manual?
└── Condition resolves or persists
        │
        ▼
CLOSURE
│
├── Alert closed when condition no longer met
└── Alert logged for pattern analysis
```

---

## PART VI — EVENT PROPAGATION

*How one event causes another. The transmission of change through the investment universe.*

---

### Propagation Chain 1 — US Federal Reserve Rate Hike

```
US FED RAISES RATE BY 25BPS
        │
        ▼
US DOLLAR STRENGTHENS (DXY index rises)
        │
        ▼
EMERGING MARKET CURRENCIES WEAKEN
        │
        ├── INR DEPRECIATES (vs USD)
        │       │
        │       ├── FII SELLS INDIA (higher USD cost of holding INR assets)
        │       │       │
        │       │       └── NIFTY 50 FALLS
        │       │               │
        │       │               └── PORTFOLIO VALUE FALLS
        │       │
        │       └── INDIA IMPORT COSTS RISE
        │               │
        │               └── OIL IMPORT BILL INCREASES
        │                       │
        │                       └── TRADE DEFICIT WIDENS
        │                               │
        │                               └── FISCAL PRESSURE ON GOVERNMENT
        │
        ├── GLOBAL BOND YIELDS RISE
        │       │
        │       ├── INDIA G-SEC YIELDS RISE (capital outflow pressure)
        │       │       │
        │       │       └── BANK COST OF FUNDS RISES
        │       │               │
        │       │               └── MCLR RISES
        │       │                       │
        │       │                       └── EMI BURDEN ON CONSUMERS RISES
        │       │                               │
        │       │                               └── CONSUMER DEMAND FALLS
        │       │
        │       └── EQUITY MULTIPLES COMPRESS
        │               │
        │               └── HIGH-PE STOCKS FALL MORE (tech, consumer discretionary)
        │
        └── GLOBAL RISK-OFF EVENT
                │
                └── INDIA VIX SPIKES
                        │
                        └── KILL SWITCH EVALUATED (if VIX > 45)
```

---

### Propagation Chain 2 — Corporate Default (Credit Contagion)

```
COMPANY X DEFAULTS ON ₹5,000 CRORE BOND
        │
        ▼
RATING AGENCIES DOWNGRADE TO D (DEFAULT)
        │
        ├── MUTUAL FUND EXPOSURE REVEALED
        │       │
        │       └── MF NAV FALLS (for debt funds with exposure)
        │               │
        │               └── RETAIL REDEMPTION PRESSURE
        │                       │
        │                       └── MF FORCED SELLING OF OTHER BONDS
        │                               │
        │                               └── BOND MARKET ILLIQUIDITY INCREASES
        │
        ├── BANK EXPOSURE TO COMPANY X REVEALED
        │       │
        │       └── BANKS WITH HIGH EXPOSURE FACE NPA PROVISIONING
        │               │
        │               └── BANK EARNINGS ESTIMATES CUT
        │                       │
        │                       └── BANKING SECTOR INDEX FALLS
        │
        └── FEAR CONTAGION TO SECTOR PEERS
                │
                └── SIMILAR-PROFILE COMPANIES FACE RATING WATCH NEGATIVE
                        │
                        └── THEIR BORROWING COSTS RISE
                                │
                                └── SECTOR CREDIT FREEZE BEGINS
```

---

### Propagation Chain 3 — Strong Monsoon (Positive)

```
IMD ANNOUNCES ABOVE-NORMAL MONSOON
        │
        ▼
KHARIF CROP SOWING AREA EXPANDS
        │
        ├── FOOD INFLATION FALLS
        │       │
        │       ├── CPI BELOW RBI TARGET
        │       │       │
        │       │       └── RBI RATE CUT PROBABILITY RISES
        │       │               │
        │       │               └── BOND YIELDS FALL
        │       │                       │
        │       │                       └── RATE-SENSITIVE SECTORS RALLY
        │       │
        │       └── RURAL DISPOSABLE INCOME RISES (farmers earn more)
        │               │
        │               └── RURAL FMCG DEMAND RISES
        │                       │
        │                       └── FMCG VOLUME GROWTH ACCELERATES
        │                               │
        │                               └── FMCG EARNINGS ESTIMATES UPGRADED
        │
        └── TWO-WHEELER / TRACTOR DEMAND RISES
                │
                └── AUTO SECTOR VOLUME GROWTH UPGRADES
```

---

### Propagation Chain 4 — Earnings Acceleration Cycle

```
SECTOR BELLWETHER REPORTS STRONG BEAT
        │
        ▼
SECTOR THESIS CONFIRMED
        │
        ├── PEER COMPANY EXPECTATIONS UPGRADED
        │       │
        │       └── SECTOR INDEX RALLIES
        │               │
        │               └── FII FLOWS INCREASE INTO SECTOR
        │
        ├── CONVICTION SCORES FOR SECTOR POSITIONS INCREASE
        │       │
        │       └── POSITION SIZES INCREASED
        │
        └── SECTOR ANALYST CONSENSUS UPGRADES
                │
                └── TARGET PRICES RAISED
                        │
                        └── NEW INSTITUTIONAL BUYING
                                │
                                └── SECTOR LEADERSHIP IN NIFTY
```

---

### Propagation Chain 5 — AI Kill Switch Cascade

```
INDIA VIX CROSSES 45
        │
        ▼
KILL SWITCH ACTIVATED (RiskGuardian layer fires)
        │
        ├── ALL PENDING BUY DECISIONS CANCELLED
        │       │
        │       └── DECISION QUEUE EMPTIED
        │
        ├── EXISTING POSITIONS REVIEWED
        │       │
        │       └── STOP LOSSES TIGHTENED WHERE APPROPRIATE
        │
        ├── NEW CAPITAL ALLOCATION FROZEN
        │       │
        │       └── FREE CASH PRESERVED
        │
        └── OPERATOR TELEGRAM ALERT SENT
                │
                └── MANUAL REVIEW PHASE
                        │
                        └── VIX FALLS BELOW 45 FOR N SESSIONS
                                │
                                └── KILL SWITCH DEACTIVATED
                                        │
                                        └── NORMAL OPERATION RESUMES
```

---

### Propagation Chain 6 — Budget Positive Surprise

```
FINANCE MINISTER ANNOUNCES RECORD INFRASTRUCTURE SPEND
        │
        ▼
CAPITAL GOODS SECTOR RE-RATED UPWARD
        │
        ├── ORDER BOOK EXPECTATIONS RISE
        │       │
        │       └── CEMENT, STEEL DEMAND ESTIMATES RISE
        │               │
        │               └── INPUT SECTOR MARGINS IMPROVE
        │
        ├── LOGISTICS AND ROAD COMPANIES RALLY
        │       │
        │       └── CONSTRUCTION ANCILLARIES: RALLY
        │
        └── TAX REDUCTION ON PERSONAL INCOME (IF ANNOUNCED)
                │
                └── CONSUMER DISCRETIONARY DEMAND ESTIMATES RISE
                        │
                        └── AUTO, RETAIL, CONSUMER DURABLES RALLY
```

---

### Propagation Chain 7 — Geopolitical Oil Shock

```
OIL-PRODUCING NATION DISRUPTION (WAR / SANCTIONS)
        │
        ▼
CRUDE OIL SPIKES 30% IN 2 WEEKS
        │
        ├── INDIA OIL IMPORT BILL RISES
        │       │
        │       ├── CURRENT ACCOUNT DEFICIT WIDENS
        │       │       │
        │       │       └── INR WEAKENS
        │       │
        │       └── PETROLEUM SUBSIDY BURDEN RISES
        │               │
        │               └── FISCAL DEFICIT CONCERN
        │
        ├── AIRLINE COSTS EXPLODE
        │       │
        │       └── AVIATION SECTOR SELL-OFF
        │
        ├── PAINT / CHEMICAL SECTOR: INPUT COST SPIKE
        │       │
        │       └── MARGIN COMPRESSION THESIS ACTIVATES
        │
        └── OIL MARKETING COMPANIES: UNDER-RECOVERY RISK
                │
                └── HPCL, BPCL FALL ON MARGIN RISK
```

---

### Propagation Chain 8 — Social Media Sentiment Cascade

```
PROMINENT INFLUENCER POSTS BULLISH THESIS ON STOCK
        │
        ▼
RETAIL SOCIAL MEDIA ATTENTION RISES
        │
        ├── GOOGLE TRENDS: STOCK NAME SPIKES
        │       │
        │       └── RETAIL BUYING PRESSURE BUILDS
        │
        ├── OPTIONS CALL BUYING INCREASES
        │       │
        │       └── GAMMA EXPOSURE RISES FOR MARKET MAKERS
        │               │
        │               └── MARKET MAKERS DELTA HEDGE BY BUYING STOCK
        │                       │
        │                       └── PRICE RISES FURTHER (GAMMA SQUEEZE)
        │
        └── PRICE RISE GENERATES MORE SOCIAL MEDIA ATTENTION
                │
                └── FEEDBACK LOOP BUILDS
                        │
                        └── REVERSAL WHEN RETAIL INTEREST PEAKS
                                │
                                └── SHARP CORRECTION
```

---

## PART VII — EVENT CAUSALITY

*The formal framework for understanding cause and effect in the event universe.*

---

### 1 — Causal Taxonomy

**Direct Causation:** A causes B through a single, documented mechanism. The mechanism is traceable and testable.
- Example: RBI rate cut DIRECTLY CAUSES MCLR to fall (mechanism: bank cost of funds decreases)

**Indirect Causation:** A causes C through an intermediary B.
- Example: Fed rate hike INDIRECTLY CAUSES NIFTY to fall (through: DXY strength → FII selling → NIFTY decline)

**Probabilistic Causation:** A increases the probability of B, but does not make B certain.
- Example: Earnings miss PROBABILISTICALLY CAUSES analyst downgrade (probability ~70%)

**Contributory Causation:** A is one of several necessary conditions for B to occur.
- Example: Panic selling requires: (shock event) + (leverage in system) + (no institutional support)

**Counterfactual Causation:** B would not have occurred without A.
- Example: The IL&FS crisis would not have cascaded without the prior build-up of short-term borrowing by NBFCs

---

### 2 — Feedback Loops

**Positive Feedback Loop (Amplifying):** Output reinforces the initial cause — creates momentum.

```
Stock price RISES
        ↓
Retail investor confidence INCREASES
        ↓
More retail buying
        ↓
Price RISES FURTHER
        ↓
Media attention increases
        ↓
Even more buying
        ↓
[until exhaustion event]
```

**Negative Feedback Loop (Stabilizing):** Output dampens the initial cause — creates mean reversion.

```
Stock price FALLS significantly below fair value
        ↓
Value investors begin BUYING
        ↓
Price STABILIZES and RECOVERS
        ↓
Return opportunity DECREASES
        ↓
Value buying momentum slows
        ↓
Price stabilizes near fair value
```

---

### 3 — Cascade Events

A cascade occurs when a single event triggers a sequence of subsequent events, each amplifying the prior, with the final outcome far larger than the original event would suggest.

**Conditions for Cascade:**
1. High leverage in the system (margin, derivatives)
2. Interconnected exposures (many parties exposed to same asset)
3. Liquidity thinning (markets become illiquid during stress)
4. Information asymmetry (some parties know they're exposed, others don't yet)

**Cascade Identification Rules:**
- Event N is a cascade if its effect size is more than 2× the direct effect of the triggering event
- Cascade probability increases with: OI concentration + high leverage + illiquid market

**Famous Cascade Examples:**
- IL&FS (2018): ₹91,000 crore default → ₹1 lakh crore NBFC credit freeze → Franklin Templeton crisis
- COVID March 2020: Lockdown → GDP concern → FII outflow → NIFTY -38% → Global funds reduce EM allocation

---

### 4 — Second-Order and Third-Order Effects

**First-Order Effect:** The direct, immediate consequence of an event.
- Repo rate cut: Bond prices rise.

**Second-Order Effect:** The consequence of the first-order consequence.
- Bond prices rise → Bank HTM portfolio marks-to-market gains → Bank capital ratios improve → More lending headroom

**Third-Order Effect:** The consequence of the second-order effect.
- More lending headroom → Banks increase credit supply → Corporate investment increases → GDP growth accelerates

**System Rule:** The AI Trading Brain must reason to at least second-order effects for every major event. Third-order effects should be modeled for macro events (RBI, Budget, Fed).

---

### 5 — Circular Causality

Some events create feedback loops where effects feed back to cause:

**Example — Inflation and Interest Rates:**
```
Inflation rises
     ↓ (RBI raises rates)
Borrowing costs rise
     ↓ (demand falls)
Growth slows
     ↓ (employment pressure)
Government spends more
     ↓ (fiscal deficit increases)
Government borrows more
     ↓ (bond supply increases)
Bond yields rise
     ↓ (borrowing costs rise further)
     ↑ (inflation may persist if supply constraints remain)
```

**Example — Market Confidence and Flows:**
```
Market rises
     ↓
Investor confidence rises
     ↓
More SIP/DII inflows
     ↓
More buying pressure
     ↓
Market rises further
     ↑ (valuation eventually becomes stretched)
     ↓
Trigger event (rate hike, global shock)
     ↓
Sharp correction
```

---

### 6 — Root Cause Analysis

When an event occurs, the system should trace back to root cause:

**Root Cause Identification Protocol:**
1. What event triggered the observed outcome? (Proximate cause)
2. What caused the triggering event? (Mediate cause)
3. What structural condition made the system vulnerable? (Root cause)

**Example:**
- Observed: NBFC stock falls 20%
- Proximate cause: Credit rating downgrade
- Mediate cause: Earnings miss due to elevated NPAs
- Root cause: NBFC had borrowed short-term to lend long-term (structural mismatch)

**System implication:** The root cause analysis determines whether the thesis is truly invalidated (structural root cause) or temporarily impaired (proximate cause only).

---

### 7 — Event Networks

Complex events are networks of interconnected simpler events. Understanding the network structure is more valuable than analyzing individual events.

**NIFTY Bull Market 2020-2021 — Event Network:**

| Node Event | Connected To | Mechanism |
|---|---|---|
| COVID vaccine approval | Risk-on return | Global fear resolved |
| Fed QE | Global liquidity surge | Cheap money needs home |
| DII sustained buying | NIFTY support | 12-month SIP continuation |
| IT sector USD revenue | IT sector rally | INR depreciation + digital demand |
| RBI rate at historic low | Low borrowing cost | Equity valuation premium |
| FII return | Market breadth | EM risk appetite normalized |

**All six events in the same direction simultaneously = structural bull market**

---

## PART VIII — EVENT CONSTITUTION

*Twenty constitutional principles governing every event in this ontology.*

---

**Principle 1 — Events Cannot Exist Outside of Time**

Every event requires a timestamp. An event without a time is not a real-world occurrence — it is a hypothetical or fiction. The timestamp is the event's most fundamental attribute. All event timestamps must be stored in a standardized format with timezone (IST for market events) and accurate to the millisecond where possible. No event shall be recorded without a timestamp.

---

**Principle 2 — Events Are Immutable**

Once an event occurs, its occurrence is permanently fixed in history. The RBI's June 2026 rate decision happened at the moment it happened. It cannot be changed, recalled, or unreported. The system must treat every recorded event as permanent. What can change is interpretation — but the event itself cannot. The event log is the system's ground truth.

---

**Principle 3 — Events Always Have Cause**

Every event was triggered by a prior state, condition, or event. There are no uncaused events. The earnings beat was caused by business performance exceeding estimates. The business performance was caused by strategic decisions. The strategic decisions were caused by management quality and market opportunity. Causation chains are infinite in principle but finite in practical analysis. The system must trace causation back at least two levels.

---

**Principle 4 — Events Always Produce Effects**

No event occurs without consequence. Every event changes at least one entity's state. Some effects are trivial (routine filing); some are systemic (circuit breaker). But all events produce information at minimum — and information, once produced, is part of the permanent record. An event with no discernible effect is a null event — and null events should be filtered from the event log.

---

**Principle 5 — Events Can Produce New Events**

Events have children. The Fed rate hike (Event A) causes bond yield rise (Event B) which causes equity sell-off (Event C) which causes FII outflow from India (Event D) which causes India VIX spike (Event E) which activates the system's kill switch (Event F). This event ancestry chain must be tracked. Knowing that Event F was caused by Event A (3 causal hops away) is essential for calibrating response duration and severity.

---

**Principle 6 — Events May Invalidate Knowledge**

Every piece of knowledge in the system was derived from events that occurred in the past. When a new event occurs that contradicts that knowledge, the knowledge must be reviewed. "Interest rates rising is bad for bank stocks" is knowledge. "Bank stocks rally despite rising interest rates" is a new event. The knowledge item must be checked: is the new event an exception, or has the relationship changed? Events are the challenge mechanism for the knowledge base.

---

**Principle 7 — Events Update Entity States**

Every entity in the system has a current state and a history of states. Events are the transitions between states. HDFC Bank's credit rating was AA+ before the event (downgrade) and AA after. The event is the transition; the rating is the state. The system must track both: the current state of every entity and the complete sequence of events that produced that state.

---

**Principle 8 — Events Cannot Exist Without Context**

An earnings beat means different things in different contexts. A 5% EPS beat in a growing economy is neutral — market expected more. A 5% EPS beat during a severe economic contraction is extraordinary — analysts had feared a miss. Context includes: the market regime, the economic cycle, the sector conditions, and the system's prior conviction level. Every event must be interpreted in its context.

---

**Principle 9 — The Same Event Can Have Different Effects on Different Entities**

A rate hike is simultaneously:
- Negative for bond prices (yield rises, price falls)
- Negative for high-leverage companies (borrowing cost rises)
- Positive for bank NIMs (short-term lending rates reprice faster than deposits)
- Neutral for cash-rich companies (no debt, benefit from higher deposit rates)
- Negative for real estate (affordability falls)

One event → multiple effects. The system must propagate every event through all affected entities separately.

---

**Principle 10 — Event Magnitude Matters as Much as Event Type**

A 1% earnings beat has completely different implications from a 15% earnings beat. A VIX at 22 and a VIX at 46 both represent "VIX is elevated" — but the system's response must be radically different. Magnitude must be quantified for every event. "Event occurred" is insufficient. "Event occurred with magnitude X" is the required format.

---

**Principle 11 — Event Timing Relative to Entity State Determines Impact**

A positive earnings surprise has greater impact when:
- Short interest is high (forces covering)
- Analyst consensus was bearish (more surprise to cover)
- Valuation was depressed (buyers were waiting for confirmation)

The same earnings beat at a stretched valuation has less impact. Timing relative to entity state is a determinant of event impact — not just event content.

---

**Principle 12 — Composite Events Must Be Decomposed**

A "sector rotation event" is not a single event — it is the composite of: multiple earnings events, a macro data event, a flow event, and a behavioral event occurring in the same direction simultaneously. The system should decompose composite events into their constituent simpler events for analysis, while recognizing the composite as a meaningful pattern.

---

**Principle 13 — Event Frequency Is Itself Informative**

When events of the same type cluster in frequency — multiple credit downgrades in the same sector within 90 days, multiple earnings misses across the same sector — the frequency pattern is itself an event (SECTOR_CREDIT_STRESS_CLUSTER; EARNINGS_MISS_CLUSTER). Event frequency patterns must be monitored and treated as events.

---

**Principle 14 — Absence of Expected Events Is an Event**

If a company normally declares dividends in Q1 and Q1 passes without a dividend declaration, the absence of declaration is informative. If a promoter has been consistently buying shares for 12 months and stops, the cessation is informative. The system must monitor for expected events that fail to materialize — treating material absences as events with negative implication.

---

**Principle 15 — Events Have Discovery Delay**

The Occurred At and Discovered At timestamps for an event differ. A company's fraud may have started years before the investigation is announced. Insider information about a merger may be in circulation days before the official announcement. The system must account for information delay when reasoning about events — the event occurred when it occurred, not when the system learned of it.

---

**Principle 16 — Events Are Not Equally Reliable**

Some events are primary sources (RBI official statement → most reliable). Some are secondary (media report → medium reliability). Some are tertiary (social media → low reliability). Some are derived (AI system's signal → reliability = model accuracy). Event reliability must be tracked and used to weight the evidence the event produces.

---

**Principle 17 — Events Can Be Planned or Spontaneous**

Planned events (scheduled monetary policy, quarterly results) allow the system to prepare, position, and anticipate. Spontaneous events (geopolitical shock, corporate fraud discovery) require immediate response without preparation. The system must distinguish between planning and reaction modes based on event type.

---

**Principle 18 — Every AI System Action Is an Event**

Within the AI Trading Brain, every action is an event: signal generated, hypothesis created, decision approved, order submitted, position closed. These internal events are as important as external market events for system governance, audit, and learning. The internal event log is the basis for all system accountability and improvement.

---

**Principle 19 — Events Exist on Multiple Timescales Simultaneously**

An RBI rate cut is:
- An instantaneous event (at the moment of announcement)
- A session-level event (market repricing throughout the day)
- A multi-week event (MCLR transmission to economy)
- A multi-month event (GDP and credit demand response)
- A multi-year event (rate cycle history)

The same event operates differently at each timescale. Analysis must address all relevant timescales.

---

**Principle 20 — The Event Log Is the Ultimate Source of Truth**

All models, knowledge items, hypotheses, and decisions are interpretations of the event stream. When there is a conflict between what the system "believes" and what the event log shows actually happened, the event log wins. The event log should be:
- Permanent (never deleted, only archived)
- Immutable (events cannot be edited after recording)
- Complete (every event above the materiality threshold must be recorded)
- Auditable (any outcome can be traced to the events that caused it)

---

## PART IX — FUTURE EVOLUTION

*How the Event Ontology grows responsibly over the next decade.*

---

### Protocol for Adding New Event Types

When new event types emerge — from technology, market evolution, or regulatory change — they must be added following this 10-step protocol:

**Step 1 — Natural Language Definition**
Define the event precisely in plain English: what occurs, what entities it affects, what changes as a result.

**Step 2 — Differentiation**
Prove that the new event type is genuinely different from all existing types. If it is a variant of an existing type, add it as a sub-type rather than a new type.

**Step 3 — Trigger Definition**
Document the precise trigger condition: what must occur for this event to be classified as this type?

**Step 4 — Affected Entities**
List all entity types that this event can affect.

**Step 5 — Information and Knowledge Produced**
Document what this event reveals to the reasoning system.

**Step 6 — State Changes**
Document which entity states change when this event occurs.

**Step 7 — Lifecycle**
Provide the event's lifecycle model: from preconditions through resolution to learning.

**Step 8 — Examples**
Provide at least 3 real-world examples from financial history.

**Step 9 — Assign Code**
Assign the next available event code (continuing the alphanumeric sequence from the appropriate group).

**Step 10 — Test with Constitutional Principles**
Verify that the new event type satisfies all 20 constitutional principles.

---

### Backward Compatibility Commitments

1. **Existing event codes are never reassigned** — EVT-001 through EVT-060 always refer to the events defined here
2. **Existing group structures are preserved** — Groups A through N remain; new groups may be added but existing groups are not reorganized
3. **Existing attribute definitions are preserved** — 20 mandatory attributes remain; additional attributes may be added
4. **Historical event records remain valid** — any event recorded under a prior definition remains valid as a historical record
5. **Taxonomies are extended, not replaced** — new dimensions may be added to taxonomy; existing dimensions are not removed

---

### Anticipated Future Event Types

| Future Event | Driver | Horizon |
|---|---|---|
| Central Bank Digital Currency Issuance | RBI CBDC rollout | 2-4 years |
| AI-Generated Signal Consensus | Multiple AI systems convergence | 2-3 years |
| Carbon Credit Price Event | ESG framework maturation | 3-5 years |
| DeFi Protocol Event (India-regulated) | Crypto regulation | 4-6 years |
| Tokenized Asset Transfer | Asset tokenization | 3-5 years |
| Social Score Impact Event | Alternative credit scoring | 2-4 years |
| Quantum Computing Disruption Event | Technology | 5-10 years |
| Space Economy Revenue Event | Commercial space sector | 5-8 years |
| Autonomous Vehicle Adoption Milestone | Technology inflection | 3-6 years |
| AI Regulatory Event (India) | AI governance | 2-4 years |
| Real-Time GDP Data Release | Statistical modernization | 2-4 years |
| ESG Mandate Threshold | Regulatory ESG requirement | 2-3 years |

---

### Deprecation Policy

Event types may be deprecated when:
1. The triggering condition is no longer possible (e.g., instrument no longer exists)
2. The event type has been superseded by a more precise definition
3. Zero instances have been observed in 5+ years

Deprecated event types are:
- Marked as DEPRECATED with deprecation date
- Never removed from the ontology
- Kept in archive section for historical reference

---

### Versioning

The Event Ontology follows semantic versioning:
- **Major version (X.0):** Constitutional principle changes or fundamental redefinition of existing event types
- **Minor version (X.Y):** New event types or groups added
- **Patch version (X.Y.Z):** Clarifications, additional examples, documentation improvements

Current version: **1.0** — as of July 1, 2026

---

## EVENT COUNT SUMMARY

| Group | Name | Event Types Defined |
|---|---|---|
| A | Corporate Events | 82 |
| B | Market Structure Events | 53 |
| C | Macro-Economic Events | 46 |
| D | Geopolitical Events | 38 |
| E | Flow Events | 27 |
| F | Regulatory and Legal Events | 27 |
| G | News, Information, and Sentiment | 29 |
| H | Alternative Data Events | 20 |
| I | AI and System Events | 42 |
| J | Lifecycle and Calendar Events | 20 |
| K | Social and Behavioral Events | 10 |
| L | ESG Events | 10 |
| M | Global Contagion Events | 10 |
| N | Composite and Multi-Source Events | 10 |
| **Total** | | **424 event types** |

*Full definitions provided for EVT-001 through EVT-060 (60 critical events with 20+ attributes each).*
*Vocabulary coverage: all 424 event types named and described in Part II.*
*Constitutional framework: 20 principles governing all events.*
*Lifecycle models: 9 complete lifecycle diagrams.*
*Propagation chains: 8 complete multi-hop propagation chains.*

---

## DOCUMENT HISTORY

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-07-01 | Initial authoritative event ontology — 424 event types across 14 groups, 60 fully defined with 20+ attributes, 9 lifecycle models, 8 propagation chains, 20 constitutional principles |

---

*This document answers the question: "What changes the state of entities?"*
*Every event that can occur in the investment universe is named here.*
*Every state transition requires an event. Every event is immutable. Every event is timestamped.*
*Before recording any state change in any system, the event that caused it must exist in this ontology.*
*Extend this document before creating any event type not already defined here.*
