# Q3 Initiative 4, Phase 0 — ScannerContext Immutability Implementation Strategy

**Scout**: Scout-Q3Init4ContextImmutability  
**Plan ID**: q3-initiative-4-phase0-20260509  
**Date**: May 9, 2026  
**Focus**: Design approach, phasing strategy, and risk mitigation plan  

---

## Strategic Approach: Progressive Immutability

**Philosophy**: Follow Q2 initiative precedent (PolicyManager consolidation + MP1 marker-prefix enforcement) with a **three-phase rollout**:

1. **Phase 1 (Immediate, Low-Risk)**: Read-only properties + internal isolation
2. **Phase 2 (Short-term)**: Frozen dataclass for ScanMetadata + builder pattern
3. **Phase 3+ (Long-term)**: Extend pattern across DIContainer and EventBus

**Key Principle**: No breaking changes to public API; refactor internals gradually.

---

## Phase 1: Read-Only Properties & Internal Isolation (Weeks 1-2)

### Scope

Enable **@property-only access** to internal fields. External code cannot directly mutate ScannerContext internals.

### Changes

#### 1.1: Convert Mutable Fields to Private with Double-Underscore

```python
# Before
class ScannerContext:
    def __init__(self, ...):
        self._discovered_variables: tuple[Any, ...] = ()
        self._detected_features: FeaturesContext = _build_empty_features_context()
        self._scan_metadata: ScanMetadata = ScanMetadata()
        self._scan_errors: list[ScanErrorEntry] = []
        self.policy_constants: PolicyConstants | None = None

# After (Phase 1)
class ScannerContext:
    def __init__(self, ...):
        self.__discovered_variables: tuple[Any, ...] = ()
        self.__detected_features: FeaturesContext = _build_empty_features_context()
        self.__scan_metadata: ScanMetadata = ScanMetadata()
        self.__scan_errors: list[ScanErrorEntry] = []
        self.__policy_constants: PolicyConstants | None = None
```

**Effect**: Python name mangling prevents external access via `context.__field`; `context._ScannerContext__field` still possible but violates convention.

#### 1.2: Add Read-Only Properties

```python
@property
def discovered_variables(self) -> tuple[Any, ...]:
    """Read-only access to discovered variables (immutable tuple)."""
    return self.__discovered_variables

@property
def detected_features(self) -> FeaturesContext:
    """Read-only access to detected features (defensive deepcopy)."""
    return copy.deepcopy(self.__detected_features)

@property
def scan_metadata(self) -> ScanMetadata:
    """Read-only access to scan metadata (defensive deepcopy)."""
    return copy.deepcopy(self.__scan_metadata)

@property
def policy_constants(self) -> PolicyConstants | None:
    """Read-only access to policy constants (immutable once set)."""
    return self.__policy_constants
```

#### 1.3: Update Internal References

Replace all `self._field` with `self.__field` in scanner_context.py methods:

```python
def orchestrate_scan(self) -> dict[str, Any]:
    # Before
    self._discovered_variables = ()
    self._detected_features = _build_empty_features_context()
    self._scan_metadata = ScanMetadata()
    self._scan_errors = []
    
    # After (Phase 1)
    self.__discovered_variables = ()
    self.__detected_features = _build_empty_features_context()
    self.__scan_metadata = ScanMetadata()
    self.__scan_errors = []
```

**Affected Methods** (grep shows ~16 mutation sites):
- orchestrate_scan() (lines 346-349, 353-354)
- _record_phase_error() (line 366, _scan_errors.append)
- _build_output_payload() (line 470)

### Tests (Phase 1)

Add immutability enforcement tests:

