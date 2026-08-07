"""predictive_gap/pga_analyzer.py — Classify each stock move for PGA-001."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .pga_collector import DailyData, DecisionRecord, SignalRecord, StockMove
from .pga_config import PGAConfig

log = logging.getLogger(__name__)

# Was-Predicted classifications
WP_YES       = "YES"
WP_PARTIALLY = "PARTIALLY"
WP_NO        = "NO"

# Was-Predictable classifications
PRED_YES   = "PREDICTABLE"
PRED_PART  = "PARTIALLY_PREDICTABLE"
PRED_NO    = "NOT_PREDICTABLE"

# Miss types
MISS_MISSED_WINNER   = "MISSED_WINNER"
MISS_MISSED_LOSER    = "MISSED_LOSER"
MISS_CORRECT         = "CORRECT"
MISS_WRONG_DIRECTION = "WRONG_DIRECTION"
MISS_NO_DATA         = "NO_DATA"


@dataclass
class StockAnalysis:
    symbol: str
    stock_move: StockMove
    was_predicted: str            # YES | PARTIALLY | NO
    was_predictable: str          # PREDICTABLE | PARTIALLY_PREDICTABLE | NOT_PREDICTABLE
    prediction_detail: str
    predictability_detail: str
    iios_signal: Optional[SignalRecord]
    iios_decision: Optional[DecisionRecord]
    dna_coverage: int
    edge_coverage: int
    miss_type: str                # one of MISS_* constants above
    is_focus_stock: bool = False  # True if in top5 gainer/loser list


def _find_signal(symbol: str, data: DailyData) -> Optional[SignalRecord]:
    """Find the most recent signal for a symbol today."""
    matches = [s for s in data.watchlist_candidates if s.symbol == symbol]
    # Also check if it was in all signals (approved + rejected have matching signals)
    for sig_set in [data.watchlist_candidates]:
        for s in sig_set:
            if s.symbol == symbol and s not in matches:
                matches.append(s)
    return matches[-1] if matches else None


def _find_decision(symbol: str, data: DailyData) -> Optional[DecisionRecord]:
    """Find today's decision for a symbol."""
    for d in data.approved_today:
        if d.symbol == symbol:
            return d
    for d in data.rejected_today:
        if d.symbol == symbol:
            return d
    return None


def _directions_match(predicted: str, actual: str) -> bool:
    """Return True if predicted (BUY/SELL/SHORT) matches actual move direction."""
    pred_up   = predicted.upper() in ("BUY", "LONG")
    actual_up = actual.upper() == "UP"
    return pred_up == actual_up


def _classify_was_predicted(
    symbol: str,
    move: StockMove,
    data: DailyData,
    cfg: PGAConfig,
) -> tuple[str, str, Optional[SignalRecord], Optional[DecisionRecord]]:
    """
    Classify whether IIOS predicted this stock's move.

    Returns (was_predicted, detail_str, iios_signal, iios_decision)
    """
    decision = _find_decision(symbol, data)
    signal   = _find_signal(symbol, data)

    if decision is not None and decision.approved:
        # IIOS approved a trade on this symbol
        if move.daily_return_pct == 0.0:
            return (WP_PARTIALLY, "Approved but no price data", signal, decision)

        if _directions_match(decision.direction, move.actual_direction):
            if abs(move.daily_return_pct) >= cfg.min_move_pct:
                return (
                    WP_YES,
                    f"Approved {decision.direction} @ conf={decision.confidence:.1f}, "
                    f"move={move.daily_return_pct:+.1f}% ✓",
                    signal,
                    decision,
                )
            else:
                return (
                    WP_PARTIALLY,
                    f"Approved {decision.direction} @ conf={decision.confidence:.1f}, "
                    f"move={move.daily_return_pct:+.1f}% (below threshold {cfg.min_move_pct}%)",
                    signal,
                    decision,
                )
        else:
            return (
                WP_NO,
                f"Approved {decision.direction} but stock moved {move.actual_direction} "
                f"({move.daily_return_pct:+.1f}%) — wrong direction",
                signal,
                decision,
            )

    elif decision is not None and not decision.approved:
        # IIOS generated a signal but rejected it
        return (
            WP_PARTIALLY,
            f"Signal generated ({decision.direction} conf={decision.confidence:.1f}) "
            f"but REJECTED: {decision.rejection_reason or 'below threshold'}",
            signal,
            decision,
        )

    elif symbol in data.scanned_today:
        # Scanner found it but no final decision
        sig = _find_signal(symbol, data)
        return (
            WP_PARTIALLY,
            f"Scanned today (in opportunity events) but no decision reached "
            + (f"— signal conf={sig.confidence:.1f}" if sig else ""),
            sig,
            None,
        )

    else:
        # Not on IIOS radar at all
        return (
            WP_NO,
            f"Not scanned today (not in universe events), "
            f"moved {move.daily_return_pct:+.1f}%",
            None,
            None,
        )


