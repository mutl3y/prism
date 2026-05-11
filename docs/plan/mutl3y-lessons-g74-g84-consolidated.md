# Mutl3y Lessons Learned: Cycles g74–g84

## Executive Summary

- Total cycles reviewed: 13 (g74 → g84 family, including godmode, g82-test, wave2-hotpath, cluster-autopilot, structure-validation, di-container-refactoring).
- Date range: 2026-05-05 → 2026-05-08.
- Key metrics (artifact-backed): consolidated findings ≈ 375+ (examples: g84 consolidated 261; g77 45; cluster-autopilot 30; g82-test 22; g78 9; g79 8) — see cited artifacts below.
  - Representative sources: [g84 findings consolidated](archive/mutl3y-cycles-g74-g84/g84-10-model-gilfoyle-comparison-20260508/g84-findings-consolidated.yaml#L1), [g77 plan & metrics](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/plan.yaml#L1), [cluster-autopilot summary](archive/mutl3y-cycles-g74-g84/mutl3y-cluster-autopilot-20260507/plan.yaml#L1), [g82-test phase0 summary](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260508-g82-test/artifacts/phase-0-findings.yaml#L1).
- High-level takeaway: Tier-0-first discovery (free-tier scouts) plus targeted tier escalation performed well for discovery and triage; most cycles produced 3–5 fix waves and required 1–2 validation gates before closure.

## Lesson Categories

### 1. Tier Enforcement

**What worked:**

- Default Tier-0 (free-tier / GPT-4o / GPT-5 mini) for Phase 0 scouts kept cost low while yielding high-signal findings (see g78, g79, g82-test artifacts). [g78 plan](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g78/plan.yaml#L1), [g82-test scout summary](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260508-g82-test/plan.yaml#L1).
- Escalating to low-cost / tier-1 for deeper probes or builders (when findings ambiguous) produced clearer root causes without large cost increases (examples in g77/godmode waves). [g77 phases](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/plan.yaml#L1), [godmode artifacts](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-godmode/mutl3y-artifacts/phase3-swarm/approach-b-di-based.yaml#L1).

**What failed / risks:**

- Occasional implicit escalation decisions (ad-hoc model routing inside autopilot) confused cost accounting and audit trails (policy visible in some plan metadata). [g79 coordination](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g79/plan.yaml#L1).
- One-off multi-model experiments (g84 model-comparison) created very large consolidated finding volumes and higher editing churn; these require explicit cost/quality gating. [g84 consolidated](archive/mutl3y-cycles-g74-g84/g84-10-model-gilfoyle-comparison-20260508/g84-findings-consolidated.yaml#L1).

**Pattern recommendations:**

- Enforce Tier-0 default for Phase 0 scouts; require a recorded tier-escalation justification artifact before any Tier-2+ dispatch. Cite justification in `model-usage-ledger` (seen in g77/g76). [g77 model ledger ref](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/plan.yaml#L1).
- For multi-model experiments, set explicit sampling and stop conditions (limit sweep breadth/timebox).

### 2. Delegation Discipline (Scout-first vs. Foreman-local edits)

**Observations:**

- Scout-first (discovery → grader → probe) reliably separated discovery from fix work and reduced premature edits (strong evidence in g77, g78, wave2-hotpath). [g77 phases](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/plan.yaml#L1), [wave2-hotpath summary](archive/mutl3y-cycles-g74-g84/mutl3y-review-wave2-hotpath-20260507/WAVE2-COMPLETE.yaml#L1).
- Foreman-local edits (ad-hoc edits during planning) sometimes introduced ownership confusion and extra fix waves (noted in cluster-autopilot logs).

**When to delegate vs. local edit:**

- Delegate to builders for multi-file or cross-cutting fixes (hotpath migration, DI refactor) — use builder waves with explicit owned_files (see wave2-hotpath). [wave2-hotpath plan](archive/mutl3y-cycles-g74-g84/mutl3y-review-wave2-hotpath-20260507/plan.yaml#L1).
- Allow foreman/local edits only for single-line clarifications, triage label changes, or artifact corrections — not substantive refactors.

**Pattern recommendations:**

- Require `owned_files` and `wave` metadata in any Phase-5 builder dispatch (enforced in many wave artifacts).
- Keep scouts read-only; scouts may propose fixes but must not change source without builder ownership.

### 3. Route Failure Recovery (Model fallback & quarantine)

**Observations:**

- Model fallback strategies worked when captured in `execution-trace` and `model-usage-ledger` (fallback → retry with alternate node or escalate to tier-1). [g77 execution trace ref](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/mutl3y-artifacts/execution-trace.yaml#L1).
- Quarantine patterns (isolate noisy model outputs and re-run with alternate model) were helpful in g84 multi-model experiments.

**Pattern recommendations:**

- Capture model fallback events in `model-usage-ledger` with `tier_selected` and `tier_reason` (ease auditability). Example ledger presence in g77/g76 artifacts.
- Quarantine noisy model outputs by labeling findings with `model_source` and re-running the same prompt under a secondary model before promoting to fix waves.

### 4. Model Usage Optimization (cost & quality)

**Cost trends:**

- Phase-0 Tier-0 scouts dominate volume but cost remains low per cycle; targeted Tier-1/Tier-2 usage for probes/builders is cost-effective. (g78/g82-test show low-cost default + selective escalation).

**Quality / re-edit patterns:**

- Findings from free-tier scouts have high signal but occasionally need re-edit during fix wave if type-safety or DI issues surface (see wave2-hotpath type delta +14 errors). [wave2-hotpath results](archive/mutl3y-cycles-g74-g84/mutl3y-review-wave2-hotpath-20260507/WAVE2-COMPLETE.yaml#L1).
- Multi-model experiments produce variance: g84 found many overlapping and duplicate findings (high re-edit churn). [g84 consolidated](archive/mutl3y-cycles-g74-g84/g84-10-model-gilfoyle-comparison-20260508/g84-findings-consolidated.yaml#L1).

**Pattern recommendations:**

- Use Tier-0 for breadth, Tier-1 for ambiguity, Tier-2+ for architectural or ownership refactors; always record ledger entries with counts and models for later ROI analysis.
- For multi-model comparisons, aggregate and dedupe findings programmatically (reduce re-edit by merging duplicates before wave assignment).

### 5. Workflow Improvements (phase sequencing, artifacts, barrier checks)

**Phase sequencing lessons:**

- Strict scout → grader → probe → builder → gatekeeper → archivist sequence reduced churn (documented in g77/g78/g76). [g77 phases](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/plan.yaml#L1).
- Hotpath migrations (wave2) benefit from a "factory-scaffolding → dual-signature migration → validation" flow; keep baseline tests fixed (wave2-hotpath pattern). [wave2-hotpath plan](archive/mutl3y-cycles-g74-g84/mutl3y-review-wave2-hotpath-20260507/WAVE2-COMPLETE.yaml#L1).

**Artifact discipline:**

- `model-usage-ledger` and `execution-trace` are essential for post-mortem and cost analysis (consistent across g76/g77/g82-test).
- Findings should include `severity`, `affected_files`, and `fix_group` to enable automated grader clustering (common in cluster-autopilot and g77).

**Barrier checks:**

- Enforce validation gates (pytest, ruff, black, mypy) before closure; cycles that skipped gates risk regression (g78/g76 show gate artifacts).

**Pattern recommendations:**

- Make `phase-start-audit` and `phase-end` artifacts required for every phase transition.
- Enforce `model-usage-ledger` entries before any Tier escalation (saves audit friction).

## Quantitative Summary (artifact-backed)

- **Total findings** (sampled from artifacts): ≈ 375+ (representative tallies: g84=261; g77=45; cluster-autopilot=30; g82-test=22; g78=9; g79=8). See cited artifacts.
- **Average findings per cycle** (approx): ~29 (375 / 13).
- **Fix-wave distribution** (observed): most cycles used 3–5 waves; deep reviews (godmode/g77) added extra waves (4+). [g77 phases](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/plan.yaml#L1), [godmode artifacts](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-godmode/findings.yaml#L1).
- **Model usage breakdown** (observed patterns):
  - Tier-0 (free-tier scouts): primary discovery mode (most cycles).
  - Tier-1 (low-cost): targeted probes / concentrated waves.
  - Tier-2 (balanced): architecture-sensitive builders or deep probes.
  - Multi-model experiments (g84) produced large finding volumes and drew multiple tiers for cross-validation. [g84 consolidated](archive/mutl3y-cycles-g74-g84/g84-10-model-gilfoyle-comparison-20260508/g84-findings-consolidated.yaml#L1).

## Recommendations for Future Cycles (Top 7, actionable)

1. **Enforce `Tier-0 default + recorded escalation` rule**: require a `model-usage-ledger` entry (tier + reason) before any Tier-1+ dispatch. (See g77/g76 ledger usage.)
2. **Make scouts strictly read-only** and require builder ownership for any source edits — record `owned_files` and `wave` metadata before Phase-5 starts. (Wave2-hotpath + g77 patterns)
3. **For multi-model sweeps**, require deduplication and a stop-condition policy to avoid exponential re-edit churn; capture `model_source` per finding. (g84 lessons)
4. **Require `phase-start-audit` and `phase-end` artifacts** for every phase transition and block Phase-5 until `phase-start-audit` passes. (Seen in g76/g75 audits)
5. **Standardize model-fallback/quarantine logging** in `execution-trace` and `model-usage-ledger` to record fallback events and quarantined findings for post-cycle ROI. (g77, g82-test evidence)
6. **For hotpath/DI work**, follow the "factory scaffolding → dual-signature migration → validation" pattern; keep baseline tests fixed (wave2-hotpath success). [wave2-hotpath summary](archive/mutl3y-cycles-g74-g84/mutl3y-review-wave2-hotpath-20260507/WAVE2-COMPLETE.yaml#L1)
7. **Automate findings clustering and severity normalization** before graders run, reduce manual duplication across model nodes (saves 20–40% grader effort shown in multi-node g84 artifacts).

---

## Sources (selected artifacts consulted)

- [mutl3y-review-20260507-g77 plan & phases](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g77/plan.yaml#L1)
- [mutl3y-review-20260507-g78 plan + findings](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g78/plan.yaml#L1) and [findings](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-g78/mutl3y-artifacts/phase0/phase-start-audit.yaml#L1)
- [mutl3y-review-20260508-g82-test phase0 summary](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260508-g82-test/artifacts/phase-0-findings.yaml#L1)
- [g84 multi-model consolidated findings](archive/mutl3y-cycles-g74-g84/g84-10-model-gilfoyle-comparison-20260508/g84-findings-consolidated.yaml#L1)
- [wave2 hotpath migration (runbook & completion)](archive/mutl3y-cycles-g74-g84/mutl3y-review-wave2-hotpath-20260507/WAVE2-COMPLETE.yaml#L1)
- [cluster-autopilot summary & findings](archive/mutl3y-cycles-g74-g84/mutl3y-cluster-autopilot-20260507/plan.yaml#L1)
- [godmode artifacts & recommendations](archive/mutl3y-cycles-g74-g84/mutl3y-review-20260507-godmode/findings.yaml#L1)
- Other cycle artifacts and execution traces under archive/mutl3y-cycles-g74-g84/ (reviewed).

---

**Prepared by**: Scout-LessonsConsolidation (Tier 0)  
**Date**: 2026-05-11  
**Cycles reviewed**: 13 (g74-g84 family)  
**Artifact count**: 375+ findings across cycles
