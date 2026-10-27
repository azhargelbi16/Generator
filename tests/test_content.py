import json
import threading

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


# --- Task 1.3: progress streaming + pembatalan ------------------------------

ANCHOR_REPLY_A = (
    '{"sections":[{"level":1,"title":"Pendahuluan","paragraphs":[{"sentences":['
    '{"text":"Pertanian organik meningkat pesat.","quote":"q1","source_ids":[0],"is_factual":true},'
    '{"text":"Pupuk alami lebih baik.","quote":"q2","source_ids":[0],"is_factual":true}]}]}]}'
)
ANCHOR_REPLY_B = (
    '{"sections":[{"level":2,"title":"Metode","paragraphs":[{"sentences":['
    '{"text":"Data dikumpulkan lewat wawancara.","quote":"q3","source_ids":[1],"is_factual":true},'
    '{"text":"Analisis memakai koding tematik.","quote":"q4","source_ids":[1],"is_factual":false}]}]}]}'
)

# Direkam dari implementasi SEBELUM Task 1.3 (fixture_anchor.py); jangkar anti-regresi.
ANCHOR_SECTIONS = [
    {
        "level": 1,
        "title": "Pendahuluan",
        "paragraphs": [{"sentences": [
            {"text": "Pertanian organik meningkat pesat.", "quote": "q1", "source_ids": [0], "is_factual": True},
            {"text": "Pupuk alami lebih baik.", "quote": "q2", "source_ids": [0], "is_factual": True},
        ]}],
    },
    {
        "level": 2,
        "title": "Metode",
        "paragraphs": [{"sentences": [
            {"text": "Data dikumpulkan lewat wawancara.", "quote": "q3", "source_ids": [1], "is_factual": True},
            {"text": "Analisis memakai koding tematik.", "quote": "q4", "source_ids": [1], "is_factual": False},
        ]}],
    },
]

ANCHOR_SOURCES = [
    Source([Author("Santoso", "Budi")], "2020", "T", "J"),
    Source([Author("Wijaya", "Ani")], "2021", "U", "J"),
]
ANCHOR_TEXTS = [
    "Pertanian organik meningkat pesat di berbagai daerah tropis. " * 7,
    "Pupuk alami lebih baik untuk kesuburan tanah jangka panjang. " * 7,
]


def _serialize(sections) -> list:
    return [
        {
            "level": section.level,
            "title": section.title,
            "paragraphs": [
                {
                    "sentences": [
                        {
                            "text": sentence.text,
                            "quote": sentence.quote,
                            "source_ids": list(sentence.source_ids),
                            "is_factual": sentence.is_factual,
                        }
                        for sentence in paragraph.sentences
                    ]
                }
                for paragraph in section.paragraphs
            ],
        }
        for section in sections
    ]


class ProgressRecorder:
    def __init__(self, cancel_after=None):
        self.batches = []
        self.born = []
        self.finished_flags = []
        self.cancel = None
        self.cancel_after = cancel_after

    def batch_started(self, n, total):
        self.batches.append((n, total))

    def sentence_born(self, sentence, status):
        self.born.append((sentence.text, status))
        if self.cancel_after is not None and self.cancel is not None:
            if len(self.born) >= self.cancel_after:
                self.cancel.set()

    def finished(self, cancelled):
        self.finished_flags.append(cancelled)


class StreamClient:
    """Client dengan chat_stream; chat() sengaja gagal agar fallback tak tersamar."""

    def __init__(self, chunk_batches):
        self.chunk_batches = list(chunk_batches)
        self.calls = 0

    def chat(self, messages, json_mode=False):
        raise AssertionError("fallback chat() tidak boleh dipanggil")

    def chat_stream(self, messages, json_mode=False, cancel=None):
        self.calls += 1
        chunks = self.chunk_batches.pop(0) if len(self.chunk_batches) > 1 else self.chunk_batches[0]
        for chunk in chunks:
            if cancel is not None and cancel.is_set():
                return
            yield chunk


def test_generate_sections_tanpa_progress_identik_dengan_perilaku_lama():
    client = FakeClient([ANCHOR_REPLY_A, ANCHOR_REPLY_B])
    sections = generate_sections(
        "tema", ["Pendahuluan", "Metode"], ANCHOR_SOURCES, ANCHOR_TEXTS, client,
        max_prompt_chars=500,
    )
    assert client.calls == 2
    assert _serialize(sections) == ANCHOR_SECTIONS


