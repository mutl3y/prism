---
plan_id: multi-platform-scanner-q3-implementation
initiative: "Q3 Initiative 7: Multi-Platform Scanner Expansion"
created_at: "2026-05-11"
status: "planning"
---

# Multi-Platform Scanner Implementation Plan

**Objective**: Implement Kubernetes and Terraform scanner plugins using unified error envelope and plugin-registry architecture.

**Timeline**: Q3 2026 (8-10 weeks estimated)  
**Dependencies**: ✅ Error envelope implementation complete (Phases 1-3)

---

## Overview: Plugin Architecture

All platform plugins follow the same pattern:

1. **Plugin Registry**: Central plugin discovery and loading
2. **Error Adapter**: Platform-specific error classification and detail building
3. **Mock Implementation**: Demo/test plugin with documented expected behavior
4. **Real Implementation**: Full scanner with live platform integration

### Unified Interfaces

All plugins share:
- **Error codes**: Platform-specific enum (K8S_*, TF_*, ANSIBLE_*)
- **Error detail structure**: Unified provenance (file, line, resource ID)
- **Error categories**: Shared taxonomy (runtime, io, parser, api, auth)
- **ScannerContext integration**: Same `_record_phase_error()` pattern

---

## Phase 1: Kubernetes Scanner (Weeks 1-2)

### Current State
- ✅ Mock plugin created: `scanner_plugins/kubernetes/mock.py`
- ✅ Error adapter stub: `scanner_plugins/kubernetes/error_adapter.py`
- ✅ Error codes planned: 10 codes across 5 categories

### Deliverables

#### 1.1 K8s Error Adapter Implementation

**File**: `src/prism/scanner_plugins/kubernetes/error_adapter.py`

Replace the stub with full implementation:

```python
# Key functions to implement:
def build_k8s_error_detail(
    manifest_context: dict[str, Any],
    exception: Exception,
) -> dict[str, Any]:
    """Build K8s error detail with unified provenance."""
    # Extract: cluster, namespace, kind, name, manifest_path, line_number
    # Match Ansible pattern: task_file + line_number + resource_id

def classify_k8s_error(exception: Exception) -> tuple[str, str, bool]:
    """Classify K8s exception to (error_code, category, recoverable)."""
    # Map: APIError → K8S_API_ERROR (api, non-recoverable)
    # Map: AuthException → K8S_AUTH_ERROR (auth, non-recoverable)
    # Map: TimeoutError → K8S_TIMEOUT (io, recoverable)
    # etc.
```

**Test Coverage**:
- 15+ exception scenarios (API errors, auth, timeouts, manifest parsing, etc.)
- Detail structure validation (all required fields present)
- Error code validation (all codes in taxonomy)
- Recoverable flag correctness (transient vs. permanent)

#### 1.2 K8s Manifest Parser

**File**: `src/prism/scanner_plugins/kubernetes/manifest_parser.py` (NEW)

Basic manifest parsing:

```python
class K8sManifestParser:
    """Parse Kubernetes YAML manifests."""
    
    def parse_manifest(manifest_path: str) -> list[dict]:
        """Parse YAML manifest, return list of resources."""
        # Return: [{"kind": "Pod", "name": "...", "line": 1, ...}, ...]
    
    def validate_manifest(manifest: dict) -> bool:
        """Check manifest has required fields."""
        # Validate: apiVersion, kind, metadata.name
```

**Test Coverage**:
- Valid manifests (Pod, Deployment, Service, StatefulSet, etc.)
- Invalid YAML (syntax errors)
- Missing required fields
- Line number accuracy

#### 1.3 Basic K8s Scanner

**File**: `src/prism/scanner_plugins/kubernetes/scanner.py` (NEW)

Mock → real transition:

```python
class KubernetesScanner:
    """Real Kubernetes scanner (Phase 1: mock cluster support)."""
    
    def scan_manifests(self, paths: list[str]) -> ScanResult:
        """Scan local K8s manifests (no cluster access yet)."""
        # Phase 1: Parse + validate local manifests
        # Phase 2 (future): Connect to live cluster, validate against running state
    
    def scan_cluster(self, cluster_config: dict) -> ScanResult:
        """Scan live K8s cluster (Phase 2+)."""
        raise NotImplementedError("Phase 2 implementation")
```

#### 1.4 K8s Error Codes

**File**: `src/prism/scanner_plugins/kubernetes/error_codes.py` (NEW)

Define 10 error codes:

