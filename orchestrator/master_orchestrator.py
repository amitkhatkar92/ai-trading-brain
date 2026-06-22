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
from system_monitor.trade_blocker_report    import TradeDiagnosticEngine
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
# ── Weekend Intelligence ──────────────────────────────────────────────
from orchestrator.weekend_intelligence import WeekendIntelligenceEngine

from communication import (
    EventType, MarketEvent, OpportunityEvent, RiskEvent,
    DecisionEvent, ExecutionEvent, LearningEvent, SystemEvent,
    Priority,
)

log = get_logger(__name__)

# ── Daily replacement audit accumulator (reset at midnight) ───────────────
_REPLACEMENT_DAILY_AUDIT: List[dict] = []
_REPLACEMENT_DAILY_DATE: str = ""

def _reset_replacement_accumulator() -> None:
    global _REPLACEMENT_DAILY_AUDIT, _REPLACEMENT_DAILY_DATE
    today = datetime.now().strftime("%Y-%m-%d")
    if _REPLACEMENT_DAILY_DATE != today:
        _REPLACEMENT_DAILY_AUDIT = []
        _REPLACEMENT_DAILY_DATE  = today

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


# Module-level accessor — set by MasterOrchestrator.__init__(); used by
# Telegram bot to reach order_manager and cycle reports without creating
# a second orchestrator instance.
_ORCH_INSTANCE: "Optional[MasterOrchestrator]" = None


