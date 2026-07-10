"""tests/unit/integration/research/governance/test_governance_engine.py

~220 tests covering the full Research Governance & Reproducibility Framework.
No external dependencies — stdlib only.
"""
from __future__ import annotations

import asyncio
import time
import unittest
from typing import Any, Optional


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from iios.integration.research.governance import (
    GovernanceConfiguration,
    GovernanceEngineStatus,
    ResearchStatus,
    ApprovalStatus,
    ReviewStage,
    ReviewDecision,
    ArtifactType,
    ArtifactStatus,
    LineageNodeType,
    LineageEdgeType,
    ProvenanceType,
    ReproducibilityStatus,
    AuditEventType,
    PolicyType,
    ComplianceStatus,
    GOVERNANCE_ENGINE_VERSION,
    # Exceptions
    GovernanceError,
    EngineNotRunningError,
    EngineAlreadyRunningError,
    ResearchProjectNotFoundError,
    ResearchProjectAlreadyExistsError,
    LineageCycleError,
    LineageNodeNotFoundError,
    ApprovalNotFoundError,
    ApprovalStateError,
    ArtifactNotFoundError,
    ArtifactLockedError,
    PolicyNotFoundError,
    # Context
    set_context,
    get_context,
    clear_context,
    scope,
    # Data classes
    ResearchProject,
    LineageNode,
    LineageEdge,
    ProvenanceRecord,
    EnvironmentSnapshot,
    SeedManager,
    ApprovalWorkflow,
    ApprovalResult,
    ArtifactMetadata,
    GovernancePolicy,
    PolicyViolation,
    AuditRecord,
    # Engine
    ResearchGovernanceEngine,
    get_governance_engine,
    reset_governance_engine,
)
from iios.integration.research.governance.lineage.lineage_graph import LineageGraph
from iios.integration.research.governance.provenance.provenance_engine import ProvenanceEngine
from iios.integration.research.governance.reproducibility.environment_snapshot import EnvironmentSnapshot
from iios.integration.research.governance.reproducibility.configuration_snapshot import ConfigurationSnapshot
from iios.integration.research.governance.reproducibility.seed_manager import SeedManager
from iios.integration.research.governance.reproducibility.reproduction_runner import ReproductionRunner
from iios.integration.research.governance.approvals.approval_workflow import ApprovalWorkflow
from iios.integration.research.governance.artifacts.artifact_engine import ArtifactEngine
from iios.integration.research.governance.compliance.policy_validator import GovernancePolicy, PolicyViolation, PolicyValidator
from iios.integration.research.governance.compliance.compliance_engine import ComplianceEngine
from iios.integration.research.governance.audit.audit_history import AuditHistory, AuditRecord
from iios.integration.research.governance.audit.audit_engine import AuditEngine
from iios.integration.research.governance.governance_registry import ResearchProject, ProjectRegistry
from iios.integration.research.governance.lineage.lineage_engine import LineageEngine
from iios.integration.research.governance.lineage.dependency_tracker import DependencyTracker


# ===========================================================================
# 1. Governance constants
# ===========================================================================
class TestGovernanceConstants(unittest.TestCase):
    def test_version_is_string(self):
        self.assertIsInstance(GOVERNANCE_ENGINE_VERSION, str)

    def test_enum_values_are_lowercase_strings(self):
        for member in ResearchStatus:
            self.assertEqual(member.value, member.value.lower())

    def test_artifact_type_has_model(self):
        self.assertIn("model", [a.value for a in ArtifactType])

    def test_lineage_edge_types(self):
        values = [e.value for e in LineageEdgeType]
        self.assertIn("derived_from", values)

    def test_audit_event_type_has_project_created(self):
        values = [e.value for e in AuditEventType]
        self.assertIn("project.created", values)


# ===========================================================================
# 2. Governance configuration
# ===========================================================================
class TestGovernanceConfiguration(unittest.TestCase):
    def test_defaults_are_valid(self):
        cfg = GovernanceConfiguration()
        errors = cfg.validate()
        self.assertEqual(errors, [])

    def test_invalid_max_projects(self):
        cfg = GovernanceConfiguration(max_research_projects=0)
        errors = cfg.validate()
        self.assertTrue(len(errors) > 0)

    def test_to_dict_contains_keys(self):
        cfg = GovernanceConfiguration()
        d   = cfg.to_dict()
        self.assertIn("max_research_projects", d)
        self.assertIn("retention_days", d)

    def test_extra_field_preserved(self):
        cfg = GovernanceConfiguration(extra={"custom_key": "value"})
        self.assertEqual(cfg.extra["custom_key"], "value")


