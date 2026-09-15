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
**Mode:** Live trading (2026-09-14 — deliberate operator decision; `PAPER_TRADING=false`, `LIVE_TRADING_AUTHORIZED=true`). `main.py --paper` | Telegram bot (`main.py --telegram`)

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
| `scripts/knowledge_system/ranking_hypothesis_validator_001.py` | RSL-001 (Ranking Self-Learning Loop, Phase B completion): NEW — automated statistical validator for KSL-001's auto-registered `PROPOSED` hypotheses. Time-ordered 70/30 train/OOS split (never shuffled), bootstrap CI (1000 iters) on the OOS effect, 4-check scorecard (sample size, CI excludes baseline, train/OOS sign consistency, effect magnitude). Verdict ≥3/4→VALIDATED, ≤1/4→NO_INCREMENTAL_VALUE, else→INSUFFICIENT_SAMPLE (retried next cycle). Drives the ARS hypothesis through the same fully-automated lifecycle chain already proven by `h001.py`'s `H-CRITICAL-001` (PROPOSED→...→RUNNING→VALIDATED/REJECTED, actor=`RHV-001`, zero human step). On VALIDATED, hands off to the adjustment engine below | N/A |
| `scripts/knowledge_system/ranking_adjustment_engine_001.py` | RSL-001 (Phase E): NEW — isolated ranking-adjustment engine, deliberately independent of OIOS's `pending_adjustments`/`shadow_mode` (same conceptual shape reused as a template only — zero imports from `oios/`, zero shared storage; own store at `data/ksl/`). Lifecycle: `SHADOW_ELIGIBLE→SHADOW_ACTIVE→ACTIVE/REJECTED`, plus `ACTIVE→ROLLED_BACK` auto-revert on live degradation — fully automated, no human step. Guardrails mirror OIOS's proven numbers as constants only (bounded weight ≤0.15, cooldown 90 days, min shadow observation days/sample). `annotate_adjusted_scores()` is the additive hook: always computes a parallel shadow score (zero effect on real selection) and only overrides the real ranking when a direction has a live-confirmed `ACTIVE` adjustment | N/A |
| `scripts/final_trading_architecture_shadow_001.py` | RSL-001: `_assign_ranks()` gained one additive, try/except-wrapped call to `annotate_adjusted_scores()` before `select_c2_top_n()`. With zero active adjustments (current state) this is byte-identical to prior behaviour — confirmed via the existing 77-test suite, all passing. This file (not `opportunity_engine/final_c2_selector.py`) is the actual live-running shadow generator that feeds KSL-001; `final_c2_selector.py`'s frozen sort (`valid.sort(key=lambda c: (-c.c2_score, c.v3_rank))`) was confirmed untouched and is only exercised by its own test file, not the production shadow pipeline | No |
| `scripts/knowledge_system/ksl_models.py` | RSL-001: `KSLShadowCandidate` gained 6 new optional/defaulted fields (`feature_id`, `shadow_start_date`, `shadow_activated_at`, `live_activated_at`, `rolled_back_at`, `status_reason`) + a `from_dict()` classmethod — additive only, mirrors the precedent already set by `EvidenceRecord`'s Phase-1 field additions in this same file | No |
| `scripts/knowledge_system/knowledge_feedback_loop_001.py` | RSL-001: added Stage 10 (`validate_pending_hypotheses()`) and Stage 11 (`advance_shadow_tracking()` + `check_rollback()`) to the existing EOD loop, both try/except-wrapped and non-fatal, matching every other stage's safety convention | No |
| `tests/test_ranking_self_learning_001.py` | RSL-001: NEW — 40/40 tests (T001–T040): scorecard statistics, time-split no-leakage invariant, automated hypothesis lifecycle (fake registry, no real files touched), shadow-tracking state machine (activate/promote/reject), auto-rollback, `annotate_adjusted_scores` no-op-vs-active behaviour, forbidden-import safety checks, frozen-selector-untouched assertion | N/A |
| `strategy_lab/strategy_generator_ai.py` | DTA-EQUITY-STRATEGYLAB-OBSERVATION-001: extended the "StrategyLab is observation-only, KDA is sole authority" carve-out (previously options/spread only, DTA-OPTIONS-ISOLATION-001) to EQUITY. `_assign()`'s active-set exclusion check and `assign_strategy()`'s final hard gate no longer `return None`/drop a signal when its strategy is SHM/PerfTracker-disabled — the health verdict is recorded on `TradeSignal.strategy_health_status` (e.g. `SHM_EXCLUDED`, `META_INACTIVE`) and the signal is still forwarded to KDA. Untouched, still-enforced equity gates: bear-market-BUY rejection, RR-below-minimum rejection, volatile-regime-low-confidence rejection — these are structural eligibility rules, not SHM's historical-performance judgement, and were never part of the options carve-out either | No |
| `models/trade_signal.py` | DTA-EQUITY-STRATEGYLAB-OBSERVATION-001: added `strategy_health_status: Optional[str] = None` — additive, observation-only field | No |
| `tests/test_equity_strategylab_observation_only_001.py` | DTA-EQUITY-STRATEGYLAB-OBSERVATION-001: NEW — 9/9 tests confirming equity signals are no longer dropped by SHM/active-set exclusion (T001–T004), and confirming bear-market/RR-minimum gates remain enforced (T005–T006) | N/A |
| `knowledge_authority/kda_constant_refinement_engine.py` | KDA-CRE-001: NEW — fully automated (no human step), self-scheduled refinement of KDA's 3 live evidence-gate constants (`_ESS_DECISION_ELIGIBLE`, `_STABILITY_DECISION_MIN`, `_CONTRADICTION_DECISION_MIN` — confirmed the other 2 declared constants, `_AUTHORITY_KNOWLEDGE_MIN`/`_AUTHORITY_STRATEGY_MIN`, are dead code since ARCH-005). Self-scheduling is evidence-driven (checks re-trigger only after ≥30 new resolved KDA outcomes accumulate) gated by a dynamic cooldown floor calculated from the system's own observed outcome-arrival rate (never below an absolute 30-day safety floor — prevents thrashing on a short burst of correlated evidence). Statistical validation mirrors RHV-001 (time-ordered 70/30 train/OOS split, bootstrap CI, 4-check scorecard) but with a materially higher minimum sample (50 vs RHV-001's 10) since this gates live-money trades. Lifecycle: `WAITING_FOR_EVIDENCE→SHADOW_ACTIVE→ACTIVE/REJECTED`, plus `ACTIVE→ROLLED_BACK` auto-revert on live degradation. Every transition is appended (never overwritten) to `data/kda_cre/constant_change_ledger.jsonl` with full reasoning, for research reuse. Own isolated store at `data/kda_cre/`; zero imports from `oios/`/`scripts/knowledge_system/` | N/A |
| `knowledge_authority/knowledge_decision_authority.py` | KDA-CRE-001: added `_effective_constants()` — additive accessor that reads KDA-CRE-001's validated overrides (mtime-cached) and falls back to the exact original hardcoded defaults on any error/missing file. `_classify_evidence_state()` and `_compute_authority()` now read the ESS/stability/contradiction thresholds through this accessor instead of the bare module constants. Public interface (`evaluate()`, inputs/outputs) completely unchanged; behavior is byte-identical unless a shadow-confirmed override exists | No |
| `orchestrator/master_orchestrator.py` | KDA-CRE-001: added one non-fatal, try/except-wrapped EOD call to `run_daily_refinement_check()` immediately after the existing `run_eod_knowledge_update()` call, matching the established EOD-stage convention | No |
| `tests/test_kda_constant_refinement_engine.py` | KDA-CRE-001: NEW — 26/26 tests (T01–T26): override accessor (defaults/valid/corrupt/out-of-bounds), dynamic cooldown calculation, scorecard statistics (validates real signal, rejects noise, never moves in a worsening direction), full state machine (waiting/cooldown/shadow-start/promote/reject/rollback/no-premature-rollback), top-level safety (`run_daily_refinement_check` never raises), ledger append-only integrity, and integration proof that `knowledge_decision_authority.py` both falls back safely with no override and actually picks up a valid one | N/A |
| `control_tower/dashboard_app.py` | Fixed hardcoded "Mode: 🧪 PAPER" header badge — was a static string, never reflected the real trading mode. `.env` was already mounted into this container (GAP-026) but never actually loaded (no `load_dotenv()` call anywhere in the file); added it plus `_real_trading_mode_label()`, mirroring `OrderManager.__init__`'s own live-mode gate exactly (paper unless BOTH `PAPER_TRADING=false` AND `LIVE_TRADING_AUTHORIZED=true`) | No |
| `ARCHITECTURE.md` / `.github/copilot-instructions.md` | Updated stale "Current mode: Paper trading" headline text to reflect the deliberate 2026-09-14 live-trading decision — was pure documentation drift, never affected runtime behavior | N/A |
| `ARCHITECTURE.md` | Naming-sprawl Plan B, Phase 0 (docs-only, zero import/behavior touched): extended §13 Subsystem Naming Glossary with the acronyms/collisions missing from the first pass — root `knowledge_system/` (options-only, live) vs `scripts/knowledge_system/` (KSL, identical folder name, different package), PRR/PGA/CLE/GVA/HKAP/IKN (all confirmed disconnected from `master_orchestrator.py`), and the "DTA" collision (`decision_tracer/`'s own `dta_*.py` file prefix vs this repo's DTA-XXX ticket convention — same token, two unrelated meanings). Also flagged (not fixed) the dead-after-construction `self.research_lab = ResearchLab()` instantiation as a separate future housekeeping item | No |
| `autonomous_research/__init__.py`, `growth_validator/__init__.py`, `decision_tracer/__init__.py`, `hkap/__init__.py`, `ikn/__init__.py`, `production_readiness/__init__.py`, `predictive_gap/__init__.py` | Naming-sprawl Plan B, Phase 1 (docstring-only, zero import/export/behavior touched): added a one-line "STATUS: DISCONNECTED from live trading... see ARCHITECTURE.md §13" banner to each confirmed-dormant package's module docstring (verified via import smoke test post-edit — all 7 still import cleanly, `__all__`/exports unchanged). `decision_tracer/` additionally notes its `dta_` file prefix is unrelated to the repo's DTA-XXX ticket convention; `hkap/` additionally notes its "reuses IIOS V1.0" premise was never true (`iios/` is only a Wave-1 placeholder) | No |
| `decision_tracer/dta_analyzer.py`→`dtrace_analyzer.py`, `dta_collector.py`→`dtrace_collector.py`, `dta_reporter.py`→`dtrace_reporter.py`, `dta_runner.py`→`dtrace_runner.py`, `decision_tracer/__init__.py` | Naming-sprawl Plan B, Phase 2: renamed `decision_tracer/`'s internal `dta_*.py` modules to `dtrace_*.py` (via `git mv`, history preserved) to remove the collision with this repo's DTA-XXX ticket convention. Confirmed 0 external references anywhere in the repo before renaming (only `__init__.py` + the 4 files themselves referenced the old names; zero test files, zero other packages). Updated all internal imports, docstring module-path headers, and CLI usage examples to match. Verified: `py_compile` + `importlib.import_module` + explicit import of all 7 public symbols (`run_dta`, `collect_trace`, `analyze`, `write_report`, `generate_report`, `TraceBundle`, `DTAAudit`) all succeed post-rename. `data/dta/` output directory and class/function names (e.g. `DTAAudit`) deliberately left untouched — out of this phase's scope (file-name collision only) | No |
| `iios/__init__.py`, `ARCHITECTURE.md` | Naming-sprawl Plan B, Phase 3 (docs/docstring-only, zero behavior touched): added a one-line clarifying note to `iios/__init__.py` distinguishing it from `oios/` (verified `__version__`/`__status__`/`__wave__`/`__all__` all unchanged post-edit). Added a standing "going forward" rule to `ARCHITECTURE.md` §13: never use "IIOS" as an informal nickname for this project in any NEW doc/docstring — pre-2026-09-14 docs that already do this are left as historical artifacts, not retroactively edited | No |
| `iios/` → `enterprise_ai_platform/` (whole package, ~5,626 tracked files, via `git mv`) + all internal imports + `tests/ai/`, `tests/unit/*`, `tests/certification/`, `tests/performance/` (mirrored test suites) + `pyproject.toml` + `.pre-commit-config.yaml` + `bootstrap.py`/`dev.py`/`run.py`/`healthcheck.py` + `hkap/__init__.py` + `scripts/check_oios_duplicate_symbols.py` + `scripts/dep_check.py` + `ARCHITECTURE.md` §13 | Naming-sprawl Plan B, Phase 4 (user-authorized actual rename, the only in-scope target — `oios/`/`autonomous_research/`/`knowledge_system/`/`knowledge_authority/` remain untouched, still live and out of scope): mechanically renamed the dormant `iios/` package to `enterprise_ai_platform/` (case-sensitive whole-word `\biios\b` → `enterprise_ai_platform` via a one-time script, uppercase "IIOS" prose/env-var-prefix/cert-code usages deliberately left untouched, matching Phase 3's precedent). True scope was ~15x larger than originally estimated (5,626 tracked files vs the ~350 first assumed) — discovered mid-execution via `pyproject.toml`'s own package config (`name = "iios"`, CLI entry points, mypy/bandit hook paths) and a full `tests/unit/*` mirror tree; proceeded since the risk profile (zero live import sites) was unchanged by the larger scope. Verified: `python -m compileall` clean on every touched file; `pytest --collect-only` across the full suite → 34,554 tests collected, 0 collection errors; ran a 361-test execution sample (`tests/unit/bootstrap` + `tests/ai/foundation`) → 360 passed, 1 failed for a pre-existing, unrelated reason (a bootstrap test asserts `paper_trading==True` by default but this repo's real `config.py` is intentionally `PAPER_TRADING=False` since the 2026-09-14 live-trading decision — not caused by the rename, not fixed here, out of this phase's scope). Historical root `.md` reports (A1–A10, `AI_PLATFORM_*.md`, root `README.md`, etc, ~70 files) deliberately left untouched per the established "don't retroactively edit historical docs" precedent | No |
| `risk_control/options_risk_engine.py` | Self-Learning Ecosystem Phase 1: wired `OptionsKnowledgeStore.get_influence()` (already existed, already used for confidence scoring in `options_opportunity_ai.py`) into `approve_and_size()`'s lot-sizing decision — a NEW consumer, not previously wired here (confirmed via prior grep: options_risk_engine.py had zero references to the knowledge store before this change). Size-UP (+1 lot) gated on the stricter `KS_AUTHENTICATED` tier only (≥40 real outcomes + walk-forward Sharpe>0, already live/automatic/zero-human-step) and always re-checked against the existing capital/capacity hard caps before applying. Size-DOWN (−1 lot, floor 1) on `KS_DEGRADED` applies unconditionally since reducing risk on decaying edge is always safe. No new parallel validation/shadow system introduced — deliberately reuses the pre-existing, already-evidence-gated state machine as the sole trust signal, applied at a stricter tier than the existing confidence consumer since sizing is a more consequential lever. Wrapped in try/except (fail-open); all 4 pre-existing risk gates (capital/capacity/VIX/loss-streak) run unchanged before and after this block | No |
| `tests/test_options_ks_bridge_phase1.py` | Self-Learning Ecosystem Phase 1: NEW — 10/10 tests (T01–T10): zero effect with no/insufficient knowledge, size-up bounded to exactly +1 lot only at KS_AUTHENTICATED with positive influence, size-up never exceeds the hard lot cap or remaining capital capacity, size-down on KS_DEGRADED never below 1 lot, bridge exception is fail-open. Full options regression suite (242 tests across knowledge lifecycle, phase2/3 hardening, rollback safety, live execution, MOP-RC-001) re-run clean after the change | N/A |
| `predictive_gap/pga_learning.py` | Self-Learning Ecosystem Phase 3: fixed a real, pre-existing bug in `_try_create_hypothesis()` (Category C) — was calling `HypothesisRegistry.create_hypothesis()` with parameters that don't exist on that method (`rationale=`, `tags=`) and an invalid enum member (`HypothesisClassification.PREDICTIVE_SIGNAL` doesn't exist), so every "auto-executed" Category C hypothesis creation had been silently failing (caught by a bare `except`, logged at DEBUG, outcome recorded as `HYPOTHESIS_FAILED`) since this file was written. Fixed to use the real required parameters (`description`, `origin`, `knowledge_gap`, `expected_knowledge_gain`, `validation_method`) and a valid classification (`COVERAGE_GAP`). Added Category A wiring (`_try_create_hypothesis_cat_a`): registers RiskFilter/PMCI misses as a `PROPOSED` hypothesis for future validation — deliberately does **not** touch `risk_control/risk_manager_ai.py`'s `MIN_RR_RATIO` or any scanner weight directly, because PGA's own miss-classification (`pga_analyzer.py::_classify_miss_type()`) explicitly excludes non-significant-move rejections (`MISS_NO_DATA`), meaning Category A evidence is survivorship-biased (only ever sees rejections that became big movers, never the ones correctly avoided) — not sound enough to auto-tune a live risk/scanner gate. Also noted but NOT fixed (out of scope for this phase): Category B's `_try_reinforce_idr()` calls `IDRRepository.add_observation()`, a method that doesn't exist on that class either — same silent-failure bug, a separate pre-existing issue | No |
| `autonomous_research/ptue.py`, `autonomous_research/ptue_models.py` | Self-Learning Ecosystem Phase 3 (incidental bug fix, found while verifying the above): replaced 2 deprecated `datetime.utcnow()` calls with `datetime.now(timezone.utc)` — Python 3.12+ deprecation, was tripping this repo's own strict `filterwarnings=["error", ...]` pytest policy (`pyproject.toml`) whenever `autonomous_research` was the first thing imported in a test session, causing intermittent, import-order-dependent test failures. Verified via `test_ptue.py` (its own standalone smoke-test script, run directly): 156/156 pass | No |
| `tests/test_pga_category_a_hypothesis_bridge.py` | Self-Learning Ecosystem Phase 3: NEW — 8/8 tests (T01–T08): Category A creates a real, correctly-classified (`PERFORMANCE_GAP`, priority `LOW`) hypothesis in `PROPOSED` status with the survivorship-bias caveat in its own description text; Category C's fix is proven by a regression test; `execute_actions()` routes Category A to `HYPOTHESIS_CREATED_FOR_VALIDATION`; bridge exception is fail-open; `risk_control.risk_manager_ai.MIN_RR_RATIO` is asserted unchanged after running the bridge. Caught and fixed a real test-isolation bug during development: my first test run used the default (unpatched) `HypothesisRegistry` path and wrote 7 real test hypotheses into the production `data/ars_hypothesis_registry.json` — caught immediately, restored the file to its original 16 entries from the pre-existing `.bak`-plus-manual-diff, and fixed the test fixture to patch `autonomous_research.hypothesis_registry._DEFAULT_REGISTRY_PATH` (read fresh per-call, not bound at import time) instead of relying on `chdir` | N/A |
| `autonomous_research/hypothesis_models.py` | Self-Learning Ecosystem Phase 2 structural prerequisite: added 3 new **optional** fields to `ScientificHypothesis` (`subject_type`, `subject_value`, `direction`) so a hypothesis can reference a concrete symbol/strategy/regime — closes the "no structured subject field" blocker found during the original Phase 2 audit. `to_dict()`/`from_dict()` both `.get()`-default, fully backward compatible with existing production `data/ars_hypothesis_registry.json` (verified) | No |
| `autonomous_research/hypothesis_registry.py` | Self-Learning Ecosystem Phase 2 structural prerequisite: `create_hypothesis()` gained optional `subject_type`/`subject_value`/`direction` kwargs; NEW `get_confirmed_adjustment(subject_type, subject_value, max_delta=0.05)` — bounded, sign-matched, multi-match-averaged accessor over `CONFIRMED` hypotheses only. Dormant today (returns `0.0`) since no hypothesis has yet reached `CONFIRMED` with these fields populated — deliberately NOT wired into `knowledge_authority/knowledge_decision_authority.py`; that wiring is a separate, explicitly-approved contract per this repo's stricter KDA change workflow, not done in this pass | No |
| `predictive_gap/pga_learning.py` | Self-Learning Ecosystem Phase 2 structural prerequisite: `_try_create_hypothesis_cat_a()` now also passes `subject_type="SYMBOL"`, `subject_value=<symbol>`, `direction="POSITIVE"` into `create_hypothesis()`, giving Category A evidence the structured shape a future KDA consumer needs | No |
| `tests/test_kda_bridge_phase2_structural.py` | Self-Learning Ecosystem Phase 2 structural prerequisite: NEW — 9/9 tests (T01–T09): backward-compat defaults-to-None, `from_dict` handles pre-existing-shape dicts, `create_hypothesis` persists subject fields, `get_confirmed_adjustment` returns `0.0` with no match and with matching-but-not-`CONFIRMED` status (incl. `VALIDATED`), correctly bounded +/− delta for `CONFIRMED`+`POSITIVE`/`NEGATIVE`, averages+clamps multiple matches, PGA Category A populates `SYMBOL`/subject_value/`POSITIVE` correctly. Combined regression (structural + Phase 1 + Phase 3): 27/27 pass; standalone `test_hypothesis_registry.py` (own 40-test suite) re-run clean; production registry files confirmed untouched | N/A |
| `knowledge_authority/knowledge_decision_authority.py` | Self-Learning Ecosystem Phase 2 (KDA wiring, explicit contract approved before implementation): `_compute_authority()` now reads `HypothesisRegistry(knowledge_provider=KnowledgeProvider()).get_confirmed_adjustment("SYMBOL", symbol, max_delta=0.05)` and nudges the existing `relevance` component only (re-clamped to its own pre-existing `[0.1, 1.0]` bound) — never touches `evidence_state`, `_determine_decision()`'s categorical BUY/SELL/HOLD/WAIT path, `_classify_authority()`, or any other component; `KnowledgeAuthorityComponents` (still exactly 6 components + composite) untouched. Fail-open (`except Exception: ars_adj = 0.0`); dormant on deploy (returns `0.0` for every symbol until a hypothesis actually reaches `CONFIRMED` with subject fields set — none do in production yet) | No |
| `tests/test_kda_phase2_bridge.py` | Self-Learning Ecosystem Phase 2 (KDA wiring): NEW — 5/5 tests (T01–T05): zero effect today with an empty isolated registry, bounded `+delta = max_delta * confidence` for a fabricated `CONFIRMED` `POSITIVE` match, `relevance` never leaves `[0.1, 1.0]` at either extreme, fail-open when `HypothesisRegistry` raises, `composite_authority` stays in `[0, 1]`. Full existing KDA regression re-run clean: 416/416 pass (`test_kda_001/002/003.py`, `test_dta_030_provenance.py`, `test_dta_system_014/015.py` — including T037's multiplicative-dampening invariant). Live-path smoke test (`import orchestrator.master_orchestrator`) clean | N/A |
| `analysis/rejection_attribution_monitor.py` | Self-Learning Ecosystem Phase 4 (persistent rejection-attribution monitor): NEW — closes a real, pre-existing gap: `RejectionTracker.ingest_rejection()` has been live-wired at 4 real rejection points (CapitalRiskEngine x2, StrategyLab, RiskControl PositionAllocator/StressTest) since DTA-ATTRIBUTION-TRAIL-001, but `RejectionTracker.update_price_follow()` was never called from anywhere in production, so every real rejection sat `PENDING` forever. `RejectionAttributionMonitor.run_daily_cycle()` resolves `PENDING` rows >=7 calendar days old via real yfinance T+1/T+3/T+5 close prices (same tested fetch pattern as `opportunity_engine/klp_outcome_engine.py::_fetch_ohlcv_yfinance`), then recomputes per-reason accuracy via the existing `accuracy_by_reason()`. `get_reason_reliability()` is a read-only accessor gated on `MIN_SAMPLES_FOR_RELIABILITY=10` (mirrors `StrategyPerformanceTracker.MIN_SAMPLE`), returns `None` below that sample size — advisory-only, NOT wired into any live risk/decision gate this phase (this repo's own earlier, explicitly-flagged finding that `MAX_POSITIONS_CAP`'s 48% "accuracy" claim was synthetic-data-only is exactly why a real per-reason figure needs its own dedicated evidence first). Writes an append-only `data/rejection_attribution/daily_summary.jsonl`. Never raises; zero imports from execution_engine/order_manager/broker APIs | No |
| `orchestrator/master_orchestrator.py` | Self-Learning Ecosystem Phase 4: added one non-fatal, try/except-wrapped EOD call to `run_daily_rejection_attribution()`, matching the established EOD-stage convention (same block style as KDA-CRE-001) | No |
| `tests/test_rejection_attribution_monitor.py` | Self-Learning Ecosystem Phase 4: NEW — 8/8 tests (T01–T08): immature rows skipped without ever calling the price fetcher, mature rows resolved with the exact T+1/T+3/T+5 closes passed through, no-data rows stay `PENDING`, reliability accessor gated correctly below/at `MIN_SAMPLES_FOR_RELIABILITY`, `run_daily_cycle` fail-open when the tracker itself raises, daily summary JSONL append verified, source-text safety scan confirms zero `execution_engine`/`order_manager`/`dhan_feed`/`broker` imports | N/A |
| `.gitignore` | Added `data/rejection_attribution/` (new runtime output directory for Phase 4) | No |
| `analysis/rejection_audit.py` | Root-cause fix: `seed_synthetic_data()` was passing `is_backfill=False` for its SYNTHETIC seed rows — meant that column could never distinguish synthetic from real data if this manual CLI (`python analysis/rejection_audit.py --reseed`) were ever pointed at the production db. Fixed to `is_backfill=True`, matching the established convention already used by `trade_quality_tracker.py`'s `backfill_from_paper_trades()`. Manual CLI only, never called from any scheduled/live path — zero behavior change to any live trading path | No |
| `analysis/rejection_attribution_monitor.py` | Following the above root-cause fix: `_compute_reliability_summary()` and `get_reason_reliability()` now filter out `is_backfill=1` rows, so synthetic/backfilled evidence can never contaminate a real per-reason reliability figure (previously undocumented as a caveat since the source bug made the filter unreliable; now safe to apply) | No |
| `tests/test_rejection_attribution_monitor.py` | Added T09 (`is_backfill=1` rows excluded from reliability computation even at/above sample threshold) and T10 (regression test proving `rejection_audit.py`'s seeded rows are now marked `is_backfill=1`) — 10/10 pass | N/A |
| `production_readiness/prr_monitor.py` | Self-Learning Ecosystem Phase 5: NEW — closes the same "computed but discarded" gap found in Phase 3/4: `prr_runner.run_prr()` already computes a daily certification summary (`certification_status`/`ils_score`/`gva_score`/`critical_failures`/`warnings`) at EOD, but the dict was discarded after one `log.info()` line. `record_daily_result()` persists it to an append-only `data/prr/daily_summary_history.jsonl`; `get_latest_certification()`/`get_certification_history()` are read-only accessors for a future dashboard/Telegram command; `check_and_alert()` sends a `notifier.market_alert()` Telegram push only on `NOT_READY` or a verdict CHANGE since the last recorded entry (mirrors the existing KDA Authority Update "alert only on state change" convention) — advisory only, never touches any trade/risk/decision gate. Found but explicitly NOT fixed (separate, bigger, out-of-scope task): `ph5_daily_pipeline.py::run_daily_pipeline()` is dead code, never called anywhere despite its own docstring claiming otherwise, so `ph9_certification.py`'s `Daily_ILC_Operational` check always evaluates a hard-coded `pipeline=None` PASS rather than a real pipeline-health signal — fixing that would change PRR's own certification *logic*, not just surface its existing output | No |
| `production_readiness/__init__.py` | Phase 5: added `prr_monitor` re-exports (`record_daily_result`, `get_certification_history`, `get_latest_certification`, `check_and_alert`), matching this package's existing re-export-everything convention | No |
| `orchestrator/master_orchestrator.py` | Phase 5: added one non-fatal, try/except-wrapped call to `record_daily_result()` + `check_and_alert()` immediately after the existing `[PRR-001]` log line, matching the established EOD-stage convention | No |
| `tests/test_prr_monitor.py` | Phase 5: NEW — 9/9 tests (T01–T09): history append + read-back (oldest-first, last-n), latest-accessor None-when-empty and correct-when-populated, alert fires on `NOT_READY` and on verdict change, alert suppressed when unchanged and ready, fail-open when the notifier itself raises, source-text safety scan confirms zero `execution_engine`/`order_manager`/`dhan_feed`/`broker`/`risk_control` imports | N/A |
| `production_readiness/ph5_daily_pipeline.py` | Root-cause fix: added `build_pipeline_result_from_live_stages()` — builds a real `DailyPipelineResult` from the orchestrator's OWN already-executed PGA/ILC result dicts, never re-running anything (confirmed via grep that GVA/SD_review/ILC-verification are never called live, so those sub-fields correctly stay `None` rather than being fabricated). Corrected the module's stale/false docstring claim that `run_daily_pipeline()` (which actually RE-RUNS PGA→ILC→GVA→SD→verification→reports) is "called from `_do_eod_learning()`, replaces the individual try/except wrappers" — it never was, and wiring it in as originally described would have duplicated PGA/ILC execution; `run_daily_pipeline()` is kept as a standalone/manual utility, untouched | No |
| `production_readiness/prr_runner.py` | Root-cause fix: `_collect_prr_data()`/`run_prr()` gained an optional `pipeline` parameter (default `None`, fully backward-compatible — CLI and all existing callers unaffected). Previously `data.setdefault("pipeline", None)` was the only place `data["pipeline"]` was ever touched, so it was permanently `None`; now the orchestrator passes a real, non-duplicated `DailyPipelineResult` through | No |
| `production_readiness/ph9_certification.py` | Root-cause fix: `Daily_ILC_Operational` check's narrative text no longer hard-codes `"/6"` (misleading once only 2 of 6 possible stages are ever populated) — now reports the actual attempted stage total. The check itself now reflects a REAL PGA/ILC outcome instead of always defaulting to the "not yet run" `INFO`-only placeholder | No |
| `production_readiness/__init__.py` | Root-cause fix: added `build_pipeline_result_from_live_stages` to the re-export list, matching this package's existing convention | No |
| `orchestrator/master_orchestrator.py` | Root-cause fix: `[PRR-001]` block now builds a `DailyPipelineResult` from the same-cycle `_pga`/`_ilc` locals (via `"_pga" in locals()` / `"_ilc" in locals()`, matching this file's own existing convention for "was this local set earlier this cycle" checks) and passes it into `run_prr(pipeline=...)` — never re-runs PGA/ILC, wrapped in its own inner try/except so a builder failure can never break the existing PRR pipeline call | No |
| `tests/test_prr_pipeline_root_cause.py` | Root-cause fix: NEW — 7/7 tests (T01–T07): builder correctly reflects real PGA/ILC success/failure and leaves untouched stages `None`; `ph9_certification.build_certificate()` now issues a real `CRITICAL` fail when ILC actually failed and a real `PASS` with an accurate (non-hard-coded) stage-count narrative when it succeeded; `run_prr(pipeline=None)` default behavior fully unchanged; `_collect_prr_data()` correctly threads the `pipeline` argument through to the certificate | N/A |

---

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
