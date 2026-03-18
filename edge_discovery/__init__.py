"""
Edge Discovery Engine Package
==============================
Autonomous research layer that continuously discovers new profitable
market patterns without human-defined rules.

Pipeline:
    FeatureExtractor → PatternMiner → CandidateStrategyGenerator
        → StrategyTester → EdgeRankingEngine → Strategy Library

Public API::

    from edge_discovery import EdgeDiscoveryEngine

    ede = EdgeDiscoveryEngine()
    report = ede.run_discovery_cycle(snapshot)   # EOD / weekly
    ede.record_outcome("EDG_MOMVOL_63_T0001", won=True)

    active = ede.get_active_strategies()         # plug into MetaController
"""

from .edge_discovery_engine         import EdgeDiscoveryEngine
from .feature_extractor             import FeatureExtractor, SymbolFeatures, FeatureVector
from .pattern_miner                 import PatternMiner, DiscoveredPattern, PatternCondition
from .candidate_strategy_generator  import CandidateStrategyGenerator, CandidateStrategy
from .strategy_tester               import StrategyTester, BacktestResult
from .edge_ranking_engine           import EdgeRankingEngine, EdgeRecord

__all__ = [
    "EdgeDiscoveryEngine",
    "FeatureExtractor",
    "SymbolFeatures",
    "FeatureVector",
    "PatternMiner",
    "DiscoveredPattern",
    "PatternCondition",
    "CandidateStrategyGenerator",
    "CandidateStrategy",
    "StrategyTester",
    "BacktestResult",
    "EdgeRankingEngine",
    "EdgeRecord",
]
