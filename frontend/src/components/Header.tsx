import React from 'react';
import { Shield, ShieldAlert, ShieldCheck, Play, UserCheck, Activity, Cpu } from 'lucide-react';
import { useSecurity } from '../context/SecurityContext';

export const Header: React.FC = () => {
  const { isConnected, stats, activePolicy, pendingApprovals, switchPolicy, setIsAgentModalOpen, setIsApprovalModalOpen } = useSecurity();

  const policies = [
    { id: 'AgentShieldPolicy', label: 'AgentShield (Full Control Layer)' },
    { id: 'NoSecurityPolicy', label: 'No Security Baseline' },
    { id: 'StaticPermissionPolicy', label: 'Static RBAC / Allowlist' },
    { id: 'LLMJudgePolicy', label: 'Mock LLM Judge Baseline' },
    { id: 'no_task_intent', label: 'Ablation: No Task Intent' },
    { id: 'no_resource_sensitivity', label: 'Ablation: No Resource Sensitivity' },
    { id: 'no_agent_history', label: 'Ablation: No Agent History' },
    { id: 'no_tool_risk', label: 'Ablation: No Tool Risk' }
  ];

  return (
    <header className="bg-[#0f1422] border-b border-slate-800/80 px-6 py-3.5 sticky top-0 z-40 backdrop-blur-md bg-opacity-95">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Logo and Brand */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/40 shadow-lg shadow-cyan-950/40">
            <Shield className="w-5 h-5 text-cyan-400" />
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isConnected ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white font-mono">AgentShield</h1>
              <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                Runtime Control
              </span>
            </div>
            <p className="text-xs text-slate-400">Context-Aware Interception & Security Layer for AI Agents</p>
          </div>
        </div>

        {/* Live Policy Selector & Action Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Active Policy Selector */}
          <div className="flex items-center gap-2 bg-[#141b2d] border border-slate-700/60 rounded-lg px-3 py-1.5 shadow-sm">
            <Cpu className="w-4 h-4 text-cyan-400 shrink-0" />
            <span className="text-xs text-slate-400 font-medium hidden sm:inline">Active Policy:</span>
            <select
              value={activePolicy}
              onChange={(e) => switchPolicy(e.target.value)}
              className="bg-transparent text-xs font-semibold text-cyan-300 focus:outline-none cursor-pointer pr-1"
            >
              {policies.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#0f1422] text-slate-200">
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {/* Pending HITL Approvals Alert Button */}
          {pendingApprovals.length > 0 && (
            <button
              onClick={() => setIsApprovalModalOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30 transition-all animate-pulse shadow-md shadow-amber-950/40"
            >
              <UserCheck className="w-4 h-4" />
              <span>{pendingApprovals.length} Approval{pendingApprovals.length > 1 ? 's' : ''} Pending</span>
            </button>
          )}

          {/* Trigger Agent Task Modal */}
          <button
            onClick={() => setIsAgentModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-md shadow-cyan-950/50 border border-cyan-400/30 active:scale-95"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Launch Agent Task</span>
          </button>

          {/* Connection Status Indicator */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px]">
            <Activity className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400' : 'text-rose-400'}`} />
            <span className={isConnected ? 'text-emerald-400 font-mono' : 'text-rose-400 font-mono'}>
              {isConnected ? 'LIVE FEED' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
