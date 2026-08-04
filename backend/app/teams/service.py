from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from fastapi import HTTPException, status

from app.teams.models import Team, team_members
from app.boards.models import Board
from app.users.models import User
from app.teams.schemas import TeamCreate, TeamUpdate

class TeamService:
    @staticmethod
    async def create_team(
        db: AsyncSession, 
        team_data: TeamCreate, 
        user_id: int
    ) -> Team:
        """Create a new team."""
        # Check if team name already exists for this user
        stmt = select(Team).where(
            Team.name == team_data.name,
            Team.created_by == user_id,
            Team.is_active == True
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team with this name already exists"
            )
        
        # Create team
        team = Team(
            name=team_data.name,
            description=team_data.description,
            created_by=user_id
        )
        
        db.add(team)
        await db.flush()
        
        # Add creator as team member with admin role
        stmt = team_members.insert().values(
            team_id=team.id,
            user_id=user_id,
            role='admin'
        )
        await db.execute(stmt)
        
        await db.commit()
        await db.refresh(team)
        
        return team
    
    @staticmethod
    async def get_teams(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Team]:
        """Get all teams for a user."""
        # Get teams where user is a member
        stmt = (
            select(Team)
            .join(team_members, team_members.c.team_id == Team.id)
            .where(team_members.c.user_id == user_id)
            .where(Team.is_active == True)
            .offset(skip)
            .limit(limit)
            .order_by(Team.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_team(
        db: AsyncSession,
        team_id: int,
        user_id: int
    ) -> Optional[Team]:
        """Get a specific team by ID with member validation."""
        # Check if user is a member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Get team with members and boards
        stmt = (
            select(Team)
            .where(Team.id == team_id)
            .options(
                selectinload(Team.members),
                selectinload(Team.boards)
            )
        )
        result = await db.execute(stmt)
        team = result.scalar_one_or_none()
        
        if not team or not team.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        return team
    
    @staticmethod
    async def update_team(
        db: AsyncSession,
        team_id: int,
        team_data: TeamUpdate,
        user_id: int
    ) -> Team:
        """Update a team."""
        # Get team with permission check
        team = await TeamService.get_team(db, team_id, user_id)
        
        # Check if user is admin of the team
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id,
            team_members.c.role.in_(['admin', 'manager'])
        )
        result = await db.execute(stmt)
        is_admin = result.first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this team"
            )
        
        # Update fields
        if team_data.name is not None:
            team.name = team_data.name
        if team_data.description is not None:
            team.description = team_data.description
        if team_data.is_active is not None:
            team.is_active = team_data.is_active
        
        await db.commit()
        await db.refresh(team)
        
        return team
    
    @staticmethod
    async def delete_team(
        db: AsyncSession,
        team_id: int,
        user_id: int
    ) -> bool:
        """Soft delete a team."""
        # Get team with permission check
        team = await TeamService.get_team(db, team_id, user_id)
        
        # Check if user is creator or admin
        if team.created_by != user_id:
            stmt = select(team_members).where(
                team_members.c.team_id == team_id,
                team_members.c.user_id == user_id,
                team_members.c.role == 'admin'
            )
            result = await db.execute(stmt)
            is_admin = result.first()
            
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only team creator or admin can delete the team"
                )
        
        # Soft delete
        team.is_active = False
        await db.commit()
        
        return True
    
    @staticmethod
    async def add_member(
        db: AsyncSession,
        team_id: int,
        user_id: int,
        member_email: str,
        role: str = 'member'
    ) -> dict:
        """Add a member to a team."""
        # Check if current user is admin
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id,
            team_members.c.role.in_(['admin', 'manager'])
        )
        result = await db.execute(stmt)
        is_admin = result.first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to add members"
            )
        
        # Find user by email
        stmt = select(User).where(User.email == member_email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already a member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user.id
        )
        result = await db.execute(stmt)
        existing = result.first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this team"
            )
        
        # Add member
        stmt = team_members.insert().values(
            team_id=team_id,
            user_id=user.id,
            role=role
        )
        await db.execute(stmt)
        await db.commit()
        
        return {
            "message": f"User {user.email} added to team successfully",
            "user_id": user.id,
            "email": user.email,
            "role": role
        }
    
    @staticmethod
    async def remove_member(
        db: AsyncSession,
        team_id: int,
        user_id: int,
        member_id: int
    ) -> dict:
        """Remove a member from a team."""
        # Check if current user is admin
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id,
            team_members.c.role.in_(['admin', 'manager'])
        )
        result = await db.execute(stmt)
        is_admin = result.first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to remove members"
            )
        
        # Check if member exists
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == member_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this team"
            )
        
        # Can't remove the creator
        stmt = select(Team).where(Team.id == team_id)
        result = await db.execute(stmt)
        team = result.scalar_one_or_none()
        
        if team and team.created_by == member_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the team creator"
            )
        
        # Remove member
        stmt = team_members.delete().where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == member_id
        )
        await db.execute(stmt)
        await db.commit()
        
        return {"message": "Member removed successfully"}