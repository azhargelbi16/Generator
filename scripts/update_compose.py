from pathlib import Path

p = Path("src/generator/ai/content.py")
content = p.read_text(encoding="utf-8")

old_compose = '''def compose(paragraph: Paragraph, labels: dict[int, str]) -> str:
    """Rangkai paragraf; sitasi dipasang kode tepat sebelum tanda baca akhir (11.4).

    Bila model sudah menulis sitasi sendiri di dalam teks, sitasi buatan kode
    tidak ditambahkan lagi. Tanpa penjagaan ini, keluaran menjadi
    "…Arifin (2024) (Lestari et al., 2024)" — sitasi ganda yang lolos ke DOCX.
    """
    parts: list[str] = []
    for sentence in paragraph.sentences:
        citation = ""
        if (
            sentence.is_factual
            and sentence.citation
            and sentence.source_ids
            and not _CITATION_IN_TEXT_RE.search(sentence.text)
        ):
            inner: list[str] = []
            for source_id in labels:
                if source_id not in sentence.source_ids:
                    continue
                label = labels[source_id].strip()
                if label.startswith("(") and label.endswith(")"):
                    label = label[1:-1]
                inner.append(label)
            if inner:
                citation = " (" + "; ".join(inner) + ")"
        parts.append(_insert_before_final_punctuation(sentence.text, citation))
    return " ".join(parts)'''

new_compose = '''def compose(paragraph: Paragraph, labels: dict[int, str]) -> str:
    """Rangkai paragraf; sitasi dipasang kode tepat sebelum tanda baca akhir (11.4).

    Bila model sudah menulis sitasi sendiri di dalam teks, sitasi buatan kode
    tidak ditambahkan lagi. Tanpa penjagaan ini, keluaran menjadi
    "…Arifin (2024) (Lestari et al., 2024)" — sitasi ganda yang lolos ke DOCX.

    Citation Smoothing: Bila dua atau lebih kalimat berturut-turut dalam satu
    paragraf naratif merujuk ke sumber yang persis sama, sitasi parentetikal
    hanya diberikan pada kalimat terakhir dari rangkaian klaim tersebut agar
    tidak terjadi repetisi mekanis per kalimat.
    """
    sentences = paragraph.sentences
    num_s = len(sentences)

    raw_citations: list[str] = []
    for sentence in sentences:
        citation = ""
        if (
            sentence.is_factual
            and sentence.citation
            and sentence.source_ids
            and not _CITATION_IN_TEXT_RE.search(sentence.text)
        ):
            inner: list[str] = []
            for source_id in labels:
                if source_id not in sentence.source_ids:
                    continue
                label = labels[source_id].strip()
                if label.startswith("(") and label.endswith(")"):
                    label = label[1:-1]
                inner.append(label)
            if inner:
                citation = " (" + "; ".join(inner) + ")"
        raw_citations.append(citation)

    final_citations = list(raw_citations)
    for i in range(num_s - 1):
        if raw_citations[i] and raw_citations[i] == raw_citations[i + 1]:
            final_citations[i] = ""

    parts: list[str] = []
    for sentence, citation in zip(sentences, final_citations):
        parts.append(_insert_before_final_punctuation(sentence.text, citation))
    return " ".join(parts)'''

content = content.replace(old_compose, new_compose)
p.write_text(content, encoding="utf-8")
print("content.py compose() updated with Citation Smoothing!")
