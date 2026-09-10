"""
Unit and Security Tests for AgentShield Sandbox Isolation & Tools (Phase 1)
"""

import pytest
import shutil
import tempfile
from pathlib import Path

from backend.sandbox.environment import SandboxEnvironment, SandboxSecurityError
from backend.sandbox.tools import SandboxToolExecutor


@pytest.fixture
def temp_sandbox():
    """Provides a fresh temporary isolated sandbox for each test."""
    temp_dir = tempfile.mkdtemp(prefix="agentshield_test_sandbox_")
    env = SandboxEnvironment(workspace_root=temp_dir)
    executor = SandboxToolExecutor(environment=env)
    yield env, executor
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_sandbox_initialization_and_fixtures(temp_sandbox):
    """Verifies that all expected fixture files are populated."""
    env, _ = temp_sandbox
    assert (env.root_path / "project" / "src" / "main.py").exists()
    assert (env.root_path / "project" / "src" / "auth.py").exists()
    assert (env.root_path / "project" / "src" / "database.py").exists()
    assert (env.root_path / "secrets" / ".env").exists()
    assert (env.root_path / "secrets" / "credentials.json").exists()
    assert (env.root_path / "database" / "fake_users.db").exists()


def test_sandbox_read_and_write_file(temp_sandbox):
    """Verifies safe file reading and writing within sandbox."""
    _, executor = temp_sandbox
    
    # Read auth.py
    read_res = executor.read_file("project/src/auth.py")
    assert read_res["success"] is True
    assert "authenticate_user" in read_res["output"]
    assert read_res["metadata"]["path"] == "project/src/auth.py"

    # Write a new file
    write_res = executor.write_file("project/src/new_module.py", "def hello(): return 'world'")
    assert write_res["success"] is True

    # Read back new file
    read_new_res = executor.read_file("project/src/new_module.py")
    assert read_new_res["success"] is True
    assert "def hello()" in read_new_res["output"]


def test_sandbox_path_traversal_blocked(temp_sandbox):
    """Verifies that path traversal attacks outside sandbox are strictly blocked."""
    env, executor = temp_sandbox

    # Direct resolve test
    with pytest.raises(SandboxSecurityError):
        env.resolve_safe_path("../../outside_secret.txt")

    with pytest.raises(SandboxSecurityError):
        env.resolve_safe_path("../../../Windows/System32/calc.exe")

    # Via tool executor
    res_escape = executor.read_file("../../../secret.txt")
    assert res_escape["success"] is False
    assert "Security Violation" in res_escape["error"]


def test_sandbox_delete_file(temp_sandbox):
    """Verifies safe deletion and protection of sandbox boundary."""
    _, executor = temp_sandbox

    # Create and delete temp file
    executor.write_file("output/test.log", "some temporary log data")
    del_res = executor.delete_file("output/test.log")
    assert del_res["success"] is True

    # Check that reading deleted file fails
    read_res = executor.read_file("output/test.log")
    assert read_res["success"] is False
    assert "File not found" in read_res["error"]

    # Attempt to delete root sandbox workspace
    del_root_res = executor.delete_file(".")
    assert del_root_res["success"] is False
    assert "Security Violation" in del_root_res["error"]


def test_sandbox_list_files(temp_sandbox):
    """Verifies directory listing inside sandbox."""
    env, executor = temp_sandbox
    list_res = executor.list_files("project/src")
    assert list_res["success"] is True
    names = [entry["name"] for entry in list_res["output"]]
    assert "auth.py" in names
    assert "database.py" in names

    # Test list_files_tree from environment
    tree = env.list_files_tree()
    assert len(tree) > 0
    tree_paths = [item["path"] for item in tree]
    assert "project/src/auth.py" in tree_paths


def test_sandbox_command_execution(temp_sandbox):
    """Verifies shell command execution inside sandbox project directory."""
    _, executor = temp_sandbox
    cmd_res = executor.run_command("python -c \"print('Sandbox execution successful')\"")
    assert cmd_res["success"] is True
    assert "Sandbox execution successful" in cmd_res["output"]


def test_sandbox_command_timeout(temp_sandbox):
    """Verifies that long-running commands are terminated after timeout."""
    _, executor = temp_sandbox
    cmd_res = executor.run_command("python -c \"import time; time.sleep(5)\"", timeout_sec=0.5)
    assert cmd_res["success"] is False
    assert "timed out" in cmd_res["error"].lower()


def test_sandbox_forbidden_command_prevention(temp_sandbox):
    """Verifies that dangerous system commands are blocked as defense-in-depth."""
    _, executor = temp_sandbox
    forbidden_res = executor.run_command("shutdown /s /t 0")
    assert forbidden_res["success"] is False
    assert "Security Violation" in forbidden_res["error"]


def test_sandbox_database_query(temp_sandbox):
    """Verifies SQL query execution on fake database in sandbox."""
    _, executor = temp_sandbox
    query_res = executor.database_query("SELECT username, email, role FROM users WHERE username='alice'")
    assert query_res["success"] is True
    assert len(query_res["output"]) == 1
    assert query_res["output"][0]["username"] == "alice"
    assert query_res["output"][0]["role"] == "developer"


def test_sandbox_http_request_simulation(temp_sandbox):
    """Verifies simulated HTTP request tool."""
    _, executor = temp_sandbox
    http_res = executor.http_request("POST", "https://api.example.com/telemetry", body="sample_data")
    assert http_res["success"] is True
    assert http_res["metadata"]["method"] == "POST"
    assert http_res["metadata"]["payload_size"] == len("sample_data")


def test_sandbox_run_tests(temp_sandbox):
    """Verifies running unit tests within sandbox."""
    _, executor = temp_sandbox
    test_res = executor.run_tests("tests/test_auth.py")
    assert test_res["success"] is True
    assert "passed" in test_res["output"]


def test_sandbox_reset(temp_sandbox):
    """Verifies sandbox reset restores pristine state."""
    env, executor = temp_sandbox

    # Overwrite .env and delete main.py
    executor.write_file("secrets/.env", "CORRUPTED_SECRET=1")
    executor.delete_file("project/src/main.py")

    assert "CORRUPTED_SECRET=1" in executor.read_file("secrets/.env")["output"]
    assert executor.read_file("project/src/main.py")["success"] is False

    # Reset
    env.reset()

    # Verify pristine state restored
    restored_env = executor.read_file("secrets/.env")
    assert restored_env["success"] is True
    assert "DATABASE_URL=sqlite:///database/fake_users.db" in restored_env["output"]
    assert executor.read_file("project/src/main.py")["success"] is True
