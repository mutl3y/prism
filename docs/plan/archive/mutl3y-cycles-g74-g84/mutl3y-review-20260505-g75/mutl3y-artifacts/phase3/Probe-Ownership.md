# Probe-Ownership Investigation: DIContainer._get_registry Seam

## Question
Is the DIContainer._get_registry seam intentional, or is it split registry authority that still needs closure?

## Answer
**INTENTIONAL SEAM — NOT SPLIT AUTHORITY**

The seam represents a deliberate two-tier registry resolution pattern:
- **Hot path (DIContainer._get_registry)**: Fail-closed, requires explicit registry in DI for factory_variable_discovery_plugin and factory_feature_detection_plugin
- **Cold path (scanner_plugins.defaults._resolve_registry)**: Fallback-enabled (explicit > di-supplied > bootstrap singleton) for policy/loader paths

## Evidence

### DIContainer Seam Structure
- **self._registry**: Stored as Optional[PluginRegistry] during init
- **plugin_registry property**: Public, returns self._registry directly (can be None)
- **_get_registry() method**: Private, raises ValueError("No plugin registry provided") if self._registry is None

### Usage Localization
- _get_registry() called only in 2 factory methods:
  - line 407: factory_variable_discovery_plugin
  - line 433: factory_feature_detection_plugin
- Both methods call _resolve_platform_key() → resolve_platform_key() which accepts registry=None gracefully
- Tests explicitly verify fail-closed behavior: `test_factory_variable_discovery_plugin_fail_closed_no_registry`

### External Resolution Layer
In scanner_plugins/defaults.py:
- _get_registry_from_di(di) uses getattr(di, "plugin_registry", None) — defensive
- _resolve_registry(di, registry) implements 3-tier fallback: explicit > di-supplied > bootstrap singleton
- _resolve_registry used 3 times in defaults.py (line 417, 478, 775) for policy/loader resolution paths

### Boundary Observation
- DIContainer enforces ingress-time registry wiring requirement
- External callers (defaults.py) handle fallback gracefully
- No cross-contamination: hot-path plugin factories never call _resolve_registry

## Conclusion
The seam is INTENTIONAL. DIContainer._get_registry represents an explicit fail-closed contract for runtime plugin resolution, while defaults._resolve_registry provides a separate fallback chain for external policy/loader paths. This two-tier pattern is well-coordinated and requires no closure.

## Risks or Open Edges

1. **Maintenance confusion**: Two distinct resolution patterns could mislead future maintainers into adding fallback to _get_registry, weakening fail-closed semantics.

2. **Bootstrap singleton re-emergence**: _resolve_registry's fallback to get_default_plugin_registry() could reintroduce implicit plugin dependencies if external callers start using it in contexts meant to be explicit-only.

3. **Inconsistent registry authority if DIContainer creation is not audited**: If future code creates DIContainer without providing registry for non-hot-path use cases, _get_registry seam could mask incomplete DI wiring.
