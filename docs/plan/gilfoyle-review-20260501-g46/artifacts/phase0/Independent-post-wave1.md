# Independent Post-Wave1 Architecture Review

Scope: broad, code-only review of `/raid5/source/test/prism/src/prism` after the current g46 wave-1 fixes. I did not read or rely on plan artifacts, AGENTS, or prior review notes for this pass.

Residual set: 10 High, 4 Medium.

Overall verdict: the codebase is materially improved, but it is not yet product-ready for durable multi-platform/plugin-safe evolution. The dominant residual theme is that runtime composition still depends on ambient process state, import-time bootstrapping, and fail-open fallback behavior at several critical plugin and facade boundaries.

## High

1. Importing the plugin package is itself a hidden composition root and third-party code execution point.
   Evidence:
   - `src/prism/scanner_plugins/__init__.py:202` sets `DEFAULT_PLUGIN_REGISTRY = initialize_default_registry()` at module import time.
   - `src/prism/scanner_plugins/bootstrap.py:195` auto-runs `discover_entry_point_plugins(registry=canonical_registry)` during initialization.
   - `src/prism/scanner_plugins/discovery.py:66` loads entry points via `ep.load()`.
   - `src/prism/scanner_plugins/discovery.py:90` executes third-party registration code via `register_callable(target_registry)`.
   Impact: registry access is not a passive read. It mutates global runtime state and executes external code before callers have an explicit bootstrap or trust-boundary decision.

2. Entry-point discovery is fail-open and can leave the process in a silently partial plugin topology.
   Evidence:
   - `src/prism/scanner_plugins/discovery.py:50` defaults `raise_on_error` to `False`.
   - `src/prism/scanner_plugins/discovery.py:74`, `src/prism/scanner_plugins/discovery.py:86`, and `src/prism/scanner_plugins/discovery.py:100` downgrade discovery/registration failures to warnings.
   - `src/prism/scanner_plugins/discovery.py:77`, `src/prism/scanner_plugins/discovery.py:87`, and `src/prism/scanner_plugins/discovery.py:105` continue after those failures.
   - `src/prism/scanner_plugins/bootstrap.py:195` invokes discovery with the default fail-open behavior.
   Impact: the runtime can start with a degraded or incomplete plugin graph without any caller-visible failure, which is a product-readiness problem for plugin composition.

3. Prepared policy-bundle construction is not platform-owned; it is hardwired to Ansible-backed defaults.
   Evidence:
   - `src/prism/scanner_plugins/bundle_resolver.py:105`, `src/prism/scanner_plugins/bundle_resolver.py:120`, and `src/prism/scanner_plugins/bundle_resolver.py:130` resolve generic policy slots on the canonical request path.
   - `src/prism/scanner_plugins/defaults.py:62` explicitly documents an `ANSIBLE-FIRST PRODUCT CONSTRAINT`.
   - `src/prism/scanner_plugins/defaults.py:82` and `src/prism/scanner_plugins/defaults.py:83` instantiate Ansible policy singletons as global fallbacks.
   Impact: runtime routing may select a non-Ansible pipeline, but request preparation still fills the policy bundle with Ansible-native parsing and extraction behavior. That is a fundamental platform-composition defect.

4. Missing plugin registrations fail open to defaults instead of failing closed.
   Evidence:
   - `src/prism/scanner_plugins/defaults.py:200`, `src/prism/scanner_plugins/defaults.py:232`, and `src/prism/scanner_plugins/defaults.py:330` return `fallback_plugin` rather than raising when registry/shape resolution does not produce a usable plugin.
   - `src/prism/scanner_plugins/defaults.py:277` returns `CommentDrivenDocumentationParser()` when no registry plugin is found.
   - `src/prism/scanner_plugins/bundle_resolver.py:105-130` consumes these resolvers on the canonical execution path.
   Impact: registration drift or plugin omission becomes silent behavior substitution instead of an explicit contract failure.

5. The singleton-safety contract for shared plugin slots is advisory, not enforced.
   Evidence:
   - `src/prism/scanner_plugins/registry.py:63` reads `PLUGIN_IS_STATELESS`.
   - `src/prism/scanner_plugins/registry.py:70-73` only warns when a stateless-required slot omits the marker.
   - `src/prism/scanner_plugins/defaults.py:79` and `src/prism/scanner_plugins/defaults.py:113-131` depend on that invariant to justify module-level singleton reuse.
   Impact: the registry accepts plugins into singleton-sensitive slots without a hard guarantee that they are safe to share across scans. One plugin author omission can reopen cross-scan state bleed.

6. README style alias state is global, mutable, and publicly exposed despite being documented as non-thread-safe.
   Evidence:
   - `src/prism/scanner_readme/style_config.py:15-18` stores aliases in module globals and exposes `STYLE_SECTION_ALIASES` as a proxy over shared mutable state.
   - `src/prism/scanner_readme/style_config.py:46-55` explicitly documents in-place global mutation and performs `clear()` / `update()`.
   - `src/prism/scanner_readme/style.py:19-27` re-exports that state and the mutator on the package surface.
   Impact: one scan can rewrite alias behavior for another scan in the same process. This is a real concurrency and multi-tenant isolation problem.

