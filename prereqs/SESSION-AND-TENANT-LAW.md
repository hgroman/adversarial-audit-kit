# Session and Tenant Management Law

**Version**: 1.1
**Created**: 2025-12-11
**Updated**: 2025-12-11 (Phase 9 preparation)
**Authority**: BINDING. This is THE source of truth. All other documents defer to this.
**Origin**: 30-Hour Multi-Tenancy Migration (Commits: `f42f09f`, `2829573`, `541f776`)
**Consolidated**: 2025-12-19 (Merged duplicate `async_session` engine into `db/session` - Commit: `docs: purge legacy references`)

---

## Why This Document Exists

The codebase had no centralized paradigm. The result:
- 30 hours of debugging
- 66 anti-pattern fixes
- Bugs that slept for months
- Anxiety and stress from unpredictable failures

**This document is the law. One source of truth. No exceptions.**

---

## The Three Service Types

Every piece of code that touches the database falls into exactly ONE of these categories:

### Type 1: CRUD Routes (API Endpoints)

**What they are**: FastAPI route handlers that respond to HTTP requests.

**Session Provider**: `get_db_session` (via `Depends()`)

**Transaction Management**: AUTO-COMMIT. The provider handles commit on success, rollback on error.

**RLS Requirement**: ALWAYS. Every query must be inside `with_tenant_context()`.

**`session.begin()`**: **NEVER**. The provider already manages the transaction.

```python
# ✅ CORRECT: CRUD Route
@router.post("/items")
async def create_item(
    request: ItemRequest,
    session: AsyncSession = Depends(get_db_session),  # Auto-commits
    current_user: dict = Depends(get_current_user)
):
    # 1. Fail fast on missing tenant
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="No tenant_id in token")

    # 2. RLS context - ALWAYS
    async with with_tenant_context(session, tenant_id):
        # 3. Database operations - NO session.begin()
        item = Item(**request.dict(), tenant_id=tenant_id)
        session.add(item)
        return item
    # 4. Auto-commit happens when request completes
```

```python
# ❌ WRONG: session.begin() with auto-commit provider
@router.post("/items")
async def create_item(session: AsyncSession = Depends(get_db_session)):
    async with session.begin():  # ❌ CAUSES "transaction already begun" ERROR
        session.add(item)
```

---

### Type 2: Background Tasks (Inline or Service)

**What they are**: Async functions that run outside the request/response cycle.

**Session Provider**: `get_session()` or `get_session_context()` (raw sessions)

**Transaction Management**: MANUAL. You must use `session.begin()`.

**RLS Requirement**: ALWAYS (after you know the tenant_id).

**`session.begin()`**: **REQUIRED**. Raw sessions don't auto-commit.

```python
# ✅ CORRECT: Background Task
async def process_item_background(item_id: str, tenant_id: str):
    async with get_session_context() as session:
        async with session.begin():  # REQUIRED for commit
            async with with_tenant_context(session, tenant_id):
                item = await session.get(Item, item_id)
                item.status = "processed"
        # Commits when begin() block exits
```

```python
# ❌ WRONG: Missing session.begin() - NEVER COMMITS
async def process_item_background(item_id: str, tenant_id: str):
    async with get_session_context() as session:
        async with with_tenant_context(session, tenant_id):
            item = await session.get(Item, item_id)
            item.status = "processed"  # ❌ This change is LOST
```

---

### Type 3: Schedulers (Two-Phase Pattern)

**What they are**: Background jobs that process queued items across ALL tenants.

**The Problem**: RLS blocks queries until you set tenant context. But you don't know the tenant_id until you query the row. Chicken-and-egg.

**The Solution**: Two-Phase Pattern.

**Phase 1 - Discovery**: Bypass RLS to find queued items and get their tenant_ids.
**Phase 2 - Processing**: Apply RLS per item using its tenant_id.

