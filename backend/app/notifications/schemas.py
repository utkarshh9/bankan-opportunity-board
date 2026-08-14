from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_CLAIMED = "task_claimed"
    TASK_COMPLETED = "task_completed"
    TASK_MOVED = "task_moved"
    COMMENT_ADDED = "comment_added"
    MENTIONED = "mentioned"
    TEAM_INVITE = "team_invite"
    MEMBER_JOINED = "member_joined"
    TASK_OVERDUE = "task_overdue"

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    sender_id: Optional[int] = None
    notification_type: NotificationType
    title: str
    message: str
    task_id: Optional[int] = None
    team_id: Optional[int] = None
    board_id: Optional[int] = None
    comment_id: Optional[int] = None
    data: Optional[Any] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationUpdate(BaseModel):
    is_read: bool