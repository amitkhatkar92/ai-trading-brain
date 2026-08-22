# PREDICTION ENGINE ARCHITECTURE
## Investment Intelligence Operating System (IIOS)
### Document Code: IIOS-PRD-ENG-ARCH-001

---

**Document Scope:** Complete engineering architecture for the Prediction Engine component of the Investment Intelligence Operating System.

**Document Status:** RATIFIED

**Series:** IIOS Architecture Document Series

**Layer Context:** Cross-cutting intelligence service; primary output consumer is Layer 10 (DebateAndDecision)

**Predecessor documents consulted:**
- IIOS-KNW-ENG-ARCH-001 — Knowledge Engine Architecture
- IIOS-OBS-ENG-ARCH-001 — Observation Engine Architecture
- IIOS-EVD-ENG-ARCH-001 — Evidence Engine Architecture
- IIOS-HYP-ENG-ARCH-001 — Hypothesis Engine Architecture
- IIOS-RSN-ENG-ARCH-001 — Reasoning Engine Architecture
- IIOS-DEC-ENG-ARCH-001 — Decision Engine Architecture
- IIOS-EXE-ENG-ARCH-001 — Execution Engine Architecture
- IIOS-LRN-ENG-ARCH-001 — Learning Engine Architecture

**Critical invariants:**
- The Prediction Engine NEVER executes trades
- The Prediction Engine NEVER overrides the Decision Engine
- The Prediction Engine NEVER bypasses governance
- All predictions are advisory intelligence, never absolute truth
- Every prediction carries an explicit uncertainty measure
- Every prediction is fully explainable and auditable

---

## IIOS COGNITIVE STACK — PREDICTION ENGINE CONTEXT

`
┌─────────────────────────────────────────────────────────────────────────────┐
│  IIOS COGNITIVE STACK                    Prediction Engine Role             │
├──────┬──────────────────────────────────┬─────────────────────────────────┤
│  L1  │ GlobalIntelligence               │ → Input: global context signals  │
│  L2  │ MarketIntelligence               │ → Input: regime, sector, event   │
│  L3  │ MetaLearning                     │ ← Output: strategy prob forecasts │
│  L4  │ OpportunityEngine                │ → Input: opportunity signals     │
│  L5  │ StrategyLab                      │ ← Output: strategy predictions   │
│  L6  │ CapitalRiskEngine                │ ← Output: position outcome range │
│  L7  │ RiskControl                      │ ← Output: risk state forecasts   │
│  L8  │ MarketSimulation                 │ → Input: Monte Carlo scenarios   │
│  L9  │ RiskGuardian                     │ ← Output: tail risk predictions  │
│  L10 │ DebateAndDecision ◄══════════════╪══ PRIMARY PREDICTION OUTPUT       │
│  L11 │ ExecutionEngine                  │ ← Output: execution quality pred │
│  L12 │ TradeMonitoring                  │ → Input: trade outcome actuals   │
│  L13 │ LearningSystem                   │ → Input: calibration feedback    │
│  L14 │ PerformanceAnalytics             │ → Input: performance history     │
│  L15 │ ResearchLab                      │ ← Output: strategy fitness preds │
│  L16 │ ValidationEngine                 │ → Input: out-of-sample feedback  │
│  L17 │ ControlTower                     │ ← Output: PSHS telemetry         │
├──────┴──────────────────────────────────┴─────────────────────────────────┤
│                                                                             │
│  ╔══════════════════════════════════════════════════════════════════╗        │
│  ║               PREDICTION ENGINE (Advisory)                       ║        │
│  ║  Consumes: Knowledge · Observation · Evidence ·                  ║        │
│  ║            Hypothesis · Reasoning · Learning · Market Simulation ║        │
│  ║  Produces: Forecasts · Probabilities · Scenarios ·               ║        │
│  ║            Confidence Distributions · Uncertainty Bounds         ║        │
│  ╚══════════════════════════════════════════════════════════════════╝        │
└─────────────────────────────────────────────────────────────────────────────┘
`

---

## PREDICTION ENGINE — INFORMATION FLOW

`
                    PREDICTION ENGINE INFORMATION FLOW
                    ═══════════════════════════════════

[Knowledge Engine]     ──→ entity knowledge, model parameters, domain rules
[Observation Engine]   ──→ current price action, volume, breadth signals
[Evidence Engine]      ──→ evaluated evidence, confidence-weighted signals
[Hypothesis Engine]    ──→ active hypotheses, confidence scores
[Reasoning Engine]     ──→ inferred conclusions, causality chains
[Learning Engine]      ──→ calibrated weights, model improvements
[MarketSimulation L8]  ──→ Monte Carlo scenario distributions
[GlobalIntelligence L1]──→ overnight context, macro environment
[MarketIntelligence L2]──→ current regime, liquidity state, sector flow
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │      PREDICTION ENGINE        │
                        │                               │
                        │  Collect → Context Build →   │
                        │  Forecast → Probability →    │
                        │  Scenario → Confidence →     │
                        │  Validate → Rank →           │
                        │  Govern → Distribute         │
                        └──────────────┬───────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
  [Decision Engine L10]   [StrategyLab L5 / Risk L7]   [ControlTower L17]
  Primary prediction       Strategy and risk           Telemetry, health,
  consumer: forecasts,     prediction consumers        audit reports
  scenarios, probabilities
`

---

## TABLE OF CONTENTS

**Part I** — Prediction Philosophy and Definitional Framework
**Part II** — Prediction Taxonomy
**Part III** — Core Component Architecture
**Part IV** — Prediction Lifecycle
**Part V** — Prediction Services
**Part VI** — Prediction Pipelines
**Part VII** — Prediction Quality Framework
**Part VIII** — Prediction Governance
**Part IX** — Prediction Constitution
**Part X** — Prediction Readiness Checklist

**Supplement A** — Prediction Taxonomy Reference
**Supplement B** — Forecast Examples and Reference Cases
**Supplement C** — Scenario Catalogue
**Supplement D** — Probability Reference and Calibration Guide
**Supplement E** — Bias and Drift Examples
**Supplement F** — Anti-Patterns
**Supplement G** — Operational Runbook
**Supplement H** — Comprehensive Glossary and Governing Design Records

**Appendix** — Worked Prediction Examples (WE-01 through WE-06)
**Document Summary** — Metrics, Maps, Indexes, Compliance, Ratification

---

## PART I — PREDICTION PHILOSOPHY AND DEFINITIONAL FRAMEWORK

### 1.1 What is Prediction?

Prediction is the disciplined, evidence-grounded attempt to characterize future states before they occur. It is not guessing, not assertion, and not certainty. It is the intellectual process of combining current knowledge, observed signals, inferred patterns, and probabilistic reasoning to describe what is likely, possible, and improbable about the future.

In the Investment Intelligence Operating System, prediction is an explicit cognitive layer. The Prediction Engine is the dedicated component that transforms the system's current understanding of the world into structured, probabilistic forward projections that equip the Decision Engine with the best possible future-state intelligence before any commitment is made.

Prediction in IIOS is governed by a fundamental epistemological principle: the future is unknowable with certainty. Every prediction is a probability distribution over possible future states, never a single certain outcome. This is not a limitation — it is a structural truth about financial markets and complex systems. The Prediction Engine embeds this truth in every output it produces.

A prediction that claims certainty is not a prediction — it is an error. A prediction without uncertainty quantification is incomplete. A prediction without a traceability path to its driving evidence is unacceptable. These three principles are non-negotiable in the IIOS Prediction Engine.

### 1.2 Definitional Ladder

The language of prediction is frequently used imprecisely. The IIOS establishes a precise definitional ladder, with each concept occupying a distinct semantic position:

**Level 1 — Assumption**
A premise accepted as true without current formal evidence. Assumptions are the unstated premises that all higher-level predictions depend on. Good prediction practice requires that all material assumptions are made explicit and are marked as such. An assumption is not a prediction — but hidden assumptions corrupt predictions.

*IIOS handling:* Every prediction record requires its material assumptions to be declared. Assumptions are reviewed for reasonableness and flagged if they conflict with current observations.

**Level 2 — Possibility**
A future state that cannot be ruled out given current information. No probability is assigned. Possibilities define the outer boundary of the prediction space — the universe of futures that are not precluded.

*IIOS handling:* Scenario generation maps the possibility space. Every generated scenario is a possibility with an assigned probability. Scenarios with probability below 2% may be retained as tail events but are not distributed to the Decision Engine as active predictions.

**Level 3 — Estimate**
A numerical approximation of an unknown quantity, derived from available data and domain knowledge. Estimates carry inherent imprecision. A price estimate of 22,300 to 22,500 is an estimate — it acknowledges the range of uncertainty.

*IIOS handling:* All quantitative forecast outputs are estimates. They are expressed as ranges or distributions, never as single point values without associated uncertainty bounds.

**Level 4 — Probability**
A quantified measure of the likelihood that a specific event or state will occur, expressed as a number between 0 (impossible) and 1 (certain). Probability is the primary language of the Prediction Engine. Every meaningful prediction in IIOS is expressed as a probability or a distribution of probabilities.

*IIOS handling:* The Probability Engine is dedicated to computing, calibrating, and monitoring probability assignments across all prediction types.

**Level 5 — Likelihood**
A relative comparison between hypotheses or scenarios given observed data. Likelihood is the statistical basis for Bayesian updating: when new evidence arrives, the likelihood function quantifies how much each hypothesis should update. Unlike probability (which applies to future events), likelihood applies to the relationship between hypotheses and already-observed data.

*IIOS handling:* The Evidence Engine computes likelihoods; the Prediction Engine uses these likelihoods as inputs to probability computations via Bayesian updating.

**Level 6 — Forecast**
A quantitative prediction of a specific measurable quantity at a defined future time horizon. Forecasts are the most structured and specific form of prediction. A complete forecast includes: the quantity being predicted, the horizon, the point estimate, the confidence interval, and the forecast error model.

*IIOS handling:* The Forecast Generator produces structured forecast records with all required fields. Forecasts are validated before distribution.

**Level 7 — Prediction**
A broader statement about future states, events, or conditions. A prediction encompasses quantitative forecasts but also includes qualitative directional assessments ("The market is likely to consolidate"), probabilistic event predictions ("There is a 68% probability of a volatility spike before 11:00 IST"), and conditional statements ("If NIFTY breaks 22,500, momentum is likely to accelerate").

*IIOS handling:* Prediction records are the primary currency of the Prediction Engine. Every prediction has a type, a target, a horizon, a probability, and an evidence trail.

**Level 8 — Projection**
An extrapolation of a current trend or trajectory into the future, assuming that the current drivers continue without regime change. Projections are deterministic extrapolations conditioned on the assumption of continuity. They are appropriate for short horizons but grow increasingly unreliable as the projection extends.

*IIOS handling:* Projections are labeled as such and carry a temporal decay: the further the projection extends, the lower its confidence score. Regime transitions invalidate projections immediately.

**Level 9 — Expectation**
The probability-weighted average of possible outcomes. The expected value of a price forecast is the sum across all scenarios of (scenario price × scenario probability). Expectation is the single number that best represents a full distribution when only one number can be communicated.

*IIOS handling:* All scenario sets produce an expectation. The expectation is always accompanied by the full distribution — a single expected value without its distribution is an incomplete summary.

**Level 10 — Confidence**
A meta-level measure of trust in a prediction itself. Confidence is distinct from probability: a prediction can have a high probability and low confidence (we believe the event is likely but we are uncertain about whether our probability estimate is correct). Confidence reflects the quality and completeness of the evidence base, the stability of the relevant relationships, and the regime appropriateness of the model.

*IIOS handling:* The Confidence Engine computes a dedicated confidence score for every prediction, independent of the prediction's probability. The Decision Engine weighs predictions by their confidence, not just their probability.

**Level 11 — Risk**
The probability-weighted exposure to unfavorable outcomes. Risk combines probability (how likely is the adverse event) with impact (how damaging would it be). Risk is not a prediction — it is a function computed over a set of predictions.

*IIOS handling:* Risk predictions (PT-05) are a distinct prediction type. The Prediction Engine produces tail risk predictions and distributes them to RiskControl (Layer 7) and RiskGuardian (Layer 9).

**Level 12 — Scenario**
A coherent, internally consistent narrative of a future state. A good scenario has: a name, a driver set, an activation probability, a NIFTY/BANKNIFTY level range, a strategy implication, a duration estimate, and a termination condition.

*IIOS handling:* The Scenario Generator produces structured scenario records. Scenarios must be mutually exclusive and exhaustive (probabilities sum to 1.0 across the full scenario set for each prediction).

**Level 13 — Outcome**
The actual realized future state against which predictions are evaluated. Outcomes are the ground truth that the Prediction Engine uses to measure forecast accuracy, calibration, and skill.

*IIOS handling:* Outcome evaluation is a formal pipeline stage. Outcomes are collected from TradeMonitoring (Layer 12) and applied to historical prediction records via the Outcome Evaluation Pipeline (PP-09).

**Level 14 — Future State**
A complete description of the system at a future point in time. A future state includes: price levels, regime label, volatility regime, portfolio state, and strategy activation status. Scenarios predict future states; outcomes confirm them.

**Level 15 — Target**
A desired or expected outcome level used as a reference for trade management. Distinct from a forecast: a target is a decision parameter, not a prediction output. Targets are computed by the Execution Engine from prediction inputs; they are not generated by the Prediction Engine itself.

*IIOS handling:* The Prediction Engine provides the forecast inputs from which the Execution Engine derives price targets. The Prediction Engine never sets targets directly.

---

### 1.3 Prediction Types

**Type 1 — Deterministic Prediction**

A prediction with a single stated outcome and no uncertainty representation. Example: "NIFTY will close at 22,450." Deterministic predictions are almost always wrong because they ignore the irreducible uncertainty of financial markets. They are appropriate only for mechanical, rule-bound outcomes with negligible uncertainty (e.g., the options contract expires worthless if it is out of the money at expiry).

In IIOS, deterministic predictions are permitted only where the outcome is mechanically determined by rules with probability approaching certainty (> 0.99). All other predictions must carry probability distributions.

**Type 2 — Probabilistic Prediction**

The primary prediction form of the IIOS. A probabilistic prediction assigns probability measures to a defined set of outcomes. "NIFTY closes above 22,400: probability 0.62; below 22,400: probability 0.38." Probabilistic predictions are honest about uncertainty and support rational decision-making under uncertainty.

The Prediction Engine generates probabilistic predictions for every prediction type. The Probability Engine is dedicated to computing and calibrating these probabilities.

**Type 3 — Scenario Prediction**

A set of alternative futures, each with associated probabilities, drivers, and implications. Scenario prediction is the richest form of prediction because it captures the multivariate, non-linear nature of market outcomes. Rather than collapsing the future into a single probability, scenario prediction preserves the full distributional structure of possible futures.

The Scenario Generator produces structured scenario sets. Every active scenario set satisfies the probability axioms: individual probabilities are non-negative, and the sum across all scenarios in a set equals 1.0.

**Type 4 — Conditional Prediction**

A prediction whose probability is conditioned on a specified precondition. "IF the RBI maintains rates at 6.25%, THEN the probability of BANKEX closing above 50,000 is 0.72." Conditional predictions are essential for event-driven analysis and capture the decision tree structure of market outcomes.

**Type 5 — Recursive Prediction**

A prediction that uses its own prior predictions as inputs. Multi-horizon forecasting is inherently recursive: the 60-minute forecast is conditioned on the 15-minute forecast, which is conditioned on the 5-minute forecast. Recursive predictions must be internally consistent — higher-horizon forecasts cannot contradict lower-horizon forecasts without an explicit regime-change event.

**Type 6 — Adaptive Prediction**

A prediction that updates in real-time as new signals arrive. Adaptive predictions are never frozen — they evolve with every new observation. The Prediction Engine's real-time prediction records are adaptive: each new observation triggers a Bayesian update to the probability distribution.

**Type 7 — Multi-Horizon Prediction**

Simultaneous, internally consistent predictions at multiple time horizons. The Prediction Engine maintains active predictions at intraday micro (5-15 minutes), intraday short (15-60 minutes), intraday (session), overnight, and multi-session horizons. Multi-horizon predictions must satisfy temporal consistency constraints.

**Type 8 — Ensemble Prediction**

A prediction formed by aggregating the outputs of multiple prediction models. The Ensemble Manager combines predictions from different model families (statistical, rule-based, pattern-recognition, AI) using regime-calibrated weights. Ensemble predictions generally outperform any single model's predictions.

**Type 9 — AI Prediction**

Predictions generated by machine learning models. AI predictions in IIOS require explainability wrappers: every AI prediction is accompanied by a feature attribution report that identifies the top driving features and their contribution to the prediction. This is a constitutional requirement — AI predictions without explainability are not distributed.

**Type 10 — Human-Assisted Prediction**

Predictions that incorporate human judgment, annotations, or corrections. When a human operator provides a directional annotation (e.g., marks a situation as "unusual" or provides a market context note), this input is treated as a high-confidence signal that modifies the Prediction Engine's active predictions.

---

### 1.4 Why Prediction Must Be Probabilistic and Explainable

**The case for probabilistic prediction:**

Financial markets are complex adaptive systems. Their future states are not mechanically determined by current states. They depend on the actions of millions of participants, each responding to their own information and incentives. This structural complexity produces irreducible uncertainty.

A prediction system that claims to know the future with certainty is not a prediction system — it is a mechanism for generating overconfident decisions that will fail when the inevitable surprises occur.

The Prediction Engine is built on the epistemological foundation that uncertainty is real, quantifiable, and must be propagated through the decision-making system. A decision made with full awareness of its uncertainty is a better decision than a decision made with false certainty.

**The case for explainable prediction:**

Explainability is not merely a usability feature — it is a safety requirement. An unexplainable prediction cannot be validated. It cannot be challenged. It cannot be improved. And when it fails, it cannot be diagnosed.

In the IIOS, every prediction must be traceable to its driving evidence, its model structure, and its material assumptions. This traceability enables:

1. Validation: the Prediction Validator can verify that the prediction is grounded in current, relevant evidence.
2. Governance: the Prediction Governance Manager can assess whether the prediction follows applicable rules.
3. Challenge: the Decision Engine's debate process can challenge a prediction on the basis of its specific evidence or assumptions.
4. Learning: the Learning Engine can trace prediction errors back to their source drivers and improve the underlying models.
5. Accountability: every prediction that influences a trade decision is auditable by human operators.

---

### 1.5 Prediction Principles

**PP-001 — Predictions are advisory, not authoritative.**
No prediction generated by the Prediction Engine constitutes a trade instruction, a risk limit, or a governance override. Predictions inform decisions; they do not make them.

**PP-002 — Every prediction carries uncertainty.**
No prediction is distributed without an associated uncertainty measure. Point forecasts without confidence intervals are not valid prediction outputs.

**PP-003 — Probabilistic over deterministic.**
All predictions in IIOS are probabilistic unless the outcome is mechanically determined with probability exceeding 0.99.

**PP-004 — Explainability is required.**
Every prediction is accompanied by a traceable explanation of its driving evidence, model, and material assumptions. AI predictions carry feature attribution reports.

**PP-005 — Calibration is monitored.**
The relationship between predicted probability and observed frequency is continuously monitored. A prediction assigned 0.70 probability should be correct 70% of the time.

**PP-006 — Predictions are regime-aware.**
Every prediction is tagged with the current regime at generation time. A prediction valid in a RANGING regime may be invalid in a TRENDING_BULL regime.

**PP-007 — Predictions expire.**
Every prediction has a defined validity horizon. Predictions are automatically flagged as STALE when their validity horizon passes without an outcome evaluation.

**PP-008 — Predictions do not override governance.**
No prediction, regardless of confidence or probability, authorizes a trade, overrides a risk limit, or bypasses the Kill Switch.

**PP-009 — Human override is absolute.**
A human operator may override, suppress, or modify any prediction at any time. The override is recorded but never resisted.

**PP-010 — Learning closes the loop.**
Every prediction with an observable outcome is evaluated post-outcome and the evaluation is fed to the Learning Engine for model improvement.

---

## PART II — PREDICTION TAXONOMY

### 2.1 Overview

The Prediction Taxonomy defines the 18 canonical prediction types recognised by the IIOS Prediction Engine. Every prediction record belongs to exactly one primary prediction type and may be tagged with secondary types for cross-type analysis. The taxonomy is designed to be exhaustive: every forward-looking statement the Prediction Engine can produce falls within one of these 18 categories.

**Prediction Type Identifier Format:** PT-{NN} where NN is the two-digit type code.

**Common fields across all prediction types:**

| Field | Description |
|---|---|
| prediction_id | Unique prediction record ID: PRD-{TYPE}-{DATE}-{SEQ:08d} |
| prediction_type | PT-01 through PT-18 |
| target_entity | What the prediction is about |
| horizon | Prediction time horizon |
| generated_at | Timestamp of prediction generation |
| regime_at_generation | Market regime at time of generation |
| probability_point | Point probability estimate |
| probability_distribution | Full distribution if available |
| confidence_score | Prediction Engine confidence in this prediction |
| uncertainty_lower | Lower bound of uncertainty range |
| uncertainty_upper | Upper bound of uncertainty range |
| driving_evidence | List of evidence IDs that drove this prediction |
| model_ids | List of model version IDs used |
| explainability_report_id | Reference to feature attribution report |
| status | ACTIVE, EXPIRED, SUPERSEDED, EVALUATED |
| outcome_id | Outcome record ID (populated after evaluation) |
| pqs_score | Prediction Quality Score at generation time |

---

### 2.2 Prediction Types

**PT-01 — Price Prediction**

*Source domain:* Price action, order flow, microstructure, pattern recognition

*Definition:* A quantitative prediction of the future price level of a specific instrument at a defined time horizon. Price predictions are the most granular and operationally immediate predictions produced by the Prediction Engine.

*What it predicts:* Closing price, high/low range, support/resistance levels, breakout probability, price gap probability.

*Primary inputs:* Observation Engine price data, Evidence Engine technical signals, Learning Engine calibrated models, MarketSimulation Monte Carlo distributions.

*Primary consumers:* Decision Engine (for trade entry/exit pricing), Execution Engine (for order price setting), RiskControl (for stop loss placement guidance).

*Key characteristics:*
Price predictions are produced at multiple horizons simultaneously (5-min, 15-min, 30-min, 60-min, session). Each horizon prediction is internally consistent with shorter-horizon predictions. Price predictions carry two key measures: the central estimate (expected price) and the price range (1-sigma interval). The ratio of the 1-sigma range to the central estimate is a direct measure of the prediction's uncertainty.

*Calibration standard:* The 68% confidence interval should contain the actual price 68% of the time. This calibration is monitored continuously by the Confidence Engine.

*Regime sensitivity:* HIGH. Price prediction models that perform well in trending regimes typically underperform in ranging regimes. All price prediction models carry a regime applicability tag.

*IIOS-specific note:* Price predictions for NIFTY and BANKNIFTY index instruments use the ^NSEI and ^NSEBANK routing symbols. Equity predictions use the .NS suffix convention.

---

**PT-02 — Trend Prediction**

*Source domain:* Technical analysis, momentum, regime identification

*Definition:* A prediction about the directional momentum and continuation probability of a current price trend. Trend predictions answer: Is the current trend likely to continue, reverse, or fade? At what probability? For how long?

*What it predicts:* Trend continuation probability, trend reversal probability, trend exhaustion signals, trend strength (based on ADX/slope measures), breakout direction probability for consolidation patterns.

*Primary inputs:* Observation Engine trend signals (moving average structure, momentum oscillators), Evidence Engine technical pattern evaluations, Hypothesis Engine directional hypotheses.

*Primary consumers:* MetaLearning (strategy weight adjustment based on trend regime), StrategyLab (strategy selection for trend-following vs mean-reversion), Decision Engine (directional bias in debate).

*Key characteristics:*
Trend predictions are intrinsically conditional: a trend prediction states "given current trend dynamics, the probability of continuation for the next N minutes is P." They must be invalidated immediately upon observation of a reversal signal that exceeds the trend invalidation threshold.

*Calibration standard:* Directional accuracy across a rolling 20-session window should exceed 55% to be considered a positive-skill prediction.

---

**PT-03 — Volatility Prediction**

*Source domain:* Volatility analysis, options market signals, VIX derivatives

*Definition:* A prediction of the expected realized volatility of an instrument or index over a specified future period. Volatility predictions are critical inputs to position sizing (Capital Risk Engine, Layer 6) and risk management (RiskControl, Layer 7).

*What it predicts:* Expected realized volatility (annualized), intraday range estimate (High-Low as % of Open), probability of volatility expansion, probability of volatility compression, implied vs realized volatility spread direction.

*Primary inputs:* Historical realized volatility, India VIX, options chain implied volatility surface, GARCH-family model outputs, regime classifier output.

*Primary consumers:* Capital Risk Engine (position sizing — wider predicted volatility → smaller position), RiskControl (stop loss width calibration), RiskGuardian (Kill Switch proximity assessment).

*Key characteristics:*
Volatility predictions are asymmetric: volatility spikes occur much faster than volatility compressions. The Prediction Engine explicitly models the asymmetry: upside volatility scenarios carry higher probability than the symmetric Gaussian assumption would suggest.

*IIOS-specific note:* The Kill Switch threshold (VIX > 45) is a hard rule, not a prediction. The Prediction Engine produces tail risk predictions for high-VIX scenarios but does not determine whether the Kill Switch fires — that is the RiskGuardian's sole authority.

---

**PT-04 — Liquidity Prediction**

*Source domain:* Market microstructure, order book depth, volume analysis

*Definition:* A prediction of the expected market liquidity state at a future time for a specific instrument. Liquidity predictions inform execution decision making: how easily can a position of the planned size be entered or exited at the expected price?

*What it predicts:* Bid-ask spread estimate, market depth estimate, price impact estimate for planned trade sizes, liquidity regime (DEEP/NORMAL/THIN/ILLIQUID), time-of-day liquidity profile.

*Primary inputs:* Observation Engine volume and order flow data, historical liquidity profiles, time-of-day seasonality models, market event calendar.

*Primary consumers:* Execution Engine (order type selection, timing), Capital Risk Engine (position size adjustment for liquidity), Decision Engine (execution quality expectations).

*Key characteristics:*
Liquidity at the open (09:15-09:30 IST) and close (15:15-15:30 IST) is structurally different from midday liquidity. Liquidity predictions carry explicit time-window conditioning. F&O expiry days have predictably different liquidity profiles and require specific liquidity prediction models.

---

**PT-05 — Risk Prediction**

*Source domain:* Risk analytics, drawdown history, correlation analysis

*Definition:* A prediction of the probability and magnitude of adverse outcomes: portfolio drawdown, strategy loss events, correlation breakdown scenarios. Risk predictions provide forward-looking risk intelligence to the risk management layers.

*What it predicts:* Probability of daily loss exceeding 1%, 2% (Kill Switch threshold), probability of strategy-level stop triggering, expected maximum adverse excursion, correlation stress probability, portfolio VaR forward estimate.

*Primary inputs:* Current portfolio state (from RiskControl), historical drawdown data (from LearningEngine and PerformanceAnalytics), volatility predictions (PT-03), macro scenario predictions (PT-06).

*Primary consumers:* RiskControl (Layer 7), RiskGuardian (Layer 9 — for Kill Switch proximity assessment), Capital Risk Engine (Layer 6 — position sizing).

*Key characteristics:*
Risk predictions must be conservative: the cost of underestimating risk vastly exceeds the cost of overestimating it. Risk predictions carry an explicit asymmetry parameter: the probability distribution for losses is fat-tailed to the downside.

---

**PT-06 — Macro Prediction**

*Source domain:* Global Intelligence (Layer 1), macroeconomic data, central bank signals

*Definition:* A prediction about macroeconomic conditions and their likely impact on IIOS-monitored instruments. Macro predictions operate at longer time horizons (days to weeks) and inform the regime and strategy selection layers.

*What it predicts:* RBI rate decision probability (hike/hold/cut), USD/INR direction probability, global risk appetite direction (risk-on/risk-off probability), crude oil impact on INR-denominated assets, FII flow direction probability.

*Primary inputs:* GlobalIntelligence (Layer 1) overnight context, central bank meeting calendars, macro data release schedules, historical macro-to-market impact studies.

*Primary consumers:* MarketIntelligence (Layer 2 — regime determination), StrategyLab (Layer 5 — strategy regime mapping), Decision Engine (macro bias in debate scoring).

---

**PT-07 — Sector Prediction**

*Source domain:* Sector rotation analysis, sector-level technical structure

*Definition:* A prediction about the relative performance and directional bias of NSE sectors over a defined horizon. Sector predictions guide sector-level opportunity identification and portfolio sector allocation.

