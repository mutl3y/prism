# Grading Rubric

| Grade | Criteria |
|---|---|
| A | No significant findings; only low-severity notes |
| B+ | 1-2 medium findings; architecture sound |
| B | 3-5 medium findings or 1 high |
| C | Multiple high findings or 1 critical |
| D | Multiple criticals or systemic ownership violations |
| F | Silent data corruption, security failure, or effectively untestable core |

Density floor:

- Packages with 10+ modules usually need at least 4 actionable findings before a "clean-ish" verdict is credible.
- If fewer than 4 findings surface, re-check typing and abstraction leakage before accepting the result.
