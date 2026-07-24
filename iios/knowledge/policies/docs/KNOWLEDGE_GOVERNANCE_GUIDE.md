# Knowledge Governance Guide

## Governance Workflow (6 Phases)

```
1. Validate Request       → structural checks (7 validation codes)
2. Load Policies          → active_only() from registry
3. Evaluate Policies      → KnowledgePolicyEvaluator per policy
4. Resolve Conflicts      → PolicyPriorityResolver
5. Generate Audit Trail   → PolicyAuditEntry per policy
6. Build Response         → KnowledgePolicyResponse
```

## Conflict Resolution Rules

| Priority | Overrides |
|---|---|
| BLOCKED | Everything |
| REJECTED | APPROVED, APPROVED_WITH_CONDITIONS |
| ESCALATED | APPROVED_WITH_CONDITIONS |
| MANUAL_REVIEW | APPROVED (automatic) |
| STEWARD_APPROVAL | APPROVED (automatic) |
| APPROVED_WITH_CONDITIONS | APPROVED |
| APPROVED | Base case |

## Policy Actions

| Action | Description |
|---|---|
| `APPROVE` | Knowledge accepted |
| `APPROVE_WITH_CONDITIONS` | Accepted with caveats |
| `REJECT` | Knowledge not accepted |
| `BLOCK` | Hard stop — highest severity |
| `ESCALATE` | Route to senior review |
| `REQUIRE_MANUAL_REVIEW` | Human review required |
| `REQUIRE_STEWARD_APPROVAL` | Domain steward must approve |
| `ARCHIVE` | Mark for archival |

## GovernanceDecision Outcomes

```python
from iios.knowledge.policies import GovernanceDecision

GovernanceDecision.APPROVED
GovernanceDecision.APPROVED_WITH_CONDITIONS
GovernanceDecision.REJECTED
GovernanceDecision.BLOCKED
GovernanceDecision.ESCALATED
GovernanceDecision.MANUAL_REVIEW
GovernanceDecision.STEWARD_APPROVAL
GovernanceDecision.ARCHIVED
```

## Policy Domains (11)

```
CLASSIFICATION, METADATA, VERSIONING, RETENTION, PUBLICATION,
ACCESS, PRIVACY, SECURITY, COMPLIANCE, AUDIT, ENTERPRISE
```

## Policy Types (15)

```
CLASSIFICATION, QUALITY, VALIDATION, VERSIONING, RETENTION,
PUBLICATION, SECURITY, PRIVACY, COMPLIANCE, ACCESS,
PROVENANCE, LINEAGE, LIFECYCLE, AUDIT, ENTERPRISE
```

## Statistics (8 counters)

```python
stats = engine.statistics()
# {
#   "policies_evaluated":         int,
#   "policies_approved":          int,
#   "policies_rejected":          int,
#   "policies_blocked":           int,
#   "manual_reviews":             int,
#   "escalations":                int,
#   "average_evaluation_time_ms": float,
#   "governance_coverage":        float,
# }
```
