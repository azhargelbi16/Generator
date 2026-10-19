"""Tes edit manual dan pulihkan sitasi (Task 17b)."""

from generator import report
from generator.ai.content import Paragraph, Section, Sentence
from generator.verification import verify_sentence, STATUS_UNVERIFIED

GOOD = "pertanian organik di indonesia sangat penting bagi petani"


def test_apply_manual_edit_marks_manual_and_keeps_uid_and_sources():
    s = Sentence("asli.", "q", [0])
    s2 = report.apply_manual_edit(s, "diubah manual.")
    assert s2.origin == "manual" and s2.uid == s.uid and s2.source_ids == [0]
    assert s2.text == "diubah manual."


def test_manual_edit_is_unverified():
    s = report.apply_manual_edit(Sentence("x", GOOD, [0]), "diubah manual.")
    assert verify_sentence(s, {0: GOOD}) == STATUS_UNVERIFIED


def test_restore_citation_sets_flag():
    s = Sentence("x.", "q", [0], citation=False)
    assert report.restore_citation(s).citation is True


def test_merge_for_regenerate_keeps_manual_by_default():
    old = [_section_with_manual()]
    new = [Section(1, "Bab Baru", [Paragraph([Sentence("Hasil baru.", "q", [0], is_factual=False)])])]
    merged = report.merge_for_regenerate(old, new, overwrite_all=False)
    texts = [s.text for sec in merged for p in sec.paragraphs for s in p.sentences]
    assert "Catatan manual saya." in texts and "Hasil baru." in texts


def test_merge_for_regenerate_overwrite_all_drops_manual():
    old = [_section_with_manual()]
    new = [Section(1, "Bab Baru", [Paragraph([Sentence("Hasil baru.", "q", [0], is_factual=False)])])]
    merged = report.merge_for_regenerate(old, new, overwrite_all=True)
    texts = [s.text for sec in merged for p in sec.paragraphs for s in p.sentences]
    assert "Catatan manual saya." not in texts and "Hasil baru." in texts


def test_merge_for_regenerate_empty_old_returns_new():
    new = [Section(1, "Bab", [Paragraph([Sentence("Isi.", "q", [0])])])]
    assert report.merge_for_regenerate([], new, overwrite_all=False) is new


def _section_with_manual():
    manual = report.apply_manual_edit(Sentence("asli.", "q", [0]), "Catatan manual saya.")
    return Section(1, "Bab Lama", [Paragraph([manual, Sentence("Lain.", "q", [0])])])

