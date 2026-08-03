"""
dna_consensus_engine.py — MLS Phase 4: DNA Consensus Layer.

Responsibilities:
    Merge daily DiscoveryReport outputs into long-term institutional knowledge.
    Maintain ConsensusDNA records with full observation history.
    Compute confidence evolution, temporal stability, regime consistency.
    Detect statistical / regime / temporal / feature drift quantitatively.
    Advance the extended lifecycle: DISCOVERED→REPLICATED→VERIFIED→INSTITUTIONAL.
    Transition to WEAKENING, DRIFTING, or RETIRED on evidence.
    Persist the ConsensusLibrary atomically to data/mls/consensus/library.json.

Explicitly NOT responsible for:
    Feature extraction (Phase 1).
    Population classification (Phase 2).
    DNA discovery (Phase 3).
    Changing ARS knowledge stores.
    Producing trading decisions.
    Changing thresholds or config.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import date as _date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from market_learning.mls_config import MLSConfig
from market_learning.dna_discovery_models import (
    DiscoveryReport,
    DNACharacteristic,
    SeparationDirection,
)
from market_learning.dna_consensus_models import (
    ConsensusDNA,
    ConsensusLevel,
    ConsensusLibrary,
    ConsensusState,
    ConsensusStatistics,
    ConfidenceEvolution,
    ConfidencePoint,
    DNAConsensusError,
    DNAStability,
    DriftMeasurement,
    DriftReport,
    DriftType,
)

log = logging.getLogger(__name__)

_DEFAULT_MLS_DIR   = Path(__file__).resolve().parent.parent / "data" / "mls"
_LIBRARY_FILENAME  = "library.json"
# Number of canonical MLS market regimes used for regime_consistency denominator
_N_KNOWN_REGIMES   = 5  # bull_trend, bear_trend, range_bound, volatile, sideways


# ═══════════════════════════════════════════════════════════════════════════════
# Pure statistical helpers — no class state, fully testable in isolation
# ═══════════════════════════════════════════════════════════════════════════════

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _trend_slope(ys: List[float]) -> float:
    """OLS slope of ys vs integer x=[0,1,...,n-1].  Returns 0.0 for n<2."""
    n = len(ys)
    if n < 2:
        return 0.0
    mx = (n - 1) / 2.0
    my = _mean(ys)
    num = sum((i - mx) * (ys[i] - my) for i in range(n))
    den = sum((i - mx) ** 2 for i in range(n))
    return num / den if abs(den) > 1e-12 else 0.0


def _temporal_stability(effects: List[float]) -> float:
    """
    1 − coefficient-of-variation of effect_abs values.
    Returns 1.0 when n<2 or mean≈0 (no variation to measure).
    """
    if len(effects) < 2:
        return 1.0
    m = _mean(effects)
    if abs(m) < 1e-9:
        return 1.0
    variance = sum((e - m) ** 2 for e in effects) / len(effects)
    std = variance ** 0.5
    cv = std / abs(m)
    return max(0.0, min(1.0, 1.0 - cv))


def _replication_freq(count: int, first_seen: str, last_seen: str) -> float:
    """
    count / (calendar_days_span + 1).
    Capped at 1.0; returns 1.0 for single-day span.
    """
    span = max(1, (_date.fromisoformat(last_seen) - _date.fromisoformat(first_seen)).days + 1)
    return min(1.0, count / span)


def _regime_consistency(regime_counts: Dict[str, int]) -> float:
    """distinct_regimes_seen / _N_KNOWN_REGIMES, capped at 1.0."""
    return min(1.0, len(regime_counts) / _N_KNOWN_REGIMES)


def _feature_persistence(obs_dates: List[str], window: int, as_of_date: str) -> float:
    """
    Fraction of the last `window` calendar days where the feature appeared.
    Days are compared to as_of_date (inclusive on the as_of end, exclusive beyond window).
    """
    if window < 1:
        return 0.0
    as_of = _date.fromisoformat(as_of_date)
    count = sum(1 for d in obs_dates
                if 0 <= (as_of - _date.fromisoformat(d)).days < window)
    return min(1.0, count / window)


def _consensus_score(
    rep_freq:    float,
    temp_stab:   float,
    regime_cons: float,
    sector_cons: float,
    conf_trend:  float,
    persistence: float,
    cfg:         MLSConfig,
) -> float:
    """
    Reproducible weighted consensus score in [0, 1].

    conf_trend is an OLS slope; converted to [0,1] via:
        trend_score = clamp(0.5 + slope / (2 * declining_threshold), 0, 1)
    So a flat slope gives 0.5, strong positive gives 1.0, strong negative 0.0.
    """
    thr = max(cfg.consensus_trend_declining_slope, 1e-6)
    trend_score = min(1.0, max(0.0, 0.5 + conf_trend / (2.0 * thr)))
    raw = (
        cfg.consensus_w_replication  * rep_freq
        + cfg.consensus_w_temporal   * temp_stab
        + cfg.consensus_w_regime     * regime_cons
        + cfg.consensus_w_sector     * sector_cons
        + cfg.consensus_w_confidence * trend_score
        + cfg.consensus_w_persistence * persistence
    )
    return min(1.0, max(0.0, raw))


def _compute_consensus_state(
    count:       int,
    score:       float,
    max_drift:   float,
    conf_trend:  float,
    absent_days: int,
    cfg:         MLSConfig,
) -> ConsensusState:
    """
    Compute lifecycle state from measurable inputs.
    Evaluation order: RETIRED → DRIFTING → WEAKENING → INSTITUTIONAL → VERIFIED → REPLICATED → DISCOVERED.
    """
    if absent_days >= cfg.consensus_retirement_absent_days:
        return ConsensusState.RETIRED
    if max_drift >= cfg.consensus_drift_threshold:
        return ConsensusState.DRIFTING
    if (count >= cfg.consensus_institutional_min_count
            and conf_trend < -cfg.consensus_trend_declining_slope):
        return ConsensusState.WEAKENING
    if (count >= cfg.consensus_institutional_min_count
            and score >= cfg.consensus_institutional_min_score):
        return ConsensusState.INSTITUTIONAL
    if count >= 5:
        return ConsensusState.VERIFIED
    if count >= 2:
        return ConsensusState.REPLICATED
    return ConsensusState.DISCOVERED


def _compute_level(state: ConsensusState) -> ConsensusLevel:
    """Map ConsensusState to finest validated ConsensusLevel."""
    return {
        ConsensusState.DISCOVERED:    ConsensusLevel.DAILY,
        ConsensusState.REPLICATED:    ConsensusLevel.WEEKLY,
        ConsensusState.VERIFIED:      ConsensusLevel.MONTHLY,
        ConsensusState.INSTITUTIONAL: ConsensusLevel.MASTER,
        ConsensusState.WEAKENING:     ConsensusLevel.MONTHLY,
        ConsensusState.DRIFTING:      ConsensusLevel.WEEKLY,
        ConsensusState.RETIRED:       ConsensusLevel.DAILY,
    }.get(state, ConsensusLevel.DAILY)


# ─── drift helpers ────────────────────────────────────────────────────────────

def _statistical_drift(effects: List[float], window: int) -> float:
    """
    |mean_recent − mean_prior| / max(|mean_prior|, 1e-6).
    Requires at least 2*window observations; returns 0.0 otherwise.
    Capped at 1.0.
    """
    if window < 1 or len(effects) < 2 * window:
        return 0.0
    recent = effects[-window:]
    prior  = effects[-2 * window:-window]
    mr = _mean(recent)
    mp = _mean(prior)
    return min(1.0, abs(mr - mp) / max(abs(mp), 1e-6))


def _regime_drift(obs: List[Dict]) -> float:
    """
    Fraction of consecutive observation pairs with a regime change.
    Returns 0.0 for n<2.
    """
    n = len(obs)
    if n < 2:
        return 0.0
    changes = sum(1 for i in range(1, n)
                  if obs[i]["regime"] != obs[i - 1]["regime"])
    return changes / (n - 1)


def _temporal_drift(obs_dates: List[str], window: int, as_of_date: str) -> float:
    """
    Decline in appearance frequency: max(0, prior_freq − recent_freq).
    recent  = appearances in (0, window] days before as_of.
    prior   = appearances in (window, 2*window] days before as_of.
    Capped at 1.0.
    """
    if window < 1:
        return 0.0
    as_of = _date.fromisoformat(as_of_date)
    recent_n = sum(1 for d in obs_dates
                   if 0 <= (as_of - _date.fromisoformat(d)).days < window)
    prior_n  = sum(1 for d in obs_dates
                   if window <= (as_of - _date.fromisoformat(d)).days < 2 * window)
    r_freq = recent_n / window
    p_freq = prior_n  / window
    return min(1.0, max(0.0, p_freq - r_freq))


def _feature_drift(confidences: List[float], window: int, threshold: float) -> float:
    """
    Magnitude of confidence decline, normalised by threshold.
    Negative OLS slope → drift; positive or zero slope → 0.0.
    Capped at 1.0.
    """
    if len(confidences) < 2:
        return 0.0
    recent = confidences[-window:] if len(confidences) >= window else confidences
    slope  = _trend_slope(recent)
    if slope >= 0.0:
        return 0.0
    return min(1.0, abs(slope) / max(threshold, 1e-6))


# ─── id helpers ───────────────────────────────────────────────────────────────

def _make_consensus_id(feature_name: str, direction: SeparationDirection) -> str:
    raw = f"{feature_name}::{direction.value}"
    return "CON-" + hashlib.sha256(raw.encode()).hexdigest()[:8]


def _consensus_key(feature_name: str, direction: SeparationDirection) -> str:
    return f"{feature_name}::{direction.value}"


def _absent_days(last_seen: str, trading_date: str) -> int:
    return (_date.fromisoformat(trading_date) - _date.fromisoformat(last_seen)).days


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class DNAConsensusEngine:
    """
    Transforms daily DiscoveryReport outputs into institutional market knowledge.

    Call update(report) once per trading day after DNADiscoveryEngine.discover().
    All other methods are read-only and safe to call from any thread.
    """

    def __init__(
        self,
        config:   Optional[MLSConfig] = None,
        data_dir: Optional[str]       = None,
    ) -> None:
        self._cfg  = config or MLSConfig()
        base       = Path(data_dir) if data_dir else _DEFAULT_MLS_DIR / "consensus"
        self._dir  = base
        self._lib_path = self._dir / _LIBRARY_FILENAME
        self._lock = threading.Lock()
        self._ensure_dirs()

    # ── public API ────────────────────────────────────────────────────────────

    def update(self, report: DiscoveryReport) -> ConsensusLibrary:
        """
        Merge the daily DiscoveryReport into the consensus library.

        Thread-safe.  Idempotent per trading_date (duplicate updates for the
        same date are silently ignored).
        Returns the updated ConsensusLibrary.
        """
        with self._lock:
            store = self._load_store()

            present_keys: set = set()
            for char in report.all_characteristics:
                key = _consensus_key(char.feature_name, char.direction)
                present_keys.add(key)
                if key not in store:
                    store[key] = self._create_new(char, report.trading_date)
                else:
                    store[key] = self._merge(store[key], char, report.trading_date)

            # Retirement sweep — features absent from this report
            for key, cdna in store.items():
                if key not in present_keys and cdna.consensus_state != ConsensusState.RETIRED:
                    absent = _absent_days(cdna.last_seen, report.trading_date)
                    if absent >= self._cfg.consensus_retirement_absent_days:
                        import dataclasses
                        store[key] = dataclasses.replace(
                            cdna,
                            consensus_state=ConsensusState.RETIRED,
                            level=ConsensusLevel.DAILY,
                        )

            lib = self._build_library(store, report.trading_date)
            self._persist(lib)
            return lib

    def master_library(self) -> ConsensusLibrary:
        """Return the full consensus library from disk (read-only)."""
        lib = self._load_library()
        if lib is None:
            return self._empty_library()
        return lib

    def confidence_history(
        self,
        feature_name: str,
        direction:    Optional[str]          = None,
        level:        ConsensusLevel         = ConsensusLevel.WEEKLY,
    ) -> List[ConfidenceEvolution]:
        """
        Return ConfidenceEvolution for every matching (feature_name, direction) pair.
        If direction is None, all directions are returned.
        """
        store = self._load_store()
        results: List[ConfidenceEvolution] = []

        window_map = {
            ConsensusLevel.DAILY:     1,
            ConsensusLevel.WEEKLY:    7,
            ConsensusLevel.MONTHLY:   20,
            ConsensusLevel.QUARTERLY: 60,
            ConsensusLevel.YEARLY:    252,
            ConsensusLevel.MASTER:    0,  # 0 = all observations
        }
        window = window_map.get(level, 7)

        for cdna in store.values():
            if cdna.feature_name != feature_name:
                continue
            if direction and cdna.direction.value != direction:
                continue

            obs = cdna.all_observations
            if window > 0:
                obs = obs[-window:]

            points = [
                ConfidencePoint(
                    date=o["date"],
                    confidence=o["confidence"],
                    effect_abs=o["effect_abs"],
                    regime=o["regime"],
                    lifecycle=cdna.consensus_state.value,
                )
                for o in obs
            ]
            confidences = [p.confidence for p in points]
            slope = _trend_slope(confidences)
            thr   = self._cfg.consensus_trend_declining_slope

            if slope > thr:
                direction_label = "IMPROVING"
            elif slope < -thr:
                direction_label = "DECLINING"
            else:
                direction_label = "STABLE"

            results.append(ConfidenceEvolution(
                feature_name=feature_name,
                direction=cdna.direction.value,
                level=level,
                points=points,
                trend_slope=round(slope, 6),
                trend_direction=direction_label,
                window_days=window if window > 0 else len(obs),
            ))
        return results

    def drift_report(
        self,
        feature_name: Optional[str] = None,
        direction:    Optional[str] = None,
    ) -> List[DriftReport]:
        """Return drift reports, optionally filtered by feature_name and/or direction."""
        lib = self._load_library()
        if lib is None:
            return []
        reports = lib.drift_reports
        if feature_name:
            reports = [r for r in reports if r.feature_name == feature_name]
        if direction:
            reports = [r for r in reports if r.direction == direction]
        return reports

    def stable_dna(self) -> List[ConsensusDNA]:
        """Return all ConsensusDNA that meet every stability threshold."""
        store = self._load_store()
        cfg   = self._cfg
        return [
            c for c in store.values()
            if (c.replication_frequency >= cfg.consensus_stability_min_rep_freq
                and c.temporal_stability >= cfg.consensus_stability_min_temporal
                and c.regime_consistency >= cfg.consensus_stability_min_regime
                and c.consensus_state not in (ConsensusState.RETIRED,
                                              ConsensusState.DRIFTING))
        ]

    def retired_dna(self) -> List[ConsensusDNA]:
        """Return all ConsensusDNA in RETIRED state."""
        store = self._load_store()
        return [c for c in store.values() if c.consensus_state == ConsensusState.RETIRED]

    def statistics(self) -> ConsensusStatistics:
        """Return aggregate statistics for the current library."""
        lib = self._load_library()
        if lib is None:
            return ConsensusStatistics(
                as_of_date="", total_consensus_dna=0, institutional_count=0,
                weakening_count=0, drifting_count=0, retired_count=0,
                avg_consensus_score=0.0, avg_replication_freq=0.0,
                top_institutional_feature=None,
            )
        return lib.statistics

    # ── internal — construction ───────────────────────────────────────────────

    def _create_new(self, char: DNACharacteristic, trading_date: str) -> ConsensusDNA:
        obs  = _obs_dict(trading_date, char.effect_abs, char.confidence, char.regime)
        rc   = {char.regime: 1}
        rep  = 1.0
        tst  = 1.0
        reg  = _regime_consistency(rc)
        sec  = reg
        trnd = 0.0
        pers = _feature_persistence([trading_date], self._cfg.consensus_trend_window, trading_date)
        scr  = _consensus_score(rep, tst, reg, sec, trnd, pers, self._cfg)
        st   = _compute_consensus_state(1, scr, 0.0, trnd, 0, self._cfg)
        return ConsensusDNA(
            consensus_id=_make_consensus_id(char.feature_name, char.direction),
            feature_name=char.feature_name,
            direction=char.direction,
            consensus_state=st,
            consensus_score=round(scr, 6),
            replication_frequency=rep,
            evidence_count=1,
            temporal_stability=tst,
            regime_consistency=round(reg, 6),
            sector_consistency=round(sec, 6),
            confidence_trend=trnd,
            feature_persistence=round(pers, 6),
            first_seen=trading_date,
            last_seen=trading_date,
            all_observations=[obs],
            regime_counts=rc,
            level=_compute_level(st),
        )

    def _merge(
        self, cdna: ConsensusDNA, char: DNACharacteristic, trading_date: str
    ) -> ConsensusDNA:
        # Idempotent: skip if this date is already recorded
        existing_dates = {o["date"] for o in cdna.all_observations}
        if trading_date in existing_dates:
            return cdna

        new_obs  = _obs_dict(trading_date, char.effect_abs, char.confidence, char.regime)
        all_obs  = sorted(cdna.all_observations + [new_obs], key=lambda o: o["date"])

        rc = dict(cdna.regime_counts)
        rc[char.regime] = rc.get(char.regime, 0) + 1

        effects     = [o["effect_abs"]  for o in all_obs]
        confidences = [o["confidence"]  for o in all_obs]
        dates       = [o["date"]        for o in all_obs]
        count       = len(all_obs)

        rep  = _replication_freq(count, cdna.first_seen, trading_date)
        tst  = _temporal_stability(effects)
        reg  = _regime_consistency(rc)
        sec  = reg
        w    = self._cfg.consensus_trend_window
        trnd = _trend_slope(confidences[-w:] if len(confidences) >= w else confidences)
        pers = _feature_persistence(dates, w, trading_date)

        dw  = self._cfg.consensus_drift_window
        thr = self._cfg.consensus_trend_declining_slope
        sd  = _statistical_drift(effects, dw)
        rd  = _regime_drift(all_obs)
        td  = _temporal_drift(dates, dw, trading_date)
        fd  = _feature_drift(confidences, dw, thr)
        mx  = max(sd, rd, td, fd)

        scr = _consensus_score(rep, tst, reg, sec, trnd, pers, self._cfg)
        st  = _compute_consensus_state(count, scr, mx, trnd, 0, self._cfg)

        return ConsensusDNA(
            consensus_id=cdna.consensus_id,
            feature_name=cdna.feature_name,
            direction=cdna.direction,
            consensus_state=st,
            consensus_score=round(scr, 6),
            replication_frequency=round(rep, 6),
            evidence_count=count,
            temporal_stability=round(tst, 6),
            regime_consistency=round(reg, 6),
            sector_consistency=round(sec, 6),
            confidence_trend=round(trnd, 6),
            feature_persistence=round(pers, 6),
            first_seen=cdna.first_seen,
            last_seen=trading_date,
            all_observations=all_obs,
            regime_counts=rc,
            level=_compute_level(st),
        )

    # ── internal — library assembly ───────────────────────────────────────────

    def _build_library(self, store: Dict[str, ConsensusDNA], as_of: str) -> ConsensusLibrary:
        all_c  = sorted(store.values(), key=lambda c: c.consensus_score, reverse=True)
        master = [c for c in all_c if c.consensus_state == ConsensusState.INSTITUTIONAL]
        drs    = [self._build_drift_report(c, as_of)
                  for c in all_c if c.evidence_count >= 2]
        stats  = self._build_statistics(all_c, as_of)
        return ConsensusLibrary(
            library_id=f"MLS-LIB-{as_of.replace('-', '')}",
            as_of_date=as_of,
            all_consensus=all_c,
            master_consensus=master,
            drift_reports=drs,
            statistics=stats,
        )

    def _build_drift_report(self, cdna: ConsensusDNA, as_of: str) -> DriftReport:
        effects     = [o["effect_abs"]  for o in cdna.all_observations]
        confidences = [o["confidence"]  for o in cdna.all_observations]
        dates       = [o["date"]        for o in cdna.all_observations]
        dw  = self._cfg.consensus_drift_window
        thr = self._cfg.consensus_drift_threshold
        dec = self._cfg.consensus_trend_declining_slope

        sd = _statistical_drift(effects, dw)
        rd = _regime_drift(cdna.all_observations)
        td = _temporal_drift(dates, dw, as_of)
        fd = _feature_drift(confidences, dw, dec)

        drifts = [
            DriftMeasurement(DriftType.STATISTICAL, round(sd, 4),
                             f"effect_abs shift={sd:.3f}", sd >= thr),
            DriftMeasurement(DriftType.REGIME,      round(rd, 4),
                             f"regime_change_freq={rd:.3f}", rd >= thr),
            DriftMeasurement(DriftType.TEMPORAL,    round(td, 4),
                             f"frequency_decline={td:.3f}", td >= thr),
            DriftMeasurement(DriftType.FEATURE,     round(fd, 4),
                             f"confidence_slope_magnitude={fd:.3f}", fd >= thr),
        ]
        mx  = max(d.magnitude for d in drifts)
        h   = hashlib.sha256(f"{cdna.consensus_id}:{as_of}".encode()).hexdigest()[:8]
        return DriftReport(
            drift_report_id=f"DRF-{h}",
            feature_name=cdna.feature_name,
            direction=cdna.direction.value,
            trading_date=as_of,
            drifts=drifts,
            max_drift=round(mx, 4),
            has_significant_drift=mx >= thr,
        )

    def _build_statistics(
        self, all_c: List[ConsensusDNA], as_of: str
    ) -> ConsensusStatistics:
        if not all_c:
            return ConsensusStatistics(
                as_of_date=as_of, total_consensus_dna=0, institutional_count=0,
                weakening_count=0, drifting_count=0, retired_count=0,
                avg_consensus_score=0.0, avg_replication_freq=0.0,
                top_institutional_feature=None,
            )
        inst   = [c for c in all_c if c.consensus_state == ConsensusState.INSTITUTIONAL]
        top    = max(inst, key=lambda c: c.consensus_score, default=None)
        n      = len(all_c)
        return ConsensusStatistics(
            as_of_date=as_of,
            total_consensus_dna=n,
            institutional_count=len(inst),
            weakening_count=sum(1 for c in all_c if c.consensus_state == ConsensusState.WEAKENING),
            drifting_count=sum(1 for c in all_c if c.consensus_state == ConsensusState.DRIFTING),
            retired_count=sum(1 for c in all_c if c.consensus_state == ConsensusState.RETIRED),
            avg_consensus_score=round(sum(c.consensus_score for c in all_c) / n, 4),
            avg_replication_freq=round(sum(c.replication_frequency for c in all_c) / n, 4),
            top_institutional_feature=top.feature_name if top else None,
        )

    # ── internal — storage ────────────────────────────────────────────────────

    def _load_store(self) -> Dict[str, ConsensusDNA]:
        if not self._lib_path.exists():
            return {}
        try:
            with open(self._lib_path, encoding="utf-8") as f:
                data = json.load(f)
            return {
                _consensus_key(c.feature_name, c.direction): c
                for c in (ConsensusDNA.from_dict(d)
                          for d in data.get("all_consensus", []))
            }
        except (json.JSONDecodeError, KeyError) as exc:
            log.warning("consensus library corrupt, starting fresh: %s", exc)
            return {}

    def _load_library(self) -> Optional[ConsensusLibrary]:
        if not self._lib_path.exists():
            return None
        try:
            with open(self._lib_path, encoding="utf-8") as f:
                data = json.load(f)
            return ConsensusLibrary.from_dict(data)
        except (json.JSONDecodeError, KeyError) as exc:
            log.warning("consensus library unreadable: %s", exc)
            return None

    def _persist(self, lib: ConsensusLibrary) -> None:
        tmp = self._lib_path.with_suffix(".tmp")
        bak = self._lib_path.with_suffix(".bak")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(lib.to_dict(), f, indent=2)
        if self._lib_path.exists():
            self._lib_path.replace(bak)
        tmp.replace(self._lib_path)

    def _ensure_dirs(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _empty_library(self) -> ConsensusLibrary:
        empty_stats = ConsensusStatistics(
            as_of_date="", total_consensus_dna=0, institutional_count=0,
            weakening_count=0, drifting_count=0, retired_count=0,
            avg_consensus_score=0.0, avg_replication_freq=0.0,
            top_institutional_feature=None,
        )
        return ConsensusLibrary(
            library_id="MLS-LIB-EMPTY",
            as_of_date="",
            all_consensus=[],
            master_consensus=[],
            drift_reports=[],
            statistics=empty_stats,
        )


# ─── helpers ──────────────────────────────────────────────────────────────────

def _obs_dict(date: str, effect_abs: float, confidence: float, regime: str) -> Dict:
    return {"date": date, "effect_abs": effect_abs, "confidence": confidence, "regime": regime}
