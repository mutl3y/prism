# Probe-DI

- agent: Probe-DI
- created_at: 2026-05-07T00:00:00Z
- scope:
  - src/prism/scanner_core/di.py
  - src/prism/scanner_plugins/registry.py
  - src/prism/scanner_core/scanner_context.py

## One-line conclusion

Registry module contains a Python syntax error that will prevent runtime imports; carry into a fix wave.

## Evidence

- File: src/prism/scanner_plugins/registry.py
- Faulty line excerpt:

```
    try:
        signature = inspect.signature(plugin_class)
    except TypeError, ValueError:
        return
```

- The above `except TypeError, ValueError:` is invalid Python 3 syntax (should be `except (TypeError, ValueError):`) and will raise a SyntaxError at import time, preventing module import and subsequent DI/registry usage.

- Related DI usage:
  - `src/prism/scanner_core/di.py` depends on `PluginRegistry` behaviour for platform key resolution and plugin class resolution (methods: `_get_registry`, `_resolve_platform_key`, `factory_variable_discovery_plugin`, `factory_feature_detection_plugin`). A non-importable `scanner_plugins.registry` breaks runtime plugin resolution.
  - `src/prism/scanner_core/scanner_context.py` uses DI factory methods (e.g., `factory_variable_discovery`, `factory_feature_detector`) which in turn rely on `PluginRegistry` being loadable and functioning.

## Impact

- High: Syntax error in `registry.py` stops module import, which can break runtime bootstrap and any consumers that import the registry or rely on plugin registration.
- Tests may still pass in isolated contexts if tests mock DI or avoid importing the faulty module; however, the defect is actionable and should be fixed.

## Recommended fix (minimal)

- Change the except clause to a valid multi-exception form:

```
    except (TypeError, ValueError):
        return
```

- Run the test matrix that imports the registry and DI: specifically any tests that import `prism.scanner_plugins.registry` or exercise plugin registration/resolution.

## Risks / Open edges

1. Deferred dynamic plugin loading paths (`register_deferred_*` + `load_plugin_from_module`) may mask additional runtime shape mismatches; after fixing syntax, run shape-validation and load tests to surface constructor-shape or API-version mismatches.
2. Some test suites may mock registry behavior and not exercise the real import path; ensure CI runs an integration path that imports `scanner_plugins.registry` to confirm runtime health.
