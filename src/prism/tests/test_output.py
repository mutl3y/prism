from prism.scanner_io import output


def test_render_final_output_falls_back_to_html_for_unknown_format():
    rendered = output.render_final_output(
        markdown_content="# Heading\n\nBody",
        output_format="rst",
        title="Demo",
        payload=None,
    )

    assert isinstance(rendered, str)
    assert "<html>" in rendered
    assert "Heading" in rendered


def test_render_final_output_json_includes_normalized_warnings():
    payload = output.build_final_output_payload(
        role_name="demo",
        description="desc",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={"scan_degraded": True},
    )

    rendered = output.render_final_output(
        markdown_content="",
        output_format="json",
        title="Demo",
        payload=payload,
    )

    assert '"warnings"' in rendered
    assert '"role_scan_degraded"' in rendered
