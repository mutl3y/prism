---
name: mutl3y-setup
description: "Configure Mutl3y review workflow paths, settings, and preferences. Use when setting up a new workspace or reconfiguring existing paths."
argument-hint: "Run without arguments for interactive setup, or provide configuration values directly."
---

# Mutl3y Setup

Interactive configuration for the Mutl3y review workflow plugin.

## Slash Commands

### Configuration Commands
- `/mutl3y-config` - Interactive configuration wizard (✅ **NEW: Auto-detects from MCP**)
- `/mutl3y-config-auto` - ✅ **NEW: Auto-configuration from project structure**
- `/mutl3y-paths` - Configure paths only
- `/mutl3y-reviewers` - Select external reviewer agents
- `/mutl3y-status` - Show current configuration
- `/mutl3y-reset` - Reset to defaults

### Mode Management Commands
- `/mutl3y-mode <mode>` - Switch to specified mode (balanced, cost-optimized, maximum-validation)
- `/mutl3y-mode-wizard` - Interactive mode selection with cost/accuracy explanations
- `/mutl3y-mode-status` - Show current mode and estimated cost impact
- `/mutl3y-reload-config` - Reload configuration from .mutl3y-config.yaml

## Configuration Prompts

When invoked, collect these settings interactively:

### Path Configuration

#### ✅ NEW: Auto-Detection from MCP Architecture

```python
# Auto-detect project structure and suggest paths
arch = mcp_codebase_memo_get_architecture(project="prism")

# Auto-populate based on detected structure
auto_config = {
    "paths": {
        "source": arch.get("source_root", "src/"),
        "tests": arch.get("test_root", "src/prism/tests/"),
        "plans": "docs/plan/",
        "lessons": "docs/plan/.mutl3y-lessons/",
        "artifacts": "mutl3y-artifacts/",
        "gate_logs": ".mutl3y-gate/",
        "temp": "tmp/"
    },
    "project_type": arch.get("project_type"),  # "python_monorepo"
    "test_framework": arch.get("test_framework"),  # "pytest"
    "lint_tools": arch.get("lint_tools")  # ["ruff", "black", "mypy"]
}

# User confirms or customizes
# Result: 80% of users skip path questions entirely
```

#### Manual Path Configuration

**Plans Directory**
- Prompt: "Where should plan artifacts be stored?"
- Default: `docs/plan/` (auto-detected)
- Description: Root directory for all review cycle plans (e.g., `docs/plan/mutl3y-review-YYYYMMDD-gN/`)

**Lessons Directory**
- Prompt: "Where should learning memory be stored?"
- Default: `docs/plan/.mutl3y-lessons/` (auto-detected)
- Description: Persistent learning artifacts across cycles

**Artifacts Directory Pattern**
- Prompt: "Artifact subdirectory pattern within plans?"
- Default: `mutl3y-artifacts/` (auto-detected)
- Description: Where scouts, builders, and gatekeepers write outputs (e.g., `docs/plan/<plan-id>/mutl3y-artifacts/`)

**Gate Logs Directory**
- Prompt: "Where should validation gate logs be stored?"
- Default: `.mutl3y-gate/` (auto-detected)
- Description: Temporary gate execution logs and validation outputs

**Temporary Files Directory**
- Prompt: "Where should temporary working files be stored?"
- Default: `docs/plan/<plan-id>/tmp/` (auto-detected)
- Description: Scratch space for transient artifacts

### External Reviewer Configuration

**Deep Review Agent**
- Prompt: "Which agent should perform unconstrained deep reviews?"
- Suggested Options:
  - `Gilfoyle Code Review Mode` (from awesome-copilot)
  - `gem-reviewer` (from awesome-copilot)
  - `Principal software engineer` (from awesome-copilot)
  - Custom agent name
- Default: `Gilfoyle Code Review Mode`
- Description: Agent for independent, whole-target reviews without findings hints

**Research Agent**
- Prompt: "Which agent should perform codebase research?"
- Suggested Options:
  - `gem-researcher` (from awesome-copilot)
  - `Explore` (built-in)
  - Custom agent name
