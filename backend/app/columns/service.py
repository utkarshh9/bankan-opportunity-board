from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from fastapi import HTTPException, status

from app.columns.models import Column
from app.boards.models import Board
from app.teams.models import team_members
from app.columns.schemas import ColumnCreate, ColumnUpdate, ColumnReorder

class ColumnService:
    # Default columns for a new board
    DEFAULT_COLUMNS = [
        {"name": "To Do", "description": "Tasks that need to be started", "order": 0},
        {"name": "In Progress", "description": "Tasks currently being worked on", "order": 1},
        {"name": "Review", "description": "Tasks awaiting review", "order": 2},
        {"name": "Done", "description": "Completed tasks", "order": 3},
    ]

    @staticmethod
    async def create_default_columns(db: AsyncSession, board_id: int, user_id: int) -> List[Column]:
        """Create default columns for a new board."""
        created_columns = []
        
        for col_data in ColumnService.DEFAULT_COLUMNS:
            column = Column(
                name=col_data["name"],
                description=col_data["description"],
                order=col_data["order"],
                board_id=board_id
            )
            db.add(column)
            created_columns.append(column)
        
        await db.commit()
        
        # Refresh all columns
        for column in created_columns:
            await db.refresh(column)
        
        return created_columns

    @staticmethod
    async def create_column(
        db: AsyncSession,
        column_data: ColumnCreate,
        user_id: int
    ) -> Column:
        """Create a new column."""
        # Check if board exists and user is a member
        stmt = select(Board).where(Board.id == column_data.board_id)
        result = await db.execute(stmt)
        board = result.scalar_one_or_none()
        
        if not board:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Board not found"
            )
        
        # Check if user is a team member
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
        
        # Check if column name already exists in board
        stmt = select(Column).where(
            Column.board_id == column_data.board_id,
            Column.name == column_data.name,
            Column.is_active == True
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Column with this name already exists in the board"
            )
        
        # Get max order for the board
        stmt = select(func.max(Column.order)).where(
            Column.board_id == column_data.board_id,
            Column.is_active == True
        )
        result = await db.execute(stmt)
        max_order = result.scalar() or -1
        
        # Create column
        column = Column(
            name=column_data.name,
            description=column_data.description,
            order=max_order + 1,
            board_id=column_data.board_id
        )
        
        db.add(column)
        await db.commit()
        await db.refresh(column)
        
        return column

    @staticmethod
    async def get_columns(
        db: AsyncSession,
        board_id: int,
        user_id: int
    ) -> List[Column]:
        """Get all columns for a board."""
        try:
            # Check if board exists and user is a member
            stmt = select(Board).where(Board.id == board_id)
            result = await db.execute(stmt)
            board = result.scalar_one_or_none()
            
            if not board:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Board not found"
                )
            
            # Check if user is a team member
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
            
            # ✅ Get columns with relationship loaded
            stmt = select(Column).where(
                Column.board_id == board_id,
                Column.is_active == True
            ).order_by(Column.order)
            
            result = await db.execute(stmt)
            columns = result.scalars().all()
            
            return columns
            
        except Exception as e:
            print(f"❌ Error in get_columns: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching columns: {str(e)}"
            )

    @staticmethod
    async def get_column(
        db: AsyncSession,
        column_id: int,
        user_id: int
    ) -> Column:
        """Get a specific column by ID."""
        # ✅ First get the column
        stmt = select(Column).where(
            Column.id == column_id,
            Column.is_active == True
        )
        result = await db.execute(stmt)
        column = result.scalar_one_or_none()
        
        if not column:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Column not found"
            )
        
        # ✅ Get the board separately to get team_id
        stmt = select(Board).where(Board.id == column.board_id)
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
        
        return column

    @staticmethod
    async def update_column(
        db: AsyncSession,
        column_id: int,
        column_data: ColumnUpdate,
        user_id: int
    ) -> Column:
        """Update a column."""
        column = await ColumnService.get_column(db, column_id, user_id)
        
        # Update fields
        if column_data.name is not None:
            column.name = column_data.name
        if column_data.description is not None:
            column.description = column_data.description
        if column_data.is_active is not None:
            column.is_active = column_data.is_active
        
        await db.commit()
        await db.refresh(column)
        
        return column

    @staticmethod
    async def reorder_columns(
        db: AsyncSession,
        reorder_data: ColumnReorder,
        user_id: int
    ) -> List[Column]:
        """Reorder columns."""
        # Get first column to validate
        if not reorder_data.column_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No columns to reorder"
            )
        
        # Get the first column
        stmt = select(Column).where(Column.id == reorder_data.column_ids[0])
        result = await db.execute(stmt)
        column = result.scalar_one_or_none()
        
        if not column:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Column not found"
            )
        
        # ✅ Get the board separately to check membership
        stmt = select(Board).where(Board.id == column.board_id)
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
        
        # Update order for each column
        for idx, column_id in enumerate(reorder_data.column_ids):
            stmt = select(Column).where(Column.id == column_id)
            result = await db.execute(stmt)
            col = result.scalar_one_or_none()
            
            if col:
                col.order = idx
        
        await db.commit()
        
        # Return updated columns
        stmt = select(Column).where(
            Column.board_id == column.board_id,
            Column.is_active == True
        ).order_by(Column.order)
        
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def delete_column(
        db: AsyncSession,
        column_id: int,
        user_id: int
    ) -> bool:
        """Soft delete a column."""
        column = await ColumnService.get_column(db, column_id, user_id)
        
        # Soft delete
        column.is_active = False
        await db.commit()
        
        return True