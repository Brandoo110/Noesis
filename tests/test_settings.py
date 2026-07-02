from noesis.config.settings import Settings, get_settings


LLM_ENV_KEYS = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_ENDPOINT",
    "DEEPSEEK_MODEL",
    "LIGHT_LLM_API_KEY",
    "LIGHT_ENDPOINT",
    "LIGHT_MODEL",
    "RISK_LLM_API_KEY",
    "RISK_ENDPOINT",
    "RISK_MODEL",
    "LIGHT_INPUT_COST_PER_MILLION",
    "LIGHT_OUTPUT_COST_PER_MILLION",
    "DEEPSEEK_INPUT_COST_PER_MILLION",
    "DEEPSEEK_OUTPUT_COST_PER_MILLION",
    "RISK_INPUT_COST_PER_MILLION",
    "RISK_OUTPUT_COST_PER_MILLION",
)


def test_settings_default_db_path_and_disabled_deepseek(monkeypatch) -> None:
    for key in LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("NOESIS_DB_PATH", raising=False)

    settings = Settings(_env_file=None)

    assert settings.db_path == "./noesis.db"
    assert settings.deepseek_enabled is False
    assert settings.deepseek_endpoint == "https://api.deepseek.com/chat/completions"
    assert settings.deepseek_model == "deepseek-v4-pro"
    assert settings.light_endpoint == "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    assert settings.light_model == "glm-4.7-flash"
    assert settings.risk_endpoint == (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )
    assert settings.risk_model == "gemini-3.1-flash-lite"


def test_settings_enable_deepseek_when_key_is_present(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    settings = Settings(_env_file=None)

    assert settings.deepseek_enabled is True


def test_settings_llm_endpoint_and_model_env_overrides(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_ENDPOINT", "https://deep.example/chat")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deep-test")
    monkeypatch.setenv("LIGHT_ENDPOINT", "https://light.example/chat")
    monkeypatch.setenv("LIGHT_MODEL", "glm-test")
    monkeypatch.setenv("RISK_ENDPOINT", "https://risk.example/chat")
    monkeypatch.setenv("RISK_MODEL", "gemini-test")

    settings = Settings(_env_file=None)

    assert settings.deepseek_endpoint == "https://deep.example/chat"
    assert settings.deepseek_model == "deep-test"
    assert settings.light_endpoint == "https://light.example/chat"
    assert settings.light_model == "glm-test"
    assert settings.risk_endpoint == "https://risk.example/chat"
    assert settings.risk_model == "gemini-test"


def test_settings_llm_cost_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("LIGHT_INPUT_COST_PER_MILLION", "0.1")
    monkeypatch.setenv("LIGHT_OUTPUT_COST_PER_MILLION", "0.2")
    monkeypatch.setenv("DEEPSEEK_INPUT_COST_PER_MILLION", "0.3")
    monkeypatch.setenv("DEEPSEEK_OUTPUT_COST_PER_MILLION", "0.4")
    monkeypatch.setenv("RISK_INPUT_COST_PER_MILLION", "0.5")
    monkeypatch.setenv("RISK_OUTPUT_COST_PER_MILLION", "0.6")

    settings = Settings(_env_file=None)

    assert settings.light_input_cost_per_million == 0.1
    assert settings.light_output_cost_per_million == 0.2
    assert settings.deepseek_input_cost_per_million == 0.3
    assert settings.deepseek_output_cost_per_million == 0.4
    assert settings.risk_input_cost_per_million == 0.5
    assert settings.risk_output_cost_per_million == 0.6


def test_get_settings_returns_cached_instance(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
