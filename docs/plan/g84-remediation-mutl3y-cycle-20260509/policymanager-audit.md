# PolicyManager Consolidation Audit

**Phase 0 Scout Discovery** | **Tier 0 (FREE)** | **May 8, 2026**

---

## Executive Summary

Audit of PolicyManager consolidation identified **8 actionable consolidation opportunities** across scanner_core and scanner_extract modules, with potential for **200+ lines of code reduction** and **4-5 days of refactoring effort** at LOW-MEDIUM risk.

**Key Finding**: Policy resolution is highly scattered—12+ accessor functions exist across 6 modules, with duplicated proxy patterns and helper utilities that could be unified into 2-3 canonical interfaces.

---

## 1. Policy Protocol Classes (Canonical Contracts)

### 1.1 PreparedTaskLineParsingPolicy
- **Location**: `scanner_data/contracts_request.py` (lines 236-249)
- **Type**: Runtime Protocol (interface)
- **Responsibilities**:
  - Define task-include detection (TASK_INCLUDE_KEYS, ROLE_INCLUDE_KEYS, etc.)
  - Task module detection
  - When-constraint extraction
  - Template include regex matching
- **Lines of Code**: 14 (interface definition)
- **Usage Locations**: 
  - `scanner_extract/task_line_parsing.py` (proxied access)
  - `scanner_core/di_helpers.py` (accessor)
  - 6+ internal callsites

### 1.2 PreparedTaskAnnotationPolicy
- **Location**: `scanner_data/contracts_request.py` (lines 291-307)
- **Type**: Runtime Protocol (interface)
- **Responsibilities**:
  - Task annotation splitting and parsing
  - Marker prefix normalization
  - YAML-like annotation detection
  - Marker line regex generation
- **Lines of Code**: 17 (interface definition)
- **Usage Locations**:
  - `scanner_extract/task_line_parsing.py` (proxied access)
  - `scanner_core/di_helpers.py` (accessor)

### 1.3 PreparedTaskTraversalPolicy
- **Location**: `scanner_data/contracts_request.py` (lines 262-289)
- **Type**: Runtime Protocol (interface)
- **Responsibilities**:
  - Task mapping iteration and traversal
  - Task include target detection
  - Role include handling (static and dynamic)
  - Unconstrained dynamic include collection
- **Lines of Code**: 28 (interface definition)
- **Usage Locations**: `scanner_extract/` modules

### 1.4 PreparedYAMLParsingPolicy
- **Location**: `scanner_data/contracts_request.py` (lines 308-315)
- **Type**: Runtime Protocol (interface)
- **Responsibilities**:
  - YAML file loading
  - YAML parse failure detection
- **Lines of Code**: 8 (interface definition)

### 1.5 PreparedVariableExtractorPolicy
- **Location**: `scanner_data/contracts_request.py` (lines 317-328)
- **Type**: Runtime Protocol (interface)
- **Responsibilities**:
  - Collect include_vars files from role paths
- **Lines of Code**: 12 (interface definition)

### 1.6 PreparedJinjaAnalysisPolicy
- **Location**: `scanner_data/contracts_request.py` (lines 249-260)
- **Type**: Runtime Protocol (interface)
- **Responsibilities**:
  - Collect undeclared Jinja variables
- **Lines of Code**: 12 (interface definition)

---

## 2. Manager & Registry Classes (Central Policy Orchestration)

### 2.1 PolicyManager (CENTRAL FACADE)
- **Location**: `scanner_core/policy_manager.py` (608 lines)
- **Type**: Unified facade for all policy coordination
- **Responsibilities**:
  - Coordinate policy resolution across 6 policy types
  - Manage policy overrides from scan_options
  - Compose prepared policy bundles
  - Delegate to FallbackPolicyRegistry for defaults
  - Implement caching (3 internal caches)
- **Methods**:
  - `resolve_prepared_bundle()` - Main entry point
  - `resolve_task_line_parsing_policy()` (35 lines, with caching)
  - `resolve_task_annotation_policy()` (35 lines, with caching)
  - `resolve_task_traversal_policy()` (35 lines, with caching)
  - `resolve_variable_extractor_policy()` (35 lines, with caching)
  - `resolve_yaml_parsing_policy()` (35 lines, with caching)
  - `resolve_jinja_analysis_policy()` (35 lines, with caching)
  - `get_platform_key()` - Extract platform from scan_options
  - `override_*_policy()` - Override specific policies (6 variants)
  - `get_fallback_policy()` - Get fallback implementation
- **Code Duplication**: High — each `resolve_*` method is nearly identical (~35 lines each) with only policy_type and return type varying

