"""CLI entry point for ansible-role-doc.

Provides a small CLI wrapper around :func:`ansible_role_doc.scanner.run_scan`.
"""
from __future__ import annotations
import argparse
import sys
from .scanner import run_scan


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    The parser includes options for output path, template, format and verbosity.
    """
    p = argparse.ArgumentParser(prog="ansible-role-doc", description="Scan an Ansible role for default() usages and render README.")
    p.add_argument("role_path", help="Path to the Ansible role directory to scan")
    p.add_argument("-o", "--output", default="README.md", help="Output README file path")
    p.add_argument("-t", "--template", default=None, help="Template path (optional). If omitted, uses bundled template.")
    p.add_argument("-f", "--format", default="md", choices=("md", "html"), help="Output format (md or html).")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return p


def main(argv=None) -> int:
    """CLI entrypoint.

    ``argv`` may be provided for testing; returns an exit code integer.
    """
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        outpath = run_scan(args.role_path, output=args.output, template=args.template, output_format=args.format)
        if args.verbose:
            print("Wrote:", outpath)
        return 0
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        return 2