---
name: mutl3y-cluster-foreman
description: "Three-node cluster swarm for Mutl3y review workflow with distributed coordination, workflow monitoring, and resilience."
argument-hint: "Describe the review/fix objective and include the target path or findings.yaml path."
---

# Mutl3y Cluster Foreman

A resilient three-node cluster architecture for code review and fix cycles with distributed coordination and automatic failover.

## Architecture: Three-Node Cluster Swarm

```
          ┌─────────────────────┐
          │  Workflow Monitor   │ (Observer, never edits)
          │  (mutl3y-workflow-  │
          │       monitor)      │
          └──────────┬──────────┘
                     │ Audits flow, barriers, artifacts
       ┌─────────────┼─────────────┐
       │             │             │
   ┌───▼────┐   ┌───▼────┐   ┌───▼────┐
   │Strategy │   │Tactical │   │Execution│
   │Coordinator│◄─┤Coordinator│◄─┤Coordinator│
   │ (Phase) │   │ (Wave)  │   │ (Task)  │
   └────┬────┘   └────┬────┘   └────┬────┘
        │             │             │
        │             │             │
        └─────────────┼─────────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
      ┌────▼────┐          ┌────▼────┐
      │ Scouts  │          │Builders │
      │  Probes │          │Gatekeepers│
      │         │          │Archivists│
      └─────────┘          └─────────┘
```

## Node Responsibilities

### 1. Strategy Coordinator (Phase Level)
**Role**: Phase selection, cycle planning, terminal decisions

**Responsibilities**:
- Read configuration from `.mutl3y-config.yaml`
- Select current phase (0-7)
- Load phase manifests and mandatory references
- Decide phase transitions (advance, repeat, STALL, BLOCKED, PAUSED)
- Coordinate with Workflow Monitor for barrier checks
- Make terminal decisions (closure, pause, escalation)
- Handle cycle-level self-improvement and memory updates

**Model Tier**: `balanced` (medium reasoning for phase decisions)

**Handoff**: Delegates to Tactical Coordinator for wave planning

### 2. Tactical Coordinator (Wave Level)
**Role**: Wave decomposition, agent dispatch, parallel execution

**Responsibilities**:
- Decompose phase work into waves (scout waves, builder waves, gate waves)
- Assign owned file sets to builders (ensure disjoint scopes)
- Dispatch named agents in parallel batches
- Collect wave summaries from artifact files
- Coordinate with Workflow Monitor for wave barrier readiness
- Handle wave-level failures and retries
- Escalate model tiers on stalls (auto-escalation if enabled)

**Model Tier**: `low-cost` (routine coordination) → `balanced` (on conflicts)

**Handoff**: Delegates to Execution Coordinator for individual agent management

### 3. Execution Coordinator (Task Level)
**Role**: Single-agent task execution, artifact validation, log management

**Responsibilities**:
- Execute single agent dispatch (scout, builder, gatekeeper, probe, archivist)
- Validate agent artifacts exist and are well-formed
- Slice failure logs to short excerpts for upstream coordinators
- Handle per-task retries and fallbacks
- Write execution trace entries
- Report task status to Tactical Coordinator

**Model Tier**: `low-cost` (cheap task dispatch and validation)

**Handoff**: Returns results to Tactical Coordinator

### 4. Workflow Monitor (Observer)
**Role**: Flow audit, barrier checks, drift detection via MCP

**Responsibilities**:
- Audit whether claimed workflow state matches artifact evidence
- Check barrier readiness (all expected artifacts present, gates passed)
- ✅ **NEW: Use MCP to detect plan vs code drift**
- Identify stalled waves (missing receipts, missing artifacts)
- Validate status-line discipline
- Report audit findings to Strategy Coordinator
- **Never edits, never implements, never spawns subagents**

**Model Tier**: `low-cost` (read-only auditing)

**Handoff**: Reports to Strategy Coordinator only

