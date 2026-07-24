# Compliance Guide

**Module:** C15 M3 — Integration Governance Policy Framework

---

## Compliance Overview

The IGPF provides `COMPLIANCE` and `AUDIT` policy types to enforce regulatory
and enterprise compliance requirements on every integration.

Compliance policies operate on the `compliance_config` field of the evaluation
context.  Every evaluation generates an immutable `IntegrationAuditEntry`
regardless of the governance decision.

---

## Compliance Policy Types

| Policy Type | Purpose |
|-------------|---------|
| `COMPLIANCE` | Regulatory compliance (GDPR, PCI-DSS, SOC 2) |
| `AUDIT` | Audit trail and logging requirements |
| `ENTERPRISE_INTEGRATION` | General enterprise governance |

---

## Audit Trail

Every call to `engine.evaluate()` automatically creates an `IntegrationAuditEntry`:

```python
# Access the audit trail
audit_entries = engine.audit.recent(n=50)
for entry in audit_entries:
    print(entry.audit_id, entry.final_action, entry.evaluation_time_ms)

# Generate a full audit report
report = engine.audit.report()
print(report.total_evaluations)
print(report.total_approved)
print(report.total_rejected)
print(report.to_dict())
```

---

## Example: Enforce Compliance Flag

```python
from iios.integration.policies import (
    IntegrationPolicyFactory, PolicyType, PolicyDomain,
    PolicyAction, ConditionOperator, PolicyPriority,
)

factory = IntegrationPolicyFactory()

# Block integrations that have not passed compliance review
condition = factory.create_condition(
    "Compliance Not Verified",
    field_path     = "compliance_config.verified",
    operator       = ConditionOperator.NOT_EQUALS,
    expected_value = True,
)
rule = factory.create_rule(
    "Block Unverified Integrations",
    PolicyAction.REQUIRE_MANUAL_REVIEW,
    [condition],
)
policy = factory.create_policy(
    "Compliance Verification Required",
    PolicyType.COMPLIANCE,
    domain   = PolicyDomain.COMPLIANCE,
    priority = PolicyPriority.HIGH,
    rules    = [rule],
)
```

---

## Compliance Context Fields

| Field | Description |
|-------|-------------|
| `compliance_config.verified` | Boolean: compliance review passed |
| `compliance_config.gdpr_applicable` | GDPR applicability flag |
| `compliance_config.pci_dss_scope` | PCI-DSS scope flag |
| `compliance_config.data_classification` | Data classification level |
| `compliance_config.retention_policy` | Data retention policy name |

---

## Statistics for Compliance Reporting

```python
stats = engine.stats.report()
print(f"Total evaluations:  {stats.policies_evaluated}")
print(f"Approved:           {stats.policies_approved}")
print(f"Rejected:           {stats.policies_rejected}")
print(f"Security reviews:   {stats.security_reviews}")
print(f"Escalations:        {stats.escalations}")
print(f"Emergency stops:    {stats.emergency_stops}")
print(f"Governance coverage:{stats.governance_coverage:.1%}")
```

---

## Audit Log Retention

The audit trail is a bounded ring-buffer (default: 10,000 entries).
For long-term compliance archiving, subscribe to governance events and
persist to a durable store:

```python
import json

def persist_audit(event):
    with open("audit_log.jsonl", "a") as f:
        f.write(json.dumps(event.to_dict()) + "\n")

engine.event_bus.add_listener(persist_audit)
```