- Default: `gem-researcher`
- Description: Agent for architecture discovery and pattern analysis

**QA Agent** (Optional)
- Prompt: "Which agent should perform QA validation?"
- Suggested Options:
  - `QA` (from awesome-copilot)
  - Custom agent name
  - None
- Default: None
- Description: Dedicated QA specialist for test validation

### Workflow Preferences

**Default Review Depth**
- Prompt: "Default review thoroughness?"
- Options: `light`, `medium`, `thorough`, `deep`
- Default: `thorough`
- Description: Initial review depth for new cycles

**Parallel Execution**
- Prompt: "Enable parallel agent execution?"
- Options: `yes`, `no`
- Default: `yes`
- Description: Run scouts/builders in parallel batches

**Auto-Escalation**
- Prompt: "Auto-escalate stalled agents to higher-tier models?"
- Options: `yes`, `no`
- Default: `yes`
- Description: Automatically retry with better models on failure

**Model Tier Defaults**
- Prompt: "Default model tiers?"
- Options:
  - Scouts: `low-cost`, `balanced`, `high-reasoning`
  - Builders: `low-cost`, `balanced`, `high-reasoning`
  - Gatekeepers: `low-cost`, `balanced`, `high-reasoning`
- Defaults: scouts=`low-cost`, builders=`low-cost`, gatekeepers=`low-cost`

### Mode Configuration

**Workflow Mode**
- Prompt: "Select workflow mode (cost/accuracy trade-off):"
- Options:
  1. **Balanced** ⚖️ (Recommended)
     - Smart cost/accuracy trade-off
     - Auto-escalates when needed
     - Token cost: 10-20% cheaper than baseline
     - Best for: Most users, production workflows
  2. **Cost-Optimized** 💰
     - Maximum free tier usage
     - Manual escalation only
     - Token cost: 30-40% cheaper than baseline
     - Best for: Tight budgets, low-risk code
  3. **Maximum Validation** 🛡️
     - Thoroughness over cost
     - Always full validation
     - Token cost: 50-80% more than baseline
     - Best for: Critical systems, compliance
- Default: `balanced`
- Description: Controls Strategy Coordinator tiering and Phase 1.5 validation behavior

## Mode Switching

### `/mutl3y-mode <mode>`

**Usage**: `/mutl3y-mode balanced` | `/mutl3y-mode cost-optimized` | `/mutl3y-mode maximum-validation`

**Behavior**:
1. Validates mode name (must be `balanced`, `cost-optimized`, or `maximum-validation`)
2. Shows cost impact comparison:
   ```
   Current mode: balanced
   New mode: cost-optimized

   Cost impact: -30% tokens per cycle
   Risk impact: +20% false negative rate

   Continue? [y/N]:
   ```
3. Updates `.mutl3y-config.yaml` with new mode settings
4. Confirms change and notes when it takes effect (next cycle start)

### `/mutl3y-mode-wizard`

**Behavior**: Interactive mode selection with detailed explanations

1. Show current mode and cost/performance metrics
2. Present 3 mode options with:
   - Cost estimate per cycle
   - False-negative risk level
   - Recommended use cases
   - Key trade-offs
3. User selects mode (1-3)
4. Show detailed cost breakdown:
   - Strategy Coordinator costs
   - Phase 1.5 validation costs
   - Worker agent costs
   - Total estimated cost vs baseline
5. Confirm selection
6. Write to config and show reload instructions

### `/mutl3y-mode-status`

**Behavior**: Show current configuration and cost metrics

**Output**:
```
Current Mode: balanced ⚖️

Strategy Coordinator:
  Default tier: low-cost
  Escalate to: balanced
  Auto-escalation: enabled

Phase 1.5 Validation:
  Enabled: yes
  Tiered: yes
  Tier 1 (lightweight): low-cost QA
  Tier 2 (medium): balanced QA + Principal
  Tier 3 (deep): balanced Gilfoyle (escalate to high-reasoning if needed)

Estimated Cost: 0.7-0.85x baseline
False Negative Risk: Low

Last updated: 2026-05-06 14:23:45
Config file: .mutl3y-config.yaml
```

