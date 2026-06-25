from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    light_llm_api_key: str = Field(default="", validation_alias="LIGHT_LLM_API_KEY")
    risk_llm_api_key: str = Field(default="", validation_alias="RISK_LLM_API_KEY")
    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")
    db_path: str = Field(default="./noesis.db", validation_alias="NOESIS_DB_PATH")
    chroma_dir: str = Field(default="./.chroma", validation_alias="CHROMA_DIR")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def deepseek_enabled(self) -> bool:
        return bool(self.deepseek_api_key.strip())

    @property
    def light_llm_enabled(self) -> bool:
        return bool(self.light_llm_api_key.strip())

    @property
    def risk_llm_enabled(self) -> bool:
        return bool(self.risk_llm_api_key.strip())

    @property
    def tavily_enabled(self) -> bool:
        return bool(self.tavily_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
