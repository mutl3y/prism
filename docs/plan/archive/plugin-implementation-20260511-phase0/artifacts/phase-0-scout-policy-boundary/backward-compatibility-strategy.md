# PolicyManager Consolidation: Backward Compatibility Strategy

**Plan ID**: g84-remediation-mutl3y-cycle-20260509  
**Phase**: phase-0-scout-policy-boundary  
**Created**: 2026-05-09  
**Status**: STRATEGY DEFINED

---

## Executive Summary

This document details the backward compatibility strategy for migrating from 6 scattered resolver functions to the unified PolicyManager facade.

**Key Commitments**:
- Existing code continues to work without modification
- Deprecation warnings guide gradual migration
- Phased rollout: new code → existing code migration → cleanup
- Zero breaking changes during transition period (6+ months)

---

## Section 1: Backward Compatibility Goals

### Goal 1: Zero Breakage

**Commitment**: Existing code that calls old resolver functions continues to work.

```python
# Old code (existing, continues to work)
from scanner_plugins.defaults import resolve_task_line_parsing_policy

policy = resolve_task_line_parsing_policy(di)
module = policy.detect_task_module(task)
```

**Implementation**: Old resolver functions delegate to PolicyManager:

```python
# In scanner_plugins/defaults.py
def resolve_task_line_parsing_policy_plugin(di):
    """DEPRECATED: Use policy_manager.resolve_task_line_parsing_policy()
    
    This function is maintained for backward compatibility only.
    New code should call di.policy_manager.resolve_task_line_parsing_policy()
    """
    warnings.warn(
        "resolve_task_line_parsing_policy_plugin() is deprecated; "
        "use di.policy_manager.resolve_task_line_parsing_policy() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    if hasattr(di, "policy_manager"):
        return di.policy_manager.resolve_task_line_parsing_policy()
    # Fallback to old implementation (for code without DI)
    return _resolve_task_line_parsing_policy_impl(di)
```

### Goal 2: Deprecation Guidance

**Commitment**: Deprecation warnings are clear, actionable, and not disruptive.

```python
# When old code runs:
UserWarning: resolve_task_line_parsing_policy_plugin() is deprecated; 
use di.policy_manager.resolve_task_line_parsing_policy() instead 
(file="src/prism/scanner_extract/task_extract_adapters.py", line=42)
```

### Goal 3: Gradual Migration

**Commitment**: Code can migrate incrementally; no all-or-nothing switchover.

Timeline:
- **Phase 1** (now): New code uses PolicyManager; old code unchanged
- **Phase 2** (3-4 months): Migrate existing consumers to PolicyManager
- **Phase 3** (6+ months): Remove deprecated functions
- **Phase 4**: Legacy wrappers removed

---

## Section 2: Deprecation Timeline

### Timeline: Deprecation Not Error (6+ months)

**Duration**: 6+ months from implementation to removal

**Phase 1 (Months 1-2)**: PolicyManager released; old code works with warnings

```python
# Old code still works
from scanner_plugins.defaults import resolve_task_line_parsing_policy
policy = resolve_task_line_parsing_policy(di)  # Works, emits DeprecationWarning
```

**Phase 2 (Months 2-4)**: Gradual migration of existing consumers

```python
# Existing code in scanner_extract/ migrated
from scanner_plugins.defaults import resolve_task_line_parsing_policy  # Remove this
policy = di.policy_manager.resolve_task_line_parsing_policy()  # Use this instead
```

**Phase 3 (Months 4-6)**: All consumers migrated; final straggler cleanup

**Phase 4 (Month 7+)**: Deprecated functions removed (breaking change)

### No Hard Deadline (Soft Deprecation)

- **Never** force immediate migration
- **Never** break existing code without warning period
- **Always** provide clear migration path
- **Always** test old and new paths together

---

## Section 3: Migration Patterns

### Pattern 1: Direct Resolver Function Call

**Old Code** (scanner_extract/task_extract_adapters.py):

