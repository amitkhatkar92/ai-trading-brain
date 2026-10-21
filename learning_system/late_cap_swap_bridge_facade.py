"""
Read-only facade re-exporting risk_control.late_cap_swap_bridge's
get_readiness_status() for consumers that must not import `risk_control`
directly (same reason/precedent as capital_risk_facade.py -- Sandy's own
safety-contract test forbids any `risk_control` import anywhere in
sandy/). Pure pass-through, never mutates anything.
"""
from risk_control.late_cap_swap_bridge import (
    get_readiness_status as _get_readiness_status,
)


def get_readiness_status() -> dict:
    return _get_readiness_status()
