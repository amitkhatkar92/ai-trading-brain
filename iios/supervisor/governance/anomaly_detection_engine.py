"""
anomaly_detection_engine.py — iios.supervisor.governance
---------------------------------------------------------
Enterprise anomaly detection engine.

Inspects all subsystem snapshots for values that deviate from expected
operating ranges and returns an AnomalyReport.  Stateless.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from typing import List

from .constants import (
    ANOMALY_MISSING_SNAPSHOT_SCORE,
    ANOMALY_RISK_HIGH,
    ANOMALY_RISK_MEDIUM,
    DOMAIN_SNAPSHOT_KEY,
    AnomalySeverity,
    SubsystemStatus,
    SupervisionDomain,
)
from .autonomous_governance_context import AutonomousGovernanceContext
from .autonomous_governance_response import (
    AnomalyReport,
    GovernanceAnomaly,
    PlatformHealthReport,
    SubsystemHealth,
)


class AnomalyDetectionEngine:
    """
    Stateless anomaly detection engine.

    Detects anomalies at two levels:
    1. Subsystem-level — derived from PlatformHealthReport status.
    2. Snapshot-level  — domain-specific field checks (risk VaR, market stress,
       error rates, etc.).
    """

    def detect(
        self,
        context:         AutonomousGovernanceContext,
        platform_health: PlatformHealthReport,
    ) -> AnomalyReport:
        """
        Detect anomalies across all supervised subsystems.

        Parameters
        ----------
        context : AutonomousGovernanceContext
        platform_health : PlatformHealthReport

        Returns
        -------
        AnomalyReport
        """
        anomalies: List[GovernanceAnomaly] = []

        # 1. Health-based anomalies.
        for health in platform_health.subsystem_health:
            a = self._health_anomaly(health)
            if a:
                anomalies.append(a)

        # 2. Domain-specific field checks.
        anomalies.extend(self._check_risk_snapshot(context))
        anomalies.extend(self._check_market_snapshot(context))
        anomalies.extend(self._check_execution_snapshot(context))
        anomalies.extend(self._check_infrastructure_snapshot(context))

        return AnomalyReport.create(tuple(anomalies))

    # ------------------------------------------------------------------
    # Health-based anomalies
    # ------------------------------------------------------------------

    def _health_anomaly(self, health: SubsystemHealth):
        if health.status == SubsystemStatus.CRITICAL:
            return GovernanceAnomaly.create(
                subsystem_id   = health.subsystem_id,
                field_path     = "health_score",
                observed_value = health.health_score,
                severity       = AnomalySeverity.CRITICAL,
                expected_range = f">= {0.30}",
                description    = f"Subsystem {health.subsystem_id} is CRITICAL (score={health.health_score:.2f})",
            )
        if health.status == SubsystemStatus.IMPAIRED:
            return GovernanceAnomaly.create(
                subsystem_id   = health.subsystem_id,
                field_path     = "health_score",
                observed_value = health.health_score,
                severity       = AnomalySeverity.HIGH,
                expected_range = f">= {0.50}",
                description    = f"Subsystem {health.subsystem_id} is IMPAIRED (score={health.health_score:.2f})",
            )
        if health.status == SubsystemStatus.DEGRADED:
            return GovernanceAnomaly.create(
                subsystem_id   = health.subsystem_id,
                field_path     = "health_score",
                observed_value = health.health_score,
                severity       = AnomalySeverity.MEDIUM,
                expected_range = f">= {0.70}",
                description    = f"Subsystem {health.subsystem_id} is DEGRADED (score={health.health_score:.2f})",
            )
        if health.status == SubsystemStatus.UNKNOWN and "snapshot_missing" in health.issues:
            return GovernanceAnomaly.create(
                subsystem_id   = health.subsystem_id,
                field_path     = "snapshot",
                observed_value = None,
                severity       = AnomalySeverity.LOW,
                expected_range = "non-empty snapshot",
                description    = f"No snapshot available for {health.subsystem_id}",
            )
        return None

    # ------------------------------------------------------------------
    # Snapshot field checks
    # ------------------------------------------------------------------

    def _check_risk_snapshot(self, context: AutonomousGovernanceContext) -> List[GovernanceAnomaly]:
        anomalies: List[GovernanceAnomaly] = []
        snap = context.risk_snapshot
        if not snap:
            return anomalies

        # VaR threshold check.
        var = snap.get("var", snap.get("value_at_risk"))
        if isinstance(var, (int, float)) and var > ANOMALY_RISK_HIGH:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.RISK_INTELLIGENCE.value,
                field_path     = "risk.var",
                observed_value = var,
                severity       = AnomalySeverity.HIGH,
                expected_range = f"<= {ANOMALY_RISK_HIGH}",
                description    = f"Risk VaR {var:.4f} exceeds high threshold {ANOMALY_RISK_HIGH}",
            ))
        elif isinstance(var, (int, float)) and var > ANOMALY_RISK_MEDIUM:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.RISK_INTELLIGENCE.value,
                field_path     = "risk.var",
                observed_value = var,
                severity       = AnomalySeverity.MEDIUM,
                expected_range = f"<= {ANOMALY_RISK_MEDIUM}",
                description    = f"Risk VaR {var:.4f} elevated above medium threshold",
            ))

        # Position limit breach.
        breach = snap.get("position_limit_breach", snap.get("limit_breach"))
        if breach:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.RISK_INTELLIGENCE.value,
                field_path     = "risk.position_limit_breach",
                observed_value = breach,
                severity       = AnomalySeverity.HIGH,
                expected_range = "False",
                description    = "Position limit breach detected in risk snapshot",
            ))
        return anomalies

    def _check_market_snapshot(self, context: AutonomousGovernanceContext) -> List[GovernanceAnomaly]:
        anomalies: List[GovernanceAnomaly] = []
        snap = context.market_snapshot
        if not snap:
            return anomalies

        market_status = snap.get("status", snap.get("market_status", ""))
        if isinstance(market_status, str) and market_status in ("halt", "halted", "suspended"):
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.MARKET_INTELLIGENCE.value,
                field_path     = "market.status",
                observed_value = market_status,
                severity       = AnomalySeverity.CRITICAL,
                expected_range = "active",
                description    = f"Market status is {market_status!r}",
            ))

        stress = snap.get("stress_score", snap.get("volatility"))
        if isinstance(stress, (int, float)) and stress > 0.8:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.MARKET_INTELLIGENCE.value,
                field_path     = "market.stress",
                observed_value = stress,
                severity       = AnomalySeverity.HIGH,
                expected_range = "<= 0.80",
                description    = f"Market stress {stress:.2f} is elevated",
            ))
        return anomalies

    def _check_execution_snapshot(self, context: AutonomousGovernanceContext) -> List[GovernanceAnomaly]:
        anomalies: List[GovernanceAnomaly] = []
        snap = context.execution_snapshot
        if not snap:
            return anomalies

        fill_rate = snap.get("fill_rate", snap.get("execution_rate"))
        if isinstance(fill_rate, (int, float)) and fill_rate < 0.50:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.EXECUTION_INTELLIGENCE.value,
                field_path     = "execution.fill_rate",
                observed_value = fill_rate,
                severity       = AnomalySeverity.HIGH,
                expected_range = ">= 0.50",
                description    = f"Execution fill rate {fill_rate:.2f} is below threshold",
            ))

        error_rate = snap.get("error_rate", snap.get("failure_rate"))
        if isinstance(error_rate, (int, float)) and error_rate > 0.10:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.EXECUTION_INTELLIGENCE.value,
                field_path     = "execution.error_rate",
                observed_value = error_rate,
                severity       = AnomalySeverity.MEDIUM,
                expected_range = "<= 0.10",
                description    = f"Execution error rate {error_rate:.2f} is elevated",
            ))
        return anomalies

    def _check_infrastructure_snapshot(self, context: AutonomousGovernanceContext) -> List[GovernanceAnomaly]:
        anomalies: List[GovernanceAnomaly] = []
        snap = context.infrastructure_metrics
        if not snap:
            return anomalies

        cpu = snap.get("cpu_usage", snap.get("cpu"))
        if isinstance(cpu, (int, float)) and cpu > 0.90:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.PLATFORM_INFRASTRUCTURE.value,
                field_path     = "infrastructure.cpu_usage",
                observed_value = cpu,
                severity       = AnomalySeverity.HIGH,
                expected_range = "<= 0.90",
                description    = f"CPU usage {cpu:.2%} is critically high",
            ))

        mem = snap.get("memory_usage", snap.get("memory"))
        if isinstance(mem, (int, float)) and mem > 0.90:
            anomalies.append(GovernanceAnomaly.create(
                subsystem_id   = SupervisionDomain.PLATFORM_INFRASTRUCTURE.value,
                field_path     = "infrastructure.memory_usage",
                observed_value = mem,
                severity       = AnomalySeverity.HIGH,
                expected_range = "<= 0.90",
                description    = f"Memory usage {mem:.2%} is critically high",
            ))
        return anomalies
