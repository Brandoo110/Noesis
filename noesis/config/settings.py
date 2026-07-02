from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    deepseek_endpoint: str = Field(
        default="https://api.deepseek.com/chat/completions",
        validation_alias="DEEPSEEK_ENDPOINT",
    )
    deepseek_model: str = Field(
        default="deepseek-v4-pro",
        validation_alias="DEEPSEEK_MODEL",
    )
    deepseek_input_cost_per_million: float = Field(
        default=0.0,
        validation_alias="DEEPSEEK_INPUT_COST_PER_MILLION",
    )
    deepseek_output_cost_per_million: float = Field(
        default=0.0,
        validation_alias="DEEPSEEK_OUTPUT_COST_PER_MILLION",
    )
    light_llm_api_key: str = Field(default="", validation_alias="LIGHT_LLM_API_KEY")
    light_endpoint: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        validation_alias="LIGHT_ENDPOINT",
    )
    light_model: str = Field(
        default="glm-4.7-flash",
        validation_alias="LIGHT_MODEL",
    )
    light_input_cost_per_million: float = Field(
        default=0.0,
        validation_alias="LIGHT_INPUT_COST_PER_MILLION",
    )
    light_output_cost_per_million: float = Field(
        default=0.0,
        validation_alias="LIGHT_OUTPUT_COST_PER_MILLION",
    )
    risk_llm_api_key: str = Field(default="", validation_alias="RISK_LLM_API_KEY")
    risk_endpoint: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        validation_alias="RISK_ENDPOINT",
    )
    risk_model: str = Field(
        default="gemini-3.1-flash-lite",
        validation_alias="RISK_MODEL",
    )
    risk_input_cost_per_million: float = Field(
        default=0.0,
        validation_alias="RISK_INPUT_COST_PER_MILLION",
    )
    risk_output_cost_per_million: float = Field(
        default=0.0,
        validation_alias="RISK_OUTPUT_COST_PER_MILLION",
    )
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
