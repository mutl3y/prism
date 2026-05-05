"""Domain-owned YAML parsing policy plugin for fsrc."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import yaml

from prism.scanner_data.contracts_request import YamlParseFailure
from prism.scanner_io.loader import build_yaml_load_error, format_candidate_failure_path


class DefaultYAMLParsingPolicyPlugin:
    """Default YAML policy preserving current safe_load behavior and failure shape."""

    PLUGIN_IS_STATELESS: ClassVar[bool] = True

    @staticmethod
    def load_yaml_file(path: str | Path) -> object:
        candidate = Path(path)
        try:
            text = candidate.read_text(encoding="utf-8")
            return yaml.safe_load(text)
        except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
            raise build_yaml_load_error(candidate, exc) from exc

    @staticmethod
    def parse_yaml_candidate(
        candidate: str | Path,
        role_root: str | Path,
    ) -> YamlParseFailure | None:
        candidate_path = Path(candidate)
        role_root_path = Path(role_root)
        try:
            text = candidate_path.read_text(encoding="utf-8")
            yaml.safe_load(text)
            return None
        except (OSError, UnicodeDecodeError) as exc:
            return {
                "file": format_candidate_failure_path(candidate_path, role_root_path),
                "line": None,
                "column": None,
                "error": f"read_error: {exc}",
            }
        except (yaml.YAMLError, ValueError) as exc:
            mark = getattr(exc, "problem_mark", None)
            line = int(mark.line) + 1 if mark is not None else None
            column = int(mark.column) + 1 if mark is not None else None
            problem = str(getattr(exc, "problem", "") or "").strip()
            if not problem:
                problem = str(exc).splitlines()[0].strip()
            return {
                "file": format_candidate_failure_path(candidate_path, role_root_path),
                "line": line,
                "column": column,
                "error": problem,
            }


__all__ = ["DefaultYAMLParsingPolicyPlugin"]
