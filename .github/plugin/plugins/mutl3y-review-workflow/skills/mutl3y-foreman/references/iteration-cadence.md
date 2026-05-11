# Iteration Cadence & Depth Escalation

This skill is designed for repeated cycles, not a single pass. Each cycle is `mutl3y-gN` by default (g3, g4, g5, ...). Continue an existing `gilfoyle-gN` sequence only when resuming historical plans. The depth of the review **scales inversely** with how clean the code is.

| Cycle State | Review Depth | Scope |
|---|---|---|
| Critical or High findings still open | **Light/targeted** review of the recently-changed files plus their immediate neighbours | Just enough breadth to confirm fixes landed and didn't introduce new Critical/High |
| Zero Critical/High findings returned by light review | **Thorough whole-codebase review** | Full Phase 0 sweep across every module in the target package(s); apply the minimum density check |
| First clean thorough review | **Second thorough whole-codebase review on a different focus axis** | Full Phase 0 sweep again; rotate the primary focus axis and reapply the safeguard floor checks |
| Second consecutive clean thorough review on a different focus axis | **Full fresh unconstrained God Mode review** | Independent whole-codebase God Mode pass with no current findings, shortlist framing, focus-axis hints, or seam-family steering |
| Clean God Mode review after the required clean thorough passes | **Done.** Sign off and stop iterating. | n/a |

**Rule:** Never sign off after a light review. A light review is only
valid as a checkpoint, not as the terminating verdict. A single clean
thorough review is also only a checkpoint. Final sign-off requires two
consecutive clean thorough reviews on different focus axes, with the
safeguard floor checks still passing, and then one clean full fresh
unconstrained `Gilfoyle Code Review God Mode` pass. "Unconstrained"
means no current findings, no shortlist framing, no focus-axis hints,
and no seam-family steering in the dispatch prompt.

**Operational corollary:** a green `live_narrow_run` or similar
checkpoint cycle may close that cycle, but it must not be narrated as
the overall loop stopping condition. If the cadence floor above is not
yet satisfied, the foreman must either open the next required cycle
immediately or leave an explicit paused-resume artifact at
`mutl3y-artifacts/phase7/paused-resume.yaml` naming that next cycle and
why stop is not yet valid. A retained `next_recommendation` without
immediate dispatch or a paused-resume artifact is a workflow stall, not
a completed checkpoint.

**Predecessor reconciliation rule:** before reporting any stop, pause, or cycle-close message for the active loop, reconcile older same-family review plans. If an earlier plan is still marked `in_progress`, either carry its unresolved findings forward into the new active cycle and close the predecessor as a handoff cycle, or keep the predecessor as the active resume surface. Never leave stale `in_progress` predecessors behind a newer green checkpoint.

## Cycle loop

```text
loop:
  1. Apply fixes from previous review's findings.yaml (Phases 3–5)
  2. Run gate (Phase 6); abort cycle if gate red
  3. If the user explicitly requested or approved repo commits in the
     current conversation, commit non-interactively as mutl3y-gN with
     one-line per FIND in the message; otherwise record
     `commit_deferred` in the Phase 7 closure or paused-resume artifact
     and continue without pretending a commit happened
  4. Launch the next Gilfoyle review:
     - If previous review had Critical/High open → light review of changed files
     - If previous review was a clean light checkpoint → thorough whole-codebase review (full Phase 0)
     - If previous review was the first clean thorough checkpoint → second thorough whole-codebase review on a different focus axis
     - If previous review was the second consecutive clean thorough checkpoint → full fresh unconstrained `Gilfoyle Code Review God Mode` review
  5. If review returns zero Critical/High AND it was the clean God Mode review after the required clean thorough passes → exit loop
     Else → goto 1 with N := N+1
```

**Closeout rule:** when step 4 is determined from a retained
`next_recommendation`, the foreman must dispatch that next cycle in the
same response turn unless it writes the paused-resume artifact first.
Calling the task finished before one of those happens is invalid.

## Hard rules — these are not suggestions

### Rule 1 — No silent drop of high-severity observations

Every `severity_hint: high` scout observation that Phase 1 does not promote to a finding must be written to a `suppressed_highs` section in the plan artifact with a one-line suppression rationale. Valid rationale codes: `false_positive`, `do_not_re_flag` (cite the digest.yaml entry), `deferred` (state the reason), `duplicate_of` (cite the FIND-ID). A blank rationale is not valid — if you cannot give one, promote the observation instead.

This rule exists because g19 scout artifacts contained the evidence for all 10 independent review findings. The Phase 1 grading pass silently dropped 6 of them. The gap was not scout blindness; it was unconstrained grading discretion.

### Rule 2 — Exhaustive review findings feed the shortlist

Any finding rated High or Critical in an exhaustive review artifact (Synthesizer-Architecture, God Mode, independent grader) that is not already in `findings.yaml` must be promoted into `findings.yaml` before implementation begins. Exhaustive review artifacts are not parallel documents — they are an extension of the shortlist. The shortlist is the only thing builders read; if it is incomplete, the exhaustive review produced no value.

### Rule 3 — `decision: null` expires after one cycle

A finding may carry `decision: null` for at most one full cycle (one light or thorough review pass). If it remains null after that, Phase 4 must either record a decision or assign a named micro-swarm investigator with a specific investigation question. Carrying `decision: null` into Phase 5 is not valid — a builder cannot act on a null decision and will skip the finding.

Track this with `decision_deadline: gN` on the finding. If `cycle > decision_deadline` and decision is still null, the foreman must resolve it before dispatching builders.

### Rule 4 — Gate-green is not sufficient close evidence for architecture findings

