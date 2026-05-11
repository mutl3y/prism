# Anchored Compaction

Use this when resuming a long or interrupted cycle, or when live context needs
 to be reduced without losing artifact trail continuity.

## Required Sections

Every compaction summary should preserve these anchors in this order:

1. `objective`
2. `current_phase`
3. `active_findings`
4. `owned_file_sets`
5. `artifacts_written`
6. `decisions_made`
7. `open_risks`
8. `next_actions`

Keep file paths, worker names, and finding IDs verbatim.

## When To Refresh

Refresh the anchored summary when:

- resuming after interruption
- context-health degradation triggers fired
- the phase changed after a long implementation or validation slice
- the current summary no longer reflects the latest retained artifacts

## Probe Questions

Before trusting a compacted summary, verify it can answer:

- Which phase is active?
- Which findings are still open?
- Which files were edited in the current slice?
- Which artifact proves the last confirmed checkpoint?
- What is the next action?

If the summary cannot answer those, rebuild it from artifacts instead of
continuing.
