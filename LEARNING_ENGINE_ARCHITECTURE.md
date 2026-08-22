# IIOS LEARNING ENGINE ARCHITECTURE

**Document Code:** IIOS-LRN-ENG-ARCH-001
**Layer:** 13 of 17 — LearningSystem
**Status:** RATIFIED
**Series:** IIOS Architecture Document Series
**Depends on:** All prior IIOS Architecture Documents (IIOS-ARCH-000 through IIOS-EXE-ENG-ARCH-001)

---

## COGNITIVE LAYER STACK

`
+------------------------------------------------------------------+
|  17  ControlTower      Telemetry · Dashboard · EventBus          |
+------------------------------------------------------------------+
|  16  ValidationEngine  6-Stage Validation Pipeline               |
+------------------------------------------------------------------+
|  15  ResearchLab       Strategy Promotion / Demotion Gates       |
+------------------------------------------------------------------+
|  14  PerformanceAnalytics  Drawdown · WFT · Attribution          |
+------------------------------------------------------------------+
| ██████████████████████████████████████████████████████████████  |
| ██  13  LearningSystem ── THIS DOCUMENT                       ██  |
| ██  Continuous Learning · Pattern Discovery · Model Updates   ██  |
| ██████████████████████████████████████████████████████████████  |
+------------------------------------------------------------------+
|  12  TradeMonitoring   Trade Health · Strategy Health            |
+------------------------------------------------------------------+
|  11  ExecutionEngine   Order Construction · Broker Routing       |
+------------------------------------------------------------------+
|  10  DebateAndDecision 5-Agent Debate · DecisionEngine           |
+------------------------------------------------------------------+
|   9  RiskGuardian      Kill Switch · VIX Guard · Daily Loss      |
+------------------------------------------------------------------+
|   8  MarketSimulation  Monte Carlo · 14 Scenarios                |
+------------------------------------------------------------------+
|   7  RiskControl       RiskManagerAI · Stress Test               |
+------------------------------------------------------------------+
|   6  CapitalRiskEngine Position Sizing · Strategy Budget         |
+------------------------------------------------------------------+
|   5  StrategyLab       MetaStrategyController · Evolution        |
+------------------------------------------------------------------+
|   4  OpportunityEngine Equity Scanner · Arbitrage                |
+------------------------------------------------------------------+
|   3  MetaLearning      k-NN Strategy Weight Predictor            |
+------------------------------------------------------------------+
|   2  MarketIntelligence Regime · Sector · Liquidity · Events     |
+------------------------------------------------------------------+
|   1  GlobalIntelligence Overnight Global Context                 |
+------------------------------------------------------------------+
`

---

## INFORMATION FLOW

`
┌──────────────────────────────────────────────────────────────────────────┐
│                    ALL IIOS LAYERS (1–17)                                 │
│  Observations · Evidence · Hypotheses · Reasoning · Decisions ·          │
│  Executions · Fills · Outcomes · Errors · Anomalies · Alerts             │
└──────────────────────┬───────────────────────────────────────────────────┘
                        │  Learning Signals (continuous stream)
                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    LEARNING ENGINE (Layer 13)                             │
│                                                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │  COLLECTION TIER                                                │    │
│   │  Learning Collector → Learning Registry → Learning Processor   │    │
│   └─────────────────────────────┬──────────────────────────────────┘    │
│                                  │                                        │
│   ┌──────────────────────────────▼─────────────────────────────────┐    │
│   │  DISCOVERY TIER                                                 │    │
│   │  Pattern Discovery Engine → Knowledge Updater                  │    │
│   │  Outcome Analyzer → Error Analyzer → Bias Detector             │    │
│   │  Drift Detector → Feedback Manager                             │    │
│   └─────────────────────────────┬──────────────────────────────────┘    │
│                                  │                                        │
│   ┌──────────────────────────────▼─────────────────────────────────┐    │
│   │  VALIDATION AND GOVERNANCE TIER                                 │    │
│   │  Learning Validation Manager → Learning Governance Manager     │    │
│   │  Model Improvement Manager → Learning Audit Manager            │    │
│   └─────────────────────────────┬──────────────────────────────────┘    │
│                                  │                                        │
│   ┌──────────────────────────────▼─────────────────────────────────┐    │
│   │  INTELLIGENCE OUTPUT TIER                                       │    │
│   │  Learning Recommendation Manager → Learning Analytics Manager  │    │
│   │  Learning Archive Manager → Learning Health Manager            │    │
│   └─────────────────────────────┬──────────────────────────────────┘    │
│                                  │                                        │
└──────────────────────────────────┼───────────────────────────────────────┘
                                    │  Intelligence Updates
                        ┌───────────┴────────────────────────┐
                        │                                      │
          ┌─────────────▼────────────┐   ┌────────────────────▼────────────┐
          │  MetaLearning (Layer 3)   │   │  StrategyLab (Layer 5)          │
          │  Weight adjustments       │   │  Strategy improvements          │
          └──────────────────────────┘   └─────────────────────────────────┘
                        │
          ┌─────────────▼────────────┐
          │  ControlTower (Layer 17)  │
          │  Telemetry · Alerts       │
          └──────────────────────────┘
`

---

## TABLE OF CONTENTS

| Section | Title |
|---|---|
| Part I | Learning Philosophy and Definitional Framework |
| Part II | Learning Taxonomy |
| Part III | Core Component Architecture |
| Part IV | Learning Lifecycle |
| Part V | Learning Services |
| Part VI | Learning Pipelines |
| Part VII | Learning Quality Framework |
| Part VIII | Learning Governance |
| Part IX | Learning Constitution |
| Part X | Learning Readiness Checklist |
| Supplement A | Learning Taxonomy Reference |
| Supplement B | Pattern Catalogue |
| Supplement C | Feedback Models |
| Supplement D | Knowledge Evolution Examples |
| Supplement E | Bias and Drift Examples |
| Supplement F | Anti-Patterns |
| Supplement G | Operational Runbook |
| Supplement H | Glossary and Governing Design Records |
| Appendix | Worked Learning Examples |
| Document Summary | Metrics · Compliance · Ratification |

---

## PART I — LEARNING PHILOSOPHY AND DEFINITIONAL FRAMEWORK

### I.1 What Is Learning?

Learning is the sustained, systematic process by which an intelligent system converts experience into durable knowledge that improves future performance.

Learning is not data collection. It is not pattern matching. It is not configuration change.

Learning is the transformation of raw experience into structured, validated, actionable intelligence that is retained across sessions, across market regimes, across strategy generations, and across system restarts.

Without learning, an intelligent system is merely reactive — executing the same logic regardless of what history has revealed. With learning, the system evolves: its mistakes become lessons; its successes become replicable patterns; its accumulated experience becomes a strategic asset.

In the IIOS, learning operates across 17 layers. Every Observation, every piece of Evidence, every Hypothesis, every Decision, every Execution, every Fill, every Outcome, and every Feedback signal is a potential learning event. The Learning Engine is the mechanism that transforms this continuous stream of system experience into durable improvements across all layers.

---

### I.2 Why Learning Exists in IIOS

The investment environment is non-stationary. Market regimes change. Correlations break. Strategies that were profitable in a trending market become losses in a ranging market. Companies change their fundamentals. Macro policies shift. Liquidity patterns evolve.

An IIOS without learning would degrade over time. Strategies calibrated on historical data would drift from reality. Models trained on past regimes would misfire in new regimes. Repeated errors would be repeated indefinitely.

The Learning Engine exists for six fundamental reasons:

1. **Regime adaptation.** The market changes; the system must learn to recognise new regimes and weight strategies accordingly.
2. **Error elimination.** Mistakes must be recorded, analysed, and prevented from recurring.
3. **Pattern capitalisation.** Recurring market patterns, once discovered and validated, become structural edges.
4. **Model calibration.** All quantitative models in the system drift over time; learning re-calibrates them.
5. **Confidence accuracy.** The system's confidence scores must track actual outcomes; learning corrects confidence drift.
6. **Strategic evolution.** Strategies that stop working must be retired; new strategies must be evaluated and promoted based on demonstrated performance.

---

### I.3 The Definitional Ladder

The following concepts form a hierarchy from raw signal to wisdom. Understanding the distinctions is essential to understanding what the Learning Engine does and does not do.

**Observation:** The raw, unvalidated perception of a market or system event. An observation has no quality attribution; it has not been checked for accuracy. The Observation Engine (Layer — referenced in prior documents) generates observations; the Learning Engine processes their outcomes to learn whether certain observation types are consistently predictive.

**Evidence:** A validated, context-tagged observation. Evidence has been checked for reliability; it carries confidence weight. The Evidence Engine produces evidence. The Learning Engine learns which evidence signals have the highest predictive value over time.

**Hypothesis:** A conditional proposition about market behaviour, generated by the Hypothesis Engine. The Learning Engine tracks whether hypotheses that were activated subsequently proved correct, enabling calibration of hypothesis confidence.

**Reasoning:** The structured inference chain that produces a recommendation. The Reasoning Engine builds reasoning chains. The Learning Engine analyses which reasoning patterns correlate with successful outcomes and which correlate with failures.

**Knowledge:** The structured, validated, persistent set of facts, patterns, and relationships that the system accepts as true. Knowledge is the current state of the system's intelligence. Learning is the process that updates this state.

**Learning:** The transformation process. Learning converts observations, evidence, outcomes, and feedback into updates to the knowledge base, model parameters, strategy weights, and behavioral rules.

**Experience:** The accumulated history of all actions, outcomes, errors, and successes across all sessions. Experience is the raw material of learning. An experience that is not analysed produces no improvement.

**Memory:** The storage of experience in structured form. In IIOS, memory is distributed: the Learning Registry holds recent learning records; the Learning Archive holds permanent history; the Knowledge Engine holds the validated knowledge base.

**Pattern:** A discovered regularity in experience. A pattern is not a single observation — it is a recurring structure observed across multiple independent instances with statistical significance. Patterns are the primary output of the Pattern Discovery Engine.

**Rule:** An explicit behavioral constraint derived from a validated pattern. A rule says: "When condition X is observed, action Y produces outcome Z with probability P." Rules are extracted from patterns; they are the operationalised form of pattern knowledge.

**Model:** A parameterised function that maps inputs to outputs. Models are the quantitative substrate of intelligence in IIOS: strategy models, confidence models, regime models, risk models. Learning calibrates and re-calibrates model parameters.

**Feedback:** A signal that evaluates the quality of a past action. Feedback in IIOS comes from trade outcomes (PNL), execution quality (EQS), strategy performance (win rate), and human operators. Feedback is the richest learning signal because it directly links action to consequence.

**Adaptation:** A behavioral change made in response to new knowledge. Adaptation is the application of learning; learning without adaptation produces no improvement. In IIOS, adaptation takes the form of strategy weight changes, model parameter updates, rule modifications, and risk limit adjustments.

**Optimization:** The systematic tuning of parameters toward an objective function. Optimization is a specific type of learning — it requires a defined metric (e.g., Sharpe ratio, win rate) and adjusts parameters to improve it. Optimization without validation is dangerous: it can overfit to historical data.

**Improvement:** A measurable, validated increase in system performance. Improvement is the demonstrable outcome of learning. Without measurement, learning cannot confirm improvement.

**Understanding:** Deep causal knowledge — not just correlation, but mechanism. Understanding asks not just "what happened?" but "why did it happen?" The Learning Engine attempts to build understanding by tracking causal chains across multiple events.

**Wisdom:** The judgment to know when to apply knowledge, when to discard it, and when to override it. Wisdom is the meta-level of intelligence: it emerges from accumulated understanding. In IIOS, wisdom is partially encoded in governance rules (what the system will never do, regardless of what learning suggests).

---

### I.4 Learning Types in IIOS

**Explicit Learning:** Structured extraction of knowledge from labeled outcomes. Example: after a strategy trade closes, the system records the entry reasoning, the decision confidence score, and the actual PNL. These labeled records are used to train and recalibrate confidence models. Explicit learning is precise but requires labeled data.

**Implicit Learning:** Passive extraction of patterns from unlabeled behavioral data. Example: the system discovers that a specific combination of technical indicators consistently precedes a breakout — not because anyone told it to look for this, but because the Pattern Discovery Engine found the correlation in historical trade data. Implicit learning can discover non-obvious patterns but requires validation.

**Incremental Learning:** Building on existing knowledge without catastrophic forgetting. In IIOS, strategies evolved over time carry forward their historical performance data. A new regime observation does not erase prior regime knowledge; it adds to it with appropriate time-weighting.

**Continuous Learning:** Learning that never stops. The Learning Engine runs continuously during trading hours and between sessions. Every fill event, every outcome, every error is immediately processed for learning potential. There is no batch learning window that requires a session restart.

**Supervised Learning (IIOS context):** Learning from outcome-labeled records. When a trade closes at a profit (positive label) or loss (negative label), all the decision factors that led to that trade become training data for improving future confidence scoring. This is supervision by market outcome.

**Unsupervised Learning (IIOS context):** Learning structure from unlabeled patterns. The Pattern Discovery Engine scans execution histories, regime histories, and market data histories for recurring structures without predefined labels. Clusters of similar-performing setups are discovered automatically.

**Reinforcement Learning (IIOS context):** Learning from reward signals. In IIOS, the reward signal is the trade outcome (PNL, win/loss). Strategy weights are adjusted based on cumulative reward: strategies that consistently produce positive reward receive higher weights; those that produce consistent losses are downweighted or disabled. The Learning Engine implements a reward-weighted update mechanism.

**Meta Learning:** Learning how to learn. The Meta Learning layer (Layer 3) in IIOS is a dedicated meta-learning component. It learns which learning updates from the Learning Engine are most reliable, most transferable across regimes, and most durable over time. Meta learning improves the quality of the learning process itself.

**Organizational Learning:** System-wide adaptation that transcends individual component boundaries. When the Learning Engine discovers a recurring error pattern that spans multiple layers (e.g., a confidence calibration error in the Reasoning Engine that causes over-sizing in the CapitalRiskEngine leading to stop-loss breaches in the ExecutionEngine), the organisational learning response involves coordinated updates across all three layers — not just a single component fix.

---

### I.5 Why Learning Never Replaces Governance

Learning improves intelligence. It does not replace judgment or governance.

There are three categories of system behavior in IIOS that learning can never override:

1. **Constitutional rules.** The Learning Engine cannot modify the Kill Switch mechanism, the position sizing governance, or the execution constitutional rules. These are fixed by design. Even if learning were to suggest (incorrectly) that removing position limits would improve returns, governance prevents this.

2. **Human authority.** The Learning Engine cannot override human operator decisions. A human operator who disables a strategy, activates the Kill Switch, or vetoes a proposed knowledge update has absolute authority. The Learning Engine records the override as a learning event but does not contest it.

3. **Risk boundaries.** The Learning Engine cannot modify risk parameters beyond their governed ranges. Daily drawdown limits, VIX guards, and volatility thresholds are set by the RiskGuardian and CapitalRiskEngine governance frameworks. Learning can propose recalibrations; it cannot apply them without governance approval.

The relationship between learning and governance is cooperative, not adversarial. Learning provides the evidence; governance provides the judgment. The Learning Engine is a consultant, not a decision maker.

---

### I.6 The IIOS Learning Principles

| Principle | Description |
|---|---|
| LP-001 Evidence before update | No knowledge update is applied without validated evidence |
| LP-002 Validation before deployment | Every learning output is validated before being applied to any system component |
| LP-003 Governance approval for structural changes | Any learning that would change strategy weights, model parameters, or risk limits requires governance review |
| LP-004 Human authority is absolute | Human overrides of learning outputs are recorded and respected without contest |
| LP-005 Incremental, not disruptive | Learning updates are incremental; no single learning event triggers a complete system reset |
| LP-006 Explainability required | Every learning update must produce a traceable rationale linking the update to the evidence that drove it |
| LP-007 Reversibility | Every learning update can be rolled back to the prior state |
| LP-008 No learning under uncertainty | When evidence is insufficient or ambiguous, no update is made; the Learning Engine waits for more data |
| LP-009 Session independence | Learning accumulated in one session is valid in subsequent sessions; learning survives restarts |
| LP-010 Preservation of history | All learning records, including superseded knowledge and retired patterns, are permanently archived |

---

## PART II — LEARNING TAXONOMY

### II.1 Overview

The IIOS Learning Taxonomy classifies all learning activities by the domain from which experience originates. Each category has a distinct source, distinct signal types, distinct pattern classes, and distinct update targets.

Learning types are not mutually exclusive. A single trade outcome may generate learning across multiple categories simultaneously: the execution quality informs Execution Learning; the fill price relative to the decision confidence informs Decision Learning; the market regime at the time of the trade informs Market Learning; the strategy that generated the signal informs Strategy Learning.

The taxonomy has 21 categories. Each is defined by its **source domain**, **primary signal**, **primary output**, and **update target**.

---

### II.2 Learning Type LT-01: Observation Learning

**Source domain:** Observation Engine (raw market perceptions)
**Primary signal:** Observation accuracy score — did the observation correctly describe the market event?
**Primary output:** Observation reliability weight per observation type and source
**Update target:** Observation Engine source weights; evidence confidence priors
**Description:** Every observation generated by the Observation Engine is compared against subsequent confirmed market data. Was the perceived event actually present? Was the magnitude accurate? Over time, some observation sources prove consistently accurate (high weight); others prove noisy (downweighted). Observation Learning produces the reliability calibration that the Evidence Engine uses when assessing incoming observations.

---

### II.3 Learning Type LT-02: Evidence Learning

**Source domain:** Evidence Engine (validated, context-tagged observations)
**Primary signal:** Evidence predictive value — how well did this evidence predict the subsequent event?
**Primary output:** Evidence confidence multipliers per evidence type and market regime
**Update target:** Evidence Engine confidence scoring; Hypothesis Engine priors
**Description:** Evidence is evaluated not only for accuracy but for predictive power. High-confidence evidence that correctly predicted a market move increases the confidence prior for that evidence type. Evidence that consistently failed to predict correctly despite high confidence is flagged for recalibration. Evidence Learning prevents confidence inflation.

---

### II.4 Learning Type LT-03: Hypothesis Learning

**Source domain:** Hypothesis Engine (conditional propositions about market behaviour)
**Primary signal:** Hypothesis validation rate — fraction of hypotheses that were subsequently confirmed by market data
**Primary output:** Hypothesis confidence calibration curves per hypothesis type and regime
**Update target:** Hypothesis Engine baseline confidence; hypothesis generation frequency
**Description:** Hypotheses are tracked from generation through market confirmation or refutation. A hypothesis about an imminent breakout is either confirmed (price breaks the level) or refuted (price reverts). The Learning Engine accumulates these outcomes and calibrates the confidence score assigned to each hypothesis type.

---

### II.5 Learning Type LT-04: Reasoning Learning

**Source domain:** Reasoning Engine (inference chains, analytical conclusions)
**Primary signal:** Reasoning quality score — did the reasoning chain lead to a correct conclusion?
**Primary output:** Reasoning pattern quality scores; weight adjustments per reasoning type
**Update target:** Reasoning Engine chain weights; inference rules
**Description:** The Reasoning Engine constructs inference chains. Each reasoning chain has an outcome: the decision it supported either led to a profitable trade or a loss. Reasoning Learning tracks reasoning chain quality over time, identifying which reasoning patterns reliably precede good outcomes and which reliably precede poor outcomes.

---

### II.6 Learning Type LT-05: Decision Learning

**Source domain:** Decision Engine (COMMITTED Decision Packages)
**Primary signal:** Decision outcome — did the decision lead to a profitable trade?
**Primary output:** Decision confidence calibration; action-type success rates by regime
**Update target:** Decision Engine confidence thresholds; action type selection preferences
**Description:** Every committed decision has an eventual outcome: it was either profitable, breakeven, or a loss. Decision Learning tracks the correlation between decision confidence score (DCS) and actual outcome. If decisions with DCS 0.75-0.85 are consistently producing losses, the calibration of the DCS model is wrong and must be corrected. Decision Learning is the primary feedback mechanism for the Decision Engine.

---

### II.7 Learning Type LT-06: Execution Learning

**Source domain:** Execution Engine (Order lifecycle, fills, EQS)
**Primary signal:** Execution Quality Score (EQS) per execution type, instrument, time of day
**Primary output:** Execution parameter calibration (slippage priors, latency benchmarks, order type preferences)
**Update target:** Execution Engine order type selection; slippage parameters; broker routing preferences
**Description:** Execution Learning analyses execution quality data to improve future execution. Does MARKET order execution in the first 10 minutes after market open produce worse slippage than LIMIT orders? Should the default TIF be IOC for certain instruments at certain times? Execution Learning answers these questions by accumulating EQS data and extracting calibration improvements.

---

### II.8 Learning Type LT-07: Outcome Learning

**Source domain:** TradeMonitoring (Layer 12) and closed trade records
**Primary signal:** Realised PNL, maximum adverse excursion, holding period, exit reason
**Primary output:** Outcome pattern library; regime-stratified outcome distributions
**Update target:** Risk parameter calibration; position sizing models; stop-loss level optimisation
**Description:** Outcome Learning analyses the full history of closed trades to extract patterns in outcomes. Were losses larger than stops implied? Were winning trades cut short by premature exits? What fraction of losses could have been avoided with a wider stop? Outcome Learning feeds directly into RiskControl and CapitalRiskEngine parameter calibration.

---

### II.9 Learning Type LT-08: Risk Learning

**Source domain:** RiskGuardian (Layer 9), RiskControl (Layer 7), CapitalRiskEngine (Layer 6)
**Primary signal:** Risk limit hits, Kill Switch activations, near-miss events, VIX threshold breaches
**Primary output:** Risk parameter calibration recommendations; regime-specific risk adjustments
**Update target:** Risk governance parameters (via governance approval); regime-specific risk thresholds
**Description:** Risk Learning analyses the history of risk events — limit hits, drawdowns, Kill Switch activations — to identify whether risk parameters are correctly calibrated. If daily drawdown Kill Switch activations cluster in specific market regimes, the regime-specific risk limits may need adjustment. Risk Learning produces calibration recommendations that require governance approval before being applied.

---

### II.10 Learning Type LT-09: Portfolio Learning

**Source domain:** PortfolioAllocation (Layer 7), Portfolio Updater (Layer 6)
**Primary signal:** Portfolio correlation evolution, sector concentration impact on returns, diversification benefit realised
**Primary output:** Portfolio construction calibration; correlation model updates; concentration limit recommendations
**Update target:** Portfolio allocation rules (via governance); correlation models
**Description:** Portfolio Learning tracks the evolving correlation structure of the portfolio and the demonstrated impact of diversification. If correlated positions consistently amplify losses during drawdowns, the correlation model used by PortfolioAllocation needs updating. If sector concentration limits are consistently binding on the best-performing trades, the limits may need governance review.

---

### II.11 Learning Type LT-10: Strategy Learning

**Source domain:** StrategyLab (Layer 5), all strategy signal records
**Primary signal:** Per-strategy win rate, Sharpe ratio, maximum drawdown, regime-stratified performance
**Primary output:** Strategy weight adjustments; strategy parameter recalibrations; retirement recommendations; promotion recommendations
**Update target:** MetaLearning strategy weights (Layer 3); StrategyLab evolution parameters
**Description:** Strategy Learning is the most operationally important learning type. It continuously tracks the performance of every active strategy across sessions and regimes. Strategies that are performing above their historical baseline receive increased weights. Strategies that have deteriorated below their promotion thresholds (WinRate >= 50%, Sharpe > 0.8, MaxDD < 15%) are flagged for demotion or retirement. Strategy Learning is the primary driver of the strategy evolution cycle.

---

### II.12 Learning Type LT-11: Behavioral Learning

**Source domain:** All engine activity logs, decision patterns, error logs
**Primary signal:** Recurring behavioral patterns — actions that are consistently preceded by specific conditions
**Primary output:** Behavioral rule library; anomaly pattern library
**Update target:** Behavioral rules across all relevant engines
**Description:** Behavioral Learning examines the system's own behavioral patterns — not market patterns, but IIOS action patterns. Does the system consistently over-trade during the first 30 minutes after market open? Does decision confidence systematically decline on Fridays? These behavioral patterns are discovered and recorded; governance decides whether to act on them.

---

### II.13 Learning Type LT-12: Market Learning

**Source domain:** MarketIntelligence (Layer 2), market data feeds
**Primary signal:** Regime classification accuracy; regime transition signals; liquidity event patterns
**Primary output:** Regime detection model calibration; liquidity pattern library
**Update target:** MarketIntelligence regime classification models; regime transition thresholds
**Description:** Market Learning improves the accuracy of regime detection. If the current regime classifier consistently misidentifies trending markets as ranging (causing strategy misweighting), Market Learning detects the miscalibration and proposes model updates.

---

### II.14 Learning Type LT-13: Macro Learning

**Source domain:** GlobalIntelligence (Layer 1), macro data feeds
**Primary signal:** Predictive accuracy of global macroeconomic indicators for subsequent NIFTY/BANKNIFTY performance
**Primary output:** Macro indicator weight calibration; cross-asset signal reliability scores
**Update target:** GlobalIntelligence indicator weights; macro signal confidence priors
**Description:** Macro Learning evaluates whether global signals (S&P futures, Nikkei, bond yields, FX rates) are being correctly weighted. If US overnight performance has become a less reliable predictor of Indian market opens (e.g., due to a decoupling period), Macro Learning detects the degradation and proposes weight reduction.

---

### II.15 Learning Type LT-14: Sector Learning

**Source domain:** MarketIntelligence sector analysis, sector performance history
**Primary signal:** Sector rotation patterns; sector-specific regime responses
**Primary output:** Sector weight calibration; sector rotation signal reliability
**Update target:** MarketIntelligence sector weights; sector rotation models
**Description:** Sector Learning tracks whether certain sectors consistently lead or lag market moves in specific regimes. If BANKING sector consistently outperforms the broader market in early BULL regimes, this becomes a sector rotation pattern that the Market Intelligence layer can exploit.

---

### II.16 Learning Type LT-15: Company Learning

**Source domain:** Equity scanner (OpportunityEngine Layer 4), instrument-specific performance history
**Primary signal:** Instrument-specific alpha signals; earnings reaction patterns; liquidity patterns
**Primary output:** Instrument-specific alpha signal calibration; instrument reliability scores
**Update target:** OpportunityEngine instrument scoring; instrument-specific execution parameters
**Description:** Company Learning tracks the performance of individual instruments in the IIOS universe. Does TATASTEEL consistently underperform the METALS sector during Q4? Is HDFC BANK more liquid at specific times of day? These instrument-specific patterns improve scanning, execution, and risk management.

---

### II.17 Learning Type LT-16: Cross-Market Learning

**Source domain:** All market data across Indian equity, derivatives, and global markets
**Primary signal:** Cross-market correlation patterns; lead-lag relationships
**Primary output:** Cross-market signal library; correlation stability scores
**Update target:** Global and market intelligence layers' cross-market models
**Description:** Cross-Market Learning discovers and tracks how different markets influence each other. The relationship between FII futures positions and subsequent index moves, or between VIX spikes and options premium behaviour, are examples of cross-market patterns the Learning Engine tracks and validates.

---

### II.18 Learning Type LT-17: Cross-Asset Learning

**Source domain:** Equity, derivatives, index futures, and macro data
**Primary signal:** Cross-asset correlation patterns; asset class rotation signals
**Primary output:** Cross-asset correlation model calibrations
**Update target:** Risk correlation models; portfolio construction models
**Description:** Cross-Asset Learning tracks how different asset classes (equity, futures, options) behave relative to each other across market regimes. In a RISK-OFF regime, equity long positions may correlate with futures short positions in unexpected ways. Cross-Asset Learning calibrates the models that govern this.

---

### II.19 Learning Type LT-18: AI Learning

**Source domain:** All AI component outputs (confidence scores, model predictions, agent debate records)
**Primary signal:** AI model prediction accuracy over time; confidence calibration drift
**Primary output:** AI model recalibration recommendations; agent weight adjustments
**Update target:** Confidence scoring models; debate agent weights
**Description:** AI Learning specifically tracks the performance of the AI components within IIOS — the confidence scoring models, the debate agents, the k-NN strategy predictor, the regime classifier. AI models drift over time; AI Learning detects this drift and proposes recalibrations.

---

### II.20 Learning Type LT-19: Human Feedback Learning

