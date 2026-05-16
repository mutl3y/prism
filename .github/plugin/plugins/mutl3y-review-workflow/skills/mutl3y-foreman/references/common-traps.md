# Common Traps During Fix Implementation

Accumulated regressions seen in past cycles. Check this list before closing a Phase 5 wave.

## Promoted functions with DI-overridable state

When promoting a function from a discovery/orchestration module into a pure helper module, check whether the caller was threading DI-resolved policy state (e.g. `INCLUDE_VARS_KEYS` from a policy plugin). If so, add an optional parameter to the promoted function to accept that state, and thread it from the caller. Failing to do this causes silent behavior regression against DI override tests.

## `create_file` append-bug on rewrite

`create_file` (and `multi_replace_string_in_file` in some failure modes) can behave like append when used to "rewrite" an existing file. Symptoms: file grows on each retry (e.g. 115 → 216 → 331 lines), duplicate `# Heading` blocks, lint reports MD024/MD025 (multiple H1s) or MD024 duplicate headings. Fix: atomic overwrite via Python heredoc.

```bash
python3 << 'PYEOF'
from pathlib import Path
content = '''<full file body here>'''
Path("/abs/path/to/file").write_text(content, encoding="utf-8")
print("OK")
PYEOF
```

Always verify after rewrite: `wc -l <file>; grep -c "^# <H1 text>" <file>` — line count should match expected, H1 count should be 1.

## Stale `from __future__ import annotations` after rewrite

Symptom: `SyntaxError: from __future__ imports must occur at the beginning of the file`. Cause: a partial rewrite (or auto-formatter on a partially-edited file) leaves a stale `from __future__ import annotations` in the middle of the file while the new content has its own at the top. Fix: `grep -n "__future__" <file>` after any large test/module rewrite; expect exactly one hit at the top.

## Stale terminal scrollback resurfacing in `<context>`

Errors shown in the user's `<context>` block can be from runs hours ago, not the current state. Before reacting (especially to a SyntaxError or test failure that contradicts your last green gate), re-verify with a fresh focused run:

```bash
.venv/bin/python -m pytest <single test file> -q --tb=short
```

Trust fresh evidence over scrollback.

## `nohup ... &` returns exit 0 instantly

Backgrounded pytest returns the shell prompt with `Exit Code: 0` immediately — that is **not** the test result. Do **not** use `wait $PID` as a standalone terminal call — it silently hangs if the process already exited in a different shell session. Instead, use `cat .mutl3y-gate/pytest.log | tail -5` to read the result directly. See [gate-commands.md § Backgrounded runs](./gate-commands.md).

## Heredoc echo flooding the captured terminal output

Long `cat >> file << 'EOF'` heredocs echo every continuation line (`> ...`) into the captured terminal output. This can flood the orchestrator's context window and truncate the trailing confirmation marker. Verify with `tail -N <file>` instead of trusting the heredoc's own output. For very long content prefer the Python heredoc above (no continuation echo).
