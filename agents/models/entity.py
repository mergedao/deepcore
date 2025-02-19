from typing import Optional, List

from pydantic import Field

from agents.protocol.schemas import AgentMode, AgentStatus, AgentDTO


class AgentInfo():
    name: Optional[str] = Field(None, description="Name of the agent")
    description: Optional[str] = Field(None, description="Description of the agent")
    mode: Optional[AgentMode] = Field(None, description='Mode of the agent')
    tool_prompt: Optional[str] = Field(None, description="Optional tool prompt for the agent")
    max_loops: Optional[int] = Field(default=None, description="Maximum number of loops the agent can perform")
    tools: Optional[List[str]] = Field(
        default=None,
        description="List of tool UUIDs to associate with the agent"
    )
    id: Optional[str] = Field(default=None, description="Optional ID of the tool, used for identifying existing tools")
    model_id: Optional[int] = Field(None, description="ID of the associated model")

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
        info.mode = dto.mode
        info.tool_prompt = dto.tool_prompt
        info.max_loops = dto.max_loops
        info.tools = [tool.id for tool in dto.tools] if dto.tools else None
        info.id = dto.id
        info.model_id = dto.model_id
        return info