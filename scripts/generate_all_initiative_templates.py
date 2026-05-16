#!/usr/bin/env python3
"""
Q2-Q4 Initiative Planning Template Generator

Creates task breakdowns for all initiatives using standardized templates.
Usage: python3 generate_all_initiative_templates.py
Output: initiative-2-tasks.md, initiative-3-tasks.md, q3-initiatives-template.md, etc.
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta

PLAN_BASE = Path("/raid5/source/test/prism/docs/plan/g84-remediation-mutl3y-cycle-20260509")

# Initiative definitions with task structures
INITIATIVES_FULL = {
    "2": {
        "name": "PolicyManager Extraction",
        "findings": 8,
        "weeks": 1,
        "start": datetime(2026, 5, 26),  # After Initiative 1
        "tier": "Tier 2",
        "cost_est": 0.050,
        "description": "Consolidate policy ownership across 4 modules to single PolicyManager",
        "phases": [
            {
                "name": "Design Phase",
                "days": 2,
                "tasks": [
                    "Create PolicyManager interface & protocol",
                    "Document policy resolution strategy",
                    "Identify all 4 policy ownership points",
                ]
            },
            {
                "name": "Implementation Phase",
                "days": 2,
                "tasks": [
                    "Extract PolicyManager class",
                    "Consolidate validation logic",
                    "Remove duplicate checks from consumers",
                ]
            },
            {
                "name": "Integration Phase",
                "days": 1,
                "tasks": [
                    "Update scan_request to delegate",
                    "Update scanner_context validation",
                    "Remove fallback paths",
                ]
            },
        ]
    },
    "3": {
        "name": "Marker-Prefix Boundary Enforcement",
        "findings": 5,
        "weeks": 1,
        "start": datetime(2026, 5, 26),  # Parallel with Initiative 2
        "tier": "Tier 2",
        "cost_est": 0.020,
        "description": "Complete MP1 contract: enforce ingress-only marker-prefix ownership",
        "phases": [
            {
                "name": "Analysis Phase",
                "days": 1,
                "tasks": [
                    "Audit all marker-prefix reads in scanner_core",
                    "Identify nested policy_context accesses",
                    "Document MP1 contract violations",
                ]
            },
            {
                "name": "Refactoring Phase",
                "days": 2,
                "tasks": [
                    "Remove nested policy_context reads",
                    "Update task_extract_adapters",
                    "Route through PolicyManager",
                ]
            },
            {
                "name": "Validation Phase",
                "days": 1,
                "tasks": [
                    "Grep audit: zero nested reads",
                    "Feature detection tests passing",
                    "Full pytest validation",
                ]
            },
        ]
    },
    "4": {
        "name": "Immutable Context Objects",
        "findings": 6,
        "weeks": 1,
        "start": datetime(2026, 8, 2),  # Q3
        "tier": "Tier 2",
        "cost_est": 0.020,
        "description": "Make ScannerContext immutable, enable thread-safe concurrent scanning",
        "phases": [
            {
                "name": "Freeze Phase",
                "days": 2,
                "tasks": [
                    "Make ScannerContext attributes read-only",
                    "Implement __setattr__ override or @frozen",
                    "Update documentation",
                ]
            },
            {
                "name": "Refactoring Phase",
                "days": 2,
                "tasks": [
                    "Update plugin methods for immutability",
                    "Implement copy-on-write",
                    "Update scanner_kernel orchestrator",
                ]
            },
            {
                "name": "Validation Phase",
                "days": 1,
                "tasks": [
                    "Thread-safety tests",
                    "Performance benchmarks",
                    "Concurrent scanning validation",
                ]
            },
        ]
    },
    "5": {
        "name": "Layer Boundary Enforcement",
        "findings": 23,
        "weeks": 1,
        "start": datetime(2026, 8, 9),  # Q3
        "tier": "Tier 2",
        "cost_est": 0.050,
        "description": "Fix 23 layer violations and enforce via CI",
        "phases": [
            {
                "name": "Analysis Phase",
                "days": 2,
                "tasks": [
                    "Audit all layer violations (8+6+5+4)",
                    "Document forbidden imports",
                    "Create violation registry",
                ]
            },
            {
                "name": "Refactoring Phase",
                "days": 2,
                "tasks": [
                    "Move protocols to scanner_data",
                    "Fix scanner_core imports",
                    "Break circular dependencies",
                ]
            },
            {
                "name": "Automation Phase",
                "days": 1,
                "tasks": [
                    "Create import validator script",
                    "Add CI enforcement",
                    "Document layer hierarchy",
                ]
            },
        ]
    },
}

def generate_initiative_template(init_id: str, init_config: dict) -> str:
    """Generate markdown task breakdown for an initiative."""
    start_date = init_config["start"]
    end_date = start_date + timedelta(days=init_config["weeks"] * 7)
    
    markdown = f"""# Q2/Q3 Initiative {init_id}: {init_config['name']}

