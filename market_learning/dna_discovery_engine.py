"""
dna_discovery_engine.py — MLS Phase 3: DNA Discovery Layer.

Responsibilities:
    Compare winner vs loser populations across all features.
    Measure feature separation via Cohen's d (pure Python, no scipy).
    Bootstrap 95% CI for every effect size.
    Compute Spearman rank correlation as monotonic evidence.
    Detect feature pairs with super-additive joint explanatory power.
    Assign lifecycle state using historical discovery reports.
    Emit DNACharacteristic, WinnerDNA, LoserDNA, NeutralDNA, DiscoveryReport.
    Persist results atomically to data/mls/dna/.

Explicitly NOT responsible for:
    Modifying ARS knowledge stores.
    Changing thresholds or config.
    Executing research or trades.
    Any write that is not a DiscoveryReport.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from market_learning.market_observer_models import (
    DailyMarketSnapshot,
    MarketObservation,
)
from market_learning.mls_config import MLSConfig
from market_learning.population_classifier_models import (
    ClassificationResult,
    ClassifierType,
    GroupLabel,
)
from market_learning.dna_discovery_models import (
    DNACharacteristic,
    DNADiscoveryError,
    DNAInteraction,
    DNALifecycle,
    DNAStatistics,
    DiscoveryReport,
    FeatureEvidence,
    FeatureType,
    InsufficientDataError,
    LoserDNA,
    NeutralDNA,
    SeparationDirection,
    WinnerDNA,
)

log = logging.getLogger(__name__)

_DEFAULT_MLS_DIR = Path(__file__).resolve().parent.parent / "data" / "mls"

# Features that are identical across all symbols in one snapshot — skip for
# inter-symbol comparison because their Cohen's d is trivially zero.
_MARKET_WIDE_FEATURES = frozenset({
    "regime_score", "regime_bull", "regime_bear", "regime_range", "regime_volatile",
    "vol_score", "vix", "vix_low", "vix_high",
    "breadth", "breadth_strong", "breadth_weak",
    "pcr", "pcr_bullish", "pcr_bearish", "pcr_neutral",
    "global_bias", "sector_flow_count", "event_count",
})

# Known binary (0/1) features — kept out of the within-group offset during testing
_BINARY_FEATURE_NAMES = frozenset({
    "volume_spike", "rsi_oversold", "rsi_overbought", "rsi_neutral",
    "macd_bull", "macd_bear", "bb_upper", "bb_lower",
    "gap_up", "gap_down", "strong_trend", "vol_compression",
    "iv_spike", "iv_low", "mom_positive",
})


# ═══════════════════════════════════════════════════════════════════════════════
# Pure statistical helpers — no class state, fully testable in isolation
# ═══════════════════════════════════════════════════════════════════════════════

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sample_var(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _cohen_d(a: List[float], b: List[float]) -> float:
    """
    Pooled Cohen's d: (mean_a - mean_b) / sqrt((var_a + var_b) / 2).

    Returns 0.0 if data is insufficient.
    Returns +/-1e6 sentinel if within-group variance is zero but means differ.
    """
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ma, mb   = _mean(a), _mean(b)
    va, vb   = _sample_var(a), _sample_var(b)
    pooled   = math.sqrt((va + vb) / 2.0)
    diff     = ma - mb
    if pooled < 1e-12:
        if abs(diff) < 1e-12:
            return 0.0
        return math.copysign(1_000.0, diff)  # near-infinite effect
    return diff / pooled


def _spearman(a: List[float], b: List[float]) -> float:
    """Spearman rank correlation between a and b (same length)."""
    n = len(a)
    if n < 3 or len(b) != n:
        return 0.0

    def _ranks(vals: List[float]) -> List[float]:
        idx = sorted(range(n), key=lambda i: vals[i])
        r   = [0.0] * n
        i   = 0
        while i < n:
            j = i
            while j < n - 1 and vals[idx[j + 1]] == vals[idx[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[idx[k]] = avg
            i = j + 1
        return r

    ra, rb = _ranks(a), _ranks(b)
    ma, mb = _mean(ra), _mean(rb)
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da  = math.sqrt(sum((ra[i] - ma) ** 2 for i in range(n)))
    db  = math.sqrt(sum((rb[i] - mb) ** 2 for i in range(n)))
    if da < 1e-12 or db < 1e-12:
        return 0.0
    return num / (da * db)


def _bootstrap_ci(
    a: List[float], b: List[float], n_boot: int, seed: int = 42
) -> Tuple[float, float]:
    """Bootstrap 95% CI for Cohen's d via percentile method."""
    if len(a) < 2 or len(b) < 2:
        return 0.0, 0.0
    rng     = random.Random(seed)
    effects = []
    for _ in range(n_boot):
        sa = [rng.choice(a) for _ in range(len(a))]
        sb = [rng.choice(b) for _ in range(len(b))]
        effects.append(_cohen_d(sa, sb))
    effects.sort()
    lo = effects[max(0, int(0.025 * n_boot))]
    hi = effects[min(len(effects) - 1, int(0.975 * n_boot))]
    return lo, hi


