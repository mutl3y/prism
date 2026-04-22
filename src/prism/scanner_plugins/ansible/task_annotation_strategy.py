"""Task-annotation parsing strategy owned by ansible plugin modules.

Delegates to the canonical shared implementations in
``scanner_plugins.policies.annotation_parsing`` and
``scanner_plugins.parsers.comment_doc.marker_utils``.
"""

from __future__ import annotations

from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    DEFAULT_DOC_MARKER_PREFIX,
    get_marker_line_re,
    normalize_marker_prefix,
)
from prism.scanner_plugins.policies.constants import (
    COMMENT_CONTINUATION_RE,
    COMMENTED_TASK_ENTRY_RE,
    TASK_ENTRY_RE,
    YAML_LIKE_KEY_VALUE_RE,
    YAML_LIKE_LIST_ITEM_RE,
)
from prism.scanner_plugins.policies.annotation_parsing import (
    annotation_payload_looks_yaml,
    extract_task_annotations_for_file,
    split_task_annotation_label,
    split_task_target_payload,
    task_anchor,
)

__all__ = [
    "DEFAULT_DOC_MARKER_PREFIX",
    "get_marker_line_re",
    "normalize_marker_prefix",
    "COMMENT_CONTINUATION_RE",
    "COMMENTED_TASK_ENTRY_RE",
    "TASK_ENTRY_RE",
    "YAML_LIKE_KEY_VALUE_RE",
    "YAML_LIKE_LIST_ITEM_RE",
    "annotation_payload_looks_yaml",
    "extract_task_annotations_for_file",
    "split_task_annotation_label",
    "split_task_target_payload",
    "task_anchor",
]
