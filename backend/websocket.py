import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json

class ConnectionManager:
    """
    The Nerve Center: Manages real-time WebSocket conduits.
    Now supports bidirectional frame streaming and telemetry.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        payload = json.dumps(message)
        await asyncio.gather(
            *[connection.send_text(payload) for connection in self.active_connections],
            return_exceptions=True
        )

    async def send_personal(self, websocket: WebSocket, message: dict):
        payload = json.dumps(message)
        await websocket.send_text(payload)

manager = ConnectionManager()
