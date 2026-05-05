# Builder-TaskContractTyping Summary

- Plan ID: `mutl3y-review-20260503-g60`
- Task ID: `g60-wave3-builder-task-contract-typing`
- Slice: `G60-M02`

## Change

Added a shared `TaskMapping` alias in `contracts_request.py` and tightened the task-shaped hot-path contracts around `detect_task_module`, `iter_task_mappings`, `expand_include_target_candidates`, `iter_role_include_targets`, and `iter_dynamic_role_include_targets`. Updated the owned ansible policy implementations and the local traversal adapter to consume the same shared task mapping shape without changing behavior.

## Validation

- PASS: `.venv/bin/python -m mypy src/prism/scanner_data/contracts_request.py src/prism/scanner_plugins/ansible/extract_policies.py src/prism/scanner_plugins/ansible/default_policies.py src/prism/scanner_plugins/ansible/task_traversal_bare.py src/prism/scanner_extract/task_file_traversal.py`
- PASS: `pytest -q src/prism/tests/test_extract_policies.py`

## Closure

`G60-M02` is closure-ready within the owned slice.
