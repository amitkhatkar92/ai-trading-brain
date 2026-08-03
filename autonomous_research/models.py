"""
models.py — Normalized data models for the ARS KnowledgeProvider.

All models are immutable read-only records.
None of these classes write, modify, or delete anything.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ─── enumerations ─────────────────────────────────────────────────────────────

class FindingClassification(str, Enum):
    WINNER_DNA        = "WINNER_DNA"
    LOSER_DNA         = "LOSER_DNA"
    FEATURE_IMPORTANCE = "FEATURE_IMPORTANCE"
    CLUSTER_PATTERN   = "CLUSTER_PATTERN"
    REGIME_PATTERN    = "REGIME_PATTERN"
    VALIDATION_RESULT = "VALIDATION_RESULT"
    EDGE_RECORD       = "EDGE_RECORD"
    UNKNOWN           = "UNKNOWN"


class EdgeStatus(str, Enum):
    ACTIVE    = "ACTIVE"
    DECAYING  = "DECAYING"
    CANDIDATE = "CANDIDATE"
    INACTIVE  = "INACTIVE"
    UNKNOWN   = "UNKNOWN"


class LoadSeverity(str, Enum):
    INFO    = "INFO"
    WARNING = "WARNING"
    ERROR   = "ERROR"


# ─── load diagnostics ─────────────────────────────────────────────────────────

@dataclass
class LoadWarning:
    severity:  LoadSeverity
    store:     str
    message:   str
    field:     Optional[str] = None


# ─── core research models ──────────────────────────────────────────────────────

@dataclass
class Evidence:
    metric:  str
    value:   Any
    context: Optional[str] = None


@dataclass
class Finding:
    finding_id:     str
    study_id:       str
    classification: FindingClassification
    description:    str
    metric:         str
    value:          Any
    confidence:     Optional[float]         = None
    lift:           Optional[float]         = None
    regime:         Optional[str]           = None
    evidence:       List[Evidence]          = field(default_factory=list)
    raw:            Optional[Dict[str, Any]] = None


@dataclass
class ResearchStudy:
    study_id:         str
    title:            str
    executed_at:      Optional[datetime]
    n_observations:   Optional[int]
    date_range_start: Optional[str]
    date_range_end:   Optional[str]
    findings:         List[Finding]          = field(default_factory=list)
    source_file:      Optional[str]          = None
    raw:              Optional[Dict[str, Any]] = None


# ─── edge and strategy models ─────────────────────────────────────────────────

@dataclass
class EdgeRecord:
    edge_id:         str
    name:            str
    status:          EdgeStatus
    category:        Optional[str]
    direction:       Optional[str]
    precision:       Optional[float]
    support:         Optional[int]
    sharpe_ratio:    Optional[float]
    oos_win_rate:    Optional[float]
    avg_return_r:    Optional[float]
    composite_score: Optional[float]
    expectancy_r:    Optional[float]
    wf_consistency:  Optional[float]
    live_trades:     int                    = 0
    live_wins:       int                    = 0
    created_at:      Optional[datetime]     = None
    last_tested:     Optional[datetime]     = None
    description:     Optional[str]          = None
    raw:             Optional[Dict[str, Any]] = None


@dataclass
class StrategyRecord:
    strategy_id:       str
    name:              str
    base_strategy:     Optional[str]
    approved:          bool
    win_rate:          Optional[float]
    total_trades:      Optional[int]
    wf_consistency:    Optional[float]
    overfitting_ratio: Optional[float]
    cross_market_rate: Optional[float]
    enabled:           Optional[bool]        = None
    approved_at:       Optional[str]         = None
    raw:               Optional[Dict[str, Any]] = None


# ─── certification model ───────────────────────────────────────────────────────

@dataclass
class Certification:
    cert_id:            str
    source_file:        str
    certified_at:       Optional[datetime]
    certification_type: str
    passed:             bool
    sections_run:       Optional[int]        = None
    activation_blocked: Optional[bool]       = None
    summary:            Optional[Dict[str, Any]] = None
    raw:                Optional[Dict[str, Any]] = None


# ─── feature and regime models ────────────────────────────────────────────────

@dataclass
class FeatureRecord:
    symbol:         str
    ts:             Optional[str]
    regime:         Optional[str]
    sector:         Optional[str]
    forward_return: Optional[float]
    features:       Dict[str, Any]  = field(default_factory=dict)
    source:         Optional[str]   = None


@dataclass
class RegimeProbabilityRecord:
    ts:             Optional[str]
    dominant_regime: Optional[str]
    confidence:     Optional[float]
    trend_prob:     Optional[float]
    range_prob:     Optional[float]
    volatile_prob:  Optional[float]
    bear_prob:      Optional[float]
    indicators:     Optional[Dict[str, Any]] = None


# ─── replay model ─────────────────────────────────────────────────────────────

@dataclass
class ReplaySummary:
    generated_at:     Optional[str]
    target_days:      Optional[int]
    days_replayed:    Optional[int]
    date_range:       Optional[Dict[str, Any]]
    run_duration_sec: Optional[float]
    metrics:          Optional[Dict[str, Any]]
    health:           Optional[Dict[str, Any]]
    raw:              Optional[Dict[str, Any]] = None


# ─── metrics and stores ───────────────────────────────────────────────────────

@dataclass
class KnowledgeMetric:
    metric_id: str
    source:    str     # which store this came from
    category:  str     # EDGE | STRATEGY | REGIME | STUDY | REPLAY
    name:      str
    value:     Any
    units:     Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class KnowledgeStore:
    store_id:       str
    store_type:     str    # STUDY|EDGE_DB|STRATEGY_DB|FEATURE_DB|REPLAY|CERTIFICATION|REGIME|UNIVERSE
    file_path:      str
    loaded:         bool
    record_count:   Optional[int]
    last_modified:  Optional[str]
    schema_version: Optional[str]
    warnings:       List[LoadWarning] = field(default_factory=list)


@dataclass
class KnowledgeSnapshot:
    generated_at:        datetime
    stores:              List[KnowledgeStore]
    studies:             List[ResearchStudy]
    edges:               List[EdgeRecord]
    strategies:          List[StrategyRecord]
    certifications:      List[Certification]
    findings:            List[Finding]
    regime_history_count: int
    feature_db_count:    int
    warnings:            List[LoadWarning]