### 2.2 FallbackPolicyRegistry
- **Location**: `scanner_core/policy_registry.py` (306 lines)
- **Type**: Registry for default policy implementations
- **Responsibilities**:
  - Maintain platform-specific default policies
  - Provide fallback chain for each policy type
  - Validate policy shapes and contracts
  - Support plugin-provided policy overrides (Wave 2+)
  - Bootstrap resolver factories (6 types × multiple platforms)
- **Methods**:
  - `get_default_policy()` - Get default for type
  - `lookup_policy()` - Platform-specific lookup with fallback
  - `register_policy()` - Register platform-specific policy
  - `register_resolver()` - Register resolver factory (Wave 2)
  - `get_resolver()` - Retrieve resolver factory (Wave 2)
  - `_bootstrap_resolvers()` - Initialize all 6 resolver factories
  - `compose_bundle()` - Compose complete bundle (not yet implemented)
- **Caching**: Internal cache + resolver caching

### 2.3 PreparedPolicyBundle (TypedDict)
- **Location**: `scanner_data/contracts_request.py` (lines 330-340)
- **Type**: Runtime payload container
- **Contents**:
  - 6 Required/NotRequired policy instances
  - `comment_doc_marker_prefix`: str
  - `ignore_unresolved_internal_underscore_references`: bool
- **Lines of Code**: 11
- **Usage**: Passed through scan_options to all policy consumers

---

## 3. Compatibility & Deprecated Functions (WAVE 3)

### 3.1 policy_compat.py Deprecation Wrappers
- **Location**: `scanner_core/policy_compat.py` (265 lines)
- **Type**: Backward-compatibility facades
- **Count**: 6 nearly-identical wrapper functions
- **Functions**:
  1. `resolve_task_line_parsing_policy()` (lines 39-76)
  2. `resolve_task_annotation_policy()` (lines 78-113)
  3. `resolve_task_traversal_policy()` (lines 116-151)
  4. `resolve_variable_extractor_policy()` (lines 154-189)
  5. `resolve_yaml_parsing_policy()` (lines 192-227)
  6. `resolve_jinja_analysis_policy()` (lines 230-265)
- **Pattern**: Each wrapper is 35-40 lines; all share identical structure:
  1. Deprecation warning
  2. Logger warning
  3. Access di.policy_manager
  4. Delegate to manager
