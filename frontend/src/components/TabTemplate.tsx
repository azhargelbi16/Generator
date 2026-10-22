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
  Wand2,
  Search,
  HelpCircle,
  Sparkles,
  Info
} from 'lucide-react';
import { api, TemplateItem } from '../lib/api';

interface RequiredTagDef {
  tag: string;
  name: string;
  desc: string;
  special: boolean;
}

const REQUIRED_TAGS_DEF: RequiredTagDef[] = [
  { tag: '{{JUDUL}}', name: 'JUDUL', desc: 'Judul lengkap laporan akademik', special: false },
  { tag: '{{NAMA}}', name: 'NAMA', desc: 'Nama lengkap mahasiswa penyusun', special: false },
  { tag: '{{NIM}}', name: 'NIM', desc: 'Nomor induk mahasiswa', special: false },
  { tag: '{{MATA_KULIAH}}', name: 'MATA_KULIAH', desc: 'Nama mata kuliah terkait', special: false },
  { tag: '{{DOSEN}}', name: 'DOSEN', desc: 'Nama dan gelar dosen pembimbing', special: false },
  { tag: '{{TANGGAL}}', name: 'TANGGAL', desc: 'Tanggal cetak (mis: 22 Oktober 2026)', special: false },
  { tag: '{{LOGO}}', name: 'LOGO', desc: 'Gambar logo 5x5 cm (Wajib berdiri sendiri di 1 paragraf)', special: true },
  { tag: '{{DAFTAR_ISI}}', name: 'DAFTAR_ISI', desc: 'Tabel daftar isi TOC otomatis Word (Wajib berdiri sendiri)', special: true },
  { tag: '{{ISI_LAPORAN}}', name: 'ISI_LAPORAN', desc: 'Seluruh bab laporan hasil AI (Wajib berdiri sendiri)', special: true },
  { tag: '{{DAFTAR_PUSTAKA}}', name: 'DAFTAR_PUSTAKA', desc: 'Daftar pustaka format APA 7 (Wajib berdiri sendiri)', special: true },
];

