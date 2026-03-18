# AI Trading Brain — Architecture

> This document is the authoritative reference for the system.
> Keep it in sync when modules change. Both humans and AI tools use it.

---

## 1. What This System Is

A **17-layer hierarchical multi-agent trading system** for Indian equity and derivatives markets (NSE).  
~62 specialized agents work in a strict top-down pipeline — each layer feeds the next.  
The system never trades blindly: every signal must survive regime detection, backtesting quality gates, a 5-agent debate, a decision threshold, and a hard risk kill-switch before reaching the broker.

**Current mode:** Paper trading (`main.py --paper`). Live orders routed through Zerodha (simulation) or Dhan (login ✅, data API blocked 451 → yfinance fallback).

---

## 2. Entry Points

```
python main.py                 # one immediate analysis cycle
python main.py --paper         # paper mode, no live orders
python main.py --schedule      # daemon mode, intraday schedule
python main.py --telegram      # Telegram bot (@Amitkhatkarbot)
python main.py --evolve        # genetic algorithm evolution pass
python main.py --backtest      # re-run all strategy backtests
python main.py --discover      # Edge Discovery Engine manually
python main.py --report        # learning engine report
python main.py --dashboard     # Streamlit Control Tower dashboard
python main.py --readiness     # system readiness pre-flight (28 checks)
```

---

## 3. Layer Map

Each layer runs inside `SystemMonitor.time_layer()` — latency tracked, WARN/CRIT thresholds enforced.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Layer  Name                   Agent(s)                  Output       │
├──────────────────────────────────────────────────────────────────────┤
│  1     GlobalIntelligence     GlobalIntelligenceEngine  PremarketBias│
│  2     MarketIntelligence     MarketDataAI + RegimeAI   RegimeLabel  │
│  3     MetaLearning           MetaLearningEngine         WeightMap   │
│  4     OpportunityEngine      EquityScanner +            TradeSignals │
│                               OptionsOpportunity + Arb               │
│  5     StrategyLab            MetaStrategyController +   Signals w/  │
│                               BacktestingAI              quality gate │
│  6     CapitalRiskEngine      CapitalRiskEngine          Sized signals│
│  7     RiskControl            RiskManagerAI +            Approved     │
│                               PortfolioAllocation +      signals      │
│                               StressTestAI                            │
│  8     MarketSimulation       SimulationEngine (MC×1000) Risk-adjusted│
│  9     RiskGuardian           FailSafeRiskGuardian       Final gate   │
│ 10     DebateAndDecision      MultiAgentDebate (×5) +    APPROVE /   │
│                               DecisionEngine             REJECT       │
│ 11     ExecutionEngine        OrderManager →             Order placed │
│                               ZerodhaBroker (sim)                     │
│ 12     TradeMonitoring        TradeMonitor +             Position     │
│                               StrategyHealthMonitor      health       │
│ 13     LearningSystem         LearningEngine +           Updated      │
│                               StrategyPerformanceTracker weight DB    │
│ 14     PerformanceAnalytics   DrawdownAnalyzer +         Analytics    │
│                               WalkForwardTester                       │
│ 15     ResearchLab            ResearchLab                LabResult    │
│ 16     ValidationEngine       ValidationEngine (6-stage) Validated    │
│ 17     ControlTower           TelemetryLogger +          SQLite +     │
│                               EventStreamMonitor + …     Dashboard    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Layer Detail

### Layer 1 — GlobalIntelligence
**File:** `global_intelligence/__init__.py`  
**Class:** `GlobalIntelligenceEngine`

Pipeline run once per cycle before market data is fetched:
```
GlobalDataAI → MacroSignalAI → CorrelationEngine → GlobalSentimentAI → PremarketBiasAI
```
Returns `PremarketBias` consumed by `MarketRegimeAI`.

**Performance:** 17ms (background pre-warm thread fills 5-min cache at init so the first cycle is instant).
```python
GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot   # ← interface locked
```

---

