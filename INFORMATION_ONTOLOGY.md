# INFORMATION ONTOLOGY
## AI Trading Brain — Complete Dictionary of Investment Information

**Version:** 1.0  
**Status:** Authoritative  
**Date:** 2026-07-01  
**Parent Document:** MASTER_KNOWLEDGE_ARCHITECTURE.md  
**Classification:** Architecture — Not Implementation

---

> *This document is the Dictionary of the AI Trading Brain.  
> Every intelligence module, every evidence type, every knowledge pattern,  
> and every decision input must be expressible within the ontology defined here.  
> If something cannot be classified here, the ontology must be extended — not bypassed.*

---

## HOW TO READ THIS DOCUMENT

### Temporal Classification Legend

| Class | Meaning |
|-------|---------|
| **Static** | Changes rarely or never — exchange rules, entity identifiers, structural facts |
| **Slow Changing** | Changes over weeks/months — fundamentals, governance, relationships |
| **Daily** | Refreshed once per trading session |
| **Intraday** | Multiple updates within a session |
| **Tick Level** | Changes with every market transaction |
| **Event Driven** | Updated only when a specific event occurs |
| **Derived** | Computed from other information — has no independent source |
| **Learned** | Produced by the system's own intelligence layer |
| **Predictive** | Forward-looking estimate; carries probability, not certainty |

### Column Key for Information Type Tables

- **K** = Can generate Knowledge (Y/N)  
- **Rec** = Can generate Recommendations (Y/N)  
- **Ri** = Can generate Risk signals (Y/N)

---

## SECTION I — META-DOMAIN A: MARKET & PRICE INFORMATION

*The foundation layer. All investment intelligence begins with accurate observation of market prices, structure, and participant behavior.*

---

### DOMAIN 1 — Market Structure Information

**Definition:** The rules, architecture, and operational parameters that govern how a market functions.  
**Why It Matters:** Market structure defines the constraints within which all information is produced and all decisions execute.  
**Overall Classification:** Static to Slow Changing

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Exchange Architecture | Segments (cash, F&O, currency), lot sizes, tick sizes, margin frameworks | Static | All | Exchange | High | Y | N | Y |
| Trading Session Structure | Pre-open, continuous, closing auction times and rules | Static | All | Exchange | High | Y | N | N |
| Circuit Breaker Rules | Index-level and scrip-level circuit limits | Slow Changing | Indices, Equities | Exchange/SEBI | High | Y | N | Y |
| Settlement Mechanism | T+1/T+2, physical vs cash settlement, auction process | Slow Changing | Equities, Derivatives | Exchange | High | Y | N | Y |
| Market Holidays | Official NSE/BSE holiday calendar | Static-Annual | All | Exchange | High | N | N | N |
| Regulatory Framework | SEBI rules governing trading, disclosure, manipulation | Slow Changing | All | SEBI | High | Y | N | Y |
| F&O Ban List | Securities under derivative trading ban due to OI limits | Daily | Derivatives | Exchange | High | Y | Y | Y |
| Index Lot Sizes | Contract multipliers for index derivatives | Slow Changing | Indices | Exchange | High | Y | Y | Y |

**Key Relationships:** F&O Ban status → reduces derivative liquidity → constrains position sizing. Circuit breakers → affect exit execution → increase liquidity risk. Settlement rules → determine holding cost and cash flow timing.

---

### DOMAIN 2 — Price Behavior Information

**Definition:** All information derived from the movement, level, and pattern of an entity's price over time.  
**Why It Matters:** Price is the aggregated opinion of all market participants. Price behavior encodes supply/demand imbalances, sentiment, and collective intelligence.  
**Overall Classification:** Tick Level to Daily, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| OHLCV Data | Open, High, Low, Close, Volume per session or intraday bar | Intraday/Daily | Equities, Indices, FX, Commodities | Exchange Feed | High | Y | Y | Y |
| Price Relative to Universe | Stock's performance vs index/sector over rolling periods | Daily | Equities | Derived | High | Y | Y | Y |
| Price Momentum | Rate of price change over defined lookback periods | Daily | Equities, Indices | Derived | Medium | Y | Y | Y |
| 52-Week High/Low | Current price relative to annual range extremes | Daily | Equities | Derived | Medium | Y | Y | Y |
| Price Level Significance | Historical support and resistance levels with conviction scores | Daily | Equities, Indices | Derived/Learned | Medium | Y | Y | Y |
| Gap Structure | Unfilled price gaps and their structural significance | Daily | Equities, Indices | Derived | Medium | Y | Y | N |
| All-Time High/Low | Price relative to absolute historical extremes | Daily | Equities | Derived | Medium | Y | Y | Y |
| Multi-Timeframe Alignment | Directional agreement across weekly, daily, hourly timeframes | Intraday/Daily | Equities | Derived | Medium | Y | Y | N |
| Price Compression | Low-range consolidation periods preceding potential breakout | Daily | Equities | Derived/Learned | Low-Medium | Y | Y | N |

**Key Relationships:** Price level → interacts with volume → confirms or questions significance. Price vs 52W high → indicator of momentum and float rotation. Price behavior vs sector → reveals relative strength or weakness.

---

### DOMAIN 3 — Volume Behavior Information

**Definition:** All information derived from the quantity of shares or contracts traded, and the nature of that trading activity.  
**Why It Matters:** Volume represents commitment. Price moves without volume are unconfirmed hypotheses. Volume patterns reveal institutional conviction, accumulation, and distribution.  
**Overall Classification:** Tick Level to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Total Traded Volume | Shares traded in a session vs historical average | Daily | Equities | Exchange | High | Y | Y | N |
| Delivery Volume | Shares resulting in actual delivery vs speculative trading | Daily | Equities | Exchange/NSE Bhav | High | Y | Y | N |
| Delivery Percentage | Ratio of delivery to total traded volume | Daily | Equities | Derived | High | Y | Y | N |
| Volume Spike Detection | Sessions where volume exceeds N-sigma above historical mean | Daily/Event | Equities | Derived | High | Y | Y | Y |
| Volume-Price Relationship | Whether high-volume sessions correspond with price advance or decline | Daily | Equities | Derived | High | Y | Y | Y |
| Institutional vs Retail Volume | Proportion of volume attributable to large vs small participants | Daily | Equities | Derived/Market Depth | Medium | Y | Y | N |
| Intraday Volume Distribution | Volume distribution across intraday periods — morning, midday, close | Intraday | Equities | Exchange | Medium | Y | N | N |
| Volume Dry-Up | Progressively declining volume in a trading range | Daily | Equities | Derived | Medium | Y | Y | N |
| Delivery Trend | Multi-day trend in delivery percentage | Daily | Equities | Derived | High | Y | Y | N |

**Key Relationships:** High delivery % + price rise → genuine accumulation signal. Volume spike + price stagnation → potential distribution. Volume vs open interest → reveal cash vs derivative dominance.

---

### DOMAIN 4 — Market Breadth Information

**Definition:** Aggregate measurements of participation and health across the entire market or a defined universe.  
**Why It Matters:** Breadth reveals whether a market move is broad and healthy or narrow and fragile. Breadth divergence from price is among the most reliable leading indicators of regime change.  
**Overall Classification:** Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Advance-Decline Ratio | Number of advancing vs declining stocks in a session | Daily | Market, Sectors | Exchange | High | Y | Y | Y |
| Advance-Decline Line | Cumulative net advances over time | Daily | Market | Derived | High | Y | Y | Y |
| % Stocks Above Key MAs | Proportion of stocks trading above 50/150/200-day MAs | Daily | Market, Sectors | Derived | High | Y | Y | Y |
| 52-Week High Count | Number of stocks making new 52-week highs in a session | Daily | Market, Sectors | Exchange | High | Y | Y | N |
| 52-Week Low Count | Number of stocks making new 52-week lows in a session | Daily | Market, Sectors | Exchange | High | Y | Y | Y |
| Sector Breadth | Advance-decline within each sector independently | Daily | Sectors | Derived | High | Y | Y | Y |
| New High / New Low Ratio | Ratio of new 52W highs to new 52W lows | Daily | Market | Derived | High | Y | Y | Y |
| Equal-Weight vs Cap-Weight Divergence | Performance difference between equal-weighted and cap-weighted index | Daily | Market, Indices | Derived | High | Y | Y | Y |

**Key Relationships:** Narrow breadth + index at high → fragile rally, elevated distribution risk. Broad breadth + rising index → genuine bull phase. Sector breadth leading index breadth → early regime shift signal.

---

### DOMAIN 5 — Market Microstructure Information

**Definition:** The mechanics of how transactions occur — the bid, ask, order types, market maker behavior, and the immediate supply/demand interaction.  
**Why It Matters:** Microstructure reveals real-time supply/demand imbalances, institutional order flow, and execution risk.  
**Overall Classification:** Tick Level to Intraday

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Bid-Ask Spread | Difference between best buy and sell prices | Tick | Equities, Derivatives | Exchange Feed | High | Y | N | Y |
| Order Book Depth | Volume available at each price level above/below current price | Tick | Equities | Exchange | High | Y | N | Y |
| Large Order Detection | Identification of block-sized orders being worked in the market | Intraday | Equities | Exchange/Derived | Medium | Y | Y | N |
| VWAP Position | Price relative to volume-weighted average price | Intraday | Equities | Derived | High | Y | Y | N |
| Market Impact Cost | Estimated price slippage for a position of given size | Intraday/Daily | Equities | Derived | Medium | Y | N | Y |
| Quote Stuffing / Manipulation Flags | Abnormal order placement/cancellation patterns | Tick | Equities | Derived | Low | N | N | Y |
| Dark Pool Prints | Large off-exchange transactions reported post-trade | Event/Daily | Equities | Exchange | Medium | Y | Y | N |
| Uptick Rule / Short Sell Flags | Exchange-flagged short-sale activity signals | Daily | Equities | Exchange | Medium | Y | N | Y |

**Key Relationships:** Wide spreads + thin book → high execution risk. Large order detection + price level → institutional accumulation signal. Impact cost → determines minimum size threshold for trading decisions.

---

### DOMAIN 6 — Liquidity Information

**Definition:** The ease and cost at which a position can be entered or exited without materially moving the market.  
**Why It Matters:** Liquidity defines the system's operating boundary. Decisions about illiquid instruments carry exit risk that can dominate P&L outcomes.  
**Overall Classification:** Daily to Intraday

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Average Daily Volume | Mean daily traded volume over rolling periods | Daily | Equities | Derived | High | Y | Y | Y |
| Free Float | Shares available for trading after promoter lock-in | Slow Changing | Equities | Exchange/BSE | High | Y | Y | Y |
| Promoter Pledge Percentage | Proportion of promoter holding pledged as collateral | Slow Changing | Equities | Exchange | High | Y | Y | Y |
| Shares in Lock-In | Shares under regulatory or contractual lock-in | Slow Changing | Equities | Exchange | High | Y | Y | Y |
| Liquidity Regime | Current market-wide liquidity condition (abundant/normal/stressed) | Daily | Market | Derived | Medium | Y | Y | Y |
| Option Open Interest (Liquidity) | Depth of options liquidity for a given strike and expiry | Daily | Derivatives | Exchange | High | Y | Y | Y |
| Bid-Ask as % of Price | Spread as a proportion of mid-price | Intraday | Equities | Derived | High | Y | N | Y |
| Days to Liquidate | Estimated sessions to exit a position at 10-20% of ADTV | Daily | Equities | Derived | High | Y | Y | Y |

**Key Relationships:** Low free float → high manipulation risk, increased volatility. High promoter pledge → financial stress signal, forced-selling risk. Liquidity regime → affects position sizing across all decisions.

---

### DOMAIN 7 — Volatility Information

