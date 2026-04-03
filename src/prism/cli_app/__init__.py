"""Package-owned implementation layer for Prism's CLI facade.

`prism.cli` remains the stable top-level CLI entry module.
New parser, dispatch, shared helper, and command implementation code should
land in this package first and be surfaced through `prism.cli` only when
intentional compatibility requires it.

Current capability ownership:
- `prism.cli_app.parser`: parser construction, option registration, and shell
  completion support
- `prism.cli_app.commands`: role, collection, repo, and completion command
  handlers
- `prism.cli_app.runtime`: exit-code mapping, output-path resolution, and
  persistence/error helpers
- `prism.cli_app.presenters`: success messaging, payload rendering, capture,
  truncation, and redaction helpers
- `prism.cli_app.shared`: shared CLI option resolution such as vars context,
  feedback-driven collection checks, and README config selection
"""

__all__: list[str] = []


def __getattr__(name: str) -> object:
    """Enforce that package-root access stays intentionally empty."""
    if name.startswith("_"):
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}' "
            f"(private member; only __all__ symbols are public)"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose only explicitly public package-root symbols."""
    return sorted(__all__)
