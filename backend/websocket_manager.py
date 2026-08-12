"""
WebSocket Server Component

Provides real-time updates to connected frontend clients.
"""

from fastapi import WebSocket
from typing import List
import logging
import asyncio
from models import WSMessage


logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts events to frontend clients.
    """
    
    def __init__(self):
        """Initialize WebSocket connection manager"""
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept and register new WebSocket connection.
        
        Args:
            websocket: WebSocket connection to register
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: WSMessage) -> None:
        """
        Send message to all connected clients.
        
        Args:
            message: WSMessage to broadcast
        """
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return
        
        message_json = message.to_json()
        
        # Broadcast to all connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)
        
        logger.debug(f"Broadcasted {message.event_type} to {len(self.active_connections)} clients")
    
    async def send_sample_recorded(self, sample_id: str, file_path: str) -> None:
        """Broadcast sample recorded event"""
        message = WSMessage(
            event_type="sample_recorded",
            payload={"sample_id": sample_id, "file_path": file_path}
        )
        await self.broadcast(message)
    
    async def send_transcription_complete(
        self,
        sample_id: str,
        transcript: str,
        confidence: float,
        is_unclear: bool
    ) -> None:
        """Broadcast transcription complete event"""
        message = WSMessage(
            event_type="transcription_complete",
            payload={
                "sample_id": sample_id,
                "transcript": transcript,
                "confidence": confidence,
                "is_unclear": is_unclear
            }
        )
        await self.broadcast(message)
    
    async def send_state_change(self, state: str, session_id: str) -> None:
        """Broadcast state change event"""
        message = WSMessage(
            event_type="state_change",
            payload={"state": state, "session_id": session_id}
        )
        await self.broadcast(message)
    
    async def send_stats_update(self, total_samples: int, session_samples: int) -> None:
        """Broadcast stats update event"""
        message = WSMessage(
            event_type="stats_update",
            payload={"total_samples": total_samples, "session_samples": session_samples}
        )
        await self.broadcast(message)
    
    async def send_quality_warning(self, warning_type: str, **kwargs) -> None:
        """Broadcast quality warning event"""
        payload = {"warning_type": warning_type}
        payload.update(kwargs)
        
        message = WSMessage(
            event_type="quality_warning",
            payload=payload
        )
        await self.broadcast(message)
    
    async def send_error(self, error_message: str, severity: str = "warning") -> None:
        """Broadcast error event"""
        message = WSMessage(
            event_type="error",
            payload={"error_message": error_message, "severity": severity}
        )
        await self.broadcast(message)
