import React, { useRef } from 'react';
import {
  BookOpen,
  CheckCircle2,
  GraduationCap,
  FileCode2,
  Settings2,
  HelpCircle,
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
    { key: 'laporan' as TabKey, number: '01', label: 'Studio Laporan', desc: isGenerating ? 'sedang menyusun...' : 'sumber & outline', icon: BookOpen },
    { key: 'review' as TabKey, number: '02', label: 'Canvas & Review', desc: 'baca per kalimat A4', icon: CheckCircle2 },
    { key: 'data' as TabKey, number: '03', label: 'Profil & Institusi', desc: 'identitas mahasiswa & dosen', icon: GraduationCap },
    { key: 'template' as TabKey, number: '04', label: 'Template Word', desc: 'format .docx & penanda', icon: FileCode2 },
    { key: 'settings' as TabKey, number: '05', label: 'Pengaturan AI', desc: 'model & endpoint', icon: Settings2 },
  ];

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
      ref={navRef}
      className={`w-[74px] bg-white/95 backdrop-blur-xl rounded-[38px] border border-white flex flex-col items-center justify-between py-5 shrink-0 shadow-lg min-h-0 z-30 select-none transition-transform duration-200 ${
        mobileOpen ? 'translate-x-0' : 'max-md:-translate-x-full'
      }`}
      aria-label="Navigasi utama"
    >
      {/* Top: Hatsune Miku Avatar Badge */}
      <div className="flex flex-col items-center space-y-1">
        <button
          type="button"
          onClick={() => {
            onTabChange('laporan');
            onClose?.();
          }}
          className="relative group cursor-pointer focus:outline-none"
          title="Generator Laporan — Hatsune Miku Studio Edition"
        >
          <div className="w-12 h-12 rounded-full ring-2 ring-[#39C5BB] p-0.5 shadow-sm overflow-hidden bg-teal-50 transition-transform duration-200 group-hover:scale-105">
            <img
              src="/assets/miku_avatar.png"
              alt="Hatsune Miku Avatar"
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback icon if image path differs
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          </div>
          <span className="absolute -bottom-1 -right-1 px-1.5 py-0.2 bg-[#39C5BB] text-white text-[10px] font-mono font-extrabold rounded-full shadow-xs">
            01
          </span>
        </button>
        <span className="text-[10px] font-bold text-teal-800 tracking-tighter">MIKU</span>
      </div>

      {/* Middle: 5 Navigation Dock Buttons */}
      <nav className="flex flex-col items-center space-y-3 w-full my-auto" aria-label="Alur kerja laporan">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.key;
          const hasReviewWarning = item.key === 'review' && unverifiedCount > 0;

          return (
            <button
              key={item.key}
              type="button"
              data-nav-key={item.key}
              aria-current={isActive ? 'page' : undefined}
              aria-label={`${item.label}, ${item.desc}`}
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
              className={`w-11 h-11 rounded-full flex items-center justify-center transition-all duration-200 relative group cursor-pointer ${
                isActive
                  ? 'bg-[#39C5BB] text-white shadow-md shadow-teal-500/20'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200'
              }`}
            >
              <Icon className="w-5 h-5" />

              {/* Warning badge for review */}
              {hasReviewWarning && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-500 text-white text-[10px] font-bold flex items-center justify-center shadow-xs">
                  {unverifiedCount}
                </span>
              )}

              {/* Pulsing live badge for active report generation */}
              {item.key === 'laporan' && isGenerating && (
                <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 animate-ping" />
              )}

              {/* Floating Tooltip Pill */}
              <div className="absolute left-14 px-3 py-1.5 bg-slate-900 text-white text-xs font-bold rounded-xl shadow-xl whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 flex flex-col">
                <span>{item.number} {item.label}</span>
                <span className="text-[10px] font-normal text-slate-300">{item.desc}</span>
              </div>
            </button>
          );
        })}
      </nav>

      {/* Bottom: Connection Status & Help */}
      <div className="flex flex-col items-center space-y-2.5">
        <div
          className="flex items-center space-x-1 cursor-pointer"
          title={`Status AI: ${aiConnected ? 'Terhubung (' + (aiModel || 'Gemini 2.5') + ')' : 'Offline'}`}
        >
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              aiConnected ? 'bg-[#39C5BB] animate-pulse shadow-xs shadow-teal-400' : 'bg-slate-400'
            }`}
          />
        </div>

        <button
          type="button"
          onClick={() => {
            alert('Generator Laporan Akademik v2.5 — Hatsune Miku Studio Edition.\nLengkap dengan profil mahasiswa, data dosen pembimbing, template Word, dan verifikasi APA 7.');
          }}
          className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 text-xs font-extrabold flex items-center justify-center transition"
          aria-label="Informasi aplikasi"
        >
          <HelpCircle className="w-4 h-4" />
        </button>
      </div>
    </aside>
  );
};
