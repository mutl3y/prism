# Wave 3: Consistency and Polish

**Wave ID:** wave_3
**Priority:** LOW
**Findings:** FIND-05, FIND-07, FIND-09
**Estimated Effort:** 2.5h total

---

## Overview

Wave 3 addresses 3 low-severity findings that represent minor design concerns and consistency issues. These have minimal runtime impact but improve long-term code quality.

---

## FIND-05: CacheKeyProtocol Convention Mismatch

### Problem

`CacheKeyProtocol` in `contracts_request.py` defines a `__cache_key__` dunder method that Python's standard library doesn't recognize. Objects implementing this can't be used directly with `dict`, `frozenset`, or `lru_cache` without wrapping.

### Remediation

**Option A (Recommended):** Document as internal convention, not a Protocol

Change from:

```python
@runtime_checkable
class CacheKeyProtocol(Protocol):
    def __cache_key__(self) -> str: ...
```

To:

```python
# Internal convention for cache key generation.
# Classes implementing this should define __cache_key__(self) -> str.
# This is NOT a runtime_checkable Protocol because __cache_key__ is not
# recognized by Python's standard library cache types.
CacheKeyConvention = Callable[[], str]
```

**Rationale:**
- Removes false promise of `isinstance()` checks
- Documents the convention without over-engineering
- Call sites that need cache keys can use `hasattr(obj, "__cache_key__")` or structural typing

**Test:** None required (documentation change only).

---

## FIND-07: Redundant Locking in Event Bus

### Problem

`EventBus` in `events.py` uses both `ContextVar` (for context isolation) and `threading.Lock` (for listener list protection). The lock may be unnecessary if listeners are registered at startup and never modified at runtime.

### Remediation

**Audit and simplify:**

1. Add comment documenting listener mutation policy:
   ```python
   # Listener list is append-only after module load.
   # No runtime registration supported; lock protects against
   # concurrent test fixture modifications only.
   _listeners: deque[EventListener] = deque()
   _listener_lock = threading.Lock()
   ```

2. If tests are the only mutators, consider using a reentrant lock or removing the lock in favor of test isolation via `ContextVar`.

3. Profile: measure lock acquisition overhead in hot path (should be negligible, but verify).

**Test:** Run `test_t3_01_scan_phase_events.py` under thread sanitizer if available.

---

## FIND-09: Inconsistent Naming Conventions

### Problem

Exit code constants in `cli.py` have inconsistent underscore prefixes:

```python
_EXIT_CODE_GENERIC_ERROR = 2
_EXIT_CODE_NOT_FOUND = 3
EXIT_CODE_AUDIT_VIOLATIONS = 8  # Missing leading underscore
```

### Remediation

**Standardize on private prefix:**

```python
_EXIT_CODE_GENERIC_ERROR = 2
_EXIT_CODE_NOT_FOUND = 3
_EXIT_CODE_AUDIT_VIOLATIONS = 8
_EXIT_CODE_PERMISSION_DENIED = 4
# ... all others with leading underscore
```

**Add ruff rule to enforce:**

In `pyproject.toml` or `setup.cfg`:

```toml
[tool.ruff.lint]
extend-select = ["N806"]  # Uppercase variable names should be const
```

Or add a project-specific convention note in `AGENTS.md`.

**Test:** `ruff check src/prism/cli.py` passes with new rule.

---

## Wave 3 Execution Notes

**All 3 findings are independent** — can be addressed in parallel or sequentially with minimal context switching.

**Total estimated effort:** 2.5h (1h + 1h + 30m)

**Risk:** Very low — cosmetic and documentation changes only.

---

## Validation Gate

```bash
pytest -q src/prism
python3 -m ruff check src/prism
python3 -m black --check src/prism
```

No mypy gate required (no type changes).

---

## Artifacts

- `wave3-find05-cachekey-protocol-doc.md`
- `wave3-find07-eventbus-lock-audit.md`
- `wave3-find09-naming-consistency.md`
- `wave3-validation-report.yaml`
