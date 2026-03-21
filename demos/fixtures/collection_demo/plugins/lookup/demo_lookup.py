DOCUMENTATION = r"""
---
lookup: demo_lookup
short_description: Return a small static lookup payload for demos
description:
  - Used by the Prism demo collection to populate non-filter plugin inventory.
"""


class LookupModule:
    def run(self, terms, variables=None, **kwargs):
        return ["demo-result"]
