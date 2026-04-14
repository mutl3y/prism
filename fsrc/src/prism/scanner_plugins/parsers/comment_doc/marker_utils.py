"""Parser-owned marker parsing utilities for comment-driven documentation."""

from __future__ import annotations

import re

DEFAULT_DOC_MARKER_PREFIX = "prism"
COMMENT_CONTINUATION_RE = re.compile(r"^\s*#\s?(.*)$")


def normalize_marker_prefix(marker_prefix: str | None) -> str:
    if not isinstance(marker_prefix, str):
        return DEFAULT_DOC_MARKER_PREFIX
    prefix = marker_prefix.strip()
    if not prefix:
        return DEFAULT_DOC_MARKER_PREFIX
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        return DEFAULT_DOC_MARKER_PREFIX
    return prefix


def get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
    escaped_prefix = re.escape(normalize_marker_prefix(marker_prefix))
    return re.compile(
        rf"^\s*#\s*{escaped_prefix}\s*~\s*(?P<label>[a-z0-9_-]+)\s*:?\s*(?P<body>.*)$",
        flags=re.IGNORECASE,
    )
