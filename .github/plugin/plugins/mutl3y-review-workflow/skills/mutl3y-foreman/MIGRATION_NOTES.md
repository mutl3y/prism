# Migration Guide: mutl3y-foreman v1 → v2

**Migration Date**: 2026-05-09  
**Impact**: Breaking change - all model selection now delegated to model-router skill

---

## What Changed

### v1 (Disabled): Monolithic
- **~1,200 lines** with embedded routing logic
- Hardcoded model examples throughout
- `references/model-routing-policy.md` (~400 lines)
- Manual model tier decisions

### v2 (Active): Thin Orchestrator
- **~420 lines** (65% reduction)
- No hardcoded models
- Delegates all routing to model-router skill
- Query-driven model selection

---

## Breaking Changes

### 1. Model Selection API

**v1 (Old)**:
```python
# Hardcoded model selection
runSubagent(
    agent_name="mutl3y-scout",
    model="GPT-4o (copilot)",  # ❌ Hardcoded
    description="Scout typing",
    prompt="Find type issues in scanner_core..."
)
```

**v2 (New)**:
```python
# Query model-router first
routing = query_model_router(
    task_type="discovery",
    cost_priority="low",
    instruction_compliance=False
)

runSubagent(
    agent_name="mutl3y-scout",
    model=routing.model,  # ✅ Dynamic
    description="Scout typing",
    prompt=f"{routing.prompt_template}\n\nFind type issues in scanner_core..."
)

# Log outcome
log_routing_outcome(
    task_id="g85-phase0-scout-typing",
    routing_config=routing,
    outcome="success"
)
```

### 2. Removed Files

- ❌ `references/model-routing-policy.md` - **DELETED** (now in model-router skill)

### 3. Removed Content from SKILL.md

- ❌ Hardcoded model examples (~150 lines)
- ❌ Anti-pattern tier examples (~40 lines)
- ❌ Tier reference guide (~80 lines)
- ❌ Model routing live rules (~110 lines)

---

## Migration Steps

### Step 1: Update All runSubagent Calls

**Pattern**:
```python
# Before: Hardcoded model
runSubagent(
    agent_name="mutl3y-scout",
    model="GPT-4o (copilot)",
    ...
)

# After: Query router
routing = query_model_router(
    task_type="discovery",  # Match task type
    cost_priority="low"      # Match old tier intent
)
runSubagent(
    agent_name="mutl3y-scout",
    model=routing.model,
    ...
)
```

**Task type mapping**:
- Scouts → `task_type="discovery"`
- Builders (mechanical) → `task_type="implementation"` + `cost_priority="low"`
- Builders (architectural) → `task_type="implementation"` + `cost_priority="balanced"`
- Probes → `task_type="code_review"` + `cost_priority="balanced"`
- Gatekeepers → `task_type="validation"` + `cost_priority="low"`

### Step 2: Add Telemetry Logging

After each dispatch, log the routing decision:

```python
log_routing_outcome(
    task_id=f"{plan_id}-{phase}-{worker_name}",
    routing_config=routing,
    outcome="success",  # or "failure", "timeout", "low_quality"
    quality_score=82,   # Optional
    findings_count=15   # Optional
)
```

### Step 3: Update Phase 0 Dispatch

**v1 (Old)**:
```python
scouts = [
    runSubagent(agent="mutl3y-scout", model="GPT-4o (copilot)", ...),
    runSubagent(agent="mutl3y-scout", model="GPT-5 mini (copilot)", ...),
    runSubagent(agent="mutl3y-scout", model="Raptor mini (copilot)", ...),
    runSubagent(agent="mutl3y-scout", model="GPT-4.1 (copilot)", ...),
]
```

**v2 (New)**:
```python
scouts = []
for scout_type in ["typing", "ownership", "control_flow", "dependencies"]:
    routing = query_model_router(
        task_type="discovery",
        cost_priority="low"
    )
    
    scouts.append(
        runSubagent(
            agent="mutl3y-scout",
            model=routing.model,  # Dynamic
            description=f"Scout-{scout_type.title()}",
            prompt=f"Scout {scout_type} in scanner_core"
        )
    )
    
    log_routing_outcome(
        task_id=f"{plan_id}-phase0-scout-{scout_type}",
        routing_config=routing,
        outcome="dispatched"
    )
```

### Step 4: Update Phase 5 Builders

**v1 (Old)**:
```python
# Hardcoded tier decisions
builders = [
    runSubagent(agent="mutl3y-builder", model="GPT-5.4 mini (copilot)", ...),  # Mechanical
    runSubagent(agent="mutl3y-builder", model="Claude Haiku 4.5 (copilot)", ...),  # Mechanical
    runSubagent(agent="mutl3y-builder", model="Claude Sonnet 4.5 (copilot)", ...),  # Architectural
]
```

