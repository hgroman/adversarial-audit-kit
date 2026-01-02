# ADR-007: RLS Tenant Context Pattern

**Status:** ACCEPTED
**Date:** 2025-12-10 (Original), 2025-12-16 (Rewritten)
**Authors:** Development Team + AI Assistants
**Supersedes:** Original ADR-007 inline SET ROLE patterns
**Related:** ADR-004 (Transaction Boundaries), ADR-008 (Dual-Session), ADR-009 (DEFAULT_TENANT_ID Removal)

> **Historical Note:** This ADR was originally written before `with_tenant_context()` existed. The inline SET ROLE patterns shown as "approved" in the original version are now deprecated and blocked by pre-commit hooks. This document has been rewritten to reflect the current canonical pattern.

---

## Context

ScraperSky implements multi-tenancy using PostgreSQL Row Level Security (RLS). Every query against an RLS-protected table must have tenant context set, which requires:

1. **Role switch**: `SET ROLE app_worker` to switch from postgres (superuser with BYPASSRLS) to app_worker (respects RLS)
2. **Tenant ID**: `set_config('app.current_tenant_id', ...)` to set the tenant ID that RLS policies check
3. **Cleanup**: `RESET ROLE` after operations to prevent connection pool pollution

Initially, these operations were performed inline in every endpoint. This led to:
- Inconsistent implementations
- Forgotten RESET ROLE in finally blocks
- Connection pool pollution when errors occurred
- Difficult-to-audit codebase

---

## Decision

### The Canonical Pattern: `with_tenant_context()`

All RLS tenant context MUST be set using the centralized context manager:

```python
from src.db.tenant_context import with_tenant_context

async with with_tenant_context(session, tenant_id):
    # All database operations here are RLS-scoped to tenant_id
    result = await session.execute(select(Model))
    # RESET ROLE handled automatically when exiting context
```

**Location:** `src/db/tenant_context.py`

This pattern:
- Encapsulates SET ROLE + set_config + RESET ROLE
- Guarantees cleanup in finally block (even on exceptions)
- Provides a single auditable pattern
- Is enforced by pre-commit hooks

---

## Implementation Patterns

### Pattern 1: Router Endpoints

Routers own RLS context. Services operate within it.

```python
from src.db.session import get_db_session
from src.db.tenant_context import with_tenant_context
from src.auth.jwt_auth import get_current_user

@router.get("/domains")
async def get_domains(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="No tenant_id in token")

async with with_tenant_context(session, tenant_id):
        # RLS automatically filters to this tenant's data
        result = await session.execute(select(Domain))
        return result.scalars().all()
```

**Key Points:**
- Use `get_db_session` (auto-commits on success)
- Extract `tenant_id` from JWT via `get_current_user`
- Wrap all database operations in `with_tenant_context`
- Services called inside do NOT set their own context

### Pattern 2: Background Tasks

Background tasks have no router above them - they own their context.

```python
from src.db.session import get_session_context
from src.db.tenant_context import with_tenant_context

async def process_item_background(item_id: str, tenant_id: str):
    async with get_session_context() as session:
        # Background task owns its context (no router above)
        async with with_tenant_context(session, tenant_id):
            item = await session.get(Item, item_id)
            item.status = "processed"
            await session.commit()  # Manual commit for background tasks
```

**Key Points:**
- Use `get_session_context()` (manual commit required)
- The task receives `tenant_id` from whoever enqueued it
- Must call `await session.commit()` explicitly

### Pattern 3: Schedulers (Two-Phase)

Schedulers need cross-tenant discovery, then per-item processing.

```python
from src.db.session import get_session_context
from src.db.tenant_context import with_tenant_context
from sqlalchemy import text

async def run_scheduler():
    # Phase 1: Cross-tenant discovery (bypass RLS)
    async with get_session_context() as session:
        await session.execute(text("SET ROLE postgres"))  # Superuser for discovery
        try:
            items = await session.execute(
                select(Item.id, Item.tenant_id).where(Item.status == "queued")
            )
            queued_items = items.fetchall()
        finally:
            # Not strictly required here since session is closing,
            # but good practice
            pass

    # Phase 2: Per-item processing (with RLS)
    for item_id, item_tenant_id in queued_items:
        async with get_session_context() as session:
            async with with_tenant_context(session, item_tenant_id):
                item = await session.get(Item, item_id)
                await process_item(session, item)
                await session.commit()
```

**Key Points:**
- Phase 1 uses `SET ROLE postgres` to discover items across ALL tenants
- Phase 2 uses `with_tenant_context()` for each item's tenant
- Each item gets its own session to isolate failures

