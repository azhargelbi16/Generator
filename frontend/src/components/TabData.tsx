import React, { useState, useEffect } from 'react';
import { 
  User, 
  GraduationCap, 
  BookOpen, 
  Image as ImageIcon, 
  Plus, 
  Trash2, 
  Edit3, 
  Check, 
  Save, 
  UploadCloud, 
  AlertCircle 
} from 'lucide-react';
import { api, Profile, Dosen, MataKuliah, Logo } from '../lib/api';
import { toast } from '../lib/toast';

interface TabDataProps {
  isActive?: boolean;
}

export const TabData: React.FC<TabDataProps> = ({ isActive = false }) => {
  const [activeSubTab, setActiveSubTab] = useState<'profil' | 'dosen' | 'matkul' | 'logo'>('profil');
  const [confirmDialog, setConfirmDialog] = useState<{ message: string; onConfirm: () => void } | null>(null);

  // Profil state
  const [profile, setProfile] = useState<Profile>({ nama: '', nim: '', prodi: '', fakultas: '', institusi: '' });
  const [profileSaved, setProfileSaved] = useState(false);

  // Dosen state
  const [dosenList, setDosenList] = useState<Dosen[]>([]);
  const [dosenForm, setDosenForm] = useState<Dosen>({ nama: '', gelar: '', identitas: '' });
  const [editingDosenId, setEditingDosenId] = useState<number | null>(null);

  // Matkul state
  const [matkulList, setMatkulList] = useState<MataKuliah[]>([]);
  const [matkulForm, setMatkulForm] = useState<MataKuliah>({ nama: '', kode: '' });
  const [editingMatkulId, setEditingMatkulId] = useState<number | null>(null);

  // Logo state
  const [logoList, setLogoList] = useState<Logo[]>([]);

  useEffect(() => {
    loadAllData();
  }, []);

  useEffect(() => {
    if (isActive) {
      loadAllData();
    }
  }, [isActive]);

  const loadAllData = async () => {
    try {
      const p = await api.getProfile();
      if (p) setProfile(p);
      const d = await api.listDosen();
      if (d) setDosenList(d);
      const m = await api.listMatkul();
      if (m) setMatkulList(m);
      const l = await api.listLogos();
      if (l) setLogoList(l);
    } catch (e) {
      console.error(e);
    }
  };

  // Profil handlers
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await api.saveProfile(profile);
    if (res?.success) {
      setProfileSaved(true);
      toast.success('Data profil mahasiswa & institusi berhasil disimpan!');
      setTimeout(() => setProfileSaved(false), 2500);
    }
  };

  // Dosen handlers
  const handleSaveDosen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dosenForm.nama.trim()) return;
    if (editingDosenId) {
      await api.updateDosen({ ...dosenForm, id: editingDosenId });
      setEditingDosenId(null);
    } else {
      await api.addDosen(dosenForm);
    }
    setDosenForm({ nama: '', gelar: '', identitas: '' });
    const d = await api.listDosen();
    if (d) setDosenList(d);
  };

  const handleDeleteDosen = (id: number) => {
    setConfirmDialog({
      message: 'Apakah Anda yakin ingin menghapus data dosen ini?',
      onConfirm: async () => {
        await api.deleteDosen(id);
        const d = await api.listDosen();
        if (d) setDosenList(d);
        setConfirmDialog(null);
        toast.success('Data dosen berhasil dihapus.');
      },
    });
  };

  // Matkul handlers
  const handleSaveMatkul = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!matkulForm.nama.trim()) return;
    if (editingMatkulId) {
      await api.updateMatkul({ ...matkulForm, id: editingMatkulId });
      setEditingMatkulId(null);
    } else {
      await api.addMatkul(matkulForm);
    }
    setMatkulForm({ nama: '', kode: '' });
    const m = await api.listMatkul();
    if (m) setMatkulList(m);
  };

  const handleDeleteMatkul = (id: number) => {
    setConfirmDialog({
      message: 'Apakah Anda yakin ingin menghapus mata kuliah ini?',
      onConfirm: async () => {
        await api.deleteMatkul(id);
        const m = await api.listMatkul();
        if (m) setMatkulList(m);
        setConfirmDialog(null);
        toast.success('Mata kuliah berhasil dihapus.');
      },
    });
  };

  // Logo handlers
  const handleUploadLogo = async () => {
    const res = await api.uploadLogo();
    if (res?.success) {
      const l = await api.listLogos();
      if (l) setLogoList(l);
      toast.success('Logo berhasil diunggah.');
    }
  };

  const handleDeleteLogo = (id: number) => {
    setConfirmDialog({
      message: 'Apakah Anda yakin ingin menghapus logo ini?',
      onConfirm: async () => {
        await api.deleteLogo(id);
        const l = await api.listLogos();
        if (l) setLogoList(l);
        setConfirmDialog(null);
        toast.success('Logo berhasil dihapus.');
      },
    });
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800 tracking-tight">Data & Profil Akademik</h2>
          <p className="text-sm text-slate-500 mt-1">
            Data ini akan dicetak otomatis ke sampul dokumen Word dan header template.
          </p>
        </div>
      </div>

      {/* Sub tabs */}
      <div className="flex border-b border-slate-200 mb-6 space-x-6">
        {[
          { key: 'profil', label: 'Profil Mahasiswa', icon: User },
          { key: 'dosen', label: 'Dosen Pembimbing/Pengampu', icon: GraduationCap },
          { key: 'matkul', label: 'Mata Kuliah', icon: BookOpen },
          { key: 'logo', label: 'Logo Kampus', icon: ImageIcon },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSubTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveSubTab(tab.key as any)}
              className={`pb-3 text-sm font-semibold flex items-center space-x-2 transition border-b-2 ${
                isActive
                  ? 'border-brand-600 text-brand-700'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Profil Tab */}
      {activeSubTab === 'profil' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 max-w-2xl">
          <form onSubmit={handleSaveProfile} className="space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                Nama Lengkap
              </label>
              <input
                type="text"
                value={profile.nama}
                onChange={(e) => setProfile({ ...profile, nama: e.target.value })}
                placeholder="Contoh: Muhammad Budi Santoso"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                  NIM / NPM
                </label>
                <input
                  type="text"
                  value={profile.nim}
                  onChange={(e) => setProfile({ ...profile, nim: e.target.value })}
                  placeholder="Contoh: 21081010123"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                  Program Studi / Jurusan
                </label>
                <input
                  type="text"
                  value={profile.prodi}
                  onChange={(e) => setProfile({ ...profile, prodi: e.target.value })}
                  placeholder="Contoh: Teknik Informatika"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                  Fakultas
                </label>
                <input
                  type="text"
                  value={profile.fakultas || ''}
                  onChange={(e) => setProfile({ ...profile, fakultas: e.target.value })}
                  placeholder="Contoh: Fakultas Ilmu Komputer"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                  Perguruan Tinggi / Institusi
                </label>
                <input
                  type="text"
                  value={profile.institusi || ''}
                  onChange={(e) => setProfile({ ...profile, institusi: e.target.value })}
                  placeholder="Contoh: Universitas Jember"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                />
              </div>
            </div>
            <div className="flex items-center justify-between pt-3">
              {profileSaved ? (
                <span className="text-xs font-semibold text-emerald-600 flex items-center space-x-1">
                  <Check className="w-4 h-4" />
                  <span>Profil tersimpan!</span>
                </span>
              ) : <div />}
              <button
                type="submit"
                className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-semibold transition flex items-center space-x-2"
              >
                <Save className="w-4 h-4" />
                <span>Simpan Profil</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Dosen Tab */}
      {activeSubTab === 'dosen' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 md:col-span-1">
            <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center space-x-2">
              <Plus className="w-4 h-4 text-brand-600" />
              <span>{editingDosenId ? 'Edit Dosen' : 'Tambah Dosen'}</span>
            </h3>
            <form onSubmit={handleSaveDosen} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nama Lengkap</label>
                <input
                  type="text"
                  value={dosenForm.nama}
                  onChange={(e) => setDosenForm({ ...dosenForm, nama: e.target.value })}
                  placeholder="Nama tanpa gelar"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Gelar Akademik</label>
                <input
                  type="text"
                  value={dosenForm.gelar}
                  onChange={(e) => setDosenForm({ ...dosenForm, gelar: e.target.value })}
                  placeholder="Contoh: S.T., M.Kom., Ph.D."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">NIDN / NIP</label>
                <input
                  type="text"
                  value={dosenForm.identitas}
                  onChange={(e) => setDosenForm({ ...dosenForm, identitas: e.target.value })}
                  placeholder="Contoh: NIDN 0012345678"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold transition"
                >
                  {editingDosenId ? 'Perbarui' : 'Simpan'}
                </button>
                {editingDosenId && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingDosenId(null);
                      setDosenForm({ nama: '', gelar: '', identitas: '' });
                    }}
                    className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-medium"
                  >
                    Batal
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 md:col-span-2">
            <h3 className="text-sm font-bold text-slate-800 mb-4">Daftar Dosen ({dosenList.length})</h3>
            {dosenList.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">Belum ada data dosen. Tambahkan di form sebelah kiri.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {dosenList.map((d) => (
                  <div key={d.id} className="py-3 flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800">
                        {d.nama}
                        {d.gelar ? `, ${d.gelar}` : ''}
                      </h4>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">{d.identitas || 'Tanpa NIDN/NIP'}</p>
                    </div>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => {
                          setEditingDosenId(d.id!);
                          setDosenForm({ nama: d.nama, gelar: d.gelar, identitas: d.identitas });
                        }}
                        className="p-1.5 text-slate-400 hover:text-brand-600 rounded-md hover:bg-slate-100"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteDosen(d.id!)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-md hover:bg-rose-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Matkul Tab */}
      {activeSubTab === 'matkul' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 md:col-span-1">
            <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center space-x-2">
              <Plus className="w-4 h-4 text-brand-600" />
              <span>{editingMatkulId ? 'Edit Mata Kuliah' : 'Tambah Mata Kuliah'}</span>
            </h3>
            <form onSubmit={handleSaveMatkul} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Nama Mata Kuliah</label>
                <input
                  type="text"
                  value={matkulForm.nama}
                  onChange={(e) => setMatkulForm({ ...matkulForm, nama: e.target.value })}
                  placeholder="Contoh: Kecerdasan Buatan"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Kode MK (Opsional)</label>
                <input
                  type="text"
                  value={matkulForm.kode}
                  onChange={(e) => setMatkulForm({ ...matkulForm, kode: e.target.value })}
                  placeholder="Contoh: IF4012"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold transition"
                >
                  {editingMatkulId ? 'Perbarui' : 'Simpan'}
                </button>
                {editingMatkulId && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingMatkulId(null);
                      setMatkulForm({ nama: '', kode: '' });
                    }}
                    className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-medium"
                  >
                    Batal
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-5 md:col-span-2">
            <h3 className="text-sm font-bold text-slate-800 mb-4">Daftar Mata Kuliah ({matkulList.length})</h3>
            {matkulList.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">Belum ada mata kuliah terdaftar.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {matkulList.map((m) => (
                  <div key={m.id} className="py-3 flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-800">{m.nama}</h4>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">{m.kode || 'Tanpa Kode'}</p>
                    </div>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => {
                          setEditingMatkulId(m.id!);
                          setMatkulForm({ nama: m.nama, kode: m.kode });
                        }}
                        className="p-1.5 text-slate-400 hover:text-brand-600 rounded-md hover:bg-slate-100"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteMatkul(m.id!)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-md hover:bg-rose-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Logo Tab */}
      {activeSubTab === 'logo' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Koleksi Logo ({logoList.length})</h3>
              <p className="text-xs text-slate-400 mt-0.5">Logo otomatis diskalakan 5x5 cm pada template DOCX.</p>
            </div>
            <button
              onClick={handleUploadLogo}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold flex items-center space-x-2 transition"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Unggah Logo Baru</span>
            </button>
          </div>

          {logoList.length === 0 ? (
            <div className="py-12 border-2 border-dashed border-slate-200 rounded-2xl text-center">
              <ImageIcon className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-600">Belum ada logo terunggah</p>
              <p className="text-xs text-slate-400 mt-1">Dukung format PNG, JPG, JPEG, BMP</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {logoList.map((l) => (
                <div key={l.id} className="p-4 rounded-xl border border-slate-200/70 bg-slate-50 flex flex-col items-center justify-between text-center relative group">
                  <div className="w-24 h-24 flex items-center justify-center p-2 bg-white rounded-lg shadow-sm border border-slate-100 mb-3">
                    {l.exists ? (
                      <img src={`file:///${l.path.replace(/\\/g, '/')}`} alt={l.nama} className="max-w-full max-h-full object-contain" />
                    ) : (
                      <AlertCircle className="w-8 h-8 text-rose-400" />
                    )}
                  </div>
                  <span className="text-xs font-semibold text-slate-700 truncate w-full">{l.nama}</span>
                  <button
                    onClick={() => handleDeleteLogo(l.id)}
                    className="mt-3 text-xs text-rose-600 hover:text-rose-700 flex items-center space-x-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Hapus</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modal */}
      {confirmDialog && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-sm font-bold text-slate-800 mb-2">Konfirmasi Tindakan</h3>
            <p className="text-xs text-slate-600 mb-5 leading-relaxed">{confirmDialog.message}</p>
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setConfirmDialog(null)}
                className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={confirmDialog.onConfirm}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold shadow-sm transition"
              >
                Hapus
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
