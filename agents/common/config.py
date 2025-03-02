from typing import Optional

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ['.env', '../.env', '../../.env', '../../../.env']
        env_file_encoding = 'utf-8'
        extra = 'ignore'

    APP_NAME: str = "deepcore"
    OTEL_ENABLED: bool = True
    OTEL_TRACE_UPLOAD_ENABLED: bool = False
    OTEL_TRACE_UPLOAD_URL: str = "http://127.0.0.1:4318/v1/traces"

    API_KEYS: Optional[list[str]] = []
    TWITTER_TOKEN: Optional[str] = ""

    HOST: str = "0.0.0.0"
    PORT: int = 8080
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    MODEL_NAME: str = "gpt-4o-2024-11-20"
    COIN_HOST: str = ""
    COIN_HOST_V2: str = ""
    COIN_API_KEY: str = ""
    COIN_API_KEY_V2: str = ""
    API_KEY: str = ""
    AI_SEARCH_HOST: str = ""
    AI_SEARCH_KEY: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = None
    REDIS_DB: int = 0
    REDIS_PREFIX: str = "default"
    LOG_LEVEL: str = "INFO"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "mydatabase"

    OPENAPI_FITTER_FIELDS: list[str] = []

    JWT_SECRET: str = ""
    JWT_EXPIRATION_TIME: int = 1  # default one day
    ENCRYPTION_KEY: str = ""

    API_BASE_URL: str = "" # base url
    TELEGRAM_REDIS_KEY: str = "deepcore_tg_bot_conf_all"



SETTINGS = Settings()
