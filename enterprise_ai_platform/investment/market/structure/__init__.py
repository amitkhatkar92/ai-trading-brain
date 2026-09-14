"""enterprise_ai_platform/investment/market/structure/__init__.py
Public API for the Institutional Market Structure Engine.
"""
from __future__ import annotations

from enterprise_ai_platform.investment.market.structure.breakout_classifier import BreakoutClassifier
from enterprise_ai_platform.investment.market.structure.breakout_engine import BreakoutEngine
from enterprise_ai_platform.investment.market.structure.breakout_statistics import BreakoutStats, BreakoutStatistics
from enterprise_ai_platform.investment.market.structure.compression_detector import CompressionDetector
from enterprise_ai_platform.investment.market.structure.confidence_calculator import ConfidenceCalculator
from enterprise_ai_platform.investment.market.structure.consolidation_engine import ConsolidationEngine
from enterprise_ai_platform.investment.market.structure.false_breakout import FalseBreakoutDetector
from enterprise_ai_platform.investment.market.structure.market_phase import MarketPhaseDetector
from enterprise_ai_platform.investment.market.structure.market_structure_engine import InstitutionalMarketStructureEngine
from enterprise_ai_platform.investment.market.structure.models import (
    Bar,
    BreakoutEvent,
    BreakoutStatus,
    BreakoutType,
    ConsolidationState,
    ConsolidationType,
    MarketStructureSnapshot,
    StructurePhase,
    StructureQualityScore,
    SwingPoint,
    SwingRelation,
    SwingSequence,
    SwingStrength,
    SwingType,
    TrendPhase,
    TrendState,
    TrendTransition,
    Zone,
    ZoneStrength,
    ZoneType,
)
from enterprise_ai_platform.investment.market.structure.pivot_detector import detect_pivots, is_pivot_high, is_pivot_low
from enterprise_ai_platform.investment.market.structure.range_detector import RangeDetector
from enterprise_ai_platform.investment.market.structure.structure_analyzer import StructureAnalyzer
from enterprise_ai_platform.investment.market.structure.structure_history import StructureHistory
from enterprise_ai_platform.investment.market.structure.structure_quality import StructureQualityAssessor
from enterprise_ai_platform.investment.market.structure.structure_score import StructureScorer
from enterprise_ai_platform.investment.market.structure.structure_state import StructureState
from enterprise_ai_platform.investment.market.structure.support_resistance_engine import SupportResistanceEngine
from enterprise_ai_platform.investment.market.structure.swing_detector import SwingDetector
from enterprise_ai_platform.investment.market.structure.swing_history import SwingHistory
from enterprise_ai_platform.investment.market.structure.trend_classifier import TrendClassifier
from enterprise_ai_platform.investment.market.structure.trend_engine import TrendEngine
from enterprise_ai_platform.investment.market.structure.trend_strength import TrendStrengthAnalyzer
from enterprise_ai_platform.investment.market.structure.trend_transition import TrendTransitionDetector
from enterprise_ai_platform.investment.market.structure.zone_detector import ZoneDetector
from enterprise_ai_platform.investment.market.structure.zone_registry import ZoneRegistry
from enterprise_ai_platform.investment.market.structure.zone_strength import ZoneStrengthCalculator

__all__ = [
    # Main engine
    "InstitutionalMarketStructureEngine",
    # Models
    "Bar",
    "BreakoutEvent",
    "BreakoutStatus",
    "BreakoutType",
    "ConsolidationState",
    "ConsolidationType",
    "MarketStructureSnapshot",
    "StructurePhase",
    "StructureQualityScore",
    "SwingPoint",
    "SwingRelation",
    "SwingSequence",
    "SwingStrength",
    "SwingType",
    "TrendPhase",
    "TrendState",
    "TrendTransition",
    "Zone",
    "ZoneStrength",
    "ZoneType",
    # Detectors / engines
    "BreakoutClassifier",
    "BreakoutEngine",
    "BreakoutStats",
    "BreakoutStatistics",
    "CompressionDetector",
    "ConfidenceCalculator",
    "ConsolidationEngine",
    "FalseBreakoutDetector",
    "MarketPhaseDetector",
    "RangeDetector",
    "StructureAnalyzer",
    "StructureHistory",
    "StructureQualityAssessor",
    "StructureScorer",
    "StructureState",
    "SupportResistanceEngine",
    "SwingDetector",
    "SwingHistory",
    "TrendClassifier",
    "TrendEngine",
    "TrendStrengthAnalyzer",
    "TrendTransitionDetector",
    "ZoneDetector",
    "ZoneRegistry",
    "ZoneStrengthCalculator",
    # Pivot functions
    "detect_pivots",
    "is_pivot_high",
    "is_pivot_low",
]
