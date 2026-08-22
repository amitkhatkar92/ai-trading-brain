# RISK ENGINE ARCHITECTURE
## Investment Intelligence Operating System (IIOS)
### Document Code: IIOS-RSK-ENG-ARCH-001

---

**Document Scope:** Complete engineering architecture for the Risk Engine of the Investment Intelligence Operating System. The Risk Engine encompasses all risk management functions across the IIOS stack: capital protection, exposure control, stress testing, scenario analysis, threshold enforcement, and the Kill Switch.

**Document Status:** RATIFIED

**Series:** IIOS Architecture Document Series

**IIOS Layers covered:** Layer 6 (CapitalRiskEngine), Layer 7 (RiskControl), Layer 8 (MarketSimulation), Layer 9 (RiskGuardian)

**Predecessor documents consulted:**
- IIOS-KNW-ENG-ARCH-001 — Knowledge Engine Architecture
- IIOS-OBS-ENG-ARCH-001 — Observation Engine Architecture
- IIOS-EVD-ENG-ARCH-001 — Evidence Engine Architecture
- IIOS-HYP-ENG-ARCH-001 — Hypothesis Engine Architecture
- IIOS-RSN-ENG-ARCH-001 — Reasoning Engine Architecture
- IIOS-DEC-ENG-ARCH-001 — Decision Engine Architecture
- IIOS-EXE-ENG-ARCH-001 — Execution Engine Architecture
- IIOS-LRN-ENG-ARCH-001 — Learning Engine Architecture
- IIOS-PRD-ENG-ARCH-001 — Prediction Engine Architecture

**Critical invariants:**
- The Risk Engine NEVER creates investment ideas
- The Risk Engine NEVER overrides governance
- The Risk Engine NEVER bypasses the Decision Engine
- Capital preservation is ALWAYS prioritized over return maximization
- The Kill Switch is ALWAYS active and NEVER subject to override by any algorithm
- All risk assessments are independent, explainable, and fully auditable

---

## IIOS COGNITIVE STACK — RISK ENGINE CONTEXT

`
┌──────────────────────────────────────────────────────────────────────────────┐
│  IIOS COGNITIVE STACK                           Risk Engine Role              │
├──────┬───────────────────────────────────────┬──────────────────────────────┤
│  L1  │ GlobalIntelligence                    │ → Input: macro risk signals   │
│  L2  │ MarketIntelligence                    │ → Input: regime, VIX, events  │
│  L3  │ MetaLearning                          │ ← Output: strategy risk caps  │
│  L4  │ OpportunityEngine                     │ → Input: new opportunity risk │
│  L5  │ StrategyLab                           │ ← Output: strategy limits     │
│ ►L6  │ CapitalRiskEngine ◄═══════════════════╪══ RISK ENGINE OUTPUT (sizing) │
│ ►L7  │ RiskControl ◄══════════════════════════╪══ RISK ENGINE OUTPUT (limits) │
│ ►L8  │ MarketSimulation ◄══════════════════════╪══ RISK ENGINE OUTPUT (stress) │
│ ►L9  │ RiskGuardian ◄══════════════════════════╪══ RISK ENGINE OUTPUT (KS)     │
│  L10 │ DebateAndDecision                     │ → Input: proposed decisions   │
│  L11 │ ExecutionEngine                       │ → Input: execution records    │
│  L12 │ TradeMonitoring                       │ → Input: live positions, PNL  │
│  L13 │ LearningSystem                        │ → Input: risk model updates   │
│  L14 │ PerformanceAnalytics                  │ → Input: drawdown history     │
│  L15 │ ResearchLab                           │ ← Output: strategy risk gates │
│  L16 │ ValidationEngine                      │ ← Output: validation risk     │
│  L17 │ ControlTower                          │ ← Output: RSHS telemetry      │
├──────┴───────────────────────────────────────┴──────────────────────────────┤
│  ╔════════════════════════════════════════════════════════════════════╗       │
│  ║                    RISK ENGINE                                      ║       │
│  ║  Detect → Measure → Score → Validate →                             ║       │
│  ║  Threshold Check → Stress Test → Scenario →                        ║       │
│  ║  Govern → Monitor → Escalate → Protect                             ║       │
│  ╚════════════════════════════════════════════════════════════════════╝       │
└──────────────────────────────────────────────────────────────────────────────┘
`

---

## RISK ENGINE INFORMATION FLOW

`
              RISK ENGINE INFORMATION FLOW
              ════════════════════════════

[Information Engine]    ──→ market data, macro context, event signals
[Observation Engine]    ──→ real-time price action, volume, breadth
[Evidence Engine]       ──→ evaluated evidence signals with confidence
[Hypothesis Engine]     ──→ active hypotheses, risk hypothesis states
[Reasoning Engine]      ──→ inferred risk conclusions, causal chains
[Decision Engine L10]   ──→ proposed trade decisions (pre-execution)
[Execution Engine L11]  ──→ execution records, EQS, fills
[Learning Engine L13]   ──→ risk model calibrations, behavioral patterns
[Prediction Engine]     ──→ risk predictions, tail risk, scenario probabilities
[TradeMonitoring L12]   ──→ live P&L, open positions, session drawdown
[GlobalIntelligence L1] ──→ overnight global risk context
[MarketIntelligence L2] ──→ regime, VIX, sector risk, liquidity state
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │         RISK ENGINE            │
                       │                                │
                       │  Detect → Classify → Measure  │
                       │  → Expose → Validate →        │
                       │  Threshold → Stress → VaR →  │
                       │  Kill Switch → Govern →       │
                       │  Monitor → Escalate            │
                       └──────────────┬─────────────────┘
                                      │
           ┌──────────────────────────┼───────────────────────────┐
           │                          │                            │
           ▼                          ▼                            ▼
[L6 CapitalRiskEngine]   [L7 RiskControl / L9 RiskGuardian]   [L17 ControlTower]
Position sizes,           Risk limits, Kill Switch,             RSHS telemetry,
risk budgets              portfolio allocation                   risk dashboard
`

---

## TABLE OF CONTENTS

**Part I** — Risk Philosophy and Definitional Framework
**Part II** — Risk Taxonomy
**Part III** — Core Component Architecture
**Part IV** — Risk Lifecycle
**Part V** — Risk Services
**Part VI** — Risk Processing Pipelines
**Part VII** — Risk Quality Framework
**Part VIII** — Risk Governance
**Part IX** — Risk Constitution
**Part X** — Risk Readiness Checklist

**Supplement A** — Risk Taxonomy Reference
**Supplement B** — Risk Formulas (Conceptual)
**Supplement C** — Stress Testing Catalogue
**Supplement D** — Scenario Catalogue
**Supplement E** — Kill Switch Matrix
**Supplement F** — Escalation Framework
**Supplement G** — Operational Runbook
**Supplement H** — Comprehensive Glossary and Governing Design Records

**Appendix** — Worked Risk Examples (WE-01 through WE-06)
**Document Summary** — Metrics, Maps, Indexes, Compliance, Ratification

---

## PART I — RISK PHILOSOPHY AND DEFINITIONAL FRAMEWORK

### 1.1 What is Risk?

Risk is the possibility that the future will differ from expectation in a way that causes harm. In the context of the IIOS, risk is specifically the possibility that investment actions will result in capital loss, portfolio deterioration, or outcomes that fall below what rational decision-making would have accepted.

Risk is not simply the chance of loss — it is the full spectrum of deviation from intended outcomes, encompassing both the probability of adverse events and the magnitude of their consequences. A position that may lose 0.1% of portfolio value is a risk. A position that may lose 3% is also a risk, but a qualitatively different one. The IIOS Risk Engine must distinguish between risks not only by probability but by severity, duration, concentration, and correlation.

The fundamental asymmetry of risk in investment management is this: gains compound; losses compound too, but in the opposite direction. A 50% loss requires a 100% gain to recover. A 20% loss requires a 25% gain. This asymmetry is the structural reason why capital preservation is always prioritized over return maximization in the IIOS. It is not a philosophical choice — it is a mathematical necessity.

The Risk Engine is the institutional memory and real-time guardian that ensures this asymmetry is never forgotten, regardless of how favorable current conditions appear.

### 1.2 Definitional Ladder

**Risk (Level 1):**
The possibility of adverse outcomes due to uncertainty about the future. Risk exists wherever uncertainty exists. In the IIOS, risk is quantified, classified, monitored, and managed — but never eliminated.

*IIOS handling:* Every investment action generates a risk record. No action is taken without a risk assessment.

**Uncertainty (Level 2):**
The condition of not knowing the future outcome with certainty. Uncertainty is the source of all risk. Unlike risk, uncertainty may not be quantifiable. Uncertainty is irreducible in complex systems.

Distinction from risk: risk is quantifiable uncertainty; uncertainty is the broader condition of which quantifiable risk is the measurable component.

*IIOS handling:* The Prediction Engine produces probabilistic forecasts to quantify uncertainty. The Risk Engine uses those forecasts to compute risk measures. Pure uncertainty (unmeasurable) is handled by the Kill Switch — when uncertainty is extreme, trading stops.

**Volatility (Level 3):**
The statistical measure of the magnitude of price or value fluctuations over time. Volatility is a measure of variability, not direction. High volatility can produce large gains or large losses.

Distinction from risk: volatility is a statistical property of price behavior; risk is the consequence of that volatility for the portfolio.

*IIOS handling:* Realized volatility and implied volatility (India VIX) are primary inputs to position sizing (Layer 6), stress testing, and the Kill Switch.

**Loss (Level 4):**
A realized adverse outcome: the portfolio or position is worth less than it was before. Loss is the realization of risk that was accepted when a position was taken.

Distinction from risk: risk is the possibility of loss; loss is risk that has materialized.

*IIOS handling:* Session loss is monitored continuously by the Drawdown Monitor (RC-07). Daily loss exceeding 2% triggers the Kill Switch (constitutional threshold).

**Drawdown (Level 5):**
The decline in portfolio value from a peak to a subsequent trough. Drawdown is a time-series measure of loss. Maximum drawdown is the largest peak-to-trough decline over a defined period.

*IIOS handling:* Drawdown is a primary risk metric. The ResearchLab promotion gate requires MaxDD < 15% for strategy promotion. Strategy demotion is triggered by drawdown thresholds.

**Exposure (Level 6):**
The amount of capital at risk due to open positions. Gross exposure is the sum of all position values. Net exposure is long minus short. Exposure concentration is the degree to which exposure is concentrated in a single instrument, sector, or factor.

*IIOS handling:* The Exposure Engine (RC-05) computes gross, net, and concentrated exposure continuously. Position limits and portfolio limits enforce maximum exposures.

**Probability (Level 7):**
The quantified likelihood of an outcome occurring. In risk management, probability appears in VaR (the probability that a loss will exceed a threshold), in scenario probabilities, and in stress test results.

*IIOS handling:* The Prediction Engine's Probability Engine provides probability inputs; the Risk Engine's VaR Engine (RC-10) uses these to compute risk measures.

**Threat (Level 8):**
A potential source of harm to the portfolio. Threats are external: a regulatory change, a geopolitical event, a technology failure, a market disruption.

*IIOS handling:* The Risk Catalog (RC-02) maintains a registry of known threats with their current severity assessments.

**Hazard (Level 9):**
The condition that enables a threat to materialize. A hazard is the precondition for a threat to become a loss. High leverage is a hazard that amplifies the threat of market movement into a large loss.

*IIOS handling:* Hazard assessment is part of the Risk Analyzer (RC-03). Known hazards are identified and their contribution to risk is quantified.

**Tail Risk (Level 10):**
Risk arising from extreme outcomes in the tails of the probability distribution. Tail risk events are rare but potentially catastrophic. The fat-tailed nature of financial returns means tail events are significantly more probable than Gaussian models predict.

*IIOS handling:* The Tail Risk Engine (RC-11) is dedicated to measuring and monitoring tail risk. Tail risk predictions (PT-17 from the Prediction Engine) feed the Tail Risk Engine continuously.

**Black Swan (Level 11):**
An event that is outside the range of normal expectations, carries extreme impact, and in retrospect appears predictable (though it was not predicted in advance). Black swans are, by definition, not modelable — their probability distributions are unknown.

*IIOS handling:* Black swans cannot be predicted. The IIOS defends against them through: (a) position size limits that prevent any single event from being catastrophic, (b) diversification across strategies and instruments, (c) Kill Switch triggers that halt trading when conditions indicate potential systemic events, (d) conservative default settings when uncertainty is extreme.

**Stress (Level 12):**
Conditions of extreme market pressure that test the portfolio beyond normal operating parameters. Stress scenarios evaluate what happens to the portfolio in extreme but plausible scenarios.

*IIOS handling:* The Stress Testing Engine (RC-08) runs 14 stress scenarios at session start and on-demand during unusual market conditions.

**Capital Protection (Level 13):**
The active management practice of ensuring that the portfolio's capital base is preserved across all market conditions. Capital protection takes precedence over return generation in all Risk Engine decisions.

*IIOS handling:* Capital protection is a GDR (GDR-RSK-001). Every component in the Risk Engine is ultimately in service of capital protection.

**Risk Appetite (Level 14):**
The amount and type of risk the IIOS is willing to accept in pursuit of its objectives. Risk appetite is a strategic parameter that constrains all risk-taking. IIOS risk appetite is conservative by design.

*IIOS handling:* Risk appetite is encoded in risk thresholds, position limits, and portfolio limits. It is reviewed and set by human operators; the Risk Engine enforces it algorithmically.

**Risk Capacity (Level 15):**
The maximum amount of risk the IIOS can absorb without threatening its continued operation. Risk capacity is an objective measure based on capital base, liquidity, and operational resilience.

**Risk Tolerance (Level 16):**
The acceptable variation in outcomes within the risk appetite framework. Risk tolerance sets the operational bands within which the Risk Engine monitors and manages day-to-day risk.

---

### 1.3 Risk Types Explained

**Systemic Risk:**
Risk that affects the entire market or financial system simultaneously. Systemic risk cannot be reduced by diversification within the market. The 2008 financial crisis, COVID-19 market crash, and major central bank policy shifts are systemic risk events. IIOS defense: Kill Switch, position limits, conservative capital allocation.

**Idiosyncratic Risk:**
Risk specific to individual instruments, companies, or strategies. Idiosyncratic risk can be reduced through diversification. An earnings miss by TATASTEEL is idiosyncratic. IIOS defense: position concentration limits, sector limits, strategy diversification.

**Known Risk:**
Risks that are identified, classified, and quantifiable. Known risks include: market risk, liquidity risk, concentration risk. IIOS approach: model, measure, and manage known risks through the full Risk Engine architecture.

**Unknown Risk:**
Risks that are not identified or anticipated. Unknown risks cannot be directly managed, only indirectly defended against through general robustness measures. IIOS defense: conservative defaults, Kill Switch, capital reserves.

**Residual Risk:**
The risk that remains after all mitigation measures have been applied. No mitigation eliminates risk entirely. The IIOS accepts residual risk within the defined risk appetite.

**Emerging Risk:**
New or evolving risks that are beginning to materialize but have not yet been fully quantified. Cybersecurity risks, algorithmic trading instability risks, and AI model risks are examples. IIOS approach: Technology Risk (RT-18) and Cyber Risk (RT-19) are explicit taxonomy entries.

**Dynamic Risk:**
Risk that changes over time in response to market conditions, portfolio changes, or system state changes. Volatility regime changes, correlation breakdowns, and liquidity crises are examples of dynamic risk. IIOS defense: real-time monitoring, adaptive thresholds.

**Adaptive Risk:**
Risk that responds to the IIOS system's own behavior. Over-trading creates market impact risk. Concentrated positions attract adversarial trading. The Risk Engine must monitor for risks that its own actions create. IIOS defense: behavioral risk monitoring (RT-11), execution impact assessment.

---

### 1.4 Why Capital Preservation Always Dominates Return Maximization

The mathematical asymmetry of losses is the fundamental reason: it takes a larger percentage gain to recover from a loss than the percentage loss itself. A 10% loss requires an 11.1% gain. A 25% loss requires a 33.3% gain. A 50% loss requires a 100% gain.

This asymmetry compounds over time. A system that experiences periodic large drawdowns, even if it generates high average returns between drawdowns, will have lower terminal capital than a system with lower but more consistent returns.

The IIOS is designed for long-term survival and performance. A system that has survived 10 years with a maximum drawdown of 8% is more valuable than a system that has returned 40% in some years and been destroyed in others. Capital that is preserved earns future returns. Capital that is lost cannot.

The Risk Engine embeds this principle as GDR-RSK-001 (Capital Preservation is Primary). Every component, every threshold, and every rule in the Risk Engine is ultimately in service of this principle.

---

### 1.5 Risk Principles

**RP-001 — Capital preservation precedes return maximization.**
When risk management and return optimization conflict, risk management wins. Always.

**RP-002 — Every risk is measured before it is accepted.**
No position is taken without a risk assessment. No trade is executed without threshold validation.

**RP-003 — Risk assessments are independent.**
The Risk Engine's assessment of a proposed trade is independent of the Decision Engine's recommendation. A promising opportunity that exceeds risk limits is rejected, regardless of confidence level.

**RP-004 — All risk assessments are explainable.**
Every risk score, every limit breach, and every Kill Switch trigger is traceable to its driving data and rule. Risk decisions that cannot be explained are not valid.

**RP-005 — The Kill Switch is unconditional.**
When Kill Switch conditions are met, trading stops. No prediction, no evidence, no human override below emergency authority level can prevent it.

**RP-006 — Conservative calibration for risk.**
Risk parameters are calibrated conservatively. It is better to over-estimate risk (accept fewer trades) than to under-estimate risk (accept dangerous trades).

**RP-007 — Diversification is required.**
No single instrument, strategy, or sector is permitted to dominate portfolio risk. Concentration limits enforce mandatory diversification.

**RP-008 — Tail risk is never ignored.**
Tail probabilities from statistical models are systematically adjusted upward. Markets have fatter tails than models suggest.

**RP-009 — Stress testing is continuous.**
The portfolio is continuously evaluated against stress scenarios. Stress test results influence position sizing in real-time.

**RP-010 — Human override is absolute.**
Human operators may override any Risk Engine decision, except Kill Switch activation during active conditions.

---

## PART II — RISK TAXONOMY

### 2.0 Taxonomy Design Principles

The IIOS Risk Taxonomy provides an exhaustive, mutually understood classification of all risk types that the system is capable of detecting, measuring, and managing. Each risk type has a canonical identifier, a precise definition, measurable attributes, input sources, management strategies, and IIOS system integration points.

Risk types are not mutually exclusive. A single investment action may simultaneously create market risk, execution risk, concentration risk, and behavioral risk. The Risk Engine is responsible for measuring each applicable risk type independently, aggregating them coherently, and presenting a unified risk picture to the downstream risk management components.

Risk type codes follow the pattern RT-NN.

---

### RT-01 — Market Risk

**Definition:** The risk of loss due to adverse movements in market prices, including equity prices, indices, and derivative values. Market risk is the most fundamental and pervasive risk type in the IIOS.

**Dimensions:** Direction risk (portfolio loss from price movement), volatility risk (loss from volatility regimes changing), correlation risk (loss from correlation structure changing), convexity risk (non-linear price sensitivity).

**Primary inputs:** Real-time price data (Observation Engine), volatility regime (MarketIntelligence), prediction forecasts (Prediction Engine PT-01, PT-02).

**Measurement:** Delta (sensitivity to price), gamma (sensitivity to delta change), VaR (Value at Risk at defined confidence), CVaR (Conditional VaR beyond threshold), beta (sensitivity to index movement).

**Management levers:** Position sizing, stop-loss levels, hedging with inverse instruments, session P&L limits.

**IIOS integration:** CapitalRiskEngine (L6), RiskControl (L7), RiskGuardian (L9).

**Systemic/Idiosyncratic split:** Systematic component (market beta × index risk); idiosyncratic component (company-specific factors).

---

### RT-02 — Portfolio Risk

**Definition:** The aggregate risk arising from the combined portfolio of all open positions. Portfolio risk is not the sum of individual position risks — it is modified by correlations between positions. Two uncorrelated positions at identical risk combine to a lower total portfolio risk than two correlated positions.

**Key measures:** Portfolio VaR (reflects correlation), portfolio CVaR, contribution to VaR by position, diversification ratio (portfolio VaR / sum of individual VaRs).

**Failure mode:** Correlation breakdown — in stress events, correlations rise toward 1.0, eliminating the diversification benefit precisely when it is most needed.

**IIOS integration:** Correlation Engine (RC-06) provides the correlation matrix; Portfolio Limit Manager (RC-17) enforces portfolio-level constraints.

---

### RT-03 — Position Risk

**Definition:** The risk arising from a single open position. Position risk encompasses both the risk of adverse price movement and the risk of the position size being inappropriate for the current market regime.

**Metrics:** Position delta, position VaR, position CVaR, beta-adjusted exposure, concentration ratio (position / portfolio).

**Limits:** Maximum position size as a percentage of portfolio capital; maximum sector allocation; maximum individual equity weight.

**IIOS integration:** Position Limit Manager (RC-16) enforces per-position limits. Capital Risk Engine (L6) sizes positions within risk budget.

---

### RT-04 — Sector Risk

**Definition:** The risk of concentrated exposure to a single economic sector. Sector-specific events (regulatory action in financial services, commodity price changes for energy, demand collapse for technology) can cause simultaneous loss across multiple positions in the same sector.

**Metrics:** Sector exposure (sum of all positions in a sector / total portfolio), sector VaR contribution, sector correlation concentration.

**Limits:** Maximum sector exposure as a percentage of portfolio.

**IIOS integration:** Sector analysis from MarketIntelligence (L2); sector limits enforced by Portfolio Limit Manager (RC-17).

---

### RT-05 — Industry Risk

**Definition:** Finer-grained than sector risk. Industries within a sector may have distinct risk profiles. Within the financial sector, banking, insurance, and asset management are different industries with different risk drivers.

**Distinction from RT-04:** Sector risk aggregates broadly; industry risk provides finer-grained concentration monitoring.

**IIOS integration:** Industry classification from the Knowledge Engine entity taxonomy; industry limits a sub-component of sector limits.

---

### RT-06 — Liquidity Risk

**Definition:** The risk that a position cannot be exited at a desired price within a desired timeframe without causing significant market impact. Liquidity risk has two components: funding liquidity (ability to meet margin requirements) and market liquidity (ability to trade without price impact).

**Market liquidity sub-types:** Bid-ask spread widening; depth reduction (thin order book); market impact (large order moves the price); time-to-liquidation (how long it takes to exit a position without unacceptable impact).

**Metrics:** Average daily volume (ADV); position size as a multiple of ADV; bid-ask spread; market depth; liquidation horizon estimate.

**IIOS integration:** Prediction Engine (PT-04 — Liquidity Prediction); Execution Engine quality metrics; session management — large positions are reduced before low-liquidity periods.

---

### RT-07 — Execution Risk

**Definition:** The risk that a trade will not be executed as intended, resulting in worse-than-expected entry or exit prices, missed fills, or partial fills. Execution risk includes slippage, market impact, and timing risk.

**Sub-types:** Slippage risk (execution price differs from intended price); partial fill risk (order not fully filled); timing risk (conditions change between signal and execution); technology risk (order fails to reach the market due to system failure).

**Metrics:** Execution Quality Score (EQS) from Execution Engine; realized slippage; fill rate.

**IIOS integration:** Execution Engine (L11) EQS feeds the Risk Engine. Poor EQS triggers execution risk alerts and potential size reduction.

---

### RT-08 — Model Risk

**Definition:** The risk that the mathematical or statistical models used by the IIOS are incorrect, miscalibrated, or misapplied. Model risk arises from: (a) incorrect model assumptions, (b) incomplete training data, (c) overfitting to historical patterns that no longer apply, (d) model drift as market structure evolves.

**Sub-types:** Estimation risk (model parameters are uncertain); specification risk (model structure is wrong); implementation risk (correct model incorrectly coded); application risk (correct model used in wrong context).

**Metrics:** Model validation scores, out-of-sample accuracy, calibration error, regime generalization score.

**IIOS integration:** Learning Engine model performance monitoring; Prediction Engine PQS metrics; ValidationEngine (L16) six-stage pipeline.

---

### RT-09 — Prediction Risk

**Definition:** The specific risk arising from reliance on predictions generated by the Prediction Engine. Prediction risk encompasses both the possibility that forecasts are wrong and the possibility that the Decision Engine over-weights predictions relative to evidence.

**Sub-types:** Forecast accuracy risk; calibration risk (probability estimates are systematically off); regime change risk (predictions trained on historical regimes that no longer apply); overconfidence risk (Decision Engine over-trusts high-confidence predictions).

**IIOS integration:** Prediction Engine PQS monitoring; confidence-scoring input to Decision Engine; Risk Engine tracking of prediction-driven trade outcomes.

---

### RT-10 — Decision Risk

**Definition:** The risk that the Decision Engine makes an incorrect decision — approves a trade that should be rejected, rejects a trade that should be approved, or resolves the multi-agent debate in a way that reflects bias rather than evidence.

