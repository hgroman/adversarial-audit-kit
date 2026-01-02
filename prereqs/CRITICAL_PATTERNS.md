```yaml
# Document Governance
doc_id: "CRITICAL_PATTERNS.md"
doc_tier: "Tier 4 – Builder Kit (Derived)"
authority: "DERIVED"
truth_scope: "pattern guidance only; cannot override Law/ADR/Registry"
defers_to:
  - "00_The_Law/SESSION-AND-TENANT-LAW.md"
  - "00_The_Law/ADR-007-RLS-TENANT-CONTEXT-PATTERN.md"
  - "00_The_Law/ADR-004-Transaction-Boundaries.md"
  - "00_The_Law/ADR-003-Dual-Status-Workflow.md"
  - "01_System_References/WORKFLOW-RLS-REGISTRY.yaml"
  - "01_System_References/SYSTEM_MAP.md"
code_truth_anchors:
  - "src/db/engine.py"
  - "src/db/session.py"
  - "src/db/tenant_context.py"
change_control:
  ai_may: ["propose_edits"]
  ai_may_not: ["apply_edits", "apply_code_changes"]
  human_required_for: ["all_changes"]
last_verified: "2025-12-19"
audit_status: "pass"
staleness_policy:
  review_after_days: 90
  warn_after_days: 180
ghost_pattern_risk: true
rls_migration_check:
  contains_tenant_id_contracts: false
  contains_set_role: true
  contains_with_tenant_context: true
  expected_post_migration_state: "No tenant_id input contracts; tenant derived from session context."
  verified_against:
    - "src/db/tenant_context.py"
domain_primary_reference:
  dual_status: true
  transaction_boundaries: true
  session_management: true
```

# Critical Patterns (Must Follow)

**Document:** 07_CRITICAL_PATTERNS.md
**Type:** Reference
**Importance:** CRITICAL - Do not violate these patterns

---

## Overview

These patterns are NON-NEGOTIABLE. They are based on hard-learned lessons from ScraperSky production deployment.

---

## 1. Supavisor Connection Parameters

### The Pattern (MANDATORY)

```python
# In connect_args
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
}

# In execution_options
execution_options = {
    "isolation_level": "READ COMMITTED",
    "no_prepare": True,
    "raw_sql": True,
}
```

### Why This Matters

Supabase uses Supavisor for connection pooling. These parameters are REQUIRED for compatibility. Without them, you'll get:
- `prepared statement does not exist` errors
- Connection pool exhaustion
- Random disconnects

### Reference

See `src/db/engine.py` lines 140-192 in ScraperSky

---

## 2. Transaction Boundaries

### The Pattern (MANDATORY)

**Routers use auto-commit providers:**
```python
from src.db.session import get_db_session  # Canonical import

@router.post("/items")
async def create_item(
    data: ItemCreate,
    session: AsyncSession = Depends(get_db_session)  # AUTO-COMMITS on success
):
    # Service creates item
    item = await ItemService.create_item(session, data)

    # NO explicit commit - get_db_session handles it automatically
    return item
```

**Services execute within transactions (no commit):**
```python
class ItemService:
    @staticmethod
    async def create_item(session: AsyncSession, data: ItemCreate):
        item = Item(**data.dict())
        session.add(item)
        await session.flush()  # NOT commit! Router's auto-commit handles it
        return item
```

### Why This Matters

- `get_db_session` auto-commits on success, auto-rollbacks on error
- No explicit `commit()` needed in routers using dependency injection
- Services never commit - they flush to get IDs, caller manages transaction
- Prevents double-commit bugs

### What NOT To Do

❌ **Never explicitly commit when using get_db_session:**
```python
@router.post("/items")
async def create_item(session: AsyncSession = Depends(get_db_session)):
    item = await ItemService.create_item(session, data)
    await session.commit()  # ❌ WRONG - causes double commit!
    return item
```

❌ **Never do this in services:**
```python
async def create_item(data):
    async with get_session() as session:  # DON'T CREATE TRANSACTIONS
        item = Item(**data.dict())
        session.add(item)
        await session.commit()  # DON'T COMMIT IN SERVICES
```

---

