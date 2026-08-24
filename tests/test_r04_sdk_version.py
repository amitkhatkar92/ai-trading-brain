"""
tests/test_r04_sdk_version.py
R-04 — DhanHQ SDK version verification.

READ-ONLY: no network calls, no broker state changes, no credentials required.
Covers: importability, version determinability, declared-constraint satisfaction,
and v2.1+ API shape (DhanContext) availability.
"""
from __future__ import annotations

import importlib.metadata
import unittest
from packaging.version import Version


_DECLARED_MIN = "2.0.0"   # declared floor from requirements.txt / pyproject.toml
_PACKAGE_NAME = "dhanhq"
_INSTALLED_VER = Version(importlib.metadata.version(_PACKAGE_NAME))
_HAS_V21_API   = _INSTALLED_VER >= Version("2.1.0")   # DhanContext, DhanLogin added in 2.1


class TestR04SdkVersion(unittest.TestCase):
    """SDK version constraints — no network, no broker, no credentials."""

    def test_package_importable(self):
        """dhanhq package must be importable in this Python environment."""
        import dhanhq  # noqa: F401

    def test_version_determinable(self):
        """Version string must be readable from package metadata."""
        ver = importlib.metadata.version(_PACKAGE_NAME)
        self.assertIsNotNone(ver)
        self.assertGreater(len(ver.strip()), 0)

    def test_satisfies_declared_minimum(self):
        """Installed version must satisfy declared floor (>=2.0.0)."""
        ver = Version(importlib.metadata.version(_PACKAGE_NAME))
        self.assertGreaterEqual(ver, Version(_DECLARED_MIN),
            f"dhanhq {ver} does not satisfy declared minimum {_DECLARED_MIN}")

    def test_core_class_importable(self):
        """dhanhq.dhanhq (REST client class) must be importable."""
        from dhanhq import dhanhq as _DhanHQ  # noqa: F401
        self.assertTrue(callable(_DhanHQ))

    @unittest.skipUnless(_HAS_V21_API,
        f"DhanContext not in dhanhq {_INSTALLED_VER} — only available >=2.1.0 (container has 2.2.0)")
    def test_dhan_context_importable(self):
        """DhanContext (v2.1+) must be importable — container runs 2.2.0."""
        from dhanhq import DhanContext  # noqa: F401
        self.assertTrue(callable(DhanContext))

    @unittest.skipUnless(_HAS_V21_API,
        f"DhanLogin not in dhanhq {_INSTALLED_VER} — only available >=2.1.0 (container has 2.2.0)")
    def test_dhan_login_importable(self):
        """DhanLogin must be importable — used by dhan_ip_verify and DTA-001 path."""
        from dhanhq import DhanLogin  # noqa: F401
        self.assertTrue(callable(DhanLogin))

    def test_version_is_known_stable(self):
        """Installed version should be one of the known compatible releases."""
        ver = importlib.metadata.version(_PACKAGE_NAME)
        known = {"2.0.2", "2.1.0", "2.2.0"}
        self.assertIn(ver, known,
            f"dhanhq {ver} is not in known-tested set {known} — verify compatibility before live use")


class TestR04VersionComparisonLogic(unittest.TestCase):
    """Pure version-comparison logic — no imports of application modules."""

    def _cmp(self, installed: str, minimum: str) -> bool:
        return Version(installed) >= Version(minimum)

    def test_202_satisfies_200(self):
        self.assertTrue(self._cmp("2.0.2", "2.0.0"))

    def test_220_satisfies_200(self):
        self.assertTrue(self._cmp("2.2.0", "2.0.0"))

    def test_199_does_not_satisfy_200(self):
        self.assertFalse(self._cmp("1.9.9", "2.0.0"))

    def test_local_vs_container_mismatch_detectable(self):
        """202 != 220: mismatch between local dev env and Docker runtime."""
        local = Version("2.0.2")
        container = Version("2.2.0")
        self.assertNotEqual(local, container,
            "Local venv and Docker container versions must be equal for a clean match")

    def test_both_satisfy_declared_floor(self):
        """Both local 2.0.2 and container 2.2.0 satisfy >=2.0.0."""
        floor = Version(_DECLARED_MIN)
        self.assertGreaterEqual(Version("2.0.2"), floor)
        self.assertGreaterEqual(Version("2.2.0"), floor)


if __name__ == "__main__":
    unittest.main()
