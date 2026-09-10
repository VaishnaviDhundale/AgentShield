import React from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  Zap,
  ArrowRight,
  Lock,
  Layers,
  Activity,
  Sparkles,
  Database,
  Terminal,
  FileCode2
} from 'lucide-react';
import { useSecurity } from '../context/SecurityContext';
import { formatLatency, getDecisionBadgeColor, getRiskColor, formatTimeAgo } from '../utils/formatters';

interface SecurityOverviewProps {
  onNavigateToTab: (tab: any) => void;
}

export const SecurityOverview: React.FC<SecurityOverviewProps> = ({ onNavigateToTab }) => {
  const { stats, events, setSelectedRequestId, setIsAgentModalOpen, setIsApprovalModalOpen, pendingApprovals } = useSecurity();

  const total = stats?.total_requests || 0;
  const allowed = stats?.allowed_requests || 0;
  const blocked = stats?.blocked_requests || 0;
  const human = stats?.human_approvals || 0;
  const latency = stats?.avg_latency_ms || 0;

  const allowPct = total > 0 ? ((allowed / total) * 100).toFixed(1) : '0.0';
  const blockPct = total > 0 ? ((blocked / total) * 100).toFixed(1) : '0.0';
  const humanPct = total > 0 ? ((human / total) * 100).toFixed(1) : '0.0';

  return (
    <div className="space-y-6">
      {/* Pending Approvals Callout Banner if active */}
      {pendingApprovals.length > 0 && (
        <div className="bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-[#111726] border border-amber-500/40 rounded-xl p-4 flex items-center justify-between shadow-lg shadow-amber-950/30">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/20 rounded-lg text-amber-400">
              <UserCheck className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-amber-200">
                Action Required: {pendingApprovals.length} Tool Request{pendingApprovals.length > 1 ? 's' : ''} Paused in Gateway
              </h3>
              <p className="text-xs text-amber-400/80">
                Agent execution is suspended pending human security authorization.
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigateToTab('approvals')}
            className="px-4 py-1.5 bg-amber-500 text-slate-950 hover:bg-amber-400 font-bold text-xs rounded-lg transition-all shadow-md shadow-amber-950/50 flex items-center gap-1.5"
          >
            <span>Review & Resolve</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Primary SOC Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Interceptions */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Interceptions</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">{total}</div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <Activity className="w-3 h-3 text-cyan-400" />
            <span>100% Routed via Gateway</span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 to-blue-500"></div>
        </div>

        {/* ALLOWED */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Authorized Actions</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">{allowed}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span className="text-emerald-400 font-semibold">{allowPct}%</span> of total requests
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-emerald-500"></div>
        </div>

        {/* BLOCKED */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Blocked Threats</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400">{blocked}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span className="text-rose-400 font-semibold">{blockPct}%</span> risk score &gt; 70
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-rose-500"></div>
        </div>

        {/* HUMAN APPROVALS */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">HITL Approvals</span>
            <UserCheck className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400">{human}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span className="text-amber-400 font-semibold">{humanPct}%</span> required escalation
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-amber-500"></div>
        </div>

        {/* AVG LATENCY */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Gateway Latency</span>
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-300">{formatLatency(latency)}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            Near-zero interception overhead
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-cyan-400"></div>
        </div>
      </div>

      {/* Decision Distribution Bar */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>Runtime Decision Breakdown</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">SQLite Audit Ingestion</span>
        </div>

        {/* Visual Multi-Segment Bar */}
        <div className="h-4 w-full bg-slate-900 rounded-full overflow-hidden flex gap-0.5 border border-slate-800 p-0.5">
          {total > 0 ? (
            <>
              <div
                style={{ width: `${allowPct}%` }}
                className="bg-emerald-500 h-full rounded-l-full transition-all duration-500"
                title={`Allowed: ${allowed} (${allowPct}%)`}
              />
              <div
                style={{ width: `${blockPct}%` }}
                className="bg-rose-500 h-full transition-all duration-500"
                title={`Blocked: ${blocked} (${blockPct}%)`}
              />
              <div
                style={{ width: `${humanPct}%` }}
                className="bg-amber-500 h-full rounded-r-full transition-all duration-500"
                title={`Human Approvals: ${human} (${humanPct}%)`}
              />
            </>
          ) : (
            <div className="w-full bg-slate-800 h-full rounded-full" />
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 mt-3 pt-3 border-t border-slate-800/60">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
            <span>ALLOW: <strong className="text-slate-200 font-mono">{allowed}</strong> ({allowPct}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
            <span>BLOCK: <strong className="text-slate-200 font-mono">{blocked}</strong> ({blockPct}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span>
            <span>ASK_HUMAN: <strong className="text-slate-200 font-mono">{human}</strong> ({humanPct}%)</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Live Activity Stream vs Agent Execution Demo */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Live Interception Feed */}
        <div className="lg:col-span-2 bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span>Live Interception Stream</span>
              </h3>
              <p className="text-xs text-slate-400">Real-time WebSocket events from Gateway</p>
            </div>
            <button
              onClick={() => onNavigateToTab('feed')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 hover:underline"
            >
              <span>View Full Feed</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {events.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center py-12 text-slate-500 border border-dashed border-slate-800 rounded-xl">
              <Layers className="w-8 h-8 mb-2 opacity-50 text-cyan-500" />
              <p className="text-sm font-medium">No live events captured in this session yet.</p>
              <p className="text-xs text-slate-600 mt-1">Launch an agent task or benchmark to stream real-time events.</p>
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1 scrollbar-thin">
              {events.slice(0, 6).map((evt, idx) => {
                const isDecision = evt.event_type === 'TOOL_REQUEST_INTERCEPTED';
                const riskInfo = getRiskColor(evt.risk_score || 0);

                return (
                  <div
                    key={idx}
                    onClick={() => {
                      if (evt.request_id) {
                        setSelectedRequestId(evt.request_id);
                        onNavigateToTab('inspector');
                      }
                    }}
                    className="p-3 bg-[#141b2d] hover:bg-[#18223a] border border-slate-800 hover:border-cyan-500/40 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-3 group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={`px-2 py-1 rounded-md text-[11px] font-bold font-mono border ${getDecisionBadgeColor(evt.decision)}`}>
                        {evt.decision || evt.event_type.replace(/_/g, ' ')}
                      </span>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-semibold text-slate-200 truncate">
                            {evt.tool_name || 'System Event'}
                          </span>
                          {evt.target_resource && (
                            <span className="text-[11px] font-mono text-cyan-400/90 truncate bg-cyan-950/40 px-1.5 py-0.5 rounded border border-cyan-800/40">
                              {evt.target_resource}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 truncate mt-0.5">
                          {evt.task_intent || evt.reason || evt.message || 'Interception event'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {isDecision && evt.risk_score !== undefined && (
                        <div className="text-right">
                          <div className={`text-xs font-bold font-mono ${riskInfo.text}`}>
                            Risk {evt.risk_score}/100
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono">
                            {formatLatency(evt.latency_ms)}
                          </div>
                        </div>
                      )}
                      <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right 1 Col: Architecture Pipeline Diagram & Quick Launch */}
        <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2 mb-3">
              <Lock className="w-4 h-4 text-cyan-400" />
              <span>Control Flow Invariant</span>
            </h3>

            {/* Architecture Pipeline Mini-Diagram */}
            <div className="space-y-1.5 font-mono text-[11px]">
              <div className="p-2 bg-[#141b2d] border border-slate-800 rounded-lg text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                <span>1. AI Agent Tool Call Request</span>
              </div>
              <div className="text-center text-slate-600 text-xs">↓</div>
              <div className="p-2 bg-cyan-950/40 border border-cyan-500/30 rounded-lg text-cyan-300 font-bold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                <span>2. AgentShield Gateway Interceptor</span>
              </div>
              <div className="text-center text-slate-600 text-xs">↓</div>
              <div className="p-2 bg-[#141b2d] border border-slate-800 rounded-lg text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                <span>3. Context Intent &amp; Risk Math</span>
              </div>
              <div className="text-center text-slate-600 text-xs">↓</div>
              <div className="p-2 bg-[#141b2d] border border-slate-800 rounded-lg text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>4. ALLOW / BLOCK / ASK_HUMAN</span>
              </div>
              <div className="text-center text-slate-600 text-xs">↓</div>
              <div className="p-2 bg-[#141b2d] border border-slate-800 rounded-lg text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                <span>5. Isolated Sandbox Execution</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800/80">
            <button
              onClick={() => setIsAgentModalOpen(true)}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-600 to-blue-600 text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-md shadow-cyan-950/40 flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>Launch Live Agent Demo</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
