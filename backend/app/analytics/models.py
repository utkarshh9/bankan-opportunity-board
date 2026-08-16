from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON, Enum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    
    goals = Column(JSON, nullable=True)  # List of sprint goals
    story_points_total = Column(Integer, default=0)
    story_points_completed = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    team = relationship("Team", foreign_keys=[team_id])
    
    def __repr__(self):
        return f"<Sprint {self.name}>"