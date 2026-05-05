agent name: Auditor-Regression
artifact path: /raid5/source/test/prism/docs/plan/mutl3y-review-20260504-g69/mutl3y-artifacts/phase6/Auditor-Regression-wave-1.md
verdict: PASS
findings: Direct `api_layer.non_collection.run_scan` now falls back through `plugin_facade.get_default_scan_pipeline_registry()` exactly like the public API seam, and `execution_request_builder` uses that passed registry as runtime authority without re-resolving it later. Caller-supplied `default_plugin_registry` precedence remains intact because the new fallback is gated behind `if default_plugin_registry is None`; this slice does not add a direct explicit-override regression test, so that part is inspection-proven rather than newly test-proven. No obvious regression risk in the direct `run_scan` path.
