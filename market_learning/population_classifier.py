"""
population_classifier.py — MLS Phase 2: Population Classification Layer.

Responsibilities:
    Read an immutable DailyMarketSnapshot from MarketObserver.
    Classify every stock in the universe along 8 independent dimensions.
    Create comparison populations for subsequent DNA discovery.
    Persist classification results atomically.

Explicitly NOT responsible for:
    Learning.  DNA discovery.  Prediction.
    Writing to ARS knowledge stores.
    Trade execution or signal generation.

Eight classifiers (all mutually exclusive + exhaustive within their type):
    PERFORMANCE      — return percentile groups (7 labels)
    SECTOR           — sector-relative strength (3 labels)
    REGIME           — alignment with current market regime (2 labels)
    LIQUIDITY        — liquidity tier (3 labels)
    VOLATILITY       — historical volatility tier (3 labels)
    MARKET_CAP       — size proxy via liquidity (3 labels)
    VOLUME_EXPANSION — volume ratio relative to history (3 labels)
    RELATIVE_STRENGTH — RSI-based momentum tier (3 labels)

Multi-label is achieved across dimensions: every stock receives exactly 8
labels (one per classifier type), enabling combinations like
"TOP_5PCT + SECTOR_WINNER + HIGH_LIQUIDITY + BULL".
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from market_learning.market_observer_models import (
    DailyMarketSnapshot,
    MarketObservation,
)
from market_learning.mls_config import MLSConfig
from market_learning.population_classifier_models import (
    ClassificationResult,
    ClassificationNotFoundError,
    ClassifierType,
    GroupLabel,
    OrphanStockError,
    Population,
    PopulationClassifierError,
    PopulationMember,
    PopulationStatistics,
)

log = logging.getLogger(__name__)

_DEFAULT_MLS_DIR = Path(__file__).resolve().parent.parent / "data" / "mls"

# Performance group label order (highest return first)
_PERF_LABELS = [
    GroupLabel.TOP_1PCT,
    GroupLabel.TOP_5PCT,
    GroupLabel.TOP_10PCT,
    GroupLabel.NEUTRAL,
    GroupLabel.BOTTOM_10PCT,
    GroupLabel.BOTTOM_5PCT,
    GroupLabel.BOTTOM_1PCT,
]


class PopulationClassifier:
    """
    MLS Phase 2 — population classification layer.

    Converts a DailyMarketSnapshot into labeled comparison populations
    across 8 independent dimensions.  Every stock ends up in exactly one
    group per dimension — no orphan stocks, no missing classifications.
    """

    def __init__(
        self,
        config: Optional[MLSConfig] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        self._config          = config or MLSConfig()
        root                  = Path(data_dir) if data_dir else _DEFAULT_MLS_DIR
        self._cls_dir         = root / "classifications"
        self._lock            = threading.Lock()
        log.info("[PopulationClassifier] Initialised. storage=%s", root)

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════

    def classify(
        self,
        snapshot: DailyMarketSnapshot,
        outcomes: Optional[Dict[str, float]] = None,
    ) -> ClassificationResult:
        """
        Classify every stock in *snapshot* across all 8 dimensions.

        Args:
            snapshot: Immutable DailyMarketSnapshot from MarketObserver.
            outcomes: Optional dict of symbol -> realized_return.
                      If None, falls back to 'mom_1d' feature as proxy.

        Returns:
            ClassificationResult — persisted atomically to disk.

        Raises:
            PopulationClassifierError: universe is empty.
            OrphanStockError: any stock failed to be classified (bug guard).
        """
        obs = snapshot.observations
        if not obs:
            raise PopulationClassifierError("Snapshot has no observations to classify")

        t_start = datetime.now()
        date    = snapshot.trading_date
        now_str = t_start.isoformat()

        # Determine realized returns
        if outcomes is not None:
            outcomes_map: Dict[str, float] = {
                sym: float(v) for sym, v in outcomes.items()
            }
            outcomes_source = "external"
        else:
            outcomes_map = {o.symbol: o.features.get("mom_1d", 0.0) for o in obs}
            outcomes_source = "feature_proxy"

        # Run all 8 classifiers
        populations: List[Population] = []
        populations += self._classify_performance(obs, outcomes_map, date, now_str)
        populations += self._classify_sector(obs, date, now_str)
        populations += self._classify_regime(obs, snapshot.regime, date, now_str)
        populations += self._classify_liquidity(obs, date, now_str)
        populations += self._classify_volatility(obs, date, now_str)
        populations += self._classify_market_cap(obs, date, now_str)
        populations += self._classify_volume_expansion(obs, date, now_str)
        populations += self._classify_relative_strength(obs, date, now_str)

        # Build per-symbol member records
        members = self._build_members(obs, populations, outcomes_map, date)

        # Validate — no orphan stocks
        classified = {sym for p in populations for sym in p.members}
        orphans    = {o.symbol for o in obs} - classified
        if orphans:
            raise OrphanStockError(f"Stocks not classified: {orphans}")

        result = ClassificationResult(
            result_id=f"MLS-CLS-{date.replace('-', '')}",
            trading_date=date,
            snapshot_id=snapshot.snapshot_id,
            universe_size=snapshot.universe_size,
            populations=populations,
            members=members,
            outcomes_source=outcomes_source,
            created_at=now_str,
        )
        self._persist(result)
        log.info(
            "[PopulationClassifier] %s: %d populations, %d members",
            result.result_id, len(populations), len(members),
        )
        return result

    def load_result(self, trading_date: str) -> Optional[ClassificationResult]:
        """Load a persisted classification result.  Returns None if absent."""
        path = self._path_for(trading_date)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return ClassificationResult.from_dict(json.load(fh))

    def list_results(self) -> List[str]:
        """Return all available classification dates as sorted ISO strings."""
        self._ensure_dirs()
        dates = [
            p.stem.removeprefix("classification_")
            for p in self._cls_dir.glob("classification_*.json")
        ]
        return sorted(dates)

    def statistics(self, trading_date: str) -> Optional[PopulationStatistics]:
        """Return aggregate statistics for one classification date."""
        result = self.load_result(trading_date)
        if result is None:
            return None
        label_counts = [len(m.labels) for m in result.members]
        perf_labels  = {l for l in GroupLabel if l.value.startswith(("TOP_", "BOTTOM_", "NEUTRAL"))}
        perf_sizes   = {
            p.label.value: p.member_count
            for p in result.populations
            if p.label in perf_labels
        }
        classifier_types = sorted({p.classifier_type.value for p in result.populations})
        return PopulationStatistics(
            trading_date=trading_date,
            universe_size=result.universe_size,
            population_count=len(result.populations),
            classifier_types_used=classifier_types,
            avg_labels_per_symbol=round(sum(label_counts) / len(label_counts), 2),
            max_labels_per_symbol=max(label_counts),
            min_labels_per_symbol=min(label_counts),
            performance_group_sizes=perf_sizes,
            outcomes_source=result.outcomes_source,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE — classifiers
    # ═══════════════════════════════════════════════════════════════════════

    def _classify_performance(
        self,
        obs: List[MarketObservation],
        outcomes: Dict[str, float],
        date: str,
        now: str,
    ) -> List[Population]:
        """Exclusive percentile groups: TOP_1PCT … BOTTOM_1PCT."""
        sorted_obs = sorted(obs, key=lambda o: outcomes.get(o.symbol, 0.0), reverse=True)
        n   = len(sorted_obs)
        cfg = self._config

        # Exclusive boundaries from each end (using floor)
        n1   = int(cfg.perf_top1_frac  * n)
        n5   = int(cfg.perf_top5_frac  * n)
        n10  = int(cfg.perf_top10_frac * n)
        bn1  = int(cfg.perf_bot1_frac  * n)
        bn5  = int(cfg.perf_bot5_frac  * n)
        bn10 = int(cfg.perf_bot10_frac * n)

        # Exclusive slices (top to bottom)
        slices = [
            (GroupLabel.TOP_1PCT,     sorted_obs[0:n1]),
            (GroupLabel.TOP_5PCT,     sorted_obs[n1:n5]),
            (GroupLabel.TOP_10PCT,    sorted_obs[n5:n10]),
            (GroupLabel.NEUTRAL,      sorted_obs[n10: max(n10, n - bn10)]),
            (GroupLabel.BOTTOM_10PCT, sorted_obs[max(n10, n - bn10): max(n10, n - bn5)]),
            (GroupLabel.BOTTOM_5PCT,  sorted_obs[max(n10, n - bn5): max(n10, n - bn1)]),
            (GroupLabel.BOTTOM_1PCT,  sorted_obs[max(n10, n - bn1):]),
        ]

        populations = []
        for label, members_obs in slices:
            syms = [o.symbol for o in members_obs]
            pop  = Population(
                population_id=f"POP-{date.replace('-','')}-PERFORMANCE-{label.value}",
                trading_date=date,
                classifier_type=ClassifierType.PERFORMANCE,
                label=label,
                member_count=len(syms),
                members=syms,
                threshold_value=(
                    outcomes.get(members_obs[-1].symbol) if members_obs else None
                ),
                created_at=now,
            )
            populations.append(pop)
        return populations

    def _classify_sector(
        self,
        obs: List[MarketObservation],
        date: str,
        now: str,
    ) -> List[Population]:
        """Classify by sector_strength: WINNER / LOSER / NEUTRAL."""
        hi = self._config.sector_winner_threshold
        lo = self._config.sector_loser_threshold

        winners, losers, neutrals = [], [], []
        for o in obs:
            ss = o.features.get("sector_strength", 0.5)
            if ss >= hi:
                winners.append(o.symbol)
            elif ss <= lo:
                losers.append(o.symbol)
            else:
                neutrals.append(o.symbol)

        return [
            self._make_pop(date, ClassifierType.SECTOR, GroupLabel.SECTOR_WINNER,  winners,  hi, now),
            self._make_pop(date, ClassifierType.SECTOR, GroupLabel.SECTOR_LOSER,   losers,   lo, now),
            self._make_pop(date, ClassifierType.SECTOR, GroupLabel.SECTOR_NEUTRAL, neutrals, None, now),
        ]

    def _classify_regime(
        self,
        obs: List[MarketObservation],
        regime: str,
        date: str,
        now: str,
    ) -> List[Population]:
        """Classify as REGIME_ALIGNED or REGIME_DIVERGENT based on current regime."""
        threshold = self._config.regime_mom_threshold
        aligned, divergent = [], []

        for o in obs:
            mom5  = o.features.get("mom_5d", 0.0)
            iv    = o.features.get("iv_rank", 0.5)
            bb    = o.features.get("bb_position", 0.0)

            is_aligned = False
            if regime == "bull_trend":
                is_aligned = mom5 > threshold
            elif regime == "bear_market":
                is_aligned = mom5 < threshold
            elif regime == "volatile":
                is_aligned = iv > 0.5
            else:
                # range_market: near band midpoint
                is_aligned = abs(bb) < 0.5

            (aligned if is_aligned else divergent).append(o.symbol)

        return [
            self._make_pop(date, ClassifierType.REGIME, GroupLabel.REGIME_ALIGNED,   aligned,   None, now),
            self._make_pop(date, ClassifierType.REGIME, GroupLabel.REGIME_DIVERGENT, divergent, None, now),
        ]

    def _classify_liquidity(
        self,
        obs: List[MarketObservation],
        date: str,
        now: str,
    ) -> List[Population]:
        """Classify by liquidity_score: HIGH / MID / LOW."""
        hi = self._config.liquidity_high_threshold
        lo = self._config.liquidity_low_threshold
        high, mid, low = [], [], []
        for o in obs:
            v = o.features.get("liquidity_score", 0.5)
            if v >= hi:
                high.append(o.symbol)
            elif v <= lo:
                low.append(o.symbol)
            else:
                mid.append(o.symbol)
        return [
            self._make_pop(date, ClassifierType.LIQUIDITY, GroupLabel.HIGH_LIQUIDITY, high, hi,   now),
            self._make_pop(date, ClassifierType.LIQUIDITY, GroupLabel.MID_LIQUIDITY,  mid,  None, now),
            self._make_pop(date, ClassifierType.LIQUIDITY, GroupLabel.LOW_LIQUIDITY,  low,  lo,   now),
        ]

    def _classify_volatility(
        self,
        obs: List[MarketObservation],
        date: str,
        now: str,
    ) -> List[Population]:
        """Classify by hist_vol_5d: HIGH / MID / LOW."""
        hi = self._config.vol_high_threshold
        lo = self._config.vol_low_threshold
        high, mid, low = [], [], []
        for o in obs:
            v = o.features.get("hist_vol_5d", 0.12)
            if v >= hi:
                high.append(o.symbol)
            elif v <= lo:
                low.append(o.symbol)
            else:
                mid.append(o.symbol)
        return [
            self._make_pop(date, ClassifierType.VOLATILITY, GroupLabel.HIGH_VOLATILITY, high, hi,   now),
            self._make_pop(date, ClassifierType.VOLATILITY, GroupLabel.MID_VOLATILITY,  mid,  None, now),
            self._make_pop(date, ClassifierType.VOLATILITY, GroupLabel.LOW_VOLATILITY,  low,  lo,   now),
        ]

    def _classify_market_cap(
        self,
        obs: List[MarketObservation],
        date: str,
        now: str,
    ) -> List[Population]:
        """Classify by liquidity_score as market cap proxy: LARGE / MID / SMALL."""
        hi = self._config.mktcap_large_threshold
        lo = self._config.mktcap_small_threshold
        large, mid, small = [], [], []
        for o in obs:
            v = o.features.get("liquidity_score", 0.5)
            if v >= hi:
                large.append(o.symbol)
            elif v <= lo:
                small.append(o.symbol)
            else:
                mid.append(o.symbol)
        return [
            self._make_pop(date, ClassifierType.MARKET_CAP, GroupLabel.LARGE_CAP, large, hi,   now),
            self._make_pop(date, ClassifierType.MARKET_CAP, GroupLabel.MID_CAP,   mid,   None, now),
            self._make_pop(date, ClassifierType.MARKET_CAP, GroupLabel.SMALL_CAP, small, lo,   now),
        ]

    def _classify_volume_expansion(
        self,
        obs: List[MarketObservation],
        date: str,
        now: str,
    ) -> List[Population]:
        """Classify by volume_ratio_raw: EXPANDING / NORMAL / CONTRACTING."""
        exp_thr = self._config.vol_expansion_ratio
        con_thr = self._config.vol_contraction_ratio
        expanding, normal, contracting = [], [], []
        for o in obs:
            v = o.features.get("volume_ratio_raw", 1.0)
            if v >= exp_thr:
                expanding.append(o.symbol)
            elif v <= con_thr:
                contracting.append(o.symbol)
            else:
                normal.append(o.symbol)
        return [
            self._make_pop(date, ClassifierType.VOLUME_EXPANSION, GroupLabel.VOLUME_EXPANDING,   expanding,   exp_thr, now),
            self._make_pop(date, ClassifierType.VOLUME_EXPANSION, GroupLabel.VOLUME_NORMAL,       normal,      None,    now),
            self._make_pop(date, ClassifierType.VOLUME_EXPANSION, GroupLabel.VOLUME_CONTRACTING,  contracting, con_thr, now),
        ]

    def _classify_relative_strength(
        self,
        obs: List[MarketObservation],
        date: str,
        now: str,
    ) -> List[Population]:
        """Classify by RSI: RS_STRONG / RS_NEUTRAL / RS_WEAK."""
        strong_thr = self._config.rs_strong_rsi
        weak_thr   = self._config.rs_weak_rsi
        strong, neutral, weak = [], [], []
        for o in obs:
            rsi = o.features.get("rsi", 50.0)
            if rsi >= strong_thr:
                strong.append(o.symbol)
            elif rsi <= weak_thr:
                weak.append(o.symbol)
            else:
                neutral.append(o.symbol)
        return [
            self._make_pop(date, ClassifierType.RELATIVE_STRENGTH, GroupLabel.RS_STRONG,  strong,  strong_thr, now),
            self._make_pop(date, ClassifierType.RELATIVE_STRENGTH, GroupLabel.RS_NEUTRAL, neutral, None,       now),
            self._make_pop(date, ClassifierType.RELATIVE_STRENGTH, GroupLabel.RS_WEAK,    weak,    weak_thr,   now),
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE — helpers
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _make_pop(
        date: str,
        cls_type: ClassifierType,
        label: GroupLabel,
        members: List[str],
        threshold: Optional[float],
        now: str,
    ) -> Population:
        return Population(
            population_id=f"POP-{date.replace('-','')}-{cls_type.value}-{label.value}",
            trading_date=date,
            classifier_type=cls_type,
            label=label,
            member_count=len(members),
            members=members,
            threshold_value=threshold,
            created_at=now,
        )

    @staticmethod
    def _build_members(
        obs: List[MarketObservation],
        populations: List[Population],
        outcomes: Dict[str, float],
        date: str,
    ) -> List[PopulationMember]:
        """Build one PopulationMember per symbol aggregating all population assignments."""
        # Build reverse index: symbol -> list of (population_id, label)
        sym_to_pops: Dict[str, List[tuple[str, str]]] = {}
        for p in populations:
            for sym in p.members:
                sym_to_pops.setdefault(sym, []).append(
                    (p.population_id, p.label.value)
                )

        members = []
        for o in obs:
            assignments = sym_to_pops.get(o.symbol, [])
            f = o.features
            members.append(PopulationMember(
                symbol=o.symbol,
                trading_date=date,
                population_ids=[a[0] for a in assignments],
                labels=[a[1] for a in assignments],
                realized_return=outcomes.get(o.symbol),
                classification_values={
                    "realized_return":  outcomes.get(o.symbol, 0.0),
                    "sector_strength":  f.get("sector_strength", 0.0),
                    "liquidity_score":  f.get("liquidity_score", 0.5),
                    "hist_vol_5d":      f.get("hist_vol_5d", 0.12),
                    "volume_ratio_raw": f.get("volume_ratio_raw", 1.0),
                    "rsi":              f.get("rsi", 50.0),
                    "mom_5d":           f.get("mom_5d", 0.0),
                    "iv_rank":          f.get("iv_rank", 0.5),
                    "bb_position":      f.get("bb_position", 0.0),
                },
            ))
        return members

    def _persist(self, result: ClassificationResult) -> None:
        """Atomic write: .tmp -> os.replace; .bak of previous."""
        self._ensure_dirs()
        path = self._path_for(result.trading_date)
        tmp  = path.with_suffix(".tmp")
        with self._lock:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(result.to_dict(), fh, indent=2)
            if path.exists():
                path.with_suffix(".bak").write_bytes(path.read_bytes())
            os.replace(tmp, path)

    def _path_for(self, trading_date: str) -> Path:
        return self._cls_dir / f"classification_{trading_date}.json"

    def _ensure_dirs(self) -> None:
        self._cls_dir.mkdir(parents=True, exist_ok=True)
