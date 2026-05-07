# PolicyConstants Hotpath Benchmark

Scope: [src/prism/tests/test_scanner_context.py](src/prism/tests/test_scanner_context.py) and [src/prism/tests/test_feature_detector.py](src/prism/tests/test_feature_detector.py)
Workload: 50-item task catalog, 300 policy lookups per run in the old path, 0 in the new path
Timing setup: `9` samples, `400` workload repetitions per sample

## Comparison

| Path | Mean / run (ms) | Median / run (ms) | Min / run (ms) | Max / run (ms) | Policy lookups / run | Matches / run |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Old path: repeated `require_prepared_policy()` | 0.2850 | 0.2833 | 0.2766 | 0.3024 | 300 | 30 |
| New path: direct `PolicyConstants` field access | 0.0078 | 0.0078 | 0.0078 | 0.0079 | 0 | 30 |

## Interpretation

Wall-clock gain: 97.25% faster on the measured workload.
Policy lookup reduction: 300 calls eliminated per run (100.0% reduction).

Expected vs actual: the benchmark expected a modest positive win from removing 300 lookup calls per run; the measured workload shows the new path is faster while preserving identical match counts.

Recommendation: include the optimization. The lookup reduction is complete, the workload is unchanged, and the wall-clock delta is positive on the representative 50-item catalog.