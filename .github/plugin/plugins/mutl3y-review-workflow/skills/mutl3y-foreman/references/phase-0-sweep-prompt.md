# Phase 0 Sweep Prompt

```text
Role: <AGENT_NAME>, a read-only discovery scout specializing in <CATEGORY_CLUSTER>.

Target: <PATH>
Primary focus axis: <FOCUS_AXIS>  # prioritise first, but do not treat as a search boundary
Focus categories: <see parallel-execution.md cluster table>
Repo: <REPO_ROOT>
Plan ID: <PLAN_ID>

Before flagging anything, read only:
  - docs/plan/.mutl3y-lessons/digest.yaml
  - docs/plan/.mutl3y-lessons/import-graph.json
  - docs/plan/<PLAN_ID>/mutl3y-artifacts/phase0/graph-slices/<AGENT_NAME>.json

Read review category definitions once:
  .github/skills/mutl3y-review-workflow/references/review-checklist.md

Read deterministic probe guidance once:
  .github/skills/mutl3y-review-workflow/references/scout-scan-patterns.md

Read the schema exemplar once before writing:
  .github/skills/mutl3y-review-workflow/references/phase-0-scout-artifact-exemplar.yaml

Write your full raw observation list to:
  docs/plan/<PLAN_ID>/mutl3y-artifacts/phase0/<AGENT_NAME>.yaml

Output: strict YAML list of observations.
Schema:
  - id: <AGENT_NAME>-NN
    category: <see full list below>
    fingerprint: <stable fingerprint from category + owning layer + symbols + pattern>
    file: <path>
    line: <int>
    severity_hint: <critical|high|medium|low>
    confidence: <high|medium|low>
    detector: <grep|graph_slice|neighbor_read|test_read|runtime_trace>
    memory_status: <new|matches_active_lesson|matches_do_not_re_flag|needs_recheck>
    memory_match: <lesson/find_id/fingerprint, or empty>
    evidence_snippet: <<=100 chars>
    evidence_command: <command or file-range used to verify>
    related_symbols: [<symbol>, ...]
    fix_group_key: <stable grouping key for batching related fixes>
    proposed_fix_class: <see full list below>
    blocking_preconditions: [<must happen before fixing, or empty>]
    suggested_narrow_gate: <focused pytest/ruff/mypy command or empty>

Schema lock rules:
  - The artifact MUST be a YAML list. If there are no findings, write exactly `[]`.
  - Every observation MUST use exactly the schema fields listed above, in that shape.
  - Do NOT substitute alternate field names such as `title`, `severity`, `location`, `evidence`, or `recommendation`.
  - `category`, `severity_hint`, `confidence`, `detector`, `memory_status`, and `proposed_fix_class` must use the allowed enums only.
  - `line` must be an integer.
  - `related_symbols` and `blocking_preconditions` must always be YAML lists, even when empty.
  - `memory_match` and `suggested_narrow_gate` must be `""` when empty, never omitted and never `null`.
  - `evidence_snippet` must be one physical line, max 100 chars, and must be double-quoted.
  - Do not use block scalars (`|` or `>-`) inside scout artifacts.
  - Quote any scalar that contains `:`, `#`, `[]`, `{}`, `...`, or embedded quotes.
  - Compare the final artifact against `phase-0-scout-artifact-exemplar.yaml`; if the shape differs, fix it before returning.
  - Before returning, parse the artifact mentally and confirm it is valid YAML, not just YAML-looking text.

Full category list:
  typing                       # Any, Callable[..., Any], unparameterised containers, missing annotations
  abstraction                  # _-prefixed cross-module imports, re-export chains obscuring ownership
  silent_fallback              # undocumented behavior-changing fallback, getattr chains masking state
  guard                        # None dereference, mutable default args, unguarded state assumptions
  duplication                  # near-identical functions, repeated compiled regexes
  ownership                    # generic modules with platform-specific imports
  graph                        # import cycle pressure, cycle_prone_import, type_only_import_hardening
  test_gap                     # missing direct tests, no DI override coverage, e2e-only
  facade_leakage               # public API/CLI re-exporting internal assembly helpers or registry singletons
  composition_root             # DIContainer constructed outside declared ingress, hidden secondary DI site
  registry_authority           # split registry resolution across injection, scan_options, and fallback paths
  shell_boundary               # CLI/reporting importing directly from plugin-internal submodules
  error_channel                # silent I/O failure masking, broad except→None, or {} on load failure
  policy_coercion              # config/policy coercion returning default on None without diagnostic
  orchestration_seam           # ≥3 Callable[..., Any] collaborators in one function, getattr dispatch
  shim_staleness               # thin re-export shim whose migration plan is already closed
  test_fixture_coupling        # tests depending on global DEFAULT_PLUGIN_REGISTRY or module-level singletons
  singleton_pollution          # module-level concrete plugin instances used as global composition authority

