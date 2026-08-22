"""
tests/unit/bootstrap/test_dependency_loader.py
================================================
Unit tests for DependencyLoader and PackageRegistry.
"""

from __future__ import annotations

import pytest

from iios.bootstrap.dependency_loader import (
    DependencyLoader,
    DependencyTier,
    PackageRegistry,
    PackageSpec,
)
from iios.bootstrap.startup_state import ValidationSeverity


class TestPackageRegistry:
    def test_register_and_query(self) -> None:
        reg = PackageRegistry()
        reg.register("pandas", True, "2.1.0")
        assert reg.is_available("pandas") is True
        assert reg.get_version("pandas") == "2.1.0"

    def test_unavailable_returns_false(self) -> None:
        reg = PackageRegistry()
        assert reg.is_available("nonexistent_pkg_xyz") is False

    def test_available_packages_list(self) -> None:
        reg = PackageRegistry()
        reg.register("pkg_a", True, "1.0")
        reg.register("pkg_b", False, "")
        assert "pkg_a" in reg.available_packages()
        assert "pkg_b" not in reg.available_packages()

    def test_to_dict(self) -> None:
        reg = PackageRegistry()
        reg.register("mypkg", True, "1.2.3")
        d = reg.to_dict()
        assert "mypkg" in d
        assert d["mypkg"]["available"] is True
        assert d["mypkg"]["version"] == "1.2.3"


class TestDependencyLoader:
    def test_stdlib_packages_are_available(self) -> None:
        """json and os are always available — sanity check probe mechanism."""
        spec = PackageSpec(
            import_name="json",
            pip_name="json",
            tier=DependencyTier.CRITICAL,
            feature="JSON stdlib",
        )
        loader = DependencyLoader(extra_packages=[spec])
        report = loader.load()
        assert report.registry.is_available("json") is True

    def test_fake_critical_package_added_to_missing_critical(self) -> None:
        spec = PackageSpec(
            import_name="iios_totally_nonexistent_pkg_xyz",
            pip_name="iios_totally_nonexistent_pkg_xyz",
            tier=DependencyTier.CRITICAL,
            feature="test",
        )
        loader = DependencyLoader(extra_packages=[spec])
        report = loader.load()
        assert "iios_totally_nonexistent_pkg_xyz" in report.missing_critical
        assert report.passed is False

    def test_fake_optional_package_does_not_block(self) -> None:
        spec = PackageSpec(
            import_name="iios_totally_nonexistent_pkg_abc",
            pip_name="iios_totally_nonexistent_pkg_abc",
            tier=DependencyTier.OPTIONAL,
            feature="test",
        )
        loader = DependencyLoader(extra_packages=[spec])
        report = loader.load()
        assert "iios_totally_nonexistent_pkg_abc" in report.missing_optional
        assert report.passed is True  # optional missing = still passes

    def test_missing_critical_produces_critical_finding(self) -> None:
        spec = PackageSpec(
            import_name="iios_totally_nonexistent_xyz2",
            pip_name="iios_totally_nonexistent_xyz2",
            tier=DependencyTier.CRITICAL,
        )
        loader = DependencyLoader(extra_packages=[spec])
        report = loader.load()
        critical_findings = [
            f for f in report.findings if f.severity == ValidationSeverity.CRITICAL
        ]
        assert len(critical_findings) >= 1

    def test_missing_optional_produces_info_finding(self) -> None:
        spec = PackageSpec(
            import_name="iios_totally_nonexistent_xyz3",
            pip_name="iios_totally_nonexistent_xyz3",
            tier=DependencyTier.OPTIONAL,
        )
        loader = DependencyLoader(extra_packages=[spec])
        report = loader.load()
        info_findings = [
            f for f in report.findings if f.severity == ValidationSeverity.INFO
        ]
        assert any("iios_totally_nonexistent_xyz3" in f.message for f in info_findings)

    def test_load_package_returns_module(self) -> None:
        loader = DependencyLoader()
        mod = loader.load_package("sys")
        assert mod is not None
        import sys as _sys
        assert mod is _sys

    def test_load_package_returns_none_for_missing(self) -> None:
        loader = DependencyLoader()
        mod = loader.load_package("iios_absolutely_fake_module_xyz")
        assert mod is None

    def test_summary_string(self) -> None:
        spec = PackageSpec("sys", "sys", DependencyTier.CRITICAL)
        loader = DependencyLoader(extra_packages=[spec])
        report = loader.load()
        assert "available" in report.summary
        assert "/" in report.summary
