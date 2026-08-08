from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime

from app.tasks.models import Task, TaskStatus, TaskPriority
from app.columns.models import Column
from app.boards.models import Board
from app.teams.models import team_members
from app.users.models import User
from app.tasks.schemas import TaskCreate, TaskUpdate, TaskMove

class TaskService:
    @staticmethod
    async def create_task(
        db: AsyncSession,
        task_data: TaskCreate,
        user_id: int
    ) -> Task:
        """Create a new task."""
        # Check if column exists and user has access
        stmt = select(Column).where(Column.id == task_data.column_id)
        result = await db.execute(stmt)
        column = result.scalar_one_or_none()
        
        if not column:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Column not found"
            )
        
        # Check if user is a team member
        stmt = select(team_members).where(
            team_members.c.team_id == task_data.team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Verify board belongs to team
        stmt = select(Board).where(
            Board.id == task_data.board_id,
            Board.team_id == task_data.team_id
        )
        result = await db.execute(stmt)
        board = result.scalar_one_or_none()
        
        if not board:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Board does not belong to the specified team"
            )
        
        # Create task
        task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority,
            status=task_data.status,
            column_id=task_data.column_id,
            board_id=task_data.board_id,
            team_id=task_data.team_id,
            assigned_to=task_data.assigned_to,
            created_by=user_id,
            estimated_hours=task_data.estimated_hours,
            deadline=task_data.deadline,
            labels=task_data.labels or [],
            required_skills=task_data.required_skills or [],
            is_specialized=task_data.is_specialized
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        return task

    @staticmethod
    async def get_tasks(
        db: AsyncSession,
        board_id: int,
        user_id: int,
        column_id: Optional[int] = None,
        status: Optional[str] = None,
        assigned_to: Optional[int] = None,
        priority: Optional[str] = None,  # ✅ NEW: Add priority filter
        skip: int = 0,
        limit: int = 100
) ->     List[Task]:
        """Get tasks with filters."""
        # Check access to board
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

        # Build query with proper filtering
        conditions = [
            Task.board_id == board_id,
            Task.is_active == True
        ]

        # Apply filters
        if column_id is not None:
            conditions.append(Task.column_id == column_id)
        if status:
            conditions.append(Task.status == status)
        if assigned_to is not None:
            conditions.append(Task.assigned_to == assigned_to)
        if priority:  # ✅ NEW: Add priority filter
            conditions.append(Task.priority == priority)

        # Build the query
        stmt = select(Task).where(and_(*conditions))

        # Order by created_at (newest first for board view)
        stmt = stmt.order_by(Task.created_at.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_task(
        db: AsyncSession,
        task_id: int,
        user_id: int
    ) -> Task:
        """Get a specific task by ID."""
        stmt = select(Task).where(
            Task.id == task_id,
            Task.is_active == True
        )
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check if user is a team member
        stmt = select(team_members).where(
            team_members.c.team_id == task.team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        return task

    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: int,
        task_data: TaskUpdate,
        user_id: int
    ) -> Task:
        """Update a task."""
        task = await TaskService.get_task(db, task_id, user_id)
        
        # Update fields
        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.priority is not None:
            task.priority = task_data.priority
        if task_data.status is not None:
            task.status = task_data.status
            if task_data.status == TaskStatus.DONE:
                task.is_completed = True
                task.completed_at = datetime.utcnow()
        if task_data.estimated_hours is not None:
            task.estimated_hours = task_data.estimated_hours
        if task_data.deadline is not None:
            task.deadline = task_data.deadline
        if task_data.labels is not None:
            task.labels = task_data.labels
        if task_data.required_skills is not None:
            task.required_skills = task_data.required_skills
        if task_data.is_specialized is not None:
            task.is_specialized = task_data.is_specialized
        if task_data.assigned_to is not None:
            task.assigned_to = task_data.assigned_to
        if task_data.is_active is not None:
            task.is_active = task_data.is_active
        
        await db.commit()
        await db.refresh(task)
        
        return task

    @staticmethod
    async def move_task(
        db: AsyncSession,
        task_id: int,
        move_data: TaskMove,
        user_id: int
    ) -> Task:
        """Move a task to a different column."""
        task = await TaskService.get_task(db, task_id, user_id)

        # Check if target column exists
        stmt = select(Column).where(
            Column.id == move_data.column_id,
            Column.is_active == True
        )
        result = await db.execute(stmt)
        column = result.scalar_one_or_none()

        if not column:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target column not found"
            )

        # Update task
        task.column_id = move_data.column_id

        # ✅ FIX: Update status based on column name
        # Map column name to status
        column_name_lower = column.name.lower()
        if "todo" in column_name_lower or "to do" in column_name_lower:
            task.status = TaskStatus.TODO
        elif "progress" in column_name_lower or "in progress" in column_name_lower:
            task.status = TaskStatus.IN_PROGRESS
        elif "review" in column_name_lower:
            task.status = TaskStatus.REVIEW
        elif "done" in column_name_lower or "complete" in column_name_lower:
            task.status = TaskStatus.DONE
            task.is_completed = True
            task.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(task)

        return task

    @staticmethod
    async def claim_task(
        db: AsyncSession,
        task_id: int,
        user_id: int
    ) -> Task:
        """Claim a task."""
        task = await TaskService.get_task(db, task_id, user_id)
        
        if task.is_claimed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already claimed"
            )
        
        if task.is_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already completed"
            )
        
        task.is_claimed = True
        task.claimed_by = user_id
        
        await db.commit()
        await db.refresh(task)
        
        return task

    @staticmethod
    async def unclaim_task(
        db: AsyncSession,
        task_id: int,
        user_id: int
    ) -> Task:
        """Unclaim a task."""
        task = await TaskService.get_task(db, task_id, user_id)
        
        if not task.is_claimed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is not claimed"
            )
        
        if task.claimed_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the one who claimed this task"
            )
        
        task.is_claimed = False
        task.claimed_by = None
        
        await db.commit()
        await db.refresh(task)
        
        return task

    @staticmethod
    async def assign_task(
        db: AsyncSession,
        task_id: int,
        assignee_id: int,
        user_id: int
    ) -> Task:
        """Assign a task to a user."""
        task = await TaskService.get_task(db, task_id, user_id)
        
        # Check if assignee is a team member
        stmt = select(team_members).where(
            team_members.c.team_id == task.team_id,
            team_members.c.user_id == assignee_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this team"
            )
        
        task.assigned_to = assignee_id
        
        await db.commit()
        await db.refresh(task)
        
        return task

    @staticmethod
    async def complete_task(
        db: AsyncSession,
        task_id: int,
        user_id: int
    ) -> Task:
        """Mark a task as completed and move to Done column."""
        task = await TaskService.get_task(db, task_id, user_id)
        
        if task.is_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is already completed"
            )
        
        # ✅ FIX: Find the "Done" column for this board
        stmt = select(Column).where(
            Column.board_id == task.board_id,
            Column.name.ilike("%done%"),  # Find column with "done" in name
            Column.is_active == True
        ).order_by(Column.order)
        
        result = await db.execute(stmt)
        done_column = result.scalar_one_or_none()
        
        if done_column:
            # Move task to Done column
            task.column_id = done_column.id
            task.status = TaskStatus.DONE
        else:
            # If no Done column found, just update status
            task.status = TaskStatus.DONE
        
        task.is_completed = True
        task.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(task)
        
        return task

    @staticmethod
    async def delete_task(
        db: AsyncSession,
        task_id: int,
        user_id: int
    ) -> bool:
        """Soft delete a task."""
        task = await TaskService.get_task(db, task_id, user_id)
        
        # Only creator or team admin can delete
        # Check if user is team admin
        stmt = select(team_members).where(
            team_members.c.team_id == task.team_id,
            team_members.c.user_id == user_id,
            team_members.c.role.in_(['admin', 'manager'])
        )
        result = await db.execute(stmt)
        is_admin = result.first()
        
        if task.created_by != user_id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this task"
            )
        
        task.is_active = False
        await db.commit()
        
        return True