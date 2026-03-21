DOCUMENTATION = r"""
---
strategy: demo_strategy
short_description: Demo strategy plugin fixture
description:
  - Used to show strategy plugin discovery in generated collection docs.
"""


class StrategyModule:
    def run(self, iterator, play_context):
        return []
