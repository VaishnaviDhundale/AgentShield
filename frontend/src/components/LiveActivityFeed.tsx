import React, { useState } from 'react';
import {
  Radio,
  Search,
  Filter,
  Pause,
  Play,
  Trash2,
  ScanEye,
  AlertTriangle,
  Clock,
  Terminal,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { useSecurity } from '../context/SecurityContext';
import { formatLatency, getDecisionBadgeColor, getRiskColor, formatTimeAgo, getSensitivityBadgeColor } from '../utils/formatters';

interface LiveActivityFeedProps {
  onInspectRequest: (requestId: string) => void;
}

export const LiveActivityFeed: React.FC<LiveActivityFeedProps> = ({ onInspectRequest }) => {
  const { events, clearEvents, isConnected } = useSecurity();
  const [searchTerm, setSearchTerm] = useState('');
  const [decisionFilter, setDecisionFilter] = useState<'ALL' | 'ALLOW' | 'BLOCK' | 'ASK_HUMAN'>('ALL');
  const [isPaused, setIsPaused] = useState(false);

  // If paused, freeze the snapshot of events
  const [frozenEvents, setFrozenEvents] = useState<typeof events>([]);

  const handleTogglePause = () => {
    if (!isPaused) {
      setFrozenEvents([...events]);
    }
    setIsPaused(!isPaused);
  };

  const displayedEvents = isPaused ? frozenEvents : events;

  const filteredEvents = displayedEvents.filter((evt) => {
    // Decision filter
    if (decisionFilter !== 'ALL') {
      if (evt.decision?.toUpperCase() !== decisionFilter) return false;
    }

    // Search filter
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchTool = evt.tool_name?.toLowerCase().includes(q);
      const matchTarget = evt.target_resource?.toLowerCase().includes(q);
      const matchIntent = evt.task_intent?.toLowerCase().includes(q);
      const matchReason = evt.reason?.toLowerCase().includes(q);
      const matchSignals = evt.signals?.some((s) => s.toLowerCase().includes(q));
      const matchType = evt.event_type?.toLowerCase().includes(q);
      return matchTool || matchTarget || matchIntent || matchReason || matchSignals || matchType;
    }

    return true;
  });

  return (
    <div className="space-y-4">
      {/* Feed Controls & Toolbar */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="relative flex items-center justify-center p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <span>Live Interception Stream</span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-normal">
                {filteredEvents.length} events
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Direct WebSocket broadcast from AgentShield Gateway
            </p>
          </div>
        </div>

        {/* Filter & Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-end">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by tool, resource, signal..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[#141b2d] border border-slate-700/60 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/60 transition-colors"
            />
          </div>

          {/* Decision Filter Pills */}
          <div className="flex items-center bg-[#141b2d] border border-slate-700/60 rounded-lg p-0.5">
            {(['ALL', 'ALLOW', 'BLOCK', 'ASK_HUMAN'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setDecisionFilter(mode)}
                className={`px-2.5 py-1 text-[11px] font-bold rounded-md transition-all ${
                  decisionFilter === mode
                    ? mode === 'ALLOW'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : mode === 'BLOCK'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : mode === 'ASK_HUMAN'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Pause / Resume Button */}
          <button
            onClick={handleTogglePause}
            className={`p-1.5 rounded-lg border text-xs font-semibold transition-all flex items-center gap-1 px-2.5 ${
              isPaused
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
            title={isPaused ? 'Resume live feed' : 'Pause live feed'}
          >
            {isPaused ? <Play className="w-3.5 h-3.5 fill-current" /> : <Pause className="w-3.5 h-3.5" />}
            <span>{isPaused ? 'Paused' : 'Pause'}</span>
          </button>

          {/* Clear Feed */}
          <button
            onClick={clearEvents}
            className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-rose-400 hover:border-rose-900/60 transition-all"
            title="Clear event history"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Events Feed Table / List */}
      <div className="bg-[#111726] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        {filteredEvents.length === 0 ? (
          <div className="py-16 text-center text-slate-500">
            <Radio className="w-8 h-8 mx-auto mb-2 text-slate-600 animate-pulse" />
            <p className="text-sm font-semibold text-slate-400">No events match the current filter.</p>
            <p className="text-xs text-slate-600 mt-1">
              Events streamed from the backend Gateway appear here in real-time.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {filteredEvents.map((evt, idx) => {
              const isInterception = evt.event_type === 'TOOL_REQUEST_INTERCEPTED';
              const riskInfo = getRiskColor(evt.risk_score || 0);

              return (
                <div
                  key={evt.request_id || idx}
                  className="p-4 hover:bg-[#141b2d] transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  {/* Left Column: Decision Badge + Main Metadata */}
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Decision Badge */}
                      <span className={`px-2.5 py-0.5 rounded-md text-xs font-bold font-mono border ${getDecisionBadgeColor(evt.decision)}`}>
                        {evt.decision || evt.event_type}
                      </span>

                      {/* Tool Name */}
                      {evt.tool_name && (
                        <span className="font-mono text-xs font-semibold text-slate-200 flex items-center gap-1">
                          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                          <span>{evt.tool_name}()</span>
                        </span>
                      )}

                      {/* Target Resource */}
                      {evt.target_resource && (
                        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[#0b0f19] text-cyan-300 border border-slate-700/60 truncate max-w-xs">
                          {evt.target_resource}
                        </span>
                      )}

                      {/* Resource Sensitivity Badge */}
                      {evt.resource_sensitivity && (
                        <span className={`text-[10px] font-bold font-mono px-1.5 py-0.2 rounded border ${getSensitivityBadgeColor(evt.resource_sensitivity)}`}>
                          {evt.resource_sensitivity} SENSITIVITY
                        </span>
                      )}

                      {/* Execution Status */}
                      {isInterception && (
                        <span className="text-[11px] font-mono flex items-center gap-1 text-slate-400">
                          {evt.action_executed ? (
                            <>
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                              <span className="text-emerald-400">Executed</span>
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3.5 h-3.5 text-rose-400" />
                              <span className="text-rose-400">Not Executed</span>
                            </>
                          )}
                        </span>
                      )}
                    </div>

                    {/* Task Intent / Description */}
                    <div className="text-xs text-slate-300">
                      <span className="text-slate-500 font-semibold">Intent: </span>
                      <span>{evt.task_intent || evt.reason || evt.message || 'System operation'}</span>
                    </div>

                    {/* Triggered Signals */}
                    {evt.signals && evt.signals.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1 pt-1">
                        <span className="text-[10px] uppercase font-bold text-slate-500">Signals:</span>
                        {evt.signals.map((sig, sIdx) => (
                          <span
                            key={sIdx}
                            className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700"
                          >
                            {sig}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right Column: Risk Score, Latency, and Inspect Button */}
                  <div className="flex items-center gap-4 shrink-0 justify-between md:justify-end border-t md:border-t-0 pt-2 md:pt-0 border-slate-800">
                    {/* Risk Score Pill */}
                    {evt.risk_score !== undefined && (
                      <div className="text-right">
                        <div className={`text-sm font-bold font-mono ${riskInfo.text}`}>
                          Risk {evt.risk_score}/100
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 flex items-center gap-1 justify-end">
                          <Clock className="w-3 h-3" />
                          <span>{formatLatency(evt.latency_ms)}</span>
                        </div>
                      </div>
                    )}

                    {/* Inspect Button */}
                    {evt.request_id && (
                      <button
                        onClick={() => onInspectRequest(evt.request_id!)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-300 hover:border-cyan-500/40 border border-slate-700 text-slate-300 transition-all flex items-center gap-1.5 active:scale-95"
                      >
                        <ScanEye className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Inspect</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
