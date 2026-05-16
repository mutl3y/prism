# Learning Candidate Reference

Use this when writing or editing learning candidates, durable lesson shapes, or
digest content.

## Candidate Types

- `false_positive`
- `missed_finding`
- `bad_fix_pattern`
- `route_failure`
- `quality_failure`
- `workflow_contract_failure`
- `gate_escape`
- `user_policy_correction`

## Compact Candidate Shape

```yaml
- kind: missed_finding
  cycle: gN
  phase: P1
  evidence: docs/plan/<plan-id>/mutl3y-artifacts/phase1/grading-summary.yaml
  pattern: "Scout missed facade leakage through public API re-export"
  proposed_memory_update: "Add facade re-export grep to Scout-Ownership"
  promote_if: "Repeats once, or High/Critical impact"
```

## Fingerprints

Every finding, scout observation, closed entry, and lesson should carry a
stable `fingerprint`.

Fingerprint basis:

- `category`
- owning layer derived from the primary file path
- related symbol names, if known
- normalized title or pattern

Use `scripts/update_learning_memory.py` as the reference implementation.

## Lesson Kinds

- `anti_pattern`
- `false_positive`
- `prompt_rule`
- `routing_rule`
- `architecture_invariant`
- `gate_rule`

## Workflow Lesson Types

- `artifact_schema_failure`
- `prompt_contract_drift`
- `barrier_recovery_rule`
- `worker_model_pairing`
- `phase_resume_rule`

Recommended `kind` pairings:

- `artifact_schema_failure` -> `prompt_rule`
- `prompt_contract_drift` -> `prompt_rule`
- `barrier_recovery_rule` -> `gate_rule`
- `worker_model_pairing` -> `routing_rule`
- `phase_resume_rule` -> `gate_rule`

## Digest Contents

`digest.yaml` should expose only the operational subset:

- paths to model history and rollup
- counts of closed and deferred findings
- active lesson IDs
- do-not-re-flag summaries
- next focus axis
- top open questions
- route-health notes that affect the next dispatch
- deep-review deltas when standard scouts missed important findings

## Staleness And Expiry

At Phase 7, mark a lesson stale or remove it from active digest when:

- a later architecture closure supersedes it
- three clean cycles pass without recurrence and it is too tactical
- the model route recovers according to `model-usage-history.yaml`
- the user corrects or narrows the policy

Keep the historical entry in `lessons.yaml`; remove only from
`digest.yaml.active_lessons` unless the user asks for archival cleanup.
