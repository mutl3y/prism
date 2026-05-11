---
name: mutl3y-foreman
description: "Thin foreman for Mutl3y review/fix cycles. Orchestrates workflow phases and delegates model selection to model-router skill."
argument-hint: "Describe the review/fix objective and include the target path or findings.yaml path."
---

# Mutl3y Foreman (v2 - Thin Orchestrator)

**Purpose**: Workflow orchestration for Mutl3y review/fix cycles. Model selection delegated to model-router skill.

**Architecture**: Thin orchestrator → queries model-router → dispatches named subagents

---

## Reference Materials

This skill includes 60 reference documents covering all aspects of the Mutl3y workflow. See `references/` folder:

**Core Protocols**:
- `deep-review-protocol.md` - Five-layer review methodology
- `foreman-execution-guardrails.md` - Execution safety and context management
- `iteration-cadence.md` - Timing and phasing guidance

**Phase-Specific Guides**:
- `phase-0-discovery.md`, `phase-0-sweep-prompt.md` - Scout launch protocol
- `phase-1-grading.md`, `phase-1-grader-prompt.md` - Finding severity assignment
- `phase-2-persist-plan.md` - Plan structure and persistence
- `phase-3-investigation.md`, `phase-3-microswarm-prompt.md` - Ambiguous finding investigation
- `phase-4-decide.md` - Wave triage and sequencing
- `phase-5-implementation.md`, `phase-5-builder-policy.md`, `phase-5-fix-wave-prompt.md` - Builder dispatch and file ownership
- `phase-6-validation.md`, `parallel-gate.md` - Gate execution and parallelism
- `phase-7-close-and-learn.md`, `phase-7-ledger-updater-prompt.md` - Closure and ledger updates

**Workflow Patterns**:
- `team-topology.md` - Team shapes and specialization
- `subagent-design.md`, `agent-naming.md` - Agent responsibilities
- `parallel-execution.md`, `parallel-sweep-and-waves.md` - Parallelization patterns
- `multiprocess-execution.md` - Concurrent execution strategy

**Telemetry & Learning**:
- `learning-ledger.md` - Ledger schema for outcomes
- `learning-candidate-reference.md` - Findings that are learning-worthy
- `model-usage-ledger-template.yaml` - Telemetry template
- `iteration-cadence.md` - Learning loop cadence

**Troubleshooting**:
- `common-traps.md` - Gotchas and mitigations
- `context-degradation-playbook.md` - Context window recovery
- `safeguards.md` - Safety guardrails

---

## Mission

Run findings-driven Python review/fix cycles while keeping orchestrator context small.

**Key principle**: This skill orchestrates WHAT to do, model-router determines WHICH model to use.

---

## Workflow Phases

1. **Phase 0: Discovery** - Parallel scouts find issues
   - **Reference**: [phase-0-discovery.md](./references/phase-0-discovery.md), [phase-0-sweep-prompt.md](./references/phase-0-sweep-prompt.md)
   
2. **Phase 1: Grading** - Assign severity to findings
   - **Reference**: [phase-1-grading.md](./references/phase-1-grading.md), [phase-1-grader-prompt.md](./references/phase-1-grader-prompt.md)
   
3. **Phase 2: Planning** - Persist plan and tasks
   - **Reference**: [phase-2-persist-plan.md](./references/phase-2-persist-plan.md)
   
4. **Phase 3: Investigation** - Probe ambiguous findings
   - **Reference**: [phase-3-investigation.md](./references/phase-3-investigation.md), [phase-3-microswarm-prompt.md](./references/phase-3-microswarm-prompt.md)
   
5. **Phase 4: Decide** - Triage implementation waves
   - **Reference**: [phase-4-decide.md](./references/phase-4-decide.md)
   
6. **Phase 5: Implementation** - Builders fix issues in waves
   - **Reference**: [phase-5-implementation.md](./references/phase-5-implementation.md), [phase-5-builder-policy.md](./references/phase-5-builder-policy.md), [phase-5-fix-wave-prompt.md](./references/phase-5-fix-wave-prompt.md)
   
7. **Phase 6: Validation** - Gates verify correctness
   - **Reference**: [phase-6-validation.md](./references/phase-6-validation.md), [parallel-gate.md](./references/parallel-gate.md)
   
8. **Phase 7: Closure** - Archive lessons and update ledger
   - **Reference**: [phase-7-close-and-learn.md](./references/phase-7-close-and-learn.md), **REQUIRED**: [closure-control-gate.md](./references/closure-control-gate.md)