STREAM_TEXTS = [
    "Pertanian organik meningkat pesat di berbagai daerah tropis termasuk Indonesia. " * 2,
    "Pupuk alami lebih baik untuk kesuburan tanah jangka panjang. " * 4,
]
STREAM_JSON = json.dumps({
    "sections": [
        {
            "level": 1,
            "title": "Pendahuluan",
            "paragraphs": [{"sentences": [
                {
                    "text": "Pertanian organik meningkat pesat di berbagai daerah tropis.",
                    "quote": "Pertanian organik meningkat pesat di berbagai daerah tropis",
                    "source_ids": [0],
                    "is_factual": True,
                },
                {"text": "Dua.", "quote": "", "source_ids": [], "is_factual": False},
            ]}],
        },
        {
            "level": 1,
            "title": "Metode",
            "paragraphs": [{"sentences": [
                {"text": "Tiga.", "quote": "", "source_ids": [], "is_factual": False},
                {"text": "Empat.", "quote": "", "source_ids": [], "is_factual": False},
            ]}],
        },
    ]
}, ensure_ascii=False)


def _slices(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def test_streaming_melahirkan_kalimat_berurutan_dan_tahan_json_patah():
    progress = ProgressRecorder()
    client = StreamClient([_slices(STREAM_JSON, 13)])
    sources = [
        Source([Author("Santoso", "Budi")], "2020", "T", "J"),
        Source([Author("Wijaya", "Ani")], "2021", "U", "J"),
    ]
    sections = generate_sections(
        "tema", ["Pendahuluan", "Metode"], sources, STREAM_TEXTS, client,
        max_prompt_chars=12000, progress=progress,
    )
    assert [text for text, _ in progress.born] == [
        "Pertanian organik meningkat pesat di berbagai daerah tropis.",
        "Dua.",
        "Tiga.",
        "Empat.",
    ]
    assert progress.born[0][1] == "terverifikasi"
    assert progress.born[1][1] == "bukan_klaim_faktual"
    assert progress.finished_flags == [False]
    assert progress.batches == [(1, 1)]
    assert [s.text for p in sections[1].paragraphs for s in p.sentences] == ["Tiga.", "Empat."]


def test_cancel_menghentikan_stream_dan_mengembalikan_kalimat_yang_sudah_lahir():
    cancel = threading.Event()
    progress = ProgressRecorder(cancel_after=2)
    progress.cancel = cancel
    chunks = [
        '{"sections":[{"level":1,"title":"Pendahuluan","paragraphs":[{"sentences":['
        '{"text":"Satu.","quote":"","source_ids":[],"is_factual":false}',
        ',{"text":"Dua.","quote":"","source_ids":[],"is_factual":false}',
        ',{"text":"Tiga.","quote":"","source_ids":[],"is_factual":false}',
        ',{"text":"Empat.","quote":"","source_ids":[],"is_factual":false}]}]}]}',
    ]
    client = StreamClient([chunks])
    sources = [
        Source([Author("Santoso", "Budi")], "2020", "T", "J"),
        Source([Author("Wijaya", "Ani")], "2021", "U", "J"),
    ]
    sections = generate_sections(
        "tema", ["Pendahuluan", "Metode"], sources, STREAM_TEXTS, client,
        max_prompt_chars=300, progress=progress, cancel=cancel,
    )
    assert progress.finished_flags == [True]
    assert [text for text, _ in progress.born] == ["Satu.", "Dua."]
    assert client.calls == 1  # batch kedua tidak pernah dipanggil
    texts = [s.text for section in sections for p in section.paragraphs for s in p.sentences]
    assert len(texts) >= 2 and set(texts) == {"Satu.", "Dua."}


def test_fallback_tanpa_chat_stream_reveal_per_batch_tanpa_duplikat():
    progress = ProgressRecorder()
    client = FakeClient([ANCHOR_REPLY_A, ANCHOR_REPLY_B])
    sections = generate_sections(
        "tema", ["Pendahuluan", "Metode"], ANCHOR_SOURCES, ANCHOR_TEXTS, client,
        max_prompt_chars=500, progress=progress,
    )
    assert progress.batches == [(1, 2), (2, 2)]
    texts = [text for text, _ in progress.born]
    assert texts == [
        "Pertanian organik meningkat pesat.",
        "Pupuk alami lebih baik.",
        "Data dikumpulkan lewat wawancara.",
        "Analisis memakai koding tematik.",
    ]
    assert len(set(texts)) == len(texts)
    assert progress.finished_flags == [False]
    assert _serialize(sections) == ANCHOR_SECTIONS



# --- Task 2.2: Kirim hanya bab relevan per batch ----------------------------


def test_batch_dengan_sumber_berbeda_hanya_meminta_bab_relevan_dan_urutan_akhir_sesuai_outline():
    from generator.ai.content import select_relevant_outline

    # Outline laporan 4 bab
    outline = ["Pendahuluan", "Metode Penelitian", "Hasil dan Pembahasan", "Kesimpulan"]

    # Sumber 0 membahas metode penelitian
    src0_text = "Metode penelitian ini menggunakan prosedur eksperimen laboratorium alat dan bahan kimia secara terstandar."
    # Sumber 1 membahas pendahuluan dan latar belakang
    src1_text = "Latar belakang masalah dan tujuan dari penelitian pendahuluan ini sangat mendasar bagi pembangunan daerah."

    # Periksa select_relevant_outline secara langsung:
    batch_metode = [(0, src0_text)]
    batch_pendahuluan = [(1, src1_text)]

    assert select_relevant_outline(outline, batch_metode) == ["Metode Penelitian"]
    assert select_relevant_outline(outline, batch_pendahuluan) == ["Pendahuluan"]

    # Reply untuk batch metode (datang pertama)
    reply_metode = json.dumps({
        "sections": [{
            "level": 1,
            "title": "Metode Penelitian",
            "paragraphs": [{"sentences": [
                {"text": "Metode penelitian dirancang secara eksperimental.", "quote": "Metode penelitian ini", "source_ids": [0], "is_factual": True}
            ]}]
        }]
    })

    # Reply untuk batch pendahuluan (datang kedua)
    reply_pendahuluan = json.dumps({
        "sections": [{
            "level": 1,
            "title": "Pendahuluan",
            "paragraphs": [{"sentences": [
                {"text": "Latar belakang masalah berfokus pada efisiensi.", "quote": "Latar belakang masalah", "source_ids": [1], "is_factual": True}
            ]}]
        }]
    })

    client = FakeClient([reply_metode, reply_pendahuluan])
    sources = [
        Source([Author("Santoso", "Budi")], "2020", "T", "J"),
        Source([Author("Wijaya", "Ani")], "2021", "U", "J"),
    ]

    # Eksekusi generate_sections dengan dua sumber terpisah
    sections = generate_sections(
        "tema",
        outline,
        sources,
        [src0_text, src1_text],
        client,
        max_prompt_chars=150,
    )

    # 1. Pastikan setiap batch HANYA meminta bab yang relevan di pesan AI
    assert client.calls == 2
    msg_batch0 = client.messages[0][1]["content"]  # Batch 0 (src0: metode)
    msg_batch1 = client.messages[1][1]["content"]  # Batch 1 (src1: pendahuluan)

    assert "Metode Penelitian" in msg_batch0
    assert "Pendahuluan" not in msg_batch0
    assert "Kesimpulan" not in msg_batch0

    assert "Pendahuluan" in msg_batch1
    assert "Metode Penelitian" not in msg_batch1
    assert "Kesimpulan" not in msg_batch1

    # 2. Urutan akhir hasil tetap sesuai urutan outline asli ("Pendahuluan" sebelum "Metode Penelitian")
    titles = [s.title for s in sections]
    assert titles == ["Pendahuluan", "Metode Penelitian"]



# --- Task 2.5: Merge tanpa duplikat semantik ---------------------------------


def test_merge_sections_membuang_dua_parafrase_ringan():
    from generator.ai.content import _merge_sections, Section, Paragraph, Sentence

    s1 = Sentence("Pengembangan sistem pertanian organik di Indonesia menunjukkan peningkatan yang signifikan.", "q", [0])
    s2 = Sentence("Pengembangan sistem pertanian organik di Indonesia menunjukkan peningkatan yang sangat signifikan.", "q", [0])

    existing = [Section(1, "Pendahuluan", [Paragraph([s1])])]
    incoming = [Section(1, "Pendahuluan", [Paragraph([s2])])]

    _merge_sections(existing, incoming)

    # Dua parafrase ringan hanya menyisakan satu kalimat
    all_sents = [s.text for s in existing[0].paragraphs[0].sentences]
    assert len(all_sents) == 1
    assert all_sents[0] == s1.text


def test_merge_sections_mempertahankan_parafrase_dengan_sitasi_berbeda():
    from generator.ai.content import _merge_sections, Section, Paragraph, Sentence

    s1 = Sentence("Pertanian organik memberikan dampak positif bagi kesuburan tanah.", "q1", [0])
    s2 = Sentence("Pertanian organik memberi dampak positif bagi kesuburan tanah.", "q2", [1])

    existing = [Section(1, "Pendahuluan", [Paragraph([s1])])]
    incoming = [Section(1, "Pendahuluan", [Paragraph([s2])])]

    _merge_sections(existing, incoming)

    # Jangan buang bila sitasi berbeda
    all_sents = [s for p in existing[0].paragraphs for s in p.sentences]
    assert len(all_sents) == 2
    assert all_sents[0].source_ids == [0]
    assert all_sents[1].source_ids == [1]


def test_generate_sections_dedup_parafrase_ringan():
    from generator.ai.content import generate_sections
    import json

    reply1 = json.dumps({
        "sections": [{
            "level": 1,
            "title": "Pendahuluan",
            "paragraphs": [{"sentences": [
                {"text": "Penerapan pertanian ramah lingkungan semakin diminati oleh para petani.", "quote": "q", "source_ids": [0], "is_factual": True}
            ]}]
        }]
    })
    reply2 = json.dumps({
        "sections": [{
            "level": 1,
            "title": "Pendahuluan",
            "paragraphs": [{"sentences": [
                {"text": "Penerapan pertanian ramah lingkungan kini semakin diminati oleh para petani.", "quote": "q", "source_ids": [0], "is_factual": True}
            ]}]
        }]
    })

    client = FakeClient([reply1, reply2])
    sources = [Source([Author("Santoso", "Budi")], "2020", "T", "J")]
    long_text = "kalimat sumber " * 1000

    sections = generate_sections(
        "tema",
        ["Pendahuluan"],
        sources,
        [long_text],
        client,
        max_prompt_chars=500,
    )

    sentences = [s for p in sections[0].paragraphs for s in p.sentences]
    assert len(sentences) == 1



# --- Uji Optimasi 15+ Sumber & Pembersihan Noise Dokumen --------------------


def test_15_sources_adaptive_batching_budgeting():
    from generator.ai.content import generate_sections
    # 15 sumber referensi dengan teks panjang
    srcs = [
        Source([Author(f"Penulis{i}", "A")], "2023", f"Jurnal {i}", "J")
        for i in range(15)
    ]
    texts = [f"Teks ilmiah penting sumber {i}. " * 200 for i in range(15)]
    c = FakeClient([REPLY, REPLY, REPLY, REPLY, REPLY])

    secs = generate_sections(
        "Tema Uji 15 Sumber",
        ["BAB 1. Pendahuluan", "BAB 2. Metode", "BAB 3. Hasil", "BAB 4. Penutup"],
        srcs,
        texts,
        c,
        max_prompt_chars=12000,
    )

    # Buktikan bahwa 15 sumber dibudgetkan secara adaptif menjadi maksimal 3 batch (bukan 45 batch!)
    assert c.calls <= 3, f"Jumlah batch ({c.calls}) melebihi budget adaptif!"
    assert len(secs) >= 1


def test_prune_noise_from_source_text():
    from generator.ai.content import prune_noise_from_source_text

    doc = (
        "Abstrak penelitian ini membahas inovasi sistem kontrol cerdas.\n"
        + "Metodologi dan hasil pengujian menunjukkan efisiensi sebesar 94%.\n" * 40
        + "\n\nDaftar Pustaka\n"
        + "1. Smith, J. (2019). Machine learning basics.\n"
        + "2. Doe, A. (2020). Advanced AI systems.\n" * 50
    )
    pruned = prune_noise_from_source_text(doc)
    assert "Daftar Pustaka" not in pruned
    assert "Smith, J." not in pruned
    assert "efisiensi sebesar 94%" in pruned


# --- Slice arsitektur 3: jalur varian per bab memakai langkah generasi sama --

VARIANT_B_OUTLINE = [
    "BAB 1. PENDAHULUAN", "1.1 Latar Belakang", "1.2 Rumusan Masalah", "1.3 Tujuan",
    "BAB 2. TINJAUAN PUSTAKA", "2.1 Subjek", "2.2 Objek",
    "BAB 3. HASIL DAN PEMBAHASAN", "3.1 Hasil", "3.2 Pembahasan",
    "BAB 4. KESIMPULAN DAN SARAN", "4.1 Kesimpulan", "4.2 Saran",
]


def _chapter_reply(title: str, text: str) -> str:
    """Jawaban model yang benar: satu section subbab berisi, bukan level BAB."""
    number = title.split()[1].rstrip(".") if title.upper().startswith("BAB") else "1"
    return json.dumps({"sections": [{
        "level": 2, "title": f"{number}.1 Subbab",
        "paragraphs": [{"sentences": [
            {"text": text, "quote": text, "source_ids": [0], "is_factual": True}
        ]}],
    }]}, ensure_ascii=False)


def _variant_client(replies):
    """FakeClient yang mencatat kwarg chat (max_tokens/timeout) per panggilan."""
    class KwargsClient:
        def __init__(self, replies):
            self.replies = list(replies)
            self.calls = 0
            self.kwargs_seen = []

        def chat(self, messages, json_mode=False, max_tokens=None, timeout=None):
            self.calls += 1
            self.kwargs_seen.append({"max_tokens": max_tokens, "timeout": timeout})
            return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]

    return KwargsClient(replies)


