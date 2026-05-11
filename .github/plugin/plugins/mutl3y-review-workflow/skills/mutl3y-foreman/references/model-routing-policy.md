# Model Routing And Cost Policy

> **Last Updated:** May 8, 2026 (Current request-based billing multipliers, pre-June 1 transition)
> **Source:** [GitHub Copilot Model Multipliers Documentation](https://docs.github.com/en/copilot/reference/copilot-billing/model-multipliers-for-annual-plans)
>
> **How to refresh this file:**
>
> 1. Visit the source URL above to check for updated multipliers
> 2. Copy and use this prompt:
>
> ```
> Update /raid5/source/test/mutl3y_review_workflow_development/skills/mutl3y-foreman/references/model-routing-policy.md with the latest model multipliers from https://docs.github.com/en/copilot/reference/copilot-billing/model-multipliers-for-annual-plans
> ```
>
> 3. Update the "Last Updated" date above

Model routing is mandatory policy, not preference: each dispatch must select a tier from the active ladder, and each fallback must be recorded.

## Current Multipliers (May 8, 2026 — Pre-June 1 Transition)

**CURRENT STATUS**: This file uses the active request-based billing multipliers as of May 8, 2026.

On June 1, 2026, GitHub will change Copilot billing from request-based to usage-based. For annual plans staying on request-based billing, multipliers will change significantly:

**Current (May 8) multipliers remain stable:**
- **Claude models**: Haiku 4.5 (0.33x), Sonnet 4.5 (1x), Opus 4.7 (15x)
- **GPT models**: GPT-4o (0x), GPT-4.1 (0x), GPT-5.4 (1x), GPT-5.4 mini (0.33x), GPT-5 mini (0.33x)
- **Gemini models**: Flash (0.33x), 2.5 Pro (1x), 3.1 Pro (1x)

**Scheduled changes (effective June 1, 2026):**
- Former "free" GPT models will change to 0.33x or 1x
- Former "balanced" models (Sonnet 4.5, GPT-5.4) will become 6x
- GPT-5.4 mini will jump from 0.33x to 6x

**Note**: If running after June 1, 2026, refresh this file for updated multipliers.

The multipliers below reflect **current (May 8, 2026) request-based pricing** for annual plans.

### Quick Reference: New Routing Strategy

**Key Changes Post-June 1:**
- Former "free" models (GPT-4o, GPT-5 mini, GPT-4.1) → now 0.33x or 1x
- Former "balanced" models (Claude Sonnet 4.5, GPT-5.4) → now **6x (!)**
- **GPT-5.4 mini shocking jump**: 0.33x → 6x (18x increase!)
- Only two 1x models remain: GPT-4.1, Gemini 2.5 Pro

**New Tier Priorities:**
1. **0.33x**: Primary tier for scouts/graders (Claude Haiku 4.5, GPT-5 mini, Gemini 3 Flash)
2. **1x**: Critical builder tier (GPT-4.1, Gemini 2.5 Pro) — use aggressively before escalating
3. **3x**: Mid-tier escalation (GPT-5.2 family) — use sparingly
4. **6x**: Reserve for architecture risk (Claude Sonnet 4.5, GPT-5.4) — was 1x!
5. **7.5x+**: GodMode only

**Builder Strategy:** Start at 1x (Gemini 2.5 Pro), avoid 6x unless high-stakes architecture or repeated 1x/3x failures.

### Capability And Cost Snapshot

Use the current runtime catalog, not stale assumptions. The following options were observed in the active environment and must drive routing decisions:

| Model | Context window | Tools | Vision | Post-6/1 cost | Notes |
|---|---:|---|---|---|---|
| `GPT-4o` | `68K` | yes | yes | `0.33x` | lowest context; adequate for scouts/graders |
| `GPT-4.1` | `128K` | yes | yes | `1x` | now true 1x cost; viable for bounded builders |
| `Claude Haiku 4.5` | `160K` | yes | yes | `0.33x` | **critical low-cost route** — vision-capable |
| `Claude Sonnet 4.5` | `160K` | yes | yes | `6x` | **6x increase!** — reserve for architecture work |
| `Gemini 2.5 Pro` | `173K` | yes | yes | `1x` | **stable at 1x** — key balanced option |
| `Gemini 3 Flash` | `173K` | yes | yes | `0.33x` | **stable at 0.33x** — preview low-cost |
| `Gemini 3.1 Pro` | `173K` | yes | yes | `6x` | **6x increase** — expensive for preview |
| `Grok Code Fast 1` | `173K` | yes | no | `0.33x` | now 0.33x; tools-only |
| `GPT-5 mini` | `192K` | yes | yes | `0.33x` | **key 0.33x route** — good context for low-cost |
| `GPT-5.2` | `192K` | yes | yes | `3x` | mid-tier, not cheap anymore |
| `GPT-5.2-Codex` | `400K` | yes | yes | `3x` | mid-tier code route |
| `GPT-5.3-Codex` | `400K` | yes | yes | `6x` | **6x increase** — expensive code route |
| `GPT-5.4` | `400K` | yes | yes | `6x` | **6x increase!** — was balanced, now high-tier |
| `GPT-5.4 mini` | `400K` | yes | yes | `6x` | **massive jump 0.33x→6x!** — avoid for scouts |
| `GPT-5.5` | `400K` | yes | yes | `7.5x` | premium escalation route |
| `Raptor mini` | `264K` | yes | yes | `0.33x` | preview 0.33x, large context |
| `Claude Opus 4.7` | `192K` | yes | yes | `27x` | **27x (was 15x)** — extreme reserve only |

Models shown as unavailable, degraded, or warning-marked in the runtime picker are not primary choices even if listed above.
Treat `0x` as lowest cost, but not as automatic first choice if the route is unstable, preview-only, or materially weaker for the task type.

Context-window rule:

- Prefer `400K` routes for artifact-heavy prompts, long findings bundles, or builder tasks with large owned-file context.
- Avoid `68K` and `128K` routes when the worker must hold long plan artifacts, multiple logs, or wide cross-file evidence in one prompt.
- Large context does not override tier or health rules; it is a tie-breaker after capability, route health, and cost tier.

### Tier mapping (POST-JUNE 1, 2026)

**CRITICAL: The 1x tier is now the only budget-friendly option for architecture work.**

- `low-cost` (0.33x): GPT-4o, GPT-5 mini, Raptor mini, Grok Code Fast 1, Claude Haiku 4.5, Gemini 3 Flash — **primary tier** for scouts, graders, narrow reads
- `budget-mid` (1x): GPT-4.1, Gemini 2.5 Pro — **only affordable architecture-capable tier**; critical for builders
- `mid` (3x): GPT-5.2, GPT-5.2-Codex, GPT-5.1 family — escalation tier for code-heavy work
- `high` (6x): Claude Sonnet 4.5, GPT-5.4, GPT-5.4 mini, GPT-5.3-Codex, Gemini 3.1 Pro — **reserve for high-stakes architecture or repeated 1x failures**
- `very-high` (7.5x-9x): GPT-5.5 (7.5x promo) — rare escalation
- `premium` (15x-27x): Claude Opus 4.5 (15x), Claude Opus 4.7 (27x) — **GodMode/emergency only**

### Routing ladders (POST-JUNE 1, 2026)

**CRITICAL STRATEGY CHANGE**: The 6x increase on former "balanced" models requires aggressive 0.33x use and careful 1x/3x tier selection before any 6x escalation.

Choose from these ladders in order. Do not stick to one vendor if the route is unhealthy.

#### `low-cost` ladder (0.33x — PRIMARY TIER)

**Use for**: Scouts, graders, finding extraction, narrow reads, bookkeeping

1. `Claude Haiku 4.5` (`0.33x`) — **best 0.33x option** for vision-capable tasks, 160K context
2. `GPT-5 mini` (`0.33x`) — strong general route, 192K context, good for scouts
3. `Gemini 3 Flash` (`0.33x`) — preview but stable, 173K context
4. `GPT-4o` (`0.33x`) — adequate for scouts despite 68K limit
5. `Raptor mini` (`0.33x`) — preview, 264K context for large-prompt scouts
6. `Grok Code Fast 1` (`0.33x`) — tools-only, skip if vision needed
7. If all 0.33x unhealthy → escalate to `budget-mid` (1x)

**Updated 2026-05-07 (post-multiplier analysis):**
- 0.33x is now the **workhorse tier** for discovery and validation phases
- Do NOT use 0.33x for architecture-sensitive builders; escalate to 1x minimum
- `Claude Haiku 4.5` and `GPT-5 mini` are the primary 0.33x routes for focused work

#### `budget-mid` ladder (1x — CRITICAL BUILDER TIER)

**Use for**: Architecture-capable builders, DI/typing work, ownership boundaries

**WARNING**: This is now the ONLY affordable architecture tier. Former "balanced" models jumped to 6x.

1. `Gemini 2.5 Pro` (`1x`) — **primary 1x builder**, architecture-aware, 173K context
2. `GPT-4.1` (`1x`) — secondary builder, proven for narrow slices, 128K context
3. `Claude Haiku 4.5` (`0.33x`) — fallback if 1x pool unhealthy AND task can tolerate reduced capability
4. If both 1x routes fail → consider `mid` (3x) escalation

**Updated 2026-05-07 (post-multiplier analysis):**
- `Gemini 2.5 Pro` is the **anchor model** for builders under new pricing
- `GPT-4.1` is viable for bounded slices but needs tighter prompts
- Do NOT escalate to 6x (Claude Sonnet 4.5, GPT-5.4) unless architecture risk is high

#### `mid` ladder (3x — ESCALATION TIER)

**Use for**: Code-heavy refactors when 1x fails, mid-complexity architecture

1. `GPT-5.2-Codex` (`3x`) — 400K context, code-focused
2. `GPT-5.2` (`3x`) — 192K context, general escalation
3. `GPT-5.1-Codex` (`3x`) — alternative code route
4. If 3x fails → escalate to `high` (6x) only for high-stakes work

#### `high` ladder (6x — RESERVE ONLY)

**Use for**: High-stakes architecture, repeated 1x/3x failures, critical DI/boundary work

**WARNING**: 6x models were 1x before June 1. Use sparingly.

1. `Claude Sonnet 4.5` (`6x`) — architecture/synthesis, 160K context
2. `GPT-5.4` (`6x`) — strong alternative, 400K context
3. `Gemini 3.1 Pro` (`6x`) — preview, 173K context
4. `GPT-5.3-Codex` (`6x`) — code-heavy, 400K context
5. If 6x fails → escalate to `very-high` (7.5x+) or GodMode only

**AVOID**: `GPT-5.4 mini` (`6x`) — jumped from 0.33x to 6x; no longer viable for scouts/graders

#### `very-high` and `premium` ladders (7.5x–27x — GODMODE ONLY)

**Use for**: Independent GodMode pass, emergency escalation after multiple 6x failures

1. `GPT-5.5` (`7.5x`) — promotional rate, rare escalation
2. `Claude Opus 4.7` (`27x`) — **27x (was 15x before June 1)** — absolute last resort

**Updated 2026-05-07**: Do not escalate to 7.5x+ until at least two documented 6x failures on the same finding OR for scheduled independent GodMode review.

Dispatch rules:

- Always set subagent `model` explicitly in `runSubagent`.
- Model label must match runtime availability.
- Filter candidates by required capabilities first: tools required, vision required, code-edit heavy, or architecture synthesis.
- Prefer stable non-preview models over preview models at equal cost unless the preview option is the only compatible low-cost route.
- If unavailable, fail fast or apply fallback policy and log it in the phase artifact.
- If you do not set `model` explicitly, subagents may inherit the currently selected chat model.

### Reliability And Fallback Policy

Subagent invocation errors are routing failures first, not task failures.

Count the following as model-route failures:

- `error invoking subagent cancelled`
- provider timeout or invocation timeout before useful output
- tool-session startup failure before useful output
- empty or truncated response with no artifact and no edit evidence

After a cancellation or timeout on a writing worker, inspect owned files and expected artifact state before choosing recover vs re-dispatch.

Do not keep retrying the same failing route.

Per-task failure budget:

1. First route failure on a task: retry once on the next compatible model in the same ladder.
2. Second route failure on the same task: mark the original model unhealthy for the rest of the cycle and continue down the ladder.
3. Third cumulative route failure across the same phase: stop using that whole cost band for the remainder of the phase and step up one tier.

Per-cycle health rule:

- Any model that fails twice in the same cycle is quarantined for the remainder of that cycle (do not dispatch to it again in that cycle).
- If two different models fail within the same cost band during one phase, treat that band as degraded for the phase and promote remaining phase work to the next tier.
- If a `balanced` route fails twice on the same architecture-sensitive finding, promote that finding only to `high-reasoning`.
- Apply this rule uniformly to all models, not only one vendor.

Fallback selection rule (POST-JUNE 1, 2026):

1. Stay in the current tier if a compatible healthy alternative exists.
2. Prefer the lowest-cost healthy alternative with the same required capabilities.
3. Prefer non-preview over preview at the same multiplier.
4. **NEW**: The 1x tier (GPT-4.1, Gemini 2.5 Pro) is now the minimum for architecture work; do NOT escalate to 6x (Claude Sonnet 4.5, GPT-5.4) unless facing high-stakes architecture or repeated 1x/3x failures.
5. Only jump to 7.5x+ models after at least two failed attempts in the 6x band OR for scheduled independent GodMode review.

Low-cost tier rule (0.33x):

- 0.33x models are now the **primary tier** for scouts, graders, finding extraction, and narrow reads.
- Do NOT use 0.33x for architecture synthesis, cross-layer refactors, or DI boundary work; escalate to 1x minimum.
- If two 0.33x routes fail in the same phase, escalate to 1x tier (not 3x or 6x) for the next attempt.

Vendor-agnostic failover rule:

- Do not hardcode fallback behavior around one named model.
- If the currently selected model errors, always move to the next healthy compatible candidate in the active ladder, regardless of vendor.
- Keep cross-vendor diversity in ladders so one provider outage cannot stall the cycle.

Artifact logging rule:

Whenever fallback occurs, record in the phase artifact:

- requested tier
- requested model
- failure type
- fallback model used
- reason the fallback was chosen (`cheapest compatible`, `vision required`, `preview avoided`, `same-tier exhausted`, `escalated to high-reasoning`)
- intended canonical worker role (`mutl3y-scout`, `mutl3y-probe`, `mutl3y-builder`, `mutl3y-gatekeeper`, or `mutl3y-archivist`)
- actual agent name when it differs from the canonical Mutl3y worker
- agent fallback reason (`canonical unavailable`, `canonical unhealthy`, `capability gap`, `route failure exhausted`)

Use short structured lines, not prose paragraphs.

### Model Usage Ledger (mandatory)

Track model reliability and response quality across cycles in:

- `docs/plan/<plan-id>/mutl3y-artifacts/model-usage-ledger.yaml`
- `docs/plan/<plan-id>/mutl3y-artifacts/model-scorecard.yaml`
- `docs/plan/.mutl3y-lessons/model-usage-history.yaml`
- `docs/plan/.mutl3y-lessons/model-usage-rollup.yaml`

Use one entry per dispatch attempt with these fields:

- `timestamp`
- `cycle`
- `phase`
- `worker`
- `task_id` (finding id or phase task)
- `requested_tier`
- `requested_model`
- `actual_model`
- `result` (`success`, `route_failure`, `quality_failure`)
- `failure_type` (`cancelled`, `timeout`, `startup`, `empty_response`, `missing_artifact`, `low_signal`, `mis-scoped_output`, `other`)
- `artifact_path`
- `quality_score` (1-5)
- `needed_reedit` (`true`/`false`)
- `recovery_action` (`none`, `reroute_same_tier`, `escalate_tier`, `prompt_tighten`, `foreman_recovery`)
- `notes`

YAML hygiene rules (mandatory):

- Use spaces only. Tabs are invalid in ledger and scorecard YAML.
- Write ledger entries through `python3 <SKILL_ROOT>/scripts/record_model_usage.py ... --validate-log .mutl3y-gate/ledger-validate.log` instead of freehand YAML row edits.
- Immediately after any ledger or scorecard update, require `.mutl3y-gate/ledger-validate.log` to report `OVERALL PASS`.
- If validation fails, treat it as a barrier failure and do not proceed until the YAML is repaired.

Model scorecard update rule (mandatory):

- At every phase barrier, append or update per-model aggregates in `model-scorecard.yaml` with:
  - attempts
  - route_failures
  - quality_failures (`quality_score <= 2`)
  - reedit_count (`needed_reedit=true`)
  - rolling_quality_avg
  - lane_tags (discovery, builder, validation, bookkeeping)
- Routing decisions in later phases must cite current scorecard status (healthy, degraded, quarantined) for the selected model.
- At Phase 7, fold the cycle-local ledger and scorecard into `.mutl3y-lessons/model-usage-history.yaml`, then regenerate `.mutl3y-lessons/model-usage-rollup.yaml`.

Quality scoring guide:

- `5`: complete, high-signal, directly actionable, no re-edit
- `4`: minor cleanup only, still actionable
- `3`: partial signal, requires one foreman tightening pass
- `2`: low-signal or over-broad, requires re-dispatch or substantial rework
- `1`: unusable output

### Routing decisions from ledger metrics

Before dispatching a worker, consult the ledger summary for that model in the current cycle and last 3 cycles.

Read order:

1. Current cycle `mutl3y-artifacts/model-scorecard.yaml`, if it exists.
2. Persistent `.mutl3y-lessons/model-usage-rollup.yaml`.
3. Persistent `.mutl3y-lessons/model-usage-history.yaml` only if rollup is stale or missing.

Model demotion triggers (any one):

- route-failure rate >= 20% in current cycle with at least 5 attempts
- quality-failure rate (`quality_score <= 2`) >= 25% in last 3 cycles with at least 8 attempts
- repeated re-edit burden: `needed_reedit=true` on 3 consecutive attempts for same task class

Model promotion/recovery trigger:

- after demotion, require 3 consecutive successful attempts with `quality_score >= 4` before restoring preferred position.

Prompt-vs-model recovery rule:

- If output is low-signal but on-topic (`quality_score=2` with coherent scope), tighten prompt once and retry with next healthy model in same tier.
- If output is mis-scoped or empty (`quality_score<=2` and `failure_type` in `empty_response|mis-scoped_output`), reroute immediately to next model and tighten prompt.
- If two retries still need major foreman rewrite, escalate tier or switch to code-specialized model.

Phase defaults:

- P0 discovery: `low-cost`
- P1 grading: `balanced` (escalate on zero-Critical/High skepticism)
- P2 persist plan: `low-cost`
- P3 probes/synthesis: probes `balanced`, synthesis `high-reasoning`
- P4 decide: `high-reasoning`
- P5 implementation: mechanical `low-cost`, refactor `balanced`, ownership/layering `high-reasoning`
- P6 validation: gate/log `low-cost`, triage `balanced`, disputed regressions `high-reasoning`
- P7 closure/bookkeeping: `low-cost`

Escalate to `high-reasoning` when:

- findings touch layering, ownership boundaries, composition root, plugin registry seams, or facade leakage
- scout, test, and runtime evidence conflict
- a fix changes cross-layer contracts, DI authority, plugin routing, or bootstrap/startup semantics
- two attempts on the same finding fail to converge

After a `high-reasoning` decision is recorded in `findings.yaml`, drop downstream mechanical steps back to `low-cost` or `balanced`.

Token discipline:

- keep prompts phase-local (finding IDs, owned files, failure excerpt)
- pass artifact paths plus short excerpts, not raw logs
- reuse stable prompt scaffolding
- do not run full-cycle high-reasoning sweeps for one ambiguous finding
