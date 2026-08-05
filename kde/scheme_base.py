"""
scheme_base.py — Abstract base for all KDE discovery schemes.

Each scheme asks exactly one scientific question and emits DiscoveryCandidate
objects.  New schemes require zero changes to the KDE engine.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .kde_models import DiscoveryCandidate, DiscoveryEvidence, EvidenceType

log = logging.getLogger(__name__)


# ── discovery context ─────────────────────────────────────────────────────────

@dataclass
class DiscoveryContext:
    """
    Read-only holder for all inputs available to every scheme.

    Thread-safe: schemes must never mutate this object.
    """
    hkap_packages: Dict[int, Any]   # {year: YearKnowledgePackage}
    dna_records:   List[Any]        # [CrossYearDNARecord]
    edge_records:  List[Any]        # [CrossYearEdgeRecord]
    config:        Any              # KDEConfig

    # ── convenience properties ────────────────────────────────────────────

    @property
    def years(self) -> List[int]:
        return sorted(self.hkap_packages.keys())

    @property
    def market_profiles(self) -> Dict[int, Any]:
        return {
            yr: pkg.market_profile
            for yr, pkg in self.hkap_packages.items()
            if pkg.market_profile is not None
        }

    @property
    def dna_snapshots(self) -> Dict[int, Any]:
        return {
            yr: pkg.dna_snapshot
            for yr, pkg in self.hkap_packages.items()
            if pkg.dna_snapshot is not None
        }

    @property
    def edge_snapshots(self) -> Dict[int, Any]:
        return {
            yr: pkg.edge_snapshot
            for yr, pkg in self.hkap_packages.items()
            if pkg.edge_snapshot is not None
        }

    @property
    def n_years(self) -> int:
        return len(self.hkap_packages)

    @property
    def all_regimes(self) -> List[str]:
        seen: set = set()
        for mp in self.market_profiles.values():
            seen.update(mp.regime_distribution.keys())
        return sorted(seen)


# ── abstract base scheme ──────────────────────────────────────────────────────

class BaseDiscoveryScheme(ABC):
    """
    Abstract base for all KDE discovery schemes.

    Subclass and implement:
        SCHEME_ID          = "S0XX"
        SCHEME_NAME        = "Human Readable Name"
        SCIENTIFIC_QUESTION = "What scientific question does this scheme ask?"

        def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]: ...
    """

    SCHEME_ID:           str = ""
    SCHEME_NAME:         str = ""
    SCIENTIFIC_QUESTION: str = ""

    # ── public interface ──────────────────────────────────────────────────

    def run(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        """Execute scheme safely; logs and returns [] on error."""
        try:
            candidates = self.discover(ctx)
            # filter below min_raw_score
            threshold = getattr(ctx.config, "min_raw_score", 0.40)
            filtered = [c for c in candidates if c.raw_score >= threshold]
            log.debug(
                "[KDE][%s] %d candidates (filtered from %d)",
                self.SCHEME_ID, len(filtered), len(candidates),
            )
            return filtered
        except Exception as exc:
            log.warning("[KDE][%s] discover() failed: %s", self.SCHEME_ID, exc)
            return []

    @abstractmethod
    def discover(self, ctx: DiscoveryContext) -> List[DiscoveryCandidate]:
        """Subclasses implement the scientific analysis here."""

    # ── helpers for subclasses ────────────────────────────────────────────

    def _make_evidence(
        self,
        evidence_type:       str,
        description:         str,
        data_points:         int,
        years_observed:      List[int],
        regimes_observed:    List[str],
        statistical_support: Dict[str, float],
        raw_values:          Dict[str, Any],
    ) -> DiscoveryEvidence:
        return DiscoveryEvidence(
            evidence_type       = evidence_type,
            description         = description,
            data_points         = data_points,
            years_observed      = list(years_observed),
            regimes_observed    = list(regimes_observed),
            statistical_support = statistical_support,
            raw_values          = raw_values,
        )

    def _candidate(
        self,
        question:          str,
        answer:            str,
        evidence:          List[DiscoveryEvidence],
        raw_score:         float,
        years_observed:    List[int],
        regimes_observed:  List[str],
        suggested_followup: List[str],
        novelty_hint:      float = 0.5,
        impact_hint:       float = 0.3,
        feature_names:     List[str] = None,
        dna_ids:           List[str] = None,
        extra_meta:        Dict[str, Any] = None,
    ) -> DiscoveryCandidate:
        meta: Dict[str, Any] = {
            "novelty_hint":   novelty_hint,
            "impact_hint":    impact_hint,
            "feature_names":  feature_names or [],
            "dna_ids":        dna_ids or [],
        }
        if extra_meta:
            meta.update(extra_meta)
        return DiscoveryCandidate(
            scheme_id          = self.SCHEME_ID,
            question           = question,
            answer             = answer,
            evidence           = evidence,
            raw_score          = min(1.0, max(0.0, raw_score)),
            years_observed     = list(years_observed),
            regimes_observed   = list(regimes_observed),
            suggested_followup = list(suggested_followup),
            metadata           = meta,
        )
