"""
Typed Event Definitions — the shared language of the agent network.
====================================================================
Every piece of information flowing between agents is wrapped in an Event.
This gives us:
  • A clear audit trail of every inter-agent communication
  • Type safety — agents know exactly what they'll receive
  • Decoupling — publishers and subscribers never import each other

Event hierarchy:
                        Event (base)
                           │
        ┌──────────────────┼───────────────────────┐
        │                  │                        │
  MarketEvent    OpportunityEvent            RiskEvent
        │                  │                        │
  DecisionEvent   ExecutionEvent          LearningEvent
                            │
                       SystemEvent
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional


class EventType(str, Enum):
    # ── Market Intelligence (Layer 2) ─────────────────────────────────
    MARKET_DATA_READY        = "market.data.ready"
    MARKET_REGIME_CLASSIFIED = "market.regime.classified"
    PRICE_UPDATE             = "market.price.update"       # Real-time tick from MarketMonitor
    SECTOR_ROTATION_DETECTED = "market.sector_rotation.detected"
    LIQUIDITY_ANALYSED       = "market.liquidity.analysed"
    EVENT_RISK_DETECTED      = "market.event_risk.detected"

    # ── Opportunity Engine (Layer 3) ──────────────────────────────────
    EQUITY_SIGNAL_FOUND       = "opportunity.equity.found"
    EQUITY_OPPORTUNITY_FOUND  = "opportunity.equity.found"   # alias
    OPTIONS_SIGNAL_FOUND      = "opportunity.options.found"
    ARBITRAGE_FOUND           = "opportunity.arbitrage.found"
    SCAN_COMPLETE             = "opportunity.scan.complete"

    # ── Strategy Lab (Layer 4) ────────────────────────────────────────
    STRATEGY_ASSIGNED        = "strategy.assigned"
    STRATEGY_EVOLVED         = "strategy.evolved"
    BACKTEST_PASSED          = "strategy.backtest.passed"
    BACKTEST_FAILED          = "strategy.backtest.failed"

    # ── Risk Control (Layer 5) ────────────────────────────────────────
    RISK_CHECK_PASSED        = "risk.check.passed"
    RISK_CHECK_REJECTED      = "risk.check.rejected"
    RISK_CHECK_FAILED        = "risk.check.failed"  # alias for rejected
    PORTFOLIO_HEAT_WARNING   = "risk.portfolio.heat_warning"
    PORTFOLIO_UPDATED        = "risk.portfolio.updated"
    DRAWDOWN_ALERT           = "risk.drawdown.alert"
    DRAWDOWN_HALT            = "risk.drawdown.halt"
    STRESS_TEST_FAILED       = "risk.stress.failed"

    # ── Debate & Decision (Layers 6–7) ────────────────────────────────
    DEBATE_STARTED           = "debate.started"
    DEBATE_VOTE_CAST         = "debate.vote.cast"
    DEBATE_COMPLETE          = "debate.complete"
    TRADE_APPROVED           = "decision.approved"
    TRADE_REJECTED           = "decision.rejected"

    # ── Execution (Layer 8) ───────────────────────────────────────────
    ORDER_PLACED             = "execution.order.placed"
    ORDER_FILLED             = "execution.order.filled"
    ORDER_REJECTED           = "execution.order.rejected"
    STOP_LOSS_HIT            = "execution.sl.hit"
    TARGET_HIT               = "execution.target.hit"

    # ── Trade Monitoring (Layer 9) ────────────────────────────────────
    POSITION_BREAKEVEN_MOVED = "monitor.breakeven.moved"
    STOP_TRAILED             = "monitor.stop.trailed"
    POSITION_CLOSED          = "monitor.position.closed"

    # ── Learning (Layer 10) ───────────────────────────────────────────
    TRADE_OUTCOME_LOGGED     = "learning.outcome.logged"
    STRATEGY_WEIGHT_UPDATED  = "learning.weight.updated"
    EOD_REPORT_READY         = "learning.eod_report.ready"
    LEARNING_CYCLE_COMPLETE  = "learning.cycle.complete"

    # ── Simulation ────────────────────────────────────────────────────
    SIMULATION_COMPLETE      = "simulation.complete"
    # ── Risk Guardian (Layer 9) ───────────────────────────────────────
    RISK_GUARDIAN_COMPLETE   = "risk.guardian.complete"
    # ── Meta-Learning ─────────────────────────────────────────────────
    META_LEARNING_APPLIED    = "meta.learning.applied"

    # ── Strategy Lab ─────────────────────────────────────────────────
    STRATEGY_LAB_COMPLETE    = "strategy.lab.complete"
    # ── Edge Discovery ─────────────────────────────────────────────
    EDGE_DISCOVERED          = "edge.discovered"
    EDGE_DEPRECATED          = "edge.deprecated"    # ── Global Intelligence ─────────────────────────────────────────────
    DISTORTION_DETECTED           = "global.distortion.detected"
    REGIME_PROBABILITY_COMPUTED   = "global.regime_probability.computed"
    # ── Learning / EOD ──────────────────────────────────────────────
    EOD_SELF_EVAL_COMPLETE        = "learning.eod_self_eval.complete"
    # ── System ────────────────────────────────────────────────────────
    SYSTEM_STARTUP           = "system.startup"
    SYSTEM_SHUTDOWN          = "system.shutdown"
    SYSTEM_HALT              = "system.halt"
    CYCLE_STARTED            = "system.cycle.started"
    CYCLE_COMPLETE           = "system.cycle.complete"
    AGENT_ERROR              = "system.agent.error"


# ─────────────────────────────────────────────────────────────────────────────
# BASE EVENT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Event:
    """
    Base class for all agent events.
    Every event carries metadata about who sent it and when.
    """
    event_type:   EventType
    source_agent: str                        # Agent that published the event
    timestamp:    datetime = field(default_factory=datetime.now)
    correlation_id: str   = ""               # Links response events to a request
    payload:      Dict[str, Any] = field(default_factory=dict)

    def reply_event(self, event_type: EventType,
                    source: str,
                    payload: Dict[str, Any]) -> "Event":
        """Create a response event with matching correlation_id."""
        return Event(event_type=event_type, source_agent=source,
                     correlation_id=self.correlation_id, payload=payload)

    def __str__(self) -> str:
        return (f"[{self.event_type.value}] "
                f"from={self.source_agent} "
                f"ts={self.timestamp.strftime('%H:%M:%S.%f')[:-3]}")


# ─────────────────────────────────────────────────────────────────────────────
# TYPED EVENT SUBCLASSES — richer payload contracts
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MarketEvent(Event):
    """Emitted by Market Intelligence agents."""
    regime:     str = ""
    volatility: str = ""
    vix:        float = 0.0


@dataclass
class OpportunityEvent(Event):
    """Emitted by Opportunity Engine when a signal is found."""
    symbol:          str   = ""
    direction:       str   = ""
    entry_price:     float = 0.0
    stop_loss:       float = 0.0
    target_price:    float = 0.0
    strategy_name:   str   = ""
    confidence:      float = 0.0


@dataclass
class RiskEvent(Event):
    """Emitted by Risk Control agents."""
    symbol:       str   = ""
    reason:       str   = ""
    portfolio_heat: float = 0.0


@dataclass
class DecisionEvent(Event):
    """Emitted by Decision Engine with final trade verdict."""
    symbol:             str   = ""
    approved:           bool  = False
    confidence_score:   float = 0.0
    position_modifier:  float = 1.0
    reasoning:          str   = ""


@dataclass
class ExecutionEvent(Event):
    """Emitted by Order Manager after each broker interaction."""
    order_id:    str   = ""
    symbol:      str   = ""
    direction:   str   = ""
    quantity:    int   = 0
    fill_price:  float = 0.0
    pnl:         float = 0.0


@dataclass
class LearningEvent(Event):
    """Emitted by Learning Engine after processing trade outcomes."""
    strategy_name:    str   = ""
    new_win_rate:     float = 0.0
    new_expectancy:   float = 0.0
    weight_modifier:  float = 0.0


@dataclass
class SystemEvent(Event):
    """Infrastructure / lifecycle events."""
    message:  str  = ""
    severity: str  = "INFO"   # INFO | WARNING | CRITICAL
