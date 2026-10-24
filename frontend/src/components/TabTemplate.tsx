import React, { useState, useEffect } from 'react';
import { 
  FileCode2, 
  UploadCloud, 
  Trash2, 
  CheckCircle2, 
  AlertTriangle, 
  Copy, 
  Check, 
  FileText,
  Search,
  Sparkles,
  FolderOpen,
  ExternalLink,
  Eye,
  BookOpen,
  Sliders,
  ZoomIn,
  ZoomOut,
  Award,
  Layers,
  GraduationCap,
  Tag,
  ShieldCheck,
  CheckCheck
} from 'lucide-react';
import { api, TemplateItem } from '../lib/api';
import { toast } from '../lib/toast';

interface RequiredTagDef {
  tag: string;
  name: string;
  friendlyName: string;
  desc: string;
  special: boolean;
  category: 'identitas' | 'media' | 'struktur';
  categoryLabel: string;
  location: string;
  sampleValue: string;
  ruleExplanation?: string;
}

const REQUIRED_TAGS_DEF: RequiredTagDef[] = [
  // 1. Identitas & Metadata Laporan
  { 
    tag: '{{JUDUL}}', 
    name: 'JUDUL', 
    friendlyName: 'Judul Lengkap Laporan / Skripsi',
    desc: 'Judul karya ilmiah yang dicetak pada halaman sampul depan (14–16 pt Bold Kapital)', 
    special: false,
    category: 'identitas',
    categoryLabel: 'Identitas & Metadata',
    location: 'Halaman Sampul (Center, 14–16 pt Bold)',
    sampleValue: 'ANALISIS DAN PERANCANGAN SISTEM INFORMASI AKADEMIK...'
  },
  { 
    tag: '{{NAMA}}', 
    name: 'NAMA', 
    friendlyName: 'Nama Lengkap Mahasiswa',
    desc: 'Nama lengkap mahasiswa penyusun laporan karya ilmiah', 
    special: false,
    category: 'identitas',
    categoryLabel: 'Identitas & Metadata',
    location: 'Halaman Sampul (Blok Disusun Oleh)',
    sampleValue: 'Budi Santoso, S.Kom.'
  },
  { 
    tag: '{{NIM}}', 
    name: 'NIM', 
    friendlyName: 'Nomor Induk Mahasiswa (NIM)',
    desc: 'Nomor induk mahasiswa resmi dari perguruan tinggi', 
    special: false,
    category: 'identitas',
    categoryLabel: 'Identitas & Metadata',
    location: 'Halaman Sampul (Di bawah Nama Mahasiswa)',
    sampleValue: '2024101010'
  },
  { 
    tag: '{{DOSEN}}', 
    name: 'DOSEN', 
    friendlyName: 'Dosen Pembimbing & Gelar',
    desc: 'Nama lengkap beserta gelar akademik dosen pembimbing', 
    special: false,
    category: 'identitas',
    categoryLabel: 'Identitas & Metadata',
    location: 'Halaman Sampul (Blok Dosen Pembimbing)',
    sampleValue: 'Dr. Ir. Dosen Pembimbing, M.Kom.'
  },
  { 
    tag: '{{MATA_KULIAH}}', 
    name: 'MATA_KULIAH', 
    friendlyName: 'Mata Kuliah / Bidang Minat',
    desc: 'Nama mata kuliah atau bidang peminatan tugas akhir', 
    special: false,
    category: 'identitas',
    categoryLabel: 'Identitas & Metadata',
    location: 'Halaman Sampul (Di bawah Dosen Pembimbing)',
    sampleValue: 'Sistem Rekayasa Perangkat Lunak'
  },
  { 
    tag: '{{TANGGAL}}', 
    name: 'TANGGAL', 
    friendlyName: 'Tanggal Cetak / Tahun Laporan',
    desc: 'Tanggal penerbitan dokumen atau tahun penyusunan (mis: 22 Oktober 2026)', 
    special: false,
    category: 'identitas',
    categoryLabel: 'Identitas & Metadata',
    location: 'Halaman Sampul (Bagian Paling Bawah)',
    sampleValue: '22 Oktober 2026'
  },

  // 2. Elemen Media & Grafis
  { 
    tag: '{{LOGO}}', 
    name: 'LOGO', 
    friendlyName: 'Logo Resmi Institusi (5x5 cm)',
    desc: 'Gambar lambang kampus yang otomatis diskalakan proporsional 5x5 cm', 
    special: true,
    category: 'media',
    categoryLabel: 'Aset Media & Logo',
    location: 'Halaman Sampul (Center, antara Judul & Identitas)',
    sampleValue: '[Gambar Logo Universitas 5x5 cm]',
    ruleExplanation: 'Wajib berada sendiri di satu baris paragraf (Center) tanpa teks pengantar lain.'
  },

  // 3. Batang Tubuh & Struktur Ilmiah
  { 
    tag: '{{DAFTAR_ISI}}', 
    name: 'DAFTAR_ISI', 
    friendlyName: 'Daftar Isi Otomatis Word (TOC)',
    desc: 'Field dinamis Microsoft Word yang menghasilkan daftar isi dengan dotted leader dan nomor halaman', 
    special: true,
    category: 'struktur',
    categoryLabel: 'Struktur Laporan',
    location: 'Halaman 2 (Tepat di bawah judul bab DAFTAR ISI)',
    sampleValue: '[Field Code TOC Word Otomatis]',
    ruleExplanation: 'Wajib berdiri sendiri di satu paragraf utuh agar kode field TOC Word berfungsi normal.'
  },
  { 
    tag: '{{ISI_LAPORAN}}', 
    name: 'ISI_LAPORAN', 
    friendlyName: 'Batang Tubuh Laporan (Bab I - V)',
    desc: 'Tempat disuntikkannya seluruh bab naskah hasil AI lengkap dengan heading berlevel dan sitasi', 
    special: true,
    category: 'struktur',
    categoryLabel: 'Struktur Laporan',
    location: 'Halaman 3 (Halaman baru setelah Daftar Isi)',
    sampleValue: '[BAB I s/d BAB V + Heading & Sitasi Lengkap]',
    ruleExplanation: 'Wajib berdiri sendiri di satu paragraf utuh untuk penempatan seluruh batang tubuh laporan.'
  },
  { 
    tag: '{{DAFTAR_PUSTAKA}}', 
    name: 'DAFTAR_PUSTAKA', 
    friendlyName: 'Daftar Pustaka APA 7th Edition',
    desc: 'Daftar referensi berurutan abjad dengan format hanging indent 1.27 cm dan tautan DOI aktif', 
    special: true,
    category: 'struktur',
    categoryLabel: 'Struktur Laporan',
    location: 'Halaman Terakhir (Di bawah judul DAFTAR PUSTAKA)',
    sampleValue: '[Daftar Pustaka APA 7 + Hanging Indent]',
    ruleExplanation: 'Wajib berdiri sendiri di satu paragraf utuh agar format hanging indent tidak rusak.'
  },
];