A finding rated High or Critical in categories `ownership`, `composition_root`, `registry_authority`, `facade_leakage`, `shell_boundary`, or `orchestration_seam` may only be marked `closed` if `closed_evidence` contains all three of:

- A line citation to the exact code that changed (file path + line number)
- Either a reference to a new test that would catch regression of this specific seam, or an explicit statement of which existing test covers it and why it would catch the regression
- Gate result (pytest -q, ruff, black, mypy delta)

Gate-green alone does not prove the seam was fixed. A registry authority split can survive a full green gate if no test exercises the injected-registry path.

### Rule 5 — Deferred findings are re-evaluated every 6 thorough cycles

Every 6th thorough cycle, the foreman reads all `status: deferred` findings from the ledger and current plan. For each, evaluate whether the original deferral condition still holds. If the blocking condition is resolved, promote back to `open` or close with evidence. If still blocked, update `deferred_reeval_due` to `current_cycle + 6`. Record the re-evaluation date and outcome in the finding and in digest.yaml.

Deferrals are not permanent. 11 deferred findings with no re-evaluation cadence become 11 permanent deferrals by g30.

## What "light review" means in practice

- Read every file modified in the last 1–3 commits
- Read the immediate importers/consumers of those files
- Apply the same review checklist categories (duplication, ownership, typing, silent fallbacks, guards, abstraction)
- Skip the ≥15-observation density floor (not enough surface to warrant it)
- Still produce a graded report with FIND-NN IDs

## What "thorough review" means in practice

- Full Phase 0 Explore subagent sweep across the entire target package(s)
- Record and pass a primary focus axis into the cycle, but treat it as a prioritisation aid rather than a boundary on what may be inspected
- If scouts surface a clear focus area or any High/Medium candidate, widen in that same cycle to the owning abstraction, close neighbors, boundary call sites, and nearby tests before grading
- Apply the minimum density check (≥15 raw observations for ≥10 modules)
- Re-examine architectural rules end-to-end (layering, fail-closed contracts, plugin boundaries)
- Cross-check against repo-level architectural documents (e.g. AGENTS.md notable findings, plan closure records)

### Phase 1 cross-cutting micro-check (every thorough cycle, not just deep reviews)

After merging Phase 0 scout artifacts and before finalising the shortlist, the foreman must run a lightweight cross-cutting check on two categories that scouts consistently miss in isolation:

**Registry authority check:** Read all Phase 0 scout observations tagged `registry_authority`, `composition_root`, or `ownership` and ask: do they, taken together, describe a split-authority path where the injected registry diverges from the fallback? A single-scout observation of "DIContainer uses default_plugin_registry" becomes a HIGH finding only when a second scout notes "runtime_registry computed from scan_options downstream" — the foreman must draw that connection at Phase 1 even without a Synthesizer.

**Facade leakage check:** Read all Phase 0 scout observations tagged `facade_leakage`, `abstraction`, or `ownership` on public API/CLI modules. For every internal helper or registry singleton mentioned, verify whether any test patches it through the public facade (which would freeze the leak as a test dependency). If yes, promote to at least HIGH facade_leakage with the test seam noted.

These two checks do not require a new agent — the foreman executes them locally from the merged scout artifacts. If either produces a new finding not already in the shortlist, promote it before proceeding to Phase 2.

The full Synthesizer-Architecture agent remains reserved for deep reviews (every 3rd thorough cycle) where a full architectural map is needed. These micro-checks exist so the most common cross-cutting patterns are caught in every cycle even without the synthesizer.

## Periodic deep review

Every third thorough review cycle, run the full deep review protocol in addition to the standard Phase 0 sweep. The deep review is designed to catch cross-cutting findings that isolated category scouts consistently miss.

| Condition | Action |
| --- | --- |
| `cycle_number % 3 == 0` (i.e. g3, g6, g9, g12, …) | Deep review after Phase 0 |
| Phase 1 promoted fewer than one-third of raw scout observations | Deep review immediately (low signal efficiency) |
| Before any major decomposition or platform expansion wave | Deep review required |
| After any wave touching plugin bootstrap, DI composition, or registry wiring | Deep review required |

What the deep review adds beyond the standard sweep:

- **Cross-cutting synthesis** — one named `Synthesizer-Architecture` agent reads all Phase 0 artifacts together and looks for findings that only emerge from combining scout reports across silos
- **Shared structural map** — the synthesizer reads the full `architecture-graph.json` so it starts from one consistent view of facades, registries, DI roots, and test links
- **Registry authority trace** — verifies that all downstream resolver paths read from the same injected registry authority
- **Composition root audit** — checks for hidden secondary composition roots outside the declared DI ingress
- **Facade leakage audit** — enumerates every symbol re-exported from public API/CLI surfaces and flags internal assembly helpers that leak
- **Shell-to-plugin boundary audit** — confirms shell layers do not import directly from plugin-internal modules, bypassing approved seams
- **Error channel audit** — checks every `except` block and `or {}` / `or None` fallback in `scanner_io` and `scanner_extract` for silent failure masking
- **Seam contract quality** — audits the six primary architecture boundary crossings for `Any`, `Callable[..., Any]`, and `dict[str, Any]` at parameter/return positions
- **Audit and reporting boundary ownership** — verifies audit and reporting modules own their rendering/execution entry points rather than re-exporting traversal or plugin internals

Full protocol and agent prompts: [deep-review-protocol.md](./deep-review-protocol.md)

## Test-update discipline during iteration

When a fix changes contract semantics (e.g. a silent-fallback fix that becomes fail-closed), tests that asserted the old silent-fallback behaviour are now wrong. Update those tests in the same wave as the fix — do not weaken the fix to keep stale tests green. Record the test update in the cycle commit message.
