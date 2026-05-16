# Resolver Chain Analysis: Policy Resolution Paths

## Overview

This document traces all 3 policy resolution paths in the system and identifies hidden dependencies, fallback mechanisms, and potential failure modes.

---

## Resolution Path #1: Primary Direct Access Path

**Name**: Direct Bundle Access (35+ call sites)

**Participants**:
- `scanner_core/di_helpers.py:get_prepared_policy_or_none()` [Root]
- `scanner_core/di_helpers.py:require_prepared_policy()` [Root wrapper]
- 35+ consumer call sites across all domains

**Resolution Flow**:
```
caller (e.g., scanner_extract/task_file_traversal.py:119)
  ↓
require_prepared_policy(di, "task_line_parsing", "task_line_parsing")
  ↓
get_prepared_policy_or_none(di, "task_line_parsing")
  ├→ scan_options = scan_options_from_di(di)
  │   ├→ if di is None: return None
  │   ├→ if di is HasScanOptions: return di.scan_options
  │   └→ else: return None
  │
  ├→ prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
  │
  └→ return bundle.get(policy_name) if bundle exists else None
       ↓
       [If None, require_prepared_policy raises ValueError]
```

**Characteristics**:
- **Synchronous**: Blocks until policy found or raises
- **No Fallback**: If bundle missing, raises immediately
- **DI-Dependent**: Requires DI context or fails
- **High Frequency**: 35+ call sites, 1000+ calls per scan

**Failure Modes**:

| Scenario | Failure | Impact | Remedy |
|----------|---------|--------|--------|
| DI is None | get_prepared_policy_or_none returns None | ValueError in require_prepared_policy | Pass DI context or pre-create bundle |
| scan_options missing | di.scan_options doesn't exist | Returns None, raises ValueError | Ensure DI has scan_options |
| prepared_policy_bundle missing | bundle key not in scan_options | Returns None, raises ValueError | Ensure bundle created before use |
| policy_name key missing | bundle doesn't have "task_line_parsing" key | Returns None, raises ValueError | Ensure all 6 policies in bundle |
| policy is None | bundle["task_line_parsing"] = None | Returns None, raises ValueError | Resolver should return non-None policy |

**Optimization Opportunities**:
- Cache result in ScannerContext.policy_constants (already done for some attributes)
- Lazy-load with memoization at module level
- Pre-populate hotloop caches during ScannerContext init

**Thread-Safety**: ✅ Safe (read-only dict access)

---

## Resolution Path #2: Fallback Registry Path (YAML Parsing Only)

**Name**: Registry Fallback Resolution (2 call sites in scanner_io/loader.py)

**Participants**:
- `scanner_io/loader.py:_get_yaml_parsing_policy()` [Entry]
- `scanner_core/di_helpers.py:get_prepared_policy_or_none()` [Primary attempt]
- `scanner_plugins/defaults.py:resolve_yaml_parsing_policy_plugin()` [Fallback invoker]
- Global plugin registry [Fallback source]
- `scanner_io/loader.py:_resolve_policy_with_registry()` [Fallback orchestrator]

**Resolution Flow**:
```
_get_yaml_parsing_policy(di=None)
  ├→ ATTEMPT PRIMARY: get_prepared_policy_or_none(di, "yaml_parsing")
  │   └→ if policy found: return policy
  │
  └→ FALLBACK: _resolve_policy_with_registry(
                  resolver=resolve_yaml_parsing_policy_plugin,
                  di=di
               )
      ├→ Check if di has plugin_registry override
      │   ├→ if yes: use DI registry
      │   └→ if no: use global fallback registry
      │
      └→ registry.get("yaml_parsing")
          ├→ invoke resolver function
          ├→ return resolved plugin instance
          └→ [No further fallback]
```

**Characteristics**:
- **Two-Stage**: Primary (bundle), then Fallback (registry)
- **Registry-Based**: Uses PluginRegistry for dynamic resolution
- **Lazy-Loaded**: Invokes resolver only if bundle missing
- **Limited Scope**: ONLY used for YAML parsing policy (1 of 6 policies)

**Failure Modes**:

| Scenario | Failure | Impact | Remedy |
|----------|---------|--------|--------|
| Bundle has yaml_parsing | Returns immediately | No fallback invoked | ✅ Expected behavior |
| Bundle missing, registry has yaml_parsing | Invokes resolver | Policy resolved dynamically | ✅ Expected behavior |
| Bundle missing, registry missing yaml_parsing | resolver() raises | yaml_parsing unavailable | Ensure registry populated |
| registry is None | resolver() cannot access registry | resolver raises | Ensure registry initialized |
| resolver returns None | None returned to caller | YAML policy unavailable | resolver must return non-None |

