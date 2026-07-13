"""tests/unit/investment/company/profile/test_classification.py"""
from __future__ import annotations

import pytest

from iios.investment.company.profile.classification_engine import ClassificationEngine
from iios.investment.company.profile.industry_mapper import IndustryMapper
from iios.investment.company.profile.taxonomy_mapper import TaxonomyMapper
from iios.investment.company.profile.theme_mapper import ThemeMapper
from iios.investment.company.profile.models import TaxonomyType


class TestTaxonomyMapper:
    def test_gics_sector_by_code(self):
        mapper = TaxonomyMapper()
        assert mapper.gics_sector("45") == "Information Technology"
        assert mapper.gics_sector("10") == "Energy"

    def test_gics_sector_unknown(self):
        mapper = TaxonomyMapper()
        assert mapper.gics_sector("99") is None

    def test_gics_industry_group(self):
        mapper = TaxonomyMapper()
        assert mapper.gics_industry_group("4510") == "Software & Services"

    def test_icb_sector(self):
        mapper = TaxonomyMapper()
        assert mapper.icb_sector("0001") == "Technology"

    def test_all_gics_sectors_nonempty(self):
        mapper = TaxonomyMapper()
        assert len(mapper.all_gics_sectors()) > 0

    def test_all_icb_sectors_nonempty(self):
        mapper = TaxonomyMapper()
        assert len(mapper.all_icb_sectors()) > 0


class TestIndustryMapper:
    def test_industries_for_sector(self):
        mapper = IndustryMapper()
        industries = mapper.industries_for_sector("Banking")
        assert "Private Banks" in industries
        assert "PSU Banks" in industries

    def test_sector_for_industry(self):
        mapper = IndustryMapper()
        sector = mapper.sector_for_industry("Private Banks")
        assert sector == "Banking"

    def test_unknown_industry(self):
        mapper = IndustryMapper()
        assert mapper.sector_for_industry("UNKNOWN_INDUSTRY") is None

    def test_all_sectors_nonempty(self):
        mapper = IndustryMapper()
        assert len(mapper.all_sectors()) > 5

    def test_all_industries_nonempty(self):
        mapper = IndustryMapper()
        assert len(mapper.all_industries()) > 10

    def test_gics_equivalent(self):
        mapper = IndustryMapper()
        assert mapper.gics_equivalent("Private Banks") == "Banks"


class TestThemeMapper:
    def test_themes_for_sector(self):
        mapper  = ThemeMapper()
        themes  = mapper.themes_for_sector("Information Technology")
        assert "Artificial Intelligence" in themes or "Cloud Computing" in themes

    def test_all_themes_nonempty(self):
        mapper = ThemeMapper()
        assert len(mapper.all_themes()) >= 10

    def test_all_megatrends_nonempty(self):
        mapper = ThemeMapper()
        assert len(mapper.all_megatrends()) >= 5

    def test_is_valid_theme(self):
        mapper = ThemeMapper()
        assert mapper.is_valid_theme("Artificial Intelligence") is True
        assert mapper.is_valid_theme("INVALID_THEME_XYZ") is False

    def test_is_valid_megatrend(self):
        mapper = ThemeMapper()
        assert mapper.is_valid_megatrend("Digitization") is True
        assert mapper.is_valid_megatrend("INVALID") is False

    def test_suggest_themes(self):
        mapper    = ThemeMapper()
        suggested = mapper.suggest_themes("Energy", keywords=["renewable"])
        assert isinstance(suggested, list)

    def test_suggest_megatrends(self):
        mapper = ThemeMapper()
        mega   = mapper.suggest_megatrends(["Renewable Energy", "Cloud Computing"])
        assert "Decarbonization" in mega or "Digitization" in mega


class TestClassificationEngine:
    def test_build_with_gics_code(self):
        engine = ClassificationEngine()
        clf    = engine.build(gics_sector_code="45", nse_sector="Information Technology")
        assert clf.gics_sector == "Information Technology"

    def test_build_with_nse_sector_auto_themes(self):
        engine = ClassificationEngine()
        clf    = engine.build(nse_sector="Information Technology")
        assert len(clf.investment_themes) > 0

    def test_build_explicit_themes(self):
        engine = ClassificationEngine()
        clf    = engine.build(
            nse_sector="Energy",
            investment_themes=["Renewable Energy"],
        )
        assert "Renewable Energy" in clf.investment_themes

    def test_build_auto_megatrends(self):
        engine = ClassificationEngine()
        clf    = engine.build(
            nse_sector="Energy",
            investment_themes=["Renewable Energy"],
        )
        assert len(clf.megatrends) > 0

    def test_update_themes_add(self):
        engine = ClassificationEngine()
        clf    = engine.build()
        engine.update_themes(clf, add=["Artificial Intelligence"])
        assert "Artificial Intelligence" in clf.investment_themes

    def test_update_themes_remove(self):
        engine = ClassificationEngine()
        clf    = engine.build(investment_themes=["Artificial Intelligence", "Cloud Computing"])
        engine.update_themes(clf, remove=["Cloud Computing"])
        assert "Cloud Computing" not in clf.investment_themes
        assert "Artificial Intelligence" in clf.investment_themes

    def test_validate_valid(self):
        engine = ClassificationEngine()
        clf    = engine.build(investment_themes=["Artificial Intelligence"])
        warns  = engine.validate(clf)
        assert warns == []

    def test_validate_invalid_theme(self):
        engine = ClassificationEngine()
        clf    = engine.build(investment_themes=["FAKE_THEME_XYZ"])
        warns  = engine.validate(clf)
        assert len(warns) > 0

    def test_taxonomy_type_default(self):
        engine = ClassificationEngine()
        clf    = engine.build()
        assert clf.taxonomy_type is TaxonomyType.GICS