def _detect_feature_type(values: List[float]) -> FeatureType:
    """Infer feature type from observed values."""
    unique = set(round(v, 8) for v in values)
    if unique <= {0.0, 1.0}:
        return FeatureType.BINARY
    if len(unique) <= 5 and all(v == int(v) for v in values if not math.isnan(v)):
        return FeatureType.ORDINAL
    return FeatureType.CONTINUOUS


def _zscore_pooled(
    vals_a: List[float], vals_b: List[float]
) -> Tuple[List[float], List[float]]:
    """Normalize both lists using their combined mean and std."""
    combined = vals_a + vals_b
    m = _mean(combined)
    n = len(combined)
    v = sum((x - m) ** 2 for x in combined) / n if n > 1 else 0.0
    s = max(math.sqrt(v), 1e-9)
    return [(x - m) / s for x in vals_a], [(x - m) / s for x in vals_b]


def _make_id(prefix: str, *parts: str) -> str:
    """Short deterministic ID from hash of concatenated parts."""
    raw = f"{prefix}:" + ":".join(parts)
    return f"{prefix}-{hashlib.sha256(raw.encode()).hexdigest()[:8]}"


# ═══════════════════════════════════════════════════════════════════════════════
# DNADiscoveryEngine
# ═══════════════════════════════════════════════════════════════════════════════

