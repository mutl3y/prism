# Mutl3y Review Workflow Plugin

Team-based, file-backed code review and fix cycle with three-node cluster architecture for resilient, context-efficient reviews.

## Overview

The Mutl3y review workflow is designed to handle complex Python codebases with a distributed agent architecture that prevents context overload and enables parallel execution. It uses a three-node cluster swarm pattern with specialized coordinators and an independent workflow monitor.

## Architecture

```text
┌─────────────────────┐
│  Workflow Monitor   │ ← Audits flow, never edits
└──────────┬──────────┘
           │
    ┌──────┼──────┐
    │      │      │
┌───▼──┐ ┌─▼──┐ ┌─▼───┐
│Strategy│Tactical│Execution│ ← Three-node cluster
└───┬──┘ └──┬─┘ └──┬──┘
    │      │     │
    └──────┼─────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐   ┌────▼────┐
│Scouts │   │Builders │
│Probes │   │Gatekeepers│
└───────┘   └─────────┘
```

### Coordinators

- **Strategy Coordinator**: Phase selection, cycle planning, terminal decisions
- **Tactical Coordinator**: Wave decomposition, agent dispatch, parallel execution
- **Execution Coordinator**: Single-agent task execution, artifact validation
- **Workflow Monitor**: Flow audit, barrier checks, drift detection (read-only)

### Worker Agents

- **Scouts**: Read-only discovery (typing, ownership, control flow, graph)
- **Builders**: Implementation workers with explicit file ownership
- **Gatekeepers**: Validation specialists (gates, logs, failure slicing)
- **Probes**: Focused investigators for ambiguous findings
- **Archivists**: Bookkeeping for closure and ledger updates

## Getting Started

### 1. Install the Plugin

```bash
gh copilot plugins install /path/to/mutl3y_review_workflow_development
```

Or from a remote repo:

```bash
gh copilot plugins install owner/mutl3y-review-workflow
```

### 2. Run Setup

On first use, run the interactive configuration wizard:

```bash
/mutl3y-config
```

This will prompt for:

- **Paths**: Where to store plans, lessons, artifacts, gate logs
- **External Reviewers**: Which agents to use for deep reviews (suggestions from awesome-copilot)
- **Preferences**: Review depth, parallel execution, auto-escalation, model tiers

Configuration is saved to `.mutl3y-config.yaml` in your workspace root.

### 3. Start a Review Cycle

```bash
/mutl3y-start
```

Or invoke the cluster foreman skill:

```bash
@workspace Use the mutl3y-cluster-foreman skill to review src/mypackage/
```

## Workflow Modes

The plugin supports three modes that balance token costs against validation thoroughness:

### 🎯 Balanced (Default)

**Philosophy**: Start cheap, escalate when needed

**Strategy**: `low-cost` → `balanced` on demand  
**Phase 1.5**: Tiered validation (lightweight → medium → deep)

**Token cost**: 10-20% cheaper than baseline  
**Best for**: Most users, production workflows

**Quick start**:
```bash
/mutl3y-mode balanced
```

### 💰 Cost-Optimized

**Philosophy**: Maximum free tier usage

**Strategy**: Always `low-cost` (manual escalation)  
**Phase 1.5**: Disabled (manual trigger only)

**Token cost**: 30-40% cheaper than baseline  
**Best for**: Tight budgets, exploratory reviews, low-risk code

**Quick start**:
```bash
/mutl3y-mode cost-optimized
```

### 🛡️ Maximum Validation

**Philosophy**: Thoroughness over cost

**Strategy**: Always `balanced`  
**Phase 1.5**: Always full parallel validation (QA + Principal + Gilfoyle)

**Token cost**: 50-80% more than baseline  
**Best for**: Critical systems, compliance, pre-release validation

**Quick start**:
```bash
/mutl3y-mode maximum-validation
```

### Choosing a Mode

**Not sure?** Run the interactive wizard:
```bash
/mutl3y-mode-wizard
```

**Check current mode**:
```bash
/mutl3y-mode-status
```

See [CONFIGURATION_MODES.md](../../CONFIGURATION_MODES.md) for detailed mode documentation.

## Slash Commands

### Configuration

- `/mutl3y-config` - Interactive configuration wizard
- `/mutl3y-paths` - Configure paths only
- `/mutl3y-reviewers` - Select external reviewer agents
- `/mutl3y-status` - Show current configuration and cluster state
- `/mutl3y-reset` - Reset to defaults

### Mode Management

- `/mutl3y-mode <mode>` - Switch to specified mode (balanced, cost-optimized, maximum-validation)
- `/mutl3y-mode-wizard` - Interactive mode selection with cost/accuracy explanations
- `/mutl3y-mode-status` - Show current mode and estimated cost impact
- `/mutl3y-reload-config` - Reload configuration from .mutl3y-config.yaml