*What it predicts:* Sector momentum score (next session), sector relative strength ranking, sector rotation phase prediction, sector-specific event impact probability.

*Primary inputs:* MarketIntelligence (Layer 2) sector data, sector index price observations, sector-level FII and DII flow estimates, sector earnings calendar.

*Primary consumers:* OpportunityEngine (Layer 4 — sector-based opportunity scanning), Decision Engine (sector bias in decision scoring).

---

**PT-08 — Company Prediction**

*Source domain:* Company-specific analysis, earnings predictions, fundamental signals

*Definition:* Predictions about individual company outcomes relevant to IIOS trading decisions: earnings surprise probability, post-result price direction, corporate action impact.

*What it predicts:* Earnings surprise direction (beat/miss/in-line probability), post-earnings gap probability and magnitude, ex-dividend price adjustment, corporate action impact on options.

*Primary inputs:* Knowledge Engine company data, earnings history, analyst consensus models, historical earnings reaction patterns.

*Primary consumers:* OpportunityEngine (Layer 4 — event-driven opportunities), Decision Engine (company-specific context for equity trades).

---

**PT-09 — Portfolio Prediction**

*Source domain:* Portfolio analytics, correlation models, factor analysis

*Definition:* Predictions about the future state of the IIOS portfolio as a whole: expected portfolio returns, portfolio correlation shifts, portfolio factor exposure changes.

*What it predicts:* Expected portfolio return (1-session, 5-session), portfolio beta to NIFTY, portfolio drawdown probability, portfolio diversification ratio forward estimate, portfolio factor drift.

*Primary inputs:* Current portfolio state, strategy performance history (Learning Engine), correlation matrix (current and forward-projected), volatility predictions (PT-03).

*Primary consumers:* Capital Risk Engine (Layer 6 — portfolio-level position sizing), RiskControl (Layer 7 — portfolio risk management).

---

**PT-10 — Strategy Prediction**

*Source domain:* Strategy performance history, regime-strategy matching

*Definition:* Predictions about the likely performance of individual IIOS strategies under current and projected market conditions. Strategy predictions are the primary bridge between the Prediction Engine and MetaLearning (Layer 3).

*What it predicts:* Per-strategy session win probability under current regime, expected Sharpe ratio contribution, strategy correlation in current portfolio (is strategy adding diversification or adding concentration?), strategy demotion/promotion probability over next 20 sessions.

*Primary inputs:* Learning Engine strategy performance data, MetaLearning regime-strategy map, current regime prediction (from PT-02 and macro context), strategy parameter set.

*Primary consumers:* MetaLearning (Layer 3 — strategy weight recalibration input), StrategyLab (Layer 5 — strategy selection), Decision Engine (strategy suitability score in debate).

---

**PT-11 — Execution Prediction**

*Source domain:* Execution quality data, market microstructure

*Definition:* Predictions about execution quality outcomes for planned trade actions. Execution predictions answer: If we place this order now, what is the expected slippage? What is the probability of fill at the limit price? What is the expected time-to-fill?

*What it predicts:* Expected slippage (in pips and INR), probability of fill at limit price within N minutes, expected time-to-fill for market and limit orders, order rejection probability by instrument class and time window.

*Primary inputs:* Learning Engine execution quality history, liquidity prediction (PT-04), time-of-day profiles, instrument-specific execution statistics.

*Primary consumers:* Execution Engine (Layer 11 — order type selection, price improvement estimation), Decision Engine (expected execution cost in trade economics calculation).

---

**PT-12 — Behavior Prediction**

*Source domain:* Behavioral analytics, Learning Engine behavioral patterns

*Definition:* Predictions about the IIOS system's own behavioral tendencies under specific conditions. Behavior predictions are meta-level: they help the system avoid its own known behavioral biases.

*What it predicts:* Probability of over-trading tendency at market open (based on historical behavioral patterns), probability of confirmation bias in evidence evaluation under current conditions, probability of excessive risk-taking after a run of wins.

*Primary inputs:* Learning Engine behavioral patterns (LT-11), IIOS behavioral history, current session context.

*Primary consumers:* Decision Engine (behavioral bias correction in debate scoring), Prediction Governance Manager (heightened monitoring under high-behavioral-risk conditions).

---

**PT-13 — Cross-Market Prediction**

*Source domain:* Cross-market correlation analysis, global market signals

*Definition:* Predictions based on correlations and relationships between NSE instruments and external markets (US markets, Asian markets, commodity markets, FX markets).

*What it predicts:* NIFTY opening gap probability given US overnight movement, Nikkei-NIFTY intraday correlation prediction, USDINR impact on IT sector probability, crude oil impact on energy sector.

*Primary inputs:* GlobalIntelligence (Layer 1) overnight data, cross-market correlation models (calibrated by Learning Engine), historical cross-market relationship patterns.

*Primary consumers:* Decision Engine (global context scoring in debate), MarketIntelligence (Layer 2 — regime refinement).

---

**PT-14 — Cross-Asset Prediction**

*Source domain:* Cross-asset class correlation, macro factor models

*Definition:* Predictions about the relationships and relative behavior of different asset classes (equity, debt, commodities, currency) in the Indian market context.

*What it predicts:* Equity-debt correlation regime prediction, gold-equity correlation in risk-off scenarios, currency-equity correlation probability, bond yield impact on equity sectors.

*Primary inputs:* GlobalIntelligence (Layer 1), MarketIntelligence (Layer 2), cross-asset correlation history, macro scenario predictions (PT-06).

*Primary consumers:* Decision Engine (cross-asset context), Portfolio prediction generation (PT-09).

---

**PT-15 — Event Prediction**

*Source domain:* Event calendar, market reaction history, news analysis

*Definition:* Predictions about the probability, timing, and market impact of specific future events: RBI meetings, corporate earnings, index rebalancings, regulatory announcements.

*What it predicts:* Event occurrence probability (for uncertain events), event direction probability (for events with uncertain outcomes), event market impact: direction probability, magnitude estimate, duration estimate.

*Primary inputs:* Market event calendar (MarketIntelligence Layer 2), earnings dates (Knowledge Engine), historical event impact database (Learning Engine).

*Primary consumers:* Decision Engine (event risk in trade timing), StrategyLab (strategy avoidance rules around known event risk windows).

---

**PT-16 — Scenario Prediction**

*Source domain:* Scenario analysis, narrative-based modeling

*Definition:* A structured set of alternative future states, each with associated probabilities, drivers, and implications. Scenario predictions are the most comprehensive prediction form: they explicitly represent the full range of plausible futures rather than collapsing to a single estimate.

*What it predicts:* A complete scenario set covering Bull, Base, Bear, and Tail scenarios for the current session or horizon. Each scenario specifies: NIFTY range, regime, strategy implications, key drivers, probability, and invalidation signals.

*Primary inputs:* All other prediction types feed into scenario generation as inputs. The Scenario Generator synthesizes the full prediction picture into a structured scenario set.

*Primary consumers:* Decision Engine (scenario-weighted trade scoring), RiskGuardian (tail scenario monitoring), ControlTower (scenario dashboard display).

*Constraint:* All scenario probabilities in a complete scenario set must sum to exactly 1.00.

---

**PT-17 — Tail Risk Prediction**

*Source domain:* Extreme value theory, tail risk analytics, stress testing

*Definition:* Predictions about low-probability, high-impact adverse outcomes. Tail risk predictions specifically focus on the left tail of the outcome distribution: the outcomes that are rare but potentially catastrophic to the portfolio.

*What it predicts:* Probability of loss exceeding VaR (Value at Risk) at 99th percentile, probability of drawdown exceeding 2% in a single session (Kill Switch proximity), probability of correlated strategy failure (when multiple strategies lose simultaneously), probability of black swan market events affecting all positions.

*Primary inputs:* Volatility predictions (PT-03), stress test scenarios (MarketSimulation Layer 8), cross-strategy correlation matrix, historical extreme event database.

*Primary consumers:* RiskGuardian (Layer 9 — Kill Switch assessment), RiskControl (Layer 7 — tail risk hedging decisions), Decision Engine (tail risk weight in debate scoring).

*Constraint:* Tail risk predictions are never understated. The Prediction Engine applies a systematic upward adjustment to tail probabilities from purely statistical models, recognizing that market tails are consistently fatter than statistical models predict.

---

**PT-18 — Probability Distribution Prediction**

*Source domain:* Statistical modeling, Bayesian inference, distributional analysis

*Definition:* A prediction of the full probability distribution over an outcome variable, rather than a point estimate or scenario set. The distribution prediction is the highest information content form of prediction.

*What it predicts:* The full probability density function (PDF) for a price outcome, a return distribution, a volatility distribution. The distribution prediction specifies: mean, standard deviation, skewness, kurtosis, and key percentile values (5th, 10th, 25th, 50th, 75th, 90th, 95th).

*Primary inputs:* Ensemble model outputs (from Ensemble Manager), Monte Carlo simulation outputs (Layer 8), Bayesian posterior distributions.

*Primary consumers:* Capital Risk Engine (Layer 6 — full distribution input to Kelly criterion position sizing), Decision Engine (full distribution for expected value computation), Risk layers.

*Special properties:* Distribution predictions are the most computationally demanding prediction type. They are generated for NIFTY, BANKNIFTY, and active portfolio instruments at session start and updated hourly.

---

### 2.3 Prediction Type Summary Table

| Code | Type | Horizon | Primary Consumer | Update Frequency |
|---|---|---|---|---|
| PT-01 | Price | 5 min – Session | Decision Engine | Continuous |
| PT-02 | Trend | 15 min – Session | MetaLearning | Per new signal |
| PT-03 | Volatility | 30 min – Session | Capital Risk, RiskControl | Every 15 min |
| PT-04 | Liquidity | Intraday | Execution Engine | Continuous |
| PT-05 | Risk | Session – 5 sessions | RiskControl, RiskGuardian | Every 30 min |
| PT-06 | Macro | Daily – Weekly | MarketIntelligence | Daily |
| PT-07 | Sector | Session – Daily | OpportunityEngine | Session start |
| PT-08 | Company | Event-driven | OpportunityEngine | On event |
| PT-09 | Portfolio | Session – 5 sessions | Capital Risk, RiskControl | Per trade |
| PT-10 | Strategy | Session – 20 sessions | MetaLearning, StrategyLab | Session end |
| PT-11 | Execution | Pre-order | Execution Engine | Per order |
| PT-12 | Behavior | Session | Decision Engine | Session start |
| PT-13 | Cross-Market | Daily | Decision Engine | Daily |
| PT-14 | Cross-Asset | Daily – Weekly | Decision Engine | Daily |
| PT-15 | Event | Event-specific | Decision Engine, StrategyLab | On calendar update |
| PT-16 | Scenario | Session | All primary consumers | Session start + triggers |
| PT-17 | Tail Risk | Session | RiskGuardian, RiskControl | Every 30 min |
| PT-18 | Distribution | Session | Capital Risk, Decision Engine | Session start + hourly |

---

## PART III — CORE COMPONENT ARCHITECTURE

### 3.1 Component Overview

The Prediction Engine comprises 20 core components organised in 4 operational tiers:

**Tier 1 — Storage and Registry (PC-01, PC-02)**
The persistent foundation: stores all prediction records, versions, and catalog entries.

**Tier 2 — Generation (PC-03 through PC-10)**
The active prediction machinery: builds, generates, and computes predictions, probabilities, and scenarios.

**Tier 3 — Validation and Governance (PC-11 through PC-15)**
The quality assurance layer: validates, compares, ranks, governs, and audits all prediction outputs.

**Tier 4 — Operations (PC-16 through PC-20)**
The operational layer: archives, monitors health, provides analytics, distributes outputs, and manages versions.

---

**Component Identification Format:** PC-{NN} — Prediction Component number NN.

**Component Health Contribution:** Each component contributes to the Prediction System Health Score (PSHS). Component health is computed as a weighted average of component-level indicators. PSHS is reported to ControlTower (Layer 17) every 60 seconds.

---

### 3.2 PC-01 — Prediction Registry

**Purpose:** The Prediction Registry is the operational store of all current and recent prediction records. It is the working memory of the Prediction Engine — the live, queryable index of every prediction that has been generated, is currently active, has been evaluated, or is pending evaluation.

**Responsibilities:**
- Maintain a complete, consistent index of all prediction records with their current lifecycle status
- Provide low-latency read access to active predictions for the Decision Engine and other consumers
- Support prediction record creation, status updates, and soft-deletion (status change to ARCHIVED)
- Enforce uniqueness of prediction record IDs
- Maintain a rolling window of recent predictions for immediate query
- Support queries by type, target, horizon, status, regime, and time range
- Propagate status change events to the EventBus for consumer notification

**Inputs:**
- New prediction records from the Prediction Builder (PC-03)
- Status update commands from the Prediction Governance Manager (PC-14)
- Outcome records from the Outcome Evaluation Pipeline (PP-09)
- Expiry triggers from the lifecycle management timer
- Human override commands from ControlTower (Layer 17)

**Outputs:**
- Prediction records in response to queries
- Status change events published to EventBus
- Registry health metrics to Prediction Health Manager (PC-17)
- Archive candidates to Prediction Archive Manager (PC-16)

**Dependencies:**
- SQLite persistent storage (via IIOS data layer)
- In-memory cache (for sub-millisecond active prediction reads)
- EventBus (Layer 17 / ControlTower)

**Interactions:**
- Prediction Builder (PC-03): receives new records on creation
- Prediction Governance Manager (PC-14): receives status update commands
- Prediction Archive Manager (PC-16): hands off records aged out of rolling window
- Decision Engine (Layer 10): serves active prediction reads

**Failure Modes:**
- In-memory cache inconsistency: cache and persistent store diverge after an unclean restart. Recovery: full cache rebuild from persistent store on startup.
- Status update lost: a status change event fails to propagate. Recovery: reconciliation scan on startup; status derived from record timestamps.
- Storage full: write attempts fail when storage approaches capacity. Recovery: emergency archive operation triggered; oldest evaluated records moved to cold storage.

**Recovery Strategy:**
Predictions Registry rebuilds from persistent store on every clean startup. The rebuild completes before any prediction reads are served to consumers. During rebuild, stale cached values from a previous session are served with a STALE label.

**Monitoring:**
- Registry size (record count by status)
- Read latency (P50, P95, P99)
- Write latency (P50, P95)
- Cache hit rate (target > 95%)
- Status inconsistency count (target = 0)

**Scalability:** Horizontal read scaling via read replicas. Registry write path is single-writer (serialized for consistency). Rolling window size is configurable (default: last 10 sessions).

**Extensibility:** New prediction types automatically inherit registry support through the common record schema. Type-specific indexes can be added without schema changes.

**Engineering Notes:** The Registry is the most read-intensive component in the Prediction Engine. The in-memory cache is the critical performance path. Cache invalidation strategy: time-based expiry with event-triggered invalidation on status changes.

---

### 3.3 PC-02 — Prediction Catalog

**Purpose:** The Prediction Catalog is the structured classification index for all validated prediction outputs. While the Registry tracks individual prediction records, the Catalog tracks patterns, calibration profiles, and ensemble weights by prediction type and regime. It is the Prediction Engine's institutional memory of what works, for which instruments, in which regimes.

**Responsibilities:**
- Maintain a classified index of calibration profiles for each prediction type and regime combination
- Store and version ensemble model weights per prediction type per regime
- Maintain a history of prediction accuracy, calibration, and skill metrics by type and regime
- Support queries: "What is the current calibration profile for PT-01 (Price) in RANGING regime?"
- Manage the active/inactive status of prediction models within each type
- Enforce naming standards and versioning for all catalog entries

**Inputs:**
- Calibration updates from the Confidence Engine (PC-07)
- Model improvement updates from Learning Engine (Layer 13)
- Ensemble weight updates from Ensemble Manager (PC-09)
- Outcome evaluation results from PP-09 (Outcome Evaluation Pipeline)

**Outputs:**
- Calibration profiles to Forecast Generator (PC-04) and Probability Engine (PC-06)
- Ensemble weight vectors to Ensemble Manager (PC-09)
- Historical accuracy profiles to Prediction Analytics Manager (PC-18)
- Catalog health metrics to Prediction Health Manager (PC-17)

**Dependencies:**
- Prediction Registry (PC-01) for individual prediction records
- Learning Engine (Layer 13) for model calibration updates
- SQLite persistent storage

**Interactions:**
- Forecast Generator (PC-04): provides calibration parameters at prediction generation time
- Probability Engine (PC-06): provides probability calibration factors
- Ensemble Manager (PC-09): provides and receives regime-specific ensemble weights
- Prediction Version Manager (PC-20): coordinates catalog entry versioning

**Failure Modes:**
- Stale calibration profile: catalog entry not updated despite model change. Recovery: Learning Engine triggers forced catalog refresh on model update deployment.
- Catalog entry conflict: two entries for same type/regime combination with different versions. Recovery: Version Manager resolves conflict using timestamp; older version archived.

**Recovery Strategy:** Full catalog loaded from persistent storage on startup. Missing entries trigger default calibration profile activation. Default profiles are deliberately conservative (wider uncertainty bounds) to avoid overconfident predictions during recovery.

**Monitoring:**
- Active calibration profiles by type and regime
- Profile age (time since last update)
- Calibration accuracy per profile (rolling 20-session)
- Model version coverage (all types covered)

**Scalability:** Catalog is read-optimized. Writes are infrequent (only on calibration updates). No horizontal scaling required.

**Engineering Notes:** The Catalog is the key to regime-aware prediction quality. Every calibration profile carries a egime_applicability field. When the current regime changes, the Catalog automatically selects the applicable profile set.

---

### 3.4 PC-03 — Prediction Builder

**Purpose:** The Prediction Builder is the intake and context-assembly component of the Prediction Engine. It does not generate predictions directly — it assembles the context, evidence package, and model inputs that the Forecast Generator, Scenario Generator, and Probability Engine require.

**Responsibilities:**
- Receive prediction requests (from Decision Engine, scheduled generation, or internal trigger)
- Collect and assemble the current context snapshot: regime, session state, portfolio state, active hypotheses, recent observations
- Fetch applicable evidence from Evidence Engine
- Select appropriate models from the Model Selector (PC-10)
- Fetch calibration profiles from the Prediction Catalog (PC-02)
- Bundle context, evidence, and model parameters into a Prediction Build Package
- Submit the Build Package to the appropriate generation component (PC-04, PC-05, PC-06)
- Create the initial prediction record shell in the Registry (PC-01)

**Inputs:**
- Prediction requests with type, target, horizon specifications
- Current regime state from MarketIntelligence (Layer 2)
- Current portfolio state from RiskControl (Layer 7)
- Active hypotheses from Hypothesis Engine
- Recent observations from Observation Engine
- Applicable evidence from Evidence Engine
- Calibration profile from Prediction Catalog (PC-02)
- Selected model set from Model Selector (PC-10)

**Outputs:**
- Prediction Build Packages to Forecast Generator (PC-04)
- Prediction Build Packages to Scenario Generator (PC-05)
- Prediction Build Packages to Probability Engine (PC-06)
- Initial prediction record shells to Prediction Registry (PC-01)

**Dependencies:**
- All input engines listed above
- Prediction Catalog (PC-02)
- Model Selector (PC-10)
- Prediction Registry (PC-01)

**Interactions:**
The Builder is the orchestrator of the prediction generation sequence. It coordinates the flow: request → context assembly → model selection → build package construction → generation dispatch.

**Failure Modes:**
- Incomplete context: one input source (e.g., Hypothesis Engine) unavailable. Recovery: proceed with available context; mark prediction as CONTEXT_INCOMPLETE; consumer sees reduced confidence.
- Stale context: cached context data is too old. Recovery: refuse to proceed until fresh context available; queue request.
- Model selection failure: no applicable model available for requested type+regime. Recovery: use fallback default model; mark prediction as DEFAULT_MODEL.

**Recovery Strategy:** Builder maintains a context freshness threshold (default: 30 seconds). Context older than threshold triggers a refresh request before building proceeds. If refresh fails within timeout (5 seconds), Builder proceeds with STALE_CONTEXT flag.

**Monitoring:**
- Build request rate
- Build latency (time from request to package dispatch)
- Incomplete context rate (target < 5%)
- Default model fallback rate (target < 10%)
- Queue depth (pending build requests)

**Scalability:** Multiple Builder instances can operate in parallel for different prediction types. Context state is shared read-only; no writer contention.

**Extensibility:** New prediction types require only a new context assembly configuration registered in the Builder. No structural changes required.

**Engineering Notes:** The Builder is the performance bottleneck for on-demand predictions during trading hours. Context assembly must complete within the 15ms budget for intraday price predictions. Pre-warming the context at session start is the primary optimization.

---

### 3.5 PC-04 — Forecast Generator

**Purpose:** The Forecast Generator is the primary quantitative prediction generation component. It takes a Prediction Build Package and produces a structured Forecast Record: a quantitative prediction of a specific measurable quantity at a defined future horizon, with full uncertainty characterization.

**Responsibilities:**
- Execute the statistical and model-based computation for each forecast type
- Produce point estimates, confidence intervals, and distributional summaries
- Apply regime-specific calibration factors from the Prediction Catalog
- Generate forecasts at all required horizons for the requested type
- Enforce temporal consistency: longer-horizon forecasts must be consistent with shorter-horizon forecasts
- Attach feature attribution reports to all AI-model-based forecasts
- Submit completed forecast records to the Prediction Registry (PC-01)
- Submit forecasts to the Ensemble Manager (PC-09) for aggregation

**Inputs:**
- Prediction Build Packages from Prediction Builder (PC-03)
- Regime-specific model parameters from Prediction Catalog (PC-02)
- Model outputs from Model Selector (PC-10) execution

**Outputs:**
- Structured Forecast Records (point estimate, confidence intervals, horizon, model attribution) to Prediction Registry
- Raw model outputs to Ensemble Manager (PC-09) for aggregation
- Feature attribution reports to Prediction Audit Manager (PC-15)

**Dependencies:**
- Prediction Builder (PC-03) for build packages
- Prediction Catalog (PC-02) for calibration
- Ensemble Manager (PC-09) for aggregation
- Model Selector (PC-10) for model execution

**Interactions:**
The Forecast Generator is downstream of the Builder and upstream of the Ensemble Manager. It operates in parallel for different prediction types (price, trend, volatility forecasts are generated simultaneously).

**Failure Modes:**
- Model computation failure: numerical instability or overflow in model computation. Recovery: fall back to simpler model class; mark as FALLBACK_MODEL.
- Calibration factor missing: no calibration profile for current regime. Recovery: use conservative default calibration (wider intervals); mark as UNCALIBRATED.
- Temporal inconsistency detected: generated forecasts violate horizon consistency. Recovery: apply consistency enforcement algorithm; log violation for investigation.

**Recovery Strategy:** The Forecast Generator operates with a two-level fallback: primary model → fallback model → default baseline (historical mean + 1-sigma intervals). The baseline is never a good forecast but is always a valid one.

**Monitoring:**
- Forecast generation latency by type
- Model failure rate
- Fallback activation rate
- Temporal consistency violation rate

**Scalability:** Forecast generation is embarrassingly parallel across types. Multiple instances for high-frequency PT-01 (Price) forecasts.

**Extensibility:** New forecast models register with the Model Selector. No changes to the Generator required.

**Engineering Notes:** Multi-horizon forecasting requires careful ordering: shortest horizon generated first, each subsequent horizon conditioned on prior horizon output. The temporal consistency enforcement algorithm adjusts longer-horizon estimates to avoid contradictions.

---

### 3.6 PC-05 — Scenario Generator

**Purpose:** The Scenario Generator produces structured scenario sets — complete, internally consistent, mutually exclusive, exhaustive narratives of possible future states. It is the most intellectually complex generation component, because it must synthesize all available prediction inputs into a coherent view of the full distribution of futures.

**Responsibilities:**
- Generate a complete scenario set for the current prediction horizon
- Ensure mutual exclusivity and exhaustiveness: scenarios must cover the full probability space and not overlap
- Assign probabilities to each scenario that are consistent with the distributional predictions (PT-18) and tail risk predictions (PT-17)
- For each scenario, specify: name, driving narrative, key market levels (NIFTY/BANKNIFTY), strategy implications, activation signal, probability, and termination condition
- Maintain a standard scenario taxonomy (BULL, BASE, BEAR, TAIL_DOWN, TAIL_UP) plus scenario-specific types
- Update scenario probabilities in real-time as new signals arrive
- Signal scenario transitions to the EventBus (new scenario activating as highest-probability)

**Inputs:**
- All active forecasts from Forecast Generator (PC-04)
- Probability distributions from Probability Engine (PC-06)
- Tail risk predictions (PT-17) from Forecast Generator
- Active hypotheses from Hypothesis Engine
- Macro scenario inputs from GlobalIntelligence (Layer 1)
- MarketSimulation scenario outputs (Layer 8)

**Outputs:**
- Active scenario sets to Prediction Registry (PC-01)
- Scenario change events to EventBus
- Current highest-probability scenario to Decision Engine (Layer 10)
- Tail scenarios to RiskGuardian (Layer 9)

**Dependencies:**
- All forecast outputs (PC-04)
- Probability Engine (PC-06)
- MarketSimulation (Layer 8)

**Interactions:**
The Scenario Generator is the synthesis component. It is the last major generation step before validation. It takes the quantitative predictions from PC-04 and PC-06 and gives them narrative coherence and strategic implication.

**Failure Modes:**
- Probability non-normalization: scenario probabilities do not sum to 1.0. Recovery: automatic normalization with audit log entry; investigate root cause.
- Scenario conflict: two scenarios have overlapping activation conditions. Recovery: merge conflicting scenarios or increase differentiation; log conflict.
- No scenarios generated (all models fail): Recovery: activate default defensive scenario set (50/50 bull/bear with wide uncertainty bounds).

**Recovery Strategy:** The Scenario Generator maintains a library of default scenario templates. If full generation fails, the default templates are instantiated with current market levels and conservative probability assignments.

**Monitoring:**
- Active scenario count
- Scenario probability sum (must equal 1.00)
- Scenario transition frequency
- Default template activation rate (target: 0%)
- Scenario narrative completeness score

**Scalability:** Scenario generation is session-start intensive. Intraday updates are lightweight (probability recalculation only). Scales by increasing computational resources at session start.

**Extensibility:** New scenario types register as templates in the Scenario Catalog (Supplement C). No structural changes required.

**Engineering Notes:** The quality of scenario generation depends on the quality of the upstream forecasts. Degraded forecast quality flows through directly to scenario quality. The Scenario Generator applies a minimum probability floor (2%) to all scenarios to prevent probability collapse to zero.

---

### 3.7 PC-06 — Probability Engine

**Purpose:** The Probability Engine is the dedicated component for computing, calibrating, and managing probability assignments across all prediction types. It is the quantitative heart of the Prediction Engine: transforming model outputs and evidence signals into well-calibrated probability statements.

**Responsibilities:**
- Compute probability assignments for all prediction types using Bayesian and frequentist methods
- Maintain and apply calibration corrections: adjust raw model probabilities to match observed frequencies
- Implement ensemble probability aggregation: combine probability estimates from multiple models
- Compute marginal and conditional probabilities for scenario analysis
- Ensure probability axioms are satisfied: all probabilities in [0,1]; mutually exclusive events sum correctly
- Monitor probability calibration in real-time: detect systematic over- or under-confidence
- Update probability estimates in real-time as new signals arrive (adaptive mode)

**Inputs:**
- Raw probability estimates from individual prediction models
- Evidence signals from Evidence Engine
- Prior probability distributions from Prediction Catalog (PC-02)
- Calibration corrections from Confidence Engine (PC-07)
- New observations from Observation Engine (for real-time Bayesian updates)

**Outputs:**
- Calibrated probability assignments to Forecast Generator (PC-04)
- Posterior probability distributions to Scenario Generator (PC-05)
- Conditional probability tables to Decision Engine (Layer 10)
- Probability calibration metrics to Confidence Engine (PC-07)

**Dependencies:**
- Prediction Catalog (PC-02) for prior distributions and calibration factors
- Confidence Engine (PC-07) for calibration corrections
- Evidence Engine for signal inputs
- Observation Engine for real-time update triggers

**Interactions:**
The Probability Engine and Confidence Engine work in a feedback loop: the Probability Engine produces raw probabilities; the Confidence Engine assesses their calibration; the calibration corrections flow back to the Probability Engine.