**v2 (New)**:
```python
# Query router based on task complexity
builder_tasks = [
    {"name": "Builder-Typing", "complexity": "mechanical"},
    {"name": "Builder-ControlFlow", "complexity": "mechanical"},
    {"name": "Builder-Ownership", "complexity": "architectural"},
]

builders = []
for task in builder_tasks:
    cost = "low" if task["complexity"] == "mechanical" else "balanced"
    
    routing = query_model_router(
        task_type="implementation",
        cost_priority=cost
    )
    
    builders.append(
        runSubagent(
            agent="mutl3y-builder",
            model=routing.model,
            description=task["name"],
            prompt=f"{routing.prompt_template}\n\nImplement {task['name']}..."
        )
    )
    
    log_routing_outcome(
        task_id=f"{plan_id}-phase5-{task['name']}",
        routing_config=routing,
        outcome="dispatched"
    )
```

---

## Task Type Mapping

| Old Pattern | New task_type | New cost_priority | Notes |
|-------------|---------------|-------------------|-------|
| Scout (free tier) | `discovery` | `low` | Volume discovery |
| Builder (mechanical, low-cost) | `implementation` | `low` | Type annotations, simple refactors |
| Builder (architectural, balanced) | `implementation` | `balanced` | DI refactors, layer boundaries |
| Probe (balanced) | `code_review` | `balanced` | Investigation needs reasoning |
| Gatekeeper (free tier) | `validation` | `low` | Test/lint/typecheck gates |
| GodMode (high-reasoning) | `code_review` | `premium` | Independent review |

---

## Cost Priority Mapping

| Old Tier | New cost_priority | Typical v2 Model |
|----------|-------------------|------------------|
| Free (0x) | `low` | Claude Haiku 4.5, GPT-5 mini |
| Low-cost (0.33x) | `low` | Claude Haiku 4.5 (winner) |
| Balanced (1x) | `balanced` | Claude Sonnet 4.5, Gemini 2.5 Pro |
| High-reasoning (7.5-15x) | `premium` | GPT-5.4, Claude Opus 4.7 |

---

## Validation

### Test Migration

```python
# Test that router returns expected models
test_cases = [
    {
        "input": {"task_type": "discovery", "cost_priority": "low"},
        "expected_tier": "tier_1_low_cost",  # 0.33x
    },
    {
        "input": {"task_type": "implementation", "cost_priority": "balanced"},
        "expected_tier": "tier_2_balanced",  # 1x or 6x post-June-1
    },
    {
        "input": {"task_type": "code_review", "cost_priority": "premium"},
        "expected_tier": "tier_4_premium",  # 7.5x+
    },
]

for test in test_cases:
    routing = query_model_router(**test["input"])
    assert routing.model_tier == test["expected_tier"]
    print(f"✅ {test['input']} → {routing.model}")
```

### Run Full Cycle

```bash
# Test full cycle with v2
cd /raid5/source/test/prism
python3 scripts/run_mutl3y_cycle.py \
  --plan-id test-v2-migration-g85 \
  --focus-axis typing \
  --target src/prism/scanner_core/ \
  --validate-routing

# Should complete successfully with router-selected models
```

---

## Rollback Plan

If migration fails:

```bash
# 1. Rename v2 back to temp
cd /raid5/source/test/mutl3y_review_workflow_development/skills
mv mutl3y-foreman mutl3y-foreman-v2-temp

# 2. Restore v1
mv mutl3y-foreman-v1-disabled mutl3y-foreman

# 3. Document what failed
echo "Rollback reason: ..." > mutl3y-foreman/ROLLBACK_REASON.md
```

---

## Benefits After Migration

1. ✅ **Separation of concerns**: Workflow ≠ model selection
2. ✅ **Single source of truth**: model-router is routing authority
3. ✅ **Maintainability**: Pricing changes don't affect workflow
4. ✅ **Context efficiency**: 65% smaller skill (1,200 → 420 lines)
5. ✅ **Telemetry-driven**: Routing learns from outcomes
6. ✅ **Instruction compliance**: Automatic gating (e.g., block Opus for Gilfoyle)

---

## Support

### If You Need Help

1. **Read model-router SKILL.md**: `/raid5/source/test/agent_and_skills/.github/skills/model-router/SKILL.md`
2. **Check REDUNDANCY_ANALYSIS.md**: Detailed comparison of v1 vs v2
3. **Review g84 study findings**: Empirical basis for routing decisions
4. **Check telemetry**: `.mutl3y-lessons/model-usage-*.yaml` for actual outcomes

### If Router Unavailable

v2 will fallback to static defaults if model-router skill unavailable:
- Discovery → Claude Haiku 4.5
- Implementation (mechanical) → Claude Haiku 4.5
- Implementation (architectural) → Claude Sonnet 4.5
- Validation → Claude Haiku 4.5

---

**Migration Status**: Complete (2026-05-09)  
**Validation**: Pending full cycle test  
**Rollback Risk**: Low (v1 fully preserved)
