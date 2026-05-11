# Deep Review Protocol

This document specifies the periodic architectural deep-review pass that runs every third thorough review cycle. It was designed after comparing standard Phase 0 scout output against independent multi-mode reviews, where scouts consistently missed cross-cutting findings that required synthesizing across category silos.

The graph-backed variant of this skill adds `architecture-graph.json` as a shared structural substrate so the synthesizer can reason from one consistent map instead of reconstructing architecture from isolated scout snippets.

## When to run

- Every third thorough review cycle (e.g. g3, g6, g9 — or whenever `cycle_number % 3 == 0`).
- Immediately when the foreman's Phase 1 grade promotes fewer than one-third of raw scout observations to findings (low signal efficiency is a sign that the scout silos missed cross-cutting synthesis).
- Immediately before any major decomposition or platform expansion wave.
- Always after a wave that touches plugin bootstrap, DI composition, or registry wiring.

## Why standard scouts miss these patterns

Standard Phase 0 scouts operate in isolated category silos. Each writes raw observations within its domain. The foreman then grades and promotes findings from those per-scout artifacts. This pipeline is efficient but has two structural blind spots:

1. **Cross-cutting findings** require reading observations from multiple scouts simultaneously. Split-brain registry authority, for example, only becomes visible when you notice that `execution_request_builder`, `di.py`, `defaults.py`, and `loader.py` each resolve the registry through different paths — something no single scout is positioned to see.
2. **Files not in any scout's primary scan surface** go unexamined. `api_layer/collection.py`, thin re-export adapters, and facade re-export tables are frequently skipped because they do not match any single category's typical patterns.

The architecture graph reduces but does not eliminate these blind spots: it gives scouts and the synthesizer a shared map of seams, facades, resolver paths, and test links, while still requiring live-source verification.

## What a deep review must cover

### 1. Composition root placement

Look for every site where `DIContainer` (or equivalent) is constructed or where `ensure_prepared_policy_bundle` is called. There should be exactly one owned composition root per request path. Flag any secondary construction site as a hidden composition root.

Questions:
- Is `DIContainer` constructed outside the declared ingress? If so, which module owns it and does that match the architecture record?
- Does any defaults/policy module call back into the core DI layer to construct runtime state?
- Is there a test that asserts the single composition root invariant?

### 2. Registry authority split

For every place the plugin registry is passed, stored, or resolved, trace whether all downstream consumers read from the same authority.

Questions:
- Does `DIContainer` expose a public `plugin_registry` property, or does it store the registry as a private attribute that resolver paths cannot reach?
- Does `execution_request_builder` inject a registry into `DIContainer` AND separately compute a `runtime_registry` from scan options? If both exist, which one wins in fallback resolvers?
- Do `defaults._resolve_registry()`, `loader._resolve_plugin_registry()`, and `kernel` routing all read from the same source for a given request?
- Is there a test proving that a custom injected registry propagates through bundle prep, loader fallback, and runtime routing?

### 3. Facade leakage audit

For every public API/CLI entry point, list the symbols re-exported at the module top level. Flag any symbol that is an internal runtime assembly helper, a composition factory, or a registry singleton.

Questions:
- Does `api.py` re-export assembly helpers (`build_run_scan_options_canonical`, `route_scan_payload_orchestration`, etc.) that are not part of the supported public contract?
- Does `api.py` re-export `DEFAULT_PLUGIN_REGISTRY`? If so, does the re-export serve a documented external use case or is it a test-patching convenience?
- Do tests patch these re-exported symbols through the public facade, which would freeze the leak as a test dependency?

### 4. Shell layer plugin boundary audit

For every shell layer (`cli.py`, `api.py`, `scanner_reporting/__init__.py`, similar facades), list every import from a `scanner_plugins.*` submodule that is not going through an approved seam.

Questions:
- Does any CLI command handler import directly from `scanner_plugins.audit.*` instead of going through an API or service facade?
- Does any reporting package import directly from `scanner_plugins.parsers.*` for rendering helpers?
- Is there an architecture guardrail test enforcing these shell-to-plugin import restrictions?

### 5. Error channel and control flow audit