**Failure Modes:**
- Calibration data missing: no historical accuracy data for current type/regime. Recovery: use default (neutral) calibration; mark probabilities as UNCALIBRATED.
- Prior collapse: Bayesian updating drives posterior to near-zero or near-one. Recovery: apply probability floor (min 0.01) and ceiling (max 0.99) for distributable predictions.
- Numerical instability: floating-point underflow in extreme probability computations. Recovery: apply log-probability space computation.

**Recovery Strategy:** Probability Engine falls back to historical base rates from the Prediction Catalog if real-time model outputs are unavailable. Historical base rates are unconditionally available.

**Monitoring:**
- Calibration error by type and regime (target < 10%)
- Probability distribution coverage (none collapsed to 0 or 1)
- Real-time update latency
- Bayesian update count per session

**Scalability:** Probability computations are independent per prediction record. Highly parallelizable.

**Engineering Notes:** The log-probability space is used internally for all computations to avoid underflow. Only converted to probability space for output. All probability outputs are rounded to 3 decimal places for consistency.

---

### 3.8 PC-07 — Confidence Engine

**Purpose:** The Confidence Engine computes, monitors, and maintains the confidence score associated with every prediction. Confidence is the meta-level quality measure of a prediction: how much should the consumer trust this prediction's probability estimate? A prediction with probability 0.75 and confidence 0.40 is saying "we think this is 75% likely, but we are not very sure about that estimate."

**Responsibilities:**
- Compute confidence scores for every generated prediction, based on: evidence base quality, model calibration history, regime familiarity, data completeness, and signal consistency
- Maintain confidence calibration: historical confidence scores should correlate with prediction accuracy at the stated level
- Apply regime-specific confidence adjustments: confidence is lower in unfamiliar regimes
- Propagate confidence degradation: when an upstream input (evidence, observation) is low quality, confidence is reduced
- Detect confidence collapse: identify predictions that should not be distributed because confidence is below minimum threshold
- Provide confidence decay modeling: confidence decreases as time passes without an update to a given prediction

**Inputs:**
- Generated predictions from Forecast Generator (PC-04)
- Evidence quality scores from Evidence Engine
- Prediction Catalog calibration history (PC-02)
- Regime familiarity score from MarketIntelligence (Layer 2)
- Data completeness flags from Prediction Builder (PC-03)

**Outputs:**
- Confidence scores attached to all prediction records
- Confidence decay alerts when prediction confidence drops below threshold
- Confidence calibration metrics to Prediction Catalog (PC-02)
- Low-confidence alerts to Prediction Governance Manager (PC-14)

**Dependencies:**
- Evidence Engine for evidence quality inputs
- Prediction Catalog (PC-02) for historical calibration data
- Prediction Builder (PC-03) for context completeness flags

**Interactions:**
The Confidence Engine interacts closely with the Probability Engine (PC-06) and the Prediction Validator (PC-11). The confidence score is a key input to validation: predictions with confidence below the minimum threshold are not distributed.

**Failure Modes:**
- Confidence not computable: all evidence quality inputs unavailable. Recovery: assign MINIMUM_CONFIDENCE (0.25); mark prediction as CONFIDENCE_DEFAULT.
- Confidence overestimation: engine systematically assigns high confidence in volatile regimes. Recovery: regime-specific confidence penalty detected and applied by calibration monitor.

**Recovery Strategy:** Default confidence (0.40) is assigned when the full confidence computation cannot be completed. Default confidence is deliberately below the typical range to ensure consumers treat such predictions cautiously.

**Monitoring:**
- Average confidence by prediction type and regime
- Confidence calibration error (rolling 20 sessions)
- Below-threshold prediction rate (target < 5%)
- Confidence decay event rate

**Scalability:** Confidence computation is lightweight. Scales horizontally with prediction volume.

**Engineering Notes:** Confidence is a first-class field in every prediction record. It is never omitted. Consumers (especially the Decision Engine) weight predictions by their confidence scores in multi-prediction aggregation.

---

### 3.9 PC-08 — Uncertainty Engine

**Purpose:** The Uncertainty Engine is responsible for explicitly quantifying, representing, and propagating the uncertainty inherent in every prediction. While the Confidence Engine measures how much to trust a prediction's probability, the Uncertainty Engine measures the range of possible outcomes: how wide is the cone of uncertainty around the central forecast?

**Responsibilities:**
- Compute uncertainty bounds (lower, upper) for every quantitative forecast
- Characterize the type of uncertainty: aleatory (irreducible, market noise) vs epistemic (reducible, data or model limitations)
- Propagate uncertainty through multi-step prediction chains (uncertainty compounds over horizons)
- Compute tail uncertainty: the probability and magnitude of outcomes beyond the stated bounds
- Detect uncertainty underestimation: a systematic bias where the system generates unrealistically tight bounds
- Provide uncertainty decomposition: attribution of total uncertainty to specific sources (data quality, model error, regime uncertainty, parameter uncertainty)

**Inputs:**
- Point estimates and model outputs from Forecast Generator (PC-04)
- Distribution predictions from Probability Engine (PC-06)
- Calibration history from Prediction Catalog (PC-02)
- Regime volatility state from MarketIntelligence (Layer 2)

**Outputs:**
- Uncertainty bounds (1-sigma, 2-sigma) attached to all prediction records
- Uncertainty decomposition reports to Prediction Analytics Manager (PC-18)
- Uncertainty calibration metrics to Prediction Catalog (PC-02)
- Tail uncertainty inputs to Scenario Generator (PC-05) for tail scenario construction

**Dependencies:**
- Forecast Generator (PC-04)
- Probability Engine (PC-06)
- Prediction Catalog (PC-02)

**Interactions:**
The Uncertainty Engine is a peer to the Confidence Engine. Confidence relates to model quality; Uncertainty relates to outcome range. Both are required fields in every prediction record.

**Failure Modes:**
- Uncertainty collapse: computed bounds are unrealistically tight (common model failure in low-volatility regimes followed by sudden volatility expansion). Recovery: apply minimum uncertainty floor (based on asset class and horizon).
- Uncertainty explosion: computed bounds are so wide as to be useless. Recovery: cap uncertainty at maximum useful width; log as DEGENERATE_UNCERTAINTY.

**Recovery Strategy:** Minimum uncertainty bounds (floors) are hard-coded per prediction type and horizon in the Prediction Catalog. These floors prevent the Uncertainty Engine from producing overconfident intervals even when models suggest higher precision.

**Monitoring:**
- Average uncertainty width by type and horizon
- Uncertainty calibration (stated intervals should contain actual outcomes at stated frequency)
- Uncertainty floor activation rate (target < 10%)
- Uncertainty collapse detection rate (target = 0)

**Engineering Notes:** The Uncertainty Engine is critical for capital sizing. Wider uncertainty on a price prediction → wider position risk → smaller position size (Capital Risk Engine). Incorrect uncertainty estimation directly affects position sizing accuracy.

---

### 3.10 PC-09 — Ensemble Manager

**Purpose:** The Ensemble Manager aggregates the outputs of multiple prediction models to produce a single, higher-quality ensemble prediction. Ensemble methods consistently outperform individual models by averaging out individual model errors.

**Responsibilities:**
- Maintain an active ensemble configuration for each prediction type and regime
- Execute the ensemble aggregation: collect model outputs, apply weights, produce weighted aggregate
- Manage ensemble weights: update weights based on recent individual model performance
- Support multiple aggregation methods: weighted average, Bayesian model averaging, stacking
- Detect and handle model disagreement: when models disagree significantly, flag the prediction as HIGH_DISAGREEMENT and widen uncertainty bounds
- Maintain model performance tracking: for each model in each ensemble, track accuracy, calibration, and regime-specific performance

**Inputs:**
- Raw model outputs from Forecast Generator (PC-04)
- Model performance history from Prediction Catalog (PC-02)
- Current regime from MarketIntelligence (Layer 2)
- Ensemble weight updates from Learning Engine (Layer 13)

**Outputs:**
- Ensemble-aggregated predictions to Prediction Registry (PC-01)
- Model disagreement flags to Confidence Engine (PC-07)
- Model performance data to Prediction Catalog (PC-02) for weight updates
- Ensemble composition reports to Prediction Audit Manager (PC-15)

**Dependencies:**
- Forecast Generator (PC-04) for individual model outputs
- Prediction Catalog (PC-02) for ensemble weights
- Learning Engine (Layer 13) for weight optimization

**Interactions:**
The Ensemble Manager is the final aggregation step in the generation pipeline before validation. Its output is the "official" prediction of the Prediction Engine.

**Failure Modes:**
- All models fail: no model output available for aggregation. Recovery: activate the single best historical model as emergency fallback; mark as SINGLE_MODEL_FALLBACK.
- Weight corruption: ensemble weights don't sum to 1.0. Recovery: renormalize; alert; investigate.
- Catastrophic disagreement: models produce fully contradictory predictions. Recovery: distribute all predictions with HIGH_DISAGREEMENT flag; do not aggregate to a single point.

**Recovery Strategy:** The Ensemble Manager maintains a minimum viable ensemble: at least one model must be available for each major prediction type (PT-01, PT-02, PT-03, PT-16). If fewer models are available, ensemble advantages are reduced but predictions continue.

**Monitoring:**
- Active model count per ensemble per type
- Inter-model disagreement distribution
- Ensemble weight concentration (Herfindahl index — avoids over-reliance on single model)
- Weight update frequency
- Fallback activation rate

**Engineering Notes:** The ensemble is dynamically configured by regime. When the regime transitions, the Ensemble Manager immediately switches to the ensemble weights appropriate for the new regime. Weights are stored in the Prediction Catalog.

---

### 3.11 PC-10 — Model Selector

**Purpose:** The Model Selector is responsible for selecting the appropriate set of prediction models for a given prediction request, based on the prediction type, target instrument, current regime, and available model versions.

**Responsibilities:**
- Maintain a registry of all available prediction models with their metadata: type applicability, regime applicability, instrument applicability, version, status, performance history
- Select the optimal model set for each prediction request
- Apply model exclusion rules: models that are degraded, in drift monitoring, or suspended are excluded
- Support model A/B testing: for experimental models, allocate a defined fraction of predictions to the experimental model
- Report model selection decisions to the Prediction Audit Manager (PC-15)
- Manage model lifecycle: active, degraded, suspended, retired

**Inputs:**
- Prediction request specifications from Prediction Builder (PC-03)
- Model registry from Prediction Catalog (PC-02)
- Model health status from Prediction Health Manager (PC-17)
- Model selection overrides from Learning Engine (Layer 13)

**Outputs:**
- Selected model set to Prediction Builder (PC-03) for build package construction
- Model selection log to Prediction Audit Manager (PC-15)
- Model utilization metrics to Prediction Analytics Manager (PC-18)

**Dependencies:**
- Prediction Catalog (PC-02) for model registry
- Prediction Health Manager (PC-17) for model health status

**Interactions:**
The Model Selector is invoked by the Prediction Builder before every prediction generation request. Its selection decision determines which models will execute.

**Failure Modes:**
- No eligible models: all models for a type/regime combination are degraded or suspended. Recovery: activate default baseline model; alert operator.
- Model registry stale: registry has not been updated with latest Learning Engine changes. Recovery: force registry refresh; proceed with current registry.

**Recovery Strategy:** Every prediction type has a designated fallback model that is never deactivated. The fallback model is simple, robust, and historically validated. It may produce lower-quality predictions but always produces valid ones.

**Monitoring:**
- Model availability by type and regime
- Model selection frequency (is any model being over-relied on?)
- Fallback model activation rate (target < 5%)
- A/B test allocation accuracy

**Engineering Notes:** The Model Selector is a configuration-driven component. New models are registered through configuration changes, not code changes. The selection algorithm is rule-based and auditable.

---

### 3.12 PC-11 — Prediction Validator

**Purpose:** The Prediction Validator runs a structured validation pipeline on every generated prediction before it is approved for distribution. No prediction leaves the Prediction Engine without having passed all applicable validation checks.

**Responsibilities:**
- Execute the 5-stage validation pipeline: Structural Validity, Evidence Grounding, Probability Integrity, Calibration Check, Regime Applicability
- Assign a validation status to every prediction: VALIDATED, CONDITIONALLY_VALIDATED, FLAGGED, REJECTED
- Compute the Prediction Quality Score (PQS) for every prediction
- Maintain validation statistics for quality monitoring
- Reject predictions that fail hard validation rules
- Flag (but not reject) predictions that fail soft validation rules, allowing consumer discretion
- Escalate systematic validation failures to the Prediction Governance Manager (PC-14)

**Inputs:**
- Generated predictions from Ensemble Manager (PC-09) and Forecast Generator (PC-04)
- Calibration profiles from Prediction Catalog (PC-02)
- Evidence quality scores from Evidence Engine
- Current regime from MarketIntelligence (Layer 2)

**Outputs:**
- Validation status attached to all prediction records
- PQS scores for all predictions
- Validation failure reports to Prediction Governance Manager (PC-14)
- Validation metrics to Prediction Health Manager (PC-17)

**Dependencies:**
- Prediction Catalog (PC-02) for calibration standards
- Evidence Engine for evidence grounding verification

**Interactions:**
The Prediction Validator is the quality gate between prediction generation and prediction distribution. Every prediction passes through it exactly once (on initial generation) and may be re-validated after an update.

**Failure Modes:**
- Validator unavailable: cannot validate predictions. Recovery: predictions are held in PENDING_VALIDATION queue; distributed with WARNING_UNVALIDATED flag if queue wait exceeds 30 seconds.
- All predictions failing validation: systematic upstream issue. Recovery: Escalate immediately; suspend prediction distribution; alert operator.

**Recovery Strategy:** The Validator applies a tiered validation: hard rules (structural validity, probability axioms) are blocking; soft rules (calibration quality, evidence depth) are flagging only. This ensures that even in degraded conditions, some predictions pass validation.

**Monitoring:**
- Validation pass rate (target > 90%)
- Rejection rate by type and rule
- PQS distribution (rolling 5 sessions)
- Systematic validation failure detection

**Engineering Notes:** The 5-stage validation pipeline is described in detail in Part IV. PQS computation uses the 13-dimension quality framework defined in Part VII.

---

### 3.13 PC-12 — Prediction Comparator

**Purpose:** The Prediction Comparator tracks predictions against each other and against prior predictions, identifying consistency, drift, and contradictions in the Prediction Engine's output. It answers: Is the current prediction consistent with yesterday's prediction for the same target? Is the current price prediction consistent with the current trend prediction?

**Responsibilities:**
- Compare current predictions against prior predictions for the same target and horizon
- Detect cross-type prediction inconsistencies: a bullish price prediction (PT-01) inconsistent with a bearish trend prediction (PT-02)
- Track prediction drift: systematic directional changes in predictions over time without corresponding market changes
- Compute prediction correlation: how strongly do predictions for related instruments covary?
- Produce comparison reports for the Decision Engine's debate process
- Alert Prediction Governance Manager when systematic inconsistencies are detected

**Inputs:**
- Current predictions from Prediction Registry (PC-01)
- Historical predictions from Prediction Archive Manager (PC-16)
- Cross-type prediction set from Prediction Registry

**Outputs:**
- Consistency flags attached to prediction records
- Cross-type inconsistency alerts to Prediction Governance Manager (PC-14)
- Comparison metrics to Prediction Analytics Manager (PC-18)
- Historical comparison reports to Decision Engine (Layer 10)

**Failure Modes:**
- Historical comparison data unavailable: first session of a new instrument. Recovery: skip cross-session comparison; intra-session comparisons proceed.
- Spurious inconsistency detection: two predictions appear inconsistent due to different effective horizons. Recovery: horizon-normalize before comparison.

**Monitoring:**
- Cross-type consistency rate (target > 85%)
- Session-over-session prediction change magnitude
- Inconsistency detection rate

---

### 3.14 PC-13 — Prediction Ranking Engine

**Purpose:** The Prediction Ranking Engine produces prioritized rankings of predictions for the Decision Engine and other consumers. When multiple predictions are available for related targets, the Ranking Engine determines which predictions should receive the most weight in decision making.

**Responsibilities:**
- Rank active predictions by confidence score, PQS score, and evidence depth
- Produce ranked prediction lists for each decision context
- Apply regime-specific ranking weights: in trending regimes, trend predictions (PT-02) rank higher; in volatile regimes, tail risk predictions (PT-17) rank higher
- Maintain ranking history to detect systematic ranking instability
- Support consumer-specific ranking views: the Decision Engine's ranking criteria differ from MetaLearning's ranking criteria

**Inputs:**
- All validated predictions from Prediction Registry (PC-01)
- Confidence scores from Confidence Engine (PC-07)
- PQS scores from Prediction Validator (PC-11)
- Current regime from MarketIntelligence (Layer 2)
- Consumer-specific ranking profiles from Prediction Catalog (PC-02)

**Outputs:**
- Ranked prediction lists to Decision Engine (Layer 10)
- Ranked strategy predictions to MetaLearning (Layer 3)
- Ranked risk predictions to RiskControl (Layer 7) and RiskGuardian (Layer 9)

**Failure Modes:**
- All predictions low quality (all PQS < 0.35): no high-quality ranking available. Recovery: distribute ranking with ALL_LOW_QUALITY flag; consumer applies conservative defaults.

**Monitoring:**
- Top-ranked prediction quality distribution
- Ranking stability (frequency of rank changes per session)

**Engineering Notes:** Ranking is not selection. The Ranking Engine presents ranked predictions; consumers decide what to act on. No prediction is ever "blocked" by ranking — ranking is advisory.

---

### 3.15 PC-14 — Prediction Governance Manager

**Purpose:** The Prediction Governance Manager is the approval authority for all prediction outputs and manages the governance lifecycle: review, approval, conditional approval, rejection, and retirement of prediction outputs and prediction models.

**Responsibilities:**
- Enforce prediction governance tiers: TIER-1-AUTO (fully automated), TIER-2-ADVISORY (automated with notification), TIER-3-HUMAN (human review required)
- Process governance escalations from Prediction Validator (PC-11) and Prediction Comparator (PC-12)
- Maintain the governance queue: items pending human review
- Manage prediction retirement: formally retire predictions that are consistently low quality or no longer applicable
- Enforce constitutional rules (Part IX) on all prediction outputs
- Issue governance decisions: APPROVE, CONDITIONALLY_APPROVE, REJECT, ESCALATE

**Inputs:**
- Validation failure reports from Prediction Validator (PC-11)
- Inconsistency alerts from Prediction Comparator (PC-12)
- Human operator decisions via Telegram bot interface
- Model performance degradation alerts from Prediction Health Manager (PC-17)

**Outputs:**
- Governance decisions to Prediction Registry (PC-01) for status updates
- Governance queue items to human operators (via Telegram)
- Model retirement recommendations to Model Selector (PC-10)
- Governance metrics to Prediction Audit Manager (PC-15)

**Dependencies:**
- Prediction Validator (PC-11), Prediction Comparator (PC-12)
- Human operator interface (Telegram bot, ControlTower dashboard)
- Prediction Audit Manager (PC-15) for immutable logging

**Failure Modes:**
- Governance queue overflow: more items than operators can process. Recovery: auto-escalate oldest items; apply conservative default decisions after timeout.
- Human operator unavailable: TIER-3 items cannot be resolved. Recovery: hold affected predictions in PENDING_GOVERNANCE; apply conservative distribution until resolved.

**Monitoring:**
- Queue depth (target < 5 items)
- Queue age (oldest item age; target < 24 hours)
- Governance decision distribution (approve/reject/escalate rates)

---

### 3.16 PC-15 — Prediction Audit Manager

**Purpose:** The Prediction Audit Manager maintains the immutable, tamper-evident audit log of every significant event in the prediction lifecycle: generation, validation, governance decision, distribution, update, outcome evaluation, and retirement.

**Responsibilities:**
- Append audit entries for all significant prediction lifecycle events
- Maintain hash-chain integrity: each audit entry references the hash of the prior entry
- Verify hash-chain integrity on startup and on demand
- Provide audit queries for governance reviews, incident investigation, and compliance reporting
- Archive completed audit segments to cold storage
- Alert on hash-chain integrity failure: this is an emergency condition

**Inputs:**
- Lifecycle events from all Prediction Engine components
- Governance decisions from Prediction Governance Manager (PC-14)
- Human override events from ControlTower (Layer 17)

**Outputs:**
- Audit log (append-only, hash-linked)
- Integrity verification reports to Prediction Governance Manager (PC-14)
- Audit query results to authorized consumers

**Dependencies:**
- All Prediction Engine components (event sources)
- Persistent storage (append-only log file)

**Failure Modes:**
- Audit Manager unavailable: per constitutional rule (equivalent to GDR-PRD-004), all prediction distributions are suspended until the Audit Manager is restored.
- Hash chain integrity failure: emergency halt of Prediction Engine; full audit investigation required before resuming.

**Monitoring:**
- Audit log growth rate
- Hash chain verification status (must = INTACT)
- Audit query latency
- Segment archive status

---

### 3.17 PC-16 — Prediction Archive Manager

**Purpose:** The Prediction Archive Manager manages the permanent archive of all historical prediction records. Nothing is ever deleted from the archive — every prediction ever generated, along with its outcome evaluation, is permanently preserved.

**Responsibilities:**
- Move aged records from the Prediction Registry to the archive based on retention rules
- Maintain archive indexing for efficient historical queries
- Provide historical prediction data to the Outcome Evaluation Pipeline (PP-09) and Learning Engine (Layer 13)
- Verify archive integrity periodically
- Manage storage tiering: recent archive in warm storage; older archive in cold storage
- Support archive queries for model back-testing and validation

**Inputs:**
- Archive candidates from Prediction Registry (PC-01)
- Outcome evaluation results from PP-09
- Retention policy from Prediction Governance Manager (PC-14)

**Outputs:**
- Archived prediction records (query responses)
- Archive integrity reports to Prediction Health Manager (PC-17)
- Historical prediction data to Learning Engine (Layer 13) and ValidationEngine (Layer 16)

**Failure Modes:**
- Archive write failure: records cannot be archived. Recovery: records remain in Registry; alert operator; investigate storage.
- Archive read failure: historical queries fail. Recovery: serve from Registry if available; alert operator.

**Monitoring:**
- Archive size and growth rate
- Archive query latency
- Archive integrity verification status

---

### 3.18 PC-17 — Prediction Health Manager

**Purpose:** The Prediction Health Manager monitors the health of all 20 Prediction Engine components and computes the Prediction System Health Score (PSHS), which is reported to ControlTower (Layer 17) every 60 seconds.

**Responsibilities:**
- Monitor all 20 Prediction Engine components for liveness, performance, and error rates
- Compute PSHS as a weighted average of component health scores
- Alert ControlTower and human operators when PSHS drops below threshold
- Maintain component health history for trend analysis
- Classify health states: NOMINAL, DEGRADED, CRITICAL, FAILED
- Coordinate component restart sequences when failures occur

**Inputs:**
- Health metrics from all 20 Prediction Engine components
- Process monitoring signals (component liveness checks)

**Outputs:**
- PSHS to ControlTower (Layer 17) every 60 seconds
- Component health alerts to human operators (via Telegram)
- Health trend reports to Prediction Analytics Manager (PC-18)

**Monitoring:**
PSHS target thresholds:
- NOMINAL: PSHS > 0.80
- DEGRADED: 0.55 < PSHS ≤ 0.80
- CRITICAL: 0.35 < PSHS ≤ 0.55
- EMERGENCY: PSHS ≤ 0.35

---

### 3.19 PC-18 — Prediction Analytics Manager

**Purpose:** Produces multi-dimensional analytics across all prediction types, model performance, calibration trends, and quality metrics. Feeds the ControlTower dashboard and Learning Engine.

**Responsibilities:**
- Compute accuracy, calibration, and skill metrics for all active prediction types
- Produce session-end analytics reports
- Identify underperforming models for Learning Engine feedback
- Provide trending analysis: are predictions getting better or worse over time?
- Generate forecast skill scores (Brier Score, CRPS) for probabilistic predictions

**Inputs:**
- Historical predictions from Archive Manager (PC-16)
- Outcome evaluations from PP-09
- Component metrics from all generation components

**Outputs:**
- Analytics reports to ControlTower (Layer 17) dashboard
- Model performance reports to Learning Engine (Layer 13)
- Skill metrics to Prediction Catalog (PC-02) for model weight updates

---

### 3.20 PC-19 — Prediction Distribution Manager

**Purpose:** Manages the controlled distribution of validated, governed predictions to authorized consumers. Ensures that the right predictions reach the right consumers at the right time, with appropriate access controls.

**Responsibilities:**
- Route validated predictions to registered consumers by type and regime
- Apply distribution filters: consumers receive only prediction types they are registered for
- Manage distribution timing: some predictions are distributed on generation; others batch-distributed at defined intervals
- Handle distribution failures: re-queue and retry failed deliveries
- Log all distributions to the Prediction Audit Manager (PC-15)

**Inputs:**
- Validated prediction records from Prediction Validator (PC-11)
- Governance approvals from Prediction Governance Manager (PC-14)
- Consumer registration profiles from Prediction Catalog (PC-02)

**Outputs:**
- Distributed predictions to registered consumers
- Distribution receipts to Prediction Audit Manager (PC-15)
- Distribution metrics to Prediction Health Manager (PC-17)

---

### 3.21 PC-20 — Prediction Version Manager

**Purpose:** Manages versioning of all prediction models, calibration profiles, and ensemble configurations. Ensures that every prediction can be reproduced with the exact model versions that generated it.

**Responsibilities:**
- Assign version identifiers to all prediction models: PVR-{TARGET}-{VERSION:04d}
- Maintain the version history of all model calibration parameters
- Support rollback to prior model versions when current version underperforms
- Provide version lineage for prediction audit queries
- Enforce version consistency: predictions generated from a consistent model version set

**Inputs:**
- Model update events from Learning Engine (Layer 13)
- Rollback requests from Prediction Governance Manager (PC-14)

**Outputs:**
- Current version sets to all generation components
- Version history to Prediction Archive Manager (PC-16)
- Rollback confirmations to Prediction Governance Manager (PC-14)

**Monitoring:**
- Active version count per prediction type
- Version age (time since last update)
- Rollback event rate (target < 5% of deployed updates)

**Engineering Notes:** Version Manager is the critical component for prediction reproducibility. Given a prediction ID, the Version Manager can reconstruct the exact model version set, parameter values, and calibration factors that produced it. This is a strict audit requirement.

---

## PART IV — PREDICTION LIFECYCLE

### 4.1 Overview

Every prediction in the IIOS passes through a defined lifecycle. The lifecycle governs how a prediction is created, validated, distributed, monitored, evaluated against outcomes, and ultimately archived or retired. The lifecycle ensures that every prediction is accountable: it was created for a reason, it was validated before distribution, it was compared to reality after the horizon passed, and the result was fed back to improve future predictions.

**Prediction Lifecycle Stage Identifier Format:** PLS-{NN}

---

### 4.2 Lifecycle Stages

**PLS-01 — Data Intake**

The lifecycle begins when the Prediction Builder (PC-03) receives a prediction request and assembles the required input data: price observations, evidence signals, hypothesis states, reasoning conclusions, learning calibrations, and regime context.

Data intake is subject to freshness validation: inputs older than the configured freshness threshold trigger a refresh before proceeding. If refresh fails, the prediction proceeds with a STALE_INPUT flag.

*State:* INTAKE_IN_PROGRESS → INTAKE_COMPLETE

---

**PLS-02 — Context Building**

The Prediction Builder assembles the full prediction context: current regime, session state, portfolio state, active hypotheses, and model selection. The context snapshot is timestamped with point-in-time (PIT) semantics: all context elements reflect the state of the world at the exact time the context was assembled.

The context snapshot is the permanent, immutable record of what the Prediction Engine "knew" when it made the prediction. It is stored alongside the prediction record and used for post-hoc analysis.

*State:* CONTEXT_BUILD_IN_PROGRESS → CONTEXT_COMPLETE

---

**PLS-03 — Forecast Generation**

The Forecast Generator (PC-04) executes the selected models on the context and produces raw forecast outputs: point estimates, confidence intervals, and distributional summaries. Forecast generation runs in parallel for all required horizons of the requested type.

*State:* GENERATION_IN_PROGRESS → GENERATED

---

**PLS-04 — Probability Assignment**

The Probability Engine (PC-06) takes the raw forecast outputs and converts them into calibrated probability assignments. Bayesian priors from the Prediction Catalog are applied. Evidence signals update the posterior probabilities.

*State:* PROBABILITY_IN_PROGRESS → PROBABILITY_ASSIGNED

---

**PLS-05 — Scenario Generation**

For PT-16 (Scenario Prediction) and for full-context predictions, the Scenario Generator (PC-05) constructs the scenario set: the structured set of alternative futures with their probabilities, drivers, and implications.

