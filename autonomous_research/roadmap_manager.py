"""
roadmap_manager.py — Scientific research prioritization engine.

ARS Phase 2B.

Responsibilities:
    Evaluate KnowledgeGap objects from GapDetector.
    Estimate scientific knowledge gain (KnowledgeGainEstimator).
    Estimate execution effort (ResearchCostEstimator).
    Track accumulated research debt (ResearchDebt).
    Maintain balanced portfolio allocation (PortfolioManager).
    Produce an optimized, transparent research roadmap.

Explicitly NOT responsible for:
    Executing research.
    Generating hypotheses.
    Modifying knowledge stores.
    Writing reports.
    Re-detecting gaps.

All priority scores and knowledge gain estimates are deterministic:
given identical gaps and config, build() always produces identical scores.

State persistence (data/ars_roadmap_state.json) tracks when each gap_id was
first observed, enabling research debt to accumulate across runs.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .cross_study_synthesizer import CrossStudySynthesizer
from .gap_detector import GapDetector
from .gap_models import GapCategory, GapSeverity, GapStatus, KnowledgeGap
from .hypothesis_registry import HypothesisRegistry
from .knowledge_provider import KnowledgeProvider
from .roadmap_models import (
    KnowledgeGainEstimate,
    ResearchCostEstimate,
    ResearchDebt,
    ResearchPortfolio,
    ResearchRoadmap,
    RoadmapBuildError,
    RoadmapEntry,
    RoadmapEntryStatus,
    RoadmapManagerConfig,
    RoadmapStatistics,
    StudyCategory,
)

logger = logging.getLogger(__name__)

_DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "ars_roadmap_state.json"
_STATE_VERSION = "1.0"

# ─── Module-level lookup tables (all values documented) ──────────────────────

_SEVERITY_IMPORTANCE: Dict[GapSeverity, float] = {
    GapSeverity.CRITICAL: 1.00,
    GapSeverity.HIGH:     0.75,
    GapSeverity.MEDIUM:   0.50,
    GapSeverity.LOW:      0.25,
}

_SEVERITY_BASE_DEBT: Dict[GapSeverity, float] = {
    GapSeverity.CRITICAL: 1.00,
    GapSeverity.HIGH:     0.75,
    GapSeverity.MEDIUM:   0.50,
    GapSeverity.LOW:      0.25,
}

_SEVERITY_FINDINGS_SCALE: Dict[GapSeverity, float] = {
    GapSeverity.CRITICAL: 2.0,
    GapSeverity.HIGH:     1.5,
    GapSeverity.MEDIUM:   1.0,
    GapSeverity.LOW:      0.5,
}

# How much evidence is missing for each gap category (supports evidence_gap_size)
_CATEGORY_EVIDENCE_GAP: Dict[GapCategory, float] = {
    GapCategory.EVIDENCE_GAP:      0.85,
    GapCategory.CONTRADICTION_GAP: 0.80,
    GapCategory.CONFIDENCE_GAP:    0.70,
    GapCategory.COVERAGE_GAP:      0.70,
    GapCategory.DATA_GAP:          0.60,
    GapCategory.REGIME_GAP:        0.65,
    GapCategory.KNOWLEDGE_GAP:     0.60,
    GapCategory.VALIDATION_GAP:    0.55,
    GapCategory.SECTOR_GAP:        0.50,
    GapCategory.TEMPORAL_GAP:      0.40,
}

# How much confidence we expect to gain by addressing each gap
_CATEGORY_CONF_IMPROVEMENT: Dict[GapCategory, float] = {
    GapCategory.CONFIDENCE_GAP:    0.80,
    GapCategory.EVIDENCE_GAP:      0.70,
    GapCategory.CONTRADICTION_GAP: 0.65,
    GapCategory.KNOWLEDGE_GAP:     0.65,
    GapCategory.COVERAGE_GAP:      0.60,
    GapCategory.VALIDATION_GAP:    0.60,
    GapCategory.REGIME_GAP:        0.55,
    GapCategory.DATA_GAP:          0.50,
    GapCategory.TEMPORAL_GAP:      0.45,
    GapCategory.SECTOR_GAP:        0.45,
}

# How much regime/sector/classification coverage the study will add
_CATEGORY_COVERAGE: Dict[GapCategory, float] = {
    GapCategory.REGIME_GAP:        0.80,
    GapCategory.COVERAGE_GAP:      0.75,
    GapCategory.SECTOR_GAP:        0.70,
    GapCategory.TEMPORAL_GAP:      0.60,
    GapCategory.KNOWLEDGE_GAP:     0.50,
    GapCategory.DATA_GAP:          0.45,
    GapCategory.EVIDENCE_GAP:      0.40,
    GapCategory.VALIDATION_GAP:    0.40,
    GapCategory.CONFIDENCE_GAP:    0.35,
    GapCategory.CONTRADICTION_GAP: 0.30,
}

# How novel/unexplored is this territory
_CATEGORY_NOVELTY: Dict[GapCategory, float] = {
    GapCategory.COVERAGE_GAP:      0.90,  # never studied
    GapCategory.REGIME_GAP:        0.70,
    GapCategory.KNOWLEDGE_GAP:     0.65,
    GapCategory.SECTOR_GAP:        0.60,
    GapCategory.CONTRADICTION_GAP: 0.50,  # revisiting existing territory
    GapCategory.EVIDENCE_GAP:      0.45,  # corroborating existing findings
    GapCategory.CONFIDENCE_GAP:    0.40,
    GapCategory.VALIDATION_GAP:    0.40,
    GapCategory.TEMPORAL_GAP:      0.35,
    GapCategory.DATA_GAP:          0.30,  # extending existing study
}

# How broadly reusable will the new findings be
_CATEGORY_REUSE: Dict[GapCategory, float] = {
    GapCategory.VALIDATION_GAP:    0.90,  # validation insights benefit all edge users
    GapCategory.REGIME_GAP:        0.80,
    GapCategory.CONTRADICTION_GAP: 0.75,  # resolving contradictions helps all consumers
    GapCategory.EVIDENCE_GAP:      0.70,
    GapCategory.COVERAGE_GAP:      0.65,
    GapCategory.KNOWLEDGE_GAP:     0.65,
    GapCategory.TEMPORAL_GAP:      0.60,
    GapCategory.SECTOR_GAP:        0.60,
    GapCategory.DATA_GAP:          0.55,
    GapCategory.CONFIDENCE_GAP:    0.55,
}

# How much uncertainty the study will remove
_CATEGORY_UNCERTAINTY: Dict[GapCategory, float] = {
    GapCategory.CONTRADICTION_GAP: 0.85,
    GapCategory.CONFIDENCE_GAP:    0.80,
    GapCategory.EVIDENCE_GAP:      0.70,
    GapCategory.KNOWLEDGE_GAP:     0.65,
    GapCategory.COVERAGE_GAP:      0.60,
    GapCategory.VALIDATION_GAP:    0.60,
    GapCategory.DATA_GAP:          0.50,
    GapCategory.REGIME_GAP:        0.55,
    GapCategory.SECTOR_GAP:        0.45,
    GapCategory.TEMPORAL_GAP:      0.40,
}

# Estimated number of new findings per category (baseline, scaled by severity)
_CATEGORY_NEW_FINDINGS: Dict[GapCategory, int] = {
    GapCategory.COVERAGE_GAP:      6,
    GapCategory.REGIME_GAP:        4,
    GapCategory.SECTOR_GAP:        4,
    GapCategory.DATA_GAP:          3,
    GapCategory.KNOWLEDGE_GAP:     3,
    GapCategory.TEMPORAL_GAP:      3,
    GapCategory.EVIDENCE_GAP:      2,
    GapCategory.VALIDATION_GAP:    2,
    GapCategory.CONTRADICTION_GAP: 2,
    GapCategory.CONFIDENCE_GAP:    2,
}

# Historical data lookback required in days
_CATEGORY_HIST_DAYS: Dict[GapCategory, int] = {
    GapCategory.TEMPORAL_GAP:      365,
    GapCategory.DATA_GAP:          180,
    GapCategory.KNOWLEDGE_GAP:     180,
    GapCategory.REGIME_GAP:        120,
    GapCategory.SECTOR_GAP:        120,
    GapCategory.COVERAGE_GAP:      120,
    GapCategory.EVIDENCE_GAP:       90,
    GapCategory.CONTRADICTION_GAP:  90,
    GapCategory.VALIDATION_GAP:     90,
    GapCategory.CONFIDENCE_GAP:     60,
}

# Expected replay / compute duration
_CATEGORY_REPLAY_HOURS: Dict[GapCategory, float] = {
    GapCategory.VALIDATION_GAP:    4.0,
    GapCategory.CONTRADICTION_GAP: 3.0,
    GapCategory.TEMPORAL_GAP:      3.0,
    GapCategory.REGIME_GAP:        2.0,
    GapCategory.SECTOR_GAP:        2.0,
    GapCategory.DATA_GAP:          2.0,
    GapCategory.COVERAGE_GAP:      2.0,
    GapCategory.KNOWLEDGE_GAP:     1.5,
    GapCategory.EVIDENCE_GAP:      1.0,
    GapCategory.CONFIDENCE_GAP:    1.0,
}

# Relative implementation effort
_CATEGORY_EFFORT: Dict[GapCategory, float] = {
    GapCategory.CONTRADICTION_GAP: 0.70,
    GapCategory.REGIME_GAP:        0.60,
    GapCategory.KNOWLEDGE_GAP:     0.60,
    GapCategory.SECTOR_GAP:        0.50,
    GapCategory.COVERAGE_GAP:      0.50,
    GapCategory.TEMPORAL_GAP:      0.45,
    GapCategory.DATA_GAP:          0.40,
    GapCategory.VALIDATION_GAP:    0.40,
    GapCategory.EVIDENCE_GAP:      0.35,
    GapCategory.CONFIDENCE_GAP:    0.35,
}

# Execution risk
_CATEGORY_RISK: Dict[GapCategory, float] = {
    GapCategory.TEMPORAL_GAP:      0.40,
    GapCategory.CONTRADICTION_GAP: 0.35,
    GapCategory.DATA_GAP:          0.30,
    GapCategory.KNOWLEDGE_GAP:     0.30,
    GapCategory.REGIME_GAP:        0.25,
    GapCategory.SECTOR_GAP:        0.25,
    GapCategory.VALIDATION_GAP:    0.25,
    GapCategory.EVIDENCE_GAP:      0.20,
    GapCategory.CONFIDENCE_GAP:    0.20,
    GapCategory.COVERAGE_GAP:      0.20,
}

# Portfolio category mapping
_GAP_TO_STUDY_CATEGORY: Dict[GapCategory, StudyCategory] = {
    GapCategory.DATA_GAP:          StudyCategory.VALIDATION,
    GapCategory.EVIDENCE_GAP:      StudyCategory.WINNER_DNA,
    GapCategory.REGIME_GAP:        StudyCategory.MARKET_REGIMES,
    GapCategory.SECTOR_GAP:        StudyCategory.SECTOR_RESEARCH,
    GapCategory.TEMPORAL_GAP:      StudyCategory.VALIDATION,
    GapCategory.VALIDATION_GAP:    StudyCategory.VALIDATION,
    GapCategory.CONTRADICTION_GAP: StudyCategory.RISK,
    GapCategory.CONFIDENCE_GAP:    StudyCategory.EXPLORATION,
    GapCategory.KNOWLEDGE_GAP:     StudyCategory.EXPLORATION,
    GapCategory.COVERAGE_GAP:      StudyCategory.MARKET_REGIMES,
}

_CATEGORY_STUDY_PREFIX: Dict[GapCategory, str] = {
    GapCategory.DATA_GAP:          "Data expansion",
    GapCategory.EVIDENCE_GAP:      "Corroboration study",
    GapCategory.REGIME_GAP:        "Regime coverage",
    GapCategory.SECTOR_GAP:        "Sector expansion",
    GapCategory.TEMPORAL_GAP:      "Knowledge refresh",
    GapCategory.VALIDATION_GAP:    "Walk-forward validation",
    GapCategory.CONTRADICTION_GAP: "Contradiction resolution",
    GapCategory.CONFIDENCE_GAP:    "Confidence improvement",
    GapCategory.KNOWLEDGE_GAP:     "Hypothesis investigation",
    GapCategory.COVERAGE_GAP:      "Classification coverage",
}

_CATEGORY_APPROACH: Dict[GapCategory, str] = {
    GapCategory.DATA_GAP:
        "Expand data window targeting minimum observation count",
    GapCategory.EVIDENCE_GAP:
        "Independent corroboration study with same methodology",
    GapCategory.REGIME_GAP:
        "Regime-specific feature analysis with market context",
    GapCategory.SECTOR_GAP:
        "Sector-stratified feature extraction run",
    GapCategory.TEMPORAL_GAP:
        "Full replay cycle with latest market data",
    GapCategory.VALIDATION_GAP:
        "Walk-forward validation with out-of-sample hold-out",
    GapCategory.CONTRADICTION_GAP:
        "Controlled A/B study with matched conditions to resolve conflict",
    GapCategory.CONFIDENCE_GAP:
        "Multi-source evidence aggregation to improve confidence",
    GapCategory.KNOWLEDGE_GAP:
        "Targeted investigation to advance stalled hypothesis",
    GapCategory.COVERAGE_GAP:
        "Exploratory study targeting uncovered classification",
}


def _entry_id(gap_id: str) -> str:
    """Deterministic entry ID from gap_id."""
    return f"RE-{hashlib.sha256(gap_id.encode()).hexdigest()[:8].upper()}"


class RoadmapManager:
    """
    Scientific research prioritization engine for IIOS.

    Consumes KnowledgeGap objects (from GapDetector or supplied directly),
    evaluates each gap across five dimensions, and produces a ranked,
    portfolio-balanced research roadmap.

    All scores are deterministic and fully documented.  Nothing is modified.

    Usage::

        kp  = KnowledgeProvider()
        reg = HypothesisRegistry(knowledge_provider=kp)
        syn = CrossStudySynthesizer(knowledge_provider=kp, hypothesis_registry=reg)
        gd  = GapDetector(kp, reg, syn)
        rm  = RoadmapManager(kp, reg, syn, gap_detector=gd)

        roadmap = rm.build()
        next_study = rm.get_next_study()
        print(rm.portfolio())
    """

    def __init__(
        self,
        knowledge_provider: KnowledgeProvider,
        hypothesis_registry: Optional[HypothesisRegistry] = None,
        synthesizer: Optional[CrossStudySynthesizer] = None,
        gap_detector: Optional[GapDetector] = None,
        config: Optional[RoadmapManagerConfig] = None,
        state_path: Optional[Path] = None,
    ) -> None:
        self._kp   = knowledge_provider
        self._reg  = hypothesis_registry
        self._syn  = synthesizer
        self._gd   = gap_detector
        self._cfg  = config or RoadmapManagerConfig()
        self._state_path = Path(state_path) if state_path else _DEFAULT_STATE_PATH
        self._lock = threading.Lock()
        self._last_roadmap: Optional[ResearchRoadmap] = None
        self._state: Dict[str, datetime] = self._load_state()

    # ═════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═════════════════════════════════════════════════════════════════════════

    def build(
        self,
        gaps: Optional[List[KnowledgeGap]] = None,
        force: bool = False,
    ) -> ResearchRoadmap:
        """
        Build (or return cached) research roadmap.

        Parameters
        ----------
        gaps:  KnowledgeGap list to evaluate.  If None, calls gap_detector.detect().
        force: Re-run even if a cached roadmap exists.

        Raises
        ------
        RoadmapBuildError: if gaps is None and no gap_detector was provided.
        """
        with self._lock:
            if self._last_roadmap is not None and not force:
                return self._last_roadmap

            t0 = time.perf_counter()
            warnings: List[str] = []
            now = datetime.now()

            # Resolve gap source
            if gaps is None:
                if self._gd is None:
                    raise RoadmapBuildError(
                        "gaps=None requires a gap_detector; none was provided."
                    )
                source_gaps = list(self._gd.detect(force=force).gaps)
            else:
                source_gaps = list(gaps)

            if not source_gaps:
                warnings.append("No gaps provided — returning empty roadmap.")
                self._last_roadmap = self._empty_roadmap(now, warnings, 0.0)
                return self._last_roadmap

            # Record first-seen timestamps (for debt accumulation)
            changed = False
            for gap in source_gaps:
                if gap.gap_id not in self._state:
                    self._state[gap.gap_id] = now
                    changed = True
            if changed:
                self._save_state()

            # Build entries
            raw: List[RoadmapEntry] = []
            for gap in source_gaps:
                kg      = self._estimate_knowledge_gain(gap)
                cost    = self._estimate_cost(gap)
                debt    = self._calculate_debt(gap)
                prio, pb = self._calculate_priority(kg, cost, debt, gap)
                cat     = _GAP_TO_STUDY_CATEGORY[gap.category]
                title   = (f"{_CATEGORY_STUDY_PREFIX[gap.category]}: "
                           f"{gap.title[:60]}")
                raw.append(RoadmapEntry(
                    entry_id=_entry_id(gap.gap_id),
                    gap=gap,
                    knowledge_gain_estimate=kg,
                    cost_estimate=cost,
                    debt=debt,
                    priority_score=prio,
                    priority_breakdown=pb,
                    study_category=cat,
                    status=RoadmapEntryStatus.PENDING,
                    rank=0,
                    recommended_study_title=title,
                    recommended_approach=_CATEGORY_APPROACH[gap.category],
                    created_at=now,
                ))

            # Sort descending by priority; tie-break by gap_id (alphabetical) for determinism
            raw.sort(key=lambda e: (-e.priority_score, e.gap.gap_id))
            for i, entry in enumerate(raw):
                entry.rank = i + 1

            duration_ms = (time.perf_counter() - t0) * 1000
            portfolio   = self._build_portfolio(raw)
            stats       = self._build_statistics(raw, duration_ms, now)

            self._last_roadmap = ResearchRoadmap(
                roadmap_id=f"RM-{uuid.uuid4().hex[:8].upper()}",
                built_at=now,
                entries=raw,
                portfolio=portfolio,
                statistics=stats,
                warnings=warnings,
            )
            return self._last_roadmap

    def list_entries(self) -> List[RoadmapEntry]:
        """Return all entries sorted by rank.  Empty before first build()."""
        if self._last_roadmap is None:
            return []
        return list(self._last_roadmap.entries)

    def top_priorities(self, n: Optional[int] = None) -> List[RoadmapEntry]:
        """Return the top N highest-priority entries (default: config.default_top_n)."""
        count = n if n is not None else self._cfg.default_top_n
        return self.list_entries()[:count]

    def portfolio(self) -> ResearchPortfolio:
        """Return portfolio analysis from the last build().  Empty before first build()."""
        if self._last_roadmap is None:
            return ResearchPortfolio(
                total_entries=0,
                allocation={cat.value: 0 for cat in StudyCategory},
                target_allocation=self._cfg.portfolio_allocation,
                actual_fraction={cat.value: 0.0 for cat in StudyCategory},
                balance_score=0.0,
                imbalanced_categories=[],
                recommendations=["No roadmap built yet — call build() first."],
            )
        return self._last_roadmap.portfolio

    def statistics(self) -> RoadmapStatistics:
        """Return statistics from the last build().  Zero stats before first build()."""
        if self._last_roadmap is None:
            return RoadmapStatistics(
                total_entries=0, pending_entries=0,
                avg_priority_score=0.0, avg_knowledge_gain=0.0,
                avg_cost=0.0, avg_debt=0.0,
                by_gap_category={}, by_severity={}, by_study_category={},
                top_priority_entry_id=None,
                total_research_debt=0.0,
                build_duration_ms=0.0,
                built_at=datetime.now(),
            )
        return self._last_roadmap.statistics

    def get_next_study(self) -> Optional[RoadmapEntry]:
        """Return the single highest-priority entry (rank=1), or None."""
        entries = self.list_entries()
        return entries[0] if entries else None

    # ═════════════════════════════════════════════════════════════════════════
    # KNOWLEDGE GAIN ESTIMATOR
    # ═════════════════════════════════════════════════════════════════════════

    def _estimate_knowledge_gain(self, gap: KnowledgeGap) -> KnowledgeGainEstimate:
        """
        Estimate the scientific knowledge gain of addressing this gap.

        Formula (component weights are constants documented in KnowledgeGainEstimate):
            raw_gain  = si*0.25 + eg*0.20 + ci*0.20 + cov*0.15 + nov*0.10 + rp*0.10
            adjusted  = raw_gain * (1 + ur * 0.15)
            final     = adjusted * (0.70 + hi * 0.30)
            total_gain = clamp(final, 0.0, 1.0)
        """
        si  = _SEVERITY_IMPORTANCE[gap.severity]
        eg  = _CATEGORY_EVIDENCE_GAP[gap.category]
        ci  = _CATEGORY_CONF_IMPROVEMENT[gap.category]
        cov = _CATEGORY_COVERAGE[gap.category]
        nov = _CATEGORY_NOVELTY[gap.category]
        rp  = _CATEGORY_REUSE[gap.category]
        ur  = _CATEGORY_UNCERTAINTY[gap.category]
        hi  = gap.estimated_knowledge_gain   # proxy: set by GapDetector from severity

        raw_gain = (
            si  * 0.25
            + eg  * 0.20
            + ci  * 0.20
            + cov * 0.15
            + nov * 0.10
            + rp  * 0.10
        )
        adjusted   = raw_gain * (1.0 + ur * 0.15)
        final      = adjusted * (0.70 + hi * 0.30)
        total_gain = min(1.0, max(0.0, final))

        base_count = _CATEGORY_NEW_FINDINGS[gap.category]
        scale      = _SEVERITY_FINDINGS_SCALE[gap.severity]
        new_findings = max(1, int(base_count * scale))

        breakdown: Dict[str, float] = {
            "scientific_importance":           si,
            "evidence_gap_size":               eg,
            "expected_confidence_improvement": ci,
            "coverage_increase":               cov,
            "novelty":                         nov,
            "reuse_potential":                 rp,
            "uncertainty_reduction":           ur,
            "historical_impact":               hi,
            "raw_gain":                        round(raw_gain,   4),
            "adjusted_gain":                   round(adjusted,   4),
            "final_gain":                      round(final,      4),
            "w_scientific_importance":         0.25,
            "w_evidence_gap_size":             0.20,
            "w_confidence_improvement":        0.20,
            "w_coverage_increase":             0.15,
            "w_novelty":                       0.10,
            "w_reuse_potential":               0.10,
            "uncertainty_bonus_factor":        0.15,
            "historical_impact_floor":         0.70,
            "historical_impact_ceiling":       0.30,
        }

        return KnowledgeGainEstimate(
            gap_id=gap.gap_id,
            scientific_importance=si,
            evidence_gap_size=eg,
            current_confidence=gap.confidence,
            expected_confidence_improvement=ci,
            expected_new_findings=new_findings,
            coverage_increase=cov,
            novelty=nov,
            historical_impact=hi,
            reuse_potential=rp,
            uncertainty_reduction=ur,
            total_gain=total_gain,
            breakdown=breakdown,
        )

    # ═════════════════════════════════════════════════════════════════════════
    # RESEARCH COST ESTIMATOR
    # ═════════════════════════════════════════════════════════════════════════

    def _estimate_cost(self, gap: KnowledgeGap) -> ResearchCostEstimate:
        """
        Estimate the effort required to address this gap.

        Formula:
            replay_factor = min(1.0, replay_hours / 8.0)
            total_cost    = effort * 0.40 + risk * 0.30 + replay_factor * 0.30
        """
        effort       = _CATEGORY_EFFORT[gap.category]
        risk         = _CATEGORY_RISK[gap.category]
        hist_days    = _CATEGORY_HIST_DAYS[gap.category]
        replay_hours = _CATEGORY_REPLAY_HOURS[gap.category]
        replay_factor = min(1.0, replay_hours / 8.0)
        total_cost   = (effort * 0.40 + risk * 0.30 + replay_factor * 0.30)
        total_cost   = min(1.0, max(0.0, total_cost))

        # Dependencies: open hypotheses for KNOWLEDGE_GAP type
        deps: List[str] = list(gap.related_hypotheses) if gap.category == GapCategory.KNOWLEDGE_GAP else []

        breakdown: Dict[str, Any] = {
            "implementation_effort":          effort,
            "risk":                           risk,
            "historical_days_required":       hist_days,
            "replay_duration_hours":          replay_hours,
            "replay_factor":                  round(replay_factor, 4),
            "total_cost":                     round(total_cost, 4),
            "w_implementation_effort":        0.40,
            "w_risk":                         0.30,
            "w_replay":                       0.30,
            "replay_normalization_hours":     8.0,
        }

        return ResearchCostEstimate(
            gap_id=gap.gap_id,
            historical_days_required=hist_days,
            replay_duration_estimate_hours=replay_hours,
            implementation_effort=effort,
            dependencies=deps,
            risk=risk,
            total_cost=total_cost,
            breakdown=breakdown,
        )

    # ═════════════════════════════════════════════════════════════════════════
    # RESEARCH DEBT
    # ═════════════════════════════════════════════════════════════════════════

    def _calculate_debt(self, gap: KnowledgeGap) -> ResearchDebt:
        """
        Calculate accumulated research debt.

        Debt grows with time (age_debt), severity (base_debt), and special
        conditions (contradiction_debt, expiry_debt).
        """
        base_debt = _SEVERITY_BASE_DEBT[gap.severity]

        first_seen    = self._state.get(gap.gap_id, gap.created_at)
        age_days      = max(0, (datetime.now() - first_seen).days)
        half_life     = max(1, self._cfg.debt_half_life_days)
        age_debt      = min(1.0, age_days / half_life)

        contradiction_debt = 0.30 if gap.category == GapCategory.CONTRADICTION_GAP else 0.0
        expiry_debt        = 0.20 if gap.category == GapCategory.TEMPORAL_GAP      else 0.0

        total_debt = min(1.0, max(0.0,
            base_debt          * 0.50
            + age_debt         * 0.30
            + contradiction_debt * 0.10
            + expiry_debt      * 0.10
        ))

        rationale = (
            f"base={base_debt:.2f} (severity {gap.severity.value}), "
            f"age={age_debt:.2f} ({age_days}d / {half_life}d half-life), "
            f"contradiction={contradiction_debt:.2f}, "
            f"expiry={expiry_debt:.2f}"
        )

        breakdown: Dict[str, float] = {
            "base_debt":                    base_debt,
            "age_debt":                     age_debt,
            "contradiction_debt":           contradiction_debt,
            "expiry_debt":                  expiry_debt,
            "base_debt_contribution":       base_debt          * 0.50,
            "age_debt_contribution":        age_debt           * 0.30,
            "contradiction_contribution":   contradiction_debt * 0.10,
            "expiry_contribution":          expiry_debt        * 0.10,
            "w_base_debt":                  0.50,
            "w_age_debt":                   0.30,
            "w_contradiction":              0.10,
            "w_expiry":                     0.10,
            "age_days":                     float(age_days),
            "debt_half_life_days":          float(half_life),
        }

        return ResearchDebt(
            gap_id=gap.gap_id,
            category=gap.category,
            severity=gap.severity,
            base_debt=base_debt,
            age_debt=age_debt,
            contradiction_debt=contradiction_debt,
            expiry_debt=expiry_debt,
            total_debt=total_debt,
            accumulation_rationale=rationale,
            breakdown=breakdown,
        )

    # ═════════════════════════════════════════════════════════════════════════
    # PRIORITY SCORER
    # ═════════════════════════════════════════════════════════════════════════

    def _calculate_priority(
        self,
        kg:   KnowledgeGainEstimate,
        cost: ResearchCostEstimate,
        debt: ResearchDebt,
        gap:  KnowledgeGap,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Compute the final priority score for a roadmap entry.

        Formula:
            urgency = severity_importance * temporal_factor
            priority = (
                kg.total_gain   * w_kg
                + debt.total    * w_debt
                + kg.sci_import * w_si
                + (1-cost)      * w_cost
                + urgency       * w_urgency
            ) / total_weight
        """
        cfg = self._cfg
        w = {
            "w_knowledge_gain":        cfg.w_knowledge_gain,
            "w_research_debt":         cfg.w_research_debt,
            "w_scientific_importance": cfg.w_scientific_importance,
            "w_cost_efficiency":       cfg.w_cost_efficiency,
            "w_urgency":               cfg.w_urgency,
        }
        total_w = sum(w.values())

        urgency = _SEVERITY_IMPORTANCE[gap.severity]
        if gap.category == GapCategory.TEMPORAL_GAP:
            urgency = min(1.0, urgency * 1.20)  # temporal gaps are more urgent

        kg_score   = kg.total_gain
        debt_score = debt.total_debt
        si_score   = kg.scientific_importance
        cost_eff   = 1.0 - cost.total_cost   # lower cost = higher priority
        urg_score  = urgency

        raw = (
            kg_score   * w["w_knowledge_gain"]
            + debt_score * w["w_research_debt"]
            + si_score   * w["w_scientific_importance"]
            + cost_eff   * w["w_cost_efficiency"]
            + urg_score  * w["w_urgency"]
        )
        priority = min(1.0, max(0.0, raw / total_w))

        breakdown: Dict[str, Any] = {
            "knowledge_gain_score":             round(kg_score,   4),
            "research_debt_score":              round(debt_score, 4),
            "scientific_importance_score":      round(si_score,   4),
            "cost_efficiency_score":            round(cost_eff,   4),
            "urgency_score":                    round(urg_score,  4),
            "knowledge_gain_contribution":      round(kg_score   * w["w_knowledge_gain"]        / total_w, 4),
            "research_debt_contribution":       round(debt_score * w["w_research_debt"]         / total_w, 4),
            "scientific_importance_contribution": round(si_score * w["w_scientific_importance"] / total_w, 4),
            "cost_efficiency_contribution":     round(cost_eff   * w["w_cost_efficiency"]       / total_w, 4),
            "urgency_contribution":             round(urg_score  * w["w_urgency"]               / total_w, 4),
            "weights_used":                     w,
            "total_weight":                     round(total_w, 4),
            "raw_score":                        round(raw,       4),
            "final_priority":                   round(priority,  4),
        }

        return priority, breakdown

    # ═════════════════════════════════════════════════════════════════════════
    # PORTFOLIO MANAGER
    # ═════════════════════════════════════════════════════════════════════════

    def _build_portfolio(self, entries: List[RoadmapEntry]) -> ResearchPortfolio:
        alloc: Dict[str, int] = {cat.value: 0 for cat in StudyCategory}
        for entry in entries:
            alloc[entry.study_category.value] += 1

        total = len(entries) or 1
        actual: Dict[str, float] = {cat: count / total for cat, count in alloc.items()}
        target = self._cfg.portfolio_allocation
        thresh = self._cfg.portfolio_imbalance_threshold

        imbalanced: List[str] = []
        total_dev = 0.0
        recs: List[str] = []
        for cat_str, tgt in sorted(target.items()):
            act = actual.get(cat_str, 0.0)
            dev = abs(act - tgt)
            total_dev += dev
            if dev > thresh:
                imbalanced.append(cat_str)
                if act < tgt:
                    recs.append(
                        f"Add more {cat_str} studies "
                        f"(current {act:.0%}, target {tgt:.0%})"
                    )
                else:
                    recs.append(
                        f"Reduce {cat_str} studies "
                        f"(current {act:.0%}, target {tgt:.0%})"
                    )

        n_cats = len(target) or 1
        balance_score = max(0.0, 1.0 - total_dev / n_cats)

        return ResearchPortfolio(
            total_entries=len(entries),
            allocation=alloc,
            target_allocation=target,
            actual_fraction=actual,
            balance_score=round(balance_score, 4),
            imbalanced_categories=imbalanced,
            recommendations=recs,
        )

    # ═════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═════════════════════════════════════════════════════════════════════════

    def _build_statistics(
        self, entries: List[RoadmapEntry], duration_ms: float, built_at: datetime
    ) -> RoadmapStatistics:
        by_cat:  Dict[str, int] = {}
        by_sev:  Dict[str, int] = {}
        by_scat: Dict[str, int] = {}
        for e in entries:
            by_cat[e.gap.category.value]    = by_cat.get(e.gap.category.value, 0) + 1
            by_sev[e.gap.severity.value]    = by_sev.get(e.gap.severity.value, 0) + 1
            by_scat[e.study_category.value] = by_scat.get(e.study_category.value, 0) + 1

        n = len(entries)
        avg = lambda xs: sum(xs) / len(xs) if xs else 0.0

        pending = sum(1 for e in entries if e.status == RoadmapEntryStatus.PENDING)
        top_id  = entries[0].entry_id if entries else None
        tot_debt = sum(e.debt.total_debt for e in entries)

        return RoadmapStatistics(
            total_entries=n,
            pending_entries=pending,
            avg_priority_score=round(avg([e.priority_score for e in entries]), 4),
            avg_knowledge_gain=round(avg([e.knowledge_gain_estimate.total_gain for e in entries]), 4),
            avg_cost=round(avg([e.cost_estimate.total_cost for e in entries]), 4),
            avg_debt=round(avg([e.debt.total_debt for e in entries]), 4),
            by_gap_category=by_cat,
            by_severity=by_sev,
            by_study_category=by_scat,
            top_priority_entry_id=top_id,
            total_research_debt=round(tot_debt, 4),
            build_duration_ms=round(duration_ms, 2),
            built_at=built_at,
        )

    # ═════════════════════════════════════════════════════════════════════════
    # STATE PERSISTENCE (for debt accumulation across runs)
    # ═════════════════════════════════════════════════════════════════════════

    def _load_state(self) -> Dict[str, datetime]:
        if self._state_path is None or not self._state_path.exists():
            return {}
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            return {
                k: datetime.fromisoformat(v)
                for k, v in data.get("gap_first_seen", {}).items()
            }
        except Exception as exc:
            logger.warning("[RoadmapManager] Failed to load state: %s", exc)
            return {}

    def _save_state(self) -> None:
        if self._state_path is None:
            return
        payload = {
            "version":       _STATE_VERSION,
            "last_updated":  datetime.now().isoformat(),
            "gap_first_seen": {k: v.isoformat() for k, v in self._state.items()},
        }
        try:
            tmp = self._state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            if self._state_path.exists():
                shutil.copy2(str(self._state_path),
                             str(self._state_path.with_suffix(".bak")))
            os.replace(str(tmp), str(self._state_path))
        except Exception as exc:
            logger.warning("[RoadmapManager] Failed to save state: %s", exc)

    # ═════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _empty_roadmap(
        self, now: datetime, warnings: List[str], duration_ms: float
    ) -> ResearchRoadmap:
        port  = self._build_portfolio([])
        stats = self._build_statistics([], duration_ms, now)
        return ResearchRoadmap(
            roadmap_id=f"RM-{uuid.uuid4().hex[:8].upper()}",
            built_at=now,
            entries=[],
            portfolio=port,
            statistics=stats,
            warnings=warnings,
        )
