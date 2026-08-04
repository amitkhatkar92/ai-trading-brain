"""
cds_models.py — Typed models for the MLS CDSEngine.

MLS Phase 5A.1.

Pure data.  No business logic.  All fields JSON-serialisable.
CDS = Contextual DNA Score.

CDS is read-only.  It never modifies PMCI, DNA, ARS, strategies, thresholds,
or any persistent store.  It never executes or recommends trades.
It evaluates how well the current market context supports each ConsensusDNA.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── exceptions ───────────────────────────────────────────────────────────────

class CDSError(Exception):
    """Base exception for CDSEngine errors."""


class CDSInputError(CDSError):
    """Invalid input supplied to CDSEngine."""


# ─── enumerations ─────────────────────────────────────────────────────────────

class DNARelevance(str, Enum):
    """Contextual relevance classification for a ConsensusDNA in today's market."""
    HIGHLY_RELEVANT = "HIGHLY_RELEVANT"  # cds >= cds_highly_relevant (0.75)
    RELEVANT        = "RELEVANT"         # cds >= cds_relevant (0.55)
    NEUTRAL         = "NEUTRAL"          # cds >= cds_neutral (0.40)
    WEAK            = "WEAK"             # cds >= cds_weak (0.25)
    IRRELEVANT      = "IRRELEVANT"       # cds >= cds_irrelevant (0.10)
    DEPRECATED      = "DEPRECATED"       # cds < cds_irrelevant (0.10)


class ContextStabilityLabel(str, Enum):
    """How much the market context has shifted relative to the previous snapshot."""
    STABLE           = "STABLE"           # (1-stability) < 0.05
    CHANGING         = "CHANGING"         # (1-stability) < 0.15
    RAPIDLY_CHANGING = "RAPIDLY_CHANGING" # (1-stability) < 0.25
    UNSTABLE         = "UNSTABLE"         # (1-stability) < 0.35
    DRIFTING         = "DRIFTING"         # (1-stability) >= 0.35


# ─── contribution ─────────────────────────────────────────────────────────────

@dataclass
class DNAContextContribution:
    """Score and explanation for one CDS match dimension."""

    name:           str             # dimension identifier (e.g. "regime_match")
    score:          float           # [0, 1] match score for this dimension
    weight:         float           # configured weight
    weighted_score: float           # score × weight — contribution to cds
    supporting:     bool            # True if score >= 0.50 (supporting the DNA)
    explanation:    str             # one-line human-readable description
    evidence:       Dict[str, Any]  # raw source values that drove this score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "score":          round(self.score, 6),
            "weight":         self.weight,
            "weighted_score": round(self.weighted_score, 6),
            "supporting":     self.supporting,
            "explanation":    self.explanation,
            "evidence":       self.evidence,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DNAContextContribution:
        return cls(
            name=d["name"],
            score=float(d["score"]),
            weight=float(d["weight"]),
            weighted_score=float(d["weighted_score"]),
            supporting=bool(d["supporting"]),
            explanation=d["explanation"],
            evidence=dict(d.get("evidence", {})),
        )


# ─── evidence ─────────────────────────────────────────────────────────────────

@dataclass
class DNAContextEvidence:
    """
    Complete raw evidence bundle for one ContextualDNAScore evaluation.

    Enables full reproduction of every CDS result from first principles.
    """

    evaluation_id:              str
    dna_id:                     str
    feature_name:               str
    direction:                  str
    regime_at_eval:             str
    vix_at_eval:                float
    breadth_at_eval:            float
    context_score_at_eval:      float
    context_stability_at_eval:  float
    fii_net_at_eval:            float
    sector_score_at_eval:       float
    global_sentiment_at_eval:   float
    dna_regime_counts:          Dict[str, int]
    dna_evidence_count:         int
    dna_last_seen:              str
    dna_replication_freq:       float
    dna_temporal_stability:     float
    dna_regime_consistency:     float
    dna_sector_consistency:     float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id":             self.evaluation_id,
            "dna_id":                    self.dna_id,
            "feature_name":              self.feature_name,
            "direction":                 self.direction,
            "regime_at_eval":            self.regime_at_eval,
            "vix_at_eval":               self.vix_at_eval,
            "breadth_at_eval":           self.breadth_at_eval,
            "context_score_at_eval":     self.context_score_at_eval,
            "context_stability_at_eval": self.context_stability_at_eval,
            "fii_net_at_eval":           self.fii_net_at_eval,
            "sector_score_at_eval":      self.sector_score_at_eval,
            "global_sentiment_at_eval":  self.global_sentiment_at_eval,
            "dna_regime_counts":         self.dna_regime_counts,
            "dna_evidence_count":        self.dna_evidence_count,
            "dna_last_seen":             self.dna_last_seen,
            "dna_replication_freq":      self.dna_replication_freq,
            "dna_temporal_stability":    self.dna_temporal_stability,
            "dna_regime_consistency":    self.dna_regime_consistency,
            "dna_sector_consistency":    self.dna_sector_consistency,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DNAContextEvidence:
        return cls(
            evaluation_id=d["evaluation_id"],
            dna_id=d["dna_id"],
            feature_name=d["feature_name"],
            direction=d["direction"],
            regime_at_eval=d["regime_at_eval"],
            vix_at_eval=float(d["vix_at_eval"]),
            breadth_at_eval=float(d["breadth_at_eval"]),
            context_score_at_eval=float(d["context_score_at_eval"]),
            context_stability_at_eval=float(d["context_stability_at_eval"]),
            fii_net_at_eval=float(d["fii_net_at_eval"]),
            sector_score_at_eval=float(d["sector_score_at_eval"]),
            global_sentiment_at_eval=float(d["global_sentiment_at_eval"]),
            dna_regime_counts=dict(d["dna_regime_counts"]),
            dna_evidence_count=int(d["dna_evidence_count"]),
            dna_last_seen=d["dna_last_seen"],
            dna_replication_freq=float(d["dna_replication_freq"]),
            dna_temporal_stability=float(d["dna_temporal_stability"]),
            dna_regime_consistency=float(d["dna_regime_consistency"]),
            dna_sector_consistency=float(d["dna_sector_consistency"]),
        )


