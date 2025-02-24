from typing import Optional, AsyncIterator, Any

from langchain_core.messages import BaseMessageChunk

from agents.agent.executor.executor import AgentExecutor


class PromptAgentExecutor(AgentExecutor):

    def __init__(self,
                 name: str,
                 llm: Optional[Any] = None,
                 role_settings: str = "",
                 **kwargs) -> None:
        """
        Initialize a PromptAgentExecutor.
        
        Args:
            name: Name of the agent
            llm: Language model instance
            role_settings: Role configuration
            **kwargs: Additional arguments passed to parent class
        """
        kwargs['system_prompt'] = role_settings
        super().__init__(
            name=name,
            llm=llm,
            role_settings=role_settings,
            **kwargs
        )

    async def stream(
            self,
            task: Optional[str] = None,
            img: Optional[str] = None,
            *args,
            **kwargs,
    ) -> AsyncIterator[str]:
        input = self.short_memory.get_history_as_string()
        async for out in self.llm.astream(input, *args, **kwargs):
            if isinstance(out, str):
                yield out
            elif isinstance(out, BaseMessageChunk):
                yield out.content
