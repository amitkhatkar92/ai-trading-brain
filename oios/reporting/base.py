"""
oios/reporting/base.py

Shared formatting utilities for all OIOS report generators.
No database writes. No imports from oios.engine.
"""
from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any

WIDTH = 72


# ---------------------------------------------------------------------------
# Layout primitives
# ---------------------------------------------------------------------------

def hr(char: str = "=") -> str:
    return char * WIDTH


def section(title: str) -> str:
    return f"\n{title}\n{'-' * len(title)}"


def kv(label: str, value: Any, lw: int = 44) -> str:
    """Left-aligned key, right-aligned value."""
    return f"  {label:<{lw}} {value}"


def kv_warn(label: str, value: Any, lw: int = 44) -> str:
    return f"  ⚠  {label:<{lw - 4}} {value}"


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------

def pct(n: int | float, total: int | float, dec: int = 1) -> str:
    if not total:
        return "N/A"
    return f"{100 * n / total:.{dec}f}%"


def fmt(v: float | None, dec: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{dec}f}"


def fmt_int(v: Any) -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "N/A"


# ---------------------------------------------------------------------------
# Statistical summary
# ---------------------------------------------------------------------------

def stats_line(vals: list) -> str:
    """One-line descriptive stats: Mean P25 P75 Min Max."""
    floats = [float(v) for v in vals if v is not None]
    if not floats:
        return "  No data"
    mean = statistics.mean(floats)
    lo, hi = min(floats), max(floats)
    if len(floats) >= 4:
        qs = statistics.quantiles(floats, n=4)
        p25, p75 = qs[0], qs[2]
    else:
        p25 = p75 = mean
    return (f"  Mean={fmt(mean)}  P25={fmt(p25, 1)}  "
            f"P75={fmt(p75, 1)}  Min={fmt(lo)}  Max={fmt(hi)}")


def quartile_win_rate(rows: list) -> list[str]:
    """
    rows: list of (score, final_state) for closed opportunities.
    Returns formatted lines comparing top-Q vs bottom-Q win rates.
    """
    closed = [(float(r[0]), str(r[1]))
              for r in rows
              if r[0] is not None and r[1] is not None]
    if len(closed) < 40:
        return [f"  Insufficient closed data ({len(closed)} obs, need ≥ 40)"]

    closed.sort(key=lambda x: x[0])
    q_end   = int(len(closed) * 0.25)
    q_start = int(len(closed) * 0.75)
    bottom  = closed[:q_end]
    top     = closed[q_start:]

    def wr(grp):
        w = sum(1 for _, s in grp if s == "TTL_EXHAUSTED")
        return w / len(grp) if grp else 0.0

    twr = wr(top)
    bwr = wr(bottom)
    gap = twr - bwr
    flag = "✓ gap ≥ 10pp" if gap >= 0.10 else "✗ gap < 10pp"
    return [
        kv("  Top-quartile win rate:",
           f"{pct(sum(1 for _,s in top if s=='TTL_EXHAUSTED'), len(top))}  ({len(top)} obs)"),
        kv("  Bottom-quartile win rate:",
           f"{pct(sum(1 for _,s in bottom if s=='TTL_EXHAUSTED'), len(bottom))}  ({len(bottom)} obs)"),
        kv("  Predictive gap:",
           f"{gap * 100:.1f}pp  {flag}  (E-Ready-3 needs ≥ 10pp)"),
    ]


# ---------------------------------------------------------------------------
# Header / footer
# ---------------------------------------------------------------------------

def report_header(title: str, report_date: str) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join([
        hr(),
        f"  {title}",
        f"  Date: {report_date}    Generated: {generated}",
        hr(),
    ])


def shadow_mode_footer(*phases: str) -> str:
    phase_str = " and ".join(phases) if phases else "Phase D and Phase E"
    return (
        f"\n{hr('-')}\n"
        f"  [SHADOW MODE] {phase_str} outputs are computed and recorded only.\n"
        f"  No shadow output modifies OS, RE, TTL, conviction, or execution.\n"
        f"{hr('-')}"
    )
