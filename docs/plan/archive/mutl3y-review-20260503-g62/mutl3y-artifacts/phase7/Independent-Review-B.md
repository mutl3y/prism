# Independent Review B - g62 Closure Slice

Review scope: code
Task: g62-independent-review-b
Plan: mutl3y-review-20260503-g62
Focus: api alias retirement, prepared bundle boundary hardening, cache-key and cache-integration closure changes
Reviewed inputs: findings.yaml, phase5 wave-6 barrier summary, phase6 foreman full-gate summary, src/prism/api.py, src/prism/api_layer/plugin_facade.py, src/prism/api_layer/non_collection.py, src/prism/scanner_core/scanner_context.py, src/prism/scanner_core/scan_cache.py, src/prism/tests/test_scanner_context.py, src/prism/tests/test_t3_03_scan_cache.py, src/prism/tests/test_g03_scan_cache_integration.py, AGENTS.md, docs/PRD.yaml

## Findings (ordered by severity)

No findings were identified that should reopen g62 or overturn the recorded closure. The promoted defects in the requested slice appear to be retired in the code that now ships, and the phase-6 full gate summary is consistent with the runtime and test paths I reviewed.

Residual low-severity concerns only:

- Low: alias retirement is complete at the public surface, but internal code still type-couples the API facade to a private non-collection alias.
  - Location: src/prism/api.py:514 and src/prism/tests/test_api_cli_entrypoints.py:17
  - Evidence: api.py no longer re-exports the private alias, but scan_role still casts run_scan to `Callable[..., api_non_collection._NormalizedNonCollectionResult]`, and the API entrypoint tests still import that private alias directly from api_layer.non_collection.
  - Why it matters: this is no longer a consumer-facing contract leak, so it does not block closure, but it preserves hidden rename-coupling between the public API layer and a private inner type name. A future private alias rename will break internal typing/tests even though the public contract is already stable.
  - Recommendation: when this seam is touched again, replace the private-alias reference with a public payload protocol or the existing RunScanOutputPayload-oriented callable shape so the API facade stops depending on a private symbol name.

- Low: cache-key hardening now distinguishes missing and malformed prepared bundles, but the canonical bundle fingerprint still assumes policy instances are safely represented by type identity plus primitive container state.
  - Location: src/prism/api_layer/non_collection.py:375-450 and src/prism/tests/test_t3_03_scan_cache.py:205
  - Evidence: `_bundle_value_fingerprint` collapses opaque objects to module.qualname strings, and `_prepared_policy_bundle_cache_marker` uses that fingerprint when the bundle passes the cacheable-shape check. The reviewed tests cover missing/malformed bundle markers and generic cache-key stability, but not a case where two same-class prepared policy instances carry different runtime state.
  - Why it matters: today this is acceptable because the plugin architecture leans heavily on stateless policy objects, and the active g62 defect was the fail-open malformed-bundle path rather than same-class state drift. This is still a real maintenance assumption: if prepared policy plugins later gain scan-specific instance state, cache-key collisions could reappear without a guardrail failing first.
  - Recommendation: keep this as follow-up debt rather than a closure blocker. A future guardrail could either assert statelessness for prepared-policy slots that participate in cache keys or add a focused test proving same-class/different-state bundles are impossible or intentionally irrelevant.

## What Holds Up

- The prepared-bundle boundary hardening is real for the closure target. ScannerContext now fails closed on missing bundles and rejects malformed task_line_parsing or jinja_analysis placeholders before orchestration begins. That matches the closure note for G62-H02 rather than merely moving the failure deeper into runtime.
- The cache-path claim for G62-M01 also holds. non_collection.run_scan normalizes cached hits through `_normalize_non_collection_result_shape` before returning them, so cached payloads are not trusted blindly, and single-file unreadable paths no longer collapse to the same sentinel-only digest in scan_cache.py.
- The wave-6 alias retirement claim is materially correct. api.py no longer exports the private normalized-result alias, and the remaining plugin_facade.ensure_prepared_policy_bundle usage is an internal api_layer seam rather than a reopened public-surface leak.
- The phase-6 foreman summary does over-explain the cache integration fixture repair, but not in a way that invalidates closure. The integration test route remains thin; however, `validate_run_scan_output_payload` intentionally supplies defaults for optional fields, so the repaired test still exercises the normalized cache round-trip successfully.

## Verdict

No reopen-worthy defect was found in the g62 closure slice. g62 can remain closed; the only remaining issues in this review are low-severity hidden-coupling and future-guardrail concerns, not active closure blockers.

Reviewer: GitHub Copilot
Date: 2026-05-03
