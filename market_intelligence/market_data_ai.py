"""
Market Data AI — Layer 2 Agent 1
==================================
Collects real-time and historical price/volume/OI data from broker APIs
and normalises it into a standard dictionary consumed by all other agents.

Collects:
  • Nifty 50, Bank Nifty, Nifty 500, Sector indices
  • Volume, Open Interest
  • FII / DII flow data
  • VIX, PCR, Market Breadth
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List

from config import INDICES, ACTIVE_BROKER
from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)


class MarketDataAI:
    """
    Collects and normalises ALL market data required by downstream agents.
    Currently uses a simulated/mock data layer; swap `_fetch_live_data` 
    with a real broker adapter from execution_engine/brokers/.
    """

    def __init__(self):
        self.indices: List[str] = INDICES
        log.info("[MarketDataAI] Initialised. Tracking %d indices.", len(self.indices))

    # ─────────────────────────────────────────────
    # PUBLIC INTERFACE
    # ─────────────────────────────────────────────

    def fetch(self) -> Dict[str, Any]:
        """
        Returns a normalised market data dictionary:
        {
          "indices": { symbol: IndexData },
          "vix":     float,
          "pcr":     float,
          "breadth": float,
          "fii_dii": FIIDIIData | None,
        }
        """
        log.info("[MarketDataAI] Fetching market data…")
        try:
            data = self._fetch_live_data()
            log.info("[MarketDataAI] Data fetched. VIX=%.1f PCR=%.2f Breadth=%.0f%%",
                     data.get("vix", 0), data.get("pcr", 0),
                     data.get("breadth", 0) * 100)
            return data
        except Exception as exc:
            log.error("[MarketDataAI] Fetch failed: %s", exc)
            return {}

    def as_agent_output(self) -> AgentOutput:
        data = self.fetch()
        return AgentOutput(
            agent_name="MarketDataAI",
            status="ok" if data else "error",
            summary=f"Fetched data for {len(data.get('indices', {}))} indices",
            data=data,
            confidence=9.0 if data else 0.0,
        )

    # ─────────────────────────────────────────────
    # PRIVATE — DATA COLLECTION
    # ─────────────────────────────────────────────

    # ── Yahoo symbol map for key Indian indices ─────────────────────────
    _YF_INDEX_MAP: Dict[str, str] = {
        "NIFTY 50":          "NIFTY",      # ^NSEI  via GLOBAL_SYMBOL_MAP
        "NIFTY BANK":        "BANKNIFTY",  # ^NSEBANK
        "NIFTY IT":          "^CNXIT",
        "NIFTY PHARMA":      "^CNXPHARMA",
        "NIFTY AUTO":        "^CNXAUTO",
        "NIFTY FMCG":        "^CNXFMCG",
    }
    # India VIX yfinance alias (resolved through GLOBAL_SYMBOL_MAP)
    _VIX_ALIAS = "INDIAVIX"  # → ^INDIAVIX

    def _fetch_live_data(self) -> Dict[str, Any]:
        """
        Fetch live market data.
        NIFTY 50, BANKNIFTY, and INDIA VIX come from yfinance (real values).
        Remaining sector indices fall back to simulation if yfinance cannot
        serve them (most sector indices are not reliably on yfinance).
        """
        import random
        from data_feeds.yahoo_feed import YahooFeed
        random.seed(int(datetime.now().timestamp()) // 60)   # stable per minute

        yf_feed   = YahooFeed()
        is_live   = yf_feed.is_live
        indices_data = {}

        # ── Real data: NIFTY 50 & BANKNIFTY ─────────────────────────────
        for full_name, alias in self._YF_INDEX_MAP.items():
            q = yf_feed.get_quote(alias) if is_live else None
            if q and q.ltp and q.ltp > 0:
                indices_data[full_name] = {
                    "symbol":     full_name,
                    "ltp":        q.ltp,
                    "open":       q.open or q.ltp,
                    "high":       q.high or q.ltp,
                    "low":        q.low  or q.ltp,
                    "close":      q.close or q.ltp,
                    "volume":     int(q.volume or 0),
                    "oi":         0,
                    "change_pct": round(q.change_pct or 0.0, 2),
                    "source":     "LIVE",
                }
            else:
                # Fallback simulation for this index
                base_prices = {
                    "NIFTY 50": 22500, "NIFTY BANK": 48000, "NIFTY 500": 20000,
                    "NIFTY MIDCAP 150": 15000, "NIFTY SMALLCAP 250": 8500,
                    "NIFTY IT": 35000, "NIFTY PSU BANK": 6500,
                    "NIFTY PHARMA": 19000, "NIFTY AUTO": 23000, "NIFTY FMCG": 21000,
                }
                base   = base_prices.get(full_name, 10000)
                chg    = random.uniform(-0.02, 0.02)
                ltp    = round(base * (1 + chg), 2)
                indices_data[full_name] = {
                    "symbol": full_name, "ltp": ltp,
                    "open": base, "high": round(ltp * 1.005, 2),
                    "low":  round(ltp * 0.995, 2), "close": base,
                    "volume": random.randint(500_000, 5_000_000),
                    "oi": 0, "change_pct": round(chg * 100, 2),
                    "source": "SIM",
                }

        # ── Fill remaining indices that aren't in _YF_INDEX_MAP ──────────
        sim_base = {
            "NIFTY 500": 20000, "NIFTY MIDCAP 150": 15000,
            "NIFTY SMALLCAP 250": 8500,
        }
        for symbol in self.indices:
            if symbol not in indices_data:
                base   = sim_base.get(symbol, 10000)
                chg    = random.uniform(-0.02, 0.02)
                ltp    = round(base * (1 + chg), 2)
                indices_data[symbol] = {
                    "symbol": symbol, "ltp": ltp,
                    "open": base, "high": round(ltp * 1.005, 2),
                    "low":  round(ltp * 0.995, 2), "close": base,
                    "volume": random.randint(500_000, 5_000_000),
                    "oi": 0, "change_pct": round(chg * 100, 2),
                    "source": "SIM",
                }

        # ── Real data: INDIA VIX ─────────────────────────────────────────
        vix_q  = yf_feed.get_quote(self._VIX_ALIAS) if is_live else None
        vix    = round(vix_q.ltp, 2) if (vix_q and vix_q.ltp and vix_q.ltp > 0) \
                 else round(random.uniform(12, 25), 2)
        vix_src = "LIVE" if (vix_q and vix_q.ltp and vix_q.ltp > 0) else "SIM"

        log.info(
            "[MarketDataAI] Key indices — NIFTY 50: %.2f (%s)  "
            "BANKNIFTY: %.2f (%s)  INDIA VIX: %.2f (%s)",
            indices_data.get("NIFTY 50", {}).get("ltp", 0),
            indices_data.get("NIFTY 50", {}).get("source", "?"),
            indices_data.get("NIFTY BANK", {}).get("ltp", 0),
            indices_data.get("NIFTY BANK", {}).get("source", "?"),
            vix, vix_src,
        )

        return {
            "indices":    indices_data,
            "vix":        vix,
            "vix_source": vix_src,
            "pcr":        round(random.uniform(0.7, 1.4), 2),
            "breadth":    round(random.uniform(0.3, 0.8), 2),
            "fii_dii":    self._fetch_fii_dii(),
            "timestamp":  datetime.now().isoformat(),
            "data_source": "LIVE" if is_live else "SIM",
        }

    def _fetch_fii_dii(self) -> Dict[str, float]:
        """Fetch FII/DII institutional flow data (simulated)."""
        import random
        return {
            "fii_buy":  round(random.uniform(2000, 8000), 2),
            "fii_sell": round(random.uniform(2000, 7000), 2),
            "dii_buy":  round(random.uniform(1500, 6000), 2),
            "dii_sell": round(random.uniform(1500, 5000), 2),
        }
