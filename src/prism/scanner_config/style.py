"""Style guide path resolution and configuration."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def default_style_guide_user_paths(
    xdg_data_home_env: str = "XDG_DATA_HOME",
    style_guide_data_dirname: str = "prism",
    style_guide_source_filename: str = "STYLE_GUIDE_SOURCE.md",
) -> list[Path]:
    xdg_data_home = os.environ.get(xdg_data_home_env)
    if xdg_data_home:
        data_home = Path(xdg_data_home).expanduser()
    else:
        data_home = (Path.home() / ".local" / "share").expanduser()
    return [
        data_home / style_guide_data_dirname / style_guide_source_filename,
    ]


def resolve_default_style_guide_source(
    explicit_path: str | None = None,
    env_style_guide_source_path: str = "PRISM_STYLE_SOURCE",
    xdg_data_home_env: str = "XDG_DATA_HOME",
    style_guide_data_dirname: str = "prism",
    style_guide_source_filename: str = "STYLE_GUIDE_SOURCE.md",
    system_style_guide_source_path: Path | None = None,
    default_style_guide_source_path: Path | None = None,
) -> str:
    if system_style_guide_source_path is None:
        system_style_guide_source_path = (
            Path("/var/lib") / style_guide_data_dirname / style_guide_source_filename
        )
    if default_style_guide_source_path is None:
        _fsrc_templates = (
            Path(__file__).parent.parent / "templates" / style_guide_source_filename
        )
        if _fsrc_templates.parent.is_dir():
            default_style_guide_source_path = _fsrc_templates
        else:
            # Fall back to src lane templates (path resolution only, not import)
            default_style_guide_source_path = (
                Path(__file__).parent.parent.parent.parent.parent.parent
                / "src"
                / "prism"
                / "templates"
                / style_guide_source_filename
            )

    if explicit_path:
        explicit_candidate = Path(explicit_path).expanduser()
        if explicit_candidate.is_file():
            return str(explicit_candidate.resolve())
        raise FileNotFoundError(f"style source path not found: {explicit_path}")

    candidates: list[Path] = []

    env_style_source = os.environ.get(env_style_guide_source_path)
    if env_style_source:
        candidates.append(Path(env_style_source).expanduser())

    candidates.append(Path.cwd() / style_guide_source_filename)
    candidates.extend(
        default_style_guide_user_paths(
            xdg_data_home_env=xdg_data_home_env,
            style_guide_data_dirname=style_guide_data_dirname,
            style_guide_source_filename=style_guide_source_filename,
        )
    )
    candidates.append(system_style_guide_source_path)
    candidates.append(default_style_guide_source_path)

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())

    return str(default_style_guide_source_path.resolve())


def _record_display_titles_warning(
    warning_collector: list[str] | None,
    *,
    code: str,
    cfg_file: Path,
    error: Exception | str,
) -> None:
    if warning_collector is None:
        return
    warning_collector.append(f"{code}: {cfg_file}: {error}")


def load_section_display_titles(
    display_titles_path: Path,
    *,
    strict: bool = False,
    warning_collector: list[str] | None = None,
    yaml_invalid_code: str = "README_SECTION_DISPLAY_TITLES_YAML_INVALID",
    io_error_code: str = "README_SECTION_DISPLAY_TITLES_IO_ERROR",
    shape_invalid_code: str = "README_SECTION_DISPLAY_TITLES_SHAPE_INVALID",
) -> dict[str, str]:
    """Load optional section display-title overrides from bundled data YAML."""
    if not display_titles_path.is_file():
        return {}
    try:
        raw = yaml.safe_load(display_titles_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        if strict:
            raise RuntimeError(
                f"{yaml_invalid_code}: {display_titles_path}: {exc}"
            ) from exc
        _record_display_titles_warning(
            warning_collector,
            code=yaml_invalid_code,
            cfg_file=display_titles_path,
            error=exc,
        )
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        if strict:
            raise RuntimeError(
                f"{io_error_code}: {display_titles_path}: {exc}"
            ) from exc
        _record_display_titles_warning(
            warning_collector,
            code=io_error_code,
            cfg_file=display_titles_path,
            error=exc,
        )
        return {}
    if not isinstance(raw, dict):
        _record_display_titles_warning(
            warning_collector,
            code=shape_invalid_code,
            cfg_file=display_titles_path,
            error="config root must be a mapping",
        )
        return {}
    payload = raw.get("display_titles")
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        _record_display_titles_warning(
            warning_collector,
            code=shape_invalid_code,
            cfg_file=display_titles_path,
            error="display_titles must be a mapping",
        )
        return {}

    parsed: dict[str, str] = {}
    for section_id, display_title in payload.items():
        if not isinstance(section_id, str) or not isinstance(display_title, str):
            continue
        sid = section_id.strip()
        label = display_title.strip()
        if sid and label:
            parsed[sid] = label
    return parsed
