# Parallel Sweep And Waves

## Phase 0 Sweep

Run four concurrent discovery subagents:

| Subagent | Categories |
|---|---|
| `Scout-Typing` | weak typing, orchestration contract quality, lossy casts, protocol gaps |
| `Scout-Ownership` | duplication, misplaced ownership, facade leakage, shell boundary, stale shims |
| `Scout-ControlFlow` | silent fallbacks, missing guards, error channels, policy coercion |
| `Scout-Graph` | import graph, composition roots, registry authority, singleton pollution, test fixture coupling |

Rules:

- Dispatch in one batch, in separate concurrent process slots when supported, wait once, then merge.
- Keep raw observations filtered; do not dump.
- Use phase-specific prompt files, not an ad hoc mega prompt.
- Each sweep writes to `docs/plan/<PLAN_ID>/mutl3y-artifacts/phase0/<AGENT_NAME>.yaml`.
- Each sweep returns only the artifact path, observation count, and a few top hits.
- Merge locally in the orchestrator into `merged-observations.yaml`.
- During merge, normalize duplicate observations by `(category, file, line, related_symbols)` and preserve all source scout IDs.
- Use finding `fingerprint` as the first dedupe key when present; fall back to `(category, file, line, related_symbols)`.
- Build `fix-groups.yaml` keyed by `fix_group_key` with: findings, files, dependency notes, suggested narrow gate, and whether groups can run in parallel.
- Promote cross-cutting findings only after at least two evidence locations are verified, or after the Synthesizer-Architecture pass confirms the connection.

## Phase 5 Fix Waves

Prefer fix groups over raw categories. Category order is a fallback when `fix-groups.yaml` is missing.

Default dependency order:

1. contract-shaping groups: `typing`, `orchestration_seam`, `extract_protocol`
2. boundary groups: `composition_root`, `registry_authority`, `facade_leakage`, `shell_boundary`
3. behavior groups: `silent_fallback`, `error_channel`, `policy_coercion`, `guard`
4. cleanup groups: `duplication`, `shim_staleness`, `singleton_pollution`, `test_fixture_coupling`
5. test-only groups: `test_gap`

Parallelize only groups with disjoint write sets and no dependency edge.
When groups are disjoint, launch their builders as one batch and join at the wave barrier instead of waiting after each launch.

Worker ownership rule:

- declare the file set up front
- one worker per fix group or explicitly coupled group cluster
- if a wave becomes cross-cutting, stop and re-slice rather than letting workers overlap
- pass each builder exactly one fix_group_key or one tightly coupled group cluster
- include the suggested narrow gate from the scout/foreman artifact in the worker prompt

File-conflict check recipe:

```bash
.venv/bin/python -c "
import yaml, json, collections
f = yaml.safe_load(open('docs/plan/<PLAN_ID>/findings.yaml'))
bycat = collections.defaultdict(set)
for x in f['findings']:
    if x.get('status', 'open') == 'open':
        for p in x.get('files', []):
            bycat[x['category']].add(p)
print(json.dumps({k: sorted(v) for k, v in bycat.items()}, indent=2))
" > .mutl3y-gate/category_files.json
```

If two categories or fix groups intersect on files, serialize them unless the same worker owns the combined group.

Before dispatching a builder wave, write `docs/plan/<PLAN_ID>/mutl3y-artifacts/phase5/wave-N-plan.yaml` with:

```yaml
wave: N
groups:
  - fix_group_key: typing.callable-protocols
    findings: [FIND-01, FIND-03]
    fingerprints: [typing:src/prism/scanner_core:abc123def456]
    owned_files: [src/example.py]
    dependencies: []
    narrow_gate: ".venv/bin/python -m pytest src/example_tests.py -q"
    learned_gate_rules: []
parallel_safe: true
```

After the wave, compare changed files with owned files and fail the barrier if edits escaped scope.
If the wave narrow gate passes but the full gate later fails, write `mutl3y-artifacts/phase6/gate-escape-learning.yaml` with the missing gate and fix_group_key.
