"""
Decision Trace — Control Tower Module 5
=======================================
Maintains a per-symbol audit trail of every key decision made during
the current and recent cycles:

  symbol → [{layer, status, detail, ts}, ...]

This lets traders see exactly why a trade was approved or rejected
at every layer.

Public API:
  get_trace(symbol)             → List[Dict]   — per-symbol history
  get_all_recent_decisions()    → List[Dict]   — flat list, newest first
  get_approved_count()          → int
  get_rejected_count()          → int
  get_rejection_reasons()       → Dict[str, int]  — reason → count
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List

from communication.events import Event, EventType
from utils import get_logger

log = get_logger(__name__)

FLAT_HISTORY_SIZE = 500   # flat ring-buffer of all decisions
SYMBOL_DEPTH      = 20    # how many trace entries to keep per symbol


class DecisionTrace:

    def __init__(self, bus) -> None:
        self._lock             = threading.Lock()
        # symbol → deque of trace entries
        self._traces: Dict[str, Deque[Dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=SYMBOL_DEPTH))
        # flat history (newest last)
        self._flat: Deque[Dict[str, Any]] = deque(maxlen=FLAT_HISTORY_SIZE)

        self._approved_count = 0
        self._rejected_count = 0
        self._rejection_reasons: Dict[str, int] = defaultdict(int)

        bus.subscribe("*", self._on_event,
                      agent_name="ControlTower.DecisionTrace", priority=95)
        log.info("[DecisionTrace] Initialised.")

    # ── Public API ─────────────────────────────────────────────────────────

    def get_trace(self, symbol: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._traces.get(symbol, []))

    def get_all_recent_decisions(self, n: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._flat)
        return list(reversed(items[-n:]))   # newest first

    def get_approved_count(self) -> int:
        with self._lock:
            return self._approved_count

    def get_rejected_count(self) -> int:
        with self._lock:
            return self._rejected_count

    def get_rejection_reasons(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._rejection_reasons)

    def get_symbols_in_flight(self) -> List[str]:
        """Return symbols that have a pending trace entry."""
        with self._lock:
            return list(self._traces.keys())

    # ── Internal ───────────────────────────────────────────────────────────

    def _on_event(self, event: Event) -> None:
        try:
            et  = (event.event_type.value
                   if hasattr(event.event_type, "value")
                   else str(event.event_type))
            pay = event.payload if isinstance(event.payload, dict) else {}

            ts_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

            with self._lock:
                if et == EventType.CYCLE_STARTED.value:
                    # Fresh cycle — clear current traces
                    self._traces.clear()
                    self._approved_count = 0
                    self._rejected_count = 0
                    self._rejection_reasons.clear()

                elif et == EventType.EQUITY_OPPORTUNITY_FOUND.value:
                    sym = pay.get("symbol", "?")
                    self._add_trace(sym, "OpportunityEngine", "FOUND",
                                    f"strategy={pay.get('strategy','?')} "
                                    f"conf={pay.get('confidence',0):.2f}", ts_str)

                elif et == EventType.RISK_CHECK_PASSED.value:
                    sym = pay.get("symbol", "?")
                    if sym and sym != "?":
                        self._add_trace(sym, "RiskControl", "PASSED",
                                        f"score={pay.get('score',0):.2f}", ts_str)

                elif et == EventType.RISK_CHECK_FAILED.value:
                    sym = pay.get("symbol", "?")
                    reason = pay.get("reason", "unknown")
                    if sym and sym != "?":
                        self._add_trace(sym, "RiskControl", "REJECTED",
                                        reason, ts_str)
                        self._rejection_reasons[f"Risk: {reason[:40]}"] += 1

                elif et == EventType.SIMULATION_COMPLETE.value:
                    # Bulk event — annotate only if per-symbol data available
                    for sym in pay.get("approved_symbols", []):
                        self._add_trace(sym, "SimulationEngine", "SIM_PASSED",
                                        f"survival={pay.get('survival_rate',0):.0%}", ts_str)
                    for entry in pay.get("rejected_symbols", []):
                        sym    = entry if isinstance(entry, str) else entry.get("symbol", "?")
                        reason = "" if isinstance(entry, str) else entry.get("reason", "")
                        self._add_trace(sym, "SimulationEngine", "SIM_REJECTED",
                                        reason, ts_str)

                elif et == EventType.TRADE_APPROVED.value:
                    sym    = pay.get("symbol", "?")
                    strat  = pay.get("strategy", "?")
                    score  = pay.get("score", 0)
                    self._add_trace(sym, "GuardianCouncil", "APPROVED",
                                    f"strategy={strat} score={score:.2f}", ts_str)
                    self._approved_count += 1
                    entry = {
                        "symbol":   sym,
                        "strategy": strat,
                        "decision": "APPROVED",
                        "reason":   "",
                        "score":    score,
                        "ts":       ts_str,
                    }
                    self._flat.append(entry)

                elif et == EventType.TRADE_REJECTED.value:
                    sym    = pay.get("symbol", "?")
                    reason = pay.get("reason", "unknown")
                    self._add_trace(sym, "GuardianCouncil", "REJECTED",
                                    reason, ts_str)
                    self._rejected_count += 1
                    self._rejection_reasons[reason[:50]] += 1
                    entry = {
                        "symbol":   sym,
                        "strategy": pay.get("strategy", "?"),
                        "decision": "REJECTED",
                        "reason":   reason,
                        "score":    pay.get("score", 0),
                        "ts":       ts_str,
                    }
                    self._flat.append(entry)

                elif et == EventType.ORDER_PLACED.value:
                    sym = pay.get("symbol", "?")
                    self._add_trace(sym, "OrderManager", "ORDER_PLACED",
                                    f"{pay.get('direction','?')} qty={pay.get('quantity','?')} "
                                    f"@ {pay.get('entry_price','?')}", ts_str)

        except Exception as exc:
            log.debug("[DecisionTrace] Error: %s", exc)

    def _add_trace(self, symbol: str, layer: str, status: str,
                   detail: str, ts: str) -> None:
        """Append a trace entry for a symbol (must hold _lock)."""
        self._traces[symbol].append({
            "layer":  layer,
            "status": status,
            "detail": detail,
            "ts":     ts,
        })
