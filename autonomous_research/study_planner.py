"""
study_planner.py — Scientific experiment design engine.

ARS Phase 2D.

Responsibilities:
    Convert validated research priorities (RoadmapEntry, KnowledgeGap,
    ScientificHypothesis) into fully specified, executable StudyPlan objects.
    Classify study risk and approval requirements.
    Validate plan dependencies.
    Maintain an in-session plan registry.

Explicitly NOT responsible for:
    Executing studies.
    Modifying knowledge stores, hypotheses, or roadmaps.
    Generating hypotheses.
    Any write operations except appending to in-memory plan registry.

Ten study types:
    HISTORICAL_REPLAY  — replay over a historical date range
    DNA_DISCOVERY      — extract winner/loser DNA patterns
    REGIME_ANALYSIS    — regime-conditional behaviour analysis
    SECTOR_RESEARCH    — sector-specific research
    EDGE_VALIDATION    — validate or invalidate a trading edge
    CROSS_VALIDATION   — resolve contradictions via controlled comparison
    FEATURE_IMPORTANCE — rank feature contributions
    PATTERN_MINING     — scan for new patterns
    META_LEARNING      — learn from prior study results
    CUSTOM             — user-defined study

Approval Classes:
    CLASS_A — standard types, LOW/MEDIUM risk → routine review
    CLASS_B — META_LEARNING / CUSTOM / HIGH risk → explicit Scientific Director approval

Plan ID is deterministic:
    SP-{sha256(f"{study_type}:{title.strip()}:{source_key}")[:8].upper()}
"""
from __future__ import annotations

import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .evidence_validator import EvidenceValidator
from .gap_detector import GapDetector
from .gap_models import GapCategory, GapSeverity, KnowledgeGap
from .hypothesis_models import HypothesisClassification, ScientificHypothesis
from .hypothesis_registry import HypothesisRegistry
from .knowledge_provider import KnowledgeProvider
from .roadmap_manager import RoadmapManager
from .roadmap_models import RoadmapEntry
from .study_planner_models import (
    ApprovalClass,
    DatasetRequirement,
    ExecutionEstimate,
    PlanningStatistics,
    PlanStatus,
    RiskClass,
    StudyDependency,
    StudyPlan,
    StudyPlannerConfig,
    StudyPlannerError,
    StudyPlanNotFoundError,
    StudyPortfolio,
    StudyTask,
    StudyType,
    ValidationPlan,
)

logger = logging.getLogger(__name__)


# ─── module-level lookup tables ───────────────────────────────────────────────

_GAP_TO_STUDY_TYPE: Dict[GapCategory, StudyType] = {
    GapCategory.DATA_GAP:          StudyType.HISTORICAL_REPLAY,
    GapCategory.EVIDENCE_GAP:      StudyType.DNA_DISCOVERY,
    GapCategory.REGIME_GAP:        StudyType.REGIME_ANALYSIS,
    GapCategory.SECTOR_GAP:        StudyType.SECTOR_RESEARCH,
    GapCategory.TEMPORAL_GAP:      StudyType.HISTORICAL_REPLAY,
    GapCategory.VALIDATION_GAP:    StudyType.EDGE_VALIDATION,
    GapCategory.CONTRADICTION_GAP: StudyType.CROSS_VALIDATION,
    GapCategory.CONFIDENCE_GAP:    StudyType.EDGE_VALIDATION,
    GapCategory.KNOWLEDGE_GAP:     StudyType.DNA_DISCOVERY,
    GapCategory.COVERAGE_GAP:      StudyType.REGIME_ANALYSIS,
}

_HYPOTHESIS_TO_STUDY_TYPE: Dict[HypothesisClassification, StudyType] = {
    HypothesisClassification.PERFORMANCE_GAP: StudyType.EDGE_VALIDATION,
    HypothesisClassification.COVERAGE_GAP:    StudyType.REGIME_ANALYSIS,
    HypothesisClassification.TEMPORAL_GAP:    StudyType.HISTORICAL_REPLAY,
    HypothesisClassification.DEGRADATION:     StudyType.EDGE_VALIDATION,
    HypothesisClassification.CONTRADICTION:   StudyType.CROSS_VALIDATION,
    HypothesisClassification.EXPLORATORY:     StudyType.DNA_DISCOVERY,
    HypothesisClassification.MANUAL:          StudyType.CUSTOM,
}

# Default risk class per study type (overridable via create_plan risk_class parameter)
_STUDY_TYPE_RISK: Dict[StudyType, RiskClass] = {
    StudyType.HISTORICAL_REPLAY:  RiskClass.LOW,
    StudyType.DNA_DISCOVERY:      RiskClass.MEDIUM,
    StudyType.REGIME_ANALYSIS:    RiskClass.MEDIUM,
    StudyType.SECTOR_RESEARCH:    RiskClass.LOW,
    StudyType.EDGE_VALIDATION:    RiskClass.MEDIUM,
    StudyType.CROSS_VALIDATION:   RiskClass.HIGH,
    StudyType.FEATURE_IMPORTANCE: RiskClass.MEDIUM,
    StudyType.PATTERN_MINING:     RiskClass.MEDIUM,
    StudyType.META_LEARNING:      RiskClass.HIGH,
    StudyType.CUSTOM:             RiskClass.HIGH,
}

