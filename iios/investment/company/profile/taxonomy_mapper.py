"""iios/investment/company/profile/taxonomy_mapper.py
Maps GICS/ICB/NAICS codes to human-readable sector/industry descriptions.
"""
from __future__ import annotations

from typing import Dict, Optional

# ── GICS Sector codes ─────────────────────────────────────────────────────────
GICS_SECTORS: Dict[str, str] = {
    "10": "Energy",
    "15": "Materials",
    "20": "Industrials",
    "25": "Consumer Discretionary",
    "30": "Consumer Staples",
    "35": "Health Care",
    "40": "Financials",
    "45": "Information Technology",
    "50": "Communication Services",
    "55": "Utilities",
    "60": "Real Estate",
}

# ── GICS Industry Group codes (first 4 digits) ────────────────────────────────
GICS_INDUSTRY_GROUPS: Dict[str, str] = {
    "1010": "Energy",
    "1510": "Materials",
    "2010": "Capital Goods",
    "2020": "Commercial & Professional Services",
    "2030": "Transportation",
    "2510": "Automobiles & Components",
    "2520": "Consumer Durables & Apparel",
    "2530": "Consumer Services",
    "2550": "Retailing",
    "3010": "Food & Staples Retailing",
    "3020": "Food, Beverage & Tobacco",
    "3030": "Household & Personal Products",
    "3510": "Health Care Equipment & Services",
    "3520": "Pharmaceuticals, Biotechnology & Life Sciences",
    "4010": "Banks",
    "4020": "Diversified Financials",
    "4030": "Insurance",
    "4510": "Software & Services",
    "4520": "Technology Hardware & Equipment",
    "4530": "Semiconductors & Semiconductor Equipment",
    "5010": "Telecommunication Services",
    "5020": "Media & Entertainment",
    "5510": "Utilities",
    "6010": "Equity Real Estate Investment Trusts",
    "6020": "Real Estate Management & Development",
}

# ── ICB Sector codes ──────────────────────────────────────────────────────────
ICB_SECTORS: Dict[str, str] = {
    "0001": "Technology",
    "1000": "Telecommunications",
    "2000": "Health Care",
    "3000": "Financials",
    "4000": "Real Estate",
    "5000": "Consumer Discretionary",
    "6000": "Consumer Staples",
    "7000": "Industrials",
    "8000": "Basic Materials",
    "9000": "Energy",
    "9500": "Utilities",
}

# ── NSE India Sector mapping ──────────────────────────────────────────────────
NSE_SECTORS: Dict[str, str] = {
    "NIFTY AUTO":         "Automobiles",
    "NIFTY BANK":         "Banking",
    "NIFTY ENERGY":       "Energy",
    "NIFTY FMCG":         "FMCG",
    "NIFTY FINANCIAL SERVICES": "Financial Services",
    "NIFTY IT":           "Information Technology",
    "NIFTY MEDIA":        "Media",
    "NIFTY METAL":        "Metals",
    "NIFTY PHARMA":       "Pharmaceuticals",
    "NIFTY PSU BANK":     "PSU Banking",
    "NIFTY REALTY":       "Real Estate",
}


class TaxonomyMapper:
    """Maps taxonomy codes to human-readable labels."""

    def gics_sector(self, code: str) -> Optional[str]:
        """Resolve 2-digit GICS sector code."""
        return GICS_SECTORS.get(code[:2] if len(code) >= 2 else code)

    def gics_industry_group(self, code: str) -> Optional[str]:
        return GICS_INDUSTRY_GROUPS.get(code[:4] if len(code) >= 4 else code)

    def icb_sector(self, code: str) -> Optional[str]:
        return ICB_SECTORS.get(code)

    def nse_sector(self, index_name: str) -> Optional[str]:
        return NSE_SECTORS.get(index_name.upper())

    def all_gics_sectors(self) -> Dict[str, str]:
        return dict(GICS_SECTORS)

    def all_icb_sectors(self) -> Dict[str, str]:
        return dict(ICB_SECTORS)

    def all_nse_sectors(self) -> Dict[str, str]:
        return dict(NSE_SECTORS)
