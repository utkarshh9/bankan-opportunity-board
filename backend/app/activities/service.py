from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import List, Optional
from fastapi import HTTPException, status

from app.activities.models import Activity, ActivityType
from app.users.models import User
from app.teams.models import team_members

class ActivityService:
    @staticmethod
    async def create_activity(
        db: AsyncSession,
        user_id: int,
        activity_type: ActivityType,
        description: str,
        team_id: Optional[int] = None,
        board_id: Optional[int] = None,
        task_id: Optional[int] = None,
        comment_id: Optional[int] = None,
        changes: Optional[dict] = None,
        extra_data: Optional[dict] = None
    ) -> Activity:
        """Create a new activity log entry."""
        activity = Activity(
            user_id=user_id,
            team_id=team_id,
            board_id=board_id,
            task_id=task_id,
            comment_id=comment_id,
            activity_type=activity_type,
            description=description,
            changes=changes,
            extra_data=extra_data
        )
        
        db.add(activity)
        await db.commit()
        await db.refresh(activity)
        
        return activity

    @staticmethod
    async def get_activities(
        db: AsyncSession,
        user_id: int,
        team_id: Optional[int] = None,
        board_id: Optional[int] = None,
        task_id: Optional[int] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Activity]:
        """Get activities with filters."""
        try:
            # ✅ Build query conditions
            conditions = []
            
            # Get all teams the user is a member of
            stmt = select(team_members.c.team_id).where(
                team_members.c.user_id == user_id
            )
            result = await db.execute(stmt)
            team_ids = [row[0] for row in result.fetchall()]
            
            # If user is not in any team, return empty list
            if not team_ids:
                return []
            
            # If team_id is provided, check if user is a member
            if team_id:
                if team_id not in team_ids:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not a member of this team"
                    )
                conditions.append(Activity.team_id == team_id)
            else:
                conditions.append(Activity.team_id.in_(team_ids))
            
            # Add optional filters
            if board_id:
                conditions.append(Activity.board_id == board_id)
            if task_id:
                conditions.append(Activity.task_id == task_id)
            
            # ✅ Build and execute query
            stmt = select(Activity).where(and_(*conditions))
            stmt = stmt.order_by(desc(Activity.created_at))
            stmt = stmt.offset(skip).limit(limit)
            
            result = await db.execute(stmt)
            activities = result.scalars().all()
            
            return activities
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error in get_activities: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching activities: {str(e)}"
            )

    @staticmethod
    async def get_team_activity(
        db: AsyncSession,
        team_id: int,
        user_id: int,
        limit: int = 50,
        skip: int = 0
    ) -> List[Activity]:
        """Get all activities for a team."""
        return await ActivityService.get_activities(
            db, user_id, team_id=team_id, limit=limit, skip=skip
        )