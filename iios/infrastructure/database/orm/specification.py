"""
iios/infrastructure/database/orm/specification.py
==================================================
Specification pattern for composable, type-safe query predicates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

__all__ = [
    "Specification",
    "Eq", "Ne", "Gt", "Ge", "Lt", "Le",
    "Like", "ILike", "In", "NotIn",
    "IsNull", "IsNotNull",
    "Between",
    "And", "Or", "Not",
    "Always", "Never",
]


class Specification(ABC):
    """Base class for query specifications.

    A Specification produces a SQL fragment and parameters::

        spec = Eq("symbol", "RELIANCE") & Gt("price", 2000)
        sql_where, params = spec.to_sql()
        # sql_where: "symbol = ? AND price > ?"
        # params:    ("RELIANCE", 2000)
    """

    @abstractmethod
    def to_sql(self) -> tuple[str, list[Any]]:
        """Return (sql_fragment, params_list)."""

    def __and__(self, other: "Specification") -> "And":
        return And(self, other)

    def __or__(self, other: "Specification") -> "Or":
        return Or(self, other)

    def __invert__(self) -> "Not":
        return Not(self)


# ── Comparisons ───────────────────────────────────────────────────────────────

class _BinarySpec(Specification):
    _OP: str = "="

    def __init__(self, column: str, value: Any) -> None:
        self._col = column
        self._val = value

    def to_sql(self) -> tuple[str, list[Any]]:
        return f"{self._col} {self._OP} ?", [self._val]


class Eq(_BinarySpec):
    """column = value"""
    _OP = "="


class Ne(_BinarySpec):
    """column != value"""
    _OP = "!="


class Gt(_BinarySpec):
    """column > value"""
    _OP = ">"


class Ge(_BinarySpec):
    """column >= value"""
    _OP = ">="


class Lt(_BinarySpec):
    """column < value"""
    _OP = "<"


class Le(_BinarySpec):
    """column <= value"""
    _OP = "<="


class Like(Specification):
    """column LIKE pattern  (use % and _ wildcards)"""

    def __init__(self, column: str, pattern: str) -> None:
        self._col = column
        self._pat = pattern

    def to_sql(self) -> tuple[str, list[Any]]:
        return f"{self._col} LIKE ?", [self._pat]


class ILike(Specification):
    """Case-insensitive LIKE (lowercased both sides for SQLite compatibility)."""

    def __init__(self, column: str, pattern: str) -> None:
        self._col = column
        self._pat = pattern.lower()

    def to_sql(self) -> tuple[str, list[Any]]:
        return f"LOWER({self._col}) LIKE ?", [self._pat]


class In(Specification):
    """column IN (v1, v2, ...)"""

    def __init__(self, column: str, values: Sequence[Any]) -> None:
        self._col = column
        self._vals = list(values)

    def to_sql(self) -> tuple[str, list[Any]]:
        if not self._vals:
            return "1=0", []  # empty IN is always false
        placeholders = ", ".join("?" * len(self._vals))
        return f"{self._col} IN ({placeholders})", list(self._vals)


class NotIn(Specification):
    """column NOT IN (v1, v2, ...)"""

    def __init__(self, column: str, values: Sequence[Any]) -> None:
        self._col = column
        self._vals = list(values)

    def to_sql(self) -> tuple[str, list[Any]]:
        if not self._vals:
            return "1=1", []  # empty NOT IN is always true
        placeholders = ", ".join("?" * len(self._vals))
        return f"{self._col} NOT IN ({placeholders})", list(self._vals)


class IsNull(Specification):
    """column IS NULL"""

    def __init__(self, column: str) -> None:
        self._col = column

    def to_sql(self) -> tuple[str, list[Any]]:
        return f"{self._col} IS NULL", []


class IsNotNull(Specification):
    """column IS NOT NULL"""

    def __init__(self, column: str) -> None:
        self._col = column

    def to_sql(self) -> tuple[str, list[Any]]:
        return f"{self._col} IS NOT NULL", []


class Between(Specification):
    """column BETWEEN low AND high"""

    def __init__(self, column: str, low: Any, high: Any) -> None:
        self._col = column
        self._low = low
        self._high = high

    def to_sql(self) -> tuple[str, list[Any]]:
        return f"{self._col} BETWEEN ? AND ?", [self._low, self._high]


# ── Composite ─────────────────────────────────────────────────────────────────

class And(Specification):
    """spec_a AND spec_b"""

    def __init__(self, *specs: Specification) -> None:
        self._specs = list(specs)

    def to_sql(self) -> tuple[str, list[Any]]:
        parts, params = [], []
        for s in self._specs:
            frag, p = s.to_sql()
            parts.append(f"({frag})")
            params.extend(p)
        return " AND ".join(parts), params


class Or(Specification):
    """spec_a OR spec_b"""

    def __init__(self, *specs: Specification) -> None:
        self._specs = list(specs)

    def to_sql(self) -> tuple[str, list[Any]]:
        parts, params = [], []
        for s in self._specs:
            frag, p = s.to_sql()
            parts.append(f"({frag})")
            params.extend(p)
        return " OR ".join(parts), params


class Not(Specification):
    """NOT spec"""

    def __init__(self, spec: Specification) -> None:
        self._spec = spec

    def to_sql(self) -> tuple[str, list[Any]]:
        frag, params = self._spec.to_sql()
        return f"NOT ({frag})", params


# ── Constants ─────────────────────────────────────────────────────────────────

class Always(Specification):
    """Always-true specification (pass-through)."""

    def to_sql(self) -> tuple[str, list[Any]]:
        return "1=1", []


class Never(Specification):
    """Always-false specification."""

    def to_sql(self) -> tuple[str, list[Any]]:
        return "1=0", []
