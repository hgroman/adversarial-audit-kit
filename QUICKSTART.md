# Quickstart: Your First Adversarial Audit

Get from zero to audit results in 5 minutes. Generate compliance tests in 2 more.

---

## Prerequisites

- Claude Code CLI installed and running
- Access to the ScraperSky repository
- A work order to audit (any `.md` file in `05_Active_Work/`)

---

## Step 1: Open Claude Code

```bash
cd /path/to/scraper-sky-backend
claude
```

---

## Step 2: Start the Audit

**Option A: Drag and Drop**

Drag `Adversarial-Audit-Kit/adversarial-audit-orchestrator.md` into your chat window, then type:

```
Audit: 00_Current_Architecture/05_Active_Work/WO-YOUR-FEATURE.md
```

**Option B: Direct Command**

```
Run adversarial audit on 00_Current_Architecture/05_Active_Work/WO-YOUR-FEATURE.md
```

---

## Step 3: Watch the Magic

The orchestrator will:

```
[1/4] Creating audit directory...
      Created: 05_Active_Work/WO-YOUR-FEATURE-Audit/

[2/4] Spawning 6 auditors in parallel...
      - Architect (ARCH-findings.md)
      - DevOps (DEVOPS-findings.md)
      - Data Assassin (SEC-findings.md)
      - Kraken (KRAKEN-findings.md)
      - Operator (OPS-findings.md)
      - Test Sentinel (TEST-findings.md)

[3/4] Monitoring for completion...
      Architect: complete
      DevOps: complete
      Data Assassin: complete
      Kraken: complete
      Operator: complete
      Test Sentinel: complete

[4/4] Producing VERDICT.md...
      Done!
```

---

## Step 4: Review the Verdict

Navigate to the audit directory:

```bash
ls 00_Current_Architecture/05_Active_Work/WO-YOUR-FEATURE-Audit/
```

You'll see:
```
WO-YOUR-FEATURE.md                 # Your work order (moved here)
compliance-test-orchestrator.md    # For Phase 2 (drag after implementation)
_STATUS.yaml                       # Audit status
ARCH-findings.md                   # Architect findings
DEVOPS-findings.md                 # DevOps findings
SEC-findings.md                    # Security findings
KRAKEN-findings.md                 # Concurrency findings
OPS-findings.md                    # Observability findings
TEST-findings.md                   # Test coverage findings
VERDICT.md                         # THE FINAL WORD
```

**Start with `VERDICT.md`** - it aggregates all findings and gives you the deployment recommendation.

---

## Phase 2: Generate Compliance Tests

*After you've implemented the fixes...*

### Step 5: Generate Tests

Drag `compliance-test-orchestrator.md` **from the audit folder** into chat:

```
Generate compliance tests
```

The 7th agent (Compliance Test Generator) reads all findings and produces a pytest file.

### Step 6: Run Tests

```bash
pytest tests/compliance/test_your_feature_compliance.py -v
```

### Step 7: Add to CI

```yaml
# .github/workflows/compliance.yml
- name: Compliance Tests
  run: pytest tests/compliance/ -v --tb=short
```

These tests run forever, preventing the same violations from returning.

---

## Understanding Your Verdict

### GO

```markdown
## DEPLOYMENT RECOMMENDATION: GO

No blockers found. Safe to implement.
```

You're clear to proceed with implementation.

### CONDITIONAL GO

```markdown
## DEPLOYMENT RECOMMENDATION: CONDITIONAL GO

Fix 3 blockers before deploy:
1. SEC-001: Missing RESET ROLE
2. ARCH-002: Wrong import path
3. DEVOPS-003: Missing dependency
```

Fix the listed items, then implement.

### BLOCKED

```markdown
## DEPLOYMENT RECOMMENDATION: BLOCKED

Fundamental issues require work order revision:
- Assumes infrastructure that doesn't exist
- Uses patterns that violate architectural law
```

Revise the work order and re-audit.

---

## What's Next?

| Goal | Action |
|------|--------|
| Understand all findings | Read individual `*-findings.md` files |
| Fix issues | Address items in order of severity (BLOCKER > WARNING > ADVISORY) |
| Re-audit after fixes | Run the audit again on the revised work order |
| Generate compliance tests | Drag `compliance-test-orchestrator.md` from audit folder (Phase 2) |
| Learn more | Read the full [README.md](README.md) |
| Troubleshoot | See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |

---

## Common First-Audit Questions

### "Why are there so many findings?"

The auditors are adversarial by design. They assume the worst. Some findings may be false positives if the registry hasn't been updated with your intentional patterns.

### "What if I disagree with a finding?"

Check if the pattern is documented in `prereqs/WORKFLOW-RLS-REGISTRY.yaml`. If it's an intentional pattern that looks like a violation, add it to the registry.

### "Do I have to fix everything?"

- **BLOCKERS**: Yes, before implementation
- **WARNINGS**: Should fix, judgment call on timing
- **ADVISORY**: Nice to have, implement if time permits

### "How do I know when I'm done fixing?"

Re-run the audit. When the verdict is GO, you're done.

---

## Pro Tips

1. **Read VERDICT.md first** - It's the executive summary
2. **Focus on BLOCKERS** - They're blocking for a reason
3. **Check the registry** - Some "violations" are intentional patterns
4. **Fix in batches** - Group related issues, commit together
5. **Re-audit after fixes** - Verify your fixes actually fixed things

---

*Total time: 5 minutes to audit, rest depends on how many issues found.*