---

## Critical Rules

### Execution Guardrails

Consult [foreman-execution-guardrails.md](./references/foreman-execution-guardrails.md) for context management, phase sequencing, and execution safety.

### Context Budget & Degradation

**Start every cycle with explicit context budget:**
```yaml
live_context = stable_rules + current_phase + active_findings + short_excerpts
```

- Keep stable instructions in SKILL.md and references; keep changing state in artifacts
- Offload raw outputs, logs, long tables to artifacts under `docs/plan/{plan_id}/artifacts/`
- Merge from disk artifacts, not chat replies
- If live context approaches limits, **consult [context-efficiency.md](./references/context-efficiency.md)** for offload rules

**When context continuity weakens despite artifact-first flow:**
- Consult [context-degradation-playbook.md](./references/context-degradation-playbook.md) for recovery
- For resumed/interrupted cycles, consult [anchored-compaction.md](./references/anchored-compaction.md) for checkpoint strategy

### Context Pressure Handling

- If live context approaches limits, consult [context-efficiency.md](./references/context-efficiency.md) for keep-in-context rules and offload strategy.
- If context continuity weakens despite artifact-first flow, consult [context-degradation-playbook.md](./references/context-degradation-playbook.md) for recovery.
- For resumed or interrupted cycles, consult [anchored-compaction.md](./references/anchored-compaction.md) for checkpoint strategy.

### Team & Agent Guidance

Consult [team-topology.md](./references/team-topology.md) for:
- Team shapes and role definitions
- Named subagent responsibilities (Scout, Builder, Probe, Gatekeeper, Archivist)
- Companion agent defaults and fallback rules
- Disjoint file ownership patterns

### Learning & Improvement

- During Phase 7 closure, consult [self-improvement-protocol.md](./references/self-improvement-protocol.md) for lesson promotion rules, lesson kinds, and digest shape.
- When reviewing durable lessons, consult [memory-hygiene.md](./references/memory-hygiene.md) for stale/superseded/conflicting-rule detection.
- Consult [learning-candidate-reference.md](./references/learning-candidate-reference.md) to determine which findings are worth promoting as lessons.

### Common Patterns & Traps

- Consult [common-traps.md](./references/common-traps.md) for file-collision prevention, context-overflow mitigation, and other gotchas.
- Consult [deep-review-protocol.md](./references/deep-review-protocol.md) for the five-layer review methodology and when to escalate.
- Consult [iteration-cadence.md](./references/iteration-cadence.md) for cycle timing and phase pacing.

---

## Model Selection (NEW v2 Pattern)

### ✅ ALWAYS Query model-router Before Dispatch

```python
# Step 1: Query model-router skill
from model_router import query_model_router

routing = query_model_router(
    task_type="discovery",  # or "code_review", "implementation", etc.
    cost_priority="low",    # or "balanced", "premium"
    instruction_compliance=True,  # Enforce gates (e.g., block Opus for Gilfoyle)
    focus_area=None        # or "concurrency", "type_safety", etc.
)

# Step 2: Use returned config
runSubagent(
    agent_name="mutl3y-scout",
    model=routing.model,  # Dynamic from router!
    prompt=f"{routing.prompt_template}\n\nYour task: ...",
    description=f"Scout with {routing.model}"
)

# Step 3: Log outcome for telemetry
log_routing_outcome(
    task_id="g85-phase0-scout1",
    routing_config=routing,
    outcome="success",
    quality_score=82,
    findings_count=15
)
```

### ❌ NEVER Hardcode Model Names

```python
# ❌ OLD WAY (v1): Hardcoded models
runSubagent(
    agent_name="mutl3y-scout",
    model="GPT-4o (copilot)",  # WRONG: Hardcoded!
    ...
)

# ✅ NEW WAY (v2): Query router
routing = query_model_router(task_type="discovery", cost_priority="low")
runSubagent(
    agent_name="mutl3y-scout",
    model=routing.model,  # RIGHT: Dynamic!
    ...
)
```

---

## Phase 0: Discovery

**Goal**: Launch parallel scouts to find issues

**Model selection strategy**: Low-cost tier (discovery task)

**Before dispatch**: Consult [phase-0-sweep-prompt.md](./references/phase-0-sweep-prompt.md) for detailed scout prompt templates and discovery strategy.

