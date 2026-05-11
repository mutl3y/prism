# Gate Commands

> **Lane note (2026-04-22):** `fsrc/` was promoted to canonical `src/` and the directory was deleted. Single-lane `src/` only.
> For the **parallel** gate recipe (fail-fast, concurrent), see [parallel-execution.md § Phase 6](./parallel-execution.md). The serial commands below are the canonical fallback when concurrent execution is not available.

Reference for running the standard validation gate after each fix wave.

## Quick Gate (fast feedback during active fixing)

```bash
cd /raid5/source/test/prism
.venv/bin/python -m pytest -p no:cov -p no:cacheprovider -q --tb=short
```

## Path-filtered inter-wave gate

Use BETWEEN waves; full gate only at Phase 7 entry. After each Phase 5 wave, run only the tests + lint touching the wave's changed files.

```bash
cd /raid5/source/test/prism
CHANGED=$(git diff --name-only HEAD -- '*.py')
TEST_PATHS=$(echo "$CHANGED" | grep -E '/tests/test_' || true)
SRC_CHANGED=$(echo "$CHANGED" | grep -vE '/tests/' || true)
IMPLIED_TESTS=$(for f in $SRC_CHANGED; do
  base=$(basename "$f" .py)
  find . -path '*/tests/test_*.py' -name "test_${base}*.py" 2>/dev/null
done | sort -u)
TARGETS=$(echo -e "$TEST_PATHS\n$IMPLIED_TESTS" | sort -u | tr '\n' ' ')
[ -n "$TARGETS" ] && .venv/bin/python -m pytest $TARGETS -q -x --tb=short
[ -n "$CHANGED" ] && .venv/bin/python -m ruff check $CHANGED
[ -n "$CHANGED" ] && .venv/bin/python -m black --check $CHANGED
```

## Resume-dirty-tree repo gate (resume/continue enforcement)

Use this when resuming/continuing a prior cycle and tracked Python files are
modified. This gate blocks new wave work until the checks are run and the
outcome recorded in `.mutl3y-gate/resume-dirty-tree.yaml` and the phase
start-audit artifact.

```bash
cd /raid5/source/test/prism
mkdir -p .mutl3y-gate
CHANGED_PY=$(
  git status --porcelain --untracked-files=no |
  awk '{print $2}' |
  grep -E '\.py$' || true
)
if [ -n "$CHANGED_PY" ]; then
  echo "Resumed-cycle: dirty tracked Python files present:" > .mutl3y-gate/resume-dirty-tree.log
  echo "$CHANGED_PY" >> .mutl3y-gate/resume-dirty-tree.log
  .venv/bin/python -m ruff check src/prism \
    >> .mutl3y-gate/resume-dirty-tree.log 2>&1
  RUFF_EXIT=$?
  .venv/bin/python -m black --check src/prism \
    >> .mutl3y-gate/resume-dirty-tree.log 2>&1
  BLACK_EXIT=$?
  STATUS=OK
  if [ $RUFF_EXIT -ne 0 ] || [ $BLACK_EXIT -ne 0 ]; then
    STATUS=BLOCKED
  fi
  cat > .mutl3y-gate/resume-dirty-tree.yaml <<-YAML
resume_dirty_tree:
  status: "$STATUS"
  ruff_exit: $RUFF_EXIT
  black_exit: $BLACK_EXIT
  checked_at: "$(date -u --iso-8601=seconds)"
  changed_files: |
$(echo "$CHANGED_PY" | sed 's/^/    /')
  log: .mutl3y-gate/resume-dirty-tree.log
YAML
  echo "Resume-dirty-tree gate result: $STATUS"
  # Foreman must copy these fields into the phase start-audit artifact
  # before narrating phase start. If STATUS != OK, do not start new wave work.
fi
```

Full gate runs once on Phase 7 entry.

## Full Gate

Run before marking any finding closed.

```bash
cd /raid5/source/test/prism
.venv/bin/python -m pytest -p no:cov -p no:cacheprovider -q --tb=short
.venv/bin/python -m ruff check src/prism
.venv/bin/python -m black --check src/prism
```

## Auto-format then re-lint

```bash
.venv/bin/python -m black <file1> <file2> ...
.venv/bin/python -m ruff check src/prism && .venv/bin/python -m black --check src/prism
```

## Typecheck

Run before closing structural findings. `tox -e typecheck` sometimes returns no captured output via the terminal tool. Use mypy directly and write to a file:

```bash
cd /raid5/source/test/prism
mkdir -p .mutl3y-gate
.venv/bin/python -m mypy src/prism > .mutl3y-gate/mypy.out 2>&1; tail -5 .mutl3y-gate/mypy.out
```

For zero-delta proofs after a refactor, baseline via `git stash`:

```bash
cd /raid5/source/test/prism
mkdir -p .mutl3y-gate
git stash && .venv/bin/python -m mypy src/prism > .mutl3y-gate/mypy.baseline 2>&1; git stash pop
.venv/bin/python -m mypy src/prism > .mutl3y-gate/mypy.current 2>&1
diff <(grep -c "error:" .mutl3y-gate/mypy.baseline) <(grep -c "error:" .mutl3y-gate/mypy.current)
```

## Backgrounded runs (avoid exit-0 false-success)

`nohup ... &` returns the shell prompt instantly with exit code 0 — that is **not** the test result. Always read the log file directly — do **not** use `wait $PID` in a separate terminal call, as it produces no output when the terminal session context has been reused and silently stalls the foreman.

Preferred pattern — launch and read log in the same command:

```bash
mkdir -p .mutl3y-gate
nohup .venv/bin/python -m pytest -p no:cov -p no:cacheprovider -q > .mutl3y-gate/pytest.log 2>&1 &
echo "launched PID=$!"
# In the SAME or next command, poll until done:
while kill -0 $! 2>/dev/null; do sleep 2; done; tail -5 .mutl3y-gate/pytest.log
```

Fallback — if a previous background run may have finished, just read the log:

```bash
cat .mutl3y-gate/pytest.log | tail -5
```

Never call `wait $PID` as a standalone command in a separate terminal invocation — it will hang silently if the process has already exited in a different shell session.

## Gate Thresholds

| Check | Pass Criteria |
| --- | --- |
| pytest | All tests pass, 0 failures (skipped allowed) |
| ruff | Exit 0, no output |
| black | "X files would be left unchanged" |
| mypy | Delta = 0 vs baseline (pre-existing errors tolerated) |

## Common Failure Patterns

ImportError after a module move:

- Check all `__init__.py` files in the import chain
- Check `defaults.py` and `scanner_plugins/__init__.py` for stale imports
- Verify `__all__` was updated in every affected re-export file

Test regression after promoting a function:

- Check if the caller was threading DI-resolved state (policy keys, plugin methods)
- Add an optional parameter to the promoted function and thread from the call site

black reformats after edits:

- Run `black <changed files>` each wave before checking in
- ruff + black must both be clean before closing a finding

Stale terminal scrollback resurfaces an old error:

- Errors shown in `<context>` blocks may be from runs hours ago
- Always re-verify with a fresh focused run (`cat .mutl3y-gate/<fresh>.log | tail -5`) before reacting
