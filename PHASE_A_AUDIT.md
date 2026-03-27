# Phase A: Scanner Decomposition - Inventory & Audit

**Date:** 2026-03-27
**Scope:** scanner.py (4154 lines, 150 functions)
**Goal:** Identify responsibility clusters and rank extraction candidates

## Executive Summary

scanner.py is organized into **11 responsibility clusters** by functional domain. After detailed analysis, we've ranked extraction candidates by risk and cohesion. **Lane 1** (Error/Uncertainty Handling) is recommended as the first safe extraction target.

---

## Cluster Breakdown (Ranked by Size)

### 1. Output Rendering (~900 lines, 35+ functions)
**Responsible for:** Rendering README sections, style guides, template composition, merge logic

**Key Functions:**
- `render_readme()` - main entry point (70+ lines)
- `_render_readme_with_style_guide()` - orchestrates style guide rendering
- `_render_guide_*()` - specific section renderers (~40 functions)
- `_compose_section_body()`, `_merge_section_body()` - template merging
- `_filter_*()` - section filtering and selection
- `_apply_section_title_overrides()` - title management

**Dependencies:**
- Internal: Heavy cross-calling among render functions
- External: `style_guide` submodule, `style_vars` submodule, Jinja2, regex helpers
- Reverse: Called from `_enrich_scan_context_with_insights()`

**Submodules Already Extracted:**
- `scanner_submodules/style_guide.py`
- `scanner_submodules/style_vars.py`

**Risk Level:** MEDIUM-HIGH
- Complex template logic with many interdependencies
- Style guide rendering already partially extracted but not fully decoupled
- **Not a candidate for Lane 1** (too coupled to orchestration)

---

### 2. Main Orchestration (~750 lines, 30+ functions)
**Responsible for:** Orchestrating the entire scan flow, building contexts, applying policies

**Key Functions:**
- `run_scan()` - main API entry (75 lines)
- `_prepare_scan_context()` - top-level orchestrator
- `_collect_scan_base_context()` - baseline artifact collection
- `_collect_scan_identity_and_artifacts()` - identity resolution
- `_apply_scan_metadata_configuration()` - metadata setup
- `_enrich_scan_context_with_insights()` - enrichment flow
- `_apply_*_policy()` - policy enforcement
- `_build_*_payload()` - payload construction
- `_finalize_*()` - finalization steps

**Dependencies:**
- Internal: Calls into all other clusters
- External: `scan_context`, `scan_request`, `scan_output_emission`, `scan_output_primary` submodules
- Reverse: Primary public API

**Risk Level:** CRITICAL
- Central orchestrator - touches all other clusters
- **Cannot be decomposed** without breaking orchestration
- **Is the coordinator to be kept thin in Phase D**

---

### 3. Variable Row Building (~500 lines, 15+ functions)
**Responsible for:** Building variable insight rows from multiple sources

**Key Functions:**
- `build_variable_insights()` - main entry (50+ lines)
- `_populate_variable_rows()` - orchestration (70+ lines)
- `_build_static_variable_rows()` - defaults/vars rows (100+ lines)
- `_append_include_vars_rows()` - include_vars merging (30+ lines)
- `_append_set_fact_rows()` - set_fact accumulation (30+ lines)
- `_append_register_rows()` - register variable collection (30+ lines)
- `_append_readme_documented_rows()` - README-declared rows (30+ lines)
- `_append_argument_spec_rows()` - argument spec rows (40+ lines)
- `_append_referenced_variable_rows()` - referenced variable discovery (30+ lines)
- `_collect_variable_reference_context()` - context for references

**Dependencies:**
- Internal: Heavy cross-calling among `_append_*` functions
- External: `variable_extractor` submodule, Jinja analyzer, YAML parsing
- Reverse: Called from `_enrich_scan_context_with_insights()`

**Risk Level:** MEDIUM
- Self-contained: builds and returns variable rows
- Clear input/output contract
- Orchestration (`_populate_variable_rows`) could be simplified
- **Strong candidate for later extraction (Phase B+)**
- **Not ideal for Lane 1** (depends on orchestration flow coordination)

---

### 4. Task/README Scanning (~600 lines, 15+ functions)
**Responsible for:** Scanning task files and README sections for variables