```python
# Query architecture context first (optional but recommended)
arch_context = mcp_codebase_memo_get_architecture(
    project="prism",
    aspects=["packages", "layer_boundaries", "high_coupling_modules"]
)

# Launch 4 scouts in parallel
scouts = []
for scout_type in ["typing", "ownership", "control_flow", "dependencies"]:
    # Query router for each scout
    routing = query_model_router(
        task_type="discovery",
        cost_priority="low",
        instruction_compliance=False,  # Scouts don't need strict compliance
        focus_area=None
    )
    
    scouts.append(
        runSubagent(
            agent_name="mutl3y-scout",
            model=routing.model,
            description=f"Scout-{scout_type.title()}",
            prompt=f"""
Scout {scout_type} issues in scanner_core.

Architecture context:
{arch_context}

Focus: {get_scout_focus(scout_type)}
Artifact: docs/plan/{plan_id}/artifacts/phase0/scout-{scout_type}.yaml
            """
        )
    )
    
    # Log routing decision
    log_routing_outcome(
        task_id=f"{plan_id}-phase0-scout-{scout_type}",
        routing_config=routing,
        outcome="dispatched",
        notes=f"Scout {scout_type} using {routing.model}"
    )
```

---

## Phase 5: Implementation

**Goal**: Builders fix issues in disjoint waves

**Model selection strategy**: Depends on task complexity
- Mechanical changes (type annotations): low-cost tier
- Architecture changes (DI refactor): balanced tier
- Cross-layer refactor: balanced tier, escalate to premium if needed

**Before dispatch**: Consult [phase-5-fix-wave-prompt.md](./references/phase-5-fix-wave-prompt.md) for detailed builder prompt templates and [phase-5-builder-policy.md](./references/phase-5-builder-policy.md) for file ownership rules.

```python
# Wave 1: 3 builders on disjoint files
builders = []

# Define builder tasks
builder_tasks = [
    {
        "name": "Builder-Typing-W1",
        "owned_files": ["scanner_context.py"],
        "task": "Add type annotations per g81-T01-T03",
        "complexity": "mechanical"  # Low complexity
    },
    {
        "name": "Builder-Ownership-W1",
        "owned_files": ["di_helpers.py", "defaults.py"],
        "task": "Extract DI policy resolver per g81-T08",
        "complexity": "architectural"  # High complexity
    },
    {
        "name": "Builder-ControlFlow-W1",
        "owned_files": ["variable_discovery.py"],
        "task": "Simplify control flow per g81-T12",
        "complexity": "mechanical"  # Low complexity
    }
]

# Dispatch each builder with appropriate model
for task in builder_tasks:
    # Query router based on complexity
    cost_priority = "low" if task["complexity"] == "mechanical" else "balanced"
    
    routing = query_model_router(
        task_type="implementation",
        cost_priority=cost_priority,
        instruction_compliance=False,
        focus_area=None
    )
    
    builders.append(
        runSubagent(
            agent_name="mutl3y-builder",
            model=routing.model,
            description=task["name"],
            prompt=f"""
{routing.prompt_template}

Owned files: {', '.join(task['owned_files'])}
Task: {task['task']}

Artifact: docs/plan/{plan_id}/artifacts/phase5/{task['name'].lower()}.yaml
            """
        )
    )
    
    # Log routing
    log_routing_outcome(
        task_id=f"{plan_id}-phase5-{task['name']}",
        routing_config=routing,
        outcome="dispatched",
        notes=f"{task['name']} ({task['complexity']}) using {routing.model}"
    )
```

---

## Phase 3: Investigation

**Goal**: Probe ambiguous findings

**Model selection strategy**: Balanced tier (investigation requires reasoning)

**Before dispatch**: Consult [phase-3-microswarm-prompt.md](./references/phase-3-microswarm-prompt.md) for detailed probe prompt templates and investigation strategy.

```python
# Probe ambiguous findings
routing = query_model_router(
    task_type="code_review",  # Investigation similar to review
    cost_priority="balanced",  # Need reasoning capability
    instruction_compliance=False,
    focus_area="architecture"  # Investigating structural issues
)

runSubagent(
    agent_name="mutl3y-probe",
    model=routing.model,
    description="Probe-Imports: Investigate circular import risk",
    prompt=f"""
{routing.prompt_template}

Question: Can scanner_core import from scanner_plugins without cycle?
Check: Import graph, __init__.py exposure, lazy import patterns.

Output: docs/plan/{plan_id}/artifacts/phase3/probe-imports.yaml
    """
)
```

