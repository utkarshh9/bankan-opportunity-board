from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, extract
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime, timedelta, date

from app.tasks.models import Task, TaskStatus, TaskPriority
from app.users.models import User
from app.teams.models import Team, team_members
from app.boards.models import Board
from app.analytics.models import Sprint
from app.analytics.schemas import (
    TaskCompletionMetric, TaskDistribution, PriorityDistribution,
    UserPerformance, TeamAnalytics, SprintVelocity, LeaderboardEntry,
    AnalyticsOverview
)

class AnalyticsService:
    
    # ============================================
    # SPRINT MANAGEMENT
    # ============================================
    
    @staticmethod
    async def create_sprint(
        db: AsyncSession,
        sprint_data: dict,
        user_id: int
    ) -> Sprint:
        """Create a new sprint."""
        # Check if user is team member
        stmt = select(team_members).where(
            team_members.c.team_id == sprint_data["team_id"],
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        sprint = Sprint(
            team_id=sprint_data["team_id"],
            name=sprint_data["name"],
            description=sprint_data.get("description"),
            start_date=sprint_data["start_date"],
            end_date=sprint_data["end_date"],
            goals=sprint_data.get("goals", []),
            story_points_total=sprint_data.get("story_points_total", 0)
        )
        
        db.add(sprint)
        await db.commit()
        await db.refresh(sprint)
        
        return sprint

    @staticmethod
    async def get_sprints(
        db: AsyncSession,
        team_id: int,
        user_id: int,
        is_active: Optional[bool] = None
    ) -> List[Sprint]:
        """Get sprints for a team."""
        # Check if user is team member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        stmt = select(Sprint).where(Sprint.team_id == team_id)
        if is_active is not None:
            stmt = stmt.where(Sprint.is_active == is_active)
        stmt = stmt.order_by(Sprint.start_date.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_sprint(
        db: AsyncSession,
        sprint_id: int,
        sprint_data: dict,
        user_id: int
    ) -> Sprint:
        """Update a sprint."""
        stmt = select(Sprint).where(Sprint.id == sprint_id)
        result = await db.execute(stmt)
        sprint = result.scalar_one_or_none()
        
        if not sprint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sprint not found"
            )
        
        # Check if user is team admin
        stmt = select(team_members).where(
            team_members.c.team_id == sprint.team_id,
            team_members.c.user_id == user_id,
            team_members.c.role.in_(['admin', 'manager'])
        )
        result = await db.execute(stmt)
        is_admin = result.first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this sprint"
            )
        
        # Update fields
        for key, value in sprint_data.items():
            if value is not None and hasattr(sprint, key):
                setattr(sprint, key, value)
        
        await db.commit()
        await db.refresh(sprint)
        
        return sprint

    # ============================================
    # ANALYTICS DASHBOARD
    # ============================================
    
    @staticmethod
    async def get_team_analytics(
        db: AsyncSession,
        team_id: int,
        user_id: int
    ) -> TeamAnalytics:
        """Get analytics for a specific team."""
        # Check if user is team member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Get team details
        stmt = select(Team).where(Team.id == team_id)
        result = await db.execute(stmt)
        team = result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        # Get task counts
        stmt = select(func.count(Task.id)).where(
            Task.team_id == team_id,
            Task.is_active == True
        )
        total_tasks = (await db.execute(stmt)).scalar() or 0
        
        stmt = select(func.count(Task.id)).where(
            Task.team_id == team_id,
            Task.is_completed == True,
            Task.is_active == True
        )
        completed_tasks = (await db.execute(stmt)).scalar() or 0
        
        stmt = select(func.count(Task.id)).where(
            Task.team_id == team_id,
            Task.status == TaskStatus.IN_PROGRESS,
            Task.is_active == True
        )
        in_progress_tasks = (await db.execute(stmt)).scalar() or 0
        
        # Get member count
        stmt = select(func.count()).select_from(team_members).where(
            team_members.c.team_id == team_id
        )
        member_count = (await db.execute(stmt)).scalar() or 0
        
        # Calculate average completion time
        stmt = select(
            func.avg(
                func.extract('epoch', Task.completed_at - Task.created_at) / 3600
            )
        ).where(
            Task.team_id == team_id,
            Task.is_completed == True,
            Task.is_active == True,
            Task.completed_at.isnot(None)
        )
        avg_time = (await db.execute(stmt)).scalar()
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return TeamAnalytics(
            team_id=team_id,
            team_name=team.name,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            completion_rate=round(completion_rate, 2),
            avg_completion_time_hours=round(avg_time, 2) if avg_time else None,
            member_count=member_count
        )

    @staticmethod
    async def get_task_distribution(
        db: AsyncSession,
        team_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Get task distribution by status and priority."""
        # Check if user is team member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Get tasks
        stmt = select(Task).where(
            Task.team_id == team_id,
            Task.is_active == True
        )
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        
        total = len(tasks) or 1  # Avoid division by zero
        
        # Status distribution
        status_counts = {}
        for task in tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        
        status_distribution = [
            TaskDistribution(
                status=status,
                count=count,
                percentage=round(count / total * 100, 2)
            )
            for status, count in status_counts.items()
        ]
        
        # Priority distribution
        priority_counts = {}
        for task in tasks:
            priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1
        
        priority_distribution = [
            PriorityDistribution(
                priority=priority,
                count=count,
                percentage=round(count / total * 100, 2)
            )
            for priority, count in priority_counts.items()
        ]
        
        return {
            "tasks_by_status": status_distribution,
            "tasks_by_priority": priority_distribution,
            "total_tasks": total - 1  # Adjust for division
        }

    # ============================================
    # LEADERBOARD
    # ============================================
    
    @staticmethod
    async def get_leaderboard(
        db: AsyncSession,
        team_id: int,
        user_id: int,
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """Get team leaderboard."""
        # Check if user is team member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Get all team members
        stmt = select(team_members.c.user_id).where(
            team_members.c.team_id == team_id
        )
        result = await db.execute(stmt)
        member_ids = [row[0] for row in result.fetchall()]
        
        entries = []
        
        for member_id in member_ids:
            # Get user details
            stmt = select(User).where(User.id == member_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                continue
            
            # Count tasks completed
            stmt = select(func.count(Task.id)).where(
                Task.team_id == team_id,
                Task.assigned_to == member_id,
                Task.is_completed == True,
                Task.is_active == True
            )
            tasks_completed = (await db.execute(stmt)).scalar() or 0
            
            # Count tasks claimed
            stmt = select(func.count(Task.id)).where(
                Task.team_id == team_id,
                Task.claimed_by == member_id,
                Task.is_active == True
            )
            tasks_claimed = (await db.execute(stmt)).scalar() or 0
            
            # Calculate average completion time
            stmt = select(
                func.avg(
                    func.extract('epoch', Task.completed_at - Task.created_at) / 3600
                )
            ).where(
                Task.team_id == team_id,
                Task.assigned_to == member_id,
                Task.is_completed == True,
                Task.is_active == True,
                Task.completed_at.isnot(None)
            )
            avg_time = (await db.execute(stmt)).scalar()
            
            # Calculate reliability score (percentage of claimed tasks completed)
            reliability_score = 0.0
            if tasks_claimed > 0:
                reliability_score = (tasks_completed / tasks_claimed) * 100
            
            # Calculate score (weighted combination)
            score = tasks_completed * 10 + int(reliability_score * 0.5)
            
            entries.append(LeaderboardEntry(
                user_id=member_id,
                full_name=user.full_name,
                email=user.email,
                score=score,
                tasks_completed=tasks_completed,
                tasks_claimed=tasks_claimed,
                avg_completion_time_hours=round(avg_time, 2) if avg_time else None,
                reliability_score=round(reliability_score, 2)
            ))
        
        # Sort by score descending
        entries.sort(key=lambda x: x.score, reverse=True)
        
        return entries[:limit]

    # ============================================
    # USER PERFORMANCE
    # ============================================
    
    @staticmethod
    async def get_user_performance(
        db: AsyncSession,
        team_id: int,
        user_id: int
    ) -> UserPerformance:
        """Get performance metrics for a specific user."""
        # Check if user is team member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Get user details
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Count tasks
        stmt = select(func.count(Task.id)).where(
            Task.team_id == team_id,
            Task.assigned_to == user_id,
            Task.is_active == True
        )
        tasks_assigned = (await db.execute(stmt)).scalar() or 0
        
        stmt = select(func.count(Task.id)).where(
            Task.team_id == team_id,
            Task.claimed_by == user_id,
            Task.is_active == True
        )
        tasks_claimed = (await db.execute(stmt)).scalar() or 0
        
        stmt = select(func.count(Task.id)).where(
            Task.team_id == team_id,
            Task.assigned_to == user_id,
            Task.is_completed == True,
            Task.is_active == True
        )
        tasks_completed = (await db.execute(stmt)).scalar() or 0
        
        # Calculate average completion time
        stmt = select(
            func.avg(
                func.extract('epoch', Task.completed_at - Task.created_at) / 3600
            )
        ).where(
            Task.team_id == team_id,
            Task.assigned_to == user_id,
            Task.is_completed == True,
            Task.is_active == True,
            Task.completed_at.isnot(None)
        )
        avg_time = (await db.execute(stmt)).scalar()
        
        completion_rate = (tasks_completed / tasks_assigned * 100) if tasks_assigned > 0 else 0
        
        return UserPerformance(
            user_id=user_id,
            full_name=user.full_name,
            email=user.email,
            tasks_completed=tasks_completed,
            tasks_claimed=tasks_claimed,
            tasks_assigned=tasks_assigned,
            completion_rate=round(completion_rate, 2),
            avg_completion_time_hours=round(avg_time, 2) if avg_time else None
        )

    # ============================================
    # SPRINT VELOCITY
    # ============================================
    
    @staticmethod
    async def get_sprint_velocity(
        db: AsyncSession,
        team_id: int,
        user_id: int,
        sprint_id: Optional[int] = None
    ) -> List[SprintVelocity]:
        """Get sprint velocity metrics."""
        # Check if user is team member
        stmt = select(team_members).where(
            team_members.c.team_id == team_id,
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        membership = result.first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this team"
            )
        
        # Get sprints
        stmt = select(Sprint).where(Sprint.team_id == team_id)
        if sprint_id:
            stmt = stmt.where(Sprint.id == sprint_id)
        stmt = stmt.order_by(Sprint.start_date.desc())
        
        result = await db.execute(stmt)
        sprints = result.scalars().all()
        
        velocities = []
        
        for sprint in sprints:
            # Count tasks completed during sprint
            stmt = select(func.count(Task.id)).where(
                Task.team_id == team_id,
                Task.is_completed == True,
                Task.is_active == True,
                Task.completed_at >= sprint.start_date,
                Task.completed_at <= sprint.end_date + timedelta(days=1)
            )
            completed_count = (await db.execute(stmt)).scalar() or 0
            
            # Calculate completion rate
            completion_rate = (sprint.story_points_completed / sprint.story_points_total * 100) if sprint.story_points_total > 0 else 0
            
            velocities.append(SprintVelocity(
                sprint_id=sprint.id,
                sprint_name=sprint.name,
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                total_points=sprint.story_points_total,
                completed_points=sprint.story_points_completed,
                completion_rate=round(completion_rate, 2)
            ))
        
        return velocities

    # ============================================
    # DASHBOARD OVERVIEW
    # ============================================
    
    @staticmethod
    async def get_dashboard_overview(
        db: AsyncSession,
        user_id: int
    ) -> AnalyticsOverview:
        """Get overall dashboard analytics for a user."""
        # Get all teams the user belongs to
        stmt = select(team_members.c.team_id).where(
            team_members.c.user_id == user_id
        )
        result = await db.execute(stmt)
        team_ids = [row[0] for row in result.fetchall()]
        
        if not team_ids:
            return AnalyticsOverview(
                total_tasks=0,
                completed_tasks=0,
                in_progress_tasks=0,
                todo_tasks=0,
                review_tasks=0,
                overall_completion_rate=0,
                active_teams=0,
                total_members=0,
                tasks_by_status=[],
                tasks_by_priority=[],
                recent_completions=[]
            )
        
        # Get all tasks across all teams
        stmt = select(Task).where(
            Task.team_id.in_(team_ids),
            Task.is_active == True
        )
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.is_completed)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        todo = sum(1 for t in tasks if t.status == TaskStatus.TODO)
        review = sum(1 for t in tasks if t.status == TaskStatus.REVIEW)
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        # Get active teams count
        stmt = select(func.count()).select_from(Team).where(
            Team.id.in_(team_ids),
            Team.is_active == True
        )
        active_teams = (await db.execute(stmt)).scalar() or 0
        
        # Get total members
        stmt = select(func.count()).select_from(team_members).where(
            team_members.c.team_id.in_(team_ids)
        )
        total_members = (await db.execute(stmt)).scalar() or 0
        
        # Task distribution by status
        status_counts = {}
        for task in tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        
        tasks_by_status = [
            TaskDistribution(
                status=status,
                count=count,
                percentage=round(count / total * 100, 2) if total > 0 else 0
            )
            for status, count in status_counts.items()
        ]
        
        # Task distribution by priority
        priority_counts = {}
        for task in tasks:
            priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1
        
        tasks_by_priority = [
            PriorityDistribution(
                priority=priority,
                count=count,
                percentage=round(count / total * 100, 2) if total > 0 else 0
            )
            for priority, count in priority_counts.items()
        ]
        
        # Recent completions (last 7 days)
        recent_completions = []
        for i in range(7):
            day = date.today() - timedelta(days=i)
            stmt = select(func.count(Task.id)).where(
                Task.team_id.in_(team_ids),
                Task.is_completed == True,
                Task.is_active == True,
                func.date(Task.completed_at) == day
            )
            count = (await db.execute(stmt)).scalar() or 0
            
            stmt = select(func.count(Task.id)).where(
                Task.team_id.in_(team_ids),
                Task.is_active == True,
                func.date(Task.created_at) == day
            )
            total_day = (await db.execute(stmt)).scalar() or 0
            
            recent_completions.append(TaskCompletionMetric(
                date=day,
                completed_count=count,
                total_count=total_day,
                completion_rate=round(count / total_day * 100, 2) if total_day > 0 else 0
            ))
        
        return AnalyticsOverview(
            total_tasks=total,
            completed_tasks=completed,
            in_progress_tasks=in_progress,
            todo_tasks=todo,
            review_tasks=review,
            overall_completion_rate=round(completion_rate, 2),
            active_teams=active_teams,
            total_members=total_members,
            tasks_by_status=tasks_by_status,
            tasks_by_priority=tasks_by_priority,
            recent_completions=recent_completions
        )