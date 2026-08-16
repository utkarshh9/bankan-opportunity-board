from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# ============================================
# SPRINT SCHEMAS
# ============================================

class SprintBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: date
    end_date: date
    goals: Optional[List[str]] = []

class SprintCreate(SprintBase):
    team_id: int
    story_points_total: Optional[int] = 0

class SprintUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    goals: Optional[List[str]] = None
    story_points_total: Optional[int] = None
    story_points_completed: Optional[int] = None

class SprintResponse(SprintBase):
    id: int
    team_id: int
    is_active: bool
    story_points_total: int
    story_points_completed: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ============================================
# ANALYTICS SCHEMAS
# ============================================

class TaskCompletionMetric(BaseModel):
    date: date
    completed_count: int
    total_count: int
    completion_rate: float

class TaskDistribution(BaseModel):
    status: str
    count: int
    percentage: float

class PriorityDistribution(BaseModel):
    priority: str
    count: int
    percentage: float

class UserPerformance(BaseModel):
    user_id: int
    full_name: str
    email: str
    tasks_completed: int
    tasks_claimed: int
    tasks_assigned: int
    completion_rate: float
    avg_completion_time_hours: Optional[float] = None

class TeamAnalytics(BaseModel):
    team_id: int
    team_name: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    completion_rate: float
    avg_completion_time_hours: Optional[float] = None
    member_count: int

class SprintVelocity(BaseModel):
    sprint_id: int
    sprint_name: str
    start_date: date
    end_date: date
    total_points: int
    completed_points: int
    completion_rate: float

class LeaderboardEntry(BaseModel):
    user_id: int
    full_name: str
    email: str
    score: int
    tasks_completed: int
    tasks_claimed: int
    avg_completion_time_hours: Optional[float] = None
    reliability_score: float = 0.0  # Percentage of claimed tasks completed

class AnalyticsOverview(BaseModel):
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    review_tasks: int
    overall_completion_rate: float
    active_teams: int
    total_members: int
    tasks_by_status: List[TaskDistribution]
    tasks_by_priority: List[PriorityDistribution]
    recent_completions: List[TaskCompletionMetric]