### Layer 2 — MarketIntelligence
**Files:** `market_intelligence/`  
**Classes:** `MarketDataAI`, `MarketRegimeAI`, `SectorRotationAI`, `LiquidityAI`, `EventDetectionAI`, `MarketMonitor`

`MarketRegimeAI` classifies into one of four regimes:

| Regime | Condition |
|---|---|
| `BULL_TREND` | ADV/DEC > 60%, VIX < 18 |
| `RANGE_MARKET` | 40% < ADV/DEC < 60%, VIX 18–22 |
| `VOLATILE` | VIX > 22 |
| `BEAR_MARKET` | ADV/DEC < 40%, PCR > 1.2 |

`MarketMonitor` runs a **30s continuous light scan** in a background thread, plus **6 scheduled deep scans** (09:05, 09:10, 09:20, 10:30, 13:00, 15:00). Fires `VOLUME_SPIKE`, `CIRCUIT_DROP_ALERT`, `BREAKOUT_TICK`, `VIX_SPIKE` events onto the `EventBus`.

---

### Layer 3 — MetaLearning
**File:** `meta_learning/`  
**Classes:** `MetaLearningEngine`, `MetaModel` (k-NN, k=10), `StrategyWeightPredictor`, `RegimeStrategyMap`

Predicts optimal strategy weights from recent regime + performance features.  
`RegimeStrategyMap` learns which strategy wins in each regime (needs ≥5 trades before rankings are trusted).

---

### Layer 4 — OpportunityEngine
**File:** `opportunity_engine/`  
**Classes:** `EquityScannerAI` (8-stock watchlist), `OptionsOpportunityAI`, `ArbitrageAI`

Generates raw `TradeSignal` objects passed to StrategyLab for quality-gating.

---

### Layer 5 — StrategyLab
**File:** `strategy_lab/`  
**Classes:** `MetaStrategyController`, `StrategyGeneratorAI`, `BacktestingAI`, `StrategyEvolutionAI`

`MetaStrategyController` selects active strategies per regime:

| Regime | Active strategies |
|---|---|
| `BULL_TREND` | Breakout_Volume, Momentum_Retest, Bull_Call_Spread, Breakout_Volume_RSI_HiVol |
| `RANGE_MARKET` | Mean_Reversion, Iron_Condor_Range, ETF_NAV_Arb, Mean_Reversion_RSI_HiVol |
| `VOLATILE` | Short_Straddle_IV_Spike, Long_Straddle_Pre_Event, Futures_Basis_Arb |
| `BEAR_MARKET` | Hedging_Model, Iron_Condor_Range, Short_Straddle_IV_Spike |

Also auto-includes any evolved variants from `data/evolved_strategies.json` that pass quality gates.

`BacktestingAI` enforces three gates before a signal is forwarded: **WalkForward ≥ 80%**, **OverfitScore < 3.0**, **CrossMarket ≥ 50%**.

---

### Layer 6 — CapitalRiskEngine
**File:** `risk_control/capital_risk_engine.py`  
**Class:** `CapitalRiskEngine`

Sizes each signal based on strategy budget allocation. Capital = ₹1,000,000 (configurable). Deployable = 50%.

---

### Layer 7 — RiskControl
**Files:** `risk_control/`  
**Classes:** `RiskManagerAI`, `PortfolioAllocationAI`, `StressTestAI`

Per-signal risk checks: max 1% capital per trade, 5% total portfolio risk. Stress-tests 4 scenarios.

---

### Layer 8 — MarketSimulation
**File:** `market_simulation/simulation_engine.py`  
**Class:** `SimulationEngine`

Runs 1,000 Monte Carlo scenarios × 14 regime scenarios per signal.

---

### Layer 9 — RiskGuardian ⛔ PROTECTED
**File:** `risk_guardian/risk_guardian.py`  
**Class:** `FailSafeRiskGuardian`

Hard kill-switch. Six circuit-breakers checked in priority order. If any fires, the cycle halts.

