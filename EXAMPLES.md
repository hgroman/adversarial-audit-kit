# Real Audit Example: WO-WF10-PHASE3.4-COMPANY-LAUNCHPAD

A complete walkthrough of an actual adversarial audit from 2026-01-02.

---

## The Work Order

**Name**: WO-WF10-PHASE3.4-COMPANY-LAUNCHPAD
**Purpose**: Add AI-powered company analysis to the Signal Platform
**Scope**: New router, service, database table, AI integration

The work order proposed:
- A new `companies` table with RLS policies
- A company router at `/api/v3/companies`
- An AI chat service using LangChain + OpenAI
- Integration with existing Signal Platform (WF10)

---

## The Audit Process

### Phase 1: Setup

```bash
# Orchestrator created the audit directory
mkdir -p 05_Active_Work/WO-WF10-PHASE3.4-COMPANY-LAUNCHPAD-Audit/

# Moved work order into it
mv WO-WF10-PHASE3.4-COMPANY-LAUNCHPAD.md WO-WF10-PHASE3.4-COMPANY-LAUNCHPAD-Audit/

# Initialized status tracking
# Created _STATUS.yaml with all 6 auditors set to "pending"
```

### Phase 2: Parallel Auditor Spawn

All 6 auditors launched simultaneously:

| Auditor | Status | Duration |
|---------|--------|----------|
| Architect | Complete | 8 min |
| DevOps | Complete | 6 min |
| Data Assassin | Complete | 7 min |
| Kraken | Complete | 9 min |
| Operator | Complete | 5 min |
| Test Sentinel | Complete | 12 min |

### Phase 3: Findings Aggregation

```markdown
| Auditor | Findings | BLOCKERS | WARNINGS | ADVISORY |
|---------|----------|----------|----------|----------|
| Architect | 9 | 3 | 4 | 2 |
| DevOps | 9 | 6 | 0 | 3 |
| Data Assassin | 8 | 1 | 1 | 2 |
| Kraken | 7 | 5 | 2 | 0 |
| Operator | 7 | 2 | 3 | 2 |
| Test Sentinel | 9 | 4 | 4 | 2 |
| **TOTAL** | **46** | **21** | **14** | **11** |
```

### Phase 4: Verdict

```
DEPLOYMENT RECOMMENDATION: BLOCKED

This work order cannot proceed to implementation in its current state.
```

---

## Sample Findings by Auditor

### Architect Findings

#### ARCH-001: Wrong Import Path (BLOCKER)

**Location**: Work order Section 5.2
**Pattern Found**: `from src.db.rls import with_tenant_context`
**Registry Check**: No such file exists in codebase
**Law Reference**: N/A - file doesn't exist
**Verdict**: VIOLATION

**Evidence**:
```bash
$ ls src/db/rls*
ls: src/db/rls*: No such file or directory

$ ls src/db/ | grep -i rls
# No output
```

**Remediation**:
```python
# Wrong
from src.db.rls import with_tenant_context

# Correct
from src.db.tenant_context import with_tenant_context
```

---

#### ARCH-002: Missing Infrastructure (BLOCKER)

**Location**: Work order Section 4.1
**Pattern Found**: References `companies` table with FK relationships
**Registry Check**: No companies table in database
**Law Reference**: TRIGGER-PROTECTION-LAW.md - Schema Change Protocol
**Verdict**: VIOLATION - work order assumes non-existent infrastructure

**Evidence**:
```sql
-- Query against production
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'companies';
-- 0 rows
```

**Impact**: All foreign key references fail. Migration will error.

**Remediation**: Add Phase 3.4.0 to create companies table infrastructure before Phase 3.4.1.

---

### DevOps Findings

#### DEVOPS-003: Missing Dependency (BLOCKER)

**Location**: Work order Section 6.1
**Pattern Found**: Uses `from langchain.llms import ChatOpenAI`
**Registry Check**: requirements.txt has no langchain
**Law Reference**: Dockerfile build protocol
**Verdict**: VIOLATION

