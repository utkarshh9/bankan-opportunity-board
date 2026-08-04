from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BoardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

class BoardCreate(BoardBase):
    team_id: int

class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class BoardResponse(BoardBase):
    id: int
    team_id: int
    created_by: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True