## 3. Dual-Status Workflow Pattern

### The Pattern (MANDATORY for processable entities)

```python
class ProcessableEntity(Base):
    # User-facing status (user decisions)
    curation_status: Mapped[str] = mapped_column(String(50))

    # System-facing status (scheduler tracking)
    processing_status: Mapped[str] = mapped_column(String(50))
```

**Adapter converts between statuses:**
```python
if entity.curation_status == "Selected":
    entity.processing_status = "Queued"
```

**Scheduler queries processing_status:**
```python
entities = await session.execute(
    select(Entity).where(Entity.processing_status == "Queued")
)
```

### Why This Matters

- Separates user intent from system state
- Enables reliable background processing
- Prevents race conditions
- Clear audit trail

### When To Use

Use dual-status when:
- Users select items for processing
- Background schedulers process items
- Processing can fail and retry
- You need to track both "what user wants" and "what system is doing"

---

## 4. 3-Phase Long Operations

### The Pattern (MANDATORY for operations >1 second)

```python
# Phase 1: Write to database (fast)
async def queue_processing(session: AsyncSession, item_id: str):
    item = await get_item(session, item_id)
    item.processing_status = "Queued"
    await session.commit()
    # Release database connection here

# Phase 2: Perform computation (no DB connection)
async def process_item_background(item_id: str):
    # Long-running operation
    result = await expensive_api_call(item_id)
    return result

# Phase 3: Write results back (fast)
async def save_results(session: AsyncSession, item_id: str, result):
    item = await get_item(session, item_id)
    item.result = result
    item.processing_status = "Complete"
    await session.commit()
```

### Why This Matters

- Prevents connection pool exhaustion
- Enables horizontal scaling
- Improves reliability
- Reduces database load

### What NOT To Do

❌ **Never hold connections during long operations:**
```python
async def process_item(session: AsyncSession, item_id: str):
    item = await get_item(session, item_id)

    # DON'T DO THIS - holds connection for minutes
    result = await expensive_api_call()  # Takes 30 seconds

    item.result = result
    await session.commit()
```

---

## 5. Centralized Enums

### The Pattern (MANDATORY)

**All enums in one file:**
```python
# src/models/enums.py

from enum import Enum

class ItemStatus(str, Enum):
    Pending = "Pending"
    Processing = "Processing"
    Complete = "Complete"
    Error = "Error"

class UserRole(str, Enum):
    Admin = "Admin"
    User = "User"
```

### Why This Matters

- Single source of truth
- Prevents duplication
- Easy to maintain
- Prevents enum drift

### What NOT To Do

❌ **Never define enums in multiple files:**
```python
# models/item.py
class ItemStatus(Enum):  # DON'T
    Pending = "Pending"

# services/item_service.py
class ItemStatus(Enum):  # DON'T DUPLICATE
    Pending = "Pending"
```

---

## 6. Async Session Management

### The Pattern (MANDATORY)

**Use dependency injection with canonical import:**
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db_session  # Canonical import per CLAUDE.md

@router.get("/items")
async def list_items(
    session: AsyncSession = Depends(get_db_session)  # Auto-commits
):
    # Session automatically managed
    items = await ItemService.list_items(session)
    return items
