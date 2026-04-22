"""Heading formatting utilities for markdown style guide rendering."""

from __future__ import annotations

import re


def normalize_style_heading(heading: str) -> str:
    """Normalize markdown heading text for style-guide matching."""
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
    normalized = re.sub(r"[^a-z0-9()]+", " ", cleaned.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def format_heading(text: str, level: int, style: str) -> str:
    """Format markdown headings using ATX or setext style."""
    if style == "atx":
        return f"{'#' * level} {text}"
    if level == 1:
        return f"{text}\n{'=' * len(text)}"
    if level == 2:
        return f"{text}\n{'-' * len(text)}"
    return f"{'#' * level} {text}"
