# Scout-ErrorEnvelope Findings (discovery only)

**ScanErrorEntry usage**

- Definition: [src/prism/scanner_data/contracts_request.py](src/prism/scanner_data/contracts_request.py) — `ScanErrorEntry` TypedDict (fields: `phase`, `error_type`, `message`, optional `traceback`, `cause`).
- Runtime usage: primary usage in [src/prism/scanner_core/scanner_context.py](src/prism/scanner_core/scanner_context.py) where ScannerContext maintains `_scan_errors: list[ScanErrorEntry]` and constructs envelopes via `_record_phase_error(...)`.
- Summary count: referenced in 2 primary modules (definition + runtime assembly) and surfaced to tests and output normalization paths.

**`scan_errors` field access (top consumers)**

Top matches (file:match-count):
- [src/prism/scanner_core/scanner_context.py](src/prism/scanner_core/scanner_context.py): 9
- [src/prism/tests/test_scanner_parity.py](src/prism/tests/test_scanner_parity.py): 3
- [src/prism/tests/test_scanner_context.py](src/prism/tests/test_scanner_context.py): 1
- [src/prism/tests/test_errors.py](src/prism/tests/test_errors.py): 1
- [src/prism/scanner_data/__init__.py](src/prism/scanner_data/__init__.py): 1
- [src/prism/scanner_data/contracts_request.py](src/prism/scanner_data/contracts_request.py): 1
- [src/prism/errors.py](src/prism/errors.py): 1

Observations:
- `scan_errors` is primarily populated by `ScannerContext` and then normalized by `prism.errors.normalize_metadata_warnings()` for downstream consumers.
- Tests read/write `scan_errors` for parity and error-normalization verification.

**Exception wrapping patterns**

- Contract (source): [src/prism/errors.py](src/prism/errors.py) defines `PrismRuntimeError` and documents the contract: internal functions may raise `ValueError`/`RuntimeError` for local validation/system issues; layer boundaries must wrap these in `PrismRuntimeError` for public APIs.
- Where `PrismRuntimeError` is raised (examples across layers):
  - [src/prism/api_layer/non_collection.py](src/prism/api_layer/non_collection.py)
  - [src/prism/scanner_kernel/orchestrator.py](src/prism/scanner_kernel/orchestrator.py)
  - [src/prism/scanner_core/di.py](src/prism/scanner_core/di.py)
  - [src/prism/scanner_core/scan_request.py](src/prism/scanner_core/scan_request.py)
  - [src/prism/scanner_plugins/defaults.py](src/prism/scanner_plugins/defaults.py)
  - [src/prism/scanner_config/*](src/prism/scanner_config/) (multiple raises)
  - [src/prism/scanner_io/*](src/prism/scanner_io/) and [src/prism/repo_services.py](src/prism/repo_services.py)
- Raw `ValueError` and other internal raises: frequent inside `src/prism/scanner_core/*` for input/shape validation and guard clauses (e.g., `scanner_context.py`, `di_helpers.py`, `variable_discovery.py`, `task_extract_adapters.py`, `feature_detector.py`, `scan_cache.py`). These are intended as internal contract checks.

**Baseline allowlist summary**

- Baseline file: `docs/dev_docs/error-boundary-audit-baseline.json` (copied for audit reference).
- Allowlist size: 23 entries (module + exception kind pairs).
- Notable allowlist entries are concentrated in `src/prism/scanner_core/*` (di, di_helpers, events, policy_registry, scan_cache, scanner_context, variable_discovery, etc.), a few `scanner_extract` and `scanner_io` modules, and one `scanner_io/output.py` entry.
- Purpose: the baseline documents justified raw raises at module boundaries that are accepted until explicitly wrapped or migrated to `PrismRuntimeError`.

**Platform extension needs (Ansible → Kubernetes/Terraform plugin errors)**

When adding platform-specific plugin executors (Kubernetes, Terraform) expect the following error-envelope needs:
- richer domain codes: platform-specific `code` values (e.g., `K8S_API_ERROR`, `K8S_RESOURCE_NOT_FOUND`, `TF_PLAN_PARSE_ERROR`) mapped into existing `category` (runtime/io/parser) via `category_for_code()` or new mappings.
- resource provenance: include resource identifiers in `detail`/`source` (cluster, namespace, kind, name, manifest path, provider region) to enable triage and automated rules.
- retry semantics: explicit `recoverable` flags and/or `detail.retryable: bool` for transient API failures vs. manifest/plan errors.
- structured cause typing: preserve underlying client exception type (e.g., `ApiException`, `TerraformPlanError`) in `cause_type` and include sanitized `traceback` only where safe.
- mapping to scan-phase: ensure plugin-layer errors populate `ScanErrorEntry.phase` and `scan_policy_blocker_facts` when they represent blocker conditions (e.g., cluster unreachable → scan degraded).
- security/sanitization: strip secrets from plugin errors (kubeconfig paths, token snippets) before adding `traceback`/`detail` to envelope.
- performance considerations: for high-frequency transient platform errors, add sample-rate / aggregation metadata to avoid noisy repeated envelopes.

**Error boundary audit baseline (quick notes)**

- The codebase already centralizes the public error contract via `PrismRuntimeError` and `prism.errors.to_failure_detail()` normalization.
- Current pattern: internal `ValueError` used extensively for shape/validation; public surfaces (API, kernel, config, plugin-resolver) wrap as `PrismRuntimeError` — this matches documented contract in `errors.py` and `scanner_context.py` docstrings.
- Baseline allowlist (23 entries) should be the starting point for any automated audit script that enforces: "no raw raises at exported module boundaries except allowlist entries." The repository contains tests referencing these behaviors (see `tests/test_errors.py`, `tests/test_scanner_context.py`).

**Artifacts produced / references**
- Collected matches: `/tmp/error_entry_usage.txt`, `/tmp/scan_errors_top10.txt`, `/tmp/exception_patterns.txt`, `/tmp/error_baseline.json` (copied from `docs/dev_docs/error-boundary-audit-baseline.json`).
- Key files to inspect:
  - [src/prism/scanner_data/contracts_request.py](src/prism/scanner_data/contracts_request.py)
  - [src/prism/scanner_core/scanner_context.py](src/prism/scanner_core/scanner_context.py)
  - [src/prism/errors.py](src/prism/errors.py)
  - [docs/dev_docs/error-boundary-audit-baseline.json](docs/dev_docs/error-boundary-audit-baseline.json)