**Source domain:** Human operator actions, overrides, Telegram commands, manual interventions
**Primary signal:** Human override patterns; human-initiated corrections; operator annotations
**Primary output:** Human feedback pattern library; governance calibration signals
**Update target:** System behavior where human overrides are repeatedly necessary (suggests automation improvement opportunities)
**Description:** Human Feedback Learning records every human override and intervention. If an operator consistently overrides a particular strategy decision, this reveals that the strategy's confidence calibration is wrong for that operator's judgment. Human feedback is the highest-quality learning signal because it carries explicit human judgment.

---

### II.21 Learning Type LT-20: Meta Learning

**Source domain:** The Learning Engine's own learning records — which learning updates proved valuable?
**Primary signal:** Learning update impact scores — did this update actually improve performance?
**Primary output:** Learning priority calibration; learning rate adjustments; learning reliability scores
**Update target:** Learning Engine's own update weights and validation thresholds
**Description:** Meta Learning evaluates the Learning Engine's own effectiveness. Did the confidence recalibration applied last week actually improve decision accuracy this week? Did the strategy weight adjustment produce the expected performance improvement? Meta Learning closes the loop on the Learning Engine's own performance.

---

### II.22 Learning Type LT-21: Error Learning

**Source domain:** Error logs, exception logs, anomaly logs across all 17 IIOS layers
**Primary signal:** Error recurrence rate; error clustering by condition, time, regime, component
**Primary output:** Error pattern library; recurring error flags; root cause hypotheses
**Update target:** Error prevention rules; component behavior adjustments
**Description:** Error Learning tracks every system error and anomaly. It looks for recurrence: an error that happens once may be a random event; an error that clusters under specific conditions is a pattern. Error Learning produces root cause hypotheses and prevention rules that are validated before deployment.

---

### II.23 Learning Type Summary Table

| Code | Name | Source | Primary Output | Update Target |
|---|---|---|---|---|
| LT-01 | Observation Learning | Observation Engine | Source reliability weights | Evidence confidence priors |
| LT-02 | Evidence Learning | Evidence Engine | Confidence multipliers | Evidence scoring |
| LT-03 | Hypothesis Learning | Hypothesis Engine | Confidence calibration | Hypothesis priors |
| LT-04 | Reasoning Learning | Reasoning Engine | Reasoning quality scores | Inference chain weights |
| LT-05 | Decision Learning | Decision Engine | DCS calibration | Decision thresholds |
| LT-06 | Execution Learning | Execution Engine | Execution parameter calibration | Slippage / routing |
| LT-07 | Outcome Learning | TradeMonitoring | Outcome pattern library | Risk parameters |
| LT-08 | Risk Learning | RiskGuardian | Risk parameter calibration | Risk thresholds (via governance) |
| LT-09 | Portfolio Learning | PortfolioAllocation | Correlation model updates | Allocation rules |
| LT-10 | Strategy Learning | StrategyLab | Strategy weight adjustments | MetaLearning weights |
| LT-11 | Behavioral Learning | All activity logs | Behavioral rule library | System behavior rules |
| LT-12 | Market Learning | MarketIntelligence | Regime model calibration | Regime classification |
| LT-13 | Macro Learning | GlobalIntelligence | Macro indicator weights | Global intelligence |
| LT-14 | Sector Learning | MarketIntelligence | Sector weight calibration | Sector rotation models |
| LT-15 | Company Learning | OpportunityEngine | Instrument alpha calibration | Instrument scoring |
| LT-16 | Cross-Market Learning | All market data | Cross-market signal library | Market intelligence |
| LT-17 | Cross-Asset Learning | Multi-asset data | Cross-asset correlation calibration | Risk models |
| LT-18 | AI Learning | All AI components | AI model recalibration | Confidence models |
| LT-19 | Human Feedback Learning | Operator actions | Human feedback pattern library | Automation calibration |
| LT-20 | Meta Learning | Learning Engine self-assessment | Learning priority calibration | Learning Engine |
| LT-21 | Error Learning | All error logs | Error pattern library | Prevention rules |

---

## PART III — CORE COMPONENT ARCHITECTURE

### III.1 Component Overview

The Learning Engine contains 21 components organised into four tiers. Every component has a defined purpose, a bounded set of responsibilities, and a set of interactions with other components. No component performs functions outside its definition.

`
TIER 1: COLLECTION AND REGISTRY
  LC-01  Learning Registry
  LC-02  Learning Catalog
  LC-03  Learning Collector
  LC-04  Learning Processor

TIER 2: DISCOVERY AND ANALYSIS
  LC-05  Pattern Discovery Engine
  LC-06  Knowledge Updater
  LC-07  Model Improvement Manager
  LC-08  Feedback Manager
  LC-09  Outcome Analyzer
  LC-10  Performance Analyzer
  LC-11  Error Analyzer
  LC-12  Bias Detector
  LC-13  Drift Detector

TIER 3: VALIDATION AND GOVERNANCE
  LC-14  Learning Validation Manager
  LC-15  Learning Governance Manager
  LC-16  Learning Audit Manager

TIER 4: OPERATIONS AND OUTPUT
  LC-17  Learning Archive Manager
  LC-18  Learning Health Manager
  LC-19  Learning Analytics Manager
  LC-20  Learning Recommendation Manager
  LC-21  Learning Catalog (dynamic extension)
`

---

### III.2 LC-01: Learning Registry

**Purpose:** The operational store of all active and recent learning records. The Learning Registry is the central indexing system for learning events that are currently being processed or that have not yet been archived.

**Responsibilities:**
- Maintain a keyed, queryable index of all learning records by type (LT-01 through LT-21), source, date, and status
- Assign unique Learning Record IDs: LRN-{TYPE}-{DATE}-{SEQ:08d}
- Track learning record lifecycle status: COLLECTED, PROCESSING, VALIDATED, APPROVED, DEPLOYED, ARCHIVED, REJECTED, SUPERSEDED
- Provide fast lookup for deduplication: detect duplicate learning inputs before processing
- Expose learning record count and status distribution to the Learning Health Manager

**Inputs:** Learning records from Learning Collector; status updates from all processing components

**Outputs:** Learning records to Learning Processor; registry state to Learning Health Manager; deduplication signals to Learning Collector

**Dependencies:** Storage Layer (SQLite); Learning Collector

**Interactions:** Central hub for all components that read or write learning record status

**Failure Modes:** Registry write failure (disk full, I/O error); stale registry (records not advancing in lifecycle); memory overflow from large registry

**Recovery Strategy:** On registry write failure: emit alert; retry with exponential back-off (3 attempts); if all fail: switch to read-only mode and hold new collection. On stale record detection: escalate to Learning Governance Manager.

**Monitoring:** Registry size; stale record count; write latency; lookup latency

**Engineering Notes:** The Learning Registry is append-friendly and uses status-field updates rather than record mutations. Historical status transitions are preserved for full lifecycle auditability.

---

### III.3 LC-02: Learning Catalog

**Purpose:** The structured classification index for all learning knowledge. The Learning Catalog organises validated learning outputs by type, domain, regime, confidence, and applicability.

**Responsibilities:**
- Maintain taxonomy of all validated learning outputs: patterns, calibration updates, model improvements, feedback signals
- Tag all catalog entries with: learning type (LT-01 through LT-21), source component, originating regime, confidence score, validity window, version
- Support queries: "What patterns are validated for TRENDING regimes?", "Which strategy calibrations were approved this month?"
- Track catalog entry lifecycle: ACTIVE, SUPERSEDED, RETIRED, EXPERIMENTAL
- Version control for catalog entries: every update creates a new version; prior version is archived, not deleted

**Inputs:** Validated learning outputs from Learning Validation Manager; retirement signals from Learning Governance Manager

**Outputs:** Catalog entries to Knowledge Updater; catalog queries from all Learning Engine components

**Dependencies:** Learning Registry; Learning Validation Manager

**Failure Modes:** Catalog inconsistency (active and superseded entries for same knowledge); version conflict; catalog query timeout

**Recovery Strategy:** On inconsistency: flag affected entries SUSPECT; quarantine; escalate to Learning Governance Manager for manual resolution.

**Engineering Notes:** Catalog entries are immutable after approval. Updates create new versions; old versions are kept with SUPERSEDED status for historical auditability.

---

### III.4 LC-03: Learning Collector

**Purpose:** The ingestion boundary of the Learning Engine. The Learning Collector receives learning signals from all 17 IIOS layers and transforms them into structured Learning Records for processing.

**Responsibilities:**
- Maintain inbound connections to all IIOS layer event streams: fills, outcomes, errors, regime changes, strategy performance updates, human overrides
- Transform raw events into typed Learning Records (classified by LT-01 through LT-21)
- Apply deduplication: detect and discard duplicate signals before registry entry
- Apply rate limiting: prevent learning signal floods from overwhelming the Processing pipeline
- Record collection metadata: source layer, signal type, timestamp, session ID, signal quality score
- Support batch collection (between sessions) and real-time collection (during sessions)

**Inputs:** Event streams from all 17 IIOS layers; human feedback from Telegram operator interface

**Outputs:** Structured Learning Records to Learning Registry; collection metrics to Learning Health Manager

**Dependencies:** EventBus (Layer 17 ControlTower); all IIOS layers (via EventBus subscriptions); Learning Registry

**Failure Modes:** Event stream disconnection; deduplication failure (duplicate records enter registry); collection rate overwhelming registry

**Recovery Strategy:** On event stream disconnection: log gap; on reconnection, replay missed events from EventBus buffer (configurable lookback window). On rate overflow: apply priority-based shedding (keep OUTCOME and ERROR signals; shed lower-priority MARKET signals under extreme load).

**Monitoring:** Collection rate per signal type; deduplication rate; dropped signal count; event stream health per source layer

**Engineering Notes:** The Learning Collector is the most latency-sensitive component during trading hours. It must not block the EventBus. All collection operations are non-blocking; records are enqueued for async processing.

---

### III.5 LC-04: Learning Processor

**Purpose:** The transformation pipeline that converts raw Learning Records into structured, analyzable learning inputs ready for pattern discovery and knowledge update.

**Responsibilities:**
- Apply context enrichment to each Learning Record: add regime context, session context, market condition context at time of event
- Apply quality scoring: assign initial quality score to each Learning Record based on data completeness, source reliability, and signal strength
- Route Learning Records to the appropriate analysis components based on learning type (LT classification)
- Apply temporal alignment: ensure Learning Records from different sources are aligned to a consistent event timeline
- Track processing latency per learning type; emit alerts if processing falls behind

**Inputs:** Learning Records from Learning Registry; context data from MarketIntelligence and GlobalIntelligence

**Outputs:** Enriched, context-tagged, quality-scored Learning Records routed to: Pattern Discovery Engine, Outcome Analyzer, Error Analyzer, Feedback Manager (by learning type)

**Dependencies:** Learning Registry; MarketIntelligence (Layer 2) for regime context; GlobalIntelligence (Layer 1) for macro context

**Failure Modes:** Context enrichment failure (regime data unavailable); routing failure (unknown learning type); processing latency buildup

**Recovery Strategy:** On context enrichment failure: process record with partial context; flag as CONTEXT_PARTIAL for later enrichment when context becomes available. On routing failure: route to Learning Governance Manager for manual classification.

**Engineering Notes:** The Learning Processor applies regime tagging to all records. This is critical: a pattern discovered without regime context is less actionable than one tagged "TRENDING_BULL, Q1". Regime context transforms generic patterns into applicable rules.

---

### III.6 LC-05: Pattern Discovery Engine

**Purpose:** The core analytical engine of the Learning System. The Pattern Discovery Engine scans accumulated learning records to discover recurring, statistically significant patterns across all learning type domains.

**Responsibilities:**
- Implement pattern detection algorithms for: temporal patterns (what happens before/after an event), conditional patterns (what conditions precede an outcome), correlation patterns (what variables move together), regime-specific patterns (patterns that only hold in specific regimes)
- Apply statistical significance testing to all candidate patterns: minimum occurrence count, confidence interval, effect size threshold
- Classify discovered patterns by: pattern type, domain, regime applicability, confidence score, expected improvement impact
- Manage pattern lifecycle: CANDIDATE, VALIDATED, ACTIVE, SUPERSEDED, RETIRED
- Maintain pattern deduplication: avoid adding patterns that are already present in the catalog with equivalent semantics
- Support incremental pattern updates: strengthen or weaken existing patterns as new evidence accumulates

**Inputs:** Enriched Learning Records from Learning Processor; existing Pattern Catalog from Learning Catalog; regime context from MarketIntelligence

**Outputs:** Candidate patterns to Learning Validation Manager; pattern updates to Learning Catalog; pattern metrics to Learning Analytics Manager

**Dependencies:** Learning Processor; Learning Catalog; Learning Validation Manager

**Failure Modes:** Pattern explosion (too many low-quality candidate patterns); statistical overfitting; regime confusion (pattern assigned wrong regime)

**Recovery Strategy:** Apply minimum occurrence count threshold (minimum 10 instances before pattern candidacy). Apply effect size filter: minimum 5% improvement in target metric. Apply regime overlap check: patterns must be validated within a single regime before multi-regime application.

**Monitoring:** Candidate pattern count; validation rate; pattern quality distribution; pattern retirement rate

**Engineering Notes:** The Pattern Discovery Engine is the most computationally intensive component. It runs in a background thread during trading hours and in a full batch mode between sessions. During trading hours, it operates on a sliding window of recent records; between sessions, it processes the full history for the current strategy generation.

---

### III.7 LC-06: Knowledge Updater

**Purpose:** The interface between the Learning Engine and the IIOS knowledge base. The Knowledge Updater applies validated, approved learning outputs to the relevant knowledge structures across all layers.

**Responsibilities:**
- Receive approved learning outputs from Learning Governance Manager
- Translate approved learning outputs into specific updates to: strategy weights (MetaLearning Layer 3), model parameters (confidence models, regime models, risk models), inference rules (Reasoning Engine), observation weights (Evidence Engine)
- Apply updates incrementally: never replace a model wholesale; update parameters within configured ranges
- Maintain update history: every knowledge update is versioned and logged
- Support rollback: every knowledge update can be reversed to the prior state
- Coordinate with target layer components to ensure updates are applied consistently

**Inputs:** Approved learning outputs from Learning Governance Manager; current knowledge state from Knowledge Engine

**Outputs:** Knowledge updates applied to target layer components; update history to Learning Audit Manager; rollback signals when requested

**Dependencies:** Learning Governance Manager; MetaLearning (Layer 3); StrategyLab (Layer 5); Evidence Engine; Reasoning Engine; Knowledge Engine

**Failure Modes:** Update application failure (target component unavailable); parameter drift beyond allowed range; rollback failure

**Recovery Strategy:** On update application failure: hold the update in PENDING_APPLY status; retry on next cycle; escalate if 3 retries fail. On parameter drift: halt updates for that parameter dimension; alert Learning Governance Manager.

**Monitoring:** Update application latency; update success rate; rollback count; parameter range compliance

**Engineering Notes:** All updates are bounded. The Knowledge Updater enforces hard limits on parameter changes per update cycle. A single learning event cannot shift a model parameter by more than a configured maximum step (e.g., strategy weight: max delta 5% per cycle; confidence prior: max delta 0.05 per cycle). This prevents learning instability.

---

### III.8 LC-07: Model Improvement Manager

**Purpose:** Manages the systematic improvement of quantitative models within IIOS. The Model Improvement Manager identifies models that have drifted from their optimal parameters and coordinates the recalibration process.

**Responsibilities:**
- Monitor prediction accuracy of all active quantitative models: confidence scoring models, regime detection models, risk models, strategy performance models
- Detect model drift: significant degradation in prediction accuracy over a rolling window
- Propose recalibration: generate recalibration recommendations with supporting evidence
- Coordinate walk-forward validation of proposed recalibrations
- Track model improvement lifecycle: MONITORING, DRIFT_DETECTED, RECALIBRATION_PROPOSED, VALIDATING, APPROVED, DEPLOYED
- Maintain model performance history: full history of all models, all parameter versions, all performance metrics

**Inputs:** Model prediction accuracy data from all model-using components; drift signals from Drift Detector; validation results from Learning Validation Manager

**Outputs:** Recalibration proposals to Learning Governance Manager; model performance reports to Learning Analytics Manager; model history to Learning Archive Manager

**Dependencies:** Drift Detector; Learning Validation Manager; Learning Governance Manager; Knowledge Updater (for approved recalibrations)

**Failure Modes:** Drift false positive (recalibration proposed when model is actually performing well); recalibration overfitting (new parameters overfit to recent data); rollback failure after bad deployment

**Recovery Strategy:** Apply minimum drift significance threshold before proposing recalibration (drift must exceed 2 standard deviations from historical performance baseline). Require walk-forward validation before any recalibration is approved.

**Engineering Notes:** The Model Improvement Manager does not itself change any parameters. It produces proposals. The governance chain (Learning Validation Manager → Learning Governance Manager → Knowledge Updater) applies the change. This separation prevents unilateral model modifications.

---

### III.9 LC-08: Feedback Manager

**Purpose:** Manages all feedback signals flowing into the Learning Engine, ensuring they are correctly attributed, weighted, and incorporated into the learning process.

**Responsibilities:**
- Collect feedback signals from: trade outcomes (PNL feedback), execution quality (EQS feedback), strategy performance (win rate feedback), human operators (override feedback, annotation feedback), and system error events (error feedback)
- Attribute each feedback signal to its originating decision, reasoning chain, hypothesis, and strategy
- Apply feedback weighting: recent feedback is weighted more than old feedback; high-confidence outcomes are weighted more than low-confidence outcomes; human feedback is weighted highest
- Manage feedback decay: old feedback signals are gradually downweighted over time
- Detect feedback paradoxes: conflicting feedback signals about the same source event
- Produce feedback summaries per learning type and per target component

**Inputs:** Trade outcomes from TradeMonitoring (Layer 12); EQS data from ExecutionEngine (Layer 11); strategy performance from StrategyPerformanceTracker; human feedback from operator interface; error events from Error Analyzer

**Outputs:** Weighted feedback records to Pattern Discovery Engine; feedback attribution to Learning Processor; feedback paradox alerts to Learning Governance Manager

**Dependencies:** TradeMonitoring; ExecutionEngine; StrategyPerformanceTracker; Learning Processor; Learning Governance Manager

**Failure Modes:** Attribution failure (feedback cannot be linked to source decision); feedback decay miscalibration; feedback paradox unresolved

**Recovery Strategy:** On attribution failure: store feedback as UNATTRIBUTED; attempt re-attribution when more context becomes available; discard after 30 days if still unattributed.

**Engineering Notes:** Feedback attribution is the most important function of the Feedback Manager. Unattributed feedback is nearly worthless: learning requires knowing which specific decision, reasoning chain, or strategy generated the feedback. The Feedback Manager maintains a 90-day attribution window for delayed outcomes.

---

### III.10 LC-09: Outcome Analyzer

**Purpose:** Systematically analyses the outcomes of all closed trades to extract actionable improvement signals.

**Responsibilities:**
- Receive closed trade records from TradeMonitoring
- Analyse outcome characteristics: PNL, holding period, exit reason, maximum adverse excursion (MAE), maximum favorable excursion (MFE), risk-reward realised vs planned
- Stratify outcome analysis by: strategy, regime, instrument class, time of day, session type, decision confidence tier
- Identify outcome patterns: consistent early exits (MFE >> final PNL), consistent oversized losses (MAE >> stop level), win rate degradation by regime
- Produce outcome pattern records for Pattern Discovery Engine
- Produce regime-stratified outcome distributions for risk calibration

**Inputs:** Closed trade records from TradeMonitoring; regime context from MarketIntelligence; execution data from ExecutionEngine

**Outputs:** Outcome pattern records to Pattern Discovery Engine; risk calibration signals to Learning Governance Manager (for risk parameter review); outcome reports to Learning Analytics Manager

**Dependencies:** TradeMonitoring (Layer 12); MarketIntelligence (Layer 2); ExecutionEngine (Layer 11)

**Failure Modes:** Incomplete trade records (missing entry/exit details); regime context unavailable for historical trades

**Recovery Strategy:** On incomplete records: flag as PARTIAL_OUTCOME; exclude from pattern analysis until complete; alert operator if incompleteness persists.

**Engineering Notes:** The Outcome Analyzer is the primary source of strategy performance feedback. Its output is the most operationally critical in the Learning Engine because strategy weight changes in MetaLearning are directly driven by outcome analysis.

---

### III.11 LC-10: Performance Analyzer

**Purpose:** Provides a systematic, multi-dimensional analysis of IIOS system performance to identify improvement opportunities across all layers.

**Responsibilities:**
- Aggregate performance metrics from all 17 IIOS layers: decision accuracy, execution quality, risk compliance, learning effectiveness
- Compute rolling performance baselines: 7-day, 30-day, 90-day rolling averages per metric
- Detect performance degradation: significant decline from baseline in any metric
- Identify performance improvement opportunities: metrics consistently below target
- Produce performance dashboards for: per-strategy performance, per-layer performance, per-regime performance, per-instrument performance
- Track performance attribution: which layer or component is most responsible for performance improvement or degradation

**Inputs:** Performance metrics from all IIOS layers; baseline data from Learning Archive Manager; outcome data from Outcome Analyzer

**Outputs:** Performance reports to Learning Analytics Manager; degradation alerts to Learning Governance Manager; improvement opportunity signals to Learning Recommendation Manager

**Dependencies:** All IIOS layers (via ControlTower telemetry); Learning Archive Manager; Outcome Analyzer; Learning Recommendation Manager

**Failure Modes:** Metric collection failure (layer not reporting); baseline data corruption; false degradation alert (statistical noise mistaken for trend)

**Recovery Strategy:** On metric collection failure: flag that layer as DATA_MISSING; exclude from performance calculations; alert operator.

**Engineering Notes:** Performance attribution is the hardest analytical challenge in the Performance Analyzer. Many performance changes have multi-factor causes. The Analyzer uses a variance decomposition approach: how much of the observed performance change can be attributed to regime change vs model drift vs execution quality vs strategy mix?

---

### III.12 LC-11: Error Analyzer

**Purpose:** Systematically analyses all system errors, anomalies, and exceptions to identify recurring patterns and root causes.

**Responsibilities:**
- Collect error events from all 17 IIOS layers via EventBus subscriptions
- Classify errors by: severity (CRITICAL, HIGH, MEDIUM, LOW), layer, component, error type, market condition at time of error
- Detect error recurrence: errors that appear in a pattern (cluster by time, condition, component)
- Perform root cause analysis: identify the chain of conditions that precedes recurring errors
- Track error resolution: did a proposed fix actually eliminate the error?
- Produce error pattern library: all validated recurring errors with their root cause hypotheses and prevention rules

**Inputs:** Error events from all IIOS layers; error resolution records from Learning Governance Manager; market condition context from MarketIntelligence

**Outputs:** Error patterns to Pattern Discovery Engine; root cause hypotheses to Learning Governance Manager; error reports to Learning Analytics Manager

**Dependencies:** EventBus (Layer 17); MarketIntelligence (Layer 2); Learning Governance Manager

**Failure Modes:** Error event loss (high-frequency error floods); root cause misattribution

**Recovery Strategy:** On error event flood: apply rate limiting; preserve CRITICAL and HIGH severity; shed LOW severity under load. On root cause misattribution: maintain multiple competing hypotheses; resolve by evidence accumulation.

---

### III.13 LC-12: Bias Detector

**Purpose:** Systematically identifies cognitive, statistical, and structural biases in IIOS decision-making, reasoning, and learning processes.

**Responsibilities:**
- Monitor for confirmation bias: does the system give disproportionate weight to evidence confirming existing beliefs?
- Monitor for recency bias: are recent events overweighted relative to historical patterns?
- Monitor for survivorship bias: are only successful strategies being analysed, ignoring failed ones?
- Monitor for anchoring bias: are initial confidence scores inappropriately sticky across multiple updates?
- Monitor for regime confusion bias: are patterns from one regime being applied incorrectly in another?
- Monitor for execution quality bias: are poorly-executed trades systematically biasing strategy performance assessment?
- Quantify detected biases with bias score metrics
- Produce bias mitigation recommendations for Learning Governance Manager

**Inputs:** Decision records, evidence records, reasoning chain records; learning update history; strategy performance history

**Outputs:** Bias detection reports to Learning Governance Manager; bias flags to Learning Validation Manager (to halt updates if bias is severe); bias metrics to Learning Analytics Manager

**Dependencies:** Learning Validation Manager; Learning Governance Manager; Learning Analytics Manager

**Failure Modes:** Bias false positive; bias blind spot (a bias exists but is not in the detection repertoire)

**Recovery Strategy:** On severe bias detection: flag all affected learning outputs as BIAS_SUSPECT; halt deployment until bias is investigated. Maintain quarterly bias detection audit to discover new bias types.

**Engineering Notes:** Bias detection is inherently incomplete: only known bias patterns can be detected. The Bias Detector must itself be monitored for bias in its detection logic. The quarterly bias audit is the mechanism for expanding the detection repertoire.

---

### III.14 LC-13: Drift Detector

**Purpose:** Detects when quantitative models, statistical patterns, or behavioral rules in the IIOS have drifted from their valid operating parameters.

**Responsibilities:**
- Monitor prediction error time series for all active quantitative models: statistical process control (control charts) per model
- Detect regime drift: when market characteristics have changed to the point that historical patterns no longer apply
- Detect data drift: when the statistical distribution of input features has changed significantly from the training distribution
- Detect concept drift: when the relationship between inputs and outputs has changed (the market structure has changed)
- Classify drift severity: DETECTED (early warning), SIGNIFICANT (action required), SEVERE (halt model)
- Produce drift reports and escalate to Model Improvement Manager and Learning Governance Manager

**Inputs:** Model prediction accuracy time series; market data statistical summaries; learning output effectiveness scores

**Outputs:** Drift alerts to Model Improvement Manager; drift severity signals to Learning Governance Manager; drift metrics to Learning Analytics Manager

**Dependencies:** Model Improvement Manager; Learning Governance Manager; MarketIntelligence (for regime drift context)

**Failure Modes:** Drift false positive (model flagged as drifted during unusual but valid market period); drift blind spot (slow drift below detection threshold)

**Recovery Strategy:** Apply minimum drift persistence threshold: drift must be detected in at least 3 consecutive monitoring cycles before escalation (prevents noise-driven false positives).

---

### III.15 LC-14: Learning Validation Manager

**Purpose:** Validates all candidate learning outputs before they are presented to Learning Governance for approval and deployment.

**Responsibilities:**
- Apply 5-stage validation pipeline to all candidate learning outputs: (1) Data Quality, (2) Statistical Significance, (3) Out-of-Sample Test, (4) Regime Stability, (5) Impact Assessment
- Maintain validation history: every validation attempt with all criteria scores and pass/fail results
- Apply validation circuit breakers: halt all validation processing if a systemic quality issue is detected
- Track validation pass rates per learning type and per originating component
- Produce validation reports for Learning Governance Manager

**Inputs:** Candidate learning outputs from Pattern Discovery Engine, Model Improvement Manager, Outcome Analyzer, Error Analyzer; validation criteria from Learning Governance Manager

**Outputs:** VALIDATED or REJECTED learning outputs to Learning Governance Manager; validation metrics to Learning Analytics Manager; circuit breaker alerts to Learning Health Manager

**Dependencies:** Pattern Discovery Engine; Model Improvement Manager; Learning Governance Manager

**Failure Modes:** Validation process failure (test infrastructure unavailable); overly strict validation (rejects valid learning); validation overfitting to validation data

**Recovery Strategy:** On validation infrastructure failure: hold all pending validations; emit alert; resume when infrastructure is restored. On persistent low pass rate (< 20% for a learning type): flag as LEARNING_TYPE_DEGRADED; escalate to governance.

---

### III.16 LC-15: Learning Governance Manager

**Purpose:** The approval and policy enforcement authority for the Learning Engine. The Learning Governance Manager decides which validated learning outputs are approved for deployment and ensures all learning operates within IIOS governance boundaries.

**Responsibilities:**
- Review all validated learning outputs from Learning Validation Manager
- Apply governance approval policies: which outputs can be auto-approved, which require human review
- Enforce learning governance boundaries: ensure no learning output violates constitutional rules or GDRs
- Maintain the governance approval queue with audit trail
- Escalate to human operators when: governance boundary is near, conflicting learning outputs exist, bias has been detected
- Coordinate rollbacks when deployed learning causes performance degradation
- Enforce retention and archiving policies for learning records

**Inputs:** Validated learning outputs from Learning Validation Manager; governance policies; human operator instructions; rollback requests from Knowledge Updater

**Outputs:** APPROVED or REJECTED disposition for each validated learning output; rollback authorisations; governance reports to Learning Audit Manager

