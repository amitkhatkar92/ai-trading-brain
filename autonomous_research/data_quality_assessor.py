"""
data_quality_assessor.py — Scientific Data Quality Assessment engine.

IIOS Research Governance — Phase 4 (Permanent Scientific Evolution).

Measures 11 independent quality dimensions against the current knowledge base
and computes an overall Scientific Data Readiness Score (0-100).

Reuses:
    KnowledgeProvider — list_features(), list_edges(), list_studies()
    sfr_models        — DQADimension, DQAResult, DQAClassification

Does NOT duplicate:
    GapDetector       — detects gaps; DQA measures quality dimensions
    EvidenceValidator — validates individual findings; DQA scores the whole DB
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .sfr_models import DQAClassification, DQADimension, DQAResult, _now_iso

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# DNA feature vocabulary (union of all known DNA patterns — all studies)
# ─────────────────────────────────────────────────────────────────────────────
_DNA_FEATURES = [
    "atr_14", "intra_range", "mom_5d", "close_pos",
    "sect_conviction", "sect_part5d", "avg_conviction",
    "mom_1d", "mom_10d", "mom_20d", "vol_ratio",
    "cons_up_days", "breadth", "sector_flow_count",
    "sector_strength", "volume_spike", "pcr",
]

# Dimension weights (sum to 1.0)
_DIM_WEIGHTS: Dict[str, float] = {
    "overall_completeness":    0.08,
    "feature_completeness":    0.14,   # atr_14 and compound DNA features
    "historical_completeness": 0.10,
    "temporal_completeness":   0.08,
    "sector_completeness":     0.08,
    "regime_completeness":     0.07,
    "direction_completeness":  0.10,   # BUY / SELL / NEUTRAL
    "compound_completeness":   0.12,   # compound pattern validation
    "missing_feature_coverage": 0.09,
    "evidence_confidence":     0.07,
    "statistical_power":       0.07,
}

# Thresholds (minimum acceptable values)
_THRESHOLDS = {
    "overall_completeness":    0.80,   # 80% features present per record
    "feature_completeness":    2000,   # records with atr_14
    "historical_completeness": 4,      # years of coverage
    "temporal_completeness":   30,     # max avg gap between records (days)
    "sector_completeness":     5,      # distinct sectors
    "regime_completeness":     2,      # distinct regimes
    "direction_completeness":  0.10,   # min SELL edge fraction
    "compound_completeness":   3,      # compound patterns validated
    "missing_feature_coverage": 1,     # at most 1 DNA feature missing
    "evidence_confidence":     0.60,   # synthesized finding confidence
    "statistical_power":       2000,   # total records
}


class DataQualityAssessor:
    """
    Measures 11 evidence quality dimensions and produces a Scientific Data
    Readiness Score (0-100).

    Reuses KnowledgeProvider exclusively.  Does not call GapDetector or
    EvidenceValidator (those serve different purposes).
    """

    def __init__(self, knowledge_provider=None) -> None:
        self._kp = knowledge_provider

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def assess(self) -> DQAResult:
        """Run all 11 dimension assessments and return a DQAResult."""
        ts = _now_iso()

        # Load raw data once
        features = self._load_features()
        edges    = self._load_edges()
        studies  = self._load_studies()

        dims: List[DQADimension] = [
            self._dim_overall_completeness(features),
            self._dim_feature_completeness(features),
            self._dim_historical_completeness(features),
            self._dim_temporal_completeness(features),
            self._dim_sector_completeness(features),
            self._dim_regime_completeness(features),
            self._dim_direction_completeness(edges),
            self._dim_compound_completeness(features),
            self._dim_missing_feature_coverage(features),
            self._dim_evidence_confidence(studies),
            self._dim_statistical_power(features),
        ]

        # Weighted overall score (0-100)
        overall = 0.0
        for dim in dims:
            w = _DIM_WEIGHTS.get(dim.name, 1 / len(dims))
            overall += (dim.score / 10.0) * w * 100.0
        overall = min(100.0, max(0.0, overall))

        classification = self._classify(overall)
        weaknesses     = [d.finding for d in dims if d.status == "FAIL"]
        recs           = [d.recommendation for d in dims if d.status != "PASS" and d.recommendation]

        summary = (
            f"DQA score={overall:.1f}/100 ({classification.value}) "
            f"dims={len([d for d in dims if d.status == 'PASS'])}/{len(dims)} PASS"
        )

        log.info("[DQA] %s", summary)
        return DQAResult(
            assessed_at=ts,
            dimensions=dims,
            overall_score=overall,
            classification=classification,
            weaknesses=weaknesses,
            recommendations=recs,
            summary_line=summary,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Dimension implementations
    # ─────────────────────────────────────────────────────────────────────

    def _dim_overall_completeness(self, features: List[Dict]) -> DQADimension:
        """What fraction of records have all expected feature slots filled?"""
        if not features:
            return self._dim_fail("overall_completeness", 0, "records", 0.80,
                                  "No feature records.", "Run Phase 2 feature expansion.")
        # count features per record, compare to expected full set
        all_keys = set()
        for r in features:
            all_keys.update(r.get("features", {}).keys())
        expected = len(all_keys)
        completeness = sum(
            len(r.get("features", {})) / expected
            for r in features if expected > 0
        ) / len(features)
        score  = min(10.0, completeness / _THRESHOLDS["overall_completeness"] * 10.0)
        status = "PASS" if completeness >= _THRESHOLDS["overall_completeness"] else (
            "MARGINAL" if completeness >= _THRESHOLDS["overall_completeness"] * 0.8 else "FAIL")
        return DQADimension(
            name="overall_completeness",
            score=score,
            raw_value=round(completeness, 3),
            unit="ratio",
            threshold=_THRESHOLDS["overall_completeness"],
            status=status,
            finding=f"Average feature completeness per record: {completeness:.1%}",
            recommendation="" if status == "PASS" else
                "Add missing feature computations to the feature generation pipeline.",
        )

    def _dim_feature_completeness(self, features: List[Dict]) -> DQADimension:
        """Records containing atr_14 (the blocking DNA feature)."""
        n_total  = len(features)
        n_atr14  = sum(1 for r in features if "atr_14" in r.get("features", {}))
        thresh   = _THRESHOLDS["feature_completeness"]
        score    = min(10.0, (n_atr14 / thresh) * 10.0) if thresh > 0 else 10.0
        status   = "PASS" if n_atr14 >= thresh else ("MARGINAL" if n_atr14 >= thresh * 0.5 else "FAIL")
        pct_str  = f"{n_atr14/n_total*100:.1f}%" if n_total > 0 else "N/A"
        return DQADimension(
            name="feature_completeness",
            score=score,
            raw_value=n_atr14,
            unit="records_with_atr_14",
            threshold=thresh,
            status=status,
            finding=f"Records with atr_14: {n_atr14:,}/{n_total:,} ({pct_str})",
            recommendation="" if status == "PASS" else
                "Run rii001.py Phase 2 to backfill atr_14 from replay.db.",
        )

    def _dim_historical_completeness(self, features: List[Dict]) -> DQADimension:
        """Year span of feature records."""
        years  = set(r.get("ts", "")[:4] for r in features if r.get("ts"))
        years  = {y for y in years if y.isdigit()}
        n_years = len(years)
        thresh  = _THRESHOLDS["historical_completeness"]
        score   = min(10.0, n_years / thresh * 10.0)
        status  = "PASS" if n_years >= thresh else ("MARGINAL" if n_years >= thresh - 1 else "FAIL")
        yr_range = f"{min(years)}–{max(years)}" if years else "N/A"
        return DQADimension(
            name="historical_completeness",
            score=score,
            raw_value=n_years,
            unit="years",
            threshold=thresh,
            status=status,
            finding=f"Coverage: {yr_range} ({n_years} years)",
            recommendation="" if status == "PASS" else
                f"Expand historical data to cover {thresh}+ years using replay.db.",
        )

    def _dim_temporal_completeness(self, features: List[Dict]) -> DQADimension:
        """Average gap between consecutive records (should be ≤30 days)."""
        dates = sorted(
            set(r.get("ts", "") for r in features if r.get("ts")),
            key=lambda d: d,
        )
        if len(dates) < 2:
            return self._dim_fail("temporal_completeness", 999, "avg_gap_days",
                                  _THRESHOLDS["temporal_completeness"],
                                  "Fewer than 2 dated records.", "Add more feature records.")
        try:
            dt_list = [datetime.fromisoformat(d[:10]) for d in dates if d]
            gaps = [(dt_list[i+1] - dt_list[i]).days for i in range(len(dt_list)-1)]
            avg_gap = sum(gaps) / len(gaps)
        except Exception:
            avg_gap = 999

        thresh = _THRESHOLDS["temporal_completeness"]
        score  = min(10.0, (thresh / avg_gap) * 10.0) if avg_gap > 0 else 10.0
        score  = max(0.0, score)
        status = "PASS" if avg_gap <= thresh else ("MARGINAL" if avg_gap <= thresh * 2 else "FAIL")
        return DQADimension(
            name="temporal_completeness",
            score=score,
            raw_value=round(avg_gap, 1),
            unit="avg_gap_days",
            threshold=thresh,
            status=status,
            finding=f"Average gap between consecutive records: {avg_gap:.1f} days",
            recommendation="" if status == "PASS" else
                "Increase sampling frequency — aim for daily records per symbol.",
        )

    def _dim_sector_completeness(self, features: List[Dict]) -> DQADimension:
        """Number of distinct sectors with evidence."""
        sectors = {r.get("sector") for r in features if r.get("sector")}
        n = len(sectors)
        thresh = _THRESHOLDS["sector_completeness"]
        score  = min(10.0, n / thresh * 10.0)
        status = "PASS" if n >= thresh else ("MARGINAL" if n >= thresh - 2 else "FAIL")
        return DQADimension(
            name="sector_completeness",
            score=score,
            raw_value=n,
            unit="sectors",
            threshold=thresh,
            status=status,
            finding=f"Distinct sectors with evidence: {n}",
            recommendation="" if status == "PASS" else
                f"Add symbols from {thresh - n} more sectors to the universe.",
        )

    def _dim_regime_completeness(self, features: List[Dict]) -> DQADimension:
        """Number of distinct market regimes represented."""
        regimes = {r.get("regime") for r in features if r.get("regime")}
        n = len(regimes)
        thresh = _THRESHOLDS["regime_completeness"]
        score  = min(10.0, n / thresh * 10.0)
        status = "PASS" if n >= thresh else "FAIL"
        return DQADimension(
            name="regime_completeness",
            score=score,
            raw_value=n,
            unit="regimes",
            threshold=thresh,
            status=status,
            finding=f"Distinct regimes: {n} ({', '.join(sorted(r for r in regimes if r))})",
            recommendation="" if status == "PASS" else
                "Ensure feature records span multiple market regimes (TRENDING, SIDEWAYS, VOLATILE).",
        )

    def _dim_direction_completeness(self, edges: List[Dict]) -> DQADimension:
        """SELL-side edge fraction (should be ≥10%)."""
        dirs  = Counter(str(e.get("direction", "")).upper() for e in edges)
        buy_n = dirs.get("BUY", 0) + dirs.get("LONG", 0)
        sel_n = dirs.get("SELL", 0) + dirs.get("SHORT", 0)
        total = len(edges)
        sell_frac = sel_n / total if total > 0 else 0.0
        thresh    = _THRESHOLDS["direction_completeness"]
        score     = min(10.0, (sell_frac / thresh) * 10.0) if thresh > 0 else 10.0
        status    = "PASS" if sell_frac >= thresh else ("MARGINAL" if sell_frac >= thresh * 0.5 else "FAIL")
        return DQADimension(
            name="direction_completeness",
            score=score,
            raw_value=round(sell_frac, 3),
            unit="sell_fraction",
            threshold=thresh,
            status=status,
            finding=f"Edges: BUY={buy_n}, SELL={sel_n} ({sell_frac:.1%} SELL)",
            recommendation="" if status == "PASS" else
                "Initiate SELL-side DNA Discovery program (H-SELL-001).",
        )

    def _dim_compound_completeness(self, features: List[Dict]) -> DQADimension:
        """Number of compound DNA patterns that can be tested (have atr_14)."""
        n_atr14 = sum(1 for r in features if "atr_14" in r.get("features", {}))
        # Proxy: if atr_14 records >= 2000, compound patterns are testable
        n_testable_patterns = 9  # W01-W09 from IRP-002
        thresh  = _THRESHOLDS["compound_completeness"]
        # Score based on whether we have sufficient records for compound testing
        completeness_ratio = min(1.0, n_atr14 / 2000) if n_atr14 > 0 else 0.0
        score   = min(10.0, completeness_ratio * 10.0 * (n_testable_patterns / thresh))
        score   = min(10.0, score)
        status  = "PASS" if n_atr14 >= 2000 else ("MARGINAL" if n_atr14 >= 500 else "FAIL")
        return DQADimension(
            name="compound_completeness",
            score=score,
            raw_value=n_atr14,
            unit="atr14_records_for_compound_testing",
            threshold=2000,
            status=status,
            finding=f"Compound DNA testable: {n_atr14:,} records with atr_14",
            recommendation="" if status == "PASS" else
                "Backfill atr_14 using replay.db OHLCV data (see rii001.py).",
        )

    def _dim_missing_feature_coverage(self, features: List[Dict]) -> DQADimension:
        """Count of DNA features completely absent from the feature DB."""
        present = set()
        for r in features:
            present.update(r.get("features", {}).keys())
        missing = [f for f in _DNA_FEATURES if f not in present]
        n_missing = len(missing)
        thresh    = _THRESHOLDS["missing_feature_coverage"]
        score     = max(0.0, 10.0 - n_missing * 3.0)   # lose 3 pts per missing feature
        status    = "PASS" if n_missing <= 0 else ("MARGINAL" if n_missing <= thresh else "FAIL")
        return DQADimension(
            name="missing_feature_coverage",
            score=score,
            raw_value=n_missing,
            unit="missing_dna_features",
            threshold=0,
            status=status,
            finding=f"Missing DNA features: {missing if missing else 'none'}",
            recommendation="" if status == "PASS" else
                f"Add {missing} to feature computation pipeline.",
        )

    def _dim_evidence_confidence(self, studies: List[Any]) -> DQADimension:
        """Mean confidence across most recent studies."""
        confs: List[float] = []
        for s in studies:
            c = getattr(s, "confidence", None)
            if c is None:
                c = s.get("confidence") if isinstance(s, dict) else None
            if isinstance(c, (int, float)):
                confs.append(float(c))
        avg_conf = sum(confs) / len(confs) if confs else 0.5
        thresh   = _THRESHOLDS["evidence_confidence"]
        score    = min(10.0, (avg_conf / thresh) * 10.0)
        status   = "PASS" if avg_conf >= thresh else ("MARGINAL" if avg_conf >= thresh * 0.8 else "FAIL")
        return DQADimension(
            name="evidence_confidence",
            score=score,
            raw_value=round(avg_conf, 3),
            unit="mean_confidence",
            threshold=thresh,
            status=status,
            finding=f"Mean study confidence: {avg_conf:.3f} ({len(confs)} studies)",
            recommendation="" if status == "PASS" else
                "Increase replication studies to raise confidence above 0.60.",
        )

    def _dim_statistical_power(self, features: List[Dict]) -> DQADimension:
        """Total feature records — statistical power proxy."""
        n       = len(features)
        thresh  = _THRESHOLDS["statistical_power"]
        score   = min(10.0, (n / thresh) * 10.0)
        status  = "PASS" if n >= thresh else ("MARGINAL" if n >= thresh * 0.5 else "FAIL")
        return DQADimension(
            name="statistical_power",
            score=score,
            raw_value=n,
            unit="total_feature_records",
            threshold=thresh,
            status=status,
            finding=f"Total feature records: {n:,} (need ≥{thresh:,})",
            recommendation="" if status == "PASS" else
                "Expand historical feature records using replay.db.",
        )

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _classify(score: float) -> DQAClassification:
        if score >= 85:  return DQAClassification.EXCELLENT
        if score >= 70:  return DQAClassification.GOOD
        if score >= 55:  return DQAClassification.ADEQUATE
        if score >= 40:  return DQAClassification.LIMITED
        return DQAClassification.INSUFFICIENT

    @staticmethod
    def _dim_fail(name: str, raw: Any, unit: str, threshold: float,
                  finding: str, rec: str) -> DQADimension:
        return DQADimension(
            name=name, score=0.0, raw_value=raw, unit=unit,
            threshold=threshold, status="FAIL",
            finding=finding, recommendation=rec,
        )

    def _load_features(self) -> List[Dict]:
        if not self._kp:
            return []
        try:
            # Use a large limit to get all records for quality assessment
            recs = self._kp.list_features(limit=50000)
            return [r.__dict__ if hasattr(r, "__dict__") else r for r in recs]
        except Exception as exc:
            log.warning("[DQA] Failed to load features: %s", exc)
            return []

    def _load_edges(self) -> List[Dict]:
        if not self._kp:
            return []
        try:
            edges = self._kp.list_edges()
            return [e.__dict__ if hasattr(e, "__dict__") else vars(e)
                    for e in edges]
        except Exception as exc:
            log.warning("[DQA] Failed to load edges: %s", exc)
            return []

    def _load_studies(self) -> List[Any]:
        if not self._kp:
            return []
        try:
            return self._kp.list_studies()
        except Exception as exc:
            log.warning("[DQA] Failed to load studies: %s", exc)
            return []
