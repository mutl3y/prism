# Phase 3 Investigation

Purpose:

- Resolve ambiguous findings that need more than scout evidence.
- Run a small, tightly scoped micro-swarm only when the finding actually warrants it.

Source of truth:

- `findings.yaml`
- Conflicting scout, test, runtime, or ownership artifacts
- `mutl3y-artifacts/phase3/` investigation artifacts written by the micro-swarm

Load now:

- `micro-swarm.md`
- `subagent-design.md`
- `phase-3-microswarm-prompt.md`

Use companion entrypoint:

- `../../agents/mutl3y-probe.agent.md`

Rules:

- Open a micro-swarm only when the finding status is `needs_investigation` and at least two evidence sources conflict.
- Scope the swarm to one finding or one tightly coupled cluster.
- Default micro-swarm size is 3-6 named investigators.
- Each investigator answers a different question, writes an artifact, and returns a tiny summary only.
- Persist all investigation output under `mutl3y-artifacts/phase3/`.
- Do not use a whole-cycle interactive swarm.

Outcomes:

- `P3 complete -> P4`
- `repeat P3`
- `STALL`
- `BLOCKED`
