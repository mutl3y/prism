# Foreman-Ownership Summary

- Plan ID: gilfoyle-review-20260501-g41
- Finding: FIND-G41-OWN-01
- Scope: src/prism/cli.py, src/prism/tests/test_scanner_guardrails.py

## Change

Routed the CLI audit helper through `prism.api_layer.plugin_facade` instead of importing `prism.scanner_plugins.audit` directly. Tightened the existing guardrail test so API and CLI entrypoints no longer carry a direct `scanner_plugins` import exception.

## Validation

- `pytest -q src/prism/tests/test_scanner_guardrails.py -k 'api_cli_entrypoints_do_not_import_scanner_plugins_directly'`
- `rg -n 'from prism\.scanner_plugins\.audit' src/prism/cli.py` returned no matches
- `ruff check src/prism/cli.py src/prism/tests/test_scanner_guardrails.py`
- `black --check src/prism/cli.py src/prism/tests/test_scanner_guardrails.py`