```python
# API & connectivity
K8S_API_ERROR = "K8S_API_ERROR"               # api, non-recoverable
K8S_CONNECTION_ERROR = "K8S_CONNECTION_ERROR" # io, recoverable
K8S_TIMEOUT = "K8S_TIMEOUT"                   # io, recoverable

# Authentication & authorization
K8S_AUTH_ERROR = "K8S_AUTH_ERROR"             # auth, non-recoverable
K8S_PERMISSION_DENIED = "K8S_PERMISSION_DENIED" # auth, non-recoverable

# Parsing & validation
K8S_MANIFEST_PARSE_ERROR = "K8S_MANIFEST_PARSE_ERROR" # parser, non-recoverable
K8S_INVALID_MANIFEST = "K8S_INVALID_MANIFEST" # parser, non-recoverable

# Resource operations
K8S_RESOURCE_NOT_FOUND = "K8S_RESOURCE_NOT_FOUND"     # api, non-recoverable
K8S_RESOURCE_CONFLICT = "K8S_RESOURCE_CONFLICT"       # api, recoverable
K8S_QUOTA_EXCEEDED = "K8S_QUOTA_EXCEEDED"             # api, non-recoverable
```

Add to `scanner_plugins/error_taxonomy.py`:

```python
# Add to ERROR_CODE_CATEGORY_MAP:
"K8S_API_ERROR": ErrorCategory.API,
"K8S_CONNECTION_ERROR": ErrorCategory.IO,
# ... etc
```

### Phase 1 Success Criteria
- ✅ Manifest parser working (10+ manifests tested)
- ✅ Error adapter classifies 15+ exception scenarios
- ✅ Error codes in taxonomy, all mapped to categories
- ✅ `build_k8s_error_detail()` returns complete provenance (manifest_path, line_number, resource_name)
- ✅ 30+ new tests pass (manifest parsing + error classification)
- ✅ pytest suite: 1369+ pass baseline maintained

---

## Phase 2: Terraform Scanner (Weeks 3-4)

### Implementation Pattern

Mirror K8s Phase 1 exactly, but for Terraform:

#### 2.1 Terraform Error Adapter

**File**: `src/prism/scanner_plugins/terraform/error_adapter.py`

#### 2.2 HCL Configuration Parser

**File**: `src/prism/scanner_plugins/terraform/config_parser.py` (NEW)

```python
class TerraformConfigParser:
    """Parse Terraform .tf and .tfvars files."""
    
    def parse_config(plan_path: str) -> list[dict]:
        """Parse HCL, return resources with line numbers."""
    
    def parse_plan(plan_json: str) -> dict:
        """Parse Terraform plan JSON output."""
```

**Note**: HCL parsing is complex. Options:
- Use `python-hcl2` library (HCL2 parser)
- Use `lark` or `pyparsing` for custom HCL1 subset
- Use `python-hcl` (older, HCL1 only)
- Fallback: Basic regex-based parsing (limited but sufficient for Phase 1)

Recommendation: **Use `python-hcl2`** (most maintained, standard Terraform format)

#### 2.3 Basic Terraform Scanner

**File**: `src/prism/scanner_plugins/terraform/scanner.py` (NEW)

```python
class TerraformScanner:
    """Real Terraform scanner (Phase 2: local config analysis)."""
    
    def scan_configs(self, paths: list[str]) -> ScanResult:
        """Scan local .tf configuration files."""
        # Phase 2: Parse + validate local configs
        # Phase 3 (future): Run terraform plan, analyze live state
```

#### 2.4 Terraform Error Codes

**File**: `src/prism/scanner_plugins/terraform/error_codes.py` (NEW)

Define 10 error codes (similar structure to K8s):

```python
# Parsing & validation
TF_PLAN_PARSE_ERROR = "TF_PLAN_PARSE_ERROR"         # parser, non-recoverable
TF_VALIDATION_ERROR = "TF_VALIDATION_ERROR"         # parser, non-recoverable

# Provider & authentication
TF_PROVIDER_AUTH_ERROR = "TF_PROVIDER_AUTH_ERROR"   # auth, non-recoverable
TF_PROVIDER_NOT_FOUND = "TF_PROVIDER_NOT_FOUND"     # api, non-recoverable

# Execution & state
TF_EXECUTION_ERROR = "TF_EXECUTION_ERROR"           # runtime, non-recoverable
TF_STATE_ERROR = "TF_STATE_ERROR"                   # io, non-recoverable
TF_TIMEOUT = "TF_TIMEOUT"                           # io, recoverable

# API & resources
TF_API_ERROR = "TF_API_ERROR"                       # api, non-recoverable
TF_FILE_NOT_FOUND = "TF_FILE_NOT_FOUND"             # io, non-recoverable
TF_VERSION_MISMATCH = "TF_VERSION_MISMATCH"         # runtime, non-recoverable
```

### Phase 2 Success Criteria
- ✅ HCL config parser working (10+ .tf files tested)
- ✅ Error adapter classifies 15+ exception scenarios
- ✅ Error codes in taxonomy, all mapped to categories
- ✅ `build_terraform_error_detail()` returns complete provenance (plan_path, line_number, resource_name)
- ✅ 30+ new tests pass (config parsing + error classification)
- ✅ pytest suite: 1369+ pass baseline maintained

---

## Phase 3: Cross-Platform Integration (Week 5)

### Parity Testing

**File**: `src/prism/tests/test_scanner_parity_multi_platform.py` (NEW)

Test unified error handling across all 3 platforms:

