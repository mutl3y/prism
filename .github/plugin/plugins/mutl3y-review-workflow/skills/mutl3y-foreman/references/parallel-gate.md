# Parallel Gate

Single-lane repo: use one full gate only at closure entry, but run independent gate steps concurrently.
Treat the gate as a multiprocess batch: launch all independent checks first, then join once.

```bash
mkdir -p .mutl3y-gate
(nohup .venv/bin/python -m pytest -p no:cov -p no:cacheprovider -q --tb=short > .mutl3y-gate/pytest.log 2>&1) & PYT=$!
(.venv/bin/python -m ruff check src/prism > .mutl3y-gate/ruff.log 2>&1) & RUFF=$!
(.venv/bin/python -m black --check src/prism > .mutl3y-gate/black.log 2>&1) & BLACK=$!

wait $PYT;   PYT_RC=$?
wait $RUFF;  RUFF_RC=$?
wait $BLACK; BLACK_RC=$?

[ $PYT_RC -eq 0 ] && [ $RUFF_RC -eq 0 ] && [ $BLACK_RC -eq 0 ] && echo GREEN || {
  echo RED
  for f in .mutl3y-gate/*.log; do
    echo "=== $f ==="
    tail -40 "$f"
  done
}
```

Use explicit `wait`; backgrounded pytest can otherwise look green too early.
Do not run pytest, ruff, and black one after another unless the environment cannot support concurrent processes.
