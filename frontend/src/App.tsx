import React, { useState, useEffect } from 'react';
import { Sidebar, TabKey } from './components/Sidebar';
import { TabLaporan } from './components/TabLaporan';
import { TabReview } from './components/TabReview';
import { TabData } from './components/TabData';
import { TabTemplate } from './components/TabTemplate';
import { TabSettings } from './components/TabSettings';
import { api } from './lib/api';
import { CheckCircle2, AlertCircle, Info, Cpu, Sparkles } from 'lucide-react';
import { ToastEventDetail } from './lib/toast';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<TabKey>('laporan');
  const [unverifiedCount, setUnverifiedCount] = useState(0);
  const [aiConnected, setAiConnected] = useState(false);
  const [aiModel, setAiModel] = useState('');
  const [toastData, setToastData] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  useEffect(() => {
    checkAppStatus(true);

    const handleToast = (e: Event) => {
      const customEvent = e as CustomEvent<ToastEventDetail>;
      if (customEvent.detail?.message) {
        setToastData({
          message: customEvent.detail.message,
          type: customEvent.detail.type || 'info',
        });
        setTimeout(() => setToastData(null), 5000);
      }
    };

    window.addEventListener('app-toast', handleToast);
    return () => window.removeEventListener('app-toast', handleToast);
  }, []);

  const checkAppStatus = async (checkAi = false) => {
    try {
      const cfg = await api.getConfig();
      if (cfg) {
        setAiModel(cfg.ai_model || '');
      }

      if (checkAi) {
        api.testAiConnection()
          .then((test) => {
            if (test) setAiConnected(test.ok);
          })
          .catch(() => setAiConnected(false));
      }

      // Check draft unverified count
      const draft = await api.loadActiveDraft();
      if (draft?.has_draft && draft.sections && draft.sections.length > 0) {
        const statuses = await api.verifyDocument(draft.sections, draft.sources || []);
        if (statuses) {
          const done = new Set(draft.done || []);
          const unv = statuses.filter(
            (s) => s.status === 'belum_terverifikasi' && !done.has(s.uid)
          ).length;
          setUnverifiedCount(unv);
        }
      } else {
        setUnverifiedCount(0);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleGenerateComplete = () => {
    setCurrentTab('review');
    checkAppStatus(false);
    showToast('Laporan akademik berhasil disusun oleh AI! Silakan tinjau per kalimat.', 'success');
  };

  const handleExportSuccess = (path: string) => {
    showToast(`Dokumen DOCX resmi berhasil diekspor di: ${path}`, 'success');
    checkAppStatus(false);
  };

  const showToast = (msg: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToastData({ message: msg, type });
    setTimeout(() => setToastData(null), 5000);
  };

  return (
    <div className="flex h-screen w-screen bg-slate-100 overflow-hidden font-sans select-none">
      {/* Sleek Modern Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onTabChange={(tab) => {
          setCurrentTab(tab);
          if (tab === 'review') {
            checkAppStatus(false);
          }
        }}
        unverifiedCount={unverifiedCount}
        aiConnected={aiConnected}
        aiModel={aiModel}
        isGenerating={isGeneratingReport}
      />

      {/* Main Content Workspace */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative bg-slate-50">
        {/* Top SaaS Enterprise Header */}
        <header className="h-14 bg-white border-b border-slate-200/80 px-6 flex items-center justify-between shrink-0 z-10 shadow-xs">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-semibold text-slate-400">Workspace</span>
            <span className="text-slate-300">/</span>
            <span className="text-xs font-bold text-slate-800 flex items-center gap-2">
              <span>Generator Dokumen Ilmiah</span>
              <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-bold shadow-xs">
                Standar Dikti & APA 7
              </span>
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-1.5 text-[11px] font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Simpan Otomatis Aktif</span>
            </div>

            <div className="flex items-center space-x-1.5 text-[11px] font-mono text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200 font-semibold">
              <Cpu className="w-3.5 h-3.5 text-blue-600" />
              <span>{aiModel || 'gpt-4o-mini'}</span>
            </div>
          </div>
        </header>

        {/* Dynamic Tab Body (Preserved / Keep-Alive) */}
        <div className="flex-1 flex overflow-hidden relative bg-slate-50">
          <div className={`flex-1 flex overflow-hidden h-full w-full ${currentTab === 'laporan' ? 'flex' : 'hidden'}`}>
            <TabLaporan
              isActive={currentTab === 'laporan'}
              onGenerateComplete={handleGenerateComplete}
              onGeneratingChange={setIsGeneratingReport}
            />
          </div>
          <div className={`flex-1 flex overflow-hidden h-full w-full ${currentTab === 'review' ? 'flex' : 'hidden'}`}>
            <TabReview
              isActive={currentTab === 'review'}
              onExportSuccess={handleExportSuccess}
            />
          </div>
          <div className={`flex-1 flex overflow-hidden h-full w-full ${currentTab === 'data' ? 'flex' : 'hidden'}`}>
            <TabData isActive={currentTab === 'data'} />
          </div>
          <div className={`flex-1 flex overflow-hidden h-full w-full ${currentTab === 'template' ? 'flex' : 'hidden'}`}>
            <TabTemplate isActive={currentTab === 'template'} />
          </div>
          <div className={`flex-1 flex overflow-hidden h-full w-full ${currentTab === 'settings' ? 'flex' : 'hidden'}`}>
            <TabSettings
              isActive={currentTab === 'settings'}
              onConfigSaved={() => checkAppStatus(true)}
            />
          </div>
        </div>

        {/* Global SaaS Floating Toast Notification */}
        {toastData && (
          <div
            className={`absolute bottom-6 right-6 z-50 px-4 py-3 rounded-2xl shadow-2xl flex items-center space-x-3 text-xs border backdrop-blur-xl transition-all duration-200 animate-slideUp ${
              toastData.type === 'error'
                ? 'bg-rose-950/95 text-rose-100 border-rose-800 shadow-rose-950/40'
                : toastData.type === 'info'
                ? 'bg-blue-950/95 text-blue-100 border-blue-800 shadow-blue-950/40'
                : 'bg-slate-900/95 text-white border-blue-500/40 shadow-xl'
            }`}
          >
            {toastData.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : toastData.type === 'info' ? (
              <Info className="w-4 h-4 text-sky-400 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            )}
            <span className="font-semibold text-slate-100">{toastData.message}</span>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