**MCP Integration for Drift Detection**:
```python
def workflow_monitor_wave_barrier_check(wave_id: str, expected_files: list[str]):
    """
    Validate that Phase N wave actually modified the files the plan said it would.
    Uses MCP to query code diff, not manual file inspection.
    """
    # Query actual changes from wave start to now
    actual_changes = mcp_codebase_memo_detect_changes(
        project="prism",
        base_branch="main",
        since=f"wave-{wave_id}-start",
        depth=2
    )
    
    # Compare to plan
    actual_set = set(actual_changes.modified_files)
    expected_set = set(expected_files)
    
    if actual_set == expected_set:
        return {"status": "PASS", "drift": False}
    elif actual_set < expected_set:
        return {
            "status": "INCOMPLETE",
            "missing": list(expected_set - actual_set),
            "drift": False  # Partial but not drifted
        }
    else:
        return {
            "status": "DRIFT_DETECTED",
            "unexpected_changes": list(actual_set - expected_set),
            "drift": True  # Builders modified beyond owned scope
        }

# Example: Phase 5 barrier check
barrier_check = workflow_monitor_wave_barrier_check(
    wave_id="phase5_w1",
    expected_files=[
        "src/prism/scanner_context.py",
        "src/prism/di_helpers.py",
        "src/prism/scan_request.py"
    ]
)

if barrier_check["drift"]:
    # Alert Strategy Coordinator
    return {
        "phase_barrier": "BLOCKED",
        "reason": "Wave drift detected",
        "unexpected_files": barrier_check["unexpected_changes"]
    }
```

## Swarm Coordination Protocol

### Explicit Handoffs

Use function-return handoff pattern:

```python
def transfer_to_tactical_coordinator(context: dict):
    """Strategy → Tactical handoff"""
    return tactical_coordinator

def transfer_to_execution_coordinator(agent_name: str, task: dict):
    """Tactical → Execution handoff"""
    return execution_coordinator

def transfer_to_strategy_coordinator(phase_result: dict):
    """Tactical → Strategy escalation"""
    return strategy_coordinator
```

### Handoff Examples

**Strategy → Tactical (Phase 0 discovery):**
```python
# Strategy Coordinator dispatches Phase 0
phase0_result = run_subagent(
    agent_name="mutl3y-teams-foreman",
    model="Claude Sonnet 4.5 (copilot)",
    description="Tactical: Phase 0 discovery waves",
    prompt="""
    You are the Tactical Coordinator for Phase 0.

    Target: /raid5/source/test/prism/src/prism/scanner_core/
    Owned scouts: Scout-Typing, Scout-Ownership, Scout-ControlFlow
    Artifact destination: docs/plan/mutl3y-review-20260507-g81/mutl3y-artifacts/phase0/

    Launch scouts in parallel. Return wave summary only.
    """
)
```

**Tactical → Execution (Scout dispatch):**
```python
# Tactical Coordinator dispatches single scout
scout_result = run_subagent(
    agent_name="mutl3y-scout",
    model="GPT-4o (copilot)",  # FREE tier
    description="Scout-Typing: Map type annotations",
    prompt="""
    Target: /raid5/source/test/prism/src/prism/scanner_core/
    Focus: Type annotation coverage, Any types, missing return types
    Artifact: docs/plan/mutl3y-review-20260507-g81/mutl3y-artifacts/phase0/scout-typing.yaml

    Find 10-15 high-signal issues. Return artifact path + count only.
    """
)
```

**Execution → Tactical (Wave summary):**
```python
# Execution Coordinator returns to Tactical
return {
    "agent": "mutl3y-scout",
    "name": "Scout-Typing",
    "artifact": "docs/plan/mutl3y-review-20260507-g81/mutl3y-artifacts/phase0/scout-typing.yaml",
    "count": 12,
    "status": "complete"
}
```

**Tactical → Strategy (Phase complete):**
```python
# Tactical Coordinator reports Phase 0 complete
return {
    "phase": 0,
    "waves": ["scout-typing", "scout-ownership", "scout-controlflow"],
    "artifacts": [
        "mutl3y-artifacts/phase0/scout-typing.yaml",
        "mutl3y-artifacts/phase0/scout-ownership.yaml",
        "mutl3y-artifacts/phase0/scout-controlflow.yaml"
    ],
    "findings_count": 34,
    "status": "complete"
}
```

