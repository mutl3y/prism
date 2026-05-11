# Anti-Patterns & Core Principles

Development Guidelines for AI Coding Assistant

Scope note: this file defines guardrails and anti-patterns. Autonomous execution enforcement is defined in [AGENTIC_BEHAVIOUR.instructions.md](AGENTIC_BEHAVIOUR.instructions.md).

---

## Core Priorities

**Code Quality:**

- Validate, don't cast: explicit construction over type coercion
- Keep it simple: prefer straightforward solutions over complex abstractions
- Simplify over layering

**Testing & Workflow:**

- Test continuously: validate each file immediately after each change
- Never refactor without testing each file immediately
- Execute tasks in dependency order

**Boundaries & Architecture:**

- Clarity at boundaries; autonomy within bounds
- Never break import boundary guards
- Never create new plugin systems (fix the existing system instead)
- Never layer compatibility over compatibility

**Type Safety:**

- Never use `cast()` without explicit construction
- Never add `@runtime_checkable` Protocols
