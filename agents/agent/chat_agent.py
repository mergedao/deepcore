import json
from datetime import datetime, timezone
from typing import AsyncIterator

from agents.agent import AbstractAgent
from agents.agent.entity.inner.node_data import NodeMessage
from agents.agent.executor.agent_executor import DeepAgentExecutor
from agents.agent.llm.openai import openai
from agents.agent.memory.memory import MemoryObject
from agents.agent.memory.redis_memory import RedisMemoryStore
from agents.agent.prompts.tool_prompts import tool_prompt
from agents.models.models import App


class ChatAgent(AbstractAgent):
    """Chat Agent"""

    agent_executor: DeepAgentExecutor = None

    redis_memory: RedisMemoryStore = RedisMemoryStore()

    def __init__(self, app: App):
        """"
        Initialize the ChatAgent with the given app.
        Args:
            app (App): The application configuration object.
        """
        super().__init__()

        def stopping_condition(response: str):
            for stop_word in self.stop_condition:
                if stop_word in response:
                    return True
            return False

        self.agent_executor = DeepAgentExecutor(
            name=app.name,
            llm=openai.get_model(),
            tool_system_prompt=app.tool_prompt if app.tool_prompt else tool_prompt(),
            max_loops=app.max_loops if app.max_loops else 5,
            output_type="list",
            node_massage_enabled=True,
            stop_func=stopping_condition,
            system_prompt=app.description,
        )

    async def stream(self, query: str, conversation_id: str) -> AsyncIterator[str]:
        """
        Run the agent with the given query and conversation ID.
        Args:
            query (str): The user's query or question.
            conversation_id (str): The unique identifier of the conversation.
        Returns:
            AsyncIterator[str]: An iterator that yields responses to the user's query.
        """
        await self.add_memory(conversation_id)

        response_buffer = ""
        try:
            is_finalized = False
            final_response: list = []
            async for output in self.agent_executor.stream(query):
                if isinstance(output, NodeMessage):
                    yield self.send_message("status", output.to_dict())
                    continue
                elif isinstance(output, list):
                    final_response = output
                    continue
                elif not isinstance(output, str):
                    continue

                for stop_word in self.stop_condition:
                    if output and stop_word in output:
                        output = output.replace(stop_word, "")

                response_buffer += output
                is_finalized = True
                if output:
                    yield self.send_message("message", {"text": output})

            # Handle the case where no final response was generated
            if not is_finalized:
                if final_response:
                    yield self.send_message("message", {"text": final_response[-1]})
                else:
                    yield self.send_message("message", {"text": self.default_final_answer})
        except Exception as e:
            print("Error occurred:", e)
            raise e
        finally:
            memory_object = MemoryObject(input=query, output=response_buffer)
            self.redis_memory.save_memory(conversation_id, memory_object)

    async def add_memory(self, conversation_id: str):
        """
        Add memory to the agent based on the conversation ID.
        """
        memory_list = self.redis_memory.get_memory_by_conversation_id(conversation_id)

        # Add system time to short-term memory
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
        self.agent_executor.short_memory.add(role="System Time", content=f"UTC Now: {current_time}")

        # Load conversation-specific memory into the agent
        for memory in memory_list:
            self.agent_executor.add_memory_object(memory)

    def send_message(self, event: str, message: dict) -> str:
        """
        Send a message to the client.
        """
        return f'event: {event}\ndata: {json.dumps(message, ensure_ascii=False)}\n\n'
