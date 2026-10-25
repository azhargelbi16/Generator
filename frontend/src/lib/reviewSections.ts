// Normalisasi payload sections mentah dari backend ke bentuk yang dipakai
// layar review (dipindah dari TabReview.tsx agar bisa diuji dan dipakai
// sidebar tanpa memuat komponen layar).

import { Section, Sentence } from './api';

export const normalizeReviewSections = (value: unknown): Section[] => {
  if (!Array.isArray(value)) return [];

  return value.flatMap((rawSection, sectionIndex) => {
    if (!rawSection || typeof rawSection !== 'object') return [];
    const section = rawSection as Record<string, unknown>;
    const rawParagraphs = Array.isArray(section.paragraphs) ? section.paragraphs : [];
    const paragraphs = rawParagraphs.map((rawParagraph) => {
      const paragraph = rawParagraph && typeof rawParagraph === 'object'
        ? rawParagraph as Record<string, unknown>
        : {};
      const rawSentences = Array.isArray(paragraph.sentences) ? paragraph.sentences : [];
      const sentences: Sentence[] = rawSentences.flatMap((rawSentence, sentenceIndex) => {
        if (!rawSentence || typeof rawSentence !== 'object') return [];
        const sentence = rawSentence as Record<string, unknown>;
        const text = String(sentence.text ?? '').trim();
        if (!text) return [];
        return [{
          uid: String(sentence.uid || `review-${sectionIndex}-${sentenceIndex}`),
          text,
          quote: String(sentence.quote ?? ''),
          source_ids: Array.isArray(sentence.source_ids)
            ? sentence.source_ids.filter((id): id is number => Number.isInteger(id))
            : [],
          is_factual: sentence.is_factual !== false,
          origin: typeof sentence.origin === 'string' ? sentence.origin : undefined,
          citation: sentence.citation !== false,
        }];
      });
      return { sentences };
    });

    return [{
      level: Number.isFinite(Number(section.level)) ? Number(section.level) : 1,
      title: String(section.title ?? '').trim(),
      paragraphs,
    }];
  });
};