```python
class TestMultiPlatformErrorEnvelope:
    """Verify error handling parity across platforms."""
    
    def test_unified_provenance_across_platforms():
        """All platforms provide file + line + resource_id."""
        # Ansible: task_file, line_number, task_index
        # K8s: manifest_path, line_number, resource_name
        # Terraform: plan_path, line_number, resource_name
        # ✅ All map to same error envelope
    
    def test_error_categories_complete():
        """All 3 platforms cover all 5 categories."""
        # Verify: runtime, io, parser, api, auth
    
    def test_recoverable_flags_consistent():
        """Transient errors marked recoverable across platforms."""
```

### Integration Tests

**File**: `src/prism/tests/test_scanner_integration_multi_platform.py` (NEW)

Test scanner orchestration:

```python
class TestMultiPlatformScanning:
    """Test scanning across Ansible + K8s + Terraform."""
    
    def test_collection_mode_multi_platform():
        """Collection mode works with all 3 platform plugins."""
    
    def test_error_aggregation():
        """Errors from all platforms aggregated correctly."""
```

### Collection Mode Support

Update `src/prism/api_layer/collection.py` to support all 3 platforms in collection scans.

### Phase 3 Success Criteria
- ✅ Cross-platform parity tests green (10+ tests)
- ✅ Collection mode supports Ansible + K8s + Terraform
- ✅ Error aggregation working (multiple platforms in one scan)
- ✅ Unified provenance verified across all 3
- ✅ pytest suite: 1400+ pass baseline

---

## Dependency Chain & Risk Mitigation

### Critical Dependencies
1. **Error Envelope** ✅ Complete (Phases 1-3)
2. **Plugin Registry** ✅ In place (used by Ansible)
3. **Error Taxonomy** ✅ Defined (5 categories, 30+ codes)

### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| HCL parsing complexity | Use `python-hcl2` library; fallback to regex-based parser |
| K8s cluster connectivity | Phase 1 = local manifest parsing only; Phase 3+ = cluster access |
| Test data availability | Use synthetic manifests + Terraform configs in tests |
| Cross-platform parity | Parity tests enforce consistent error handling |

---

## Implementation Sequence

```
Error Envelope ✅ (Complete)
    ↓
Phase 1a: K8s Error Adapter (1 day)
Phase 1b: K8s Manifest Parser (2 days)
Phase 1c: K8s Error Codes (1 day)
Phase 1d: K8s Tests (2 days)
    ↓
Phase 2a: Terraform Error Adapter (1 day)
Phase 2b: HCL Config Parser (2 days)
Phase 2c: Terraform Error Codes (1 day)
Phase 2d: Terraform Tests (2 days)
    ↓
Phase 3: Cross-Platform Integration (3-5 days)
    ↓
COMPLETE: Multi-platform scanner ready
```

**Total effort**: 8-10 weeks (fits Q3 timeline)

---

## Files to Create

### Kubernetes Plugin
- `src/prism/scanner_plugins/kubernetes/mock.py` ✅ DONE
- `src/prism/scanner_plugins/kubernetes/error_adapter.py` (update stub)
- `src/prism/scanner_plugins/kubernetes/error_codes.py` (NEW)
- `src/prism/scanner_plugins/kubernetes/manifest_parser.py` (NEW)
- `src/prism/scanner_plugins/kubernetes/scanner.py` (NEW)
- `src/prism/tests/test_kubernetes_error_adapter.py` (NEW)
- `src/prism/tests/test_kubernetes_manifest_parser.py` (NEW)

### Terraform Plugin
- `src/prism/scanner_plugins/terraform/mock.py` ✅ DONE
- `src/prism/scanner_plugins/terraform/error_adapter.py` (update stub)
- `src/prism/scanner_plugins/terraform/error_codes.py` (NEW)
- `src/prism/scanner_plugins/terraform/config_parser.py` (NEW)
- `src/prism/scanner_plugins/terraform/scanner.py` (NEW)
- `src/prism/tests/test_terraform_error_adapter.py` (NEW)
- `src/prism/tests/test_terraform_config_parser.py` (NEW)

### Integration Tests
- `src/prism/tests/test_scanner_parity_multi_platform.py` (NEW)
- `src/prism/tests/test_scanner_integration_multi_platform.py` (NEW)

---

## Next Steps

1. **Immediate** (May 12-15):
   - Review this plan with team
   - Confirm HCL parser library choice (recommend: `python-hcl2`)
   - Set Phase 1 kickoff date

2. **Phase 1 Start** (Week of May 19):
   - Dispatch Scout to validate manifest test data availability
   - Begin K8s error adapter implementation
   - Set up test scaffolding

3. **Phase 1 Complete** (By June 2):
   - K8s plugin fully tested
   - Phase 2 kickoff

4. **Phase 2 Complete** (By June 16):
   - Terraform plugin fully tested
   - Begin Phase 3 integration

5. **Phase 3 Complete** (By June 30):
   - Multi-platform scanning operational
   - Ready for Q3 production deployment
