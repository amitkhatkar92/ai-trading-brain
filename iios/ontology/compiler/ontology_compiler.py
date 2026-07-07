"""
iios/ontology/compiler/ontology_compiler.py
=============================================
Compiles OntologyDocument objects into fully resolved CompiledOntology
artefacts, ready for fast runtime querying.

Compilation pipeline:
1. Resolve inheritance (merge parent properties into child)
2. Build children index (parent → set of child URIs)
3. Build alias index (alias / short name → canonical URI)
4. Detect circular inheritance
5. Validate cross-references (parent_uri must be known or external)
6. Return CompiledOntology
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..ontology_constants import MAX_INHERITANCE_DEPTH, OntologyStatus
from ..ontology_exceptions import (
    OntologyCircularInheritanceError,
    OntologyCompileError,
)
from ..runtime.runtime_object import (
    CompiledOntology,
    OntologyDocument,
    OntologyProperty,
    OntologyTypeDef,
)

__all__ = [
    "OntologyCompiler",
    "get_ontology_compiler",
    "reset_ontology_compiler",
]

_LOG = logging.getLogger("iios.ontology.compiler")


class OntologyCompiler:
    """
    Compiles a raw OntologyDocument into a CompiledOntology.

    The compiler is stateless — it does not maintain singletons.
    One compiler instance can compile multiple documents sequentially.
    To resolve cross-document inheritance the caller must supply
    *external_types* — a dict of URI → OntologyTypeDef from already-
    compiled ontologies that this document imports.
    """

    def compile(
        self,
        doc:            OntologyDocument,
        external_types: Optional[dict[str, OntologyTypeDef]] = None,
    ) -> CompiledOntology:
        """
        Compile *doc* and return a CompiledOntology.

        Args:
            doc:            The raw ontology document to compile.
            external_types: All type definitions visible from imported
                            documents (URI → TypeDef).  Needed for
                            cross-document inheritance resolution.
        """
        ext = external_types or {}
        warnings: list[str] = []

        _LOG.debug("Compiling ontology %r (%d types)", doc.name, len(doc.types))
        t0 = time.perf_counter()

        # Step 1 — collect own types keyed by URI
        own_types: dict[str, OntologyTypeDef] = {}
        for typedef in doc.types.values():
            own_types[typedef.uri] = typedef

        # Step 2 — build universe of all visible types (own + external)
        all_visible = {**ext, **own_types}

        # Step 3 — detect circular inheritance within own types
        self._check_cycles(own_types, all_visible)

        # Step 4 — resolve inherited properties for each own type
        property_index: dict[str, dict[str, OntologyProperty]] = {}
        for uri, typedef in own_types.items():
            try:
                merged = self._resolve_properties(typedef, all_visible, [])
            except OntologyCircularInheritanceError:
                raise
            except Exception as exc:
                warnings.append(f"Property resolution failed for {uri!r}: {exc}")
                merged = dict(typedef.properties)
            property_index[uri] = merged

        # Step 5 — build children index (within own types)
        children: dict[str, set[str]] = {uri: set() for uri in own_types}
        for uri, typedef in own_types.items():
            if typedef.parent_uri:
                parent = typedef.parent_uri
                if parent not in children:
                    children[parent] = set()
                children[parent].add(uri)

        # Step 6 — build alias index
        alias_index: dict[str, str] = {}
        for uri, typedef in own_types.items():
            # Short name (unqualified)
            alias_index[typedef.name] = uri
            for alias in typedef.aliases:
                if alias in alias_index and alias_index[alias] != uri:
                    warnings.append(
                        f"Alias {alias!r} collision: {alias_index[alias]!r} vs {uri!r}. Keeping first."
                    )
                else:
                    alias_index[alias] = uri

        elapsed = (time.perf_counter() - t0) * 1_000.0
        _LOG.debug(
            "Compiled %r in %.1fms: %d types, %d aliases, %d warnings",
            doc.name, elapsed, len(own_types), len(alias_index), len(warnings),
        )

        return CompiledOntology(
            document       = doc,
            compiled_at    = time.time(),
            status         = OntologyStatus.COMPILED,
            types          = own_types,
            relationships  = dict(doc.relationships),
            property_index = property_index,
            children       = children,
            alias_index    = alias_index,
            warnings       = warnings,
        )

    # ── Cycle detection ────────────────────────────────────────────────────────

    def _check_cycles(
        self,
        own_types:   dict[str, OntologyTypeDef],
        all_visible: dict[str, OntologyTypeDef],
    ) -> None:
        """DFS-based cycle detection in the inheritance graph."""
        GREY = 1  # currently visiting
        BLACK = 2  # fully visited
        colour: dict[str, int] = {}

        def dfs(uri: str, path: list[str]) -> None:
            if colour.get(uri) == BLACK:
                return
            if colour.get(uri) == GREY:
                raise OntologyCircularInheritanceError(path + [uri])
            colour[uri] = GREY
            typedef = all_visible.get(uri)
            if typedef and typedef.parent_uri:
                dfs(typedef.parent_uri, path + [uri])
            colour[uri] = BLACK

        for uri in own_types:
            dfs(uri, [])

    # ── Property resolution ────────────────────────────────────────────────────

    def _resolve_properties(
        self,
        typedef:     OntologyTypeDef,
        all_visible: dict[str, OntologyTypeDef],
        ancestors:   list[str],
    ) -> dict[str, OntologyProperty]:
        """
        Return merged dict of all properties for *typedef*, walking up
        the inheritance chain.  Own properties override inherited ones.
        """
        if len(ancestors) > MAX_INHERITANCE_DEPTH:
            raise OntologyCompileError(
                f"Inheritance depth exceeded {MAX_INHERITANCE_DEPTH} for {typedef.uri!r}"
            )

        if typedef.parent_uri is None:
            # Root — just own properties
            return dict(typedef.properties)

        parent = all_visible.get(typedef.parent_uri)
        if parent is None:
            # External parent (cross-document) — just own properties
            return dict(typedef.properties)

        parent_props = self._resolve_properties(
            parent, all_visible, ancestors + [typedef.uri]
        )
        # Own properties shadow parent properties
        merged = {**parent_props, **typedef.properties}
        return merged


# ── Module-level singleton ────────────────────────────────────────────────────

import threading as _threading

_lock     = _threading.Lock()
_compiler: Optional["OntologyCompiler"] = None


def get_ontology_compiler() -> OntologyCompiler:
    global _compiler
    if _compiler is None:
        with _lock:
            if _compiler is None:
                _compiler = OntologyCompiler()
    return _compiler


def reset_ontology_compiler() -> None:
    global _compiler
    with _lock:
        _compiler = None
