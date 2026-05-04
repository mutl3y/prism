# Fresh Independent Review Fix Table

Plan: `mutl3y-review-20260504-g73`
Date: `2026-05-04`
Source: fresh live-source review of `src/prism`, explicitly ignoring prior review artifacts as evidence.

## Fix Queue

| ID | Severity | Status | Primary Files | Problem | Fix Direction | Suggested Gate |
| --- | --- | --- | --- | --- | --- | --- |
| `FIR-H01` | High | New active | `src/prism/scanner_kernel/plugin_name_resolver.py`, `src/prism/scanner_core/di.py`, `src/prism/scanner_core/execution_request_builder.py` | Platform selection resolves as `terraform` in kernel plugin-name routing but `ansible` in DI/runtime assembly when only `scan_options["platform"]` is set. | Centralize platform resolution and either honor `platform` everywhere or reject it everywhere. | Focused test proving `platform` fallback returns the same key through plugin-name resolver, DI, and execution-request assembly. |
| `FIR-H02` | High | Fold into `G73-H04` | `src/prism/scanner_core/scan_cache.py`, `src/prism/api_layer/non_collection.py`, `src/prism/scanner_plugins/registry.py`, `src/prism/scanner_plugins/bootstrap.py` | Runtime cache identity fingerprints mutable registry objects as `type@id`, so registry mutation does not invalidate cached scan output. | Add registry revision/state fingerprint and include it in runtime wiring identity, or disable caching for mutable registries without a fingerprint. | Regression where mutating a valid registry changes runtime wiring identity and cache key. |
| `FIR-H03` | High | Fold into `G73-H05` | `src/prism/api_layer/non_collection.py`, `src/prism/scanner_core/scan_cache.py` | Prepared-policy bundle marker collapses stateful policy instances to class name, allowing different same-class policies to share cache keys. | Require semantic `cache_fingerprint` on opaque prepared-policy members or make opaque bundles uncacheable. | Regression where two same-class policy instances with different state produce distinct markers or bypass caching. |
| `FIR-H04` | High | New active | `src/prism/api_layer/plugin_facade.py`, `src/prism/scanner_plugins/interfaces.py` | Facade wrapper detects orchestration capability on the factory callable, not the produced plugin instance, so callable factories returning orchestrating plugins are downgraded to preflight-only behavior. | Detect and preserve `orchestrate_scan_payload` on the produced instance while retaining payload/context isolation. | Regression where a callable factory returning an orchestrating plugin remains orchestrating after `isolate_scan_pipeline_registry`. |
| `FIR-H05` | High | Fold into `G73-H04` | `src/prism/scanner_plugins/bootstrap.py`, `src/prism/scanner_plugins/registry.py`, `src/prism/api_layer/plugin_facade.py` | The canonical default registry is a process-wide mutable singleton returned directly to callers with mutation APIs. | Expose read-only runtime views for normal consumers and keep mutation behind bootstrap/composition seams with revisioning. | Regression proving default facade consumers cannot mutate the canonical runtime registry directly, or that mutations bump a revision and invalidate cache identity. |

## Behavioral Evidence Captured

```text
platform_resolution: terraform ansible ansible
registry_identity_same_after_valid_mutation: True
bundle_marker_same_for_stateful_instances: True
callable_factory_orchestrate_preserved: False
```

## Recommended Wave Order

1. `FIR-H01` platform-resolution unification. It is small, cross-layer, and blocks clean multi-platform reasoning.
2. `G73-H04` + `FIR-H02` + `FIR-H05` registry lifecycle/cache identity bundle. Treat registry mutation, read-only views, and revisioning as one ownership seam.
3. `G73-H05` + `FIR-H03` prepared-policy cache fingerprint bundle. This is a runtime-contract typing and cache-semantics seam.
4. `FIR-H04` callable factory orchestration preservation. This is a focused plugin-facade compatibility fix and can be parallelized only if it does not overlap the registry bundle.

## Independent Review Pattern That Worked

- Dispatch multiple independent reviewers with different axes: architecture/runtime, security/error handling, adversarial logic, and QA/test gaps.
- Explicitly forbid use of prior review artifacts, memories, and previous scan output as evidence.
- Require live source and tests as the evidence base.
- Ask for candidate Critical/High findings, but require uncertainty downgrades instead of severity inflation.
- After the reviewers return, run small local behavior checks for the top candidates before promoting them.
- Keep the final review findings-first and source-backed; do not let quota pressure invent fake Highs.
