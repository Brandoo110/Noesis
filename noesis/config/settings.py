from datetime import UTC, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEEPSEEK_V4_PRO_INPUT_CNY_PER_MILLION = 3.0
DEEPSEEK_V4_PRO_OUTPUT_CNY_PER_MILLION = 6.0
DEEPSEEK_PEAK_PRICE_MULTIPLIER = 2.0
GLM_47_FLASH_INPUT_CNY_PER_MILLION = 0.0
GLM_47_FLASH_OUTPUT_CNY_PER_MILLION = 0.0
USD_TO_CNY_REFERENCE_RATE = 6.78
GEMINI_31_FLASH_LITE_INPUT_USD_PER_MILLION = 0.25
GEMINI_31_FLASH_LITE_OUTPUT_USD_PER_MILLION = 1.50
GEMINI_31_FLASH_LITE_INPUT_CNY_PER_MILLION = round(
    GEMINI_31_FLASH_LITE_INPUT_USD_PER_MILLION * USD_TO_CNY_REFERENCE_RATE,
    3,
)
GEMINI_31_FLASH_LITE_OUTPUT_CNY_PER_MILLION = round(
    GEMINI_31_FLASH_LITE_OUTPUT_USD_PER_MILLION * USD_TO_CNY_REFERENCE_RATE,
    3,
)
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


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
        default=DEEPSEEK_V4_PRO_INPUT_CNY_PER_MILLION,
        validation_alias="DEEPSEEK_INPUT_COST_PER_MILLION",
    )
    deepseek_output_cost_per_million: float = Field(
        default=DEEPSEEK_V4_PRO_OUTPUT_CNY_PER_MILLION,
        validation_alias="DEEPSEEK_OUTPUT_COST_PER_MILLION",
    )
    deepseek_peak_pricing_enabled: bool = Field(
        default=True,
        validation_alias="DEEPSEEK_PEAK_PRICING_ENABLED",
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
        default=GLM_47_FLASH_INPUT_CNY_PER_MILLION,
        validation_alias="LIGHT_INPUT_COST_PER_MILLION",
    )
    light_output_cost_per_million: float = Field(
        default=GLM_47_FLASH_OUTPUT_CNY_PER_MILLION,
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
        default=GEMINI_31_FLASH_LITE_INPUT_CNY_PER_MILLION,
        validation_alias="RISK_INPUT_COST_PER_MILLION",
    )
    risk_output_cost_per_million: float = Field(
        default=GEMINI_31_FLASH_LITE_OUTPUT_CNY_PER_MILLION,
        validation_alias="RISK_OUTPUT_COST_PER_MILLION",
    )
    llm_cost_currency: str = Field(default="CNY", validation_alias="LLM_COST_CURRENCY")
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

    def deepseek_cost_multiplier_at(self, now: datetime | None = None) -> float:
        if not self.deepseek_peak_pricing_enabled:
            return 1.0
        timestamp = now or datetime.now(UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        beijing_now = timestamp.astimezone(BEIJING_TZ)
        is_peak = (9 <= beijing_now.hour < 12) or (14 <= beijing_now.hour < 18)
        return DEEPSEEK_PEAK_PRICE_MULTIPLIER if is_peak else 1.0

    def deepseek_input_cost_per_million_at(self, now: datetime | None = None) -> float:
        return self.deepseek_input_cost_per_million * self.deepseek_cost_multiplier_at(now)

    def deepseek_output_cost_per_million_at(self, now: datetime | None = None) -> float:
        return self.deepseek_output_cost_per_million * self.deepseek_cost_multiplier_at(now)

    @field_validator("llm_cost_currency")
    @classmethod
    def normalize_cost_currency(cls, value: str) -> str:
        return value.strip().upper() or "CNY"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