# (data_fetch_hours, compute_hours, analysis_hours)
_COMPUTE_PROFILE: Dict[StudyType, Tuple[float, float, float]] = {
    StudyType.HISTORICAL_REPLAY:  (1.0, 4.0, 1.0),
    StudyType.DNA_DISCOVERY:      (0.5, 2.0, 1.0),
    StudyType.REGIME_ANALYSIS:    (1.0, 3.0, 1.5),
    StudyType.SECTOR_RESEARCH:    (0.5, 2.0, 1.0),
    StudyType.EDGE_VALIDATION:    (0.5, 2.0, 1.0),
    StudyType.CROSS_VALIDATION:   (1.0, 4.0, 2.0),
    StudyType.FEATURE_IMPORTANCE: (1.0, 3.0, 1.5),
    StudyType.PATTERN_MINING:     (1.5, 6.0, 2.0),
    StudyType.META_LEARNING:      (2.0, 8.0, 3.0),
    StudyType.CUSTOM:             (1.0, 4.0, 2.0),
}

_COMPUTE_INTENSITY: Dict[StudyType, str] = {
    StudyType.META_LEARNING:      "HIGH",
    StudyType.PATTERN_MINING:     "HIGH",
    StudyType.HISTORICAL_REPLAY:  "MEDIUM",
    StudyType.CROSS_VALIDATION:   "MEDIUM",
    StudyType.FEATURE_IMPORTANCE: "MEDIUM",
    StudyType.REGIME_ANALYSIS:    "MEDIUM",
    StudyType.CUSTOM:             "MEDIUM",
    StudyType.DNA_DISCOVERY:      "LOW",
    StudyType.SECTOR_RESEARCH:    "LOW",
    StudyType.EDGE_VALIDATION:    "LOW",
}

_PARALLELIZABLE: Dict[StudyType, bool] = {
    StudyType.HISTORICAL_REPLAY:  True,
    StudyType.DNA_DISCOVERY:      False,
    StudyType.REGIME_ANALYSIS:    True,
    StudyType.SECTOR_RESEARCH:    True,
    StudyType.EDGE_VALIDATION:    True,
    StudyType.CROSS_VALIDATION:   False,
    StudyType.FEATURE_IMPORTANCE: True,
    StudyType.PATTERN_MINING:     True,
    StudyType.META_LEARNING:      False,
    StudyType.CUSTOM:             False,
}