export const TabTemplate: React.FC = () => {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateItem | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedTag, setCopiedTag] = useState<string | null>(null);
  const [copiedPath, setCopiedPath] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const list = await api.listTemplates();
      if (list) {
        setTemplates(list);
        if (list.length > 0) {
          if (!selectedTemplate || !list.some((t) => t.id === selectedTemplate.id)) {
            setSelectedTemplate(list[0]);
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
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    setLoading(true);
    try {
      const res = await api.uploadTemplate();
      if (res?.success) {
        await loadTemplates();
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDefault = async () => {
    setLoading(true);
    try {
      await api.createDefaultTemplate();
      await loadTemplates();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    setLoading(true);
    try {
      await api.deleteTemplate(id);
      setConfirmDeleteId(null);
      await loadTemplates();
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedTag(text);
    setTimeout(() => setCopiedTag(null), 1500);
  };

  const copyPathToClipboard = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const filteredTemplates = templates.filter((t) =>
    t.nama.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.deskripsi?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const readyCount = templates.filter((t) => t.status === 'lengkap').length;
  const invalidCount = templates.length - readyCount;

  // Helper function to check status of a required tag for the selected template
  const getTagStatus = (tagDef: RequiredTagDef) => {
    if (!selectedTemplate) return { status: 'missing', label: 'Belum Ada' };
    const missing = selectedTemplate.missing || [];
    const notStandalone = selectedTemplate.not_standalone || [];
    const placeholders = selectedTemplate.placeholders || [];

    const isMissing = missing.includes(tagDef.tag) || !placeholders.includes(tagDef.name);
    const isNotStandalone = notStandalone.includes(tagDef.tag);

    if (isMissing) {
      return { status: 'missing', label: 'Hilang (Belum Ada)' };
    }
    if (isNotStandalone) {
      return { status: 'not_standalone', label: 'Tidak Berdiri Sendiri' };
    }
    return { status: 'valid', label: 'Valid & Terpasang' };
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 max-w-6xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
            <FileCode2 className="w-5 h-5 text-brand-600" />
            <span>Manajemen Template Dokumen (.docx)</span>
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Kelola dan validasi template Microsoft Word Anda. Penanda <code className="text-brand-700 font-semibold px-1 py-0.5 bg-brand-50 rounded">{"{{...}}"}</code> akan otomatis terisi saat ekspor.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleCreateDefault}
            disabled={loading}
            className="px-3.5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition border border-slate-200/80 shadow-sm"
            title="Buat template standar resmi dengan cover, logo, TOC, dan daftar pustaka lengkap"
          >
            <Wand2 className="w-3.5 h-3.5 text-brand-600" />
            <span>Buat Template Standar</span>
          </button>

          <button
            onClick={handleUpload}
            disabled={loading}
            className="px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-2 transition shadow-md shadow-brand-600/20"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Unggah Template .docx</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Template</span>
            <div className="text-2xl font-extrabold text-slate-800 mt-0.5">{templates.length}</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600 font-bold">
            <FileText className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Siap Digunakan</span>
            <div className="text-2xl font-extrabold text-emerald-600 mt-0.5">{readyCount}</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Perlu Perbaikan</span>
            <div className="text-2xl font-extrabold text-amber-600 mt-0.5">{invalidCount}</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Main Grid: Left Template List, Right Detailed Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 Cols): Template List */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 flex flex-col min-h-[520px]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <span>Daftar Template Dokumen</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {templates.length}
              </span>
            </h3>
          </div>

          {/* Search Box */}
          <div className="relative mb-3">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari nama template..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {templates.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-200 rounded-xl">
              <FileCode2 className="w-12 h-12 text-slate-300 mb-3" />
              <h4 className="text-sm font-bold text-slate-700">Belum Ada Template</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-xs mb-4">
                Unggah file dokumen Word (.docx) Anda atau buat template standar otomatis dalam satu klik.
              </p>
              <button
                onClick={handleCreateDefault}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Buat Template Standar Otomatis</span>
              </button>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 max-h-[580px]">
              {filteredTemplates.map((tpl) => {
                const isSelected = selectedTemplate?.id === tpl.id;
                const isLengkap = tpl.status === 'lengkap';
                return (
                  <div
                    key={tpl.id}
                    onClick={() => setSelectedTemplate(tpl)}
                    className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                      isSelected
                        ? 'border-brand-500 bg-brand-50/40 shadow-sm ring-1 ring-brand-500/20'
                        : 'border-slate-200/80 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start space-x-2.5 min-w-0 flex-1">
                        <div className={`p-2 rounded-lg mt-0.5 ${isSelected ? 'bg-brand-100 text-brand-700' : 'bg-slate-100 text-slate-500'}`}>
                          <FileText className="w-4 h-4 shrink-0" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <h4 className="text-xs font-bold text-slate-800 truncate">{tpl.nama}</h4>
                          <p className="text-[11px] text-slate-400 truncate mt-0.5">
                            {tpl.deskripsi || tpl.path}
                          </p>
                        </div>
                      </div>

                      {isLengkap ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/80 shrink-0 flex items-center space-x-1">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Siap</span>
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/80 shrink-0 flex items-center space-x-1">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Kurang</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column (7 Cols): Inspector & Live Checklist */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 flex flex-col">
          {selectedTemplate ? (
            <div className="space-y-6">
              {/* Template Header Info */}
              <div className="flex items-start justify-between border-b border-slate-100 pb-4">
                <div className="space-y-1 min-w-0 flex-1 pr-3">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-800 truncate">{selectedTemplate.nama}</h3>
                    {selectedTemplate.status === 'lengkap' ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 shrink-0">
                        Valid & Lengkap
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 shrink-0">
                        Belum Memenuhi Syarat
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                    <span className="truncate max-w-sm">{selectedTemplate.path}</span>
                    <button
                      type="button"
                      onClick={() => copyPathToClipboard(selectedTemplate.path)}
                      className="text-slate-400 hover:text-slate-600 underline text-[11px] shrink-0"
                    >
                      {copiedPath ? 'Tersalin!' : 'Salin Path'}
                    </button>
                  </div>
                </div>

                {/* Delete button or confirmation */}
                {confirmDeleteId === selectedTemplate.id ? (
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-rose-600 font-semibold">Yakin hapus?</span>
                    <button
                      onClick={() => handleDelete(selectedTemplate.id)}
                      className="px-2.5 py-1 bg-rose-600 text-white rounded-lg text-xs font-semibold hover:bg-rose-700"
                    >
                      Ya
                    </button>
                    <button
                      onClick={() => setConfirmDeleteId(null)}
                      className="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg text-xs hover:bg-slate-200"
                    >
                      Batal
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmDeleteId(selectedTemplate.id)}
                    className="px-3 py-1.5 text-xs text-rose-600 hover:bg-rose-50 rounded-xl flex items-center space-x-1.5 transition border border-rose-100 shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Hapus Template</span>
                  </button>
                )}
              </div>

              {/* Status Alert Banner */}
              {selectedTemplate.status === 'lengkap' ? (
                <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200/80 flex items-start space-x-2.5 text-xs text-emerald-800">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Template Siap Digunakan!</span>
                    <p className="text-emerald-700 text-[11px] mt-0.5">
                      Seluruh penanda wajib telah terpasang dengan benar pada dokumen Word ini dan siap diproses oleh modul renderer laporan.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 flex items-start space-x-2.5 text-xs text-amber-900">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="font-bold">Template Belum Memenuhi Syarat Ekspor:</span>
                    {selectedTemplate.missing?.length > 0 && (
                      <p className="text-amber-800 text-[11px]">
                        • Penanda wajib yang belum ditemukan: <strong className="font-mono">{selectedTemplate.missing.join(', ')}</strong>
                      </p>
                    )}
                    {selectedTemplate.not_standalone?.length > 0 && (
                      <p className="text-amber-800 text-[11px]">
                        • Penanda khusus harus berada sendiri di satu paragraf (tidak boleh dicampur teks lain): <strong className="font-mono">{selectedTemplate.not_standalone.join(', ')}</strong>
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Live Interactive Placeholder Checklist */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <span>Pemeriksaan Penanda Wajib (10 Penanda)</span>
                    <Info className="w-3.5 h-3.5 text-slate-400" />
                  </h4>
                  <span className="text-[11px] text-slate-400">Klik kartu untuk menyalin tag</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {REQUIRED_TAGS_DEF.map((def) => {
                    const st = getTagStatus(def);
                    const isCopied = copiedTag === def.tag;
                    return (
                      <div
                        key={def.tag}
                        onClick={() => copyToClipboard(def.tag)}
                        className={`p-2.5 rounded-xl border text-left cursor-pointer transition flex items-center justify-between group ${
                          st.status === 'valid'
                            ? 'bg-emerald-50/30 border-emerald-200/80 hover:bg-emerald-50/60'
                            : st.status === 'not_standalone'
                            ? 'bg-amber-50/40 border-amber-200 hover:bg-amber-50/70'
                            : 'bg-rose-50/40 border-rose-200 hover:bg-rose-50/70'
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-xs font-bold text-slate-800">{def.tag}</span>
                            {def.special && (
                              <span className="text-[9px] font-semibold px-1 py-0.2 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                                Blok Paragraf
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">{def.desc}</p>
                        </div>

                        <div className="flex items-center space-x-2 shrink-0">
                          {st.status === 'valid' ? (
                            <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                              <Check className="w-3 h-3 stroke-[2.5]" />
                            </span>
                          ) : st.status === 'not_standalone' ? (
                            <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center">
                              <AlertTriangle className="w-3 h-3" />
                            </span>
                          ) : (
                            <span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center">
                              <span className="text-xs font-bold leading-none">✕</span>
                            </span>
                          )}

                          <span className="opacity-0 group-hover:opacity-100 transition text-[10px] text-brand-600 font-semibold">
                            {isCopied ? 'Tersalin!' : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Collapsible Word Formatting Guide */}
              <div className="border border-slate-200/80 rounded-xl overflow-hidden text-xs">
                <button
                  type="button"
                  onClick={() => setShowGuide(!showGuide)}
                  className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100/80 font-bold text-slate-700 flex items-center justify-between transition"
                >
                  <span className="flex items-center gap-1.5">
                    <HelpCircle className="w-4 h-4 text-brand-600" />
                    <span>Petunjuk Format Microsoft Word untuk Mahasiswa</span>
                  </span>
                  <span className="text-slate-400">{showGuide ? '▲ Tutup' : '▼ Lihat Panduan'}</span>
                </button>

                {showGuide && (
                  <div className="p-4 bg-white space-y-2.5 text-slate-600 leading-relaxed border-t border-slate-100">
                    <p>
                      <strong>1. Gaya Judul Bab & Subbab:</strong> Pastikan gaya judul di Word menggunakan <code>Heading 1</code> untuk BAB dan <code>Heading 2</code> untuk Subbab agar daftar isi dapat di-generate otomatis.
                    </p>
                    <p>
                      <strong>2. Aturan Penanda Berdiri Sendiri:</strong> Penanda <code>{"{{ISI_LAPORAN}}"}</code>, <code>{"{{DAFTAR_PUSTAKA}}"}</code>, <code>{"{{DAFTAR_ISI}}"}</code>, dan <code>{"{{LOGO}}"}</code> harus menjadi satu-satunya teks dalam paragraf tersebut tanpa spasi atau teks pengantar lain.
                    </p>
                    <p>
                      <strong>3. Batas Margin & Spasi:</strong> Format baku akademik dianjurkan menggunakan margin 4-4-3-3 cm (Kiri 4 cm, Atas 4 cm, Kanan 3 cm, Bawah 3 cm) dengan font Times New Roman 12 pt dan spasi 1.5.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-400">
              <FileCode2 className="w-12 h-12 text-slate-200 mb-2" />
              <p className="text-sm font-semibold text-slate-600">Pilih Template dari Daftar di Sebelah Kiri</p>
              <p className="text-xs text-slate-400 mt-1 max-w-sm">
                Klik salah satu template untuk melihat live checklist penanda dan status kelayakan ekspor.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
