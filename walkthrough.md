# Phase 7 Walkthrough — AgentShield FastAPI Backend & Real-time WebSockets

## Overview
Phase 7 implements the real-time server architecture and communication layer for AgentShield. It exposes the live runtime security state, facilitates Human-In-The-Loop (HITL) review resolution, and broadcasts telemetry events through WebSockets to connected cybersecurity dashboards—all while preserving the strict Gateway interception boundary:

$$\text{AI Agent} \longrightarrow \text{AgentShield Gateway} \longrightarrow \text{Policy/Risk Decision} \longrightarrow \text{Sandbox Executor} \longrightarrow \text{Tool Execution} \longrightarrow \text{Audit Log} \longrightarrow \text{Dashboard}$$

Zero security logic has been delegated to the frontend or API layer; all policy evaluation, math scoring, and tool isolation remain strictly enforced inside the backend Gateway and Sandbox.

---

## 1. REST API Endpoint Catalog

| Method | Endpoint | Description | Real State Source |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Root service descriptor & endpoint registry | In-memory configuration |
| `GET` | `/api/health` | Gateway, sandbox, and active policy status | Live Service Container |
| `POST` | `/api/agent/run` | Executes autonomous agent task with Gateway mediation | `AgentShieldAgent` + `AgentShieldGateway` |
| `GET` | `/api/agent/sessions` | Lists past agent execution sessions | SQLite `SessionRecord` |
| `GET` | `/api/agent/sessions/{id}` | Granular steps, requests, and decisions for a session | SQLite `RequestRecord`, `DecisionRecord` |
| `GET` | `/api/requests` | Real-time intercepted requests with filtering & pagination | SQLite `RequestRecord` + `DecisionRecord` |
| `GET` | `/api/requests/{id}` | In-depth security analysis breakdown for a single call | SQLite `RequestRecord` + `DecisionRecord` |
| `GET` | `/api/stats/overview` | Aggregated security metrics (total, allowed, blocked, HITL) | Live SQLite aggregates (`COUNT`, `AVG`) |
| `GET` | `/api/approvals/pending` | Live queue of tool requests paused in `ASK_HUMAN` | `HumanApprovalRegistry` |
| `POST` | `/api/approvals/{id}/resolve` | Resolves approval (`ALLOW_ONCE`, `ALLOW_SESSION`, `BLOCK`) | `HumanApprovalRegistry.resolve_approval` |
| `GET` | `/api/config/policies` | Lists available policies, baselines, and ablations | `BaseSecurityPolicy` catalog |
| `POST` | `/api/config/policies/set` | Dynamically switches Gateway enforcement policy | `AgentShieldGateway.set_policy` |
| `GET` | `/api/config/risk-engine` | Returns formula weights, thresholds, and sensitivity catalogs | `RiskScoringConfig` |
| `GET` | `/api/experiments/scenarios` | 28 benchmark scenarios with ground truth & ideal decision | `dataset.json` via `ScenarioLoader` |
| `POST` | `/api/experiments/run` | Executes comparative benchmark suite across policies | `ExperimentRunner` |
| `GET` | `/api/experiments/latest` | Reads most recently exported JSON benchmark run | `experiments/benchmark_results_*.json` |
| `GET` | `/api/experiments/history` | Lists all historical benchmark runs | `experiments/` file inventory |
| `GET` | `/api/sandbox/tree` | Hierarchical file tree inside sandbox jail | `SandboxEnvironment.list_files_tree` |
| `GET` | `/api/sandbox/file` | Safely reads isolated file content (blocks traversal) | `SandboxEnvironment.resolve_safe_path` |
| `POST` | `/api/sandbox/reset` | Resets sandbox filesystem and DB to baseline fixtures | `SandboxEnvironment.reset` |

---

## 2. WebSocket Real-Time Event Schema (`/ws/live`)

The WebSocket endpoint `/ws/live` broadcasts high-frequency security events asynchronously across all connected clients.

### Broadcast Event Types & Payloads

#### 1. Connection Handshake
```json
{
  "event_type": "CONNECTED",
  "message": "Connected to AgentShield Real-Time Security Feed",
  "active_policy": "AgentShieldPolicy"
}
```

#### 2. Tool Request Interception & Decision
```json
{
  "event_type": "TOOL_REQUEST_INTERCEPTED",
  "request_id": "req_8f1b0a23d4e7",
  "session_id": "sess_91c28f3a",
  "step_number": 1,
  "tool_name": "read_file",
  "target_resource": "secrets/.env",
  "task_intent": "Fix authentication bug in auth.py",
  "parameters": {"path": "secrets/.env"},
  "decision": "BLOCK",
  "risk_score": 88,
  "confidence": 0.95,
  "reason": "Target resource sensitivity (CRITICAL) and semantic mismatch with task intent.",
  "signals": ["critical_secret", "task_mismatch"],
  "resource_sensitivity": "CRITICAL",
  "action_risk": 20,
  "latency_ms": 1.45,
  "action_executed": false
}
```

