---
layout: default
title: Provenance Categories
---

## Overview

Prism classifies every variable insight row with a **provenance issue category** when the scanner cannot fully resolve or unambiguously determine the variable's origin. Categories fall into two top-level classes:

- **Unresolved** — the scanner could not find any static definition for the variable. These are the categories that matter most for noise-reduction work and are counted in the `unresolved_noise_variables` metric.
- **Informational Precedence** — the scanner found a definition but noted a well-understood, deterministic precedence relationship. These are not errors; they are annotated for human awareness.

Ambiguous categories sit between the two: a definition exists, but its runtime value cannot be determined statically.

---

## Unresolved Categories

These categories indicate that no static definition was located. They all contribute to the `unresolved_noise_variables` metric (see below). High counts in this group are a signal that scanner tuning or role authoring improvements are needed.

### `unresolved_no_static_definition`

The variable is referenced in task templates but has no entry in `defaults/main.yml`, `vars/main.yml`, or any statically resolvable include file. This is the most straightforward noise case: the variable simply does not appear anywhere the scanner can read. It may be injected by a parent playbook, an inventory, or a wrapping role, none of which can be verified statically.

### `unresolved_dynamic_include_vars`

The variable is referenced and the role contains one or more `include_vars` tasks whose file path is a Jinja template expression (dynamic). Because the path is not known until runtime, the scanner cannot determine which file would actually be loaded, and therefore cannot confirm whether a definition exists. Roles that rely heavily on dynamic `include_vars` will accumulate counts here.

### `unresolved_readme_documented_only`

The variable appears in the role's README (typically under a "Role Variables" section or a backtick reference) but is absent from all role files the scanner can reach. The README authors intended it to be an accepted input, but it has no backing defaults or vars entry. This usually means a README-only annotation without a corresponding `defaults/main.yml` entry.

### `unresolved_other`

The variable is marked unresolved but its uncertainty reason does not match any of the more specific patterns above. This is a catch-all for edge cases or novel unresolved situations not yet assigned their own sub-category.

---

## Ambiguous Categories

These categories indicate that a definition was found but the scanner cannot determine which value will be in effect at runtime.

### `ambiguous_set_fact_runtime`

The variable's effective value is set by a `set_fact` task at runtime. Because the task body may depend on other runtime state, the scanner records the variable as ambiguous rather than resolved with a static default. This is expected for roles that compute derived values during execution.

### `ambiguous_include_vars_sources`

The role has multiple `include_vars` statements pointing to different files, and the scanner detects that more than one could supply the variable. Which file actually wins depends on runtime ordering or conditions, making the provenance ambiguous.

### `ambiguous_other`

The variable is marked ambiguous but the uncertainty reason does not match `set_fact` or `include_vars` patterns. Used as a fallback for novel ambiguous situations.

---

## Informational Precedence Category

### `precedence_defaults_overridden_by_vars`

The variable is defined in **both** `defaults/main.yml` and `vars/main.yml`. Ansible's variable precedence rules mean `vars/` always wins over `defaults/`, so the effective value is deterministic — but an operator may be surprised that the defaults-level value is silently overridden. This category is **informational only**: it does not contribute to `unresolved_noise_variables` and should not be treated as a bug.

#### Legacy alias: `ambiguous_defaults_vars_override`

Older scanner outputs used the name `ambiguous_defaults_vars_override` for the same condition. The current codebase normalises this to `precedence_defaults_overridden_by_vars` internally and emits the legacy name as a backward-compatible alias. Downstream consumers should migrate to the canonical name; the alias will eventually be removed.

---

## The `unresolved_noise_variables` Metric

`unresolved_noise_variables` is the sum of variables whose category falls in the unresolved set:

- `unresolved_no_static_definition`
- `unresolved_dynamic_include_vars`
- `unresolved_readme_documented_only`
- `unresolved_other`

Informational precedence categories (`precedence_defaults_overridden_by_vars`) and ambiguous categories (`ambiguous_set_fact_runtime`, `ambiguous_include_vars_sources`, `ambiguous_other`) are **excluded** from this count. The metric is used as the primary signal in scanner improvement cycles: a lower ratio of `unresolved_noise_variables` to `total_variables` indicates a cleaner, more statically-resolvable role.

---

## Lane Metrics

Per-cycle cohort snapshots. Cohort: 20 matched targets across batches. `unresolved_noise_variables` counter was introduced after the batches below were scanned, so values are derived from category sums.

### 2026-03-25 — batch 8 vs batch 15

Baseline: `roles25-refresh-20260322-candidate8` (batch 8) | Candidate: `overnigh_500-builtins-top20-20260324` (batch 15)

| Metric | Baseline (b8) | Candidate (b15) | Delta |
| ------ | ------------- | --------------- | ----- |
| total\_variables | 5,210 | 5,257 | +47 |
| unresolved\_variables | 1,253 (24.05%) | 1,300 (24.73%) | +47 (+0.68pp) |
| `unresolved_no_static_definition` | 1,252 | 1,296 | +44 |
| `unresolved_dynamic_include_vars` | 1 | 4 | +3 |
| `unresolved_readme_documented_only` | 0 | 0 | 0 |
| `unresolved_other` | 0 | 0 | 0 |
| `ambiguous_set_fact_runtime` | 121 | 121 | 0 |
| `ambiguous_include_vars_sources` | 0 | 0 | 0 |
| `ambiguous_other` | 0 | 0 | 0 |
| `precedence_defaults_overridden_by_vars` | 2 | 2 | 0 |

**Lane verdict: FAIL** — unresolved ratio increased +0.68pp; 44 new `unresolved_no_static_definition` entries driving the increase. Next action: Lane A (`ignored_identifiers.yml`) diagnostic to identify leaking builtins.

---

## Change Log

- **2026-03-25** — Initial version. Renamed `ambiguous_defaults_vars_override` to `precedence_defaults_overridden_by_vars`; added legacy alias and `unresolved_noise_variables` metric.
