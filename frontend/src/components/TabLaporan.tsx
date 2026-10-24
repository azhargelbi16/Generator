import React, { useState, useEffect } from 'react';
import { 
  FilePlus, 
  Globe, 
  FileText, 
  Sparkles, 
  Trash2, 
  Edit3, 
  Play, 
  Square, 
  BookOpen, 
  Layers, 
  ExternalLink,
  Plus,
  CheckCircle2,
  AlertCircle,
  FolderOpen,
  Search,
  Hash,
  Clock,
  RotateCcw,
  Loader2
} from 'lucide-react';
import { 
  api, 
  SourceRecord, 
  FormatVariant, 
  Dosen, 
  MataKuliah, 
  Logo, 
  TemplateItem,
  SavedDraftItem
} from '../lib/api';
import { toast } from '../lib/toast';

interface TabLaporanProps {
  onGenerateComplete: () => void;
  onGeneratingChange?: (generating: boolean) => void;
  isActive?: boolean;
}

export const TabLaporan: React.FC<TabLaporanProps> = ({ onGenerateComplete, onGeneratingChange, isActive = false }) => {
  const streamEndRef = React.useRef<HTMLDivElement>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  // Inputs & Setup
  const [topic, setTopic] = useState('');
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [selectedSourceIdx, setSelectedSourceIdx] = useState<number | null>(null);

  // Entities & Dropdowns
  const [dosenList, setDosenList] = useState<Dosen[]>([]);
  const [matkulList, setMatkulList] = useState<MataKuliah[]>([]);
  const [logoList, setLogoList] = useState<Logo[]>([]);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [variants, setVariants] = useState<FormatVariant[]>([]);

  // Selected values
  const [selectedDosen, setSelectedDosen] = useState('');
  const [selectedMatkul, setSelectedMatkul] = useState('');
  const [selectedLogoPath, setSelectedLogoPath] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [selectedVariant, setSelectedVariant] = useState('b');
  const [outline, setOutline] = useState<string[]>([]);

  // Modals & States
  const [webUrlModal, setWebUrlModal] = useState(false);
  const [webUrlInput, setWebUrlInput] = useState('');
  const [manualTextModal, setManualTextModal] = useState(false);
  const [manualTextInput, setManualTextInput] = useState('');
  const [loadingSource, setLoadingSource] = useState(false);
  const [suggestingOutline, setSuggestingOutline] = useState(false);
  const [generatingTitle, setGeneratingTitle] = useState(false);

  // DOI Resolver State
  const [doiModal, setDoiModal] = useState(false);
  const [doiInput, setDoiInput] = useState('');
  const [resolvingDoi, setResolvingDoi] = useState(false);

  // Project & Draft Manager State
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [savedDrafts, setSavedDrafts] = useState<SavedDraftItem[]>([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [loadingProjects, setLoadingProjects] = useState(false);

  // Generation Live State
  const [isGenerating, setIsGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState({ batch: 1, total: 1 });
  const [recentSentences, setRecentSentences] = useState<Array<{ uid: string; text: string; status: string }>>([]);

  useEffect(() => {
    onGeneratingChange?.(isGenerating);
  }, [isGenerating, onGeneratingChange]);

  useEffect(() => {
    loadInitialData();

    // Listen to pywebview custom events
    const handleBatchProgress = (e: any) => {
      setGenProgress(e.detail);
    };
    const handleSentenceBorn = (e: any) => {
      setRecentSentences((prev) => [...prev, e.detail]);
    };
    const handleGenComplete = (e: any) => {
      setIsGenerating(false);
      if (e?.detail?.sections) {
        api.saveActiveDraft({
          fields: {
            JUDUL: topic,
            DOSEN: selectedDosen,
            MATA_KULIAH: selectedMatkul,
            LOGO_PATH: selectedLogoPath,
            TEMPLATE_ID: selectedTemplateId,
            VARIANT: selectedVariant,
            OUTLINE: outline,
          },
          sources,
          sections: e.detail.sections,
          done: [],
        });
      }
      onGenerateComplete();
    };
    const handleGenError = (e: any) => {
      setIsGenerating(false);
      toast.error('Terjadi kesalahan saat generate: ' + e.detail.error);
    };

    window.addEventListener('gen_batch_progress', handleBatchProgress);
    window.addEventListener('gen_sentence_born', handleSentenceBorn);
    window.addEventListener('gen_complete', handleGenComplete);
    window.addEventListener('gen_error', handleGenError);

    return () => {
      window.removeEventListener('gen_batch_progress', handleBatchProgress);
      window.removeEventListener('gen_sentence_born', handleSentenceBorn);
      window.removeEventListener('gen_complete', handleGenComplete);
      window.removeEventListener('gen_error', handleGenError);
    };
  }, []);

  // Reload dropdowns and template data whenever tab becomes active
  useEffect(() => {
    if (isActive && !isGenerating) {
      loadInitialData();
    }
  }, [isActive]);

  // Auto-save form inputs to active draft after 1000ms idle
  useEffect(() => {
    if (isGenerating) return;
    if (!topic && sources.length === 0 && outline.length === 0) return;

    const timer = setTimeout(() => {
      api.saveActiveDraft({
        fields: {
          JUDUL: topic,
          DOSEN: selectedDosen,
          MATA_KULIAH: selectedMatkul,
          LOGO_PATH: selectedLogoPath,
          TEMPLATE_ID: selectedTemplateId,
          VARIANT: selectedVariant,
          OUTLINE: outline,
        },
        sources,
        sections: [],
        done: [],
      });
    }, 1000);

    return () => clearTimeout(timer);
  }, [topic, sources, selectedDosen, selectedMatkul, selectedLogoPath, selectedTemplateId, selectedVariant, outline, isGenerating]);

  // Smooth auto-scroll saat kalimat baru tiba
  useEffect(() => {
    if (autoScroll && isGenerating) {
      streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [recentSentences, autoScroll, isGenerating]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 140;
    setAutoScroll(isNearBottom);
  };

  const loadInitialData = async () => {
    try {
      const [d, m, l, t, v, draft] = await Promise.all([
        api.listDosen(),
        api.listMatkul(),
        api.listLogos(),
        api.listTemplates(),
        api.getFormatVariants(),
        api.loadActiveDraft(),
      ]);

      if (d) setDosenList(d);
      if (m) setMatkulList(m);
      if (l) setLogoList(l);
      if (t) {
        setTemplates(t);
        setSelectedTemplateId((prev) => {
          if (prev && t.some((item) => item.id === prev)) {
            return prev;
          }
          const defaultItem = t.find((x) => x.is_default && x.status === 'lengkap');
          if (defaultItem) return defaultItem.id;
          const valid = t.find((x) => x.status === 'lengkap');
          return valid ? valid.id : (t[0] ? t[0].id : null);
        });
      }
      if (v) setVariants(v);

      if (draft?.has_draft) {
        setTopic(draft.fields?.JUDUL || '');
        if (draft.sources) setSources(draft.sources);
        if (draft.fields?.DOSEN) setSelectedDosen(draft.fields.DOSEN);
        if (draft.fields?.MATA_KULIAH) setSelectedMatkul(draft.fields.MATA_KULIAH);
        if (draft.fields?.LOGO_PATH) setSelectedLogoPath(draft.fields.LOGO_PATH);
        if (draft.fields?.TEMPLATE_ID) setSelectedTemplateId(Number(draft.fields.TEMPLATE_ID));
        if (draft.fields?.VARIANT) setSelectedVariant(draft.fields.VARIANT);

        if (draft.fields?.OUTLINE && Array.isArray(draft.fields.OUTLINE) && draft.fields.OUTLINE.length > 0) {
          setOutline(draft.fields.OUTLINE);
        } else if (draft.sections && draft.sections.length > 0) {
          setOutline(draft.sections.map((s) => s.title));
        } else if (v) {
          const matchedV = v.find((x) => x.code === (draft.fields?.VARIANT || 'b'));
          if (matchedV && matchedV.outline_titles.length > 0) {
            setOutline(matchedV.outline_titles);
          }
        }
      } else if (v && outline.length === 0) {
        // default variant outline
        const varB = v.find((x) => x.code === 'b');
        if (varB) setOutline(varB.outline_titles);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleVariantChange = (code: string) => {
    setSelectedVariant(code);
    const v = variants.find((x) => x.code === code);
    if (v && v.outline_titles.length > 0) {
      setOutline(v.outline_titles);
    } else {
      setOutline([]);
    }
  };

  // Add Sources Handlers
  const handleAddPdf = async () => {
    setLoadingSource(true);
    toast.info('Membuka dialog dan memproses berkas PDF...');
    try {
      const res = await api.pickPdfSource();
      if (res?.success && res.record) {
        setSources((prev) => [...prev, res.record!]);
        toast.success(`Sumber PDF "${res.record.title || 'Dokumen'}" berhasil ditambahkan.`);
      } else if (res?.error) {
        toast.error(res.error);
      }
    } catch (err: any) {
      toast.error(`Gagal membaca PDF: ${err?.message || err}`);
    } finally {
      setLoadingSource(false);
    }
  };

  const handleAutoGenerateTitle = async () => {
    if (sources.length === 0) {
      toast.error('Tambahkan setidaknya satu sumber jurnal terlebih dahulu di panel kiri.');
      return;
    }
    setGeneratingTitle(true);
    try {
      const res = await api.generateTitleFromSources(sources);
      if (res?.success && res.title) {
        setTopic(res.title);
        toast.success('Judul laporan berhasil disusun dari sumber jurnal!');
      } else {
        toast.error(res?.error || 'Gagal merumuskan judul otomatis.');
      }
    } catch (err: any) {
      toast.error(`Terjadi kesalahan: ${err?.message || err}`);
    } finally {
      setGeneratingTitle(false);
    }
  };

  const handleAddWeb = async () => {
    if (!webUrlInput.trim()) return;
    setLoadingSource(true);
    try {
      const res = await api.addWebSource(webUrlInput.trim());
      if (res?.success && res.record) {
        setSources((prev) => [...prev, res.record!]);
        setWebUrlModal(false);
        setWebUrlInput('');
        toast.success('Sumber Web berhasil ditambahkan.');
      } else if (res?.error) {
        toast.error(res.error);
      }
    } finally {
      setLoadingSource(false);
    }
  };

  const handleAddManual = async () => {
    if (!manualTextInput.trim()) return;
    setLoadingSource(true);
    try {
      const res = await api.addManualSource(manualTextInput.trim());
      if (res?.success && res.record) {
        setSources((prev) => [...prev, res.record!]);
        setManualTextModal(false);
        setManualTextInput('');
        toast.success('Sumber Manual berhasil ditambahkan.');
      } else if (res?.error) {
        toast.error(res.error);
      }
    } finally {
      setLoadingSource(false);
    }
  };

  // DOI Resolver Handler
  const handleResolveDoi = async () => {
    if (!doiInput.trim()) return;
    setResolvingDoi(true);
    try {
      const res = await api.resolveDoiSource(doiInput.trim());
      if (res?.success && res.record) {
        setSources((prev) => [...prev, res.record!]);
        setDoiModal(false);
        setDoiInput('');
        toast.success(`Berhasil menambahkan referensi: ${res.record.title}`);
      } else {
        toast.error(res?.error || 'Gagal menyelesaikan DOI.');
      }
    } finally {
      setResolvingDoi(false);
    }
  };

  // Multi-Project Handlers
  const handleOpenProjectModal = async () => {
    setLoadingProjects(true);
    setProjectModalOpen(true);
    try {
      const list = await api.listSavedDrafts();
      if (list) setSavedDrafts(list);
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleSaveNamedProject = async () => {
    if (!newProjectName.trim()) {
      toast.error('Masukkan nama proyek terlebih dahulu.');
      return;
    }
    const state = {
      fields: {
        JUDUL: topic,
        DOSEN: selectedDosen,
        MATA_KULIAH: selectedMatkul,
        LOGO_PATH: selectedLogoPath,
        TEMPLATE_ID: selectedTemplateId,
        VARIANT: selectedVariant,
        OUTLINE: outline,
      },
      sources,
      sections: [],
      done: [],
    };
    const res = await api.saveNamedDraft(newProjectName.trim(), state);
    if (res?.success) {
      toast.success(`Proyek '${newProjectName}' berhasil disimpan!`);
      setNewProjectName('');
      const list = await api.listSavedDrafts();
      if (list) setSavedDrafts(list);
    } else {
      toast.error(res?.error || 'Gagal menyimpan proyek.');
    }
  };

  const handleLoadProject = async (draftId: string) => {
    const res = await api.loadNamedDraft(draftId);
    if (res?.success && res.draft) {
      const d = res.draft;
      setTopic(d.fields?.JUDUL || '');
      if (d.sources) setSources(d.sources);
      if (d.fields?.DOSEN) setSelectedDosen(d.fields.DOSEN);
      if (d.fields?.MATA_KULIAH) setSelectedMatkul(d.fields.MATA_KULIAH);
      if (d.fields?.LOGO_PATH) setSelectedLogoPath(d.fields.LOGO_PATH);
      if (d.fields?.TEMPLATE_ID) setSelectedTemplateId(Number(d.fields.TEMPLATE_ID));
      if (d.fields?.VARIANT) setSelectedVariant(d.fields.VARIANT);
      if (d.fields?.OUTLINE && Array.isArray(d.fields.OUTLINE) && d.fields.OUTLINE.length > 0) {
        setOutline(d.fields.OUTLINE);
      } else if (d.sections && d.sections.length > 0) {
        setOutline(d.sections.map((s: any) => s.title));
      }
      setProjectModalOpen(false);
      toast.success(`Proyek '${d.fields?.JUDUL || draftId}' berhasil dimuat.`);
    } else {
      toast.error(res?.error || 'Gagal memuat proyek.');
    }
  };

  const handleDeleteProject = async (draftId: string) => {
    await api.deleteNamedDraft(draftId);
    const list = await api.listSavedDrafts();
    if (list) setSavedDrafts(list);
    toast.success('Draf proyek berhasil dihapus.');
  };

  const handleNewBlankProject = async () => {
    await api.clearActiveDraft();
    setTopic('');
    setSources([]);
    setSelectedSourceIdx(null);
    const varB = variants.find((x) => x.code === 'b');
    if (varB) setOutline(varB.outline_titles);
    setProjectModalOpen(false);
    toast.info('Memulai lembar kerja proyek baru.');
  };

  const handleDeleteSource = (idx: number) => {
    setSources((prev) => prev.filter((_, i) => i !== idx));
    if (selectedSourceIdx === idx) setSelectedSourceIdx(null);
  };

  const handleSuggestOutline = async () => {
    if (!topic.trim()) {
      toast.error('Tulis judul laporan terlebih dahulu.');
      return;
    }
    setSuggestingOutline(true);
    try {
      const res = await api.suggestOutline(topic, sources);
      if (res?.success && res.outline) {
        setOutline(res.outline);
        toast.success('Saran outline berhasil disusun.');
      } else {
        toast.error(res?.error || 'Gagal menyusun saran outline.');
      }
    } finally {
      setSuggestingOutline(false);
    }
  };

  // Start Generate
  const handleStartGenerate = async () => {
    if (!topic.trim()) {
      toast.error('Judul laporan belum diisi.');
      return;
    }
    if (sources.length === 0) {
      toast.error('Masukkan minimal satu sumber referensi.');
      return;
    }
    if (outline.length === 0) {
      toast.error('Outline masih kosong.');
      return;
    }

    await api.saveActiveDraft({
      fields: {
        JUDUL: topic,
        DOSEN: selectedDosen,
        MATA_KULIAH: selectedMatkul,
        LOGO_PATH: selectedLogoPath,
        TEMPLATE_ID: selectedTemplateId,
        VARIANT: selectedVariant,
        OUTLINE: outline,
      },
      sources,
      sections: [],
      done: [],
    });

    setIsGenerating(true);
    setRecentSentences([]);
    setAutoScroll(true);
    const res = await api.startGeneration({
      topic,
      outline,
      sources,
      variant: selectedVariant,
    });
    if (res?.error) {
      setIsGenerating(false);
      toast.error(res.error);
    }
  };

  const handleCancelGenerate = async () => {
    await api.cancelGeneration();
    setIsGenerating(false);
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Live Generation Paper Canvas */}
      {isGenerating ? (
        <div className="flex-1 bg-slate-100/90 flex flex-col h-full overflow-hidden select-none">
          {/* Top Floating Glass Header */}
          <div className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-8 py-4 shrink-0 shadow-xs z-10">
            <div className="max-w-4xl mx-auto flex items-center justify-between">
              <div className="flex items-center space-x-3.5 min-w-0">
                <div className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shadow-xs shrink-0">
                  <Sparkles className="w-5 h-5 animate-pulse" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-extrabold text-slate-800 tracking-tight truncate">
                      {topic || 'Menyusun Laporan Akademik...'}
                    </h3>
                    <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 text-[10px] font-extrabold border border-blue-200 shrink-0">
                      Batch {genProgress.batch} dari {genProgress.total}
                    </span>
                  </div>
                  <div className="flex items-center space-x-3 text-xs text-slate-500 mt-1">
                    <span className="flex items-center gap-1 font-semibold text-slate-700">
                      <FileText className="w-3.5 h-3.5 text-blue-600" />
                      <span>{recentSentences.length} Kalimat Disusun</span>
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{recentSentences.filter((s) => s.status === 'terverifikasi').length} Terverifikasi</span>
                    </span>
                    <span>•</span>
                    <span className="text-slate-400">Verifikasi Sitasi APA 7 Real-Time</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3 shrink-0">
                <button
                  type="button"
                  onClick={handleCancelGenerate}
                  className="px-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition shadow-xs active:scale-95"
                >
                  <Square className="w-3.5 h-3.5 fill-rose-600 text-rose-600" />
                  <span>Batalkan Generasi</span>
                </button>
              </div>
            </div>

            {/* Smooth progress bar */}
            <div className="max-w-4xl mx-auto mt-3 bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-600 to-indigo-600 h-full transition-all duration-500 rounded-full"
                style={{ width: `${Math.round((genProgress.batch / Math.max(1, genProgress.total)) * 100)}%` }}
              />
            </div>
          </div>

          {/* Flowing A4 Paper Sheet Preview */}
          <div
            ref={containerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-6 md:p-8 flex justify-center"
          >
            <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl border border-slate-200/90 p-8 md:p-12 paper-sheet font-serif min-h-[600px] flex flex-col justify-between">
              <div>
                {/* Report Title on Paper */}
                <div className="text-center pb-6 mb-8 border-b border-slate-200">
                  <h1 className="text-lg md:text-xl font-bold text-slate-900 tracking-tight font-sans">
                    {topic.toUpperCase() || 'LAPORAN AKADEMIK'}
                  </h1>
                  <p className="text-xs text-slate-500 font-sans mt-2">
                    Disusun otomatis berbasis sintesis {sources.length} sumber referensi • Format Baku Akademik
                  </p>
                </div>

                {/* Sentences flow as real paragraphs */}
                <div className="text-slate-800 text-[15px] leading-relaxed md:leading-[1.85] text-justify space-y-4">
                  {recentSentences.length === 0 ? (
                    <div className="text-center py-24 text-slate-400 font-sans text-xs flex flex-col items-center space-y-2">
                      <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                      <span>Mempersiapkan sintesis pustaka dan merancang kerangka bab...</span>
                    </div>
                  ) : (
                    <div className="inline">
                      {recentSentences.map((s, idx) => {
                        const isLatest = idx === recentSentences.length - 1;
                        return (
                          <span
                            key={s.uid || idx}
                            className={`inline transition-all ${
                              isLatest ? 'animate-sentence-born bg-blue-50/60 font-medium' : ''
                            }`}
                          >
                            <span>{s.text} </span>
                          </span>
                        );
                      })}
                      {/* Blinking typing cursor at end */}
                      <span className="inline-block w-1.5 h-4 bg-blue-600 animate-cursor-blink ml-1 align-middle rounded-xs" />
                    </div>
                  )}
                  <div ref={streamEndRef} className="h-4" />
                </div>
              </div>

              {/* Floating Bottom Auto-scroll Pill (if user scrolled up) */}
              {!autoScroll && (
                <div className="sticky bottom-4 flex justify-center mt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setAutoScroll(true);
                      streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="px-3.5 py-1.5 bg-slate-900/90 text-white text-xs font-semibold rounded-full shadow-lg backdrop-blur-md flex items-center space-x-1.5 hover:bg-slate-800 transition"
                  >
                    <span>Gulir ke kalimat terbaru ↓</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Normal Setup View */
        <div className="flex-1 flex overflow-hidden">
          {/* Left Column: Sumber Referensi */}
          <div className="w-96 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0">
            <div className="p-5 flex-1 flex flex-col overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <BookOpen className="w-4 h-4 text-brand-600" />
                  <h3 className="font-bold text-slate-800 text-sm">Sumber Referensi</h3>
                </div>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {sources.length}
                </span>
              </div>

              {/* Source action buttons */}
              <div className="grid grid-cols-4 gap-1.5 mb-4">
                <button
                  onClick={handleAddPdf}
                  disabled={loadingSource}
                  className="p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold flex flex-col items-center justify-center space-y-1 transition text-center"
                  title="Unggah berkas PDF native atau scan OCR"
                >
                  <FilePlus className="w-4 h-4 text-brand-600" />
                  <span>PDF/OCR</span>
                </button>
                <button
                  onClick={() => setDoiModal(true)}
                  disabled={loadingSource}
                  className="p-2 rounded-xl border border-purple-200 bg-purple-50/50 hover:bg-purple-100/60 text-purple-800 text-[11px] font-semibold flex flex-col items-center justify-center space-y-1 transition text-center"
                  title="Cari metadata resmi via DOI CrossRef"
                >
                  <Hash className="w-4 h-4 text-purple-600" />
                  <span>Cari DOI</span>
                </button>
                <button
                  onClick={() => setWebUrlModal(true)}
                  disabled={loadingSource}
                  className="p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold flex flex-col items-center justify-center space-y-1 transition text-center"
                  title="Ambil teks dari link web atau jurnal"
                >
                  <Globe className="w-4 h-4 text-blue-600" />
                  <span>Tautan Web</span>
                </button>
                <button
                  onClick={() => setManualTextModal(true)}
                  disabled={loadingSource}
                  className="p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold flex flex-col items-center justify-center space-y-1 transition text-center"
                  title="Tempel teks referensi langsung"
                >
                  <FileText className="w-4 h-4 text-amber-600" />
                  <span>Manual</span>
                </button>
              </div>

              {/* Source List */}
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {loadingSource && (
                  <div className="p-3 mb-2 rounded-xl bg-brand-50 border border-brand-200 text-brand-800 text-xs flex items-center space-x-2 animate-pulse">
                    <Loader2 className="w-4 h-4 animate-spin text-brand-600 shrink-0" />
                    <span>Sedang memproses sumber & mengekstrak data...</span>
                  </div>
                )}
                {sources.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-xs">
                    Belum ada sumber referensi.<br />Tambahkan PDF atau tautan web di atas.
                  </div>
                ) : (
                  sources.map((s, idx) => {
                    const isSelected = selectedSourceIdx === idx;
                    return (
                      <div
                        key={idx}
                        onClick={() => setSelectedSourceIdx(idx)}
                        className={`p-3 rounded-xl border text-left cursor-pointer transition ${
                          isSelected
                            ? 'border-brand-500 bg-brand-50/50 shadow-sm'
                            : 'border-slate-200/80 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0 pr-2">
                            <div className="flex items-center gap-1.5 mb-1">
                              <span className="text-[10px] font-bold uppercase px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                                {s.kind?.toUpperCase() || 'WEB'}
                              </span>
                              {(s.text?.length || 0) > 8000 ? (
                                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  Naskah Lengkap ({Math.round((s.text?.length || 0) / 1000)}k karakter)
                                </span>
                              ) : (
                                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                                  Abstrak ({s.text?.length || 0} karakter)
                                </span>
                              )}
                            </div>
                            <h4 className="text-xs font-bold text-slate-800 truncate">
                              {idx + 1}. {s.title || 'Tanpa Judul'}
                            </h4>
                            <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                              {s.authors?.map((a) => a.family).join(', ') || 'Tanpa Penulis'} ({s.year || 'n.d.'})
                            </p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteSource(idx);
                            }}
                            className="text-slate-400 hover:text-rose-600 p-1"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Selected source metadata editor drawer */}
            {selectedSourceIdx !== null && sources[selectedSourceIdx] && (
              <div className="p-4 border-t border-slate-200 bg-slate-50 text-xs space-y-2">
                <div className="flex items-center justify-between font-bold text-slate-700">
                  <span>Koreksi Metadata Sumber #{selectedSourceIdx + 1}</span>
                  <button onClick={() => setSelectedSourceIdx(null)} className="text-slate-400 hover:text-slate-600">✕</button>
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 font-semibold uppercase">Judul</label>
                  <input
                    type="text"
                    value={sources[selectedSourceIdx].title || ''}
                    onChange={(e) => {
                      const updated = [...sources];
                      updated[selectedSourceIdx].title = e.target.value;
                      setSources(updated);
                    }}
                    className="w-full px-2 py-1 bg-white border border-slate-200 rounded text-xs"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-500 font-semibold uppercase">Tahun</label>
                    <input
                      type="text"
                      value={sources[selectedSourceIdx].year || ''}
                      onChange={(e) => {
                        const updated = [...sources];
                        updated[selectedSourceIdx].year = e.target.value;
                        setSources(updated);
                      }}
                      className="w-full px-2 py-1 bg-white border border-slate-200 rounded text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500 font-semibold uppercase">Publikasi / Jurnal</label>
                    <input
                      type="text"
                      value={sources[selectedSourceIdx].container || ''}
                      onChange={(e) => {
                        const updated = [...sources];
                        updated[selectedSourceIdx].container = e.target.value;
                        setSources(updated);
                      }}
                      className="w-full px-2 py-1 bg-white border border-slate-200 rounded text-xs"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Pengaturan Laporan & Outline */}
          <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-800 tracking-tight">Formulir Pembuatan Laporan</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Tentukan judul, format varian fakultas, dan tinjau struktur outline bab sebelum AI mulai menulis.
                </p>
              </div>
              <button
                type="button"
                onClick={handleOpenProjectModal}
                className="px-4 py-2 bg-slate-100 hover:bg-brand-50 hover:text-brand-700 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold flex items-center space-x-2 transition shadow-sm"
              >
                <FolderOpen className="w-4 h-4 text-brand-600" />
                <span>Kelola Draf & Proyek</span>
              </button>
            </div>

            {/* Judul Laporan */}
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                    Judul Laporan Akademik
                  </label>
                  <button
                    type="button"
                    onClick={handleAutoGenerateTitle}
                    disabled={generatingTitle || sources.length === 0}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition border ${
                      sources.length === 0
                        ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed opacity-70'
                        : 'bg-purple-50 hover:bg-purple-100 text-purple-700 border-purple-200 shadow-sm active:scale-95'
                    }`}
                    title={
                      sources.length === 0
                        ? 'Tambahkan sumber jurnal di panel kiri untuk merumuskan judul otomatis'
                        : 'Rumuskan rekomendasi judul laporan akademik otomatis berdasarkan jurnal referensi'
                    }
                  >
                    {generatingTitle ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-600" />
                        <span>Menyusun Judul AI...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                        <span>Saran Judul dari Jurnal (AI)</span>
                      </>
                    )}
                  </button>
                </div>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="Contoh: Analisis Kinerja Algoritma Klasifikasi Data Mining pada Citra Medis"
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-base font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>

              {/* Template & Formats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                      Template Word (.docx)
                    </label>
                    {templates.length > 0 && selectedTemplateId && (
                      <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>Format Terverifikasi</span>
                      </span>
                    )}
                  </div>
                  <select
                    value={selectedTemplateId || ''}
                    onChange={(e) => setSelectedTemplateId(Number(e.target.value))}
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 font-medium text-slate-800"
                  >
                    {templates.map((t) => (
                      <option key={t.id} value={t.id} disabled={t.status !== 'lengkap'}>
                        {t.nama} {t.status !== 'lengkap' ? '(Kurang Penanda)' : '✓ Siap Pakai'}
                      </option>
                    ))}
                  </select>

                  {/* Selected Template Academic Spec Bar */}
                  {selectedTemplateId && (() => {
                    const selT = templates.find((t) => t.id === selectedTemplateId);
                    return (
                      <div className="mt-2 p-2 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-mono text-[10px]">
                            {selT?.spec?.paper || 'A4'} ({selT?.spec?.margin || '4-4-3-3 cm'})
                          </span>
                          <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-mono text-[10px]">
                            {selT?.spec?.font || 'Times New Roman 12pt'}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-mono text-[10px]">
                            Spasi {selT?.spec?.spacing || '1.5'}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-indigo-50 border border-indigo-200 text-indigo-700 font-semibold text-[10px]">
                            APA 7 Ready
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Varian Format Laporan
                  </label>
                  <select
                    value={selectedVariant}
                    onChange={(e) => handleVariantChange(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 font-semibold text-brand-800"
                  >
                    {variants.map((v) => (
                      <option key={v.code} value={v.code}>
                        {v.code === 'b' ? '⭐ Varian B (Baku): Makalah Kuliah Standar Dikti (4 Bab)' :
                         v.code === 'a' ? '📚 Varian A: Makalah Tinjauan / Komparatif (Multi-Topik)' :
                         v.code === 'c' ? '🔬 Varian C: Laporan Praktikum Laboratorium' :
                         '✨ Format Bebas: Outline Kustom'}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Dosen & Matkul Selection */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Dosen Pembimbing</label>
                  <select
                    value={selectedDosen}
                    onChange={(e) => setSelectedDosen(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="">-- Pilih Dosen --</option>
                    {dosenList.map((d) => (
                      <option key={d.id} value={`${d.nama}${d.gelar ? ', ' + d.gelar : ''}`}>
                        {d.nama} {d.gelar}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Mata Kuliah</label>
                  <select
                    value={selectedMatkul}
                    onChange={(e) => setSelectedMatkul(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="">-- Pilih Mata Kuliah --</option>
                    {matkulList.map((m) => (
                      <option key={m.id} value={m.nama}>
                        {m.nama}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Logo Kampus</label>
                  <select
                    value={selectedLogoPath}
                    onChange={(e) => setSelectedLogoPath(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="">-- Pilih Logo --</option>
                    {logoList.map((l) => (
                      <option key={l.id} value={l.path}>
                        {l.nama}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Outline Box */}
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-800">Struktur Bab & Outline</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedVariant === 'bebas'
                      ? 'Format bebas: Anda bisa mengedit outline sendiri atau meminta AI mengusulkannya.'
                      : 'Format baku terkunci: Penomoran BAB 1 s/d BAB 4 mengikuti spesifikasi varian terpilih.'}
                  </p>
                </div>
                {selectedVariant === 'bebas' && (
                  <button
                    onClick={handleSuggestOutline}
                    disabled={suggestingOutline}
                    className="px-3 py-1.5 bg-brand-50 hover:bg-brand-100 text-brand-700 rounded-lg text-xs font-semibold flex items-center space-x-1.5 border border-brand-200"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{suggestingOutline ? 'Menyusun...' : 'Usulkan Outline AI'}</span>
                  </button>
                )}
              </div>

              <textarea
                value={outline.join('\n')}
                onChange={(e) => selectedVariant === 'bebas' && setOutline(e.target.value.split('\n'))}
                readOnly={selectedVariant !== 'bebas'}
                rows={8}
                className={`w-full p-4 rounded-xl text-xs font-mono border ${
                  selectedVariant === 'bebas'
                    ? 'bg-slate-50 border-slate-200'
                    : 'bg-slate-100/70 border-slate-200 text-slate-700 cursor-not-allowed'
                }`}
              />
            </div>

            {/* Generate Action Button */}
            <div className="pt-2">
              <button
                onClick={handleStartGenerate}
                disabled={sources.length === 0 || !topic.trim()}
                className="w-full py-4 bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 text-white rounded-2xl font-bold text-base shadow-lg shadow-brand-600/25 transition flex items-center justify-center space-x-3"
              >
                <Sparkles className="w-5 h-5" />
                <span>Generate Laporan Sekarang</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Web URL Modal */}
      {webUrlModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-800 mb-2">Tambah Tautan Web</h3>
            <p className="text-xs text-slate-500 mb-3">
              Mendukung tautan halaman artikel ilmiah (ArXiv, OJS kampus, Neliti) maupun berkas PDF langsung.
            </p>
            <div className="mb-4 p-2.5 bg-blue-50/60 border border-blue-200/60 rounded-xl text-[11px] text-blue-800 space-y-1">
              <p>💡 <strong>Catatan Pembacaan Tautan:</strong></p>
              <ul className="list-disc list-inside space-y-0.5 text-blue-700">
                <li>Jika tersedia file PDF Open Access, sistem otomatis mengunduh <strong>naskah lengkap</strong>.</li>
                <li>Jika situs jurnal mengunci PDF dengan paywall/login, sistem hanya akan membaca <strong>abstrak & metadata</strong>.</li>
              </ul>
            </div>
            <input
              type="url"
              value={webUrlInput}
              onChange={(e) => setWebUrlInput(e.target.value)}
              placeholder="https://..."
              className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs mb-4 font-mono"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setWebUrlModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                Batal
              </button>
              <button
                onClick={handleAddWeb}
                disabled={loadingSource || !webUrlInput.trim()}
                className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5"
              >
                <span>{loadingSource ? 'Mengambil...' : 'Tambah Sumber'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Text Modal */}
      {manualTextModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-800 mb-2">Tempel Teks Sumber Manual</h3>
            <textarea
              value={manualTextInput}
              onChange={(e) => setManualTextInput(e.target.value)}
              rows={8}
              placeholder="Tempel abstrak atau bagian jurnal di sini..."
              className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setManualTextModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                Batal
              </button>
              <button
                onClick={handleAddManual}
                disabled={loadingSource || !manualTextInput.trim()}
                className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold"
              >
                <span>{loadingSource ? 'Memproses...' : 'Simpan Sumber'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
      {/* DOI Resolver Modal */}
      {doiModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-slate-200">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-9 h-9 rounded-xl bg-purple-100 flex items-center justify-center text-purple-700">
                <Hash className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-800">Cari Referensi via DOI (CrossRef)</h3>
                <p className="text-xs text-slate-500">Metadata bibliografi APA 7 diambil langsung dan resmi dari CrossRef.</p>
              </div>
            </div>
            <div className="mb-4 p-2.5 bg-purple-50/60 border border-purple-200/60 rounded-xl text-[11px] text-purple-900 space-y-1">
              <p>💡 <strong>Contoh input yang didukung:</strong></p>
              <ul className="list-disc list-inside space-y-0.5 text-purple-800">
                <li><code>10.1016/j.biortech.2020.123456</code></li>
                <li><code>https://doi.org/10.1038/s41586-020-2649-2</code></li>
              </ul>
            </div>
            <input
              type="text"
              value={doiInput}
              onChange={(e) => setDoiInput(e.target.value)}
              placeholder="10.xxxx/..."
              className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs mb-4 font-mono"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDoiModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleResolveDoi}
                disabled={resolvingDoi || !doiInput.trim()}
                className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{resolvingDoi ? 'Menghubungi CrossRef...' : 'Cari & Tambah'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Project & Draft Manager Modal */}
      {projectModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl p-6 max-w-2xl w-full shadow-2xl border border-slate-200 max-h-[85vh] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center text-brand-700">
                    <FolderOpen className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-800">Manajemen Draf & Proyek Laporan</h3>
                    <p className="text-xs text-slate-500">Buka kembali pekerjaan sebelumnya atau simpan draf dengan nama khusus.</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setProjectModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600 text-lg font-bold p-1"
                >
                  ✕
                </button>
              </div>

              {/* Simpan Proyek Saat Ini Form */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl mb-4 flex items-center gap-2">
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="Beri nama proyek, mis: Tugas Akhir Pertanian Presisi V1"
                  className="flex-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs"
                />
                <button
                  type="button"
                  onClick={handleSaveNamedProject}
                  className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shrink-0"
                >
                  Simpan Proyek
                </button>
              </div>

              {/* Saved Drafts List */}
              <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                {loadingProjects ? (
                  <div className="text-center py-12 text-xs text-slate-400">Memuat daftar draf proyek...</div>
                ) : savedDrafts.length === 0 ? (
                  <div className="text-center py-12 text-xs text-slate-400">Belum ada draf tersimpan.</div>
                ) : (
                  savedDrafts.map((d) => (
                    <div
                      key={d.draft_id}
                      className={`p-3 rounded-xl border flex items-center justify-between text-xs transition ${
                        d.is_active ? 'bg-brand-50/60 border-brand-200' : 'bg-white border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex-1 pr-3">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-800 truncate">{d.title}</span>
                          {d.is_active && (
                            <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-brand-100 text-brand-700">
                              Aktif Sekarang
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {d.sources_count} sumber • {d.sentence_count} kalimat terverifikasi • ID: <code>{d.draft_id}</code>
                        </p>
                      </div>
                      <div className="flex items-center space-x-2 shrink-0">
                        {!d.is_active && (
                          <button
                            type="button"
                            onClick={() => handleLoadProject(d.draft_id)}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs"
                          >
                            Buka
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteProject(d.draft_id)}
                          className="p-1 text-slate-400 hover:text-rose-600"
                          title="Hapus draf ini"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-slate-100 mt-4">
              <button
                type="button"
                onClick={handleNewBlankProject}
                className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg text-xs font-semibold flex items-center space-x-1"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Mulai Lembar Kerja Kosong Baru</span>
              </button>
              <button
                type="button"
                onClick={() => setProjectModalOpen(false)}
                className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
