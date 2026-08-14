from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum

class ActivityType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_MOVED = "task_moved"
    TASK_COMPLETED = "task_completed"
    TASK_CLAIMED = "task_claimed"
    TASK_UNCLAIMED = "task_unclaimed"
    TASK_ASSIGNED = "task_assigned"
    TASK_DELETED = "task_deleted"
    COMMENT_ADDED = "comment_added"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"
    TEAM_CREATED = "team_created"
    TEAM_UPDATED = "team_updated"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    BOARD_CREATED = "board_created"
    BOARD_UPDATED = "board_updated"

class UserBrief(BaseModel):
    id: int
    full_name: str
    email: str

class ActivityResponse(BaseModel):
    id: int
    user_id: int
    team_id: Optional[int] = None
    board_id: Optional[int] = None
    task_id: Optional[int] = None
    comment_id: Optional[int] = None
    activity_type: ActivityType
    description: str
    changes: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    user: Optional[UserBrief] = None
    
    class Config:
        from_attributes = True