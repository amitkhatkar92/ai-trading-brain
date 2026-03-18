# AI Trading Brain — Copilot Instructions

## Core Principle: Intentional Evolution

**Modify existing files only when the change improves architecture.**
**Avoid rewrites that break interfaces.**
**Evolution is intentional, not accidental.**

Before touching any file, answer these three questions:
1. Does this change improve correctness, performance, or architecture?
2. Does it preserve all existing public interfaces (class names, method signatures, return types)?
3. Is it the smallest change that achieves the goal?

If any answer is "no" — don't make the change.

**For any change to a core or protected module, state the architectural impact
before writing a single line of code.** Describe: which layers are affected,
which interfaces are touched, and what breaks if the change is wrong.
This prevents blind modifications and gives the user a chance to redirect.

---

## Change Policy

| Type | Allowed? | Rule |
|---|---|---|
| Bug fix | ✅ | Preserve interface, fix behaviour |
| Performance improvement | ✅ | Same interface, faster internals |
| New feature (additive) | ✅ | Add new methods/classes, don't remove old |
| Refactor for clarity | ⚠️ | Only if it removes a real coupling problem |
| Rename / move | ❌ | Never — breaks imports across 17 layers |
| Rewrite working module | ❌ | Never without explicit user instruction |
| Add new file | ✅ | Preferred over modifying existing wiring |

---

## Architecture Overview

**Full detail:** see [ARCHITECTURE.md](../ARCHITECTURE.md)

**Project:** `C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain\`
**Stack:** Python 3.14 | `.venv/` | 17-layer hierarchical multi-agent system | ~62 agents
**Broker:** Dhan (login ✅, data API blocked 451) → yfinance auto-fallback
**Mode:** Paper trading (`main.py --paper`) | Telegram bot (`main.py --telegram`)

### Layer Order (do not reorder)
```
1  GlobalIntelligence      — overnight global context (S&P, Nikkei, bonds, FX)
2  MarketIntelligence      — NIFTY/BANKNIFTY regime, sector, liquidity, events
3  MetaLearning            — k-NN strategy weight predictor
4  OpportunityEngine       — equity scanner, options opportunities, arbitrage
5  StrategyLab             — MetaStrategyController, backtesting, evolution
6  CapitalRiskEngine       — position sizing per strategy budget
7  RiskControl             — RiskManagerAI, PortfolioAllocation, StressTest
8  MarketSimulation        — Monte Carlo, 14 scenarios
9  RiskGuardian            — final kill-switch (VIX>45, daily loss>2%)
10 DebateAndDecision       — 5-agent debate, DecisionEngine (threshold 6.5)
11 ExecutionEngine         — OrderManager → ZerodhaBroker (sim mode)
12 TradeMonitoring         — TradeMonitor, StrategyHealthMonitor
13 LearningSystem          — LearningEngine, StrategyPerformanceTracker
14 PerformanceAnalytics    — DrawdownAnalyzer, WalkForwardTester
15 ResearchLab             — promotion gates: WinRate≥50%, Sharpe>0.8, MaxDD<15%
16 ValidationEngine        — 6-stage: Backtest→WFT→CrossMarket→MC→Sensitivity→Regime
17 ControlTower            — SQLite telemetry, Streamlit dashboard, EventBus
```

### Key Singletons — never instantiate twice
```python
get_performance_tracker()    # learning_system.strategy_performance_tracker
get_regime_strategy_map()    # meta_learning.regime_strategy_map
get_telegram_bot()           # notifications.telegram_bot
get_feed_manager()           # data_feeds.data_feed_manager
```

### Critical Interfaces — never change signatures
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

### Latency Thresholds (system_monitor/system_monitor.py)
```python
LAYER_LATENCY_WARN_MS  = 2_000   # per-layer default
LAYER_LATENCY_CRIT_MS  = 5_000   # per-layer default; abort cycle if exceeded
LAYER_LATENCY_WARN_OVERRIDES = {"GlobalIntelligence": 5_000}
LAYER_LATENCY_CRIT_OVERRIDES = {"GlobalIntelligence": 12_000}
```

### Performance Baseline (current, do not regress)
```
GlobalIntelligence    17ms  ✅  (cache + background pre-warm)
MarketIntelligence    19ms  ✅
Full cycle:          172ms  ✅  HEALTHY
```

---

## Files Modified — Running Log

| File | Reason | Interfaces changed? |
|---|---|---|
| `global_intelligence/global_data_ai.py` | 5-min cache + background pre-warm thread | No — `fetch()` sig unchanged |
| `data_feeds/yahoo_feed.py` | `timeout=8` on `yf.download()` | No |
| `system_monitor/system_monitor.py` | Per-layer WARN/CRIT overrides | No |
| `orchestrator/master_orchestrator.py` | +MarketMonitor, +StrategyPerformanceTracker, +RegimeStrategyMap | No |
| `config.py` | SCHEDULE expanded, CONTINUOUS_SCAN_INTERVAL=30 | No |
| `market_intelligence/market_monitor.py` | NEW — 30s continuous scan + 6 deep-scan slots | N/A |
| `learning_system/strategy_performance_tracker.py` | NEW — win rate / auto-disable | N/A |
| `meta_learning/regime_strategy_map.py` | NEW — regime→strategy learning map | N/A |
| `notifications/telegram_bot.py` | +/perf, +/learn commands (13 total) | No |
| `orchestrator/master_orchestrator.py` | Full scheduler rewrite: pre-market init, market-hours guard, all 10 slots | No |
| `main.py` | SIGTERM handler for clean scheduler shutdown | No |
| `scripts/autostart.bat` | NEW — Windows Task Scheduler entry point | N/A |
| `scripts/setup_windows_task.py` | NEW — registers 08:00 weekday Task Scheduler job | N/A |
| `strategy_lab/strategy_generator_ai.py` | Bug fix: `_best_evolved_variant` now filters by `min_signal_rr`; `_load_evolved_strategies` now honours explicit `min_rr` from JSON | No |
| `execution_engine/order_manager.py` | Explicit `PAPER_TRADING` check; persistent CSV journal at `data/paper_trades.csv` | No |
| `main.py` | Dynamic date (was hardcoded); removed shadowing `_dt` local import | No |

---

## Protected Modules (edit only with explicit instruction)

These modules are stable and load-bearing. They may evolve, but only when the
user explicitly asks. Never modify them speculatively or as a side-effect of
another change.

| Module | Why protected | What explicit approval unlocks |
|---|---|---|
| `risk_guardian/risk_guardian.py` | Kill-switch logic is intentional — wrong edit = real money loss | New kill conditions, threshold tuning |
| `strategy_lab/backtesting_ai.py` | WFT/OOS quality gates are calibrated | New metrics, additional test types |
| `validation_engine/` | 6-stage pipeline, promotion criteria set | New validation stage, adjusted thresholds |
| `strategy_lab/evolved_strategies/` | Earned through evolution runs — not hand-written | Parameter tuning, fitness re-evaluation |
| `data/` directory | Live SQLite databases + persisted state | Schema migrations only, never destructive |
| `data_feeds/dhan_feed.py` | Broker auth + order routing — bugs here affect live orders | New endpoint mapping, fallback logic |
