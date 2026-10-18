"""Tes inti report: gerbang ekspor, pending, sitasi, label, dan referensi (Task 17a)."""

from generator.report import (can_export, pending, references_for, labels_for,
    uncited_ids, non_factual_uids, cited_ids)
from generator.verification import verify_sections, STATUS_VERIFIED
from generator.ai.content import Sentence, Paragraph, Section
from generator.ai.citation import Author, Source

GOOD = "pertanian organik di indonesia sangat penting bagi petani"


def test_can_export_blocks_when_unverified():
    s = Section(1, "B", [Paragraph([Sentence("x", "kata kata kata kata kata kata kata kata", [0])])])
    st = verify_sections([s], {0: "teks lain sama sekali berbeda dan tidak berkaitan lagi"})
    ok, msg = can_export(st)
    assert ok is False and msg


def test_can_export_allows_when_verified():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0])])])
    st = verify_sections([s], {0: GOOD})
    assert can_export(st) == (True, "")


def test_pending_excludes_verified_sentences():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0]),
                                    Sentence("y", "kata kata kata kata kata kata kata kata", [0])])])
    st = verify_sections([s], {0: GOOD})
    assert st[0].status == STATUS_VERIFIED
    assert pending(st, frozenset()) == [1]


def test_non_factual_blocks_until_marked_done():
    s = Section(1, "B", [Paragraph([Sentence("Bab ini membahas.", is_factual=False)])])
    st = verify_sections([s], {})
    assert can_export(st)[0] is False
    assert can_export(st, done=frozenset({st[0].sentence.uid}))[0] is True


def test_done_keyed_by_stable_uid_survives_insertion():
    a = Sentence("kalimat asli.", is_factual=False)
    st = verify_sections([Section(1, "B", [Paragraph([a])])], {})
    done = frozenset({st[0].sentence.uid})
    assert can_export(st, done=done)[0] is True

    st2 = verify_sections([Section(1, "B", [Paragraph([Sentence("kalimat baru.", is_factual=False), a])])], {})
    assert st2[1].sentence.uid == a.uid
    assert pending(st2, done) == [0]


def test_non_factual_uids_for_bulk_mark():
    s = Section(1, "B", [Paragraph([Sentence("pengantar.", is_factual=False),
                                    Sentence("klaim.", GOOD, [0])])])
    st = verify_sections([s], {0: GOOD})
    assert non_factual_uids(st) == [st[0].sentence.uid]
    assert can_export(st, done=frozenset(non_factual_uids(st)))[0] is True


def test_cited_ids_collects_referenced_sources():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0, 1]),
                                    Sentence("y", is_factual=False)])])
    st = verify_sections([s], {0: GOOD})
    assert cited_ids(st) == {0, 1}


def test_cited_ids_ignores_citation_suppressed():
    s = Section(1, "B", [Paragraph([Sentence("x", GOOD, [0], citation=False),
                                    Sentence("y", GOOD, [1])])])
    st = verify_sections([s], {0: GOOD, 1: GOOD})
    assert cited_ids(st) == {1}


def test_references_only_cited_sources():
    src = [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "U", "J")]
    refs = references_for(src, {0})
    assert len(refs) == 1 and uncited_ids(src, {0}) == [1]


def test_labels_keyed_by_original_source_index():
    src = [Source([Author("Zed")], "2020", "Z", "J"),
           Source([Author("Abadi", "T")], "2020", "A", "J")]
    labels = labels_for(src, {0, 1})
    assert set(labels) == {0, 1}
    assert labels[0].startswith("(Zed") and labels[1].startswith("(Abadi")


def test_labels_no_suffix_from_uncited_source():
    src = [Source([Author("Santoso", "Budi")], "2020", "A", "J"),
           Source([Author("Santoso", "Budi")], "2020", "B", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "C", "J")]
    labels = labels_for(src, {0, 2})
    assert labels[0] == "(Santoso, 2020)" and labels[2] == "(Wijaya, 2021)"
