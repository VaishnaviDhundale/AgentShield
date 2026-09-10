import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  X,
  AlertTriangle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Terminal,
  FileCode2,
  CheckCircle2,
  Lock,
  Layers
} from 'lucide-react';
import { useSecurity } from '../context/SecurityContext';
import { PendingApproval } from '../types';
import { getRiskColor, formatLatency } from '../utils/formatters';

export const HumanApprovalModal: React.FC = () => {
  const {
    isApprovalModalOpen,
    setIsApprovalModalOpen,
    pendingApprovals,
    resolveApproval
  } = useSecurity();

  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);
  const [reviewerNotes, setReviewerNotes] = useState<string>('');
  const [resolving, setResolving] = useState<boolean>(false);

  // Auto-select first pending approval if none selected
  useEffect(() => {
    if (pendingApprovals.length > 0 && !selectedApprovalId) {
      setSelectedApprovalId(pendingApprovals[0].approval_id);
    } else if (pendingApprovals.length === 0) {
      setSelectedApprovalId(null);
    }
  }, [pendingApprovals, selectedApprovalId]);

  if (!isApprovalModalOpen && pendingApprovals.length === 0) {
    return null;
  }

  const selectedApproval = pendingApprovals.find((p) => p.approval_id === selectedApprovalId) || pendingApprovals[0];
  const riskInfo = getRiskColor(selectedApproval?.risk_score || 50);

  const handleAction = async (decision: 'ALLOW_ONCE' | 'ALLOW_SESSION' | 'BLOCK') => {
    if (!selectedApproval) return;
    setResolving(true);
    try {
      await resolveApproval(selectedApproval.approval_id, decision, reviewerNotes);
      setReviewerNotes('');
      if (pendingApprovals.length <= 1) {
        setIsApprovalModalOpen(false);
      }
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#111726] border border-amber-500/50 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl shadow-amber-950/40 flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-amber-950/60 to-[#141b2d] border-b border-amber-500/30 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-inner">
              <UserCheck className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">
                  Human-In-The-Loop Authorization
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  {pendingApprovals.length} PENDING
                </span>
              </div>
              <p className="text-xs text-amber-400/80">
                AgentShield Gateway suspended execution for high-risk action confirmation.
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsApprovalModalOpen(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        {pendingApprovals.length === 0 ? (
          <div className="p-12 text-center text-slate-400 space-y-2">
            <ShieldCheck className="w-12 h-12 mx-auto text-emerald-400" />
            <h3 className="text-sm font-bold text-white">All Approval Requests Resolved</h3>
            <p className="text-xs text-slate-500">There are currently no active actions paused in the Gateway.</p>
          </div>
        ) : (
          <div className="p-6 space-y-5 overflow-y-auto scrollbar-thin">
            {/* Multiple Approvals Tabs if > 1 */}
            {pendingApprovals.length > 1 && (
              <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-800">
                {pendingApprovals.map((p, idx) => (
                  <button
                    key={p.approval_id}
                    onClick={() => setSelectedApprovalId(p.approval_id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all whitespace-nowrap ${
                      selectedApproval?.approval_id === p.approval_id
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                    }`}
                  >
                    Request #{idx + 1}: {p.tool_name}()
                  </button>
                ))}
              </div>
            )}

            {/* Request Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Intent & Action */}
              <div className="bg-[#141b2d] border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Declared Task Intent
                  </span>
                  <span className="text-[10px] font-mono text-cyan-400">Context Origin</span>
                </div>
                <p className="text-xs font-semibold text-slate-100 bg-[#0b0f19] p-2.5 rounded-lg border border-slate-800">
                  {selectedApproval.task_intent}
                </p>

                <div className="space-y-1.5 pt-1">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Requested Tool &amp; Target
                  </div>
                  <div className="flex items-center gap-2 font-mono text-xs text-cyan-300 bg-[#0b0f19] p-2.5 rounded-lg border border-slate-800">
                    <Terminal className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span className="font-bold">{selectedApproval.tool_name}()</span>
                    <span className="text-slate-500">→</span>
                    <span className="truncate">{selectedApproval.target_resource || 'Default Target'}</span>
                  </div>
                </div>
              </div>

              {/* Risk Engine Breakdown */}
              <div className="bg-[#141b2d] border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Security Risk Analysis
                  </span>
                  <span className={`text-xs font-mono font-bold ${riskInfo.text}`}>
                    Risk Score: {selectedApproval.risk_score}/100
                  </span>
                </div>

                <div className="bg-[#0b0f19] p-2.5 rounded-lg border border-slate-800 space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-500">Escalation Reason:</div>
                  <p className="text-xs text-amber-300/90 leading-relaxed">
                    {selectedApproval.reason || 'Calculated risk falls in the ASK_HUMAN range (40 - 70).'}
                  </p>
                </div>

                {/* Signals */}
                {selectedApproval.signals && selectedApproval.signals.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {selectedApproval.signals.map((sig, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/40"
                      >
                        {sig}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Input Parameters Preview */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Full Tool Parameters:
              </span>
              <div className="p-3 bg-[#0a0d14] border border-slate-800 rounded-xl text-xs font-mono text-cyan-300 max-h-32 overflow-y-auto scrollbar-thin">
                <pre>{JSON.stringify(selectedApproval.parameters, null, 2)}</pre>
              </div>
            </div>

            {/* Reviewer Notes Field */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Reviewer Notes / Authorization Rationale (Optional):
              </label>
              <input
                type="text"
                placeholder="e.g. Authorized database migration for issue #412"
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                className="w-full px-3 py-2 bg-[#0b0f19] border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/60 transition-colors"
              />
            </div>
          </div>
        )}

        {/* Modal Footer Actions */}
        {pendingApprovals.length > 0 && selectedApproval && (
          <div className="bg-[#0f1422] border-t border-slate-800 px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-[11px] text-slate-500 font-mono flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>Timeout defaults to BLOCK automatically</span>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              {/* BLOCK Action */}
              <button
                disabled={resolving}
                onClick={() => handleAction('BLOCK')}
                className="flex-1 sm:flex-none px-4 py-2 rounded-xl text-xs font-bold bg-rose-600/20 text-rose-300 border border-rose-500/40 hover:bg-rose-600/30 transition-all flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50"
              >
                <ShieldAlert className="w-4 h-4" />
                <span>Reject (BLOCK)</span>
              </button>

              {/* ALLOW ONCE Action */}
              <button
                disabled={resolving}
                onClick={() => handleAction('ALLOW_ONCE')}
                className="flex-1 sm:flex-none px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/50 border border-emerald-400/40 transition-all flex items-center justify-center gap-1.5 active:scale-95 disabled:opacity-50"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Approve Once</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
