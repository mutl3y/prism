# Ledger Schema

Use this only when you need exact file shapes for ledger updates.

Default memory directory: `docs/plan/.mutl3y-lessons`.

## Files

| File | Purpose |
| --- | --- |
| `docs/plan/.mutl3y-lessons/closed_findings.yaml` | Cross-cycle closed/deferred/do-not-re-flag findings and skip patterns |
| `docs/plan/.mutl3y-lessons/lessons.yaml` | Global anti-patterns, false positives, invariants |
| `docs/plan/.mutl3y-lessons/focus-axis-log.yaml` | Focus-axis rotation history |
| `docs/plan/.mutl3y-lessons/import-graph.json` | Cached import graph |
| `docs/plan/.mutl3y-lessons/architecture-graph.json` | Deterministic structural graph for shared architecture context |
| `docs/plan/.mutl3y-lessons/cycle-log.md` | Append-only cycle log |
| `docs/plan/.mutl3y-lessons/digest.yaml` | Compact merged read for review subagents |
| `docs/plan/.mutl3y-lessons/model-usage-history.yaml` | Per-cycle model reliability and quality snapshots |
| `docs/plan/.mutl3y-lessons/model-usage-rollup.yaml` | Compact current/last-3-cycle route health summary |
| `docs/plan/<plan-id>/mutl3y-artifacts/execution-trace.yaml` | Compact per-plan execution checkpoint trace for restart after interruption |

## Minimal Shapes

### `closed_findings.yaml`

```yaml
- id: FIND-01
  fingerprint: duplication:src/prism/scanner_core:abc123def456
  cycle: g3
  category: duplication
  severity: medium
  status: closed
  title: "Example title"
  files_touched:
    - src/example.py
  evidence_one_line: "pytest + lint green; helper consolidated."
```

### `lessons.yaml`

```yaml
anti_patterns:
  - id: LESSON-01
    kind: anti_pattern
    fingerprint: ownership:src/prism/scanner_core:def456abc123
    pattern: "DI factory hardcoding a concrete plugin class"
    category: ownership
    prompt_rule: "Scout-Ownership must check DI factories before declaring scanner_core platform-free."
false_positives:
  - id: FP-01
    pattern: "_get_*_policy(di) helper without prepared bundle"
    suppress_in_categories: [silent_fallback]
invariants:
  - "PluginRegistry is the only path to plugin resolution."
```

The repository may also use a list-shaped lesson ledger:

```yaml
- id: LESSON-09
  kind: prompt_rule
  cycle: g34
  category: subagent_dispatch
  fingerprint: subagent_dispatch:artifact-output:abc123def456
  lesson: "Subagents must verify artifact files exist before reporting success."
  pattern: "subagent dispatch producing a YAML/JSON artifact without explicit artifact_exists check"
  false_positive_signature: "terminal-only dispatches with no file output"
  prompt_rule: "Every file-writing dispatch prompt must require artifact_exists confirmation."
```

### `focus-axis-log.yaml`

```yaml
axes:
  - cycle: g5
    primary: concurrency
    result: zero_critical_high
required_axes: [architecture, typing, ownership, concurrency, error_handling, performance, security, test_gaps]
```

### `digest.yaml`

```yaml
generated_at: 2026-04-25T19:00:00Z
model_usage_history_path: docs/plan/.mutl3y-lessons/model-usage-history.yaml
model_usage_rollup_path: docs/plan/.mutl3y-lessons/model-usage-rollup.yaml
focus_axis_due_next: error_handling
anti_patterns: []
false_positives: []
closed_skip_patterns: {}
invariants: []
active_lessons: []
do_not_re_flag: []
```

Lesson `kind` values:

- `anti_pattern`
- `false_positive`
- `prompt_rule`
- `routing_rule`
- `architecture_invariant`
- `gate_rule`

### `model-usage-history.yaml`

```yaml
version: 1
updated_at: "2026-05-01"
policy:
  source_of_truth: "docs/plan/<plan-id>/mutl3y-artifacts/model-usage-ledger.yaml"
cycles:
  - cycle: g34
    plan_id: gilfoyle-review-20260429-g32-refresh
    ledger_path: docs/plan/gilfoyle-review-20260429-g32-refresh/mutl3y-artifacts/model-usage-ledger.yaml
    highlights: []
    model_snapshot:
      GPT-5 mini:
        attempts: 2
        successes: 1
        quality_avg: 2.0
        status: watch
```

### `model-usage-rollup.yaml`

