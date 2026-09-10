"""
AgentShield - FastAPI Backend & Real-time WebSockets Server
"""

import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.service import service
from backend.api.websocket_manager import ws_manager
from backend.api.routes_agent import router as agent_router
from backend.api.routes_requests import router as requests_router
from backend.api.routes_approval import router as approval_router
from backend.api.routes_experiments import router as experiments_router
from backend.api.routes_sandbox import router as sandbox_router
from backend.api.routes_config import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for startup and shutdown routines."""
    # Ensure sandbox and DB are ready
    service.env.reset()
    yield
    # Cleanup if necessary


app = FastAPI(
    title="AgentShield API",
    description="Runtime Security Control Layer for AI Agents - Real-time Gateway, Risk Scoring, HITL Approval, and Scientific Evaluation.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local React/Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular REST routers
app.include_router(agent_router)
app.include_router(requests_router)
app.include_router(approval_router)
app.include_router(experiments_router)
app.include_router(sandbox_router)
app.include_router(config_router)


@app.get("/")
def root_status():
    """AgentShield status and endpoint directory."""
    return {
        "name": "AgentShield Runtime Security Control Layer",
        "version": "1.0.0",
        "status": "ONLINE",
        "active_policy": service.gateway.policy.__class__.__name__,
        "websocket_endpoint": "/ws/live",
        "docs": "/docs"
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "gateway_active": True,
        "sandbox_ready": service.env.root_path.exists(),
        "active_policy": service.gateway.policy.__class__.__name__,
        "pending_approvals": len(service.approval_registry.get_pending_approvals())
    }


@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    """
    Real-time WebSocket feed for AgentShield Dashboard.
    Streams tool requests, policy decisions, risk scores, rule activations,
    HITL approval events, and sandbox execution outputs.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial handshake / welcome state
        await websocket.send_text(json.dumps({
            "event_type": "CONNECTED",
            "message": "Connected to AgentShield Real-Time Security Feed",
            "active_policy": service.gateway.policy.__class__.__name__
        }))
        
        while True:
            # Keep-alive receive loop (handles client pings or control messages)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_text(json.dumps({"event_type": "PONG"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
