# Principal Post-Wave2 Review

Scope: fresh whole-codebase review of `/raid5/source/test/prism/src/prism`.

Method:

- Code-only review.
- No reliance on `docs/plan` artifacts, `AGENTS.md`, or prior findings.
- Broad pass across runtime architecture, public boundaries, trust boundaries, import-time side effects, process-global state, fail-open behavior, and contract strength.

Result:

- Fewer than 10 High issues remain.
- Residual set: 4 High, 7 Medium.

## High

### H1. Plugin integrity still fails open into hardwired fallback behavior

Why this is durable:

- The canonical prepared-policy path still substitutes fallback plugins instead of failing the contract when plugin resolution, construction, or shape validation goes wrong.

Code evidence:

- `src/prism/scanner_plugins/defaults.py:62` documents an explicit `ANSIBLE-FIRST PRODUCT CONSTRAINT`.
- `src/prism/scanner_plugins/defaults.py:82` through `src/prism/scanner_plugins/defaults.py:87` create module-level fallback singleton instances for task parsing, annotation parsing, traversal, variable extraction, YAML parsing, and Jinja analysis.
- `src/prism/scanner_plugins/bundle_resolver.py:102` derives plugin strictness from `scan_options["strict_phase_failures"]`.
- `src/prism/scanner_plugins/bundle_resolver.py:104` through `src/prism/scanner_plugins/bundle_resolver.py:130` fill missing prepared-policy slots by calling resolver functions.
- `src/prism/scanner_plugins/defaults.py:200`, `src/prism/scanner_plugins/defaults.py:232`, and `src/prism/scanner_plugins/defaults.py:330` return `fallback_plugin` on malformed shape, constructor failure, or missing registry plugin.

Impact:

- Runtime/plugin integrity is still coupled to content-tolerance mode. A broken or incomplete plugin topology can silently devolve to the built-in fallback stack instead of failing closed.

### H2. Collection scans still demote runtime/control-plane failures into partial success

Why this is durable:

- The collection facade still treats runtime exceptions from individual role scans as recoverable per-role fallout.

Code evidence:

- `src/prism/api.py:50` through `src/prism/api.py:52` declare `PrismRuntimeError` and `RuntimeError` as collection-role runtime recoverable errors.
- `src/prism/api_layer/collection.py:161` merges those runtime exceptions into `recoverable_scan_errors`.
- `src/prism/api_layer/collection.py:199` catches `recoverable_scan_errors` and records a failure entry instead of aborting the collection scan.

Impact:

- Broken runtime invariants inside a role scan can still produce a success-shaped collection payload with failures appended, which weakens the public reliability contract for batch scans.

### H3. The public and runtime boundaries still rely on dict-and-Any pipes instead of enforceable contracts

Why this is durable:

- The highest-value boundaries are still typed as open dictionaries and `Any`, so cross-boundary drift remains a runtime problem instead of a mechanically prevented one.

Code evidence:

- `src/prism/api.py:58` through `src/prism/api.py:88` keep `run_scan()` as a retained public compatibility seam returning `dict[str, object]`.
- `src/prism/api.py:137` injects the default plugin registry and internal runtime classes directly into that public call.
- `src/prism/scanner_data/__init__.py:39` through `src/prism/scanner_data/__init__.py:46` define `RoleScanResult` and `RepoScanResult` as wrappers around `payload: dict[str, Any]`.
- `src/prism/scanner_plugins/interfaces.py:24` through `src/prism/scanner_plugins/interfaces.py:92` define variable-discovery, feature-detection, and scan-pipeline protocols in terms of `dict[str, Any]`.
- `src/prism/scanner_core/protocols_runtime.py:22` through `src/prism/scanner_core/protocols_runtime.py:86` still expose kernel/runtime seams through `Any` and `dict[str, Any]` contracts.

Impact:

- Product-readiness is limited because the system has structured modules but not equally strong public/runtime contracts. Boundary regressions are still easy to express and hard to exclude.

### H4. `scanner_plugins.defaults` still owns a second, hidden composition path outside the canonical runtime

Why this is durable:

- Exported helper flows still construct their own synthetic DI state instead of reusing the canonical request-prepared runtime path.

Code evidence:

- `src/prism/scanner_plugins/defaults.py:469` defines `_make_standalone_di()`.
- `src/prism/scanner_plugins/defaults.py:478` calls `ensure_prepared_policy_bundle(scan_options=options, di=None)`.
- `src/prism/scanner_plugins/defaults.py:481` sets `di.plugin_registry = None` on the synthetic DI object.
- `src/prism/scanner_plugins/defaults.py:485` through `src/prism/scanner_plugins/defaults.py:530` use that synthetic DI in exported helper functions such as `extract_role_notes_from_comments()` and the dynamic-include collectors.

