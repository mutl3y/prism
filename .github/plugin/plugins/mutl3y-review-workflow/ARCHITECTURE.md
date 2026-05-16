# Mutl3y Cluster Architecture Overview

## Design Rationale

The three-node cluster architecture addresses specific weaknesses observed in single-foreman workflows:

1. **Context Overload**: A single foreman accumulates phase metadata, wave plans, agent outputs, and failure logs, leading to degraded performance.
2. **Off-Track Behavior**: Without external monitoring, the foreman can drift from workflow discipline (skipping barriers, missing artifacts).
3. **Sequential Bottlenecks**: Single-threaded coordination prevents parallel execution of independent waves.
4. **Failure Propagation**: Foreman stalls cascade to all workers without recovery mechanisms.

## Solution: Distributed Coordination + Observer Pattern

### Three Coordinators (Peer-to-Peer Swarm)

Each coordinator operates in a separate context with explicit handoff protocols:

**Strategy Coordinator (Phase Level)**
- **Context Size**: ~5-10KB (phase manifests, cycle metadata)
- **Model Tier**: `balanced` (needs moderate reasoning for terminal decisions)
- **Handoff Pattern**: Delegates to Tactical → receives phase results
- **Responsibilities**: Phase selection, terminal decisions, self-improvement

**Tactical Coordinator (Wave Level)**
- **Context Size**: ~3-8KB (wave plans, owned file sets)
- **Model Tier**: `low-cost` (routine) → `balanced` (on conflicts)
- **Handoff Pattern**: Receives from Strategy → delegates to Execution → aggregates results → returns to Strategy
- **Responsibilities**: Wave decomposition, parallel dispatch, conflict resolution

**Execution Coordinator (Task Level)**
- **Context Size**: ~1-3KB (single task, single artifact)
- **Model Tier**: `low-cost` (cheap dispatch)
- **Handoff Pattern**: Receives from Tactical → executes agent → returns result
- **Responsibilities**: Single-agent dispatch, artifact validation, retry logic

### Independent Observer (Workflow Monitor)

**Workflow Monitor**
- **Context Size**: ~2-5KB (audit checklists, barrier criteria)
- **Model Tier**: `low-cost` (read-only auditing)
- **Communication**: Reports to Strategy only, never takes control
- **Responsibilities**: Flow audit, barrier checks, drift detection

## Key Patterns Applied

### 1. Context Isolation (from multi-agent-patterns)

Each coordinator sees only its layer:
- Strategy: phase decisions, no wave details
- Tactical: wave coordination, no task-level logs
- Execution: single task, no full wave context
- Monitor: audit evidence, no implementation details

Benefits: No "telephone game" (paraphrasing errors), clean failure boundaries, predictable context growth.

### 2. Explicit Handoff (from multi-agent-patterns)

Function-return handoff ensures type-safe transitions:

```python
def transfer_to_tactical_coordinator(phase_context):
    return tactical_coordinator  # Strategy → Tactical

def transfer_to_execution_coordinator(task):
    return execution_coordinator  # Tactical → Execution
```

Benefits: No ambiguity about who owns control, easy to trace execution flow, simpler debugging.

### 3. Consensus on Critical Decisions (from multi-agent-patterns)

Strategy + Monitor must agree before terminal actions (closure, pause):

```yaml
decision: close_cycle
strategy_vote: approve
monitor_audit: barrier_passed
consensus: true
```

If conflict:
- Monitor presents evidence gap
- Strategy reconsiders
- Escalate to human if still blocked (`BLOCKED` status)

Benefits: Prevents premature closure, catches workflow discipline violations, human-in-the-loop safety net.

### 4. Failure Isolation and Escalation

**Execution Level**: Retry → escalate model tier → report `STALL`
**Tactical Level**: Re-plan wave → escalate to Strategy
**Strategy Level**: Emit `BLOCKED` → write closure artifact → wait for human

Benefits: Local failures don't cascade, automatic recovery for transient issues, clear escalation path.

### 5. Parallel Execution with Disjoint Ownership

Tactical Coordinator ensures builders have non-overlapping file sets:

```yaml
wave_3:
  - builder: Builder-Typing
    owned_files: [src/scanner_core/di.py, src/scanner_core/events.py]
  - builder: Builder-Ownership
    owned_files: [src/scanner_extract/task_line_parsing.py]
```

Launches both in parallel, waits once at barrier.

Benefits: Wall-clock time = max(task_durations), not sum(task_durations); no merge conflicts; clear accountability.

## Coordinator Quick Reference