For every module in `scanner_io` and `scanner_extract`, check every `except` block and every `or {}` / `or []` / `or None` default-on-failure pattern.

Questions:
- Is any `TypeError` or `OSError` being caught and silently converted to a fallback value without emitting a diagnostic?
- Are there `or {}` patterns that prevent distinguishing between "file not found" and "file loaded but empty"?
- Is strict-mode enforcement respected — i.e., does a shape validation failure actually raise when `strict=True`, or does it silently return `{}`?
- Are broad `except Exception` boundaries narrowed to the actual expected error set?

### 6. Seam contract quality at architecture boundaries

Focus on the six primary architecture boundary crossings:
- `scanner_core` ↔ `scanner_plugins`
- `scanner_kernel` ↔ `scanner_core`
- `api_layer` ↔ `scanner_kernel`
- `cli_app` ↔ `api_layer`
- `scanner_plugins` ↔ `scanner_extract`
- `scanner_io` ↔ `scanner_plugins`

For each, check whether the parameters and return types at the crossing use named protocols/TypedDicts or fall back to `Any`, `dict[str, Any]`, or `Callable[..., Any]`.

Questions:
- Do orchestration seams accept collaborators typed as `Callable[..., Any]`? If so, how many — and does the count exceed three in a single function signature?
- Do runtime protocols return `Any` instead of named result types?
- Do plugin interfaces use `dict[str, Any]` for their primary payload shapes?

### 7. Audit and reporting boundary ownership

Questions:
- Is the audit logic (dynamic include audit, rule loader, runner) owned by the audit plugin or is it actually re-exporting extraction traversal internals?
- Does the reporting package own its rendering entry points, or does it delegate to plugin-internal renderer modules?
- Is there a stable service-layer seam for audit and reporting that shell layers can depend on without reaching into plugin internals?

## Deep review dispatch

Run the deep review as a two-agent pass after the standard Phase 0 sweep:

### Pass A — Cross-cutting synthesis agent

Dispatch one named agent: `Synthesizer-Architecture`.

Prompt:
```text
Role: Synthesizer-Architecture, a cross-cutting architectural reviewer.

You have access to all Phase 0 scout artifacts for this cycle.
Read them, the full `docs/plan/.mutl3y-lessons/architecture-graph.json`, then perform the seven deep-review checks defined in:
  .github/skills/mutl3y-review-workflow/references/deep-review-protocol.md

Do NOT re-flag findings already in findings.yaml.
DO flag cross-cutting findings that require reading across multiple scouts.

For each deep-review check that surfaces a new finding, verify against live source
before writing the finding. Do not include unverified claims.

Write your output to:
  docs/plan/<PLAN_ID>/mutl3y-artifacts/phase0/Synthesizer-Architecture.yaml

Schema: same as Phase 0 scout schema plus:
  cross_cutting: true
  scouts_that_missed: [Scout-Typing|Scout-Ownership|Scout-ControlFlow|Scout-Graph]
  verification_evidence: <one line from live source confirming the claim>

Return only: agent name, artifact path, finding count, top 3 cross-cutting hits.
```

Before reading live source, use the graph to enumerate:

- all known composition-root candidates
- registry-resolution paths
- facade re-export edges
- shell-to-plugin boundary crossings
- singleton-touching tests and fixtures

### Pass B — God Mode independent grader (mandatory periodic calibration)

Dispatch the `Gilfoyle Code Review God Mode` agent as an independent pass
with no access to current cycle findings in any of these cases:

- At least every sixth thorough review cycle.
- Before final sign-off after the required clean thorough passes.
- Before a major architectural migration.
- Immediately after any cycle where scouts returned a clean or near-clean
  result but recent God Mode history still shows missed High/Critical
  findings in the same seam family.

For any pass described as `independent`, `fresh`, or `unconstrained`,
the prompt must stay whole-target and bias-minimal.

When Phase 7 is active, `closure-control-gate.md` is the canonical enforcement
surface for this requirement. The foreman must record the independence check in
`mutl3y-artifacts/phase7/closure-control-gate.yaml` before dispatch and may not
count a biased prompt as satisfying God Mode after the fact.

Required prompt contract:

- Allowed inputs: repo root or target path, artifact output path,
  severity or reporting schema, and a statement that the review must
  use live source.
