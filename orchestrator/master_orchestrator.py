"""
Layer 1 — Master Orchestrator AI
=====================================
The central brain of the AI Trading Brain system.

Responsibilities:
  • Coordinate all 10 layers in sequence
  • Schedule analysis tasks throughout the trading day
  • Aggregate results from every division
  • Halt trading if risk limits are breached
  • Trigger end-of-day learning cycle
  • Publish and consume events via the EDA communication layer

Flow:
  market_intelligence → opportunity_engine → strategy_lab
      → risk_control → debate → decision → execution
      → trade_monitoring → learning_system

EDA (Event-Driven Architecture) layer:
  Each completed layer step publishes typed events to the EventBus.
  Any other agent can subscribe to those events for reactive behaviour.
  The TaskQueue is used for scheduled background tasks (monitoring,
  EOD learning) so they never block the main trading cycle.
"""

from __future__ import annotations
import sched
import time
import threading
from datetime import datetime
from typing import List, Optional

from config import SCHEDULE, MAX_DRAWDOWN_PCT
from models import MarketSnapshot, TradeSignal, Portfolio
from utils  import get_logger
from utils.kill_switch import is_trading_enabled, get_kill_switch_status

# ── Layer imports ──────────────────────────────────────────────────────────
from market_intelligence.market_data_ai      import MarketDataAI
from market_intelligence.market_regime_ai    import MarketRegimeAI
from market_intelligence.market_monitor      import MarketMonitor
from market_intelligence.sector_rotation_ai  import SectorRotationAI
from market_intelligence.liquidity_ai        import LiquidityAI
from market_intelligence.event_detection_ai       import EventDetectionAI
from market_intelligence.regime_probability_model  import RegimeProbabilityModel, RegimeProbabilities

from opportunity_engine.equity_scanner_ai         import EquityScannerAI
from opportunity_engine.options_opportunity_ai    import OptionsOpportunityAI
from opportunity_engine.arbitrage_ai              import ArbitrageAI
from opportunity_engine.opportunity_density_monitor import OpportunityDensityMonitor

from strategy_lab.strategy_generator_ai     import StrategyGeneratorAI
from strategy_lab.strategy_evolution_ai     import StrategyEvolutionAI
from strategy_lab.backtesting_ai            import BacktestingAI
from strategy_lab.meta_strategy_controller  import MetaStrategyController

from risk_control.risk_manager_ai           import RiskManagerAI
from risk_control.portfolio_allocation_ai   import PortfolioAllocationAI
from risk_control.stress_test_ai            import StressTestAI
from risk_control.capital_risk_engine       import CapitalRiskEngine

from debate_system.multi_agent_debate       import MultiAgentDebate
from decision_ai.decision_engine            import DecisionEngine
from execution_engine.order_manager         import OrderManager
from trade_monitoring.trade_monitor         import TradeMonitor
from trade_monitoring.strategy_health_monitor import StrategyHealthMonitor
from learning_system.learning_engine        import LearningEngine
from learning_system.strategy_performance_tracker import StrategyPerformanceTracker
from learning_system.daily_self_evaluation  import DailyAISelfEvaluator

from market_simulation.simulation_engine    import SimulationEngine, SimulationResult

from global_intelligence                    import GlobalIntelligenceEngine, DistortionResult

# ── Production safety & evaluation layers ─────────────────────────────────
from data_integrity                         import DataIntegrityEngine
from risk_guardian                          import FailSafeRiskGuardian, GuardianDecision
from system_monitor                         import SystemMonitor
from performance                            import PerformanceEvaluator
from research_lab                           import ResearchLab
from validation_engine                      import ValidationEngine
from meta_learning                          import MetaLearningEngine
from meta_learning.regime_strategy_map      import RegimeStrategyMap

# ── EDA / Communication layer ──────────────────────────────────────────────
from communication import (
    get_bus, get_router, get_memory, get_task_queue,)
# ── Control Tower (monitoring) ────────────────────────────────────────────
from control_tower import ControlTower

# ── Edge Discovery Engine ─────────────────────────────────────────────
from edge_discovery import EdgeDiscoveryEngine

from communication import (
    EventType, MarketEvent, OpportunityEvent, RiskEvent,
    DecisionEvent, ExecutionEvent, LearningEvent, SystemEvent,
    Priority,
)

log = get_logger(__name__)

# ── All agent names (used to register with the MessageRouter) ──────────────
ALL_AGENTS = [
    "MasterOrchestrator",
    # Layer 0: Data Integrity
    "DataIntegrityEngine", "DataValidator", "AnomalyDetector",
    # Layer 1: Global Intelligence
    "GlobalDataAI", "MacroSignalAI", "CorrelationEngine",
    "GlobalSentimentAI", "PremarketBiasAI",
    # Layer 2: Market Intelligence
    "MarketDataAI", "MarketRegimeAI", "SectorRotationAI",
    "LiquidityAI", "EventDetectionAI", "RegimeProbabilityModel",
    # Layer 1.5: Global Distortion
    "MarketDistortionScanner",
    # Layer 3: Opportunity Engine
    "EquityScannerAI", "OptionsOpportunityAI", "ArbitrageAI",
    # Layer 4: Strategy Lab
    "StrategyGeneratorAI", "StrategyEvolutionAI", "BacktestingAI", "MetaStrategyController",
    "CapitalRiskEngine",
    # Layer 5: Risk Control
    "RiskManagerAI", "PortfolioAllocationAI", "StressTestAI",
    # Layer 5.5: Simulation
    "SimulationEngine",
    # Layer 6-7: Debate & Decision
    "MultiAgentDebate", "DecisionEngine",
    # Layer 7.5: Fail-Safe Risk Guardian
    "FailSafeRiskGuardian",
    # Layer 8: Execution
    "OrderManager",
    # Layer 9: Monitoring
    "TradeMonitor", "StrategyHealthMonitor",
    # Layer 10: Learning
    "LearningEngine",
    # Operational layers
    "SystemMonitor", "PerformanceEvaluator", "ResearchLab",
    # Validation Engine
    "ValidationEngine", "BacktestEngine", "WalkForwardAnalyzer",
    "CrossMarketValidator", "MonteCarloSimulator",
    "ParameterSensitivityAnalyzer", "RegimeRobustnessTester",
    "ValidationReportBuilder",
    # Meta-Learning Engine
    "MetaLearningEngine", "FeatureExtractor", "MetaModel",
    "TrainingEngine", "StrategyWeightPredictor", "PerformanceDataset",
]