def _variant_sources():
    return [Source([Author("Santoso", "Budi")], "2020", "T", "J")]


def test_jalur_varian_per_bab_event_berurutan_dan_struktur_lengkap():
    from generator.ai.content import generate_sections as gen

    replies = [
        _chapter_reply("BAB 1. PENDAHULUAN", "Latar belakang biochar di tanah asam."),
        _chapter_reply("BAB 2. TINJAUAN PUSTAKA", "Kajian terdahulu tentang pembenah tanah."),
        _chapter_reply("BAB 3. HASIL DAN PEMBAHASAN", "Hasil uji menunjukkan pH naik."),
        _chapter_reply("BAB 4. KESIMPULAN DAN SARAN", "Biochar efektif pada dosis tepat."),
    ]
    progress = ProgressRecorder()
    sections = gen(
        "tema", VARIANT_B_OUTLINE, _variant_sources(), ["teks sumber jurnal."],
        _variant_client(replies), progress=progress, variant="b",
    )
    assert progress.batches == [(index, 9) for index in range(1, 10)]
    assert progress.finished_flags == [False]
    assert len(progress.born) == 4  # satu kalimat unik per bab, berurutan
    titles = [s.title for s in sections]
    assert titles[0] == "BAB 1. PENDAHULUAN"
    assert "BAB 4. KESIMPULAN DAN SARAN" in titles
    assert len(titles) >= 4