```python
# ✅ CORRECT: Scheduler Two-Phase Pattern
async def process_queue():
    # PHASE 1: Discovery (bypass RLS)
    session = await get_session()
    try:
        async with session.begin():
            # Bypass RLS to see all tenants' queued items
            await session.execute(text("SET ROLE postgres"))

            stmt = select(Item.id, Item.tenant_id).where(Item.status == "queued").limit(10)
            result = await session.execute(stmt)
            items_to_process = [(row.id, row.tenant_id) for row in result]

            # Mark as processing while we have the lock
            if items_to_process:
                ids = [item[0] for item in items_to_process]
                await session.execute(
                    update(Item).where(Item.id.in_(ids)).values(status="processing")
                )
    finally:
        await session.close()

    # PHASE 2: Processing (apply RLS per item)
    for item_id, tenant_id in items_to_process:
        async with get_session_context() as session:
            async with session.begin():
                async with with_tenant_context(session, str(tenant_id)):
                    # Now RLS is enforced for this tenant
                    item = await session.get(Item, item_id)
                    await process_single_item(item)
                    item.status = "completed"
```

**Alternative: Chicken-and-Egg Pattern** (for single-item processing or webhooks)

This pattern applies when:
- **Schedulers** processing a single item by ID
- **Webhook routers** receiving callbacks without JWT tokens (e.g., n8n, Stripe, etc.)

```python
# ✅ CORRECT: Chicken-and-Egg Pattern
async def process_single_item_wrapper(item_id: UUID, session: AsyncSession):
    async with session.begin():
        # Step 1: Bypass RLS to get tenant_id
        await session.execute(text("SET ROLE postgres"))
        try:
            stmt = select(Item).where(Item.id == item_id)
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
        finally:
            await session.execute(text("RESET ROLE"))  # ALWAYS reset

        if not item or not item.tenant_id:
            raise ValueError(f"Item {item_id} not found or has no tenant_id")

        # Step 2: Apply RLS with known tenant_id
        async with with_tenant_context(session, str(item.tenant_id)):
            # Process with RLS enforced
            await do_work(item)
            item.status = "completed"
```

**Real-World Example: Webhook Router (wf8_n8n_webhook_router.py)**

```python
# ✅ CORRECT: Webhook Chicken-and-Egg Pattern
# Webhooks don't have JWT tokens - must discover tenant_id from data

await session.execute(text("SET ROLE postgres"))
try:
    stmt = select(Contact.tenant_id).where(Contact.id == request.contact_id)
    result = await session.execute(stmt)
    contact_row = result.first()
finally:
    await session.execute(text("RESET ROLE"))  # ALWAYS reset

if not contact_row or not contact_row.tenant_id:
    raise HTTPException(status_code=404, detail="Contact not found")

tenant_id = str(contact_row.tenant_id)

# Now use discovered tenant_id for RLS-protected operations
async with with_tenant_context(session, tenant_id):
    result = await service.process_enrichment(request, session)
```

### Chicken-and-Egg Implementation Registry

**CRITICAL:** Always use `select()` + `scalar_one_or_none()`, NOT `session.get()`.

| Workflow | File | Pattern | Status |
|----------|------|---------|--------|
| WF3 | `wf3_domain_extraction_scheduler.py:65-108` | `select()` + `scalar_one_or_none()` | ✅ Verified |
| WF3 | `wf3_business_to_domain_service.py:54-76` | `select()` + `scalar_one_or_none()` | ✅ Verified |
| WF5 | `wf5_processing_service.py:384-490` | `select()` + `scalars().first()` | ✅ Verified |
| WF8 | `wf8_n8n_webhook_router.py:244-260` | `select()` + `first()` | ✅ Verified |
| WF5 | `wf5_sitemap_import_service.py:59-87` | `select()` + `scalar_one_or_none()` | ✅ Fixed (commit `d26878e`, 2025-12-16) |

**Copy-Paste Source:** `wf3_domain_extraction_scheduler.py` lines 65-108 is the canonical working example for schedulers using `run_job_loop`.

**Why `select()` not `session.get()`:**
- `session.get()` may use cached/identity-mapped objects that don't reflect the current role
- `select()` always executes a fresh query against the database with the current role

### Chicken-and-Egg Anti-Patterns (CRITICAL)

