import React, { useState, useEffect } from 'react';
import { 
  FolderOpen, 
  X, 
  Search, 
  BookmarkPlus, 
  Clock, 
  Trash2, 
  RotateCcw, 
  Loader2 
} from 'lucide-react';
import { api, SavedDraftItem } from '../lib/api';
import { toast } from '../lib/toast';

interface DraftManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDraft: (draftId: string) => Promise<void> | void;
  onNewBlankProject?: () => Promise<void> | void;
  canSaveCurrent?: boolean;
  onSaveNamedProject?: (name: string) => Promise<boolean>;
}

export const DraftManagerModal: React.FC<DraftManagerModalProps> = ({
  isOpen,
  onClose,
  onSelectDraft,
  onNewBlankProject,
  canSaveCurrent = false,
  onSaveNamedProject,
}) => {
  const [savedDrafts, setSavedDrafts] = useState<SavedDraftItem[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [selectedDraftIds, setSelectedDraftIds] = useState<string[]>([]);
  const [draftSearchQuery, setDraftSearchQuery] = useState('');
  const [isDeletingDrafts, setIsDeletingDrafts] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [isSavingProject, setIsSavingProject] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (isOpen) {
      loadDraftsList();
      setSelectedDraftIds([]);
      setDraftSearchQuery('');
      setNewProjectName('');
    }
  }, [isOpen]);

  const loadDraftsList = async () => {
    setLoadingProjects(true);
    try {
      const list = await api.listSavedDrafts();
      if (list) setSavedDrafts(list);
    } catch (err) {
      console.error(err);
      toast.error('Gagal memuat daftar draf.');
    } finally {
      setLoadingProjects(false);
    }
  };

  const formatDraftDate = (epochSec: number) => {
    if (!epochSec) return '-';
    try {
      const d = new Date(epochSec * 1000);
      return d.toLocaleDateString('id-ID', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '-';
    }
  };

  const handleToggleSelectDraft = (draftId: string) => {
    setSelectedDraftIds((prev) =>
      prev.includes(draftId) ? prev.filter((id) => id !== draftId) : [...prev, draftId]
    );
  };

  const handleSelectAllDrafts = (filteredItems: SavedDraftItem[]) => {
    const allFilteredIds = filteredItems.map((d) => d.draft_id);
    const allSelected = allFilteredIds.length > 0 && allFilteredIds.every((id) => selectedDraftIds.includes(id));
    if (allSelected) {
      setSelectedDraftIds((prev) => prev.filter((id) => !allFilteredIds.includes(id)));
    } else {
      setSelectedDraftIds((prev) => Array.from(new Set([...prev, ...allFilteredIds])));
    }
  };

  const handleDeleteSingle = async (draftId: string, title?: string) => {
    if (!window.confirm(`Hapus draf "${title || draftId}"?`)) {
      return;
    }
    try {
      await api.deleteNamedDraft(draftId);
      setSelectedDraftIds((prev) => prev.filter((id) => id !== draftId));
      if (draftId === 'active') {
        await api.clearActiveDraft();
      }
      await loadDraftsList();
      toast.success('Draf proyek berhasil dihapus.');
    } catch (err) {
      console.error(err);
      toast.error('Gagal menghapus draf.');
    }
  };

  const handleBatchDeleteDrafts = async () => {
    if (selectedDraftIds.length === 0) return;
    const count = selectedDraftIds.length;
    if (!window.confirm(`Apakah Anda yakin ingin menghapus ${count} draf yang dipilih? Tindakan ini tidak dapat dibatalkan.`)) {
      return;
    }
    setIsDeletingDrafts(true);
    try {
      if (api.deleteNamedDrafts) {
        await api.deleteNamedDrafts(selectedDraftIds);
      } else {
        await Promise.all(selectedDraftIds.map((id) => api.deleteNamedDraft(id)));
      }
      if (selectedDraftIds.includes('active')) {
        await api.clearActiveDraft();
      }
      setSelectedDraftIds([]);
      await loadDraftsList();
      toast.success(`${count} draf proyek berhasil dihapus.`);
    } catch (err) {
      console.error(err);
      toast.error('Terjadi kesalahan saat menghapus draf.');
    } finally {
      setIsDeletingDrafts(false);
    }
  };

  const handleSaveCurrent = async () => {
    if (!newProjectName.trim()) {
      toast.error('Masukkan nama proyek terlebih dahulu.');
      return;
    }
    if (!onSaveNamedProject) return;

    setIsSavingProject(true);
    try {
      const ok = await onSaveNamedProject(newProjectName.trim());
      if (ok) {
        setNewProjectName('');
        await loadDraftsList();
      }
    } finally {
      setIsSavingProject(false);
    }
  };

  if (!isOpen) return null;

  const filteredDrafts = savedDrafts.filter((d) => {
    if (!draftSearchQuery.trim()) return true;
    const q = draftSearchQuery.toLowerCase();
    return d.title.toLowerCase().includes(q) || d.draft_id.toLowerCase().includes(q);
  });
  const allFilteredSelected =
    filteredDrafts.length > 0 && filteredDrafts.every((d) => selectedDraftIds.includes(d.draft_id));

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn"
      role="presentation"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl p-6 max-w-3xl w-full shadow-2xl border border-slate-200 max-h-[88vh] flex flex-col justify-between"
        role="dialog"
        aria-modal="true"
        aria-labelledby="project-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-3.5">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-brand-100 border border-brand-200 flex items-center justify-center text-brand-700 shrink-0">
                <FolderOpen className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 id="project-dialog-title" className="text-base font-bold text-slate-800">
                    Manajemen Draf & Proyek Laporan
                  </h3>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold border border-slate-200">
                    {savedDrafts.length} Draf
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Buka kembali draf naskah, telusuri arsip proyek, atau bersihkan draf usang.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 text-base font-bold w-8 h-8 rounded-lg flex items-center justify-center transition"
              aria-label="Tutup dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Form Simpan Draf Saat Ini (jika diaktifkan) */}
          {canSaveCurrent && onSaveNamedProject && (
            <div className="p-3.5 bg-gradient-to-r from-brand-50/70 via-brand-50/30 to-slate-50 border border-brand-200 rounded-xl mb-3 shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="new-draft-input" className="text-xs font-bold text-slate-700 flex items-center space-x-1.5">
                  <BookmarkPlus className="w-3.5 h-3.5 text-brand-700" />
                  <span>Simpan Sesi Kerja Saat Ini Sebagai Draf Baru</span>
                </label>
                <span className="text-[11px] text-slate-400">Tersimpan otomatis saat menyusun</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="new-draft-input"
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSaveCurrent()}
                  placeholder="Contoh: Makalah Pertanian Presisi - Bab 1-3 Revisi..."
                  className="flex-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 shadow-xs"
                />
                <button
                  type="button"
                  onClick={handleSaveCurrent}
                  disabled={isSavingProject}
                  className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shrink-0 shadow-xs flex items-center space-x-1.5 transition active:scale-95 disabled:opacity-50"
                >
                  {isSavingProject ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <BookmarkPlus className="w-3.5 h-3.5" />
                  )}
                  <span>Simpan Draf</span>
                </button>
              </div>
            </div>
          )}

          {/* Toolbar: Pencarian, Pilih Semua & Hapus Terpilih */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-2.5">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={draftSearchQuery}
                onChange={(e) => setDraftSearchQuery(e.target.value)}
                placeholder="Cari judul draf..."
                className="w-full pl-8 pr-7 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 transition"
              />
              {draftSearchQuery && (
                <button
                  type="button"
                  onClick={() => setDraftSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex items-center space-x-2 shrink-0">
              <label className="flex items-center space-x-2 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 cursor-pointer select-none text-xs text-slate-700 transition">
                <input
                  type="checkbox"
                  checked={allFilteredSelected}
                  onChange={() => handleSelectAllDrafts(filteredDrafts)}
                  className="w-3.5 h-3.5 rounded text-brand-600 focus:ring-brand-500 border-slate-300 cursor-pointer"
                />
                <span className="font-medium">
                  Pilih Semua {filteredDrafts.length > 0 ? `(${filteredDrafts.length})` : ''}
                </span>
              </label>

              {selectedDraftIds.length > 0 && (
                <button
                  type="button"
                  onClick={handleBatchDeleteDrafts}
                  disabled={isDeletingDrafts}
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition active:scale-95 disabled:opacity-50"
                >
                  {isDeletingDrafts ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                  <span>Hapus Terpilih ({selectedDraftIds.length})</span>
                </button>
              )}
            </div>
          </div>

          {/* Daftar Draf */}
          <div className="max-h-[340px] overflow-y-auto space-y-2 pr-1">
            {loadingProjects ? (
              <div className="text-center py-10 text-xs text-slate-500 flex items-center justify-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                <span>Memuat daftar draf proyek...</span>
              </div>
            ) : savedDrafts.length === 0 ? (
              <div className="text-center py-10 border border-dashed border-slate-200 rounded-xl bg-slate-50/50 text-xs text-slate-500">
                Belum ada draf tersimpan. Sesi lembar kerja Anda otomatis tersimpan saat menyusun laporan.
              </div>
            ) : filteredDrafts.length === 0 ? (
              <div className="text-center py-10 border border-dashed border-slate-200 rounded-xl bg-slate-50/50 text-xs text-slate-500">
                Tidak ada draf yang cocok dengan kata kunci &quot;{draftSearchQuery}&quot;.
              </div>
            ) : (
              filteredDrafts.map((d) => {
                const isSelected = selectedDraftIds.includes(d.draft_id);
                return (
                  <div
                    key={d.draft_id}
                    className={`p-3 rounded-xl border transition flex items-start sm:items-center justify-between gap-3 text-xs ${
                      d.is_active
                        ? 'bg-brand-50/70 border-brand-300 ring-1 ring-brand-200/60 shadow-xs'
                        : isSelected
                        ? 'bg-brand-50/30 border-brand-200 shadow-xs'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/40'
                    }`}
                  >
                    <div className="flex items-start sm:items-center space-x-3 flex-1 min-w-0">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelectDraft(d.draft_id)}
                        className="mt-1 sm:mt-0 w-4 h-4 rounded text-brand-600 focus:ring-brand-500 border-slate-300 cursor-pointer shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-800 truncate text-[13px]">{d.title}</span>
                          {d.is_active ? (
                            <span className="shrink-0 inline-flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 border border-brand-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
                              <span>Aktif Sekarang</span>
                            </span>
                          ) : (
                            <span className="shrink-0 text-[10px] text-slate-500 font-semibold bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                              Arsip
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500 mt-1">
                          <span className="inline-flex items-center space-x-1">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>{formatDraftDate(d.mtime)}</span>
                          </span>
                          <span className="text-slate-300">•</span>
                          <span><strong>{d.sources_count}</strong> sumber</span>
                          <span className="text-slate-300">•</span>
                          <span><strong>{d.sections_count}</strong> bab</span>
                          <span className="text-slate-300">•</span>
                          <span><strong>{d.sentence_count}</strong> kalimat</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1.5 shrink-0">
                      {!d.is_active && (
                        <button
                          type="button"
                          onClick={() => onSelectDraft(d.draft_id)}
                          className="px-2.5 py-1 bg-white hover:bg-brand-50 text-brand-700 border border-brand-200 rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1 transition"
                        >
                          <FolderOpen className="w-3 h-3" />
                          <span>Buka</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDeleteSingle(d.draft_id, d.title)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                        aria-label={`Hapus draf ${d.title}`}
                        title="Hapus draf ini"
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

        {/* Modal Footer */}
        <div className="flex justify-between items-center pt-3.5 border-t border-slate-100 mt-3 text-xs">
          {onNewBlankProject ? (
            <button
              type="button"
              onClick={onNewBlankProject}
              className="px-3 py-1.5 text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg font-medium flex items-center space-x-1.5 transition active:scale-95"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Mulai Lembar Kerja Kosong Baru</span>
            </button>
          ) : <div />}

          <div className="flex items-center space-x-3">
            {selectedDraftIds.length > 0 && (
              <span className="text-slate-500 font-medium">
                {selectedDraftIds.length} draf dipilih
              </span>
            )}
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
            >
              Tutup
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