**Definition:** The magnitude and character of price fluctuation — both historical and implied by options markets.  
**Why It Matters:** Volatility is the primary determinant of risk and the key input to position sizing. It encodes market uncertainty and regime character.  
**Overall Classification:** Intraday to Daily, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Historical Volatility (HV) | Annualized standard deviation of returns over rolling windows | Daily | Equities, Indices | Derived | High | Y | Y | Y |
| Implied Volatility (IV) | Market's expectation of future volatility derived from options prices | Intraday/Daily | Equities, Indices | Derived | High | Y | Y | Y |
| IV vs HV Relationship | Whether options are pricing more/less volatility than realized | Daily | Equities | Derived | High | Y | Y | Y |
| India VIX | NIFTY 50 options-implied 30-day volatility index | Daily | Market | NSE | High | Y | Y | Y |
| Volatility Regime | Current characterization: low/medium/high/extreme | Daily | Market | Derived/Learned | High | Y | Y | Y |
| IV Rank (IVR) | Current IV percentile relative to past 52 weeks | Daily | Equities | Derived | High | Y | Y | Y |
| IV Skew | Difference in IV between puts and calls at equidistant strikes | Daily | Equities | Derived | Medium | Y | Y | Y |
| Volatility Term Structure | IV relationship across near/mid/far expiries | Daily | Equities, Indices | Derived | Medium | Y | Y | N |
| Realized vs Expected Volatility | Gap between what options implied and what actually occurred | Daily | Equities | Derived | High | Y | N | N |
| Volatility Clustering | Periods of elevated or suppressed volatility persisting | Daily | Equities | Derived/Learned | Medium | Y | Y | Y |

**Key Relationships:** India VIX > 25 → systemic fear, positions should be sized smaller. IV skew rising → market pricing tail risk asymmetrically. HV expansion → position sizing reduction required. Low IV regime → options relatively cheap → favorable for protection strategies.

---

### DOMAIN 8 — Technical / Chart Structure Information

**Definition:** Patterns, levels, and structural formations derived from price and volume history that represent supply/demand equilibria and directional tendency.  
**Why It Matters:** Chart structure encodes the collective memory of market participants — the prices at which they have bought, sold, and been trapped. These levels have forward predictive value because participants remember them.  
**Overall Classification:** Daily, Derived, Learned

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Trend Structure | Higher highs/lows (uptrend) vs lower highs/lows (downtrend) | Daily | Equities, Indices | Derived | High | Y | Y | Y |
| Support/Resistance Levels | Price zones where supply or demand has historically reversed | Daily | Equities, Indices | Derived/Learned | Medium | Y | Y | Y |
| Chart Pattern Formation | Recognized formations: base, wedge, flag, H&S, cup | Daily | Equities | Derived | Medium | Y | Y | N |
| Moving Average Structure | Price relative to key MAs and MA alignment | Daily | Equities, Indices | Derived | High | Y | Y | Y |
| Relative Strength (RS Line) | Price ratio of stock vs benchmark index | Daily | Equities | Derived | High | Y | Y | N |
| Trend Slope & Angle | Rate and angle of the prevailing trend | Daily | Equities | Derived | Medium | Y | Y | N |
| Base Depth & Length | Duration and percentage depth of consolidation patterns | Daily | Equities | Derived/Learned | Medium | Y | Y | N |
| Pivot Points | Calculated levels derived from prior session high/low/close | Daily | Equities, Indices | Derived | Medium | N | Y | N |
| Multi-Timeframe Trend Alignment | Whether short, medium, long-term trends are in agreement | Daily | Equities | Derived | High | Y | Y | N |

**Key Relationships:** Chart structure + volume → confirms or negates pattern significance. RS Line vs sector trend → identifies leaders and laggards. MA alignment → determines trend health and momentum sustainability.

---

## SECTION II — META-DOMAIN B: MACRO, POLICY & GLOBAL INFORMATION

*The macro environment is the tide. Individual companies are boats. The tide determines how many boats rise and fall.*

---

### DOMAIN 9 — Macro Economic Information

**Definition:** Aggregate measures of the economy's health, growth, and structural condition.  
**Why It Matters:** Macro determines the fundamental environment for corporate earnings, consumer demand, credit availability, and investor risk appetite.  
**Overall Classification:** Slow Changing, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| GDP Growth Rate | Quarter-on-quarter and year-on-year economic growth | Event/Quarterly | Market, All Sectors | MoSPI | High | Y | Y | Y |
| Consumer Price Inflation (CPI) | Measure of consumer goods and services price changes | Monthly/Event | Market, Consumer | MoSPI/RBI | High | Y | Y | Y |
| Wholesale Price Index (WPI) | Producer-level inflation measure | Monthly | Industrial, Materials | DIPP | High | Y | Y | Y |
| Industrial Production (IIP) | Output index for industrial sectors | Monthly | Industrial Sectors | MoSPI | Medium | Y | Y | N |
| Unemployment Rate | Proportion of labor force without employment | Monthly | Consumer Sectors | MOSPI/CMIE | Medium | Y | Y | Y |
| Current Account Deficit | Trade in goods and services balance with rest of world | Quarterly | Market, FX | RBI | High | Y | Y | Y |
| Fiscal Deficit | Government revenue vs expenditure gap | Monthly/Annual | Market, Bonds | MoF | High | Y | Y | Y |
| PMI Manufacturing & Services | Survey-based leading indicators of economic activity | Monthly | Sectors, Market | S&P Global | High | Y | Y | Y |
| Bank Credit Growth | Year-on-year growth in bank lending to industry and consumers | Monthly | Banking, Economy | RBI | High | Y | Y | N |
| GST Collections | Monthly goods and services tax revenue | Monthly | Market, Economy | MoF | High | Y | Y | N |
| Core Sector Output | Output of 8 core infrastructure sectors | Monthly | Infrastructure | DIPP | Medium | Y | N | N |

**Key Relationships:** High inflation → RBI tightening → rate-sensitive sectors decline. Strong IIP + PMI → earnings upgrade cycle. Current account deficit widening → INR depreciation pressure → IT sector benefits.

---

### DOMAIN 10 — Monetary Policy Information

**Definition:** Central bank decisions, communications, and actions that govern money supply, interest rates, and credit conditions.  
**Why It Matters:** Monetary policy is the single most powerful influence on asset valuations. It determines the risk-free rate, the cost of capital, and the liquidity available for investment.  
**Overall Classification:** Event Driven, Slow Changing

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Repo Rate | RBI's benchmark lending rate to commercial banks | Event/Slow | All | RBI | High | Y | Y | Y |
| Reverse Repo Rate | Rate at which banks park funds with RBI | Event/Slow | Banking | RBI | High | Y | Y | N |
| Cash Reserve Ratio (CRR) | Mandatory reserve banks must hold with RBI | Event/Slow | Banking | RBI | High | Y | Y | N |
| Statutory Liquidity Ratio (SLR) | Mandatory liquid assets banks must hold | Event/Slow | Banking | RBI | Medium | Y | N | N |
| RBI Policy Stance | Accommodative / neutral / withdrawal of accommodation | Event | All | RBI | High | Y | Y | Y |
| Open Market Operations | RBI's bond purchases/sales to manage liquidity | Event | Bonds, Banking | RBI | High | Y | Y | N |
| System Liquidity | Daily excess/deficit liquidity in the banking system | Daily | Banking, Bonds | RBI | High | Y | Y | N |
| Inflation Target Status | RBI's 4% CPI target — above/within/below band | Monthly | All | Derived | High | Y | Y | Y |
| Forward Guidance Language | Tone and signals in RBI policy statements | Event | All | RBI MPC | Medium | Y | Y | N |
| Fed Funds Rate (US) | US Federal Reserve benchmark rate — global cost of capital reference | Event | All, FX | US Fed | High | Y | Y | Y |

**Key Relationships:** Rate hike → discounts future earnings → PE compression → equity valuations decline. Rate cut → opposite. System liquidity surplus → lower short rates → NBFC/housing finance benefit. Fed rate vs RBI rate differential → determines FII debt flow direction.

---

### DOMAIN 11 — Fiscal Policy Information

**Definition:** Government taxing, spending, borrowing, and investment decisions.  
**Why It Matters:** Fiscal policy determines sectoral allocation of government capital, creates winners and losers across industries, and influences infrastructure investment cycles.  
**Overall Classification:** Event Driven (Union Budget), Slow Changing

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Union Budget Allocations | Sector-wise spending by central government | Annual/Event | All Sectors | MoF | High | Y | Y | Y |
| Capital Expenditure Plan | Government's multi-year infrastructure investment program | Annual | Infra, Capital Goods | MoF | High | Y | Y | N |
| Tax Policy Changes | Changes to corporate tax, capital gains tax, securities transaction tax | Annual | All | MoF | High | Y | Y | Y |
| Subsidies & Support Schemes | Government support programs for specific sectors | Event | Consumer, Agri, Energy | MoF | Medium | Y | Y | N |
| Disinvestment / PSU Privatization | Government sale of stakes in public sector companies | Event | PSUs | MoF/DIPAM | High | Y | Y | N |
| Production-Linked Incentive (PLI) | Sector-specific incentive programs for domestic manufacturing | Event/Slow | Manufacturing | MoF | High | Y | Y | N |
| Borrowing Program | Government's market borrowing calendar and amounts | Quarterly | Bonds | RBI/MoF | High | Y | N | Y |
| State Budgets | State-level spending that affects regional and sector dynamics | Annual | Regional, Infra | State Finance | Medium | Y | N | N |

**Key Relationships:** High capex allocation → capital goods, cement, steel, construction benefit. Tax cuts → consumption sectors, consumer discretionary benefit. Disinvestment → PSU share supply overhang. PLI → domestic manufacturing capacity expansion over 3-5 years.

---

### DOMAIN 12 — Regulatory Policy Information

**Definition:** Rules, guidelines, and enforcement actions by market, sector, and industry regulators.  
**Why It Matters:** Regulation determines operational boundaries, cost structures, and competitive dynamics within industries.  
**Overall Classification:** Event Driven, Slow Changing

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| SEBI Regulations | Rules governing trading, disclosure, insider trading, corporate governance | Slow/Event | All Listed | SEBI | High | Y | N | Y |
| Banking Regulations | RBI guidelines on capital requirements, lending norms, asset classification | Slow/Event | Banking | RBI | High | Y | Y | Y |
| Sector-Specific Regulation | Telecom (TRAI), Insurance (IRDAI), Pharma (CDSCO), Power (CERC) | Slow/Event | Sector | Respective Regulator | High | Y | Y | Y |
| NCLT / Insolvency Orders | Bankruptcy, resolution, and restructuring proceedings | Event | Company | NCLT | High | Y | Y | Y |
| Antitrust / CCI Rulings | Competition Commission orders, merger approvals, penalties | Event | Companies | CCI | High | Y | Y | Y |
| Environmental Regulations | Pollution norms, green energy mandates, carbon obligations | Slow/Event | Industrial, Energy | MoEF | Medium | Y | N | Y |
| Import/Export Policy | Tariff changes, import duties, export restrictions | Event | Commodities, Manufacturing | DGFT | High | Y | Y | Y |
| FDI Policy | Sectoral limits and conditions for foreign investment | Slow/Event | Sectors | DPIIT | High | Y | Y | N |

**Key Relationships:** SEBI margin regulation changes → derivatives activity, broker volumes. RBI NPA classification rules → banking sector provisioning cycles. Import duty changes → domestic manufacturers vs importers.

---

### DOMAIN 13 — Geopolitical Information

**Definition:** Relationships, conflicts, alliances, and tensions between nations that affect trade, capital flows, and market confidence.  
**Why It Matters:** Geopolitical events create sudden regime shifts in risk appetite, capital flows, and commodity prices.  
**Overall Classification:** Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Military Conflicts | Active wars and their proximity to trade routes and supply chains | Event | Commodities, Market | News | Low | Y | N | Y |
| Trade Disputes & Tariffs | Bilateral trade wars, tariff escalations, trade deal negotiations | Event/Slow | Exports, Manufacturing | News/Government | Medium | Y | Y | Y |
| Sanctions | Restrictions on trade with specific nations | Event | Commodities, Companies | News/Government | High | Y | Y | Y |
| Diplomatic Relations | India's bilateral relationships with trade partners | Slow/Event | Sectors, FX | News | Medium | Y | N | Y |
| Global Supply Chain Disruption | Events affecting critical supply chains (Suez, Taiwan Strait) | Event | Commodities, Manufacturing | News | Medium | Y | N | Y |
| Election Cycles (Global) | Major elections creating policy uncertainty or change | Event | Markets, FX, Sectors | Electoral Bodies | Medium | Y | Y | Y |
| India Domestic Political Events | State elections, coalition dynamics, policy continuity signals | Event | Market, Sectors | News | High | Y | Y | Y |

