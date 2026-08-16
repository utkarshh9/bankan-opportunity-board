from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.database import get_db
from app.core.security import decode_token
from app.websocket.manager import manager
from app.users.models import User
from app.boards.models import Board
from app.teams.models import team_members

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/board/{board_id}")
async def websocket_board(
    websocket: WebSocket,
    board_id: int,
    token: str = None
):
    """WebSocket endpoint for real-time board updates."""
    user_id = None
    
    try:
        # ✅ Authenticate user via token query parameter
        # In production, you'd use a better method (cookies, headers)
        if token:
            payload = decode_token(token)
            if payload:
                user_id = int(payload.get("sub"))
        
        if not user_id:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        # ✅ Verify user has access to this board
        # This would use your existing permission logic
        # For now, we'll check if user is a team member
        # Get board's team_id
        async for db in get_db():
            from sqlalchemy import select
            stmt = select(Board).where(Board.id == board_id)
            result = await db.execute(stmt)
            board = result.scalar_one_or_none()
            
            if not board:
                await websocket.close(code=4002, reason="Board not found")
                return
            
            # Check if user is a team member
            stmt = select(team_members).where(
                team_members.c.team_id == board.team_id,
                team_members.c.user_id == user_id
            )
            result = await db.execute(stmt)
            membership = result.first()
            
            if not membership:
                await websocket.close(code=4003, reason="Access denied")
                return
            break
        
        # ✅ Connect to WebSocket
        await manager.connect(websocket, user_id, board_id)
        
        # ✅ Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # ✅ Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message.get("type") == "typing":
                    await manager.broadcast_to_board(
                        board_id,
                        {
                            "type": "typing",
                            "data": {
                                "user_id": user_id,
                                "is_typing": message.get("is_typing", False)
                            }
                        },
                        exclude_user=user_id
                    )
                
                # Add more message types as needed
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"}
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": str(e)}
                })
    
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id, board_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if user_id:
            manager.disconnect(user_id, board_id)

@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = None
):
    """WebSocket endpoint for real-time notifications."""
    user_id = None
    
    try:
        # Authenticate user
        if token:
            payload = decode_token(token)
            if payload:
                user_id = int(payload.get("sub"))
        
        if not user_id:
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        # Accept connection
        await websocket.accept()
        
        # Store connection for notifications
        manager.user_connections[user_id] = websocket
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "data": {
                "user_id": user_id,
                "message": "Connected to notifications"
            }
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message.get("type") == "mark_read":
                    # Handle mark as read via WebSocket
                    notification_id = message.get("notification_id")
                    if notification_id:
                        # Process mark as read
                        pass
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"}
                })
    
    except WebSocketDisconnect:
        if user_id and user_id in manager.user_connections:
            del manager.user_connections[user_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if user_id and user_id in manager.user_connections:
            del manager.user_connections[user_id]