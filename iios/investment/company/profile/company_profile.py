"""iios/investment/company/profile/company_profile.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.profile.company_identity import CompanyIdentity
from iios.investment.company.profile.company_metadata import CompanyMetadata
from iios.investment.company.profile.company_snapshot import CompanySnapshot


@dataclass
class CompanyProfile:
    """
    Unified profile for a listed company.

    Holds identity, metadata, latest snapshot, and raw financial/
    ownership/governance data ready for analysis.
    """

    profile_id:      str             = field(default_factory=lambda: str(uuid.uuid4()))
    company_id:      str             = ""
    identity:        CompanyIdentity = field(default_factory=CompanyIdentity)
    company_meta:    CompanyMetadata = field(default_factory=CompanyMetadata)

    # Latest snapshot (populated after each analysis cycle)
    latest_snapshot: CompanySnapshot | None = None

    # Raw data stores (dict inputs from data providers)
    income_data:     dict[str, Any] = field(default_factory=dict)
    balance_data:    dict[str, Any] = field(default_factory=dict)
    cashflow_data:   dict[str, Any] = field(default_factory=dict)
    valuation_data:  dict[str, Any] = field(default_factory=dict)
    ownership_data:  dict[str, Any] = field(default_factory=dict)
    governance_data: dict[str, Any] = field(default_factory=dict)
    corporate_actions_raw: list[dict[str, Any]] = field(default_factory=list)

    metadata:        dict[str, Any] = field(default_factory=dict)
    created_at:      float          = field(default_factory=time.time)
    updated_at:      float          = field(default_factory=time.time)

    # ── mutation helpers ──────────────────────────────────────────────────────

    def update_snapshot(self, snapshot: CompanySnapshot) -> None:
        self.latest_snapshot = snapshot
        self.updated_at      = time.time()

    def update_financials(
        self,
        income:   dict[str, Any],
        balance:  dict[str, Any],
        cashflow: dict[str, Any],
    ) -> None:
        self.income_data   = income
        self.balance_data  = balance
        self.cashflow_data = cashflow
        self.updated_at    = time.time()

    def update_ownership(self, ownership: dict[str, Any]) -> None:
        self.ownership_data = ownership
        self.updated_at     = time.time()

    def update_governance(self, governance: dict[str, Any]) -> None:
        self.governance_data = governance
        self.updated_at      = time.time()

    def add_corporate_action(self, action: dict[str, Any]) -> None:
        self.corporate_actions_raw.append(action)
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id":   self.profile_id,
            "company_id":   self.company_id,
            "identity":     self.identity.to_dict(),
            "company_meta": self.company_meta.to_dict(),
            "has_snapshot": self.latest_snapshot is not None,
            "has_financials": bool(self.income_data),
            "has_ownership":  bool(self.ownership_data),
            "has_governance": bool(self.governance_data),
            "metadata":     self.metadata,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
        }