class MasterOrchestrator:
    """
    Chief AI Officer — coordinates all agents and manages the full
    trade lifecycle from market open to end-of-day learning.

    EDA additions
    -------------
    • self.bus       — EventBus singleton (publish/subscribe)
    • self.router    — MessageRouter singleton (point-to-point messaging)
    • self.memory    — OrchestratorAI's own AgentMemory
    • self.task_queue— Global TaskQueue; workers started for monitoring/learning
    """

    def __init__(self):
        log.info("═" * 60)
        log.info("  AI TRADING BRAIN — Master Orchestrator Initialising")
        log.info("═" * 60)
        # ── Layer 0: Data Integrity ────────────────────────────────────
        self.data_integrity      = DataIntegrityEngine()
        # ── Layer 1: Global Market Intelligence (pre-market context) ─────
        self.global_intelligence = GlobalIntelligenceEngine()
        # ── Layer 2: Market Intelligence ──────────────────────────────
        self.market_data_ai      = MarketDataAI()
        self.market_regime_ai    = MarketRegimeAI()
        self.sector_rotation_ai  = SectorRotationAI()
        self.liquidity_ai        = LiquidityAI()
        self.event_detection_ai       = EventDetectionAI()
        self.regime_probability_model = RegimeProbabilityModel()
        # ── Continuous Monitoring (Q2 — runs in background thread) ─────
        self.market_monitor = MarketMonitor(
            feed=None,   # feed wired after order_manager init; see _start_monitor()
            on_signal=self._on_market_signal,
            on_deep_scan=self._on_deep_scan,
        )

        # ── Layer 3: Opportunity Engine ────────────────────────────────
        self.equity_scanner      = EquityScannerAI()
        self.options_opportunity  = OptionsOpportunityAI()
        self.arbitrage_ai        = ArbitrageAI()
        self.odm                 = OpportunityDensityMonitor()  # density-tracking control layer

        # ── Layer 4: Strategy Lab ──────────────────────────────────────
        self.meta_strategy       = MetaStrategyController()
        # ── Layer 2.5: Meta-Learning Engine ────────────────────────────
        self.meta_learning       = MetaLearningEngine()
        self.strategy_generator  = StrategyGeneratorAI(meta_controller=self.meta_strategy)
        self.strategy_evolution  = StrategyEvolutionAI()
        self.backtesting_ai      = BacktestingAI()
        # ── Meta-Control: Capital Risk Engine (between Lab and Risk Control) ───
        self.capital_risk_engine = CapitalRiskEngine()
        # ── Layer 5: Risk Control ──────────────────────────────────────
        self.risk_manager        = RiskManagerAI()
        self.portfolio_allocator = PortfolioAllocationAI()
        self.stress_test_ai      = StressTestAI()

        # ── Market Simulation Engine (between Risk Control and Debate) ────
        self.simulation_engine   = SimulationEngine(mc_runs=1_000)

        # ── Layer 7.5: Fail-Safe Risk Guardian ────────────────────────
        self.risk_guardian       = FailSafeRiskGuardian(total_capital=1_000_000)

        # ── Layer 6–7: Debate & Decision ───────────────────────────────
        self.debate_system       = MultiAgentDebate()
        self.decision_engine     = DecisionEngine()

        # ── Layer 8: Execution ─────────────────────────────────────────
        self.order_manager       = OrderManager()

        # ── Layer 9: Trade Monitoring ──────────────────────────────────
        self.trade_monitor       = TradeMonitor()

        # ── Meta-Control: Strategy Health Monitor (between Monitoring & Learning)
        self.strategy_health     = StrategyHealthMonitor()

        # ── Layer 10: Learning ─────────────────────────────────────
        self.learning_engine     = LearningEngine()
        self.learning_engine.inject_health_monitor(self.strategy_health)
        # ── Q3: Strategy Performance Tracker (win rate / expectancy / auto-disable)
        self.perf_tracker        = StrategyPerformanceTracker()
        # ── Q3: Regime → Strategy best-fit map (meta-learning mechanism 2)
        self.regime_strategy_map = RegimeStrategyMap()
        # ── Daily AI Self-Evaluation ──────────────────────────────
        self.self_evaluator      = DailyAISelfEvaluator()

        # ── Operational layers ─────────────────────────────────────────
        self.system_monitor      = SystemMonitor()
        self.performance_evaluator = PerformanceEvaluator(capital=1_000_000)
        self.research_lab        = ResearchLab()
        # ── Validation Engine ──────────────────────────────────────────
        self.validation_engine   = ValidationEngine(n_mc_runs=1_000)

        self._halt = False

        # ── EDA Communication Layer ────────────────────────────────────
        self.bus        = get_bus()
        self.router     = get_router()
        self.memory     = get_memory("MasterOrchestrator")
        self.task_queue = get_task_queue()
        self._setup_eda()
        # ── Control Tower (passive observer — wire after bus is ready) ─────
        self.control_tower = ControlTower.get_instance(self.bus)

        # ── Edge Discovery Engine (research layer) ────────────────────
        self.edge_discovery = EdgeDiscoveryEngine()
        # Cache last snapshot so the EOD learning cycle can run EDE
        self._last_snapshot: Optional[MarketSnapshot] = None

        # ── Persistence + Notifications ───────────────────────────────
        try:
            from database      import get_db
            from notifications import get_notifier
            self.db       = get_db()
            self.notifier = get_notifier()
            self.db.log_event("orchestrator", "SYSTEM_START",
                              "Master Orchestrator initialised")
        except Exception as _exc:
            log.warning("[Orchestrator] DB/Notifier not available: %s", _exc)
            self.db       = None
            self.notifier = None

        log.info("All agents initialised successfully.")

    # ──────────────────────────────────────────────────────────────────
    # EDA SETUP
    # ──────────────────────────────────────────────────────────────────

    def _setup_eda(self):
        """
        • Register all agents with the MessageRouter so they can exchange
          direct messages.
        • Subscribe the Orchestrator to key system events.
        • Start background TaskQueue workers for monitoring and learning.
        """
        # Register every agent in the router
        for name in ALL_AGENTS:
            self.router.register(name)

        # Subscribe to SYSTEM_HALT events (e.g. Risk Manager sends one on breach)
        self.bus.subscribe(
            EventType.SYSTEM_HALT,
            self._on_system_halt,
            agent_name="MasterOrchestrator",
            priority=10,   # highest priority
        )

        # Subscribe to DRAWDOWN_ALERT
        self.bus.subscribe(
            EventType.DRAWDOWN_ALERT,
            self._on_drawdown_alert,
            agent_name="MasterOrchestrator",
        )

        # Start TaskQueue workers so background tasks run without blocking cycles
        self.task_queue.start_worker("TradeMonitor")
        self.task_queue.start_worker("LearningEngine")
        self.task_queue.start_worker("MasterOrchestrator")

        log.info("[EDA] Communication layer wired. Bus ready. Workers started.")

    def _on_system_halt(self, event):
        log.critical("[EDA] SYSTEM_HALT event received — halting trading. Source: %s",
                     event.source_agent)
        self._halt = True
        self.order_manager.close_all_positions()

    def _on_drawdown_alert(self, event):
        pct = event.payload.get("drawdown_pct", 0) * 100
        log.warning("[EDA] DRAWDOWN_ALERT: %.1f%% drawdown reported.", pct)
        if pct >= MAX_DRAWDOWN_PCT * 100:
            self._halt = True
            self.order_manager.close_all_positions()

    # ── Continuous Monitoring callbacks (Q2) ──────────────────────────────────

    def _start_monitor(self) -> None:
        """Wire a live feed into MarketMonitor and start the background thread."""
        if self.market_monitor.is_running:
            return
        try:
            from data_feeds.dhan_feed import DhanFeed
            self.market_monitor._feed = DhanFeed()
            self.market_monitor.start()
            log.info("[Orchestrator] ✅ Continuous market monitoring started.")
        except Exception as exc:
            log.warning("[Orchestrator] Could not start market monitor: %s", exc)

    def _on_market_signal(self, event_type: str, data: dict) -> None:
        """
        Called by MarketMonitor on every real-time signal.
        Routes events to the EventBus for downstream agents.
        """
        log.info("[Orchestrator] 📡 Market signal: %s — %s", event_type, data)
        try:
            self.bus.publish(MarketEvent(
                event_type=EventType.PRICE_UPDATE,
                source_agent="MarketMonitor",
                payload={"signal_type": event_type, **data},
            ))
            # Telegram alert for high-priority signals
            if event_type in ("CIRCUIT_DROP_ALERT", "VIX_SPIKE") and self.notifier:
                sym  = data.get("symbol", "")
                val  = data.get("change_pct") or data.get("jump_pct", "")
                self.notifier.send_alert(
                    f"⚠️ <b>{event_type}</b> — {sym} {val}"
                )
        except Exception as exc:
            log.debug("[Orchestrator] Signal dispatch error: %s", exc)

    def _on_deep_scan(self, scan_name: str) -> None:
        """
        Called by MarketMonitor when a scheduled deep-scan time fires.
        Triggers the appropriate analysis layer.
        """
        log.info("[Orchestrator] 🕐 Scheduled deep scan: %s", scan_name)
        if self._halt:
            return
        try:
            # Force-expire the GlobalDataAI cache so the next cycle fetches fresh data
            try:
                self.global_intelligence.data_ai._last_fetch_ts = 0.0
            except Exception:
                pass

            if scan_name == "market_open_regime":
                # Re-run regime classification with fresh data
                raw = self.market_data_ai.fetch()
                self.market_regime_ai.classify(raw)
            elif scan_name in ("first_opportunity_scan", "mid_morning_scan",
                               "afternoon_scan"):
                # Lightweight opportunity re-scan (non-blocking)
                self.task_queue.submit_to(
                    "MasterOrchestrator",
                    self.run_full_cycle,
                    priority=Priority.HIGH,
                    description=f"deep_scan:{scan_name}",
                )
            elif scan_name == "closing_analysis":
                log.info("[Orchestrator] Closing analysis — checking positions.")
                self.trade_monitor.check_open_positions()
        except Exception as exc:
            log.warning("[Orchestrator] Deep scan error (%s): %s", scan_name, exc)

    # ──────────────────────────────────────────────────────────────────
    # PRIMARY CYCLE
    # ──────────────────────────────────────────────────────────────────

    def run_full_cycle(self) -> None:
        """Execute one complete analysis + execution cycle."""
        if self._halt:
            log.warning("Trading halted — skipping cycle.")
            return

        # ── Emergency Kill Switch Check ──────────────────────────────────
        # Professional safety mechanism: if kill_switch.json has
        # "trading_enabled": false, stop ALL trading immediately, regardless
        # of other conditions. This allows instant remote halt via file change.
        if not is_trading_enabled():
            status = get_kill_switch_status()
            log.critical(
                "🚨 EMERGENCY KILL SWITCH ACTIVE — Trading disabled. Reason: %s",
                status.get("reason", "Unknown")
            )
            return

        log.info("▶ Starting full analysis cycle — %s",
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.system_monitor.start_cycle()

        # ── Expire / context-invalidate LIMIT orders from prior cycle(s) ─
        # Four checks (in priority order):
        #   1. Time expiry (3 × 5-min candles = 15 min)
        #   2. Distortion event active this cycle
        #   3. Market regime has changed since signal was created
        #   4. VIX spike ≥ threshold + 30% relative rise vs. signal VIX
        # All context values come from the PREVIOUS cycle's snapshot so the
        # check is available at the very start of the new cycle, before new
        # market data is fetched.
        _prev_regime    = (
            str(self._last_snapshot.regime.value)
            if self._last_snapshot and hasattr(self._last_snapshot.regime, "value")
            else str(getattr(self._last_snapshot, "regime", ""))
            if self._last_snapshot else ""
        )
        _prev_vix       = float(getattr(self._last_snapshot, "vix", 0.0)) if self._last_snapshot else 0.0
        _prev_distortion = bool(getattr(self.global_intelligence.last_distortion, "any_distortion", False))
        _expired_ids = self.order_manager.check_and_expire_stale_limits(
            current_regime    = _prev_regime,
            current_vix       = _prev_vix,
            distortion_active = _prev_distortion,
        )
        for _oid in _expired_ids:
            self.bus.publish(SystemEvent(
                event_type=EventType.ORDER_REJECTED,
                source_agent="OrderManager",
                payload={"order_id": _oid, "reason": "context_invalidated"},
            ))

        # ── Re-entry: attempt to re-place time-expired limit orders ───
        # Only runs when context is still valid (regime unchanged, no
        # distortion, VIX not spiked).  Uses previous-cycle snapshot so
        # the check is available before new market data is fetched.
        _reentry_records = self.order_manager.attempt_all_reentries(
            current_prices    = {},           # skip price-proximity in live loop
            current_regime    = _prev_regime,
            current_vix       = _prev_vix,
            distortion_active = _prev_distortion,
        )
        for _reo in _reentry_records:
            self.trade_monitor.register(_reo)
            self.bus.publish(ExecutionEvent(
                event_type=EventType.ORDER_PLACED,
                source_agent="OrderManager",
                payload={
                    "order_id":    _reo.order_id,
                    "symbol":      _reo.symbol,
                    "direction":   _reo.direction,
                    "entry_price": _reo.entry_price,
                    "strategy":    _reo.strategy,
                    "reason":      "reentry",
                },
            ))

        # ── AET confirmations: place deferred CONFIRMATION-mode orders ─
        # Orders deferred because VIX was elevated or distortion was active
        # at signal time are re-evaluated each cycle.  If conditions have
        # normalised within AET_MAX_WAIT_CANDLES, the limit order is placed now.
        _aet_records = self.order_manager.attempt_aet_confirmations(
            current_vix       = _prev_vix,
            current_regime    = _prev_regime,
            distortion_active = _prev_distortion,
        )
        for _aeo in _aet_records:
            self.trade_monitor.register(_aeo)
            self.bus.publish(ExecutionEvent(
                event_type=EventType.ORDER_PLACED,
                source_agent="OrderManager",
                payload={
                    "order_id":    _aeo.order_id,
                    "symbol":      _aeo.symbol,
                    "direction":   _aeo.direction,
                    "entry_price": _aeo.entry_price,
                    "strategy":    _aeo.strategy,
                    "reason":      "aet_confirmed",
                },
            ))

        self.bus.publish(SystemEvent(
            event_type=EventType.CYCLE_STARTED,
            source_agent="MasterOrchestrator",
            payload={"ts": datetime.now().isoformat()},
        ))

        # ── STEP 0: Global Market Intelligence ────────────────────────
        with self.system_monitor.time_layer("GlobalIntelligence"):
            log.info("── Layer 1: Global Market Intelligence ──")
            premarket_bias = self.global_intelligence.run()
        if self._abort_if_timed_out("GlobalIntelligence"): return

        # ── STEP 0.5: Publish distortion result to event bus ──────────
        _dist = self.global_intelligence.last_distortion
        if _dist.any_distortion or _dist.stress_score >= 3:
            log.warning("[Orchestrator] ⚠ Distortion: Risk=%s  Score=%d/8  Flags=%s",
                        _dist.risk_level, _dist.stress_score,
                        _dist.active_flags or "none")
            if self.notifier and _dist.risk_level in ("HIGH", "EXTREME"):
                self.notifier.send_alert(
                    f"🚨 <b>DISTORTION ALERT</b> — Risk={_dist.risk_level}  "
                    f"Score={_dist.stress_score}/8\n"
                    + (f"Flags: {', '.join(_dist.active_flags)}" if _dist.active_flags else "")
                )
        self.bus.publish(SystemEvent(
            event_type=EventType.DISTORTION_DETECTED,
            source_agent="MarketDistortionScanner",
            payload={
                "risk_level":          _dist.risk_level,
                "stress_score":        _dist.stress_score,
                "any_distortion":      _dist.any_distortion,
                "active_flags":        _dist.active_flags,
                "trading_allowed":     _dist.behavior_overrides.trading_allowed,
                "size_multiplier":     _dist.behavior_overrides.position_size_multiplier,
                "max_new_trades":      _dist.behavior_overrides.max_new_trades,
                "hedge_preferred":     _dist.behavior_overrides.hedge_preferred,
                "sector_watches":      _dist.sector_watches,
            },
        ))

        # ── STEP 1: Market Intelligence (+ Data Integrity gate) ────────
        with self.system_monitor.time_layer("MarketIntelligence"):
            snapshot: MarketSnapshot = self._run_market_intelligence(premarket_bias)
        if snapshot is None:
            log.error("Market intelligence failed. Aborting cycle.")
            self.system_monitor.finalize_cycle(had_error=True)
            return
        if self._abort_if_timed_out("MarketIntelligence"): return

        # ── STEP 1.3: Regime Probability Model ────────────────────────
        # Computes soft probabilities for all 4 regimes so the system can
        # lean toward strategies early — before a regime is fully confirmed.
        # Also provides fallback strategy weights when the ML model is cold.
        with self.system_monitor.time_layer("RegimeProbabilityModel"):
            log.info("── Layer 2.3: Regime Probability Model ──")
            _regime_probs: RegimeProbabilities = self.regime_probability_model.compute(
                snapshot,
                stress_score=self.global_intelligence.last_distortion.stress_score,
            )
            self.bus.publish(SystemEvent(
                event_type=EventType.REGIME_PROBABILITY_COMPUTED,
                source_agent="RegimeProbabilityModel",
                payload=_regime_probs.to_dict(),
            ))

        # ── STEP 1.5: Meta-Learning — predict strategy weights ─────────
        with self.system_monitor.time_layer("MetaLearning"):
            log.info("── Layer 2.5: Meta-Learning Engine ──")
            from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS
            _all_strats = list(STRATEGY_PARAMS.keys())
            ml_allocation = self.meta_learning.predict(
                snapshot, _all_strats, print_report=False)
            if ml_allocation.model_active:
                # ML model is warm — use its weights; blend in 20% MRPM for stability
                _mrpm_w = _regime_probs.map_to_strategy_names(_all_strats)
                _ml_w   = ml_allocation.allocations or {}
                _blended = {
                    s: round(_ml_w.get(s, 0.0) * 0.80 + _mrpm_w.get(s, 0.0) * 0.20, 4)
                    for s in _all_strats
                }
                self.meta_strategy.set_ml_weights(_blended)
            else:
                # ML model is cold — use MRPM directly as strategy allocation
                _mrpm_w = _regime_probs.map_to_strategy_names(_all_strats)
                self.meta_strategy.set_ml_weights(_mrpm_w)
            log.info("[MetaLearning] Top strategy: %s  |  Model: %s  |  MRPM dominant: %s",
                     ml_allocation.top_strategy or "(warming up)",
                     "Active" if ml_allocation.model_active else "→ MRPM fallback",
                     _regime_probs.dominant.value)
            self.bus.publish(SystemEvent(
                event_type=EventType.META_LEARNING_APPLIED,
                source_agent="MetaLearningEngine",
                payload={
                    "top_strategy": ml_allocation.top_strategy or "",
                    "model_active": ml_allocation.model_active,
                    "allocations":  {k: round(v, 4)
                                     for k, v in (ml_allocation.allocations or {}).items()},
                },
            ))

        # ── STEP 2: Opportunity Scan (ODM-guided) ─────────────────────
        odm_directive = self.odm.get_directive(snapshot)
        if odm_directive.tier != "NORMAL":
            log.info("[ODM] %s", odm_directive.message)
        with self.system_monitor.time_layer("OpportunityEngine"):
            signals: List[TradeSignal] = self._run_opportunity_engine(snapshot, odm_directive)
        if not signals:
            log.info("No opportunities found this cycle.")
            self.odm.record_cycle(signals_generated=0, approved_trades=0)
            self.system_monitor.finalize_cycle()
            return

        # ── STEP 3: Strategy Evaluation ──────────────────────────────
        with self.system_monitor.time_layer("StrategyLab"):
            enriched_signals = self._run_strategy_lab(signals, snapshot)
        if self._abort_if_timed_out("StrategyLab"): return

        # ── STEP 3.5: Capital Risk Engine ────────────────────────────
        with self.system_monitor.time_layer("CapitalRiskEngine"):
            portfolio = self.order_manager.get_portfolio()
            cre_signals = self.capital_risk_engine.allocate(
                enriched_signals, snapshot, portfolio
            )

        # ── STEP 4: Risk Filtering ─────────────────────────────────
        with self.system_monitor.time_layer("RiskControl"):
            approved_signals = self._run_risk_control(cre_signals, snapshot)
        if self._abort_if_timed_out("RiskControl"): return
        # ── STEP 4.5: Market Simulation ────────────────────────────────
        with self.system_monitor.time_layer("MarketSimulation"):
            sim_result: SimulationResult = self.simulation_engine.run(
                approved_signals, snapshot
            )
            self.bus.publish(SystemEvent(
                event_type=EventType.SIMULATION_COMPLETE,
                source_agent="SimulationEngine",
                payload={
                    "approved":  len(sim_result.approved_trades),
                    "rejected":  len(approved_signals) - len(sim_result.approved_trades),
                    "rate":      (len(sim_result.approved_trades)
                                  / max(len(approved_signals), 1)),
                },
            ))

        # ── STEP 5: Fail-Safe Risk Guardian gate ───────────────────────
        with self.system_monitor.time_layer("RiskGuardian"):
            guardian_decision: GuardianDecision = self.risk_guardian.evaluate(
                sim_result.approved_trades, snapshot, portfolio
            )
        # ── Emit guardian funnel event so replay can track the rejection stage ──
        self.bus.publish(SystemEvent(
            event_type=EventType.RISK_GUARDIAN_COMPLETE,
            source_agent="RiskGuardian",
            payload={
                "approved": len(guardian_decision.approved_signals) if guardian_decision.approved else 0,
                "blocked":  len(guardian_decision.rejected_signals) if not guardian_decision.approved else 0,
                "decision": "APPROVED" if guardian_decision.approved else "BLOCKED",
            },
        ))
        if not guardian_decision.approved:
            log.warning("[RiskGuardian] BLOCKED: %s", guardian_decision.reason)
            self.system_monitor.finalize_cycle()
            return

        # ── STEP 6: Debate + Decision ──────────────────────────────────
        executed: List[dict] = []
        with self.system_monitor.time_layer("DebateAndDecision"):
            for signal in guardian_decision.approved_signals:
                row = self._run_debate_and_decide(signal, snapshot)
                if row:
                    executed.append(row)

        self.bus.publish(SystemEvent(
            event_type=EventType.CYCLE_COMPLETE,
            source_agent="MasterOrchestrator",
            payload={"signals_processed": len(approved_signals)},
        ))

        # ── CYCLE SUMMARY TABLE ────────────────────────────────────────
        cycle_report = self.system_monitor.finalize_cycle()
        self.system_monitor.print_cycle_table(cycle_report)
        self._last_snapshot = snapshot    # cache for EOD EDE cycle
        # Inform ODM of outcome so it can tune density tier next cycle
        self.odm.record_cycle(signals_generated=len(signals), approved_trades=len(executed))
        if executed:
            self._print_cycle_summary(executed, snapshot)
        else:
            log.info("✔ Cycle complete. No trades executed this cycle.")
            return

        log.info("✔ Cycle complete.")

    # ──────────────────────────────────────────────────────────────────
    # INTERNAL LAYER RUNNERS
    # ──────────────────────────────────────────────────────────────────

    def _abort_if_timed_out(self, layer_name: str) -> bool:
        """
        Checks whether the last layer exceeded the CRITICAL latency threshold.
        If so, finalises the cycle as an error and returns True so the caller
        can `return` immediately (aborting downstream layers).

        Usage::
            with self.system_monitor.time_layer("StrategyLab"):
                enriched_signals = self._run_strategy_lab(...)
            if self._abort_if_timed_out("StrategyLab"): return
        """
        if self.system_monitor.should_abort_cycle():
            log.error("[Orchestrator] Layer '%s' exceeded critical latency — "
                      "aborting this cycle to protect downstream layers.",
                      layer_name)
            self.system_monitor.finalize_cycle(had_error=True)
            return True
        return False

    def _run_market_intelligence(self, premarket_bias=None) -> Optional[MarketSnapshot]:
        log.info("── Layer 2: Market Intelligence ──")
        raw      = self.market_data_ai.fetch()

        # ── Data Integrity Gate ──────────────────────────────────────
        integrity = self.data_integrity.run(raw)
        # Only abort on hard validation errors (corrupt/missing prices).
        # Statistical anomalies (VIX spikes, PCR outliers) are market signals —
        # they must NOT block the pipeline; downstream layers see the anomaly report.
        if not integrity.validation.passed:
            log.error("[DataIntegrity] FAILED — %d error(s). Skipping cycle.",
                      len(integrity.validation.errors))
            self.system_monitor.record_agent_error("DataIntegrityEngine")
            return None
        if integrity.anomaly.is_anomalous:
            log.warning("[DataIntegrity] Anomaly detected (non-blocking) — pipeline continues.")
        raw = integrity.clean_data   # use sanitised data

        # ── LIVE DATA VERIFICATION SNAPSHOT ─────────────────────────────
        _nifty  = raw.get("indices", {}).get("NIFTY 50", {})
        _bnk    = raw.get("indices", {}).get("NIFTY BANK", {})
        _vix    = raw.get("vix", 0.0)
        _src    = raw.get("data_source", "SIM")
        _vix_src= raw.get("vix_source", "SIM")
        _ts     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _n_chg  = _nifty.get("change_pct", 0.0)
        _b_chg  = _bnk.get("change_pct", 0.0)
        _n_arrow = "+" if _n_chg >= 0 else ""
        _b_arrow = "+" if _b_chg >= 0 else ""
        _width  = 58
        log.info("┌" + "─" * _width + "┐")
        log.info("│  LIVE DATA SNAPSHOT  │  %-28s  [%s] │", _ts, _src)
        log.info("├" + "─" * _width + "┤")
        log.info("│  NIFTY 50    :  %10.2f   (%s%.2f%%)  [%s]%s│",
                 _nifty.get("ltp", 0), _n_arrow, _n_chg,
                 _nifty.get("source", "SIM"),
                 " " * max(0, 6 - len(_nifty.get("source", "SIM"))))
        log.info("│  BANKNIFTY   :  %10.2f   (%s%.2f%%)  [%s]%s│",
                 _bnk.get("ltp", 0),  _b_arrow, _b_chg,
                 _bnk.get("source", "SIM"),
                 " " * max(0, 6 - len(_bnk.get("source", "SIM"))))
        log.info("│  INDIA VIX   :  %10.2f                [%s]%s│",
                 _vix, _vix_src,
                 " " * max(0, 6 - len(_vix_src)))
        log.info("├" + "─" * _width + "┤")
        log.info("│  ► Cross-check vs NSE / Groww / Kite to verify accuracy  │")
        log.info("└" + "─" * _width + "┘")

        regime   = self.market_regime_ai.classify(
            raw,
            global_bias=getattr(premarket_bias, "regime_nudge", "neutral"),
            global_sentiment_score=getattr(premarket_bias, "bias_score", 0.0),
        )
        sectors  = self.sector_rotation_ai.analyse(raw)
        liquidity = self.liquidity_ai.analyse(raw)
        events   = self.event_detection_ai.scan()

        snapshot = MarketSnapshot(
            timestamp     = datetime.now(),
            indices       = raw.get("indices", {}),
            regime        = regime.data.get("regime"),
            volatility    = regime.data.get("volatility"),
            vix           = raw.get("vix", 15.0),
            sector_flows  = sectors.data.get("flows", []),
            sector_leaders= sectors.data.get("leaders", []),
            events_today  = events.data.get("events", []),
            market_breadth= raw.get("breadth", 0.5),
            pcr           = raw.get("pcr", 1.0),
            global_bias   = getattr(premarket_bias, "regime_nudge", None),
            global_sentiment_score = getattr(premarket_bias, "bias_score", 0.0),
        )
        log.info(snapshot.summary())

        # Publish to EDA bus so any subscriber gets the market context
        self.bus.publish(MarketEvent(
            event_type=EventType.MARKET_DATA_READY,
            source_agent="MarketDataAI",
            payload={"vix": snapshot.vix, "regime": snapshot.regime,
                     "breadth": snapshot.market_breadth, "pcr": snapshot.pcr},
        ))
        self.bus.publish(MarketEvent(
            event_type=EventType.MARKET_REGIME_CLASSIFIED,
            source_agent="MarketRegimeAI",
            payload={"regime": snapshot.regime,
                     "volatility": str(snapshot.volatility)},
        ))

        # Cache regime in every agent's memory via the shared memory registry
        self.memory.remember_regime(
            str(snapshot.regime), snapshot.vix)

        return snapshot

    def _run_opportunity_engine(self, snapshot: MarketSnapshot,
                                odm_directive=None) -> List[TradeSignal]:
        log.info("── Layer 3: Opportunity Engine ──")
        equity_signals  = self.equity_scanner.scan(snapshot, odm_directive=odm_directive)
        options_signals = self.options_opportunity.scan(snapshot)
        arb_signals     = self.arbitrage_ai.scan(snapshot)
        all_signals     = (equity_signals + options_signals + arb_signals)
        log.info("  Found %d raw opportunities", len(all_signals))

        # Publish one event per signal found
        for sig in all_signals:
            self.bus.publish(OpportunityEvent(
                event_type=EventType.EQUITY_OPPORTUNITY_FOUND,
                source_agent="EquityScannerAI",
                payload={"symbol":     sig.symbol,
                         "direction":  str(sig.direction),
                         "strategy":   sig.strategy_name or "",
                         "confidence": sig.confidence},
            ))

        # Publish SCAN_COMPLETE with totals so Control Tower funnel works
        self.bus.publish(SystemEvent(
            event_type=EventType.SCAN_COMPLETE,
            source_agent="MasterOrchestrator",
            payload={
                "equity":  len(equity_signals),
                "options": len(options_signals),
                "arb":     len(arb_signals),
                "total":   len(all_signals),
            },
        ))

        return all_signals

    def _run_strategy_lab(self, signals: List[TradeSignal],
                          snapshot: MarketSnapshot) -> List[TradeSignal]:
        log.info("── Layer 4: Strategy Lab ──")
        # Compute the passing set = backtest gate ∩ SHM live health
        from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS
        from strategy_lab.backtesting_ai import _BACKTEST_CACHE
        all_strategies = list(STRATEGY_PARAMS.keys())
        bt_passing  = {name for name, r in _BACKTEST_CACHE.items() if r.passes_gate}
        if not bt_passing:
            bt_passing = set(all_strategies)   # fallback before first backtest run
        shm_disabled  = self.strategy_health.get_disabled_strategies()
        perf_disabled = self.perf_tracker.get_disabled_set()
        passing_set   = bt_passing - shm_disabled - perf_disabled
        if perf_disabled:
            log.info("[StrategyLab] PerfTracker retired %d strategies: %s",
                     len(perf_disabled), ", ".join(sorted(perf_disabled)))
        # Print SHM health report if any data exists (else suppressed)
        self.strategy_health.print_health_report()
        self.meta_strategy.print_activation_report(snapshot, passing_set, all_strategies)

        matched = self.strategy_generator.assign_strategy(signals, snapshot)
        evolved = self.strategy_evolution.apply_evolved_params(matched)
        tested  = self.backtesting_ai.filter_by_backtest(evolved)
        log.info("  %d signals after strategy lab", len(tested))

        self.bus.publish(SystemEvent(
            event_type=EventType.STRATEGY_LAB_COMPLETE,
            source_agent="StrategyGeneratorAI",
            payload={
                "assigned":   len(matched),
                "after_evo":  len(evolved),
                "after_bt":   len(tested),
            },
        ))
        return tested

    def _run_risk_control(self, signals: List[TradeSignal],
                          snapshot: MarketSnapshot) -> List[TradeSignal]:
        log.info("── Layer 5: Risk Control ──")
        checked    = self.risk_manager.filter(signals)
        sized      = self.portfolio_allocator.size_positions(checked, snapshot)
        stressed   = self.stress_test_ai.validate(sized, snapshot)
        log.info("  %d signals passed risk control", len(stressed))

        rejected_count = len(signals) - len(stressed)
        if rejected_count:
            self.bus.publish(RiskEvent(
                event_type=EventType.RISK_CHECK_FAILED,
                source_agent="RiskManagerAI",
                payload={"rejected": rejected_count},
            ))
        if stressed:
            self.bus.publish(RiskEvent(
                event_type=EventType.RISK_CHECK_PASSED,
                source_agent="RiskManagerAI",
                payload={"approved": len(stressed)},
            ))

        return stressed

    def _run_debate_and_decide(self, signal: TradeSignal,
                                snapshot: MarketSnapshot) -> dict | None:
        """Run debate + decision for one signal.  Returns a summary row if trade executed."""
        log.info("── Layer 6–7: Debate & Decision for %s ──", signal.symbol)
        votes    = self.debate_system.run(signal, snapshot)
        decision = self.decision_engine.decide(signal, votes, snapshot)

        if decision.approved:
            log.info("  ✅ %s", decision.summary())
            self.bus.publish(DecisionEvent(
                event_type=EventType.TRADE_APPROVED,
                source_agent="DecisionEngine",
                payload={
                    "symbol":   signal.symbol,
                    "strategy": signal.strategy_name or "",
                    "score":    decision.confidence_score,
                    "modifier": decision.position_size_modifier,
                    "votes":    {k: getattr(v, "score", v)
                                 for k, v in (votes.votes if hasattr(votes, "votes") else {}).items()},
                },
            ))
            order = self.order_manager.execute(
                signal,
                decision,
                signal_context={
                    "regime":     (
                        snapshot.regime.value
                        if hasattr(snapshot.regime, "value")
                        else str(snapshot.regime)
                    ),
                    "vix":        snapshot.vix,
                    "distortion": bool(
                        getattr(self.global_intelligence.last_distortion,
                                "any_distortion", False)
                    ),
                },
            )
            if order:
                # ── Update portfolio heat (Portfolio Guard wiring) ────────────────
                # Every live open position uses MAX_RISK_PER_TRADE_PCT of
                # total capital.  Heat = open_positions * RISK_PER_TRADE.
                try:
                    from config import MAX_RISK_PER_TRADE_PCT as _rpt
                    _open_count = len(self.order_manager.get_open_orders())
                    self.risk_manager.update_portfolio_heat(_open_count * _rpt)
                except Exception:
                    pass
                self.trade_monitor.register(order)
                self.bus.publish(ExecutionEvent(
                    event_type=EventType.ORDER_PLACED,
                    source_agent="OrderManager",
                    payload={
                        "symbol":       signal.symbol,
                        "order_id":     getattr(order, "order_id", "sim"),
                        "entry_price":  signal.entry_price,
                        "stop_loss":    signal.stop_loss,
                        "target_price": signal.target_price,
                        "strategy":     signal.strategy_name or "",
                        "direction":    (signal.direction.value
                                         if hasattr(signal.direction, "value")
                                         else str(signal.direction)),
                        "quantity":     getattr(order, "quantity",
                                                getattr(signal, "quantity", 0)),
                        "confidence":   getattr(signal, "confidence", 0.0),
                        "rr":           getattr(signal, "risk_reward_ratio", 0.0),
                    },
                ))
                # Notify — Telegram + DB log
                if self.notifier:
                    direction = getattr(signal, "direction", "")
                    self.notifier.trade_opened(
                        signal.symbol,
                        direction.value if hasattr(direction, "value") else str(direction),
                        signal.entry_price, signal.stop_loss, signal.target_price,
                        signal.strategy_name or "", "paper",
                    )
                if self.db:
                    self.db.log_event("orchestrator", "TRADE_OPENED",
                                      f"symbol={signal.symbol} strategy={signal.strategy_name}")
                return {
                    "symbol":   signal.symbol,
                    "ltp":      signal.entry_price,   # LTP at time of scan
                    "entry":    signal.entry_price,
                    "sl":       signal.stop_loss,
                    "target":   signal.target_price,
                    "strategy": signal.strategy_name,
                    "score":    decision.confidence_score,
                    "modifier": decision.position_size_modifier,
                    "qty":      getattr(order, "quantity", 0),
                }
        else:
            log.info("  ❌ %s", decision.summary())
            self.bus.publish(DecisionEvent(
                event_type=EventType.TRADE_REJECTED,
                source_agent="DecisionEngine",
                payload={
                    "symbol":   signal.symbol,
                    "strategy": signal.strategy_name or "",
                    "score":    decision.confidence_score,
                    "reason":   decision.summary(),
                },
            ))
        return None

    def _print_cycle_summary(self, executed: List[dict],
                              snapshot: MarketSnapshot) -> None:
        """Print a formatted cycle-end table including live LTP for data verification."""
        ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hdr = (f"\n{'═'*92}\n"
               f"  CYCLE SUMMARY  |  {ts}  |  Regime: {snapshot.regime.value}"
               f"  |  VIX: {snapshot.vix:.1f}\n"
               f"{'═'*92}")
        log.info(hdr)
        log.info(
            "  %-11s  %-13s  %-28s  %-8s  %-8s  %-8s  %s",
            "Symbol", "LTP (live)", "Strategy", "Entry", "SL", "Target", "Score  Qty"
        )
        log.info("  %s", "─" * 88)
        for r in executed:
            rr = (r["target"] - r["entry"]) / max(r["entry"] - r["sl"], 0.01)
            log.info(
                "  %-11s  %-13s  %-28s  %-8.2f  %-8.2f  %-8.2f  %.2f/10  qty=%d  R:R=%.1f",
                r["symbol"],
                f"₹{r['ltp']:,.2f}",
                r["strategy"],
                r["entry"], r["sl"], r["target"],
                r["score"], r["qty"], rr,
            )
        log.info("  %s", "─" * 88)
        log.info(
            "  %d trade(s) executed  |  Data source: EquityScannerAI (live per-cycle LTP)",
            len(executed),
        )
        log.info("  Market data timestamp: %s", ts)
        log.info("═" * 92)

    # ──────────────────────────────────────────────────────────────────
    # MONITORING & LEARNING
    # ──────────────────────────────────────────────────────────────────

    def monitor_open_positions(self) -> None:
        """Called on a tick / every few minutes for live management."""
        # Submit as a background task so it never blocks a trading cycle
        self.task_queue.submit_to(
            "TradeMonitor",
            fn=self._do_monitor,
            priority=Priority.HIGH,
            description="monitor_open_positions",
        )

    def _do_monitor(self):
        """Internal — runs inside the TradeMonitor worker thread."""
        self.trade_monitor.check_all()
        portfolio: Portfolio = self.order_manager.get_portfolio()

        self.bus.publish(RiskEvent(
            event_type=EventType.PORTFOLIO_UPDATED,
            source_agent="TradeMonitor",
            payload={"drawdown_pct": portfolio.drawdown_pct,
                     "open_positions": len(portfolio.positions)},
        ))

        if portfolio.drawdown_pct >= MAX_DRAWDOWN_PCT:
            log.critical(
                "⚠ Max drawdown %.1f%% hit — HALTING trading.",
                portfolio.drawdown_pct * 100
            )
            self.bus.publish(SystemEvent(
                event_type=EventType.SYSTEM_HALT,
                source_agent="TradeMonitor",
                payload={"reason": "max_drawdown_breached",
                         "drawdown_pct": portfolio.drawdown_pct},
            ))

    def run_eod_learning(self) -> None:
        """End-of-day: feed outcomes back into the Learning Engine via TaskQueue."""
        self.task_queue.submit_to(
            "LearningEngine",
            fn=self._do_eod_learning,
            priority=Priority.NORMAL,
            description="eod_learning",
        )

    def _do_eod_learning(self):
        """Internal — runs inside the LearningEngine worker thread."""
        log.info("── Layer 10: EOD Learning ──")
        trades = self.trade_monitor.get_closed_trades()
        self.learning_engine.learn(trades)

        self.bus.publish(LearningEvent(
            event_type=EventType.LEARNING_CYCLE_COMPLETE,
            source_agent="LearningEngine",
            payload={"trades_processed": len(trades)},
        ))

        # ── Performance Evaluation ──────────────────────────────────
        log.info("── Layer 11: Performance Evaluation ──")
        for trade in trades:
            strategy   = getattr(trade, "strategy_name", "unknown")
            regime     = getattr(trade, "regime",        "unknown")
            pnl        = getattr(trade, "pnl",           0.0)
            r_multiple = getattr(trade, "r_multiple",    0.0)
            won        = pnl > 0
            self.performance_evaluator.record_trade(
                strategy=strategy, regime=regime,
                pnl=pnl, r_multiple=r_multiple, won=won,
            )
            # ── Q3: Strategy Performance Tracker (win rate, auto-disable) ──
            self.perf_tracker.record_trade(strategy, pnl_r=r_multiple)
            # ── Q3: Regime → Strategy best-fit map ─────────────────────
            if regime and regime != "unknown":
                self.regime_strategy_map.record(regime, strategy, pnl_r=r_multiple)
        if trades:
            report = self.performance_evaluator.evaluate()
            self.performance_evaluator.print_full_report(report)
            # Log leaderboard
            log.info("\n%s", self.perf_tracker.get_table())
            log.info("[RegimeStrategyMap] %s", self.regime_strategy_map.learning_stage())

        # ── Meta-Learning Feedback ─────────────────────────────────────
        log.info("── Layer 13: Meta-Learning Feedback ──")
        for trade in trades:
            self.meta_learning.record_result(
                strategy   = getattr(trade, "strategy_name", "unknown"),
                snapshot   = None,    # uses cached last_snapshot
                r_multiple = getattr(trade, "r_multiple",    0.0),
                return_pct = getattr(trade, "pnl",           0.0) / 1_000_000 * 100,
                won        = getattr(trade, "pnl",           0.0) > 0,
            )
        self.meta_learning.retrain_if_due()

        # ── Validation Engine (runs when enough trade history exists) ──
        log.info("── Layer 12: Strategy Validation ──")
        all_pnls = [getattr(t, "pnl", 0.0) for t in trades]
        if len(all_pnls) >= 30:
            self.validation_engine.validate(
                strategy_name="Portfolio",
                pnl_series=all_pnls,
                capital=1_000_000,
                print_report=True,
            )
        else:
            log.info("[ValidationEngine] Only %d trades — need 30+ to validate.",
                     len(all_pnls))

        # ── Edge Discovery (runs after learning so outcomes can seed the DB) ───
        log.info("── Edge Discovery Engine ──")
        ede_snapshot = self._last_snapshot
        if ede_snapshot is not None:
            # Feed closed-trade outcomes into the feature DB
            for trade in trades:
                sym    = getattr(trade, "symbol",    "?")
                pnl    = getattr(trade, "pnl",       0.0)
                entry  = getattr(trade, "entry_price", 1.0) or 1.0
                ret_pct = pnl / entry if entry else 0.0
                strat  = getattr(trade, "strategy_name", "")
                self.edge_discovery.enrich_with_outcomes(sym, ret_pct)
                self.edge_discovery.record_outcome(strat, pnl > 0)

            ede_report = self.edge_discovery.run_discovery_cycle(
                ede_snapshot, publish_event=True)
            log.info("%s", ede_report)
        else:
            log.info("[EDE] No snapshot cached — skipping discovery this cycle.")

        # ── EOD Notification + DB log + Platform JSON ──────────────────
        total_pnl    = sum(getattr(t, "pnl", 0.0) for t in trades) if trades else 0.0
        wins         = sum(1 for t in trades if getattr(t, "pnl", 0.0) > 0) if trades else 0
        losses       = len(trades) - wins if trades else 0
        win_rate_pct = round(wins / len(trades) * 100, 1) if trades else 0.0
        if self.notifier:
            self.notifier.eod_summary(
                len(trades), wins, losses, total_pnl, 1_000_000
            )
        if self.db:
            self.db.log_event(
                "orchestrator", "EOD_LEARNING",
                f"trades={len(trades)} wins={wins} pnl={total_pnl:+.0f}",
            )
        # ── Write platform dashboard JSON ──────────────────────────────
        try:
            import json as _json
            import pathlib as _pl
            import csv as _csv
            import config as _cfg_eod
            _pilot_cap = getattr(_cfg_eod, "PILOT_CAPITAL", 100_000)
            _eod_date  = datetime.now().strftime("%Y-%m-%d")
            _csv_path  = _pl.Path("data/paper_trades.csv")
            _open_trades, _closed_trades = [], []
            if _csv_path.exists():
                with open(_csv_path, newline="", encoding="utf-8") as _fh:
                    for _row in _csv.DictReader(_fh):
                        (_closed_trades if _row.get("event","").upper() == "CLOSED"
                         else _open_trades).append(_row)
            _cum_pnl  = sum(float(_r.get("pnl", 0) or 0) for _r in _closed_trades)
            _eod_payload = {
                "date":         _eod_date,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "today": {
                    "trades":        len(trades),
                    "wins":          wins,
                    "losses":        losses,
                    "net_pnl":       round(total_pnl, 2),
                    "win_rate_pct":  win_rate_pct,
                },
                "cumulative": {
                    "closed_trades": len(_closed_trades),
                    "open_trades":   len(_open_trades),
                    "cum_pnl":       round(_cum_pnl, 2),
                    "cum_return_pct": round(_cum_pnl / _pilot_cap * 100, 3) if _pilot_cap else 0,
                },
                "pilot_capital": _pilot_cap,
                "mode":          "paper",
            }
            _pl.Path("data").mkdir(exist_ok=True)
            _dash_path = _pl.Path("data/paper_trading_daily.json")
            _dash_path.write_text(
                _json.dumps(_eod_payload, indent=2, default=str),
                encoding="utf-8",
            )
            log.info("[EOD] Platform dashboard JSON → %s", _dash_path.resolve())
        except Exception as _dash_exc:
            log.warning("[EOD] Dashboard JSON write failed: %s", _dash_exc)

        # ── Daily AI Self-Evaluation ───────────────────────────────────
        log.info("── Daily AI Self-Evaluation ──")
        try:
            perf_report  = self.performance_evaluator.evaluate() if trades else None
            distortion   = getattr(self.global_intelligence, "last_distortion", None)
            eval_result  = self.self_evaluator.evaluate(
                trades, perf_report, last_distortion=distortion)
            eval_text    = self.self_evaluator.render(eval_result)
            log.info("\n%s", eval_text)
            self.self_evaluator.save(eval_result, eval_text)
            self.self_evaluator.notify(eval_result, eval_text)
            self.bus.publish(SystemEvent(
                event_type   = EventType.EOD_SELF_EVAL_COMPLETE,
                source_agent = "DailyAISelfEvaluator",
                payload      = {
                    "overall_score": eval_result.overall_score,
                    "grade":         eval_result.grade,
                    "issues_count":  len(eval_result.issues),
                },
            ))
        except Exception as _eval_exc:
            log.warning("[SelfEval] EOD evaluation failed: %s", _eval_exc)

        # Print end-of-day diagnostics
        self.bus.print_stats()
        self.task_queue.print_stats()

    # ──────────────────────────────────────────────────────────────────
    # SCHEDULER
    # ──────────────────────────────────────────────────────────────────

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_market_session() -> bool:
        """
        Returns True only during NSE trading hours on weekdays.
        Prevents the scheduler from firing full cycles on weekends or
        during overnight hours when no data is available.
        """
        now = datetime.now()
        if now.weekday() >= 5:          # Saturday=5, Sunday=6
            return False
        market_open  = now.replace(hour=9,  minute=0,  second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=31, second=0, microsecond=0)
        return market_open <= now <= market_close

    def _premarket_init(self) -> None:
        """
        Pre-market initialization — runs at 08:00.
        Warms caches, validates data feeds, and notifies via Telegram.
        Runs regardless of _is_market_session() (market hasn't opened yet).
        """
        log.info("═" * 60)
        log.info("  🌅 PRE-MARKET INITIALIZATION — %s",
                 datetime.now().strftime("%Y-%m-%d %H:%M"))
        log.info("═" * 60)

        # Force-refresh global intelligence cache so it's hot for 09:05
        try:
            self.global_intelligence.data_ai.fetch(force=True)
            log.info("  ✅ GlobalDataAI cache refreshed")
        except Exception as exc:
            log.warning("  ⚠️  GlobalDataAI pre-warm failed: %s", exc)

        # Check data feed health
        try:
            from data_feeds import get_feed_manager
            status = get_feed_manager().get_status()
            log.info("  📡 Feed status: %s", status)
        except Exception:
            pass

        # Telegram notification — system is online and ready
        try:
            from notifications import get_notifier
            import config as _cfg
            n = get_notifier()
            now_str = datetime.now().strftime("%d %b %Y, %H:%M")
            _mode = "🧪 Paper" if getattr(_cfg, "PAPER_TRADING", False) else "💵 Live"
            _body = (
                f"Date: {now_str}\n"
                f"Mode: {_mode} | Capital: ₹{getattr(_cfg, 'PILOT_CAPITAL', 100_000):,.0f}\n"
                f"First scan: 09:05 | Full cycles: 09:45 / 10:30 / 13:00\n"
                f"EOD report will be sent at 15:35.\n"
                f"Ready for market open at 09:15."
            )
            n.market_alert("🟢 AI Trading Brain Online", _body)
        except Exception as exc:
            log.debug("Telegram pre-market ping failed: %s", exc)

        log.info("  Pre-market init complete. Waiting for 09:05 deep scan.")

    def _premarket_data_warmup(self) -> None:
        """
        Secondary pre-market pass at 08:30 — refresh all Indian index data
        so the first cycle at 09:05 runs with up-to-date quotes.
        """
        log.info("[Orchestrator] 08:30 data warm-up — refreshing index quotes…")
        try:
            from data_feeds import get_feed_manager
            fm = get_feed_manager()
            fm.get_multiple_quotes(["NIFTY", "BANKNIFTY", "INDIAVIX"])
            log.info("[Orchestrator] Index quotes refreshed ✓")
        except Exception as exc:
            log.warning("[Orchestrator] Data warm-up failed: %s", exc)

    def _guarded_cycle(self) -> None:
        """Run a full cycle only during market hours; log a skip otherwise."""
        if self._is_market_session():
            self.run_full_cycle()
        else:
            log.debug("[Orchestrator] Outside market session — cycle skipped.")

    def start_scheduler(self) -> None:
        """
        Start the full intraday scheduler:
          • 08:00  — pre-market system initialization + Telegram ping
          • 08:30  — data warm-up (refresh index quotes)
          • 09:05–15:00 — deep-scan slots (via MarketMonitor callbacks)
          • 09:45 / 10:30 / 13:00 — full analysis cycles
          • 15:35  — EOD learning cycle
          • Every 5 min — open-position monitor (market hours only)

        Continuous 30-second light scan is handled by MarketMonitor in its
        own background thread (started by _start_monitor below).
        """
        import schedule as sched_lib   # pip install schedule

        # ── Start continuous monitoring thread (30s light scan) ────────
        self._start_monitor()

        # ── Pre-market ─────────────────────────────────────────────────
        sched_lib.every().day.at("08:00").do(self._premarket_init)
        sched_lib.every().day.at("08:30").do(self._premarket_data_warmup)

        # ── Intraday full-cycle slots ───────────────────────────────────
        # 09:45  first trade decision window
        sched_lib.every().day.at(SCHEDULE["trade_decision"]).do(self._guarded_cycle)
        # 10:30  mid-morning re-scan
        sched_lib.every().day.at(SCHEDULE["mid_morning_scan"]).do(self._guarded_cycle)
        # 13:00  afternoon session
        sched_lib.every().day.at(SCHEDULE["afternoon_scan"]).do(self._guarded_cycle)

        # ── EOD learning ───────────────────────────────────────────────
        sched_lib.every().day.at(SCHEDULE["eod_learning"]).do(self.run_eod_learning)

        # ── Position monitor (every 5 min, market hours only) ──────────
        sched_lib.every(5).minutes.do(
            lambda: self.monitor_open_positions()
            if self._is_market_session() else None
        )

        log.info("[Orchestrator] Scheduler armed.")
        log.info("  Pre-market : 08:00 init | 08:30 data warm-up")
        log.info("  Deep scans : 09:05 / 09:10 / 09:20 / 10:30 / 13:00 / 15:00  (MarketMonitor)")
        log.info("  Full cycle : 09:45 / 10:30 / 13:00")
        log.info("  EOD        : 15:35")
        log.info("  Monitoring : every 5 min  |  Light scan: every 30s")

        self.bus.publish(SystemEvent(
            event_type=EventType.SYSTEM_STARTUP,
            source_agent="MasterOrchestrator",
            payload={"ts": datetime.now().isoformat()},
        ))

        def _run():
            while not self._halt:
                sched_lib.run_pending()
                time.sleep(15)   # 15s resolution gives < 15s slot jitter

        t = threading.Thread(target=_run, daemon=True, name="Scheduler")
        t.start()
        log.info("[Orchestrator] Scheduler thread running (15s resolution).")

    def shutdown(self):
        """Gracefully shut down the task queue and publish SYSTEM_SHUTDOWN event."""
        log.info("Shutting down AI Trading Brain…")
        self.bus.publish(SystemEvent(
            event_type=EventType.SYSTEM_SHUTDOWN,
            source_agent="MasterOrchestrator",
            payload={"ts": datetime.now().isoformat()},
        ))
        self.task_queue.shutdown(timeout=5.0)
