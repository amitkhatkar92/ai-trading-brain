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
import os
import sched
import time
import threading
from datetime import datetime
from typing import List, Optional

from config import SCHEDULE, MAX_DRAWDOWN_PCT, TOTAL_CAPITAL
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
from risk_control.smart_execution           import SmartExecutionEngine
from risk_control.correlation_engine        import CorrelationEngine

from debate_system.multi_agent_debate       import MultiAgentDebate
from decision_ai.decision_engine            import DecisionEngine
from execution_engine.order_manager             import OrderManager
from execution_engine.options_order_manager     import OptionsOrderManager, get_options_order_manager
from risk_control.options_risk_engine           import get_options_risk_engine
from learning_system.options_performance_tracker import get_options_performance_tracker
from models.trade_signal                        import SignalType as _SigType
from models.agent_output                        import DecisionResult as _DecisionResult
from trade_monitoring.trade_monitor             import TradeMonitor
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
        
        # ── Layer 5.5: Smart Execution & Correlation Control ──────────
        # Get capital from config; defaults to 50k for safety
        from config import TOTAL_CAPITAL
        _capital = getattr(_cfg, 'TOTAL_CAPITAL', TOTAL_CAPITAL) if '_cfg' in dir() else TOTAL_CAPITAL
        try:
            _capital = float(TOTAL_CAPITAL)
        except (TypeError, ValueError):
            _capital = 50_000
        self.smart_execution = SmartExecutionEngine(capital=_capital)
        self.correlation_engine = CorrelationEngine(max_per_sector=2)

        # ── Market Simulation Engine (between Risk Control and Debate) ────
        self.simulation_engine   = SimulationEngine(mc_runs=1_000)

        # ── Layer 7.5: Fail-Safe Risk Guardian ────────────────────────
        self.risk_guardian       = FailSafeRiskGuardian(total_capital=1_000_000)

        # ── Layer 6–7: Debate & Decision ───────────────────────────────
        self.debate_system       = MultiAgentDebate()
        self.decision_engine     = DecisionEngine()

        # ── Layer 8: Execution ─────────────────────────────────────────
        self.order_manager       = OrderManager()

        # ── Layer 8b: Options Execution (dedicated, lot-aware) ─────────
        self.options_order_manager = get_options_order_manager()
        self.options_risk_engine   = get_options_risk_engine()
        # Pre-warm the learning tracker so it loads persisted weights
        get_options_performance_tracker()

        # ── Layer 9: Trade Monitoring ──────────────────────────────────
        self.trade_monitor       = TradeMonitor()
        # Cross-wire: both directions so each can call the other's close/deregister methods.
        self.order_manager.inject_trade_monitor(self.trade_monitor)
        self.trade_monitor.inject_order_manager(self.order_manager)
        # Re-register any positions restored from the journal so TradeMonitor
        # monitors their SL/target and can fire adaptive profit extension on them.
        for _carry in self.order_manager.get_open_orders():
            self.trade_monitor.register(_carry)
            log.debug("[Orchestrator] TradeMonitor registered carry: %s %s",
                      _carry.symbol, _carry.order_id)

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
        # Feed-degraded escalation counter (symbol → consecutive degraded cycles)
        self._feed_degraded_counts: dict = {}
        # Monitoring continuity: tracks last successful _do_monitor execution.
        # Used by FIX #3 blackout detection to emit [MonitoringGap] warnings.
        self._last_monitor_ts: Optional[datetime] = None

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
        # Mark session dirty — streak must reset at EOD
        try:
            from learning_system.strategy_performance_tracker import get_stability_ledger
            get_stability_ledger().flag_session_issue(
                f"SYSTEM_HALT from {event.source_agent}")
        except Exception:
            pass

    def _on_drawdown_alert(self, event):
        pct = event.payload.get("drawdown_pct", 0) * 100
        log.warning("[EDA] DRAWDOWN_ALERT: %.1f%% drawdown reported.", pct)
        if pct >= MAX_DRAWDOWN_PCT * 100:
            self._halt = True
            self.order_manager.close_all_positions()
            # Mark session dirty — a real drawdown halt is a structural event
            try:
                from learning_system.strategy_performance_tracker import get_stability_ledger
                get_stability_ledger().flag_session_issue(
                    f"DRAWDOWN_HALT {pct:.1f}%")
            except Exception:
                pass

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
        scan_name may carry a correlation ID: "{name}#{id}" — strip before use.
        """
        # Parse optional correlation ID embedded by MarketMonitor
        if "#" in scan_name:
            actual_name, scan_id = scan_name.split("#", 1)
        else:
            actual_name, scan_id = scan_name, scan_name

        log.info("[Orchestrator] [ScanStart] id=%s scan=%s", scan_id, actual_name)
        _t0 = time.monotonic()
        if self._halt:
            log.info("[Orchestrator] [ScanDone]  id=%s scan=%s result=HALTED duration=0ms", scan_id, actual_name)
            return
        try:
            # Force-expire the GlobalDataAI cache so the next cycle fetches fresh data
            try:
                self.global_intelligence.data_ai._last_fetch_ts = 0.0
            except Exception:
                pass

            if actual_name == "market_open_regime":
                # Re-run regime classification with fresh data
                raw = self.market_data_ai.fetch()
                self.market_regime_ai.classify(raw)
            elif actual_name in ("first_opportunity_scan", "strategy_evaluation",
                               "mid_morning_scan", "mid_session_scan",
                               "afternoon_scan", "early_afternoon_scan"):
                # Lightweight opportunity re-scan (non-blocking)
                self.task_queue.submit_to(
                    "MasterOrchestrator",
                    self.run_full_cycle,
                    priority=Priority.HIGH,
                    description=f"deep_scan:{actual_name}:{scan_id}",
                )
            elif actual_name == "closing_analysis":
                log.info("[Orchestrator] Closing analysis — checking positions.")
                self.bus.publish(SystemEvent(
                    event_type=EventType.CYCLE_STARTED,
                    source_agent="MasterOrchestrator",
                    payload={"ts": datetime.now().isoformat(), "label": "closing_analysis"},
                ))
                self.trade_monitor.check_open_positions()
                # Also evaluate options exit conditions
                try:
                    _closed = self.options_order_manager.check_exits()
                    if _closed:
                        log.info("[Orchestrator] Options check_exits: %d position(s) closed.", _closed)
                except Exception as _oe:
                    log.debug("[Orchestrator] options check_exits error: %s", _oe)
                self.bus.publish(SystemEvent(
                    event_type=EventType.CYCLE_COMPLETE,
                    source_agent="MasterOrchestrator",
                    payload={"label": "closing_analysis"},
                ))
            _dur = int((time.monotonic() - _t0) * 1000)
            log.info("[Orchestrator] [ScanDone]  id=%s scan=%s result=OK duration=%dms", scan_id, actual_name, _dur)
        except Exception as exc:
            _dur = int((time.monotonic() - _t0) * 1000)
            log.warning("[Orchestrator] [ScanDone]  id=%s scan=%s result=ERROR duration=%dms: %s",
                        scan_id, actual_name, _dur, exc)

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

        # ── STEP 4b: Options Fast-Path ────────────────────────────────
        # Options/spread signals must NOT pass through the equity-oriented
        # gates below (MarketSimulation stability, Debate R:R scoring,
        # SmartExecution, DecisionEngine 6.8 threshold).  Route them directly
        # to OptionsRiskEngine → OptionsOrderManager here, then continue with
        # equity signals only for the remaining steps.
        _options_signals = [s for s in approved_signals
                            if s.signal_type in (_SigType.OPTIONS, _SigType.SPREAD)]
        approved_signals = [s for s in approved_signals
                            if s.signal_type not in (_SigType.OPTIONS, _SigType.SPREAD)]

        if _options_signals:
            log.info("── Options Fast-Path: %d signal(s) ──", len(_options_signals))
            self._run_options_fast_path(_options_signals, snapshot)

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

        # ── STEP 5.5: Smart Execution & Correlation Filtering ─────────────
        # Apply intelligent trade selection BEFORE debate & decision
        log.info("── Layer 5.5: Smart Execution & Correlation Filtering ──")
        
        # Step 1: Decorrelate by sector
        # Convert TradeSignal objects to dicts for correlation engine
        signals_as_dicts_for_corr = [
            {
                "symbol": s.symbol,
                "sector": getattr(s, "sector", "OTHER"),
                "direction": s.direction.value if hasattr(s.direction, "value") else str(s.direction),
                "confidence": getattr(s, "confidence_score", 0.7),
                "_original_signal": s,  # Keep reference
            }
            for s in guardian_decision.approved_signals
        ]
        
        with self.system_monitor.time_layer("CorrelationEngine"):
            decorrelated_dicts = self.correlation_engine.reduce_correlation(signals_as_dicts_for_corr)
            
            # Extract original signals from decorrelated dicts
            decorrelated_signals = [
                d.get("_original_signal") for d in decorrelated_dicts
                if "_original_signal" in d and d.get("_original_signal") is not None
            ]
            
            sector_summary = self.correlation_engine.get_sector_summary(decorrelated_dicts)
            log.info(
                "[CorrelationEngine] After decorrelation: %d signals "
                "(Sector breakdown: %s)",
                len(decorrelated_signals),
                ", ".join(f"{s}: {c}" for s, c in sector_summary.items())
            )
            self.bus.publish(SystemEvent(
                event_type=EventType.RISK_CHECK_PASSED,
                source_agent="CorrelationEngine",
                payload={
                    "approved": len(decorrelated_signals),
                    "before_correlation": len(guardian_decision.approved_signals),
                    "after_correlation": len(decorrelated_signals),
                    "sector_breakdown": sector_summary,
                },
            ))
        
        # Step 2: Apply smart execution filtering
        with self.system_monitor.time_layer("SmartExecutionEngine"):
            portfolio = self.order_manager.get_portfolio()
            current_capital = portfolio.total_capital if hasattr(portfolio, 'total_capital') else snapshot.portfolio_value if hasattr(snapshot, 'portfolio_value') else TOTAL_CAPITAL
            
            final_signals = self.smart_execution.filter_trades(
                trades=[
                    {
                        "symbol": s.symbol,
                        "sector": getattr(s, "sector", "OTHER"),
                        "direction": s.direction.value if hasattr(s.direction, "value") else str(s.direction),
                        "confidence": getattr(s, "confidence_score", 0.7),
                        "entry_price": s.entry_price,
                        "stop_loss": s.stop_loss,
                        "target": s.target if hasattr(s, "target") else None,
                        "original_signal": s,  # keep reference to full signal
                    }
                    for s in decorrelated_signals
                ],
                vix=snapshot.vix,
                drawdown_factor=1.0,  # Could be adjusted based on portfolio drawdown
            )
            
            # Separate accepted and rejected
            accepted_trade_dicts = [t for t in final_signals if "position_size" in t]
            rejected_trade_dicts = [t for t in final_signals if "rejection_reason" in t]
            
            # Extract original signals from accepted trades
            final_approved_signals = [
                t.get("original_signal") for t in accepted_trade_dicts
                if "original_signal" in t and t.get("original_signal") is not None
            ]
            
            # Log summary
            exec_summary = self.smart_execution.get_summary(final_signals)
            log.info(
                "[SmartExecutionEngine] Summary: "
                "Accepted=%d | Rejected=%d | "
                "Total Exposure=$%.0f (%.1f%%) | "
                "Bullish=$%.0f | Bearish=$%.0f",
                exec_summary["accepted_count"],
                exec_summary["rejected_count"],
                exec_summary["total_exposure"],
                exec_summary["exposure_pct"],
                exec_summary["direction_breakdown"]["BUY"],
                exec_summary["direction_breakdown"]["SELL"],
            )
            self.bus.publish(SystemEvent(
                event_type=EventType.PORTFOLIO_UPDATED,
                source_agent="SmartExecutionEngine",
                payload=exec_summary,
            ))
        
        # Use filtered signals for debate & decision
        signals_for_debate = final_approved_signals

        # ── STEP 6: Debate + Decision ──────────────────────────────────
        executed: List[dict] = []
        with self.system_monitor.time_layer("DebateAndDecision"):
            for signal in signals_for_debate:
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
        self.odm.record_cycle(signals_generated=len(signals), approved_trades=len(sim_result.approved_trades))
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
        import time as _t
        log.info("── Layer 3: Opportunity Engine ──")

        _t0 = _t.monotonic()
        equity_signals  = self.equity_scanner.scan(snapshot, odm_directive=odm_directive)
        _t1 = _t.monotonic()

        options_signals = self.options_opportunity.scan(snapshot)
        _t2 = _t.monotonic()

        arb_signals     = self.arbitrage_ai.scan(snapshot)
        _t3 = _t.monotonic()

        log.info("[OE-timing] equity=%.0fms  options=%.0fms  arb=%.0fms",
                 (_t1 - _t0) * 1000, (_t2 - _t1) * 1000, (_t3 - _t2) * 1000)

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

        matched = self.strategy_generator.assign_strategy(
            signals, snapshot,
            excluded_strategies=shm_disabled | perf_disabled,
            shm_ref=self.strategy_health,
        )
        evolved = self.strategy_evolution.apply_evolved_params(matched)
        tested  = self.backtesting_ai.filter_by_backtest(
            evolved, vix=snapshot.vix, regime=snapshot.regime
        )
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

    # ── Options-specific constants ──────────────────────────────────────────
    # Minimum confidence to enter an options trade.  Higher than equity
    # (6.0) because options skip the 5-agent debate that normally validates
    # signal quality — we compensate with stricter chain quality gates.
    _OPTIONS_MIN_CONFIDENCE   = 6.5

    # IVR must be ≥ this to sell premium (IC / short spreads)
    _IVR_SELL_MIN             = 20.0

    # IVR must be ≤ this to buy volatility (Straddle / debit spreads)
    _IVR_BUY_MAX              = 55.0

    # DTE window: don't enter outside this range (gamma / theta trade-off).
    # VIX-adaptive: high VIX compresses the window to shorter expiries where
    # the position reaches its profit target faster and carries less event risk.
    _DTE_MIN                  = 10
    _DTE_MAX                  = 60
    # VIX thresholds used to adapt the DTE window at runtime
    _VIX_HIGH_DTE_MAX         = 30    # DTE_MAX when VIX ≥ 25  (high vol — shorter)
    _VIX_LOW_DTE_MIN          = 20    # DTE_MIN when VIX < 15  (low vol — longer)

    # Chain quality score minimum (0.0–1.0, see OptionsFeed.chain_quality_score)
    _CHAIN_QUALITY_MIN        = 0.5

    def _run_options_fast_path(self, signals: List[TradeSignal],
                               snapshot: MarketSnapshot) -> None:
        """
        Proper multi-layer execution path for OPTIONS and SPREAD signals.

        Equity pipeline gates that are bypassed (wrong calibration):
          ✗  RiskManagerAI    — 2.0 R:R threshold doesn't apply to credit spreads
          ✗  MarketSimulation — stability threshold calibrated for equities
          ✗  CorrelationEngine — sector-based; index options are uncorrelated
          ✗  SmartExecution   — equity-specific position filtering
          ✗  MultiAgentDebate — R:R scoring penalises credit strategies
          ✗  DecisionEngine   — 6.8 threshold built for directional equity

        Options-specific gates applied (4 independent layers):
          Layer A: Universal kill-switch  — VIX > 45, trading disabled
          Layer B: Signal quality gate    — live data, confidence, DTE, IVR-strategy fit
          Layer C: OptionsRiskEngine      — capital %, per-trade loss, VIX sell limit, lot sizing
          Layer D: OptionsOrderManager    — execution, position limit, duplicate check
        """
        log.info("── Options Fast-Path: %d signal(s) entering 4-layer validation ──",
                 len(signals))

        # ── LAYER A: Universal Kill-Switch ─────────────────────────────
        # These thresholds match RiskGuardian's hard-coded limits exactly.
        # Options must never trade when the entire system is halted.
        if not is_trading_enabled():
            log.warning("[OptionsFastPath] ⛔ Kill switch active — all options blocked.")
            return

        if snapshot.vix > 45.0:
            log.warning(
                "[OptionsFastPath] ⛔ VIX=%.1f > 45 — extreme market stress, "
                "options blocked (all strategies).", snapshot.vix
            )
            return

        # ── LAYER B: Signal Quality Gate ────────────────────────────────
        qualified = self._options_quality_gate(signals, snapshot)
        if not qualified:
            return

        # ── LAYERS C + D: Risk sizing + Execution ───────────────────────
        _sig_ctx = {
            "regime": (
                snapshot.regime.value
                if hasattr(snapshot.regime, "value")
                else str(snapshot.regime)
            ),
            "vix": snapshot.vix,
        }
        for signal in qualified:
            # Layer C: OptionsRiskEngine
            approved = self.options_risk_engine.approve_and_size(
                signal, snapshot,
                open_exposure_rs=self.options_order_manager.get_total_options_exposure_rs(),
            )
            if not approved:
                log.info(
                    "[OptionsFastPath] ❌ [LayerC] Risk engine rejected %s %s.",
                    signal.symbol, signal.strategy_name,
                )
                continue

            # Layer D: OptionsOrderManager
            order = self.options_order_manager.execute(signal, _DecisionResult(
                approved=True,
                confidence_score=signal.confidence,
                position_size_modifier=1.0,
                reasoning="options_quality_gate_approved",
            ), signal_context=_sig_ctx)

            if order:
                log.info(
                    "[OptionsFastPath] ✅ PLACED %s  %s  lots=%d  "
                    "max_loss=₹%.0f  DTE=%d  chain_quality=%.2f",
                    order.order_id, order.strategy, order.lots,
                    order.max_loss_rs, order.dte_at_entry,
                    signal._meta_quality if hasattr(signal, "_meta_quality") else 1.0,
                )

                # ── Correlation visibility check ───────────────────────
                # Index options (NIFTY / BANKNIFTY) share directional exposure
                # with any open equity position.  This is a WARNING only —
                # the trade has already been placed.  Visibility so the user
                # can make informed decisions about total index exposure.
                _INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY"}
                if signal.symbol in _INDEX_SYMBOLS:
                    try:
                        _eq_open = self.order_manager.get_open_orders()
                        if _eq_open:
                            _eq_syms = [o.symbol for o in _eq_open]
                            log.warning(
                                "[CorrelationWarning] Index options + equity exposure overlap detected. "
                                "Options: %s %s  |  Open equity positions: %s  "
                                "— combined index exposure not independently diversified.",
                                signal.symbol, signal.strategy_name or "",
                                ", ".join(_eq_syms),
                            )
                    except Exception:
                        pass   # visibility only — never block execution

                self.bus.publish(ExecutionEvent(
                    event_type=EventType.ORDER_PLACED,
                    source_agent="OptionsOrderManager",
                    payload={
                        "symbol":      signal.symbol,
                        "order_id":    order.order_id,
                        "entry_price": signal.entry_price,
                        "strategy":    signal.strategy_name or "",
                        "lots":        order.lots,
                        "lot_size":    order.lot_size,
                        "max_loss_rs": order.max_loss_rs,
                        "expiry":      order.expiry_date.isoformat(),
                        "dte":         order.dte_at_entry,
                    },
                ))

        # Run exit checks each cycle to close positions that hit SL/TP/DTE
        self.options_order_manager.check_exits()

    def _options_quality_gate(
        self,
        signals:  List[TradeSignal],
        snapshot: MarketSnapshot,
    ) -> List[TradeSignal]:
        """
        Options-specific multi-check quality filter.

        Replaces the equity Debate + DecisionEngine for options signals.
        Each check is independent — all must pass.

        Check 1: Live data only — synthetic B-S chain rejected
        Check 2: Minimum confidence threshold (OPTIONS_MIN_CONFIDENCE = 6.5)
        Check 3: Chain quality score ≥ 0.5 (from OptionsFeed.chain_quality_score)
        Check 4: DTE window (VIX-adaptive):
                   VIX ≥ 25 → DTE 10–30 (shorter expiry during high vol)
                   VIX < 15 → DTE 20–60 (longer expiry during low vol)
                   else     → DTE 10–60 (normal window)
        Check 5: IVR–strategy alignment
          • Iron Condor / short spread: IVR ≥ 20 (enough premium to collect)
          • Long Straddle / debit buy:  IVR ≤ 55 (don't overpay for vol)
        Check 6: Correlation de-duplication
          • If two index signals share the same directional bias (both BUY or
            both SELL), only the higher-confidence one is kept.  Neutral
            strategies (Iron Condor / Straddle) are exempt.
        """
        import json as _json
        passed: List[TradeSignal] = []

        # ── Compute VIX-adaptive DTE bounds for this cycle ─────────────
        vix = snapshot.vix
        if vix >= 25.0:
            dte_min = self._DTE_MIN                  # 10
            dte_max = self._VIX_HIGH_DTE_MAX         # 30 — shorter expiry during stress
            _dte_note = f"[VIX={vix:.1f}≥25 → DTE cap={dte_max}]"
        elif vix < 15.0:
            dte_min = self._VIX_LOW_DTE_MIN          # 20 — avoid theta waste on shorts
            dte_max = self._DTE_MAX                  # 60
            _dte_note = f"[VIX={vix:.1f}<15 → DTE floor={dte_min}]"
        else:
            dte_min = self._DTE_MIN                  # 10
            dte_max = self._DTE_MAX                  # 60
            _dte_note = f"[VIX={vix:.1f} normal window]"

        log.debug("[OptionsQuality] DTE window: %d–%d %s", dte_min, dte_max, _dte_note)

        for sig in signals:
            sym = sig.symbol
            strat = sig.strategy_name or ""

            # Parse signal metadata
            meta: dict = {}
            try:
                meta = _json.loads(sig.notes or "{}")
            except Exception:
                pass

            is_live      = meta.get("is_live", False)
            chain_qual   = meta.get("chain_quality", 0.0)
            dte          = meta.get("dte", 0)
            iv_rank      = meta.get("iv_rank", 50.0)
            chain_issues = meta.get("chain_issues", [])

            # Check 1: Live data gate
            if not is_live:
                log.info(
                    "[OptionsQuality] ❌ [C1] %s %s — synthetic data, not permitted.",
                    sym, strat,
                )
                continue

            # Check 2: Confidence threshold
            if sig.confidence < self._OPTIONS_MIN_CONFIDENCE:
                log.info(
                    "[OptionsQuality] ❌ [C2] %s %s — confidence %.1f < %.1f.",
                    sym, strat, sig.confidence, self._OPTIONS_MIN_CONFIDENCE,
                )
                continue

            # Check 3: Chain quality score
            if chain_qual < self._CHAIN_QUALITY_MIN:
                log.warning(
                    "[OptionsQuality] ❌ [C3] %s %s — chain_quality=%.2f < %.2f. "
                    "Issues: %s",
                    sym, strat, chain_qual, self._CHAIN_QUALITY_MIN,
                    "; ".join(chain_issues) if chain_issues else "unknown",
                )
                continue

            # Check 4: VIX-adaptive DTE window
            if dte < dte_min:
                log.info(
                    "[OptionsQuality] ❌ [C4] %s %s — DTE=%d < %d %s.",
                    sym, strat, dte, dte_min, _dte_note,
                )
                continue
            if dte > dte_max:
                log.info(
                    "[OptionsQuality] ❌ [C4] %s %s — DTE=%d > %d %s.",
                    sym, strat, dte, dte_max, _dte_note,
                )
                continue

            # Check 5: IVR–strategy alignment
            is_credit_strat = any(k in strat for k in ["Iron_Condor", "Bear_Put_Spread",
                                                         "Bull_Call_Spread"])
            is_buy_vol_strat = "Straddle" in strat or "Strangle" in strat

            if is_credit_strat and iv_rank < self._IVR_SELL_MIN:
                log.info(
                    "[OptionsQuality] ❌ [C5] %s %s — IVR=%.0f < %.0f, "
                    "insufficient premium to sell.",
                    sym, strat, iv_rank, self._IVR_SELL_MIN,
                )
                continue

            if is_buy_vol_strat and iv_rank > self._IVR_BUY_MAX:
                log.info(
                    "[OptionsQuality] ❌ [C5] %s %s — IVR=%.0f > %.0f, "
                    "vol too expensive to buy.",
                    sym, strat, iv_rank, self._IVR_BUY_MAX,
                )
                continue

            sig._meta_quality = chain_qual  # attach for logging in fast-path
            passed.append(sig)
            log.info(
                "[OptionsQuality] ✅ %s %s passed C1–C5  "
                "confidence=%.1f  DTE=%d  IVR=%.0f  chain_quality=%.2f",
                sym, strat, sig.confidence, dte, iv_rank, chain_qual,
            )

        # ── Check 6: Correlation de-duplication ────────────────────────
        # Both NIFTY and BANKNIFTY are driven by the same broad market.
        # Two directional signals in the same direction double the index
        # exposure without adding independent edge.  Keep the higher-confidence
        # one.  Neutral strategies (Iron Condor, Long Straddle) are exempt
        # because they profit from range / vol, not a specific direction.
        _NEUTRAL = {"Iron_Condor_Range", "Long_Straddle"}
        directional = [s for s in passed
                       if (s.strategy_name or "") not in _NEUTRAL]
        neutral     = [s for s in passed
                       if (s.strategy_name or "") in _NEUTRAL]

        # Group directional signals by bias (BUY / SELL)
        from models.trade_signal import SignalDirection as _SD
        buys  = [s for s in directional if s.direction == _SD.BUY]
        sells = [s for s in directional if s.direction == _SD.SELL]

        def _deduplicate(group: List[TradeSignal]) -> List[TradeSignal]:
            """If >1 signal in same direction, keep highest confidence only."""
            if len(group) <= 1:
                return group
            best = max(group, key=lambda s: s.confidence)
            dropped = [s.symbol for s in group if s is not best]
            log.info(
                "[OptionsQuality] [C6] Correlation control: keeping %s %s "
                "(confidence=%.1f); dropping same-direction duplicate(s): %s",
                best.symbol, best.strategy_name, best.confidence, dropped,
            )
            return [best]

        passed = _deduplicate(buys) + _deduplicate(sells) + neutral

        log.info(
            "[OptionsQuality] %d/%d signal(s) passed all 6 checks (C1–C6).",
            len(passed), len(signals),
        )
        return passed



    def _run_risk_control(self, signals: List[TradeSignal],
                          snapshot: MarketSnapshot) -> List[TradeSignal]:
        log.info("── Layer 5: Risk Control ──")
        # NOTE: options/spread signals are removed from `signals` before this
        # function is called (see STEP 4b options fast-path above).
        # This function only handles equity and futures signals.

        # Use heat-split filter so we can hand heat-blocked elite signals to
        # the institutional rotation engine (SmartSwap 2.0).
        checked, heat_blocked = self.risk_manager.filter_with_heat_split(signals)

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

        # ── SmartSwap 2.0: Institutional Rotation Engine ──────────────
        # Only heat-blocked signals that are independently valid enter here.
        # This is an upgrade path, never a rescue mechanism.
        if heat_blocked:
            log.info(
                "[RotationEngine] %d heat-blocked candidate(s) entering rotation eval.",
                len(heat_blocked),
            )
            portfolio = self.order_manager.get_portfolio()
            self._institutional_rotation_engine(heat_blocked, snapshot, portfolio)

        return stressed

    # ─────────────────────────────────────────────────────────────────────────
    # INSTITUTIONAL ROTATION ENGINE — SmartSwap 2.0
    # Portfolio-level upgrade path.  Only elite signals blocked by heat enter.
    # Never a rescue mechanism — only an upgrade mechanism.
    # ─────────────────────────────────────────────────────────────────────────

    def _institutional_rotation_engine(
        self,
        heat_blocked: List[TradeSignal],
        snapshot: "MarketSnapshot",
        portfolio: "Portfolio",
    ) -> None:
        """
        Institutional SmartSwap 2.0.

        Called with signals that passed all risk checks EXCEPT portfolio heat.
        Each candidate is evaluated through 7 strict institutional gates.
        If all gates pass, the single weakest position is closed and the
        incoming elite trade is opened.  Max 1 rotation per calendar day.

        Gate summary
        ─────────────
        1. Incoming score ≥ 8.0  (elite only — enforced upstream by heat-split,
           but double-checked here for defensive correctness)
        2. A weak existing position exists (R ≤ 0.25 OR stale > 3 days)
        3. Score edge: new_score ≥ weakest_score + 1.0
        4. No same-thesis duplication (same symbol OR same strategy_name)
        5. Daily rotation cap: max 1 forced rotation per calendar day
        6. No late-day rotations after 13:30 IST
        7. Forced-close loss cap: do not rotate if position is down > -0.50 R
        """
        today = datetime.now().date()

        for sig in heat_blocked:
            sig.notes += " [reason=HEAT_BLOCK_ROTATION_CANDIDATE]"
            log.info(
                "[RotationEval] %s %s score=%.2f reason=HEAT_BLOCK_ROTATION_CANDIDATE",
                sig.symbol, sig.direction, sig.confidence,
            )

            # ── Gate 1: Elite incoming signal ─────────────────────────────────
            if sig.confidence < 8.0:
                log.info(
                    "[RotationReject] %s score=%.2f < 8.0 — not elite",
                    sig.symbol, sig.confidence,
                )
                continue

            # ── Gate 5: Daily rotation cap ────────────────────────────────────
            last_date = getattr(self, "_last_rotation_date", None)
            if last_date == today:
                log.info(
                    "[RotationReject] %s — daily rotation cap reached (1/day). "
                    "Next eligible: tomorrow.",
                    sig.symbol,
                )
                continue

            # ── Gate 6: No late-day rotations ─────────────────────────────────
            now = datetime.now()
            cutoff = now.replace(hour=13, minute=30, second=0, microsecond=0)
            if now >= cutoff:
                log.info(
                    "[RotationReject] %s — after 13:30 IST cutoff (%s). "
                    "Too late to rotate safely.",
                    sig.symbol, now.strftime("%H:%M"),
                )
                continue

            # ── Gate 2: Find weakest eligible existing position ───────────────
            # Deterministic: rank by (r_multiple ASC, days_open DESC).
            weakest: Optional["Position"] = None
            weakest_r: float = float("inf")
            weakest_days: int = 0

            for pos in portfolio.positions.values():
                r = pos.r_multiple
                days_open = (now - pos.entry_time).days

                # Eligible for replacement: weak R or stale
                if r <= 0.25 or days_open > 3:
                    # Choose the weakest (lowest R); break ties by oldest
                    if (weakest is None
                            or r < weakest_r
                            or (r == weakest_r and days_open > weakest_days)):
                        weakest = pos
                        weakest_r = r
                        weakest_days = days_open

            if weakest is None:
                log.info(
                    "[RotationReject] %s — no weak/stale position eligible for rotation "
                    "(all positions healthy R > 0.25 and age ≤ 3 days).",
                    sig.symbol,
                )
                continue

            log.info(
                "[RotationEval] Weakest position: %s R=%.2f days=%d",
                weakest.symbol, weakest_r, weakest_days,
            )

            # ── Gate 3: Score edge — new must outperform by ≥ 1.0 ────────────
            weakest_confidence = getattr(weakest, "confidence", 0.0)
            score_edge = sig.confidence - weakest_confidence
            if score_edge < 1.0:
                log.info(
                    "[RotationReject] %s score_edge=%.2f < 1.0 "
                    "(new=%.1f old=%.1f). Not enough improvement.",
                    sig.symbol, score_edge, sig.confidence, weakest_confidence,
                )
                continue

            # ── Gate 4: No same-thesis duplication ───────────────────────────
            if (sig.symbol == weakest.symbol
                    or sig.strategy_name == weakest.strategy_name):
                log.info(
                    "[RotationReject] %s — same thesis as target position %s "
                    "(symbol=%s strategy=%s). Rotation would not diversify.",
                    sig.symbol, weakest.symbol,
                    sig.symbol == weakest.symbol,
                    sig.strategy_name == weakest.strategy_name,
                )
                continue

            # ── Gate 7: Forced-close loss cap (-0.50 R) ───────────────────────
            if weakest_r < -0.50:
                log.info(
                    "[RotationReject] %s — target position %s is down %.2f R "
                    "(limit -0.50 R). Closing a deep loser is a stop-loss, "
                    "not a rotation. Use normal SL management.",
                    sig.symbol, weakest.symbol, weakest_r,
                )
                continue

            # ── ALL GATES PASSED ──────────────────────────────────────────────
            log.warning(
                "[RotationApproved] ROTATION APPROVED: close %s (R=%.2f, %dd) "
                "→ open %s (score=%.1f, edge=+%.1f). Executing.",
                weakest.symbol, weakest_r, weakest_days,
                sig.symbol, sig.confidence, score_edge,
            )

            # Close the weakest position via order manager
            try:
                self.order_manager.close_position(
                    weakest.symbol,
                    reason=f"SMARTSWAP_ROTATION: replaced by {sig.symbol}",
                )
            except Exception as exc:
                log.error(
                    "[RotationError] Failed to close %s for rotation: %s",
                    weakest.symbol, exc,
                )
                continue

            # Mark daily cap consumed — only 1 rotation per day
            self._last_rotation_date = today

            # Route the incoming signal through the full debate + decision path
            try:
                self._run_debate_and_decide(sig, snapshot)
            except Exception as exc:
                log.error(
                    "[RotationError] Failed to open %s after rotation close: %s",
                    sig.symbol, exc,
                )

            # Process at most one rotation per cycle regardless of candidate count
            break

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
                    "votes":    {v.agent_name: v.score for v in votes},
                },
            ))

            # ── Equity / Futures path (original logic) ─────────────────
            # NOTE: OPTIONS/SPREAD signals are handled in _run_options_fast_path()
            # BEFORE the debate loop.  They will never appear here.
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
                # order_manager already sent the correct notification:
                #   paper LIMIT → limit_order_placed() (pending fill)
                #   live        → trade_opened() (submitted to broker)
                # Do NOT fire a second trade_opened() here to avoid duplicates.
                if False and self.notifier:  # disabled — notification handled by order_manager
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

    def _post_restore_governance_pass(self) -> None:
        """
        FIX #2 — Restart Recovery Safety Pass.

        Immediately after _restore_from_journal() restores carry positions,
        run a full governance reconciliation BEFORE the normal scheduler resumes.
        This ensures no restored position waits up to 5 minutes for its first
        SL/adaptive/carry-expiry check after a restart or crash window.

        Evaluates in order:
          1. Fetch fresh LTP via MarketDataRouter
          2. Update market context (regime + VIX from last snapshot)
          3. call check_all() — fires SL/adaptive/carry-expiry immediately
          4. Record reconciliation stats via order_manager.update_restore_stats()
          5. Telegram alert if market is open and any immediate actions fired
        """
        restored = self.order_manager.get_open_orders()
        if not restored:
            log.info("[PostRestoreGovernance] No carry positions — pass complete (clean start).")
            return

        log.info(
            "[PostRestoreGovernance] ▶ Running immediate governance pass for "
            "%d restored position(s) — evaluating SL/adaptive/carry-expiry now.",
            len(restored),
        )

        # Measure monitoring gap: time since last successful _do_monitor call.
        _gap_sec = 0
        if self._last_monitor_ts is not None:
            _gap_sec = int((datetime.now() - self._last_monitor_ts).total_seconds())
            if _gap_sec > 60:
                log.warning(
                    "[PostRestoreGovernance] Monitoring gap detected: %d sec "
                    "(%d min) — positions unmonitored during restart window.",
                    _gap_sec, _gap_sec // 60,
                )

        # Fetch live prices
        _live_pf: dict = {}
        _degraded_syms: set = set()
        try:
            from data_feeds.market_data_router import get_market_data_router
            _router  = get_market_data_router()
            _syms    = list({o.symbol for o in restored})
            _quotes  = _router.get_live_prices(_syms)
            _degraded_syms = _router.get_degraded_symbols()
            for sym, q in _quotes.items():
                if q and getattr(q, "ltp", 0) > 0:
                    _live_pf[sym] = float(q.ltp)
            log.info(
                "[PostRestoreGovernance] LTP fetch: %d/%d symbols live  degraded=%s",
                len(_live_pf), len(_syms), sorted(_degraded_syms) or "none",
            )
        except Exception as _exc:
            log.warning("[PostRestoreGovernance] LTP fetch failed: %s", _exc)

        # Update market context
        if self._last_snapshot:
            try:
                _regime_str = (
                    self._last_snapshot.regime.value
                    if hasattr(self._last_snapshot.regime, "value")
                    else str(self._last_snapshot.regime)
                )
                self.trade_monitor.update_market_context(_regime_str, self._last_snapshot.vix)
            except Exception:
                pass

        # ── Migration-era plausibility validation ─────────────────────────
        # Compare stored entry_price against current live LTP.
        # A large deviation (>50%) indicates a possible instrument mapping
        # change, corporate action (demerger/split/bonus), or stale CSV data
        # from a pre-migration session.  These are flagged as
        # RECONCILIATION_SUSPECT so they can be investigated before SL fires.
        _PLAUSIBILITY_THRESHOLD = 0.50   # 50% max acceptable deviation
        _reconciliation_suspects: list = []
        for _rec in restored:
            _entry = getattr(_rec, "entry_price", 0)
            _ltp   = _live_pf.get(_rec.symbol)
            if _ltp and _entry > 0:
                _deviation = abs(_ltp - _entry) / _entry
                if _deviation > _PLAUSIBILITY_THRESHOLD:
                    _reconciliation_suspects.append(_rec.symbol)
                    log.warning(
                        "[PostRestoreGovernance] RECONCILIATION_SUSPECT %s "
                        "entry=%.2f  ltp=%.2f  deviation=%.0f%% — "
                        "possible instrument mapping change (demerger/split?) "
                        "or stale pre-migration position.  "
                        "SL governance remains active; manual review advised.",
                        _rec.symbol, _entry, _ltp, _deviation * 100,
                    )
        if _reconciliation_suspects:
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().send_alert(
                    f"⚠️ RECONCILIATION_SUSPECT on restore: "
                    f"{_reconciliation_suspects}\n"
                    f"Entry prices deviate >50% from current LTP. "
                    f"Check for demerger/corporate action or stale CSV data."
                )
            except Exception:
                pass
        # ── End plausibility check ─────────────────────────────────────────

        # Immediate governance check
        _open_before = len(self.trade_monitor.get_open_trades())
        if _live_pf:
            try:
                self.trade_monitor.check_all(_live_pf, degraded_symbols=_degraded_syms)
                log.info("[PostRestoreGovernance] check_all complete.")
            except Exception as _ca_exc:
                log.warning("[PostRestoreGovernance] check_all error: %s", _ca_exc)
        else:
            log.warning(
                "[PostRestoreGovernance] No live prices available — "
                "SL check deferred to first scheduler monitor cycle."
            )

        # Also run carry-expiry check with live prices
        try:
            _n_expired = self.order_manager.check_and_expire_carries(_live_pf)
            if _n_expired:
                log.info(
                    "[PostRestoreGovernance] CarryExpiry: %d position(s) "
                    "expired immediately at restart.", _n_expired,
                )
        except Exception as _ce_exc:
            log.warning("[PostRestoreGovernance] CarryExpiry check failed: %s", _ce_exc)

        _open_after = len(self.trade_monitor.get_open_trades())
        _immediate_actions = _open_before - _open_after

        # Record stats
        try:
            self.order_manager.update_restore_stats(
                monitoring_gap_seconds = _gap_sec,
                reconciled_count       = len(restored),
                immediate_sl_hits      = max(0, _immediate_actions),
            )
        except Exception:
            pass

        # Telegram alert (market hours only)
        if self._is_market_session():
            try:
                from notifications.notifier_manager import get_notifier
                _lines = [
                    f"Restart governance pass: {len(restored)} position(s) checked",
                    f"Gap: {_gap_sec // 60} min  Live prices: {len(_live_pf)}/{len(restored)}",
                ]
                if _immediate_actions:
                    _lines.append(
                        f"⚠️ {_immediate_actions} position(s) acted on immediately "
                        f"(SL/expiry breach during restart window)"
                    )
                if _degraded_syms:
                    _lines.append(f"Feed degraded: {sorted(_degraded_syms)}")
                get_notifier().send_alert("\n".join(_lines))
            except Exception:
                pass

        log.info(
            "[PostRestoreGovernance] ✅ Complete — reconciled=%d  "
            "immediate_actions=%d  gap=%ds",
            len(restored), _immediate_actions, _gap_sec,
        )

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
        # ── FIX #3: Monitoring blackout detection ─────────────────────────
        _now_ts = datetime.now()
        _MONITOR_INTERVAL_SEC = 5 * 60   # expected 5-min cycle
        if self._last_monitor_ts is not None:
            _gap_sec = (_now_ts - self._last_monitor_ts).total_seconds()
            if _gap_sec > _MONITOR_INTERVAL_SEC * 2:   # > 10 min = blackout
                _open_count = len(self.trade_monitor.get_open_trades())
                log.warning(
                    "[MonitoringGap] %.0f sec gap detected (expected ≤%d sec)  "
                    "affected_positions=%d  last_monitor=%s",
                    _gap_sec, _MONITOR_INTERVAL_SEC, _open_count,
                    self._last_monitor_ts.strftime("%H:%M:%S"),
                )
                if _open_count > 0 and self._is_market_session():
                    try:
                        from notifications.notifier_manager import get_notifier
                        get_notifier().send_alert(
                            f"[MonitoringGap] {_gap_sec/60:.0f} min monitoring blackout "
                            f"during market hours. {_open_count} position(s) unmonitored.\n"
                            f"Last monitor: {self._last_monitor_ts.strftime('%H:%M:%S IST')}"
                        )
                    except Exception:
                        pass
                try:
                    self.order_manager.update_restore_stats(
                        monitoring_gap_seconds=int(_gap_sec)
                    )
                except Exception:
                    pass
        # ── End FIX #3 ────────────────────────────────────────────────────

        # Pass latest market context so adaptive exit thresholds are regime-aware
        if self._last_snapshot:
            _regime_str = (
                self._last_snapshot.regime.value
                if hasattr(self._last_snapshot.regime, "value")
                else str(self._last_snapshot.regime)
            )
            self.trade_monitor.update_market_context(_regime_str, self._last_snapshot.vix)
        # Pass live prices so check_all() evaluates real target/SL hits.
        # MarketDataRouter: Dhan-primary, Yahoo-fallback, cache-safety-net.
        # Accepts bare symbols; returns bare-keyed dict with feed_source set.
        try:
            from data_feeds.market_data_router import get_market_data_router
            _router   = get_market_data_router()
            _open_syms = list({o.symbol for o in self.trade_monitor.get_open_trades()})
            _live_pf: dict = {}
            _degraded_syms: set = set()

            if _open_syms:
                _quotes = _router.get_live_prices(_open_syms)
                _degraded_syms = _router.get_degraded_symbols()

                _INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "INDIAVIX"}
                for _bare, _q in _quotes.items():
                    if _q and getattr(_q, "ltp", 0) > 0:
                        _live_pf[_bare] = float(_q.ltp)

                # ── Feed source summary ───────────────────────────────────
                _stats = _router.get_router_stats()
                if _stats["last_source_dist"] or _degraded_syms:
                    log.info(
                        "[Monitor] Feed: %s  degraded=%s",
                        _stats["last_source_dist"],
                        sorted(_degraded_syms),
                    )

                # ── Batch sanity check ────────────────────────────────────
                # Dhan typically returns correct prices; this guard catches
                # edge-cases where a feed returns garbage for ALL symbols
                # simultaneously (e.g. yfinance errno 24 / full-batch failure).
                _INDEX_SPOT_MIN = 10_000
                _bad = 0
                for _sym, _px in list(_live_pf.items()):
                    if _sym in _INDEX_SYMBOLS:
                        if _px < _INDEX_SPOT_MIN:
                            _bad += 1
                    else:
                        if not (5.0 < _px < 50_000):
                            _bad += 1
                if _bad > 0 and _live_pf and (_bad / len(_live_pf)) > 0.5:
                    log.warning(
                        "[Monitor] Batch price sanity FAILED (%d/%d symbols invalid) "
                        "— discarding entire tick to prevent false SL/target exits.",
                        _bad, len(_live_pf),
                    )
                    _live_pf = {}
                elif _bad > 0:
                    for _sym in [s for s, p in list(_live_pf.items())
                                 if (s in _INDEX_SYMBOLS and p < _INDEX_SPOT_MIN)
                                 or (s not in _INDEX_SYMBOLS and not (5.0 < p < 50_000))]:
                        log.warning(
                            "[Monitor] Dropping corrupt price for %s: %.2f",
                            _sym, _live_pf.pop(_sym),
                        )

                # ── Feed-degraded escalation (Telegram alert at 6 cycles ≈ 30 min) ─
                _FEED_DEGRADED_ALERT_CYCLES = 6
                for _sym in list(self._feed_degraded_counts.keys()):
                    if _sym not in _degraded_syms:
                        self._feed_degraded_counts.pop(_sym, None)
                for _sym in _degraded_syms:
                    cnt = self._feed_degraded_counts.get(_sym, 0) + 1
                    self._feed_degraded_counts[_sym] = cnt
                    if cnt == _FEED_DEGRADED_ALERT_CYCLES:
                        log.warning(
                            "[Orchestrator] FEED_DEGRADED_ESCALATION %s "
                            "-- %d consecutive cycles with no live price",
                            _sym, cnt,
                        )
                        try:
                            from notifications.notifier_manager import get_notifier
                            get_notifier().send_alert(
                                f"[FEED_DEGRADED] {_sym} has had no live price "
                                f"for {cnt} consecutive monitoring cycles (~30 min). "
                                "SL monitoring suppressed. Manual review recommended."
                            )
                        except Exception:
                            pass

        except Exception as _mon_exc:
            log.warning("[Monitor] Price fetch failed: %s", _mon_exc, exc_info=True)
            _live_pf = {}
            _degraded_syms = set()

        # ── Fix options positions: replace raw spot with synthetic premium ──
        # NIFTY SELL (Bull_Call_Spread) is priced in option premium units, not
        # spot units.  Passing spot (24535) against an SL of 1729 would cause
        # an immediate false SL trigger.  Instead, compute a Black-Scholes
        # synthetic premium using live spot + India VIX as the IV proxy.
        _OPTIONS_STRATEGIES = {
            "bull_call_spread", "bear_put_spread", "iron_condor",
            "long_straddle", "short_straddle", "covered_call",
            "bull_put_spread", "bear_call_spread",
        }
        _OPT_INDICES = {"NIFTY", "BANKNIFTY", "FINNIFTY"}
        _options_fixed: dict = {}
        for _order in self.trade_monitor.get_open_trades():
            _strat_lo = (_order.strategy or "").lower().replace("_", "").replace("-", "").replace(" ", "")
            _is_opt   = any(s.replace("_", "") in _strat_lo for s in _OPTIONS_STRATEGIES)
            if _is_opt and _order.symbol in _OPT_INDICES and _order.symbol in _live_pf:
                try:
                    from data_feeds.options_feed import get_options_feed, bs_greeks as _bs_greeks
                    _spot = _live_pf[_order.symbol]   # live spot from Dhan (Yahoo fallback)
                    # Guard: NIFTY/BANKNIFTY spot below 10,000 is corrupt data
                    # (they trade ~20,000–30,000).  Skip this tick rather than
                    # computing a nonsensical premium that could trigger false exits.
                    _min_idx_spot = {"NIFTY": 10_000, "BANKNIFTY": 20_000, "FINNIFTY": 10_000}
                    if _spot < _min_idx_spot.get(_order.symbol, 10_000):
                        log.warning(
                            "[Monitor] Skipping options pricing for %s — "
                            "spot %.0f looks corrupt (min expected %.0f)",
                            _order.symbol, _spot,
                            _min_idx_spot.get(_order.symbol, 10_000),
                        )
                        continue
                    _chain = get_options_feed().get_chain(_order.symbol, dte_target=30)
                    if _chain and _chain.atm_call():
                        # The chain may be up to 5 min old (cache TTL).
                        # Recompute the ATM premium with the LIVE spot so that
                        # the premium tracks the market tick-to-tick.
                        _ivl   = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "FINNIFTY": 50.0}.get(
                                     _order.symbol, 50.0)
                        _atm_k = round(_spot / _ivl) * _ivl
                        _dte_v = max(_chain.dte, 1)
                        _iv_v  = _chain.atm_iv if _chain.atm_iv > 0 else 0.16
                        _bs    = _bs_greeks(_spot, _atm_k, _dte_v / 365.0, 0.065, _iv_v, True)
                        _syn_premium = max(_bs["price"], 0.01)
                        _options_fixed[_order.symbol] = _syn_premium
                        # Slide LTPGuard baseline BEFORE check_all so the
                        # 20%-deviation guard compares tick-to-tick movement
                        # (not entry-to-now).  Without this, options positions
                        # that move 40-60% from entry trigger the guard forever,
                        # making P&L and exit logic invisible.
                        self.trade_monitor.seed_ltp(_order.order_id, _syn_premium)
                        log.info(
                            "[Monitor] Options synthetic premium %s: %.2f "
                            "(BS live-recalc, spot=%.0f, atm_k=%.0f, iv=%.1f%%, dte=%d)",
                            _order.symbol, _syn_premium, _spot, _atm_k,
                            _iv_v * 100, _dte_v,
                        )
                except Exception as _opt_exc:
                    log.debug("[Monitor] Options pricing error for %s: %s",
                              _order.symbol, _opt_exc)
        # Merge — options synthetic prices override raw spot prices
        _live_pf.update(_options_fixed)

        # ── Pass live prices to trade monitor so SL/target use real prices ──
        if _live_pf:
            log.debug("[Monitor] Passing %d live prices to check_all: %s",
                      len(_live_pf),
                      {s: round(p, 2) for s, p in _live_pf.items()})
            _check_all_ok = False
            try:
                self.trade_monitor.check_all(_live_pf, degraded_symbols=_degraded_syms)
                _check_all_ok = True
            except Exception as _ca_exc:
                log.warning("[Monitor] check_all error: %s", _ca_exc, exc_info=True)

            # ── Deterministic carry-expiry check ──────────────────────────────
            # Carry expiry must be time-bound (every cycle) not restart-bound.
            # Passes the validated live prices so exits use real market prices.
            try:
                _n_expired = self.order_manager.check_and_expire_carries(_live_pf)
                if _n_expired:
                    log.info("[Monitor] CarryExpiry: closed %d position(s) at live LTP.", _n_expired)
            except Exception as _ce_exc:
                log.warning("[Monitor] CarryExpiry check failed: %s", _ce_exc)

            # ── Sync portfolio position LTPs from LTPGuard-validated prices ──────
            # CRITICAL: use get_resolved_prices() NOT raw _live_pf.
            # Raw feed values can be garbage at market close (e.g. all NSE stocks
            # at ~₹1000 when yfinance retries fail).  They pass the coarse batch
            # sanity check (5 < px < 50,000) but are correctly corrected by
            # LTPGuard inside check_all().  Using the validated prices here
            # prevents corrupt values from reaching portfolio.drawdown_pct and
            # triggering a false emergency_close halt.
            _validated_pf  = self.trade_monitor.get_resolved_prices() if _check_all_ok else {}
            _portfolio_obj = self.order_manager.get_portfolio()
            for _sym, _px in _validated_pf.items():
                _pos = _portfolio_obj.positions.get(_sym)
                if _pos is not None:
                    _pos.ltp = _px
                    _pos.has_live_ltp = True

        portfolio: Portfolio = self.order_manager.get_portfolio()

        # ── P0.5: Freeze drawdown halt-decision on corrupted batch ───────────
        # If LTPGuard corrected more than 50% of symbols this cycle, the entire
        # batch is suspect.  The corrected prices are already in portfolio
        # positions (updated above), so the next clean cycle starts from a good
        # state.  But we skip the halt-decision here because even the corrected
        # values may not reflect the true market accurately when a majority of
        # the feed is broken.  This prevents a false emergency_close from firing.
        _guard_corr  = self.trade_monitor.get_guard_correction_count()
        _syms_count  = len(self.trade_monitor.get_resolved_prices())
        if _guard_corr > 0 and _syms_count > 0 and (_guard_corr / _syms_count) > 0.5:
            log.warning(
                "[Monitor] ⚠ BATCH CORRUPTION FREEZE: %d/%d symbols corrected by LTPGuard "
                "— skipping drawdown halt-check this cycle to prevent false emergency_close.",
                _guard_corr, _syms_count,
            )
            self.bus.publish(RiskEvent(
                event_type=EventType.PORTFOLIO_UPDATED,
                source_agent="TradeMonitor",
                payload={"drawdown_pct": portfolio.drawdown_pct,
                         "open_positions": len(portfolio.positions),
                         "data_quality": "CORRUPTED_BATCH_FROZEN"},
            ))
            return

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

        # ── FIX #3: Record successful monitor timestamp ────────────────
        self._last_monitor_ts = _now_ts

    def run_eod_learning(self) -> None:
        """End-of-day: feed outcomes back into the Learning Engine via TaskQueue."""
        from config import is_nse_holiday
        if is_nse_holiday():
            log.info("[Orchestrator] 🏖️  NSE HOLIDAY — EOD learning skipped.")
            return
        self.bus.publish(SystemEvent(
            event_type=EventType.CYCLE_STARTED,
            source_agent="MasterOrchestrator",
            payload={"ts": datetime.now().isoformat(), "label": "eod_learning"},
        ))
        self.task_queue.submit_to(
            "LearningEngine",
            fn=self._do_eod_learning,
            priority=Priority.NORMAL,
            description="eod_learning",
        )

    def _do_eod_learning(self):
        """Internal — runs inside the LearningEngine worker thread."""
        log.info("── Layer 10: EOD Learning ──")
        trades = list(self.trade_monitor.get_closed_trades())

        # Recover any trades closed before a mid-day restart (not in in-memory
        # list because TradeMonitor._closed_orders is cleared on each startup).
        # Read today's CLOSE rows from the paper trade CSV and merge them in.
        _seen_oids = {t.order_id for t in trades}
        # ── LEARNING CLASSIFICATION INVARIANT ─────────────────────────────────
        # Every exit reason that exists in this system MUST be classified before
        # it is allowed to enter (or be blocked from) the learning pipeline.
        #
        # Classification rule — ask these three questions for every new reason:
        #
        #   (A) Strategy decision?    → INCLUDE  (real price, real outcome)
        #   (B) System intervention?  → EXCLUDE  (not a strategy outcome)
        #   (C) Data repair?          → EXCLUDE  (corrupted or synthetic data)
        #
        # WHY: Silent misclassification → AI learns wrong behaviour → all
        # downstream metrics degrade without any visible error. There is no
        # safety net below this filter.
        #
        # Current classification:
        #
        #   INCLUDE (A — strategy decisions at real market price):
        #     close_target    — target hit
        #     close_sl        — stop-loss hit
        #     adaptive_exit   — EARLY_LOSS / TIME_STALE / TIME_CAP exits
        #
        #   EXCLUDE (B — system intervention, price may be synthetic):
        #     emergency_close     — system halt; exit recorded @ entry_price (pnl=0)
        #     close_emergency     — TradeMonitor MAE guard; risk-engine intervened
        #     SESSION_EXPIRED     — broker auto-squared MIS position at EOD
        #     SESSION_EXPIRED_EXTENDED — same, for extended carry positions
        #     REPLACEMENT         — smart-swap leg; not a standalone trade decision
        #
        #   EXCLUDE (C — data repair):
        #     SYSTEM_CLEANUP      — cleanup_stale_opens.py manual repair
        #
        #   PENDING CLASSIFICATION (wired up = reclassify):
        #     close_eod  — currently dead code (nothing dispatches it).
        #                  If wired as strategy max-hold at real LTP → (A) INCLUDE
        #                  If wired as forced 15:30 system flatten     → (B) EXCLUDE
        # ──────────────────────────────────────────────────────────────────────
        _skip_reasons = {
            # (B) system interventions — synthetic or broker-forced exits
            # NOTE: SESSION_EXPIRED / SESSION_EXPIRED_EXTENDED are excluded here
            # because they have two sub-cases handled below:
            #   pnl == 0  → no real LTP obtained → skip (synthetic exit, no signal)
            #   pnl != 0  → real LTP fetched     → INCLUDE (genuine carry-limit outcome)
            "REPLACEMENT",
            "emergency_close",         # system halt → exit @ entry_price (synthetic pnl)
            "close_emergency",         # TradeMonitor MAE — risk-engine intervention
            # (C) data repair
            "SYSTEM_CLEANUP",
        }
        _session_expired_reasons = {"SESSION_EXPIRED", "SESSION_EXPIRED_EXTENDED"}
        try:
            import csv as _csv
            from execution_engine.order_manager import PAPER_TRADE_LOG
            _today = datetime.now().strftime("%Y-%m-%d")
            if os.path.exists(PAPER_TRADE_LOG):
                with open(PAPER_TRADE_LOG, newline="", encoding="utf-8") as _fh:
                    for _row in _csv.DictReader(_fh):
                        if not _row.get("timestamp", "").startswith(_today):
                            continue
                        if _row.get("event", "").upper() != "CLOSE":
                            continue
                        _oid = _row.get("order_id", "").strip()
                        if not _oid or _oid in _seen_oids:
                            continue
                        _reason = _row.get("reason", "")
                        if _reason in _skip_reasons:
                            continue
                        # SESSION_EXPIRED with real LTP → include in learning.
                        # SESSION_EXPIRED with pnl=0    → skip (no real price data).
                        if _reason in _session_expired_reasons:
                            try:
                                _se_pnl = float(_row.get("pnl", 0) or 0)
                            except (ValueError, TypeError):
                                _se_pnl = 0.0
                            if _se_pnl == 0.0:
                                log.info(
                                    "[LearningSkip] SESSION_EXPIRED skipped (zero pnl): "
                                    "%s %s strategy=%s",
                                    _row.get("symbol", ""), _oid, _row.get("strategy", ""),
                                )
                                continue  # synthetic ₹0 exit — no signal value
                            log.info(
                                "[LearningInclude] SESSION_EXPIRED accepted (real pnl): "
                                "%s %s strategy=%s pnl=₹%+.0f",
                                _row.get("symbol", ""), _oid, _row.get("strategy", ""), _se_pnl,
                            )
                        try:
                            _entry = float(_row.get("entry_price", 0) or 0)
                            _exit  = float(_row.get("exit_price",  0) or 0)
                            _qty   = int(float(_row.get("quantity",  1) or 1))
                            _pnl   = float(_row.get("pnl", 0) or 0)
                            _sl    = float(_row.get("stop_loss", 0) or 0)
                            _r_risk = abs(_entry - _sl) if _sl else 1.0
                            _r_mult = _pnl / (_r_risk * _qty) if _r_risk * _qty else 0.0
                            from execution_engine.order_manager import OrderRecord
                            _rec = OrderRecord(
                                order_id    = _oid,
                                symbol      = _row.get("symbol", ""),
                                direction   = _row.get("direction", "BUY"),
                                quantity    = _qty,
                                entry_price = _entry,
                                stop_loss   = _sl,
                                target      = float(_row.get("target", 0) or 0),
                                strategy    = _row.get("strategy", ""),
                                status      = "closed",
                                order_type  = "MARKET",
                                placed_at   = datetime.now(),
                            )
                            _rec.pnl        = _pnl
                            _rec.r_multiple = _r_mult
                            _seen_oids.add(_oid)
                            trades.append(_rec)
                            log.info(
                                "[EOD-Learn] Recovered CSV-closed trade: %s %s pnl=₹%s",
                                _oid, _row.get("symbol", ""), f"{_pnl:+,.0f}",
                            )
                        except Exception as _row_exc:
                            log.debug("[EOD-Learn] Skipping malformed close row %s: %s",
                                      _oid, _row_exc)
        except Exception as _csv_exc:
            log.warning("[EOD-Learn] Could not recover CSV trades: %s", _csv_exc)

        if not trades:
            log.info("[EOD-Learn] No closed trades today — learning skipped.")
        else:
            log.info("[EOD-Learn] Processing %d closed trade(s) (in-memory + CSV).", len(trades))
        self.learning_engine.learn(trades)

        self.bus.publish(LearningEvent(
            event_type=EventType.LEARNING_CYCLE_COMPLETE,
            source_agent="LearningEngine",
            payload={"trades_processed": len(trades)},
        ))

        # ── Performance Evaluation ──────────────────────────────────
        log.info("── Layer 11: Performance Evaluation ──")
        for trade in trades:
            # OrderRecord uses .strategy; fall back to .strategy_name for compat
            strategy   = getattr(trade, "strategy", None) or getattr(trade, "strategy_name", "unknown")
            regime     = getattr(trade, "signal_regime", None) or getattr(trade, "regime", "unknown")
            pnl        = getattr(trade, "pnl",           0.0)
            r_multiple = getattr(trade, "r_multiple",    0.0)
            won        = pnl > 0
            self.performance_evaluator.record_trade(
                strategy=strategy, regime=regime,
                pnl=pnl, r_multiple=r_multiple, won=won,
            )
            # ── Q3: Strategy Performance Tracker (win rate, auto-disable) ──
            # Pass order_id so LearningGate can filter LEGACY_UNVERIFIED trades.
            _oid = getattr(trade, "order_id", "")
            self.perf_tracker.record_trade(strategy, pnl_r=r_multiple, order_id=_oid)
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
                strategy   = getattr(trade, "strategy", None) or getattr(trade, "strategy_name", "unknown"),
                snapshot   = None,    # uses cached last_snapshot
                r_multiple = getattr(trade, "r_multiple",    0.0),
                return_pct = getattr(trade, "pnl",           0.0) / 1_000_000 * 100,
                won        = getattr(trade, "pnl",           0.0) > 0,
            )
        self.meta_learning.retrain_if_due()

        # ── Validation Engine (runs when enough trade history exists) ──
        # INTEGRITY RULE: gate on cumulative *official* trades, not session count.
        # A single day with 30+ intraday trades must not unlock optimisation.
        log.info("── Layer 12: Strategy Validation ──")
        all_pnls = [getattr(t, "pnl", 0.0) for t in trades]
        _total_official = sum(
            s.official_trades for s in self.perf_tracker.get_all_stats().values()
        )
        if _total_official >= 30:
            self.validation_engine.validate(
                strategy_name="Portfolio",
                pnl_series=all_pnls,
                capital=TOTAL_CAPITAL,
                print_report=True,
            )
        else:
            log.info("[ValidationEngine] Only %d official trades — need 30+ to validate.",
                     _total_official)

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
        # Pre-fetch stability + official-trade counts for the EOD header
        _stab_streak   = 0
        _stab_required = 10
        _off_trades    = 0
        _off_target    = 30
        try:
            from learning_system.strategy_performance_tracker import (
                get_stability_ledger as _get_sl,
                get_performance_tracker as _get_pt,
            )
            _sl = _get_sl()
            _stab_streak   = _sl.streak
            _stab_required = _sl.required
            _off_trades    = sum(
                s.official_trades for s in _get_pt().get_all_stats().values()
            )
        except Exception:
            pass
        if self.notifier:
            self.notifier.eod_summary(
                len(trades), wins, losses, total_pnl, TOTAL_CAPITAL,
                stability_streak=_stab_streak,
                stability_required=_stab_required,
                official_trades=_off_trades,
                official_target=_off_target,
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
            _pilot_cap = getattr(_cfg_eod, "TOTAL_CAPITAL", 1_000_000)
            _eod_date  = datetime.now().strftime("%Y-%m-%d")
            _nifty_eod = 0.0
            try:
                from data_feeds import get_feed_manager as _gfm_eod
                _q_eod = _gfm_eod().get_quote("NIFTY")
                if _q_eod and getattr(_q_eod, "ltp", None):
                    _nifty_eod = float(_q_eod.ltp)
            except Exception:
                pass
            _csv_path  = _pl.Path("data/paper_trades.csv")
            _open_trades, _closed_trades = [], []
            if _csv_path.exists():
                with open(_csv_path, newline="", encoding="utf-8") as _fh:
                    for _row in _csv.DictReader(_fh):
                        (_closed_trades if _row.get("event","").upper() == "CLOSED"
                         else _open_trades).append(_row)
            # Only count TODAY's in-memory open orders (not stale CSV rows from
            # previous sessions whose in-memory state was lost on restart)
            _live_open_count = len(self.order_manager.get_open_orders()) if self.order_manager else len(_open_trades)
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
                    "open_trades":   _live_open_count,
                    "cum_pnl":       round(_cum_pnl, 2),
                    "cum_return_pct": round(_cum_pnl / _pilot_cap * 100, 3) if _pilot_cap else 0,
                },
                "pilot_capital": _pilot_cap,
                "nifty_ltp":     _nifty_eod,
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

        # ── Operational Retrospective (cycle health, funnel, ODM, flags) ───
        log.info("── EOD Operational Retrospective ──")
        try:
            from learning_system.eod_retrospective import run_eod_retrospective
            _retro_plain, _retro_html = run_eod_retrospective()
            if self.notifier:
                self.notifier.market_alert("📊 Daily Retrospective", _retro_html)
            log.info("[EOD-Retro] Operational retrospective sent.")
        except Exception as _retro_exc:
            log.warning("[EOD-Retro] Retrospective failed: %s", _retro_exc)

        # ── Performance Analytics Layer ────────────────────────────────────
        log.info("── EOD Performance Analytics ──")
        try:
            analytics = self.trade_monitor.get_analytics()
            if analytics.trade_count() > 0:
                _perf_plain = analytics.daily_report()
                _perf_tg    = analytics.telegram_report()
                log.info("\n%s", _perf_plain)
                if self.notifier:
                    self.notifier.market_alert("📊 AI Performance Report", _perf_tg)
                log.info("[TradeAnalytics] Performance report sent (%d trades).",
                         analytics.trade_count())
            else:
                log.info("[TradeAnalytics] No trades today — report suppressed.")
        except Exception as _pa_exc:
            log.warning("[TradeAnalytics] EOD report failed: %s", _pa_exc)

        # ── Stability Ledger (two-ledger baseline confirmation) ────────────
        try:
            from learning_system.strategy_performance_tracker import get_stability_ledger
            _stability = get_stability_ledger()
            _sess_result = _stability.close_session()
            log.info("[EOD] %s", _stability.status_summary())
            if self.notifier:
                self.notifier.market_alert(
                    "📊 Stability Check",
                    _stability.status_summary(),
                )
        except Exception as _stab_exc:
            log.warning("[EOD] Stability ledger update failed: %s", _stab_exc)

        # ── SHM Cooldown Tick — advance disabled-strategy session counter ──
        try:
            self.strategy_health.tick_session()
            log.info("[EOD] SHM session tick complete.")
        except Exception as _shm_tick_exc:
            log.warning("[EOD] SHM tick_session failed: %s", _shm_tick_exc)

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
        Returns True only during NSE trading hours on weekdays that are not
        public holidays. Prevents the scheduler from firing full cycles on
        weekends, overnight hours, or NSE holidays.
        """
        from config import is_nse_holiday
        now = datetime.now()
        if now.weekday() >= 5:          # Saturday=5, Sunday=6
            return False
        if is_nse_holiday(now.date()):  # NSE public holiday
            return False
        # Container runs in IST (Asia/Kolkata). NSE hours: 09:15–15:30 IST
        market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=32, second=0, microsecond=0)
        return market_open <= now <= market_close

    def _premarket_init(self) -> None:
        """
        Pre-market initialization — runs at 08:00.
        Warms caches, validates data feeds, and notifies via Telegram.
        Skipped on NSE holidays.
        """
        from config import is_nse_holiday
        if is_nse_holiday():
            log.info("[Orchestrator] 🏖️  NSE HOLIDAY — pre-market init skipped.")
            return
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
            _nifty = self._get_nifty_str()
            _body = (
                f"Date: {now_str}\n"
                f"Mode: {_mode} | Capital: ₹{getattr(_cfg, 'TOTAL_CAPITAL', 1_000_000):,.0f}\n"
                f"{_nifty}\n"
                f"First scan: 09:05 | Full cycles: 09:45 / 10:30 / 11:30 / 13:00 / 14:00 / 15:00\n"
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

    def _get_nifty_str(self) -> str:
        """Return current NIFTY LTP formatted for Telegram messages (or 'NIFTY: N/A')."""
        try:
            from data_feeds import get_feed_manager
            q = get_feed_manager().get_quote("NIFTY")
            if q and getattr(q, "ltp", None):
                return f"NIFTY: ₹{float(q.ltp):,.2f}"
        except Exception:
            pass
        return "NIFTY: N/A"

    def _market_open_notify(self) -> None:
        """Send Telegram notification when NSE market opens at 09:15."""
        from config import is_nse_holiday
        if is_nse_holiday():
            log.info("[Orchestrator] 🏖️  NSE HOLIDAY — market-open notify skipped.")
            return
        log.info("[Orchestrator] 🔔 Market OPEN — 09:15 notification")
        try:
            from notifications import get_notifier
            import config as _cfg
            n = get_notifier()
            _mode = "🧪 Paper" if getattr(_cfg, "PAPER_TRADING", False) else "💵 Live"
            _nifty = self._get_nifty_str()
            n.market_alert(
                "🟢 Market OPEN — Trading Started",
                f"NSE/BSE opened at 09:15\n"
                f"Mode: {_mode}\n"
                f"{_nifty}\n"
                f"First full cycle: 09:45\n"
                f"Scanning every 30 seconds for opportunities.",
            )
        except Exception as exc:
            log.debug("Telegram market-open notify failed: %s", exc)

    def _market_close_notify(self) -> None:
        """
        Called at 15:30 IST when NSE market closes.

        EOD RISK MANAGEMENT (not a force-flush):
        - This system is NOT purely intraday.  Positions with strong momentum
          or overnight thesis should be allowed to carry.
        - Action is risk-aware: only log position state for next-session awareness.
        - AdaptiveExitEngine (time/loss gates) handles intraday stale positions
          during the day.  Nothing is force-closed here.

        Sends Telegram market-close notification.
        """
        from config import is_nse_holiday
        if is_nse_holiday():
            log.info("[Orchestrator] 🏖️  NSE HOLIDAY — market-close notify skipped.")
            return
        log.info("[Orchestrator] 🔔 Market CLOSE — 15:30 notification")

        # ── EOD risk summary (no forced close) ────────────────────────────
        # Log the state of every open position so the next session starts
        # with full awareness.  The AdaptiveExitEngine already cleared
        # genuinely stale/stopped positions during the day.
        try:
            open_orders = self.order_manager.get_open_orders()
            if open_orders:
                log.info("[Orchestrator] EOD state — %d position(s) carrying to next session:",
                         len(open_orders))
                for rec in open_orders:
                    try:
                        from data_feeds import get_feed_manager as _gfm
                        _IDX = {"NIFTY", "BANKNIFTY", "INDIAVIX"}
                        _sym = rec.symbol if rec.symbol in _IDX else f"{rec.symbol}.NS"
                        q = _gfm().get_quote(_sym)
                        ltp = q.ltp if (q and q.ltp and q.ltp > 0) else rec.entry_price
                    except Exception:
                        ltp = rec.entry_price
                    risk   = abs(rec.entry_price - rec.stop_loss) if rec.stop_loss else 0
                    r_mult = (ltp - rec.entry_price) / risk if (risk > 0 and rec.direction == "BUY") \
                              else (rec.entry_price - ltp) / risk if risk > 0 else 0
                    log.info(
                        "[Orchestrator]   CARRY  %s %s  entry=%.2f  ltp=%.2f  "
                        "sl=%.2f  r_mult=%.2fR  strategy=%s",
                        rec.symbol, rec.direction, rec.entry_price, ltp,
                        rec.stop_loss or 0, r_mult, rec.strategy,
                    )
            else:
                log.info("[Orchestrator] EOD — no open positions. Clean session end.")
        except Exception as eod_exc:
            log.warning("[Orchestrator] EOD position state read failed: %s", eod_exc)
        try:
            from notifications import get_notifier
            import config as _cfg
            n = get_notifier()
            _mode = "🧪 Paper" if getattr(_cfg, "PAPER_TRADING", False) else "💵 Live"
            # Gather quick P&L summary from paper journal if available
            summary = ""
            try:
                import csv, os
                journal = os.path.join(os.path.dirname(__file__), "..", "data", "paper_trades.csv")
                if os.path.exists(journal):
                    with open(journal, newline="", encoding="utf-8") as f:
                        rows = list(csv.DictReader(f))
                    today = datetime.now().strftime("%Y-%m-%d")
                    today_rows = [r for r in rows if r.get("timestamp", "").startswith(today)]
                    if today_rows:
                        summary = f"\nTrades today: {len(today_rows)}"
            except Exception:
                pass
            _nifty = self._get_nifty_str()
            n.market_alert(
                "🔴 Market CLOSED — Session Ended",
                f"NSE/BSE closed at 15:30\n"
                f"Mode: {_mode}{summary}\n"
                f"{_nifty}\n"
                f"EOD learning & report will run at 15:35.",
            )
        except Exception as exc:
            log.debug("Telegram market-close notify failed: %s", exc)

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
          • 09:45 / 10:30 / 11:30 / 13:00 / 14:00 / 15:00 — full analysis cycles
          • 15:35  — EOD learning cycle
          • Every 5 min — open-position monitor (market hours only)

        Continuous 30-second light scan is handled by MarketMonitor in its
        own background thread (started by _start_monitor below).
        """
        import schedule as sched_lib   # pip install schedule

        # ── Startup ping — immediate Telegram on service boot ──────────
        try:
            from notifications import get_notifier
            import config as _cfg
            _mode = "🧪 Paper" if getattr(_cfg, "PAPER_TRADING", False) else "💵 Live"
            _nifty = self._get_nifty_str()
            # Restore integrity snapshot for startup ping
            _rs_ping = ""
            try:
                rs = self.order_manager.get_restore_stats()
                total_r = rs.get("restored_carry", 0)
                orphan  = rs.get("orphan_monitored_count", 0)
                expired = rs.get("expired_at_restore", 0)
                if total_r or orphan or expired:
                    _rs_ping = (
                        f"\nRestore: carry={total_r} orphan_watch={orphan} "
                        f"session_expired={expired}"
                    )
            except Exception:
                pass
            get_notifier().market_alert(
                "🚀 AI Trading Brain Started",
                f"System is ONLINE on cloud server\n"
                f"Date: {datetime.now().strftime('%d %b %Y, %H:%M IST')}\n"
                f"Mode: {_mode}\n"
                f"{_nifty}{_rs_ping}\n"
                f"Schedule: 08:00 pre-market → 09:15 open → 09:45/10:30/11:30/13:00/14:00/15:00 cycles → 15:30 close → 15:35 EOD\n"
                f"Dashboard: http://178.18.252.24:8501",
            )
        except Exception as exc:
            log.debug("Telegram startup ping failed: %s", exc)

        # ── Start continuous monitoring thread (30s light scan) ────────
        self._start_monitor()

        # ── Post-restore governance pass ────────────────────────────────
        # Immediately evaluate SL/adaptive/carry-expiry for all restored
        # positions BEFORE the normal scheduler begins.  Any SL breach or
        # carry limit that occurred during the restart window is caught here
        # rather than waiting up to 5 minutes for the first monitor cycle.
        self._post_restore_governance_pass()

        # ── Pre-market ─────────────────────────────────────────────────
        sched_lib.every().day.at("08:00").do(self._premarket_init)
        sched_lib.every().day.at("08:30").do(self._premarket_data_warmup)

        # ── Intraday full-cycle slots ───────────────────────────────────
        # 09:45  first trade decision window
        sched_lib.every().day.at(SCHEDULE["trade_decision"]).do(self._guarded_cycle)
        # 10:30  mid-morning re-scan
        sched_lib.every().day.at(SCHEDULE["mid_morning_scan"]).do(self._guarded_cycle)
        # 11:30  post-circuit / momentum phase
        sched_lib.every().day.at(SCHEDULE["mid_session_scan"]).do(self._guarded_cycle)
        # 13:00  afternoon session
        sched_lib.every().day.at(SCHEDULE["afternoon_scan"]).do(self._guarded_cycle)
        # 14:00  afternoon momentum window
        sched_lib.every().day.at(SCHEDULE["early_afternoon_scan"]).do(self._guarded_cycle)
        # 15:00  pre-expiry / closing trades
        sched_lib.every().day.at(SCHEDULE["closing_analysis"]).do(self._guarded_cycle)

        # ── Market open / close notifications ─────────────────────────
        sched_lib.every().day.at("09:15").do(self._market_open_notify)
        sched_lib.every().day.at("15:30").do(self._market_close_notify)  # 15:30 IST = NSE close

        # ── EOD learning ───────────────────────────────────────────────
        sched_lib.every().day.at(SCHEDULE["eod_learning"]).do(self.run_eod_learning)

        # ── Position monitor (every 5 min, market hours only) ──────────
        sched_lib.every(5).minutes.do(
            lambda: self.monitor_open_positions()
            if self._is_market_session() else None
        )

        log.info("[Orchestrator] Scheduler armed.")
        log.info("  Pre-market : 08:00 init | 08:30 data warm-up")
        log.info("  Deep scans : 09:05 / 09:10 / 09:20  (MarketMonitor — opening window only)")
        log.info("  Full cycle : 09:45 / 10:30 / 11:30 / 13:00 / 14:00 / 15:00")
        log.info("  EOD        : 15:35")
        log.info("  Monitoring : every 5 min  |  Light scan: every 30s")

        self.bus.publish(SystemEvent(
            event_type=EventType.SYSTEM_STARTUP,
            source_agent="MasterOrchestrator",
            payload={"ts": datetime.now().isoformat()},
        ))

        def _run(_stop_event: threading.Event):
            _heartbeat_counter = 0
            log.info("[Scheduler] SYSTEM LOOP ACTIVE — 15s resolution")
            while not self._halt:
                try:
                    sched_lib.run_pending()
                except Exception as _exc:
                    log.error("[Scheduler] Exception in run_pending — continuing: %s", _exc)
                _heartbeat_counter += 1
                # Log heartbeat + publish event every 5 min (20 × 15s)
                if _heartbeat_counter >= 20:
                    _heartbeat_counter = 0
                    log.info("[Scheduler] SYSTEM LOOP ACTIVE — heartbeat OK")
                    try:
                        self.bus.publish(SystemEvent(
                            event_type=EventType.SYSTEM_HEARTBEAT,
                            source_agent="MasterOrchestrator",
                            payload={"ts": datetime.now().isoformat(), "uptime": "ok"},
                        ))
                    except Exception:
                        pass
                time.sleep(15)   # 15s resolution gives < 15s slot jitter
            # _halt was set (kill-switch / drawdown breach) — signal main to exit
            # so the container can be restarted cleanly by Docker/systemd.
            log.critical("[Scheduler] _halt=True — scheduler loop exited. Signalling main thread.")
            _stop_event.set()

        # _stop_event is injected after signal handlers are registered in main.py;
        # use a placeholder Event here — main.py will replace it via set_stop_event().
        self._main_stop_event = threading.Event()

        t = threading.Thread(
            target=_run,
            args=(self._main_stop_event,),
            daemon=True,
            name="Scheduler",
        )
        t.start()
        log.info("[Orchestrator] Scheduler thread running (15s resolution).")

    def set_stop_event(self, stop_event: threading.Event) -> None:
        """Let main.py inject the real stop Event so halt propagates to the main loop."""
        self._main_stop_event = stop_event

    def shutdown(self):
        """Gracefully shut down the task queue and publish SYSTEM_SHUTDOWN event."""
        log.info("Shutting down AI Trading Brain…")
        self.bus.publish(SystemEvent(
            event_type=EventType.SYSTEM_SHUTDOWN,
            source_agent="MasterOrchestrator",
            payload={"ts": datetime.now().isoformat()},
        ))
        self.task_queue.shutdown(timeout=5.0)
