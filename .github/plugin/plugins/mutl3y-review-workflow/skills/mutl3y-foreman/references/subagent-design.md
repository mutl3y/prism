# Subagent Design

Use named teams, not anonymous helpers.

Default companion agent mapping:

- scout work -> [mutl3y-scout.agent.md](../../agents/mutl3y-scout.agent.md)
- probe work -> [mutl3y-probe.agent.md](../../agents/mutl3y-probe.agent.md)
- builder work -> [mutl3y-builder.agent.md](../../agents/mutl3y-builder.agent.md)
- validation work -> [mutl3y-gatekeeper.agent.md](../../agents/mutl3y-gatekeeper.agent.md)
- bookkeeping work -> [mutl3y-archivist.agent.md](../../agents/mutl3y-archivist.agent.md)

## Good Delegation Targets

- wide discovery sweeps
- import/use-site enumeration
- disjoint implementation waves with clear ownership
- optional independent grading
- temporary micro-swarms for one ambiguous finding

## Keep Local In The Foreman

- merge of discovery artifacts
- grading by default
- user-facing decisions
- exact edit planning across teams
- small blocking tasks
- Phase 7 bookkeeping by default

## Ownership Rules

- Every writer owns a declared file set.
- Parallel writers must have disjoint write scopes.
- A worker should adapt to prior edits rather than reverting them.
- If scope expands, stop and re-slice.

## Output Rules

Workers should usually return:

- agent name
- artifact path
- count summary
- 3-8 key bullets max

They should not dump long raw findings into chat if the same data can
live in a file.

## Smells

- the foreman doing implementation by default
- delegating the next critical-path decision and waiting idle
- overlapping fix waves without explicit file ownership
- flat swarm cross-talk instead of artifact handoffs
- giant prose reports that should have been artifact files
