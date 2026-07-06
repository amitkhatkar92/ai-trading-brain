"""
iios/configuration/configuration_resolver.py
==============================================
Variable reference resolution for configuration values.

Supports:
  - ``${ENV_VAR}``              — environment variable substitution
  - ``${ENV_VAR:-default}``     — environment variable with fallback
  - ``${section.field}``        — cross-reference to another config key

Circular reference detection raises ``ConfigurationMergeError``.
Unresolved references that are not optional trigger a warning but are
left as-is (the raw reference string).

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from .configuration_exception import ConfigurationMergeError

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationResolver",
]


# Regex to match ${VAR}, ${VAR:-default}, ${section.field}
_REF_RE = re.compile(r"\$\{([^}]+)\}")


class ConfigurationResolver:
    """Resolves variable references within a configuration dict.

    All string values in the dict are scanned for ``${...}`` patterns.
    Resolution order:
        1. env vars from the provided *env* dict (defaults to ``os.environ``)
        2. cross-references within *data* itself using dotted key path

    Args:
        max_depth: Maximum recursion depth for nested references.
        strict: If ``True``, raise on unresolved references. Default: ``False``
                (leave unresolved references as raw strings and log a warning).
    """

    def __init__(
        self,
        max_depth: int = 10,
        strict: bool = False,
    ) -> None:
        self._max_depth = max_depth
        self._strict = strict

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        data: dict[str, Any],
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Resolve all variable references in *data*.

        Args:
            data: Nested configuration dict (will NOT be mutated).
            env:  Environment variables dict. Defaults to ``os.environ``.

        Returns:
            New dict with all resolvable references substituted.
        """
        if env is None:
            env = dict(os.environ)

        # Two-pass: first pass fills a flat lookup table for cross-references
        flat = _flatten(data)
        resolved_flat = self._resolve_flat(flat, env)
        return _unflatten(resolved_flat)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_flat(
        self,
        flat: dict[str, Any],
        env: dict[str, str],
    ) -> dict[str, Any]:
        """Resolve references in a flattened (dotted-key) dict."""
        result: dict[str, Any] = {}
        in_progress: set[str] = set()

        def _resolve_key(key: str, depth: int) -> Any:
            if depth > self._max_depth:
                raise ConfigurationMergeError(
                    f"Maximum reference resolution depth ({self._max_depth}) exceeded at key {key!r}",
                    key=key,
                )
            if key in in_progress:
                raise ConfigurationMergeError(
                    f"Circular reference detected at key {key!r}",
                    key=key,
                )
            if key in result:
                return result[key]

            val = flat.get(key)
            if not isinstance(val, str):
                result[key] = val
                return val

            in_progress.add(key)
            try:
                resolved = self._resolve_string(val, env, flat, _resolve_key, depth + 1)
            finally:
                in_progress.discard(key)

            result[key] = resolved
            return resolved

        for key in flat:
            _resolve_key(key, 0)

        return result

    def _resolve_string(
        self,
        value: str,
        env: dict[str, str],
        flat: dict[str, Any],
        resolve_key_fn: Any,
        depth: int,
    ) -> Any:
        """Expand all ``${...}`` patterns within *value*.

        If the entire string is one reference and the resolved value is
        not a string (e.g. it's an int or bool), return the resolved type
        directly (no string wrapping).
        """
        # Check if the whole string is a single reference
        single_match = _REF_RE.fullmatch(value.strip())
        if single_match:
            replacement = self._lookup(
                single_match.group(1), env, flat, resolve_key_fn, depth
            )
            return replacement

        # Otherwise, substitute all occurrences and keep as string
        def _sub(m: re.Match) -> str:
            replacement = self._lookup(m.group(1), env, flat, resolve_key_fn, depth)
            return str(replacement)

        return _REF_RE.sub(_sub, value)

    def _lookup(
        self,
        ref: str,
        env: dict[str, str],
        flat: dict[str, Any],
        resolve_key_fn: Any,
        depth: int,
    ) -> Any:
        """Look up a reference token (without surrounding ``${`` / ``}``)."""
        # Check for default value: ${VAR:-default}
        default: Any = None
        has_default = False
        if ":-" in ref:
            ref, default_str = ref.split(":-", 1)
            default = default_str
            has_default = True

        # 1. Environment variable
        if ref in env:
            return env[ref]

        # 2. Cross-reference to another config key (dotted path)
        if "." in ref:
            if ref in flat:
                return resolve_key_fn(ref, depth)

        # 3. Fall back to default
        if has_default:
            return default

        # 4. Unresolved
        full_ref = "${" + ref + (":-" + str(default) if has_default else "") + "}"
        if self._strict:
            raise ConfigurationMergeError(
                f"Unresolved configuration reference: {full_ref!r}",
                key=ref,
            )
        logger.warning("Unresolved configuration reference: %s", full_ref)
        return full_ref


# ---------------------------------------------------------------------------
# Flatten / unflatten helpers
# ---------------------------------------------------------------------------


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Recursively flatten a nested dict to dotted-key form."""
    result: dict[str, Any] = {}
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_flatten(v, full_key))
        else:
            result[full_key] = v
    return result


def _unflatten(flat: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct a nested dict from a flattened dotted-key dict."""
    result: dict[str, Any] = {}
    for key, value in flat.items():
        parts = key.split(".")
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return result
