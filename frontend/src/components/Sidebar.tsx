import React, { useRef } from 'react';
import {
  BookOpen,
  CheckCircle2,
  Database,
  FileCode2,
  Settings2,
  Circle,
  ShieldCheck,
  X,
} from 'lucide-react';

export type TabKey = 'laporan' | 'review' | 'data' | 'template' | 'settings';

interface SidebarProps {
  currentTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  unverifiedCount: number;
  aiConnected: boolean;
  aiModel: string;
  isGenerating?: boolean;
  mobileOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  unverifiedCount,
  aiConnected,
  aiModel,
  isGenerating = false,
  mobileOpen = false,
  onClose,
}) => {
  const navItems = [
    { key: 'laporan' as TabKey, number: '01', label: 'Studio laporan', desc: isGenerating ? 'sedang menyusun' : 'sumber dan kerangka', icon: BookOpen },
    { key: 'review' as TabKey, number: '02', label: 'Canvas & review', desc: 'baca per kalimat', icon: CheckCircle2 },
    { key: 'data' as TabKey, number: '03', label: 'Profil & institusi', desc: 'identitas akademik', icon: Database },
    { key: 'template' as TabKey, number: '04', label: 'Template Word', desc: 'format dan penanda', icon: FileCode2 },
    { key: 'settings' as TabKey, number: '05', label: 'Pengaturan AI', desc: 'endpoint dan model', icon: Settings2 },
  ];
  const activeItem = navItems.find((item) => item.key === currentTab);
  const navRef = useRef<HTMLElement>(null);

  const moveFocus = (currentKey: TabKey, direction: 1 | -1 | 'start' | 'end') => {
    const currentIndex = navItems.findIndex((item) => item.key === currentKey);
    const nextIndex = direction === 'start'
      ? 0
      : direction === 'end'
        ? navItems.length - 1
        : (currentIndex + direction + navItems.length) % navItems.length;
    navRef.current?.querySelector<HTMLButtonElement>(`[data-nav-key="${navItems[nextIndex].key}"]`)?.focus();
  };

  return (
    <aside
      id="primary-navigation"
      className={`app-sidebar shrink-0 select-none relative z-20 ${mobileOpen ? 'is-mobile-open' : ''}`}
      aria-label="Navigasi utama"
    >
      <div className="sidebar-top">
        <button type="button" className="mobile-sidebar-close" onClick={onClose} aria-label="Tutup navigasi">
          <X className="w-4 h-4" />
        </button>
        <div className="wordmark" aria-label="Generator Laporan">
          <div className="wordmark-rule" aria-hidden="true" />
          <div>
            <div className="wordmark-name">GENERATOR</div>
            <div className="wordmark-subtitle">laporan akademik</div>
          </div>
        </div>

        <div className="sidebar-intro">
          <span className="sidebar-intro-label">MEJA KERJA AKADEMIK</span>
          <p>Kumpulkan sumber, bentuk outline, lalu periksa naskah tanpa kehilangan jejak.</p>
        </div>

        <nav ref={navRef} className="sidebar-nav" aria-label="Tahap kerja laporan">
          <div className="sidebar-section-heading">
            <span className="sidebar-section-label">ALUR KERJA</span>
            <span className="sidebar-section-count">{navItems.length} tahap</span>
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.key;
            const hasReviewWarning = item.key === 'review' && unverifiedCount > 0;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => {
                  onTabChange(item.key);
                  onClose?.();
                }}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
                    event.preventDefault();
                    moveFocus(item.key, 1);
                  }
                  if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
                    event.preventDefault();
                    moveFocus(item.key, -1);
                  }
                  if (event.key === 'Home') {
                    event.preventDefault();
                    moveFocus(item.key, 'start');
                  }
                  if (event.key === 'End') {
                    event.preventDefault();
                    moveFocus(item.key, 'end');
                  }
                }}
                data-nav-key={item.key}
                aria-current={isActive ? 'page' : undefined}
                aria-label={`${item.label}, ${item.desc}`}
                className={`sidebar-nav-item ${isActive ? 'is-active' : ''}`}
              >
                <span className="sidebar-nav-number">{item.number}</span>
                <span className="sidebar-nav-icon" aria-hidden="true"><Icon className="w-4 h-4" /></span>
                <span className="sidebar-nav-copy">
                  <span className="sidebar-nav-label">{item.label}</span>
                  <span className="sidebar-nav-desc">{item.desc}</span>
                </span>
                {hasReviewWarning && <span className="sidebar-count">{unverifiedCount}</span>}
                {item.key === 'template' && <span className="sidebar-status">siap</span>}
                {item.key === 'laporan' && isGenerating && <span className="sidebar-live">aktif</span>}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-focus-card" aria-live="polite">
          <div className="sidebar-focus-top">
            <span className="sidebar-focus-label">AKTIF SEKARANG</span>
            <span className={`sidebar-focus-pulse ${isGenerating ? 'is-live' : ''}`} aria-hidden="true" />
          </div>
          <strong>{activeItem?.label}</strong>
          <span>{isGenerating ? 'AI sedang menyusun draf dari sumber aktif.' : activeItem?.desc}</span>
          <div className="sidebar-focus-meta">
            <span>{activeItem?.number} / {navItems.length}</span>
            <span>{isGenerating ? 'menyusun' : 'siap dipakai'}</span>
          </div>
        </div>
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-standard">
          <div className="sidebar-standard-icon" aria-hidden="true"><ShieldCheck className="w-3.5 h-3.5" /></div>
          <div>
            <div className="sidebar-standard-title">Ruang akademik</div>
            <div className="sidebar-standard-copy">APA 7 dan template lokal</div>
          </div>
        </div>

        <div className="sidebar-ai">
          <div className="sidebar-ai-head">
            <span className="sidebar-section-label">LAYANAN AI</span>
            <span className={`sidebar-ai-status ${aiConnected ? 'is-connected' : 'is-offline'}`}>
              <Circle className="w-2.5 h-2.5 fill-current" aria-hidden="true" />
              {aiConnected ? 'terhubung' : 'offline'}
            </span>
          </div>
          <div className="sidebar-ai-model">{aiModel || 'pilih endpoint di pengaturan'}</div>
        </div>
      </div>
    </aside>
  );
};