**Why Only YAML Parsing?**

**Current System Design**: Only scanner_io/loader.py implements fallback registry logic. Other policies (task_line_parsing, jinja_analysis, etc.) use primary path only.

**Reason**: YAML loading happens early in codebase traversal, before full policy bundle is typically resolved. Fallback allows graceful degradation if bundle not yet created.

**Risk**: If other policies need fallback, they must implement similar two-stage resolution

**Thread-Safety**: ⚠️ Conditional (registry must be immutable)

---

## Resolution Path #3: Bundle Orchestration Path (Creation-Time Only)

**Name**: Policy Bundle Creation and Assembly (1 entry point)

**Participants**:
- `api_layer/non_collection.py:_ensure_prepared_policy_bundle_for_execution_request()` [Entry]
- `api_layer/plugin_facade.py:ensure_prepared_policy_bundle()` [Facade]
- `scanner_plugins/bundle_resolver.py:ensure_prepared_policy_bundle()` [Orchestrator]
- 6× `scanner_plugins/defaults.py:resolve_*_policy_plugin()` [Resolver functions]
- `scanner_plugins/bundle_resolver.py:_validate_prepared_policy_bundle()` [Validator]
- Fallback registry [For each resolver]

**Resolution Flow**:
```
_ensure_prepared_policy_bundle_for_execution_request(scan_options, di)
  ├→ prepared_bundle = plugin_facade.ensure_prepared_policy_bundle(
                          scan_options=scan_options,
                          di=di
                       )
  │
  ├→ [Inside facade]
  │   └→ bundle_resolver.ensure_prepared_policy_bundle(scan_options, di)
  │       ├→ Extract existing_bundle from scan_options
  │       ├→ Start with dict (empty or copy of existing)
  │       │
  │       ├→ IF bundle["task_line_parsing"] is None:
  │       │   └→ resolve_task_line_parsing_policy_plugin(di)
  │       │       ├→ _resolve_plugin_with_precedence(
  │       │       │    di_factory_name="factory_task_line_parsing_policy_plugin",
  │       │       │    registry_plugin_name="task_line_parsing",
  │       │       │    fallback_plugin=ANSIBLE_TASK_LINE_FALLBACK,
  │       │       │    strict_mode=True,
  │       │       │    registry=custom_registry or DEFAULT
  │       │       │  )
  │       │       │  ├→ Check DI for factory
  │       │       │  ├→ Check registry for plugin
  │       │       │  ├→ Use fallback if strict_mode=False
  │       │       │  └→ Return resolved plugin
  │       │       └→ Return task_line_parsing plugin
  │       │
  │       ├→ [Repeat for remaining 5 policies...]
  │       │   task_annotation_parsing
  │       │   task_traversal
  │       │   yaml_parsing
  │       │   jinja_analysis
  │       │   variable_extractor
  │       │
  │       └→ _validate_prepared_policy_bundle(bundle)
  │           └→ Check all required attributes present
  │
  └→ Store in scan_options["prepared_policy_bundle"] = bundle
```

**Characteristics**:
- **Orchestrator Pattern**: Resolves all 6 policies in one coordinated call
- **Idempotent**: If policy already in bundle, reuses existing
- **Strict Validation**: Checks all required attributes after resolution
- **Once Per Scan**: Called during request preparation

**Resolver Precedence** (for each policy):
1. **DI Factory**: Check if DI container has factory function
2. **Registry Lookup**: Check plugin registry by name
3. **Fallback Plugin**: Use hardcoded fallback (e.g., Ansible) if strict_mode=False
4. **Error**: Raise ValueError if strict_mode=True and no policy found

**Failure Modes**:

| Scenario | Failure | Impact | Remedy |
|----------|---------|--------|--------|
| DI factory exists | Returns from factory | ✅ Expected behavior | Factory responsible for correctness |
| Registry has plugin | Returns from registry | ✅ Expected behavior | Registry responsible for correctness |
| Fallback exists, strict=False | Returns fallback | ✅ Graceful degradation | Acceptable default |
| No policy found, strict=True | Raises ValueError | ❌ Scan fails | Ensure resolver chain populated |
| Bundle validation fails | Raises ValueError | ❌ Scan fails | Check bundle shape requirements |
| Multiple calls overwrite | Last write wins | ✅ Expected behavior | Orchestrator idempotent |

**Thread-Safety**: ⚠️ Unsafe
- `ensure_prepared_policy_bundle()` modifies scan_options dict
- If multiple threads call simultaneously, race condition possible
- Need lock or isolated scan_options per thread

