# Work Order: Integration Test Standardization

**Created:** 2026-01-01
**Status:** PENDING
**Priority:** HIGH
**Type:** Quality Assurance / Testing Infrastructure
**Estimated Effort:** 40-60 hours (5-8 hours per workflow)
**Reference Implementation:** `tests/integration/test_wf10_*.py`

---

## Objective

Bring all workflow integration tests (WF1-WF9) up to the comprehensive standard established by the WF10 Unified Signal Platform test suite. Each workflow should have systematic coverage of happy paths, error cases, RLS isolation, edge cases, and concurrency behavior.

---

## Background

### The WF10 Standard

During Phase 5 of the WF10 Unified Signal Platform implementation (2026-01-01), a comprehensive integration test suite was created that serves as a gold standard for workflow testing:

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_wf10_signal_options.py` | 8 | API endpoint behavior, filtering, normalization |
| `test_wf10_batch_trigger.py` | 10 | Core functionality, large batches, duplicates |
| `test_wf10_callback.py` | 8 | Completion flow, auth, validation, error handling |
| `test_wf10_rls_isolation.py` | 6 | Tenant isolation, cross-tenant protection |
| `test_wf10_fallback.py` | 9 | Graceful degradation, missing config handling |
| `test_wf10_concurrency.py` | 7 | Parallel requests, connection pool stress |

**Total: 48 tests** providing comprehensive coverage of a single workflow.

### Current State

Existing workflow tests are inconsistent in coverage depth. Many lack:
- RLS isolation verification
- Concurrency testing
- Edge case coverage (empty inputs, large batches)
- Fallback behavior testing
- Comprehensive error case coverage

---

## The Testing Methodology

### 1. Happy Path Tests
Verify the core functionality works as expected:
- API endpoints return correct status codes
- Database records are created/updated correctly
- Response payloads match expected schema
- Workflow state transitions occur properly

### 2. Error Case Tests
Verify graceful failure handling:
- Invalid input validation (422 responses)
- Missing required fields
- Authentication failures (401/403)
- Not found cases (404)
- Internal errors don't leak sensitive info (500)

### 3. RLS Isolation Tests
**CRITICAL for multi-tenant security:**
- Tenant A cannot see Tenant B's data via direct query
- API endpoints only return current tenant's data
- Cross-tenant operations are blocked
- NULLIF wrapper prevents empty string RLS errors

### 4. Edge Case Tests
Verify boundary conditions:
- Empty inputs (empty arrays, null values)
- Large batches (50+ items)
- Duplicate entries in same request
- Unknown/invalid entity types
- Maximum field lengths

### 5. Fallback Behavior Tests
Verify graceful degradation:
- Missing configuration (workflow_methods, env vars)
- Inactive records are ignored
- Default values are applied correctly
- System doesn't crash on missing optional data

### 6. Concurrency Tests
Verify parallel request handling:
- Multiple simultaneous requests succeed
- No race conditions or deadlocks
- Connection pool handles load
- No duplicate records from retries (unless intended)

---

## Test File Template

For each workflow, create the following test files:

```
tests/integration/
├── test_wfX_[primary_endpoint].py      # Core CRUD operations
├── test_wfX_[secondary_endpoint].py    # Additional endpoints
├── test_wfX_rls_isolation.py           # RLS security tests
├── test_wfX_edge_cases.py              # Boundary conditions
└── test_wfX_concurrency.py             # Parallel request tests
```

---

## Workflow-Specific Requirements

### WF1: Places Search (The Scout)
- Test Google Maps API integration mocking
- Test place_staging record creation
- Test search result pagination
- RLS: Verify tenant isolation of staged places

### WF2: Deep Scan (The Analyst)
- Test scheduler picks up queued items
- Test place details enrichment
- Test status transitions (Queued → Processing → Completed)
- Concurrency: Multiple schedulers don't double-process

### WF3: Local Business (The Navigator)
- Test domain extraction from places
- Test local_business record creation
- Test deduplication logic
- RLS: Cross-tenant business isolation

### WF4: Domain Curation (The Surveyor)
- Test domain CRUD operations
- Test sitemap discovery triggering
- Test dual-status pattern (curation + processing)
- Edge: Large domain batches

### WF5: Sitemap Curation (The Flight Planner)
- Test sitemap file processing
- Test page URL extraction
- Test sitemap parsing edge cases (malformed XML)
- Concurrency: Parallel sitemap processing

### WF7: Page Curation (The Extractor)
- Test contact extraction
- Test page scraping results
- Test extraction failure handling
- Edge: Very large pages, timeout handling

### WF8: Contact Curation (The Connector)
- Test CRM sync operations
- Test Brevo/HubSpot integration mocking
- Test contact deduplication
- RLS: Contact data isolation

### WF9: Semantic Copilot (The Librarian)
- Test vector search queries
- Test embedding generation
- Test relevance scoring
- Edge: Empty results, very long queries

---

## Test Infrastructure Requirements

### Fixtures Already Available
From `tests/integration/conftest.py`:
- `api_client` - Authenticated AsyncClient with dev bypass token
- `real_session` - AsyncSession for direct DB queries
- `db_engine` - Engine with Supavisor-compatible settings
- `TEST_TENANT_ID` - Isolated test tenant UUID

### Critical Patterns

**1. Always RESET ROLE before cleanup:**
```python
finally:
    await real_session.execute(text("RESET ROLE"))
    await real_session.execute(text("DELETE FROM table WHERE ..."))
    await real_session.commit()
