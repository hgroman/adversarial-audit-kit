# 🚨 RLS CRITICAL PATH - READ THIS FIRST 🚨

**Version:** 1.0
**Created:** 2025-12-14
**Authority:** BINDING - This document is the entry point for all RLS-related work
**Origin:** Post-audit discovery of documentation gaps that misled AI pairing partners

---

## ⚠️ THIS WILL SINK THE SHIP ⚠️

Row-Level Security (RLS) is the **foundation of multi-tenancy** in ScraperSky.

**If you get this wrong:**
- Tenant A sees Tenant B's data
- You have a data breach
- The platform is legally liable
- 30+ hours of debugging (we've been there)

**This is not optional. This is not negotiable. This is the law.**

---

## Before You Write ANY Database Code

### Step 1: Know Your Role

| I am writing a... | Am I a Context Owner? | Do I call `with_tenant_context()`? |
|-------------------|----------------------|-----------------------------------|
| **Router endpoint** | ✅ YES | ✅ YES - I set context for services I call |
| **Service method** | ❌ NO | ❌ NO - I trust my caller set it |
| **Background task** | ✅ YES | ✅ YES - No router above me |
| **Scheduler** | ✅ YES | ✅ YES - After discovery phase |

### Step 2: Understand the Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│  ROUTER (Context Owner)                                         │
│  - Extracts tenant_id from JWT                                  │
│  - Calls with_tenant_context(session, tenant_id)                │
│  - All service calls happen INSIDE this context                 │
│                                                                 │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │  SERVICE (Context Participant)                          │  │
│    │  - Receives session (already in RLS context)            │  │
│    │  - Does NOT call with_tenant_context() itself           │  │
│    │  - Trusts that caller has set the context               │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight:** Routers own context. Services operate within it.

### Step 3: Check the Registry

Before modifying any file, verify it's listed in:
```
00_Current_Architecture/01_System_References/WORKFLOW-RLS-REGISTRY.yaml
```

If it's not listed, **add it before you start work**.

### Step 4: Follow the Law

Read the full rules in:
```
00_Current_Architecture/00_The_Law/SESSION-AND-TENANT-LAW.md
00_Current_Architecture/00_The_Law/SERVICE-CONSOLIDATION-LAW.md
```

Especially the sections: **§RLS Context Ownership** and **§Meteor-Proof Service Architecture**.

---

## Quick Decision Tree

```
Are you touching the database?
│
├─ NO → You're fine, carry on
│
└─ YES → What type of code are you in?
         │
         ├─ Router endpoint?
         │   └─ YOU set with_tenant_context()
         │      Services you call do NOT set it
         │
         ├─ Service method?
         │   └─ You do NOT set with_tenant_context()
         │      Your CALLER (router) already set it
         │      🚨 DEFENSE-IN-DEPTH: You MUST call verify_rls_context()
         │
         ├─ Background task?
         │   └─ YOU set with_tenant_context()
         │      You have no router above you
         │
         └─ Scheduler?
             └─ Two-phase pattern:
                1. Discovery: SET ROLE postgres (bypass RLS)
                2. Processing: with_tenant_context() per item
```

---

## Common Mistakes That Will Sink You

### Mistake 1: Auditing Services for `with_tenant_context` Usage

**Wrong thinking:** "This service imports `with_tenant_context` but never uses it - BUG!"

**Reality:** Services don't set context. Their callers do. Check the ROUTER.

### Mistake 2: Adding `with_tenant_context` to a Service

**Wrong:** Adding context setting inside a service method.

**Right:** The router that calls the service should set context.

### Mistake 3: Forgetting Context in Background Tasks

Background tasks have no router above them. They ARE the context owner.

```python
# ✅ CORRECT: Background task sets its own context
async def process_item_background(item_id: str, tenant_id: str):
    async with get_session_context() as session:
        async with session.begin():
            async with with_tenant_context(session, tenant_id):
                await SomeService.do_work(session, item_id)
```

---

## File Header Requirement

All files in `src/routers/`, `src/services/`, and `src/services/background/` should have an RLS CONTRACT header:

```python
"""
[filename] - [description]

RLS CONTRACT:
  Role: Owner | Participant | Exempt
  Context Set By: [self | caller filename | N/A]
  Tables Touched: [list]
  Governing Law: SESSION-AND-TENANT-LAW.md
"""
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [SESSION-AND-TENANT-LAW.md](./SESSION-AND-TENANT-LAW.md) | The binding law - Three Service Types, Golden Rules |
| [SERVICE-CONSOLIDATION-LAW.md](./SERVICE-CONSOLIDATION-LAW.md) | Specialist Service patterns, RLS Guards, and Factory usage |
| [SYSTEM_MAP.md](../01_System_References/SYSTEM_MAP.md) | Architecture overview with RLS layers |
| [WORKFLOW-RLS-REGISTRY.yaml](../01_System_References/WORKFLOW-RLS-REGISTRY.yaml) | File-by-file RLS tracking |

---

## Audit Tool

Run this to check for RLS violations:
```bash
python tools/architecture_audit.py
```

This checks for (includes but not limited to):
- DEFAULT_TENANT_ID fallbacks
- SET ROLE without RESET ROLE
- session.begin() with auto-commit providers
- Ghost UUIDs
- Missing RLS Contract headers
- Column defaults
- Dev User UUID references

---

## Sign-Off

This document exists because an AI pairing partner was misled by unclear documentation and nearly proposed incorrect "fixes" to working code.

**The cost of confusion:** Hours of debugging, false alarms, wasted effort.

**The cost of this document:** 10 minutes to read.

**Read it. Follow it. Don't sink the ship.**

---

| Role | Signature | Date |
|------|-----------|------|
| Author | Claude (Cascade) | 2025-12-14 |
| Trigger | Audit confusion incident | 2025-12-14 |
