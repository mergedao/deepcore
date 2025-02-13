from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=['.env', '../.env', '../../.env', '../../../.env'], extra='ignore',
                                      env_file_encoding="utf-8")
    OPENAI_API_KEY: str = Field(..., description="OpenAI's API key")
    OPENAI_MODEL_NAME: str = Field(..., description="OpenAI's model name")


SETTINGS = Settings()