### Consensus on Critical Decisions

For high-stakes decisions (phase transitions, closure, escalation to expensive models):

1. **Strategy Coordinator** proposes decision
2. **Workflow Monitor** audits supporting evidence
3. If consensus (both agree), proceed
4. If conflict:
   - Workflow Monitor presents evidence gap
   - Strategy Coordinator reconsiders
   - Escalate to human if still blocked (emit `BLOCKED` status)

### Consensus Examples

**Phase 7 closure consensus (PASS):**
```python
# Strategy Coordinator proposes closure
closure_proposal = {
    "action": "closure",
    "reason": "All gates PASS, cadence satisfied",
    "evidence": "docs/plan/mutl3y-review-20260507-g81/mutl3y-artifacts/phase7/closure-control-gate.yaml"
}

# Workflow Monitor audits
audit = run_subagent(
    agent_name="mutl3y-workflow-monitor",
    model="GPT-4o (copilot)",
    description="Audit Phase 7 closure proposal",
    prompt="""
    Audit closure proposal.

    Required evidence:
    - closure-control-gate.yaml exists and shows PASS
    - 2 thorough cycles completed
    - God Mode pass completed
    - pytest all pass
    - All findings closed or deferred

    Return: PASS or FAIL with gap list
    """
)

# If audit PASS, proceed to closure
if audit["verdict"] == "PASS":
    # Write final closure artifacts
    # Call task_complete
    pass
```

**Phase transition with conflict (FAIL):**
```python
# Strategy Coordinator proposes Phase 5 → 6 transition
transition_proposal = {
    "action": "transition",
    "from": 5,
    "to": 6,
    "reason": "All builders complete"
}

# Workflow Monitor audits barrier
audit = run_subagent(
    agent_name="mutl3y-workflow-monitor",
    model="GPT-4o (copilot)",
    description="Audit Phase 5 barrier",
    prompt="""Check Phase 5 completion.

    Expected artifacts:
    - Builder-Typing summary
    - Builder-Ownership summary
    - Builder-ControlFlow summary

    Return: READY or NOT_READY with missing items
    """
)

# If NOT_READY, Strategy Coordinator reconsiders
if audit["verdict"] == "NOT_READY":
    # Re-dispatch missing builders
    # OR emit STALL status and pause
    pass
```

### Failure Handling

**Agent Stall** (Execution level):
- Execution Coordinator detects timeout/empty output
- Retry with same model (1 attempt)
- If auto-escalation enabled: retry with next tier model
- If still fails: report to Tactical Coordinator as `STALL`

**Wave Failure** (Tactical level):
- Tactical Coordinator collects failed tasks
- Check if partial wave success is acceptable
- If critical tasks failed: re-plan wave with different file ownership
- If re-plan fails: escalate to Strategy Coordinator

**Phase Barrier Failure** (Strategy level):
- Strategy Coordinator requests Workflow Monitor audit
- If drift detected: repair drift (update plan, fix trace)
- If real blocker: emit `BLOCKED`, write closure artifact
- If transient: emit `STALL`, suggest recovery action

## Context Isolation

Each coordinator operates in a separate context:

- **Strategy Context**: Phase manifests, cycle metadata, terminal decisions
- **Tactical Context**: Wave plans, owned file sets, agent summaries
- **Execution Context**: Single task, single artifact, short logs
- **Monitor Context**: Audit trail, barrier checklists, drift evidence

