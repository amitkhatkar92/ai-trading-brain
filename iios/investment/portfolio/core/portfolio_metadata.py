"""iios/investment/portfolio/core/portfolio_metadata.py

Rich metadata attached to every portfolio managed by the framework.
Metadata is immutable after construction and version-stamped.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, FrozenSet, Optional

from iios.investment.portfolio.core.portfolio_types import (
    PortfolioCapability,
    PortfolioDomain,
    PortfolioVersion,
)
from iios.investment.portfolio.core.investment_style import (
    InvestmentStyle,
    InvestmentHorizon,
)
from iios.investment.portfolio.portfolio_constants import RiskLevel


@dataclass(frozen=True)
class PortfolioMetadata:
    """
    Immutable descriptor for a portfolio.

    Attached at registration time and never mutated.  Changes require
    creating a new metadata instance with an incremented version.
    """

    # Identity
    portfolio_id:    str              = field(default_factory=lambda: str(uuid.uuid4()))
    name:            str              = ""
    display_name:    str              = ""
    description:     str              = ""
    version:         str              = "1.0.0"
    schema_version:  PortfolioVersion = PortfolioVersion.V1

    # Classification
    domain:          PortfolioDomain  = PortfolioDomain.CUSTOM
    style:           InvestmentStyle  = InvestmentStyle.UNKNOWN
    horizon:         InvestmentHorizon= InvestmentHorizon.MEDIUM_TERM
    risk_level:      RiskLevel        = RiskLevel.UNKNOWN

    # Ownership / governance
    owner:           str              = ""
    manager:         str              = ""
    custodian:       str              = ""
    broker:          str              = ""
    account_id:      str              = ""
    fund_code:       str              = ""
    benchmark:       str              = ""
    base_currency:   str              = "INR"

    # Capabilities declared by the implementation
    capabilities:    FrozenSet[PortfolioCapability] = field(default_factory=frozenset)

    # Taxonomy / discovery
    tags:            FrozenSet[str]   = field(default_factory=frozenset)
    labels:          FrozenSet[str]   = field(default_factory=frozenset)
    category:        str              = ""
    sub_category:    str              = ""

    # Constraints summary (informational — enforcement is in configuration)
    min_capital:     float            = 0.0
    max_capital:     float            = 1e12   # 1 trillion default ceiling
    min_positions:   int              = 0
    max_positions:   int              = 10_000

    # Provenance
    class_module:    str              = ""     # dotted module path of implementation
    class_name:      str              = ""     # class name of implementation
    created_at:      float            = field(default_factory=time.time)
    created_by:      str              = ""
    notes:           str              = ""

    # Extended attributes (arbitrary key-value pairs)
    attributes:      dict[str, Any]   = field(default_factory=dict)

    def has_capability(self, cap: PortfolioCapability) -> bool:
        return cap in self.capabilities

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id":   self.portfolio_id,
            "name":           self.name,
            "display_name":   self.display_name,
            "description":    self.description,
            "version":        self.version,
            "schema_version": self.schema_version.value,
            "domain":         self.domain.value,
            "style":          self.style.value,
            "horizon":        self.horizon.value,
            "risk_level":     self.risk_level.value,
            "owner":          self.owner,
            "manager":        self.manager,
            "custodian":      self.custodian,
            "broker":         self.broker,
            "account_id":     self.account_id,
            "benchmark":      self.benchmark,
            "base_currency":  self.base_currency,
            "capabilities":   sorted(c.value for c in self.capabilities),
            "tags":           sorted(self.tags),
            "labels":         sorted(self.labels),
            "category":       self.category,
            "min_capital":    self.min_capital,
            "max_capital":    self.max_capital,
            "min_positions":  self.min_positions,
            "max_positions":  self.max_positions,
            "class_module":   self.class_module,
            "class_name":     self.class_name,
            "created_at":     self.created_at,
            "created_by":     self.created_by,
            "notes":          self.notes,
            "attributes":     dict(self.attributes),
        }


def build_metadata(
    portfolio_id:  str,
    name:          str,
    domain:        PortfolioDomain,
    *,
    display_name:  str                  = "",
    description:   str                  = "",
    version:       str                  = "1.0.0",
    style:         InvestmentStyle      = InvestmentStyle.UNKNOWN,
    horizon:       InvestmentHorizon    = InvestmentHorizon.MEDIUM_TERM,
    risk_level:    RiskLevel            = RiskLevel.UNKNOWN,
    owner:         str                  = "",
    base_currency: str                  = "INR",
    benchmark:     str                  = "",
    capabilities:  Optional[FrozenSet[PortfolioCapability]] = None,
    tags:          Optional[FrozenSet[str]]                 = None,
    class_module:  str                  = "",
    class_name:    str                  = "",
    created_by:    str                  = "",
    min_capital:   float                = 0.0,
    max_capital:   float                = 1e12,
    max_positions: int                  = 10_000,
    attributes:    Optional[dict[str, Any]] = None,
) -> PortfolioMetadata:
    """Factory function for PortfolioMetadata with sensible defaults."""
    return PortfolioMetadata(
        portfolio_id  = portfolio_id,
        name          = name,
        display_name  = display_name or name,
        description   = description,
        version       = version,
        domain        = domain,
        style         = style,
        horizon       = horizon,
        risk_level    = risk_level,
        owner         = owner,
        base_currency = base_currency,
        benchmark     = benchmark,
        capabilities  = capabilities or frozenset(),
        tags          = tags or frozenset(),
        class_module  = class_module,
        class_name    = class_name,
        created_by    = created_by,
        min_capital   = min_capital,
        max_capital   = max_capital,
        max_positions = max_positions,
        attributes    = attributes or {},
    )
