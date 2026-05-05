# Builder-CliPresenterOwnership Summary

- Plan ID: `mutl3y-review-20260503-g60`
- Task ID: `g60-wave2b-builder-cli-public-io-seam`
- Objective: `G60-M01`

Corrected the earlier seam regression by restoring `prism.cli` to the public runtime package seam. Collection markdown rendering and summary formatting now flow through `prism.scanner_io`, and `prism.scanner_io.__init__` explicitly re-exports `format_collection_summary` alongside `render_collection_markdown`.

Updated the focused regression in `src/prism/tests/test_cli_app.py` to monkeypatch `prism.scanner_io`, proving that the collection CLI path uses the public scanner I/O package seam rather than `prism.cli_app` or the private `collection_renderer` module. Collection CLI text-output behavior remains unchanged.

Validation:

- `pytest -q src/prism/tests/test_cli_api_guardrails.py -k runtime_modules_do_not_import_src_facade_packages` -> PASS
- `pytest -q src/prism/tests/test_collection_contract.py -k cli_collection_text_output` -> PASS
- `pytest -q src/prism/tests/test_cli_app.py -k scanner_io_public_seam` -> PASS