> **Incident Reference:** WF5 Sitemap Import RLS Bug (Dec 2025, commits `c1fa6e8` through `f524784`)
> Records stuck in "Processing" forever because service re-fetched after setting tenant context.

#### ❌ Anti-Pattern 1: Re-fetching After Tenant Context

```python
# ❌ WRONG - Re-fetching inside tenant context FAILS
async def process_item(item_id, session):
    # Step 1: Fetch without RLS (works)
    item = await session.get(Item, item_id)
    tenant_id = str(item.tenant_id)

    # Step 2: Set tenant context
    async with with_tenant_context(session, tenant_id):
        # ❌ RE-FETCH - This FAILS! RLS blocks visibility
        fresh_item = await session.get(Item, item_id)
        if not fresh_item:
            logger.error("Item not found")  # Record stuck forever
            return
        await do_work(fresh_item)
```

**Why it fails:** After `with_tenant_context` sets `ROLE app_worker`, RLS policies apply. The record may not be visible if the policy check fails (e.g., `auth.uid()` is NULL for schedulers).

#### ✅ Correct Pattern: Use Same Object

```python
# ✅ CORRECT - Use the SAME object, don't re-fetch
async def process_item(item_id, session):
    # Step 1: Fetch without RLS
    await session.execute(text("SET ROLE postgres"))
    try:
        stmt = select(Item).where(Item.id == item_id)
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
    finally:
        await session.execute(text("RESET ROLE"))

    tenant_id = str(item.tenant_id)

    # Step 2: Set tenant context and use SAME object
    async with with_tenant_context(session, tenant_id):
        # ✅ NO re-fetch - use the object we already have
        await do_work(item)
        item.status = "completed"  # SQLAlchemy tracks changes
```

#### ❌ Anti-Pattern 2: Service Managing Own Transactions

```python
# ❌ WRONG - Service commits inside with_tenant_context
async with with_tenant_context(session, tenant_id):
    await do_work(item)
    await session.commit()  # ❌ Closes transaction, breaks context manager
    # Error: "Can't operate on closed transaction inside context manager"
```

**Rule:** Services should NOT call `session.commit()` or `session.rollback()`. The caller (scheduler or router) manages the transaction.

---

## RLS Context Ownership

### The Core Principle

**Routers own RLS context. Services operate within it.**

This is the layered responsibility pattern that governs tenant isolation:

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
│    │  - May receive tenant_id as parameter for data ops      │  │
│    │  - Trusts that caller has set the context               │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Why Services Don't Set Context

1. **Single Responsibility**: Services handle business logic, not authentication
2. **Reusability**: Services are called by multiple consumers (routers, background tasks, other services)
3. **Caller Knows Best**: The caller (router) has the JWT; the service should be tenant-agnostic
4. **Avoid Double-Context**: Nesting `with_tenant_context` is wasteful and confusing

### Correct Pattern

```python
# ✅ CORRECT: Router owns context, service operates within it
@router.post("/places/status")
async def update_status(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="No tenant_id")

    # Router sets context
    async with with_tenant_context(session, tenant_id):
        # Service operates within context - does NOT set its own
        result = await PlacesService.update_status(
            session=session,
            place_id=place_id,
            status=status,
            tenant_id=tenant_id  # Passed for data operations, not for RLS
        )
    return result
```

```python
# ✅ CORRECT: Service trusts caller has set context
class PlacesService:
    @staticmethod
    async def update_status(session, place_id, status, tenant_id):
        # No with_tenant_context here - caller already set it
        # tenant_id is used for data assignment, not RLS
        stmt = update(Place).where(Place.id == place_id).values(status=status)
        await session.execute(stmt)
```

### Exception: Background Tasks and Schedulers

Background tasks and schedulers have no router above them. They ARE the context owner:

```python
# ✅ CORRECT: Background task owns its own context
async def process_item_background(item_id: str, tenant_id: str):
    async with get_session_context() as session:
        async with session.begin():
            # Background task sets context (no router above it)
            async with with_tenant_context(session, tenant_id):
                await SomeService.do_work(session, item_id)
```

### How to Know Who Owns Context

