"""
sandy/sandy_supervisor.py
=============================
Self-Learning Ecosystem — Phase 7a: "Sandy" Master Meta-Learning Supervisor
(core, data-gathering only -- no Telegram/chat wiring yet, see Phase 7b/7c).

Sandy polls every self-learning agent/phase built in this project (Phases
1-6 plus the pre-existing baseline loops) through their own already-public,
read-only accessors, classifies each one's activity trend, and answers
fixed-keyword queries with a template-based (no LLM) summary.

GOVERNANCE (hard constraints, mirrors every prior phase):
  - Read-only w.r.t. every other agent's actual logic/state. Sandy may
    CALL an agent's own pre-existing, already-safe public recompute
    method (e.g. run_hkap_kde_discovery()) to request a fresh read, but
    NEVER invents new mutation logic and NEVER bypasses an agent's own
    validation/evidence gate. Each agent's own governance decides
    whether to actually change anything -- Sandy only observes, flags,
    and reports.
  - No trade/order/risk-gate access whatsoever.
  - Correlation-with-system-performance claims (a future addition) must
    stay advisory/observational only -- never framed as proven causation.

Safety contract: read-only w.r.t. all trading/decision state. Writes only
to data/sandy/health_history.jsonl (new, append-only). Zero imports from
execution_engine, order_manager, broker APIs, or risk_control. Never raises.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from utils import get_logger

from .sandy_models import (
    AgentHealthReport,
    TREND_ACTIVE,
    TREND_DEGRADING,
    TREND_IDLE,
    TREND_IMPROVING,
    TREND_UNKNOWN,
)

log = get_logger(__name__)

_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR  = os.path.join(_ROOT, "data", "sandy")
HISTORY_FILE = os.path.join(HISTORY_DIR, "health_history.jsonl")

IDLE_THRESHOLD_DAYS = 7   # no new evidence in this many days -> flagged IDLE

SELF_LEARNING_PHASE = "SELF_LEARNING_PHASE"
BASELINE_LOOP       = "BASELINE_LOOP"


class SandySupervisor:
    """Polls every self-learning agent's own read-only accessor; never mutates anything."""

    def __init__(self) -> None:
        self._last_snapshot: Optional[Dict[str, Dict[str, Any]]] = None

    # ── public API ──────────────────────────────────────────────────────────

    def poll_all_agents(self) -> Dict[str, AgentHealthReport]:
        """Poll every registered agent, classify trend vs the last snapshot, persist. Never raises."""
        try:
            return self._poll_impl()
        except Exception as exc:
            log.debug("[Sandy] poll_all_agents error: %s", exc)
            return {}

    def daily_digest(self) -> str:
        """Template-based, human-readable summary of the current poll. Never raises."""
        try:
            reports = self.poll_all_agents()
            return self._format_digest(reports)
        except Exception as exc:
            return f"Sandy hit an error building the digest: {exc}"

    def answer(self, query: str) -> str:
        """
        Fixed-keyword, template-based query response. Never raises.
        Recognised forms (case-insensitive):
          "hi sandy" / "sandy"        -> greeting + top issues
          "sandy report"              -> full digest
          "sandy status <name>"       -> one agent's live status
          "sandy help"                -> capability list
        """
        try:
            return self._answer_impl(query)
        except Exception as exc:
            return f"Sandy hit an error answering that: {exc}"

    # ── data-gathering ────────────────────────────────────────────────────

    def _poll_impl(self) -> Dict[str, AgentHealthReport]:
        pollers = [
            self._poll_options_ks_bridge,
            self._poll_ars_hypothesis_bridge,
            self._poll_pga_learning,
            self._poll_rejection_attribution,
            self._poll_production_readiness,
            self._poll_hkap_kde_bridge,
            self._poll_kda_cre,
            self._poll_rsl_001,
            self._poll_strategy_performance,
            self._poll_regime_strategy_map,
            self._poll_ars_scheduler,
            self._poll_ikn_bridge,
            self._poll_debate_weight_refinement,
            self._poll_dtrace_scheduler,
            self._poll_regime_map_refinement,
            self._poll_shm_regime_health,
            self._poll_trust_weighted_ranking,
            self._poll_shm_profile_refinement,
            self._poll_sizing_bounds_refinement,
            self._poll_capital_reserve_readiness,
            self._poll_options_health,
        ]
        self._last_snapshot = self._load_last_snapshot()
        reports: Dict[str, AgentHealthReport] = {}
        for poller in pollers:
            try:
                report = poller()
                if report is not None:
                    reports[report.name] = report
            except Exception as exc:
                log.debug("[Sandy] poller %s failed: %s", getattr(poller, "__name__", repr(poller)), exc)

        self._classify_trends(reports)
        self._persist_snapshot(reports)
        return reports

    def _poll_options_ks_bridge(self) -> AgentHealthReport:
        from knowledge_system.options_knowledge_store import (
            get_options_knowledge_store, KS_AUTHENTICATED, KS_VALIDATED, KS_DEGRADED,
        )
        store = get_options_knowledge_store()
        authenticated = len(store.get_items_by_state(KS_AUTHENTICATED))
        validated     = len(store.get_items_by_state(KS_VALIDATED))
        degraded      = len(store.get_items_by_state(KS_DEGRADED))
        total         = len(store.get_all_items())
        stage = "AUTHENTICATED" if authenticated else ("VALIDATED" if validated else "OBSERVED")
        issues = ["No items degraded yet — no issues"] if not degraded else [f"{degraded} item(s) degraded"]
        return AgentHealthReport(
            name="Options Knowledge Bridge (Phase 1)",
            category=SELF_LEARNING_PHASE, stage=stage, evidence_count=total,
            summary=f"{total} items tracked ({authenticated} authenticated, {validated} validated, {degraded} degraded).",
            issues=[] if not degraded else issues,
            raw={"authenticated": authenticated, "validated": validated, "degraded": degraded, "total": total},
        )

    def _poll_ars_hypothesis_bridge(self) -> AgentHealthReport:
        from autonomous_research.knowledge_provider import KnowledgeProvider
        from autonomous_research.hypothesis_registry import HypothesisRegistry
        reg = HypothesisRegistry(knowledge_provider=KnowledgeProvider())
        all_h = reg.list_all()
        confirmed = reg.list_confirmed()
        with_subject = [h for h in all_h if getattr(h, "subject_type", None) and getattr(h, "direction", None)]
        stage = "DORMANT (no CONFIRMED+subject hypothesis yet)"
        if any(h in confirmed for h in with_subject):
            stage = "ACTIVE (bridge nudging KDA relevance)"
        return AgentHealthReport(
            name="ARS Hypothesis -> KDA Bridge (Phase 2)",
            category=SELF_LEARNING_PHASE, stage=stage, evidence_count=len(all_h),
            summary=f"{len(all_h)} hypotheses total, {len(confirmed)} CONFIRMED, "
                    f"{len(with_subject)} carry a structured subject.",
            issues=[] if with_subject else ["No hypothesis has a structured subject yet — bridge is dormant."],
            raw={"total": len(all_h), "confirmed": len(confirmed), "with_subject": len(with_subject)},
        )

    def _poll_pga_learning(self) -> AgentHealthReport:
        from predictive_gap.pga_learning import get_last_run_summary
        summary = get_last_run_summary()
        if summary is None:
            return AgentHealthReport(
                name="Predictive Gap Analysis (Phase 3)",
                category=SELF_LEARNING_PHASE, stage="NO RUNS YET",
                summary="PGA has not produced a learning-actions report yet.",
                issues=["No PGA run recorded yet."],
            )
        return AgentHealthReport(
            name="Predictive Gap Analysis (Phase 3)",
            category=SELF_LEARNING_PHASE, stage="ACTIVE",
            evidence_count=summary["total_actions"], last_activity_at=summary["report_date"],
            summary=f"Last run {summary['report_date']}: {summary['total_actions']} learning "
                    f"actions, categories={summary['by_category']}.",
            raw=summary,
        )

    def _poll_rejection_attribution(self) -> AgentHealthReport:
        history = self._read_jsonl_tail(
            os.path.join(_ROOT, "data", "rejection_attribution", "daily_summary.jsonl"), n=1,
        )
        if not history:
            return AgentHealthReport(
                name="Rejection Attribution Monitor (Phase 4)",
                category=SELF_LEARNING_PHASE, stage="NO RUNS YET",
                summary="No daily rejection-attribution cycle has run yet.",
                issues=["No cycle recorded yet."],
            )
        latest = history[-1]
        return AgentHealthReport(
            name="Rejection Attribution Monitor (Phase 4)",
            category=SELF_LEARNING_PHASE, stage="ACTIVE",
            evidence_count=latest.get("classified_total"), last_activity_at=latest.get("date"),
            summary=f"Resolved {latest.get('resolved_today', 0)} rejections on {latest.get('date')}; "
                    f"{latest.get('classified_total', 0)} classified total; "
                    f"reliable reasons={latest.get('reasons_with_min_sample', [])}.",
            raw=latest,
        )

    def _poll_production_readiness(self) -> AgentHealthReport:
        from production_readiness.prr_monitor import get_latest_certification
        latest = get_latest_certification()
        if latest is None:
            return AgentHealthReport(
                name="Production Readiness Monitor (Phase 5)",
                category=SELF_LEARNING_PHASE, stage="NO RUNS YET",
                summary="No PRR certification recorded yet.",
                issues=["No certification recorded yet."],
            )
        status = latest.get("certification_status", "UNKNOWN")
        issues = [] if status == "PRODUCTION_READY" else [f"Certification status is {status}."]
        return AgentHealthReport(
            name="Production Readiness Monitor (Phase 5)",
            category=SELF_LEARNING_PHASE, stage=status,
            last_activity_at=latest.get("date"),
            summary=f"{latest.get('date')}: {status}, ILS={latest.get('ils_score', 0):.1f}, "
                    f"GVA={latest.get('gva_score', 0):.1f}, critical={latest.get('critical_failures', 0)}.",
            issues=issues, raw=latest,
        )

    def _poll_hkap_kde_bridge(self) -> AgentHealthReport:
        from hkap.hkap_kde_bridge import get_latest_discovery_run
        latest = get_latest_discovery_run()
        if latest is None:
            return AgentHealthReport(
                name="HKAP -> KDE Discovery Bridge (Phase 6)",
                category=SELF_LEARNING_PHASE, stage="NO RUNS YET",
                summary="No HKAP->KDE discovery run recorded yet.",
                issues=["No discovery run recorded yet."],
            )
        return AgentHealthReport(
            name="HKAP -> KDE Discovery Bridge (Phase 6)",
            category=SELF_LEARNING_PHASE, stage="ACTIVE",
            evidence_count=latest.get("total_discoveries"), last_activity_at=latest.get("generated_at"),
            summary=f"{latest.get('total_discoveries', 0)} discoveries from years "
                    f"{latest.get('years_used')}, avg_score={latest.get('avg_score', 0):.3f}.",
            raw=latest,
        )

    def _poll_kda_cre(self) -> AgentHealthReport:
        from knowledge_authority.kda_constant_refinement_engine import get_refinement_status
        status = get_refinement_status()
        per_constant = status.get("per_constant", {})
        active = [n for n, s in per_constant.items() if s.get("status") == "ACTIVE"]
        waiting = [n for n, s in per_constant.items() if s.get("status") == "WAITING_FOR_EVIDENCE"]
        stage = "ACTIVE" if active else ("WAITING_FOR_EVIDENCE" if waiting else "SHADOW/OTHER")
        return AgentHealthReport(
            name="KDA Constant Refinement Engine (KDA-CRE-001)",
            category=SELF_LEARNING_PHASE, stage=stage,
            summary=f"{len(active)}/{len(per_constant)} constants ACTIVE, {len(waiting)} waiting for evidence.",
            raw=status,
        )

    def _poll_ars_scheduler(self) -> AgentHealthReport:
        from autonomous_research.ars_scheduler import get_last_run_summary
        latest = get_last_run_summary()
        if latest is None:
            return AgentHealthReport(
                name="ARS Scheduler -- 9-agent research cluster (Priority 1)",
                category=SELF_LEARNING_PHASE, stage="NO RUNS YET",
                summary="No autonomous research cycle has run yet.",
                issues=["No cycle recorded yet."],
            )
        stage = "ACTIVE" if latest.get("status") == "OK" else latest.get("status", "UNKNOWN")
        return AgentHealthReport(
            name="ARS Scheduler -- 9-agent research cluster (Priority 1)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=latest.get("decisions"), last_activity_at=latest.get("generated_at"),
            summary=f"gaps={latest.get('total_gaps_open', 0)} plans={latest.get('plans_created', 0)} "
                    f"review_health={latest.get('review_health')} decisions={latest.get('decisions', 0)}.",
            raw=latest,
        )

    def _poll_ikn_bridge(self) -> AgentHealthReport:
        from ikn.ikn_network import IKNNetwork
        from ikn.ikn_config import IKNConfig
        ikn = IKNNetwork(IKNConfig())
        try:
            stats = ikn.statistics()
        finally:
            ikn.close()
        stage = "ACTIVE" if stats.total_nodes > 0 else "NO DATA YET"
        return AgentHealthReport(
            name="Institutional Knowledge Network (Priority 2)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=stats.total_relationships,
            summary=f"{stats.total_nodes} nodes, {stats.total_relationships} relationships, "
                    f"avg_confidence={stats.avg_confidence:.3f}.",
            issues=[] if stats.total_nodes > 0 else ["IKN store has no data yet."],
            raw=stats.to_dict() if hasattr(stats, "to_dict") else {},
        )

    def _poll_debate_weight_refinement(self) -> AgentHealthReport:
        from debate_system.debate_weight_refinement_engine import get_refinement_status
        from debate_system.debate_vote_tracker import get_debater_accuracy
        status = get_refinement_status().get("per_agent", {})
        accuracy = get_debater_accuracy()
        active = [n for n, s in status.items() if s.get("status") == "ACTIVE"]
        shadow = [n for n, s in status.items() if s.get("status") == "SHADOW_ACTIVE"]
        total_resolved = sum(a.get("sample_size", 0) for a in accuracy.values())
        stage = "ACTIVE" if active else ("SHADOW" if shadow else "WAITING_FOR_EVIDENCE")
        return AgentHealthReport(
            name="Debate Weight Refinement Engine (Priority 3)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=total_resolved,
            summary=f"{len(active)} ACTIVE, {len(shadow)} in SHADOW, "
                    f"{total_resolved} resolved votes total across all debaters.",
            raw={"status": status, "accuracy": accuracy},
        )

    def _poll_dtrace_scheduler(self) -> AgentHealthReport:
        from decision_tracer.dtrace_scheduler import get_last_run_summary
        latest = get_last_run_summary()
        if latest is None:
            return AgentHealthReport(
                name="Decision Tracer Scheduler (Priority 4)",
                category=SELF_LEARNING_PHASE, stage="NO RUNS YET",
                summary="No daily decision-trace batch has run yet.",
                issues=["No batch recorded yet."],
            )
        stage = "ACTIVE" if latest.get("status") == "OK" else latest.get("status", "UNKNOWN")
        return AgentHealthReport(
            name="Decision Tracer Scheduler (Priority 4)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=latest.get("symbols_traced", 0),
            last_activity_at=latest.get("generated_at"),
            summary=f"{latest.get('symbols_traced', 0)} symbol(s) traced on {latest.get('trade_date', latest.get('trace_date'))}.",
            raw=latest,
        )

    def _poll_regime_map_refinement(self) -> AgentHealthReport:
        from strategy_lab.regime_map_refinement_engine import get_refinement_status
        from meta_learning.regime_map_evidence_log import get_records
        status = get_refinement_status().get("per_pair", {})
        demoted = [k for k, s in status.items() if s.get("status") == "ACTIVE"]
        shadow = [k for k, s in status.items() if s.get("status") == "SHADOW_ACTIVE"]
        total_evidence = len(get_records())
        stage = "ACTIVE" if demoted else ("SHADOW" if shadow else "WAITING_FOR_EVIDENCE")
        return AgentHealthReport(
            name="Regime Map Refinement Engine (Priority 5)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=total_evidence,
            summary=f"{len(demoted)} demoted, {len(shadow)} in SHADOW, "
                    f"{total_evidence} regime-tagged trade(s) observed total.",
            raw=status,
        )

    def _poll_shm_regime_health(self) -> AgentHealthReport:
        from trade_monitoring.strategy_regime_health_engine import get_refinement_status
        status = get_refinement_status().get("per_pair", {})
        disabled = [k for k, s in status.items() if s.get("status") == "ACTIVE"]
        shadow = [k for k, s in status.items() if s.get("status") == "SHADOW_ACTIVE"]
        total_pairs = len(status)
        stage = "ACTIVE" if disabled else ("SHADOW" if shadow else "WAITING_FOR_EVIDENCE")
        return AgentHealthReport(
            name="StrategyHealthMonitor Regime-Aware Disabling (#24)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=total_pairs,
            summary=f"{len(disabled)} regime-scoped disable(s) active, {len(shadow)} in SHADOW, "
                    f"{total_pairs} (regime,strategy) pair(s) tracked.",
            raw=status,
        )

    def _poll_trust_weighted_ranking(self) -> AgentHealthReport:
        from opportunity_engine.trust_weighted_ranking_engine import get_status
        status = get_status()
        stage = "ACTIVE" if status.get("gate_met") else "WAITING_FOR_EVIDENCE"
        return AgentHealthReport(
            name="Trust-Weighted Candidate Ranking (#26)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=status.get("history_days_count", 0),
            summary=f"{status.get('history_days_count', 0)}/{status.get('min_history_days')} "
                    f"day(s) of persisted trust history, gate_met={status.get('gate_met')}.",
            raw=status,
        )

    def _poll_shm_profile_refinement(self) -> AgentHealthReport:
        from trade_monitoring.strategy_profile_refinement_engine import get_refinement_status
        status = get_refinement_status().get("per_strategy", {})
        applied = [k for k, s in status.items() if s.get("status") == "ACTIVE"]
        shadow = [k for k, s in status.items() if s.get("status") == "SHADOW_ACTIVE"]
        total = len(status)
        stage = "ACTIVE" if applied else ("SHADOW" if shadow else "WAITING_FOR_EVIDENCE")
        return AgentHealthReport(
            name="Profile-Aware Governance Auto-Apply (#25)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=total,
            summary=f"{len(applied)} profile(s) auto-applied, {len(shadow)} in SHADOW, "
                    f"{total} strategy/strategies tracked.",
            raw=status,
        )

    def _poll_sizing_bounds_refinement(self) -> AgentHealthReport:
        from learning_system.sizing_bounds_refinement_engine import get_refinement_status, get_records
        status = get_refinement_status()
        stage = status.get("status", "WAITING_FOR_EVIDENCE")
        total_evidence = len(get_records())
        return AgentHealthReport(
            name="Sizing Bounds Calibration (#27)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=total_evidence,
            summary=f"status={stage}, active_adjustment={status.get('active_adjustment', 0.0)}, "
                    f"{total_evidence} sizing outcome(s) observed total.",
            raw=status,
        )

    def _poll_capital_reserve_readiness(self) -> AgentHealthReport:
        from analysis.capital_reserve_readiness_engine import get_readiness_status
        status = get_readiness_status()
        stage = status.get("status", "WAITING_FOR_EVIDENCE")
        return AgentHealthReport(
            name="Intelligent Capital Reserve Readiness (#28)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=status.get("classified_samples", 0),
            summary=f"status={stage}, false_negative_pct={status.get('false_negative_pct', 'n/a')}, "
                    f"{status.get('classified_samples', 0)} MAX_POSITIONS_CAP rejection(s) resolved.",
            raw=status,
        )

    def _poll_options_health(self) -> AgentHealthReport:
        from data_feeds.options_health_history import get_options_health_status, get_history_days_count
        status = get_options_health_status("NIFTY")
        days = get_history_days_count()
        stage = status.get("status", "WAITING_FOR_EVIDENCE")
        return AgentHealthReport(
            name="Options Health Metrics Dashboard (#10)",
            category=SELF_LEARNING_PHASE, stage=stage,
            evidence_count=days,
            summary=f"status={stage}, {days}/7 day(s) of persisted history.",
            raw=status,
        )

    def _poll_rsl_001(self) -> AgentHealthReport:
        from scripts.knowledge_system.ranking_adjustment_engine_001 import get_active_adjustments_status
        status = get_active_adjustments_status()
        candidates = status.get("candidates", [])
        active_config = status.get("active_config", {})
        stage = "ACTIVE" if active_config else ("SHADOW" if candidates else "NO CANDIDATES YET")
        return AgentHealthReport(
            name="Ranking Self-Learning Loop (RSL-001)",
            category=SELF_LEARNING_PHASE, stage=stage, evidence_count=len(candidates),
            summary=f"{len(candidates)} shadow candidate(s) tracked, {len(active_config)} direction(s) live-active.",
            raw=status,
        )

    def _poll_strategy_performance(self) -> AgentHealthReport:
        from learning_system.strategy_performance_tracker import get_performance_tracker
        tracker = get_performance_tracker()
        all_stats = tracker.get_all_stats()
        disabled = tracker.get_disabled_set()
        total_trades = sum(s.total_trades for s in all_stats.values())
        return AgentHealthReport(
            name="Strategy Performance Tracker (baseline)",
            category=BASELINE_LOOP, stage="ACTIVE" if all_stats else "NO DATA YET",
            evidence_count=total_trades,
            summary=f"{len(all_stats)} strategies tracked, {len(disabled)} auto-disabled, "
                    f"{total_trades} total trades recorded.",
            issues=[f"{len(disabled)} strategy(ies) auto-disabled: {sorted(disabled)}"] if disabled else [],
        )

    def _poll_regime_strategy_map(self) -> AgentHealthReport:
        from meta_learning.regime_strategy_map import get_regime_strategy_map
        rsm = get_regime_strategy_map()
        return AgentHealthReport(
            name="Regime Strategy Map (baseline)",
            category=BASELINE_LOOP, stage="ACTIVE" if rsm.total_trades else "NO DATA YET",
            evidence_count=rsm.total_trades, summary=rsm.learning_stage(),
        )

    # ── trend classification ─────────────────────────────────────────────

    def _classify_trends(self, reports: Dict[str, AgentHealthReport]) -> None:
        prior = self._last_snapshot or {}
        now = datetime.now(timezone.utc)
        for name, report in reports.items():
            prev = prior.get(name)
            if prev is None:
                report.trend = TREND_UNKNOWN
                continue
            prev_count = prev.get("evidence_count")
            prev_at = prev.get("polled_at")
            if report.evidence_count is None or prev_count is None:
                report.trend = TREND_UNKNOWN
                continue
            if report.evidence_count > prev_count:
                report.trend = TREND_ACTIVE
                continue
            # no growth since last poll -- check staleness
            try:
                prev_dt = datetime.fromisoformat(prev_at) if prev_at else None
            except Exception:
                prev_dt = None
            if prev_dt and (now - prev_dt) >= timedelta(days=IDLE_THRESHOLD_DAYS):
                report.trend = TREND_IDLE
                report.issues.append(
                    f"No new evidence in >= {IDLE_THRESHOLD_DAYS} days (stuck at {report.evidence_count})."
                )
            else:
                report.trend = TREND_UNKNOWN

    # ── persistence ───────────────────────────────────────────────────────

    def _load_last_snapshot(self) -> Optional[Dict[str, Dict[str, Any]]]:
        try:
            lines = self._read_jsonl_tail(HISTORY_FILE, n=1)
            if not lines:
                return None
            return lines[-1].get("agents", {})
        except Exception:
            return None

    def _persist_snapshot(self, reports: Dict[str, AgentHealthReport]) -> None:
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
            polled_at = datetime.now(timezone.utc).isoformat()
            record = {
                "polled_at": polled_at,
                "agents": {
                    name: {"evidence_count": r.evidence_count, "polled_at": polled_at, "stage": r.stage}
                    for name, r in reports.items()
                },
            }
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            log.debug("[Sandy] snapshot write skipped: %s", exc)

    @staticmethod
    def _read_jsonl_tail(path: str, n: int) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
            return [json.loads(ln) for ln in lines[-n:]]
        except Exception:
            return []

    # ── template-based reply composition ─────────────────────────────────

    def _format_digest(self, reports: Dict[str, AgentHealthReport]) -> str:
        lines = ["Hi, Sandy here. Here's where every self-learning agent stands right now:", ""]
        for name, r in sorted(reports.items()):
            flag = "⚠️ " if r.issues or r.trend in (TREND_IDLE, TREND_DEGRADING) else ""
            lines.append(f"{flag}{name}: {r.stage} — {r.summary}")
        attention = [r for r in reports.values() if r.issues or r.trend in (TREND_IDLE, TREND_DEGRADING)]
        lines.append("")
        if attention:
            lines.append(f"{len(attention)} agent(s) need a look:")
            for r in attention:
                for issue in (r.issues or [f"trend={r.trend}"]):
                    lines.append(f"  - {r.name}: {issue}")
        else:
            lines.append("Nothing needs attention right now.")
        return "\n".join(lines)

    def _format_greeting(self, reports: Dict[str, AgentHealthReport]) -> str:
        attention = [r for r in reports.values() if r.issues or r.trend in (TREND_IDLE, TREND_DEGRADING)]
        if not attention:
            return (f"Hi! I checked all {len(reports)} agents — everything looks fine, "
                     f"nothing needs your attention right now. Ask 'Sandy report' for the full picture.")
        lines = [f"Hi! I checked all {len(reports)} agents. {len(attention)} need a look:"]
        for r in attention[:5]:
            reason = r.issues[0] if r.issues else f"trend={r.trend}"
            lines.append(f"  - {r.name}: {reason}")
        lines.append("Ask 'Sandy report' for the full picture, or 'Sandy status <name>' for one agent.")
        return "\n".join(lines)

    def _format_agent_detail(self, report: AgentHealthReport) -> str:
        lines = [
            f"{report.name}",
            f"Stage: {report.stage}   Trend: {report.trend}",
            f"{report.summary}",
        ]
        if report.issues:
            lines.append("Issues:")
            lines.extend(f"  - {i}" for i in report.issues)
        return "\n".join(lines)

    def _answer_impl(self, query: str) -> str:
        q = (query or "").strip().lower()
        reports = self.poll_all_agents()

        if q.startswith("sandy status"):
            target = q[len("sandy status"):].strip()
            if not target:
                return "Tell me which agent, e.g. 'Sandy status HKAP'."
            matches = [r for name, r in reports.items() if target in name.lower()]
            if not matches:
                names = ", ".join(sorted(reports.keys()))
                return f"I don't recognise '{target}'. Known agents: {names}"
            return "\n\n".join(self._format_agent_detail(r) for r in matches)

        if q in ("sandy report", "report"):
            return self._format_digest(reports)

        if q in ("sandy help", "help"):
            return (
                "I'm Sandy. Ask me:\n"
                "  'Hi Sandy' or 'Sandy' — quick greeting + what needs attention\n"
                "  'Sandy report' — full status of every agent\n"
                "  'Sandy status <name>' — one agent's live detail\n"
                "  'Sandy help' — this message"
            )

        if q in ("hi sandy", "sandy", "hello sandy"):
            return self._format_greeting(reports)

        return "I didn't recognise that. Try 'Sandy help' to see what I can do."


# ── singleton ─────────────────────────────────────────────────────────────

_supervisor: Optional[SandySupervisor] = None


def get_sandy_supervisor() -> SandySupervisor:
    global _supervisor
    if _supervisor is None:
        _supervisor = SandySupervisor()
    return _supervisor
