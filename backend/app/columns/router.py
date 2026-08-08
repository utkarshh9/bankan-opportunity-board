from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.users.models import User
from app.columns.service import ColumnService
from app.columns.schemas import ColumnCreate, ColumnUpdate, ColumnResponse, ColumnReorder
from app.tasks.models import Task

router = APIRouter(prefix="/columns", tags=["Columns"])

@router.post("/", response_model=ColumnResponse, status_code=status.HTTP_201_CREATED)
async def create_column(
    column_data: ColumnCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new column in a board."""
    column = await ColumnService.create_column(db, column_data, current_user.id)
    return column

@router.get("/board/{board_id}", response_model=List[ColumnResponse])
async def get_columns(
    board_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all columns for a board."""
    try:
        columns = await ColumnService.get_columns(db, board_id, current_user.id)
        
        # ✅ CORRECTED: Use a separate query for task counts
        result = []
        for column in columns:
            # Count tasks in this column using a proper async query
            stmt = select(func.count(Task.id)).where(
                Task.column_id == column.id,
                Task.is_active == True
            )
            task_count_result = await db.execute(stmt)
            task_count = task_count_result.scalar() or 0
            
            # Convert to dict and add task_count
            column_dict = {
                "id": column.id,
                "name": column.name,
                "description": column.description,
                "order": column.order,
                "board_id": column.board_id,
                "is_active": column.is_active,
                "created_at": column.created_at,
                "updated_at": column.updated_at,
                "task_count": task_count
            }
            result.append(column_dict)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_columns endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching columns: {str(e)}"
        )

@router.get("/{column_id}", response_model=ColumnResponse)
async def get_column(
    column_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific column by ID."""
    column = await ColumnService.get_column(db, column_id, current_user.id)
    
    # ✅ CORRECTED: Use a separate query for task count
    stmt = select(func.count(Task.id)).where(
        Task.column_id == column.id,
        Task.is_active == True
    )
    task_count_result = await db.execute(stmt)
    task_count = task_count_result.scalar() or 0
    
    # Convert to dict and add task_count
    column_dict = {
        "id": column.id,
        "name": column.name,
        "description": column.description,
        "order": column.order,
        "board_id": column.board_id,
        "is_active": column.is_active,
        "created_at": column.created_at,
        "updated_at": column.updated_at,
        "task_count": task_count
    }
    
    return column_dict

@router.put("/{column_id}", response_model=ColumnResponse)
async def update_column(
    column_id: int,
    column_data: ColumnUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a column."""
    column = await ColumnService.update_column(db, column_id, column_data, current_user.id)
    return column

@router.post("/reorder", response_model=List[ColumnResponse])
async def reorder_columns(
    reorder_data: ColumnReorder,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reorder columns."""
    columns = await ColumnService.reorder_columns(db, reorder_data, current_user.id)
    return columns

@router.delete("/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(
    column_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a column (soft delete)."""
    await ColumnService.delete_column(db, column_id, current_user.id)
    return None