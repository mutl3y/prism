DOCUMENTATION = r"""
---
lookup: environment_lookup
short_description: Demo lookup that returns environment-style values
description:
  - Demonstrates how Prism inventories multiple lookup plugins in one collection.
"""


class LookupModule:
    def run(self, terms, variables=None, **kwargs):
        return ["ENV=demo"]