def _classify_was_predictable(
    symbol: str,
    move: StockMove,
    data: DailyData,
    cfg: PGAConfig,
) -> tuple[str, str]:
    """
    Classify whether IIOS *could* have predicted this move with better intelligence.

    Returns (was_predictable, detail_str)
    """
    dna = data.dna_coverage.get(symbol, 0)
    edges = data.edge_coverage.get(symbol, 0)
    in_universe = symbol in data.universe_symbols
    scanned = symbol in data.scanned_today
    move_abs = abs(move.daily_return_pct)

    # Large moves with no data are external events
    if move_abs > 10.0 and dna == 0 and not scanned:
        return (
            PRED_NO,
            f"No DNA, not scanned, {move_abs:.1f}% move — likely ExternalEvent "
            "(earnings surprise / news / corporate action)",
        )

    if dna >= cfg.dna_coverage_min and scanned:
        return (
            PRED_YES,
            f"DNA coverage={dna}, was scanned — sufficient knowledge existed",
        )

    if dna >= cfg.dna_coverage_min and not scanned:
        return (
            PRED_PART,
            f"DNA coverage={dna} (sufficient) but not scanned today — "
            "scanner threshold or PMCI filter blocked it",
        )

    if dna > 0 and (scanned or in_universe):
        return (
            PRED_PART,
            f"DNA coverage={dna} (partial), edges={edges}, "
            f"scanned={scanned} — limited evidence, harder to predict",
        )

    if in_universe and dna == 0:
        return (
            PRED_PART,
            f"In universe but no DNA patterns — knowledge gap identified",
        )

    return (
        PRED_NO,
        f"No DNA, not in active universe — NOT_PREDICTABLE with current intelligence",
    )


def _classify_miss_type(
    move: StockMove,
    was_predicted: str,
    decision: Optional[DecisionRecord],
    cfg: PGAConfig,
) -> str:
    """Classify the type of miss / outcome."""
    is_significant = abs(move.daily_return_pct) >= cfg.min_move_pct

    if was_predicted == WP_YES:
        return MISS_CORRECT

    if not is_significant:
        return MISS_NO_DATA  # stock barely moved — no meaningful classification

    if move.move_type == "GAINER":
        # Stock went up significantly
        if decision is not None and decision.approved and not _directions_match(decision.direction, move.actual_direction):
            return MISS_WRONG_DIRECTION
        return MISS_MISSED_WINNER

    if move.move_type == "LOSER":
        # Stock went down significantly
        if decision is not None and decision.approved and not _directions_match(decision.direction, move.actual_direction):
            return MISS_WRONG_DIRECTION
        return MISS_MISSED_LOSER

    return MISS_NO_DATA


def analyze_universe(data: DailyData, cfg: PGAConfig) -> List[StockAnalysis]:
    """
    Classify all focus stocks (gainers + losers) for the day.

    Returns one StockAnalysis per focus stock.
    """
    focus_symbols: Dict[str, StockMove] = {}
    for m in data.gainers + data.losers:
        focus_symbols[m.symbol] = m

    # Also analyze scanned/executed stocks not in the focus list
    for dec in data.approved_today + data.rejected_today:
        if dec.symbol not in focus_symbols and dec.symbol in data.all_moves:
            focus_symbols[dec.symbol] = data.all_moves[dec.symbol]

    results: List[StockAnalysis] = []
    focus_set = {m.symbol for m in data.gainers + data.losers}

    for symbol, move in focus_symbols.items():
        wp, wp_detail, sig, dec = _classify_was_predicted(symbol, move, data, cfg)
        pred, pred_detail = _classify_was_predictable(symbol, move, data, cfg)
        miss_type = _classify_miss_type(move, wp, dec, cfg)

        results.append(StockAnalysis(
            symbol=symbol,
            stock_move=move,
            was_predicted=wp,
            was_predictable=pred,
            prediction_detail=wp_detail,
            predictability_detail=pred_detail,
            iios_signal=sig,
            iios_decision=dec,
            dna_coverage=data.dna_coverage.get(symbol, 0),
            edge_coverage=data.edge_coverage.get(symbol, 0),
            miss_type=miss_type,
            is_focus_stock=symbol in focus_set,
        ))

    log.info(
        "[PGA] Analysis: total=%d correct=%d missed_winner=%d missed_loser=%d wrong_dir=%d",
        len(results),
        sum(1 for r in results if r.miss_type == MISS_CORRECT),
        sum(1 for r in results if r.miss_type == MISS_MISSED_WINNER),
        sum(1 for r in results if r.miss_type == MISS_MISSED_LOSER),
        sum(1 for r in results if r.miss_type == MISS_WRONG_DIRECTION),
    )

    return results
