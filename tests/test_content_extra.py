from generator.ai.content import (Sentence, Paragraph, Section, suggest_outline,
    paraphrase, merge_regenerated)
from generator.ai.citation import Author, Source


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages, json_mode=False):
        self.calls += 1
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


SRC = [Source([Author("Santoso", "Budi")], "2020", "T", "J")]


def test_suggest_outline_returns_titles():
    c = FakeClient(['{"outline":["Pendahuluan","Metode","Pembahasan"]}'])
    assert suggest_outline("tema", SRC, ["teks sumber"], c) == ["Pendahuluan", "Metode", "Pembahasan"]


def test_suggest_outline_bad_json_returns_empty():
    assert suggest_outline("tema", SRC, ["teks"], FakeClient(["bukan json"])) == []


def test_paraphrase_returns_ai_sentences():
    old = Paragraph([Sentence("Teks asli.", "q", [0])])
    c = FakeClient(['{"sentences":[{"text":"Teks yang diparafrase.","quote":"q","source_ids":[0],"is_factual":true}]}'])
    new = paraphrase(old, SRC, ["teks sumber pertanian organik meningkat pesat"], c)
    assert new.sentences[0].text == "Teks yang diparafrase."
    assert new.sentences[0].origin == "ai"


def test_merge_regenerated_keeps_manual_by_default():
    old = [Section(1, "Bab", [Paragraph([Sentence("hasil ai lama.", origin="ai")]),
                               Paragraph([Sentence("catatan manual.", origin="manual")])])]
    new = [Section(1, "Bab", [Paragraph([Sentence("hasil ai baru.", origin="ai")])])]
    merged = merge_regenerated(old, new)
    texts = [s.text for sec in merged for p in sec.paragraphs for s in p.sentences]
    assert "hasil ai baru." in texts and "catatan manual." in texts and "hasil ai lama." not in texts


def test_merge_regenerated_overwrite_all_drops_manual():
    old = [Section(1, "Bab", [Paragraph([Sentence("catatan manual.", origin="manual")])])]
    new = [Section(1, "Bab", [Paragraph([Sentence("hasil ai baru.")])])]
    merged = merge_regenerated(old, new, overwrite_all=True)
    texts = [s.text for sec in merged for p in sec.paragraphs for s in p.sentences]
    assert "catatan manual." not in texts and "hasil ai baru." in texts
