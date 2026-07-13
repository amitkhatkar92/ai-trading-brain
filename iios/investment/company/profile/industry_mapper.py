"""iios/investment/company/profile/industry_mapper.py
NSE/BSE sector and industry-level mappings for Indian markets.
Maps company tickers/sectors to standardised industry groups.
"""
from __future__ import annotations

from typing import Dict, List, Optional

# NSE sector → constituent industry groups
_NSE_SECTOR_INDUSTRIES: Dict[str, List[str]] = {
    "Automobiles":           ["Auto OEMs", "Auto Ancillaries", "EV Components"],
    "Banking":               ["Private Banks", "PSU Banks", "Small Finance Banks"],
    "Energy":                ["Oil & Gas", "Refineries", "Gas Distribution", "Renewable Energy"],
    "FMCG":                  ["Foods", "Beverages", "Personal Care", "Tobacco", "Household Products"],
    "Financial Services":    ["NBFCs", "Insurance", "Brokers", "Fintech"],
    "Information Technology": ["IT Services", "IT Products", "BPO/KPO", "Software"],
    "Media":                 ["Broadcasting", "Print", "Digital Media", "Entertainment"],
    "Metals":                ["Steel", "Aluminium", "Copper", "Mining", "Precious Metals"],
    "Pharmaceuticals":       ["Bulk Drugs", "Formulations", "CRO/CRAMS", "Diagnostics"],
    "Real Estate":           ["Residential", "Commercial", "REITs"],
    "Chemicals":             ["Specialty Chemicals", "Agrochemicals", "Dyes & Pigments"],
    "Cement":                ["Large Cap Cement", "Small Cap Cement"],
    "Infrastructure":        ["Roads", "Railways", "Ports", "Airports", "Construction"],
    "Telecom":               ["Wireless", "Broadband", "Towers"],
    "Textiles":              ["Cotton", "Synthetic", "Readymade Garments"],
    "Consumer Durables":     ["White Goods", "Electronics", "Furniture"],
    "Utilities":             ["Power Generation", "Power Distribution", "Gas"],
    "Healthcare":            ["Hospitals", "Medical Devices", "Diagnostics"],
    "Capital Goods":         ["Industrial Machinery", "Defence", "Electrical Equipment"],
    "Agriculture":           ["Seeds", "Fertilizers", "Crop Protection"],
}

# Standard industry group → GICS equivalent
_INDUSTRY_TO_GICS: Dict[str, str] = {
    "Private Banks":         "Banks",
    "PSU Banks":             "Banks",
    "NBFCs":                 "Diversified Financials",
    "IT Services":           "Software & Services",
    "Oil & Gas":             "Energy",
    "Bulk Drugs":            "Pharmaceuticals, Biotechnology & Life Sciences",
    "Auto OEMs":             "Automobiles & Components",
    "Auto Ancillaries":      "Automobiles & Components",
    "Steel":                 "Materials",
    "Specialty Chemicals":   "Materials",
}


class IndustryMapper:
    """Industry-level mapping utilities for NSE/BSE markets."""

    def industries_for_sector(self, sector: str) -> List[str]:
        return _NSE_SECTOR_INDUSTRIES.get(sector, [])

    def all_sectors(self) -> List[str]:
        return sorted(_NSE_SECTOR_INDUSTRIES.keys())

    def gics_equivalent(self, industry: str) -> Optional[str]:
        return _INDUSTRY_TO_GICS.get(industry)

    def sector_for_industry(self, industry: str) -> Optional[str]:
        for sector, industries in _NSE_SECTOR_INDUSTRIES.items():
            if industry in industries:
                return sector
        return None

    def all_industries(self) -> List[str]:
        all_ind: List[str] = []
        for industries in _NSE_SECTOR_INDUSTRIES.values():
            all_ind.extend(industries)
        return sorted(set(all_ind))