**Dependencies:** Learning Validation Manager; Knowledge Updater; Learning Audit Manager; Human operator interface (Telegram)

**Failure Modes:** Governance backlog (approved outputs pile up waiting for deployment); conflicting approvals; human operator unavailable for required approvals

**Recovery Strategy:** On governance backlog: prioritise by learning impact score (highest impact reviewed first). On conflicting approvals: hold conflicting outputs; request human resolution.

---

### III.17 LC-16: Learning Audit Manager

**Purpose:** Maintains the immutable, hash-chain-linked audit log of all learning events, decisions, and updates.

**Responsibilities:**
- Write an audit event for every learning lifecycle state transition
- Maintain SHA-256 hash chain linking all audit events (identical security model to Execution Audit Manager)
- Support audit queries: "What was the knowledge state at date/time X?", "Which learning outputs were deployed this week?", "Who approved this update?"
- Verify hash chain integrity on startup and periodically during operation
- Produce compliance reports for governance review

**Inputs:** Learning lifecycle events from all Learning Engine components; governance decisions from Learning Governance Manager

**Outputs:** Audit records (append-only, hash-chained); compliance reports; integrity alerts

**Dependencies:** Storage Layer; all Learning Engine components; Learning Governance Manager

**Failure Modes:** Audit write failure; hash chain breach (tampering or corruption)

**Recovery Strategy:** On audit write failure: hold all learning updates; emit CRITICAL alert. On hash chain breach: halt all updates; escalate to security review.

**Engineering Notes:** The Learning Audit Manager follows the same security model as the Execution Audit Manager (IIOS-EXE-ENG-ARCH-001 Supplement L). Audit records are append-only, hash-chain-linked, and never truncated.

---

### III.18 LC-17: Learning Archive Manager

**Purpose:** Manages the permanent, compressed, queryable archive of all historical learning records, superseded knowledge versions, retired patterns, and closed learning cycles.

**Responsibilities:**
- Archive terminal-state learning records: DEPLOYED, REJECTED, SUPERSEDED, RETIRED
- Maintain queryable archive with indexes by: learning type, date, strategy, regime, component, quality score
- Support historical replay: reconstruct the state of the learning system at any past date for analysis
- Manage archive compression and storage efficiency
- Enforce retention policies: configurable retention per learning type (minimum 3 years for all types)

**Inputs:** Terminal-state learning records from Learning Registry; archive requests from Learning Governance Manager

**Outputs:** Archived records to SQLite + compressed files; historical query results; archive health metrics

**Dependencies:** Storage Layer; Learning Registry; Learning Governance Manager

**Failure Modes:** Archive write failure; archive corruption; archive query timeout on large history

**Recovery Strategy:** On write failure: emit alert; buffer records in memory; retry; escalate if buffer fills. Maintain archive integrity checksums.

---

### III.19 LC-18: Learning Health Manager

**Purpose:** Continuously monitors the health of all 21 Learning Engine components and reports the aggregate learning system health to ControlTower.

**Responsibilities:**
- Poll health status of all 21 components every 30 seconds
- Compute Learning System Health Score (LSHS): weighted average of all component health scores
- Detect component degradation or failure and trigger recovery procedures
- Emit health alerts via EventBus to ControlTower and Telegram
- Track learning throughput: records collected per hour, validated per hour, deployed per hour

**Inputs:** Health status polls from all 21 components; throughput metrics from Learning Collector and Learning Processor

**Outputs:** LSHS to ControlTower; health alerts via EventBus; health reports to Learning Analytics Manager

**Dependencies:** All 21 Learning Engine components; EventBus (Layer 17)

**Failure Modes:** Health monitor failure itself (the monitor crashes); health status false HEALTHY for degraded component

**Recovery Strategy:** Health Manager is the last component in the activation sequence; if it fails, emit alert before shutdown.

---

### III.20 LC-19: Learning Analytics Manager

**Purpose:** Provides session-level, cross-session, and historical analytics for the Learning Engine's own performance and effectiveness.

**Responsibilities:**
- Compute Learning Quality Score (LQS): the composite quality metric for the Learning Engine (analogous to EQS for Execution, DCS for Decision)
- Produce session analytics: patterns discovered, knowledge updates applied, feedback processed, errors analysed
- Track learning effectiveness over time: are deployed learning updates actually improving IIOS performance?
- Produce cross-strategy learning attribution: which strategies benefit most from learning?
- Generate learning trend reports for governance review

**Inputs:** Metrics from all Learning Engine components; IIOS performance metrics from PerformanceAnalytics (Layer 14)

**Outputs:** LQS per session; learning effectiveness reports; analytics summaries to ControlTower dashboard

**Dependencies:** All Learning Engine components; PerformanceAnalytics (Layer 14); ControlTower (Layer 17)

---

### III.21 LC-20: Learning Recommendation Manager

**Purpose:** Synthesises all learning signals into prioritised, actionable recommendations for human operators and system governance.

**Responsibilities:**
- Aggregate signals from: Performance Analyzer, Outcome Analyzer, Pattern Discovery Engine, Bias Detector, Drift Detector, Error Analyzer, Feedback Manager
- Produce prioritised recommendation list: ranked by expected improvement impact
- Classify recommendations by: action type (model recalibration, strategy demotion, parameter adjustment, governance review), urgency (IMMEDIATE, THIS_SESSION, THIS_WEEK, PLANNED), confidence (HIGH, MEDIUM, LOW)
- Deliver recommendations via: Telegram alerts (IMMEDIATE), dashboard panel (all), weekly summary (LOW/PLANNED)
- Track recommendation outcomes: were implemented recommendations effective?

**Inputs:** Signals from all Discovery tier components; performance data from Performance Analyzer

**Outputs:** Prioritised recommendations to Telegram operator interface and dashboard; recommendation history to Learning Archive Manager

**Dependencies:** Performance Analyzer; Outcome Analyzer; Pattern Discovery Engine; Bias Detector; Drift Detector; Error Analyzer; Telegram interface

**Engineering Notes:** The Learning Recommendation Manager does not apply any update itself. It is a communication component. Every recommendation it produces must pass through Learning Validation → Learning Governance before any knowledge update is applied.

---

## PART IV — LEARNING LIFECYCLE

### IV.1 Overview

The Learning Lifecycle defines the complete journey from raw experience collection through validated knowledge deployment. Every learning event in the IIOS follows this lifecycle. No knowledge update is applied without completing the mandatory stages.

The lifecycle has 13 stages, each with defined entry criteria, exit criteria, and responsible components.

---

### IV.2 Complete Lifecycle Stage Definitions

**Stage 1: EXPERIENCE COLLECTION**

Experience arrives at the Learning Collector from all 17 IIOS layers. Raw events include: trade fills, strategy outcomes, error events, human overrides, market regime changes, model prediction results. The Collector transforms these into structured Learning Records and submits them to the Learning Registry.

Entry criteria: Any system event matching a subscribed learning signal type.
Exit criteria: Learning Record created in registry with status COLLECTED.
Responsible component: Learning Collector, Learning Registry.

**Stage 2: VALIDATION**

The Learning Processor applies initial quality validation to each collected Learning Record. This validates that the record is complete, accurately attributed, and sourced from a reliable signal.

Entry criteria: Learning Record in COLLECTED status.
Exit criteria: Learning Record in PROCESSING status with quality score assigned; or REJECTED (poor quality).
Responsible component: Learning Processor.

**Stage 3: CONTEXT ENRICHMENT**

The Learning Processor enriches the Learning Record with market context: the regime at the time of the event, macro conditions, session context, instrument state. Context is essential for pattern discovery — a pattern without context is much less actionable.

Entry criteria: Learning Record passed initial quality validation.
Exit criteria: Learning Record tagged with regime, macro context, session ID, and source chain IDs.
Responsible component: Learning Processor.

**Stage 4: PATTERN DETECTION**

The Pattern Discovery Engine analyses enriched Learning Records to detect candidate patterns. It compares each record against existing patterns (reinforcing existing patterns or initiating new candidate patterns), and against anti-patterns (flagging records that match known failure modes).

Entry criteria: Enriched Learning Record with context tags.
Exit criteria: Pattern confidence updated (existing patterns); or candidate pattern INITIATED (new pattern).
Responsible component: Pattern Discovery Engine.

**Stage 5: KNOWLEDGE EXTRACTION**

When a candidate pattern has accumulated sufficient evidence (minimum instance count, statistical significance, effect size above threshold), the Knowledge Updater extracts a formal knowledge claim from it: a testable, quantified statement about system behavior or market behavior.

Entry criteria: Candidate pattern with sufficient evidence (minimum 10 instances, p < 0.05, effect size > 5%).
Exit criteria: Knowledge claim in CANDIDATE status, ready for validation.
Responsible component: Knowledge Updater; Pattern Discovery Engine.

**Stage 6: MODEL UPDATE PREPARATION**

The Model Improvement Manager prepares the specific model parameter changes implied by the knowledge claim. For a confidence recalibration, this means the new parameter values. For a strategy weight adjustment, this means the new weight allocation. For a risk limit recommendation, this means the proposed new threshold.

Entry criteria: Validated knowledge claim with quantified update recommendations.
Exit criteria: Proposed model update packaged with before/after parameter comparison, projected impact, and validation plan.
Responsible component: Model Improvement Manager.

**Stage 7: VALIDATION**

The Learning Validation Manager runs the 5-stage validation pipeline on the proposed update:

`
Stage 7a: Data Quality Check
  ─ Is the underlying data reliable and complete?
  ─ Are there data gaps, obvious errors, or survivorship bias in the dataset?

Stage 7b: Statistical Significance Test
  ─ Is the effect statistically significant (p < 0.05)?
  ─ Is the effect size practically meaningful (> 5% improvement)?
  ─ Is the sample size sufficient (n >= minimum threshold)?

Stage 7c: Out-of-Sample Test
  ─ Does the pattern hold on a held-out test period not used in discovery?
  ─ The most recent 20% of the pattern's history is reserved for out-of-sample testing.

Stage 7d: Regime Stability Test
  ─ Does the pattern hold across multiple market regimes, or is it regime-specific?
  ─ If regime-specific: is the regime assignment correct?

Stage 7e: Impact Assessment
  ─ What is the projected improvement in the target metric?
  ─ What is the risk of the proposed update: could it worsen performance in edge cases?
`

Entry criteria: Proposed model update from Model Improvement Manager.
Exit criteria: VALIDATION_PASSED or VALIDATION_FAILED with reasons.
Responsible component: Learning Validation Manager.

**Stage 8: GOVERNANCE APPROVAL**

The Learning Governance Manager reviews validated learning outputs. The governance tier determines the approval path:

| Governance Tier | Condition | Approval path |
|---|---|---|
| TIER-1-AUTO | Minor calibration; projected impact < 2%; no safety boundary | Automatic approval |
| TIER-2-ADVISORY | Moderate impact; 2%-10%; no safety boundary | Auto-approved; human notification |
| TIER-3-HUMAN | Major update; > 10% projected impact; or near safety boundary | Human approval required |
| TIER-4-COMMITTEE | Structural change; new strategy promotion; rule modification | Multi-human approval required |

Entry criteria: Validated learning output from Learning Validation Manager.
Exit criteria: APPROVED with deployment authorisation; or REJECTED with reasons.
Responsible component: Learning Governance Manager.

**Stage 9: DEPLOYMENT**

The Knowledge Updater applies the approved update to the target layer component. Updates are applied incrementally within configured bounds. The Knowledge Updater confirms the update was applied successfully and records the before/after parameter state.

Entry criteria: APPROVED disposition from Learning Governance Manager.
Exit criteria: Update applied to target component; update confirmation recorded.
Responsible component: Knowledge Updater.

**Stage 10: MONITORING**

The deployed update is monitored for its intended effect. The Performance Analyzer tracks the target metric in the sessions following deployment. Is the improvement materialising as projected?

Entry criteria: Update deployed to target component.
Exit criteria: 5 sessions of post-deployment monitoring completed; improvement confirmed or not confirmed.
Responsible component: Performance Analyzer; Model Improvement Manager.

**Stage 11: FEEDBACK**

The monitoring results are fed back into the Learning Engine. Did the deployment improve performance? If yes: the pattern that drove it is strengthened; confidence in similar patterns is raised. If no: the pattern is flagged for re-investigation; the confidence model that produced it is questioned.

Entry criteria: Post-deployment monitoring data.
Exit criteria: Feedback incorporated into Learning Record; pattern confidence updated.
Responsible component: Feedback Manager; Pattern Discovery Engine.

**Stage 12: EVOLUTION**

As new evidence accumulates, knowledge evolves. Patterns may be refined, broadened, or narrowed. Model parameters may be fine-tuned. Knowledge claims may be expanded from single-regime to multi-regime. Evolution is continuous; a deployed knowledge item is never treated as final.

Entry criteria: Sufficient new evidence post-deployment.
Exit criteria: Updated knowledge claim in catalog; prior version archived with SUPERSEDED status.
Responsible component: Knowledge Updater; Learning Catalog.

**Stage 13: ARCHIVE AND RETIREMENT**

Knowledge items that have been superseded by newer, better-validated versions, or that are no longer applicable (e.g., a regime that no longer occurs), are retired. Retired items are permanently archived with their full history. They are never deleted.

Entry criteria: SUPERSEDED or RETIRED status.
Exit criteria: Learning record in permanent archive with complete provenance trail.
Responsible component: Learning Archive Manager.

---

### IV.3 Lifecycle State Transition Diagram

`
   [EXPERIENCE_COLLECTED]
           |
           v
       [VALIDATED] ──── FAIL ──> [REJECTED] ──> [ARCHIVED]
           |
           v
   [CONTEXT_ENRICHED]
           |
           v
  [PATTERN_DETECTED]
           |
    sufficient evidence?
           |── NO ──> [PENDING_EVIDENCE] (accumulate; revisit)
           |
           v YES
  [KNOWLEDGE_EXTRACTED]
           |
           v
  [UPDATE_PREPARED]
           |
           v
     [VALIDATING]
           |
    validation passed?
           |── FAIL ──> [VALIDATION_FAILED] ──> [REJECTED]
           |
           v PASS
  [GOVERNANCE_PENDING]
           |
    approval decision?
           |── REJECTED ──> [REJECTED] ──> [ARCHIVED]
           |── HELD ──> [PENDING_HUMAN_APPROVAL]
           |
           v APPROVED
      [DEPLOYING]
           |
           v
      [MONITORING]
           |
    improvement confirmed?
           |── NOT_CONFIRMED ──> [ROLLBACK_INITIATED] ──> [PRIOR_VERSION_RESTORED]
           |
           v CONFIRMED
      [ACTIVE]
           |
    new version available?
           |── YES ──> [SUPERSEDED] ──> [ARCHIVED]
           |
           v still valid
      [ACTIVE] (continuous monitoring loop)
`

---

### IV.4 Learning Record Status Reference

| Status | Description | Terminal? |
|---|---|---|
| COLLECTED | Raw learning record ingested | No |
| PROCESSING | Being enriched and routed | No |
| VALIDATED | Initial quality validation passed | No |
| REJECTED | Failed quality, statistical, or governance check | Yes |
| PATTERN_DETECTED | Contributing to a pattern | No |
| KNOWLEDGE_EXTRACTED | Formal knowledge claim created | No |
| UPDATE_PREPARED | Model update packaged | No |
| VALIDATING | In 5-stage validation pipeline | No |
| VALIDATION_FAILED | Failed validation | Yes |
| GOVERNANCE_PENDING | Awaiting governance approval | No |
| PENDING_HUMAN_APPROVAL | Awaiting human review | No |
| APPROVED | Approved for deployment | No |
| DEPLOYING | Being applied to target components | No |
| ACTIVE | Deployed and being monitored | No |
| MONITORING | Post-deployment monitoring active | No |
| ROLLBACK_INITIATED | Reverting deployed update | No |
| SUPERSEDED | Replaced by newer version | Yes |
| RETIRED | No longer applicable | Yes |
| ARCHIVED | Permanently archived | Yes |

---

### IV.5 Lifecycle Timing Reference

| Stage | Target duration | Alert threshold |
|---|---|---|
| Collection to Validated | < 30 seconds | > 5 minutes |
| Validated to Pattern Detected | Variable (accumulation period) | Alert if pattern stalls > 30 days |
| Pattern to Knowledge Extracted | < 24 hours after threshold met | > 48 hours |
| Knowledge to Update Prepared | < 1 hour | > 4 hours |
| Update Prepared to Validation Complete | < 4 hours (small update); < 24 hours (large) | > 48 hours |
| Validation to Governance Decision | < 1 hour (TIER-1-AUTO); < 24 hours (TIER-3-HUMAN) | > 72 hours |
| Governance Approved to Deployed | < 1 hour | > 4 hours |
| Deployment to Active Monitoring | Immediate | — |
| Monitoring period | 5 sessions minimum | Alert if < 3 sessions of data available |

---

### IV.6 Learning PIT Semantics

The Learning Engine uses Point-in-Time (PIT) semantics throughout. Every state transition is recorded with a wall-clock timestamp, session ID, and the system state at the time of transition. This enables:

- Historical reconstruction: "What was the strategy weight model on session SES-20260101-0001?"
- Counterfactual analysis: "What would performance have been if this pattern had been deployed two weeks earlier?"
- Audit compliance: every learning state is fully provable from the audit trail.

---

## PART V — LEARNING SERVICES

### V.1 Overview

The Learning Services layer provides the operational service interfaces through which the Learning Engine components interact, and through which other IIOS layers consume learning outputs. There are 12 services.

---

### V.2 LS-01: Collection Service

**Purpose:** Provides the unified API for all Learning Engine ingestion operations.

**Capabilities:**
- Ingest learning signals from all 17 IIOS layers via EventBus
- Apply signal type classification (LT-01 through LT-21)
- Apply deduplication and rate limiting
- Batch collection for between-session processing
- Replay missed events from EventBus buffer (up to configurable lookback)

**Service properties:**
- Non-blocking: all collection is async; never blocks the EventBus
- Idempotent: duplicate signals produce no duplicate records
- Priority-aware: OUTCOME and ERROR signals have highest collection priority

**Consumers:** Learning Collector (LC-03)

---

### V.3 LS-02: Pattern Discovery Service

**Purpose:** Provides the query and management interface for the Pattern Discovery Engine.

**Capabilities:**
- Submit new learning records for pattern analysis
- Query the pattern catalog: by learning type, regime, confidence tier, date range
- Request pattern validation for a specific candidate pattern
- Subscribe to pattern updates: receive notifications when patterns are strengthened, weakened, or retired

**Service properties:**
- Long-running computation: pattern scanning runs in background; results are delivered asynchronously
- Regime-partitioned: all queries support regime filters; cross-regime queries are explicitly flagged

**Consumers:** Learning Governance Manager; Learning Analytics Manager; StrategyLab (via learning recommendations)

---

### V.4 LS-03: Knowledge Update Service

**Purpose:** The interface through which approved knowledge updates are applied to target layer components.

**Capabilities:**
- Apply incremental parameter updates to all registered target models
- Enforce parameter change bounds (max delta per update cycle)
- Validate parameter state after update (post-application sanity check)
- Rollback any applied update to prior state
- Report update application status and history

**Service properties:**
- Transactional: update either fully applies or fully reverts (no partial application)
- Bounded: all updates are bounded by constitutional parameter limits
- Reversible: full rollback capability to any prior parameter version

**Consumers:** Knowledge Updater (LC-06); Model Improvement Manager (LC-07)

---

### V.5 LS-04: Feedback Service

**Purpose:** Provides the interface for all feedback signal collection, attribution, and delivery.

**Capabilities:**
- Receive feedback signals from TradeMonitoring, ExecutionEngine, StrategyPerformanceTracker, human operators
- Attribute feedback signals to source decisions, reasoning chains, hypotheses, and strategies
- Deliver attributed feedback to Pattern Discovery Engine and Learning Processor
- Support manual feedback submission by operators via Telegram interface

**Service properties:**
- Attribution-first: every feedback signal has source attribution before processing
- Weighted: recent feedback is weighted more than old; human feedback weighted highest
- Decay-aware: feedback weight decays on a configurable schedule

**Consumers:** Feedback Manager (LC-08); Pattern Discovery Engine (LC-05)

---

### V.6 LS-05: Model Improvement Service

**Purpose:** Provides the management interface for model monitoring and recalibration lifecycle.

**Capabilities:**
- Register models for monitoring (specify model ID, current parameters, performance metric)
- Subscribe to drift alerts for specific models
- Submit recalibration proposals for validation
- Query model performance history and drift history

**Service properties:**
- Model-agnostic: supports any parameterised model; does not depend on model type
- History-preserving: all model versions and performance histories are permanently available

**Consumers:** Model Improvement Manager (LC-07); Drift Detector (LC-13); Learning Governance Manager (LC-15)

---

### V.7 LS-06: Validation Service

**Purpose:** Exposes the 5-stage validation pipeline as a service for all learning outputs.

**Capabilities:**
- Submit learning output for validation (synchronous or asynchronous)
- Configure validation criteria for each learning type
- Query validation history for any learning output
- Produce validation reports on demand

**Validation pipeline stages exposed as service operations:**
1. Data Quality Check
2. Statistical Significance Test
3. Out-of-Sample Test
4. Regime Stability Test
5. Impact Assessment

**Service properties:**
- Configurable: validation criteria are configurable per learning type and governance tier
- Circuit-breaker: if validation failure rate exceeds threshold, service halts and alerts

**Consumers:** Learning Validation Manager (LC-14)

---

### V.8 LS-07: Governance Service

**Purpose:** Manages the governance approval workflow for all learning outputs.

**Capabilities:**
- Submit validated learning outputs for governance review
- Query governance status of any pending output
- Record governance decisions (APPROVED, REJECTED, HELD)
- Escalate to human operators via Telegram for TIER-3-HUMAN and TIER-4-COMMITTEE decisions
- Produce governance audit trail

**Service properties:**
- Authority-aware: different operations require different authority levels
- Traceable: every governance decision is permanently logged
- Escalation-capable: automatically escalates TIER-3 and TIER-4 items to human operators

**Consumers:** Learning Governance Manager (LC-15); Learning Audit Manager (LC-16)

---

### V.9 LS-08: Analytics Service

**Purpose:** Provides learning analytics and quality metrics to ControlTower and human operators.

**Capabilities:**
- Compute Learning Quality Score (LQS) per session and per rolling window
- Produce learning pipeline throughput metrics
- Produce pattern catalog statistics
- Produce strategy learning effectiveness reports
- Deliver analytics to ControlTower dashboard and Telegram

**Service properties:**
- Non-blocking: analytics computation does not block learning pipeline
- Session-aware: produces both intra-session and cross-session analytics

**Consumers:** Learning Analytics Manager (LC-19); ControlTower (Layer 17); human operators

---

### V.10 LS-09: Recommendation Service

**Purpose:** Delivers prioritised learning recommendations to human operators and governance.

**Capabilities:**
- Aggregate signals from all Discovery tier components
- Rank recommendations by projected impact and urgency
- Deliver recommendations via Telegram (IMMEDIATE), dashboard (all), weekly report (PLANNED)
- Track recommendation outcomes: were implemented recommendations effective?

**Service properties:**
- Impact-ranked: always presents highest-impact recommendations first
- Human-readable: recommendations are expressed in plain-language format, not raw metrics

**Consumers:** Learning Recommendation Manager (LC-20); human operators; ControlTower

---

### V.11 LS-10: Audit Service

**Purpose:** Provides the query interface for the Learning Audit Log.

**Capabilities:**
- Record audit events (append-only)
- Query audit events by: learning record ID, learning type, date range, component, decision type
- Verify hash chain integrity
- Produce compliance reports

**Service properties:**
- Append-only: no audit record is ever modified or deleted
- Hash-chain-linked: every audit event is linked to its predecessor via SHA-256
- Integrity-verifiable: hash chain can be verified on demand

**Consumers:** Learning Audit Manager (LC-16); Learning Governance Manager; compliance auditors

---

### V.12 LS-11: Archive Service

**Purpose:** Manages the permanent, compressed archive of learning history.

**Capabilities:**
- Archive terminal-state learning records
- Query historical learning records with full-text and metadata search
- Retrieve specific historical knowledge states by date
- Support retention policy enforcement

**Service properties:**
- Permanent: records are never deleted; only compressed after retention threshold
- Queryable: indexed by type, date, strategy, regime, quality score

**Consumers:** Learning Archive Manager (LC-17); forensic analysis; compliance review

---

### V.13 LS-12: Health Service

**Purpose:** Exposes the Learning Engine health status to ControlTower and all consumers.

**Capabilities:**
- Report Learning System Health Score (LSHS) on demand
- Report per-component health status
- Report learning throughput metrics (records/hour through each lifecycle stage)
- Subscribe to health alert events (component failure, circuit breaker activation)

**Service properties:**
- Always available: health service is the first activated and last deactivated component
- Self-monitoring: the Health Manager monitors its own health independently

**Consumers:** Learning Health Manager (LC-18); ControlTower (Layer 17); human operators

---

## PART VI — LEARNING PIPELINES

### VI.1 Overview

The Learning Engine implements 10 processing pipelines. Each pipeline handles a specific category of learning input from ingestion through knowledge update. Pipelines share infrastructure (Learning Registry, Validation Service, Governance Service, Audit Service) but have distinct processing logic, validation criteria, and update targets.

---

### VI.2 Pipeline LP-01: Observation-to-Learning Pipeline

`
[Observation Engine outputs]
         |
         v
[Learning Collector]
  Signal type: LT-01 Observation Learning
         |
         v
[Learning Processor]
  Enrichment: observation type, source reliability history, regime context
         |
         v
[Outcome Comparison]
  Compare observation against subsequent confirmed market data
  Compute observation accuracy score per observation type and source
         |
         v
[Pattern Discovery Engine]
  Pattern class: OBSERVATION_RELIABILITY
  Question: "Does observation source S consistently produce accurate observations of type T?"
         |
         v
[Knowledge Updater]
  Target: Evidence Engine source reliability weights
  Update: increase weight for consistent sources; decrease for noisy sources
         |
    Validation → Governance → Deployment
`

**Key quality metric:** Observation Accuracy Rate (OAR) per source and observation type
**Update frequency:** Weekly (accumulate week of observations; update at weekend)
**Governance tier:** TIER-1-AUTO for weight adjustments < 10%; TIER-2-ADVISORY for > 10%

---

### VI.3 Pipeline LP-02: Outcome-to-Learning Pipeline

`
[TradeMonitoring (Layer 12)]
  Closed trade record: entry, exit, PNL, MAE, MFE, exit reason, strategy, regime
         |
         v
[Learning Collector]
  Signal type: LT-07 Outcome Learning
         |
         v
[Outcome Analyzer]
  Decompose: actual PNL vs planned PNL, MAE vs stop, MFE vs TP
  Stratify: by strategy, regime, instrument class, time, confidence tier
         |
         v
[Feedback Manager]
  Attribute to: source decision, reasoning chain, hypothesis, strategy
  Weight by: PNL magnitude, decision confidence tier
         |
         v
[Pattern Discovery Engine]
  Pattern classes: OUTCOME_BY_REGIME, STRATEGY_OUTCOME_TREND, EXECUTION_QUALITY_IMPACT
         |
         v
[Knowledge Updater]
  Targets: MetaLearning strategy weights, Decision Engine confidence calibration
         |
    Validation → Governance → Deployment
`

**Key quality metric:** Outcome Attribution Rate (OAR2): fraction of closed trades with full attribution
**Update frequency:** Session-end (after 15:30 IST); each closed session
**Governance tier:** TIER-2-ADVISORY for weight changes < 5%; TIER-3-HUMAN for > 5% or strategy demotion

---

### VI.4 Pipeline LP-03: Execution Feedback Pipeline

`
[Execution Engine (Layer 11)]
  EQS data per execution: all 12 dimensions
         |
         v
[Learning Collector]
  Signal type: LT-06 Execution Learning
         |
         v
[Learning Processor]
  Enrich: time of day, instrument class, broker, regime, order type
         |
         v
[Pattern Discovery Engine]
  Pattern classes: EQS_BY_TIME, EQS_BY_INSTRUMENT, EQS_BY_ORDER_TYPE, SLIPPAGE_PATTERNS
         |
         v
[Knowledge Updater]
  Targets: Execution Engine slippage priors, order type preferences, broker routing weights
         |
    Validation → Governance → Deployment
`

**Key quality metric:** Average EQS improvement over rolling 30-session window
**Update frequency:** Weekly (7 sessions of EQS data before update)
**Governance tier:** TIER-1-AUTO for execution parameter calibration; TIER-2-ADVISORY for routing changes

