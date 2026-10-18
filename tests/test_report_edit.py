"""Tes edit manual dan pulihkan sitasi (Task 17b)."""

from generator import report
from generator.ai.content import Sentence
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
