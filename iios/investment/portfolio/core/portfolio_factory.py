"""iios/investment/portfolio/core/portfolio_factory.py

Factory for creating BasePortfolio instances from the class registry.
The factory injects the PortfolioRuntimeContext and wires up lifecycle
infrastructure before returning the portfolio to the caller.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type, TYPE_CHECKING

from iios.investment.portfolio.core.framework_context import PortfolioRuntimeContext
from iios.investment.portfolio.core.portfolio_metadata import PortfolioMetadata, build_metadata
from iios.investment.portfolio.core.portfolio_registry import (
    PortfolioClassNotFoundError,
    PortfolioClassRegistry,
)
from iios.investment.portfolio.core.portfolio_types import (
    PortfolioCapability,
    PortfolioDomain,
)

if TYPE_CHECKING:
    from iios.investment.portfolio.core.base_portfolio import BasePortfolio

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FactoryResult:
    """Result of one portfolio creation attempt."""

    result_id:   str              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:str              = ""
    class_name:  str              = ""
    success:     bool             = False
    portfolio:   Optional["BasePortfolio"] = field(default=None, compare=False, hash=False)
    error:       str              = ""
    duration_ms: float            = 0.0
    created_at:  float            = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":    self.result_id,
            "portfolio_id": self.portfolio_id,
            "class_name":   self.class_name,
            "success":      self.success,
            "error":        self.error,
            "duration_ms":  self.duration_ms,
        }


class PortfolioFactory:
    """
    Creates BasePortfolio instances from the class registry.

    Responsibilities:
    - Look up the class from PortfolioClassRegistry
    - Build PortfolioMetadata for the instance
    - Inject PortfolioRuntimeContext
    - Instantiate and return the portfolio

    Does NOT start lifecycle — that is the PortfolioFramework's job.
    """

    def __init__(
        self,
        registry: PortfolioClassRegistry,
        context:  PortfolioRuntimeContext,
    ) -> None:
        self._registry = registry
        self._context  = context

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    def create(
        self,
        class_name:   str,
        *,
        portfolio_id: str              = "",
        name:         str              = "",
        domain:       Optional[PortfolioDomain] = None,
        metadata:     Optional[PortfolioMetadata] = None,
        kwargs:       Optional[Dict[str, Any]] = None,
    ) -> FactoryResult:
        """
        Create a portfolio instance of the registered *class_name*.

        Args:
            class_name:   Registered name of the portfolio class.
            portfolio_id: Explicit ID; generated if omitted.
            name:         Human-readable name; defaults to class_name.
            domain:       Domain override; uses registry domain if omitted.
            metadata:     Provide a fully-built PortfolioMetadata to bypass
                          auto-construction.
            kwargs:       Extra keyword arguments forwarded to the constructor.
        """
        t0 = time.time()
        pid = portfolio_id or str(uuid.uuid4())

        try:
            cls   = self._registry.get_class(class_name)
            entry = self._registry.get_entry(class_name)
        except PortfolioClassNotFoundError as exc:
            return FactoryResult(
                portfolio_id = pid,
                class_name   = class_name,
                success      = False,
                error        = str(exc),
                duration_ms  = (time.time() - t0) * 1_000,
            )

        # Build metadata if not provided
        if metadata is None:
            resolved_domain = domain or entry.domain
            metadata = build_metadata(
                portfolio_id = pid,
                name         = name or class_name,
                domain       = resolved_domain,
                capabilities = entry.capabilities,
                tags         = entry.tags,
                class_module = entry.module_path.rsplit(".", 1)[0] if "." in entry.module_path else entry.module_path,
                class_name   = class_name,
                version      = entry.version,
                description  = entry.description,
            )

        try:
            portfolio = cls(
                metadata = metadata,
                context  = self._context,
                **(kwargs or {}),
            )
            log.info(
                "Portfolio created: %s (class=%s, id=%s)",
                portfolio.name, class_name, pid,
            )
            return FactoryResult(
                portfolio_id = pid,
                class_name   = class_name,
                success      = True,
                portfolio    = portfolio,
                duration_ms  = (time.time() - t0) * 1_000,
            )
        except Exception as exc:
            log.error(
                "Failed to create portfolio %s (class=%s): %s",
                pid, class_name, exc,
            )
            return FactoryResult(
                portfolio_id = pid,
                class_name   = class_name,
                success      = False,
                error        = str(exc),
                duration_ms  = (time.time() - t0) * 1_000,
            )

    def create_or_raise(
        self,
        class_name:   str,
        **kwargs: Any,
    ) -> "BasePortfolio":
        """Like create() but raises RuntimeError on failure."""
        result = self.create(class_name, **kwargs)
        if not result.success:
            raise RuntimeError(
                f"Failed to create portfolio (class={class_name!r}): {result.error}"
            )
        return result.portfolio  # type: ignore[return-value]
