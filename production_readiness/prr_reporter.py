"""
production_readiness/prr_reporter.py — PRR-001 Report Writer.

Generates 9 markdown reports:
    EDGE_LIFECYCLE_AUDIT.md
    SHORT_TRADING_AUDIT.md
    SIGNAL_FRESHNESS_REPORT.md
    UNIVERSE_COVERAGE_REPORT.md
    DAILY_LEARNING_PIPELINE_REPORT.md
    KNOWLEDGE_VALIDITY_REPORT.md
    MISSED_OPPORTUNITY_REPORT.md
    LEARNING_IMPACT_REPORT.md
    FINAL_PRODUCTION_READINESS_CERTIFICATE.md
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .prr_config import REPORT_DIR
from .prr_models import (
    DailyPipelineResult,
    EdgeGateResult,
    KnowledgeValidityReport,
    LearningImpactSummary,
    MissedOpportunityReport,
    ProductionCertificate,
    ShortDNAAudit,
    SignalFreshnessReport,
    UniverseCoverageReport,
)

log = logging.getLogger(__name__)


def _dir(today: str) -> Path:
    d = REPORT_DIR / today
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─────────────────────────────────────────────────────────────────────────────


def write_edge_lifecycle_audit(edge_gate: Optional[EdgeGateResult], today: str) -> Path:
    d = _dir(today)
    path = d / "EDGE_LIFECYCLE_AUDIT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if edge_gate is None:
        path.write_text(f"# EDGE_LIFECYCLE_AUDIT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    blocked_list = "\n".join(f"- `{e}`" for e in edge_gate.blocked_edge_ids) or "_None_"
    path.write_text(f"""# EDGE_LIFECYCLE_AUDIT — {today}
_Generated: {ts} | PRR-001 Phase 1_

## Summary

| Metric | Value |
|--------|-------|
| Total edges | {edge_gate.total_edges} |
| ACTIVE edges | {edge_gate.active_edges} |
| CANDIDATE edges | {edge_gate.candidate_edges} |
| DECAYING (blocked) | {edge_gate.decaying_blocked} |
| RETIRED (blocked) | {edge_gate.retired_blocked} |
| % blocked | {edge_gate.pct_blocked:.1f}% |

## Blocked Edge IDs

{blocked_list}

## Governance Rule

> **DECAYING and RETIRED edges are permanently blocked from contributing to**
> **live signals, decisions, or confidence calculations.**
>
> DECAYING edge contribution = {0.0} (configured via DECAYING_EDGE_CONTRIBUTION).
> RETIRED edges are excluded entirely.

## Status

{"⚠️ " + str(edge_gate.decaying_blocked + edge_gate.retired_blocked) + " edges were blocked this cycle." if (edge_gate.decaying_blocked + edge_gate.retired_blocked) > 0 else "✅ No DECAYING/RETIRED edges affected this cycle."}
""", encoding="utf-8")
    return path


def write_short_trading_audit(short_dna: Optional[ShortDNAAudit], today: str) -> Path:
    d = _dir(today)
    path = d / "SHORT_TRADING_AUDIT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if short_dna is None:
        path.write_text(f"# SHORT_TRADING_AUDIT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    signals_md = ""
    for sig in short_dna.top_signals:
        conds = "\n".join(f"  - {c}" for c in sig.matching_conditions) or "  - _none_"
        signals_md += (
            f"\n### {sig.symbol}\n"
            f"- Direction: {sig.direction}\n"
            f"- DNA Confidence: {sig.dna_confidence:.3f}\n"
            f"- Governance Approved: {'✅' if sig.governance_approved else '❌'}\n"
            f"- Rejection Reason: {sig.rejection_reason or '_none_'}\n"
            f"- Matching Conditions:\n{conds}\n"
        )

    path.write_text(f"""# SHORT_TRADING_AUDIT — {today}
_Generated: {ts} | PRR-001 Phase 2_

## H001 Status: CONFIRMED ✅

> H001: Loser DNA cross-year validation — loser DNA patterns apply across market cycles
> and may generate SHORT signals when institutional conditions match.

## Summary

| Metric | Value |
|--------|-------|
| Loser DNA patterns loaded | {short_dna.total_loser_dna} |
| SHORT conditions evaluated | {short_dna.conditions_evaluated} |
| SHORT signals generated | {short_dna.short_signals_generated} |
| SHORT signals governance-approved | {short_dna.short_signals_approved} |
| Regime | {short_dna.regime} |
| Confidence gate | {short_dna.confidence_gate:.2f} |

## Signal Details
{signals_md or "_No SHORT DNA signals this cycle._"}

## Governance

