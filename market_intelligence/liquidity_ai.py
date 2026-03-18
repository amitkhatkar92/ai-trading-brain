"""
Liquidity AI — Layer 2 Agent 4
=================================
Tracks institutional and retail capital flows to assess overall
market liquidity and directional intent of big money.

Monitors:
  • FII flows (buying vs selling)
  • DII flows
  • Retail vs institutional participation ratio
  • Pre-open order book imbalance
"""

from __future__ import annotations
from typing import Any, Dict

from models.agent_output import AgentOutput
from utils import get_logger

log = get_logger(__name__)


class LiquidityAI:
    """Analyses FII/DII and liquidity signals."""

    STRONG_FII_INFLOW  =  2000   # INR crores
    STRONG_FII_OUTFLOW = -2000

    def __init__(self):
        log.info("[LiquidityAI] Initialised.")

    def analyse(self, raw_data: Dict[str, Any]) -> AgentOutput:
        fii_dii  = raw_data.get("fii_dii", {})
        fii_net  = fii_dii.get("fii_buy", 0) - fii_dii.get("fii_sell", 0)
        dii_net  = fii_dii.get("dii_buy", 0) - fii_dii.get("dii_sell", 0)

        liquidity_bias = self._assess_bias(fii_net, dii_net)
        confidence     = self._confidence(fii_net, dii_net)

        summary = (
            f"FII Net: ₹{fii_net:+,.0f} Cr | "
            f"DII Net: ₹{dii_net:+,.0f} Cr | "
            f"Bias: {liquidity_bias}"
        )
        log.info("[LiquidityAI] %s", summary)

        return AgentOutput(
            agent_name="LiquidityAI",
            status="ok",
            summary=summary,
            confidence=confidence,
            data={
                "fii_net": fii_net,
                "dii_net": dii_net,
                "liquidity_bias": liquidity_bias,
                "institutional_net": fii_net + dii_net,
            },
        )

    def _assess_bias(self, fii_net: float, dii_net: float) -> str:
        combined = fii_net + dii_net
        if combined > self.STRONG_FII_INFLOW:
            return "STRONG_INFLOW"
        elif combined > 0:
            return "MILD_INFLOW"
        elif combined > self.STRONG_FII_OUTFLOW:
            return "MILD_OUTFLOW"
        else:
            return "STRONG_OUTFLOW"

    def _confidence(self, fii_net: float, dii_net: float) -> float:
        magnitude = abs(fii_net + dii_net)
        if magnitude > 5000:
            return 9.0
        elif magnitude > 2000:
            return 7.5
        elif magnitude > 500:
            return 6.0
        return 5.0