Scenarios are verified for probability normalization (sum = 1.00) before proceeding.

*State:* SCENARIO_GENERATION_IN_PROGRESS → SCENARIOS_COMPLETE

---

**PLS-06 — Confidence Assessment**

The Confidence Engine (PC-07) and Uncertainty Engine (PC-08) compute the confidence score and uncertainty bounds for each forecast. These two values are attached to the prediction record.

A confidence score below the minimum threshold (default: 0.25) causes the prediction to be flagged as LOW_CONFIDENCE. Predictions with LOW_CONFIDENCE are still distributed but carry a prominent flag.

*State:* CONFIDENCE_IN_PROGRESS → CONFIDENCE_ASSESSED

---

**PLS-07 — Ensemble Aggregation**

The Ensemble Manager (PC-09) aggregates outputs from multiple models into the final ensemble prediction. The ensemble aggregation step produces the official Prediction Engine output.

*State:* ENSEMBLE_IN_PROGRESS → ENSEMBLE_COMPLETE

---

**PLS-08 — Validation**

The Prediction Validator (PC-11) runs the 5-stage validation pipeline on the ensemble prediction. The pipeline stages are:

**Stage V-01 — Structural Validity:**
Verify that the prediction record is complete: all required fields present, no null values in mandatory fields, prediction type is recognized, target instrument is valid.
*Hard rule: structural failure → REJECTED*

**Stage V-02 — Probability Integrity:**
Verify that all probability values are in [0,1]. Verify that scenario probabilities sum to 1.00. Verify that confidence is in [0,1]. Verify that uncertainty bounds are well-formed (lower < upper).
*Hard rule: probability axiom violation → REJECTED*

**Stage V-03 — Evidence Grounding:**
Verify that the prediction is supported by at least one piece of current (within-session) evidence with confidence > 0.40. Predictions generated without any evidence are flagged as UNSUPPORTED.
*Soft rule: failure → FLAGGED (not rejected)*

**Stage V-04 — Calibration Check:**
Compare the prediction's stated confidence with the historical calibration data for this type/regime combination. Flag if the stated confidence is outside ±2 standard deviations of the historical calibration range.
*Soft rule: failure → CONDITIONALLY_VALIDATED*

**Stage V-05 — Regime Applicability:**
Verify that the model(s) used to generate the prediction have a track record in the current regime. Models with fewer than 5 sessions of history in the current regime are flagged as REGIME_UNTESTED.
*Soft rule: failure → FLAGGED*

*Overall validation outcomes:*
- All stages pass → VALIDATED
- Stage V-03, V-04, or V-05 fail (soft rules only) → CONDITIONALLY_VALIDATED or FLAGGED
- Stage V-01 or V-02 fail → REJECTED (prediction not distributed)

*State:* VALIDATION_IN_PROGRESS → VALIDATED / CONDITIONALLY_VALIDATED / FLAGGED / REJECTED

---

**PLS-09 — Comparison**

The Prediction Comparator (PC-12) compares the validated prediction against:
(a) The prior prediction for the same target and horizon (from the previous session or previous generation cycle)
(b) Concurrent predictions of related types (cross-type consistency check)

Significant deviations from prior predictions trigger a PREDICTION_DRIFT flag. Cross-type inconsistencies trigger an INCONSISTENT flag.

*State:* COMPARISON_IN_PROGRESS → COMPARISON_COMPLETE

---

**PLS-10 — Governance and Approval**

The Prediction Governance Manager (PC-14) processes governance decisions based on the prediction's flags and quality scores.

**TIER-1-AUTO:** Validated predictions with PQS ≥ 0.72 and no flags → automatic approval, distribute immediately.

**TIER-2-ADVISORY:** Predictions with CONDITIONALLY_VALIDATED, FLAGGED, or PQS in [0.56, 0.71] → automatic approval with operator notification.

**TIER-3-HUMAN:** Predictions with LOW_CONFIDENCE, INCONSISTENT, PREDICTION_DRIFT flags, or PQS < 0.56 → hold for human operator review. If operator approves within timeout (2 minutes for intraday predictions), distribute. If timeout, distribute with AWAITING_HUMAN_REVIEW flag.

*State:* GOVERNANCE_IN_PROGRESS → APPROVED / CONDITIONALLY_APPROVED / REJECTED / AWAITING_REVIEW

---

**PLS-11 — Distribution**

The Prediction Distribution Manager (PC-19) distributes approved predictions to all registered consumers. Distribution is logged by the Prediction Audit Manager (PC-15) for every prediction-consumer pair.

*State:* DISTRIBUTION_IN_PROGRESS → DISTRIBUTED

---

**PLS-12 — Monitoring**

After distribution, the Prediction Engine monitors the prediction's trajectory toward its horizon. Monitoring serves two purposes:

1. **Accuracy monitoring:** Track how well the current prediction is tracking reality as the horizon approaches.
2. **Invalidation detection:** Detect when the conditions that justified the prediction have changed materially, requiring the prediction to be updated or superseded.

Monitoring events include: prediction update (probability revision), prediction superseded (new prediction for same target), prediction invalidated (regime change makes prediction irrelevant), prediction affirmed (intermediate signals consistent with prediction).

*State:* DISTRIBUTED → MONITORING

---

**PLS-13 — Outcome Evaluation**

When the prediction horizon arrives, the Prediction Engine retrieves the actual outcome and evaluates the prediction's accuracy. Outcome evaluation computes:

- Was the prediction directionally correct?
- Was the actual outcome within the stated confidence interval?
- What was the prediction's calibration error (stated probability vs observed frequency)?
- What was the Brier Score (probabilistic accuracy metric) for this prediction?

These metrics are written back to the prediction record and forwarded to the Learning Engine (Layer 13) for model improvement.

*State:* MONITORING → OUTCOME_EVALUATED

---

**PLS-14 — Archive**

After outcome evaluation, the prediction record is archived: moved from the active Prediction Registry to the Prediction Archive. Archived predictions are fully queryable and permanently preserved.

*State:* OUTCOME_EVALUATED → ARCHIVED

---

**PLS-15 — Retirement**

Prediction models or prediction types that are consistently underperforming (PQS < 0.35 for 20+ sessions) may be formally retired. Retired prediction types are no longer generated. Retired models are no longer selected. All historical records of retired types/models remain permanently in the archive.

*State:* ARCHIVED → (model → RETIRED; record stays ARCHIVED permanently)

---

### 4.3 Prediction Lifecycle State Transition Diagram

`
                     PREDICTION LIFECYCLE STATE MACHINE
                     ════════════════════════════════════

  NEW_REQUEST
      │
      ▼
  INTAKE_IN_PROGRESS ──→ INTAKE_COMPLETE
                                │
                                ▼
                   CONTEXT_BUILD_IN_PROGRESS ──→ CONTEXT_COMPLETE
                                                       │
                                                       ▼
                                           GENERATION_IN_PROGRESS ──→ GENERATED
                                                                           │
                                                                           ▼
                                                               PROBABILITY_ASSIGNED
                                                                           │
                                                                           ▼
                                                              SCENARIOS_COMPLETE (if applicable)
                                                                           │
                                                                           ▼
                                                              CONFIDENCE_ASSESSED
                                                                           │
                                                                           ▼
                                                              ENSEMBLE_COMPLETE
                                                                           │
                                         ╔══════════════════════════════╗
                                         ║       VALIDATION GATE         ║
                                         ╚══════════════════════════════╝
                                                                           │
                                   ┌───────────────┬──────────────────────┤
                                   │               │                      │
                               VALIDATED   CONDITIONALLY_           REJECTED
                                   │         VALIDATED                    │
                                   └────────────┬──                 ARCHIVED
                                                │
                                         COMPARISON_COMPLETE
                                                │
                                         ╔════════════════════╗
                                         ║   GOVERNANCE GATE   ║
                                         ╚════════════════════╝
                                                │
                            ┌───────────────────┤
                            │                   │
                       APPROVED         AWAITING_REVIEW
                            │
                       DISTRIBUTED
                            │
                       MONITORING
                            │
                   (horizon arrives)
                            │
                   OUTCOME_EVALUATED
                            │
                       ARCHIVED ──────────────────→ (model) RETIRED
`

---

### 4.4 Prediction Status Reference

| Status | Meaning | Distributable? |
|---|---|---|
| INTAKE_IN_PROGRESS | Data being collected | No |
| CONTEXT_COMPLETE | Context assembled, generation pending | No |
| GENERATED | Raw forecast produced | No |
| PROBABILITY_ASSIGNED | Probabilities computed | No |
| SCENARIOS_COMPLETE | Scenarios generated | No |
| CONFIDENCE_ASSESSED | Confidence and uncertainty attached | No |
| ENSEMBLE_COMPLETE | Ensemble aggregation done | No |
| VALIDATED | Passed all validation stages | Pending governance |
| CONDITIONALLY_VALIDATED | Passed hard rules, soft rule flags | Pending governance |
| FLAGGED | Soft rule failures; governance review | Pending governance |
| REJECTED | Hard rule failure | Never |
| AWAITING_REVIEW | Held for human approval | No |
| APPROVED | Governance approved | Yes |
| DISTRIBUTED | Delivered to consumers | Yes |
| MONITORING | Active monitoring post-distribution | Yes |
| UPDATED | Prediction probability revised | Yes |
| SUPERSEDED | Replaced by newer prediction | Historical |
| INVALIDATED | Conditions changed materially | No |
| OUTCOME_EVALUATED | Outcome compared against prediction | No |
| ARCHIVED | Permanently stored | No |

---

### 4.5 Lifecycle Timing Reference

| Stage | Typical Duration | Maximum Duration |
|---|---|---|
| Data Intake | 5-10 ms | 30 ms |
| Context Building | 10-20 ms | 50 ms |
| Forecast Generation | 50-200 ms | 500 ms |
| Probability Assignment | 20-50 ms | 100 ms |
| Scenario Generation | 100-300 ms | 1,000 ms |
| Confidence Assessment | 10-20 ms | 50 ms |
| Ensemble Aggregation | 20-50 ms | 100 ms |
| Validation | 10-30 ms | 100 ms |
| Comparison | 20-40 ms | 100 ms |
| Governance (TIER-1) | < 1 ms | 10 ms |
| Distribution | 5-20 ms | 50 ms |
| **Total (TIER-1, on-demand)** | **~250 ms** | **~2,000 ms** |
| Outcome Evaluation | Async, session end | Session end |
| Archive | Async, post-session | Next session start |

---

### 4.6 Point-in-Time (PIT) Semantics

Every prediction is generated from a context snapshot that is strictly point-in-time. The context snapshot records the exact state of all input signals at the timestamp of context assembly. Subsequent changes to input signals do not retroactively change the prediction — they trigger a new prediction generation cycle.

This PIT discipline ensures that:
1. Predictions are reproducible: given the same context snapshot, the same prediction is produced.
2. Post-hoc analysis is reliable: the "what did the system know?" question has a precise answer.
3. Outcome evaluation is fair: the prediction is evaluated against the context that was available when it was made, not retroactive knowledge.

---

## PART V — PREDICTION SERVICES

### 5.1 Overview

The Prediction Engine exposes 12 services to other IIOS layers. These services are the defined interfaces through which authorized consumers request and receive prediction intelligence. Services encapsulate the internal complexity of the Prediction Engine behind clean, type-safe interfaces.

**Service Identifier Format:** PS-{NN}

---

**PS-01 — Forecast Service**

*Interface:* Request → Structured Forecast Record

*Purpose:* Provides on-demand and scheduled quantitative forecasts for specified prediction types, targets, and horizons.

*Request parameters:*

| Parameter | Description |
|---|---|
| prediction_type | PT-01 through PT-18 |
| target_instrument | NSE symbol or index code |
| horizon | Time horizon: 5m, 15m, 30m, 60m, session |
| consumer_id | Authorized consumer identifier |
| urgency | NORMAL, HIGH (affects queue priority) |

*Response:* Complete Forecast Record with point estimate, confidence intervals, confidence score, uncertainty bounds, model attribution, and PQS.

*SLA:* Response within 500ms for NORMAL urgency; within 100ms for HIGH urgency (served from cache if valid forecast exists).

*Consumers:* Decision Engine (Layer 10), Capital Risk Engine (Layer 6), Execution Engine (Layer 11).

---

**PS-02 — Probability Service**

*Interface:* Request → Probability Assignment

*Purpose:* Provides calibrated probability estimates for specified events or threshold conditions.

*Request parameters:*

| Parameter | Description |
|---|---|
| event_description | Structured event specification |
| target_instrument | NSE symbol |
| horizon | Time horizon |
| conditional_on | Optional: condition the probability on a specified event |

*Response:* Probability value (0-1), confidence score, calibration history reference.

*SLA:* Response within 200ms.

*Consumers:* Decision Engine (debate scoring), RiskControl, StrategyLab.

---

**PS-03 — Scenario Service**

*Interface:* Request → Active Scenario Set

*Purpose:* Provides the current complete scenario set for specified target and horizon. The scenario set includes all active scenarios with their probabilities, narratives, and implications.

*Request parameters:*

| Parameter | Description |
|---|---|
| target | NIFTY, BANKNIFTY, PORTFOLIO, specific instrument |
| horizon | Session, overnight, multi-session |
| scenario_count | Requested number of scenarios (default: 4) |

*Response:* Complete Scenario Set: [BULL, BASE, BEAR, TAIL] scenarios with probabilities summing to 1.00, each with driver narrative, market level ranges, strategy implications, and activation conditions.

*SLA:* Response within 1,000ms on demand; 100ms from pre-computed cache at session start.

*Consumers:* Decision Engine (primary scenario consumer), RiskGuardian (tail scenario monitoring).

---

**PS-04 — Confidence Service**

*Interface:* Request → Confidence Assessment

*Purpose:* Returns the current confidence score for a specified prediction, or computes a new confidence assessment for a provided forecast.

*Request parameters:*

| Parameter | Description |
|---|---|
| prediction_id | ID of existing prediction (optional) |
| forecast_inputs | Raw forecast inputs (for fresh confidence computation) |
| type | Prediction type |

*Response:* Confidence score (0-1), confidence tier (HIGH/MEDIUM/LOW/MINIMUM), confidence components breakdown.

*SLA:* 50ms for existing prediction; 200ms for fresh computation.

*Consumers:* Decision Engine, Prediction Ranking Engine (PC-13), all prediction consumers.

---

**PS-05 — Validation Service**

*Interface:* Submit prediction for validation → Validation result

*Purpose:* Validates a generated prediction against the 5-stage validation pipeline. Returns validation status and PQS score.

*Response:* Validation status (VALIDATED / CONDITIONALLY_VALIDATED / FLAGGED / REJECTED), stage-by-stage results, PQS score, specific failure reasons.

*Consumers:* Internal use by Prediction Validator (PC-11); external consumers may request re-validation of existing predictions.

---

**PS-06 — Comparison Service**

*Interface:* Request → Comparison report

*Purpose:* Returns a comparison of the specified prediction against historical predictions for the same target, and/or a cross-type consistency check.

*Response:* Comparison report: prior prediction values, change magnitude, consistency assessment, DRIFT or INCONSISTENT flags if applicable.

*Consumers:* Decision Engine (for debate context), Prediction Governance Manager (PC-14).

---

**PS-07 — Distribution Service**

*Interface:* Internal service — routes approved predictions to registered consumers

*Purpose:* Manages the controlled distribution of predictions. Maintains consumer registration, routing rules, and distribution logs.

*Consumers:* All authorized prediction consumers (internal IIOS service — not directly invoked by external consumers).

---

**PS-08 — Monitoring Service**

*Interface:* Subscribe to prediction monitoring events

*Purpose:* Provides a subscription-based stream of prediction monitoring events: updates, invalidations, affirmations, scenario transitions.

*Consumers:* Decision Engine (real-time prediction monitoring), ControlTower (dashboard updates), RiskGuardian (tail event monitoring).

---

**PS-09 — Governance Service**

*Interface:* Submit governance item / retrieve governance queue / submit decision

*Purpose:* Manages the governance workflow: submission of governance items (by Prediction Validator and other components), queue management, decision recording.

*Consumers:* Internal Prediction Engine components, human operators via Telegram bot interface.

---

**PS-10 — Audit Service**

*Interface:* Query audit log for specified prediction ID or time range

*Purpose:* Provides tamper-evident audit records for any prediction or prediction lifecycle event.

*Response:* Audit trail for specified query: all events in sequence with timestamps, component attribution, and hash verification.

*Consumers:* Compliance processes, human operators, ValidationEngine (Layer 16).

---

**PS-11 — Archive Service**

*Interface:* Query historical predictions / retrieve outcome evaluation records

*Purpose:* Provides access to the permanent prediction archive for historical analysis, back-testing, and model evaluation.

*Consumers:* Learning Engine (Layer 13), ValidationEngine (Layer 16), PerformanceAnalytics (Layer 14), human operators.

---

**PS-12 — Health Service**

*Interface:* Request → PSHS and component health report

*Purpose:* Returns the current Prediction System Health Score and per-component health status.

*Response:* PSHS value, component health breakdown, active alert list, recent health trend.

*Consumers:* ControlTower (Layer 17 — dashboard), human operators.

---

## PART VI — PREDICTION PIPELINES

### 6.1 Overview

The Prediction Engine implements 10 defined pipelines. Each pipeline is a sequenced workflow that transforms inputs into specific prediction outputs or performs prediction lifecycle operations.

**Pipeline Identifier Format:** PP-{NN}

---

**PP-01 — Knowledge-to-Prediction Pipeline**

*Purpose:* Transforms structured knowledge from the Knowledge Engine into prediction priors and model calibration parameters.

*Trigger:* Session start; Knowledge Engine model update; calibration review trigger.

`
[Knowledge Engine]
  ├── Domain knowledge (market structure, instrument properties)
  ├── Entity relationships (sector membership, index composition)
  └── Validated model parameters
              │
              ▼
   [Prediction Builder PC-03]
   — Extract knowledge-based priors
   — Map entity relationships to prediction scope
   — Load knowledge-validated model constraints
              │
              ▼
   [Prediction Catalog PC-02]
   — Register knowledge-derived calibration profiles
   — Update domain prior distributions
              │
              ▼
   [Forecast Generator PC-04] [Probability Engine PC-06]
   — Apply knowledge priors to forecast generation
   — Condition probability computations on domain constraints
`

*Output:* Updated Prediction Catalog with knowledge-derived priors; generation components have access to domain constraints.

---

**PP-02 — Reasoning-to-Prediction Pipeline**

*Purpose:* Transforms reasoned conclusions from the Reasoning Engine into prediction inputs that reflect the IIOS system's current inferred understanding.

*Trigger:* New reasoning conclusion published by Reasoning Engine; per-cycle reasoning update.

`
[Reasoning Engine]
  ├── Inferred conclusions (e.g., "momentum is strengthening")
  ├── Causality chains (e.g., "RBI hawkishness → bank sector pressure")
  └── Conditional inferences (e.g., "IF VIX < 15 THEN low volatility regime likely")
              │
              ▼
   [Prediction Builder PC-03]
   — Parse reasoning conclusions into prediction-relevant signals
   — Map conditional inferences to conditional prediction inputs
   — Weight inferences by their confidence scores
              │
              ▼
   [Forecast Generator PC-04]
   — Apply reasoning-based signals as additional inputs
   — Update directional priors based on inferred conclusions
              │
              ▼
   [Scenario Generator PC-05]
   — Construct scenario narratives consistent with reasoning conclusions
   — Assign scenario probabilities informed by inference confidence
              │
              ▼
   [Prediction Registry PC-01]
   — New prediction records with reasoning attribution
`

*Output:* Updated predictions that reflect the Reasoning Engine's current inferred understanding.

---

**PP-03 — Learning Feedback Pipeline**

*Purpose:* Applies Learning Engine model improvements and calibration updates to Prediction Engine models and calibration profiles.

*Trigger:* Learning Engine deploys a knowledge update relevant to prediction models.

`
[Learning Engine (L13)]
  ├── Calibrated strategy weights → PT-10 (Strategy Prediction) models
  ├── DCS recalibration → confidence model updates
  └── Model improvement updates → registered prediction models
              │
              ▼
   [Prediction Version Manager PC-20]
   — Receive model version update
   — Create new version entry
   — Preserve prior version for rollback
              │
              ▼
   [Prediction Catalog PC-02]
   — Update calibration profiles with Learning Engine outputs
   — Update ensemble weights based on Learning feedback
              │
              ▼
   [Ensemble Manager PC-09]
   — Reload ensemble weights for affected prediction types
              │
              ▼
   [Prediction Audit Manager PC-15]
   — Log: model update applied; version number; source Learning Engine record
`

*Output:* Prediction Engine models are updated with Learning Engine improvements. All updates are versioned and auditable.

---

**PP-04 — Scenario Pipeline**

*Purpose:* The primary scenario generation pipeline, executed at session start and triggered by material regime changes during the session.

*Trigger:* Session start (09:00 IST); regime change signal; significant market event.

`
[Input collection]
  ├── Current regime (MarketIntelligence L2)
  ├── Overnight global context (GlobalIntelligence L1)
  ├── Active hypotheses (Hypothesis Engine)
  ├── Forecast Generator outputs (PC-04) — PT-01, PT-02, PT-03
  ├── Macro predictions (PT-06)
  └── MarketSimulation outputs (L8)
              │
              ▼
   [Scenario Generator PC-05]
   — Construct 4 scenarios: BULL, BASE, BEAR, TAIL_DOWN
   — Assign probabilities (sum = 1.00)
   — Specify NIFTY/BANKNIFTY ranges for each scenario
   — Specify strategy implications
   — Specify activation signals and termination conditions
              │
              ▼
   [Probability Engine PC-06]
   — Validate scenario probabilities
   — Apply Bayesian normalization
              │
              ▼
   [Prediction Validator PC-11]
   — Validate scenario set completeness
   — Verify probability normalization
              │
              ▼
   [Prediction Distribution Manager PC-19]
   — Distribute to Decision Engine (L10)
   — Distribute to RiskGuardian (L9) [tail scenarios]
   — Post to ControlTower dashboard (L17)
`

*Output:* Active scenario set, distributed to all consumers. Typically 4 scenarios at session start.

---

**PP-05 — Probability Pipeline**

*Purpose:* Real-time Bayesian probability update pipeline, triggered by each new observation signal.

*Trigger:* New observation from Observation Engine; new evidence signal from Evidence Engine.

`
[New Signal]
  ├── Price observation (Observation Engine)
  └── Evidence signal (Evidence Engine)
              │
              ▼
   [Probability Engine PC-06]
   — Retrieve prior probability distribution
   — Compute likelihood of signal given each hypothesis
   — Apply Bayes' theorem: posterior = likelihood × prior / normalizer
   — Compute updated posterior probability distribution
              │
              ▼
   [Confidence Engine PC-07]
   — Assess impact on confidence (does new signal increase or decrease confidence?)
              │
              ▼
   [Prediction Registry PC-01]
   — Update affected prediction records with new probability values
   — Set status to UPDATED
              │
              ▼
   [EventBus]
   — Publish probability update event (consumed by Decision Engine if significant)
`

*Output:* Real-time probability updates. Decision Engine receives significant updates (probability delta > 5% on active predictions).

---

**PP-06 — Validation Pipeline**

*Purpose:* The formal 5-stage validation pipeline applied to all newly generated predictions.

*Trigger:* Prediction reaches ENSEMBLE_COMPLETE status.

`
[ENSEMBLE_COMPLETE prediction]
              │
              ▼
   [Stage V-01: Structural Validity]
   — All mandatory fields present?
   — Type recognized? Target valid? Horizon valid?
   Pass: continue | Fail: → REJECTED
              │
              ▼
   [Stage V-02: Probability Integrity]
   — All probabilities in [0,1]?
   — Scenario probabilities sum to 1.00?
   Pass: continue | Fail: → REJECTED
              │
              ▼
   [Stage V-03: Evidence Grounding]
   — At least one current evidence item with confidence > 0.40?
   Pass: continue | Fail: FLAG(UNSUPPORTED) → continue
              │
              ▼
   [Stage V-04: Calibration Check]
   — Stated confidence within ±2σ of historical calibration range?
   Pass: continue | Fail: FLAG(CALIBRATION_MISMATCH) → continue
              │
              ▼
   [Stage V-05: Regime Applicability]
   — Model has ≥ 5 sessions history in current regime?
   Pass: VALIDATED | Fail: FLAG(REGIME_UNTESTED) → CONDITIONALLY_VALIDATED
              │
              ▼
   [PQS Computation]
   — Compute Prediction Quality Score (13 dimensions)
              │
              ▼
   [Prediction Registry PC-01] — update status
   [Prediction Governance Manager PC-14] — escalate if FLAGGED
`

*Output:* Validated prediction record with status, flags, and PQS score.

---

**PP-07 — Distribution Pipeline**

*Purpose:* Routes approved predictions to their registered consumers.

*Trigger:* Governance APPROVE or CONDITIONALLY_APPROVE decision.

`
[APPROVED prediction]
              │
              ▼
   [Prediction Distribution Manager PC-19]
   — Look up consumer registry for this prediction type
   — Apply distribution filters (regime-specific routing)
   — Package prediction for each consumer
              │
              ▼
   [Prediction Audit Manager PC-15]
   — Log distribution: prediction_id × consumer_id × timestamp
              │
              ▼
   [Consumer delivery]
   ├── Decision Engine (L10) — primary consumer
   ├── MetaLearning (L3) — strategy predictions
   ├── RiskControl (L7) — risk predictions
   ├── RiskGuardian (L9) — tail risk predictions
   ├── StrategyLab (L5) — strategy predictions
   └── ControlTower (L17) — PSHS and telemetry
`

*Output:* Predictions delivered to registered consumers; distribution logged.

---

**PP-08 — Monitoring Pipeline**

*Purpose:* Continuous monitoring of distributed predictions for accuracy trajectory and invalidation signals.

*Trigger:* Continuous, running throughout the trading session for all MONITORING status predictions.

`
[Active MONITORING predictions]
              │
              ▼
   [New observation/signal arrives]
              │
              ▼
   [Prediction Comparator PC-12]
   — Is current market state consistent with the prediction?
   — Has an invalidation signal been detected?
              │
              ├── Consistent: update confidence (upward)
              ├── Inconsistent but within bounds: no action
              └── Invalidation signal detected:
                          │
                          ▼
                   [Prediction Builder PC-03]
                   — Trigger new prediction generation cycle
                          │
                          ▼
                   [Old prediction → SUPERSEDED]
`

*Output:* Real-time monitoring events; updated confidence scores; prediction supersession on invalidation.

---

**PP-09 — Outcome Evaluation Pipeline**

*Purpose:* Evaluates every expired prediction against its actual outcome.

*Trigger:* Prediction horizon passes; session end (batch evaluation of all expired session predictions).

`
[Expired prediction (horizon passed)]
              │
              ▼
   [TradeMonitoring (L12) / Market Data]
   — Retrieve actual outcome for the predicted target at horizon
              │
              ▼
   [Prediction Analytics Manager PC-18]
   — Compute accuracy: was prediction directionally correct?
   — Compute calibration error: stated probability vs observed frequency
   — Compute Brier Score for probabilistic predictions
   — Compute CRPS for distribution predictions
              │
              ▼
   [Prediction Audit Manager PC-15]
   — Log outcome evaluation result
              │
              ▼
   [Prediction Registry PC-01]
   — Update prediction record: status → OUTCOME_EVALUATED
   — Write back accuracy metrics
              │
              ▼
   [Learning Engine (L13)]
   — Submit accuracy metrics as learning feedback (LT-05 equivalents)
   — Trigger model calibration updates if systematic errors detected
`

*Output:* Evaluated prediction records; learning feedback to Learning Engine; model calibration updates.

---

**PP-10 — Archive Pipeline**

*Purpose:* Moves outcome-evaluated predictions from the active Registry to the permanent Archive.

*Trigger:* Session end; Prediction Registry rolling window capacity reached.

`
[OUTCOME_EVALUATED predictions]
              │
              ▼
   [Prediction Archive Manager PC-16]
   — Verify outcome evaluation completeness
   — Compress and index prediction records
   — Write to persistent archive storage
   — Verify write integrity
              │
              ▼
   [Prediction Registry PC-01]
   — Remove archived records from active Registry
   — Confirm archive receipt
              │
              ▼
   [Prediction Audit Manager PC-15]
   — Log archive operation
`

*Output:* Archived prediction records; compact Registry; audit log updated.

---

## PART VII — PREDICTION QUALITY FRAMEWORK

### 7.1 Overview

