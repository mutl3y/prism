"""Canonical marker parsing utilities for comment-driven documentation.

Ownership: comment_doc plugin layer — per design, plugin layers own
marker behavior; scanner_data owns only schema contracts.
"""

from __future__ import annotations

import functools
import re

from prism.scanner_config.section import DEFAULT_DOC_MARKER_PREFIX

COMMENT_CONTINUATION_RE = re.compile(r"^\s*#\s?(.*)$")
_MARKER_LINE_RE_CACHE_SIZE = 128


def normalize_marker_prefix(marker_prefix: str | None) -> str:
    if not isinstance(marker_prefix, str):
        return DEFAULT_DOC_MARKER_PREFIX
    prefix = marker_prefix.strip()
    if not prefix:
        return DEFAULT_DOC_MARKER_PREFIX
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        return DEFAULT_DOC_MARKER_PREFIX
    return prefix


class NormalizesMarkerPrefix:
    """Mixin that provides the canonical normalize_marker_prefix staticmethod."""

    @staticmethod
    def normalize_marker_prefix(marker_prefix: str | None) -> str:
        return normalize_marker_prefix(marker_prefix)


@functools.lru_cache(maxsize=_MARKER_LINE_RE_CACHE_SIZE)
def get_marker_line_re(marker_prefix: str = DEFAULT_DOC_MARKER_PREFIX):
    escaped_prefix = re.escape(normalize_marker_prefix(marker_prefix))
    return re.compile(
        rf"^\s*#\s*{escaped_prefix}\s*~\s*(?P<label>[a-z0-9_-]+)\s*:?\s*(?P<body>.*)$",
        flags=re.IGNORECASE,
    )
