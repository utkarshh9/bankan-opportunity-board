from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.users.models import User
from app.tasks.service import TaskService
from app.tasks.schemas import (
    TaskCreate, 
    TaskUpdate, 
    TaskResponse, 
    TaskMove, 
    TaskClaim,
    TaskAssign
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task."""
    task = await TaskService.create_task(db, task_data, current_user.id)
    return task

@router.get("/board/{board_id}", response_model=List[TaskResponse])
async def get_tasks(
    board_id: int,
    column_id: Optional[int] = Query(None, description="Filter by column ID"),
    status: Optional[str] = Query(None, description="Filter by status (todo, in_progress, review, done)"),
    assigned_to: Optional[int] = Query(None, description="Filter by assignee ID"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, critical)"),  # ✅ NEW
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tasks for a board with filters."""
    tasks = await TaskService.get_tasks(
        db, 
        board_id, 
        current_user.id, 
        column_id, 
        status, 
        assigned_to,
        priority,  # ✅ NEW
        skip, 
        limit
    )
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific task by ID."""
    task = await TaskService.get_task(db, task_id, current_user.id)
    return task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a task."""
    task = await TaskService.update_task(db, task_id, task_data, current_user.id)
    return task

@router.post("/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: int,
    move_data: TaskMove,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Move a task to a different column."""
    task = await TaskService.move_task(db, task_id, move_data, current_user.id)
    return task

@router.post("/{task_id}/claim", response_model=TaskResponse)
async def claim_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Claim a task."""
    task = await TaskService.claim_task(db, task_id, current_user.id)
    return task

@router.post("/{task_id}/unclaim", response_model=TaskResponse)
async def unclaim_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unclaim a task."""
    task = await TaskService.unclaim_task(db, task_id, current_user.id)
    return task

@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: int,
    assign_data: TaskAssign,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign a task to a user."""
    task = await TaskService.assign_task(db, task_id, assign_data.user_id, current_user.id)
    return task

@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a task as completed and move to Done column."""
    task = await TaskService.complete_task(db, task_id, current_user.id)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task (soft delete)."""
    await TaskService.delete_task(db, task_id, current_user.id)
    return None