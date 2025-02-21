from typing import Optional, List, Tuple, Dict
from enum import Enum
from datetime import datetime

from pydantic import Field, BaseModel

from agents.protocol.schemas import AgentDTO


class AgentMode(str, Enum):
    REACT = "ReAct"
    CALL = "call"


class ToolInfo(BaseModel):
    id: str
    name: str
    type: str
    origin: str
    path: str
    method: str
    parameters: Dict
    is_stream: Optional[bool] = False
    output_format: Optional[Dict] = None
    description: Optional[str] = None
    auth_config: Optional[Dict] = None
    is_public: bool = False
    is_official: bool = False
    tenant_id: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information"""
    id: Optional[int] = Field(None, description="ID of the model")
    name: str = Field(..., description="Name of the model")
    endpoint: str = Field(..., description="API endpoint of the model")
    api_key: Optional[str] = Field(None, description="API key for the model")
    is_official: Optional[bool] = Field(False, description="Whether the model is official preset")
    is_public: Optional[bool] = Field(False, description="Whether the model is public")


class AgentInfo():
    name: Optional[str] = Field(None, description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    mode: Optional[AgentMode] = Field(None, description='Mode of the agent')
    tool_prompt: Optional[str] = Field(None, description="Optional tool prompt for the agent")
    max_loops: Optional[int] = Field(default=None, description="Maximum number of loops the agent can perform")
    tools: Optional[List[ToolInfo]] = Field(
        default=None,
        description="List of ToolInfo objects associated with the agent"
    )
    id: Optional[str] = Field(default=None, description="Optional ID of the tool, used for identifying existing tools")
    model: Optional[ModelInfo] = Field(None, description="Tuple of (model_info, api_key)")

    @staticmethod
    def from_dto(dto: AgentDTO) -> 'AgentInfo':
        """
        Convert AgentDTO to AgentInfo
        
        Args:
            dto: Instance of AgentDTO
            
        Returns:
            Instance of AgentInfo
        """
        info = AgentInfo()
        info.name = dto.name
        info.description = dto.description
        info.mode = AgentMode(dto.mode) if dto.mode else None
        info.tool_prompt = dto.tool_prompt
        info.max_loops = dto.max_loops
        info.tools = []
        if dto.tools:
            for tool in dto.tools:
                if not isinstance(tool, str):  # 如果不是字符串ID
                    info.tools.append(ToolInfo(**tool.model_dump()))
        info.id = dto.id
        return info

    def set_model(self, model_info: ModelInfo) -> None:
        """
        Set model information
        
        Args:
            model_info: Model information
            api_key: API key for the model
        """
        self.model = model_info
