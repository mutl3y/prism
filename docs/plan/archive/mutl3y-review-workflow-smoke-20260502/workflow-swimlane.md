# Workflow Swimlane

Readable operator view of the Mutl3y workflow. This is deliberately ASCII-first
so the routing, ownership, and loop-back paths stay legible.

```text
Legend
  [action]   work performed in that lane
  <decision> foreman-owned branch
  -->        forward handoff
  <--        repair / loop back
  ==>        artifact written or updated
  !!         stall / recover before continuing

Entry routing
  resolve phase from plan.yaml + findings.yaml
      |
      +--> P0 ............ Panel A
      +--> P1-P4 ......... Panel B
      +--> P5-P6 ......... Panel C
      \--> P7 ............ Panel D

PANEL A  Cycle Entry + Discovery
+----------------------------+----------------------------+----------------------------+----------------------------+
| Foreman / Routing          | Review Agents              | Delivery Agents            | Artifacts / State          |
+----------------------------+----------------------------+----------------------------+----------------------------+
| [load always-read refs]    |                            |                            | [digest.yaml + rollup]     |
| [read plan + findings]     |                            |                            | [plan.yaml / findings.yaml]|
| <repo state trustworthy?>  |                            |                            | [resumption pointer match] |
| no --> !! STALL            |                            |                            | [recover missing evidence] |
| yes --> [write P0 audit]   |                            |                            | ==> phase0/start-audit     |
| [dispatch scout batch] --> | [Scout-Typing]             |                            | ==> phase0/Scout-*.yaml    |
|                            | [Scout-Ownership]          |                            |                            |
|                            | [Scout-ControlFlow]        |                            |                            |
|                            | [Scout-Graph]              |                            |                            |
| <High/Med or seam family?> |                            |                            |                            |
| yes -->                    | [bounded widening pass]    |                            | [same-cycle widened notes] |
| no  --> skip widen         |                            |                            |                            |
| [run P0 barrier]           |                            | [sync ledger + scorecard] | ==> learning-context.yaml  |
| <deep review required?>    |                            |                            | ==> model ledger/scorecard |
| yes -->                    | [Synthesizer-Architecture] |                            | ==> deep_review_delta      |
|                            | [God Mode calibration]     |                            | ==> scout-coverage-patch   |
| no  --> skip deep review   |                            |                            |                            |
| [handoff to Phase 1]       |                            |                            | [grading input ready]      |
+----------------------------+----------------------------+----------------------------+----------------------------+

PANEL B  Grading + Planning + Investigation
+----------------------------+----------------------------+----------------------------+----------------------------+
| Foreman / Routing          | Review Agents              | Delivery Agents            | Artifacts / State          |
+----------------------------+----------------------------+----------------------------+----------------------------+
| [Phase 1 grading]          |                            |                            | [Phase 1 scout inputs]     |
| [registry micro-check]     |                            |                            |                            |
| [facade micro-check]       |                            |                            |                            |
| <need indep. grader?>      |                            |                            |                            |
| yes -->                    | [independent grader]       |                            |                            |
| [write compact grading]    |                            |                            | ==> grading artifact       |
| [record suppressed_highs]  |                            |                            | ==> grading artifact       |
| [Phase 2 persist plan]     |                            |                            | ==> findings.yaml          |
| [sync resumption ptr]      |                            |                            | ==> plan.yaml              |
| <needs investigation?>     |                            |                            | ==> phase2 summary         |
| yes -->                    | [3-6 named probes]         |                            | ==> phase3/*.yaml          |
| [Phase 4 decide]           |                            |                            |                            |
| [dedup + normalize]        |                            |                            |                            |
| [record decisions]         |                            |                            | ==> findings.yaml          |
| [shape disjoint waves]     |                            |                            | ==> phase4 summary         |
| <owned files disjoint?>    |                            |                            |                            |
| no --> [re-slice wave] <-- |                            |                            |                            |
| yes --> [handoff to P5]    |                            |                            | [wave plan ready]          |
+----------------------------+----------------------------+----------------------------+----------------------------+

PANEL C  Implementation Waves + Validation
+----------------------------+----------------------------+----------------------------+----------------------------+
| Foreman / Routing          | Review Agents              | Delivery Agents            | Artifacts / State          |
+----------------------------+----------------------------+----------------------------+----------------------------+
| [write wave start audit]   |                            |                            | ==> wave-N-start-audit     |
| [write wave plan]          |                            |                            | ==> wave-N-plan.yaml       |
| [dispatch full batch] -->  |                            | [Builder-* batch]          |                            |
| [wave barrier]             |                            | [builder summaries]        | ==> phase5 summaries       |
| [check missing output]     |                            | [recover / re-dispatch]    |                            |
| [pre-validation checks]    |                            | [narrow gate + grep]       | ==> ledger + plan sync     |
| [Phase 6 validation]       |                            | [Gatekeeper]               | ==> .mutl3y-gate/*         |
| <need regression audit?>   |                            |                            |                            |
| yes -->                    |                            | [Auditor-Regression]       |                            |
| <gate green?>              |                            |                            | [gate-escape candidate?]   |
| no --> [repair loop]       |                            |                            | ==> gate-escape candidate  |
| [return to P5] <---------- |                            |                            |                            |
| yes --> [handoff to P7]    |                            |                            | [closure inputs ready]     |
+----------------------------+----------------------------+----------------------------+----------------------------+

PANEL D  Closeout + Iteration / Sign-off
+----------------------------+----------------------------+----------------------------+----------------------------+
| Foreman / Routing          | Review Agents              | Delivery Agents            | Artifacts / State          |
+----------------------------+----------------------------+----------------------------+----------------------------+
| [Phase 7 close & learn]    |                            | [Archivist optional]       |                            |
| [close findings]           |                            | [compile lessons]          | ==> lessons/history/digest |
| [collect learning inputs]  |                            |                            |                            |
| <clean thorough passes?>   |                            |                            |                            |
| no --> [rotate focus axis] |                            |                            | [next cycle seed]          |
| [start next cycle]         |                            |                            | [return to Panel A]        |
| yes -->                    | [final God Mode sign-off]  |                            |                            |
| <any High/Critical?>       |                            |                            |                            |
| yes --> [promote findings] |                            |                            | ==> findings.yaml          |
| [set calibration req]      |                            |                            | ==> cycle summary          |
| [start next cycle]         |                            |                            | [return to Panel A]        |
| no --> [DONE]              |                            |                            | [stop iterating]           |
+----------------------------+----------------------------+----------------------------+----------------------------+

Cadence notes
  - light review while High/Critical remain open
  - first clean light review triggers thorough whole-codebase review
  - second clean thorough review must rotate focus axis
  - final sign-off is a clean full God Mode pass after the required clean
    thorough passes
```

Use this as the easiest reading view. Keep the decision-map artifact for the
most exact branch semantics when you need to audit every edge.
