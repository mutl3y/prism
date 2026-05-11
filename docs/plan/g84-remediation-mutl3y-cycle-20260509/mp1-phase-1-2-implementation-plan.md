# MP1 Marker-Prefix Enforcement: 2-Phase Implementation Plan

**Scout Role**: MP1ImplementationStrategy  
**Initiative**: Q2 Initiative 3  
**Scope**: Phased rollout of marker-prefix ingress ownership enforcement  
**Tier Selected**: Tier 0 (FREE) — Scout discovery task, audit clean, boundaries locked  
**Tier Reason**: Default tier for phase planning; no escalation criteria met

---

## Executive Summary

MP1 enforcement hardens marker-prefix ownership to ingress-only, eliminating dynamic late-resolver fallback paths. This plan sequences implementation across 2 phases (1-2 weeks):

- **Phase 1**: CI validation, audit enforcement, test gating (Week 1)
- **Phase 2**: Plugin hardening, full distribution rollout (Week 2)

Key risk mitigation: audit-first, test-gating, phased rollout per subsystem, rollback markers at each phase boundary.

---

## Phase 1: Audit, CI Setup & Validation (Days 1-5, Week 1)

### Goals
- Lock marker-prefix ingress ownership via CI enforcement
- Establish audit baseline and validation gates
- Ensure scanner_core, scanner_extract, scanner_io all validate ingress paths
- Add test coverage for marker-prefix flow validation

### Tasks

#### 1.1 Audit Baseline (Day 1-2)
**Objective**: Verify MP1 audit findings and establish clean state

