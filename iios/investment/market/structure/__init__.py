"""iios/investment/market/structure/__init__.py
Public API for the Institutional Market Structure Engine.
"""
from __future__ import annotations

from iios.investment.market.structure.breakout_classifier import BreakoutClassifier
from iios.investment.market.structure.breakout_engine import BreakoutEngine
from iios.investment.market.structure.breakout_statistics import BreakoutStats, BreakoutStatistics
from iios.investment.market.structure.compression_detector import CompressionDetector
from iios.investment.market.structure.confidence_calculator import ConfidenceCalculator
from iios.investment.market.structure.consolidation_engine import ConsolidationEngine
from iios.investment.market.structure.false_breakout import FalseBreakoutDetector
from iios.investment.market.structure.market_phase import MarketPhaseDetector
from iios.investment.market.structure.market_structure_engine import InstitutionalMarketStructureEngine
from iios.investment.market.structure.models import (
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
from iios.investment.market.structure.pivot_detector import detect_pivots, is_pivot_high, is_pivot_low
from iios.investment.market.structure.range_detector import RangeDetector
from iios.investment.market.structure.structure_analyzer import StructureAnalyzer
from iios.investment.market.structure.structure_history import StructureHistory
from iios.investment.market.structure.structure_quality import StructureQualityAssessor
from iios.investment.market.structure.structure_score import StructureScorer
from iios.investment.market.structure.structure_state import StructureState
from iios.investment.market.structure.support_resistance_engine import SupportResistanceEngine
from iios.investment.market.structure.swing_detector import SwingDetector
from iios.investment.market.structure.swing_history import SwingHistory
from iios.investment.market.structure.trend_classifier import TrendClassifier
from iios.investment.market.structure.trend_engine import TrendEngine
from iios.investment.market.structure.trend_strength import TrendStrengthAnalyzer
from iios.investment.market.structure.trend_transition import TrendTransitionDetector
from iios.investment.market.structure.zone_detector import ZoneDetector
from iios.investment.market.structure.zone_registry import ZoneRegistry
from iios.investment.market.structure.zone_strength import ZoneStrengthCalculator

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
