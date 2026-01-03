# Adversarial Audit Kit

A multi-agent adversarial code review system that finds what humans miss.

---

## What This Is

The Adversarial Audit Kit is a **two-phase system**:

- **Phase 1**: Deploy **6 specialized AI auditors** in parallel to stress-test work orders before implementation
- **Phase 2**: Transform findings into **executable compliance tests** that prevent regression forever

### The 7 Agents

| Agent | Codename | Phase | Purpose |
|-------|----------|-------|---------|
| **Architect** | Structure Breaker | 1 | Circular imports, layer violations, dead code, god files |
| **DevOps** | Build Saboteur | 1 | Missing dependencies, broken Docker builds, unregistered routers |
| **Data Assassin** | Security Predator | 1 | RLS bypasses, tenant leaks, role mismanagement |
| **Kraken** | Concurrency Crusher | 1 | Connection pool exhaustion, blocking I/O, race conditions |
| **Operator** | 2AM Nightmare | 1 | Missing logs, silent failures, unobservable errors |
| **Test Sentinel** | Coverage Hunter | 1 | Missing test categories, untestable code, fixture gaps |
| **Compliance Test Generator** | Truth Encoder | 2 | Transforms findings into pytest tests |

**Phase 1** auditors read prerequisite documents (the architectural "law"), then attack the work order from their specialty. Findings are classified as **BLOCKER**, **WARNING**, or **ADVISORY**.

**Phase 2** takes those findings and generates executable tests. *A finding is an opinion. A passing test is a fact.*

---

## Why This Exists

On **2025-12-26**, an auditor created a false work order `WO-RLS-LAW-VIOLATION-FIX.md` because they didn't read the registry before calling something a violation. Hours wasted on a documented, intentional pattern.

On **2026-01-02**, we ran the first full audit cycle on `WO-WF10-PHASE3.4-COMPANY-LAUNCHPAD`. The result:

| Metric | Count |
|--------|-------|
| **BLOCKERS found** | 21 |
| **WARNINGS found** | 14 |
| **Existing production bugs found** | 1 (SEC-002: role leak) |
| **Time to complete** | ~15 minutes |

The kit found that the work order assumed a `companies` table that didn't exist, used imports from files that don't exist, violated the ORM mandate with raw SQL, and provided 3 tests when 56+ were required.

**We fixed SEC-002 in production that same day.**

---

## Quick Start (5 Minutes)

### Phase 1: Adversarial Audit

**Step 1: Start the Audit**

Drag `adversarial-audit-orchestrator.md` into your Claude Code chat, then provide the work order path:

```
Audit: 00_Current_Architecture/05_Active_Work/WO-MY-FEATURE.md
```

**Step 2: Wait for 6 Auditors**

The orchestrator:
1. Creates `WO-MY-FEATURE-Audit/` directory
2. Spawns 6 auditors in parallel
3. Monitors completion
4. Copies `compliance-test-orchestrator.md` into the audit folder
5. Produces `VERDICT.md` with deployment recommendation

**Step 3: Review Verdict**

```
WO-MY-FEATURE-Audit/
  WO-MY-FEATURE.md                 # Your work order (moved here)
  compliance-test-orchestrator.md  # For Phase 2 (drag later)
  _STATUS.yaml                     # Audit progress
  ARCH-findings.md                 # Architect findings
  DEVOPS-findings.md               # DevOps findings
  SEC-findings.md                  # Security findings
  KRAKEN-findings.md               # Concurrency findings
  OPS-findings.md                  # Observability findings
  TEST-findings.md                 # Test coverage findings
  VERDICT.md                       # Final recommendation
```

### Phase 2: Compliance Tests (After Implementation)

**Step 4: Implement Fixes**

Address the BLOCKER findings from Phase 1, implement the work order.

**Step 5: Generate Compliance Tests**

Drag `compliance-test-orchestrator.md` **from the audit folder** into chat:

```
Generate compliance tests
```

The 7th agent reads all findings and produces:

```
tests/compliance/test_wf10_phase34_compliance.py
```

**Step 6: Run Tests Forever**

```bash
pytest tests/compliance/ -v
```

Add to CI - these tests prevent regression permanently.

---

## Understanding the Verdict

### Deployment Recommendations

| Verdict | Meaning | Action |
|---------|---------|--------|
| **GO** | No blockers found | Safe to implement |
| **CONDITIONAL GO** | Blockers found but fixable | Fix blockers first, then implement |
| **BLOCKED** | Fundamental issues | Revise work order before implementation |

### Finding Severity

| Severity | Meaning | Blocks Deploy? |
|----------|---------|----------------|
| **BLOCKER** | Will cause production failure | Yes |
| **WARNING** | Should fix, may cause issues | No |
| **ADVISORY** | Improvement suggestion | No |

---

## The 7 Agents

### Phase 1 Auditors (1-6)

### 1. Architect (audit-01-architect)

**Mindset**: "I will find the circular dependency that crashes on import."

**Hunts for**:
- Circular imports that crash before the app starts
- Layer violations (router importing router, service importing router)
- Dead code with 0 call sites
- God files over 1000 lines
- Missing `wfX_` naming prefixes
- Database-model synchronization failures

**Key question**: "Will this even import successfully?"

---

### 2. DevOps (audit-02-devops)

**Mindset**: "I will find why Docker build fails at 2 AM."

**Hunts for**:
- Missing dependencies in `requirements.txt`
- Docker build failures
- Unregistered routers in `main.py`
- Missing environment variables in `render.yaml`
- File naming that pre-commit hooks reject
- Import paths that don't exist

**Key question**: "Will this deploy successfully?"

---

### 3. Data Assassin (audit-03-data-assassin)

**Mindset**: "I will find the tenant data leak."

**Hunts for**:
- `SET ROLE` without `RESET ROLE` (role leak)
- RLS bypass without proper authorization
- Missing `WITH CHECK` clauses on RLS policies
- Hardcoded tenant IDs
- SQL injection vectors in dynamic queries
- AI-generated SQL execution risks

**Key question**: "Can Tenant A see Tenant B's data?"

---

### 4. Kraken (audit-04-kraken)

**Mindset**: "I will exhaust your connection pool at 10 concurrent requests."

**Hunts for**:
- Blocking I/O in `__init__` methods
- Holding database connections during external API calls
- Missing rate limiting on expensive operations
- Session stored as instance variable (not per-request)
- In-memory state that doesn't scale across workers
- Race conditions in status updates

**Key question**: "What happens at 100 concurrent users?"

---

### 5. Operator (audit-05-operator)

**Mindset**: "I will make your 2 AM incident investigation impossible."

**Hunts for**:
- Missing `tenant_id` in log messages
- Silent failure patterns (catch-and-ignore)
- No health check endpoints
- Errors logged without context
- Missing structured logging
- No metrics or alerting hooks

**Key question**: "When this breaks at 2 AM, can I find the cause?"

---

### 6. Test Sentinel (audit-06-test-sentinel)

**Mindset**: "I will find the untested edge case that breaks production."

**Hunts for**:
- Missing multi-tenant test fixtures
- No error case tests
- No concurrency tests
- Insufficient test count (WF10 requires 56+)
- Missing integration test categories
- Untestable code patterns (hidden dependencies)

**Key question**: "How do we know this works?"

---

### Phase 2 Agent

### 7. Compliance Test Generator (compliance-test-generator)

**Mindset**: "A finding is an opinion. A passing test is a fact."

**Purpose**: Transforms Phase 1 findings into executable pytest tests that:
- Encode each finding as a test
- Cite the architectural law being verified
- Detect violation patterns automatically
- Run in CI forever, preventing regression