**Key Relationships:** Middle East conflict → oil price shock → OMC, aviation, chemicals affected. India-China tension → defensive sector premium, border infrastructure spending. US election → dollar policy → EM capital flow direction.

---

### DOMAIN 14 — Global Market Information

**Definition:** The state of international equity, bond, currency, and commodity markets that influence Indian market direction and risk appetite.  
**Why It Matters:** India is integrated with global markets. Global risk sentiment, capital allocation decisions by foreign institutions, and cross-market correlations affect daily Indian market behavior.  
**Overall Classification:** Intraday to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| S&P 500 Direction & Magnitude | US equity market daily performance | Daily | Market, IT | Exchange | High | Y | Y | Y |
| Nasdaq Composite | US technology index — primary influence on Indian IT | Daily | IT Sector | Exchange | High | Y | Y | Y |
| Nikkei 225 | Japanese equity market — Asian risk appetite proxy | Daily | Market | Exchange | Medium | Y | Y | N |
| Hang Seng | Hong Kong/Chinese markets — EM and Asian bellwether | Daily | Market, Metals | Exchange | Medium | Y | Y | Y |
| Dow Jones Industrial Average | US blue-chip index — global risk tone | Daily | Market | Exchange | Medium | Y | Y | N |
| MSCI Emerging Markets Index | Peer EM performance — FII allocation signals | Daily | Market | MSCI | High | Y | Y | Y |
| European Indices (DAX, CAC, FTSE) | European market health and risk tone | Daily | Market | Exchange | Low-Medium | Y | N | N |
| SGX Nifty | Singapore-listed Nifty futures — pre-open Indian market signal | Intraday | Market | SGX | High | Y | Y | N |
| Global Risk-On/Risk-Off Signal | Aggregate characterization of global market sentiment | Daily | All | Derived | High | Y | Y | Y |

**Key Relationships:** S&P 500 strong → FII flows to EM → Indian market benefits. MSCI EM outperforming → India attracts incremental allocation. Global risk-off → FIIs sell EM including India → broad decline.

---

### DOMAIN 15 — Cross-Asset Information

**Definition:** Signals derived from the relationship between different asset classes — equities, bonds, currencies, commodities, credit.  
**Why It Matters:** Cross-asset relationships encode the most important macro signals. When bonds, equities, and currencies are in conflict, one of them is wrong — and identifying which is a significant intelligence advantage.  
**Overall Classification:** Daily, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Equity-Bond Relationship | Correlation between equity and bond price movements | Daily | Market | Derived | High | Y | Y | Y |
| Credit Spread Signal | Investment-grade and high-yield spread widening/tightening | Daily | Market | Derived | High | Y | Y | Y |
| Dollar vs Equity Correlation | USD strength vs EM equity performance relationship | Daily | Market, FX | Derived | High | Y | Y | Y |
| Gold vs Risk Assets | Gold price behavior as a safe-haven demand indicator | Daily | Market | Derived | Medium | Y | Y | Y |
| Yield Curve Shape | Difference between long-term and short-term rates | Daily | Market, Banking | Derived | High | Y | Y | Y |
| Commodity vs Inflation Trade | Raw material price trends and their earnings implications | Daily | Materials, Consumer | Derived | High | Y | Y | Y |
| Risk Parity Signal | When multiple asset classes decline simultaneously | Daily | Market | Derived | High | N | N | Y |

**Key Relationships:** Inverted yield curve → recession signal → defensive sector rotation. Credit spreads widening + equity rising → unsustainable divergence. Strong dollar → EM outflows → Indian market pressure.

---

### DOMAIN 16 — Currency / FX Information

**Definition:** Exchange rate movements and the factors that drive them.  
**Why It Matters:** For India, the INR/USD rate affects import costs, inflation, RBI policy, FII returns, and the competitive position of exporters.  
**Overall Classification:** Tick Level to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| USD/INR Rate | US Dollar vs Indian Rupee exchange rate | Intraday | Market, IT, Pharma, OMC | RBI/Exchange | High | Y | Y | Y |
| Dollar Index (DXY) | Measure of USD strength vs basket of major currencies | Intraday | Market, EM | USDX | High | Y | Y | Y |
| FII Currency Hedging Flows | FII forward/options hedging activity on INR | Daily | FX, Market | RBI | Medium | Y | Y | N |
| RBI FX Intervention | Central bank's market operations to stabilize INR | Event | INR, Market | RBI | High | Y | N | Y |
| India FX Reserves | Total foreign exchange reserves held by RBI | Weekly | Market, INR | RBI | High | Y | N | N |
| Currency Volatility (INR) | Implied and realized volatility of INR | Daily | FX, Options | Derived | High | Y | Y | Y |
| EM Currency Basket | Performance of peer EM currencies vs USD | Daily | Market | Derived | Medium | Y | Y | Y |

**Key Relationships:** INR weakening → IT and pharma (USD earners) benefit. INR weakening → OMCs suffer (USD oil imports). Strong DXY → FII selling pressure on EM including India. INR volatility → elevated if RBI not actively defending → risk signal.

---

### DOMAIN 17 — Commodity Information

**Definition:** Price, supply, demand, and structural dynamics of physical commodities.  
**Why It Matters:** Commodities are both input costs and revenue drivers for large sections of the equity universe. Commodity price trends drive significant sector rotations.  
**Overall Classification:** Intraday to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Crude Oil (Brent & WTI) | Global crude oil benchmark prices | Intraday | OMC, Aviation, Chemicals, Paint | ICE/NYMEX | High | Y | Y | Y |
| Natural Gas | Global and Indian natural gas prices | Daily | Power, Fertilizer | MCX/ICE | High | Y | Y | Y |
| Gold | International and Indian gold prices | Intraday | Jewellery, Safe Haven | MCX/COMEX | High | Y | Y | Y |
| Silver | Silver commodity price | Daily | Industrial, Jewellery | MCX | Medium | Y | Y | N |
| Base Metals (Copper, Zinc, Aluminium) | Industrial metal prices | Daily | Metals, Manufacturing | LME/MCX | High | Y | Y | Y |
| Steel (HRC, CRC prices) | Hot/cold rolled coil prices — domestic and global | Daily | Steel, Auto, Capital Goods | Derived | High | Y | Y | Y |
| Agricultural Commodities | Sugar, cotton, soybean, wheat prices | Daily | FMCG, Agri | NCDEX/MCX | Medium | Y | Y | N |
| Coal | Thermal and coking coal prices | Daily | Power, Steel | Imported | High | Y | Y | Y |
| Fertilizer Prices | Urea, DAP prices — government subsidy implications | Slow/Event | Fertilizers, Agri | Global | High | Y | Y | Y |
| OPEC+ Production Decisions | Cartel supply decisions affecting global oil balance | Event | Crude, OMC | OPEC | High | Y | Y | Y |

**Key Relationships:** Crude oil rise → OMC margin squeeze → government subsidy pressure. Copper price → leading indicator of global industrial activity. Steel price rise → capital goods, construction input cost pressure. Coal price → power generation costs, steel production costs.

---

### DOMAIN 18 — Fixed Income / Interest Rate Information

**Definition:** Government and corporate bond yields, credit spreads, and the broader fixed income market condition.  
**Why It Matters:** Bond markets price the risk-free rate and credit risk. They provide the discount rate for all equity valuation and signal the credit health of the economy.  
**Overall Classification:** Intraday to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| 10-Year G-Sec Yield | India benchmark government bond yield | Intraday | All (discount rate) | RBI/NSE | High | Y | Y | Y |
| Yield Curve (India) | Spread between short and long-term G-Sec yields | Daily | Market, Banking | Derived | High | Y | Y | Y |
| Corporate Bond Spreads | Premium of corporate bonds over G-Sec at each rating | Daily | NBFC, Corporate | SEBI/CCIL | High | Y | Y | Y |
| US 10-Year Treasury Yield | Global risk-free rate reference — affects FII allocation | Intraday | Market, FX, FII | US Treasury | High | Y | Y | Y |
| Commercial Paper Rates | Short-term borrowing rates for corporates | Daily | NBFC, Corporate | FIMMDA | High | Y | Y | Y |
| Bond Market FII Activity | Foreign buying/selling of Indian government and corporate bonds | Daily | Market, INR | SEBI/NSDL | High | Y | Y | Y |
| G-Sec Auction Results | Demand and yield at government bond auctions | Event | Bonds | RBI | Medium | Y | N | N |

**Key Relationships:** G-Sec yield rise → equity PE compression, especially growth stocks. Corporate spread widening → credit stress in NBFC/corporate sector. US 10Y yield rise → FII debt outflows from India → INR pressure.

---

## SECTION III — META-DOMAIN C: SECTOR, INDUSTRY & COMPETITIVE INFORMATION

*The layer where macro meets company — where economy-wide forces translate into specific sector dynamics.*

---

### DOMAIN 19 — Sector Information

**Definition:** Information about the collective behavior, trends, and relative position of a defined group of companies sharing a common business theme.  
**Why It Matters:** Sector trends explain 30-40% of individual stock performance. Identifying which sectors are in favor and why is a primary intelligence function.  
**Overall Classification:** Daily, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Sector Relative Strength | Sector performance vs Nifty 50 over rolling periods | Daily | Sector ETFs, Indices | Derived | High | Y | Y | Y |
| Sector Rotation Signal | Which sectors are gaining or losing institutional allocation | Daily | Sectors | Derived | High | Y | Y | N |
| Sector Breadth | Advance-decline within each sector independently | Daily | Sectors | Derived | High | Y | Y | Y |
| Sector PE/PB vs History | Current valuation of sector vs own historical average | Daily | Sectors | Derived | High | Y | Y | Y |
| Sector Earnings Revision Trend | Direction of consensus earnings upgrades/downgrades | Event/Monthly | Sectors | Derived | High | Y | Y | Y |
| Sector FII Ownership Change | Change in FII's aggregate holding in a sector | Quarterly | Sectors | Exchange | High | Y | Y | N |
| Sector Correlation to Market | Beta of sector to Nifty 50 in current regime | Daily | Sectors | Derived | High | Y | N | Y |
| Sector Leadership Concentration | Whether sector gains are led by few or many stocks | Daily | Sectors | Derived | Medium | Y | Y | N |

**Key Relationships:** Sector rotation → identifies institutional capital flows. Sector breadth → confirms or questions sector move quality. Sector PE vs history → contextualizes whether opportunity is early or late cycle.

---

### DOMAIN 20 — Industry Information

**Definition:** Dynamics specific to a sub-industry: competitive structure, pricing power, regulatory environment, and cycle position.  
**Why It Matters:** Two companies in the same sector can face very different industry dynamics. Industry-level analysis reveals which companies are structurally advantaged.  
**Overall Classification:** Slow Changing to Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Industry Capacity Utilization | Current utilization vs peak capacity in the industry | Monthly/Quarterly | Industrial | Industry Associations | Medium | Y | Y | Y |
| Industry Pricing Power | Ability of industry players to raise prices without volume loss | Slow/Event | All Industries | Research | Medium | Y | Y | N |
| Competitive Structure (HHI) | Industry concentration — oligopoly vs fragmented competition | Slow | Companies | Research/Derived | Medium | Y | N | Y |
| Industry Demand Cycle | Current position in demand cycle (early, mid, late, downturn) | Slow/Monthly | Sectors, Companies | Research | Low-Medium | Y | Y | N |
| Industry Inventory Levels | Aggregate inventory position in the industry supply chain | Monthly | Manufacturing | Industry Data | Medium | Y | Y | N |
| Regulation-Driven Disruption | Regulatory changes creating winners and losers within an industry | Event | Companies | Regulators | High | Y | Y | Y |
| Technology Disruption Risk | New technologies threatening existing business models | Slow | Companies | Research | Low | Y | N | Y |
| Entry Barriers | Structural barriers preventing new competition | Slow | Companies | Research | Medium | Y | N | N |

