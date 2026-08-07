"""
knowledge_provider.py — Unified read-only knowledge access layer for ARS.

ARS Phase 1.1 — KnowledgeProvider.

Responsibilities:
    Load, validate, normalise, and expose all research knowledge.

Explicitly NOT responsible for:
    Writing, modifying, deleting, generating, inferring, or scheduling anything.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    Certification,
    EdgeRecord,
    EdgeStatus,
    Evidence,
    FeatureRecord,
    Finding,
    FindingClassification,
    KnowledgeMetric,
    KnowledgeSnapshot,
    KnowledgeStore,
    LoadSeverity,
    LoadWarning,
    RegimeProbabilityRecord,
    ReplaySummary,
    ResearchStudy,
    StrategyRecord,
)

logger = logging.getLogger(__name__)

# ─── default data directory ───────────────────────────────────────────────────
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class KnowledgeProvider:
    """
    Unified read-only access to all ARS knowledge stores.

    All methods are pure retrievals.  Nothing is written, inferred, or scheduled.

    Usage::

        kp = KnowledgeProvider()
        studies   = kp.list_studies()
        edges     = kp.list_edges()
        findings  = kp.list_findings()
        snapshot  = kp.get_snapshot()
        warnings  = kp.get_warnings()
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._warnings: List[LoadWarning] = []

        # Lazy-loaded caches — populated on first call to each public method
        self._studies:        Optional[List[ResearchStudy]]          = None
        self._edges:          Optional[List[EdgeRecord]]             = None
        self._strategies:     Optional[List[StrategyRecord]]         = None
        self._certifications: Optional[List[Certification]]          = None
        self._regime_history: Optional[List[RegimeProbabilityRecord]] = None
        self._features:       Optional[List[FeatureRecord]]          = None
        self._replay_summary: Optional[ReplaySummary]                = None
        self._stores:         Optional[List[KnowledgeStore]]         = None

    # ═════════════════════════════════════════════════════════════════════════
    # PUBLIC QUERY API — pure retrieval, no side effects
    # ═════════════════════════════════════════════════════════════════════════

    def list_studies(self) -> List[ResearchStudy]:
        """Return all loaded research studies, ordered by execution date."""
        if self._studies is None:
            self._studies = self._load_all_studies()
        return list(self._studies)

    def get_study(self, study_id: str) -> Optional[ResearchStudy]:
        """Return a specific study by ID, or None if not found."""
        for s in self.list_studies():
            if s.study_id == study_id:
                return s
        return None

    def get_latest_study(self) -> Optional[ResearchStudy]:
        """Return the most recently executed study."""
        dated = [s for s in self.list_studies() if s.executed_at is not None]
        return max(dated, key=lambda s: s.executed_at) if dated else None  # type: ignore[arg-type]

    # ─── findings ─────────────────────────────────────────────────────────────

    def list_findings(self) -> List[Finding]:
        """Return all findings extracted from all studies."""
        return [f for s in self.list_studies() for f in s.findings]

    def get_findings_by_classification(
        self, classification: FindingClassification
    ) -> List[Finding]:
        """Return findings matching a specific classification."""
        return [f for f in self.list_findings() if f.classification == classification]

    # ─── edges ────────────────────────────────────────────────────────────────

    def list_edges(
        self,
        status: Optional[EdgeStatus] = None,
        min_composite_score: Optional[float] = None,
    ) -> List[EdgeRecord]:
        """Return discovered edges.  Optionally filter by status or composite score.

        PRR-001 Phase 1 — DECAYING Edge Gate:
        DECAYING and RETIRED edges are permanently excluded from all callers.
        They must never contribute to live signals, confidence calculations,
        or decision inputs regardless of any caller-supplied status filter.
        """
        if self._edges is None:
            self._edges = self._load_edges()
        edges = list(self._edges)
        # ── PRR-001 Phase 1: Block DECAYING and RETIRED edges ─────────────────
        _blocked_statuses = {"DECAYING", "RETIRED"}
        _before = len(edges)
        edges = [
            e for e in edges
            if (getattr(e, "status", None) is None
                or str(getattr(e.status, "value", e.status)).upper() not in _blocked_statuses)
        ]
        _blocked = _before - len(edges)
        if _blocked > 0:
            import logging as _log
            _log.getLogger(__name__).info(
                "[EdgeGate] list_edges: blocked %d DECAYING/RETIRED edges "
                "(remaining=%d). PRR-001 Phase 1 gate active.",
                _blocked, len(edges),
            )
        # ─────────────────────────────────────────────────────────────────────
        if status is not None:
            edges = [e for e in edges if e.status == status]
        if min_composite_score is not None:
            edges = [e for e in edges if (e.composite_score or 0.0) >= min_composite_score]
        return edges

    # ─── strategies ───────────────────────────────────────────────────────────

    def list_strategies(
        self,
        approved_only: bool = False,
        enabled_only: bool = False,
    ) -> List[StrategyRecord]:
        """Return strategy records from evolved_strategies.json and strategy_performance.json."""
        if self._strategies is None:
            self._strategies = self._load_strategies()
        strats = list(self._strategies)
        if approved_only:
            strats = [s for s in strats if s.approved]
        if enabled_only:
            strats = [s for s in strats if s.enabled is not False]
        return strats

    # ─── certifications ───────────────────────────────────────────────────────

    def list_certifications(self) -> List[Certification]:
        """Return all certification and validation records."""
        if self._certifications is None:
            self._certifications = self._load_certifications()
        return list(self._certifications)

    # ─── metrics ──────────────────────────────────────────────────────────────

    def list_knowledge_metrics(
        self, category: Optional[str] = None
    ) -> List[KnowledgeMetric]:
        """Return flat list of measurable metrics from all knowledge stores."""
        metrics: List[KnowledgeMetric] = []

        for e in self.list_edges():
            if e.composite_score is not None:
                metrics.append(KnowledgeMetric(
                    metric_id=f"edge.{e.edge_id}.composite_score",
                    source="discovered_edges.json",
                    category="EDGE",
                    name="composite_score",
                    value=e.composite_score,
                    timestamp=e.last_tested.isoformat() if e.last_tested else None,
                ))
            if e.oos_win_rate is not None:
                metrics.append(KnowledgeMetric(
                    metric_id=f"edge.{e.edge_id}.oos_win_rate",
                    source="discovered_edges.json",
                    category="EDGE",
                    name="oos_win_rate",
                    value=e.oos_win_rate,
                    timestamp=e.last_tested.isoformat() if e.last_tested else None,
                ))

        for s in self.list_strategies():
            if s.win_rate is not None:
                metrics.append(KnowledgeMetric(
                    metric_id=f"strategy.{s.strategy_id}.win_rate",
                    source="strategy_performance.json",
                    category="STRATEGY",
                    name="win_rate",
                    value=s.win_rate,
                ))
            if s.wf_consistency is not None:
                metrics.append(KnowledgeMetric(
                    metric_id=f"strategy.{s.strategy_id}.wf_consistency",
                    source="evolved_strategies.json",
                    category="STRATEGY",
                    name="wf_consistency",
                    value=s.wf_consistency,
                ))

        for f in self.list_findings():
            if isinstance(f.value, (int, float)):
                metrics.append(KnowledgeMetric(
                    metric_id=f"finding.{f.finding_id}",
                    source=f.study_id,
                    category="STUDY",
                    name=f.metric,
                    value=f.value,
                    units=f.classification.value,
                ))

        if category is not None:
            metrics = [m for m in metrics if m.category == category]
        return metrics

    # ─── regime history ────────────────────────────────────────────────────────

    def get_regime_history(
        self,
        limit: Optional[int] = None,
        dominant_regime: Optional[str] = None,
    ) -> List[RegimeProbabilityRecord]:
        """Return regime probability history.  Optionally filter by regime or limit rows."""
        if self._regime_history is None:
            self._regime_history = self._load_regime_history()
        records = list(self._regime_history)
        if dominant_regime:
            records = [r for r in records if r.dominant_regime == dominant_regime]
        if limit:
            records = records[-limit:]
        return records

    # ─── feature database ──────────────────────────────────────────────────────

    def list_features(
        self,
        limit: Optional[int] = 500,
        regime: Optional[str] = None,
    ) -> List[FeatureRecord]:
        """Return feature records from ede_feature_db.json.  Default limit 500 to guard memory."""
        if self._features is None:
            self._features = self._load_features()
        records = list(self._features)
        if regime:
            records = [r for r in records if r.regime == regime]
        if limit is not None:
            records = records[:limit]
        return records

    # ─── replay summary ────────────────────────────────────────────────────────

    def get_replay_summary(self) -> Optional[ReplaySummary]:
        """Return the replay summary record."""
        if self._replay_summary is None:
            self._replay_summary = self._load_replay_summary()
        return self._replay_summary

    # ─── store inventory ───────────────────────────────────────────────────────

    def list_stores(self) -> List[KnowledgeStore]:
        """Return metadata about all known knowledge stores (file exists, size, type)."""
        if self._stores is None:
            self._stores = self._build_store_inventory()
        return list(self._stores)

    # ─── search ────────────────────────────────────────────────────────────────

    def search(self, keyword: str) -> Dict[str, List[Any]]:
        """
        Case-insensitive keyword search across studies, edges, strategies, findings.

        Returns dict with keys: studies, edges, strategies, findings.
        No inference — pure text match on names and descriptions.
        """
        kw = keyword.lower()
        return {
            "studies": [
                s for s in self.list_studies()
                if kw in s.title.lower() or kw in s.study_id.lower()
            ],
            "edges": [
                e for e in self.list_edges()
                if kw in e.name.lower() or kw in (e.description or "").lower()
            ],
            "strategies": [
                s for s in self.list_strategies()
                if kw in s.name.lower() or kw in (s.base_strategy or "").lower()
            ],
            "findings": [
                f for f in self.list_findings()
                if kw in f.description.lower() or kw in f.metric.lower()
            ],
        }

    # ─── diagnostics ──────────────────────────────────────────────────────────

    def get_warnings(self) -> List[LoadWarning]:
        """Return all load warnings accumulated during the session."""
        return list(self._warnings)

    def get_snapshot(self) -> KnowledgeSnapshot:
        """Return a complete point-in-time snapshot of all loaded knowledge."""
        return KnowledgeSnapshot(
            generated_at=datetime.now(),
            stores=self.list_stores(),
            studies=self.list_studies(),
            edges=self.list_edges(),
            strategies=self.list_strategies(),
            certifications=self.list_certifications(),
            findings=self.list_findings(),
            regime_history_count=len(self.get_regime_history()),
            feature_db_count=len(self.list_features(limit=None)),
            warnings=self.get_warnings(),
        )

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNAL LOADERS — private, read-only, no side effects
    # ═════════════════════════════════════════════════════════════════════════

    def _warn(
        self,
        severity: LoadSeverity,
        store: str,
        message: str,
        field: Optional[str] = None,
    ) -> None:
        w = LoadWarning(severity=severity, store=store, message=message, field=field)
        self._warnings.append(w)
        log = logger.error if severity == LoadSeverity.ERROR else logger.warning
        log("[KnowledgeProvider] %s | %s", store, message)

    def _safe_load_json(self, path: Path, store_id: str) -> Optional[Any]:
        """Load JSON file. Returns None and records a warning on any failure."""
        if not path.exists():
            self._warn(LoadSeverity.WARNING, store_id, f"File not found: {path}")
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self._warn(LoadSeverity.ERROR, store_id, f"JSON decode error: {exc}")
            return None
        except OSError as exc:
            self._warn(LoadSeverity.ERROR, store_id, f"Cannot read file: {exc}")
            return None

    def _safe_parse_dt(self, value: Optional[str]) -> Optional[datetime]:
        """Parse datetime string, trying multiple formats.  Returns None on failure."""
        if not value:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(value[:26], fmt[:len(value)])
                return dt
            except (ValueError, TypeError):
                continue
        # Last resort: strip timezone offset and retry
        try:
            return datetime.fromisoformat(value[:19])
        except (ValueError, TypeError):
            return None

    # ─── study loaders ────────────────────────────────────────────────────────

    def _load_all_studies(self) -> List[ResearchStudy]:
        study_files: Dict[str, Path] = {
            "study002":  self._data_dir / "study002_results.json",
            "study002a": self._data_dir / "study002a_results.json",
            "re001a":    self._data_dir / "re001a_results.json",
        }
        # Auto-discover any future ars_study_*.json files
        for f in sorted(self._data_dir.glob("ars_study_*.json")):
            study_files[f.stem] = f

        studies: List[ResearchStudy] = []
        for study_id, path in study_files.items():
            raw = self._safe_load_json(path, study_id)
            if raw is None:
                continue
            study = self._normalize_study(study_id, raw, str(path))
            if study is not None:
                studies.append(study)

        # Sort by execution date, oldest first
        studies.sort(key=lambda s: s.executed_at or datetime.min)
        return studies

    def _normalize_study(
        self, study_id: str, raw: Any, source_file: str
    ) -> Optional[ResearchStudy]:
        if not isinstance(raw, dict):
            self._warn(LoadSeverity.WARNING, study_id, "Top-level JSON is not an object")
            return None

        title = (
            raw.get("study")
            or raw.get("study_id")
            or raw.get("title")
            or study_id
        )
        executed_at = self._safe_parse_dt(raw.get("executed_at"))

        # n_observations: check multiple locations
        n_obs = raw.get("n_observations")
        if n_obs is None:
            stage0 = raw.get("stage0_data") or {}
            n_obs = stage0.get("n_total") or stage0.get("n_observations") if isinstance(stage0, dict) else None
        if n_obs is None:
            final = raw.get("final") or {}
            n_obs = final.get("feat_labeled") if isinstance(final, dict) else None

        # date_range
        dr = raw.get("date_range") or {}
        dr_start = dr.get("start") if isinstance(dr, dict) else None
        dr_end   = dr.get("end")   if isinstance(dr, dict) else None

        findings = self._extract_findings(study_id, raw)

        return ResearchStudy(
            study_id=study_id,
            title=str(title),
            executed_at=executed_at,
            n_observations=int(n_obs) if n_obs is not None else None,
            date_range_start=dr_start,
            date_range_end=dr_end,
            findings=findings,
            source_file=source_file,
            raw=raw,
        )

    def _extract_findings(self, study_id: str, raw: Dict[str, Any]) -> List[Finding]:
        findings: List[Finding] = []

        # ── Winner DNA patterns (Study 2A stage4) ────────────────────────────
        stage4 = raw.get("stage4_winner_dna") or {}
        if isinstance(stage4, dict):
            for i, pattern in enumerate(stage4.get("dna_patterns") or []):
                if not isinstance(pattern, dict):
                    continue
                conds = pattern.get("conditions") or []
                findings.append(Finding(
                    finding_id=f"{study_id}.winner_dna.{i}",
                    study_id=study_id,
                    classification=FindingClassification.WINNER_DNA,
                    description="Winner DNA: " + "; ".join(str(c) for c in conds[:3]),
                    metric="train_confidence",
                    value=pattern.get("train_confidence"),
                    confidence=pattern.get("test_confidence"),
                    lift=pattern.get("test_lift"),
                    evidence=[
                        Evidence("conditions",        conds),
                        Evidence("train_lift",        pattern.get("train_lift")),
                        Evidence("wf_stable",         pattern.get("wf_stable")),
                        Evidence("avg_forward_return", pattern.get("avg_forward_return")),
                        Evidence("train_support",     pattern.get("train_support")),
                        Evidence("test_n_match",      pattern.get("test_n_match")),
                    ],
                    raw=pattern,
                ))

        # ── Loser DNA patterns (Study 2A stage5) ─────────────────────────────
        stage5 = raw.get("stage5_loser_dna") or {}
        if isinstance(stage5, dict):
            # key is loser_dna_patterns in study002a
            for i, pattern in enumerate(stage5.get("loser_dna_patterns") or stage5.get("dna_patterns") or []):
                if not isinstance(pattern, dict):
                    continue
                conds = pattern.get("conditions") or []
                findings.append(Finding(
                    finding_id=f"{study_id}.loser_dna.{i}",
                    study_id=study_id,
                    classification=FindingClassification.LOSER_DNA,
                    description="Loser DNA: " + "; ".join(str(c) for c in conds[:3]),
                    metric="confidence",
                    value=pattern.get("confidence") or pattern.get("train_confidence"),
                    confidence=pattern.get("confidence") or pattern.get("test_confidence"),
                    lift=pattern.get("lift") or pattern.get("test_lift"),
                    evidence=[
                        Evidence("conditions",   conds),
                        Evidence("n_losers",     pattern.get("n_losers")),
                        Evidence("support",      pattern.get("support")),
                    ],
                    raw=pattern,
                ))

        # ── Feature importance ranking (Study 2A stage3) ─────────────────────
        stage3 = raw.get("stage3_ranking") or {}
        if isinstance(stage3, dict):
            # full_ranking contains dicts; top10/top5 are bare name lists
            full_ranking = stage3.get("full_ranking") or []
            for feat_info in full_ranking[:10]:
                if not isinstance(feat_info, dict):
                    continue
                feat_name = feat_info.get("feature") or "unknown"
                score = (
                    feat_info.get("combined_score")
                    or feat_info.get("composite_score")
                    or feat_info.get("rf_importance")
                )
                findings.append(Finding(
                    finding_id=f"{study_id}.feature.{feat_name}",
                    study_id=study_id,
                    classification=FindingClassification.FEATURE_IMPORTANCE,
                    description=f"Top feature: {feat_name}",
                    metric="combined_score",
                    value=score,
                    evidence=[
                        Evidence("rf_importance", feat_info.get("rf_importance")),
                        Evidence("mi_norm",       feat_info.get("mi_norm")),
                        Evidence("cohens_d",      feat_info.get("abs_cohens_d")),
                        Evidence("mwu_pval",      feat_info.get("mwu_pval_w_vs_l")),
                    ],
                    raw=feat_info,
                ))

        # ── Cluster patterns (Study 2A stage6) ───────────────────────────────
        stage6 = raw.get("stage6_clusters") or {}
        if isinstance(stage6, dict):
            for i, cluster in enumerate(stage6.get("clusters") or []):
                if not isinstance(cluster, dict):
                    continue
                label = cluster.get("label") or f"cluster_{i}"
                findings.append(Finding(
                    finding_id=f"{study_id}.cluster.{i}",
                    study_id=study_id,
                    classification=FindingClassification.CLUSTER_PATTERN,
                    description=f"Cluster {i}: {label}",
                    metric="avg_return",
                    value=cluster.get("avg_return") or cluster.get("win_rate") or cluster.get("winner_rate"),
                    evidence=[
                        Evidence("centroid",        cluster.get("centroid_features")),
                        Evidence("size",            cluster.get("size")),
                        Evidence("pct_of_winners",  cluster.get("pct_of_winners")),
                        Evidence("dominant_regime", cluster.get("dominant_regime")),
                        Evidence("best_silhouette", stage6.get("best_silhouette")),
                    ],
                    raw=cluster,
                ))

        # ── Edge discovery results (Study 002 stage5_ede) ────────────────────
        stage5_ede = raw.get("stage5_ede") or {}
        if isinstance(stage5_ede, dict) and stage5_ede.get("new_edges") is not None:
            findings.append(Finding(
                finding_id=f"{study_id}.ede.new_edges",
                study_id=study_id,
                classification=FindingClassification.EDGE_RECORD,
                description=f"EdgeDiscovery: {stage5_ede.get('new_edges')} new edges added",
                metric="new_edges",
                value=stage5_ede.get("new_edges"),
                evidence=[
                    Evidence("edges_after",  stage5_ede.get("edges_after")),
                    Evidence("edges_before", stage5_ede.get("edges_before")),
                    Evidence("new_strats",   stage5_ede.get("new_strats")),
                ],
                raw=stage5_ede,
            ))

        # ── Platform state snapshot (RE001A final) ───────────────────────────
        final = raw.get("final") or {}
        if isinstance(final, dict) and final.get("edges_total") is not None:
            findings.append(Finding(
                finding_id=f"{study_id}.platform_snapshot",
                study_id=study_id,
                classification=FindingClassification.VALIDATION_RESULT,
                description="Platform state snapshot (post-study)",
                metric="edges_total",
                value=final.get("edges_total"),
                evidence=[
                    Evidence("strats_total",  final.get("strats_total")),
                    Evidence("feat_labeled",  final.get("feat_labeled")),
                    Evidence("perf_tracked",  final.get("perf_tracked")),
                    Evidence("edges_by_status", final.get("edges_by_status")),
                ],
                raw=final,
            ))

        return findings

    # ─── edge loader ──────────────────────────────────────────────────────────

    def _load_edges(self) -> List[EdgeRecord]:
        path = self._data_dir / "discovered_edges.json"
        raw = self._safe_load_json(path, "discovered_edges")
        if raw is None:
            return []
        if not isinstance(raw, dict):
            self._warn(LoadSeverity.WARNING, "discovered_edges",
                       f"Expected dict, got {type(raw).__name__}")
            return []

        valid_statuses = set(EdgeStatus._value2member_map_)
        edges: List[EdgeRecord] = []
        for edge_id, rec in raw.items():
            if not isinstance(rec, dict):
                continue
            raw_status = rec.get("status", "UNKNOWN")
            status = EdgeStatus(raw_status) if raw_status in valid_statuses else EdgeStatus.UNKNOWN
            edges.append(EdgeRecord(
                edge_id=edge_id,
                name=rec.get("name", edge_id),
                status=status,
                category=rec.get("category"),
                direction=rec.get("direction"),
                precision=rec.get("precision"),
                support=rec.get("support"),
                sharpe_ratio=rec.get("sharpe_ratio"),
                oos_win_rate=rec.get("oos_win_rate"),
                avg_return_r=rec.get("avg_return_r"),
                composite_score=rec.get("composite_score"),
                expectancy_r=rec.get("expectancy_r"),
                wf_consistency=rec.get("wf_consistency"),
                live_trades=int(rec.get("live_trades") or 0),
                live_wins=int(rec.get("live_wins") or 0),
                created_at=self._safe_parse_dt(rec.get("created_at")),
                last_tested=self._safe_parse_dt(rec.get("last_tested")),
                description=rec.get("description"),
                raw=rec,
            ))
        return edges

    # ─── strategy loaders ─────────────────────────────────────────────────────

    def _load_strategies(self) -> List[StrategyRecord]:
        strategies: List[StrategyRecord] = []

        # evolved_strategies.json — 177+ variant parameter sets
        raw_ev = self._safe_load_json(
            self._data_dir / "evolved_strategies.json", "evolved_strategies"
        )
        if isinstance(raw_ev, dict):
            for variant_name, rec in raw_ev.items():
                if not isinstance(rec, dict):
                    continue
                strategies.append(StrategyRecord(
                    strategy_id=f"evolved.{variant_name}",
                    name=variant_name,
                    base_strategy=rec.get("base_strategy"),
                    approved=bool(rec.get("approved", False)),
                    win_rate=None,
                    total_trades=None,
                    wf_consistency=rec.get("wf_consistency"),
                    overfitting_ratio=rec.get("overfitting_ratio"),
                    cross_market_rate=rec.get("cross_market_rate"),
                    enabled=None,
                    approved_at=rec.get("approved_at"),
                    raw=rec,
                ))

        # strategy_performance.json — live performance tracking
        raw_perf = self._safe_load_json(
            self._data_dir / "strategy_performance.json", "strategy_performance"
        )
        if isinstance(raw_perf, dict):
            for name, rec in raw_perf.items():
                if not isinstance(rec, dict):
                    continue
                total = int(rec.get("total_trades") or 0)
                wins  = int(rec.get("wins") or 0)
                strategies.append(StrategyRecord(
                    strategy_id=f"perf.{name}",
                    name=name,
                    base_strategy=None,
                    approved=True,
                    win_rate=wins / total if total > 0 else None,
                    total_trades=total,
                    wf_consistency=None,
                    overfitting_ratio=None,
                    cross_market_rate=None,
                    enabled=rec.get("enabled"),
                    approved_at=None,
                    raw=rec,
                ))

        return strategies

    # ─── certification loaders ────────────────────────────────────────────────

    def _load_certifications(self) -> List[Certification]:
        certs: List[Certification] = []

        # provider_verification.json
        raw_pv = self._safe_load_json(
            self._data_dir / "provider_verification.json", "provider_verification"
        )
        if isinstance(raw_pv, dict):
            certs.append(Certification(
                cert_id="provider_verification",
                source_file=str(self._data_dir / "provider_verification.json"),
                certified_at=self._safe_parse_dt(raw_pv.get("timestamp")),
                certification_type="PROVIDER_VERIFICATION",
                passed=bool(raw_pv.get("dhan_live") or raw_pv.get("ao_live")),
                summary={
                    "dhan_live": raw_pv.get("dhan_live"),
                    "ao_live":   raw_pv.get("ao_live"),
                },
                raw=raw_pv,
            ))

        # validation_reports/latest_validation.json
        latest_path = self._data_dir / "validation_reports" / "latest_validation.json"
        raw_lv = self._safe_load_json(latest_path, "latest_validation")
        if isinstance(raw_lv, dict):
            certs.append(Certification(
                cert_id="latest_validation",
                source_file=str(latest_path),
                certified_at=self._safe_parse_dt(raw_lv.get("run_timestamp_utc")),
                certification_type="SYSTEM_VALIDATION",
                passed=not bool(raw_lv.get("activation_blocked", True)),
                sections_run=raw_lv.get("sections_run"),
                activation_blocked=raw_lv.get("activation_blocked"),
                summary=raw_lv.get("deployment_snapshot"),
                raw=raw_lv,
            ))

        # validation_reports/*.json — all timestamped validation runs
        vr_dir = self._data_dir / "validation_reports"
        if vr_dir.exists():
            for vr_file in sorted(vr_dir.glob("*.json")):
                if vr_file.name == "latest_validation.json":
                    continue
                raw_vr = self._safe_load_json(vr_file, f"validation_{vr_file.stem}")
                if not isinstance(raw_vr, dict):
                    continue
                certs.append(Certification(
                    cert_id=f"validation_{vr_file.stem}",
                    source_file=str(vr_file),
                    certified_at=self._safe_parse_dt(raw_vr.get("run_timestamp_utc")),
                    certification_type="SYSTEM_VALIDATION",
                    passed=not bool(raw_vr.get("activation_blocked", True)),
                    sections_run=raw_vr.get("sections_run"),
                    activation_blocked=raw_vr.get("activation_blocked"),
                    summary=raw_vr.get("deployment_snapshot"),
                    raw=raw_vr,
                ))

        return certs

    # ─── regime history loader ────────────────────────────────────────────────

    def _load_regime_history(self) -> List[RegimeProbabilityRecord]:
        path = self._data_dir / "regime_probability_history.json"
        raw = self._safe_load_json(path, "regime_probability_history")
        if raw is None:
            return []
        if not isinstance(raw, list):
            self._warn(LoadSeverity.WARNING, "regime_probability_history",
                       f"Expected list, got {type(raw).__name__}")
            return []
        records: List[RegimeProbabilityRecord] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            probs = entry.get("probabilities") or {}
            records.append(RegimeProbabilityRecord(
                ts=entry.get("ts"),
                dominant_regime=probs.get("dominant"),
                confidence=probs.get("confidence"),
                trend_prob=probs.get("trend_prob"),
                range_prob=probs.get("range_prob"),
                volatile_prob=probs.get("volatile_prob"),
                bear_prob=probs.get("bear_prob"),
                indicators=entry.get("indicators"),
            ))
        return records

    # ─── feature database loader ──────────────────────────────────────────────

    def _load_features(self) -> List[FeatureRecord]:
        path = self._data_dir / "ede_feature_db.json"
        raw = self._safe_load_json(path, "ede_feature_db")
        if raw is None:
            return []
        if not isinstance(raw, list):
            self._warn(LoadSeverity.WARNING, "ede_feature_db",
                       f"Expected list, got {type(raw).__name__}")
            return []
        records: List[FeatureRecord] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            records.append(FeatureRecord(
                symbol=entry.get("symbol") or "",
                ts=entry.get("ts"),
                regime=entry.get("regime"),
                sector=entry.get("sector"),
                forward_return=entry.get("forward_return"),
                features=entry.get("features") or {},
                source=entry.get("source"),
            ))
        return records

    # ─── replay summary loader ────────────────────────────────────────────────

    def _load_replay_summary(self) -> Optional[ReplaySummary]:
        path = self._data_dir / "replay_summary.json"
        raw = self._safe_load_json(path, "replay_summary")
        if raw is None or not isinstance(raw, dict):
            return None
        return ReplaySummary(
            generated_at=raw.get("generated_at"),
            target_days=raw.get("target_days"),
            days_replayed=raw.get("days_replayed"),
            date_range=raw.get("date_range"),
            run_duration_sec=raw.get("run_duration_sec"),
            metrics=raw.get("metrics"),
            health=raw.get("health"),
            raw=raw,
        )

    # ─── store inventory ──────────────────────────────────────────────────────

    def _build_store_inventory(self) -> List[KnowledgeStore]:
        # (store_id, relative_path, store_type)
        registry = [
            ("study002",              "study002_results.json",            "STUDY"),
            ("study002a",             "study002a_results.json",           "STUDY"),
            ("re001a",                "re001a_results.json",              "STUDY"),
            ("discovered_edges",      "discovered_edges.json",            "EDGE_DB"),
            ("evolved_strategies",    "evolved_strategies.json",          "STRATEGY_DB"),
            ("strategy_performance",  "strategy_performance.json",        "STRATEGY_DB"),
            ("ede_feature_db",        "ede_feature_db.json",              "FEATURE_DB"),
            ("regime_probability",    "regime_probability_history.json",  "REGIME"),
            ("replay_summary",        "replay_summary.json",              "REPLAY"),
            ("replay_trades",         "replay_trades.json",               "REPLAY"),
            ("provider_verification", "provider_verification.json",       "CERTIFICATION"),
            ("nifty500_universe",     "nifty500_universe.json",           "UNIVERSE"),
            ("improvement_backlog",   "improvement_backlog.json",         "BACKLOG"),
        ]

        stores: List[KnowledgeStore] = []
        for store_id, filename, store_type in registry:
            path = self._data_dir / filename
            exists = path.exists()
            mtime = None
            if exists:
                try:
                    mtime = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                except OSError:
                    pass
            store_warns = [w for w in self._warnings if w.store == store_id]
            stores.append(KnowledgeStore(
                store_id=store_id,
                store_type=store_type,
                file_path=str(path),
                loaded=exists,
                record_count=None,   # populated lazily on list_* calls
                last_modified=mtime,
                schema_version=None,
                warnings=store_warns,
            ))

        # validation_reports/ directory
        vr_dir = self._data_dir / "validation_reports"
        vr_count = len(list(vr_dir.glob("*.json"))) if vr_dir.exists() else 0
        stores.append(KnowledgeStore(
            store_id="validation_reports",
            store_type="CERTIFICATION",
            file_path=str(vr_dir),
            loaded=vr_dir.exists(),
            record_count=vr_count,
            last_modified=None,
            schema_version=None,
        ))

        # replay.db — SQLite, not loaded into memory; metadata only
        replay_db = self._data_dir / "replay.db"
        stores.append(KnowledgeStore(
            store_id="replay_db",
            store_type="REPLAY_DB",
            file_path=str(replay_db),
            loaded=replay_db.exists(),
            record_count=None,
            last_modified=None,
            schema_version=None,
            warnings=[LoadWarning(
                severity=LoadSeverity.INFO,
                store="replay_db",
                message="SQLite database (100MB+) — not loaded into memory; "
                        "query directly via sqlite3 for large operations.",
            )] if replay_db.exists() else [],
        ))

        return stores