```

**Note:** `get_db_session` (from `src/db/session.py`) is the **ONLY** valid source per SESSION-AND-TENANT-LAW.md. `get_session_dependency` is DEPRECATED.

### Why This Matters

- Automatic session cleanup
- Auto-commit on success, auto-rollback on error
- Connection pooling via Supavisor
- Testability

---

## 7. Retry Logic with Exponential Backoff

### The Pattern (RECOMMENDED for external APIs)

```python
async def call_external_api_with_retry(item_id: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = await external_api_call(item_id)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff: 5min, 10min, 20min
            delay_minutes = 5 * (2 ** attempt)
            await asyncio.sleep(delay_minutes * 60)
```

### Why This Matters

- Handles temporary failures
- Doesn't hammer failing services
- Gives time for service recovery
- Reduces wasted API calls

---

## Pattern Violations = Technical Debt

These patterns exist because:
1. They solve real production problems
2. Alternatives were tried and failed
3. Recovery from violations is expensive

**When in doubt, follow the pattern.**

---

## Reference

For complete implementations, see:
- **Supavisor:** `src/db/engine.py`
- **Transactions:** `src/routers/wf7_page_modernized_scraper_router.py`
- **Dual-Status:** `src/services/wf7_page_curation_service.py`
- **3-Phase:** `src/services/background/wf5_sitemap_import_scheduler.py`
- **Enums:** `src/models/enums.py`

---

## 8. Docker Build Verification

### The Pattern (MANDATORY)

**NEVER assume code works just because you wrote it.**

1.  **Run the build:** `docker compose up --build`
2.  **Check the logs:** `docker compose logs -f app`
3.  **Verify startup:** Ensure no "ImportError" or "ModuleNotFound" errors appear.

### Why This Matters

- We run in Docker on Render.com.
- Local environment != Production environment.
- "It works on my machine" is not a valid excuse.
- **If it doesn't build in Docker, it doesn't exist.**

---

## 9. Universal File Naming

### The Pattern (MANDATORY)

**All new files must follow the Workflow Prefix format:**
`wf[N]_[DescriptiveName].py`

**✅ Correct:**
- `src/models/wf8_contact.py`
- `src/routers/wf7_pages_router.py`

**❌ Incorrect:**
- `src/routers/pages_router.py` (No prefix)
- `src/routers/pages.py` (Ambiguous)

### Why This Matters

- **Instant Context:** You know exactly what a file does, where it lives, and what workflow it belongs to just by reading the name.
- **Preventing "Ghost Files":** Harder to lose track of files when they are numbered sequences.

---

## 10. Authentication Ownership

### The Pattern (MANDATORY)

**Routers own Authentication. Services are Auth-Agnostic.**

**✅ Correct (Router):**
```python
@router.post("/items")
async def create_item(
    item: ItemCreate,
    current_user: User = Depends(get_current_active_user),  # Router gets user
    session: AsyncSession = Depends(get_db_session)
):
    # Pass user_id or tenant_id explicitly
    return await ItemService.create(session, item, user_id=current_user.id)
```

**✅ Correct (Service):**
```python
class ItemService:
    async def create(session, item, user_id: UUID):
        # Service just uses the ID. It doesn't know about HTTP or JWTs.
        obj = Item(**item.dict(), user_id=user_id)
        session.add(obj)
```

**❌ Incorrect (Service):**
```python
class ItemService:
    async def create(session, item):
        # WRONG: Service trying to access HTTP context
        user = get_current_user()
```

### Why This Matters

- **Testing:** Services can be tested without mocking HTTP requests.
- **Background Jobs:** Schedulers don't have an HTTP context or a "current user".
- **Separation of Concerns:** Auth is an API concern. Logic is a Service concern.

---

---

## 11. Canonical Settings Import

### The Pattern (MANDATORY)

**Always import `settings` directly. Never use a getter function.**

**✅ Correct:**
```python
from src.config.settings import settings

def my_function():
    db_url = settings.DATABASE_URL
```

**❌ Incorrect:**
```python
from src.config import get_settings  # DO NOT USE
from functools import lru_cache

@lru_cache()
def get_settings(): ... # DO NOT DEFINE THIS
```

### Why This Matters

- **Singleton Consistency:** Ensures we are all using the exact same configuration instance.
- **Performance:** Avoids re-parsing environment variables.
- **Testing:** Makes it easier to mock the single `settings` object.

---

## 12. Supabase Project ID Truth

### The Pattern (MANDATORY)

**The ONLY valid Supabase Project ID is:** `ddfldwzhdhhzhxywqnyz`

**❌ Incorrect (Deprecated/Legacy):**
- `ylweoikbvbzgmhvnyakx` (Old project, will fail permissions)

### Why This Matters

- **MCP Tooling:** The Supabase MCP server requires the correct Project ID to execute SQL.
- **Permissions:** The old project ID has different RLS policies and will cause "Permission Denied" errors.
- **Hardcoded Check:** If you see the old ID in code, **fix it immediately**.

---

## 13. API Router Prefixing

### The Pattern (MANDATORY)

**Routers must define their FULL prefix (including `/api/v3`).**

**✅ Correct (`src/routers/my_router.py`):**
```python
router = APIRouter(
    prefix="/api/v3/my-resource",  # Full path defined here
    tags=["My Resource"]
)
```

**✅ Correct (`src/main.py`):**
```python
app.include_router(my_router)  # No prefix added here
```

**❌ Incorrect:**
```python
# Router
router = APIRouter(prefix="/my-resource")

# Main
app.include_router(my_router, prefix="/api/v3") # DON'T SPLIT THE PATH
```

### Why This Matters

- **Searchability:** You can grep for `/api/v3/my-resource` and find the definition immediately.
- **Consistency:** Prevents "double prefixing" or "missing prefix" bugs.
- **Refactoring:** Moving a router doesn't require changing `main.py`.

---

## 14. SQLAlchemy Enum Columns

### The Pattern (MANDATORY)

**Enum columns must use `native_enum=True` and `values_callable`.**

**✅ Correct:**
```python
status = Column(
    Enum(
        MyEnum,
        name="my_enum_type",
        native_enum=True,
        values_callable=lambda x: [e.value for e in x]
    ),
    nullable=False
)
```

### Why This Matters

- **Migration Safety:** Prevents Alembic from generating incorrect migration scripts.
- **Type Safety:** Ensures PostgreSQL treats the column as a true ENUM type.
- **The "Train Wreck":** We had a production incident caused by missing these parameters. Do not remove them.

---

## 15. No Placeholder Data

### The Pattern (MANDATORY)

**NEVER commit placeholder data (e.g., "placeholder@example.com").**

**✅ Correct:**
```python
if not extracted_email:
    raise ValueError("No email found - cannot create contact")
```

**❌ Incorrect:**
```python
email = "placeholder@example.com" # NEVER DO THIS
```

### Why This Matters

- **Data Pollution:** We have thousands of fake records in production because of this.
- **False Confidence:** The system "works" but produces garbage.
- **Business Value:** A contact with a fake email is worth $0.

---

## 16. Legacy Deprecation

### The Pattern (MANDATORY)

**When introducing a new system (System B), you MUST explicitly disable the old system (System A).**

**✅ Correct:**
1.  Deploy System B.
2.  **Immediately** delete/disable System A's scheduler/trigger.
3.  Verify only System B is running.

**❌ Incorrect:**
- Leaving System A running "just in case".
- Result: Race conditions, duplicate processing, data corruption.

### Why This Matters

- **The "Honeybee" Incident:** We had two sitemap processors running simultaneously, causing a race condition that took days to debug.
- **One Truth:** There can be only one active processor for a given workflow.

---

## 17. SQLAlchemy Enum .value

### The Pattern (MANDATORY)

**ALWAYS use `.value` when comparing Enums in SQLAlchemy queries.**

**✅ Correct:**
```python
# Filter by value
query = select(Contact).where(Contact.status == ContactStatus.New.value)

# Assign value
contact.status = ContactStatus.Active.value
```

**❌ Incorrect:**
```python
# SQLAlchemy tries to compare Enum object to String column -> FAILS
query = select(Contact).where(Contact.status == ContactStatus.New)
```

### Why This Matters

- **PostgreSQL Error:** `operator does not exist: enum_type = customenumtype`.
- **Recurring Bug:** This has broken production multiple times.
- **Simple Rule:** Database columns are strings (or native enums), Python Enums are objects. Compare apples to apples.

---

## 18. Pydantic ConfigDict

### The Pattern (MANDATORY)

**All Pydantic models returned from ORM objects must have `model_config`.**

**✅ Correct:**
```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
```

**❌ Incorrect:**
```python
class UserResponse(BaseModel):
    # Missing config -> will fail when parsing ORM object
    id: UUID
```

### Why This Matters

- **Serialization:** Without `from_attributes=True` (formerly `orm_mode`), Pydantic cannot read data from SQLAlchemy objects.
- **Runtime Errors:** Endpoints will crash with `pydantic.error_wrappers.ValidationError`.

---

## 19. Stop Sign: Ghost Files

### The Pattern (MANDATORY)

**If a tool reports a critical file (e.g., `.env`) is missing, STOP.**

**✅ Correct:**
1.  Tool says: "File .env not found."
2.  You say: "STOP. I see this file in the file list. Requesting visual confirmation."

**❌ Incorrect:**
- "Oh, it's missing? I'll create a new one." -> **DATA LOSS**

### Why This Matters

- **Tool Hallucinations:** AI tools sometimes fail to see files that exist.
- **Data Safety:** Overwriting `.env` or `docker-compose.yml` can destroy local configuration and secrets.

---

## 20. Six-Tier Validation

### The Pattern (MANDATORY)

**"It works" is not a valid status. You must prove it.**

**The 6 Tiers of Truth:**
1.  **Startup:** Does `docker compose up` succeed without errors?
2.  **Imports:** Can you run `python -c "from src... import X"`?
3.  **DB Connection:** Can the app connect to the DB?
4.  **Records:** Can you create/read a record?
5.  **Service:** Does the business logic execute?
6.  **API:** Does the endpoint return 200 OK?

### Why This Matters

- **Compliance Theater:** AI often claims things work without checking.
- **Integration Gaps:** Unit tests pass, but the app crashes on startup.

---

---

## 21. Database Connection Holding

### The Pattern (MANDATORY)

**NEVER hold a database connection open during a slow external API call.**

**✅ Correct:**
```python
# Phase 1: Fetch data (Quick)
async with get_db_session() as session:
    items = await get_items(session)

# Phase 2: External API (Slow) - NO DB CONNECTION
results = []
for item in items:
    result = await external_api.process(item)
    results.append(result)

# Phase 3: Save results (Quick)
async with get_db_session() as session:
    await save_results(session, results)
```

**❌ Incorrect:**
```python
async with get_db_session() as session:
    items = await get_items(session)
    # HOLDING CONNECTION for 30 seconds...
    for item in items:
        await external_api.process(item) # TIMEOUT!
```

### Why This Matters

- **Connection Starvation:** If 10 threads hold connections for 30 seconds, the pool runs out.
- **Timeouts:** Supavisor/PgBouncer will kill the connection.
- **The "Sibi" Incident:** This pattern caused a complete outage of WF4.

---

## 22. Double Transaction Management

### The Pattern (MANDATORY)

**NEVER manually commit/rollback inside a dependency-injected session.**

**✅ Correct:**
```python
# Router or Context Manager handles the transaction
async def my_service(session: AsyncSession):
    session.add(obj)
    await session.flush() # Just flush, don't commit
```

**❌ Incorrect:**
```python
async def my_service(session: AsyncSession):
    session.add(obj)
    await session.commit() # VIOLATION!
```

### Why This Matters

- **Idle in Transaction:** Manual commits inside a context manager leave the connection in an undefined state.
- **Locking:** This causes "RowShareLock" accumulation, blocking all updates.
- **The "Double Commit" Incident:** We had to kill production connections to fix this.

---

---

## 23. Internal Token Infrastructure

### The Pattern (MANDATORY)

**The internal token logic in `src/auth/jwt_auth.py` is CRITICAL INFRASTRUCTURE.**

**✅ Correct:**
- Leave the internal token check alone.
- It allows schedulers and background services to authenticate.

**❌ Incorrect:**
- "Fixing" security by blocking the internal token.
- Result: All background jobs fail.

### Why This Matters

- **The "Security Fix" Outage:** AI partners repeatedly "fix" this, causing production outages.
- **Scheduler Auth:** Schedulers run without a user context. They NEED this token.

---

## 24. No Inline Schemas

### The Pattern (MANDATORY)

**Schemas must be defined in `src/schemas/`. NEVER define Pydantic models inside a router.**

**✅ Correct:**
```python
from src.schemas.my_schema import MyRequest
```

**❌ Incorrect:**
```python
@router.post("/item")
async def create_item(item: Item):
    class Item(BaseModel): # VIOLATION!
        name: str
```

### Why This Matters

- **Circular Dependencies:** Inline schemas cannot be reused or imported.
- **Refactoring Nightmares:** Moving code becomes impossible.
- **Security Audits:** We cannot audit schemas if they are hidden inside functions.

---

## 25. No O(n²) Operations on Large Content

### The Pattern (MANDATORY)

**NEVER run expensive operations (especially regex) inside a loop over large content.**

**❌ Incorrect (The "OOM Killer"):**
```python
# DANGEROUS: O(n²) complexity
for url in urls:  # Loop 10,000 times
    # Searching the ENTIRE content (1MB+) for EACH URL
    match = re.search(f"<loc>{url}</loc>.*?<lastmod>(.*?)</lastmod>", content)
```

**✅ Correct:**
```python
# SAFE: O(n) complexity
# Extract all URLs in one pass
urls = re.findall(r"<loc>(.*?)</loc>", content)

# Check metadata presence globally, not per-URL
has_lastmod = "<lastmod>" in content
```

### Why This Matters

- **Complexity:** O(N * M) where N is number of items and M is content size.
- **Memory:** A 1MB sitemap with 10k URLs can consume GBs of RAM, causing container OOM kills (Exit Code 137).
- **The Incident:** 2025-11-21 Production Crash Loop lasted 6 hours due to this pattern in `sitemap_analyzer.py`.

### The Solution

1. **Parse Once:** Use an XML parser (lxml, xml.etree) to traverse the tree once.
2. **Stream:** For very large files, use streaming parsers (`iterparse`).
3. **Simplify:** If you must use regex, do it once on the whole file, not inside a loop.

---

## 26. No Unbounded Database Queries

### The Pattern (MANDATORY)

**ALWAYS enforce a hard limit on database queries. NEVER fetch "all" records.**

**❌ Incorrect:**
```python
# DANGEROUS: Could return 1 million rows
items = await session.execute(select(Item).where(Item.status == 'pending'))
```

**✅ Correct:**
```python
# SAFE: Hard limit enforced
items = await session.execute(
    select(Item)
    .where(Item.status == 'pending')
    .limit(100)
)
```

### Why This Matters

- **Memory Exhaustion:** Loading 100k+ rows into memory crashes the application.
- **Connection Timeout:** Large result sets can exceed Supavisor's connection timeout.
- **Performance:** Even if it doesn't crash, it's slow and wasteful.

### When To Use Pagination

For user-facing lists, use offset/limit pagination:
```python
page_size = 50
offset = (page_number - 1) * page_size

items = await session.execute(
    select(Item)
    .where(Item.status == 'pending')
    .limit(page_size)
    .offset(offset)
)
```

---

## 27. Tenant Context for RLS

### The Pattern (MANDATORY)

**ALWAYS use the centralized `with_tenant_context()` manager for RLS-protected queries.**

**✅ Correct:**
```python
from src.db.tenant_context import with_tenant_context
from fastapi import HTTPException

# In a router with get_db_session (auto-commit):
tenant_id = current_user.get("tenant_id")
if not tenant_id:
    raise HTTPException(status_code=401, detail="No tenant_id in token")

async with with_tenant_context(session, tenant_id):
    # All queries here respect RLS for this tenant
    result = await session.execute(select(MyModel))
    # RESET ROLE is GUARANTEED on exit (even on exception)
```

**❌ Incorrect (Inline SET ROLE):**
```python
# DON'T DO THIS - connection pool pollution!
await session.execute(text("SET ROLE app_worker;"))
await session.execute(
    text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
    {"tenant_id": str(tenant_id)},
)
# ... queries ...
# MISSING RESET ROLE! Connection returns to pool with stale tenant context
```

### Why This Matters

- **Connection Pool Pollution:** Without `RESET ROLE`, the connection returns to the pool still as `app_worker` with a stale `tenant_id`. The next request may see wrong tenant's data.
- **Guaranteed Cleanup:** The context manager's `finally` block ensures `RESET ROLE` is always called, even if an exception occurs.
- **Code Reduction:** Replaces 4-6 lines of inline code with 2 lines (import + `async with`).
- **Auditability:** Easy to grep for `with_tenant_context` to find all tenant-scoped code.

### Scheduler Exception Pattern

When a scheduler needs to discover `tenant_id` from the database (chicken-and-egg problem):

```python
async with session.begin():
    # Step 1: Temporarily bypass RLS to fetch record
    await session.execute(text("SET ROLE postgres;"))
    try:
        stmt = select(Place).where(Place.id == item_id)
        result = await session.execute(stmt)
        place = result.scalar_one_or_none()
    finally:
        await session.execute(text("RESET ROLE;"))  # IMMEDIATELY reset

    if not place:
        raise ValueError(f"Place {item_id} not found")

    # Step 2: Now use proper tenant context
    if not place.tenant_id:
        raise ValueError(f"Place {item_id} has no tenant_id")
    tenant_id = str(place.tenant_id)
    async with with_tenant_context(session, tenant_id):
        # All RLS-protected operations here
        await process_place(place, session)
```

### Reference

- **Implementation:** `src/db/tenant_context.py`
- **ADR:** [ADR-007-RLS-TENANT-CONTEXT-PATTERN.md](../00_The_Law/ADR-007-RLS-TENANT-CONTEXT-PATTERN.md)

---

## 28. Object Load Before RLS Context

### The Pattern (MANDATORY)

**Objects loaded BEFORE `with_tenant_context()` become STALE after context is set.**

**❌ Incorrect (StaleDataError):**
```python
# Load object BEFORE tenant context
sitemap_file = await session.get(SitemapFile, sitemap_file_id)
tenant_id = str(sitemap_file.tenant_id)

async with with_tenant_context(session, tenant_id):
    # sitemap_file is now STALE - session role changed!
    sitemap_file.status = "Complete"  # StaleDataError!
    await session.commit()
```

**✅ Correct:**
```python
# Step 1: Load object to get tenant_id (read-only is OK)
sitemap_file = await session.get(SitemapFile, sitemap_file_id)
tenant_id = str(sitemap_file.tenant_id)
sitemap_file_id = sitemap_file.id  # Capture ID

async with with_tenant_context(session, tenant_id):
    # Step 2: RE-LOAD inside tenant context
    fresh_sitemap_file = await session.get(SitemapFile, sitemap_file_id)

    # Step 3: Operate on FRESH object
    fresh_sitemap_file.status = "Complete"
    await session.commit()
```

### Why This Matters

- **The WF5 Incident (2025-12-11):** `SitemapFile with id {id} not found during processing` - object was loaded before RLS context switch.
- **Rule:** Always re-fetch objects after calling `with_tenant_context()`.

---

## 29. Implicit Context in Background Tasks

### The Pattern (MANDATORY)

**Background tasks have NO implicit context. Pass everything explicitly.**

**❌ Incorrect:**
```python
asyncio.create_task(
    process_domain_with_own_session(
        job_id=job_id,
        domain=domain.domain,
        # user_id missing! Will be None.
        # tenant_id missing! Will be None.
    )
)
```

**✅ Correct:**
```python
asyncio.create_task(
    process_domain_with_own_session(
        job_id=job_id,
        domain=domain.domain,
        user_id=str(domain.user_id) if domain.user_id else None,
        tenant_id=str(domain.tenant_id) if domain.tenant_id else None,
    )
)
```

### Why This Matters

- **The WF4 Incident (2025-12-11):** `ERROR - user_id is required for background processing. Got: None`
- **Rule:** When spawning background tasks, explicitly pass ALL required context.

---

## Appendix: RLS Migration Incident History

These incidents occurred during the Dec 9-11, 2025 multi-tenancy migration:

| Date | Issue | Root Cause | Fix |
|------|-------|------------|-----|
| 2025-12-10 | Deep Scan: "Place {id} not found" | RLS blocked query before tenant context set | Chicken-and-Egg pattern |
| 2025-12-10 | Domain Extraction: "LocalBusiness {id} not found" | Same as above | Chicken-and-Egg pattern |
| 2025-12-11 | Sitemap Import: StaleDataError | Object loaded before `with_tenant_context()` | Re-load inside context |
| 2025-12-11 | WF4: "user_id required, got None" | Background task missing explicit context | Pass all context explicitly |

**Lesson:** Every scheduler that starts with an ID lookup needs the Chicken-and-Egg pattern. No exceptions.

---

**Status:** ✅ Critical patterns documented (29 patterns)
