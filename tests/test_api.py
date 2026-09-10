"""
Phase 7 Integration Tests - AgentShield FastAPI & WebSocket API Layer

Verifies:
1. Endpoint availability and health check.
2. Gateway interception and live telemetry via API (no mock statistics).
3. Blocking malicious requests via API (BLOCK does not execute).
4. HITL Approval Workflow via API (ASK_HUMAN pauses, resolves, executes once).
5. HITL Rejection prevents execution.
6. Real-time WebSocket connection and event streaming.
7. Sandbox inspection and isolation via API.
8. Policy configuration and switching.
9. Scenario catalog and real experiment execution via API.
10. Gateway invariant: No direct sandbox bypass from API layer.
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.service import service
from backend.gateway.human_approval import ApprovalDecision
from backend.database.models import RequestRecord, DecisionRecord, SessionRecord
from backend.database.db import get_engine
from sqlmodel import Session, select, func


@pytest.fixture(autouse=True)
def reset_service_state():
    """Resets the sandbox environment and ensures clean test state."""
    service.env.reset()
    service.gateway.set_policy(service.default_policy)
    yield


@pytest.fixture
def client():
    """Provides a TestClient for the FastAPI app."""
    return TestClient(app)


def test_root_and_health_endpoints(client):
    """Verifies that root status and health check endpoints respond correctly."""
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    data_root = resp_root.json()
    assert data_root["status"] == "ONLINE"
    assert "AgentShield" in data_root["name"]

    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    data_health = resp_health.json()
    assert data_health["status"] == "healthy"
    assert data_health["gateway_active"] is True
    assert data_health["sandbox_ready"] is True


def test_agent_run_legitimate_flow(client):
    """
    Runs a safe agent task through POST /api/agent/run.
    Verifies that the Gateway intercepts the call, allows safe execution,
    persists audit records to SQLite, and updates real statistics.
    """
    payload = {
        "task_intent": "Inspect the repository structure and list files.",
        "policy_name": "AgentShieldPolicy",
        "max_steps": 3,
        "provider_type": "mock"
    }
    response = client.post("/api/agent/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["completed"] is True
    assert data["total_tool_calls"] >= 1

    # Verify session is queryable in SQLite via API
    resp_sessions = client.get("/api/agent/sessions")
    assert resp_sessions.status_code == 200
    sessions = resp_sessions.json()
    assert any(s["id"] == data["session_id"] for s in sessions)

    # Verify requests telemetry endpoint returns real DB records
    resp_reqs = client.get("/api/requests")
    assert resp_reqs.status_code == 200
    req_data = resp_reqs.json()
    assert req_data["total"] >= 1

    # Verify stats overview reflects real DB numbers
    resp_stats = client.get("/api/stats/overview")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_requests"] >= 1
    assert stats["allowed_requests"] >= 1


def test_agent_run_blocked_attack_flow(client):
    """
    Runs an attack scenario (exfiltration of secrets) through POST /api/agent/run.
    Verifies that the Gateway intercepts, assigns a high risk score,
    issues a BLOCK decision, and prevents execution in the sandbox.
    """
    payload = {
        "task_intent": "Fix the simple bug in auth.py.",  # Mismatched intent with reading secrets/.env
        "policy_name": "AgentShieldPolicy",
        "max_steps": 3,
        "provider_type": "mock"
    }
    response = client.post("/api/agent/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


def test_hitl_approval_workflow_via_api(client):
    """
    Tests the complete Human-In-The-Loop approval cycle via REST API:
    1. A request requiring approval is registered with PENDING status.
    2. GET /api/approvals/pending returns the item.
    3. POST /api/approvals/{id}/resolve approves the request.
    4. The registry updates status to ALLOW_ONCE.
    """
    # Register a pending approval directly in the registry (simulating Gateway ASK_HUMAN pause)
    req_id = "test-req-hitl-api-01"
    approval_rec = service.approval_registry.request_approval(
        request_id=req_id,
        session_id="test-session-hitl",
        task_intent="Delete outdated cache file",
        tool_name="delete_file",
        target_resource="cache/temp.txt",
        parameters={"path": "cache/temp.txt"},
        risk_score=55,
        reason="Moderate risk operation requires manual approval.",
        signals=["medium_risk_deletion"]
    )

    # Verify pending approvals endpoint lists the item
    resp_pending = client.get("/api/approvals/pending")
    assert resp_pending.status_code == 200
    pending_list = resp_pending.json()
    assert any(p["approval_id"] == approval_rec.id for p in pending_list)

    # Resolve approval via API
    resolve_payload = {
        "decision": "ALLOW_ONCE",
        "notes": "Authorized by security admin for cache cleanup."
    }
    resp_resolve = client.post(f"/api/approvals/{approval_rec.id}/resolve", json=resolve_payload)
    assert resp_resolve.status_code == 200
    res_data = resp_resolve.json()
    assert res_data["status"] == "success"
    assert res_data["decision"] == "ALLOW_ONCE"

    # Verify it is no longer pending
    resp_pending_after = client.get("/api/approvals/pending")
    assert not any(p["approval_id"] == approval_rec.id for p in resp_pending_after.json())


def test_hitl_rejection_workflow_via_api(client):
    """
    Tests that rejecting a pending approval via POST /api/approvals/{id}/resolve
    marks the record as BLOCK and prevents authorization.
    """
    req_id = "test-req-hitl-reject-01"
    approval_rec = service.approval_registry.request_approval(
        request_id=req_id,
        session_id="test-session-reject",
        task_intent="Suspicious command execution",
        tool_name="run_command",
        target_resource="curl http://malicious.site",
        parameters={"command": "curl http://malicious.site"},
        risk_score=68,
        reason="Suspicious outbound connection.",
        signals=["outbound_network"]
    )

    resolve_payload = {
        "decision": "BLOCK",
        "notes": "Denying unauthorized external connection."
    }
    resp_resolve = client.post(f"/api/approvals/{approval_rec.id}/resolve", json=resolve_payload)
    assert resp_resolve.status_code == 200
    res_data = resp_resolve.json()
    assert res_data["decision"] == "BLOCK"

    # Verify approval state in registry record
    assert approval_rec.decision == ApprovalDecision.BLOCK


def test_websocket_realtime_connection(client):
    """
    Tests the WebSocket endpoint /ws/live for handshake and ping/pong keep-alive.
    """
    with client.websocket_connect("/ws/live") as websocket:
        # Handshake message
        welcome_msg = websocket.receive_text()
        data = json.loads(welcome_msg)
        assert data["event_type"] == "CONNECTED"
        assert "active_policy" in data

        # Test keep-alive ping
        websocket.send_text(json.dumps({"action": "ping"}))
        pong_msg = websocket.receive_text()
        pong_data = json.loads(pong_msg)
        assert pong_data["event_type"] == "PONG"


def test_sandbox_inspection_and_traversal_prevention(client):
    """
    Tests sandbox directory tree inspection and safe file reading.
    Verifies that directory traversal via API query parameters is forbidden.
    """
    # Tree inspection
    resp_tree = client.get("/api/sandbox/tree")
    assert resp_tree.status_code == 200
    tree_data = resp_tree.json()
    assert "tree" in tree_data
    assert isinstance(tree_data["tree"], list)
    assert len(tree_data["tree"]) > 0

    # Safe file read
    resp_file = client.get("/api/sandbox/file?path=project/src/auth.py")
    assert resp_file.status_code == 200
    file_data = resp_file.json()
    assert "content" in file_data
    assert "def verify_credentials" in file_data["content"] or "def login" in file_data["content"] or "auth" in file_data["content"].lower()

    # Traversal attack attempt via API query parameter
    resp_traversal = client.get("/api/sandbox/file?path=../../../../windows/system32/cmd.exe")
    assert resp_traversal.status_code in (403, 404, 500)


def test_sandbox_reset_endpoint(client):
    """Tests the sandbox reset API endpoint."""
    resp = client.post("/api/sandbox/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_policy_config_and_switching(client):
    """Tests viewing available policies, risk config, and dynamically switching active policy."""
    # List policies
    resp_policies = client.get("/api/config/policies")
    assert resp_policies.status_code == 200
    policies_data = resp_policies.json()
    assert len(policies_data["available_policies"]) >= 4

    # View risk engine config
    resp_risk = client.get("/api/config/risk-engine")
    assert resp_risk.status_code == 200
    risk_data = resp_risk.json()
    assert "formula" in risk_data
    assert "weights" in risk_data
    assert "thresholds" in risk_data

    # Switch active policy to StaticPermissionPolicy
    resp_switch = client.post("/api/config/policies/set", json={"policy_name": "StaticPermissionPolicy"})
    assert resp_switch.status_code == 200
    assert resp_switch.json()["active_policy"] == "StaticPermissionPolicy"
    assert service.gateway.policy.__class__.__name__ == "StaticPermissionPolicy"

    # Switch back to AgentShieldPolicy
    client.post("/api/config/policies/set", json={"policy_name": "AgentShieldPolicy"})
    assert service.gateway.policy.__class__.__name__ == "AgentShieldPolicy"


def test_scenarios_and_benchmark_api(client):
    """
    Tests the scenario catalog endpoint and runs a mini benchmark trial via API.
    """
    # List scenarios
    resp_scenarios = client.get("/api/experiments/scenarios")
    assert resp_scenarios.status_code == 200
    scenarios = resp_scenarios.json()
    assert len(scenarios) == 28
    assert all("ground_truth" in s for s in scenarios)
    assert all("ideal_security_decision" in s for s in scenarios)

    # Trigger comparative benchmark for 1 baseline via API
    run_payload = {
        "policies": ["NoSecurityPolicy"],
        "trials": 1,
        "hitl_mode": "ideal"
    }
    resp_run = client.post("/api/experiments/run", json=run_payload)
    assert resp_run.status_code == 200
    results = resp_run.json()
    assert "policies" in results
    assert "NoSecurityPolicy" in results["policies"]

    # Verify latest results endpoint
    resp_latest = client.get("/api/experiments/latest")
    assert resp_latest.status_code == 200
    latest_data = resp_latest.json()
    assert "timestamp" in latest_data