- Forbidden inputs: current focus axis, current shortlist, scout top
  hits, suspected seam families, named candidate files beyond the
  target root, or any instruction of the form "check whether X/Y/Z is
  still broken".
- Forbidden framing: any phrasing that steers toward the current cycle
  storyline, such as execution-request ingress, registry authority,
  defaults ownership, facade leakage, or similar seam-family hints.
- Required wording: explicitly say that the pass must ignore the
  current cycle's active hypothesis and surface the highest-signal
  High/Critical findings wherever they are.
- Required scope statement: the entire target package is in scope, not
  only areas suggested by the foreman or scouts.

Before dispatch, the foreman must perform one explicit independence check:

- If the God Mode prompt mentions the focus axis, current shortlist,
  top findings, target seam families, or more than one concretely
  named code area outside the broad target path, the prompt is biased
  and must be rewritten before dispatch.
- If the prompt asks whether the current cycle was validly closed or whether a
  known closure claim should be overturned, the prompt is closure-directed and
  does not count as unconstrained.

Reference prompt shape:

```text
Role: independent whole-target reviewer.

Target: <PATH>
Plan ID: <PLAN_ID>
Write full results to: docs/plan/<PLAN_ID>/mutl3y-artifacts/phase1/<ARTIFACT>.yaml

Rules:
- Review the whole target from live source.
- Do not use current cycle findings, shortlist framing, focus-axis
  hints, or suspected seam families.
- Ignore the orchestrator's current hypothesis; surface the
  highest-signal High/Critical findings wherever they actually are.
- Medium findings are optional and should only be included when they
  materially affect wave sizing.
- Verify every promoted finding against live source before writing it.

Return only: agent name, artifact path, finding count, and top findings.
```

After it returns, merge only net-new findings that have been verified
against live source into the exhaustive review artifact. Do not promote
them into `findings.yaml` unless they rank High or Critical.

If either pass finds a High/Critical issue that standard scouts missed,
write a scout coverage patch before Phase 7 closure:

`docs/plan/<PLAN_ID>/mutl3y-artifacts/phase7/scout-coverage-patch.yaml`

Required fields: `kind: missed_finding`, `missed_by`, `found_by`,
`severity`, `pattern`, `why_missed`, `new_probe`, `prompt_target`, and
`proposed_memory_update`.

If God Mode returns any missed High/Critical findings, Phase 7 must
treat that cycle as a calibration event:

- write the scout-coverage patch artifact
- update the relevant scout prompt target before the next fresh scout
  cycle when the change is low-risk documentation or prompt guidance
- compile the lesson into `.mutl3y-lessons`
- do not claim the scout layer has absorbed the pattern until a later
  scout cycle surfaces that seam family without God Mode help

## Merging deep-review output

After both passes complete:

1. The foreman reads the Synthesizer-Architecture artifact alongside
  the existing shortlist.
2. Any finding ranked High or Critical that is not already in
  `findings.yaml` is promoted into the shortlist.
3. Medium cross-cutting findings go into the cycle's exhaustive review
  artifact but do not automatically enter the shortlist.
4. The foreman records how many deep-review findings were found in
  `digest.yaml` under a `deep_review_delta` key for trend tracking.
5. The foreman records missed-scout coverage patches for any
  High/Critical deep-review delta before running the learning-memory
  compiler.
6. If God Mode produced missed High/Critical findings, the foreman
  records `scout_calibration_required: true` in the cycle summary and
  carries that requirement into the next scout cycle.

## What to record in digest.yaml

After each deep review cycle, append to the cycle record:

```yaml
deep_review_delta:
  cycle: gN
  standard_shortlist_count: <number>
  deep_review_additional_high: <number>
  deep_review_additional_medium: <number>
  top_missed_area: <facade_leakage|registry_authority|composition_root|control_flow|seam_contracts|shell_boundary|audit_reporting>
```

If `deep_review_additional_high` is consistently nonzero, the standard
Phase 0 sweep is under-covering. Re-examine which focus areas need
promotion into the standing scout prompts.
If the misses cluster around one unresolved seam family, improve graph
coverage for that node or edge type before widening scout prompts
further.
