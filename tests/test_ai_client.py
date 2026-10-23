import pytest
from generator.config import Config
from generator.ai.client import AIClient, AIError, StreamError, check_connection


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Cegah jeda time.sleep nyata selama tes unit."""
    monkeypatch.setattr("generator.ai.client.time.sleep", lambda s: None)


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


# --- Task 2.5: daftar model dari GET {base}/models ---------------------------


def _fake_get(monkeypatch, payload=None, status=200, raises=None):
    if raises is not None:
        def boom(*a, **k):
            raise raises

        monkeypatch.setattr("generator.ai.client.requests.get", boom)
        return

    class Resp:
        def __init__(self):
            self.status_code = status

        def json(self):
            if isinstance(payload, Exception):
                raise payload
            return payload

    monkeypatch.setattr("generator.ai.client.requests.get", lambda *a, **k: Resp())


def test_list_models_mengembalikan_id_urut_server(monkeypatch):
    from generator.ai.client import list_models

    _fake_get(monkeypatch, {"data": [{"id": "m2"}, {"id": "m1"}]})
    assert list_models(_cfg()) == ["m2", "m1"]


def test_list_models_http_400_ditolak(monkeypatch):
    from generator.ai.client import list_models

    _fake_get(monkeypatch, {}, status=404)
    with pytest.raises(AIError):
        list_models(_cfg())


def test_list_models_format_asam_ditolak(monkeypatch):
    from generator.ai.client import list_models

    _fake_get(monkeypatch, {"data": "bukan-list"})
    with pytest.raises(AIError, match="tidak mendukung"):
        list_models(_cfg())


def test_list_models_jaringan_error_dibungkus(monkeypatch):
    from generator.ai.client import list_models

    _fake_get(monkeypatch, raises=Exception("jaringan putus"))
    with pytest.raises(AIError, match="jaringan putus"):
        list_models(_cfg())


# --- Task 2.3: Retry, batas token, dan output terpotong ----------------------


def test_chat_retry_429_lalu_sukses(monkeypatch):
    import json as _json

    slept = []
    monkeypatch.setattr("generator.ai.client.time.sleep", lambda s: slept.append(s))

    calls = 0

    class Resp429:
        status_code = 429
        text = "rate limit"
        headers = {"Retry-After": "3"}

        def raise_for_status(self):
            pass

    class Resp200:
        status_code = 200
        text = _json.dumps({"choices": [{"message": {"content": "hasil sukses"}}]})
        headers = {}

        def raise_for_status(self):
            pass

    def mock_post(*a, **k):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Resp429()
        return Resp200()

    monkeypatch.setattr("generator.ai.client.requests.post", mock_post)
    client = AIClient(_cfg())
    res = client.chat([{"role": "user", "content": "ping"}])
    assert res == "hasil sukses"
    assert calls == 2
    assert slept == [3.0]


def test_chat_retry_429_tiga_kali_berakhir_aierror(monkeypatch):
    slept = []
    monkeypatch.setattr("generator.ai.client.time.sleep", lambda s: slept.append(s))

    calls = 0

    class Resp429:
        status_code = 429
        text = "rate limit exceeded"
        headers = {}

        def raise_for_status(self):
            pass

    def mock_post(*a, **k):
        nonlocal calls
        calls += 1
        return Resp429()

    monkeypatch.setattr("generator.ai.client.requests.post", mock_post)
    client = AIClient(_cfg())
    with pytest.raises(AIError, match="HTTP 429"):
        client.chat([{"role": "user", "content": "ping"}])
    assert calls == 4  # 1 initial + 3 retries
    assert slept == [2.0, 4.0, 8.0]


def test_chat_retry_timeout_berakhir_aierror(monkeypatch):
    import requests

    slept = []
    monkeypatch.setattr("generator.ai.client.time.sleep", lambda s: slept.append(s))
    calls = 0

    def mock_post(*a, **k):
        nonlocal calls
        calls += 1
        raise requests.exceptions.Timeout("koneksi timeout")

    monkeypatch.setattr("generator.ai.client.requests.post", mock_post)
    client = AIClient(_cfg())
    with pytest.raises(AIError, match="timeout setelah 3 retry"):
        client.chat([{"role": "user", "content": "ping"}])
    assert calls == 4
    assert slept == [2.0, 4.0, 8.0]


def test_chat_kirim_max_tokens_eksplisit_dan_streaming_timeout(monkeypatch):
    import json as _json

    rekam = {}

    class RespChat:
        status_code = 200
        text = _json.dumps({"choices": [{"message": {"content": "ok"}}]})
        headers = {}

        def raise_for_status(self):
            pass

    class RespStream:
        status_code = 200
        headers = {}

        def iter_lines(self):
            return iter(['data: {"choices":[{"delta":{"content":"ok"}}]}', "data: [DONE]"])

        def raise_for_status(self):
            pass

    def mock_post(*a, **k):
        rekam["payload"] = k.get("json")
        rekam["timeout"] = k.get("timeout")
        if k.get("stream"):
            return RespStream()
        return RespChat()

    monkeypatch.setattr("generator.ai.client.requests.post", mock_post)
    client = AIClient(_cfg())

    # 1. Non-streaming: max_tokens default 4096
    client.chat([{"role": "user", "content": "ping"}])
    assert rekam["payload"]["max_tokens"] == 4096
    assert rekam["timeout"] == 120

    # 2. Streaming: max_tokens default 4096 dan timeout 300
    list(client.chat_stream([{"role": "user", "content": "ping"}]))
    assert rekam["payload"]["max_tokens"] == 4096
    assert rekam["timeout"] == 300


def test_chat_finish_reason_length_raises_aierror(monkeypatch):
    import json as _json

    class Resp:
        status_code = 200
        text = _json.dumps({
            "choices": [{
                "finish_reason": "length",
                "message": {"content": "teks terpotong di tengah"}
            }]
        })
        headers = {}

        def raise_for_status(self):
            pass

    monkeypatch.setattr("generator.ai.client.requests.post", lambda *a, **k: Resp())
    client = AIClient(_cfg())
    with pytest.raises(AIError, match="finish_reason=length"):
        client.chat([{"role": "user", "content": "tulis bab"}])


def test_chat_stream_finish_reason_length_raises_stream_error(monkeypatch):
    lines = [
        'data: {"choices":[{"delta":{"content":"awal kalimat "}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
    ]
    _fake_stream(monkeypatch, lines)
    client = AIClient(_cfg())
    stream = client.chat_stream([{"role": "user", "content": "tulis bab"}])
    assert next(stream) == "awal kalimat "
    with pytest.raises(StreamError, match="finish_reason=length"):
        next(stream)


def test_output_terpotong_memicu_kegagalan_batch(monkeypatch):
    from generator.ai.content import generate_sections
    from generator.ai.citation import Author, Source

    class ClientOutputTerpotong:
        def chat(self, *a, **k):
            raise AIError("Respons AI terpotong karena batas token (finish_reason=length).")

    sources = [Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal")]
    with pytest.raises(ValueError, match="Respons AI tidak terbaca"):
        generate_sections("tema", ["Pendahuluan"], sources, ["teks sumber"], ClientOutputTerpotong())


def test_batch_terpotong_gagal_tapi_batch_lain_selamat(monkeypatch):
    from generator.ai.content import generate_sections
    from generator.ai.citation import Author, Source
    import json as _json

    valid_reply = _json.dumps({
        "sections": [{
            "title": "Pendahuluan",
            "paragraphs": [{
                "sentences": [{
                    "text": "Kalimat yang berhasil.",
                    "quote": "teks",
                    "source_ids": [0],
                    "is_factual": True,
                }]
            }]
        }]
    })

    calls = 0

    class AlternatingClient:
        def chat(self, *a, **k):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise AIError("Respons AI terpotong karena batas token (finish_reason=length).")
            return valid_reply

    sources = [Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal")]
    long_source = "kalimat sumber " * 1000
    secs = generate_sections(
        "tema",
        ["Pendahuluan"],
        sources,
        [long_source],
        AlternatingClient(),
        max_prompt_chars=500,
    )
    assert len(secs) >= 1
    assert secs[0].paragraphs[0].sentences[0].text == "Kalimat yang berhasil."
