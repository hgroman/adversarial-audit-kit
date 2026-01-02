# Troubleshooting Guide

Solutions to common issues when running adversarial audits.

---

## Agent Won't Start

### Symptom
```
Error: Agent type 'audit-06-test-sentinel' not found
```

### Cause
The agent isn't registered in Claude Code's subagent configuration.

### Solution
1. **Immediate workaround**: Use `general-purpose` agent instead:
   ```
   Task(subagent_type="general-purpose", prompt="[paste agent persona content]...")
   ```

2. **Permanent fix**: Register the agent in your Claude Code configuration (see agent registration docs)

### Why This Happens
Claude Code loads agent definitions at startup. If agents were added after the session started, they won't be available until restart.

---

## Agent Produces No Findings

### Symptom
Findings file contains only headers, no actual findings.

### Possible Causes

**1. Agent didn't complete mandatory reading**
- Check if the agent acknowledged the prereqs
- Look for "Required reading complete" in agent output

**2. Work order has no issues in that domain**
- A clean findings file is valid for well-written work orders
- Verify by checking if other auditors found issues

**3. Agent timeout**
- Check `_STATUS.yaml` for `status: timeout`
- Re-run the specific agent with more time

### Solution
Re-run the specific auditor with explicit instructions:
```
Read all prereqs in Adversarial-Audit-Kit/prereqs/, then audit [work order path]
```

---

## False Positives

### Symptom
Auditor flags something as VIOLATION that's actually an intentional pattern.

### Example
```
VIOLATION: job_service.py uses with_tenant_context internally
```
But `job_service.py` is documented as a self-enforcing service.

### Cause
The pattern isn't in `WORKFLOW-RLS-REGISTRY.yaml`, or the auditor didn't read the registry.

### Solution

**1. Verify it's actually intentional**
```bash
grep -A 10 "job_service" prereqs/WORKFLOW-RLS-REGISTRY.yaml
```

**2. If missing, add to registry**
```yaml
# In WORKFLOW-RLS-REGISTRY.yaml
exceptions:
  self_enforcing_services:
    - path: src/services/job_service.py
      reason: "Self-enforcing service - sets own tenant context"
      documented_in: SESSION-AND-TENANT-LAW.md
```

**3. Re-run the audit**
The pattern should now be recognized as INTENTIONAL_PATTERN.

---

## Audit Takes Too Long

### Symptom
Agents running for 30+ minutes without completing.

### Possible Causes

**1. Large work order**
- Work orders over 500 lines take longer to analyze

**2. Complex codebase checks**
- Some verification commands are expensive (e.g., grep across entire repo)

**3. Agent stuck in loop**
- Agent may be re-reading files or repeating checks

### Solutions

**1. Check progress**
```bash
cat 05_Active_Work/WO-XXX-Audit/_STATUS.yaml
```
See which agents are still `in_progress`.

**2. Use timeouts**
The orchestrator has built-in timeout handling:
- 10 min: Warning logged
- 30 min: Agent marked as timeout, proceed with available findings

**3. Run agents sequentially**
If parallel execution is problematic:
```
Task(subagent_type="audit-01-architect", run_in_background=false, ...)
```

---

## VERDICT.md Not Generated

### Symptom
All 6 findings files exist, but no VERDICT.md.

### Cause
The orchestrator didn't reach Phase 4 (aggregation).

### Solution

**1. Check status**
```bash
cat 05_Active_Work/WO-XXX-Audit/_STATUS.yaml
```
Look for `all_complete: true`.

**2. Manual aggregation**
If all agents completed but verdict wasn't generated:
```
Read all 6 findings files in WO-XXX-Audit/, aggregate findings,
and produce VERDICT.md with deployment recommendation.
```

---

## Agent Finds Issue in Production Code

### Symptom
Auditor finds a violation in existing production code, not the work order.

### Example (Real: 2026-01-02)
```
SEC-002: wf10_signal_router.py:109-120
SET ROLE without RESET ROLE - role leak vulnerability
```