---

## Hidden Resolution Paths (Anti-Patterns)

### Path A: Direct Attribute Access (Task Line Parsing Constants)

**Location**: `scanner_extract/task_line_parsing.py` (module-level instances)

```python
# Module-level instances created at import time
TASK_INCLUDE_KEYS = _PolicyBackedCollectionProxy("TASK_INCLUDE_KEYS")
ROLE_INCLUDE_KEYS = _PolicyBackedCollectionProxy("ROLE_INCLUDE_KEYS")
# ...

# Usage in hotloop:
if "task" in TASK_INCLUDE_KEYS:  # ← Calls __contains__
    # Inside __contains__:
    # return getattr(require_prepared_policy(None, "task_line_parsing", ...), ...)
```

**Problem**: Proxy calls `require_prepared_policy(di=None, ...)`, which cannot access scan_options

**Resolution Path** (Attempted):
```
__contains__()
  ├→ _current_value()
  │   ├→ require_prepared_policy(None, "task_line_parsing", "task_line_parsing")
  │   │   ├→ get_prepared_policy_or_none(None, "task_line_parsing")
  │   │   │   ├→ scan_options_from_di(None)
  │   │   │   │   └→ di is None: return None ← PROBLEM!
  │   │   │   └→ Cannot access bundle
  │   │   └→ raises ValueError ← BROKEN!
```

**Status**: **BROKEN** - Module-level proxies cannot resolve policy

**Workaround**: Currently works because `di=None` case must be handled somehow upstream, but details not documented

---

### Path B: Direct Import Fallback (Never Executed)

**Location**: Nowhere currently, but potential anti-pattern

**Risk**: If some module directly imports ansible task keywords without going through resolver

```python
# Anti-pattern (not currently done):
from prism.scanner_plugins.ansible.task_keywords import TASK_INCLUDE_KEYS  # Direct import!
# Bypasses policy bundle, always uses ansible keywords
# Makes policy override impossible
```

**Status**: NOT OBSERVED - Policy system enforces proper resolution

---

## Resolver Configuration Matrix

| Policy | DI Factory | Registry Name | Fallback | Strict Mode | Hotloop | Critical |
|--------|-----------|---------------|----------|------------|---------|----------|
| task_line_parsing | factory_task_line_parsing_policy_plugin | "task_line_parsing" | AnsibleTaskLineParsingPolicy | True | YES | YES |
| task_annotation_parsing | factory_task_annotation_policy_plugin | "task_annotation_parsing" | AnsibleTaskAnnotationPolicy | True | YES | YES |
| task_traversal | factory_task_traversal_policy_plugin | "task_traversal" | AnsibleTaskTraversalPolicy | True | NO | NO |
| yaml_parsing | factory_yaml_parsing_policy_plugin | "yaml_parsing" | AnsibleYAMLParsingPolicy | False | NO | NO |
| jinja_analysis | factory_jinja_analysis_policy_plugin | "jinja_analysis" | AnsibleJinjaAnalysisPolicy | True | YES | YES |
| variable_extractor | factory_variable_extractor_policy_plugin | "variable_extractor" | AnsibleVariableExtractorPolicy | True | NO | NO |

---

## Recommendations

### Immediate (Critical)

1. **Fix Module-Level Proxies**: Replace di=None with proper DI context passing or cache lookup
2. **Add Thread-Safety**: Lock bundle creation in orchestrator
3. **Document Fallback Registry**: Clarify that YAML parsing is only policy with fallback

### Short-Term (High Priority)

1. **Audit Hidden Paths**: Verify no other fallback registry paths exist
2. **Validate All Resolvers**: Ensure all 6 resolvers handle strict_mode correctly
3. **Document Resolver Chain**: Create runbook for adding new policies

### Long-Term (Medium Priority)

1. **Immutable Bundles**: Make PreparedPolicyBundle immutable after creation
2. **Lazy-Loading Optimization**: Implement memoization for hotloop policies
3. **Unified Fallback**: Consider whether other policies need fallback registry too

---

## Resolver Chain Health Check

**Current Status**: ⚠️ Partially Working
- ✅ Bundle orchestration working
- ✅ Primary access path working for runtime
- ⚠️ Hotloop path (module-level proxies) design questionable
- ⚠️ Thread-safety not documented
- ⚠️ Fallback registry undocumented

**Blockers Before Integration Tests**:
1. Confirm module-level proxy resolution mechanism
2. Add thread-safety lock to bundle creation
3. Document fallback registry scope and limitations
