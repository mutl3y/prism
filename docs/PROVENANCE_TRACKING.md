# Variable Provenance Tracking Architecture

## Goal
Track the source, location, and confidence level of each discovered variable across `defaults/`, `vars/`, `meta/`, `include_vars`, `set_fact`, and role README inputs.

## Core Concepts

### Provenance Data Structure
Each variable will carry provenance metadata:

```python
{
    "name": "var_name",
    "value": "default_value",
    "provenance": {
        "source_file": "defaults/main.yml",      # relative path within role
        "line": 42,                               # line number in source file
        "confidence": "explicit",                 # explicit|inferred|dynamic_unknown
        "source_type": "defaults",                # defaults|vars|meta|include_vars|set_fact|readme
        "notes": "optional additional context"
    }
}
```

### Confidence Levels

1. **`explicit`** — Direct assignment in discoverable file
   - `var_name: value` in defaults/main.yml
   - Variable explicitly defined in meta/main.yml
   - Static `include_vars: path/to/file.yml` with discovered content

2. **`inferred`** — Derived from context but not directly stated
   - Variable name extracted from `set_fact` but value cannot be determined statically
   - Variable referenced in template with `default(...)` filter
   - Variable mentioned in role README variable table (discovered via README parsing)

3. **`dynamic_unknown`** — Present but cannot resolve statically
   - Dynamic `include_vars` that depends on task conditions or variables
   - `set_fact` with computed value (e.g., `set_fact: my_var: "{{ other_var }}_suffix"`)
   - Role parameter inputs (referenced in docs but not code)

### Source Types

- **`defaults`** — From `defaults/main.yml`
- **`vars`** — From `vars/main.yml`
- **`meta`** — From `meta/main.yml` (e.g., min/max ansible versions, platform vars)
- **`include_vars`** — From files included via `include_vars` tasks
- **`set_fact`** — From `set_fact` task definitions
- **`readme`** — From documented variable tables in role README

## Integration Points

### Scanner Pipeline

1. **`build_variable_insights()`** (scanner.py)
   - Current: Returns variable dict
   - New: Each variable includes `provenance` metadata
   - Responsibility: Track source file and line as variables are collected

2. **`describe_variable()`** (scanner.py helper)
   - Current: Returns description string
   - New: Populated from provenance data + inferred context
   - Includes confidence level in output

3. **Variable Rendering** (scanner.py, templates)
   - If confidence is `dynamic_unknown`, append annotation: `(value not statically determinable)`
   - If confidence is `inferred`, append annotation: `(may require documentation review)`
   - Only `explicit` values render without annotation (default behavior)

### Scanner Report Output

New scanner-report section: **Variable Provenance Summary**

```
## Variable Provenance Summary

- Explicit (directly discoverable): 12 variables
- Inferred (derived from context): 5 variables
- Dynamic/Unknown: 3 variables

Unknown/Dynamic Variables:
| Variable | Location | Confidence | Notes |
|---|---|---|---|
| deploy_mode | tasks/deploy.yml:28 | inferred | Value controlled by task conditions |
| custom_path | set_fact (line 45) | dynamic_unknown | Computed from other variables |
```

### JSON Output

Variables now include provenance:

```json
{
  "variables": [
    {
      "name": "app_port",
      "value": "8080",
      "provenance": {
        "source_file": "defaults/main.yml",
        "line": 12,
        "confidence": "explicit",
        "source_type": "defaults"
      }
    }
  ]
}
```

## Implementation Phases

### Batch 1: Provenance Infrastructure (Foundation)
- Add `VariableProvenance` TypedDict to scanner.py
- Update `build_variable_insights()` to track source_file, line, confidence
- Update `Variable` rendering helpers to include provenance in output
- Wire provenance through JSON and dict outputs
- Add tests for basic provenance tracking

### Batch 2: Enhance defaults/vars/meta Coverage
- Ensure all collected variables from these sources carry explicit confidence
- Track line numbers accurately for all three sources
- Add descriptive notes for edge cases (empty values, comments, etc.)
- Test against mock_role and enhanced_mock_role

### Batch 3: include_vars Tracking
- Parse `include_vars` task references to find static paths
- Load included files and track discovered variables
- Mark as `explicit` (file found and loaded) vs `inferred` (referenced but not found)
- Add tracking for conditional includes (mark confidence as `dynamic_unknown`)

### Batch 4: set_fact & Task Defaults
- Extract variable names from `set_fact` task definitions
- Track confidence based on value complexity:
  - Simple literals = `explicit`
  - Templates/references = `inferred`
  - Computed/conditional = `dynamic_unknown`
- Capture task-level default overrides via task `vars`

### Batch 5: README & Role Parameters
- Extract variables from role README variable tables (source_type = `readme`)
- Mark as `inferred` (documented reference without code verification)
- Identify role parameter inputs mentioned in docs/comments
- Add optional provenance annotation in generated README

## Breaking Changes

None initially. Provenance is **additive**:
- Existing variable output format unchanged by default
- Annotations only appear if explicitly requested (scanner report, JSON payload)
- README rendering unchanged unless new annotation flags are set

## Testing Strategy

1. Add provenance tests to `test_scan.py`:
   - Verify source_file, line, confidence populated correctly
   - Test all three confidence levels
   - Test source_type enumeration (defaults, vars, meta, etc.)

2. Add end-to-end tests for each batch
   - Mock role with all variable source types
   - Verify scanner report includes provenance summary
   - Verify JSON output contains all metadata

3. Regression tests
   - Ensure existing variable rendering unchanged
   - Verify tests still pass after each batch

## Success Criteria

- ✅ All variables in defaults/vars/meta tracked with line numbers and confidence
- ✅ include_vars references resolved where statically discoverable
- ✅ set_fact definitions extracted with confidence labels
- ✅ Scanner report shows provenance summary by confidence level
- ✅ JSON output includes all provenance metadata
- ✅ Annotations optional and non-breaking to existing output
- ✅ >= 90% test coverage for new provenance code