**Key Relationships:** Industry capacity utilization > 85% → pricing power improves → margin expansion. New entrant in oligopoly → pricing pressure → margin compression. Technology disruption → stranded assets → long-term valuation risk.

---

### DOMAIN 21 — Supply Chain Information

**Definition:** The upstream and downstream relationships of a company or industry — raw material sources, logistics networks, and customer delivery chains.  
**Why It Matters:** Supply chain disruptions can devastate earnings unexpectedly. Supply chain advantages can create durable competitive moats.  
**Overall Classification:** Slow Changing to Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Key Input Costs | Primary raw material prices relevant to a company's COGS | Daily/Slow | Companies | MCX/Industry | High | Y | Y | Y |
| Supplier Concentration | Degree to which a company depends on few suppliers | Slow | Companies | Annual Reports | Medium | Y | N | Y |
| Logistics & Freight Costs | Transportation costs affecting input and output pricing | Daily/Monthly | Manufacturing, FMCG | Industry | Medium | Y | Y | Y |
| Inventory Build/Drawdown | Company and channel inventory health | Quarterly/Event | Companies | Research | Medium | Y | Y | Y |
| Supply Chain Disruption Events | Port congestion, natural disasters, trade blockages | Event | Sectors | News | Medium | N | N | Y |
| Import Dependency | Reliance on imported inputs — FX and tariff exposure | Slow | Companies | Annual Reports | High | Y | N | Y |
| Contract Manufacturing Exposure | Degree of outsourced vs captive production | Slow | Companies | Annual Reports | Medium | Y | N | N |

**Key Relationships:** High input cost concentration + commodity price spike → margin pressure → earnings downgrade. Supply chain disruption → near-term revenue shortfall → stock weakness. Inventory destocking → demand slowdown signal for upstream suppliers.

---

### DOMAIN 22 — Customer & Revenue Concentration Information

**Definition:** The distribution of a company's revenue across customers, geographies, and product lines.  
**Why It Matters:** Revenue concentration creates single-point risk. A company with 40% revenue from one customer has enormous hidden risk if that relationship weakens.  
**Overall Classification:** Slow Changing, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Top Customer Concentration | Revenue % from top 1/3/5 customers | Quarterly/Annual | Companies | Annual Reports | High | Y | N | Y |
| Geographic Revenue Mix | Domestic vs export revenue, and export geography mix | Quarterly | Companies | Financial Reports | High | Y | Y | Y |
| Product/Segment Mix | Revenue distribution across products or business segments | Quarterly | Companies | Segment Reporting | High | Y | Y | Y |
| Customer Health Assessment | Financial health of key customers | Slow/Event | Companies | Research | Low | Y | N | Y |
| Government as Customer | Reliance on government contracts and spending cycles | Slow | Companies | Annual Reports | High | Y | Y | Y |
| Market Share Trends | Company's share of total addressable market over time | Quarterly/Annual | Companies | Research | Medium | Y | Y | N |

**Key Relationships:** Export-heavy + INR weakness → revenue upside. Government customer + fiscal tightening → payment delays, order slowdown. Customer health deterioration → receivables risk → earnings quality decline.

---

### DOMAIN 23 — Competitive Intelligence Information

**Definition:** Information about the competitive landscape: rivals' moves, market share shifts, product launches, and pricing dynamics.  
**Why It Matters:** Competitive dynamics determine whether a company's advantages are durable or temporary. Competitive threats are often visible before they appear in financial statements.  
**Overall Classification:** Slow Changing to Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Competitor Actions | Product launches, pricing changes, capacity expansions by rivals | Event | Companies | News/Research | Low-Medium | Y | Y | Y |
| Market Share Movement | Quarterly/annual change in market share position | Quarterly | Companies | Research/Industry | Medium | Y | Y | N |
| Competitor Financial Health | Rival's revenue growth, margins, and debt situation | Quarterly | Companies | Public Reports | Medium | Y | Y | N |
| Price War Detection | Signs of irrational pricing behavior in an industry | Event/Slow | Industries | Research | Low | Y | N | Y |
| Patent / IP Disputes | Legal challenges to competitive advantages | Event | Pharma, Tech | Court Filings | Medium | Y | N | Y |
| New Market Entrant | Foreign or domestic player entering an established market | Event | Industries | News | Medium | Y | Y | Y |
| Consolidation Activity | Industry M&A reducing competitive fragmentation | Event | Industries | News | Medium | Y | Y | N |

---

## SECTION IV — META-DOMAIN D: COMPANY INFORMATION

*The deepest layer of intelligence — understanding each company as a living, evolving entity.*

---

### DOMAIN 24 — Company Fundamental Information

**Definition:** The core financial and operational facts that describe a company's business quality, growth trajectory, and competitive position.  
**Why It Matters:** Fundamentals are the anchor of long-term value. Price converges toward fundamental value — eventually. Understanding fundamentals allows conviction in situations where price has temporarily diverged.  
**Overall Classification:** Slow Changing, Event Driven (quarterly results)

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Revenue Growth | Year-on-year and quarter-on-quarter revenue growth rate | Quarterly | Companies | Financial Reports | High | Y | Y | N |
| EBITDA Margin | Earnings before interest, tax, depreciation as % of revenue | Quarterly | Companies | Financial Reports | High | Y | Y | N |
| PAT Margin | Net profit as percentage of revenue | Quarterly | Companies | Financial Reports | High | Y | Y | N |
| Return on Equity (ROE) | Net profit / shareholder equity — capital efficiency measure | Quarterly/Annual | Companies | Derived | High | Y | Y | N |
| Return on Capital Employed (ROCE) | EBIT / total capital employed — operational efficiency | Annual | Companies | Derived | High | Y | Y | N |
| Free Cash Flow (FCF) | Operating cash flow minus capital expenditure | Quarterly | Companies | Financial Reports | High | Y | Y | N |
| FCF Yield | Free cash flow as % of market capitalization | Daily/Quarterly | Companies | Derived | High | Y | Y | N |
| Earnings Quality Score | Consistency of cash flow conversion from reported earnings | Quarterly | Companies | Derived | Medium | Y | Y | Y |
| Revenue Visibility | Proportion of future revenue that is contracted or recurring | Quarterly/Annual | Companies | Research | Medium | Y | Y | N |
| Business Model Durability | Assessment of whether the competitive advantage is structural | Slow | Companies | Research/Learned | Low | Y | N | N |

---

### DOMAIN 25 — Financial Statement Information

**Definition:** The complete set of audited financial disclosures required of listed companies.  
**Why It Matters:** Financial statements are the authoritative record of a company's economic activity. They contain both the headline metrics and — in the notes — the information that most market participants miss.  
**Overall Classification:** Event Driven (quarterly), Slow Changing

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Profit & Loss Statement | Revenue, costs, EBITDA, depreciation, interest, PAT | Quarterly | Companies | Exchange Filing | High | Y | Y | N |
| Balance Sheet | Assets, liabilities, equity — snapshot of financial position | Quarterly | Companies | Exchange Filing | High | Y | Y | Y |
| Cash Flow Statement | Operating, investing, financing cash flows | Quarterly | Companies | Exchange Filing | High | Y | Y | Y |
| Notes to Accounts | Off-balance-sheet items, contingencies, policy changes, related party | Quarterly | Companies | Exchange Filing | High | Y | N | Y |
| Segment Reporting | Revenue and profit by business segment | Quarterly | Companies | Exchange Filing | High | Y | Y | N |
| Auditor's Report | Audit opinion, qualifications, emphasis of matter | Annual | Companies | Exchange Filing | High | Y | N | Y |
| Auditor Change | Change in statutory auditor | Event | Companies | Exchange | High | N | N | Y |
| Restatement | Prior period financial correction | Event | Companies | Exchange | High | N | N | Y |
| Working Capital Changes | Changes in receivables, payables, inventory | Quarterly | Companies | Derived | High | Y | Y | Y |

**Key Relationships:** Cash flow vs reported earnings divergence → earnings quality concern. Notes: contingent liabilities → hidden balance sheet risk. Auditor qualification → governance red flag.

---

### DOMAIN 26 — Valuation Information

**Definition:** Measures of how the market is pricing a company relative to its earnings, assets, cash flows, and comparable peers.  
**Why It Matters:** Valuation contextualizes whether a price move represents opportunity or risk. High-quality businesses at appropriate valuations are preferred to any business at excessive valuations.  
**Overall Classification:** Daily (prices change), Slow Changing (fundamentals change)

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Price / Earnings (PE) | Market price divided by earnings per share | Daily | Companies | Derived | High | Y | Y | N |
| PE vs Own History | Current PE relative to company's historical PE range | Daily | Companies | Derived | High | Y | Y | Y |
| PEG Ratio | PE divided by earnings growth rate | Daily | Companies | Derived | Medium | Y | Y | N |
| Price / Book (PB) | Market price vs book value of equity per share | Daily | Companies | Derived | High | Y | Y | N |
| EV / EBITDA | Enterprise value vs operating earnings | Daily | Companies | Derived | High | Y | Y | N |
| EV / Sales | Enterprise value vs revenue — for high-growth or low-margin companies | Daily | Companies | Derived | Medium | Y | Y | N |
| Dividend Yield | Annual dividend per share / market price | Daily | Companies | Derived | High | Y | Y | N |
| Sector Relative PE | Company PE vs median sector PE | Daily | Companies | Derived | High | Y | Y | N |
| DCF Intrinsic Value | Discounted cash flow-based fair value estimate | Quarterly | Companies | Research/Derived | Low | Y | Y | N |
| Earnings Yield vs G-Sec | Company earnings yield vs 10Y G-Sec — equity risk premium | Daily | Companies | Derived | High | Y | Y | Y |

---

### DOMAIN 27 — Earnings Information

**Definition:** Everything related to a company's reported earnings and the market's expectations and reactions around them.  
**Why It Matters:** Earnings are the most important single event in a company's quarterly cycle. Beats and misses, guidance changes, and consensus revisions drive significant price movements.  
**Overall Classification:** Event Driven, Daily (estimates change)

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Earnings Date | Scheduled date for quarterly/annual results announcement | Event | Companies | Exchange | High | Y | N | N |
| Consensus EPS Estimate | Aggregate analyst forecast for earnings per share | Daily | Companies | Bloomberg/Research | Medium | Y | Y | N |
| EPS Beat / Miss | Reported EPS vs consensus — the surprise | Event | Companies | Exchange/Research | High | Y | Y | Y |
| Revenue Beat / Miss | Reported revenue vs consensus | Event | Companies | Exchange/Research | High | Y | Y | Y |
| Management Guidance | Forward-looking revenue and margin guidance from management | Event | Companies | Exchange/Concall | High | Y | Y | Y |
| Earnings Revision Momentum | Direction of analyst consensus changes over rolling period | Daily/Event | Companies | Research | High | Y | Y | N |
| Conference Call Tone | Management language, confidence, candor on earnings calls | Event | Companies | Derived/Research | Medium | Y | Y | Y |
| Pre-announcement / Warning | Company-issued guidance change ahead of formal results | Event | Companies | Exchange | High | Y | Y | Y |
| Earnings Seasonality | Company's historical earnings performance by quarter | Historical | Companies | Derived | Medium | Y | Y | N |

---

### DOMAIN 28 — Corporate Action Information

