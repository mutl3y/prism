"""T1-02: targeted unit tests to lift coverage on small under-tested surfaces.

These tests exercise small helper modules whose behavior was below 70% line
coverage. They use no I/O and no fixtures beyond stdlib + the imported APIs.
"""

from __future__ import annotations

import pytest

# ---- scanner_plugins/kubernetes/__init__.py -------------------------------


def test_kubernetes_reserved_target_metadata_is_consistent() -> None:
    from prism.scanner_plugins import kubernetes as k

    entry = k.build_reserved_target_classifier_entry()
    assert entry["target_type"] == "kubernetes_manifest"
    assert entry["plugin_id"] == "prism.kubernetes.v1"
    assert entry["support_state"] == "unsupported"
    assert isinstance(entry["matchers"], list) and entry["matchers"]
    # mutating returned matchers must not affect module constants
    entry["matchers"].append({"kind": "x", "pattern": "y"})
    assert (
        k.KUBERNETES_RESERVED_TARGET_CLASSIFIER_ENTRY["matchers"] != entry["matchers"]
    )

    cap = k.build_reserved_target_capability_response()
    assert cap["error_code"] == k.UNSUPPORTED_TARGET_CAPABILITY_ERROR_CODE
    assert cap["degraded_success"] is False

    outcome = k.build_unsupported_scan_pipeline_outcome()
    assert outcome["outcome"] == "PLATFORM_NOT_SUPPORTED"
    assert outcome["supported"] is False
    assert outcome["plugin_id"] == "prism.kubernetes.v1"


# ---- scanner_plugins/terraform/__init__.py --------------------------------


def test_terraform_reserved_target_metadata_is_consistent() -> None:
    from prism.scanner_plugins import terraform as t

    entry = t.build_reserved_target_classifier_entry()
    assert entry["target_type"] == "terraform_module"
    assert entry["support_state"] == "stubbed"

    cap = t.build_reserved_target_capability_response()
    assert cap["error_code"] == t.STUBBED_TARGET_CAPABILITY_ERROR_CODE

    outcome = t.build_unsupported_scan_pipeline_outcome()
    assert outcome["outcome"] == "PLATFORM_NOT_SUPPORTED"
    assert outcome["plugin_id"] == "prism.terraform.v1"


# ---- scanner_plugins/audit/__init__.py ------------------------------------


def test_audit_plugin_protocol_runtime_checkable() -> None:
    from prism.scanner_plugins.audit import AuditPlugin

    class _Conforms:
        AUDIT_PLUGIN_NAME = "x"

        def evaluate(self, scan_payload, rules):
            return []

    class _Missing:
        pass

    assert isinstance(_Conforms(), AuditPlugin)
    assert not isinstance(_Missing(), AuditPlugin)


# ---- scanner_io/__init__.py -----------------------------------------------


def test_scanner_io_package_public_api_only() -> None:
    import prism.scanner_io as io_pkg

    public = set(io_pkg.__all__)
    assert "OutputOrchestrator" in public
    assert "render_collection_markdown" in public
    assert dir(io_pkg) == sorted(public)
    with pytest.raises(AttributeError, match="private member"):
        io_pkg._not_real  # noqa: B018
    with pytest.raises(AttributeError, match="has no attribute"):
        io_pkg.does_not_exist  # noqa: B018


# ---- scanner_readme/__init__.py -------------------------------------------


def test_scanner_readme_package_public_api_only() -> None:
    import prism.scanner_readme as r

    assert "render_readme" in r.__all__
    assert "format_heading" in r.__all__
    assert dir(r) == sorted(r.__all__)
    with pytest.raises(AttributeError, match="private member"):
        r._hidden  # noqa: B018
    with pytest.raises(AttributeError):
        r.totally_made_up  # noqa: B018


def test_scanner_readme_refresh_policy_derived_state_delegates() -> None:
    import prism.scanner_readme as r

    r.refresh_policy_derived_state({"section_aliases": {"foo": "bar"}})
    snapshot = r.get_style_section_aliases_snapshot()
    assert snapshot.get("foo") == "bar"


# ---- scanner_readme/style_formatter.py ------------------------------------


def test_normalize_style_heading_strips_links_and_punct() -> None:
    from prism.scanner_readme.style_formatter import normalize_style_heading

    assert normalize_style_heading("[Variables](#vars)") == "variables"
    assert normalize_style_heading("Role  Variables!") == "role variables"


def test_format_heading_atx_and_setext() -> None:
    from prism.scanner_readme.style_formatter import format_heading

    assert format_heading("Title", 1, "atx") == "# Title"
    assert format_heading("Sub", 3, "atx") == "### Sub"
    assert format_heading("Hi", 1, "setext") == "Hi\n=="
    assert format_heading("Sub", 2, "setext") == "Sub\n---"
    # level >= 3 falls back to ATX even when style is setext
    assert format_heading("Deep", 4, "setext") == "#### Deep"


# ---- scanner_readme/style_config.py ---------------------------------------


def test_style_section_aliases_scope_isolates_overrides() -> None:
    from prism.scanner_readme.style_config import (
        get_style_section_aliases_snapshot,
        style_section_aliases_scope,
    )

    baseline = get_style_section_aliases_snapshot()
    with style_section_aliases_scope({"only": "this"}):
        assert get_style_section_aliases_snapshot() == {"only": "this"}
    assert get_style_section_aliases_snapshot() == baseline


