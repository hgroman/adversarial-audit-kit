# Adversarial Audit Kit

A multi-agent adversarial code review system that finds what humans miss.

---

## What This Is

The Adversarial Audit Kit deploys **6 specialized AI auditors** in parallel to stress-test work orders before implementation. Each auditor brings a different adversarial lens:

| Auditor | Codename | Hunts For |
|---------|----------|-----------|
| **Architect** | Structure Breaker | Circular imports, layer violations, dead code, god files |
| **DevOps** | Build Saboteur | Missing dependencies, broken Docker builds, unregistered routers |
| **Data Assassin** | Security Predator | RLS bypasses, tenant leaks, role mismanagement |
| **Kraken** | Concurrency Crusher | Connection pool exhaustion, blocking I/O, race conditions |
| **Operator** | 2AM Nightmare | Missing logs, silent failures, unobservable errors |
| **Test Sentinel** | Coverage Hunter | Missing test categories, untestable code, fixture gaps |

Each auditor reads the same prerequisite documents (the architectural "law"), then attacks the work order from their specialty. Findings are classified as **BLOCKER**, **WARNING**, or **ADVISORY**.

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

### Step 1: Drag and Drop

Drag `adversarial-audit-orchestrator.md` into your Claude Code chat, then provide the work order path:

```
Audit: 00_Current_Architecture/05_Active_Work/WO-MY-FEATURE.md
```

### Step 2: Wait

The orchestrator:
1. Creates `WO-MY-FEATURE-Audit/` directory
2. Spawns 6 auditors in parallel
3. Monitors completion
4. Produces `VERDICT.md` with deployment recommendation

### Step 3: Review Verdict

```
Adversarial-Audit-Kit/
  audits/
    WO-MY-FEATURE-Audit/
      WO-MY-FEATURE.md      # Your work order (moved here)
      _STATUS.yaml          # Audit progress
      ARCH-findings.md      # Architect findings
      DEVOPS-findings.md    # DevOps findings
      SEC-findings.md       # Security findings
      KRAKEN-findings.md    # Concurrency findings
      OPS-findings.md       # Observability findings
      TEST-findings.md      # Test coverage findings
      VERDICT.md            # Final recommendation
```

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

## The 6 Auditors

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
├── adversarial-audit-orchestrator.md   # Main orchestrator (drag into chat)
├── agents/                             # The 6 auditor personas
│   ├── audit-01-architect.md
│   ├── audit-02-devops.md
│   ├── audit-03-data-assassin.md
│   ├── audit-04-kraken.md
│   ├── audit-05-operator.md
│   └── audit-06-test-sentinel.md
├── prereqs/                            # Required reading for all auditors
│   ├── 00_MANDATORY-PREREQS.md         # Reading list
│   ├── SESSION-AND-TENANT-LAW.md       # RLS canonical law
│   ├── WORKFLOW-RLS-REGISTRY.yaml      # Pattern allowlist
│   ├── CRITICAL_PATTERNS.md            # 29 architectural patterns
│   └── [other reference docs...]
├── audits/                             # Completed audit outputs
│   └── WO-XXX-Audit/                   # One directory per work order
│       ├── WO-XXX.md                   # Work order (moved here)
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

---

## Credits

Created for ScraperSky Backend to catch architectural violations before they reach production.

*"The best time to find a bug is before you write the code. The second best time is during adversarial audit."*