# Task templates: list of (title, description, inputs, outputs, hours_fraction)
_TASK_TEMPLATES: Dict[StudyType, List[Tuple[str, str, List[str], List[str], float]]] = {
    StudyType.HISTORICAL_REPLAY: [
        ("Define Scope",          "Specify universe, date range, and strategy parameters.",
         [],                      ["scope_document"],                   0.5),
        ("Fetch Historical Data", "Download and validate OHLCV and feature data.",
         ["scope_document"],      ["raw_data"],                         0.25),
        ("Run Replay",            "Execute strategy replay over the full historical window.",
         ["raw_data"],            ["replay_results"],                   0.45),
        ("Compute Metrics",       "Calculate performance, risk, and statistical metrics.",
         ["replay_results"],      ["metrics_report"],                   0.15),
        ("Document Findings",     "Summarize findings and update knowledge base.",
         ["metrics_report"],      ["study_report", "findings"],         0.15),
    ],
    StudyType.DNA_DISCOVERY: [
        ("Load Classifications",  "Load winner/loser trade classifications from KP.",
         [],                      ["classified_trades"],                0.25),
        ("Extract DNA Features",  "Compute pre-trade feature vectors for all classes.",
         ["classified_trades"],   ["feature_matrix"],                   0.30),
        ("Cluster Analysis",      "Apply clustering to identify stable DNA patterns.",
         ["feature_matrix"],      ["cluster_model", "cluster_report"],  0.25),
        ("Stability Validation",  "Validate cluster stability across time periods.",
         ["cluster_model"],       ["stability_report"],                 0.10),
        ("Document DNA",          "Summarize DNA signatures and update knowledge base.",
         ["stability_report"],    ["study_report", "dna_signatures"],   0.10),
    ],
    StudyType.REGIME_ANALYSIS: [
        ("Define Regimes",        "Specify the market regime classification methodology.",
         [],                      ["regime_definition"],                0.20),
        ("Fetch Multi-Year Data", "Fetch data spanning multiple regime cycles.",
         ["regime_definition"],   ["multi_year_data"],                  0.25),
        ("Compute Regime Stats",  "Compute conditional statistics for each regime.",
         ["multi_year_data"],     ["regime_statistics"],                0.30),
        ("Cross-Period Validation","Validate regime characteristics across time windows.",
         ["regime_statistics"],   ["validation_report"],                0.15),
        ("Document Regimes",      "Summarize regime characteristics and update KP.",
         ["validation_report"],   ["study_report", "regime_profiles"],  0.10),
    ],
    StudyType.SECTOR_RESEARCH: [
        ("Define Sector Universe","Specify sector classification and member symbols.",
         [],                      ["sector_definition"],                0.20),
        ("Fetch Sector Data",     "Download sector-specific historical data.",
         ["sector_definition"],   ["sector_data"],                      0.25),
        ("Characterize Sectors",  "Compute sector-level statistics and patterns.",
         ["sector_data"],         ["sector_stats"],                     0.30),
        ("Cross-Sector Compare",  "Compare sector behaviours across market conditions.",
         ["sector_stats"],        ["comparison_report"],                0.15),
        ("Document Sectors",      "Summarize sector insights and update knowledge base.",
         ["comparison_report"],   ["study_report", "sector_profiles"],  0.10),
    ],
    StudyType.EDGE_VALIDATION: [
        ("Define Edge Hypothesis","State the edge hypothesis with measurable criteria.",
         [],                      ["edge_hypothesis"],                  0.15),
        ("Fetch OOS Data",        "Fetch dedicated out-of-sample data period.",
         ["edge_hypothesis"],     ["oos_data"],                         0.25),
        ("Apply Edge Rules",      "Execute edge detection rules on OOS data.",
         ["oos_data"],            ["raw_edge_results"],                 0.30),
        ("Statistical Testing",   "Run significance tests and compute effect sizes.",
         ["raw_edge_results"],    ["significance_report"],              0.20),
        ("Document Edge Status",  "Record VALID/INVALID verdict and update KP.",
         ["significance_report"], ["study_report", "edge_verdict"],     0.10),
    ],
    StudyType.CROSS_VALIDATION: [
        ("Map Conflicting Evidence","Identify all evidence supporting each position.",
         [],                        ["evidence_map"],                   0.20),
        ("Collect Comparison Data", "Fetch data required for controlled comparison.",
         ["evidence_map"],          ["comparison_data"],                0.25),
        ("Design Comparison",       "Define fair comparison protocol for both positions.",
         ["comparison_data"],       ["comparison_protocol"],            0.15),
        ("Execute Comparison",      "Run both sides of the comparison study.",
         ["comparison_protocol"],   ["comparison_results"],             0.30),
        ("Resolve Contradiction",   "Document resolution or escalate to Scientific Director.",
         ["comparison_results"],    ["study_report", "resolution_record"], 0.10),
    ],
    StudyType.FEATURE_IMPORTANCE: [
        ("Define Feature Universe","Enumerate all candidate features and groups.",
         [],                       ["feature_universe"],                0.15),
        ("Fetch Feature Data",     "Download all required feature data.",
         ["feature_universe"],     ["feature_data"],                    0.20),
        ("Compute Importance",     "Apply importance metrics (SHAP, MI, correlation).",
         ["feature_data"],         ["importance_scores"],               0.35),
        ("Temporal Stability",     "Validate that rankings are stable over time.",
         ["importance_scores"],    ["stability_analysis"],              0.20),
        ("Document Rankings",      "Publish ranked feature list and update KP.",
         ["stability_analysis"],   ["study_report", "feature_rankings"], 0.10),
    ],
    StudyType.PATTERN_MINING: [
        ("Define Search Space",    "Specify pattern types, timeframes, and filters.",
         [],                       ["search_spec"],                     0.15),
        ("Scan Historical Data",   "Run pattern scanner over full historical window.",
         ["search_spec"],          ["pattern_candidates"],              0.40),
        ("Statistical Screening",  "Filter for statistically significant patterns.",
         ["pattern_candidates"],   ["screened_patterns"],               0.20),
        ("OOS Validation",         "Validate patterns on reserved OOS period.",
         ["screened_patterns"],    ["oos_validation"],                  0.15),
        ("Document Patterns",      "Publish validated patterns and update KP.",
         ["oos_validation"],       ["study_report", "pattern_library"], 0.10),
    ],
    StudyType.META_LEARNING: [
        ("Collect Study Results",  "Aggregate all prior study results and metadata.",
         [],                       ["study_corpus"],                    0.20),
        ("Meta-Feature Engineering","Build meta-features describing study conditions.",
         ["study_corpus"],         ["meta_features"],                   0.25),
        ("Train Meta-Learner",     "Train model to predict which studies will succeed.",
         ["meta_features"],        ["meta_model"],                      0.35),
        ("Holdout Validation",     "Validate meta-learner on held-out studies.",
         ["meta_model"],           ["holdout_report"],                  0.15),
        ("Document Meta-Insights", "Publish meta-learning insights and update KP.",
         ["holdout_report"],       ["study_report", "meta_insights"],   0.05),
    ],
    StudyType.CUSTOM: [
        ("Define Objective",       "Document the custom study objective and scope.",
         [],                       ["objective_document"],              0.20),
        ("Collect Required Data",  "Fetch all data required by the custom study.",
         ["objective_document"],   ["custom_data"],                     0.25),
        ("Execute Custom Analysis","Run the custom analysis protocol.",
         ["custom_data"],          ["analysis_results"],                0.35),
        ("Validate Results",       "Apply validation protocol to custom results.",
         ["analysis_results"],     ["validation_report"],               0.10),
        ("Document Findings",      "Publish findings and update knowledge base.",
         ["validation_report"],    ["study_report", "custom_findings"], 0.10),
    ],
}