| Code Location | Context Owner? | Sets `with_tenant_context`? |
|---------------|----------------|----------------------------|
| Router endpoint | ✅ YES | ✅ YES |
| Service method | ❌ NO | ❌ NO (trusts caller) |
| Background task | ✅ YES | ✅ YES |
| Scheduler | ✅ YES | ✅ YES (after discovery phase) |

### Common Mistake: Auditing Services for `with_tenant_context`

If you audit a service file and find it imports `with_tenant_context` but never uses it:
- **This is NOT a bug** (usually)
- Check if the service is called from a router that sets context
- The import may exist from migration work but isn't needed

**The audit question is**: "Does the ROUTER that calls this service set `with_tenant_context`?"

---

## Session Provider Reference

| Provider | Location | Auto-Commit? | Use `session.begin()`? | Use Case |
|----------|----------|--------------|------------------------|----------|
| `get_db_session` | `src/db/session.py` | ✅ YES | ❌ **NO** | CRUD routes |
| `get_session_context()` | `src/db/session.py` | ❌ NO | ✅ **YES** | Background tasks |
| `get_session()` | `src/db/session.py` | ❌ NO | ✅ **YES** | Schedulers |

---

## The Golden Rules

### Rule 1: Know Your Service Type
Before writing ANY database code, identify which type you're in:
- CRUD Route → Auto-commit, no `session.begin()`, RLS always
- Background Task → Manual commit, YES `session.begin()`, RLS always
- Scheduler → Two-Phase Pattern, YES `session.begin()`, postgres then RLS

### Rule 2: Never Mix Patterns
```python
# ❌ WRONG: Auto-commit provider + session.begin()
async def route(session: AsyncSession = Depends(get_db_session)):
    async with session.begin():  # CONFLICT
```

```python
# ❌ WRONG: Raw session without session.begin()
async def background_task():
    session = await get_session()
    session.add(item)  # NEVER COMMITS
```

### Rule 3: Fail Fast on Missing Tenant
```python
# ✅ CORRECT
tenant_id = current_user.get("tenant_id")
if not tenant_id:
    raise HTTPException(status_code=401, detail="No tenant_id in token")

# ❌ WRONG - Masks bugs
tenant_id = current_user.get("tenant_id") or DEFAULT_TENANT_ID
```

### Rule 4: Always Reset Role
```python
# ✅ CORRECT
await session.execute(text("SET ROLE postgres"))
try:
    # query
finally:
    await session.execute(text("RESET ROLE"))  # ALWAYS

# ❌ WRONG - Role leak
await session.execute(text("SET ROLE postgres"))
# query
# forgot to reset - next query runs as postgres!
```

### Rule 5: No Inline Functions in Routes
```python
# ❌ WRONG - Hard to audit, hides session management
@router.post("/")
async def endpoint():
    async def background_work():  # INLINE FUNCTION
        session = await get_session()
        # ...
    asyncio.create_task(background_work())

# ✅ CORRECT - Move to src/services/background/
from src.services.background.my_service import process_background
@router.post("/")
async def endpoint():
    asyncio.create_task(process_background(args))
```

### Rule 6: Registry Rule
All new endpoints, services, and schedulers MUST be registered in:
```
00_Current_Architecture/01_System_References/WORKFLOW-RLS-REGISTRY.yaml
```
Unregistered code is non-compliant and blocks merge.

### Rule 7: No DEFAULT_TENANT_ID Fallbacks in Business Logic
```python
# ❌ BANNED - Masks bugs, enables data leakage
tenant_id = current_user.get("tenant_id", DEFAULT_TENANT_ID)
tenant_id = record.tenant_id if record.tenant_id else DEFAULT_TENANT_ID

# ✅ CORRECT - Fail fast
tenant_id = current_user.get("tenant_id")
if not tenant_id:
    raise HTTPException(status_code=401, detail="No tenant_id in token")

# ✅ CORRECT - For services processing records
if not record.tenant_id:
    raise ValueError(f"Record {record.id} has no tenant_id - data integrity issue")
```

### Rule 8: Defense-in-Depth RLS Guard
To prevent data leaks from missing `with_tenant_context()` calls in routers/tasks, every service method MUST verify its own RLS context.

