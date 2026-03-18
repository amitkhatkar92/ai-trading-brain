"""
Signal Visualizer — Control Tower Module 4
==========================================
Tracks the signal funnel for each trading cycle:

  generated → strategies_assigned → risk_approved
            → sim_approved → debate_approved → executed

Also keeps a history of the last HISTORY_SIZE cycles so the
dashboard can show a trend chart.

Public API:
  get_current_funnel()   → Dict[str, int]      — current cycle counts
  get_funnel_history()   → List[Dict[str,int]] — last N cycles
  get_conversion_rates() → Dict[str, float]    — per-stage conversion %
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List

from communication.events import Event, EventType
from utils import get_logger

log = get_logger(__name__)

HISTORY_SIZE = 50   # how many completed cycles to retain


_EMPTY_FUNNEL = {
    "generated":           0,
    "strategies_assigned": 0,
    "risk_approved":       0,
    "sim_approved":        0,
    "debate_approved":     0,
    "executed":            0,
}


class SignalVisualizer:

    def __init__(self, bus) -> None:
        self._lock    = threading.Lock()
        self._current: Dict[str, Any] = dict(_EMPTY_FUNNEL)
        self._current["cycle_id"] = ""

        self._history: Deque[Dict[str, Any]] = deque(maxlen=HISTORY_SIZE)

        bus.subscribe("*", self._on_event,
                      agent_name="ControlTower.SignalVisualizer", priority=96)
        log.info("[SignalVisualizer] Initialised.")

    # ── Public API ─────────────────────────────────────────────────────────

    def get_current_funnel(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._current)

    def get_funnel_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def get_conversion_rates(self) -> Dict[str, float]:
        f = self.get_current_funnel()
        base = f.get("generated", 0) or 1   # avoid div-by-0
        return {
            "strategy_assign_rate": f.get("strategies_assigned", 0) / base,
            "risk_pass_rate":       f.get("risk_approved",       0) / base,
            "sim_pass_rate":        f.get("sim_approved",        0) / base,
            "debate_pass_rate":     f.get("debate_approved",     0) / base,
            "execution_rate":       f.get("executed",            0) / base,
        }

    # ── Internal ───────────────────────────────────────────────────────────

    def _on_event(self, event: Event) -> None:
        try:
            et  = (event.event_type.value
                   if hasattr(event.event_type, "value")
                   else str(event.event_type))
            pay = event.payload if isinstance(event.payload, dict) else {}

            with self._lock:
                if et == EventType.CYCLE_STARTED.value:
                    # Archive previous cycle if it had any signals
                    if self._current.get("generated", 0):
                        self._history.append(dict(self._current))
                    # Reset
                    self._current = dict(_EMPTY_FUNNEL)
                    self._current["cycle_id"] = (
                        event.correlation_id
                        or event.timestamp.strftime("%H:%M:%S"))

                elif et == EventType.SCAN_COMPLETE.value:
                    total = (pay.get("equity", 0)
                             + pay.get("options", 0)
                             + pay.get("arb", 0)
                             + pay.get("total", 0))
                    # If "total" key already sums everything, avoid double-counting
                    if pay.get("total"):
                        total = pay["total"]
                    self._current["generated"] = total

                elif et == EventType.STRATEGY_LAB_COMPLETE.value:
                    self._current["strategies_assigned"] = pay.get("assigned", 0)

                elif et == EventType.RISK_CHECK_PASSED.value:
                    self._current["risk_approved"] = max(
                        self._current["risk_approved"],
                        pay.get("approved", self._current["risk_approved"] + 1))

                elif et == EventType.SIMULATION_COMPLETE.value:
                    self._current["sim_approved"] = pay.get("approved", 0)

                elif et == EventType.TRADE_APPROVED.value:
                    self._current["debate_approved"] += 1

                elif et == EventType.ORDER_PLACED.value:
                    self._current["executed"] += 1

                elif et == EventType.CYCLE_COMPLETE.value:
                    self._history.append(dict(self._current))

        except Exception as exc:
            log.debug("[SignalVisualizer] Error: %s", exc)
