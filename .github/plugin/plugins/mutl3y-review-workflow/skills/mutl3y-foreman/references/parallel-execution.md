# Parallel Execution Patterns

Read only the phase recipe you need:

- Sweep and fix-wave batching: [parallel-sweep-and-waves.md](./parallel-sweep-and-waves.md)
- Parallel full gate: [parallel-gate.md](./parallel-gate.md)

Default to parallel only when file sets or phase dependencies are disjoint.
Default batch cap is four writing or read-heavy workers per barrier unless the
phase recipe explicitly justifies a wider batch.
