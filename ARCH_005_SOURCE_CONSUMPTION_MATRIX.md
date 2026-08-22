# ARCH-005 Source Consumption Matrix
## KDA Evidence Pipeline: Producer → Storage → Consumer → Decision Influence

**Scope:** All data sources flowing through the KDA pipeline as of ARCH-005  
**KFE Pool (as of ARCH-004):** 2819 records | OOS annotated: 106 (32 PASSED, 57 FAILED, 17 TESTED)

---

## Legend

| Status | Meaning |
|---|---|
| `CONNECTED` | Source is produced, consumed, and influences KDA decisions |
| `CONNECTED_NO_DECISION` | Source is consumed and stored but doesn't directly change BUY/SELL/HOLD |
| `AVAILABLE_BUT_NOT_DECISION_RELEVANT` | Source data exists but KDA doesn't consume it |
| `SHADOW_ONLY` | Source influences only monitoring/logging, not decisions |
| `PLANNED` | Source identified, wiring not yet implemented |

---

## Matrix

### A. Market Data Sources

| Source | Producer | Storage | KDA Consumer | KFE Angle | Decision Influence | Outcome Feedback | Status |
|---|---|---|---|---|---|---|---|
| NIFTY/BANKNIFTY price | DhanFeed / YFinance | In-memory | HBE → BehaviourMetrics | MARKET | Via ESS (historical pattern match) | EOD via KDAOutcomeEngine | `CONNECTED` |
| Equity price (scanner signals) | YFinance / DhanFeed | TradeSignal | KnowledgeDecisionPipeline | STOCK, DIRECTION, MAGNITUDE | Primary: ESS, target_prob, stop_prob | EOD outcome matching | `CONNECTED` |
| ATR (Average True Range) | Scanner (computed) | TradeSignal.atr | KDA._derive_target_stop() | VOLATILITY | Target/stop fallback when ESS low | — | `CONNECTED` |
| Sector data | MarketIntelligence | MarketContext | HBE (regime context) | SECTOR | ESS segmentation by sector | — | `CONNECTED` |
| VIX level | GlobalDataAI | GlobalSnapshot | RiskGuardian (not KDA) | — | KDA never sees VIX directly; RiskGuardian may VETO | — | `CONNECTED_NO_DECISION` |
| OI (Open Interest) | DhanFeed / yfinance | trade data | KFE via pool records | — | OOS annotation (PASSED/FAILED/TESTED) | KDAOutcomeEngine | `CONNECTED` |

### B. Knowledge Object / Fusion Sources

| Source | Producer | Storage | KDA Consumer | KFE Angle | Decision Influence | Outcome Feedback | Status |
|---|---|---|---|---|---|---|---|
| KnowledgeObject pool | KFE.analyse_record() | SQLite `knowledge_objects` | `run_knowledge_shadow()` Step 3 | ALL 16 angles | ESS → evidence_state; angles → supporting/contradicting | EOD: KDAOutcomeEngine | `CONNECTED` |
| OOS holdout annotation | KFE._annotate_oos_holdout() | KnowledgeFusionRecord | KFE → MultiAngleView | OOS_VALIDATION | oos_pass_rate → SUPPORT if ≥0.6, CONTRADICT if <0.3 | — | `CONNECTED` |
| HBE BehaviourMetrics | HBE.get_behaviour_profile() | In-memory (not persisted) | `_shadow_impl()` Step 2 | Implicit via ESS | target_hit_prob, stop_first_prob, expected_move, horizon | — | `CONNECTED` |
| KFE recency fraction | KFE pool | KnowledgeFusionRecord | KDA._extract_recency() | RECENCY | SUPPORT if ess_fraction ≥ 0.5 | — | `CONNECTED` |
| Source redundancy | KFE pool | KnowledgeFusionRecord | KDA._count_sources() | REDUNDANCY | authority component: source_diversity | — | `CONNECTED` |
| Contradiction count | KFE pool | KnowledgeFusionRecord | KDA._extract_contradiction_factor() | CONTRADICTION | major contradictions → contradiction_factor → evidence_state gating | — | `CONNECTED` |

### C. Strategy / Context Sources

| Source | Producer | Storage | KDA Consumer | KFE Angle | Decision Influence | Outcome Feedback | Status |
|---|---|---|---|---|---|---|---|
| Scanner confidence | EquityScannerAI | TradeSignal.scanner_confidence | KDA.evaluate() obs dict | — | authority: relevance component (conf/10) | — | `CONNECTED` |
| Strategy context (StrategyLab) | MetaStrategyController | In-memory | KDA._parse_strategy_context() | — | KDA relationship classification (ALIGNED/DIVERGENT/etc.) | — | `CONNECTED_NO_DECISION` |
| Regime (BULL/BEAR/SIDEWAYS) | MarketIntelligence | MarketContext | HBE evidence segmentation | MARKET (indirect) | ESS segmented by regime in BehaviourMetrics | — | `CONNECTED` |
| MOP-RC-001 observation fields | EquityScannerAI | JSONL observer | KFE pool (future) | — | `expected_move_pct`, `_obs_candidate_score`, `_obs_regime` on TradeSignal | Via daily summary | `CONNECTED_NO_DECISION` |

