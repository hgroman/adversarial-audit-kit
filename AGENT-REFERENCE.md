# Agent Reference Card

Quick reference for all 7 agents (6 auditors + 1 test generator).

---

## At a Glance

### Phase 1: Auditors

| Agent | Code | Output File | Key Question |
|-------|------|-------------|--------------|
| Architect | `audit-01-architect` | ARCH-findings.md | "Will this import?" |
| DevOps | `audit-02-devops` | DEVOPS-findings.md | "Will this deploy?" |
| Data Assassin | `audit-03-data-assassin` | SEC-findings.md | "Can tenant A see tenant B's data?" |
| Kraken | `audit-04-kraken` | KRAKEN-findings.md | "What breaks at 100 users?" |
| Operator | `audit-05-operator` | OPS-findings.md | "Can I debug this at 2 AM?" |
| Test Sentinel | `audit-06-test-sentinel` | TEST-findings.md | "How do we know it works?" |

### Phase 2: Test Generator

| Agent | Code | Output File | Key Question |
|-------|------|-------------|--------------|
| Compliance Test Generator | `compliance-test-generator` | test_*_compliance.py | "How do we prove it stays fixed?" |

---

## 1. Architect

**File**: `agents/audit-01-architect.md`
**Mindset**: "I will find the circular dependency that crashes on import."

### Hunts For

| Issue | Detection Method |
|-------|------------------|
| Circular imports | `python -c "from src.X import Y"` |
| Layer violations | `grep -rn "from src.routers" src/services/` |
| Dead code | Methods with 0 call sites |
| God files | `wc -l` > 1000 lines |
| Naming violations | Missing `wfX_` prefix |
| Schema-model mismatch | Compare migrations to SQLAlchemy models |

### Required Reading
1. `SESSION-AND-TENANT-LAW.md`
2. `WORKFLOW-RLS-REGISTRY.yaml`
3. `CRITICAL_PATTERNS.md` (patterns 2,3,5,9,13,14,17,18,24)

### Sample Finding
```markdown
## Finding: ARCH-002

**Location**: work order Section 4.1
**Pattern Found**: References `companies` table
**Verdict**: VIOLATION - table does not exist

### Remediation
Add Phase 3.4.0 to create companies table infrastructure.
```

---

## 2. DevOps

**File**: `agents/audit-02-devops.md`
**Mindset**: "I will find why Docker build fails at 2 AM."

### Hunts For

| Issue | Detection Method |
|-------|------------------|
| Missing dependencies | `grep -i package requirements.txt` |
| Docker build failures | `docker build .` |
| Unregistered routers | Check `main.py` includes |
| Missing env vars | Check `render.yaml` |
| Pre-commit violations | File naming, formatting |
| Import errors | Path verification |

### Required Reading
1. `render.yaml` - Production env config
2. `Dockerfile` - Build process
3. `requirements.txt` - Dependencies

### Sample Finding
```markdown
## Finding: DEVOPS-003

**Location**: work order Section 6.1
**Pattern Found**: Uses `langchain`
**Verdict**: VIOLATION - not in requirements.txt

### Remediation
Add to requirements.txt:
langchain>=0.1.0
langchain-openai>=0.0.5
```

---

## 3. Data Assassin

**File**: `agents/audit-03-data-assassin.md`
**Mindset**: "I will find the tenant data leak."

### Hunts For

| Issue | Detection Method |
|-------|------------------|
| SET ROLE without RESET | Pattern scan |
| RLS bypass | Check for postgres role usage |
| Missing WITH CHECK | RLS policy review |
| Hardcoded tenant IDs | UUID grep |
| SQL injection | Dynamic query analysis |
| AI-generated SQL | Execution path trace |

### Required Reading
1. `SESSION-AND-TENANT-LAW.md` (especially Rule 4)
2. `00_RLS-CRITICAL-PATH.md`
3. `ADR-007-RLS-TENANT-CONTEXT-PATTERN.md`

### Sample Finding
```markdown
## Finding: SEC-002

**Location**: src/routers/wf10_signal_router.py:109-120
**Pattern Found**: SET ROLE without RESET ROLE
**Verdict**: VIOLATION - role leak vulnerability

### Remediation
await session.execute(text("SET ROLE postgres"))
try:
    # query
finally:
    await session.execute(text("RESET ROLE"))
```

