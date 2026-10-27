import React, { useState, useEffect } from 'react';
import { DraftManagerModal } from './DraftManagerModal';
import { 
  FilePlus, 
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
  Clock,
  RotateCcw,
  Loader2,
  Search,
  BookmarkPlus,
  X
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
  onNavigateToReview?: () => void;
}

/**
 * Deskripsi jujur atas cakupan isi sumber (UAT: mahasiswa harus tahu apakah
 * AI mengutip dari isi jurnal atau hanya abstrak/metadata).
 * `content_status` dihitung backend saat sumber ditambahkan.
 */
const describeSourceContent = (
  s: SourceRecord
): { label: string; tone: 'ok' | 'warn' | 'danger'; hint: string } => {
  const n = s.text?.length || 0;
  const status = s.content_status || (n >= 1800 ? 'fulltext' : n > 600 ? 'partial' : 'abstract');
  if (status === 'metadata_only' || (s.kind === 'doi' && n < 250)) {
    return {
      label: '⚠ Metadata saja — tanpa isi kutipan',
      tone: 'danger',
      hint: 'Sumber DOI ini tidak membawa teks yang bisa dikutip, sehingga AI tidak boleh menulis kalimat yang mengutipnya. Unggah PDF jurnal yang sama lewat tombol PDF/OCR, lalu koreksi metadata agar sitasinya memakai isi jurnal.',
    };
  }
  if (status === 'fulltext') {
    return {
      label: n >= 8000 ? `Naskah lengkap (${Math.round(n / 1000)}rb karakter)` : `Teks lengkap (${n} karakter)`,
      tone: 'ok',
      hint: 'Seluruh isi dokumen tersimpan dan dipakai AI sebagai bahan kutipan — bukan hanya abstrak.',
    };
  }
  if (status === 'partial') {
    return {
      label: `Teks ${n} karakter`,
      tone: 'warn',
      hint: 'Cakupan teks terbatas. Untuk jurnal berbayar, halaman web umumnya hanya menampilkan abstrak — unggah PDF lengkap agar AI mengutip isi jurnal (metode, hasil, pembahasan).',
    };
  }
  return {
    label: `⚠ Kemungkinan hanya abstrak (${n} karakter)`,
    tone: 'warn',
    hint: 'Teks yang tersimpan sangat pendek. Abstrak tidak cukup untuk laporan akademik — unggah PDF jurnal lengkap atau tempel teks isinya lewat tombol Manual.',
  };
};