Impact:

- Prism still has more than one live composition root for plugin/policy resolution. That increases the odds that helper behavior diverges from the canonical scan runtime under plugin or registry changes.

## Medium

### M1. Style alias state is still process-global and explicitly not thread-safe

Code evidence:

- `src/prism/scanner_readme/style_config.py:43` defines `refresh_policy_derived_state()`.
- `src/prism/scanner_readme/style_config.py:47` states the function is `NOT thread-safe`.
- `src/prism/scanner_readme/style_config.py:54` and `src/prism/scanner_readme/style_config.py:55` mutate `_STYLE_SECTION_ALIASES` in place.

Impact:

- Concurrent scans can still observe shared mutable README style-alias state.

### M2. Default event listeners remain process-global and leak into every new DI container

Code evidence:

- `src/prism/scanner_core/events.py:146` defines `_DEFAULT_LISTENERS` at module scope.
- `src/prism/scanner_core/events.py:150` through `src/prism/scanner_core/events.py:173` expose global registration and lookup.
- `src/prism/scanner_core/di.py:189` seeds each new container from `get_default_listeners()`.
- `src/prism/progress.py:52` through `src/prism/progress.py:56` temporarily mutate that global listener set.

Impact:

- Observability configuration is still ambient process state rather than purely request-scoped wiring.

### M3. Malformed `policy_context` is silently dropped during canonical option normalization

Code evidence:

- `src/prism/scanner_core/scan_request.py:26` defines `_normalize_policy_context()`.
- `src/prism/scanner_core/scan_request.py:30` returns `(None, [])` for any non-dict `policy_context`.

Impact:

- Callers can provide malformed routing/policy context and quietly fall back to default behavior with no warning payload.

### M4. Malformed policy config input still reverts enforcement toggles to defaults

Code evidence:

- `src/prism/scanner_config/policy.py:48` logs and returns an empty dict when the config root is not a mapping.
- `src/prism/scanner_config/policy.py:152`, `src/prism/scanner_config/policy.py:163`, `src/prism/scanner_config/policy.py:182`, `src/prism/scanner_config/policy.py:193`, `src/prism/scanner_config/policy.py:212`, `src/prism/scanner_config/policy.py:223`, `src/prism/scanner_config/policy.py:242`, and `src/prism/scanner_config/policy.py:253` all return the default value when coercion fails or the config is malformed.

Impact:

- Broken policy configuration still changes behavior back to defaults rather than producing a hard configuration failure.

### M5. README rendering still defaults missing `platform_key` to `ansible`

Code evidence:

- `src/prism/scanner_readme/guide.py:68` and `src/prism/scanner_readme/guide.py:95` read `metadata["platform_key"]`.
- `src/prism/scanner_readme/guide.py:71` and `src/prism/scanner_readme/guide.py:98` log and default to `'ansible'` when it is missing or empty.

Impact:

- Missing routing metadata still becomes platform-specific rendering behavior instead of a contract error.

### M6. Style-guide source resolution still depends on ambient environment and current working directory

Code evidence:

- `src/prism/scanner_config/style.py:26` defines `resolve_default_style_guide_source()`.
- `src/prism/scanner_config/style.py:63` reads `PRISM_STYLE_SOURCE` from the environment.
- `src/prism/scanner_config/style.py:67` searches `Path.cwd()`.
- `src/prism/api.py:359` republishes this helper on the public API surface.

Impact:

- Output can still change based on process environment and working directory rather than explicit request input.

### M7. Kernel/plugin enablement still depends on process-global environment flags

Code evidence:

- `src/prism/scanner_kernel/repo_context.py:69` through `src/prism/scanner_kernel/repo_context.py:70` gate kernel behavior on `PRISM_KERNEL_ENABLED`.
- `src/prism/scanner_plugins/ansible/feature_flags.py:13` through `src/prism/scanner_plugins/ansible/feature_flags.py:16` gate Ansible plugin enablement on `PRISM_KERNEL_ENABLED` and `PRISM_ANSIBLE_PLUGIN_ENABLED`.

Impact:

- Two identical API calls can still take materially different execution paths because ambient process flags changed between calls.

## Bottom Line

The wave-2 fixes removed several concrete trust-boundary and mutability defects. The residual risk is now concentrated in composition ownership, fail-open plugin fallback behavior, and weak public/runtime contract boundaries. That is materially better than earlier slices, but it is not yet product-ready architecture.
