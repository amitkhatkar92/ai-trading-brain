"""
Smart Execution Engine — Feasibility & Selection Layer Over Already-Sized Signals
===================================================================================

DTA-SMARTEXEC-002: implements a 3-Rule feasibility/selection system over
signals whose quantity was ALREADY set upstream by CapitalRiskEngine +
PortfolioAllocationAI. SmartExecution never sizes a position itself:
  1. Capital Exposure Control (max 80% total, using REAL notional)
  3. Directional Risk Control (max 70% per direction, using REAL notional)
  4. Confidence + R:R Trade Selection (rank, then accept/reject in order)

Ownership boundary:
  - Sector decorrelation is owned exclusively by CorrelationEngine
    (runs upstream). SmartExecution does not duplicate a sector cap.
  - Capital availability (regime/VIX/drawdown) is owned exclusively by
    CapitalRiskEngine. SmartExecution reads each signal's REAL quantity
    and checks that CUMULATIVE already-approved notional stays within a
    flat 80%/70% ceiling — a sanity/feasibility check, not a second
    capital-risk engine.

Does NOT impose hard trade limits. Instead:
  • Filters by confidence and correlation
  • Controls exposure dynamically
  • Selects optimal trade set within limits
  • Logs every rejection with reason

Flow:
  signals (from strategy) → filter_trades() → selected_trades (to execution)
"""

from __future__ import annotations
import logging
from typing import List, Dict, Optional, Any

log = logging.getLogger(__name__)