# ─── historical analogue ──────────────────────────────────────────────────────

@dataclass
class DNAContextSimilarity:
    """One historical market context that resembles today's context."""

    analogue_id:        str         # historical MarketContext.context_id
    analogue_date:      str         # ISO date of the historical context
    similarity_score:   float       # cosine similarity [0, 1]
    context_score:      float       # historical MarketContext.context_score
    regime:             str         # historical regime label
    explanation:        str         # why today resembles this context
    matched_dimensions: List[str]   # component names with |delta| < 0.20

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analogue_id":        self.analogue_id,
            "analogue_date":      self.analogue_date,
            "similarity_score":   round(self.similarity_score, 6),
            "context_score":      round(self.context_score, 6),
            "regime":             self.regime,
            "explanation":        self.explanation,
            "matched_dimensions": self.matched_dimensions,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DNAContextSimilarity:
        return cls(
            analogue_id=d["analogue_id"],
            analogue_date=d["analogue_date"],
            similarity_score=float(d["similarity_score"]),
            context_score=float(d["context_score"]),
            regime=d["regime"],
            explanation=d["explanation"],
            matched_dimensions=list(d.get("matched_dimensions", [])),
        )


# ─── contextual dna score ─────────────────────────────────────────────────────

@dataclass
class ContextualDNAScore:
    """
    CDS evaluation result for one ConsensusDNA in today's market context.

    Produced by CDSEngine.evaluate_dna().  Read-only after construction.
    Reproducible: same (dna_id, evaluation_date) → same evaluation_id.
    """

    evaluation_id:              str                          # "CDS-{sha256[:8]}"
    dna_id:                     str                          # ConsensusDNA.consensus_id
    feature_name:               str
    direction:                  str
    evaluation_date:            str                          # ISO date
    cds:                        float                        # [0, 1] overall CDS
    relevance:                  DNARelevance
    contributions:              List[DNAContextContribution] # always 10
    supporting_dimensions:      List[str]    # contribution names where score >= 0.50
    conflicting_dimensions:     List[str]    # contribution names where score <  0.50
    context_stability_label:    ContextStabilityLabel
    historical_similarity_score: float                       # [0, 1]
    historical_matches:         List[DNAContextSimilarity]
    evidence:                   DNAContextEvidence
    explanation:                str
    confidence:                 float                        # [0, 1]
    library_id:                 str
    evaluated_at:               str                          # ISO datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id":              self.evaluation_id,
            "dna_id":                     self.dna_id,
            "feature_name":               self.feature_name,
            "direction":                  self.direction,
            "evaluation_date":            self.evaluation_date,
            "cds":                        round(self.cds, 6),
            "relevance":                  self.relevance.value,
            "contributions":              [c.to_dict() for c in self.contributions],
            "supporting_dimensions":      self.supporting_dimensions,
            "conflicting_dimensions":     self.conflicting_dimensions,
            "context_stability_label":    self.context_stability_label.value,
            "historical_similarity_score": round(self.historical_similarity_score, 6),
            "historical_matches":         [m.to_dict() for m in self.historical_matches],
            "evidence":                   self.evidence.to_dict(),
            "explanation":                self.explanation,
            "confidence":                 round(self.confidence, 6),
            "library_id":                 self.library_id,
            "evaluated_at":               self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ContextualDNAScore:
        return cls(
            evaluation_id=d["evaluation_id"],
            dna_id=d["dna_id"],
            feature_name=d["feature_name"],
            direction=d["direction"],
            evaluation_date=d["evaluation_date"],
            cds=float(d["cds"]),
            relevance=DNARelevance(d["relevance"]),
            contributions=[DNAContextContribution.from_dict(c) for c in d["contributions"]],
            supporting_dimensions=list(d["supporting_dimensions"]),
            conflicting_dimensions=list(d["conflicting_dimensions"]),
            context_stability_label=ContextStabilityLabel(d["context_stability_label"]),
            historical_similarity_score=float(d["historical_similarity_score"]),
            historical_matches=[DNAContextSimilarity.from_dict(m) for m in d["historical_matches"]],
            evidence=DNAContextEvidence.from_dict(d["evidence"]),
            explanation=d["explanation"],
            confidence=float(d["confidence"]),
            library_id=d["library_id"],
            evaluated_at=d["evaluated_at"],
        )