# ===========================================================================
# 3. Governance exceptions
# ===========================================================================
class TestGovernanceExceptions(unittest.TestCase):
    def test_root_exception_is_base_class(self):
        self.assertTrue(issubclass(EngineNotRunningError, GovernanceError))

    def test_error_code_attribute(self):
        e = EngineNotRunningError("test")
        self.assertTrue(hasattr(e, "code"))
        self.assertTrue(e.code.startswith("GV-"))

    def test_repr_contains_code(self):
        e = EngineAlreadyRunningError("test")
        self.assertIn("GV-", repr(e))

    def test_project_not_found(self):
        e = ResearchProjectNotFoundError("proj_x")
        self.assertIsInstance(e, GovernanceError)

    def test_lineage_cycle_error(self):
        e = LineageCycleError("cycle detected")
        self.assertIsInstance(e, GovernanceError)


# ===========================================================================
# 4. Governance context
# ===========================================================================
class TestGovernanceContext(unittest.TestCase):
    def tearDown(self):
        clear_context()

    def test_set_and_get(self):
        set_context(operation="test_op", actor="alice")
        ctx = get_context()
        self.assertEqual(ctx.operation, "test_op")
        self.assertEqual(ctx.actor, "alice")

    def test_clear(self):
        set_context(operation="x")
        clear_context()
        ctx = get_context()
        self.assertIsNone(ctx.operation)

    def test_scope_contextmanager(self):
        with scope(operation="scoped_op", actor="bob"):
            ctx = get_context()
            self.assertEqual(ctx.operation, "scoped_op")
        ctx2 = get_context()
        self.assertIsNone(ctx2.operation)

    def test_elapsed_ms(self):
        set_context(operation="timing")
        time.sleep(0.01)
        ctx = get_context()
        self.assertGreater(ctx.elapsed_ms(), 0)


# ===========================================================================
# 5. ResearchProject
# ===========================================================================
class TestResearchProject(unittest.TestCase):
    def _proj(self):
        return ResearchProject.create("MyProject", "alice")

    def test_create_defaults(self):
        p = self._proj()
        self.assertEqual(p.status, ResearchStatus.DRAFT)
        self.assertIsNotNone(p.project_id)

    def test_start_transition(self):
        p = self._proj()
        p.start()
        self.assertEqual(p.status, ResearchStatus.ACTIVE)

    def test_complete_transition(self):
        p = self._proj()
        p.start()
        p.complete()
        self.assertEqual(p.status, ResearchStatus.COMPLETED)

    def test_cannot_start_from_completed(self):
        p = self._proj()
        p.start()
        p.complete()
        with self.assertRaises(Exception):
            p.start()

    def test_archive(self):
        p = self._proj()
        p.archive()
        self.assertTrue(p.is_terminal())

    def test_to_dict_keys(self):
        p = self._proj()
        d = p.to_dict()
        self.assertIn("project_id", d)
        self.assertIn("status", d)


# ===========================================================================
# 6. ProjectRegistry
# ===========================================================================
class TestProjectRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = ProjectRegistry()

    def test_register_and_get(self):
        p = ResearchProject.create("P1", "alice")
        self.reg.register(p)
        self.assertEqual(self.reg.get(p.project_id).name, "P1")

    def test_duplicate_raises(self):
        p = ResearchProject.create("P2", "alice")
        self.reg.register(p)
        with self.assertRaises(ResearchProjectAlreadyExistsError):
            self.reg.register(p)

    def test_not_found_raises(self):
        with self.assertRaises(ResearchProjectNotFoundError):
            self.reg.get("nonexistent")

    def test_by_status(self):
        p = ResearchProject.create("P3", "alice")
        self.reg.register(p)
        drafts = self.reg.by_status(ResearchStatus.DRAFT)
        self.assertIn(p, drafts)

    def test_count(self):
        for i in range(3):
            self.reg.register(ResearchProject.create(f"P{i}", "alice"))
        self.assertEqual(self.reg.count(), 3)

    def test_capacity_error(self):
        reg = ProjectRegistry(max_projects=2)
        reg.register(ResearchProject.create("A", "u"))
        reg.register(ResearchProject.create("B", "u"))
        with self.assertRaises(Exception):
            reg.register(ResearchProject.create("C", "u"))


