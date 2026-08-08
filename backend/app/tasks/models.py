from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    
    # Foreign Keys
    column_id = Column(Integer, ForeignKey('columns.id'), nullable=False)
    board_id = Column(Integer, ForeignKey('boards.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    
    # Assignment
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    claimed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Task details
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)
    deadline = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Tracking
    is_claimed = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    labels = Column(JSON, nullable=True)  # Array of labels/tags
    required_skills = Column(JSON, nullable=True)  # Array of skills
    is_specialized = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    column = relationship("Column", back_populates="tasks")
    board = relationship("Board", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])
    creator = relationship("User", foreign_keys=[created_by])
    claimer = relationship("User", foreign_keys=[claimed_by])
    
    def __repr__(self):
        return f"<Task {self.title}>"