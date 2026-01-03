# Compliance Test Generator

**Transform audit findings into executable truth.**

---

## What This Is

The Compliance Test Generator is the **second phase** of the adversarial audit process. It takes the findings from all 6 auditors and transforms them into a pytest test suite that:

1. **Encodes each finding** as an executable test
2. **Cites the architectural law** being verified
3. **Detects violation patterns** automatically
4. **Runs in CI forever** - preventing regression

**A finding is an opinion. A passing test is a fact.**

---

## The Two-Phase Audit Process

```
PHASE 1: ADVERSARIAL AUDIT (Pre-Implementation)
┌─────────────────────────────────────────────────────────┐
│  Work Order → 6 Auditors → Findings → VERDICT          │
│                                                         │
│  Output: "Here's what's wrong and why"                  │
└─────────────────────────────────────────────────────────┘
                          ↓
PHASE 2: COMPLIANCE TESTS (Post-Implementation)
┌─────────────────────────────────────────────────────────┐
│  Findings → Test Generator → pytest suite               │
│                                                         │
│  Output: "Here's how to prove it's fixed"               │
└─────────────────────────────────────────────────────────┘
                          ↓
CONTINUOUS: CI/CD
┌─────────────────────────────────────────────────────────┐
│  pytest tests/compliance/ → Pass/Fail → Deploy/Block   │
│                                                         │
│  Output: "It stays fixed forever"                       │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

1. Complete an adversarial audit first:
   ```
   Adversarial-Audit-Kit/adversarial-audit-orchestrator.md
   ```

2. Have the audit directory with all 6 findings files:
   ```
   WO-XXX-Audit/
   ├── ARCH-findings.md
   ├── DEVOPS-findings.md
   ├── SEC-findings.md
   ├── KRAKEN-findings.md
   ├── OPS-findings.md
   ├── TEST-findings.md
   └── VERDICT.md
   ```

### Generate Tests

Drag `compliance-test-orchestrator.md` into Claude Code chat:

```
Generate compliance tests for 05_Active_Work/WO-WF10-PHASE3.4-Audit/
```

### Output

```
tests/compliance/test_wf10_phase34_compliance.py
```

### Run Tests

```bash
pytest tests/compliance/test_wf10_phase34_compliance.py -v
```

---

## What Gets Generated

For each VIOLATION finding, the generator creates tests that:

| Finding | Becomes Test That... |
|---------|---------------------|
| ARCH-001: Wrong import | Scans for bad import patterns |
| SEC-002: Missing RESET ROLE | Verifies all SET ROLE have RESET |
| DEVOPS-003: Missing dependency | Checks requirements.txt |
| KRAKEN-001: Blocking __init__ | Finds blocking calls in constructors |
| OPS-001: No tenant in logs | Verifies log statements have context |
| TEST-001: Low coverage | Counts test files per workflow |

### Example Generated Test

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
            set_count = content.count("SET ROLE")
            reset_count = content.count("RESET ROLE")

            if set_count > reset_count:
                violations.append(f"{py_file}: {set_count} SET, {reset_count} RESET")

        assert violations == [], (
            f"Role leak vulnerability:\n"
            f"{chr(10).join(violations)}\n"
            f"LAW: Every SET ROLE must have RESET ROLE in finally block."
        )
```

---

## Test Categories

Tests are organized by auditor domain:

| Class | Covers | Example Checks |
|-------|--------|----------------|
| `TestArchitecturalCompliance` | ARCH-* | Layer violations, imports, naming |
| `TestSecurityCompliance` | SEC-* | RLS, tenant isolation, role management |
| `TestBuildCompliance` | DEVOPS-* | Dependencies, registration, Docker |
| `TestConcurrencyCompliance` | KRAKEN-* | Connection pools, blocking I/O |
| `TestObservabilityCompliance` | OPS-* | Logging, error handling |
| `TestCoverageCompliance` | TEST-* | Test counts, fixtures |

---

## CI Integration

Add to your GitHub workflow:

```yaml
# .github/workflows/compliance.yml
name: Compliance Tests

on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pytest

      - name: Run Compliance Tests
        run: pytest tests/compliance/ -v --tb=short
```

---

## Why This Matters

### Before: Findings Decay

```
Day 1: Audit finds 21 violations
Day 7: Developer fixes issues
Day 30: New code reintroduces 3 violations
Day 60: Nobody remembers the audit
Day 90: Same violations in production
```

### After: Tests Prevent Regression

```
Day 1: Audit finds 21 violations → 21 tests generated
Day 7: Developer fixes issues → all tests pass
Day 30: New code fails 3 tests → PR blocked
Day 60: Tests still running
Day 90: Violations impossible to merge
```

**Tests are permanent. Findings files are forgotten.**

---

## Directory Structure

```
Compliance-Test-Generator/
├── README.md                         # This file
├── compliance-test-orchestrator.md   # Main prompt (drag into chat)
├── agents/
│   └── test-generator.md             # Test generation persona
├── templates/
│   └── test_template.py              # Base test structure
└── output/
    └── [generated test files]
```

---

## Relationship to Adversarial Audit Kit

```
Adversarial-Audit-Kit/          ← PHASE 1: Find violations
  └── Produces: *-findings.md

Compliance-Test-Generator/       ← PHASE 2: Prove compliance
  └── Produces: test_*_compliance.py

tests/compliance/               ← PHASE 3: Run forever
  └── Runs in: CI/CD
```

**Both kits work together. Neither replaces the other.**

- Adversarial Audit: Finds issues in work orders BEFORE implementation
- Compliance Tests: Verifies fixes and prevents regression AFTER implementation

---

## Best Practices

### For Test Generation

1. **Run after audit completes** - All 6 findings files must exist
2. **Review generated tests** - Verify they test what they claim
3. **Add to CI immediately** - Tests only work if they run
4. **Don't modify generated tests** - Regenerate instead

### For Test Maintenance

1. **Regenerate on re-audit** - New audit = new tests
2. **Keep old tests** - Unless findings are resolved
3. **Document intentional failures** - Some tests may be skipped with reason

---

## FAQ

### Q: What if a finding is INTENTIONAL?

Tests are only generated for VIOLATION findings. INTENTIONAL patterns are documented in the test file header but don't get tests.

### Q: What if the tests fail?

That means the violations still exist. Fix the code, not the tests.

### Q: Can I edit the generated tests?

You can, but it's better to regenerate. If the test is wrong, the finding description or detection logic needs improvement.

### Q: How long do tests take to run?

Target: < 30 seconds for the entire compliance suite. Tests that need more time should be marked `@pytest.mark.slow`.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-02 | Initial release |

---

*"The audit finds the problems. The tests prove they're solved. CI keeps them solved."*
