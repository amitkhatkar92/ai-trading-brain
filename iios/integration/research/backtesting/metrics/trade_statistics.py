"""metrics/trade_statistics.py — Per-trade and aggregate trade statistics."""
from __future__ import annotations

import statistics
from typing import Any


# ── Accessors ─────────────────────────────────────────────────────────────────

def _net_pnls(trades: list[dict[str, Any]]) -> list[float]:
    return [t.get("net_pnl", 0.0) for t in trades]


def _winners(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [t for t in trades if t.get("net_pnl", 0.0) > 0]


def _losers(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [t for t in trades if t.get("net_pnl", 0.0) < 0]


# ── Core statistics ───────────────────────────────────────────────────────────

def win_rate(trades: list[dict[str, Any]]) -> float:
    if not trades:
        return 0.0
    return len(_winners(trades)) / len(trades)


def profit_factor(trades: list[dict[str, Any]]) -> float:
    wins_total  = sum(t["net_pnl"] for t in _winners(trades))
    loss_total  = abs(sum(t["net_pnl"] for t in _losers(trades)))
    if loss_total == 0.0:
        return float("inf") if wins_total > 0 else 0.0
    return wins_total / loss_total


def expectancy(trades: list[dict[str, Any]]) -> float:
    """Average net PnL per trade."""
    if not trades:
        return 0.0
    return sum(_net_pnls(trades)) / len(trades)


def avg_win(trades: list[dict[str, Any]]) -> float:
    winners = _winners(trades)
    if not winners:
        return 0.0
    return sum(t["net_pnl"] for t in winners) / len(winners)


def avg_loss(trades: list[dict[str, Any]]) -> float:
    """Returns a positive number (magnitude of average loss)."""
    losers = _losers(trades)
    if not losers:
        return 0.0
    return abs(sum(t["net_pnl"] for t in losers) / len(losers))


def largest_win(trades: list[dict[str, Any]]) -> float:
    pnls = [t["net_pnl"] for t in _winners(trades)]
    return max(pnls) if pnls else 0.0


def largest_loss(trades: list[dict[str, Any]]) -> float:
    """Returns a positive number."""
    pnls = [abs(t["net_pnl"]) for t in _losers(trades)]
    return max(pnls) if pnls else 0.0


def avg_trade_duration(trades: list[dict[str, Any]]) -> float:
    """Average trade duration in seconds."""
    durations = [t.get("duration_sec", 0.0) for t in trades]
    return sum(durations) / len(durations) if durations else 0.0


def max_consecutive_wins(trades: list[dict[str, Any]]) -> int:
    """Longest consecutive winning streak."""
    best = count = 0
    for t in trades:
        if t.get("net_pnl", 0) > 0:
            count += 1
            best   = max(best, count)
        else:
            count  = 0
    return best


def max_consecutive_losses(trades: list[dict[str, Any]]) -> int:
    """Longest consecutive losing streak."""
    best = count = 0
    for t in trades:
        if t.get("net_pnl", 0) < 0:
            count += 1
            best   = max(best, count)
        else:
            count  = 0
    return best


def trade_return_distribution(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a dict summarising the distribution of trade returns."""
    pcts = [t.get("return_pct", 0.0) for t in trades]
    if not pcts:
        return {}
    return {
        "count":  len(pcts),
        "mean":   statistics.mean(pcts),
        "median": statistics.median(pcts),
        "stdev":  statistics.stdev(pcts) if len(pcts) > 1 else 0.0,
        "min":    min(pcts),
        "max":    max(pcts),
    }


def trades_by_symbol(trades: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for t in trades:
        sym = t.get("symbol", "UNKNOWN")
        result.setdefault(sym, []).append(t)
    return result
