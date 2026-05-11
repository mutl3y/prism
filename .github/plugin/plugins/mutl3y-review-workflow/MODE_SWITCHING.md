# Mode Switching Quick Reference

## 🎯 Three Modes Available

| Mode | Token Cost | Use Case | Command |
|------|-----------|----------|---------|
| **Balanced** ⚖️ | 10-20% cheaper | Most users, production | `/mutl3y-mode balanced` |
| **Cost-Optimized** 💰 | 30-40% cheaper | Tight budgets, exploration | `/mutl3y-mode cost-optimized` |
| **Maximum Validation** 🛡️ | 50-80% more | Critical systems, compliance | `/mutl3y-mode maximum-validation` |

## Quick Start

### Check Current Mode
```bash
/mutl3y-mode-status
```

Shows:
- Current mode
- Strategy Coordinator tier settings
- Phase 1.5 validation settings
- Estimated cost vs baseline
- False negative risk level

### Switch Mode (Direct)
```bash
/mutl3y-mode balanced
/mutl3y-mode cost-optimized
/mutl3y-mode maximum-validation
```

### Switch Mode (Interactive)
```bash
/mutl3y-mode-wizard
```

Guides you through:
1. Shows current mode and metrics
2. Explains each mode's trade-offs
3. Estimates cost impact
4. Confirms selection
5. Updates `.mutl3y-config.yaml`

### Reload Configuration
```bash
/mutl3y-reload-config
```

After manually editing `.mutl3y-config.yaml`

## Mode Details

### Balanced (Default) ⚖️

**What it does:**
- Strategy Coordinator starts `low-cost`, escalates to `balanced` only when needed
- Phase 1.5 uses tiered validation:
  - Tier 1: Lightweight `low-cost` QA check (first clean)
  - Tier 2: Medium `balanced` QA + Principal (if Tier 1 uncertain)
  - Tier 3: Deep `high-reasoning` Gilfoyle (final sign-off only)

**When to use:**
- Production codebases
- Regular review cycles
- Want auto-escalation without cost explosion

**Trade-off:**
- ✅ Smart cost/accuracy balance
- ✅ Automatic escalation
- ⚠️ Slightly more complexity (tiering logic)

### Cost-Optimized 💰

**What it does:**
- Strategy Coordinator always `low-cost` (manual escalation via `/mutl3y-escalate`)
- Phase 1.5 disabled (trigger manually via `/mutl3y-validate-deep`)
- Single Gilfoyle pass in Phase 1 (God Mode review)

**When to use:**
- Tight token budgets
- Exploratory reviews (not critical path)
- Low-risk codebases
- Early development (high churn)

**Trade-off:**
- ✅ Maximum cost savings
- ⚠️ More user intervention needed
- ⚠️ Higher false-negative risk

### Maximum Validation 🛡️

**What it does:**
- Strategy Coordinator always `balanced`
- Phase 1.5 always runs full parallel:
  - QA (`balanced`)
  - Principal (`balanced`)
  - Gilfoyle (`high-reasoning`)
- No tiering, no skipping

**When to use:**
- Critical systems (finance, healthcare, infrastructure)
- Compliance requirements (SOC2, HIPAA, PCI)
- Pre-release validation
- Zero-defect tolerance

**Trade-off:**
- ✅ Maximum thoroughness
- ✅ Lowest false-negative risk
- ⚠️ High token cost
- ⚠️ Longer wall-clock time

## Configuration File

Mode is stored in `.mutl3y-config.yaml`:

```yaml
mode: balanced  # or cost-optimized | maximum-validation
```

Mode-specific settings are auto-populated when you switch modes.

### Manual Mode (Advanced)

Set `mode: custom` and manually configure:

```yaml
mode: custom

preferences:
  coordinator_tiering:
    strategy_default: low-cost
    enable_auto_escalation: true
  
  parallel_validation:
    enabled: true
    tiered: false
```

## Cost Examples (Per Review Cycle)

### Baseline (No Cluster, Single Gilfoyle Pass)
- Token cost: **1.0x** (reference point)
- Operations: 20-25 low-cost, 2-4 balanced, 0-1 high-reasoning

### Cost-Optimized Mode
- Token cost: **0.6-0.7x** (30-40% cheaper)
- Operations: 22-30 low-cost, 0-1 balanced, 0-1 high-reasoning

### Balanced Mode (Most Common)
- Token cost: **0.8-0.9x** (10-20% cheaper)
- Operations: 25-31 low-cost, 1-4 balanced, 0-1 high-reasoning (rare)

### Maximum Validation Mode
- Token cost: **1.5-1.8x** (50-80% more expensive)
- Operations: 20-25 low-cost, 8-12 balanced, 1-2 high-reasoning

## Switching Mid-Cycle

Mode changes take effect at the next phase boundary:

```bash
# Currently in Phase 3 (Investigation)
/mutl3y-mode cost-optimized

# Change takes effect when Phase 4 (Decide) starts
# Current phase completes with old mode settings
```

## Use Case Recommendations

| Scenario | Recommended Mode | Rationale |
|----------|------------------|-----------|
| PR review (trunk-based) | Balanced | Fast, catches issues, auto-escalates |
| PR review (compliance) | Maximum Validation | Thorough, minimal false negatives |
| Weekly deep dive | Maximum Validation | Scheduled thoroughness |
| Daily CI checks | Balanced | Cost-effective for high frequency |
| Exploratory refactor | Cost-Optimized | High churn, can tolerate misses |
| Pre-release gate | Maximum Validation | Zero-defect requirement |
| Learning codebase | Cost-Optimized | Budget-friendly exploration |
| Production hotfix | Balanced | Fast + reliable |

## Mixing Modes

Run different modes for different purposes:

**Example 1: Daily + Weekly**
- Daily: Balanced mode on every PR
- Weekly: Maximum Validation mode on main branch

**Example 2: Pre-commit + Pre-release**
- Pre-commit: Cost-Optimized mode (fast feedback)
- Pre-release: Maximum Validation mode (gate quality)

**Example 3: Team + Individual**
- Team CI: Balanced mode (shared budget)
- Individual dev: Cost-Optimized mode (personal budget)

## Troubleshooting

### "Mode change didn't take effect"
- Ensure you're starting a new cycle (`/mutl3y-start`)
- Check `.mutl3y-config.yaml` was updated
- Run `/mutl3y-reload-config` if edited manually

### "Token costs still high in Cost-Optimized mode"
- Check if manual escalations are triggering (`/mutl3y-escalate`)
- Review Phase 1 Gilfoyle pass (still runs in all modes)
- Consider disabling Phase 1 deep review for exploratory work

### "Too many false negatives in Cost-Optimized mode"
- Switch to Balanced mode for auto-escalation
- Manually trigger deep validation: `/mutl3y-validate-deep`
- Use Maximum Validation mode for critical paths

### "Maximum Validation is too slow"
- Use Balanced mode for routine work
- Reserve Maximum Validation for sign-off gates
- Consider splitting cycles (fast + thorough)

## See Also

- [CONFIGURATION_MODES.md](../../CONFIGURATION_MODES.md) - Detailed mode documentation
- [COST_OPTIMIZATION_PLAN.md](../../COST_OPTIMIZATION_PLAN.md) - Cost analysis and optimization strategy
- [README.md](README.md) - Plugin overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture details