```python
from scanner_plugins.defaults import resolve_task_line_parsing_policy

def extract_task_annotations(di, file_path):
    policy = resolve_task_line_parsing_policy(di)
    module = policy.detect_task_module(...)
    return annotations
```

**Emits Warning**:

```
DeprecationWarning: resolve_task_line_parsing_policy_plugin() is deprecated; 
use di.policy_manager.resolve_task_line_parsing_policy() instead
  File "src/prism/scanner_extract/task_extract_adapters.py", line 42
```

**New Code** (same file, migrated):

```python
def extract_task_annotations(di, file_path):
    policy = di.policy_manager.resolve_task_line_parsing_policy()
    module = policy.detect_task_module(...)
    return annotations
```

**No Warning**: New code path is clean

---

### Pattern 2: Using Prepared Policy Bundle

**Old Code** (scanner_core/task_catalog.py):

```python
from scanner_plugins.defaults import (
    resolve_task_traversal_policy,
    resolve_yaml_parsing_policy,
)

def build_task_catalog(di, path):
    task_policy = resolve_task_traversal_policy(di)
    yaml_policy = resolve_yaml_parsing_policy(di)
    tasks = task_policy.iter_task_mappings(...)
    return tasks
```

**Emits Warnings** (for each resolver call)

**New Code** (same file, migrated):

```python
def build_task_catalog(di, path):
    bundle = di.policy_manager.resolve_prepared_policy_bundle()
    task_policy = bundle["task_traversal"]
    yaml_policy = bundle["yaml_parsing"]
    tasks = task_policy.iter_task_mappings(...)
    return tasks
```

**Benefit**: Cleaner; avoids repeated resolver calls

---

### Pattern 3: Conditional Fallback (Optional Policies)

**Old Code** (scanner_core/variable_discovery.py):

```python
try:
    policy = resolve_variable_extractor_policy(di)
except MissingPolicyError:
    # Use default if not found
    policy = None
```

**New Code**:

```python
try:
    policy = di.policy_manager.resolve_variable_extractor_policy()
except MissingPolicyError:
    policy = None
```

**Behavior**: Identical; PolicyManager handles missing policies consistently

---

## Section 4: Testing Strategy for Backward Compatibility

### Test 1: Deprecated Functions Still Work

**File**: `tests/backward_compat/test_old_resolver_functions.py`

```python
def test_deprecated_resolver_returns_same_policy():
    """Old resolver and new resolver return equivalent policies."""
    di = DIContainer.default()
    
    # Old path (emits warning)
    with pytest.warns(DeprecationWarning):
        old_policy = resolve_task_line_parsing_policy(di)
    
    # New path (no warning)
    new_policy = di.policy_manager.resolve_task_line_parsing_policy()
    
    # Both return the same policy instance (cached)
    assert old_policy is new_policy

def test_deprecated_functions_emit_warnings():
    """Each deprecated function emits a DeprecationWarning."""
    di = DIContainer.default()
    
    deprecated_functions = [
        resolve_task_line_parsing_policy,
        resolve_task_annotation_parsing_policy,
        # ... etc for all 6 functions
    ]
    
    for func in deprecated_functions:
        with pytest.warns(DeprecationWarning, match="is deprecated"):
            func(di)
```

### Test 2: Consumers Can Call Either Path

**File**: `tests/backward_compat/test_consumer_paths.py`

```python
def test_task_extract_adapters_via_old_path():
    """task_extract_adapters can call old resolver functions."""
    di = DIContainer.default()
    
    # Simulate old code path
    with pytest.warns(DeprecationWarning):
        result = extract_task_annotations_old_style(di, file_path)
    
    assert result is not None

def test_task_extract_adapters_via_new_path():
    """task_extract_adapters can call new PolicyManager."""
    di = DIContainer.default()
    
    # Simulate new code path
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # No warnings expected
        result = extract_task_annotations_new_style(di, file_path)
    
    assert result is not None
```