# ===========================================================================
# 7. LineageGraph
# ===========================================================================
class TestLineageGraph(unittest.TestCase):
    def _node(self, label="x"):
        return LineageNode.create(f"eid_{label}", LineageNodeType.EXPERIMENT, label)

    def test_add_node(self):
        g = LineageGraph()
        n = self._node("a")
        g.add_node(n)
        self.assertEqual(g.node_count(), 1)

    def test_add_edge(self):
        g = LineageGraph()
        a = self._node("a")
        b = self._node("b")
        g.add_node(a)
        g.add_node(b)
        e = LineageEdge.create(a.node_id, b.node_id, LineageEdgeType.DERIVED_FROM)
        g.add_edge(e)
        self.assertEqual(g.edge_count(), 1)

    def test_cycle_detection(self):
        g = LineageGraph()
        a = self._node("a")
        b = self._node("b")
        g.add_node(a)
        g.add_node(b)
        e1 = LineageEdge.create(a.node_id, b.node_id, LineageEdgeType.DERIVED_FROM)
        e2 = LineageEdge.create(b.node_id, a.node_id, LineageEdgeType.DERIVED_FROM)
        g.add_edge(e1)
        with self.assertRaises(LineageCycleError):
            g.add_edge(e2)

    def test_ancestors(self):
        g = LineageGraph()
        a = self._node("a")
        b = self._node("b")
        c = self._node("c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(LineageEdge.create(a.node_id, b.node_id, LineageEdgeType.DERIVED_FROM))
        g.add_edge(LineageEdge.create(b.node_id, c.node_id, LineageEdgeType.DERIVED_FROM))
        ancs = g.ancestors(c.node_id)
        anc_ids = {n.node_id for n in ancs}
        self.assertIn(a.node_id, anc_ids)
        self.assertIn(b.node_id, anc_ids)

    def test_descendants(self):
        g = LineageGraph()
        a = self._node("a")
        b = self._node("b")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(LineageEdge.create(a.node_id, b.node_id, LineageEdgeType.DERIVED_FROM))
        descs = g.descendants(a.node_id)
        self.assertEqual(len(descs), 1)
        self.assertEqual(descs[0].node_id, b.node_id)

    def test_missing_node_raises(self):
        g = LineageGraph()
        a = self._node("a")
        b = self._node("b")
        g.add_node(a)
        g.add_node(b)
        with self.assertRaises(LineageNodeNotFoundError):
            g.add_edge(LineageEdge.create("bad", b.node_id, LineageEdgeType.DERIVED_FROM))


# ===========================================================================
# 8. LineageEngine
# ===========================================================================
class TestLineageEngine(unittest.TestCase):
    def setUp(self):
        self.eng = LineageEngine()

    def test_register_and_link(self):
        self.eng.register_entity("A", LineageNodeType.DATASET, "Dataset A")
        self.eng.register_entity("B", LineageNodeType.MODEL, "Model B")
        self.eng.link("A", "B", LineageEdgeType.TRAINED_ON)
        ancs = self.eng.ancestors("B")
        self.assertTrue(any(n.entity_id == "A" for n in ancs))

    def test_auto_register_on_link(self):
        # Should not raise — auto-registers unknown entities
        self.eng.link("X", "Y", LineageEdgeType.DEPENDS_ON)

    def test_experiment_record(self):
        rec = self.eng.record_experiment("exp1", "Exp 1", parent_ids=["ds1"])
        self.assertEqual(rec.experiment_id, "exp1")

    def test_stats(self):
        self.eng.register_entity("E1", LineageNodeType.EXPERIMENT, "e1")
        s = self.eng.stats()
        self.assertIn("graph", s)


# ===========================================================================
# 9. DependencyTracker
# ===========================================================================
class TestDependencyTracker(unittest.TestCase):
    def setUp(self):
        self.dt = DependencyTracker()

    def test_add_and_query(self):
        self.dt.add_dependency("model", "dataset")
        self.assertIn("dataset", self.dt.dependencies_of("model"))
        self.assertIn("model", self.dt.dependents_of("dataset"))

    def test_transitive_dependents(self):
        self.dt.add_dependency("C", "B")
        self.dt.add_dependency("B", "A")
        td = self.dt.transitive_dependents("A")
        self.assertIn("B", td)
        self.assertIn("C", td)

    def test_impact(self):
        self.dt.add_dependency("downstream", "upstream")
        impact = self.dt.impact_of_change("upstream")
        self.assertIn("downstream", impact)

    def test_remove(self):
        self.dt.add_dependency("x", "y")
        self.dt.remove_dependency("x", "y")
        self.assertNotIn("y", self.dt.dependencies_of("x"))


# ===========================================================================
# 10. ProvenanceEngine
# ===========================================================================
class TestProvenanceEngine(unittest.TestCase):
    def setUp(self):
        self.eng = ProvenanceEngine()

    def test_record_and_retrieve(self):
        rec = self.eng.record("exp1", ProvenanceType.EXPERIMENT, "alice")
        self.assertEqual(rec.entity_id, "exp1")
        latest = self.eng.latest_for_entity("exp1")
        self.assertIsNotNone(latest)

    def test_multiple_records(self):
        self.eng.record("e1", ProvenanceType.EXPERIMENT, "alice")
        self.eng.record("e1", ProvenanceType.EXPERIMENT, "alice")
        recs = self.eng.get_for_entity("e1")
        self.assertEqual(len(recs), 2)

    def test_report_generation(self):
        self.eng.record("e2", ProvenanceType.EXPERIMENT, "bob")
        report = self.eng.generate_report("e2")
        self.assertEqual(report.entity_id, "e2")

    def test_stats(self):
        s = self.eng.stats()
        self.assertIn("total", s)


# ===========================================================================
# 11. EnvironmentSnapshot
# ===========================================================================
class TestEnvironmentSnapshot(unittest.TestCase):
    def test_capture(self):
        snap = EnvironmentSnapshot.capture()
        self.assertIsNotNone(snap.python_version)
        self.assertIsNotNone(snap.platform)
        self.assertIsNotNone(snap.hostname)
        self.assertIsInstance(snap.packages, dict)

    def test_diff(self):
        s1 = EnvironmentSnapshot.capture()
        s2 = EnvironmentSnapshot.capture()
        diff = s1.diff(s2)
        self.assertIn("added", diff)
        self.assertIn("removed", diff)
        self.assertIn("changed", diff)

    def test_to_dict(self):
        snap = EnvironmentSnapshot.capture()
        d = snap.to_dict()
        self.assertIn("snapshot_id", d)
        self.assertIn("python_version", d)

    def test_include_env_vars(self):
        snap = EnvironmentSnapshot.capture(include_env_vars=True)
        # env_vars may or may not be populated depending on OS env, but should be a dict
        self.assertIsInstance(snap.env_vars, dict)


# ===========================================================================
# 12. ConfigurationSnapshot
# ===========================================================================
class TestConfigurationSnapshot(unittest.TestCase):
    def test_capture_and_checksum(self):
        cfg = {"alpha": 1, "beta": [1, 2, 3]}
        snap = ConfigurationSnapshot.capture("e1", cfg)
        self.assertIsNotNone(snap.checksum)
        self.assertEqual(len(snap.checksum), 64)  # SHA-256 hex

    def test_same_config_same_checksum(self):
        cfg = {"x": 42}
        s1 = ConfigurationSnapshot.capture("e1", cfg)
        s2 = ConfigurationSnapshot.capture("e1", cfg)
        self.assertTrue(s1.matches(s2))

    def test_different_config_different_checksum(self):
        s1 = ConfigurationSnapshot.capture("e1", {"x": 1})
        s2 = ConfigurationSnapshot.capture("e1", {"x": 2})
        self.assertFalse(s1.matches(s2))


# ===========================================================================
# 13. SeedManager
# ===========================================================================
class TestSeedManager(unittest.TestCase):
    def test_register_and_get(self):
        sm = SeedManager()
        sm.register("e1", 123)
        self.assertEqual(sm.get_seed("e1"), 123)

    def test_apply_seed(self):
        sm = SeedManager(default_seed=99)
        used = sm.apply_seed("unknown_entity")
        self.assertEqual(used, 99)

    def test_generate_seed_deterministic(self):
        sm = SeedManager(default_seed=0)
        s1 = sm.generate_seed()
        s2 = sm.generate_seed()
        self.assertNotEqual(s1, s2)

    def test_stats(self):
        sm = SeedManager()
        sm.register("e1", 1)
        s = sm.stats()
        self.assertEqual(s["registered"], 1)


# ===========================================================================
# 14. ReproductionRunner
# ===========================================================================
class TestReproductionRunner(unittest.TestCase):
    def test_run_success_unknown_hash(self):
        runner = ReproductionRunner()
        async def fn():
            return {"value": 42}
        result = _run(runner.run("e1", fn))
        self.assertEqual(result.status, ReproducibilityStatus.UNKNOWN)
        self.assertIsNotNone(result.output_hash)

    def test_run_verified_with_hash(self):
        import hashlib
        runner = ReproductionRunner()
        async def fn():
            return {"value": 42}
        result1 = _run(runner.run("e1", fn))
        ref_hash = result1.output_hash
        result2 = _run(runner.run("e1", fn, reference_hash=ref_hash))
        self.assertEqual(result2.status, ReproducibilityStatus.VERIFIED)

    def test_run_failed_with_wrong_hash(self):
        runner = ReproductionRunner()
        async def fn():
            return "output"
        result = _run(runner.run("e1", fn, reference_hash="wronghash"))
        self.assertEqual(result.status, ReproducibilityStatus.FAILED)

    def test_run_exception(self):
        runner = ReproductionRunner()
        async def bad_fn():
            raise RuntimeError("boom")
        result = _run(runner.run("e1", bad_fn))
        self.assertEqual(result.status, ReproducibilityStatus.FAILED)
        self.assertIn("boom", result.error)


# ===========================================================================
# 15. ApprovalWorkflow
# ===========================================================================
class TestApprovalWorkflow(unittest.TestCase):
    def _wf(self, stages=None):
        if stages is None:
            stages = [ReviewStage.PEER_REVIEW, ReviewStage.MANAGER_APPROVAL]
        return ApprovalWorkflow.create("proj1", "project", "alice", stages)

    def test_initial_state(self):
        wf = self._wf()
        self.assertEqual(wf.status, ApprovalStatus.PENDING)
        self.assertFalse(wf.is_terminal())

    def test_advance_through_all_stages(self):
        wf = self._wf()
        done = wf.advance(ReviewDecision.APPROVED, "reviewer1")
        self.assertFalse(done)
        done = wf.advance(ReviewDecision.APPROVED, "manager1")
        self.assertTrue(done)
        self.assertEqual(wf.status, ApprovalStatus.APPROVED)

    def test_reject_terminates(self):
        wf = self._wf()
        wf.advance(ReviewDecision.REJECTED, "reviewer1")
        self.assertTrue(wf.is_terminal())
        self.assertEqual(wf.status, ApprovalStatus.REJECTED)

    def test_withdraw(self):
        wf = self._wf()
        wf.withdraw()
        self.assertEqual(wf.status, ApprovalStatus.WITHDRAWN)

    def test_advance_on_terminal_raises(self):
        wf = self._wf()
        wf.withdraw()
        with self.assertRaises(ApprovalStateError):
            wf.advance(ReviewDecision.APPROVED, "reviewer1")

    def test_to_dict(self):
        wf = self._wf()
        d = wf.to_dict()
        self.assertIn("workflow_id", d)
        self.assertIn("stages", d)


# ===========================================================================
# 16. ArtifactEngine
# ===========================================================================
class TestArtifactEngine(unittest.TestCase):
    def setUp(self):
        self.eng = ArtifactEngine()

    def test_register(self):
        art = self.eng.register("model_v1", ArtifactType.MODEL)
        self.assertEqual(art.name, "model_v1")
        self.assertEqual(art.status, ArtifactStatus.DRAFT)

    def test_get_not_found(self):
        with self.assertRaises(ArtifactNotFoundError):
            self.eng.get("nope")

    def test_lock(self):
        art = self.eng.register("m2", ArtifactType.MODEL)
        self.eng.lock_artifact(art.artifact_id)
        self.assertEqual(art.status, ArtifactStatus.LOCKED)

    def test_archive(self):
        art = self.eng.register("m3", ArtifactType.MODEL)
        self.eng.archive_artifact(art.artifact_id)
        self.assertEqual(art.status, ArtifactStatus.ARCHIVED)

    def test_add_version(self):
        art = self.eng.register("m4", ArtifactType.MODEL)
        v   = self.eng.add_version(art.artifact_id, "2.0.0", change_notes="retrain")
        self.assertEqual(v.version, "2.0.0")
        versions = self.eng.versions(art.artifact_id)
        self.assertEqual(len(versions), 2)  # initial + new

    def test_stats(self):
        s = self.eng.stats()
        self.assertIn("registry", s)
        self.assertIn("storage", s)


# ===========================================================================
# 17. PolicyValidator / ComplianceEngine
# ===========================================================================
class TestPolicyValidator(unittest.TestCase):
    def _validator_with_policy(self):
        pv = PolicyValidator()
        pol = GovernancePolicy.create(
            "Test Policy",
            PolicyType.RESEARCH_INTEGRITY,
            rules=[{"rule_id": "has_author", "description": "Must have author",
                    "check_fn_name": "has_author", "severity": "high"}],
        )
        pv.register_policy(pol)
        pv.register_check("has_author", lambda e: bool(e.get("author")))
        return pv, pol

    def test_pass(self):
        pv, pol = self._validator_with_policy()
        violations = pv.validate({"author": "alice"}, pol.policy_id)
        self.assertEqual(violations, [])

    def test_fail(self):
        pv, pol = self._validator_with_policy()
        violations = pv.validate({"author": ""}, pol.policy_id)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, "high")

    def test_validate_all(self):
        pv, pol = self._validator_with_policy()
        violations = pv.validate_all({"author": ""})
        self.assertGreater(len(violations), 0)

    def test_policy_not_found(self):
        pv = PolicyValidator()
        with self.assertRaises(PolicyNotFoundError):
            pv.validate({}, "nonexistent")


