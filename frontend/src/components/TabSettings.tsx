import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Key, 
  Thermometer, 
  Globe, 
  Save, 
  RefreshCw, 
  Eye, 
  EyeOff, 
  CheckCircle2, 
  AlertCircle,
  GraduationCap,
  Search
} from 'lucide-react';
import { api, AppConfig } from '../lib/api';
import { toast } from '../lib/toast';

interface TabSettingsProps {
  onConfigSaved: () => void;
  isActive?: boolean;
}

export const TabSettings: React.FC<TabSettingsProps> = ({ onConfigSaved, isActive = false }) => {
  const [config, setConfig] = useState<AppConfig>({
    ai_base_url: 'http://localhost:1234/v1',
    ai_api_key: '',
    ai_model: 'gpt-4o-mini',
    ai_temperature: 0.2,
    citation_style: 'et_al',
    dosen_review: false,
  });

  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [models, setModels] = useState<string[]>([]);
  const [modelSearch, setModelSearch] = useState('');
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    if (isActive) {
      loadConfig();
    }
  }, [isActive]);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const res = await api.getConfig();
      if (res) {
        setConfig(res);
      }
    } catch (e) {
      console.error('Failed to load config:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const res = await api.saveConfig(config);
      if (res?.success) {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
        onConfigSaved();
      }
    } catch (e: any) {
      toast.error('Gagal menyimpan konfigurasi: ' + (e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testAiConnection(config.ai_base_url, config.ai_api_key, config.ai_model);
      if (res) {
        setTestResult(res);
        // Status sidebar jangan menggantung stale: umumkan hasil tes terbaru.
        window.dispatchEvent(new CustomEvent('ai-status-changed', {
          detail: { connected: !!res.ok, model: config.ai_model },
        }));
      }
    } catch (e: any) {
      setTestResult({ ok: false, message: e.message || 'Koneksi gagal.' });
    } finally {
      setTesting(false);
    }
  };

  const handleFetchModels = async () => {
    setFetchingModels(true);
    try {
      const res = await api.fetchModels(config.ai_base_url, config.ai_api_key);
      if (res?.ok && res.models?.length > 0) {
        setModels(res.models);
        if (!res.models.includes(config.ai_model)) {
          setConfig((prev) => ({ ...prev, ai_model: res.models[0] }));
        }
      } else {
        toast.error(res?.error || 'Tidak ada model ditemukan dari endpoint.');
      }
    } catch (e: any) {
      toast.error('Gagal mengambil daftar model: ' + e.message);
    } finally {
      setFetchingModels(false);
    }
  };

  const filteredModels = models.filter((m) =>
    m.toLowerCase().includes(modelSearch.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto utility-studio">
      <div className="mb-6 utility-header">
        <h2 className="text-xl font-bold text-slate-800 tracking-tight">Pengaturan Layanan AI</h2>
        <p className="text-sm text-slate-500 mt-1">
          Hubungkan aplikasi ke penyedia AI lokal (LM Studio, Ollama) atau layanan cloud (OpenAI, OpenRouter).
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden p-6 space-y-6">
        {/* Base URL */}
        <div>
          <label htmlFor="ai-base-url" className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
            Base URL Endpoint (OpenAI-compatible)
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Globe className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
              <input
                id="ai-base-url"
                type="text"
                value={config.ai_base_url}
                onChange={(e) => setConfig({ ...config, ai_base_url: e.target.value })}
                placeholder="http://localhost:1234/v1"
                className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono"
              />
            </div>
            <button
              onClick={handleTestConnection}
              disabled={testing}
              className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-medium transition-all flex items-center space-x-2 shrink-0 border border-slate-200"
            >
              <RefreshCw className={`w-4 h-4 ${testing ? 'animate-spin' : ''}`} />
              <span>{testing ? 'Menguji...' : 'Tes Koneksi'}</span>
            </button>
          </div>

          {/* Quick presets */}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="text-[11px] text-slate-400">Preset cepat:</span>
            {[
              { label: '9Router (Lokal)', url: 'http://localhost:20128/v1' },
              { label: 'LM Studio', url: 'http://localhost:1234/v1' },
              { label: 'Ollama', url: 'http://localhost:11434/v1' },
              { label: 'OpenAI', url: 'https://api.openai.com/v1' },
              { label: 'OpenRouter', url: 'https://openrouter.ai/api/v1' },
            ].map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => setConfig({ ...config, ai_base_url: p.url })}
                className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-600 transition"
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Test Result Alert */}
          {testResult && (
            <div
              className={`mt-3 p-3 rounded-xl flex items-start space-x-2.5 text-xs ${
                testResult.ok
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              {testResult.ok ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              )}
              <span>{testResult.message}</span>
            </div>
          )}
        </div>

        {/* API Key */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="ai-api-key" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
              API Key (Opsional untuk LLM Lokal)
            </label>
            {config.ai_api_key_set && (
              <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                ✓ Tersimpan di Sistem
              </span>
            )}
          </div>
          <div className="relative">
            <Key className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
            <input
              id="ai-api-key"
              type={showKey ? 'text' : 'password'}
              value={config.ai_api_key}
              onChange={(e) => setConfig({ ...config, ai_api_key: e.target.value })}
              placeholder={config.ai_api_key_set ? "•••••••• (Tersimpan - Kosongkan jika tidak ingin mengubah)" : "sk-..."}
              className="w-full pl-9 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-3 text-slate-400 hover:text-slate-600"
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            Disimpan secara lokal di data/config.json. API key selalu diredaksi dari file log.
          </p>
        </div>

        {/* Model & Fetch */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="flex justify-between items-center mb-2">
              <label htmlFor="ai-model" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                Nama Model AI
              </label>
              <button
                type="button"
                onClick={handleFetchModels}
                disabled={fetchingModels}
                className="text-xs text-brand-700 hover:text-brand-800 font-semibold flex items-center space-x-1"
              >
                <RefreshCw className={`w-3 h-3 ${fetchingModels ? 'animate-spin' : ''}`} />
                <span>Ambil Model dari Server</span>
              </button>
            </div>
            {models.length > 0 ? (
              <div className="space-y-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={modelSearch}
                    onChange={(e) => setModelSearch(e.target.value)}
                    placeholder={`Cari dari ${models.length} model...`}
                    className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <select
                  value={config.ai_model}
                  onChange={(e) => setConfig({ ...config, ai_model: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 font-mono"
                  size={models.length > 10 ? 5 : undefined}
                >
                  {filteredModels.map((m) => (
                    <option key={m} value={m} className="py-1">
                      {m}
                    </option>
                  ))}
                </select>
                <div className="flex justify-between items-center text-[11px] text-slate-400">
                  <span>{filteredModels.length} model ditemukan</span>
                  <button
                    type="button"
                    onClick={() => {
                      setModels([]);
                      setModelSearch('');
                    }}
                    className="text-slate-500 hover:text-slate-700 underline"
                  >
                    Input manual
                  </button>
                </div>
              </div>
            ) : (
              <div className="relative">
                <Bot className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                <input
                  id="ai-model"
                  type="text"
                  value={config.ai_model}
                  onChange={(e) => setConfig({ ...config, ai_model: e.target.value })}
                  placeholder="gpt-4o-mini"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-mono"
                />
              </div>
            )}
          </div>

          {/* Temperature Slider */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                Temperatur ({config.ai_temperature})
              </label>
              <span className="text-[11px] text-slate-400">
                {config.ai_temperature <= 0.3 ? 'Sangat Faktual (Cocok Akademik)' : 'Lebih Kreatif'}
              </span>
            </div>
            <div className="flex items-center space-x-3 mt-3">
              <Thermometer className="w-4 h-4 text-slate-400" />
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.ai_temperature}
                onChange={(e) => setConfig({ ...config, ai_temperature: parseFloat(e.target.value) })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
              />
              <span className="font-mono text-sm font-semibold w-10 text-right text-slate-700">
                {config.ai_temperature}
              </span>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 pt-5 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Citation Style */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
              Gaya Singkatan Penulis (APA 7)
            </label>
            <div className="flex gap-3">
              <label className="flex items-center space-x-2 text-sm text-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="citation_style"
                  checked={config.citation_style === 'et_al'}
                  onChange={() => setConfig({ ...config, citation_style: 'et_al' })}
                  className="accent-brand-600"
                />
                <span>Internasional: <em>(Santoso et al., 2024)</em></span>
              </label>
              <label className="flex items-center space-x-2 text-sm text-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="citation_style"
                  checked={config.citation_style === 'dkk'}
                  onChange={() => setConfig({ ...config, citation_style: 'dkk' })}
                  className="accent-brand-600"
                />
                <span>Bahasa Indonesia: <em>(Santoso dkk., 2024)</em></span>
              </label>
            </div>
          </div>

          {/* Dosen Review Checkbox */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
              Mode Review Dosen (AI Advisor)
            </label>
            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={config.dosen_review}
                onChange={(e) => setConfig({ ...config, dosen_review: e.target.checked })}
                className="w-4 h-4 mt-0.5 rounded accent-brand-600"
              />
              <div className="text-xs">
                <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <GraduationCap className="w-3.5 h-3.5 text-brand-600" />
                  Aktifkan Catatan Kritis Dosen Otomatis
                </span>
                <p className="text-slate-400 mt-0.5">
                  AI akan memberikan catatan kritis pembimbing (kelemahan argumen & potensi pertanyaan penguji) di panel samping review.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Save Bar */}
        <div className="border-t border-slate-100 pt-5 flex items-center justify-between">
          <div>
            {saveSuccess && (
              <span className="text-xs font-semibold text-emerald-600 flex items-center space-x-1">
                <CheckCircle2 className="w-4 h-4" />
                <span>Pengaturan berhasil disimpan!</span>
              </span>
            )}
          </div>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-6 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-brand-600/20 transition flex items-center space-x-2"
          >
            <Save className="w-4 h-4" />
            <span>{loading ? 'Menyimpan...' : 'Simpan Pengaturan'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
