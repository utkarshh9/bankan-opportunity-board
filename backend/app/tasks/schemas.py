from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    estimated_hours: Optional[int] = Field(None, ge=1, le=100)
    deadline: Optional[date] = None
    labels: Optional[List[str]] = []
    required_skills: Optional[List[str]] = []
    is_specialized: bool = False

class TaskCreate(TaskBase):
    column_id: int
    board_id: int
    team_id: int
    assigned_to: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    estimated_hours: Optional[int] = Field(None, ge=1, le=100)
    deadline: Optional[date] = None
    labels: Optional[List[str]] = None
    required_skills: Optional[List[str]] = None
    is_specialized: Optional[bool] = None
    assigned_to: Optional[int] = None
    is_active: Optional[bool] = None

class TaskResponse(TaskBase):
    id: int
    column_id: int
    board_id: int
    team_id: int
    assigned_to: Optional[int] = None
    created_by: int
    claimed_by: Optional[int] = None
    is_claimed: bool
    is_completed: bool
    is_active: bool
    actual_hours: Optional[int] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TaskMove(BaseModel):
    column_id: int
    order: Optional[int] = None

class TaskClaim(BaseModel):
    task_id: int

class TaskAssign(BaseModel):
    user_id: int