---

## 4. Kraken

**File**: `agents/audit-04-kraken.md`
**Mindset**: "I will exhaust your connection pool at 10 concurrent requests."

### Hunts For

| Issue | Detection Method |
|-------|------------------|
| Blocking `__init__` | LLM/API client initialization |
| Connection hold during I/O | Trace session lifecycle |
| Missing rate limits | Endpoint analysis |
| Session as instance var | Class attribute scan |
| In-memory state | Dict/list storage patterns |
| Race conditions | Concurrent update paths |

### Required Reading
1. `ADR-001-Supavisor-Requirements.md`
2. `L4_Service_Guardian_Pattern_AntiPattern_Companion.md`
3. `SCHEDULER_REFERENCE.md`

### Sample Finding
```markdown
## Finding: KRAKEN-001

**Location**: work order Section 6.2
**Pattern Found**: ChatOpenAI() in __init__
**Verdict**: VIOLATION - blocks event loop

### Remediation
Use lazy initialization:
@property
def llm(self):
    if self._llm is None:
        self._llm = ChatOpenAI(...)
    return self._llm
```

---

## 5. Operator

**File**: `agents/audit-05-operator.md`
**Mindset**: "I will make your 2 AM incident investigation impossible."

### Hunts For

| Issue | Detection Method |
|-------|------------------|
| Missing tenant_id in logs | Log statement scan |
| Silent failures | Catch-and-ignore patterns |
| No health checks | Endpoint inventory |
| Logs without context | Structured logging check |
| Missing metrics | Observability gaps |
| No alerting hooks | Critical path analysis |

### Required Reading
1. `OBSERVABILITY-REQUIREMENTS.md`
2. `L4_Service_Guardian_Pattern_AntiPattern_Companion.md`
3. `CRITICAL_PATTERNS.md` (logging patterns)

### Sample Finding
```markdown
## Finding: OPS-001

**Location**: work order Section 6
**Pattern Found**: logger.info without tenant_id
**Verdict**: VIOLATION - no tenant isolation in logs

### Remediation
logger.info(
    "Chat request",
    extra={"tenant_id": tenant_id, "user_id": user_id}
)
```

---

## 6. Test Sentinel

**File**: `agents/audit-06-test-sentinel.md`
**Mindset**: "I will find the untested edge case that breaks production."

### Hunts For

| Issue | Detection Method |
|-------|------------------|
| Missing fixtures | Test file analysis |
| No error tests | Happy path only |
| No concurrency tests | Parallel execution gaps |
| Low test count | Count vs. standard |
| Missing categories | 6-category check |
| Untestable code | Dependency analysis |

### Required Reading
1. `WO-INTEGRATION-TEST-STANDARDIZATION.md`
2. `L4_Service_Guardian_Pattern_AntiPattern_Companion.md`
3. Existing test examples in `tests/`

### Test Categories Required

| Category | Minimum | Purpose |
|----------|---------|---------|
| Unit | 20+ | Isolated function testing |
| Integration | 15+ | Cross-component testing |
| Multi-tenant | 10+ | RLS isolation verification |
| Error cases | 5+ | Failure mode handling |
| Concurrency | 3+ | Race condition detection |
| E2E | 3+ | Full workflow testing |
| **TOTAL** | **56+** | |

### Sample Finding
```markdown
## Finding: TEST-001

**Location**: work order Section 8
**Pattern Found**: 3 tests provided
**Verdict**: VIOLATION - requires 56+ tests

### Remediation
Expand test section with:
- 20+ unit tests
- 15+ integration tests
- 10+ multi-tenant tests
- 5+ error case tests
- 3+ concurrency tests
- 3+ E2E tests
```

---

## Finding Codes

Each auditor uses a consistent code prefix:

| Agent | Code Format | Example |
|-------|-------------|---------|
| Architect | ARCH-XXX | ARCH-001, ARCH-MODEL-SYNC-001 |
| DevOps | DEVOPS-XXX | DEVOPS-003 |
| Data Assassin | SEC-XXX | SEC-002 |
| Kraken | KRAKEN-XXX | KRAKEN-001 |
| Operator | OPS-XXX | OPS-001 |
| Test Sentinel | TEST-XXX | TEST-001 |

