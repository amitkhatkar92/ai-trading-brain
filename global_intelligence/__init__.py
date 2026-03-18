"""
Global Intelligence Layer
==========================
Runs before Market Intelligence to provide overnight global context
that biases the regime classification and strategy selection.

Pipeline
--------
GlobalDataAI → MacroSignalAI → CorrelationEngine → GlobalSentimentAI → PremarketBiasAI
                                                                              ↓
                                                                     PremarketBias
                                                                     (consumed by MarketRegimeAI)

Quick usage
-----------
from global_intelligence import GlobalIntelligenceEngine

engine = GlobalIntelligenceEngine()
bias   = engine.run()   # → PremarketBias
"""

from .global_data_ai             import GlobalDataAI, GlobalSnapshot
from .macro_signal_ai            import MacroSignalAI, MacroSignals, RiskSentiment
from .correlation_engine         import CorrelationEngine, CorrelationResult
from .global_sentiment_ai        import GlobalSentimentAI, GlobalSentimentScore, SentimentLabel
from .premarket_bias_ai          import PremarketBiasAI, PremarketBias, NiftyBias
from .market_distortion_scanner  import (
    MarketDistortionScanner, DistortionResult, BehaviorOverrides,
)

from utils import get_logger
_log = get_logger(__name__)


class GlobalIntelligenceEngine:
    """
    Top-level orchestrator for the Global Intelligence Layer.

    Runs the complete pipeline and returns a PremarketBias object
    that is fed into MarketRegimeAI for regime classification.

    Usage
    -----
    brain.global_intelligence = GlobalIntelligenceEngine()
    bias = brain.global_intelligence.run()
    """

    def __init__(self):
        self.data_ai          = GlobalDataAI()
        self.macro_ai         = MacroSignalAI()
        self.correlation      = CorrelationEngine()
        self.sentiment_ai     = GlobalSentimentAI()
        self.bias_ai          = PremarketBiasAI()
        self.distortion_scanner = MarketDistortionScanner()
        # Exposed after each run() call so the orchestrator can read it
        self.last_distortion: DistortionResult = DistortionResult()
        _log.info("[GlobalIntelligenceEngine] Initialised. 6 sub-agents active (incl. DistortionScanner).")

    def run(self) -> PremarketBias:
        """
        Execute the full global intelligence pipeline.

        Order
        -----
        1. Fetch raw global data
        2. Compute macro signals
        3. Run Market Distortion Scanner  ← gates downstream behavior
        4. Correlation, sentiment, premarket bias

        Returns PremarketBias for MarketRegimeAI.
        DistortionResult is stored on self.last_distortion for the orchestrator.
        """
        snap       = self.data_ai.fetch()
        macro      = self.macro_ai.analyse(snap)

        # ── Market Distortion Scanner (runs before regime / bias) ────
        self.last_distortion = self.distortion_scanner.scan(snap, macro)
        _log.info("[GlobalIntelligenceEngine] DistortionScan: Risk=%s  Score=%d/8",
                  self.last_distortion.risk_level, self.last_distortion.stress_score)

        corr       = self.correlation.compute(snap)
        sentiment  = self.sentiment_ai.score(snap, macro, corr)
        bias       = self.bias_ai.compute(snap, macro, sentiment)
        self.bias_ai.print_premarket_report(snap, bias)
        return bias

    @property
    def last_snapshot(self):
        """Alias kept for direct access to raw data if needed."""
        return self.data_ai


__all__ = [
    "GlobalIntelligenceEngine",
    "GlobalDataAI",             "GlobalSnapshot",
    "MacroSignalAI",            "MacroSignals",         "RiskSentiment",
    "CorrelationEngine",        "CorrelationResult",
    "GlobalSentimentAI",        "GlobalSentimentScore", "SentimentLabel",
    "PremarketBiasAI",          "PremarketBias",        "NiftyBias",
    "MarketDistortionScanner",  "DistortionResult",     "BehaviorOverrides",
]