---

## Phase 6: Validation Gate

**Goal**: Run test/lint/typecheck gates

**Model selection**: Gatekeeper uses low-cost tier (validation task)

```python
# Query router for gatekeeper
routing = query_model_router(
    task_type="validation",
    cost_priority="low",
    instruction_compliance=False,
    cluster_topology_preference="3-node"  # Gatekeeper benefits from clustering
)

runSubagent(
    agent_name="mutl3y-gatekeeper",
    model=routing.model,
    description="Gatekeeper: Run validation gates",
    prompt=f"""
{routing.prompt_template}

Run gates:
1. pytest src/prism/tests/ -q
2. ruff check src/prism
3. mypy src/prism

Log results to: docs/plan/{plan_id}/.mutl3y-gate/

Artifact: docs/plan/{plan_id}/artifacts/phase6/gate-results.yaml
    """
)
```

---

## Phase 7: Closure Requirements (CRITICAL)

### ✅ HARD PRECONDITION: Closure Control Gate

**BEFORE calling task_complete or claiming cycle closure:**

1. Load [closure-control-gate.md](./references/closure-control-gate.md)
2. Run all gate checks defined in that reference
3. Write `docs/plan/{plan_id}/artifacts/phase7/closure-control-gate.yaml` with results
4. Verify ALL checks show `status: PASS`
5. **Only then** proceed to archivist dispatch and task_complete

**This is NOT optional. Do not skip or synthesize locally.**

```python
# Load and execute closure gate
from pathlib import Path
import yaml

gate_ref = Path("./references/closure-control-gate.md").read_text()
# Parse gate requirements from reference

gate_results = {
    "validation_gates": {
        "pytest_all_pass": True,
        "ruff_clean": True,
        "mypy_delta_zero": True
    },
    "findings_status": {
        "open_blocking": 0,
        "open_high": 0
    },
    "can_close": {
        "decision": "PASS",  # or FAIL
        "blocking_issues": [],
        "next_action": "Proceed to Phase 7 archivist"
    }
}

# Write gate result
with open(f"docs/plan/{plan_id}/artifacts/phase7/closure-control-gate.yaml", "w") as f:
    yaml.dump(gate_results, f)

# Verify PASS before continuing
if gate_results["can_close"]["decision"] != "PASS":
    # ❌ BLOCKED: Cannot close
    write_pause_artifact(plan_id, gate_results["can_close"]["blocking_issues"])
    return  # Do NOT call task_complete
else:
    # ✅ PASS: Continue to archivist
    run_subagent(
        agent_name="mutl3y-archivist",
        model=query_model_router(task_type="validation", cost_priority="low").model,
        description="Archivist: Update ledger and promote lessons",
        prompt=f"Load [phase-7-ledger-updater-prompt.md](./references/phase-7-ledger-updater-prompt.md) for detailed instructions..."
    )
```

### Phase 7 Learning & Ledger Update

Consult [phase-7-close-and-learn.md](./references/phase-7-close-and-learn.md) and [phase-7-ledger-updater-prompt.md](./references/phase-7-ledger-updater-prompt.md) for:

- Lesson promotion criteria
- Ledger schema and update rules
- `.mutl3y-lessons/` file structure
- Learning candidate evaluation

**Key rule**: Use [memory-hygiene.md](./references/memory-hygiene.md) to detect stale, superseded, or conflicting lessons before promotion.

---

## Recording Telemetry

**After each dispatch**, record routing outcome:

```python
def log_routing_outcome(task_id, routing_config, outcome, quality_score=None, findings_count=None, notes=None):
    """
    Record routing decision for telemetry feedback.
    
    Flows to: .mutl3y-lessons/ → mempalace → future routing decisions
    """
    telemetry = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "model": routing_config.model,
        "model_tier": routing_config.model_tier,
        "cost_multiplier": routing_config.cost_multiplier,
        "cluster_topology": routing_config.cluster_topology,
        "outcome": outcome,  # "success" | "failure" | "timeout" | "low_quality"
        "quality_score": quality_score,
        "findings_count": findings_count,
        "notes": notes
    }
    
    # Append to lesson file
    append_yaml(
        f"docs/plan/{plan_id}/.mutl3y-lessons/model-usage-{cycle}.yaml",
        telemetry
    )
    
    # Also log via script for ledger update
    run_command(f"""
python3 scripts/record_model_usage.py \\
  --plan-id {plan_id} \\
  --cycle {cycle} \\
  --phase {current_phase} \\
  --worker {task_id} \\
  --actual-model "{routing_config.model}" \\
  --result {outcome} \\
  --quality-score {quality_score or 0}
    """)
```

