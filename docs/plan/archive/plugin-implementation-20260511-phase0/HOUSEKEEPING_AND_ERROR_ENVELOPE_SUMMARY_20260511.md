# Housekeeping + Error Envelope Design Review Complete

**Date**: 2026-05-11  
**Status**: ✅ Complete

---

## Housekeeping Execution ✅

**Result**: 22 directories → 2 active plans

### What Was Archived

**Phase 1: Old Mutl3y Cycles** (13 directories)
- g74, g75, g76, g77, g78, g79 cycles (all superseded by g84)
- godmode, g82-test, wave2-hotpath, cluster-autopilot
- structure-validation, g84-discovery, di-container-refactoring

**Phase 3: Future Initiative Stubs** (4 directories)
- Q2 Initiative 2 (PolicyManager)
- Q3 Initiative 4 (Cache Optimization + Phase 0)
- Q3 Initiative 6 (Type Safety Phase 5)

**Phase 4: Old Architecture Reviews** (2 directories)
- architecture-extensibility-review-20260421
- g82-tier-enforcement-test-20260508

### Current State

```
docs/plan/
├── .mutl3y-lessons/                           # Mutl3y workflow lessons (kept)
├── g84-remediation-mutl3y-cycle-20260509/     # ✅ COMPLETE: g84 full cycle
├── post-g84-arch-refactor-20260511/           # ✅ ACTIVE: Error envelope work
└── archive/
    ├── mutl3y-cycles-g74-g84/                 # 13 old cycles
    ├── future-initiatives/                    # 4 Q2/Q3 stubs
    └── architecture-reviews/                  # 2 old reviews
```

**Reduction**: 91% reduction (22 → 2 active directories)

---

## Error Envelope Design Review ✅

### Problem Identified (User Feedback)

**Ansible error envelope lacked file provenance:**
```python
# OLD DESIGN (before review)
detail: {
    "module_name": "copy",
    "task_name": "Copy configuration file",  # ❌ Can be duplicated!
    "role_path": "/path/to/role",
    "collection": "ansible.builtin"
}
```

**Issue**: Task names can be duplicated across files or within the same file. No way to pinpoint exact task location.

### Solution Applied

**Unified Ansible provenance with K8s/Terraform:**
```python
# NEW DESIGN (after review)
detail: {
    "module_name": "copy",
    "task_name": "Copy configuration file",
    "task_file": "tasks/main.yml",           # ✅ Relative path from role root
    "line_number": 42,                       # ✅ Task start line in file
    "task_index": 3,                         # ✅ Task position in file (0-based)
    "role_path": "/path/to/role",
    "collection": "ansible.builtin"
}
```

### Design Benefits

1. **Unified Provenance**: All platforms (Ansible, K8s, Terraform) now have file path + line number
2. **Duplicate-Safe**: Task names can repeat, but `task_file` + `line_number` uniquely identifies location
3. **Already Available**: Scanner captures this during catalog assembly (`task_file`, `task_index`, `raw_lines`)
4. **Implementation Path**: Thread task context through `scanner_context` to `_record_phase_error()`

### Updated Success Criteria

Added new criterion:
- ✅ **Provenance unification**: Ansible errors as diagnostic as K8s/Terraform

---

## Implementation Plan Updated

**Phase 2, Day 2 changes**:
- Ansible adapter now populates unified provenance fields:
  - `task_file` (relative path from role root)
  - `line_number` (task start line)
  - `task_index` (position in file)
  - `module_name`, `task_name`, `role_path`, `collection`
- Thread task context through scanner_context for error recording

**Current Limitations section updated**:
- Added: "**Ansible-specific**: Task errors lack file path + line number (task names can duplicate)"

---

## Next Steps

**Option A: Continue with error envelope implementation** (3-5 days)
- Now includes unified Ansible provenance
- Ready for Phase 1 (Protocol Design)

**Option B: Create consolidated lessons + roadmap first** (2-3 hours)
- Extract learnings from 19 archived plans
- Document future Q2/Q3 initiatives

**Option C: Both in parallel**
- Quick lessons extraction while Phase 1 design proceeds

**Recommendation**: Option A — Error envelope is the validated work item, lessons can be extracted later.

---

**Prepared By**: Tier 2 Foreman  
**Artifacts**:
- [HOUSEKEEPING_PROPOSAL_20260511.md](HOUSEKEEPING_PROPOSAL_20260511.md)
- [ERROR_ENVELOPE_IMPLEMENTATION_PLAN.md](post-g84-arch-refactor-20260511/ERROR_ENVELOPE_IMPLEMENTATION_PLAN.md)
- Archive: `docs/plan/archive/` (19 directories)
