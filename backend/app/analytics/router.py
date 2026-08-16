from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.users.models import User
from app.analytics.service import AnalyticsService
from app.analytics.schemas import (
    SprintCreate, SprintUpdate, SprintResponse,
    TeamAnalytics, LeaderboardEntry, UserPerformance,
    SprintVelocity, AnalyticsOverview
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# ============================================
# SPRINT ENDPOINTS
# ============================================

@router.post("/sprints", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
async def create_sprint(
    sprint_data: SprintCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new sprint."""
    sprint = await AnalyticsService.create_sprint(
        db, sprint_data.model_dump(), current_user.id
    )
    return sprint

@router.get("/sprints/team/{team_id}", response_model=List[SprintResponse])
async def get_sprints(
    team_id: int,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all sprints for a team."""
    sprints = await AnalyticsService.get_sprints(db, team_id, current_user.id, is_active)
    return sprints

@router.put("/sprints/{sprint_id}", response_model=SprintResponse)
async def update_sprint(
    sprint_id: int,
    sprint_data: SprintUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a sprint."""
    sprint = await AnalyticsService.update_sprint(
        db, sprint_id, sprint_data.model_dump(exclude_unset=True), current_user.id
    )
    return sprint

# ============================================
# ANALYTICS ENDPOINTS
# ============================================

@router.get("/team/{team_id}")
async def get_team_analytics(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get team analytics."""
    analytics = await AnalyticsService.get_team_analytics(db, team_id, current_user.id)
    return analytics

@router.get("/team/{team_id}/distribution")
async def get_task_distribution(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get task distribution by status and priority."""
    distribution = await AnalyticsService.get_task_distribution(db, team_id, current_user.id)
    return distribution

@router.get("/team/{team_id}/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    team_id: int,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get team leaderboard."""
    leaderboard = await AnalyticsService.get_leaderboard(db, team_id, current_user.id, limit)
    return leaderboard

@router.get("/team/{team_id}/user/{user_id}/performance", response_model=UserPerformance)
async def get_user_performance(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics for a specific user."""
    performance = await AnalyticsService.get_user_performance(db, team_id, user_id)
    return performance

@router.get("/team/{team_id}/velocity", response_model=List[SprintVelocity])
async def get_sprint_velocity(
    team_id: int,
    sprint_id: Optional[int] = Query(None, description="Filter by sprint ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sprint velocity metrics."""
    velocity = await AnalyticsService.get_sprint_velocity(db, team_id, current_user.id, sprint_id)
    return velocity

@router.get("/dashboard", response_model=AnalyticsOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get overall dashboard analytics."""
    overview = await AnalyticsService.get_dashboard_overview(db, current_user.id)
    return overview