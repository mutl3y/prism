"""Task-file line parsing constants and marker helpers for fsrc."""

from __future__ import annotations

import re
from typing import Any, Iterator

from prism.scanner_data.di_helpers import require_prepared_policy


def _get_task_line_parsing_policy(di=None):
    return require_prepared_policy(di, "task_line_parsing", "task_line_parsing")


def _get_task_annotation_policy(di: object | None = None):
    return require_prepared_policy(
        di, "task_annotation_parsing", "task_annotation_parsing"
    )


class _PolicyBackedCollectionProxy:
    def __init__(self, policy_attr_name: str) -> None:
        self._policy_attr_name = policy_attr_name

    def _current_value(self) -> object:
        return getattr(_get_task_line_parsing_policy(), self._policy_attr_name)

    def __iter__(self) -> Iterator[Any]:
        value = self._current_value()
        if isinstance(value, (set, tuple, list, frozenset)):
            return iter(value)
        return iter(())

    def __contains__(self, item: object) -> bool:
        value = self._current_value()
        if isinstance(value, (set, tuple, list, frozenset)):
            return item in value
        return False

    def __len__(self) -> int:
        value = self._current_value()
        if isinstance(value, (set, tuple, list, frozenset)):
            return len(value)
        return 0

    def __repr__(self) -> str:
        return repr(self._current_value())


class _PolicyBackedRegexProxy:
    def __init__(self, policy_attr_name: str) -> None:
        self._policy_attr_name = policy_attr_name

    def _current_regex(self) -> re.Pattern[str]:
        current = getattr(_get_task_line_parsing_policy(), self._policy_attr_name)
        if isinstance(current, re.Pattern):
            return current
        raise ValueError(
            f"prepared_policy_bundle.task_line_parsing.{self._policy_attr_name} "
            f"must be a compiled re.Pattern, got {type(current).__name__}"
        )

    def match(self, *args: Any, **kwargs: Any):
        return self._current_regex().match(*args, **kwargs)

    def search(self, *args: Any, **kwargs: Any):
        return self._current_regex().search(*args, **kwargs)

    def fullmatch(self, *args: Any, **kwargs: Any):
        return self._current_regex().fullmatch(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._current_regex(), name)


TASK_INCLUDE_KEYS = _PolicyBackedCollectionProxy("TASK_INCLUDE_KEYS")
ROLE_INCLUDE_KEYS = _PolicyBackedCollectionProxy("ROLE_INCLUDE_KEYS")
INCLUDE_VARS_KEYS = _PolicyBackedCollectionProxy("INCLUDE_VARS_KEYS")
SET_FACT_KEYS = _PolicyBackedCollectionProxy("SET_FACT_KEYS")
TASK_BLOCK_KEYS = _PolicyBackedCollectionProxy("TASK_BLOCK_KEYS")
TASK_META_KEYS = _PolicyBackedCollectionProxy("TASK_META_KEYS")


def get_task_include_keys(di: object | None = None) -> object:
    return _get_task_line_parsing_policy(di).TASK_INCLUDE_KEYS


def get_role_include_keys(di: object | None = None) -> object:
    return _get_task_line_parsing_policy(di).ROLE_INCLUDE_KEYS


def get_include_vars_keys(di: object | None = None) -> object:
    return _get_task_line_parsing_policy(di).INCLUDE_VARS_KEYS


def get_set_fact_keys(di: object | None = None) -> object:
    return _get_task_line_parsing_policy(di).SET_FACT_KEYS


def get_task_block_keys(di: object | None = None) -> object:
    return _get_task_line_parsing_policy(di).TASK_BLOCK_KEYS


def get_task_meta_keys(di: object | None = None) -> object:
    return _get_task_line_parsing_policy(di).TASK_META_KEYS


def get_templated_include_re(di: object | None = None) -> re.Pattern[str] | object:
    return _get_task_line_parsing_policy(di).TEMPLATED_INCLUDE_RE


def _extract_constrained_when_values(
    task: dict,
    variable: str,
    *,
    di: object | None = None,
) -> list[str]:
    return _get_task_line_parsing_policy(di).extract_constrained_when_values(
        task, variable
    )


def _normalize_marker_prefix(
    marker_prefix: str | None,
    *,
    di: object | None = None,
) -> str:
    return _get_task_annotation_policy(di).normalize_marker_prefix(marker_prefix)


def _build_marker_line_re(
    marker_prefix: str | None,
    *,
    di: object | None = None,
):
    normalized_prefix = _normalize_marker_prefix(marker_prefix, di=di)
    return _get_task_annotation_policy(di).get_marker_line_re(normalized_prefix)


def get_marker_line_re(marker_prefix, *, di: object | None = None):
    return _build_marker_line_re(marker_prefix, di=di)


class _PolicyBackedMarkerLineRegexProxy:
    """Proxy that resolves marker-line regex from annotation policy at call time."""

    def _current_regex(self) -> re.Pattern[str]:
        policy = _get_task_annotation_policy()
        regex = policy.get_marker_line_re(policy.normalize_marker_prefix(None))
        if isinstance(regex, re.Pattern):
            return regex
        raise ValueError(
            "prepared_policy_bundle.task_annotation_parsing.get_marker_line_re "
            "must return a compiled re.Pattern"
        )

    def match(self, *args: Any, **kwargs: Any):
        return self._current_regex().match(*args, **kwargs)

    def search(self, *args: Any, **kwargs: Any):
        return self._current_regex().search(*args, **kwargs)

    def fullmatch(self, *args: Any, **kwargs: Any):
        return self._current_regex().fullmatch(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._current_regex(), name)


ROLE_NOTES_RE = _PolicyBackedMarkerLineRegexProxy()
TASK_NOTES_LONG_RE = _PolicyBackedMarkerLineRegexProxy()


class _PolicyBackedAnnotationRegexProxy:
    def __init__(self, policy_attr_name: str) -> None:
        self._policy_attr_name = policy_attr_name

    def _current_regex(self) -> re.Pattern[str]:
        current = getattr(_get_task_annotation_policy(), self._policy_attr_name, None)
        if isinstance(current, re.Pattern):
            return current
        raise ValueError(
            f"prepared_policy_bundle.task_annotation_parsing.{self._policy_attr_name} "
            f"must be a compiled regex pattern"
        )

    def match(self, *args: Any, **kwargs: Any):
        return self._current_regex().match(*args, **kwargs)

    def search(self, *args: Any, **kwargs: Any):
        return self._current_regex().search(*args, **kwargs)

    def fullmatch(self, *args: Any, **kwargs: Any):
        return self._current_regex().fullmatch(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._current_regex(), name)


COMMENT_CONTINUATION_RE = _PolicyBackedAnnotationRegexProxy(
    "COMMENT_CONTINUATION_RE",
)
COMMENTED_TASK_ENTRY_RE = _PolicyBackedAnnotationRegexProxy(
    "COMMENTED_TASK_ENTRY_RE",
)
TASK_ENTRY_RE = _PolicyBackedAnnotationRegexProxy(
    "TASK_ENTRY_RE",
)
YAML_LIKE_KEY_VALUE_RE = _PolicyBackedAnnotationRegexProxy(
    "YAML_LIKE_KEY_VALUE_RE",
)
YAML_LIKE_LIST_ITEM_RE = _PolicyBackedAnnotationRegexProxy(
    "YAML_LIKE_LIST_ITEM_RE",
)
TEMPLATED_INCLUDE_RE = _PolicyBackedRegexProxy("TEMPLATED_INCLUDE_RE")
