"""Status dokumen yang sudah direview: satu sumber kebenaran tab Review.

Verifikasi kalimat, sitasi, analitik, preflight, dan persiapan ekspor semula
masing-masing membangun ulang hal yang sama: normalisasi sections dari dict,
teks sumber, status kalimat, dan himpunan sumber terkutip. Modul ini memiliki
rekonstruksi itu sekali — operasi lama di ApiBridge mendelegasi ke sini —
sehingga definisi "sitasi aktif", "status", dan "analitik" tidak bisa saling
meleset antar layar.

Semantik yang dipertahankan persis:
- Status kalimat memakai label verification.py (terverifikasi, perlu_ditinjau,
  tidak_terverifikasi, bukan_klaim_faktual) tanpa perubahan nama.
- ``cited_ids`` memakai semantik produksi lama (filter ``citation`` saja,
  tanpa memandang ``is_factual``) yang dipakai sitasi, preflight, dan ekspor.
  Bandingkan dengan report.cited_ids yang mensyaratkan faktual — dua definisi
  itu sengaja tetap terpisah karena dipakai tujuan berbeda.
- Amplop respons (envelope) tiap operasi lama tidak berubah.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import report
from .ai.citation import Source
from .ai.content import Section
from .sources.records import record_to_source
from .verification import SentenceStatus, verify_sections


@dataclass
class ReviewedDocument:
    """Hasil normalisasi payload review + turunan yang bisa dihitung darinya."""

    sections: list[Section]
    sources: list[Source]
    source_texts: list[str]
    _statuses: list[SentenceStatus] | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_payload(cls, sections_dicts: list[dict], sources_data: list[dict]) -> "ReviewedDocument":
        """Bangun dari payload mentah UI; verifikasi status dihitung malas."""
        sections = report.sections_from_dicts(sections_dicts)
        sources = [record_to_source(s) for s in sources_data]
        texts = [s.get("text", "") for s in sources_data]
        return cls(sections=sections, sources=sources, source_texts=texts)

    @property
    def statuses(self) -> list[SentenceStatus]:
        if self._statuses is None:
            self._statuses = verify_sections(self.sections, self.source_texts)
        return self._statuses

    @property
    def cited_ids(self) -> set[int]:
        """Indeks sumber dengan sitasi aktif pada kalimat apa pun."""
        return {
            i
            for sec in self.sections
            for p in sec.paragraphs
            for s in p.sentences
            if s.citation
            for i in s.source_ids
        }

    def status_payload(self) -> list[dict]:
        """Amplop lama verify_document (urutan & kunci persis sama)."""
        return [
            {
                "index": st.index,
                "uid": st.sentence.uid,
                "status": st.status,
                "reason": getattr(st, "reason", ""),
                "is_factual": st.sentence.is_factual,
                "source_ids": st.sentence.source_ids,
            }
            for st in self.statuses
        ]

    def citation_payload(self, style: str = "et_al") -> dict:
        """Amplop lama compute_citations_and_references."""
        cited = self.cited_ids
        labels = report.labels_for(self.sources, cited, style=style)
        label_forms = report.label_forms_for(self.sources, cited, style=style)
        refs = report.references_for(self.sources, cited)
        return {
            "labels": {str(k): v for k, v in labels.items()},
            "label_forms": {str(k): v for k, v in label_forms.items()},
            "references": refs,
            "cited_ids": list(cited),
        }

    def analytics(self) -> dict:
        """Amplop lama get_document_analytics (metrik kualitas akademik)."""
        total_words = 0
        total_chars = 0
        total_sentences = 0
        total_paragraphs = 0
        factual_sentences = 0
        cited_factual_sentences = 0
        section_distribution = []

        for sec in self.sections:
            sec_words = 0
            for p in sec.paragraphs:
                total_paragraphs += 1
                for s in p.sentences:
                    total_sentences += 1
                    words = s.text.split()
                    w_count = len(words)
                    total_words += w_count
                    total_chars += len(s.text)
                    sec_words += w_count
                    if s.is_factual:
                        factual_sentences += 1
                        if s.citation and s.source_ids:
                            cited_factual_sentences += 1
            section_distribution.append({
                "title": sec.title,
                "words": sec_words,
            })

        reading_time_minutes = max(1, round(total_words / 200)) if total_words > 0 else 0
        coverage_pct = round((cited_factual_sentences / max(1, factual_sentences)) * 100) if factual_sentences > 0 else 100

        # Skor Kematangan Akademik (0-100)
        structure_score = min(30, len(self.sections) * 7.5)
        length_score = min(30, (total_words / 1500) * 30)
        citation_score = (coverage_pct / 100) * 40
        academic_score = min(100, round(structure_score + length_score + citation_score))

        # Skor Keterbacaan (Indonesian Reading Ease Adaptation)
        avg_sentence_len = (total_words / max(1, total_sentences))
        readability = max(10, min(100, round(100 - (avg_sentence_len * 1.8))))

        return {
            "total_words": total_words,
            "total_chars": total_chars,
            "total_sentences": total_sentences,
            "total_paragraphs": total_paragraphs,
            "reading_time_minutes": reading_time_minutes,
            "citation_coverage_pct": coverage_pct,
            "academic_score": academic_score,
            "readability_score": readability,
            "section_distribution": section_distribution,
        }

    def snapshot(self, style: str = "et_al") -> dict:
        """Satu panggilan untuk layar review dan sidebar: status + sitasi +
        analitik sekaligus, dengan bentuk identik gabungan operasi lamanya."""
        return {
            "statuses": self.status_payload(),
            "citations": self.citation_payload(style),
            "analytics": self.analytics(),
        }