**Definition:** Specific announced events that alter the capital structure, ownership, or financial terms of a security.  
**Why It Matters:** Corporate actions have mechanical price implications (splits, rights) and signal management's views on capital allocation (buybacks, dividends).  
**Overall Classification:** Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Dividend Announcement | Cash dividend declared — amount, record date, ex-date | Event | Companies | Exchange | High | Y | Y | N |
| Stock Split | Increase in share count with proportional price reduction | Event | Companies | Exchange | High | N | N | N |
| Bonus Issue | Free share issuance to existing shareholders | Event | Companies | Exchange | Medium | Y | Y | N |
| Rights Issue | Capital raising through discounted shares to existing holders | Event | Companies | Exchange | High | Y | Y | Y |
| Buyback | Company purchasing own shares from the market | Event | Companies | Exchange | High | Y | Y | N |
| Merger / Acquisition | Company combining with or acquiring another entity | Event | Companies | Exchange | High | Y | Y | Y |
| Demerger / Spin-off | Separation of a business unit into independent company | Event | Companies | Exchange | High | Y | Y | N |
| Open Offer (Takeover) | Public offer to acquire controlling stake | Event | Companies | SEBI | High | Y | Y | N |
| Delisting | Company's intention to remove shares from exchange | Event | Companies | Exchange | High | Y | N | Y |
| Block Deals | Large pre-arranged transactions above minimum threshold | Event | Companies | Exchange | High | Y | Y | N |

---

### DOMAIN 29 — Corporate Governance Information

**Definition:** The quality of a company's systems for accountability, transparency, and protection of minority shareholder interests.  
**Why It Matters:** Governance is the difference between financial statements that can be trusted and those that cannot. Poor governance is an asymmetric risk — it compounds silently until it explodes.  
**Overall Classification:** Slow Changing, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Board Composition | Independence, expertise, tenure, and diversity of board members | Slow/Annual | Companies | Exchange | High | Y | N | Y |
| Related Party Transactions | Transactions between company and promoter-related entities | Quarterly | Companies | Exchange | High | Y | N | Y |
| Promoter Shareholding Trend | Change in promoter ownership over time | Quarterly | Companies | Exchange | High | Y | Y | Y |
| Promoter Pledge Level | % of promoter holding pledged — financial stress indicator | Quarterly | Companies | Exchange | High | Y | Y | Y |
| Audit Committee Independence | Quality and independence of audit oversight | Annual | Companies | Annual Report | Medium | Y | N | Y |
| Disclosure Quality | Timeliness and completeness of regulatory filings | Ongoing | Companies | Exchange | High | Y | N | Y |
| Legal Cases & Contingencies | Material litigation risks disclosed in notes | Annual | Companies | Annual Report | Medium | Y | N | Y |
| AGM Voting Outcomes | Results of shareholder votes on key resolutions | Annual/Event | Companies | Exchange | Medium | Y | N | Y |

---

### DOMAIN 30 — Management Information

**Definition:** Information about the people who run the company — their quality, decisions, incentives, and track record.  
**Why It Matters:** Management quality is the most durable competitive advantage and the hardest to replicate. Great management compounds capital over decades. Poor management destroys it.  
**Overall Classification:** Slow Changing, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| CEO/CFO Track Record | Historical performance under current leadership team | Slow | Companies | Research | Low | Y | N | N |
| Management Change | CEO, CFO, or other key executive departure or appointment | Event | Companies | Exchange | High | Y | Y | Y |
| Management Compensation | Total compensation vs company performance alignment | Annual | Companies | Annual Report | Low | Y | N | Y |
| Capital Allocation History | How management has deployed free cash flow historically | Annual | Companies | Derived | High | Y | N | N |
| Insider Buying / Selling | Management's own purchases or sales of company shares | Event | Companies | SEBI | High | Y | Y | N |
| Promoter Commitment Signals | Announcements, investments, or statements by founding family | Event/Slow | Companies | Exchange/News | Medium | Y | Y | N |
| Management Guidance Accuracy | Historical accuracy of management's own forecasts | Derived | Companies | Derived/Learned | High | Y | N | N |

---

### DOMAIN 31 — Capital Structure Information

**Definition:** How a company funds itself — the mix of debt and equity, the terms of borrowing, and the sustainability of the debt burden.  
**Why It Matters:** Overleveraged companies are fragile. Their earnings power is consumed by interest costs, their equity becomes an option, and they are vulnerable to credit market disruptions.  
**Overall Classification:** Slow Changing, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Net Debt / EBITDA | Debt coverage ratio — leverage measure | Quarterly | Companies | Derived | High | Y | Y | Y |
| Interest Coverage Ratio | EBIT / interest expense — ability to service debt | Quarterly | Companies | Derived | High | Y | Y | Y |
| Debt Maturity Profile | When existing debt needs to be refinanced | Annual | Companies | Annual Report | High | Y | N | Y |
| Credit Rating (Corporate) | Rating agency assessment of debt repayment ability | Event | Companies | CRISIL/ICRA/Care | High | Y | Y | Y |
| Debt Covenants | Conditions attached to borrowings that may trigger default | Annual | Companies | Annual Report | High | Y | N | Y |
| Refinancing Risk | Whether upcoming debt maturities can be rolled at acceptable rates | Slow/Event | Companies | Derived | High | Y | N | Y |
| Capital Expenditure Plans | Announced or indicated future capital investment | Event/Quarterly | Companies | Exchange/Research | Medium | Y | Y | N |
| Working Capital Cycle | Receivable, payable, inventory days — cash conversion efficiency | Quarterly | Companies | Derived | High | Y | Y | Y |

---

### DOMAIN 32 — ESG Information

**Definition:** Environmental, Social, and Governance factors that affect a company's risk profile, stakeholder relationships, and long-term sustainability.  
**Why It Matters:** ESG issues represent risks and opportunities invisible in short-term financial statements. Regulatory pressure, institutional mandates, and consumer behavior changes make ESG increasingly material.  
**Overall Classification:** Slow Changing, Annual, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Carbon Footprint & Emissions | Company's greenhouse gas emissions and reduction targets | Annual | Industrial, Energy | Company Reports | Low | Y | N | Y |
| Environmental Compliance | Adherence to pollution norms, environmental approvals | Event/Slow | Industrial | Regulators | Medium | Y | N | Y |
| ESG Score (Third Party) | MSCI, Sustainalytics, or domestic ESG rating | Annual | Companies | ESG Agencies | Low | Y | N | N |
| Labor Practices | Employee safety record, litigation, union relations | Slow/Event | Companies | Research/News | Low | Y | N | Y |
| Governance Score | Composite governance quality score | Slow/Annual | Companies | Derived | Medium | Y | N | Y |
| FII ESG Mandate Compliance | Whether company meets ESG criteria for institutional mandates | Slow | Companies | Research | Low | Y | N | N |
| Stranded Asset Risk | Regulatory or transition risk to existing asset values | Slow | Energy, Industrial | Research | Low | Y | N | Y |

---

## SECTION V — META-DOMAIN E: MARKET PARTICIPANT & FLOW INFORMATION

*Who is doing what, and what does that signal about future price direction?*

---

### DOMAIN 33 — Options Information

**Definition:** Data derived from the listed options market for equities and indices.  
**Why It Matters:** Options markets are where sophisticated participants express their views with defined risk. Options data reveals expected ranges, fear levels, positioning, and potential price magnets.  
**Overall Classification:** Intraday to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Open Interest (OI) by Strike | Accumulation of contracts at each strike price | Daily | Equities, Indices | Exchange | High | Y | Y | N |
| Put-Call Ratio (PCR) | Total put OI / total call OI — sentiment and hedging measure | Daily | Indices, Equities | Derived | High | Y | Y | Y |
| Max Pain Level | Strike price where maximum option value expires worthless | Daily | Equities, Indices | Derived | Medium | Y | Y | N |
| OI-Weighted Average Strike | Average strike weighted by open interest — range expectation | Daily | Indices | Derived | Medium | Y | Y | N |
| Options Buildup Analysis | Whether OI additions are call/put long/short buildup | Daily | Equities | Derived | High | Y | Y | N |
| IV Percentile / IVR | Current implied volatility relative to historical range | Daily | Equities, Indices | Derived | High | Y | Y | Y |
| IV Surface / Skew | Visualization of IV across strikes and expiries | Daily | Indices | Derived | High | Y | Y | Y |
| Gamma Exposure (GEX) | Net gamma of market makers — affects price stability | Daily | Indices | Derived | Medium | Y | N | Y |
| Options Unusual Activity | Large unusual options purchases that may signal information | Intraday | Equities | Derived | Low | Y | Y | N |

---

### DOMAIN 34 — Futures & Derivatives Information

**Definition:** Data from equity and index futures markets, including positioning, premium/discount, and rollover patterns.  
**Why It Matters:** Futures markets reflect directional positioning of leveraged participants. Basis and rollover data reveal conviction and hedging demand.  
**Overall Classification:** Intraday to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Futures Open Interest | Total outstanding contracts — measures market commitment | Daily | Equities, Indices | Exchange | High | Y | Y | Y |
| Futures Basis / Premium | Difference between futures and spot price | Intraday | Equities, Indices | Derived | High | Y | Y | N |
| Rollover Data | % of OI rolled from near to next month as expiry approaches | Daily | Equities, Indices | Derived | High | Y | Y | N |
| Cost of Carry | Annualized rate implied by futures basis | Daily | Equities | Derived | High | Y | Y | N |
| Long / Short Buildup | Whether OI + price change indicates new long or short | Daily | Equities | Derived | High | Y | Y | Y |
| Long / Short Unwinding | Position liquidation signals | Daily | Equities | Derived | High | Y | Y | Y |
| Futures Volume vs Spot | Ratio of derivative to cash market activity | Daily | Equities | Derived | Medium | Y | N | N |
| F&O Expiry Date | Upcoming monthly/weekly expiry — affects price behavior | Event/Static | Equities, Indices | Exchange | High | Y | Y | N |

---

### DOMAIN 35 — Institutional Activity Information

**Definition:** The investment behavior of large, organized market participants — FIIs, mutual funds, insurance companies, and other institutions.  
**Why It Matters:** Institutional flows are large enough to move markets. Institutional buying is the primary driver of sustained uptrends. Institutional selling creates sustained downtrends. Anticipating institutional behavior is a significant intelligence advantage.  
**Overall Classification:** Daily, Quarterly

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| FII Equity Net Flows | Daily net purchases/sales by Foreign Institutional Investors | Daily | Market | SEBI/NSE | High | Y | Y | Y |
| DII Equity Net Flows | Daily net purchases/sales by Domestic Institutional Investors | Daily | Market | SEBI/NSE | High | Y | Y | Y |
| Mutual Fund Holdings (Quarterly) | MF portfolio holdings by stock, reported quarterly | Quarterly | Companies | SEBI/AMFI | High | Y | Y | N |
| FII Holdings Change (Quarterly) | Change in FII ownership by company | Quarterly | Companies | Exchange | High | Y | Y | N |
| Block Deals | Large pre-market transactions — often institutional | Event | Companies | Exchange | High | Y | Y | N |
| Bulk Deals | Large same-day transactions disclosed end-of-day | Event | Companies | Exchange | High | Y | Y | N |
| Insurance & Pension Flows | Systematic buying from LIC, NPS, EPFO — structural demand | Monthly | Market | IRDAI/PFRDA | Medium | Y | N | N |
| MF Category Inflows | Flows into large-cap, mid-cap, small-cap fund categories | Monthly | Market | AMFI | High | Y | Y | Y |

---

### DOMAIN 36 — Retail Behavior Information

**Definition:** The aggregate investment and trading behavior of individual, non-institutional investors.  
**Why It Matters:** Retail behavior is a contrarian sentiment indicator at extremes. Peak retail enthusiasm often precedes market tops; peak retail pessimism often precedes recoveries.  
**Overall Classification:** Daily to Monthly

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Demat Account Growth | Monthly additions to demat accounts — retail participation proxy | Monthly | Market | CDSL/NSDL | Medium | Y | Y | N |
| SIP Flows | Monthly SIP inflow data — systematic retail equity investment | Monthly | Market, MF | AMFI | High | Y | Y | N |
| Retail Derivatives Activity | Retail participation in F&O as % of total volume | Daily | Derivatives | Exchange | Medium | Y | N | Y |
| Call-to-Action Ratio | Ratio of individual investors buying calls vs puts | Daily | Derivatives | Exchange | Medium | Y | N | Y |
| Social Media Trading Buzz | Volume of retail discussion around specific stocks | Daily | Companies | Social Data | Low | Y | N | Y |
| IPO Subscription (Retail) | Retail tranche subscription in IPOs — sentiment indicator | Event | Market | Exchange | Medium | Y | N | N |
| Retail Margin Funding | Levels of retail-funded margin positions | Daily | Market | Exchange/SEBI | Medium | Y | N | Y |

