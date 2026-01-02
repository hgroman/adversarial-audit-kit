```yaml
# Document Governance
doc_id: "L4_Service_Guardian_Pattern_AntiPattern_Companion.md"
doc_tier: "Tier 4 – Builder Kit (Derived)"
authority: "DERIVED"
truth_scope: "service pattern guidance only; cannot override Law/ADR/Registry"
defers_to:
  - "00_The_Law/SESSION-AND-TENANT-LAW.md"
  - "00_The_Law/ADR-003-Dual-Status-Workflow.md"
  - "00_The_Law/ADR-004-Transaction-Boundaries.md"
  - "00_The_Law/ADR-007-RLS-TENANT-CONTEXT-PATTERN.md"
  - "01_System_References/WORKFLOW-RLS-REGISTRY.yaml"
  - "01_System_References/SYSTEM_MAP.md"
code_truth_anchors:
  - "src/services/"
  - "src/common/curation_sdk/"
change_control:
  ai_may: ["propose_edits"]
  ai_may_not: ["apply_edits", "apply_code_changes"]
  human_required_for: ["all_changes"]
last_verified: "2025-12-19"
audit_status: "audited"
staleness_policy:
  review_after_days: 90
  warn_after_days: 180
ghost_pattern_risk: true
rls_migration_check:
  contains_tenant_id_contracts: true
  contains_set_role: false
  contains_with_tenant_context: true  # Services use with_tenant_context extensively
  note: "tenant_id IS REQUIRED for INSERT operations per The Law. See Pattern #7."
  verified_against:
    - "src/db/tenant_context.py"
    - "src/services/page_scraper/wf7_page_curation_service.py:141"
    - "src/services/sitemap/wf5_sitemap_import_service.py:76"
domain_primary_reference:
  dual_status: "CRITICAL_PATTERNS.md#dual-status"
  service_contracts: true
```

# L4 Service Guardian Pattern-AntiPattern Companion

## Instant Pattern Recognition & Violation Detection Guide

**Version:** 1.2 (Simple Scraper Pattern + WF7 Victory Update)
**Purpose:** Enable instant service pattern recognition and violation detection
**Cardinal Rule:** Services ACCEPT sessions, never create them!
**Constitutional Authority:** Universal Trigger Pattern & Dual-Status Update Pattern enforcement
**Usage:** Load ONLY this document for complete L4 service review authority
**Verification Requirement:** Pattern claims must be verified against actual codebase

**CRITICAL UPDATE (2025-09-14):** Added Dual Status Adapter Pattern enforcement following sitemap import service fix (commit 5c8c4ef)
**CRITICAL UPDATE (2025-09-19):** Fixed contact creation failure caused by SQLAlchemy enum model changes (commit 426650f)
**CRITICAL UPDATE (2025-09-20):** WF7 Contact Scraping complete refactor - Simple Scraper Pattern implementation (commits d6079e4, 17e740f, 117e858)

---

## QUICK REFERENCE SECTION

### 🎯 INSTANT PATTERN CHECKLIST

- [ ] Service accepts `AsyncSession` as parameter, never creates sessions
- [ ] Service file named `{workflow_name}_service.py` or `{workflow_name}_scheduler.py`
- [ ] Business logic encapsulated in service, not in router
- [ ] Service returns data/None, router handles HTTP responses
- [ ] Scheduler uses `run_job_loop` pattern from Curation SDK
- [ ] All database operations use the passed session parameter
- [ ] **DUAL STATUS ADAPTER:** Only queue processing when curation approves (Selected → Queued)
- [ ] **DUAL STATUS COORDINATION:** Curation and Processing status fields work in harmony
- [ ] **SIMPLE SCRAPER PATTERN:** Use proven simple scraping over complex multi-layered approaches

### 🔴 INSTANT REJECTION TRIGGERS