_DEFAULT_EXPECTED_OUTPUTS: Dict[StudyType, List[str]] = {
    StudyType.HISTORICAL_REPLAY:  ["replay_results", "metrics_report", "study_report"],
    StudyType.DNA_DISCOVERY:      ["dna_signatures", "cluster_report", "study_report"],
    StudyType.REGIME_ANALYSIS:    ["regime_profiles", "validation_report", "study_report"],
    StudyType.SECTOR_RESEARCH:    ["sector_profiles", "comparison_report", "study_report"],
    StudyType.EDGE_VALIDATION:    ["edge_verdict", "significance_report", "study_report"],
    StudyType.CROSS_VALIDATION:   ["resolution_record", "comparison_results", "study_report"],
    StudyType.FEATURE_IMPORTANCE: ["feature_rankings", "stability_analysis", "study_report"],
    StudyType.PATTERN_MINING:     ["pattern_library", "oos_validation", "study_report"],
    StudyType.META_LEARNING:      ["meta_insights", "meta_model", "study_report"],
    StudyType.CUSTOM:             ["custom_findings", "validation_report", "study_report"],
}

_DEFAULT_SUCCESS_CRITERIA: Dict[StudyType, List[str]] = {
    StudyType.HISTORICAL_REPLAY:  ["Win rate ≥ 50%", "Sharpe ratio ≥ 0.8",
                                   "Max drawdown ≤ 15%"],
    StudyType.DNA_DISCOVERY:      ["At least 3 stable DNA clusters identified",
                                   "Cluster stability > 0.70 across time windows"],
    StudyType.REGIME_ANALYSIS:    ["All target regimes profiled",
                                   "Regime conditional statistics significant (p < 0.05)"],
    StudyType.SECTOR_RESEARCH:    ["All target sectors characterized",
                                   "Sector differentiation statistically confirmed"],
    StudyType.EDGE_VALIDATION:    ["Win rate ≥ 50%", "OOS Sharpe ≥ 0.8",
                                   "Statistical significance p < 0.05"],
    StudyType.CROSS_VALIDATION:   ["Contradiction resolved or documented",
                                   "Both positions tested under identical conditions"],
    StudyType.FEATURE_IMPORTANCE: ["All features ranked", "Top-10 rankings stable ≥ 70%"],
    StudyType.PATTERN_MINING:     ["At least 1 new validated pattern found",
                                   "OOS confirmation rate ≥ 60%"],
    StudyType.META_LEARNING:      ["Meta-model predicts study outcome with ≥ 65% accuracy",
                                   "Holdout AUROC ≥ 0.65"],
    StudyType.CUSTOM:             ["Custom success criteria met as defined in objective"],
}

_DEFAULT_ACCEPTANCE_CRITERIA: Dict[StudyType, List[str]] = {
    StudyType.HISTORICAL_REPLAY:  ["Pass: win_rate ≥ min_win_rate",
                                   "Pass: sharpe ≥ min_sharpe",
                                   "Pass: max_drawdown ≤ max_drawdown_threshold"],
    StudyType.DNA_DISCOVERY:      ["Pass: ≥ 2 stable clusters",
                                   "Pass: cluster purity ≥ 0.60"],
    StudyType.REGIME_ANALYSIS:    ["Pass: all required regimes covered",
                                   "Pass: per-regime sample size ≥ 30"],
    StudyType.SECTOR_RESEARCH:    ["Pass: all required sectors covered",
                                   "Pass: per-sector sample size ≥ 30"],
    StudyType.EDGE_VALIDATION:    ["Pass: win_rate ≥ min_win_rate",
                                   "Pass: sharpe ≥ min_sharpe",
                                   "Pass: not contradicted by OOS"],
    StudyType.CROSS_VALIDATION:   ["Pass: both positions have equal sample sizes",
                                   "Pass: comparison protocol pre-registered"],
    StudyType.FEATURE_IMPORTANCE: ["Pass: ranking produces stable top-3 ≥ 2 windows",
                                   "Pass: importance sum of top-10 ≥ 0.80 of total"],
    StudyType.PATTERN_MINING:     ["Pass: discovered patterns confirmed OOS",
                                   "Pass: minimum 100 pattern occurrences in sample"],
    StudyType.META_LEARNING:      ["Pass: holdout accuracy ≥ 0.65",
                                   "Pass: calibration ECE ≤ 0.10"],
    StudyType.CUSTOM:             ["Pass: all custom acceptance criteria from objective"],
}


# ─── plan ID ──────────────────────────────────────────────────────────────────

def _plan_id(study_type: StudyType, title: str, source_key: str) -> str:
    """Deterministic plan_id: SP-{sha256(study_type:title:source_key)[:8]}."""
    seed = f"{study_type.value}:{title.strip()}:{source_key}"
    return f"SP-{hashlib.sha256(seed.encode()).hexdigest()[:8].upper()}"


# ─── StudyPlanner ─────────────────────────────────────────────────────────────

