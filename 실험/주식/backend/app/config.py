from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "sqlite:///./stock_insight.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    openai_request_timeout_seconds: int = 45
    news_api_key: str = ""
    default_market: str = "ALL"
    enable_llm_analysis: bool = False
    enable_external_data: bool = True
    request_timeout_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
