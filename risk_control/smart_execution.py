"""
Smart Execution Engine — Intelligent Trade Selection & Position Sizing
========================================================================

Implements the 5-Rule Professional System:
  1. Capital Exposure Control (max 80% total)
  2. Sector-Based Filtering (max 2 per sector)
  3. Directional Risk Control (max 70% per direction)
  4. Confidence-Based Trade Selection (rank + execute top trades)
  5. Dynamic Position Sizing (confidence × VIX × drawdown factor)

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
    Intelligent trade execution filter with multi-rule risk control.
    
    Attributes:
        capital (float)               : Total available capital
        max_exposure (float)          : 80% of capital (exposure ceiling)
        max_sector_trades (int)       : Max trades per sector (default 2)
        max_direction_exposure (float): 70% of capital per direction
    """
    
    def __init__(self, capital: float = 50_000):
        self.capital = capital
        self.max_exposure = 0.80 * capital
        self.max_sector_trades = 2
        self.max_direction_exposure = 0.70 * capital
    
    def filter_trades(
        self,
        trades: List[Dict[str, Any]],
        vix: float = 15.0,
        drawdown_factor: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Filter and size trades according to 5-rule system.
        
        Args:
            trades            : List of trade dicts with keys:
                                  symbol, sector, direction, confidence
                                  (required); entry_price, stop_loss, target
                                  (optional)
            vix               : Current VIX level (used for VIX-adjusted sizing)
            drawdown_factor   : Drawdown-based position size multiplier
                                (1.0 = normal, 0.5 = after losses)
        
        Returns:
            List of accepted trades with added "position_size" field.
            Rejected trades retain "rejection_reason" field.
        
        Pseudocode:
        1. Sort trades by confidence (high → low)
        2. For each trade:
           - Check sector limit (≤2 per sector)
           - Calculate position size (confidence × VIX × drawdown)
           - Check capital limit (≤80%)
           - Check direction limit (≤70% per direction)
           - If all pass → accept, else → reject + log reason
        3. Return selected + rejected trades
        """
        
        selected = []
        rejected = []
        total_exposure = 0.0
        sector_count: Dict[str, int] = {}
        bullish_exposure = 0.0
        bearish_exposure = 0.0
        
        # Sort by confidence (highest first)
        sorted_trades = sorted(
            trades,
            key=lambda x: x.get("confidence", 0.0),
            reverse=True
        )
        
        log.info(
            "[SmartExecution] Filtering %d trades | "
            "Capital: $%.0f | Max Exposure: $%.0f (80%%) | "
            "VIX: %.2f | Drawdown Factor: %.2f",
            len(sorted_trades), self.capital, self.max_exposure, vix, drawdown_factor
        )
        
        for trade in sorted_trades:
            symbol = trade.get("symbol", "UNKNOWN")
            sector = trade.get("sector", "OTHER")
            direction = trade.get("direction", "BUY")
            confidence = trade.get("confidence", 0.5)
            
            # ── RULE 2: Sector Limit (max 2 per sector) ──
            sector_trades_so_far = sector_count.get(sector, 0)
            if sector_trades_so_far >= self.max_sector_trades:
                trade["rejection_reason"] = "sector_limit"
                rejected.append(trade)
                log.debug(
                    "  ✗ %s (%s) — REJECTED: sector '%s' already has %d trades",
                    symbol, direction, sector, sector_trades_so_far
                )
                continue
            
            # ── RULE 5: Dynamic Position Sizing ──
            # position_size = capital × confidence_factor × vix_factor × drawdown_factor
            
            # Confidence factor: clamp to [0.3, 0.9]
            confidence_factor = max(0.3, min(confidence, 0.9))
            
            # VIX factor: lower VIX → larger positions; higher VIX → smaller
            # At VIX=15 (normal) → factor=1.0
            # At VIX=25 (elevated) → factor=0.4 (half size)
            # Range: [0.4, 1.0] (no position grows above normal despite low VIX)
            vix_normal = 15.0
            vix_factor = max(0.4, min(1.0, 1.0 - (vix - vix_normal) / 20.0))
            
            position_size = (
                self.capital
                * confidence_factor
                * vix_factor
                * drawdown_factor
            )
            
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
            sector_count[sector] = sector_trades_so_far + 1
            
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