# ─── dna context profile ──────────────────────────────────────────────────────

@dataclass
class DNAContextProfile:
    """Rich multi-dimensional context profile for one ConsensusDNA."""

    dna_id:                    str
    feature_name:              str
    direction:                 str
    evaluation_date:           str
    latest_cds:                float
    latest_relevance:          DNARelevance
    regime_affinity:           Dict[str, float]   # regime → fraction of DNA history
    strong_regimes:            List[str]           # regimes where fraction >= 0.50
    weak_regimes:              List[str]           # regimes where fraction <  0.20
    avg_historical_similarity: float
    supporting_count:          int
    conflicting_count:         int
    top_contribution:          str                 # name of highest weighted_score contribution
    context_stability:         ContextStabilityLabel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dna_id":                    self.dna_id,
            "feature_name":              self.feature_name,
            "direction":                 self.direction,
            "evaluation_date":           self.evaluation_date,
            "latest_cds":                round(self.latest_cds, 6),
            "latest_relevance":          self.latest_relevance.value,
            "regime_affinity":           self.regime_affinity,
            "strong_regimes":            self.strong_regimes,
            "weak_regimes":              self.weak_regimes,
            "avg_historical_similarity": round(self.avg_historical_similarity, 6),
            "supporting_count":          self.supporting_count,
            "conflicting_count":         self.conflicting_count,
            "top_contribution":          self.top_contribution,
            "context_stability":         self.context_stability.value,
        }

    @classmethod
    def from_score(cls, score: ContextualDNAScore) -> DNAContextProfile:
        """Derive a DNAContextProfile from a single ContextualDNAScore."""
        regime_affinity: Dict[str, float] = {}
        strong_regimes: List[str] = []
        weak_regimes: List[str] = []

        r_contrib = next((c for c in score.contributions if c.name == "regime_match"), None)
        if r_contrib:
            counts = r_contrib.evidence.get("dna_regime_counts", {})
            total = sum(counts.values())
            if total > 0:
                for reg, cnt in counts.items():
                    frac = round(cnt / total, 3)
                    regime_affinity[reg] = frac
                    if frac >= 0.50:
                        strong_regimes.append(reg)
                    elif frac < 0.20:
                        weak_regimes.append(reg)

        top_contrib = (
            max(score.contributions, key=lambda c: c.weighted_score).name
            if score.contributions else ""
        )

        return cls(
            dna_id=score.dna_id,
            feature_name=score.feature_name,
            direction=score.direction,
            evaluation_date=score.evaluation_date,
            latest_cds=score.cds,
            latest_relevance=score.relevance,
            regime_affinity=regime_affinity,
            strong_regimes=strong_regimes,
            weak_regimes=weak_regimes,
            avg_historical_similarity=score.historical_similarity_score,
            supporting_count=len(score.supporting_dimensions),
            conflicting_count=len(score.conflicting_dimensions),
            top_contribution=top_contrib,
            context_stability=score.context_stability_label,
        )


# ─── dna context history ──────────────────────────────────────────────────────

