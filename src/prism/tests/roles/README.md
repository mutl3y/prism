# Test Role Fixtures

This folder provides stable role fixture entry points used by tests.

- `base_mock_role` is the baseline fixture for deterministic scanner and render tests.
  It points to `../mock_role`.
- `enhanced_mock_role` is the production-like fixture for realism tests and broader
  scenario coverage.
  It points to `../enhanced_mock_role`.
- `comment_driven_demo_role` is a documentation-heavy fixture that demonstrates
  dense use of comment-driven notes, warnings, runbooks, and task annotations
  across a fuller role workflow.
- `inrole_config_role` is a dedicated fixture for in-role readme config behavior.

Source directories:

- Baseline fixture content: `src/prism/tests/mock_role/`
- Enhanced fixture content: `src/prism/tests/enhanced_mock_role/`

Guidance:

- Use `base_mock_role` when adding unit tests that should remain stable over time.
- Use `enhanced_mock_role` when validating richer defaults/vars, multi-path tasks,
  metadata detail, or molecule-style scaffolding.
