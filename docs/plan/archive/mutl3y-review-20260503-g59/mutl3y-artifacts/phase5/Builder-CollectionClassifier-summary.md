Builder-CollectionClassifier

- Scope: G59-M01 in src/prism/tests/test_collection_contract.py
- Change: Added a focused regression proving scan_collection demotes a recoverable PrismRuntimeError with a role_content_* code into the failures list instead of reraising.
- Validation: `cd /raid5/source/test/prism && .venv/bin/python -m pytest -q src/prism/tests/test_collection_contract.py -k role_content` passed.
- Status: Ready for closure.