---

## MCP Integration

### Architecture Context (Phase 0)

```python
# Before launching scouts, query architecture
arch_context = mcp_codebase_memo_get_architecture(
    project="prism",
    aspects=["packages", "services", "dependencies", "layer_boundaries"]
)

# Benefit: Scouts get targeted context without flooding tokens
# Result: 25-30% faster discovery, 35% fewer exploratory questions
```

### Ownership Validation (Phase 5)

```python
# Before parallel builders, validate disjoint file ownership
ownership_audit = mcp_codebase_memo_detect_changes(
    project="prism",
    base_branch="main",
    since="wave-4-end",
    depth=2
)

# Prevent file collisions
validate_disjoint_ownership(owned_files_by_builder)
```

---

## Workflow Examples

### Example 1: Start New Cycle

```bash
# Create plan structure
plan_id="mutl3y-review-20260509-g85"
mkdir -p docs/plan/${plan_id}/{artifacts/{phase0,phase1,phase2,phase3,phase5,phase6,phase7},.mutl3y-gate}

# Initialize plan.yaml
cat > docs/plan/${plan_id}/plan.yaml << 'EOF'
plan_id: mutl3y-review-20260509-g85
cycle: g85
focus_axis: typing
status: phase0_discovery
target_path: src/prism/scanner_core/
next_action: "Phase 0: Dispatch 4 parallel scouts"
EOF

# Initialize findings.yaml
cat > docs/plan/${plan_id}/findings.yaml << 'EOF'
findings: []
EOF
```

### Example 2: Phase 0 Dispatch (Parallel Scouts)

```python
# Step 1: Query architecture context
arch_context = mcp_codebase_memo_get_architecture(project="prism")

# Step 2: Launch 4 scouts with router-selected models
for scout_type in ["typing", "ownership", "control_flow", "dependencies"]:
    routing = query_model_router(
        task_type="discovery",
        cost_priority="low"
    )
    
    runSubagent(
        agent_name="mutl3y-scout",
        model=routing.model,
        description=f"Scout-{scout_type.title()}",
        prompt=f"Scout {scout_type} in scanner_core\n{arch_context}"
    )
```

### Example 3: Phase 5 Wave (Builders)

```python
# Mechanical tasks: low-cost tier
routing_mech = query_model_router(
    task_type="implementation",
    cost_priority="low"
)

# Architectural tasks: balanced tier
routing_arch = query_model_router(
    task_type="implementation",
    cost_priority="balanced"
)

# Dispatch builders
builders = [
    runSubagent(
        agent_name="mutl3y-builder",
        model=routing_mech.model,  # Low-cost for typing
        description="Builder-Typing",
        prompt="Add type annotations to scanner_context.py"
    ),
    runSubagent(
        agent_name="mutl3y-builder",
        model=routing_arch.model,  # Balanced for DI refactor
        description="Builder-Ownership",
        prompt="Extract DI policy resolver to defaults.py"
    )
]
```

---

## Continuation & Execution Modes

### Autopilot Mode vs. Manual Mode

**AUTOPILOT INTENT**: The user explicitly requests continuous execution using keywords like:
- "keep going"
- "run to completion"  
- "iterate until done"
- "autonomous"
- "continuously"

**If autopilot intent is detected:**
- Continue iterating autonomously through all phases until cycle complete or explicitly paused
- After completing any phase, **immediately dispatch the next phase** without waiting for user confirmation
- A `next_action` in `plan.yaml` is an **execution obligation**, not a note for later
- **Do not call task_complete** while a valid `next_action` exists (unless paused)

**If autopilot intent is NOT detected (manual mode):**
- Complete only the current phase or task requested
- Write `next_action` to `plan.yaml` recommending what to do next
- Call `task_complete` with summary and return control to user
- Wait for explicit user instruction before continuing

### Pausing & Unblocking

**When to pause** (even in autopilot):
- Gate validation fails and requires user decision
- Ambiguous architectural choice blocks implementation
- Need external input to triage findings

