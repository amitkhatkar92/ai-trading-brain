"""iios/decision_evaluation/evaluation_constants.py"""
from __future__ import annotations
from enum import Enum


class CriterionDirection(Enum):
    MAXIMIZE = "maximize"  # higher is better
    MINIMIZE = "minimize"  # lower is better
    TARGET   = "target"    # closest to target is better


class CriterionType(Enum):
    QUANTITATIVE = "quantitative"
    QUALITATIVE  = "qualitative"
    BOOLEAN      = "boolean"
    COMPOSITE    = "composite"


class ScoringMethod(Enum):
    WEIGHTED_SUM     = "weighted_sum"
    WEIGHTED_PRODUCT = "weighted_product"
    TOPSIS           = "topsis"
    SIMPLE           = "simple"


class NormalizationMethod(Enum):
    MINMAX = "minmax"
    ZSCORE = "zscore"
    MAXABS = "maxabs"
    NONE   = "none"


class RankingMethod(Enum):
    SCORE     = "score"
    PARETO    = "pareto"
    UTILITY   = "utility"
    DOMINANCE = "dominance"


class WeightingStrategy(Enum):
    EQUAL    = "equal"
    MANUAL   = "manual"
    PRIORITY = "priority"
    ENTROPY  = "entropy"


class EvaluationMode(Enum):
    STRICT      = "strict"       # all criteria mandatory
    LENIENT     = "lenient"      # missing criteria skipped
    BEST_EFFORT = "best_effort"  # partial scoring allowed
    AUDIT       = "audit"        # non-blocking, log only


# ── Engine metadata ────────────────────────────────────────────────────────────
EVALUATION_ENGINE_VERSION   = "1.0.0"
EVALUATION_ENGINE_SYSTEM_ID = "iios:evaluation:engine"

# ── Limits ─────────────────────────────────────────────────────────────────────
MAX_ALTERNATIVES_PER_REQUEST = 500
MAX_CRITERIA_PER_REQUEST     = 100
MAX_CRITERIA_IN_REGISTRY     = 10_000
MAX_EVALUATION_HISTORY       = 50_000

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_CRITERION_WEIGHT     = 1.0
DEFAULT_NORMALIZATION        = NormalizationMethod.MINMAX
DEFAULT_SCORING_METHOD       = ScoringMethod.WEIGHTED_SUM
DEFAULT_RANKING_METHOD       = RankingMethod.SCORE