def test_jalur_varian_mengirim_max_tokens_16384_dan_timeout_240():
    from generator.ai.content import generate_sections as gen

    replies = [_chapter_reply(f"BAB {n}. X", f"Isi bab {n}.") for n in range(1, 5)]
    client = _variant_client(replies)
    gen("tema", VARIANT_B_OUTLINE, _variant_sources(), ["teks sumber."],
        client, variant="b")
    # Bab dipecah per ≤2 subbab: BAB1 2, BAB2 4, BAB3 2, BAB4 1 = 9 panggilan.
    assert client.calls == 9
    # Volume isi 3× lebih besar (3 paragraf per subbab): anggaran token dinaikkan
    # dari 8192 agar respons tidak terpotong; streaming memakai anggaran yang sama.
    assert all(kw == {"max_tokens": 16384, "timeout": 240.0} for kw in client.kwargs_seen)


def test_jalur_batch_mengirim_max_tokens_16384_tanpa_timeout():
    from generator.ai.content import generate_sections as gen

    client = _variant_client([REPLY])
    gen("tema", ["Pendahuluan"], _variant_sources(), ["teks sumber."], client)
    assert client.calls == 1
    assert client.kwargs_seen[0] == {"max_tokens": 16384, "timeout": None}


def test_jalur_varian_partial_output_dipulihkan_dari_aierror():
    from generator.ai.content import generate_sections as gen
    from generator.ai.client import AIError

    class PartialClient:
        def __init__(self):
            self.calls = 0

        def chat(self, messages, json_mode=False, max_tokens=None, timeout=None):
            self.calls += 1
            if self.calls == 1:
                exc = AIError("Respons terpotong karena batas token.")
                exc.partial_content = _chapter_reply("BAB 1. PENDAHULUAN", "Kalimat parsial yang selamat.")
                raise exc
            return _chapter_reply("BAB 2. TINJAUAN PUSTAKA", "Kajian lanjutan.")

    progress = ProgressRecorder()
    sections = gen(
        "tema", VARIANT_B_OUTLINE, _variant_sources(), ["teks sumber."],
        PartialClient(), progress=progress, variant="b",
    )
    texts = [s.text for sec in sections for p in sec.paragraphs for s in p.sentences]
    assert "Kalimat parsial yang selamat." in texts
    assert "Kajian lanjutan." in texts
    assert progress.finished_flags == [False]