def test_refresh_policy_derived_state_ignores_non_string_pairs() -> None:
    from prism.scanner_readme.style_config import (
        STYLE_SECTION_ALIASES,
        refresh_policy_derived_state,
    )

    refresh_policy_derived_state(
        {"section_aliases": {"good": "ok", 1: "skip", "drop": 2}}
    )
    assert STYLE_SECTION_ALIASES.get("good") == "ok"
    assert 1 not in STYLE_SECTION_ALIASES
    assert "drop" not in STYLE_SECTION_ALIASES


def test_refresh_policy_derived_state_no_change_when_missing() -> None:
    from prism.scanner_readme.style_config import refresh_policy_derived_state

    # Should not raise and should be a no-op for non-dict
    refresh_policy_derived_state({"section_aliases": "not a dict"})
    refresh_policy_derived_state({})


def test_refresh_policy_derived_state_replaces_public_alias_snapshot() -> None:
    from prism.scanner_readme.style_config import (
        STYLE_SECTION_ALIASES,
        refresh_policy_derived_state,
    )

    refresh_policy_derived_state({"section_aliases": {"first": "value"}})
    before_refresh = dict(STYLE_SECTION_ALIASES)

    refresh_policy_derived_state({"section_aliases": {"second": "value"}})

    assert before_refresh == {"first": "value"}
    assert dict(STYLE_SECTION_ALIASES) == {"second": "value"}


# ---- api_layer/payload_helpers.py ----------------------------------------


def test_normalize_scan_role_payload_shape_aliases_and_warnings() -> None:
    from prism.api_layer.payload_helpers import normalize_scan_role_payload_shape

    payload = {
        "display_variables": [1, 2],
        "requirements_display": [{"name": "x"}],
        "undocumented_default_filters": ["a"],
        "metadata": {"warnings": ["w1", "w2"]},
    }
    out = normalize_scan_role_payload_shape(payload)
    assert out["variables"] == [1, 2]
    assert out["requirements"] == [{"name": "x"}]
    assert out["default_filters"] == ["a"]
    # original keys preserved
    assert out["display_variables"] == [1, 2]


def test_normalize_scan_role_payload_shape_handles_non_dict_metadata() -> None:
    from prism.api_layer.payload_helpers import normalize_scan_role_payload_shape

    out = normalize_scan_role_payload_shape({"metadata": "ignored"})
    assert "warnings" not in out


# ---- scanner_data/di_helpers.py -------------------------------------------


class _FakeDI:
    def __init__(self, scan_options):
        self.scan_options = scan_options


def test_scan_options_from_di_variants() -> None:
    from prism.scanner_core.di_helpers import scan_options_from_di

    assert scan_options_from_di(None) is None
    assert scan_options_from_di(_FakeDI(None)) is None
    assert scan_options_from_di(_FakeDI({"k": 1})) == {"k": 1}


def test_get_prepared_policy_or_none_paths() -> None:
    from prism.scanner_core.di_helpers import get_prepared_policy_or_none

    assert get_prepared_policy_or_none(None, "p") is None
    assert get_prepared_policy_or_none(_FakeDI({}), "p") is None
    assert (
        get_prepared_policy_or_none(_FakeDI({"prepared_policy_bundle": "no"}), "p")
        is None
    )
    di = _FakeDI({"prepared_policy_bundle": {"p": object()}})
    assert (
        get_prepared_policy_or_none(di, "p")
        is di.scan_options["prepared_policy_bundle"]["p"]
    )


def test_require_prepared_policy_returns_or_raises() -> None:
    from prism.scanner_core.di_helpers import require_prepared_policy

    sentinel = object()
    di = _FakeDI({"prepared_policy_bundle": {"p": sentinel}})
    assert require_prepared_policy(di, "p", "ctx") is sentinel
    with pytest.raises(ValueError, match="prepared_policy_bundle.missing"):
        require_prepared_policy(di, "missing", "ctx")


# ---- scanner_plugins/parsers/comment_doc/marker_utils.py ------------------


def test_normalize_marker_prefix_validation() -> None:
    from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
        DEFAULT_DOC_MARKER_PREFIX,
        normalize_marker_prefix,
    )

    assert normalize_marker_prefix(None) == DEFAULT_DOC_MARKER_PREFIX
    assert normalize_marker_prefix("") == DEFAULT_DOC_MARKER_PREFIX
    assert normalize_marker_prefix("   ") == DEFAULT_DOC_MARKER_PREFIX
    assert normalize_marker_prefix("bad space") == DEFAULT_DOC_MARKER_PREFIX
    assert normalize_marker_prefix("ok-1.x_y") == "ok-1.x_y"
    assert normalize_marker_prefix(123) == DEFAULT_DOC_MARKER_PREFIX  # type: ignore[arg-type]


def test_get_marker_line_re_matches_marker_lines() -> None:
    from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
        get_marker_line_re,
    )

    pattern = get_marker_line_re("prism")
    m = pattern.match("# prism~runbook: do the thing")
    assert m is not None
    assert m.group("label") == "runbook"
    assert m.group("body").strip() == "do the thing"

    custom = get_marker_line_re("doc-x")
    m2 = custom.match("#doc-x ~ note: hi")
    assert m2 is not None and m2.group("label") == "note"


def test_get_marker_line_re_cache_is_bounded() -> None:
    from prism.scanner_plugins.parsers.comment_doc.marker_utils import (
        get_marker_line_re,
    )

    get_marker_line_re.cache_clear()

    for index in range(160):
        get_marker_line_re(f"doc-{index}")

    cache_info = get_marker_line_re.cache_info()
    assert cache_info.maxsize == 128
    assert cache_info.currsize <= cache_info.maxsize