```python
# ✅ CORRECT: Service Layer Lockdown
from src.db.tenant_context import verify_rls_context

async def my_service_method(session, tenant_id, ...):
    # trap missing/mismatched context BEFORE executing any queries
    await verify_rls_context(session, tenant_id)
    # ...
```
See [SERVICE-CONSOLIDATION-LAW.md](./SERVICE-CONSOLIDATION-LAW.md) for full protocol.

**Exception**: `DEFAULT_TENANT_ID` is acceptable ONLY in:
- Model column defaults (for new record creation)
- Development/testing fixtures
- **`src/auth/jwt_auth.py`** - Dev token generation only (when `DEV_MODE=true`)
- NEVER in routers, services, or schedulers

**Documented Exception: jwt_auth.py (line ~176)**
```python
# ✅ ALLOWED: Dev token generation for local testing
# This fallback ONLY applies when DEV_MODE=true and no real JWT is provided
# Production deployments MUST have DEV_MODE=false
tenant_id = current_user.get("tenant_id", DEFAULT_TENANT_ID)  # Dev mode only
```
This exception exists because local development often lacks a real auth provider.
**Risk**: If `DEV_MODE=true` in production, this could mask missing tenant_id bugs.

---

## File Organization

```
src/
├── routers/                    # Type 1: CRUD Routes
│   └── *.py                    # Use get_db_session, NO session.begin()
│
├── services/
│   ├── */                      # Business logic, receive sessions
│   └── background/             # Type 2 & 3: Background Tasks & Schedulers
│       └── wf*_scheduler.py    # Use get_session(), YES session.begin()
│
├── common/
│   └── curation_sdk/
│       └── scheduler_loop.py   # SDK for schedulers
│
└── db/
    ├── session.py              # Session providers
    └── tenant_context.py       # with_tenant_context
```

---

## Audit Commands

### Find violations of Rule 2 (session.begin with auto-commit)
```bash
for f in src/routers/*.py; do
  if grep -q "get_db_session\|get_session_dependency" "$f" && \
     grep -q "async with session.begin():" "$f"; then
    echo "VIOLATION: $f"
  fi
done
```

### Find violations of Rule 5 (inline functions in routes)
```bash
grep -rn "^        async def\|^            async def" src/routers/
```

### Find raw sessions missing session.begin()
```bash
# Manual review required - check each get_session() usage
grep -rn "await get_session()" src/ --include="*.py" | grep -v "session.begin"
```

---

## Pre-Commit Enforcement

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: session-begin-with-autocommit
        name: Block session.begin() with auto-commit providers
        entry: bash -c 'for f in src/routers/*.py; do if grep -q "get_db_session\|get_session_dependency" "$f" && grep -q "async with session.begin():" "$f"; then echo "BLOCKED: $f has session.begin() with auto-commit provider"; exit 1; fi; done'
        language: system
        pass_filenames: false

      - id: inline-functions-in-routers
        name: Block inline async functions in routers
        entry: bash -c 'if grep -rn "^        async def\|^            async def" src/routers/ --include="*.py" | grep -v "^$"; then echo "BLOCKED: Inline functions in routers"; exit 1; fi'
        language: system
        pass_filenames: false
