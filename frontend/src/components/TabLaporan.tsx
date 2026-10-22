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
  RotateCcw
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
}

export const TabLaporan: React.FC<TabLaporanProps> = ({ onGenerateComplete }) => {
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
    loadInitialData();

    // Listen to pywebview custom events
    const handleBatchProgress = (e: any) => {
      setGenProgress(e.detail);
    };
    const handleSentenceBorn = (e: any) => {
      setRecentSentences((prev) => [e.detail, ...prev.slice(0, 15)]);
    };
    const handleGenComplete = () => {
      setIsGenerating(false);
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
        const valid = t.find((x) => x.status === 'lengkap');
        if (valid) setSelectedTemplateId(valid.id);
      }
      if (v) setVariants(v);

      if (draft?.has_draft) {
        setTopic(draft.fields?.JUDUL || '');
        if (draft.sources) setSources(draft.sources);
        if (draft.fields?.DOSEN) setSelectedDosen(draft.fields.DOSEN);
        if (draft.fields?.MATA_KULIAH) setSelectedMatkul(draft.fields.MATA_KULIAH);
        if (draft.fields?.LOGO_PATH) setSelectedLogoPath(draft.fields.LOGO_PATH);
        if (draft.fields?.TEMPLATE_ID) setSelectedTemplateId(Number(draft.fields.TEMPLATE_ID));
      } else if (v) {
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
    try {
      const res = await api.pickPdfSource();
      if (res?.success && res.record) {
        setSources((prev) => [...prev, res.record!]);
        toast.success('Sumber PDF berhasil ditambahkan.');
      } else if (res?.error) {
        toast.error(res.error);
      }
    } finally {
      setLoadingSource(false);
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

    setIsGenerating(true);
    setRecentSentences([]);
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
      {/* Live Generation Overlay View */}
      {isGenerating ? (
        <div className="flex-1 bg-slate-900 text-white flex flex-col p-8 overflow-hidden select-none">
          <div className="max-w-4xl w-full mx-auto flex-1 flex flex-col justify-between">
            {/* Header & Status */}
            <div>
              <div className="flex items-center justify-between pb-6 border-b border-slate-800">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-600/30 border border-brand-500/50 flex items-center justify-center text-brand-400 animate-pulse">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white tracking-tight">AI Sedang Menyusun Laporan...</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Batch {genProgress.batch} dari {genProgress.total} • Kalimat langsung diverifikasi dengan teks sumber
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleCancelGenerate}
                  className="px-4 py-2 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 rounded-xl text-xs font-semibold flex items-center space-x-2 transition"
                >
                  <Square className="w-3.5 h-3.5" />
                  <span>Batalkan</span>
                </button>
              </div>

              {/* Progress bar */}
              <div className="mt-4 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-brand-500 h-full transition-all duration-300"
                  style={{ width: `${Math.round((genProgress.batch / Math.max(1, genProgress.total)) * 100)}%` }}
                />
              </div>
            </div>

            {/* Live Streaming Sentences Box */}
            <div className="my-6 flex-1 bg-slate-950/70 border border-slate-800/80 rounded-2xl p-6 overflow-y-auto font-serif space-y-3">
              <span className="text-[11px] font-sans font-bold uppercase tracking-wider text-brand-400/80 block mb-2">
                Kalimat Baru Lahir & Diverifikasi:
              </span>
              {recentSentences.map((s, idx) => (
                <div
                  key={s.uid || idx}
                  className="text-sm leading-relaxed text-slate-200 transition-all animate-fadeIn"
                >
                  <span>{s.text}</span>{' '}
                  <span
                    className={`text-[10px] font-sans font-bold px-1.5 py-0.5 rounded ${
                      s.status === 'terverifikasi'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                        : s.status === 'bukan_klaim'
                        ? 'bg-slate-800 text-slate-400'
                        : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                    }`}
                  >
                    {s.status}
                  </span>
                </div>
              ))}
            </div>

            <div className="text-center text-xs text-slate-500">
              Menjaga akurasi kutipan APA 7 • Bab dinormalisasi sesuai varian yang dipilih
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
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                  Judul Laporan Akademik
                </label>
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
                  {selectedTemplateId && (
                    <div className="mt-2 p-2 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-mono text-[10px]">
                          A4 (4-4-3-3 cm)
                        </span>
                        <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700 font-mono text-[10px]">
                          Times New Roman 12pt
                        </span>
                        <span className="px-2 py-0.5 rounded bg-indigo-50 border border-indigo-200 text-indigo-700 font-semibold text-[10px]">
                          APA 7 Ready
                        </span>
                      </div>
                    </div>
                  )}
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
                        Varian {v.code.toUpperCase()}: {v.name}
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