class DNADiscoveryEngine:
    """
    MLS Phase 3 — DNA discovery layer.

    Reads DailyMarketSnapshot (Phase 1) and ClassificationResult (Phase 2)
    and discovers statistically verified feature characteristics that separate
    winners from losers BEFORE price movement.

    Read-only with respect to all other MLS layers.
    Writes only to data/mls/dna/.
    """

    def __init__(
        self,
        config:   Optional[MLSConfig] = None,
        data_dir: Optional[Path]      = None,
    ) -> None:
        self._config  = config or MLSConfig()
        root          = Path(data_dir) if data_dir else _DEFAULT_MLS_DIR
        self._dna_dir = root / "dna"
        self._lock    = threading.Lock()
        log.info("[DNADiscoveryEngine] Initialised. storage=%s", root)

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════

    def discover(
        self,
        snapshot:       DailyMarketSnapshot,
        classification: ClassificationResult,
        history:        Optional[List[DiscoveryReport]] = None,
    ) -> DiscoveryReport:
        """
        Full DNA discovery for one trading day.

        Args:
            snapshot:       DailyMarketSnapshot from MarketObserver.
            classification: ClassificationResult from PopulationClassifier.
            history:        Optional list of previous DiscoveryReports (used for
                            lifecycle advancement).

        Returns:
            DiscoveryReport — persisted atomically to disk.

        Raises:
            InsufficientDataError: winner or loser group smaller than dna_min_group_size.
        """
        obs_map   = {o.symbol: o for o in snapshot.observations}
        date      = snapshot.trading_date
        regime    = snapshot.regime
        now_str   = datetime.now().isoformat()
        hist      = history or []

        # 1. Extract population groups
        winner_obs, loser_obs, neutral_obs = self._extract_groups(classification, obs_map)

        n_min = self._config.dna_min_group_size
        if len(winner_obs) < n_min or len(loser_obs) < n_min:
            raise InsufficientDataError(
                f"winners={len(winner_obs)}, losers={len(loser_obs)}, "
                f"min_group_size={n_min}"
            )

        # 2. Winner-vs-loser feature analysis
        all_chars = self._analyse_features(
            winner_obs, loser_obs, date, regime, hist,
            dir_high=SeparationDirection.WINNERS_HIGHER,
            dir_low=SeparationDirection.WINNERS_LOWER,
        )
        winner_chars = [c for c in all_chars if c.direction == SeparationDirection.WINNERS_HIGHER]
        loser_chars  = [c for c in all_chars if c.direction == SeparationDirection.WINNERS_LOWER]

        # 3. Neutral analysis: neutral vs (winner + loser) extremes
        neutral_chars: List[DNACharacteristic] = []
        extremes = winner_obs + loser_obs
        if len(neutral_obs) >= n_min and len(extremes) >= n_min:
            neutral_chars = self._analyse_features(
                neutral_obs, extremes, date, regime, hist,
                dir_high=SeparationDirection.NEUTRALS_HIGHER,
                dir_low=SeparationDirection.NEUTRALS_LOWER,
            )

        # 4. Feature interaction discovery
        all_interactions       = self._discover_interactions(winner_obs, loser_obs, all_chars, date, regime)
        neutral_interactions   = self._discover_interactions(neutral_obs, extremes, neutral_chars, date, regime)

        # 5. Collect population IDs
        win_labels = {GroupLabel(l) for l in self._config.dna_winner_labels}
        los_labels = {GroupLabel(l) for l in self._config.dna_loser_labels}
        win_pop_ids = [
            p.population_id for p in classification.populations
            if p.classifier_type == ClassifierType.PERFORMANCE and p.label in win_labels
        ]
        los_pop_ids = [
            p.population_id for p in classification.populations
            if p.classifier_type == ClassifierType.PERFORMANCE and p.label in los_labels
        ]
        neu_pop = classification.get_population_by_type(
            ClassifierType.PERFORMANCE, GroupLabel.NEUTRAL
        )

        # 6. Build DNA profiles
        winner_dna = WinnerDNA(
            date=date,
            characteristics=winner_chars,
            interactions=all_interactions,
            population_ids=win_pop_ids,
            n_members=len(winner_obs),
            regime=regime,
        )
        loser_dna = LoserDNA(
            date=date,
            characteristics=loser_chars,
            interactions=all_interactions,
            population_ids=los_pop_ids,
            n_members=len(loser_obs),
            regime=regime,
        )
        neutral_dna = NeutralDNA(
            date=date,
            characteristics=neutral_chars,
            interactions=neutral_interactions,
            population_ids=[neu_pop.population_id] if neu_pop else [],
            n_members=len(neutral_obs),
            regime=regime,
        )

        report = DiscoveryReport(
            report_id=f"MLS-DNA-{date.replace('-', '')}",
            trading_date=date,
            snapshot_id=snapshot.snapshot_id,
            classification_id=classification.result_id,
            winner_dna=winner_dna,
            loser_dna=loser_dna,
            neutral_dna=neutral_dna,
            all_characteristics=all_chars + neutral_chars,
            all_interactions=all_interactions + neutral_interactions,
            regime=regime,
            universe_size=snapshot.universe_size,
            created_at=now_str,
        )

        self._persist(report)
        log.info(
            "[DNADiscoveryEngine] %s: %d chars (%d winner, %d loser, %d neutral), "
            "%d interactions",
            report.report_id,
            len(report.all_characteristics),
            len(winner_chars), len(loser_chars), len(neutral_chars),
            len(report.all_interactions),
        )
        return report

    def winner_dna(self, trading_date: str) -> Optional[WinnerDNA]:
        """Return the WinnerDNA for *trading_date*, or None."""
        r = self.load_report(trading_date)
        return r.winner_dna if r else None

    def loser_dna(self, trading_date: str) -> Optional[LoserDNA]:
        """Return the LoserDNA for *trading_date*, or None."""
        r = self.load_report(trading_date)
        return r.loser_dna if r else None

    def neutral_dna(self, trading_date: str) -> Optional[NeutralDNA]:
        """Return the NeutralDNA for *trading_date*, or None."""
        r = self.load_report(trading_date)
        return r.neutral_dna if r else None

    def list_characteristics(
        self, trading_date: Optional[str] = None
    ) -> List[DNACharacteristic]:
        """Return all characteristics for one date, or all dates if None."""
        if trading_date is not None:
            r = self.load_report(trading_date)
            return r.all_characteristics if r else []
        chars: List[DNACharacteristic] = []
        for d in self.list_reports():
            r = self.load_report(d)
            if r:
                chars.extend(r.all_characteristics)
        return chars

    def list_reports(self) -> List[str]:
        """Return all available discovery dates as sorted ISO strings."""
        self._ensure_dirs()
        dates = [
            p.stem.removeprefix("dna_")
            for p in self._dna_dir.glob("dna_*.json")
        ]
        return sorted(dates)

    def load_report(self, trading_date: str) -> Optional[DiscoveryReport]:
        """Load a persisted discovery report. Returns None if absent."""
        path = self._path_for(trading_date)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return DiscoveryReport.from_dict(json.load(fh))

    def statistics(self, trading_date: str) -> Optional[DNAStatistics]:
        """Return aggregate statistics for one discovery date."""
        r = self.load_report(trading_date)
        if r is None:
            return None
        chars = r.all_characteristics
        w_dir = SeparationDirection.WINNERS_HIGHER
        l_dir = SeparationDirection.WINNERS_LOWER
        n_dir = {SeparationDirection.NEUTRALS_HIGHER, SeparationDirection.NEUTRALS_LOWER}

        w_chars = [c for c in chars if c.direction == w_dir]
        l_chars = [c for c in chars if c.direction == l_dir]
        n_chars = [c for c in chars if c.direction in n_dir]

        lifecycle_dist: Dict[str, int] = {}
        for c in chars:
            lifecycle_dist[c.lifecycle.value] = lifecycle_dist.get(c.lifecycle.value, 0) + 1

        avg_eff = round(sum(c.effect_abs for c in chars) / len(chars), 4) if chars else 0.0
        top_w   = max(w_chars, key=lambda c: c.effect_abs).feature_name if w_chars else None
        top_l   = max(l_chars, key=lambda c: c.effect_abs).feature_name if l_chars else None

        return DNAStatistics(
            trading_date=trading_date,
            total_characteristics=len(chars),
            winner_characteristics=len(w_chars),
            loser_characteristics=len(l_chars),
            neutral_characteristics=len(n_chars),
            total_interactions=len(r.all_interactions),
            top_winner_feature=top_w,
            top_loser_feature=top_l,
            avg_effect_size=avg_eff,
            lifecycle_distribution=lifecycle_dist,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE — group extraction
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_groups(
        self,
        classification: ClassificationResult,
        obs_map:        Dict[str, MarketObservation],
    ) -> Tuple[List[MarketObservation], List[MarketObservation], List[MarketObservation]]:
        """Extract winner, loser, and neutral observation groups."""
        win_labels = {GroupLabel(l) for l in self._config.dna_winner_labels}
        los_labels = {GroupLabel(l) for l in self._config.dna_loser_labels}

        winner_syms: set[str] = set()
        loser_syms:  set[str] = set()
        for p in classification.populations:
            if p.classifier_type != ClassifierType.PERFORMANCE:
                continue
            if p.label in win_labels:
                winner_syms |= set(p.members)
            elif p.label in los_labels:
                loser_syms |= set(p.members)

        neu_pop = classification.get_population_by_type(
            ClassifierType.PERFORMANCE, GroupLabel.NEUTRAL
        )
        neutral_syms = set(neu_pop.members) if neu_pop else set()

        return (
            [obs_map[s] for s in winner_syms  if s in obs_map],
            [obs_map[s] for s in loser_syms   if s in obs_map],
            [obs_map[s] for s in neutral_syms if s in obs_map],
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE — feature analysis
    # ═══════════════════════════════════════════════════════════════════════

    def _analyse_features(
        self,
        group_a:  List[MarketObservation],
        group_b:  List[MarketObservation],
        date:     str,
        regime:   str,
        history:  List[DiscoveryReport],
        dir_high: SeparationDirection,
        dir_low:  SeparationDirection,
    ) -> List[DNACharacteristic]:
        """Analyse all features and return those passing the effect-size gate."""
        # Collect all feature names that appear in both groups
        names_a = {k for o in group_a for k in o.features}
        names_b = {k for o in group_b for k in o.features}
        feature_names = sorted((names_a & names_b) - _MARKET_WIDE_FEATURES)

        chars: List[DNACharacteristic] = []
        for fname in feature_names:
            vals_a = [o.features.get(fname, 0.0) for o in group_a]
            vals_b = [o.features.get(fname, 0.0) for o in group_b]
            char = self._analyse_one_feature(
                fname, vals_a, vals_b,
                date, regime, history,
                dir_high, dir_low,
            )
            if char is not None:
                chars.append(char)
        return chars

    def _analyse_one_feature(
        self,
        feature_name: str,
        vals_a:       List[float],
        vals_b:       List[float],
        date:         str,
        regime:       str,
        history:      List[DiscoveryReport],
        dir_high:     SeparationDirection,
        dir_low:      SeparationDirection,
    ) -> Optional[DNACharacteristic]:
        """Analyse one feature.  Returns None if below effect-size gate."""
        cfg = self._config

        # Reject constant features (no between-group information)
        all_vals = vals_a + vals_b
        if len(all_vals) < 2:
            return None
        m_all = _mean(all_vals)
        pooled_var = sum((v - m_all) ** 2 for v in all_vals) / len(all_vals)
        if pooled_var < 1e-14:
            return None

        ftype = _detect_feature_type(all_vals)
        d     = _cohen_d(vals_a, vals_b)
        if abs(d) < cfg.dna_min_effect_size:
            return None

        # Bootstrap CI
        ci_lo, ci_hi = _bootstrap_ci(vals_a, vals_b, cfg.dna_bootstrap_samples)

        # Spearman: feature value vs winner-label (1=group_a, 0=group_b)
        combined_feat   = vals_a + vals_b
        performance_lbl = [1.0] * len(vals_a) + [0.0] * len(vals_b)
        spearman = _spearman(combined_feat, performance_lbl)

        direction = dir_high if d > 0 else dir_low

        confidence = self._compute_confidence(abs(d), ci_lo, ci_hi, abs(spearman))

        lifecycle, occurrence_count, first_seen = self._lifecycle_info(
            feature_name, direction, date, history
        )

        ma, mb  = _mean(vals_a), _mean(vals_b)
        std_a   = math.sqrt(_sample_var(vals_a))
        std_b   = math.sqrt(_sample_var(vals_b))

        evidence = FeatureEvidence(
            feature_name=feature_name,
            feature_type=ftype,
            winner_mean=round(ma,   6),
            winner_std=round(std_a, 6),
            loser_mean=round(mb,    6),
            loser_std=round(std_b,  6),
            effect_size=round(d,        6),
            effect_abs=round(abs(d),    6),
            direction=direction,
            ci_low=round(ci_lo,  6),
            ci_high=round(ci_hi, 6),
            spearman_corr=round(spearman, 6),
            n_winners=len(vals_a),
            n_losers=len(vals_b),
        )

        char_id = _make_id("DNA", feature_name, date, direction.value)

        return DNACharacteristic(
            char_id=char_id,
            feature_name=feature_name,
            feature_type=ftype,
            direction=direction,
            effect_size=round(d,        6),
            effect_abs=round(abs(d),    6),
            confidence=round(confidence, 4),
            lifecycle=lifecycle,
            trading_date=date,
            regime=regime,
            evidence=evidence,
            first_seen=first_seen,
            last_seen=date,
            occurrence_count=occurrence_count,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE — interaction discovery
    # ═══════════════════════════════════════════════════════════════════════

    def _discover_interactions(
        self,
        group_a:  List[MarketObservation],
        group_b:  List[MarketObservation],
        chars:    List[DNACharacteristic],
        date:     str,
        regime:   str,
    ) -> List[DNAInteraction]:
        """Find feature pairs with super-additive joint explanatory power."""
        if len(chars) < 2 or len(group_a) < 2 or len(group_b) < 2:
            return []

        threshold = self._config.dna_interaction_amplify
        # Consider the top-N characteristics only to bound combinatorial search
        top = sorted(chars, key=lambda c: c.effect_abs, reverse=True)[:8]

        interactions: List[DNAInteraction] = []
        seen: set[tuple[str, str]] = set()

        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                c1, c2    = top[i], top[j]
                pair_key  = (
                    min(c1.feature_name, c2.feature_name),
                    max(c1.feature_name, c2.feature_name),
                )
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                w_f1 = [o.features.get(c1.feature_name, 0.0) for o in group_a]
                w_f2 = [o.features.get(c2.feature_name, 0.0) for o in group_a]
                l_f1 = [o.features.get(c1.feature_name, 0.0) for o in group_b]
                l_f2 = [o.features.get(c2.feature_name, 0.0) for o in group_b]

                if not (w_f1 and w_f2 and l_f1 and l_f2):
                    continue

                # Pooled-normalise each feature independently
                w_f1n, l_f1n = _zscore_pooled(w_f1, l_f1)
                w_f2n, l_f2n = _zscore_pooled(w_f2, l_f2)

                w_joint = [a + b for a, b in zip(w_f1n, w_f2n)]
                l_joint = [a + b for a, b in zip(l_f1n, l_f2n)]

                joint_d     = _cohen_d(w_joint, l_joint)
                max_indiv   = max(c1.effect_abs, c2.effect_abs)
                amplify     = abs(joint_d) / max(1e-9, max_indiv) - 1.0

                if amplify >= threshold:
                    int_id = _make_id("INT", c1.feature_name, c2.feature_name, date)
                    interactions.append(DNAInteraction(
                        interaction_id=int_id,
                        features=[c1.feature_name, c2.feature_name],
                        joint_effect=round(abs(joint_d), 6),
                        max_individual=round(max_indiv, 6),
                        amplification=round(amplify, 6),
                        trading_date=date,
                        regime=regime,
                    ))

        return interactions

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE — confidence + lifecycle
    # ═══════════════════════════════════════════════════════════════════════

    def _compute_confidence(
        self,
        effect_abs:   float,
        ci_lo:        float,
        ci_hi:        float,
        spearman_abs: float,
    ) -> float:
        """Weighted [0, 1] confidence score using MLSConfig weights."""
        cfg     = self._config
        min_eff = max(cfg.dna_min_effect_size, 0.01)

        eff_score = min(1.0, effect_abs / (2.0 * min_eff))

        ci_width  = ci_hi - ci_lo
        ci_score  = max(0.0, 1.0 - ci_width / max(0.01, 2.0 * effect_abs))

        spr_score = min(1.0, spearman_abs / max(cfg.dna_min_spearman, 0.01))

        return (
            cfg.confidence_effect_size_weight    * eff_score
            + cfg.confidence_significance_weight * ci_score
            + cfg.confidence_consistency_weight  * spr_score
        )

    def _lifecycle_info(
        self,
        feature_name: str,
        direction:    SeparationDirection,
        date:         str,
        history:      List[DiscoveryReport],
    ) -> Tuple[DNALifecycle, int, str]:
        """Return (lifecycle, occurrence_count, first_seen)."""
        matching = [
            c
            for r in history
            for c in r.all_characteristics
            if c.feature_name == feature_name and c.direction == direction
        ]
        n = len(matching)
        first_seen = date

        if matching:
            first_seen = min(c.first_seen for c in matching)

        if n == 0:
            lifecycle = DNALifecycle.DISCOVERED
        elif n == 1:
            lifecycle = DNALifecycle.REPLICATED
        elif n >= 2 and n < 4:
            lifecycle = DNALifecycle.VERIFIED
        else:
            # Check for weakening: effect declining over last 3 appearances
            sorted_eff = [
                c.effect_abs
                for c in sorted(matching, key=lambda c: c.trading_date)
            ]
            if len(sorted_eff) >= 3 and sorted_eff[-1] < sorted_eff[-3] * 0.70:
                lifecycle = DNALifecycle.WEAKENING
            else:
                lifecycle = DNALifecycle.STABLE

        return lifecycle, n + 1, first_seen

    # ═══════════════════════════════════════════════════════════════════════
    # PRIVATE — storage
    # ═══════════════════════════════════════════════════════════════════════

    def _persist(self, report: DiscoveryReport) -> None:
        """Atomic write: .tmp -> os.replace, plus .bak of previous version."""
        self._ensure_dirs()
        path = self._path_for(report.trading_date)
        tmp  = path.with_suffix(".tmp")
        with self._lock:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(report.to_dict(), fh, indent=2)
            if path.exists():
                path.with_suffix(".bak").write_bytes(path.read_bytes())
            os.replace(tmp, path)

    def _path_for(self, trading_date: str) -> Path:
        return self._dna_dir / f"dna_{trading_date}.json"

    def _ensure_dirs(self) -> None:
        self._dna_dir.mkdir(parents=True, exist_ok=True)
