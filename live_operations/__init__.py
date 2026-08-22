"""
live_operations — LOL-001 Live Operations Layer
================================================
Operational layer converting IIOS from a development platform into
a daily-operated institutional trading desk.

No architecture changes. No strategy changes. No research changes.
Operational layer only.

Exports
-------
run_premarket        — phases 1–2–7: health check + report + GO/NO-GO
run_live_monitor     — phase 3: continuous intraday monitor
run_incident_check   — phase 4: one-pass incident scan
run_postmarket       — phases 5–6: daily report + executive summary
LOLRunner            — full automated runner
"""
from __future__ import annotations

from .lol_runner import (
    LOLRunner,
    run_premarket,
    run_live_monitor,
    run_incident_check,
    run_postmarket,
)

__all__ = [
    "LOLRunner",
    "run_premarket",
    "run_live_monitor",
    "run_incident_check",
    "run_postmarket",
]
