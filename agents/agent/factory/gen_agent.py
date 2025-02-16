import json

from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate
from pydantic import BaseModel, Field

from agents.agent.llm.openai import openai

gen_aegnt_prompt = """\
You are an expert in generating agent configurations. Your task is to generate agent configuration based on user input according to the requirements.

Requirements
1. the content you generate should use the same language as the user input

User Input: {input}

Now, begin generate the agent:
"""


class AgentConfigurations(BaseModel):
    """Agent configurations"""
    name: str = Field(description="Name of the agent. 4 ~ 8 characters")
    description: str = Field(description="Description of the agent. within 200 characters")
    role_settings: str = Field(
        description="LLM role settings for the agent. 200 ~ 1000 characters, output with markdown format, contains ## Role ## Skills(3～5) ## Limit(3～5)")
    welcome_message: str = Field(description="welcome message for the agent. within 50 characters")


async def gen_agent(input: str):
    structured_model = openai.get_model().with_structured_output(AgentConfigurations)

    prompt = ChatPromptTemplate.from_messages([HumanMessagePromptTemplate.from_template(gen_aegnt_prompt)])

    chain = prompt | structured_model
    async for chunk in chain.astream({'input': input}):
        if isinstance(chunk, AgentConfigurations):
            yield f'event: message\ndata: {json.dumps(chunk.model_dump(), ensure_ascii=False)}\n\n'
        else:
            yield f'event: message\ndata: {str(chunk)}\n\n'
