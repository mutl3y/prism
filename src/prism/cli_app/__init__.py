"""Package-owned implementation layer for Prism's CLI facade.

`prism.cli` remains the stable top-level CLI entry module.
New parser, dispatch, shared helper, and command implementation code should
land in this package first and be surfaced through `prism.cli` only when
intentional compatibility requires it.
"""