def test_cancel_jalur_varian_menghentikan_dan_menyimpan_sebagian():
    from generator.ai.content import generate_sections as gen

    cancel = threading.Event()
    progress = ProgressRecorder(cancel_after=2)
    progress.cancel = cancel
    replies = [_chapter_reply(f"BAB {n}. X", f"Isi bab {n}.") for n in range(1, 5)]
    client = _variant_client(replies)
    sections = gen(
        "tema", VARIANT_B_OUTLINE, _variant_sources(), ["teks sumber."],
        client, progress=progress, cancel=cancel, variant="b",
    )
    assert progress.finished_flags == [True]
    assert client.calls == 2  # bab 3-4 tidak pernah diminta
    texts = [s.text for sec in sections for p in sec.paragraphs for s in p.sentences]
    assert len(texts) >= 2


# --- Perbaikan: sitasi ganda & pengulangan lintas bab ------------------------


def test_compose_tidak_menggandakan_sitasi_yang_sudah_ada_di_teks():
    from generator.ai.content import compose

    p = Paragraph([
        Sentence("Menurut Lestari dkk. (2024), adopsi AI meningkat.", "q", [0]),
        Sentence("Setiawan dan Rahardjo (2023) menguji irigasi presisi.", "q", [0]),
    ])
    out = compose(p, {0: "(Lestari et al., 2024)"})
    assert out == (
        "Menurut Lestari dkk. (2024), adopsi AI meningkat. "
        "Setiawan dan Rahardjo (2023) menguji irigasi presisi."
    )


def test_compose_tetap_menambah_sitasi_bila_teks_belum_bersitasi():
    from generator.ai.content import compose

    p = Paragraph([Sentence("Adopsi AI meningkat.", "q", [0])])
    assert compose(p, {0: "(Lestari et al., 2024)"}) == "Adopsi AI meningkat (Lestari et al., 2024)."


