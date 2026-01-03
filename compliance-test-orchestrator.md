# COMPLIANCE TEST ORCHESTRATOR

**Transform audit findings into executable truth.**

Drag this file into Claude Code chat to generate compliance tests. When dragged from an audit folder, it automatically reads findings from the same directory.

---
name: compliance-test-orchestrator
description: |
  Reads adversarial audit findings from the same directory, cross-references architectural laws, and generates a pytest test suite that verifies implementation compliance. Each finding becomes one or more tests. Tests run in CI forever, preventing regression.
tools: Read, Write, Glob, Grep, Bash
---

## ACTIVATION

This file is placed in each audit folder by the adversarial-audit-orchestrator.

**When dragged into chat:**
1. Detect the directory this file was dragged from
2. That directory IS the audit folder containing all findings
3. Read findings from same directory (sibling files)

**EXECUTE IMMEDIATELY. DO NOT ASK FOR PERMISSION.**

---

## PHASE 1: VALIDATE INPUTS

### 1.1 Determine Audit Directory

When this file is dragged from an audit folder, the audit directory is the SAME folder this file is in.

```bash
# The audit directory is where this file lives
# Look for sibling files: VERDICT.md, *-findings.md
AUDIT_DIR="."  # Current context when dragged

ls ./
# Must contain:
# - ARCH-findings.md
# - DEVOPS-findings.md
# - SEC-findings.md
# - KRAKEN-findings.md
# - OPS-findings.md
# - TEST-findings.md
# - VERDICT.md
```

**If any findings file is missing, STOP and report.**

### 1.2 Read the Verdict

```bash
cat ./VERDICT.md
```

Extract:
- Total finding counts by severity
- List of all finding IDs
- Deployment recommendation

---

## PHASE 2: INGEST ALL FINDINGS

### 2.1 Read Each Findings File

```bash
cat $AUDIT_DIR/ARCH-findings.md
cat $AUDIT_DIR/DEVOPS-findings.md
cat $AUDIT_DIR/SEC-findings.md
cat $AUDIT_DIR/KRAKEN-findings.md
cat $AUDIT_DIR/OPS-findings.md
cat $AUDIT_DIR/TEST-findings.md
```

### 2.2 Parse Findings

For each finding, extract:

```yaml
- id: ARCH-001
  severity: BLOCKER
  location: src/routers/company_router.py:15
  pattern: "Wrong import path: src.db.rls"
  law: "SESSION-AND-TENANT-LAW.md §Imports"
  verdict: VIOLATION
  remediation: "Use src.db.tenant_context instead"
```

### 2.3 Filter Findings

- **VIOLATION** → Generate test
- **INTENTIONAL** → Document in test file header, no test
- **FALSE_ALARM** → Skip entirely

---

## PHASE 3: LOAD THE LAWS

### 3.1 Required Law Reading

```bash
cat 00_Current_Architecture/00_The_Law/SESSION-AND-TENANT-LAW.md
cat 00_Current_Architecture/00_The_Law/ADR-001-Supavisor-Requirements.md
cat 00_Current_Architecture/00_The_Law/ADR-007-RLS-TENANT-CONTEXT-PATTERN.md
cat 00_Current_Architecture/00_The_Law/SQLALCHEMY-PATTERNS-LAW.md
```

### 3.2 Cross-Reference

For each finding, identify:
- Which law section it violates
- The exact rule text
- The correct pattern

---

## PHASE 4: GENERATE TEST SUITE

### 4.1 Create Test File

```python
# tests/compliance/test_{wo_name}_compliance.py

"""
Compliance Test Suite: {Work Order Name}

Generated: {ISO timestamp}
Audit Source: {audit_dir}
Verdict: {GO|CONDITIONAL GO|BLOCKED}

This test suite verifies implementation compliance with all VIOLATION
findings from the adversarial audit. Each test encodes a specific
architectural law and detects the corresponding violation pattern.

VIOLATIONS COVERED ({count}):
{list of finding IDs and descriptions}

INTENTIONAL PATTERNS SKIPPED ({count}):
{list of intentional findings with reasons}

RUN: pytest tests/compliance/test_{wo_name}_compliance.py -v
"""

import ast
import re
from pathlib import Path
import pytest

# === STRUCTURAL COMPLIANCE ===
class TestArchitecturalCompliance:
    """Tests for ARCH-* findings."""
    # ... generated tests ...

# === SECURITY COMPLIANCE ===
class TestSecurityCompliance:
    """Tests for SEC-* findings."""
    # ... generated tests ...

# === BUILD COMPLIANCE ===
class TestBuildCompliance:
    """Tests for DEVOPS-* findings."""
    # ... generated tests ...

# === CONCURRENCY COMPLIANCE ===
class TestConcurrencyCompliance:
    """Tests for KRAKEN-* findings."""
    # ... generated tests ...

# === OBSERVABILITY COMPLIANCE ===
class TestObservabilityCompliance:
    """Tests for OPS-* findings."""
    # ... generated tests ...

# === COVERAGE COMPLIANCE ===
class TestCoverageCompliance:
    """Tests for TEST-* findings."""
    # ... generated tests ...
```

