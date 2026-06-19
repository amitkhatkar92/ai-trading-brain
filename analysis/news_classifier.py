"""
analysis/news_classifier.py
==============================
NEWS_AUDIT_001 — Pure classification functions and constants.

No database. No IO. No live-system imports.
All functions are deterministic and unit-testable.

Core question answered by this module:
    "Does this type of news event actually move the market in a
     predictable direction for our strategies?"

News types tracked
------------------
EARNINGS             : company earnings release (quarterly/annual)
RBI_POLICY           : RBI monetary policy decision
FED_MEETING          : US Federal Reserve FOMC decision
ECB_MEETING          : European Central Bank policy decision
BUDGET               : Union Budget / state budget
TAX_POLICY           : tax law changes (LTCG, STT, corporate tax)
SECTOR_NEWS          : sector-wide event (auto, pharma, IT, metals, etc.)
INDEX_REBAL          : NIFTY/SENSEX index rebalancing
FII_FLOW             : large FII buy/sell event (threshold-based)
REGULATORY           : SEBI rule change, new compliance, circuit breakers
CORPORATE_ACTION     : bonus, split, buyback, dividend announcement
UPGRADE_DOWNGRADE    : analyst rating change
ELECTION             : Lok Sabha / state / US presidential election
POLITICAL_EVENT      : coalition collapse, PM/cabinet change, policy reversal
WAR                  : military conflict / escalation (India-Pak, Russia-Ukraine, etc.)
GEOPOLITICAL_TENSION: non-war border friction, diplomatic crisis, Taiwan Strait
SANCTIONS            : trade sanctions, export controls, entity lists
TRADE_WAR            : tariff escalation, WTO dispute, trade deal collapse
NATURAL_DISASTER     : earthquake, flood, cyclone, pandemic outbreak
CRUDE_OIL_SHOCK      : OPEC cut/hike, supply disruption, demand shock
CURRENCY_SHOCK       : INR/USD spike > 1%, DXY rally, EM selloff
BLACK_SWAN           : COVID-type, Lehman-type, flash crash, exchange outage
NONE                 : no relevant news event

Sentiment labels
----------------
POSITIVE : bullish for the stock/market
NEGATIVE : bearish for the stock/market
NEUTRAL  : no clear directional bias
MIXED    : conflicting signals (e.g. good revenue, bad guidance)

Impact horizon
--------------
INTRADAY   : effect expected same-day only
SHORT_TERM : 1–3 days
MEDIUM_TERM: 1–2 weeks
LONG_TERM  : months+
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class NewsType(str, Enum):
    # Company-level
    EARNINGS             = "EARNINGS"
    CORPORATE_ACTION     = "CORPORATE_ACTION"
    UPGRADE_DOWNGRADE    = "UPGRADE_DOWNGRADE"
    # Sector
    SECTOR_NEWS          = "SECTOR_NEWS"
    INDEX_REBAL          = "INDEX_REBAL"
    FII_FLOW             = "FII_FLOW"
    # Central banks / macro policy
    RBI_POLICY           = "RBI_POLICY"
    FED_MEETING          = "FED_MEETING"
    ECB_MEETING          = "ECB_MEETING"
    # Fiscal / tax
    BUDGET               = "BUDGET"
    TAX_POLICY           = "TAX_POLICY"
    # Politics / elections
    ELECTION             = "ELECTION"
    POLITICAL_EVENT      = "POLITICAL_EVENT"
    # Geopolitical spectrum
    WAR                  = "WAR"
    GEOPOLITICAL_TENSION = "GEOPOLITICAL_TENSION"
    SANCTIONS            = "SANCTIONS"
    TRADE_WAR            = "TRADE_WAR"
    # Macro shocks
    NATURAL_DISASTER     = "NATURAL_DISASTER"
    CRUDE_OIL_SHOCK      = "CRUDE_OIL_SHOCK"
    CURRENCY_SHOCK       = "CURRENCY_SHOCK"
    BLACK_SWAN           = "BLACK_SWAN"
    # Legacy / misc
    REGULATORY           = "REGULATORY"
    NONE                 = "NONE"


class NewsSentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL  = "NEUTRAL"
    MIXED    = "MIXED"


class ImpactHorizon(str, Enum):
    INTRADAY    = "INTRADAY"
    SHORT_TERM  = "SHORT_TERM"
    MEDIUM_TERM = "MEDIUM_TERM"
    LONG_TERM   = "LONG_TERM"
    UNKNOWN     = "UNKNOWN"


# ── Prior knowledge: expected impact per news type ───────────────────────────
# Based on NSE empirical patterns (mean absolute move, direction predictability)
# Used for comparison against observed outcomes.

NEWS_TYPE_PRIORS: Dict[str, dict] = {
    NewsType.EARNINGS: {
        "expected_move_pct":     5.5,   # avg absolute move post-earnings
        "direction_predictable": True,  # sentiment → direction is usually reliable
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "Strongest single-stock catalyst. Avoid SHORT strategies pre-earnings.",
    },
    NewsType.RBI_POLICY: {
        "expected_move_pct":     1.8,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "MEDIUM",
        "note": "Rate cuts → BULL on banks. Rate hikes → BEAR on rate-sensitives.",
    },
    NewsType.FED_MEETING: {
        "expected_move_pct":     1.2,
        "direction_predictable": False,  # reaction often counter-intuitive
        "typical_horizon":       ImpactHorizon.INTRADAY.value,
        "strategy_impact":       "MEDIUM",
        "note": "Initial move often reversed within 24h. Prefer to wait it out.",
    },
    NewsType.BUDGET: {
        "expected_move_pct":     3.2,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.MEDIUM_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "Sector-specific impact. Capex-heavy budget → Infra/Metals bid.",
    },
    NewsType.SECTOR_NEWS: {
        "expected_move_pct":     2.8,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "MEDIUM",
        "note": "Sector ETF + top-3 stocks move together.",
    },
    NewsType.INDEX_REBAL: {
        "expected_move_pct":     2.1,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "MEDIUM",
        "note": "Inclusions bid, exclusions sold. Predictable but short-lived.",
    },
    NewsType.FII_FLOW: {
        "expected_move_pct":     1.5,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "LOW",
        "note": "Sustained buying > 3 days signals regime shift.",
    },
    # GEOPOLITICAL merged → GEOPOLITICAL_TENSION (added in NEWS_AUDIT_002)
    NewsType.REGULATORY: {
        "expected_move_pct":     2.4,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.MEDIUM_TERM.value,
        "strategy_impact":       "MEDIUM",
        "note": "SEBI bans → sector-specific bear. Compliance relief → relief rally.",
    },
    NewsType.CORPORATE_ACTION: {
        "expected_move_pct":     3.5,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "MEDIUM",
        "note": "Buybacks are reliably bullish. Bonus/split → sentiment bid.",
    },
    NewsType.UPGRADE_DOWNGRADE: {
        "expected_move_pct":     1.8,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "LOW",
        "note": "Sell-side upgrades from neutral → buy show strongest move.",
    },
    # ── New in NEWS_AUDIT_002 ────────────────────────────────────────────────
    NewsType.ECB_MEETING: {
        "expected_move_pct":     0.9,
        "direction_predictable": False,
        "typical_horizon":       ImpactHorizon.INTRADAY.value,
        "strategy_impact":       "LOW",
        "note": "Limited direct NSE impact; relevant for IT/pharma export sectors.",
    },
    NewsType.TAX_POLICY: {
        "expected_move_pct":     2.8,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.MEDIUM_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "LTCG hike → market selloff. STT removal → broad rally. Highly directional.",
    },
    NewsType.ELECTION: {
        "expected_move_pct":     4.5,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.MEDIUM_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "Pre-election: low vol. Result day: large gap. Continuity → BULL. Surprise → HIGH_VOL.",
    },
    NewsType.POLITICAL_EVENT: {
        "expected_move_pct":     2.2,
        "direction_predictable": False,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "MEDIUM",
        "note": "Coalition instability, PM change → uncertainty spike. Direction unclear.",
    },
    NewsType.WAR: {
        "expected_move_pct":     6.5,
        "direction_predictable": True,   # always bearish initially
        "typical_horizon":       ImpactHorizon.LONG_TERM.value,
        "strategy_impact":       "CRITICAL",
        "note": "Regime-transition event. Initial gap-down. Defence/Oil rally. Avoid all new positions."
                " Monitor for regime shift to HIGH_VOL.",
    },
    NewsType.GEOPOLITICAL_TENSION: {
        "expected_move_pct":     3.8,
        "direction_predictable": False,
        "typical_horizon":       ImpactHorizon.MEDIUM_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "Non-war friction: Taiwan Strait, border skirmish, diplomatic expulsion."
                " Raises VIX, direction uncertain.",
    },
    NewsType.SANCTIONS: {
        "expected_move_pct":     3.2,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.LONG_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "Target-country assets fall sharply. Counter-party sectors (energy, metals) bid.",
    },
    NewsType.TRADE_WAR: {
        "expected_move_pct":     2.8,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.LONG_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "IT/pharma export sectors most affected on NSE. Tariff escalation → BEAR.",
    },
    NewsType.NATURAL_DISASTER: {
        "expected_move_pct":     2.0,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "MEDIUM",
        "note": "Infra/insurance impact. Cyclone/flood → cement, building materials bid post-event.",
    },
    NewsType.CRUDE_OIL_SHOCK: {
        "expected_move_pct":     3.5,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.MEDIUM_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "India is net oil importer. Crude spike → INR weak, oil PSUs fall, OMCs under pressure."
                " OPEC cut → immediate bearish for NIFTY.",
    },
    NewsType.CURRENCY_SHOCK: {
        "expected_move_pct":     2.5,
        "direction_predictable": True,
        "typical_horizon":       ImpactHorizon.SHORT_TERM.value,
        "strategy_impact":       "HIGH",
        "note": "INR > 85 → FII outflows, broad selloff. DXY rally → EM pressure."
                " IT exports benefit from weak INR.",
    },
    NewsType.BLACK_SWAN: {
        "expected_move_pct":     12.0,
        "direction_predictable": True,   # always bearish initially
        "typical_horizon":       ImpactHorizon.LONG_TERM.value,
        "strategy_impact":       "CRITICAL",
        "note": "COVID, Lehman, flash crash, exchange outage, major fraud."
                " Immediate circuit breaker risk. All positions review required.",
    },
    NewsType.NONE: {
        "expected_move_pct":     0.8,
        "direction_predictable": False,
        "typical_horizon":       ImpactHorizon.INTRADAY.value,
        "strategy_impact":       "NONE",
        "note": "Baseline noise.",
    },
}


# ── Core classification ───────────────────────────────────────────────────────

@dataclass
class NewsImpactResult:
    """Output of classify_news_impact()."""
    alignment:      str    # ALIGNED / OPPOSED / NEUTRAL
    expected_move:  float  # from priors
    observed_move:  float  # actual 5d move (provided externally)
    beat_expected:  bool   # |observed| >= |expected| * 0.8
    direction_match: bool  # sentiment direction matched observed direction


def classify_news_impact(
    news_type:    str,
    sentiment:    str,
    direction:    str,         # "LONG" or "SHORT" (trade direction)
    observed_move_pct: float,  # % move in trade direction over 5 days
) -> NewsImpactResult:
    """
    Determine whether the news event was aligned with the trade or not.

    ALIGNED : news moved price in the trade's favour
    OPPOSED : news moved price against the trade
    NEUTRAL : insufficient move (<= 1%)

    Args:
        news_type:          NewsType string value.
        sentiment:          NewsSentiment string value.
        direction:          "LONG" or "SHORT".
        observed_move_pct:  signed % move in trade direction (positive = good).

    Returns:
        NewsImpactResult.
    """
    prior = NEWS_TYPE_PRIORS.get(news_type, NEWS_TYPE_PRIORS[NewsType.NONE.value])
    exp   = prior["expected_move_pct"]

    if abs(observed_move_pct) <= 1.0:
        alignment = "NEUTRAL"
    elif observed_move_pct > 0:
        alignment = "ALIGNED"
    else:
        alignment = "OPPOSED"

    # Sentiment → expected direction
    sent_bull = sentiment in (NewsSentiment.POSITIVE.value, "POSITIVE")
    sent_bear = sentiment in (NewsSentiment.NEGATIVE.value, "NEGATIVE")
    long_trade = direction.upper() == "LONG"

    direction_match = (
        (sent_bull and long_trade  and observed_move_pct > 0) or
        (sent_bear and not long_trade and observed_move_pct > 0)
    )

    return NewsImpactResult(
        alignment       = alignment,
        expected_move   = exp,
        observed_move   = observed_move_pct,
        beat_expected   = abs(observed_move_pct) >= exp * 0.8,
        direction_match = direction_match,
    )


# ── Batch analysis ────────────────────────────────────────────────────────────

def compute_news_win_rates(records: List[dict]) -> Dict[str, dict]:
    """
    Win rate and avg move breakdown by news_type × sentiment.

    Args:
        records: list of dicts with keys:
            news_type, sentiment, trade_taken, outcome (WIN/LOSS/None),
            move_5d_pct (optional)

    Returns:
        Dict keyed by "NEWS_TYPE__SENTIMENT" with per-combination stats.
    """
    buckets: Dict[str, list] = defaultdict(list)
    for r in records:
        key = f"{r.get('news_type','NONE')}__{r.get('sentiment','NEUTRAL')}"
        buckets[key].append(r)

    result = {}
    for key, recs in buckets.items():
        closed = [r for r in recs if r.get("outcome") in ("WIN", "LOSS", "BREAKEVEN")]
        wins   = [r for r in closed if r.get("outcome") == "WIN"]
        moves  = [r["move_5d_pct"] for r in recs if r.get("move_5d_pct") is not None]

        result[key] = {
            "total":         len(recs),
            "trades_taken":  sum(1 for r in recs if r.get("trade_taken")),
            "closed":        len(closed),
            "wins":          len(wins),
            "win_rate":      round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
            "avg_move_pct":  round(statistics.mean(moves), 2)        if moves  else 0.0,
            "max_move_pct":  round(max(moves), 2)                    if moves  else 0.0,
        }
    return result


def impact_by_news_type(records: List[dict]) -> Dict[str, dict]:
    """
    Per news_type: win rate, avg move, direction predictability score.

    Direction predictability = % of cases where sentiment matched outcome direction.
    """
    buckets: Dict[str, list] = defaultdict(list)
    for r in records:
        buckets[r.get("news_type", "NONE")].append(r)

    result = {}
    for ntype, recs in buckets.items():
        closed     = [r for r in recs if r.get("outcome") in ("WIN", "LOSS", "BREAKEVEN")]
        wins       = [r for r in closed if r.get("outcome") == "WIN"]
        moves      = [r["move_5d_pct"] for r in recs if r.get("move_5d_pct") is not None]
        dir_match  = [r for r in recs if r.get("sentiment_direction_matched") is True]
        prior      = NEWS_TYPE_PRIORS.get(ntype, {})

        predictability = (
            round(len(dir_match) / len(recs) * 100, 1)
            if recs else 0.0
        )
        win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0.0

        result[ntype] = {
            "total":              len(recs),
            "closed":             len(closed),
            "wins":               len(wins),
            "win_rate":           win_rate,
            "avg_move_pct":       round(statistics.mean(moves), 2) if moves else 0.0,
            "direction_accuracy": predictability,
            "expected_move":      prior.get("expected_move_pct", 0.0),
            "strategy_impact":    prior.get("strategy_impact", "UNKNOWN"),
            "verdict":            _verdict(win_rate, len(closed), predictability),
        }
    return result


def _verdict(win_rate: float, n: int, direction_accuracy: float) -> str:
    if n < 5:
        return "INSUFFICIENT_DATA"
    if win_rate >= 65 and direction_accuracy >= 65:
        return "STRONG_SIGNAL"
    elif win_rate >= 55 or direction_accuracy >= 60:
        return "MODERATE_SIGNAL"
    elif win_rate >= 45:
        return "WEAK_SIGNAL"
    return "NO_SIGNAL"