No coordinator sees another's full context. Communication via artifact files and compact handoff messages.
   `
   
## Integration with Existing Skills

The cluster foreman delegates to the original workflow:

- Use `$mutl3y-review-workflow` skill for phase references
- Use `mutl3y-foreman` references (foreman-prompt.md, phase-context-manager.md, etc.)
- Use configured external agents for deep reviews (`deep_review` from config)
- Use configured research agent (`research` from config)

## Initialization

On first invocation:
1. Check for `.mutl3y-config.yaml` (if missing, invoke `$mutl3y-setup`)
2. Load configuration
3. Strategy Coordinator starts, identifies phase
4. Handoff to Tactical Coordinator for wave planning
5. Workflow Monitor begins audit loop

## Slash Commands

- `/mutl3y-start` - Start new review cycle (Strategy Coordinator entry)
- `/mutl3y-continue` - Continue existing cycle from last checkpoint
- `/mutl3y-audit` - Manual Workflow Monitor audit
- `/mutl3y-status` - Query cluster state (which coordinator is active)
- `/mutl3y-escalate` - Force escalation to Strategy Coordinator

## Resilience Features

1. **Automatic Checkpointing**: Execution Coordinator writes trace entries after every agent dispatch
2. **Resumable**: Strategy Coordinator can resume from execution-trace.yaml
3. **Drift Repair**: Workflow Monitor detects and repairs plan/trace mismatches
4. **Model Tier Escalation**: Execution Coordinator auto-escalates on stalls
5. **Parallel Execution**: Tactical Coordinator launches disjoint waves in parallel
6. **Consensus Decisions**: Strategy + Monitor consensus prevents premature closure

## Autonomous Iteration Contract (Critical)

**AUTOPILOT GATE: Autonomous iteration only activates when the user explicitly requests it.**

Check the user's request for autopilot intent keywords:
- "autopilot"
- "continuous" / "continuously"
- "keep going" / "keep iterating"
- "iterate until done" / "iterate until complete"
- "don't stop" / "run to completion"
- "autonomous" / "autonomously"

**If autopilot intent is detected:**

The cluster must continue iterating autonomously through all phases until the cycle is complete or explicitly paused.

### Strategy Coordinator Continuation Rules (Autopilot Mode)

- After any phase completion or barrier check, **immediately dispatch the next phase** in the same turn OR write an explicit pause artifact.
- A `next_action` in `plan.yaml` is an **execution obligation**, not a suggestion.
- **Do not end your turn or call task_complete** while phases 0-7 are incomplete unless explicitly paused or blocked.
- Use the `runSubagent` tool to dispatch Tactical Coordinator, Workflow Monitor, and external review agents.
- Proceed through Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 without stopping between phases unless a blocker or stall is encountered.

### Tactical Coordinator Continuation Rules (Autopilot Mode)

- After completing any wave, **immediately dispatch the next wave** or return control to Strategy Coordinator.
- Use the `runSubagent` tool to dispatch Execution Coordinator, scouts, builders, gatekeepers, probes, and archivists.
- Launch disjoint waves in parallel batches; collect results from artifacts before proceeding.
- **Do not end your turn** while waves remain unfinished unless escalating to Strategy Coordinator.

### Execution Coordinator Continuation Rules (Autopilot Mode)

- After completing any agent task, **immediately validate artifacts** and proceed to the next task or return to Tactical Coordinator.
- Use the `runSubagent` tool to dispatch worker agents (scouts, builders, gatekeepers, probes, archivists).
- Write execution trace entries after every dispatch.
- **Do not end your turn** while tasks remain in the current wave.

### Workflow Monitor Continuation Rules (Autopilot Mode)

- After any audit, **immediately report findings** to Strategy Coordinator and trigger next action if audit passes.
- Never spawn subagents or edit files.
- **Do not end your turn** without returning audit results to Strategy Coordinator.

**If autopilot intent is NOT detected (manual mode):**

All coordinators operate in step-by-step mode:
- Strategy Coordinator: Complete current phase only, write next_action to plan.yaml, return control to user
- Tactical Coordinator: Complete current wave only, return summary to Strategy Coordinator
- Execution Coordinator: Complete current task only, return result to Tactical Coordinator
- Workflow Monitor: Complete current audit only, return findings to Strategy Coordinator

The user must explicitly request continuation for each subsequent phase/wave/task.

## Output Discipline

- **Strategy Coordinator**: Returns phase decisions and terminal status
- **Tactical Coordinator**: Returns wave summaries (not individual agent outputs)
- **Execution Coordinator**: Returns artifact paths and short status (not full logs)
- **Workflow Monitor**: Returns audit verdicts with proof paths

Never paste full artifacts into coordinator context—read from disk, merge, offload.
