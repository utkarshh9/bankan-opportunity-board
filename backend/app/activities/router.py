from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.users.models import User
from app.activities.service import ActivityService
from app.activities.schemas import ActivityResponse
from app.users.models import User as UserModel

router = APIRouter(prefix="/activities", tags=["Activities"])

@router.get("/", response_model=List[ActivityResponse])
async def get_activities(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    board_id: Optional[int] = Query(None, description="Filter by board ID"),
    task_id: Optional[int] = Query(None, description="Filter by task ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activities with filters."""
    try:
        activities = await ActivityService.get_activities(
            db=db,
            user_id=current_user.id,
            team_id=team_id,
            board_id=board_id,
            task_id=task_id,
            limit=limit,
            skip=skip
        )
        
        # ✅ Build response without lazy loading
        result = []
        for activity in activities:
            # ✅ Get user data separately (no lazy loading)
            user_data = None
            if activity.user_id:
                stmt = select(UserModel).where(UserModel.id == activity.user_id)
                user_result = await db.execute(stmt)
                user = user_result.scalar_one_or_none()
                if user:
                    user_data = {
                        "id": user.id,
                        "full_name": user.full_name,
                        "email": user.email
                    }
            
            activity_dict = {
                "id": activity.id,
                "user_id": activity.user_id,
                "team_id": activity.team_id,
                "board_id": activity.board_id,
                "task_id": activity.task_id,
                "comment_id": activity.comment_id,
                "activity_type": activity.activity_type.value if hasattr(activity.activity_type, 'value') else str(activity.activity_type),
                "description": activity.description,
                "changes": activity.changes,
                "extra_data": activity.extra_data,
                "created_at": activity.created_at,
                "user": user_data
            }
            result.append(activity_dict)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_activities endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching activities: {str(e)}"
        )

@router.get("/team/{team_id}", response_model=List[ActivityResponse])
async def get_team_activities(
    team_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all activities for a team."""
    try:
        activities = await ActivityService.get_team_activity(
            db=db,
            team_id=team_id,
            user_id=current_user.id,
            limit=limit,
            skip=skip
        )
        
        # ✅ Build response without lazy loading
        result = []
        for activity in activities:
            user_data = None
            if activity.user_id:
                stmt = select(UserModel).where(UserModel.id == activity.user_id)
                user_result = await db.execute(stmt)
                user = user_result.scalar_one_or_none()
                if user:
                    user_data = {
                        "id": user.id,
                        "full_name": user.full_name,
                        "email": user.email
                    }
            
            activity_dict = {
                "id": activity.id,
                "user_id": activity.user_id,
                "team_id": activity.team_id,
                "board_id": activity.board_id,
                "task_id": activity.task_id,
                "comment_id": activity.comment_id,
                "activity_type": activity.activity_type.value if hasattr(activity.activity_type, 'value') else str(activity.activity_type),
                "description": activity.description,
                "changes": activity.changes,
                "extra_data": activity.extra_data,
                "created_at": activity.created_at,
                "user": user_data
            }
            result.append(activity_dict)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_team_activities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching team activities: {str(e)}"
        )