1. **Session creation in service** → REJECT (Cardinal Rule violation)
2. **Business logic in router** → REJECT (Pattern #2 violation)
3. **Missing service for workflow** → REJECT (Pattern #1 violation)
4. **Service handling HTTP responses** → REJECT (Pattern #4 violation)
5. **Direct transaction management** → REJECT (Pattern #5 violation)
6. **Missing tenant_id on INSERT** → REJECT (Pattern #7 violation - RLS requires tenant_id)
7. **DEFAULT_TENANT_ID or hardcoded UUIDs** → REJECT (The Law ADR-009)
8. **Broken dual adapter coordination** → REJECT (Universal Trigger Pattern violation)
9. **Auto-queuing without curation approval** → REJECT (Dual-Status Update Pattern violation)
10. **Over-engineered scraping with external dependencies** → REJECT (Simple Scraper Pattern violation)

### ✅ APPROVAL REQUIREMENTS

Before approving ANY service implementation:

1. Verify service accepts `AsyncSession` parameter
2. Confirm workflow naming convention followed
3. Check business logic properly encapsulated
4. Verify no HTTP concerns in service layer
5. Confirm scheduler uses SDK pattern if applicable
6. **VERIFY tenant_id on INSERT:** All new records must include tenant_id from parent
7. **VERIFY no DEFAULT_TENANT_ID:** No hardcoded UUIDs or fallbacks
8. **VERIFY DUAL ADAPTER LOGIC:** Only queue when curation_status = "Selected"
9. **VERIFY STATUS COORDINATION:** Processing status follows curation decisions
10. **VERIFY SIMPLE SCRAPING:** Use simple, proven scraping patterns over complex external dependencies

---

## PATTERN #1: Service File Existence & Naming

### ✅ CORRECT PATTERN:

```python
# File: src/services/wf4_domain_curation_service.py
# For workflow WF4_Domain_Curation

# File: src/services/background/wf5_sitemap_import_scheduler.py
# For workflow WF5_Sitemap_Curation scheduler component
```

**Why:** Consistent naming enables instant workflow identification
**Citation:** Layer 4 Blueprint Section 2.1, Constitutional naming convention

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Missing Service Entirely**

```python
# WF7 audit result:
# MISSING: src/services/wf7_page_curation_service.py
# MISSING: src/services/background/wf7_page_curation_scheduler.py
```

**Detection:** Check if service file exists for workflow
**From WF7:** Complete absence of Layer 4 components
**Impact:** Workflow lacks business logic encapsulation, architectural breakdown

**Violation B: Wrong Naming Convention**

```python
# File: src/services/sitemap_files_service.py  # WRONG!
# Should be: wf5_sitemap_files_service.py

# File: src/services/sitemap_import_scheduler.py  # WRONG!
# Should be: background/wf5_sitemap_import_scheduler.py
```

**Detection:** Service name doesn't match workflow name
**From WF5:** Inconsistent naming breaks workflow traceability
**Impact:** Confusion about service ownership and purpose

---

## PATTERN #2: Session Acceptance (CARDINAL RULE)

### ✅ CORRECT PATTERN:

```python
async def process_domain(
    domain_id: int,
    session: AsyncSession  # ACCEPT session as parameter
) -> Optional[DomainResult]:
    """Service accepts session, never creates."""
    domain = await session.get(Domain, domain_id)
    if domain:
        domain.status = "processed"
        # Use passed session for all operations
    return domain
```

**Why:** Services must accept sessions to maintain transaction boundaries
**Citation:** Layer 4 Blueprint Cardinal Rule, Constitution Article III.4

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Service Creating Session**

```python
# From wf1_places_deep_service.py:180
async def process_place(place_id: int):
    # VIOLATION: Service creating its own session!
    session = await get_session()
    if not session:
        logger.error("Failed to acquire database session.")
        return None
```

**Detection:** Any `get_session()`, `get_background_session()` in service
**From Audit:** wf1_places_deep_service.py violates cardinal rule
**Impact:** Breaks transaction control, creates nested transactions

**Violation B: Service Using Background Session**

```python
# From sitemap processing services
async def process_sitemap():
    # VIOLATION: Service creating background session
    async with get_background_session() as session:
        # Processing logic
```

**Detection:** `get_background_session()` anywhere in service
**From WF5:** Multiple sitemap services create sessions
**Impact:** Transaction boundaries become unmanageable

---

## PATTERN #3: Business Logic Encapsulation

### ✅ CORRECT PATTERN:

```python
# Service encapsulates complex business logic
async def list_domains_with_filters(
    session: AsyncSession,
    filters: DomainFilters,
    pagination: PaginationParams
) -> DomainListResult:
    """Complex listing logic belongs in service."""
    query = select(Domain)

    # Apply complex filters
    if filters.status:
        query = query.filter(Domain.status == filters.status)

    # Apply sorting logic
    if filters.sort_by:
        query = apply_sorting(query, filters.sort_by)

    # Execute and return data
    result = await session.execute(query)
    return DomainListResult(domains=result.scalars().all())
```

**Why:** Services own business logic, routers handle HTTP only
**Citation:** Layer 4 Blueprint Section 2.1.A

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Complex Logic in Router**

```python
# From wf4_domain_router.py router - VIOLATION!
ALLOWED_SORT_FIELDS = {
    "domain": Domain.domain,
    "created_at": Domain.created_at,
    # Complex mapping logic in router!
}

@router.get("/list")
async def list_domains(session: AsyncSession = Depends(get_session)):
    # VIOLATION: Complex business logic in router
    query = select(Domain)
    # Multiple filters, sorting, pagination logic
    # Should be in service layer!
```

**Detection:** Complex queries, business rules in router files
**From WF4:** list_domains endpoint exceeds Pattern B scope
**Impact:** Router becomes bloated, business logic scattered

---

## PATTERN #4: Return Types & HTTP Separation

### ✅ CORRECT PATTERN:

```python
# Service returns data or None, never HTTP responses
async def get_domain_details(
    domain_id: int,
    session: AsyncSession
) -> Optional[Domain]:  # Returns domain object or None
    """Service returns data, not HTTP responses."""
    return await session.get(Domain, domain_id)

# Router handles HTTP concerns
@router.get("/{domain_id}")
async def get_domain(
    domain_id: int,
    session: AsyncSession = Depends(get_session)
):
    domain = await domain_service.get_domain_details(domain_id, session)
    if not domain:
        raise HTTPException(status_code=404)  # HTTP in router only
    return domain
```

**Why:** Clean separation of concerns between layers
**Citation:** Layer 4 Blueprint Section 2.2

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Service Returning HTTP Responses**

```python
# VIOLATION: Service handling HTTP concerns
async def get_domain(domain_id: int, session: AsyncSession):
    domain = await session.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=404)  # WRONG LAYER!
    return JSONResponse(content={"domain": domain})  # WRONG!
```

**Detection:** `HTTPException`, `JSONResponse` in service files
**From Audit:** Services mixing HTTP concerns
**Impact:** Layer responsibilities become confused

---

## PATTERN #5: Scheduler Implementation

### ✅ CORRECT PATTERN:

```python
# Using Curation SDK pattern
from src.common.curation_sdk.scheduler_loop import run_job_loop

async def process_domain_queue():
    """Scheduler using SDK pattern."""
    await run_job_loop(
        process_fn=process_single_domain,
        queue_query=select(Domain).filter(
            Domain.status == "pending"
        ),
        status_field="status",
        processing_value="processing",
        completed_value="completed",
        failed_value="failed"
    )
```

**Why:** Consistent scheduler pattern across all workflows
**Citation:** Constitution Article III.1 - Universal Background Pattern

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Missing Workflow Scheduler**

```python
# From WF4 audit:
# MISSING: src/services/background/wf4_sitemap_discovery_scheduler.py
# domain_scheduler.py exists but doesn't process workflow queue!
```

**Detection:** No dedicated scheduler for workflow status field
**From WF4:** Missing scheduler for `sitemap_analysis_status`
**Impact:** Workflow queue never processed, critical functional gap

**Violation B: Manual Queue Processing**

```python
# VIOLATION: Not using SDK pattern
async def process_queue():
    domains = await session.execute(
        select(Domain).filter(Domain.status == "pending")
    )
    for domain in domains:
        # Manual processing without SDK
```

**Detection:** Manual queue loops instead of `run_job_loop`
**From Audit:** Inconsistent scheduler implementations
**Impact:** Error handling, retry logic inconsistent

---

## PATTERN #6: Dual Status Adapter Coordination (CONSTITUTIONAL REQUIREMENT)

### ✅ CORRECT PATTERN:

```python
# Universal Trigger Pattern implementation
def apply_dual_adapter_logic(curation_status: str, item_data: dict):
    """Only queue for processing when curation approves."""
    if curation_status == "Selected":
        item_data["processing_status"] = "Queued"  # Queue approved items
    elif curation_status == "New":
        item_data["processing_status"] = "New"     # Wait for human decision
    else:
        item_data["processing_status"] = "New"     # Default: wait

    return item_data

# Example: Page workflow coordination
if hb["decision"] == "skip" or hb["confidence"] < 0.2:
    page_data["page_processing_status"] = PageProcessingStatus.Filtered
    page_data["page_curation_status"] = PageCurationStatus.New
elif (high_value_conditions):
    # Auto-select high-value pages and queue for processing
    page_data["page_curation_status"] = PageCurationStatus.Selected
    page_data["page_processing_status"] = PageProcessingStatus.Queued
else:
    # Default: New pages wait for manual curation
    page_data["page_curation_status"] = PageCurationStatus.New
    page_data["page_processing_status"] = PageProcessingStatus.New
```

**Why:** Implements Constitutional Article III.2 - Universal Trigger Pattern
**Citation:** ScraperSky Development Constitution, Dual-Status Update Pattern

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Auto-Queuing Without Curation Approval**

```python
# VIOLATION: From sitemap import service (FIXED in commit 5c8c4ef)
if hb["decision"] == "skip" or hb["confidence"] < 0.2:
    page_data["page_processing_status"] = PageProcessingStatus.Filtered
else:
    page_data["page_processing_status"] = PageProcessingStatus.Queued  # WRONG!
    # This queues ALL non-filtered pages regardless of curation status
```

**Detection:** Processing status set to "Queued" without checking curation status
**From Fix:** Sitemap import service violated dual adapter pattern
**Impact:** System processes items that haven't been human-approved

**Violation B: Broken Status Coordination**

```python
# VIOLATION: Mismatched status pairs
item.curation_status = "New"      # Human hasn't decided
item.processing_status = "Queued"  # But system queues anyway - WRONG!
```

**Detection:** Curation="New" paired with Processing="Queued"
**Impact:** Bypasses human approval workflow, violates Constitutional pattern

### DUAL ADAPTER PAIRS IDENTIFIED:

> **NOTE (2025-12-21):** Enum consolidation has reduced 27 enums to 9 canonical types.
> Most curation statuses map to `WorkflowCurationStatus`, most processing statuses
> map to `WorkflowProcessingStatus`. See `src/models/enums.py` for current mappings.

1. **Page Workflow:** `WorkflowCurationStatus` ↔ `WorkflowProcessingStatus`
2. **Contact Workflow:** `WorkflowCurationStatus` ↔ `WorkflowProcessingStatus`
3. **HubSpot Workflow:** `WorkflowCurationStatus` ↔ `WorkflowProcessingStatus`
4. **Sitemap Import:** `SitemapCurationStatusEnum` ↔ `WorkflowProcessingStatus`

### VERIFICATION COMMANDS:

```bash
# Check for broken dual adapter logic
grep -n "processing_status.*Queued" src/services/*.py
grep -n "curation_status.*New" src/services/*.py

# Verify coordination patterns
grep -A5 -B5 "curation_status.*Selected" src/services/*.py
```

---

## PATTERN #7: Tenant ID Requirements for INSERT Operations

### ✅ CORRECT PATTERN:

```python
# The Law (SESSION-AND-TENANT-LAW.md line 55) REQUIRES tenant_id for INSERT policies
# RLS policies only filter by tenant during SELECT - INSERT must explicitly set tenant_id

# CORRECT: Always include tenant_id when creating new records
# From wf7_page_curation_service.py:141-142
new_contact = Contact(
    page_id=page.id,
    tenant_id=page.tenant_id,  # REQUIRED for INSERT
    email=email,
    source_type="page_scrape",
    contact_curation_status=ContactCurationStatus.New,
)
session.add(new_contact)

# CORRECT: Get tenant_id from parent record
# From wf5_sitemap_import_service.py:76-80
tenant_id = str(sitemap_file.tenant_id)
page_data = {
    "domain_id": domain_id,
    "url": page_url,
    "tenant_id": tenant_id,  # REQUIRED - inherit from parent
    "sitemap_file_id": sitemap_file.id,
}
```

**Why:** RLS INSERT policies require tenant_id to be explicitly set
**Citation:** SESSION-AND-TENANT-LAW.md line 55: "tenant_id=tenant_id in INSERT"

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Missing Tenant ID on INSERT**

```python
# VIOLATION: Omitting tenant_id on INSERT causes database errors
new_contact = Contact(
    page_id=page.id,
    # MISSING: tenant_id - will fail RLS INSERT policy!
    email=email,
    source_type="page_scrape",
)
session.add(new_contact)  # FAILS: RLS policy requires tenant_id
```

**Detection:** INSERT operations without tenant_id field
**Impact:** Database INSERT failures, RLS policy violations

**Violation B: Hardcoded or Default Tenant ID**

```python
# VIOLATION: Never use hardcoded UUIDs or DEFAULT_TENANT_ID
page_data = {
    "domain_id": domain_id,
    "url": page_url,
    "tenant_id": DEFAULT_TENANT_ID,  # FORBIDDEN per The Law
    "sitemap_file_id": sitemap_file.id,
}
```

**Detection:** `DEFAULT_TENANT_ID` or hardcoded UUID patterns
**From The Law:** ADR-009-DEFAULT-TENANT-ID-REMOVAL.md
**Impact:** Multi-tenant isolation violation, data leakage

### TENANT ID SOURCE HIERARCHY:

1. **Router endpoints:** Get from `current_user["tenant_id"]`
2. **Background jobs:** Get from parent record's `tenant_id`
3. **Schedulers:** Use two-phase pattern (SET ROLE postgres for discovery, then get tenant_id per item)

### VERIFICATION COMMANDS:

```bash
# Verify tenant_id is used in INSERT operations
grep -n "tenant_id=.*\.tenant_id" src/services/**/*.py

# Find any DEFAULT_TENANT_ID usage (should be 0 matches in services)
grep -rn "DEFAULT_TENANT_ID" src/services/
```

---

## PATTERN #8: Async I/O Correctness (Await vs Async Iterator)

### ✅ CORRECT PATTERN:

```python
# Services must await coroutines. Use async-for only on async iterators.
result = await crawler.arun(url, config)  # arun returns a coroutine → await it
return result  # or handle the returned object appropriately

# If the library exposes an async iterator, then:
async for item in crawler.stream(url, config):
    process(item)
```

**Why:** Using `async for` on a coroutine raises a runtime error and short-circuits processing.
**Citation:** Python async/await semantics; WF7 remediation tests

### ❌ ANTI-PATTERN VIOLATIONS:

```python
# wf4_domain_to_sitemap_adapter_service.py - VIOLATION!
async for result in self.crawler.arun(url, self.config):  # WRONG: arun is a coroutine
    results.append(result)
```

**Detection:** `'async for' requires an object with __aiter__ method, got coroutine` in logs
**Impact:** Crawler never yields data; downstream logic runs with empty content, masking failures

### Detection:

```bash
grep -n "async for .*arun\(" -n src/services/**/*.py
```

### Remediation Template:

```python
try:
    result = await self.crawler.arun(url, self.config)
    if not result:
        logger.warning("No content extracted from %s", url)
        return None
    return result
except Exception as e:
    logger.error("Error crawling %s: %s", url, e)
    return None
```

---

## VERIFICATION REQUIREMENTS

### Service Review Protocol

```bash
# Verify service accepts session
grep -n "AsyncSession" src/services/wf4_domain_curation_service.py

# Check for session creation violations
grep -n "get_session\|get_background_session" src/services/*.py

# Verify no HTTP concerns in services
grep -n "HTTPException\|JSONResponse" src/services/*.py

# Check for tenant_id usage
grep -n "tenant_id" src/services/*.py

# DUAL ADAPTER VERIFICATION
# Check for broken auto-queuing patterns
grep -n "processing_status.*Queued" src/services/*.py

# Verify curation approval logic
grep -A3 -B3 "curation_status.*Selected" src/services/*.py

# Find dual adapter pairs
grep -n "CurationStatus\|ProcessingStatus" src/models/enums.py
```

### What WF7 Did Wrong:

```python
# 1. No service files created at all
# 2. Router contained all business logic
# 3. Inline schemas instead of separate layer
# 4. No scheduler for background processing
# 5. Broke dual adapter pattern in sitemap import (FIXED)
```

### What WF7 Should Have Done:

```python
# 1. Create src/services/wf7_page_curation_service.py
# 2. Create src/services/background/wf7_page_curation_scheduler.py
# 3. Move business logic from router to service
# 4. Service accepts AsyncSession parameter
# 5. Use run_job_loop for scheduler
# 6. Implement proper dual adapter coordination
```

### RECENT FIX EXAMPLE (Commit 5c8c4ef):

```python
# BEFORE (Broken):
else:
    page_data["page_processing_status"] = PageProcessingStatus.Queued  # WRONG!

# AFTER (Fixed):
elif (high_value_conditions):
    page_data["page_curation_status"] = PageCurationStatus.Selected
    page_data["page_processing_status"] = PageProcessingStatus.Queued
else:
    page_data["page_curation_status"] = PageCurationStatus.New
    page_data["page_processing_status"] = PageProcessingStatus.New
```

---

## GUARDIAN CITATION FORMAT

When reviewing Layer 4 services, use this format:

```markdown
L4 SERVICE GUARDIAN ANALYSIS:
✅ Compliant with Pattern #1: Service files exist with correct naming
❌ VIOLATION of Pattern #2: Service creating session at line 45
❌ VIOLATION of Pattern #3: Complex business logic in router
⚠️ WARNING on Pattern #5: Scheduler missing for workflow queue
❌ VIOLATION of Pattern #6: Broken dual adapter coordination at line 208

REQUIRED CORRECTIONS:

1. Move session creation to router, pass as parameter
2. Extract business logic from router to service
3. Create dedicated workflow scheduler
4. Fix dual adapter logic: Only queue when curation_status="Selected"

APPROVAL: DENIED - Cardinal Rule and Constitutional violations must be corrected
```

---

## REPLACES

- Full Layer 4 Services Blueprint (200+ lines)
- All workflow-specific L4 audit reports (7 documents)
- Service implementation guidelines
- Scheduler pattern documentation

**With this single 450-line companion for instant pattern recognition!**

---

## PATTERN #9: Simple Scraper Pattern (NEW - 2025-09-20)

### ✅ CORRECT PATTERN:

```python
# File: src/utils/simple_scraper.py
async def scrape_page_simple_async(url: str) -> str:
    """Simple, effective, non-blocking async scraper."""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp...',
        # Standard browser headers
    }

    try:
        connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                response.raise_for_status()
                html_content = await response.text()
                return html_content

    except Exception as e:
        logging.error(f"Simple async scraper failed for {url}: {e}")
        return ""  # Return empty string on failure

# Service usage - Single line replacement
html_content = await scrape_page_simple_async(page_url)
```

**Why:** Replaces complex multi-layered scraping logic with proven simple approach
**Citation:** WF7 Contact Scraping Victory (2025-09-20), commits d6079e4, 17e740f, 117e858

### ❌ ANTI-PATTERN VIOLATIONS:

**Violation A: Over-Engineered Scraping Logic**

```python
# VIOLATION: From wf7_page_curation_service.py (FIXED in commit 117e858)
# 70+ lines of complex aiohttp + ScraperAPI fallback logic
try:
    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            # Complex retry logic with exponential backoff
            # SSL connector issues
            # ClientResponseError failures

        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            # Complex error handling

    # ScraperAPI fallback
    async with ScraperAPIClient() as scraper_client:
        html_content = await scraper_client.fetch(page_url, render_js=False)
        # HTTP 403 - credits exhausted
```

**Detection:** Multiple retry loops, complex fallback chains, external API dependencies
**From WF7:** Complex scraping logic failed with `ClientResponseError` and API credit exhaustion
**Impact:** Brittle, expensive, difficult to debug scraping failures

**Violation B: External API Dependency for Basic Scraping**

```python
# VIOLATION: Relying on ScraperAPI for basic HTTP requests
async with ScraperAPIClient() as scraper_client:
    html_content = await scraper_client.fetch(page_url, render_js=False)
    # Fails when credits exhausted - HTTP 403
```

**Detection:** External scraping service calls for basic HTML retrieval
**From WF7:** ScraperAPI credit exhaustion caused complete scraping failure
**Impact:** Unnecessary external dependency, cost, and single point of failure

### SIMPLE SCRAPER SUCCESS METRICS:

**Before Fix (Broken):**
- 70+ lines of complex scraping logic
- Multiple external dependencies (ScraperAPI)
- `ClientResponseError` failures
- HTTP 403 credit exhaustion
- 0% success rate

**After Fix (Working - commits d6079e4, 17e740f, 117e858):**
- Single line service call: `html_content = await scrape_page_simple_async(page_url)`
- 37 lines of simple, focused scraping logic
- No external dependencies
- 100% success rate (2/2 test cases)
- Content extraction: 149KB+ HTML successfully scraped

**VERIFICATION EVIDENCE:**
```
2025-09-20 05:00:30,909 - Simple async scraper successful for https://acuitylaservision.com/our-laser-vision-correction-surgeon/. Content length: 149088
2025-09-20 05:27:09,667 - Simple async scraper successful for https://thevisioncenterny.com/testimonials/. Content length: 141340
```

### GUARDIAN PRINCIPLE:
**"Simple solutions win. Replace complexity with proven simplicity."**

---

## 🛡️ RECENT CRITICAL FIXES

### SQLAlchemy Enum Model Pattern Violation (FIXED - Commit 426650f)

**VIOLATION TYPE:** Model Definition Inconsistency Breaking Service Layer
**IMPACT:** Contact creation complete failure in email_scraper service
**ROOT CAUSE:** SQLAlchemy model change from enum class to string literals without updating service code

**VIOLATION DETAILS:**
```python
# BEFORE (Working):
email_type = Column(Enum(ContactEmailTypeEnum, create_type=False, native_enum=True))
# Service code: email_type=ContactEmailTypeEnum.SERVICE ✅ (auto-converted)

# AFTER (Broken):
email_type = Column(Enum('SERVICE', 'CORPORATE', 'FREE', 'UNKNOWN', name='contactemailtypeenum'))
# Service code: email_type=ContactEmailTypeEnum.SERVICE ❌ (no auto-conversion)
```

**FIX APPLIED (Commit 426650f):**
```python
# In src/tasks/email_scraper.py:234
# BEFORE: email_type=email_type,
# AFTER:  email_type=email_type.value,  # Convert enum to string
```

**GUARDIAN PATTERN:** When changing SQLAlchemy model enum definitions, ALL service code using those enums must be updated to use `.value` for string extraction.

**VERIFICATION:** Database schema never changed - always expected strings. Issue was Python-side enum object vs string mismatch.

---

### WF7 Contact Scraping Complete Refactor (FIXED - Commits d6079e4, 17e740f, 117e858)

**VIOLATION TYPE:** Multiple cascading service layer failures preventing end-to-end functionality
**IMPACT:** WF7 Contact Scraping completely non-functional - pages queued but no contacts created
**ROOT CAUSE:** BaseModel UUID generation + Database enum mismatches + Over-engineered scraping logic

**VIOLATION DETAILS:**

**Issue 1: BaseModel UUID Generation Failure (FIXED in commit d6079e4)**
```python
# BEFORE (Broken):
id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
# SQLAlchemy object instantiation failed - server_default incompatible with client creation

# AFTER (Fixed):
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
# Client-side UUID generation works with SQLAlchemy objects
```

**Issue 2: Database Enum Name Mismatches (FIXED in commit 17e740f)**
```python
# BEFORE (Broken):
contact_curation_status = Column(Enum(..., name='contactcurationstatus'))  # No underscores
# Database expected: contact_curation_status (with underscores)

# AFTER (Fixed):
contact_curation_status = Column(Enum(..., name='contact_curation_status'))  # Matches DB
# Perfect alignment with database schema
```

**Issue 3: Over-Engineered Scraping Logic (FIXED in commit 117e858)**
```python
# BEFORE (Broken): 70+ lines of complex aiohttp + ScraperAPI fallback
# ClientResponseError failures, HTTP 403 credit exhaustion, 0% success rate

# AFTER (Fixed): Simple Scraper Pattern
html_content = await scrape_page_simple_async(page_url)  # Single line, 100% success
```

**FIX RESULTS:**
- **Test 1**: `svale@acuitylaservision.com` + `2459644568` - SUCCESS
- **Test 2**: `info@thevisioncenterny.com` + `1748983646` - SUCCESS
- **Success Rate**: 100% (2/2 tests)
- **Content Extraction**: 149KB+ HTML per page
- **End-to-End**: Page queued → Content scraped → Contact extracted → Database inserted → Page completed

**GUARDIAN PATTERN:** When multiple service layer issues cascade, fix foundation first (BaseModel), then data layer (enums), then business logic (scraping). Test end-to-end after each fix.

**VERIFICATION EVIDENCE:**
```
2025-09-20 05:00:31,271 - SCHEDULER_LOOP: Finished processing batch for Page. Success: 1, Failed: 0, Total Attempted: 1.
2025-09-20 05:27:10,027 - SCHEDULER_LOOP: Finished processing batch for Page. Success: 1, Failed: 0, Total Attempted: 1.
```

---

_"Services accept, never create. Simple solutions win. This is the way."_
**- The L4 Service Guardian**
