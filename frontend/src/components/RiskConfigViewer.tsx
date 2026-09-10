import React, { useEffect, useState } from 'react';
import {
  Settings,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  UserCheck,
  Cpu,
  Layers,
  Terminal,
  Lock,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';
import { RiskConfig } from '../types';

export const RiskConfigViewer: React.FC = () => {
  const [config, setConfig] = useState<RiskConfig | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await api.getRiskConfig();
      setConfig(data);
    } catch (err) {
      console.error('Failed to load risk configuration:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-inner">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                Mathematical Risk Scoring Engine Parameters
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                Reproducible Formula
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Governs the multi-signal mathematical risk engine, weight distribution, and threshold boundaries.
            </p>
          </div>
        </div>

        <button
          onClick={loadConfig}
          className="p-2 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-cyan-400 transition-colors"
          title="Refresh parameters"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Formula Showcase Banner */}
      <div className="bg-[#111726] border border-cyan-500/30 rounded-xl p-5 shadow-lg shadow-cyan-950/20 bg-gradient-to-br from-cyan-950/20 to-[#111726]">
        <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2 font-mono flex items-center gap-2">
          <Cpu className="w-4 h-4" />
          <span>Universal Risk Scoring Formula</span>
        </h3>
        <div className="p-3 bg-[#0a0d14] border border-slate-800 rounded-xl text-xs font-mono text-cyan-200 overflow-x-auto">
          <code>
            RiskScore = min(100, max(0, w_res · S_res + w_tool · R_tool + w_intent · M_intent + w_anom · A_hist + Rules))
          </code>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Every risk score is deterministically reproducible from explicit signals and normalized weights. Zero magic constants.
        </p>
      </div>

      {/* Grid: Formula Weights & Thresholds */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Normalized Weights Card */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span>Normalized Signal Weights</span>
          </h3>

          <div className="space-y-3 font-mono text-xs">
            {/* Resource Sensitivity Weight */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w_res (Resource Sensitivity)</span>
                <strong className="text-cyan-400">{config?.weights.w_resource_sensitivity ?? 0.35} (35%)</strong>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div className="bg-cyan-500 h-full" style={{ width: `${(config?.weights.w_resource_sensitivity ?? 0.35) * 100}%` }}></div>
              </div>
            </div>

            {/* Task Intent Mismatch Weight */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w_intent (Intent Mismatch)</span>
                <strong className="text-cyan-400">{config?.weights.w_intent_mismatch ?? 0.35} (35%)</strong>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div className="bg-cyan-500 h-full" style={{ width: `${(config?.weights.w_intent_mismatch ?? 0.35) * 100}%` }}></div>
              </div>
            </div>

            {/* Tool Risk Weight */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w_tool (Tool Action Risk)</span>
                <strong className="text-cyan-400">{config?.weights.w_tool_risk ?? 0.20} (20%)</strong>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div className="bg-cyan-500 h-full" style={{ width: `${(config?.weights.w_tool_risk ?? 0.20) * 100}%` }}></div>
              </div>
            </div>

            {/* Anomaly Score Weight */}
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>w_anom (Agent Behavioral Drift)</span>
                <strong className="text-cyan-400">{config?.weights.w_anomaly ?? 0.10} (10%)</strong>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                <div className="bg-cyan-500 h-full" style={{ width: `${(config?.weights.w_anomaly ?? 0.10) * 100}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Decision Thresholds Card */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Authorization Threshold Boundaries</span>
          </h3>

          <div className="space-y-3 font-mono text-xs">
            {/* ALLOW Tier */}
            <div className="p-3 bg-emerald-950/30 border border-emerald-500/30 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <div>
                  <span className="font-bold text-emerald-300 block">ALLOW Tier</span>
                  <span className="text-[11px] text-slate-400">Automatic authorization</span>
                </div>
              </div>
              <span className="text-sm font-bold text-emerald-400">Score &lt; 40</span>
            </div>

            {/* ASK_HUMAN Tier */}
            <div className="p-3 bg-amber-950/30 border border-amber-500/30 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <UserCheck className="w-5 h-5 text-amber-400" />
                <div>
                  <span className="font-bold text-amber-300 block">ASK_HUMAN Tier</span>
                  <span className="text-[11px] text-slate-400">Execution paused for human review</span>
                </div>
              </div>
              <span className="text-sm font-bold text-amber-400">40 ≤ Score &lt; 70</span>
            </div>

            {/* BLOCK Tier */}
            <div className="p-3 bg-rose-950/30 border border-rose-500/30 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-5 h-5 text-rose-400" />
                <div>
                  <span className="font-bold text-rose-300 block">BLOCK Tier</span>
                  <span className="text-[11px] text-slate-400">Hard stop / access denied</span>
                </div>
              </div>
              <span className="text-sm font-bold text-rose-400">Score ≥ 70</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