---

## Severity Levels

All agents use the same severity scale:

| Severity | Symbol | Meaning | Blocks Deploy |
|----------|--------|---------|---------------|
| BLOCKER | BLOCKER | Production will fail | Yes |
| WARNING | WARNING | Should fix, may cause issues | No |
| ADVISORY | ADVISORY | Improvement suggestion | No |

---

## Running Individual Agents

To run a single agent instead of all 6:

```
Task(
    subagent_type="audit-01-architect",
    prompt="Audit 05_Active_Work/WO-XXX.md for structural issues"
)
```

Or with general-purpose if agent not registered:

```
Task(
    subagent_type="general-purpose",
    prompt="[Read agents/audit-01-architect.md persona, then audit...]"
)
```

---

## Agent Tools

Each agent has access to:

| Tool | Purpose |
|------|---------|
| Read | Read files, prereqs, work orders |
| Grep | Pattern search in codebase |
| Glob | Find files by pattern |
| Bash | Run verification commands |

Agents do NOT have Write access to production code. They only write to their findings file.

---

## Customizing Agents

To modify an agent's focus:

1. Edit `agents/audit-XX-name.md`
2. Update the "Hunts For" section
3. Add new required reading if needed
4. Test with a sample work order

To add a new agent:

1. Create `agents/audit-0X-newname.md`
2. Follow the existing persona format
3. Update orchestrator to spawn the new agent
4. Add new findings file to VERDICT template

---

## 7. Compliance Test Generator

**File**: `agents/compliance-test-generator.md`
**Mindset**: "A finding is an opinion. A passing test is a fact."

### Purpose

Transforms Phase 1 audit findings into executable pytest tests that run forever in CI.

### Generates Tests For

| Finding Type | Test Class | Checks |
|--------------|------------|--------|
| ARCH-* | `TestArchitecturalCompliance` | Imports, layers, naming, schema sync |
| SEC-* | `TestSecurityCompliance` | RLS, tenant isolation, role management |
| DEVOPS-* | `TestBuildCompliance` | Dependencies, registration, env vars |
| KRAKEN-* | `TestConcurrencyCompliance` | Connection pools, blocking I/O |
| OPS-* | `TestObservabilityCompliance` | Logging, error handling |
| TEST-* | `TestCoverageCompliance` | Test counts, fixtures |

### Required Input

All 6 Phase 1 findings files in the audit directory:
- ARCH-findings.md
- DEVOPS-findings.md
- SEC-findings.md
- KRAKEN-findings.md
- OPS-findings.md
- TEST-findings.md

### Output

```
tests/compliance/test_{wo_name}_compliance.py
```

### Sample Generated Test

```python
class TestSecurityCompliance:
    """
    LAW: SESSION-AND-TENANT-LAW.md §Rule 4
    FINDING: SEC-002 - SET ROLE must have RESET ROLE
    """

    def test_all_set_role_have_reset_role(self):
        """Every SET ROLE must have corresponding RESET ROLE."""
        violations = []
        for py_file in Path("src").rglob("*.py"):
            content = py_file.read_text()
            if content.count("SET ROLE") > content.count("RESET ROLE"):
                violations.append(str(py_file))

        assert violations == [], f"Role leak: {violations}"
```

### Invocation

Drag `compliance-test-orchestrator.md` **from the audit folder** into chat after implementation is complete.

---

## The Two-Phase Workflow

```
PHASE 1: ADVERSARIAL AUDIT
┌────────────────────────────────────────────┐
│  Work Order → 6 Auditors → Findings        │
│  Output: "Here's what's wrong"             │
└────────────────────────────────────────────┘
                    ↓
          [Developer fixes issues]
                    ↓
PHASE 2: COMPLIANCE TESTS
┌────────────────────────────────────────────┐
│  Findings → Test Generator → pytest suite  │
│  Output: "Here's how to prove it's fixed"  │
└────────────────────────────────────────────┘
                    ↓
CONTINUOUS: CI/CD
┌────────────────────────────────────────────┐
│  pytest tests/compliance/ → Pass/Fail      │
│  Output: "It stays fixed forever"          │
└────────────────────────────────────────────┘
```