**Key Functions:**
- `scan_for_default_filters()` - main filter scanner (40 lines)
- `scan_for_all_filters()` - all filters variant (40 lines)
- `_scan_file_for_default_filters()` - per-file scan (40 lines)
- `_scan_file_for_all_filters()` - per-file all filters (45 lines)
- `_collect_dynamic_task_include_tokens()` - dynamic include detection
- `_collect_dynamic_include_var_tokens()` - dynamic var extraction
- `_extract_readme_input_variables()` - README variable extraction (50+ lines)
- `_extract_readme_variable_names_from_line()` - line-level parsing (30+ lines)
- `_collect_readme_input_variables()` - orchestration (30 lines)
- Helper functions: `_is_readme_variable_section_heading()`, `_resolve_variable_section_heading_state()`, `_consume_fence_marker()`, etc.

**Dependencies:**
- Internal: Functions call into variable extractor, Jinja analyzer
- External: `_jinja_analyzer` submodule, `variable_extractor` submodule, `task_parser` submodule
- Reverse: Called from `_enrich_scan_context_with_insights()`

**Risk Level:** MEDIUM
- Mostly independent scanning logic
- Clear input/output (file path → list of variables/defaults)
- Depends on external submodules but not on scanner.py internals
- **Candidate for later extraction (Phase B+)**

---

### 5. Error/Uncertainty Handling (~300 lines, 8 functions)
**Responsible for:** Building uncertainty reasons, handling non-authoritative evidence

**Key Functions:**
- `_build_referenced_variable_uncertainty_reason()` - referenced var uncertainty (20 lines)
- `_append_non_authoritative_test_evidence_uncertainty_reason()` - test evidence logic (20 lines)
- `_collect_non_authoritative_test_variable_evidence()` - evidence collection (100+ lines)
- `_test_evidence_probability()` - probability calculation (10 lines)
- `_attach_non_authoritative_test_evidence()` - evidence attachment (60+ lines)
- `_should_suppress_internal_unresolved_reference()` - suppression logic (20 lines)

**Dependencies:**
- Internal: Minimal cross-dependencies
- External: Regex, path operations, minimal scanner.py dependencies
- Reverse: Called from variable row building functions

**Risk Level:** LOW ✅
- **Self-contained and minimal external dependencies**
- **Clear input/output:** row dict → modified row dict or None
- **No dependencies on orchestration state**
- **Easy to test in isolation**
- **Candidate for Lane 1** ✅

**Note:** Already partially exported to `scan_metrics` submodule but wrapper functions remain in scanner.py

---

### 6. Configuration/Setup (~300 lines, 10+ functions)
**Responsible for:** Loading configuration, resolving defaults, managing style guides

