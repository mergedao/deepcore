import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

from agents.agent import AbstractAgent
from agents.agent.entity.inner.node_data import NodeMessage
from agents.agent.entity.inner.tool_output import ToolOutput
from agents.agent.executor.agent_executor import DeepAgentExecutor
from agents.agent.llm.default_llm import openai
from agents.agent.memory.memory import MemoryObject
from agents.agent.memory.redis_memory import RedisMemoryStore
from agents.agent.prompts.tool_prompts import tool_prompt
from agents.agent.tools import coin_tools, ai_search_tool

logger = logging.getLogger(__name__)


class CoinAgent(AbstractAgent):
    redis_memory: RedisMemoryStore = RedisMemoryStore()
    need_now_time: bool = True

    def __init__(self):
        def stopping_condition(response: str):
            for stop_word in self.stop_condition:
                if stop_word in response:
                    return True
            return False

        self.agent_executor: DeepAgentExecutor = DeepAgentExecutor(
            name="Deepcore Agent",
            llm=openai.get_model(),
            tool_system_prompt=tool_prompt(),
            tools=[
                coin_tools.query_price_by_ids,
                coin_tools.query_historical_data_by_ids,
                coin_tools.query_markets_by_currency,
                coin_tools.query_top_gainers_losers,
                coin_tools.query_token_price_by_id,
            ],
            async_tools=[
                ai_search_tool.ai_search
            ],
            max_loops=6,
            output_type="list",
            node_massage_enabled=True,
            stop_func=stopping_condition,
            system_prompt="You are an Deepcore Agent.Your can provide you with cryptocurrency information and transaction data, as well as assist in generating professional research reports on the crypto market. You can solve problems directly or utilize specialized tools to perform detailed tasks and deliver precise solutions.",
        )

    async def stream(self, query: str, conversation_id: str) -> AsyncIterator[str]:
        """
        Executes a query using the agent and yields responses asynchronously.

        :param query: The input query string.
        :param conversation_id: The conversation ID used to fetch and save memory.
        :return: An asynchronous iterator of response strings.
        """
        memory_list = self.redis_memory.get_memory_by_conversation_id(conversation_id)
        response_buffer = ""
        try:
            # Add system time to short-term memory
            current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
            self.agent_executor.short_memory.add(role="System Time", content=f"UTC Now: {current_time}")

            # Load conversation-specific memory into the agent
            for memory in memory_list:
                self.agent_executor.add_memory_object(memory)

            # Process the query and yield responses
            is_finalized = False
            async for output in self.agent_executor.stream(query):
                if isinstance(output, NodeMessage):
                    yield self.seed_node_message(output)
                elif isinstance(output, ToolOutput):
                    yield output.get_output()
                    response_buffer = "..."
                    is_finalized = True
                    continue

                if not isinstance(output, str):
                    continue

                for stop_word in self.stop_condition:
                    if output and stop_word in output:
                        output = output.replace(stop_word, "")

                response_buffer += output
                is_finalized = True
                if output:
                    yield self.send_message(output)

            # Handle the case where no final response was generated
            if not is_finalized:
                yield self.send_message(self.default_final_answer)

        except Exception as error:
            logger.error("Error executing agent run: %s", error, exc_info=True)
        finally:
            # Save conversation memory
            memory_object = MemoryObject(input=query, output=response_buffer)
            self.redis_memory.save_memory(conversation_id, memory_object)

    def send_message(self, message: str) -> str:
        return f'event: message\ndata: {json.dumps({"text": message}, ensure_ascii=False)}\n\n'

    def seed_node_message(self, node_message: NodeMessage):
        return f'event: status\ndata: {json.dumps(node_message.to_dict(), ensure_ascii=False)}\n\n'
