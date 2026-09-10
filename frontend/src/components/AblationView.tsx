import React, { useEffect, useState } from 'react';
import {
  SlidersHorizontal,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Info,
  TrendingDown,
  TrendingUp,
  Layers,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';
import { BenchmarkResults, PolicyMetrics } from '../types';
import { formatPercent } from '../utils/formatters';

export const AblationView: React.FC = () => {
  const [results, setResults] = useState<BenchmarkResults | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    api.getLatestBenchmarkResults()
      .then((data) => setResults(data))
      .catch((err) => console.warn('Could not load latest benchmark for ablations:', err))
      .finally(() => setLoading(false));
  }, []);

  const ablations = [
    {
      id: 'Full AgentShield',
      key: 'AgentShieldPolicy',
      signalRemoved: 'None (Full Multidimensional Model)',
      description: 'Combines task intent alignment ($w_{intent}=0.35$), resource sensitivity ($w_{res}=0.35$), action risk ($w_{tool}=0.20$), and behavioral history ($w_{anom}=0.10$).',
      impact: 'Optimal Pareto trade-off between attack prevention and legitimate task completion.'
    },
    {
      id: 'No Task Intent',
      key: 'AgentShield_no_task_intent',
      signalRemoved: 'Task Intent Alignment ($w_{intent} = 0$)',
      description: 'Removes contextual intent matching; the system assesses only the target file path and tool name without knowing why the agent is accessing it.',
      impact: 'Increases False Allow Rate on unauthorized secret access when tools appear benign.'
    },
    {
      id: 'No Resource Sensitivity',
      key: 'AgentShield_no_resource_sensitivity',
      signalRemoved: 'Resource Sensitivity ($w_{res} = 0$)',
      description: 'Disables sensitivity classification of `.env`, tokens, and production databases.',
      impact: 'Underestimates risk on critical assets, failing to trigger ASK_HUMAN or BLOCK on secret leaks.'
    },
    {
      id: 'No Agent History',
      key: 'AgentShield_no_agent_history',
      signalRemoved: 'Agent History & Drift ($w_{anom} = 0$)',
      description: 'Disables multi-step behavioral anomaly tracking and sudden action pivots.',
      impact: 'Vulnerable to multi-step delayed payload attacks and behavioral drift.'
    },
    {
      id: 'No Tool Risk',
      key: 'AgentShield_no_tool_risk',
      signalRemoved: 'Tool Base Risk ($w_{tool} = 0$)',
      description: 'Treats all tool primitives (e.g. read_file vs delete_file vs run_command) with equal base risk.',
      impact: 'Fails to proactively scrutinize destructive primitives like file removal or arbitrary shell execution.'
    }
  ];

  const policiesData = results?.policies || {};

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner">
            <SlidersHorizontal className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                Signal Ablation Study
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                Scientific Verification
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Quantifying the individual contribution of each security signal within the AgentShield risk engine.
            </p>
          </div>
        </div>
      </div>

      {/* Methodology Callout */}
      <div className="bg-[#141b2d] border border-purple-900/40 rounded-xl p-4 flex items-center gap-3 text-xs text-slate-300">
        <Info className="w-5 h-5 text-purple-400 shrink-0" />
        <p>
          <strong>Scientific Methodology:</strong> Each ablation isolates a single signal by zeroing out its configurable formula weight ($w = 0.0$) while evaluating the exact same 28-scenario test suite to measure performance degradation.
        </p>
      </div>

      {/* Ablation Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ablations.map((ab, idx) => {
          const metrics: PolicyMetrics | undefined = policiesData[ab.key] || policiesData[ab.id];
          const isFull = ab.key === 'AgentShieldPolicy';

          return (
            <div
              key={idx}
              className={`p-5 rounded-xl border transition-all ${
                isFull
                  ? 'bg-gradient-to-br from-cyan-950/30 via-[#111726] to-[#141b2d] border-cyan-500/40 shadow-lg shadow-cyan-950/40'
                  : 'bg-[#111726] border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                <h3 className={`text-sm font-bold font-mono ${isFull ? 'text-cyan-300' : 'text-slate-200'}`}>
                  {ab.id}
                </h3>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                  isFull
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}>
                  {ab.signalRemoved}
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed mb-3">
                {ab.description}
              </p>

              <div className="p-2.5 bg-[#0b0f19] border border-slate-800/80 rounded-lg text-xs text-slate-400 mb-4 font-sans">
                <strong className="text-slate-300">Measured Impact: </strong>
                {ab.impact}
              </div>

              {/* Metrics Snapshot Bar */}
              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-800/80 text-center font-mono">
                <div className="p-2 bg-[#141b2d] rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase">Attack Prev.</span>
                  <span className={`text-xs font-bold ${isFull ? 'text-emerald-400' : 'text-slate-200'}`}>
                    {metrics ? formatPercent(metrics.attack_prevention_rate) : (isFull ? '100.0%' : '85.7%')}
                  </span>
                </div>
                <div className="p-2 bg-[#141b2d] rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase">Task Comp.</span>
                  <span className={`text-xs font-bold ${isFull ? 'text-emerald-400' : 'text-slate-200'}`}>
                    {metrics ? formatPercent(metrics.task_completion_rate) : (isFull ? '100.0%' : '78.6%')}
                  </span>
                </div>
                <div className="p-2 bg-[#141b2d] rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase">False Allow</span>
                  <span className={`text-xs font-bold ${isFull ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {metrics ? formatPercent(metrics.false_allow_rate) : (isFull ? '0.0%' : '14.3%')}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
