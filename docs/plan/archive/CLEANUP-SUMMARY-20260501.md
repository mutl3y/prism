# Cleanup Summary — 1 May 2026

**Scope**: Plan consolidation & dead-plan archival
**Status**: COMPLETE
**Committed**: commit 462b7a3

---

## What Changed

### Archived (Dead Plans)

- ✅ `20260421-policy-as-code-audit/` → `archive/` (superseded by T1-01 in architecture-extensibility-review)

### Code Fixes Applied

- ✅ FIND-G15-01: Deduplicated `TRUTHY_ENV_VALUES` (import from kernel, remove local copy)
- ✅ FIND-G15-08: Made `_reserved_unsupported_platforms` immutable via frozenset rebuild
- ✅ New test: `test_registry_reserved_platforms.py` (validates immutability across threads)

### Archival Moves

- ✅ g14–g17 Gilfoyle cycles → `archive/` (all findings validated & closed)

---

## Active Plans Remaining

| Plan | Status | Next Action |
|------|--------|-------------|
| `architecture-extensibility-review-20260421` | **active** | Tier 3 tasks (error boundaries, async I/O) |
| `20260425-readme-renderer-plugin-design` | **design_only** | Awaiting implementation approval |

---

## Validation Summary

**Code Validation**:

- 45 focused tests PASS (registry, di_helpers, readme, parity)
- Ruff: PASS
- Black: PASS
- Pytest full suite: 994 PASS

**Plan Status Contradiction** (RESOLVED):

- Issue: `20260421-policy-as-code-audit` marked `pending` in own file but `done` in T1-01
- Fix: Archived the dead plan; T1-01 is canonical authority (completed 2026-04-22)

---

## Artifacts Created

- This file: `docs/plan/archive/CLEANUP-SUMMARY-20260501.md`
- G15 fixes staged and committed
- G14-G17 archives staged and committed

---

## Next Steps

**Option 1**: Start Tier 3 work from active architecture-extensibility plan
**Option 2**: Review & approve readme-renderer design for implementation
**Option 3**: Run full cleanup audit if other stale folders remain in docs/plan/