**Pause pattern:**
```python
# Write pause artifact
with open(f"docs/plan/{plan_id}/PAUSED.md", "w") as f:
    f.write(f"""
## Cycle Paused: {plan_id}

**Reason**: {blocker_description}

**Resume action**: User decision on {decision_point}

**Status**: Phase {current_phase} waiting for user
""")

# Update plan.yaml
update_yaml(f"docs/plan/{plan_id}/plan.yaml", {
    "status": "paused",
    "next_action": f"User decision: {decision_point}"
})

# Now call task_complete (breaking autopilot flow)
```

**When resuming from pause:**
- User says "continue with [Option A]" or similar
- Foreman loads PAUSED.md to understand context
- Foreman resumes from specified decision point
- If autopilot keywords present in resume request, continue autonomously

---

## Anti-Patterns

### ❌ NEVER: Hardcode Model Names

```python
# ❌ WRONG
runSubagent(model="GPT-4o (copilot)", ...)  # Hardcoded!

# ✅ RIGHT
routing = query_model_router(task_type="discovery", cost_priority="low")
runSubagent(model=routing.model, ...)
```

### ❌ NEVER: Skip Router Query

```python
# ❌ WRONG: Assuming model without querying
runSubagent(model="Claude Haiku 4.5 (copilot)", ...)  # No justification!

# ✅ RIGHT: Let router decide based on task characteristics
routing = query_model_router(...)  # Returns model + justification
runSubagent(model=routing.model, ...)
```

### ❌ NEVER: Parallel Builders on Same Files

```python
# ❌ WRONG: File collision
builders = [
    runSubagent(prompt="Owned: scanner_context.py, di.py\nTask: Extract policy"),
    runSubagent(prompt="Owned: scanner_context.py, scan_request.py\nTask: Add types")
]
# scanner_context.py appears in both - WILL COLLIDE!

# ✅ RIGHT: Disjoint file sets
builders = [
    runSubagent(prompt="Owned: di.py\nTask: Extract policy"),
    runSubagent(prompt="Owned: scan_request.py\nTask: Add types"),
    runSubagent(prompt="Owned: scanner_context.py\nTask: Wire both")  # Wave 2, after deps
]
```

---

## Removed Content (Delegated to model-router)

The following content was **removed from v1** and is now handled by model-router skill:

- ❌ `references/model-routing-policy.md` (~400 lines) - **Deleted**
- ❌ Hardcoded model examples (~150 lines) - **Replaced with router queries**
- ❌ Anti-pattern tier examples (~40 lines) - **Removed (gating automatic)**
- ❌ Tier reference guide (~80 lines) - **Removed (query router instead)**
- ❌ Model routing live rules (~110 lines) - **Simplified to "query router"**

**Total reduction**: ~780 lines removed, delegated to model-router skill

---

## References

### Active References (Keep in mutl3y-foreman)

Workflow-specific references remain:
- `references/deep-review-protocol.md` - Review depth rules
- `references/iteration-cadence.md` - Cycle cadence rules
- `references/phase-*-*.md` - Phase-specific guidance
- `references/closure-control-gate.md` - Closure requirements
- `references/foreman-execution-guardrails.md` - Execution rules

### Delegated References (Moved to model-router)

Model selection references now live in model-router skill:
- Model selection database → mempalace `copilot_models` wing
- Routing rules → query `model-router` skill
- Cost projections → `model-router/references/cost-quality-curves.md`
- g84 study findings → `model-router/references/g84-study-summary.md`

---

## Key Rules

1. ✅ **Always query model-router** before dispatching subagents
2. ✅ **Log every routing decision** for telemetry feedback
3. ✅ **Use MCP context queries** to give scouts targeted information
4. ✅ **Validate disjoint file ownership** before parallel builders
5. ✅ **Run gates as validation** (pytest/ruff/mypy)
6. ✅ **Close with closure-control-gate.yaml** satisfaction

---

## Migration from v1

If you have existing v1 mutl3y-foreman usage:

**v1 (disabled) location**: `/raid5/source/test/mutl3y_review_workflow_development/skills/mutl3y-foreman-v1-disabled/`

**Changes in v2**:
- All model selection now delegated to model-router skill
- `references/model-routing-policy.md` removed (~400 lines)
- Hardcoded model examples replaced with router queries
- ~780 lines removed (65% reduction)
- Only workflow orchestration remains

**See**: `MIGRATION_NOTES.md` for detailed migration guide

---

**Version**: 2.0 (Thin Orchestrator)  
**Last Updated**: 2026-05-09  
**Status**: Active