---

### VI.5 Pipeline LP-04: Decision Review Pipeline

`
[Decision Engine (Layer 10/11)]
  Decision Package outcomes: DCS at time of decision; actual outcome
         |
         v
[Learning Collector]
  Signal type: LT-05 Decision Learning
         |
         v
[Feedback Manager]
  Attribute outcome to specific DCS tier, action type, debate consensus score
         |
         v
[Pattern Discovery Engine]
  Pattern class: DCS_CALIBRATION — "Is DCS X% actually associated with Y% win rate?"
         |
         v
[Model Improvement Manager]
  Target model: Decision Engine confidence scoring model
  Proposed recalibration: DCS tiers recalibrated to match actual outcome frequencies
         |
    Validation (5-stage) → Governance → Deployment
`

**Key quality metric:** Decision Confidence Calibration Score (DCCS): correlation between DCS and actual outcome frequency
**Update frequency:** Monthly (minimum 30 decisions before recalibration)
**Governance tier:** TIER-3-HUMAN (confidence model changes are structural)

---

### VI.6 Pipeline LP-05: Pattern Discovery Pipeline

`
[All Learning Records (LT-01 through LT-21)]
         |
         v
[Pattern Discovery Engine: continuous scan]
  Scan modes:
    1. Incremental: new records added to existing pattern instances
    2. Full scan: between-session complete history rescan
    3. Regime-specific: targeted scan within one regime
         |
         v
[Candidate Pattern: sufficient evidence reached]
  Metadata: type, domain, regime, instances, confidence, effect size
         |
         v
[Learning Validation Manager: 5-stage validation]
         |
         v
[Learning Governance Manager: approval]
         |
         v
[Learning Catalog: ACTIVE pattern added]
         |
         v
[Learning Recommendation Manager: notify operator if significant]
`

**Key quality metric:** Pattern Validation Rate (PVR): % of candidate patterns that pass 5-stage validation
**Target PVR:** > 40% (a PVR < 25% indicates the discovery engine is too liberal)
**Update frequency:** Continuous; batch full scan at weekend

---

### VI.7 Pipeline LP-06: Knowledge Update Pipeline

`
[Approved learning output from Governance Service]
         |
         v
[Knowledge Updater: parameter translation]
  Convert abstract learning output to specific parameter delta
  Verify delta within constitutional bounds
         |
         v
[Target component: parameter update applied]
  Examples:
    MetaLearning: strategy weight += delta (bounded by max_weight_delta)
    Decision Engine: confidence tier boundaries shifted
    Execution Engine: slippage prior updated
    Evidence Engine: source reliability weight updated
         |
         v
[Knowledge Updater: post-application validation]
  Verify parameter is within valid range post-application
  Record before/after state
         |
         v
[Learning Audit Manager: update audit event written]
         |
         v
[Performance Analyzer: monitoring begins]
  Track target metric for 5 sessions post-deployment
`

**Key quality metric:** Knowledge Update Effectiveness Rate (KUER): % of deployed updates that produce measurable improvement
**Target KUER:** > 60% (majority of updates should improve performance)
**Update frequency:** Per approval; triggered by governance decisions

---

### VI.8 Pipeline LP-07: Model Improvement Pipeline

`
[Drift Detector: model drift detected]
         |
         v
[Model Improvement Manager: recalibration proposal prepared]
  Contents: affected model, current parameters, proposed parameters, evidence summary
         |
         v
[Walk-Forward Test]
  Test proposed parameters on held-out recent history
  Must show improvement on out-of-sample period
         |
         v
[Learning Validation Manager: 5-stage validation]
         |
         v
[Learning Governance Manager: TIER-3-HUMAN approval]
         |
         v
[Knowledge Updater: model parameter update applied]
         |
         v
[Model Improvement Manager: post-deployment monitoring]
  Track model prediction accuracy for 10 sessions
  Rollback if accuracy declines further post-update
`

**Key quality metric:** Model Calibration Improvement Score (MCIS): improvement in prediction accuracy post-recalibration
**Update frequency:** Triggered by drift detection; at most monthly per model
**Governance tier:** TIER-3-HUMAN (model changes are structural)

---

### VI.9 Pipeline LP-08: Validation Pipeline

`
[Any candidate learning output requiring validation]
         |
         v
[Learning Validation Manager: Stage 1 — Data Quality]
  FAIL → REJECTED → Archive
         |
         v
[Stage 2: Statistical Significance Test]
  FAIL → REJECTED → Archive
         |
         v
[Stage 3: Out-of-Sample Test]
  FAIL → REJECTED → Archive; record as "pattern of insufficient generality"
         |
         v
[Stage 4: Regime Stability Test]
  FAIL → Re-classify as regime-specific (not a failure; a refinement)
         |
         v
[Stage 5: Impact Assessment]
  FAIL → REJECTED if negative projected impact
         |
         v
[VALIDATION_PASSED: forward to Governance Pipeline]
`

---

### VI.10 Pipeline LP-09: Governance Pipeline

`
[VALIDATION_PASSED learning output]
         |
         v
[Learning Governance Manager: governance tier classification]
         |
    TIER-1-AUTO ───> Auto-approved ──> Deployment Pipeline
    TIER-2-ADVISORY ─> Auto-approved + Notification ──> Deployment Pipeline
    TIER-3-HUMAN ───> Human approval queue ──> Telegram notification
                              |
                         Human decision
                         APPROVED ──> Deployment Pipeline
                         REJECTED ──> Archive (with reason)
    TIER-4-COMMITTEE ─> Multi-human queue ──> Telegram to all admins
                              |
                         All admins approve ──> Deployment Pipeline
                         Any admin rejects ──> REJECTED ──> Archive
`

---

### VI.11 Pipeline LP-10: Archive Pipeline

`
[Terminal-state learning records (DEPLOYED, REJECTED, SUPERSEDED, RETIRED)]
         |
         v
[Learning Archive Manager: record ingestion]
  Apply metadata: archive timestamp, terminal reason, final quality score
         |
         v
[Compression: records older than 90 days compressed]
         |
         v
[Index update: archived record added to queryable index]
         |
         v
[Integrity check: archive checksum updated]
         |
         v
[Retention check: records beyond retention window → cold storage tier]
`

---

## PART VII — LEARNING QUALITY FRAMEWORK

### VII.1 Purpose

The Learning Quality Framework defines how the quality of learning outputs is measured. It is the basis for the Learning Quality Score (LQS) — the composite quality metric for the Learning Engine, analogous to the Execution Quality Score (EQS) in the Execution Engine.

---

### VII.2 Learning Quality Dimensions

The LQS is computed as a weighted sum of 12 quality dimensions (LQD-01 through LQD-12):

LengthLQS = \sum_{d=1}^{12} w_d \cdot s_dLength

where $ is the weight for dimension $ and  \in [0,1]$ is the normalised score.

---

### VII.3 Dimension Definitions

**LQD-01: Accuracy (weight: 0.20)**

Does the learning output correctly describe the underlying pattern, calibration, or relationship? An accurate learning output is one where the proposed knowledge claim is factually correct when evaluated against the ground truth data.

Score 1.0: knowledge claim perfectly matches ground truth on validation data.
Score 0.5: knowledge claim partially matches (correct direction, wrong magnitude).
Score 0.0: knowledge claim is factually incorrect.

**LQD-02: Novelty (weight: 0.10)**

Does the learning output add new knowledge to the system? Learning that merely confirms what is already known at the same confidence level has low novelty. Learning that revises an existing belief substantially, or discovers an entirely new pattern, has high novelty.

Score 1.0: entirely new pattern or significant revision of prior knowledge.
Score 0.5: incremental refinement of existing knowledge.
Score 0.0: duplicate of existing knowledge with no new information.

**LQD-03: Generalization (weight: 0.15)**

Does the learning output generalise beyond the specific examples from which it was derived? A high-generalization output holds across multiple regimes, instrument classes, and time periods. A low-generalization output only applies to a specific narrow condition.

Score 1.0: generalises across all regimes; stable out-of-sample.
Score 0.5: regime-specific but consistent within that regime.
Score 0.0: overfit; fails on out-of-sample data.

**LQD-04: Repeatability (weight: 0.10)**

Is the learning output consistently produced from similar data? If the same pattern is present in multiple independent datasets, the learning engine should discover it consistently. Low repeatability indicates a brittle discovery process.

Score 1.0: pattern discovered consistently in all independent replications.
Score 0.5: discovered in majority of replications.
Score 0.0: found in only one specific dataset; cannot be replicated.

**LQD-05: Stability (weight: 0.10)**

Does the learning output remain valid over time, once deployed? High stability means the deployed knowledge continues to improve performance across multiple sessions. Low stability means the improvement is transient.

Score 1.0: improvement holds for > 20 sessions post-deployment.
Score 0.5: improvement holds for 5-20 sessions.
Score 0.0: improvement disappears within 5 sessions.

**LQD-06: Reliability (weight: 0.10)**

Is the underlying data from which the learning was derived trustworthy? High-reliability learning comes from clean, complete, well-attributed data. Low-reliability learning comes from sparse, noisy, or ambiguously-attributed data.

Score 1.0: clean, complete, well-attributed data; source reliability > 90%.
Score 0.5: some gaps or noise in underlying data.
Score 0.0: sparse or unreliable data; attribution unclear.

**LQD-07: Bias Detection (weight: 0.05)**

Has the learning output been checked for known biases? A high bias-detection score means the output has been screened for all known bias types (confirmation, recency, survivorship, anchoring, regime confusion) and is clean.

Score 1.0: all bias checks passed; no bias detected.
Score 0.5: minor bias detected; documented and controlled.
Score 0.0: significant bias detected; output should be quarantined.

**LQD-08: Drift Detection (weight: 0.05)**

Has the context within which this learning output is valid been checked for drift? A high drift score means the learning output was validated in a stable market context, and drift monitoring is active post-deployment.

Score 1.0: drift monitoring active; no drift detected; learning applicable to current regime.
Score 0.5: mild drift detected; learning partially applicable.
Score 0.0: severe drift; learning not applicable to current conditions.

**LQD-09: Explainability (weight: 0.05)**

Can the learning output be explained in plain language? A high-explainability score means a human operator can understand what the learning discovered and why it proposes an update. Low explainability is a red flag — unexplainable outputs may be spurious correlations.

Score 1.0: clear plain-language explanation; causal hypothesis documented.
Score 0.5: partially explained; mechanism hypothesised but not confirmed.
Score 0.0: black-box correlation; no explanation available.

**LQD-10: Traceability (weight: 0.03)**

Can the learning output be fully traced back to its source data? A traceable output has a complete provenance trail: from the raw events that triggered it, through the pattern discovery process, to the validation tests and governance approval.

Score 1.0: complete provenance trail; all source records identified.
Score 0.5: partial provenance; some source records missing.
Score 0.0: no provenance; cannot be traced to source data.

**LQD-11: Confidence (weight: 0.04)**

Is the confidence assigned to this learning output calibrated to the actual evidence? A well-calibrated learning output assigns confidence proportional to the strength of the evidence. Overconfident outputs are dangerous (applied too aggressively); underconfident outputs are wasted (ignored despite being valid).

Score 1.0: confidence calibrated to evidence; historical calibration error < 5%.
Score 0.5: moderate calibration error (5-15%).
Score 0.0: severe calibration error (> 15%); confidence is unreliable.

**LQD-12: Improvement Impact (weight: 0.03)**

What is the projected improvement in the target metric if this learning output is deployed? High-impact outputs deserve more governance attention and faster deployment. Very low-impact outputs may not be worth the deployment risk.

Score 1.0: projected improvement > 5% in target metric.
Score 0.5: projected improvement 1-5%.
Score 0.0: projected improvement < 1%; marginal.

---

### VII.4 LQS Formula and Tiers

LengthLQS = 0.20 \cdot s_{01} + 0.10 \cdot s_{02} + 0.15 \cdot s_{03} + 0.10 \cdot s_{04} + 0.10 \cdot s_{05} + 0.10 \cdot s_{06} + 0.05 \cdot s_{07} + 0.05 \cdot s_{08} + 0.05 \cdot s_{09} + 0.03 \cdot s_{10} + 0.04 \cdot s_{11} + 0.03 \cdot s_{12}Length

**LQS Tiers:**

| Tier | Range | Interpretation |
|---|---|---|
| EXCELLENT | 0.85 – 1.00 | High-quality learning; fast-track to governance approval |
| GOOD | 0.70 – 0.84 | Good learning; standard validation and governance |
| ACCEPTABLE | 0.55 – 0.69 | Acceptable; proceed with enhanced monitoring post-deployment |
| MARGINAL | 0.35 – 0.54 | Marginal quality; require TIER-3-HUMAN approval regardless of impact |
| FAILED | 0.00 – 0.34 | Below quality threshold; reject; archive with failure reasons |

---

### VII.5 Quality Monitoring Thresholds

| Metric | Target | Warning | Critical |
|---|---|---|---|
| Session average LQS | > 0.75 | < 0.65 | < 0.50 |
| Pattern validation rate | > 40% | < 25% | < 10% |
| Knowledge update effectiveness rate | > 60% | < 45% | < 30% |
| Rollback rate (deployed updates rolled back) | < 5% | > 10% | > 20% |
| Bias detection rate | 0% bias unchecked | > 5% unchecked | > 15% unchecked |
| Human override rate on auto-approved updates | < 3% | > 8% | > 15% |

---

## PART VIII — LEARNING GOVERNANCE

### VIII.1 Overview

Learning Governance ensures that the Learning Engine operates within the boundaries established by the IIOS Architecture, does not violate constitutional rules, and produces improvements that are traceable, reversible, and approved by the appropriate authority.

---

### VIII.2 Governance Ownership

| Governance function | Owner |
|---|---|
| Learning constitutional rules | IIOS Architecture (this document) |
| Governance tier assignment | Learning Governance Manager |
| TIER-1 auto-approval | Learning Governance Manager (automatic) |
| TIER-2 advisory approval | Learning Governance Manager + notification to human |
| TIER-3 human approval | Human operator (via Telegram) |
| TIER-4 committee approval | All registered human administrators |
| Rollback authority | Human operator (any tier) |
| Bias investigation | Learning Governance Manager + human operator |

---

### VIII.3 Naming Standards

| Object | Format | Example |
|---|---|---|
| Learning Record ID | LRN-{TYPE}-{DATE}-{SEQ:08d} | LRN-LT10-20260101-00000001 |
| Pattern ID | PAT-{DOMAIN}-{DATE}-{SEQ:06d} | PAT-STRATEGY-20260101-000001 |
| Knowledge Update ID | KU-{TARGET}-{DATE}-{SEQ:06d} | KU-METALRN-20260101-000001 |
| Model Version ID | MDL-{MODEL}-{VERSION:04d} | MDL-DCSMODEL-0047 |
| Audit Event ID | LAUD-{LRN_ID}-{SEQ:06d} | LAUD-LRN-LT10-...-000001 |
| Session Report ID | LRPT-{SESSION_ID}-{SEQ:04d} | LRPT-SES-20260101-0001-0001 |

---

### VIII.4 Versioning

All knowledge objects in the Learning Catalog are versioned:
- Every approved update creates a new version of the affected knowledge object
- Version format: {MAJOR}.{MINOR} — MAJOR incremented for structural changes; MINOR for calibration updates
- Prior versions are archived with SUPERSEDED status (never deleted)
- Rollback restores the immediately prior version

---

### VIII.5 Knowledge Approval Matrix

| Update type | Auto-approved? | Human required? | Committee required? |
|---|---|---|---|
| Calibration update: < 2% parameter change | Yes (TIER-1) | No | No |
| Calibration update: 2%-10% parameter change | Advisory (TIER-2) | Notification only | No |
| Strategy weight change: < 5% | Advisory (TIER-2) | Notification only | No |
| Strategy weight change: > 5% | No | Yes (TIER-3) | No |
| Strategy demotion | No | Yes (TIER-3) | No |
| Strategy promotion | No | Yes (TIER-3) | No |
| Strategy retirement | No | Yes (TIER-3) | No |
| New pattern deployment: any | Advisory (TIER-2) | Notification only | No |
| Model structural change | No | Yes (TIER-3) | No |
| Risk parameter change | No | Yes (TIER-3) | No |
| Constitutional rule modification | No | No | Yes (TIER-4) |
| Kill Switch behavior modification | No | No | Prohibited |

---

### VIII.6 Compliance Requirements

| Requirement | Rule |
|---|---|
| All learning updates audited | LC-GOV-001 |
| All updates reversible | LC-GOV-002 |
| No update without validation | LC-GOV-003 |
| No constitutional boundary violations | LC-GOV-004 |
| Kill Switch is never subject to learning | LC-GOV-005 |
| Human authority absolute | LC-GOV-006 |
| Bias check before deployment | LC-GOV-007 |
| Minimum evidence threshold enforced | LC-GOV-008 |
| Out-of-sample test mandatory | LC-GOV-009 |
| Full provenance trail required | LC-GOV-010 |

---

### VIII.7 Security Requirements

| Requirement | Implementation |
|---|---|
| Audit log is append-only | File permissions; no overwrite |
| Audit hash chain | SHA-256; verified on startup |
| Learning updates not externally injectable | Learning Collector accepts EventBus signals only; no external HTTP input |
| Human approval via authenticated channel | Telegram bot token; authorised chat IDs only |
| Knowledge backup | Archive replicated to VPS hourly |
| Model parameter bounds enforced | Knowledge Updater constitutional limits |

---

### VIII.8 Retention Policy

| Record type | Retention | Storage tier |
|---|---|---|
| Active learning records (ACTIVE status) | Indefinite (in registry) | Hot (SQLite) |
| Terminal learning records | 3 years minimum | Warm (SQLite + compressed) |
| Audit log | Indefinite | Append-only file |
| Model version history | Indefinite | SQLite |
| Pattern catalog history | Indefinite | SQLite |
| Session analytics reports | 2 years | SQLite |

---

## PART IX — LEARNING CONSTITUTION

### IX.1 Purpose

The Learning Constitution is the set of non-negotiable rules that govern the Learning Engine. No learning output, no algorithm, no configuration change, and no operator command may violate these rules. They are immutable architectural invariants.

The rules are organised into 14 categories. Each rule has a unique code, a title, a statement, and a rationale.

---

### IX.2 Category A: Learning Integrity

**LC-A-001: Evidence First**
No knowledge update is applied without validated, source-attributed evidence supporting it.
*Rationale: Updates without evidence are guesses. Guesses embedded in the knowledge base erode system quality.*

**LC-A-002: Minimum Evidence Threshold**
No pattern is promoted from CANDIDATE to VALIDATED with fewer than 10 independent instances.
*Rationale: Statistical significance requires a minimum sample. Single-event or two-event patterns are noise.*

**LC-A-003: Statistical Significance Mandatory**
No learning output is deployed without passing a statistical significance test (p < 0.05).
*Rationale: Without significance testing, the system would embed random correlations as knowledge.*

**LC-A-004: Out-of-Sample Test Mandatory**
No learning output is deployed without passing an out-of-sample validation test using held-out data not seen during pattern discovery.
*Rationale: In-sample performance is insufficient; the system must demonstrate generalization.*

**LC-A-005: Incrementality Enforced**
Learning updates are incremental. No single learning event causes a parameter change larger than the configured maximum step.
*Rationale: Large, abrupt parameter changes destabilize the system. Incremental learning is stable learning.*

**LC-A-006: Reversibility Required**
Every deployed learning update can be rolled back to the prior parameter state within one trading session.
*Rationale: If a deployed update causes harm, the ability to reverse it immediately limits the damage.*

**LC-A-007: Provenance Mandatory**
Every learning output has a traceable provenance chain linking it to its source data, discovery process, and validation history.
*Rationale: Unexplained knowledge cannot be verified, debugged, or audited.*

---

### IX.3 Category B: Knowledge Integrity

**LC-B-001: No Overwrites**
Knowledge updates create new versions; they do not overwrite prior versions. All prior versions are archived.
*Rationale: The history of knowledge evolution is as important as the current state.*

**LC-B-002: Catalog Consistency**
The Learning Catalog always reflects a consistent view of active knowledge. No two conflicting knowledge items may both be ACTIVE simultaneously for the same domain.
*Rationale: Conflicting active knowledge produces inconsistent system behavior.*

**LC-B-003: Version Sequencing**
Knowledge versions are applied in sequence. A version with a lower sequence number is never applied after one with a higher number.
*Rationale: Out-of-order updates create inconsistent states.*

**LC-B-004: Knowledge Scope Boundaries**
A learning output targeting the Execution Engine cannot modify parameters in the Decision Engine (or vice versa). Each learning output has a bounded target scope.
*Rationale: Cross-boundary updates create unpredictable coupling between layers.*

**LC-B-005: Knowledge Expiry**
Knowledge items marked RETIRED are never re-activated. If a retired pattern reappears, a new pattern record is created from scratch.
*Rationale: A retired pattern was retired for reasons. Re-activation bypasses the retirement rationale.*

---

### IX.4 Category C: Pattern Integrity

**LC-C-001: Pattern Source Integrity**
Patterns are only discovered from validated, attributed Learning Records. Patterns cannot be manually asserted; they must be discovered from data.
*Rationale: Manual pattern assertion bypasses the discovery and validation process, introducing unverified knowledge.*

**LC-C-002: Regime Tagging Required**
All patterns are tagged with the market regime(s) in which they were discovered and validated. Cross-regime patterns are explicitly marked and require additional validation.
*Rationale: Patterns from one regime applied in another regime are one of the most common sources of model failures.*

**LC-C-003: Confidence Calibration Required**
Every pattern has an associated confidence score calibrated to the validation evidence. Confidence is not assigned arbitrarily.
*Rationale: Calibrated confidence allows the system to appropriately weight patterns in decision-making.*

**LC-C-004: Pattern Lifecycle Enforced**
Patterns advance through defined lifecycle states: CANDIDATE → VALIDATED → ACTIVE → SUPERSEDED → RETIRED. No state may be skipped.
*Rationale: Lifecycle enforcement prevents premature deployment of unvalidated patterns.*

**LC-C-005: Effect Size Minimum**
No pattern is promoted from CANDIDATE to VALIDATED with an effect size below 5% improvement in the target metric.
*Rationale: Patterns with negligible effect sizes create noise in the knowledge base without delivering improvement.*

---

### IX.5 Category D: Feedback Integrity

**LC-D-001: Attribution Required**
All feedback signals are attributed to source decisions, reasoning chains, hypotheses, or strategies before being processed. Unattributed feedback is held in a PENDING_ATTRIBUTION queue.
*Rationale: Unattributed feedback cannot improve the correct component.*

**LC-D-002: Feedback Decay Mandatory**
Feedback signals decay in weight over time according to a configured decay schedule. No feedback signal from more than 180 days ago carries the same weight as current feedback.
*Rationale: Old feedback may reflect a market regime that no longer applies. Decayed feedback prevents the system from over-anchoring on historical conditions.*

**LC-D-003: Feedback Paradox Resolution**
Conflicting feedback signals (e.g., two outcomes with opposite PNL for similar decisions) are flagged as PARADOX and held for human review rather than being averaged.
*Rationale: Averaging conflicting signals produces meaningless noise. Resolution requires understanding the cause of the conflict.*

**LC-D-004: Human Feedback Priority**
Human feedback (operator overrides, annotations, corrections) is weighted higher than automated feedback in all attribution models.
*Rationale: Human judgment carries information that automated signals may miss.*

---

### IX.6 Category E: Bias Control

**LC-E-001: Bias Check Before Deployment**
All learning outputs are checked for the six primary bias types (confirmation, recency, survivorship, anchoring, regime confusion, execution quality) before governance approval.
*Rationale: Biased learning embeds systematic errors. Bias check before deployment is the last line of defense.*

**LC-E-002: Bias Quarantine**
Any learning output with a detected bias score above the SIGNIFICANT threshold is quarantined. Quarantined outputs cannot proceed to governance approval without human investigation.
*Rationale: Significant bias in a learning output means the knowledge claim may be systematically wrong in a specific direction — more dangerous than random error.*

**LC-E-003: Survivorship Bias Prevention**
Learning analyses always include data from failed strategies and rejected decisions, not only from profitable ones.
*Rationale: Learning from successes only produces a biased model that overestimates the success rate of future decisions.*

**LC-E-004: Recency Bias Dampening**
Learning weight schedules apply a time-decay function that gives more weight to recent signals but does not completely ignore historical signals.
*Rationale: Pure recency bias would cause the system to abandon valid long-term patterns during any short-term anomaly.*

---

### IX.7 Category F: Drift Control

**LC-F-001: Drift Monitoring Always Active**
Drift detection is active for all deployed quantitative models at all times during trading hours and between sessions.
*Rationale: Model drift is cumulative; early detection prevents small drift from becoming large performance degradation.*

**LC-F-002: Drift Halt on Severe Detection**
When SEVERE drift is detected in any model, that model's outputs are flagged DRIFT_DEGRADED and given reduced weight until the model is recalibrated.
*Rationale: Using a severely drifted model as if it were accurate is worse than using no model.*

**LC-F-003: Drift Root Cause Required**
A drift recalibration proposal must include a root cause hypothesis for the drift (regime change, data distribution shift, concept shift). Root cause unknown is an acceptable hypothesis but must be explicitly documented.
*Rationale: Recalibrating without understanding why drift occurred may produce a model that drifts again immediately.*

---

### IX.8 Category G: Validation Rules

**LC-G-001: 5-Stage Validation Non-Negotiable**
All learning outputs proceed through the 5-stage validation pipeline. No stage may be skipped, even for TIER-1-AUTO outputs.
*Rationale: TIER-1-AUTO means the approval is automatic; it does not mean validation is skipped.*

**LC-G-002: Validation Independence**
The entity that discovers a pattern is not the entity that validates it. The Pattern Discovery Engine discovers; the Learning Validation Manager validates.
*Rationale: Self-validation is a form of confirmation bias. Independent validation provides the second opinion.*

**LC-G-003: Validation Circuit Breaker**
If the validation pass rate for any learning type falls below 10% over a rolling 30-day window, a validation circuit breaker is activated for that learning type. All new outputs from that type are held pending investigation.
*Rationale: A 10% pass rate indicates the discovery process is generating poor-quality candidates. Continuing to process them wastes resources and clogs the governance pipeline.*

**LC-G-004: Validation History Required**
The full history of all validation attempts (pass and fail) for every learning output is permanently archived.
*Rationale: Understanding why outputs fail validation improves the discovery process over time.*

---

### IX.9 Category H: Governance Rules

**LC-H-001: Governance Before Deployment**
No learning output is applied to any IIOS component without passing through the governance approval pipeline.
*Rationale: Deployment without governance is an uncontrolled change to a live trading system.*

**LC-H-002: TIER Assignment Non-Negotiable**
Governance tier assignment cannot be downgraded by any algorithm or configuration. A TIER-3-HUMAN output cannot be auto-approved even if the system is under time pressure.
*Rationale: Governance tier assignment reflects the risk level of the change. Downgrading tier introduces unacceptable risk.*

**LC-H-003: Governance Backlog Limit**
If the governance approval queue exceeds 50 items, new TIER-1-AUTO and TIER-2-ADVISORY items are paused. TIER-3-HUMAN items are escalated immediately.
*Rationale: An unbounded governance queue means important items may wait too long while low-priority items consume review capacity.*

**LC-H-004: Kill Switch Exempt from Learning**
The Kill Switch mechanism, its activation thresholds, its persistence behavior, and its human-only deactivation requirement are not subject to learning updates of any kind.
*Rationale: Kill Switch is an absolute safety mechanism. Learning cannot improve safety mechanisms by weakening them.*

**LC-H-005: Constitutional Rules Exempt from Learning**
Constitutional rules across all IIOS engines cannot be modified by learning outputs.
*Rationale: Constitutional rules are the architectural invariants of the system. They are not empirical claims; they are design commitments.*

---

### IX.10 Category I: Auditability

**LC-I-001: All Learning Events Audited**
Every learning lifecycle state transition, every governance decision, every knowledge update, and every rollback is recorded in the Learning Audit Log.
*Rationale: Without a complete audit trail, it is impossible to determine why the system's intelligence changed.*

**LC-I-002: Audit Log Append-Only**
The Learning Audit Log is append-only. Existing records are never modified or deleted.
*Rationale: A mutable audit log provides no forensic guarantee.*

