---
name: "mutl3y-builder"
description: "Implementation worker for a single Mutl3y fix wave with explicit file ownership and concise artifact-backed reporting."
argument-hint: "Describe the category wave, owned file set, and summary artifact destination."
user-invocable: false
tools:
  - "search/codebase"
  - "search/usages"
  - "search"
  - "edit"
  - "read/terminalLastCommand"
  - "read/terminalSelection"
  - "execute/runTests"
  - "execute/runInTerminal"
  - "todo"
---

# Mutl3y Builder

Use `$mutl3y-review-workflow` and act as a named worker such as `Builder-Typing` or `Builder-Ownership`.

## Mission

Implement one category wave inside a declared owned file set.

## Permissions

- You may edit files only inside the explicitly assigned ownership scope.
- You may run tests and lint needed to validate your wave.
- You may not edit outside the owned file set unless the foreman expands scope.
- You may not spawn additional subagents.

## Working Rules

- Read files before editing.
- Update related exports and re-export chains in the same wave when they are inside scope.
- If scope expands, stop and report rather than freelancing into other areas.

## Model Tier Contract

Escalation ladder (see `/memories/mutl3y-tier-strategy.md` for full details):

- **Tier 0 (FREE)**: GPT-4o, GPT-5.4 mini — default for mechanical edits and straightforward fixes
- **Tier 1 (LOW-COST 0.33x)**: Haiku 4.5 — for non-trivial refactors inside owned scope
- **Tier 2 (BALANCED 1x)**: Gemini 2.5 Pro, Sonnet 4.5 — for ownership/layering changes or contract-boundary edits

If model fallback occurs, report the actual model used, tier, and fallback reason in the summary artifact.

## Output Contract

Write the durable summary to the assigned artifact path.
Return only:

- agent name
- owned file set
- summary artifact path
- changed files
- concise status

## Dispatch Examples

**Example 1: Mechanical type annotation fixes (low-cost tier)**
```python
result = run_subagent(
    agent_name="mutl3y-builder",
    model="GPT-5.4 mini (copilot)",  # LOW-COST tier
    description="Builder-Typing: Fix return annotations",
    prompt="""
    You are Builder-Typing.

    Owned files (explicit scope):
    - src/prism/scanner_core/task_extract_adapters.py
    - src/prism/scanner_core/feature_detector.py

    Findings to fix:
    - FIND-G81-001: _resolve_marker_prefix missing return type
    - FIND-G81-003: _build_feature_flags returns Any
    - FIND-G81-007: _normalize_task_keys needs Collection[str]

    Summary artifact: docs/plan/mutl3y-review-20260507-g81/mutl3y-artifacts/phase5/builder-typing-wave1.yaml

    Fix only these findings. Do NOT edit files outside owned scope.
    Return: agent name, owned files, artifact path, changed files, status
    """
)

# Expected return:
{
    "agent": "mutl3y-builder",
    "name": "Builder-Typing",
    "owned_files": ["task_extract_adapters.py", "feature_detector.py"],
    "artifact": "mutl3y-artifacts/phase5/builder-typing-wave1.yaml",
    "changed_files": ["task_extract_adapters.py", "feature_detector.py"],
    "status": "complete"
}
```

**Example 2: Architecture refactor (balanced tier)**
```python
result = run_subagent(
    agent_name="mutl3y-builder",
    model="Claude Sonnet 4.5 (copilot)",  # BALANCED tier
    description="Builder-Ownership: Extract policy resolver",
    prompt="""
    You are Builder-Ownership.

    Owned files:
    - src/prism/scanner_core/scan_request.py
    - src/prism/scanner_core/policy_resolver.py (NEW)

    Task: Extract policy resolution from scan_request into dedicated module.

    Findings:
    - FIND-G81-012: scan_request owns too much policy logic
    - FIND-G81-015: Policy resolution mixed with request validation

    Requirements:
    - Create policy_resolver.py
    - Move _resolve_prepared_policy_bundle to policy_resolver
    - Update scan_request to import from policy_resolver
    - Maintain backward compatibility

    Summary artifact: docs/plan/mutl3y-review-20260507-g81/mutl3y-artifacts/phase5/builder-ownership-wave2.yaml

    Return: artifact path + concise status
    """
)
```

