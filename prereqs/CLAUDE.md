# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ScraperSky Backend is a **multi-tenant FastAPI service** for large-scale web metadata extraction. It runs exclusively in Docker, uses Supabase for PostgreSQL with Row-Level Security (RLS), and processes data through 9 workflow pipelines (WF1-WF9).

**Documentation**: Architecture documentation lives in `00_Current_Architecture/` organized into:
- **00_The_Law/** - ADRs and binding architectural rules
- **01_System_References/** - System overview, data schemas, workflow diagrams
- **02_Workflow_Truth/** - Deep-dive guides for each workflow (WF1-WF9)
- **03_Builder_Kit/** - Layer-by-layer pattern & anti-pattern guides
- **04_Active_Work/** - Current work orders and technical debt tracking

## Development Commands

### Docker (Mandatory - "If it doesn't build in Docker, it doesn't exist")

```bash
# Start with environment-specific compose file
docker compose -f docker-compose.dev.yml up --build      # Development (bypass token enabled)
docker compose -f docker-compose.staging.yml up --build  # Staging
docker compose -f docker-compose.prod.yml up --build     # Production

# Check logs
docker compose logs -f scrapersky

# Shutdown
docker compose down

# Full verification protocol (required before deploying)
docker compose -f docker-compose.dev.yml up --build -d
sleep 15
docker compose -f docker-compose.dev.yml logs --tail=50 | grep -E "(ERROR|ModuleNotFoundError|Traceback|Application startup complete)"
curl -f http://localhost:8000/health && echo "✅ PASSED" || echo "❌ FAILED"
docker compose -f docker-compose.dev.yml down
```

### Testing

```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_architecture_enforcement.py -v

# Run with markers
pytest -m unit          # Fast, mock-based unit tests
pytest -m integration   # Real database/Supabase tests
pytest -m architecture  # Pattern enforcement tests
pytest -m rls           # Security-critical RLS tests
pytest -m slow          # Long-running tests

# Run single test function
pytest tests/test_file.py::test_function_name -v
```

**Note**: Tests use `asyncio_mode = auto` - async fixtures are handled automatically.

### Linting & Formatting

```bash
# Check and format
ruff check .
ruff format .

# Pre-commit hooks (minimal - just whitespace/newlines)
pre-commit run --all-files
```

### Architecture Enforcement

```bash
# Run unified architecture audit (checks ALL violations)
python tools/architecture_audit.py

# Pre-commit hooks will BLOCK commits that violate:
# - Tenant ID fallbacks (DEFAULT_TENANT_ID, hardcoded UUIDs)
# - Session management patterns (wrong imports, deprecated patterns)
# - RLS violations (SET ROLE without RESET ROLE)
# - Inline async functions in routers
```

## High-Level Architecture

### The 9 Workflow System (WF1-WF9)

**All code uses workflow prefixing** (enforced by pre-commit hooks). Files must start with `wfX_` unless explicitly excepted.

| WF | Name | Purpose | Key Files |
|----|------|---------|-----------|
| WF1 | Places Search (The Scout) | Google Maps API discovery | `src/routers/wf1_place_staging_router.py`, `src/models/wf1_place_staging.py` |
| WF2 | Deep Scan (The Analyst) | Place details enrichment | `src/services/background/wf2_deep_scan_scheduler.py` |
| WF3 | Local Business (The Navigator) | Domain extraction from places | `src/models/wf3_local_business.py`, `src/routers/wf3_local_business_router.py` |
| WF4 | Domain Curation (The Surveyor) | Sitemap discovery | `src/models/wf4_domain.py`, `src/routers/wf4_domain_router.py` |
| WF5 | Sitemap Curation (The Flight Planner) | Page discovery from sitemaps | `src/models/wf5_sitemap_file.py`, `src/services/sitemap/wf5_processing_service.py` |
| WF6 | **DOES NOT EXIST** | Merged into WF5/WF7 - never reference | N/A |
| WF7 | Page Curation (The Extractor) | Contact extraction from pages | `src/models/wf7_page.py`, `src/services/page_scraper/wf7_processing_service.py` |
| WF8 | Contact Curation (The Connector) | CRM sync (Brevo, HubSpot, n8n) | `src/models/wf8_contact.py`, `src/routers/wf8_contacts_router.py` |
| WF9 | Semantic Copilot (The Librarian) | AI knowledge search via vector DB | `src/routers/wf9_copilot_router.py` |

**Complete workflow details**: See `00_Current_Architecture/02_Workflow_Truth/MODULE-CARD-WF*.md` for each workflow's deep-dive guide.

**Visual data flow**: See `00_Current_Architecture/01_System_References/SYSTEM_MAP.md` for Mermaid diagrams showing how data flows WF1→WF2→WF3→...→WF8.

### Layer System

The codebase is organized in strict layers. **Never mix layers** (enforced by audit tools):

1. **Layer 1 - Models** (`src/models/`) - SQLAlchemy ORM models, all enums in `src/models/enums.py`
2. **Layer 2 - Schemas** (`src/schemas/`) - Pydantic models for request/response validation
3. **Layer 3 - Routers** (`src/routers/`) - FastAPI route handlers, use dependency injection for auth/sessions
4. **Layer 4 - Services** (`src/services/`) - Business logic, background tasks, schedulers
5. **Layer 5 - Config** (`src/config/`) - Settings, logging, runtime configuration
6. **Layer 6 - Static** (`static/`) - Frontend HTML/JS files
7. **Layer 7 - Tests** (`tests/`) - Unit, integration, and E2E tests

**Pattern guides**: Each layer has a detailed pattern/anti-pattern guide in `00_Current_Architecture/03_Builder_Kit/LX_*_Guardian_*.md`

### Iron Mandates (Non-Negotiable)

1. **ORM ONLY**: Use SQLAlchemy AsyncSession for all database writes. NO raw SQL except for WF9 (Vector Search).
2. **NO LOCALHOST HTTP**: Services must NEVER call each other via `http://localhost:8000`. Use direct Python imports.
3. **DOCKER IS TRUTH**: If it doesn't build and run in Docker, it doesn't exist.
4. **V3 ONLY**: All routers use `/api/v3/`. There is no V1 or V2.

### Critical Architectural Rules (READ BEFORE CODING)

These rules are **enforced by pre-commit hooks** - violations will block commits.

**Complete reference**: `00_Current_Architecture/00_The_Law/SESSION-AND-TENANT-LAW.md`

#### 1. Database Session Management

**Router Endpoints** (auto-commit):
```python
from src.db.session import get_db_session

@router.get("/example")
async def example(session: AsyncSession = Depends(get_db_session)):
    # Session auto-commits on success, auto-rollbacks on error
    # NEVER use session.begin() here - it's already handled
```

**Background Tasks** (manual commit):
```python
from src.db.session import get_session_context

async with get_session_context() as session:
    # Manual commit/rollback required
    await session.commit()
```

**FORBIDDEN**:
- ❌ `from src.session.async_session import get_session` in routers
- ❌ `get_background_session` (deprecated)
- ❌ `session.begin()` when using `get_db_session` (already provides transaction)

**Reference**: `00_Current_Architecture/00_The_Law/ADR-004-Transaction-Boundaries.md`

#### 2. Tenant Context & RLS

**Always use the centralized tenant context manager**:
```python
from src.db.tenant_context import with_tenant_context

async with with_tenant_context(session, current_user["tenant_id"]):
    # All queries here respect RLS for this tenant
    result = await session.execute(select(Domain))
```

**FORBIDDEN**:
- ❌ `DEFAULT_TENANT_ID` fallbacks anywhere except definition files
- ❌ Hardcoded UUIDs: `550e8400-e29b-41d4-a716-446655440000`
- ❌ Inline `SET ROLE app_worker` without `RESET ROLE` in finally block
- ❌ Direct `set_config('app.current_tenant_id', ...)` outside `tenant_context.py`

**Exception**: Schedulers use `SET ROLE postgres` for cross-tenant queue discovery (they scan all tenants' queued items before setting tenant context).

**References**:
- `00_Current_Architecture/00_The_Law/ADR-007-RLS-TENANT-CONTEXT-PATTERN.md`
- `00_Current_Architecture/00_The_Law/ADR-009-DEFAULT-TENANT-ID-REMOVAL.md`

#### 3. Enum Management

**All enums MUST live in** `src/models/enums.py`. No inline enum definitions.

```python
from src.models.enums import DomainStatusEnum, ContactCurationStatus

# ❌ WRONG - inline enum
class MyStatus(str, Enum):
    pending = "pending"

# ✅ RIGHT - import from centralized location
status = DomainStatusEnum.pending
```

**Reference**: `00_Current_Architecture/00_The_Law/ADR-005-ENUM-Catastrophe.md` (explains why this rule exists)

#### 4. Supavisor Connection Pooling

**MANDATORY**: All database connections MUST use Supavisor (port 6543, not 5432) with these parameters:

```python
# In src/db/session.py - already configured correctly
connect_args = {
    "statement_cache_size": 0,              # CRITICAL for Supavisor
    "prepared_statement_cache_size": 0,     # CRITICAL for Supavisor
    "server_settings": {
        "search_path": "public",
        "application_name": "scrapersky_backend",
    },
}

execution_options = {
    "isolation_level": "READ COMMITTED",
    "raw_sql": True,        # REQUIRED for Supavisor
    "no_prepare": True,     # REQUIRED for Supavisor
}
```

**Database URL format**:
```
postgresql+asyncpg://postgres.{project_ref}:{password}@{host}:6543/postgres?statement_cache_size=0&prepared_statement_cache_size=0
```

**Reference**: `00_Current_Architecture/00_The_Law/ADR-001-Supavisor-Requirements.md`

#### 5. No Inline Async Functions in Routers

```python
# ❌ WRONG - inline function creates session management ambiguity
@router.post("/example")
async def example(session: AsyncSession = Depends(get_db_session)):
    async def helper():
        # Unclear which session this uses
        pass

# ✅ RIGHT - extract to service layer
from src.services.example_service import process_example

@router.post("/example")
async def example(session: AsyncSession = Depends(get_db_session)):
    return await process_example(session)
```

#### 6. The Dual-Status Pattern

When a user selects an item, you MUST update BOTH statuses:

```python
# ✅ CORRECT - triggers the system
item.curation_status = "Selected"
item.processing_status = "Queued"  # Scheduler picks this up

# ❌ WRONG - system ignores it forever
item.curation_status = "Selected"  # No processing_status = stuck
```

**Reference**: `00_Current_Architecture/01_System_References/DUAL_ADAPTERS.md`

### Database Schema Changes

**DO NOT create migration files**. We have direct Supabase access via MCP.

```python
# ✅ Execute SQL directly via Supabase MCP
# Note: project_id shown is the production project
mcp__supabase-mcp-server__execute_sql(
    project_id="ddfldwzhdhhzhxywqnyz",
    query="ALTER TABLE domains ADD COLUMN new_field TEXT;"
)
```

Use `mcp__supabase-mcp-server__list_projects` to discover available projects.

### File Naming Conventions

**Workflow Prefixing** (enforced):
- Models: `wfX_resource_name.py` (e.g., `wf4_domain.py`)
- Routers: `wfX_resource_router.py` (e.g., `wf5_sitemap_file_router.py`)
- Services: `wfX_service_name.py` (e.g., `wf7_processing_service.py`)
- Schemas: `wfX_resource_schemas.py` (e.g., `wf8_contact_schemas.py`)

**Exceptions** (allowed without `wfX_` prefix):
- Core infrastructure: `src/db/`, `src/config/`, `src/auth/`, `src/core/`
- Shared utilities: `src/common/`, `src/utils/`, `src/scraper/`
- Cross-workflow: `src/models/base.py`, `src/models/enums.py`, `src/models/tenant.py`

### Debug Tools

**Conditional loading based on environment**:

```bash
# Enable debug mode
export FASTAPI_DEBUG_MODE=true
docker compose up

# Debug endpoints (only available when FASTAPI_DEBUG_MODE=true)
curl http://localhost:8000/debug/routes
curl http://localhost:8000/debug/loaded-src-files
```

**Production** (default): Debug tools never load - zero overhead.

### Background Schedulers

All schedulers run via APScheduler in `src/scheduler_instance.py`, registered in `src/main.py` lifespan.

Environment variables control scheduling:
- `DOMAIN_SCHEDULER_INTERVAL_MINUTES` (default: 1)
- `DOMAIN_SCHEDULER_BATCH_SIZE` (default: 10)
- `SITEMAP_SCHEDULER_INTERVAL_MINUTES` (default: 1)
- `SITEMAP_SCHEDULER_BATCH_SIZE` (default: 20)

**Pattern**:
```python
# src/services/background/wfX_scheduler.py
from src.scheduler_instance import get_scheduler
from src.db.session import get_session_context

async def scheduler_task():
    async with get_session_context() as session:
        # Cross-tenant discovery - use postgres role
        await session.execute(text("SET ROLE postgres"))
        items = await session.execute(select(Model).where(...))

        for item in items:
            # Set tenant context for each item
            async with with_tenant_context(session, item.tenant_id):
                await process_item(session, item)

def setup_scheduler():
    scheduler = get_scheduler()
    scheduler.add_job(
        scheduler_task,
        "interval",
        minutes=int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "1")),
        id="unique_scheduler_id",
        replace_existing=True,
    )
```

### Authentication

JWT-based authentication at API gateway. **Never** handle JWT/tenant auth in database operations.

```python
from src.auth.jwt_auth import get_current_user

@router.get("/protected")
async def protected_endpoint(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    # current_user = {"user_id": "...", "tenant_id": "...", "email": "..."}
    async with with_tenant_context(session, current_user["tenant_id"]):
        # Query with RLS
        pass
```

### Vector Database & Semantic Search (WF9)

**DO**: Use the semantic query CLI for vector searches
```bash
python -m tools.vector.search.semantic_query "your query"
```

**DON'T**: Pass vector embeddings as string literals in SQL queries via MCP - this causes truncation.

## Common Pitfalls

1. **Import errors in Docker**: `docker compose build` only tests compilation, NOT runtime imports. Always run `docker compose up` to verify imports work.

2. **Connection pool exhaustion**: Must use Supavisor (port 6543) with `statement_cache_size=0` and `prepared_statement_cache_size=0`.

3. **RLS not filtering data**: Ensure you're using `with_tenant_context()` and the session has `SET ROLE app_worker` executed.

4. **Session reuse across async boundaries**: Each async context needs its own session. Don't pass sessions between different async functions unless you control the lifecycle.

5. **Enum duplication**: All enums in `src/models/enums.py`. Check there first before defining a new one.

6. **Git diff hanging**: If `git diff` hangs, configure: `git config --global core.pager cat`

## Project Context

- **Deployment**: Render.com (see `render.yaml`)
- **Database**: Supabase PostgreSQL with RLS
- **Python Version**: 3.11 (see `Dockerfile`)
- **Framework**: FastAPI 3.0.0
- **ORM**: SQLAlchemy 2.x (async)
- **Task Scheduling**: APScheduler
- **CORS**: Configured via `src/config/settings.py` - development allows all origins, production requires explicit configuration

## Documentation Structure

All architecture documentation lives in `00_Current_Architecture/`:

### 00_The_Law/ - Binding Rules
- **SESSION-AND-TENANT-LAW.md** - The canonical session management & RLS rulebook
- **AI_CHEAT_SHEET.md** - AI-optimized architecture summary
- **ADR-001 through ADR-010** - Architecture Decision Records explaining "why" behind each rule

### 01_System_References/ - Big Picture
- **SYSTEM_MAP.md** - Complete data flow diagrams (Mermaid), table relationships, file maps
- **DATA_SCHEMA.md** - Detailed database schema documentation
- **SCHEDULER_REFERENCE.md** - Background job patterns and configuration
- **DUAL_ADAPTERS.md** - The dual-status pattern (curation vs processing)
- **WORKFLOW-RLS-REGISTRY.yaml** - Which endpoints use RLS and how

### 02_Workflow_Truth/ - Deep Dives
- **MODULE-CARD-WF1** through **MODULE-CARD-WF9** - Complete guides for each workflow (WF6 doesn't exist)
- Covers: Places Scout, Deep Scan Analyst, Domain Navigator, Domain-to-Sitemap, Sitemap Scraper, Page Scraper, Contacts/CRM, AI Copilot

### 03_Builder_Kit/ - How to Build
- **L1_Model_Guardian** through **L7_Test_Guardian** - Layer-by-layer pattern guides
- **CRITICAL_PATTERNS.md** - Must-follow patterns
- **CRM-INTEGRATION-PLAYBOOK.md** - Adding new CRM integrations
- **NEW_WORKFLOW_CHECKLIST_BRIEF.md** - Steps to add a new workflow
- **COMPONENT_LIBRARY.md** - Reusable components
- **WF*_LOGIC_MAP.md** - Detailed logic maps for each workflow

### 04_Active_Work/ - Current State
- **TECHNICAL_DEBT_BACKLOG.md** - Known issues and planned fixes
- **CRUD_STANDARDIZATION_STATUS.md** - Migration status
- **RLS-ENDPOINT-REGISTRY.md** - RLS implementation tracking
- **WO-*.md** - Active work orders

## When in Doubt

1. **Quick answer**: Check `00_Current_Architecture/00_The_Law/AI_CHEAT_SHEET.md`
2. **Understand "why"**: Read the relevant ADR in `00_The_Law/`
3. **See patterns**: Look at `03_Builder_Kit/` for your layer
4. **See working examples**: Check `src/` code that follows the patterns
