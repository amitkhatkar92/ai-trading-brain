"""
knowledge_snapshot_metadata.py — iios.knowledge.snapshot
----------------------------------------------------------
SnapshotMetadataBuilder — constructs SnapshotMetadata from
runtime environment and component context.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import os
import platform
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from .constants import BUILD_VERSION, FRAMEWORK_VERSION
from .knowledge_snapshot import SnapshotMetadata


class SnapshotMetadataBuilder:
    """
    Constructs a SnapshotMetadata value object from runtime context.

    Usage:
        metadata = (
            SnapshotMetadataBuilder()
            .with_environment("production")
            .with_source_components(["iios.lifecycle", "iios.engine"])
            .with_correlation_id("corr-001")
            .build()
        )
    """

    def __init__(self) -> None:
        self._environment:       str       = self._detect_environment()
        self._framework_version: str       = FRAMEWORK_VERSION
        self._build_version:     str       = BUILD_VERSION
        self._source_components: List[str] = []
        self._correlation_ids:   List[str] = []
        self._trace_ids:         List[str] = []

    # ------------------------------------------------------------------
    # Fluent API
    # ------------------------------------------------------------------

    def with_environment(self, env: str) -> "SnapshotMetadataBuilder":
        self._environment = env
        return self

    def with_framework_version(self, version: str) -> "SnapshotMetadataBuilder":
        self._framework_version = version
        return self

    def with_build_version(self, version: str) -> "SnapshotMetadataBuilder":
        self._build_version = version
        return self

    def with_source_components(
        self, components: List[str],
    ) -> "SnapshotMetadataBuilder":
        self._source_components = list(components)
        return self

    def add_source_component(self, component: str) -> "SnapshotMetadataBuilder":
        if component not in self._source_components:
            self._source_components.append(component)
        return self

    def with_correlation_id(self, cid: str) -> "SnapshotMetadataBuilder":
        if cid not in self._correlation_ids:
            self._correlation_ids.append(cid)
        return self

    def with_trace_id(self, tid: str) -> "SnapshotMetadataBuilder":
        if tid not in self._trace_ids:
            self._trace_ids.append(tid)
        return self

    def auto_trace(self) -> "SnapshotMetadataBuilder":
        """Generate and add a new trace ID."""
        self._trace_ids.append(f"trace-{uuid.uuid4().hex[:12]}")
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> SnapshotMetadata:
        return SnapshotMetadata(
            environment       = self._environment,
            framework_version = self._framework_version,
            build_version     = self._build_version,
            source_components = tuple(self._source_components),
            correlation_ids   = tuple(self._correlation_ids),
            trace_ids         = tuple(self._trace_ids),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_environment() -> str:
        """Infer environment from IIOS_ENV → ENV → hostname prefix."""
        env = (
            os.environ.get("IIOS_ENV")
            or os.environ.get("ENV")
            or os.environ.get("ENVIRONMENT")
        )
        if env:
            return env.lower()
        host = platform.node().lower()
        if "prod" in host:
            return "production"
        if "stag" in host:
            return "staging"
        if "dev" in host or "local" in host:
            return "development"
        return "production"

    @classmethod
    def default(cls) -> SnapshotMetadata:
        """Return a minimal metadata object with just environment info."""
        return (
            cls()
            .with_source_components(
                [
                    "iios.knowledge.lifecycle",
                    "iios.knowledge.engine",
                    "iios.knowledge.policies",
                    "iios.knowledge.intelligence",
                ]
            )
            .auto_trace()
            .build()
        )