| Breaker | Threshold |
|---|---|
| Daily loss | > 2% of capital |
| Portfolio risk | > 5% |
| Open trades | > 8 |
| NIFTY intraday drop | > 5% |
| VIX | > 45 |
| Consecutive losses | ≥ 3 → pause |
| Margin buffer | < 20% |

Returns `GuardianDecision(approved, rule_triggered, reason, approved_signals, rejected_signals)`.

---

### Layer 10 — DebateAndDecision
**Files:** `debate_system/`, `decision_ai/`  
**Classes:** `MultiAgentDebate`, `DecisionEngine`

5 debater agents score every signal independently:

| Agent | Weight |
|---|---|
| Technical | 0.30 |
| Risk | 0.25 |
| Macro | 0.20 |
| Sentiment | 0.15 |
| Regime | 0.10 |

`DecisionEngine` aggregates votes → weighted score → threshold check (`MIN_CONFIDENCE_SCORE = 6.5`).  
Signals scoring < 6.5 are rejected before any order is placed.

---

### Layer 11 — ExecutionEngine
**File:** `execution_engine/order_manager.py`  
**Class:** `OrderManager`

Routes approved signals to the configured broker. Retries up to 3×. Maintains live `Portfolio`.  
Active broker set via `ACTIVE_BROKER` in `config.py` (zerodha | dhan | angelone).

---

### Layer 12 — TradeMonitoring
**File:** `trade_monitoring/`  
**Classes:** `TradeMonitor`, `StrategyHealthMonitor`

Watches open positions for stop-loss / target hits. `StrategyHealthMonitor` tracks per-strategy health and disables strategies that degrade.

---

### Layer 13 — LearningSystem
**Files:** `learning_system/`  
**Classes:** `LearningEngine`, `StrategyPerformanceTracker`

`LearningEngine` runs EOD — adjusts weights in `data/learning_db.json` from closed trade outcomes.  
`StrategyPerformanceTracker` auto-disables a strategy when (after ≥10 trades):
- Win rate < 35%, or
- Expectancy < −0.30R, or
- 5 consecutive losses

---

### Layer 14 — PerformanceAnalytics
**File:** `performance/`  
**Classes:** `DrawdownAnalyzer`, `WalkForwardTester`, `RegimePerformanceTracker`, `StrategyAttribution`, `PerformanceEvaluator`

---

### Layer 15 — ResearchLab
**File:** `research_lab/research_lab.py`  
**Class:** `ResearchLab`

Isolated sandbox. New strategies are tested here before promotion. Promotion gates:

| Gate | Threshold |
|---|---|
| Return | > 0% |
| Win rate | ≥ 50% |
| Max drawdown | < 15% |
| Sharpe ratio | > 0.8 |
| Walk-forward pass | ≥ 60% |

---

### Layer 16 — ValidationEngine ⛔ PROTECTED
**File:** `validation_engine/`  
**Class:** `ValidationEngine`

6-stage sequential pipeline. A strategy must pass **all 6 stages** in order to be promoted.

```
IS/OOS Backtest → Walk-Forward → Cross-Market → Monte Carlo → Parameter Sensitivity → Regime Robustness
```

Requires minimum 30 trades. Any stage failure stops the pipeline.

---

### Layer 17 — ControlTower
**File:** `control_tower/`  
**Class:** `ControlTower` (singleton)

Passive observability only — subscribes to `EventBus`, never modifies agent state.

| Sub-module | What it logs |
|---|---|
| `TelemetryLogger` | All events → SQLite (`data/control_tower.db`) — tables: `ct_events`, `ct_cycles`, `ct_decisions` |
| `EventStreamMonitor` | Real-time event flow |
| `AgentStatusMonitor` | Per-agent health |
| `SignalVisualizer` | Signal lifecycle |
| `DecisionTrace` | Full debate → decision audit trail |

Dashboard: `streamlit run control_tower/dashboard_app.py`

---

## 5. Cross-Cutting Infrastructure

### Data Feeds
**File:** `data_feeds/data_feed_manager.py`  
Singleton: `get_feed_manager()`