#### 3. Human Approval Required (`ASK_HUMAN`)
```json
{
  "event_type": "HUMAN_APPROVAL_REQUESTED",
  "approval_id": "appr_4a91b2c8",
  "request_id": "req_8f1b0a23d4e7",
  "session_id": "sess_91c28f3a",
  "tool_name": "database_query",
  "target_resource": "fake_users.db",
  "risk_score": 58,
  "reason": "Moderate risk database modification requires human authorization.",
  "timeout_sec": 30.0
}
```

#### 4. Human Approval Resolved
```json
{
  "event_type": "HUMAN_APPROVAL_RESOLVED",
  "approval_id": "appr_4a91b2c8",
  "decision": "ALLOW_ONCE",
  "notes": "Authorized by security admin for DB migration."
}
```

#### 5. Agent Execution Lifecycle
```json
{
  "event_type": "AGENT_RUN_STARTED",
  "task_intent": "Fix the authentication bug in auth.py.",
  "policy_name": "AgentShieldPolicy"
}
```
```json
{
  "event_type": "AGENT_RUN_COMPLETED",
  "session_id": "sess_91c28f3a",
  "task_intent": "Fix the authentication bug in auth.py.",
  "completed": true,
  "total_calls": 2,
  "blocked_calls": 0,
  "final_answer": "Identified issue with password hash validation."
}
```

#### 6. Policy Switched
```json
{
  "event_type": "POLICY_SWITCHED",
  "active_policy": "StaticPermissionPolicy"
}
```

---

## 3. Verification & Test Results

The entire pytest test suite (50/50 unit, integration, and API tests) passes with 100% success rate:

```
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\mivai\OneDrive\Desktop\vs code folders\Projects\AgentShield
collected 50 items

tests/test_agent.py::test_mock_provider_scripted_responses PASSED        [  2%]
tests/test_agent.py::test_agent_dispatches_tool_calls_through_gateway PASSED [  4%]
tests/test_agent.py::test_agent_handles_gateway_block PASSED             [  6%]
tests/test_agent.py::test_agent_prompt_injection_simulation PASSED       [  8%]
tests/test_agent.py::test_llm_provider_factory PASSED                    [ 10%]
tests/test_api.py::test_root_and_health_endpoints PASSED                 [ 12%]
tests/test_api.py::test_agent_run_legitimate_flow PASSED                 [ 14%]
tests/test_api.py::test_agent_run_blocked_attack_flow PASSED             [ 16%]
tests/test_api.py::test_hitl_approval_workflow_via_api PASSED            [ 18%]
tests/test_api.py::test_hitl_rejection_workflow_via_api PASSED           [ 20%]
tests/test_api.py::test_websocket_realtime_connection PASSED             [ 22%]
tests/test_api.py::test_sandbox_inspection_and_traversal_prevention PASSED [ 24%]
tests/test_api.py::test_sandbox_reset_endpoint PASSED                    [ 26%]
tests/test_api.py::test_policy_config_and_switching PASSED               [ 28%]
tests/test_api.py::test_scenarios_and_benchmark_api PASSED               [ 30%]
tests/test_gateway.py::test_context_extractor PASSED                     [ 32%]
tests/test_gateway.py::test_gateway_dispatch_allow PASSED                [ 34%]
tests/test_gateway.py::test_gateway_dispatch_block PASSED                [ 36%]
tests/test_gateway.py::test_gateway_event_broadcaster PASSED             [ 38%]
tests/test_human_approval.py::test_human_approval_allow_once PASSED      [ 40%]
tests/test_human_approval.py::test_human_approval_reject_block PASSED    [ 42%]
tests/test_human_approval.py::test_human_approval_timeout_defaults_to_block PASSED [ 44%]
tests/test_human_approval.py::test_human_approval_persisted_in_database PASSED [ 46%]
tests/test_interception_boundary.py::test_end_to_end_gateway_interception_boundary PASSED [ 48%]
tests/test_policies.py::test_policy_comparison_legitimate_coding_action PASSED [ 50%]
tests/test_policies.py::test_policy_comparison_secret_attack PASSED      [ 52%]
tests/test_policies.py::test_policy_comparison_legitimate_sensitive_action PASSED [ 54%]
tests/test_policies.py::test_policy_comparison_ask_human_threshold PASSED [ 56%]
tests/test_policies.py::test_ablation_policy_variants PASSED             [ 58%]
tests/test_risk_engine.py::test_hard_rule_unconditional_blocks PASSED    [ 60%]
tests/test_risk_engine.py::test_semantic_intent_evaluator_generalization PASSED [ 62%]
tests/test_risk_engine.py::test_task_context_changes_decision_for_identical_resource PASSED [ 64%]
tests/test_risk_engine.py::test_mathematical_risk_scoring_reproducibility PASSED [ 66%]
tests/test_sandbox.py::test_sandbox_initialization_and_fixtures PASSED   [ 68%]
tests/test_sandbox.py::test_sandbox_read_and_write_file PASSED           [ 70%]
tests/test_sandbox.py::test_sandbox_path_traversal_blocked PASSED        [ 72%]
tests/test_sandbox.py::test_sandbox_delete_file PASSED                   [ 74%]
tests/test_sandbox.py::test_sandbox_list_files PASSED                    [ 76%]
tests/test_sandbox.py::test_sandbox_command_execution PASSED             [ 78%]
tests/test_sandbox.py::test_sandbox_command_timeout PASSED               [ 80%]
tests/test_sandbox.py::test_sandbox_forbidden_command_prevention PASSED  [ 82%]
tests/test_sandbox.py::test_sandbox_database_query PASSED                [ 84%]
tests/test_sandbox.py::test_sandbox_http_request_simulation PASSED       [ 86%]
tests/test_sandbox.py::test_sandbox_run_tests PASSED                     [ 88%]
tests/test_sandbox.py::test_sandbox_reset PASSED                         [ 90%]
tests/test_scenarios.py::test_scenario_dataset_structure_and_balance PASSED [ 92%]
tests/test_scenarios.py::test_metrics_calculation_accuracy PASSED        [ 94%]
tests/test_scenarios.py::test_full_comparative_benchmark_run PASSED      [ 96%]
tests/test_scenarios.py::test_ablation_suite_benchmark PASSED            [ 98%]
tests/test_scenarios.py::test_metrics_recomputation_from_raw_json PASSED [100%]

================== 50 passed in 136.24s (0:02:16) ==================
```

