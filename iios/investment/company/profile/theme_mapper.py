"""iios/investment/company/profile/theme_mapper.py
Maps companies to investment themes and megatrends.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

# Canonical investment themes
INVESTMENT_THEMES: List[str] = [
    "Artificial Intelligence",
    "Cloud Computing",
    "Cybersecurity",
    "Digital Payments",
    "Electric Vehicles",
    "Renewable Energy",
    "Healthcare Technology",
    "5G Connectivity",
    "Defence & Aerospace",
    "Financial Inclusion",
    "E-Commerce",
    "Semiconductor",
    "Robotics & Automation",
    "Data Analytics",
    "Infrastructure Development",
    "Smart Cities",
    "Specialty Chemicals",
    "PLI Beneficiary",
    "Export-Oriented",
    "Domestic Consumption",
]

# Megatrends (longer duration structural shifts)
MEGATRENDS: List[str] = [
    "Decarbonization",
    "Digitization",
    "Deglobalization",
    "Demographic Shift",
    "Urbanization",
    "Energy Transition",
    "Health & Wellness",
    "Middle Class Expansion",
    "Supply Chain Resilience",
    "Water & Food Security",
]

# Sector → likely themes
_SECTOR_THEMES: Dict[str, List[str]] = {
    "Information Technology": ["Artificial Intelligence", "Cloud Computing", "Cybersecurity",
                               "Digital Payments", "Data Analytics"],
    "Pharmaceuticals":        ["Healthcare Technology", "Health & Wellness"],
    "Automobiles":            ["Electric Vehicles", "Robotics & Automation"],
    "Energy":                 ["Renewable Energy", "Decarbonization", "Energy Transition"],
    "Banking":                ["Digital Payments", "Financial Inclusion"],
    "Defence":                ["Defence & Aerospace"],
    "Chemicals":              ["Specialty Chemicals"],
    "Infrastructure":         ["Infrastructure Development", "Smart Cities"],
    "Telecom":                ["5G Connectivity"],
    "Semiconductors":         ["Semiconductor", "Artificial Intelligence"],
}


class ThemeMapper:
    """Maps companies to investment themes and megatrends."""

    def themes_for_sector(self, sector: str) -> List[str]:
        return list(_SECTOR_THEMES.get(sector, []))

    def all_themes(self) -> List[str]:
        return list(INVESTMENT_THEMES)

    def all_megatrends(self) -> List[str]:
        return list(MEGATRENDS)

    def is_valid_theme(self, theme: str) -> bool:
        return theme in INVESTMENT_THEMES

    def is_valid_megatrend(self, trend: str) -> bool:
        return trend in MEGATRENDS

    def suggest_themes(
        self,
        sector: str,
        industry: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> List[str]:
        suggested: Set[str] = set(self.themes_for_sector(sector))
        if keywords:
            for kw in keywords:
                for theme in INVESTMENT_THEMES:
                    if kw.lower() in theme.lower():
                        suggested.add(theme)
        return sorted(suggested)

    def suggest_megatrends(self, themes: List[str]) -> List[str]:
        mapping = {
            "Renewable Energy":       "Decarbonization",
            "Electric Vehicles":      "Decarbonization",
            "Artificial Intelligence": "Digitization",
            "Cloud Computing":        "Digitization",
            "Digital Payments":       "Digitization",
            "Healthcare Technology":  "Health & Wellness",
            "Financial Inclusion":    "Middle Class Expansion",
            "Infrastructure Development": "Urbanization",
        }
        suggested: Set[str] = set()
        for theme in themes:
            mt = mapping.get(theme)
            if mt:
                suggested.add(mt)
        return sorted(suggested)