| Feed | Status | Used for |
|---|---|---|
| `DhanFeed` | Login ✅, data API blocked (451) | Order routing, fallback for Indian quotes |
| `YahooFeed` | ✅ Live | Global indices, Indian indices (^NSEI, ^NSEBANK), all commodities |
| `NSEFeed` | ✅ yfinance-backed | Options chains, PCR, sector data |

```python
BaseFeed.get_quote(symbol: str) -> Optional[TickerQuote]       # ← interface locked
BaseFeed.get_multiple_quotes(symbols: List[str]) -> Dict[...]   # ← interface locked
BaseFeed.get_history(symbol, days, interval) -> List[PriceBar]  # ← interface locked
```

### Communication
**File:** `communication/`  
**Classes:** `EventBus` (singleton `get_bus()`), `MessageRouter`, `TaskQueue`

Thread-safe, priority-ordered (`CRITICAL > HIGH > NORMAL`). Wildcard `"*"` subscription supported.  
`TaskQueue` workers: `TradeMonitor`, `LearningEngine`, `MasterOrchestrator`.

### Notifications
**File:** `notifications/telegram_bot.py`  
**Class:** `TelegramCommandBot` (singleton `get_telegram_bot()`)  
Bot: @Amitkhatkarbot | 13 commands:

```
/start /help /status /nifty /vix /market /snapshot
/perf  /learn /positions /pnl /edges /pause /resume
```

### System Monitor
**File:** `system_monitor/system_monitor.py`

| Constant | Value | Meaning |
|---|---|---|
| `LAYER_LATENCY_WARN_MS` | 2,000 | Default WARN threshold |
| `LAYER_LATENCY_CRIT_MS` | 5,000 | Default CRIT → abort cycle |
| `LAYER_LATENCY_WARN_OVERRIDES["GlobalIntelligence"]` | 5,000 | Raised for network layer |
| `LAYER_LATENCY_CRIT_OVERRIDES["GlobalIntelligence"]` | 12,000 | |

```python
SystemMonitor.time_layer(layer_name: str) -> contextmanager   # ← interface locked
```

### Edge Discovery
**File:** `edge_discovery/edge_discovery_engine.py`  
**Class:** `EdgeDiscoveryEngine`

Discovers new strategy edges from market data patterns. Pipeline:
```
FeatureExtractor → PatternMiner → CandidateStrategyGenerator → StrategyTester → EdgeRankingEngine
```
Requires ≥100 DB rows to mine. Promoted edges written to `data/evolved_strategies.json` and subscribed to `EDGE_DISCOVERED` on EventBus.  
Currently: 8 edges found, 6 active.

---

## 6. Data & Persistence

```
data/
├── control_tower.db          # SQLite — all telemetry (ct_events, ct_cycles, ct_decisions)
├── trading_brain.db          # SQLite — trade history, portfolio state
├── paper_trades.csv          # Paper trading journal — every simulated order (OPEN/CLOSE rows)
├── learning_db.json          # Strategy/agent weight adjustments (EOD learning)
├── evolved_strategies.json   # Evolved strategy variants (earned — do not hand-edit)
├── strategy_performance.json # StrategyPerformanceTracker per-strategy stats
└── regime_strategy_map.json  # RegimeStrategyMap regime→strategy win-rate history
```

---

## 7. Configuration

**File:** `config.py`

| Key constant | Value | Purpose |
|---|---|---|
| `TOTAL_CAPITAL` | ₹1,000,000 | Base capital (from env `TOTAL_CAPITAL`) |
| `MAX_RISK_PER_TRADE_PCT` | 1% | Per-trade risk cap |
| `MAX_PORTFOLIO_RISK_PCT` | 5% | Total portfolio exposure cap |
| `MIN_CONFIDENCE_SCORE` | 6.5 | Debate score floor for execution |
| `CONTINUOUS_SCAN_INTERVAL` | 30s | MarketMonitor tick rate |
| `ACTIVE_BROKER` | `zerodha` | From env `ACTIVE_BROKER` |
| `USE_LIVE_DATA` | True | Enables yfinance / Dhan live data |

