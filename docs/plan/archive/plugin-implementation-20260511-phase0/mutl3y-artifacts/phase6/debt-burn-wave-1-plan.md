version: 1
plan_id: g84-remediation-mutl3y-cycle-20260509
cycle: g84
phase: P6-debt-burn
wave: 1
status: planned
objective: "Close repo-wide ruff, black, and mypy gates before Phase 7 closure"
scope:
  ruff:
    errors: 26
    fixable: 22
    auto_fix_possible: true
  black:
    files_to_reformat: 19
    auto_format_possible: true
  mypy:
    errors: 110
    files_affected: 20
    categories: "TypedDict mismatches, protocol type failures, ScanPolicyContext issues, ScanMetadata type errors"
workers_planned:
  - Scout-LintScope (Tier 0, categorize ruff/mypy)
  - Builder-RuffFix (Tier 0, apply --fix)
  - Builder-BlackFormat (Tier 0, apply formatter)
  - Builder-MypyTargeted (Tier 0→1, fix touched-file mypy first, then assess repo-wide)
timeline:
  - action: "Scout categorizes ruff/mypy by touched-file vs. repo-wide"
  - action: "Builder-RuffFix applies ruff --fix to auto-fixable errors"
  - action: "Builder-BlackFormat applies black to reformat 19 files"
  - action: "Builder-MypyTargeted fixes type errors in touched files first"
  - action: "Full gate run: pytest + ruff + black + mypy"
  - action: "Record Phase 7 entry checkpoint"