### Workflow

- `/mutl3y-start` - Start new review cycle (Strategy Coordinator entry)
- `/mutl3y-continue` - Continue existing cycle from last checkpoint
- `/mutl3y-audit` - Manual Workflow Monitor audit
- `/mutl3y-escalate` - Force escalation to Strategy Coordinator

## Skills

### mutl3y-setup

Interactive configuration and reconfiguration. Collects paths, external agent preferences, and workflow settings.

### mutl3y-foreman

The original thin foreman for single-coordinator workflows. Delegates to named subagents, keeps artifacts on disk, and maintains compact context.

### mutl3y-cluster-foreman

Enhanced three-node cluster architecture with:

- Distributed coordination (Strategy/Tactical/Execution)
- Workflow Monitor for barrier checks and drift detection
- Consensus-based critical decisions
- Automatic failover and model tier escalation
- Parallel wave execution with disjoint file ownership

## Configuration File

`.mutl3y-config.yaml` example:

```yaml
version: 1.0.0
mode: balanced  # balanced | cost-optimized | maximum-validation

paths:
  plans: docs/plan/
  lessons: docs/plan/.mutl3y-lessons/
  artifacts: mutl3y-artifacts/
  gate_logs: .mutl3y-gate/
  temp: tmp/

external_agents:
  deep_review: Gilfoyle Code Review God Mode
  research: gem-researcher
  qa: QA
  lightweight_qa: QA
  principal: Principal software engineer

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
    tiered: true
    tier1_on_first_clean: true
    tier2_on_second_clean: true
    tier3_before_signoff: true
  
  model_tiers:
    scouts: low-cost
    builders: low-cost
    gatekeepers: low-cost
```

## External Agent Recommendations

For deep reviews, consider these agents from awesome-copilot:

- **gem-reviewer**: Meticulous QA specialist with edge-case analysis
- **gem-researcher**: Codebase exploration and architecture discovery
- **Gilfoyle Code Review God Mode**: Sardonic, brutally honest code review
- **Principal software engineer**: Principal-level guidance and technical leadership

Configure via `/mutl3y-reviewers` or edit `.mutl3y-config.yaml`.

## Workflow Phases

0. **Discovery**: Broad read-only sweep for issues
1. **Grading**: Prioritize findings by severity
2. **Persist Plan**: Write plan.yaml with tasks and waves
3. **Investigation**: Micro-swarms for ambiguous findings
4. **Decide**: Accept, defer, or reject findings
5. **Implementation**: Parallel builder waves with disjoint file ownership
6. **Validation**: Gates, regression checks, lint/test
7. **Close and Learn**: Update ledgers, promote lessons, closure control

## Resilience Features

1. **Automatic Checkpointing**: Execution Coordinator writes trace entries after every agent dispatch
2. **Resumable**: Strategy Coordinator can resume from `execution-trace.yaml`
3. **Drift Repair**: Workflow Monitor detects and repairs plan/trace mismatches
4. **Model Tier Escalation**: Execution Coordinator auto-escalates on stalls
5. **Parallel Execution**: Tactical Coordinator launches disjoint waves in parallel
6. **Consensus Decisions**: Strategy + Monitor consensus prevents premature closure

## Self-Improvement

Mutl3y learns from each cycle:

- **Memory Store**: `docs/plan/.mutl3y-lessons/` (persistent across cycles)
- **Model Usage Ledger**: Tracks which models/routes succeeded/failed
- **Learning Candidates**: Written during cycles, promoted in Phase 7
- **God Mode Calibration**: Missed High/Critical findings update scout coverage

## Context Discipline

- **Artifact-First Output**: Discovery, probes, gate logs written to disk
- **Summary-Only Chat Returns**: Subagents return compact status lines
- **No Inline Large Payloads**: Full YAML findings, test logs stay in artifacts
- **Repo-Only Temp Paths**: All scratch files under `docs/plan/<plan-id>/tmp/`

## Development

This plugin is in active development. Contributions welcome!

### Structure

```text
mutl3y_review_workflow_development/
├── agents/              # Worker agents and monitor
├── skills/              # Foreman variants and setup
├── plugins/             # Plugin metadata
└── eng/                 # Build and validation scripts
```

### Testing Locally

```bash
cd /path/to/mutl3y_review_workflow_development
npm run build
npm run plugin:validate
```

## License

MIT

## Credits

Built on patterns from:

- Multi-agent architectures (LangGraph research)
- Context engineering best practices
- Mutl3y and Gilfoyle review workflows (Prism project)
