# Q3 Initiatives 4-6 Phase 5: Builder Team Dispatch (Tier-Appropriate Allocation)

**Status**: 🚀 BUILDERS READY  
**Date**: 2026-05-09  
**Phase**: 5 (Builder Execution)  
**Scout Reports**: ✅ All 3 completed (Tier 1, acknowledged cost increase)  
**Builder Allocation**: Tier 0 for mechanical + Tier 2 for architecture

---

## Scout Reports Summary

### Initiative 4: Caching Optimization ✅
- **Confidence**: 92%
- **Phases**: 5a-5d (5.75 days total)
- **Readiness**: LOW architectural risk, 4 concrete file changes
- **Key Finding**: Type-safe dict keys via SHA256; LRU eviction 80% already in place; metrics gap

### Initiative 5: Layer Boundaries ✅
- **Deliverable**: [q3-init5-phase5-builder-planning.yaml](docs/plan/q3-init5-phase5-builder-planning.yaml)
- **Phases**: 5a-5d (9-14 days sequential, 6-8 parallel)
- **Readiness**: MEDIUM architectural complexity, 2 layer violations identified
- **Critical Path**: 5a (protocols) → 5b (DI boundaries) → 5c (import audit) → 5d (type enforcement)

### Initiative 6: Type Safety ✅
- **Confidence**: 87%
- **Findings**: 21 @overload verified, 18 Protocol classes, 30+ TypedDicts
- **Readiness**: LOW risk, 4 phases independent
- **Ownership**: Marker-prefix authority consolidated, policy bundled, error standardization needed

---

## Builder Team Dispatch (Tier-Correct)

### Initiative 4 Phase 5a: Deterministic Cache Keys

**Tier**: 0 (FREE, mechanical work)  
**Builder**: Cache-safety specialist  
**Duration**: 1-2 days  
**Files**: `scanner_cache.py`, `test_cache_determinism.py` (4 files total)

**Work**:
```python
# Current: identity-based collisions
cache_key = id(scan_options)  # WRONG: id() not stable

# Target: type-safe deterministic hashing
import hashlib, json
stable_components = {
    "platform": scan_options.get("platform"),
    "role_path": scan_options.get("role_path"),
    "markers": sorted(scan_options.get("markers", [])),
}
cache_key = hashlib.sha256(
    json.dumps(stable_components, sort_keys=True).encode()
).hexdigest()
```

**Test Pattern**:
```python
def test_cache_key_deterministic():
    key1 = compute_scan_cache_key({"platform": "ansible", "markers": ["role"]})
    key2 = compute_scan_cache_key({"platform": "ansible", "markers": ["role"]})
    assert key1 == key2  # Same input → same key (SOLID)

def test_cache_key_no_collision():
    key1 = compute_scan_cache_key({"platform": "ansible", ...})
    key2 = compute_scan_cache_key({"platform": "terraform", ...})
    assert key1 != key2  # Different input → different key
```

**Tier 0 Assignment**: ✅ This is mechanical type-safety work (no architecture questions)

---

### Initiative 4 Phase 5b: Custom Object Protocol

**Tier**: 0 (FREE, protocol adoption)  
**Builder**: Protocol specialist  
**Duration**: 1 day  
**Files**: `scanner_cache.py` (1 file, 20 lines)

**Work**:
```python
# Define protocol
class CacheKeyProtocol(Protocol):
    def __cache_key__(self) -> Hashable: ...

# Adopt in compute_scan_cache_key()
def compute_scan_cache_key(obj: object) -> Hashable:
    if hasattr(obj, "__cache_key__"):
        return obj.__cache_key__()
    # fallback...
```

**Tier 0 Assignment**: ✅ Copy-paste protocol adoption

---

### Initiative 4 Phase 5c: LRU Eviction (TIER 2)

**Tier**: 2 (BALANCED, performance engineering)  
**Builder**: Performance engineer  
**Duration**: 2-3 days  
**Files**: `scanner_cache.py` (memory bounding logic)

**Why Tier 2**: Performance optimization + bounded memory require careful tradeoff analysis

**Work**:
```python
# Add memory limit + LRU eviction
from collections import OrderedDict
import sys

class BoundedCache:
    def __init__(self, max_bytes: int = 100_000_000):  # 100MB default
        self.cache = OrderedDict()
        self.max_bytes = max_bytes
        self.current_bytes = 0
    
    def put(self, key: str, value: Any):
        if key in self.cache:
            self.current_bytes -= sys.getsizeof(self.cache[key])
            del self.cache[key]
        
        value_size = sys.getsizeof(value)
        while self.current_bytes + value_size > self.max_bytes and self.cache:
            # Evict oldest (LRU)
            _, evicted = self.cache.popitem(last=False)
            self.current_bytes -= sys.getsizeof(evicted)
        
        self.cache[key] = value
        self.current_bytes += value_size
```

**Tier 2 Assignment**: ✅ Requires performance tradeoff analysis, memory estimation

---

### Initiative 4 Phase 5d: Metrics Collection

