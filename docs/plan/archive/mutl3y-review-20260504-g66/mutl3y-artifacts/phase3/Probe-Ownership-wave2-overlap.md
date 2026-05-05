# Probe-Ownership: G66-H01 / G66-H02 overlap

## Scope

- Question: can G66-H01 and G66-H02 be split into disjoint wave-2 implementation slices, or does the shared `execution_request_builder` boundary require serialized/shared ownership?
- Files inspected: `findings.yaml`, `src/prism/scanner_plugins/interfaces.py`, `src/prism/api_layer/plugin_facade.py`, `src/prism/api.py`, `src/prism/api_layer/non_collection.py`, `src/prism/scanner_core/execution_request_builder.py`, `src/prism/scanner_core/scanner_context.py`, `src/prism/scanner_data/contracts_request.py`, and focused tests in `src/prism/tests/test_execution_request_builder.py`, `src/prism/tests/test_scanner_context.py`, `src/prism/tests/test_plugin_kernel_extension_parity.py`.

## Ownership read

### H01 primary ownership

H01 starts outside scanner_core:

- `scanner_plugins/interfaces.py` owns the public scan-pipeline plugin contract and still exposes weak dict-based seams (`process_scan_pipeline(... dict[str, Any], dict[str, Any])`, `orchestrate_scan_payload(... payload: dict[str, Any]) -> dict[str, Any]`).
- `api_layer/plugin_facade.py` redefines a second copy of that runtime contract with slightly different `Any`/`object` widening, then wraps registry factories through `_wrap_scan_pipeline_plugin_factory()`.
- `api.py` owns the public handoff into `api_layer/non_collection.run_scan()` and injects the isolated registry via `plugin_facade.get_default_scan_pipeline_registry()`.

This means H01's conceptual owner is the plugin/facade/API seam, not ScannerContext.

### H02 primary ownership

H02 starts inside scanner_core:

- `execution_request_builder._ScanStateBridge.prepare_scan_context()` assembles the payload handed to `ScannerContext`, and this is where malformed members are currently normalized into acceptable-looking shapes:
  - `_normalize_role_notes()` fills missing buckets with empty lists.
  - `_build_display_variables()` skips rows with missing names and coerces booleans/defaults.
  - `_build_requirements_display()` converts `external_collections` strings into list payloads.
  - YAML parse failures are accepted as `[]` unless the incoming value is already a list.
- `scanner_context.py` then performs another tolerant projection layer:
  - `_copy_scan_metadata()` returns `{}` for non-dict input.
  - `_copy_display_variables()` returns `{}` for non-dict input.
  - `_build_output_payload()` consumes the bridge payload after these coercions.
- `contracts_request.py` owns the target TypedDicts that would need tightening if this handoff becomes fail-closed.

This means H02's conceptual owner is the builder-to-ScannerContext handoff.

## Shared boundary assessment

The overlap is real and write-relevant, not just file-list noise.

- `api_layer/non_collection.py` constructs exactly one `NonCollectionRunScanExecutionRequest` and then consumes its `scan_options`, `runtime_registry`, `strict_mode`, and `build_payload_fn` as a single bundle for kernel routing and payload orchestration.
- `execution_request_builder._assemble_runtime_participants()` wires `ScannerContext` through `prepare_scan_context_fn=lambda opts: _bridge_slot[0].prepare_scan_context(opts, canonical_options)`.
- `execution_request_builder._finalize_execution_request()` finalizes the prepared-policy bundle, replaces scan options on the DI container, and instantiates the scanner context before the request is exposed.

That makes `execution_request_builder` the shared owner of the only hop between the H01 ingress/runtime contract world and the H02 payload-handoff world.

## Can wave 2 be disjoint?

No.

Even if H01 is mostly an outer-seam typing cleanup, its scanner-core touchpoint is the same request object and same builder-owned runtime assembly that H02 must change to make the payload handoff fail closed. There is no separate downstream owner after the builder that would let H02 proceed independently, and there is no separate upstream owner inside scanner_core that would let H01 avoid the builder entirely.

## Is there a one-hop seam split?

Yes, but it is serialized, not disjoint.

Recommended wave-2 shape:

1. Slice A: H01-first, owned as the protocol/facade/API contract tightening slice.
   - Primary files: `scanner_plugins/interfaces.py`, `api_layer/plugin_facade.py`, `api.py`.
   - Builder touch should stay minimal and type-surface only: request signatures/aliases needed to consume the tightened scan-pipeline contracts without changing payload-shaping behavior.

2. Slice B: H02-second, owned as the builder-to-ScannerContext fail-closed slice.
   - Primary files: `execution_request_builder.py`, `scanner_context.py`, `contracts_request.py`.
   - This slice can then make the payload handoff reject malformed role notes, display variables, metadata, YAML failures, and collection displays without simultaneously redesigning the public plugin contract.

## Recommendation

Wave 2 should be a serialized two-slice wave with one shared owner for `execution_request_builder`, not two disjoint parallel slices.

Reason:

- H01 and H02 converge on the same builder-owned request assembly seam.
- The clean split is temporal: outer contract first, then payload handoff.
- Trying to run them in parallel would create cross-slice conflicts over `ScanOptionsDict`/request typing, builder wiring, and the expectations encoded in `test_execution_request_builder.py` and `test_scanner_context.py`.

## Risks / open edges

1. H01 may expand slightly into `scanner_kernel/orchestrator.py` and `scanner_kernel/plugin_name_resolver.py`, because those modules already define their own scan-pipeline Protocols; if those stay divergent, the facade cleanup will stop at the builder boundary instead of truly unifying the contract.
2. H02 may require new explicit validator helpers or stricter TypedDict members in `contracts_request.py`; that is still compatible with serialized ownership, but it increases the chance that H01's type changes should land first to avoid double-churn on request/payload aliases.
