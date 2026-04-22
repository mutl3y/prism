"""Comment-driven documentation parser implementations."""

from __future__ import annotations

from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
    CommentDrivenDocumentationParser,
)
from prism.scanner_plugins.parsers.comment_doc.role_notes_parser import (
    extract_role_notes_from_comments,
)

__all__ = [
    "CommentDrivenDocumentationParser",
    "extract_role_notes_from_comments",
]