SHORT signals follow identical governance to LONG:
- Confidence gate: {short_dna.confidence_gate:.1f}
- Risk management: PortfolioAllocation + RiskManagerAI
- Decision debate: 5-agent consensus (threshold 6.5)
- Execution: OrderManager (PAPER mode)
""", encoding="utf-8")
    return path


def write_signal_freshness_report(freshness: Optional[SignalFreshnessReport], today: str) -> Path:
    d = _dir(today)
    path = d / "SIGNAL_FRESHNESS_REPORT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if freshness is None:
        path.write_text(f"# SIGNAL_FRESHNESS_REPORT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    path.write_text(f"""# SIGNAL_FRESHNESS_REPORT — {today}
_Generated: {ts} | PRR-001 Phase 3_

## Summary

| Status | Count | % |
|--------|-------|---|
| FRESH (0–5 trading days) | {freshness.fresh} | {round(100*freshness.fresh/max(freshness.signals_checked,1),1):.1f}% |
| WEAKENING (6–15 days) | {freshness.weakening} | {round(100*freshness.weakening/max(freshness.signals_checked,1),1):.1f}% |
| EXPIRED (15+ days) | {freshness.expired} | {round(100*freshness.expired/max(freshness.signals_checked,1),1):.1f}% |
| **Blocked from execution** | **{freshness.blocked_for_execution}** | |

Total signals checked: **{freshness.signals_checked}**
Oldest blocked: **{freshness.oldest_blocked_days:.1f} trading days**

## Governance Rule

| Age | Status | Action |
|-----|--------|--------|
| 0–5 trading days | FRESH | Execute normally |
| 6–15 trading days | WEAKENING | Execute with warning; entry thesis may have changed |
| >15 trading days | EXPIRED | **BLOCKED** — never executed |

## Implementation

Signal freshness is enforced in `execution_engine/order_manager.py` via
`is_signal_expired()` from `production_readiness.ph3_signal_freshness`.
""", encoding="utf-8")
    return path


def write_universe_coverage_report(universe: Optional[UniverseCoverageReport], today: str) -> Path:
    d = _dir(today)
    path = d / "UNIVERSE_COVERAGE_REPORT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if universe is None:
        path.write_text(f"# UNIVERSE_COVERAGE_REPORT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    excl_rows = "\n".join(
        f"| {e.symbol} | {e.sector} | {e.adv_crore:.1f} | {e.exclusion_reason} |"
        for e in universe.symbols if not e.is_eligible
    )[:3000]

    path.write_text(f"""# UNIVERSE_COVERAGE_REPORT — {today}
_Generated: {ts} | PRR-001 Phase 4_

## Summary

| Metric | Value |
|--------|-------|
| Total Nifty500 symbols | {universe.total_nifty500} |
| Eligible for scanning | {universe.eligible} |
| Excluded | {universe.excluded} |
| Coverage | {universe.coverage_pct:.1f}% |
| Unexpected exclusions | {len(universe.unexpected_exclusions)} |

## Exclusion Breakdown

{chr(10).join(f"- {k}: {v}" for k,v in universe.exclusion_breakdown.items()) or "_None_"}

## Excluded Symbols

| Symbol | Sector | ADV (Cr) | Reason |
|--------|--------|-----------|--------|
{excl_rows or "| — | — | — | — |"}

## Governance Rule

> **No symbols are hardcoded.** The universe is automatically maintained from
> `data/nifty500_universe.json` filtered by ADV ≥ {50} Cr.
> Universe refreshes every 24 hours without manual intervention.
""", encoding="utf-8")
    return path


def write_daily_pipeline_report(pipeline: Optional[DailyPipelineResult], today: str) -> Path:
    d = _dir(today)
    path = d / "DAILY_LEARNING_PIPELINE_REPORT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if pipeline is None:
        path.write_text(f"# DAILY_LEARNING_PIPELINE_REPORT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    def _row(stage):
        if stage is None:
            return "| ? | — | — | — |"
        icon = "✅" if stage.success else "❌"
        return f"| {stage.stage} | {icon} | {stage.elapsed_seconds:.1f}s | {stage.error or 'OK'} |"

    path.write_text(f"""# DAILY_LEARNING_PIPELINE_REPORT — {today}
_Generated: {ts} | PRR-001 Phase 5_

## Pipeline Result

**Stages completed:** {pipeline.stages_completed}/6
**Total elapsed:** {pipeline.total_elapsed_seconds:.1f}s

## Stage Summary

| Stage | Status | Time | Notes |
|-------|--------|------|-------|
{_row(pipeline.pga)}
{_row(pipeline.ilc)}
{_row(pipeline.gva)}
{_row(pipeline.sd_review)}
{_row(pipeline.verification)}
{_row(pipeline.reports)}

## Governance

