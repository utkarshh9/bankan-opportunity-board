from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from fastapi import HTTPException, status
from datetime import datetime

from app.notifications.models import Notification, NotificationType
from app.teams.models import team_members

class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: int,
        sender_id: Optional[int],
        notification_type: NotificationType,
        title: str,
        message: str,
        task_id: Optional[int] = None,
        team_id: Optional[int] = None,
        board_id: Optional[int] = None,
        comment_id: Optional[int] = None,
        data: Optional[dict] = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            sender_id=sender_id,
            notification_type=notification_type,
            title=title,
            message=message,
            task_id=task_id,
            team_id=team_id,
            board_id=board_id,
            comment_id=comment_id,
            data=data
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        return notification

    @staticmethod
    async def get_notifications(
        db: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        skip: int = 0
    ) -> List[Notification]:
        """Get user notifications."""
        stmt = select(Notification).where(
            Notification.user_id == user_id
        )
        
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        
        stmt = stmt.order_by(desc(Notification.created_at))
        stmt = stmt.offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_unread_count(
        db: AsyncSession,
        user_id: int
    ) -> int:
        """Get unread notification count."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> Notification:
        """Mark a notification as read."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
        result = await db.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(notification)
        
        return notification

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user_id: int
    ) -> int:
        """Mark all notifications as read."""
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        result = await db.execute(stmt)
        notifications = result.scalars().all()
        
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        await db.commit()
        
        return len(notifications)

    @staticmethod
    async def delete_notification(
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> bool:
        """Delete a notification."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
        result = await db.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        await db.delete(notification)
        await db.commit()
        
        return True