# Light Cycle — Diff-Scoped Review

A **light** review never reads whole files. It feeds the sweep subagents only the changed regions plus narrow neighbour windows.

## Inputs

- `BASE` — the SHA of the last green gate (typically the previous cycle's closing commit).
- `HEAD` — current working tree.
- `WINDOW` — neighbour line count above and below each hunk. Default `20`.

## Recipe

```bash
# Files changed since last green
git diff --name-only "$BASE"..HEAD -- '*.py' > .mutl3y-gate/changed_files.txt

# Per-file context windows (hunks plus WINDOW lines either side)
git diff -U"$WINDOW" "$BASE"..HEAD -- '*.py' > .mutl3y-gate/light_context.diff

# Optional: explicit neighbour list — first-degree importers of changed files
.venv/bin/python -c "import json,sys; g=json.load(open('docs/plan/.mutl3y-lessons/import-graph.json')); \
  changed=open('.mutl3y-gate/changed_files.txt').read().split(); \
  print('\n'.join({i for f in changed for i in g['graph'].get(f,{}).get('imported_by',[])}))" \
  > .mutl3y-gate/light_neighbours.txt
```

## Sweep dispatch

Each Phase 0 sweep subagent receives:

- `light_context.diff` (the only file content)
- `light_neighbours.txt` (file paths only, for the subagent to optionally read)
- The standard ledger preamble + cluster categories

**Hard rule:** the sweep prompt forbids reading any file not listed in `changed_files.txt` or `light_neighbours.txt`.

## When to escalate to thorough

- Light review returns **zero Critical/High** → next cycle is thorough (whole-package).
- Light review touches a file that crosses a package boundary → next cycle is thorough.
- Two consecutive light reviews → forced thorough on the third.
