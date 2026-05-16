# Learning Ledger

This is now a short index. Do not load ledger schemas or examples unless you are actively editing ledger files.

## Read This First

- For normal review work, read [ledger-read-protocol.md](./ledger-read-protocol.md).
- For file shapes and example payloads, read [ledger-schema.md](./ledger-schema.md).

## Rule of Thumb

- Review subagents should read only `digest.yaml`, cached `import-graph.json`, and a role-scoped architecture-graph slice.
- The foreman should also read `model-usage-rollup.yaml` before first dispatch.
- Orchestrator updates persistent ledger files only after a green gate or an explicitly accepted closure state.
- During P0-P6, write learning candidates to phase artifacts; do not mutate persistent memory mid-cycle.
- Raw ledger files are fallback material, not first-line context.
- Promote only lessons that change future behavior: scan probes, prompt wording, routing, do-not-re-flag policy, focus-axis rotation, or gate selection.

## Files

- `closed_findings.yaml`: per-plan closed findings and skip patterns
- `lessons.yaml`: repo-global anti-patterns, false positives, invariants
- `focus-axis-log.yaml`: cycle focus rotation history
- `import-graph.json`: cached import graph
- `architecture-graph.json`: deterministic structural graph for shared architecture context
- `cycle-log.md`: append-only cycle summary
- `digest.yaml`: compact merged read for review subagents
- `model-usage-history.yaml`: per-cycle route/quality snapshots
- `model-usage-rollup.yaml`: compact route-health summary for the next dispatch