### D. Angle Sources (all 16 KDA angles)

| Angle Name | Confidence Source | SUPPORT Threshold | CONTRADICT Path | Decision Impact |
|---|---|---|---|---|
| STOCK | KFE pool (symbol-level win_rate) | conf ≥ 0.55 | conf < 0.20 AND n ≥ 10 | Primary directional signal |
| MARKET | KFE pool (index correlation) | conf ≥ 0.55 (NEUTRAL — not in SUPPORT list) | conf < 0.20 AND n ≥ 10 | Weak influence (NEUTRAL most cases) |
| SECTOR | KFE pool (sector correlation) | conf ≥ 0.55 | conf < 0.20 AND n ≥ 10 | Material conflict contributor |
| VOLATILITY | KFE pool (vol regime fit) | conf ≥ 0.55 | conf < 0.20 AND n ≥ 10 | ATR relevance |
| DIRECTION | KFE pool (directional accuracy) | conf ≥ 0.55 | conf < 0.20 AND n ≥ 10 | Primary conflict indicator |
| MAGNITUDE | KFE pool (move size fit) | NEUTRAL (not in SUPPORT list) | — | Weak |
| TIME | KFE pool (session timing fit) | NEUTRAL | — | Weak |
| RISK | KFE pool | NEUTRAL | — | Weak |
| SELECTION | KFE pool | NEUTRAL | — | Weak |
| COUNTERFACTUAL | KFE pool | NEUTRAL | — | Weak |
| LEADER_OUTCOME | KFE pool (leader stock correlation) | conf ≥ 0.55 | conf < 0.20 AND n ≥ 10 | Strong when conflict |
| SOURCE_QUALITY | KFE pool (data source quality) | conf ≥ 0.55 | — | authority: quality component |
| RECENCY | KFE pool (temporal recency) | ess_fraction ≥ 0.5 | — | Freshness signal |
| REDUNDANCY | KFE pool (multi-source agreement) | conf ≥ 0.55 | — | authority: diversity component |
| CONTRADICTION | KFE pool (explicit contradictions) | n_minor = 0 | n_minor > 0 | Direct conflict indicator |
| OOS_VALIDATION | KFE._annotate_oos_holdout() | oos_pass_rate ≥ 0.6 | oos_pass_rate < 0.3 | Evidence quality gate |

### E. Outcome / Learning Sources

| Source | Producer | Storage | KDA Consumer | Decision Influence | Status |
|---|---|---|---|---|---|
| Closed trade outcomes | OrderManager CSV journal | `data/paper_trades.csv` | EOD KDAOutcomeEngine | Updates KFE pool ESS for future evaluations | `CONNECTED` |
| KDA decision ledger | `_shadow_impl()` Step 7 | SQLite | KDAComparativeAnalyzer | Tracks decision accuracy; influences future authority scoring | `CONNECTED` |
| Strategy performance | StrategyPerformanceTracker | In-memory + SQLite | — | Not yet flowing into KDA angles | `AVAILABLE_BUT_NOT_DECISION_RELEVANT` |
| Walk-forward test results | WalkForwardTester | ResearchLab | — | Not yet flowing into KFE angles | `AVAILABLE_BUT_NOT_DECISION_RELEVANT` |
| Debate agent votes | DebateEngine | In-memory | — | KDA is NOT influenced by debate; debate is downstream secondary context | `CONNECTED_NO_DECISION` |

---

## Summary Counts

| Status | Count |
|---|---|
| `CONNECTED` | 14 |
| `CONNECTED_NO_DECISION` | 5 |
| `AVAILABLE_BUT_NOT_DECISION_RELEVANT` | 2 |
| `SHADOW_ONLY` | 0 |
| `PLANNED` | 0 |

---

## Gap Analysis

### Gap 1: StrategyPerformanceTracker → KFE angles (deferred)
- WinRate and auto-disable signals from StrategyPerformanceTracker do not yet flow back into KFE pool records
- Impact: Low. KFE pool is updated via trade outcomes already.
- Decision: Deferred to ARCH-006 or post-live review

### Gap 2: Walk-forward test results → OOS_VALIDATION angle (deferred)
- WalkForwardTester produces OOS metrics but does not write them to KFE records as `oos_pass_rate`
- Current workaround: KFE._annotate_oos_holdout() uses PASSED/FAILED annotation from holdout pool
- Impact: Medium. OOS_VALIDATION angle defaults to NEUTRAL for most symbols
- Decision: Deferred

### Gap 3: MARKET angle consistently NEUTRAL
- MARKET angle (NIFTY/BANKNIFTY index) is not in the SUPPORT name list → always NEUTRAL even with high confidence
- Impact: Low. MARKET never contributes to material conflict (can't CONTRADICT).
- Decision: By design — index direction is context, not signal