## Configuration Storage

Write configuration to `.mutl3y-config.yaml` in the workspace root.

### Complete Configuration Example

```yaml
version: 1.0.0
mode: balanced  # balanced | cost-optimized | maximum-validation | custom

paths:
  plans: docs/plan/
  lessons: docs/plan/.mutl3y-lessons/
  artifacts: mutl3y-artifacts/
  gate_logs: .mutl3y-gate/
  temp: tmp/

external_agents:
  deep_review: Gilfoyle Code Review God Mode
  research: gem-researcher
  qa: QA  # for Phase 1.5 validation
  lightweight_qa: QA  # low-cost variant for Tier 1
  principal: Principal software engineer  # for Phase 1.5 Tier 2

preferences:
  default_depth: thorough
  parallel_execution: true
  auto_escalation: true

  # Mode-specific settings (auto-populated based on mode)
  coordinator_tiering:
    strategy_default: low-cost
    strategy_escalate: balanced
    enable_auto_escalation: true

  parallel_validation:
    enabled: true
    tiered: true  # true for balanced mode
    tier1_on_first_clean: true
    tier2_on_second_clean: true
    tier3_before_signoff: true
    bypass_on_findings: true
    manual_trigger_only: false

  model_tiers:
    scouts: low-cost
    builders: low-cost
    gatekeepers: low-cost
```

## Mode Configurations

### Balanced Mode (Default)

```yaml
mode: balanced

preferences:
  coordinator_tiering:
    strategy_default: low-cost
    strategy_escalate: balanced
    enable_auto_escalation: true

  parallel_validation:
    enabled: true
    tiered: true
    tier1_on_first_clean: true
    tier2_on_second_clean: true
    tier3_before_signoff: true
```

### Configuration Examples by Use Case

**Example 1: New workspace setup**
```bash
# User runs: /mutl3y-config

# Interactive prompts:
Where should plan artifacts be stored? [docs/plan/]: docs/reviews/
Where should learning memory be stored? [docs/plan/.mutl3y-lessons/]: .mutl3y/lessons/
Which agent for deep reviews? [Gilfoyle Code Review Mode]: Gilfoyle Code Review Mode
Which agent for research? [gem-researcher]: gem-researcher
Default review depth? [thorough]: thorough
Enable parallel execution? [yes]: yes

# Result: .mutl3y-config.yaml written with custom paths
```

**Example 2: Auto-configuration with MCP (NEW)**
```bash
# User runs: /mutl3y-config-auto

# Output:
Querying project architecture...

Auto-detected configuration:
- Project: Python monorepo (prism)
- Test framework: pytest
- Lint tools: ruff, black, mypy
- Source: src/prism/
- Tests: src/prism/tests/
- Plans: docs/plan/
- Artifacts: mutl3y-artifacts/

Use detected paths? [Y/n]: Y

Configuration written to .mutl3y-config.yaml

⏱️ TIME SAVED: 5 minutes (vs 15-20 minute manual setup)
```

**Example 3: Switch to cost-optimized mode**
```bash
# User runs: /mutl3y-mode cost-optimized

# Output:
Current mode: balanced
New mode: cost-optimized

Cost impact: -30% tokens per cycle
Risk impact: +20% false negative rate

Changes:
  - Strategy Coordinator: low-cost only (no auto-escalation)
  - Phase 1.5 validation: disabled
  - Scouts: GPT-4o (FREE tier)
  - Builders: GPT-5.4 mini (LOW-COST tier)

Continue? [y/N]: y

Configuration updated. Changes take effect on next /mutl3y-start.
```