class SmartExecutionEngine:
    """
    Trade feasibility/selection filter over already-sized signals.
    
    Attributes:
        capital (float)               : Total available capital
        max_exposure (float)          : 80% of capital (exposure ceiling)
        max_direction_exposure (float): 70% of capital per direction
    """
    
    def __init__(self, capital: float = 50_000):
        self.capital = capital
        self.max_exposure = 0.80 * capital
        self.max_direction_exposure = 0.70 * capital
    
    def filter_trades(
        self,
        trades: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Filter and size trades according to 5-rule system.
        
        Args:
            trades            : List of trade dicts with keys:
                                  symbol, sector, direction, confidence,
                                  quantity (required for sizing); entry_price,
                                  stop_loss, target (optional)
        
        Returns:
            List of accepted trades with added "position_size" field
            (== quantity * entry_price, the REAL already-sized notional).
            Rejected trades retain "rejection_reason" field.
        
        Pseudocode:
        1. Sort trades by combined score (confidence 55% + R:R 45%)
        2. For each trade:
           - Read real notional (quantity × entry_price)
           - Check capital limit (≤80%)
           - Check direction limit (≤70% per direction)
           - If all pass → accept, else → reject + log reason
        3. Return selected + rejected trades
        """
        
        selected = []
        rejected = []
        total_exposure = 0.0
        bullish_exposure = 0.0
        bearish_exposure = 0.0
        
        def _combined_score(t: dict) -> float:
            """Rank by combined score: confidence 55% + normalised R:R 45%.
            confidence is 0–1 (normalised from 0–10 by the orchestrator).
            rr normalised as min(rr/5, 1.0) so RR≥5 scores 1.0.
            """
            conf   = t.get("confidence", 0.7)
            entry  = t.get("entry_price", 0.0)
            target = t.get("target", 0.0) or 0.0
            stop   = t.get("stop_loss", entry) or entry
            risk   = abs(entry - stop)
            rr     = abs(target - entry) / risk if (risk > 0 and entry > 0) else 1.0
            rr_norm = min(rr / 5.0, 1.0)
            return conf * 0.55 + rr_norm * 0.45

        # Sort by combined score (confidence 55% + R:R 45%), highest first
        sorted_trades = sorted(trades, key=_combined_score, reverse=True)
        
        log.info(
            "[SmartExecution] Filtering %d trades | "
            "Capital: $%.0f | Max Exposure: $%.0f (80%%)",
            len(sorted_trades), self.capital, self.max_exposure
        )
        
        for trade in sorted_trades:
            symbol = trade.get("symbol", "UNKNOWN")
            sector = trade.get("sector", "OTHER")
            direction = trade.get("direction", "BUY")
            confidence = trade.get("confidence", 0.5)
            
            # ── RULE 1 input: real, already-sized notional ──
            # DTA-SMARTEXEC-002: CapitalRiskEngine + PortfolioAllocationAI
            # already decided quantity; SmartExecution only checks that the
            # CUMULATIVE already-approved notional stays within a flat
            # 80%/70% ceiling. It never re-derives sizing from confidence,
            # VIX, or drawdown — those are CapitalRiskEngine's exclusive
            # ownership (see module docstring).
            position_size = trade.get("quantity", 0) * trade.get("entry_price", 0.0)
            
            # ── RULE 1: Capital Exposure Control (max 80% total) ──
            if total_exposure + position_size > self.max_exposure:
                trade["rejection_reason"] = "capital_limit"
                rejected.append(trade)
                log.debug(
                    "  ✗ %s (%s) — REJECTED: capital limit exceeded "
                    "(current: $%.0f, new size: $%.0f, max: $%.0f)",
                    symbol, direction, total_exposure, position_size, self.max_exposure
                )
                continue
            
            # ── RULE 3: Direction Control (max 70% per direction) ──
            if direction.upper() in ("BUY", "LONG"):
                if bullish_exposure + position_size > self.max_direction_exposure:
                    trade["rejection_reason"] = "direction_limit_bullish"
                    rejected.append(trade)
                    log.debug(
                        "  ✗ %s (BUY) — REJECTED: bullish exposure limit exceeded "
                        "(current: $%.0f, new size: $%.0f, max: $%.0f)",
                        symbol, bullish_exposure, position_size, self.max_direction_exposure
                    )
                    continue
                bullish_exposure += position_size
            else:  # SELL / SHORT
                if bearish_exposure + position_size > self.max_direction_exposure:
                    trade["rejection_reason"] = "direction_limit_bearish"
                    rejected.append(trade)
                    log.debug(
                        "  ✗ %s (SELL) — REJECTED: bearish exposure limit exceeded "
                        "(current: $%.0f, new size: $%.0f, max: $%.0f)",
                        symbol, bearish_exposure, position_size, self.max_direction_exposure
                    )
                    continue
                bearish_exposure += position_size
            
            # ── RULE 4: Quality Filter (confidence-based) ──
            # Implicit: already sorted by confidence; low-confidence are rejected naturally
            # when higher-confidence trades exhaust exposure limits.
            
            # ─────────────────────────────────────────────────────────
            # ✅ TRADE ACCEPTED
            # ─────────────────────────────────────────────────────────
            trade["position_size"] = position_size
            selected.append(trade)
            
            total_exposure += position_size
            
            log.info(
                "  ✓ %s (%s) — ACCEPTED | Size: $%.0f | Confidence: %.2f | "
                "Sector: %s | Total Exposure: $%.0f / $%.0f (%.1f%%)",
                symbol, direction, position_size, confidence, sector,
                total_exposure, self.max_exposure,
                (total_exposure / self.max_exposure) * 100
            )
        
        # ── Summary logging ──
        log.info(
            "[SmartExecution] Summary: %d accepted | %d rejected | "
            "Total Exposure: $%.0f (%.1f%%) | "
            "Bullish: $%.0f | Bearish: $%.0f",
            len(selected), len(rejected),
            total_exposure, (total_exposure / self.max_exposure) * 100,
            bullish_exposure, bearish_exposure
        )
        
        return selected + rejected

    def get_summary(self, filtered_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of filtered trades for reporting.
        
        Returns:
            Dict with keys: accepted_count, rejected_count, total_exposure,
                           exposure_pct, sector_breakdown, direction_breakdown
        """
        accepted = [t for t in filtered_trades if "position_size" in t]
        rejected = [t for t in filtered_trades if "rejection_reason" in t]
        
        total_exposure = sum(t.get("position_size", 0) for t in accepted)
        exposure_pct = (total_exposure / self.max_exposure) * 100 if self.max_exposure > 0 else 0
        
        # Breakdown by sector
        sector_breakdown = {}
        for trade in accepted:
            sector = trade.get("sector", "OTHER")
            size = trade.get("position_size", 0)
            sector_breakdown[sector] = sector_breakdown.get(sector, 0.0) + size
        
        # Breakdown by direction
        direction_breakdown = {"BUY": 0.0, "SELL": 0.0}
        for trade in accepted:
            direction = trade.get("direction", "BUY").upper()
            size = trade.get("position_size", 0)
            if direction in ("BUY", "LONG"):
                direction_breakdown["BUY"] += size
            else:
                direction_breakdown["SELL"] += size
        
        return {
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "total_exposure": round(total_exposure, 2),
            "exposure_pct": round(exposure_pct, 1),
            "sector_breakdown": {k: round(v, 2) for k, v in sector_breakdown.items()},
            "direction_breakdown": {k: round(v, 2) for k, v in direction_breakdown.items()},
        }
