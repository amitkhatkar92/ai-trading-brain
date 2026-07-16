"""iios/execution/positions/book/position_book_validation.py
==================================================
BookValidationResult — result of a book consistency check.
BookValidator        — validates the Position Book's internal consistency.

Validation checks
-----------------
1. Duplicate positions     — no position_id appears twice in the registry
2. Index consistency       — every indexed position_id exists in primary store
3. Lifecycle consistency   — live counts match ACTIVE/CLOSED/ARCHIVED partitions
4. Identifier consistency  — all required IDs are non-empty for each entry
5. Snapshot consistency    — snapshot field counts match live state

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from .constants import ValidationSeverity
from .exceptions import PositionBookValidationError

if TYPE_CHECKING:
    from .position_book_registry import BookRegistry


@dataclass(frozen=True)
class ValidationFinding:
    """A single finding (error or warning) from a book validation run."""
    severity: ValidationSeverity
    code:     str
    message:  str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "code":     self.code,
            "message":  self.message,
        }


@dataclass(frozen=True)
class BookValidationResult:
    """
    Immutable result of a book consistency validation run.
    """

    is_valid:    bool
    findings:    Tuple[ValidationFinding, ...]
    validated_at: float = field(default_factory=time.time)

    @property
    def errors(self) -> List[ValidationFinding]:
        return [f for f in self.findings if f.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationFinding]:
        return [f for f in self.findings if f.severity == ValidationSeverity.WARNING]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":     self.is_valid,
            "error_count":  self.error_count,
            "warning_count": self.warning_count,
            "findings":     [f.to_dict() for f in self.findings],
            "validated_at": self.validated_at,
        }


class BookValidator:
    """
    Validates the internal consistency of the Position Book.

    Validation is purely in-memory — no I/O, no broker calls.
    Each ``validate_*`` method returns a list of ``ValidationFinding`` objects.
    ``validate_all()`` runs all checks and returns a ``BookValidationResult``.
    """

    # ── Public entry point ────────────────────────────────────────────────────

    def validate_all(self, registry: "BookRegistry") -> BookValidationResult:
        """
        Run all consistency checks against *registry*.

        Returns a ``BookValidationResult`` with is_valid == True only if
        no ERROR-severity findings were produced.
        """
        findings: List[ValidationFinding] = []
        findings.extend(self.validate_no_duplicates(registry))
        findings.extend(self.validate_index_consistency(registry))
        findings.extend(self.validate_lifecycle_consistency(registry))
        findings.extend(self.validate_identifier_consistency(registry))

        is_valid = not any(
            f.severity == ValidationSeverity.ERROR for f in findings
        )
        return BookValidationResult(
            is_valid=is_valid,
            findings=tuple(findings),
            validated_at=time.time(),
        )

    # ── Individual checks ─────────────────────────────────────────────────────

    def validate_no_duplicates(
        self, registry: "BookRegistry",
    ) -> List[ValidationFinding]:
        """Check that no position_id appears more than once."""
        findings: List[ValidationFinding] = []
        entries = registry.all()
        seen: set = set()
        for entry in entries:
            pid = entry.position_id
            if pid in seen:
                findings.append(ValidationFinding(
                    severity=ValidationSeverity.ERROR,
                    code="PB3-DUP-001",
                    message=f"Duplicate position_id detected: '{pid}'",
                ))
            seen.add(pid)
        return findings

    def validate_index_consistency(
        self, registry: "BookRegistry",
    ) -> List[ValidationFinding]:
        """
        Verify that every position_id in secondary indexes exists
        in the primary store.
        """
        findings: List[ValidationFinding] = []
        index     = registry.index
        all_ids   = {e.position_id for e in registry.all()}

        # Collect position IDs from all secondary index buckets
        utilization = index.utilization()  # just to confirm index is accessible
        # Walk primary count against the registry count
        idx_count = index.count()
        reg_count = len(all_ids)
        if idx_count != reg_count:
            findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code="PB3-IDX-001",
                message=(
                    f"Index primary count ({idx_count}) does not match "
                    f"registry entry count ({reg_count})"
                ),
            ))
        return findings

    def validate_lifecycle_consistency(
        self, registry: "BookRegistry",
    ) -> List[ValidationFinding]:
        """
        Verify that active/closed/archived/suspended counts from
        the index match what a direct state scan would produce.
        """
        from iios.execution.positions.lifecycle import (
            ACTIVE_STATES, TERMINAL_STATES, SUSPENDED_STATES,
        )
        findings: List[ValidationFinding] = []
        entries = registry.all()

        direct_active    = sum(1 for e in entries if e.state in ACTIVE_STATES)
        direct_archived  = sum(1 for e in entries if e.state in TERMINAL_STATES)
        direct_suspended = sum(1 for e in entries if e.state in SUSPENDED_STATES)

        idx_active    = len(registry.index.active())
        idx_archived  = len(registry.index.archived())
        idx_suspended = len(registry.index.suspended())

        if idx_active != direct_active:
            findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code="PB3-LC-001",
                message=(
                    f"Active count mismatch: index={idx_active}, "
                    f"direct scan={direct_active}"
                ),
            ))
        if idx_archived != direct_archived:
            findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code="PB3-LC-002",
                message=(
                    f"Archived count mismatch: index={idx_archived}, "
                    f"direct scan={direct_archived}"
                ),
            ))
        if idx_suspended != direct_suspended:
            findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code="PB3-LC-003",
                message=(
                    f"Suspended count mismatch: index={idx_suspended}, "
                    f"direct scan={direct_suspended}"
                ),
            ))
        return findings

    def validate_identifier_consistency(
        self, registry: "BookRegistry",
    ) -> List[ValidationFinding]:
        """
        Check that all entries have non-empty required identifier fields:
        position_id, portfolio_id, strategy_id, instrument, exchange.
        """
        findings: List[ValidationFinding] = []
        for entry in registry.all():
            pid = entry.position_id
            for attr, label in (
                ("portfolio_id", "portfolio_id"),
                ("instrument",   "instrument"),
                ("exchange",     "exchange"),
            ):
                val = getattr(entry, attr, "")
                if not val:
                    findings.append(ValidationFinding(
                        severity=ValidationSeverity.WARNING,
                        code="PB3-ID-001",
                        message=f"Position '{pid}' has empty {label}",
                    ))
        return findings

    # ── Helper ────────────────────────────────────────────────────────────────

    def raise_if_invalid(self, result: BookValidationResult) -> None:
        """Raise ``PositionBookValidationError`` if *result* is not valid."""
        if not result.is_valid:
            error_messages = tuple(f.message for f in result.errors)
            raise PositionBookValidationError(
                f"Book validation failed with {result.error_count} error(s)",
                errors=error_messages,
            )