def test_merge_sections_membuang_duplikat_identik_lintas_bab():
    from generator.ai.content import Paragraph, Section, Sentence, _merge_sections

    text = "Biochar menaikkan pH tanah asam pada dosis 10 ton per hektar."
    existing = [Section(1, "BAB 1. PENDAHULUAN", [Paragraph([Sentence(text, "q", [0])])])]
    incoming = [
        Section(1, "BAB 3. HASIL DAN PEMBAHASAN", [Paragraph([Sentence(text, "q", [0])])]),
        Section(1, "BAB 4. KESIMPULAN", [Paragraph([Sentence(text, "q", [0])])]),
    ]

    _merge_sections(existing, incoming)

    assert len(existing) == 3
    assert existing[1].paragraphs == []
    assert existing[2].paragraphs == []


def test_merge_sections_mempertahankan_duplikat_identik_dengan_sitasi_berbeda():
    from generator.ai.content import Paragraph, Section, Sentence, _merge_sections

    text = "Biochar menaikkan pH tanah asam pada dosis 10 ton per hektar."
    existing = [Section(1, "BAB 1. PENDAHULUAN", [Paragraph([Sentence(text, "q", [0])])])]
    incoming = [Section(1, "BAB 3. HASIL", [Paragraph([Sentence(text, "q", [1])])])]

    _merge_sections(existing, incoming)

    # Sumber berbeda = dasar faktual berbeda, jadi tidak dibuang.
    assert len(existing[1].paragraphs) == 1


def test_merge_sections_membuang_dua_set_kesimpulan_parafrase():
    """BAB 4 kerap datang dua set butir mirip (~0,6); ambang khusus 0,55."""
    from generator.ai.content import Paragraph, Section, Sentence, _merge_sections

    set_a = [
        Sentence("1. Motif penggunaan media sosial berpengaruh besar terhadap prestasi akademik mahasiswa.", "q", [0]),
        Sentence("2. Durasi pemakaian harian menjadi jembatan penurunan hasil belajar mahasiswa.", "q", [0]),
    ]
    set_b = [
        Sentence("1. Motif pemakaian media sosial memengaruhi capaian prestasi akademik mahasiswa.", "q", [0]),
        Sentence("2. Durasi pemakaian harian menjadi penghubung menurunnya hasil belajar mahasiswa.", "q", [0]),
    ]
    existing = [Section(2, "Kesimpulan", [Paragraph(set_a)])]
    incoming = [Section(2, "Kesimpulan", [Paragraph(set_b)])]

    _merge_sections(existing, incoming)

    texts = [s.text for p in existing[0].paragraphs for s in p.sentences]
    assert len(texts) == 2, texts  # hanya satu set yang tersisa
    assert all(t.startswith("1. Motif penggunaan") or t.startswith("2. Durasi pemakaian") for t in texts)


def test_merge_sections_kesimpulan_sitasi_berbeda_tetap_dipertahankan():
    from generator.ai.content import Paragraph, Section, Sentence, _merge_sections

    a = Sentence("1. Motif penggunaan media sosial berpengaruh besar terhadap prestasi akademik mahasiswa.", "q", [0])
    b = Sentence("1. Motif pemakaian media sosial memengaruhi capaian prestasi akademik mahasiswa.", "q", [1])
    existing = [Section(2, "Saran", [Paragraph([a])])]
    incoming = [Section(2, "Saran", [Paragraph([b])])]

    _merge_sections(existing, incoming)

    texts = [s.text for p in existing[0].paragraphs for s in p.sentences]
    assert len(texts) == 2  # sumber berbeda: keduanya hidup


def test_merge_sections_bab_naratif_dedup_parafrase_06():
    """Kemiripan ~0,66 di bab naratif DIDEDUP (ambang diturunkan ke 0,6)."""
    from generator.ai.content import Paragraph, Section, Sentence, _merge_sections

    a = Sentence("Pertanian organik memberi manfaat besar bagi petani dan konsumen.", "q", [0])
    b = Sentence("Pertanian organik memberi manfaat nyata bagi petani dan masyarakat.", "q", [0])
    existing = [Section(2, "Latar Belakang", [Paragraph([a])])]
    incoming = [Section(2, "Latar Belakang", [Paragraph([b])])]

    _merge_sections(existing, incoming)

    texts = [s.text for p in existing[0].paragraphs for s in p.sentences]
    assert len(texts) == 1  # parafrase ringan dibuang

    # Kalimat dengan topik benar-benar berbeda tetap dipertahankan.
    c = Sentence("Pupuk organik cair mempercepat pertumbuhan akar tanaman muda.", "q", [0])
    d = Sentence("Pengairan berselang menekan emisi metana pada lahan sawah.", "q", [0])
    other = [Section(2, "Pembahasan", [Paragraph([c])])]
    _merge_sections(other, [Section(2, "Pembahasan", [Paragraph([d])])])
    assert len([s for p in other[0].paragraphs for s in p.sentences]) == 2