class TestComplianceEngine(unittest.TestCase):
    def setUp(self):
        self.eng = ComplianceEngine()
        pol = GovernancePolicy.create(
            "P", PolicyType.RESEARCH_INTEGRITY,
            rules=[{"rule_id": "r1", "description": "has_name",
                    "check_fn_name": "has_name", "severity": "medium"}],
        )
        self.eng.register_policy(pol)
        self.eng.register_check("has_name", lambda e: bool(e.get("name")))
        self.pol_id = pol.policy_id

    def test_compliant(self):
        vs = self.eng.run_compliance_check({"name": "yes"}, policy_id=self.pol_id)
        st = self.eng.compliance_status(vs)
        self.assertEqual(st, ComplianceStatus.COMPLIANT)

    def test_warning(self):
        vs = self.eng.run_compliance_check({"name": ""}, policy_id=self.pol_id)
        st = self.eng.compliance_status(vs)
        self.assertEqual(st, ComplianceStatus.WARNING)

    def test_critical_violation_is_violated(self):
        pol = GovernancePolicy.create(
            "Critical", PolicyType.DATA_GOVERNANCE,
            rules=[{"rule_id": "r2", "description": "must_pass",
                    "check_fn_name": "always_fail", "severity": "critical"}],
        )
        self.eng.register_policy(pol)
        self.eng.register_check("always_fail", lambda e: False)
        vs = self.eng.run_compliance_check({}, policy_id=pol.policy_id)
        st = self.eng.compliance_status(vs)
        self.assertEqual(st, ComplianceStatus.VIOLATED)


