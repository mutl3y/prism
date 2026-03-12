"""CLI entry point for ansible-role-doc"""
from __future__ import annotations
import argparse
import sys
from .scanner import run_scan

def build_parser():
    p = argparse.ArgumentParser(prog="ansible-role-doc", description="Scan an Ansible role for default() usages and render README.")
    p.add_argument("role_path", help="Path to the Ansible role directory to scan")
    p.add_argument("-o", "--output", default="README.md", help="Output README file path")
    p.add_argument("-t", "--template", default=None, help="Template path (optional). If omitted, uses bundled template.")
    return p

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        run_scan(args.role_path, output=args.output, template=args.template)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(2)