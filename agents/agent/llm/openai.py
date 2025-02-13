from langchain_community.chat_models.openai import ChatOpenAI

from agents.agent.llm.model import Model
from agents.common.config import SETTINGS


class ChatGPT(Model):
    """Chat GPT model"""
    use_model = ChatOpenAI(openai_api_key=SETTINGS.OPENAI_API_KEY, model_name=SETTINGS.MODEL_NAME,)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_model(self):
        return self.use_model



openai = ChatGPT()
