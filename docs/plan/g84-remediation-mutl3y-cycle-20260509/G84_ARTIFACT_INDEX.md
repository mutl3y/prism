# G84 Artifact Index

Plan: g84-remediation-mutl3y-cycle-20260509  
Last updated: 2026-05-10

## Purpose

This index provides a single navigation layer for all artifacts under this folder after consolidation.

It is designed to answer three practical questions quickly:

1. What is the current truth?
2. What was completed vs deferred?
3. What should be used to drive the remaining implementation waves?

## Source-of-Truth Precedence

When two artifacts conflict, use this precedence (highest first):

1. Current test results and executable code in src/prism and tests
2. Gate artifacts and closure gates
3. Wave execution yaml and builder reports
4. Narrative summaries and roadmap docs

## Fast Reading Order

If you only have 20-30 minutes, read in this order:

0. FINAL_9_WAVE_WORKOFF_ADDENDUM.md
1. PHASE7_FINAL_CLOSURE_GATE.md
2. FINAL_SIGN_OFF.md
3. wave_1_tier1_execution.yaml
4. wave_2_tier2_execution.yaml
5. WAVE2_TIER2_EXECUTION_SUMMARY.md
6. Q2_2026_EXECUTION_STATUS.md
7. Q2_2026_FINAL_SUMMARY.md
8. g84-deferred-findings-roadmap-q2q42026.md

## Core Governance and Closure

- Final 9-wave execution addendum: FINAL_9_WAVE_WORKOFF_ADDENDUM.md
- Final sign-off: FINAL_SIGN_OFF.md
- Final closure gate: PHASE7_FINAL_CLOSURE_GATE.md
- Phase 7 summary: PHASE7_CLOSURE_REPORT.md
- Phase 5/6 summary: PHASE5_6_SUMMARY.md
- Current status snapshot: STATUS_REPORT.md
- Consolidated roadmap summary: COMPLETE_ROADMAP_SUMMARY.md

## Phase and Wave Execution Artifacts

- Main execution plan: EXECUTION_PLAN.md
- Execution checkpoint: EXECUTION_TRACE_CHECKPOINT.md
- Phase 5 wave closure yaml: phase-5-wave-1-critical-tier1-closure.yaml
- Wave 1 execution yaml: wave_1_execution.yaml
- Wave 1 tier execution yaml: wave_1_tier1_execution.yaml
- Wave 1 closure report: WAVE1_CLOSURE_REPORT.md
- Wave 1 additional reports:
  - WAVE1_ATTEMPT1_CHECKPOINT.md
  - WAVE1_BATCH2_SUMMARY.md
  - WAVE1_BATCH3_EXECUTION_LOG.md
  - WAVE-1-BATCH-5-CLOSURE-ARTIFACT.md
- Wave 2 execution yaml: wave_2_tier2_execution.yaml
- Wave 2 reports:
  - WAVE2_TIER2_EXECUTION_SUMMARY.md
  - WAVE2_BUILDER_REPORT.md
  - PHASE2_WAVE2_COMPLETION_REPORT.md
  - phase2-wave2-completion.json
- Wave 3 artifacts:
  - wave_3_execution.yaml
  - wave_3_execution_summary.yaml
- Wave 4 artifact:
  - wave4-consolidation-completion-report.md

## Q2 Initiative Artifacts

- Q2 program status:
  - Q2_2026_EXECUTION_STATUS.md
  - Q2_2026_FINAL_SUMMARY.md
  - Q2_INITIATIVES_PHASE0_COMPLETE.md
- Initiative 1:
  - Q2_INITIATIVE_1_PHASE0_KICKOFF.md
  - Q2_INITIATIVE_1_PHASE0_EXECUTION_TRACKER.md
  - Q2_INITIATIVE_1_DETAILED_TASKS.md
  - TASK_1_1_COMPLETION_SUMMARY.md
  - di-container-audit.md
  - call-site-analysis.md
  - extraction-boundaries.yaml
- Initiative 2:
  - Q2_INITIATIVE_2_DETAILED_TASKS.md
  - policymanager-audit.md
  - policy-consolidation-opportunities.yaml
- Initiative 3 (MP1):
  - Q2_INITIATIVE_3_DETAILED_TASKS.md
  - Q2_INITIATIVE_3_COMPLETE_SUMMARY.md
  - Q2_INITIATIVE_3_PHASE3_CANARY_DEPLOYMENT.md

## MP1 Contract and Deployment Pack