```python
def test_scanner_context_fields_not_directly_accessible():
    """Verify ScannerContext internal fields use name mangling."""
    context = ScannerContext(di=..., role_path=..., scan_options=...)
    
    # Direct access should fail
    with pytest.raises(AttributeError):
        _ = context._discovered_variables
    
    with pytest.raises(AttributeError):
        _ = context._scan_metadata
    
    # @property access should work
    assert isinstance(context.discovered_variables, tuple)
    assert isinstance(context.scan_metadata, dict)

def test_scanner_context_defensive_copies_prevent_mutation():
    """Verify returned data cannot mutate internal state."""
    context = ScannerContext(di=..., role_path=..., scan_options=...)
    result = context.orchestrate_scan()
    
    # Mutate returned metadata
    metadata = context.scan_metadata
    metadata["scan_degraded"] = True
    
    # Internal state should be unchanged
    fresh_metadata = context.scan_metadata
    assert fresh_metadata.get("scan_degraded") != True
```

### Risk: Phase 1

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Test breakage (grep for `._field` access) | MEDIUM | Search codebase for direct field access; update test fixtures |
| Name mangling confusion | LOW | Document clearly in PR; add linter rule to flag ._field patterns |
| IDE autocompletion loss | LOW | Properties provide same interface; IDE recognizes @property |

### Effort Estimate

- Code changes: 2-3 days (update ~50 lines in scanner_context.py)
- Tests: 1 day (add 5-10 new test cases)
- Review & CI: 1 day
- **Total**: 4-5 days

### Backward Compatibility

✅ **PUBLIC API UNCHANGED** — All external callers use @property interface (no change)  
✅ **DEFENSIVE COPIES MAINTAINED** — Existing deepcopy strategy continues  
⚠️ **INTERNAL CODE ONLY** — Only scanner_context.py and tests need updates

---

## Phase 2: Frozen Dataclass & Builder Pattern (Weeks 3-6)

### Scope

Transition ScanMetadata to frozen dataclass; implement builder pattern for payload assembly.

### 2.1: Frozen Dataclass for ScanMetadata

#### Current State (TypedDict)

```python
class ScanMetadata(TypedDict, total=False):
    """Metadata payload attached to scanner outputs."""
    plugin_name: str
    features: dict[str, object]
    scan_errors: list[ScanErrorEntry]
    scan_degraded: bool
    # ... 10+ more fields
```

**Problem**: Dict is mutable; no runtime enforcement.

#### Target State (Frozen Dataclass)

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ScanMetadata:
    """Immutable scan metadata payload."""
    
    plugin_name: str | None = None
    features: dict[str, object] | None = None
    scan_errors: tuple[ScanErrorEntry, ...] = field(default_factory=tuple)
    scan_degraded: bool = False
    scan_policy_warnings: list[ScanPolicyWarning] | None = None
    scan_policy_blocker_facts: ScanPolicyBlockerFacts | None = None
    variable_insights: list[VariableInsight] | None = None
    yaml_parse_failures: tuple[YamlParseFailure, ...] = field(default_factory=tuple)
    role_notes: RoleNotes | None = None
    ignore_unresolved_internal_underscore_references: bool = False
    underscore_filtered_unresolved_count: int = 0
    concise_readme: bool = False
    include_scanner_report_link: bool = False
    scanner_report_relpath: str | None = None
    
    def __post_init__(self) -> None:
        """Validate immutable structure after construction."""
        if self.scan_errors and not isinstance(self.scan_errors, tuple):
            raise ValueError("scan_errors must be tuple (immutable)")
        if self.yaml_parse_failures and not isinstance(self.yaml_parse_failures, tuple):
            raise ValueError("yaml_parse_failures must be tuple (immutable)")
