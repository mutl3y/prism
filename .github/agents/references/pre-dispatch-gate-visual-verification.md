# Pre-Dispatch Gate Checklist (6-Step)

**For**: Visual verification task with Playwright
**Task ID**: visual_verification_colors
**Plan ID**: copilot-usage-find-ft-verification
**Timestamp**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Step 1: Identify Task Type & Cost Priority

- **Task Type**: `visual_verification`
- **Cost Priority**: `free` (Tier 0 only)
- **Instruction Compliance**: Yes (repo requires FREE tier)
- **Focus Area**: Dashboard color consistency verification

**Status**: ✅ PASS

---

## Step 2: Query Model-Router Routing Logic

**From foreman instructions (Model Dispatch Contract)**:

| Cost Tier | Models | Cost Multiplier |
| --- | --- | --- |
| Tier 0 (FREE) | GPT-5 mini, GPT-4.1, GPT-4o, Raptor mini | 0x (0) |
| Tier 1 (low-cost) | Claude Haiku 4.5, GPT-5.4 mini, Gemini 3 Flash | 0.33x |

**This Repository**: FREE-tier-only policy (Tier 0 only)

**Routing Decision**:

- Task: Visual verification with Playwright
- Capability Required: Multimodal (screenshot analysis)
- Tier 0 Model Match: **GPT-4o** ✅

**Status**: ✅ PASS

---

## Step 3: Verify Model Matches Phase Expectations

**Phase Context**: copilot-usage color verification (UI/UX validation)

**Model**: GPT-4o

- **Tier**: 0x (FREE)
- **Cost Multiplier**: 0
- **Capability**: Multimodal (vision + text)
- **Fit for Task**: Excellent (screenshot analysis, color consistency)
- **Repository Policy Compliant**: Yes (Tier 0 only)

**Status**: ✅ PASS

---

## Step 4: Log in Phase Artifact Manifest

**Artifact Path**: `docs/plan/copilot-usage-find-ft-verification/.mutl3y-gate/pre-dispatch-visual-verification.yaml`

```yaml
dispatch_timestamp: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
task_id: "visual_verification_colors"
task_type: "visual_verification"
cost_priority: "free"

model_selection:
  requested_model: "GPT-4o"
  requested_tier: "0x"
  cost_multiplier: 0
  capability: "multimodal"

routing_decision:
  gate_passed: true
  gates_checked:
    - task_type_valid: true
    - tier_0_constraint: true
    - cost_multiplier_zero: true
    - multimodal_capability: true
    - repository_policy_compliant: true

fallback_models: ["GPT-5 mini", "GPT-4.1"]
gate_reason: "Tier 0 model with multimodal capability for screenshot analysis"
```

**Status**: ✅ PASS

---

## Step 5: Set Explicit Model Parameter (Correct Format)

**runSubagent Call Format**:

```python
runSubagent(
    agent="gem-debugger",
    model="GPT-4o",  # ← EXACTLY as registered (not "gpt-4o", not "GPT-4O")
    description="Visual verification of dashboard color consistency",
    prompt="""
    Task: Verify dashboard color consistency with Playwright screenshots

    Requirement: Check that all graph colors match the unified Plotly Paired12 palette

    Steps:
    1. Take screenshot of dashboard at http://127.0.0.1:8050/
    2. Inspect colors of all traces in graphs
    3. Verify color consistency across:
       - Bar charts
       - Line charts
       - Scatter plots
    4. Report any mismatches to Paired12 palette
    5. Confirm date labels display correctly on x-axis
    """
)
```

**Status**: ✅ PASS

---

## Step 6: Verify All Steps Complete Before Dispatch

| Step | Criterion | Status |
| --- | --- | --- |
| 1 | Task type & cost priority identified | ✅ |
| 2 | Model-router routing logic queried | ✅ |
| 3 | Model matches phase expectations | ✅ |
| 4 | Logged in phase artifact | ✅ |
| 5 | Model parameter format correct | ✅ |
| 6 | All steps verified | ✅ |

**Final Gate Status**: 🟢 **ALL CLEAR - PROCEED WITH DISPATCH**

**Cost Validation**:

- Model: GPT-4o
- Cost Multiplier: 0x (FREE)
- Repository Budget: ✅ Compliant
- Policy Enforcement: ✅ Tier 0 only enforced

## DISPATCH AUTHORIZED

Next: Execute `runSubagent` with GPT-4o model parameter