**Sub-types:** Commission bias (tendency to approve trades); threshold miscalibration (decision threshold set too permissively); debate dominance (one agent's view systematically dominates the debate without sufficient evidence); cascade risk (a chain of connected decisions amplifies a single error).

**IIOS integration:** Risk Engine reviews proposed decisions before execution. Learning Engine tracks decision outcome quality. Risk Governance Manager (RC-18) flags systematic decision patterns.

---

### RT-11 — Behavioral Risk

**Definition:** The risk arising from systematic cognitive and behavioral patterns in the IIOS's design that could lead to predictable, exploitable, or self-destructive behavior. In traditional finance, behavioral risk refers to human biases. In IIOS, it refers to algorithmic behavioral patterns.

**Sub-types:** Herding risk (all strategies converge to the same trades); over-trading risk (excessive trade frequency increases execution costs and slippage); recency bias (over-weighting recent market conditions in risk assessment); anchoring risk (thresholds not updated as market conditions change).

**IIOS integration:** Behavioral monitoring in the Risk Governance Manager (RC-18); trade frequency limits; strategy correlation monitoring.

---

### RT-12 — Counterparty Risk

**Definition:** The risk that the counterparty to a trade (broker, exchange, clearinghouse) fails to fulfill its obligations. In the IIOS context, this primarily refers to broker failure (Dhan) or exchange failure (NSE/BSE).

**Sub-types:** Broker insolvency risk; settlement failure risk; margin call risk (broker requires additional margin); connectivity risk (broker connection fails during open positions).

**IIOS integration:** Dhan connectivity monitoring (yfinance fallback for data); open position exposure to broker failure is monitored. The Kill Switch includes broker connectivity failure as a trigger condition.

---

### RT-13 — Currency Risk

**Definition:** The risk of loss due to adverse currency movements. In the IIOS (India equity market), this primarily applies to: (a) foreign-listed instruments or ETFs, (b) companies with significant foreign currency exposure affecting earnings, (c) macro-driven INR/USD exchange rate effects on equity valuations.

**IIOS integration:** GlobalIntelligence (L1) monitors FX rates; macro risk signals feed the MarketIntelligence risk assessment.

---

### RT-14 — Interest Rate Risk

**Definition:** The risk of loss due to adverse changes in interest rates. Interest rate risk in the equity context operates through: (a) discount rate effects on equity valuations, (b) debt cost effects on leveraged companies, (c) yield curve changes attracting capital flows away from equities.

**Metrics:** Portfolio interest rate sensitivity; sector-level debt-to-equity ratios for held positions; RBI monetary policy signals.

**IIOS integration:** GlobalIntelligence (L1) monitors bond yields; macro environment signals in MarketIntelligence (L2).

---

### RT-15 — Macro Risk

**Definition:** The risk arising from large-scale macroeconomic changes that affect the broad market environment. Macro risks include GDP growth changes, inflation, monetary policy shifts, fiscal policy changes, and global economic cycles.

**Metrics:** Current macroeconomic regime (GlobalIntelligence); confidence score; probability of regime change in next session.

**IIOS integration:** GlobalIntelligence (L1) provides macro risk context; regime-sensitive position sizing in Capital Risk Engine (L6).

---

### RT-16 — Political Risk

**Definition:** The risk of loss arising from political events, policy changes, geopolitical conflicts, elections, or regulatory actions driven by political factors.

**Sub-types:** Domestic political risk (Indian elections, budget announcements, policy shifts); geopolitical risk (trade conflicts, border tensions, global alliances); regulatory political risk (politically-driven regulatory changes to financial markets).

**IIOS integration:** EventRisk predictions from Prediction Engine (PT-16); GlobalIntelligence geopolitical monitors.

---

### RT-17 — Regulatory Risk

**Definition:** The risk arising from changes in laws, regulations, or exchange rules that affect the trading environment. SEBI regulations, NSE/BSE circuit breakers, F&O margin requirements, and position limit rules are all regulatory risk sources.

**IIOS integration:** Risk Policy Manager (RC-12) maintains current regulatory constraints; regulatory changes require Risk Threshold Manager updates.

---

### RT-18 — Technology Risk

**Definition:** The risk arising from failure of the technology systems that support the IIOS. Hardware failure, software bugs, database corruption, algorithm errors, and network failures all constitute technology risk.

**Sub-types:** Infrastructure failure; data feed failure; algorithm error; latency risk (decisions made on stale data); integration failure (IIOS component communication failure).

**IIOS integration:** System Monitor tracks all component latency; health monitoring via Risk Health Manager (RC-22); technology failure triggers escalation and potentially the Kill Switch.

---

### RT-19 — Cyber Risk

**Definition:** The risk of loss, operational disruption, or data breach due to malicious cyber activity. API key compromise, unauthorized trading, system intrusion, and DDoS attacks are examples.

**IIOS integration:** Security monitoring is a governance function. API credentials are never exposed in logs. System authentication is monitored. Unusual trading patterns may trigger the Kill Switch.

---

### RT-20 — Operational Risk

**Definition:** The risk arising from inadequate or failed internal processes, people, or systems. Misconfigured parameters, incorrect data, wrong order direction, and system startup failures are operational risks.

**Sub-types:** Process risk; human error risk; system failure risk; data quality risk.

**IIOS integration:** The Risk Engine's input validation pipeline checks data quality before any risk computation. Operational risk alerts feed the escalation framework.

---

### RT-21 — Concentration Risk

**Definition:** The risk arising from excessive concentration of exposure in a single instrument, sector, strategy, or risk factor. Concentration amplifies losses when the concentrated item underperforms.

**Metrics:** Herfindahl-Hirschman Index (HHI) of portfolio weights; maximum single-name exposure ratio; maximum sector exposure ratio.

**Limits:** Hard concentration limits enforced by Position Limit Manager (RC-16) and Portfolio Limit Manager (RC-17).

**IIOS integration:** Concentration risk is continuously monitored; new positions that would create concentration are rejected unless within defined tolerance.

---

### RT-22 — Correlation Risk

**Definition:** The risk arising from the instability of correlations between portfolio positions. Diversification depends on correlations remaining below 1.0. In market stress events, correlations of seemingly unrelated instruments rise sharply — this is the diversification breakdown phenomenon.

**Metrics:** Realized correlation matrix; rolling correlation stability; correlation regime change probability (from Prediction Engine).

**IIOS integration:** Correlation Engine (RC-06) monitors correlation stability; regime-based correlation adjustments in stress testing.

---

### RT-23 — Tail Risk

**Definition:** The risk arising from extreme outcomes in the tail of the probability distribution. Financial returns are fat-tailed — extreme events occur more frequently than a normal distribution predicts. Tail risk measures the expected loss conditional on being in the tail of the distribution.

**Metrics:** Conditional VaR (CVaR) at 95% and 99% confidence; expected shortfall (ES); historical maximum loss; stress test outcomes.

**IIOS integration:** Tail Risk Engine (RC-11); Prediction Engine PT-17 (Tail Risk Prediction); Kill Switch triggers.

---

### RT-24 — Black Swan Risk

**Definition:** The risk of unprecedented, unpredicted, extreme events that fall outside the range of historical experience. Black swans, by definition, cannot be predicted or modeled from historical data. Defense is structural, not predictive.

**IIOS defense:** Position size limits ensure no single event is catastrophic; Kill Switch halts trading when market conditions are extreme; capital reserves preserve the ability to resume after a black swan event.

---

### RT-25 — Event Risk

**Definition:** The risk arising from specific discrete events that cause sudden, large price movements. Earnings announcements, central bank decisions, geopolitical events, natural disasters, and corporate actions (mergers, delistings, dividends) are event risks.

**Metrics:** Probability of event occurrence; estimated event impact on held positions.

**IIOS integration:** Prediction Engine PT-16 (Event Prediction); pre-event risk reduction is triggered by the Capital Protection Manager (RC-15) when event probability exceeds thresholds.

---

### RT-26 — Strategy Risk

**Definition:** The risk arising from the strategies themselves: that a strategy was overfitted, that its regime has ended, that its capacity is limited, or that multiple strategies are highly correlated in their trading behavior.

**Sub-types:** Strategy overfitting risk; regime non-stationarity risk; strategy capacity risk; strategy correlation risk (all strategies simultaneously enter the same trade); strategy concentration risk (too much capital allocated to a single strategy).

**IIOS integration:** Learning Engine monitors strategy performance; strategy demotion thresholds; ResearchLab promotion gates; strategy correlation monitoring in Correlation Engine (RC-06).

---

### 2.1 Risk Taxonomy Summary Table

| Code  | Risk Type           | Scope       | Primary Engine         | Kill Switch Trigger |
|-------|---------------------|-------------|------------------------|---------------------|
| RT-01 | Market Risk         | Position    | L6, L7, RC-04          | Indirect            |
| RT-02 | Portfolio Risk      | Portfolio   | RC-06, RC-17           | Indirect            |
| RT-03 | Position Risk       | Position    | RC-16, RC-04           | Indirect            |
| RT-04 | Sector Risk         | Portfolio   | RC-17, RC-04           | No                  |
| RT-05 | Industry Risk       | Portfolio   | RC-17, RC-04           | No                  |
| RT-06 | Liquidity Risk      | Position    | RC-05, RC-14           | Indirect            |
| RT-07 | Execution Risk      | Trade       | L11 EQS, RC-04         | No                  |
| RT-08 | Model Risk          | System      | L16 Validation         | No                  |
| RT-09 | Prediction Risk     | System      | Prediction Engine PQS  | No                  |
| RT-10 | Decision Risk       | Decision    | RC-18 Governance       | No                  |
| RT-11 | Behavioral Risk     | System      | RC-18 Governance       | No                  |
| RT-12 | Counterparty Risk   | Broker      | RC-14 Kill Switch      | Direct              |
| RT-13 | Currency Risk       | Portfolio   | L1 GlobalIntelligence  | No                  |
| RT-14 | Interest Rate Risk  | Portfolio   | L1, L2                 | No                  |
| RT-15 | Macro Risk          | System      | L1, L2                 | Indirect            |
| RT-16 | Political Risk      | System      | Prediction PT-16       | Indirect            |
| RT-17 | Regulatory Risk     | System      | RC-12 Policy           | Indirect            |
| RT-18 | Technology Risk     | System      | System Monitor         | Direct              |
| RT-19 | Cyber Risk          | System      | Security Monitoring    | Direct              |
| RT-20 | Operational Risk    | System      | RC-20 Archive          | Indirect            |
| RT-21 | Concentration Risk  | Portfolio   | RC-16, RC-17           | No                  |
| RT-22 | Correlation Risk    | Portfolio   | RC-06 Correlation      | No                  |
| RT-23 | Tail Risk           | Portfolio   | RC-11 Tail Risk        | Direct              |
| RT-24 | Black Swan Risk     | System      | RC-14 Kill Switch      | Direct              |
| RT-25 | Event Risk          | Position    | Prediction PT-16       | Indirect            |
| RT-26 | Strategy Risk       | Strategy    | Learning Engine        | No                  |

---

## PART III — CORE COMPONENT ARCHITECTURE

### 3.0 Component Design Principles

The Risk Engine is organized into twenty-two core components. Each component is a logically distinct unit of risk management responsibility. Components communicate through defined interfaces, never through direct state sharing. Each component's failure is isolated — the failure of one component must not cascade to disable unrelated components.

Component codes follow the pattern RC-NN.

**Four-Tier Component Architecture:**

| Tier | Name               | Components         | Purpose                                    |
|------|--------------------|--------------------|--------------------------------------------|
| T1   | Detection Layer    | RC-01 to RC-06     | Identify and measure risk                  |
| T2   | Assessment Layer   | RC-07 to RC-11     | Evaluate risk magnitude and scenarios      |
| T3   | Control Layer      | RC-12 to RC-17     | Enforce limits, thresholds, and Kill Switch|
| T4   | Governance Layer   | RC-18 to RC-22     | Govern, audit, archive, and report         |

---

### RC-01 — Risk Registry

**Purpose:** The Risk Registry is the IIOS master record of all active, acknowledged, and archived risk records. Every risk event, limit breach, Kill Switch trigger, and governance action originates in or is recorded in the Risk Registry.

**Responsibilities:**
1. Maintain the authoritative register of all current risk records
2. Assign canonical risk record identifiers (RSK-{TYPE}-{YYYYMMDD}-{SEQ:08d})
3. Enforce risk record schema validity on all inbound records
4. Provide query interface for current active risks
5. Propagate risk state changes to all subscribed components
6. Maintain hash chain integrity for audit compliance
7. Enforce immutability of finalized risk records
8. Provide risk snapshot at any point in time
9. Support time-travel queries (state of risk register at any past timestamp)
10. Track risk record lifecycle from creation through archival

**Inputs:**
- Risk detection signals from RC-03 (Risk Analyzer)
- Limit breach notifications from RC-13 (Risk Threshold Manager)
- Kill Switch events from RC-14 (Kill Switch Manager)
- Governance actions from RC-18 (Risk Governance Manager)
- Audit events from RC-19 (Risk Audit Manager)

**Outputs:**
- Canonical risk records to all Risk Engine components
- Active risk summary to Risk Health Manager (RC-22)
- Risk state changes to event bus for downstream layers
- Archive-ready records to Risk Archive Manager (RC-20)

**Dependencies:** Risk Catalog (RC-02) for risk type classification; Risk Audit Manager (RC-19) for hash chain management.

**Interactions:** All Risk Engine components read active risk records from the Registry. The Registry does not compute risk — it records it.

**Failure Modes:**
- Write failure: Risk record not persisted — alert immediate, no risk actions until resolved
- Hash chain corruption: Registry integrity compromised — system enters read-only mode, Kill Switch evaluation continues on in-memory state
- Query performance degradation: Slow reads delay risk assessment — mitigated by in-memory active risk cache

**Recovery Strategy:** Primary: restart with journal replay. Secondary: promote read-only replica to primary, reconcile divergent records after recovery. All risk actions taken during failure are logged separately and reconciled.

**Monitoring:** Registry write latency; record count by type and status; hash chain validation status; query response time.

**Scalability:** Registry is partitioned by session date. Active partition is memory-resident for fast reads. Historical partitions are archived to persistent storage.

**Extensibility:** New risk types are added by extending the Risk Catalog (RC-02), not by modifying the Registry schema. The Registry schema is fixed — it records risk records in a type-agnostic way, with type-specific attributes as a structured extension.

**Engineering Notes:** The Risk Registry is the single source of truth for all risk information in the IIOS. It must be available before any risk computation begins and must remain available throughout the trading session. Recovery from Registry failure takes priority over all other recovery activities.

---

### RC-02 — Risk Catalog

**Purpose:** The Risk Catalog is the controlled vocabulary and classification authority for all risk types in the IIOS. It defines what types of risks exist, their properties, their relationships to each other, and their classification rules.

**Responsibilities:**
1. Maintain the canonical list of all supported risk types (RT-01 through RT-26 and future types)
2. Define classification rules for mapping raw risk signals to risk types
3. Maintain risk type hierarchy (category → subcategory → specific type)
4. Define measurement frameworks for each risk type
5. Specify default thresholds for each risk type (which the Risk Threshold Manager enforces)
6. Maintain risk type versioning (catalog version controls the type definitions)
7. Support multi-classification (a single risk signal may map to multiple risk types)
8. Provide risk type descriptions for governance and audit reporting
9. Maintain inter-type relationships (RT-21 Concentration Risk is exacerbated by RT-04 Sector Risk)
10. Track which risk types are currently active in the IIOS

**Inputs:**
- Governance updates from Risk Policy Manager (RC-12)
- New risk type proposals from Risk Governance Manager (RC-18)
- Regulatory changes from external governance inputs

**Outputs:**
- Risk type definitions to Risk Analyzer (RC-03)
- Classification rules to all detection components
- Threshold defaults to Risk Threshold Manager (RC-13)

**Failure Modes:** Catalog corruption — fall back to last validated version; no new classifications until catalog is restored.

**Engineering Notes:** The Risk Catalog is read-only during trading sessions. Modifications are only applied at session start after validation. The Catalog is a governance artifact — changes require formal review.

---

### RC-03 — Risk Analyzer

**Purpose:** The Risk Analyzer is the primary detection and classification engine. It continuously processes incoming signals from all upstream engines, identifies risk conditions, classifies them against the Risk Catalog, and creates draft risk records for the Risk Registry.

**Responsibilities:**
1. Continuously receive and process signals from all input sources
2. Detect emerging risk conditions before they breach thresholds
3. Classify detected risks against Risk Catalog (RT-01 through RT-26)
4. Assign preliminary severity scores to detected risks
5. Identify correlated risks (multiple risk types triggered by a single event)
6. Construct risk causal chains (which upstream condition drove this risk)
7. Forward classified risk records to Risk Registry (RC-01)
8. Maintain risk detection history for pattern analysis
9. Provide real-time risk signal dashboard to Risk Health Manager (RC-22)
10. Support on-demand risk analysis for specific scenarios or positions

**Inputs:**
- Market data from Observation Engine (price, volume, volatility)
- Evidence assessments from Evidence Engine
- Predictions from Prediction Engine (all 18 types)
- Execution records from Execution Engine (L11)
- Portfolio state from TradeMonitoring (L12)
- Macro context from GlobalIntelligence (L1)
- Regime signals from MarketIntelligence (L2)
- Learning signals from Learning Engine (L13)
- Decision proposals from Decision Engine (L10)

**Outputs:**
- Classified risk records to Risk Registry (RC-01)
- Severity assessments to Risk Scoring Engine (RC-04)
- Causal chains to Risk Audit Manager (RC-19)
- Real-time signals to Risk Health Manager (RC-22)

**Failure Modes:**
- Input source failure: Continue with available inputs; log missing source; flag uncertainty elevation
- Classification failure: Route unclassified signal to "uncategorized risk" bucket; human review queue
- Performance degradation: Implement signal priority queue — Kill Switch signals always first; market risk second; all others behind

**Recovery Strategy:** The Risk Analyzer maintains a signal buffer for brief outages. On recovery, buffered signals are processed in priority order. Signals older than the session are discarded.

**Monitoring:** Detection latency per signal type; classification accuracy (post-session audit); false positive/negative rates; signal throughput.

**Engineering Notes:** The Risk Analyzer is a stream processor, not a batch processor. Its latency directly determines the IIOS's response time to emerging risks. Target: < 100ms from signal arrival to risk record creation.

---

### RC-04 — Risk Scoring Engine

**Purpose:** The Risk Scoring Engine computes quantitative risk scores for all classified risks. It aggregates individual risk assessments into portfolio-level Risk Scores and produces the Risk Quality Score (RQS) that governs overall risk system health.

**Responsibilities:**
1. Compute per-risk severity scores using type-specific scoring algorithms
2. Aggregate individual risk scores into position-level composite scores
3. Aggregate position-level scores into portfolio-level composite Risk Score
4. Compute the Risk Quality Score (RQS) across 12 dimensions
5. Track score evolution over time to detect deterioration trends
6. Produce risk score explanations for governance and audit
7. Maintain score calibration against realized outcomes
8. Compute regime-adjusted scores (risk is higher in uncertain regimes)
9. Score validation: reject scores outside the valid range [0.0, 1.0]
10. Provide comparative scoring: how does current risk compare to historical distributions?

**Inputs:**
- Classified risk records from Risk Analyzer (RC-03)
- Portfolio state (positions, exposure) from TradeMonitoring (L12)
- Volatility state from MarketIntelligence (L2)
- Correlation matrix from Correlation Engine (RC-06)
- Historical risk outcomes from Risk Archive Manager (RC-20)

**Outputs:**
- Per-risk scores to Risk Registry (RC-01)
- Portfolio risk score to Risk Threshold Manager (RC-13)
- RQS score to Risk Health Manager (RC-22)
- Score explanations to Risk Audit Manager (RC-19)

**Risk Quality Score (RQS) Formula:**

RQS = 0.20 x RQD-01 (Accuracy)
    + 0.15 x RQD-02 (Sensitivity)
    + 0.12 x RQD-03 (Timeliness)
    + 0.10 x RQD-04 (Coverage)
    + 0.10 x RQD-05 (Consistency)
    + 0.08 x RQD-06 (Robustness)
    + 0.08 x RQD-07 (Reliability)
    + 0.05 x RQD-08 (Explainability)
    + 0.05 x RQD-09 (Traceability)
    + 0.03 x RQD-10 (Governance)
    + 0.02 x RQD-11 (Auditability)
    + 0.02 x RQD-12 (Capital Protection Effectiveness)

All weights sum to 1.00. All dimension scores are in [0.0, 1.0].

**RQS Tiers:**

| Tier       | Range        | Meaning                                     |
|------------|--------------|---------------------------------------------|
| EXCELLENT  | 0.88 - 1.00  | Risk system operating optimally              |
| GOOD       | 0.72 - 0.87  | Risk system operating well within bounds     |
| ACCEPTABLE | 0.55 - 0.71  | Risk system operational; monitor closely     |
| MARGINAL   | 0.35 - 0.54  | Risk system degraded; reduce position sizes  |
| FAILED     | 0.00 - 0.34  | Risk system failed; halt new trades          |

**Failure Modes:** Score engine crash — freeze scores at last valid state; escalate immediately; no new trades until recovery.

---

### RC-05 — Exposure Engine

**Purpose:** The Exposure Engine continuously computes the IIOS portfolio's financial exposure across all dimensions: gross, net, sector, strategy, factor, and tail exposure. Exposure is the primary input to position sizing and portfolio limit enforcement.

**Responsibilities:**
1. Compute gross exposure (sum of all position market values)
2. Compute net exposure (long minus short in currency terms)
3. Compute sector exposure by RT-04 sector classification
4. Compute industry exposure by RT-05 industry classification
5. Compute strategy exposure (how much capital allocated to each strategy)
6. Compute factor exposure (sensitivity to market factors: momentum, value, volatility)
7. Compute tail exposure (expected loss under tail scenarios)
8. Track exposure changes in real-time as positions are opened, modified, and closed
9. Project exposure evolution given pending orders
10. Compute exposure utilization ratios (current exposure / allowed exposure limits)

**Inputs:**
- Live positions from TradeMonitoring (L12)
- Pending orders from Execution Engine (L11)
- Portfolio history from Risk Archive Manager (RC-20)
- Market prices from Observation Engine

**Outputs:**
- Exposure vectors to Risk Threshold Manager (RC-13)
- Gross/net exposure to Portfolio Limit Manager (RC-17)
- Factor exposure to Correlation Engine (RC-06)
- Tail exposure to Tail Risk Engine (RC-11)

**Exposure Record Format:**

| Field           | Description                                |
|-----------------|--------------------------------------------|
| timestamp       | UTC nanosecond timestamp                   |
| session_date    | Trading session date                       |
| gross_exposure  | Sum of all position absolute values (INR)  |
| net_exposure    | Long - Short (INR)                         |
| net_pct         | Net exposure / portfolio NAV               |
| sector_map      | Map of sector code to exposure (INR)       |
| strategy_map    | Map of strategy ID to exposure (INR)       |
| largest_position| Symbol and size of largest single position |
| utilization_pct | gross_exposure / maximum_allowed_exposure  |

**Engineering Notes:** Exposure must be updated within 100ms of any position change. Stale exposure data must be flagged and acted on: if exposure data is more than 500ms old, the Exposure Engine raises a STALE_EXPOSURE alert.

---

### RC-06 — Correlation Engine

**Purpose:** The Correlation Engine maintains the statistical correlation structure between all instruments and strategies currently in the portfolio. Correlation is critical to accurate portfolio risk measurement — ignoring correlations systematically understates portfolio risk.

**Responsibilities:**
1. Compute rolling realized correlation matrix for all portfolio instruments
2. Maintain exponentially-weighted moving correlation estimates (EWMA)
3. Detect correlation regime changes (from decorrelated to correlated state)
4. Provide stress-state correlation estimates (correlations approach 1.0 in stress)
5. Compute strategy correlation (are strategies entering the same trades?)
6. Monitor pairwise correlation stability over time
7. Provide correlation-adjusted VaR inputs to VaR Engine (RC-10)
8. Alert when correlation breakdown events are detected
9. Compute diversification ratio (portfolio VaR / sum of individual VaRs)
10. Track correlation between IIOS strategy signals (behavioral risk RT-11 monitoring)

**Inputs:**
- Historical price series from data feeds (yfinance)
- Execution records from Execution Engine (L11) for strategy correlation
- Stress regime signals from Stress Testing Engine (RC-08)
- Prediction Engine correlation forecasts (PT-02 Trend, PT-03 Volatility)

**Outputs:**
- Correlation matrix to VaR Engine (RC-10)
- Correlation matrix to Portfolio Limit Manager (RC-17)
- Correlation matrix to Risk Scoring Engine (RC-04)
- Correlation alerts to Risk Registry (RC-01)
- Diversification ratio to Risk Health Manager (RC-22)

**EWMA Correlation Formula (conceptual):**

For instruments i and j:
- rho_ewma(t) = lambda x rho_ewma(t-1) + (1 - lambda) x r_i(t) x r_j(t)
- lambda is the decay factor (shorter decay = faster adaptation to regime changes)
- Normal regime lambda: 0.94 (slow adaptation)
- Stress regime lambda: 0.75 (fast adaptation)

**Failure Modes:** Insufficient price history — compute partial correlation with available data; flag instruments with short history. Correlation instability — enter conservative mode: apply stress-state correlation estimates uniformly.

**Engineering Notes:** The correlation matrix scales quadratically with the number of instruments. For N instruments, there are N(N-1)/2 pairs. For the IIOS typical portfolio (up to 10 instruments), this is manageable. For opportunity scanning (100+ instruments), the Correlation Engine uses a factor model approximation to reduce computation.

---

### RC-07 — Drawdown Monitor

**Purpose:** The Drawdown Monitor tracks portfolio and position-level drawdown in real-time throughout the trading session. It is the primary early warning system for capital deterioration and the most direct embodiment of the capital preservation mandate.

**Responsibilities:**
1. Compute intraday portfolio drawdown from the session peak P&L
2. Compute per-position drawdown from position entry price
3. Compute per-strategy drawdown from strategy high-water mark
4. Track running maximum portfolio P&L (session peak)
5. Continuously compare current P&L to peak to compute current drawdown
6. Trigger drawdown alerts at configurable thresholds (1.0%, 1.5%, 2.0%)
7. Escalate to Kill Switch Manager (RC-14) when daily loss threshold is breached (2.0%)
8. Maintain historical drawdown statistics: maximum session drawdown, average daily drawdown
9. Provide drawdown trajectory — is the portfolio recovering or still deteriorating?
10. Compute time-in-drawdown statistics for strategy governance

**Inputs:**
- Real-time P&L from TradeMonitoring (L12)
- Position data from Execution Engine (L11)
- Session peak P&L (maintained internally)
- Strategy P&L attribution from LearningSystem (L13)

**Outputs:**
- Current drawdown to Risk Registry (RC-01)
- Drawdown alerts to Risk Threshold Manager (RC-13)
- Kill Switch trigger signal to Kill Switch Manager (RC-14) when DD > 2.0%
- Strategy drawdown reports to LearningSystem (L13) for governance

**Drawdown State Machine:**

`
NORMAL (DD < 1.0%)
  ├── DD reaches 1.0% → ALERT_L1
ALERT_L1 (1.0% <= DD < 1.5%)
  ├── DD falls below 0.8% → NORMAL
  ├── DD reaches 1.5% → ALERT_L2
ALERT_L2 (1.5% <= DD < 2.0%)
  ├── DD falls below 1.2% → ALERT_L1
  ├── DD reaches 2.0% → KILL_SWITCH_TRIGGER
KILL_SWITCH_TRIGGER (DD >= 2.0%)
  └── Kill Switch activated → session halted
`

**Failure Modes:** P&L feed disruption — use last known P&L; assume worst case (continue falling); escalate if gap > 30 seconds. Drawdown Monitor failure — Kill Switch assumes maximum drawdown is active; halts trading until monitor is restored.

**Engineering Notes:** Drawdown computation must have < 50ms latency. A delayed drawdown alarm that prevents timely Kill Switch activation is a critical failure. The Drawdown Monitor is a Tier-1 safety component.

---

### RC-08 — Stress Testing Engine

**Purpose:** The Stress Testing Engine evaluates the portfolio against a catalogue of defined stress scenarios. It answers the question: what would happen to this portfolio if a specific adverse market event occurred?

**Responsibilities:**
1. Maintain the IIOS stress scenario catalogue (14 standard scenarios plus custom scenarios)
2. Apply stress scenarios to the current portfolio at session start
3. Apply on-demand stress tests when market conditions change significantly
4. Apply intraday stress tests at defined checkpoints (10:00, 11:30, 13:00, 14:30)
5. Compute portfolio P&L impact for each stress scenario
6. Compute position-level impact for each stress scenario
7. Identify which positions are most vulnerable under each scenario
8. Compare stress test results to capital tolerance thresholds
9. Recommend position reductions when stress test losses exceed limits
10. Archive all stress test results for historical analysis

**Inputs:**
- Current portfolio positions from TradeMonitoring (L12)
- Current market prices from Observation Engine
- Correlation matrix from Correlation Engine (RC-06)
- Stress scenario definitions from Scenario Engine (RC-09)
- Historical stress calibrations from Risk Archive Manager (RC-20)

**Outputs:**
- Stress test results to Risk Registry (RC-01)
- Portfolio stress loss to Risk Threshold Manager (RC-13)
- Position-level stress impacts to Capital Protection Manager (RC-15)
- Vulnerability report to Risk Analytics Manager (RC-21)

**Standard Stress Scenarios (14):**

| ID    | Name                          | Market Impact                              |
|-------|-------------------------------|--------------------------------------------|
| SS-01 | Market Circuit Breaker 5%     | Index drops 5% intraday                    |
| SS-02 | Market Circuit Breaker 10%    | Index drops 10% intraday                   |
| SS-03 | Flash Crash                   | Index drops 15% within 30 minutes          |
| SS-04 | Volatility Spike (VIX 50+)    | VIX doubles from current, all corr to 1.0  |
| SS-05 | Liquidity Crisis               | Bid-ask spreads widen 5x; depth falls 80%  |
| SS-06 | RBI Emergency Rate Hike       | 100bps surprise rate hike; equity -6%      |
| SS-07 | Sector Shock                  | Largest portfolio sector drops 15%         |
| SS-08 | Single Name Collapse          | Largest position drops 20% limit down      |
| SS-09 | FII Outflow Event             | Systemic foreign selling; market -8%       |
| SS-10 | INR Currency Crisis           | INR/USD falls 5%; FII flight               |
| SS-11 | Global Contagion              | Correlated global sell-off (-12% NSE)      |
| SS-12 | Earnings Disaster             | Portfolio's largest position misses -25%   |
| SS-13 | Correlation Breakdown         | All portfolio correlations → 0.95          |
| SS-14 | Technology Failure            | Order routing fails; positions unhedgeable |

**Stress Test Governance:** Any individual scenario showing portfolio loss > 2% of NAV requires position reduction to bring the scenario loss below threshold. Refusal to reduce requires Kill Switch escalation.

**Failure Modes:** Scenario data corruption — run with conservative parameter substitution; alert operator. Engine crash — fall back to simplified stress heuristics until engine is restored.

---

### RC-09 — Scenario Engine

**Purpose:** The Scenario Engine generates, maintains, and evaluates risk scenarios — structured representations of possible future states that are used to evaluate portfolio risk under different market conditions. The Scenario Engine provides scenario infrastructure for both the Stress Testing Engine (historical stress scenarios) and the Prediction Engine (forward-looking probabilistic scenarios).

**Responsibilities:**
1. Maintain the full scenario catalogue (stress scenarios + Prediction Engine scenarios)
2. Generate new scenarios from Prediction Engine inputs (PT-07 Portfolio Prediction, PT-08 Scenario types)
3. Evaluate scenario probability from the Prediction Engine
4. Compute portfolio impact for each scenario
5. Track scenario validation: did the predicted scenario materialize?
6. Maintain scenario history for calibration of future scenario probabilities
7. Coordinate scenario sets: ensure coverage of full probability space (scenario probabilities should sum close to 1.0)
8. Identify scenario gaps — market states not covered by any scenario
9. Compute expected portfolio P&L as the probability-weighted average across scenarios
10. Archive completed scenarios with outcome data

**Inputs:**
- Scenario predictions from Prediction Engine (PT-08, PT-15 Scenario Prediction)
- Historical market events from Risk Archive Manager (RC-20)
- Macro state from GlobalIntelligence (L1)
- Stress scenarios from Stress Testing Engine (RC-08)

**Outputs:**
- Scenario records to Risk Registry (RC-01)
- Probability-weighted portfolio impact to Capital Protection Manager (RC-15)
- Scenario probabilities to VaR Engine (RC-10)
- Scenario archive to Risk Archive Manager (RC-20)

**Scenario Record Structure:**

| Field               | Description                                        |
|---------------------|----------------------------------------------------|
| scenario_id         | SCN-{TARGET}-{YYYYMMDD}-{SEQ:04d}                  |
| scenario_type       | STRESS / PREDICTION / CUSTOM                       |
| description         | Human-readable scenario description                |
| trigger_conditions  | Market conditions that define the scenario         |
| probability         | Assigned probability [0.01, 1.0]                   |
| portfolio_impact    | Expected P&L impact (INR and pct NAV)              |
| position_impacts    | Per-position P&L impacts                           |
| status              | ACTIVE / INVALIDATED / REALIZED / ARCHIVED         |
| expiry              | When the scenario is no longer relevant            |

---

### RC-10 — VaR Engine

**Purpose:** The Value at Risk (VaR) Engine computes the portfolio's VaR and Conditional VaR (CVaR) at defined confidence levels. VaR answers: with a given probability, the portfolio will not lose more than X. CVaR answers: given that the loss exceeds VaR, what is the expected magnitude?

**Responsibilities:**
1. Compute 1-day VaR at 95% confidence (operational VaR)
2. Compute 1-day VaR at 99% confidence (regulatory/stress VaR)
3. Compute CVaR (Expected Shortfall) at 95% and 99%
4. Compute component VaR — each position's contribution to portfolio VaR
5. Compute incremental VaR — the change in portfolio VaR from adding a position
6. Provide VaR decomposition: systematic VaR vs idiosyncratic VaR
7. Support multiple VaR methodologies: historical simulation, parametric, Monte Carlo
8. Track VaR accuracy: VaR exceedances (proportion of days actual loss exceeded VaR)
9. Provide VaR backtest results for model governance
10. Compute VaR utilization: current VaR / VaR limit

**Inputs:**
- Historical return data from data feeds
- Correlation matrix from Correlation Engine (RC-06)
- Portfolio positions from Exposure Engine (RC-05)
- Scenario probabilities from Scenario Engine (RC-09)
- Tail risk parameters from Tail Risk Engine (RC-11)

**Outputs:**
- Portfolio VaR to Risk Threshold Manager (RC-13)
- Component VaR to Portfolio Limit Manager (RC-17)
- VaR backtest results to Risk Governance Manager (RC-18)
- VaR time series to Risk Analytics Manager (RC-21)

**VaR Methodologies:**

Historical Simulation:
- Uses the actual historical distribution of portfolio returns (no parametric assumptions)
- Advantages: captures actual fat tails; no distribution assumptions
- Disadvantages: limited by historical window; may not represent current regime
- IIOS use: primary VaR methodology

Parametric VaR:
- Assumes portfolio returns are normally distributed
- Advantages: computationally simple; well-understood
- Disadvantages: underestimates tail risk due to normality assumption
- IIOS use: secondary methodology; used as a fast sanity check

Monte Carlo VaR:
- Simulates thousands of return paths using stochastic models
- Advantages: can incorporate complex non-linear dependencies
- Disadvantages: computationally intensive; depends on model quality
- IIOS use: stress scenarios and option-heavy portfolios

**VaR Limits:**

| VaR Type            | Confidence | Limit (% NAV) |
|---------------------|------------|----------------|
| Operational 1d VaR  | 95%        | 1.0%           |
| Stress 1d VaR       | 99%        | 2.0%           |
| CVaR (ES) 95%       | 95%        | 1.5%           |
| CVaR (ES) 99%       | 99%        | 3.0%           |

---

### RC-11 — Tail Risk Engine

**Purpose:** The Tail Risk Engine focuses specifically on extreme risk events in the tail of the return distribution. While the VaR Engine provides measures at defined confidence levels, the Tail Risk Engine evaluates truly extreme scenarios that lie beyond normal confidence intervals.

**Responsibilities:**
1. Compute fat-tail adjusted loss estimates using extreme value theory (EVT) concepts
2. Evaluate portfolio exposure to left-tail (large loss) events
3. Monitor tail dependence: do portfolio instruments crash simultaneously?
4. Process Tail Risk Predictions from the Prediction Engine (PT-17)
5. Compute portfolio loss under 1-in-10, 1-in-50, and 1-in-100 year scenarios
6. Identify which positions are most vulnerable in tail events
7. Compute tail risk contribution by position and strategy
8. Monitor tail risk evolution over the session
9. Coordinate with Kill Switch Manager (RC-14) on tail risk thresholds
10. Archive tail risk assessments for longitudinal analysis

**Inputs:**
- Historical return distribution from Risk Archive Manager (RC-20)
- Tail Risk Predictions from Prediction Engine (PT-17)
- Portfolio state from Exposure Engine (RC-05)
- Correlation matrix from Correlation Engine (RC-06)
- VaR results from VaR Engine (RC-10)

**Outputs:**
- Tail loss estimates to Risk Threshold Manager (RC-13)
- Portfolio tail vulnerability report to Capital Protection Manager (RC-15)
- Tail risk signals to Kill Switch Manager (RC-14)
- Tail risk time series to Risk Analytics Manager (RC-21)

**Tail Risk Concepts (Definitional):**

Expected Shortfall at 99% (ES99):
- The expected loss given that the loss exceeds the 99% VaR threshold
- ES99 captures the average severity of extreme tail events
- ES99 > VaR99 always; the gap indicates the shape of the extreme tail

Conditional Tail Expectation:
- The expected value of the portfolio given it is in the worst X% of outcomes
- Provides a more complete picture of extreme loss scenarios

Left-Tail Probability Mass:
- The fraction of the return distribution below a defined loss threshold
- Fat-tailed distributions have more mass in the left tail than Gaussian distributions

**Engineering Notes:** Tail risk computation depends heavily on the quality and length of historical data. Short history periods (< 250 sessions) produce unreliable tail estimates. The Tail Risk Engine applies explicit fat-tail multipliers to compensate for potential understating of tail probabilities.

---

### RC-12 — Risk Policy Manager

**Purpose:** The Risk Policy Manager maintains the complete set of IIOS risk policies. A policy is a formal, durable rule that governs how the Risk Engine behaves. Policies are distinct from thresholds: a threshold is a number (VaR < 1%), while a policy is a rule (when VaR limit is breached, reduce position sizes by 50%).

**Responsibilities:**
1. Maintain the canonical risk policy set (version-controlled)
2. Enforce policy consistency: policies must not contradict each other
3. Provide policy lookup to all Risk Engine components
4. Track policy applicability: which policies apply to which contexts?
5. Validate that risk thresholds are set in compliance with active policies
6. Coordinate policy updates with Risk Governance Manager (RC-18)
7. Implement policy precedence: higher-priority policies override lower-priority ones
8. Maintain policy activation/deactivation history
9. Support policy override by human operators with full audit trail
10. Provide policy compliance reports for governance

**Core Policy Categories:**

| Category          | Description                                          |
|-------------------|------------------------------------------------------|
| Capital Policies  | Rules for capital preservation and allocation        |
| Exposure Policies | Rules for gross/net/concentration exposure limits    |
| Threshold Policies| Rules for when limits are breached and what happens  |
| Kill Switch Policies| Rules for Kill Switch activation and deactivation  |
| Governance Policies| Rules for human oversight and override              |
| Audit Policies    | Rules for record-keeping, retention, and review      |
| Stress Policies   | Rules for stress testing frequency and thresholds    |
| Recovery Policies | Rules for system behavior after failure or breach    |

**Policy Record Format:**

| Field            | Description                                     |
|------------------|-------------------------------------------------|
| policy_id        | POL-{CATEGORY}-{SEQ:04d}                         |
| policy_name      | Human-readable policy name                       |
| description      | Full policy description                          |
| rule_statement   | Formal rule statement                            |
| priority         | Policy priority (1 = highest)                    |
| applies_to       | Scope: position / portfolio / system             |
| activation_date  | When this policy became active                   |
| version          | Policy version                                   |
| override_allowed | Boolean: can human operators override?           |

**Failure Modes:** Policy engine failure — fall back to conservative defaults; all position changes suspended until policies are restored.

---

### RC-13 — Risk Threshold Manager

**Purpose:** The Risk Threshold Manager is the operational enforcement layer for all numerical risk limits. It continuously compares current risk measurements to their thresholds and triggers escalation actions when limits are approached or breached.

**Responsibilities:**
1. Maintain all current risk thresholds (configurable per session)
2. Continuously compare risk metrics to thresholds
3. Trigger graduated alert levels: WARNING (75% of limit), ALERT (90%), BREACH (100%), CRITICAL (110%)
4. Route breach events to the appropriate response component
5. Escalate to Kill Switch Manager when critical thresholds are breached
6. Prevent thresholds from being set outside policy-defined ranges
7. Track threshold breach history for governance reporting
8. Support dynamic threshold adjustment based on regime (tighter in volatile regimes)
9. Maintain separate thresholds for: position, portfolio, sector, VaR, drawdown, stress
10. Provide threshold utilization dashboard to Risk Health Manager (RC-22)

**Threshold Levels:**

| Level   | Trigger        | Action                                          |
|---------|----------------|-------------------------------------------------|
| INFO    | 50% of limit   | Log only; no action                              |
| WARNING | 75% of limit   | Notify operator; heightened monitoring           |
| ALERT   | 90% of limit   | Restrict new positions in breaching category     |
| BREACH  | 100% of limit  | Halt new positions; mandate reduction plan       |
| CRITICAL| 110% of limit  | Immediate escalation to Kill Switch consideration|

**Standard Threshold Reference:**

| Metric                 | WARNING   | ALERT     | BREACH    | CRITICAL   |
|------------------------|-----------|-----------|-----------|------------|
| Session Drawdown       | 1.0%      | 1.5%      | 2.0%      | 2.5%       |
| Portfolio VaR (95%)    | 0.75%     | 0.90%     | 1.0%      | 1.25%      |
| Gross Exposure         | 75% limit | 90% limit | 100% limit| 110% limit |
| Sector Concentration   | 30%       | 40%       | 50%       | 60%        |
| Single Name            | 10%       | 15%       | 20%       | 25%        |
| Strategy Concentration | 40%       | 50%       | 60%       | 70%        |

**Failure Modes:** Threshold comparison failure — immediately assume all thresholds are breached; halt new trades; escalate.

---

### RC-14 — Kill Switch Manager

**Purpose:** The Kill Switch Manager is the IIOS's unconditional emergency halt mechanism. When Kill Switch conditions are met, it immediately halts all new trade generation and initiates controlled position management. The Kill Switch is the final line of defense and its authority supersedes all other system components.

**Responsibilities:**
1. Monitor all Kill Switch trigger signals from other components
2. Evaluate Kill Switch trigger conditions continuously
3. Activate Kill Switch immediately when any trigger condition is met
4. Broadcast Kill Switch activation to all IIOS layers
5. Initiate controlled position wind-down (close existing positions per policy)
6. Prevent re-arming of the Kill Switch until human authorization
7. Log every Kill Switch evaluation (both triggered and not triggered) for audit
8. Coordinate Kill Switch deactivation after human review
9. Provide Kill Switch status to ControlTower (L17) for dashboard
10. Maintain Kill Switch activation history for performance analysis

**Kill Switch Trigger Conditions:**

| Trigger                   | Code    | Threshold            | Source              |
|---------------------------|---------|----------------------|---------------------|
| Daily Loss                | KS-T01  | Portfolio DD >= 2.0% | RC-07 Drawdown      |
| VIX Extreme               | KS-T02  | India VIX >= 45      | L2 MarketIntelligence|
| Broker Disconnection      | KS-T03  | Connect fail > 60s   | L11 Execution Engine|
| Data Feed Failure         | KS-T04  | Feed down > 30s      | Observation Engine  |
| Tail Risk Extreme         | KS-T05  | Tail event prob >30% | RC-11 Tail Risk     |
| Manual Activation         | KS-T06  | Operator command     | Human operator      |
| Stress Test Breach        | KS-T07  | Any SS stress > 3%   | RC-08 Stress Test   |
| Portfolio Limit Breach    | KS-T08  | Exposure > 110% limit| RC-17 Portfolio     |
| Technology Failure        | KS-T09  | System Monitor alert | L17 ControlTower    |
| Market Circuit Breaker    | KS-T10  | Exchange circuit hit | L2 MarketIntelligence|

**Kill Switch State Machine:**

`
ARMED (normal operating state)
  ├── Any KS trigger fires → TRIGGERED
TRIGGERED
  ├── Broadcast halt to all layers
  ├── Begin position wind-down
  └── → ACTIVE
ACTIVE (trading halted)
  ├── Human review and authorization → RESET_PENDING
  ├── Trigger condition clears + no human → ACTIVE (stays locked)
RESET_PENDING
  ├── Human confirms reset → ARMED
  └── Human cancels → ACTIVE
MANUAL_OVERRIDE (emergency human override for specific triggers only)
  ├── Override logged and audited
  └── → ARMED with override annotation
`

**Constitutional Guarantee:** The Kill Switch NEVER consults the Decision Engine, the Prediction Engine, or any scoring system before activating. It is a pure threshold comparator — if a trigger condition is met, it fires. No probability, no confidence score, no debate can prevent it.

**Failure Modes:** Kill Switch component failure — immediately assume triggered; halt all trading until component is restored. Partial failure — conservative mode: apply most restrictive interpretation of all thresholds.

---

### RC-15 — Capital Protection Manager

**Purpose:** The Capital Protection Manager implements proactive and reactive capital preservation strategies. Unlike the Kill Switch (which is a hard halt), the Capital Protection Manager uses graduated responses to protect capital while maintaining trading continuity where safe.

**Responsibilities:**
1. Monitor portfolio capital continuously against protection thresholds
2. Implement graduated response framework: reduce before halting
3. Recommend position size reductions when capital is at risk
4. Compute the maximum safe position size for any new opportunity given current exposure
5. Coordinate pre-event risk reduction (reduce before high-impact events)
6. Monitor capital recovery trajectory after adverse events
7. Enforce minimum cash reserve (capital not deployed in positions)
8. Protect against capital drain from accumulated transaction costs
9. Coordinate with CapitalRiskEngine (L6) on position sizing constraints
10. Maintain capital protection history for governance reporting

**Capital Protection Levels:**

| Level      | Condition                      | Response                                       |
|------------|--------------------------------|------------------------------------------------|
| STANDARD   | Normal operations              | Normal position sizing per risk budget          |
| ELEVATED   | Portfolio at 75% drawdown limit| Reduce all new position sizes by 25%            |
| DEFENSIVE  | Portfolio at 90% drawdown limit| Reduce all new position sizes by 50%            |
| PROTECTIVE | Portfolio at 95% drawdown limit| Reduce all new positions by 75%; begin exits    |
| HALT       | Portfolio at Kill Switch limit | No new positions; Kill Switch review            |

**Pre-Event Protection:** When the Prediction Engine signals a high-probability event (PT-16 Event Prediction, probability > 0.60), the Capital Protection Manager automatically reduces positions in event-exposed instruments by 30% before the event.

---

### RC-16 — Position Limit Manager

**Purpose:** The Position Limit Manager enforces hard limits on the size of individual positions. It is the first line of defense against single-position concentration risk.

**Responsibilities:**
1. Enforce maximum single-name position size as a percentage of portfolio NAV
2. Enforce maximum single-name position in absolute INR terms
3. Enforce maximum leverage per position (for derivatives)
4. Validate new orders against position limits before approval
5. Track current position sizes continuously
6. Alert when positions approach limits
7. Prevent orders that would breach position limits
8. Support position limit overrides with human authorization and audit trail
9. Provide position limit utilization reports
10. Coordinate with Execution Engine (L11) to block limit-breaching orders

**Standard Position Limits:**

| Limit Type               | Default     | Notes                              |
|--------------------------|-------------|------------------------------------|
| Single name max (% NAV)  | 15%         | Hard limit; override requires approval|
| Single name max (INR)    | Policy-set  | Based on account size               |
| Sector total max (% NAV) | 40%         | Hard limit                          |
| F&O position size        | 10% NAV     | More conservative for derivatives   |

---

### RC-17 — Portfolio Limit Manager

**Purpose:** The Portfolio Limit Manager enforces aggregate portfolio-level constraints. While the Position Limit Manager handles individual positions, the Portfolio Limit Manager ensures the portfolio as a whole stays within defined parameters.

**Responsibilities:**
1. Enforce maximum gross exposure (sum of all position values / NAV)
2. Enforce maximum net directional exposure (long - short / NAV)
3. Enforce maximum strategy concentration (one strategy / total strategies)
4. Enforce diversification requirements (minimum number of uncorrelated positions)
5. Validate portfolio-level correlation (prevent over-correlated portfolio)
6. Monitor portfolio VaR against portfolio VaR limit
7. Enforce minimum diversification ratio
8. Alert when portfolio concentration risk is rising
9. Provide portfolio limit dashboard to Risk Health Manager (RC-22)
10. Coordinate with Capital Protection Manager (RC-15) on portfolio-level responses

**Portfolio Limits:**

| Limit                     | Default | Enforcement             |
|---------------------------|---------|-------------------------|
| Max gross exposure (% NAV)| 100%    | Hard limit              |
| Max net exposure (% NAV)  | 80%     | Hard limit              |
| Max single strategy (%)   | 60%     | Alert at 50%            |
| Portfolio VaR 95% (% NAV) | 1.0%    | Soft limit → reduction  |
| Min diversification ratio | 0.70    | Alert when below         |
| Max avg correlation       | 0.65    | Alert when above         |

---

### RC-18 — Risk Governance Manager

**Purpose:** The Risk Governance Manager oversees the entire Risk Engine from a governance perspective: ensuring that risk processes are followed, policies are adhered to, human oversight is maintained, and the overall risk management function meets its obligations.

**Responsibilities:**
1. Monitor all Risk Engine components for policy compliance
2. Produce daily governance reports for human review
3. Track risk management decision quality over time
4. Maintain the risk governance log (all governance-relevant events)
5. Flag systematic risk management failures for investigation
6. Manage the risk policy review calendar
7. Coordinate human oversight requirements (daily review, exception reports)
8. Monitor for behavioral risks in the IIOS (RT-11)
9. Track compliance with all active risk policies
10. Provide governance certification inputs for the Risk Readiness assessment

**Governance Oversight Matrix:**

| Domain              | Frequency   | Reviewer        | Escalation Trigger          |
|---------------------|-------------|-----------------|------------------------------|
| Kill Switch log     | Daily       | Human operator  | Any unexamined activation    |
| Limit breaches      | Daily       | Human operator  | Repeated breaches            |
| VaR exceedances     | Weekly      | Risk manager    | > 5% exceedance rate         |
| Policy compliance   | Weekly      | Risk manager    | Any policy violation         |
| Strategy risk review| Monthly     | Senior review   | Drawdown > 5% over period    |

---

### RC-19 — Risk Audit Manager

**Purpose:** The Risk Audit Manager maintains the tamper-proof audit trail for all Risk Engine actions. Every risk assessment, threshold breach, Kill Switch event, and governance action is recorded with a cryptographic hash chain that prevents retroactive modification.

**Responsibilities:**
1. Record all risk events with full context (inputs, assessment, decision, outcome)
2. Maintain SHA-256 hash chain linking all audit records sequentially
3. Validate hash chain integrity continuously
4. Provide audit query interface for governance and compliance
5. Generate structured audit reports for regulatory compliance
6. Detect and alert on any hash chain corruption
7. Ensure audit records are written before the events they record are acted on
8. Maintain audit record retention per policy (minimum 7 years for financial records)
9. Support time-point queries: what was the risk state at a specific timestamp?
10. Coordinate with Risk Archive Manager (RC-20) for long-term audit storage

**Audit Record Format:**

| Field           | Description                                       |
|-----------------|---------------------------------------------------|
| audit_id        | AUD-RSK-{YYYYMMDD}-{SEQ:08d}                       |
| timestamp       | UTC nanosecond timestamp                           |
| event_type      | RISK_DETECTED / THRESHOLD_BREACH / KS_TRIGGER etc  |
| component_id    | RC-NN identifier of component generating event     |
| inputs_hash     | SHA-256 hash of input data                         |
| assessment_hash | SHA-256 hash of risk assessment result             |
| action_taken    | Description of action taken in response            |
| prior_hash      | Hash of immediately preceding audit record         |
| chain_hash      | SHA-256(prior_hash + audit_id + event_hash)        |

---

### RC-20 — Risk Archive Manager

**Purpose:** The Risk Archive Manager provides durable, long-term storage for all risk records, ensuring historical risk data is available for backtesting, calibration, governance review, and regulatory compliance.

**Responsibilities:**
1. Archive risk records at end of each session
2. Maintain risk time series for historical analysis
3. Provide historical risk data to VaR Engine, Stress Testing Engine, and Tail Risk Engine
4. Implement retention policies (session data: 1 year; summary data: 7 years)
5. Manage storage efficiency through compression and summarization
6. Support point-in-time queries for forensic analysis
7. Provide data for Learning Engine risk model calibration
8. Ensure archive integrity through periodic validation
9. Support regulatory reporting data extracts
10. Coordinate data lifecycle: active → archive → purge (per policy)

---

### RC-21 — Risk Analytics Manager

**Purpose:** The Risk Analytics Manager produces analytical views of risk data for understanding, calibration improvement, and governance. It transforms raw risk records into structured reports and trend analyses.

**Responsibilities:**
1. Produce session risk summary reports
2. Compute rolling risk statistics (7-day, 30-day, 90-day)
3. Identify risk trends: is portfolio risk increasing or decreasing over time?
4. Compute risk model accuracy: how well did VaR predict actual losses?
5. Track threshold breach frequency and patterns
6. Produce strategy-level risk attribution reports
7. Compute risk-adjusted performance metrics (Sharpe, Sortino, Calmar)
8. Support ad-hoc risk analysis queries from governance users
9. Provide risk data for ControlTower (L17) dashboard
10. Produce the Risk Performance Report for ResearchLab (L15) strategy evaluation

---

### RC-22 — Risk Health Manager

**Purpose:** The Risk Health Manager monitors the health of the Risk Engine itself — ensuring that all components are operating correctly, data quality is maintained, and the overall risk system is ready to fulfill its capital protection mandate.

**Responsibilities:**
1. Monitor all 22 Risk Engine components for operational health
2. Compute overall Risk Engine Health Score (REHS) from component health scores
3. Report REHS to ControlTower (L17) for dashboard
4. Detect component degradation before component failure
5. Initiate component recovery sequences
6. Maintain readiness certification: the Risk Engine is only READY when REHS >= threshold
7. Track data quality for all Risk Engine inputs
8. Monitor processing latency for all components vs defined SLAs
9. Coordinate with ControlTower event bus for risk system health events
10. Provide risk system health history for capacity planning

**REHS Thresholds:**

| REHS Level    | Range       | Trading Implication                    |
|---------------|-------------|----------------------------------------|
| OPTIMAL       | 0.90 - 1.00 | Full trading capability                |
| NOMINAL       | 0.75 - 0.89 | Full trading; monitoring elevated      |
| DEGRADED      | 0.55 - 0.74 | Reduced position sizes; alert operator |
| CRITICAL      | 0.30 - 0.54 | New positions halted; recovery required|
| FAILED        | 0.00 - 0.29 | Kill Switch forced active              |

---

## PART IV — RISK LIFECYCLE

### 4.0 Lifecycle Design Philosophy

The Risk Lifecycle is the complete sequence of stages that a risk signal traverses from initial detection through final archival. Unlike a trade lifecycle (which has a clear start and end), a risk record may be active for a full trading session, may transition through multiple states, and may trigger escalation actions at multiple points.

The lifecycle is designed around three principles:
1. **No risk is ignored:** Every detected signal is classified and assessed, even if assessed as negligible.
2. **Progressive escalation:** Responses to risk are proportional to severity, with escalation paths to more severe responses as severity increases.
3. **Complete auditability:** Every state transition is logged with full context, timestamp, and responsible component.

---

### 4.1 Risk Lifecycle Stages

**Stage 1 — Risk Detection (RLS-01)**

*Trigger:* New signal received by Risk Analyzer (RC-03)
*Actions:* Signal ingested; preliminary classification attempted; risk record stub created in Risk Registry
*Duration:* Target < 50ms
*Output:* Risk stub record with initial classification
*Failure:* Signal queued; retry with exponential backoff; alert if stuck

**Stage 2 — Risk Classification (RLS-02)**

*Trigger:* Risk stub moves from DETECTED to CLASSIFYING state
*Actions:* Full risk type classification against Risk Catalog (RC-02); multi-classification if applicable; causal chain construction
*Duration:* Target < 100ms
*Output:* Classified risk record with RT-NN codes
*Failure:* Fall back to "UNCLASSIFIED" category; human review queue

**Stage 3 — Risk Measurement (RLS-03)**

*Trigger:* Classified risk record enters MEASURING state
*Actions:* Quantitative measurement of risk magnitude using type-specific metrics; regime adjustment; uncertainty quantification
*Duration:* Target < 200ms (may be longer for complex Monte Carlo computations)
*Output:* Risk record with quantitative severity score
*Failure:* Conservative default score applied (assumes maximum severity in category); escalation alert

**Stage 4 — Exposure Calculation (RLS-04)**

*Trigger:* Measured risk record enters EXPOSURE state
*Actions:* Exposure Engine (RC-05) computes financial exposure at risk; component exposures by position, sector, strategy
*Duration:* Target < 150ms
*Output:* Exposure vector appended to risk record
*Failure:* Use cached exposure; flag as potentially stale; alert

**Stage 5 — Validation (RLS-05)**

*Trigger:* Risk record with exposure enters VALIDATING state
*Actions:* Five validation checks:
  V-01 Schema validation: risk record fields are complete and well-formed
  V-02 Score range: severity score in [0.0, 1.0]; exposure values non-negative
  V-03 Consistency check: risk type matches input signal type
  V-04 Data freshness: all input data used is within accepted staleness tolerance
  V-05 Audit linkage: audit trail created and linked before proceeding

*Output:* VALIDATED or INVALID risk record
*Failure:* Invalid records are quarantined; human review queue; error logged

**Stage 6 — Threshold Evaluation (RLS-06)**

*Trigger:* Validated risk record enters THRESHOLD_EVAL state
*Actions:* Risk Threshold Manager (RC-13) compares all measured metrics to thresholds; determines breach level (INFO / WARNING / ALERT / BREACH / CRITICAL); routes to appropriate response
*Duration:* Target < 50ms
*Output:* Risk record annotated with breach level; response actions initiated

**Stage 7 — Mitigation (RLS-07)**

*Trigger:* Risk record enters MITIGATION state when response action required
*Actions:* Graduated response based on breach level: position size reduction recommendation; new position restrictions; hedging recommendations; escalation to Kill Switch
*Duration:* Variable; depends on response type
*Output:* Mitigation action record; notification to relevant layers

**Stage 8 — Approval (RLS-08)**

*Trigger:* Mitigation actions enter PENDING_APPROVAL state for human-required actions
*Actions:* Human operator notified (Telegram); operator approves, modifies, or rejects mitigation plan; all decisions logged
*Duration:* Variable; human response time
*Output:* Approved mitigation plan or rejection with rationale

**Stage 9 — Continuous Monitoring (RLS-09)**

*Trigger:* Active risk record enters MONITORING state after initial assessment
*Actions:* Periodic re-assessment at monitoring interval; threshold re-check on each update; trend detection; severity trajectory monitoring
*Monitoring intervals:*
  - Kill Switch risks: every 5 seconds
  - Market risk: every 30 seconds
  - Portfolio risk: every 60 seconds
  - Structural risks (model, behavioral): every session
*Output:* Continuous updates to risk record; escalation if severity rises

**Stage 10 — Escalation (RLS-10)**

*Trigger:* Risk severity rises above escalation threshold during monitoring
*Actions:* Escalation path activated based on risk type and severity; Kill Switch Manager notified if applicable; human operator notified; position management initiated
*Output:* Escalation record; downstream actions

**Stage 11 — Recovery (RLS-11)**

*Trigger:* Risk condition has been mitigated or resolved
*Actions:* Risk record severity updated downward; restrictions lifted if applicable; recovery plan implemented; monitoring continues at reduced frequency
*Output:* Recovery record; restriction relief notifications

**Stage 12 — Archive (RLS-12)**

*Trigger:* Risk record is no longer active (session end, or risk fully resolved)
*Actions:* Risk record finalized with complete history; written to Risk Archive Manager (RC-20); hash chain finalized; summary statistics computed
*Output:* Archived risk record; session risk summary

**Stage 13 — Retirement (RLS-13)**

*Trigger:* Archived risk record reaches end of active retention period
*Actions:* Risk record summarized; detailed record purged per retention policy; summary record retained for long-term statistics
*Output:* Summary record in long-term archive

---

### 4.2 Risk Lifecycle State Machine

`
RISK LIFECYCLE STATE MACHINE
════════════════════════════

SIGNAL_ARRIVED
  │
  ▼
DETECTED ──(classification failure)──→ UNCLASSIFIED_REVIEW
  │
  ▼
CLASSIFYING
  │
  ▼
MEASURING ──(measurement failure)──→ CONSERVATIVE_SCORED
  │
  ▼
EXPOSURE_CALC
  │
  ▼
VALIDATING ──(validation failure)──→ QUARANTINED
  │
  ▼
THRESHOLD_EVAL
  │                │
  │                ▼
  │            NO_ACTION ──→ MONITORING
  │
  ▼
MITIGATION_REQUIRED
  │
  ├──(auto-mitigable)──→ MITIGATING ──→ MONITORING
  │
  └──(human required)──→ PENDING_APPROVAL
                           │            │
                           │            ▼
                           │         APPROVED ──→ MITIGATING ──→ MONITORING
                           │
                           ▼
                        REJECTED ──→ ESCALATION ──→ KILL_SWITCH_REVIEW
                                                          │
                                              KS_TRIGGERED or KS_CLEARED

MONITORING ──(severity rises)──→ THRESHOLD_EVAL
MONITORING ──(session end / resolved)──→ ARCHIVING ──→ ARCHIVED
ARCHIVED ──(retention expiry)──→ RETIRED
`

---

### 4.3 Risk Record Status Reference

| Status               | Description                                        |
|----------------------|----------------------------------------------------|
| SIGNAL_ARRIVED       | Raw signal received; not yet processed             |
| DETECTED             | Signal processed; initial detection recorded       |
| CLASSIFYING          | Risk type classification in progress               |
| UNCLASSIFIED         | Classification failed; queued for review           |
| MEASURING            | Quantitative measurement in progress               |
| CONSERVATIVE_SCORED  | Measurement failed; conservative defaults applied  |
| EXPOSURE_CALC        | Exposure calculation in progress                   |
| VALIDATING           | Validation checks in progress                      |
| QUARANTINED          | Validation failed; isolated for human review       |
| THRESHOLD_EVAL       | Comparing metrics to thresholds                    |
| NO_ACTION            | Thresholds not breached; monitoring only           |
| MITIGATION_REQUIRED  | Threshold breach requires action                   |
| MITIGATING           | Mitigation actions in progress                     |
| PENDING_APPROVAL     | Waiting for human operator approval                |
| APPROVED             | Mitigation plan approved                           |
| REJECTED             | Mitigation rejected; escalation initiated          |
| MONITORING           | Active risk under continuous monitoring            |
| ESCALATION           | Risk severity has increased; higher-level response |
| KILL_SWITCH_REVIEW   | Kill Switch consideration activated                |
| RESOLVED             | Risk condition has been mitigated or ended         |
| ARCHIVING            | Being written to archive                           |
| ARCHIVED             | Permanently recorded in archive                    |
| RETIRED              | Archived record summary retained; detail purged    |

---

### 4.4 Lifecycle Timing Reference

| Stage               | Target Duration | SLA Hard Limit | Action if Exceeded             |
|---------------------|-----------------|----------------|--------------------------------|
| Detection           | < 50ms          | 200ms          | Alert; dequeue; prioritize     |
| Classification      | < 100ms         | 500ms          | Conservative fallback          |
| Measurement         | < 200ms         | 1,000ms        | Conservative score applied     |
| Exposure Calc       | < 150ms         | 750ms          | Cached exposure used           |
| Validation          | < 50ms          | 200ms          | Auto-quarantine                |
| Threshold Eval      | < 50ms          | 100ms          | Conservative breach assumed    |
| Kill Switch (total) | < 500ms         | 1,000ms        | KS forced active               |

---

## PART V — RISK SERVICES

### 5.0 Service Architecture Overview

Risk Services are the named, purpose-bounded computation units that implement the Risk Engine's functional capabilities. Services are distinct from components: a component is a long-lived architectural unit with state; a service is a callable function that performs a specific risk computation.

Each service is independently invocable, idempotent, and side-effect-free (services compute and return results; they do not modify registry state directly — that is a component responsibility).

Services are organized into 14 service units: RS-01 through RS-14.

---

### RS-01 — Risk Analysis Service

**Purpose:** Exposes the Risk Analyzer (RC-03) capabilities as a callable service. Accepts a risk context (position, event, market state) and returns a classified risk assessment.

**Interface:** receive_risk_context(context) → RiskAssessment

**Primary consumers:** Decision Engine (L10) pre-trade checks; Execution Engine (L11) order validation.

**Latency target:** < 200ms end-to-end for pre-trade risk assessment.

---

### RS-02 — Exposure Service

**Purpose:** Provides current exposure data for any combination of positions, strategies, or sectors. Used by position sizing (L6) and the Decision Engine to understand current exposure state before accepting new opportunities.

**Interface:** get_exposure(scope: ALL / POSITION / SECTOR / STRATEGY) → ExposureReport

---

### RS-03 — Correlation Service

**Purpose:** Provides correlation data and correlation-adjusted risk measures. Used by the VaR Engine, Portfolio Limit Manager, and StrategyLab to understand the diversification state of the portfolio.

**Interface:** get_correlation(instrument_list) → CorrelationMatrix; get_diversification_ratio() → float

---

### RS-04 — Stress Testing Service

**Purpose:** Runs stress tests on demand or on schedule. Returns portfolio impact for all or a specified subset of stress scenarios.

**Interface:** run_stress_test(scenario_ids, portfolio_snapshot) → StressTestReport

**Latency target:** Full 14-scenario suite < 2 seconds.

---

### RS-05 — Scenario Service

**Purpose:** Manages risk scenario lifecycle: creation, probability update, validation, and archival. Integrates with the Prediction Engine's scenario outputs.

**Interface:** create_scenario(definition) → ScenarioRecord; update_probability(scenario_id, new_probability) → None; get_active_scenarios() → List[ScenarioRecord]

---

### RS-06 — VaR Service

**Purpose:** Computes Value at Risk and Conditional VaR for the current portfolio or for a proposed position set.

**Interface:** compute_var(confidence, horizon_days, portfolio_snapshot) → VaRResult; compute_incremental_var(new_position, confidence) → IncrementalVaR

---

### RS-07 — Threshold Service

**Purpose:** Provides threshold query and update capabilities. Allows authorized components to check threshold utilization and governance to update thresholds within policy limits.

**Interface:** check_threshold(metric, value) → ThresholdResult; get_utilization() → ThresholdUtilizationReport

---

### RS-08 — Kill Switch Service

**Purpose:** Provides Kill Switch status and manual trigger capabilities. This is the service-layer interface to the Kill Switch Manager (RC-14).

**Interface:** get_status() → KillSwitchStatus; evaluate_triggers() → TriggerEvaluation; manual_trigger(reason) → KillSwitchActivation; manual_clear(authorization) → KillSwitchClearance

---

### RS-09 — Capital Protection Service

**Purpose:** Computes capital protection recommendations for a given portfolio state and proposed action.

**Interface:** get_protection_level() → ProtectionLevel; compute_safe_position_size(opportunity, current_exposure) → SafePositionSize

---

### RS-10 — Governance Service

**Purpose:** Provides risk governance reporting and compliance checking. Used by ControlTower (L17) for dashboard data and human operators for oversight.

**Interface:** get_governance_report(session_date) → GovernanceReport; check_policy_compliance() → ComplianceReport

---

### RS-11 — Monitoring Service

**Purpose:** Provides real-time risk monitoring data stream. Streams continuous risk metrics to ControlTower (L17) and any authorized subscriber.

**Interface:** subscribe_risk_stream(subscriber_id, filters) → RiskEventStream; get_risk_snapshot() → RiskSnapshot

---

### RS-12 — Audit Service

**Purpose:** Provides audit record query and report generation capabilities.

**Interface:** query_audit(start_time, end_time, event_type) → List[AuditRecord]; validate_chain_integrity() → ChainIntegrityReport; generate_audit_report(period) → AuditReport

---

### RS-13 — Archive Service

**Purpose:** Provides access to historical risk data for calibration and analysis.

**Interface:** get_historical_risk(symbol, start_date, end_date) → List[RiskRecord]; get_session_risk_summary(session_date) → SessionRiskSummary; get_drawdown_history(strategy_id) → DrawdownHistory

---

### RS-14 — Health Service

**Purpose:** Provides Risk Engine health status and readiness certification.

**Interface:** get_health_status() → REHSReport; get_readiness() → ReadinessReport; certify_ready() → ReadinessCertification

---

## PART VI — RISK PROCESSING PIPELINES

### 6.0 Pipeline Design Philosophy

Risk Processing Pipelines are the structured, sequential processing chains that transform raw inputs into risk outputs. Each pipeline has a defined trigger, a sequence of processing stages, and defined outputs. Pipelines provide the architectural context for understanding how Risk Engine components collaborate to produce specific results.

Ten pipelines are defined: RP-01 through RP-10.

---

### RP-01 — Decision-to-Risk Pipeline

**Purpose:** Evaluates the risk of a proposed trade decision before it is approved for execution.

**Trigger:** Decision Engine (L10) proposes a trade opportunity.

**Flow Diagram:**

`
RP-01: DECISION-TO-RISK PIPELINE
══════════════════════════════════

[L10 Decision Engine]
  │ Proposed trade: symbol, direction, size, strategy
  ▼
[RC-03 Risk Analyzer]
  │ Classify risks: RT-01 Market, RT-03 Position, RT-07 Execution, RT-09 Prediction
  │ Risk context: regime, sector, correlation, volatility
  ▼
[RC-04 Risk Scoring Engine]
  │ Compute severity for each risk type
  │ Aggregate to Trade Risk Score (TRS)
  ▼
[RC-05 Exposure Engine]
  │ Check: does this trade increase exposure beyond limits?
  │ Compute incremental gross/net/sector exposure
  ▼
[RC-10 VaR Engine]
  │ Compute incremental VaR: does this trade increase portfolio VaR?
  │ Check incremental VaR against VaR limit headroom
  ▼
[RC-13 Risk Threshold Manager]
  │ Evaluate all applicable thresholds
  │ Determine: APPROVED / REDUCED / REJECTED
  ▼
[RC-15 Capital Protection Manager]
  │ Apply protection level: is portfolio in ELEVATED/DEFENSIVE mode?
  │ Apply any size reduction from protection level
  ▼
[RC-19 Risk Audit Manager]
  │ Record complete assessment for audit trail
  ▼
[Decision Output]
  ├── APPROVED: trade proceeds at proposed size
  ├── REDUCED: trade proceeds at reduced size (with reason)
  └── REJECTED: trade blocked (with reason and threshold breach detail)
`

**Latency SLA:** < 500ms end-to-end (includes all sub-computations). Decisions waiting > 500ms receive a TIMEOUT_CONSERVATIVE result — approved only if all checked metrics were below WARNING level.

**Failure Handling:** Any component failure in the pipeline triggers a CONSERVATIVE_REJECT — the trade is blocked until the component recovers. It is always safer to miss a trade than to take an un-assessed trade.

---

### RP-02 — Execution Risk Pipeline

**Purpose:** Monitors execution quality in real-time and identifies execution risk events.

**Trigger:** New execution event from Execution Engine (L11): order submitted, filled, partially filled, rejected, or cancelled.

**Flow Diagram:**

`
RP-02: EXECUTION RISK PIPELINE
════════════════════════════════

[L11 Execution Engine]
  │ Execution event: symbol, order, fill, EQS
  ▼
[RC-03 Risk Analyzer]
  │ Classify: RT-07 Execution Risk, RT-06 Liquidity Risk
  │ Compare fill price to signal price: slippage?
  │ Compare fill size to intended size: partial fill?
  ▼
[RC-04 Risk Scoring Engine]
  │ Score execution risk severity
  │ Classify: NORMAL / ELEVATED / POOR / FAILED
  ▼
[RC-05 Exposure Engine]
  │ Update live exposure post-fill
  │ Compute current gross/net exposure
  ▼
[RC-13 Risk Threshold Manager]
  │ Check: does post-fill state breach any threshold?
  ▼
[RC-07 Drawdown Monitor]
  │ Update session P&L with realized fill
  │ Check: is session drawdown affected?
  ▼
[RC-19 Risk Audit Manager]
  │ Record execution risk assessment
  ▼
[Output: Execution Risk Record]
  ├── If EQS consistently poor → recommend reduced sizes
  └── If threshold breached → escalate
`

---

### RP-03 — Portfolio Monitoring Pipeline

**Purpose:** Continuously monitors the aggregate portfolio risk state throughout the trading session.

**Trigger:** Periodic timer (every 60 seconds) and on any position change.

**Flow Diagram:**

`
RP-03: PORTFOLIO MONITORING PIPELINE
══════════════════════════════════════

[Timer / Position Change Trigger]
  ▼
[RC-05 Exposure Engine]
  │ Compute current gross, net, sector exposures
  ▼
[RC-06 Correlation Engine]
  │ Update rolling correlation matrix
  │ Detect correlation regime changes
  ▼
[RC-10 VaR Engine]
  │ Recompute portfolio VaR with current positions and correlation
  │ Compute diversification ratio
  ▼
[RC-04 Risk Scoring Engine]
  │ Compute portfolio composite Risk Score
  │ Compute RQS (Risk Quality Score)
  ▼
[RC-17 Portfolio Limit Manager]
  │ Check: gross/net exposure vs limits
  │ Check: VaR vs portfolio VaR limit
  │ Check: concentration vs limits
  ▼
[RC-07 Drawdown Monitor]
  │ Check: session P&L vs drawdown thresholds
  ▼
[RC-13 Risk Threshold Manager]
  │ Aggregate threshold status
  │ Determine overall portfolio risk level
  ▼
[RC-22 Risk Health Manager]
  │ Update REHS with current monitoring results
  ▼
[ControlTower L17]
  │ Push portfolio risk dashboard update
  └── Risk snapshot broadcast to event bus
`

---

### RP-04 — Exposure Pipeline

**Purpose:** Dedicated pipeline for exposure computation and enforcement on any new order before submission.

**Trigger:** New order request from Execution Engine before submission to broker.

**Flow Diagram:**

`
RP-04: EXPOSURE PIPELINE
═════════════════════════

[Order Request]
  │ Symbol, direction, size, strategy
  ▼
[RC-05 Exposure Engine]
  │ Compute current exposure vectors
  │ Simulate: what is exposure AFTER this order?
  ▼
[RC-16 Position Limit Manager]
  │ Check: post-trade single-name exposure vs position limit
  ▼
[RC-17 Portfolio Limit Manager]
  │ Check: post-trade gross/net exposure vs portfolio limits
  │ Check: sector exposure post-trade vs sector limit
  ▼
[RC-15 Capital Protection Manager]
  │ Apply protection level to sizing
  ▼
[Result]
  ├── ORDER_APPROVED: exposure limits not breached
  ├── ORDER_REDUCED: approved with smaller size
  └── ORDER_BLOCKED: would breach hard exposure limit
`

---

### RP-05 — Stress Testing Pipeline

**Purpose:** Runs stress tests on the current portfolio on a scheduled basis and on demand.

**Trigger:** Session start; every 90 minutes during session; any significant market event.

**Flow Diagram:**

`
RP-05: STRESS TESTING PIPELINE
════════════════════════════════

[Trigger: Timer / Market Event]
  ▼
[RC-09 Scenario Engine]
  │ Retrieve applicable scenarios from catalogue
  │ 14 standard + any custom active scenarios
  ▼
[RC-08 Stress Testing Engine]
  │ For each scenario:
  │   Apply scenario parameters to current portfolio
  │   Compute P&L impact per position
  │   Aggregate to portfolio impact
  │   Classify: SAFE / WARNING / BREACH / CRITICAL
  ▼
[RC-11 Tail Risk Engine]
  │ Compute tail loss estimate based on stress results
  │ Identify most vulnerable positions
  ▼
[RC-13 Risk Threshold Manager]
  │ Check: does any scenario breach stress loss threshold?
  ▼
[RC-15 Capital Protection Manager]
  │ If breach: compute required position reductions
  ▼
[RC-14 Kill Switch Manager]
  │ If any scenario shows loss > KS threshold → KS evaluation
  ▼
[RC-20 Risk Archive Manager]
  │ Archive stress test results
  ▼
[Output: Stress Test Report]
  └── Published to ControlTower dashboard
`

---

### RP-06 — Scenario Pipeline

**Purpose:** Manages the full lifecycle of risk scenarios from creation through outcome validation.

**Trigger:** New scenario created by Scenario Engine (from Prediction Engine inputs) or scheduled scenario review.

**Flow Diagram:**

`
RP-06: SCENARIO PIPELINE
══════════════════════════

[Prediction Engine: PT-15 Scenario Prediction]
  │ New scenario definition with probability estimate
  ▼
[RC-09 Scenario Engine]
  │ Validate scenario: is it internally consistent?
  │ Check: does probability assignment create coverage gaps?
  ▼
[RC-08 Stress Testing Engine]
  │ Compute portfolio impact of new scenario
  ▼
[RC-04 Risk Scoring Engine]
  │ Compute probability-weighted risk contribution
  ▼
[RC-01 Risk Registry]
  │ Register active scenario
  ▼
[Continuous Monitoring Loop]
  │ Every 30 minutes: update scenario probabilities from Prediction Engine
  │ Check: has scenario been invalidated by new evidence?
  ▼
[Scenario Outcome Check (post-session)]
  │ Did the scenario materialize? Record outcome.
  ▼
[RC-20 Risk Archive Manager]
  └── Archive scenario with outcome for calibration
`

---

### RP-07 — Kill Switch Pipeline

**Purpose:** The Kill Switch Pipeline implements the fastest possible path from trigger condition to trading halt.

**Trigger:** Any Kill Switch trigger condition (KS-T01 through KS-T10).

**Design Principle:** This pipeline is intentionally simple. Complex processing slows down the Kill Switch. Simplicity is a safety feature.

**Flow Diagram:**

`
RP-07: KILL SWITCH PIPELINE
═════════════════════════════

[Trigger Signal]
  │ Any of: KS-T01 to KS-T10
  ▼
[RC-14 Kill Switch Manager]
  │ EVALUATE: is this a valid trigger? (< 50ms)
  │ YES → ACTIVATE
  │ NO → log evaluation; continue
  ▼
[If ACTIVATED]
  │ Broadcast: KILL_SWITCH_ACTIVE to ALL IIOS layers
  │ Broadcast: HALT_ALL_NEW_TRADES
  ▼
[All Layers Receive Halt Signal]
  │ L10 Decision Engine: reject all pending proposals
  │ L11 Execution Engine: cancel all pending orders
  │ L6/L7 Risk layers: no new position approvals
  ▼
[RC-15 Capital Protection Manager]
  │ Initiate position wind-down if policy requires
  │ (depends on trigger type — some triggers preserve positions)
  ▼
[RC-19 Risk Audit Manager]
  │ Record Kill Switch activation with full context
  ▼
[L17 ControlTower]
  │ Dashboard: RED status
  │ Telegram alert to operator
  ▼
[Human Operator]
  │ Reviews trigger; decides: CLEAR or MAINTAIN
  ▼
[RC-14 Kill Switch Manager]
  └── CLEARED: → ARMED state; trading resumes
      MAINTAINED: → ACTIVE; await further review
`

**Total pipeline latency (trigger to halt broadcast): target < 200ms.**

---

### RP-08 — Governance Pipeline

**Purpose:** Implements the governance review and compliance checking cycle.

**Trigger:** Session start; session end; daily governance timer; governance-relevant event.

**Flow Diagram:**

`
RP-08: GOVERNANCE PIPELINE
═══════════════════════════

[Governance Trigger]
  ▼
[RC-18 Risk Governance Manager]
  │ Collect all events from session requiring governance attention:
  │   - Limit breaches
  │   - Kill Switch events
  │   - Policy exceptions
  │   - Human overrides
  ▼
[RC-12 Risk Policy Manager]
  │ Audit: are all active policies being complied with?
  │ Flag policy violations
  ▼
[RC-10 VaR Engine]
  │ VaR backtest: did predicted VaR hold?
  │ Compute exceedance rate
  ▼
[RC-13 Risk Threshold Manager]
  │ Threshold review: are thresholds appropriate for current regime?
  ▼
[RC-19 Risk Audit Manager]
  │ Generate governance report from audit records
  ▼
[RC-21 Risk Analytics Manager]
  │ Compute governance metrics: breach frequency, exceedance rate
  ▼
[Human Review Queue]
  │ Governance report delivered via Telegram / Dashboard
  └── Human operator reviews and acknowledges
`

---

### RP-09 — Audit Pipeline

**Purpose:** Produces complete, verified audit records for all risk management actions.

**Trigger:** Every significant Risk Engine event; end-of-session audit closure.

**Flow Diagram:**

`
RP-09: AUDIT PIPELINE
══════════════════════

[Risk Engine Event]
  │ Any state change, threshold breach, KS event, governance action
  ▼
[RC-19 Risk Audit Manager]
  │ Create audit record with full context
  │ Compute SHA-256 hash of record
  │ Retrieve prior record hash
  │ Compute chain_hash = SHA-256(prior_hash + record)
  │ Append to audit chain
  ▼
[Hash Chain Validation]
  │ Verify chain is intact (periodic; every 100 records)
  ▼
[RC-20 Risk Archive Manager]
  │ Write audit records to persistent storage
  ▼
[End-of-Session Audit Closure]
  │ Generate session audit summary
  │ Produce hash chain integrity certificate
  └── Archive complete session audit bundle
`

---

### RP-10 — Recovery Pipeline

**Purpose:** Implements controlled recovery from Risk Engine component failures.

**Trigger:** Component health failure detected by RC-22 Risk Health Manager.

**Flow Diagram:**

`
RP-10: RECOVERY PIPELINE
═════════════════════════

[RC-22 Risk Health Manager detects failure]
  │ Component: {RC-NN} Health Score: {score}
  ▼
[Classify failure: PARTIAL / TOTAL / DATA_LOSS]
  ▼
[PARTIAL failure]
  │ Continue with degraded mode
  │ Apply conservative fallbacks for failed component
  │ Alert operator; begin recovery
  │
[TOTAL failure]
  │ Activate safe mode: no new trades; existing positions maintained
  │ Initiate component restart
  │ Alert operator immediately
  │
[DATA_LOSS failure]
  │ Recover from last checkpoint
  │ Replay events since checkpoint
  │ Validate recovered state
  ▼
[Component Restart Sequence]
  │ 1. Validate environment
  │ 2. Load last known good state
  │ 3. Replay event buffer
  │ 4. Verify component health
  │ 5. Re-integrate into pipeline
  ▼
[RC-22 Risk Health Manager]
  │ Validate recovery
  │ Update REHS
  ▼
[Resume normal operations if REHS >= threshold]
  └── Alert operator: recovery complete
`

---

## PART VII — RISK QUALITY FRAMEWORK

### 7.0 Quality Framework Purpose

The Risk Quality Framework defines the standards by which the Risk Engine evaluates its own performance. A risk management system must be more than just operational — it must be accurate, timely, comprehensive, consistent, and effective. The framework provides 12 quality dimensions that together constitute the Risk Quality Score (RQS).

Quality monitoring is not optional — the IIOS cannot trust a risk assessment produced by a degraded risk system. The RQS gates the risk system's contribution to the overall IIOS.

---

### 7.1 Risk Quality Dimensions

**RQD-01 — Accuracy (Weight: 0.20)**

*Definition:* The degree to which risk measurements correctly reflect the actual risk present in the portfolio.

*Measurement:* Post-session comparison of predicted loss metrics to actual outcomes; VaR exceedance rate (target: close to 5% at 95% confidence); stress test accuracy (did stressed scenarios predict actual stress behavior?).

*Formula:* Accuracy = 1 - (absolute_prediction_error / expected_prediction_error)

*Minimum acceptable:* 0.65 (historical VaR exceedance rate must be between 3% and 8%)

*Degradation triggers:* VaR consistently violated; stress test consistently underestimates; risk scores don't correlate with actual adverse outcomes.

---

**RQD-02 — Sensitivity (Weight: 0.15)**

*Definition:* The degree to which the Risk Engine detects risk conditions early enough to enable effective mitigation. High sensitivity means the Risk Engine responds before thresholds are breached, not after.

*Measurement:* Early warning lead time (how many seconds before a threshold breach was a WARNING issued?); proportion of Kill Switch events preceded by WARNING state.

*Target:* 100% of Kill Switch activations should be preceded by at least one WARNING or ALERT state.

*Degradation triggers:* Threshold breaches with no prior warning; Kill Switch activations without prior ALERT state.

---

**RQD-03 — Timeliness (Weight: 0.12)**

*Definition:* The degree to which risk assessments are produced within required time constraints. Stale risk assessments are not risk assessments — they are historical records.

*Measurement:* Proportion of risk assessments completed within SLA; average pipeline latency vs target; maximum observed latency.

*SLA target:* 99% of pre-trade risk assessments completed within 500ms.

*Degradation triggers:* Consistent SLA violations; risk assessments completing after the window where they could influence decisions.

---

**RQD-04 — Coverage (Weight: 0.10)**

*Definition:* The degree to which all applicable risk types are assessed for every portfolio action. A risk assessment that misses the most applicable risk type has failed.

*Measurement:* Proportion of trades for which all applicable RT codes were evaluated; risk type coverage ratio (evaluated types / applicable types).

*Target:* 100% coverage for RT-01, RT-03, RT-07 on every trade. Full 26-type assessment on every significant portfolio action.

*Degradation triggers:* Systematic omission of any RT code; classification failures resulting in "UNCLASSIFIED" records.

---

**RQD-05 — Consistency (Weight: 0.10)**

*Definition:* The degree to which the Risk Engine produces consistent risk assessments for similar inputs. Inconsistency in risk assessment — giving different answers to essentially identical questions — indicates model instability.

*Measurement:* Stability of risk scores across sessions with similar market conditions; intraday variability of risk scores for unchanged positions.

*Target:* Risk score variance for unchanged positions < 5% per hour.

*Degradation triggers:* Large risk score swings without corresponding market changes; inconsistent treatment of similar instruments.

---

**RQD-06 — Robustness (Weight: 0.08)**

*Definition:* The degree to which the Risk Engine maintains its quality under adverse conditions: data gaps, system stress, component failures, and extreme market volatility.

*Measurement:* Quality degradation under simulated stress; behavior during component failures; quality during high-volatility market sessions.

*Target:* RQS should not fall below 0.55 even under single-component failure scenarios.

*Degradation triggers:* Catastrophic quality collapse on component failure; inability to maintain conservative defaults under stress.

---

**RQD-07 — Reliability (Weight: 0.08)**

*Definition:* The degree to which the Risk Engine consistently operates without failure. Reliability is measured over time: uptime, mean-time-between-failures, mean-time-to-recovery.

*Measurement:* Component availability during session; number of component failures per session; recovery time from failure.

*Target:* 99.9% availability for Tier-1 components (Kill Switch, Drawdown Monitor); 99% for all others.

*Degradation triggers:* Repeated component failures; slow recovery from failure; cascading failures.

---

**RQD-08 — Explainability (Weight: 0.05)**

*Definition:* The degree to which risk assessments can be explained in plain language with reference to specific inputs and rules. An unexplainable risk rejection damages trust in the system.

*Measurement:* Proportion of risk decisions for which a complete explanation chain (input → risk type → measurement → threshold → decision) exists.

*Target:* 100% of REJECTED and REDUCED decisions have complete explanation chains.

---

**RQD-09 — Traceability (Weight: 0.05)**

*Definition:* The degree to which every risk assessment can be traced back to its inputs, through its computations, to its outputs. Traceability supports audit, debugging, and governance.

*Measurement:* Proportion of risk records with complete audit chains; proportion of decisions reproducible from archived inputs.

*Target:* 100% of risk records have traceable audit chains.

---

**RQD-10 — Governance (Weight: 0.03)**

*Definition:* The degree to which the Risk Engine's operation conforms to its defined governance framework: policies, procedures, review requirements, and human oversight.

*Measurement:* Policy compliance rate; proportion of sessions with completed governance review; human oversight completion rate.

---

**RQD-11 — Auditability (Weight: 0.02)**

*Definition:* The degree to which the audit trail is complete, intact, and tamper-proof. The hash chain must be valid; all events must be recorded; no gaps.

*Measurement:* Hash chain integrity score; audit record completeness; gap rate (events with no audit record).

---

**RQD-12 — Capital Protection Effectiveness (Weight: 0.02)**

*Definition:* The degree to which the Risk Engine actually prevents capital loss. This is the ultimate outcome metric — did the risk management system achieve its primary goal?

*Measurement:* Proportion of adverse events that were detected before they caused significant loss; proportion of Kill Switch activations that prevented further loss; ratio of risk system costs (missed opportunities) to benefits (prevented losses).

---

### 7.2 RQS Monitoring and Response

**Intraday RQS monitoring:**

| RQS Level  | RQS Range    | Action                                                 |
|------------|--------------|--------------------------------------------------------|
| EXCELLENT  | 0.88 - 1.00  | No action; full operations                             |
| GOOD       | 0.72 - 0.87  | Monitor; investigate any dimension below 0.60          |
| ACCEPTABLE | 0.55 - 0.71  | Reduce position sizes by 20%; identify weak dimensions |
| MARGINAL   | 0.35 - 0.54  | Reduce by 50%; halt new positions in weakest categories|
| FAILED     | 0.00 - 0.34  | Halt all new positions; escalate; begin recovery       |

**RQS degradation investigation process:**
1. Identify the dimensions with lowest scores
2. Trace degradation to specific components (which component drives the low score?)
3. Check if degradation is temporary (data gap) or structural (component failure)
4. Apply targeted recovery to the failing component
5. Validate RQS recovery before resuming full operations

---

## PART VIII — RISK GOVERNANCE

### 8.0 Governance Philosophy

Risk governance is the institutional framework that ensures the Risk Engine operates as intended, evolves responsibly, and maintains the trust of human operators. Governance is not bureaucracy — it is the set of accountability structures that prevent the Risk Engine from drifting from its mandate.

Governance distinguishes the IIOS Risk Engine from an ad-hoc rule checker. An ad-hoc rule checker might produce correct outputs most of the time. A governed Risk Engine can demonstrate that it has produced correct outputs, explain why it made each decision, and show that its behavior was consistent with its stated principles.

---

### 8.1 Ownership and Responsibility

| Role                    | Responsibility                                          |
|-------------------------|---------------------------------------------------------|
| Risk Architecture Owner | Defines risk policies, thresholds, and constitutional rules|
| Session Operator        | Monitors live risk dashboard; responds to escalations   |
| Governance Reviewer     | Reviews daily governance reports; approves exceptions   |
| Policy Manager          | Updates risk policies; reviews threshold calibration    |
| Audit Reviewer          | Reviews audit records; validates hash chain integrity   |

---

### 8.2 Risk Naming Standards

**Risk Record IDs:**

| Record Type       | Format                              | Example                          |
|-------------------|-------------------------------------|----------------------------------|
| Risk Record       | RSK-{TYPE}-{YYYYMMDD}-{SEQ:08d}     | RSK-RT01-20260703-00000001       |
| Policy Record     | POL-{CAT}-{SEQ:04d}                 | POL-CAP-0001                     |
| Audit Record      | AUD-RSK-{YYYYMMDD}-{SEQ:08d}        | AUD-RSK-20260703-00000001        |
| Scenario Record   | SCN-{TARGET}-{YYYYMMDD}-{SEQ:04d}   | SCN-NIFTY-20260703-0001          |
| Stress Test       | STR-{SCENARIO}-{YYYYMMDD}-{SEQ:04d} | STR-SS01-20260703-0001           |
| Kill Switch Event | KSE-{TRIGGER}-{YYYYMMDD}-{SEQ:04d}  | KSE-T01-20260703-0001            |

**Risk Classification Tags:** RT-01 through RT-26 (see Part II taxonomy).

---

### 8.3 Versioning

**Policy versioning:** Policies use semantic versioning (MAJOR.MINOR.PATCH). MAJOR change = fundamental policy change requiring re-ratification. MINOR change = scope extension or threshold update. PATCH = text clarification.

**Threshold versioning:** Thresholds are versioned per session: session-date + version number. Any threshold change mid-session requires audit record.

**Scenario versioning:** Scenarios are versioned independently. Scenario content changes create a new version; the prior version is archived.

---

### 8.4 Validation Workflow

Before any change to risk policies, thresholds, or constitutional rules:
1. Change proposed with full rationale
2. Impact assessment: which components are affected?
3. Backtesting: how would the change have affected historical sessions?
4. Review by governance authority
5. Approval with signature
6. Implementation with effective date
7. Post-implementation monitoring period
8. Formal close-out or roll-back if monitoring period fails

---

### 8.5 Risk Policies

**Capital Policies (POL-CAP):**

POL-CAP-0001: Session drawdown limit is 2.0% of portfolio NAV. Kill Switch activates at breach.
POL-CAP-0002: No single position may exceed 15% of portfolio NAV.
POL-CAP-0003: No single sector may exceed 40% of portfolio NAV.
POL-CAP-0004: Gross portfolio exposure may not exceed 100% of NAV.
POL-CAP-0005: Minimum cash reserve of 10% of NAV at all times.

**Threshold Policies (POL-THR):**

POL-THR-0001: Thresholds may only be changed between sessions. No intraday changes.
POL-THR-0002: Threshold reductions (tighter limits) may be made at any time.
POL-THR-0003: Threshold relaxations require governance review before next session.

**Kill Switch Policies (POL-KS):**

POL-KS-0001: Kill Switch deactivation requires human operator authorization. No algorithmic clearing.
POL-KS-0002: All Kill Switch activations must be logged and reviewed within 24 hours.
POL-KS-0003: Kill Switch state is broadcast to all IIOS layers within 200ms.

**Audit Policies (POL-AUD):**

POL-AUD-0001: All risk decisions are logged in the audit chain before being acted on.
POL-AUD-0002: Audit records are retained for a minimum of 7 years.
POL-AUD-0003: Hash chain integrity is validated at session start and end.

---

### 8.6 Compliance Framework

| Requirement               | Standard         | Frequency    |
|---------------------------|------------------|--------------|
| Session risk summary      | Internal         | Daily        |
| Kill Switch log review    | Internal         | Daily        |
| VaR backtest              | Internal         | Weekly       |
| Policy compliance review  | Internal         | Weekly       |
| Full governance report    | Internal         | Monthly      |
| Audit chain integrity     | Internal         | Session start/end|

---

### 8.7 Security Requirements

1. Risk Registry write access is restricted to authorized Risk Engine components.
2. Kill Switch deactivation is restricted to authorized human operators.
3. Risk policy changes are access-controlled and fully logged.
4. Audit records are immutable: no delete or modify operations permitted.
5. All Risk Engine component communications are authenticated.
6. Kill Switch trigger state is maintained in tamper-resistant state: cannot be overwritten by algorithm.

---

### 8.8 Retention Policy

| Record Type          | Active Retention | Archive Retention | Purge Policy         |
|----------------------|------------------|-------------------|----------------------|
| Risk Records         | 1 trading session| 1 year detailed   | 7 years summarized   |
| Audit Records        | 1 trading session| 7 years full      | After 7 years        |
| Kill Switch Events   | Permanent        | Permanent         | Never purged         |
| Stress Test Results  | 30 sessions      | 1 year            | After 1 year         |
| Scenario Records     | Until retired     | 2 years           | After 2 years summary|
| Governance Reports   | 6 months active  | 7 years           | After 7 years        |
| Threshold History    | Permanent        | Permanent         | Never purged         |

---

## PART IX — RISK CONSTITUTION

### 9.0 Constitutional Purpose

The Risk Constitution is the highest-authority governance document for the Risk Engine. It contains the inviolable rules that govern all Risk Engine behavior. Constitutional rules cannot be overridden by configuration, by algorithm, or by individual operator decisions. Changes to the Constitution require formal re-ratification.

The Constitution is organized into 16 categories covering all aspects of risk management. Each rule is numbered and independently citable. The total rule set comprises 112 rules.

---

### Category RC-A — Capital Preservation (Rules 1–12)

**RC-A.01** Capital preservation is the primary mandate of the Risk Engine. All other functions are in service of this mandate.

**RC-A.02** The Risk Engine shall never approve a position that, if it moved adversely to maximum expected range, would cause the session drawdown to exceed the 2.0% Kill Switch threshold.

**RC-A.03** No position size shall exceed the capital risk budget allocated by the Capital Risk Engine (L6). Risk Engine approval does not override the capital budget; it further constrains it.

**RC-A.04** When the Risk Engine and the Decision Engine produce conflicting recommendations (Decision Engine: approve; Risk Engine: reject), the Risk Engine's rejection is final.

**RC-A.05** A minimum cash reserve of 10% of portfolio NAV shall be maintained at all times. Positions that would reduce cash below this level shall be reduced to comply.

**RC-A.06** Portfolio gross exposure shall not exceed 100% of NAV. Leveraged positions (F&O) shall be counted at their notional exposure, not their premium value.

**RC-A.07** When in doubt about the risk of a proposed action, the Risk Engine shall act conservatively: reject the action. The cost of a missed opportunity is always recoverable; the cost of a catastrophic loss may not be.

**RC-A.08** The Risk Engine shall compute an expected worst-case loss for every position before approving it. Positions where the worst-case loss exceeds 0.5% of NAV require elevated approval.

**RC-A.09** Position concentration shall be actively managed. No single instrument shall represent more than 15% of NAV by exposure.

**RC-A.10** Sector concentration shall be actively managed. No single sector shall exceed 40% of NAV by exposure.

**RC-A.11** Strategy concentration shall be monitored. No single strategy shall control more than 60% of deployed capital.

**RC-A.12** Capital protection measures are cumulative — they do not cancel each other. Position limits AND sector limits AND VaR limits AND drawdown limits all apply simultaneously.

---

### Category RC-B — Risk Integrity (Rules 13–20)

**RC-B.01** Every risk assessment shall be produced from verified, recent data. No risk assessment shall use data older than 5 minutes for market-sensitive inputs.

**RC-B.02** Risk assessments shall be reproducible. Given the same inputs, the Risk Engine shall produce the same risk assessment. Non-determinism in risk assessment is a defect.

**RC-B.03** Risk type misclassification is a defect, not an acceptable operational state. Unclassified risk signals shall be treated as maximum severity until classified.

**RC-B.04** Risk scores shall be calibrated against realized outcomes. A risk engine that consistently overestimates risk is too conservative; a risk engine that consistently underestimates is dangerous. Both are defects.

**RC-B.05** The Risk Engine shall maintain a calibration record. When calibration error exceeds 25%, the engine shall alert and begin recalibration.

**RC-B.06** Risk assessments shall be independent of the commercial desirability of the proposed trade. A highly profitable opportunity with excessive risk is rejected.

**RC-B.07** The Risk Engine shall not learn to be more permissive over time in the absence of adverse outcomes. Historical good outcomes do not justify relaxing limits without formal governance review.

**RC-B.08** Risk measurements shall use the most conservative of available methodologies when methodologies disagree.

---

### Category RC-C — Exposure Integrity (Rules 21–30)

**RC-C.01** Exposure calculations shall reflect the actual financial risk of positions, not their notional size or accounting value where these differ.

**RC-C.02** Exposure data shall be updated within 100ms of any position change. Stale exposure data shall be flagged; a STALE_EXPOSURE alert shall prevent new position approvals until refreshed.

**RC-C.03** For derivative positions (F&O), exposure shall be computed at notional value of the underlying, not the premium paid. Notional exposure reflects actual risk.

**RC-C.04** Exposure calculations shall include pending orders (submitted but not filled). Assuming a pending order will fill at full size is the conservative assumption.

**RC-C.05** Net exposure (long minus short) shall not be used to justify gross exposure violations. A portfolio with large long and large short positions still has large gross exposure risk.

**RC-C.06** Exposure concentration shall be monitored across three dimensions simultaneously: single name, sector, and strategy. A position that is within all three limits individually but contributes to concentration across all three simultaneously requires human review.

**RC-C.07** When two exposure calculations produce different results, the higher (more conservative) result shall be used until the discrepancy is resolved.

**RC-C.08** The Exposure Engine shall produce a reconciled exposure report at session close. Any discrepancy between intraday exposure tracking and end-of-session actuals triggers an investigation.

**RC-C.09** Exposure limits apply to the aggregate portfolio inclusive of all strategies. Individual strategies cannot each take maximum exposure.

**RC-C.10** Historical exposure data shall be preserved for VaR calibration. Minimum 250 sessions of daily exposure history is required for reliable VaR estimates.

---

### Category RC-D — Portfolio Protection (Rules 31–40)

**RC-D.01** Portfolio-level risk controls take precedence over individual position-level controls. A position that is within its individual limits but pushes the portfolio over a portfolio limit shall be rejected.

**RC-D.02** Portfolio diversification is mandatory. The IIOS shall not operate with a single concentrated position representing more than 30% of portfolio risk.

**RC-D.03** Correlation monitoring is a portfolio protection function. When average portfolio correlation rises above 0.65, the Risk Engine shall reduce new position approvals and alert the operator.

**RC-D.04** The portfolio's diversification ratio shall be monitored. A diversification ratio below 0.70 indicates insufficient diversification and shall trigger position review.

**RC-D.05** Pre-event protection is mandatory. When the Prediction Engine assigns probability > 0.60 to a significant market event affecting held positions, the Capital Protection Manager shall proactively reduce those positions by 30%.

**RC-D.06** Drawdown trajectory monitoring is required. A portfolio recovering from a drawdown shall be managed at 75% of normal position sizes until full recovery.

**RC-D.07** Intraday portfolio risk reviews shall occur at minimum at 10:00, 11:30, 13:00, 14:30, and 15:00 IST.

**RC-D.08** Portfolio VaR shall be recomputed after every position change. Using stale VaR for threshold checks is prohibited.

**RC-D.09** The portfolio shall maintain a minimum of 3 uncorrelated risk exposures at all times during active trading. Trading with fewer than 3 uncorrelated positions reduces diversification protection.

**RC-D.10** No new positions shall be added to the portfolio when the portfolio is in PROTECTIVE or HALT capital protection levels.

---

### Category RC-E — Kill Switch Integrity (Rules 41–50)

**RC-E.01** The Kill Switch is unconditional. When any of the ten defined trigger conditions (KS-T01 through KS-T10) is met, the Kill Switch activates. No algorithm may prevent this activation.

**RC-E.02** The Kill Switch shall activate within 200ms of a trigger condition being confirmed. Latency in Kill Switch activation is a critical defect.

**RC-E.03** The Kill Switch broadcasts its state to ALL IIOS layers simultaneously upon activation. No layer is exempted from the halt signal.

**RC-E.04** Kill Switch deactivation requires explicit human authorization. No algorithmic condition, no elapsed time, and no market recovery automatically clears the Kill Switch.

**RC-E.05** All Kill Switch activations are permanently logged. Kill Switch records are never purged.

**RC-E.06** Kill Switch trigger conditions are calibrated conservatively. False activations (Kill Switch fires but the risk was not as severe as expected) are preferable to missed activations.

**RC-E.07** The Kill Switch state is tamper-resistant. No process running within the IIOS may modify the Kill Switch state except the Kill Switch Manager acting on a valid trigger or a human operator providing authorization.

**RC-E.08** Kill Switch testing is conducted at session start. The Kill Switch mechanism is verified before every trading session.

**RC-E.09** When the Kill Switch is active, no new positions may be opened. Existing positions may be maintained or closed, depending on the trigger type and operator instruction.

**RC-E.10** After a Kill Switch activation, a post-event review is mandatory before the next session. The review shall identify the root cause and document any mitigations.

---

### Category RC-F — Stress Testing (Rules 51–58)

**RC-F.01** Stress testing is mandatory. The full 14-scenario suite shall be run at every session start before any trading commences.

**RC-F.02** No session begins if any stress test shows a projected portfolio loss exceeding 3% of NAV. Such a scenario requires immediate position review.

**RC-F.03** Intraday stress tests shall be conducted at minimum four times per session (10:00, 11:30, 13:00, 14:30).

**RC-F.04** Stress test results shall be archived for every run. Results are never overwritten; they accumulate.

**RC-F.05** Stress test scenarios are calibrated annually against actual market events. Historical events that were not covered by the scenario catalogue require new scenario creation.

**RC-F.06** Custom stress scenarios may be added by governance authority. They cannot be removed without equivalent authority.

**RC-F.07** Any stress scenario showing a loss exceeding 2% of NAV shall trigger position review. Scenarios with losses exceeding 3% shall block new positions until exposure is reduced.

**RC-F.08** Stress test outcomes that persistently underestimate actual adverse events indicate model miscalibration. The Stress Testing Engine shall recalibrate.

---

### Category RC-G — Tail Risk (Rules 59–65)

**RC-G.01** Tail risk is never assumed to follow a normal distribution. All tail risk computations shall use fat-tail adjusted estimates.

**RC-G.02** The Tail Risk Engine shall compute left-tail exposure at 1-in-10, 1-in-50, and 1-in-100 year scenarios at every session start.

**RC-G.03** Tail risk exposure that exceeds 5% of NAV in a 1-in-10 year scenario shall block new positions.

**RC-G.04** Tail risk predictions from the Prediction Engine (PT-17) shall be incorporated into tail risk assessment on every update cycle.

**RC-G.05** When the Prediction Engine assigns a probability greater than 5% to a tail event in the next session, position sizes shall be reduced by 30%.

**RC-G.06** Tail risk contributions by position shall be computed. Positions contributing disproportionate tail risk shall be candidates for size reduction.

**RC-G.07** Historical tail events (actual sessions where loss exceeded VaR99) shall be archived and used for tail model calibration.

---

### Category RC-H — Scenario Control (Rules 66–72)

**RC-H.01** Active scenarios shall be maintained for the full range of plausible market outcomes. The scenario set shall have no uncovered regions of probability mass > 0.20.

**RC-H.02** Scenario probabilities shall be updated at minimum every 30 minutes during the trading session.

**RC-H.03** Scenarios that have been invalidated by market events shall be promptly retired and replaced.

**RC-H.04** Scenario probabilities shall sum to approximately 1.0 (within 0.10 tolerance). Systematic under-coverage or over-coverage of the probability space is a defect.

**RC-H.05** No scenario shall be assigned a probability of 0.0 until it has been formally invalidated. Probability floor: 0.01 for any active scenario.

**RC-H.06** Scenario outcomes shall be compared to actual market outcomes at session close. Scenario accuracy is tracked for calibration.

**RC-H.07** The scenario catalogue shall include at minimum: a base scenario, a bear scenario, a bull scenario, a tail-down scenario, and a high-volatility scenario for every session.

---

### Category RC-I — Threshold Enforcement (Rules 73–80)

**RC-I.01** Thresholds are hard limits. When a hard threshold is breached, the corresponding action is mandatory. Thresholds are not suggestions.

**RC-I.02** Soft thresholds (WARNING, ALERT) generate alerts but do not block trading. Hard thresholds (BREACH, CRITICAL) block the relevant category of trading.

**RC-I.03** Threshold values are set conservatively. In regime uncertainty, thresholds shall be tightened, not relaxed.

**RC-I.04** Thresholds shall be regime-sensitive. Volatility-adjusted thresholds that tighten during high-VIX periods are preferred over fixed thresholds.

**RC-I.05** No intraday threshold relaxation is permitted. Thresholds may only be tightened during a session; relaxation requires next-session governance review.

**RC-I.06** Threshold breaches shall be alerted to human operators within 10 seconds.

**RC-I.07** The proportion of sessions experiencing threshold breaches is tracked. Persistent threshold breaches indicate either miscalibrated thresholds or excessive risk-taking.

**RC-I.08** Hard threshold breaches that would have caused the Kill Switch to fire but didn't (because the breach was marginal) are flagged for governance review.

---

### Category RC-J — Governance (Rules 81–88)

**RC-J.01** All risk management decisions are governed. Governance is not optional and does not depend on whether anything went wrong.

**RC-J.02** The daily governance report shall be reviewed by a human operator. Unreviewed governance reports are a governance failure.

**RC-J.03** Risk policy changes require formal approval. No policy change takes effect without documented approval.

**RC-J.04** The Risk Engine shall produce a complete governance report at every session close. This report includes: all threshold breaches, Kill Switch events, policy exceptions, and human overrides.

**RC-J.05** Human overrides of risk decisions are legitimate and supported, but all overrides are logged, explained, and reviewed.

**RC-J.06** Risk governance reviews shall evaluate whether the Risk Engine is becoming more or less permissive over time. Systematic drift toward permissiveness without formal policy revision is a governance failure.

**RC-J.07** External regulatory requirements are governance requirements. Any regulatory rule that affects risk management is automatically elevated to a policy-level requirement.

**RC-J.08** Governance review findings shall be acted on within a defined timeframe. Open findings with no action after 30 days escalate to senior review.

---

### Category RC-K — Security (Rules 89–94)

**RC-K.01** Risk Engine state (thresholds, Kill Switch state, positions) is protected against unauthorized modification.

**RC-K.02** Kill Switch state is tamper-resistant. Any attempted modification from a non-authorized source is treated as a security incident and logged.

**RC-K.03** Audit records are immutable. No modification or deletion of audit records is permitted under any circumstances.

**RC-K.04** Risk policies and thresholds are access-controlled. Only authorized governance users may modify them.

**RC-K.05** Anomalous trading patterns (unusual order frequency, size, or direction) that could indicate unauthorized access shall trigger an immediate security review and Kill Switch evaluation.

**RC-K.06** Risk Engine logs never contain account credentials, authentication tokens, or personally identifiable information.

---

### Category RC-L — Auditability (Rules 95–100)

**RC-L.01** Every risk decision is auditable. A risk assessment that cannot be reproduced from its archived inputs is incomplete.

**RC-L.02** The audit chain is validated at session start and session end. An invalid audit chain blocks session start until the discrepancy is resolved.

**RC-L.03** Risk decisions are logged before they are executed, not after. The audit record is the authorization token for the action.

**RC-L.04** Audit records contain: the specific inputs, the classification, the measurement, the threshold comparison, the action taken, and the timestamp of each step.

**RC-L.05** Point-in-time queries shall be supported. The risk state at any past timestamp during the retention period shall be reconstructable from audit records.

**RC-L.06** Audit completeness is measured. The proportion of risk decisions without complete audit records is an RQS metric (RQD-11).

---

### Category RC-M — Historical Preservation (Rules 101–104)

**RC-M.01** Risk history is a first-class asset. Historical risk data enables calibration, backtesting, and learning. Risk history shall never be deleted within retention periods.

**RC-M.02** Session risk summaries shall be permanent records. Even after detailed records are purged after 1 year, session summaries are retained for 7 years.

**RC-M.03** Kill Switch events are permanently preserved. No time limit applies.

**RC-M.04** VaR backtest data (predicted VaR vs actual loss) shall be retained for 2 years minimum to support model calibration.

---

### Category RC-N — Human Override (Rules 105–108)

**RC-N.01** Human operators have absolute authority over the Risk Engine's non-constitutional parameters. They may tighten thresholds, relax thresholds (within policy), add scenarios, and initiate manual Kill Switch.

**RC-N.02** Human overrides of REJECTED decisions are logged, audited, and reviewed. An operator who consistently overrides risk rejections is flagged for governance review.

**RC-N.03** Human operators may NOT override the Kill Switch once it is in ACTIVE state, except to authorize the RESET_PENDING → ARMED transition after a proper review.

**RC-N.04** Human override capability is a risk management feature, not a risk management bypass. Human judgment is a necessary complement to algorithmic risk management, not a replacement.

---

### Category RC-O — Model Independence (Rules 109–111)

**RC-O.01** Risk assessments are independent of the models that generated the investment signals. A signal from a highly accurate model receives the same risk scrutiny as a signal from an untested model.

**RC-O.02** The Risk Engine shall not grant preferential treatment to trades from high-performing strategies. Past performance does not reduce current risk.

**RC-O.03** The Risk Engine shall not be influenced by the confidence score of the Prediction Engine. High prediction confidence does not reduce market risk. A highly confident prediction that is wrong produces losses identical to a low-confidence prediction that is wrong.

---

### Category RC-P — Policy Compliance (Rules 112)

**RC-P.01** Every Risk Engine action is compliant with at least one active policy. Risk Engine actions that cannot be traced to a policy are defects.

**RC-P.02** (Reserved for future policy extension.)

**RC-P.03** (Reserved for future policy extension.)

---

## PART X — RISK READINESS CHECKLIST

### 10.0 Readiness Philosophy

The Risk Readiness Checklist is the formal certification process that must be completed before the Risk Engine is considered operational for a new trading session. The checklist is not advisory — it is a gate. Sessions begin only when the checklist is passed.

The checklist is organized into six domains: Component Readiness, Data Readiness, Policy Readiness, Governance Readiness, Operational Readiness, and Post-Session Assessment.

---

### 10.1 Component Readiness (22 items)

| Item | Component                      | Check                                      | Pass Condition                         |
|------|--------------------------------|--------------------------------------------|----------------------------------------|
| CR-01| RC-01 Risk Registry            | Registry accepts writes; hash chain valid  | Write test succeeds; chain intact       |
| CR-02| RC-02 Risk Catalog             | All 26 risk types loaded; version current  | 26 RT codes present; version matches   |
| CR-03| RC-03 Risk Analyzer            | Signal processing active; latency within SLA| P50 detection < 50ms                  |
| CR-04| RC-04 Risk Scoring Engine      | RQS computation functional                 | Test score in [0.0, 1.0]              |
| CR-05| RC-05 Exposure Engine          | Exposure computes from test portfolio      | Non-zero result; latency < 150ms       |
| CR-06| RC-06 Correlation Engine       | Correlation matrix computed; no NaN        | Matrix dimensions correct; no nulls    |
| CR-07| RC-07 Drawdown Monitor         | P&L feed connected; session peak reset     | Initial drawdown = 0.0%               |
| CR-08| RC-08 Stress Testing Engine    | All 14 scenarios loaded; test run passes   | 14 results; no scenario errors         |
| CR-09| RC-09 Scenario Engine          | Active scenarios loaded; probabilities sum | Prob sum within [0.90, 1.10]          |
| CR-10| RC-10 VaR Engine               | Historical data sufficient (>=250 sessions)| VaR computed; no insufficient-data err |
| CR-11| RC-11 Tail Risk Engine         | Fat-tail parameters loaded; test computes  | Tail loss estimate > 0                 |
| CR-12| RC-12 Risk Policy Manager      | All policies loaded; no conflicts          | Policy count >= minimum; no conflicts  |
| CR-13| RC-13 Risk Threshold Manager   | All thresholds set; within policy bounds   | All thresholds within valid ranges     |
| CR-14| RC-14 Kill Switch Manager      | KS armed; trigger monitoring active        | Status = ARMED; all 10 triggers active |
| CR-15| RC-15 Capital Protection Mgr   | Protection level correct (STANDARD)        | Status = STANDARD                      |
| CR-16| RC-16 Position Limit Manager   | All position limits active                 | Limits loaded; within policy range     |
| CR-17| RC-17 Portfolio Limit Manager  | Portfolio limits active                    | Gross/net limits set and active        |
| CR-18| RC-18 Risk Governance Manager  | Prior session governance cleared           | No open unreviewed governance items    |
| CR-19| RC-19 Risk Audit Manager       | Audit chain ready; prior chain closed      | Hash chain integrity: VALID            |
| CR-20| RC-20 Risk Archive Manager     | Write access to archive; disk space ok     | Write test succeeds; disk >= 10% free  |
| CR-21| RC-21 Risk Analytics Manager   | Historical data accessible                 | Can retrieve last 30 sessions          |
| CR-22| RC-22 Risk Health Manager      | REHS computation functional                | REHS >= NOMINAL (>= 0.75)             |

---

### 10.2 Data Readiness (10 items)

| Item  | Check                                              | Pass Condition                         |
|-------|----------------------------------------------------|----------------------------------------|
| DR-01 | Market price data feed active                      | Last data < 60 seconds ago             |
| DR-02 | India VIX data available                           | VIX value received; non-zero           |
| DR-03 | Correlation history sufficient (>= 250 sessions)  | 250+ sessions available                |
| DR-04 | VaR history sufficient (>= 250 sessions)           | 250+ sessions available                |
| DR-05 | Prior session performance data loaded              | Strategy stats from last session loaded|
| DR-06 | GlobalIntelligence (L1) data current               | Global snapshot < 12 hours old        |
| DR-07 | MarketIntelligence (L2) regime current             | Regime computed for today              |
| DR-08 | Position data reconciled with broker               | Broker positions match IIOS positions  |
| DR-09 | Stress scenario parameters current                 | SS parameters last updated < 30 days  |
| DR-10 | Risk model calibration current                     | VaR model last recalibrated < 30 days |

---

### 10.3 Policy Readiness (7 items)

| Item  | Check                                              | Pass Condition                            |
|-------|----------------------------------------------------|-------------------------------------------|
| PR-01 | All capital policies (POL-CAP) active              | All POL-CAP rules loaded and active       |
| PR-02 | All threshold policies (POL-THR) active            | All POL-THR rules loaded and active       |
| PR-03 | Kill Switch policies (POL-KS) active               | All POL-KS rules active; KS armed        |
| PR-04 | Audit policies (POL-AUD) active                    | Retention schedules set                   |
| PR-05 | No policy conflicts detected                       | Conflict check returns 0 conflicts        |
| PR-06 | All policies version-current                       | No policy has an expired version flag     |
| PR-07 | Human operator briefed on active policies          | Operator acknowledgment recorded          |

---

### 10.4 Governance Readiness (5 items)

| Item  | Check                                              | Pass Condition                              |
|-------|----------------------------------------------------|---------------------------------------------|
| GR-01 | Prior session governance report reviewed           | Review acknowledgment present               |
| GR-02 | Open risk findings resolved or acknowledged        | No unacknowledged open findings > 1 session |
| GR-03 | Kill Switch log reviewed if any prior activation   | Any KS events from prior session reviewed  |
| GR-04 | VaR backtest reviewed if exceedance flagged        | Any VaR exceedances from prior week reviewed|
| GR-05 | Human operator declared available for session      | Operator availability confirmed             |

---

### 10.5 Operational Test (7 items)

| Item  | Test                                               | Pass Condition                              |
|-------|----------------------------------------------------|---------------------------------------------|
| OT-01 | End-to-end test: submit mock trade through RP-01  | Returns APPROVED or REDUCED; no error      |
| OT-02 | Kill Switch test: simulate DD = 2.1% signal       | Kill Switch activates; manual reset required|
| OT-03 | Drawdown Monitor test: reset session peak          | Session peak = 0; DD = 0.0%               |
| OT-04 | Stress test run: all 14 scenarios execute          | 14 results returned; none in error state   |
| OT-05 | Exposure Engine: compute from current positions    | Result consistent with broker positions    |
| OT-06 | Audit chain: hash chain integrity validation       | All records pass hash validation           |
| OT-07 | REHS: compute and confirm                          | REHS >= NOMINAL                            |

---

### 10.6 Post-Session Assessment (10 items)

At session close, the Risk Engine completes a post-session assessment to evaluate performance and identify improvements.

| Item  | Assessment                                         | Target                                     |
|-------|----------------------------------------------------|--------------------------------------------|
| PS-01 | Session max drawdown                               | < 1.0% (no action needed)                 |
| PS-02 | Threshold breaches during session                  | 0 BREACH, 0 CRITICAL                      |
| PS-03 | Kill Switch activations                            | 0 (unless market justified)               |
| PS-04 | VaR exceedances                                    | 0 (session); < 5% rolling 3-month         |
| PS-05 | Stress test worst scenario vs actual               | Stress scenario bounded actual loss        |
| PS-06 | Risk Engine latency compliance                     | 99% of assessments within SLA             |
| PS-07 | RQS score: end-of-session                          | >= ACCEPTABLE (>= 0.55)                   |
| PS-08 | Audit chain integrity: end-of-session validation   | VALID                                     |
| PS-09 | Governance report generated and queued for review  | Report present                            |
| PS-10 | Risk Archive: session records archived             | Archive write confirmed                   |

---

### 10.7 Readiness Matrix

| Level          | REHS    | Component Readiness | Data Readiness | Kill Switch | Trading Implication         |
|----------------|---------|---------------------|----------------|-------------|------------------------------|
| FULLY_READY    | >= 0.90 | All 22 pass         | All 10 pass    | ARMED       | Full position sizing         |
| OPERATIONAL    | >= 0.75 | >= 20 pass          | >= 9 pass      | ARMED       | Normal trading               |
| DEGRADED       | >= 0.55 | >= 18 pass          | >= 8 pass      | ARMED       | 50% position sizes; alert   |
| RESTRICTED     | >= 0.30 | >= 15 pass          | >= 7 pass      | ARMED       | 25% sizes; operator review  |
| NOT_READY      | < 0.30  | < 15 pass           | < 7 pass       | ANY         | No trading; recovery required|

---

### 10.8 Readiness State Machine

`
READINESS STATE MACHINE
════════════════════════

PRE_SESSION_INIT
  │ Run checklists CR-01 through OT-07
  ▼
EVALUATING_READINESS
  │
  ├── All criteria met → FULLY_READY
  │                          │
  │                          ▼ Trading session opens
  │
  ├── Marginal criteria → DEGRADED / RESTRICTED
  │                          │
  │                          ▼ Reduced trading; operator notification
  │
  └── Critical failures → NOT_READY
                              │
                              ▼ Recovery procedures; no session start

FULLY_READY / OPERATIONAL (during session)
  ├── REHS degrades → DEGRADED
  ├── Kill Switch fires → KILL_SWITCH_ACTIVE
  └── Session ends → POST_SESSION

POST_SESSION
  ├── PS-01 through PS-10 assessed
  └── Archive and governance report → PRE_SESSION_INIT (next session)
`

---

## SUPPLEMENT A — RISK TAXONOMY REFERENCE

### A.1 Full Taxonomy Index

| Code  | Risk Type           | Domain     | Measurable | Kill Switch Trigger |
|-------|---------------------|------------|------------|---------------------|
| RT-01 | Market Risk         | Price      | Yes        | Indirect            |
| RT-02 | Portfolio Risk      | Portfolio  | Yes        | Indirect            |
| RT-03 | Position Risk       | Position   | Yes        | Indirect            |
| RT-04 | Sector Risk         | Portfolio  | Yes        | No                  |
| RT-05 | Industry Risk       | Portfolio  | Yes        | No                  |
| RT-06 | Liquidity Risk      | Market     | Partial    | Indirect            |
| RT-07 | Execution Risk      | Execution  | Yes        | No                  |
| RT-08 | Model Risk          | System     | Partial    | No                  |
| RT-09 | Prediction Risk     | System     | Partial    | No                  |
| RT-10 | Decision Risk       | Decision   | Partial    | No                  |
| RT-11 | Behavioral Risk     | System     | Partial    | No                  |
| RT-12 | Counterparty Risk   | Broker     | Partial    | Direct              |
| RT-13 | Currency Risk       | Macro      | Yes        | No                  |
| RT-14 | Interest Rate Risk  | Macro      | Yes        | No                  |
| RT-15 | Macro Risk          | Macro      | Partial    | Indirect            |
| RT-16 | Political Risk      | External   | No         | Indirect            |
| RT-17 | Regulatory Risk     | External   | Partial    | Indirect            |
| RT-18 | Technology Risk     | System     | Yes        | Direct              |
| RT-19 | Cyber Risk          | System     | Partial    | Direct              |
| RT-20 | Operational Risk    | System     | Partial    | Indirect            |
| RT-21 | Concentration Risk  | Portfolio  | Yes        | No                  |
| RT-22 | Correlation Risk    | Portfolio  | Yes        | No                  |
| RT-23 | Tail Risk           | Portfolio  | Yes        | Direct              |
| RT-24 | Black Swan Risk     | System     | No         | Direct              |
| RT-25 | Event Risk          | Position   | Partial    | Indirect            |
| RT-26 | Strategy Risk       | Strategy   | Partial    | No                  |

### A.2 Risk Type Hierarchy

`
IIOS RISK TYPE HIERARCHY
═════════════════════════

Market-Driven Risks
├── RT-01 Market Risk
│   ├── Direction Risk
│   ├── Volatility Risk
│   └── Correlation Risk (as market factor)
├── RT-06 Liquidity Risk
├── RT-13 Currency Risk
└── RT-14 Interest Rate Risk

Portfolio-Level Risks
├── RT-02 Portfolio Risk
├── RT-04 Sector Risk
├── RT-05 Industry Risk
├── RT-21 Concentration Risk
└── RT-22 Correlation Risk (as portfolio factor)

Position-Level Risks
├── RT-03 Position Risk
├── RT-07 Execution Risk
└── RT-25 Event Risk

System and Model Risks
├── RT-08 Model Risk
├── RT-09 Prediction Risk
├── RT-10 Decision Risk
├── RT-11 Behavioral Risk
├── RT-18 Technology Risk
├── RT-19 Cyber Risk
└── RT-20 Operational Risk

Macro and External Risks
├── RT-15 Macro Risk
├── RT-16 Political Risk
└── RT-17 Regulatory Risk

Extreme / Tail Risks
├── RT-23 Tail Risk
├── RT-24 Black Swan Risk
└── RT-12 Counterparty Risk

Strategy Risks
└── RT-26 Strategy Risk
`

---

## SUPPLEMENT B — RISK FORMULAS (CONCEPTUAL)

### B.1 Value at Risk (VaR) — Conceptual

**Historical Simulation VaR:**
1. Collect the portfolio's historical daily return series (minimum 250 observations)
2. Sort returns from worst to best
3. VaR at confidence level c = the loss at the (1-c) percentile of the sorted series
4. VaR(95%, 1-day) = the loss at the 5th percentile of the historical distribution

**Parametric VaR:**
VaR(c, T) = portfolio_value x z_c x portfolio_volatility x sqrt(T)
Where: z_c is the standard normal quantile at confidence c; T is the time horizon in days

**Key insight:** Parametric VaR assumes normality. It underestimates tail losses because financial returns are fat-tailed. IIOS uses historical simulation as the primary method to avoid this assumption.

---

### B.2 Conditional VaR (Expected Shortfall)

CVaR(c) = (1 / (1-c)) x integral from -infinity to VaR(c) of x * f(x) dx

In discrete terms: CVaR(95%) = the average of the worst 5% of historical returns

CVaR is always >= VaR at the same confidence level. CVaR captures the average magnitude of losses that exceed VaR. It is a more complete measure of tail risk.

---

### B.3 Portfolio Volatility

Portfolio variance = sum over all pairs (i, j) of: weight_i x weight_j x cov(i, j)

Where cov(i, j) = correlation(i, j) x volatility_i x volatility_j

Portfolio volatility = sqrt(portfolio variance)

Key insight: diversification reduces portfolio volatility only if correlations < 1.0. When correlations approach 1.0 (stress state), portfolio volatility approaches the weighted average of individual volatilities — diversification benefit disappears.

---

### B.4 Drawdown Computation

Session_Peak_PNL(t) = max over all tau <= t of: PNL(tau)

Current_Drawdown(t) = Session_Peak_PNL(t) - PNL(t) (if positive) or 0 (if portfolio above peak)

Drawdown_Pct(t) = Current_Drawdown(t) / Starting_Portfolio_NAV

Kill Switch condition: Drawdown_Pct(t) >= 0.02 (2% of NAV)

---

### B.5 Exposure Metrics

Gross Exposure = sum of abs(position_value_i) for all positions i

Net Exposure = sum of signed_position_value_i for all positions i (positive = net long; negative = net short)

Net Exposure Ratio = Net Exposure / Portfolio_NAV

Gross Exposure Ratio = Gross Exposure / Portfolio_NAV

Concentration Index (HHI) = sum of (weight_i)^2 for all positions i (weight = position / portfolio)
HHI = 1.0 for a single-position portfolio; decreases as diversification increases

---

### B.6 EWMA Volatility

EWMA_variance(t) = lambda x EWMA_variance(t-1) + (1 - lambda) x return(t)^2

EWMA_volatility(t) = sqrt(EWMA_variance(t))

Normal lambda: 0.94 (RiskMetrics standard)
Stress lambda: 0.75 (faster adaptation)

---

### B.7 Risk Quality Score (RQS)

RQS = 0.20 x RQD-01 + 0.15 x RQD-02 + 0.12 x RQD-03 + 0.10 x RQD-04
    + 0.10 x RQD-05 + 0.08 x RQD-06 + 0.08 x RQD-07 + 0.05 x RQD-08
    + 0.05 x RQD-09 + 0.03 x RQD-10 + 0.02 x RQD-11 + 0.02 x RQD-12

All weights sum to 1.00. All RQD dimension scores in [0.0, 1.0].

---

### B.8 Diversification Ratio

Diversification_Ratio = Portfolio_VaR / (sum of individual position VaRs)

Diversification_Ratio = 1.0 when all positions are perfectly correlated (no diversification benefit)
Diversification_Ratio < 1.0 when correlations < 1.0 (diversification provides benefit)
Diversification_Ratio approaching 0.0 is extremely high diversification benefit

IIOS minimum: Diversification_Ratio >= 0.70. Below 0.70 indicates excessive concentration.

---

## SUPPLEMENT C — STRESS TESTING CATALOGUE

### C.1 Stress Testing Design

The IIOS stress testing catalogue provides a complete library of stress scenarios used to evaluate portfolio resilience. Each scenario is defined by its trigger conditions, its market impact parameters, its IIOS portfolio impact formula, and its historical precedents.

Stress scenarios are organized into four categories:
- Category I: Market Price Shocks (SS-01 to SS-04)
- Category II: Market Structure Events (SS-05 to SS-07)
- Category III: Macro and External Events (SS-08 to SS-11)
- Category IV: IIOS-Specific Events (SS-12 to SS-14)

---

### C.2 Stress Scenario Definitions

**SS-01 — Market Circuit Breaker 5%**
*Category:* Market Price Shock
*Description:* The NIFTY 50 index falls 5% intraday, triggering the NSE Level 1 circuit breaker. Trading halts for 45 minutes.
*Parameters:* Index fall = -5%; Beta-weighted portfolio impact = -5% x portfolio_beta; Sector impacts vary by beta.
*Worst-case provision:* All positions assumed at full beta to index during this scenario.
*Historical precedents:* March 23, 2020 (COVID crash); March 12, 2020; multiple sessions in 2008.
*Risk Engine response:* All new positions suspended during halt; on resumption, stress test repeated.

**SS-02 — Market Circuit Breaker 10%**
*Category:* Market Price Shock
*Description:* The NIFTY 50 index falls 10% intraday, triggering the NSE Level 2 circuit breaker. Trading halts for 2 hours.
*Parameters:* Index fall = -10%; portfolio impact = -10% x portfolio_beta; F&O positions face margin calls.
*Kill Switch implication:* Portfolio drawdown of 10% x typical_beta (~1.1) = ~11% estimated loss. Kill Switch is active before this threshold.
*Risk Engine response:* Kill Switch already active (DD > 2%); focus shifts to position maintenance.

**SS-03 — Flash Crash**
*Category:* Market Price Shock
*Description:* The index falls 15% within 30 minutes due to algorithmic cascade. Sharp, fast, and potentially partially reversed.
*Parameters:* Index fall = -15%; recovery partial (50% reversal in 60 minutes); liquidity evaporates during fall.
*Key risk:* Stop losses triggered at worst prices; unable to exit at reasonable prices.
*Portfolio impact formula:* Initial impact = -15% x portfolio_beta; realized impact depends on stop loss placement.
*Historical precedents:* US May 6, 2010; NSE occasional mini-crashes during high-frequency events.

**SS-04 — Volatility Spike (VIX 50+)**
*Category:* Market Price Shock
*Description:* India VIX doubles from current level to 50+ within one session. Correlations converge toward 1.0.
*Parameters:* VIX = 50; all correlations set to 0.90 (stress correlation); implied volatility increases 100%.
*Portfolio impact:* Systematic repricing of all risk measures; VaR expands dramatically.
*Kill Switch check:* VIX >= 45 is an explicit Kill Switch trigger (KS-T02).

**SS-05 — Liquidity Crisis**
*Category:* Market Structure Event
*Description:* Market-wide liquidity evaporates. Bid-ask spreads widen 5x; order book depth falls 80%.
*Parameters:* Bid-ask spread multiplier = 5x; depth = 20% of normal; market impact = 5x normal.
*Portfolio impact:* Any exit or entry costs 5x the normal spread. Large positions become illiquid.
*Key risk:* Positions that appear profitable become loss-making when exit costs are factored in.

**SS-06 — RBI Emergency Rate Hike**
*Category:* Market Structure Event
*Description:* Reserve Bank of India announces a surprise emergency rate hike of 100 basis points.
*Parameters:* Equity impact = -6%; financial sector impact = -10%; bond yields +100bps.
*Historical precedents:* RBI had emergency actions in 2013 (taper tantrum) and 2022 (emergency meeting).
*Portfolio impact:* Banking sector positions most affected; rate-sensitive companies second.

**SS-07 — Sector Shock**
*Category:* Market Structure Event
*Description:* The portfolio's largest sector exposure experiences a 15% sector-specific decline.
*Parameters:* Identified sector drops 15%; other sectors flat; correlation within sector = 0.95.
*Portfolio impact:* Equal to sector_weight x (-15%) + correlation drag on other positions.

**SS-08 — Single Name Collapse**
*Category:* Macro / External Event
*Description:* The portfolio's largest single position hits limit-down (20% lower circuit breaker).
*Parameters:* Largest position: -20%; circuit breaker halts trading.
*Portfolio impact:* position_weight x (-20%); position cannot be exited on the day.

**SS-09 — FII Outflow Event**
*Category:* Macro / External Event
*Description:* Significant Foreign Institutional Investor outflows triggered by global risk-off sentiment. Market falls 8% over 2 days.
*Parameters:* Market impact = -8% over 2 sessions; INR weakens; emerging market correlation rises.
*Historical precedents:* Multiple events during Fed tightening cycles; COVID initial reaction March 2020.

**SS-10 — INR Currency Crisis**
*Category:* Macro / External Event
*Description:* The Indian Rupee falls 5% against USD in a single session due to capital flight.
*Parameters:* INR/USD -5%; foreign capital exits India equities; market falls 4%.
*Portfolio impact:* Direct for currency-exposed positions; indirect via market fall.

**SS-11 — Global Contagion**
*Category:* Macro / External Event
*Description:* A major global financial event causes a correlated sell-off across all asset classes. NSE falls 12%.
*Parameters:* Correlation to global markets = 1.0 during event; market falls -12%; volatility +150%.
*Historical precedents:* 2008 Lehman; 2020 COVID; 2022 Russia-Ukraine (partial).

**SS-12 — Earnings Disaster**
*Category:* IIOS-Specific Event
*Description:* The portfolio's largest holding reports a catastrophic earnings miss, falling 25%.
*Parameters:* Largest position: -25%; rest of portfolio: market impact from correlated names.
*Portfolio impact:* position_weight x (-25%); sector contagion adds 2-4%.

**SS-13 — Correlation Breakdown**
*Category:* IIOS-Specific Event
*Description:* The diversification assumption breaks down: all portfolio instruments correlate to 0.95.
*Parameters:* All pairwise correlations = 0.95; portfolio VaR → weighted average of individual VaRs.
*Portfolio impact:* VaR expands by (1/diversification_ratio) factor; effectively eliminates diversification benefit.

**SS-14 — Technology Failure**
*Category:* IIOS-Specific Event
*Description:* IIOS order management system fails during open positions. Unable to execute new orders or close positions.
*Parameters:* No trades possible for 30 minutes; market moves adversely.
*Portfolio impact:* Assumes adverse market movement of 0.5% during failure period; inability to hedge.
*Kill Switch check:* Technology failure is KS-T09; Kill Switch activates on system monitor alert.

---

### C.3 Stress Test Execution Matrix

| Scenario | Execution Frequency  | Portfolio Impact Limit | Action if Breached            |
|----------|----------------------|-----------------------|-------------------------------|
| SS-01    | Session start + 4x   | > 1.0% NAV            | Reduce beta-exposed positions |
| SS-02    | Session start + 4x   | > 2.0% NAV            | Kill Switch pre-condition     |
| SS-03    | Session start         | > 2.5% NAV            | Reduce position sizes 30%     |
| SS-04    | Session start + 4x   | > 1.5% NAV            | Reduce sizes; monitor VIX     |
| SS-05    | Session start + 2x   | > 1.0% NAV            | Reduce illiquid positions     |
| SS-06    | Session start         | > 1.5% NAV            | Reduce financial sector       |
| SS-07    | Session start         | > 1.0% NAV            | Review largest sector         |
| SS-08    | Session start + 4x   | > 0.5% NAV            | Reduce largest position       |
| SS-09    | Session start         | > 1.0% NAV            | Review foreign-exposed names  |
| SS-10    | Session start         | > 0.5% NAV            | Review INR-sensitive names    |
| SS-11    | Session start         | > 2.0% NAV            | Reduce overall exposure       |
| SS-12    | Session start + 4x   | > 1.0% NAV            | Reduce largest holding        |
| SS-13    | Session start + 2x   | > 1.5% NAV            | Improve diversification       |
| SS-14    | Session start + 1x   | Any                   | Verify technology backup      |

---

## SUPPLEMENT D — SCENARIO CATALOGUE

### D.1 Session Scenario Framework

For each trading session, the Scenario Engine maintains a complete scenario set covering the full probability distribution of session outcomes. The session scenario framework requires a minimum of 5 base scenario types.

**Required Base Scenarios:**

| ID     | Type          | Description                                           | Probability Range |
|--------|---------------|-------------------------------------------------------|-------------------|
| BASE   | Base Case     | Conditions continue roughly as expected               | 0.35 - 0.50       |
| BULL   | Bull Case     | Positive conditions: upward momentum, low volatility  | 0.15 - 0.30       |
| BEAR   | Bear Case     | Adverse conditions: downward pressure, rising vol     | 0.15 - 0.30       |
| TAIL_D | Tail Down     | Extreme adverse event: circuit breaker or equivalent  | 0.01 - 0.05       |
| HVOL   | High Vol      | Volatility spike without clear direction              | 0.05 - 0.15       |

Probabilities are assigned by the Prediction Engine. Sum across all active scenarios must be within [0.90, 1.10].

---

### D.2 Scenario Templates

**BULL Scenario Template:**

| Field               | Value                                              |
|---------------------|----------------------------------------------------|
| Trigger             | GlobalIntelligence: positive overnight; VIX falling|
| Expected NIFTY      | +0.5% to +1.5% intraday                           |
| Expected VIX        | -5% to -15% from session open                     |
| Expected Volume     | 90-110% of 30-day average                          |
| Correlation regime  | Normal (lambda = 0.94)                             |
| Liquidity           | Normal to good                                     |
| Portfolio impact    | +beta x index_gain                                 |
| Key risk            | Overpaying on entries; chasing momentum            |

**BASE Scenario Template:**

| Field               | Value                                              |
|---------------------|----------------------------------------------------|
| Trigger             | No strong directional signal; mixed data           |
| Expected NIFTY      | -0.5% to +0.5% intraday                           |
| Expected VIX        | -5% to +5% from session open                      |
| Expected Volume     | 80-120% of 30-day average                          |
| Correlation regime  | Normal (lambda = 0.94)                             |
| Liquidity           | Normal                                             |
| Portfolio impact    | Near-zero; individual stock selection dominant     |
| Key risk            | Low alpha environment; execution costs meaningful  |

**BEAR Scenario Template:**

| Field               | Value                                              |
|---------------------|----------------------------------------------------|
| Trigger             | GlobalIntelligence: negative overnight; high VIX   |
| Expected NIFTY      | -1.0% to -3.0% intraday                           |
| Expected VIX        | +10% to +30% from session open                    |
| Expected Volume     | 110-150% of 30-day average                         |
| Correlation regime  | Elevated (lambda = 0.85)                           |
| Liquidity           | Reduced; spreads widen                             |
| Portfolio impact    | -beta x abs(index_fall)                            |
| Key risk            | Stop losses triggered; drawdown limit approached   |

**TAIL_DOWN Scenario Template:**

| Field               | Value                                              |
|---------------------|----------------------------------------------------|
| Trigger             | Circuit breaker / extreme sell-off signal          |
| Expected NIFTY      | -5% to -15%                                       |
| Expected VIX        | +50% to +150%                                      |
| Expected Volume     | 200-400% of 30-day average                         |
| Correlation regime  | Stress (all correlations → 0.95; lambda = 0.70)   |
| Liquidity           | Crisis: spreads 5x; depth 20%                      |
| Portfolio impact    | beta x index_fall + liquidity_haircut               |
| Kill Switch         | Active at -2% portfolio drawdown                   |
| Key risk            | Inability to exit; margin calls; cascade losses    |

**HIGH_VOLATILITY Scenario Template:**

| Field               | Value                                              |
|---------------------|----------------------------------------------------|
| Trigger             | VIX spike without clear direction                  |
| Expected NIFTY      | Wide range: -2% to +2%                            |
| Expected VIX        | +30% to +80% from session open                    |
| Expected Volume     | 120-180% of 30-day average                         |
| Correlation regime  | Elevated; unstable                                 |
| Liquidity           | Variable; deteriorates during swings               |
| Portfolio impact    | High variance: outcomes range from -1.5% to +1.5% |
| Key risk            | Whipsaw; stop loss hunting; slippage               |

---

### D.3 Scenario Probability Assignment Rules

1. The Prediction Engine (RS-05 Scenario Service) provides probability estimates for each scenario type.
2. The Scenario Engine validates that the sum of all active scenario probabilities is within [0.90, 1.10].
3. When Prediction Engine is unavailable, the default probability set is: BASE=0.40, BULL=0.25, BEAR=0.25, TAIL_DOWN=0.02, HVOL=0.08.
4. Scenario probabilities are updated every 30 minutes during the session.
5. No scenario probability may be set to 0.0 while the scenario is active; minimum is 0.01.
6. Scenarios that have been invalidated by market events are retired and replaced.

---

### D.4 Scenario Outcome Tracking

| Field             | Description                                           |
|-------------------|-------------------------------------------------------|
| scenario_id       | SCN-{TYPE}-{YYYYMMDD}-{SEQ:04d}                       |
| outcome           | MATERIALIZED / NEAR_MISS / INVALIDATED / NO_OUTCOME   |
| actual_nifty_move | Realized NIFTY change for the session                 |
| predicted_range   | The range the scenario predicted                      |
| within_range      | Boolean: did actual fall within scenario range?       |
| p_at_materialization| Probability assigned when scenario materialized   |
| calibration_error | abs(probability - actual_frequency) over rolling 100  |

---

## SUPPLEMENT E — KILL SWITCH MATRIX

### E.1 Kill Switch Architecture Overview

The Kill Switch is the IIOS's unconditional trading halt mechanism. It is the ultimate capital protection tool and the final enforcement layer of the Risk Engine. The Kill Switch has no analog in other engine architectures — it is unique to the Risk Engine as the guardian of capital.

The Kill Switch Matrix documents all trigger conditions, their activation criteria, their consequences, and the required recovery actions.

---

### E.2 Complete Kill Switch Trigger Matrix

| Code   | Trigger Name              | Condition                           | Source               | Activate | Auto-Clear | Human Required |
|--------|---------------------------|-------------------------------------|----------------------|----------|------------|----------------|
| KS-T01 | Daily Loss Threshold      | Portfolio DD >= 2.0%                | RC-07 Drawdown       | Immediate| No         | Yes            |
| KS-T02 | VIX Extreme               | India VIX >= 45                     | L2 MarketIntel       | Immediate| Conditional| Yes            |
| KS-T03 | Broker Disconnection      | Connection fail > 60 seconds        | L11 Execution        | 60s delay| Conditional| Yes            |
| KS-T04 | Data Feed Failure         | Price feed down > 30 seconds        | Observation Engine   | 30s delay| Conditional| Yes            |
| KS-T05 | Tail Risk Extreme         | Tail event probability > 30%        | RC-11 Tail Risk      | Immediate| No         | Yes            |
| KS-T06 | Manual Activation         | Operator command                    | Human operator       | Immediate| No         | Yes (same)     |
| KS-T07 | Stress Test Breach        | Any scenario: loss > 3% NAV         | RC-08 Stress Test    | Immediate| No         | Yes            |
| KS-T08 | Portfolio Limit Breach    | Gross exposure > 110% limit         | RC-17 Portfolio      | Immediate| No         | Yes            |
| KS-T09 | Technology Failure        | System Monitor critical alert       | L17 ControlTower     | Immediate| Conditional| Yes            |
| KS-T10 | Market Circuit Breaker    | NSE Level 1 or Level 2 circuit      | L2 MarketIntel       | Immediate| Conditional| Yes            |

**Conditional Auto-Clear:** For KS-T02 (VIX), KS-T03 (broker), KS-T04 (data feed), KS-T09 (technology), KS-T10 (circuit breaker) — when the triggering condition resolves, the Kill Switch enters RESET_PENDING state automatically, but human authorization is still required to progress to ARMED.

---

### E.3 Kill Switch State Definitions

| State           | Meaning                                                   | Permitted Actions                    |
|-----------------|-----------------------------------------------------------|--------------------------------------|
| ARMED           | Normal operating state; ready to trigger if conditions met| All trading permitted                |
| TRIGGERED       | Trigger condition detected; evaluating                    | Evaluation only; no new trades       |
| ACTIVE          | Trading halted; full kill state                           | Position maintenance or wind-down only|
| RESET_PENDING   | Trigger condition resolved; awaiting human auth           | No new trades; positions maintained  |
| MANUAL_OVERRIDE | Human has overridden specific trigger; annotated          | Trading permitted under restrictions |

---

### E.4 Kill Switch Consequences by Trigger Type

**KS-T01 (Daily Loss):**
- Consequence: Immediate trading halt. Session is over. Positions maintained unless operator instructs close.
- Recovery: Next session only. Post-event review mandatory before restart.
- Position management: Operator decides whether to close remaining positions or carry to next session.

**KS-T02 (VIX Extreme):**
- Consequence: Trading halt while VIX >= 45. VIX typically spikes and retreats.
- Recovery: When VIX falls below 40, RESET_PENDING automatically. Human authorization to resume.
- Position management: Positions maintained during halt. Risk Engine continues monitoring.

**KS-T03 (Broker Disconnection):**
- Consequence: No new orders possible. Existing positions held in uncertainty (broker may or may not have received last orders).
- Recovery: When broker connection restored and position reconciliation passes, RESET_PENDING.
- Position management: Wait for broker reconnection; reconcile position state before resuming.

**KS-T04 (Data Feed Failure):**
- Consequence: No reliable price data. Risk assessments unreliable.
- Recovery: When data feed restored and data passes freshness validation, RESET_PENDING.
- Position management: Positions held. No risk assessments until data restored.

**KS-T05 (Tail Risk Extreme):**
- Consequence: Tail event probability too high for normal operations. Immediate halt.
- Recovery: When tail risk assessment returns to < 20%, RESET_PENDING. Human authorization required.
- Position management: Operator reviews and decides on position management.

**KS-T06 (Manual):**
- Consequence: Immediate halt as instructed by operator.
- Recovery: Human operator issues CLEAR command with rationale.
- Position management: As directed by operator.

**KS-T07 (Stress Test Breach):**
- Consequence: Halt new positions. Existing stress breach requires position review.
- Recovery: When stress test results return to < 2% NAV impact, human authorization to resume.
- Position management: Reduce positions to bring stress test within limits.

**KS-T08 (Portfolio Limit Breach):**
- Consequence: Immediate halt. Portfolio exposure must be reduced.
- Recovery: After exposure is reduced to within 100% limit, human authorization to resume.
- Position management: Mandatory position reduction.

**KS-T09 (Technology Failure):**
- Consequence: Trading halted due to system unreliability.
- Recovery: After system recovery and successful readiness check, RESET_PENDING.
- Position management: Positions held; no changes until system is reliable.

**KS-T10 (Market Circuit Breaker):**
- Consequence: Exchange has halted trading. IIOS aligns with exchange.
- Recovery: When exchange resumes trading, RESET_PENDING. Operator may opt for post-halt session assessment.
- Position management: No changes possible during circuit breaker halt.

---

### E.5 Kill Switch Testing Protocol

**Pre-session test (mandatory):**
1. Issue a simulated KS-T01 signal with DD = 2.1% (above threshold)
2. Verify Kill Switch transitions from ARMED to TRIGGERED to ACTIVE
3. Verify halt signal broadcast to all IIOS layers
4. Issue manual RESET authorization
5. Verify Kill Switch transitions to ARMED
6. Confirm test result: PASS / FAIL
7. If FAIL: do not start session; diagnose and repair Kill Switch

---

## SUPPLEMENT F — ESCALATION FRAMEWORK

### F.1 Escalation Design Principles

The Escalation Framework defines the progressive response structure for risk events of increasing severity. Escalation is not a failure state — it is a feature. A well-designed escalation framework means that risk issues are handled at the appropriate level: minor issues automatically; moderate issues with operator awareness; severe issues with operator intervention; extreme issues with full halt.

Escalation has three dimensions:
1. **Severity escalation:** As risk severity increases, the response intensity increases.
2. **Time escalation:** If a risk condition persists beyond a defined duration, it escalates to the next level.
3. **Frequency escalation:** If a risk condition recurs frequently, it escalates beyond its individual instance severity.

---

### F.2 Escalation Levels

| Level | Name          | Risk State               | Human Involvement    | Response                         |
|-------|---------------|--------------------------|----------------------|----------------------------------|
| E-0   | Informational | INFO threshold           | None required        | Log; dashboard update            |
| E-1   | Warning       | WARNING threshold (75%)  | Optional monitoring  | Telegram notification; monitor   |
| E-2   | Alert         | ALERT threshold (90%)    | Awareness required   | Telegram alert; review dashboard |
| E-3   | Breach        | BREACH threshold (100%)  | Active engagement    | Telegram urgent; position review |
| E-4   | Critical      | CRITICAL threshold (110%)| Immediate action     | Phone/urgent alert; manual review|
| E-5   | Kill Switch   | Kill Switch trigger       | Mandatory            | Kill Switch activated; session halt|

---

### F.3 Escalation Rules

**Severity Escalation:**
- Risk assessment crosses WARNING → E-1 (automatic notification)
- Risk assessment crosses ALERT → E-2 (automatic alert)
- Risk assessment crosses BREACH → E-3 (automatic urgent; position management triggered)
- Risk assessment crosses CRITICAL → E-4 (immediate; pending Kill Switch evaluation)
- Kill Switch trigger condition met → E-5 (Kill Switch activated)

**Time Escalation:**
- E-1 not acknowledged within 10 minutes → auto-escalates to E-2
- E-2 not acknowledged within 5 minutes → auto-escalates to E-3
- E-3 not acknowledged within 3 minutes → auto-escalates to E-4
- E-4 not acknowledged within 1 minute → auto-escalates to E-5 (Kill Switch evaluation)

**Frequency Escalation:**
- Same risk type breaches WARNING 3 times in one session → base level elevated to E-2 for rest of session
- Same risk type breaches ALERT 2 times in one session → tighten threshold by 10% for next session
- Kill Switch triggered twice in 5 sessions → governance review required before next session

---

### F.4 Escalation Routing Matrix

| Risk Type       | E-1               | E-2               | E-3                  | E-4                  | E-5            |
|-----------------|-------------------|-------------------|----------------------|----------------------|----------------|
| Market Risk     | Auto log          | Telegram notify   | Restrict new positions| Reduce by 50%        | Kill Switch    |
| Portfolio Risk  | Auto log          | Telegram notify   | Portfolio review     | Halt new positions   | Kill Switch    |
| Execution Risk  | Auto log          | Telegram alert    | Reduce sizes 25%     | Halt new orders      | Kill Switch    |
| Tail Risk       | Auto log          | Telegram alert    | Reduce sizes 30%     | Halt; assess         | Kill Switch    |
| Technology Risk | System alert      | Telegram alert    | Degraded mode        | Safe mode            | Kill Switch    |
| All other       | Auto log          | Telegram notify   | Operator review      | Escalate to E-4      | Kill Switch    |

---

### F.5 Escalation Communication Protocols

**Telegram Notification Format (E-1):**
[IIOS RISK WARNING]
Level: E-1 WARNING
Risk: {risk_type} ({RT-NN})
Current: {metric_value}
Threshold: {threshold} (75% level)
Time: {HH:MM:SS IST}
Session: {session_date}

**Telegram Alert Format (E-2):**
[IIOS RISK ALERT]
Level: E-2 ALERT
Risk: {risk_type} ({RT-NN})
Current: {metric_value} / {threshold} (ALERT level)
Position affected: {symbol or portfolio}
Suggested action: {action}
Time: {HH:MM:SS IST}

**Kill Switch Notification Format (E-5):**
[KILL SWITCH ACTIVATED]
Trigger: {KS-TNN} - {trigger_name}
Condition: {trigger_condition}
Value: {metric_value}
Time: {HH:MM:SS IST}
Status: TRADING HALTED
Positions: {n_positions} open, {total_exposure} INR
Action required: Human review and authorization to resume

---

### F.6 Post-Escalation Review Requirements

| Escalation Level | Review Requirement                                   | Timeframe          |
|-----------------|------------------------------------------------------|--------------------|
| E-1             | No review required; captured in session summary      | None mandatory     |
| E-2             | Mention in session review                            | Same-session       |
| E-3             | Written explanation and mitigation taken             | Within 24 hours    |
| E-4             | Full written incident report                         | Within 24 hours    |
| E-5 (Kill Switch)| Full kill switch event review; root cause analysis   | Before next session|

---

## SUPPLEMENT G — OPERATIONAL RUNBOOK

### G.1 Runbook Purpose

The IIOS Risk Engine Operational Runbook provides the step-by-step procedures for all routine and non-routine Risk Engine operations. The Runbook is the authoritative operational reference for session operators and system administrators.

The Runbook is organized into four sections:
- Pre-Session Startup Sequence
- Intraday Operations
- Post-Session Processing
- Incident Recovery Procedures

---

### G.2 Pre-Session Startup Sequence

**Target completion: Before 09:10 IST (5 minutes before market open)**

| Step | Time      | Action                                               | Expected Result             | Fallback if Failed               |
|------|-----------|------------------------------------------------------|-----------------------------|----------------------------------|
| 1    | 08:45     | Verify system is running (Docker health check)        | Both containers healthy      | Restart containers               |
| 2    | 08:47     | Check GlobalIntelligence data freshness              | Snapshot < 12 hours old     | Trigger L1 fetch manually        |
| 3    | 08:48     | Check MarketIntelligence regime current              | Regime = today's date        | Trigger L2 cycle                 |
| 4    | 08:50     | Verify broker connectivity (Dhan / fallback)         | Connection status: ACTIVE   | Switch to yfinance fallback      |
| 5    | 08:52     | Load Risk Engine state: policies, thresholds, catalog| All 22 components initialized| Fix failed components; re-init   |
| 6    | 08:53     | Kill Switch test (mandatory)                         | KS test: PASS               | Do NOT start session if FAIL     |
| 7    | 08:54     | Run 14-scenario stress test on empty portfolio       | All 14 scenarios: no errors  | Fix stress engine before start   |
| 8    | 08:55     | Load prior session risk summary                      | Prior summary loaded         | Log warning; proceed             |
| 9    | 08:56     | Validate audit chain integrity                       | Chain: VALID                | Do NOT start if chain INVALID    |
| 10   | 08:57     | Compute REHS                                         | REHS >= NOMINAL (0.75)      | Diagnose degraded components     |
| 11   | 08:58     | Complete readiness checklist CR-01 through OT-07     | All checks PASS              | Degraded mode if marginal; STOP if critical|
| 12   | 08:59     | Set session parameters: drawdown peak = 0            | DD = 0.0%; peak = 0         | Force reset if non-zero          |
| 13   | 09:00     | Publish readiness status to ControlTower (L17)       | Dashboard: GREEN             | Proceed if DEGRADED; abort if RED|
| 14   | 09:05     | Monitor market open (09:15 IST)                      | First quotes received        | Data feed check if no quotes     |
| 15   | 09:15     | First intraday stress run after market open          | SS results updated           | Continue; manual alert if fail   |
| 16   | 09:16     | Confirm Kill Switch ARMED after first trade data     | KS status = ARMED            | Verify; alert if not ARMED       |

---

### G.3 Intraday Operations Schedule

| Time (IST) | Event                              | Risk Engine Action                                     |
|------------|------------------------------------|--------------------------------------------------------|
| 09:15      | Market Open                        | Begin real-time monitoring; first price data           |
| 09:15-09:30| Opening Range                      | Elevated monitoring; volatility typically high         |
| 09:30      | Opening range analysis             | Regime confirmation; scenario probability first update |
| 10:00      | First intraday full stress test    | Run all 14 scenarios; update portfolio risk score      |
| 10:00      | First portfolio monitoring cycle   | Exposure, VaR, correlation update                      |
| 10:30      | Mid-morning check                  | Drawdown check; threshold utilization review           |
| 11:00      | Strategy performance review        | L13 Learning Engine check-in; strategy risk attribution|
| 11:30      | Second intraday stress test        | Run all 14 scenarios; update risk scores               |
| 11:30      | Portfolio monitoring cycle         | Full exposure and VaR update                           |
| 12:00      | Midday operational check           | Check system health; REHS update                       |
| 13:00      | Third intraday stress test         | Run all 14 scenarios                                   |
| 13:00      | Scenario probability update        | Prediction Engine updates for second half of session   |
| 13:30      | Pre-close preparation begins       | Risk gradually tightened for EOD                       |
| 14:30      | Fourth intraday stress test        | Run all 14 scenarios                                   |
| 14:30      | Pre-close risk assessment          | Full portfolio risk review; position management plan   |
| 15:00      | Final stress test                  | Last scenario run before close                         |
| 15:00      | Pre-close exposure reduction       | Begin reducing positions per EOD policy                |
| 15:15      | Final trade approval window        | Last window for new positions (if any)                 |
| 15:25      | No new positions                   | Risk Engine stops approving new positions              |
| 15:30      | Market Close                       | Final P&L locked; session stats computed               |
| 15:30      | Post-session processing begins     | See G.4 below                                          |

---

### G.4 Post-Session Processing (12 steps)

| Step | Action                                                | Expected Result                          |
|------|-------------------------------------------------------|------------------------------------------|
| 1    | Reconcile positions with broker                       | Broker positions match IIOS records      |
| 2    | Compute final session P&L and drawdown                | Session P&L recorded; max DD confirmed   |
| 3    | Run post-session VaR backtest                         | VaR exceedance: 0 or 1 this session      |
| 4    | Compare stress scenarios to actual outcomes           | Scenario accuracy recorded               |
| 5    | Compute session RQS score                             | RQS recorded in session summary          |
| 6    | Generate governance report                            | Full governance report ready for review  |
| 7    | Close audit chain for session                         | Chain closed; integrity hash generated   |
| 8    | Archive session risk records                          | Archive write confirmed                  |
| 9    | Archive session stress test results                   | All 14+ scenario results archived        |
| 10   | Update Learning Engine with risk outcomes             | Risk outcome data delivered to L13       |
| 11   | Telegram session summary to operator                  | Summary sent; operator confirms receipt  |
| 12   | Dashboard: session summary page published             | ControlTower dashboard updated           |

---

### G.5 Incident Recovery Procedures

**IRP-01: Drawdown Monitor Failure**

*Symptoms:* RC-07 Drawdown Monitor not updating; session P&L stuck; REHS falling.

*Steps:*
1. Attempt component restart (RC-07 restart procedure)
2. If restart fails: manually compute current P&L from broker positions and last known state
3. If P&L calculation shows DD > 1.5%: manually trigger Kill Switch (KS-T06 Manual)
4. If DD < 1.5%: operate in degraded mode with conservative position sizes (50% of normal)
5. Alert operator immediately; escalate to E-4
6. Resolve and restart before next position approval
7. Document incident for governance review

**IRP-02: Kill Switch Failure**

*Symptoms:* Kill Switch Manager (RC-14) not responding; KS state unknown; REHS critical.

*Steps:*
1. Immediately halt ALL trading (manual decision: no new orders)
2. Do NOT assume Kill Switch is armed
3. Alert operator at highest urgency
4. Attempt Kill Switch Manager restart
5. Run Kill Switch test (step 6 of startup sequence)
6. If test FAILS: do not resume trading; investigate root cause
7. If test PASSES: resume with elevated monitoring
8. Document incident; post-session review mandatory

**IRP-03: Audit Chain Corruption**

*Symptoms:* Hash chain validation fails; hash mismatch detected; RC-19 reports chain error.

*Steps:*
1. Do NOT delete or modify any audit records
2. Alert operator; escalate to E-4
3. Identify the first record with a broken chain
4. Determine if corruption is storage failure or logic error
5. If storage failure: restore from backup; re-validate
6. If logic error: identify defective record; quarantine; restart from last valid record
7. Re-validate entire chain after repair
8. Document incident; retain all evidence for forensic review

**IRP-04: Data Feed Failure**

*Symptoms:* Price data not updating; KS-T04 triggered; Risk Analyzer receiving stale data.

*Steps:*
1. Kill Switch activates automatically (KS-T04)
2. Attempt data feed reconnection (primary: Dhan)
3. If Dhan unavailable: switch to yfinance fallback (automatic in IIOS)
4. Validate data quality after failover (compare Dhan/yfinance last known prices)
5. Once data feed is confirmed operational: operator authorizes Kill Switch reset
6. Resume operations with data feed health monitoring elevated
7. Document incident

**IRP-05: VaR Engine Failure**

*Symptoms:* VaR computation errors; RC-10 reporting failures; REHS degraded.

*Steps:*
1. Enter conservative mode: assume VaR = BREACH level; halt new positions
2. Attempt RC-10 restart
3. If restart succeeds: run VaR test computation; validate result
4. If restart fails: substitute parametric VaR as emergency fallback (more conservative)
5. Alert operator; escalate to E-3
6. Do not approve new positions until either VaR Engine restored or parametric fallback validated

**IRP-06: Stress Testing Engine Failure**

*Symptoms:* RC-08 not producing results; stress test errors at scheduled checkpoints.

*Steps:*
1. Attempt RC-08 restart
2. If restart fails: apply conservative worst-case assumption (assume SS-02 conditions apply)
3. Under SS-02 assumption: reduce all positions by 30%; halt new positions
4. Alert operator
5. Restore RC-08 before next scheduled stress test; validate with test run

**IRP-07: Correlation Engine Failure**

*Symptoms:* RC-06 not producing correlation matrix; VaR Engine receiving errors; portfolio risk assessment degraded.

*Steps:*
1. Switch VaR computation to assume stress-state correlation (all correlations = 0.90)
2. This is conservative: portfolio VaR will be higher than reality
3. Continue trading at reduced position sizes (50% of normal)
4. Alert operator
5. Attempt RC-06 restart; validate correlation matrix before restoring normal operation

**IRP-08: Risk Registry Failure**

*Symptoms:* RC-01 not accepting writes; risk records not being created; REHS critical.

*Steps:*
1. Halt new trading immediately — risk assessments cannot be recorded
2. Attempt RC-01 restart with journal replay
3. If restart fails: promote read-only replica (if available) to primary
4. If no replica: do not trade; wait for RC-01 recovery
5. Alert operator; escalate to E-5 consideration
6. Document: all risk actions taken during failure must be reconciled post-recovery

---

### G.6 Weekly Maintenance Checklist

| Task                                       | Frequency | Action                                    |
|--------------------------------------------|-----------|-------------------------------------------|
| VaR model validation                       | Weekly    | Compare VaR predictions to actual losses  |
| Stress scenario review                     | Weekly    | Are scenarios still relevant?             |
| Threshold review                           | Weekly    | Are thresholds appropriate for regime?    |
| Kill Switch log review                     | Weekly    | Review any KS activations                 |
| Correlation matrix health check            | Weekly    | Are correlations stable? Any anomalies?   |
| Governance report review                   | Weekly    | Review operator acknowledgment            |
| Data archive integrity check               | Monthly   | Validate archive; check disk space        |
| Audit chain integrity check                | Monthly   | Full chain re-validation                  |
| Policy review                              | Monthly   | Review active policies; any updates?      |
| Risk Engine calibration review             | Monthly   | Is RQS >= GOOD? Any systematic issues?    |
| Strategy risk attribution review           | Monthly   | Which strategies are contributing most risk|
| Full stress scenario recalibration         | Quarterly | Update scenario parameters                |

---

## SUPPLEMENT H — COMPREHENSIVE GLOSSARY AND GOVERNING DESIGN RECORDS

### H.1 Comprehensive Glossary

**Accuracy (RQD-01):** The degree to which risk measurements correctly reflect actual risk present in the portfolio. Measured post-session by comparing predicted loss metrics to actual outcomes.

**Active Risk:** Risk that is currently being managed by the Risk Engine; a risk record in MONITORING or MITIGATION_REQUIRED state.

**Alpha:** Excess return generated by a strategy above a benchmark. In the IIOS, risk management constrains alpha-seeking to protect capital.

**ALERT Level:** The threshold level at which 90% of a risk limit has been consumed; triggers operator awareness notifications.

**Audit Chain:** The cryptographic hash chain maintained by the Risk Audit Manager (RC-19) that links all audit records sequentially, preventing retroactive modification.

**Backtest:** Retrospective evaluation of a model or strategy against historical data. VaR backtesting compares predicted VaR to actual losses.

**BREACH Level:** The threshold level at which a risk limit has been reached (100%); triggers mandatory response actions.

**Behavioral Risk (RT-11):** Risk arising from systematic algorithmic behavioral patterns in the IIOS that could lead to predictable or self-destructive behavior (herding, over-trading, anchoring).

**Beta:** The sensitivity of a portfolio or position to movements in the market index. A beta of 1.2 means a 1% market move produces approximately a 1.2% portfolio move.

**Black Swan (RT-24):** An unprecedented, unpredicted event with extreme impact that falls outside the range of historical experience. Not modelable from historical data.

**Calibration:** The process of adjusting risk model parameters to ensure that probability estimates are accurate. A well-calibrated VaR model produces approximately the correct exceedance rate.

**Capital Protection Level:** The current operational mode of the Capital Protection Manager (RC-15): STANDARD, ELEVATED, DEFENSIVE, PROTECTIVE, or HALT.

**Cascade Failure:** A failure mode where one component's failure causes failure in dependent components, leading to a chain reaction.

**Circuit Breaker:** An exchange-imposed halt on trading when an index moves beyond a defined threshold (NSE: Level 1 at -5%, Level 2 at -10%).

**Concentration Risk (RT-21):** Risk arising from excessive exposure to a single instrument, sector, or factor.

**Conditional VaR (CVaR):** Also known as Expected Shortfall (ES). The expected loss given that the loss exceeds the VaR threshold. CVaR >= VaR always.

**Conservative Mode:** A fallback operating mode where position sizes are reduced and approvals are more restrictive, used when components are degraded or risk data is uncertain.

**Correlation (RC-06):** The statistical measure of co-movement between two instruments. Ranges from -1.0 (perfect inverse) through 0.0 (independent) to +1.0 (perfect co-movement).

**Correlation Breakdown:** The phenomenon where asset correlations approach 1.0 during market stress, eliminating the diversification benefit precisely when it is most needed.

**CRITICAL Level:** The threshold level at which 110% of a risk limit has been consumed; triggers immediate escalation and Kill Switch consideration.

**Counterparty Risk (RT-12):** The risk that the broker, exchange, or clearinghouse fails to fulfill its obligations.

**Decision Risk (RT-10):** Risk arising from incorrect decisions by the Decision Engine: commission bias, threshold miscalibration, or debate dominance.

**Diversification:** The practice of spreading exposure across uncorrelated instruments, sectors, and strategies to reduce portfolio risk.

**Diversification Ratio:** The ratio of portfolio VaR to the sum of individual position VaRs. Less than 1.0 indicates diversification benefit.

**Drawdown:** The decline in portfolio value from a peak to a subsequent trough. Session drawdown is measured from the session peak P&L.

**Escalation Framework:** The progressive response structure for risk events of increasing severity; ranges from E-0 (informational) to E-5 (Kill Switch).

**Event Risk (RT-25):** Risk arising from specific discrete events that cause sudden large price movements.

**EWMA (Exponentially Weighted Moving Average):** A calculation method that gives more weight to recent observations. Used in the Correlation Engine and volatility computation.

**Execution Risk (RT-07):** Risk that a trade will not be executed as intended, resulting in worse-than-expected prices, missed fills, or partial fills.

**Expected Shortfall (ES):** See Conditional VaR.

**Exposure:** The amount of capital at risk due to open positions. See Gross Exposure and Net Exposure.

**Exposure Engine (RC-05):** The Risk Engine component responsible for computing and maintaining portfolio exposure across all dimensions.

**Fat Tail:** The property of financial return distributions where extreme events occur more frequently than a normal (Gaussian) distribution would predict. Financial returns are fat-tailed.

**Gross Exposure:** The sum of the absolute values of all position market values. Does not offset long and short positions.

**Governing Design Record (GDR):** A formal, ratified architectural decision that is immutable once ratified. Describes the decision, its rationale, and its implications.

**Hash Chain:** A sequence of records where each record includes the hash of the previous record, creating a tamper-evident chain.

**Herfindahl-Hirschman Index (HHI):** A measure of concentration. HHI = sum of squared portfolio weight shares. HHI = 1.0 for a perfectly concentrated portfolio.

**Idiosyncratic Risk:** Risk specific to individual instruments or companies; can be reduced through diversification.

**INFO Level:** The threshold level at which 50% of a risk limit has been consumed; logged only, no action required.

**Kill Switch (RC-14):** The unconditional trading halt mechanism. Activates when any of 10 defined trigger conditions is met.

**Kill Switch Matrix:** The complete documentation of all Kill Switch triggers, their conditions, consequences, and recovery procedures.

**Kill Switch Manager (RC-14):** The Risk Engine component responsible for monitoring Kill Switch triggers and managing Kill Switch state.

**Latency SLA:** Service Level Agreement for maximum acceptable processing time for a Risk Engine computation. Measured by component.

**Left-Tail:** The left side of the return distribution; represents losses. Tail risk focuses on the extreme left tail.

**Liquidity Risk (RT-06):** Risk that a position cannot be exited at a desired price within a desired timeframe without causing significant market impact.

**Macro Risk (RT-15):** Risk arising from large-scale macroeconomic changes affecting the broad market environment.

**Market Risk (RT-01):** Risk of loss due to adverse movements in market prices.

**Model Risk (RT-08):** Risk that the mathematical models used by the IIOS are incorrect, miscalibrated, or misapplied.

**Monte Carlo VaR:** VaR computed by simulating thousands of return paths using stochastic models. Computationally intensive but can capture complex non-linear dependencies.

**NAV (Net Asset Value):** The current total value of the portfolio, used as the base for percentage-based risk limits.

**Net Exposure:** Long positions minus short positions in currency terms. Measures directional bias.

**Normal Distribution:** A symmetric bell-shaped probability distribution. Financial returns deviate from normality (fat tails, negative skew), so purely parametric models based on normality understate risk.

**Operational Risk (RT-20):** Risk arising from inadequate or failed internal processes, people, or systems.

**Parametric VaR:** VaR computed using the assumption that returns follow a normal distribution. Computationally simple but underestimates tail risk.

**PIT (Point-In-Time):** An assessment that reflects the state of the world at a specific moment in time. All risk assessments in IIOS are PIT assessments — they reflect current conditions, not average conditions.

**Political Risk (RT-16):** Risk of loss arising from political events, policy changes, or geopolitical conflicts.

**Portfolio Risk (RT-02):** Aggregate risk arising from the combined portfolio of all open positions; modified by correlations between positions.

**Position Risk (RT-03):** Risk arising from a single open position.

**Prediction Risk (RT-09):** Specific risk from reliance on Prediction Engine forecasts; encompasses forecast accuracy risk, calibration risk, and overconfidence risk.

**REHS (Risk Engine Health Score):** The composite measure of operational health of the Risk Engine; computed by RC-22 Risk Health Manager.

**Recovery Pipeline (RP-10):** The Risk Processing Pipeline for controlled recovery from component failures.

**Regulatory Risk (RT-17):** Risk arising from changes in laws, regulations, or exchange rules.

**Residual Risk:** Risk remaining after all mitigation measures have been applied.

**Risk Appetite:** The amount and type of risk the IIOS is willing to accept in pursuit of its objectives.

**Risk Capacity:** The maximum risk the IIOS can absorb without threatening continued operation.

**Risk Catalog (RC-02):** The controlled vocabulary and classification authority for all risk types in the IIOS.

**Risk Constitution:** The highest-authority governance document for the Risk Engine; contains 112 inviolable rules.

**Risk Engine Health Score (REHS):** See REHS.

**Risk Quality Score (RQS):** A weighted composite of 12 quality dimensions; measures how well the Risk Engine is performing its function.

**Risk Record:** A structured data record capturing a detected risk event, its classification, measurement, and lifecycle state.

**Risk Registry (RC-01):** The master record of all active, acknowledged, and archived risk records.

**Risk Tolerance:** The acceptable variation in outcomes within the risk appetite framework.

**RQS:** See Risk Quality Score.

**Scenario Engine (RC-09):** The Risk Engine component responsible for generating, maintaining, and evaluating risk scenarios.

**Sector Risk (RT-04):** Risk of concentrated exposure to a single economic sector.

**Sensitivity (RQD-02):** The degree to which the Risk Engine detects risk conditions early enough to enable effective mitigation.

**Session Drawdown:** The maximum percentage decline in portfolio value from the session's highest P&L to any subsequent lower P&L.

**Slippage:** The difference between the intended execution price and the actual execution price.

**Strategy Risk (RT-26):** Risk arising from the trading strategies themselves: overfitting, regime change, capacity limits, or strategy correlation.

**Stress Scenario:** A structured scenario representing an extreme but plausible market event used to evaluate portfolio resilience.

**Stress Testing Engine (RC-08):** The Risk Engine component responsible for running stress scenarios against the current portfolio.

**Systemic Risk:** Risk that affects the entire market simultaneously; cannot be reduced by diversification within the market.

**Tail Risk (RT-23):** Risk arising from extreme outcomes in the tail of the probability distribution.

**Tail Risk Engine (RC-11):** The Risk Engine component specifically focused on measuring and monitoring tail risk.

**Technology Risk (RT-18):** Risk arising from failure of technology systems supporting the IIOS.

**Threshold:** A numerical level that triggers a defined response when a risk metric exceeds it.

**Time-in-Drawdown:** The duration a strategy or portfolio has been in a drawdown state. Used for strategy governance.

**VaR (Value at Risk):** A statistical measure that quantifies the maximum expected loss at a given confidence level over a defined time horizon.

**VaR Engine (RC-10):** The Risk Engine component responsible for computing VaR and CVaR for the portfolio.

**VaR Exceedance:** An event where the actual portfolio loss exceeds the predicted VaR for that day. Exceedance rate should be approximately (1 - confidence) if the VaR model is well-calibrated.

**Volatility:** The statistical measure of the magnitude of price or value fluctuations over time.

**WARNING Level:** The threshold level at which 75% of a risk limit has been consumed; triggers optional monitoring notification.

---

### H.2 Governing Design Records

**GDR-RSK-001 — Capital Preservation is the Primary Mandate**

*Decision:* Capital preservation takes precedence over return maximization in all Risk Engine decisions.

*Rationale:* The mathematical asymmetry of losses (a 50% loss requires a 100% gain to recover) makes capital preservation a mathematical necessity for long-term operational viability. An IIOS that survives a decade with modest but consistent returns outperforms one that alternates between exceptional gains and catastrophic losses.

*Implications:*
1. Risk Engine rejections override Decision Engine approvals when capital is at risk
2. Conservative calibration is the default; permissive calibration requires explicit governance approval
3. All Risk Engine components exist in service of capital preservation
4. This GDR cannot be modified or superseded by any per-session configuration

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

**GDR-RSK-002 — Independent Risk Evaluation**

*Decision:* Risk Engine assessments are fully independent of the Decision Engine's recommendation, the Prediction Engine's confidence, or the strategy's historical performance.

*Rationale:* If the Risk Engine's approval is correlated with the Decision Engine's enthusiasm, it provides no independent check. The value of risk management comes entirely from its independence. A system where "high confidence in prediction = lower risk scrutiny" provides less protection precisely when it is most needed.

*Implications:*
1. The Risk Engine does not have access to the Decision Engine's vote tally or confidence score
2. High-performing strategies receive identical risk scrutiny to new strategies
3. A unanimous Decision Engine approval with high confidence that exceeds a risk limit is still blocked
4. Model performance history does not modify risk thresholds

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

**GDR-RSK-003 — Kill Switch Authority is Unconditional**

*Decision:* When Kill Switch trigger conditions are met, the Kill Switch activates unconditionally. No algorithm, no score, and no human instruction can prevent activation.

*Rationale:* The Kill Switch's value as a safety mechanism depends entirely on its unconditional nature. A Kill Switch that can be overridden by a sufficiently confident algorithm is not a Kill Switch — it is a suggestion. The cases where the Kill Switch is most needed (extreme market stress, cascading failures, unanticipated events) are exactly the cases where algorithmic confidence may be at its highest and most misleading.

*Exception:* Human operators may override the Kill Switch only in MANUAL_OVERRIDE state for specific, annotated, non-algorithmic reasons. This preserves human authority while preventing algorithmic bypass.

*Implications:*
1. Kill Switch activation logic is deterministic and transparent
2. No "confidence score" pathway can suppress a Kill Switch trigger
3. Kill Switch testing is mandatory every session
4. All Kill Switch activations are permanently logged and never purged

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

**GDR-RSK-004 — Audit Before Action**

*Decision:* All risk management actions are logged in the audit chain before they are executed.

*Rationale:* Post-hoc audit logging can be manipulated or lost if the system fails between action and logging. Pre-action logging ensures that every action is accountable before it affects the portfolio.

*Implications:*
1. Risk assessment results are written to audit before being communicated to the Decision Engine
2. Kill Switch activation is written to audit before the halt signal is broadcast
3. Any component failure between audit-write and action execution is resolved by replaying from audit
4. Audit write failure blocks the action

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

**GDR-RSK-005 — Risk Records Are Immutable**

*Decision:* Risk records and audit records are immutable once finalized. No process may modify or delete a risk record.

*Rationale:* The integrity of the risk management system depends on the completeness and accuracy of its historical record. A system that can modify its own history cannot be trusted to have accurately assessed past risks. This is both a security requirement and a governance requirement.

*Implications:*
1. The Risk Archive Manager has no delete or update operations for finalized records
2. Corrections are handled by creating new records with references to the original
3. Database architecture for risk storage uses append-only writes
4. Attempts to modify or delete risk records are treated as security incidents

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

**GDR-RSK-006 — Conservative Calibration by Default**

*Decision:* When risk measurement involves choices between methodologies, the more conservative (higher risk estimate) methodology is used.

*Rationale:* Risk measurement uncertainty should resolve in favor of capital preservation. If the historical simulation VaR and the parametric VaR disagree, the higher value is used. If two exposure calculations produce different results, the higher value is used. This prevents systematic underestimation of risk.

*Implications:*
1. VaR methodology: historical simulation (not parametric normality assumption)
2. Correlation: stress-period correlations applied in uncertain regimes
3. Tail risk: fat-tail adjusted estimates always; no normality assumption in tails
4. Exposure: pending orders counted at full size until confirmed filled

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

**GDR-RSK-007 — Human Override is Legitimate and Monitored**

*Decision:* Human operators may override Risk Engine decisions (except Kill Switch during ACTIVE state). All overrides are logged, audited, and reviewed.

*Rationale:* Algorithmic risk management is not infallible. Human judgment is necessary for novel situations, extraordinary events, and cases where the Risk Engine's models have not captured a specific market condition. Human override capability preserves the system's ability to handle situations outside its training distribution.

*Counter-balance:* Overrides are not free. Every override creates an audit record, is visible in governance reporting, and is reviewed. Systematic override patterns trigger governance review.

*Implications:*
1. Override interface requires a mandatory reason field
2. All overrides are included in daily governance reporting
3. Operators who frequently override risk rejections are flagged for review
4. No override may circumvent the Kill Switch in ACTIVE state

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

**GDR-RSK-008 — Risk Assessment Never Authorizes Trades**

*Decision:* The Risk Engine assesses and constrains investment actions. It never authorizes, recommends, or initiates them.

*Rationale:* The Risk Engine is a guardian, not an advisor. Conflating risk management with investment recommendation creates a fundamental conflict of interest — a risk engine that wants to see trades approved (to validate its own utility) will be systematically biased toward permissiveness. The Risk Engine's role is purely constraining: it sets the boundaries within which investment decisions occur.

*Implications:*
1. The Risk Engine's output is: APPROVED / REDUCED / REJECTED — never "this looks like a good trade"
2. The Risk Engine has no visibility into the potential upside of a trade; it evaluates downside only
3. Risk Engine personnel have no performance targets tied to trade approval rates
4. The Risk Engine's quality metrics (RQS) do not include trade volume or P&L

*Ratified:* Yes — IIOS-RSK-ENG-ARCH-001

---

## APPENDIX — WORKED RISK EXAMPLES

### WE-01 — Pre-Trade Risk Assessment: TATASTEEL Long

**Scenario:** The Decision Engine (L10) proposes a long position in TATASTEEL. The Risk Engine (RP-01 Decision-to-Risk Pipeline) evaluates it.

**Input Context:**
- Proposed: Long 200 shares TATASTEEL @ 160 INR (total: 32,000 INR)
- Current portfolio NAV: 500,000 INR
- Current session P&L: +2,000 INR (drawdown: 0%)
- VIX India: 16.5 (normal)
- Current gross exposure: 280,000 INR (56% of NAV)
- Sector (Metals): current exposure 40,000 INR (8% of NAV)

**Step 1 — RC-03 Risk Analyzer: Classification**
- RT-01 Market Risk: price direction uncertainty; Metals sector in moderate volatility
- RT-03 Position Risk: position = 32,000 / 500,000 = 6.4% of NAV
- RT-04 Sector Risk: Metals after this trade = 72,000 / 500,000 = 14.4% (within limit)
- RT-07 Execution Risk: Metals is liquid; EQS historical = 0.87 (GOOD)
- RT-09 Prediction Risk: Price prediction (PT-01) confidence for TATASTEEL = 0.72 (GOOD)

**Step 2 — RC-04 Risk Scoring Engine: Scoring**

| Risk Type | Severity Score | Weight | Contribution |
|-----------|----------------|--------|--------------|
| RT-01     | 0.30 (moderate)| 0.40   | 0.12         |
| RT-03     | 0.20 (low)     | 0.25   | 0.05         |
| RT-04     | 0.15 (low)     | 0.20   | 0.03         |
| RT-07     | 0.15 (low)     | 0.10   | 0.015        |
| RT-09     | 0.25 (moderate)| 0.05   | 0.013        |

Trade Risk Score (TRS) = 0.12 + 0.05 + 0.03 + 0.015 + 0.013 = 0.228 (LOW-MODERATE)

**Step 3 — RC-05 Exposure Engine: Exposure Check**
Post-trade gross exposure: 280,000 + 32,000 = 312,000 INR = 62.4% of NAV
Gross exposure limit: 100% NAV = 500,000 INR
Utilization post-trade: 62.4% → WARNING level is 75% (375,000). Still in INFO band.

**Step 4 — RC-10 VaR Engine: Incremental VaR**
Portfolio VaR (95%, 1-day) before trade: 3,200 INR (0.64% NAV)
Incremental VaR for 32,000 TATASTEEL at beta 1.1: +320 INR
Portfolio VaR post-trade: 3,520 INR (0.70% NAV)
VaR limit (95%): 1.0% NAV = 5,000 INR
Utilization: 70.4% → INFO band.

**Step 5 — RC-13 Risk Threshold Manager**
Session drawdown: 0.0% → GREEN
Gross exposure utilization: 62.4% → INFO (50% level: 50%; INFO: < 75%)
Portfolio VaR utilization: 70.4% → INFO
Sector concentration (Metals 14.4%): INFO (limit 40%)
Position concentration (6.4%): INFO (limit 15%)
Overall threshold status: INFO → NO_ACTION

**Step 6 — RC-15 Capital Protection Manager**
Protection Level: STANDARD (no active protection elevation)
No size reduction required.

**Step 7 — RC-19 Risk Audit Manager**
Audit record created: AUD-RSK-20260703-00000247
Inputs hash: SHA-256({TATASTEEL, 200, 160, 500000, ...})
Assessment: TRS = 0.228; all thresholds INFO; APPROVED
Action hash: SHA-256(assessment + APPROVED + sizing)
Chain hash: SHA-256(prior_hash + audit_id + action_hash)

**Decision: APPROVED — full size (200 shares)**

Total pipeline time: 187ms (within 500ms SLA)

---

### WE-02 — Kill Switch Activation: Daily Loss Threshold

**Scenario:** Session is proceeding normally. Multiple strategies have entered positions. An adverse market move causes rapid drawdown.

**Timeline:**

09:15 IST — Market open; portfolio 3 positions; NAV 500,000 INR; initial exposure 180,000 INR.

10:23 IST — NIFTY suddenly drops 1.8% on negative global news. Three portfolio positions all down.

10:23:15 — RC-07 Drawdown Monitor update:
Session P&L: -6,200 INR
Session peak P&L: +1,800 INR (achieved at 10:15)
Session drawdown = (1,800 + 6,200) / 500,000 = 1.6%
Threshold check: ALERT (90% of 2.0% = 1.8%... actually 1.6% is at ALERT level (80% of 2.0%))
E-2 ALERT sent to operator via Telegram at 10:23:16.

10:24:30 IST — Further selling; NIFTY down 2.3% from session open.

10:24:32 — RC-07 Drawdown Monitor update:
Session P&L: -10,400 INR
Session peak: +1,800 INR
Session drawdown = 12,200 / 500,000 = 2.44%
BREACH threshold (2.0%) confirmed.
KS-T01 signal sent to RC-14 Kill Switch Manager.

10:24:32 + 42ms — RC-14 Kill Switch Manager: KS-T01 trigger validated. DD = 2.44% > 2.0%.
Kill Switch: TRIGGERED → ACTIVE.

10:24:32 + 63ms — Broadcast: KILL_SWITCH_ACTIVE to all 17 IIOS layers.
L10 Decision Engine: pending proposals rejected.
L11 Execution Engine: no new orders.

10:24:32 + 89ms — RC-19 Risk Audit: KSE-T01-20260703-0001 written.

10:24:32 + 110ms — L17 ControlTower: dashboard RED. Telegram:
[KILL SWITCH ACTIVATED]
Trigger: KS-T01 - Daily Loss Threshold
Condition: Portfolio DD >= 2.0%
Value: DD = 2.44% (loss -10,400 INR)
Time: 10:24:32 IST
Status: TRADING HALTED

Total time from trigger to halt broadcast: 63ms (target < 200ms: PASS)

**Operator Response:**
10:31:00 — Operator reviews. Market stabilizing. Decides to not resume session (drawdown already at limit).
10:31:45 — Operator issues MANUAL_CLEAR with reason: "Session ended; DD limit hit; no recovery today."
Kill Switch transitions: ACTIVE → RESET_PENDING → ARMED (for next session).

**Post-event:** Kill Switch review completed before next session. Root cause: concentrated exposure across correlated positions during rapid market move. Mitigation: improve sector correlation monitoring.

---

### WE-03 — Stress Test Discovery: Pre-Session

**Scenario:** Pre-session startup. Session from previous day left 3 positions open. Stress test at 09:00.

**Portfolio before session:**
- Position A: RELIANCE 100 shares @ 2,950 INR = 295,000 INR (49% of NAV)
- Position B: TCS 50 shares @ 4,100 INR = 205,000 INR (34.2% of NAV)
- Position C: AXISBANK 300 shares @ 1,200 INR = 360,000 INR (60.0% of NAV)

Wait — this portfolio has gross exposure = 860,000 INR against assumed NAV 600,000 INR = 143.3% exposure. This is an anomaly from prior session (illustrative).

**Step 1 — Stress test SS-08 (Single Name Collapse):**
Largest position: AXISBANK 360,000 INR (60% of NAV)
SS-08 parameters: Largest position -20%
Impact: 360,000 x 0.20 = 72,000 INR = 12% of NAV

12% exceeds the SS-08 action threshold (1.0% NAV) by a large margin. SS-08 result: CRITICAL.

**Step 2 — Stress test SS-02 (Market Circuit Breaker 10%):**
Portfolio beta ~ 1.15
Impact: NAV x 1.15 x 0.10 = 600,000 x 1.15 x 0.10 = 69,000 INR = 11.5% NAV
SS-02 result: CRITICAL.

**Risk Engine response:**
- Stress test reveals catastrophic position concentration in AXISBANK (60% NAV)
- RC-15 Capital Protection Manager: HALT level activated immediately
- No new positions permitted until exposure reduced
- Operator Telegram:

[RISK ALERT: STRESS TEST BREACH]
Level: E-3 BREACH
Scenario: SS-08 Single Name Collapse
AXISBANK exposure: 60% NAV
SS-08 impact: 12% NAV (limit: 1.0%)
Action required: Reduce AXISBANK position significantly before session start
Status: New positions blocked

**Operator action:** Instructs reduction of AXISBANK to max 15% NAV before market open. Position reduction orders placed immediately at 09:05. By 09:15, AXISBANK = 90,000 INR (15% NAV). Stress tests re-run; all pass.

---

### WE-04 — VaR Exceedance Handling

**Scenario:** Monday session. Prior Friday, portfolio VaR (95%, 1-day) was computed as 4,800 INR (0.96% of 500,000 NAV). Friday was the 250th session in the VaR history.

**Monday result:** NIFTY drops 2.8% on surprise Fed announcement over weekend. Portfolio loss: 13,200 INR = 2.64% NAV.

**VaR Exceedance detection:**
At session close: Actual loss (13,200) > VaR prediction (4,800)
VaR exceedance recorded.

**Impact on VaR model:**
Rolling 250-session VaR exceedance rate:
Prior exceedances in 250 sessions: 11 (4.4%; target 5% at 95% confidence)
Add this exceedance: 12 in 250 (4.8%)
Status: Within acceptable range (3% to 8%)

**VaR backtest results:**
Daily VaR exceedance rate: 4.8% — within acceptable (not a calibration failure)

**But the severity is flagged:**
Actual loss = 2.75x the VaR prediction. Severity of exceedance is high.
RC-21 Risk Analytics Manager flags: "High-severity VaR exceedance detected. Weekend event type. Consider adding SS-15 (Weekend Global Shock) scenario to catalogue."

**Follow-up:**
Governance review recommends: Add SS-15 scenario; review VaR horizon (1-day VaR may not capture weekend gap risk). Scenario Engine creates SCN-WKND_SHOCK candidate for governance approval.

---

### WE-05 — Correlation Breakdown Detection

**Scenario:** Normal session. Market shows signs of stress. Correlation Engine (RC-06) detects correlation regime change.

**Detection:**
At 11:15 IST, RC-06 monitoring detects:
Average rolling 20-day correlation (portfolio): 0.42 (normal)
EWMA correlation (lambda=0.94) current: 0.67
EWMA correlation with stress lambda (0.75): 0.79
Correlation regime change detected: ELEVATED → approaching STRESS threshold (0.90)

**Risk Engine response:**
1. Risk Analyzer (RC-03) creates RT-22 Correlation Risk record
2. Risk Scoring Engine computes severity: 0.69 (elevated — ALERT)
3. Threshold Manager: ALERT level (within soft thresholds)
4. Portfolio Limit Manager: rechecks portfolio VaR with updated correlation matrix
5. VaR increases from 4,200 INR to 5,800 INR (38% increase)
6. New VaR (5,800) = 1.16% NAV — slightly above the 1.0% VaR limit
7. Threshold Manager: ALERT on portfolio VaR (90% of 2% stress threshold)

**Actions:**
- New position approvals restricted to small sizes (25% of normal maximum)
- Operator notified: E-2 ALERT
- Telegram: "Portfolio correlation rising (0.79). VaR elevated. Restricting new positions."
- Stress tests run with updated correlation matrix
- Session ends at 0.67 average correlation; restriction maintained

**Post-session:**
Correlation regime change is documented in session risk summary. Learning Engine (L13) receives correlation state as input for next-session risk model calibration.

---

### WE-06 — Complete Risk Quality Score Computation

**Scenario:** End of session. RC-04 Risk Scoring Engine computes the session's final RQS.

**Dimension scores:**

| Dimension    | Code   | Score | Weight | Contribution |
|--------------|--------|-------|--------|--------------|
| Accuracy     | RQD-01 | 0.91  | 0.20   | 0.182        |
| Sensitivity  | RQD-02 | 0.88  | 0.15   | 0.132        |
| Timeliness   | RQD-03 | 0.95  | 0.12   | 0.114        |
| Coverage     | RQD-04 | 1.00  | 0.10   | 0.100        |
| Consistency  | RQD-05 | 0.87  | 0.10   | 0.087        |
| Robustness   | RQD-06 | 0.83  | 0.08   | 0.066        |
| Reliability  | RQD-07 | 0.97  | 0.08   | 0.078        |
| Explainability| RQD-08| 0.92  | 0.05   | 0.046        |
| Traceability | RQD-09 | 1.00  | 0.05   | 0.050        |
| Governance   | RQD-10 | 0.85  | 0.03   | 0.026        |
| Auditability | RQD-11 | 1.00  | 0.02   | 0.020        |
| Cap Protect  | RQD-12 | 0.90  | 0.02   | 0.018        |

RQS = sum of all contributions = 0.182 + 0.132 + 0.114 + 0.100 + 0.087 + 0.066 + 0.078 + 0.046 + 0.050 + 0.026 + 0.020 + 0.018

RQS = 0.919

**Tier:** EXCELLENT (0.88 - 1.00)

**Session summary:** Risk Engine operated at EXCELLENT quality for the session. All pre-trade assessments completed within SLA (99.2%). Kill Switch was not triggered. No threshold BREACHes. VaR within limits. Full audit chain intact.

---

## DOCUMENT SUMMARY

### DS.1 Document Metrics

| Metric                    | Value                                    |
|---------------------------|------------------------------------------|
| Document Code             | IIOS-RSK-ENG-ARCH-001                    |
| Series                    | IIOS Architecture Document Series        |
| Version                   | 1.0 (RATIFIED)                           |
| Document Date             | 2026-07-03                               |
| IIOS Layers Covered       | L6 (CapitalRisk), L7 (RiskControl), L8 (MarketSim), L9 (RiskGuardian) |
| Risk Types Defined        | 26 (RT-01 through RT-26)                |
| Components Designed       | 22 (RC-01 through RC-22)                 |
| Services Defined          | 14 (RS-01 through RS-14)                 |
| Pipelines Defined         | 10 (RP-01 through RP-10)                 |
| Quality Dimensions        | 12 (RQD-01 through RQD-12)              |
| Constitutional Rules      | 112 (across 16 categories RC-A to RC-P) |
| Kill Switch Triggers      | 10 (KS-T01 through KS-T10)             |
| Stress Scenarios          | 14 (SS-01 through SS-14)                |
| Governing Design Records  | 8 (GDR-RSK-001 through GDR-RSK-008)    |
| Lifecycle Stages          | 13 (RLS-01 through RLS-13)              |
| Risk Record Statuses      | 23                                      |
| Escalation Levels         | 6 (E-0 through E-5)                     |
| Readiness Checklist Items | 61                                      |
| Worked Examples           | 6 (WE-01 through WE-06)                 |
| Supplements               | 8 (A through H)                         |
| Glossary Terms            | 75+                                     |

---

### DS.2 Parts Summary

| Part   | Title                           | Key Deliverable                                      |
|--------|---------------------------------|------------------------------------------------------|
| Part I | Risk Philosophy                 | 16-concept definitional ladder; 10 Risk Principles   |
| Part II| Risk Taxonomy                   | 26 risk types (RT-01 to RT-26) with full definitions |
| Part III| Core Components                | 22 components (RC-01 to RC-22) with 11-section specs |
| Part IV| Risk Lifecycle                  | 13 stages; state machine; 23-status table            |
| Part V | Risk Services                   | 14 services (RS-01 to RS-14)                         |
| Part VI| Risk Processing Pipelines       | 10 pipelines with ASCII flow diagrams                |
| Part VII| Risk Quality Framework         | 12 RQS dimensions; formula; tiers                    |
| Part VIII| Risk Governance               | Ownership, naming, versioning, policies, retention   |
| Part IX| Risk Constitution               | 112 rules across 16 categories                       |
| Part X | Risk Readiness Checklist        | 61 checks; readiness matrix; state machine           |

---

### DS.3 Supplements Summary

| Supplement | Title                     | Key Content                                    |
|------------|---------------------------|------------------------------------------------|
| A          | Taxonomy Reference         | 26-type index; 7-category hierarchy diagram    |
| B          | Formulas (Conceptual)      | VaR, CVaR, vol, drawdown, exposure, EWMA, RQS |
| C          | Stress Testing Catalogue   | 14 scenarios with parameters and action matrix |
| D          | Scenario Catalogue         | 5 base scenario templates; assignment rules    |
| E          | Kill Switch Matrix         | 10 triggers; state definitions; testing protocol|
| F          | Escalation Framework       | 6 levels; 3 escalation rules; routing matrix   |
| G          | Operational Runbook        | Startup, intraday, post-session, 8 IRPs        |
| H          | Glossary + 8 GDRs          | 75+ terms; 8 Governing Design Records          |

---

### DS.4 RQS Quick Reference

| Code   | Dimension                     | Weight | Degradation Trigger                        |
|--------|-------------------------------|--------|--------------------------------------------|
| RQD-01 | Accuracy                      | 0.20   | VaR exceedance rate outside 3%-8%          |
| RQD-02 | Sensitivity                   | 0.15   | KS fires without prior WARNING/ALERT       |
| RQD-03 | Timeliness                    | 0.12   | Assessment SLA compliance < 95%            |
| RQD-04 | Coverage                      | 0.10   | Any applicable RT code not evaluated       |
| RQD-05 | Consistency                   | 0.10   | Score variance > 5% for unchanged positions|
| RQD-06 | Robustness                    | 0.08   | RQS falls below 0.55 under failure         |
| RQD-07 | Reliability                   | 0.08   | Component availability < 99%              |
| RQD-08 | Explainability                | 0.05   | REJECTED decisions without explanation     |
| RQD-09 | Traceability                  | 0.05   | Any decision without audit chain           |
| RQD-10 | Governance                    | 0.03   | Unreviewed governance reports              |
| RQD-11 | Auditability                  | 0.02   | Hash chain validation failures             |
| RQD-12 | Capital Protection Eff.       | 0.02   | Undetected adverse events before loss      |

---

### DS.5 GDR Quick Reference

| GDR Code     | Title                                     | Key Rule                                          |
|--------------|-------------------------------------------|---------------------------------------------------|
| GDR-RSK-001  | Capital Preservation is Primary           | Risk management always beats return optimization  |
| GDR-RSK-002  | Independent Risk Evaluation               | Risk assessment is fully independent of Decision Engine|
| GDR-RSK-003  | Kill Switch Authority is Unconditional    | No algorithm can prevent Kill Switch activation   |
| GDR-RSK-004  | Audit Before Action                       | Actions logged before executed                    |
| GDR-RSK-005  | Risk Records are Immutable               | No delete or modify; append-only                  |
| GDR-RSK-006  | Conservative Calibration by Default       | Higher risk estimate used when methodologies disagree|
| GDR-RSK-007  | Human Override is Legitimate and Monitored| Overrides allowed; all logged and reviewed        |
| GDR-RSK-008  | Risk Assessment Never Authorizes Trades   | Risk Engine is a guardian, not an advisor         |

---

### DS.6 Component-Tier Mapping

| Tier | Purpose        | Components                          |
|------|----------------|-------------------------------------|
| T1   | Detection      | RC-01 Registry, RC-02 Catalog, RC-03 Analyzer, RC-04 Scoring, RC-05 Exposure, RC-06 Correlation |
| T2   | Assessment     | RC-07 Drawdown, RC-08 Stress, RC-09 Scenario, RC-10 VaR, RC-11 Tail Risk |
| T3   | Control        | RC-12 Policy, RC-13 Threshold, RC-14 Kill Switch, RC-15 Capital Protection, RC-16 Position Limits, RC-17 Portfolio Limits |
| T4   | Governance     | RC-18 Governance, RC-19 Audit, RC-20 Archive, RC-21 Analytics, RC-22 Health |

---

### DS.7 Cross-Layer Integration Reference

**Input Sources:**

| Source Layer          | What Risk Engine Receives                                    |
|-----------------------|--------------------------------------------------------------|
| L1 GlobalIntelligence | Overnight macro risk context; global market state           |
| L2 MarketIntelligence | VIX; regime; sector risk; circuit breaker signals           |
| L4 OpportunityEngine  | New opportunity context for pre-trade risk assessment        |
| L10 Decision Engine   | Proposed trade decisions for RP-01 Decision-to-Risk pipeline|
| L11 Execution Engine  | Execution records, EQS, fills for RP-02 Execution Risk      |
| L12 TradeMonitoring   | Live P&L, open positions, session drawdown                  |
| L13 Learning Engine   | Risk model calibrations; behavioral patterns                |
| L14 PerformanceAnalytics| Historical drawdown; strategy performance                 |
| Prediction Engine     | All 18 prediction types; tail risk; scenario probabilities  |
| Evidence Engine       | Evaluated evidence with confidence for risk context         |
| Reasoning Engine      | Risk inferences; causal chains                              |

**Output Consumers:**

| Consumer Layer        | What Risk Engine Delivers                                    |
|-----------------------|--------------------------------------------------------------|
| L6 CapitalRiskEngine  | Position size constraints; risk budget limits               |
| L7 RiskControl        | Live risk limits; policy enforcement decisions              |
| L9 RiskGuardian       | Kill Switch state; tail risk triggers; final halt signals   |
| L15 ResearchLab       | Strategy risk gates (max DD, risk-adjusted metrics)         |
| L16 ValidationEngine  | Risk validation results for strategy promotion              |
| L17 ControlTower      | REHS; RQS; all risk metrics for dashboard; event bus        |
| L10 Decision Engine   | APPROVED / REDUCED / REJECTED with reasons and risk score   |
| L3 MetaLearning       | Risk-adjusted strategy performance for weight optimization  |

**Contracts the Risk Engine NEVER violates:**
1. Never creates investment ideas or trade recommendations
2. Never executes trades or submits orders
3. Never overrides the Kill Switch through algorithmic means
4. Never modifies audit records
5. Never grants approval above defined risk limits
6. Never operates without an active audit chain

---

### DS.8 Performance Targets and SLAs

| Metric                         | Target           | Hard Limit       |
|--------------------------------|------------------|------------------|
| Pre-trade risk assessment (E2E)| < 500ms          | 1,000ms          |
| Kill Switch trigger to halt    | < 200ms          | 500ms            |
| Drawdown update latency        | < 50ms           | 200ms            |
| Exposure update latency        | < 100ms          | 500ms            |
| Portfolio monitoring cycle     | < 2,000ms        | 5,000ms          |
| Full stress test (14 scenarios)| < 2,000ms        | 5,000ms          |
| VaR computation                | < 500ms          | 2,000ms          |
| Audit chain write              | < 20ms           | 100ms            |
| REHS computation               | < 200ms          | 500ms            |
| Kill Switch test (startup)     | < 5,000ms        | 10,000ms         |

---

## QUICK-START REFERENCE CARD

`
┌──────────────────────────────────────────────────────────────────────────┐
│  RISK ENGINE QUICK-START REFERENCE CARD                                   │
│  IIOS-RSK-ENG-ARCH-001                                                    │
├────────────────────────────────┬─────────────────────────────────────────┤
│  RISK RECORD ID FORMAT         │  RSK-{TYPE}-{YYYYMMDD}-{SEQ:08d}        │
│  AUDIT RECORD ID FORMAT        │  AUD-RSK-{YYYYMMDD}-{SEQ:08d}           │
│  KILL SWITCH EVENT FORMAT      │  KSE-{TRIGGER}-{YYYYMMDD}-{SEQ:04d}     │
│  SCENARIO ID FORMAT            │  SCN-{TARGET}-{YYYYMMDD}-{SEQ:04d}      │
├────────────────────────────────┴─────────────────────────────────────────┤
│  CRITICAL THRESHOLDS                                                       │
│  Session Drawdown Kill Switch:    2.0% of NAV                             │
│  India VIX Kill Switch:           >= 45                                   │
│  Single Name Max Exposure:        15% of NAV                              │
│  Sector Max Exposure:             40% of NAV                              │
│  Gross Portfolio Exposure Max:    100% of NAV                             │
│  Stress Test Max Loss (any SS):   3% of NAV → Kill Switch pre-condition   │
│  VaR 95% 1-day Limit:            1.0% of NAV                             │
│  Min Cash Reserve:                10% of NAV                              │
│  Min Diversification Ratio:       0.70                                    │
│  Max Avg Correlation:             0.65                                    │
├────────────────────────────────────────────────────────────────────────── │
│  KILL SWITCH: 10 TRIGGERS AT A GLANCE                                     │
│  KS-T01 Daily loss >= 2.0%        KS-T06 Manual operator                  │
│  KS-T02 VIX >= 45                 KS-T07 Stress loss > 3% NAV             │
│  KS-T03 Broker fail > 60s         KS-T08 Gross exposure > 110% limit      │
│  KS-T04 Data feed fail > 30s      KS-T09 Technology failure               │
│  KS-T05 Tail event prob > 30%     KS-T10 Market circuit breaker           │
├────────────────────────────────────────────────────────────────────────── │
│  RQS TIERS                                                                 │
│  EXCELLENT  0.88 - 1.00  Full operations                                  │
│  GOOD       0.72 - 0.87  Normal with monitoring                           │
│  ACCEPTABLE 0.55 - 0.71  Reduce sizes 20%; investigate                    │
│  MARGINAL   0.35 - 0.54  Reduce sizes 50%; halt weak categories           │
│  FAILED     0.00 - 0.34  Halt all new positions                           │
├────────────────────────────────────────────────────────────────────────── │
│  REHS LEVELS                                                               │
│  OPTIMAL    0.90 - 1.00  Full capability                                   │
│  NOMINAL    0.75 - 0.89  Normal operations                                 │
│  DEGRADED   0.55 - 0.74  50% position sizes; operator alert               │
│  CRITICAL   0.30 - 0.54  Halt new positions; recovery                     │
│  FAILED     0.00 - 0.29  Kill Switch forced active                        │
├────────────────────────────────────────────────────────────────────────── │
│  SESSION INTRADAY CHECKPOINTS                                              │
│  09:15 Market open                13:00 Full stress test + scenario update │
│  10:00 First stress test          14:30 Fourth stress test                 │
│  10:00 Portfolio monitoring       15:00 Final stress test                  │
│  11:30 Second stress test         15:25 No new positions after this       │
│  11:30 Portfolio monitoring       15:30 Market close + post-session        │
├────────────────────────────────────────────────────────────────────────── │
│  THE 5 THINGS THE RISK ENGINE NEVER DOES                                   │
│  1. Never creates or recommends trade ideas                                │
│  2. Never executes or submits orders                                       │
│  3. Never overrides the Kill Switch algorithmically                       │
│  4. Never modifies or deletes audit records                               │
│  5. Never allows an unapproved action to proceed                          │
├────────────────────────────────────────────────────────────────────────── │
│  22 COMPONENTS AT A GLANCE (Tier 1-4)                                     │
│  T1: RC-01 Registry | RC-02 Catalog | RC-03 Analyzer                      │
│      RC-04 Scoring | RC-05 Exposure | RC-06 Correlation                   │
│  T2: RC-07 Drawdown | RC-08 Stress | RC-09 Scenario                       │
│      RC-10 VaR | RC-11 Tail Risk                                          │
│  T3: RC-12 Policy | RC-13 Threshold | RC-14 Kill Switch                   │
│      RC-15 CapProtect | RC-16 Position Limits | RC-17 Portfolio Limits    │
│  T4: RC-18 Governance | RC-19 Audit | RC-20 Archive                       │
│      RC-21 Analytics | RC-22 Health                                       │
└──────────────────────────────────────────────────────────────────────────┘
`

---

`
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║           RISK ENGINE ARCHITECTURE                                         ║
║           IIOS-RSK-ENG-ARCH-001                                           ║
║                                                                            ║
║           Status: RATIFIED                                                 ║
║           Series: IIOS Architecture Document Series                       ║
║                                                                            ║
║           "The Risk Engine's job is not to prevent all losses.             ║
║            Its job is to ensure that no loss ever becomes fatal."          ║
║                                                                            ║
║           22 Components. 26 Risk Types. 10 Kill Switch Triggers.          ║
║           14 Stress Scenarios. 112 Constitutional Rules.                   ║
║           One mandate: protect capital.                                    ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════╝
`

---

### Architectural Impact Statement

The Risk Engine Architecture (IIOS-RSK-ENG-ARCH-001) defines the complete risk management function of the Investment Intelligence Operating System. It establishes the Risk Engine as the unconditional guardian of capital — a function that cannot be bypassed, that operates independently of investment objectives, and that prioritizes preservation over performance in every scenario where the two conflict.

The architecture is designed for institutional-grade reliability in a retail-scale deployment. Every design decision reflects the asymmetry of losses: the cost of a missed trade is recoverable; the cost of a catastrophic loss may not be. The Kill Switch, the conservative calibration defaults, the multi-layer threshold enforcement, the complete audit trail, and the 112 constitutional rules all exist in service of a single mathematical reality: you cannot compound returns from capital you no longer have.

This document is complete and ratified as of 2026-07-03.

Document Code: IIOS-RSK-ENG-ARCH-001
Series Position: 15th document in the IIOS Architecture Document Series
