DOCUMENTATION = r"""
---
connection: demo_connection
short_description: Demo connection plugin fixture
description:
  - Minimal connection plugin used to demonstrate connection plugin inventory.
"""

transport = "demo"


class Connection:
    def exec_command(self, cmd, in_data=None, sudoable=True):
        return 0, "demo connection executed", ""
