"""Tes interaksi Review: toolbar melayang, sunting inline, aksi massal (Task 4.2)."""

import time

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton, QToolButton

from generator import report
from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.sources.records import record_to_source, source_to_record
from generator.verification import (
    STATUS_UNVERIFIED,
    verify_sections,
)

QUOTED = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah"
)
SOURCE_TEXT = QUOTED + " secara berkelanjutan untuk masa depan"


class _State:
    def __init__(self):
        self.sources = [
            source_to_record(
                Source([Author("Santoso", "Budi")], "2020", "Judul A", "Jurnal"),
                SOURCE_TEXT,
                "manual",
            )
        ]
        self.done = set()
        self.fields = {"judul": "Laporan Uji"}
        self.saved = 0
        s0 = Sentence(text="Kalimat pertama yang teruji.", quote=QUOTED, source_ids=[0])
        s1 = Sentence(text="Klaim tanpa dasar sama sekali.", quote="tak ada", source_ids=[0])
        s2 = Sentence(text="Narasi pembuka tanpa klaim.", quote="", source_ids=[], is_factual=False)
        s3 = Sentence(text="Narasi penutup tanpa klaim.", quote="", source_ids=[], is_factual=False)
        s4 = Sentence(
            text="Kalimat dengan sitasi terlepas.", quote=QUOTED, source_ids=[0], citation=False
        )
        s5 = Sentence(text="Kalimat terakhir yang teruji.", quote=QUOTED, source_ids=[0])
        self.sentences = [s0, s1, s2, s3, s4, s5]
        self.sections = [Section(1, "Bab Satu", [Paragraph(self.sentences)])]
        self.statuses = verify_sections(self.sections, {0: SOURCE_TEXT})

    def _save_draft(self):
        self.saved += 1


def _page(qapp, cfg_default):
    from generator.qt.review_page import ReviewPage

    state = _State()
    page = ReviewPage(state, cfg=cfg_default)
    page.render_document()
    return page, state


def _button(root, text):
    for button in root.findChildren(QPushButton):
        if text in button.text():
            return button
    raise AssertionError(f"tombol {text!r} tidak ditemukan")


def _wait_worker(page, timeout_ms=5000):
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    page._worker.finished.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()
    page._thread.wait(2000)


def test_toolbar_melayang_satu_aktif_dekat_kalimat(qapp, cfg_default):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QWidget

    page, state = _page(qapp, cfg_default)

    def _expected_pos(uid):
        block = page._document.document().firstBlock()
        while block.isValid():
            data = block.userData()
            if data is not None:
                for span in data.spans:
                    if span["uid"] == uid:
                        cursor = QTextCursor(block)
                        cursor.setPosition(block.position() + span["start"])
                        rect = page._document.cursorRect(cursor)
                        return page._document.viewport().mapToGlobal(rect.topLeft()) + QPoint(
                            0, rect.height() + 2
                        )
            block = block.next()
        raise AssertionError(uid)

    page.select(state.sentences[0].uid)
    assert page._toolbar.isVisible()
    assert page._toolbar.pos() == _expected_pos(state.sentences[0].uid)
    page.select(state.sentences[5].uid)
    assert page._toolbar.isVisible()
    assert page._toolbar.pos() == _expected_pos(state.sentences[5].uid)
    # Hanya satu toolbar melayang yang aktif.
    pelampung = page.findChildren(QWidget, "toolbarAksi")
    assert len(pelampung) == 1 and pelampung[0] is page._toolbar


