"""
decision_tracer/dta_analyzer.py
=================================
DTA-001 — Decision Traceability Audit — Question Analyzer

Answers 10 audit questions from a TraceBundle.
All answers are evidence-based only — no assumptions.

Q1  Why was this stock selected?
Q2  Why were other stocks rejected?
Q3  Which knowledge (IKN) contributed?
Q4  Which DNA contributed?
Q5  Which PMCI factors mattered?
Q6  Which CDS factors mattered?
Q7  Which historical studies supported this?
Q8  Which hypotheses supported it?
Q9  What could have changed the decision?   ← counterfactual
Q10 If the trade loses, what exactly will be learned?
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .dta_collector import (
    TraceBundle, DNAMatch, EdgeMatch, RejectionRecord,
    _eval_condition as _eval_cond,
)


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


_APPROVAL_THRESHOLD = 6.5


def _build_counterfactual(bundle: TraceBundle, feat: dict,
                          full_matches: list, active_edges: list,
                          dna_hits: list) -> List[str]:
    """What single change would flip the decision?"""
    d = bundle.decision
    if not d:
        return ["No decision record — counterfactual cannot be computed."]

    items: List[str] = []

    if d.decision == "REJECTED":
        gap = _APPROVAL_THRESHOLD - d.confidence
        items.append(
            f"CONFIDENCE GAP: Need +{gap:.2f} points more to reach APPROVED threshold "
            f"({d.confidence:.2f} → {_APPROVAL_THRESHOLD})"
        )
        # Single-feature flips
        rsi = feat.get("rsi")
        if rsi and float(rsi) > 70:
            items.append(
                f"RSI FLIP: RSI={float(rsi):.1f} is overbought. "
                f"If RSI dropped to 65, overbought penalty removed → confidence would rise"
            )
        vol = feat.get("volume_ratio_raw")
        if vol and float(vol) < 1.5:
            items.append(
                f"VOLUME FLIP: volume_ratio={float(vol):.2f} is weak. "
                f"A 2× volume day (ratio≥2.0) would strengthen breakout signal"
            )
        # Closest missed edges
        for em in active_edges:
            if not em.all_satisfied and em.satisfied_count > 0:
                missed = [c for c in em.conditions if not _eval_cond(c, feat)]
                for c in missed[:2]:
                    curr = feat.get(c.get("feature", ""), "N/A")
                    thr  = c.get("threshold", 0)
                    op   = c.get("operator", "")
                    try:
                        gap_cond = abs(float(str(curr)) - float(thr))
                        items.append(
                            f"EDGE FLIP '{em.name}': {c.get('feature')} needs {op} {thr} "
                            f"(current={curr}, gap={gap_cond:.4f}) — "
                            f"satisfying this would unlock edge precision={_fmt_pct(em.precision)}"
                        )
                    except (ValueError, TypeError):
                        items.append(
                            f"EDGE FLIP '{em.name}': {c.get('feature')} needs {op} {thr} "
                            f"(current={curr})"
                        )
        # VIX / regime flip
        if bundle.market_ctx and bundle.market_ctx.vix > 22:
            vix_drop = bundle.market_ctx.vix - 20
            items.append(
                f"VIX FLIP: VIX={bundle.market_ctx.vix:.1f}. "
                f"If VIX dropped {vix_drop:.1f} pts to <20, position_modifier would increase "
                f"→ confidence adjustment improves"
            )
    else:  # APPROVED — what would cause rejection?
        buffer = d.confidence - _APPROVAL_THRESHOLD
        items.append(
            f"CONFIDENCE BUFFER: {buffer:.2f} pts above threshold. "
            f"Decision would flip to REJECTED if confidence fell to "
            f"< {_APPROVAL_THRESHOLD} (needs -{buffer:.2f})"
        )
        # Which satisfied edge conditions are closest to breaking?
        for em in full_matches[:2]:
            for c in em.conditions:
                curr = feat.get(c.get("feature", ""))
                if curr is not None:
                    try:
                        margin = abs(float(curr) - float(c.get("threshold", 0)))
                        if margin < 0.1:
                            items.append(
                                f"EDGE MARGIN '{em.name}': "
                                f"{c.get('feature')}={float(curr):.4f} is only "
                                f"{margin:.4f} units from breaking condition "
                                f"{c.get('operator')} {c.get('threshold')}"
                            )
                    except (ValueError, TypeError):
                        pass
        # Regime / VIX degradation
        if bundle.market_ctx:
            ctx = bundle.market_ctx
            if ctx.vix < 30:
                items.append(
                    f"VIX ESCALATION: If VIX rises from {ctx.vix:.1f} above 30, "
                    f"position_modifier decreases and confidence drops below threshold"
                )
            if ctx.regime in ("range_market",):
                items.append(
                    f"REGIME SHIFT: Current regime='{ctx.regime}'. "
                    f"If regime transitions to 'volatile' or 'bear_market', "
                    f"breakout strategy weight drops → confidence below threshold"
                )
        # DNA flip
        loser_close = [m for m in bundle.dna_matches if m.category == "loser"
                       and not m.matched and m.confidence > 0.7]
        if loser_close:
            items.append(
                f"DNA FLIP: {len(loser_close)} high-confidence loser DNA patterns "
                f"are NOT yet triggered. If "
                f"{', '.join(m.feature_name for m in loser_close[:3])} values shift "
                f"to loser range, decision could reverse"
            )

    if not items:
        items.append("No single-variable flip identified — decision is robust to small changes.")

    return items


def _build_loss_learning(bundle: TraceBundle, dna_hits: list,
                         full_matches: list) -> List[str]:
    """Name the exact records that will be updated if this trade loses."""
    d    = bundle.decision
    strat = d.strategy if d else ""
    steps: List[str] = []

    # 1. Strategy performance tracker — named strategy
    sp = bundle.strategy_perf
    if sp:
        steps.append(
            f"STRATEGY TRACKER ['{strat}']: "
            f"total_trades={sp.get('total_trades',0)+1}  wins stays at {sp.get('wins',0)}  "
            f"→ new win_rate={(sp.get('wins',0)/max(sp.get('total_trades',1)+1,1)*100):.1f}%  "
            f"(threshold for auto-disable: win_rate < 40% over last 10 trades)"
        )
    else:
        steps.append(
            f"STRATEGY TRACKER ['{strat}']: Will record 1 loss. "
            f"Auto-disable triggers if consecutive losses reach threshold."
        )

    # 2. DNA records — by ID
    winner_hits = [m for m in dna_hits if m.category == "winner"]
    if winner_hits:
        ids = [str(m.dna_id) for m in winner_hits[:6]]
        steps.append(
            f"DNA RECORDS (institutional_dna.db): "
            f"Winner DNA IDs [{', '.join(ids)}] will have consensus_score decremented. "
            f"Feature→outcome pair recorded as loss. "
            f"If confidence falls below 0.5, lifecycle transitions ESTABLISHED → DECAYING."
        )
    loser_hits = [m for m in bundle.dna_matches if m.category == "loser" and m.matched]
    if loser_hits:
        ids = [str(m.dna_id) for m in loser_hits[:4]]
        steps.append(
            f"DNA RECORDS — LOSER REINFORCEMENT: IDs [{', '.join(ids)}] will be reinforced "
            f"(this is a correct loser-DNA signal — increases their confidence score)"
        )

    # 3. Edge records — by name/ID
    if full_matches:
        for em in full_matches[:3]:
            steps.append(
                f"EDGE RECORD ['{em.name}' ID={em.edge_id}]: "
                f"live_trades +1, live_wins unchanged. "
                f"live_sharpe degrades. If below DECAYING threshold, "
                f"status transitions ACTIVE → DECAYING."
            )

    # 4. Hypothesis
    confirmed_hyps = [h for h in bundle.hypothesis_refs if h["status"] == "CONFIRMED"]
    proposed_hyps  = [h for h in bundle.hypothesis_refs if h["status"] == "PROPOSED"]
    if confirmed_hyps:
        h = confirmed_hyps[0]
        steps.append(
            f"HYPOTHESIS [{h['id']}] '{h['title'][:60]}': "
            f"Counter-evidence recorded. If confirmation_rate drops below 50%, "
            f"status may revert to PROPOSED."
        )
    if bundle.market_ctx and bundle.market_ctx.regime:
        steps.append(
            f"HYPOTHESIS ENGINE: New hypothesis auto-generated: "
            f"'{strat} BUY in {bundle.market_ctx.regime} with VIX={bundle.decision.vix:.1f} "
            f"has negative outcome' — enters registry for next study run."
        )

    # 5. Meta-learning
    if bundle.market_ctx and bundle.market_ctx.meta_top_strategy:
        steps.append(
            f"META-LEARNING (regime_strategy_map): "
            f"Strategy '{bundle.market_ctx.meta_top_strategy}' in regime "
            f"'{bundle.market_ctx.regime}' records 1 loss. "
            f"k-NN weight updated on next retrain. "
            f"Allocation weight reduces in subsequent cycle's strategy_mix."
        )

    # 6. IKN knowledge graph
    study_nodes = [r for r in bundle.ikn_refs if r.node_type in ("STUDY", "DISCOVERY")]
    if study_nodes:
        steps.append(
            f"IKN GRAPH: {len(study_nodes)} study/discovery nodes referenced this trade. "
            f"Loss outcome stored as evidence. "
            f"Edge confidence re-weighted in next IKN update cycle."
        )

    # 7. KNN model
    vix_str = f"{d.vix:.1f}" if d else "0"
    steps.append(
        f"KNN REGIME MODEL: Feature vector for {bundle.symbol} "
        f"(regime={d.regime if d else 'N/A'}, VIX={vix_str}) "
        f"added to training set with label=LOSS. "
        f"Model retrained in next walk-forward validation run."
    )

    return steps


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

    # ── Q2: Why were other stocks rejected? (Rejection Audit) ─────────────────
    q2 = AuditAnswer(
        question="Why were other stocks rejected? (Full scanner rejection audit)"
    )
    rejections = bundle.rejection_audit
    n_scanned  = bundle.scanner_universe_size
    n_rejected = sum(1 for r in rejections if r.decision_outcome in ("REJECTED", "NOT_DECIDED"))
    n_approved = sum(1 for r in rejections if r.decision_outcome == "APPROVED")

    if rejections:
        q2.verdict = "ANSWERED"
        q2.answer  = (
            f"{n_scanned} stocks were scanned this cycle. "
            f"Target ({bundle.symbol}) was selected. "
            f"{n_rejected} others rejected or pre-filtered; {n_approved} also approved. "
            f"Rejection reasons by stock:"
        )
        for r in rejections[:12]:
            gap_str = f"  gap_vs_target={r.vs_target_gap:+.2f}" if r.vs_target_gap else ""
            q2.evidence.append(
                f"{r.symbol:<16} scan_conf={r.scanner_confidence:.2f}  "
                f"outcome={r.decision_outcome:<12}{gap_str}  "
                f"→ {r.rejection_reason[:80]}"
            )
        # Rank target among scanned
        all_confs = [bundle.signal.confidence if bundle.signal else 0]
        all_confs += [r.scanner_confidence for r in rejections]
        all_confs.sort(reverse=True)
        target_conf = bundle.signal.confidence if bundle.signal else 0
        rank = sum(1 for c in all_confs if c > target_conf) + 1
        q2.evidence.append(
            f"{bundle.symbol} scanner rank: #{rank} of {n_scanned} stocks by initial confidence"
        )
    else:
        q2.answer  = "No rejection audit data — cycle events not available."
        q2.verdict = "INSUFFICIENT"

    audit.answers.append(q2)

    # ── Q3: Which knowledge (IKN) contributed? ────────────────────────────────
    q3 = AuditAnswer(question="Which knowledge (IKN) contributed to this decision?")
    dna_nodes  = [r for r in bundle.ikn_refs if r.node_type == "DNA"]
    stud_nodes = [r for r in bundle.ikn_refs if r.node_type in ("STUDY", "DISCOVERY", "FINDING")]
    hyp_nodes  = [r for r in bundle.ikn_refs if r.node_type == "HYPOTHESIS"]
    other_nodes= [r for r in bundle.ikn_refs if r.node_type not in ("DNA","STUDY","DISCOVERY","FINDING","HYPOTHESIS")]

    if bundle.ikn_refs:
        q3.verdict = "ANSWERED"
        q3.answer  = (
            f"IKN graph contributed {len(bundle.ikn_refs)} nodes: "
            f"{len(dna_nodes)} DNA, {len(stud_nodes)} study/discovery, "
            f"{len(hyp_nodes)} hypothesis, {len(other_nodes)} other."
        )
        for r in bundle.ikn_refs[:10]:
            rels = f" → {r.relationships[0][:50]}" if r.relationships else ""
            q3.evidence.append(f"[{r.node_type}] {r.name[:50]}{rels}")
    else:
        q3.answer  = "No IKN nodes matched current feature set."
        q3.verdict = "PARTIAL"

    audit.answers.append(q3)

    # ── Q4: Which DNA contributed? ────────────────────────────────────────────
    q4 = AuditAnswer(question="Which DNA patterns contributed to this decision?")
    winner_dna = [m for m in dna_hits if m.category == "winner"]
    loser_dna  = [m for m in bundle.dna_matches if m.category == "loser" and m.matched]
    hypo_dna   = [m for m in bundle.dna_matches if m.lifecycle in ("CONFIRMED_WINNER", "ESTABLISHED")]

    if dna_hits:
        q4.verdict = "ANSWERED"
        q4.answer  = (
            f"{len(dna_hits)}/{len(bundle.dna_matches)} DNA patterns matched. "
            f"Winner DNA: {len(winner_dna)}  Loser DNA warns: {len(loser_dna)}  "
            f"High-confidence (lifecycle=ESTABLISHED/CONFIRMED_WINNER): {len(hypo_dna)}"
        )
        for m in winner_dna[:6]:
            q4.evidence.append(
                f"[DNA#{m.dna_id} WINNER] {m.feature_name}={m.feature_value:.3f}  "
                f"conf={m.confidence:.3f}  lifecycle={m.lifecycle}"
            )
        for m in loser_dna[:3]:
            q4.evidence.append(
                f"[DNA#{m.dna_id} LOSER ⚠] {m.feature_name}={m.feature_value:.3f}  "
                f"conf={m.confidence:.3f}  lifecycle={m.lifecycle}"
            )
        if hypo_dna:
            q4.evidence.append(
                f"High-conviction DNA (established lifecycle): "
                + ", ".join(f"#{m.dna_id}" for m in hypo_dna[:5])
            )
    else:
        q4.answer  = "No DNA patterns matched. Decision made on scanner/edge signals only."
        q4.verdict = "PARTIAL"

    audit.answers.append(q4)

    # ── Q5: PMCI factor breakdown ─────────────────────────────────────────────
    q5 = AuditAnswer(question="Which PMCI factors mattered? (Scanner/signal sub-component scores)")
    if d:
        q5.verdict = "ANSWERED"
        pmci_factors = []

        # Signal-level score (composite PMCI)
        if bundle.signal:
            pmci_factors.append(
                f"PMCI composite score: {bundle.signal.confidence:.2f}/10  "
                f"(strategy={bundle.signal.strategy}  direction={bundle.signal.direction})"
            )

        # Momentum sub-score: mom_1d, mom_5d, mom_20d, adx_score
        mom_feats = {k: feat.get(k) for k in ("mom_1d", "mom_5d", "mom_20d", "adx_score") if feat.get(k) is not None}
        if mom_feats:
            pmci_factors.append(
                "MOMENTUM: " + "  ".join(f"{k}={float(v):.4f}" for k, v in mom_feats.items())
            )

        # Volume sub-score: volume_ratio_raw, volume_spike
        vol_feats = {k: feat.get(k) for k in ("volume_ratio_raw", "volume_spike") if feat.get(k) is not None}
        if vol_feats:
            pmci_factors.append(
                "VOLUME: " + "  ".join(f"{k}={float(v):.4f}" for k, v in vol_feats.items())
            )

        # Technical sub-score: rsi, macd_signal_norm, macd_bull, close_pos, intra_range
        tech_feats = {k: feat.get(k) for k in (
            "rsi", "rsi_overbought", "rsi_oversold",
            "macd_signal_norm", "macd_bull", "macd_bear",
            "close_pos", "intra_range", "atr_14"
        ) if feat.get(k) is not None}
        if tech_feats:
            pmci_factors.append(
                "TECHNICAL: " + "  ".join(f"{k}={float(v):.4f}" for k, v in tech_feats.items())
            )

        # Regime sub-score: regime_bull, regime_range, regime_score
        reg_feats = {k: feat.get(k) for k in ("regime_bull", "regime_range", "regime_score", "global_bias") if feat.get(k) is not None}
        if reg_feats:
            pmci_factors.append(
                "REGIME: " + "  ".join(f"{k}={float(v):.4f}" for k, v in reg_feats.items())
            )

        # Sentiment: breadth, pcr, sector_flow_count, avg_conviction
        sent_feats = {k: feat.get(k) for k in ("breadth", "pcr", "sector_flow_count", "avg_conviction") if feat.get(k) is not None}
        if sent_feats:
            pmci_factors.append(
                "SENTIMENT: " + "  ".join(f"{k}={float(v):.4f}" for k, v in sent_feats.items())
            )

        if full_matches:
            pmci_factors.append(
                f"EDGE CONFIRMATION: {len(full_matches)} active edge(s) fully satisfied — "
                + ", ".join(f"{e.name} (prec={_fmt_pct(e.precision)})" for e in full_matches[:3])
            )

        q5.answer = (
            f"PMCI composite: {bundle.signal.confidence:.2f}/10 "
            f"broken into {len(pmci_factors)} sub-factor groups below."
            if bundle.signal else "Scanner signal not available."
        )
        q5.evidence = pmci_factors
    else:
        q5.answer  = "No decision record — PMCI cannot be reconstructed."
        q5.verdict = "INSUFFICIENT"

    audit.answers.append(q5)

    # ── Q6: CDS factor breakdown ──────────────────────────────────────────────
    q6 = AuditAnswer(question="Which CDS factors mattered? (Decision engine sub-score breakdown)")
    if d:
        q6.verdict = "ANSWERED"
        cds_factors = []

        # The 4 CDS components stored in ct_decisions
        total = d.technical_score + d.risk_score + d.macro_score + d.regime_score
        if total > 0:
            cds_factors.append(
                f"TECHNICAL SCORE:  {d.technical_score:.4f}  "
                f"({d.technical_score/total*100:.0f}% weight)"
            )
            cds_factors.append(
                f"RISK SCORE:       {d.risk_score:.4f}  "
                f"({d.risk_score/total*100:.0f}% weight)"
            )
            cds_factors.append(
                f"MACRO SCORE:      {d.macro_score:.4f}  "
                f"({d.macro_score/total*100:.0f}% weight)"
            )
            cds_factors.append(
                f"REGIME SCORE:     {d.regime_score:.4f}  "
                f"({d.regime_score/total*100:.0f}% weight)"
            )
            cds_factors.append(
                f"WEIGHTED COMPOSITE → CONFIDENCE: {d.confidence:.4f}/10"
            )
        else:
            # Scores not separately stored — show what we have
            cds_factors.append(f"Final confidence: {d.confidence:.4f}/10")
            if bundle.signal:
                cds_factors.append(f"Scanner (pre-CDS): {bundle.signal.confidence:.2f}/10")
                delta = d.confidence - bundle.signal.confidence
                cds_factors.append(
                    f"CDS adjustment: {delta:+.2f} "
                    f"({'increased by risk/regime' if delta >= 0 else 'reduced by risk/regime filters'})"
                )

        # Position modifier breakdown
        cds_factors.append(
            f"POSITION MODIFIER: {d.position_modifier:.3f} "
            f"({d.position_modifier*100:.0f}% of max position) — "
            f"applied by regime ({d.regime}) and VIX ({d.vix:.1f})"
        )

        # Strategy attribution
        if bundle.market_ctx and bundle.market_ctx.strategy_mix:
            top = sorted(bundle.market_ctx.strategy_mix.items(), key=lambda x: -x[1])[:3]
            cds_factors.append(
                "STRATEGY ALLOCATION (meta-learning weights): "
                + "  ".join(f"{s}={w:.3f}" for s, w in top)
            )

        q6.answer = (
            f"CDS final score: {d.confidence:.2f}/10 via 4 sub-components "
            f"(technical + risk + macro + regime). "
            f"Position modifier: {d.position_modifier:.0%} of max size."
        )
        q6.evidence = cds_factors
    else:
        q6.answer  = "No decision record — CDS cannot be reconstructed."
        q6.verdict = "INSUFFICIENT"

    audit.answers.append(q6)

    # ── Q7: Historical studies ────────────────────────────────────────────────
    q7 = AuditAnswer(question="Which historical studies supported this decision?")
    study_nodes = [r for r in bundle.ikn_refs if r.node_type in ("STUDY", "DISCOVERY", "FINDING")]
    if bundle.study_references or study_nodes:
        q7.verdict = "ANSWERED"
        q7.answer  = (
            f"{len(bundle.study_references)} study files and "
            f"{len(study_nodes)} IKN study nodes reference features in this decision."
        )
        for ref in bundle.study_references[:5]:
            q7.evidence.append(ref)
        for r in study_nodes[:3]:
            q7.evidence.append(f"IKN [{r.node_type}] {r.name[:60]}")
    else:
        q7.answer  = "No study references matched current feature set."
        q7.verdict = "PARTIAL"

    audit.answers.append(q7)

    # ── Q8: Hypotheses ───────────────────────────────────────────────────────
    q8 = AuditAnswer(question="Which hypotheses supported this decision?")
    confirmed = [h for h in bundle.hypothesis_refs if h["status"] == "CONFIRMED"]
    proposed  = [h for h in bundle.hypothesis_refs if h["status"] == "PROPOSED"]
    hyp_nodes = [r for r in bundle.ikn_refs if r.node_type == "HYPOTHESIS"]

    if confirmed or proposed or hyp_nodes:
        q8.verdict = "ANSWERED"
        q8.answer  = (
            f"{len(confirmed)} confirmed + {len(proposed)} proposed hypotheses in registry. "
            f"{len(hyp_nodes)} hypothesis IKN nodes matched features."
        )
        for h in confirmed[:3]:
            q8.evidence.append(f"✓ CONFIRMED [{h['id']}] {h['title']} (conf={h.get('confidence','')})")
        for h in proposed[:5]:
            q8.evidence.append(f"○ PROPOSED  [{h['id']}] {h['title']}")
        for r in hyp_nodes[:3]:
            q8.evidence.append(f"IKN [{r.node_type}] {r.name[:60]}")
    else:
        q8.answer  = "No hypotheses matched current feature context."
        q8.verdict = "PARTIAL"

    audit.answers.append(q8)

    # ── Q9: What could have changed the decision? (COUNTERFACTUAL) ────────────
    q9 = AuditAnswer(question="What could have changed the decision? (Sensitivity / counterfactual)")
    q9.verdict = "ANSWERED"
    cf_items = _build_counterfactual(bundle, feat, full_matches, active_edges, dna_hits)
    q9.answer = (
        f"{len(cf_items)} counterfactual conditions identified that could flip "
        f"this decision from {d.decision if d else 'N/A'} to the opposite outcome."
    )
    q9.evidence = cf_items
    audit.answers.append(q9)

    # ── Q10: If loses, what exactly will be learned? ──────────────────────────
    q10 = AuditAnswer(
        question="If this trade loses, what EXACTLY will be learned? (Named records)",
        verdict="ANSWERED",
    )
    learning_steps = _build_loss_learning(bundle, dna_hits, full_matches)
    q10.answer = (
        f"If this trade results in a loss, {len(learning_steps)} specific "
        f"knowledge records will be updated (named below)."
    )
    q10.evidence = learning_steps
    audit.answers.append(q10)

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