---

### DOMAIN 37 — Fund Flow Information

**Definition:** Net capital movements into and out of different investment vehicles, asset classes, and geographies.  
**Why It Matters:** Fund flows are the actual plumbing of market prices. Understanding where institutional capital is flowing — and where it is leaving — provides directional intelligence.  
**Overall Classification:** Daily to Monthly

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| FII Debt Flows | Foreign buying/selling in Indian government and corporate bonds | Daily | Bonds, INR | SEBI/NSDL | High | Y | Y | Y |
| Global EM Fund Flows | Capital allocation to all emerging market equity funds | Weekly | Market | EPFR Global | High | Y | Y | Y |
| ETF Flows (Index-Linked) | Flows into NIFTY, Sensex, and sector ETFs | Daily | Market, Sectors | AMC/Exchange | High | Y | Y | N |
| FII Futures Positioning | Net long/short position of FIIs in index futures | Daily | Market | Exchange | High | Y | Y | Y |
| DII Segment-Wise Flows | Insurance vs MF vs NPS contribution to DII total | Monthly | Market | Derived | Medium | Y | N | N |
| MF New Fund Offer (NFO) | Capital raised in new fund launches — appetite indicator | Event | Market | AMFI | Low | Y | N | N |

---

### DOMAIN 38 — Insider & Promoter Activity Information

**Definition:** Transactions by company insiders, promoters, and those with potentially material non-public information.  
**Why It Matters:** Insiders know their businesses better than anyone. Meaningful insider buying is among the most reliable positive signals available. Promoter selling at inflated valuations is an important warning.  
**Overall Classification:** Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Promoter Buying/Selling | Open market transactions by promoter group | Event | Companies | SEBI/Exchange | High | Y | Y | N |
| Director/KMP Transactions | Buying or selling by key management personnel | Event | Companies | SEBI/Exchange | High | Y | Y | N |
| Promoter Pledge Creation | New pledge of promoter shares as loan collateral | Event | Companies | Exchange | High | Y | N | Y |
| Promoter Pledge Release | Removal of pledge — financial improvement signal | Event | Companies | Exchange | High | Y | Y | N |
| ESOP Exercise | Management exercising stock options — may signal valuation view | Event | Companies | Exchange | Medium | Y | N | N |
| Creeping Acquisition | Gradual promoter increase toward open offer threshold | Slow/Event | Companies | SEBI | High | Y | Y | N |

---

### DOMAIN 39 — Index Information

**Definition:** The composition, weights, and mechanical behavior of market indices.  
**Why It Matters:** Index inclusion/exclusion forces large, predictable buying and selling from passive funds. Understanding index mechanics converts announcements into anticipatable price events.  
**Overall Classification:** Slow Changing, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Index Composition | Current constituents of NIFTY 50, 100, 200, 500 | Slow Changing | Companies | NSE | High | Y | Y | N |
| Index Weights | Market-cap weight of each constituent | Daily | Companies | NSE | High | Y | Y | N |
| Index Rebalancing Schedule | Quarterly review schedule for index changes | Event | Companies | NSE | High | Y | Y | N |
| Inclusion/Exclusion Announcement | Company added to or removed from index | Event | Companies | NSE | High | Y | Y | N |
| Passive AUM Tracking | Total AUM in passive funds tracking each index | Monthly | Market | AMFI | Medium | Y | N | N |
| MSCI Rebalancing | Changes to MSCI indices affecting FII allocation | Event | Companies | MSCI | High | Y | Y | Y |

---

## SECTION VI — META-DOMAIN F: INTELLIGENCE & ALTERNATIVE DATA

*Information that requires interpretation, aggregation, or unconventional collection.*

---

### DOMAIN 40 — Sentiment Information

**Definition:** Measures of the collective mood, fear, greed, and directional bias of market participants.  
**Why It Matters:** Sentiment is a contrarian tool. Extreme readings — both bullish and bearish — are historically associated with market turning points.  
**Overall Classification:** Daily to Intraday, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Fear & Greed Index | Composite indicator of market emotion | Daily | Market | Derived | Medium | Y | Y | Y |
| Investor Survey Data | Surveys measuring bullish vs bearish investor positioning | Weekly | Market | AAII, IIFL etc. | Low | Y | Y | N |
| News Sentiment Score | NLP-derived sentiment from financial news | Daily/Intraday | Companies, Market | Derived | Medium | Y | Y | N |
| Social Media Sentiment | Aggregate sentiment from financial social media | Intraday | Companies | Derived | Low | Y | N | Y |
| VIX as Sentiment | India VIX level as direct fear gauge | Daily | Market | NSE | High | Y | Y | Y |
| Put-Call Ratio as Sentiment | Options market's directional bias | Daily | Market | Derived | High | Y | Y | Y |
| Analyst Consensus Sentiment | Aggregate buy/sell/hold rating distribution | Daily | Companies | Bloomberg/Research | Medium | Y | Y | N |
| Market Expectation Index | Deviation of market expectations from historical norms | Daily | Market | Derived | Medium | Y | Y | N |

---

### DOMAIN 41 — News & Media Information

**Definition:** Real-time and historical published information from news services, company communications, and media.  
**Why It Matters:** News creates price discontinuities. Most price gaps are news-driven. Distinguishing between news that changes fundamentals and noise that creates temporary price disruption is a critical intelligence capability.  
**Overall Classification:** Event Driven, Intraday

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Corporate Announcements | Exchange-filed disclosures by listed companies | Event | Companies | Exchange | High | Y | Y | Y |
| Breaking Financial News | Market-moving news from financial media | Intraday/Event | Companies, Market | News Wires | Variable | N | N | Y |
| Management Interviews | CEO/CFO statements in media | Event | Companies | Media | Low | Y | Y | N |
| Government Policy Announcements | Ministerial statements, policy notifications | Event | Sectors, Market | Government | High | Y | Y | Y |
| RBI / SEBI Communications | Regulatory circulars, guidelines, and speeches | Event | Market | RBI/SEBI | High | Y | Y | Y |
| Earnings Conference Calls | Management discussion on quarterly results | Event/Quarterly | Companies | Company | High | Y | Y | Y |
| Media Coverage Intensity | Volume of news coverage as a sentiment and attention proxy | Daily | Companies | Derived | Low | Y | N | N |
| Rumor vs Confirmed News | Classification of news by verification status | Event | Companies | Derived | Low | N | N | Y |

---

### DOMAIN 42 — Analyst & Research Information

**Definition:** Independent assessments and forecasts by sell-side analysts, independent researchers, and rating agencies.  
**Why It Matters:** Analyst consensus shapes institutional behavior. Revisions to consensus drive significant price movements. Analyst herding and lagging creates exploitable opportunities.  
**Overall Classification:** Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Rating (Buy/Sell/Hold) | Analyst recommendation category | Event | Companies | Brokerages | Medium | Y | Y | N |
| Target Price | Analyst's 12-month price target | Event | Companies | Brokerages | Low | Y | Y | N |
| Target Price vs Current | Upside/downside implied by analyst target | Daily | Companies | Derived | Low | Y | Y | N |
| Consensus Earnings Estimate | Median/mean EPS forecast across all analysts | Daily | Companies | Bloomberg/Research | Medium | Y | Y | N |
| Estimate Revision Trend | Direction of changes in consensus estimates | Daily | Companies | Derived | High | Y | Y | Y |
| Number of Analysts Covering | Coverage depth — thin coverage = more volatility on surprises | Slow | Companies | Research | Medium | Y | N | Y |
| Analyst Upgrade Cycle | Multiple analysts upgrading in same period | Event | Companies | Derived | High | Y | Y | N |

---

### DOMAIN 43 — Credit & Debt Quality Information

**Definition:** Assessments of the creditworthiness of companies, banks, and sovereigns.  
**Why It Matters:** Credit quality problems in the banking sector or large corporates create systemic risks that eventually affect equity prices broadly.  
**Overall Classification:** Event Driven, Slow Changing

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Credit Rating (Corporate) | CRISIL/ICRA/Care rating for debt instruments | Event | Companies | Rating Agencies | High | Y | Y | Y |
| Rating Outlook Change | Change in rating direction without immediate rating change | Event | Companies | Rating Agencies | High | Y | Y | Y |
| NPA Levels (Banking) | Non-performing assets as % of gross advances | Quarterly | Banks | Exchange | High | Y | Y | Y |
| GNPA / NNPA Trend | Direction of NPA over multiple quarters | Quarterly | Banks | Derived | High | Y | Y | Y |
| Slippage Ratio | Fresh NPAs added in a quarter | Quarterly | Banks | Exchange | High | Y | Y | Y |
| Credit Spread (Company Bonds) | Premium over G-Sec for company's bonds | Daily | Companies | FIMMDA/Derived | High | Y | Y | Y |
| Debt Stress Score | Composite of leverage, coverage, maturity, refinancing risk | Quarterly | Companies | Derived | High | Y | Y | Y |

---

### DOMAIN 44 — Alternative Data Information

**Definition:** Non-traditional data sources that provide early or independent insights into economic and company activity.  
**Why It Matters:** Traditional data is available to all. Alternative data can provide an edge in information timeliness. It is important to define these as future sources even if not currently collected.  
**Overall Classification:** Daily to Monthly, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Satellite Imagery | Parking lot density, factory throughput, crop estimates | Daily/Weekly | Retail, Mining, Agri | Satellite Providers | Low | Y | Y | N |
| Credit/Debit Card Transaction Data | Aggregated consumer spending patterns by category | Weekly | Consumer, FMCG | Fintech Aggregators | Medium | Y | Y | N |
| Mobile App Downloads | Fintech, e-commerce, travel app activity | Weekly | Technology, Consumer | App Stores | Medium | Y | Y | N |
| Web Traffic (Alexa/SimilarWeb) | Online traffic to company and competitor websites | Monthly | E-commerce, Fintech | Web Analytics | Low | Y | N | N |
| Job Postings | Hiring activity by company — leading revenue growth indicator | Weekly | Companies | Job Portals | Low | Y | Y | N |
| GST E-Way Bills | Daily inter-state goods movement proxy for economic activity | Daily | Economy, Logistics | GSTN | High | Y | Y | N |
| Power Consumption Data | Electricity demand as industrial activity proxy | Monthly | Economy, Industrials | CEA | Medium | Y | Y | N |
| Auto Registration Data | Monthly vehicle registrations — leading demand indicator | Monthly | Automobiles | Vahan/SIAM | High | Y | Y | N |

---

### DOMAIN 45 — Regulatory Filings Information

**Definition:** Mandatory disclosures filed by listed companies and market participants with exchanges and regulators.  
**Why It Matters:** Regulatory filings contain material information that must be disclosed. They are authoritative, timestamped, and legally binding.  
**Overall Classification:** Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| BSE/NSE Exchange Filings | Investor presentations, annual reports, concall transcripts | Event | Companies | Exchange | High | Y | Y | Y |
| Shareholding Pattern | Quarterly disclosure of promoter, FII, DII, retail % | Quarterly | Companies | Exchange | High | Y | Y | Y |
| SAST Disclosures | Substantial acquisition of shares and takeover disclosures | Event | Companies | SEBI | High | Y | Y | N |
| Insider Trading Disclosures | Mandatory declarations of insider transactions | Event | Companies | SEBI | High | Y | Y | N |
| Annual Report (Full) | Complete audited annual report with all disclosures | Annual | Companies | Exchange | High | Y | N | Y |
| DRHP / Prospectus | Detailed company description for IPO/FPO/NCD issuances | Event | Companies | SEBI | High | Y | Y | N |
| Penalty Orders | Regulatory penalties imposed on companies | Event | Companies | SEBI/Exchange | High | Y | N | Y |

---

## SECTION VII — META-DOMAIN G: SYSTEM INTELLIGENCE INFORMATION

*The internal knowledge layer — what the system has learned about itself and the world.*

---