- **Code Duplication**: **40+ lines of duplicated warning/delegation logic** across 6 functions
- **Consolidation Opportunity**: Generate via template macro or single factory function (OPPORTUNITY #1)

---

## 4. Policy Accessor Helpers (SCATTERED PATTERNS)

### 4.1 di_helpers.py (Scanner-Core Helpers)
- **Location**: `scanner_core/di_helpers.py` (155 lines total, 50+ lines policy-related)
- **Functions**:
  1. `scan_options_from_di()` - Extract scan_options from DI container (20 lines)
  2. `get_prepared_policy_or_none()` - Safe policy retrieval (15 lines)
  3. `require_prepared_policy()` - Fail-fast policy retrieval (10 lines)
  4. `get_event_bus_or_none()` - Event bus accessor (secondary)
- **Pattern**: Consistent error handling with logging
- **Duplication**: Similar logic exists in scanner_extract modules
- **Consolidation Score**: Medium — these are canonical, but duplication exists elsewhere

### 4.2 variable_extractor.py (Inline Accessor)
- **Location**: `scanner_extract/variable_extractor.py` (lines 20-29)
- **Function**: `get_variable_extractor_policy()` (10 lines)
- **Pattern**: Inline policy extraction with fail-fast error
- **Duplication**: Duplicates logic from `require_prepared_policy()` in di_helpers
- **Consolidation Opportunity**: Replace with call to `require_prepared_policy()` (OPPORTUNITY #2)

### 4.3 task_line_parsing.py (Helpers)
- **Location**: `scanner_extract/task_line_parsing.py` (lines 105-135)
- **Functions**:
  1. `_task_line_policy_attr()` (3 lines) - Extract attribute from policy
  2. `get_task_include_keys()` (3 lines)
  3. `get_role_include_keys()` (3 lines)
  4. `get_include_vars_keys()` (3 lines)
  5. `get_set_fact_keys()` (3 lines)
  6. `get_task_block_keys()` (3 lines)
  7. `get_task_meta_keys()` (3 lines)
  8. `get_templated_include_re()` (3 lines)
  9. `_extract_constrained_when_values()` (5 lines)
  10. `_normalize_marker_prefix()` (3 lines)
  11. `_build_marker_line_re()` (5 lines)
- **Pattern**: All delegate to `require_prepared_policy()` with policy attribute access
- **Duplication**: **8 nearly-identical 3-line getter functions** using same pattern
- **Consolidation Opportunity**: Replace with generic `get_policy_attr()` helper (OPPORTUNITY #3)

---

## 5. Proxy Pattern Classes (POLICY-BACKED COLLECTIONS)

### 5.1 _PolicyBackedCollectionProxy
- **Location**: `scanner_extract/task_line_parsing.py` (lines 13-41)
- **Type**: Dynamic attribute proxy
- **Responsibilities**:
  - Intercept attribute access on module constants (TASK_INCLUDE_KEYS, etc.)
  - Resolve from prepared_policy_bundle at call time
  - Support Collection interface (__iter__, __contains__, __len__)
- **Lines of Code**: 29
- **Usage**: 6 module-level constants proxied (lines 80-85)
- **Pattern**: Lazy-evaluation proxy for policy-backed collections
- **Duplication**: Nearly identical to _PolicyBackedRegexProxy (below)
- **Consolidation Opportunity**: Genericize into `PolicyBackedAttributeProxy` template (OPPORTUNITY #4)

### 5.2 _PolicyBackedRegexProxy
- **Location**: `scanner_extract/task_line_parsing.py` (lines 45-75)
- **Type**: Dynamic regex proxy
- **Responsibilities**:
  - Intercept regex method calls on module-level regex proxies
  - Resolve re.Pattern from prepared_policy_bundle at call time
  - Support regex interface (match, search, fullmatch, getattr)
- **Lines of Code**: 31
- **Pattern**: Runtime resolution with type validation
- **Consolidation Opportunity**: Merge with _PolicyBackedCollectionProxy using duck-typing (OPPORTUNITY #4)

---

## 6. Policy Context & TypedDicts (SCATTERED CONTEXT MANAGEMENT)

### 6.1 ScanPolicyContext (Core Context)
- **Location**: `scanner_data/contracts_request.py` (lines 367-405)
- **Subcontexts**:
  - `DynamicIncludesPolicyContext` - Dynamic include behavior
  - `AnnotationsPolicyContext` - Annotation behavior
  - `ReferencesPolicyContext` - Reference behavior
  - `PluginRuntimePolicyContext` - Plugin runtime behavior
  - `CommentDocPolicyContext` - Comment doc behavior
  - `SelectionPolicyContext` - Selection behavior
  - `PolicyContext` - Parent (base) context
- **Consolidation Opportunity**: Context handling scattered across multiple modules; could use unified context builder (OPPORTUNITY #5)

### 6.2 Policy Context Normalization (scan_request.py)
- **Functions**: `_is_scan_policy_context()`, `_copy_scan_policy_context()`, `_normalize_policy_context()`
- **Location**: `scanner_core/scan_request.py` (lines 21-57)
- **Lines of Code**: ~37
- **Pattern**: Manual context manipulation, duplicated across modules
- **Consolidation Opportunity**: Centralize context builder/normalizer (OPPORTUNITY #5)

---

## 7. Caching Strategy (MULTIPLE IMPLEMENTATIONS)

### 7.1 PolicyManager Caching
- **Caches**: 3 separate caches
  1. `_cache` - Generic policy cache (dict[str, Any])
  2. `_bundle_cache` - Bundle-specific cache
  3. `_policy_cache` - Policy-specific cache
  4. `_preresolved_cache` - Pre-resolved cache
- **Strategy**: Key by `f"{policy_type}:{id(scan_options)}"`
- **Lock**: RLock per cache

### 7.2 FallbackPolicyRegistry Caching
- **Caches**: 1 main cache + resolver caching
- **Strategy**: Similar key pattern
- **Lock**: RLock per cache

### 7.3 Local Caching in Proxies
- **Pattern**: Each proxy calls `_current_value()` or `_current_regex()` at runtime
- **Issue**: No caching at proxy level; repeated lookups possible
- **Consolidation Opportunity**: Unified cache layer (OPPORTUNITY #6)

---

## 8. Summary of 8 Consolidation Opportunities

| # | Opportunity | Current State | Consolidation Target | Est. Savings | Risk | Effort |
|---|-------------|---------------|----------------------|--------------|------|--------|
| 1 | Deprecation wrapper duplication | 6× 35-40 line functions (policy_compat.py) | Template macro or factory (1-2 functions) | 40-50 lines | LOW | 0.5 days |
| 2 | Inline policy accessor in variable_extractor | Duplicates `require_prepared_policy()` logic (10 lines) | Replace with canonical helper call | 10 lines | LOW | 0.25 days |
| 3 | Scattered policy attr getters | 8 nearly-identical 3-line functions in task_line_parsing | Generic `get_policy_attr()` helper | 20 lines | LOW | 0.5 days |
| 4 | Proxy pattern duplication | _PolicyBackedCollectionProxy + _PolicyBackedRegexProxy (60 lines) | Genericize to `PolicyBackedProxy[T]` template (25 lines) | 35 lines | MEDIUM | 1 day |
| 5 | Policy context management | Scattered normalization across modules (~50 lines) | Centralized context builder/validator (1 module) | 25 lines | MEDIUM | 1 day |
| 6 | Multi-level caching fragmentation | 3 caches in PolicyManager + 1 in Registry (uncooordinated) | Unified cache layer or shared cache strategy | 30-40 lines refactored | MEDIUM | 1 day |
| 7 | resolve_* method duplication in PolicyManager | 6 nearly-identical 35-line methods (210 lines total) | Template/macro or base method (50 lines) | 160 lines | HIGH | 1.5 days |
| 8 | Policy type string validation scattered | `SUPPORTED_POLICY_TYPES` in registry, policy_type checks in manager | Centralize type enum or constant (scanner_data/policy_constants.py) | 20 lines | LOW | 0.5 days |

---

## Ownership & Module Boundaries

### Current Ownership
- **scanner_core/policy_manager.py**: PolicyManager (central facade)
- **scanner_core/policy_registry.py**: FallbackPolicyRegistry (registry)
- **scanner_core/policy_compat.py**: Deprecated wrappers
- **scanner_core/di_helpers.py**: Accessor utilities
- **scanner_data/contracts_request.py**: Protocol definitions & TypedDicts
- **scanner_extract/task_line_parsing.py**: Proxy patterns + helpers
- **scanner_extract/variable_extractor.py**: Inline accessor

### Proposed Post-Consolidation Ownership
- **scanner_core/policy_manager.py**: Unified facade (reduced duplication)
- **scanner_core/policy_registry.py**: Registry (unchanged)
- **scanner_core/policy_compat.py**: DEPRECATED → DELETE after Wave 3
- **scanner_core/di_helpers.py**: Canonical accessors (expanded)
- **scanner_core/policy_proxy.py**: NEW — generic proxy patterns
- **scanner_data/policy_contracts.py**: NEW — centralized context + constants
- **scanner_extract/task_line_parsing.py**: Uses canonical proxies & helpers (simplified)
- **scanner_extract/variable_extractor.py**: Uses canonical helper (simplified)

---

## Risk Assessment

### Low Risk
- Opportunity #1: Deprecation wrapper refactoring (already deprecated)
- Opportunity #2: Inline accessor consolidation (pure substitution)
- Opportunity #3: Scattered getter consolidation (mechanical refactor)
- Opportunity #8: Type constant centralization (no behavior change)

### Medium Risk
- Opportunity #4: Proxy pattern genericization (requires duck-typing validation)
- Opportunity #5: Context builder centralization (affects multiple modules)
- Opportunity #6: Caching layer unification (performance impact risk)

### High Risk
- Opportunity #7: PolicyManager method duplication refactoring (70% of manager code affected)

---

## Testing Strategy

- **Unit**: Per-opportunity test isolation (each refactor is independently testable)
- **Integration**: Existing pytest suite validates all policy resolution paths
- **Regression**: Parity testing against current behavior required for each opportunity
- **Performance**: Caching consolidation requires benchmark comparison

---

## Effort Estimate

| Phase | Opportunities | Est. Effort | Risk |
|-------|---------------|------------|------|
| Wave 1 (LOW) | #1, #2, #3, #8 | 1.75 days | LOW |
| Wave 2 (MEDIUM) | #4, #5, #6 | 3 days | MEDIUM |
| Wave 3 (HIGH) | #7 | 1.5 days | HIGH |
| **TOTAL** | **8** | **~6.25 days** | **MEDIUM** |

---

## Next Steps

1. **Phase 0 Closure**: This audit delivered 8 findings ✓
2. **Phase 1**: Prioritize Wave 1 opportunities (LOW-RISK quick wins)
3. **Phase 3**: Probe Wave 2 opportunities (MEDIUM-RISK)
4. **Phase 5**: Build Wave 3 refactoring (HIGH-RISK, high-impact)
5. **Phase 6**: Gatekeeper validation of consolidation parity
6. **Phase 7**: Archive lessons learned

---

**Audit Tier**: Tier 0 (FREE) — Discovery only  
**Estimated Cost**: $0.001  
**Deliverables**: 2 files (policymanager-audit.md + policy-consolidation-opportunities.yaml)  
**Status**: ✅ COMPLETE
