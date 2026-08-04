from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.users.models import User
from app.boards.service import BoardService
from app.boards.schemas import BoardCreate, BoardUpdate, BoardResponse

router = APIRouter(prefix="/boards", tags=["Boards"])

@router.post("/", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(
    board_data: BoardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new board."""
    board = await BoardService.create_board(db, board_data, current_user.id)
    return board

@router.get("/team/{team_id}", response_model=List[BoardResponse])
async def get_boards(
    team_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all boards in a team."""
    boards = await BoardService.get_boards(db, team_id, current_user.id, skip, limit)
    return boards

@router.get("/{board_id}", response_model=BoardResponse)
async def get_board(
    board_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific board by ID."""
    board = await BoardService.get_board(db, board_id, current_user.id)
    return board

@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: int,
    board_data: BoardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a board."""
    board = await BoardService.update_board(db, board_id, board_data, current_user.id)
    return board

@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a board (soft delete)."""
    await BoardService.delete_board(db, board_id, current_user.id)
    return None