**Example 3: Mode wizard with detailed explanations**
```bash
# User runs: /mutl3y-mode-wizard

# Interactive wizard:
Current mode: balanced (0.8-0.9x baseline cost)

Select workflow mode:

1. Balanced ⚖️ (Recommended)
   • Smart cost/accuracy trade-off
   • Auto-escalates when needed
   • Strategy: low-cost → balanced
   • Scouts: GPT-4o, GPT-5 mini (FREE)
   • Builders: GPT-5.4 mini (LOW-COST)
   • Cost: 10-20% cheaper than baseline
   • Best for: Most users, production workflows

2. Cost-Optimized 💰
   • Maximum free tier usage
   • Manual escalation only
   • Strategy: low-cost only
   • Scouts: GPT-4o (FREE)
   • Builders: GPT-5.4 mini (LOW-COST)
   • Cost: 30-40% cheaper than baseline
   • Risk: +20% false negatives
   • Best for: Tight budgets, low-risk code

3. Maximum Validation 🛡️
   • Thoroughness over cost
   • Always full validation
   • Strategy: balanced → high-reasoning
   • Scouts: Claude Sonnet 4.5
   • Builders: Claude Sonnet 4.5
   • Cost: 50-80% more than baseline
   • Best for: Critical systems, compliance

Choice [1-3]: 2

Detailed cost breakdown (Cost-Optimized):
  Strategy Coordinator: 50 tokens/decision × 15 decisions = 750 tokens
  Scouts (4 × FREE): 2000 tokens/scout × 4 = 8000 tokens
  Builders (6 × LOW-COST): 3000 tokens/build × 6 = 18000 tokens
  Gatekeepers (FREE): 1000 tokens
  Total: ~27,750 tokens (vs 35,000 baseline = -21%)

Confirm switch to cost-optimized? [y/N]: y

Configuration updated.
```

**Example 4: Check current mode status**
```bash
# User runs: /mutl3y-mode-status

# Output:
Current Mode: balanced ⚖️

Strategy Coordinator:
  Default tier: low-cost (GPT-5.4 mini, GPT-4o, Haiku 4.5)
  Escalate to: balanced (Claude Sonnet 4.5, GPT-5.4)
  Auto-escalation: enabled
  Escalation trigger: 2 failures on one finding

Phase 1.5 Validation:
  Enabled: yes
  Tiered: yes
  Tier 1 (lightweight): low-cost QA
  Tier 2 (medium): balanced QA + Principal
  Tier 3 (deep): balanced Gilfoyle (escalate to high-reasoning only if findings are incomplete)

Worker Model Tiers:
  Scouts: low-cost (GPT-4o, GPT-5 mini, Raptor mini)
  Builders: low-cost → balanced (on architecture refactors)
  Gatekeepers: low-cost (GPT-4o)
  Probes: low-cost → balanced (on ambiguity)
  Gilfoyle: balanced → high-reasoning (only if balanced findings shallow/incomplete)

Estimated Cost: 0.7-0.85x baseline
False Negative Risk: Low

Last updated: 2026-05-07 10:45:32
Config file: .mutl3y-config.yaml
```

### Cost-Optimized Mode

```yaml
mode: cost-optimized

preferences:
  coordinator_tiering:
    strategy_default: low-cost
    strategy_escalate: balanced
    enable_auto_escalation: false  # manual only

  parallel_validation:
    enabled: false
    manual_trigger_only: true
```

### Maximum Validation Mode

```yaml
mode: maximum-validation

preferences:
  coordinator_tiering:
    strategy_default: balanced
    strategy_escalate: high-reasoning
    enable_auto_escalation: true

  parallel_validation:
    enabled: true
    tiered: false  # always full validation
    always_all_three: true
  
  gilfoyle_escalation:
    default_tier: balanced  # GPT-4o, Claude Sonnet 4.5, Gemini 2.5 Pro
    escalate_to: high-reasoning  # only if balanced findings incomplete
```

## Validation

After collecting configuration:
1. Verify paths are valid (create if missing, with confirmation)
2. Check external agents are available (warn if not found)
3. Write `.mutl3y-config.yaml` to workspace root
4. Confirm setup complete

## Reconfiguration

On `/mutl3y-config`, load existing `.mutl3y-config.yaml` and present current values as defaults, allowing selective updates.

## Reset

On `/mutl3y-reset`, restore factory defaults and optionally delete existing configuration file.