**Generates tests for**:
- ARCH-* → `TestArchitecturalCompliance` (imports, layers, naming)
- SEC-* → `TestSecurityCompliance` (RLS, tenant isolation, roles)
- DEVOPS-* → `TestBuildCompliance` (dependencies, registration)
- KRAKEN-* → `TestConcurrencyCompliance` (connection pools, blocking I/O)
- OPS-* → `TestObservabilityCompliance` (logging, error handling)
- TEST-* → `TestCoverageCompliance` (test counts, fixtures)

**Key question**: "How do we prove it stays fixed?"

**Invocation**: Drag `compliance-test-orchestrator.md` from audit folder after implementation.

---

## How Agents Work

### Mandatory Reading

Every agent MUST complete prerequisite reading before auditing:

1. `prereqs/00_MANDATORY-PREREQS.md` - What to read and why
2. `prereqs/SESSION-AND-TENANT-LAW.md` - The canonical RLS rulebook
3. `prereqs/00_RLS-CRITICAL-PATH.md` - Critical security paths
4. `prereqs/WORKFLOW-RLS-REGISTRY.yaml` - Source of truth for allowed patterns

**Why this matters**: Without reading the registry, auditors create false positives. The registry documents intentional patterns that look like violations.

### The Verification Loop

```
1. Find potential issue
2. Check WORKFLOW-RLS-REGISTRY.yaml
3. Check SESSION-AND-TENANT-LAW.md
4. Verdict: VIOLATION | INTENTIONAL | FALSE_ALARM
5. Document with law citations
```

### Output Format

Every finding includes:

```markdown
## Finding: [AUDITOR-CODE]-XXX

**Location**: file_path:line_number
**Severity**: BLOCKER | WARNING | ADVISORY
**Law Reference**: Which document section applies
**Verdict**: VIOLATION | INTENTIONAL_PATTERN | FALSE_ALARM

### Evidence
[Code snippet or command output]

### Impact
[What happens if this ships]

### Remediation
[Specific fix with code example]
```

---

## Directory Structure

```
Adversarial-Audit-Kit/
├── README.md                           # This file
├── adversarial-audit-orchestrator.md   # Phase 1 orchestrator (drag into chat)
├── compliance-test-orchestrator.md     # Phase 2 orchestrator (copied to audit folders)
├── agents/                             # The 7 agent personas
│   ├── audit-01-architect.md           # Phase 1: Structure
│   ├── audit-02-devops.md              # Phase 1: Build/Deploy
│   ├── audit-03-data-assassin.md       # Phase 1: Security
│   ├── audit-04-kraken.md              # Phase 1: Concurrency
│   ├── audit-05-operator.md            # Phase 1: Observability
│   ├── audit-06-test-sentinel.md       # Phase 1: Coverage
│   └── compliance-test-generator.md    # Phase 2: Test Generation
├── prereqs/                            # Required reading for all auditors
│   ├── 00_MANDATORY-PREREQS.md         # Reading list
│   ├── SESSION-AND-TENANT-LAW.md       # RLS canonical law
│   ├── WORKFLOW-RLS-REGISTRY.yaml      # Pattern allowlist
│   ├── CRITICAL_PATTERNS.md            # 29 architectural patterns
│   └── [other reference docs...]
├── audits/                             # Completed audit outputs
│   └── WO-XXX-Audit/                   # One directory per work order
│       ├── WO-XXX.md                   # Work order (moved here)
│       ├── compliance-test-orchestrator.md  # Drag this for Phase 2
│       ├── _STATUS.yaml                # Progress tracking
│       ├── *-findings.md               # 6 findings files
│       └── VERDICT.md                  # Final recommendation
└── work-orders/                        # Staging area for work orders
```

---

## Integration with Claude Code

### Agent Registration

The auditor agents are designed to work with Claude Code's Task tool. When properly registered in the subagent configuration, you can invoke them directly:

