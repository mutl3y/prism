# Agentic Behaviour Enforcement

Development Guidelines for Autonomous and Delegated Execution Behaviour

---

## Always (Priority Hierarchy)

Apply these in order of precedence:

1. **Delegate to subagents whenever possible** to reduce context cost and keep orchestrator context low
   - Operate autonomously only when subagents cannot handle the task or when delegation is cost-inefficient
2. **Drive delegated tasks to closure** and avoid mid-implementation deferrals
3. **When operating autonomously, use [AGENTIC-SKILLS](../skills/AGENTIC-SKILLS/SKILL.md)**
4. **Handle incomplete tasks explicitly**: if a task cannot be completed or delegated due to missing information or hard constraints, document the blocker and escalate to the user

## Agentic Behaviour (Active)

- Error Recovery (max 2 iterations, then escalate)
- Context Tracking (maintain session state, risk assessment)
- Communication Protocols (proactive updates at milestones/blockers)
- Proactive Detection (flag patterns, suggest improvements)
- Task Prioritization (when multiple objectives are given, apply the priority hierarchy)
- Test-Driven Execution (write tests first)
- Parallelism Discipline (run independent work in parallel, serialize coupled work)
- Keep-going Discipline (avoid unnecessary pauses, keep momentum)

---

## Parallelism Discipline (Active)

- Parallelize independent tasks and read-only discovery when there is no shared state
- Serialize tasks that touch overlapping files, shared contracts, or ordered dependencies
- Before parallel edits, define explicit ownership boundaries per worker
- Join at barriers: wait for all parallel workers before advancing phases
- If scope overlap appears mid-run, stop fan-out and re-slice before continuing

---

## Conflict Resolution (Active)

When new guidance conflicts with your active plan:

| Deviation | Action |
|-----------|--------|
| <10% | Adjust plan inline, continue |
| ≥10% | Pause → summarize trade-offs → request clarification → do not assume |

---

## Error Recovery

Max 2 iterations, then escalate. See [AGENTIC-SKILLS](../skills/AGENTIC-SKILLS/SKILL.md) for full protocols.

---

## Completion Checklist

**Before committing:**

- [ ] All affected tests pass
- [ ] No new type checker errors
- [ ] Import boundaries respected
- [ ] No cast() without validation
- [ ] No TODOs without tickets
- [ ] Documentation updated if needed
- [ ] Commit message explains "why" not just "what"

**Before marking work complete:**

- [ ] All planned tasks finished
- [ ] Integration tests pass
- [ ] No known regressions
- [ ] Code reviewed (if applicable)
- [ ] Changelog updated
- [ ] Migration guide written (if breaking changes)
