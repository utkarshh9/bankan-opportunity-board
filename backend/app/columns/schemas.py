from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ColumnBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    order: Optional[int] = 0

class ColumnCreate(ColumnBase):
    board_id: int

class ColumnUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    order: Optional[int] = None
    is_active: Optional[bool] = None

class ColumnResponse(ColumnBase):
    id: int
    board_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    task_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class ColumnReorder(BaseModel):
    column_ids: List[int]  # Ordered list of column IDs