```
Task(subagent_type="audit-01-architect", prompt="Audit WO-XXX...")
```

**Note**: Agents must be registered in Claude Code's configuration to use direct invocation. The orchestrator falls back to `general-purpose` if a specific agent isn't registered.

### Parallel Execution

The orchestrator spawns all 6 agents simultaneously using:

```
run_in_background: true
```

This allows parallel execution while the orchestrator monitors `_STATUS.yaml` for completion.

---

## Real Results: WO-WF10-PHASE3.4

Our first full audit cycle (2026-01-02) found:

### Infrastructure Issues
- `companies` table doesn't exist (FK references fail)
- LangChain not in requirements.txt (ModuleNotFoundError)
- OPENAI_API_KEY not configured (crash on startup)

### Code Pattern Violations
- Wrong import: `src.db.rls` (file doesn't exist)
- Raw SQL violates ORM mandate
- Wrong session pattern: `db.fetch_all()` (method doesn't exist)
- File naming: `company_router.py` (requires `wf10_` prefix)
- Router not registered in main.py (404 on all endpoints)

### Concurrency & Scale Issues
- Blocking LangChain `__init__` (event loop blocked)
- Connection held during AI call (pool exhaustion)
- No rate limiting (cost explosion risk)

### Security Issues
- **SEC-002**: `SET ROLE` without `RESET ROLE` in production code
- AI-generated SQL execution risk
- Incomplete RLS policies (missing WITH CHECK)

### Observability Issues
- No tenant_id in logs
- AI Chat silent failures

### Test Coverage Issues
- Only 3 tests provided (56+ required)
- Missing multi-tenant fixtures
- No error case tests
- No concurrency tests

**Result**: Work order BLOCKED, SEC-002 fixed same day, work order revised with all issues addressed.

---

## Best Practices

### For Work Order Authors

1. **Read the Prerequisites First** - If you understand SESSION-AND-TENANT-LAW.md, fewer surprises
2. **Include Infrastructure** - Document what tables/columns must exist
3. **Show Complete Imports** - Use real import paths from the codebase
4. **Follow Naming Conventions** - `wfX_` prefix, proper casing
5. **Specify Test Requirements** - What categories, how many tests

### For Auditors

1. **Complete Required Reading** - No exceptions
2. **Verify Before Reporting** - Check the registry first
3. **Cite the Law** - Every finding references a document
4. **Provide Remediation** - Don't just complain, show the fix
5. **Be Adversarial, Not Antagonistic** - Find real issues, not nitpicks

### For Reviewers

1. **Start with VERDICT.md** - Get the summary first
2. **Focus on BLOCKERS** - These must be fixed
3. **Check for False Positives** - Verify against registry
4. **Track Remediation** - Mark issues as fixed in the work order

---

## FAQ

### Q: How long does an audit take?

**A**: Typically 10-20 minutes for all 6 agents to complete. Complex work orders may take longer.

### Q: Can I run a single auditor instead of all 6?

**A**: Yes, invoke the specific agent directly with the Task tool. However, the full audit provides the most value.

### Q: What if an agent finds a false positive?

**A**: This usually means the registry needs updating. Document the intentional pattern in WORKFLOW-RLS-REGISTRY.yaml.

### Q: Can I audit existing code, not just work orders?

**A**: Yes, point the auditor at any file path. The kit works best with work orders but can audit any code.

### Q: How do I add a new auditor?

**A**: Create a new persona file in `agents/`, update the orchestrator to spawn it, and document its focus areas.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-01 | Initial release with 6 auditors |
| 1.0.1 | 2026-01-02 | First production audit (WO-WF10-PHASE3.4), fixed SEC-002 |
| 2.0 | 2026-01-02 | Added Phase 2: Compliance Test Generator (7th agent) |

---

## Credits

Created for ScraperSky Backend to catch architectural violations before they reach production.

*"The best time to find a bug is before you write the code. The second best time is during adversarial audit."*
