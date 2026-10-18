import pytest
from generator.config import Config
from generator.ai.client import AIClient, AIError, check_connection


def _cfg():
    return Config("http://x/v1", "k", "m", 0.2)


def test_chat_returns_content(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "halo"}}]}

        def raise_for_status(self):
            pass

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    assert AIClient(_cfg()).chat([{"role": "user", "content": "hai"}]) == "halo"


def test_chat_http_error_raises_ai_error(monkeypatch):
    class Resp:
        status_code = 500
        text = "boom"

        def json(self):
            return {}

        def raise_for_status(self):
            raise Exception("500")

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    with pytest.raises(AIError):
        AIClient(_cfg()).chat([{"role": "user", "content": "hai"}])


def test_chat_wraps_unexpected_exception(monkeypatch):
    def boom(*a, **k):
        raise Exception("jaringan putus")

    monkeypatch.setattr("generator.ai.client.requests.post", boom)
    with pytest.raises(AIError):
        AIClient(_cfg()).chat([{"role": "user", "content": "hai"}])


def test_check_connection_reports_failure(monkeypatch):
    def boom(*a, **k):
        raise AIError("offline")

    monkeypatch.setattr("generator.ai.client.AIClient.chat", lambda self, *a, **k: boom())
    ok, msg = check_connection(AIClient(_cfg()))
    assert ok is False and msg
