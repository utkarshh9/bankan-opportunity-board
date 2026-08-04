from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from fastapi import HTTPException, status

from app.boards.models import Board
from app.teams.models import Team, team_members
from app.boards.schemas import BoardCreate, BoardUpdate

class BoardService:
    @staticmethod
    async def create_board(
        db: AsyncSession,
        board_data: BoardCreate,
        user_id: int
    ) -> Board:
        """Create a new board."""
        # Check if team exists and user is a member
        stmt = select(team_members).where(
            team_members.c.team_id == board_data.team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Check if board name already exists in team
        stmt = select(Board).where(
            Board.team_id == board_data.team_id,
            Board.name == board_data.name,
            Board.is_active == True
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Board with this name already exists in the team"
            )
        
        # Create board
        board = Board(
            name=board_data.name,
            description=board_data.description,
            team_id=board_data.team_id,
            created_by=user_id
        )
        
        db.add(board)
        await db.commit()
        await db.refresh(board)
        
        return board
    
    @staticmethod
    async def get_boards(
        db: AsyncSession,
        team_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Board]:
        """Get all boards in a team."""
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
        
        # Get boards
        stmt = (
            select(Board)
            .where(Board.team_id == team_id)
            .where(Board.is_active == True)
            .offset(skip)
            .limit(limit)
            .order_by(Board.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_board(
        db: AsyncSession,
        board_id: int,
        user_id: int
    ) -> Board:
        """Get a specific board by ID."""
        stmt = (
            select(Board)
            .where(Board.id == board_id)
            .where(Board.is_active == True)
        )
        result = await db.execute(stmt)
        board = result.scalar_one_or_none()
        
        if not board:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        # Check if user is a member of the team
        stmt = select(team_members).where(
            team_members.c.team_id == board.team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        return board
    
    @staticmethod
    async def update_board(
        db: AsyncSession,
        board_id: int,
        board_data: BoardUpdate,
        user_id: int
    ) -> Board:
        """Update a board."""
        board = await BoardService.get_board(db, board_id, user_id)
        
        # Update fields
        if board_data.name is not None:
            board.name = board_data.name
        if board_data.description is not None:
            board.description = board_data.description
        if board_data.is_active is not None:
            board.is_active = board_data.is_active
        
        await db.commit()
        await db.refresh(board)
        
        return board
    
    @staticmethod
    async def delete_board(
        db: AsyncSession,
        board_id: int,
        user_id: int
    ) -> bool:
        """Soft delete a board."""
        board = await BoardService.get_board(db, board_id, user_id)
        
        # Soft delete
        board.is_active = False
        await db.commit()
        
        return True