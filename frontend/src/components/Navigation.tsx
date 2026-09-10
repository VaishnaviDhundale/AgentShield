import React from 'react';
import {
  LayoutDashboard,
  Radio,
  ScanEye,
  UserCheck,
  BarChart3,
  SlidersHorizontal,
  FolderTree,
  Settings
} from 'lucide-react';
import { useSecurity } from '../context/SecurityContext';

export type TabType = 'overview' | 'feed' | 'inspector' | 'approvals' | 'evaluation' | 'ablation' | 'sandbox' | 'config';

interface NavigationProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ activeTab, setActiveTab }) => {
  const { pendingApprovals, events } = useSecurity();

  const navItems: { id: TabType; label: string; icon: React.ReactNode; badge?: number }[] = [
    { id: 'overview', label: 'Security Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'feed', label: 'Live Activity Feed', icon: <Radio className="w-4 h-4" />, badge: events.length > 0 ? events.length : undefined },
    { id: 'inspector', label: 'Request Inspector', icon: <ScanEye className="w-4 h-4" /> },
    { id: 'approvals', label: 'Human Approval Center', icon: <UserCheck className="w-4 h-4" />, badge: pendingApprovals.length > 0 ? pendingApprovals.length : undefined },
    { id: 'evaluation', label: 'Evaluation Center', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'ablation', label: 'Ablation View', icon: <SlidersHorizontal className="w-4 h-4" /> },
    { id: 'sandbox', label: 'Sandbox Explorer', icon: <FolderTree className="w-4 h-4" /> },
    { id: 'config', label: 'Risk Engine Settings', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <nav className="bg-[#0b0f19] border-b border-slate-800/80 px-6">
      <div className="max-w-7xl mx-auto flex items-center gap-1 overflow-x-auto scrollbar-none py-2">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-950/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge !== undefined && (
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                    item.id === 'approvals'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'bg-cyan-500/20 text-cyan-300'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
