# Subagent & False-Clean Safeguards

Reviews can return a misleading "all clean" verdict for two reasons. Both must be guarded against, because both have happened in past cycles and were not noticed at the time.

## 1. Subagent failure detection

A subagent (Explore, runSubagent for the Gilfoyle reviewer, search_subagent, execution_subagent) can fail or time out and return a short or empty result that *looks* like a successful review with no findings. **Treat any of the following as a subagent failure, not a clean review:**

- Returned text is shorter than ~30 lines for a thorough review
- No `FIND-NN` IDs anywhere in the output
- No grade (A–F) in the output
- Output contains error markers: `Error`, `Traceback`, `timeout`, `timed out`, `failed`, `No tools were invoked`, `<final_answer></final_answer>` empty
- Output contains only the agent's preamble with no analysis body
- Reviewer reports zero findings without listing the files it actually examined

**Required response on detected failure:**
1. Do **not** mark the cycle complete.
2. Do **not** advance the gN counter.
3. Re-run the subagent with the same prompt; if it fails twice, fall back to direct file reads + a manual review pass.
4. Record the failure in the cycle log.

## 2. False-clean / review exhaustion detection

After 2–3 successful cycles the reviewer can start returning thin reports because the obvious surface has been cleaned, not because the codebase is actually done. Apply the following floor checks before accepting a "zero Critical/High" verdict from a thorough review:

| Check | Trigger |
|---|---|
| **Coverage proof** | Reviewer must list (by path) every file/package it inspected. If the list is shorter than the target package's actual file count, reject as incomplete. |
| **Category proof** | Reviewer must explicitly state findings per category (duplication / ownership / typing / silent_fallback / guard / abstraction). Missing categories must be called out as "examined: none found", not silently omitted. |
| **Density floor** | For ≥10 modules, raw observations (before grading) must be ≥15. A thorough review reporting <5 observations of any kind is a false-clean signal — re-run with a wider scope or rotate the focus area (e.g. concurrency, error handling, performance, public API stability) that the previous review skipped. |
| **Diff probe** | At least one finding must reference a file that was *not* modified in the last 3 commits. If every finding sits on freshly-changed code, the reviewer is only auditing the diff, not the codebase. |
| **Rotation discipline** | Each thorough cycle must declare its primary focus axis (architecture, concurrency, typing, error handling, performance, security, test gaps). Track focus axes across cycles; do not accept a "clean" verdict until every axis has been the primary focus at least once. |

If any floor check fails, the verdict is **inconclusive, not clean.** Re-run with an explicit instruction to address the failed check (e.g. "rotate focus to concurrency and error handling; explicitly examine these files: …").

**Sign-off requires all of:**
- Subagent failure indicators absent
- All floor checks passed
- All declared focus axes have been covered across the cycle history
- Two consecutive thorough reviews on different focus axes both return zero Critical/High

Stopping after a single thorough-clean review is not sufficient — it has produced false negatives in past runs.