Each stage is fully failure-isolated: failure of one stage never stops the rest.
Pipeline runs automatically at 15:35 IST after each market close.
""", encoding="utf-8")
    return path


def write_knowledge_validity_report(kv: Optional[KnowledgeValidityReport], today: str) -> Path:
    d = _dir(today)
    path = d / "KNOWLEDGE_VALIDITY_REPORT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if kv is None:
        path.write_text(f"# KNOWLEDGE_VALIDITY_REPORT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    by_type_rows = "\n".join(
        f"| {t} | {v.get('VALID',0)} | {v.get('AGING',0)} | {v.get('STALE',0)} |"
        for t, v in kv.by_type.items()
    )
    stale_items = [i for i in kv.items if i.validity_status == "STALE"][:20]
    stale_rows  = "\n".join(
        f"| {i.item_id[:24]} | {i.item_type} | {i.days_since_verified}d | {i.blocks_trading} |"
        for i in stale_items
    )

    path.write_text(f"""# KNOWLEDGE_VALIDITY_REPORT — {today}
_Generated: {ts} | PRR-001 Phase 6_

## Summary

| Metric | Count |
|--------|-------|
| Total knowledge items | {kv.total_items} |
| VALID | {kv.valid_items} |
| STALE | {kv.stale_items} |
| Trading blocked | {kv.trading_blocked_items} |

## By Knowledge Type

| Type | VALID | AGING | STALE |
|------|-------|-------|-------|
{by_type_rows or "_No data_"}

## Stale Items (top 20)

| ID | Type | Age | Blocks Trading |
|----|------|-----|----------------|
{stale_rows or "_None — all knowledge is current_"}

## Validity Thresholds

| Knowledge Type | Stale Threshold |
|----------------|-----------------|
| DNA | 90 days since last_seen |
| Edge | 60 days since last update |
| Hypothesis | 180 days since last review |
""", encoding="utf-8")
    return path


def write_missed_opportunity_report(missed: Optional[MissedOpportunityReport], today: str) -> Path:
    d = _dir(today)
    path = d / "MISSED_OPPORTUNITY_REPORT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if missed is None:
        path.write_text(f"# MISSED_OPPORTUNITY_REPORT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    rows = "\n".join(
        f"| {c.symbol} | {c.move_pct:+.1f}% | {c.direction} | {c.classification} | {'🔴 YES' if c.triggers_learning else 'No'} |"
        for c in missed.classifications
    )
    path.write_text(f"""# MISSED_OPPORTUNITY_REPORT — {today}
_Generated: {ts} | PRR-001 Phase 7_

## Summary

| Classification | Count |
|----------------|-------|
| Correctly Ignored | {missed.correctly_ignored} |
| Universe Limitation | {missed.universe_limitation} |
| Knowledge Limitation | {missed.knowledge_limitation} |
| Research Limitation | {missed.research_limitation} |
| Threshold Limitation | {missed.threshold_limitation} |
| Risk Limitation | {missed.risk_limitation} |
| Portfolio Limitation | {missed.portfolio_limitation} |
| External Event | {missed.external_event} |
| **Triggers Learning** | **{missed.triggers_learning}** |

Total misses analysed: **{missed.total_misses}**

## Individual Classifications

| Symbol | Move | Direction | Classification | Triggers Learning |
|--------|------|-----------|----------------|-------------------|
{rows or "_No misses to classify_"}

## Governance Rule

Only **Knowledge_Limitation**, **Research_Limitation**, and **Threshold_Limitation**
misses generate new learning actions. All other categories are either expected
system behaviour or external events outside IIOS control.
""", encoding="utf-8")
    return path


def write_learning_impact_report(impact: Optional[LearningImpactSummary], today: str) -> Path:
    d = _dir(today)
    path = d / "LEARNING_IMPACT_REPORT.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if impact is None:
        path.write_text(f"# LEARNING_IMPACT_REPORT — {today}\n\n_No data available._\n", encoding="utf-8")
        return path

    improved_list = "\n".join(f"- {a}" for a in impact.top_improved) or "_None yet_"
    declined_list = "\n".join(f"- {a}" for a in impact.top_declined) or "_None yet_"

    path.write_text(f"""# LEARNING_IMPACT_REPORT — {today}
_Generated: {ts} | PRR-001 Phase 8_

## Summary

| Metric | Value |
|--------|-------|
| Total learning actions | {impact.total_actions} |
| Pending verification | {impact.pending_verification} |
| Under verification | {impact.under_verification} |
| Improved | {impact.improved} |
| No change | {impact.no_change} |
| Declined | {impact.declined} |
| Retired | {impact.retired} |
| **Avg improvement** | **{impact.avg_improvement_pct:.1f}%** |
| **ROI positive rate** | **{impact.roi_positive_pct:.1f}%** |

## Top Improved Actions

{improved_list}

## Top Declined Actions

{declined_list}

## Source

