"""
Sector Rotation AI — Layer 2 Agent 3
=======================================
Detects inter-sector money flows and generates a ranked list of
sectors receiving capital inflows vs those seeing outflows.

Example output:
  Capital moving to:
    1. PSU Banks
    2. Capital Goods
    3. Defence
"""

from __future__ import annotations
from typing import Any, Dict, List

from models.market_data  import SectorFlow
from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)

SECTOR_INDICES = {
    "PSU Banks":      "NIFTY PSU BANK",
    "IT":             "NIFTY IT",
    "Pharma":         "NIFTY PHARMA",
    "Auto":           "NIFTY AUTO",
    "FMCG":           "NIFTY FMCG",
    "Private Banks":  "NIFTY BANK",
}


class SectorRotationAI:
    """Ranks sectors by relative strength and volume participation."""

    def __init__(self):
        log.info("[SectorRotationAI] Initialised.")

    def analyse(self, raw_data: Dict[str, Any]) -> AgentOutput:
        indices = raw_data.get("indices", {})
        flows: List[SectorFlow] = []

        for sector, index_symbol in SECTOR_INDICES.items():
            idx = indices.get(index_symbol, {})
            change_pct = idx.get("change_pct", 0.0)
            volume     = idx.get("volume", 0)
            # Simple flow score: weighted change + volume factor
            flow_score = change_pct * 0.7 + (volume / 1_000_000) * 0.3
            flows.append(SectorFlow(
                sector_name=sector,
                flow_score=round(flow_score, 3),
                rank=0,
            ))

        flows.sort(key=lambda x: x.flow_score, reverse=True)
        for rank, flow in enumerate(flows, 1):
            flow.rank = rank

        top_sectors = [f.sector_name for f in flows[:3]]
        summary = f"Top inflow sectors: {', '.join(top_sectors)}"
        log.info("[SectorRotationAI] %s", summary)

        return AgentOutput(
            agent_name="SectorRotationAI",
            status="ok",
            summary=summary,
            confidence=7.5,
            data={"flows": flows, "leaders": top_sectors},
        )
