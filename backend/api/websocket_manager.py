"""
Real-time WebSocket Connection Manager for AgentShield Dashboard
"""

import json
from typing import List, Dict, Any
from fastapi import WebSocket


class WebSocketManager:
    """Manages real-time WebSocket subscriber connections and event broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers a new WebSocket client connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event_data: Dict[str, Any]) -> None:
        """Broadcasts a JSON security event to all active clients."""
        if not self.active_connections:
            return

        payload = json.dumps(event_data)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


# Global singleton instance
ws_manager = WebSocketManager()