def get_orchestrator() -> "Optional[MasterOrchestrator]":
    """Return the running MasterOrchestrator instance (None before first init)."""
    return _ORCH_INSTANCE


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
        # ── Cycle diagnostic state (set by sub-methods, read at cycle end) ──
        self._last_sl_reject_summary: dict = {}
        self._last_rc_reject_summary: dict = {}
        self._last_options_placed: int = 0
        self._last_oqg_summary: dict = {}

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
        # ── Weekend Intelligence Engine ───────────────────────────────
        self.weekend_intelligence = WeekendIntelligenceEngine(orchestrator=self)
        # Cache last snapshot so the EOD learning cycle can run EDE
        self._last_snapshot: Optional[MarketSnapshot] = None
        # Last completed cycle report — read by Telegram /cycle command
        self._last_cycle_report: dict = {}
        # Feed-degraded escalation counter (symbol → consecutive degraded cycles)
        self._feed_degraded_counts: dict = {}
        # Monitoring continuity: tracks last successful _do_monitor execution.
        # Used by FIX #3 blackout detection to emit [MonitoringGap] warnings.
        self._last_monitor_ts: Optional[datetime] = None
        # Counts cycles where open positions existed but the price feed was empty.
        # Incremented in _do_monitor; reset to 0 on any successful check_all().
        self._missed_monitor_cycles: int = 0

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

        # Phase 1 — [RuntimeImportAudit]: prove exact files executing after restart
        try:
            import inspect as _inspect
            import learning_system.daily_self_evaluation as _dse_mod
            import trade_monitoring.trade_analytics       as _ta_mod
            import learning_system.eod_retrospective      as _retro_mod
            log.info(
                "[RuntimeImportAudit] daily_self_evaluation=%s "
                "trade_analytics=%s eod_retrospective=%s pid=%d",
                os.path.abspath(_inspect.getfile(_dse_mod.DailyAISelfEvaluator)),
                os.path.abspath(_inspect.getfile(_ta_mod.TradeAnalytics)),
                os.path.abspath(_inspect.getfile(_retro_mod.EODRetrospective))
                    if hasattr(_retro_mod, "EODRetrospective")
                    else _retro_mod.__file__,
                os.getpid(),
            )
        except Exception as _ria_exc:
            log.warning("[RuntimeImportAudit] FAILED: %s", _ria_exc)

        # Register as the global singleton (for Telegram bot access)
        global _ORCH_INSTANCE
        _ORCH_INSTANCE = self

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

        # ── Wire OIOS execution feedback bridge (shadow-safe, fire-and-forget) ──
        try:
            from oios.execution_bridge import get_execution_bridge
            self._oios_exec_bridge = get_execution_bridge()
            self._oios_exec_bridge.subscribe(self.bus)
            log.info("[EDA] OIOS execution feedback bridge wired.")
        except Exception as _bridge_exc:
            log.warning("[EDA] OIOS execution bridge not loaded: %s", _bridge_exc)

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
            from data_feeds import get_feed_manager
            self.market_monitor._feed = get_feed_manager().dhan  # reuse singleton DhanFeed
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
                # ── Layer 1: ExecutionWindowGuard ─────────────────────────
                # The deep-scan path bypasses _guarded_cycle and calls
                # run_full_cycle directly via the task queue.  Guard here
                # so no full cycle (and therefore no order placement) is
                # submitted before the 09:45 execution window opens.
                _now_scan = datetime.now()
                _scan_win = _now_scan.replace(hour=9, minute=45, second=0, microsecond=0)
                if _now_scan < _scan_win:
                    _mins = int((_scan_win - _now_scan).total_seconds() / 60)
                    log.info(
                        "[ExecWindowGuard] L1 deep_scan=%s suppressed at %s — "
                        "execution window opens 09:45 (%d min remaining).",
                        actual_name, _now_scan.strftime("%H:%M:%S"), _mins,
                    )
                    return
                # ── end Layer 1 ───────────────────────────────────────────
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
            log.info("[GlobalAbortCause] cause=self._halt cycle_skipped=True")
            return

        # ── Layer 2: ExecutionWindowGuard ─────────────────────────────────
        # Defence-in-depth: catch any call path that bypassed Layer 1.
        # run_full_cycle() must never execute before 09:45 IST.
        _rfc_now = datetime.now()
        _rfc_win = _rfc_now.replace(hour=9, minute=45, second=0, microsecond=0)
        if _rfc_now < _rfc_win:
            _rfc_mins = int((_rfc_win - _rfc_now).total_seconds() / 60)
            log.info(
                "[ExecWindowGuard] L2 run_full_cycle suppressed at %s — "
                "execution window opens 09:45 (%d min remaining).",
                _rfc_now.strftime("%H:%M:%S"), _rfc_mins,
            )
            log.info("[GlobalAbortCause] cause=exec_window_not_open cycle_skipped=True")
            return
        # ── end Layer 2 ───────────────────────────────────────────────────

        # ── Emergency Kill Switch Check ──────────────────────────────────
        if not is_trading_enabled():
            status = get_kill_switch_status()
            log.critical(
                "🚨 EMERGENCY KILL SWITCH ACTIVE — Trading disabled. Reason: %s",
                status.get("reason", "Unknown")
            )
            log.info("[GlobalAbortCause] cause=kill_switch reason=%s cycle_skipped=True",
                     status.get("reason", "Unknown"))
            return

        log.info("▶ Starting full analysis cycle — %s",
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.system_monitor.start_cycle()

        # ── Observability: CandidateFreshnessAudit ────────────────────────
        try:
            import json as _json_cfa
            from pathlib import Path as _Path_cfa
            from datetime import datetime as _dt_cfa, date as _date_cfa
            _cfa_today  = _date_cfa.today().isoformat()
            _cfa_path   = _Path_cfa("data/daily_candidates.json")
            _cfa_n      = 0
            _cfa_fresh  = False
            _cfa_stale_n = 0
            _cfa_ttl_h  = 0.0
            if _cfa_path.exists():
                try:
                    _cfa_data = _json_cfa.loads(_cfa_path.read_text(encoding="utf-8"))
                    _cfa_cands = _cfa_data.get("candidates", [])
                    _cfa_n    = len(_cfa_cands)
                    _cfa_mtime = _cfa_path.stat().st_mtime
                    _cfa_fresh = _date_cfa.fromtimestamp(_cfa_mtime).isoformat() == _cfa_today
                    _now_ts   = _dt_cfa.now().timestamp()
                    for _c in _cfa_cands:
                        _vu = _c.get("valid_until_utc") or _c.get("expires_at")
                        if _vu:
                            try:
                                import time as _time_cfa
                                _exp = _dt_cfa.fromisoformat(_vu.replace("Z", "+00:00")).timestamp()
                                if _exp < _now_ts:
                                    _cfa_stale_n += 1
                            except Exception:
                                pass
                except Exception:
                    pass
            log.info(
                "[CandidateFreshnessAudit] date=%s candidates=%d fresh=%s stale_count=%d",
                _cfa_today, _cfa_n, _cfa_fresh, _cfa_stale_n,
            )
        except Exception as _cfa_exc:
            log.debug("[CandidateFreshnessAudit] skipped: %s", _cfa_exc)

        # V2.5: Shadow audit — fire-and-forget, never delays the cycle
        try:
            from opportunity_engine.delta_refresh_shadow import run_shadow_audit as _rsa
            _rsa(datetime.now().strftime("%H%M"))
        except Exception:
            pass

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
        _diag = TradeDiagnosticEngine()  # observability only — no pipeline effect
        odm_directive = self.odm.get_directive(snapshot)
        if odm_directive.tier != "NORMAL":
            log.info("[ODM] %s", odm_directive.message)
        with self.system_monitor.time_layer("OpportunityEngine"):
            signals: List[TradeSignal] = self._run_opportunity_engine(snapshot, odm_directive)
        if not signals:
            log.info("No opportunities found this cycle.")
            _diag.record_stage("OpportunityEngine", 0, 0, "NO_ENTRY_CONDITIONS_MET")
            _diag.set_totals(0, 0)
            _diag.generate()
            self.odm.record_cycle(signals_generated=0, approved_trades=0)
            self.system_monitor.finalize_cycle()
            return

        # ── STEP 3: Strategy Evaluation ──────────────────────────────
        with self.system_monitor.time_layer("StrategyLab"):
            enriched_signals = self._run_strategy_lab(signals, snapshot)
        if self._abort_if_timed_out("StrategyLab"): return
        _sl_reasons = getattr(self, '_last_sl_reject_summary', {})
        _sl_top = max(_sl_reasons, key=_sl_reasons.get, default="UNKNOWN") if _sl_reasons else "OK"
        _diag.record_stage("StrategyLab", len(signals), len(enriched_signals), _sl_top)

        # ── STEP 3.5: Capital Risk Engine ────────────────────────────
        with self.system_monitor.time_layer("CapitalRiskEngine"):
            portfolio = self.order_manager.get_portfolio()
            cre_signals = self.capital_risk_engine.allocate(
                enriched_signals, snapshot, portfolio
            )
        _diag.record_stage("CapitalRiskEngine", len(enriched_signals), len(cre_signals))

        # ── [PortfolioCapacityAudit] — slot utilization ───────────────────
        try:
            from risk_control.capital_risk_engine import _MAX_POSITIONS as _CRE_MAX
            _pca_positions   = list(portfolio.positions.values()) if portfolio else []
            _pca_n_open      = len(_pca_positions)
            _pca_now         = datetime.now()
            _pca_profitable  = sum(1 for p in _pca_positions if p.unrealised_pnl > 0)
            _pca_losing      = sum(1 for p in _pca_positions if p.unrealised_pnl < 0)
            _pca_stale       = sum(1 for p in _pca_positions if not p.has_live_ltp)
            _pca_over2d      = sum(
                1 for p in _pca_positions
                if (_pca_now - p.entry_time).total_seconds() >= 2 * 86400
            )
            _pca_over3d      = sum(
                1 for p in _pca_positions
                if (_pca_now - p.entry_time).total_seconds() >= 3 * 86400
            )
            _pca_slots_avail = max(0, _CRE_MAX - _pca_n_open)
            _pca_blocked     = _pca_n_open >= _CRE_MAX
            log.info(
                "[PortfolioCapacityAudit] max_positions=%d positions_open=%d "
                "positions_stale=%d positions_profitable=%d positions_losing=%d "
                "positions_over_2_days=%d positions_over_3_days=%d "
                "available_slots=%d blocked_due_to_capacity=%s",
                _CRE_MAX, _pca_n_open,
                _pca_stale, _pca_profitable, _pca_losing,
                _pca_over2d, _pca_over3d,
                _pca_slots_avail, _pca_blocked,
            )
        except Exception as _pca_exc:
            log.debug("[PortfolioCapacityAudit] skipped: %s", _pca_exc)

        # ── [PortfolioQualityAudit] + [ReplacementOpportunityAudit] ──────────
        try:
            from risk_control.capital_risk_engine import (
                get_last_cycle_exposure_rejections as _get_ec_cycle,
                _MAX_POSITIONS as _CRE_MAX_POS,
            )
            _ec_cycle_rejs = _get_ec_cycle()

            # ── [PortfolioQualityAudit] ─────────────────────────────────
            _pqa_orders = self.order_manager.get_open_orders()
            _pqa_n      = len(_pqa_orders)
            if _pqa_n > 0:
                _pqa_scores    = [r.confidence_score for r in _pqa_orders]
                _pqa_avg_sc    = round(sum(_pqa_scores) / _pqa_n, 2)
                _pqa_min_sc    = min(_pqa_scores)
                _pqa_max_sc    = max(_pqa_scores)
                _pqa_weakest   = next((r.symbol for r in _pqa_orders
                                       if r.confidence_score == _pqa_min_sc), "NONE")
                _pqa_strongest = next((r.symbol for r in _pqa_orders
                                       if r.confidence_score == _pqa_max_sc), "NONE")
            else:
                _pqa_avg_sc = _pqa_min_sc = _pqa_max_sc = 0.0
                _pqa_weakest = _pqa_strongest = "NONE"
            log.info(
                "[PortfolioQualityAudit] positions_open=%d avg_portfolio_score=%.2f "
                "lowest_score=%.2f highest_score=%.2f avg_confidence=%.2f "
                "weakest_position=%s strongest_position=%s",
                _pqa_n, _pqa_avg_sc, _pqa_min_sc, _pqa_max_sc, _pqa_avg_sc,
                _pqa_weakest, _pqa_strongest,
            )

            # ── [ReplacementOpportunityAudit] per heat-rejected signal ──
            _reset_replacement_accumulator()
            _pqa_now = datetime.now()
            for _ec_r in _ec_cycle_rejs:
                try:
                    _roa_sym   = _ec_r["symbol"]
                    _roa_score = _ec_r.get("score", 0.0)
                    _roa_conv  = _ec_r.get("conviction", 0.0)
                    _roa_strat = _ec_r.get("strategy", "unknown")
                    _roa_entry = _ec_r.get("entry", 0.0)
                    _roa_stop  = _ec_r.get("stop", 0.0)
                    _roa_tgt   = _ec_r.get("target", 0.0)
                    _roa_rr    = _ec_r.get("rr", 0.0)

                    # Build evictable candidate list (mirrors _smart_swap_check logic)
                    _roa_candidates = []
                    for _roa_rec in _pqa_orders:
                        if _roa_rec.status != "open":
                            continue
                        _roa_age = ((_pqa_now - _roa_rec.placed_at).total_seconds() / 60.0
                                    if _roa_rec.placed_at else 999.0)
                        if _roa_age < 20.0:
                            continue  # too fresh
                        _roa_risk = (abs(_roa_rec.entry_price - _roa_rec.stop_loss)
                                     if _roa_rec.stop_loss and
                                     _roa_rec.stop_loss != _roa_rec.entry_price else 0.0)
                        _roa_pos  = portfolio.positions.get(_roa_rec.symbol)
                        _roa_r    = None
                        if _roa_pos and _roa_pos.has_live_ltp and _roa_risk > 0:
                            _roa_r = (
                                (_roa_pos.ltp - _roa_rec.entry_price) / _roa_risk
                                if _roa_rec.direction == "BUY"
                                else (_roa_rec.entry_price - _roa_pos.ltp) / _roa_risk
                            )
                        if _roa_r is not None and _roa_r >= 1.5:
                            continue  # safe winner — never evict
                        _roa_candidates.append((_roa_r, _roa_age, _roa_rec))

                    _roa_portfolio_full = _pqa_n >= _CRE_MAX_POS
                    _roa_has_candidate  = len(_roa_candidates) > 0
                    _roa_wk_sym = _roa_wk_strat = "NONE"
                    _roa_wk_sc  = _roa_wk_conf  = 0.0
                    _roa_eligible = False

                    if _roa_has_candidate:
                        _roa_candidates.sort(
                            key=lambda x: (x[0] if x[0] is not None else 0.0,
                                           x[2].confidence_score, -x[1])
                        )
                        _, _, _roa_wk_rec = _roa_candidates[0]
                        _roa_wk_sym   = _roa_wk_rec.symbol
                        _roa_wk_strat = _roa_wk_rec.strategy
                        _roa_wk_sc    = _roa_wk_rec.confidence_score
                        _roa_wk_conf  = _roa_wk_rec.confidence_score
                        # Score-delta gate (mirrors _SWAP_SCORE_DELTA = 0.5)
                        _roa_eligible = _roa_score >= _roa_wk_sc + 0.5
                        # RR gate (mirrors _SWAP_MIN_NEW_RR = 1.5)
                        if _roa_rr < 1.5:
                            _roa_eligible = False

                    _roa_sc_delta   = round(_roa_score - _roa_wk_sc, 2)
                    _roa_conf_delta = round(_roa_conv - _roa_wk_conf, 2)

                    if not _roa_portfolio_full:
                        _roa_rej = "PORTFOLIO_NOT_FULL"
                    elif not _roa_has_candidate:
                        _roa_rej = "NO_EVICTABLE_POSITIONS"
                    elif _roa_rr < 1.5:
                        _roa_rej = "NEW_SIGNAL_RR_TOO_LOW"
                    elif not _roa_eligible:
                        _roa_rej = "SCORE_DELTA_INSUFFICIENT"
                    else:
                        _roa_rej = "REPLACEMENT_ELIGIBLE_NOT_TRIGGERED"

                    log.info(
                        "[ReplacementOpportunityAudit] symbol=%s strategy=%s "
                        "new_signal_score=%.2f new_signal_confidence=%.2f "
                        "new_signal_conviction=%.2f portfolio_full=%s "
                        "lowest_position_symbol=%s lowest_position_strategy=%s "
                        "lowest_position_score=%.2f lowest_position_confidence=%.2f "
                        "score_delta=%.2f confidence_delta=%.2f "
                        "replacement_candidate=%s replacement_eligible=%s "
                        "replacement_triggered=False rejection_reason=%s",
                        _roa_sym, _roa_strat,
                        _roa_score, _roa_score, _roa_conv,
                        _roa_portfolio_full,
                        _roa_wk_sym, _roa_wk_strat,
                        _roa_wk_sc, _roa_wk_conf,
                        _roa_sc_delta, _roa_conf_delta,
                        _roa_has_candidate, _roa_eligible,
                        _roa_rej,
                    )
                    _REPLACEMENT_DAILY_AUDIT.append({
                        "symbol":        _roa_sym,
                        "strategy":      _roa_strat,
                        "score":         _roa_score,
                        "candidate":     _roa_has_candidate,
                        "eligible":      _roa_eligible,
                        "score_delta":   _roa_sc_delta,
                        "rej_reason":    _roa_rej,
                    })
                except Exception as _roa_exc:
                    log.debug("[ReplacementOpportunityAudit] per-signal error: %s", _roa_exc)

        except Exception as _rep_block_exc:
            log.debug("[ReplacementOpportunityAudit] block skipped: %s", _rep_block_exc)

        # ── STEP 4: Risk Filtering ─────────────────────────────────
        with self.system_monitor.time_layer("RiskControl"):
            approved_signals = self._run_risk_control(cre_signals, snapshot)
        if self._abort_if_timed_out("RiskControl"): return
        _rc_out_total = len(approved_signals)  # before options split; for TradeDiagnostic
        _rc_s = getattr(self, '_last_rc_reject_summary', {})
        _rc_blocker = (
            f"RR×{_rc_s.get('rr', 0)} HEAT×{_rc_s.get('heat', 0)} "
            f"OTHER×{_rc_s.get('other', 0)}"
        ) if any(_rc_s.get(k, 0) for k in ('rr', 'heat', 'other')) else "OK"
        _diag.record_stage("RiskControl", len(cre_signals), _rc_out_total, _rc_blocker)

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
        _n_opts_signals = len(_options_signals)  # captured for TradeDiagnostic

        if _options_signals:
            log.info("── Options Fast-Path: %d signal(s) ──", len(_options_signals))
            self._run_options_fast_path(_options_signals, snapshot)
            _oqg = getattr(self, '_last_oqg_summary', {})
            _diag.record_stage("OptionsQualityGate",
                               _oqg.get('in', _n_opts_signals),
                               _oqg.get('passed', 0),
                               "C1-C6_QUALITY_GATES" if _oqg.get('rejected', 0) > 0 else "OK")

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
            # ── Priority 6 (SimulationCalibrationAudit): threshold drift ──
            try:
                from market_simulation.simulation_calibration_audit import (
                    get_simulation_audit as _gsa,
                )
                _sa = _gsa()
                _sa.record_cycle(sim_result)
                _sa.emit_cycle_audit()
            except Exception:
                pass
        _diag.record_stage("MarketSimulation", len(approved_signals),
                           len(sim_result.approved_trades) if hasattr(sim_result, 'approved_trades') else len(approved_signals),
                           "STABILITY_THRESHOLD")

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
            _diag.record_stage("RiskGuardian",
                               len(sim_result.approved_trades) if hasattr(sim_result, 'approved_trades') else 0,
                               0, guardian_decision.reason or "GUARDIAN_BLOCKED")
            _diag.set_totals(len(signals), 0, _n_opts_signals,
                             getattr(self, '_last_options_placed', 0))
            _diag.generate()
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
                        "confidence": s.confidence / 10.0,  # TradeSignal.confidence is 0–10; normalise to 0–1
                        "entry_price": s.entry_price,
                        "stop_loss": s.stop_loss,
                        "target": s.target_price,           # TradeSignal uses target_price, not target
                        "original_signal": s,
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
        _diag.record_stage("DebateAndDecision", len(signals_for_debate), len(executed),
                           "CONFIDENCE_BELOW_THRESHOLD_6.5")

        # ── SIGNAL LIFECYCLE FUNNEL SUMMARY ───────────────────────────
        # Counts each signal as it passes through each filter stage.
        # Lets you see exactly where signals are disappearing each cycle.
        _n_generated   = len(signals)
        _n_strategy    = len(enriched_signals)
        _n_risk        = len(approved_signals)
        _n_sim         = len(sim_result.approved_trades)   if hasattr(sim_result, "approved_trades")   else _n_risk
        _n_guardian    = len(guardian_decision.approved_signals) if guardian_decision.approved else 0
        _n_debate      = len(signals_for_debate)
        _n_executed    = len(executed)
        log.info(
            "[SignalLifecycle] generated=%d  strategy_lab=%d  risk_control=%d  "
            "simulation=%d  guardian=%d  debate_input=%d  executed=%d",
            _n_generated, _n_strategy, _n_risk, _n_sim,
            _n_guardian, _n_debate, _n_executed,
        )

        # ── [PipelineAttrition] structured funnel report ──────────────────────
        def _pct(a: int, b: int) -> str:
            return f"{100 * a // b if b else 0}%"
        _prep_attrition = getattr(
            __import__(
                "opportunity_engine.equity_scanner_ai",
                fromlist=["_LAST_PREPARED_STATS"],
            ),
            "_LAST_PREPARED_STATS", {},
        )
        _n_watchlist = _prep_attrition.get("watchlist_count", 0) if isinstance(_prep_attrition, dict) else 0
        _n_prepared  = _prep_attrition.get("prepared_count",  0) if isinstance(_prep_attrition, dict) else 0
        log.info(
            "[PipelineAttrition] "
            "watchlist=%d prepared=%d(-%.0f%%) "
            "signals=%d(-%.0f%%) "
            "strategy_lab=%d(-%.0f%%) "
            "risk_control=%d(-%.0f%%) "
            "simulation=%d(-%.0f%%) "
            "approved=%d(-%.0f%%) "
            "dominant_attrition=%s",
            _n_watchlist,
            _n_prepared,  100 - (100 * _n_prepared  // _n_watchlist  if _n_watchlist  else 100),
            _n_generated, 100 - (100 * _n_generated // _n_prepared   if _n_prepared   else 100),
            _n_strategy,  100 - (100 * _n_strategy  // _n_generated  if _n_generated  else 100),
            _n_risk,      100 - (100 * _n_risk      // _n_strategy   if _n_strategy   else 100),
            _n_sim,       100 - (100 * _n_sim       // _n_risk       if _n_risk       else 100),
            _n_executed,  100 - (100 * _n_executed  // _n_sim        if _n_sim        else 100),
            max(
                [
                    ("prepared_enrichment",  _n_watchlist  - _n_prepared),
                    ("signal_generation",    _n_prepared   - _n_generated),
                    ("strategy_lab",         _n_generated  - _n_strategy),
                    ("risk_control",         _n_strategy   - _n_risk),
                    ("simulation",           _n_risk       - _n_sim),
                    ("debate_execution",     _n_sim        - _n_executed),
                ],
                key=lambda x: x[1],
            )[0],
        )

        # ── Self-Diagnostic: "Why no trade?" synthesis ────────────────────────────
        _diag.set_totals(
            generated=_n_generated,
            executed=_n_executed,
            options_in=getattr(self, '_last_oqg_summary', {}).get('in', 0),
            options_fast_path_passed=getattr(self, '_last_options_placed', 0),
        )
        _diag.generate()

        # ── Forensic telemetry: execution stage (observational only) ─────────────
        try:
            from control_tower.pipeline_forensic_reporter import get_forensic_reporter as _gfr
            _regime_val_f = (
                getattr(snapshot.regime, "value", str(snapshot.regime))
                if snapshot else "UNKNOWN"
            )
            _carry_cnt = len(self.trade_monitor.get_open_trades()) if hasattr(self.trade_monitor, "get_open_trades") else 0
            _forensic_r = _gfr()
            _forensic_r.record_execution_cycle(
                candidates=_n_generated,
                approved=_n_risk,
                orders=_n_executed,
                regime=_regime_val_f,
                stale_count=_carry_cnt,
            )
            # Emit per-cycle pipeline tags for intraday observability
            from opportunity_engine.equity_scanner_ai import _LAST_PREPARED_STATS as _fps
            _prep_cnt = _fps.get("prepared_count", 0) if isinstance(_fps, dict) else 0
            _inv_cnt  = _fps.get("invalidated_count", 0) if isinstance(_fps, dict) else 0
            _forensic_r.emit_cycle_pipeline_tags(
                cycle_num=getattr(self.system_monitor, "_cycle_id", 0),
                prepared_count=_prep_cnt,
                invalidated_count=_inv_cnt,
                signals=_n_generated,
                approved=_n_risk,
                regime=_regime_val_f,
            )
        except Exception:
            pass

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
        # ── PER-CYCLE FEED HEALTH SUMMARY ─────────────────────────────
        try:
            from data_feeds import get_feed_manager as _gfm_cycle
            _fm = _gfm_cycle()
            log.info("[FeedHealth] %s", _fm.get_cycle_feed_summary())
            # Market Truth Governor: log warnings, fire Telegram on SYNTHETIC
            _fm.check_truth_governance()
            # Phase 7: persistent CSV audit trail
            _fm.write_cycle_audit()
            _fm.reset_cycle_stats()
            # Periodic token expiry check (warns at <24h and <6h)
            _fm.dhan.check_token_expiry()
        except Exception:
            pass

        # ── CAPTURE LAST CYCLE REPORT (for Telegram /cycle) ───────────
        try:
            from data_feeds.data_feed_manager import FeedTruthLevel as _FTL
            from data_feeds import get_feed_manager as _gfm2
            _fm2          = _gfm2()
            _truth_lvl, _truth_mod = _fm2.get_current_truth_level()
            _opts_lvl, _           = _fm2.get_options_truth_level()
            import config as _cfg
            _schedule = getattr(_cfg, "SCHEDULE", {})
            _now_slot = datetime.now().hour * 100 + datetime.now().minute
            _next_slot = next(
                (t for t in sorted(_schedule.keys()) if t > _now_slot), None
            )
            self._last_cycle_report = {
                "ts":           datetime.now().strftime("%d-%b %H:%M"),
                "regime":       str(getattr(snapshot.regime, "value", snapshot.regime)),
                "vix":          round(float(getattr(snapshot, "vix", 0.0)), 1),
                "truth_level":  str(_truth_lvl),
                "truth_mod":    _truth_mod,
                "opts_truth":   str(_opts_lvl),
                "feed_stats":   _fm2.get_cycle_stats_summary(),   # Phase 9
                "executed":     [
                    {
                        "symbol":    r.get("symbol", "?"),
                        "strategy":  r.get("strategy", "?"),
                        "score":     round(float(r.get("score", 0)), 2),
                        "direction": r.get("direction", "?"),
                        "entry":     round(float(r.get("entry", 0)), 2),
                    }
                    for r in executed
                ],
                "signals_scanned": len(signals),
                "next_slot":    f"{_next_slot // 100:02d}:{_next_slot % 100:02d}" if _next_slot else "—",
            }
        except Exception:
            pass

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

        # ── [StrategyLabReject] forensic audit ────────────────────────────────
        # Emit one structured line per signal that did NOT survive strategy lab
        # so operators can identify the dominant rejection vector.
        from strategy_lab.backtesting_ai import _BACKTEST_CACHE as _BT_CACHE_REF
        from strategy_lab.strategy_generator_ai import STRATEGY_PARAMS as _SP_REF
        _tested_syms  = {s.symbol for s in tested}
        _matched_syms = {s.symbol for s in matched}
        _reject_by_reason: dict = {}
        _reject_by_strategy: dict = {}
        for _s in signals:
            if _s.symbol in _tested_syms:
                continue  # survived
            _strat    = getattr(_s, "strategy_name", "UNASSIGNED")
            _bt_result = _BT_CACHE_REF.get(_strat)
            _bt_score  = getattr(_bt_result, "composite_score", None) if _bt_result else None
            _passes_gate = getattr(_bt_result, "passes_gate", None) if _bt_result else None
            if _s.symbol not in _matched_syms:
                # Dropped by assign_strategy: bear-market equity long, R:R below
                # strategy min_rr, or MetaController active-set exclusion.
                _rr = getattr(_s, "risk_reward_ratio", 0.0)
                _assigned_strat = getattr(_s, "strategy_name", "UNKNOWN")
                _params = _SP_REF.get(_assigned_strat, {})
                _min_rr = _params.get("min_rr", 0.0)
                if _rr < _min_rr:
                    _rej_reason = f"RR_{_rr:.1f}_below_min_{_min_rr:.1f}"
                elif _assigned_strat in (shm_disabled | perf_disabled):
                    _rej_reason = "STRATEGY_DISABLED"
                else:
                    _rej_reason = "ASSIGN_REJECTED"
            elif _strat in (shm_disabled | perf_disabled):
                _rej_reason = "STRATEGY_DISABLED"
            elif _passes_gate is False:
                _rej_reason = "BACKTEST_GATE_FAIL"
            else:
                _rej_reason = "BACKTEST_SCORE_LOW"
            _regime_match = (
                getattr(snapshot.regime, "value", str(snapshot.regime))
                if snapshot else "UNKNOWN"
            )
            _qgate = "PASS" if _passes_gate else ("FAIL" if _passes_gate is False else "NO_DATA")
            log.info(
                "[StrategyLabReject] symbol=%s strategy=%s rejection_reason=%s "
                "backtest_score=%s regime_match=%s quality_gate=%s",
                _s.symbol, _strat, _rej_reason,
                f"{_bt_score:.3f}" if _bt_score is not None else "N/A",
                _regime_match, _qgate,
            )
            _reject_by_reason[_rej_reason]    = _reject_by_reason.get(_rej_reason, 0) + 1
            _reject_by_strategy[_strat]       = _reject_by_strategy.get(_strat, 0) + 1
        _strategy_reject_count = len(signals) - len(tested)
        if _strategy_reject_count:
            log.info(
                "[StrategyLabReject] AGGREGATE strategy_reject_count=%d "
                "reject_by_strategy=%s reject_by_reason=%s",
                _strategy_reject_count,
                dict(sorted(_reject_by_strategy.items(), key=lambda x: -x[1])),
                dict(sorted(_reject_by_reason.items(), key=lambda x: -x[1])),
            )
        self._last_sl_reject_summary = dict(_reject_by_reason)  # for TradeDiagnostic

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

        # ── Layer 2 (options): ExecutionWindowGuard ───────────────────────
        # Options fast-path bypasses run_full_cycle; guard independently.
        _ofp_now = datetime.now()
        _ofp_win = _ofp_now.replace(hour=9, minute=45, second=0, microsecond=0)
        if _ofp_now < _ofp_win:
            log.info(
                "[ExecWindowGuard] L2 options_fast_path suppressed at %s — "
                "execution window opens 09:45.",
                _ofp_now.strftime("%H:%M:%S"),
            )
            return
        # ── end Layer 2 (options) ─────────────────────────────────────────

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
        self._last_oqg_summary = {  # for TradeDiagnostic
            "in": len(signals), "passed": len(qualified),
            "rejected": len(signals) - len(qualified),
        }
        self._last_options_placed = 0  # reset; incremented per placed order below
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
                self._last_options_placed += 1
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
            _notes_parse_ok = False
            _notes_raw = sig.notes or ""
            try:
                meta = _json.loads(_notes_raw or "{}")
                _notes_parse_ok = True
            except Exception as _pe:
                # Should not happen after CRE/LiquidityGuard were fixed to use
                # JSON-aware mutations.  Kept as a hard-stop safety net.
                log.info(
                    "[MetadataCorruptionDetected] "
                    "module=master_orchestrator._options_quality_gate  "
                    "symbol=%s  strategy=%s  error=%s  notes_snippet=%r",
                    sym, strat, type(_pe).__name__, _notes_raw[:100],
                )

            is_live      = meta.get("is_live", False)
            chain_qual   = meta.get("chain_quality", 0.0)
            dte          = meta.get("dte", 0)
            iv_rank      = meta.get("iv_rank", 50.0)
            chain_issues = meta.get("chain_issues", [])

            # ── Capability lookup (used by both audit lines below) ─────────────
            _cap_source = "UNKNOWN"
            _cap_live   = False
            try:
                from data_feeds import get_feed_manager as _gfm_qual
                _cap_info   = _gfm_qual().get_options_capability(sym)
                _cap_source = _cap_info.get("source", "UNKNOWN")
                _cap_live   = _cap_info.get("chain_live", False)
            except Exception:
                pass

            # [MetadataIntegrityAudit] — emitted for every signal ──────────────
            log.info(
                "[MetadataIntegrityAudit] symbol=%s  strategy=%s  "
                "notes_parse_ok=%s  metadata_keys=%s  is_live=%s  source=%s",
                sym, strat,
                _notes_parse_ok,
                sorted(meta.keys()),
                is_live,
                _cap_source,
            )

            # [OptionsDecisionTrace] — full pipeline journey ───────────────────
            _iv_source = (
                "DHAN_LIVE" if _cap_source == "DHAN"
                else "BS_SEED" if _cap_source in ("ANGELONE", "NSE")
                else "UNKNOWN"
            )
            log.info(
                "[OptionsDecisionTrace] symbol=%s  strategy=%s  confidence=%.1f  "
                "capability_source=%s  capability_live=%s  "
                "signal_dte=%d  signal_iv_rank=%.0f  "
                "notes_parse_ok=%s  is_live_in_notes=%s",
                sym, strat, sig.confidence,
                _cap_source, _cap_live,
                dte, iv_rank,
                _notes_parse_ok,
                is_live,
            )

            # Check 1: Live data gate
            if not is_live:
                log.info(
                    "[OptionsQualityAudit] symbol=%s  strategy=%s  "
                    "source=%s  chain_live=%s  iv_source=%s  iv_rank=%.0f  "
                    "is_synthetic=%s  rejection_reason=%s  notes_parse_ok=%s",
                    sym, strat,
                    _cap_source, _cap_live,
                    _iv_source, iv_rank,
                    not _cap_live,
                    "notes_json_corrupted" if not _notes_parse_ok else "is_live_false_in_notes",
                    _notes_parse_ok,
                )
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

        # ── [RiskControlDecision] for PortfolioAllocationAI drops ─────────────
        from risk_control.risk_manager_ai import MIN_RR_RATIO as _MIN_RR
        _pa_out_syms = {s.symbol for s in sized}
        for _s in checked:
            if _s.symbol not in _pa_out_syms:
                _req_rr = 0.5 if _s.signal_type in (_SigType.OPTIONS, _SigType.SPREAD) else _MIN_RR
                log.info(
                    "[RiskControlDecision] symbol=%s strategy=%s confidence=%.2f "
                    "conviction=%.2f rr_ratio=%.2f required_rr=%.1f "
                    "heat_before=%.4f heat_after=%.4f "
                    "rejection_reason=POSITION_LIMIT_REJECTION exact=SIZING_DROP_PA",
                    _s.symbol, _s.strategy_name, _s.confidence,
                    _s.confidence / 10.0, _s.risk_reward_ratio, _req_rr,
                    self.risk_manager._current_portfolio_heat,
                    self.risk_manager._current_portfolio_heat,
                )
        _pa_rej = len(checked) - len(sized)

        # ── [RiskControlDecision] for StressTestAI drops ──────────────────────
        _st_out_syms = {s.symbol for s in stressed}
        for _s in sized:
            if _s.symbol not in _st_out_syms:
                _req_rr = 0.5 if _s.signal_type in (_SigType.OPTIONS, _SigType.SPREAD) else _MIN_RR
                log.info(
                    "[RiskControlDecision] symbol=%s strategy=%s confidence=%.2f "
                    "conviction=%.2f rr_ratio=%.2f required_rr=%.1f "
                    "heat_before=%.4f heat_after=%.4f "
                    "rejection_reason=OTHER_EXACT exact=STRESS_TEST_FAIL",
                    _s.symbol, _s.strategy_name, _s.confidence,
                    _s.confidence / 10.0, _s.risk_reward_ratio, _req_rr,
                    self.risk_manager._current_portfolio_heat,
                    self.risk_manager._current_portfolio_heat,
                )
        _st_rej = len(sized) - len(stressed)

        # ── [RiskControlSummary] ──────────────────────────────────────────────
        _rm_s = getattr(self.risk_manager, "_last_reject_summary", {})
        _rc_full = {
            "rr_rejected":              _rm_s.get("RR_REJECTION", 0),
            "heat_rejected":            _rm_s.get("HEAT_REJECTION", 0),
            "cooldown_rejected":        _rm_s.get("COOLDOWN_REJECTION", 0),
            "governance_rejected":      _rm_s.get("GOVERNANCE_REJECTION", 0),
            "liquidity_rejected":       _rm_s.get("LIQUIDITY_REJECTION", 0),
            "position_limit_rejected":  _rm_s.get("POSITION_LIMIT_REJECTION", 0) + _pa_rej,
            "sector_rejected":          _rm_s.get("SECTOR_LIMIT_REJECTION", 0),
            "correlation_rejected":     _rm_s.get("CORRELATION_REJECTION", 0),
            "stale_rejected":           _rm_s.get("STALE_SIGNAL_REJECTION", 0),
            "other_rejected":           _rm_s.get("OTHER_EXACT", 0) + _st_rej,
        }
        _rc_total_rej = sum(_rc_full.values())
        _rc_dom_key   = max(_rc_full, key=_rc_full.get) if _rc_total_rej > 0 else "none"
        _rc_signals_in = len(signals)
        log.info(
            "[RiskControlSummary] signals_in=%d signals_out=%d "
            "rr_rejected=%d heat_rejected=%d cooldown_rejected=%d governance_rejected=%d "
            "liquidity_rejected=%d position_limit_rejected=%d sector_rejected=%d "
            "correlation_rejected=%d stale_rejected=%d other_rejected=%d "
            "dominant_reason=%s",
            _rc_signals_in, len(stressed),
            _rc_full["rr_rejected"], _rc_full["heat_rejected"],
            _rc_full["cooldown_rejected"], _rc_full["governance_rejected"],
            _rc_full["liquidity_rejected"], _rc_full["position_limit_rejected"],
            _rc_full["sector_rejected"], _rc_full["correlation_rejected"],
            _rc_full["stale_rejected"], _rc_full["other_rejected"],
            _rc_dom_key,
        )

        # ── [RiskControlVerdict] ─────────────────────────────────────────────
        if _rc_signals_in == 0 or _rc_total_rej == 0:
            _rc_verdict = "RISKCONTROL_HEALTHY"
        elif _rc_dom_key in ("rr_rejected", "heat_rejected"):
            _rc_verdict = "RISKCONTROL_HEALTHY"
        elif _rc_dom_key in (
            "governance_rejected", "other_rejected", "position_limit_rejected",
            "sector_rejected", "stale_rejected", "liquidity_rejected",
            "correlation_rejected",
        ):
            _rc_verdict = "RISKCONTROL_OVER_RESTRICTIVE"
        else:
            _rc_verdict = "INSUFFICIENT_EVIDENCE"
        log.info(
            "[RiskControlVerdict] verdict=%s dominant_reason=%s "
            "signals_in=%d signals_out=%d total_rejected=%d",
            _rc_verdict, _rc_dom_key, _rc_signals_in, len(stressed), _rc_total_rej,
        )

        # ── Update _last_rc_reject_summary for TradeDiagnostic blocker string ─
        self._last_rc_reject_summary = {
            "rr":   _rc_full["rr_rejected"],
            "heat": _rc_full["heat_rejected"],
            "other": (
                _rc_full["governance_rejected"] + _rc_full["cooldown_rejected"] +
                _rc_full["liquidity_rejected"]  + _rc_full["position_limit_rejected"] +
                _rc_full["sector_rejected"]     + _rc_full["correlation_rejected"] +
                _rc_full["stale_rejected"]      + _rc_full["other_rejected"]
            ),
        }

        # ── [BorderlineConfidenceAudit] + shadow persistence ─────────────────
        try:
            import json as _json_bl
            from pathlib import Path as _Path_bl
            from datetime import datetime as _dt_bl
            from risk_control.risk_manager_ai import (
                get_last_cycle_borderline_rejections as _get_bl,
            )
            _bl_list = _get_bl()
            _bl_regime = str(getattr(snapshot, "regime", "UNKNOWN"))
            for _bl in _bl_list:
                log.info(
                    "[BorderlineConfidenceAudit] symbol=%s strategy=%s "
                    "confidence=%.2f conviction=%.2f rr_ratio=%.2f "
                    "sector=%s regime=%s "
                    "would_pass_simulation=%s would_pass_debate=%s",
                    _bl["symbol"], _bl["strategy"],
                    _bl["confidence"], _bl["conviction"], _bl["rr_ratio"],
                    _bl.get("sector", "UNKNOWN"), _bl_regime,
                    _bl["would_pass_simulation"], _bl["would_pass_debate"],
                )
            # Persist to shadow tracking file for [BorderlineOutcome] EOD
            if _bl_list:
                _bl_path = _Path_bl("/app/data") if _Path_bl("/app/data").exists() \
                    else _Path_bl(__file__).resolve().parents[1] / "data"
                _bl_file = _bl_path / "borderline_rejections.json"
                _existing: list = []
                if _bl_file.exists():
                    try:
                        _existing = _json_bl.loads(_bl_file.read_text(encoding="utf-8"))
                    except Exception:
                        _existing = []
                _today_str = _dt_bl.now().strftime("%Y-%m-%d")
                for _bl in _bl_list:
                    # Deduplicate: same symbol + same rejection date
                    _key = (_bl["symbol"], _today_str, _bl["strategy"])
                    if not any(
                        e.get("symbol") == _key[0]
                        and e.get("rejection_date") == _key[1]
                        and e.get("strategy") == _key[2]
                        for e in _existing
                    ):
                        _existing.append({
                            "symbol":        _bl["symbol"],
                            "strategy":      _bl["strategy"],
                            "confidence":    _bl["confidence"],
                            "rr_ratio":      _bl["rr_ratio"],
                            "entry_price":   _bl["entry_price"],
                            "stop_loss":     _bl["stop_loss"],
                            "direction":     _bl["direction"],
                            "rejection_date": _today_str,
                            "regime":        _bl_regime,
                            "sector":        _bl.get("sector", "UNKNOWN"),
                            "would_pass_simulation": _bl["would_pass_simulation"],
                            "would_pass_debate":     _bl["would_pass_debate"],
                            "day1_price":    None,
                            "day3_price":    None,
                            "day5_price":    None,
                        })
                _bl_file.write_text(
                    _json_bl.dumps(_existing, indent=2), encoding="utf-8"
                )
        except Exception as _bl_exc:
            log.debug("[BorderlineConfidenceAudit] block skipped: %s", _bl_exc)

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

            # ── Resolve OrderRecord + exit price for the weakest position ─────
            # portfolio.positions is keyed by symbol; close_position requires
            # the UUID order_id from the matching OrderRecord.
            _rot_records = self.order_manager.get_open_orders()
            _rot_rec     = next(
                (r for r in _rot_records
                 if r.symbol == weakest.symbol and r.status == "open"),
                None,
            )
            if _rot_rec is None:
                log.warning(
                    "[RotationReject] %s — no open OrderRecord found for weakest "
                    "position %s. Skipping rotation.",
                    sig.symbol, weakest.symbol,
                )
                continue
            # Prefer live LTP; fall back to entry price if no live feed.
            _rot_exit_px = (
                weakest.ltp
                if weakest.has_live_ltp and weakest.ltp > 0
                else _rot_rec.entry_price
            )

            # Close the weakest position via order manager
            try:
                self.order_manager.close_position(
                    _rot_rec.order_id,
                    _rot_exit_px,
                    reason=f"SMARTSWAP_ROTATION: replaced by {sig.symbol}",
                )
                log.info(
                    "[InstitutionalRotation] closed_symbol=%s closed_oid=%s "
                    "exit_price=%.2f incoming_symbol=%s incoming_score=%.2f "
                    "replaced_score=%.2f",
                    weakest.symbol, _rot_rec.order_id, _rot_exit_px,
                    sig.symbol, sig.confidence, weakest_confidence,
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

        # ── Market Truth Governance ─────────────────────────────────────────
        # EQUITY truth controls hard suppression/cap (equity LTPs are the source
        # of truth for P&L).  OPTIONS truth applies a modest size penalty only —
        # it must never cause a hard block on equity trades.
        try:
            from data_feeds import get_feed_manager as _gfm_dd
            from data_feeds.data_feed_manager import FeedTruthLevel, OptionsTruthLevel
            _fm_gov      = _gfm_dd()
            _equity_lvl, _ = _fm_gov.get_current_truth_level()
            _opts_lvl, _   = _fm_gov.get_options_truth_level()

            # ── EQUITY TRUTH: hard rules ─────────────────────────────────────
            if decision.approved and _equity_lvl == FeedTruthLevel.SYNTHETIC:
                log.warning(
                    "[MarketTruthGovernor] EQUITY_SYNTHETIC — "
                    "SUPPRESSING new trade approval for %s", signal.symbol,
                )
                decision.approved               = False
                decision.trade_type             = "REJECT"
                decision.position_size_modifier = 0.0
                decision.reasoning += (
                    " | [GOVERNANCE] BLOCKED: 100% synthetic equity data — no live truth"
                )

            elif decision.approved and decision.trade_type == "FULL" and _equity_lvl == FeedTruthLevel.CRITICAL:
                log.warning(
                    "[MarketTruthGovernor] EQUITY_CRITICAL — "
                    "downgrading %s FULL→PARTIAL, size capped 50%%", signal.symbol,
                )
                decision.trade_type             = "PARTIAL"
                decision.position_size_modifier = min(decision.position_size_modifier, 0.5)
                decision.reasoning += (
                    " | [GOVERNANCE] Size capped 50%: CRITICAL equity feed (>60% sim)"
                )

            # ── OPTIONS TRUTH: soft penalty only — never a hard block ────────
            if decision.approved and _opts_lvl == OptionsTruthLevel.SYNTHETIC:
                _size_cap = 0.60
                decision.position_size_modifier = min(decision.position_size_modifier, _size_cap)
                if decision.trade_type == "FULL":
                    decision.trade_type = "PARTIAL"
                log.info(
                    "[OptionsGovernance] equity_truth=%s options_truth=SYNTHETIC "
                    "action=PARTIAL_DOWNGRADE size_cap=60%% symbol=%s",
                    _equity_lvl, signal.symbol,
                )
                decision.reasoning += (
                    f" | [GOVERNANCE] Options synthetic (equity={_equity_lvl}): size capped 60%%"
                )

            elif decision.approved and _opts_lvl == OptionsTruthLevel.DEGRADED_CACHE:
                _size_cap = 0.80
                decision.position_size_modifier = min(decision.position_size_modifier, _size_cap)
                log.info(
                    "[OptionsGovernance] equity_truth=%s options_truth=DEGRADED_CACHE "
                    "size_cap=80%% symbol=%s",
                    _equity_lvl, signal.symbol,
                )
                decision.reasoning += (
                    " | [GOVERNANCE] Options cache-degraded: size capped 80%%"
                )

        except Exception:
            pass

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

    def get_last_cycle_report(self) -> dict:
        """Return the most recently captured cycle summary (for Telegram /cycle)."""
        return dict(self._last_cycle_report)

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
        _syms = list({o.symbol for o in restored})   # unique symbols (denominator for label)
        try:
            from data_feeds.market_data_router import get_market_data_router
            _router  = get_market_data_router()
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

        # Also run carry-expiry check with LTPGuard-validated prices
        # (raw _live_pf can contain corrupt Dhan values — must use resolved prices)
        try:
            _post_validated = self.trade_monitor.get_resolved_prices()
            _n_expired = self.order_manager.check_and_expire_carries(_post_validated or _live_pf)
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
                    f"Gap: {_gap_sec // 60} min  Live prices: {len(_live_pf)}/{len(_syms)}",
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

        # ── Empty-feed guard: warn when open positions will be silently skipped ──
        _open_trades = self.trade_monitor.get_open_trades()
        if not _live_pf and _open_trades:
            self._missed_monitor_cycles += 1
            _affected_syms = sorted({o.symbol for o in _open_trades})
            log.warning(
                "[Monitor] OPEN_POSITIONS_PRESENT_BUT_NO_PRICE_FEED "
                "missed_cycle=%d  open_positions=%d  symbols=%s  ts=%s",
                self._missed_monitor_cycles,
                len(_open_trades),
                _affected_syms,
                _now_ts.strftime("%H:%M:%S"),
            )
            try:
                from notifications.notifier_manager import get_notifier
                if self._missed_monitor_cycles == 1 or self._missed_monitor_cycles % 6 == 0:
                    get_notifier().send_alert(
                        f"[Monitor] No price feed for {len(_open_trades)} open "
                        f"position(s) — cycle #{self._missed_monitor_cycles} skipped.\n"
                        f"Symbols: {_affected_syms}\n"
                        f"Time: {_now_ts.strftime('%H:%M:%S IST')}"
                    )
            except Exception:
                pass
        elif _live_pf and self._missed_monitor_cycles > 0:
            # Feed recovered — reset counter
            log.info(
                "[Monitor] Price feed recovered after %d missed cycle(s).",
                self._missed_monitor_cycles,
            )
            self._missed_monitor_cycles = 0

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
            # CRITICAL: pass get_resolved_prices() (LTPGuard-validated), NOT raw
            # _live_pf.  _live_pf can contain corrupt Dhan values (~₹1000) that
            # LTPGuard corrects inside check_all().  Using raw prices here caused
            # phantom P&L on MARICO (exit=1001.96 vs real~810) on 2026-06-11.
            _validated_pf  = self.trade_monitor.get_resolved_prices() if _check_all_ok else {}
            try:
                _n_expired = self.order_manager.check_and_expire_carries(_validated_pf or _live_pf)
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

    def _run_saturday_intelligence(self) -> None:
        """
        Weekend Intelligence — Saturday deep accumulation cycle.
        Runs only on Saturdays (weekday == 5). Guard is here so the
        scheduler can use every().day.at() without risk of firing on
        weekdays.
        """
        if datetime.now().weekday() != 5:
            return
        try:
            self.weekend_intelligence.run_saturday_cycle()
        except Exception as exc:
            log.error("[WeekendResearch] Saturday cycle crashed: %s", exc, exc_info=True)

    def _run_sunday_intelligence(self) -> None:
        """
        Weekend Intelligence — Sunday Monday preparation cycle.
        Runs only on Sundays (weekday == 6).
        """
        if datetime.now().weekday() != 6:
            return
        try:
            self.weekend_intelligence.run_sunday_cycle()
        except Exception as exc:
            log.error("[MondayPreparation] Sunday cycle crashed: %s", exc, exc_info=True)

    def _run_post_market_scan(self) -> None:
        """
        Phase D — Post-market deep scan.  Scheduled at 16:45 IST.
        Runs ~20 min, writes prepared candidates to data/daily_candidates.json.
        Skipped on NSE holidays; skipped if SCANNER_SHADOW_MODE=True until
        shadow validation is complete.
        """
        try:
            from config import is_nse_holiday
            if is_nse_holiday():
                log.info("[Orchestrator] NSE HOLIDAY — post-market scan skipped.")
                return
            log.info("[Orchestrator] 16:45 IST — starting Phase D post-market scanner.")
            from opportunity_engine.market_scanner import run_scan
            success = run_scan()
            if success:
                log.info("[Orchestrator] Phase D scanner complete — candidate store updated.")
            else:
                log.warning("[Orchestrator] Phase D scanner returned failure — static fallback active tomorrow.")
        except Exception as exc:
            log.error("[Orchestrator] Phase D scanner crashed: %s", exc, exc_info=True)

        # ── Observability: UniverseGenerationAudit ────────────────────────
        try:
            import json as _json_uga
            from pathlib import Path as _Path_uga
            from datetime import date as _date_uga
            _uga_today = _date_uga.today().isoformat()
            _uga_path  = _Path_uga("data/daily_candidates.json")
            _uga_n     = 0
            _uga_fresh = False
            _uga_source = "UNKNOWN"
            if _uga_path.exists():
                try:
                    _uga_data  = _json_uga.loads(_uga_path.read_text(encoding="utf-8"))
                    _uga_n     = len(_uga_data.get("candidates", []))
                    _uga_mtime = _uga_path.stat().st_mtime
                    _uga_fresh = _date_uga.fromtimestamp(_uga_mtime).isoformat() == _uga_today
                    _uga_source = _uga_data.get("source", "phase_d")
                except Exception:
                    pass
            log.info(
                "[UniverseGenerationAudit] date=%s candidates_written=%d fresh=%s source=%s",
                _uga_today, _uga_n, _uga_fresh, _uga_source,
            )
        except Exception as _uga_exc:
            log.debug("[UniverseGenerationAudit] skipped: %s", _uga_exc)

        # ── OIOS Layer 1A + 1B signal scan — signal_births + opportunities ─────
        # Runs after Phase D candidate scan in the 16:45 IST post-market slot.
        # Shadow-safe: writes only to market_behavior.db; never touches the
        # execution engine, signals, risk control, or position sizing path.
        try:
            from oios.db.connection import get_connection as _oios_get_conn
            from oios.scanners import layer_1a as _oios_l1a
            from oios.scanners import layer_1b as _oios_l1b
            from oios.scanners.signal_writer import write_scan_results as _oios_write
            from datetime import date as _oios_date
            _oios_scan_date = _oios_date.today().isoformat()
            _oios_regime = "unknown"
            if self._last_snapshot is not None:
                _snap_r = self._last_snapshot.regime
                _oios_regime = (
                    _snap_r.value if hasattr(_snap_r, "value") else str(_snap_r)
                ) or "unknown"
            with _oios_get_conn() as _oios_conn:
                _oios_symbols = [
                    r[0] for r in _oios_conn.execute(
                        "SELECT symbol FROM universe_stocks WHERE is_active=1"
                    ).fetchall()
                ]
                if _oios_symbols:
                    _oios_sector_map = dict(
                        _oios_conn.execute(
                            "SELECT symbol, sector FROM universe_stocks"
                        ).fetchall()
                    )
                    # Layer 1A — Confirmation DNA scanner
                    _oios_r1a = _oios_l1a.run_scan(
                        _oios_conn, _oios_symbols, _oios_scan_date, _oios_regime
                    )
                    _oios_w1a = _oios_write(
                        _oios_conn, _oios_r1a,
                        birth_ttl_days=10,
                        symbol_to_sector=_oios_sector_map,
                    )
                    # Layer 1B — Early Warning DNA scanner
                    _oios_r1b = _oios_l1b.run_scan(
                        _oios_conn, _oios_symbols, _oios_scan_date, _oios_regime
                    )
                    _oios_w1b = _oios_write(
                        _oios_conn, _oios_r1b,
                        birth_ttl_days=18,
                        symbol_to_sector=_oios_sector_map,
                    )
                    log.info(
                        "[OIOS] signal_births: 1A=%d 1B=%d  new_opps=%d  merged=%d  date=%s",
                        _oios_w1a["written"], _oios_w1b["written"],
                        _oios_w1a["new_opps"] + _oios_w1b["new_opps"],
                        _oios_w1a["merged"]   + _oios_w1b["merged"],
                        _oios_scan_date,
                    )
                else:
                    log.info("[OIOS] universe_stocks empty — signal scan skipped.")
        except Exception as _oios_scan_exc:
            log.warning("[OIOS] Signal scan failed (non-critical): %s", _oios_scan_exc)

    def _run_premarket_refiner(self) -> None:
        """
        Phase G — Pre-market refinement.  Scheduled at 08:45 IST.
        Applies overnight gap / conviction-decay re-scoring to prepared candidates.
        Skipped if USE_PREMARKET_REFINEMENT is False or candidate store is stale.
        """
        _ran_ok = False
        try:
            from config import USE_PREMARKET_REFINEMENT
            if not USE_PREMARKET_REFINEMENT:
                log.info("[Orchestrator] Premarket refiner disabled (USE_PREMARKET_REFINEMENT=False).")
                _ran_ok = True
                return
            from config import is_nse_holiday
            if is_nse_holiday():
                log.info("[Orchestrator] NSE HOLIDAY — premarket refiner skipped.")
                _ran_ok = True
                return
            log.info("[Orchestrator] 08:45 IST — starting Phase G premarket refiner.")
            from opportunity_engine.premarket_refiner import run_premarket_refinement
            run_premarket_refinement()
            _ran_ok = True
        except ImportError:
            # Phase G module not yet implemented — silently skip
            log.info("[Orchestrator] Phase G premarket_refiner not yet implemented — skipping.")
            _ran_ok = True
        except Exception as exc:
            log.error("[Orchestrator] Premarket refiner crashed: %s", exc, exc_info=True)
        finally:
            # Always emit a ct_event so the dashboard knows this slot was serviced
            try:
                self.bus.publish(SystemEvent(
                    event_type=EventType.PREMARKET_REFINER_RUN,
                    source_agent="PremarketRefiner",
                    payload={"ok": _ran_ok, "ts": datetime.now().isoformat()},
                ))
            except Exception:
                pass

        # ── Observability: PremarketReadinessAudit ────────────────────────
        try:
            import json as _json_pmra
            from pathlib import Path as _Path_pmra
            from datetime import datetime as _dt_pmra, date as _date_pmra
            _pmra_path = _Path_pmra("data/daily_candidates.json")
            _pmra_today = _date_pmra.today().isoformat()
            _pmra_n = 0
            _pmra_fresh = False
            _pmra_refined_at = None
            if _pmra_path.exists():
                try:
                    _pmra_data = _json_pmra.loads(_pmra_path.read_text(encoding="utf-8"))
                    _pmra_n = len(_pmra_data.get("candidates", []))
                    _pmra_mtime = _pmra_path.stat().st_mtime
                    _pmra_fresh = _date_pmra.fromtimestamp(_pmra_mtime).isoformat() == _pmra_today
                    _pmra_refined_at = _pmra_data.get("refined_at") or _pmra_data.get("prepared_at")
                except Exception:
                    pass
            log.info(
                "[PremarketReadinessAudit] date=%s candidates=%d fresh=%s refined_at=%s",
                _pmra_today, _pmra_n, _pmra_fresh, _pmra_refined_at or "UNKNOWN",
            )
        except Exception as _pmra_exc:
            log.debug("[PremarketReadinessAudit] skipped: %s", _pmra_exc)

        # ── Pre-Market Configuration Integrity Audit ────────────────────────────
        try:
            from utils.deployment_integrity_auditor import emit_deployment_integrity_audit as _dia
            _dia(context="premarket")
        except Exception as _dia_exc:
            log.debug("[DeploymentIntegrityAudit] premarket skipped: %s", _dia_exc)

    # ── Fix 1: Intraday expired-candidate refresh ─────────────────────────────

    def _run_intraday_refresh(self, label: str = "intraday") -> None:
        """
        Fix 1 — Mid-session refresh of expired prepared candidates.
        Scheduled at 11:30 IST and 13:30 IST.

        Fetches current LTPs for all 65 prepared candidates (expired + valid).
        Candidates whose price is still within ±5% of their stored base_ltp
        have their valid_until_utc extended by 4 hours.

        Runs only on market days; safely skips on NSE holidays.
        Never modifies RSI/ATR/S&R levels — only extends TTL for structurally
        unchanged setups so they remain in the prepared pool until session end.
        """
        _ret_scheduled  = datetime.now().strftime("%H:%M:%S")
        _ret_triggered  = False
        _ret_skipped    = False
        _ret_skip_reason = "NOT_REACHED"
        try:
            from config import is_nse_holiday
            if is_nse_holiday():
                _ret_skipped, _ret_skip_reason = True, "NSE_HOLIDAY"
                log.info(
                    "[RefreshExecutionTrace] scheduled_time=%s actual_time=%s "
                    "triggered=False skipped=True reason=NSE_HOLIDAY label=%s",
                    _ret_scheduled, _ret_scheduled, label,
                )
                return
            if not self._is_market_session():
                _ret_skipped, _ret_skip_reason = True, "OUTSIDE_MARKET_HOURS"
                log.info(
                    "[RefreshExecutionTrace] scheduled_time=%s actual_time=%s "
                    "triggered=False skipped=True reason=OUTSIDE_MARKET_HOURS label=%s",
                    _ret_scheduled, _ret_scheduled, label,
                )
                log.debug("[IntradayRefresh] Outside market hours — skipped (%s).", label)
                return

            from opportunity_engine.candidate_store import CandidateStore, STORE_FILE
            import json

            if not STORE_FILE.exists():
                _ret_skipped, _ret_skip_reason = True, "NO_STORE_FILE"
                log.info(
                    "[RefreshExecutionTrace] scheduled_time=%s actual_time=%s "
                    "triggered=False skipped=True reason=NO_STORE_FILE label=%s",
                    _ret_scheduled, _ret_scheduled, label,
                )
                log.debug("[IntradayRefresh] No store file — skipped (%s).", label)
                return

            payload   = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            candidates = payload.get("candidates", [])
            all_syms  = [c["symbol"] for c in candidates if c.get("symbol")]
            if not all_syms:
                _ret_skipped, _ret_skip_reason = True, "NO_CANDIDATES"
                log.info(
                    "[RefreshExecutionTrace] scheduled_time=%s actual_time=%s "
                    "triggered=False skipped=True reason=NO_CANDIDATES label=%s",
                    _ret_scheduled, _ret_scheduled, label,
                )
                return

            # Count stale before refresh
            from datetime import timezone as _tz
            _now_utc = datetime.now(_tz.utc)

            def _count_stale(cands: list) -> int:
                total = 0
                for _c in cands:
                    vu = _c.get("valid_until_utc") or ""
                    if not vu:
                        continue
                    try:
                        if datetime.fromisoformat(vu.replace("Z", "+00:00")) < _now_utc:
                            total += 1
                    except Exception:
                        pass
                return total

            _stale_before = _count_stale(candidates)

            _ret_triggered = True
            _ret_actual    = datetime.now().strftime("%H:%M:%S")
            log.info(
                "[RefreshExecutionTrace] scheduled_time=%s actual_time=%s "
                "triggered=True skipped=False reason=OK label=%s "
                "candidates_total=%d stale_before=%d",
                _ret_scheduled, _ret_actual, label, len(candidates), _stale_before,
            )
            log.info("[IntradayRefresh] %s — fetching LTPs for %d prepared candidates...",
                     label, len(all_syms))

            try:
                from data_feeds import get_feed_manager
                feed = get_feed_manager()
                ns_syms = [f"{s}.NS" for s in all_syms]
                quotes  = feed.get_multiple_quotes(ns_syms)
                prices: dict = {}
                for ns_sym, q in quotes.items():
                    bare = ns_sym.replace(".NS", "")
                    if q is not None and hasattr(q, "ltp") and q.ltp and q.ltp > 0:
                        prices[bare] = float(q.ltp)
            except Exception as exc:
                log.warning("[IntradayRefresh] LTP fetch failed: %s — refresh aborted.", exc)
                log.info(
                    "[RefreshCandidateAudit] label=%s candidates_examined=%d "
                    "candidates_refreshed=0 candidates_skipped=%d "
                    "expired_before_refresh=%d failure_reason=LTP_FETCH_FAILED",
                    label, len(candidates), len(candidates), _stale_before,
                )
                log.info(
                    "[RefreshSummary] refresh_runs=1 total_candidates_refreshed=0 "
                    "stale_before=%d stale_after=%d dominant_reason=LTP_FETCH_FAILED",
                    _stale_before, _stale_before,
                )
                return

            extended = CandidateStore.refresh_expired(prices, extend_hours=4.0)

            # Recount stale after refresh
            _payload_after = json.loads(STORE_FILE.read_text(encoding="utf-8"))
            _cands_after   = _payload_after.get("candidates", [])
            _stale_after   = _count_stale(_cands_after)
            _prices_found  = sum(1 for s in all_syms if s in prices)
            _skipped_count = len(all_syms) - _prices_found

            log.info(
                "[RefreshCandidateAudit] label=%s candidates_examined=%d "
                "candidates_refreshed=%d candidates_skipped=%d "
                "expired_before_refresh=%d prices_found=%d prices_missing=%d",
                label, len(candidates), extended, _skipped_count,
                _stale_before, _prices_found, _skipped_count,
            )
            log.info(
                "[RefreshSummary] refresh_runs=1 total_candidates_refreshed=%d "
                "stale_before=%d stale_after=%d dominant_reason=%s",
                extended, _stale_before, _stale_after,
                "TTL_EXTENDED" if extended > 0 else
                ("NO_PRICES" if _prices_found == 0 else "PRICE_DRIFT_EXCEEDED"),
            )

            log.info("[IntradayRefresh] %s complete — %d/%d expired candidates revived.",
                     label, extended, len(all_syms))

        except Exception as exc:
            log.error("[IntradayRefresh] %s crashed: %s", label, exc, exc_info=True)
            if not _ret_triggered:
                log.info(
                    "[RefreshExecutionTrace] scheduled_time=%s actual_time=%s "
                    "triggered=False skipped=True reason=EXCEPTION label=%s error=%s",
                    _ret_scheduled, datetime.now().strftime("%H:%M:%S"), label, exc,
                )

    # ── Fix 7: Weekly nifty500_universe.json rebuild ──────────────────────────

    def _check_scanner_events(self) -> None:
        """
        V2 — Poll for pending event-driven mini rescan requests from equity_scanner_ai.
        Called every 5 minutes by the position-monitor slot during market hours.

        Handles the event by running _run_intraday_refresh() which re-fetches
        LTPs and extends TTL for structurally unchanged candidates.
        Trigger events: POOL_EXHAUSTION, REGIME_TRANSITION, BREADTH_COLLAPSE,
        VIX_SURGE, EXPLORATION_STARVATION.
        """
        try:
            from opportunity_engine.equity_scanner_ai import get_pending_mini_rescan
            event = get_pending_mini_rescan()
            if not event:
                return
            reason   = event.get("reason", "UNKNOWN")
            priority = event.get("priority", "NORMAL")
            log.info(
                "[ScannerEvent] Mini rescan requested: %s priority=%s — running intraday refresh.",
                reason, priority,
            )
            label = f"event_{reason.split(':')[0].lower()}"
            self._run_intraday_refresh(label=label)
        except Exception as exc:
            log.debug("[ScannerEvent] Poll failed: %s", exc)

    def _run_weekly_universe_rebuild(self) -> None:
        """
        Fix 7 — Rebuild nifty500_universe.json every Monday at 08:30 IST.
        Runs the Phase D market_scanner in universe-rebuild-only mode so the
        source pool for the 16:45 IST post-market scan is never more than
        one week stale.

        Guard: only runs on Mondays (weekday == 0).  If the existing file is
        less than 24 hours old the rebuild is skipped (e.g. if today's 16:45
        scan already refreshed it).
        """
        if datetime.now().weekday() != 0:   # 0 = Monday
            return
        try:
            from config import is_nse_holiday
            if is_nse_holiday():
                log.info("[UniverseRebuild] NSE HOLIDAY (Monday) — universe rebuild skipped.")
                return

            import time as _time
            from pathlib import Path as _Path
            _universe_file = _Path(__file__).parent.parent / "data" / "nifty500_universe.json"
            if _universe_file.exists():
                age_h = (_time.time() - _universe_file.stat().st_mtime) / 3600.0
                if age_h < 24.0:
                    log.info("[UniverseRebuild] nifty500_universe.json is only %.1fh old — skipping.", age_h)
                    return

            log.info("[UniverseRebuild] Monday 08:30 — rebuilding nifty500_universe.json...")
            from opportunity_engine.market_scanner import run_scan
            success = run_scan()
            if success:
                log.info("[UniverseRebuild] Universe rebuild complete — nifty500_universe.json refreshed.")
            else:
                log.warning("[UniverseRebuild] Universe rebuild returned failure — previous file retained.")
        except Exception as exc:
            log.error("[UniverseRebuild] Crashed: %s", exc, exc_info=True)


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
            "ORPHAN_CLOSE",            # closed before first monitoring cycle (never had live LTP)
            "EOD_CLOSE",               # forced end-of-day flatten (currently dead code; exclude until wired)
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

        # ── OIOS live_observations — ingest paper_trades.csv ─────────────────
        # Runs every EOD after learning so enrichment can use today's outcomes.
        # Non-critical: failure does not affect learning, risk, or notifications.
        try:
            from analysis.live_observation_collector import ingest_from_csv as _ingest_live_obs
            _obs_result = _ingest_live_obs()
            log.info(
                "[OIOS] live_observations: new=%d processed=%d skipped=%d errors=%d",
                _obs_result["new"], _obs_result["processed"],
                _obs_result["skipped"], _obs_result["errors"],
            )
        except Exception as _live_obs_exc:
            log.warning("[OIOS] live_observation ingest failed (non-critical): %s", _live_obs_exc)

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

        # ── PCR Cache Quality Summary ──────────────────────────────────────
        try:
            self.market_data_ai.emit_pcr_cache_summary()
        except Exception as _pcr_sum_exc:
            log.warning("[EOD] PCR cache summary failed: %s", _pcr_sum_exc)

        # ── Phase 6: Dhan daily data-feed summary ─────────────────────────
        try:
            from data_feeds import get_feed_manager
            _fm = get_feed_manager()
            _dhan = getattr(_fm, "_dhan_feed", None) or getattr(_fm, "dhan_feed", None)
            if _dhan is not None and hasattr(_dhan, "emit_daily_summary"):
                _dhan.emit_daily_summary()
            else:
                log.debug("[EOD] DhanFeed not accessible via feed_manager — skipping emit_daily_summary")
        except Exception as _dhan_sum_exc:
            log.warning("[EOD] DhanFeed daily summary failed: %s", _dhan_sum_exc)

        # ── Symbol Normalization Health ────────────────────────────────────
        try:
            from utils.symbol_utils import get_normalization_health as _gnh
            from utils.symbol_utils import reset_normalization_counters as _rsc
            _h = _gnh()
            log.info(
                "[SymbolNormalizationHealth] symbols_processed=%d symbols_normalized=%d "
                "normalization_rate=%.6f lookup_failures_prevented=%d",
                _h["symbols_processed"], _h["symbols_normalized"],
                _h["normalization_rate"], _h["lookup_failures_prevented"],
            )
            _rsc()
        except Exception as _sym_e:
            log.debug("[SymbolNormalizationHealth] skipped: %s", _sym_e)

        # ── Options OI EOD Summary ─────────────────────────────────────────
        try:
            from data_feeds import get_feed_manager as _get_fm_ois
            _fm_ois  = _get_fm_ois()
            _ois_syms = ["NIFTY", "BANKNIFTY"]
            _ois_checked = 0
            _ois_with_oi = 0
            _ois_without_oi = 0
            _ois_pcr_vals: list = []
            _ois_fail_reasons: list = []
            for _ois_sym in _ois_syms:
                _ois_st  = getattr(_fm_ois, "_options_chain_state", {}).get(_ois_sym, {})
                _ois_ch  = _ois_st.get("chain")
                _ois_checked += 1
                if _ois_ch is None:
                    _ois_without_oi += 1
                    _ois_fail_reasons.append(f"{_ois_sym}:NO_CHAIN")
                    continue
                _ois_toi = _ois_ch.total_oi or 0
                if _ois_toi > 0:
                    _ois_with_oi += 1
                else:
                    _ois_without_oi += 1
                    # determine why: are any contracts non-zero?
                    _sample_c = next((c for c in _ois_ch.contracts if (c.oi or 0) > 0), None)
                    _ois_fail_reasons.append(
                        f"{_ois_sym}:ZERO_TOTAL_OI_but_contract_oi_nonzero={_sample_c is not None}"
                    )
                if _ois_ch.pcr:
                    _ois_pcr_vals.append(_ois_ch.pcr)
            _avg_pcr_ois  = sum(_ois_pcr_vals) / len(_ois_pcr_vals) if _ois_pcr_vals else 0.0
            _dom_fail_ois = _ois_fail_reasons[0] if _ois_fail_reasons else "NONE"
            log.info(
                "[OptionsOISummary] chains_checked=%d chains_with_oi=%d "
                "chains_without_oi=%d avg_pcr=%.4f dominant_failure_reason=%s",
                _ois_checked, _ois_with_oi, _ois_without_oi,
                _avg_pcr_ois, _dom_fail_ois,
            )
        except Exception as _ois_exc:
            log.debug("[OptionsOISummary] skipped: %s", _ois_exc)

        # ── EOD Configuration Integrity Audit ────────────────────────────────
        try:
            from utils.deployment_integrity_auditor import emit_deployment_integrity_audit as _dia_eod
            _dia_eod(context="eod")
        except Exception as _dia_eod_exc:
            log.debug("[DeploymentIntegrityAudit] eod skipped: %s", _dia_eod_exc)

        # ── [ExposureCapSummary] + [LearningOpportunityAudit] + [ExposureCapVerdict] ─
        try:
            from risk_control.capital_risk_engine import (
                get_daily_exposure_rejections as _get_ec_rej,
                _MAX_POSITIONS as _EC_MAX,
            )
            from config import MIN_CONFIDENCE_SCORE as _EC_MIN_CONF

            _ec_rejs = _get_ec_rej()
            _ec_n    = len(_ec_rejs)

            # ── [ExposureCapSummary] ────────────────────────────────────
            if _ec_n > 0:
                _ec_pass_rc  = sum(1 for r in _ec_rejs if r.get("would_pass_risk_control"))
                _ec_pass_sim = sum(1 for r in _ec_rejs if r.get("would_pass_simulation"))
                _ec_pass_deb = sum(1 for r in _ec_rejs if r.get("would_pass_debate"))
                _ec_scores   = [r["score"] for r in _ec_rejs]
                _ec_avg_sc   = round(sum(_ec_scores) / len(_ec_scores), 2)
                _ec_max_sc   = round(max(_ec_scores), 2)
                # Strategy distribution
                _ec_strat_d: dict = {}
                for r in _ec_rejs:
                    s = r.get("strategy", "unknown")
                    _ec_strat_d[s] = _ec_strat_d.get(s, 0) + 1
                # Sector distribution
                _ec_sect_d: dict = {}
                for r in _ec_rejs:
                    s = r.get("sector", "UNKNOWN")
                    _ec_sect_d[s] = _ec_sect_d.get(s, 0) + 1
                log.info(
                    "[ExposureCapSummary] signals_rejected=%d "
                    "signals_would_pass_risk_control=%d signals_would_pass_simulation=%d "
                    "signals_would_pass_debate=%d "
                    "avg_score_rejected=%.2f max_score_rejected=%.2f "
                    "strategy_distribution=%s sector_distribution=%s",
                    _ec_n, _ec_pass_rc, _ec_pass_sim, _ec_pass_deb,
                    _ec_avg_sc, _ec_max_sc,
                    _ec_strat_d, _ec_sect_d,
                )
            else:
                _ec_pass_rc = _ec_pass_sim = _ec_pass_deb = 0
                _ec_avg_sc  = _ec_max_sc = 0.0
                log.info(
                    "[ExposureCapSummary] signals_rejected=0 "
                    "signals_would_pass_risk_control=0 signals_would_pass_simulation=0 "
                    "signals_would_pass_debate=0 avg_score_rejected=0.00 "
                    "max_score_rejected=0.00 strategy_distribution={} sector_distribution={}"
                )

            # ── [LearningOpportunityAudit] ──────────────────────────────
            # Count today's executed trades from paper journal
            _ec_executed = len(trades)
            _ec_total    = _ec_executed + _ec_n
            _ec_loss_pct = round(_ec_n / _ec_total * 100, 1) if _ec_total > 0 else 0.0
            log.info(
                "[LearningOpportunityAudit] executed_trades=%d blocked_trades=%d "
                "learning_samples_generated=%d learning_samples_lost=%d "
                "estimated_learning_loss_pct=%.1f",
                _ec_executed, _ec_n,
                _ec_executed, _ec_n,
                _ec_loss_pct,
            )

            # ── [ExposureCapVerdict] ────────────────────────────────────
            _ec_pass_rc_pct = round(_ec_pass_rc / _ec_n * 100, 1) if _ec_n > 0 else 0.0
            if _ec_n < 3:
                _ec_verdict = "INSUFFICIENT_EVIDENCE"
                _ec_reason  = (
                    f"Only {_ec_n} EXPOSURE_CAP rejection(s) today — "
                    f"need >=3 for statistical verdict"
                )
            elif _ec_avg_sc < _EC_MIN_CONF:
                _ec_verdict = "EXPOSURE_CAP_HEALTHY"
                _ec_reason  = (
                    f"avg_score_rejected={_ec_avg_sc:.2f} < "
                    f"MIN_CONFIDENCE_SCORE={_EC_MIN_CONF} — "
                    f"rejected signals were below execution quality threshold; "
                    f"{_ec_pass_rc}/{_ec_n} projected to pass risk_control"
                )
            elif _ec_pass_rc_pct >= 50.0 and _ec_loss_pct >= 40.0:
                _ec_verdict = "EXPOSURE_CAP_TOO_RESTRICTIVE"
                _ec_reason  = (
                    f"avg_score_rejected={_ec_avg_sc:.2f} >= {_EC_MIN_CONF}; "
                    f"{_ec_pass_rc_pct:.0f}% projected to pass risk_control; "
                    f"estimated_learning_loss_pct={_ec_loss_pct:.1f}% — "
                    f"cap is blocking high-quality signals"
                )
            else:
                _ec_verdict = "INSUFFICIENT_EVIDENCE"
                _ec_reason  = (
                    f"avg_score={_ec_avg_sc:.2f} would_pass_rc={_ec_pass_rc_pct:.0f}% "
                    f"learning_loss={_ec_loss_pct:.1f}% — mixed evidence, "
                    f"need higher would_pass_rc_pct (>=50%) AND learning_loss (>=40%) "
                    f"to confirm restrictive"
                )
            log.info(
                "[ExposureCapVerdict] verdict=%s reason=\"%s\"",
                _ec_verdict, _ec_reason,
            )
        except Exception as _ec_eod_exc:
            log.debug("[ExposureCapSummary] EOD audit skipped: %s", _ec_eod_exc)

        # ── [ReplacementSummary] + [ReplacementVerdict] ────────────────────────
        try:
            _reset_replacement_accumulator()
            _rep_n      = len(_REPLACEMENT_DAILY_AUDIT)
            _rep_cands  = sum(1 for r in _REPLACEMENT_DAILY_AUDIT if r.get("candidate"))
            _rep_elig   = sum(1 for r in _REPLACEMENT_DAILY_AUDIT if r.get("eligible"))
            # replacement_triggered is always 0 — CRE does not call _smart_swap_check
            _rep_triggered = 0
            # higher_quality = eligible (score_delta passed AND rr >= 1.5)
            _rep_hq     = _rep_elig
            _rep_deltas = [r["score_delta"] for r in _REPLACEMENT_DAILY_AUDIT
                           if "score_delta" in r]
            _rep_avg_d  = round(sum(_rep_deltas) / len(_rep_deltas), 2) if _rep_deltas else 0.0
            _rep_max_d  = round(max(_rep_deltas), 2) if _rep_deltas else 0.0

            # Dominant rejection reason across all per-signal audits
            _rep_rej_counts: dict = {}
            for r in _REPLACEMENT_DAILY_AUDIT:
                _rr = r.get("rej_reason", "UNKNOWN")
                _rep_rej_counts[_rr] = _rep_rej_counts.get(_rr, 0) + 1
            _rep_dom_rej = (max(_rep_rej_counts, key=_rep_rej_counts.get)
                            if _rep_rej_counts else "NONE")

            log.info(
                "[ReplacementSummary] exposure_rejections=%d "
                "replacement_candidates=%d replacement_eligible=%d "
                "replacement_triggered=%d higher_quality_signals_rejected=%d "
                "avg_score_delta=%.2f max_score_delta=%.2f "
                "dominant_rejection_reason=%s",
                _rep_n, _rep_cands, _rep_elig,
                _rep_triggered, _rep_hq,
                _rep_avg_d, _rep_max_d,
                _rep_dom_rej,
            )

            # ── [ReplacementVerdict] ────────────────────────────────────
            if _rep_n == 0:
                _rep_verdict = "NO_REPLACEMENT_OPPORTUNITIES_FOUND"
                _rep_reason  = "No heat-rejected signals recorded today"
            elif _rep_elig == 0 and _rep_cands == 0:
                _rep_verdict = "REPLACEMENT_WORKING"
                _rep_reason  = (
                    f"{_rep_n} rejected signals; no evictable positions found "
                    f"(all positions fresh/winning) — cap is working correctly"
                )
            elif _rep_elig == 0 and _rep_cands > 0:
                _rep_verdict = "REPLACEMENT_TOO_STRICT"
                _rep_reason  = (
                    f"{_rep_cands}/{_rep_n} rejections had an evictable candidate "
                    f"but none passed score_delta >= 0.5 or rr >= 1.5 threshold; "
                    f"avg_score_delta={_rep_avg_d:.2f} max_score_delta={_rep_max_d:.2f}"
                )
            elif _rep_elig > 0 and _rep_triggered == 0:
                _rep_verdict = "REPLACEMENT_NOT_TRIGGERING"
                _rep_reason  = (
                    f"{_rep_elig}/{_rep_n} rejected signals met replacement eligibility "
                    f"(score_delta >= 0.5 and rr >= 1.5) but replacement_triggered=0 — "
                    f"CRE rejects at layer 3.5 before order_manager._smart_swap_check "
                    f"is reachable at layer 11; dominant_rej={_rep_dom_rej}"
                )
            else:
                _rep_verdict = "REPLACEMENT_WORKING"
                _rep_reason  = (
                    f"triggered={_rep_triggered} eligible={_rep_elig} "
                    f"candidates={_rep_cands} total_rejections={_rep_n}"
                )
            log.info(
                "[ReplacementVerdict] verdict=%s reason=\"%s\"",
                _rep_verdict, _rep_reason,
            )
        except Exception as _rep_eod_exc:
            log.debug("[ReplacementSummary] EOD audit skipped: %s", _rep_eod_exc)

        # ── [BorderlineOutcome] + [BorderlineConfidenceSummary] + [BorderlineConfidenceVerdict]
        try:
            import json as _json_bv
            from pathlib import Path as _Path_bv
            from datetime import datetime as _dt_bv
            from data_feeds.data_feed_manager import get_feed_manager as _get_feed_bv

            _bl_path_bv = _Path_bv("/app/data") if _Path_bv("/app/data").exists() \
                else _Path_bv(__file__).resolve().parents[1] / "data"
            _bl_file_bv = _bl_path_bv / "borderline_rejections.json"

            if _bl_file_bv.exists():
                _bl_data: list = _json_bv.loads(_bl_file_bv.read_text(encoding="utf-8"))
                _today_bv = _dt_bv.now().strftime("%Y-%m-%d")
                _feed_bv = _get_feed_bv()
                _changed = False

                for _entry in _bl_data:
                    try:
                        _rej_date = _dt_bv.strptime(_entry["rejection_date"], "%Y-%m-%d")
                        _days_elapsed = (_dt_bv.now() - _rej_date).days
                        _sym = _entry["symbol"]

                        # Fill price slots as days elapse
                        if _days_elapsed >= 1 and _entry.get("day1_price") is None:
                            _q = _feed_bv.get_quote(_sym)
                            if _q and getattr(_q, "ltp", None):
                                _entry["day1_price"] = float(_q.ltp)
                                _changed = True
                        if _days_elapsed >= 3 and _entry.get("day3_price") is None:
                            _q = _feed_bv.get_quote(_sym)
                            if _q and getattr(_q, "ltp", None):
                                _entry["day3_price"] = float(_q.ltp)
                                _changed = True
                        if _days_elapsed >= 5 and _entry.get("day5_price") is None:
                            _q = _feed_bv.get_quote(_sym)
                            if _q and getattr(_q, "ltp", None):
                                _entry["day5_price"] = float(_q.ltp)
                                _changed = True

                        # Emit [BorderlineOutcome] for signals with day5 filled
                        if _entry.get("day5_price") is not None:
                            _ep  = float(_entry["entry_price"])
                            _sl  = float(_entry["stop_loss"])
                            _dir = str(_entry.get("direction", "BUY")).upper()
                            _p1  = _entry.get("day1_price")
                            _p3  = _entry.get("day3_price")
                            _p5  = _entry["day5_price"]
                            _prices = [p for p in [_p1, _p3, _p5] if p is not None]
                            _risk = abs(_ep - _sl) if abs(_ep - _sl) > 0 else 1.0
                            if _dir == "SELL" or _dir == "SHORT":
                                _max_fav = _ep - min(_prices) if _prices else 0.0
                                _max_adv = max(_prices) - _ep if _prices else 0.0
                                _shadow_r = (_ep - _p5) / _risk
                            else:
                                _max_fav = max(_prices) - _ep if _prices else 0.0
                                _max_adv = _ep - min(_prices) if _prices else 0.0
                                _shadow_r = (_p5 - _ep) / _risk
                            log.info(
                                "[BorderlineOutcome] symbol=%s entry_price=%.2f "
                                "price_after_1_day=%s price_after_3_days=%s price_after_5_days=%.2f "
                                "max_favorable_move=%.2f max_adverse_move=%.2f shadow_R=%.2f",
                                _sym, _ep,
                                f"{_p1:.2f}" if _p1 else "N/A",
                                f"{_p3:.2f}" if _p3 else "N/A",
                                _p5, _max_fav, _max_adv, _shadow_r,
                            )
                    except Exception as _bv_row_exc:
                        log.debug("[BorderlineOutcome] row error %s: %s", _entry.get("symbol"), _bv_row_exc)

                if _changed:
                    _bl_file_bv.write_text(_json_bv.dumps(_bl_data, indent=2), encoding="utf-8")

                # ── [BorderlineConfidenceSummary] ─────────────────────────
                _bl_today = [e for e in _bl_data if e.get("rejection_date") == _today_bv]
                _bl_with_outcome = [
                    e for e in _bl_data if e.get("day5_price") is not None
                ]
                _n_rej = len(_bl_today)
                _avg_conf = (sum(e["confidence"] for e in _bl_today) / _n_rej) if _n_rej else 0.0
                _avg_rr   = (sum(e["rr_ratio"] for e in _bl_today) / _n_rej)   if _n_rej else 0.0

                # Shadow win rate: direction-adjusted R > 0 = win
                _shadow_results = []
                for _e in _bl_with_outcome:
                    try:
                        _ep  = float(_e["entry_price"])
                        _sl  = float(_e["stop_loss"])
                        _p5  = float(_e["day5_price"])
                        _dir = str(_e.get("direction", "BUY")).upper()
                        _risk = abs(_ep - _sl) if abs(_ep - _sl) > 0 else 1.0
                        _r = (_ep - _p5) / _risk if _dir in ("SELL", "SHORT") else (_p5 - _ep) / _risk
                        _shadow_results.append(_r)
                    except Exception:
                        pass
                _shadow_win_rate = (sum(1 for r in _shadow_results if r > 0) / len(_shadow_results)) if _shadow_results else 0.0
                _avg_shadow_r    = (sum(_shadow_results) / len(_shadow_results)) if _shadow_results else 0.0

                log.info(
                    "[BorderlineConfidenceSummary] signals_rejected=%d avg_confidence=%.2f "
                    "avg_rr=%.2f shadow_win_rate=%.1f%% avg_shadow_R=%.2f "
                    "total_with_outcome=%d",
                    _n_rej, _avg_conf, _avg_rr,
                    _shadow_win_rate * 100, _avg_shadow_r,
                    len(_bl_with_outcome),
                )

                # ── [BorderlineConfidenceVerdict] ─────────────────────────
                if len(_bl_with_outcome) < 5:
                    _bl_verdict = "INSUFFICIENT_EVIDENCE"
                    _bl_reason  = f"only {len(_bl_with_outcome)} completed outcome(s) — need >= 5"
                elif _shadow_win_rate >= 0.50 and _avg_shadow_r >= 0.5:
                    _bl_verdict = "CONFIDENCE_FLOOR_TOO_HIGH"
                    _bl_reason  = (
                        f"shadow_win_rate={_shadow_win_rate:.0%} avg_shadow_R={_avg_shadow_r:.2f} "
                        f"-- borderline signals are profitable above threshold"
                    )
                else:
                    _bl_verdict = "CONFIDENCE_FLOOR_HEALTHY"
                    _bl_reason  = (
                        f"shadow_win_rate={_shadow_win_rate:.0%} avg_shadow_R={_avg_shadow_r:.2f} "
                        f"-- below breakeven; floor is justified"
                    )
                log.info(
                    "[BorderlineConfidenceVerdict] verdict=%s reason=\"%s\"",
                    _bl_verdict, _bl_reason,
                )

        except Exception as _bl_eod_exc:
            log.debug("[BorderlineConfidenceSummary] EOD audit skipped: %s", _bl_eod_exc)


        # Observability-only: emits [UniverseGenerationAudit], [CandidateFreshnessAudit],
        # [RefreshValidationAudit], [SignalReadinessAudit], [PipelineReadinessAssessment],
        # [SystemReadinessReport]. No behavioral changes. All in try/except.
        try:
            import sqlite3 as _sq3_sra
            from pathlib import Path as _Path_sra
            from datetime import datetime as _dt_sra
            _sra_now     = _dt_sra.now()
            _sra_today   = _sra_now.strftime("%Y-%m-%d")
            _app_root_sra = _Path_sra("/app") if _Path_sra("/app").exists() else _Path_sra(__file__).resolve().parents[1]

            # ── Helpers ──────────────────────────────────────────────────
            def _sra_age_min(ts):
                if not ts:
                    return None
                try:
                    return (_sra_now - _dt_sra.fromisoformat(str(ts).replace("Z", ""))).total_seconds() / 60
                except Exception:
                    return None

            def _sra_open_dbs():
                _d = _app_root_sra / "data"
                return list(_d.glob("*.db")) + list(_d.glob("*.sqlite")) if _d.exists() else []

            def _sra_tables(conn):
                return [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]

            def _sra_query(conn, sql, params=()):
                try:
                    cur = conn.execute(sql, params)
                    cols = [d[0] for d in cur.description]
                    return [dict(zip(cols, row)) for row in cur.fetchall()]
                except Exception:
                    return []

            # ── PHASE 1: Universe Generation ─────────────────────────────
            _sra_univ_candidates  = 0
            _sra_univ_data_ok     = 0
            _sra_univ_data_fail   = 0
            _sra_univ_trigger     = "UNKNOWN"
            _sra_univ_phase       = "UNKNOWN"
            _sra_univ_active      = False
            _sra_univ_last_upd    = "none"
            _sra_univ_sec_cap     = 0
            _sra_univ_score_floor = 0
            _sra_univ_scan_ok     = False

            try:
                import opportunity_engine.equity_scanner_ai as _esm_sra
                _sc = getattr(_esm_sra, "_scanner", getattr(_esm_sra, "_instance", None))
                if _sc is None:
                    # Try to access via orchestrator attribute
                    _sc = getattr(self, "equity_scanner", getattr(self, "_equity_scanner", None))
                if _sc is not None:
                    _sra_univ_phase    = str(getattr(_sc, "phase", getattr(_sc, "_phase", "UNKNOWN")))
                    _sra_univ_active   = bool(getattr(_sc, "prepared_universe_active",
                                                       getattr(_sc, "_prepared_universe_active", False)))
                    _llu = getattr(_sc, "last_level_update", getattr(_sc, "_last_level_update", None))
                    _sra_univ_last_upd = str(_llu) if _llu else "none"
                    _sra_univ_trigger  = "SCHEDULER"
            except Exception:
                pass

            # Query SQLite for today's candidate rows
            for _cdb in _sra_open_dbs():
                try:
                    with _sq3_sra.connect(str(_cdb)) as _cc:
                        for _tbl in _sra_tables(_cc):
                            if any(k in _tbl.lower() for k in ("candidate", "universe", "opportunity")):
                                _rows = _sra_query(_cc, f"SELECT * FROM {_tbl} ORDER BY rowid DESC LIMIT 200")
                                if not _rows:
                                    continue
                                _today_cnt = 0
                                for _r in _rows:
                                    for _tf in ("prepared_at", "created_at", "timestamp"):
                                        if _tf in _r and _r[_tf]:
                                            _am = _sra_age_min(_r[_tf])
                                            if _am is not None and 0 < _am < 1440:
                                                _today_cnt += 1
                                                _sra_univ_trigger = _r.get("trigger_source", "SCHEDULER")
                                            break
                                    _inv_r = str(_r.get("invalidation_reason", "")).upper()
                                    if _inv_r in ("SECTOR_CAP", "SECTOR_CONCENTRATION", "SECTOR_LIMIT"):
                                        _sra_univ_sec_cap += 1
                                    elif _inv_r in ("SCORE_FLOOR", "LOW_SCORE", "BELOW_THRESHOLD"):
                                        _sra_univ_score_floor += 1
                                if _today_cnt > 0:
                                    _sra_univ_candidates = _today_cnt
                                    _sra_univ_data_ok    = _today_cnt
                                    _sra_univ_scan_ok    = True
                                break
                except Exception:
                    pass

            # Fallback: JSON candidate stores
            for _jp in [_app_root_sra / "data" / "prepared_candidates.json",
                        _app_root_sra / "data" / "daily_candidates.json",
                        _app_root_sra / "data" / "candidates.json"]:
                if _jp.exists() and _sra_univ_candidates == 0:
                    try:
                        import json as _json_sra
                        _jd = _json_sra.loads(_jp.read_text())
                        _jl = _jd if isinstance(_jd, list) else list(_jd.values())
                        _sra_univ_candidates = len(_jl)
                        _sra_univ_data_ok    = _sra_univ_candidates
                        _sra_univ_scan_ok    = _sra_univ_candidates > 0
                        _sra_univ_trigger    = "SCHEDULER"
                    except Exception:
                        pass

            _sra_univ_coverage = round(100 * _sra_univ_data_ok / max(_sra_univ_candidates, 1), 1) if _sra_univ_candidates > 0 else 0.0

            log.info(
                "[UniverseGenerationAudit] date=%s scan_executed=%s trigger_source=%s "
                "universe_attempted=%d data_ok=%d data_failed=%d coverage_pct=%.1f%% "
                "sector_cap_removals=%d score_floor_removals=%d final_candidates_written=%d "
                "phase=%s prepared_universe_active=%s last_level_update=%s",
                _sra_today, _sra_univ_scan_ok, _sra_univ_trigger,
                _sra_univ_candidates, _sra_univ_data_ok, _sra_univ_data_fail,
                _sra_univ_coverage, _sra_univ_sec_cap, _sra_univ_score_floor,
                _sra_univ_candidates, _sra_univ_phase, _sra_univ_active,
                _sra_univ_last_upd,
            )

            # ── PHASE 2: Premarket Refinement ─────────────────────────────
            # Inferred from candidate timestamps: if any candidate has a refined_at
            # or prepared_at between 08:00-09:30 today, the refiner ran.
            _sra_pm_ran         = False
            _sra_pm_cands_after = _sra_univ_candidates
            _sra_pm_reason      = "NO_REFINEMENT_RECORD_FOUND"

            for _cdb in _sra_open_dbs():
                try:
                    with _sq3_sra.connect(str(_cdb)) as _cc:
                        for _tbl in _sra_tables(_cc):
                            if any(k in _tbl.lower() for k in ("candidate", "universe", "refine")):
                                _pmrows = _sra_query(
                                    _cc,
                                    f"SELECT * FROM {_tbl} WHERE "
                                    f"COALESCE(refined_at, prepared_at, created_at) >= ? "
                                    f"AND COALESCE(refined_at, prepared_at, created_at) < ? "
                                    f"ORDER BY rowid DESC LIMIT 50",
                                    (_sra_today + " 08:00:00", _sra_today + " 09:30:00"),
                                )
                                if _pmrows:
                                    _sra_pm_ran         = True
                                    _sra_pm_cands_after = len(_pmrows)
                                    _sra_pm_reason      = "REFINEMENT_INFERRED_FROM_DB"
                                    break
                except Exception:
                    pass

            if not _sra_pm_ran:
                if _sra_univ_candidates == 0:
                    _sra_pm_reason = "NO_GAP_DATA"
                elif _sra_now.hour < 8:
                    _sra_pm_reason = "PRE_SCHEDULE"
                else:
                    _sra_pm_reason = "NO_REFINEMENT_REQUIRED"

            log.info(
                "[PremarketReadinessAudit] date=%s refiner_executed=%s "
                "candidates_before=%d candidates_after=%d "
                "no_change_reason=%s",
                _sra_today, _sra_pm_ran,
                _sra_univ_candidates, _sra_pm_cands_after,
                _sra_pm_reason if not _sra_pm_ran else "none",
            )

            # ── PHASE 3: Candidate Freshness ──────────────────────────────
            _sra_cf_count  = 0
            _sra_cf_fresh  = 0
            _sra_cf_expire = 0
            _sra_cf_inval  = 0
            _sra_cf_ages   = []
            _sra_cf_ttl    = 480  # 8h default

            try:
                import config as _cfg_sra
                for _a in ("CANDIDATE_TTL_MINUTES", "UNIVERSE_TTL_MINUTES"):
                    if hasattr(_cfg_sra, _a):
                        _sra_cf_ttl = getattr(_cfg_sra, _a)
                        break
            except Exception:
                pass

            for _cdb in _sra_open_dbs():
                try:
                    with _sq3_sra.connect(str(_cdb)) as _cc:
                        for _tbl in _sra_tables(_cc):
                            if any(k in _tbl.lower() for k in ("candidate", "universe")):
                                _cfrows = _sra_query(_cc, f"SELECT * FROM {_tbl} ORDER BY rowid DESC LIMIT 200")
                                if not _cfrows:
                                    continue
                                for _r in _cfrows:
                                    _ts = None
                                    for _tf in ("prepared_at", "last_refresh_time", "refreshed_at", "created_at"):
                                        if _tf in _r and _r[_tf]:
                                            _ts = _r[_tf]
                                            break
                                    _age_m = _sra_age_min(_ts)
                                    if _age_m is not None:
                                        _sra_cf_ages.append(_age_m)
                                        if _age_m > _sra_cf_ttl:
                                            _sra_cf_expire += 1
                                        else:
                                            _sra_cf_fresh += 1
                                    else:
                                        _sra_cf_fresh += 1
                                    if _r.get("invalidated") or _r.get("is_invalid"):
                                        _sra_cf_inval += 1
                                _sra_cf_count = _sra_cf_fresh + _sra_cf_expire + _sra_cf_inval
                                break
                except Exception:
                    pass

            _sra_cf_avg_age = round(sum(_sra_cf_ages) / len(_sra_cf_ages), 1) if _sra_cf_ages else None
            _sra_cf_max_age = round(max(_sra_cf_ages), 1) if _sra_cf_ages else None

            log.info(
                "[CandidateFreshnessAudit] date=%s candidate_count=%d "
                "fresh=%d expired=%d invalidated=%d "
                "avg_age_minutes=%s oldest_age_minutes=%s ttl_minutes=%d ttl_rejected=%d",
                _sra_today, _sra_cf_count,
                _sra_cf_fresh, _sra_cf_expire, _sra_cf_inval,
                _sra_cf_avg_age, _sra_cf_max_age, _sra_cf_ttl, _sra_cf_expire,
            )

            # ── PHASE 4: Refresh Validation — top-20 before execution ─────
            _sra_rv_refreshed = 0
            _sra_rv_stale     = 0
            _sra_rv_target    = 30  # minutes
            _sra_rv_stale_flag = False

            try:
                import config as _cfg_sra2
                for _a2 in ("CANDIDATE_REFRESH_TARGET_MINUTES", "REFRESH_TARGET_MINUTES",
                            "MAX_CANDIDATE_AGE_MINUTES"):
                    if hasattr(_cfg_sra2, _a2):
                        _sra_rv_target = getattr(_cfg_sra2, _a2)
                        break
            except Exception:
                pass

            for _cdb in _sra_open_dbs():
                try:
                    with _sq3_sra.connect(str(_cdb)) as _cc:
                        for _tbl in _sra_tables(_cc):
                            if any(k in _tbl.lower() for k in ("candidate", "universe")):
                                _rvrows = _sra_query(
                                    _cc,
                                    f"SELECT * FROM {_tbl} ORDER BY "
                                    f"COALESCE(score, composite_score, rank_score, 0) DESC LIMIT 20"
                                )
                                if not _rvrows:
                                    _rvrows = _sra_query(_cc, f"SELECT * FROM {_tbl} LIMIT 20")
                                for _r in _rvrows:
                                    _ts = None
                                    for _tf in ("last_refresh_time", "refreshed_at", "prepared_at"):
                                        if _tf in _r and _r[_tf]:
                                            _ts = _r[_tf]
                                            break
                                    _age_m = _sra_age_min(_ts)
                                    if _age_m is not None and _age_m > _sra_rv_target:
                                        _sra_rv_stale += 1
                                        _sra_rv_stale_flag = True
                                        _sym = _r.get("symbol", _r.get("ticker", "?"))
                                        log.warning(
                                            "[RefreshValidationAudit] STALE symbol=%s "
                                            "age_minutes=%.1f freshness_target_minutes=%d "
                                            "stale_before_execution=True",
                                            _sym, _age_m, _sra_rv_target,
                                        )
                                    else:
                                        _sra_rv_refreshed += 1
                                break
                except Exception:
                    pass

            log.info(
                "[RefreshValidationAudit] date=%s top_n=%d refreshed=%d stale=%d "
                "stale_before_execution=%s freshness_target_minutes=%d",
                _sra_today, _sra_rv_refreshed + _sra_rv_stale,
                _sra_rv_refreshed, _sra_rv_stale,
                _sra_rv_stale_flag, _sra_rv_target,
            )

            # ── PHASE 5: Signal Readiness ──────────────────────────────────
            _sra_trades_today    = 0
            _sra_open_positions  = 0
            _sra_exec_eligible   = 0

            try:
                import csv as _csv_sra
                _cpath = _app_root_sra / "data" / "paper_trades.csv"
                if _cpath.exists():
                    with _cpath.open() as _cf:
                        for _cr in _csv_sra.DictReader(_cf):
                            _cts = _cr.get("timestamp", _cr.get("time", _cr.get("date", "")))
                            if _sra_today in str(_cts):
                                _sra_trades_today += 1
            except Exception:
                pass

            try:
                _positions = getattr(self.order_manager, "_positions",
                                     getattr(self.order_manager, "positions", {}))
                _sra_open_positions = len(_positions)
            except Exception:
                pass

            try:
                _om_stats = getattr(self.order_manager, "get_stats",
                                    getattr(self.order_manager, "stats", None))
                if callable(_om_stats):
                    _st = _om_stats()
                    _sra_exec_eligible = _st.get("execution_eligible",
                                                  _st.get("eligible_signals", 0))
            except Exception:
                pass

            log.info(
                "[SignalReadinessAudit] date=%s prepared_candidates=%d "
                "execution_eligible=%d open_positions=%d trades_today=%d",
                _sra_today, _sra_univ_candidates,
                _sra_exec_eligible, _sra_open_positions, _sra_trades_today,
            )

            # ── PHASE 6: Pipeline Readiness Assessment ─────────────────────
            _sra_blockers    = []
            _sra_dom_blocker = "NONE"
            _sra_sec_blocker = None

            if _sra_univ_candidates == 0:
                _sra_blockers.append("NO_UNIVERSE_CANDIDATES")
            if _sra_cf_expire > _sra_cf_fresh:
                _sra_blockers.append("MAJORITY_CANDIDATES_STALE")
            if _sra_rv_stale_flag:
                _sra_blockers.append(f"STALE_TOP_CANDIDATES_{_sra_rv_stale}")

            try:
                _ca_path = _app_root_sra / "data" / "ca_quarantine.json"
                if _ca_path.exists():
                    import json as _json_sra2
                    _ca = _json_sra2.loads(_ca_path.read_text())
                    _ca_count = len(_ca) if isinstance(_ca, (list, dict)) else 0
                    if _ca_count > 0:
                        _sra_blockers.append(f"CA_QUARANTINE_{_ca_count}_POSITIONS")
            except Exception:
                pass

            # Check daily P&L for risk-guardian trigger
            try:
                _cpath2 = _app_root_sra / "data" / "paper_trades.csv"
                if _cpath2.exists():
                    import csv as _csv_sra2
                    _today_pnl = 0.0
                    with _cpath2.open() as _cf2:
                        for _cr2 in _csv_sra2.DictReader(_cf2):
                            _ts2 = _cr2.get("timestamp", _cr2.get("date", ""))
                            if _sra_today in str(_ts2):
                                try:
                                    _today_pnl += float(_cr2.get("pnl", _cr2.get("realized_pnl", 0)) or 0)
                                except Exception:
                                    pass
                    if _today_pnl < -50000:
                        _sra_blockers.append(f"DAILY_LOSS_LIMIT_pnl={_today_pnl:.0f}")
            except Exception:
                pass

            if _sra_blockers:
                _sra_dom_blocker = _sra_blockers[0]
                _sra_sec_blocker = _sra_blockers[1] if len(_sra_blockers) > 1 else None

            log.info(
                "[PipelineReadinessAssessment] date=%s dominant_blocker=%s "
                "secondary_blocker=%s all_blockers=%s open_positions=%d trades_today=%d",
                _sra_today, _sra_dom_blocker, _sra_sec_blocker,
                _sra_blockers, _sra_open_positions, _sra_trades_today,
            )

            # ── PHASE 7: System Readiness Report (Final Score) ─────────────
            _sra_score_univ   = 100 if _sra_univ_candidates >= 10 else (50 if _sra_univ_candidates > 0 else 0)
            _sra_score_pm     = 100 if _sra_pm_ran else (100 if _sra_now.hour < 8 else 20)
            _sra_cf_total     = max(_sra_cf_fresh + _sra_cf_expire + _sra_cf_inval, 1)
            _sra_score_fresh  = int(100 * _sra_cf_fresh / _sra_cf_total) if _sra_cf_count > 0 else 0
            _sra_rv_total     = max(_sra_rv_refreshed + _sra_rv_stale, 1)
            _sra_score_refr   = int(100 * _sra_rv_refreshed / _sra_rv_total) if (_sra_rv_refreshed + _sra_rv_stale) > 0 else (0 if _sra_univ_candidates > 0 else 50)
            _sra_score_sig    = 100 if _sra_trades_today > 0 else (70 if _sra_open_positions > 0 else (30 if _sra_univ_candidates > 0 else 0))
            _sra_score_exec   = max(0, 100 - len(_sra_blockers) * 20)
            _sra_overall      = (_sra_score_univ + _sra_score_pm + _sra_score_fresh + _sra_score_refr + _sra_score_sig + _sra_score_exec) // 6
            _sra_status       = "READY" if _sra_overall >= 75 else ("PARTIAL" if _sra_overall >= 45 else "NOT_READY")
            _sra_reco         = "SYSTEM_HEALTHY" if _sra_overall >= 75 else ("MONITOR" if _sra_overall >= 45 else "ACTION_REQUIRED")

            log.info(
                "[SystemReadinessReport] date=%s "
                "universe_generation=%d premarket_refinement=%d candidate_freshness=%d "
                "refresh_health=%d signal_readiness=%d execution_readiness=%d "
                "overall=%d overall_status=%s recommendation=%s",
                _sra_today,
                _sra_score_univ, _sra_score_pm, _sra_score_fresh,
                _sra_score_refr, _sra_score_sig, _sra_score_exec,
                _sra_overall, _sra_status, _sra_reco,
            )

        except Exception as _sra_exc:
            log.debug("[SystemReadinessAudit] EOD phase skipped: %s", _sra_exc)

        # ── Phase 7: Re-entry audit summary ───────────────────────────────
        try:
            _reentry_events = self.order_manager.get_reentry_summary()
            _re_count  = len(_reentry_events)
            _re_same   = sum(1 for e in _reentry_events if e.get("same_direction"))
            _re_opp    = _re_count - _re_same
            _re_fast   = sum(1 for e in _reentry_events if e.get("gap_seconds", 9999) < 1800)
            log.info(
                "[ReEntrySummary] count=%d same_dir=%d opposite_dir=%d "
                "rapid_reentry_under30min=%d",
                _re_count, _re_same, _re_opp, _re_fast,
            )
        except Exception as _re_exc:
            log.debug("[EOD] ReEntrySummary failed: %s", _re_exc)

        # Print end-of-day diagnostics
        self.bus.print_stats()
        self.task_queue.print_stats()

        # V2.5: Shadow audit summary — decision-gate verdict for the day
        try:
            from opportunity_engine.delta_refresh_shadow import log_shadow_audit_summary as _lsas
            _lsas()
        except Exception as _shadow_exc:
            log.debug("[ShadowAuditSummary] Skipped: %s", _shadow_exc)

        # ── Patch 8: Prepared Universe Audit (shadow validation report) ───────
        # Compares today's prepared candidates vs actually-traded symbols.
        # Emits [PreparedUniverseAudit] — the primary activation-readiness report.
        # Always runs (even when USE_PREPARED_UNIVERSE=False) so shadow data
        # accumulates before activation.
        try:
            self._run_prepared_universe_audit(trades)
        except Exception as _audit_exc:
            log.debug("[PreparedUniverseAudit] Skipped: %s", _audit_exc)

        # ── Section 5: Exploration Performance Audit (EOD) ───────────────────
        # Emits [ExplorationAudit] — primary calibration telemetry for deciding
        # when to increase EXPLORATION_BUDGET_PCT beyond the soft-activation 3%.
        try:
            self._run_exploration_audit(trades)
        except Exception as _exp_exc:
            log.debug("[ExplorationAudit] Skipped: %s", _exp_exc)

        # ── Section 6: Daily Pipeline Forensic Summary (EOD) ────────────────
        # Emits [PipelineForensicSummary] — master daily observability report.
        # Purely observational, no behavioral mutation.
        try:
            from control_tower.pipeline_forensic_reporter import get_forensic_reporter as _gfr
            _gfr().emit_daily_summary()
        except Exception as _frs_exc:
            log.debug("[PipelineForensicSummary] Skipped: %s", _frs_exc)

        # ── Priority 7 (TelemetryCoverageAudit): meta-audit of all audit modules ──
        # Probes all 6 Forensic Refinement audit modules, reports coverage,
        # warns on dark (zero-activity) modules, and calls emit_eod_report()
        # on each — so all EOD forensic summaries fire from this single call.
        try:
            from control_tower.telemetry_coverage_audit import (
                get_telemetry_coverage_audit as _gtca,
            )
            _gtca().emit_coverage_report()
        except Exception as _tca_exc:
            log.debug("[TelemetryCoverageAudit] Skipped: %s", _tca_exc)

        # ── InvalidationEffectivenessReport: 5-section EOD invalidation summary ──
        # Crosses persistent invalidation_state.json with current store to
        # classify genuine vs feed-induced, recovery rates, and recurring symbols.
        try:
            from opportunity_engine.invalidation_tracker import get_invalidation_tracker as _git_eod
            _git_eod().emit_session_summary()
        except Exception as _inv_eod_exc:
            log.debug("[InvalidationEffectivenessReport] Skipped: %s", _inv_eod_exc)

        # ── OIOS market_leaders_daily — top winner/loser capture ─────────────
        # Captures top-15 winners and top-15 losers from the active universe.
        # Source: ohlcv_daily (populated by existing Phase A data feeds).
        # Non-critical: failure does not affect EOD learning or notifications.
        try:
            from oios.db.connection import get_connection as _ml_oios_conn
            from oios.phase_f.leader_capture import capture_daily_leaders as _cap_leaders
            _ml_date = datetime.now().strftime("%Y-%m-%d")
            _ml_regime = "unknown"
            if self._last_snapshot is not None:
                _snap_r2 = self._last_snapshot.regime
                _ml_regime = (
                    _snap_r2.value if hasattr(_snap_r2, "value") else str(_snap_r2)
                ) or "unknown"
            with _ml_oios_conn() as _ml_conn:
                _ml_leaders = _cap_leaders(_ml_date, _ml_conn, regime=_ml_regime)
            log.info(
                "[OIOS] market_leaders_daily: captured=%d date=%s regime=%s",
                len(_ml_leaders), _ml_date, _ml_regime,
            )
        except Exception as _ml_exc:
            log.warning("[OIOS] market_leaders_daily capture failed (non-critical): %s", _ml_exc)

    # ──────────────────────────────────────────────────────────────────
    # PATCH 8 — SHADOW MODE VALIDATION / PREPARED UNIVERSE AUDIT
    # ──────────────────────────────────────────────────────────────────

    def _run_prepared_universe_audit(self, trades: list) -> None:
        """
        Patch 8 — EOD prepared-universe audit.

        Compares:
          - Today's prepared candidates (from daily_candidates.json)
          - Actually-selected trade symbols (from closed + open orders today)
          - Missed opportunities (prepared but not traded)
          - Exploration catches (traded but NOT in prepared list)
          - Score distribution of prepared vs selected
          - Concentration metrics

        Emits [PreparedUniverseAudit] — the primary activation-readiness report.
        This report becomes the signal to enable USE_PREPARED_UNIVERSE=True when
        overlap ≥ 50% and missed_rate is stable over 5+ sessions.

        Telemetry only — no behavioral mutation.
        """
        try:
            from opportunity_engine.candidate_store import CandidateStore
        except ImportError:
            return

        candidates = CandidateStore.read()
        if not candidates:
            log.info("[PreparedUniverseAudit] No candidate store available — audit skipped.")
            return

        prepared_syms = {c["symbol"] for c in candidates}

        # Traded symbols today
        traded_syms: set = set()
        for t in trades:
            sym = getattr(t, "symbol", None)
            if sym:
                traded_syms.add(sym)
        # Also include open orders
        try:
            for o in self.order_manager.get_open_orders():
                sym = getattr(o, "symbol", getattr(o, "tradingsymbol", None))
                if sym:
                    traded_syms.add(sym.replace(".NS", ""))
        except Exception:
            pass

        # Metrics
        overlap_syms     = prepared_syms & traded_syms
        missed_syms      = prepared_syms - traded_syms
        exploration_syms = traded_syms - prepared_syms

        overlap_count     = len(overlap_syms)
        prepared_count    = len(prepared_syms)
        missed_count      = len(missed_syms)
        exploration_count = len(exploration_syms)
        traded_count      = len(traded_syms)

        overlap_pct  = round(overlap_count / traded_count * 100, 1) if traded_count else 0.0
        missed_pct   = round(missed_count  / prepared_count * 100, 1) if prepared_count else 0.0
        explore_pct  = round(exploration_count / max(traded_count, 1) * 100, 1)

        # Score distribution of prepared candidates
        scores  = [c.get("score", 0.0) for c in candidates]
        avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
        min_score = round(min(scores), 3) if scores else 0.0
        max_score = round(max(scores), 3) if scores else 0.0

        # Sector distribution of missed candidates
        sector_missed: dict = {}
        for c in candidates:
            if c["symbol"] in missed_syms:
                sec = c.get("sector", "UNKNOWN")
                sector_missed[sec] = sector_missed.get(sec, 0) + 1

        # Premarket completion status
        premarket_complete = False
        try:
            import json as _json
            from opportunity_engine.candidate_store import STORE_FILE
            if STORE_FILE.exists():
                _p = _json.loads(STORE_FILE.read_text(encoding="utf-8"))
                premarket_complete = bool(_p.get("premarket_refresh_complete", False))
        except Exception:
            pass

        log.info(
            "[PreparedUniverseAudit]"
            " date=%s"
            " prepared=%d"
            " traded=%d"
            " overlap=%d(%.1f%%)"
            " missed=%d(%.1f%%)"
            " exploration_catches=%d(%.1f%%)"
            " score_avg=%.3f score_min=%.3f score_max=%.3f"
            " premarket_complete=%s"
            " top_missed_sectors=%s",
            datetime.now().strftime("%Y-%m-%d"),
            prepared_count,
            traded_count,
            overlap_count, overlap_pct,
            missed_count, missed_pct,
            exploration_count, explore_pct,
            avg_score, min_score, max_score,
            premarket_complete,
            str(sorted(sector_missed.items(), key=lambda x: -x[1])[:5]),
        )

        # Readiness signal: ≥50% overlap for 5+ sessions → ready to enable
        if overlap_pct >= 50.0 and traded_count >= 3:
            log.info(
                "[PreparedUniverseAudit] READINESS_SIGNAL overlap=%.1f%% >= 50%%"
                " — consider enabling USE_PREPARED_UNIVERSE=True after 5+ consistent sessions.",
                overlap_pct,
            )
        elif overlap_pct < 30.0 and traded_count >= 3:
            log.info(
                "[PreparedUniverseAudit] LOW_OVERLAP overlap=%.1f%% < 30%%"
                " — scanner may be targeting wrong regime; review [PreparedUniverseStats].",
                overlap_pct,
            )

    def _run_exploration_audit(self, trades: list) -> None:
        """
        Section 5 — EOD exploration performance audit.

        Emits [ExplorationAudit] using:
          - Session counters from equity_scanner_ai._EXPLORE_STATS
          - Closed trades tagged [EXPLORATORY] in entry_label

        This is the primary calibration telemetry for EXPLORATION_BUDGET_PCT
        progression (3→5→8→10). Never raises.
        """
        try:
            from opportunity_engine.equity_scanner_ai import get_session_exploration_stats
            stats = get_session_exploration_stats()
        except Exception:
            stats = {}

        evaluated         = stats.get("evaluated", 0)
        signals_generated = stats.get("signals_generated", 0)

        # Identify exploration trades from today's closed trades
        explore_trades = []
        prepared_trades = []
        for t in trades:
            lbl = getattr(t, "entry_label", "") or ""
            if "[EXPLORATORY]" in lbl:
                explore_trades.append(t)
            else:
                prepared_trades.append(t)

        executed = len(explore_trades)

        # Win/loss and avg_r from exploration trades
        wins = 0
        total_r = 0.0
        for t in explore_trades:
            pnl  = getattr(t, "pnl", None)
            risk = getattr(t, "risk_amount", None)
            if pnl is not None:
                if pnl > 0:
                    wins += 1
                if risk and risk > 0:
                    total_r += pnl / risk

        wr    = round(wins / executed * 100, 1) if executed else 0.0
        avg_r = round(total_r / executed, 2) if executed else 0.0

        # False positive rate: signals generated but not executed
        false_pos_rate = round(
            (signals_generated - executed) / max(signals_generated, 1), 3
        )

        # Missed prepared equivalents: prepared candidates in today's store
        # that match symbols the exploration found — overlap shows redundancy
        missed_prepared_equiv = 0
        try:
            from opportunity_engine.candidate_store import CandidateStore
            candidates = CandidateStore.read() or []
            prepared_syms = {c["symbol"] for c in candidates}
            explore_syms  = {getattr(t, "symbol", "") for t in explore_trades}
            missed_prepared_equiv = len(explore_syms & prepared_syms)
        except Exception:
            pass

        log.info(
            "[ExplorationAudit]"
            " date=%s"
            " evaluated=%d"
            " signals_generated=%d"
            " executed=%d"
            " wr=%.1f"
            " avg_r=%.2f"
            " false_positive_rate=%.3f"
            " missed_prepared_equivalents=%d"
            " prepared_trades_today=%d",
            datetime.now().strftime("%Y-%m-%d"),
            evaluated,
            signals_generated,
            executed,
            wr,
            avg_r,
            false_pos_rate,
            missed_prepared_equiv,
            len(prepared_trades),
        )

        # Budget progression hint
        if executed >= 3 and wr >= 60.0 and false_pos_rate <= 0.15:
            log.info(
                "[ExplorationAudit] BUDGET_INCREASE_ELIGIBLE"
                " wr=%.1f avg_r=%.2f false_pos=%.3f"
                " — review 10+ sessions before increasing EXPLORATION_BUDGET_PCT",
                wr, avg_r, false_pos_rate,
            )

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

        # ── Fix 2: S/R level auto-validation ─────────────────────────
        # Detects and repairs any resistance<LTP or support>LTP entries
        # using ATR(14)-anchored levels fetched from yfinance.
        try:
            from opportunity_engine.equity_scanner_ai import validate_and_refresh_sr_levels
            _sr_result = validate_and_refresh_sr_levels()
            if _sr_result["repaired"] > 0:
                log.warning(
                    "  ⚠️  S/R levels repaired: %d/%d symbols had broken levels — rebuilt with ATR(14).",
                    _sr_result["repaired"], _sr_result["total"],
                )
                try:
                    from notifications import get_notifier
                    get_notifier().market_alert(
                        "🔧 S/R Levels Auto-Repaired",
                        f"{_sr_result['repaired']} symbol(s) had stale resistance/support "
                        f"levels.\nRepaired: {_sr_result['broken_symbols']}\n"
                        f"ATR-anchored levels applied — levels are now valid.",
                    )
                except Exception:
                    pass
            else:
                log.info("  ✅ S/R levels valid — no repair needed.")
        except Exception as _sr_exc:
            log.warning("  ⚠️  S/R level validation failed: %s", _sr_exc)

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

        # ── Fix 3: Prepared universe freshness check ─────────────────
        # If daily_candidates.json is missing or from a previous day,
        # trigger Phase D scanner now so first cycle has fresh candidates.
        try:
            import json as _json
            from pathlib import Path as _Path
            from datetime import date as _date
            _cand_path = _Path("data/daily_candidates.json")
            _needs_scan = False
            if not _cand_path.exists():
                log.warning("  ⚠️  daily_candidates.json missing — triggering Phase D scan.")
                _needs_scan = True
            else:
                _mtime = _date.fromtimestamp(_cand_path.stat().st_mtime)
                if _mtime < _date.today():
                    log.warning(
                        "  ⚠️  daily_candidates.json is stale (last updated %s) — triggering Phase D scan.",
                        _mtime,
                    )
                    _needs_scan = True
                else:
                    _cand_data = _json.loads(_cand_path.read_text())
                    _n_cands   = len(_cand_data.get("candidates", []))
                    log.info("  ✅ Prepared universe fresh: %d candidates.", _n_cands)
            if _needs_scan:
                import threading as _threading
                _t = _threading.Thread(
                    target=self._run_post_market_scan,
                    daemon=True, name="PremarketPhaseD",
                )
                _t.start()
                log.info("  Phase D scanner triggered in background thread.")
        except Exception as _cand_exc:
            log.warning("  ⚠️  Candidate freshness check failed: %s", _cand_exc)

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

    def _run_oios_weekly_research(self) -> None:
        """
        OIOS Phase F weekly differential research pipeline — runs on Saturday.

        For each trading day in the past 7 calendar days that has
        market_leaders_daily rows, runs in sequence:
          1. feature_extractor.extract_features_batch()
          2. control_population.build_controls_for_date()
          3. differential_engine.compute_differentials()

        Day-of-week guard: returns immediately on non-Saturday days.
        Non-critical: failure does not affect trading engine or positions.
        """
        from datetime import timedelta
        if datetime.now().weekday() != 5:   # 5 = Saturday
            return
        log.info("[OIOS] Saturday Phase F weekly research pipeline starting.")
        try:
            from oios.db.connection import get_connection as _wk_oios_conn
            from oios.phase_f import feature_extractor as _wk_fe
            from oios.phase_f import control_population as _wk_cp
            from oios.phase_f import differential_engine as _wk_de
            _wk_today = datetime.now().date()
            _wk_processed = 0
            with _wk_oios_conn() as _wk_conn:
                for _wk_delta in range(7):
                    _wk_td = (_wk_today - timedelta(days=_wk_delta)).isoformat()
                    _wk_n_leaders = _wk_conn.execute(
                        "SELECT COUNT(*) FROM market_leaders_daily WHERE trade_date=?",
                        (_wk_td,),
                    ).fetchone()[0]
                    if _wk_n_leaders == 0:
                        continue
                    _wk_leaders = [
                        dict(r) for r in _wk_conn.execute(
                            "SELECT leader_id, symbol, trade_date, sector "
                            "FROM market_leaders_daily WHERE trade_date=?",
                            (_wk_td,),
                        ).fetchall()
                    ]
                    _wk_fe.extract_features_batch(_wk_leaders, _wk_conn)
                    _wk_cp.build_controls_for_date(_wk_td, _wk_conn)
                    _wk_n_diff = _wk_de.compute_differentials(_wk_td, _wk_conn)
                    log.info(
                        "[OIOS] Differential research %s: leaders=%d diffs=%d",
                        _wk_td, _wk_n_leaders, _wk_n_diff,
                    )
                    _wk_processed += 1
            log.info("[OIOS] Weekly research complete: %d trading day(s) processed.", _wk_processed)
        except Exception as _wk_exc:
            log.warning("[OIOS] Weekly research failed (non-critical): %s", _wk_exc)

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

        # ── Startup CSV orphan audit ────────────────────────────────
        # Detects any position in paper_trades.csv as OPEN-without-CLOSE
        # that is NOT tracked by order_manager — fires Telegram alert.
        self._startup_csv_orphan_audit()

        # ── Pre-market ─────────────────────────────────────────────────
        sched_lib.every().day.at("08:00").do(self._premarket_init)
        sched_lib.every().day.at("08:30").do(self._premarket_data_warmup)

        # ── Phase 8: GlobalDataAI pre-open force-refreshes ─────────────
        def _global_prewarm():
            try:
                self.global_intelligence.data_ai.fetch(force=True)
                log.info("[Orchestrator] GlobalDataAI pre-open prewarm complete.")
            except Exception as _pw_exc:
                log.warning("[Orchestrator] GlobalDataAI prewarm failed: %s", _pw_exc)
        sched_lib.every().day.at("08:45").do(_global_prewarm)
        sched_lib.every().day.at("09:00").do(_global_prewarm)
        sched_lib.every().day.at("09:10").do(_global_prewarm)

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

        # ── Post-market deep scan (Phase D) — 16:45 IST ───────────────
        sched_lib.every().day.at(SCHEDULE["post_market_scan"]).do(self._run_post_market_scan)

        # ── Pre-market refiner (Phase G) — 08:45 IST ──────────────────
        sched_lib.every().day.at(SCHEDULE["premarket_refiner"]).do(self._run_premarket_refiner)

        # ── Fix 1: Intraday candidate TTL refresh — 11:30 and 13:30 IST ──────
        # Re-validates expired prepared candidates against live LTPs.
        # Extends TTL by 4h for setups that are still structurally intact.
        sched_lib.every().day.at("11:30").do(
            lambda: self._run_intraday_refresh("mid_session")
        )
        sched_lib.every().day.at("13:30").do(
            lambda: self._run_intraday_refresh("afternoon")
        )

        # ── Fix 7: Weekly nifty500_universe.json rebuild — Monday 08:30 IST ──
        # Keeps the Phase D scanner's source pool fresh on a weekly cadence.
        sched_lib.every().day.at("08:30").do(self._run_weekly_universe_rebuild)

        # ── Weekend intelligence ────────────────────────────────────────
        # Day-of-week guard is inside the runner methods; every().day fires
        # daily but the guard returns immediately on non-weekend days.
        sched_lib.every().day.at(SCHEDULE["saturday_intelligence"]).do(
            self._run_saturday_intelligence
        )
        sched_lib.every().day.at(SCHEDULE["sunday_intelligence"]).do(
            self._run_sunday_intelligence
        )

        # ── OIOS Phase F weekly research (Saturday 17:30 IST) ─────────────────
        # Day-of-week guard inside the method; fires daily but no-ops Mon–Fri, Sun.
        sched_lib.every().day.at("17:30").do(self._run_oios_weekly_research)

        # V2: position monitor + scanner event poll (every 5 min, market hours only)
        def _five_min_tasks():
            if not self._is_market_session():
                return
            self.monitor_open_positions()
            self._check_scanner_events()   # V2: handle event-driven mini rescans

        sched_lib.every(5).minutes.do(_five_min_tasks)

        log.info("[Orchestrator] Scheduler armed.")
        log.info("  Pre-market : 08:00 init | 08:30 data warm-up + [Mon] universe rebuild")
        log.info("  Deep scans : 09:05 / 09:10 / 09:20  (MarketMonitor — opening window only)")
        log.info("  Full cycle : 09:45 / 10:30 / 11:30 / 13:00 / 14:00 / 15:00")
        log.info("  Intraday refresh: 11:30 (mid-session) | 13:30 (afternoon) — candidate TTL extension")
        log.info("  EOD        : 15:35")
        log.info("  Post-scan  : 16:45  (Phase D market scanner)")
        log.info("  Pre-mkt    : 08:45  (Phase G premarket refiner)")
        log.info("  Monitoring : every 5 min  |  Light scan: every 30s")
        log.info("  Weekend    : Saturday 08:00 deep accumulation | Sunday 09:00 Monday prep")

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


    def _startup_csv_orphan_audit(self) -> None:
        """
        Fix: Startup CSV Orphan Audit.

        Reads paper_trades.csv immediately on startup and detects any OPEN row
        that has no matching CLOSE row.  Cross-checks against order_manager's
        in-memory state so positions that ARE being tracked are not falsely
        flagged.  Any truly orphaned row → CRITICAL log + Telegram alert.

        This runs synchronously before the scheduler thread starts so the
        user is notified within seconds of container boot.
        """
        import csv
        from pathlib import Path

        csv_path = Path("data/paper_trades.csv")
        if not csv_path.exists():
            log.info("[OrphanAudit] paper_trades.csv not found — skipping.")
            return

        try:
            rows = list(csv.DictReader(open(csv_path)))
        except Exception as exc:
            log.warning("[OrphanAudit] Could not read CSV: %s", exc)
            return

        opens  = {r["order_id"]: r for r in rows if r.get("event", "").strip() == "OPEN"}
        closes = {r["order_id"] for r in rows  if r.get("event", "").strip() == "CLOSE"}
        orphan_ids = set(opens.keys()) - closes

        if not orphan_ids:
            log.info("[OrphanAudit] CSV integrity OK — 0 orphaned positions.")
            return

        # Cross-check: is the order_manager already tracking these?
        try:
            tracked_ids = {o.order_id for o in self.order_manager.get_open_orders()}
        except Exception:
            tracked_ids = set()

        truly_orphaned = orphan_ids - tracked_ids
        tracked_orphans = orphan_ids & tracked_ids

        for oid in tracked_orphans:
            log.info(
                "[OrphanAudit] %s is OPEN-without-CLOSE in CSV but IS tracked "
                "by order_manager — restore OK.",
                opens[oid].get("symbol", oid),
            )

        if not truly_orphaned:
            log.info(
                "[OrphanAudit] All %d CSV-open positions are tracked — no action needed.",
                len(orphan_ids),
            )
            return

        # Build alert message
        lines = []
        for oid in truly_orphaned:
            r = opens[oid]
            lines.append(
                f"  {r.get('symbol','?')} {r.get('direction','?')} "
                f"{r.get('quantity','?')} @ {r.get('entry_price','?')} "
                f"(SL={r.get('stop_loss','?')})"
            )
        alert_body = (
            f"WARNING: {len(truly_orphaned)} position(s) found in paper_trades.csv "
            f"as OPEN without a CLOSE row AND not tracked by order_manager:\n"
            + "\n".join(lines)
            + "\nManual review required."
        )
        log.critical("[OrphanAudit] %s", alert_body)

        try:
            from notifications import get_notifier
            get_notifier().market_alert("⚠️ ORPHAN POSITION ALERT", alert_body)
        except Exception as exc:
            log.warning("[OrphanAudit] Telegram alert failed: %s", exc)

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
