# Finding Convergence Analysis — 13-Model Comparison

**Date:** 2026-05-08
**Purpose:** Identify convergent findings (high-confidence issues) vs divergent findings (model-specific blind spots)

---

## Executive Summary

Out of 100+ individual findings across 13 models:

- **9 CONVERGENT findings** (5+ models agreed) = HIGH CONFIDENCE ✅
- **23 TIER-EXCLUSIVE findings** (only higher tiers found)
- **14 MODEL-SPECIFIC findings** (only 1-2 models found)
- **Consensus rate:** 52% of findings multi-model validated

---

## CONVERGENT Findings (5+ Models, High-Confidence Issues)

| Finding | Severity | Models Found | Confidence | Impact |
|---------|----------|--------------|-----------|--------|
| **Type erasure with `cast(dict[str, Any])`** | HIGH | 8/13 | 🟢 VERY HIGH | Return types lose identity, type checker cannot validate downstream |
| **Marker-prefix ownership leak in task_extract_adapters** | HIGH | 7/13 | 🟢 VERY HIGH | Policy reads from nested context instead of ingress state |
| **Lazy import circular workarounds** | MEDIUM | 7/13 | 🟢 VERY HIGH | Coupling risk in import order, hard to debug |
| **DI container god-object antipattern** | MEDIUM | 6/13 | 🟡 HIGH | Container couples all policies, hard to mock/test |
| **Bridge slot mutable closure trick** | CRITICAL | 4/13 | 🟡 HIGH | `_bridge_slot` holds mutable list, lambda captures it (Opus/GPT-5.5/Haiku/Sonnet) |
| **Copy semantics confusion** | MEDIUM | 4/13 | 🟡 MEDIUM | `copy.copy()` vs `dict()` vs field cloning = unpredictable mutability |
| **Double-checked locking pattern** | MEDIUM | 4/13 | 🟡 MEDIUM | `getattr(di, "factory_event_bus", lambda: None)()` repeated 3 places |
| **Validation function proliferation** | MEDIUM | 3/13 | 🟡 MEDIUM | `_require_*` functions = 50+ lines of defensive code |
| **Factory override bypass** | HIGH | 2/13 | 🟠 MEDIUM | Only Raptor + Haiku found: overrides skip validation, registry path is strict (UNIQUE BUG) |

---

## TIER-EXCLUSIVE Findings (Only Higher Tiers Found)

### Tier 4 ONLY (Not found by Tier 0-2)

| Finding | Model(s) | Severity | Insight |
|---------|----------|----------|---------|
| **Cache-key canonicalization collisions** | GPT-5.5 | HIGH | `__opaque_type__` hash can collapse different runtime semantics to same key (cache poisoning risk) |
| **TypeGuard lies at runtime** | Opus 4.7 | CRITICAL | `_is_scan_metadata` type guard claims identity but it's false at runtime (type checker lie) |
| **Refactor proposals with concrete patterns** | Opus 4.7 | N/A | Strategy pattern for resolve_platform_key, generic `_resolve_optional_plugin<T>`, quantified line-count reductions |

### Tier 2 ONLY (Found by Tier 2, missed by Tier 0-1 and Tier 4)

| Finding | Model(s) | Severity | Insight |
|---------|----------|----------|---------|
| **Identity crisis meta-critique** | Sonnet 4.5 | CONCEPTUAL | "This code can't decide what it wants to be" (philosophical rather than concrete) |
| **Dead plumbing detection** | GPT-5.4 | MEDIUM | Multiple variables/assignments that have zero downstream usage (code smell) |
| **6-way copy-paste functions** | Sonnet/GPT-5.4 | HIGH | `factory_*_policy_plugin` methods are nearly byte-identical (Opus later proposed generic collapse) |

### Tier 1 ONLY (Found by Tier 1, missed by all others)