The Prediction Quality Score (PQS) is the composite metric that measures the quality of every Prediction Engine output. It is a weighted sum of 13 quality dimensions (PQD-01 through PQD-13), each measuring a distinct aspect of prediction quality.

PQS is computed at generation time by the Prediction Validator (PC-11). It is updated after outcome evaluation. It is used by the Prediction Governance Manager (PC-14) to determine the governance tier and by prediction consumers to weight predictions.

**PQS Formula (plain text notation):**

PQS = (0.20 × PQD01) + (0.15 × PQD02) + (0.10 × PQD03) + (0.10 × PQD04) + (0.08 × PQD05) + (0.08 × PQD06) + (0.07 × PQD07) + (0.05 × PQD08) + (0.05 × PQD09) + (0.04 × PQD10) + (0.04 × PQD11) + (0.02 × PQD12) + (0.02 × PQD13)

Where each PQD dimension is scored in [0, 1]. Total weights = 1.00.

---

### 7.2 Quality Dimensions

**PQD-01 — Accuracy (weight: 0.20)**

*Definition:* The degree to which the prediction's central estimate is correct when evaluated against the actual outcome. Accuracy is measured post-outcome.

*At generation time:* Estimated from model calibration history (historical accuracy for this type/regime combination).

*Post-outcome:* Measured directly: was the directional prediction correct? Was the point estimate within the stated confidence interval?

*Measurement scale:* 0.0 (completely wrong) to 1.0 (completely correct). Directional predictions score 0 or 1; quantitative forecasts score based on normalized error.

*Monitoring target:* Rolling 20-session accuracy > 0.55 (better than random for directional) for all active prediction types.

---

**PQD-02 — Calibration (weight: 0.15)**

*Definition:* The degree to which the stated probability corresponds to the observed frequency. A well-calibrated prediction engine assigns probability 0.70 to events that occur 70% of the time.

*Measurement:* Calibration error = |stated_probability − observed_frequency| measured over a rolling sample of minimum 20 predictions per type/tier.

*Scoring:* PQD-02 = max(0, 1 − 2 × calibration_error). Calibration error of 0 → PQD-02 = 1.0; calibration error of 0.5 → PQD-02 = 0.0.

*Monitoring target:* PQD-02 > 0.75 (calibration error < 12.5%) for all active prediction types.

---

**PQD-03 — Confidence (weight: 0.10)**

*Definition:* The confidence score computed by the Confidence Engine (PC-07). Reflects the quality of the evidence base, model calibration history, and regime familiarity.

*Measurement:* Directly the confidence score from PC-07, normalized to [0,1].

*Monitoring target:* Average PQD-03 > 0.60 across all active predictions.

---

**PQD-04 — Reliability (weight: 0.10)**

*Definition:* The completeness and quality of the data inputs used to generate the prediction. High reliability means all required data sources were available, fresh, and within quality thresholds.

*Measurement:* Data quality score computed by Prediction Builder (PC-03): (available_sources / required_sources) × (fresh_sources / available_sources).

*Monitoring target:* PQD-04 > 0.85 (no more than 15% of required data sources missing or stale).

---

**PQD-05 — Stability (weight: 0.08)**

*Definition:* The degree to which repeated generation of predictions for the same target and context produces consistent results. High stability means the prediction is robust to minor variations in input data.

*Measurement:* Measured by intraday re-generation: if a prediction is generated twice within 5 minutes with essentially the same inputs, do the outputs agree within a tolerance band?

*Monitoring target:* PQD-05 > 0.80.

---

**PQD-06 — Generalization (weight: 0.08)**

*Definition:* The degree to which the prediction model performs well across different market conditions and not just the specific conditions on which it was trained.

*Measurement:* Model performance in out-of-sample regimes compared to in-sample regimes. A model that only works in TRENDING regimes and fails in RANGING regimes has low generalization.

*Monitoring target:* PQD-06 > 0.65 (acceptable cross-regime generalization).

---

**PQD-07 — Robustness (weight: 0.07)**

*Definition:* The degree to which the prediction is resilient to input perturbations: small changes in input data should not cause large changes in the prediction output.

*Measurement:* Sensitivity analysis: perturb input signals by ±5% and measure the resulting change in prediction probability. High robustness = small output change per input perturbation.

*Monitoring target:* PQD-07 > 0.70.

---

**PQD-08 — Explainability (weight: 0.05)**

*Definition:* The degree to which the prediction is accompanied by a clear, complete explanation of its driving evidence, model structure, and material assumptions.

*Measurement:* Completeness score of the explainability report: (fields_present / fields_required). Key fields: driving evidence list, top model features, material assumptions list, model version references.

*Monitoring target:* PQD-08 = 1.00 for AI predictions (explainability is mandatory). PQD-08 > 0.80 for all other predictions.

---

**PQD-09 — Traceability (weight: 0.05)**

*Definition:* The degree to which the prediction can be fully traced to its source data, models, and evidence chain. Full traceability means: given the prediction record, a complete provenance chain can be reconstructed.

*Measurement:* Binary score with partial credit: 1.0 if full provenance chain is present; 0.0 if source data cannot be traced.

*Monitoring target:* PQD-09 = 1.00 for all predictions.

---

**PQD-10 — Bias (weight: 0.04)**

*Definition:* The absence of systematic directional error in predictions. A biased prediction systematically over-predicts or under-predicts, producing predictions that are consistently too high or too low.

*Measurement:* Bias score = 1 − |mean_error|. A prediction that is on average 10% too high has a bias score of 0.90.

*Monitoring target:* PQD-10 > 0.90 (mean error < 10%).

---

**PQD-11 — Drift (weight: 0.04)**

*Definition:* The absence of model drift: the prediction model's accuracy should remain stable over time, not gradually degrade.

*Measurement:* Computed by Drift Detector equivalent in Prediction Engine. Comparison of accuracy in recent 10 sessions vs prior 10 sessions. Drift score = 1 − |recent_accuracy − prior_accuracy|.

*Monitoring target:* PQD-11 > 0.85 (accuracy change < 15%).

---

**PQD-12 — Forecast Skill (weight: 0.02)**

*Definition:* The degree to which the prediction adds value over a naive baseline (e.g., "tomorrow is like today"). Forecast skill is measured by Brier Skill Score (BSS) for binary probabilistic predictions, or CRPS Skill Score for distributional predictions.

*Measurement:* BSS = 1 − (Brier_Score / Brier_Score_baseline). BSS = 0 means no skill over baseline; BSS = 1 means perfect skill.

*Monitoring target:* PQD-12 > 0.10 (positive skill over baseline).

---

**PQD-13 — Uncertainty Quality (weight: 0.02)**

*Definition:* The quality of the uncertainty representation: are the stated uncertainty bounds actually correct? Do 68% confidence intervals actually contain the outcome 68% of the time?

*Measurement:* Coverage rate: (actual outcomes within stated interval) / (total predictions with stated interval). Target coverage = stated confidence level (e.g., 68% for 1-sigma).

*Monitoring target:* Coverage rate within ±5 percentage points of the stated confidence level.

---

### 7.3 PQS Tier Reference

| Tier | PQS Range | Governance Tier | Distribution |
|---|---|---|---|
| EXCELLENT | 0.88 – 1.00 | TIER-1-AUTO | Immediate distribution |
| GOOD | 0.72 – 0.87 | TIER-1-AUTO | Immediate distribution |
| ACCEPTABLE | 0.56 – 0.71 | TIER-2-ADVISORY | Distribute with notification |
| MARGINAL | 0.35 – 0.55 | TIER-3-HUMAN | Hold for human review |
| FAILED | 0.00 – 0.34 | Reject | Not distributed |

---

### 7.4 Quality Monitoring Thresholds

| Metric | Warning Threshold | Critical Threshold | Action |
|---|---|---|---|
| Average PQS (by type) | < 0.65 | < 0.50 | Escalate; review models |
| Calibration error | > 15% | > 25% | Suspend type; recalibrate |
| Accuracy (directional) | < 52% | < 48% | Review model; consider suspension |
| Bias score | < 0.85 | < 0.70 | Bias alert; detrend model |
| Drift score | < 0.80 | < 0.65 | Drift alert; recalibrate |
| Coverage rate deviation | > 8 ppts | > 15 ppts | Uncertainty recalibration |
| Explainability rate | < 95% | < 85% | Reject unexplained predictions |

---

## PART VIII — PREDICTION GOVERNANCE

### 8.1 Ownership

| Governance Domain | Owner | Authority Level |
|---|---|---|
| Prediction Engine architecture | IIOS Architecture Authority | Tier 4 — structural changes |
| Prediction model deployment | Prediction Governance Manager (PC-14) | Tier 3 — human approval |
| Prediction catalog updates | Prediction Catalog (PC-02) + Learning Engine | Tier 1/2 — auto with notification |
| Prediction distribution rules | Prediction Governance Manager (PC-14) | Tier 3 |
| Constitutional rules | IIOS Architecture Authority | Immutable |
| GDR amendments | IIOS Architecture Authority (extraordinary review) | Immutable in production |
| Human override of any prediction | Any authorised operator | Absolute and unconditional |

---

### 8.2 Naming Standards

| Object | Format | Example |
|---|---|---|
| Prediction record | PRD-{TYPE}-{YYYYMMDD}-{SEQ:08d} | PRD-PT01-20260703-00000042 |
| Forecast record | FCS-{HORIZON}-{YYYYMMDD}-{SEQ:06d} | FCS-SESSION-20260703-000007 |
| Scenario set | SCN-{TARGET}-{YYYYMMDD}-{SEQ:04d} | SCN-NIFTY-20260703-0001 |
| Individual scenario | SCN-{SET_ID}-{NAME} | SCN-NIFTY-20260703-0001-BULL |
| Probability record | PRB-{EVENT}-{YYYYMMDD}-{SEQ:06d} | PRB-NIFTY_CLOSE_UP-20260703-000005 |
| Model version | PVR-{MODEL}-{VERSION:04d} | PVR-NIFTY_PRICE_MODEL-0023 |
| Audit entry | PAUD-{PRD_ID}-{SEQ:04d} | PAUD-PRD-PT01-20260703-00000042-0001 |
| Prediction quality report | PQR-{YYYYMMDD}-{SEQ:04d} | PQR-20260703-0001 |

---

### 8.3 Versioning

All prediction models, calibration profiles, and ensemble configurations are versioned. Versioning rules:

- **Model version increment:** On every Learning Engine update that changes model parameters.
- **Calibration profile increment:** On every recalibration that changes the calibration factor.
- **Ensemble weight increment:** On every regime-specific weight update.
- **Prior version retention:** Minimum 10 prior versions retained for rollback.
- **Rollback protocol:** Rollback requests go to the Prediction Version Manager (PC-20) and require TIER-2-ADVISORY governance approval.

---

### 8.4 Governance Tier Matrix

| Condition | Tier | Approver | Timeout |
|---|---|---|---|
| PQS ≥ 0.72, no flags | TIER-1-AUTO | Automated | None |
| 0.56 ≤ PQS < 0.72, soft flags | TIER-2-ADVISORY | Automated + notify operator | 30 minutes |
| PQS < 0.56, or INCONSISTENT flag | TIER-3-HUMAN | Human operator | 2 min (intraday); 30 min (pre-session) |
| Structural architecture change | TIER-4-COMMITTEE | Multi-reviewer | No timeout |
| First deployment of new model type | TIER-3-HUMAN | Human operator | 24 hours |
| Model rollback | TIER-2-ADVISORY | Automated + notify operator | 30 minutes |

---

### 8.5 Compliance Requirements

| Requirement | Standard | Monitoring |
|---|---|---|
| All distributed predictions have PQS ≥ 0.35 | Hard minimum | Per prediction |
| All predictions carry uncertainty bounds | Constitutional rule | Per prediction |
| All AI predictions carry explainability reports | Constitutional rule | Per AI prediction |
| Prediction audit log hash chain intact | Constitutional rule | Continuous |
| No predictions distributed during Kill Switch | Constitutional rule | Continuous |
| Governance queue cleared within 24 hours | SLA | Daily |
| Outcome evaluation rate > 90% | Quality standard | Weekly |
| Calibration error < 15% per type | Quality standard | Rolling 20 sessions |

---

### 8.6 Security Requirements

- **Access control:** Only authorized IIOS components and human operators may request predictions or modify prediction records.
- **Audit immutability:** The prediction audit log is append-only. No prediction event may be deleted or modified after creation.
- **Version integrity:** Model version files are hash-verified before loading. Modified model files are rejected.
- **Distribution control:** Predictions are distributed only to registered consumers. No prediction data is exposed to unauthenticated external systems.
- **Human override logging:** All human overrides are logged with: operator ID, timestamp, prediction affected, reason (if provided).

---

### 8.7 Retention Policy

| Category | Minimum Retention | Storage Tier |
|---|---|---|
| Active prediction records | Session + 5 days | Hot storage |
| Outcome-evaluated predictions | 5 years | Warm storage |
| Archived predictions (all) | 10 years | Cold storage |
| Model versions | 3 years from retirement | Warm storage |
| Audit log | Permanent | Append-only |
| Governance decisions | 5 years | Warm storage |
| Quality reports | 3 years | Cold storage |

---

## PART IX — PREDICTION CONSTITUTION

### 9.1 Overview

The Prediction Constitution comprises 100+ immutable rules governing every aspect of the Prediction Engine's operation. These rules cannot be overridden by configuration, algorithm, or policy. They are the architectural laws of the Prediction Engine.

Rules are organized in 16 categories (PC-A through PC-P).

---

### PC-A — Prediction Integrity

**PC-A-001:** Every prediction generated by the Prediction Engine is advisory intelligence. No prediction constitutes a trade instruction, a risk limit override, or a governance decision.

**PC-A-002:** Every prediction carries an explicit probability measure. Predictions without probability assignments are not complete and must not be distributed.

**PC-A-003:** Every prediction carries explicit uncertainty bounds. A point estimate without uncertainty bounds is not a valid prediction output.

**PC-A-004:** The Prediction Engine never claims certainty. No prediction may be labelled with a probability of 1.00 unless the outcome is mechanically determined and provably certain.

**PC-A-005:** The Prediction Engine is never the sole basis for a trade decision. Predictions are inputs to the Decision Engine's debate process; they are never direct trade authorizations.

**PC-A-006:** All predictions are time-bounded. Every prediction carries a defined validity horizon, after which it is automatically placed in STALE status.

**PC-A-007:** Prediction records are immutable once created. Updates to probability values create new update events; they do not overwrite the original record.

**PC-A-008:** Every prediction is independently auditable. Given a prediction ID, the complete evidence chain, model versions, and context snapshot that produced it can be reconstructed.

---

### PC-B — Probability Integrity

**PC-B-001:** All probability values are in the closed interval [0, 1]. Values outside this range are rejected before distribution.

**PC-B-002:** For any complete set of mutually exclusive and exhaustive scenarios, the sum of scenario probabilities must equal 1.00 (within floating-point tolerance of ±0.001).

**PC-B-003:** No distributed prediction may assign probability exactly 0.00 or exactly 1.00 to any outcome that is not mechanically determined. Minimum distributable probability: 0.01. Maximum distributable probability: 0.99.

**PC-B-004:** Probability updates are bounded: no single update event may change any probability by more than 0.25 (25 percentage points). Larger changes require a new prediction generation cycle.

**PC-B-005:** Conditional probabilities must be consistent with their unconditional counterparts. P(A|B) × P(B) must equal P(A and B) within tolerance.

**PC-B-006:** Bayesian updating is the required method for real-time probability revision. Ad-hoc probability adjustments without a likelihood computation are prohibited.

---

### PC-C — Forecast Integrity

**PC-C-001:** All quantitative forecasts are expressed as ranges (minimum, central estimate, maximum) or full distributions. Point-only forecasts are prohibited for quantitative outcomes.

**PC-C-002:** Forecast horizons must be explicitly stated. A forecast without a defined horizon is not a valid forecast.

**PC-C-003:** Multi-horizon forecasts must be temporally consistent. The longer-horizon forecast distribution must encompass the shorter-horizon forecast distribution within its cone of uncertainty.

**PC-C-004:** Forecasts must be compared against their prior values. Every new forecast for a previously-forecast target includes a comparison to the prior forecast.

**PC-C-005:** Forecasts are never "final." A forecast for a target in the future is always revisable as new information arrives.

**PC-C-006:** Forecast evaluation is mandatory. Every forecast with an observable outcome must be evaluated within one session of the outcome occurring.

---

### PC-D — Scenario Integrity

**PC-D-001:** Scenarios must be mutually exclusive: the activation conditions of any two scenarios in a set must not overlap.

**PC-D-002:** Scenarios must be exhaustive: the set of scenarios must cover the full probability space. The sum of all scenario probabilities in a complete set must equal 1.00.

**PC-D-003:** Every scenario must specify its activation signal: the observable market condition that would indicate this scenario is playing out.

**PC-D-004:** Every scenario must specify its termination condition: the observable condition that would indicate this scenario is no longer active.

**PC-D-005:** Scenarios are updated in real-time as their activation signals are observed or refuted. A scenario whose activation probability drops below 2% is deactivated and replaced.

---

### PC-E — Confidence Integrity

**PC-E-001:** Confidence is a first-class field in every prediction record. It is never omitted or defaulted to 1.0 without computation.

**PC-E-002:** Confidence must be calibrated: historical confidence scores should correlate with prediction accuracy at the stated level. Systematic confidence overestimation is a constitutional violation.

**PC-E-003:** Low-confidence predictions (confidence < 0.35) are distributed with a prominent LOW_CONFIDENCE flag. They are never silently degraded.

**PC-E-004:** Confidence degrades over time without updates. A prediction that has not been refreshed within its staleness threshold automatically reduces its confidence score.

**PC-E-005:** The minimum distributable confidence is 0.25. Predictions with confidence below this threshold are held in PENDING_GOVERNANCE until human approval.

---

### PC-F — Calibration

**PC-F-001:** Prediction calibration is monitored continuously. A rolling calibration monitor runs for every active prediction type and regime combination.

**PC-F-002:** Calibration errors exceeding 25% trigger immediate model suspension for the affected type/regime combination. Suspended models may not generate predictions until recalibrated and re-approved.

**PC-F-003:** Calibration recalibration requires a minimum of 20 outcome evaluations. Recalibration on fewer samples is prohibited.

**PC-F-004:** Calibration corrections are applied incrementally. No single recalibration event may shift the calibration factor by more than 20 percentage points.

**PC-F-005:** All calibration updates are logged to the Prediction Audit Manager with full provenance.

---

### PC-G — Validation

**PC-G-001:** Every prediction is validated before distribution. No prediction bypasses the 5-stage validation pipeline.

**PC-G-002:** Hard validation failures (structural validity, probability integrity) result in immediate rejection. Rejected predictions are archived with failure reasons but never distributed.

**PC-G-003:** Soft validation failures result in FLAGGED or CONDITIONALLY_VALIDATED status. Flagged predictions are distributed but carry their flags as permanent attributes.

**PC-G-004:** The Prediction Validator is never disabled. In emergency degraded operation, validation is simplified but never eliminated.

**PC-G-005:** Validation statistics are maintained. The validation pass rate is a monitored metric. A persistent low pass rate triggers escalation to the Prediction Governance Manager.

**PC-G-006:** Re-validation of existing predictions is permitted only when material new information has arrived that justifies re-evaluation.

---

### PC-H — Governance

**PC-H-001:** No prediction is distributed without governance approval. The governance tier may be TIER-1-AUTO (automated, no human review) but governance is never skipped entirely.

**PC-H-002:** Governance decisions are immutable once made. A TIER-1-AUTO approval cannot be retroactively rescinded (it can be superseded by a new governance event).

**PC-H-003:** The governance queue must be cleared within 24 hours. Items older than 24 hours automatically escalate to the next tier.

**PC-H-004:** Prediction type retirement requires TIER-3-HUMAN approval. No prediction type may be retired by automated decision.

**PC-H-005:** New prediction types require TIER-4-COMMITTEE approval. The introduction of a new prediction type is an architectural change.

**PC-H-006:** All governance decisions are logged to the Prediction Audit Manager with the decision, rationale, and decision authority.

---

### PC-I — Auditability

**PC-I-001:** The Prediction Audit Manager is a prerequisite for prediction distribution. If the Audit Manager is unavailable, prediction distribution is suspended until it is restored.

**PC-I-002:** Every distribution event is logged: prediction ID, consumer, timestamp, prediction state at distribution.

**PC-I-003:** The audit log hash chain must be verified on every startup. Hash chain integrity failure is an emergency condition that suspends all Prediction Engine operations.

**PC-I-004:** Audit log entries are immutable. No audit entry may be modified, deleted, or retroactively altered.

**PC-I-005:** Any human operator action (override, suppression, approval, rejection) is logged to the audit trail with the operator identifier and timestamp.

---

### PC-J — Historical Preservation

**PC-J-001:** No prediction record is ever deleted. The terminal states for predictions are ARCHIVED and RETIRED (for models). DELETED is not a valid prediction lifecycle state.

**PC-J-002:** Outcome evaluation records are permanently preserved alongside their predictions. The historical accuracy of the Prediction Engine is a permanent institutional record.

**PC-J-003:** Every model version used to generate a prediction is permanently preserved. The exact model state that produced any historical prediction can be reconstructed.

**PC-J-004:** Archive integrity verification is performed weekly. Any archive corruption is treated as an emergency condition.

---

### PC-K — Bias Control

**PC-K-001:** Prediction bias is monitored continuously. A bias monitor runs for every active prediction type, measuring the mean directional error.

**PC-K-002:** When systematic bias exceeding 10% is detected, the biased model is flagged for recalibration. Flagged models continue to operate but their predictions carry a BIAS_SUSPECT flag.

**PC-K-003:** Confirmation bias is explicitly detected and countered. The Prediction Engine maintains evidence for and against all active predictions.

**PC-K-004:** Recency bias is controlled: the evidence window for predictions must include a minimum lookback period that extends beyond the most recent market move. An evidence window of fewer than 5 sessions is not permitted.

**PC-K-005:** Survivorship bias is prevented: outcome evaluation includes predictions that were superseded, not just predictions that remained active to their horizon.

---

### PC-L — Drift Control

**PC-L-001:** Model drift is monitored by the Drift Detector equivalent in the Prediction Engine. A rolling accuracy comparison between recent and historical sessions triggers drift alerts when accuracy divergence exceeds 15%.

**PC-L-002:** Regime drift is separately monitored: a model trained in RANGING regime conditions may drift when applied to a TRENDING regime. Regime applicability checks (Stage V-05) are the primary defense.

**PC-L-003:** Distribution drift is monitored for PT-18 (Probability Distribution Predictions): the shape of predicted distributions (skewness, kurtosis) is compared against historical norms.

**PC-L-004:** Drift alerts trigger mandatory model review. Drift review must be completed within 5 sessions of the alert.

---

### PC-M — Human Override

**PC-M-001:** A human operator may override any prediction at any time, without providing justification. The override is recorded but never contested.

**PC-M-002:** A human operator may suppress the distribution of any prediction. Suppressed predictions remain in the Registry but are not distributed to consumers.

**PC-M-003:** A human operator may force the invalidation of any active scenario. The operator-invalidated scenario is archived with the override reason.

**PC-M-004:** Human overrides are high-weight learning signals. Every human override is submitted to the Learning Engine as a Human Feedback learning event (equivalent to LT-19 in the Learning Engine architecture).

---

### PC-N — Security

**PC-N-001:** Prediction outputs are accessible only to authorized, registered consumers within the IIOS. No prediction data is exposed to unauthenticated external systems.

**PC-N-002:** Model parameters are stored encrypted at rest. Model files are hash-verified before loading. Tampered model files are rejected.

**PC-N-003:** The prediction distribution channel is authenticated. Any delivery failure is logged and retried with exponential backoff.

---

### PC-O — Quality Control

**PC-O-001:** The Prediction System Health Score (PSHS) is computed and reported every 60 seconds. PSHS values are never estimated or interpolated between computation cycles.

**PC-O-002:** Predictions with PQS < 0.35 are rejected before distribution. This threshold is a hard minimum and cannot be lowered by configuration.

**PC-O-003:** The average PQS across all distributed predictions is monitored as a rolling 5-session metric. Persistent average PQS below 0.60 triggers a system-wide quality review.

**PC-O-004:** Quality degradation in any single prediction type (average PQS for that type below 0.50 for 5 consecutive sessions) triggers suspension of that type pending review.

**PC-O-005:** Quality improvement is continuous. The Prediction Engine targets PQS improvement in every model update cycle.

---

### PC-P — Explainability

**PC-P-001:** All AI-model-generated predictions must carry a feature attribution report. AI predictions without explainability are not distributed.

**PC-P-002:** Feature attribution reports must identify the top 3 driving features with their contribution magnitudes. A report listing only one or two drivers is incomplete.

**PC-P-003:** Material assumptions must be declared in every prediction record. An assumption is material if removing it would change the prediction probability by more than 10 percentage points.

**PC-P-004:** Prediction explanations must be human-readable. Technical model internals (layer weights, gradient values) are not acceptable as explanations. The explanation must state the business reasoning: "The bullish prediction is driven by: (1) NIFTY above 20-day EMA, (2) BANKNIFTY sector leadership, (3) FII inflow signal from GlobalIntelligence."

**PC-P-005:** Explanations are stored permanently alongside prediction records. They are part of the immutable prediction record.

---

## PART X — PREDICTION READINESS CHECKLIST

### 10.1 Overview

The Prediction Readiness Checklist defines the conditions that must be satisfied before the Prediction Engine is considered ready to support live decision making. The checklist is divided into six sections covering pre-session initialization, model readiness, data readiness, governance readiness, and operational readiness.

---

### 10.2 Pre-Session Initialization Checklist (executed at session start, 08:45 IST)

**Section 1 — Component Readiness**

| Item | Check | Status Field | Required? |
|---|---|---|---|
| PRE-01 | Prediction Registry (PC-01) — ACTIVE, responsive | PSHS component | MANDATORY |
| PRE-02 | Prediction Catalog (PC-02) — loaded, all calibration profiles present | Component | MANDATORY |
| PRE-03 | Prediction Builder (PC-03) — context assembly operational | Component | MANDATORY |
| PRE-04 | Forecast Generator (PC-04) — at least one model loaded per type | Component | MANDATORY |
| PRE-05 | Scenario Generator (PC-05) — scenario templates loaded | Component | MANDATORY |
| PRE-06 | Probability Engine (PC-06) — prior distributions loaded | Component | MANDATORY |
| PRE-07 | Confidence Engine (PC-07) — calibration history loaded | Component | MANDATORY |
| PRE-08 | Uncertainty Engine (PC-08) — uncertainty floor parameters loaded | Component | MANDATORY |
| PRE-09 | Ensemble Manager (PC-09) — ensemble weights loaded for all active types | Component | MANDATORY |
| PRE-10 | Model Selector (PC-10) — model registry current | Component | MANDATORY |
| PRE-11 | Prediction Validator (PC-11) — validation rules current | Component | MANDATORY |
| PRE-12 | Prediction Comparator (PC-12) — prior session predictions available | Component | ADVISORY |
| PRE-13 | Prediction Ranking Engine (PC-13) — ranking profiles loaded | Component | ADVISORY |
| PRE-14 | Prediction Governance Manager (PC-14) — queue < 5 pending items | Component | MANDATORY |
| PRE-15 | Prediction Audit Manager (PC-15) — hash chain verified | Component | MANDATORY |
| PRE-16 | Prediction Archive Manager (PC-16) — accessible | Component | MANDATORY |
| PRE-17 | Prediction Health Manager (PC-17) — PSHS computation active | Component | MANDATORY |
| PRE-18 | Prediction Analytics Manager (PC-18) — session reports ready | Component | ADVISORY |
| PRE-19 | Prediction Distribution Manager (PC-19) — consumer registry current | Component | MANDATORY |
| PRE-20 | Prediction Version Manager (PC-20) — version integrity verified | Component | MANDATORY |

**Section 2 — Data Readiness**

| Item | Check | Required? |
|---|---|---|
| DAT-01 | Overnight global context (GlobalIntelligence L1) received and fresh | MANDATORY |
| DAT-02 | Current regime classification (MarketIntelligence L2) available | MANDATORY |
| DAT-03 | Active hypotheses (Hypothesis Engine) available | ADVISORY |
| DAT-04 | Current evidence set (Evidence Engine) available | MANDATORY |
| DAT-05 | Recent reasoning conclusions (Reasoning Engine) available | ADVISORY |
| DAT-06 | Learning Engine calibration updates from prior session applied | MANDATORY |
| DAT-07 | MarketSimulation scenario distributions (Layer 8) available | ADVISORY |
| DAT-08 | Prior session outcome evaluations completed | ADVISORY |
| DAT-09 | Model drift check completed for all active models | MANDATORY |
| DAT-10 | Portfolio state (RiskControl L7) available for portfolio predictions | MANDATORY |

