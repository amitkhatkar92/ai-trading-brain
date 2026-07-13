"""iios/investment/company/opportunity/ranking_engine.py
Thread-safe ranking engine — maintains global, sector, and industry rankings.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.company.opportunity.opportunity_profile import OpportunityStrength
from iios.investment.company.opportunity.opportunity_statistics import score_to_strength
from iios.investment.company.opportunity.ranking_history import RankingHistory
from iios.investment.company.opportunity.ranking_score import RankingResult, RankingScore
from iios.investment.company.opportunity.ranking_statistics import rank_tickers, top_n_tickers


class RankingEngine:
    """
    Maintains live rankings for all evaluated companies.
    Thread-safe; designed for continuous incremental updates.

    Rankings are recomputed on every update (O(N log N)).
    For millions of companies, use a sorted container; this implementation
    targets hundreds of thousands within a single process.
    """

    def __init__(self, history_capacity: int = 50) -> None:
        self._lock    = threading.RLock()
        self._scores:  Dict[str, float] = {}             # ticker → composite score
        self._sectors: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._industries: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._ticker_sector:   Dict[str, str] = {}
        self._ticker_industry: Dict[str, str] = {}
        self._ranks:    Dict[str, int] = {}
        self._history   = RankingHistory(capacity=history_capacity)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(
        self,
        ticker:   str,
        score:    float,
        sector:   Optional[str] = None,
        industry: Optional[str] = None,
    ) -> RankingResult:
        """
        Record a new score for *ticker* and recompute all rankings.
        Returns the updated RankingResult.
        """
        with self._lock:
            old_rank = self._ranks.get(ticker)
            self._scores[ticker] = score
            if sector:
                self._ticker_sector[ticker] = sector
                self._sectors[sector][ticker] = score
            if industry:
                self._ticker_industry[ticker] = industry
                self._industries[industry][ticker] = score

            self._ranks = rank_tickers(self._scores)
            sec  = sector or self._ticker_sector.get(ticker)
            ind  = industry or self._ticker_industry.get(ticker)
            sec_rank  = self._sector_rank(ticker, sec)
            ind_rank  = self._industry_rank(ticker, ind)

            result = RankingResult(
                ticker=ticker,
                global_rank=self._ranks.get(ticker),
                sector_rank=sec_rank,
                industry_rank=ind_rank,
                score=score,
                population_size=len(self._scores),
            )
            self._history.record(result, previous_rank=old_rank)
            return result

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_ranking(self, ticker: str) -> Optional[RankingResult]:
        with self._lock:
            if ticker not in self._scores:
                return None
            sec = self._ticker_sector.get(ticker)
            ind = self._ticker_industry.get(ticker)
            return RankingResult(
                ticker=ticker,
                global_rank=self._ranks.get(ticker),
                sector_rank=self._sector_rank(ticker, sec),
                industry_rank=self._industry_rank(ticker, ind),
                score=self._scores[ticker],
                population_size=len(self._scores),
            )

    def get_top(
        self,
        n:        int = 20,
        sector:   Optional[str] = None,
        industry: Optional[str] = None,
    ) -> List[str]:
        """Return tickers for the top-*n* ranked companies (globally or by sector/industry)."""
        with self._lock:
            if sector and sector in self._sectors:
                return top_n_tickers(self._sectors[sector], n)
            if industry and industry in self._industries:
                return top_n_tickers(self._industries[industry], n)
            return top_n_tickers(self._scores, n)

    def get_score(self, ticker: str) -> Optional[float]:
        with self._lock:
            return self._scores.get(ticker)

    def get_global_rank(self, ticker: str) -> Optional[int]:
        with self._lock:
            return self._ranks.get(ticker)

    def population_size(self) -> int:
        with self._lock:
            return len(self._scores)

    def score_distribution(self) -> Dict[str, float]:
        """Return basic score statistics across the entire population."""
        with self._lock:
            if not self._scores:
                return {}
            vals = list(self._scores.values())
            n = len(vals)
            mean = sum(vals) / n
            return {
                "count":  n,
                "min":    min(vals),
                "max":    max(vals),
                "mean":   round(mean, 2),
            }

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._scores.keys())

    def get_ranking_history(self, ticker: str, n: int = 10):
        return self._history.get_history(ticker, n)

    # ── Private ───────────────────────────────────────────────────────────────

    def _sector_rank(self, ticker: str, sector: Optional[str]) -> Optional[int]:
        if not sector or sector not in self._sectors:
            return None
        sec_ranks = rank_tickers(self._sectors[sector])
        return sec_ranks.get(ticker)

    def _industry_rank(self, ticker: str, industry: Optional[str]) -> Optional[int]:
        if not industry or industry not in self._industries:
            return None
        ind_ranks = rank_tickers(self._industries[industry])
        return ind_ranks.get(ticker)
