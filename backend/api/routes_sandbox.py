"""
Sandbox Management and Inspection REST Endpoints for AgentShield
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.api.service import service
from backend.api.websocket_manager import ws_manager
from backend.sandbox.environment import SandboxSecurityError

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox"])


class ResetSandboxPayload(BaseModel):
    hard_reset: bool = True


@router.get("/tree")
def get_sandbox_file_tree():
    """
    Returns the current directory tree of the isolated sandbox filesystem.
    """
    tree = service.env.list_files_tree()
    return {
        "sandbox_root": str(service.env.root_path.name),
        "tree": tree
    }


@router.get("/file")
def view_sandbox_file(path: str = Query(..., description="Relative path within sandbox")):
    """
    Safely inspects file contents within the sandbox jail.
    Path traversal attacks are blocked by resolve_safe_path.
    """
    try:
        resolved = service.env.resolve_safe_path(path)
        if not resolved.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        if resolved.is_dir():
            raise HTTPException(status_code=400, detail="Target path is a directory, not a file.")
        
        content = resolved.read_text(encoding="utf-8", errors="replace")
        return {
            "path": path,
            "size_bytes": resolved.stat().st_size,
            "content": content
        }
    except SandboxSecurityError as sse:
        raise HTTPException(status_code=403, detail=str(sse))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_sandbox(payload: ResetSandboxPayload = ResetSandboxPayload()):
    """
    Resets the sandbox filesystem and databases back to pristine baseline fixture state.
    """
    service.env.reset()
    
    await ws_manager.broadcast({
        "event_type": "SANDBOX_RESET",
        "message": "Sandbox environment reset to pristine baseline fixtures."
    })
    
    return {
        "status": "success",
        "message": "Sandbox environment restored to baseline fixtures."
    }