**LC-I-003: Hash Chain Mandatory**
All Learning Audit Log entries are hash-chain-linked using SHA-256. Chain integrity is verified at startup and periodically during operation.
*Rationale: Hash chain provides tamper detection — any modification to the audit log is immediately detectable.*

**LC-I-004: Audit Failure Halts Updates**
If the Learning Audit Manager is unavailable or detects a hash chain breach, all knowledge updates are halted until the audit infrastructure is restored and verified.
*Rationale: Unaudited updates cannot be traced, verified, or reversed.*

---

### IX.11 Category J: Historical Preservation

**LC-J-001: No Deletion**
No learning record, pattern, model version, or knowledge catalog entry is ever deleted from the archive. Retirement and archiving are the terminal states; deletion is not a valid state.
*Rationale: Deleted history cannot be used for forensic analysis, model re-training, or compliance review.*

**LC-J-002: Minimum Retention**
All learning records are retained for a minimum of 3 years.
*Rationale: Multi-year retention allows walk-forward analysis over full market cycles.*

**LC-J-003: Historical State Reconstruction**
The archive is structured to support reconstruction of the complete knowledge state at any historical date.
*Rationale: Counterfactual analysis ("what would performance have been with 2025 knowledge?") requires state reconstruction capability.*

---

### IX.12 Category K: Human Override

**LC-K-001: Override Always Available**
Human operators can override any learning output, halt any knowledge update, or rollback any deployed update at any time.
*Rationale: The learning system is an assistant; the human operator is the authority.*

**LC-K-002: Override Recorded and Analysed**
Every human override of a learning output is recorded and eventually analysed to determine whether the override revealed a flaw in the learning process.
*Rationale: Human overrides are themselves learning events. They reveal cases where the automated learning was wrong.*

**LC-K-003: Override Does Not Suppress Signal**
A human override of a specific learning output does not suppress the underlying signal from the learning pipeline. The signal continues to be processed; only the specific output is overridden.
*Rationale: The signal may be correct even if the proposed action was wrong. Suppressing the signal prevents future similar learning.*

---

### IX.13 Category L: Security

**LC-L-001: External Injection Prohibited**
Learning signals are accepted only from registered IIOS layer components via the EventBus. No external system may inject learning signals.
*Rationale: External injection would allow manipulation of the IIOS knowledge base by unauthorized parties.*

**LC-L-002: Credentials Not Logged**
All audit log entries are checked to ensure they contain no credential data, broker tokens, or API keys.
*Rationale: Credential exposure in logs is a security violation (OWASP).*

**LC-L-003: Knowledge Access Controlled**
Read access to the learning catalog and audit log requires OPERATOR level authentication. Write access is restricted to internal Learning Engine components.
*Rationale: Unauthorized modification of the knowledge base is a critical security risk.*

---

### IX.14 Category M: Quality Control

**LC-M-001: LQS Minimum for Deployment**
No learning output with LQS < 0.55 (below ACCEPTABLE tier) is approved for deployment, regardless of governance tier.
*Rationale: The LQS threshold is the quality gate. Below ACCEPTABLE quality, the risk of deploying incorrect knowledge outweighs the potential benefit.*

**LC-M-002: Rollback Trigger**
A deployed learning output is automatically flagged for rollback review if the target metric degrades by more than 5% in the 5 sessions following deployment.
*Rationale: Early performance degradation after a deployment is a strong signal that the update was incorrect.*

**LC-M-003: Learning Type Quality Monitoring**
The validation pass rate for each learning type (LT-01 through LT-21) is monitored continuously. Types with consistently low pass rates are investigated and potentially suspended.
*Rationale: A learning type that consistently produces poor-quality outputs is consuming governance capacity without delivering value.*

---

### IX.15 Category N: Continuous Improvement

**LC-N-001: Meta Learning Always Active**
Meta Learning (LT-20) is never suspended. The Learning Engine must always be learning about its own effectiveness.
*Rationale: Without meta learning, the Learning Engine cannot improve its own processes.*

**LC-N-002: Quarterly Bias Audit**
The Bias Detector's detection repertoire is reviewed and expanded quarterly to include newly identified bias patterns.
*Rationale: New biases emerge as the system evolves. Quarterly review prevents bias blind spots from becoming permanent.*

**LC-N-003: Annual Knowledge Review**
All ACTIVE knowledge items in the Learning Catalog are reviewed annually to confirm they remain valid and applicable.
*Rationale: Old knowledge that is no longer applicable in current market conditions must be retired. Annual review prevents stale knowledge accumulation.*

---

## PART X — LEARNING READINESS CHECKLIST

### X.1 Purpose

The Learning Readiness Checklist defines the conditions that must be satisfied before the Learning Engine is considered operationally ready for a trading session. It also defines the readiness matrix for each use case.

---

### X.2 Pre-Session Readiness Checklist

**Section 1: Infrastructure Readiness**

| Check | Expected | Failure action |
|---|---|---|
| Storage Layer reachable | Response < 200ms | Abort learning; alert operator |
| Learning Registry loadable | Registry responds | Abort; alert operator |
| Learning Audit Log hash chain valid | Chain intact | Abort; security alert |
| EventBus connection active | Heartbeat received | Abort; alert operator |
| All 21 components activated in sequence | All HEALTHY | Degrade; continue with reduced capability; alert |

---

**Section 2: Data Readiness**

| Check | Expected | Failure action |
|---|---|---|
| Previous session outcomes loaded | All closed trades from prior session available | Warn; proceed with partial outcome data |
| Market regime context available | Regime classification from MarketIntelligence | Warn; process records with REGIME_UNKNOWN tag |
| Strategy performance data current | StrategyPerformanceTracker data for last 7 days | Warn; proceed; flag strategy learning as DEGRADED |
| Error log from prior session reviewed | Error Analyzer processed all errors | Warn; defer error learning to intra-session |

---

**Section 3: Knowledge Readiness**

| Check | Expected | Failure action |
|---|---|---|
| Learning Catalog consistent | No conflicting ACTIVE entries | Halt; resolve conflicts before proceeding |
| All PENDING_HUMAN_APPROVAL items reviewed | Queue empty or operator aware | Notify operator |
| Rollback candidates cleared | No deployed updates flagged for rollback review | Process rollback reviews; notify operator |
| Pending governance items reviewed | TIER-3 queue empty or acknowledged | Notify operator |

---

**Section 4: Validation Readiness**

| Check | Expected | Failure action |
|---|---|---|
| Validation circuit breakers inactive | No learning type in circuit breaker state | Investigate; proceed with degraded learning for affected type |
| Out-of-sample data available | Most recent 20% of history reserved and accessible | Warn; fall back to in-sample-only validation (flag outputs) |
| Bias detector calibration current | Last calibration < 90 days | Schedule quarterly recalibration |

---

**Section 5: Governance Readiness**

| Check | Expected | Failure action |
|---|---|---|
| Governance pipeline empty | No stale items older than 72 hours | Escalate stale items; notify operator |
| Human approval channel active | Telegram bot responsive | Alert; TIER-3/4 decisions require manual approval |
| Auto-approval thresholds current | TIER-1/2 bounds within last review cycle | Use defaults if stale |

---

**Section 6: Pattern and Model Readiness**

| Check | Expected | Failure action |
|---|---|---|
| Active pattern catalog loaded | All ACTIVE patterns available | Abort if catalog unavailable |
| Drift detection active for all models | All models registered with Drift Detector | Warn; activate monitoring for missing models |
| Model performance baselines current | Rolling baselines from last 30 sessions | Warn; use extended baselines |
| Knowledge update history loaded | All deployed updates with rollback capability | Abort if rollback capability unavailable |

---

### X.3 Intraday Readiness Checks

During trading hours, the Learning Engine performs continuous readiness monitoring:

| Check | Frequency | Alert threshold |
|---|---|---|
| Learning Collector signal rate | Continuous | Alert if signal rate drops to 0 for > 5 minutes |
| Learning Registry write latency | Every 60s | Alert if > 500ms |
| Pattern Discovery Engine active | Every 5 min | Alert if no activity for > 30 min |
| Audit log write success | Continuous | Alert if any write fails |
| Governance queue size | Every 10 min | Alert if TIER-3 queue > 5 items |
| Learning Health Score | Every 30s | Alert if LSHS < 0.70 |

---

### X.4 Post-Session Readiness

After the trading session ends (after 15:30 IST), the Learning Engine performs end-of-session processing. This must complete before the next session's pre-session checks run.

| Step | Component | Expected duration |
|---|---|---|
| Collect all session outcome signals | Learning Collector | < 5 min |
| Process all session learning records | Learning Processor | < 15 min |
| Run Outcome Analyzer on all closed trades | Outcome Analyzer | < 10 min |
| Run Performance Analyzer session report | Performance Analyzer | < 5 min |
| Run Error Analyzer on session errors | Error Analyzer | < 5 min |
| Run Bias Detector scan on session patterns | Bias Detector | < 10 min |
| Produce session LQS report | Learning Analytics Manager | < 5 min |
| Archive all terminal-state records | Learning Archive Manager | < 10 min |
| Produce session recommendations | Learning Recommendation Manager | < 5 min |

**Total post-session processing target:** < 60 minutes

---

### X.5 Readiness Matrix

| Use Case | Required sections | Minimum LSHS | Acceptable degradation |
|---|---|---|---|
| Standard trading session | All 6 sections | > 0.75 | One DEGRADED component permitted |
| Post-incident recovery session | All 6 sections + extended validation | > 0.80 | No degradation |
| Paper trading session | Sections 1, 2, 3 | > 0.60 | Multiple DEGRADED components permitted |
| Backtesting support | Sections 1, 2 | > 0.50 | Full degradation permitted except Audit |
| Strategy evaluation | Sections 1, 2, 3, 4 | > 0.70 | Minor degradation permitted |
| Emergency session (Kill Switch active) | Section 1 only | > 0.50 | No learning updates; monitoring only |

---

### X.6 Readiness State Machine

`
         [SYSTEM_STARTING]
                |
                v
     [INFRASTRUCTURE_CHECK]
          /           \
    FAIL               PASS
     |                   |
     v                   v
[ABORT_WITH_ALERT]   [DATA_CHECK]
                      /       \
                 FAIL           PASS
                  |               |
                  v               v
              [DEGRADED]     [KNOWLEDGE_CHECK]
              (alert, proceed)   /        \
                            FAIL           PASS
                              |              |
                              v              v
                       [ABORT: CATALOG]  [VALIDATION_CHECK]
                       INCONSISTENCY          |
                                              v
                                     [GOVERNANCE_CHECK]
                                              |
                                              v
                                   [PATTERN_MODEL_CHECK]
                                              |
                                              v
                                  [LEARNING_ENGINE_READY]
`

---

## SUPPLEMENT A — LEARNING TAXONOMY REFERENCE

### A.1 Learning Type Classification Matrix

| Code | Name | Temporal scope | Signal frequency | Update frequency | Impact tier |
|---|---|---|---|---|---|
| LT-01 | Observation Learning | Intraday to Weekly | High | Weekly | LOW |
| LT-02 | Evidence Learning | Intraday to Weekly | High | Weekly | MEDIUM |
| LT-03 | Hypothesis Learning | Intraday to Monthly | Medium | Monthly | MEDIUM |
| LT-04 | Reasoning Learning | Session to Monthly | Medium | Monthly | HIGH |
| LT-05 | Decision Learning | Session to Monthly | Medium | Monthly | HIGH |
| LT-06 | Execution Learning | Intraday to Weekly | High | Weekly | MEDIUM |
| LT-07 | Outcome Learning | Session to Quarterly | Medium | Weekly | HIGH |
| LT-08 | Risk Learning | Session to Quarterly | Low | Monthly | CRITICAL |
| LT-09 | Portfolio Learning | Weekly to Quarterly | Low | Monthly | HIGH |
| LT-10 | Strategy Learning | Session to Quarterly | Medium | Weekly | CRITICAL |
| LT-11 | Behavioral Learning | Session to Monthly | Medium | Monthly | MEDIUM |
| LT-12 | Market Learning | Intraday to Monthly | High | Monthly | HIGH |
| LT-13 | Macro Learning | Daily to Quarterly | Low | Monthly | MEDIUM |
| LT-14 | Sector Learning | Weekly to Quarterly | Low | Monthly | MEDIUM |
| LT-15 | Company Learning | Session to Yearly | Low | Monthly | LOW |
| LT-16 | Cross-Market Learning | Daily to Quarterly | Low | Quarterly | MEDIUM |
| LT-17 | Cross-Asset Learning | Daily to Quarterly | Low | Quarterly | MEDIUM |
| LT-18 | AI Learning | Session to Monthly | Medium | Monthly | HIGH |
| LT-19 | Human Feedback Learning | Session | Low | Per feedback | CRITICAL |
| LT-20 | Meta Learning | Session to Monthly | Low | Monthly | HIGH |
| LT-21 | Error Learning | Intraday to Monthly | Medium | Weekly | HIGH |

---

### A.2 Learning Type to IIOS Layer Mapping

| Learning Type | Primary IIOS Layers Affected | Learning flows to |
|---|---|---|
| LT-01 Observation | Layer 1 (Observation), Layer 2 (Evidence) | Evidence Engine source weights |
| LT-02 Evidence | Layer 2 (Evidence Engine) | Evidence confidence multipliers |
| LT-03 Hypothesis | Layer 3 (Hypothesis Engine) | Hypothesis confidence priors |
| LT-04 Reasoning | Layer 4 (Reasoning Engine) | Inference chain weights |
| LT-05 Decision | Layer 5 (Decision Engine) | DCS calibration |
| LT-06 Execution | Layer 11 (Execution Engine) | Execution parameters |
| LT-07 Outcome | Layer 12 (TradeMonitoring) | Risk and strategy parameters |
| LT-08 Risk | Layers 6, 7, 9 (Risk layers) | Risk thresholds (via governance) |
| LT-09 Portfolio | Layer 7 (RiskControl/Portfolio) | Allocation rules |
| LT-10 Strategy | Layers 3, 5 (MetaLearning, StrategyLab) | Strategy weights |
| LT-11 Behavioral | All layers | Behavioral rules |
| LT-12 Market | Layer 2 (MarketIntelligence) | Regime models |
| LT-13 Macro | Layer 1 (GlobalIntelligence) | Global indicator weights |
| LT-14 Sector | Layer 2 (MarketIntelligence) | Sector rotation models |
| LT-15 Company | Layer 4 (OpportunityEngine) | Instrument alpha scoring |
| LT-16 Cross-Market | Layers 1, 2 | Cross-market signal models |
| LT-17 Cross-Asset | Layers 6, 7 (Capital, Risk) | Correlation models |
| LT-18 AI | All AI components | AI model calibration |
| LT-19 Human Feedback | All layers | Governance calibration |
| LT-20 Meta | Layer 13 (Learning Engine) | Learning process calibration |
| LT-21 Error | All layers | Prevention rules |

---

## SUPPLEMENT B — PATTERN CATALOGUE

### B.1 Purpose

This supplement defines the structure of the Pattern Catalogue and provides a reference catalogue of well-known pattern classes that the Pattern Discovery Engine is configured to detect.

---

### B.2 Pattern Record Structure

Every pattern in the Learning Catalog has the following structure:

| Field | Description | Example |
|---|---|---|
| Pattern ID | Unique identifier | PAT-STRATEGY-20260101-000001 |
| Pattern class | Classification code | STRATEGY_OUTCOME_TREND |
| Learning type | LT code | LT-10 |
| Domain | What domain does this pattern address | Strategy performance |
| Regime applicability | Which market regimes | TRENDING_BULL |
| Discovery date | When first discovered | 2026-01-01 |
| Instance count | Number of confirming instances | 47 |
| Confidence score | Calibrated confidence | 0.78 |
| Effect size | Measured improvement | +6.2% win rate |
| Status | Lifecycle status | ACTIVE |
| Description | Plain-language description | "STR-MOMENTUM strategies outperform by 6% in early BULL regimes" |
| Knowledge update | What update this pattern drives | MetaLearning weight +0.05 for MOMENTUM strategies in BULL |
| Validation history | IDs of validation runs | [VAL-000001, VAL-000002] |
| Deployment history | When and where deployed | [KU-METALRN-20260201-000001] |

---

### B.3 Known Pattern Classes

**STRATEGY_OUTCOME_TREND**
Recurring trend in strategy performance over time. Examples:
- "STR-X has been declining in win rate for 15+ consecutive sessions" → demotion candidate
- "STR-Y wins at 65%+ in TRENDING regimes but 40% in RANGING" → regime-specific weight adjustment

**DCS_CALIBRATION_ERROR**
The Decision Confidence Score is systematically wrong for a tier. Examples:
- "DCS 0.70-0.80 decisions are winning at 45% (not 70-80%)" → confidence model recalibration
- "DCS 0.90+ decisions are performing no better than DCS 0.70" → high-confidence overfit

**EQS_BY_TIME**
Execution quality degrades at specific times. Examples:
- "EQS drops 15% in the first 15 minutes after market open" → delay MEDIUM urgency orders in opening period
- "Friday afternoon executions have 2x average slippage" → switch to LIMIT from MARKET on Friday afternoons

**SLIPPAGE_BY_INSTRUMENT**
Instrument-specific slippage patterns. Examples:
- "TATASTEEL MARKET orders slip 0.25% vs 0.10% average" → increase TATASTEEL slippage prior
- "NIFTY futures slip < 0.05% at all times" → MARKET orders acceptable for NIFTY

**REGIME_TRANSITION_SIGNAL**
Leading indicators for regime transitions. Examples:
- "When INDIA_VIX spikes > 20%, a BULL→BEAR transition follows within 3 sessions in 78% of cases"
- "When BANKNIFTY outperforms NIFTY by > 1.5% for 3 consecutive sessions, a SECTOR_ROTATION pattern follows"

**MAE_STOP_BREACH**
Stop losses are consistently being triggered too early or too late. Examples:
- "15% of TATASTEEL LONG trades are stopped out at -1.5% but would have recovered to +2% within 2 sessions" → widen stop
- "STR-BREAKOUT trades reach -5% MAE before any stop is triggered" → stop placement model recalibration

**EVIDENCE_SOURCE_RELIABILITY**
Specific evidence sources are consistently inaccurate. Examples:
- "Options flow data from source X has 40% accuracy in predicting moves > 1%" → downweight source X
- "Futures premium data predicts spot direction with 72% accuracy in BULL regimes" → increase weight

**HUMAN_OVERRIDE_PATTERN**
Human operators consistently override specific decision types. Examples:
- "Operator has overridden 8 of the last 10 STR-SHORT-SELLING decisions" → STR confidence model may be wrong for this operator
- "All operator overrides of TIER-2-ADVISORY items involved BANKING sector" → BANKING sector model may need recalibration

**ERROR_RECURRENCE**
Specific errors occur in a pattern. Examples:
- "Connectivity timeout errors cluster between 09:15-09:20 IST" → broker reconnection logic needs improvement for market-open period
- "Order rejection rate spikes when INDIA_VIX > 25" → position size reduction in high-volatility periods

---

### B.4 Pattern Confidence Calibration Reference

| Confidence tier | Meaning | Minimum instances | Maximum age |
|---|---|---|---|
| VERY_HIGH (0.90-1.00) | Extremely consistent pattern; held across multiple regimes | 50+ | 6 months |
| HIGH (0.75-0.89) | Strong pattern; validated across at least 2 regimes | 25+ | 6 months |
| MEDIUM (0.55-0.74) | Valid pattern; regime-specific or moderate effect size | 10+ | 3 months |
| LOW (0.35-0.54) | Weak pattern; experimental; needs more evidence | 10 | 1 month |
| CANDIDATE (< 0.35) | Below threshold; not deployed | Any | Active accumulation |

---

## SUPPLEMENT C — FEEDBACK MODELS

### C.1 Feedback Model Architecture

The Feedback Manager implements four distinct feedback models. Each model governs how a specific type of feedback signal is collected, attributed, weighted, and processed.

---

### C.2 Model FM-01: Trade Outcome Feedback

**Signal:** Realised PNL, MAE, MFE, holding period for each closed trade.
**Attribution:** Trade outcome attributed to: strategy (which generated the signal), decision (which committed the execution), execution (which filled the order).
**Weighting:**
Lengthw_{PNL} = \frac{|PNL|}{daily\_avg\_PNL} \times regime\_reliability \times confidence\_weightLength
**Decay function:** Exponential decay with half-life of 60 sessions.
**Paradox detection:** Triggered when two trades with similar decision parameters produce outcomes > 3 standard deviations apart.

---

### C.3 Model FM-02: Execution Quality Feedback

**Signal:** EQS per execution (12 dimensions).
**Attribution:** EQS attributed to: order type, instrument, time of day, broker, regime.
**Weighting:** Proportional to order value (larger trades weighted more heavily in calibration).
**Decay function:** No decay; execution quality data is timeless (order type preferences do not depend on regime).
**Update target:** Execution Engine order type selection, slippage priors, broker routing.

---

### C.4 Model FM-03: Strategy Performance Feedback

**Signal:** Per-strategy win rate, Sharpe ratio, maximum drawdown across sessions.
**Attribution:** Attributed to strategy ID and regime at time of signal generation.
**Weighting:** Rolling 30-session window, equal-weighted within window.
**Decay function:** Hard cutoff at 90 sessions (sessions older than 90 sessions not included in current window).
**Update target:** MetaLearning strategy weights; StrategyLab evolution parameters.

---

### C.5 Model FM-04: Human Feedback

**Signal:** Operator override action, operator annotation, operator-submitted correction.
**Attribution:** Attributed to the specific decision, strategy, or learning output that was overridden or corrected.
**Weighting:** Human feedback weight = 3x automated feedback weight of equivalent signal strength.
**Decay function:** No decay; human feedback is treated as permanent calibration signal.
**Update target:** All components the human override relates to; governance calibration.

---

## SUPPLEMENT D — KNOWLEDGE EVOLUTION EXAMPLES

### D.1 Example: Strategy Weight Recalibration

