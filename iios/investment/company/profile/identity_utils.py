"""iios/investment/company/profile/identity_utils.py
Validator, normaliser and differ for CompanyIdentity (models.py types).
"""
from __future__ import annotations

import re
from typing import List, Optional

from iios.investment.company.profile.models import CompanyIdentity

_ISIN_RE   = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
_CUSIP_RE  = re.compile(r"^[A-Z0-9]{9}$")
_LEI_RE    = re.compile(r"^[A-Z0-9]{20}$")
_TICKER_RE = re.compile(r"^[A-Z0-9.\-&]{1,20}$")


class IdentityValidator:
    """Validates CompanyIdentity fields."""

    @staticmethod
    def validate_isin(isin: Optional[str]) -> bool:
        if isin is None:
            return True
        return bool(_ISIN_RE.match(isin.upper()))

    @staticmethod
    def validate_cusip(cusip: Optional[str]) -> bool:
        if cusip is None:
            return True
        return bool(_CUSIP_RE.match(cusip.upper()))

    @staticmethod
    def validate_lei(lei: Optional[str]) -> bool:
        if lei is None:
            return True
        return bool(_LEI_RE.match(lei.upper()))

    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        return bool(_TICKER_RE.match(ticker.upper()))

    def validate(self, identity: CompanyIdentity) -> List[str]:
        errors = []
        if not identity.ticker:
            errors.append("ticker is required")
        elif not self.validate_ticker(identity.ticker):
            errors.append(f"invalid ticker: {identity.ticker}")
        if not identity.name:
            errors.append("name is required")
        if not identity.exchange:
            errors.append("exchange is required")
        if not identity.country:
            errors.append("country is required")
        if not identity.currency:
            errors.append("currency is required")
        if identity.isin and not self.validate_isin(identity.isin):
            errors.append(f"invalid ISIN: {identity.isin}")
        if identity.cusip and not self.validate_cusip(identity.cusip):
            errors.append(f"invalid CUSIP: {identity.cusip}")
        if identity.lei and not self.validate_lei(identity.lei):
            errors.append(f"invalid LEI: {identity.lei}")
        return errors


class IdentityNormaliser:
    """Normalises CompanyIdentity field formats."""

    @staticmethod
    def normalise(identity: CompanyIdentity) -> CompanyIdentity:
        return CompanyIdentity(
            ticker=identity.ticker.upper().strip(),
            name=identity.name.strip(),
            exchange=identity.exchange.upper().strip(),
            country=identity.country.upper().strip(),
            currency=identity.currency.upper().strip(),
            listing_status=identity.listing_status,
            corporate_structure=identity.corporate_structure,
            sector=identity.sector,
            industry=identity.industry,
            sub_industry=identity.sub_industry,
            isin=identity.isin.upper().strip() if identity.isin else None,
            cusip=identity.cusip.upper().strip() if identity.cusip else None,
            lei=identity.lei.upper().strip() if identity.lei else None,
        )


class IdentityDiffer:
    """Detects field-level changes between two CompanyIdentity objects."""

    @staticmethod
    def diff(old: CompanyIdentity, new: CompanyIdentity) -> dict:
        changes = {}
        for field in ("ticker", "name", "exchange", "country", "currency",
                      "listing_status", "corporate_structure",
                      "sector", "industry", "sub_industry", "isin", "cusip", "lei"):
            old_val = getattr(old, field)
            new_val = getattr(new, field)
            if old_val != new_val:
                changes[field] = {
                    "from": str(old_val) if old_val else None,
                    "to":   str(new_val) if new_val else None,
                }
        return changes