**Section 3 — Model Readiness**

| Item | Check | Required? |
|---|---|---|
| MDL-01 | All model versions verified (hash check) | MANDATORY |
| MDL-02 | Calibration profiles current (< 5 sessions old) for all active types | MANDATORY |
| MDL-03 | No suspended models without approved replacement | MANDATORY |
| MDL-04 | Ensemble weights current for active regime | MANDATORY |
| MDL-05 | Fallback models available for all mandatory types (PT-01, PT-02, PT-03, PT-16) | MANDATORY |
| MDL-06 | AI model explainability wrappers loaded and tested | MANDATORY |
| MDL-07 | No models in drift alert without review | ADVISORY |

**Section 4 — Governance Readiness**

| Item | Check | Required? |
|---|---|---|
| GOV-01 | Governance queue < 5 pending items | MANDATORY |
| GOV-02 | No governance items older than 24 hours | MANDATORY |
| GOV-03 | Human operator confirmed (Telegram channel active) | MANDATORY |
| GOV-04 | Constitutional rules version current | MANDATORY |
| GOV-05 | Prediction distribution consumer registry current | MANDATORY |

**Section 5 — Prediction Generation Test**

Before commencing live prediction generation, a session-start prediction test is executed:

| Item | Check | Required? |
|---|---|---|
| GEN-01 | Generate PT-16 (Scenario Prediction) for NIFTY — session | MANDATORY |
| GEN-02 | Scenario probabilities sum to 1.00 | MANDATORY |
| GEN-03 | Scenario set passes 5-stage validation | MANDATORY |
| GEN-04 | Generate PT-01 (Price Prediction) for NIFTY — 60min | MANDATORY |
| GEN-05 | Price prediction has uncertainty bounds present | MANDATORY |
| GEN-06 | PQS ≥ 0.55 for all session-start predictions | MANDATORY |
| GEN-07 | Predictions distributed to Decision Engine (test acknowledgment) | MANDATORY |

**Section 6 — Post-Session Checklist (executed at session end, 15:35 IST)**

| Item | Check |
|---|---|
| PST-01 | Outcome evaluation pipeline executed for all expired session predictions |
| PST-02 | Learning feedback submitted to Learning Engine |
| PST-03 | Session PQS report generated and archived |
| PST-04 | Model drift check completed |
| PST-05 | Governance queue reviewed |
| PST-06 | Archive pipeline executed |
| PST-07 | PSHS trend report generated |
| PST-08 | Calibration check run for all types with > 5 new evaluations |
| PST-09 | Audit log integrity verified |
| PST-10 | Prior session prediction comparison statistics generated |

---

### 10.3 Prediction Readiness Matrix

| Scenario | Required Predictions Ready | Minimum PQS | Minimum PSHS |
|---|---|---|---|
| Full prediction support | PT-01 through PT-18 | 0.72 (GOOD) | 0.80 (NOMINAL) |
| Standard prediction support | PT-01, PT-02, PT-03, PT-05, PT-16, PT-17 | 0.60 (ACCEPTABLE) | 0.65 (DEGRADED) |
| Minimal prediction support | PT-16 (Scenario), PT-17 (Tail Risk) | 0.55 | 0.50 (PARTIAL) |
| Emergency prediction support | PT-16 (default template only) | None (defaults) | Any |
| No prediction support | None | N/A | < 0.35 |

**Decision Engine behavior at each level:**

| Level | Decision Engine impact |
|---|---|
| Full | Full prediction intelligence available; standard debate weights |
| Standard | Core predictions available; non-core types absent; operator notified |
| Minimal | Only scenario and tail risk predictions; Decision Engine applies conservative defaults |
| Emergency | Default scenarios only; Decision Engine operates in high-uncertainty mode |
| None | Prediction Engine offline; Decision Engine operates without prediction support |

---

### 10.4 Readiness State Machine

`
               PREDICTION ENGINE READINESS STATE MACHINE
               ═══════════════════════════════════════════

  STARTUP
      │
      ▼
  INITIALIZING ──→ Component load and health check
      │
      ├──(PSHS < 0.35)──────────→ EMERGENCY_MODE
      │                                │
      ├──(PSHS 0.35-0.54)──────→ MINIMAL_READY      ──→ Operator alert
      │                                │
      ├──(PSHS 0.55-0.79)──────→ DEGRADED_READY     ──→ Operator notification
      │                                │
      └──(PSHS ≥ 0.80)─────────→ FULLY_READY        ──→ Normal operation
                                       │
                                  (intraday events)
                                       │
                       ┌──────────────┴──────────────────┐
                       │                                   │
              COMPONENT_FAILURE                   KILL_SWITCH_ACTIVE
                       │                                   │
               ┌───────┴────────┐                  FROZEN_OPERATION
               │                │                  (collection only)
           (recoverable)  (non-recoverable)
               │                │
           DEGRADED         EMERGENCY
`

---

## SUPPLEMENT A — PREDICTION TAXONOMY REFERENCE

### A.1 Classification Matrix

| Code | Type | Temporal Scope | Signal Frequency | Update Frequency | Impact Tier |
|---|---|---|---|---|---|
| PT-01 | Price | Intraday (5 min – Session) | Continuous | Continuous | CRITICAL |
| PT-02 | Trend | Intraday – Session | Per new signal | Per new signal | HIGH |
| PT-03 | Volatility | 30 min – Session | Every 5 min | Every 15 min | CRITICAL |
| PT-04 | Liquidity | Intraday | Continuous | Continuous | HIGH |
| PT-05 | Risk | Session – 5 sessions | Every 30 min | Every 30 min | CRITICAL |
| PT-06 | Macro | Daily – Weekly | Daily | Daily | MEDIUM |
| PT-07 | Sector | Session – Daily | Session start | Session start | MEDIUM |
| PT-08 | Company | Event-driven | On event | On event | MEDIUM |
| PT-09 | Portfolio | Session – 5 sessions | Per trade | Per trade | HIGH |
| PT-10 | Strategy | Session – 20 sessions | Session end | Session end | HIGH |
| PT-11 | Execution | Pre-order | Per order | Per order | HIGH |
| PT-12 | Behavior | Session | Session start | Session start | MEDIUM |
| PT-13 | Cross-Market | Daily | Daily | Daily | MEDIUM |
| PT-14 | Cross-Asset | Daily – Weekly | Daily | Daily | LOW |
| PT-15 | Event | Event-specific | On calendar update | On calendar update | HIGH |
| PT-16 | Scenario | Session | Session start + triggers | Session start + triggers | CRITICAL |
| PT-17 | Tail Risk | Session | Every 30 min | Every 30 min | CRITICAL |
| PT-18 | Distribution | Session | Session start | Session start + hourly | CRITICAL |

---

### A.2 IIOS Layer Mapping

| Prediction Type | Primary Input Layers | Primary Output Consumers | Feedback Source |
|---|---|---|---|
| PT-01 Price | L1, L2, Observation | L10 Decision, L11 Execution | L12 TradeMonitoring |
| PT-02 Trend | L2, Observation, Evidence | L3 MetaLearning, L10 Decision | L12 TradeMonitoring |
| PT-03 Volatility | L1, L2, Observation | L6 CapitalRisk, L7 RiskControl | L12, L14 Analytics |
| PT-04 Liquidity | L2, Observation | L11 Execution, L6 CapitalRisk | L12 TradeMonitoring |
| PT-05 Risk | L7, L8, Portfolio | L7 RiskControl, L9 RiskGuardian | L12, L14 Analytics |
| PT-06 Macro | L1 GlobalIntelligence | L2 MarketIntelligence, L10 Decision | L14 Analytics |
| PT-07 Sector | L2 MarketIntelligence | L4 OpportunityEngine, L10 Decision | L14 Analytics |
| PT-08 Company | Knowledge Engine | L4 OpportunityEngine | Earnings outcomes |
| PT-09 Portfolio | L6, L7, Portfolio state | L6 CapitalRisk, L7 RiskControl | L14 Analytics |
| PT-10 Strategy | L13 Learning, L3 MetaLearning | L3 MetaLearning, L5 StrategyLab | L13 Learning |
| PT-11 Execution | L13 Learning, execution history | L11 Execution | L12 TradeMonitoring |
| PT-12 Behavior | L13 Learning, behavior history | L10 Decision | L13 Learning |
| PT-13 Cross-Market | L1 GlobalIntelligence | L2 MarketIntelligence, L10 Decision | L14 Analytics |
| PT-14 Cross-Asset | L1, L2 | L10 Decision | L14 Analytics |
| PT-15 Event | L2, Knowledge Engine | L10 Decision, L5 StrategyLab | Event outcomes |
| PT-16 Scenario | All types combined | L10 Decision, L9 RiskGuardian | All outcomes |
| PT-17 Tail Risk | L8 MarketSimulation, L7 | L9 RiskGuardian, L7 RiskControl | Extreme events |
| PT-18 Distribution | L8 MarketSimulation, models | L6 CapitalRisk, L10 Decision | L14 Analytics |

---

## SUPPLEMENT B — FORECAST EXAMPLES AND REFERENCE CASES

### B.1 Forecast Record Structure

A complete forecast record contains:

| Field | Type | Description |
|---|---|---|
| forecast_id | ID | FCS-{HORIZON}-{YYYYMMDD}-{SEQ:06d} |
| prediction_id | Reference | Parent prediction record ID |
| prediction_type | Enum | PT-01 through PT-18 |
| target | Symbol | NSE symbol or index code |
| horizon | Duration | 5m, 15m, 30m, 60m, 4h, session, daily |
| generated_at | Timestamp | PIT timestamp |
| regime_at_generation | Enum | TRENDING_BULL, RANGING, etc. |
| point_estimate | Float | Central forecast value |
| lower_bound_1sigma | Float | Lower bound of 68% confidence interval |
| upper_bound_1sigma | Float | Upper bound of 68% confidence interval |
| lower_bound_2sigma | Float | Lower bound of 95% confidence interval |
| upper_bound_2sigma | Float | Upper bound of 95% confidence interval |
| probability_direction | Float | Probability of upward move (0-1) |
| confidence_score | Float | Confidence Engine output (0-1) |
| pqs_score | Float | Prediction Quality Score (0-1) |
| driving_evidence | List | Evidence IDs that drove this forecast |
| model_versions | List | PVR model version IDs used |
| ensemble_weights | Dict | Model name → weight used in ensemble |
| explainability_report | Text | Human-readable explanation of drivers |
| material_assumptions | List | Declared material assumptions |
| status | Enum | VALIDATED, DISTRIBUTED, MONITORING, etc. |
| outcome_value | Float | Actual value at horizon (null until evaluated) |
| accuracy_score | Float | Post-outcome accuracy score (null until evaluated) |
| calibration_error | Float | Post-outcome calibration error (null until evaluated) |

---

### B.2 Reference Forecast Case: NIFTY Session Price Forecast

**Scenario:** 09:05 IST, July 3, 2026. Generating session-end price forecast for NIFTY.

**Context:**
- Overnight: US markets closed +0.8% (GlobalIntelligence)
- Current NIFTY spot: 22,640
- Regime: TRENDING_BULL (MarketIntelligence)
- India VIX: 13.4 (low volatility)
- Active hypothesis: "NIFTY uptrend to continue" (confidence 0.71)
- Recent evidence: price above all major moving averages, FII net buyer signal

**Generated Forecast:**

| Field | Value |
|---|---|
| forecast_id | FCS-SESSION-20260703-000001 |
| target | ^NSEI (NIFTY) |
| horizon | Session (close, 15:30 IST) |
| generated_at | 2026-07-03T09:05:12.342Z |
| regime | TRENDING_BULL |
| point_estimate | 22,780 |
| lower_bound_1sigma | 22,640 |
| upper_bound_1sigma | 22,920 |
| lower_bound_2sigma | 22,510 |
| upper_bound_2sigma | 23,050 |
| probability_direction | 0.67 (67% probability of upward close) |
| confidence_score | 0.74 |
| pqs_score | 0.79 (GOOD) |
| model_versions | [PVR-NIFTY_PRICE_MODEL-0023, PVR-ENSEMBLE_TREND-0011] |
| explainability | "Bullish forecast driven by: (1) Overnight US +0.8% global tailwind, (2) TRENDING_BULL regime with NIFTY above 20/50 EMA, (3) Active hypothesis H-007 (trend continuation, confidence 0.71), (4) Low VIX (13.4) supports continued directional move" |
| material_assumptions | ["No adverse macro event before close", "FII flows remain positive", "Regime does not transition to RANGING before 13:00 IST"] |

**Governance decision:** TIER-1-AUTO (PQS 0.79; no flags)

**Distribution:** Decision Engine (L10), Capital Risk Engine (L6), ControlTower dashboard

---

### B.3 Reference Forecast Case: Volatility Prediction

**Scenario:** 10:30 IST. Generating 60-minute realized volatility prediction for NIFTY.

**Context:**
- India VIX: 13.4
- Intraday NIFTY range so far: 22,610 - 22,655 (45 points, 0.20%)
- No major events scheduled in next 90 minutes
- Implied vs realized spread: IV slightly elevated (IVol 13.8% vs HVol 12.1%)

**Generated Forecast:**

| Field | Value |
|---|---|
| forecast_id | FCS-60MIN-20260703-000004 |
| target | NIFTY realized volatility |
| horizon | 60 minutes |
| point_estimate | 11.5% annualized |
| lower_bound_1sigma | 9.8% |
| upper_bound_1sigma | 13.2% |
| probability_volatility_expansion | 0.28 (28%) |
| probability_volatility_compression | 0.45 (45%) |
| confidence_score | 0.81 |
| pqs_score | 0.84 (GOOD) |
| explainability | "Low volatility forecast driven by: (1) No scheduled events in horizon, (2) Intraday range already tight (0.20%), (3) VIX 13.4 — below 1-year mean, (4) 28% probability of expansion primarily driven by IV premium (IVol/HVol spread 1.14x suggests some residual uncertainty)" |

---

### B.4 Reference Forecast Case: Strategy Prediction

**Scenario:** Session end (15:35 IST), July 3. Generating next-session prediction for STR-MOMENTUM_BREAKOUT_004.

**Context:**
- Session performance: 2 trades, 2 wins (WIN_RATE_TODAY = 100% — too few samples)
- Rolling 30-session win rate: 58%
- Rolling 30-session Sharpe: 0.84
- Current regime: TRENDING_BULL
- Regime history: 22 of last 30 sessions were TRENDING_BULL; win rate in TRENDING_BULL: 65%

**Generated Prediction (PT-10):**

| Field | Value |
|---|---|
| prediction_id | PRD-PT10-20260703-00000015 |
| target | STR-MOMENTUM_BREAKOUT_004 |
| horizon | Next session |
| probability_profitable_session | 0.63 |
| expected_sharpe_contribution | 0.09 (session contribution estimate) |
| regime_applicability | HIGH (specialized for TRENDING regimes) |
| confidence_score | 0.77 |
| pqs_score | 0.75 (GOOD) |
| explainability | "Strategy prediction driven by: (1) 65% historical win rate in TRENDING_BULL regime, (2) Current TRENDING_BULL regime expected to persist (Trend Prediction PT-02 confidence 0.74), (3) Strategy Sharpe 0.84 is above minimum threshold, (4) No evidence of strategy degradation in recent sessions" |

---

## SUPPLEMENT C — SCENARIO CATALOGUE

### C.1 Standard Scenario Types

The Prediction Engine maintains a library of standard scenario templates. Sessions are initialized from these templates, which are then customized with current market levels and probabilities.

**BULL Scenario Template:**

| Field | Template Value |
|---|---|
| name | BULL |
| description | Sustained upward momentum; NIFTY closes above prior session high |
| typical_probability_range | 0.25 – 0.45 |
| activation_signal | NIFTY above intraday VWAP + trend momentum positive |
| termination_signal | NIFTY below intraday VWAP for 30+ minutes |
| NIFTY_range_vs_open | +0.6% to +1.8% |
| strategy_implications | LONG bias; momentum strategies preferred; mean reversion strategies reduced |
| risk_state | LOW-MEDIUM |
| typical_VIX_range | 10 – 16 |

**BASE Scenario Template:**

| Field | Template Value |
|---|---|
| name | BASE |
| description | Sideways to mildly directional; close within ±0.3% of open |
| typical_probability_range | 0.25 – 0.40 |
| activation_signal | NIFTY oscillating around VWAP without sustained directional move |
| termination_signal | Sustained breakout above or below VWAP by 0.3%+ |
| NIFTY_range_vs_open | -0.3% to +0.3% |
| strategy_implications | Mixed; mean reversion strategies preferred; momentum strategies reduced |
| risk_state | LOW |
| typical_VIX_range | 10 – 18 |

**BEAR Scenario Template:**

| Field | Template Value |
|---|---|
| name | BEAR |
| description | Sustained downward momentum; NIFTY closes below prior session low |
| typical_probability_range | 0.15 – 0.35 |
| activation_signal | NIFTY below intraday VWAP + downward momentum signal |
| termination_signal | NIFTY above intraday VWAP for 30+ minutes |
| NIFTY_range_vs_open | -1.8% to -0.6% |
| strategy_implications | SHORT bias or cash; stop losses tighter |
| risk_state | MEDIUM-HIGH |
| typical_VIX_range | 15 – 25 |

**TAIL_DOWN Scenario Template:**

| Field | Template Value |
|---|---|
| name | TAIL_DOWN |
| description | Adverse extreme event; NIFTY gap or crash; Kill Switch proximity |
| typical_probability_range | 0.02 – 0.12 |
| activation_signal | NIFTY down > 1.5% from open; or VIX spike > 5 points intraday |
| termination_signal | NIFTY recovery above -1.5% from open; VIX stabilizes |
| NIFTY_range_vs_open | -2% to -5%+ |
| strategy_implications | All positions review; Kill Switch proximity alert |
| risk_state | HIGH — CRITICAL |
| typical_VIX_range | 25 – 45+ |

---

### C.2 Scenario Record Structure

A complete scenario record contains:

| Field | Description |
|---|---|
| scenario_id | SCN-{SET_ID}-{NAME} |
| scenario_set_id | Parent scenario set ID |
| name | BULL / BASE / BEAR / TAIL_DOWN / custom |
| description | Human-readable narrative |
| probability | Float [0.01, 0.99] |
| driving_factors | List of contributing factors with weights |
| NIFTY_lower | Lower NIFTY level for this scenario |
| NIFTY_upper | Upper NIFTY level for this scenario |
| BANKNIFTY_lower | Lower BANKNIFTY level |
| BANKNIFTY_upper | Upper BANKNIFTY level |
| strategy_implications | Dict: strategy → recommended adjustment |
| risk_implication | Risk tier for this scenario |
| activation_signal | Observable condition that activates this scenario |
| termination_signal | Observable condition that terminates this scenario |
| created_at | Timestamp |
| last_updated_at | Timestamp |
| status | ACTIVE / DEACTIVATED / TERMINATED |

---

## SUPPLEMENT D — PROBABILITY REFERENCE AND CALIBRATION GUIDE

### D.1 Probability Calibration Fundamentals

A well-calibrated prediction system is one where the stated probability corresponds to the observed frequency. Calibration is the most fundamental quality criterion for a probabilistic prediction engine.

**Definition of calibration:**

If the Prediction Engine assigns probability 0.70 to 100 events, calibration requires that approximately 70 of those events actually occur. If only 54 occur, the predictions are systematically overconfident. If 83 occur, they are systematically underconfident.

**Calibration error measurement:**

For a batch of N predictions with stated probability p(i) and binary outcome o(i) (1 = event occurred, 0 = did not occur):

Mean Calibration Error (MCE) = |mean(p(i)) - mean(o(i))| across the batch

A MCE of 0.00 is perfect calibration. An MCE of 0.10 means predictions are on average 10 percentage points off from reality.

**Expected Calibration Error (ECE):**

ECE is computed by grouping predictions into bins by stated probability (e.g., [0-0.1), [0.1-0.2), ... [0.9-1.0)) and measuring the calibration error within each bin. ECE = weighted average of bin calibration errors.

**Brier Score:**

The Brier Score is a proper scoring rule for probabilistic predictions. For a single prediction with stated probability p and outcome o (0 or 1):

Brier Score = (p - o)^2

Lower Brier Score = better prediction. A Brier Score of 0 is perfect. A naive predictor that always predicts 0.5 has a Brier Score of 0.25.

**Brier Skill Score (BSS):**

BSS = 1 - (Brier_Score / Brier_Score_reference)

Where the reference is the climatological baseline (historical frequency). BSS > 0 means the Prediction Engine adds skill over baseline. BSS = 1 is perfect skill. BSS < 0 means the engine is worse than baseline.

---

### D.2 Calibration Reference Values

| Calibration Error | Interpretation | Action |
|---|---|---|
| < 5% | Excellent calibration | None |
| 5% – 10% | Good calibration | Monitor |
| 10% – 15% | Acceptable calibration | Review scheduled |
| 15% – 20% | Warning | Flag; schedule recalibration |
| > 20% | Poor calibration | Recalibrate immediately |
| > 25% | Constitutional threshold | Suspend type; mandatory recalibration |

---

### D.3 Calibration by Prediction Type

Different prediction types require different calibration approaches:

**PT-01 Price Prediction calibration:**
Calibration for price predictions is measured by whether actual prices fall within the stated confidence intervals. The 68% confidence interval should contain the actual price 68% of the time. Calibration is computed separately for each horizon.

**PT-02 Trend Prediction calibration:**
Directional accuracy is the primary calibration metric. Rolling 20-session directional accuracy target: > 55%. Trend predictions assigned probability > 0.70 should be directionally correct > 70% of the time.

**PT-05 Risk Prediction calibration:**
Risk predictions require conservative calibration: it is better to over-predict risk (too conservative, accepts fewer trades) than to under-predict risk (too aggressive, misses tail events). Risk calibration factor applies an asymmetric adjustment: tail probabilities are multiplied by 1.25 relative to the raw model output.

**PT-16 Scenario Prediction calibration:**
Scenario calibration is measured by whether the highest-probability scenario is the one that actually plays out. Target: highest-probability scenario realized in > 40% of sessions (it should not be always the most probable, as market surprise is normal).

**PT-17 Tail Risk calibration:**
Tail risk predictions must not be underestimated. The minimum tail probability for any session is 2% regardless of model output. Tail probability calibration target: actual tail events should occur at a frequency within 2× of the predicted tail probability.

---

### D.4 Bayesian Updating Reference

The Probability Engine uses Bayesian updating to revise probabilities as new evidence arrives.

**Bayes' theorem (plain notation):**

P(H | E) = P(E | H) × P(H) / P(E)

Where:
- P(H) is the prior probability of hypothesis H
- P(E | H) is the likelihood of evidence E given H is true
- P(E) is the marginal probability of evidence E
- P(H | E) is the posterior probability of H given E

**Example application:**

Prior: P(NIFTY_UP_TODAY) = 0.60 (baseline probability from PT-02 trend prediction)

New evidence: Strong FII buying observed in first 30 minutes.

Likelihood P(FII_BUY | NIFTY_UP) = 0.75 (historically, FII buying correlates with up days)
Likelihood P(FII_BUY | NIFTY_DOWN) = 0.30

P(NIFTY_UP | FII_BUY) = (0.75 × 0.60) / [(0.75 × 0.60) + (0.30 × 0.40)]
                       = 0.45 / (0.45 + 0.12)
                       = 0.45 / 0.57
                       = 0.789

The FII buying signal updated the NIFTY UP probability from 0.60 to 0.79.

---

## SUPPLEMENT E — BIAS AND DRIFT EXAMPLES

### E.1 Prediction Bias Examples

**Example B-01: Recency Bias in Trend Prediction**

*Observation:* After a strong 5-session bull run, the Trend Prediction model consistently assigns > 0.75 probability to continuation, even when overbought signals are present.

*Root cause:* The model's evidence window is 5 sessions. After 5 consecutive up sessions, all evidence is bullish. The model has no memory of the prior mean-reversion regime.

*Detection:* Bias detector compares model prediction (mean probability assigned to UP in last 20 sessions: 0.72) against actual outcome frequency (UP in last 20 sessions: 54%). Miscalibration gap: 18 percentage points. Alert triggered.

*IIOS safeguard:* Minimum lookback rule (PC-K-004): evidence window must include minimum 10 sessions. Recency bias flag added to active trend predictions. Confidence score reduced.

---

**Example B-02: Overconfidence in Low-Volatility Regime**

*Observation:* When VIX is below 13, the Price Prediction model produces very tight confidence intervals (1-sigma range < 0.5% of price). However, actual price ranges in these sessions are frequently 0.8-1.2%.

*Root cause:* Model was calibrated on long-run volatility data. Current low-VIX period is unusual. Model is not adjusting for regime-appropriate uncertainty.

*Detection:* Uncertainty Quality (PQD-13) score drops below 0.70. Coverage rate for 1-sigma intervals drops to 55% (should be 68%).

*IIOS safeguard:* Uncertainty floor (PC-08) activated. Minimum 1-sigma range enforced at 0.6% of price in any regime. Uncertainty recalibration triggered.

---

**Example B-03: Confirmation Bias in Scenario Probability**

*Observation:* On a day when the prior day's trading created strong BULL sentiment, the Scenario Generator consistently assigns BULL probability > 0.60 even when contradictory signals (gap down open, weak breadth) are present.

*Root cause:* The scenario generation is weighting the prior session narrative too heavily relative to current-session signals.

*Detection:* Prediction Comparator detects scenario probability is not updating normally in response to new signals (signal responsiveness score below threshold).

*IIOS safeguard:* Context freshness rule: prior session signals receive < 20% of the total context weight for intraday scenario generation. Current session signals receive ≥ 80%.

---

### E.2 Prediction Drift Examples

**Example D-01: Trend Model Regime Drift**

*Observation:* The PT-02 Trend Prediction model, trained primarily on TRENDING regimes, is now being applied in a period of extended RANGING conditions. Its directional accuracy drops from 62% to 47% over 15 sessions.

*Detection:* Drift detector (rolling accuracy comparison: last 10 sessions 47% vs prior 10 sessions 62%). Drift score: 0.85 → 0.56. Alert triggered.

*IIOS safeguard:* Regime applicability check (Stage V-05) was already flagging this model as REGIME_UNTESTED for RANGING. But it was still in the ensemble. Alert triggers model weight reduction for RANGING regime in the Ensemble Manager.

---

**Example D-02: Calibration Drift in Risk Prediction**

*Observation:* The PT-05 Risk Prediction model was calibrated during a low-volatility period (2025). Now in mid-2026 with higher baseline volatility, tail probabilities are being systematically underestimated.

*Detection:* Outcome evaluation shows tail events occurring at 1.8× the predicted rate. Risk calibration error exceeds 25% (constitutional threshold).

*IIOS safeguard:* Risk type (PT-05) suspended per PC-F-002. Emergency recalibration initiated with current-period data. New model version deployed after recalibration.

---

## SUPPLEMENT F — ANTI-PATTERNS

### F.1 Overview

Anti-patterns are known failure modes in prediction system design. The Prediction Engine documents them explicitly and provides specific safeguards against each.

---

**AP-01 — The Oracle**

*Description:* A prediction system that claims deterministic, certain forecasts. "NIFTY WILL close at 22,450 today." No uncertainty, no probability, no acknowledgment that the future is unknown.

*Harm:* Overconfident decision-making; failure to size positions for actual risk; catastrophic surprise when certainty proves wrong.

*IIOS safeguard:* Constitutional rule PC-A-002 mandates probability measures. Constitutional rule PC-B-003 prohibits probability 1.00. Deterministic predictions rejected at validation Stage V-02.

---

**AP-02 — The Broken Clock**

*Description:* A prediction system that always predicts the same outcome (always bullish, always bearish). A broken clock is right twice a day.

*Harm:* Appears calibrated if the predicted direction happens to be the dominant outcome during the calibration period. Fails completely when regime changes.

*IIOS safeguard:* Bias monitor (PC-K-001) detects systematic directional bias. A model with probability > 0.70 assigned to the same direction in > 85% of predictions is flagged as DIRECTIONALLY_BIASED.

---

**AP-03 — The Hedger**

*Description:* A prediction system that assigns probabilities close to 0.50 for everything, ensuring it is never badly wrong but also never useful.

*Harm:* Zero decision utility. Predictions near 0.50 do not differentiate outcomes and provide no actionable intelligence.