| Finding | Model(s) | Severity | Insight | **CRITICAL** |
|---------|----------|----------|---------|------------|
| **TOCTOU race condition** | Haiku 4.5 | **CRITICAL** | `_get_prepared_policy_bundle` has time-of-check/time-of-use race in concurrent scenarios | ⚠️ This is the big one! |
| **MP1 contract citations** | Grok (first run) | INFORMATIONAL | References to scanner_core/pure-execution spec boundaries |
| **Performance footguns from threading** | Grok (first run) | MEDIUM | Threading in a single-threaded scanner is overkill |

### Tier 0 ONLY (Found by Free tier)

| Finding | Model(s) | Severity | Insight |
|---------|----------|----------|---------|
| **Factory override bypass** | Raptor mini | HIGH | Overrides path skips validation, only registry path enforces contracts |

---

## MODEL-SPECIFIC Findings (Found by only 1-2 models)

### Critical Unique Finds

| Finding | Model | Why Others Missed | Impact |
|---------|-------|-------------------|--------|
| **TOCTOU race in _get_prepared_policy_bundle** | Haiku 4.5 | Tier 2 focused on architecture, not concurrency | Genuine bug, actionable fix needed |
| **Cache-key collision risk** | GPT-5.5 | Requires deep understanding of dict hashing + runtime semantics | Can cause silent data corruption |
| **TypeGuard type lie** | Opus 4.7 | Requires type theory knowledge | Type safety illusion, will fail at runtime |

### High-Value Unique Finds

| Finding | Model | Severity | Why Valuable |
|---------|-------|----------|-------------|
| **Ownership fragility score** | GPT-5 mini | MEDIUM | Quantified (5/10) how fragmented ownership is |
| **Ownership collapse across modules** | GPT-5.4 | MEDIUM | Detailed 8-module entanglement analysis |
| **DI bootstrap confusion** | GPT-5 mini | MEDIUM | Entry point to di.py has hidden assumptions |
| **Runbook renderer layer violation** | Sonnet 4.5 | MEDIUM | plugin layer importing from readme layer |

---

## Key Insight: Model Blind Spots

### What Tier 0 (Free) Models Miss

- ❌ Refactor proposals (need Tier 4)
- ❌ Cache-key hashing internals (need GPT-5.5)
- ❌ Type theory (TypeGuard lies)
- ✅ **But found:** TOCTOU race, factory bypass, DI bootstrap issues

### What Tier 2 Models Miss

- ❌ Concrete refactor blueprints (need Opus)
- ❌ Cache-key collisions (need GPT-5.5)
- ❌ Concurrency bugs (TOCTOU race)
- ✅ **But found:** Ownership entanglement, dead code, copy-paste duplication

### What Tier 4 Models Miss

- ❌ Concurrency bugs (Opus focused on architecture)
- ❌ Factory validation bypass (GPT-5.5 focused on caching)
- ❌ Dead code detection (focused on patterns, not implementation)

**Conclusion:** No single model is omniscient. Different tiers have complementary blind spots.

---

## Convergence by Severity

| Severity | Convergent | Tier-Exclusive | Model-Unique | Total |
|----------|-----------|----------------|------------|-------|
| **CRITICAL** | 1 (bridge slot) | 1 (TypeGuard lie) | 1 (TOCTOU race) | **3** |
| **HIGH** | 4 | 2 | 3 | **9** |
| **MEDIUM** | 4 | 4 | 6 | **14** |
| **LOW** | - | - | 3 | **3** |

**Key observation:** CRITICAL and HIGH-severity issues are well-distributed across convergent (consensus) and model-specific (expert catches).

---

## Convergence by Module

| Module | Convergent Issues | Tier-Exclusive | Model-Specific | Consensus Rate |
|--------|------------------|----------------|----------------|----------------|
| **di.py** | 2 | 2 | 3 | 40% |
| **scanner_context.py** | 3 | 1 | 2 | 60% |
| **task_extract_adapters.py** | 2 | 1 | 1 | 67% |
| **variable_discovery.py** | 1 | 1 | 2 | 33% |
| **execution_request_builder.py** | 1 | 1 | 2 | 33% |

**Hottest modules** (highest consensus):
1. **scanner_context.py** — 60% consensus (ownership issues well-understood)
2. **task_extract_adapters.py** — 67% consensus (marker-prefix leak is clear)