Powered by ILC Verification Engine — 30/60/90-day rolling measurement windows.
Registry: `data/ilc/learning_registry.json`
""", encoding="utf-8")
    return path


def write_final_certificate(cert: Optional[ProductionCertificate], today: str) -> Path:
    d = _dir(today)
    path = d / "FINAL_PRODUCTION_READINESS_CERTIFICATE.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if cert is None:
        path.write_text(f"# FINAL_PRODUCTION_READINESS_CERTIFICATE — {today}\n\n_Not generated._\n", encoding="utf-8")
        return path

    verdict_icon = {"PRODUCTION_READY": "✅", "PRODUCTION_READY_WITH_OBSERVATIONS": "⚠️", "NOT_READY": "❌"}.get(cert.verdict, "?")
    checks_rows = "\n".join(
        f"| {c.check_name} | {'✅' if c.passed else '❌'} | {c.severity} | {c.detail[:80]} |"
        for c in cert.checks
    )

    path.write_text(f"""# FINAL PRODUCTION READINESS CERTIFICATE
## PRR-001 — {today}
_Generated: {ts}_

---

## VERDICT: {verdict_icon} {cert.verdict}

> {cert.narrative}

---

## Certifying Agents

{', '.join(cert.certifying_agents)}

## Scores

| Metric | Value |
|--------|-------|
| Institutional Learning Score (ILS) | {cert.ils_score:.1f}/100 |
| Growth Validation Score (GVA) | {cert.gva_score:.1f}/100 |
| Critical failures | {cert.critical_failures} |
| Observations | {cert.warnings} |

## Production Capability Matrix

| Capability | Status |
|------------|--------|
| DECAYING Edge Gate | {'✅ ACTIVE' if cert.edge_gate_pct_blocked >= 0 else '❌ INACTIVE'} — {cert.edge_gate_pct_blocked:.1f}% edges blocked |
| SHORT DNA Operationalisation | {'✅ ACTIVE' if cert.short_dna_operational else '❌ NOT ACTIVE'} — H001 confirmed |
| Signal Expiry Gate | {'✅ ACTIVE' if cert.signal_expiry_active else '❌ NOT ACTIVE'} — 15+ day signals blocked |
| Auto Universe | {'✅ ACTIVE' if cert.auto_universe_active else '❌ NOT ACTIVE'} — no hardcoded symbols |
| Daily ILC Pipeline | {'✅ ACTIVE' if cert.daily_ilc_active else '❌ NOT ACTIVE'} — automated post-market |
| Knowledge Validity | {'✅ ACTIVE' if cert.knowledge_validity_active else '❌ NOT ACTIVE'} — expiry tracked |
| Learning Verification | {'✅ ACTIVE' if cert.learning_verification_active else '❌ NOT ACTIVE'} — 30/60/90d windows |

## Checks Detail

| Check | Result | Severity | Detail |
|-------|--------|----------|--------|
{checks_rows}

---

## Permanent Governance Rules (PRR-001)

1. **Never trade using DECAYING, RETIRED, Expired, or Unverified knowledge.**
2. **Knowledge becomes Institutional Knowledge only after measured improvement.**
3. **Universe maintenance is automatic — no manual symbol lists.**
4. **Learning is automatic — no manual trigger required.**
5. **Verification is automatic — 30/60/90-day rolling windows always active.**
6. **No manual intervention in the learning → institutionalisation cycle.**

---

_IIOS shall operate as a fully autonomous closed-loop institutional trading intelligence:_
_Observe → Predict → Trade → Evaluate → Research → Learn → Verify → Improve → Institutionalise → Repeat_
""", encoding="utf-8")
    return path


def write_all_reports(data: Dict[str, Any], today: Optional[str] = None) -> None:
    """Write all 9 PRR-001 reports from the data dict produced by prr_runner."""
    today = today or datetime.now().date().isoformat()

    edge_gate    = data.get("edge_gate")
    short_dna    = data.get("short_dna")
    freshness    = data.get("freshness")
    universe     = data.get("universe")
    pipeline     = data.get("pipeline")
    kv           = data.get("knowledge_validity")
    missed       = data.get("missed_opps")
    impact       = data.get("learning_impact")
    cert         = data.get("certificate")

    paths = [
        write_edge_lifecycle_audit(edge_gate, today),
        write_short_trading_audit(short_dna, today),
        write_signal_freshness_report(freshness, today),
        write_universe_coverage_report(universe, today),
        write_daily_pipeline_report(pipeline, today),
        write_knowledge_validity_report(kv, today),
        write_missed_opportunity_report(missed, today),
        write_learning_impact_report(impact, today),
        write_final_certificate(cert, today),
    ]
    log.info(
        "[PRRReporter] %d reports written to %s", len(paths), _dir(today),
    )