*IIOS safeguard:* Forecast Skill monitoring (PQD-12). A model with BSS consistently near 0 is reviewed for retirement. Predictions that do not add skill over the baseline are not useful.

---

**AP-04 — The Ghost Scenario**

*Description:* A scenario that remains active in the scenario set long after its activation conditions have been definitively refuted.

*Harm:* Decision Engine allocates attention and weight to scenarios that are no longer plausible. Tail scenario from opening remains active at 14:30 IST despite clearly not having activated.

*IIOS safeguard:* Monitoring Pipeline (PP-08) continuously checks for scenario refutation signals. Scenarios whose activation probability drops below 2% are automatically deactivated. Termination conditions are checked hourly.

---

**AP-05 — The Hindsight Predictor**

*Description:* A prediction system that performs well in back-test but fails in live operation because its "predictions" were actually calibrated on the outcomes they claim to predict.

*Harm:* False confidence in model quality. Live performance significantly worse than back-test.

*IIOS safeguard:* PIT semantics (Section 4.6): all predictions are generated from context that was available at prediction time. Outcome data is never allowed in prediction context. Walk-forward testing (Layer 16 ValidationEngine) validates that back-test performance holds in out-of-sample conditions.

---

**AP-06 — The Cascading Failure**

*Description:* Multiple prediction types all fail simultaneously because they all depend on the same upstream input (e.g., regime classification). When regime classification fails, all regime-conditioned predictions become unreliable.

*Harm:* Systemic degradation that appears as a single-source failure spreading through the prediction system.

*IIOS safeguard:* Dependency isolation: each prediction type maintains a fallback path that does not depend on the shared upstream input. When regime classification is unavailable, predictions use a "regime-agnostic" calibration profile.

---

**AP-07 — The False Precision Trap**

*Description:* Stating predictions with spuriously high precision. "NIFTY will close at 22,463.50 with 84.3% confidence." The implied precision has no basis in the model's actual resolution.

*Harm:* Misleads consumers about actual prediction quality. Creates false confidence in trade entry/exit precision.

*IIOS safeguard:* Rounding rules: price predictions are rounded to the nearest 5 points (appropriate for NIFTY). Probability predictions are rounded to 2 decimal places. Uncertainty bounds are stated as round numbers. False precision in explainability reports is explicitly flagged.

---

**AP-08 — The Invisible Assumption**

*Description:* A prediction that depends on material unstated assumptions. "NIFTY will close above 22,500" without declaring the implicit assumption "...assuming no major adverse events before 15:30 IST."

*Harm:* The prediction appears to fail without explanation when the implicit assumption is violated. No learning occurs because the failure is misattributed.

*IIOS safeguard:* Constitutional rule PC-P-003 mandates declaration of all material assumptions. Validation Stage V-03 checks for assumption declarations. Predictions without material assumptions declared for a high-uncertainty context are flagged.

---

**AP-09 — The Learning-Resistant System**

*Description:* A prediction system that does not learn from its errors. Calibration errors persist indefinitely because there is no outcome evaluation pipeline.

*Harm:* The system continues to make the same systematic errors forever. No improvement over time.

*IIOS safeguard:* Outcome evaluation (PP-09) is mandatory for all predictions with observable outcomes. Learning feedback to Learning Engine (Layer 13) is constitutional. The Learning Engine's calibration improvements (LT-05 equivalent) flow back to the Prediction Engine via PP-03 (Learning Feedback Pipeline).

---

## SUPPLEMENT G — OPERATIONAL RUNBOOK

### G.1 Prediction Engine Startup Sequence

The following 22-step sequence activates the Prediction Engine in the correct order at session start (execution window: 08:45–09:10 IST).

| Step | Action | Component | Success Criterion |
|---|---|---|---|
| 1 | Load persistent Prediction Registry from storage | PC-01 | Registry loaded; count > 0 if prior session exists |
| 2 | Load Prediction Catalog (calibration profiles and ensemble weights) | PC-02 | All active types have calibration profiles |
| 3 | Verify model version integrity (hash check) | PC-20 | All model hashes verified |
| 4 | Load Prediction Audit Manager; verify hash chain | PC-15 | Hash chain INTACT |
| 5 | Activate Prediction Health Manager | PC-17 | PSHS computation starts |
| 6 | Activate Prediction Archive Manager | PC-16 | Archive accessible; integrity verified |
| 7 | Activate Prediction Version Manager | PC-20 | Version registry current |
| 8 | Load Probability Engine priors | PC-06 | Prior distributions loaded for all types |
| 9 | Load Confidence Engine calibration history | PC-07 | Calibration history loaded |
| 10 | Load Uncertainty Engine floor parameters | PC-08 | Floor parameters loaded for all types |
| 11 | Activate Ensemble Manager; load ensemble weights | PC-09 | Weights loaded for current regime |
| 12 | Activate Model Selector; load model registry | PC-10 | All mandatory types have eligible models |
| 13 | Activate Prediction Validator; load constitutional rules | PC-11 | Validation pipeline ready |
| 14 | Activate Prediction Governance Manager; check queue | PC-14 | Queue < 5 items; no items > 24 hours old |
| 15 | Activate Prediction Distribution Manager; load consumer registry | PC-19 | Consumer registry current |
| 16 | Activate Prediction Comparator; load prior session predictions | PC-12 | Prior session predictions available |
| 17 | Activate Prediction Ranking Engine; load ranking profiles | PC-13 | Ranking profiles loaded |
| 18 | Activate Prediction Analytics Manager | PC-18 | Analytics engine ready |
| 19 | Request current context from input sources | PC-03 | Regime, portfolio, evidence available |
| 20 | Generate session-start prediction suite: PT-16, PT-17, PT-01, PT-03 | PC-03/04/05 | All session-start predictions generated and validated |
| 21 | Distribute session-start predictions to consumers | PC-19 | Decision Engine, RiskGuardian acknowledge receipt |
| 22 | Log startup completion to Prediction Audit Manager | PC-15 | Startup event logged |

**Startup health gate:** Steps 1-5 are blocking. If any of these fail, the Prediction Engine does not proceed to Step 6. Human operator is alerted immediately.

---

### G.2 Intraday Operations

**Continuous operations (running throughout trading session):**

| Operation | Component | Frequency | Alert Condition |
|---|---|---|---|
| Price prediction update (PT-01) | PC-03/04/09 | On significant price move (>0.2%) | Failure to generate within 60s of trigger |
| Probability Bayesian update | PC-06 | On each new evidence signal | Update latency > 200ms |
| Scenario probability revision | PC-05/06 | Every 15 minutes; on activation signal | Scenario probabilities not summing to 1.00 |
| Confidence decay application | PC-07 | Every 10 minutes | Confidence below minimum for any active prediction |
| PSHS computation | PC-17 | Every 60 seconds | PSHS drops below 0.55 |
| Governance queue monitoring | PC-14 | Continuous | Queue > 5 items or any item > 2 hours old (intraday) |
| Audit log flush | PC-15 | Every 5 minutes | Hash chain integrity failure |
| Monitoring pipeline scan | PP-08 | Every 2 minutes | Scenario invalidation signal detected |

**Key intraday events:**

09:15 IST — Market open: activate real-time price prediction monitoring (PT-01 continuous update)
10:00 IST — Morning scenario review: update scenario probabilities from first 45 minutes of trading
11:30 IST — Mid-morning review: recalibrate PT-03 (volatility) from intraday realized volatility
13:00 IST — Post-lunch review: update all session-end price forecasts (PT-01 session horizon)
14:30 IST — Pre-close review: final scenario probability update; generate close-price prediction
15:00 IST — Expiry warning: activate expiry-specific liquidity and execution predictions if applicable
15:30 IST — Close: deactivate real-time monitoring; initiate post-session processing

---

### G.3 Post-Session Operations (15:35 – 16:30 IST)

12-step post-session processing sequence:

| Step | Operation | Component |
|---|---|---|
| 1 | Collect session close prices and outcomes | PP-09 trigger |
| 2 | Run outcome evaluation pipeline for all expired predictions | PP-09 |
| 3 | Compute session accuracy and calibration statistics | PC-18 |
| 4 | Submit learning feedback to Learning Engine (Layer 13) | PP-03 trigger |
| 5 | Run drift detection scan for all active models | PC-18/PC-09 |
| 6 | Run calibration check for types with > 5 new evaluations | PC-07/PC-06 |
| 7 | Update ensemble weights based on session model performance | PC-09 |
| 8 | Generate session PQS report | PC-18 |
| 9 | Run governance queue review; escalate aged items | PC-14 |
| 10 | Execute archive pipeline | PP-10 |
| 11 | Verify audit log integrity | PC-15 |
| 12 | Generate PSHS trend report; prepare overnight prediction suite (PT-06, PT-13, PT-14) | PC-17/PC-04 |

---

### G.4 Recovery Procedures

**Recovery Procedure 1 — Hash Chain Integrity Failure:**

1. Immediately halt all prediction distribution
2. Alert human operator via Telegram
3. Run full audit log integrity verification scan
4. Identify the point of hash chain corruption
5. Quarantine predictions generated after the corruption point
6. Restore audit log from last verified backup if available
7. If no backup: generate incident report; contact IIOS architecture authority
8. Do not resume prediction distribution until hash chain is verified INTACT

**Recovery Procedure 2 — Calibration Emergency (error > 25%):**

1. Suspend the affected prediction type immediately (per PC-F-002)
2. Alert operator: "PT-XX suspended due to calibration error > 25%"
3. Identify the cause: regime change? Data quality degradation? Model corruption?
4. Recalibrate using current-regime data (minimum 20 samples required)
5. Generate new model version via PC-20
6. Submit for TIER-3-HUMAN governance review
7. Deploy after human approval
8. Monitor for 5 sessions post-deployment

**Recovery Procedure 3 — Scenario Generator Failure:**

1. Activate default scenario templates from Supplement C
2. Assign historical base-rate probabilities to default templates
3. Distribute with FALLBACK_SCENARIO flag
4. Alert operator
5. Investigate and resolve root cause
6. Regenerate scenarios when root cause is resolved
7. Supersede fallback scenarios with new generated scenarios

**Recovery Procedure 4 — No Predictions Available (PSHS < 0.35):**

1. Enter EMERGENCY_MODE immediately
2. Halt all active prediction distribution
3. Alert operator urgently
4. Notify Decision Engine: prediction support unavailable; Decision Engine switches to conservative mode
5. Attempt component-by-component restart in startup sequence order
6. Resume prediction generation when PSHS > 0.55
7. Perform accelerated validation on first predictions after recovery

---

### G.5 Weekly Maintenance Checklist

| Operation | Frequency | Owner |
|---|---|---|
| Full accuracy report for all prediction types | Weekly | PC-18 |
| Drift detection scan (full history) | Weekly | PC-18 |
| Calibration report for all types and regimes | Weekly | PC-07 |
| Model version review: retire old versions > 20 behind current | Weekly | PC-20 |
| Ensemble weight review: is any single model > 70% weight? | Weekly | PC-09 |
| Bias detection scan (full history) | Weekly | PC-12 |
| Governance queue deep review | Weekly | PC-14 |
| Archive integrity verification | Weekly | PC-16 |
| Prediction taxonomy review: are all 18 types actively generating? | Weekly | PC-17 |
| Anti-pattern scan: check for known anti-pattern signatures | Weekly | PC-18 |

---

## SUPPLEMENT H — COMPREHENSIVE GLOSSARY AND GOVERNING DESIGN RECORDS

### H.1 Glossary

**Accuracy (PQD-01):** The quality dimension measuring whether a prediction's central estimate is correct when evaluated against the actual outcome. The highest-weight quality dimension in the PQS formula.

**Adaptive Prediction:** A prediction that updates in real-time as new signals arrive. Adaptive predictions are never frozen — they evolve with every new observation via the Probability Engine's Bayesian update mechanism.

**Assumption (definitional ladder Level 1):** A premise accepted as true without current formal evidence. All material assumptions underlying a prediction must be declared per constitutional rule PC-P-003.

**Bayesian Updating:** The process of revising probability estimates in light of new evidence using Bayes' theorem. The primary mechanism for real-time probability revision in the Prediction Engine.

**Brier Score:** A proper scoring rule for probabilistic predictions. Computed as (p - o)^2 where p is stated probability and o is binary outcome. Lower is better; 0.00 is perfect; 0.25 is the naive baseline.

**Brier Skill Score (BSS):** BSS = 1 - (Brier_Score / Brier_Score_baseline). Measures the prediction engine's skill relative to the historical frequency baseline. BSS > 0 means positive skill.

**Calibration (PQD-02):** The correspondence between stated probability and observed frequency. A well-calibrated system assigns probability 0.70 to events that occur 70% of the time.

**Calibration Error:** The absolute difference between stated mean probability and observed outcome frequency for a batch of predictions. Target: < 10% for all active types.

**Confidence (PQD-03):** The meta-level quality measure of a prediction: how much should the consumer trust this prediction's probability estimate? Confidence is distinct from probability.

**Conditional Prediction:** A prediction whose probability is conditioned on a specified precondition. "IF event A, THEN P(outcome B) = 0.72."

**CRPS (Continuous Ranked Probability Score):** A proper scoring rule for distributional predictions (PT-18). Generalizes the Brier Score to continuous distributions. Lower CRPS = better distributional prediction.

**Deterministic Prediction:** A prediction with a single stated outcome and no uncertainty. Prohibited in IIOS except for mechanically-determined outcomes with probability > 0.99.

**Distribution Prediction (PT-18):** A prediction of the full probability density function over an outcome variable. The highest-information-content prediction form.

**Drift (PQD-11):** The gradual degradation of model accuracy over time. Detected by comparing rolling accuracy windows. Three types: concept drift, data drift, model miscalibration.

**Ensemble Prediction:** A prediction formed by aggregating the outputs of multiple prediction models. Ensemble Manager (PC-09) performs this aggregation.

**Event Prediction (PT-15):** Predictions about the probability, timing, and market impact of specific future events (RBI meetings, earnings, index rebalancings).

**Expectation:** The probability-weighted average of possible outcomes. The mathematical expected value across all scenarios.

**Explainability (PQD-08):** The degree to which a prediction is accompanied by a traceable, human-readable explanation of its driving evidence, model structure, and material assumptions.

**Feature Attribution:** A report identifying the specific model features that most influenced an AI model's prediction output. Required for all AI predictions (constitutional rule PC-P-001).

**Forecast:** A quantitative prediction of a specific measurable quantity at a defined future time horizon. The most structured and specific prediction form.

**Forecast Skill (PQD-12):** The degree to which a prediction adds value over a naive baseline. Measured by BSS or CRPS Skill Score.

**Generalization (PQD-06):** The degree to which a prediction model performs well across different market conditions and not just the specific conditions on which it was trained.

**Ghost Scenario:** An anti-pattern where scenarios that have been refuted remain active in the scenario set. Prevented by the monitoring pipeline's deactivation logic.

**Governing Design Record (GDR):** An immutable architectural decision for the Prediction Engine. Eight GDRs are defined in Section H.2.

**Kill Switch:** The RiskGuardian (Layer 9) mechanism that halts all trading operations. The Prediction Engine NEVER modifies Kill Switch logic or behavior (GDR-PRD-007).

**Likelihood:** A relative comparison between hypotheses given observed data. The basis for Bayesian updating.

**Material Assumption:** An assumption whose removal would change the prediction probability by more than 10 percentage points. All material assumptions must be declared.

**Model Selector (PC-10):** The component responsible for selecting appropriate prediction models for each request.

**Multi-Horizon Prediction:** Simultaneous predictions at multiple time horizons (5-min, 15-min, 30-min, 60-min, session) that are internally consistent.

**Outcome:** The actual realized future state against which a prediction is evaluated.

**Outcome Evaluation Pipeline (PP-09):** The pipeline that evaluates every expired prediction against its actual outcome and feeds results back to the Learning Engine.

**Point-in-Time (PIT) Semantics:** The principle that a prediction is generated from a context snapshot that reflects the exact state of all inputs at the moment of context assembly. Subsequent changes do not retroactively alter the prediction.

**Possibility (definitional ladder Level 2):** A future state that cannot be ruled out. No probability assigned. Defines the outer boundary of the prediction space.

**Prediction:** A broad statement about future states, events, or conditions. May include quantitative forecasts and qualitative assessments.

**Prediction Builder (PC-03):** The intake and context-assembly component of the Prediction Engine.

**Prediction Catalog (PC-02):** The structured classification index for calibration profiles and ensemble weights by prediction type and regime.

**Prediction Constitution:** The set of 100+ immutable rules governing the Prediction Engine (Part IX).

**Prediction Quality Score (PQS):** The composite quality metric for prediction outputs. Computed as weighted sum of 13 PQD dimensions. Tiers: EXCELLENT (0.88+), GOOD (0.72-0.87), ACCEPTABLE (0.56-0.71), MARGINAL (0.35-0.55), FAILED (< 0.35).

**Prediction Registry (PC-01):** The operational store of all current and recent prediction records.

**Prediction System Health Score (PSHS):** The weighted aggregate health score of all 20 Prediction Engine components. Reported to ControlTower every 60 seconds.

**Prediction Validator (PC-11):** The component that runs the 5-stage validation pipeline on every generated prediction.

**Probabilistic Prediction:** A prediction expressed as a probability distribution over possible outcomes. The primary prediction form of the IIOS.

**Probability (definitional ladder Level 4):** A quantified measure of likelihood, expressed between 0 and 1.

**Probability Distribution Prediction (PT-18):** See Distribution Prediction.

**Probability Engine (PC-06):** The component dedicated to computing, calibrating, and managing probability assignments.

**Projection (definitional ladder Level 8):** An extrapolation of a current trend or trajectory into the future, assuming continuity.

**Recency Bias:** A bias where the most recent market moves are over-weighted in the evidence base. Controlled by the minimum lookback rule (PC-K-004).

**Regime Applicability:** The property of a prediction model that specifies which market regimes it has been validated for. Models applied to untested regimes are flagged REGIME_UNTESTED.

**Reliability (PQD-04):** The completeness and quality of the data inputs used to generate a prediction.

**Risk (definitional ladder Level 11):** The probability-weighted exposure to unfavorable outcomes. Combines probability with impact.

**Risk Prediction (PT-05):** Predictions about the probability and magnitude of adverse portfolio outcomes.

**Robustness (PQD-07):** The degree to which a prediction is resilient to small input perturbations.

**Scenario (definitional ladder Level 12):** A coherent, internally consistent narrative of a future state.

**Scenario Generator (PC-05):** The component that produces structured scenario sets.

**Scenario Prediction (PT-16):** A structured set of alternative futures, each with probabilities, drivers, and implications.

**Stability (PQD-05):** The degree to which repeated generation for the same target and context produces consistent results.

**Strategy Prediction (PT-10):** Predictions about the likely performance of individual IIOS strategies under current conditions.

**Tail Risk Prediction (PT-17):** Predictions about low-probability, high-impact adverse outcomes.

**Target (definitional ladder Level 15):** A desired or expected outcome level used as a reference for trade management. The Prediction Engine provides forecast inputs from which targets are derived; it does not set targets directly.

**Temporal Consistency:** The property that multi-horizon forecasts are internally consistent: longer-horizon forecasts must not contradict shorter-horizon forecasts.

**Traceability (PQD-09):** The degree to which a prediction can be fully traced to its source data, models, and evidence chain.

**Uncertainty (PQD-13):** The range of possible outcomes around the central forecast. Quantified as confidence intervals by the Uncertainty Engine (PC-08).

**Uncertainty Engine (PC-08):** The component responsible for explicitly quantifying and representing the uncertainty in every prediction.

**Validation Pipeline:** The 5-stage pipeline (V-01 through V-05) run on every prediction before distribution.

---

### H.2 Governing Design Records

**GDR-PRD-001: Predictions are Advisory Only**

No prediction generated by the Prediction Engine constitutes a trade instruction, a risk limit, or a governance override. Predictions are advisory intelligence that informs decisions. The Decision Engine makes decisions; the Prediction Engine provides intelligence.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-PRD-002: Every Prediction Carries Uncertainty**

No prediction is distributed without an explicit uncertainty measure. Point estimates without confidence intervals are not valid Prediction Engine outputs. The Uncertainty Engine's output is a mandatory component of every prediction record.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-PRD-003: Probabilistic Always, Deterministic Never (unless mechanically certain)**

All Prediction Engine outputs are expressed as probability distributions or probability measures. Deterministic predictions (a single certain outcome) are prohibited unless the outcome is mechanically determined with probability ≥ 0.99.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-PRD-004: Audit Before Prediction Distribution**

No prediction is distributed to consumers until the Prediction Audit Manager has recorded the prediction generation event. If the Audit Manager is unavailable, prediction distribution is suspended until it is restored.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-PRD-005: No Prediction Records Deleted**

No prediction record, scenario record, probability record, or model version is ever deleted. The terminal states are ARCHIVED and RETIRED. Historical preservation of every prediction ever generated, along with its outcome evaluation, is permanent.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-PRD-006: Human Override is Absolute and Unconditional**

A human operator may override, suppress, or modify any prediction at any time, without justification. The override is recorded and eventually analysed as a learning event, but it is never contested, blocked, or deferred.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-PRD-007: Kill Switch is Never Subject to Prediction**

The Kill Switch mechanism — its activation logic, its activation thresholds, its persistence behavior, its deactivation requirement — is not subject to Prediction Engine outputs of any kind. No prediction may propose, suggest, or imply changes to Kill Switch behavior. When the Kill Switch is active, prediction distribution is frozen.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-PRD-008: Explainability is Non-Negotiable**

Every prediction distributed by the Prediction Engine is accompanied by a human-readable explanation of its driving evidence, model structure, and material assumptions. Predictions generated by AI/ML models carry feature attribution reports. Unexplained predictions are not distributed.

*Effective date: IIOS v1.0. Immutable.*

---

## APPENDIX: WORKED PREDICTION EXAMPLES

### Worked Example WE-01: Complete NIFTY Session Prediction Cycle

**Scenario:** July 3, 2026, session start. The Prediction Engine generates the complete prediction suite for the trading session.

**Context assembly (08:55 IST):**

| Input | Value |
|---|---|
| Overnight US market (S&P 500) | +0.8% |
| Overnight Asia (Nikkei) | +0.6% |
| India VIX | 13.4 |
| Prior session NIFTY close | 22,580 |
| Current NIFTY futures | 22,640 (indicative) |
| Regime (MarketIntelligence) | TRENDING_BULL |
| Active hypotheses | H-007: NIFTY uptrend continuation (confidence 0.71) |
| Recent evidence | Price above 20/50 EMA, FII net buyer 3 consecutive sessions |
| MarketSimulation output | Bull scenario 38%, Base 35%, Bear 20%, Tail 7% |

**Step 1: Generate PT-16 (Scenario Prediction)**

Scenario Generator builds session scenario set:

| Scenario | Probability | NIFTY Range | Key Driver |
|---|---|---|---|
| BULL | 0.40 | 22,700 – 22,920 | Global tailwind + TRENDING_BULL regime |
| BASE | 0.32 | 22,580 – 22,700 | Moderate consolidation after prior gains |
| BEAR | 0.20 | 22,380 – 22,580 | Profit taking; NIFTY near short-term resistance |
| TAIL_DOWN | 0.08 | < 22,300 | Unexpected adverse event (VIX spike > 18) |

Probability check: 0.40 + 0.32 + 0.20 + 0.08 = 1.00 ✅

**Step 2: Generate PT-01 (Price Prediction) — session close**

Forecast Generator outputs:
- Point estimate: 22,760
- 1-sigma range: [22,630, 22,890]
- 2-sigma range: [22,510, 23,010]
- P(close > 22,640): 0.67
- Confidence: 0.76, PQS: 0.79

**Step 3: Generate PT-03 (Volatility Prediction) — session**

- Expected realized volatility: 11.8% annualized
- Intraday range estimate: 0.5% – 0.9% of open
- P(volatility expansion): 0.30

**Step 4: Generate PT-17 (Tail Risk Prediction)**

- P(session loss > 1.5% from open): 0.07 (from TAIL_DOWN scenario)
- P(Kill Switch proximity — VIX > 35): 0.01
- Risk state: LOW

**Step 5: Validation**

All four predictions pass 5-stage validation:
- Structural: PASS
- Probability integrity: PASS (scenario sum = 1.00)
- Evidence grounding: PASS (FII signal, H-007 active)
- Calibration check: PASS (PQS values in GOOD tier)
- Regime applicability: PASS (all models have > 20 sessions in TRENDING_BULL)

**Step 6: Governance and Distribution**

TIER-1-AUTO for all four predictions (PQS > 0.72, no flags).

Distributed at 09:02 IST to:
- Decision Engine (L10): receives all four predictions
- Capital Risk Engine (L6): receives PT-03 (volatility), PT-17 (tail risk)
- RiskGuardian (L9): receives PT-17 (tail risk), TAIL_DOWN scenario
- ControlTower dashboard: receives all predictions

---

### Worked Example WE-02: Real-Time Probability Update

**Scenario:** 09:40 IST. NIFTY has gapped up and is now +0.9% from open. Strong buying observed.

**Prior probability state (09:02 IST):**
P(BULL scenario) = 0.40, P(BASE) = 0.32, P(BEAR) = 0.20, P(TAIL_DOWN) = 0.08

**New evidence at 09:40 IST:**
- NIFTY at 22,844 — upper end of BULL range
- FII buying: net +580 Cr in first 25 minutes (strong signal)
- BANKNIFTY outperforming NIFTY by 0.3% (sector leadership)
- VIX dropped to 12.9

**Bayesian Update:**

Likelihood of observing this combination given BULL scenario: 0.82
Likelihood given BASE: 0.25
Likelihood given BEAR: 0.05
Likelihood given TAIL_DOWN: 0.02

Unnormalized posteriors:
BULL: 0.82 × 0.40 = 0.328
BASE: 0.25 × 0.32 = 0.080
BEAR: 0.05 × 0.20 = 0.010
TAIL_DOWN: 0.02 × 0.08 = 0.0016

Total (normalizer): 0.328 + 0.080 + 0.010 + 0.0016 = 0.4196

Updated posteriors:
BULL: 0.328 / 0.4196 = 0.78
BASE: 0.080 / 0.4196 = 0.19
BEAR: 0.010 / 0.4196 = 0.02
TAIL_DOWN: 0.0016 / 0.4196 = 0.004 (rounds to 0.01 — floor applied)

Re-normalized with floor applied: BULL 0.77, BASE 0.19, BEAR 0.03, TAIL_DOWN 0.01 (sum = 1.00 ✅)

**Distribution:** Prediction Registry updated. Decision Engine receives: "BULL scenario probability updated from 0.40 → 0.77. Significant probability shift (+0.37). Confidence: 0.81."

Decision Engine debate notes the significant BULL probability increase.

---

### Worked Example WE-03: Scenario Invalidation and Replacement

**Scenario:** 11:00 IST. The BEAR scenario activation signal fires: NIFTY drops below intraday VWAP and holds there for 35 minutes.

**Prior state:** BULL 0.77, BASE 0.19, BEAR 0.03, TAIL_DOWN 0.01

**Bear activation signal detected:**

The monitoring pipeline (PP-08) detects: NIFTY below VWAP for 32 minutes. BEAR scenario activation condition: "NIFTY below VWAP for 30+ minutes."

**BEAR scenario activates:**

Scenario probabilities revised:
- BEAR: elevated from 0.03 to 0.30 (significant reversal signal)
- BULL: reduced from 0.77 to 0.40 (still dominant but contested)
- BASE: 0.26 (increased — consolidation alternative)
- TAIL_DOWN: 0.04

Sum = 1.00 ✅

**Price prediction revised:**

PT-01 (Price, session close) revised:
- Prior: 22,760, P(up) = 0.67
- Revised: 22,660, P(up) = 0.50
- Confidence adjusted: 0.76 → 0.65 (scenario conflict increases uncertainty)
- Uncertainty bounds widened by 15%

**Distribution:** All consumers receive scenario update event. Decision Engine receives highest-priority update: scenario transition in progress.

---

### Worked Example WE-04: AI Model Prediction with Explainability

**Scenario:** Generating PT-10 (Strategy Prediction) using an AI pattern recognition model.

**Model:** Neural-network pattern classifier trained to recognize regime-strategy match patterns.

**Prediction:**

Target: STR-PAIRS_ARBITRAGE_003 performance probability for next session.

| Field | Value |
|---|---|
| prediction_id | PRD-PT10-20260703-00000018 |
| probability_profitable_session | 0.52 |
| confidence_score | 0.61 |
| pqs_score | 0.72 (GOOD — just at threshold) |
| model_type | AI (neural network) |
| explainability_required | YES (PC-P-001) |

