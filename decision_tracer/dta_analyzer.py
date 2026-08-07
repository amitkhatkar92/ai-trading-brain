"""
decision_tracer/dta_analyzer.py
=================================
DTA-001 — Decision Traceability Audit — Question Analyzer

Answers the 8 audit questions from a TraceBundle.
All answers are evidence-based only — no assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .dta_collector import TraceBundle, DNAMatch, EdgeMatch


@dataclass
class AuditAnswer:
    question: str
    answer:   str = ""
    evidence: List[str] = field(default_factory=list)
    verdict:  str = ""   # ANSWERED | PARTIAL | INSUFFICIENT


@dataclass
class DTAAudit:
    symbol:    str = ""
    timestamp: str = ""
    answers:   List[AuditAnswer] = field(default_factory=list)
    overall_confidence: float = 0.0
    overall_verdict:    str = ""


def _fmt_pct(v: float) -> str:
    return f"{v*100:.1f}%" if v <= 1.0 else f"{v:.1f}%"


def _fmt_conf(c: float) -> str:
    return f"{c:.2f}/10"


def analyze(bundle: TraceBundle) -> DTAAudit:
    audit = DTAAudit(symbol=bundle.symbol, timestamp=bundle.audit_ts)
    d     = bundle.decision
    feat  = bundle.features.features if bundle.features else {}

    # Pre-compute useful facts
    active_edges  = [e for e in bundle.edge_matches if e.status == "ACTIVE"]
    full_matches  = [e for e in bundle.edge_matches if e.all_satisfied]
    partial_edges = [e for e in bundle.edge_matches if not e.all_satisfied and e.satisfied_count > 0 and e.status == "ACTIVE"]
    dna_hits      = [m for m in bundle.dna_matches if m.matched]
    direction     = bundle.signal.direction if bundle.signal else (
                    "BUY" if d and d.decision == "APPROVED" else "")

    # ── Q1: Why BUY / Why this decision? ─────────────────────────────────────
    q1 = AuditAnswer(
        question="Why BUY? (or: What drove this decision?)",
        verdict="ANSWERED" if d else "INSUFFICIENT",
    )
    if d and d.decision == "APPROVED":
        q1.answer = (
            f"Decision APPROVED — {bundle.symbol} cleared all 12 decision layers. "
            f"Strategy: {d.strategy}. Final confidence: {_fmt_conf(d.confidence)}."
        )
        if bundle.signal:
            q1.evidence.append(
                f"Scanner signal: direction={bundle.signal.direction}  "
                f"initial_confidence={bundle.signal.confidence:.2f}  "
                f"strategy={bundle.signal.strategy}"
            )
        if bundle.market_ctx:
            ctx = bundle.market_ctx
            q1.evidence.append(
                f"Market context: regime={ctx.regime}  VIX={ctx.vix:.1f}  "
                f"breadth={ctx.breadth:.3f}  PCR={ctx.pcr:.2f}"
            )
        if full_matches:
            q1.evidence.append(
                f"Active edge fully satisfied: "
                + ", ".join(f"{e.name} (prec={_fmt_pct(e.precision)} oos_wr={_fmt_pct(e.oos_wr)})"
                            for e in full_matches[:3])
            )
        if dna_hits:
            winner = [m for m in dna_hits if m.category == "winner"]
            q1.evidence.append(
                f"DNA matches: {len(dna_hits)} total  {len(winner)} winner DNA  "
                f"avg_confidence={sum(m.confidence for m in dna_hits)/max(len(dna_hits),1):.3f}"
            )
        if d.position_modifier < 1.0:
            q1.evidence.append(
                f"Position modifier applied: {d.position_modifier:.2%} of full size "
                f"(risk-adjusted entry)"
            )
        q1.evidence.append(
            f"Decision engine score: {d.confidence:.2f}  "
            f"position_modifier={d.position_modifier:.3f}  "
            f"regime={d.regime}  VIX={d.vix:.1f}"
        )
    elif d and d.decision == "REJECTED":
        q1.answer = f"Decision REJECTED for {bundle.symbol}."
        q1.evidence.append(f"Rejection reason: {d.rejection_reason}")
        q1.evidence.append(f"Score: {d.confidence:.2f} (threshold not met)")
        if bundle.signal:
            q1.evidence.append(
                f"Initial scanner signal: {bundle.signal.direction} @ {bundle.signal.confidence:.2f} "
                f"— reduced to {d.confidence:.2f} after risk/regime adjustment"
            )
    else:
        q1.answer = f"No decision record found for {bundle.symbol}."

    audit.answers.append(q1)

    # ── Q2: Why not BUY yesterday? ───────────────────────────────────────────
    q2 = AuditAnswer(question="Why not BUY yesterday? (or: Why not the previous cycle?)")
    prev = bundle.prev_decision
    if not prev:
        q2.answer = "No prior decision record found for comparison."
        q2.verdict = "INSUFFICIENT"
    else:
        diff = bundle.prev_cycle_diff
        if prev.decision == "APPROVED":
            q2.answer = (
                f"Previous decision was also APPROVED at {prev.ts[:10]} — "
                f"the system was trading {bundle.symbol} across multiple cycles."
            )
            q2.verdict = "ANSWERED"
        else:
            reasons = []
            if "regime_changed" in diff:
                reasons.append(f"Regime changed: {diff['regime_changed']}")
            if "vix_changed" in diff:
                reasons.append(f"VIX changed: {diff['vix_changed']}")
            if "confidence_changed" in diff:
                reasons.append(f"Confidence changed: {diff['confidence_changed']}")
            if "strategy_changed" in diff:
                reasons.append(f"Strategy changed: {diff['strategy_changed']}")

            if reasons:
                q2.answer = (
                    f"Previous decision at {prev.ts[:10]} was {prev.decision}. "
                    f"Key changes: {'; '.join(reasons)}."
                )
                q2.evidence.extend(reasons)
            else:
                q2.answer = (
                    f"Previous decision at {prev.ts[:10]} was {prev.decision} "
                    f"with confidence {prev.confidence:.2f}. "
                    f"Conditions appear similar — entry threshold not reached."
                )
                q2.evidence.append(f"Previous rejection: {prev.rejection_reason[:200]}")
            q2.verdict = "ANSWERED"

    q2.evidence.append(
        f"Decision history: last {len(bundle.decision_history)} decisions — "
        + " | ".join(f"{r.ts[:10]}:{r.decision}" for r in bundle.decision_history[:5])
    )
    audit.answers.append(q2)

    # ── Q3: Why not BUY tomorrow? ─────────────────────────────────────────────
    q3 = AuditAnswer(question="Why not BUY tomorrow? (What conditions would block entry?)")
    q3.verdict = "ANSWERED"
    blockers = []

    if bundle.market_ctx:
        ctx = bundle.market_ctx
        if ctx.vix > 25:
            blockers.append(
                f"VIX={ctx.vix:.1f} is elevated. If VIX exceeds 45 the kill switch fires. "
                f"High volatility typically suppresses breakout performance."
            )
        if ctx.regime in ("volatile", "bear_market"):
            blockers.append(
                f"Current regime '{ctx.regime}' — if this persists tomorrow, "
                f"breakout/momentum strategies are de-weighted in strategy mix."
            )
        if not ctx.trading_allowed:
            blockers.append(
                f"Distortion flag is active ({ctx.distortion}). "
                f"Trading may be blocked or size reduced."
            )

    if d and d.confidence < 7.0:
        blockers.append(
            f"Current confidence {d.confidence:.2f} is close to threshold {d.confidence:.2f}. "
            f"Any degradation in momentum/volume features would push below 6.5 → REJECTED."
        )

    # Feature-specific warnings
    rsi = feat.get("rsi", 0)
    if rsi and float(rsi) > 70:
        blockers.append(
            f"RSI={float(rsi):.1f} — currently overbought. "
            f"If RSI remains >70 tomorrow, mean-reversion risk increases."
        )

    active_edge_conds = []
    for e in full_matches[:2]:
        active_edge_conds.append(
            f"Active edge '{e.name}' requires {e.total_count} conditions. "
            f"If any of these fail tomorrow, the edge no longer fires."
        )
        for c in e.conditions[:3]:
            active_edge_conds.append(
                f"  Condition: {c.get('feature')} {c.get('operator')} {c.get('threshold')} "
                f"(current: {feat.get(c.get('feature',''),'N/A')})"
            )
    blockers.extend(active_edge_conds)

    if not blockers:
        blockers.append(
            "No specific blockers identified based on current data. "
            "Entry tomorrow depends on regime stability, VIX, and feature freshness."
        )

    q3.answer = (
        f"Entry could be blocked tomorrow if: {'; '.join(blockers[:3])}. "
        f"Full conditions below."
    )
    q3.evidence.extend(blockers)
    audit.answers.append(q3)

    # ── Q4: What evidence contributed? ───────────────────────────────────────
    q4 = AuditAnswer(
        question="What evidence contributed to this decision?",
        verdict="ANSWERED",
    )
    evidence_items = []

    # Active edges
    if full_matches:
        for em in full_matches[:3]:
            evidence_items.append(
                f"ACTIVE EDGE '{em.name}': ALL {em.total_count} conditions satisfied  "
                f"precision={_fmt_pct(em.precision)}  sharpe={em.sharpe:.2f}  "
                f"oos_win_rate={_fmt_pct(em.oos_wr)}"
            )
    if active_edges and not full_matches:
        for em in active_edges[:3]:
            evidence_items.append(
                f"ACTIVE EDGE '{em.name}': {em.satisfied_count}/{em.total_count} conditions met"
            )

    # DNA matches
    winner_dna = [m for m in dna_hits if m.category == "winner" and m.direction == direction]
    loser_dna  = [m for m in bundle.dna_matches if m.category == "loser" and m.matched]
    if winner_dna:
        evidence_items.append(
            f"WINNER DNA: {len(winner_dna)} patterns matched — "
            + ", ".join(f"{m.feature_name}={m.feature_value:.3f}" for m in winner_dna[:3])
        )
    if loser_dna:
        evidence_items.append(
            f"LOSER DNA warning: {len(loser_dna)} loser patterns triggered — "
            + ", ".join(m.feature_name for m in loser_dna[:3])
        )

    # IKN references
    study_nodes = [r for r in bundle.ikn_refs if r.node_type in ("STUDY", "DISCOVERY")]
    if study_nodes:
        evidence_items.append(
            f"IKN KNOWLEDGE GRAPH: {len(study_nodes)} study/discovery nodes referenced — "
            + ", ".join(r.name[:40] for r in study_nodes[:3])
        )

    # Historical approval rate
    if bundle.decision_history:
        past_approved = sum(1 for r in bundle.decision_history if r.decision == "APPROVED")
        approval_rate = past_approved / len(bundle.decision_history) * 100
        evidence_items.append(
            f"HISTORICAL: {past_approved}/{len(bundle.decision_history)} past cycles APPROVED "
            f"({approval_rate:.0f}% historical approval rate for {bundle.symbol})"
        )

    # Studies
    if bundle.study_references:
        evidence_items.append(
            f"RESEARCH STUDIES: {len(bundle.study_references)} studies referenced patterns "
            f"matching current features"
        )
        evidence_items.extend(bundle.study_references[:3])

    # Confirmed hypothesis
    confirmed = [h for h in bundle.hypothesis_refs if h["status"] == "CONFIRMED"]
    if confirmed:
        evidence_items.append(
            f"CONFIRMED HYPOTHESIS: {confirmed[0]['id']} — {confirmed[0]['title']}"
        )

    q4.answer = f"{len(evidence_items)} evidence sources contributed to this decision."
    q4.evidence = evidence_items
    audit.answers.append(q4)

    # ── Q5: Confidence? ───────────────────────────────────────────────────────
    q5 = AuditAnswer(question="Confidence? (Score breakdown and components)")
    if d:
        q5.verdict = "ANSWERED"
        q5.answer  = (
            f"Final confidence: {_fmt_conf(d.confidence)}  "
            f"(threshold ≥6.5 for APPROVED, ≥6.8 for full-size)\n"
            f"  Position modifier: {d.position_modifier:.3f} × "
            f"({d.position_modifier*100:.0f}% of max position size)"
        )
        score_sources = []
        if bundle.signal:
            score_sources.append(
                f"Scanner raw score: {bundle.signal.confidence:.2f}/10 "
                f"({bundle.signal.strategy})"
            )
        score_sources.append(
            f"After risk/regime adjustment: {d.confidence:.2f}/10 "
            f"(modifier={d.position_modifier:.3f})"
        )
        if bundle.market_ctx:
            ctx = bundle.market_ctx
            dom = ctx.regime_probs.get("dominant", ctx.regime)
            score_sources.append(
                f"Regime probability: dominant={dom}  "
                f"bull={ctx.regime_probs.get('bull_trend', 0):.2f}  "
                f"range={ctx.regime_probs.get('range', 0):.2f}  "
                f"volatile={ctx.regime_probs.get('volatile', 0):.2f}"
            )
        # Key features affecting confidence
        key_feats = ["rsi", "macd_signal_norm", "volume_ratio_raw", "breadth",
                     "pcr", "atr_14", "adx_score", "avg_conviction"]
        feat_lines = []
        for kf in key_feats:
            v = feat.get(kf)
            if v is not None:
                feat_lines.append(f"{kf}={float(v):.3f}")
        if feat_lines:
            score_sources.append("Key feature values: " + "  ".join(feat_lines))

        q5.evidence = score_sources
    else:
        q5.answer  = f"No decision record — confidence cannot be computed."
        q5.verdict = "INSUFFICIENT"

    audit.answers.append(q5)

    # ── Q6: Risk? ─────────────────────────────────────────────────────────────
    q6 = AuditAnswer(question="Risk? (What risk factors were evaluated?)")
    if bundle.risk_ctx and d:
        rc = bundle.risk_ctx
        q6.verdict = "ANSWERED"
        risks = []

        # VIX
        if d.vix > 30:
            risks.append(f"HIGH VIX: {d.vix:.1f} (>30 = elevated risk environment)")
        elif d.vix > 20:
            risks.append(f"MODERATE VIX: {d.vix:.1f} (20–30 = watch zone)")
        else:
            risks.append(f"LOW VIX: {d.vix:.1f} (<20 = normal conditions)")

        # Regime
        risks.append(f"Regime: {d.regime}")

        # Position sizing
        if d.position_modifier < 1.0:
            risks.append(
                f"Risk-adjusted position: {d.position_modifier*100:.0f}% of max size "
                f"(regime/VIX reduction applied)"
            )

        # Portfolio state
        if rc.open_positions > 0:
            risks.append(f"Open positions: {rc.open_positions} (concentration risk)")
        if rc.drawdown_pct > 1.0:
            risks.append(f"Portfolio drawdown: {rc.drawdown_pct:.1f}% (monitoring)")

        # Risk checks
        if rc.risk_reasons:
            risks.append("Risk check flags: " + " | ".join(rc.risk_reasons[:3]))
        else:
            risks.append("Risk checks passed: all capital and position limits satisfied")

        # Kill switch thresholds
        risks.append(
            "Kill switch thresholds: VIX>45 (HALT all trading), "
            "daily_loss>2% (HALT), NIFTY_drop>-5% (HALT)"
        )

        q6.answer = (
            f"Risk status: {'PASS' if rc.risk_passed else 'FLAG'}  "
            f"Guardian: {'APPROVED' if rc.guardian_approved else 'BLOCKED'}  "
            f"Simulation: {'PASS' if rc.simulation_approved else 'REJECT'}"
        )
        q6.evidence = risks
    else:
        q6.answer  = "Risk context unavailable — no cycle events found."
        q6.verdict = "INSUFFICIENT"

    audit.answers.append(q6)

    # ── Q7: Alternative candidates? ───────────────────────────────────────────
    q7 = AuditAnswer(question="Alternative candidates? (What else was considered?)")
    alts = bundle.alternative_candidates
    if alts:
        q7.verdict = "ANSWERED"
        q7.answer  = (
            f"{len(alts)} alternative candidates were identified in the same cycle. "
            f"Top candidates by scanner confidence:"
        )
        for a in alts[:8]:
            q7.evidence.append(
                f"{a.symbol:<15} dir={a.direction:<6} "
                f"confidence={a.confidence:.2f}  strategy={a.strategy}"
            )
        # Show where RELIANCE ranked
        all_signals = sorted(
            alts + ([bundle.signal] if bundle.signal else []),
            key=lambda x: -x.confidence
        )
        rank = next((i+1 for i, s in enumerate(all_signals) if s.symbol == bundle.symbol), None)
        if rank:
            q7.evidence.append(
                f"{bundle.symbol} ranked #{rank} of {len(all_signals)} candidates "
                f"by initial scanner confidence"
            )
    else:
        q7.answer  = "No alternative candidates found in this cycle."
        q7.verdict = "PARTIAL"

    audit.answers.append(q7)

    # ── Q8: Expected learning if wrong? ──────────────────────────────────────
    q8 = AuditAnswer(
        question="Expected learning if wrong? (How will the system update if this trade fails?)",
        verdict="ANSWERED",
    )
    learning_steps = []

    # Strategy performance tracker
    strat = bundle.decision.strategy if bundle.decision else ""
    sp = bundle.strategy_perf
    if sp:
        learning_steps.append(
            f"STRATEGY TRACKER: '{strat}' currently has "
            f"trades={sp.get('total_trades',0)}  wins={sp.get('wins',0)}  "
            f"enabled={sp.get('enabled',True)}. "
            f"If this trade loses, win_rate declines and may trigger auto-disable."
        )
    else:
        learning_steps.append(
            f"STRATEGY TRACKER: Strategy '{strat}' will record the outcome. "
            f"If consecutive losses reach threshold, strategy is auto-disabled."
        )

    # DNA update
    matched_dna_names = [m.feature_name for m in dna_hits[:5]]
    if matched_dna_names:
        learning_steps.append(
            f"DNA UPDATE: Features {matched_dna_names} triggered DNA patterns. "
            f"A loss will reduce consensus_score and confidence of matched winner DNA. "
            f"If confidence falls below threshold, DNA transitions to RETIRED lifecycle."
        )

    # Edge learning
    if full_matches:
        em_names = [e.name for e in full_matches[:2]]
        learning_steps.append(
            f"EDGE LEARNING: Active edge(s) {em_names} were triggered. "
            f"A loss increments live_trades with live_wins unchanged, "
            f"degrading live_sharpe → edge transitions to DECAYING status."
        )

    # Hypothesis generation
    learning_steps.append(
        "HYPOTHESIS ENGINE: A failed trade in this regime/feature context "
        "may generate a new hypothesis (e.g., 'Breakout_Volume fails in high-VIX range markets'). "
        "This enters the hypothesis registry for next research study."
    )

    # Meta-learning
    if bundle.market_ctx and bundle.market_ctx.meta_top_strategy:
        learning_steps.append(
            f"META-LEARNING: Current top strategy is '{bundle.market_ctx.meta_top_strategy}'. "
            f"A loss will reduce its allocation weight in the next cycle's strategy mix."
        )

    # KNN update
    learning_steps.append(
        "KNN / REGIME MODEL: The (features → outcome) record will be added to the "
        "ML dataset for next model retrain. "
        "OOS improvement is measured in the next walk-forward evaluation."
    )

    q8.answer = (
        f"If this trade results in a loss, {len(learning_steps)} learning mechanisms activate:"
    )
    q8.evidence = learning_steps
    audit.answers.append(q8)

    # ── Overall ───────────────────────────────────────────────────────────────
    answered = sum(1 for a in audit.answers if a.verdict == "ANSWERED")
    total    = len(audit.answers)
    audit.overall_confidence = d.confidence if d else 0.0
    audit.overall_verdict    = (
        f"{answered}/{total} questions answered with evidence  |  "
        f"Decision: {d.decision if d else 'NOT_FOUND'}  |  "
        f"Confidence: {_fmt_conf(d.confidence) if d else 'N/A'}"
    )

    return audit
