"""iios/execution/oms/persistence/repository_validation.py
==================================================
RepositoryValidator — validates requests, contracts, and snapshots.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

from typing import Any

from iios.execution.oms.persistence.constants import (
    SCHEMA_VERSION,
    OperationType,
    PersistenceValidationCode,
    RecordStatus,
)
from iios.execution.oms.persistence.exceptions import (
    PersistenceValidationError,
    StorageContractViolationError,
    VersionConflictError,
)
from iios.execution.oms.persistence.repository_interface import REQUIRED_METHODS
from iios.execution.oms.persistence.repository_request import RepositoryRequest


class RepositoryValidator:
    """
    Stateless validator for persistence layer inputs.

    All methods raise appropriate PersistenceError subclasses on failure.
    Callers can also use ``collect_*`` variants that return error strings
    instead of raising.
    """

    # ------------------------------------------------------------------
    # Request validation
    # ------------------------------------------------------------------

    def validate_request(self, request: RepositoryRequest) -> None:
        """Raise PersistenceValidationError if request is malformed."""
        errors = self.collect_request_errors(request)
        if errors:
            raise PersistenceValidationError(
                f"Invalid {request.operation.value} request: {errors[0]}",
                errors=tuple(errors),
                correlation_id=request.correlation_id,
            )

    def collect_request_errors(self, request: RepositoryRequest) -> list[str]:
        errors: list[str] = []

        # Operations that require a record_id
        if request.operation in (
            OperationType.UPDATE,
            OperationType.DELETE,
            OperationType.ARCHIVE,
            OperationType.RESTORE,
            OperationType.FIND,
        ):
            if not request.record_id:
                errors.append(
                    f"{PersistenceValidationCode.MISSING_RECORD_ID.value}: "
                    f"record_id required for {request.operation.value}"
                )

        # SAVE and UPDATE require a payload
        if request.operation in (OperationType.SAVE, OperationType.UPDATE):
            if not request.payload:
                errors.append("payload must not be empty for SAVE/UPDATE")

        # SAVE requires a record_id
        if request.operation == OperationType.SAVE and not request.record_id:
            errors.append(
                f"{PersistenceValidationCode.MISSING_RECORD_ID.value}: "
                "record_id required for SAVE"
            )

        # Limit / offset sanity
        if request.limit < 1:
            errors.append("limit must be >= 1")
        if request.offset < 0:
            errors.append("offset must be >= 0")

        # Time range sanity
        if request.time_range_start and request.time_range_end:
            if request.time_range_start > request.time_range_end:
                errors.append("time_range_start must be <= time_range_end")

        return errors

    # ------------------------------------------------------------------
    # Duplicate / existence checks
    # ------------------------------------------------------------------

    def validate_no_duplicate(
        self,
        record_id:  str,
        repository: Any,   # StorageContract — avoid circular import
    ) -> None:
        """Raise DuplicateRecordError if record_id already exists."""
        from iios.execution.oms.persistence.exceptions import DuplicateRecordError
        if repository.exists(record_id):
            raise DuplicateRecordError(record_id)

    def validate_record_exists(
        self,
        record_id:  str,
        repository: Any,
    ) -> None:
        """Raise RecordNotFoundError if record_id is absent from active pool."""
        from iios.execution.oms.persistence.exceptions import RecordNotFoundError
        if not repository.exists(record_id):
            raise RecordNotFoundError(record_id)

    # ------------------------------------------------------------------
    # Version conflict
    # ------------------------------------------------------------------

    def validate_version(
        self,
        record_id:        str,
        expected_version: int,
        actual_version:   int,
    ) -> None:
        """Raise VersionConflictError if versions differ and expected != 0."""
        if expected_version != 0 and expected_version != actual_version:
            raise VersionConflictError(
                record_id, expected_version, actual_version
            )

    # ------------------------------------------------------------------
    # Contract inspection
    # ------------------------------------------------------------------

    def validate_contract(self, repository: Any) -> list[str]:
        """
        Return a list of missing required methods.

        An empty list means the repository satisfies the contract.
        """
        violations: list[str] = []
        for method_name in REQUIRED_METHODS:
            if not hasattr(repository, method_name):
                violations.append(f"missing '{method_name}'")
        return violations

    def assert_contract(self, repository: Any) -> None:
        """Raise StorageContractViolationError if any required method is missing."""
        repo_id    = getattr(repository, "repository_id", "<unknown>")
        violations = self.validate_contract(repository)
        if violations:
            raise StorageContractViolationError(
                repo_id, violations=tuple(violations)
            )

    # ------------------------------------------------------------------
    # Snapshot validation
    # ------------------------------------------------------------------

    def validate_snapshot(self, snapshot: Any) -> bool:
        """
        Return True if snapshot fields are internally consistent.

        Does not raise — callers decide how to handle False.
        """
        try:
            active_count = sum(
                1 for r in snapshot.records
                if r.status == RecordStatus.ACTIVE
            )
            archived_count = sum(
                1 for r in snapshot.records
                if r.status == RecordStatus.ARCHIVED
            )
            return (
                len(snapshot.records) == snapshot.total_records
                and active_count   == snapshot.total_active
                and archived_count == snapshot.total_archived
            )
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Schema version
    # ------------------------------------------------------------------

    def validate_schema_version(
        self,
        record_id:       str,
        actual_schema:   str,
        expected_schema: str = SCHEMA_VERSION,
    ) -> None:
        """Raise SchemaVersionError if schema versions do not match."""
        if actual_schema != expected_schema:
            from iios.execution.oms.persistence.exceptions import SchemaVersionError
            raise SchemaVersionError(record_id, expected_schema, actual_schema)
