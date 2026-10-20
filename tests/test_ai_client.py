import pytest
from generator.config import Config
from generator.ai.client import AIClient, AIError, StreamError, check_connection


def _cfg():
    return Config("http://x/v1", "k", "m", 0.2)


def _fake_stream(monkeypatch, lines, status=200):
    class Resp:
        status_code = status

        def iter_lines(self):
            return iter(lines)

        def raise_for_status(self):
            pass

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())


def _chunk(text: str) -> str:
    return 'data: {"choices":[{"delta":{"content":"%s"}}]}' % text


def test_chat_stream_menyusun_delta(monkeypatch):
    _fake_stream(monkeypatch, [_chunk("A"), _chunk("B"), "data: [DONE]"])
    client = AIClient(_cfg())
    assert list(client.chat_stream([{"role": "user", "content": "ping"}])) == ["A", "B"]


def test_chat_stream_http400_jadi_stream_error(monkeypatch):
    _fake_stream(monkeypatch, [], status=400)
    client = AIClient(_cfg())
    with pytest.raises(StreamError):
        list(client.chat_stream([{"role": "user", "content": "ping"}]))


def test_chat_stream_cancel_berhenti(monkeypatch):
    import threading

    _fake_stream(monkeypatch, [_chunk("A"), _chunk("B"), "data: [DONE]"])
    cancel = threading.Event()
    stream = AIClient(_cfg()).chat_stream([{"role": "user", "content": "ping"}], cancel=cancel)
    assert next(stream) == "A"
    cancel.set()
    assert list(stream) == []


def test_chat_returns_content(monkeypatch):
    import json as _json

    class Resp:
        status_code = 200
        text = _json.dumps({"choices": [{"message": {"content": "halo"}}]})

        def json(self):
            return _json.loads(self.text)

        def raise_for_status(self):
            pass

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    assert AIClient(_cfg()).chat([{"role": "user", "content": "hai"}]) == "halo"


def test_chat_allows_long_generation_timeout(monkeypatch):
    """Generate laporan panjang bisa lebih dari semenit; batas klien harus longgar."""
    import json as _json

    dipakai = {}

    class Resp:
        status_code = 200
        text = _json.dumps({"choices": [{"message": {"content": "ok"}}]})

        def json(self):
            return _json.loads(self.text)

        def raise_for_status(self):
            pass

    def rekam(*a, **k):
        dipakai["timeout"] = k.get("timeout")
        return Resp()

    monkeypatch.setattr("generator.ai.client.requests.post", rekam)
    AIClient(_cfg()).chat([{"role": "user", "content": "hai"}])
    assert dipakai["timeout"] >= 120, dipakai["timeout"]


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


def test_chat_parses_sse_body_with_done_marker(monkeypatch):
    body = (
        '{"choices":[{"finish_reason":"stop","index":0,"message":'
        '{"content":"pong!","role":"assistant"}}],'
        '"usage":{"total_tokens":61}}data: [DONE]\n\n'
    )

    class Resp:
        status_code = 200
        text = body

        def raise_for_status(self):
            pass

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    assert AIClient(_cfg()).chat([{"role": "user", "content": "ping"}]) == "pong!"


def test_chat_parses_prefixed_sse_events(monkeypatch):
    body = 'data: {"choices":[{"message":{"content":"halo"}}]}\n\ndata: [DONE]\n'

    class Resp:
        status_code = 200
        text = body

        def raise_for_status(self):
            pass

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    assert AIClient(_cfg()).chat([{"role": "user", "content": "ping"}]) == "halo"


def test_unparseable_body_raises_clear_error(monkeypatch):
    class Resp:
        status_code = 200
        text = "<html>bukan json</html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    with pytest.raises(AIError, match="tidak dikenal"):
        AIClient(_cfg()).chat([{"role": "user", "content": "ping"}])
