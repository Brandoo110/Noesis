from noesis.config.settings import Settings, get_settings


def test_settings_default_db_path_and_disabled_deepseek(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("NOESIS_DB_PATH", raising=False)

    settings = Settings()

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

    settings = Settings()

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

    settings = Settings()

    assert settings.deepseek_endpoint == "https://deep.example/chat"
    assert settings.deepseek_model == "deep-test"
    assert settings.light_endpoint == "https://light.example/chat"
    assert settings.light_model == "glm-test"
    assert settings.risk_endpoint == "https://risk.example/chat"
    assert settings.risk_model == "gemini-test"


def test_get_settings_returns_cached_instance(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
