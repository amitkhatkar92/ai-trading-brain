"""iios/investment/market/sector_rotation/sector_taxonomy.py
Pluggable sector taxonomy supporting GICS, ICB, NSE and custom classifications.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Set

from iios.investment.market.sector_rotation.models import SectorCharacter, TaxonomyType

# ── GICS ──────────────────────────────────────────────────────────────────────

_GICS_SECTORS: List[str] = [
    "Information Technology",
    "Financials",
    "Health Care",
    "Consumer Discretionary",
    "Communication Services",
    "Industrials",
    "Consumer Staples",
    "Energy",
    "Utilities",
    "Real Estate",
    "Materials",
]

_GICS_CHARACTER: Dict[str, str] = {
    "Information Technology":   SectorCharacter.GROWTH.value,
    "Financials":               SectorCharacter.CYCLICAL.value,
    "Health Care":              SectorCharacter.DEFENSIVE.value,
    "Consumer Discretionary":   SectorCharacter.CYCLICAL.value,
    "Communication Services":   SectorCharacter.GROWTH.value,
    "Industrials":              SectorCharacter.CYCLICAL.value,
    "Consumer Staples":         SectorCharacter.DEFENSIVE.value,
    "Energy":                   SectorCharacter.CYCLICAL.value,
    "Utilities":                SectorCharacter.DEFENSIVE.value,
    "Real Estate":              SectorCharacter.VALUE.value,
    "Materials":                SectorCharacter.CYCLICAL.value,
}

_GICS_INDUSTRIES: Dict[str, List[str]] = {
    "Information Technology": [
        "Software", "Technology Hardware", "Semiconductors",
        "IT Services", "Electronic Equipment",
    ],
    "Financials": [
        "Banks", "Insurance", "Capital Markets",
        "Diversified Financials", "Consumer Finance",
    ],
    "Health Care": [
        "Pharmaceuticals", "Biotechnology", "Medical Devices",
        "Health Care Services", "Life Sciences Tools",
    ],
    "Consumer Discretionary": [
        "Automobiles", "Retailing", "Textiles",
        "Hotels Restaurants Leisure", "Media",
    ],
    "Communication Services": [
        "Telecom Services", "Media Entertainment",
        "Interactive Media",
    ],
    "Industrials": [
        "Capital Goods", "Transportation", "Commercial Services",
        "Defense", "Electrical Equipment",
    ],
    "Consumer Staples": [
        "Food Beverage", "Tobacco", "Household Products",
        "Personal Products", "Food Retailing",
    ],
    "Energy": [
        "Oil Gas", "Energy Equipment Services",
        "Renewable Energy",
    ],
    "Utilities": [
        "Electric Utilities", "Gas Utilities",
        "Water Utilities", "Multi-Utilities",
    ],
    "Real Estate": [
        "REITs", "Real Estate Management",
        "Real Estate Development",
    ],
    "Materials": [
        "Chemicals", "Metals Mining", "Paper Forest",
        "Construction Materials",
    ],
}

# ── ICB ───────────────────────────────────────────────────────────────────────

_ICB_SECTORS: List[str] = [
    "Technology",
    "Financials",
    "Health Care",
    "Consumer Cyclicals",
    "Telecommunications",
    "Industrials",
    "Consumer Non-Cyclicals",
    "Energy",
    "Utilities",
    "Real Estate",
    "Basic Materials",
]

_ICB_CHARACTER: Dict[str, str] = {
    "Technology":             SectorCharacter.GROWTH.value,
    "Financials":             SectorCharacter.CYCLICAL.value,
    "Health Care":            SectorCharacter.DEFENSIVE.value,
    "Consumer Cyclicals":     SectorCharacter.CYCLICAL.value,
    "Telecommunications":     SectorCharacter.DEFENSIVE.value,
    "Industrials":            SectorCharacter.CYCLICAL.value,
    "Consumer Non-Cyclicals": SectorCharacter.DEFENSIVE.value,
    "Energy":                 SectorCharacter.CYCLICAL.value,
    "Utilities":              SectorCharacter.DEFENSIVE.value,
    "Real Estate":            SectorCharacter.VALUE.value,
    "Basic Materials":        SectorCharacter.CYCLICAL.value,
}

_ICB_INDUSTRIES: Dict[str, List[str]] = {
    "Technology":             ["Software", "Hardware", "Semiconductors", "IT Services"],
    "Financials":             ["Banking", "Insurance", "Financial Services"],
    "Health Care":            ["Pharma", "Biotech", "Medical Equipment"],
    "Consumer Cyclicals":     ["Auto", "Retail", "Travel Leisure"],
    "Telecommunications":     ["Fixed Line", "Mobile Telecom"],
    "Industrials":            ["Industrial Engineering", "Aerospace Defense", "Transportation"],
    "Consumer Non-Cyclicals": ["Food Beverage", "Personal Goods", "Drug Retail"],
    "Energy":                 ["Oil Equipment", "Exploration Production", "Integrated Oil"],
    "Utilities":              ["Electricity", "Gas Water"],
    "Real Estate":            ["Property Investment", "Property Services"],
    "Basic Materials":        ["Chemicals", "Industrial Metals", "Mining"],
}

# ── NSE ───────────────────────────────────────────────────────────────────────

_NSE_SECTORS: List[str] = [
    "Banks",
    "IT",
    "FMCG",
    "Pharma",
    "Auto",
    "Metal",
    "Realty",
    "Media",
    "Energy",
    "Infrastructure",
    "PSU",
    "Financial Services",
]

_NSE_CHARACTER: Dict[str, str] = {
    "Banks":              SectorCharacter.CYCLICAL.value,
    "IT":                 SectorCharacter.GROWTH.value,
    "FMCG":               SectorCharacter.DEFENSIVE.value,
    "Pharma":             SectorCharacter.DEFENSIVE.value,
    "Auto":               SectorCharacter.CYCLICAL.value,
    "Metal":              SectorCharacter.CYCLICAL.value,
    "Realty":             SectorCharacter.CYCLICAL.value,
    "Media":              SectorCharacter.CYCLICAL.value,
    "Energy":             SectorCharacter.CYCLICAL.value,
    "Infrastructure":     SectorCharacter.CYCLICAL.value,
    "PSU":                SectorCharacter.VALUE.value,
    "Financial Services": SectorCharacter.CYCLICAL.value,
}

_NSE_INDUSTRIES: Dict[str, List[str]] = {
    "Banks":              ["Private Banks", "PSU Banks", "Small Finance Banks"],
    "IT":                 ["Software", "IT Consulting", "BPO"],
    "FMCG":               ["Food", "Beverages", "Personal Care"],
    "Pharma":             ["Domestic Pharma", "Export Pharma", "CDMO"],
    "Auto":               ["Passenger Vehicles", "Commercial Vehicles", "Auto Ancillaries"],
    "Metal":              ["Steel", "Aluminium", "Non-Ferrous Metals"],
    "Realty":             ["Residential", "Commercial", "Retail Real Estate"],
    "Media":              ["Broadcasting", "Print", "Digital Media"],
    "Energy":             ["Oil Gas", "Power", "Renewable"],
    "Infrastructure":     ["Construction", "Cement", "Roads"],
    "PSU":                ["PSU Banks", "Defense PSU", "Utilities PSU"],
    "Financial Services": ["NBFC", "Insurance", "Broking"],
}

# ── Registry ──────────────────────────────────────────────────────────────────

_TAXONOMY_DATA: Dict[str, Dict] = {
    TaxonomyType.GICS.value: {
        "sectors":    _GICS_SECTORS,
        "character":  _GICS_CHARACTER,
        "industries": _GICS_INDUSTRIES,
    },
    TaxonomyType.ICB.value: {
        "sectors":    _ICB_SECTORS,
        "character":  _ICB_CHARACTER,
        "industries": _ICB_INDUSTRIES,
    },
    TaxonomyType.NSE.value: {
        "sectors":    _NSE_SECTORS,
        "character":  _NSE_CHARACTER,
        "industries": _NSE_INDUSTRIES,
    },
}


# ── Protocol ──────────────────────────────────────────────────────────────────

class TaxonomyProvider(Protocol):
    def sectors(self) -> List[str]: ...
    def industries_for(self, sector: str) -> List[str]: ...
    def sector_for_industry(self, industry: str) -> Optional[str]: ...
    def character(self, sector: str) -> str: ...
    def is_defensive(self, sector: str) -> bool: ...
    def is_cyclical(self, sector: str) -> bool: ...
    def is_growth(self, sector: str) -> bool: ...


# ── Implementation ────────────────────────────────────────────────────────────

@dataclass
class SectorTaxonomy:
    """Multi-standard pluggable sector taxonomy.

    Supports GICS, ICB, NSE out of the box.  Custom taxonomies can be injected
    via ``register_custom``.
    """
    taxonomy_type: str = TaxonomyType.GICS.value
    _custom_sectors:    List[str]               = field(default_factory=list, repr=False)
    _custom_character:  Dict[str, str]          = field(default_factory=dict, repr=False)
    _custom_industries: Dict[str, List[str]]    = field(default_factory=dict, repr=False)

    # cache: industry → sector reverse map
    _reverse_map: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._rebuild_reverse_map()

    # ── configuration ─────────────────────────────────────────────────────────

    def register_custom(
        self,
        sectors: List[str],
        character: Dict[str, str],
        industries: Dict[str, List[str]],
    ) -> None:
        """Inject a custom taxonomy (switches taxonomy_type to CUSTOM)."""
        self.taxonomy_type = TaxonomyType.CUSTOM.value
        self._custom_sectors    = list(sectors)
        self._custom_character  = dict(character)
        self._custom_industries = {k: list(v) for k, v in industries.items()}
        self._rebuild_reverse_map()

    def _rebuild_reverse_map(self) -> None:
        self._reverse_map = {}
        for sector, inds in self._industries_map().items():
            for ind in inds:
                self._reverse_map[ind] = sector

    def _data(self) -> Dict:
        if self.taxonomy_type in _TAXONOMY_DATA:
            return _TAXONOMY_DATA[self.taxonomy_type]
        return {
            "sectors":    self._custom_sectors,
            "character":  self._custom_character,
            "industries": self._custom_industries,
        }

    def _industries_map(self) -> Dict[str, List[str]]:
        return self._data().get("industries", {})

    # ── public API ────────────────────────────────────────────────────────────

    def sectors(self) -> List[str]:
        return list(self._data()["sectors"])

    def industries_for(self, sector: str) -> List[str]:
        return list(self._data().get("industries", {}).get(sector, []))

    def all_industries(self) -> List[str]:
        result: List[str] = []
        for inds in self._industries_map().values():
            result.extend(inds)
        return result

    def sector_for_industry(self, industry: str) -> Optional[str]:
        return self._reverse_map.get(industry)

    def character(self, sector: str) -> str:
        return self._data().get("character", {}).get(sector, SectorCharacter.UNKNOWN.value)

    def is_defensive(self, sector: str) -> bool:
        return self.character(sector) == SectorCharacter.DEFENSIVE.value

    def is_cyclical(self, sector: str) -> bool:
        return self.character(sector) == SectorCharacter.CYCLICAL.value

    def is_growth(self, sector: str) -> bool:
        return self.character(sector) == SectorCharacter.GROWTH.value

    def is_value(self, sector: str) -> bool:
        return self.character(sector) == SectorCharacter.VALUE.value

    def defensive_sectors(self) -> List[str]:
        return [s for s in self.sectors() if self.is_defensive(s)]

    def cyclical_sectors(self) -> List[str]:
        return [s for s in self.sectors() if self.is_cyclical(s)]

    def growth_sectors(self) -> List[str]:
        return [s for s in self.sectors() if self.is_growth(s)]

    def known_sectors(self) -> Set[str]:
        return set(self._data()["sectors"])

    @staticmethod
    def for_type(taxonomy_type: str) -> "SectorTaxonomy":
        return SectorTaxonomy(taxonomy_type=taxonomy_type)
