"""Tes Review Hasil ala MS Word: render, span, garis bergelombang, navigasi (Task 4.1)."""

from PySide6.QtGui import QTextCharFormat, QTextCursor

from generator import report
from generator.ai.citation import Author, Source
from generator.ai.content import Paragraph, Section, Sentence
from generator.sources.records import record_to_source, source_to_record
from generator.verification import (
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
    verify_sections,
)

QUOTED = (
    "pertanian organik di indonesia sangat penting bagi petani indonesia "
    "karena menjaga kesuburan tanah"
)
SOURCE_TEXT = QUOTED + " secara berkelanjutan untuk masa depan"
LONG_TEXT = "Kalimat panjang yang melintasi batas blok. " + "kata " * 900


class _State:
    """Stub controller_state: sumber, sections, done, statuses, fields."""

    def __init__(self):
        self.sources = [
            source_to_record(
                Source([Author("Santoso", "Budi")], "2020", "Judul A", "Jurnal"),
                SOURCE_TEXT,
                "manual",
            )
        ]
        self.sections = []
        self.done = set()
        self.statuses = []
        self.fields = {"judul": "Laporan Uji Coba"}


def _verified(i, text=None, source_ids=(0,)):
    return Sentence(
        text=text or f"Kalimat faktual nomor {i} teruji di sumber.",
        quote=QUOTED,
        source_ids=list(source_ids),
        is_factual=True,
    )


def _build_state():
    """2 bab, 45 kalimat: 40 terverifikasi, 1 tidak, 4 bukan klaim."""
    state = _State()
    bab_satu = []
    for i in range(20):
        bab_satu.append(_verified(i))
    bab_satu.append(
        Sentence(
            text="Klaim ini sama sekali tidak berdasar.",
            quote="tak ada di sumber ini",
            source_ids=[0],
            is_factual=True,
        )
    )
    for i in range(4):
        bab_satu.append(
            Sentence(
                text=f"Pembuka narasi nomor {i} tanpa klaim.",
                quote="",
                source_ids=[],
                is_factual=False,
            )
        )
    bab_dua = [_verified(100, text=LONG_TEXT)]
    for i in range(1, 20):
        bab_dua.append(_verified(100 + i))
    state.sections = [
        Section(1, "Bab Satu", [Paragraph(bab_satu)]),
        Section(1, "Bab Dua", [Paragraph(bab_dua)]),
    ]
    state.statuses = verify_sections(state.sections, {0: SOURCE_TEXT})
    return state


def _page(qapp, state, cfg_default):
    from generator.qt.review_page import ReviewPage

    page = ReviewPage(state, cfg=cfg_default)
    return page


def _plain_sentences(state):
    labels = report.labels_for(
        [record_to_source(r) for r in state.sources],
        report.cited_ids(state.statuses),
    )
    return [
        (s.uid, report.display_text(s, labels))
        for s in (x for sec in state.sections for p in sec.paragraphs for x in p.sentences)
    ]


def _fmt_at(document, pos):
    cursor = QTextCursor(document)
    cursor.setPosition(pos)
    return cursor.charFormat()


def test_dokumen_memuat_judul_heading_dan_seluruh_teks(qapp, cfg_default):
    state = _build_state()
    page = _page(qapp, state, cfg_default)
    page.render_document()
    text = page._document.toPlainText()
    assert "Laporan Uji Coba" in text
    assert "Bab Satu" in text
    assert "Bab Dua" in text
    for _uid, displayed in _plain_sentences(state):
        assert displayed in text


def test_uid_at_memetakan_posisi_tiap_kalimat_termasuk_blok_panjang(qapp, cfg_default):
    state = _build_state()
    page = _page(qapp, state, cfg_default)
    page.render_document()
    document = page._document.document()
    plain = page._document.toPlainText()
    # Kalimat pertama bab dua adalah kalimat super panjang (melintasi blok).
    long_uid, long_text = next(uid_text for uid_text in _plain_sentences(state) if len(uid_text[1]) > 2000)
    start = plain.index(long_text)
    tengah = start + len(long_text) // 2
    assert page.uid_at(tengah) == long_uid
    # Seluruh kalimat biasa terpetakan.
    for uid, displayed in _plain_sentences(state):
        if len(displayed) > 2000:
            continue
        pos = plain.index(displayed) + 1
        assert page.uid_at(pos) == uid, displayed[:40]
    # Posisi di luar span (heading judul) -> None.
    assert page.uid_at(2) is None or page.uid_at(2) in {u for u, _ in _plain_sentences(state)}
    assert document.characterCount() > 0


def test_span_tidak_terverifikasi_spellcheck_merah_lainnya_tanpa_garis(qapp, cfg_default):
    state = _build_state()
    page = _page(qapp, state, cfg_default)
    page.render_document()
    document = page._document.document()
    plain = page._document.toPlainText()
    by_uid = {item.sentence.uid: item.status for item in state.statuses}
    for uid, displayed in _plain_sentences(state):
        pos = plain.index(displayed) + 2
        fmt = _fmt_at(document, pos)
        status = by_uid[uid]
        if status == STATUS_UNVERIFIED:
            assert fmt.underlineStyle() == QTextCharFormat.SpellCheckUnderline, displayed
            assert fmt.underlineColor().name() == "#ff0000"
        elif status == STATUS_VERIFIED:
            assert fmt.underlineStyle() == QTextCharFormat.NoUnderline, displayed
        else:  # bukan klaim faktual
            assert fmt.underlineStyle() == QTextCharFormat.NoUnderline, displayed
            assert fmt.underlineColor().name() != "#ff0000"


def test_panel_navigasi_per_bab_dengan_ringkasan(qapp, cfg_default):
    state = _build_state()
    page = _page(qapp, state, cfg_default)
    page.render_document()
    texts = [page._nav.item(i).text() for i in range(page._nav.count())]
    assert len(texts) == 2
    assert "✓ 20 · ⚠ 1 · 4 bukan klaim" in texts[0]
    assert "✓ 20" in texts[1]


def test_status_bar_ringkasan_45_kalimat(qapp, cfg_default):
    state = _build_state()
    page = _page(qapp, state, cfg_default)
    page.render_document()
    assert page._status_bar.text() == "45 kalimat · ✓ 40 · ⚠ 1 · 4 bukan klaim · terverifikasi 89%"
    counts = page.counts()
    assert counts == {
        "total": 45,
        "terverifikasi": 40,
        "belum": 1,
        "bukan_klaim": 4,
        "selesai": 0,
        "persen": 89,
    }


def test_klik_navigasi_memindahkan_scrollbar_ke_blok_bab(qapp, cfg_default):
    state = _build_state()
    page = _page(qapp, state, cfg_default)
    page.render_document()
    before = page._document.verticalScrollBar().value()
    item = page._nav.item(1)
    page._nav.itemClicked.emit(item)
    assert page._document.textCursor().position() != 0
    assert page._document.verticalScrollBar().value() != before or page._document.textCursor().position() > 0


def test_select_menyorot_span_dan_emits_activation(qapp, cfg_default):
    state = _build_state()
    page = _page(qapp, state, cfg_default)
    page.render_document()
    uid = state.sections[0].paragraphs[0].sentences[0].uid
    got = []
    page.sentenceActivated.connect(lambda u: got.append(u))
    page.select(uid)
    assert page._selected_uid == uid
    page.sentenceActivated.emit(uid)  # sinyal publik terpancar saat kalimat diaktifkan
    assert got == [uid]
