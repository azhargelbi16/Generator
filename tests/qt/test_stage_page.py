"""Tes Panggung Penuh Qt: dokumen menulis dirinya, dapur AI, batal (Task 3.2)."""

import json
import time

from PySide6.QtTest import QTest

from generator.verification import (
    STATUS_NON_FACTUAL,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
)

SOURCE_TEXT = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah secara berkelanjutan untuk masa depan"
)
TEKS_PELENGKAP = (
    "pengelolaan lahan sawah memerlukan perhatian serius dari semua pihak "
    "terkait hingga tingkat daerah di seluruh nusantara ini sekarang"
)
GOOD_QUOTE = "pertanian organik di indonesia sangat penting bagi petani"

# (teks, quote, is_factual) — satu bab tiga kalimat dengan tiga status berbeda.
BAB_SATU = [
    ("Pertanian organik menjadi fondasi penting.", GOOD_QUOTE, True),
    ("Klaim ini tidak memiliki dasar yang jelas.", "tak ada di sumber", True),
    ("Bab ini membahas latar belakang masalah.", "", False),
]
BAB_DUA = [
    ("Metode penelitian dipilih secara hati-hati.", GOOD_QUOTE, True),
    ("Data dikumpulkan dari berbagai daerah.", GOOD_QUOTE, True),
    ("Hasil akan dibahas pada bagian berikutnya.", GOOD_QUOTE, True),
]


def _bab_json(items):
    sentences = [
        {"text": text, "quote": quote, "source_ids": [0], "is_factual": factual}
        for text, quote, factual in items
    ]
    return json.dumps(
        {"sections": [{"level": 1, "title": "Bab", "paragraphs": [{"sentences": sentences}]}]},
        ensure_ascii=False,
    )


class _State:
    """Stub controller_state: cukup menyediakan generate_plan().

    Dua sumber dengan total teks > max_prompt_chars (200) supaya engine
    membuat tepat dua batch — fake client menghasilkan satu bab per batch.
    """

    def __init__(self):
        from generator.ai.citation import Author, Source

        self._sources = [
            Source([Author("Santoso", "Budi")], "2020", "Judul", "Jurnal"),
            Source([Author("Manurung", "Ana")], "2021", "Judul Dua", "Jurnal"),
        ]
        self._texts = [SOURCE_TEXT, TEKS_PELENGKAP]

    def generate_plan(self):
        return ("Topik Laporan", ["Bab Satu", "Bab Dua"], self._sources, self._texts)


class FakeStreamClient:
    """chat_stream mengalirkan satu bab JSON per panggilan, potongan demi potongan."""

    def __init__(self, payloads, delay=0.004):
        self._payloads = list(payloads)
        self._delay = delay
        self._calls = 0

    def _next(self):
        payload = self._payloads[self._calls % len(self._payloads)]
        self._calls += 1
        return payload

    def chat_stream(self, messages, json_mode=False, cancel=None):
        payload = self._next()
        for i in range(0, len(payload), 6):
            if cancel is not None and cancel.is_set():
                return
            time.sleep(self._delay)
            yield payload[i : i + 6]

    def chat(self, messages, json_mode=False):
        return self._next()


class FakeBatchClient:
    """Tanpa chat_stream: fallback reveal per batch lewat chat()."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self._calls = 0

    def chat(self, messages, json_mode=False):
        payload = self._payloads[self._calls % len(self._payloads)]
        self._calls += 1
        return payload


def _stage(client):
    from generator.qt.stage_page import StagePage

    stage = StagePage()
    stage._client_factory = lambda: client
    return stage


def _run(qapp, stage, state, timeout_ms=15000, max_prompt_chars=200):
    finished = []
    stage.finished.connect(lambda cancelled: finished.append(cancelled))
    stage.start_generate(state, max_prompt_chars=max_prompt_chars)
    deadline = time.monotonic() + timeout_ms / 1000
    while not finished and time.monotonic() < deadline:
        qapp.processEvents()
        QTest.qWait(5)
    assert finished, "finished tidak pernah dipancarkan"
    return finished[0]


def test_dokumen_enam_kalimat_berurutan_dengan_lencana(qapp, db_tmp):
    client = FakeStreamClient([_bab_json(BAB_SATU), _bab_json(BAB_DUA)])
    stage = _stage(client)
    batch_labels = []
    stage.batchProgress.connect(
        lambda n, total, count, hint: batch_labels.append(stage._batch_label.text())
    )
    assert _run(qapp, stage, _State()) is False

    text = stage._document.toPlainText()
    kalimat = [item[0] for item in BAB_SATU + BAB_DUA]
    positions = [text.index(k) for k in kalimat]
    assert positions == sorted(positions), "kalimat tidak berurutan"
    assert "[terverifikasi]" in text
    assert "[belum terverifikasi]" in text
    assert "[bukan klaim faktual]" in text
    # Lencana sesuai status tiap kalimat.
    assert f"{BAB_SATU[0][0]} [terverifikasi]" in text
    assert f"{BAB_SATU[1][0]} [belum terverifikasi]" in text
    assert f"{BAB_SATU[2][0]} [bukan klaim faktual]" in text
    # Bar progres per bab memuat "Bab 1 dari 2".
    assert "Bab 1 dari 2" in batch_labels
    # Panel Dapur AI memuat narasi minimal.
    kitchen = [stage._kitchen.item(i).text() for i in range(stage._kitchen.count())]
    joined = "\n".join(kitchen)
    assert "Membaca sumber..." in joined
    assert "Menulis bab 1..." in joined
    assert "Memverifikasi kutipan" in joined


def test_eta_label_berubah_selama_proses(qapp, db_tmp):
    client = FakeStreamClient([_bab_json(BAB_SATU), _bab_json(BAB_DUA)], delay=0.03)
    stage = _stage(client)
    eta_values = []
    stage.batchProgress.connect(
        lambda n, total, count, hint: eta_values.append(stage._eta_label.text())
    )
    _run(qapp, stage, _State())
    assert len(set(eta_values)) >= 2, eta_values


def test_batal_setelah_tiga_kalimat_finished_true(qapp, db_tmp):
    client = FakeStreamClient([_bab_json(BAB_SATU), _bab_json(BAB_DUA)], delay=0.03)
    stage = _stage(client)
    arrived = []

    def _batal_setelah_3(_text, _status):
        arrived.append(1)
        if len(arrived) == 3:
            stage.cancel()

    stage.sentenceArrived.connect(_batal_setelah_3)
    cancelled = _run(qapp, stage, _State())
    assert cancelled is True
    text = stage._document.toPlainText()
    kalimat = [item[0] for item in BAB_SATU + BAB_DUA]
    tampil = [k for k in kalimat if k in text]
    assert len(tampil) == 3, text


def test_fallback_tanpa_streaming_enam_kalimat_unik(qapp, db_tmp):
    client = FakeBatchClient([_bab_json(BAB_SATU), _bab_json(BAB_DUA)])
    stage = _stage(client)
    assert _run(qapp, stage, _State()) is False
    text = stage._document.toPlainText()
    kalimat = [item[0] for item in BAB_SATU + BAB_DUA]
    for k in kalimat:
        assert text.count(k) == 1, k
    positions = [text.index(k) for k in kalimat]
    assert positions == sorted(positions)