interface TabTemplateProps {
  isActive?: boolean;
}

export const TabTemplate: React.FC<TabTemplateProps> = ({ isActive = false }) => {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateItem | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedTag, setCopiedTag] = useState<string | null>(null);
  const [copiedPath, setCopiedPath] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'specs' | 'tags'>('preview');
  const [previewPage, setPreviewPage] = useState<'cover' | 'toc' | 'body' | 'references'>('cover');
  const [showMarginGuide, setShowMarginGuide] = useState(true);
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // Diagnostic Tags Filter State
  const [tagStatusFilter, setTagStatusFilter] = useState<'all' | 'valid' | 'issues'>('all');
  const [tagCategoryFilter, setTagCategoryFilter] = useState<'all' | 'identitas' | 'media' | 'struktur'>('all');
  const [tagSearchQuery, setTagSearchQuery] = useState('');

  // Customization Modal State
  const [showCustomizeModal, setShowCustomizeModal] = useState(false);
  const [customFont, setCustomFont] = useState('Times New Roman');
  const [customMargin, setCustomMargin] = useState('4433');
  const [customSpacing, setCustomSpacing] = useState(1.5);

  useEffect(() => {
    loadTemplates();
  }, []);

  useEffect(() => {
    if (isActive) {
      loadTemplates();
    }
  }, [isActive]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const list = await api.listTemplates();
      if (list) {
        setTemplates(list);
        if (list.length > 0) {
          if (!selectedTemplate || !list.some((t) => t.id === selectedTemplate.id)) {
            const std = list.find((t) => t.is_default || t.nama.includes('Standar'));
            setSelectedTemplate(std || list[0]);
          } else {
            const updated = list.find((t) => t.id === selectedTemplate.id);
            if (updated) setSelectedTemplate(updated);
          }
        } else {
          setSelectedTemplate(null);
        }
      }
    } catch (e) {
      console.error(e);
      toast.error('Gagal memuat daftar template.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    setLoading(true);
    try {
      const res = await api.uploadTemplate();
      if (res?.success) {
        toast.success('Template berhasil diunggah dan diverifikasi!');
        await loadTemplates();
      } else if (res?.cancelled) {
        // user cancelled
      } else {
        toast.error('Gagal mengunggah template.');
      }
    } catch (e: any) {
      toast.error(e?.message || 'Gagal memproses template Word.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDefault = async () => {
    setLoading(true);
    try {
      const res = await api.createDefaultTemplate({
        font_name: customFont,
        margin_preset: customMargin,
        line_spacing: customSpacing
      });
      if (res?.success) {
        toast.success('Template Standar Akademik berhasil dibuat dan siap digunakan!');
        setShowCustomizeModal(false);
        await loadTemplates();
      } else {
        toast.error(res?.error || 'Gagal membuat template standar.');
      }
    } catch (e: any) {
      toast.error(e?.message || 'Terjadi kesalahan sistem.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenInWord = async (templateId: number) => {
    try {
      const res = await api.openTemplate(templateId);
      if (res?.success) {
        toast.success('Membuka file template di Microsoft Word...');
      } else {
        toast.error(res?.error || 'Gagal membuka di Word.');
      }
    } catch (e: any) {
      toast.error('Gagal meluncurkan Microsoft Word.');
    }
  };

  const handleOpenFolder = async () => {
    try {
      const res = await api.openTemplatesFolder();
      if (res?.success) {
        toast.info('Membuka folder template di File Explorer...');
      } else {
        toast.error(res?.error || 'Gagal membuka folder.');
      }
    } catch (e) {
      toast.error('Gagal membuka folder template.');
    }
  };

  const handleDelete = async (id: number) => {
    setLoading(true);
    try {
      await api.deleteTemplate(id);
      setConfirmDeleteId(null);
      toast.success('Template berhasil dihapus.');
      await loadTemplates();
    } catch (e) {
      toast.error('Gagal menghapus template.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedTag(text);
    toast.success(`Jangkar Word ${text} disalin ke clipboard!`);
    setTimeout(() => setCopiedTag(null), 1500);
  };

  const copyAllTagsToClipboard = () => {
    const allText = REQUIRED_TAGS_DEF.map((t) => `${t.tag} -> ${t.friendlyName} (${t.location})`).join('\n');
    navigator.clipboard.writeText(allText);
    toast.success('Daftar seluruh 10 jangkar Word berhasil disalin!');
  };

  const copyPathToClipboard = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedPath(true);
    toast.info('Path berkas berhasil disalin!');
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const filteredTemplates = templates.filter((t) =>
    t.nama.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.deskripsi?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const readyCount = templates.filter((t) => t.status === 'lengkap').length;
  const invalidCount = templates.length - readyCount;

  // Helper for tag status
  const getTagStatus = (tagDef: RequiredTagDef) => {
    if (!selectedTemplate) return { status: 'missing', label: 'Belum Terpasang' };
    const missing = selectedTemplate.missing || [];
    const notStandalone = selectedTemplate.not_standalone || [];
    const placeholders = selectedTemplate.placeholders || [];

    const isMissing = missing.includes(tagDef.tag) || !placeholders.includes(tagDef.name);
    const isNotStandalone = notStandalone.includes(tagDef.tag);

    if (isMissing) {
      return { status: 'missing', label: 'Belum Terpasang' };
    }
    if (isNotStandalone) {
      return { status: 'not_standalone', label: 'Tercampur Teks Lain' };
    }
    return { status: 'valid', label: 'Terdeteksi & Valid' };
  };

  const tagStatuses = REQUIRED_TAGS_DEF.map((t) => ({ def: t, ...getTagStatus(t) }));
  const validCount = tagStatuses.filter((s) => s.status === 'valid').length;
  const issuesCount = 10 - validCount;
  const healthPercent = Math.round((validCount / 10) * 100);

  const filteredDiagnosticTags = tagStatuses.filter(({ def, status }) => {
    if (tagStatusFilter === 'valid' && status !== 'valid') return false;
    if (tagStatusFilter === 'issues' && status === 'valid') return false;
    if (tagCategoryFilter !== 'all' && def.category !== tagCategoryFilter) return false;
    if (tagSearchQuery.trim()) {
      const q = tagSearchQuery.toLowerCase();
      const match = def.tag.toLowerCase().includes(q) || 
                    def.friendlyName.toLowerCase().includes(q) || 
                    def.desc.toLowerCase().includes(q) || 
                    def.location.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 max-w-7xl mx-auto space-y-6 text-slate-800 template-studio">
      {/* Educational SaaS Banner: Mengapa Ada {{ }} */}
      <div className="p-5 rounded-2xl bg-brand-600 text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4 template-intro">
        <div className="flex items-start space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-white/15 text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5 border border-white/20">
            <Sparkles className="w-5 h-5 text-brand-100" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold tracking-tight text-white">
                Mengapa Template Word Menggunakan Tanda Kurung {"{{ ... }}"}?
              </h3>
                <span className="text-[10px] font-bold px-2 py-0.2 rounded-full bg-white/20 text-brand-100 border border-white/30">
                Jangkar Otomatis AI
              </span>
            </div>
            <p className="text-xs text-brand-50 leading-relaxed max-w-3xl">
              Tanda kurung ganda <code className="font-mono px-1.5 py-0.5 rounded bg-brand-900/60 text-white font-bold border border-brand-400/40">{"{{ ... }}"}</code> adalah <strong>"Jangkar Otomatis"</strong> di Microsoft Word. Tanda ini memberi tahu sistem lokasi persis untuk menyuntikkan judul, nama, logo, bab AI, dan daftar pustaka APA 7 tanpa merusak margin 4-4-3-3 cm atau tata letak dokumen Word yang sudah Anda atur.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
          <button
            onClick={copyAllTagsToClipboard}
            className="px-4 py-2 bg-white/15 hover:bg-white/25 text-white border border-white/30 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition shadow-sm"
          >
              <Copy className="w-3.5 h-3.5 text-brand-100" />
            <span>Salin Seluruh Jangkar</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Left Template List, Right Studio Workstation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 template-workbench">
        {/* Left Column (4 Cols): Template List */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-4 flex flex-col min-h-[600px]">
          <div className="flex items-center justify-between mb-3 px-1">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span>Daftar Template Dokumen</span>
                <span className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-brand-50 text-brand-700 border border-brand-200">
                {templates.length}
              </span>
            </h3>

            <div className="flex items-center space-x-1">
              <button
                onClick={handleOpenFolder}
                className="p-1.5 hover:bg-slate-100 text-slate-500 hover:text-slate-800 rounded-lg transition"
                title="Buka Folder Template"
              >
                <FolderOpen className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowCustomizeModal(true)}
                 className="p-1.5 hover:bg-brand-50 text-slate-500 hover:text-brand-600 rounded-lg transition"
                title="Kustomisasi Format Standar"
              >
                <Sliders className="w-4 h-4" />
              </button>
              <button
                onClick={handleUpload}
                 className="p-1.5 hover:bg-brand-50 text-slate-500 hover:text-brand-600 rounded-lg transition"
                title="Unggah Berkas .docx"
              >
                <UploadCloud className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div className="relative mb-3">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari template..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {templates.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-200 rounded-xl">
              <FileCode2 className="w-10 h-10 text-slate-300 mb-2" />
              <h4 className="text-xs font-bold text-slate-700">Belum Ada Template</h4>
              <p className="text-[11px] text-slate-400 mt-1 max-w-xs mb-3">
                Buat template standar resmi dengan sampul, logo, dan TOC lengkap secara otomatis.
              </p>
              <button
                onClick={handleCreateDefault}
                className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 shadow-md shadow-brand-600/20"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Buat Template Standar</span>
              </button>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[640px]">
              {filteredTemplates.map((tpl) => {
                const isSelected = selectedTemplate?.id === tpl.id;
                const isLengkap = tpl.status === 'lengkap';
                const isDefault = tpl.is_default || tpl.nama.includes('Standar');

                return (
                  <button
                    key={tpl.id}
                    type="button"
                    onClick={() => setSelectedTemplate(tpl)}
                    aria-pressed={isSelected}
                    className={`w-full p-3 rounded-xl border text-left transition-all duration-150 relative ${
                      isSelected
                      ? 'border-brand-500 bg-brand-50/70 shadow-sm ring-1 ring-brand-500/30'
                        : 'border-slate-200/80 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start space-x-2.5 min-w-0 flex-1">
                        <div className={`p-2 rounded-lg mt-0.5 shrink-0 ${
                          isDefault 
                            ? 'bg-brand-600 text-white shadow-sm'
                            : isSelected ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-500'
                        }`}>
                          {isDefault ? <GraduationCap className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <h4 className="text-xs font-bold text-slate-800 truncate">{tpl.nama}</h4>
                            {isDefault && (
                              <span className="ui-status-info text-[9px] font-bold px-1.5 py-0.2 rounded border shrink-0">
                                Resmi
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 truncate mt-0.5">
                            {tpl.deskripsi || tpl.path}
                          </p>

                          <div className="flex items-center gap-1.5 mt-2">
                            <span className="text-[10px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                              {tpl.spec?.margin || '4-4-3-3 cm'}
                            </span>
                            <span className="text-[10px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                              {tpl.spec?.font || 'Times New Roman'}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="shrink-0 flex flex-col items-end">
                        {isLengkap ? (
                          <span className="ui-status-success text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                            <span>Siap</span>
                          </span>
                        ) : (
                          <span className="ui-status-warning text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 flex items-center space-x-1">
                            <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                            <span>Kurang</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column (8 Cols): Workstation Studio */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 flex flex-col min-h-[600px]">
          {selectedTemplate ? (
            <div className="space-y-5">
              {/* Template Top Header Details */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-extrabold text-slate-800 truncate">{selectedTemplate.nama}</h3>
                    {selectedTemplate.status === 'lengkap' ? (
                      <span className="ui-status-success text-[10px] font-bold px-2.5 py-0.5 rounded-full border flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                        <span>Format Valid & Siap Ekspor</span>
                      </span>
                    ) : (
                      <span className="ui-status-warning text-[10px] font-bold px-2.5 py-0.5 rounded-full border flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                        <span>Perlu Melengkapi Penanda</span>
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                    <span className="truncate max-w-md">{selectedTemplate.path}</span>
                    <button
                      type="button"
                      onClick={() => copyPathToClipboard(selectedTemplate.path)}
                        className="text-brand-700 hover:text-brand-800 underline text-[11px] shrink-0"
                    >
                      {copiedPath ? 'Tersalin!' : 'Salin Path'}
                    </button>
                  </div>
                </div>

                {/* Direct Action Buttons for Selected Template */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleOpenInWord(selectedTemplate.id)}
                      className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-bold flex items-center space-x-1.5 transition shadow-md shadow-brand-600/20"
                    title="Buka dan sunting template langsung di aplikasi Microsoft Word lokal"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Buka di MS Word</span>
                  </button>

                  {/* Delete Button */}
                  {confirmDeleteId === selectedTemplate.id ? (
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleDelete(selectedTemplate.id)}
                        className="px-2.5 py-1.5 bg-rose-600 text-white rounded-xl text-xs font-semibold hover:bg-rose-700"
                      >
                        Hapus
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="px-2.5 py-1.5 bg-slate-100 text-slate-600 rounded-xl text-xs hover:bg-slate-200"
                      >
                        Batal
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmDeleteId(selectedTemplate.id)}
                      className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition border border-slate-200"
                      title="Hapus template ini"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Workstation Mode Switcher Tabs */}
              <div className="flex items-center justify-between border-b border-slate-200">
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => setActiveTab('preview')}
                    className={`px-4 py-2.5 text-xs font-bold flex items-center space-x-2 border-b-2 transition ${
                      activeTab === 'preview'
                        ? 'border-blue-600 text-blue-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>Pratinjau Lembar A4 (Live Visual)</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('specs')}
                    className={`px-4 py-2.5 text-xs font-bold flex items-center space-x-2 border-b-2 transition ${
                      activeTab === 'specs'
                        ? 'border-blue-600 text-blue-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Spesifikasi Format Baku</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('tags')}
                    className={`px-4 py-2.5 text-xs font-bold flex items-center space-x-2 border-b-2 transition ${
                      activeTab === 'tags'
                        ? 'border-blue-600 text-blue-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Diagnostik & Jangkar Word</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      selectedTemplate.status === 'lengkap' 
                        ? 'bg-emerald-100 text-emerald-800' 
                        : 'bg-amber-100 text-amber-800'
                    }`}>
                      {validCount}/10 Valid
                    </span>
                  </button>
                </div>

                {activeTab === 'preview' && (
                  <div className="hidden sm:flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500 pb-1">
                    <label className="flex items-center space-x-1.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={showMarginGuide}
                        onChange={(e) => setShowMarginGuide(e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500 text-xs"
                      />
                      <span className="text-[11px] font-medium text-slate-600">Garis Margin 4-4-3-3 cm</span>
                    </label>

                    <div className="flex items-center space-x-1 pl-2 border-l border-slate-200">
                      <button
                        onClick={() => setZoomLevel(Math.max(80, zoomLevel - 10))}
                        className="p-1 hover:bg-slate-100 rounded text-slate-500"
                        title="Perkecil"
                      >
                        <ZoomOut className="w-3.5 h-3.5" />
                      </button>
                      <span className="text-[11px] font-mono text-slate-600 w-8 text-center">{zoomLevel}%</span>
                      <button
                        onClick={() => setZoomLevel(Math.min(125, zoomLevel + 10))}
                        className="p-1 hover:bg-slate-100 rounded text-slate-500"
                        title="Perbesar"
                      >
                        <ZoomIn className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* TAB 1: VISUAL A4 PREVIEW CANVAS */}
              {activeTab === 'preview' && (
                <div className="space-y-4">
                  {/* Page Switcher Toolbar */}
                  <div className="flex items-center justify-between bg-slate-50 p-2 rounded-xl border border-slate-200/80">
                    <div className="flex items-center space-x-1.5 overflow-x-auto">
                      <button
                        onClick={() => setPreviewPage('cover')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                          previewPage === 'cover'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        1. Halaman Sampul (Cover)
                      </button>

                      <button
                        onClick={() => setPreviewPage('toc')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                          previewPage === 'toc'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        2. Daftar Isi Otomatis (TOC)
                      </button>

                      <button
                        onClick={() => setPreviewPage('body')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                          previewPage === 'body'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        3. Batang Tubuh Laporan (Bab I - V)
                      </button>

                      <button
                        onClick={() => setPreviewPage('references')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                          previewPage === 'references'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        4. Daftar Pustaka (APA 7)
                      </button>
                    </div>

                    <span className="text-[11px] font-mono text-slate-400 hidden md:inline">
                      Format Kertas: A4 (210 × 297 mm)
                    </span>
                  </div>

                  {/* The Simulated A4 Paper Canvas on Neutral Drafting Backdrop */}
                  <div className="flex justify-center p-8 bg-slate-100 rounded-2xl border border-slate-200 overflow-auto min-h-[500px] shadow-inner relative">
                    {/* CSS zoom (bukan transform) agar ukuran layout ikut menskala:
                        overflow container menghitung area scroll dengan benar dan
                        kertas A4 yang dizoom tidak lagi keluar dari bingkai. */}
                    <div
                      style={{ zoom: zoomLevel / 100 }}
                      className="a4-preview-sheet w-[560px] min-h-[780px] bg-white text-slate-900 rounded shadow-xl relative transition-transform duration-150 p-10 flex flex-col justify-between font-serif select-none border border-slate-200"
                    >
                      {/* Margin Overlay Indicators */}
                      {showMarginGuide && (
                        <>
                          <div className="absolute top-0 left-0 right-0 h-10 border-b border-dashed border-blue-300 pointer-events-none flex items-center justify-center text-[10px] text-blue-500 font-sans opacity-80">
                            Atas: 4 cm
                          </div>
                          <div className="absolute top-0 bottom-0 left-0 w-10 border-r border-dashed border-blue-300 pointer-events-none flex items-center justify-center text-[10px] text-blue-500 font-sans opacity-80 [writing-mode:vertical-rl]">
                            Kiri: 4 cm (Batas Penjilidan)
                          </div>
                          <div className="absolute top-0 bottom-0 right-0 w-8 border-l border-dashed border-blue-300 pointer-events-none flex items-center justify-center text-[10px] text-blue-500 font-sans opacity-80 [writing-mode:vertical-rl]">
                            Kanan: 3 cm
                          </div>
                          <div className="absolute bottom-0 left-0 right-0 h-8 border-t border-dashed border-blue-300 pointer-events-none flex items-center justify-center text-[10px] text-blue-500 font-sans opacity-80">
                            Bawah: 3 cm
                          </div>
                        </>
                      )}

                      {/* PAGE 1: COVER PAGE */}
                      {previewPage === 'cover' && (
                        <div className="flex flex-col items-center justify-between h-full text-center space-y-6 pt-4 pb-4">
                          <div className="space-y-3">
                            <h1 className="text-base font-extrabold uppercase tracking-wide text-slate-900 leading-snug max-w-md">
                              ANALISIS DAN IMPLEMENTASI SISTEM AKADEMIK CERDAS BERBASIS MODEL BAHASA BESAR
                            </h1>
                            <p className="text-xs font-bold text-slate-700 tracking-wider">
                              LAPORAN TUGAS AKHIR / PRAKTIKUM MAHASISWA
                            </p>
                          </div>

                          {/* University Logo Box */}
                          <div className="w-24 h-24 border-2 border-dashed border-slate-300 rounded-2xl flex flex-col items-center justify-center p-2 bg-slate-50 text-slate-500">
                            <GraduationCap className="w-8 h-8 text-blue-600 mb-1" />
                            <span className="text-[9px] font-sans font-semibold text-slate-700">Logo Kampus</span>
                            <span className="text-[8px] font-sans text-slate-400">Ukuran 5x5 cm</span>
                          </div>

                          {/* Student & Lecturer Meta */}
                          <div className="space-y-4 text-xs text-slate-800">
                            <div>
                              <p className="font-bold">Disusun Oleh:</p>
                              <p className="font-medium text-slate-700">Nama : NAMA MAHASISWA</p>
                              <p className="font-medium text-slate-700">NIM  : 2024101010</p>
                            </div>

                            <div>
                              <p className="font-bold">Dosen Pembimbing:</p>
                              <p className="font-medium text-slate-700">Dr. Ir. Dosen Pembimbing, M.Kom.</p>
                              <p className="text-[11px] text-slate-500">NIDN: 0012057801</p>
                            </div>

                            <div>
                              <p className="font-semibold text-slate-700">Mata Kuliah: Sistem Rekayasa Perangkat Lunak</p>
                            </div>
                          </div>

                          {/* University & Year Footer */}
                          <div className="text-xs font-bold text-slate-800 space-y-0.5">
                            <p>PROGRAM STUDI TEKNIK INFORMATIKA</p>
                            <p>FAKULTAS ILMU KOMPUTER</p>
                            <p className="text-slate-600 font-medium">2026</p>
                          </div>
                        </div>
                      )}

                      {/* PAGE 2: TABLE OF CONTENTS */}
                      {previewPage === 'toc' && (
                        <div className="space-y-4 text-left">
                          <h2 className="text-center font-bold text-sm tracking-wider text-slate-900 border-b border-slate-200 pb-2">
                            DAFTAR ISI
                          </h2>
                          <div className="space-y-2 text-xs font-sans text-slate-700 pt-2 leading-relaxed">
                            <div className="flex justify-between items-baseline">
                              <span className="font-bold">HALAMAN JUDUL</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">i</span>
                            </div>
                            <div className="flex justify-between items-baseline">
                              <span className="font-bold">KATA PENGANTAR</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">ii</span>
                            </div>
                            <div className="flex justify-between items-baseline">
                              <span className="font-bold">DAFTAR ISI</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">iii</span>
                            </div>
                            <div className="flex justify-between items-baseline pt-2">
                              <span className="font-bold">BAB I PENDAHULUAN</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">1</span>
                            </div>
                            <div className="flex justify-between items-baseline pl-4">
                              <span>1.1 Latar Belakang Masalah</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">1</span>
                            </div>
                            <div className="flex justify-between items-baseline pl-4">
                              <span>1.2 Rumusan Masalah</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">2</span>
                            </div>
                            <div className="flex justify-between items-baseline pt-2">
                              <span className="font-bold">BAB II TINJAUAN PUSTAKA</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">4</span>
                            </div>
                            <div className="flex justify-between items-baseline pl-4">
                              <span>2.1 Landasan Teori</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">4</span>
                            </div>
                            <div className="flex justify-between items-baseline pt-2">
                              <span className="font-bold">BAB III METODOLOGI PENELITIAN</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">9</span>
                            </div>
                            <div className="flex justify-between items-baseline pt-2">
                              <span className="font-bold">BAB IV HASIL DAN PEMBAHASAN</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">15</span>
                            </div>
                            <div className="flex justify-between items-baseline pt-2">
                              <span className="font-bold">BAB V KESIMPULAN DAN SARAN</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">24</span>
                            </div>
                            <div className="flex justify-between items-baseline pt-2">
                              <span className="font-bold">DAFTAR PUSTAKA</span>
                              <span className="border-b border-dotted border-slate-400 flex-1 mx-2"></span>
                              <span className="font-serif">26</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* PAGE 3: REPORT BODY */}
                      {previewPage === 'body' && (
                        <div className="space-y-4 text-left leading-relaxed">
                          <div className="text-center space-y-0.5">
                            <h2 className="font-bold text-sm text-slate-900 tracking-wider">BAB I</h2>
                            <h3 className="font-bold text-sm text-slate-900 tracking-wider">PENDAHULUAN</h3>
                          </div>

                          <div className="space-y-3 text-xs text-slate-800 text-justify">
                            <h4 className="font-bold text-xs text-slate-900">1.1 Latar Belakang Masalah</h4>
                            <p className="indent-6">
                              Kepatuhan terhadap kaidah penulisan akademik merupakan standar fundamental dalam penyusunan laporan ilmiah pada perguruan tinggi (Kemendikbudristek, 2024). Penggunaan template terstandarisasi dengan margin 4-4-3-3 cm dan tipografi Times New Roman 12 pt memastikan konsistensi visual serta memenuhi kriteria penjilidan resmi fakultas (Suryadi & Pratama, 2024).
                            </p>
                            <p className="indent-6">
                              Dalam ekosistem pendidikan modern, otomatisasi pembentukan dokumen berbasis kecerdasan buatan harus senantiasa diverifikasi silang dengan sumber rujukan primer terindeks DOI maupun artikel jurnal bereputasi (Adiwijaya et al., 2023). Hal ini menjamin bahwa setiap klaim faktual dapat dipertanggungjawabkan keabsahannya.
                            </p>
                          </div>
                        </div>
                      )}

                      {/* PAGE 4: BIBLIOGRAPHY */}
                      {previewPage === 'references' && (
                        <div className="space-y-4 text-left">
                          <h2 className="text-center font-bold text-sm tracking-wider text-slate-900 border-b border-slate-200 pb-2">
                            DAFTAR PUSTAKA
                          </h2>
                          <div className="space-y-3 text-xs text-slate-800 leading-normal pt-2">
                            <p className="pl-6 -indent-6">
                              Adiwijaya, R., & Hartono, B. (2023). Penerapan model bahasa alami dalam rekayasa perangkat lunak akademik. <em>Jurnal Ilmiah Teknologi Informasi</em>, 15(2), 112–125. https://doi.org/10.1016/j.jiti.2023.04.01
                            </p>
                            <p className="pl-6 -indent-6">
                              CrossRef International. (2024). <em>Digital Object Identifier Standard Guidelines for Scholarly Publishing</em>. Elsevier Academic Press.
                            </p>
                            <p className="pl-6 -indent-6">
                              Suryadi, M., Pratama, A., & Wibowo, S. (2024). Otomatisasi struktur dokumen karya tulis ilmiah menggunakan ekstraksi sitasi terdistribusi. <em>Prosiding Konferensi Nasional Ilmu Komputer</em>, 8(1), 45–53.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: ACADEMIC FORMAT SPECIFICATIONS */}
              {activeTab === 'specs' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-brand-50 border border-brand-200/80 flex items-start space-x-3">
                    <Award className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-bold text-blue-950">Pedoman Baku Karya Ilmiah & Laporan Perguruan Tinggi</h4>
                      <p className="text-[11px] text-blue-800 mt-0.5">
                        Template ini telah diprogram mengikuti buku pedoman resmi penulisan skripsi, tugas akhir, dan laporan akademik perguruan tinggi di Indonesia.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1">
                      <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">1. Dimensi Kertas</span>
                      <h5 className="text-xs font-bold text-slate-800">Standar ISO A4 (21.0 × 29.7 cm)</h5>
                      <p className="text-[11px] text-slate-500">
                        Menggunakan ukuran kertas standar internasional A4 dengan gramatur baku minimal 80 gsm untuk cetak dokumen resmi.
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1">
                      <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">2. Margin 4-4-3-3 cm</span>
                      <h5 className="text-xs font-bold text-slate-800">Kiri 4 cm, Atas 4 cm, Kanan 3 cm, Bawah 3 cm</h5>
                      <p className="text-[11px] text-slate-500">
                        Margin kiri 4 cm dirancang khusus memberi ruang penjilidan hard cover/soft cover agar teks tidak terpotong saat dibaca.
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1">
                      <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">3. Tipografi & Hirarki</span>
                      <h5 className="text-xs font-bold text-slate-800">Times New Roman 12 pt (Isi) & 14 pt (BAB)</h5>
                      <p className="text-[11px] text-slate-500">
                        Gaya judul bab menggunakan Heading 1 (14 pt Tebal Kapital Terpusat), sedangkan Subbab menggunakan Heading 2 (12 pt Tebal).
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1">
                      <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">4. Spasi & Paragraf</span>
                      <h5 className="text-xs font-bold text-slate-800">1.5 Spasi Baris & Rata Kiri-Kanan (Justify)</h5>
                      <p className="text-[11px] text-slate-500">
                        Baris pertama setiap alinea menjorok ke dalam (first-line indent) sebesar 1 cm dengan format rata kiri-kanan rapi.
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1">
                      <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">5. Daftar Isi Dinamis</span>
                      <h5 className="text-xs font-bold text-slate-800">Native Word TOC Field Code</h5>
                      <p className="text-[11px] text-slate-500">
                        Daftar isi dibuat menggunakan field resmi Word yang otomatis menyelaraskan judul bab dan nomor halaman tanpa ketik manual.
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1">
                      <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">6. Standar Bibliografi</span>
                      <h5 className="text-xs font-bold text-slate-800">APA 7th Edition (Hanging Indent 1.27 cm)</h5>
                      <p className="text-[11px] text-slate-500">
                        Daftar pustaka berurutan abjad dengan indentasi gantung 1.27 cm lengkap dengan pranala DOI/URL artikel jurnal.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: DIAGNOSTIK & JANGKAR PENANDA WORD */}
              {activeTab === 'tags' && (
                <div className="space-y-5 animate-fadeIn">
                  {/* Hero Health Dashboard Card */}
                  <div className="p-5 rounded-2xl bg-brand-50 border border-brand-200 shadow-sm relative overflow-hidden">
                    <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="space-y-1.5">
                        <div className="flex items-center space-x-2">
                          <span className="p-1 rounded-md bg-blue-100 text-blue-700">
                            <ShieldCheck className="w-4 h-4" />
                          </span>
                          <span className="text-xs font-bold uppercase tracking-widest text-blue-700">
                            Pusat Diagnostik & Verifikasi Berkas
                          </span>
                        </div>
                        <h4 className="text-lg font-extrabold tracking-tight text-slate-900 flex items-center gap-2">
                          <span>Kelayakan Template Ekspor</span>
                          {validCount === 10 ? (
                            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1 shadow-xs">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              <span>100% Siap Ekspor</span>
                            </span>
                          ) : (
                            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 flex items-center gap-1 shadow-xs">
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                              <span>{issuesCount} Jangkar Perlu Diperiksa</span>
                            </span>
                          )}
                        </h4>
                        <p className="text-xs text-slate-600 max-w-xl">
                          Sistem otomatis memindai berkas Word (.docx) Anda untuk mendeteksi 10 jangkar data agar siap disuntikkan naskah laporan dari AI.
                        </p>
                      </div>

                      {/* Right Action Quick Tools on Banner */}
                      <div className="flex items-center gap-2.5 shrink-0">
                        <button
                          type="button"
                          onClick={copyAllTagsToClipboard}
                          className="px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center space-x-1.5 transition border border-slate-200 shadow-xs"
                        >
                          <CheckCheck className="w-3.5 h-3.5 text-blue-600" />
                          <span>Salin 10 Jangkar</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleOpenInWord(selectedTemplate.id)}
                          className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center space-x-1.5 transition shadow-sm shadow-blue-500/20"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Buka di Word</span>
                        </button>
                      </div>
                    </div>

                    {/* Segmented Visual Progress Meter */}
                    <div className="mt-4 pt-4 border-t border-blue-200/60">
                      <div className="flex items-center justify-between text-xs mb-2">
                        <span className="text-[11px] font-semibold text-slate-600">
                          Kemajuan Jangkar ({validCount} dari 10 Terpasang Sempurna)
                        </span>
                        <span className="text-[11px] font-mono font-bold text-blue-700">
                          {healthPercent}% Lengkap
                        </span>
                      </div>
                      <div className="grid grid-cols-10 gap-1.5">
                        {tagStatuses.map((ts, idx) => (
                          <div
                            key={idx}
                            title={`${ts.def.friendlyName}: ${ts.label}`}
                            className={`h-2 rounded-full transition-all duration-300 ${
                              ts.status === 'valid'
                                ? 'bg-emerald-500 shadow-xs'
                                : ts.status === 'not_standalone'
                                ? 'bg-amber-400 shadow-xs'
                                : 'bg-slate-200'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Filter and Search Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200/80">
                    <div className="flex items-center space-x-1 overflow-x-auto">
                      <button
                        onClick={() => setTagStatusFilter('all')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                          tagStatusFilter === 'all'
                            ? 'bg-blue-600 text-white shadow-xs'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        Semua ({tagStatuses.length})
                      </button>

                      <button
                        onClick={() => setTagStatusFilter('valid')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1 ${
                          tagStatusFilter === 'valid'
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        <span>Valid</span>
                        <span className="px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800 text-[10px]">
                          {validCount}
                        </span>
                      </button>

                      <button
                        onClick={() => setTagStatusFilter('issues')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1 ${
                          tagStatusFilter === 'issues'
                            ? 'bg-amber-50 text-amber-800 border border-amber-200 shadow-xs'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        <span>Perlu Dicek</span>
                        <span className="px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-800 text-[10px]">
                          {issuesCount}
                        </span>
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <select
                        value={tagCategoryFilter}
                        onChange={(e) => setTagCategoryFilter(e.target.value as any)}
                        className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        <option value="all">Semua Kategori</option>
                        <option value="identitas">👤 Identitas & Metadata (6)</option>
                        <option value="media">Aset Media & Logo (1)</option>
                        <option value="struktur">📑 Struktur Laporan (3)</option>
                      </select>

                      <div className="relative">
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
                        <input
                          type="text"
                          value={tagSearchQuery}
                          onChange={(e) => setTagSearchQuery(e.target.value)}
                          placeholder="Cari nama..."
                          className="pl-7 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 w-32 sm:w-40"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Diagnostic Cards List */}
                  {filteredDiagnosticTags.length === 0 ? (
                    <div className="p-8 text-center text-slate-400 bg-slate-50 rounded-xl border border-slate-200/80">
                      <Tag className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                      <p className="text-xs font-bold text-slate-600">Tidak ada jangkar yang sesuai filter.</p>
                      <button
                        onClick={() => { setTagStatusFilter('all'); setTagCategoryFilter('all'); setTagSearchQuery(''); }}
                        className="mt-2 text-xs text-blue-600 font-semibold hover:underline"
                      >
                        Reset Filter
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {filteredDiagnosticTags.map(({ def, status, label }) => {
                        const isCopied = copiedTag === def.tag;
                        const isValid = status === 'valid';
                        const isNotStandalone = status === 'not_standalone';

                        return (
                          <div
                            key={def.tag}
                            className={`p-4 rounded-xl border transition-all relative overflow-hidden bg-white shadow-xs ${
                              isValid
                                ? 'border-slate-200/90 hover:border-slate-300 hover:shadow-sm'
                                : isNotStandalone
                                ? 'border-amber-300 bg-amber-50/20'
                                : 'border-rose-300 bg-rose-50/20'
                            }`}
                          >
                            <div className={`absolute top-0 bottom-0 left-0 w-1.5 ${
                              isValid ? 'bg-emerald-500' : isNotStandalone ? 'bg-amber-500' : 'bg-rose-500'
                            }`} />

                            <div className="pl-2 flex flex-col md:flex-row md:items-center justify-between gap-3">
                              <div className="space-y-2 min-w-0 flex-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  {/* Human-Friendly Primary Name */}
                                  <h5 className="text-sm font-extrabold text-slate-800 tracking-tight">
                                    {def.friendlyName}
                                  </h5>

                                  {/* Tag Monospace Pill */}
                                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200">
                                    {def.tag}
                                  </span>

                                  {def.special ? (
                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 flex items-center gap-1">
                                      <Layers className="w-3 h-3 text-indigo-600" />
                                      <span>Paragraf Mandiri</span>
                                    </span>
                                  ) : (
                                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                                      Teks Sebaris
                                    </span>
                                  )}

                                  <span className="text-[10px] font-semibold text-slate-400">
                                    • {def.categoryLabel}
                                  </span>
                                </div>

                                <div>
                                  <p className="text-xs text-slate-600">{def.desc}</p>
                                  <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-1 flex-wrap">
                                    <span className="flex items-center gap-1 text-slate-600">
                                      <strong className="text-slate-700">Posisi:</strong> {def.location}
                                    </span>
                                    <span className="text-slate-300">|</span>
                                    <span className="font-mono text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">
                                      Hasil Ekspor: {def.sampleValue}
                                    </span>
                                  </div>
                                  {def.ruleExplanation && isNotStandalone && (
                                    <div className="mt-2 p-2 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-800 flex items-start space-x-1.5">
                                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                                      <span>{def.ruleExplanation}</span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-2.5 shrink-0 self-end md:self-center">
                                {isValid ? (
                                  <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold flex items-center space-x-1.5">
                                    <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                                    <span>Terpasang & Valid</span>
                                  </span>
                                ) : isNotStandalone ? (
                                  <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-xs font-bold flex items-center space-x-1.5">
                                    <AlertTriangle className="w-3.5 h-3.5" />
                                    <span>Tercampur Teks Lain</span>
                                  </span>
                                ) : (
                                  <span className="px-3 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200 text-xs font-bold flex items-center space-x-1.5">
                                    <span className="text-xs">✕</span>
                                    <span>Belum Terpasang</span>
                                  </span>
                                )}

                                <button
                                  type="button"
                                  onClick={() => copyToClipboard(def.tag)}
                                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition border ${
                                    isCopied
                                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
                                  }`}
                                  title="Salin penanda Word ini"
                                >
                                  {isCopied ? (
                                    <>
                                      <Check className="w-3.5 h-3.5" />
                                      <span>Tersalin!</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="w-3.5 h-3.5 text-slate-500" />
                                      <span>Salin Jangkar</span>
                                    </>
                                  )}
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-400">
              <FileCode2 className="w-12 h-12 text-slate-300 mb-2" />
              <p className="text-sm font-semibold text-slate-600">Pilih Template dari Daftar di Sebelah Kiri</p>
              <p className="text-xs text-slate-400 mt-1 max-w-sm">
                Klik salah satu template untuk melihat pratinjau lembar A4 dan checklist kelayakan ekspor.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* CUSTOMIZE STANDARD TEMPLATE MODAL */}
      {showCustomizeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-200">
                  <Sliders className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">Kustomisasi Template Standar</h3>
                  <p className="text-[11px] text-slate-400">Atur parameter format baku dokumen Word</p>
                </div>
              </div>
              <button
                onClick={() => setShowCustomizeModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1.5">Tipografi / Jenis Huruf</label>
                <select
                  value={customFont}
                  onChange={(e) => setCustomFont(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="Times New Roman">Times New Roman (Rekomendasi Resmi Skripsi)</option>
                  <option value="Arial">Arial (Modern Sans-Serif)</option>
                  <option value="Georgia">Georgia (Serif Elegan)</option>
                  <option value="Calibri">Calibri (Microsoft Office Default)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1.5">Batas Margin Halaman</label>
                <select
                  value={customMargin}
                  onChange={(e) => setCustomMargin(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="4433">Margin 4-4-3-3 cm (Standar Skripsi / Tesis / Tugas Akhir)</option>
                  <option value="3333">Margin 3-3-3-3 cm (Standar Makalah Bebas / Artikel Jurnal)</option>
                </select>
                <p className="text-[10px] text-slate-400 mt-1">
                  *Margin 4-4-3-3 cm memberi ruang ekstra 4 cm di sebelah kiri untuk penjilidan jilid tebal.
                </p>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1.5">Spasi Baris (Line Spacing)</label>
                <select
                  value={customSpacing}
                  onChange={(e) => setCustomSpacing(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="1.5">1.5 Spasi (Standar Pedoman Perguruan Tinggi)</option>
                  <option value="2.0">2.0 Spasi (Double Spacing - Standar Draft Internasional)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowCustomizeModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-semibold"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleCreateDefault}
                disabled={loading}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-bold flex items-center space-x-1.5 shadow-md shadow-brand-600/20"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Terapkan & Buat Template</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
