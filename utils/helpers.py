"""General-purpose helper utilities used across the agent layers."""

from __future__ import annotations
from datetime import datetime, time
from typing import Any, Dict


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a float between min_val and max_val."""
    return max(min_val, min(max_val, value))


def pct_change(old: float, new: float) -> float:
    """Safe percentage change from old to new."""
    if old == 0:
        return 0.0
    return (new - old) / old


def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """Recursively flatten a nested dict."""
    items: list = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def current_session() -> str:
    """Return the current market session label."""
    now = datetime.now().time()
    pre_market  = time(8, 0)
    open_time   = time(9, 15)
    mid_day     = time(12, 0)
    close_time  = time(15, 30)
    eod         = time(16, 0)

    if now < pre_market:
        return "overnight"
    elif now < open_time:
        return "pre_market"
    elif now < mid_day:
        return "morning_session"
    elif now < close_time:
        return "afternoon_session"
    elif now < eod:
        return "post_market"
    else:
        return "closed"


def risk_per_trade(capital: float, risk_pct: float, entry: float, stop: float) -> int:
    """Calculate the number of shares/units to trade given a risk percentage."""
    risk_amount  = capital * risk_pct
    risk_per_unit = abs(entry - stop)
    if risk_per_unit == 0:
        return 0
    return int(risk_amount / risk_per_unit)
