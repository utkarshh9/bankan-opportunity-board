from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Set
from fastapi import HTTPException, status

from app.comments.models import Comment
from app.tasks.models import Task
from app.teams.models import team_members
from app.comments.schemas import CommentCreate, CommentUpdate
from app.activities.service import ActivityService
from app.activities.models import ActivityType
from app.notifications.service import NotificationService
from app.notifications.models import NotificationType

class CommentService:
    @staticmethod
    async def create_comment(
        db: AsyncSession,
        comment_data: CommentCreate,
        user_id: int
    ) -> Comment:
        """Create a new comment on a task."""
        
        # Check if task exists
        stmt = select(Task).where(Task.id == comment_data.task_id)
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
        
        # If parent_id is provided, check if parent comment exists
        if comment_data.parent_id:
            stmt = select(Comment).where(Comment.id == comment_data.parent_id)
            result = await db.execute(stmt)
            parent = result.scalar_one_or_none()
            
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found"
                )
        
        # ✅ Store mentions from the request - handle different formats
        mentions_list = []
        if comment_data.mentions:
            # If mentions is a list, use it directly
            if isinstance(comment_data.mentions, list):
                mentions_list = comment_data.mentions
            # If mentions is a string, try to parse it
            elif isinstance(comment_data.mentions, str):
                try:
                    import json
                    mentions_list = json.loads(comment_data.mentions)
                except:
                    mentions_list = []
        
        # Create comment
        comment = Comment(
            content=comment_data.content,
            task_id=comment_data.task_id,
            user_id=user_id,
            parent_id=comment_data.parent_id,
            mentions=mentions_list
        )
        
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        
        # Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.COMMENT_ADDED,
            description=f"User commented on task '{task.title}'",
            team_id=task.team_id,
            board_id=task.board_id,
            task_id=task.id,
            comment_id=comment.id,
            extra_data={
                "comment_content": comment.content[:100],
                "task_title": task.title
            }
        )
        
        # ✅ Create notifications for task assignee and mentioned users
        recipients: Set[int] = set()
        
        # Add task assignee if exists and not the comment author
        if task.assigned_to and task.assigned_to != user_id:
            recipients.add(task.assigned_to)
            print(f"🔔 Adding assignee {task.assigned_to} to recipients")
        
        # ✅ Add mentioned users from the stored mentions list
        if mentions_list:
            for mention_id in mentions_list:
                if mention_id != user_id:
                    recipients.add(mention_id)
                    print(f"🔔 Adding mention {mention_id} to recipients")
        
        print(f"📨 Total recipients: {recipients}")
        
        # Create notifications for each recipient
        for recipient_id in recipients:
            if recipient_id != user_id:
                print(f"📨 Creating notification for user {recipient_id}")
                try:
                    # Check if recipient is a team member
                    stmt = select(team_members).where(
                        team_members.c.team_id == task.team_id,
                        team_members.c.user_id == recipient_id
                    )
                    result = await db.execute(stmt)
                    is_member = result.first()
                    
                    if not is_member:
                        print(f"⚠️ User {recipient_id} is not a member of team {task.team_id}, skipping notification")
                        continue
                    
                    # Check if mentioned or assignee
                    is_mentioned = recipient_id in (mentions_list or [])
                    notification_type = NotificationType.MENTIONED if is_mentioned else NotificationType.COMMENT_ADDED
                    
                    # Create the notification
                    notification = await NotificationService.create_notification(
                        db=db,
                        user_id=recipient_id,
                        sender_id=user_id,
                        notification_type=notification_type,
                        title="You were mentioned in a comment" if is_mentioned else "New comment on your task",
                        message=f"{task.title}: {comment.content[:100]}...",
                        task_id=task.id,
                        team_id=task.team_id,
                        board_id=task.board_id,
                        comment_id=comment.id,
                        data={
                            "task_title": task.title,
                            "comment_content": comment.content,
                            "mentioned": is_mentioned,
                            "comment_id": comment.id
                        }
                    )
                    print(f"✅ Notification created with ID: {notification.id}")
                    
                except Exception as e:
                    print(f"❌ Error creating notification for user {recipient_id}: {e}")
        
        return comment

    @staticmethod
    async def get_comments(
        db: AsyncSession,
        task_id: int,
        user_id: int
    ) -> List[Comment]:
        """Get all comments for a task."""
        # Check if task exists and user has access
        stmt = select(Task).where(Task.id == task_id)
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
        
        # Get comments
        stmt = select(Comment).where(
            Comment.task_id == task_id,
            Comment.is_active == True
        ).order_by(Comment.created_at)
        
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_comment(
        db: AsyncSession,
        comment_id: int,
        user_id: int
    ) -> Comment:
        """Get a specific comment by ID."""
        stmt = select(Comment).where(
            Comment.id == comment_id,
            Comment.is_active == True
        )
        result = await db.execute(stmt)
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        # Check if user has access to the task
        stmt = select(Task).where(Task.id == comment.task_id)
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
        
        return comment

    @staticmethod
    async def update_comment(
        db: AsyncSession,
        comment_id: int,
        comment_data: CommentUpdate,
        user_id: int
    ) -> Comment:
        """Update a comment."""
        comment = await CommentService.get_comment(db, comment_id, user_id)
        
        # Only comment author can update
        if comment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this comment"
            )
        
        # Get the task first
        stmt = select(Task).where(Task.id == comment.task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if comment_data.content is not None:
            comment.content = comment_data.content
            comment.is_edited = True
        
        await db.commit()
        await db.refresh(comment)
        
        # Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.COMMENT_UPDATED,
            description=f"User updated comment on task '{task.title}'",
            task_id=comment.task_id,
            comment_id=comment.id,
            extra_data={
                "comment_content": comment.content[:100],
                "task_title": task.title
            }
        )
        
        return comment

    @staticmethod
    async def delete_comment(
        db: AsyncSession,
        comment_id: int,
        user_id: int
    ) -> bool:
        """Soft delete a comment."""
        comment = await CommentService.get_comment(db, comment_id, user_id)
        
        # Get the task first
        stmt = select(Task).where(Task.id == comment.task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        # Only comment author or team admin can delete
        is_admin = False
        if task:
            stmt = select(team_members).where(
                team_members.c.team_id == task.team_id,
                team_members.c.user_id == user_id,
                team_members.c.role.in_(['admin', 'manager'])
            )
            result = await db.execute(stmt)
            is_admin = result.first() is not None
        
        if comment.user_id != user_id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this comment"
            )
        
        comment.is_active = False
        await db.commit()
        
        # Create activity log
        await ActivityService.create_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.COMMENT_DELETED,
            description=f"User deleted comment on task '{task.title if task else 'unknown'}'",
            task_id=comment.task_id,
            comment_id=comment.id,
            extra_data={
                "comment_id": comment.id
            }
        )
        
        return True