from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate


async def get_chain_prompt(human_prompt,
                           system_prompt=None) -> ChatPromptTemplate:
    human_message = HumanMessagePromptTemplate.from_template(human_prompt)

    if system_prompt is None:
        return ChatPromptTemplate.from_messages([human_message])

    system_message = SystemMessage(content=system_prompt)

    return ChatPromptTemplate.from_messages([system_message, human_message])
