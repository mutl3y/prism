**Independent Review A — g62 (post-close, task-scope)**

Review scope: task (g62-independent-review-a)
Reviewed artifacts (minimum): findings.yaml, plan.yaml, phase6 gate summary, api.py, api_layer/non_collection.py, scanner_core/scan_cache.py, test_api_cli_entrypoints.py, test_g03_scan_cache_integration.py

**Findings (ordered by severity)**

- Medium: potential registry-type/semantics ambiguity between API and non-collection layer
  - Location: [src/prism/api.py] (public `run_scan`) and [src/prism/api_layer/non_collection.py] (package `run_scan`)
  - Evidence: `src/prism/api.py` constructs `default_plugin_registry` by calling `plugin_facade.get_default_scan_pipeline_registry()` and passes it into `api_non_collection.run_scan(..., default_plugin_registry=default_plugin_registry)`; `src/prism/api_layer/non_collection.py` if `default_plugin_registry is None` falls back to `plugin_facade.get_default_plugin_registry()`.
  - Why it matters: names and callers imply two distinct registry concepts ("scan-pipeline registry" vs "plugin registry"); passing a scan-pipeline registry into a parameter typed/used as the general `default_plugin_registry` relies on the two registry objects being fully compatible. This is a readability/ownership leak risk and could mask subtle behavioral changes if these registries evolve separately.
  - Recommendation: add a small comment or type alias at the API seam clarifying the expected registry shape (or explicitly normalize/convert the scan-pipeline registry to the expected plugin-registry API before passing). Add a focused unit test that asserts the API-level parameter accepts the scan-pipeline registry object and that lookup methods used by non_collection behave identically.

- Low: missing explicit unit test for malformed `prepared_policy_bundle` cache-marker branch
  - Location: [src/prism/api_layer/non_collection.py] in `_has_cacheable_prepared_policy_bundle_shape` / `_prepared_policy_bundle_cache_marker`
  - Evidence: code treats dicts containing mapping-shaped `task_line_parsing`/`jinja_analysis` as non-cacheable (intentionally), returning the `"malformed"` marker. I did not find a direct unit test in the reviewed tests that asserts the cache-marker returns `("__prepared_policy_bundle_state__", "malformed")` for a deliberately malformed bundle (tests exercise cache hits/misses broadly in test_g03_scan_cache_integration.py but do not exercise malformed-prepared-bundle fingerprinting explicitly).
  - Why it matters: the cache key computation (and therefore cache hits/misses) intentionally depends on distinguishing cacheable vs malformed prepared bundles; lacking a focused test raises a small residual risk that future refactors could regress the malformed detection logic unnoticed.
  - Recommendation: add a small unit test exercising `_prepared_policy_bundle_cache_marker` or an integration test where `scan_options` contains a malformed `prepared_policy_bundle` to assert the cache key uses `("__prepared_policy_bundle_state__","malformed")` and that cached results are not incorrectly fingerprinted.

- Informational: cache integration fixture repair and normalization path verified — no action required
  - Location: [src/prism/tests/test_g03_scan_cache_integration.py] and [docs/.../phase6/foreman-full-gate-summary.md]
  - Evidence: `foreman-full-gate-summary.md` documents the local `RunScanOutputPayload` contract enforcement and that `_cache_test_route()` in the integration test was repaired. The integration tests (test_g03_scan_cache_integration.py) assert correct hit/miss behavior and isolation of returned payloads (mutation after set/get does not leak). The InMemoryLRUScanCache uses `_clone_container_structure` for stored values.
  - Conclusion: the integration test repair addressed the regression exposed by the full-gate rerun; test coverage here is adequate for the LRU backend behaviors exercised.

**Open questions and assumptions**

- Assumption: `plugin_facade.get_default_scan_pipeline_registry()` and `plugin_facade.get_default_plugin_registry()` continue to return registry objects that are functionally compatible for the lookups performed by `api_layer/non_collection.run_scan` (this is true per the tests' monkeypatching, but the naming difference is a readability/ownership concern). Please confirm if the codebase treats these as the same runtime object or deliberately separated registries with overlapping API surfaces.

- Question: are there additional integration tests that intentionally exercise `prepared_policy_bundle` caching behaviour (malformed vs cacheable) beyond the scope of `test_g03_scan_cache_integration.py`? If not, consider adding the small focused test recommended above.

**Short review summary**

- I reviewed the listed plan artifacts, code, and tests. The four promoted/closed findings referenced in `findings.yaml` and the gate summary appear to have been addressed (tests pass per the gate summary). No new critical bugs or behavioral regressions were identified in the reviewed files. Two small residual items remain:
  - a readability/ownership ambiguity around which registry object (`scan_pipeline` vs `plugin`) is passed at the API seam (medium severity: clarity/ownership, not an immediate runtime failure), and
  - a missing focused unit test for the malformed-`prepared_policy_bundle` cache-marker branch (low severity test gap).

- Overall, closure is valid for the reviewed scope (task-level). The full-gate evidence (`pytest -q: 1109 passed, 7 skipped`) supports the claim that runtime behavior regressed by the earlier stub issue was repaired; the residual items are low-to-medium maintenance risks and should be tracked as small follow-ups rather than blockers to closure.

**Suggested next steps (quick)**

- Add a one-line clarifying comment in `src/prism/api.py` near where the registry is fetched, noting the expectation that the scan-pipeline registry is compatible with `api_layer/non_collection` usage.
- Add a unit test asserting the malformed `prepared_policy_bundle` cache marker behavior (or add to existing scan-cache integration tests).

---

Reviewer: GitHub Copilot (independent post-close reviewer)
Date: 2026-05-03

(End of Independent-Review-A)
