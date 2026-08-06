"""
methodology_auditor.py — Scientific Methodology Audit for IIOS Research.

IRP-002A — Methodology Governance Enhancement.

Every research study must pass a methodology audit BEFORE evidence collection.
The audit detects the three confounds identified in H001 meta-validation:
  1. Missing control group
  2. Methodological asymmetry
  3. Inverted proxy variables

Plus four additional systematic checks:
  4. Sample size / statistical power
  5. Validation symmetry
  6. Independent replication readiness
  7. Bias detection (directional / sector / regime / time-period)

Audit result:
  PASS              — all checks pass; conclusion promotable to Institutional Knowledge
  PASS_WITH_LIMITS  — minor gaps; conclusion promotable with documented caveats
  FAIL              — critical gap detected; research may proceed but promotion blocked

This module has NO side effects on the knowledge stores.
It reads only; it never writes.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ─── constants ───────────────────────────────────────────────────────────────

# Minimum feature records for 80% power at δ=0.10 effect size (approximate)
MIN_RECORDS_FOR_POWER = 400
# Minimum records for definitive conclusion (z-score ≥ 1.96 at 95%)
MIN_RECORDS_DEFINITIVE = 1500
# Minimum replication studies for independent confirmation
MIN_REPLICATION_STUDIES = 2
# Maximum directional imbalance before flagging BUY/SELL bias
MAX_DIR_IMBALANCE = 0.80  # >80% in one direction = biased
# Maximum single-sector concentration before flagging sector bias
MAX_SECTOR_CONCENTRATION = 0.70


# ─── enumerations ────────────────────────────────────────────────────────────

class AuditVerdict(str, Enum):
    PASS             = "PASS"
    PASS_WITH_LIMITS = "PASS_WITH_LIMITATIONS"
    FAIL             = "FAIL"


class CheckStatus(str, Enum):
    PASS    = "PASS"
    WARNING = "WARNING"
    FAIL    = "FAIL"
    SKIP    = "SKIP"


# ─── data models ─────────────────────────────────────────────────────────────

@dataclass
class AuditCheck:
    """Result of one individual audit check."""
    check_id:    str
    name:        str
    status:      CheckStatus
    finding:     str
    detail:      str = ""
    is_critical: bool = False   # FAIL on a critical check blocks promotion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id":    self.check_id,
            "name":        self.name,
            "status":      self.status.value,
            "finding":     self.finding,
            "detail":      self.detail,
            "is_critical": self.is_critical,
        }


@dataclass
class AuditResult:
    """Complete methodology audit result for one research study."""
    study_id:          str
    study_title:       str
    audit_date:        str
    verdict:           AuditVerdict
    promotion_blocked: bool                  # True when verdict is FAIL
    checks:            List[AuditCheck]      = field(default_factory=list)
    limitations:       List[str]             = field(default_factory=list)
    confounds_detected: List[str]            = field(default_factory=list)
    proxy_issues:      List[str]             = field(default_factory=list)
    bias_flags:        List[str]             = field(default_factory=list)
    n_pass:            int = 0
    n_warning:         int = 0
    n_fail:            int = 0
    n_skip:            int = 0
    sample_size:       int = 0
    power_estimate:    float = 0.0           # estimated statistical power (0–1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_id":           self.study_id,
            "study_title":        self.study_title,
            "audit_date":         self.audit_date,
            "verdict":            self.verdict.value,
            "promotion_blocked":  self.promotion_blocked,
            "n_pass":             self.n_pass,
            "n_warning":          self.n_warning,
            "n_fail":             self.n_fail,
            "n_skip":             self.n_skip,
            "sample_size":        self.sample_size,
            "power_estimate":     round(self.power_estimate, 3),
            "limitations":        self.limitations,
            "confounds_detected": self.confounds_detected,
            "proxy_issues":       self.proxy_issues,
            "bias_flags":         self.bias_flags,
            "checks":             [c.to_dict() for c in self.checks],
        }

    @property
    def summary_line(self) -> str:
        return (
            f"verdict={self.verdict.value}  "
            f"pass={self.n_pass} warn={self.n_warning} fail={self.n_fail}  "
            f"power={self.power_estimate:.0%}  "
            f"promotion_blocked={self.promotion_blocked}"
        )


# ─── auditor ─────────────────────────────────────────────────────────────────

class MethodologyAuditor:
    """Performs the 7-check methodology audit on a research study plan.

    Parameters
    ----------
    knowledge_provider : KnowledgeProvider | None
        Used for bias detection and replication readiness checks.
        If None, those checks are SKIP'd rather than failing.
    """

    def __init__(self, knowledge_provider: Optional[Any] = None) -> None:
        self._kp = knowledge_provider

    def audit(self, study_plan: Any) -> AuditResult:
        """Run all 7 checks and return a complete AuditResult.

        Parameters
        ----------
        study_plan : StudyPlan | Any
            The study plan to audit. Reads attributes gracefully.
        """
        study_id    = str(getattr(study_plan, "plan_id", "unknown"))
        study_title = str(getattr(study_plan, "title", "Untitled study"))
        audit_date  = datetime.now().strftime("%Y-%m-%d")

        checks: List[AuditCheck] = []
        checks.append(self._check_control_group(study_plan))
        checks.append(self._check_method_symmetry(study_plan))
        checks.append(self._check_proxy_validation(study_plan))
        checks.append(self._check_sample_size(study_plan))
        checks.append(self._check_validation_symmetry(study_plan))
        checks.append(self._check_replication_readiness(study_plan))
        checks.append(self._check_bias(study_plan))

        n_pass    = sum(1 for c in checks if c.status == CheckStatus.PASS)
        n_warning = sum(1 for c in checks if c.status == CheckStatus.WARNING)
        n_fail    = sum(1 for c in checks if c.status == CheckStatus.FAIL)
        n_skip    = sum(1 for c in checks if c.status == CheckStatus.SKIP)

        critical_fails = [c for c in checks if c.status == CheckStatus.FAIL and c.is_critical]

        # Verdict determination
        if critical_fails:
            verdict = AuditVerdict.FAIL
        elif n_fail > 0 or n_warning >= 3:
            verdict = AuditVerdict.PASS_WITH_LIMITS
        else:
            verdict = AuditVerdict.PASS

        promotion_blocked = (verdict == AuditVerdict.FAIL)

        # Aggregate issues
        limitations    = [c.finding for c in checks if c.status in (CheckStatus.WARNING, CheckStatus.FAIL)]
        confounds      = [c.finding for c in checks if c.status == CheckStatus.FAIL and c.is_critical]
        proxy_issues   = [c.detail for c in checks if c.check_id == "C03" and c.status != CheckStatus.PASS]
        bias_flags     = [c.detail for c in checks if c.check_id == "C07" and c.status != CheckStatus.PASS]

        # Sample size from check C04
        c04 = next((c for c in checks if c.check_id == "C04"), None)
        sample_size   = int(c04.meta.get("n", 0)) if c04 and hasattr(c04, "meta") else 0
        power_est     = float(c04.meta.get("power", 0.0)) if c04 and hasattr(c04, "meta") else 0.0

        result = AuditResult(
            study_id=study_id,
            study_title=study_title,
            audit_date=audit_date,
            verdict=verdict,
            promotion_blocked=promotion_blocked,
            checks=checks,
            limitations=limitations,
            confounds_detected=confounds,
            proxy_issues=proxy_issues,
            bias_flags=bias_flags,
            n_pass=n_pass,
            n_warning=n_warning,
            n_fail=n_fail,
            n_skip=n_skip,
            sample_size=sample_size,
            power_estimate=power_est,
        )

        log.info(
            "[MA] Audit complete study_id=%s verdict=%s pass=%d warn=%d fail=%d",
            study_id, verdict.value, n_pass, n_warning, n_fail,
        )
        return result

    # ─── check 1: Control Group ───────────────────────────────────────────────

    def _check_control_group(self, plan: Any) -> AuditCheck:
        """Does the study have a defined comparison / control group?"""
        desc   = str(getattr(plan, "description", "") or "").lower()
        title  = str(getattr(plan, "title", "") or "").lower()
        tasks  = getattr(plan, "tasks", []) or []
        tasks_text = " ".join(str(t) for t in tasks).lower()

        control_signals = [
            "control group", "comparison group", "baseline",
            "symmetric", "vs ", "versus", "compared to", "benchmark",
            "reference group", "winner dna", "loser dna",
        ]

        found = [s for s in control_signals if s in desc + title + tasks_text]

        if found:
            return AuditCheck(
                check_id="C01", name="Control Group",
                status=CheckStatus.PASS,
                finding=f"Comparison group declared: {found[0]!r}",
                detail=f"Signals found: {found}",
                is_critical=False,
            )

        # If no comparison group keyword — warning for descriptive studies, fail for validation
        study_type = str(getattr(getattr(plan, "study_type", None), "value",
                                 getattr(plan, "study_type", "UNKNOWN"))).upper()
        is_validation = any(v in study_type for v in ("VALID", "COMPARA", "HYPOTHESIS"))

        status  = CheckStatus.FAIL if is_validation else CheckStatus.WARNING
        finding = ("No comparison group detected. "
                   "Validation studies require a control group to prevent unilateral bias.")
        return AuditCheck(
            check_id="C01", name="Control Group",
            status=status,
            finding=finding,
            detail=f"study_type={study_type}. Add explicit comparison or baseline to study plan.",
            is_critical=is_validation,
        )

    # ─── check 2: Method Symmetry ─────────────────────────────────────────────

    def _check_method_symmetry(self, plan: Any) -> AuditCheck:
        """Are identical methods applied to both groups?"""
        desc  = str(getattr(plan, "description", "") or "").lower()
        title = str(getattr(plan, "title", "") or "").lower()
        text  = desc + title

        symmetry_signals   = ["identical method", "same method", "symmetric", "same threshold",
                               "same lift", "same year", "same confidence", "irp-002", "feature_match only"]
        asymmetry_signals  = ["edge_lifecycle", "proxy method", "alternative method",
                               "different threshold", "different year"]

        sym_found  = any(s in text for s in symmetry_signals)
        asym_found = any(s in text for s in asymmetry_signals)

        if sym_found and not asym_found:
            return AuditCheck(
                check_id="C02", name="Method Symmetry",
                status=CheckStatus.PASS,
                finding="Symmetric methodology declared in study plan.",
                detail="Explicit symmetry language detected.",
                is_critical=False,
            )
        if asym_found:
            return AuditCheck(
                check_id="C02", name="Method Symmetry",
                status=CheckStatus.WARNING,
                finding="Asymmetric method signals detected. Verify both groups use identical evaluation.",
                detail=f"Asymmetry terms found in plan: {[s for s in asymmetry_signals if s in text]}",
                is_critical=False,
            )
        return AuditCheck(
            check_id="C02", name="Method Symmetry",
            status=CheckStatus.WARNING,
            finding="Method symmetry not explicitly declared in study plan.",
            detail="Add explicit statement that identical methods apply to both groups.",
            is_critical=False,
        )

    # ─── check 3: Proxy Validation ────────────────────────────────────────────

    def _check_proxy_validation(self, plan: Any) -> AuditCheck:
        """Are all proxy variables measuring the intended phenomenon?"""
        desc  = str(getattr(plan, "description", "") or "").lower()
        tasks = str(getattr(plan, "tasks", "") or "").lower()
        text  = desc + tasks

        # Known problematic proxy patterns
        bad_proxies = {
            "edge_lifecycle":  "BUY-edge-decay, not loser DNA persistence (all 132 DECAYING edges are BUY)",
            "decaying edges":  "May be BUY-direction only — check direction distribution before using as SHORT proxy",
            "candidate edges": "CANDIDATE status reflects research queue, not DNA validity",
        }

        found_bad: List[Tuple[str, str]] = [
            (proxy, reason) for proxy, reason in bad_proxies.items() if proxy in text
        ]

        explicit_proxy_ok = any(s in text for s in ["feature_match only", "no proxy", "direct measurement",
                                                      "no edge_lifecycle", "feature match"])

        if found_bad and not explicit_proxy_ok:
            issues = "; ".join(f"{p}: {r}" for p, r in found_bad)
            return AuditCheck(
                check_id="C03", name="Proxy Validation",
                status=CheckStatus.FAIL,
                finding="Invalid proxy variable(s) detected in study plan.",
                detail=issues,
                is_critical=True,
            )
        if explicit_proxy_ok:
            return AuditCheck(
                check_id="C03", name="Proxy Validation",
                status=CheckStatus.PASS,
                finding="Direct measurement declared — no proxy variables.",
                detail="feature_match or equivalent direct method specified.",
                is_critical=False,
            )
        return AuditCheck(
            check_id="C03", name="Proxy Validation",
            status=CheckStatus.WARNING,
            finding="Proxy variable usage not declared. Confirm no inverted proxies are in use.",
            detail="Explicitly state measurement method (feature_match / direct observation).",
            is_critical=False,
        )

    # ─── check 4: Sample Size ─────────────────────────────────────────────────

    def _check_sample_size(self, plan: Any) -> AuditCheck:
        """Is statistical power sufficient for the planned comparison?"""
        n = 0
        source = "unknown"

        # Try knowledge provider first
        if self._kp:
            try:
                feats = self._kp.list_features()
                n = len(feats) if feats else 0
                source = "KnowledgeProvider"
            except Exception:
                pass

        # Fall back to plan metadata
        if n == 0:
            rd = getattr(plan, "required_data", None)
            if rd:
                n = int(getattr(rd, "min_samples", 0) or 0)
                if n == 0:
                    n = int(getattr(rd, "n_records", 0) or 0)
                source = "plan.required_data"

        # Approximate power at δ=0.10 (typical lift difference) using normal approximation
        # z_alpha=1.645 (one-tailed 95%), z_beta=0.842 (80% power)
        # n_required ≈ 2*(z_alpha+z_beta)^2 / delta^2
        # For delta=0.10: n_required ≈ 2*(2.487)^2 / 0.01 ≈ 1237 per group
        if n >= MIN_RECORDS_DEFINITIVE:
            power = 0.95
            status = CheckStatus.PASS
            finding = f"Sample size sufficient: n={n} ({source})."
        elif n >= MIN_RECORDS_FOR_POWER:
            # Rough power estimation
            delta = 0.10
            z = (math.sqrt(n / 2) * delta) / 0.333 if n > 0 else 0
            power = min(0.90, max(0.50, 0.5 + 0.5 * math.erf(z / math.sqrt(2) - 1.28)))
            status = CheckStatus.WARNING
            finding = (f"Sample size marginal: n={n} ({source}). "
                       f"Estimated power ≈ {power:.0%} at δ=0.10 effect size.")
        elif n > 0:
            power = max(0.10, n / MIN_RECORDS_DEFINITIVE * 0.80)
            status = CheckStatus.FAIL
            finding = (f"Insufficient sample size: n={n} ({source}). "
                       f"Minimum {MIN_RECORDS_FOR_POWER} recommended, {MIN_RECORDS_DEFINITIVE} for definitive conclusion.")
        else:
            power = 0.0
            status = CheckStatus.SKIP
            finding = "Sample size unknown — cannot assess statistical power."

        c = AuditCheck(
            check_id="C04", name="Sample Size & Statistical Power",
            status=status,
            finding=finding,
            detail=f"n={n}  power≈{power:.0%}  min_recommended={MIN_RECORDS_FOR_POWER}  definitive={MIN_RECORDS_DEFINITIVE}",
            is_critical=False,
        )
        c.meta = {"n": n, "power": power}  # type: ignore[attr-defined]
        return c

    # ─── check 5: Validation Symmetry ────────────────────────────────────────

    def _check_validation_symmetry(self, plan: Any) -> AuditCheck:
        """Same years, thresholds, and confidence rules applied to all groups?"""
        desc  = str(getattr(plan, "description", "") or "").lower()
        tasks = str(getattr(plan, "tasks", "") or "").lower()
        text  = desc + tasks

        year_sym   = any(s in text for s in ["2025", "2026", "train", "valid", "same year"])
        thresh_sym = any(s in text for s in ["1.15", "0.65", "chi-sq", "threshold", "lift"])
        conf_sym   = any(s in text for s in ["confidence", "0.15", "alpha"])

        declared = sum([year_sym, thresh_sym, conf_sym])

        if declared >= 2:
            return AuditCheck(
                check_id="C05", name="Validation Symmetry",
                status=CheckStatus.PASS,
                finding="Training/validation split and thresholds declared.",
                detail=f"year_split={year_sym}  thresholds={thresh_sym}  confidence={conf_sym}",
                is_critical=False,
            )
        return AuditCheck(
            check_id="C05", name="Validation Symmetry",
            status=CheckStatus.WARNING,
            finding="Validation parameters not fully declared in study plan.",
            detail="Explicitly document: training year, validation year, lift threshold, stability threshold.",
            is_critical=False,
        )

    # ─── check 6: Independent Replication ────────────────────────────────────

    def _check_replication_readiness(self, plan: Any) -> AuditCheck:
        """Can the conclusion be independently verified by another study?"""
        n_studies = 0
        if self._kp:
            try:
                studies = self._kp.list_studies()
                n_studies = len(studies) if studies else 0
            except Exception:
                pass

        if n_studies >= MIN_REPLICATION_STUDIES:
            return AuditCheck(
                check_id="C06", name="Independent Replication",
                status=CheckStatus.PASS,
                finding=f"Replication possible: {n_studies} studies in knowledge base.",
                detail=f"CrossStudySynthesizer can identify corroborating findings across {n_studies} studies.",
                is_critical=False,
            )
        if n_studies > 0:
            return AuditCheck(
                check_id="C06", name="Independent Replication",
                status=CheckStatus.WARNING,
                finding=f"Replication limited: only {n_studies} study in knowledge base.",
                detail="Schedule a replication study before promoting to Institutional Knowledge.",
                is_critical=False,
            )
        return AuditCheck(
            check_id="C06", name="Independent Replication",
            status=CheckStatus.SKIP,
            finding="Replication status unknown — knowledge provider unavailable.",
            detail="Provide KnowledgeProvider to enable replication readiness check.",
            is_critical=False,
        )

    # ─── check 7: Bias Detection ──────────────────────────────────────────────

    def _check_bias(self, plan: Any) -> AuditCheck:
        """Detect directional, sector, regime, time-period, and selection bias."""
        flags: List[str] = []
        detail_parts: List[str] = []

        if not self._kp:
            c = AuditCheck(
                check_id="C07", name="Bias Detection",
                status=CheckStatus.SKIP,
                finding="Bias check skipped — knowledge provider unavailable.",
                detail="Provide KnowledgeProvider to enable bias detection.",
                is_critical=False,
            )
            c.detail = ""
            return c

        # ── Directional bias (BUY vs SELL in edge library) ───────────────────
        try:
            edges = self._kp.list_edges()
            if edges:
                buy_count  = sum(1 for e in edges if str(getattr(e, "direction", "")).upper() in ("BUY", "LONG"))
                sell_count = sum(1 for e in edges if str(getattr(e, "direction", "")).upper() in ("SELL", "SHORT"))
                total_dir  = buy_count + sell_count
                if total_dir > 0:
                    buy_frac = buy_count / total_dir
                    if buy_frac > MAX_DIR_IMBALANCE:
                        flags.append(f"BUY bias: {buy_frac:.0%} of edges are BUY ({buy_count}/{total_dir})")
                        detail_parts.append(
                            f"BUY={buy_count} SELL={sell_count} — "
                            "edge_lifecycle proxy is invalid for SHORT patterns due to this imbalance"
                        )
                    elif (1 - buy_frac) > MAX_DIR_IMBALANCE:
                        flags.append(f"SELL bias: {(1-buy_frac):.0%} of edges are SELL ({sell_count}/{total_dir})")
        except Exception as e:
            detail_parts.append(f"Directional bias check error: {e}")

        # ── Feature record time-period bias ──────────────────────────────────
        try:
            feats = self._kp.list_features()
            if feats:
                years: Dict[str, int] = {}
                for f in feats:
                    yr = str(getattr(f, "ts", "") or "")[:4]
                    if yr.isdigit():
                        years[yr] = years.get(yr, 0) + 1
                total_f = len(feats)
                most_common_yr, most_common_n = max(years.items(), key=lambda x: x[1]) if years else ("?", 0)
                if total_f > 0 and most_common_n / total_f > 0.80:
                    flags.append(f"Time-period bias: {most_common_n/total_f:.0%} of records from {most_common_yr}")
                elif len(years) == 1:
                    yr_only = next(iter(years))
                    flags.append(f"Single-year feature records: all {total_f} records from {yr_only}")
                    detail_parts.append(f"Only {yr_only} available — cross-year validation limited to 1 train + 1 valid year")
        except Exception as e:
            detail_parts.append(f"Time-period bias check error: {e}")

        # ── Regime bias ───────────────────────────────────────────────────────
        try:
            feats = self._kp.list_features()
            if feats:
                regimes: Dict[str, int] = {}
                for f in feats:
                    r = str(getattr(f, "regime", "") or "unknown")
                    regimes[r] = regimes.get(r, 0) + 1
                total_r = sum(regimes.values())
                if total_r > 0:
                    top_regime, top_n = max(regimes.items(), key=lambda x: x[1])
                    if top_n / total_r > MAX_DIR_IMBALANCE:
                        flags.append(f"Regime bias: {top_n/total_r:.0%} of records in {top_regime!r}")
                        detail_parts.append(f"Regime distribution: {dict(regimes)}")
        except Exception as e:
            detail_parts.append(f"Regime bias check error: {e}")

        # ── Selection bias: feature records source ────────────────────────────
        try:
            feats = self._kp.list_features()
            if feats:
                sources: Dict[str, int] = {}
                for f in feats:
                    s = str(getattr(f, "source", "") or "unknown")
                    sources[s] = sources.get(s, 0) + 1
                if len(sources) == 1:
                    src = next(iter(sources))
                    flags.append(f"Selection bias: all records from single source {src!r}")
                    detail_parts.append("Diversify feature record sources for robustness.")
        except Exception as e:
            detail_parts.append(f"Selection bias check error: {e}")

        if not flags:
            return AuditCheck(
                check_id="C07", name="Bias Detection",
                status=CheckStatus.PASS,
                finding="No material bias detected.",
                detail="; ".join(detail_parts) if detail_parts else "All bias checks passed.",
                is_critical=False,
            )

        # If directional bias (the critical one from H001), it's a FAIL
        has_dir_bias = any("bias" in f.lower() and ("buy" in f.lower() or "sell" in f.lower()) for f in flags)
        status = CheckStatus.FAIL if has_dir_bias else CheckStatus.WARNING

        c = AuditCheck(
            check_id="C07", name="Bias Detection",
            status=status,
            finding=f"Bias detected: {'; '.join(flags)}",
            detail="; ".join(detail_parts),
            is_critical=has_dir_bias,
        )
        c.detail = "; ".join(flags + detail_parts)
        return c
