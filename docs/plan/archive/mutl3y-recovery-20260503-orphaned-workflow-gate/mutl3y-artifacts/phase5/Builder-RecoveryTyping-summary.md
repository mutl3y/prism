agent name: Builder-RecoveryTyping

owned file set:

- src/prism/scanner_core/di.py
- src/prism/scanner_kernel/orchestrator.py
- src/prism/scanner_core/metadata_merger.py
- src/prism/tests/test_execution_request_builder.py
- docs/plan/mutl3y-recovery-20260503-orphaned-workflow-gate/mutl3y-artifacts/phase5/Builder-RecoveryTyping-summary.md

summary artifact path:

- docs/plan/mutl3y-recovery-20260503-orphaned-workflow-gate/mutl3y-artifacts/phase5/Builder-RecoveryTyping-summary.md

changed files:

- src/prism/scanner_core/di.py
- src/prism/scanner_kernel/orchestrator.py
- src/prism/scanner_core/metadata_merger.py
- src/prism/tests/test_execution_request_builder.py
- docs/plan/mutl3y-recovery-20260503-orphaned-workflow-gate/mutl3y-artifacts/phase5/Builder-RecoveryTyping-summary.md

concise status:

- Focused recovery typing debt in the owned seam was reduced to zero on the requested mypy slice without widening to Any.
- DI scan-option snapshots now stay on ScanOptionsDict, override returns are narrowed at keyed seams, and the container exposes the read-only state surface the typed tests expect.
- Kernel orchestration now routes through typed scan-option, metadata, routing, and registry helpers while preserving existing preflight carrier behavior.
- Policy warning merging preserves the ScanPolicyWarning TypedDict shape via shallow copy.
- Execution-request tests now use typed scan-option builders and protocol-aligned doubles.

validation results:

- `.venv/bin/python -m mypy src/prism/scanner_core/di.py src/prism/scanner_kernel/orchestrator.py src/prism/scanner_core/metadata_merger.py src/prism/tests/test_execution_request_builder.py` -> success, no issues found in 4 source files
- `.venv/bin/python -m pytest -q src/prism/tests/test_execution_request_builder.py src/prism/tests/test_plugin_kernel_extension_parity.py` -> 47 passed in 1.33s

formatting follow-up (2026-05-03):

- `.venv/bin/python -m black --check src/prism/scanner_core/metadata_merger.py src/prism/scanner_kernel/orchestrator.py src/prism/tests/test_execution_request_builder.py` -> all files left unchanged (black clean)