# --- Alur Rumusan Masalah -> Tujuan -> Pembahasan ----------------------------


def test_varian_d_mengirim_rumusan_masalah_dan_tujuan_ke_bab_pembahasan():
    """Bab 3 menerima konteks Bab 1 agar pembahasan sejajar dengan rumusan masalah."""
    import json

    from generator import format_spec
    from generator.ai.citation import Author, Source
    from generator.ai.content import generate_sections

    captured: list[list[dict]] = []

    def reply(title: str, text: str) -> str:
        return json.dumps({
            "sections": [{
                "level": 2,
                "title": title,
                "paragraphs": [{"sentences": [{
                    "text": text, "quote": "q", "source_ids": [0], "is_factual": True,
                }]}],
            }],
        })

    class Client:
        def chat(self, messages, **kwargs):
            captured.append(messages)
            if len(captured) == 1:
                return json.dumps({"sections": [
                    {"level": 2, "title": "Latar Belakang",
                     "paragraphs": [{"sentences": [
                         {"text": "Media sosial telah menjadi bagian hidup mahasiswa.",
                          "quote": "q", "source_ids": [0], "is_factual": True}]}]},
                    {"level": 2, "title": "Rumusan Masalah",
                     "paragraphs": [{"sentences": [
                         {"text": "1. Bagaimana pengaruh motif penggunaan media sosial?",
                          "quote": "q", "source_ids": [0], "is_factual": True}]}]},
                    {"level": 2, "title": "Tujuan",
                     "paragraphs": [{"sentences": [
                         {"text": "1. Mengetahui pengaruh motif penggunaan media sosial.",
                          "quote": "q", "source_ids": [0], "is_factual": True}]}]},
                ]})
            return reply("Topik bahasan", "Isi bab berikutnya.")

    source = Source([Author("Santoso", "Budi")], "2020", "T", "J")
    sections = generate_sections(
        "media sosial", format_spec.outline_titles(format_spec.get_variant("D")),
        [source], ["teks sumber yang panjang"], Client(), variant="D",
    )

    assert len(captured) == 9  # varian D: 2 + 3 + 3 + 1 panggilan
    bab2_prompt = captured[2][-1]["content"]
    bab3_prompt = captured[5][-1]["content"]
    assert "Bagaimana pengaruh motif penggunaan media sosial?" in bab2_prompt
    assert "Mengetahui pengaruh motif penggunaan media sosial." in bab3_prompt
    assert "KONTEKS DARI BAB SEBELUMNYA" in bab3_prompt
    assert "BAB 4. KESIMPULAN DAN SARAN" in [s.title for s in sections]


# --- Struktur paragraf dari schema pipih Gemini ------------------------------


def _flat_sentence(text, **extra):
    payload = {"text": text, "quote": "", "source_ids": [0], "is_factual": True}
    payload.update(extra)
    return payload


def test_parser_kalimat_pipih_tanpa_penanda_dipecah_beberapa_paragraf():
    from generator.ai.content import _sections_from_dict

    data = {"sections": [{
        "level": 2,
        "title": "1.1 Latar Belakang",
        "paragraphs": [_flat_sentence(f"Kalimat nomor {index}.") for index in range(8)],
    }]}
    paragraphs = _sections_from_dict(data)[0].paragraphs
    total = sum(len(paragraph.sentences) for paragraph in paragraphs)
    assert total == 8
    assert len(paragraphs) >= 2
    assert all(len(paragraph.sentences) <= 5 for paragraph in paragraphs)


def test_parser_mengelompokkan_paragraf_menurut_field_paragraph():
    from generator.ai.content import _sections_from_dict

    data = {"sections": [{
        "level": 2,
        "title": "1.1 Latar Belakang",
        "paragraphs": [
            _flat_sentence("Kalimat pertama.", paragraph=1),
            _flat_sentence("Kalimat kedua.", paragraph=1),
            _flat_sentence("Kalimat ketiga.", paragraph=2),
        ],
    }]}
    paragraphs = _sections_from_dict(data)[0].paragraphs
    assert len(paragraphs) == 2
    assert len(paragraphs[0].sentences) == 2
    assert len(paragraphs[1].sentences) == 1


def test_parser_butir_bernomor_tetap_satu_per_paragraf():
    from generator.ai.content import _sections_from_dict

    data = {"sections": [{
        "level": 2,
        "title": "1.2 Rumusan Masalah",
        "paragraphs": [
            _flat_sentence("1. Pertanyaan pertama?"),
            _flat_sentence("2. Pertanyaan kedua?"),
            _flat_sentence("3. Pertanyaan ketiga?"),
            _flat_sentence("4. Pertanyaan keempat?"),
            _flat_sentence("5. Pertanyaan kelima?"),
        ],
    }]}
    paragraphs = _sections_from_dict(data)[0].paragraphs
    assert len(paragraphs) == 5
    assert all(len(paragraph.sentences) == 1 for paragraph in paragraphs)