7. Kernel and plugin behavior still depend on process-wide environment flags rather than request-scoped inputs.
   Evidence:
   - `src/prism/scanner_kernel/repo_context.py:16`, `src/prism/scanner_kernel/repo_context.py:37`, and `src/prism/scanner_kernel/repo_context.py:70` gate repo-context construction on `PRISM_KERNEL_ENABLED`.
   - `src/prism/scanner_kernel/collection_context.py:31` gates collection-context construction on the same ambient flag.
   - `src/prism/scanner_plugins/ansible/feature_flags.py:9-10` and `src/prism/scanner_plugins/ansible/feature_flags.py:17` gate Ansible plugin enablement on `PRISM_KERNEL_ENABLED` and `PRISM_ANSIBLE_PLUGIN_ENABLED`.
   Impact: two calls with identical API parameters can take different runtime paths solely because process environment changed. That is hidden global state at a trust boundary.

8. Platform routing falls back to implicit registry order when callers do not specify a platform.
   Evidence:
   - `src/prism/scanner_core/di.py:90-92` falls back to `registry.get_default_platform_key()`.
   - `src/prism/scanner_plugins/registry.py:436` returns `next(iter(source.keys()))` when no explicit default is set.
   Impact: runtime behavior depends on registration order rather than an explicit product contract. Extension packages and registration sequencing can change effective routing without changing API input.

9. `scanner_plugins.defaults` maintains a second composition root that bypasses the canonical DI/registry path.
   Evidence:
   - `src/prism/scanner_plugins/defaults.py:469` defines `_make_standalone_di`.
   - `src/prism/scanner_plugins/defaults.py:478` calls `ensure_prepared_policy_bundle(scan_options=options, di=None)`.
   - `src/prism/scanner_plugins/defaults.py:481` sets `di.plugin_registry = None` on the synthetic DI object.
   Impact: exported helper flows built on this path can resolve a different plugin/policy topology than the canonical scanner execution path. That fractures composition ownership.

10. The public `run_scan` API remains an open dict-returning compatibility seam that wires internal runtime parts directly.
    Evidence:
    - `src/prism/api.py:58` exposes `run_scan` on the public package surface.
    - `src/prism/api.py:88` returns `dict[str, object]` rather than a stable public result contract.
    - `src/prism/api.py:131-137` wires `DIContainer`, `FeatureDetector`, `ScannerContext`, and the default plugin registry into the public call.
    - `src/prism/api_layer/plugin_facade.py:37-39` resolves that registry by importing `DEFAULT_PLUGIN_REGISTRY` directly.
    Impact: the public facade is still a compatibility wrapper over internal composition details, not a stable product boundary.

## Medium

1. Style-guide source resolution is ambient-state driven on the public API surface.
    Evidence:
    - `src/prism/scanner_config/style.py:63` reads `PRISM_STYLE_SOURCE`.
    - `src/prism/scanner_config/style.py:67` searches the current working directory.
    - `src/prism/scanner_config/style.py:75-76` falls back through system and bundled defaults.
    - `src/prism/api.py:359-381` republishes this helper on the public API surface.
    Impact: README/style output can vary with process environment and CWD instead of explicit request input.

2. `api_layer.non_collection` still leaks internal runtime seams through module-level lazy re-exports.
    Evidence:
    - `src/prism/api_layer/non_collection.py:459` re-exports `build_run_scan_options_canonical`.
    - `src/prism/api_layer/non_collection.py:465` re-exports `route_scan_payload_orchestration`.
    - `src/prism/api_layer/non_collection.py:469` re-exports `orchestrate_scan_payload_with_selected_plugin`.
    Impact: the package boundary still exposes internals from scanner_core and scanner_kernel through an API-layer module.

3. Repo scan façade resolution is cached in a hidden module-global singleton.
    Evidence:
    - `src/prism/api_layer/non_collection.py:32` stores `_repo_scan_facade` at module scope.
    - `src/prism/api_layer/non_collection.py:37` mutates that global on first resolution.
    Impact: repo-scan dependency ownership is process-global and harder to isolate in long-lived runtimes.

4. `PluginRegistry` exposes inconsistent list-contract shapes across slots.
    Evidence:
    - `src/prism/scanner_plugins/registry.py:387-389` returns `list[str]` for scan-pipeline plugins.
    - `src/prism/scanner_plugins/registry.py:407-409` returns a `dict[str, type[ReadmeRendererPlugin]]` for readme renderers despite the same `list_*` naming pattern.
    Impact: registry boundary contracts are inconsistent and invite adapter-side `Any` or duck-typing at call sites.

## Bottom Line

The residual architecture risk is still concentrated at composition boundaries, not inside the core scanning logic. The code is closer to a stable scanner, but the runtime remains too dependent on import-time bootstrap, ambient process state, and permissive default substitution to call it fully product-ready.