### DOMAIN 46 — Historical Pattern Information

**Definition:** Documented recurring behavioral patterns in price, volume, sentiment, or other variables at specific times or under specific conditions.  
**Why It Matters:** History does not repeat exactly but it rhymes. Patterns that have occurred repeatedly under similar conditions carry predictive probability.  
**Overall Classification:** Derived, Learned

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Seasonality | Systematic performance patterns by month, quarter, or week | Derived | Market, Sectors | Derived/Learned | Medium | Y | Y | N |
| Earnings Season Behavior | Typical pre/post earnings price behavior by sector | Derived | Companies | Derived/Learned | Medium | Y | Y | N |
| Expiry Week Patterns | Price behavior tendencies in options expiry week | Derived | Indices | Derived/Learned | Low | Y | Y | N |
| Budget Day Patterns | Historical market behavior around Union Budget | Derived | Market, Sectors | Derived/Learned | Low | Y | Y | N |
| Post-Breakout Behavior | Historical follow-through rates after technical breakouts | Derived | Equities | Derived/Learned | Medium | Y | Y | N |
| Volatility Mean Reversion | Historical tendency for volatility spikes to revert | Derived | Market | Derived/Learned | High | Y | Y | N |
| Sector Rotation Cycles | Historical sequence of sector leadership changes in cycles | Derived | Sectors | Derived/Learned | Low | Y | Y | N |

---

### DOMAIN 47 — Relationship & Entity Graph Information

**Definition:** The network of connections between entities — corporate ownership, financial interdependencies, supply relationships, and competitive links.  
**Why It Matters:** The entity graph reveals hidden risks and opportunities. A promoter group controlling multiple companies creates cross-entity risks. Supply chain links create earnings contagion paths.  
**Overall Classification:** Slow Changing, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Corporate Group Structure | Parent-subsidiary-associate network of companies | Slow | Companies | Annual Reports | High | Y | N | Y |
| Common Promoter Groups | Multiple listed entities under same promoter group | Slow | Companies | Exchange | High | Y | N | Y |
| Supply Chain Graph | Upstream and downstream entity relationships | Slow | Companies | Derived/Research | Medium | Y | Y | Y |
| Customer-Supplier Links | Which companies are customers and which are suppliers | Slow | Companies | Research | Medium | Y | Y | N |
| Financial Contagion Paths | How stress in one entity can transmit to another | Derived | Companies | Derived | Medium | Y | N | Y |
| Competitive Relationship Map | Who competes directly vs indirectly with whom | Slow | Companies | Research | Medium | Y | Y | N |
| Index Membership Cross-Ownership | How entities share common shareholders (passive funds) | Slow | Companies | Derived | Low | Y | N | N |

---

### DOMAIN 48 — Risk Information

**Definition:** Quantified and characterized measures of the risk present in individual positions, the portfolio, and the broader market.  
**Why It Matters:** Risk information is the system's safety infrastructure. Without accurate risk measurement, conviction and decision quality are meaningless.  
**Overall Classification:** Daily, Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Position-Level VaR | Maximum expected loss for a single position at 95/99% confidence | Daily | Positions | Derived | Medium | Y | N | Y |
| Portfolio VaR | Maximum expected loss for the total portfolio | Daily | Portfolio | Derived | Medium | Y | N | Y |
| Drawdown | Peak-to-current loss in a position or portfolio | Daily | Positions, Portfolio | Derived | High | Y | Y | Y |
| Maximum Historical Drawdown | Worst historical drawdown for a strategy or entity | Historical | Companies, Strategies | Derived | High | Y | Y | Y |
| Correlation Risk | Degree to which portfolio positions move together | Daily | Portfolio | Derived | High | Y | Y | Y |
| Concentration Risk | Single-entity or sector concentration in portfolio | Daily | Portfolio | Derived | High | Y | N | Y |
| Liquidity Risk | Risk that a position cannot be exited at acceptable prices | Daily | Positions | Derived | High | Y | N | Y |
| Tail Risk | Probability of extreme loss events | Daily | Portfolio | Derived | Low | Y | N | Y |
| Stress Test Results | Portfolio behavior under defined adverse scenarios | Weekly | Portfolio | Derived | Medium | Y | N | Y |

---

### DOMAIN 49 — Portfolio Information

**Definition:** The complete current state of the system's investment positions, capital allocation, and performance attribution.  
**Why It Matters:** Portfolio information is the context within which every new decision is evaluated. A decision that is excellent in isolation may be inappropriate given current portfolio state.  
**Overall Classification:** Intraday to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Open Positions | Current holdings with entry price, current price, P&L | Intraday | Portfolio | Internal | High | Y | Y | Y |
| Capital Utilization | Percentage of available capital currently deployed | Daily | Portfolio | Internal | High | Y | Y | Y |
| Unrealized P&L | Current gain/loss on open positions | Intraday | Portfolio | Derived | High | N | Y | Y |
| Realized P&L | Closed trade outcomes for the period | Daily | Portfolio | Internal | High | Y | N | N |
| Portfolio Beta | Aggregate market sensitivity of current positions | Daily | Portfolio | Derived | High | Y | Y | Y |
| Sector Exposure | Portfolio allocation by sector | Daily | Portfolio | Derived | High | Y | Y | Y |
| Position Age | Duration each position has been held | Daily | Positions | Internal | High | Y | Y | N |
| Performance Attribution | Return decomposed by strategy, sector, position | Daily | Portfolio | Derived | High | Y | N | N |
| Capital Reserve | Undeployed capital available for new opportunities | Daily | Portfolio | Internal | High | Y | Y | N |

---

### DOMAIN 50 — Execution Information

**Definition:** The complete record of the system's trading activity, execution quality, and operational behavior.  
**Why It Matters:** Execution information is the most granular feedback on system behavior. It enables slippage analysis, timing quality assessment, and operational improvement.  
**Overall Classification:** Tick Level to Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Trade Journal | Complete record of every order — entry, exit, price, time, reason | Event | All | Internal | High | Y | N | N |
| Execution Slippage | Difference between decision price and actual fill price | Event | All | Derived | High | Y | N | N |
| Order Rejection Log | Broker-rejected orders and reasons | Event | All | Broker | High | N | N | Y |
| Entry Timing Quality | Whether entries were made at optimal intraday points | Daily | Positions | Derived/Learned | Medium | Y | N | N |
| Exit Timing Quality | Whether exits captured intended P&L efficiently | Daily | Positions | Derived/Learned | Medium | Y | N | N |
| Broker Fill Quality | Assessment of broker execution quality over time | Daily | All | Derived | Medium | Y | N | N |

---

### DOMAIN 51 — Calendar & Temporal Information

**Definition:** Time-based facts that affect market behavior, corporate events, and system scheduling.  
**Why It Matters:** Markets are not temporally uniform. Specific dates have systematic effects on prices, liquidity, and decision relevance.  
**Overall Classification:** Static to Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Market Holiday Calendar | Official NSE/BSE non-trading days | Static-Annual | All | Exchange | High | N | N | N |
| F&O Expiry Calendar | Monthly and weekly expiry dates for all F&O segments | Static-Annual | Derivatives | Exchange | High | Y | Y | N |
| Results Calendar | Scheduled earnings announcement dates | Event | Companies | Exchange | High | Y | Y | N |
| Dividend Ex-Date Calendar | Ex-dividend dates causing price adjustments | Event | Companies | Exchange | High | Y | Y | N |
| RBI MPC Meeting Dates | Scheduled monetary policy committee meeting dates | Static-Annual | Market | RBI | High | Y | Y | N |
| Budget Date | Union Budget announcement date | Annual | Market | Government | High | Y | Y | N |
| AGM Calendar | Annual general meeting dates for major companies | Annual | Companies | Exchange | Low | N | N | N |
| Index Rebalancing Date | Quarterly NSE index review effective dates | Event | Companies | NSE | High | Y | Y | N |

---

### DOMAIN 52 — Learned Knowledge

**Definition:** Patterns, models, and insights generated by the system itself through the analysis of its accumulated observations and outcomes.  
**Why It Matters:** Learned knowledge is the most proprietary form of intelligence the system possesses. It cannot be purchased from any data vendor.  
**Overall Classification:** Learned

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Entity Behavioral Model | The system's model of how a specific entity behaves under various conditions | Learned | Companies | Internal | Variable | Y | Y | N |
| Regime-Strategy Reliability Map | Which evidence patterns are reliable in which market regimes | Learned | Market | Internal | Variable | Y | Y | N |
| Relationship Strength Score | Validated strength of inter-entity relationships | Learned | Entity Pairs | Internal | Medium | Y | Y | N |
| Evidence Type Reliability | Historical predictive accuracy of each evidence type | Learned | System | Internal | High | Y | Y | N |
| Conviction Calibration | How well the system's conviction scores predict outcomes | Learned | Portfolio | Internal | High | Y | N | N |
| Pattern Base Rates | How often specific information patterns precede defined outcomes | Learned | Companies | Internal | Variable | Y | Y | N |
| Anomaly Library | Documented unusual behaviors and their typical resolutions | Learned | Companies | Internal | Variable | Y | N | Y |

---

### DOMAIN 53 — Derived & Computed Information

**Definition:** Information created by transforming, combining, or computing from raw source information. Has no independent source — quality is bounded by inputs.  
**Why It Matters:** Most intelligence is derived. Raw information becomes useful through computation. Derived information must always be traceable to its source.  
**Overall Classification:** Derived

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Technical Indicators | Moving averages, RSI, MACD, Bollinger Bands, ATR | Daily/Intraday | Equities | Derived | Medium | Y | Y | N |
| Fundamental Ratios | PE, PB, EV/EBITDA, ROE, ROCE, Debt/Equity | Quarterly/Daily | Companies | Derived | High | Y | Y | Y |
| Composite Scores | Multi-factor scoring models combining several inputs | Daily | Companies | Derived | Medium | Y | Y | N |
| Percentile Rankings | Entity's current metric ranked vs universe history | Daily | Companies | Derived | High | Y | Y | N |
| Signal Strength Measures | Quantified strength of a pattern or signal | Daily | Equities | Derived | Medium | Y | Y | N |
| Correlation Matrices | Pairwise correlation between entities or factors | Daily | Portfolio | Derived | High | Y | N | Y |
| Rolling Return Metrics | Returns over rolling windows of varying lengths | Daily | Equities | Derived | High | Y | Y | N |

---

### DOMAIN 54 — Predictive Information

**Definition:** Forward-looking estimates and probability assessments about future states of entities and markets.  
**Why It Matters:** All investment decisions are ultimately about the future. Predictive information must be clearly labeled as probabilistic and carry explicit uncertainty bounds.  
**Overall Classification:** Predictive

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Earnings Forecast | Forward earnings per share estimates | Daily | Companies | Research | Low | Y | Y | N |
| Price Target | Expected future price level with time horizon | Event | Companies | Research | Low | Y | Y | N |
| Scenario Analysis | Portfolio or entity behavior under defined macro scenarios | Weekly | Portfolio | Internal | Low | Y | Y | Y |
| Probability Estimate | System-derived probability of a directional outcome | Daily | Equities | Learned/Derived | Variable | Y | Y | Y |
| Macro Forecast | GDP, inflation, rate trajectory predictions | Quarterly | Economy | Research | Very Low | Y | N | N |
| Regime Transition Probability | Estimated probability of market regime change | Daily | Market | Learned/Derived | Low | Y | Y | Y |

---

### DOMAIN 55 — Reasoning Information

**Definition:** Structured arguments, hypotheses, and conviction assessments produced by the system's reasoning layer.  
**Why It Matters:** Reasoning information is the bridge between knowledge and decision. Preserving it enables learning from whether the reasoning was correct, not just whether the outcome was profitable.  
**Overall Classification:** Derived, Learned, Event Driven

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Active Hypothesis | Current directional hypothesis for an entity under consideration | Event | Companies | Internal | Variable | Y | Y | N |
| Evidence Inventory | Compiled list of supporting and contradicting evidence for a hypothesis | Event | Companies | Internal | High | N | Y | N |
| Conviction Score | Quantified confidence level for a directional hypothesis | Event | Companies | Internal | Variable | Y | Y | Y |
| Conflict Resolution Record | Documentation of how contradicting evidence was weighed | Event | Companies | Internal | Medium | Y | N | N |
| Falsification Conditions | Explicit conditions that would invalidate the current hypothesis | Event | Companies | Internal | High | Y | Y | Y |
| Reasoning Quality Score | Post-outcome assessment of reasoning quality | Learned | Portfolio | Internal | High | Y | N | N |

