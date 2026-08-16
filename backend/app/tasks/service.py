from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime
from app.websocket.manager import manager
import json

from app.tasks.models import Task, TaskStatus, TaskPriority
from app.columns.models import Column
from app.boards.models import Board
from app.teams.models import team_members
from app.users.models import User
from app.tasks.schemas import TaskCreate, TaskUpdate, TaskMove
from app.notifications.service import NotificationService
from app.notifications.models import NotificationType
from app.activities.service import ActivityService
from app.activities.models import ActivityType

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
        
        # ✅ Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_CREATED,
            description=f"User created task '{task.title}'",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            extra_data={
                "task_title": task.title,
                "priority": task.priority,
                "status": task.status
            }
        )
        
        # ✅ Create notification for assignee if assigned
        if task_data.assigned_to and task_data.assigned_to != user_id:
            await NotificationService.create_notification(
                db=db,
                user_id=task_data.assigned_to,
                sender_id=user_id,
                notification_type=NotificationType.TASK_ASSIGNED,
                title="Task Assigned",
                message=f"You have been assigned to task '{task.title}'",
                task_id=task.id,
                team_id=task.team_id,
                board_id=task.board_id,
                data={
                    "task_title": task.title,
                    "priority": task.priority,
                    "task_id": task.id
                }
            )

        # Websocket: Broadcast task creation to board members
        try:
            await manager.broadcast_task_update(
                board_id=task.board_id,
                task_data={
                    "action": "created",
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "column_id": task.column_id,
                        "priority": task.priority,
                        "assigned_to": task.assigned_to,
                        "created_by": task.created_by
                    }
                },
                exclude_user=user_id
            )
        except Exception as e:
            print(f"⚠️ WebSocket broadcast error: {e}")
        
        return task

    @staticmethod
    async def get_tasks(
        db: AsyncSession,
        board_id: int,
        user_id: int,
        column_id: Optional[int] = None,
        status: Optional[str] = None,
        assigned_to: Optional[int] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
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
        if priority:
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
        
        # Track changes for activity log
        changes = {}
        if task_data.title is not None and task_data.title != task.title:
            changes["title"] = {"old": task.title, "new": task_data.title}
            task.title = task_data.title
        if task_data.description is not None and task_data.description != task.description:
            changes["description"] = {"old": task.description, "new": task_data.description}
            task.description = task_data.description
        if task_data.priority is not None and task_data.priority != task.priority:
            changes["priority"] = {"old": task.priority, "new": task_data.priority}
            task.priority = task_data.priority
        if task_data.status is not None and task_data.status != task.status:
            changes["status"] = {"old": task.status, "new": task_data.status}
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
        if task_data.assigned_to is not None and task_data.assigned_to != task.assigned_to:
            changes["assigned_to"] = {"old": task.assigned_to, "new": task_data.assigned_to}
            task.assigned_to = task_data.assigned_to
            
            # ✅ Send notification for new assignment
            if task_data.assigned_to and task_data.assigned_to != user_id:
                await NotificationService.create_notification(
                    db=db,
                    user_id=task_data.assigned_to,
                    sender_id=user_id,
                    notification_type=NotificationType.TASK_ASSIGNED,
                    title="Task Assigned",
                    message=f"You have been assigned to task '{task.title}'",
                    task_id=task.id,
                    team_id=task.team_id,
                    board_id=task.board_id,
                    data={
                        "task_title": task.title,
                        "priority": task.priority,
                        "task_id": task.id
                    }
                )
        if task_data.is_active is not None:
            task.is_active = task_data.is_active
        
        await db.commit()
        await db.refresh(task)
        
        # ✅ Create activity log if changes were made
        if changes:
            await ActivityService.create_activity(
                db=db,
                user_id=user_id,
                activity_type=ActivityType.TASK_UPDATED,
                description=f"User updated task '{task.title}'",
                team_id=task.team_id,
                board_id=task.board_id,
                task_id=task.id,
                changes=changes,
                extra_data={
                    "task_title": task.title
                }
            )
        
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

        # Track old column
        old_column_id = task.column_id
        old_status = task.status

        # Update task
        task.column_id = move_data.column_id

        # Update status based on column name
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

        # ✅ Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_MOVED,
            description=f"User moved task '{task.title}' to {column.name}",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            changes={
                "column": {"old": old_column_id, "new": task.column_id},
                "status": {"old": old_status, "new": task.status}
            },
            extra_data={
                "task_title": task.title,
                "column_name": column.name
            }
        )

        # ✅ Send notification to assignee if task was completed
        if task.status == TaskStatus.DONE and task.assigned_to and task.assigned_to != user_id:
            await NotificationService.create_notification(
                db=db,
                user_id=task.assigned_to,
                sender_id=user_id,
                notification_type=NotificationType.TASK_COMPLETED,
                title="Task Completed",
                message=f"Task '{task.title}' has been completed",
                task_id=task.id,
                team_id=task.team_id,
                board_id=task.board_id,
                data={
                    "task_title": task.title,
                    "task_id": task.id
                }
            )

        # Websocket: Broadcast task move to board members
        try:
            await manager.broadcast_task_update(
                board_id=task.board_id,
                task_data={
                    "action": "moved",
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "column_id": task.column_id
                    }
                },
                exclude_user=user_id
            )
        except Exception as e:
            print(f"⚠️ WebSocket broadcast error: {e}")

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
        
        # ✅ Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_CLAIMED,
            description=f"User claimed task '{task.title}'",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            extra_data={
                "task_title": task.title,
                "claimed_by": user_id
            }
        )
        
        # ✅ Send notification to task creator
        if task.created_by != user_id:
            await NotificationService.create_notification(
                db=db,
                user_id=task.created_by,
                sender_id=user_id,
                notification_type=NotificationType.TASK_CLAIMED,
                title="Task Claimed",
                message=f"Task '{task.title}' has been claimed",
                task_id=task.id,
                team_id=task.team_id,
                board_id=task.board_id,
                data={
                    "task_title": task.title,
                    "claimed_by": user_id,
                    "task_id": task.id
                }
            )
        
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
        
        # ✅ Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_UNCLAIMED,
            description=f"User unclaimed task '{task.title}'",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            extra_data={
                "task_title": task.title
            }
        )
        
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
        
        old_assignee = task.assigned_to
        task.assigned_to = assignee_id
        
        await db.commit()
        await db.refresh(task)
        
        # ✅ Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_ASSIGNED,
            description=f"User assigned task '{task.title}' to user {assignee_id}",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            changes={
                "assigned_to": {"old": old_assignee, "new": assignee_id}
            },
            extra_data={
                "task_title": task.title,
                "assignee_id": assignee_id
            }
        )
        
        # ✅ Send notification to new assignee
        if assignee_id != user_id:
            await NotificationService.create_notification(
                db=db,
                user_id=assignee_id,
                sender_id=user_id,
                notification_type=NotificationType.TASK_ASSIGNED,
                title="Task Assigned",
                message=f"You have been assigned to task '{task.title}'",
                task_id=task.id,
                team_id=task.team_id,
                board_id=task.board_id,
                data={
                    "task_title": task.title,
                    "priority": task.priority,
                    "task_id": task.id
                }
            )
        
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
        
        # Find the "Done" column for this board
        stmt = select(Column).where(
            Column.board_id == task.board_id,
            Column.name.ilike("%done%"),
            Column.is_active == True
        ).order_by(Column.order)
        
        result = await db.execute(stmt)
        done_column = result.scalar_one_or_none()
        
        if done_column:
            task.column_id = done_column.id
            task.status = TaskStatus.DONE
        else:
            task.status = TaskStatus.DONE
        
        task.is_completed = True
        task.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(task)
        
        # ✅ Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_COMPLETED,
            description=f"User completed task '{task.title}'",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            extra_data={
                "task_title": task.title,
                "completed_at": task.completed_at.isoformat()
            }
        )
        
        # ✅ Send notification to task creator and assignee
        recipients = set()
        if task.created_by and task.created_by != user_id:
            recipients.add(task.created_by)
        if task.assigned_to and task.assigned_to != user_id:
            recipients.add(task.assigned_to)

        for recipient_id in recipients:
            await NotificationService.create_notification(
                db=db,
                user_id=recipient_id,
                sender_id=user_id,
                notification_type=NotificationType.TASK_COMPLETED,
                title="Task Completed",
                message=f"Task '{task.title}' has been completed",
                task_id=task.id,
                team_id=task.team_id,
                board_id=task.board_id,
                data={
                    "task_title": task.title,
                    "completed_by": user_id,
                    "task_id": task.id
                }
            )

        # Websocket: Broadcast task completion to board members
        try:
            await manager.broadcast_task_update(
                board_id=task.board_id,
                task_data={
                    "action": "completed",
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "column_id": task.column_id,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None
                    }
                },
                exclude_user=user_id
            )
        except Exception as e:
            print(f"⚠️ WebSocket broadcast error: {e}")
        
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
        
        # ✅ Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_DELETED,
            description=f"User deleted task '{task.title}'",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            extra_data={
                "task_title": task.title,
                "task_id": task.id
            }
        )
        
        return True