"""Uji end-to-end pipeline: generate, verifikasi, label, dan compose (Task 18)."""

from generator.ai.content import generate_sections, compose
from generator.ai.citation import Author, order_and_label, Source
from generator.verification import verify_sections, STATUS_VERIFIED


class FakeClient:
    def chat(self, messages, json_mode=False):
        return ('{"sections":[{"level":1,"title":"Bab","paragraphs":[{"sentences":[{"text":'
                '"Pertanian organik meningkat pesat di Indonesia.","quote":'
                '"pertanian organik meningkat pesat di indonesia sangat penting","source_ids":[0],"is_factual":true}]}]}]}')


def test_pipeline_is_grounded_and_verified():
    src = [Source([Author("Zed")], "2020", "T", "J"),
           Source([Author("Abadi", "T")], "2021", "U", "J")]
    texts = {0: "laporan pertanian organik meningkat pesat di indonesia sangat penting"}
    secs = generate_sections("tema", ["Bab"], src, [texts[0], "teks sumber kedua"], FakeClient())
    statuses = verify_sections(secs, texts)
    assert all(s.status == STATUS_VERIFIED for s in statuses)
    labels = {l.source_index: l.in_text for l in order_and_label(src, cite={0})}
    out = compose(secs[0].paragraphs[0], labels)
    assert labels[0].startswith("(Zed") and out.endswith("(Zed, 2020).")