@dataclass
class DNAContextHistory:
    """
    Trend analysis over multiple CDS evaluations for one ConsensusDNA.

    Built from a list of past ContextualDNAScore objects via from_scores().
    """

    dna_id:          str
    feature_name:    str
    entries:         List[Dict[str, Any]]  # {date, cds, relevance, regime, context_score}
    cds_trend:       str      # "IMPROVING" | "DECLINING" | "STABLE"
    cds_trend_slope: float    # signed slope per observation period
    avg_cds:         float
    latest_cds:      float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dna_id":          self.dna_id,
            "feature_name":    self.feature_name,
            "entries":         self.entries,
            "cds_trend":       self.cds_trend,
            "cds_trend_slope": round(self.cds_trend_slope, 6),
            "avg_cds":         round(self.avg_cds, 6),
            "latest_cds":      round(self.latest_cds, 6),
        }

    @classmethod
    def from_scores(cls, scores: List[ContextualDNAScore]) -> DNAContextHistory:
        """Build history from a list of CDS evaluations for the same DNA."""
        if not scores:
            return cls(
                dna_id="", feature_name="", entries=[],
                cds_trend="STABLE", cds_trend_slope=0.0, avg_cds=0.0, latest_cds=0.0,
            )

        sorted_scores = sorted(scores, key=lambda s: s.evaluation_date)
        entries = [
            {
                "date":          s.evaluation_date,
                "cds":           s.cds,
                "relevance":     s.relevance.value,
                "regime":        s.evidence.regime_at_eval,
                "context_score": s.evidence.context_score_at_eval,
            }
            for s in sorted_scores
        ]

        vals = [s.cds for s in sorted_scores]
        avg_cds = sum(vals) / len(vals)

        if len(vals) >= 2:
            slope = vals[-1] - vals[0]
        else:
            slope = 0.0

        if slope > 0.05:
            trend = "IMPROVING"
        elif slope < -0.05:
            trend = "DECLINING"
        else:
            trend = "STABLE"

        return cls(
            dna_id=sorted_scores[0].dna_id,
            feature_name=sorted_scores[0].feature_name,
            entries=entries,
            cds_trend=trend,
            cds_trend_slope=round(slope, 4),
            avg_cds=round(avg_cds, 4),
            latest_cds=round(vals[-1], 4),
        )


# ─── library result ───────────────────────────────────────────────────────────

@dataclass
class CDSLibraryResult:
    """Complete CDS evaluation of a full ConsensusLibrary."""

    library_id:        str
    evaluation_date:   str
    scores:            List[ContextualDNAScore]
    statistics:        "DNAContextStatistics"
    context_id:        str                     # MarketContext.context_id used
    context_stability: ContextStabilityLabel
    evaluated_at:      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "library_id":        self.library_id,
            "evaluation_date":   self.evaluation_date,
            "scores":            [s.to_dict() for s in self.scores],
            "statistics":        self.statistics.to_dict(),
            "context_id":        self.context_id,
            "context_stability": self.context_stability.value,
            "evaluated_at":      self.evaluated_at,
        }


# ─── statistics ───────────────────────────────────────────────────────────────

@dataclass
class DNAContextStatistics:
    """Aggregate statistics for a batch CDS evaluation of a ConsensusLibrary."""

    evaluation_date:            str
    library_id:                 str
    total_dna:                  int
    highly_relevant_count:      int
    relevant_count:             int
    neutral_count:              int
    weak_count:                 int
    irrelevant_count:           int
    deprecated_count:           int
    avg_cds:                    float
    top_dna_id:                 Optional[str]
    top_dna_feature:            Optional[str]
    top_cds:                    float
    least_dna_id:               Optional[str]
    least_dna_feature:          Optional[str]
    least_cds:                  float
    avg_supporting_dimensions:  float    # avg number of supporting dims per DNA
    avg_historical_similarity:  float
    dominant_context_stability: str      # ContextStabilityLabel.value of the batch

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_date":            self.evaluation_date,
            "library_id":                 self.library_id,
            "total_dna":                  self.total_dna,
            "highly_relevant_count":      self.highly_relevant_count,
            "relevant_count":             self.relevant_count,
            "neutral_count":              self.neutral_count,
            "weak_count":                 self.weak_count,
            "irrelevant_count":           self.irrelevant_count,
            "deprecated_count":           self.deprecated_count,
            "avg_cds":                    round(self.avg_cds, 6),
            "top_dna_id":                 self.top_dna_id,
            "top_dna_feature":            self.top_dna_feature,
            "top_cds":                    round(self.top_cds, 6),
            "least_dna_id":               self.least_dna_id,
            "least_dna_feature":          self.least_dna_feature,
            "least_cds":                  round(self.least_cds, 6),
            "avg_supporting_dimensions":  round(self.avg_supporting_dimensions, 3),
            "avg_historical_similarity":  round(self.avg_historical_similarity, 6),
            "dominant_context_stability": self.dominant_context_stability,
        }

    @classmethod
    def empty(cls, evaluation_date: str = "", library_id: str = "") -> DNAContextStatistics:
        return cls(
            evaluation_date=evaluation_date,
            library_id=library_id,
            total_dna=0,
            highly_relevant_count=0,
            relevant_count=0,
            neutral_count=0,
            weak_count=0,
            irrelevant_count=0,
            deprecated_count=0,
            avg_cds=0.0,
            top_dna_id=None,
            top_dna_feature=None,
            top_cds=0.0,
            least_dna_id=None,
            least_dna_feature=None,
            least_cds=0.0,
            avg_supporting_dimensions=0.0,
            avg_historical_similarity=0.0,
            dominant_context_stability=ContextStabilityLabel.STABLE.value,
        )