**Timeline**: {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}  
**Goal**: Resolve {init_config['findings']} findings via coordinated refactoring  
**Tier**: {init_config['tier']}  
**Cost**: ${init_config['cost_est']:.3f} (estimated)

## Summary

{init_config['description']}

---

## Phase Breakdown

"""

    day_num = 1
    for phase_idx, phase in enumerate(init_config["phases"], 1):
        phase_end = day_num + phase["days"]
        markdown += f"""### Phase {phase_idx}: {phase['name']} ({phase['days']} days)

**Timeline**: Day {day_num}-{phase_end-1}  
**Tasks**:

"""
        for task_idx, task in enumerate(phase["tasks"], 1):
            markdown += f"- [ ] Task {phase_idx}.{task_idx}: {task}\n"
        
        markdown += f"""
**Success Criteria**:
- All tasks completed
- Success metrics for phase met
- Checkpoint gates passed

**Validation**:
- Unit tests passing (80%+ coverage if new code)
- Integration tests green
- Mypy/ruff clean
- No regressions

---

"""
        day_num = phase_end

    markdown += f"""## Success Metrics

| Metric | Target | Unit |
|--------|--------|------|
| Findings Resolved | {init_config['findings']} | findings |
| Test Pass Rate | >99% | % |
| Code Coverage | ≥80% | % |
| Mypy Errors | 0 | errors |
| Regression | 0 | failures |

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Breaking changes | MEDIUM | Backward compat + extensive testing |
| Integration issues | MEDIUM | Integration tests + staging |
| Performance regression | LOW | Benchmarks before/after |
| Type system issues | LOW | Mypy strict mode enforcement |

## Deliverables

- ✅ Refactored code files (exact list per phase)
- ✅ Test suite (80%+ coverage)
- ✅ Documentation updates
- ✅ Migration guides (if needed)
- ✅ CI enforcement rules

## Team Roles

- **Architect**: Design reviews, phase gates
- **Refactoring Engineer**: Code changes
- **QA Engineer**: Testing, validation
- **Type Safety**: Mypy enforcement
- **Technical Writer**: Documentation

## Effort Estimate

- **Design**: {init_config['weeks']}% of effort
- **Implementation**: {int(60 - init_config['weeks']*5)}% of effort
- **Testing**: {int(30 - init_config['weeks']*5)}% of effort
- **Total**: {init_config['weeks']} week(s)

## Cost Estimate

- Tier 2 rate: ~$0.050/hour
- Estimated effort: {init_config['weeks']*40} hours
- **Total Cost**: ${init_config['cost_est']:.3f}

## Dependencies

**Depends On**:
- Initiative {int(init_id)-1 if int(init_id) > 1 else 'N/A'} (if sequential)

**Enables**:
- Initiative {int(init_id)+1} (if sequential)

## Status

- [ ] Design approved
- [ ] Phase 1 complete
- [ ] Phase 2 complete
- [ ] Phase 3 complete
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Ready for production

