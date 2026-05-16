# Tier 0 (FREE) Model Registry

**Repository Policy**: FREE-tier only. All model dispatches must use Tier 0 (0x cost) models.

## Authorized Tier 0 Models

| Model | Cost (0x) | Best For | Context |
| --- | --- | --- | --- |
| GPT-5 mini | FREE | Discovery, validation, lightweight tasks | Fast, low latency |
| GPT-4.1 | FREE | Code review, analysis | Balanced quality |
| GPT-4o | FREE | Visual verification, screenshots, UI/UX analysis | Multimodal capable |
| Raptor mini (Preview) | FREE | Lightweight reasoning, experiments | Preview status |

## Model Selection by Task Type

### Visual Verification (Playwright, Screenshots)
**→ Use: GPT-4o**
Reason: Multimodal capability for screenshot analysis, color scheme validation, UI consistency checks.

### Discovery & Scanning
**→ Use: GPT-5 mini or Claude Haiku 4.5**
Reason: Fast discovery without vision requirements.

### Code Review & Implementation
**→ Use: GPT-4.1 or GPT-5 mini**
Reason: Code quality analysis, mechanical refactoring.

### Validation & Gates
**→ Use: GPT-5 mini**
Reason: Test/lint/typecheck orchestration, low cost.

---

## Usage Rules

1. **Only use models listed above**
2. **Check cost_multiplier in model dispatch contract**
   - Must be `0x` (exactly 0, FREE)
   - NOT 0.25x, 0.33x, or 1x
3. **Register model used in pre-dispatch gate** before runSubagent call
4. **Log model selection** in phase artifact manifest
5. **No fallback to higher tiers** without explicit policy override

---

## Pre-Dispatch Gate Validation

```yaml
task_type: visual_verification
cost_priority: free  # REQUIRED: must be "free" for this repo
requested_model: "GPT-4o"
requested_tier: "0x"
constraints:
  - cost_multiplier: 0
    description: "Must be FREE tier (0x)"
  - capabilities_required:
      - multimodal
      - screenshot_analysis
artifact_path: "docs/plan/{plan_id}/.mutl3y-gate/pre-dispatch-{task_id}.yaml"
```

---

## Cost Verification

Before dispatch, verify:

```python
if model_data["cost_multiplier"] != 0:
    raise ValueError(f"Model {model_name} is not FREE tier (cost={model_data['cost_multiplier']})")
```