### This Is Actually Good
The adversarial audit found a real production bug while auditing a work order.

### Action
1. **Fix immediately** - Production security issues take priority
2. **Document in VERDICT.md** - Note that existing code was also fixed
3. **Update work order** - Reference the fix

### Example Fix
```python
# Before (vulnerable)
find_stmt = text("SELECT tenant_id FROM ...")
res = await session.execute(find_stmt, {"id": signal_id})

# After (fixed)
await session.execute(text("SET ROLE postgres"))
try:
    find_stmt = text("SELECT tenant_id FROM ...")
    res = await session.execute(find_stmt, {"id": signal_id})
finally:
    await session.execute(text("RESET ROLE"))
```

---

## Conflicting Findings

### Symptom
Two auditors disagree about the same code.

### Example
```
ARCH-003: Raw SQL is appropriate here
SEC-001: Raw SQL violates ORM mandate
```

### Resolution Process

**1. Check the law hierarchy**
```
SESSION-AND-TENANT-LAW.md > ADRs > Pattern Guides
```
Higher authority wins.

**2. Check for exceptions**
Some patterns have documented exceptions (e.g., WF9 Vector Search uses raw SQL).

**3. Use judgment**
If the law is genuinely ambiguous:
- Document the conflict in VERDICT.md
- Recommend clarifying the law
- Choose the safer option (usually the security auditor's recommendation)

---

## Audit Directory Already Exists

### Symptom
```
Error: WO-XXX-Audit/ already exists
```

### Cause
Previous audit was run on this work order.

### Solutions

**1. Review existing audit**
If the previous audit is still relevant, use those findings.

**2. Archive and re-run**
```bash
mv WO-XXX-Audit/ WO-XXX-Audit-$(date +%Y%m%d)/
# Then run new audit
```

**3. Re-audit in place**
Some orchestrators allow `--force` to overwrite existing findings.

---

## Prereq Files Not Found

### Symptom
```
Error: prereqs/SESSION-AND-TENANT-LAW.md not found
```

### Cause
The audit kit was moved or prereq files weren't copied.

### Solution

**1. Verify prereqs exist**
```bash
ls Adversarial-Audit-Kit/prereqs/
```

**2. If missing, restore from repo**
```bash
git checkout -- Adversarial-Audit-Kit/prereqs/
```

**3. Update paths in agent prompts**
If the kit was relocated, update the prereq paths in agent definitions.

---

## Rate Limiting from External Verification

### Symptom
Agents get rate-limited when verifying against external systems.

### Example
- Too many GitHub API calls
- Docker Hub rate limiting
- Package registry throttling

### Solutions

**1. Use cached results**
Pre-fetch and cache dependency information.

**2. Reduce verification depth**
Skip external checks, focus on local analysis:
```
Audit locally only - do not make external API calls
```

**3. Spread over time**
Run agents sequentially instead of parallel to reduce burst load.

---

## Memory/Context Exhaustion

### Symptom
Agent stops mid-audit with context length error.

### Cause
Large codebases or verbose prereq files exceed context window.

### Solutions

**1. Summarize prereqs**
Create condensed versions of large prereq files.

**2. Scope the audit**
Focus on specific files rather than entire codebase:
```
Audit only the files mentioned in the work order
```

**3. Split the audit**
Run multiple focused audits instead of one comprehensive one:
```
Audit WO-XXX for security only (Data Assassin)
Audit WO-XXX for architecture only (Architect)
```

---

## Getting Help

If none of these solutions work:

1. **Check the agent output** - Full logs often reveal the issue
2. **Inspect _STATUS.yaml** - Shows exactly where things went wrong
3. **Run a single agent** - Isolate the problem to one auditor
4. **Ask for human review** - Some edge cases need human judgment

---

*Remember: The goal is to find real issues, not to have a perfect audit process. A partial audit with actionable findings is better than no audit.*