**Tasks**:
- [ ] Run full marker-prefix audit across codebase (rgrep for `DEFAULT_DOC_MARKER_PREFIX`, fallback patterns, late resolution)
- [ ] Verify scanner_core has NO hardcoded marker defaults (expect `frozenset()` or explicit `prepared_policy_bundle` only)
- [ ] Verify scanner_extract delegates all marker-prefix to `scan_request` → `prepared_policy_bundle`
- [ ] Check scanner_io output module for any marker-prefix resolution (expect none outside prepared_policy)
- [ ] Verify all plugin layer (scanner_plugins/*) accesses marker-prefix only via `prepared_policy_bundle`
- [ ] Document all 7 canonical ingress paths (scan_request normalization, policy context, CLI default, API projection, config file, plugin init, DI factory)
- [ ] Baseline metrics: line count of late-resolver code, count of fallback invocations (target: 0)

**Deliverable**: `audit_baseline_mp1_20260509.json` with violation count and ingress path verification

#### 1.2 CI Enforcement Setup (Day 2-3)
**Objective**: Automate marker-prefix ownership validation in CI

**Tasks**:
- [ ] Add ruff rule: no bare `DEFAULT_DOC_MARKER_PREFIX` in scanner_core, scanner_extract (allowlist: scanner_data/defaults, scanner_readme/guide.py, CLI help)
- [ ] Add ruff rule: no `getattr(..., "comment_doc_marker_prefix", ...)` late resolution outside allowlisted modules (allowlist: tests only)
- [ ] Add ruff rule: all scanner_* module functions that return or accept marker-prefix strings must import/use only from `prepared_policy_bundle` types
- [ ] Create `.pre-commit-hook.yaml` for ruff rules; add to tox lint env
- [ ] Create GitHub Actions job: `lint-mp1-marker-ownership` (runs ruff MP1 rules, blocks PR if violations)
- [ ] Verify tox lint pipeline includes new MP1 rules
- [ ] Test CI enforcement: seed a violation in scanner_core, confirm ruff catch

**Deliverable**: `.pre-commit-config.yaml` with MP1 rules, GitHub Actions workflow YAML, passing lint run

#### 1.3 Test Gating (Day 3-4)
**Objective**: Add tests that fail if marker-prefix ownership is violated

**Tasks**:
- [ ] Create `test_mp1_marker_prefix_ingress_ownership.py` with 5 test cases:
  - **Test A**: Verify scanner_core does not access `comment_doc_marker_prefix` directly; only via prepared_policy_bundle
  - **Test B**: Verify scanner_extract delegates all marker-prefix to scan_request (mock prepared_policy_bundle)
  - **Test C**: Verify scanner_io output module does not define/resolve marker-prefix; only consumes from context
  - **Test D**: Verify API and CLI entry points project marker-prefix into prepared_policy_bundle (use audit trace)
  - **Test E**: Verify plugin layer cannot override marker-prefix ownership; only reads from policy bundle
- [ ] Add test fixtures for all 7 ingress paths (scan_request, policy_context, CLI, API, config, plugin init, DI)
- [ ] Add negative test: inject late-resolver call, confirm test catches it
- [ ] Add test run to tox full suite; mark as `pytest.mark.mp1_blocking` (fail = CI red)
- [ ] Run full test suite; confirm baseline PASS

**Deliverable**: `test_mp1_marker_prefix_ingress_ownership.py` (5 tests, all passing), tox config updated

#### 1.4 Marker-Prefix Flow Validation (Day 4-5)
**Objective**: Document and validate canonical ingress flow

**Tasks**:
- [ ] Create visual flow diagram: CLI input → scan_request normalization → prepared_policy_bundle → scanner_core/extract/io
- [ ] Create compliance matrix: each scanner_* subsystem (core, extract, io, plugins, readme) vs. marker-prefix access pattern
  - Expected: all subsystems read-only from prepared_policy_bundle, no write/override
  - Row = subsystem, Column = (ingress paths, resolution method, violations count)
- [ ] Verify all 7 ingress paths route through scan_request or prepared_policy_bundle (no backdoors)
- [ ] Run audit trace: follow marker-prefix from CLI all the way to output; confirm no uncontrolled resolution
- [ ] Document any remaining gray zones (e.g., test fixtures, mocks) in allowlist with rationale

**Deliverable**: MP1_ingress_flow_diagram.md, compliance_matrix.yaml, audit_trace_log.md

#### 1.5 Documentation & Rollback Prep (Day 5)
**Objective**: Lock Phase 1 state; prepare rollback points

**Tasks**:
- [ ] Document Phase 1 state: audit clean, CI enforced, tests gating, ingress flow validated
- [ ] Create rollback marker: `git tag mp1-phase1-checkpoint-20260509`
- [ ] Create rollback procedure: if Phase 1 fails CI, run `git reset --hard mp1-phase1-checkpoint-20260509`
- [ ] Update tox configuration to include all Phase 1 gates: lint, audit, tests
- [ ] Create Phase 1 sign-off checklist (5 items); confirm all PASS

**Deliverable**: Phase 1 checkpoint tag, rollback procedure document, sign-off checklist (all items ✅)

---

## Phase 2: Plugin Hardening & Distribution Rollout (Days 6-10, Week 2)

### Goals
- Harden plugin system to enforce marker-prefix from policy bundle only
- Enforce no plugin can inject marker-prefix at runtime
- Rollout to distributed scanner instances
- Final validation and metrics

### Tasks

#### 2.1 Plugin Layer Hardening (Day 6-7)
**Objective**: Lock plugin access to marker-prefix; prevent injection

**Tasks**:
- [ ] Audit `scanner_plugins/defaults.py` and all resolver functions for marker-prefix access
- [ ] Add `@requires_prepared_policy_bundle` decorator to all plugin factory methods (verify prepared_policy_bundle arg is present, fail-closed if missing)
- [ ] Remove or inline any plugin factory function that accepts or injects marker-prefix as independent kwarg
- [ ] Create `scanner_plugins/marker_prefix_policy.py`: single source for marker-prefix access in plugin layer
  - Export `get_marker_prefix_from_policy(di: DIContainer) -> str` 
  - Fail-closed if prepared_policy_bundle missing
- [ ] Update all plugin init code (Ansible, Kubernetes, Terraform) to use canonical getter
- [ ] Add test: mock prepared_policy_bundle removal, confirm plugin init fails loudly (not silent fallback)
- [ ] Verify no plugin can initialize without prepared_policy_bundle

**Deliverable**: Plugin hardening implementation, canonical getter, tests passing (no silent fallbacks)

#### 2.2 Runtime Enforcement (Day 7-8)
**Objective**: Add runtime assertions to catch any marker-prefix override attempts

**Tasks**:
- [ ] Add runtime assertion in scanner_core hot path: before task extraction, assert `prepared_policy_bundle.comment_doc_marker_prefix == scan_request.comment_doc_marker_prefix` (or None)
- [ ] If assertion fails, log CRITICAL error with context, fail-closed (do not proceed)
- [ ] Add metric: counter for assertion failures (expect 0 in production)
- [ ] Add test: inject prepared_policy_bundle with different marker-prefix than scan_request, confirm assertion catches it
- [ ] Add test: mock plugin attempt to override marker-prefix at runtime, confirm scanner rejects with error
- [ ] Document assertion in scanner_core docstring: why it exists, what it prevents

**Deliverable**: Runtime assertions in place, counter metrics, 2 edge-case tests passing

#### 2.3 Scanner Compatibility Layer Validation (Day 8)
**Objective**: Verify scanner distribution points enforce marker-prefix ownership

**Tasks**:
- [ ] Test `api.py` marker-prefix flow: CLI call → API layer → scan_request projection
  - Verify API never overrides marker-prefix from prepared_policy
- [ ] Test `cli.py` marker-prefix flow: CLI args → scan_request normalization
  - Verify CLI validates marker-prefix input (not None, valid format, max length)
- [ ] Test `repo_services.py` marker-prefix flow: orchestration layer
  - Verify repo_services passes prepared_policy_bundle unchanged to scanner_core
- [ ] Create integration test: end-to-end CLI → scanner_core → output with marker-prefix validation at each step
- [ ] Verify no compatibility layer can inject marker-prefix outside canonical paths
- [ ] Run full integration test suite; confirm all passing

**Deliverable**: Integration tests passing, compatibility layer marker-prefix flow validated

#### 2.4 Distribution Rollout (Day 9)
**Objective**: Deploy MP1 enforcement to distributed scanner instances

**Tasks**:
- [ ] Create rollout checklist: all Phase 1 checks passing? Phase 2 tests passing? Plugin hardening complete?
- [ ] Stage rollout: deploy to internal instances first (prism-learn, development instances)
  - Run smoke test: scan a known repo, verify marker-prefix is ingress-owned
  - Verify metrics: 0 assertion failures, 0 late-resolver invocations
  - Check logs: no CRITICAL errors, no fallback warnings
- [ ] If smoke PASS: deploy to next tier (staging instances)
  - Run same smoke test
  - Monitor for 1-2 hours: any regressions?
- [ ] If staging PASS: deploy to production instances
  - Phased: 25% → 50% → 75% → 100% canary rollout
  - Monitor error rate and marker-prefix metrics at each step
- [ ] Create rollback plan: if any step fails, revert to mp1-phase1-checkpoint-20260509
- [ ] Verify distributed instances all report: marker-prefix ownership enforced, 0 violations

**Deliverable**: Rollout checklist (PASS), smoke test results, metrics from all tiers, no regressions

#### 2.5 Monitoring & Final Validation (Day 9-10)
**Objective**: Confirm MP1 enforcement stable in production; document lessons

**Tasks**:
- [ ] Add production monitoring: daily count of marker-prefix override attempts (expect 0)
- [ ] Set alert: if marker-prefix override attempt > 0 in 24h, page on-call
- [ ] Create dashboard: marker-prefix ownership metrics (assertion passes, late-resolver calls, ingress paths used)
- [ ] Run final audit: confirm 0 violations across all scanner_* subsystems
- [ ] Document lessons learned: what worked, what was risky, how to avoid in future phases
- [ ] Update MP1 specification with final state: marker-prefix is 100% ingress-owned, no exceptions
- [ ] Create follow-up plan: K8s/Terraform expansion unblocked

**Deliverable**: Monitoring alerts configured, dashboard live, final audit (0 violations), lessons doc

#### 2.6 Release & Rollback Prep (Day 10)
**Objective**: Lock Phase 2 state; prepare future rollback

**Tasks**:
- [ ] Create rollback marker: `git tag mp1-phase2-final-20260510`
- [ ] Create release notes: MP1 enforcement complete, marker-prefix is ingress-owned
- [ ] Update AGENTS.md: MP1 closure with final date and metrics
- [ ] Update README: document marker-prefix ownership contract for future developers
- [ ] Create runbook: if production issue → how to rollback MP1 (revert to phase1 checkpoint, then investigate)
- [ ] Schedule post-mortem if any Phase 2 issues; otherwise mark initiative complete

**Deliverable**: Release tag, release notes, updated docs, runbook

---

## Risk Mitigation Strategy

### Risk 1: CI Enforcement Too Strict (False Positives)
**Impact**: Blocks legitimate code, slows development  
**Mitigation**:
- Extensive allowlist in ruff rules for known edge cases (test fixtures, mocks)
- Dry-run Phase 1 ruff rules on current codebase before enabling CI block
- If violations found, investigate first before tightening rule (may need code refactor, not allowlist)
- Escalation: if >5 violations found, audit audit itself; escalate to Tier 1 review

### Risk 2: Plugin Layer Injection Backdoor Discovered
**Impact**: MP1 enforcement bypass, security hole  
**Mitigation**:
- Comprehensive Phase 2.1 plugin audit before runtime enforcement
- Add negative tests: attempt every known injection pattern, confirm blocked
- If injection found: pause Phase 2, escalate to Tier 2 architecture review, refactor injection vector
- Rollback to phase1 checkpoint, re-audit plugin layer

### Risk 3: Distributed Instances Incompatible with MP1
**Impact**: Scanner breaks on customer systems  
**Mitigation**:
- Phased canary rollout: internal → staging → 25%→50%→75%→100% production
- Smoke tests at each step; any regression → immediate rollback
- Monitor metrics in real-time; if override attempts spike, rollback
- Runbook prepared before rollout; on-call aware

### Risk 4: Existing Code Violates MP1 Boundary
**Impact**: Refactoring needed mid-phase  
**Mitigation**:
- Phase 1.1 audit is comprehensive; expect to find violations
- If violations found: prioritize refactoring before Phase 2
- Update timeline: add 1-2 days for refactoring if needed
- Create task list in Phase 1.5; escalate to Phase 2 if still open

### Risk 5: Timeline Overrun (1-2 weeks becomes 3-4 weeks)
**Impact**: Initiative delay, Q2 goals slip  
**Mitigation**:
- Strict day-by-day gating; if any day overruns, escalate to Tier 1 review
- If Phase 1 not done by end Day 5, pause Phase 2, replan
- Prioritize: audit → CI setup → tests (defer monitoring to after rollout if needed)
- Plan backup: Tier 1 fast-track available for unblocking decisions

---

## Rollback Plan

### Level 1: Phase 1 Rollback (Days 1-5)
**Trigger**: Phase 1 gate not passing by end Day 5, or audit finds >10 violations

**Rollback**:
```bash
git reset --hard HEAD
# No release tag yet; nothing deployed
# Escalate to Tier 1: re-audit, refactor code if needed
```

**Outcome**: Restart Phase 1 with refactored code or clarified audit

### Level 2: Phase 2 Early Rollback (Days 6-8)
**Trigger**: Plugin hardening finds >5 injection vectors, or runtime assertions failing in tests

**Rollback**:
```bash
git checkout mp1-phase1-checkpoint-20260509
git revert mp1-phase2-commits  # Revert Phase 2 commits
# Phase 1 stays in place; Phase 2 gets re-designed
```

**Outcome**: Phase 1 enforcement active; Phase 2 re-planned with root-cause fix

### Level 3: Canary Rollback (Day 9, Staging Phase)
**Trigger**: Smoke test fails at staging, or metrics show violations

**Rollback**:
```bash
git checkout mp1-phase1-checkpoint-20260509
# Redeploy from Phase 1 final state
# Run smoke test to confirm Phase 1 still works
```

**Outcome**: Back to Phase 1 enforcement; Phase 2 issues investigated before retry

### Level 4: Production Rollback (Day 9-10, Canary or Full)
**Trigger**: Any tier (25%, 50%, 75%, 100%) shows override attempts or errors

**Rollback**:
```bash
# Immediate: roll back canary tier to mp1-phase1-checkpoint-20260509
# Wait: monitor for 1 hour, confirm no errors
# If errors > 0: roll back all tiers
```

**Outcome**: Full rollback to Phase 1; post-mortem scheduled

### Post-Rollback Recovery
1. Root-cause analysis (Tier 1 review)
2. Code refactoring or design change
3. Restart at Phase 1 checkpoint (not day 1)

---

## Timeline: 2-Week Execution Plan

**Week 1 (May 9-15, 2026): Phase 1**
- Day 1-2: Audit baseline, document violations
- Day 2-3: CI setup, ruff rules, GitHub Actions
- Day 3-4: Test gating (5 tests), negative tests
- Day 4-5: Flow validation, ingress audit, rollback prep
- **Gate**: All Phase 1 checks PASS, tag phase1-checkpoint

**Week 2 (May 16-22, 2026): Phase 2**
- Day 6-7: Plugin hardening, canonical getter, decorator
- Day 7-8: Runtime assertions, edge-case tests
- Day 8: Compatibility layer validation (integration tests)
- Day 9: Smoke tests, canary rollout (internal → staging → 25%)
- Day 10: Final monitoring, release notes, runbook
- **Gate**: All Phase 2 checks PASS, tag phase2-final, release

**Checkpoints**:
- EOD Day 5: Phase 1 complete, ready for Phase 2 start
- EOD Day 8: Phase 2 tech complete, ready for rollout
- EOD Day 10: Phase 2 complete, MP1 live in production

---

## Dependencies: Initiative 2 Requirements

### Required from Initiative 2:
1. **PolicyManager** (DI factory)
   - `prepared_policy_bundle` must be available in DI container
   - MP1 relies on this being injected at ingress (scan_request, API, CLI)
   - **Status**: Assume Initiative 2 complete (audit clean, boundaries locked per user)

2. **DIContainer** (Dependency Injection)
   - `di.factory_prepared_policy_bundle()` must exist
   - MP1 runtime assertions depend on DI providing prepared_policy_bundle
   - **Status**: Assume Initiative 2 complete

3. **Prepared Policy Bundle Contract** (ScanRequest → PreparedPolicyBundle)
   - `prepared_policy_bundle.comment_doc_marker_prefix` must be defined
   - MP1 ingress paths route through this
   - **Status**: Assume Initiative 2 complete (per user: boundaries locked)

### MP1 Does NOT Wait For:
- Kubernetes platform expansion (separate Q3 initiative)
- Terraform platform expansion (separate Q3 initiative)
- Additional marker-prefix use cases (MP2 future work)

**Blocking Status**: ✅ UNBLOCKED — Initiative 2 complete, MP1 can proceed

---

## Sign-Off Checklist

**Phase 1 (Week 1)**:
- [ ] Audit baseline clean (0-5 violations documented)
- [ ] CI enforcement active (ruff rules, GitHub Actions)
- [ ] 5 MP1 tests passing, negative tests passing
- [ ] Ingress flow audit complete, no backdoors
- [ ] Phase 1 checkpoint tag created

**Phase 2 (Week 2)**:
- [ ] Plugin hardening complete, no injection vectors
- [ ] Runtime assertions in place, edge tests passing
- [ ] Compatibility layer tests passing
- [ ] Canary rollout complete (100% production)
- [ ] 0 violations in production, alerts configured
- [ ] Phase 2 final tag created, release notes published

**Initiative Complete**: Both checklists ✅ → MP1 LIVE, Q2 Initiative 3 DONE

---

## Metrics & Success Criteria

| Metric | Target | Timeline |
|--------|--------|----------|
| Audit violations | 0 | End Phase 1 |
| MP1 tests passing | 5/5 + negative tests | End Phase 1 |
| Plugin injection vectors | 0 | End Phase 2 |
| Runtime assertion failures | 0 | EOD Phase 2 + 1 week monitor |
| Production rollout status | 100% | End Phase 2 |
| Mean-time-to-rollback (MTTR) | <5 min | Runbook documented |

---

## Appendix: Contingency Paths

### If Timeline Slips to 3 Weeks:
- Phase 1: keep 5 days (hard deadline)
- Phase 2: extend to 10 days (add Day 5.5-6 for refactoring if audit finds violations)
- Revisit EOD Day 5: if violations > 10, escalate to Tier 1, replan Phase 2

### If Injection Vectors Found in Phase 2:
- Pause Phase 2, escalate to Tier 2 architecture review
- Redesign plugin layer with static analysis guards
- Restart Phase 2 with refactored code

### If Production Rollout Fails:
- Immediate rollback to Phase 1 checkpoint
- Post-mortem with Tier 1 review
- Root-cause fix, restart Phase 2 (not day 1, from checkpoint)

---

**Next Step**: Execute Phase 1 (Day 1: Audit baseline) starting May 9, 2026.

