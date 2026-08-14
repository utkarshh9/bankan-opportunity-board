from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class ActivityType(str, enum.Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_MOVED = "task_moved"
    TASK_COMPLETED = "task_completed"
    TASK_CLAIMED = "task_claimed"
    TASK_UNCLAIMED = "task_unclaimed"
    TASK_ASSIGNED = "task_assigned"
    TASK_DELETED = "task_deleted"
    COMMENT_ADDED = "comment_added"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"
    TEAM_CREATED = "team_created"
    TEAM_UPDATED = "team_updated"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    BOARD_CREATED = "board_created"
    BOARD_UPDATED = "board_updated"

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True)
    board_id = Column(Integer, ForeignKey('boards.id'), nullable=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    comment_id = Column(Integer, ForeignKey('comments.id'), nullable=True)
    
    activity_type = Column(Enum(ActivityType), nullable=False)
    description = Column(Text, nullable=False)
    changes = Column(JSON, nullable=True)
    
    extra_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    team = relationship("Team", foreign_keys=[team_id])
    board = relationship("Board", foreign_keys=[board_id])
    task = relationship("Task", foreign_keys=[task_id])
    comment = relationship("Comment", foreign_keys=[comment_id])
    
    def __repr__(self):
        return f"<Activity {self.activity_type} by {self.user_id}>"