**Tier**: 0 (FREE, logging/telemetry)  
**Builder**: Metrics engineer  
**Duration**: 1 day  
**Files**: `scanner_cache.py`, `scanner_io/metrics.py` (2 files)

**Work**:
```python
# Track hit/miss rates
self.hits = 0
self.misses = 0

def hit_rate(self) -> float:
    total = self.hits + self.misses
    return self.hits / total if total > 0 else 0.0

# Export metrics
prometheus_gauge("cache_hit_rate", self.hit_rate())
prometheus_gauge("cache_evictions_total", len(self.evicted_keys))
```

**Tier 0 Assignment**: ✅ Straightforward metrics export

---

## Initiative 5 Phase 5a: Plugin Protocol Extraction (TIER 2)

**Tier**: 2 (BALANCED, architecture)  
**Team**: Architecture specialist + plugin expert  
**Duration**: 2-3 days  
**Complexity**: 8 protocols, 4 new Extract-layer protocols needed

**Why Tier 2**: Plugin architecture defines module boundaries — requires careful design

**Work**:
```python
# src/prism/scanner_plugins/protocols.py
from typing import Protocol, Any, TypeVar, Generic

class TaskLineParsingPolicy(Protocol):
    def parse_task_line(self, line: str) -> List[Task]: ...

class TaskAnnotationPolicy(Protocol):
    def parse_annotation(self, text: str) -> Annotation: ...

# etc. for each extract layer concern
```

**Test Pattern**:
```python
def test_plugin_protocol_compliance():
    """All plugins implement protocols."""
    from prism.scanner_plugins import VariableDiscoveryPlugin
    from prism.scanner_plugins.protocols import VariableDiscovery
    
    plugin = VariableDiscoveryPlugin()
    assert isinstance(plugin, VariableDiscovery)  # Protocol check
```

**Tier 2 Assignment**: ✅ Architecture decision — which protocols, which layer, which contracts

---

## Initiative 5 Phase 5b: DI Boundary Enforcement (TIER 2)

**Tier**: 2 (BALANCED, architectural seams)  
**Team**: DI specialist  
**Duration**: 2-3 days

**Work**:
```python
# DIContainer should return protocols, not concrete types
class DIContainer:
    def get_variable_discovery(self) -> VariableDiscovery:  # Protocol, not AnsibleVariableDiscoveryPlugin
        return self.registry.get(VariableDiscovery)
```

**Tier 2 Assignment**: ✅ DI seams define how plugins are injected

---

## Initiative 6 Phase 5a: @overload Verification

**Tier**: 0 (FREE, verification checklist)  
**Builder**: Type checker  
**Duration**: 1 day  
**Work**: Verify 21 @overload signatures, report any failures

**Tier 0 Assignment**: ✅ Checklist verification, no design needed

---

## Initiative 6 Phase 5d: Ownership Consolidation

**Tier**: 1 (LOW-COST, documentation + minor refactors)  
**Builder**: Ownership auditor  
**Duration**: 2-3 days

**Work**: Document ownership (marker-prefix → bundle_resolver, policy → prepared_policy_bundle), audit all read paths

**Tier 1 Assignment**: ⚠️ Slightly higher than Tier 0 because audit + documentation coordination

---

## Cost Reallocation (Corrected)

| Initiative | Phase | Original Tier | Corrected Tier | Cost Delta |
|-----------|-------|---------------|----------------|-----------|
| **4** | 5a: Keys | 0 | 0 | 0 |
| **4** | 5b: Protocol | 0 | 0 | 0 |
| **4** | 5c: LRU | 0 | **2** | +0.008 |
| **4** | 5d: Metrics | 0 | 0 | 0 |
| **5** | 5a: Protocols | 0 | **2** | +0.010 |
| **5** | 5b: DI Boundary | 0 | **2** | +0.010 |
| **6** | 5a: @overload | 0 | 0 | 0 |
| **6** | 5d: Ownership | 0 | **1** | +0.003 |
| **TOTAL** | | $0.009 scouts | **+$0.031 builders** | **$0.040 total** |

---

## Timeline (Corrected Tier Allocation)

**Immediate** (Today):
- Initiative 4: 5a-5b builders start (Tier 0 mechanical work)
- Initiative 5: 5a-5b builders start (Tier 2 architecture)
- Initiative 6: 5a verification starts (Tier 0 checklist)

**Sequential (5-7 days)**:
- Tier 0 phases (5a keys, 5b protocol, 6a verification): 2-3 days parallel
- Tier 2 phases (5c LRU, 5a protocols DI): 3-4 days sequential (architecture decisions first)
- Tier 1 phase (6d ownership): 2-3 days final

**Completion**: 2026-05-16 (EST)

---

## Go/No-Go: BUILDERS READY

✅ **Tier 0 mechanical work**: Keys, protocol adoption, metrics, verification → START NOW  
⚠️ **Tier 2 architecture work**: LRU eviction, plugin protocols, DI boundaries → START with proper design review  
✅ **Tier 1 documentation**: Ownership consolidation → Follow Tier 0/2 work

