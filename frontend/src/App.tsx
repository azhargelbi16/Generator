import React, { useState, useEffect } from 'react';
import { Sidebar, TabKey } from './components/Sidebar';
import { TabLaporan } from './components/TabLaporan';
import { TabReview } from './components/TabReview';
import { TabData } from './components/TabData';
import { TabTemplate } from './components/TabTemplate';
import { TabSettings } from './components/TabSettings';
import { api } from './lib/api';
import { CheckCircle2, AlertCircle, Info, Cpu, Menu, X } from 'lucide-react';
import { ToastEventDetail } from './lib/toast';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<TabKey>('laporan');
  const [unverifiedCount, setUnverifiedCount] = useState(0);
  const [aiConnected, setAiConnected] = useState(false);
  const [aiModel, setAiModel] = useState('');
  const [toastData, setToastData] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [saveState, setSaveState] = useState<'saved' | 'saving' | 'error'>('saved');

  useEffect(() => {
    checkAppStatus(true);

    const handleSaveState = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const status = detail.status;
      if (status === 'saving' || status === 'saved' || status === 'error') {
        setSaveState(status);
      }
    };

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

    const handleAiStatus = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      setAiConnected(!!detail.connected);
      if (detail.model) setAiModel(String(detail.model));
    };
    window.addEventListener('app-toast', handleToast);
    window.addEventListener('ai-status-changed', handleAiStatus);
    window.addEventListener('generator-save-state', handleSaveState);

    const handleSwitchTab = (e: Event) => {
      const tab = (e as CustomEvent).detail?.tab;
      if (tab) setCurrentTab(tab as TabKey);
    };
    window.addEventListener('switch-tab-request', handleSwitchTab);
    return () => {
      window.removeEventListener('app-toast', handleToast);
      window.removeEventListener('ai-status-changed', handleAiStatus);
      window.removeEventListener('generator-save-state', handleSaveState);
      window.removeEventListener('switch-tab-request', handleSwitchTab);
    };
  }, []);

  useEffect(() => {
    const closeMobileNavigation = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setMobileNavOpen(false);
      // Escape juga menutup dialog teratas lewat tombol tutup/batalnya,
      // standar SaaS: keyboard tetap jalan tanpa harus membidik tombol ✕.
      const dialogs = Array.from(document.querySelectorAll<HTMLElement>('[role="dialog"]'));
      const top = dialogs[dialogs.length - 1];
      if (!top) return;
      const closer = Array.from(top.querySelectorAll<HTMLElement>('button')).find((btn) => {
        const label = (btn.getAttribute('aria-label') || btn.textContent || '').trim().toLowerCase();
        return label === '✕' || label === 'batal' || label.includes('tutup') || label.includes('batal &');
      });
      if (closer) closer.click();
    };

    window.addEventListener('keydown', closeMobileNavigation);
    return () => window.removeEventListener('keydown', closeMobileNavigation);
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
    <div className="app-shell flex h-screen w-screen overflow-hidden font-sans p-3 gap-3 bg-[#EEF5F5] box-border">
      <a className="skip-link" href="#workspace">Lewati ke area kerja</a>
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
        mobileOpen={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />

      <button
        type="button"
        className={`mobile-nav-scrim ${mobileNavOpen ? 'is-visible' : ''}`}
        onClick={() => setMobileNavOpen(false)}
        aria-label="Tutup navigasi"
        tabIndex={mobileNavOpen ? 0 : -1}
      />

      <main id="workspace" className="app-main flex-1 flex flex-col h-full overflow-hidden rounded-[32px] bg-white/80 backdrop-blur-xl border border-white shadow-xl relative min-w-0" tabIndex={-1}>
        <header className="h-14 px-6 flex items-center justify-between border-b border-teal-100/70 bg-white/70 backdrop-blur-md shrink-0 z-20">
          <div className="app-header-leading">
            <button
              type="button"
              className="mobile-nav-toggle"
              onClick={() => setMobileNavOpen((open) => !open)}
              aria-expanded={mobileNavOpen}
              aria-controls="primary-navigation"
              aria-label={mobileNavOpen ? 'Tutup navigasi' : 'Buka navigasi'}
            >
              {mobileNavOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
            <div className="app-breadcrumb">
            <span className="app-kicker">RUANG KERJA</span>
            <span className="app-slash">/</span>
            <span className="app-title">Generator Laporan</span>
            <span className="app-context">alat penyusunan akademik</span>
            </div>
          </div>

          <div className="app-header-status">
            <div className={`save-state ${saveState === 'error' ? 'is-error' : ''} ${saveState === 'saving' ? 'is-saving' : ''}`} aria-label="Status penyimpanan">
              <span className="save-state-mark" aria-hidden="true" />
              <span>
                {saveState === 'saving'
                  ? 'menyimpan...'
                  : saveState === 'error'
                    ? 'gagal menyimpan — dicoba ulang'
                    : 'tersimpan otomatis'}
              </span>
            </div>
            <div className={`model-state ${aiConnected ? 'is-connected' : 'is-offline'}`}>
              <Cpu className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{aiModel || 'layanan belum dipilih'}</span>
            </div>
          </div>
        </header>

        {/* Dynamic Tab Body (Preserved / Keep-Alive) */}
        <div className="app-workspace flex-1 flex overflow-hidden relative">
          <div className={`flex-1 flex overflow-hidden h-full w-full ${currentTab === 'laporan' ? 'flex' : 'hidden'}`}>
            <TabLaporan
              isActive={currentTab === 'laporan'}
              onGenerateComplete={handleGenerateComplete}
              onGeneratingChange={setIsGeneratingReport}
              onNavigateToReview={() => setCurrentTab('review')}
            />
          </div>
          <div className={`flex-1 flex overflow-hidden h-full w-full ${currentTab === 'review' ? 'flex' : 'hidden'}`}>
            <TabReview
              isActive={currentTab === 'review'}
              onExportSuccess={handleExportSuccess}
              onNavigateToLaporan={() => setCurrentTab('laporan')}
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

        {/* Global toast notification */}
        {toastData && (
          <div
            className={`app-toast absolute bottom-6 right-6 z-50 transition-all duration-200 animate-slideUp ${toastData.type}`}
            role="status"
            aria-live="polite"
          >
            {toastData.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : toastData.type === 'info' ? (
              <Info className="w-4 h-4 text-orange-300 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-orange-300 shrink-0" />
            )}
            <span>{toastData.message}</span>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
