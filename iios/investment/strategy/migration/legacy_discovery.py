"""iios/investment/strategy/migration/legacy_discovery.py
Discovers legacy strategies from all known sources in the AI Trading Brain.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.migration.legacy_metadata import (
    EntryCondition,
    LegacyHealthStatus,
    LegacyStrategyMetadata,
    LegacyStrategySource,
    LegacyStrategyType,
)
from iios.investment.strategy.migration.legacy_registry import LegacyStrategyRegistry
from iios.investment.strategy.migration.legacy_catalog import LegacyCatalog


# ── Default search paths ───────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
_DISCOVERED_EDGES_PATH  = os.path.join(_PROJECT_ROOT, "data", "discovered_edges.json")
_EVOLVED_STRATEGIES_PATH = os.path.join(_PROJECT_ROOT, "data", "evolved_strategies.json")


@dataclass
class DiscoveryConfig:
    """Configuration for the legacy discovery engine."""
    scan_discovered_edges:  bool = True
    scan_evolved_strategies: bool = True
    include_unapproved:     bool = True
    include_decaying:       bool = True
    max_strategies:         int  = 5000
    discovered_edges_path:  str  = _DISCOVERED_EDGES_PATH
    evolved_strategies_path: str = _EVOLVED_STRATEGIES_PATH


@dataclass
class DiscoveryResult:
    """Result of a discovery run."""
    total_discovered:   int = 0
    code_based_count:   int = 0
    json_based_count:   int = 0
    evolved_count:      int = 0
    skipped_count:      int = 0
    errors:             List[str] = field(default_factory=list)
    strategies:         List[LegacyStrategyMetadata] = field(default_factory=list)
    discovered_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms:        float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_discovered": self.total_discovered,
            "code_based_count": self.code_based_count,
            "json_based_count": self.json_based_count,
            "evolved_count":    self.evolved_count,
            "skipped_count":    self.skipped_count,
            "error_count":      len(self.errors),
            "discovered_at":    self.discovered_at.isoformat(),
            "duration_ms":      round(self.duration_ms, 2),
        }


class LegacyDiscoveryEngine:
    """
    Discovers all legacy strategies from known sources.

    Sources scanned:
    1. LegacyStrategyRegistry (hardcoded code-based strategies)
    2. data/discovered_edges.json (ML-discovered edge strategies)
    3. data/evolved_strategies.json (GA-evolved strategy variants)
    """

    def __init__(
        self,
        config: Optional[DiscoveryConfig] = None,
        registry: Optional[LegacyStrategyRegistry] = None,
    ) -> None:
        self._config   = config or DiscoveryConfig()
        self._registry = registry or LegacyStrategyRegistry()
        self._catalog  = LegacyCatalog()
        self._lock     = threading.RLock()
        self._last_result: Optional[DiscoveryResult] = None

    def discover(self) -> DiscoveryResult:
        """Run a full discovery scan. Thread-safe."""
        import time
        start = time.monotonic()
        result = DiscoveryResult()

        # 1. Code-based strategies from registry
        code_strategies = self._registry.all()
        result.code_based_count = len(code_strategies)
        result.strategies.extend(code_strategies)

        # 2. Discovered edges from JSON
        if self._config.scan_discovered_edges:
            json_strategies, errors = self._scan_discovered_edges()
            result.json_based_count = len(json_strategies)
            result.strategies.extend(json_strategies)
            result.errors.extend(errors)

        # 3. Evolved strategies from JSON
        if self._config.scan_evolved_strategies:
            evolved, errors = self._scan_evolved_strategies()
            result.evolved_count = len(evolved)
            result.strategies.extend(evolved)
            result.errors.extend(errors)

        # Deduplicate by name
        seen: set = set()
        unique: List[LegacyStrategyMetadata] = []
        for s in result.strategies:
            if s.strategy_name not in seen:
                seen.add(s.strategy_name)
                unique.append(s)
            else:
                result.skipped_count += 1
        result.strategies = unique

        # Cap if configured
        if len(result.strategies) > self._config.max_strategies:
            result.skipped_count += len(result.strategies) - self._config.max_strategies
            result.strategies = result.strategies[:self._config.max_strategies]

        result.total_discovered = len(result.strategies)
        result.duration_ms = (time.monotonic() - start) * 1000

        # Populate catalog
        self._catalog.ingest(result.strategies)

        with self._lock:
            self._last_result = result

        return result

    def get_catalog(self) -> LegacyCatalog:
        return self._catalog

    def last_result(self) -> Optional[DiscoveryResult]:
        with self._lock:
            return self._last_result

    # ── private scanners ──────────────────────────────────────────────────────

    def _scan_discovered_edges(self) -> Tuple[List[LegacyStrategyMetadata], List[str]]:
        """Scan data/discovered_edges.json."""
        strategies: List[LegacyStrategyMetadata] = []
        errors: List[str] = []

        if not os.path.exists(self._config.discovered_edges_path):
            return strategies, errors

        try:
            with open(self._config.discovered_edges_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except Exception as exc:
            errors.append(f"Failed to read discovered_edges.json: {exc}")
            return strategies, errors

        for name, entry in data.items():
            try:
                meta = self._parse_edge_entry(name, entry)
                if meta is None:
                    continue
                if not self._config.include_unapproved and not meta.is_approved:
                    continue
                if not self._config.include_decaying and meta.health_status == LegacyHealthStatus.DECAYING:
                    continue
                strategies.append(meta)
            except Exception as exc:
                errors.append(f"Failed to parse {name}: {exc}")

        return strategies, errors

    def _parse_edge_entry(self, name: str, entry: Dict[str, Any]) -> Optional[LegacyStrategyMetadata]:
        """Parse a single entry from discovered_edges.json."""
        params = entry.get("strategy_params", entry)

        # Parse entry conditions
        conditions: List[EntryCondition] = []
        for cond in entry.get("entry_conditions", []):
            try:
                conditions.append(EntryCondition(
                    feature=cond["feature"],
                    operator=cond["operator"],
                    threshold=float(cond["threshold"]),
                ))
            except (KeyError, ValueError):
                pass

        # Health status
        status_str = entry.get("status", "").upper()
        health = LegacyHealthStatus.DECAYING if status_str == "DECAYING" else \
                 LegacyHealthStatus.ACTIVE   if status_str == "ACTIVE"   else \
                 LegacyHealthStatus.ARCHIVED if status_str == "ARCHIVED" else \
                 LegacyHealthStatus.UNKNOWN

        # Parse timestamps
        disc_at: Optional[datetime] = None
        last_tested: Optional[datetime] = None
        try:
            raw_created = params.get("created_at") or entry.get("created_at")
            if raw_created:
                disc_at = datetime.fromisoformat(raw_created.rstrip("Z"))
        except Exception:
            pass
        try:
            raw_tested = entry.get("last_tested")
            if raw_tested:
                last_tested = datetime.fromisoformat(raw_tested.rstrip("Z"))
        except Exception:
            pass

        return LegacyStrategyMetadata(
            strategy_id=f"legacy_{name}",
            strategy_name=name,
            source=LegacyStrategySource.DISCOVERED_EDGES,
            strategy_type=(
                LegacyStrategyType.JSON_BASED if conditions
                else LegacyStrategyType.PATTERN_ONLY
            ),
            min_rr=float(params.get("min_rr", 2.0)),
            max_loss_pct=float(params.get("max_loss_pct", 0.02)),
            stop_loss_pct=float(params.get("stop_loss_pct", params.get("max_loss_pct", 0.02))),
            target_multiplier=float(params.get("target_multiplier", 2.0)),
            base_strategy=str(params.get("base_strategy", "")),
            category=str(params.get("category", entry.get("category", "unknown"))),
            direction=str(params.get("direction", entry.get("direction", "BUY"))),
            precision=_safe_float(entry.get("precision")),
            support=_safe_int(entry.get("support")),
            sharpe_ratio=_safe_float(entry.get("sharpe_ratio")),
            oos_win_rate=_safe_float(entry.get("oos_win_rate")),
            avg_return_r=_safe_float(entry.get("avg_return_r")),
            max_drawdown=_safe_float(entry.get("max_drawdown")),
            composite_score=_safe_float(entry.get("composite_score")),
            expectancy_r=_safe_float(entry.get("expectancy_r")),
            entry_conditions=conditions,
            health_status=health,
            is_approved=bool(params.get("approved", entry.get("is_approved", False))),
            live_trades=int(entry.get("live_trades", 0)),
            live_wins=int(entry.get("live_wins", 0)),
            description=str(params.get("description", entry.get("description", ""))),
            pattern_id=str(params.get("pattern_id", entry.get("pattern_id", ""))),
            discovered_at=disc_at,
            last_tested=last_tested,
            source_path=self._config.discovered_edges_path,
            raw_definition=entry,
        )

    def _scan_evolved_strategies(self) -> Tuple[List[LegacyStrategyMetadata], List[str]]:
        """Scan data/evolved_strategies.json."""
        strategies: List[LegacyStrategyMetadata] = []
        errors: List[str] = []

        if not os.path.exists(self._config.evolved_strategies_path):
            return strategies, errors

        try:
            with open(self._config.evolved_strategies_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except Exception as exc:
            errors.append(f"Failed to read evolved_strategies.json: {exc}")
            return strategies, errors

        for name, params in data.items():
            try:
                meta = LegacyStrategyMetadata(
                    strategy_id=f"legacy_{name}",
                    strategy_name=name,
                    source=LegacyStrategySource.EVOLVED_STRATEGIES,
                    strategy_type=LegacyStrategyType.HYBRID,
                    min_rr=float(params.get("min_rr", 2.0)),
                    max_loss_pct=float(params.get("max_loss_pct", 0.02)),
                    base_strategy=str(params.get("base_strategy", "")),
                    category="evolved",
                    is_approved=bool(params.get("approved", False)),
                    health_status=LegacyHealthStatus.ACTIVE,
                    tags=["evolved", params.get("base_strategy", "")],
                    source_path=self._config.evolved_strategies_path,
                    raw_definition=params,
                )
                if not self._config.include_unapproved and not meta.is_approved:
                    continue
                strategies.append(meta)
            except Exception as exc:
                errors.append(f"Failed to parse evolved strategy {name}: {exc}")

        return strategies, errors


# ── helpers ────────────────────────────────────────────────────────────────────

def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None