def test_parser_menerima_kalimat_pipih_di_level_section():
    from generator.ai.content import _sections_from_dict

    data = {"sections": [{
        "level": 2,
        "title": "2.1 Tinjauan",
        "sentences": [_flat_sentence(f"Kalimat {index}.") for index in range(8)],
    }]}
    paragraphs = _sections_from_dict(data)[0].paragraphs
    assert sum(len(p.sentences) for p in paragraphs) == 8
    assert len(paragraphs) >= 2


def test_rencana_generasi_memecah_bab_tanpa_judul_bab():
    from generator.ai.content import _chapter_generation_plans

    plans = _chapter_generation_plans([(
        "BAB 2. TINJAUAN PUSTAKA",
        [
            "BAB 2. TINJAUAN PUSTAKA",
            "2.1 {Subjek}", "2.1.1 {Aspek 1}", "2.1.2 {Aspek 2}",
            "2.2 {Objek}", "2.2.1 {Aspek 1}",
        ],
    )])
    assert len(plans) == 3  # potongan 2 + 2 + 1 subbab
    assert plans[0][2] == ["2.1 {Subjek}", "2.1.1 {Aspek 1}"]
    assert plans[1][2] == ["2.1.2 {Aspek 2}", "2.2 {Objek}"]
    assert plans[2][2] == ["2.2.1 {Aspek 1}"]
    assert plans[0][3] is True and plans[1][3] is False
    assert all("BAB 2. TINJAUAN PUSTAKA" not in titles for _, _, titles, _ in plans)


# --- Retry bila model menaruh isi di level BAB -------------------------------


def test_bab_diulang_sekali_bila_isi_menempel_di_level_bab():
    import json
    import re

    from generator.ai.citation import Author, Source
    from generator.ai.content import generate_sections

    class FocusClient:
        def __init__(self):
            self.calls = 0
            self.calls_by_chapter: dict[str, int] = {}

        def chat(self, messages, **kwargs):
            system = messages[0]["content"]
            match = re.search(r'tulis HANYA section untuk "([^"]+)"', system)
            focus = match.group(1) if match else ""
            self.calls += 1
            self.calls_by_chapter[focus] = self.calls_by_chapter.get(focus, 0) + 1
            if focus.startswith("BAB 1") and self.calls_by_chapter[focus] == 1:
                # Respons salah: isi diletakkan di level BAB, bukan subbab.
                return json.dumps({"sections": [{
                    "level": 1,
                    "title": "BAB 1. PENDAHULUAN",
                    "paragraphs": [_flat_sentence("Isi nyasar di level bab.")],
                }]})
            number = focus.split()[1].rstrip(".") if focus else "1"
            return json.dumps({"sections": [{
                "level": 2,
                "title": f"{number}.1 Subbab",
                "paragraphs": [{"sentences": [{
                    "text": f"Isi bab {number}.",
                    "quote": "q",
                    "source_ids": [0],
                    "is_factual": True,
                }]}],
            }]})

    client = FocusClient()
    source = Source([Author("Santoso", "Budi")], "2020", "T", "J")
    sections = generate_sections(
        "tema", ["BAB 1. PENDAHULUAN"], [source], ["teks sumber yang panjang"],
        client, variant="B",
    )

    assert client.calls_by_chapter["BAB 1. PENDAHULUAN"] == 3  # 2 bagian + 1 ulangan
    assert client.calls == 10  # 9 panggilan (bab dipecah) + 1 ulangan
    texts = [s.text for sec in sections for p in sec.paragraphs for s in p.sentences]
    assert "Isi nyasar di level bab." not in texts  # isi salah dibersihkan
    assert any("Isi bab 1." in text for text in texts)



def test_compose_citation_smoothing_meredam_repetisi_beruntun():
    from generator.ai.content import Paragraph, Sentence, compose

    # 4 kalimat berturut-turut dari sumber [0]
    p = Paragraph([
        Sentence("Kalimat pertama membahas isu.", "q1", [0]),
        Sentence("Kalimat kedua memperdalam analisis.", "q2", [0]),
        Sentence("Kalimat ketiga menjelaskan metode.", "q3", [0]),
        Sentence("Kalimat keempat menyajikan temuan.", "q4", [0]),
    ])
    out = compose(p, {0: "(Kalfas et al., 2024)"})
    # Hanya kalimat terakhir yang ditempeli sitasi parentetikal
    assert out == (
        "Kalimat pertama membahas isu. "
        "Kalimat kedua memperdalam analisis. "
        "Kalimat ketiga menjelaskan metode. "
        "Kalimat keempat menyajikan temuan (Kalfas et al., 2024)."
    )