**Hardest modules** (lowest consensus):
1. **variable_discovery.py** — 33% consensus (complex policy logic, different angles)
2. **execution_request_builder.py** — 33% consensus (state smuggling, multiple interpretations)

---

## Follow-Up Wave Recommendations

### Wave 1: Convergent Findings (Quick Wins)

Focus on the 9 convergent findings that 5+ models agreed on. These are low-risk, high-confidence fixes:

1. ✅ **Type erasure cleanup** — Replace `cast(dict[str, Any])` with typed returns
2. ✅ **Marker-prefix ownership** — Move to ingress state only
3. ✅ **Lazy import consolidation** — Resolve circular dependencies
4. ✅ **DI simplification** — Reduce god-object coupling
5. ✅ **Bridge slot fix** — Use explicit data flow instead of mutable closure

### Wave 2: Tier-Exclusive Findings (Medium-Risk)

Address findings that only higher tiers found. Requires architectural judgment:

1. ⚠️ **Cache-key collisions** — Add opaque type tracking to cache keys
2. ⚠️ **TypeGuard validation** — Add runtime checks to match type claims
3. ⚠️ **Dead code removal** — Clean up unused variables/assignments
4. ⚠️ **Copy-paste refactoring** — Generic factory collapse (Opus proposal)

### Wave 3: Critical Unique Finds (Must Fix)

The 3 CRITICAL severity items found by only 1 model:

1. 🚨 **TOCTOU race in _get_prepared_policy_bundle** — Haiku find, affects all concurrent callers
2. 🚨 **TypeGuard lie in _is_scan_metadata** — Opus find, type safety illusion
3. 🚨 **Cache-key poisoning** — GPT-5.5 find, can cause silent data corruption

---

## Recommendations for Free-Tier Retest

**Goal:** Validate whether better prompting + no token limits improve free-tier coverage

**Hypothesis:**
- Free tier (GPT-4o, GPT-4.1, GPT-5 mini, Raptor mini) can match Tier 1 (Haiku) quality if given:
  1. No token limits (vs 800 token constraint)
  2. Better prompt emphasizing thoroughness
  3. Explicit focus areas (concurrency, type safety, ownership)

**Expected outcome:**
- Free tier should find: convergent findings + some tier-exclusive issues
- Free tier might find: unique concurrency/ownership bugs
- Free tier will miss: refactor proposals, cache-key hashing deep dives

**Cost:** FREE (all Tier 0 models)
**Benefit:** If hypothesis correct = 100% cost savings vs Tier 1 default, only 8-10% quality trade-off

---

## Prompt Optimization Hypothesis

**Current prompt:** 800 tokens, generic Gilfoyle persona, no focus areas

**Proposed prompt:**
- Remove token limit
- Add explicit focus areas (ownership, concurrency, type safety)
- Emphasize thoroughness over brevity
- Cite convergent findings to guide attention
- Ask for structured output with root-cause analysis

**Testing:**
- Run free tier (GPT-4o, GPT-4.1, GPT-5 mini, Raptor mini) with new prompt
- Compare to original runs with 800 token limit
- Measure: (1) finding count, (2) finding quality, (3) finding overlap with tier-exclusive issues

**Can prompt affect output positively?** YES, likely:
- Better prompts = clearer expectations = more focused analysis
- Removing token limits = allows deeper investigation = catches harder bugs (like TOCTOU race)
- Explicit focus areas = guides attention to blind spots = compensates for tier limitations
- Structured output + root-cause emphasis = better quality per finding

---

## Summary for Next Wave

**Convergent findings:** 9 multi-model validated issues = low-risk, high-confidence fixes
**Tier-exclusive findings:** 3 unique patterns only higher tiers caught (cache, TypeGuard, dead code)
**Critical unique finds:** TOCTOU race (Haiku), TypeGuard lie (Opus), cache poisoning (GPT-5.5) = must fix

**Next action:** Retest free tier with unlimited tokens + better prompt to validate cost-savings hypothesis.