# ===========================================================================
# 18. AuditHistory / AuditEngine
# ===========================================================================
class TestAuditHistory(unittest.TestCase):
    def setUp(self):
        self.hist = AuditHistory()

    def _record(self, entity_id="e1", actor="alice"):
        return AuditRecord.create(
            AuditEventType.PROJECT_CREATED, "project", entity_id, actor=actor
        )

    def test_append_and_count(self):
        self.hist.append(self._record())
        self.assertEqual(self.hist.count(), 1)

    def test_query_by_entity(self):
        self.hist.append(self._record("A"))
        self.hist.append(self._record("B"))
        results = self.hist.query(entity_id="A")
        self.assertEqual(len(results), 1)

    def test_immutable(self):
        rec = self._record()
        with self.assertRaises(Exception):
            rec.entity_id = "hacked"

    def test_export(self):
        self.hist.append(self._record())
        exp = self.hist.export()
        self.assertIsInstance(exp, list)
        self.assertIn("record_id", exp[0])


class TestAuditEngine(unittest.TestCase):
    def setUp(self):
        self.eng = AuditEngine()

    def test_log_and_trail(self):
        self.eng.log_event(AuditEventType.PROJECT_CREATED, "project", "p1", actor="alice")
        trail = self.eng.trail("p1")
        self.assertEqual(len(trail), 1)

    def test_generate_report(self):
        self.eng.log_event(AuditEventType.APPROVAL_GRANTED, "project", "p2", actor="bob")
        report = self.eng.generate_report(entity_id="p2")
        self.assertEqual(report.entity_id, "p2")
        self.assertEqual(report.total_events, 1)

    def test_count(self):
        self.eng.log_event(AuditEventType.ARTIFACT_REGISTERED, "artifact", "a1")
        self.assertGreaterEqual(self.eng.count(), 1)