**Evidence**:
```bash
$ grep -i langchain requirements.txt
# No output

$ grep -i openai requirements.txt
# No output
```

**Impact**: ModuleNotFoundError on any import of the AI service.

**Remediation**:
```txt
# Add to requirements.txt
langchain>=0.1.0
langchain-openai>=0.0.5
openai>=1.0.0
```

---

#### DEVOPS-006: Router Not Registered (BLOCKER)

**Location**: Work order Section 5.1
**Pattern Found**: Creates `company_router.py` but no registration in main.py
**Registry Check**: main.py router includes
**Law Reference**: FastAPI router registration protocol
**Verdict**: VIOLATION

**Evidence**:
```python
# main.py shows no include for company_router
# All endpoints would return 404
```

**Remediation**:
```python
# Add to main.py
from src.routers.wf10_company_router import router as company_router
app.include_router(company_router)
```

---

### Data Assassin Findings

#### SEC-002: Role Leak in Production (BLOCKER)

**Location**: `src/routers/wf10_signal_router.py:109-120`
**Pattern Found**: `SET ROLE` without matching `RESET ROLE`
**Registry Check**: SESSION-AND-TENANT-LAW.md Rule 4
**Law Reference**: "SET ROLE must always have RESET ROLE in finally block"
**Verdict**: VIOLATION - **IN EXISTING PRODUCTION CODE**

**Evidence**:
```python
# Lines 109-120 (BEFORE fix)
find_stmt = text("SELECT tenant_id FROM public.action_signals WHERE id = :id")
res = await session.execute(find_stmt, {"id": signal_id})
# NO SET ROLE, NO RESET ROLE
```

**Impact**: Role state undefined after this endpoint. Subsequent queries may fail or bypass RLS.

**Remediation**:
```python
await session.execute(text("SET ROLE postgres"))
try:
    find_stmt = text("SELECT tenant_id FROM public.action_signals WHERE id = :id")
    res = await session.execute(find_stmt, {"id": signal_id})
finally:
    await session.execute(text("RESET ROLE"))
```

**Note**: This was in existing production code, not the work order. Fixed same day.

---

### Kraken Findings

#### KRAKEN-001: Blocking Initialization (BLOCKER)

**Location**: Work order Section 6.2
**Pattern Found**: `ChatOpenAI()` called in class `__init__`
**Registry Check**: Known blocking I/O pattern
**Law Reference**: L4_Service_Guardian - Lazy Initialization
**Verdict**: VIOLATION

**Evidence**:
```python
class AIChatService:
    def __init__(self):
        self.llm = ChatOpenAI(...)  # BLOCKS event loop
```

**Impact**: At 10+ concurrent requests, event loop blocked. 500 errors for all users.

**Remediation**:
```python
class AIChatService:
    def __init__(self):
        self._llm = None  # Lazy

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(...)
        return self._llm
```

---

#### KRAKEN-003: Connection Held During AI Call (BLOCKER)

**Location**: Work order Section 6.3
**Pattern Found**: DB session held open while awaiting OpenAI API
**Registry Check**: Pool exhaustion pattern
**Law Reference**: ADR-001-Supavisor-Requirements
**Verdict**: VIOLATION

**Evidence**:
```python
async def chat(self, session, user_id, message):
    context = await session.execute(...)  # Hold connection
    response = await self.llm.ainvoke(...)  # 2-10 second AI call
    await session.execute(...)  # Still holding
```

**Impact**: 5 concurrent chat requests exhaust connection pool. All other endpoints blocked.

**Remediation**:
```python
async def chat(self, session, user_id, message):
    # Fetch context, release connection
    context = await session.execute(...)
    await session.commit()  # Release

    # AI call with no connection held
    response = await self.llm.ainvoke(...)

    # Re-acquire for save
    await session.execute(...)
```

---

### Operator Findings

