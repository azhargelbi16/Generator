import pytest
from generator.ai.content import generate_sections, compose, Sentence, Paragraph
from generator.ai.citation import Author, Source


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        self.messages = []

    def chat(self, messages, json_mode=False):
        self.calls += 1
        self.messages.append(messages)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


REPLY = ('{"sections":[{"level":1,"title":"Pendahuluan","paragraphs":[{"sentences":['
         '{"text":"Pertanian organik meningkat.","quote":"q1","source_ids":[0],"is_factual":true},'
         '{"text":"Pupuk alami lebih baik.","quote":"q2","source_ids":[1],"is_factual":true}]}]}]}')


def test_generate_parses_sections():
    src = [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
           Source([Author("Wijaya", "Ani")], "2021", "U", "J")]
    secs = generate_sections("tema", ["Pendahuluan"], src, ["teks1", "teks2"], FakeClient([REPLY]))
    assert secs[0].level == 1 and secs[0].title == "Pendahuluan"
    assert secs[0].paragraphs[0].sentences[0].quote == "q1"


def test_generate_coerces_string_source_ids_and_drops_invalid():
    reply = ('{"sections":[{"level":1,"title":"B","paragraphs":[{"sentences":['
             '{"text":"a.","quote":"q","source_ids":["0","x"],"is_factual":true}]}]}]}')
    secs = generate_sections("tema", ["B"], [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                             ["teks"], FakeClient([reply]))
    assert secs[0].paragraphs[0].sentences[0].source_ids == [0]


def test_sentence_uid_is_unique_and_overridable():
    a, b = Sentence("x."), Sentence("x.")
    assert a.uid and b.uid and a.uid != b.uid
    assert Sentence("x.", uid="tetap").uid == "tetap"


def test_generate_requires_source_text():
    with pytest.raises(ValueError):
        generate_sections("tema", ["X"], [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                          [], FakeClient([REPLY]))


def test_generate_rejects_mismatched_sources_and_texts():
    with pytest.raises(ValueError):
        generate_sections("tema", ["X"],
                          [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
                           Source([Author("Wijaya", "Ani")], "2021", "U", "J")],
                          ["hanya satu teks"], FakeClient([REPLY]))


def test_generate_batches_long_sources_and_dedups():
    long_text = "kalimat " * 2000
    c = FakeClient([REPLY, REPLY])
    secs = generate_sections("tema", ["Pendahuluan"],
                             [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                             [long_text], c, max_prompt_chars=500)
    assert c.calls >= 2
    texts = [s.text for s in secs[0].paragraphs[0].sentences]
    assert len(texts) == len(set(texts))


def test_compose_places_citation_before_period():
    p = Paragraph([Sentence("Pertanian organik meningkat.", "q1", [0]),
                   Sentence("Pupuk alami lebih baik.", "q2", [1])])
    out = compose(p, {0: "(Santoso, 2020)", 1: "(Wijaya, 2021)"})
    assert out == "Pertanian organik meningkat (Santoso, 2020). Pupuk alami lebih baik (Wijaya, 2021)."


def test_compose_skips_non_factual():
    p = Paragraph([Sentence("Bab ini membahas pertanian.", is_factual=False)])
    assert compose(p, {}) == "Bab ini membahas pertanian."


def test_compose_ignores_unknown_source_id():
    p = Paragraph([Sentence("Pernyataan tanpa sumber dikenal.", "x", [99])])
    assert compose(p, {}) == "Pernyataan tanpa sumber dikenal."


def test_compose_merges_multiple_citations():
    p = Paragraph([Sentence("Dua sumber mendukung klaim ini.", "q", [1, 0])])
    out = compose(p, {0: "(Abadi, 2020)", 1: "(Zed, 2021)"})
    assert out == "Dua sumber mendukung klaim ini (Abadi, 2020; Zed, 2021)."


def test_compose_respects_citation_flag():
    p = Paragraph([Sentence("Klaim tanpa sitasi.", "q", [0], citation=False)])
    assert compose(p, {0: "(Santoso, 2020)"}) == "Klaim tanpa sitasi."


def test_sentence_defaults_to_ai_origin_and_citation_on():
    s = Sentence("x.")
    assert s.origin == "ai" and s.citation is True


def test_prompt_labels_each_chunk_with_source_id():
    c = FakeClient([REPLY])
    generate_sections("tema", ["Pendahuluan"],
                      [Source([Author("Santoso", "Budi")], "2020", "T", "J"),
                       Source([Author("Wijaya", "Ani")], "2021", "U", "J")],
                      ["teks satu", "teks dua"], c)
    joined = " ".join(m["content"] for m in c.messages[0])
    assert "[sumber 0]" in joined and "[sumber 1]" in joined


def test_bad_json_raises_after_all_batches_fail():
    with pytest.raises(ValueError):
        generate_sections("tema", ["X"], [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                          ["teks"], FakeClient(["bukan json"]))


def test_partial_bad_batch_keeps_good_sections():
    long_text = "kalimat " * 2000
    c = FakeClient(["bukan json", REPLY])
    secs = generate_sections("tema", ["Pendahuluan"],
                             [Source([Author("Santoso", "Budi")], "2020", "T", "J")],
                             [long_text], c, max_prompt_chars=500)
    assert secs and secs[0].title == "Pendahuluan"
