"""Comment-driven documentation parsing policy implementations."""

from __future__ import annotations

from pathlib import Path

from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
    COMMENT_CONTINUATION_RE,
)
from prism.scanner_plugins.parsers.comment_doc.marker_utils import get_marker_line_re
from prism.scanner_plugins.interfaces import CommentDrivenDocumentationPlugin


def _normalize_exclude_patterns(exclude_paths: list[str] | None) -> list[str]:
    if not exclude_paths:
        return []
    patterns: list[str] = []
    for raw in exclude_paths:
        if not isinstance(raw, str):
            continue
        candidate = raw.strip().replace("\\", "/")
        if candidate:
            patterns.append(candidate)
    return patterns


def _is_relpath_excluded(relpath: str, exclude_paths: list[str] | None) -> bool:
    relpath = relpath.strip().replace("\\", "/")
    if not relpath:
        return False

    for pattern in _normalize_exclude_patterns(exclude_paths):
        normalized_pattern = pattern.rstrip("/")
        if relpath == normalized_pattern or relpath.startswith(
            f"{normalized_pattern}/"
        ):
            return True
        if Path(relpath).match(pattern):
            return True
    return False


def _collect_relevant_yaml_files(
    role_root: Path,
    exclude_paths: list[str] | None,
) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    for subdir in ("tasks", "defaults", "vars", "handlers"):
        root = role_root / subdir
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".yml", ".yaml"}:
                continue
            relpath = path.relative_to(role_root).as_posix()
            if _is_relpath_excluded(relpath, exclude_paths):
                continue
            if path in seen:
                continue
            seen.add(path)
            files.append(path)

    return files


def extract_role_notes_from_comments(
    role_path: str,
    exclude_paths: list[str] | None = None,
    marker_prefix: str = "prism",
) -> dict[str, list[str]]:
    """Extract role note metadata from task comments."""
    marker_line_re = get_marker_line_re(marker_prefix)
    role_root = Path(role_path).resolve()
    categories: dict[str, list[str]] = {
        "warnings": [],
        "deprecations": [],
        "notes": [],
        "additionals": [],
    }

    for file_path in _collect_relevant_yaml_files(role_root, exclude_paths):
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        i = 0
        while i < len(lines):
            line = lines[i]
            match = marker_line_re.match(line)
            if not match:
                i += 1
                continue

            label = (match.group("label") or "").strip().lower()
            note_type = "note"
            if label == "warning":
                note_type = "warning"
            elif label == "deprecated":
                note_type = "deprecated"
            elif label in {"additional", "additionals"}:
                note_type = "additional"
            elif label in {"note", "notes"}:
                note_type = "note"
            else:
                i += 1
                continue

            text = (match.group("body") or "").strip()
            continuation: list[str] = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if marker_line_re.match(next_line):
                    break
                cont_match = COMMENT_CONTINUATION_RE.match(next_line)
                if not cont_match:
                    break
                continuation.append((cont_match.group(1) or "").strip())
                j += 1

            if continuation:
                text = " ".join(part for part in [text, *continuation] if part)

            if text:
                if note_type == "warning":
                    categories["warnings"].append(text)
                elif note_type == "deprecated":
                    categories["deprecations"].append(text)
                elif note_type == "additional":
                    categories["additionals"].append(text)
                else:
                    categories["notes"].append(text)

            i = j if j > i + 1 else i + 1

    return categories


class CommentDrivenDocumentationParser(CommentDrivenDocumentationPlugin):
    """Parser-owned implementation for comment-driven role notes."""

    def extract_role_notes_from_comments(
        self,
        role_path: str,
        exclude_paths: list[str] | None = None,
        marker_prefix: str = "prism",
    ) -> dict[str, list[str]]:
        return extract_role_notes_from_comments(
            role_path,
            exclude_paths=exclude_paths,
            marker_prefix=marker_prefix,
        )