---

**Created**: {datetime.now().strftime('%Y-%m-%d')}  
**Owner**: Architecture Team  
**Status**: READY FOR PLANNING
"""
    
    return markdown


def generate_q3_template():
    """Generate Q3 initiatives planning template."""
    template = """# Q3 2026 Initiatives Planning Template

**Quarter**: Q3 2026 (August-October)  
**Total Findings Target**: 35 (Initiatives 4-5)  
**Total Cost Est**: $0.070  
**Total Weeks**: 2

## Initiative Schedule

### Initiative 4: Immutable Context Objects
- **Weeks**: Aug 2-16 (2 weeks)
- **Findings**: 6
- **Cost**: $0.020
- **Status**: Planning

### Initiative 5: Layer Boundary Enforcement
- **Weeks**: Aug 9-23 (2 weeks, parallel with Init 4)
- **Findings**: 23
- **Cost**: $0.050
- **Status**: Planning

### Initiative 6: Type Safety Improvements
- **Weeks**: Aug 16-30 (2 weeks, parallel phase)
- **Findings**: 19
- **Cost**: $0.010 (Tier 1)
- **Status**: Planning

---

## Weekly Breakdown

### Week 1 (Aug 2-8)
- Init 4: Freeze phase (2 days)
- Init 5: Analysis phase (2 days)
- Init 6: Type audit phase (2 days)

### Week 2 (Aug 9-15)
- Init 4: Refactoring phase (2 days)
- Init 5: Refactoring phase (2 days)
- Init 6: Fix implementation (2 days)

### Week 3 (Aug 16-22)
- Init 4: Validation phase (1 day)
- Init 5: Automation phase (1 day)
- Init 6: Validation phase (1 day)

### Week 4+ (Aug 23-31)
- Buffer for overruns
- Prep for Q4 initiatives

---

## Success Criteria

✅ 35 findings resolved  
✅ 1150+ tests passing  
✅ Mypy clean  
✅ Layer violations zero (CI enforced)  
✅ Cost ≤$0.070

---

## Next Steps

1. Finalize Initiative 4-6 task breakdowns (use template)
2. Assign team members to initiatives
3. Setup CI enforcement for layer boundaries
4. Create Q4 planning template
"""
    return template


def main():
    print("📋 Generating Initiative Planning Templates...\n")
    
    # Generate Initiative 2-5 detailed task breakdowns
    for init_id in ["2", "3", "4", "5"]:
        if init_id in INITIATIVES_FULL:
            init_config = INITIATIVES_FULL[init_id]
            template = generate_initiative_template(init_id, init_config)
            
            output_path = PLAN_BASE / f"initiative-{init_id}-tasks.md"
            with open(output_path, "w") as f:
                f.write(template)
            
            print(f"✅ Initiative {init_id}: {init_config['name']}")
            print(f"   Output: initiative-{init_id}-tasks.md")
            print(f"   Findings: {init_config['findings']} | Cost: ${init_config['cost_est']:.3f}\n")
    
    # Generate Q3 template
    q3_template = generate_q3_template()
    q3_path = PLAN_BASE / "q3-initiatives-template.md"
    with open(q3_path, "w") as f:
        f.write(q3_template)
    print(f"✅ Q3 Planning Template: q3-initiatives-template.md\n")
    
    # Summary
    total_findings = sum(INITIATIVES_FULL[iid]["findings"] for iid in ["2", "3", "4", "5"])
    total_cost = sum(INITIATIVES_FULL[iid]["cost_est"] for iid in ["2", "3", "4", "5"])
    
    print("📊 Summary:")
    print(f"   Initiatives: 4 (2, 3, 4, 5)")
    print(f"   Total Findings: {total_findings}")
    print(f"   Total Cost: ${total_cost:.3f}")
    print(f"   Quarter Coverage: Q2-Q3 (8 weeks)")


if __name__ == "__main__":
    main()