#### OPS-001: No Tenant Context in Logs (BLOCKER)

**Location**: Work order Section 6
**Pattern Found**: `logger.info(f"Chat request from user {user_id}")`
**Registry Check**: OBSERVABILITY-REQUIREMENTS.md
**Law Reference**: "All logs must include tenant_id for isolation"
**Verdict**: VIOLATION

**Evidence**: No log statements include `tenant_id`. At 2 AM with 50 tenants, which tenant has the issue?

**Remediation**:
```python
logger.info(
    "Chat request received",
    extra={"tenant_id": tenant_id, "user_id": user_id}
)
```

---

### Test Sentinel Findings

#### TEST-001: Insufficient Test Coverage (BLOCKER)

**Location**: Work order Section 8
**Pattern Found**: 3 tests provided
**Registry Check**: WO-INTEGRATION-TEST-STANDARDIZATION.md
**Law Reference**: "WF10 requires 56+ tests across 6 categories"
**Verdict**: VIOLATION

**Evidence**:
| Category | Required | Provided |
|----------|----------|----------|
| Unit tests | 20+ | 2 |
| Integration tests | 15+ | 1 |
| Multi-tenant tests | 10+ | 0 |
| Error case tests | 5+ | 0 |
| Concurrency tests | 3+ | 0 |
| E2E tests | 3+ | 0 |
| **TOTAL** | **56+** | **3** |

**Remediation**: Expand test section to include all 6 categories with specific test cases.

---

## The Fix

After receiving the VERDICT, the work order was revised:

### Added Phase 3.4.0 (Prerequisites)
- Companies table schema with RLS policies
- SQLAlchemy model: `src/models/wf10_company.py`
- CRUD service: `src/services/wf10_company_service.py`

### Fixed All Import Paths
```python
# Before
from src.db.rls import with_tenant_context

# After
from src.db.tenant_context import with_tenant_context
```

### Fixed File Naming
```
# Before
company_router.py

# After
wf10_company_router.py
```

### Replaced Raw SQL with ORM
```python
# Before
db.fetch_all("SELECT * FROM companies WHERE tenant_id = $1", tenant_id)

# After
stmt = select(Company).where(Company.tenant_id == tenant_id)
result = await session.execute(stmt)
```

### Added Lazy Initialization
```python
class AIChatService:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(...)
        return self._llm
```

### Added Rate Limiting
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(...):
```

### Added Structured Logging
```python
logger.info(
    "Company chat request",
    extra={
        "tenant_id": tenant_id,
        "user_id": user_id,
        "company_id": company_id
    }
)
```

### Expanded Test Requirements
Full 56+ test specification across 6 categories.

---

## Production Bug Fixed

The audit also discovered SEC-002 in existing production code. This was fixed and committed the same day:

```bash
git commit -m "fix(security): SEC-002 - Add RESET ROLE to complete_signal endpoint"
git push origin main
```

---

## Lessons Learned

1. **Prerequisite infrastructure matters** - The work order assumed a table existed. It didn't.

2. **Import paths must be verified** - `src.db.rls` doesn't exist. Copy-paste errors propagate.

3. **Audits find production bugs** - SEC-002 wasn't in the work order, but the Data Assassin found it anyway.

4. **21 blockers sounds like a lot** - But fixing them before implementation saved weeks of debugging.

5. **The registry prevents false positives** - Without WORKFLOW-RLS-REGISTRY.yaml, half the findings would have been wrong.

---

## Final Outcome

| Metric | Before Audit | After Audit |
|--------|--------------|-------------|
| Work order status | Ready to implement | Revised, ready to re-audit |
| Production bugs | 1 unknown | 0 (SEC-002 fixed) |
| Missing infrastructure | Undefined | Phase 3.4.0 added |
| Test coverage | 3 tests | 56+ test spec |
| Time to discover issues | Would have been days/weeks | 15 minutes |

---

*This audit prevented an estimated 2-3 weeks of debugging and one production security incident.*
