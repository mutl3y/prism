DOCUMENTATION = r"""
---
module: demo_report
short_description: Demo reporting module fixture for Prism plugin inventory
description:
  - A second module plugin that makes generated documentation more representative.
options:
  format:
    description:
      - Output format for the generated report.
    type: str
    default: text
"""

EXAMPLES = r"""
- name: Generate a demo report
  demo.prism_demos.demo_report:
    format: json
"""


def main():
    return {"changed": False, "format": "text"}


if __name__ == "__main__":
    main()
