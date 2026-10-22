import React, { useState, useEffect } from 'react';
import { Sidebar, TabKey } from './components/Sidebar';
import { TabLaporan } from './components/TabLaporan';
import { TabReview } from './components/TabReview';
import { TabData } from './components/TabData';
import { TabTemplate } from './components/TabTemplate';
import { TabSettings } from './components/TabSettings';
import { api } from './lib/api';
import { CheckCircle2 } from 'lucide-react';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<TabKey>('laporan');
  const [unverifiedCount, setUnverifiedCount] = useState(0);
  const [aiConnected, setAiConnected] = useState(false);
  const [aiModel, setAiModel] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    checkAppStatus(true);
  }, []);

  const checkAppStatus = async (checkAi = false) => {
    try {
      const cfg = await api.getConfig();
      if (cfg) {
        setAiModel(cfg.ai_model || '');
      }

      if (checkAi) {
        // Fire in background so UI renders instantly without waiting for network probe
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
    showToast('Laporan berhasil disusun oleh AI! Silakan tinjau per kalimat.');
  };

  const handleExportSuccess = (path: string) => {
    showToast(`Dokumen DOCX berhasil disimpan di: ${path}`);
    checkAppStatus(false);
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 5000);
  };

  return (
    <div className="flex h-screen w-screen bg-slate-100 overflow-hidden font-sans">
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
      />
      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {currentTab === 'laporan' && (
          <TabLaporan onGenerateComplete={handleGenerateComplete} />
        )}
        {currentTab === 'review' && (
          <TabReview onExportSuccess={handleExportSuccess} />
        )}
        {currentTab === 'data' && <TabData />}
        {currentTab === 'template' && <TabTemplate />}
        {currentTab === 'settings' && (
          <TabSettings onConfigSaved={() => checkAppStatus(true)} />
        )}

        {/* Global Toast Notification */}
        {toastMessage && (
          <div className="absolute bottom-6 right-6 z-50 bg-slate-900 text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center space-x-3 text-xs border border-slate-700 animate-slideUp">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="font-medium">{toastMessage}</span>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