```

**Benefits**:
- Runtime enforcement: `FrozenInstanceError` on mutation attempts
- Type-safe access: `.scan_errors` instead of `["scan_errors"]`
- Validation: `__post_init__` can enforce invariants

**Breaking Change**:
- Callers using `metadata["key"] = value` dict syntax will fail
- **Mitigation**: Provide backward-compatibility wrapper

#### 2.1.1: Backward-Compatibility Wrapper

```python
class ScanMetadataCompat(dict):
    """Backward-compatibility wrapper for ScanMetadata migration."""
    
    def __init__(self, metadata: ScanMetadata):
        """Wrap frozen dataclass in dict interface."""
        self.__dict_data = {
            "plugin_name": metadata.plugin_name,
            "features": metadata.features,
            "scan_errors": list(metadata.scan_errors),
            "scan_degraded": metadata.scan_degraded,
            # ... all fields
        }
    
    def __getitem__(self, key: str) -> Any:
        return self.__dict_data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        # Raise with clear deprecation message
        raise TypeError(
            f"ScanMetadata is immutable (frozen dataclass). "
            f"Cannot set {key}. "
            f"Use ScanMetadataBuilder to construct new instances."
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.__dict_data.get(key, default)
    
    # ... proxy other dict methods
```

**Usage**:
- New code: Use frozen dataclass directly
- Legacy code: Use wrapper (emits deprecation warnings)
- Grace period: 2 releases before removing wrapper

#### 2.2: ScanMetadataBuilder Pattern

```python
class ScanMetadataBuilder:
    """Builder for constructing immutable ScanMetadata instances."""
    
    def __init__(self, base: ScanMetadata | None = None) -> None:
        """Initialize builder from existing metadata or empty."""
        if base is None:
            self._data = {}
        else:
            self._data = {
                "plugin_name": base.plugin_name,
                "features": copy.copy(base.features) if base.features else None,
                "scan_errors": tuple(base.scan_errors) if base.scan_errors else (),
                "scan_degraded": base.scan_degraded,
                # ... all fields
            }
    
    def with_features(self, features: dict[str, object]) -> "ScanMetadataBuilder":
        """Add feature context."""
        self._data["features"] = copy.copy(features)
        return self
    
    def with_scan_error(self, error: ScanErrorEntry) -> "ScanMetadataBuilder":
        """Append scan error."""
        errors = list(self._data.get("scan_errors", ()))
        errors.append(error)
        self._data["scan_errors"] = tuple(errors)
        return self
    
    def with_policy_warnings(self, warnings: list[ScanPolicyWarning]) -> "ScanMetadataBuilder":
        """Set policy warnings."""
        self._data["scan_policy_warnings"] = warnings
        return self
    
    def with_blocker_facts(self, facts: ScanPolicyBlockerFacts) -> "ScanMetadataBuilder":
        """Set blocker facts."""
        self._data["scan_policy_blocker_facts"] = facts
        return self
    
    def build(self) -> ScanMetadata:
        """Construct immutable ScanMetadata."""
        return ScanMetadata(**self._data)
```

**Usage in _build_output_payload**:

```python
def _build_output_payload(self) -> dict[str, object]:
    self._validate_required_scan_option_keys()
    context_payload = self._build_context_payload()
    
    # Use builder for step-by-step assembly
    metadata = (
        ScanMetadataBuilder(context_payload.get("metadata"))
        .with_features(_copy_features_metadata(self.__detected_features))
        .with_policy_warnings(merge_policy_warning_entries(...))
        .with_blocker_facts(self._build_scan_policy_blocker_facts(...))
        .build()
    )
    
    # Add errors to metadata (immutable after build)
    if self.__scan_errors:
        metadata = (
            ScanMetadataBuilder(metadata)
            .with_scan_error(...)  # or bulk add
            .build()
        )
    
    self.__scan_metadata = metadata
    return { ... }
```

### 2.3: Update ScanErrorEntry to Frozen

```python
@dataclass(frozen=True)
class ScanErrorEntry:
    """Immutable scan-phase error entry."""
    phase: str
    error_type: str
    message: str
    traceback: str | None = None
    cause: str | None = None
```

### Tests (Phase 2)

```python
def test_scan_metadata_frozen():
    """Verify ScanMetadata is frozen at runtime."""
    metadata = ScanMetadata(scan_degraded=True)
    
    with pytest.raises(FrozenInstanceError):
        metadata.scan_degraded = False

def test_scan_metadata_builder_creates_immutable_instance():
    """Verify builder produces immutable metadata."""
    builder = ScanMetadataBuilder()
    metadata = (
        builder
        .with_features({"key": "value"})
        .with_blocker_facts({...})
        .build()
    )
    
    assert isinstance(metadata, ScanMetadata)
    with pytest.raises(FrozenInstanceError):
        metadata.features = {}

def test_scan_metadata_compat_wrapper_supports_legacy_code():
    """Verify legacy dict-style access works via wrapper."""
    metadata = ScanMetadata(scan_degraded=True)
    compat = ScanMetadataCompat(metadata)
    
    # Read works
    assert compat["scan_degraded"] == True
    
    # Write raises with clear message
    with pytest.raises(TypeError, match="immutable"):
        compat["scan_degraded"] = False
```

### Risk: Phase 2

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking change to callers using dict syntax | HIGH | Provide compat wrapper; deprecation period of 2 releases |
| Test failures (dict vs dataclass access) | MEDIUM | Update tests to use `.field` syntax; provide adapter for legacy tests |
| Performance impact (deepcopy of features) | LOW | Features dict is typically small (<50 KB); benchmark before/after |
| Circular imports (builder in contracts module) | MEDIUM | Place builder in separate module; import only where needed |

### Effort Estimate

- Frozen dataclass: 2-3 days
- Builder pattern: 2 days
- Compat wrapper: 1 day
- Tests: 2-3 days
- Documentation: 1 day
- **Total**: 8-10 days

### Backward Compatibility

⚠️ **BREAKING CHANGE** — Dict-style access fails unless using wrapper  
✅ **GRACE PERIOD** — Wrapper available for 2 releases (deprecation warnings)  
✅ **PUBLIC OPTION** — Builders exposed as public API for new code

---

## Phase 3+: Extended Immutability (Long-term)

### Scope

Apply immutability pattern to remaining scanner_core structures:
- DIContainer (make registry, cache read-only)
- EventBus (immutable event records)
- VariableDiscovery, FeatureDetector (frozen result objects)

### Timeline

- **Phase 3** (Q3 2026): DIContainer immutability
- **Phase 4+** (Q4 2026+): EventBus, plugins

### Estimated Effort

- 15-20 days per phase (parallel with other Q3 initiatives)

---

## Decision Tree: When to Apply Immutability

```
┌─ Is this a result/output object? (discovered_variables, scan_metadata)
│  └─ YES → Use frozen dataclass + @property access
│
├─ Is this an input passed at construction? (di, scan_options, role_path)
│  └─ YES → Use @property with __ prefix (Phase 1)
│
├─ Is this internal temporary state? (cache, event bus queue)
│  └─ YES → Keep mutable; document single-use semantics
│
└─ Is this shared across threads? (DIContainer)
   └─ YES → Add threading.RLock for mutations; consider frozen variant
```

---

## Integration Checkpoints

### Before Phase 1

- [ ] Grep for all `._field` access patterns in codebase
- [ ] Add linter rule to flag direct field access
- [ ] Document name mangling pattern in developer guide
- [ ] Identify all test fixtures that access `._field`

### Between Phase 1 & 2

- [ ] Ensure all Phase 1 tests pass
- [ ] Collect feedback on @property naming
- [ ] Design frozen dataclass migration strategy

### Before Phase 2

- [ ] Design builder API with stakeholders
- [ ] Implement compat wrapper prototype
- [ ] Plan deprecation communication (2-release grace period)
- [ ] Update API documentation

### After Phase 2

- [ ] Announce deprecation of dict-style metadata access
- [ ] Monitor wrapper usage in telemetry (if available)
- [ ] Plan compat wrapper removal (v2.X release)

---

## Risk Mitigation Plan

### Production Impact: Minimal

**Rationale**:
1. No external mutation sites found (grep search returned 0)
2. Single-use design already enforced (documented in docstring)
3. Defensive copies already protect callers
4. DIContainer isolation prevents external state leakage

### Mitigation Strategy

| Risk | Mitigation |
|------|-----------|
| Test breakage | Run full test suite after Phase 1; update fixtures as needed |
| Callers expecting mutable fields | Use @property interface (no change); compat wrapper for Phase 2 |
| Performance impact | Benchmark deepcopy operations; optimize if needed |
| Documentation lag | Update docstrings in PR; add migration guide in Phase 2 |

### Rollback Plan

- **Phase 1**: Simple revert (replace __ with _ in scanner_context.py)
- **Phase 2**: Requires removing frozen dataclass; keep compat wrapper alive
- **Trigger**: If >3 production issues or >50% test failures

---

## Success Criteria

### Phase 1 (Read-Only Properties)

- [ ] All 5 internal fields use __ prefix and @property access
- [ ] Zero `._field` access remaining (linter enforces)
- [ ] All tests pass (existing + new immutability tests)
- [ ] No performance degradation (benchmark suite)
- [ ] Documentation updated (docstrings, dev guide)

### Phase 2 (Frozen Dataclass)

- [ ] ScanMetadata is frozen dataclass; no mutations possible
- [ ] Builder pattern used for all payload assembly
- [ ] Compat wrapper available for legacy code
- [ ] Deprecation warnings emitted for dict-style access
- [ ] Tests cover frozen behavior + builder chain
- [ ] Performance impact <5% on metadata operations

### Phase 3+ (Extended Immutability)

- [ ] Pattern applied to DIContainer, EventBus
- [ ] All core data structures immutable by design
- [ ] Zero unsafe mutations in scanner_core

---

## Communication Plan

### Phase 1 (Internal)

**PR Description**:
```markdown
## Refactor: Scanner Context Internal Field Access via Properties

Convert ScannerContext mutable fields to use Python name mangling (__)
and expose via read-only @property. This prevents accidental external
mutations and prepares for frozen dataclass transition in Phase 2.

### Changes
- Rename _field to __field for discovered_variables, detected_features, etc.
- Add @property accessors for all internal state
- Update internal method references
- Add immutability enforcement tests

### Impact
- PUBLIC API: No change (existing @property interface continues)
- INTERNAL CODE: Update 50 lines in scanner_context.py
- TESTS: Add 5 new immutability tests

### Backward Compatibility
✅ Fully backward-compatible with public API
```

### Phase 2 (Public Announcement)

**Release Notes**:
```markdown
## Deprecation Notice: Dictionary-Style ScanMetadata Access

ScanMetadata is now a frozen dataclass (immutable). Direct dictionary
access (metadata["key"]) now requires the ScanMetadataCompat wrapper.

### Timeline
- v2.X (current): dict-style access works via compat wrapper (deprecated)
- v2.X+1: Wrapper available but not recommended
- v2.X+2: dict-style access removed; use builder or frozen dataclass

### Migration
Use ScanMetadataBuilder for new code:

    metadata = (
        ScanMetadataBuilder()
        .with_features(features)
        .with_policy_warnings(warnings)
        .build()
    )
```

---

## Timeline Summary

| Phase | Duration | Effort | Risk | Deliverable |
|-------|----------|--------|------|-------------|
| Phase 1 | 1-2 weeks | 4-5 days | LOW | @property-only access + immutability tests |
| Phase 2 | 2-3 weeks | 8-10 days | MEDIUM | Frozen dataclass + builder + compat wrapper |
| Phase 3+ | TBD | 15-20 days | MEDIUM | Extended immutability to DIContainer, EventBus |

---

## Conclusion

**ScannerContext immutability is achievable with low production risk** because:

1. ✅ No external mutation sites in codebase (grep verified)
2. ✅ Single-use pattern already documented and enforced
3. ✅ Defensive copies protect external callers
4. ✅ DIContainer isolation prevents state leakage
5. ✅ Pattern mirrors Q2 successes (PolicyManager, MP1)

**Phase 1 is immediate and safe** (read-only properties). **Phase 2 requires migration planning** (compat wrapper + deprecation period). **Phase 3+ extends pattern** across scanner_core with diminishing risk.

**Recommended Action**: Proceed with Phase 1 immediately; assess Phase 2 go/no-go after Phase 1 success.

---

**Report Generated**: May 9, 2026 18:00 UTC  
**Model**: Tier 0 (FREE)  
**Status**: ✅ COMPLETE — Ready for Phase 1 Implementation (W/O from arch team)
