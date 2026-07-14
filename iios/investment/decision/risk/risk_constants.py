"""iios/investment/decision/risk/risk_constants.py
All enumerations, constants, and thresholds for the Decision Risk Engine.
"""
from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    CRITICAL = "critical"   # >= 80
    HIGH     = "high"       # >= 60
    MEDIUM   = "medium"     # >= 40
    LOW      = "low"        # >= 20
    MINIMAL  = "minimal"    # <  20

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        if score >= 80.0: return cls.CRITICAL
        if score >= 60.0: return cls.HIGH
        if score >= 40.0: return cls.MEDIUM
        if score >= 20.0: return cls.LOW
        return cls.MINIMAL

    @property
    def is_actionable(self) -> bool:
        """True when risk level requires explicit risk management action."""
        return self in {RiskLevel.CRITICAL, RiskLevel.HIGH}

    @property
    def numeric(self) -> int:
        return {"critical": 5, "high": 4, "medium": 3, "low": 2, "minimal": 1}[self.value]

    @property
    def blocks_execution(self) -> bool:
        return self == RiskLevel.CRITICAL


class RiskDimension(str, Enum):
    MARKET     = "market"
    COMPANY    = "company"
    STRATEGY   = "strategy"
    EXECUTION  = "execution"
    CONFIDENCE = "confidence"

    @property
    def default_weight(self) -> float:
        return {
            "market":     0.30,
            "company":    0.25,
            "strategy":   0.20,
            "execution":  0.15,
            "confidence": 0.10,
        }[self.value]


class ScenarioType(str, Enum):
    BULL_MARKET       = "bull_market"
    BEAR_MARKET       = "bear_market"
    SIDEWAYS_MARKET   = "sideways_market"
    VOLATILITY_SPIKE  = "volatility_spike"
    FLASH_CRASH       = "flash_crash"
    LIQUIDITY_CRISIS  = "liquidity_crisis"
    MACRO_SHOCK       = "macro_shock"
    SECTOR_SHOCK      = "sector_shock"
    BASE_CASE         = "base_case"

    @property
    def is_adverse(self) -> bool:
        return self in {
            ScenarioType.BEAR_MARKET,
            ScenarioType.FLASH_CRASH,
            ScenarioType.LIQUIDITY_CRISIS,
            ScenarioType.MACRO_SHOCK,
        }


class RiskControlStatus(str, Enum):
    ACTIVE   = "active"
    BREACHED = "breached"
    WARNING  = "warning"
    INACTIVE = "inactive"
    BYPASSED = "bypassed"

    @property
    def blocks_execution(self) -> bool:
        return self == RiskControlStatus.BREACHED


class RiskPolicyStatus(str, Enum):
    COMPLIANT     = "compliant"
    VIOLATION     = "violation"
    WARNING       = "warning"
    NOT_EVALUATED = "not_evaluated"

    @property
    def allows_execution(self) -> bool:
        return self in {RiskPolicyStatus.COMPLIANT, RiskPolicyStatus.WARNING}


class ExposureLevel(str, Enum):
    OVER_EXPOSED  = "over_exposed"    # > 80 %
    HIGH          = "high"            # > 60 %
    MODERATE      = "moderate"        # > 40 %
    LOW           = "low"             # > 20 %
    MINIMAL       = "minimal"         # <= 20 %

    @classmethod
    def from_fraction(cls, fraction: float) -> "ExposureLevel":
        if fraction > 0.80: return cls.OVER_EXPOSED
        if fraction > 0.60: return cls.HIGH
        if fraction > 0.40: return cls.MODERATE
        if fraction > 0.20: return cls.LOW
        return cls.MINIMAL


class RiskEngineStatus(str, Enum):
    INITIALIZING = "initializing"
    READY        = "ready"
    EVALUATING   = "evaluating"
    DEGRADED     = "degraded"
    STOPPED      = "stopped"

    @property
    def is_operational(self) -> bool:
        return self in {
            RiskEngineStatus.READY,
            RiskEngineStatus.EVALUATING,
            RiskEngineStatus.DEGRADED,
        }


class RiskQualityGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

    @classmethod
    def from_quality(cls, score: float) -> "RiskQualityGrade":
        if score >= 90.0: return cls.A
        if score >= 75.0: return cls.B
        if score >= 60.0: return cls.C
        if score >= 45.0: return cls.D
        return cls.F


# ─── Dimension weights (must sum to 1.0) ─────────────────────────────────────
MARKET_RISK_WEIGHT     = 0.30
COMPANY_RISK_WEIGHT    = 0.25
STRATEGY_RISK_WEIGHT   = 0.20
EXECUTION_RISK_WEIGHT  = 0.15
CONFIDENCE_RISK_WEIGHT = 0.10

# ─── Risk thresholds ─────────────────────────────────────────────────────────
CRITICAL_RISK_THRESHOLD = 80.0
HIGH_RISK_THRESHOLD     = 60.0
MEDIUM_RISK_THRESHOLD   = 40.0
LOW_RISK_THRESHOLD      = 20.0

MAX_ALLOWED_RISK_DEFAULT = 70.0      # default policy cap
MAX_CAPITAL_EXPOSURE_PCT = 0.05      # 5 % per decision default
MAX_SECTOR_CONCENTRATION = 0.30      # 30 % max same-sector
EXECUTION_RISK_CONF_FLOOR = 40.0     # confidence below this = high exec risk

# ─── Scenario parameters ─────────────────────────────────────────────────────
DEFAULT_SCENARIO_PROBABILITY = 0.10  # 10 % base probability per scenario
SCENARIO_WORST_CASE_WEIGHT   = 0.25  # weight given to worst-case scenario
SCENARIO_AVERAGE_WEIGHT      = 0.75  # weight given to average scenario

# ─── Exposure defaults ───────────────────────────────────────────────────────
DEFAULT_CAPITAL_AT_RISK_PCT  = 0.02  # 2 % if no position data provided
MIN_EVIDENCE_ITEMS_LOW_RISK  = 5     # fewer items → elevated evidence gap risk

# ─── Performance ─────────────────────────────────────────────────────────────
DEFAULT_RISK_TIMEOUT_SECS = 10.0
HISTORY_WINDOW_SIZE       = 100