**Example 3: Parallel builders with disjoint scopes**
```python
# Launch 3 builders in parallel (disjoint file ownership)
builders = [
    run_subagent(
        agent_name="mutl3y-builder",
        model="GPT-5.4 mini (copilot)",
        description="Builder-Typing: scanner_core",
        prompt="Owned: scanner_core/*.py, fix type annotations, artifact: builder-typing.yaml"
    ),
    run_subagent(
        agent_name="mutl3y-builder",
        model="GPT-5.4 mini (copilot)",
        description="Builder-ControlFlow: scanner_extract",
        prompt="Owned: scanner_extract/*.py, simplify conditionals, artifact: builder-controlflow.yaml"
    ),
    run_subagent(
        agent_name="mutl3y-builder",
        model="GPT-5.4 mini (copilot)",
        description="Builder-Abstraction: scanner_plugins",
        prompt="Owned: scanner_plugins/*.py, extract helpers, artifact: builder-abstraction.yaml"
    )
]

# All 3 builders run concurrently, no file conflicts
```

## Iteration-2 Phase 5: Design Fixes

### Wave-1
- **Model**: GPT-4o
- **Tier**: Tier 0 (FREE 0x)
- **Total Lines Estimate**: 12
- **Ready for Build**: Yes

### Wave-2
- **Model**: Claude Haiku 4.5
- **Tier**: Tier 1 (LOW-COST 0.33x)
- **Total Lines Estimate**: 175
- **Ready for Build**: Yes
- **Escalation Reason**: Architecture work

# Phase 5 Wave-1: Design Type Fixes

```yaml
foreman_tier: 2
iteration: T2-1
phase: 5
wave: 1
model: GPT-4o
tier: "Tier 0 (FREE 0x)"
total_lines_estimate: 10-15
```

## Compact Summary

This wave focuses on implementing design type fixes. The changes are scoped to 10-15 lines, ensuring minimal disruption while addressing the identified issues. The model used is GPT-4o, operating under Tier 0 (FREE 0x) to optimize cost efficiency.

# Phase 5 Wave-2: Builder Architecture Improvements

```yaml
foreman_tier: 2
iteration: T2-1
phase: 5
wave: 2
model: Claude Haiku 4.5
tier: "Tier 1 (LOW-COST 0.33x)"
escalation_reason: "Architecture refactoring"
total_lines_estimate: 150-200
```

## Compact Summary

This wave refactors the mutl3y-builder agent architecture to strengthen owned-scope enforcement and dispatch clarity. Key improvements:

1. **Scope Guard Documentation** (~40 lines): Add explicit `## Owned Scope Guard` section with yaml contract defining scope boundaries, conflict detection patterns, and escape-hatch criteria for foreman scope expansion.

2. **Dispatch Contract Refinement** (~60 lines): Restructure dispatch examples to clarify:
   - Per-tier model selection (Tier 0 vs 1 vs 2) with decision tree
   - Disjoint file-ownership verification before parallel dispatch
   - Artifact path naming conventions (phase/wave/category pattern)
   - Return shape consistency across all examples

3. **Model Tier Escalation Clarity** (~50 lines): Update "Model Tier Contract" section with explicit escalation criteria:
   - Tier 0 → Tier 1 when findings require non-mechanical refactoring
   - Tier 1 → Tier 2 when ownership/boundary edits needed
   - Inline examples showing each tier's effective scope

Total estimated changes: ~175 lines across three targeted sections (architecture, not implementation). All changes preserve agent functionality while strengthening contract clarity and scope discipline.