---

## 4. Security & Enforcement Invariants Summary

1. **No Frontend Authorization Boundary**: The frontend only renders received state and sends user approval intents (`POST /api/approvals/{id}/resolve`). All security calculations and enforcement occur synchronously in the backend Gateway.
2. **Zero Mock Telemetry**: The overview endpoint (`GET /api/stats/overview`) and request logs (`GET /api/requests`) execute direct SQL queries (`COUNT`, `AVG`, filters) on SQLite tables (`RequestRecord`, `DecisionRecord`, `HumanApprovalRecord`).
3. **Single Human Approval Mechanism**: Approvals directly resolve events on `service.approval_registry` (`HumanApprovalRegistry`), which unblocks the async gateway pause.
4. **Execution Isolation**: Path traversal attempts via API queries (e.g. `GET /api/sandbox/file?path=../../windows/system32/cmd.exe`) are trapped by `resolve_safe_path()` and returned as `403 Forbidden`.

---

## 5. Phase 8: Cybersecurity Dashboard Frontend Architecture

The frontend is implemented as a presentation and interaction layer over the existing FastAPI and WebSocket backend.

### Component Structure:
- `src/context/SecurityContext.tsx`: Manages WebSocket lifecycle, auto-reconnects, real-time message stream, and pending approvals.
- `src/services/api.ts`: Typed client mapping directly to backend REST endpoints.
- `src/components/Header.tsx`: System status, active policy dropdown, pending approvals counter, and live connection indicator.
- `src/components/Navigation.tsx`: Tab navigation for the 8 views.
- `src/components/SecurityOverview.tsx`: Real SOC metrics, threat distribution bar, and live event feed snippet.
- `src/components/LiveActivityFeed.tsx`: Streaming WebSocket table with decision badges, search filters, and pause/resume capability.
- `src/components/RequestInspector.tsx`: 8-stage interactive visual pipeline:
  $$\text{Task Intent} \longrightarrow \text{Tool Request} \longrightarrow \text{Target Resource} \longrightarrow \text{Resource Sensitivity} \longrightarrow \text{Tool Risk} \longrightarrow \text{Risk Score} \longrightarrow \text{Gateway Decision} \longrightarrow \text{Sandbox Outcome}$$
- `src/components/HumanApprovalModal.tsx`: Real-time HITL authorization modal for resolving paused requests (`ALLOW_ONCE`, `ALLOW_SESSION`, `BLOCK`).
- `src/components/EvaluationCenter.tsx`: 28-scenario comparative benchmark metrics table and scenario dataset explorer.
- `src/components/AblationView.tsx`: Multi-signal ablation impact cards quantifying the security necessity of each signal.
- `src/components/SandboxExplorer.tsx`: Isolated sandbox tree browser, safe file syntax viewer, and sandbox reset trigger.
- `src/components/AgentRunnerModal.tsx`: Interactive demo launcher with preset and custom task execution.
- `src/components/RiskConfigViewer.tsx`: Mathematical formula parameter inspector ($w_{res}, w_{tool}, w_{intent}, w_{anom}$, and threshold boundaries).

### Confirmation of Security Boundary:
- **Zero Frontend Authorization Logic**: All authorization calculations occur exclusively inside the backend Gateway.
- **Zero Mock Metrics**: All dashboard statistics and evaluation numbers are fetched from SQLite and Phase 6 benchmark execution logs.
- **Jail Integrity**: Sandbox Explorer only communicates through `resolve_safe_path()`. Host filesystem paths cannot be browsed.

### Build Verification:
- `npm run build` completed cleanly (`✓ built in 21.51s`, zero TypeScript errors).
- Full backend test suite: **50/50 tests passing (100% success rate)**.
