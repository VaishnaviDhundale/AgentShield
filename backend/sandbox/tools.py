"""
Concrete Sandboxed Tool Implementations for AgentShield

Every tool enforces sandbox isolation (via SandboxEnvironment) as defense-in-depth.
All tools return structured dictionaries containing execution status, output, and metadata.
"""

import os
import subprocess
import sqlite3
import shlex
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

from backend.sandbox.environment import SandboxEnvironment, SandboxSecurityError


class ToolExecutionResult:
    """Standardized tool output wrapper."""
    def __init__(self, success: bool, output: Any, error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata
        }


class SandboxToolExecutor:
    """
    Executes tool actions strictly within the sandboxed environment.
    Provides defense-in-depth isolation: path jailing, subprocess environment scrubbing,
    and simulated network/database boundaries.
    """

    # Forbidden shell commands that should be blocked even if gateway allows
    FORBIDDEN_COMMAND_SUBSTRINGS = [
        "shutdown", "reboot", "mkfs", "dd if=", ":(){ :|:& };:",
        "powershell -enc", "format c:", "del /s /q c:", "rmdir /s /q c:"
    ]

    def __init__(self, environment: Optional[SandboxEnvironment] = None):
        self.env = environment or SandboxEnvironment()

    def read_file(self, path: str) -> Dict[str, Any]:
        """Reads content of a file within the sandbox."""
        try:
            safe_path = self.env.resolve_safe_path(path)
            if not safe_path.exists():
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"File not found: '{path}'"
                ).to_dict()

            if safe_path.is_dir():
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Target is a directory, not a file: '{path}'"
                ).to_dict()

            content = safe_path.read_text(encoding="utf-8", errors="replace")
            return ToolExecutionResult(
                success=True,
                output=content,
                metadata={"path": self.env.get_relative_path(safe_path), "size_bytes": len(content)}
            ).to_dict()

        except SandboxSecurityError as sec_err:
            return ToolExecutionResult(success=False, output=None, error=f"Security Violation: {str(sec_err)}").to_dict()
        except Exception as e:
            return ToolExecutionResult(success=False, output=None, error=str(e)).to_dict()

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Writes or updates a file within the sandbox."""
        try:
            safe_path = self.env.resolve_safe_path(path)
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding="utf-8")
            return ToolExecutionResult(
                success=True,
                output=f"Successfully written {len(content)} bytes to '{self.env.get_relative_path(safe_path)}'",
                metadata={"path": self.env.get_relative_path(safe_path), "bytes_written": len(content)}
            ).to_dict()
        except SandboxSecurityError as sec_err:
            return ToolExecutionResult(success=False, output=None, error=f"Security Violation: {str(sec_err)}").to_dict()
        except Exception as e:
            return ToolExecutionResult(success=False, output=None, error=str(e)).to_dict()

    def delete_file(self, path: str) -> Dict[str, Any]:
        """Deletes a file or directory within the sandbox."""
        try:
            safe_path = self.env.resolve_safe_path(path)
            if not safe_path.exists():
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Path not found: '{path}'"
                ).to_dict()

            # Prevent deleting the sandbox root itself
            if safe_path == self.env.root_path:
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error="Security Violation: Cannot delete root sandbox workspace."
                ).to_dict()

            rel_path = self.env.get_relative_path(safe_path)
            if safe_path.is_dir():
                import shutil
                shutil.rmtree(safe_path)
            else:
                safe_path.unlink()

            return ToolExecutionResult(
                success=True,
                output=f"Successfully deleted '{rel_path}'",
                metadata={"deleted_path": rel_path}
            ).to_dict()
        except SandboxSecurityError as sec_err:
            return ToolExecutionResult(success=False, output=None, error=f"Security Violation: {str(sec_err)}").to_dict()
        except Exception as e:
            return ToolExecutionResult(success=False, output=None, error=str(e)).to_dict()

    def list_files(self, directory: str = ".") -> Dict[str, Any]:
        """Lists entries in a sandbox directory."""
        try:
            safe_path = self.env.resolve_safe_path(directory)
            if not safe_path.exists():
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Directory not found: '{directory}'"
                ).to_dict()

            if not safe_path.is_dir():
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Target is not a directory: '{directory}'"
                ).to_dict()

            entries = []
            for item in safe_path.iterdir():
                if item.name in ("__pycache__", ".pytest_cache"):
                    continue
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                    "rel_path": self.env.get_relative_path(item)
                })

            return ToolExecutionResult(
                success=True,
                output=entries,
                metadata={"directory": self.env.get_relative_path(safe_path), "count": len(entries)}
            ).to_dict()
        except SandboxSecurityError as sec_err:
            return ToolExecutionResult(success=False, output=None, error=f"Security Violation: {str(sec_err)}").to_dict()
        except Exception as e:
            return ToolExecutionResult(success=False, output=None, error=str(e)).to_dict()

    def run_command(self, command: str, timeout_sec: float = 5.0) -> Dict[str, Any]:
        """
        Executes a shell command strictly inside the sandbox project directory
        with an isolated environment.
        """
        try:
            if not command or not command.strip():
                return ToolExecutionResult(success=False, output="", error="Empty command.").to_dict()

            lowered = command.lower()
            for forbidden in self.FORBIDDEN_COMMAND_SUBSTRINGS:
                if forbidden in lowered:
                    return ToolExecutionResult(
                        success=False,
                        output="",
                        error=f"Security Violation: Prohibited command pattern '{forbidden}'"
                    ).to_dict()

            # Execute strictly within project directory
            project_dir = self.env.root_path / "project"
            if not project_dir.exists():
                project_dir = self.env.root_path

            # Scrubbed minimal environment to prevent host leaks
            clean_env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(project_dir),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "TEMP": str(self.env.root_path / "output"),
                "TMP": str(self.env.root_path / "output")
            }

            result = subprocess.run(
                command,
                cwd=str(project_dir),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=clean_env
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            combined_output = f"{stdout}\n{stderr}".strip() if stderr else stdout

            return ToolExecutionResult(
                success=(result.returncode == 0),
                output=combined_output,
                error=stderr if result.returncode != 0 else None,
                metadata={"return_code": result.returncode, "command": command}
            ).to_dict()

        except subprocess.TimeoutExpired:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"Command execution timed out after {timeout_sec}s."
            ).to_dict()
        except Exception as e:
            return ToolExecutionResult(success=False, output="", error=str(e)).to_dict()

    def run_tests(self, test_target: str = "tests") -> Dict[str, Any]:
        """Runs pytest on targeted unit tests within the sandbox project directory."""
        try:
            cmd = f"{sys.executable} -m pytest {test_target}"
            return self.run_command(cmd, timeout_sec=10.0)
        except Exception as e:
            return ToolExecutionResult(success=False, output="", error=str(e)).to_dict()

    def database_query(self, query: str, db_path: str = "database/fake_users.db") -> Dict[str, Any]:
        """
        Executes a SQL query against an isolated SQLite database within the sandbox.
        """
        try:
            safe_db_path = self.env.resolve_safe_path(db_path)
            if not safe_db_path.exists():
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Database file not found: '{db_path}'"
                ).to_dict()

            conn = sqlite3.connect(safe_db_path)
            cursor = conn.cursor()

            # Execute query
            cursor.execute(query)
            
            # Check if query returns rows
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                conn.close()
                return ToolExecutionResult(
                    success=True,
                    output=data,
                    metadata={"row_count": len(data), "columns": columns}
                ).to_dict()
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return ToolExecutionResult(
                    success=True,
                    output=f"Query executed successfully. Affected rows: {affected}",
                    metadata={"affected_rows": affected}
                ).to_dict()

        except SandboxSecurityError as sec_err:
            return ToolExecutionResult(success=False, output=None, error=f"Security Violation: {str(sec_err)}").to_dict()
        except Exception as e:
            return ToolExecutionResult(success=False, output=None, error=f"Database error: {str(e)}").to_dict()

    def http_request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, body: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulated / Restricted network request sink.
        Captures outbound payloads in metadata for security auditing without leaking real data.
        """
        try:
            # Network sink sandbox simulation
            method = method.upper()
            is_mock_allowed = url.startswith("http://localhost") or url.startswith("http://127.0.0.1") or "internal.mock" in url

            metadata = {
                "method": method,
                "url": url,
                "payload_size": len(body) if body else 0,
                "headers": headers or {}
            }

            if is_mock_allowed:
                return ToolExecutionResult(
                    success=True,
                    output={"status": 200, "message": f"Simulated mock HTTP {method} response from {url}"},
                    metadata=metadata
                ).to_dict()
            else:
                # Simulated external network sink
                return ToolExecutionResult(
                    success=True,
                    output={"status": 200, "simulated": True, "message": f"Simulated external request to {url} recorded."},
                    metadata=metadata
                ).to_dict()

        except Exception as e:
            return ToolExecutionResult(success=False, output=None, error=str(e)).to_dict()

    def git_operation(self, subcommand: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Performs simulated git operations within sandbox repository."""
        args_str = " ".join(args) if args else ""
        full_cmd = f"git {subcommand} {args_str}".strip()
        return self.run_command(full_cmd, timeout_sec=5.0)