---

### DOMAIN 56 — Decision Information

**Definition:** The complete record of every investment decision the system has made, including rationale, parameters, and outcome.  
**Why It Matters:** Decision records are the raw material of learning. A system that does not preserve its decision rationale cannot improve its decision quality.  
**Overall Classification:** Event Driven, Learned

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Decision Record | Complete decision with entity, direction, rationale, conviction | Event | Companies | Internal | High | Y | N | N |
| Decision Parameters | Entry logic, stop-loss, target, position size, time horizon | Event | Positions | Internal | High | N | Y | Y |
| Decision Lifecycle State | Current state: pending/active/monitoring/closed | Daily | Positions | Internal | High | N | Y | N |
| Decision Outcome | Final result: profit/loss, win/loss, exit reason | Event | Closed Positions | Internal | High | Y | N | N |
| Prediction vs Reality Gap | Where the outcome deviated from the reasoning assumption | Event | Closed Positions | Derived | High | Y | N | N |
| Decision Revision History | Record of any modifications to an active decision | Event | Positions | Internal | High | Y | N | Y |

---

### DOMAIN 57 — Observation Records

**Definition:** The system's log of notable market observations that do not yet constitute knowledge but warrant monitoring.  
**Why It Matters:** Not every observation immediately leads to a hypothesis. Maintaining an observation record allows patterns to be recognized across time.  
**Overall Classification:** Event Driven, Daily

| Information Type | Definition | Temporal Class | Primary Entities | Source | Confidence | K | Rec | Ri |
|---|---|---|---|---|---|---|---|---|
| Anomaly Flag | Observation that deviates significantly from historical norms | Event | Companies | Internal | Variable | Y | N | Y |
| Behavioral Change Note | Documented change in entity behavior awaiting confirmation | Event | Companies | Internal | Low | Y | N | N |
| Watch List Entry | Entity flagged for increased monitoring | Event | Companies | Internal | N/A | N | N | N |
| Relationship Change Signal | Evidence that an established relationship is weakening | Event | Entity Pairs | Internal | Low | Y | N | Y |
| Regime Transition Signal | Early indicators of potential market regime change | Daily | Market | Internal | Low | Y | Y | Y |

---

## SECTION VIII — INTER-DOMAIN RELATIONSHIP MAP

The following chains represent the most important information flow pathways in the system.

```
MACRO ENVIRONMENT
├── Monetary Policy (Domain 10)
│   → Interest Rate Level
│   → Banking Sector (Domain 24) margins, NIM
│   → NBFC credit cost (Domain 31)
│   → All company discount rates (Domain 26 — Valuation)
│   → INR/USD (Domain 16) via rate differentials
│   → FII Debt Flows (Domain 37)
│
├── Crude Oil Price (Domain 17)
│   → OMC stocks (Domain 24) — input cost
│   → Aviation (Domain 24) — fuel cost
│   → Paints (Domain 21) — raw material (titanium dioxide, petrochemicals)
│   → Fertilizers (Domain 21) — natural gas input
│   → Inflation trajectory (Domain 9) — pass-through
│   → RBI policy (Domain 10) — inflation → rate response
│
├── USD/INR (Domain 16)
│   → IT sector (Domain 24) — USD revenue, INR cost = margin benefit when weak
│   → Pharma exporters (Domain 24) — same dynamic
│   → OMC (Domain 24) — USD crude payable, INR revenue = margin pressure when weak
│   → FII flows (Domain 35) — weak INR reduces INR-hedged returns
│
└── Global Risk Sentiment (Domain 14)
    → FII Equity Flows (Domain 35)
    → Market Breadth (Domain 4)
    → India VIX (Domain 7)
    → Sector Rotation (Domain 19)

COMPANY INFORMATION CHAINS
├── Earnings Beat (Domain 27)
│   → Price Behavior (Domain 2) — gap up
│   → Volume Spike (Domain 3)
│   → Analyst Revisions (Domain 42) — upward
│   → Institutional Buying (Domain 35)
│   → Valuation Reset (Domain 26)
│
├── Promoter Pledge Increase (Domain 38)
│   → Liquidity Risk (Domain 6)
│   → Governance Concern (Domain 29)
│   → Credit Rating Watch (Domain 43)
│   → Institutional Selling (Domain 35)
│   → Price Decline (Domain 2)
│
└── New Regulation in Sector (Domain 12)
    → Industry Dynamics Change (Domain 20)
    → Competitive Structure Shift (Domain 23)
    → Earnings Estimate Revision (Domain 42)
    → Valuation Rerating (Domain 26)

PARTICIPANT FLOW CHAINS
├── FII Selling + DII Buying (Domain 35)
│   → Market holds despite FII outflow
│   → DII absorption capacity (Domain 37) — how long can this continue?
│   → Retail SIP flows (Domain 36) — structural support
│
└── Options PCR Extreme (Domain 33)
    → Contrarian sentiment signal (Domain 40)
    → Max Pain gravity (Domain 33)
    → Expiry week positioning (Domain 34)
    → Short covering catalyst (Domain 3) — volume spike
```

---

## SECTION IX — INFORMATION COVERAGE MATRIX

This matrix drives the development roadmap. Priority is determined by Importance × Expected Impact / Collection Difficulty.

| # | Information Domain | Importance | Current Availability | Collection Difficulty | Expected Impact | Future Priority |
|---|---|---|---|---|---|---|
| 1 | Price Behavior (D2) | Critical | Full | Easy | Very High | Maintain |
| 2 | Volume Behavior (D3) | Critical | Full | Easy | Very High | Maintain |
| 3 | Options Information (D33) | Critical | Full (Dhan) | Medium | Very High | Enhance OI analysis |
| 4 | Futures & Derivatives (D34) | Critical | Full | Medium | High | Maintain |
| 5 | Macro Economic (D9) | Critical | Partial | Medium | Very High | Add PMI, IIP feeds |
| 6 | Monetary Policy (D10) | Critical | Partial | Easy | Very High | Add RBI full text parser |
| 7 | Global Market (D14) | Critical | Partial (yfinance) | Easy | Very High | Fix DXY/VIX/US10Y feeds |
| 8 | Volatility Information (D7) | Critical | Full | Easy | Very High | Maintain |
| 9 | Market Breadth (D4) | High | Partial | Medium | High | Build breadth dashboard |
| 10 | Sector Information (D19) | High | Partial | Medium | High | Expand sector rotation model |
| 11 | Institutional Activity (D35) | High | Daily FII/DII | Medium | High | Add MF quarterly mining |
| 12 | Fund Flow (D37) | High | FII equity only | Medium | High | Add FII debt, ETF flows |
| 13 | Corporate Fundamentals (D24) | High | Partial (yfinance) | Medium | High | Add structured fundamental DB |
| 14 | Earnings Information (D27) | High | Partial | Medium | High | Build results tracker |
| 15 | Valuation (D26) | High | Partial | Medium | High | Build valuation history DB |
| 16 | Volume Behavior — Delivery (D3) | High | Full (bhav) | Easy | High | Maintain |
| 17 | Sentiment (D40) | High | Partial (PCR, VIX) | Medium | Medium | Add survey data |
| 18 | Corporate Action (D28) | High | Partial | Medium | High | Build event calendar |
| 19 | Market Structure (D1) | Medium | Full | N/A | Medium | Maintain |
| 20 | Currency/FX (D16) | Critical | Partial | Easy | Very High | Fix USD/INR, DXY feeds |
| 21 | Commodity (D17) | High | Partial | Easy | High | Add sector mapping layer |
| 22 | Fixed Income (D18) | High | Partial (US10Y) | Medium | High | Add India G-Sec yield feed |
| 23 | Technical/Chart Structure (D8) | High | Full | Easy | High | Maintain |
| 24 | Analyst/Research (D42) | Medium | None | Hard | Medium | Long-term priority |
| 25 | Insider/Promoter Activity (D38) | High | None | Medium | High | Build SEBI scraper |
| 26 | Corporate Governance (D29) | Medium | None | Hard | Medium | Future module |
| 27 | Supply Chain (D21) | Medium | None | Very Hard | Medium | Future module |
| 28 | Regulatory Policy (D12) | High | None | Hard | High | Add regulatory event feeds |
| 29 | Geopolitical (D13) | Medium | None | Very Hard | Medium | News NLP long-term |
| 30 | ESG Information (D32) | Low | None | Hard | Low | 3+ year horizon |
| 31 | Alternative Data (D44) | Medium | None | Very Hard | Medium | 2+ year horizon |
| 32 | Credit & Debt Quality (D43) | High | None | Medium | High | Add rating change feeds |
| 33 | News & Media (D41) | Medium | None | Hard | Medium | NLP pipeline future |
| 34 | Learned Knowledge (D52) | Critical | Partial (OIOS) | N/A | Very High | OIOS Phase expansion |
| 35 | Historical Pattern (D46) | High | Partial | Derived | High | Expand behavioral library |
| 36 | Portfolio Information (D49) | Critical | Full | N/A | Very High | Maintain |
| 37 | Risk Information (D48) | Critical | Partial | Derived | Very High | Expand stress testing |
| 38 | Execution Information (D50) | High | Partial | Easy | High | Maintain + enhance |
| 39 | Calendar/Temporal (D51) | High | Partial | Easy | High | Build complete calendar |
| 40 | Relationship/Entity Graph (D47) | High | None | Hard | High | Entity graph future module |
| 41 | Derived & Computed (D53) | High | Full | Derived | High | Maintain |
| 42 | Decision Information (D56) | Critical | Full | N/A | Very High | Maintain + enhance audit |
| 43 | Reasoning Information (D55) | Critical | Partial | N/A | Very High | Expand conviction model |
| 44 | Market Microstructure (D5) | Medium | None | Hard | Medium | Future module |
| 45 | Liquidity Information (D6) | High | Partial | Medium | High | Add free float, pledge data |
| 46 | Index Information (D39) | High | Partial | Easy | High | Add MSCI rebalancing |
| 47 | Peer/Comparable Information (D20, D23, D26) | Medium | None | Medium | Medium | Build peer comparison layer |
| 48 | Competitive Intelligence (D23) | Medium | None | Very Hard | Medium | News NLP long-term |
| 49 | Retail Behavior (D36) | Medium | None | Medium | Medium | Add AMFI, demat data |
| 50 | Observation Records (D57) | High | Full | N/A | High | Maintain + formalize |

---

## SECTION X — ONTOLOGY INTEGRITY PRINCIPLES

1. **Every information type has exactly one authoritative definition in this document.** If an information type appears to belong to two domains, it is assigned to the more specific one with a cross-reference.

2. **Derived information always traces back to source information.** No derived information type is authoritative without documentation of its derivation path.

3. **Learned knowledge is always labeled as such.** It is never presented as objective fact — it is the system's current best estimate, subject to revision.

4. **Predictive information always carries uncertainty.** No prediction is stated as certain. Confidence levels and conditions are always explicit.

5. **This ontology is technology-independent.** Nothing in this document constrains the implementation. Any compliant technology that can represent these information types fulfills this ontology.

6. **This ontology is extensible.** New domains and information types can be added by following the same structure. Nothing in the existing ontology is deleted — only extended or refined.

7. **The Coverage Matrix is the development roadmap.** Priorities are set by the matrix. Modules that are not yet built are planned here as future priorities — not forgotten.

---

## DOCUMENT HISTORY

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-07-01 | Initial complete ontology — 57 domains, 400+ information types, Coverage Matrix |

---

*This document is the Dictionary of the AI Trading Brain.  
Every information type the system will ever process  
must be expressible within the taxonomy defined here.  
Extend this document before building any new intelligence module.*