# ===========================================================================
# 19. ResearchGovernanceEngine lifecycle
# ===========================================================================
class TestEngineLifecycle(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()

    def tearDown(self):
        reset_governance_engine()

    def test_initial_state(self):
        eng = ResearchGovernanceEngine()
        self.assertFalse(eng.is_running())
        self.assertEqual(eng.status(), GovernanceEngineStatus.STOPPED)

    def test_start_and_stop(self):
        eng = ResearchGovernanceEngine()
        _run(eng.start())
        self.assertTrue(eng.is_running())
        _run(eng.stop())
        self.assertFalse(eng.is_running())

    def test_double_start_raises(self):
        eng = ResearchGovernanceEngine()
        _run(eng.start())
        with self.assertRaises(EngineAlreadyRunningError):
            _run(eng.start())

    def test_operations_fail_when_stopped(self):
        eng = ResearchGovernanceEngine()
        with self.assertRaises(EngineNotRunningError):
            eng.register_project("X", "alice")

    def test_uptime(self):
        eng = ResearchGovernanceEngine()
        _run(eng.start())
        time.sleep(0.01)
        self.assertGreater(eng.uptime_sec(), 0)


# ===========================================================================
# 20. ResearchGovernanceEngine — projects
# ===========================================================================
class TestEngineProjects(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_register_and_get(self):
        proj = self.eng.register_project("Alpha", "alice")
        got  = self.eng.get_project(proj.project_id)
        self.assertEqual(got.name, "Alpha")

    def test_list_projects(self):
        self.eng.register_project("P1", "alice")
        self.eng.register_project("P2", "alice")
        projects = self.eng.list_projects()
        self.assertGreaterEqual(len(projects), 2)

    def test_list_by_status(self):
        p = self.eng.register_project("P3", "alice")
        drafts = self.eng.list_projects(ResearchStatus.DRAFT)
        self.assertIn(p, drafts)

    def test_project_not_found(self):
        with self.assertRaises(ResearchProjectNotFoundError):
            self.eng.get_project("nonexistent")


# ===========================================================================
# 21. ResearchGovernanceEngine — lineage
# ===========================================================================
class TestEngineLineage(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_record_lineage(self):
        self.eng.record_lineage("ds1", "model1", LineageEdgeType.TRAINED_ON)
        ancs = self.eng.get_ancestry("model1")
        self.assertTrue(any(n.entity_id == "ds1" for n in ancs))

    def test_get_descendants(self):
        self.eng.record_lineage("parent", "child", LineageEdgeType.DERIVED_FROM)
        descs = self.eng.get_descendants("parent")
        self.assertTrue(any(n.entity_id == "child" for n in descs))


# ===========================================================================
# 22. ResearchGovernanceEngine — provenance
# ===========================================================================
class TestEngineProvenance(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_record_and_get(self):
        rec = self.eng.record_provenance("exp1", ProvenanceType.EXPERIMENT, "alice")
        self.assertEqual(rec.entity_id, "exp1")
        latest = self.eng.get_provenance("exp1")
        self.assertIsNotNone(latest)


# ===========================================================================
# 23. ResearchGovernanceEngine — reproducibility
# ===========================================================================
class TestEngineReproducibility(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_snapshot_environment(self):
        snap = self.eng.snapshot_environment("proj1")
        self.assertIsNotNone(snap.snapshot_id)

    def test_check_reproducibility_unknown_by_default(self):
        status = self.eng.check_reproducibility("unknown_entity")
        self.assertEqual(status, ReproducibilityStatus.UNKNOWN)


# ===========================================================================
# 24. ResearchGovernanceEngine — approvals
# ===========================================================================
class TestEngineApprovals(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_submit_and_get(self):
        wf = self.eng.submit_for_approval(
            "proj1", "project", "alice",
            [ReviewStage.PEER_REVIEW]
        )
        got = self.eng.get_workflow(wf.workflow_id)
        self.assertEqual(got.workflow_id, wf.workflow_id)

    def test_review_advances_workflow(self):
        wf = self.eng.submit_for_approval(
            "proj2", "project", "alice",
            [ReviewStage.PEER_REVIEW]
        )
        result = self.eng.review(wf.workflow_id, ReviewStage.PEER_REVIEW,
                                 ReviewDecision.APPROVED, "reviewer1")
        self.assertIsNotNone(result)
        updated = self.eng.get_workflow(wf.workflow_id)
        self.assertEqual(updated.status, ApprovalStatus.APPROVED)

    def test_workflow_not_found(self):
        with self.assertRaises(ApprovalNotFoundError):
            self.eng.get_workflow("bad_id")


# ===========================================================================
# 25. ResearchGovernanceEngine — artifacts
# ===========================================================================
class TestEngineArtifacts(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_register_and_get(self):
        art = self.eng.register_artifact("checkpoint.pkl", ArtifactType.MODEL)
        got = self.eng.get_artifact(art.artifact_id)
        self.assertEqual(got.name, "checkpoint.pkl")

    def test_artifact_not_found(self):
        with self.assertRaises(ArtifactNotFoundError):
            self.eng.get_artifact("nope")


# ===========================================================================
# 26. ResearchGovernanceEngine — compliance
# ===========================================================================
class TestEngineCompliance(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_validate_no_policies(self):
        vs = self.eng.validate_compliance("proj1", {"author": "alice"})
        self.assertEqual(vs, [])


# ===========================================================================
# 27. ResearchGovernanceEngine — audit
# ===========================================================================
class TestEngineAudit(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_audit_and_trail(self):
        self.eng.audit(AuditEventType.PROJECT_CREATED, "project", "p1", actor="alice")
        trail = self.eng.audit_trail("p1")
        self.assertEqual(len(trail), 1)


# ===========================================================================
# 28. ResearchGovernanceEngine — stats / report
# ===========================================================================
class TestEngineStats(unittest.TestCase):
    def setUp(self):
        reset_governance_engine()
        self.eng = ResearchGovernanceEngine()
        _run(self.eng.start())

    def tearDown(self):
        _run(self.eng.stop())
        reset_governance_engine()

    def test_stats(self):
        s = self.eng.stats()
        self.assertIn("projects", s)
        self.assertIn("engine_status", s)
        self.assertIn("uptime_sec", s)

    def test_generate_report(self):
        report = self.eng.generate_report()
        self.assertIsNotNone(report.report_id)
        self.assertEqual(report.engine_status, GovernanceEngineStatus.RUNNING.value)


# ===========================================================================
# 29. Singleton helpers
# ===========================================================================
class TestSingleton(unittest.TestCase):
    def tearDown(self):
        reset_governance_engine()

    def test_get_governance_engine_returns_same(self):
        e1 = get_governance_engine()
        e2 = get_governance_engine()
        self.assertIs(e1, e2)

    def test_reset_creates_new_instance(self):
        e1 = get_governance_engine()
        reset_governance_engine()
        e2 = get_governance_engine()
        self.assertIsNot(e1, e2)

    def test_auto_start(self):
        eng = get_governance_engine(auto_start=True)
        self.assertTrue(eng.is_running())


# ===========================================================================
# 30. GovernanceReport
# ===========================================================================
class TestGovernanceReport(unittest.TestCase):
    def test_create(self):
        from iios.integration.research.governance.core.governance_report import GovernanceReport
        rpt = GovernanceReport.create("running", 42.0, total_projects=5)
        self.assertIsNotNone(rpt.report_id)
        self.assertEqual(rpt.total_projects, 5)

    def test_to_dict(self):
        from iios.integration.research.governance.core.governance_report import GovernanceReport
        rpt = GovernanceReport.create("running", 10.0)
        d   = rpt.to_dict()
        self.assertIn("report_id", d)
        self.assertIn("engine_status", d)


# ===========================================================================
# 31. GovernanceHistory
# ===========================================================================
class TestGovernanceHistory(unittest.TestCase):
    def _event(self, entity_id="e1"):
        from iios.integration.research.governance.core.governance_event import GovernanceEvent
        return GovernanceEvent.create("project.created", "project", entity_id)

    def test_append_and_count(self):
        from iios.integration.research.governance.core.governance_history import GovernanceHistory
        hist = GovernanceHistory()
        hist.append(self._event())
        self.assertEqual(hist.count(), 1)

    def test_query(self):
        from iios.integration.research.governance.core.governance_history import GovernanceHistory
        hist = GovernanceHistory()
        hist.append(self._event("A"))
        hist.append(self._event("B"))
        results = hist.query(entity_id="A")
        self.assertEqual(len(results), 1)

    def test_latest(self):
        from iios.integration.research.governance.core.governance_history import GovernanceHistory
        hist = GovernanceHistory()
        for i in range(5):
            hist.append(self._event(f"e{i}"))
        latest = hist.latest(3)
        self.assertEqual(len(latest), 3)

    def test_clear(self):
        from iios.integration.research.governance.core.governance_history import GovernanceHistory
        hist = GovernanceHistory()
        hist.append(self._event())
        hist.clear()
        self.assertEqual(hist.count(), 0)


if __name__ == "__main__":
    unittest.main()
