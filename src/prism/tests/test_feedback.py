import json
from urllib.error import HTTPError, URLError

import pytest

from prism import feedback


def test_load_feedback_returns_none_for_missing_source():
    assert feedback.load_feedback(None) is None
    assert feedback.load_feedback("") is None


def test_load_feedback_reads_local_file(tmp_path):
    path = tmp_path / "feedback.json"
    path.write_text(
        json.dumps({"version": "1.0", "recommendations": [{"type": "check"}]}),
        encoding="utf-8",
    )

    payload = feedback.load_feedback(str(path))

    assert payload is not None
    assert payload["version"] == "1.0"


def test_load_feedback_raises_for_missing_local_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="feedback file not found"):
        feedback.load_feedback(str(tmp_path / "missing.json"))


def test_load_feedback_raises_for_invalid_json(tmp_path):
    path = tmp_path / "feedback.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError, match="invalid JSON"):
        feedback.load_feedback(str(path))


def test_load_feedback_raises_when_payload_is_not_object(tmp_path):
    path = tmp_path / "feedback.json"
    path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON object"):
        feedback.load_feedback(str(path))


def test_load_feedback_reads_http_source(monkeypatch):
    class _FakeResponse:
        def read(self):
            return b'{"version":"1.0"}'

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=10):
        assert req.full_url == "https://example.test/feedback"
        assert timeout == 10
        return _FakeResponse()

    monkeypatch.setattr(feedback, "urlopen", fake_urlopen)

    payload = feedback.load_feedback("https://example.test/feedback")

    assert payload is not None
    assert payload["version"] == "1.0"


def test_load_feedback_wraps_url_error(monkeypatch):
    def fake_urlopen(req, timeout=10):
        raise URLError("timeout")

    monkeypatch.setattr(feedback, "urlopen", fake_urlopen)

    with pytest.raises(URLError, match="failed to fetch feedback"):
        feedback.load_feedback("https://example.test/feedback")


def test_load_feedback_wraps_http_error(monkeypatch):
    def fake_urlopen(req, timeout=10):
        raise HTTPError(req.full_url, 500, "server", {}, None)

    monkeypatch.setattr(feedback, "urlopen", fake_urlopen)

    with pytest.raises(HTTPError, match="API returned 500"):
        feedback.load_feedback("https://example.test/feedback")


def test_apply_feedback_recommendations_returns_defaults():
    result = feedback.apply_feedback_recommendations(
        None, include_collection_checks=True
    )

    assert result["include_collection_checks"] is True
    assert result["recommendations_applied"] == []


def test_apply_feedback_recommendations_keeps_flag_until_future_phase():
    result = feedback.apply_feedback_recommendations(
        {
            "recommendations": [
                {"type": "check_collection_compliance", "display": False}
            ]
        },
        include_collection_checks=False,
    )

    assert result["include_collection_checks"] is False
    assert result["recommendations_applied"] == []