### Test 3: Both Paths Produce Identical Results

**File**: `tests/backward_compat/test_old_vs_new_equivalence.py`

```python
def test_old_and_new_paths_equivalent():
    """Old and new resolution paths produce equivalent results."""
    di = DIContainer.default()
    test_inputs = [
        {"module": "debug", "when": "condition"},
        {"module": "set_fact", "when": "other_condition"},
    ]
    
    for test_input in test_inputs:
        # Old path
        with pytest.warns(DeprecationWarning):
            old_policy = resolve_task_line_parsing_policy(di)
            old_result = old_policy.detect_task_module(test_input)
        
        # New path
        new_policy = di.policy_manager.resolve_task_line_parsing_policy()
        new_result = new_policy.detect_task_module(test_input)
        
        # Results must be identical
        assert old_result == new_result
```

---

## Section 5: Deprecation Warning Configuration

### Warning Emission Strategy

**Emit DeprecationWarning** (not UserWarning):

```python
import warnings

warnings.warn(
    "resolve_task_line_parsing_policy() is deprecated; "
    "use di.policy_manager.resolve_task_line_parsing_policy() instead",
    DeprecationWarning,
    stacklevel=2,
)
```

**Why DeprecationWarning?**
- Hidden by default (doesn't spam users)
- Visible in CI with `-W error::DeprecationWarning` (catches issues)
- Clear that this is for developers, not end-users

### Suppressing Warnings (Temporary)

**During Transition**: Tests can suppress warnings temporarily:

```python
import warnings

# Suppress all deprecation warnings for now
warnings.filterwarnings("ignore", category=DeprecationWarning)

# or use pytest marker
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_something():
    pass
```

**Never use in production code**.

### CI Configuration

**.github/workflows/test.yml** (excerpt):

```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Run tests with strict deprecation warnings
      run: pytest -W error::DeprecationWarning -v
```

**Effect**: CI breaks if new code uses deprecated functions; old code OK during transition.

---

## Section 6: Migration Checklist for Consumers

### For Each Consumer Module

**Step 1: Identify all resolver function calls**

```bash
grep -r "resolve_.*_policy" src/prism/scanner_extract/ src/prism/scanner_core/
```

**Step 2: Map to PolicyManager equivalents**

| Old Function | New Call |
|--------------|----------|
| `resolve_task_line_parsing_policy(di)` | `di.policy_manager.resolve_task_line_parsing_policy()` |
| `resolve_jinja_analysis_policy(di)` | `di.policy_manager.resolve_jinja_analysis_policy()` |
| `resolve_task_traversal_policy(di)` | `di.policy_manager.resolve_task_traversal_policy()` |
| `resolve_task_annotation_parsing_policy(di)` | `di.policy_manager.resolve_task_annotation_parsing_policy()` |
| `resolve_yaml_parsing_policy(di)` | `di.policy_manager.resolve_yaml_parsing_policy()` |
| `resolve_variable_extractor_policy(di)` | `di.policy_manager.resolve_variable_extractor_policy()` |

**Step 3: Update imports**

```python
# Remove old imports
from scanner_plugins.defaults import resolve_task_line_parsing_policy

# Implicit: di.policy_manager is available (via DIContainer)
```

**Step 4: Update call sites**

```python
# Before
policy = resolve_task_line_parsing_policy(di)

# After
policy = di.policy_manager.resolve_task_line_parsing_policy()
```

**Step 5: Test**

```bash
pytest tests/ -W error::DeprecationWarning -v
# Should pass with no warnings from migrated code
```

**Step 6: Commit**

```bash
git commit -m "refactor: migrate to PolicyManager facade

Migrated src/prism/scanner_extract/task_extract_adapters.py to use
di.policy_manager.resolve_*() instead of deprecated resolver functions.

No functional changes; backward compatibility maintained."
```

---

## Section 7: Rollback Strategy

### If Migration Issues Arise

**Scenario 1**: New PolicyManager has bug

**Action**:
1. Disable PolicyManager integration (set `use_policy_manager=False` in config)
2. Old resolver functions continue to work (no bug)
3. Fix and re-enable

**Scenario 2**: Old code needs to continue working

**Action**:
- Deprecated functions will remain for 6+ months
- No action needed; old code keeps working
- Gradual migration at own pace

**Scenario 3**: Deprecation warnings too noisy

**Action**:
```python
# In test setup
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
```

---

## Section 8: Public Communication

### Message to Team

> **PolicyManager Consolidation (Q2 Initiative 2)**
>
> We're consolidating policy resolution to improve testability and maintainability.
>
> **What's changing**:
> - New `PolicyManager` facade for unified policy resolution
> - Old `resolve_*()` functions deprecated (but still work)
>
> **Timeline**:
> - New code uses PolicyManager immediately
> - Existing code continues to work with deprecation warnings
> - Full migration by Month 4
> - Deprecation cleanup by Month 7
>
> **Action Required** (now): None. Existing code continues to work.
>
> **Action Required** (Month 2-4): Migrate your module to PolicyManager when ready.
>
> **Help Available**: See `consolidation-sequence.md` for migration guide.

### Documentation Updates

**File**: `docs/POLICY_CONSOLIDATION.md` (new)

```markdown
# Policy Consolidation: Developer Guide

## Quick Start

### New Code (Use PolicyManager)

```python
policy = di.policy_manager.resolve_task_line_parsing_policy()
```

### Existing Code (Old Style, Still Works)

```python
from scanner_plugins.defaults import resolve_task_line_parsing_policy
policy = resolve_task_line_parsing_policy(di)  # Emits DeprecationWarning
```

## Migration Path

1. When you touch a module that calls `resolve_*()`, migrate it
2. See `consolidation-sequence.md` Section 6 for checklist
3. Run tests with `-W error::DeprecationWarning` to check
```

---

## Section 9: Edge Cases & Handling

### Edge Case 1: Code Without DI

**Scenario**: Legacy code not using DIContainer

**Handling**:
```python
def resolve_task_line_parsing_policy(di=None):
    """Fallback for code without DI."""
    if di is None or not hasattr(di, "policy_manager"):
        # Fall back to old implementation
        return _old_resolver_implementation()
    # Use new PolicyManager
    return di.policy_manager.resolve_task_line_parsing_policy()
```

### Edge Case 2: Multiple DI Containers

**Scenario**: Tests with different DIContainers

**Handling**:
```python
# Each DIContainer gets its own PolicyManager
di1 = DIContainer.default()
di2 = DIContainer.default()

# Resolvers use their own container
policy1 = di1.policy_manager.resolve_task_line_parsing_policy()
policy2 = di2.policy_manager.resolve_task_line_parsing_policy()

# Policies may be different instances (OK; no sharing assumed)
assert policy1 is not policy2  # Allowed
```

### Edge Case 3: Circular Import Prevention

**Scenario**: Avoid circular imports during migration

**Handling**: Import from bootstrap, not defaults:

```python
# Correct
from scanner_plugins.bootstrap import initialize_policy_manager

# Avoid
from scanner_plugins.defaults import resolve_task_line_parsing_policy
```

---

## Section 10: Checklist for Phase 1 Implementation

- [ ] Backward compat layer implemented (deprecation wrappers)
- [ ] Deprecation warnings emit correctly
- [ ] Old resolver functions delegate to PolicyManager
- [ ] Backward compat tests pass
- [ ] Old and new paths produce identical results
- [ ] CI configured to catch new code using deprecated functions
- [ ] Documentation updated with migration guide
- [ ] Team notified of deprecation timeline
- [ ] Migration checklist prepared for all consumer modules

---

## References

- Architecture: `policy-boundary-design.md`
- Implementation: `consolidation-sequence.md`
- Interface: `policy-manager-interface.py`