```yaml
version: 1
generated_at: "2026-05-01T00:00:00Z"
windows:
  last_3_cycles:
    by_model: {}
routing_recommendations:
  degraded_models: []
  watch_models: []
  notes: []
```

### `execution-trace.yaml`

```yaml
version: 1
plan_id: "gilfoyle-review-20260501-g44"
cycle: "g44"
updated_at: "2026-05-02T12:00:00Z"
authoritative_resume_anchor: "docs/plan/gilfoyle-review-20260501-g44/plan.yaml"
latest_checkpoint:
  phase: "P6"
  wave: 2
  status: "OK"
  status_line: "[g44 | P6→P7 | OK — pytest PASS, ruff PASS, black PASS]"
  next_action: "Run Phase 7 closeout bookkeeping."
  blocking_issues: []
  plan_pointer_synced: true
  receipt_proof:
    - "Gatekeeper returned in this turn"
  artifact_proof:
    - "docs/plan/gilfoyle-review-20260501-g44/.mutl3y-gate/pytest.log"
    - "docs/plan/gilfoyle-review-20260501-g44/.mutl3y-gate/ruff.log"
    - "docs/plan/gilfoyle-review-20260501-g44/.mutl3y-gate/black.log"
  source_summary_artifact: "docs/plan/gilfoyle-review-20260501-g44/mutl3y-artifacts/phase6/gate-summary.yaml"
timeline:
  - timestamp: "2026-05-02T12:00:00Z"
    phase: "P6"
    wave: 2
    status: "OK"
    event: "gate_verdict"
    summary: "pytest PASS, ruff PASS, black PASS"
    source_artifacts:
      - "docs/plan/gilfoyle-review-20260501-g44/.mutl3y-gate/pytest.log"
      - "docs/plan/gilfoyle-review-20260501-g44/.mutl3y-gate/ruff.log"
      - "docs/plan/gilfoyle-review-20260501-g44/.mutl3y-gate/black.log"
    plan_pointer_synced: true
```

### `architecture-graph.json`

```json
{
  "generated_at": "2026-04-27T10:30:00Z",
  "repo_root": "/example/repo",
  "nodes": [
    {
      "id": "module:src/prism/api.py",
      "kind": "module",
      "file": "src/prism/api.py",
      "symbol": null,
      "metadata": {
        "is_public_facade": true
      }
    }
  ],
  "edges": [
    {
      "kind": "re_exports",
      "from": "module:src/prism/api.py",
      "to": "function:src/prism/repo_layer/repo_services.py:route_scan_payload"
    }
  ]
}
```

## Ledger Validation

After any update to `docs/plan/<plan-id>/mutl3y-artifacts/model-usage-ledger.yaml` or
`model-scorecard.yaml`, validate both files immediately with:

```bash
python3 <SKILL_ROOT>/scripts/validate_yaml_artifacts.py \
  docs/plan/<plan-id>/mutl3y-artifacts/model-usage-ledger.yaml \
  docs/plan/<plan-id>/mutl3y-artifacts/model-scorecard.yaml \
  > .mutl3y-gate/ledger-validate.log
```

Rules:

- Tabs are forbidden in ledger and scorecard YAML.
- `OVERALL PASS` is required before leaving the barrier or Phase 7 bookkeeping.
- Validation failure is a `STALL`, not a non-blocking bookkeeping issue.

## Deterministic Writer Path

Preferred ledger update path:

```bash
python3 <SKILL_ROOT>/scripts/record_model_usage.py \
  --plan-dir docs/plan/<plan-id> \
  --cycle <gN> \
  --phase <P0|P5|P6|P7> \
  --worker <AGENT_NAME> \
  --task-id <task-id> \
  --requested-tier <tier> \
  --requested-model <model> \
  --actual-model <model> \
  --result <success|route_failure|quality_failure> \
  --failure-type <none|cancelled|timeout|startup|empty_response|missing_artifact|low_signal|mis-scoped_output|other> \
  --artifact-path <artifact-path> \
  --quality-score <1-5> \
  --needed-reedit <true|false> \
  --recovery-action <none|reroute_same_tier|escalate_tier|prompt_tighten|foreman_recovery> \
  --notes "<concise note>" \
  --validate-log .mutl3y-gate/ledger-validate.log
```

Behavior:

- Appends one list-shaped ledger row deterministically.
- Recomputes `model-scorecard.yaml` from the ledger.
- Emits `.mutl3y-gate/ledger-validate.log` and exits non-zero on malformed output.
- Supports `--on-parse-error initialize` for controlled recovery when an existing ledger is already malformed.
