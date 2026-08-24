"""
Options Validator (OOS + Walk-Forward)
=======================================

Validates KnowledgeItems using out-of-sample (OOS) temporal splits and
walk-forward (WFO) analysis.

OOS Split
---------
  - Data is split temporally: first 70% is in-sample, last 30% is OOS.
  - In-sample win_rate is NOT used for validation.
  - OOS win_rate compared to 0.50 using one-tailed binomial test.
  - Minimum 5 OOS outcomes required for statistical relevance.

Walk-Forward (WFO)
------------------
  - Data is split into K=3 folds.
  - For each fold: train on preceding folds, test on current fold.
  - Sharpe-like measure computed: avg_pnl_test / std_pnl_test.
  - Average WFO Sharpe across all folds returned.
  - Minimum MIN_WFO_TEST_N outcomes per fold required.

Note: With current data volumes (initial phase), OOS/WFO will operate on
small N.  The thresholds in options_knowledge_store.py are conservative
(MIN_OUTCOMES_VALIDATED=20) precisely to avoid premature validation.

Persistence: none (pure computation; results are stored in KnowledgeStore)
"""

from __future__ import annotations

import math
import threading
from typing import List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── WFO parameters ────────────────────────────────────────────────────────
OOS_SPLIT_RATIO = 0.70   # fraction used as in-sample
WFO_K_FOLDS     = 3      # number of folds
MIN_WFO_TEST_N  = 5      # minimum outcomes in each test fold


def run_oos_validation(outcomes: List[Tuple[int, float, str]]) -> Tuple[int, int, float]:
    """
    Run OOS temporal split validation.

    Parameters
    ----------
    outcomes : list of (win:int, pnl:float, observed_at:str) sorted by date

    Returns
    -------
    (oos_n, oos_wins, p_value)
    """
    if len(outcomes) < 10:
        return 0, 0, 1.0

    sorted_obs = sorted(outcomes, key=lambda x: x[2])
    split_idx  = int(len(sorted_obs) * OOS_SPLIT_RATIO)
    oos_obs    = sorted_obs[split_idx:]

    if len(oos_obs) < 5:
        return 0, 0, 1.0

    oos_n    = len(oos_obs)
    oos_wins = sum(o[0] for o in oos_obs)
    p_value  = _binomial_p(oos_wins, oos_n, 0.50)

    return oos_n, oos_wins, p_value


def run_walk_forward(outcomes: List[Tuple[int, float, str]]) -> Optional[float]:
    """
    Run walk-forward validation.

    Returns the average Sharpe-like metric across folds, or None if
    insufficient data.
    """
    if len(outcomes) < WFO_K_FOLDS * MIN_WFO_TEST_N:
        return None

    sorted_obs = sorted(outcomes, key=lambda x: x[2])
    n          = len(sorted_obs)
    fold_size  = n // WFO_K_FOLDS

    sharpes: List[float] = []
    for fold_idx in range(1, WFO_K_FOLDS):
        train = sorted_obs[: fold_idx * fold_size]
        test  = sorted_obs[fold_idx * fold_size: (fold_idx + 1) * fold_size]

        if len(test) < MIN_WFO_TEST_N:
            continue

        pnls = [t[1] for t in test]
        avg  = sum(pnls) / len(pnls)
        std  = _std(pnls)
        if std <= 0:
            # All outcomes same sign — Sharpe is either ∞ or −∞
            sharpes.append(1.0 if avg > 0 else -1.0)
        else:
            sharpes.append(avg / std)

    if not sharpes:
        return None
    return sum(sharpes) / len(sharpes)


def validate_knowledge_item(item) -> None:
    """
    Validate a KnowledgeItem and write OOS + WFO results back.

    Parameters
    ----------
    item : KnowledgeItem (from options_knowledge_store)

    The item must have `linked_opportunity_ids` to retrieve outcomes, but
    since we don't pass the full journal here, we reconstruct from the
    item's aggregate statistics only.

    NOTE: This is called from the research pipeline which passes the
    raw outcome list directly via validate_with_raw_outcomes().
    """
    log.debug(
        "[Validator] validate_knowledge_item called without raw outcomes "
        "for %s — skipping (use validate_with_raw_outcomes).",
        item.item_id,
    )


def validate_with_raw_outcomes(
    item,
    outcomes: List[Tuple[int, float, str]],
) -> None:
    """
    Validate a KnowledgeItem with raw outcome tuples and write results back.

    Parameters
    ----------
    item     : KnowledgeItem
    outcomes : list of (win, pnl, observed_at_str)
    """
    from knowledge_system.options_knowledge_store import get_options_knowledge_store

    oos_n, oos_wins, p_value = run_oos_validation(outcomes)
    wfo_sharpe = run_walk_forward(outcomes)

    store = get_options_knowledge_store()
    if oos_n >= 5:
        store.mark_oos_result(item.item_id, oos_n, oos_wins, p_value)
        log.info(
            "[Validator] OOS result for %s: n=%d wins=%d p=%.3f",
            item.item_id, oos_n, oos_wins, p_value,
        )
    if wfo_sharpe is not None:
        store.mark_wfo_result(item.item_id, wfo_sharpe)
        log.info(
            "[Validator] WFO result for %s: sharpe=%.3f",
            item.item_id, wfo_sharpe,
        )


# ── Statistical helpers ────────────────────────────────────────────────────

def _binomial_p(k: int, n: int, p_null: float) -> float:
    """
    One-tailed (right-tail) binomial p-value:
    P(X >= k | n, p_null)

    Uses a normal approximation for n >= 20, exact for n < 20.
    """
    if n <= 0:
        return 1.0
    if n < 20:
        return _binomial_exact_p(k, n, p_null)
    mu  = n * p_null
    sig = math.sqrt(n * p_null * (1 - p_null))
    if sig <= 0:
        return 0.0 if k > mu else 1.0
    z = (k - 0.5 - mu) / sig   # continuity correction
    return 1.0 - _norm_cdf(z)


def _binomial_exact_p(k: int, n: int, p: float) -> float:
    """Exact right-tail binomial probability P(X >= k)."""
    total = 0.0
    binom = _binom_coeff(n, k)
    for i in range(k, n + 1):
        if i > k:
            binom = binom * (n - i + 1) / i
        total += binom * (p ** i) * ((1 - p) ** (n - i))
    return min(total, 1.0)


def _binom_coeff(n: int, k: int) -> float:
    """Binomial coefficient C(n,k)."""
    if k < 0 or k > n:
        return 0.0
    k = min(k, n - k)
    result = 1.0
    for i in range(k):
        result = result * (n - i) / (i + 1)
    return result


def _norm_cdf(x: float) -> float:
    """Standard normal CDF using math.erf."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu  = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)
