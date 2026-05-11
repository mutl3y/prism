# Team Topology

This skill uses a hierarchical team-of-teams model, not a flat swarm.

## Teams

- **Foreman**: owns phase control, merge, grading by default,
  decisions, and final sign-off
  Companion agent: [mutl3y-teams-foreman.agent.md](../../agents/mutl3y-teams-foreman.agent.md)
- **Discovery team**: broad read-only sweep agents
  Companion agent: [mutl3y-scout.agent.md](../../agents/mutl3y-scout.agent.md)
- **Micro-swarm**: temporary 2-3 investigator agents for one ambiguous finding
  Companion agent: [mutl3y-probe.agent.md](../../agents/mutl3y-probe.agent.md)
- **Implementation team**: category-based edit workers with explicit file ownership
  Companion agent: [mutl3y-builder.agent.md](../../agents/mutl3y-builder.agent.md)
- **Validation team**: gate runner and optional regression auditor
  Companion agent: [mutl3y-gatekeeper.agent.md](../../agents/mutl3y-gatekeeper.agent.md)
- **Bookkeeping**: closure and ledger maintenance when delegation is justified
  Companion agent: [mutl3y-archivist.agent.md](../../agents/mutl3y-archivist.agent.md)

## Why

This keeps:

- global reasoning centralized
- discovery parallel
- implementation off the foreman's context budget
- write ownership clear

## Default Split

- Foreman local: merge, decide, grade by default, ledger closeout by default
- Workers: discovery, implementation, optional investigation,
  optional validation audit

Do not let every team talk to every other team directly. Use artifact
files as the handoff surface.

## Agent Selection Rule

- If a Mutl3y companion agent exists for the role, dispatch that exact
  `mutl3y-*` agent first.
- Use generic agents only as fallback, not as a parallel primary lane.
- Valid fallback reasons are limited to:
  - canonical agent unavailable
  - canonical agent unhealthy in-cycle
  - missing required capability for the slice
  - temporary route failure after canonical retry policy is exhausted
- When fallback is used, log:
  - intended Mutl3y role
  - actual agent name
  - fallback reason
  - whether metrics should be normalized back to the canonical lane in the
    summary artifact
