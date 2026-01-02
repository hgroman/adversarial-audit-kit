# MANDATORY PREREQUISITES FOR ALL AUDITS

> ⚠️ **STOP**: No audit findings are valid until these documents are read.

## Required Reading (In Order)

Before reporting ANY violation related to RLS, tenant context, sessions, or database patterns, the auditor MUST read and understand:

| # | Document | Path | Purpose |
|---|----------|------|---------|
| 1 | **SESSION-AND-TENANT-LAW.md** | `00_The_Law/SESSION-AND-TENANT-LAW.md` | Binding law for all session/tenant patterns |
| 2 | **00_RLS-CRITICAL-PATH.md** | `00_The_Law/00_RLS-CRITICAL-PATH.md` | RLS critical path, header requirements |
| 3 | **ADR-007-RLS-TENANT-CONTEXT-PATTERN.md** | `00_The_Law/ADR-007-RLS-TENANT-CONTEXT-PATTERN.md` | Pattern establishment and rationale |
| 4 | **SYSTEM_MAP.md** | `01_System_References/SYSTEM_MAP.md` | Architecture overview, RLS context ownership table |
| 5 | **WORKFLOW-RLS-REGISTRY.yaml** | `01_System_References/WORKFLOW-RLS-REGISTRY.yaml` | Canonical workflow→service→table mapping |

## Validation Rule

**Any "violation" finding MUST cite which specific section of which law document it contradicts.**

If a pattern is documented as intentional in any of these five documents, it is NOT a violation.

### Examples of Intentional Patterns (NOT Violations)

1. **Self-enforcing services** (e.g., `job_service.py`) - Defense in depth, documented in SYSTEM_MAP.md
2. **Scheduler delegation** (e.g., `wf4_sitemap_discovery_scheduler.py` delegates to adapter) - Documented in WORKFLOW-RLS-REGISTRY.yaml
3. **Chicken-and-Egg pattern** for webhooks - Documented in SESSION-AND-TENANT-LAW.md

## Failure Mode This Prevents

On 2025-12-26, an adversarial audit created a false Work Order (WO-RLS-LAW-VIOLATION-FIX.md) claiming `job_service.py` violated RLS ownership rules. The audit ran grep commands and found `with_tenant_context` calls inside the service, concluding this was a violation.

**The audit was wrong.** The self-enforcing pattern is intentional and documented. Hours were wasted before the documentation was properly consulted.

## Enforcement

All audit templates in this folder MUST include a reference to this file at the top of their prompt section.
