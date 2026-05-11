# Context Efficiency

Use filesystem offload aggressively. This skill produces large intermediate artifacts; they should live on disk, not be recopied into chat context.

## Offload To Files

- merged Phase 0 observations
- per-cluster Phase 0 observation files
- long finding drafts before final grading
- gate logs under `.mutl3y-gate/`
- file-set conflict maps
- decision tables
- diff probes for false-clean checks
- per-wave change summaries and rollback notes
- micro-swarm investigation notes

Preferred locations:

- `docs/plan/<plan-id>/mutl3y-artifacts/` for durable cycle artifacts
- `.gate/` for transient validation output

Suggested layout:

```text
docs/plan/<plan-id>/
  mutl3y-artifacts/
    phase0/
      sweep-typing.yaml
      sweep-ownership.yaml
      sweep-control-flow.yaml
      sweep-graph.yaml
      merged-observations.yaml
    phase5/
      Builder-Typing-summary.md
      Builder-Ownership-summary.md
    phase3/
      Probe-Imports.md
      Probe-Tests.md
    phase6/
      gate-summary.md
.mutl3y-gate/
  pytest.log
  ruff.log
  black.log
```

## Keep In Context

- current phase
- active findings or category slice
- the exact file being edited
- the specific gate failure excerpt you are fixing
- artifact paths plus the 5-20 lines that matter from them

## Cache-Friendly Layout

If the runtime supports prompt caching:

- keep stable skill instructions and reference paths first
- put changing inputs late: target path, current findings, diff summary, gate failures
- avoid rewriting the stable preamble between cycles

Prompt caching helps repeated cycles. It does not replace filesystem offload.

## Practical Rule

If an intermediate result is longer than a short screenful, write it to a file and keep only:

- artifact path
- one-line purpose
- tiny excerpt or count summary

Named-agent artifacts are preferred because they make handoffs readable without opening the prompt history.
