# Self-Improvement Protocol

Use this when starting or closing a review cycle, recovering from a bad
dispatch, or changing prompts or routing policy.

## Canonical Memory Store

Use `docs/plan/.mutl3y-lessons/` as the persistent learning store:

- `digest.yaml`: compact read for the next Phase 0
- `lessons.yaml`: durable anti-patterns, false positives, invariants,
  and prompt rules
- `closed_findings.yaml`: closed/deferred/do-not-re-flag findings with evidence
- `focus-axis-log.yaml`: axis rotation, grade, gate state, and cycle outcome
- `cycle-log.md`: append-only human cycle narrative
- `model-usage-history.yaml`: per-cycle model reliability snapshots
- `model-usage-rollup.yaml`: compact route-health summary used before dispatch
- `import-graph.json` and `architecture-graph.json`: regenerated only when needed

Do not create a second memory directory for Mutl3y unless the user
explicitly asks to migrate.

## Resolve Skill Root

Before running helper scripts, resolve `SKILL_ROOT` to the directory that
actually contains this skill:

- vendored-in-repo layout: `.github/skills/mutl3y-review-workflow`
- shared-workspace layout: the external checkout path that contains this skill directory

The commands below use `"$SKILL_ROOT/scripts/update_learning_memory.py"`
so the same workflow works in both layouts.

## Cycle Start

Before Phase 0, run the deterministic readiness check:

```bash
python3 "$SKILL_ROOT/scripts/update_learning_memory.py" \
  check-readiness --repo-root .
```

Do not block solely because optional graph artifacts are stale, but do
record the readiness result in `learning-context.yaml`.

Then read only:

1. `digest.yaml`
2. `model-usage-rollup.yaml`
3. the current plan's `findings.yaml`, if continuing a plan
4. a role-scoped architecture graph slice, not the full graph

Then write a one-screen `learning-context.yaml` artifact under `docs/plan/<plan-id>/mutl3y-artifacts/phase0/`:

```yaml
memory_source: docs/plan/.mutl3y-lessons
active_lessons: []
do_not_re_flag_count: 0
focus_axis_due_next: architecture
model_route_notes: []
stale_or_missing_memory: []
readiness_check: {}
```

If memory is missing or stale, continue the cycle but record the gap in `stale_or_missing_memory`.

## During The Cycle

Learning candidates belong in phase artifacts first, not in persistent ledgers.

Use `references/learning-candidate-reference.md` as the canonical source for:

- candidate kinds
- compact candidate shapes
- fingerprint structure
- lesson-kind and workflow-lesson-type tables
- digest-content rules
- staleness and expiry rules

## Finding Fingerprints

Every finding, scout observation, closed entry, and lesson should carry a
stable `fingerprint`.

Use `scripts/update_learning_memory.py` as the reference implementation.
Do not hand-invent a different fingerprint shape in prompts.

Fingerprints are used to:

- suppress repeat findings already closed or marked `do_not_re_flag`
- identify when an old closure needs `needs_recheck`
- connect lessons to future observations without loading full historical prose
- dedupe merged scout observations before fix grouping

## Negative Examples

At Phase 0, scouts should see compact negative examples from
`digest.yaml.do_not_re_flag`, not raw closed-finding prose.

Use this shape in the digest:

```yaml
do_not_re_flag:
  - find_id: FIND-G4-01
    fingerprint: graph:src/prism/scanner_io:abc123
    reason: "Lazy defaults import is registry-routed pre-scan semantics."
```

If current evidence contradicts a negative example, scouts must mark the
observation `memory_status: needs_recheck` and cite the `find_id`.

## Missed-Finding Feedback

When deep review, God Mode, full validation, or the user finds an issue that
standard scouts missed, write:

`docs/plan/<plan-id>/mutl3y-artifacts/phase7/scout-coverage-patch.yaml`

```yaml
- kind: missed_finding
  missed_by: [Scout-Ownership]
  found_by: Gilfoyle Code Review God Mode
  severity: high
  pattern: "Public facade re-exported an internal registry singleton"
  why_missed: "Scout checked imports but not __all__ re-export symbols."
  new_probe: >-
    rg -n "__all__|DEFAULT_PLUGIN_REGISTRY|build_.*options"
    src/prism/api.py src/prism/cli.py
  prompt_target: references/scout-scan-patterns.md
  proposed_memory_update: "Add facade __all__ re-export probe to Scout-Ownership."
```

The compiler can promote this to a `prompt_rule` when it meets promotion rules.

When the missed finding came from `Gilfoyle Code Review God Mode` and
severity is High or Critical, do not defer the feedback loop to a vague
future cycle. Before the next fresh scout pass:

- update the named `prompt_target` when the change is documentation/prompt-only
- add a concise lesson candidate that describes the exact missed seam family
- mark the next scout cycle as a calibration check for that probe

The goal is not to eliminate God Mode immediately. The goal is to shrink
its net-new High or Critical delta over time and prove that shrinkage with
later scout artifacts.

## Gate-Escape Learning

When a builder's narrow gate passes but the later full gate fails, write:

`docs/plan/<plan-id>/mutl3y-artifacts/phase6/gate-escape-learning.yaml`

```yaml
- kind: gate_escape
  fix_group_key: typing.protocol-normalization
  narrow_gate_that_passed: >-
    .venv/bin/python -m pytest src/prism/tests/test_a.py -q
  full_gate_failure: "test_b.py failed through importer above changed callsite"
  missing_gate: ".venv/bin/python -m pytest src/prism/tests/test_b.py -q"
  proposed_memory_update: >-
    Builder must test importer layers above normalized plugin callsites.
  lesson_kind: gate_rule
```

Future fix-wave plans should include the learned `missing_gate` when the
same fingerprint or fix group recurs.

## Promotion Rules

Promote a candidate to persistent memory only in Phase 7 after a green or
intentionally accepted gate.

Promote when at least one is true:

- two independent examples support the same pattern
- one High/Critical regression has clear evidence
- the user gives an explicit policy correction
- model rollup shows repeated route or quality failure for the same task class
- a deep review finds a High/Critical issue that standard scouts missed

Do not promote:

- one-off tactical notes with no future detection rule
- raw logs or long explanations
- duplicate lessons already covered by `active_lessons`
- findings that are better represented as `do_not_re_flag`

## Phase 7 Write Order

1. Ensure learning candidates and gate escapes are written under the
  plan's artifacts directory.
2. Run:

```bash
python3 "$SKILL_ROOT/scripts/update_learning_memory.py" compile \
  --repo-root . \
  --plan-dir docs/plan/<plan-id> \
  --plan-id <plan-id> \
  --cycle <gN> \
  --focus-axis <axis> \
  --gate-result <GREEN|ACCEPTED>
```

1. Review the JSON summary printed by the compiler.
2. If the compiler reports unexpected promotions or stale memory,
  inspect the touched ledger files before final sign-off.
3. If the compiler reports a YAML parse warning, it has preserved the
  original file as `*.parse-error.bak`; inspect the backup after
  closure and repair the source ledger if the lost data matters.

The digest must be small enough for scouts to read every cycle. Prefer IDs,
counts, and short rules over prose.

## Lesson Quality Bar

Each durable lesson should include:

- `id`
- `kind`
- `cycle`
- `category`
- `lesson`
- `pattern`
- `fingerprint`
- `false_positive_signature`
- optional `prompt_rule`
- optional `routing_rule`
- optional `expires_when`

If a lesson changes a prompt, cite the exact prompt or reference file that
should absorb the rule.
