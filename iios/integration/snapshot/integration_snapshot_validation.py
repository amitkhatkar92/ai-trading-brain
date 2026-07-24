"""
integration_snapshot_validation.py — iios.integration.snapshot
---------------------------------------------------------------
IntegrationSnapshotValidation — validates the structural and semantic
integrity of an IntegrationSnapshot before publication.

The 7 validation checks:
  1. IDENTIFIER_CONSISTENCY  — all IDs are non-empty
  2. VERSION_CONSISTENCY     — integration_version, framework_version,
                               snapshot_version are non-empty SemVer-ish
  3. CONNECTOR_CONSISTENCY   — connector_count ≥ 0; types non-null
  4. PROTOCOL_CONSISTENCY    — all protocol fields are non-empty
  5. SECURITY_CONSISTENCY    — authentication/authorization providers ≥ 0
  6. METADATA_INTEGRITY      — environment and framework_version present
  7. SNAPSHOT_COMPLETENESS   — snapshot_id and snapshot_timestamp present

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import SnapshotValidationCheck, VALIDATION_CHECK_ORDER
from .integration_snapshot import IntegrationSnapshot

_log = get_logger(__name__)


@dataclass(frozen=True)
class SnapshotValidationIssue:
    """A single validation finding — either an error or a warning."""
    check:    SnapshotValidationCheck
    severity: str      # "error" | "warning"
    message:  str


@dataclass(frozen=True)
class SnapshotValidationReport:
    """Immutable result of a snapshot validation run."""
    snapshot_id: str
    issues:      Tuple[SnapshotValidationIssue, ...]
    passed:      bool
    checked_at:  str

    @property
    def errors(self) -> List[SnapshotValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[SnapshotValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class IntegrationSnapshotValidation:
    """
    Validates IntegrationSnapshot integrity.

    Thread-safe (stateless — each call is independent).
    """

    def validate(self, snapshot: IntegrationSnapshot) -> SnapshotValidationReport:
        """
        Run all 7 integrity checks and return a SnapshotValidationReport.

        Parameters
        ----------
        snapshot : IntegrationSnapshot
            The snapshot to validate.

        Returns
        -------
        SnapshotValidationReport
            passed=True only when there are zero error-severity issues.
        """
        issues: List[SnapshotValidationIssue] = []

        for check in VALIDATION_CHECK_ORDER:
            found = self._run_check(check, snapshot)
            issues.extend(found)

        errors = [i for i in issues if i.severity == "error"]
        passed = len(errors) == 0

        _log.info(
            f"Snapshot validation: {snapshot.snapshot_id!r} "
            f"passed={passed} errors={len(errors)} warnings={len(issues)-len(errors)}"
        )

        return SnapshotValidationReport(
            snapshot_id = snapshot.snapshot_id,
            issues      = tuple(issues),
            passed      = passed,
            checked_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ── Per-check runners ─────────────────────────────────────────────

    def _run_check(
        self,
        check:    SnapshotValidationCheck,
        snapshot: IntegrationSnapshot,
    ) -> List[SnapshotValidationIssue]:
        runner = {
            SnapshotValidationCheck.IDENTIFIER_CONSISTENCY: self._check_identifiers,
            SnapshotValidationCheck.VERSION_CONSISTENCY:    self._check_versions,
            SnapshotValidationCheck.CONNECTOR_CONSISTENCY:  self._check_connectors,
            SnapshotValidationCheck.PROTOCOL_CONSISTENCY:   self._check_protocols,
            SnapshotValidationCheck.SECURITY_CONSISTENCY:   self._check_security,
            SnapshotValidationCheck.METADATA_INTEGRITY:     self._check_metadata,
            SnapshotValidationCheck.SNAPSHOT_COMPLETENESS:  self._check_completeness,
        }.get(check)
        if runner is None:
            return []
        return runner(snapshot)

    # ── Check 1: Identifier consistency ──────────────────────────────

    def _check_identifiers(
        self, snapshot: IntegrationSnapshot
    ) -> List[SnapshotValidationIssue]:
        issues: List[SnapshotValidationIssue] = []
        check = SnapshotValidationCheck.IDENTIFIER_CONSISTENCY

        for field_name, value in [
            ("snapshot_id",             snapshot.snapshot_id),
            ("integration_session_id",  snapshot.integration_session_id),
            ("integration_workflow_id", snapshot.integration_workflow_id),
            ("enterprise_session_id",   snapshot.enterprise_session_id),
        ]:
            if not value or not value.strip():
                issues.append(SnapshotValidationIssue(
                    check    = check,
                    severity = "error",
                    message  = f"Required identifier {field_name!r} is empty",
                ))
        return issues

    # ── Check 2: Version consistency ──────────────────────────────────

    def _check_versions(
        self, snapshot: IntegrationSnapshot
    ) -> List[SnapshotValidationIssue]:
        issues: List[SnapshotValidationIssue] = []
        check = SnapshotValidationCheck.VERSION_CONSISTENCY

        for field_name, value in [
            ("integration_version", snapshot.integration_version),
            ("framework_version",   snapshot.framework_version),
            ("snapshot_version",    snapshot.snapshot_version),
        ]:
            if not value or not value.strip():
                issues.append(SnapshotValidationIssue(
                    check    = check,
                    severity = "error",
                    message  = f"Required version field {field_name!r} is empty",
                ))
            elif not _is_semver_ish(value):
                issues.append(SnapshotValidationIssue(
                    check    = check,
                    severity = "warning",
                    message  = f"Version {field_name!r}={value!r} is not SemVer format",
                ))
        return issues

    # ── Check 3: Connector consistency ────────────────────────────────

    def _check_connectors(
        self, snapshot: IntegrationSnapshot
    ) -> List[SnapshotValidationIssue]:
        issues: List[SnapshotValidationIssue] = []
        check = SnapshotValidationCheck.CONNECTOR_CONSISTENCY
        cs    = snapshot.connector_summary

        if cs.connector_count < 0:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "error",
                message  = f"connector_count is negative: {cs.connector_count}",
            ))
        if cs.connector_availability < 0.0 or cs.connector_availability > 1.0:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "warning",
                message  = (
                    f"connector_availability {cs.connector_availability} "
                    f"is outside [0.0, 1.0]"
                ),
            ))
        cs_conn = snapshot.connectivity_summary
        if cs_conn.registered_connectors < 0:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "error",
                message  = "registered_connectors in connectivity_summary is negative",
            ))
        return issues

    # ── Check 4: Protocol consistency ─────────────────────────────────

    def _check_protocols(
        self, snapshot: IntegrationSnapshot
    ) -> List[SnapshotValidationIssue]:
        issues: List[SnapshotValidationIssue] = []
        check = SnapshotValidationCheck.PROTOCOL_CONSISTENCY
        ps    = snapshot.protocol_summary

        known_states = {"enabled", "disabled", "unknown", "degraded", "unavailable"}
        for proto, val in [
            ("rest",                ps.rest),
            ("graphql",             ps.graphql),
            ("grpc",                ps.grpc),
            ("websocket",           ps.websocket),
            ("kafka",               ps.kafka),
            ("rabbitmq",            ps.rabbitmq),
            ("redis_streams",       ps.redis_streams),
            ("database_connectors", ps.database_connectors),
            ("webhook_services",    ps.webhook_services),
            ("file_transfer",       ps.file_transfer),
        ]:
            if not val:
                issues.append(SnapshotValidationIssue(
                    check    = check,
                    severity = "error",
                    message  = f"Protocol field {proto!r} is empty",
                ))
            elif val not in known_states:
                issues.append(SnapshotValidationIssue(
                    check    = check,
                    severity = "warning",
                    message  = f"Protocol {proto!r} has unrecognized state: {val!r}",
                ))
        return issues

    # ── Check 5: Security consistency ────────────────────────────────

    def _check_security(
        self, snapshot: IntegrationSnapshot
    ) -> List[SnapshotValidationIssue]:
        issues: List[SnapshotValidationIssue] = []
        check = SnapshotValidationCheck.SECURITY_CONSISTENCY
        ss    = snapshot.security_summary

        if ss.authentication_providers < 0:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "error",
                message  = "authentication_providers is negative",
            ))
        if ss.authorization_providers < 0:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "error",
                message  = "authorization_providers is negative",
            ))
        if ss.certificates < 0:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "warning",
                message  = "certificates count is negative",
            ))
        if ss.secrets < 0:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "warning",
                message  = "secrets count is negative",
            ))
        return issues

    # ── Check 6: Metadata integrity ───────────────────────────────────

    def _check_metadata(
        self, snapshot: IntegrationSnapshot
    ) -> List[SnapshotValidationIssue]:
        issues: List[SnapshotValidationIssue] = []
        check = SnapshotValidationCheck.METADATA_INTEGRITY
        meta  = snapshot.metadata

        if not meta.environment or not meta.environment.strip():
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "warning",
                message  = "Metadata environment is empty",
            ))
        if not meta.framework_version or not meta.framework_version.strip():
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "error",
                message  = "Metadata framework_version is empty",
            ))
        if not meta.generated_at:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "warning",
                message  = "Metadata generated_at is empty",
            ))
        return issues

    # ── Check 7: Snapshot completeness ───────────────────────────────

    def _check_completeness(
        self, snapshot: IntegrationSnapshot
    ) -> List[SnapshotValidationIssue]:
        issues: List[SnapshotValidationIssue] = []
        check = SnapshotValidationCheck.SNAPSHOT_COMPLETENESS

        if not snapshot.snapshot_id:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "error",
                message  = "snapshot_id is missing",
            ))
        if not snapshot.snapshot_timestamp:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "error",
                message  = "snapshot_timestamp is missing",
            ))
        if not snapshot.created_at:
            issues.append(SnapshotValidationIssue(
                check    = check,
                severity = "warning",
                message  = "created_at is missing",
            ))
        return issues


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════


def _is_semver_ish(version: str) -> bool:
    """
    Return True if version looks like SemVer (MAJOR.MINOR.PATCH) or
    a simple dotted-number string (e.g. "1.0", "2").
    """
    parts = version.split(".")
    if not (1 <= len(parts) <= 4):
        return False
    for p in parts:
        if not p.isdigit():
            return False
    return True
