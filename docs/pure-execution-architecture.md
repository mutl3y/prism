# Pure Execution Core Migration — Architecture Governance

**Status:** Complete
**Completed:** 2026-04-18 (NCK1 + SCB1 + MP1 closure)
**Promoted to canonical src:** 2026-04-22 (fsrc→src promotion)

---

## What Was Built

The scanner was refactored from a monolithic god-module with embedded
platform-specific behavior into a **pure execution core** where behavior
ownership lives in plugin layers driven by request-bound `policy_context`.

### Ownership Boundaries (Locked)

| Layer | Owns | Must NOT own |
| --- | --- | --- |
| `scanner_core` | Execution lifecycle, immutable payload shaping | Registry lookups, marker rules, platform branches |
| `scanner_kernel` | Preflight, plugin selection, strict/non-strict routing | Parser or traversal implementation |
| `scanner_plugins.*` | Scan-pipeline behavior, parsing, traversal, policy | Scanner payload schema contracts |
| `api.py` / `cli.py` | Thin compatibility boundaries | Plugin selection or routing decisions |

### Three Closed Slices

**NCK1** — Non-collection execution core/kernel split
`scanner_core` owns non-collection request authority. `scanner_kernel` owns
route/preflight/runtime carrier contract. `api.py` and `api_layer/non_collection.py`
are thin compatibility boundaries only.

**SCB1** — ScannerContext payload-shape parity
`scanner_context` emits typed blocker facts only. `scanner_kernel` translates
them into strict failures or non-strict warnings. The single approved fsrc-only
metadata extension is `scan_policy_blocker_facts`.

**MP1** — Marker-prefix ingress ownership
`scan_request.ensure_prepared_policy_bundle()` projects `comment_doc_marker_prefix`
at ingress. `task_extract_adapters` consumes only explicit caller input or the
canonical top-level key plus default fallback. No late-resolution fallbacks on
the hot path.

---

## Plugin Selection (Deterministic)

Resolution order — first match wins:

1. `request.option.scan_pipeline_plugin`
2. `policy_context.selection.plugin`
3. Platform match
4. Registry default (lexical ascending tie-break)

---

## Strict / Non-Strict Failure Contract

| Failure Mode | Strict | Non-Strict |
| --- | --- | --- |
| `registry_default_plugin_unavailable` | error `scan_pipeline_default_unavailable` | fallback to `legacy_orchestrator` + warning |
| `registry_lookup_exception` | error `scan_pipeline_router_failed` | fallback to `legacy_orchestrator` + warning |
| `selected_plugin_missing` | error `scan_pipeline_plugin_missing` | fallback to `legacy_orchestrator` + warning |
| `preflight_execution_exception` | error `scan_pipeline_router_failed` | fallback to `legacy_orchestrator` + warning |
| `runtime_execution_exception` | error `scan_pipeline_execution_failed` | fallback to `legacy_payload` + warning |
| `policy_context_alias_conflict` | error `policy_context_alias_conflict` | canonical key wins + warning |
| `unknown_policy_context_key` | error `policy_context_unknown_key` | continue with warning |

---

## Policy Context Governance

Canonical marker prefix key: `policy_context.comment_doc.marker.prefix`

Deprecated aliases (non-strict: canonical wins with warning):

- `policy_context.comment_doc_marker_prefix`
- `policy_context.comment_doc.marker_prefix`

`version` field is required (integer). Supported: `1`, `2`. Missing/invalid/unsupported:
strict → error; non-strict → warning + version-1 fallback.

---

## Ansible Plugin Separation (Completed 2026-04-19)

All Ansible-specific logic evicted from `scanner_core`:

- `IGNORED_IDENTIFIERS` in `variable_pipeline.py` → `frozenset()` (evicted)
- `AnsibleVariableDiscoveryPlugin` and `AnsibleFeatureDetectionPlugin` own
  Ansible behavior in `scanner_plugins.ansible`
- `VariableDiscovery` and `FeatureDetector` in `scanner_core` are generic
  delegation wrappers only
- DI factory defaults (`factory_variable_discovery_plugin`, `factory_feature_detection_plugin`)
  resolve through `PluginRegistry` — zero hardcoded Ansible imports in `scanner_core`
- All `_get_*_policy(di)` functions raise `ValueError` without `prepared_policy_bundle`
  — no silent fallbacks

**Active compatibility seams:** CSR-001 through CSR-004, CSR-009 through CSR-015 (11 total)
**Retired:** CSR-005, CSR-006, CSR-007, CSR-008, CSR-016, CSR-017, CSR-018

---

## Expansion Readiness

| Criterion | Status |
| --- | --- |
| Zero Ansible imports in `scanner_core` | ✅ |
| Registry-driven DI factory defaults | ✅ |
| All policy getters fail-closed | ✅ |
| Parity tests accounted | ✅ |
| Compatibility seam count reduced | ✅ |
| K8s / Terraform plugin slots reserved | ✅ |
| Multi-platform protocols in place | ✅ |

Kubernetes and Terraform scan plugins are **unblocked at the gate level**.
No implementations exist yet — expansion planning can proceed.

---

## Residual Debt (Non-Blocking)

- `variable_discovery` prepared-policy ownership cleanup (GF2-W4-T03 deferred:
  18+ consumer call sites; only blocks concurrent multi-platform scanning)
- Proxy singleton remediation deferred from GF2 wave 4

---

## Normative References

- Plan: `docs/plan/pure-execution-core-plugin-architecture-20260413/plan.yaml`
- Contract matrix: `docs/plan/pure-execution-core-plugin-architecture-20260413/artifacts/contract_matrix.yaml`
- CI guardrail: `.github/workflows/prism.yml` job `plan-governance-guardrail`
- Test assertion obligations: `contract_matrix.yaml` → `risk_to_test_assertion_mapping`