### 4.2 Test Generation Rules

**For each VIOLATION finding:**

1. **Identify the violation pattern** - What code/structure indicates the problem?
2. **Write detection logic** - How to find this pattern programmatically?
3. **Assert compliance** - Test fails if pattern found, passes if clean
4. **Write actionable error** - Tell exactly what's wrong and how to fix

### 4.3 Test Quality Checklist

Every generated test must:

- [ ] Have a docstring citing LAW and FINDING
- [ ] Be deterministic (no randomness, no timing)
- [ ] Run fast (< 1 second unless `@pytest.mark.slow`)
- [ ] Be independent (no test order dependencies)
- [ ] Have informative assertion messages

---

## PHASE 5: VERIFY TESTS

### 5.1 Syntax Check

```bash
python -m py_compile tests/compliance/test_{wo_name}_compliance.py
```

### 5.2 Collect Tests

```bash
pytest tests/compliance/test_{wo_name}_compliance.py --collect-only
```

**Expected:** Each VIOLATION finding has at least one test collected.

### 5.3 Dry Run (if implementation exists)

```bash
pytest tests/compliance/test_{wo_name}_compliance.py -v --tb=short
```

---

## PHASE 6: REPORT

### 6.1 Summary Output

```markdown
# Compliance Test Generation Complete

**Work Order:** {name}
**Audit Source:** {audit_dir}
**Generated:** {timestamp}

## Tests Generated

| Category | Findings | Tests | Coverage |
|----------|----------|-------|----------|
| ARCH | 3 | 5 | 100% |
| SEC | 2 | 4 | 100% |
| DEVOPS | 4 | 6 | 100% |
| KRAKEN | 2 | 3 | 100% |
| OPS | 2 | 2 | 100% |
| TEST | 1 | 2 | 100% |
| **TOTAL** | **14** | **22** | **100%** |

## Output File

`tests/compliance/test_{wo_name}_compliance.py`

## Run Tests

```bash
pytest tests/compliance/test_{wo_name}_compliance.py -v
```

## What These Tests Verify

1. **ARCH-001**: No wrong import paths (src.db.rls → src.db.tenant_context)
2. **SEC-002**: Every SET ROLE has RESET ROLE in finally block
3. **DEVOPS-003**: All imports have requirements.txt entries
...

## CI Integration

Add to your workflow:

```yaml
- name: Compliance Tests
  run: pytest tests/compliance/ -v --tb=short
```
```

---

## SUCCESS CRITERIA

- [ ] All 6 findings files read successfully
- [ ] Every VIOLATION finding has at least one test
- [ ] Test file passes syntax check
- [ ] Test file collects without errors
- [ ] Tests are fast (< 30 seconds total)
- [ ] Error messages cite laws and provide fixes
- [ ] Test file is self-documenting

---

## FAILURE RECOVERY

### If Findings File Missing

```
ERROR: {AUDIT_DIR}/SEC-findings.md not found

The audit appears incomplete. Please run the full adversarial audit first:
  - Drag adversarial-audit-orchestrator.md into chat
  - Provide the work order path
  - Wait for all 6 auditors to complete
```

### If No VIOLATION Findings

```
INFO: No VIOLATION findings to test.

All findings were either INTENTIONAL or FALSE_ALARM.
No compliance test suite needed for this work order.
```

### If Test Generation Fails

```
ERROR: Could not generate test for {finding_id}

Finding: {description}
Reason: {why generation failed}

Manual test creation may be required. The compliance-test-generator agent
has embedded templates for all 6 test categories.
```

---

## INTEGRATION WITH ADVERSARIAL AUDIT

This orchestrator is the **second phase** of the audit process:

```
┌─────────────────────────────────────────────────────────────┐
│                    ADVERSARIAL AUDIT KIT                     │
│  Work Order → 6 Auditors → Findings.md → VERDICT.md         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 COMPLIANCE TEST GENERATOR                    │
│  Findings.md → Test Generator → test_compliance.py          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                         CI/CD                                │
│  pytest tests/compliance/ → Pass/Fail → Block/Allow Deploy  │
└─────────────────────────────────────────────────────────────┘
```

**The audit finds issues. The tests prove they're fixed. CI prevents regression.**

---

## EXAMPLE USAGE

```
User: Generate compliance tests for 05_Active_Work/WO-WF10-PHASE3.4-Audit/