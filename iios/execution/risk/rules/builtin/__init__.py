"""iios/execution/risk/rules/builtin/__init__.py
==================================================
Built-in risk rules for the IIOS Execution Risk Rules Framework.

C6 Execution Intelligence — Phase 4, Module 3
"""
from .compliance_rule import ComplianceRule
from .daily_loss_rule import DailyLossRule
from .duplicate_order_rule import DuplicateOrderRule
from .emergency_stop_rule import EmergencyStopRule
from .exposure_rule import ExposureRule
from .liquidity_rule import LiquidityRule
from .margin_rule import MarginRule
from .operational_health_rule import OperationalHealthRule
from .order_size_rule import OrderSizeRule
from .position_limit_rule import PositionLimitRule
from .price_deviation_rule import PriceDeviationRule
from .session_rule import SessionRule

__all__ = [
    "ComplianceRule",
    "DailyLossRule",
    "DuplicateOrderRule",
    "EmergencyStopRule",
    "ExposureRule",
    "LiquidityRule",
    "MarginRule",
    "OperationalHealthRule",
    "OrderSizeRule",
    "PositionLimitRule",
    "PriceDeviationRule",
    "SessionRule",
]

ALL_BUILTIN_RULES = [
    EmergencyStopRule,
    ComplianceRule,
    ExposureRule,
    MarginRule,
    LiquidityRule,
    OrderSizeRule,
    PositionLimitRule,
    DailyLossRule,
    PriceDeviationRule,
    SessionRule,
    OperationalHealthRule,
    DuplicateOrderRule,
]
