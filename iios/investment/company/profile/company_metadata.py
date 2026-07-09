"""iios/investment/company/profile/company_metadata.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import BusinessModel, CompanyStage


@dataclass
class CompanyMetadata:
    """Business characteristics and descriptive attributes."""

    company_id:     str          = ""
    business_model: BusinessModel = BusinessModel.UNKNOWN
    stage:          CompanyStage  = CompanyStage.UNKNOWN
    founded_year:   int | None   = None
    employees:      int          = 0
    headquarters:   str          = ""
    description:    str          = ""
    products:       list[str]    = field(default_factory=list)
    geographies:    list[str]    = field(default_factory=list)
    competitors:    list[str]    = field(default_factory=list)
    key_risks:      list[str]    = field(default_factory=list)
    tags:           list[str]    = field(default_factory=list)
    attributes:     dict[str, Any] = field(default_factory=dict)
    updated_at:     float        = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id":     self.company_id,
            "business_model": self.business_model.value,
            "stage":          self.stage.value,
            "founded_year":   self.founded_year,
            "employees":      self.employees,
            "headquarters":   self.headquarters,
            "description":    self.description,
            "products":       self.products,
            "geographies":    self.geographies,
            "competitors":    self.competitors,
            "key_risks":      self.key_risks,
            "tags":           self.tags,
            "attributes":     self.attributes,
            "updated_at":     self.updated_at,
        }