**Key Functions:**
- `resolve_default_style_guide_source()` - style guide resolution (40+ lines)
- `load_readme_marker_prefix()` - marker prefix loading (15 lines)
- `load_fail_on_*()- policy loaders (~10 variants, 15 lines total)
- `load_non_authoritative_test_evidence_*()` - evidence limits loaders
- `load_readme_section_*()` - section configuration loaders
- `_load_section_display_titles()` - display title loading
- `_resolve_section_selector()` - section selection logic
- `_refresh_policy()` - policy refresh (30 lines)

**Dependencies:**
- Internal: Minimal cross-dependencies
- External: YAML parsing, path operations, config file I/O
- Reverse: Called from orchestration and main entry point

**Risk Level:** LOW-MEDIUM
- Most functions are pure config loaders (stateless)
- `resolve_default_style_guide_source()` has more complexity
- **Could be extracted to dedicated submodule**
- **Not prioritized for Lane 1** (lower impact than error handling)

---

### 7. Data Loading (~200 lines, 10+ functions)
**Responsible for:** Loading role metadata, requirements, variables

**Key Functions:**
- `load_meta()` - galaxy.yml loading (10 lines + wrapper)
- `load_variables()` - loads vars/main.yml (20 lines)
- `load_requirements()` - requirements.yml loading (5 lines)
- `_load_role_variable_maps()` - maps from role paths (25 lines)
- `_parse_yaml_candidate()` - YAML parsing wrapper (25 lines)
- `_iter_role_variable_map_candidates()` - enumerates variable sources (10 lines)
- `_iter_role_argument_spec_entries()` - argument spec enumeration (30+ lines)
- `_map_argument_spec_type()` - type mapping (20 lines)

**Dependencies:**
- Internal: Mostly independent
- External: YAML parsing, path operations
- Reverse: Called from data collection and variable building

**Risk Level:** LOW
- Simple wrappers around YAML/file I/O
- **Good extraction candidate for Phase B**

---

### 8. File Discovery (~100 lines, 4 functions)
**Responsible for:** Enumerating files to scan

**Key Functions:**
- `_iter_role_yaml_candidates()` - finds YAML files (20 lines)
- `_collect_yaml_parse_failures()` - error collection (20 lines)
- `_iter_role_argument_spec_entries()` - argument spec files (already in Data Loading)
- `_iter_role_variable_map_candidates()` - variable source enumeration (already in Data Loading)

**Dependencies:**
- Internal: Minimal
- External: Path operations, directory traversal
- Reverse: Called from data loading

**Risk Level:** LOW
- Simple path operations
- Self-contained

---

### 9. Requirements/Collections (~150 lines, 5 functions)
**Responsible for:** Handling requirement and collection normalization

**Key Functions:**
- `_normalize_meta_role_dependencies()` - meta dependencies (5 lines)
- `_normalize_included_role_dependencies()` - included role dependencies (5 lines)
- `_extract_declared_collections_from_meta()` - collection extraction (5 lines)
- `_extract_declared_collections_from_requirements()` - requirements parsing (5 lines)
- `_build_collection_compliance_notes()` - note generation (15 lines)

**Dependencies:**
- Internal: Mostly wrappers
- External: minimal
- Reverse: Called from data collection

**Risk Level:** LOW
- Mostly delegated to `requirements` submodule
- Wrapper functions are thin

---

### 10. Runbook/Report (~200 lines, 7 functions)
**Responsible for:** Rendering runbooks and scanner reports

**Key Functions:**
- `render_runbook()` - runbook rendering (10 lines)
- `render_runbook_csv()` - CSV variant (5 lines)
- `_build_runbook_rows()` - row building (5 lines)
- `_build_scanner_report_markdown()` - report generation (20 lines)
- `_classify_provenance_issue()` - issue classification (5 lines)
- `_is_unresolved_noise_category()` - category checking (5 lines)
- `_extract_scanner_counters()` - counter extraction (15 lines)

**Dependencies:**
- Internal: Minimal
- External: `runbook`, `scanner_report` submodules
- Reverse: Called from output emission

**Risk Level:** MEDIUM
- Mostly delegated to submodules
- Thin wrappers
- **Already substantially extracted**

---

### 11. Utility/Helpers (~50 lines, 5+ functions)
**Responsible for:** Utility functions, data shaping

**Key Functions:**
- `_refresh_known_names()` - refresh variable names (5 lines)
- `_redact_secret_defaults()` - secret redaction (10 lines)
- `_format_requirement_line()` - formatting helper (5 lines)
- `normalize_requirements()` - requirements normalization (5 lines)
- Type definitions: `VariableProvenance`, `VariableRow`

**Risk Level:** LOW
- Simple helpers
- No dependencies on orchestration

---

## Ranked Extraction Candidates (by risk)

### ✅ Lane 1: Error/Uncertainty Handling (RECOMMENDED - LOW RISK)
**Size:** ~300 lines / 8 functions
**Target Module:** `scanner_submodules/scanner_errorhandling.py`

**What to Extract:**
```python
def _build_referenced_variable_uncertainty_reason(...)
def _append_non_authoritative_test_evidence_uncertainty_reason(...)
def _collect_non_authoritative_test_variable_evidence(...)
def _test_evidence_probability(...)
def _attach_non_authoritative_test_evidence(...)
def _should_suppress_internal_unresolved_reference(...)
+ constants: NON_AUTHORITATIVE_TEST_EVIDENCE_*
```

**Rationale:**
- ✅ Self-contained: no cross-dependencies with other cluster functions
- ✅ Clear contract: row dict → modified row (or None)
- ✅ No orchestration state dependency
- ✅ Already partially exported to `scan_metrics` submodule
- ✅ Testable in isolation
- ✅ Well-defined responsibility: uncertainty reason building + evidence attachment
- ✅ Can be wrapped with thin shims in scanner.py

**Risk Score:** 1/10 (MINIMAL)

**Behavioral Preservation:** Simple delegation - can move code wholesale then call from scanner.py

---

### 🟡 Lane 2: Configuration/Setup (LOW RISK, LOWER PRIORITY)
**Size:** ~300 lines / 10 functions
**Target Module:** `scanner_submodules/scanner_config.py`

**Candidate Functions:**
- `resolve_default_style_guide_source()`, `_refresh_policy()`
- All `load_*()` config loaders
- `_load_section_display_titles()`, `_resolve_section_selector()`

**Risk Score:** 2/10
**Assessment:** Lower priority than Lane 1 (less central to processing), mostly already delegated to submodules

---

### 🟡 Lane 3: Data Loading & File Discovery (LOW RISK, GOOD FOR BATCH)
**Size:** ~300 lines / 14 functions
**Combined Extraction Target:** `scanner_submodules/scanner_discovery.py` (already partially exists)

**Candidate Functions:**
- `load_meta()`, `load_variables()`, `load_requirements()`
- `_parse_yaml_candidate()`, `_load_role_variable_maps()`
- All `_iter_role_*()` functions
- `_map_argument_spec_type()`, `_collect_yaml_parse_failures()`

**Risk Score:** 2/10
**Assessment:** Good candidates, mostly simple loaders (already exists: `scan_discovery.py`)

---

### 🟠 Lane 4: Requirements/Collections (VERY LOW PRIORITY)
**Size:** ~150 lines
**Target Module:** Already in `requirements` submodule (thin wrappers remain)

**Risk Score:** 3/10
**Assessment:** Low impact, mostly delegated already

---

### 🔴 Lane 5: Runbook/Report (ALREADY EXTRACTED, LOW PRIORITY)
**Size:** ~200 lines
**Target Module:** Already in `runbook`, `scanner_report` submodules

**Risk Score:** 3/10
**Assessment:** Thin wrappers remain, delegated to submodules

---

### ⛔ NOT RECOMMENDED FOR EXTRACTION

**Variable Row Building (~500 lines):**
- Risk: MEDIUM - orchestration-dependent
- **Defer to Phase B:** After orchestration is simplified

**Task/README Scanning (~600 lines):**
- Risk: MEDIUM - Jinja/YAML analysis dependent
- **Defer to Phase B:** After variable extraction simplifies flow

**Output Rendering (~900 lines):**
- Risk: MEDIUM-HIGH - complex inter-dependencies
- **Defer to Phase C/D:** After core data flow streamlined

**Main Orchestration (~750 lines):**
- Risk: CRITICAL - cannot be extracted (is the orchestrator)
- **Phase D Goal:** Keep this as thin coordinator only

---

## Recommendation: Lane 1 Selection

### ✅ **LANE 1: Error/Uncertainty Handling**

**Selection Rationale:**
1. **Lowest Risk:** Minimal dependencies, clear boundaries, already partially extracted
2. **Easy to Test:** Can be tested with simple row dicts, no orchestration mocking needed
3. **Behavioral Preservation:** Code moves wholesale, thin wrapper calls it
4. **Quick Win:** ~300 lines, clear extraction pattern
5. **Unblocks Future Lanes:** Later extraction of variable row building depends on cleanup in this area
6. **Existing Infrastructure:** Already has `scan_metrics` submodule, can extend pattern

### Implementation Plan (if executed in Phase B1):

1. **Create** `src/prism/scanner_submodules/scanner_errorhandling.py`
   - Copy functions: `_build_referenced_variable_uncertainty_reason()`, `_append_non_authoritative_test_evidence_uncertainty_reason()`, `_collect_non_authoritative_test_variable_evidence()`, etc.
   - Copy constants: `NON_AUTHORITATIVE_TEST_EVIDENCE_*`
   - Add docstrings connecting to scanner.py concepts

2. **Update scanner.py**
   - Import from new module: `from .scanner_submodules.scanner_errorhandling import (...)`
   - Delete original function definitions
   - Keep wrapper functions if needed for compatibility (likely not needed)

3. **Add Tests** (if warranted)
   - Test `_build_referenced_variable_uncertainty_reason()` with sample row dicts
   - Test `_attach_non_authoritative_test_evidence()` with file evidence
   - Test probability computation edge cases

4. **Validate**
   - Run full test suite: `pytest -xvs` (expect 746 tests pass)
   - Test scanner execution end-to-end

---

## Alternative Lanes (if Lane 1 deemed too narrow)

### 🟡 **COMBINED PLAN: Error Handling + Configuration Setup (500 lines)**
Merge Lanes 1 + 2:
- `scanner_submodules/scanner_setup.py` with error + config functions
- Risk increase: minimal (still ~2/10)
- Scope increase: ~67%
- Value increase: Removes 500 lines from scanner.py in one PR

---

## Success Metrics (Phase A)

- [x] All 150 functions categorized
- [x] 11 clusters identified with line counts
- [x] 5 ranked extraction candidates with risk scores
- [x] Lane 1 selected with clear rationale
- [x] Implementation plan documented (ready for Phase B1)
- [ ] (Phase B1) Run extraction and full test validation
- [ ] (Phase B2) Update modernization-plan.md

---

## Next Steps

**If proceeding to Phase B1 (Lane 1 Extraction):**
1. Create `scanner_errorhandling.py` test file with simple unit tests
2. Extract error/uncertainty code
3. Update imports in scanner.py
4. Run full test suite
5. Commit with message linking to Item 13

**If deferring Lane 1:**
- Continue to Phase B with different lane selection
- Recommended: Lanes 2+3 combined (Data Loading + Config)

---

Generated: 2026-03-27 | Phase A Complete
