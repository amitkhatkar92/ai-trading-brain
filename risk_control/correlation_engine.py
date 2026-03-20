"""
Correlation Engine — Intelligent Trade Decorrelation
=====================================================

Reduces hidden sector correlation risk by:
  1. Assigning sectors to each trade (based on symbol lookup)
  2. Grouping trades by sector
  3. Keeping only top-confidence trades per sector (default max 2)

Example:
  Input:  [HDFC BUY, ICICI BUY, AXIS BUY, SBIN BUY, KOTAK BUY]
  Output: [HDFC BUY (top), ICICI BUY (2nd)] + others → controlled sector focus
  
  Without CorrelationEngine → 5 trades looks like 5 independent bets
  With CorrelationEngine → system sees "one large banking bet"

This prevents correlated blowups where 5 trades fail together.
"""

from __future__ import annotations
import logging
from typing import List, Dict, Optional, Any

log = logging.getLogger(__name__)


class CorrelationEngine:
    """
    Intelligent trade decorrelation by sector grouping and confidence ranking.
    
    Attributes:
        sector_map (Dict[str, str])  : Symbol → sector mapping
                                       e.g., "HDFC" → "BANK"
        max_trades_per_sector (int)  : Max trades from same sector (default 2)
    """
    
    # ── Static Sector Mapping ──────────────────────────────────────────
    # Maps NSE symbols to sectors. Extend this as new symbols are added.
    DEFAULT_SECTOR_MAP = {
        # ── Banking & Financial ────────────────────────────────────────
        "HDFC":      "BANK",
        "ICICI":     "BANK",
        "AXIS":      "BANK",
        "SBIN":      "BANK",
        "KOTAK":     "BANK",
        "INDUSIND":  "BANK",
        "AUBANK":    "BANK",
        "HDFCBANK":  "BANK",
        
        # ── IT ─────────────────────────────────────────────────────────
        "INFY":      "IT",
        "TCS":       "IT",
        "WIPRO":     "IT",
        "TECHM":     "IT",
        "HCL":       "IT",
        "LTTS":      "IT",
        "MPHASIS":   "IT",
        
        # ── Energy & Oil ───────────────────────────────────────────────
        "RELIANCE":  "ENERGY",
        "ONGC":      "ENERGY",
        "ADANIGREEN": "ENERGY",
        "ADANIPOWER": "ENERGY",
        "BPCL":      "ENERGY",
        "HPCL":      "ENERGY",
        
        # ── Auto ───────────────────────────────────────────────────────
        "MARUTI":    "AUTO",
        "TATA":      "AUTO",
        "TATAMOTORS": "AUTO",
        "BAJAJFINSV": "AUTO",
        "EICHER":    "AUTO",
        "SUNDARAUTO": "AUTO",
        "ASHOKLEY":  "AUTO",
        
        # ── Pharma ─────────────────────────────────────────────────────
        "SUNITPHARM": "PHARMA",
        "DIVI":      "PHARMA",
        "CIPLA":     "PHARMA",
        "LUPIN":     "PHARMA",
        "CADILAHC":  "PHARMA",
        "SUNPHARMA": "PHARMA",
        
        # ── FMCG ───────────────────────────────────────────────────────
        "HINDUNILVR": "FMCG",
        "ITC":       "FMCG",
        "BRITANNIA": "FMCG",
        "NESTLEIND": "FMCG",
        "CMSTEEL":   "FMCG",
        "DABUR":     "FMCG",
        
        # ── Real Estate ────────────────────────────────────────────────
        "SOBHA":     "REALTY",
        "LODHA":     "REALTY",
        "PRESTIGE":  "REALTY",
        "GODREJCP":  "REALTY",
        "DLF":       "REALTY",
        "SUPREMEIND": "REALTY",
        
        # ── Telecom ────────────────────────────────────────────────────
        "JIOTOWER":  "TELECOM",
        "INDIATOWER": "TELECOM",
        "BHARTIARTL": "TELECOM",
        "IDEA":      "TELECOM",
        "VODAFONE":  "TELECOM",
        
        # ── Metal & Mining ─────────────────────────────────────────────
        "TATASTEEL": "METAL",
        "HINDALCO":  "METAL",
        "JSPL":      "METAL",
        "JSWSTEEL":  "METAL",
        "TATACONSUM": "METAL",
        
        # ── Cement ─────────────────────────────────────────────────────
        "SHREECEM":  "CEMENT",
        "ULTRACEMCO": "CEMENT",
        "DALBHARAT": "CEMENT",
        "ACC":       "CEMENT",
        "AMB":       "CEMENT",
        
        # ── Consumer ───────────────────────────────────────────────────
        "TATACONSUM": "CONSUMER",
        "MRF":       "CONSUMER",
        "TITAN":     "CONSUMER",
        "BOSCHLTD":  "CONSUMER",
        
        # ── Financial Services ────────────────────────────────────────
        "LT":        "FINANCE",
        "BAJAJFINSV": "FINANCE",
        "HDFC":      "FINANCE",
        "SBICARD":   "FINANCE",
        "AXISBANK":  "FINANCE",
    }
    
    def __init__(self, sector_map: Optional[Dict[str, str]] = None, max_per_sector: int = 2):
        """
        Initialize Correlation Engine.
        
        Args:
            sector_map       : Custom sector mapping (uses DEFAULT if None)
            max_per_sector   : Max trades from same sector
        """
        self.sector_map = sector_map or self.DEFAULT_SECTOR_MAP.copy()
        self.max_trades_per_sector = max_per_sector
        log.info(
            "[CorrelationEngine] Initialized with %d symbol mappings | "
            "Max %d trades per sector",
            len(self.sector_map), max_per_sector
        )
    
    def assign_sector(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assign sector to a trade based on symbol lookup.
        
        Args:
            trade : Dict with key "symbol"
        
        Returns:
            Updated trade dict with "sector" field set
        """
        symbol = trade.get("symbol", "").upper()
        sector = self.sector_map.get(symbol, "OTHER")
        trade["sector"] = sector
        return trade
    
    def group_by_sector(self, trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group trades by sector.
        
        Args:
            trades : List of trade dicts (must have "sector" field)
        
        Returns:
            Dict mapping sector name → list of trades in that sector
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for trade in trades:
            sector = trade.get("sector", "OTHER")
            if sector not in grouped:
                grouped[sector] = []
            grouped[sector].append(trade)
        return grouped
    
    def reduce_correlation(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply sector-based decorrelation to trades.
        
        Process:
          1. Assign sectors to all trades
          2. Group by sector
          3. Keep only top N trades per sector (by confidence)
          4. Return filtered trades
        
        Args:
            trades : List of trade dicts from decision engine
        
        Returns:
            Filtered list with reduced correlation (max N per sector)
        
        Example:
          Input: [HDFC (conf=0.8), ICICI (conf=0.9), AXIS (conf=0.7),
                  INFY (conf=0.85), TCS (conf=0.75)]
          Output: [ICICI (0.9), HDFC (0.8), INFY (0.85), TCS (0.75)]
                  ^ 2 BANK, 2 IT → controlled sector exposure
        """
        log.info("[CorrelationEngine] Decorrelating %d trades", len(trades))
        
        # Step 1: Assign sectors
        trades_with_sectors = [self.assign_sector(t) for t in trades]
        
        # Step 2: Group by sector
        grouped = self.group_by_sector(trades_with_sectors)
        
        log.debug("[CorrelationEngine] Grouped into %d sectors:", len(grouped))
        for sector, sector_trades in grouped.items():
            log.debug("  → Sector '%s': %d trades", sector, len(sector_trades))
        
        # Step 3: Filter by sector, keeping only top N by confidence
        filtered_trades = []
        for sector, sector_trades in grouped.items():
            # Sort by confidence (highest first)
            sorted_sector_trades = sorted(
                sector_trades,
                key=lambda x: x.get("confidence", 0.0),
                reverse=True
            )
            
            # Keep only top N
            kept = sorted_sector_trades[:self.max_trades_per_sector]
            rejected_sector = sorted_sector_trades[self.max_trades_per_sector:]
            
            filtered_trades.extend(kept)
            
            # Log sector filtering
            if len(kept) < len(sector_trades):
                log.info(
                    "[CorrelationEngine] Sector '%s': keeping %d / %d trades "
                    "(rejected: %s)",
                    sector, len(kept), len(sector_trades),
                    ", ".join([t.get("symbol", "?") for t in rejected_sector])
                )
            else:
                log.debug(
                    "[CorrelationEngine] Sector '%s': keeping all %d trades",
                    sector, len(kept)
                )
        
        log.info(
            "[CorrelationEngine] Decorrelation complete: %d trades → %d trades "
            "(%.1f%% retained)",
            len(trades_with_sectors), len(filtered_trades),
            (len(filtered_trades) / len(trades)) * 100 if trades else 0
        )
        
        return filtered_trades
    
    def get_sector_summary(self, trades: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Get breakdown of trades by sector.
        
        Returns:
            Dict mapping sector → count of trades
        """
        grouped = self.group_by_sector(trades)
        return {sector: len(trades_list) for sector, trades_list in grouped.items()}
