"""iios/investment/company/profile/classification_engine.py
Assigns and manages CompanyClassification from raw inputs or sector/industry.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.profile.models import (
    CompanyClassification,
    TaxonomyType,
)
from iios.investment.company.profile.taxonomy_mapper import TaxonomyMapper
from iios.investment.company.profile.theme_mapper import ThemeMapper


class ClassificationEngine:
    """Builds and validates CompanyClassification objects."""

    def __init__(self) -> None:
        self._taxonomy = TaxonomyMapper()
        self._themes   = ThemeMapper()

    def build(
        self,
        *,
        taxonomy_type:       TaxonomyType = TaxonomyType.GICS,
        gics_sector_code:    Optional[str] = None,
        gics_industry_group: Optional[str] = None,
        gics_industry:       Optional[str] = None,
        gics_sub_industry:   Optional[str] = None,
        icb_sector_code:     Optional[str] = None,
        icb_subsector:       Optional[str] = None,
        naics_code:          Optional[str] = None,
        nse_sector:          Optional[str] = None,
        investment_themes:   Optional[List[str]] = None,
        megatrends:          Optional[List[str]] = None,
        custom_tags:         Optional[List[str]] = None,
    ) -> CompanyClassification:
        # Resolve GICS sector label from code
        gics_sector_label = None
        if gics_sector_code:
            gics_sector_label = self._taxonomy.gics_sector(gics_sector_code)

        # Resolve ICB sector label
        icb_sector_label = None
        if icb_sector_code:
            icb_sector_label = self._taxonomy.icb_sector(icb_sector_code)

        # Auto-suggest themes from NSE sector if not provided
        themes = list(investment_themes or [])
        if not themes and nse_sector:
            themes = self._themes.themes_for_sector(nse_sector)

        # Auto-suggest megatrends from themes if not provided
        mega = list(megatrends or [])
        if not mega and themes:
            mega = self._themes.suggest_megatrends(themes)

        return CompanyClassification(
            taxonomy_type=taxonomy_type,
            gics_sector=gics_sector_label or gics_sector_code,
            gics_industry_group=gics_industry_group,
            gics_industry=gics_industry,
            gics_sub_industry=gics_sub_industry,
            icb_sector=icb_sector_label or icb_sector_code,
            icb_subsector=icb_subsector,
            naics_code=naics_code,
            nse_sector=nse_sector,
            investment_themes=themes,
            megatrends=mega,
            custom_tags=list(custom_tags or []),
        )

    def update_themes(
        self,
        classification: CompanyClassification,
        add: Optional[List[str]] = None,
        remove: Optional[List[str]] = None,
    ) -> CompanyClassification:
        themes = set(classification.investment_themes)
        if add:
            themes.update(add)
        if remove:
            themes -= set(remove)
        classification.investment_themes = sorted(themes)
        # Re-derive megatrends
        classification.megatrends = self._themes.suggest_megatrends(
            classification.investment_themes
        )
        return classification

    def validate(self, classification: CompanyClassification) -> List[str]:
        """Return list of validation warnings (empty = ok)."""
        warnings = []
        for theme in classification.investment_themes:
            if not self._themes.is_valid_theme(theme):
                warnings.append(f"Unknown investment theme: {theme}")
        for trend in classification.megatrends:
            if not self._themes.is_valid_megatrend(trend):
                warnings.append(f"Unknown megatrend: {trend}")
        return warnings