**Feature Attribution Report (generated by AI model explainability wrapper):**

Top 5 driving features and their contribution to P(profitable_session) = 0.52:

| Rank | Feature | Direction | Contribution |
|---|---|---|---|
| 1 | NIFTY-BANKNIFTY correlation (current session) | Positive | +0.09 |
| 2 | Strategy Sharpe ratio (last 20 sessions) | Positive | +0.07 |
| 3 | Pairs volatility spread (current) | Negative | -0.04 |
| 4 | Regime: TRENDING_BULL (less favorable for pairs) | Negative | -0.07 |
| 5 | Time since last profitable session (2 sessions) | Neutral | +0.01 |

**Human-readable explanation:**

"Strategy prediction for STR-PAIRS_ARBITRAGE_003: 52% probability of profitable session.
Positive factors: Strong NIFTY-BANKNIFTY correlation (pairs strategies benefit from correlated moves), acceptable recent Sharpe.
Negative factors: TRENDING_BULL regime is suboptimal for pairs arbitrage (strategy performs better in RANGING regimes — see Pattern PAT-STRATEGY-20260510-000007 equivalent). Pairs volatility spread currently elevated (reduces edge).
Assessment: Marginally above 50% probability. Conservative sizing recommended."

**Governance:** TIER-1-AUTO (PQS 0.72, explainability report complete). Distributed to MetaLearning (L3) for strategy weight input.

---

### Worked Example WE-05: Prediction Outcome Evaluation

**Scenario:** Session end, July 3, 2026. Evaluating the session-start price prediction.

**Original prediction (generated 09:05 IST):**
- Prediction ID: PRD-PT01-20260703-00000001
- Point estimate: 22,760
- 1-sigma range: [22,630, 22,890]
- P(close > 22,640): 0.67
- Horizon: session close (15:30 IST)

**Actual outcome (15:30 IST):**
- NIFTY session close: 22,834

**Outcome evaluation (executed 15:40 IST):**

| Metric | Computation | Score |
|---|---|---|
| Directional accuracy | Predicted UP (P = 0.67); actual = UP (close 22,834 > open 22,640) | CORRECT (1.0) |
| Interval coverage | Actual 22,834 within [22,630, 22,890]? | YES — within 1-sigma interval ✅ |
| Point estimate error | |22,834 - 22,760| = 74 points (0.33% error) | Excellent |
| Brier Score | (0.67 - 1.0)^2 = 0.11 | Good |
| Calibration contribution | Prediction is 1 of 847 evaluated today — contributes to rolling calibration |  |
| PQS post-outcome update | Accuracy dimension updated: 0.90 | PQS revised: 0.82 |

**Learning feedback submitted:**
- Type: PT-01 Price Prediction
- Horizon: Session
- Regime: TRENDING_BULL
- Directional accuracy: CORRECT
- Brier Score: 0.11
- Interval coverage: WITHIN_1SIGMA
- Learning Engine (L13) receives this as a model performance record

---

### Worked Example WE-06: Full Scenario Lifecycle — TAIL_DOWN Termination

**Scenario:** A TAIL_DOWN scenario was generated at session start with 8% probability. By 14:00 IST, it is clearly not playing out. The monitoring pipeline initiates termination.

**Original scenario:** TAIL_DOWN — P = 0.08. Activation signal: "NIFTY down > 1.5% from open OR VIX spike > 5 points intraday."

**State at 14:00 IST:**
- NIFTY at 22,834 — up 0.86% from open
- VIX at 12.9 — down 0.5 points from session start
- No adverse events

**Monitoring pipeline check:**
- Activation signal: NOT triggered (NIFTY is UP, not down 1.5%)
- Termination condition check: "NIFTY recovery above -1.5% from open; VIX stabilizes" — MET

**Termination sequence:**

1. Monitoring pipeline (PP-08) detects termination condition met
2. TAIL_DOWN scenario status → TERMINATED
3. Probability mass redistributed: 0.08 reallocated proportionally to remaining scenarios
4. Updated: BULL 0.79, BASE 0.17, BEAR 0.04, TAIL_DOWN 0.00 (removed from active set)
5. New scenario probabilities sum: 0.79 + 0.17 + 0.04 = 1.00 ✅
6. Audit log: TAIL_DOWN-SCN-NIFTY-20260703-0001 terminated at 14:03:22 IST — termination condition met
7. Decision Engine notified: tail risk scenario terminated; portfolio tail risk reduced
8. RiskGuardian notified: TAIL_DOWN no longer active
9. Capital Risk Engine: position sizing constraints from tail risk slightly relaxed

**Post-session outcome evaluation:**
TAIL_DOWN did not occur. Prediction accuracy for this scenario: CORRECT (predicted low probability; scenario did not occur). Brier Score contribution: (0.08 - 0.0)^2 = 0.0064 (excellent).

---

## DOCUMENT SUMMARY AND CLOSING MATERIALS

### Summary Section 1: Document Metrics

| Metric | Value |
|---|---|
| Document title | IIOS Prediction Engine Architecture |
| Document code | IIOS-PRD-ENG-ARCH-001 |
| Layer context | Cross-cutting intelligence service; primary consumer: Layer 10 (DebateAndDecision) |
| Parts | I through X |
| Supplements | A through H |
| Governing Design Records | 8 (GDR-PRD-001 through GDR-PRD-008) |
| Constitutional rule categories | 16 (PC-A through PC-P) |
| Constitutional rules | 100+ |
| Prediction types | 18 (PT-01 through PT-18) |
| Components | 20 (PC-01 through PC-20) |
| Services | 12 (PS-01 through PS-12) |
| Pipelines | 10 (PP-01 through PP-10) |
| Lifecycle stages | 15 (PLS-01 through PLS-15) |
| Lifecycle statuses | 19 |
| PQS dimensions | 13 (PQD-01 through PQD-13) |
| Anti-patterns documented | 9 (AP-01 through AP-09) |
| Standard scenario templates | 4 (BULL, BASE, BEAR, TAIL_DOWN) |
| Worked examples | 6 (WE-01 through WE-06) |
| Governing Design Records | 8 |
| Glossary terms | 65+ |

---

### Summary Section 2: Parts Summary

| Part | Title | Purpose |
|---|---|---|
| I | Prediction Philosophy and Definitional Framework | 15-level definitional ladder; 10 prediction types; 10 principles; epistemological foundations |
| II | Prediction Taxonomy | 18 prediction type definitions (PT-01 through PT-18) with source, inputs, consumers |
| III | Core Component Architecture | 20 components across 4 tiers; full 12-section definitions per component |
| IV | Prediction Lifecycle | 15 stages; 5-stage validation pipeline; state machine; lifecycle timing; PIT semantics |
| V | Prediction Services | 12 services (PS-01 through PS-12) with full specifications |
| VI | Prediction Pipelines | 10 pipelines (PP-01 through PP-10) with ASCII flow diagrams |
| VII | Prediction Quality Framework | 13 PQS dimensions; formula; tiers; monitoring thresholds |
| VIII | Prediction Governance | Ownership; naming; versioning; governance tier matrix; compliance; security; retention |
| IX | Prediction Constitution | 100+ rules across 16 categories (PC-A through PC-P) |
| X | Prediction Readiness Checklist | 6-section checklist; 5-level readiness matrix; readiness state machine |

---

### Summary Section 3: Supplements Summary

| Supplement | Title | Contents |
|---|---|---|
| A | Prediction Taxonomy Reference | Classification matrix (18 types) + IIOS layer mapping table |
| B | Forecast Examples and Reference Cases | Forecast record structure + 4 annotated forecast examples |
| C | Scenario Catalogue | 4 standard scenario templates + complete scenario record structure |
| D | Probability Reference and Calibration Guide | Brier Score, BSS, ECE, Bayesian updating example, calibration reference values |
| E | Bias and Drift Examples | 3 bias examples + 2 drift examples |
| F | Anti-Patterns | 9 anti-patterns (AP-01 through AP-09) with descriptions and IIOS safeguards |
| G | Operational Runbook | 22-step startup; intraday ops; 12-step post-session; 4 recovery procedures; weekly maintenance |
| H | Glossary and GDRs | 65+ glossary terms; 8 immutable GDRs |

---

### Summary Section 4: PQS Quick Reference

| Code | Dimension | Weight | Target |
|---|---|---|---|
| PQD-01 | Accuracy | 0.20 | > 0.55 (directional) |
| PQD-02 | Calibration | 0.15 | Error < 10% |
| PQD-03 | Confidence | 0.10 | > 0.60 average |
| PQD-04 | Reliability | 0.10 | > 0.85 |
| PQD-05 | Stability | 0.08 | > 0.80 |
| PQD-06 | Generalization | 0.08 | > 0.65 |
| PQD-07 | Robustness | 0.07 | > 0.70 |
| PQD-08 | Explainability | 0.05 | 1.00 (AI); > 0.80 (others) |
| PQD-09 | Traceability | 0.05 | 1.00 |
| PQD-10 | Bias | 0.04 | > 0.90 |
| PQD-11 | Drift | 0.04 | > 0.85 |
| PQD-12 | Forecast Skill | 0.02 | BSS > 0.10 |
| PQD-13 | Uncertainty Quality | 0.02 | Coverage ±5% of stated |
| **Total** | | **1.00** | |

---

### Summary Section 5: GDR Quick Reference

| GDR | Title | Immutable since |
|---|---|---|
| GDR-PRD-001 | Predictions are Advisory Only | IIOS v1.0 |
| GDR-PRD-002 | Every Prediction Carries Uncertainty | IIOS v1.0 |
| GDR-PRD-003 | Probabilistic Always, Deterministic Never | IIOS v1.0 |
| GDR-PRD-004 | Audit Before Prediction Distribution | IIOS v1.0 |
| GDR-PRD-005 | No Prediction Records Deleted | IIOS v1.0 |
| GDR-PRD-006 | Human Override is Absolute and Unconditional | IIOS v1.0 |
| GDR-PRD-007 | Kill Switch is Never Subject to Prediction | IIOS v1.0 |
| GDR-PRD-008 | Explainability is Non-Negotiable | IIOS v1.0 |

---

### Summary Section 6: Component-to-Tier Mapping

**Tier 1 — Storage and Registry**
- PC-01: Prediction Registry
- PC-02: Prediction Catalog

**Tier 2 — Generation**
- PC-03: Prediction Builder
- PC-04: Forecast Generator
- PC-05: Scenario Generator
- PC-06: Probability Engine
- PC-07: Confidence Engine
- PC-08: Uncertainty Engine
- PC-09: Ensemble Manager
- PC-10: Model Selector

**Tier 3 — Validation and Governance**
- PC-11: Prediction Validator
- PC-12: Prediction Comparator
- PC-13: Prediction Ranking Engine
- PC-14: Prediction Governance Manager
- PC-15: Prediction Audit Manager

**Tier 4 — Operations**
- PC-16: Prediction Archive Manager
- PC-17: Prediction Health Manager
- PC-18: Prediction Analytics Manager
- PC-19: Prediction Distribution Manager
- PC-20: Prediction Version Manager

---

### Summary Section 7: Governing Documents

| Document | Code | Relationship |
|---|---|---|
| ARCHITECTURE.md | IIOS-ARCH-000 | Master architecture |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | IIOS-KNW-ENG-ARCH-001 | Knowledge base consumed by Prediction Engine |
| OBSERVATION_ENGINE_ARCHITECTURE.md | IIOS-OBS-ENG-ARCH-001 | Observations consumed by Prediction Engine |
| EVIDENCE_ENGINE_ARCHITECTURE.md | IIOS-EVD-ENG-ARCH-001 | Evidence consumed by Prediction Engine |
| HYPOTHESIS_ENGINE_ARCHITECTURE.md | IIOS-HYP-ENG-ARCH-001 | Hypotheses consumed by Prediction Engine |
| REASONING_ENGINE_ARCHITECTURE.md | IIOS-RSN-ENG-ARCH-001 | Reasoning consumed by Prediction Engine |
| DECISION_ENGINE_ARCHITECTURE.md | IIOS-DEC-ENG-ARCH-001 | Primary prediction consumer |
| EXECUTION_ENGINE_ARCHITECTURE.md | IIOS-EXE-ENG-ARCH-001 | Execution predictions distributed here |
| LEARNING_ENGINE_ARCHITECTURE.md | IIOS-LRN-ENG-ARCH-001 | Learning Engine calibrates Prediction models |
| PREDICTION_ENGINE_ARCHITECTURE.md | IIOS-PRD-ENG-ARCH-001 | This document |

---

### Summary Section 8: Architectural Impact Statement

**What the Prediction Engine does:**
- Transforms the system's current understanding into probabilistic forward projections
- Generates quantitative forecasts with full uncertainty characterization
- Produces structured scenario sets covering the full probability space
- Computes calibrated probabilities for events and outcomes
- Ranks and governs prediction quality through a 5-stage validation pipeline
- Distributes validated predictions to authorized IIOS consumers
- Evaluates predictions against outcomes and feeds accuracy data to the Learning Engine

**What the Prediction Engine does NOT do:**
- Execute trades
- Make investment decisions
- Override the Decision Engine
- Override the Kill Switch
- Override human operators
- Apply knowledge updates (that is the Learning Engine's role)
- Set price targets directly (it provides forecast inputs for target computation)

**Failure impact:** If the Prediction Engine fails, the IIOS continues to operate but the Decision Engine operates without prediction intelligence. This means: no scenario probabilities, no quantitative price forecasts, no strategy performance predictions. The system defaults to conservative decision-making until predictions are restored.

---

### Summary Section 9: Ratification Statement

This document has been reviewed for completeness, internal consistency, and full alignment with all predecessor IIOS architecture documents. The following statements are confirmed:

1. The Prediction Engine is correctly characterized as a cross-cutting intelligence service with primary output to Layer 10 (DebateAndDecision).
2. The eight GDRs are consistent with the governance frameworks in the Decision Engine and Learning Engine architectures.
3. The Prediction Constitution does not conflict with any prior architecture document's constitutional rules.
4. The Kill Switch is explicitly and unconditionally exempt from Prediction Engine outputs (GDR-PRD-007).
5. Human operator authority is explicitly preserved and unconditional (GDR-PRD-006).
6. The PQS framework is consistent with and complementary to the LQS (Learning) and EQS (Execution) quality frameworks.
7. The governance tier model is consistent with the governance tier model in prior architecture documents.
8. No Prediction Engine output can authorize a trade, override a risk limit, or bypass governance.
9. All AI-generated predictions require explainability reports (GDR-PRD-008).
10. The prediction audit log uses the same hash-chain integrity approach as the Learning Engine audit log.

**Document status:** RATIFIED

**Document code:** IIOS-PRD-ENG-ARCH-001

---

## END OF DOCUMENT

### Document Footer

`
=============================================================================
IIOS PREDICTION ENGINE ARCHITECTURE
Document Code: IIOS-PRD-ENG-ARCH-001
Layer: Cross-cutting intelligence service
Primary consumer: Layer 10 (DebateAndDecision)
Status: RATIFIED
Series: IIOS Architecture Document Series
=============================================================================
Inputs:         Knowledge · Observation · Evidence · Hypothesis · Reasoning
                Learning · GlobalIntelligence (L1) · MarketIntelligence (L2)
                MarketSimulation (L8)
Outputs:        Decision Engine (L10) · MetaLearning (L3) · StrategyLab (L5)
                RiskControl (L7) · RiskGuardian (L9) · ControlTower (L17)
=============================================================================
Constitutional rules:     100+ (PC-A through PC-P)
Governing Design Records: 8   (GDR-PRD-001 through GDR-PRD-008)
Prediction types:         18  (PT-01 through PT-18)
Components:               20  (PC-01 through PC-20)
Services:                 12  (PS-01 through PS-12)
Pipelines:                10  (PP-01 through PP-10)
Lifecycle stages:         15
PQS dimensions:           13
=============================================================================
The Prediction Engine does not reason.
The Prediction Engine does not decide.
The Prediction Engine does not execute.
The Prediction Engine predicts — probabilistically, explainably,
with full uncertainty, and always in service of better decisions.
=============================================================================
`

---

## SUPPLEMENT I — CROSS-LAYER INTEGRATION REFERENCE AND PERFORMANCE TARGETS

### I.1 Prediction Engine Cross-Layer Integration Summary

The Prediction Engine is unique in the IIOS stack: it is the most broadly connected component, receiving inputs from 9 layers and delivering outputs to 7 layers. This supplement provides a concise cross-layer integration reference.

---

### I.2 Input Integration Contracts

| Source Layer | Signals Consumed | Frequency | Prediction Types Enabled |
|---|---|---|---|
| L1 GlobalIntelligence | Overnight S&P, Nikkei, bonds, FX, VIX | Daily (overnight) | PT-06 Macro, PT-13 Cross-Market, PT-14 Cross-Asset, PT-16 Scenario |
| L2 MarketIntelligence | Regime, sector rotation, liquidity, event calendar | Per session + intraday | All types (regime conditions every prediction) |
| L4 OpportunityEngine | Opportunity signals, scanner output | Per scan cycle | PT-08 Company, PT-07 Sector |
| L8 MarketSimulation | Monte Carlo distributions, 14 scenario outputs | Session start + triggers | PT-16 Scenario, PT-17 Tail Risk, PT-18 Distribution |
| L12 TradeMonitoring | Closed trade outcomes, execution records | Per trade close | Outcome evaluation (PP-09) for all types |
| L13 LearningSystem | Calibration updates, model improvements | Per Learning Engine deployment | All types (via PP-03 Learning Feedback Pipeline) |
| L14 PerformanceAnalytics | Historical performance, drawdown data | Session end | PT-05 Risk, PT-09 Portfolio, PT-10 Strategy |
| L16 ValidationEngine | Out-of-sample feedback, walk-forward results | Per validation cycle | PT-10 Strategy (strategy prediction calibration) |
| Knowledge Engine | Entity data, domain rules, model constraints | Daily | PP-01 Knowledge-to-Prediction Pipeline |

---

### I.3 Output Integration Contracts

| Consumer Layer | Predictions Delivered | Frequency | How Consumed |
|---|---|---|---|
| L3 MetaLearning | PT-10 Strategy predictions, PT-02 Trend | Session end | Strategy weight recalibration input |
| L5 StrategyLab | PT-10 Strategy, PT-15 Event | Session end + event triggers | Strategy selection, evolution guidance |
| L6 CapitalRisk | PT-03 Volatility, PT-18 Distribution, PT-09 Portfolio | Per update | Position sizing computation |
| L7 RiskControl | PT-05 Risk, PT-17 Tail Risk, PT-03 Volatility | Every 30 min | Risk management adjustments |
| L9 RiskGuardian | PT-17 Tail Risk, PT-16 TAIL_DOWN scenario | Every 30 min | Kill Switch proximity assessment |
| L10 DebateAndDecision | All types (primary consumer) | On demand + continuous | Decision scoring, debate inputs |
| L11 Execution | PT-04 Liquidity, PT-11 Execution | Pre-order | Order type selection, slippage estimation |
| L17 ControlTower | PSHS, all prediction types (dashboard) | Every 60 sec (PSHS); per update (predictions) | Telemetry, dashboard display |

---

### I.4 Performance Targets

**On-critical-path operations (must complete within session trade cycle):**

| Operation | Time Budget | SLA Target | Action if Exceeded |
|---|---|---|---|
| On-demand price forecast (PT-01) from cache | < 100 ms | 99th percentile | Log; serve cache value |
| On-demand price forecast (PT-01) fresh generation | < 500 ms | 99th percentile | Fall back to cache |
| Scenario probability update | < 200 ms | 99th percentile | Defer; serve prior probabilities |
| Probability Bayesian update | < 50 ms | 99th percentile | Queue and process async |
| PSHS computation | < 50 ms | 99th percentile | Serve cached value |
| Prediction Registry read | < 20 ms | 99th percentile | Serve from in-memory cache |

**Asynchronous operations (off-critical-path):**

| Operation | Time Budget | Cadence |
|---|---|---|
| Scenario generation (session start) | < 3 minutes | Session start |
| Full prediction suite generation | < 5 minutes | Session start |
| Outcome evaluation pipeline | < 10 minutes | Session end |
| Model drift scan | < 2 minutes | Daily |
| Calibration check | < 3 minutes | Per type, weekly or on threshold trigger |
| Archive pipeline | < 5 minutes | Session end |
| Learning feedback submission | < 2 minutes | Session end |
| Audit log verification | < 1 minute | Daily |

---

### I.5 Service Level Targets

| SLT Code | Target | Measurement |
|---|---|---|
| SLT-PRD-01 | PSHS > 0.80 at session start | Session start health check |
| SLT-PRD-02 | Session-start predictions generated by 09:10 IST | Daily |
| SLT-PRD-03 | Prediction pass rate > 90% (validation stage) | Rolling 5 sessions |
| SLT-PRD-04 | Average PQS > 0.65 (GOOD tier) | Rolling 5 sessions |
| SLT-PRD-05 | Calibration error < 15% for all active types | Rolling 20 sessions |
| SLT-PRD-06 | Outcome evaluation rate > 90% | Weekly |
| SLT-PRD-07 | Audit log hash chain intact: 100% | Continuous |
| SLT-PRD-08 | No prediction distributed without uncertainty bounds | Per prediction — zero tolerance |
| SLT-PRD-09 | No AI prediction distributed without explainability report | Per prediction — zero tolerance |
| SLT-PRD-10 | Governance queue cleared within 24 hours | Daily |
| SLT-PRD-11 | PSHS reported to ControlTower every 60 seconds | Continuous |
| SLT-PRD-12 | No predictions distributed during Kill Switch activation | Zero tolerance |

---

### I.6 Prediction Engine Identifier Reference

| Object | Format | Example |
|---|---|---|
| Prediction record | PRD-{TYPE}-{YYYYMMDD}-{SEQ:08d} | PRD-PT01-20260703-00000042 |
| Forecast record | FCS-{HORIZON}-{YYYYMMDD}-{SEQ:06d} | FCS-SESSION-20260703-000007 |
| Scenario set | SCN-{TARGET}-{YYYYMMDD}-{SEQ:04d} | SCN-NIFTY-20260703-0001 |
| Scenario | SCN-{SET_ID}-{NAME} | SCN-NIFTY-20260703-0001-BULL |
| Probability record | PRB-{EVENT}-{YYYYMMDD}-{SEQ:06d} | PRB-NIFTY_UP-20260703-000005 |
| Model version | PVR-{MODEL}-{VERSION:04d} | PVR-NIFTY_PRICE_MODEL-0023 |
| Audit entry | PAUD-{PRD_ID}-{SEQ:04d} | PAUD-PRD-PT01-20260703-00000042-0001 |
| Quality report | PQR-{YYYYMMDD}-{SEQ:04d} | PQR-20260703-0001 |
| Governance item | GOV-PRD-{TIER}-{YYYYMMDD}-{SEQ:06d} | GOV-PRD-TIER2-20260703-000001 |

---

### I.7 Five Things the Prediction Engine Never Does

1. **Never executes trades.** The Prediction Engine has no connection to the Order Manager or any broker interface. It produces intelligence; it never acts.

2. **Never overrides the Decision Engine.** Predictions are advisory inputs to the Decision Engine's debate process. The Decision Engine weighs predictions against all other evidence and makes its own decision. A high-probability prediction does not compel a trade.

3. **Never bypasses governance.** Every prediction passes through the 5-stage validation pipeline and governance approval before distribution. No shortcut path exists.

4. **Never touches the Kill Switch.** GDR-PRD-007 is absolute. When the Kill Switch is active, prediction distribution is frozen. The Prediction Engine never assesses, proposes, or influences Kill Switch behavior.

5. **Never distributes unexplained AI predictions.** GDR-PRD-008 is absolute. AI model predictions without feature attribution and human-readable explanation are not distributed.

---

### I.8 What Makes a Prediction Great

A great IIOS prediction is:

**Accurate:** It is correct more often than a naive baseline would be.

**Well-calibrated:** Its stated probabilities correspond to observed frequencies.

**Explainable:** A human operator can understand why the prediction was made.

**Humble:** It acknowledges its uncertainty with realistic bounds.

**Timely:** It is generated within the time constraints of the trading cycle.

**Robust:** It is not easily overturned by small input changes.

**Consistent:** It does not contradict related predictions without good reason.

**Self-improving:** Each evaluated outcome feeds back to make the next prediction better.

A prediction that is accurate but unexplainable is dangerous. A prediction that is explainable but poorly calibrated is misleading. Only the combination of all dimensions — embodied in the PQS framework — produces prediction intelligence that the Decision Engine can genuinely rely on.

The Prediction Engine's ultimate purpose is to equip the Decision Engine with the best possible probabilistic intelligence about the future, enabling better decisions, while always remembering that the future is uncertain, that markets are complex, and that humility about what we know is the foundation of robust investment decision-making.

---

## END OF SUPPLEMENT MATERIAL

---

## SUPPLEMENT J — QUICK-START REFERENCE CARD

### J.1 Critical Numbers

| Parameter | Value |
|---|---|
| Minimum probability for distribution | 0.01 |
| Maximum probability for distribution | 0.99 |
| Minimum PQS for distribution | 0.35 (FAILED tier rejected) |
| Minimum confidence for distribution | 0.25 |
| Minimum evidence items for grounding | 1 (with confidence > 0.40) |
| Minimum sessions for calibration | 20 |
| Maximum probability update per single event | 0.25 (25 percentage points) |
| Scenario probability floor | 0.01 |
| PSHS NOMINAL threshold | > 0.80 |
| PSHS DEGRADED threshold | 0.55 – 0.80 |
| PSHS CRITICAL threshold | 0.35 – 0.55 |
| PSHS EMERGENCY threshold | ≤ 0.35 |
| Calibration suspension threshold | > 25% error |
| Minimum lookback period (evidence) | 10 sessions |
| Governance queue maximum item age | 24 hours |

---

### J.2 The 18 Prediction Types at a Glance

| Code | Type | One-Line Description |
|---|---|---|
| PT-01 | Price | Price level and range at defined horizons |
| PT-02 | Trend | Trend direction continuation probability |
| PT-03 | Volatility | Expected realized volatility and range |
| PT-04 | Liquidity | Market depth and execution quality forecast |
| PT-05 | Risk | Probability and magnitude of adverse outcomes |
| PT-06 | Macro | Macroeconomic events and their market impact |
| PT-07 | Sector | Sector relative performance and rotation |
| PT-08 | Company | Earnings surprises and corporate events |
| PT-09 | Portfolio | Portfolio return, correlation, and factor exposure |
| PT-10 | Strategy | Per-strategy session performance probability |
| PT-11 | Execution | Slippage, fill probability, execution quality |
| PT-12 | Behavior | IIOS own behavioral bias probabilities |
| PT-13 | Cross-Market | Correlation-based forecasts from global markets |
| PT-14 | Cross-Asset | Cross-asset class relationship forecasts |
| PT-15 | Event | Scheduled event probability and impact |
| PT-16 | Scenario | Full alternative future scenario set (BULL/BASE/BEAR/TAIL) |
| PT-17 | Tail Risk | Low-probability, high-impact adverse outcome probabilities |
| PT-18 | Distribution | Full probability density function over outcomes |

---

### J.3 The Validation Pipeline in One Table

| Stage | Rule Type | Checks | Failure Action |
|---|---|---|---|
| V-01 Structural Validity | Hard | All fields present; type recognized; target valid | REJECT |
| V-02 Probability Integrity | Hard | Probabilities in [0,1]; scenarios sum to 1.00 | REJECT |
| V-03 Evidence Grounding | Soft | At least one evidence item with confidence > 0.40 | FLAG(UNSUPPORTED) |
| V-04 Calibration Check | Soft | Stated confidence within ±2σ of historical range | FLAG(CALIBRATION_MISMATCH) |
| V-05 Regime Applicability | Soft | Model has ≥ 5 sessions in current regime | FLAG(REGIME_UNTESTED) |

Hard rule failure = REJECTED (not distributed). Soft rule failure = FLAGGED or CONDITIONALLY_VALIDATED (distributed with flags).

---

### J.4 The Governance Decision Tree in One Table

| Condition | Tier | Approver | Distribution |
|---|---|---|---|
| PQS ≥ 0.72, no flags | TIER-1-AUTO | Automated | Immediate |
| 0.56 ≤ PQS < 0.72, soft flags | TIER-2-ADVISORY | Auto + operator notified | After notification |
| PQS < 0.56 or INCONSISTENT | TIER-3-HUMAN | Human operator | After approval |
| Model architecture change | TIER-4-COMMITTEE | Multi-reviewer | After full review |
| First new model deployment | TIER-3-HUMAN | Human operator | After approval |
