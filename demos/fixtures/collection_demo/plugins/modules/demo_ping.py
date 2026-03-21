DOCUMENTATION = r"""
---
module: demo_ping
short_description: Demo module fixture for Prism plugin inventory
description:
  - Minimal module file used to demonstrate module plugin discovery.
options:
  message:
    description:
      - Message returned by the demo module.
    type: str
    default: pong
"""

EXAMPLES = r"""
- name: Run demo ping module
  demo.prism_demos.demo_ping:
    message: hello
"""

RETURN = r"""
message:
  description: Response message.
  type: str
  returned: always
"""


def main():
    return {"changed": False, "message": "pong"}


if __name__ == "__main__":
    main()
