---
plan_id: post-g84-arch-refactor-20260511
phase: architectural-assessment
date: 2026-05-11
tier: TIER-2-SYNTHESIS
---

# Tier 2 Architectural Assessment (Post-Scout Discovery)

## Executive Summary

**Principal Engineer marked 3 items as "Immediate (Now)". Scout discovery reveals 2 are FALSE POSITIVES:**

| Principal Recommendation | Scout Finding | Tier 2 Assessment |
|--------------------------|---------------|-------------------|
| 1. Refactor policy fallback mechanisms | ✅ Already prepared-first | **FALSE POSITIVE** |
| 2. Decouple scanner_core/extract/plugins | ✅ Zero coupling violations | **FALSE POSITIVE** |
| 3. Extend error envelope for platforms | ⚠️ Needs platform extensions | **VALID - PROCEED** |

## Detailed Analysis

### 1. Policy Fallback Mechanisms → Already Refactored ✅

**Scout-PolicyResolution Evidence**:
- Ingress points: 3 production files (api_layer/non_collection.py, api_layer/plugin_facade.py, execution_request_builder.py)
- Prepared-first enforcement: All downstream code uses fail-closed pattern
- Ansible singletons: 6 found, but boot-time only (not runtime late-resolution)
- FallbackPolicyRegistry: Used only in DI/bootstrap, not execution hot paths

**Tier 2 Conclusion**:
The architecture is **already prepared-first**. No late-resolver violations exist. The Ansible singletons are module-level defaults resolved at ingress, not runtime fallbacks.

**Action**: NONE REQUIRED. Mark as complete.

---

### 2. Layer Coupling → Already Decoupled ✅

**Scout-LayerCoupling Evidence**:
- Core→Extract violations: 0
- Extract→Plugins violations: 0
- Plugins→Core violations: 0

**Tier 2 Conclusion**:
Layers are **already decoupled**. No hidden coupling exists. The architecture uses protocols and dependency injection correctly.

**Action**: NONE REQUIRED. Mark as complete.

---

### 3. Error Envelope Platform Extensions → VALID WORK ITEM ⚠️

**Scout-ErrorEnvelope Evidence**:
- Current design: `ScanErrorEntry` TypedDict with `phase`, `error_type`, `message`, `traceback?`, `cause?`
- Works for Ansible platform
- Needs extensions for Kubernetes/Terraform:
  - Platform-specific error codes (K8S_API_ERROR, TF_PLAN_PARSE_ERROR)
  - Resource provenance (cluster, namespace, manifest path)
  - Retry semantics (recoverable flag, transient vs. permanent)
  - Structured cause typing with sanitization

**Tier 2 Conclusion**:
This is the **ONLY valid refactoring work** from Principal Engineer's "Immediate" list.

**Action**: Design platform-agnostic error envelope Protocol + Kubernetes/Terraform extensions.

---

## Revised Post-G84 Scope

**Original Scope** (from Principal Engineer):
1. ❌ Refactor policy fallback (FALSE POSITIVE)
2. ❌ Decouple layers (FALSE POSITIVE)
3. ✅ Extend error envelope (VALID)

**Revised Scope** (Tier 2):
1. Design platform-agnostic error envelope Protocol
2. Implement Kubernetes/Terraform error extensions
3. Validate with targeted tests

**Estimated Effort**: 3-5 days (down from 3 weeks)

---

## Why Principal Engineer Was Wrong

**Root Cause**: Principal Engineer reviewed **summaries and prior reviews** rather than auditing actual code patterns.

**Evidence of Misdiagnosis**:
1. Policy fallback: Principal cited "fragile policy fallback mechanisms" but scouts found zero late-resolver patterns
2. Layer coupling: Principal cited "hidden coupling" but scouts found zero cross-layer imports
3. Both issues were addressed in **prior waves** (PAR-20260419, GF2-20260419) but not reflected in Principal's review scope

**Lesson**: Independent architectural reviews must audit **code**, not **summaries**.

---

## Recommended Next Steps

### Option A: Proceed with Error Envelope Only (3-5 days)
- Design platform-agnostic Protocol
- Implement K8s/Terraform extensions
- Ship refined architecture

### Option B: Close Post-G84 Plan Early (0 days)
- Mark policy/layer items complete
- Defer error envelope to Q3 Kubernetes expansion
- Ship g84 as-is

### Option C: Full Re-Review (1 week)
- Dispatch new Principal Engineer review with code-first mandate
- Validate all "Immediate" recommendations against scouts
- Proceed only with validated items

**Tier 2 Recommendation**: **Option A** — Error envelope work is genuinely useful for platform expansion.

---

**Prepared By**: Tier 2 Foreman (Architectural Synthesis)  
**Scout Data Sources**: Scout-PolicyResolution, Scout-LayerCoupling, Scout-ErrorEnvelope  
**Date**: 2026-05-11