def test_tandai_selesai_mengubah_done_nav_dan_info(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    uid = state.sentences[0].uid
    page.select(uid)
    _button(page._toolbar, "✔ Tandai selesai").click()
    assert uid in state.done
    assert page.counts()["selesai"] == 1
    assert "1 selesai" in page._nav.item(0).text()
    assert page._info.text() == "Kalimat ditandai selesai."


def test_setujui_semua_terverifikasi_tidak_ikut_merah(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    tombol = _button(page._controls, "Setujui semua terverifikasi")
    assert tombol.text() == "Setujui semua terverifikasi (3)"
    tombol.click()
    assert len(state.done) == 3
    merah = next(s for s in state.sentences if s.uid in {i.sentence.uid for i in state.statuses if i.status == STATUS_UNVERIFIED})
    assert merah.uid not in state.done
    assert page.counts()["selesai"] == 3


def test_tandai_semua_bukan_klaim(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    _button(page._controls, "☑ Tandai semua bukan klaim selesai").click()
    bukan_klaim = {state.sentences[2].uid, state.sentences[3].uid}
    assert bukan_klaim <= state.done
    assert page.counts()["selesai"] == 2


def test_pulihkan_sitasi(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    page.select(state.sentences[4].uid)
    _button(page._toolbar, "↩ Pulihkan sitasi").click()
    assert state.sentences[4].citation is True
    assert page._info.text() == "Sitasi kalimat dipulihkan."
    page.select(state.sentences[0].uid)
    _button(page._toolbar, "↩ Pulihkan sitasi").click()
    assert page._info.text() == "Sitasi kalimat ini sudah aktif."


def test_parafrase_fake_client_mengganti_dan_menurunkan_status(qapp, cfg_default, monkeypatch):
    from generator.ai import content as content_mod

    baru = Sentence(text="Hasil parafrase yang baru.", quote="tak ada", source_ids=[0])

    def _fake_paraphrase(paragraph, sources, texts, client):
        return Paragraph([baru])

    monkeypatch.setattr(content_mod, "paraphrase", _fake_paraphrase)
    page, state = _page(qapp, cfg_default)
    page._client_factory = lambda: object()
    page.select(state.sentences[0].uid)
    uid_lama = state.sentences[0].uid
    _button(page._toolbar, "✒ Parafrase").click()
    _wait_worker(page)
    assert "Hasil parafrase yang baru" in page._document.toPlainText()
    assert uid_lama not in {s.uid for sec in state.sections for p in sec.paragraphs for s in p.sentences}
    baru_status = next(i.status for i in state.statuses if i.sentence.uid == baru.uid)
    assert baru_status == STATUS_UNVERIFIED


def test_sunting_inline_commit_pindah_ke_kalimat_lain(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    doc = page._document
    page.select(state.sentences[0].uid)
    assert doc.isReadOnly() is False  # mode edit aktif
    cursor = doc.textCursor()
    block = cursor.block()
    data = block.userData()
    span = next(s for s in data.spans if s["uid"] == state.sentences[0].uid)
    cursor.setPosition(block.position() + span["start"])
    cursor.setPosition(block.position() + span["end"], QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText("Teks hasil suntingan manual.")
    scroll_akhir = doc.verticalScrollBar().value()
    page.select(state.sentences[5].uid)  # commit terjadi saat pindah
    kalimat = next(
        s for sec in state.sections for p in sec.paragraphs for s in p.sentences
        if s.uid == state.sentences[0].uid
    )
    assert kalimat.text == "Teks hasil suntingan manual."
    assert kalimat.origin == "manual"
    assert "Teks hasil suntingan manual" in doc.toPlainText()
    # Span kalimat lain di blok sama tetap terpetakan benar (cari tanpa titik:
    # label sitasi disisipkan sebelum tanda baca akhir).
    plain = doc.toPlainText()
    target = state.sentences[5].text.rstrip(".")
    assert page.uid_at(plain.index(target) + 1) == state.sentences[5].uid
    assert doc.verticalScrollBar().value() == scroll_akhir


def test_enter_saat_mode_edit_tidak_membelah_dokumen(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    doc = page._document
    sebelum = doc.document().blockCount()
    page.select(state.sentences[0].uid)
    QTest.keyClick(doc, Qt.Key.Key_Return)
    assert doc.document().blockCount() == sebelum
    assert state.sentences[0].text == "Kalimat pertama yang teruji."


def test_menu_sumber_menampilkan_label_dan_judul(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    page.select(state.sentences[0].uid)
    tombol = next(b for b in page._toolbar.findChildren(QToolButton) if "Sumber" in b.text())
    menu = tombol.menu()
    teks = [a.text() for a in menu.actions()]
    assert any("Santoso" in t for t in teks)
    assert any("Judul A" in t for t in teks)


def test_tombol_simpan_docx_memancarkan_sinyal(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    got = []
    page.exportRequested.connect(lambda: got.append(True))
    _button(page._controls, "💾 Simpan DOCX").click()
    assert got == [True]

def test_sunting_sebagian_tidak_menggandakan_sitasi(qapp, cfg_default):
    page, state = _page(qapp, cfg_default)
    doc = page._document
    page.select(state.sentences[0].uid)
    cursor = doc.textCursor()
    block = cursor.block()
    span = next(s for s in block.userData().spans if s["uid"] == state.sentences[0].uid)
    cursor.setPosition(block.position() + span["start"])
    cursor.setPosition(block.position() + span["end"], QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText("Kalimat kedua yang teruji (Santoso, 2020).")
    page.select(state.sentences[5].uid)  # commit saat pindah kalimat
    kalimat = next(
        s for sec in state.sections for p in sec.paragraphs for s in p.sentences
        if s.uid == state.sentences[0].uid
    )
    assert kalimat.text == "Kalimat kedua yang teruji."
    assert "(Santoso, 2020)(Santoso, 2020)" not in doc.toPlainText()
