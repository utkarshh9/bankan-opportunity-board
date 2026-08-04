from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

class TeamCreate(TeamBase):
    pass

class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class TeamMemberResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: str
    joined_at: datetime

class TeamResponse(TeamBase):
    id: int
    created_by: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    member_count: Optional[int] = 0
    board_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class TeamDetailResponse(TeamResponse):
    members: List[TeamMemberResponse] = []
    boards: List[dict] = []  # We'll populate this later