# Builder-ControlFlow Wave 1 Summary

- Finding: G66-H03
- Fix group: collection-scan.metadata-shape-error-channel
- Invariant preserved: collection reporting keeps malformed per-role metadata on the runbook path in the structured failure channel instead of silently degrading it to an empty mapping.
- Change: api_layer.collection now rejects non-dict runbook metadata locally and records the role through the existing collection failure record path.
- Test coverage: added a regression in test_collection_contract that proves invalid per-role metadata on the runbook path becomes a role_content_invalid failure and does not emit runbook artifacts for that role.
- Narrow gate: `pytest -q src/prism/tests/test_collection_contract.py -k runbook` -> 3 passed, 21 deselected.
- Scope: no expansion needed.
- Common-traps candidate: none beyond the existing silent-fallback guidance.