class StudyPlanner:
    """
    Scientific experiment design engine for ARS.

    Converts validated research priorities into fully specified StudyPlan
    objects that can be approved and executed without additional planning.

    All read operations (list_plans, statistics, estimate_cost) are thread-safe.
    Concurrent create_plan / create_from_* calls are protected by a single lock.

    Usage::

        kp      = KnowledgeProvider()
        reg     = HypothesisRegistry(kp)
        planner = StudyPlanner(kp, hypothesis_registry=reg)

        plan = planner.create_from_gap(my_gap)
        issues = planner.validate_dependencies(plan.plan_id)
        est    = planner.estimate_cost(plan.plan_id)
        stats  = planner.statistics()
    """

    def __init__(
        self,
        knowledge_provider:  KnowledgeProvider,
        hypothesis_registry: Optional[HypothesisRegistry]  = None,
        gap_detector:        Optional[GapDetector]          = None,
        roadmap_manager:     Optional[RoadmapManager]       = None,
        evidence_validator:  Optional[EvidenceValidator]    = None,
        config:              Optional[StudyPlannerConfig]   = None,
    ) -> None:
        self._kp   = knowledge_provider
        self._hr   = hypothesis_registry
        self._gd   = gap_detector
        self._rm   = roadmap_manager
        self._ev   = evidence_validator
        self._cfg  = config or StudyPlannerConfig()
        self._plans: Dict[str, StudyPlan] = {}
        self._lock  = threading.Lock()

    # ═════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═════════════════════════════════════════════════════════════════════════

    def create_plan(
        self,
        title:                    str,
        study_type:               StudyType,
        scientific_question:      str,
        objective:                str                          = "",
        background:               str                          = "",
        supporting_evidence:      Optional[List[str]]          = None,
        related_hypotheses:       Optional[List[str]]          = None,
        related_gaps:             Optional[List[str]]          = None,
        dataset_requirements:     Optional[List[DatasetRequirement]] = None,
        dependencies:             Optional[List[StudyDependency]] = None,
        risk_class:               Optional[RiskClass]          = None,
        estimated_knowledge_gain: float                        = 0.5,
        source_gap_id:            Optional[str]                = None,
        source_hypothesis_id:     Optional[str]                = None,
        source_entry_id:          Optional[str]                = None,
    ) -> StudyPlan:
        """Create a StudyPlan from explicit parameters."""
        source_key = source_gap_id or source_hypothesis_id or source_entry_id or ""
        pid        = _plan_id(study_type, title, source_key)

        eff_risk = risk_class if risk_class is not None else _STUDY_TYPE_RISK[study_type]
        approval  = self._assign_approval_class(study_type, eff_risk)

        ds_reqs   = dataset_requirements or [self._default_dataset(study_type)]
        vplan     = self._default_validation_plan(study_type)
        tasks     = self._build_tasks(study_type)
        estimate  = self._build_estimate(study_type, ds_reqs)
        outputs   = _DEFAULT_EXPECTED_OUTPUTS[study_type]
        sc        = _DEFAULT_SUCCESS_CRITERIA[study_type]
        ac        = _DEFAULT_ACCEPTANCE_CRITERIA[study_type]

        plan = StudyPlan(
            plan_id=pid,
            study_type=study_type,
            title=title,
            objective=objective or f"Address {study_type.value.lower().replace('_', ' ')} research objective.",
            scientific_question=scientific_question,
            background=background,
            supporting_evidence=supporting_evidence or [],
            related_hypotheses=related_hypotheses or [],
            related_gaps=related_gaps or [],
            dataset_requirements=ds_reqs,
            validation_plan=vplan,
            tasks=tasks,
            execution_estimate=estimate,
            dependencies=dependencies or [],
            risk_class=eff_risk,
            approval_class=approval,
            status=PlanStatus.DRAFT,
            expected_outputs=outputs,
            success_criteria=sc,
            acceptance_criteria=ac,
            estimated_knowledge_gain=float(estimated_knowledge_gain),
            source_gap_id=source_gap_id,
            source_hypothesis_id=source_hypothesis_id,
            source_entry_id=source_entry_id,
            created_at=datetime.now(),
        )
        with self._lock:
            self._plans[pid] = plan
        return plan

    def create_from_gap(self, gap: KnowledgeGap) -> StudyPlan:
        """Create a StudyPlan for a KnowledgeGap."""
        study_type = _GAP_TO_STUDY_TYPE[gap.category]
        title      = f"{study_type.value.replace('_', ' ').title()}: {gap.title}"
        question   = (
            f"Does addressing the {gap.category.value.lower().replace('_', ' ')} "
            f"'{gap.title}' produce actionable research insights?"
        )
        background = f"{gap.severity_rationale}\n\n{gap.description}".strip()
        return self.create_plan(
            title=title,
            study_type=study_type,
            scientific_question=question,
            objective=gap.recommended_action,
            background=background,
            supporting_evidence=list(gap.supporting_evidence),
            related_hypotheses=list(gap.related_hypotheses),
            related_gaps=[gap.gap_id] + list(gap.related_findings),
            estimated_knowledge_gain=gap.estimated_knowledge_gain,
            source_gap_id=gap.gap_id,
        )

    def create_from_hypothesis(self, hypothesis_id: str) -> StudyPlan:
        """Create a StudyPlan to validate a ScientificHypothesis."""
        if self._hr is None:
            raise StudyPlannerError(
                "hypothesis_registry is required for create_from_hypothesis()."
            )
        hyp = self._hr.get(hypothesis_id)
        if hyp is None:
            raise StudyPlanNotFoundError(
                f"Hypothesis '{hypothesis_id}' not found in registry."
            )

        study_type = _HYPOTHESIS_TO_STUDY_TYPE.get(hyp.classification, StudyType.CUSTOM)
        title      = f"Validate Hypothesis: {hyp.title}"
        ev_ids     = [ref.evidence_id for ref in hyp.supporting_evidence]
        gain       = hyp.confidence if hyp.confidence else 0.5

        return self.create_plan(
            title=title,
            study_type=study_type,
            scientific_question=hyp.research_question,
            objective=f"Validate or reject hypothesis: {hyp.title}",
            background=hyp.description,
            supporting_evidence=ev_ids,
            related_hypotheses=[hypothesis_id] + list(hyp.dependencies),
            related_gaps=[hyp.knowledge_gap] if hyp.knowledge_gap else [],
            estimated_knowledge_gain=gain,
            source_hypothesis_id=hypothesis_id,
        )

    def create_from_entry(self, entry: RoadmapEntry) -> StudyPlan:
        """Create a StudyPlan from a RoadmapEntry (wraps create_from_gap with entry context)."""
        gap   = entry.gap
        study_type = _GAP_TO_STUDY_TYPE[gap.category]
        title = entry.recommended_study_title

        question = (
            f"Does addressing roadmap entry '{entry.entry_id}' "
            f"({gap.category.value.lower().replace('_', ' ')}: {gap.title}) "
            f"produce actionable research insights?"
        )
        background = (
            f"Roadmap rank: {entry.rank}  |  Priority score: {entry.priority_score:.2f}\n"
            f"{gap.severity_rationale}\n\n{gap.description}"
        ).strip()

        return self.create_plan(
            title=title,
            study_type=study_type,
            scientific_question=question,
            objective=entry.recommended_approach,
            background=background,
            supporting_evidence=list(gap.supporting_evidence),
            related_hypotheses=list(gap.related_hypotheses),
            related_gaps=[gap.gap_id],
            estimated_knowledge_gain=entry.knowledge_gain_estimate.total_gain,
            source_gap_id=gap.gap_id,
            source_entry_id=entry.entry_id,
        )

    def list_plans(
        self,
        status: Optional[PlanStatus] = None,
        study_type: Optional[StudyType] = None,
    ) -> List[StudyPlan]:
        """Return stored plans, optionally filtered by status or study type."""
        with self._lock:
            plans = list(self._plans.values())
        if status is not None:
            plans = [p for p in plans if p.status == status]
        if study_type is not None:
            plans = [p for p in plans if p.study_type == study_type]
        return plans

    def get_plan(self, plan_id: str) -> StudyPlan:
        """Return a plan by ID; raises StudyPlanNotFoundError if not found."""
        with self._lock:
            plan = self._plans.get(plan_id)
        if plan is None:
            raise StudyPlanNotFoundError(f"Plan '{plan_id}' not found.")
        return plan

    def validate_dependencies(self, plan_id: str) -> List[str]:
        """
        Validate all dependencies of a plan.

        Returns a list of issue strings (empty = no issues).
        Checks:
          1. All depends_on_plan_id values reference known plans.
          2. No circular dependency chains.
          3. Blocking dependencies are flagged if unresolved.
        """
        plan = self.get_plan(plan_id)
        issues: List[str] = []

        for dep in plan.dependencies:
            if dep.depends_on_plan_id:
                with self._lock:
                    exists = dep.depends_on_plan_id in self._plans
                if not exists:
                    severity = "BLOCKING" if dep.is_blocking else "non-blocking"
                    issues.append(
                        f"{severity} dependency on unknown plan "
                        f"'{dep.depends_on_plan_id}': {dep.reason}"
                    )

            if dep.depends_on_gap_id and self._gd is not None:
                known_ids = {g.gap_id for g in self._gd.detect_all()}
                if dep.depends_on_gap_id not in known_ids:
                    issues.append(
                        f"Dependency on gap '{dep.depends_on_gap_id}' not found "
                        f"in current gap set: {dep.reason}"
                    )

            if dep.depends_on_hypothesis_id and self._hr is not None:
                if self._hr.get_hypothesis(dep.depends_on_hypothesis_id) is None:
                    issues.append(
                        f"Dependency on hypothesis '{dep.depends_on_hypothesis_id}' "
                        f"not found in registry: {dep.reason}"
                    )

        # Circular dependency check (DFS)
        cycles = self._detect_cycles(plan_id)
        issues.extend(cycles)

        return issues

    def estimate_cost(self, plan_id: str) -> ExecutionEstimate:
        """Return the execution estimate for a stored plan."""
        return self.get_plan(plan_id).execution_estimate

    def portfolio(self) -> StudyPortfolio:
        """Build an aggregate portfolio view of all current plans."""
        with self._lock:
            plans = list(self._plans.values())

        by_type:     Dict[str, int] = {t.value: 0 for t in StudyType}
        by_approval: Dict[str, int] = {a.value: 0 for a in ApprovalClass}
        by_risk:     Dict[str, int] = {r.value: 0 for r in RiskClass}
        by_status:   Dict[str, int] = {s.value: 0 for s in PlanStatus}

        for p in plans:
            by_type[p.study_type.value]         += 1
            by_approval[p.approval_class.value] += 1
            by_risk[p.risk_class.value]         += 1
            by_status[p.status.value]           += 1

        total_hours = sum(p.execution_estimate.total_hours for p in plans)
        total_gain  = sum(p.estimated_knowledge_gain for p in plans)
        b_ids       = [p.plan_id for p in plans if p.approval_class == ApprovalClass.CLASS_B]

        return StudyPortfolio(
            plans=plans,
            total_plans=len(plans),
            by_study_type=by_type,
            by_approval_class=by_approval,
            by_risk_class=by_risk,
            by_status=by_status,
            total_compute_hours=total_hours,
            total_knowledge_gain=total_gain,
            class_b_plans=b_ids,
            built_at=datetime.now(),
        )

    def latest_plans(self, n: int = 10) -> List[StudyPlan]:
        """Return the N most recently created plans (newest first)."""
        with self._lock:
            plans = list(self._plans.values())
        return sorted(plans, key=lambda p: p.created_at, reverse=True)[:n]

    def statistics(self) -> PlanningStatistics:
        """Return aggregate statistics for all plans in this session."""
        with self._lock:
            plans = list(self._plans.values())

        n = len(plans)
        by_type:     Dict[str, int] = {t.value: 0 for t in StudyType}
        by_approval: Dict[str, int] = {a.value: 0 for a in ApprovalClass}
        by_risk:     Dict[str, int] = {r.value: 0 for r in RiskClass}

        for p in plans:
            by_type[p.study_type.value]         += 1
            by_approval[p.approval_class.value] += 1
            by_risk[p.risk_class.value]         += 1

        avg_gain  = (sum(p.estimated_knowledge_gain for p in plans) / n) if n else 0.0
        avg_hours = (sum(p.execution_estimate.total_hours for p in plans) / n) if n else 0.0
        b_frac    = (by_approval.get(ApprovalClass.CLASS_B.value, 0) / n) if n else 0.0

        return PlanningStatistics(
            total_plans_created=n,
            by_study_type=by_type,
            by_approval_class=by_approval,
            by_risk_class=by_risk,
            avg_knowledge_gain=avg_gain,
            avg_compute_hours=avg_hours,
            class_b_fraction=b_frac,
            built_at=datetime.now(),
        )

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _assign_approval_class(
        self, study_type: StudyType, risk_class: RiskClass
    ) -> ApprovalClass:
        """CLASS_B if study_type is in class_b list or risk meets/exceeds threshold."""
        if study_type in self._cfg.class_b_study_types:
            return ApprovalClass.CLASS_B
        _levels = [RiskClass.LOW, RiskClass.MEDIUM, RiskClass.HIGH]
        if _levels.index(risk_class) >= _levels.index(self._cfg.class_b_risk_threshold):
            return ApprovalClass.CLASS_B
        return ApprovalClass.CLASS_A

    def _default_dataset(self, study_type: StudyType) -> DatasetRequirement:
        """Build a reasonable default DatasetRequirement for a study type."""
        today     = datetime.now()
        end_date  = today.strftime("%Y-%m-%d")
        start_dt  = today - timedelta(days=self._cfg.default_date_lookback_days)
        start_date = start_dt.strftime("%Y-%m-%d")

        symbols = self._available_symbols()

        regimes: List[str] = []
        sectors: List[str] = []
        feature_groups: List[str] = ["OHLCV"]

        if study_type == StudyType.REGIME_ANALYSIS:
            regimes = ["TRENDING_UP", "TRENDING_DOWN", "SIDEWAYS", "HIGH_VOLATILITY"]
        elif study_type == StudyType.SECTOR_RESEARCH:
            sectors = ["IT", "BANKING", "PHARMA", "AUTO", "FMCG"]
        elif study_type in (StudyType.FEATURE_IMPORTANCE, StudyType.DNA_DISCOVERY):
            feature_groups = ["OHLCV", "VOLUME", "MOMENTUM", "VOLATILITY", "TREND"]
        elif study_type == StudyType.PATTERN_MINING:
            feature_groups = ["OHLCV", "CANDLE_PATTERNS", "TECHNICAL"]

        return DatasetRequirement(
            name=f"primary_{study_type.value.lower()}",
            symbols=symbols,
            date_start=start_date,
            date_end=end_date,
            regimes=regimes,
            sectors=sectors,
            feature_groups=feature_groups,
            min_observations=self._cfg.default_min_observations,
            notes=f"Primary dataset for {study_type.value} study.",
        )

    def _available_symbols(self) -> List[str]:
        """Return a short list of symbols from KP with sensible fallback."""
        try:
            studies = self._kp.list_studies()
            seen: Dict[str, None] = {}
            for study in studies[:5]:
                for f in study.findings:
                    if f.raw and "symbol" in f.raw:
                        seen[f.raw["symbol"]] = None
                if len(seen) >= 5:
                    break
            if seen:
                return list(seen.keys())[: self._cfg.max_symbols_per_plan]
        except Exception:
            pass
        return ["NIFTY", "BANKNIFTY"]

    def _default_validation_plan(self, study_type: StudyType) -> ValidationPlan:
        """Build a default validation plan for a study type."""
        cfg = self._cfg
        methodology = {
            StudyType.HISTORICAL_REPLAY:  "Walk-forward replay with OOS holdout validation.",
            StudyType.DNA_DISCOVERY:      "Cross-validation of cluster stability across time.",
            StudyType.REGIME_ANALYSIS:    "Per-regime statistical testing with significance checks.",
            StudyType.SECTOR_RESEARCH:    "Sector-stratified analysis with cross-comparison.",
            StudyType.EDGE_VALIDATION:    "Out-of-sample test with statistical significance threshold.",
            StudyType.CROSS_VALIDATION:   "Controlled A/B comparison with matched sample sizes.",
            StudyType.FEATURE_IMPORTANCE: "Permutation importance with temporal stability check.",
            StudyType.PATTERN_MINING:     "OOS pattern confirmation with false discovery correction.",
            StudyType.META_LEARNING:      "Holdout study set validation with calibration check.",
            StudyType.CUSTOM:             "Custom validation protocol as defined in the objective.",
        }[study_type]

        sc = _DEFAULT_SUCCESS_CRITERIA[study_type]
        ac = _DEFAULT_ACCEPTANCE_CRITERIA[study_type]

        metrics = ["win_rate", "sharpe_ratio", "max_drawdown", "n_observations"]
        if study_type in (StudyType.DNA_DISCOVERY, StudyType.PATTERN_MINING):
            metrics += ["cluster_purity", "stability_score"]
        elif study_type == StudyType.FEATURE_IMPORTANCE:
            metrics += ["mean_importance", "ranking_stability"]
        elif study_type == StudyType.META_LEARNING:
            metrics += ["accuracy", "auroc", "ece"]

        return ValidationPlan(
            methodology=methodology,
            walk_forward_windows=cfg.default_walk_forward_windows,
            oos_split=cfg.default_oos_split,
            cross_validation_folds=cfg.default_cv_folds,
            success_criteria=sc,
            acceptance_criteria=ac,
            metrics=metrics,
            min_win_rate=cfg.default_min_win_rate,
            min_sharpe=cfg.default_min_sharpe,
            max_drawdown=cfg.default_max_drawdown,
        )

    def _build_tasks(self, study_type: StudyType) -> List[StudyTask]:
        """Build the standard task list for a study type."""
        template = _TASK_TEMPLATES[study_type]
        fetch, compute, analysis = _COMPUTE_PROFILE[study_type]
        total = fetch + compute + analysis

        tasks = []
        for order, (title, desc, inputs, outputs, frac) in enumerate(template, start=1):
            tasks.append(StudyTask(
                task_id=f"T{order:02d}",
                title=title,
                description=desc,
                inputs=list(inputs),
                outputs=list(outputs),
                estimated_hours=round(total * frac, 2),
                order=order,
            ))
        return tasks

    def _build_estimate(
        self,
        study_type: StudyType,
        dataset_requirements: List[DatasetRequirement],
    ) -> ExecutionEstimate:
        """Compute execution estimate from study type and dataset requirements."""
        fetch, compute, analysis = _COMPUTE_PROFILE[study_type]
        total = fetch + compute + analysis

        n_symbols = sum(len(d.symbols) for d in dataset_requirements)
        n_years   = (self._cfg.default_date_lookback_days / 365.0)
        storage   = max(1.0, n_symbols * n_years * self._cfg.storage_mb_per_symbol_year)
        cost      = compute * self._cfg.cost_per_compute_hour_usd

        return ExecutionEstimate(
            data_fetch_hours=fetch,
            compute_hours=compute,
            analysis_hours=analysis,
            total_hours=total,
            compute_cost_usd=round(cost, 2),
            storage_mb=round(storage, 1),
            parallelizable=_PARALLELIZABLE[study_type],
            compute_intensity=_COMPUTE_INTENSITY[study_type],
            breakdown={
                "data_fetch_hours":       fetch,
                "compute_hours":          compute,
                "analysis_hours":         analysis,
                "total_hours":            total,
                "n_symbols":              n_symbols,
                "n_years_lookback":       round(n_years, 2),
                "cost_per_hour_usd":      self._cfg.cost_per_compute_hour_usd,
                "storage_mb_per_sym_yr":  self._cfg.storage_mb_per_symbol_year,
            },
        )

    def _detect_cycles(self, start_id: str) -> List[str]:
        """DFS cycle detection over plan dependency graph. Returns issue strings."""
        issues: List[str] = []

        def dfs(current: str, visited: set, path: List[str]) -> None:
            if current in visited:
                cycle_str = " → ".join(path + [current])
                issues.append(f"Circular dependency detected: {cycle_str}")
                return
            with self._lock:
                plan = self._plans.get(current)
            if plan is None:
                return
            visited.add(current)
            for dep in plan.dependencies:
                if dep.depends_on_plan_id:
                    dfs(dep.depends_on_plan_id, visited.copy(), path + [current])

        dfs(start_id, set(), [])
        return issues
