DOCUMENTATION = r"""
---
plugin: demo_inventory
short_description: Demo dynamic inventory plugin fixture
description:
  - Provides a minimal inventory plugin so Prism can document inventory coverage.
options:
  plugin:
    description:
      - Token required by Ansible inventory plugin loading.
    required: true
    choices:
      - demo.prism_demos.demo_inventory
"""

NAME = "demo.prism_demos.demo_inventory"


class InventoryModule:
    def parse(self, inventory, loader, path, cache=True):
        return {"all": {"hosts": ["demo-host"]}}
