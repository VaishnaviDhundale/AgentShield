"""
Sandbox Environment Manager for AgentShield

Provides filesystem isolation, strict path traversal / jail checks,
and resettable simulation state from pre-configured fixtures.
"""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional, Union, List, Dict, Any


class SandboxSecurityError(Exception):
    """Raised when an action violates sandbox isolation or security boundaries."""
    pass


class SandboxEnvironment:
    """
    Manages the isolated sandbox workspace for AI agent execution.
    Guarantees no access outside the designated sandbox root directory.
    """

    def __init__(self, workspace_root: Optional[Union[str, Path]] = None, fixtures_dir: Optional[Union[str, Path]] = None):
        if workspace_root is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.root_path = (base_dir / "sandbox_runtime").resolve()
        else:
            self.root_path = Path(workspace_root).resolve()

        if fixtures_dir is None:
            self.fixtures_path = (Path(__file__).resolve().parent / "fixtures").resolve()
        else:
            self.fixtures_path = Path(fixtures_dir).resolve()

        self.ensure_initialized()

    def ensure_initialized(self) -> None:
        """Ensures the sandbox directory exists and is populated."""
        if not self.root_path.exists() or not any(self.root_path.iterdir()):
            self.reset()

    def reset(self) -> None:
        """
        Completely resets the sandbox filesystem back to the pristine state
        defined in the fixtures directory.
        """
        if self.root_path.exists():
            shutil.rmtree(self.root_path, ignore_errors=True)

        self.root_path.mkdir(parents=True, exist_ok=True)

        if self.fixtures_path.exists():
            # Copy all files and folders from fixtures
            for item in self.fixtures_path.iterdir():
                if item.name == "__pycache__" or item.name == "init_db.py":
                    continue
                dest_path = self.root_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest_path)

        # Re-initialize clean SQLite db if needed
        db_path = self.root_path / "database" / "fake_users.db"
        self._ensure_database(db_path)

    def _ensure_database(self, db_path: Path) -> None:
        """Creates clean fake_users.db tables if missing."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not db_path.exists() or db_path.stat().st_size == 0:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                api_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            sample_users = [
                ("alice", "alice@example.internal", "developer", "tok_fake_user_alice_111"),
                ("bob", "bob@example.internal", "developer", "tok_fake_user_bob_222"),
                ("charlie", "charlie@example.internal", "analyst", "tok_fake_user_charlie_333"),
                ("admin", "security-admin@example.internal", "administrator", "tok_fake_admin_999_critical")
            ]
            cursor.executemany(
                "INSERT OR IGNORE INTO users (username, email, role, api_token) VALUES (?, ?, ?, ?)",
                sample_users
            )
            conn.commit()
            conn.close()

    def resolve_safe_path(self, target_path: Union[str, Path]) -> Path:
        """
        Validates and resolves a path strictly within the sandbox jail root.
        
        Raises SandboxSecurityError on directory traversal (e.g. `../../`, `/etc/passwd`)
        or symlink escapes.
        """
        if not target_path or not str(target_path).strip():
            raise SandboxSecurityError("Empty or invalid target path provided.")

        raw_str = str(target_path).replace("\\", "/").strip()

        # Disallow explicit root escapes or known dangerous root anchors on unix/windows
        if raw_str.startswith("/") or (len(raw_str) > 1 and raw_str[1] == ":"):
            # Check if it already points inside self.root_path
            resolved = Path(raw_str).resolve()
        else:
            resolved = (self.root_path / raw_str).resolve()

        # Strict containment check
        try:
            resolved.relative_to(self.root_path)
        except ValueError:
            raise SandboxSecurityError(
                f"Path traversal blocked: target '{target_path}' resolves outside sandbox boundary."
            )

        return resolved

    def get_relative_path(self, path: Union[str, Path]) -> str:
        """Returns relative path string from sandbox root."""
        resolved = self.resolve_safe_path(path)
        rel = resolved.relative_to(self.root_path)
        return str(rel).replace("\\", "/")

    def list_files_tree(self, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Returns a hierarchical or flat list representation of sandbox files for dashboard."""
        results = []
        for root, dirs, files in os.walk(self.root_path):
            rel_root = Path(root).relative_to(self.root_path)
            depth = len(rel_root.parts)
            if depth > max_depth:
                continue

            for d in dirs:
                if d in ("__pycache__", ".pytest_cache"):
                    continue
                dir_path = (Path(root) / d).resolve()
                results.append({
                    "path": str(dir_path.relative_to(self.root_path)).replace("\\", "/"),
                    "type": "directory",
                    "name": d,
                    "size": 0
                })

            for f in files:
                if f.endswith(".pyc"):
                    continue
                file_path = (Path(root) / f).resolve()
                results.append({
                    "path": str(file_path.relative_to(self.root_path)).replace("\\", "/"),
                    "type": "file",
                    "name": f,
                    "size": file_path.stat().st_size if file_path.exists() else 0
                })
        return sorted(results, key=lambda x: (x["type"] != "directory", x["path"]))
