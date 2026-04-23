# Performance Benchmark Suite (T4-01)

Establishes baseline benchmarks so future regressions and the T3-02 async
I/O work have measurable targets.

## Suite

`src/prism/tests/test_t4_01_perf_benchmarks.py` covers three scenarios:

1. **Single-file YAML parse** — exercises `prism.scanner_io.loader.parse_yaml_candidate`
   on `demos/fixtures/role_demo/tasks/main.yml`.
2. **Small role scan** — runs `prism.api.scan_role` end-to-end against the
   shipped `role_demo` fixture.
3. **Large synthetic role scan** — generates an in-tmp role with 100 task
   files and runs `prism.api.scan_role`.

The suite uses [`pytest-benchmark`](https://pypi.org/project/pytest-benchmark/)
and is gated by `pytest.importorskip("pytest_benchmark")` so installations
without the extra dependency are unaffected.

## Run locally

```bash
.venv/bin/pip install pytest-benchmark
PRISM_RUN_BENCHMARKS=1 .venv/bin/python -m pytest \
    src/prism/tests/test_t4_01_perf_benchmarks.py \
    --benchmark-only \
    --benchmark-json=.benchmarks/results.json
```

The suite is gated by the ``PRISM_RUN_BENCHMARKS`` environment variable so
that the default ``pytest -q`` invocation skips it (the benchmark fixtures
touch the real filesystem and can be perturbed when other test modules in
the run enable pyfakefs).

## CI integration

Recommended CI step (artifact upload, no pass/fail gate yet):

```yaml
- name: Run benchmarks
  env:
    PRISM_RUN_BENCHMARKS: "1"
  run: |
    pip install pytest-benchmark
    pytest src/prism/tests/test_t4_01_perf_benchmarks.py \
      --benchmark-only \
      --benchmark-json=.benchmarks/results.json
- uses: actions/upload-artifact@v4
  with:
    name: prism-benchmarks
    path: .benchmarks/results.json
```

Budgets and pass/fail thresholds will be set after the baseline stabilises
(per T4-01 acceptance criteria: artifact upload first, gate later).
