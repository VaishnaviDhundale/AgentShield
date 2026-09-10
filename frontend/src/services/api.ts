/**
 * REST API client for AgentShield FastAPI Backend
 */

import {
  OverviewStatistics,
  RequestItem,
  RequestDetail,
  PendingApproval,
  PolicyMetadata,
  BenchmarkResults,
  ScenarioItem,
  SandboxFileEntry,
  RiskConfig
} from '../types';

const API_BASE = '/api';

export const api = {
  // 1. Overview & Health
  async getOverviewStats(): Promise<OverviewStatistics> {
    const res = await fetch(`${API_BASE}/stats/overview`);
    if (!res.ok) throw new Error('Failed to fetch overview statistics');
    return res.json();
  },

  async getHealth(): Promise<{ status: string; active_policy: string; pending_approvals: number }> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Failed to fetch health status');
    return res.json();
  },

  // 2. Telemetry & Requests
  async getRequests(limit: number = 50, decisionFilter?: string): Promise<{ total: number; items: RequestItem[] }> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (decisionFilter && decisionFilter !== 'ALL') {
      params.append('decision_filter', decisionFilter);
    }
    const res = await fetch(`${API_BASE}/requests?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch requests');
    return res.json();
  },

  async getRequestDetail(requestId: string): Promise<RequestDetail> {
    const res = await fetch(`${API_BASE}/requests/${requestId}`);
    if (!res.ok) throw new Error(`Failed to fetch details for request ${requestId}`);
    return res.json();
  },

  // 3. Agent Execution
  async runAgentTask(payload: {
    task_intent: string;
    policy_name: string;
    max_steps?: number;
    provider_type?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/agent/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to execute agent task');
    return res.json();
  },

  async getSessions(limit: number = 20): Promise<any[]> {
    const res = await fetch(`${API_BASE}/agent/sessions?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch sessions');
    return res.json();
  },

  // 4. Human Approval Workflow
  async getPendingApprovals(): Promise<PendingApproval[]> {
    const res = await fetch(`${API_BASE}/approvals/pending`);
    if (!res.ok) throw new Error('Failed to fetch pending approvals');
    return res.json();
  },

  async resolveApproval(approvalId: string, decision: 'ALLOW_ONCE' | 'ALLOW_SESSION' | 'BLOCK', notes?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/approvals/${approvalId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, notes })
    });
    if (!res.ok) throw new Error(`Failed to resolve approval ${approvalId}`);
    return res.json();
  },

  // 5. Policy & Risk Configuration
  async getPolicies(): Promise<{ active_policy: string; available_policies: PolicyMetadata[] }> {
    const res = await fetch(`${API_BASE}/config/policies`);
    if (!res.ok) throw new Error('Failed to fetch policy configurations');
    return res.json();
  },

  async setActivePolicy(policyName: string): Promise<{ status: string; active_policy: string }> {
    const res = await fetch(`${API_BASE}/config/policies/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ policy_name: policyName })
    });
    if (!res.ok) throw new Error(`Failed to switch active policy to ${policyName}`);
    return res.json();
  },

  async getRiskConfig(): Promise<RiskConfig> {
    const res = await fetch(`${API_BASE}/config/risk-engine`);
    if (!res.ok) throw new Error('Failed to fetch risk engine config');
    return res.json();
  },

  // 6. Experiments & Benchmark Evaluation
  async getScenarios(category?: string): Promise<ScenarioItem[]> {
    const url = category ? `${API_BASE}/experiments/scenarios?category=${encodeURIComponent(category)}` : `${API_BASE}/experiments/scenarios`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch benchmark scenarios');
    return res.json();
  },

  async runBenchmark(payload: { policies: string[]; trials?: number; hitl_mode?: string }): Promise<BenchmarkResults> {
    const res = await fetch(`${API_BASE}/experiments/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to run benchmark experiment');
    return res.json();
  },

  async getLatestBenchmarkResults(): Promise<BenchmarkResults> {
    const res = await fetch(`${API_BASE}/experiments/latest`);
    if (!res.ok) throw new Error('Failed to fetch latest benchmark results');
    return res.json();
  },

  async getBenchmarkHistory(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/experiments/history`);
    if (!res.ok) throw new Error('Failed to fetch benchmark history');
    return res.json();
  },

  // 7. Sandbox Management
  async getSandboxTree(): Promise<{ sandbox_root: string; tree: SandboxFileEntry[] }> {
    const res = await fetch(`${API_BASE}/sandbox/tree`);
    if (!res.ok) throw new Error('Failed to fetch sandbox tree');
    return res.json();
  },

  async getSandboxFile(path: string): Promise<{ path: string; size_bytes: number; content: string }> {
    const res = await fetch(`${API_BASE}/sandbox/file?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error(`Failed to read file ${path}`);
    return res.json();
  },

  async resetSandbox(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/sandbox/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hard_reset: true })
    });
    if (!res.ok) throw new Error('Failed to reset sandbox environment');
    return res.json();
  }
};