- MP1 baseline and boundaries:
  - mp1-audit-baseline.yaml
  - mp1-enforcement-boundaries.yaml
  - mp1-ingress-paths-documented.yaml
  - mp1-compliance-matrix.yaml
  - mp1-compliance-metrics.yaml
- MP1 implementation reports:
  - mp1-phase-1-checkpoint.md
  - mp1-phase-1-gate-report.yaml
  - mp1-phase-1-grader-report.md
  - mp1-phase-2-gate-report.yaml
  - mp1-runtime-enforcement-report.md
  - mp1-plugin-hardening-report.md
  - mp1-compatibility-validation-report.md
  - mp1-ci-implementation-report.md
  - mp1-test-gating-report.md
- MP1 operations:
  - mp1-canary-rollout-plan.md
  - phase-3-canary-deployment.md
  - mp1-monitoring-and-alerting-plan.md
  - mp1-rollback-procedures.md
  - mp1-ruff-rules.yaml
  - mp1-flow-diagram.md
  - mp1-flow-specification: marker-prefix-flow-specification.yaml

## Q3 Planning Pack

- Q3 program-level docs:
  - Q3_INITIATIVES_456_EXECUTION_READY.md
  - Q3_INITIATIVES_456_BUILDERS_TIER_CORRECT.md
  - Q3_INITIATIVES_456_PHASE5_SCOUT_PLAN.md
  - Q3_INITIATIVE_4_DETAILED_TASKS.md
  - Q3_INITIATIVE_5_DETAILED_TASKS.md
- Initiative 5 boundary enforcement:
  - q3-init5-layer-dependency-audit.md
  - q3-init5-boundary-enforcement-rules.yaml
  - q3-init5-remediation-roadmap.md
  - q3-init5-phase5-builder-planning.yaml
  - q3-init5-grading-report.yaml
- Initiative 6 type safety:
  - q3-init6-type-safety-audit.md
  - q3-init6-type-improvement-strategy.yaml
  - q3-init6-implementation-roadmap.md
  - q3-init6-grading-report.yaml

## Deferred and Long-Range Planning

- Deferred roadmap: g84-deferred-findings-roadmap-q2q42026.md
- Multi-week initiatives: MULTI_WEEK_ARCHITECTURAL_INITIATIVES.md
- Initiative trackers:
  - q2-initiatives-tracking.yaml
  - initiative-1-tracking.yaml
  - initiative-2-tasks.md
  - initiative-3-tasks.md
  - initiative-4-tasks.md
  - initiative-5-tasks.md
  - q3-initiatives-template.md
  - Q4_INITIATIVES_PLANNING_TEMPLATE.md

## Dashboard and Visual Artifacts

- DASHBOARD.html
- DASHBOARD_UPDATED_20260509.html

## Raw Artifact Subtree

Directory: artifacts/

High-value files:

- artifacts/PHASE_PROGRESS_TRACKER.md
- artifacts/PHASE_0_COMPLETION_REPORT.md
- artifacts/INITIATIVE_1_CLOSURE_CERTIFICATE.md
- artifacts/ARCHITECTURE_REVIEW_g84_gem_reviewer.md
- artifacts/ARCHITECTURE_REVIEW_findings.json
- artifacts/model_usage_ledger.yaml
- artifacts/wave_2_tier1_execution.yaml
- artifacts/wave_4_execution.yaml
- artifacts/wave_1_batch_4_summary.yaml
- artifacts/wave-4-execution-plan.yaml

Scout and task subfolders in artifacts:

- artifacts/phase-0-scout-policy-audit/
- artifacts/phase-0-scout-policy-boundary/
- artifacts/phase-0-scout-policy-caching/
- artifacts/phase-0-scout-policy-coordination/
- artifacts/phase-1-grader/
- artifacts/task-1-1-di-container-audit/
- artifacts/task-1-2-boundary-design/
- artifacts/task-1-3-service-locator-contract/
- artifacts/task-2-1-di-container-refactor/
- artifacts/task-2-2-service-locator/
- artifacts/task-2-3-integration-testing/

## Practical Guidance for Remaining Implementation Waves

For final implementation waves, use this control loop:

1. Select wave scope from execution yaml and deferred roadmap.
2. Confirm expected contracts from gate docs and MP1/boundary docs.
3. Execute wave changes.
4. Run the same full-suite gate before updating status artifacts.
5. Update only one canonical progress tracker after gate pass.

Recommended canonical progress tracker for ongoing waves:

- q2-initiatives-tracking.yaml (or create a single final-waves tracker if preferred)

## Known Drift Risk

Status summaries may be ahead of current runtime/test reality.
Always verify against current full pytest output before marking wave closure complete.