export const TabLaporan: React.FC<TabLaporanProps> = ({ onGenerateComplete, onGeneratingChange, isActive = false, onNavigateToReview }) => {
  const streamEndRef = React.useRef<HTMLDivElement>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const onGenerateCompleteRef = React.useRef(onGenerateComplete);
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
  const [selectedVariant, setSelectedVariant] = useState('D');
  const [outline, setOutline] = useState<string[]>([]);

  // Modals & States
  const [manualTextModal, setManualTextModal] = useState(false);
  const [manualTextInput, setManualTextInput] = useState('');
  const [loadingSource, setLoadingSource] = useState(false);
  const [suggestingOutline, setSuggestingOutline] = useState(false);
  const [generatingTitle, setGeneratingTitle] = useState(false);

  // Project & Draft Manager State
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [savedDrafts, setSavedDrafts] = useState<SavedDraftItem[]>([]);
    const [loadingProjects, setLoadingProjects] = useState(false);
  const [selectedDraftIds, setSelectedDraftIds] = useState<string[]>([]);
    
  // Generation Live State
  const [isGenerating, setIsGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState({ batch: 1, total: 1 });
  const [recentSentences, setRecentSentences] = useState<Array<{ uid: string; text: string; status: string }>>([]);
  const generationContextRef = React.useRef({
    topic: '',
    selectedDosen: '',
    selectedMatkul: '',
    selectedLogoPath: '',
    selectedTemplateId: null as number | null,
    selectedVariant: 'D',
    outline: [] as string[],
    sources: [] as SourceRecord[],
  });

  useEffect(() => {
    onGenerateCompleteRef.current = onGenerateComplete;
  }, [onGenerateComplete]);

  useEffect(() => {
    generationContextRef.current = {
      topic,
      selectedDosen,
      selectedMatkul,
      selectedLogoPath,
      selectedTemplateId,
      selectedVariant,
      outline,
      sources,
    };
  }, [topic, selectedDosen, selectedMatkul, selectedLogoPath, selectedTemplateId, selectedVariant, outline, sources]);

  useEffect(() => {
    onGeneratingChange?.(isGenerating);
  }, [isGenerating, onGeneratingChange]);

  useEffect(() => {
    const modalOpen = manualTextModal || projectModalOpen;
    if (!modalOpen) return;

    const closeModal = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setManualTextModal(false);
      setProjectModalOpen(false);
    };

    window.addEventListener('keydown', closeModal);
    return () => window.removeEventListener('keydown', closeModal);
  }, [manualTextModal, projectModalOpen]);

  useEffect(() => {
    loadInitialData();

    // Metadata sumber diperkaya AI di latar setelah sumber ditambahkan
    // (unggah tetap instan); gabungkan hasilnya ke kartu yang cocok.
    const handleMetadataReady = (e: any) => {
      const d = e?.detail || {};
      if (!d.ref) return;
      setSources((prev) => prev.map((s, idx) => {
        if (s.ref !== d.ref) return s;
        const authors = Array.isArray(d.authors) && d.authors.length > 0 ? d.authors : s.authors;
        return {
          ...s,
          title: d.title || s.title,
          year: d.year || s.year,
          container: d.container || s.container,
          doi: d.doi || s.doi,
          url: d.url || s.url,
          authors,
        };
      }));
      toast.info('Metadata sumber diperbaiki otomatis dari isi dokumen (AI). Koreksi manual tetap bisa lewat kartu sumber.');
    };

    // Listen to pywebview custom events
    const handleBatchProgress = (e: any) => {
      setGenProgress(e.detail);
    };
    const handleSentenceBorn = (e: any) => {
      setRecentSentences((prev) => [...prev, e.detail]);
    };
    const handleGenComplete = async (e: any) => {
      const generatedSections = e?.detail?.sections;
      if (!Array.isArray(generatedSections) || generatedSections.length === 0) {
        setIsGenerating(false);
        toast.error('Laporan selesai tanpa isi dokumen. Silakan coba generate ulang.');
        return;
      }

      const current = generationContextRef.current;
      try {
        await api.saveActiveDraft({
          fields: {
            JUDUL: current.topic,
            DOSEN: current.selectedDosen,
            MATA_KULIAH: current.selectedMatkul,
            LOGO_PATH: current.selectedLogoPath,
            TEMPLATE_ID: current.selectedTemplateId,
            VARIANT: current.selectedVariant,
            OUTLINE: current.outline,
          },
          sources: current.sources,
          sections: generatedSections,
          done: [],
        });
        setIsGenerating(false);
        onGenerateCompleteRef.current();
      } catch (error) {
        console.error(error);
        setIsGenerating(false);
        toast.error('Laporan selesai tetapi gagal disimpan. Tab Review tidak dibuka agar dokumen tidak kosong.');
      }
    };
    const handleGenError = (e: any) => {
      setIsGenerating(false);
      toast.error('Terjadi kesalahan saat generate: ' + e.detail.error);
    };

    window.addEventListener('gen_batch_progress', handleBatchProgress);
    window.addEventListener('gen_sentence_born', handleSentenceBorn);
    window.addEventListener('gen_complete', handleGenComplete);
    window.addEventListener('gen_error', handleGenError);
    window.addEventListener('source_metadata_ready', handleMetadataReady);

    return () => {
      window.removeEventListener('gen_batch_progress', handleBatchProgress);
      window.removeEventListener('gen_sentence_born', handleSentenceBorn);
      window.removeEventListener('gen_complete', handleGenComplete);
      window.removeEventListener('gen_error', handleGenError);
      window.removeEventListener('source_metadata_ready', handleMetadataReady);
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
      window.dispatchEvent(new CustomEvent('generator-save-state', { detail: { status: 'saving' } }));
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
      }).then(() => {
        window.dispatchEvent(new CustomEvent('generator-save-state', { detail: { status: 'saved' } }));
      }).catch((err) => {
        // Autosave yang gagal tidak boleh diam saja (F2); tandai di header.
        console.error('[Autosave Gagal]', err);
        window.dispatchEvent(new CustomEvent('generator-save-state', { detail: { status: 'error' } }));
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
    // allSettled (bukan Promise.all): satu panggilan gagal tidak boleh
    // mengosongkan SEMUA dropdown — dosen/matkul/logo/template tetap terisi
    // dan kegagalan yang ada dilaporkan eksplisit.
    try {
      const [d, m, l, t, v, draft] = await Promise.all([
        api.listDosen().catch((err) => { console.error('[listDosen]', err); return null; }),
        api.listMatkul().catch((err) => { console.error('[listMatkul]', err); return null; }),
        api.listLogos().catch((err) => { console.error('[listLogos]', err); return null; }),
        api.listTemplates().catch((err) => { console.error('[listTemplates]', err); return null; }),
        api.getFormatVariants().catch((err) => { console.error('[getFormatVariants]', err); return null; }),
        api.loadActiveDraft().catch((err) => { console.error('[loadActiveDraft]', err); return null; }),
      ]);

      if (Array.isArray(d) && d.length >= 0) setDosenList(d);
      if (Array.isArray(m)) setMatkulList(m);
      if (Array.isArray(l)) setLogoList(l);
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

      const currentVar = (draft?.fields?.VARIANT || 'D').toUpperCase();
      const normalizedVar = ['A', 'B', 'C', 'D'].includes(currentVar) ? currentVar : (currentVar === 'BEBAS' ? 'bebas' : 'D');
      setSelectedVariant(normalizedVar);

      if (draft?.has_draft) {
        setTopic(draft.fields?.JUDUL || '');
        if (draft.sources) setSources(draft.sources);
        if (draft.fields?.DOSEN) setSelectedDosen(draft.fields.DOSEN);
        if (draft.fields?.MATA_KULIAH) setSelectedMatkul(draft.fields.MATA_KULIAH);
        if (draft.fields?.LOGO_PATH) setSelectedLogoPath(draft.fields.LOGO_PATH);
        if (draft.fields?.TEMPLATE_ID) setSelectedTemplateId(Number(draft.fields.TEMPLATE_ID));

        let activeOutline: string[] = [];
        if (draft.fields?.OUTLINE && Array.isArray(draft.fields.OUTLINE)) {
          activeOutline = draft.fields.OUTLINE.filter((x: string) => typeof x === 'string' && x.trim().length > 0);
        }
        if (activeOutline.length === 0 && draft.sections && draft.sections.length > 0) {
          activeOutline = draft.sections.map((s) => s.title).filter((t: string) => t && t.trim().length > 0);
        }
        if (activeOutline.length === 0 && v) {
          const matchedV = v.find((x) => x.code.toUpperCase() === normalizedVar.toUpperCase()) || v.find((x) => x.code.toUpperCase() === 'D');
          if (matchedV && matchedV.outline_titles && matchedV.outline_titles.length > 0) {
            activeOutline = matchedV.outline_titles;
          }
        }
        if (activeOutline.length > 0) {
          setOutline(activeOutline);
        } else if (v) {
          const varDefault = v.find((x) => x.code.toUpperCase() === 'D');
          if (varDefault && varDefault.outline_titles) setOutline(varDefault.outline_titles);
        }
      } else if (v) {
        const matched = v.find((x) => x.code.toUpperCase() === normalizedVar.toUpperCase()) || v.find((x) => x.code.toUpperCase() === 'D');
        if (matched && matched.outline_titles && matched.outline_titles.length > 0) {
          setOutline(matched.outline_titles);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleVariantChange = (code: string) => {
    setSelectedVariant(code);
    const matched = variants.find((x) => x.code.toUpperCase() === code.toUpperCase());
    if (matched && matched.outline_titles && matched.outline_titles.length > 0) {
      setOutline(matched.outline_titles);
      toast.info(`Outline dimuat ulang sesuai format ${matched.name}.`);
    } else if (code.toLowerCase() === 'bebas' && outline.filter((x) => x.trim()).length === 0) {
      setOutline([
        'BAB 1. PENDAHULUAN',
        'BAB 2. TINJAUAN PUSTAKA',
        'BAB 3. PEMBAHASAN',
        'BAB 4. PENUTUP',
      ]);
    }
  };

  const handleResetOutline = () => {
    const matched = variants.find((x) => x.code.toUpperCase() === selectedVariant.toUpperCase()) || variants.find((x) => x.code.toUpperCase() === 'D');
    if (matched && matched.outline_titles && matched.outline_titles.length > 0) {
      setOutline(matched.outline_titles);
      toast.success(`Outline di-reset ke struktur baku ${matched.name}.`);
    } else {
      setOutline([
        'BAB 1. PENDAHULUAN',
        'BAB 2. TINJAUAN PUSTAKA',
        'BAB 3. HASIL DAN PEMBAHASAN',
        'BAB 4. KESIMPULAN DAN SARAN',
      ]);
      toast.success('Outline di-reset ke struktur standar akademik.');
    }
  };

  const handleAddChapter = () => {
    const currentCount = outline.filter((x) => x.trim()).length;
    const newChapter = `BAB ${currentCount + 1}. JUDUL BAB BARU`;
    setOutline((prev) => [...prev.filter((x) => x.trim()), newChapter]);
    toast.success('Bab baru ditambahkan ke outline. Anda dapat langsung mengedit judulnya.');
  };

  // Add Sources Handlers
  const appendSourceRecords = (newRecords: SourceRecord[], successMsg?: string) => {
    if (newRecords.length === 0) return;
    const norm = (s?: string) => (s || '').replace(/\s+/g, ' ').trim().slice(0, 300).toLowerCase();
    const keyOf = (s: SourceRecord) => norm(s.text) || `${norm(s.title)}|${s.year || ''}`;

    let duplicateFound = false;
    const currentKeys = new Set(sources.map(keyOf));
    for (const rec of newRecords) {
      const k = keyOf(rec);
      if (k && currentKeys.has(k)) {
        duplicateFound = true;
      }
      if (k) currentKeys.add(k);
    }

    setSources((prev) => [...prev, ...newRecords]);

    if (duplicateFound) {
      toast.info(`⚠ Ada sumber dengan isi/judul serupa di daftar. Sumber ganda memperkuat bobot saat generate — hapus bila tidak disengaja.`);
    }
    if (successMsg) {
      toast.success(successMsg);
    }
  };

  const appendSourceRecord = (record: SourceRecord, successMsg: string) => {
    appendSourceRecords([record], successMsg);
  };

  const handleAddPdf = async () => {
    setLoadingSource(true);
    toast.info('Membuka dialog dan memproses berkas PDF...');
    try {
      const res = await api.pickPdfSource();
      if (res?.cancelled) {
        return;
      }
      if (res?.warning) {
        toast.info(res.warning);
      }
      const incoming: SourceRecord[] = res?.records && res.records.length > 0
        ? res.records
        : (res?.record ? [res.record] : []);

      if (incoming.length > 0) {
        const msg = incoming.length === 1
          ? `Sumber PDF "${incoming[0].title || 'Dokumen'}" berhasil ditambahkan.`
          : `${incoming.length} berkas PDF referensi berhasil ditambahkan sekaligus.`;
        appendSourceRecords(incoming, msg);
      }

      if (res?.errors && res.errors.length > 0) {
        toast.error(`Beberapa berkas gagal dibaca: ${res.errors.join('; ')}`);
      } else if (!incoming.length && res?.error) {
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

  const handleAddManual = async () => {
    if (!manualTextInput.trim()) return;
    setLoadingSource(true);
    try {
      const res = await api.addManualSource(manualTextInput.trim());
      if (res?.success && res.record) {
        appendSourceRecord(res.record, 'Sumber Manual berhasil ditambahkan.');
        setManualTextModal(false);
        setManualTextInput('');
      } else if (res?.error) {
        toast.error(res.error);
      }
    } finally {
      setLoadingSource(false);
    }
  };

  // Multi-Project Handlers
  const handleOpenProjectModal = async () => {
    setLoadingProjects(true);
    setProjectModalOpen(true);
    setSelectedDraftIds([]);
    try {
      const list = await api.listSavedDrafts();
      if (list) setSavedDrafts(list);
    } finally {
      setLoadingProjects(false);
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

      // Navigasi cerdas: Jika draf yang dibuka telah berisi naskah laporan, buka langsung di Tab Review!
      if (d.sections && Array.isArray(d.sections) && d.sections.length > 0 && onNavigateToReview) {
        onNavigateToReview();
      }
    } else {
      toast.error(res?.error || 'Gagal memuat proyek.');
    }
  };

  const handleNewBlankProject = async () => {
    await api.clearActiveDraft();
    setTopic('');
    setSources([]);
    setSelectedSourceIdx(null);
    const matchedVariant =
      variants.find((x) => x.code.toUpperCase() === selectedVariant.toUpperCase()) ||
      variants.find((x) => x.code.toUpperCase() === 'D');
    if (matchedVariant) setOutline(matchedVariant.outline_titles);
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
    const totalSourceChars = sources.reduce((acc, s) => acc + (s.text || '').length, 0);
    const quotableSources = sources.filter((s) => (s.text || '').length >= 250);
    if (quotableSources.length === 0) {
      toast.error(
        'Semua sumber hanya berisi metadata/abstrak tanpa teks yang bisa dikutip. ' +
        'Unggah PDF jurnal lengkap (atau tempel isinya lewat Manual) sebelum generate.'
      );
      return;
    }
    if (totalSourceChars < 4000) {
      toast.info(
        `Sumber terbatas (±${totalSourceChars.toLocaleString('id-ID')} karakter dari ${quotableSources.length} sumber berisi). Laporan berisiko terlalu tipis; tambahkan sumber lain untuk isi yang lebih kaya.`
      );
    }
    let effectiveOutline = outline.map((x) => x.trim()).filter(Boolean);
    if (effectiveOutline.length === 0) {
      const matched = variants.find((x) => x.code.toUpperCase() === selectedVariant.toUpperCase()) || variants.find((x) => x.code.toUpperCase() === 'D');
      if (matched && matched.outline_titles && matched.outline_titles.length > 0) {
        effectiveOutline = matched.outline_titles;
      } else {
        effectiveOutline = [
          'BAB 1. PENDAHULUAN',
          'BAB 2. TINJAUAN PUSTAKA',
          'BAB 3. HASIL DAN PEMBAHASAN',
          'BAB 4. KESIMPULAN DAN SARAN',
        ];
      }
      setOutline(effectiveOutline);
      toast.info('Outline otomatis disiapkan dari struktur baku.');
    }

    await api.saveActiveDraft({
      fields: {
        JUDUL: topic,
        DOSEN: selectedDosen,
        MATA_KULIAH: selectedMatkul,
        LOGO_PATH: selectedLogoPath,
        TEMPLATE_ID: selectedTemplateId,
        VARIANT: selectedVariant,
        OUTLINE: effectiveOutline,
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
      outline: effectiveOutline,
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
    <div className="flex-1 flex overflow-hidden report-root">
      {/* Live Generation Paper Canvas */}
      {isGenerating ? (
        <div className="flex-1 bg-slate-100/90 flex flex-col h-full overflow-hidden generation-studio">
          {/* Top Floating Glass Header */}
          <div className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-8 py-4 shrink-0 shadow-xs z-10 generation-header">
            <div className="max-w-4xl mx-auto flex items-center justify-between">
              <div className="flex items-center space-x-3.5 min-w-0">
                <div className="w-10 h-10 rounded-2xl ui-info-surface border flex items-center justify-center shadow-xs shrink-0">
                  <Sparkles className="w-5 h-5" aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-extrabold text-slate-800 tracking-tight truncate">
                      {topic || 'Menyusun Laporan Akademik...'}
                    </h3>
                    <span className="ui-status-info px-2 py-0.5 rounded-full text-[10px] font-extrabold border shrink-0">
                      Batch {genProgress.batch} dari {genProgress.total}
                    </span>
                  </div>
                  <div className="flex items-center space-x-3 text-xs text-slate-500 mt-1">
                    <span className="flex items-center gap-1 font-semibold text-slate-700">
                      <FileText className="w-3.5 h-3.5 text-brand-700" aria-hidden="true" />
                      <span>{recentSentences.length} Kalimat Disusun</span>
                    </span>
                    <span>•</span>
                      <span className="flex items-center gap-1 text-brand-700 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5 text-brand-600" />
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
                  className="px-4 py-2 ui-status-danger border rounded-xl text-xs font-bold flex items-center space-x-1.5 transition shadow-xs active:scale-95"
                >
                  <Square className="w-3.5 h-3.5 fill-current" aria-hidden="true" />
                  <span>Batalkan Generasi</span>
                </button>
              </div>
            </div>

            {/* Smooth progress bar */}
            <div className="max-w-4xl mx-auto mt-3 bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-brand-600 h-full transition-all duration-500 rounded-full"
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
            <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl border border-slate-200/90 p-8 md:p-12 paper-sheet font-serif min-h-[600px] flex flex-col justify-between generation-paper">
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
                      <Loader2 className="w-6 h-6 animate-spin text-brand-700" aria-hidden="true" />
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
                               isLatest ? 'animate-sentence-born ui-info-surface font-medium' : ''
                            }`}
                          >
                            <span>{s.text} </span>
                          </span>
                        );
                      })}
                      {/* Blinking typing cursor at end */}
                      <span className="inline-block w-1.5 h-4 bg-brand-600 animate-cursor-blink ml-1 align-middle rounded-xs" aria-hidden="true" />
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
        <div className="flex-1 flex overflow-hidden report-studio">
          {/* Left Column: Sumber Referensi */}
          <div className="w-96 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0 report-source-desk">
            <div className="p-5 flex-1 flex flex-col overflow-hidden source-desk-content">
              <div className="flex items-center justify-between mb-4 source-desk-heading">
                <div className="flex items-center space-x-2">
                  <BookOpen className="w-4 h-4 text-brand-600" />
                  <div>
                    <span className="studio-overline">01 / INPUT</span>
                    <h3 className="font-bold text-slate-800 text-sm">Sumber Referensi</h3>
                  </div>
                </div>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {sources.length}
                </span>
              </div>

              {/* Source action buttons */}
              <div className="grid grid-cols-2 gap-2 mb-4 source-action-grid">
                <button
                  onClick={handleAddPdf}
                  disabled={loadingSource}
                  className="p-3 rounded-xl border text-xs font-semibold flex items-center justify-center space-x-2 transition text-center ui-action-secondary shadow-sm hover:shadow"
                  title="Unggah berkas PDF naskah lengkap (native atau scan OCR)"
                >
                  <FilePlus className="w-4 h-4 text-brand-600 shrink-0" />
                  <span>PDF / OCR</span>
                </button>
                <button
                  onClick={() => setManualTextModal(true)}
                  disabled={loadingSource}
                  className="p-3 rounded-xl border text-xs font-semibold flex items-center justify-center space-x-2 transition text-center ui-action-secondary shadow-sm hover:shadow"
                  title="Tempel atau ketik teks naskah referensi langsung"
                >
                  <FileText className="w-4 h-4 text-brand-600 shrink-0" />
                  <span>Teks Manual</span>
                </button>
              </div>

              {/* Source List */}
              <div className="flex-1 overflow-y-auto space-y-2 pr-1 source-list">
                {loadingSource && (
                  <div className="p-3 mb-2 rounded-xl bg-brand-50 border border-brand-200 text-brand-800 text-xs flex items-center space-x-2 animate-pulse">
                    <Loader2 className="w-4 h-4 animate-spin text-brand-600 shrink-0" />
                    <span>Sedang memproses sumber & mengekstrak data...</span>
                  </div>
                )}
                {sources.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-xs px-4">
                    Belum ada sumber referensi.<br />
                    Gunakan tombol <span className="font-semibold text-slate-600">PDF/OCR</span> atau <span className="font-semibold text-slate-600">Teks Manual</span> di atas untuk menambahkan naskah lengkap artikel ilmiah Anda.
                  </div>
                ) : (
                  sources.map((s, idx) => {
                    const isSelected = selectedSourceIdx === idx;
                    return (
                      <article
                        key={idx}
                        className={`source-card p-3 rounded-xl border text-left transition ${
                          isSelected
                            ? 'source-card-is-selected shadow-sm'
                            : ''
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <button
                            type="button"
                            className="source-card-select flex-1 min-w-0 pr-2 text-left"
                            onClick={() => setSelectedSourceIdx(idx)}
                            aria-pressed={isSelected}
                            aria-label={`Pilih sumber ${idx + 1}: ${s.title || 'Tanpa Judul'}`}
                          >
                            <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                              <span className="text-[10px] font-bold uppercase px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                                {s.kind?.toUpperCase() || 'WEB'}
                              </span>
                              {(() => {
                                const info = describeSourceContent(s);
                                const toneCls =
                                  info.tone === 'ok'
                                    ? 'bg-brand-50 text-brand-700 border border-brand-200'
                                    : info.tone === 'danger'
                                      ? 'ui-status-danger border'
                                      : 'ui-status-warning border';
                                return (
                                  <span
                                    className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${toneCls}`}
                                    title={info.hint}
                                  >
                                    {info.label}
                                  </span>
                                );
                              })()}
                            </div>
                            <h4 className="text-xs font-bold text-slate-800 truncate">
                              {idx + 1}. {s.title || 'Tanpa Judul'}
                            </h4>
                            <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                              {s.authors?.map((a) => a.family).join(', ') || 'Tanpa Penulis'} ({s.year || 'n.d.'})
                            </p>
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteSource(idx);
                            }}
                            className="source-card-delete text-slate-400 p-2"
                            aria-label={`Hapus sumber ${idx + 1}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </article>
                    );
                  })
                )}
              </div>
            </div>

            {/* Selected source metadata editor drawer */}
            {selectedSourceIdx !== null && sources[selectedSourceIdx] && (
              <div className="p-4 border-t border-slate-200 bg-slate-50 text-xs space-y-2 source-metadata">
                <div className="flex items-center justify-between font-bold text-slate-700">
                  <span>Koreksi Metadata Sumber #{selectedSourceIdx + 1}</span>
                  <button onClick={() => setSelectedSourceIdx(null)} className="text-slate-400 hover:text-slate-600">✕</button>
                </div>
                <div>
                  <label htmlFor="meta-judul" className="text-[10px] text-slate-500 font-semibold uppercase">Judul</label>
                  <input
                    id="meta-judul"
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
                <div>
                  <label htmlFor="meta-penulis" className="text-[10px] text-slate-500 font-semibold uppercase">
                    Penulis (pisahkan dengan ; bila lebih dari satu)
                  </label>
                  <input
                    type="text"
                    value={(sources[selectedSourceIdx].authors || [])
                      .map((a) => [a.family, a.given].filter(Boolean).join(', '))
                      .join('; ')}
                    onChange={(e) => {
                      // Aplikasi tidak menebak pemisahan nama penulis: mahasiswa
                      // menuliskannya eksplisit, dipisah ";" (F8).
                      const updated = [...sources];
                      updated[selectedSourceIdx].authors = e.target.value
                        .split(';')
                        .map((part) => part.trim())
                        .filter(Boolean)
                        .map((part) => {
                          const comma = part.indexOf(',');
                          return comma > 0
                            ? { family: part.slice(0, comma).trim(), given: part.slice(comma + 1).trim(), is_org: false, abbrev: '' }
                            : { family: part, given: '', is_org: false, abbrev: '' };
                        });
                      setSources(updated);
                    }}
                    placeholder="Contoh: Santoso, A; Wijaya, B"
                    id="meta-penulis"
                    className="w-full px-2 py-1 bg-white border border-slate-200 rounded text-xs"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label htmlFor="meta-tahun" className="text-[10px] text-slate-500 font-semibold uppercase">Tahun</label>
                    <input
                      id="meta-tahun"
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
                    <label htmlFor="meta-publikasi" className="text-[10px] text-slate-500 font-semibold uppercase">Publikasi / Jurnal</label>
                    <input
                      id="meta-publikasi"
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
          <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto space-y-6 report-composer">
            {/* PROPORTIONAL HATSUNE MIKU HERO BANNER */}
            <div className="rounded-[24px] px-7 py-5 relative overflow-hidden shadow-md flex items-center justify-between min-h-[145px]" style={{ background: 'linear-gradient(135deg, #5AD5CD 0%, #39C5BB 50%, #209C93 100%)' }}>
              {/* Left Text Content */}
              <div className="relative z-10 max-w-lg text-slate-950 space-y-1.5">
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-0.5 rounded-full bg-white/90 text-slate-900 font-extrabold text-xs font-mono tracking-wider shadow-2xs">
                    初音ミク × GENERATOR LAPORAN
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-[#FF5B88] text-white font-extrabold text-xs shadow-2xs">
                    APA 7th
                  </span>
                </div>
                <h1 className="text-xl font-black text-slate-950 tracking-tight leading-tight">
                  Susun Laporan Ilmiah Berbasis Jurnal
                </h1>
                <p className="text-xs text-slate-950/90 font-medium leading-relaxed">
                  Sintesis literatur otomatis dengan verifikasi kutipan APA 7 dan keluaran DOCX rapi sesuai format baku Dikti.
                </p>
                <div className="flex items-center space-x-2 pt-0.5 text-xs font-mono font-extrabold">
                  <span className="px-3 py-0.5 rounded-full bg-white text-slate-900 shadow-2xs">VARIAN {selectedVariant.toUpperCase()} (SINTESIS)</span>
                  <span className="px-3 py-0.5 rounded-full bg-black/20 text-white backdrop-blur-xs">{sources.length} SUMBER • {outline.length} BAB</span>
                </div>
              </div>

              {/* Right Character Graphic (Transparent Miku, 0 grey hair halos) */}
              <div className="relative z-10 w-[240px] h-[160px] -mb-5 flex items-end justify-end shrink-0 pointer-events-none">
                <img
                  src="/assets/miku_hero.png"
                  alt="Hatsune Miku"
                  className="h-full object-contain filter drop-shadow-md"
                  onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                />
              </div>
            </div>

            {/* Student Identity Summary Pill (Links to Tab 03 Profil & Data) */}
            <div className="p-3.5 rounded-2xl bg-[#E4F9F8]/60 border border-teal-200/70 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-full bg-[#39C5BB] text-white flex items-center justify-center font-bold text-base shrink-0 shadow-xs">
                  🎓
                </div>
                <div className="text-xs">
                  <span className="text-slate-500 block font-mono">IDENTITAS PENULIS LAPORAN:</span>
                  <span className="font-extrabold text-slate-900">
                    Data Mahasiswa & Dosen Tersinkronisasi
                  </span>
                  <span className="text-teal-800 font-mono"> (APA 7 Ready)</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  window.dispatchEvent(new CustomEvent('switch-tab-request', { detail: { tab: 'data' } }));
                }}
                className="px-3.5 py-1.5 rounded-full text-xs font-bold bg-white text-[#219E95] border border-teal-200 hover:bg-[#E4F9F8] transition shadow-2xs shrink-0 cursor-pointer"
              >
                ✏️ Kelola di Tab Data
              </button>
            </div>

            <div className="flex items-center justify-between report-form-header">
              <div>
                <span className="studio-overline">02 / BRIEF</span>
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
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-4 report-panel report-brief">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="brief-judul" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                    Judul Laporan Akademik
                  </label>
                  <button
                    type="button"
                    onClick={handleAutoGenerateTitle}
                    disabled={generatingTitle || sources.length === 0}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition border ${
                      sources.length === 0
                        ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed opacity-70'
                        : 'ui-action-ai shadow-sm active:scale-95'
                    }`}
                    title={
                      sources.length === 0
                        ? 'Tambahkan sumber jurnal di panel kiri untuk merumuskan judul otomatis'
                        : 'Rumuskan rekomendasi judul laporan akademik otomatis berdasarkan jurnal referensi'
                    }
                  >
                    {generatingTitle ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Menyusun Judul AI...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
                        <span>Saran Judul dari Jurnal (AI)</span>
                      </>
                    )}
                  </button>
                </div>
                <input
                  id="brief-judul"
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
                    <label htmlFor="brief-template" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                      Template Word (.docx)
                    </label>
                    {templates.length > 0 && selectedTemplateId && (
                      <span className="text-[10px] font-semibold text-brand-700 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-brand-600" />
                        <span>Format Terverifikasi</span>
                      </span>
                    )}
                  </div>
                  <select
                    id="brief-template"
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
                          <span className="ui-status-info px-2 py-0.5 rounded border font-semibold text-[10px]">
                            APA 7 Ready
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                <div>
                  <label htmlFor="brief-varian" className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Varian Format Laporan
                  </label>
                  <select
                    id="brief-varian"
                    value={variants.find((x) => x.code.toUpperCase() === selectedVariant.toUpperCase())?.code || selectedVariant}
                    onChange={(e) => handleVariantChange(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 font-semibold text-brand-800"
                  >
                    {variants.map((v) => {
                      const c = v.code.toUpperCase();
                      const label =
                         c === 'B' ? 'Varian B (Baku): Makalah Kuliah Standar Dikti (4 Bab)' :
                         c === 'A' ? 'Varian A: Makalah Tinjauan / Komparatif (Multi-Topik)' :
                         c === 'C' ? 'Varian C: Laporan Praktikum Laboratorium' :
                         c === 'D' ? 'Varian D: Tinjauan Pustaka (Sintesis Tanpa Bab Hasil)' :
                         'Format Bebas: Outline Kustom Mandiri';
                      return (
                        <option key={v.code} value={v.code}>
                          {label}
                        </option>
                      );
                    })}
                  </select>
                </div>
              </div>

              {/* Dosen & Matkul Selection */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div>
                  <label htmlFor="brief-dosen" className="block text-xs font-semibold text-slate-600 mb-1">Dosen Pengampu</label>
                  <select
                    id="brief-dosen"
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
                  <label htmlFor="brief-matkul" className="block text-xs font-semibold text-slate-600 mb-1">Mata Kuliah</label>
                  <select
                    id="brief-matkul"
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
                  <label htmlFor="brief-logo" className="block text-xs font-semibold text-slate-600 mb-1">Logo Kampus</label>
                  <div className="flex items-center gap-2">
                    {(() => {
                      const selectedLogo = logoList.find((l) => l.path === selectedLogoPath);
                      if (selectedLogo?.data_url) {
                        return (
                          <div className="w-8 h-8 rounded-lg border border-slate-200 bg-white p-1 flex items-center justify-center shrink-0 shadow-xs" title={`Logo: ${selectedLogo.nama}`}>
                            <img src={selectedLogo.data_url} alt={selectedLogo.nama} className="max-w-full max-h-full object-contain" />
                          </div>
                        );
                      }
                      return null;
                    })()}
                    <select
                      id="brief-logo"
                      value={selectedLogoPath}
                      onChange={(e) => setSelectedLogoPath(e.target.value)}
                      className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                    >
                      <option value="">-- Pilih Logo --</option>
                      {logoList.map((l) => (
                        <option key={l.id} value={l.path}>
                          {l.nama} {!l.exists && '(Berkas Tidak Ditemukan)'}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* Outline Box */}
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-3 report-panel report-outline">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-brand-600" />
                    <h3 className="text-sm font-bold text-slate-800">Struktur Bab & Outline Laporan</h3>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Daftar bab yang akan ditulis AI (satu bab per baris). Anda bebas mengedit judul, menambah bab baru, atau memuat ulang format baku.
                  </p>
                </div>
                <div className="flex items-center flex-wrap gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={handleAddChapter}
                    className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center space-x-1 border border-slate-200 transition"
                    title="Tambah bab baru ke akhir outline"
                  >
                    <Plus className="w-3.5 h-3.5 text-slate-600" />
                    <span>Tambah Bab</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleResetOutline}
                    className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center space-x-1 border border-slate-200 transition"
                    title="Muat ulang outline baku sesuai varian format terpilih"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
                    <span>Muat Ulang Baku</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleSuggestOutline}
                    disabled={suggestingOutline || sources.length === 0}
                    className="px-2.5 py-1.5 bg-brand-50 hover:bg-brand-100 text-brand-700 rounded-lg text-xs font-semibold flex items-center space-x-1 border border-brand-200 transition disabled:opacity-50"
                    title="Gunakan AI untuk merumuskan usulan bab dari topik dan naskah jurnal"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-brand-600" />
                    <span>{suggestingOutline ? 'Menyusun...' : 'Usulkan outline'}</span>
                  </button>
                </div>
              </div>

              <textarea
                value={outline.join('\n')}
                onChange={(e) => setOutline(e.target.value.split('\n'))}
                placeholder={"BAB 1. PENDAHULUAN\nBAB 2. TINJAUAN PUSTAKA\nBAB 3. HASIL DAN PEMBAHASAN\nBAB 4. KESIMPULAN DAN SARAN"}
                rows={7}
                className="w-full p-3.5 rounded-xl text-xs font-mono border bg-slate-50 border-slate-200 text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition leading-relaxed"
              />
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>{outline.filter((x) => x.trim()).length} bab terdaftar</span>
                <span>Tip: tulis satu bab per baris, contoh: <code>BAB 1. PENDAHULUAN</code></span>
              </div>
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

      {/* Manual Text Modal */}
      {manualTextModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50" role="presentation" onClick={() => setManualTextModal(false)}>
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-slate-200" role="dialog" aria-modal="true" aria-labelledby="manual-text-dialog-title" onClick={(event) => event.stopPropagation()}>
            <h3 id="manual-text-dialog-title" className="text-base font-bold text-slate-800 mb-2">Tempel Teks Sumber Manual</h3>
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

      {/* Multi-Project & Draft Manager Modal */}
      <DraftManagerModal
        isOpen={projectModalOpen}
        onClose={() => setProjectModalOpen(false)}
        onSelectDraft={handleLoadProject}
        onNewBlankProject={handleNewBlankProject}
        canSaveCurrent={true}
        onSaveNamedProject={async (name: string) => {
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
          const res = await api.saveNamedDraft(name, state);
          if (res?.success) {
            toast.success(`Proyek '${name}' berhasil disimpan!`);
            return true;
          } else {
            toast.error(res?.error || 'Gagal menyimpan proyek.');
            return false;
          }
        }}
      />

    </div>
  );
};
