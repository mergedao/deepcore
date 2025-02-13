from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

class ToolModel(BaseModel):

    id: int
    app_id: int
    name: str
    type: str
    content: str
    update_time: Optional[datetime] = None
    create_time: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True

class AppModel(BaseModel):

    id: int
    name: str
    description: str
    mode: str
    icon: str
    status: str
    tool_prompt: str
    max_loops: int
    is_deleted: bool
    update_time: datetime
    create_time: datetime
    tools: Optional[List[ToolModel]] = None

    class Config:
        orm_mode = True
        from_attributes = True
