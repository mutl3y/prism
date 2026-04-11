"""Default plugin fallbacks for fsrc scanner plugin ownership seams."""

from __future__ import annotations

from prism.scanner_plugins.interfaces import CommentDrivenDocumentationPlugin


class DefaultCommentDrivenDocumentationPlugin(CommentDrivenDocumentationPlugin):
    """Fallback comment-doc plugin returning stable empty category buckets."""

    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]:
        del role_path
        del exclude_paths
        del marker_prefix
        return {
            "warnings": [],
            "deprecations": [],
            "notes": [],
            "additionals": [],
        }


def resolve_comment_driven_documentation_plugin(
    di: object | None,
) -> CommentDrivenDocumentationPlugin:
    """Resolve plugin from DI factory when present, otherwise use fallback."""
    factory = getattr(di, "factory_comment_driven_doc_plugin", None)
    if callable(factory):
        plugin = factory()
        if plugin is not None:
            return plugin
    return DefaultCommentDrivenDocumentationPlugin()


__all__ = [
    "DefaultCommentDrivenDocumentationPlugin",
    "resolve_comment_driven_documentation_plugin",
]
