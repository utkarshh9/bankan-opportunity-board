from typing import Dict, List, Set, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manage WebSocket connections and broadcasting."""
    
    def __init__(self):
        # Active connections: {user_id: {board_id: WebSocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        # Room memberships: {room_name: Set[user_id]}
        self.rooms: Dict[str, Set[int]] = {}
        # User connections: {user_id: WebSocket} for direct messages
        self.user_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int, board_id: int):
        """Connect a user to a board's WebSocket."""
        await websocket.accept()
        
        # Add to user connections
        self.user_connections[user_id] = websocket
        
        # Add to board connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][board_id] = websocket
        
        # Add to room
        room_name = f"board_{board_id}"
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(user_id)
        
        logger.info(f"User {user_id} connected to board {board_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "data": {
                "user_id": user_id,
                "board_id": board_id,
                "message": "Connected to board"
            }
        })

    def disconnect(self, user_id: int, board_id: int):
        """Disconnect a user from a board."""
        # Remove from board connections
        if user_id in self.active_connections:
            self.active_connections[user_id].pop(board_id, None)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from room
        room_name = f"board_{board_id}"
        if room_name in self.rooms:
            self.rooms[room_name].discard(user_id)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
        
        # Remove from user connections if no more boards
        if user_id in self.user_connections:
            # Check if user has any other connections
            if user_id not in self.active_connections:
                del self.user_connections[user_id]
        
        logger.info(f"User {user_id} disconnected from board {board_id}")

    async def send_to_user(self, user_id: int, data: dict):
        """Send a message to a specific user."""
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json(data)
                return True
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                return False
        return False

    async def broadcast_to_board(self, board_id: int, data: dict, exclude_user: Optional[int] = None):
        """Broadcast a message to all users in a board room."""
        room_name = f"board_{board_id}"
        if room_name not in self.rooms:
            return
        
        for user_id in list(self.rooms[room_name]):
            if user_id == exclude_user:
                continue
            await self.send_to_user(user_id, data)

    async def broadcast_to_team(self, team_id: int, data: dict, exclude_user: Optional[int] = None):
        """Broadcast a message to all users in a team."""
        # Get all board IDs in the team
        # This will be used to broadcast to all boards in a team
        room_prefix = f"team_{team_id}"
        for room_name in self.rooms:
            if room_name.startswith(room_prefix):
                for user_id in list(self.rooms[room_name]):
                    if user_id == exclude_user:
                        continue
                    await self.send_to_user(user_id, data)

    async def send_notification(self, user_id: int, notification_data: dict):
        """Send a real-time notification to a user."""
        await self.send_to_user(user_id, {
            "type": "notification",
            "data": notification_data
        })

    async def broadcast_task_update(self, board_id: int, task_data: dict, exclude_user: Optional[int] = None):
        """Broadcast a task update to all users in a board."""
        await self.broadcast_to_board(board_id, {
            "type": "task_update",
            "data": task_data
        }, exclude_user)

    async def broadcast_comment_update(self, board_id: int, comment_data: dict, exclude_user: Optional[int] = None):
        """Broadcast a comment update to all users in a board."""
        await self.broadcast_to_board(board_id, {
            "type": "comment_update",
            "data": comment_data
        }, exclude_user)

    async def broadcast_column_update(self, board_id: int, column_data: dict, exclude_user: Optional[int] = None):
        """Broadcast a column update to all users in a board."""
        await self.broadcast_to_board(board_id, {
            "type": "column_update",
            "data": column_data
        }, exclude_user)

# Global connection manager instance
manager = ConnectionManager()