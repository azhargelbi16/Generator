import React from 'react';
import { 
  FileText, 
  CheckCircle2, 
  Database, 
  FileCode2, 
  Settings, 
  Sparkles,
  Bot
} from 'lucide-react';

export type TabKey = 'laporan' | 'review' | 'data' | 'template' | 'settings';

interface SidebarProps {
  currentTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  unverifiedCount: number;
  aiConnected: boolean;
  aiModel: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  unverifiedCount,
  aiConnected,
  aiModel,
}) => {
  const navItems = [
    {
      key: 'laporan' as TabKey,
      label: 'Buat Laporan',
      icon: FileText,
      badge: null,
    },
    {
      key: 'review' as TabKey,
      label: 'Review Hasil',
      icon: CheckCircle2,
      badge: unverifiedCount > 0 ? unverifiedCount : null,
    },
    {
      key: 'data' as TabKey,
      label: 'Data & Profil',
      icon: Database,
      badge: null,
    },
    {
      key: 'template' as TabKey,
      label: 'Template Word',
      icon: FileCode2,
      badge: null,
    },
    {
      key: 'settings' as TabKey,
      label: 'Pengaturan AI',
      icon: Settings,
      badge: null,
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between select-none shrink-0 shadow-sm">
      {/* App Header */}
      <div>
        <div className="p-5 border-b border-slate-100 flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-700 to-brand-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-semibold text-slate-800 text-sm tracking-tight leading-none">Generator Laporan</h1>
            <p className="text-[11px] text-slate-400 mt-1 font-medium">Akademik & Sitasi APA 7</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.key;
            return (
              <button
                key={item.key}
                onClick={() => onTabChange(item.key)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-brand-50 text-brand-800 font-semibold shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-brand-600' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== null && (
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* AI Status Card */}
      <div className="p-3 border-t border-slate-100">
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Bot className="w-4 h-4 text-slate-500" />
              <span className="text-xs font-semibold text-slate-700">Layanan AI</span>
            </div>
            <span className="flex items-center space-x-1.5">
              <span className={`w-2 h-2 rounded-full ${aiConnected ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
              <span className="text-[11px] font-medium text-slate-500">{aiConnected ? 'Terhubung' : 'Offline'}</span>
            </span>
          </div>
          <p className="text-[11px] text-slate-500 truncate mt-1.5 font-mono">
            {aiModel || 'gpt-4o-mini'}
          </p>
        </div>
      </div>
    </aside>
  );
};
