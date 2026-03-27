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

## Scanner Submodule Layout

`scanner.py` is an orchestrator that delegates to focused submodules under `src/prism/scanner_submodules/`:

| Module | Responsibility |
| --- | --- |
| `scan_request.py` | scan option-map shaping and detailed-catalog flag normalization |
| `scan_context.py` | scan context/payload shaping; TypedDict definitions for internal seam contracts |
| `scan_metrics.py` | scanner counter extraction and uncertainty/provenance attribution |
| `scan_output_emission.py` | sidecar output emission orchestration (scanner report, runbook) |
| `scan_discovery.py` | role identity resolution and metadata/requirements/variable path discovery |
| `scan_output_primary.py` | primary output rendering and write orchestration |
| `scanner_report.py` | scanner report markdown rendering and typed row/section helpers |

Pre-existing submodules (`task_parser.py`, `variable_extractor.py`, `readme_config.py`, `output.py`, `runbook.py`, `style_guide.py`, `style_vars.py`, `doc_insights.py`, `requirements.py`) retain their original responsibilities.

`src/prism/repo_services.py` holds shared repo-intake, clone, fetch, sparse-checkout, and temp-workspace orchestration extracted from `cli.py`. Both `api.py` and `cli.py` import from `repo_services`.

## Typed Seam Contracts

Internal TypedDicts stabilize payload boundaries between scan orchestration stages. Primary contracts:

- `scan_context.py`: `ScanContext`, `RunScanOutputPayload`, `EmitScanOutputsArgs`, `ScanReportSidecarArgs`, `RunbookSidecarArgs`
- `scanner_report.py`: `ScannerReportMetadata`, `NormalizedScannerReportMetadata`, `ReadmeSectionRenderInput`, `ScannerReportIssueListRow`, `ScannerReportYamlParseFailureRow`, `ScannerReportSectionRenderInput`, `SectionBodyRenderResult`, `AnnotationQualityCounters`, `ScannerCounters`
- `output.py`: `FinalOutputPayload`

## Mypy Gate

`tox -e typecheck` runs `mypy` over all 25 source files in the prism package. The gate is also wired as a pre-commit hook (`mypy-seams`) and runs in CI on every push/PR via `.github/workflows/prism.yml`.

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
