import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ToolType(str, Enum):
    OPENAPI = "openapi"
    FUNCTION = "function"


class AgentMode(str, Enum):
    REACT = "ReAct"
    CALL = "call"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"  # New draft status added


class ToolInfo(BaseModel):
    id: Optional[int] = Field(None, description="Optional ID of the tool, used for identifying existing tools")
    name: str = Field(..., description="Name of the tool")
    type: ToolType = Field(default=ToolType.OPENAPI, description='Type of the tool')
    content: str = Field(..., description="Content or configuration details of the tool")


class AgentCreate(BaseModel):
    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    mode: AgentMode = Field(default=AgentMode.REACT, description='Mode of the agent')
    icon: Optional[str] = Field(None, description="Optional icon for the agent")
    status: Optional[AgentStatus] = Field(default=AgentStatus.ACTIVE,
                                          description="Status of the agent, can be active, inactive, or draft")
    tool_prompt: Optional[str] = Field(None, description="Optional tool prompt for the agent")
    max_loops: int = Field(default=5, description="Maximum number of loops the agent can perform")
    tools: List[ToolInfo] = Field(default_factory=list, description="List of tools associated with the agent")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Optional new name for the agent")
    description: Optional[str] = Field(None, description="Optional new description for the agent")
    status: Optional[AgentStatus] = Field(None,
                                          description="New status for the agent, can be active, inactive, or draft")
    tool_prompt: Optional[str] = Field(None, description="Optional new tool prompt for the agent")
    max_loops: int = Field(default=5, description="Optional new maximum loops for the agent")
    tools: List[ToolInfo] = Field(default_factory=list, description="Optional new list of tools for the agent")


class ToolCreate(BaseModel):
    app_id: int = Field(..., description="ID of the application to which the tool belongs")
    name: str = Field(..., description="Name of the tool")
    type: ToolType = Field(default=ToolType.OPENAPI, description='Type of the tool')
    content: str = Field(..., description="Content or configuration details of the tool")


class ToolUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Optional new name for the tool")
    type: ToolType = Field(default=ToolType.OPENAPI, description='Type of the tool')
    content: Optional[str] = Field(None, description="Optional new content for the tool")


class DialogueRequest(BaseModel):
    query: Optional[str] = None
    conversation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), alias="conversationId")


class DialogueResponse(BaseModel):
    response: str = Field(..., description="Response message from the agent")


class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 10
