"""iios/investment/portfolio/exposure/exposure_tracker.py
Computes real-time exposures from a Portfolio object.
"""
from __future__ import annotations

from iios.investment.portfolio.core.portfolio import Portfolio
from iios.investment.portfolio.portfolio_constants import PositionType
from iios.investment.portfolio.exposure.exposure_limits import ExposureLimits
from iios.investment.portfolio.exposure.exposure_report import ExposureReport
from iios.investment.portfolio.portfolio_constants import AllocationStatus


class ExposureTracker:
    """
    Derives all exposure breakdowns from a Portfolio instance.

    Does NOT modify the portfolio — purely a read-only computation.
    """

    def compute(
        self,
        portfolio: Portfolio,
        limits:    ExposureLimits | None = None,
    ) -> ExposureReport:
        nav = portfolio.total_nav
        if nav <= 0:
            return ExposureReport(portfolio_id=portfolio.portfolio_id)

        lim = limits or ExposureLimits()

        long_mv  = 0.0
        short_mv = 0.0
        by_sector:      dict[str, float] = {}
        by_country:     dict[str, float] = {}
        by_asset_class: dict[str, float] = {}
        by_currency:    dict[str, float] = {}
        by_strategy:    dict[str, float] = {}

        for pos in portfolio.positions.values():
            mv = pos.market_value
            if pos.position_type == PositionType.SHORT:
                short_mv += mv
            else:
                long_mv += mv

            weight = mv / nav

            sector = pos.sector or "unknown"
            by_sector[sector] = by_sector.get(sector, 0.0) + weight

            country = pos.country or "unknown"
            by_country[country] = by_country.get(country, 0.0) + weight

            ac = pos.asset_class.value
            by_asset_class[ac] = by_asset_class.get(ac, 0.0) + weight

            cur = pos.currency or portfolio.base_currency
            by_currency[cur] = by_currency.get(cur, 0.0) + weight

            strat = pos.strategy_id or "unknown"
            by_strategy[strat] = by_strategy.get(strat, 0.0) + weight

        gross_exp = (long_mv + short_mv) / nav
        net_exp   = (long_mv - short_mv) / nav
        long_exp  = long_mv  / nav
        short_exp = short_mv / nav
        cash_pct  = portfolio.cash / nav

        breaches = self._check_breaches(
            lim, by_sector, by_country, by_asset_class,
            gross_exp, cash_pct,
            max(p.weight for p in portfolio.positions.values()) if portfolio.positions else 0.0,
        )

        status = AllocationStatus.WITHIN_LIMITS if not breaches else AllocationStatus.OVERALLOCATED

        return ExposureReport(
            portfolio_id   = portfolio.portfolio_id,
            gross_exposure = round(gross_exp, 6),
            net_exposure   = round(net_exp,   6),
            long_exposure  = round(long_exp,  6),
            short_exposure = round(short_exp, 6),
            cash_pct       = round(cash_pct,  6),
            by_sector      = {k: round(v, 6) for k, v in by_sector.items()},
            by_country     = {k: round(v, 6) for k, v in by_country.items()},
            by_asset_class = {k: round(v, 6) for k, v in by_asset_class.items()},
            by_currency    = {k: round(v, 6) for k, v in by_currency.items()},
            by_strategy    = {k: round(v, 6) for k, v in by_strategy.items()},
            limit_breaches = breaches,
            status         = status,
            metadata       = {"nav": nav},
        )

    @staticmethod
    def _check_breaches(
        lim:        ExposureLimits,
        by_sector:  dict[str, float],
        by_country: dict[str, float],
        by_ac:      dict[str, float],
        gross:      float,
        cash_pct:   float,
        top_w:      float,
    ) -> list[str]:
        breaches: list[str] = []
        for sec, w in by_sector.items():
            if w > lim.max_sector_exposure:
                breaches.append(f"Sector {sec!r} exposure {w:.1%} > limit {lim.max_sector_exposure:.1%}")
        for cty, w in by_country.items():
            if w > lim.max_country_exposure:
                breaches.append(f"Country {cty!r} exposure {w:.1%} > limit {lim.max_country_exposure:.1%}")
        for ac, w in by_ac.items():
            if w > lim.max_asset_class:
                breaches.append(f"Asset class {ac!r} exposure {w:.1%} > limit {lim.max_asset_class:.1%}")
        if gross > lim.max_gross_exposure:
            breaches.append(f"Gross exposure {gross:.1%} > limit {lim.max_gross_exposure:.1%}")
        if cash_pct < lim.min_cash_pct:
            breaches.append(f"Cash {cash_pct:.1%} < minimum {lim.min_cash_pct:.1%}")
        if top_w > lim.max_single_position:
            breaches.append(f"Top position {top_w:.1%} > limit {lim.max_single_position:.1%}")
        return breaches
