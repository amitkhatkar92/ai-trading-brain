"""
capability_gateway.py -- iios.ai.capability.gateway
=====================================================
:class:`CapabilityGateway` — single lifecycle-aware public entry point
for the A9 Enterprise Capability Platform.

A9 Enterprise Capability Platform — Phase 3, Module 9
"""
from __future__ import annotations

from typing import Any, Callable, Dict, FrozenSet, List, Optional

from ..connectors.connector_interface  import BaseConnector, ConnectorType
from ..container.capability_container  import CapabilityContainer
from ..core.capability_descriptor      import CapabilityDescriptor
from ..core.capability_types           import CapabilityCategory, CapabilityType
from ..engine.capability_request       import CapabilityContext, CapabilityRequest
from ..engine.capability_response      import CapabilityResponse
from ..events.capability_events        import (
    AuthorizationDeniedEvent, AuthorizationGrantedEvent,
    CapabilityDeregisteredEvent, CapabilityDisabledEvent,
    CapabilityEnabledEvent, CapabilityExecutedEvent,
    CapabilityFailedEvent, CapabilityRegisteredEvent,
    ConnectorRegisteredEvent, PolicyAddedEvent, PolicyRemovedEvent,
    QuotaExceededEvent, SkillRegisteredEvent,
)
from ..exceptions.capability_exceptions import (
    AICapabilityException,
    AICapabilityPermissionDeniedError,
    AICapabilityPolicyViolationError,
    AICapabilityQuotaExceededError,
)
from ..lifecycle                        import AILifecycleAwareMixin
from ..policy.capability_audit          import CapabilityAuditEventType, CapabilityAuditReport
from ..policy.capability_permission     import CapabilityPermission, CapabilityRole
from ..policy.capability_policy         import CapabilityPolicy
from ..skills.skill_interface           import BaseSkill, SkillCategory
from ..snapshot.capability_snapshot     import CapabilitySystemSnapshot

SYSTEM_ID = "iios:ai:capability:gateway"
VERSION   = "1.0.0"

_SRC = SYSTEM_ID


