import pytest

from prism.feedback import apply_feedback_recommendations, load_feedback


def test_load_feedback_returns_none_for_none_source_branch():
    assert load_feedback(None) is None


def test_load_feedback_returns_none_for_empty_string_branch():
    assert load_feedback("") is None


def test_load_feedback_raises_for_missing_file_branch():
    with pytest.raises(FileNotFoundError):
        load_feedback("/nonexistent/path/feedback.json")


def test_load_feedback_reads_valid_json_file_branch(tmp_path):
    feedback_file = tmp_path / "feedback.json"
    feedback_file.write_text(
        '{"version": "1.0", "recommendations": []}', encoding="utf-8"
    )

    result = load_feedback(str(feedback_file))

    assert result is not None
    assert result["version"] == "1.0"


def test_load_feedback_raises_for_invalid_json_branch(tmp_path):
    feedback_file = tmp_path / "feedback.json"
    feedback_file.write_text("not valid json {{{", encoding="utf-8")

    with pytest.raises(Exception):
        load_feedback(str(feedback_file))


def test_load_feedback_raises_for_non_dict_json_branch(tmp_path):
    feedback_file = tmp_path / "feedback.json"
    feedback_file.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError):
        load_feedback(str(feedback_file))


def test_apply_feedback_recommendations_none_feedback_branch():
    result = apply_feedback_recommendations(None, include_collection_checks=True)

    assert result["include_collection_checks"] is True
    assert result["recommendations_applied"] == []


def test_apply_feedback_recommendations_empty_feedback_branch():
    result = apply_feedback_recommendations({}, include_collection_checks=False)

    assert result["include_collection_checks"] is False
    assert result["recommendations_applied"] == []


def test_apply_feedback_recommendations_passes_through_cli_flag_branch():
    result = apply_feedback_recommendations(
        {"recommendations": []}, include_collection_checks=True
    )

    assert result["include_collection_checks"] is True
