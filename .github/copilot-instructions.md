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
| `orchestrator/master_orchestrator.py` | `_do_monitor`: index symbols (NIFTY/BANKNIFTY) exempt from `.NS` suffix — use bare names so `GLOBAL_SYMBOL_MAP` routes to `^NSEI`/`^NSEBANK`; `_do_eod_learning`: recovers CSV-closed trades from today to handle post-restart zero-count; strategy attribute lookup fixed (`strategy` over `strategy_name`) | No |
| `autonomous_research/rc_models.py` | NEW — Pure data models for ResearchCoordinator: `ResearchStage`, `ResearchRun`, `ResearchTelemetry`, `ResearchSummary`, `RCStatus`, `ResearchHealth`, `ResearchStageState`, stage constants | N/A |
| `autonomous_research/rc_config.py` | NEW — `RCConfig` dataclass with per-stage toggles and `dry_run` | N/A |
| `control_tower/telemetry_logger.py` | **DTA-BLOCKERS-001**: SQLite `timeout=30→1` + `PRAGMA busy_timeout=800` on BOTH `sqlite3.connect()` calls in `_connect()`. Prevents 30s×2=60s block per cycle when dashboard reader holds WAL lock on `control_tower.db`. | No |
| `control_tower/mi_latency_audit.py` | **DTA-BLOCKERS-001**: Added `timeout=1`, `PRAGMA busy_timeout=800`, `PRAGMA integrity_check` (corrupt→auto-recreate) in `_get_conn()`. Wrapped `_write_record()` in `try/except sqlite3.DatabaseError` with `self._conn=None` reset. | No |
| `scripts/dhan_auth/dhan_token_agent.py` | **DTA-BLOCKERS-001**: TOTP generated fresh per retry window instead of once; on `Invalid TOTP` (API_ERROR_IN_200) waits for next 30s TOTP window and retries up to 2×. On exhaustion: sends Telegram alert with step-by-step TOTP re-registration instructions pointing to Dhan portal. | No |
| `autonomous_research/__init__.py` | Added RC exports: `ResearchCoordinator`, `RCConfig`, all RC models and constants | No |
| `test_rc.py` | NEW — 190/190 tests (T001–T190) | N/A |
| `models/trade_signal.py` | MOP-RC-001: added `expected_move_pct`, `_obs_candidate_score`, `_obs_regime` (all `Optional`, default `None`) | No |
| `opportunity_engine/equity_scanner_ai.py` | MOP-RC-001: compute+attach observational fields in `scan()`, extend `[EdgeTelemetry]`, call observer | No |
| `opportunity_engine/mop_rc001_observer.py` | NEW — MOP-RC-001 append-only JSONL observer, `record_signal_observation()`, `write_daily_summary_md()` | N/A |
| `test_mop_rc001.py` | NEW — 15 tests (T001–T015): formula, None-safety, invariance, no look-ahead, dedup | N/A |
| `.gitignore` + `.dockerignore` | Gitignore ALL runtime/research data: KEL, shadow evidence, KSL state, options, iv_history, LOL, scanner_memory, regime_history, scheduler_health, trade_analytics, **strategy_performance, odm_state, knowledge_pipeline_health, ml_performance_dataset, paper_trading_daily, discovered_edges, evolved_strategies, ars_hypothesis_registry, ars_study_\*.json, ars/rc/history.json, mover_discovery\*, klp/knowledge_fusion/source_inventory** | No |
| `scripts/safe_pull.sh` | NEW — backs up all runtime data, runs git pull, restores files. Use instead of bare `git pull` in deployment commands | N/A |
| `build_manifest.json` | Regenerated; deploy command now includes `generate_build_manifest.py` to prevent DeploymentDrift | No |
| `orchestrator/master_orchestrator.py` | Universe rebuild: Monday-only guard removed, schedule moved from 08:30 to 16:15 IST, runs daily post-market | No |
| `audit/dta041_pit_discovery_evidence.py` | DTA-041 Phase 2: `record_outcome` for immutable PIT_OUTCOME appends | No |
| `opportunity_engine/klp_outcome_engine.py` | DTA-041 Phase 2: `fill_pending_pit_outcomes` to resolve matured PIT outcomes from OHLCV bars | No |
| `opportunity_engine/historical_behaviour_engine.py` | DTA-041 Phase 2: `_load_pit_discovery_file` + maturity-enforced ingestion into HBE evidence pool | No |
| `tests/test_dta041_phase2_delayed_outcome.py` | DTA-041 Phase 2: 4 new tests proving maturity enforcement, lineage preservation, HBE ingestion, and empirical profile updates | N/A |
| `risk_control/capital_risk_engine.py` | DTA-CRE-DIAG-001: `get_last_cycle_dominant_rejection_reason()` getter exposing the already-computed dominant rejection reason | No |
| `execution_engine/order_manager.py` | DTA-AET-DIAG-001: AET CONFIRMATION deferral log now states the real trigger (distortion flags, or VIX) instead of always printing a VIX comparison | No |
| `control_tower/pipeline_forensic_reporter.py` | DTA-KDA-DIAG-001: `record_kda_authority()` + new `[PipelineKDA]` daily summary line (StrategyLab-override rate as a standing metric) | No |
| `orchestrator/master_orchestrator.py` | DTA-CRE-DIAG-001/DTA-AET-DIAG-001/DTA-KDA-DIAG-001 wiring; DTA-KDA-FINAL-AUTHORITY-001: formalized KDA as sole final BUY/SELL/REJECT authority, StrategyLab explicitly observation-only; DTA-KDA-CONV-002: made the KDA conviction win-rate term symmetric (previously only rewarded win-rate >55%, never penalized <55%, letting large sample size alone produce high conviction on poor-track-record setups) | No |
| `ARCHITECTURE.md` | Layer 5: added explicit ARCHITECTURAL RULE callout formalizing KDA as sole final trading authority, StrategyLab as observation-only | N/A |
| `orchestrator/master_orchestrator.py` | DTA-OPTIONS-CRE-ISOLATION-001 (Phase D root-cause fix): options/spread signals now split out of `enriched_signals` BEFORE `CapitalRiskEngine`, not after `RiskControl` as before. Root cause: CRE ranked equity+options+arb together under one shared `MAX_POSITIONS` cap; equity's 25-40 candidates/cycle vs options' ~2/cycle meant options were crowded out on effectively every cycle (100% of CRE rejections in the `rejection_audit.db` retention window were `MAX_POSITIONS_CAP`). Options now bypass CapitalRiskEngine entirely — `OptionsRiskEngine` remains their sole, independent capital gate. Equity's `enriched_signals`, ranking, and cap are untouched | No |
| `strategy_lab/strategy_generator_ai.py` | DTA-OPTIONS-ISOLATION-001: added missing `Bear_Put_Spread` entry to `STRATEGY_PARAMS` (was absent, causing StrategyLab to silently relabel Bear_Put_Spread signals to `Hedging_Model` via the regime fallback path); exempted OPTIONS/SPREAD signal types from the SHM/PerfTracker active-set exclusion in `_assign()` and the final hard gate in `assign_strategy()` so StrategyLab stays observation-only for options (mirrors the KDA-supremacy rule already established for equity) — equity behavior unchanged | No |
| `strategy_lab/meta_strategy_controller.py` | DTA-OPTIONS-ISOLATION-001: added `Bear_Put_Spread` to `_REGIME_MAP[BEAR_MARKET]` (was missing, so it never appeared in the regime candidate set) | No |
| `risk_control/capital_risk_engine.py` | DTA-OPTIONS-ISOLATION-001: added `Bear_Put_Spread` to `_STRATEGY_SHARE` (12%, mirrors `Bull_Call_Spread`) | No |
| `strategy_lab/backtesting_ai.py` | DTA-OPTIONS-ISOLATION-001: added `Bear_Put_Spread` to `_BACKTEST_CACHE` (mirrors `Bull_Call_Spread`'s pre-seeded gate-passing profile), removing reliance on `filter_by_backtest()`'s fail-open default | No |
| `opportunity_engine/options_opportunity_ai.py` | DTA-HEDGING-MODEL-001: implemented `_build_hedging_model()` — a Bear Call credit spread (defined max loss by construction), realizing the long-reserved but never-built `Hedging_Model` strategy slot (best pre-seeded Sharpe/drawdown in the roster). Registered in the `builders` dict; `_select_strategy()`'s BEAR_MARKET branch now prefers `Hedging_Model` when IVR ≥ `IVR_SELL_THRESHOLD` (enough premium to justify selling), falling back to the existing `Bear_Put_Spread` debit spread otherwise. Chosen over a naive protective put per prior (disconnected) research in `analysis/options_backtester.py` showing protective puts underperform (13.4% WR, PF 0.77) vs credit spreads | No |
| `opportunity_engine/options_opportunity_ai.py` | DTA-OPTIONS-SELF-LEARNING-001 (Phase D completion): `_base_confidence()` now also consumes `OptionsUnderlyingResponseTracker.get_distribution()` (block 3) — the "underlying move → option move" leverage-capture research, previously computed and persisted but never fed into any decision (only debug-logged). Bounded ±0.3 delta, zero effect until the tracker's own `MIN_OBS_FOR_DISTRIBUTION` gate is met with real data. Closes the last unwired link in the options self-learning loop: real trade closes → `OptionsKnowledgeStore`/`OptionsPerformanceTracker`/`OptionsUnderlyingResponseTracker` (all auto-updating, no human gate) → automatically consumed back into `_base_confidence()` on the next signal. Equity untouched — this function is only ever called from the options builders | No |
| `knowledge_system/equity_hedge_shadow_engine.py` | NEW — DTA-EQUITY-HEDGE-SHADOW-001: read-only shadow observer of equity's own `ORDER_PLACED` events (filters `source_agent=="OrderManager"` only — never touches or reads back into equity decisions). For each real equity trade, attempts a single-stock option chain lookup (honestly records `chain_available=False` today — confirmed empirically that no live/synthetic single-stock chain support exists yet) and, when available, shadow-tracks a hypothetical protective hedge (PUT vs long equity, CALL vs short) with zero real capital. Implements the automated `EQH-Ready-1..5` readiness gate (volume ≥40, OOS sign-test p<0.10, profitable net of a 2% cost estimate, no symbol >80% of evidence, single-stock-only evidence) — reuses existing project thresholds, no new numbers invented. When all 5 pass for a symbol, marks `READY_FOR_LIVE` and fires a Telegram alert; does **not** place any real trade — no single-stock options execution path exists anywhere in this codebase yet, so "automatic" here means the AUTHENTICATION decision only, not a live-trading switch | No |
| `orchestrator/master_orchestrator.py` | DTA-EQUITY-HEDGE-SHADOW-001: wired `EquityHedgeShadowEngine` in the same additive, try/except-wrapped spot as the existing OIOS execution bridge (`subscribe(self.bus)` + `start()` background loop) — pure additive EventBus subscriber, zero equity code touched | No |
| `data_feeds/dhan_fno_security_map.py` | DTA-EQUITY-HEDGE-EXEC-001: fixed a real, pre-existing bug in `_download_to()` — `dhanhq` SDK's `fetch_security_list()` now returns a pandas `DataFrame`, not a list of dicts; `if result:` raised "ambiguous truth value" and silently fell back to a stale local CSV every day. Now handles both return shapes explicitly. Added `get_lot_size(underlying)` — reads the real, verified `SEM_LOT_UNITS` field from Dhan's own instrument master (never hard-coded); returns `None` (fail-closed) for unknown symbols | No |
| `data_feeds/dhan_feed.py` | DTA-EQUITY-HEDGE-EXEC-001: `get_options_chain()` now supports single-stock (`NSE_EQ`) underlyings in addition to index (`IDX_I`) — empirically verified against live Dhan API 2026-09-12 (RELIANCE returns real strikes/security_ids/Greeks via `NSE_EQ`, identical response schema to indices). `under_exchange_segment` is now derived from the looked-up symbol's segment instead of being hard-coded to `"IDX_I"` everywhere. Index behavior completely unchanged (same segment value used) | No |
| `execution_engine/options_order_manager.py` | DTA-EQUITY-HEDGE-EXEC-001: fixed a dangerous silent fallback — `lot_size = NSE_LOT_SIZES.get(signal.symbol, 75)` defaulted to 75 (NIFTY-ish) for ANY unrecognized symbol, which would have sized a real single-stock order with the wrong quantity. Now checks `NSE_LOT_SIZES` (indices) then `DhanFnOSecurityMap.get_lot_size()` (verified real instrument-master lot size for stocks); if neither resolves, the order is rejected rather than guessed | No |
| `risk_control/options_risk_engine.py` | DTA-EQUITY-HEDGE-EXEC-001: same fail-closed fix as above — `lot_size = int(meta.get("lot_size", 75))` removed; missing/invalid `lot_size` in signal metadata now rejects the trade instead of silently sizing risk against a guessed value (defense-in-depth alongside the OptionsOrderManager fix, since this method runs first in the pipeline) | No |
| `knowledge_system/equity_hedge_shadow_engine.py` | DTA-EQUITY-HEDGE-EXEC-001 (supersedes the shadow-only note above): live execution built. Structure corrected per user clarification to a SAME-DIRECTION defined-risk companion option (long CALL alongside a long equity trade, long PUT alongside a short one) — not a traditional opposite-direction protective hedge; captures the "underlying move → option move" leverage research with max loss capped at the premium paid. New `_attempt_live_execution()`: only ever runs for a symbol already in `_ready_symbols` (defense-in-depth re-check even if called directly); fetches the real chain, re-validates chain quality/DTE/OI/premium against the same thresholds the index options fast-path already uses, resolves a VERIFIED lot size (rejects rather than guesses), then routes the signal through the existing, already-proven `OptionsRiskEngine.approve_and_size()` → `OptionsOrderManager.execute()` — no new, untested execution path. **Production is configured for live real-money trading** (`PAPER_TRADING=false`, `LIVE_TRADING_AUTHORIZED=true` — confirmed on both local and VPS `.env`, not a test artifact), so this can place real orders once a symbol authenticates; validated exclusively via a fully-mocked test (real chain fetch, but `OptionsRiskEngine`/`OptionsOrderManager` replaced with mocks) to guarantee zero capital risk during verification — real order placement itself remains untested against a live broker fill | No |

---


## Deployment Rule — MANDATORY after every code change

**Every code modification must be followed by a full deploy cycle. No exceptions.**
Local, VPS, and container must always run identical code.

### Steps (run in order, do not skip)

```powershell
# 1 — Commit all changed files
git add <files>
git commit -m "<message>"

# 2 — Push to origin
git push origin main

# 3 — Deploy to VPS (single command)
# safe_pull.sh backs up runtime data → pulls → restores data → no knowledge lost
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && bash scripts/safe_pull.sh && python3 scripts/generate_build_manifest.py && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

### Definition of done
The deploy is complete **only** when `docker compose ps` shows **both** containers `Up … (healthy)`:
```
ai-trading-brain          Up N seconds (healthy)
trading-dashboard         Up N seconds (healthy)
```

If either container is not healthy — **stop, diagnose with `docker logs ai-trading-brain`, fix, redeploy before continuing.**

### Why
- The `data/` volume is persistent (`./data:/app/data`) — runtime files survive restarts
- `docker compose build --no-cache` ensures the new Python source is baked in, not cached
- A partial deploy (local committed, VPS not updated) is a split-brain state and must never persist

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
