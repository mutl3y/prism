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
