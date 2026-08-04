"""
dre_engine.py — DNA Reinforcement Engine.

O-002: DNA Reinforcement Engine (DRE).

DRE is the live-learning reinforcement component of IIOS.
It reads closed trade outcomes, identifies which institutional DNA features
contributed to the trade decision via PMCI, and updates their confidence
and temporal stability using verified trading evidence.

DRE NEVER:
    Creates new DNA.
    Invokes discovery, consensus, or classification engines.
    Changes PMCI logic, CDS logic, strategies, or trading rules.
    Modifies DNA lifecycle (INSTITUTIONAL → RETIRED etc.).

DRE ONLY:
    Reads existing InstitutionalDNA from IDR.
    Updates confidence and temporal_stability via idr.update().
    Records a full audit trail in data/mls/dre/history.json.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .dre_config import DREConfig
from .dre_models import (
    DNAConfidenceUpdate,
    DNAReinforcement,
    DNAReinforcementHistory,
    DREError,
    DREInputError,
    DREProcessingError,
    OutcomeQuality,
    ReinforcementEvidence,
    ReinforcementStatistics,
    ReinforcementType,
)

log = logging.getLogger(__name__)

_DEFAULT_DRE_DIR = Path(__file__).resolve().parent.parent / "data" / "mls" / "dre"


# ─── private helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Attribute-or-dict accessor — works for dataclasses, NamedTuples, and dicts."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _classify_outcome(r_multiple: float, won: bool, cfg: DREConfig) -> OutcomeQuality:
    if won:
        if r_multiple >= cfg.r_excellent_threshold:
            return OutcomeQuality.EXCELLENT
        if r_multiple >= cfg.r_good_threshold:
            return OutcomeQuality.GOOD
        return OutcomeQuality.FAIR
    else:
        if r_multiple >= cfg.r_fair_min:
            return OutcomeQuality.FAIR
        if r_multiple >= cfg.r_poor_min:
            return OutcomeQuality.POOR
        return OutcomeQuality.BAD


def _determine_type(
    is_matched: bool,
    won: bool,
    r_multiple: float,
    cfg: DREConfig,
) -> ReinforcementType:
    """Map (DNA role, outcome) → ReinforcementType."""
    if abs(r_multiple) < cfg.min_r_multiple_magnitude:
        return ReinforcementType.NEUTRAL
    if is_matched:
        return ReinforcementType.POSITIVE if won else ReinforcementType.NEGATIVE
    # conflicting DNA
    return ReinforcementType.CONTRADICTORY if won else ReinforcementType.NEUTRAL


def _compute_confidence_delta(
    rtype: ReinforcementType,
    r_multiple: float,
    alignment: float,
    cfg: DREConfig,
) -> float:
    """
    Compute signed, capped confidence delta for one reinforcement event.

    Formula:
        raw = learning_rate × clamp(|R|, scale_min, scale_max) × alignment
        delta = raw × direction_sign
        result = clamp(delta, -max_single_trade_delta, +max_single_trade_delta)
    """
    if rtype in (ReinforcementType.NEUTRAL, ReinforcementType.INSUFFICIENT_EVIDENCE):
        return 0.0

    r_factor = min(max(abs(r_multiple), cfg.r_multiple_scale_min), cfg.r_multiple_scale_max)
    raw = cfg.learning_rate * r_factor * alignment

    if rtype == ReinforcementType.POSITIVE:
        delta = +raw
    elif rtype == ReinforcementType.NEGATIVE:
        delta = -raw
    elif rtype == ReinforcementType.CONTRADICTORY:
        delta = -raw * cfg.contradictory_weight
    else:
        delta = 0.0

    return min(max(delta, -cfg.max_single_trade_delta), cfg.max_single_trade_delta)


def _compute_stability_delta(rtype: ReinforcementType, cfg: DREConfig) -> float:
    if rtype == ReinforcementType.POSITIVE:
        return cfg.stability_win_delta
    if rtype in (ReinforcementType.NEGATIVE, ReinforcementType.CONTRADICTORY):
        return cfg.stability_loss_delta
    return cfg.stability_neutral_delta


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(value, lo), hi)


def _build_reason(
    rtype: ReinforcementType,
    feature: str,
    direction: str,
    alignment: float,
    r_multiple: float,
    quality: OutcomeQuality,
    conf_delta: float,
) -> str:
    return (
        f"{rtype.value}: '{feature}' ({direction}) "
        f"alignment={alignment:.3f} R={r_multiple:+.2f} "
        f"quality={quality.value} "
        f"confidence_delta={conf_delta:+.5f}"
    )


def _reinforcement_id(dna_id: str, trade_id: str, ts: str) -> str:
    raw = f"{dna_id}:{trade_id}:{ts}"
    return "DRE-" + hashlib.sha256(raw.encode()).hexdigest()[:12]


# ─── DNAReinforcementEngine ───────────────────────────────────────────────────

class DNAReinforcementEngine:
    """
    DNA Reinforcement Engine — the live-learning reinforcement layer of IIOS.

    Responsibilities:
        Read PMCI evidence from closed trades.
        Identify institutional DNA that contributed to each trade decision.
        Evaluate outcome quality using R-multiple (NOT PnL alone).
        Update DNA confidence and temporal_stability via IDR.update().
        Record every reinforcement with full audit trail.
        Persist history atomically to data/mls/dre/history.json.

    Thread-safe: process_trade() and process_batch() acquire the internal lock.

    Parameters
    ----------
    idr : IDRRepository or compatible mock
        Provides list_active(), get(), and update().  If None, uses the
        default IDRRepository at data/mls/institutional_dna.db.
    config : DREConfig or None
        Operational configuration.  Uses defaults if None.
    data_root : Path or None
        Override for the data directory root.  Used by tests.
    """

    # ── init ──────────────────────────────────────────────────────────────────

    def __init__(
        self,
        idr: Optional[Any] = None,
        config: Optional[DREConfig] = None,
        data_root: Optional[Path] = None,
    ) -> None:
        self._config = config or DREConfig()
        self._lock = threading.Lock()
        self._pending: Set[str] = set()   # trade IDs currently in flight

        root = Path(data_root) if data_root else _DEFAULT_DRE_DIR
        root.mkdir(parents=True, exist_ok=True)
        self._history_path = root / "history.json"

        self._idr = idr or self._default_idr()
        self._history: List[DNAReinforcement] = []
        self._trades_processed: int = 0
        self._idr_writes: int = 0

        self._load_history()
        log.info(
            "[DRE] Initialised — config_fingerprint=%s dry_run=%s history=%d",
            self._config.fingerprint(), self._config.dry_run, len(self._history),
        )

    @staticmethod
    def _default_idr() -> Any:
        from .idr_repository import IDRRepository
        from .mls_config import MLSConfig
        cfg = MLSConfig()
        db_path = _DEFAULT_DRE_DIR.parent / "institutional_dna.db"
        return IDRRepository(db_path=db_path, config=cfg)

    # ── public API ────────────────────────────────────────────────────────────

    def process_trade(
        self,
        trade: Any,
        pmci_result: Any,
        ca_pmci_result: Optional[Any] = None,
        cds_scores: Optional[Dict[str, Any]] = None,
    ) -> List[DNAReinforcement]:
        """
        Process one closed trade and reinforce every DNA that contributed.

        Parameters
        ----------
        trade :
            Closed trade record.  Accepted as OrderRecord, dataclass, or dict.
            Required keys: order_id, symbol, direction, pnl, strategy,
            signal_regime, confidence_score.  Optional: r_multiple,
            placed_at, closed_at, initial_stop_loss.
        pmci_result :
            PMCIResult for the trade symbol at decision time.
            Must expose .pmci_score, .breakdown.matched_dna,
            .breakdown.conflicting_dna.
        ca_pmci_result :
            CAPMCIResult, optional.  Provides ca_pmci score for evidence.
        cds_scores :
            Dict mapping dna_id → ContextualDNAScore, optional.
            Provides per-DNA context scores for evidence enrichment.

        Returns
        -------
        List[DNAReinforcement]
            One record per DNA that was processed (eligible or not).
            Records with type=INSUFFICIENT_EVIDENCE were skipped in IDR.
        """
        if pmci_result is None:
            raise DREInputError("pmci_result is required for process_trade()")

        trade_id = str(_get(trade, "order_id", "") or _get(trade, "trade_id", "unknown"))

        with self._lock:
            if trade_id in self._pending:
                log.warning("[DRE] Trade '%s' already in-flight — skipping.", trade_id)
                return []
            self._pending.add(trade_id)

        try:
            results = self._process_one(trade, trade_id, pmci_result, ca_pmci_result, cds_scores)
        finally:
            with self._lock:
                self._pending.discard(trade_id)

        return results

    def process_batch(
        self,
        items: List[Tuple[Any, Any, Optional[Any], Optional[Dict[str, Any]]]],
    ) -> List[DNAReinforcement]:
        """
        Process a batch of (trade, pmci_result, ca_pmci_result, cds_scores) tuples.

        Safety: each DNA may be reinforced at most max_reinforcements_per_batch
        times per call, preventing a single batch from drifting any DNA.

        Returns a flat list of all DNAReinforcement records produced.
        """
        if not items:
            return []

        all_reinforcements: List[DNAReinforcement] = []
        dna_counts: Dict[str, int] = {}

        for trade, pmci, ca_pmci, cds in items:
            per_trade = self.process_trade(trade, pmci, ca_pmci, cds)
            for r in per_trade:
                dna_counts[r.dna_id] = dna_counts.get(r.dna_id, 0) + 1
                if dna_counts[r.dna_id] > self._config.max_reinforcements_per_batch:
                    log.debug(
                        "[DRE] DNA '%s' hit batch cap (%d) — skipping extra reinforcement.",
                        r.dna_id, self._config.max_reinforcements_per_batch,
                    )
                    continue
                all_reinforcements.append(r)

        return all_reinforcements

    def history(
        self,
        dna_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DNAReinforcement]:
        """
        Return reinforcement history, newest first.

        Parameters
        ----------
        dna_id : str or None
            Filter to a specific DNA id.  None returns all records.
        limit : int
            Maximum records to return.
        """
        with self._lock:
            records = list(reversed(self._history))
        if dna_id:
            records = [r for r in records if r.dna_id == dna_id]
        return records[:limit]

    def statistics(self) -> ReinforcementStatistics:
        """Return aggregate statistics across all recorded reinforcements."""
        with self._lock:
            hist = list(self._history)
            trades = self._trades_processed
            idr_writes = self._idr_writes

        if not hist:
            return ReinforcementStatistics(
                total_reinforcements=0, positive_count=0, negative_count=0,
                neutral_count=0, contradictory_count=0,
                insufficient_evidence_count=0, trades_processed=trades,
                dna_updated=0, dna_skipped=0,
                avg_confidence_delta=0.0, avg_stability_delta=0.0,
                max_confidence_delta=0.0, min_confidence_delta=0.0,
                total_idr_writes=idr_writes,
                first_reinforcement_at=None, last_reinforcement_at=None,
            )

        type_counts = {t.value: 0 for t in ReinforcementType}
        for r in hist:
            type_counts[r.reinforcement_type] = type_counts.get(r.reinforcement_type, 0) + 1

        deltas = [r.confidence_delta for r in hist]
        stab_deltas = [r.stability_delta for r in hist]
        updated = sum(1 for r in hist if r.reinforcement_type != ReinforcementType.INSUFFICIENT_EVIDENCE.value)
        skipped = sum(1 for r in hist if r.reinforcement_type == ReinforcementType.INSUFFICIENT_EVIDENCE.value)

        return ReinforcementStatistics(
            total_reinforcements=len(hist),
            positive_count=type_counts.get(ReinforcementType.POSITIVE.value, 0),
            negative_count=type_counts.get(ReinforcementType.NEGATIVE.value, 0),
            neutral_count=type_counts.get(ReinforcementType.NEUTRAL.value, 0),
            contradictory_count=type_counts.get(ReinforcementType.CONTRADICTORY.value, 0),
            insufficient_evidence_count=type_counts.get(ReinforcementType.INSUFFICIENT_EVIDENCE.value, 0),
            trades_processed=trades,
            dna_updated=updated,
            dna_skipped=skipped,
            avg_confidence_delta=sum(deltas) / len(deltas),
            avg_stability_delta=sum(stab_deltas) / len(stab_deltas),
            max_confidence_delta=max(deltas),
            min_confidence_delta=min(deltas),
            total_idr_writes=idr_writes,
            first_reinforcement_at=hist[0].processed_at,
            last_reinforcement_at=hist[-1].processed_at,
        )

    def pending(self) -> List[str]:
        """Return trade IDs currently being processed (thread diagnostic)."""
        with self._lock:
            return list(self._pending)

    # ── private processing ────────────────────────────────────────────────────

    def _process_one(
        self,
        trade: Any,
        trade_id: str,
        pmci_result: Any,
        ca_pmci_result: Optional[Any],
        cds_scores: Optional[Dict[str, Any]],
    ) -> List[DNAReinforcement]:
        """Core processing: produce reinforcements for one trade."""
        # ── extract trade fields ──────────────────────────────────────────
        pnl       = float(_get(trade, "pnl", 0.0) or 0.0)
        r_mult    = float(_get(trade, "r_multiple", 0.0) or 0.0)
        won       = pnl > 0.0
        symbol    = str(_get(trade, "symbol", ""))
        direction = str(_get(trade, "direction", ""))
        strategy  = str(_get(trade, "strategy", "") or _get(trade, "strategy_name", ""))
        regime    = str(_get(trade, "signal_regime", "") or _get(trade, "regime", ""))
        conf_sc   = float(_get(trade, "confidence_score", 0.0) or 0.0)
        placed_at = _get(trade, "placed_at", None)
        closed_at = _get(trade, "closed_at", None)

        holding_h = 0.0
        if placed_at and closed_at:
            try:
                if not isinstance(placed_at, datetime):
                    placed_at = datetime.fromisoformat(str(placed_at))
                if not isinstance(closed_at, datetime):
                    closed_at = datetime.fromisoformat(str(closed_at))
                holding_h = (closed_at - placed_at).total_seconds() / 3600.0
            except Exception:
                pass

        outcome_quality = _classify_outcome(r_mult, won, self._config)

        # ── extract PMCI breakdown ────────────────────────────────────────
        breakdown = getattr(pmci_result, "breakdown", None)
        if breakdown is None:
            log.debug("[DRE] Trade '%s': no PMCI breakdown — returning empty.", trade_id)
            with self._lock:
                self._trades_processed += 1
            return []

        pmci_score   = float(getattr(pmci_result, "pmci_score", 0.0))
        ca_pmci_sc   = float(getattr(ca_pmci_result, "ca_pmci", 0.0)) if ca_pmci_result else 0.0
        cds_map: Dict[str, float] = {}
        if cds_scores:
            for dna_id_key, cds_obj in cds_scores.items():
                cds_map[dna_id_key] = float(getattr(cds_obj, "cds", 0.0))

        # ── build IDR lookup by (feature_name, direction) ─────────────────
        idr_lookup = self._build_idr_lookup()

        # ── process each DNA evidence item ────────────────────────────────
        reinforcements: List[DNAReinforcement] = []

        matched    = list(getattr(breakdown, "matched_dna", []) or [])
        conflicting = list(getattr(breakdown, "conflicting_dna", []) or [])

        evidence_items = [(pev, True) for pev in matched] + [(pev, False) for pev in conflicting]

        for pev, is_matched in evidence_items:
            alignment = float(getattr(pev, "alignment", 0.0))
            if alignment < self._config.min_alignment_threshold:
                continue

            feat = str(getattr(pev, "feature_name", ""))
            dirn = str(getattr(pev, "direction", ""))
            dna  = idr_lookup.get((feat, dirn))

            if dna is None:
                log.debug("[DRE] Trade '%s': no IDR match for (%s, %s).", trade_id, feat, dirn)
                continue

            contrib = float(getattr(pev, "contribution", 0.0))
            cds_val = cds_map.get(dna.id, 0.0)

            ev = ReinforcementEvidence(
                trade_id=trade_id,
                symbol=symbol,
                trade_direction=direction,
                strategy=strategy,
                regime_at_entry=regime,
                pmci_score=pmci_score,
                ca_pmci_score=ca_pmci_sc,
                cds_score=cds_val,
                dna_alignment=alignment,
                dna_contribution=contrib,
                r_multiple=r_mult,
                pnl=pnl,
                holding_period_h=round(holding_h, 3),
                won=won,
                outcome_quality=outcome_quality.value,
                confidence_score=conf_sc,
            )

            rec = self._reinforce_one_dna(
                dna=dna,
                trade_id=trade_id,
                is_matched=is_matched,
                r_multiple=r_mult,
                won=won,
                outcome_quality=outcome_quality,
                evidence=ev,
            )
            reinforcements.append(rec)

        # ── persist ───────────────────────────────────────────────────────
        with self._lock:
            self._trades_processed += 1
            self._history.extend(reinforcements)
            if not self._config.dry_run:
                self._save_history()

        if reinforcements:
            log.debug(
                "[DRE] Trade '%s': %d reinforcement(s) applied.",
                trade_id, len(reinforcements),
            )
        return reinforcements

    def _reinforce_one_dna(
        self,
        dna: Any,
        trade_id: str,
        is_matched: bool,
        r_multiple: float,
        won: bool,
        outcome_quality: OutcomeQuality,
        evidence: ReinforcementEvidence,
    ) -> DNAReinforcement:
        """Apply (or compute for dry-run) one reinforcement to one DNA."""
        ts = _now()
        cfg = self._config

        # ── eligibility check ─────────────────────────────────────────────
        lifecycle = str(getattr(dna, "lifecycle", ""))
        ev_count  = int(getattr(dna, "evidence_count", 0))

        if lifecycle not in cfg.eligible_lifecycles or ev_count < cfg.min_idr_evidence_count:
            return DNAReinforcement(
                reinforcement_id=_reinforcement_id(dna.id, trade_id, ts),
                dna_id=dna.id,
                feature_name=dna.feature_name,
                direction=dna.direction,
                trade_id=trade_id,
                reinforcement_type=ReinforcementType.INSUFFICIENT_EVIDENCE.value,
                evidence=evidence,
                confidence_before=float(getattr(dna, "confidence", 0.0)),
                confidence_after=float(getattr(dna, "confidence", 0.0)),
                confidence_delta=0.0,
                stability_before=float(getattr(dna, "temporal_stability", 0.0)),
                stability_after=float(getattr(dna, "temporal_stability", 0.0)),
                stability_delta=0.0,
                evidence_count_before=ev_count,
                evidence_count_after=ev_count,
                reason=(
                    f"INSUFFICIENT_EVIDENCE: lifecycle={lifecycle} "
                    f"evidence_count={ev_count} "
                    f"(need lifecycle in {cfg.eligible_lifecycles}, "
                    f"evidence_count>={cfg.min_idr_evidence_count})"
                ),
                idr_revision=None,
                processed_at=ts,
            )

        # ── compute deltas ────────────────────────────────────────────────
        rtype        = _determine_type(is_matched, won, r_multiple, cfg)
        conf_delta   = _compute_confidence_delta(rtype, r_multiple, evidence.dna_alignment, cfg)
        stab_delta   = _compute_stability_delta(rtype, cfg)

        conf_before  = float(getattr(dna, "confidence", 0.0))
        stab_before  = float(getattr(dna, "temporal_stability", 0.0))
        conf_after   = _clamp(conf_before + conf_delta, cfg.confidence_min, cfg.confidence_max)
        stab_after   = _clamp(stab_before + stab_delta, cfg.stability_min, cfg.stability_max)

        reason = _build_reason(
            rtype, dna.feature_name, dna.direction,
            evidence.dna_alignment, r_multiple, outcome_quality, conf_delta,
        )

        # ── write to IDR ──────────────────────────────────────────────────
        idr_revision: Optional[int] = None
        if not cfg.dry_run:
            try:
                meta = dict(getattr(dna, "metadata", {}) or {})
                meta["last_dre_reinforcement"] = ts
                meta["dre_reinforcement_count"] = int(meta.get("dre_reinforcement_count", 0)) + 1
                revision = self._idr.update(
                    dna.id,
                    {
                        "confidence":         conf_after,
                        "temporal_stability": stab_after,
                        "evidence_count":     ev_count + 1,
                        "metadata":           meta,
                    },
                    reason=reason,
                    study_id="DRE",
                    operator="dre_engine",
                )
                idr_revision = getattr(revision, "version", None)
                with self._lock:
                    self._idr_writes += 1
            except Exception as exc:
                log.warning(
                    "[DRE] IDR write failed for DNA '%s' (trade '%s'): %s",
                    dna.id, trade_id, exc,
                )

        return DNAReinforcement(
            reinforcement_id=_reinforcement_id(dna.id, trade_id, ts),
            dna_id=dna.id,
            feature_name=dna.feature_name,
            direction=dna.direction,
            trade_id=trade_id,
            reinforcement_type=rtype.value,
            evidence=evidence,
            confidence_before=conf_before,
            confidence_after=conf_after,
            confidence_delta=round(conf_after - conf_before, 6),
            stability_before=stab_before,
            stability_after=stab_after,
            stability_delta=round(stab_after - stab_before, 6),
            evidence_count_before=ev_count,
            evidence_count_after=ev_count + 1,
            reason=reason,
            idr_revision=idr_revision,
            processed_at=ts,
        )

    # ── IDR lookup ────────────────────────────────────────────────────────────

    def _build_idr_lookup(self) -> Dict[Tuple[str, str], Any]:
        """Return a (feature_name, direction) → InstitutionalDNA mapping."""
        try:
            active = self._idr.list_active()
            return {(d.feature_name, d.direction): d for d in active}
        except Exception as exc:
            log.warning("[DRE] IDR lookup failed: %s", exc)
            return {}

    # ── history persistence ───────────────────────────────────────────────────

    def _load_history(self) -> None:
        if not self._history_path.exists():
            self._history = []
            return
        try:
            raw = json.loads(self._history_path.read_text(encoding="utf-8"))
            self._history = [DNAReinforcement.from_dict(r) for r in raw]
        except Exception as exc:
            log.warning("[DRE] Could not load history: %s", exc)
            self._history = []

    def _save_history(self) -> None:
        """Atomically persist history (called under self._lock)."""
        keep = self._history[-self._config.max_history_records:]
        tmp  = self._history_path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps([r.to_dict() for r in keep], indent=2, default=str),
                encoding="utf-8",
            )
            tmp.replace(self._history_path)
        except Exception as exc:
            log.warning("[DRE] History save failed: %s", exc)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    # ── summarise batch ───────────────────────────────────────────────────────

    def summarise_batch(
        self,
        reinforcements: List[DNAReinforcement],
    ) -> List[DNAConfidenceUpdate]:
        """
        Group a list of reinforcements by DNA and return per-DNA summaries.

        Useful for EOD reporting.
        """
        by_dna: Dict[str, List[DNAReinforcement]] = {}
        for r in reinforcements:
            by_dna.setdefault(r.dna_id, []).append(r)

        updates: List[DNAConfidenceUpdate] = []
        for dna_id, recs in by_dna.items():
            type_counts: Dict[str, int] = {}
            for r in recs:
                type_counts[r.reinforcement_type] = type_counts.get(r.reinforcement_type, 0) + 1
            dominant = max(type_counts, key=type_counts.get)

            net_conf  = sum(r.confidence_delta for r in recs)
            net_stab  = sum(r.stability_delta  for r in recs)
            final_c   = recs[-1].confidence_after
            final_s   = recs[-1].stability_after

            try:
                dna_obj = self._idr.get(dna_id)
                lifecycle = dna_obj.lifecycle
                feature   = dna_obj.feature_name
                dirn      = dna_obj.direction
            except Exception:
                lifecycle = "unknown"
                feature   = recs[0].feature_name
                dirn      = recs[0].direction

            updates.append(DNAConfidenceUpdate(
                dna_id=dna_id,
                feature_name=feature,
                direction=dirn,
                lifecycle=lifecycle,
                reinforcements=recs,
                net_confidence_delta=round(net_conf, 6),
                net_stability_delta=round(net_stab, 6),
                final_confidence=final_c,
                final_stability=final_s,
                dominant_type=dominant,
                explanation=(
                    f"{len(recs)} reinforcement(s): "
                    f"dominant={dominant} "
                    f"net_conf_delta={net_conf:+.5f} "
                    f"net_stab_delta={net_stab:+.5f}"
                ),
            ))
        return updates
