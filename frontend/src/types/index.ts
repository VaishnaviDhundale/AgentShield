/**
 * Domain types and schemas for AgentShield Dashboard
 */

export type DecisionType = 'ALLOW' | 'BLOCK' | 'ASK_HUMAN' | 'UNKNOWN';
export type ResourceSensitivity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface OverviewStatistics {
  system_status: string;
  total_requests: number;
  allowed_requests: number;
  blocked_requests: number;
  human_approvals: number;
  total_sessions: number;
  avg_latency_ms: number;
  active_policy: string;
}

export interface SecurityEvent {
  event_type: string;
  request_id?: string;
  session_id?: string;
  step_number?: number;
  tool_name?: string;
  target_resource?: string;
  task_intent?: string;
  parameters?: Record<string, any>;
  decision?: DecisionType;
  risk_score?: number;
  confidence?: number;
  reason?: string;
  signals?: string[];
  resource_sensitivity?: ResourceSensitivity;
  action_risk?: number;
  latency_ms?: number;
  action_executed?: boolean;
  approval_id?: string;
  active_policy?: string;
  notes?: string;
  timestamp?: string;
  [key: string]: any;
}

export interface RequestItem {
  request_id: string;
  session_id: string;
  step_number: number;
  tool_name: string;
  target_resource: string;
  task_intent: string;
  parameters: Record<string, any>;
  created_at: string | null;
  decision: DecisionType;
  risk_score: number;
  confidence: number;
  reason: string;
  signals: string[];
  policy_name: string;
  resource_sensitivity: ResourceSensitivity;
  action_risk: number;
  latency_ms: number;
}

export interface RequestDetail {
  request: {
    id: string;
    session_id: string;
    step_number: number;
    tool_name: string;
    target_resource: string;
    task_intent: string;
    parameters: Record<string, any>;
    agent_history: any[];
    created_at: string | null;
  };
  decision: {
    decision: DecisionType;
    risk_score: number;
    confidence: number;
    reason: string;
    signals: string[];
    policy_name: string;
    resource_sensitivity: ResourceSensitivity;
    action_risk: number;
    latency_ms: number;
    estimated_cost_usd: number;
  } | null;
}

export interface PendingApproval {
  approval_id: string;
  request_id: string;
  session_id: string;
  task_intent: string;
  tool_name: string;
  target_resource: string;
  parameters: Record<string, any>;
  risk_score: number;
  reason: string;
  signals: string[];
  created_at: number;
  timeout_sec: number;
  status: string;
}

export interface PolicyMetadata {
  id: string;
  name: string;
  description: string;
  type: 'control_layer' | 'baseline' | 'ablation';
}

export interface PolicyMetrics {
  policy_name: string;
  total_scenarios: number;
  safe_scenarios: number;
  unsafe_scenarios: number;
  false_allow_rate: number;
  attack_prevention_rate: number;
  false_block_rate: number;
  task_completion_rate: number;
  human_intervention_rate: number;
  avg_latency_ms: number;
  total_cost_usd: number;
}

export interface BenchmarkResults {
  timestamp: string;
  total_scenarios: number;
  trials_per_scenario: number;
  hitl_mode: string;
  policies: Record<string, PolicyMetrics>;
  raw_records?: any[];
}

export interface ScenarioItem {
  id: string;
  category: string;
  task_intent: string;
  requested_tool: string;
  target_resource: string;
  parameters: Record<string, any>;
  ground_truth: 'SAFE' | 'UNSAFE';
  ideal_security_decision: DecisionType;
  attack_type: string;
  description: string;
}

export interface SandboxFileEntry {
  path: string;
  type: 'file' | 'directory';
  name: string;
  size: number;
}

export interface RiskConfig {
  formula: string;
  weights: {
    w_resource_sensitivity: number;
    w_tool_risk: number;
    w_intent_mismatch: number;
    w_anomaly: number;
  };
  thresholds: {
    allow_threshold: number;
    block_threshold: number;
    ask_human_range: string;
  };
  sensitivity_scores: Record<string, number>;
  tool_risk_scores: Record<string, number>;
}
