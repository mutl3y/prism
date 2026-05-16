**Touched-file mypy errors**

- **src/prism/api.py**: 4 errors — Fixable Tier 0
  - Categories: Protocol/Callable/Protocol mismatch(1), Other(1), Arg/Signature mismatch(2)
  - Examples: Argument "write_collection_runbook_artifacts_fn" to "scan_collection" has incompatible type "def write_collection_runbook_artifacts(*, role_name: str, metadata: dict[str, object], runbook_output_dir: str | None, runbook_csv_output_dir: str | None) -> None"; expected "WriteCollectionRunbookArtifactsFn"  [arg-type]; "WriteCollectionRunbookArtifactsFn.__call__" has type "def __call__(self, *, role_name: str, metadata: ScanMetadata, runbook_output_dir: str | None, runbook_csv_output_dir: str | None) -> None"; Argument "metadata" to "write_collection_runbook_artifacts_facade" has incompatible type "dict[str, object]"; expected "ScanMetadata"  [arg-type]

- **src/prism/scanner_core/di.py**: 13 errors — Fixable Tier 0
  - Categories: Other(13)
  - Examples: Single overload definition, multiple required  [misc]; Single overload definition, multiple required  [misc]; Single overload definition, multiple required  [misc]

- **src/prism/tests/test_policy_integration.py**: 1 errors — Tier 1 likely
  - Categories: TypedDict(1)
  - Examples: TypedDict "ScanPolicyContext" has no key "mutated"  [typeddict-unknown-key]

**Touched-files total errors:** 18

**Pre-existing repo-wide mypy errors**

- Total (excluding touched files): 130

- Categories summary:
  - Other: 89
  - TypedDict: 18
  - Arg/Signature mismatch: 14
  - Return type / assignment: 4
  - Missing import / name: 4
  - Operator/type op: 1

**Escalation criteria (Tier 0 vs Tier 1→2)**

- Tier 1→2 escalation recommended when:
  - A TypedDict contract is violated across many modules (>20 errors) indicating a canonical ScanOptions/ScanMetadata shape mismatch; or
  - Protocol/Callable signature mismatches affect public API types (e.g., WriteCollectionRunbookArtifactsFn) requiring API/design change; or
  - Changes imply contract-wide signature/behavioural changes (tests + runtime callers require coordinated updates).

- Tier 0 fixes (low-cost) when:
  - Local argument/return incompatibilities in a single file; or
  - Operator/type errors fixable by narrow annotation/casts; or
  - Test fixtures constructing dicts can be changed to match TypedDict (or use cast/typed helpers) in localized waves.

- Observation: TypedDict errors=18, Protocol-ish errors=0 → mostly Tier 0 fixable; escalate only if blockers remain after waves.

**Recommended builder wave order**

1. Fast Tier-0 waves (low-risk fixes):
   - Fix local argument/return mismatches in recently touched files (`api.py`, `scanner_core/di.py`, `scanner_core/scanner_context.py`).
   - Apply casts or narrow annotations where safe; update tests to use helper constructors for ScanOptions dicts where feasible.
2. TypedDict stabilization wave:
   - Normalize `ScanOptionsDict` and related TypedDicts: add total=False variants for test fixtures or provide canonical builders.
3. Protocol/Callable signatures wave (Tier-1 if needed):
   - Reconcile `WriteCollectionRunbookArtifactsFn`-style Callable/Protocol mismatches across APIs and callers; treat as coordinated change with reviews.
4. Final QA gate: run mypy, pytest, and iterate.

**Top hits (files with most errors)**

- src/prism/tests/test_t1_02_coverage_lift_batch2.py: 24 errors
- src/prism/tests/test_execution_request_builder.py: 18 errors
- src/prism/scanner_core/di.py: 13 errors
- src/prism/scanner_plugins/ansible/feature_detection.py: 12 errors
- src/prism/scanner_core/plugin_resolver.py: 10 errors
- src/prism/tests/test_kernel.py: 10 errors