```

**2. Use unique identifiers for test data:**
```python
signal_type = f"test-{uuid4().hex[:8]}"  # Unique per test run
```

**3. Monkeypatch secrets for callback tests:**
```python
@pytest.fixture(autouse=True)
def set_callback_secret(monkeypatch):
    monkeypatch.setattr("src.config.settings.settings.SOME_SECRET", "test-value")
```

**4. Handle response structure variations:**
```python
error_msg = data.get("detail", "") or data.get("message", "")
```

---

## CI/CD Considerations

### Parallel Test Execution

**Current Issue:** Tests run sequentially, taking 5-10 minutes for the full suite.

**Recommendation:** Implement parallel test execution using `pytest-xdist`:

```bash
# Install
pip install pytest-xdist

# Run with 4 parallel workers
pytest -n 4 tests/integration/

# Run with auto-detected CPU count
pytest -n auto tests/integration/
```

**Requirements for Parallel Safety:**
1. Each test must use unique identifiers (no shared test data)
2. Tests must clean up after themselves
3. Connection pool must handle concurrent test sessions
4. Consider separate test databases per worker for full isolation

### Recommended CI Configuration

```yaml
# .github/workflows/test.yml
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-group: [wf1-wf3, wf4-wf5, wf7-wf9, wf10]
    steps:
      - name: Run Integration Tests
        run: |
          pytest tests/integration/test_${{ matrix.test-group }}*.py \
            -n auto \
            --tb=short \
            -v
```

---

## Acceptance Criteria

For each workflow (WF1-WF9), the following must be completed:

- [ ] Minimum 20 integration tests per workflow
- [ ] RLS isolation tests verifying tenant boundaries
- [ ] Concurrency tests with at least 10 parallel requests
- [ ] Edge case coverage (empty, large, duplicate inputs)
- [ ] Error case coverage (auth, validation, not found)
- [ ] All tests pass in CI with parallel execution
- [ ] Test execution time under 2 minutes per workflow

---

## Priority Order

1. **WF4 (Domain Curation)** - High traffic, core to pipeline
2. **WF5 (Sitemap Curation)** - Complex processing, many edge cases
3. **WF8 (Contact Curation)** - External CRM integrations
4. **WF3 (Local Business)** - Deduplication logic critical
5. **WF7 (Page Curation)** - Scraping reliability
6. **WF1 (Places Search)** - External API dependency
7. **WF2 (Deep Scan)** - Scheduler complexity
8. **WF9 (Semantic Copilot)** - Vector search edge cases

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test count per workflow | ~5-10 | 20+ |
| RLS tests per workflow | 0-2 | 5+ |
| Concurrency tests | 0 | 5+ per workflow |
| CI execution time | N/A | < 5 min total (parallel) |
| Test coverage | Unknown | 80%+ per workflow |

---

## References

- **Reference Implementation:** `tests/integration/test_wf10_*.py`
- **Test Infrastructure:** `tests/integration/conftest.py`
- **Workflow Documentation:** `00_Current_Architecture/02_Workflow_Truth/`
- **Session Management Law:** `00_Current_Architecture/00_The_Law/SESSION-AND-TENANT-LAW.md`
