Builder Resume Gate — Summary

Change: enforce repo-wide `ruff` and `black --check` on resumed cycles with dirty tracked Python files.

Why: resumed/continued cycles that already have uncommitted edits can silently bypass inter-wave lint/format checks and lead to wasted work. This gate enforces the check before new wave work starts.

Enforcement:
- Detect tracked, modified `.py` files in the working tree on resume.
- Run these repo-wide commands:
  - `.venv/bin/python -m ruff check src/prism`
  - `.venv/bin/python -m black --check src/prism`
- Record the result in the phase start-audit artifact under `resume_dirty_tree.status` and in `.mutl3y-gate/resume-dirty-tree.yaml` with `OK`, `STALL`, or `BLOCKED`.
- Foreman MUST block new wave work until `resume_dirty_tree.status == OK`.

Touched files:
- /raid5/source/test/agent_and_skills/.github/skills/mutl3y-review-workflow/SKILL.md
- /raid5/source/test/agent_and_skills/.github/skills/mutl3y-review-workflow/references/phase-0-discovery.md
- /raid5/source/test/agent_and_skills/.github/skills/mutl3y-review-workflow/references/foreman-execution-guardrails.md
- /raid5/source/test/agent_and_skills/.github/skills/mutl3y-review-workflow/references/gate-commands.md

Status: applied and recorded. The gate snippet logs to `.mutl3y-gate/resume-dirty-tree.{yaml,log}` and foreman should copy fields into the phase start-audit artifact before narrating phase start.
