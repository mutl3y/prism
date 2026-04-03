---
layout: default
title: Architecture
---

Prism is a static-analysis documentation engine for Ansible roles and collections.

It is best understood as a contract-and-governance pipeline, not only a renderer.

## Pipeline Overview

1. discover role/collection structure
2. parse YAML and Jinja signals
3. compute variable insights and scanner counters
4. render docs and machine-readable payloads

## Primary Components

- scanner core for role analysis
- collection plugin catalog extraction
- CLI orchestration (`role`, `collection`, `repo`)
- output rendering (`md`, `json`, `html`, `pdf`)

## Scanner Package Decomposition

`scanner.py` remains a public facade and delegates canonical runtime behavior to package-owned modules under `src/prism/`:

| Package | Ownership boundary |
| --- | --- |
| `scanner_core/` | request normalization, DI-driven orchestration, scan runtime/context assembly, variable discovery orchestration |
| `scanner_data/` | typed contracts and builders for request/result envelopes, scan payloads, report metadata, and variable rows |
| `scanner_extract/` | YAML/task traversal, variable/reference extraction, role feature collection, requirements and discovery loaders |
| `scanner_readme/` | README rendering, style parsing/normalization, documentation insights, section composition |
| `scanner_analysis/` | scanner metrics, report shaping, runbook generation, dependency analysis helpers |
| `scanner_io/` | output rendering/writing, scan output emission, YAML candidate loading and parse-failure reporting |
| `scanner_config/` | policy/config loading, style/section markers, legacy retirement behavior, runtime scan policy switches |
| `scanner_compat/` | compatibility bridge helpers isolated from canonical runtime paths |

Cross-package architecture guardrails enforce one-way decomposition: canonical scanner packages must not reverse-import `prism.scanner`, and private cross-package imports are blocked except for explicitly whitelisted seams.

`src/prism/repo_services.py` holds shared repo-intake, clone, fetch, sparse-checkout, and temp-workspace orchestration extracted from `cli.py`. Both `api.py` and `cli.py` import from `repo_services`.

## Typed Seam Contracts

Typed contracts are centralized in `scanner_data/` and exposed via `scanner_data/contracts.py` and domain split modules (`contracts_request.py`, `contracts_output.py`, `contracts_report.py`, `contracts_variables.py`, `contracts_collection.py`, `contracts_errors.py`).

Primary scanner boundaries:

- request/runtime: `ScanOptionsDict`, `ScanContext`, `ScanBaseContext`, `ScanContextPayload`, `FailurePolicyContract`
- output envelopes: `ScanRenderPayload`, `RunScanOutputPayload`, `RunbookSidecarPayload`, `FinalOutputPayload`
- reporting: `ScannerReportMetadata`, `NormalizedScannerReportMetadata`, `ScannerCounters`, `AnnotationQualityCounters`, report row contracts
- public API results: `RoleScanResult`, `CollectionScanResult`, `RepoScanResult`

## Mypy Gate

`tox -e typecheck` runs `mypy` over `src/`. The gate is also wired as a pre-commit hook (`mypy-seams`) and runs in CI on every push/PR via `.github/workflows/prism.yml`.

Flags: `--ignore-missing-imports --disable-error-code=import-untyped --follow-imports=silent`

## Contract And Governance Layers

- contract layer: generated markdown/json defines automation interface behavior
- confidence layer: provenance and uncertainty flags mark non-deterministic areas
- governance layer: CI policies consume scanner flags and JSON fields
- learning loop: `prism-learn` aggregates fleet-wide trends and recommendations

## Design Principle

Prefer deterministic, reviewable output over speculative runtime inference.

## Latest Outstanding Unresolved

From the latest available unresolved provenance report for batch 15 (`overnigh_500-builtins-top20-20260324`):

- unresolved variables: 1,300 of 5,257 total (24.73%)
- top unresolved repositories by count:
  - `ansible-opnsense`: 128 unresolved
  - `AZURE-CIS`: 128 unresolved
  - `bitcoin_core`: 96 unresolved
  - `open_ondemand`: 94 unresolved
  - `rhel6_stig`: 76 unresolved

Built-in variable leakage is still visible in unresolved output, including `ansible_distribution`, `ansible_distribution_major_version`, and `ansible_mounts`.

### Dynamic include_vars Example (Path Unknown At Scan Time)

Concrete report example: in `rhel7_stig`, batch 15 includes:

- `Dynamic include_vars (path unknown at scan time) (1)`
- unresolved variable: `ansible_distribution` (an Ansible gathered fact for OS name, not a role variable expected in `meta/main.yml`)

Representative pattern (matching real RHEL8-CIS style):

```yaml
- name: Include OS specific variables
  tags: always
  ansible.builtin.include_vars:
    file: "{{ ansible_distribution }}.yml"
```

`ansible_distribution` returns the OS name exactly as Ansible reports it — e.g. `RedHat` for Red Hat Enterprise Linux (note: `RedHat` is the correct spelling, matching the Ansible fact value). For a role that declares only `EL` platforms in `meta/main.yml` (as `RHEL8-CIS` does), the complete set of possible `ansible_distribution` values at runtime is bounded and known: `RedHat`, `CentOS`, `Rocky`, `AlmaLinux`, `OracleLinux`. If `vars/RedHat.yml` exists in the role, the scanner *could* statically prove provenance for `ansible_distribution` in this pattern — by cross-referencing the `meta/main.yml` platform list against the vars files present on disk. Currently the scanner treats this as path-unknown at scan time; this is the concrete improvement opportunity for the next lane.

## Implication For Next Lane

Lane A next cycle: implement constrained `include_vars` resolution for roles whose `meta/main.yml` declares a single OS family (e.g. `EL`). When `ansible_distribution` is used as the sole template token in an `include_vars` path, enumerate the bounded set of `ansible_distribution` values for that platform family and check which `vars/<value>.yml` files exist. Mark matched variables as resolved (provenance: `include_vars_platform_constrained`) rather than `unresolved_dynamic_include_vars`. This eliminates false unresolved noise for EL-only roles using the standard `RedHat.yml`/`AlmaLinux.yml` vars-file pattern without masking genuinely missing definitions.