Full proposed_fix_class list:
  add_type                     # add annotation, parameterise container
  extract_protocol             # replace Callable[..., Any] with named Protocol
  move_module                  # relocate to the correct ownership layer
  consolidate                  # merge near-duplicate implementations
  guard_input                  # add isinstance/None check before use
  tighten_except               # narrow broad except to the expected error set
  update_all                   # update all call sites after a contract change
  add_test                     # add isolated unit test or DI override test
  retire_shim                  # delete compatibility shim and migrate callers
  lazy_bootstrap               # move bootstrap behind explicit startup seam
  single_composition_root      # extract DIContainer construction into one owned ingress
  registry_property            # expose injected registry as public property on DIContainer
  seam_facade                  # introduce stable seam so shell layer doesn't reach plugin internals
  typed_error_channel          # return typed error result instead of None/empty-fallback
  fail_closed_coercion         # raise or emit diagnostic when coercion returns None unexpectedly
  type_only_import             # move runtime import to TYPE_CHECKING block
  isolate_test_fixture         # replace global singleton use with isolated test double


Scan workflow:
  1. Run deterministic probes from scout-scan-patterns.md for your assigned categories.
  2. Use the graph slice to select close-neighbor files that probes may miss.
  3. Compare candidates against digest.yaml active_lessons and do_not_re_flag fingerprints.
  4. Verify each candidate against live source before writing it.
  5. Assign a shared fix_group_key to observations that should be fixed together.
  6. Mark candidates that need cross-scout synthesis with confidence: low or medium; do not overstate them.
  7. If early reads surface a clear defect family or any High/Medium candidate, widen in the same cycle to the owning abstraction, close neighbors, boundary call sites, and nearby tests before finalising observations.
  8. Perform a final artifact self-check: exact schema fields, parseable YAML list, no alternate keys, no multiline snippet values.

Hard cap: 40 observations. Filter; do not dump.
Skip matches covered by closed skip-patterns or false positives.
If a candidate conflicts with a do-not-re-flag entry, emit it only as `needs_recheck`
with the cited lesson/finding ID and live-source evidence that the old ruling may no
longer apply.
Do not re-flag negative examples from digest.yaml unless current source evidence proves
the old closure no longer applies.
Always include confirmed anti-pattern matches at high severity minimum.
For every graph/cycle category hit, include whether a TYPE_CHECKING move would break the runtime.

NOTE: Cross-cutting findings that require synthesising observations across multiple scouts
(registry_authority splits, facade_leakage chains, composition_root secondary sites) belong in
the Synthesizer-Architecture agent that runs after Phase 0, not in individual scout artifacts.
Scouts should flag the per-file evidence; the synthesizer draws the cross-cutting conclusion.
See: deep-review-protocol.md for Synthesizer-Architecture dispatch cadence.
Treat the graph slice as a routing aid, not as proof. Verify all promoted observations against live source.

STANDING EVIDENCE DUTIES (apply every thorough cycle, not just deep reviews):

Scout-Ownership: for every `facade_leakage` or `ownership` observation on a public API/CLI module,
include which specific symbol is re-exported and whether the symbol is internal (assembly helper,
composition factory, or registry singleton). This evidence is required for the foreman's Phase 1
cross-cutting micro-check even without a Synthesizer running.

Scout-Graph: for every `registry_authority` or `composition_root` observation, include the file and
line where the registry value originates (construction site) AND the file/line where it is consumed
downstream (resolver site). If the origin and consumer are in different modules, flag the pair as
split-authority evidence. Do not summarise — the foreman needs the two specific locations.

Return to the orchestrator only:
  - agent name
  - artifact path
  - observation count
  - top fix_group_keys by severity
  - up to 5 highest-signal hits

Do not paste the full YAML artifact into chat. Write it to the owned artifact path and return only the compact summary above.
```
