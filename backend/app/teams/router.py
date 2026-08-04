from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_manager
from app.users.models import User
from app.teams.service import TeamService
from app.teams.schemas import (
    TeamCreate, 
    TeamUpdate, 
    TeamResponse, 
    TeamDetailResponse
)

router = APIRouter(prefix="/teams", tags=["Teams"])

@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new team."""
    team = await TeamService.create_team(db, team_data, current_user.id)
    return team

@router.get("/", response_model=List[TeamResponse])
async def get_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all teams for the current user."""
    teams = await TeamService.get_teams(db, current_user.id, skip, limit)
    return teams

@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific team by ID."""
    team = await TeamService.get_team(db, team_id, current_user.id)
    return team

@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a team."""
    team = await TeamService.update_team(db, team_id, team_data, current_user.id)
    return team

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a team (soft delete)."""
    await TeamService.delete_team(db, team_id, current_user.id)
    return None

@router.post("/{team_id}/members")
async def add_member(
    team_id: int,
    email: str,
    role: str = "member",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a member to a team."""
    return await TeamService.add_member(db, team_id, current_user.id, email, role)

@router.delete("/{team_id}/members/{member_id}")
async def remove_member(
    team_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a member from a team."""
    return await TeamService.remove_member(db, team_id, current_user.id, member_id)