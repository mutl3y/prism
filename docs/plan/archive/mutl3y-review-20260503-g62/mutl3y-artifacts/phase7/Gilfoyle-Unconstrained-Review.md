# Gilfoyle Unconstrained Review

- Agent: Gilfoyle Code Review God Mode
- Task: g62-gilfoyle-unconstrained-review
- Plan: mutl3y-review-20260503-g62
- Scope: unconstrained post-close review across closure artifacts, API/api_layer, scanner_core, scanner_kernel, plugin facade, cache seam, and adjacent tests

## Findings

### High: public API path downgrades reserved unsupported platforms from `platform_not_supported` to `platform_not_registered`

- Closure impact: reopen-worthy. This invalidates the g62 closure claim that the remaining registry/bootstrap seam is merely clarity debt. The public API seam still changes runtime behavior.
- Primary anchors:
  - `src/prism/api.py:256-347`
  - `src/prism/api.py:291`
  - `src/prism/api_layer/plugin_facade.py:207-303`
  - `src/prism/api_layer/plugin_facade.py:308-311`
  - `src/prism/scanner_kernel/orchestrator.py:424-497`
  - `src/prism/scanner_kernel/orchestrator.py:458-459`
  - `src/prism/tests/test_platform_routing_fail_closed.py:58-67`
  - `src/prism/tests/test_platform_routing_fail_closed.py:140-149`
- What the code does:
  - `prism.api.run_scan()` fetches `plugin_facade.get_default_scan_pipeline_registry()` and passes that isolated wrapper into `api_layer.non_collection.run_scan()` as `default_plugin_registry`.
  - `plugin_facade.isolate_scan_pipeline_registry()` forwards scan-pipeline lookups plus several plugin getters, but it does not expose `is_reserved_unsupported_platform()`.
  - `scanner_kernel.orchestrator.route_scan_payload_orchestration()` distinguishes reserved unsupported platforms only when `registry.is_reserved_unsupported_platform(plugin_name)` exists and returns true.
  - Because the API path supplies the isolated wrapper instead of the canonical registry, the reserved-platform branch is skipped and the code falls through to the explicit-selection branch, raising `platform_not_registered` instead.
- Why this matters:
  - The repository already defines a stronger fail-closed contract for reserved platforms. The lower-level tests in `test_platform_routing_fail_closed.py` explicitly assert that `terraform` and `kubernetes` raise `platform_not_supported` when routed with the canonical registry.
  - The public API path silently weakens that contract and misclassifies a reserved capability as merely absent registration. That is not naming debt. It is behavioral drift on a public execution path.
  - This sits directly adjacent to closed finding `G62-H01`, whose closure note claimed the remaining bootstrap/DI/facade seams were canonical rather than duplicated authority. The seam still mutates observable behavior, so the close was overstated.
- Falsifiable evidence:
  - Read-only public API probe:
    - `api.run_scan(<tiny-role>, scan_pipeline_plugin='terraform')` raised `platform_not_registered`.
  - Read-only lower-level control probe:
    - `route_scan_payload_orchestration(..., scan_options={'scan_pipeline_plugin': 'terraform'}, registry=get_default_plugin_registry())` raised `platform_not_supported`.
  - That difference is only explainable if the registry object supplied by the API path is missing behavior relied on by the kernel routing contract.
- Why the current tests did not catch it:
  - `src/prism/tests/test_platform_routing_fail_closed.py` covers the kernel route directly with the canonical registry.
  - The reviewed API-entrypoint tests cover scan-pipeline isolation and bundle/cache behavior, but they do not cover reserved unsupported platform routing through `prism.api.run_scan()`.

## Open Questions / Assumptions

- Assumption: the intended public contract is the one asserted in `src/prism/tests/test_platform_routing_fail_closed.py`, namely that reserved unsupported platforms fail with `platform_not_supported`, not `platform_not_registered`.
- Open question: should the API layer pass the full canonical plugin registry into non-collection runtime orchestration, or should the isolated wrapper be expanded to preserve `is_reserved_unsupported_platform()` and any other kernel-visible registry semantics? Either fix would repair the contract; the current state does not.

## Summary

g62 was closed too aggressively. One reopen-worthy defect remains on the live public API path: the registry-isolation seam changes reserved-platform failure classification from `platform_not_supported` to `platform_not_registered`. Everything else reviewed here was residual debt or correctly closed, but this one is an actual contract break, not documentation drama.
