Invariant preserved: collection scanning still demotes only typed role-content failures into collection failure records and still reraises non-content runtime failures; DI plugin construction still fails closed on malformed constructor shape without coercing arbitrary constructor exceptions into the PrismRuntimeError channel.

Files changed:

- src/prism/api_layer/collection.py
- src/prism/scanner_core/di.py
- src/prism/tests/test_scanner_core_di.py

Finding status:

- G61-M01 is closed-ready in owned scope.

Narrow gate:

- Command: `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_collection_contract.py -k exception src/prism/tests/test_scanner_core_di.py -k 'bad_constructor or constructor_exception'`
- Result: 4 passed, 76 deselected.

Additional importer-layer tests run:

- `cd /raid5/source/test/prism && .venv/bin/python -m ruff check src/prism/api_layer/collection.py src/prism/scanner_core/di.py src/prism/tests/test_collection_contract.py src/prism/tests/test_scanner_core_di.py`
- Result: passed.

Scope expansion needed: none.