| Coordinator | Entry Point | Model Tier | Handoff To | Returns To |
|-------------|-------------|------------|------------|------------|
| Strategy | `/mutl3y-start`, `/mutl3y-continue` | `balanced` | Tactical | User |
| Tactical | (from Strategy) | `low-cost`/`balanced` | Execution | Strategy |
| Execution | (from Tactical) | `low-cost` | Worker agents | Tactical |
| Monitor | `/mutl3y-audit`, (auto during barriers) | `low-cost` | (reports to Strategy) | Strategy |

## External Agent Integration

Configuration (`.mutl3y-config.yaml`) specifies external agents:

```yaml
external_agents:

  deep_review: gem-reviewer  # From awesome-copilot
  research: gem-researcher    # From awesome-copilot
  qa: QA                      # Generic
```

Strategy Coordinator dispatches these for:
- **Deep Review**: Unconstrained whole-target review without findings hints (Phase 1, terminal verification)
- **Research**: Architecture discovery, dependency analysis (Phase 0, Phase 3)
- **QA**: Test validation, edge-case analysis (Phase 6)

## Configuration Flow

1. User runs `/mutl3y-config` (or plugin auto-prompts on first use)
2. `mutl3y-setup` skill collects paths and preferences
3. Writes `.mutl3y-config.yaml` to workspace root
4. Strategy Coordinator reads config on startup
5. External agents are available by name (e.g., `gem-reviewer`)

## Resumption and Checkpointing

**Automatic Checkpointing** (Execution Coordinator):
- After every agent dispatch, writes entry to `execution-trace.yaml`
- Includes: agent name, task, status, artifact path, model used

**Resumption** (Strategy Coordinator):
- Reads `execution-trace.yaml` to find last completed phase/wave
- Loads `plan.yaml` to see remaining work
- Workflow Monitor audits for drift (plan vs trace mismatch)
- Resumes from last checkpoint

## Cost and Performance Characteristics

### Token Economics

Baseline: single-agent chat = 1x tokens

- Strategy Coordinator: ~2x tokens (needs phase context)
- Tactical Coordinator: ~1.5x tokens (needs wave coordination)
- Execution Coordinator: ~1x tokens (minimal context)
- Monitor: ~0.5x tokens (read-only, cheap models)

Total cluster overhead: ~5x single-agent baseline

Compare to multi-agent research average: 15x tokens

**Why lower?** Context isolation prevents accumulated history in any single context. Coordinators offload to artifacts aggressively.

### Wall-Clock Time

**Sequential (single foreman)**:
- Phase 0: 5 scouts × 2min = 10min
- Phase 5: 4 builders × 3min = 12min
- Total: ~22min

**Parallel (cluster)**:
- Phase 0: max(5 scouts) = 2min
- Phase 5: max(4 builders) = 3min
- Total: ~5min (75% reduction)

**Trade-off**: More tokens (5x), less time (0.25x)

### Model Tier Usage

Default configuration uses `low-cost` models for 80% of operations:
- Scouts: `low-cost`
- Builders (mechanical): `low-cost`
- Gatekeepers: `low-cost`
- Execution Coordinator: `low-cost`
- Monitor: `low-cost`

Escalate to `balanced` only when needed:
- Strategy Coordinator (terminal decisions)
- Tactical Coordinator (conflicts)
- Builders (non-trivial refactors)

Use `high-reasoning` sparingly:
- Complex architecture decisions
- Ambiguous ownership changes
- Disputed regressions

## Comparison to Original Workflow

| Feature | Single Foreman | Three-Node Cluster |
|---------|----------------|---------------------|
| Context per node | 50-200KB | 1-10KB |
| Parallel execution | No | Yes (disjoint waves) |
| Workflow monitoring | Self-monitored | Independent observer |
| Failure recovery | Manual | Auto-escalation |
| Resumption | Manual checkpoint | Automatic trace |
| Configuration | Hardcoded paths | Interactive setup |
| External agents | Hardcoded names | Configurable |
| Token cost | 1x | 5x |
| Wall-clock time | 1x | 0.25x |

## When to Use Which Foreman

**Use `mutl3y-foreman` (single coordinator) when**:
- Small codebases (<1000 LOC)
- Simple review cycles (light/medium depth)
- Token budget is primary constraint
- Learning the workflow

**Use `mutl3y-cluster-foreman` (three-node) when**:
- Large codebases (>1000 LOC)
- Thorough/deep review cycles
- Wall-clock time matters
- Production workflows
- Need workflow monitoring
- Want parallel execution

## References

- [multi-agent-patterns](../../../agent_and_skills/.github/skills/context-engineering/multi-agent-patterns/SKILL.md)
- [context-efficiency](./skills/mutl3y-foreman/references/context-efficiency.md)
- [model-routing-policy](./skills/mutl3y-foreman/references/model-routing-policy.md)
- [team-topology](./skills/mutl3y-foreman/references/team-topology.md)