**Starting state (Session SES-20260101-0001):**
STR-MOMENTUM_BREAKOUT_002 weight in MetaLearning: 0.18 (ranked #2 of 12 active strategies).
Regime: TRENDING_BULL.

**Outcome data (sessions SES-20260101 to SES-20260130):**
30 sessions of outcomes recorded.
Win rate: 52% (below STR minimum of 55% for sustained TRENDING_BULL period).
Sharpe ratio: 0.72 (below minimum of 0.8 for demotion consideration threshold).

**Learning Engine action:**

1. Outcome Analyzer flags STR-MOMENTUM_BREAKOUT_002: win rate declining trend detected (3 consecutive months below target).
2. Pattern Discovery Engine: STRATEGY_OUTCOME_TREND pattern: "STR-MOMENTUM_BREAKOUT_002 underperforming in TRENDING_BULL since NIFTY > 23,500" — possible correlation with high-valuation environment.
3. Knowledge Extraction: propose weight reduction from 0.18 to 0.13 (-0.05 delta).
4. Validation: LQS 0.82 (GOOD); passes all 5 stages including out-of-sample test on prior 6-month period.
5. Governance: TIER-2-ADVISORY (weight change 5%, strategy not demoted); auto-approved; operator notified.
6. Deployment: MetaLearning weight updated from 0.18 to 0.13.
7. Monitoring: 5 sessions of post-deployment monitoring initiated.
8. Outcome: Subsequent 5 sessions show stable IIOS performance without STR-MOMENTUM_BREAKOUT_002 over-contribution.

---

### D.2 Example: Decision Confidence Model Recalibration

**Discovery:** Decision Learning (LT-05) detects that DCS 0.75-0.85 decisions (which should win ~75-85% of the time by calibration) are actually winning at 58%.

**Impact:** System is overestimating confidence in a significant tier of decisions. This means it is deploying more capital to lower-quality decisions than it should.

**Resolution:**
1. Pattern Discovery Engine: DCS_CALIBRATION_ERROR pattern confirmed (47 instances; p < 0.001).
2. Model Improvement Manager: proposes DCS model recalibration — reduce the 0.75-0.85 tier's effective weight in capital sizing by 15%.
3. Validation: walk-forward test on last 90 sessions; out-of-sample test passes.
4. Governance: TIER-3-HUMAN (model structural change); human operator reviews evidence and approves.
5. Deployment: confidence model parameters updated.
6. Monitoring: 10 sessions. Observed win rate for DCS 0.75-0.85 tier: 62% (improvement; not yet fully calibrated — further learning continues).

---

### D.3 Example: New Pattern: Sector Rotation

**Discovery (LT-14 Sector Learning):**
12 weeks of sector performance data shows: when the BANKING sector (HDFCBANK, ICICIBANK) outperforms the METALS sector (TATASTEEL, JSWSTEEL) by > 2% over 5 consecutive sessions, a SERVICES_OUTPERFORMANCE pattern follows in the next 3-8 sessions with 74% frequency.

**Learning lifecycle:**
1. Pattern Discovery: PAT-SECTOR-20260601-000012 — SECTOR_ROTATION_BANKING_TO_SERVICES
2. Instance count: 16 (minimum 10 ✅); p-value: 0.023 ✅; effect size: +8.4% alpha on SERVICES stocks ✅
3. Out-of-sample test: held-out last 3 occurrences — 2 of 3 confirmed ✅
4. Regime: applicable in TRENDING_BULL and RANGING regimes
5. Validation: LQS 0.79 (GOOD)
6. Governance: TIER-2-ADVISORY; auto-approved; operator notified
7. Deployment: OpportunityEngine sector rotation signal sensitivity increased for this pattern

---

## SUPPLEMENT E — BIAS AND DRIFT EXAMPLES

### E.1 Bias Example: Recency Bias in Strategy Assessment

**Description:** After a particularly strong week for STR-MEAN_REVERSION_007 (5 wins in 5 trades), the Feedback Manager's rolling window starts to show STR-MEAN_REVERSION_007 as the top-performing strategy, displacing STR-BREAKOUT_MOMENTUM_001 which has a stronger 30-session track record.

**Detection:** Bias Detector identifies recency overweighting: the 5-session window is exceeding its governing influence relative to the 30-session window.

**Mitigation:** Recency Bias dampening rule (LC-E-004): the 5-session performance contributes at most 15% of the total feedback weight for strategy ranking. The 30-session window contributes 60%.

---

### E.2 Bias Example: Survivorship Bias in Pattern Analysis

**Description:** The Pattern Discovery Engine is mining trade records to find conditions that precede profitable trades. It discovers that a specific MACD crossover pattern precedes profitable trades in 72% of cases. However, the database being mined contains only trades that were actually executed — not all signals that were generated. Many signals that would have led to losses were filtered out by governance checks before execution.

**Detection:** Bias Detector: SURVIVORSHIP_BIAS flagged — pattern discovery dataset contains only executed (filtered) trades. The 72% figure applies to survived-governance trades, not all potential trades.

**Mitigation:** Pattern Discovery Engine is required to access the full signal record (including rejected signals) for pattern mining, not only the executed trade record.

---

### E.3 Bias Example: Confirmation Bias in Evidence Assessment

**Description:** The system has developed a strong BULL market hypothesis. When new evidence arrives that contradicts the BULL hypothesis (e.g., weak FII data, declining advance-decline ratio), the Evidence Engine is downweighting it. When confirming evidence arrives (e.g., strong IT sector performance), it is overweighted.

**Detection:** Bias Detector: CONFIRMATION_BIAS flag — evidence weights are significantly asymmetric between confirming and contradicting signals relative to their historical reliability.

**Mitigation:** Evidence weights are re-normalised; a symmetric evidence update rule is enforced.

---

### E.4 Drift Example: Concept Drift in Regime Classifier

**Description:** The regime classifier was trained on data from 2020-2024. The IIOS is now in 2026. The classification boundaries that separate TRENDING_BULL from RANGING in the NIFTY have shifted: what was previously classified as a ranging NIFTY (flat 200-point range) is now a standard-deviation move in a lower-volatility environment.

**Detection:** Drift Detector: CONCEPT_DRIFT flagged — regime classifier prediction accuracy has declined from 78% to 61% over the last 30 sessions.

**Mitigation:** Model Improvement Manager: regime classifier recalibration initiated. New regime boundaries proposed based on rolling volatility adjustment. Walk-forward validation confirms improvement. TIER-3-HUMAN approval obtained.

---

### E.5 Drift Example: Data Drift in Evidence Source

**Description:** An evidence source (options open interest data) was historically scraped at 14:30 IST and reflected intraday build-up. A change in data delivery means it now arrives at 15:15 IST, reflecting end-of-day positioning. The statistical distribution of the values has changed, but the model using the evidence was not aware of the source change.

**Detection:** Drift Detector: DATA_DRIFT flagged — statistical distribution of options_open_interest feature has shifted (mean +15%, variance -30% vs training distribution).

**Mitigation:** Evidence source metadata updated; evidence reliability recalibrated for the new delivery time; model retrained with awareness of the temporal shift.

---

## SUPPLEMENT F — ANTI-PATTERNS

### F.1 Purpose

Anti-patterns are known failure modes in learning system design. This supplement documents the anti-patterns that the IIOS Learning Engine is explicitly designed to avoid. Each anti-pattern has a description, the harm it causes, and the safeguard in the IIOS architecture that prevents it.

---

### F.2 Anti-Pattern AP-01: Perpetual Learning Loop

**Description:** The Learning Engine generates a knowledge update, deploys it, the update changes system behavior, the changed behavior generates new learning signals, which generate another update, and so on in an accelerating loop.

**Harm:** The system destabilizes. Performance oscillates. Parameter changes are too frequent to evaluate. The system becomes impossible to diagnose.

**IIOS Safeguard:**
- Minimum monitoring period of 5 sessions before a new update to the same parameter is considered (LC-A-006 reversibility + monitoring requirement)
- Maximum update frequency per parameter dimension: 1 update per 7 sessions
- Rollback trigger at 5% performance degradation prevents bad updates from persisting

---

### F.3 Anti-Pattern AP-02: Ghost Knowledge

**Description:** Knowledge items in the catalog that are no longer applicable to current market conditions but are still ACTIVE. The system continues to use them, degrading performance without an obvious reason.

**Harm:** Stale knowledge produces wrong decisions. Performance declines gradually without a clear trigger event.

**IIOS Safeguard:**
- Annual knowledge review of all ACTIVE items (LC-N-003)
- Drift Detector monitoring: stale knowledge in a drifted regime will trigger a drift alert
- Pattern confidence decay: patterns that are not being reinforced by new evidence gradually lower in confidence until they reach the CANDIDATE threshold and are re-evaluated

---

### F.4 Anti-Pattern AP-03: The Knowledgeable Fool

**Description:** The Learning Engine discovers many patterns and deploys them aggressively. The system becomes "knowledgeable" with hundreds of active patterns, but the sheer volume of patterns creates conflicting rules and inconsistent behavior.

**Harm:** Over-constrained behavior. Too many rules conflict; the system becomes paralyzed trying to satisfy all constraints. Performance degrades despite (or because of) abundant "knowledge."

**IIOS Safeguard:**
- Pattern catalog size monitoring: alert if active pattern count exceeds threshold for a domain
- Effect size minimum (LC-C-005): only patterns with meaningful effect sizes are deployed
- Pattern deduplication: semantically equivalent patterns are merged, not stacked

---

### F.5 Anti-Pattern AP-04: Overfitted Oracle

**Description:** Models are recalibrated frequently on recent data. They become highly accurate on the training window but fail catastrophically on new data.

**Harm:** Models that appear well-calibrated in backtests fail in live trading. The walk-forward test is bypassed or insufficiently rigorous.

**IIOS Safeguard:**
- Out-of-sample test mandatory (LC-A-004, LC-G-001): 20% of pattern history is always reserved for out-of-sample testing
- Walk-forward validation required for all model recalibrations
- Minimum pattern age: recent-only patterns (< 2 months of data) receive LOW confidence tier regardless of in-sample statistics

---

### F.6 Anti-Pattern AP-05: The Amnesiac

**Description:** The Learning Engine does not preserve historical knowledge. When a strategy is retired, all its associated patterns and performance data are deleted. When a regime reappears, the system has no memory of how it behaved in that regime previously.

**Harm:** The system repeats mistakes from the past. Historical market patterns that recur are not recognised.

**IIOS Safeguard:**
- No deletion rule (LC-J-001): all records are permanently archived
- Historical state reconstruction capability: any past knowledge state can be reconstructed
- Retired pattern library: retired patterns are accessible for future comparison with new pattern candidates

---

### F.7 Anti-Pattern AP-06: Unilateral Structural Change

**Description:** A large learning update is applied automatically because the system classified it as TIER-1-AUTO, when the actual impact was TIER-3 or higher. A strategy weight shifts from 5% to 15% without human awareness.

**Harm:** Major changes without human oversight. If the change is wrong, it may cause significant losses before it is noticed.

**IIOS Safeguard:**
- Governance tier is determined by impact, not by convenience
- TIER assignment cannot be downgraded (LC-H-002)
- Bounded updates: Knowledge Updater enforces maximum delta per cycle
- Alert on all TIER-2 and above events: human operator always informed

---

### F.8 Anti-Pattern AP-07: Learning from Hallucinated Data

**Description:** The Learning Engine processes data that appears to be real outcomes but is actually artifacts of system errors (e.g., a fill event that was logged twice, a PNL calculation error, a regime misclassification).

**Harm:** The system learns from incorrect data and applies wrong updates. Performance degrades for undetectable reasons.

**IIOS Safeguard:**
- Data quality check (Stage 7a of validation pipeline): all data is validated before contributing to pattern discovery
- Learning Record quality score: low-quality records are flagged QUALITY_SUSPECT and excluded from pattern analysis
- Attribution validation: fill events are cross-checked against broker records; discrepancies flag the record as SUSPECT

---

### F.9 Anti-Pattern AP-08: Feedback Without Attribution

**Description:** Feedback signals are processed without being attributed to the specific decision, strategy, or system component that generated the associated action. The learning signal "trade lost money" is processed without knowing which strategy, which decision confidence tier, or which market regime was involved.

**Harm:** Unattributed feedback improves nothing. The system records the outcome but cannot direct learning to the correct component.

**IIOS Safeguard:**
- Attribution required (LC-D-001): all feedback is attributed before processing
- Unattributed feedback is held in PENDING_ATTRIBUTION queue; not processed until attributed
- Attribution coverage metric: tracked as a key performance indicator of the Feedback Manager

---

### F.10 Anti-Pattern AP-09: Learning Under Kill Switch

**Description:** The Kill Switch is active; the system is not trading. The Learning Engine continues to process market data and generates strategy weight updates based on market movements that the system was not participating in.

**Harm:** Strategy weights are updated based on a market period the system did not trade in. The performance data is phantom — not based on actual fills.

**IIOS Safeguard:**
- Kill Switch state is available to the Learning Engine
- During Kill Switch ACTIVE periods: Learning Engine collects signals but flags all market-based learning as KILL_SWITCH_PERIOD
- KILL_SWITCH_PERIOD records are downweighted in pattern discovery (the system was not trading; market moves do not reflect actual performance)

---

## SUPPLEMENT G — OPERATIONAL RUNBOOK

### G.1 Pre-Session Startup (07:30 IST)

**Component activation sequence:**

`
1.  Storage Layer
2.  Learning Audit Manager (must be active before any learning operations)
3.  Learning Registry
4.  Learning Catalog (load active catalog entries)
5.  Learning Archive Manager
6.  Feedback Manager (load attribution history)
7.  Pattern Discovery Engine (load active patterns and candidate patterns)
8.  Outcome Analyzer
9.  Performance Analyzer
10. Error Analyzer
11. Bias Detector
12. Drift Detector
13. Model Improvement Manager (load model monitoring baselines)
14. Learning Validation Manager
15. Learning Governance Manager (load pending approvals)
16. Knowledge Updater (load pending deployments)
17. Learning Collector (begin EventBus subscriptions)
18. Learning Processor
19. Learning Analytics Manager
20. Learning Recommendation Manager
21. Learning Health Manager
    [All 21 components active]
22. Emit: LEARNING_ENGINE_STARTED event to EventBus
23. Run pre-session readiness checklist (Sections 1-6)
24. If any CRITICAL failure: abort and alert
25. If DEGRADED: continue with reduced capability; alert operator
`

---

### G.2 Intraday Operations (09:15 - 15:30 IST)

**Continuous operations:**
- Learning Collector: ingest EventBus signals (fills, outcomes, errors, regime changes) in real-time
- Pattern Discovery Engine: incremental pattern scan every 15 minutes
- Drift Detector: model accuracy monitoring every 5 minutes
- Learning Health Manager: component health poll every 30 seconds
- Audit Manager: write all learning events in real-time

**Operator monitoring:**
- Check Learning Recommendation Manager dashboard every 60 minutes
- Review any IMMEDIATE recommendations via Telegram
- Review any pending TIER-3-HUMAN governance items

---

### G.3 End-of-Session Processing (15:30 - 17:00 IST)

`
1.  Close EventBus subscriptions for intraday signals
2.  Outcome Analyzer: process all closed trades from session
3.  Error Analyzer: process all session errors
4.  Performance Analyzer: session performance report
5.  Feedback Manager: attribute all session feedback signals
6.  Pattern Discovery Engine: full session scan (all session records)
7.  Bias Detector: scan all session patterns for bias
8.  Drift Detector: update model accuracy measurements with session data
9.  Learning Analytics Manager: produce session LQS report
10. Learning Recommendation Manager: produce session recommendation list
11. Archive all terminal-state records
12. Emit: LEARNING_SESSION_COMPLETE event to EventBus
`

---

### G.4 Recovery Procedures

**Recovery G-REC-001: Learning Registry Failure**
1. Learning Registry unavailable
2. Learning Collector: queue signals in memory buffer (max 1,000 records)
3. Alert operator
4. Restore registry from backup
5. Replay buffered records
6. Verify queue integrity

**Recovery G-REC-002: Audit Log Hash Chain Breach**
1. Hash chain integrity failure detected
2. ALL learning updates halted immediately
3. CRITICAL alert to operator via Telegram
4. Identify breach point in hash chain
5. Quarantine all records after breach point pending investigation
6. Human operator reviews and approves resolution path
7. DO NOT resume learning updates until audit integrity is confirmed

**Recovery G-REC-003: Pattern Discovery Engine Failure**
1. Pattern Discovery Engine crashes or stalls
2. Learning Health Manager detects FAILED status
3. Alert operator
4. No new patterns generated; existing active patterns remain valid
5. Restart Pattern Discovery Engine; reload state from last checkpoint
6. Resume incremental scanning from last processed record ID

**Recovery G-REC-004: Governance Backlog**
1. Governance queue exceeds 50 items
2. Learning Governance Manager: pause TIER-1 and TIER-2 processing
3. Alert operator to review TIER-3 and TIER-4 items
4. Operator clears high-priority items
5. Resume full processing when queue < 20 items

**Recovery G-REC-005: Bias Detection Alert**
1. Bias Detector identifies SIGNIFICANT bias in a learning output
2. Affected output quarantined (status: BIAS_SUSPECT)
3. Alert operator
4. Operator investigates bias source
5. If bias confirmed: reject output; retrain with bias-corrected data
6. If bias disputed: escalate to TIER-4-COMMITTEE for review

---

### G.5 Weekly Maintenance

| Task | Component | Requirement |
|---|---|---|
| Full pattern scan on complete history | Pattern Discovery Engine | Every weekend |
| Model drift baseline update | Drift Detector | Weekly (rolling baselines updated) |
| Governance queue review | Learning Governance Manager | Weekly |
| Bias detector coverage review | Bias Detector | Monthly (not weekly; calendar check) |
| Archive integrity verification | Learning Archive Manager | Weekly |
| LQS trend report | Learning Analytics Manager | Weekly |

---

## SUPPLEMENT H — GLOSSARY AND GOVERNING DESIGN RECORDS

### H.1 Glossary

**Accuracy (LQD-01):** The quality dimension measuring whether a learning output correctly describes the underlying pattern or calibration. A high accuracy score means the knowledge claim is factually correct when evaluated against ground truth.

**Active Learning:** A pattern or knowledge item in ACTIVE lifecycle status — validated, approved, deployed, and currently being monitored. All ACTIVE items are included in the system's operational knowledge base.

**Adaptation:** The behavioral change that results from applying a learning output. Learning produces knowledge; adaptation applies it. Without adaptation, learning has no effect.

**Anti-Pattern:** A known failure mode in learning system design. The IIOS architecture explicitly documents anti-patterns and provides safeguards against each.

**Attribution:** The process of linking a feedback signal or outcome to the specific decision, reasoning chain, hypothesis, or strategy that generated the associated action. Attribution is required before feedback can improve the correct component.

**Behavioral Learning (LT-11):** Learning from the IIOS system's own behavioral patterns — not market patterns, but system action patterns (e.g., over-trading at market open, systematic over-confidence on Fridays).

**Bias:** A systematic error in a learning process that produces consistently wrong outputs in a specific direction. The IIOS architecture identifies and guards against six primary bias types: confirmation, recency, survivorship, anchoring, regime confusion, and execution quality bias.

**Bias Detector (LC-12):** The Learning Engine component that systematically checks all learning outputs for known bias types before they proceed to governance approval.

**Candidate Pattern:** A pattern that has been initiated by the Pattern Discovery Engine but has not yet accumulated sufficient evidence (minimum 10 instances, p < 0.05, effect size > 5%) to proceed to validation.

**Concept Drift:** A type of model drift where the underlying relationship between inputs and outputs has changed. Different from data drift (the distribution of inputs changed) and model drift (the model became miscalibrated without the relationship changing).

**Confidence Calibration:** The process of ensuring that confidence scores accurately reflect actual outcome frequencies. A well-calibrated confidence score of 0.75 should correspond to a 75% win rate on decisions where that score was assigned.

**Continuous Learning:** Learning that operates without interruption. The IIOS Learning Engine is a continuous learner: it processes signals in real-time during trading hours and in batch mode between sessions. There is no session restart that resets learning state.

**Data Drift:** A type of model drift where the statistical distribution of input features has changed significantly from the training distribution. The model's parameters are no longer appropriate for the new input distribution.

**Decision Confidence Calibration Score (DCCS):** The metric measuring the correlation between Decision Confidence Score (DCS) and actual outcome frequency. A DCCS of 1.0 means perfect calibration; DCS 0.80 corresponds to 80% win rate.

**Decision Learning (LT-05):** The learning type that tracks the outcomes of COMMITTED Decision Packages and uses them to calibrate the Decision Engine's confidence scoring model.

**Drift:** The gradual change in model performance over time as market conditions evolve. Three types: concept drift, data drift, and model miscalibration drift.

**Drift Detector (LC-13):** The Learning Engine component that monitors quantitative models for drift using statistical process control techniques. Alerts the Model Improvement Manager when drift is detected.

**Effect Size:** The practical magnitude of an improvement. A pattern with statistically significant but tiny effect size (< 5% improvement) is not worth deploying. Effect size is LQD-12 (Improvement Impact).

**Error Learning (LT-21):** The learning type that analyses all system errors and anomalies to identify recurring patterns and root causes.

**Evidence Learning (LT-02):** The learning type that evaluates the predictive value of evidence signals and calibrates evidence confidence multipliers.

**Execution Learning (LT-06):** The learning type that analyses EQS data to improve execution parameters — order type selection, slippage priors, broker routing preferences.

**Explicit Learning:** Structured extraction of knowledge from labeled outcomes. In IIOS, explicit learning occurs when trade outcomes (positive/negative PNL) are used to train confidence models.

**Feedback Decay:** The process of reducing the weight of old feedback signals over time. Prevents the system from over-anchoring on historical conditions that may no longer apply.

**Feedback Manager (LC-08):** The Learning Engine component responsible for collecting, attributing, weighting, and processing all feedback signals.

**Generalization (LQD-03):** The quality dimension measuring whether a learning output applies beyond the specific examples from which it was derived. High generalization indicates robustness; low generalization indicates overfitting.

**Ghost Knowledge:** An anti-pattern where knowledge items that are no longer applicable to current market conditions remain ACTIVE in the catalog, causing performance degradation.

**Governing Design Record (GDR):** An immutable architectural decision that cannot be overridden by configuration, algorithm, or policy. GDRs for the Learning Engine are documented in Section H.2.

**Human Feedback Learning (LT-19):** The learning type that collects and analyses human operator overrides, annotations, and corrections, treating them as high-weight learning signals.

**Hypothesis Learning (LT-03):** The learning type that tracks hypothesis validation rates and calibrates the confidence assigned to each hypothesis type.

**Implicit Learning:** Passive extraction of patterns from unlabeled behavioral data. The Pattern Discovery Engine performs implicit learning — it discovers patterns without being told what to look for.

**Incremental Learning:** Building on existing knowledge without forgetting. IIOS strategy weights, model parameters, and patterns all update incrementally — new information refines the existing state rather than replacing it wholesale.

**Knowledge Catalog:** See Learning Catalog. The structured index of all validated, ACTIVE knowledge items.

**Knowledge Update Service (LS-03):** The service interface through which approved knowledge updates are applied to target layer components.

**Knowledge Updater (LC-06):** The component that translates approved learning outputs into specific updates to model parameters, strategy weights, and inference rules, and applies them to target components.

**Learning:** The transformation of experience into durable, actionable knowledge that improves future performance. The full definitional ladder is in Part I.

**Learning Archive Manager (LC-17):** The component managing the permanent archive of all historical learning records, superseded knowledge, and retired patterns.

**Learning Audit Manager (LC-16):** The component maintaining the immutable, hash-chain-linked audit log of all learning events.

**Learning Catalog (LC-02):** The structured classification index for all validated learning outputs, organised by type, domain, regime, confidence, and version.

**Learning Collector (LC-03):** The ingestion boundary of the Learning Engine; receives signals from all 17 IIOS layers.

**Learning Governance Manager (LC-15):** The approval authority for all learning outputs; enforces governance tiers and constitutional rules.

**Learning Health Manager (LC-18):** The component that monitors the health of all 21 Learning Engine components.

**Learning Processor (LC-04):** The transformation pipeline that enriches and routes raw Learning Records for pattern discovery and knowledge update.

**Learning Quality Score (LQS):** The composite quality metric for learning outputs. Computed as weighted sum of 12 quality dimensions. Tiers: EXCELLENT (0.85+), GOOD (0.70-0.84), ACCEPTABLE (0.55-0.69), MARGINAL (0.35-0.54), FAILED (< 0.35).

**Learning Record:** A structured representation of a learning event, created by the Learning Collector from a raw system signal. Has a unique ID in the format LRN-{TYPE}-{DATE}-{SEQ:08d}.

**Learning Recommendation Manager (LC-20):** The component that synthesises learning signals into prioritised, plain-language recommendations for human operators.

**Learning Registry (LC-01):** The operational store of all active and recent learning records with their lifecycle status.

**Learning System Health Score (LSHS):** The weighted aggregate health score of all 21 Learning Engine components. Reported to ControlTower.

**Learning Validation Manager (LC-14):** The component that runs the 5-stage validation pipeline on all candidate learning outputs.

**Meta Learning (LT-20):** Learning about learning — evaluating the effectiveness of the Learning Engine's own outputs and using this evaluation to improve the learning process.

**Model Drift:** Degradation in model prediction accuracy over time. Three types: concept drift, data drift, and model miscalibration.

**Model Improvement Manager (LC-07):** The component that monitors model performance, detects drift, and manages the model recalibration lifecycle.

**Novelty (LQD-02):** The quality dimension measuring whether a learning output adds genuinely new knowledge. Duplicate knowledge has low novelty.

**Organizational Learning:** System-wide adaptation that spans multiple layers — when a cross-layer problem is identified and coordinated multi-layer updates are required.

**Outcome Analyzer (LC-09):** The component that systematically analyses closed trade records to extract outcome patterns.

**Outcome Learning (LT-07):** The learning type that extracts actionable patterns from trade outcome data.

**Overfitted Oracle:** An anti-pattern where models are recalibrated so frequently on recent data that they overfit and fail on new data.

**Pattern:** A discovered, validated, statistically significant regularity in the Learning Engine's accumulated data. Every pattern has an ID, a confidence score, an effect size, a regime tag, and a lifecycle status.

**Pattern Discovery Engine (LC-05):** The core analytical component of the Learning Engine that scans Learning Records to discover candidate patterns.

**Performance Analyzer (LC-10):** The component that produces multi-dimensional performance analytics across all IIOS layers.

**Reasoning Learning (LT-04):** The learning type that tracks the quality of reasoning chains and adjusts inference chain weights based on outcome correlation.

**Reinforcement Learning (IIOS context):** Learning from reward signals. In IIOS, the reward signal is trade PNL. Strategy weights in MetaLearning are adjusted based on cumulative reward.

**Repeatability (LQD-04):** The quality dimension measuring whether a learning output is consistently produced from similar data. Low repeatability indicates a brittle discovery process.

**Rollback:** The restoration of a prior knowledge state after a deployed update is found to be harmful. All deployed updates in the IIOS are rollback-capable to the immediately prior version.

**Stability (LQD-05):** The quality dimension measuring whether a deployed learning output remains valid over time. High stability means the improvement holds for 20+ sessions.

**Strategy Learning (LT-10):** The most operationally important learning type. Tracks per-strategy performance across sessions and regimes; drives strategy weight adjustments and demotion/promotion recommendations.

**Supervised Learning (IIOS context):** Learning from outcome-labeled records. Trade outcomes (profit/loss) provide labels for training confidence models.

**Survivorship Bias:** A bias where only successful outcomes are analysed, ignoring failures. In IIOS, prevented by including rejected signals and failed strategies in all pattern analyses.

**Traceability (LQD-10):** The quality dimension measuring whether a learning output can be fully traced to its source data.

**Unsupervised Learning (IIOS context):** Learning structure from unlabeled patterns. The Pattern Discovery Engine performs unsupervised learning when it discovers patterns without predefined labels.

**Wisdom:** The judgment to know when to apply knowledge, when to discard it, and when to override it. The highest level of the definitional ladder. In IIOS, encoded in governance rules and human override authority.

---

### H.2 Governing Design Records

**GDR-LRN-001: Learning Never Replaces Governance**

No learning output — regardless of its quality score, confidence, or projected impact — may override constitutional rules, Kill Switch behavior, or human authority. Learning provides intelligence; governance provides authority. These are permanently separated.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-LRN-002: Evidence Before Update**

No knowledge update is applied without source-attributed, validated evidence supporting it. Manual knowledge assertions are not permitted. All knowledge claims must emerge from the discovery and validation pipeline.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-LRN-003: Incrementality Required**

Learning updates are incremental. No single learning event may change any parameter by more than a configured maximum step. Rapid, large parameter changes are prohibited regardless of the apparent quality of the driving evidence.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-LRN-004: Audit Before Update**

No knowledge update is applied until the Learning Audit Manager has recorded the update intent. If the Audit Manager is unavailable, updates are held until it is restored.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-LRN-005: No Deletion**

No learning record, pattern, model version, or knowledge item is ever deleted. The terminal states are ARCHIVED and RETIRED, not DELETED. Historical preservation is permanent.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-LRN-006: Human Override is Absolute**

A human operator may override any learning output, halt any knowledge update, or rollback any deployed update at any time without justification. The override is recorded and eventually analysed as a learning event in itself, but it is never contested.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-LRN-007: Kill Switch is Never Subject to Learning**

The Kill Switch mechanism — its activation logic, its persistence behavior, its deactivation requirement — is not subject to learning updates of any kind. No learning output may propose any change to Kill Switch behavior.

*Effective date: IIOS v1.0. Immutable.*

---

**GDR-LRN-008: Reversibility Required**

Every knowledge update has a rollback path. The system can restore any parameter to its pre-update state within one trading session. Updates without rollback capability are not deployed.

*Effective date: IIOS v1.0. Immutable.*

---

## APPENDIX: WORKED LEARNING EXAMPLES

### Worked Example WE-01: Complete Strategy Learning Cycle

**Scenario:** STR-MEAN_REVERSION_007 has been active for 3 months. The Learning Engine is asked to evaluate whether its weight should change.

**Data collected (LT-10: Strategy Learning):**

Session history: 65 sessions.
Current regime distribution: 45 TRENDING_BULL sessions, 20 RANGING sessions.
Win rate: 58% overall; 65% in RANGING; 47% in TRENDING_BULL.
Sharpe ratio: 0.91 overall; 1.12 in RANGING; 0.61 in TRENDING_BULL.
Max drawdown: 8.2%.
Current MetaLearning weight: 0.14.

**Learning Engine Processing:**

Step 1 — Outcome Analyzer receives 65 closed trades with regime tags.

Step 2 — Pattern Discovery Engine: scans stratified outcome data.
- Discovers: STRATEGY_OUTCOME_REGIME_DEPENDENT pattern
- Finding: "STR-MEAN_REVERSION_007 performs significantly better in RANGING regimes than TRENDING_BULL"
- Statistical test: regime-stratified win rates differ by 18% (p < 0.001); effect size: Sharpe improvement 0.51 in RANGING vs TRENDING_BULL
- Instance count: RANGING = 20, TRENDING_BULL = 45; both above minimum ✅

Step 3 — Knowledge Extraction: propose regime-specific weight adjustment
- RANGING regime: increase weight from 0.14 to 0.19 (+0.05 delta)
- TRENDING_BULL regime: decrease weight from 0.14 to 0.09 (-0.05 delta)

Step 4 — LQS Assessment:

| Dimension | Score | Notes |
|---|---|---|
| LQD-01 Accuracy | 0.93 | Pattern matches ground truth data |
| LQD-02 Novelty | 0.78 | Regime dependency not previously quantified |
| LQD-03 Generalization | 0.82 | Validated in both regime types |
| LQD-04 Repeatability | 0.85 | Pattern consistent across quarterly sub-periods |
| LQD-05 Stability | 0.80 | Regime dependency has been present for 3 months |
| LQD-06 Reliability | 0.92 | Clean, complete trade records |
| LQD-07 Bias Detection | 0.90 | No survivorship bias; all signals included |
| LQD-08 Drift Detection | 0.85 | No drift in regime classification |
| LQD-09 Explainability | 0.95 | Clear causal hypothesis: mean reversion works in sideways markets |
| LQD-10 Traceability | 1.00 | Full provenance to source trade records |
| LQD-11 Confidence | 0.88 | Calibration error < 5% |
| LQD-12 Impact | 0.85 | Projected Sharpe improvement: +0.12 via regime-appropriate weighting |
| **LQS** | **0.877** | **GOOD tier** |

Step 5 — 5-Stage Validation:
- Stage 7a Data Quality: PASS (complete records, accurate regime tags)
- Stage 7b Statistical Significance: PASS (p < 0.001; effect size 0.51 Sharpe)
- Stage 7c Out-of-Sample: held out sessions 56-65; regime-specific weighting performed better in held-out period ✅
- Stage 7d Regime Stability: PASS (applicable in RANGING; reduced in TRENDING_BULL — this is a refinement, not a failure)
- Stage 7e Impact: PASS (projected +12% improvement in Sharpe via correct regime weighting)

Step 6 — Governance:
- Impact = 5% weight change; TIER-2-ADVISORY
- Auto-approved; operator notification sent via Telegram

Step 7 — Deployment:
- MetaLearning: RANGING weight for STR-MEAN_REVERSION_007: 0.14 → 0.19
- MetaLearning: TRENDING_BULL weight for STR-MEAN_REVERSION_007: 0.14 → 0.09

Step 8 — Post-deployment monitoring (5 sessions):
- RANGING session (session 66): STR-MEAN_REVERSION_007 active with weight 0.19 — WIN (+1.8%)
- TRENDING_BULL sessions (67-70): STR-MEAN_REVERSION_007 active with weight 0.09 — 2 wins, 2 losses
- Overall performance improvement: LSHS stable; session IIOS Sharpe improved from 0.88 to 0.96

Step 9 — Feedback:
Pattern confidence strengthened: STRATEGY_OUTCOME_REGIME_DEPENDENT updated to confidence 0.82.
Meta Learning records: this update was effective (LT-20 feedback).

---

### Worked Example WE-02: Confidence Model Recalibration

**Scenario:** The Decision Confidence Score (DCS) for the 0.70-0.80 tier is miscalibrated.

**Discovery (LT-05: Decision Learning):**

Data: 90 decisions with DCS in [0.70, 0.80) over last 4 months.
Expected win rate for this tier: 70-80%.
Actual win rate: 54%.
This is a large miscalibration: the system is treating 54%-quality decisions as if they were 70-80% quality.

**Implication:**
- Capital Risk Engine is sizing positions based on 70-80% confidence
- Actual quality is 54%
- Result: systematic oversizing of medium-quality decisions

**Pattern:**
DCS_CALIBRATION_ERROR pattern ID: PAT-DECISION-20260601-000003
Instances: 90 decisions ✅
p < 0.0001 ✅
Effect size: Win rate gap of 16-26 percentage points ✅

**Proposed fix:**
Adjust DCS model so that decisions currently scoring 0.70-0.80 will score 0.50-0.65 after recalibration.
Capital Risk Engine will then size them appropriately.

**Validation:**
- Walk-forward test: apply recalibration to last 30 decisions in held-out set
- Performance with recalibrated sizing: drawdown reduced 23%; returns maintained
- LQS: 0.91 (EXCELLENT)

**Governance:** TIER-3-HUMAN (model structural change)
Telegram to operator: "DCS model miscalibration detected (0.70-0.80 tier winning at 54% vs expected 70-80%). Proposed recalibration. Review evidence: [PAT-DECISION-20260601-000003]. Approve? [YES/NO]"
Operator response: "YES — approve."

**Deployment:**
DCS model parameters updated.
Monitoring: 10 sessions.
Outcome: Average decision size in the 0.70-0.80 tier reduced by 18%. Overall portfolio drawdown improvement: 1.4%.

---

### Worked Example WE-03: Error Pattern Discovery and Prevention

**Scenario:** The Error Analyzer detects a recurring pattern in execution errors.

**Signal (LT-21: Error Learning):**
Over 20 sessions, 14 ORDER_REJECTED errors have occurred.
Error classification: PRICE_TICK_SIZE_VIOLATION (order price not a valid multiple of tick size).
Error distribution: 13 of 14 errors involve NSE derivatives instruments.
Error timing: all 14 errors occur on orders generated within 5 minutes of options expiry.

**Pattern Discovery:**
Pattern class: ERROR_RECURRENCE
Hypothesis: Near-expiry options have different tick size rules on NSE than regular trading hours. The Order Builder is not applying the near-expiry tick size exception.

**Impact:**
14 rejected orders represent missed execution on 14 decisions. PNL opportunity cost: estimated 3,200 INR across 20 sessions.

**Knowledge Extraction:**
Rule proposal: "For NSE options within 30 minutes of expiry, apply tick size = 0.05 regardless of the standard tick size for that options series."

**Validation:**
- Data Quality: PASS (all errors well-documented with timestamps and instrument details)
- Statistical Significance: PASS (14 errors in 20 sessions; error rate 0% without near-expiry; 100% correlation with near-expiry window)
- Out-of-Sample: N/A (prevention rule; not a predictive model)
- Regime Stability: PASS (errors occur in all regime types)
- Impact: +14 successful orders over prior 20-session period; avoid 3,200 INR PNL loss

**Governance:**
TIER-2-ADVISORY (execution parameter change)
Operator notification: "Recurring ORDER_REJECTED pattern detected. Near-expiry tick size rule missing in Order Builder. Proposed fix: apply tick_size=0.05 for NSE options within 30 min of expiry. This is an architectural recommendation for the Execution Engine — not a learning update. Forwarded to development."

**Action:**
This is forwarded to the development team as an architectural correction request. The Learning Engine's role is complete: it discovered the pattern, proposed the fix, and forwarded the recommendation. The actual code change in the Execution Engine goes through the standard development and deployment process.

---

### Worked Example WE-04: Bias Correction in Evidence Assessment

**Scenario:** The Bias Detector identifies confirmation bias in how the Evidence Engine is weighting contradictory signals.

**Detection:**
Bias Detector runs weekly scan on Evidence Engine output.
Observation: Over the last 15 sessions, when the MarketIntelligence regime is BULL, the Evidence Engine assigns average confidence 0.72 to confirming evidence (evidence that supports BULL thesis) and 0.41 to contradicting evidence (evidence that challenges BULL thesis).

Historical calibration data shows: confirming and contradicting evidence of similar source reliability should have similar confidence weights in a well-calibrated system. The 31-point gap is larger than expected statistical variation.

**Bias type:** Confirmation Bias (BULL_REGIME_ANCHORING)

**Severity assessment:**
Bias Score: 0.62 (SIGNIFICANT threshold: 0.60) — just above quarantine threshold.

**Action:**
All Evidence Engine outputs from the last 15 sessions are flagged as BIAS_SUSPECT.
Operator notified: "Confirmation bias detected in Evidence Engine (BULL regime). Contradicting evidence is being systematically underweighted by ~31 confidence points. Reviewing evidence weighting logic."

**Investigation:**
Root cause: the Evidence Engine's regime prior was updated 16 sessions ago, assigning a strong prior to BULL continuation. This prior is asymmetrically influencing update rules for confirming vs contradicting evidence.

**Correction:**
Evidence Engine update rule is recalibrated: the regime prior is applied symmetrically (it can raise confidence in BULL-confirming evidence but cannot lower confidence in BULL-contradicting evidence below source-reliability-based baseline).

**Outcome:**
Confirmation bias score drops from 0.62 to 0.18 after recalibration.
BIAS_SUSPECT flags on historical sessions retained for historical awareness.

---

### Worked Example WE-05: Meta Learning Feedback Loop

**Scenario:** The Meta Learning component (LT-20) evaluates whether recent learning updates have been effective.

**Data:**
Over the last 3 months, 42 knowledge updates have been deployed.
Effectiveness tracking (5 sessions post-deployment for each):
- 28 updates: target metric improved as projected (67% effectiveness rate)
- 9 updates: no measurable change (21%)
- 5 updates: target metric slightly worsened (12%)

**Meta Learning Analysis:**
Question: Are certain types of learning updates systematically less effective?

Stratification by learning type:
- LT-10 Strategy Learning updates: 12 deployed; 9 effective (75%); 3 no change
- LT-05 Decision Learning updates: 6 deployed; 5 effective (83%); 1 slightly worsened
- LT-06 Execution Learning updates: 8 deployed; 3 effective (38%); 4 no change; 1 worsened
- LT-07 Outcome Learning updates: 10 deployed; 8 effective (80%); 2 no change
- LT-08 Risk Learning updates: 3 deployed; 1 effective; 2 worsened (67% failure)

**Findings:**
1. LT-06 Execution Learning updates have a 38% effectiveness rate — below the 60% target.
   Hypothesis: execution parameter changes are being made based on insufficient data (fewer than the minimum sessions needed for the execution market to stabilise after a change).

2. LT-08 Risk Learning updates have a high failure rate.
   Hypothesis: risk parameter changes are too conservative in their proposed adjustments — changes are too small to measure, but when they are measurable, they sometimes produce adverse results.

**Proposed meta-learning updates:**
1. Increase minimum data requirement for LT-06 Execution Learning: from 7 sessions to 14 sessions before execution parameter update.
2. For LT-08 Risk Learning: increase governance tier from TIER-2-ADVISORY to TIER-3-HUMAN (require human review for all risk parameter changes given elevated failure rate).

**LQS assessment:** 0.84 (GOOD) — meta learning is itself a high-quality signal.

**Validation:** PASS on all 5 stages.
**Governance:** TIER-3-HUMAN (changing governance tiers for risk learning is structural).
**Operator:** Approves.
**Deployment:** LT-06 minimum sessions: 7 → 14. LT-08 governance: TIER-2-ADVISORY → TIER-3-HUMAN.

This is organizational learning: the Learning Engine has improved itself.

---

### Worked Example WE-06: Cross-Session Knowledge Continuity

**Scenario:** The IIOS restarts after a deployment (3:45 AM). Does the Learning Engine preserve all its knowledge?

**Knowledge state before restart:**
- 287 ACTIVE patterns in Learning Catalog
- 12 deployed knowledge updates (DEPLOYED status) from last 60 days
- 3 pending governance items (TIER-3-HUMAN, awaiting operator approval)
- Learning Audit Log: 15,847 events; hash chain intact
- Model version: DCSModel-0047; StrategyWeightModel-0093; RegimeClassifier-0031

**Restart sequence:**
1. Storage Layer loads: Learning Registry, Learning Catalog, Learning Archive all intact.
2. Learning Audit Manager: loads audit log; verifies hash chain — PASS (chain intact through last shutdown event).
3. Learning Catalog: 287 ACTIVE patterns loaded; all versions preserved.
4. Pending governance items: 3 items in PENDING_HUMAN_APPROVAL state loaded; operator notified via Telegram.
5. Model versions: DCSModel-0047, StrategyWeightModel-0093, RegimeClassifier-0031 loaded with all parameters.
6. Feedback Manager: attribution history loaded; 90-day window intact.
7. Pattern Discovery Engine: loads candidate patterns and instance counts.
8. Drift Detector: loads rolling baselines (30-session window intact).
9. All 21 components activated in sequence.

**Result:**
The Learning Engine resumes from exactly the state it was in before the restart. No knowledge is lost. All patterns, models, governance items, and audit history are preserved.

The first session after restart begins with a fully informed Learning Engine: it has 3+ months of accumulated strategy learning, calibrated models, and active patterns — not a blank slate.

---

## DOCUMENT SUMMARY AND CLOSING MATERIALS

### Summary Section 1: Document Metrics

| Metric | Value |
|---|---|
| Document title | IIOS Learning Engine Architecture |
| Document code | IIOS-LRN-ENG-ARCH-001 |
| Layer | Layer 13 of 17 in the IIOS cognitive stack |
| Layer name | LearningSystem |
| Parts | I through X |
| Supplements | A through H |
| Governing Design Records | 8 (GDR-LRN-001 through GDR-LRN-008) |
| Learning Constitution rules | 100+ across 14 categories (LC-A through LC-N) |
| Learning types | 21 (LT-01 through LT-21) |
| Components | 21 (LC-01 through LC-20, plus Learning Catalog as LC-21) |
| Services | 12 (LS-01 through LS-12) |
| Pipelines | 10 (LP-01 through LP-10) |
| Lifecycle stages | 13 |
| LQS dimensions | 12 |
| Anti-patterns documented | 9 (AP-01 through AP-09) |
| Known pattern classes | 9 |
| Feedback models | 4 (FM-01 through FM-04) |
| Worked examples | 6 (WE-01 through WE-06) |
| Governance tiers | 4 (TIER-1-AUTO through TIER-4-COMMITTEE) |
| Learning record statuses | 19 |
| Glossary terms | 65+ |

---

### Summary Section 2: Parts Summary

| Part | Title | Purpose |
|---|---|---|
| I | Learning Philosophy and Definitional Framework | 15-concept definitional ladder; 9 learning types; 10 principles; governance invariants |
| II | Learning Taxonomy | 21 learning type definitions (LT-01 through LT-21) with source, signal, output, target |
| III | Core Component Architecture | 21 components across 4 tiers; full definitions per component |
| IV | Learning Lifecycle | 13 stages; state machine; lifecycle timing; PIT semantics |
| V | Learning Services | 12 services (LS-01 through LS-12) |
| VI | Learning Pipelines | 10 pipelines (LP-01 through LP-10) with ASCII flow diagrams |
| VII | Learning Quality Framework | 12 LQS dimensions; formula; tiers; monitoring thresholds |
| VIII | Learning Governance | Ownership; naming; versioning; approval matrix; compliance; security; retention |
| IX | Learning Constitution | 100+ rules across 14 categories |
| X | Learning Readiness Checklist | 6-section pre-session checklist; intraday and EOD checks; readiness matrix; state machine |

---

### Summary Section 3: Supplements Summary

| Supplement | Title | Contents |
|---|---|---|
| A | Learning Taxonomy Reference | Classification matrix; IIOS layer mapping table |
| B | Pattern Catalogue | Pattern record structure; 9 known pattern classes; confidence calibration reference |
| C | Feedback Models | 4 models: Trade Outcome, EQS, Strategy Performance, Human Feedback |
| D | Knowledge Evolution Examples | 3 examples: strategy weight recalibration, DCS recalibration, sector rotation pattern |
| E | Bias and Drift Examples | 3 bias examples + 2 drift examples |
| F | Anti-Patterns | 9 anti-patterns with descriptions, harms, and IIOS safeguards |
| G | Operational Runbook | 21-step startup; intraday ops; 12-step EOD; 5 recovery procedures; weekly maintenance |
| H | Glossary and GDRs | 65+ glossary terms; 8 immutable GDRs |

---

### Summary Section 4: LQS Quick Reference

| Code | Dimension | Weight | Target |
|---|---|---|---|
| LQD-01 | Accuracy | 0.20 | > 0.90 |
| LQD-02 | Novelty | 0.10 | > 0.60 |
| LQD-03 | Generalization | 0.15 | > 0.75 |
| LQD-04 | Repeatability | 0.10 | > 0.80 |
| LQD-05 | Stability | 0.10 | > 0.80 |
| LQD-06 | Reliability | 0.10 | > 0.85 |
| LQD-07 | Bias Detection | 0.05 | 1.00 |
| LQD-08 | Drift Detection | 0.05 | > 0.90 |
| LQD-09 | Explainability | 0.05 | > 0.80 |
| LQD-10 | Traceability | 0.03 | 1.00 |
| LQD-11 | Confidence | 0.04 | > 0.85 |
| LQD-12 | Improvement Impact | 0.03 | > 0.70 |
| **Total** | | **1.00** | |

**LQS Tiers:**

| Tier | Range | Meaning |
|---|---|---|
| EXCELLENT | 0.85 – 1.00 | High-quality learning; fast-track governance |
| GOOD | 0.70 – 0.84 | Above target; standard governance |
| ACCEPTABLE | 0.55 – 0.69 | Within limits; enhanced post-deployment monitoring |
| MARGINAL | 0.35 – 0.54 | Below target; TIER-3-HUMAN regardless of impact |
| FAILED | 0.00 – 0.34 | Reject; archive with failure reasons |

---

### Summary Section 5: Component-to-Tier Mapping

**Tier 1: Collection and Registry**
- LC-01: Learning Registry
- LC-02: Learning Catalog
- LC-03: Learning Collector
- LC-04: Learning Processor

**Tier 2: Discovery and Analysis**
- LC-05: Pattern Discovery Engine
- LC-06: Knowledge Updater
- LC-07: Model Improvement Manager
- LC-08: Feedback Manager
- LC-09: Outcome Analyzer
- LC-10: Performance Analyzer
- LC-11: Error Analyzer
- LC-12: Bias Detector
- LC-13: Drift Detector

**Tier 3: Validation and Governance**
- LC-14: Learning Validation Manager
- LC-15: Learning Governance Manager
- LC-16: Learning Audit Manager

**Tier 4: Operations and Output**
- LC-17: Learning Archive Manager
- LC-18: Learning Health Manager
- LC-19: Learning Analytics Manager
- LC-20: Learning Recommendation Manager

---

### Summary Section 6: Governing Design Records Quick Reference

| GDR | Title | Immutable since |
|---|---|---|
| GDR-LRN-001 | Learning Never Replaces Governance | IIOS v1.0 |
| GDR-LRN-002 | Evidence Before Update | IIOS v1.0 |
| GDR-LRN-003 | Incrementality Required | IIOS v1.0 |
| GDR-LRN-004 | Audit Before Update | IIOS v1.0 |
| GDR-LRN-005 | No Deletion | IIOS v1.0 |
| GDR-LRN-006 | Human Override is Absolute | IIOS v1.0 |
| GDR-LRN-007 | Kill Switch is Never Subject to Learning | IIOS v1.0 |
| GDR-LRN-008 | Reversibility Required | IIOS v1.0 |

---

### Summary Section 7: Learning Engine in IIOS Stack Context

`
[Layer 1-12: Signal generators]
  Observations · Evidence · Hypotheses · Reasoning · Decisions
  Executions · Fills · Outcomes · Errors · Regime changes · Human overrides
                          │
                          │  Learning signals (via EventBus)
                          ▼
            ┌─────────────────────────┐
            │  LEARNING ENGINE (13)    │
            │                          │
            │  Collect → Process →    │
            │  Discover → Validate → │
            │  Govern → Deploy →     │
            │  Monitor → Evolve      │
            └────────────┬────────────┘
                          │  Knowledge updates (approved)
              ┌───────────┴──────────────────────────────┐
              │                           │               │
    ┌─────────▼───────────┐ ┌─────────▼───────────┐  ┌──▼──────────────┐
    │  MetaLearning (3)    │ │  StrategyLab (5)     │  │  ControlTower   │
    │  Strategy weights    │ │  Strategy evolution  │  │  Telemetry      │
    └─────────────────────┘ └─────────────────────┘  └─────────────────┘
              │
    ┌─────────▼──────────────────────────┐
    │  All other layers (improved)        │
    │  Reasoning Engine, Decision Engine, │
    │  Execution Engine, Risk layers      │
    └─────────────────────────────────────┘
`

---

### Summary Section 8: Governing Documents

| Document | Code | Relationship |
|---|---|---|
| ARCHITECTURE.md | IIOS-ARCH-000 | Master architecture; Layer 13 defined |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | IIOS-KNW-ENG-ARCH-001 | Knowledge base that Learning Engine updates |
| DECISION_ENGINE_ARCHITECTURE.md | IIOS-DEC-ENG-ARCH-001 | Upstream decision maker; Learning Engine calibrates its DCS |
| EXECUTION_ENGINE_ARCHITECTURE.md | IIOS-EXE-ENG-ARCH-001 | Upstream executor; Learning Engine calibrates execution parameters |
| REASONING_ENGINE_ARCHITECTURE.md | IIOS-RSN-ENG-ARCH-001 | Reasoning chains whose quality Learning Engine evaluates |
| HYPOTHESIS_ENGINE_ARCHITECTURE.md | IIOS-HYP-ENG-ARCH-001 | Hypotheses whose validation rates Learning Engine tracks |
| EVIDENCE_ENGINE_ARCHITECTURE.md | IIOS-EVD-ENG-ARCH-001 | Evidence whose predictive value Learning Engine calibrates |
| OBSERVATION_ENGINE_ARCHITECTURE.md | IIOS-OBS-ENG-ARCH-001 | Observations whose accuracy Learning Engine tracks |
| LEARNING_ENGINE_ARCHITECTURE.md | IIOS-LRN-ENG-ARCH-001 | This document |

---

### Summary Section 9: Compliance Checklist

**Before first production learning session:**
- [ ] All 21 components activated and HEALTHY
- [ ] Learning Audit Log hash chain verified
- [ ] Learning Catalog consistent (no conflicting ACTIVE entries)
- [ ] All model versions loaded with rollback capability
- [ ] No pending governance items older than 72 hours
- [ ] Drift detection baselines loaded (minimum 10 sessions)
- [ ] Feedback attribution history loaded (minimum 30-day window)
- [ ] Meta Learning (LT-20) active
- [ ] Error Learning (LT-21) active
- [ ] Human operator confirmed and Telegram channel active

**Weekly compliance:**
- [ ] Full pattern scan on complete history completed
- [ ] Drift detector baselines updated
- [ ] Governance queue reviewed and cleared
- [ ] LQS trend report reviewed
- [ ] Archive integrity verification completed

**Monthly compliance:**
- [ ] Bias detector coverage review
- [ ] Knowledge update effectiveness rate reviewed (target > 60%)
- [ ] Model performance review (all active models vs baseline)
- [ ] Rollback rate review (target < 5%)
- [ ] Human override rate review (target < 3% of auto-approved updates)
- [ ] Meta Learning (LT-20) effectiveness assessment

**Annual compliance:**
- [ ] Annual knowledge review (all ACTIVE catalog items)
- [ ] GDR compliance review (all 8 GDRs verified active)
- [ ] Bias detection repertoire expanded (new known biases added)

---

### Summary Section 10: Architectural Impact Statement

**Architectural role:** The Learning Engine is the intelligence-compounding mechanism of the IIOS. Every other engine in the system can be improved by the Learning Engine — but only through the validated, governed, incremental update path defined in this document.

**What the Learning Engine does:**
- Transforms accumulated experience into durable, validated knowledge
- Calibrates every quantitative model in the system over time
- Discovers recurring market and behavioral patterns
- Tracks and improves strategy performance
- Detects and eliminates recurring errors
- Detects and corrects model bias and drift
- Provides human operators with prioritised improvement recommendations

**What the Learning Engine does NOT do:**
- Execute trades
- Make investment decisions
- Set risk limits without governance approval
- Override the Kill Switch
- Override human operators
- Modify constitutional rules
- Apply knowledge updates without validation and governance

**Impact of failure:** If the Learning Engine fails, the IIOS continues to trade but does not improve. Strategy weights remain static. Model drift is not detected. Recurring errors are not corrected. Gradually, performance may degrade as market conditions evolve and the fixed system fails to adapt.

**Impact of incorrect learning:** An incorrect learning update (e.g., a wrong confidence model recalibration) can cause systematic degradation in decision quality until it is detected and rolled back. The 5-session post-deployment monitoring, the 5% degradation rollback trigger, and the reversibility guarantee (GDR-LRN-008) are the primary safeguards.

---

### Summary Section 11: Version History

| Version | Date | Summary |
|---|---|---|
| 1.0 | 2026 | Initial ratification of Learning Engine architecture |

---

### Summary Section 12: Ratification Statement

This document has been reviewed for completeness, internal consistency, and alignment with all prior IIOS architecture documents. The following statements are confirmed:

1. The Learning Engine is correctly positioned as Layer 13, with defined inputs from layers 1-12 and defined outputs to layers 3, 5, and 17.
2. The eight GDRs are consistent with the governance frameworks in the Decision Engine and Execution Engine architectures.
3. The Learning Constitution does not conflict with any prior architecture document's constitutional rules.
4. The Kill Switch is explicitly and unconditionally exempt from learning (GDR-LRN-007).
5. Human operator authority is explicitly preserved and unconditional (GDR-LRN-006).
6. The LQS framework is consistent with the EQS (Execution) and DCS (Decision) quality frameworks.
7. The governance tier model is consistent with the governance tier model in the Decision Engine Architecture.
8. No learning update can violate any IIOS constitutional rule from any layer.

**Document status:** RATIFIED

**Document code:** IIOS-LRN-ENG-ARCH-001

**Next review:** When any of the following occur:
- A new learning type is added (requires updating LT taxonomy)
- A new layer is added to the IIOS stack
- A GDR is amended (requires extraordinary review)
- The LQS weights are recalibrated
- The governance tier model is revised

---

## END OF DOCUMENT

### Document Footer

`
=============================================================================
IIOS LEARNING ENGINE ARCHITECTURE
Document Code: IIOS-LRN-ENG-ARCH-001
Layer: 13 of 17 — LearningSystem
Status: RATIFIED
Series: IIOS Architecture Document Series
=============================================================================
Upstream inputs:    All layers 1-12 (via EventBus learning signals)
Primary outputs:    MetaLearning (Layer 3) · StrategyLab (Layer 5)
                    All layers (via Knowledge Updater)
Oversight:          ControlTower (Layer 17) · Human operators
=============================================================================
Constitutional rules:     100+ (LC-A through LC-N)
Governing Design Records: 8   (GDR-LRN-001 through GDR-LRN-008)
Learning types:           21  (LT-01 through LT-21)
Components:               21  (LC-01 through LC-20)
Services:                 12  (LS-01 through LS-12)
Pipelines:                10  (LP-01 through LP-10)
Lifecycle stages:         13
LQS dimensions:           12
=============================================================================
The Learning Engine does not reason.
The Learning Engine does not execute.
The Learning Engine does not decide.
The Learning Engine learns — continuously, incrementally, safely, and traceably.
It is the long-term memory and self-improvement system of IIOS.
=============================================================================
`

---

## SUPPLEMENT I — CROSS-LAYER INTEGRATION CONTRACTS

### I.1 Integration Overview

The Learning Engine interfaces with every IIOS layer. This supplement defines the precise interface contract for each major integration: what the Learning Engine receives, what it sends back, the protocol for applying updates, and the fallback behavior when the interface is unavailable.

**Integration principle:** All Learning Engine interfaces are read-heavy and write-sparse. The Learning Engine ingests continuously but deploys updates infrequently — only when validated, approved knowledge exists and governance has cleared it.

---

### I.2 Integration Contract: Learning Engine ↔ MetaLearning (Layer 3)

**Direction:** Bidirectional

**L3 → L13 (input):**

| Signal | Description | Frequency |
|---|---|---|
| Regime state | Current market regime label | Per regime transition |
| Strategy weight snapshot | Full strategy weight vector | Session start + each weight change |
| k-NN prediction accuracy | Per-session prediction accuracy | Session end |
| Regime-strategy co-occurrence | Which strategies were active in each regime | Session end |

**L13 → L3 (output, Learning Engine updates MetaLearning):**

| Update | Description | Trigger |
|---|---|---|
| Strategy weight delta | Regime-specific weight adjustment | After TIER-1 or TIER-2 governance approval |
| Weight adjustment limit | Maximum delta per cycle | GDR-LRN-003 enforced (default: 5% per strategy weight) |
| Regime label confidence | Confidence in current regime classification | Pattern-based recalibration |
| k-NN parameter recalibration | k, weighting function adjustments | After model improvement governance cycle |

**Protocol:**
1. Learning Engine submits weight adjustment proposal as a Knowledge Update (type: STRATEGY_WEIGHT_DELTA)
2. Knowledge Updater verifies governance approval (TIER-1-AUTO minimum)
3. Audit Manager records the update with full provenance (source pattern ID, LQS score, approval tier)
4. Knowledge Updater calls MetaLearning's weight update interface with delta vector
5. MetaLearning applies delta; confirms update; records in its own log
6. Monitoring: subsequent 5 sessions tracked for performance impact

**Rollback:**
If performance metric (IIOS regime-adjusted Sharpe) degrades more than 5% in the 5-session monitoring window, the Learning Engine automatically proposes rollback via the same governance pathway.

**Fallback (MetaLearning unavailable):**
Weight updates are queued. When MetaLearning comes online, queued updates are applied in order, oldest first.

---

### I.3 Integration Contract: Learning Engine ↔ StrategyLab (Layer 5)

**Direction:** Bidirectional

**L5 → L13 (input):**

| Signal | Description | Frequency |
|---|---|---|
| Strategy backtest results | All backtest metrics per strategy per run | Each backtest completion |
| Evolved strategy variants | Newly evolved strategies with parameter sets | Each evolution cycle |
| Walk-forward test results | WFT metrics per strategy | Each WFT cycle |
| Promotion/demotion events | Strategy status changes | Per event |
| Strategy fitness scores | Multi-dimensional fitness vector | Each evolution cycle |

**L13 → L5 (output):**

| Update | Description | Trigger |
|---|---|---|
| Strategy performance labels | LT-10 outcome labels applied to strategies | Session end |
| Win rate trend alert | Alert when win rate declining | When 3-session rolling win rate drops 10+ points |
| Regime-performance map | Strategy × regime performance matrix | Weekly batch learning |
| Promotion recommendation | Recommend strategy for promotion to active | When ResearchLab gates would be met |
| Demotion recommendation | Recommend strategy for demotion | When win rate < 45% for 10 consecutive sessions |

**Protocol:**
Strategy performance feedback loop:
1. Each closed trade is tagged with originating strategy ID
2. Outcome Analyzer computes per-strategy session metrics
3. Learning Catalog updated: strategy performance entry refreshed
4. If win rate falls below demotion threshold: TIER-2-ADVISORY proposal sent
5. StrategyLab receives recommendation; applies its own governance process before demotion
6. (Note: Learning Engine can recommend but not force demotion — the decision remains with StrategyLab)

---

### I.4 Integration Contract: Learning Engine ↔ Decision Engine (Layer 10)

**Direction:** Bidirectional

**L10 → L13 (input):**

| Signal | Description | Frequency |
|---|---|---|
| Decision Package | Full record of every COMMITTED decision | Per decision |
| Decision outcome | Outcome tag: WIN/LOSS/NEUTRAL/ABORTED | Trade close |
| Debate outcome | 5-agent debate records and vote vectors | Per decision |
| DCS pre-decision | Decision Confidence Score assigned | Per decision |
| DCS post-outcome | Actual outcome vs DCS projection | Trade close |

**L13 → L10 (output):**

| Update | Description | Trigger |
|---|---|---|
| DCS calibration delta | Recalibration of DCS → actual win rate mapping | After governance approval |
| Debate quality signal | Retrospective quality score for past debates | Session end batch |
| Confidence tier redefinition | Boundary adjustment for DCS tiers | TIER-3-HUMAN, max once per quarter |

**Protocol:**
DCS recalibration cycle:
1. Decision Learning (LT-05) accumulates decisions with outcomes
2. When minimum count (20 per tier) is reached: calibration analysis runs
3. For each DCS tier: compare projected win rate vs actual win rate
4. If miscalibration gap > 10%: Knowledge Update proposed
5. Governance: TIER-2-ADVISORY for minor recalibrations (< 10% delta), TIER-3-HUMAN for model structural changes
6. Deployed recalibration: validated in held-out 20% of decision history first

---

### I.5 Integration Contract: Learning Engine ↔ Execution Engine (Layer 11)

**Direction:** Primarily L11 → L13, with occasional L13 → L11

**L11 → L13 (input):**

| Signal | Description | Frequency |
|---|---|---|
| EQS record | Execution Quality Score per order | Per order fill |
| Slippage record | Actual vs expected slippage | Per order fill |
| Order rejection | Rejected order with reason code | Per rejection |
| Order type outcome | Performance by order type (MARKET, LIMIT, SL) | Session end |
| Broker routing outcome | Performance by broker and routing path | Session end |

**L13 → L11 (output):**

| Update | Description | Trigger |
|---|---|---|
| Slippage prior update | Updated slippage estimate by instrument class | After 14+ sessions (enhanced requirement, see WE-05) |
| Order type preference | Recommended order type for instrument class | After governance cycle |
| Time-of-day routing | Routing preference adjustment by time window | After error pattern analysis |

---

### I.6 Integration Contract: Learning Engine ↔ RiskControl (Layer 7)

**Direction:** Bidirectional (Learning Engine is read-only to most risk parameters)

**L7 → L13 (input):**

| Signal | Description | Frequency |
|---|---|---|
| VaR realisation | Actual portfolio loss vs VaR projection | Session end |
| Drawdown event | Intraday drawdown events with context | Per event |
| Kill Switch activation | Kill Switch trigger event with reason | Per activation |
| Stop loss hit | Per-trade stop loss hit with context | Per event |

**L13 → L7 (output):**

| Update | Description | Trigger |
|---|---|---|
| VaR model accuracy signal | Retrospective VaR back-test results | Weekly |
| Risk learning recommendation | Human-reviewed risk parameter recalibration | TIER-3-HUMAN only |
| Drawdown pattern alert | Identified systematic drawdown pattern | Pattern confidence > 0.80 |

**Note:** Per GDR-LRN-007, Kill Switch parameters are never targets of Learning Engine updates.

---

### I.7 Integration Contract: Learning Engine ↔ ControlTower (Layer 17)

**Direction:** Primarily L13 → L17

**L13 → L17 (output):**

| Signal | Description | Frequency |
|---|---|---|
| LSHS (Learning System Health Score) | Overall component health score | Every 60 seconds |
| Learning count (session) | Count of learning records processed this session | Session-level |
| Knowledge updates deployed | Count and type of updates deployed this session | Per update + session end |
| Governance queue depth | Pending approvals awaiting human review | Real-time |
| Active patterns count | Current ACTIVE pattern count in catalog | Session end |
| Anti-pattern alerts | Any anti-pattern detection events | Per event |
| LQS distribution summary | Distribution of LQS scores (session) | Session end |
| Error pattern alerts | New error patterns discovered | Per event |

**L17 → L13 (input):**

| Signal | Description | Frequency |
|---|---|---|
| Human override commands | Halt updates, rollback, approve governance items | On demand |
| Operational mode | Current IIOS mode (PAPER, LIVE, SUSPENDED) | Mode changes |

---

### I.8 Integration Contract: Learning Engine ↔ TradeMonitoring (Layer 12)

**Direction:** Primarily L12 → L13

**L12 → L13 (input):**

| Signal | Description | Frequency |
|---|---|---|
| Closed trade record | Complete trade record with all outcomes | Per trade close |
| Open position heartbeat | Real-time PNL, distance to exit, duration | Every 30 seconds during trading |
| Stop adjustment event | Stop loss or target price adjustment | Per adjustment |
| Monitoring alert | TradeMonitor threshold breach events | Per breach |
| Session PNL summary | Full session PNL table | Session end |

**Value to Learning Engine:**
The trade monitoring stream is the primary source for LT-07 (Outcome Learning) and LT-10 (Strategy Learning). It provides the ground truth outcomes that feed every feedback model.

---

### I.9 Integration Contract: Learning Engine ↔ LearningSystem (Internal)

**Self-referential contract (Meta Learning — LT-20):**

The Learning Engine evaluates its own outputs. Specifically:

| Evaluation target | Metric | Threshold |
|---|---|---|
| Knowledge update effectiveness | Post-deployment improvement rate | > 60% |
| LQS prediction accuracy | LQS vs actual post-deployment outcome | Correlation > 0.65 |
| Governance tier accuracy | Tier assignment vs actual impact | Tier-impact alignment > 80% |
| Pattern confidence calibration | Confidence vs observed pattern frequency | Calibration error < 10% |
| Rollback rate | % of deployed updates rolled back | < 5% |
| Human override rate | % of auto-approved updates later overridden | < 3% |

If any meta-learning metric falls below threshold for 3 consecutive evaluations, the Learning Engine escalates to TIER-3-HUMAN with a full self-assessment report.

---

## SUPPLEMENT J — PERFORMANCE TARGETS, SLAs, AND CAPACITY MODEL

### J.1 Learning Engine Performance Targets

The Learning Engine must not impede IIOS trading operations. All Learning Engine processing that is on the critical path of a trading cycle must complete within defined time budgets. Non-critical processing runs asynchronously and has relaxed time budgets.

**Critical path operations (on-cycle):**

| Operation | Time Budget | Action if Exceeded |
|---|---|---|
| Learning Collector — signal ingestion | < 5 ms per signal | Drop and log; never block EventBus |
| Learning Processor — routing | < 10 ms per record | Queue and process async |
| LSHS computation | < 50 ms | Use cached value; refresh in background |
| Read from Learning Catalog | < 20 ms | Use in-memory cache |
| Check for applicable patterns | < 30 ms | Return empty if not met in time |

**Asynchronous operations (off-cycle):**

| Operation | Time Budget | Cadence |
|---|---|---|
| Pattern Discovery scan | < 90 seconds | Session end |
| Knowledge Update deployment | < 30 seconds | Per update (off-cycle only) |
| LQS computation | < 15 seconds per candidate | On demand |
| 5-stage validation pipeline | < 5 minutes total | Per candidate |
| Model improvement cycle | < 10 minutes total | Weekly or on trigger |
| Archive operations | < 2 minutes | Session end |
| Audit log flush | < 10 seconds | Every 5 minutes |
| Drift detection scan | < 60 seconds | Daily |
| Bias detection scan | < 90 seconds | Weekly |
| Meta learning evaluation | < 3 minutes | Weekly |
| Learning Recommendation Manager | < 30 seconds | Session end |

---

### J.2 Service Level Targets

| SLT Code | Target | Measurement |
|---|---|---|
| SLT-LRN-01 | LSHS > 0.80 at start of each session | Session start health check |
| SLT-LRN-02 | Knowledge update effectiveness > 60% | Monthly average |
| SLT-LRN-03 | Rollback rate < 5% of deployed updates | Monthly average |
| SLT-LRN-04 | Human override rate < 3% of auto-approved | Monthly average |
| SLT-LRN-05 | Governance queue cleared within 24 hours | Max item age |
| SLT-LRN-06 | Audit log hash chain intact: 100% | Continuous |
| SLT-LRN-07 | No learning update applied during Kill Switch | Continuous; zero tolerance |
| SLT-LRN-08 | LQS > 0.55 (ACCEPTABLE) before any deployment | Per update |
| SLT-LRN-09 | Pattern minimum evidence before promotion | 10 instances, p < 0.05 |
| SLT-LRN-10 | Out-of-sample validation on 20% held-out data | Per model update |
| SLT-LRN-11 | Post-deployment monitoring: minimum 5 sessions | Per knowledge update |
| SLT-LRN-12 | LSHS reported to ControlTower every 60 seconds | Continuous |

---

### J.3 Capacity Model

**Learning Record volume estimate:**

| Signal source | Records per session | Records per year (250 trading days) |
|---|---|---|
| Trade observations | ~50 | ~12,500 |
| Decision packages | ~20 | ~5,000 |
| Evidence assessments | ~200 | ~50,000 |
| Hypothesis evaluations | ~100 | ~25,000 |
| Reasoning chain records | ~40 | ~10,000 |
| Execution fill records | ~25 | ~6,250 |
| Error events | ~5 | ~1,250 |
| Human override events | ~1 | ~250 |
| Regime transition events | ~3 | ~750 |
| Macro/sector signals | ~50 | ~12,500 |
| **Total** | **~494** | **~123,500** |

**Retention model:**

| Status | Retention period | Storage tier |
|---|---|---|
| ACTIVE records | Indefinite (working memory) | Hot storage (SQLite in-memory + persistent) |
| DEPLOYED updates | 5 years minimum | Warm storage (SQLite persistent) |
| ARCHIVED patterns | 10 years minimum | Cold storage (SQLite persistent; compressed) |
| RETIRED knowledge | 10 years minimum | Cold storage |
| Audit log | Permanent (never purged) | Append-only log; periodic integrity check |
| Error records | 3 years minimum | Warm storage |

**Storage growth estimate:**

| Year | Cumulative records | Estimated storage |
|---|---|---|
| Year 1 | 123,500 | ~35 MB |
| Year 3 | 370,500 | ~105 MB |
| Year 5 | 617,500 | ~175 MB |
| Year 10 | 1,235,000 | ~350 MB |

Learning Engine storage is well within the capacity of a standard server deployment. No specialized data infrastructure is required for the first decade of operation.

---

### J.4 Concurrency Model

The Learning Engine is designed for safe concurrent operation within a single IIOS instance:

**Write-safe zones (serialised):**

| Zone | Serialization mechanism |
|---|---|
| Learning Registry writes | Single writer; async queue |
| Learning Catalog updates | Write-lock per catalog entry |
| Knowledge Update deployment | Serialized knowledge update queue |
| Audit log writes | Append-only; hash chain requires serial writes |
| Model parameter updates | Atomic updates per model version |

**Read-safe zones (parallel allowed):**

| Zone | Parallel readers |
|---|---|
| Learning Catalog reads | Unlimited parallel readers |
| Pattern query | Unlimited parallel readers |
| LQS computation | Multiple independent computations in parallel |
| Performance analytics | Read-only; parallel scans supported |

**Conflict resolution:**
If a knowledge update is proposed while a prior update to the same parameter is in the deployment pipeline, the newer proposal is queued. Updates to the same parameter are never applied concurrently. The queue is drained in order of proposal time.

---

### J.5 Data Quality Requirements

For Learning Engine outputs to be reliable, the inputs from each upstream layer must meet minimum data quality standards.

| Layer | Required data quality | If quality fails |
|---|---|---|
| Layer 11 Execution | Fill records must include: filled price, quantity, timestamp, strategy tag, order type | LT-06 Execution Learning suspended for affected sessions |
| Layer 12 TradeMonitor | Closed trade records must include: entry/exit prices, strategy, regime tag, PNL | LT-07 Outcome Learning suspended |
| Layer 10 Decision | Decision Packages must include: DCS at commit time, strategy, reasoning chain ID | LT-05 Decision Learning suspended |
| Layer 9 RiskGuardian | Kill Switch state must be reliably communicated | All learning updates suspended while state unknown |
| Layer 3 MetaLearning | Strategy weight vector must be accessible | LT-10 Strategy Learning proceeds; weight update queued |
| Layer 17 ControlTower | LSHS reporting must be possible | Fail silently; log locally |

**Data quality validation:**
The Learning Processor validates every incoming Learning Record against a schema. Records failing validation are placed in QUARANTINE status and logged. Quarantined records are not included in pattern discovery or model training. Operators are notified of systematic data quality issues.

---

### J.6 Fault Tolerance Model

**Fault categories and responses:**

| Fault | Learning Engine response |
|---|---|
| Learning Audit Manager unavailable | HOLD all knowledge updates; queue them; resume when Audit Manager restored |
| Learning Catalog corrupted | Load from archive snapshot; replay recent records to rebuild |
| Model version file missing | Load prior version from archive; restart improvement cycle from prior version |
| Governance queue inaccessible | HOLD all TIER-2+ updates; escalate to TIER-3-HUMAN; alert operator |
| EventBus signal loss | Learning Engine operates in degraded mode; processes buffered records; alerts operator |
| Drift Detector failure | Disable automatic drift alerts; schedule manual drift review within 5 sessions |
| Pattern Discovery failure | Disable new pattern generation; existing patterns remain active |
| Hash chain integrity failure | HALT Learning Engine; alert operator; do not process any updates until chain is verified or rebuilt |
| Kill Switch activation | FREEZE all learning update deployments; continue collection only; resume after Kill Switch deactivated by operator |

**Graceful degradation levels:**

| LSHS Range | Learning Engine status | Capability |
|---|---|---|
| 0.90 – 1.00 | NOMINAL | Full capability |
| 0.75 – 0.89 | DEGRADED | Core learning active; reduced analytics |
| 0.55 – 0.74 | PARTIAL | Collection + Outcome analysis only |
| 0.35 – 0.54 | MINIMAL | Collection only; all updates suspended |
| 0.00 – 0.34 | EMERGENCY | All updates suspended; alert operator immediately |

---

## SUPPLEMENT K — INDEX OF TABLES AND DIAGRAMS

### K.1 Index of Major Tables

| Table | Location |
|---|---|
| Learning Types Summary (LT-01 through LT-21) | Part II |
| Component Summary (LC-01 through LC-20) | Part III |
| Lifecycle Stage Definitions | Part IV |
| 5-Stage Validation Pipeline | Part IV |
| Governance Tier Matrix | Part IV |
| Learning Record Status Reference (19 statuses) | Part IV |
| Lifecycle Timing Reference | Part IV |
| Learning Services Summary (LS-01 through LS-12) | Part V |
| LQS Dimensions (LQD-01 through LQD-12) | Part VII |
| LQS Tier Reference | Part VII |
| Quality Monitoring Thresholds | Part VII |
| Ownership Table | Part VIII |
| Constitutional Rule Category Index (LC-A through LC-N) | Part IX |
| Readiness Matrix | Part X |
| Classification Matrix (Supplement A) | Supplement A |
| IIOS Layer Mapping (Supplement A) | Supplement A |
| Pattern Classes Reference (Supplement B) | Supplement B |
| Confidence Calibration Reference (Supplement B) | Supplement B |
| GDR Quick Reference | Supplement H |
| LQS Quick Reference | Document Summary |
| Component-to-Tier Mapping | Document Summary |
| Cross-Layer Integration Contracts | Supplement I |
| Performance Targets | Supplement J |
| Service Level Targets | Supplement J |
| Capacity Model | Supplement J |
| Fault Tolerance Model | Supplement J |

---

### K.2 Index of ASCII Diagrams

| Diagram | Location |
|---|---|
| IIOS 17-Layer Cognitive Stack (Layer 13 highlighted) | Part I introduction |
| Learning Engine Information Flow (all 17 layers → L13 → L3/L5/L17) | Part I |
| Lifecycle State Transition Diagram | Part IV |
| LP-01 through LP-10 Pipeline Flow Diagrams | Part VI |
| IIOS Stack Context Diagram (L13 in full context) | Document Summary Section 7 |

---

### K.3 Index of LaTeX Formulas

| Formula | Location |
|---|---|
| LQS composite formula | Part VII |
| Feedback decay formula (FM-01) | Supplement C |
| EQS feedback formula (FM-02) | Supplement C |
| Strategy performance formula (FM-03) | Supplement C |
| Human feedback formula (FM-04) | Supplement C |

---

---

## SUPPLEMENT L — CANONICAL LEARNING RECORD FORMATS AND IDENTIFIER REFERENCE

### L.1 Learning Record Identifier Format

Every object in the Learning Engine has a unique, typed identifier. This supplement defines all identifier formats and provides canonical record examples.

**Identifier formats:**

| Object type | Format | Example |
|---|---|---|
| Learning Record | LRN-{TYPE}-{DATE:YYYYMMDD}-{SEQ:08d} | LRN-STRATEGY-20260601-00000001 |
| Pattern | PAT-{DOMAIN}-{DATE:YYYYMMDD}-{SEQ:06d} | PAT-STRATEGY-20260601-000001 |
| Knowledge Update | KU-{TARGET}-{DATE:YYYYMMDD}-{SEQ:06d} | KU-METAWT-20260601-000001 |
| Model Version | MDL-{MODEL}-{VERSION:04d} | MDL-DCSMODEL-0047 |
| Learning Audit Entry | LAUD-{LRN_ID}-{SEQ:04d} | LAUD-LRN-STRATEGY-20260601-00000001-0001 |
| Session Report | LRPT-{SESSION_DATE:YYYYMMDD}-{SEQ:04d} | LRPT-20260601-0001 |
| Governance Item | GOV-{TIER}-{DATE:YYYYMMDD}-{SEQ:06d} | GOV-TIER2-20260601-000001 |
| Feedback Signal | FBK-{TYPE}-{DATE:YYYYMMDD}-{SEQ:08d} | FBK-TRADEOUTCOME-20260601-00000001 |

---

### L.2 Canonical Learning Record: Strategy Performance (LT-10)

A complete, canonical Learning Record for a Strategy Learning event:

**Header fields:**

| Field | Value (example) |
|---|---|
| record_id | LRN-STRATEGY-20260601-00000042 |
| learning_type | LT-10 |
| learning_type_label | STRATEGY_LEARNING |
| created_at | 2026-06-01T16:00:05.342Z |
| session_date | 2026-06-01 |
| status | PENDING_PROCESSING |
| source_layer | LearningSystem |
| source_component | LC-09 (Outcome Analyzer) |
| pit_snapshot_at | 2026-06-01T15:59:59.999Z |

**Content fields:**

| Field | Value (example) |
|---|---|
| strategy_id | STR-MEAN_REVERSION_007 |
| session_win_rate | 0.62 |
| session_trades | 8 |
| session_pnl | 2450 (INR) |
| regime_at_session | RANGING |
| rolling_30d_win_rate | 0.58 |
| rolling_30d_sharpe | 0.89 |
| current_ml_weight | 0.14 |
| evidence_quality | HIGH |
| requires_pattern_discovery | True |

**Provenance fields:**

| Field | Value |
|---|---|
| source_trade_ids | [TRD-20260601-00001, ..., TRD-20260601-00008] |
| source_session_report | LRPT-20260601-0001 |
| audit_trail | LAUD-LRN-STRATEGY-20260601-00000042-0001 |

---

### L.3 Canonical Learning Record: Error Pattern (LT-21)

**Header:**

| Field | Value |
|---|---|
| record_id | LRN-ERROR-20260601-00000007 |
| learning_type | LT-21 |
| learning_type_label | ERROR_LEARNING |
| created_at | 2026-06-01T09:18:32.117Z |
| source_layer | ExecutionEngine |
| source_component | LC-11 (Error Analyzer) |
| status | PENDING_PROCESSING |

**Content:**

| Field | Value |
|---|---|
| error_code | ORDER_REJECTED |
| error_sub_code | PRICE_TICK_SIZE_VIOLATION |
| instrument | NIFTY24JUN22000CE |
| order_time | 2026-06-01T09:17:45.003Z |
| distance_to_expiry_mins | 12 |
| occurrence_count_7d | 3 |
| occurrence_count_30d | 9 |
| pattern_candidate_id | PAT-ERROR-20260601-000003 |
| severity | HIGH |
| impact_pnl_est | -420 (INR) |

---

### L.4 Canonical Pattern Record

A fully promoted, ACTIVE pattern record:

| Field | Value (example) |
|---|---|
| pattern_id | PAT-STRATEGY-20260510-000007 |
| pattern_class | STRATEGY_OUTCOME_REGIME_DEPENDENT |
| description | STR-MEAN_REVERSION_007 performs significantly better in RANGING regimes |
| domain | STRATEGY |
| source_learning_type | LT-10 |
| confidence | 0.82 |
| effect_size | 0.51 (Sharpe differential) |
| instance_count | 20 (RANGING) + 45 (TRENDING_BULL) |
| p_value | < 0.001 |
| lqs_score | 0.877 |
| regime_applicability | [RANGING, TRENDING_BULL] |
| first_observed | 2026-05-10 |
| last_validated | 2026-06-01 |
| validation_count | 3 |
| status | ACTIVE |
| derived_updates | [KU-METAWT-20260510-000002] |
| audit_chain | [LAUD-..., LAUD-...] |

---

### L.5 Canonical Knowledge Update Record

| Field | Value (example) |
|---|---|
| ku_id | KU-METAWT-20260510-000002 |
| source_pattern_id | PAT-STRATEGY-20260510-000007 |
| update_type | STRATEGY_WEIGHT_DELTA |
| target_layer | MetaLearning (Layer 3) |
| target_parameter | strategy_weight[STR-MEAN_REVERSION_007][RANGING] |
| prior_value | 0.14 |
| proposed_value | 0.19 |
| delta | +0.05 |
| governance_tier | TIER-2-ADVISORY |
| governance_id | GOV-TIER2-20260510-000009 |
| lqs_at_proposal | 0.877 |
| status | DEPLOYED |
| deployed_at | 2026-05-10T16:10:02.551Z |
| post_deploy_sessions | 5 |
| post_deploy_outcome | EFFECTIVE |
| rollback_available | True |
| rollback_value | 0.14 |
| audit_chain | [LAUD-..., LAUD-..., LAUD-...] |

---

### L.6 Summary of Learning Type × Component Responsibility Matrix

| Learning Type | Primary Collector | Primary Analyzer | Primary Output Component |
|---|---|---|---|
| LT-01 Observation | LC-03 | LC-04 | LC-05 Pattern Discovery |
| LT-02 Evidence | LC-03 | LC-09 Outcome Analyzer | LC-06 Knowledge Updater |
| LT-03 Hypothesis | LC-03 | LC-09 | LC-06 |
| LT-04 Reasoning | LC-03 | LC-09 | LC-06 |
| LT-05 Decision | LC-03 | LC-07 Model Improvement | LC-07 |
| LT-06 Execution | LC-03 | LC-09 | LC-06 |
| LT-07 Outcome | LC-03 | LC-09 | LC-05 + LC-06 |
| LT-08 Risk | LC-03 | LC-10 Performance Analyzer | LC-06 |
| LT-09 Portfolio | LC-03 | LC-10 | LC-06 |
| LT-10 Strategy | LC-03 | LC-09 + LC-10 | LC-06 |
| LT-11 Behavioral | LC-03 | LC-05 | LC-20 Recommendation |
| LT-12 Market | LC-03 | LC-05 | LC-06 |
| LT-13 Macro | LC-03 | LC-05 | LC-06 |
| LT-14 Sector | LC-03 | LC-05 | LC-06 |
| LT-15 Company | LC-03 | LC-05 | LC-06 |
| LT-16 Cross-Market | LC-03 | LC-05 | LC-06 |
| LT-17 Cross-Asset | LC-03 | LC-05 | LC-06 |
| LT-18 AI Model | LC-03 | LC-07 Model Improvement | LC-07 |
| LT-19 Human Feedback | LC-08 Feedback Manager | LC-08 | LC-06 |
| LT-20 Meta Learning | LC-19 Analytics | LC-19 | LC-15 Governance |
| LT-21 Error | LC-11 Error Analyzer | LC-11 | LC-20 Recommendation |

---

## END OF SUPPLEMENT MATERIAL

---

## SUPPLEMENT M — LEARNING ENGINE QUICK-START REFERENCE CARD

This supplement provides a concise operational reference. It is intended for human operators who need a fast lookup of key numbers, thresholds, identifiers, and rules without reading the full document.

---

### M.1 Critical Thresholds — At a Glance

| Threshold | Value | Reference |
|---|---|---|
| Minimum evidence instances before pattern promotion | 10 | Part IV |
| Minimum p-value for statistical significance | < 0.05 | Part IV |
| Minimum effect size for deployment | > 5% | Part IV |
| Out-of-sample reserved fraction | 20% of history | Part IV |
| Minimum post-deployment monitoring sessions | 5 | Part IV |
| Maximum strategy weight change per update cycle | 5% (configurable) | GDR-LRN-003 |
| Maximum confidence prior change per update cycle | 0.05 (configurable) | GDR-LRN-003 |
| LQS minimum for deployment (ACCEPTABLE) | 0.55 | Part VII |
| Feedback decay half-life (trade outcomes) | 60 sessions | Supplement C |
| Human feedback decay | No decay | Supplement C |
| Rollback trigger: performance degradation | > 5% on target metric | Part IV |
| LSHS emergency threshold | < 0.35 | Supplement J |
| Meta learning effectiveness target | > 60% | Supplement I |
| Rollback rate target | < 5% | Supplement J |
| Human override rate target | < 3% | Supplement J |

---

### M.2 The Five Things the Learning Engine Never Does

1. **Never executes trades.** The Learning Engine has no connection to the Order Manager or broker interfaces. It cannot place, modify, or cancel an order.

2. **Never makes an investment decision.** No learning output constitutes a trade recommendation. Learning outputs are knowledge updates to models and parameters; they improve future decisions but are not decisions themselves.

3. **Never modifies the Kill Switch.** GDR-LRN-007 is absolute. Kill Switch activation logic, persistence, and deactivation requirements are entirely outside the Learning Engine's scope.

4. **Never applies an unvalidated update.** Every knowledge update must pass the 5-stage validation pipeline and governance approval before deployment. There is no shortcut path.

5. **Never operates without an audit trail.** GDR-LRN-004 requires the Audit Manager to record every update before it is applied. If the Audit Manager is down, updates are held. There is no audit-bypassing mode.

---

### M.3 What Triggers an Automatic Rollback

| Trigger | Action |
|---|---|
| Post-deployment performance degradation > 5% on target metric | Automatic rollback proposal → TIER-2-ADVISORY |
| LSHS drops below 0.55 within 5 sessions of a knowledge update | Automatic rollback proposal |
| New error rate increases > 2× baseline within 5 sessions of update | Automatic rollback proposal |
| Knowledge Audit hash chain integrity failure | HALT all updates; alert operator |

---

### M.4 Governance Decision Tree (Quick Reference)

`
New Knowledge Update proposed
           │
           ▼
   Impact Assessment
           │
     ╔═════╧══════╗
     ║  Low impact ║ (< 1% change) → TIER-1-AUTO → Apply immediately
     ╚═════╤══════╝
           │
     ╔═════╧══════╗
     ║ Medium impact║ (1-10% change) → TIER-2-ADVISORY → Auto-approve + notify
     ╚═════╤══════╝
           │
     ╔═════╧══════╗
     ║  High impact ║ (> 10% change) → TIER-3-HUMAN → Await operator approval
     ╚═════╤══════╝
           │
     ╔═════╧══════╗
     ║ Structural   ║ (model architecture) → TIER-4-COMMITTEE → Multi-reviewer
     ╚═════════════╝
`

Additional TIER-3-HUMAN triggers regardless of impact size:
- LQS < 0.55 (MARGINAL)
- Any change to risk parameters
- Any change to governance tier definitions
- First deployment of a new model
- Any rollback (even within TIER-1 threshold)

---

### M.5 Complete Learning Type Quick Lookup

| Code | Type | What it learns | Output |
|---|---|---|---|
| LT-01 | Observation Learning | Observation completeness and accuracy | Data quality rules |
| LT-02 | Evidence Learning | Evidence signal predictive value | Evidence confidence weights |
| LT-03 | Hypothesis Learning | Hypothesis validation rates | Hypothesis confidence priors |
| LT-04 | Reasoning Learning | Reasoning chain quality | Inference chain weights |
| LT-05 | Decision Learning | DCS calibration | DCS model recalibration |
| LT-06 | Execution Learning | EQS; slippage; order type | Execution parameter updates |
| LT-07 | Outcome Learning | Trade outcome patterns | Pattern discoveries |
| LT-08 | Risk Learning | Risk model accuracy | Risk model recalibration |
| LT-09 | Portfolio Learning | Portfolio-level patterns | Portfolio parameter updates |
| LT-10 | Strategy Learning | Per-strategy performance | Strategy weight adjustments |
| LT-11 | Behavioral Learning | IIOS own behavioral patterns | Behavioral rule updates |
| LT-12 | Market Learning | Market microstructure patterns | Market model updates |
| LT-13 | Macro Learning | Macro impact on IIOS | Macro prior updates |
| LT-14 | Sector Learning | Sector rotation patterns | Sector model updates |
| LT-15 | Company Learning | Company-specific patterns | Company confidence adjustments |
| LT-16 | Cross-Market Learning | Cross-market correlations | Cross-market models |
| LT-17 | Cross-Asset Learning | Cross-asset regime signals | Cross-asset priors |
| LT-18 | AI Model Learning | AI model performance | Model architecture feedback |
| LT-19 | Human Feedback Learning | Operator overrides and corrections | Confidence model adjustments |
| LT-20 | Meta Learning | Learning Engine effectiveness | Learning process improvements |
| LT-21 | Error Learning | Error recurrence patterns | Prevention rule proposals |
