import React, { useState } from 'react';
import { SecurityProvider, useSecurity } from './context/SecurityContext';
import { Header } from './components/Header';
import { Navigation, TabType } from './components/Navigation';
import { SecurityOverview } from './components/SecurityOverview';
import { LiveActivityFeed } from './components/LiveActivityFeed';
import { RequestInspector } from './components/RequestInspector';
import { HumanApprovalModal } from './components/HumanApprovalModal';
import { EvaluationCenter } from './components/EvaluationCenter';
import { AblationView } from './components/AblationView';
import { SandboxExplorer } from './components/SandboxExplorer';
import { RiskConfigViewer } from './components/RiskConfigViewer';
import { AgentRunnerModal } from './components/AgentRunnerModal';
import { Shield, Radio, Layers, Database, Lock } from 'lucide-react';

const DashboardContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const { setSelectedRequestId, stats, isConnected } = useSecurity();

  const handleInspectRequest = (requestId: string) => {
    setSelectedRequestId(requestId);
    setActiveTab('inspector');
  };

  return (
    <div className="min-h-screen bg-[#0a0d14] text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <Header />

      {/* Tab Navigation */}
      <Navigation activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === 'overview' && (
          <SecurityOverview onNavigateToTab={(tab) => setActiveTab(tab)} />
        )}
        {activeTab === 'feed' && (
          <LiveActivityFeed onInspectRequest={handleInspectRequest} />
        )}
        {activeTab === 'inspector' && <RequestInspector />}
        {activeTab === 'approvals' && (
          <div className="space-y-6">
            <HumanApprovalModal />
            <div className="bg-[#111726] border border-slate-800 rounded-xl p-8 text-center text-slate-400">
              <p className="text-sm font-semibold text-slate-300">
                Human Approval review interface is also accessible via the header indicator.
              </p>
            </div>
          </div>
        )}
        {activeTab === 'evaluation' && <EvaluationCenter />}
        {activeTab === 'ablation' && <AblationView />}
        {activeTab === 'sandbox' && <SandboxExplorer />}
        {activeTab === 'config' && <RiskConfigViewer />}
      </main>

      {/* Floating / Standalone Modals */}
      <HumanApprovalModal />
      <AgentRunnerModal />

      {/* SOC Footer */}
      <footer className="bg-[#0b0f19] border-t border-slate-800/80 px-6 py-3 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-mono">
            <Shield className="w-3.5 h-3.5 text-cyan-500" />
            <span className="text-slate-400">AgentShield Security Control Layer v1.0.0</span>
            <span className="text-slate-700">|</span>
            <span>Invariant: AI Agent → Gateway → Policy Decision → Sandbox</span>
          </div>

          <div className="flex items-center gap-4 font-mono text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
              <span>{isConnected ? 'WebSocket Stream Connected' : 'Stream Disconnected'}</span>
            </div>
            <div className="flex items-center gap-1">
              <Database className="w-3 h-3 text-slate-400" />
              <span>SQLite Audit Log Ingestion Active</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <SecurityProvider>
      <DashboardContent />
    </SecurityProvider>
  );
};

export default App;