---

## 8. Key Singletons

Never instantiate these twice — use the getter functions.

```python
get_feed_manager()           # data_feeds.data_feed_manager
get_performance_tracker()    # learning_system.strategy_performance_tracker
get_regime_strategy_map()    # meta_learning.regime_strategy_map
get_telegram_bot()           # notifications.telegram_bot
get_bus()                    # communication.event_bus
get_instance(bus)            # control_tower (ControlTower)
```

---

## 9. Critical Interfaces — Never Change Signatures

```python
# GlobalDataAI
GlobalDataAI.fetch(force: bool = False) -> GlobalSnapshot

# SystemMonitor
SystemMonitor.time_layer(layer_name: str) -> contextmanager

# MasterOrchestrator
MasterOrchestrator.run_full_cycle() -> None
MasterOrchestrator.start_scheduler() -> None

# BaseFeed
BaseFeed.get_quote(symbol: str) -> Optional[TickerQuote]
BaseFeed.get_multiple_quotes(symbols: List[str]) -> Dict[str, TickerQuote]
BaseFeed.get_history(symbol, days, interval) -> List[PriceBar]
```

---

## 10. Performance Baseline (do not regress)

```
GlobalIntelligence    17ms   ✅  (5-min cache + background pre-warm)
MarketIntelligence    19ms   ✅
MetaLearning           7ms   ✅
OpportunityEngine     86ms   ✅
StrategyLab            9ms   ✅
Full cycle:          172ms   ✅  HEALTHY — 0 alerts
```

---

## 11. Scheduling

The system runs as a Windows scheduled task, auto-starting at **08:00 on weekdays** via `scripts/autostart.bat`. Register it once with:

```
python scripts/setup_windows_task.py           # install
python scripts/setup_windows_task.py --status  # check
python scripts/setup_windows_task.py --uninstall
```

Once running, the intraday timeline is:

```
08:00  _premarket_init           — cache refresh, feed health check, Telegram ping
08:30  _premarket_data_warmup    — refresh NIFTY / BANKNIFTY / VIX quotes

──── market opens 09:15 ──────────────────────────────────────────────────
09:05  MarketMonitor deep scan   — regime detection (callback: _on_deep_scan)
09:10  MarketMonitor deep scan   — first opportunity scan
09:20  MarketMonitor deep scan   — strategy evaluation
09:45  Full cycle (_guarded_cycle)
10:30  MarketMonitor deep scan + full cycle
13:00  MarketMonitor deep scan + full cycle
15:00  MarketMonitor deep scan   — closing analysis
──── continuous ──────────────────────────────────────────────────────────
  *  Every 30s  MarketMonitor light scan  (VOLUME_SPIKE, BREAKOUT_TICK …)
  *  Every 5min open-position monitor (market hours only)
──── EOD ─────────────────────────────────────────────────────────────────
15:35  run_eod_learning          — performance tracker, regime map update
```

**Market-hours guard:** `_is_market_session()` prevents full cycles from firing on weekends or before 09:00 / after 15:31. Deep scans and position monitoring are also gated.

All output appended to `logs/scheduler.log`.

---

## 12. Adding to the System

**Right way to extend:**

| Goal | How |
|---|---|
| New strategy | Add to `ResearchLab`, promote through `ValidationEngine` |
| New data source | Add a new `BaseFeed` subclass, register in `DataFeedManager` |
| New Telegram command | Add handler to `telegram_bot.py`, register in `_handlers` |
| New learning signal | Add to `LearningEngine.learn()` and `StrategyPerformanceTracker` |
| New kill condition | Explicit instruction required — see `risk_guardian/risk_guardian.py` |
| New validation stage | Explicit instruction required — see `validation_engine/` |

**Wrong way:** modifying orchestrator layer order, renaming classes, changing interface signatures, hand-editing `evolved_strategies.json`.
