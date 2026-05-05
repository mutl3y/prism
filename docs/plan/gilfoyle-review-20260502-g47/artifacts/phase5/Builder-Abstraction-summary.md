# Builder-Abstraction Summary

- Finding addressed: `G46-H11`
- Owned files changed: `src/prism/scanner_plugins/parsers/yaml/parsing_policy.py`, `src/prism/scanner_io/loader.py`, `src/prism/tests/test_dataload.py`
- Concise changes: added regression coverage proving invalid YAML must not collapse into empty success-shaped role variable data; changed the default YAML loading path to raise contextual `RuntimeError` on read/parse failures instead of returning `None`, which preserves the error signal for strict callers and non-strict warning paths.
- Gate result: `pytest -q src/prism/tests/test_dataload.py` -> `8 passed`
