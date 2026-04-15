"""
Event Detection AI — Layer 2 Agent 5
=======================================
Monitors economic calendar and news feed for high-impact events that
require reducing exposure or adjusting strategy.

Events tracked:
  • RBI Monetary Policy
  • Budget / Union Budget
  • US Fed meetings / CPI / NFP
  • Elections
  • Quarterly earnings (Nifty 50 companies)
  • Geopolitical events
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List

from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)

# ── Static economic calendar (extend with live API feed) ─────────────────────
# resolve_hour_ist: IST hour (24h) after which the event is considered resolved
#   on event day. None = post-market event (US events after 21:00 IST) —
#   stays active all Indian market hours, expires naturally next day.
KNOWN_EVENTS: Dict[str, Dict[str, Any]] = {
    # format: "YYYY-MM-DD": {"name": ..., "impact": ..., "sectors": [...], "resolve_hour_ist": int|None}
    "2026-03-15": {"name": "RBI Monetary Policy",       "impact": "HIGH",   "sectors": ["Banking"], "resolve_hour_ist": 11},
    "2026-03-20": {"name": "US Fed FOMC Meeting",        "impact": "HIGH",   "sectors": ["All"],     "resolve_hour_ist": None},
    "2026-04-01": {"name": "Q4 Results Season Start",    "impact": "MEDIUM", "sectors": ["All"],     "resolve_hour_ist": 12},
    "2026-04-15": {"name": "US CPI Release",             "impact": "HIGH",   "sectors": ["All"],     "resolve_hour_ist": None},
    "2026-02-01": {"name": "Union Budget",               "impact": "HIGH",   "sectors": ["All"],     "resolve_hour_ist": 13},
}


class EventDetectionAI:
    """Scans economic calendar and live news for market-moving events."""

    LOOKAHEAD_DAYS = 2    # Flag events within the next N days (reduced 3→2: less pre-event noise)

    def __init__(self):
        log.info("[EventDetectionAI] Initialised with %d calendar events.", len(KNOWN_EVENTS))

    def scan(self) -> AgentOutput:
        today           = date.today()
        upcoming_events = self._check_calendar(today)
        risk_level      = self._assess_risk(upcoming_events)

        summary = (
            f"Events in next {self.LOOKAHEAD_DAYS}d: {len(upcoming_events)} | "
            f"Risk Level: {risk_level}"
        )

        if upcoming_events:
            for ev in upcoming_events:
                log.warning("[EventDetectionAI] ⚠ Event: %s — %s", ev["name"], ev["impact"])
        else:
            log.info("[EventDetectionAI] No high-impact events in next %d days.", self.LOOKAHEAD_DAYS)

        return AgentOutput(
            agent_name="EventDetectionAI",
            status="warning" if risk_level in ("HIGH", "CRITICAL") else "ok",
            summary=summary,
            confidence=8.0,
            data={
                "events": [e["name"] for e in upcoming_events],
                "risk_level": risk_level,
                "reduce_exposure": risk_level in ("HIGH", "CRITICAL"),
                "details": upcoming_events,
            },
        )

    def _check_calendar(self, today: date) -> List[Dict[str, Any]]:
        upcoming: List[Dict[str, Any]] = []
        now_hour = datetime.now().hour  # IST hour (server runs IST)
        for date_str, info in KNOWN_EVENTS.items():
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            days_away  = (event_date - today).days
            if not (0 <= days_away <= self.LOOKAHEAD_DAYS):
                continue
            # On event day: check if the event has already been resolved
            if days_away == 0:
                resolve_hour = info.get("resolve_hour_ist")
                if resolve_hour is not None and now_hour >= resolve_hour + 1:
                    log.info("[EventDetectionAI] ✅ Event resolved: %s (past %02d:00 IST)",
                             info["name"], resolve_hour + 1)
                    continue  # event announced — uncertainty cleared
            upcoming.append({**info, "date": date_str, "days_away": days_away})
        return upcoming

    def _assess_risk(self, events: List[Dict[str, Any]]) -> str:
        if not events:
            return "NONE"
        high_count = sum(1 for e in events if e.get("impact") == "HIGH")
        if high_count >= 2:
            return "CRITICAL"
        elif high_count == 1:
            return "HIGH"
        return "MEDIUM"
