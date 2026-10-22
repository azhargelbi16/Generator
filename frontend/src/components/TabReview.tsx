import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle, 
  RefreshCw, 
  Save, 
  GraduationCap, 
  FileDown, 
  ExternalLink,
  BookOpen,
  Check,
  RotateCcw,
  Sparkles,
  X,
  FileCheck2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ListOrdered,
  Eye,
  EyeOff
} from 'lucide-react';
import { 
  api, 
  Section, 
  Sentence, 
  SourceRecord, 
  SentenceStatus 
} from '../lib/api';
import { toast } from '../lib/toast';

interface TabReviewProps {
  onExportSuccess: (path: string) => void;
}

export const TabReview: React.FC<TabReviewProps> = ({ onExportSuccess }) => {
  const [sections, setSections] = useState<Section[]>([]);
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [statuses, setStatuses] = useState<SentenceStatus[]>([]);
  const [doneUids, setDoneUids] = useState<Set<string>>(new Set());
  const [citations, setCitations] = useState<{ labels: Record<string, string>; references: string[] }>({ labels: {}, references: [] });

  // Selected Sentence State
  const [selectedUid, setSelectedUid] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [paraphrasing, setParaphrasing] = useState(false);

  // Dosen Review Drawer
  const [dosenDrawerOpen, setDosenDrawerOpen] = useState(false);
  const [dosenNotes, setDosenNotes] = useState<Array<{ section_title: string; sentence_uid: string; severity: string; comment: string }>>([]);
  const [loadingDosen, setLoadingDosen] = useState(false);

  // Export & Preflight Modal
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [preflightIssues, setPreflightIssues] = useState<Array<{ kind: string; message: string }>>([]);
  const [preflightChecks, setPreflightChecks] = useState<Array<{ label: string; ok: boolean; detail: string }>>([]);
  const [isExporting, setIsExporting] = useState(false);

  // Canvas Studio & View Controls
  const [zoom, setZoom] = useState<number>(100);
  const [fitWidth, setFitWidth] = useState<boolean>(false);
  const [showOutline, setShowOutline] = useState<boolean>(true);
  const [readingMode, setReadingMode] = useState<boolean>(false);

  const handleZoomIn = () => setZoom((prev) => Math.min(150, prev + 15));
  const handleZoomOut = () => setZoom((prev) => Math.max(70, prev - 15));
  const handleResetZoom = () => setZoom(100);

  const handleScrollToSection = (secIdx: number) => {
    const el = document.getElementById(`section-heading-${secIdx}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  useEffect(() => {
    loadDraft();
  }, []);

  const loadDraft = async () => {
    try {
      const draft = await api.loadActiveDraft();
      if (draft?.has_draft && draft.sections && draft.sections.length > 0) {
        setSections(draft.sections);
        const s = draft.sources || [];
        setSources(s);
        const done = new Set(draft.done || []);
        setDoneUids(done);

        // Verify sentences
        const verifiedStatuses = await api.verifyDocument(draft.sections, s);
        if (verifiedStatuses) setStatuses(verifiedStatuses);

        // Compute APA citations
        const cit = await api.computeCitations(s, draft.sections, 'et_al');
        if (cit) setCitations({ labels: cit.labels, references: cit.references });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getSentenceStatus = (uid: string) => {
    const st = statuses.find((s) => s.uid === uid);
    return st ? st.status : 'belum_terverifikasi';
  };

  const isSentenceDone = (uid: string) => {
    return doneUids.has(uid);
  };

  // Find sentence and its coordinates
  const findSentence = (uid: string): Sentence | null => {
    for (const sec of sections) {
      for (const p of sec.paragraphs) {
        for (const s of p.sentences) {
          if (s.uid === uid) return s;
        }
      }
    }
    return null;
  };

  const handleSentenceClick = (s: Sentence) => {
    setSelectedUid(s.uid);
    setEditingText(s.text);
  };

  const handleToggleDone = (uid: string) => {
    const next = new Set(doneUids);
    if (next.has(uid)) {
      next.delete(uid);
    } else {
      next.add(uid);
    }
    setDoneUids(next);
    saveCurrentDraft(sections, next);
  };

  const handleSaveEdit = async () => {
    if (!selectedUid) return;
    const updated = sections.map((sec) => ({
      ...sec,
      paragraphs: sec.paragraphs.map((p) => ({
        ...p,
        sentences: p.sentences.map((s) => {
          if (s.uid === selectedUid) {
            return { ...s, text: editingText, origin: 'manual' };
          }
          return s;
        }),
      })),
    }));
    setSections(updated);

    // Re-verify
    const newStatuses = await api.verifyDocument(updated, sources);
    if (newStatuses) setStatuses(newStatuses);

    saveCurrentDraft(updated, doneUids);
  };

  const handleParaphrase = async () => {
    if (!selectedUid) return;
    const sent = findSentence(selectedUid);
    if (!sent) return;

    setParaphrasing(true);
    try {
      const res = await api.paraphraseSentence(sent, sources);
      if (res?.success && res.sentence) {
        setEditingText(res.sentence.text);
        const updated = sections.map((sec) => ({
          ...sec,
          paragraphs: sec.paragraphs.map((p) => ({
            ...p,
            sentences: p.sentences.map((s) => (s.uid === selectedUid ? res.sentence! : s)),
          })),
        }));
        setSections(updated);
        const newStatuses = await api.verifyDocument(updated, sources);
        if (newStatuses) setStatuses(newStatuses);
        saveCurrentDraft(updated, doneUids);
      } else {
        toast.error(res?.error || 'Gagal memparafrase kalimat.');
      }
    } finally {
      setParaphrasing(false);
    }
  };

  const handleRestoreCitation = () => {
    if (!selectedUid) return;
    const updated = sections.map((sec) => ({
      ...sec,
      paragraphs: sec.paragraphs.map((p) => ({
        ...p,
        sentences: p.sentences.map((s) => {
          if (s.uid === selectedUid) {
            return { ...s, citation: true };
          }
          return s;
        }),
      })),
    }));
    setSections(updated);
    saveCurrentDraft(updated, doneUids);
  };

  // Bulk actions
  const handleMarkAllDone = () => {
    const allUids = new Set<string>();
    sections.forEach((sec) =>
      sec.paragraphs.forEach((p) => p.sentences.forEach((s) => allUids.add(s.uid)))
    );
    setDoneUids(allUids);
    saveCurrentDraft(sections, allUids);
  };

  const handleMarkVerifiedDone = () => {
    const next = new Set(doneUids);
    statuses.forEach((st) => {
      if (st.status === 'terverifikasi') next.add(st.uid);
    });
    setDoneUids(next);
    saveCurrentDraft(sections, next);
  };

  const saveCurrentDraft = (curSections: Section[], curDone: Set<string>) => {
    api.saveActiveDraft({
      sections: curSections,
      sources,
      done: Array.from(curDone),
    });
  };

  // Dosen Review
  const handleRequestDosenReview = async () => {
    setLoadingDosen(true);
    setDosenDrawerOpen(true);
    try {
      const res = await api.requestDosenReview(sections, sources);
      if (res?.success && res.notes) {
        setDosenNotes(res.notes);
      } else {
        toast.error(res?.error || 'Gagal meminta review dosen.');
      }
    } finally {
      setLoadingDosen(false);
    }
  };

  // Preflight & Export Trigger
  const handleOpenExportModal = async () => {
    const draft = await api.loadActiveDraft();
    const res = await api.runPreflight({
      sections,
      sources,
      done: Array.from(doneUids),
      fields: draft?.fields || { JUDUL: 'Laporan' },
    });
    if (res) {
      setPreflightChecks(res.checks);
      setPreflightIssues(res.issues);
      setExportModalOpen(true);
    }
  };

  const handleExecuteExport = async () => {
    setIsExporting(true);
    try {
      const draft = await api.loadActiveDraft();
      const res = await api.exportReport({
        sections,
        sources,
        fields: draft?.fields || { JUDUL: 'Laporan' },
        template_id: draft?.fields?.TEMPLATE_ID || 1,
        open_word: true,
      });

      if (res?.success && res.output_path) {
        setExportModalOpen(false);
        onExportSuccess(res.output_path);
      } else {
        toast.error(res?.error || 'Ekspor dokumen gagal.');
      }
    } finally {
      setIsExporting(false);
    }
  };

  // Calculate statistics
  const totalSentences = statuses.length;
  const verifiedCount = statuses.filter((s) => s.status === 'terverifikasi').length;
  const unverifiedCount = statuses.filter((s) => s.status === 'belum_terverifikasi').length;
  const nonFactualCount = statuses.filter(
    (s) => s.status === 'bukan_klaim' || s.status === 'bukan_klaim_faktual'
  ).length;
  const doneCount = doneUids.size;

  const selectedSentence = selectedUid ? findSentence(selectedUid) : null;
  const selectedStatus = selectedUid ? getSentenceStatus(selectedUid) : null;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-100">
      {/* Top Review Bar */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0 shadow-sm z-10">
        {/* Sentence Counter Badges */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-slate-100 text-slate-700 font-semibold border border-slate-200">
            <span>Selesai: {doneCount}/{totalSentences}</span>
          </div>
          <span className="flex items-center space-x-1 text-emerald-700 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{verifiedCount} Terverifikasi</span>
          </span>
          <span className="flex items-center space-x-1 text-rose-700 font-semibold">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{unverifiedCount} Perlu Cek</span>
          </span>
          <span className="flex items-center space-x-1 text-slate-500 font-medium">
            <span>{nonFactualCount} Opini/Pengantar</span>
          </span>
        </div>

        {/* Action Buttons & Canvas Controls */}
        <div className="flex items-center space-x-2">
          {/* Zoom and Outline Controls */}
          <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 mr-2 text-xs">
            <button
              type="button"
              onClick={() => setShowOutline(!showOutline)}
              className={`p-1.5 rounded-md transition ${
                showOutline ? 'bg-white text-brand-700 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Tampilkan / Sembunyikan Struktur Bab"
            >
              <ListOrdered className="w-3.5 h-3.5" />
            </button>
            <div className="w-[1px] h-4 bg-slate-300 mx-1" />
            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1.5 rounded-md hover:bg-white text-slate-600 transition"
              title="Perkecil Lembar Kerja"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-700 hover:bg-white rounded transition"
              title="Kembalikan ke 100%"
            >
              {zoom}%
            </button>
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1.5 rounded-md hover:bg-white text-slate-600 transition"
              title="Perbesar Lembar Kerja"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <div className="w-[1px] h-4 bg-slate-300 mx-1" />
            <button
              type="button"
              onClick={() => setFitWidth(!fitWidth)}
              className={`p-1.5 rounded-md transition ${
                fitWidth ? 'bg-white text-brand-700 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'
              }`}
              title={fitWidth ? "Kembali ke Lebar Kertas Standar" : "Sesuaikan Lebar Layar (Fit Width)"}
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setReadingMode(!readingMode)}
              className={`p-1.5 rounded-md transition ${
                readingMode ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-800'
              }`}
              title={readingMode ? "Keluar Mode Baca" : "Mode Baca Santai (Tanpa Gangguan)"}
            >
              {readingMode ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          <button
            onClick={handleMarkVerifiedDone}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
          >
            Setujui Semua Terverifikasi
          </button>
          <button
            onClick={handleRequestDosenReview}
            className="px-3.5 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition"
          >
            <GraduationCap className="w-4 h-4" />
            <span>Review Dosen (AI)</span>
          </button>
          <button
            onClick={handleOpenExportModal}
            className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-bold shadow-md shadow-brand-600/20 flex items-center space-x-2 transition"
          >
            <FileDown className="w-4 h-4" />
            <span>Simpan DOCX</span>
          </button>
        </div>
      </div>

      {/* Main Review Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Outline Navigator Sidebar */}
        {showOutline && sections.length > 0 && (
          <div className="w-60 bg-white border-r border-slate-200 flex flex-col justify-between shrink-0 shadow-sm z-10 animate-slideRight">
            <div className="p-4 flex-1 overflow-y-auto">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                <div className="flex items-center space-x-2 text-xs font-bold text-slate-700">
                  <ListOrdered className="w-4 h-4 text-brand-600" />
                  <span>Struktur Bab</span>
                </div>
                <span className="text-[10px] font-semibold text-slate-400">{sections.length} Bagian</span>
              </div>
              <div className="space-y-1">
                {sections.map((sec, idx) => {
                  const secSentences = sec.paragraphs.flatMap((p) => p.sentences);
                  const verified = secSentences.filter((s) => getSentenceStatus(s.uid) === 'terverifikasi').length;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleScrollToSection(idx)}
                      className={`w-full text-left p-2 rounded-lg text-xs font-medium transition hover:bg-brand-50 hover:text-brand-800 ${
                        sec.level === 1 ? 'font-bold text-slate-800' : 'pl-4 text-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="truncate flex-1">{sec.title || `Bab ${idx + 1}`}</span>
                        {secSentences.length > 0 && (
                          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-500 shrink-0 ml-1">
                            {verified}/{secSentences.length}
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
                {citations.references.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      const el = document.getElementById('daftar-pustaka-heading');
                      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }}
                    className="w-full text-left p-2 rounded-lg text-xs font-bold text-slate-700 hover:bg-brand-50 hover:text-brand-800 transition"
                  >
                    DAFTAR PUSTAKA
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Document Paper Sheet (Scrollable) */}
        <div className="flex-1 overflow-y-auto p-8 flex justify-center">
          {sections.length === 0 ? (
            <div className="text-center py-24 text-slate-400 text-sm">
              Belum ada hasil laporan untuk direview.<br />Silakan generate laporan terlebih dahulu di tab <strong>Buat Laporan</strong>.
            </div>
          ) : (
            <div
              style={{
                width: fitWidth ? '100%' : `${Math.round(820 * (zoom / 100))}px`,
                maxWidth: fitWidth ? '100%' : `${Math.round(820 * (zoom / 100))}px`,
                fontSize: `${15 * (zoom / 100)}px`,
              }}
              className={`bg-white paper-sheet rounded-xl p-16 font-serif text-slate-800 leading-relaxed shadow-lg border border-slate-200/60 my-4 select-text transition-all duration-150 ${
                fitWidth ? 'max-w-5xl' : ''
              }`}
            >
              {sections.map((section, secIdx) => (
                <div id={`section-heading-${secIdx}`} key={secIdx} className="mb-8 scroll-mt-6">
                  {/* Chapter/Subchapter Heading */}
                  <h3
                    className={`font-sans font-bold text-slate-900 mb-4 ${
                      section.level === 1
                        ? 'text-lg text-center uppercase tracking-wide border-b border-slate-200 pb-2 mt-8'
                        : section.level === 2
                        ? 'text-base mt-6'
                        : 'text-sm mt-4'
                    }`}
                  >
                    {section.title}
                  </h3>

                  {/* Paragraphs */}
                  {section.paragraphs.map((para, pIdx) => (
                    <p key={pIdx} className="text-justify indent-8 text-[15px] leading-8 mb-4">
                      {para.sentences.map((sent) => {
                        const isSelected = selectedUid === sent.uid;
                        const status = getSentenceStatus(sent.uid);
                        const isDone = isSentenceDone(sent.uid);

                        // Build rendered citation string if active
                        let citationText = '';
                        if (sent.citation && sent.source_ids?.length > 0) {
                          const labels = sent.source_ids
                            .map((id) => citations.labels[id])
                            .filter(Boolean);
                          if (labels.length > 0) {
                            citationText = ` (${labels.join('; ')})`;
                          }
                        }

                        return (
                          <span
                            key={sent.uid}
                            onClick={() => handleSentenceClick(sent)}
                            className={`cursor-pointer transition-all duration-150 relative rounded px-0.5 ${
                              isSelected
                                ? 'bg-amber-200/90 text-slate-900 ring-2 ring-amber-400 font-medium'
                                : status === 'belum_terverifikasi' && !isDone
                                ? 'underline decoration-wavy decoration-rose-400 decoration-1 text-slate-900'
                                : 'hover:bg-amber-50'
                            }`}
                          >
                            <span>{sent.text}</span>
                            {citationText && (
                              <span className="font-sans font-normal text-slate-600 text-[13px]">
                                {citationText}
                              </span>
                            )}
                            {' '}
                          </span>
                        );
                      })}
                    </p>
                  ))}

                  {/* Daftar Pustaka APA 7 render at the end */}
                  {secIdx === sections.length - 1 && citations.references.length > 0 && (
                    <div id="daftar-pustaka-heading" className="mt-12 pt-8 border-t border-slate-200 scroll-mt-6">
                      <h4 className="font-sans font-bold text-center text-sm uppercase mb-4">
                        Daftar Pustaka
                      </h4>
                      <div className="space-y-3 text-xs pl-8 -indent-8 font-serif leading-relaxed text-slate-700">
                        {citations.references.map((ref, rIdx) => (
                          <p key={rIdx}>{ref}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Selected Sentence Inspector / Evidence Drawer (Right Side) */}
        {selectedSentence && !readingMode && (
          <div className="w-96 bg-white border-l border-slate-200 flex flex-col justify-between shrink-0 shadow-lg z-20">
            <div className="p-5 flex-1 overflow-y-auto space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                      selectedStatus === 'terverifikasi'
                        ? 'bg-emerald-100 text-emerald-800'
                        : selectedStatus === 'bukan_klaim' || selectedStatus === 'bukan_klaim_faktual'
                        ? 'bg-slate-100 text-slate-600'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {selectedStatus === 'terverifikasi'
                      ? '✓ Terverifikasi Sumber'
                      : selectedStatus === 'bukan_klaim' || selectedStatus === 'bukan_klaim_faktual'
                      ? '○ Bukan Klaim Faktual'
                      : '⚠ Belum Terverifikasi'}
                  </span>
                  {isSentenceDone(selectedSentence.uid) && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                      Selesai
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setSelectedUid(null)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Inline Editor */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
                  Sunting Kalimat di Tempat:
                </label>
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  rows={4}
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-serif leading-relaxed focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
                <button
                  onClick={handleSaveEdit}
                  className="mt-2 w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition flex items-center justify-center space-x-1.5 shadow-sm shadow-blue-500/20"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Simpan Perubahan Kalimat</span>
                </button>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  onClick={() => handleToggleDone(selectedSentence.uid)}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition ${
                    isSentenceDone(selectedSentence.uid)
                      ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      : 'bg-brand-50 text-brand-700 hover:bg-brand-100 border border-brand-200'
                  }`}
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>{isSentenceDone(selectedSentence.uid) ? 'Batal Selesai' : 'Tandai Selesai'}</span>
                </button>

                <button
                  onClick={handleParaphrase}
                  disabled={paraphrasing}
                  className="py-2 px-3 bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{paraphrasing ? 'Memproses...' : 'Parafrase AI'}</span>
                </button>
              </div>

              {!selectedSentence.citation && (
                <button
                  onClick={handleRestoreCitation}
                  className="w-full py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-medium flex items-center justify-center space-x-1"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Pulihkan Sitasi Sumber</span>
                </button>
              )}

              {/* Side-by-Side Evidence Inspection */}
              <div className="border-t border-slate-100 pt-3">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center space-x-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-brand-600" />
                  <span>Bukti Kutipan dari Teks Sumber:</span>
                </label>

                {selectedSentence.quote ? (
                  <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-slate-800 leading-relaxed font-serif italic">
                    "{selectedSentence.quote}"
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">
                    Tidak ada kutipan langsung (kalimat ini berupa ringkasan atau bukan klaim faktual).
                  </p>
                )}

                {/* Referenced Sources List */}
                {selectedSentence.source_ids && selectedSentence.source_ids.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Sumber yang Dirujuk:</span>
                    {selectedSentence.source_ids.map((id) => {
                      const s = sources[id];
                      return s ? (
                        <div key={id} className="p-2 rounded-lg bg-slate-50 border border-slate-200/80 text-xs">
                          <p className="font-semibold text-slate-800 truncate">{s.title || 'Tanpa Judul'}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            {s.authors?.map((a) => a.family).join(', ')} ({s.year || 'n.d.'})
                          </p>
                        </div>
                      ) : null;
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Dosen Notes Drawer */}
        {dosenDrawerOpen && (
          <div className="w-80 bg-white border-l border-slate-200 flex flex-col justify-between shrink-0 shadow-lg z-20">
            <div className="p-5 flex-1 overflow-y-auto">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center space-x-2">
                  <GraduationCap className="w-4 h-4 text-indigo-600" />
                  <h3 className="font-bold text-slate-800 text-sm">Catatan Review Dosen</h3>
                </div>
                <button onClick={() => setDosenDrawerOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
              </div>

              {loadingDosen ? (
                <div className="text-center py-16 text-slate-400 text-xs space-y-2">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600" />
                  <p>AI sedang membaca kritis laporan Anda layaknya dosen pembimbing...</p>
                </div>
              ) : dosenNotes.length === 0 ? (
                <div className="text-center py-16 text-slate-400 text-xs">
                  Tidak ada catatan kritis dari dosen. Laporan dinilai sudah memenuhi kriteria akademik yang baik.
                </div>
              ) : (
                <div className="space-y-3">
                  {dosenNotes.map((note, idx) => (
                    <div
                      key={idx}
                      onClick={() => note.sentence_uid && setSelectedUid(note.sentence_uid)}
                      className="p-3 rounded-xl border border-slate-200/80 bg-slate-50 hover:bg-indigo-50/50 hover:border-indigo-300 transition cursor-pointer text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-700 truncate">{note.section_title}</span>
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            note.severity === 'lemah'
                              ? 'bg-rose-100 text-rose-800'
                              : note.severity === 'berani'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {note.severity}
                        </span>
                      </div>
                      <p className="text-slate-600 leading-relaxed">{note.comment}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Preflight Export Modal */}
      {exportModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center text-brand-700">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-800">Pemeriksaan Kesiapan Ekspor DOCX</h3>
                <p className="text-xs text-slate-500">Memvalidasi sitasi, berkas, dan template sebelum menyimpan.</p>
              </div>
            </div>

            {/* Checklist */}
            <div className="space-y-2 mb-6">
              {preflightChecks.map((c, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border flex items-start space-x-3 text-xs ${
                    c.ok ? 'bg-emerald-50/50 border-emerald-200 text-emerald-900' : 'bg-amber-50/60 border-amber-200 text-amber-900'
                  }`}
                >
                  {c.ok ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="font-bold">{c.label}</span>
                    <p className="text-[11px] mt-0.5 opacity-80">{c.detail}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Warning if issues */}
            {preflightIssues.length > 0 && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 mb-6">
                <strong>Catatan:</strong> Masih ada beberapa kalimat atau penanda yang belum ditandai selesai. Anda tetap bisa melanjutkan bila yakin.
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setExportModalOpen(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                Batal & Kembali Review
              </button>
              <button
                onClick={handleExecuteExport}
                disabled={isExporting}
                className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-bold shadow-md shadow-brand-600/20 flex items-center space-x-2"
              >
                <Save className="w-4 h-4" />
                <span>{isExporting ? 'Mengekspor...' : 'Simpan & Buka di Word'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
