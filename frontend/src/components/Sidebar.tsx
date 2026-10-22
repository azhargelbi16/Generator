import React from 'react';
import { 
  FileText, 
  CheckCircle2, 
  Database, 
  FileCode2, 
  Settings, 
  Sparkles,
  Bot,
  Zap,
  ShieldCheck
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
      label: 'Studio Laporan',
      desc: 'Penyusunan & Sumber AI',
      icon: FileText,
      badge: null,
    },
    {
      key: 'review' as TabKey,
      label: 'Canvas & Review',
      desc: 'Verifikasi Kalimat Fakta',
      icon: CheckCircle2,
      badge: unverifiedCount > 0 ? unverifiedCount : null,
      badgeType: 'warning',
    },
    {
      key: 'data' as TabKey,
      label: 'Profil & Institusi',
      desc: 'Mahasiswa, Dosen, Logo',
      icon: Database,
      badge: null,
    },
    {
      key: 'template' as TabKey,
      label: 'Template Word',
      desc: 'Standar Format & Penanda',
      icon: FileCode2,
      badge: 'Resmi',
      badgeType: 'info',
    },
    {
      key: 'settings' as TabKey,
      label: 'Pengaturan AI',
      desc: 'Model, Suhu, Endpoint',
      icon: Settings,
      badge: null,
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200/80 flex flex-col justify-between select-none shrink-0 shadow-sm relative z-20">
      {/* Brand Header */}
      <div>
        <div className="p-4 border-b border-slate-100 flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h1 className="font-extrabold text-slate-900 text-sm tracking-tight leading-none">
                ACADEMIA<span className="text-blue-600">.AI</span>
              </h1>
              <span className="px-1.5 py-0.2 rounded-md bg-blue-100 text-blue-800 text-[9px] font-bold tracking-wider border border-blue-200">
                PRO
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Enterprise Report Engine</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          <div className="px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase text-slate-400">
            Navigasi Utama
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.key;
            return (
              <button
                key={item.key}
                onClick={() => onTabChange(item.key)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-left transition-all duration-150 group ${
                  isActive
                    ? 'bg-blue-50/80 text-blue-700 font-bold border-l-3 border-blue-600 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div className={`p-1.5 rounded-lg transition-colors ${
                    isActive ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500 group-hover:text-blue-600 group-hover:bg-blue-50'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold truncate leading-tight">{item.label}</div>
                    <div className={`text-[10px] truncate leading-tight mt-0.5 ${isActive ? 'text-blue-600/80 font-medium' : 'text-slate-400'}`}>
                      {item.desc}
                    </div>
                  </div>
                </div>

                {item.badge !== null && (
                  <div className="shrink-0 pl-1">
                    {item.badgeType === 'warning' ? (
                      <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                        {item.badge}
                      </span>
                    ) : (
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                        isActive ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer System Telemetry Status */}
      <div className="p-3 border-t border-slate-100 space-y-2">
        {/* Academic Standard Compliance Tag */}
        <div className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-[11px]">
          <div className="flex items-center space-x-1.5 text-slate-700">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
            <span className="font-semibold text-[11px]">Standar Dikti & APA 7</span>
          </div>
          <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
            Aktif
          </span>
        </div>

        {/* AI Engine Status Card */}
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5">
              <Bot className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-slate-800">Layanan AI</span>
            </div>
            <span className="flex items-center space-x-1.5">
              <span className={`w-2 h-2 rounded-full ${aiConnected ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
              <span className="text-[10px] font-bold text-slate-600">{aiConnected ? 'Terhubung' : 'Offline'}</span>
            </span>
          </div>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-200/60 text-[10px]">
            <span className="text-slate-500 truncate max-w-[130px] font-mono">
              {aiModel || 'gpt-4o-mini'}
            </span>
            <span className="text-blue-700 font-semibold flex items-center">
              <Zap className="w-3 h-3 mr-0.5 text-amber-500" />
              Siap
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
