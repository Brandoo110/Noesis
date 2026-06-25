from noesis.config.settings import Settings, get_settings


def test_settings_default_db_path_and_disabled_deepseek(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("NOESIS_DB_PATH", raising=False)

    settings = Settings()

    assert settings.db_path == "./noesis.db"
    assert settings.deepseek_enabled is False


def test_settings_enable_deepseek_when_key_is_present(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    settings = Settings()

    assert settings.deepseek_enabled is True


def test_get_settings_returns_cached_instance(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