class CapabilityGateway(AILifecycleAwareMixin):
    """
    Single public entry point for the A9 Enterprise Capability Platform.

    Usage::

        gw = CapabilityGateway()
        gw.start()

        descriptor = CapabilityDescriptor.create("my_tool")
        gw.register_capability(descriptor)
        gw.register_handler(descriptor.descriptor_id, lambda p: p.get("x", 0) * 2)

        ctx     = CapabilityContext.create("agent_x")
        request = CapabilityRequest.create(descriptor.descriptor_id, ctx, x=21)
        response = gw.execute_capability(request)

        gw.stop()
    """

    SYSTEM_ID  : str = SYSTEM_ID
    VERSION    : str = VERSION
    MODULE_ID  : str = "A9"
    MODULE_NAME: str = "Capability Management"
    API_VERSION: str = "v1"
    DESCRIPTION: str = "AI capability registry, skill management and quota enforcement"
    STATUS     : str = "stable"

    def __init__(self) -> None:
        super().__init__()
        self._container: Optional[CapabilityContainer] = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._container = CapabilityContainer()

    def _on_stop(self) -> None:
        self._container = None

    @property
    def _c(self) -> CapabilityContainer:
        if self._container is None:
            raise AICapabilityException(
                "[AI-1400] CapabilityGateway is not running — call start() first"
            )
        return self._container

    # ── TASK 1: Capability registry ───────────────────────────────────────────

    def register_capability(self, descriptor: CapabilityDescriptor) -> None:
        """Register a capability descriptor and emit :class:`CapabilityRegisteredEvent`."""
        self._c.registry.register(descriptor)
        self._c.event_bus.publish(
            CapabilityRegisteredEvent.create(_SRC, descriptor.descriptor_id, descriptor.name)
        )

    def deregister_capability(self, capability_id: str) -> None:
        self._c.registry.deregister(capability_id)
        self._c.event_bus.publish(
            CapabilityDeregisteredEvent.create(_SRC, capability_id)
        )

    def find_capability(self, capability_id: str) -> Optional[CapabilityDescriptor]:
        return self._c.registry.get_optional(capability_id)

    def get_capability(self, capability_id: str) -> CapabilityDescriptor:
        return self._c.registry.get(capability_id)

    def list_capabilities(
        self,
        capability_type: Optional[CapabilityType]     = None,
        category:        Optional[CapabilityCategory] = None,
        tags:            Optional[FrozenSet[str]]      = None,
        active_only:     bool                          = False,
    ) -> List[CapabilityDescriptor]:
        return self._c.registry.discover(capability_type, category, tags, active_only)

    def enable_capability(self, capability_id: str) -> None:
        self._c.registry.enable(capability_id)
        self._c.event_bus.publish(CapabilityEnabledEvent.create(_SRC, capability_id))

    def disable_capability(self, capability_id: str) -> None:
        self._c.registry.disable(capability_id)
        self._c.event_bus.publish(CapabilityDisabledEvent.create(_SRC, capability_id))

    # ── TASK 3: Execution ─────────────────────────────────────────────────────

    def register_handler(
        self,
        capability_id: str,
        handler:       Callable[[Dict[str, Any]], Any],
    ) -> None:
        """Bind an execution handler to a registered capability."""
        self._c.executor.register_handler(capability_id, handler)

    def execute_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        """
        Execute a capability request.

        Authorization pipeline (in order):
          1. Policy evaluation (raises :class:`AICapabilityPolicyViolationError`)
          2. Permission authorization (raises :class:`AICapabilityPermissionDeniedError`)
          3. Quota check (raises :class:`AICapabilityQuotaExceededError`)
        """
        c             = self._c
        descriptor    = c.registry.get(request.capability_id)
        principal_id  = request.context.principal_id
        capability_id = request.capability_id

        # 1. Policy check
        try:
            c.policy_engine.evaluate(principal_id, capability_id)
        except AICapabilityPolicyViolationError as exc:
            c.event_bus.publish(
                AuthorizationDeniedEvent.create(_SRC, principal_id, capability_id, str(exc))
            )
            c.audit.record(
                CapabilityAuditEventType.AUTH_DENIED, principal_id, capability_id, "denied"
            )
            raise

        # 2. Permission check (only if descriptor requires auth)
        if descriptor.requires_auth:
            try:
                c.authorization.authorize(principal_id, capability_id)
            except AICapabilityPermissionDeniedError as exc:
                c.event_bus.publish(
                    AuthorizationDeniedEvent.create(_SRC, principal_id, capability_id, str(exc))
                )
                c.audit.record(
                    CapabilityAuditEventType.AUTH_DENIED, principal_id, capability_id, "denied"
                )
                raise

        # 3. Quota check
        try:
            c.quota.record_execution(principal_id, capability_id)
        except AICapabilityQuotaExceededError as exc:
            c.event_bus.publish(
                QuotaExceededEvent.create(_SRC, principal_id, capability_id, "hourly")
            )
            c.audit.record(
                CapabilityAuditEventType.QUOTA_EXCEEDED, principal_id, capability_id, "quota_exceeded"
            )
            raise

        # 4. Execute
        import time
        started = time.time()
        response = c.executor.execute(request, descriptor)
        duration = (time.time() - started) * 1000

        # 5. Audit + events
        if response.is_successful():
            c.audit.record(
                CapabilityAuditEventType.EXECUTE_SUCCESS,
                principal_id, capability_id, "success", duration
            )
            c.event_bus.publish(
                CapabilityExecutedEvent.create(_SRC, capability_id, principal_id, duration)
            )
        else:
            c.audit.record(
                CapabilityAuditEventType.EXECUTE_FAILURE,
                principal_id, capability_id, "failure", duration,
                notes=response.result.error or ""
            )
            c.event_bus.publish(
                CapabilityFailedEvent.create(
                    _SRC, capability_id, principal_id,
                    response.result.error or "unknown"
                )
            )

        return response

    # ── TASK 3: Authorize only (no execution) ────────────────────────────────

    def authorize_capability(self, principal_id: str, capability_id: str) -> bool:
        """
        Return True when the principal is authorized.

        Raises :class:`AICapabilityPermissionDeniedError` if denied.
        """
        self._c.authorization.authorize(principal_id, capability_id)
        self._c.event_bus.publish(
            AuthorizationGrantedEvent.create(_SRC, principal_id, capability_id)
        )
        return True

    def is_authorized(self, principal_id: str, capability_id: str) -> bool:
        return self._c.authorization.is_authorized(principal_id, capability_id)

    # ── TASK 6: Permissions & roles ───────────────────────────────────────────

    def grant_permission(self, permission: CapabilityPermission) -> None:
        self._c.authorization.grant(permission)

    def revoke_permission(self, principal_id: str, capability_id: str) -> None:
        self._c.authorization.revoke(principal_id, capability_id)

    def list_permissions(self, principal_id: str) -> List[CapabilityPermission]:
        return self._c.authorization.list_permissions(principal_id)

    def create_role(self, role: CapabilityRole) -> None:
        self._c.authorization.create_role(role)

    def assign_role(self, principal_id: str, role_name: str) -> None:
        self._c.authorization.assign_role(principal_id, role_name)

    def revoke_role(self, principal_id: str, role_name: str) -> None:
        self._c.authorization.revoke_role(principal_id, role_name)

    def list_roles(self) -> List[CapabilityRole]:
        return self._c.authorization.list_roles()

    # ── TASK 6: Policies ──────────────────────────────────────────────────────

    def add_policy(self, policy: CapabilityPolicy) -> None:
        self._c.policy_engine.add_policy(policy)
        self._c.event_bus.publish(PolicyAddedEvent.create(_SRC, policy.policy_id, policy.name))

    def remove_policy(self, policy_id: str) -> None:
        self._c.policy_engine.remove_policy(policy_id)
        self._c.event_bus.publish(PolicyRemovedEvent.create(_SRC, policy_id))

    def evaluate_policy(self, principal_id: str, capability_id: str) -> bool:
        return self._c.policy_engine.evaluate(principal_id, capability_id)

    def list_policies(self) -> List[CapabilityPolicy]:
        return self._c.policy_engine.list_policies()

    # ── TASK 6: Quota ─────────────────────────────────────────────────────────

    def set_quota(
        self,
        principal_id:  str,
        capability_id: str,
        max_per_hour:  int = 0,
        max_per_day:   int = 0,
    ) -> None:
        self._c.quota.set_quota(principal_id, capability_id, max_per_hour, max_per_day)

    def check_quota(self, principal_id: str, capability_id: str) -> bool:
        return self._c.quota.check_quota(principal_id, capability_id)

    def get_usage(self, principal_id: str, capability_id: str) -> Dict[str, int]:
        return self._c.quota.get_usage(principal_id, capability_id)

    # ── TASK 4: Connectors ────────────────────────────────────────────────────

    def register_connector(self, connector: BaseConnector) -> None:
        self._c.connectors.register(connector)
        self._c.event_bus.publish(
            ConnectorRegisteredEvent.create(
                _SRC, connector.connector_id, connector.descriptor.name
            )
        )

    def get_connector(self, connector_id: str) -> BaseConnector:
        return self._c.connectors.get(connector_id)

    def list_connectors(
        self,
        connector_type: Optional[ConnectorType] = None,
    ) -> List[BaseConnector]:
        return self._c.connectors.list_connectors(connector_type)

    # ── TASK 5: Skills ────────────────────────────────────────────────────────

    def register_skill(self, skill: BaseSkill) -> None:
        self._c.skills.register(skill)
        self._c.event_bus.publish(
            SkillRegisteredEvent.create(
                _SRC, skill.skill_id, skill.skill_descriptor.name
            )
        )

    def get_skill(self, skill_id: str) -> BaseSkill:
        return self._c.skills.get(skill_id)

    def list_skills(
        self,
        category: Optional[SkillCategory] = None,
    ) -> List[BaseSkill]:
        return self._c.skills.list_skills(category)

    # ── Audit ─────────────────────────────────────────────────────────────────

    def query_audit(
        self,
        principal_id:  Optional[str] = None,
        capability_id: Optional[str] = None,
        since:         Optional[float] = None,
        limit:         int = 500,
    ) -> list:
        return self._c.audit.query(principal_id, capability_id, since=since, limit=limit)

    def audit_report(self, principal_id: str) -> CapabilityAuditReport:
        return self._c.audit.generate_report(principal_id)

    # ── Introspection ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        c = self._c
        all_caps    = c.registry.list_all()
        active_caps = c.registry.list_active()
        return {
            "is_running":          self.is_ai_running,
            "total_capabilities":  len(all_caps),
            "active_capabilities": len(active_caps),
            "total_connectors":    c.connectors.count(),
            "total_skills":        c.skills.count(),
            "total_handlers":      c.executor.handler_count(),
            "total_executions":    c.executor.total_executions(),
            "failed_executions":   c.executor.failed_executions(),
            "total_audit_records": c.audit.total_count(),
            "policy_count":        c.policy_engine.policy_count(),
            "quota_count":         c.quota.quota_count(),
            "system_id":           SYSTEM_ID,
            "version":             VERSION,
        }

    def status(self) -> Dict[str, Any]:
        return self.health()

    def snapshot(self) -> CapabilitySystemSnapshot:
        c        = self._c
        all_caps = c.registry.list_all()
        disabled = [d for d in all_caps if not d.is_executable()]
        return CapabilitySystemSnapshot.build(
            is_running            = self.is_ai_running,
            total_capabilities    = len(all_caps),
            active_capabilities   = len(c.registry.list_active()),
            disabled_capabilities = len(disabled),
            total_connectors      = c.connectors.count(),
            total_skills          = c.skills.count(),
            total_handlers        = c.executor.handler_count(),
            total_audit_records   = c.audit.total_count(),
            total_executions      = c.executor.total_executions(),
            failed_executions     = c.executor.failed_executions(),
            total_roles           = len(c.authorization.list_roles()),
            total_permissions     = c.authorization.permission_count(),
            policy_count          = c.policy_engine.policy_count(),
            quota_count           = c.quota.quota_count(),
        )
