"""enterprise_ai_platform/investment/company/ownership/shareholder_value.py
Shareholder value dataclass profile re-export and convenience.
(Actual engine is in value_creation.py)
"""
from enterprise_ai_platform.investment.company.ownership.value_creation import ShareholderValueEngine
from enterprise_ai_platform.investment.company.ownership.ownership_profile import (
    ShareholderValueProfile,
    ShareholderValueLabel,
)

__all__ = ["ShareholderValueEngine", "ShareholderValueProfile", "ShareholderValueLabel"]