### Pattern 4: Services (Context Participants)

Services do NOT set RLS context - they trust their caller.

```python
# ✅ CORRECT: Service trusts caller has set context
class DomainService:
    @staticmethod
    async def update_status(session: AsyncSession, domain_id: str, status: str):
        # No with_tenant_context here - caller already set it
        stmt = update(Domain).where(Domain.id == domain_id).values(status=status)
        await session.execute(stmt)
```

**Why?**
- Single Responsibility: Services handle business logic, not authentication
- Reusability: Services are called by routers, background tasks, other services
- Caller Knows Best: The caller has the JWT; the service is tenant-agnostic

---

## What `with_tenant_context()` Does Internally

```python
# src/db/tenant_context.py
@asynccontextmanager
async def with_tenant_context(
    session: AsyncSession,
    tenant_id: str,
) -> AsyncGenerator[AsyncSession, None]:
    """Set tenant context for RLS and ALWAYS clean up."""
    try:
        # Switch from postgres superuser to app_worker (respects RLS)
        await session.execute(text("SET ROLE app_worker;"))

        # Set tenant ID for RLS policy evaluation
        # The 'true' parameter makes this local to the current transaction
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

        yield session

    finally:
        # ALWAYS clean up to prevent connection pool pollution
        try:
            await session.execute(text("RESET ROLE;"))
        except Exception:
            # Connection may be closed or in failed transaction
            pass
```

---

## Deprecated Patterns (DO NOT USE)

### Inline SET ROLE in Routers

```python
# ❌ DEPRECATED - Pre-commit hook "prefer-tenant-context" warns against this
@router.get("/items")
async def get_items(session: AsyncSession = Depends(get_db_session)):
    await session.execute(text("SET ROLE app_worker;"))
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": tenant_id}
    )
    try:
        result = await session.execute(select(Item))
    finally:
        await session.execute(text("RESET ROLE;"))  # Easy to forget!
```

**Why deprecated?**
- Easy to forget RESET ROLE in finally block
- Inconsistent implementations across codebase
- Hard to audit

### DEFAULT_TENANT_ID Fallback

```python
# ❌ DEPRECATED - Pre-commit hook "no-default-tenant-fallback-routers" blocks this
tenant_id = current_user.get("tenant_id") or DEFAULT_TENANT_ID
```

**Why deprecated?**
- Masks missing tenant context
- Creates data leakage risk
- See ADR-009 for full explanation

**Exception:** `DEFAULT_TENANT_ID` exists in `src/auth/jwt_auth.py` for development bypass mode only. This is an allowed exception per ADR-009.

---

## Migration Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ COMPLETE | `with_tenant_context()` created in `src/db/tenant_context.py` |
| Phase 2 | ✅ COMPLETE | Major endpoints migrated to use context manager |
| Phase 3 | ✅ COMPLETE | Pre-commit hooks enforce pattern |
| Phase 4 | ⚠️ EXCEPTION | `DEFAULT_TENANT_ID` remains in `jwt_auth.py` for dev bypass (per ADR-009) |

---

## Enforcement

### Pre-commit Hooks

| Hook | What It Does |
|------|--------------|
| `prefer-tenant-context` | Warns on inline SET ROLE patterns |
| `no-default-tenant-fallback-routers` | Blocks DEFAULT_TENANT_ID fallbacks in routers |
| `set-role-needs-reset` | Requires RESET ROLE with SET ROLE (if inline pattern used) |

### Architecture Audit

```bash
python tools/architecture_audit.py
```

---

## Quick Reference: Who Owns RLS Context?

| Code Location | Context Owner? | Sets `with_tenant_context`? |
|---------------|----------------|----------------------------|
| Router endpoint | ✅ YES | ✅ YES |
| Service method | ❌ NO | ❌ NO (trusts caller) |
| Background task | ✅ YES | ✅ YES |
| Scheduler discovery phase | ✅ YES | Uses `SET ROLE postgres` |
| Scheduler processing phase | ✅ YES | ✅ YES (per-item) |

---

## Related Decisions

- **SESSION-AND-TENANT-LAW.md** - The canonical reference for all session and tenant patterns
- **ADR-004** - Transaction Boundaries (session providers)
- **ADR-008** - Dual-Session Pattern (auto-commit vs manual-commit)
- **ADR-009** - DEFAULT_TENANT_ID Removal (exception for dev bypass)

---

*This ADR was rewritten on 2025-12-16 to reflect the evolution from inline SET ROLE patterns to the centralized `with_tenant_context()` pattern.*
