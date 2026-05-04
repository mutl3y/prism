# Parent Bundle Regrade After Wave A

Date: 2026-05-04
Plan: `mutl3y-review-20260504-g73`

## Verdict

- `G73-H04`: High retired. The cache/runtime-path failure mode that justified High severity is closed because registry mutation now changes runtime wiring identity through `PluginRegistry.get_state_fingerprint()`, and the isolated scan-pipeline registry view forwards that fingerprint. The canonical default registry remains process-global and mutable by explicit callers, but that remaining seam is visible composition behavior rather than hidden stale-cache corruption.
- `G73-H05`: High retired. Prepared-policy runtime invariants are now defended on the hot path: malformed bundles are rejected, stateful opaque prepared-policy members bypass cache use unless they expose a semantic `cache_fingerprint()`, and the non-collection entrypoint still routes through the canonical prepared-policy bundle seam. Remaining loose helper typing does not currently reopen the runtime behavior that made this bundle High.

## Evidence Used

- `src/prism/scanner_plugins/registry.py` revision fingerprinting and snapshot propagation.
- `src/prism/scanner_core/scan_cache.py` runtime registry fingerprint usage.
- `src/prism/api_layer/plugin_facade.py` isolated registry fingerprint forwarding.
- `src/prism/api_layer/non_collection.py` prepared-policy cache bypass for uncacheable stateful bundle members.
- `src/prism/tests/test_t3_03_scan_cache.py::test_build_runtime_wiring_identity_tracks_registry_state_revision`
- `src/prism/tests/test_api_cli_entrypoints.py::test_fsrc_api_run_scan_bypasses_cache_for_uncacheable_prepared_policy_bundle`
- `src/prism/tests/test_api_cli_entrypoints.py::test_fsrc_non_collection_run_scan_uses_canonical_policy_bundle_fn`

## Residual Non-High Debt

- The default registry remains a deliberate process-wide composition seam. If stronger mutation governance is wanted later, that should be tracked as a new lower-severity ownership follow-up instead of kept open as a stale High.
- `PreparedPolicyBundle` still carries protocol-shaped opaque members by design. Additional type tightening can continue as routine contract hardening, but it is no longer required to prevent cache-key collisions or hidden runtime drift.
