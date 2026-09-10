import React, { useEffect, useState } from 'react';
import {
  ScanEye,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  UserCheck,
  CheckCircle2,
  XCircle,
  FileCode2,
  Terminal,
  Activity,
  Layers,
  Database,
  Cpu,
  Clock,
  Sparkles,
  RefreshCw
} from 'lucide-react';
import { useSecurity } from '../context/SecurityContext';
import { api } from '../services/api';
import { RequestDetail, RequestItem } from '../types';
import { formatLatency, getDecisionBadgeColor, getRiskColor, getSensitivityBadgeColor } from '../utils/formatters';

export const RequestInspector: React.FC = () => {
  const { selectedRequestId, setSelectedRequestId } = useSecurity();
  const [requestsList, setRequestsList] = useState<RequestItem[]>([]);
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch recent requests for selector
  const loadRequests = async () => {
    try {
      const res = await api.getRequests(30);
      setRequestsList(res.items);
      if (!selectedRequestId && res.items.length > 0) {
        setSelectedRequestId(res.items[0].request_id);
      }
    } catch (err) {
      console.error('Failed to load requests list:', err);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  // Fetch specific request detail whenever selectedRequestId changes
  useEffect(() => {
    if (!selectedRequestId) return;
    let isCurrent = true;
    setLoading(true);
    setError(null);

    api.getRequestDetail(selectedRequestId)
      .then((data) => {
        if (isCurrent) setDetail(data);
      })
      .catch((err) => {
        if (isCurrent) setError(err.message);
      })
      .finally(() => {
        if (isCurrent) setLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedRequestId]);

  const req = detail?.request;
  const dec = detail?.decision;
  const riskInfo = getRiskColor(dec?.risk_score || 0);

  return (
    <div className="space-y-6">
      {/* Header & Request Selector Bar */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <ScanEye className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Runtime Security Request Inspector
            </h2>
            <p className="text-xs text-slate-400">
              Granular contextual signal analysis and decision breakdown
            </p>
          </div>
        </div>

        {/* Request Dropdown Selector */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <span className="text-xs text-slate-400 font-semibold shrink-0">Select Request:</span>
          <select
            value={selectedRequestId || ''}
            onChange={(e) => setSelectedRequestId(e.target.value)}
            className="bg-[#141b2d] border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500 max-w-xs md:max-w-md truncate"
          >
            {requestsList.map((r) => (
              <option key={r.request_id} value={r.request_id} className="bg-[#0f1422] text-slate-200">
                [{r.decision}] {r.tool_name} → {r.target_resource || 'default'} ({r.task_intent?.slice(0, 35)}...)
              </option>
            ))}
          </select>
          <button
            onClick={loadRequests}
            className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-cyan-400 transition-colors"
            title="Refresh requests list"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {loading && (
        <div className="py-20 text-center text-slate-400 font-mono text-sm">
          Loading granular telemetry breakdown...
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-500/15 border border-rose-500/30 rounded-xl text-rose-300 text-xs font-mono">
          {error}
        </div>
      )}

      {!loading && !error && !req && (
        <div className="py-20 text-center text-slate-500 border border-dashed border-slate-800 rounded-xl">
          <ScanEye className="w-8 h-8 mx-auto mb-2 text-slate-600" />
          <p className="text-sm font-semibold text-slate-400">No request selected.</p>
          <p className="text-xs text-slate-600 mt-1">Select an intercepted tool call to inspect its security decision pipeline.</p>
        </div>
      )}

      {!loading && req && (
        <div className="space-y-6">
          {/* Visual 8-Stage Execution Pipeline */}
          <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>Security Interception &amp; Decision Pipeline</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-8 gap-3">
              {/* Step 1: Task Intent */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">1. Task Intent</span>
                <p className="text-xs text-slate-200 font-medium line-clamp-3 mt-1" title={req.task_intent}>
                  {req.task_intent}
                </p>
                <div className="mt-2 text-[10px] font-mono text-cyan-400">Context Source</div>
              </div>

              {/* Step 2: Tool Request */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">2. Tool Call</span>
                <div className="text-xs font-mono font-bold text-cyan-300 mt-1">
                  {req.tool_name}()
                </div>
                <div className="text-[10px] text-slate-400">Step #{req.step_number}</div>
              </div>

              {/* Step 3: Target Resource */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">3. Target Resource</span>
                <div className="text-xs font-mono font-semibold text-slate-200 truncate mt-1" title={req.target_resource}>
                  {req.target_resource || 'None'}
                </div>
                <div className="text-[10px] text-slate-400">Resource Path</div>
              </div>

              {/* Step 4: Sensitivity */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">4. Sensitivity</span>
                <div className="mt-1">
                  <span className={`text-[11px] font-bold font-mono px-2 py-0.5 rounded border ${getSensitivityBadgeColor(dec?.resource_sensitivity)}`}>
                    {dec?.resource_sensitivity || 'LOW'}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400">Resource Tier</div>
              </div>

              {/* Step 5: Action Risk */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">5. Tool Risk</span>
                <div className="text-sm font-mono font-bold text-slate-200 mt-1">
                  {dec?.action_risk ?? 10}/100
                </div>
                <div className="text-[10px] text-slate-400">Base Tool Weight</div>
              </div>

              {/* Step 6: Risk Score */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">6. Computed Risk</span>
                <div className={`text-base font-mono font-bold mt-1 ${riskInfo.text}`}>
                  {dec?.risk_score ?? 0}/100
                </div>
                <div className="text-[10px] font-mono text-slate-400">
                  {formatLatency(dec?.latency_ms)}
                </div>
              </div>

              {/* Step 7: Gateway Decision */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">7. Decision</span>
                <div className="mt-1">
                  <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded border ${getDecisionBadgeColor(dec?.decision)}`}>
                    {dec?.decision || 'UNKNOWN'}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono">
                  {dec?.policy_name || 'AgentShield'}
                </div>
              </div>

              {/* Step 8: Execution Result */}
              <div className="p-3 bg-[#141b2d] border border-slate-800 rounded-xl flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase">8. Sandbox Outcome</span>
                <div className="mt-1 flex items-center gap-1.5 font-mono text-xs font-semibold">
                  {dec?.decision === 'ALLOW' ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span className="text-emerald-400">Executed</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 text-rose-400" />
                      <span className="text-rose-400">Prevented</span>
                    </>
                  )}
                </div>
                <div className="text-[10px] text-slate-400">Jail Integrity Safe</div>
              </div>
            </div>
          </div>

          {/* Detailed Breakdown: Left (Contextual Signals & Decision Logic) / Right (Parameters & History) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Security Reasoning & Signal Analysis */}
            <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <span>Security Engine Authorization Analysis</span>
              </h3>

              {/* Primary Reason Callout */}
              <div className="p-3.5 bg-[#141b2d] border border-slate-800 rounded-xl space-y-1">
                <div className="text-[11px] font-bold text-slate-400 uppercase">Decision Rationale:</div>
                <p className="text-xs text-slate-200 leading-relaxed font-sans">
                  {dec?.reason || 'Evaluated within declared task intent scope.'}
                </p>
              </div>

              {/* Mathematical Formula Expansion */}
              <div className="p-3.5 bg-[#0e1424] border border-slate-800/80 rounded-xl space-y-2">
                <div className="text-[11px] font-bold text-cyan-400 uppercase font-mono">
                  Mathematical Risk Score Calculation:
                </div>
                <div className="p-2 bg-slate-950/80 rounded-lg text-xs font-mono text-slate-300 border border-slate-800 overflow-x-auto">
                  <code>Risk = min(100, max(0, 0.35 * S_res + 0.20 * R_tool + 0.35 * M_intent + 0.10 * A_hist + Rules))</code>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono text-slate-400 pt-1">
                  <div>S_res: <strong className="text-cyan-300">{dec?.resource_sensitivity || 'LOW'}</strong></div>
                  <div>R_tool: <strong className="text-cyan-300">{dec?.action_risk || 10}</strong></div>
                  <div>Score: <strong className={riskInfo.text}>{dec?.risk_score || 0}/100</strong></div>
                  <div>Confidence: <strong className="text-cyan-300">{((dec?.confidence || 0.95) * 100).toFixed(0)}%</strong></div>
                </div>
              </div>

              {/* Active Signals */}
              <div className="space-y-1.5">
                <div className="text-[11px] font-bold text-slate-400 uppercase">Triggered Security Signals:</div>
                {dec?.signals && dec.signals.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {dec.signals.map((sig, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-lg text-xs font-mono bg-cyan-950/40 text-cyan-300 border border-cyan-800/60"
                      >
                        {sig}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No anomaly or violation signals triggered.</p>
                )}
              </div>
            </div>

            {/* Right: Request Parameters & Execution Telemetry */}
            <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <FileCode2 className="w-4 h-4 text-cyan-400" />
                <span>Tool Arguments &amp; Execution Metadata</span>
              </h3>

              {/* Tool Parameters Raw View */}
              <div className="space-y-1.5">
                <div className="text-[11px] font-bold text-slate-400 uppercase">Input Parameters:</div>
                <div className="p-3 bg-[#0a0d14] border border-slate-800 rounded-xl text-xs font-mono text-cyan-300 max-h-48 overflow-y-auto scrollbar-thin">
                  <pre>{JSON.stringify(req.parameters, null, 2)}</pre>
                </div>
              </div>

              {/* Metadata Details */}
              <div className="grid grid-cols-2 gap-3 text-xs pt-2 border-t border-slate-800">
                <div className="p-2.5 bg-[#141b2d] rounded-lg border border-slate-800/80">
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase">Session ID</span>
                  <span className="font-mono text-slate-300 text-[11px] truncate block">{req.session_id}</span>
                </div>
                <div className="p-2.5 bg-[#141b2d] rounded-lg border border-slate-800/80">
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase">Request ID</span>
                  <span className="font-mono text-slate-300 text-[11px] truncate block">{req.id}</span>
                </div>
                <div className="p-2.5 bg-[#141b2d] rounded-lg border border-slate-800/80">
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase">Interception Latency</span>
                  <span className="font-mono text-slate-300 text-[11px] block">{formatLatency(dec?.latency_ms)}</span>
                </div>
                <div className="p-2.5 bg-[#141b2d] rounded-lg border border-slate-800/80">
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase">Enforcing Policy</span>
                  <span className="font-mono text-slate-300 text-[11px] block">{dec?.policy_name || 'AgentShield'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
