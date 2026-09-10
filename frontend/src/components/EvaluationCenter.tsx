import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  Play,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  Zap,
  DollarSign,
  UserCheck,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Layers
} from 'lucide-react';
import { api } from '../services/api';
import { BenchmarkResults, PolicyMetrics, ScenarioItem } from '../types';
import { formatPercent, formatLatency } from '../utils/formatters';

export const EvaluationCenter: React.FC = () => {
  const [results, setResults] = useState<BenchmarkResults | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningExperiment, setRunningExperiment] = useState<boolean>(false);
  const [activeSubTab, setActiveSubTab] = useState<'metrics' | 'scenarios'>('metrics');

  const loadLatestResults = async () => {
    setLoading(true);
    try {
      const data = await api.getLatestBenchmarkResults();
      setResults(data);
    } catch (err) {
      console.warn('No existing benchmark runs found:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadScenarios = async () => {
    try {
      const list = await api.getScenarios();
      setScenarios(list);
    } catch (err) {
      console.error('Failed to fetch scenario dataset:', err);
    }
  };

  useEffect(() => {
    loadLatestResults();
    loadScenarios();
  }, []);

  const handleTriggerBenchmark = async () => {
    setRunningExperiment(true);
    try {
      const newResults = await api.runBenchmark({
        policies: [
          'NoSecurityPolicy',
          'StaticPermissionPolicy',
          'LLMJudgePolicy',
          'AgentShieldPolicy'
        ],
        trials: 1,
        hitl_mode: 'ideal'
      });
      setResults(newResults);
    } catch (err) {
      console.error('Failed to run benchmark experiment:', err);
    } finally {
      setRunningExperiment(false);
    }
  };

  const policiesData = results?.policies || {};
  const policyKeys = ['NoSecurityPolicy', 'StaticPermissionPolicy', 'LLMJudgePolicy', 'AgentShieldPolicy'];

  const getPolicyDisplayName = (key: string): string => {
    switch (key) {
      case 'NoSecurityPolicy':
        return 'No Security Baseline';
      case 'StaticPermissionPolicy':
        return 'Static RBAC / Allowlist';
      case 'LLMJudgePolicy':
        return 'Mock LLM Judge Baseline';
      case 'AgentShieldPolicy':
        return 'AgentShield (Full Control Layer)';
      default:
        return key;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner & Trigger Action */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-inner">
            <BarChart3 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                Comparative Scientific Evaluation Center
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                28-Scenario Benchmark
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Empirical evaluation comparing AgentShield against standard baselines across standardized security &amp; utility metrics.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          <button
            disabled={runningExperiment}
            onClick={loadLatestResults}
            className="p-2 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-cyan-400 transition-colors disabled:opacity-50"
            title="Refresh results from database"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            disabled={runningExperiment}
            onClick={handleTriggerBenchmark}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-950/40 border border-cyan-400/30 transition-all flex items-center gap-2 active:scale-95 disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 fill-current ${runningExperiment ? 'animate-pulse' : ''}`} />
            <span>{runningExperiment ? 'Executing 28 Scenarios...' : 'Run Comparative Benchmark'}</span>
          </button>
        </div>
      </div>

      {/* Sub-Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveSubTab('metrics')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeSubTab === 'metrics'
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Comparative Policy Metrics
        </button>
        <button
          onClick={() => setActiveSubTab('scenarios')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeSubTab === 'scenarios'
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Scenario Dataset Catalog ({scenarios.length})
        </button>
      </div>

      {activeSubTab === 'metrics' && (
        <div className="space-y-6">
          {/* Scientific Disclaimer Note */}
          <div className="bg-[#141b2d] border border-cyan-900/40 rounded-xl p-3.5 flex items-center gap-3 text-xs text-slate-300">
            <Info className="w-5 h-5 text-cyan-400 shrink-0" />
            <p>
              <strong>Evaluation Note:</strong> All metrics below reflect empirical execution on the{' '}
              <span className="text-cyan-300 font-mono font-semibold">28-scenario benchmark</span> suite. Baseline LLM judge results represent the deterministic Mock LLM Provider for offline test reproducibility.
            </p>
          </div>

          {/* Comparative Table */}
          <div className="bg-[#111726] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#0b0f19] text-slate-400 uppercase tracking-wider border-b border-slate-800 text-[11px]">
                  <tr>
                    <th className="py-3.5 px-4 font-bold">Policy</th>
                    <th className="py-3.5 px-3 text-center">Attack Prev. Rate (APR) ↑</th>
                    <th className="py-3.5 px-3 text-center">False Allow Rate (FAR) ↓</th>
                    <th className="py-3.5 px-3 text-center">False Block Rate (FBR) ↓</th>
                    <th className="py-3.5 px-3 text-center">Task Comp. Rate (TCR) ↑</th>
                    <th className="py-3.5 px-3 text-center">Human Interv. (HIR)</th>
                    <th className="py-3.5 px-3 text-center">Avg Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {policyKeys.map((key) => {
                    const m: PolicyMetrics | undefined = policiesData[key];
                    const isAgentShield = key === 'AgentShieldPolicy';

                    return (
                      <tr
                        key={key}
                        className={`transition-colors ${
                          isAgentShield
                            ? 'bg-cyan-950/20 hover:bg-cyan-950/30 text-cyan-200'
                            : 'hover:bg-[#141b2d] text-slate-300'
                        }`}
                      >
                        <td className="py-4 px-4 font-sans font-bold flex items-center gap-2">
                          {isAgentShield && <ShieldCheck className="w-4 h-4 text-cyan-400" />}
                          <span className={isAgentShield ? 'text-cyan-300 font-mono' : ''}>
                            {getPolicyDisplayName(key)}
                          </span>
                        </td>
                        <td className="py-4 px-3 text-center">
                          <span className={`px-2 py-1 rounded font-bold ${
                            m && m.attack_prevention_rate >= 0.9 ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'
                          }`}>
                            {m ? formatPercent(m.attack_prevention_rate) : 'N/A'}
                          </span>
                        </td>
                        <td className="py-4 px-3 text-center">
                          <span className={`px-2 py-1 rounded font-bold ${
                            m && m.false_allow_rate <= 0.1 ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'
                          }`}>
                            {m ? formatPercent(m.false_allow_rate) : 'N/A'}
                          </span>
                        </td>
                        <td className="py-4 px-3 text-center">
                          <span className={`px-2 py-1 rounded font-bold ${
                            m && m.false_block_rate <= 0.15 ? 'text-emerald-400 bg-emerald-500/10' : 'text-amber-400 bg-amber-500/10'
                          }`}>
                            {m ? formatPercent(m.false_block_rate) : 'N/A'}
                          </span>
                        </td>
                        <td className="py-4 px-3 text-center">
                          <span className={`px-2 py-1 rounded font-bold ${
                            m && m.task_completion_rate >= 0.85 ? 'text-emerald-400 bg-emerald-500/10' : 'text-slate-400 bg-slate-800'
                          }`}>
                            {m ? formatPercent(m.task_completion_rate) : 'N/A'}
                          </span>
                        </td>
                        <td className="py-4 px-3 text-center text-slate-400 font-mono">
                          {m ? formatPercent(m.human_intervention_rate) : 'N/A'}
                        </td>
                        <td className="py-4 px-3 text-center font-mono text-slate-400">
                          {m ? formatLatency(m.avg_latency_ms) : 'N/A'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Key Empirical Insights Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-[#111726] border border-slate-800 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-400">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span>No Security Weakness</span>
              </div>
              <p className="text-xs text-slate-300">
                Permits 100% of malicious attempts (exfiltration, prompt injection, and destruction) resulting in 0% attack prevention.
              </p>
            </div>

            <div className="p-4 bg-[#111726] border border-slate-800 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-400">
                <XCircle className="w-4 h-4 text-amber-400" />
                <span>Static RBAC False Blocks</span>
              </div>
              <p className="text-xs text-slate-300">
                Lacks task context and blindly blocks legitimate sensitive operations (e.g. valid secret key rotation, authorized queries).
              </p>
            </div>

            <div className="p-4 bg-[#111726] border border-cyan-500/30 rounded-xl space-y-2 bg-gradient-to-br from-cyan-950/30 to-[#111726]">
              <div className="flex items-center gap-2 text-xs font-bold uppercase text-cyan-400">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                <span>AgentShield Advantage</span>
              </div>
              <p className="text-xs text-cyan-100">
                Context-aware intent alignment distinguishes legitimate sensitive tasks from unauthorized access while maintaining near-zero latency overhead.
              </p>
            </div>
          </div>
        </div>
      )}

      {activeSubTab === 'scenarios' && (
        <div className="bg-[#111726] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="p-4 bg-[#0b0f19] border-b border-slate-800 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
              28 Balanced Scenario Catalog (Ground Truth &amp; Ideal Decisions)
            </span>
            <span className="text-xs text-slate-500 font-mono">Structured JSON Dataset</span>
          </div>

          <div className="divide-y divide-slate-800/80 max-h-[500px] overflow-y-auto scrollbar-thin">
            {scenarios.map((scn) => (
              <div key={scn.id} className="p-4 hover:bg-[#141b2d] transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-mono font-bold text-cyan-300">
                      {scn.id}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {scn.category}
                    </span>
                    <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded ${
                      scn.ground_truth === 'SAFE'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    }`}>
                      GROUND TRUTH: {scn.ground_truth}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300 border border-cyan-800/40">
                      IDEAL: {scn.ideal_security_decision}
                    </span>
                  </div>

                  <div className="text-xs text-slate-200 font-sans">
                    <strong className="text-slate-400">Task: </strong>
                    {scn.task_intent}
                  </div>

                  <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
                    <span className="text-cyan-400">{scn.requested_tool}()</span>
                    <span className="text-slate-600">→</span>
                    <span className="text-slate-300">{scn.target_resource}</span>
                  </div>
                </div>

                <div className="text-right text-[11px] font-mono text-slate-500 shrink-0">
                  Attack: <span className="text-slate-300">{scn.attack_type}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
