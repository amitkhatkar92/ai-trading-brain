"""tests/unit/investment/company/profile/test_identity.py"""
from __future__ import annotations

import pytest

from iios.investment.company.profile.company_aliases import AliasStore, GlobalAliasIndex
from iios.investment.company.profile.identity_utils import (
    IdentityDiffer,
    IdentityNormaliser,
    IdentityValidator,
)
from iios.investment.company.profile.models import (
    AliasType,
    CompanyAlias,
    CompanyIdentity,
    CorporateStructure,
    ListingStatus,
)


class TestIdentityValidator:
    def test_valid_identity(self, identity):
        errors = IdentityValidator().validate(identity)
        assert errors == []

    def test_missing_ticker(self):
        ident  = CompanyIdentity(ticker="", name="TCS", exchange="NSE",
                                  country="IN", currency="INR")
        errors = IdentityValidator().validate(ident)
        assert any("ticker" in e for e in errors)

    def test_valid_isin(self):
        assert IdentityValidator.validate_isin("INE002A01018") is True

    def test_invalid_isin(self):
        assert IdentityValidator.validate_isin("INVALID") is False

    def test_none_isin_is_valid(self):
        assert IdentityValidator.validate_isin(None) is True

    def test_valid_lei(self):
        assert IdentityValidator.validate_lei("549300TRUWOONSUZZA49") is True

    def test_invalid_lei(self):
        assert IdentityValidator.validate_lei("SHORT") is False

    def test_valid_cusip(self):
        assert IdentityValidator.validate_cusip("037833100") is True

    def test_valid_ticker(self):
        assert IdentityValidator.validate_ticker("RELIANCE") is True
        assert IdentityValidator.validate_ticker("BRK.B") is True

    def test_identity_with_bad_isin(self):
        ident  = CompanyIdentity(ticker="X", name="X", exchange="NSE",
                                  country="IN", currency="INR", isin="BAD")
        errors = IdentityValidator().validate(ident)
        assert any("ISIN" in e for e in errors)


class TestIdentityNormaliser:
    def test_normalises_ticker_lowercase(self):
        ident = CompanyIdentity(ticker="reliance", name="RIL",
                                exchange="nse", country="in", currency="inr")
        norm  = IdentityNormaliser.normalise(ident)
        assert norm.ticker   == "RELIANCE"
        assert norm.exchange == "NSE"
        assert norm.country  == "IN"
        assert norm.currency == "INR"

    def test_strips_whitespace(self):
        ident = CompanyIdentity(ticker=" TCS ", name=" TCS Ltd ",
                                exchange="NSE", country="IN", currency="INR")
        norm  = IdentityNormaliser.normalise(ident)
        assert norm.ticker == "TCS"
        assert norm.name   == "TCS Ltd"

    def test_normalises_isin(self):
        ident = CompanyIdentity(ticker="X", name="X", exchange="NSE",
                                country="IN", currency="INR",
                                isin="ine002a01018")
        norm  = IdentityNormaliser.normalise(ident)
        assert norm.isin == "INE002A01018"


class TestIdentityDiffer:
    def test_no_diff_identical(self, identity):
        changes = IdentityDiffer.diff(identity, identity)
        assert changes == {}

    def test_detects_ticker_change(self, identity):
        new_ident = CompanyIdentity(
            ticker="RELI", name=identity.name, exchange=identity.exchange,
            country=identity.country, currency=identity.currency,
        )
        changes = IdentityDiffer.diff(identity, new_ident)
        assert "ticker" in changes
        assert changes["ticker"]["from"] == "RELIANCE"
        assert changes["ticker"]["to"]   == "RELI"

    def test_detects_sector_change(self, identity):
        import copy
        new_ident = copy.copy(identity)
        new_ident.sector = "Technology"
        changes   = IdentityDiffer.diff(identity, new_ident)
        assert "sector" in changes


class TestAliasStore:
    def test_add_and_retrieve(self):
        store = AliasStore()
        alias = CompanyAlias(AliasType.ABBREVIATION, "RIL")
        store.add(alias)
        assert len(store) == 1
        assert store.find("RIL") is not None

    def test_no_duplicates(self):
        store = AliasStore()
        alias = CompanyAlias(AliasType.ABBREVIATION, "RIL")
        store.add(alias)
        store.add(alias)   # duplicate
        assert len(store) == 1

    def test_remove(self):
        store = AliasStore()
        store.add(CompanyAlias(AliasType.ABBREVIATION, "RIL"))
        removed = store.remove(AliasType.ABBREVIATION, "RIL")
        assert removed is True
        assert len(store) == 0

    def test_by_type(self):
        store = AliasStore()
        store.add(CompanyAlias(AliasType.ABBREVIATION, "RIL"))
        store.add(CompanyAlias(AliasType.TRADE_NAME, "Jio"))
        trade_names = store.by_type(AliasType.TRADE_NAME)
        assert len(trade_names) == 1
        assert trade_names[0].value == "Jio"

    def test_old_tickers(self):
        store = AliasStore()
        store.add(CompanyAlias(AliasType.TICKER_OLD, "RELIANCEP"))
        assert "RELIANCEP" in store.old_tickers()


class TestGlobalAliasIndex:
    def test_register_and_lookup(self):
        idx = GlobalAliasIndex()
        idx.register("pid123", [CompanyAlias(AliasType.ABBREVIATION, "RIL")])
        assert idx.lookup("ril") == "pid123"
        assert idx.lookup("RIL") == "pid123"

    def test_deregister(self):
        idx = GlobalAliasIndex()
        aliases = [CompanyAlias(AliasType.ABBREVIATION, "RIL")]
        idx.register("pid123", aliases)
        idx.deregister("pid123", aliases)
        assert idx.lookup("RIL") is None
