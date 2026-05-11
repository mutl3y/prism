# Agent Naming

Never use numbered names like `agent-1` or `worker-2`.

Use descriptive names that encode role and slice.

## Patterns

- Discovery scouts: `Scout-Typing`, `Scout-Ownership`, `Scout-ControlFlow`, `Scout-Graph`
- Investigators: `Probe-Imports`, `Probe-Tests`, `Probe-Ownership`
- Builders: `Builder-Typing`, `Builder-Duplication`, `Builder-Ownership`
- Validators: `Gatekeeper`, `Auditor-Regression`
- Bookkeeping: `Archivist-Ledger`

## Rules

- Name must reveal the agent's job without opening its prompt.
- If two agents share a family, differentiate by scope, not numbers.
- Keep the same names across cycles when the role is stable.

Good:

- `Builder-Typing`
- `Probe-Tests`
- `Scout-Graph`

Bad:

- `worker-1`
- `agent-2`
- `subagent-a`
