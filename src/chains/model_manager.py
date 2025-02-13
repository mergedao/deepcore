from functools import lru_cache

from langchain_openai import ChatOpenAI

from src.config import SETTINGS


@lru_cache(maxsize=1)
def get_chain_openai_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=SETTINGS.OPENAI_MODEL_NAME,
        api_key=SETTINGS.OPENAI_API_KEY
    )