```

---

## Compliance Status (2025-12-16)

| Check | Status | Notes |
|-------|--------|-------|
| session.begin() with auto-commit | ✅ CLEAN | 66 fixed in commit `f42f09f` |
| Missing session.begin() with raw session | ✅ CLEAN | 1 fixed in commit `2829573` |
| Missing imports | ✅ CLEAN | 1 fixed in commit `541f776` |
| Inline functions in routers | ✅ CLEAN | 0 found (resolved) |
| Scheduler Two-Phase Pattern | ✅ ALL CORRECT | All 10 schedulers verified |
| Service hardcoded fallbacks | ✅ CLEAN | 5 files fixed in Phase 9 prep |
| Router DEFAULT_TENANT_ID fallbacks | ✅ CLEAN | 0 in routers (all use JWT) |
| Inline SET ROLE (not with_tenant_context) | ✅ APPROVED | Scheduler discovery + chicken-and-egg patterns only |

---

## PR Review Checklist

**Every PR touching database code MUST pass this checklist.**

### Mandatory Checks (Blocks Merge)

- [ ] **Session Pattern**: No `session.begin()` in files using `get_db_session` or `get_session_dependency`
- [ ] **Tenant Context**: All DB operations inside `with_tenant_context()` (except scheduler discovery phase)
- [ ] **No Silent Fallbacks**: No `DEFAULT_TENANT_ID` used as fallback in routers or services
- [ ] **Role Cleanup**: Every `SET ROLE` has matching `RESET ROLE` in finally block
- [ ] **Registry Updated**: New endpoints/services added to `WORKFLOW-RLS-REGISTRY.yaml`

### Required Verification

- [ ] **Test with Different Tenant**: Tested with non-default tenant_id
- [ ] **Error Handling**: Graceful failure on missing tenant_id (HTTP 401, not silent default)
- [ ] **No Inline Functions**: No `async def` inside router functions

### Review Questions

1. What service type is this? (CRUD Route / Background Task / Scheduler)
2. Which session provider is being used?
3. Is RLS enforced on all database operations?
4. Can this code leak data to the wrong tenant?

---

## Related Documents

These documents provide additional context but defer to this law:
- `LESSONS-LEARNED-MULTI-TENANCY-MIGRATION.md` - Historical context
- `SESSION-MANAGEMENT-PATTERN-ANTIPATTERN-COMPANION.md` - Code examples
- `SESSION-MANAGEMENT-ARCHITECTURAL-CHARTER.md` - Architecture rules
- `SQLALCHEMY-PATTERNS-LAW.md` - SQLAlchemy-specific patterns (bulk inserts, etc.)

---

## Appendix A: SQLAlchemy Implementation Notes

This appendix covers SQLAlchemy-specific behaviors that affect database operations. For comprehensive coverage, see `SQLALCHEMY-PATTERNS-LAW.md`.

### A.1 Bulk Insert Key Consistency (Critical)

**When using `pg_insert().values(list_of_dicts)`, all dictionaries MUST have identical keys.**

```python
# ❌ ANTI-PATTERN: Conditional key inclusion
page_dict = {"id": page.id, "url": page.url}
if page.last_modified is not None:
    page_dict["last_modified"] = page.last_modified  # BREAKS bulk insert

# ✅ CORRECT: Always include all keys
page_dict = {
    "id": page.id,
    "url": page.url,
    "last_modified": page.last_modified,  # Include even if None
}
```

**Why**: SQLAlchemy generates a single INSERT statement based on the first dict's keys. Mismatched keys cause: `INSERT value for column <table>.<column> is explicitly rendered as a boundparameter in the VALUES clause`

**Origin**: WF5 Sitemap Import fix (commit `d26878e`, 2025-12-16)

### A.2 Services Don't Commit

Services operating within a transaction (called from routers or schedulers) must NOT call `session.commit()` or `session.rollback()`. The caller manages the transaction.

```python
# ❌ WRONG: Service managing transaction
async def _do_process(self, item, session):
    try:
        # work
        await session.commit()  # ❌ Conflicts with caller's transaction
    except:
        await session.rollback()  # ❌ Conflicts with caller's transaction

# ✅ CORRECT: Service operates within caller's transaction
async def _do_process(self, item, session):
    # work
    # No commit/rollback - caller handles it
    # On error, raise exception to let caller rollback
```

**Origin**: WF5 Sitemap Import fix (commit `f524784`, 2025-12-16) - removed 12 explicit commit/rollback calls

### A.3 Use flush() for Intermediate Results

When you need query results (like `rowcount`) without committing:

```python
result = await session.execute(insert_stmt)
await session.flush()  # Makes rowcount available
rows_inserted = result.rowcount  # Now accessible
# Transaction still open - caller will commit
```

---

## Sign-Off

This is the law. Violations block merges.

| Role | Signature | Date |
|------|-----------|------|
| Author | Claude (Cascade) | 2025-12-11 |
| Approver | | |

---

**Remember**: The code that works by accident will fail by surprise. Follow this law.
