from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentCreate(CommentBase):
    task_id: int
    parent_id: Optional[int] = None
    mentions: Optional[List[int]] = [] 

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=2000)

class CommentResponse(CommentBase):
    id: int
    task_id: int
    user_id: int
    parent_id: Optional[int] = None
    mentions: Optional[List[int]] = [] 
    attachments: Optional[List[str]] = []
    is_active: bool
    is_edited: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CommentWithReplies(CommentResponse):
    replies: List['CommentWithReplies'] = []

CommentWithReplies.model_rebuild()