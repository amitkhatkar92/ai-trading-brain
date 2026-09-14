"""reproducibility/environment_snapshot.py — Runtime environment capture."""
from __future__ import annotations

import os
import platform
import socket
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


def _capture_packages() -> dict[str, str]:
    """Return {package: version} for all installed distributions."""
    try:
        import importlib.metadata as meta
        return {d.name: d.version for d in meta.distributions()}
    except Exception:
        try:
            import pkg_resources  # type: ignore
            return {pkg.key: pkg.version for pkg in pkg_resources.working_set}
        except Exception:
            return {}


_SAFE_ENV_PREFIXES = ("PYTHON", "LANG", "LC_", "TZ", "HOME", "USER", "VIRTUAL_ENV")


@dataclass
class EnvironmentSnapshot:
    """
    Complete snapshot of the Python runtime environment at a point in time.

    Captures Python version, OS, hostname, installed packages, and
    optionally a filtered set of environment variables.
    """
    snapshot_id:  str
    python_version: str
    platform:     str
    hostname:     str
    packages:     dict[str, str]    # package → version
    env_vars:     dict[str, str]    # captured env vars (filtered)
    captured_at:  float

    @classmethod
    def capture(
        cls,
        *,
        include_env_vars: bool = False,
        snapshot_id: Optional[str] = None,
    ) -> "EnvironmentSnapshot":
        env_vars: dict[str, str] = {}
        if include_env_vars:
            for k, v in os.environ.items():
                if any(k.upper().startswith(p) for p in _SAFE_ENV_PREFIXES):
                    env_vars[k] = v
        return cls(
            snapshot_id    = snapshot_id or f"env_{uuid.uuid4().hex[:10]}",
            python_version = sys.version.split()[0],
            platform       = platform.platform(),
            hostname       = socket.gethostname(),
            packages       = _capture_packages(),
            env_vars       = env_vars,
            captured_at    = time.time(),
        )

    def diff(self, other: "EnvironmentSnapshot") -> dict[str, Any]:
        """Return changed, added, and removed packages compared to ``other``."""
        added   = {k: v for k, v in self.packages.items() if k not in other.packages}
        removed = {k: v for k, v in other.packages.items() if k not in self.packages}
        changed = {
            k: {"from": other.packages[k], "to": v}
            for k, v in self.packages.items()
            if k in other.packages and other.packages[k] != v
        }
        return {"added": added, "removed": removed, "changed": changed}

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "python_version": self.python_version,
            "platform":       self.platform,
            "hostname":       self.hostname,
            "package_count":  len(self.packages),
            "packages":       self.packages,
            "env_var_count":  len(self.env_vars),
            "captured_at":    self.captured_at,
        }
