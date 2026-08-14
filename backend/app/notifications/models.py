from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class NotificationType(str, enum.Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_CLAIMED = "task_claimed"
    TASK_COMPLETED = "task_completed"
    TASK_MOVED = "task_moved"
    COMMENT_ADDED = "comment_added"
    MENTIONED = "mentioned"
    TEAM_INVITE = "team_invite"
    MEMBER_JOINED = "member_joined"
    TASK_OVERDUE = "task_overdue"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Links to related items
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True)
    board_id = Column(Integer, ForeignKey('boards.id'), nullable=True)
    comment_id = Column(Integer, ForeignKey('comments.id'), nullable=True)
    
    # Metadata
    data = Column(JSON, nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    sender = relationship("User", foreign_keys=[sender_id])
    task = relationship("Task", foreign_keys=[task_id])
    team = relationship("Team", foreign_keys=[team_id])
    board = relationship("Board", foreign_keys=[board_id])
    comment = relationship("Comment", foreign_keys=[comment_id])
    
    def __repr__(self):
        return f"<Notification {self.id} for User {self.user_id}>"