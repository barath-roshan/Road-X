"""Test suite verifying configuration, paths, and directory management."""

from pathlib import Path
from ml.common.config import Settings, settings


def test_settings_initialization():
    """Verify default Settings object initializes with valid paths."""
    assert settings.project_root.exists()
    assert (settings.project_root / "ml").exists()
    assert settings.data_dir.name == "data"
    assert settings.models_dir.name == "models"
    assert settings.raw_data_dir.name == "raw"
    assert settings.processed_data_dir.name == "processed"
    assert settings.external_data_dir.name == "external"


def test_ensure_directories(tmp_path: Path):
    """Verify ensure_directories creates required directories."""
    custom_settings = Settings(project_root=tmp_path)
    custom_settings.ensure_directories()

    assert custom_settings.data_dir.is_dir()
    assert custom_settings.raw_data_dir.is_dir()
    assert custom_settings.processed_data_dir.is_dir()
    assert custom_settings.external_data_dir.is_dir()
    assert custom_settings.models_dir.is_dir()
    assert custom_settings.logs_dir.is_dir()


def test_required_workspace_directories_exist():
    """Verify that expected repository directories exist in the workspace."""
    assert settings.data_dir.is_dir()
    assert settings.raw_data_dir.is_dir()
    assert settings.processed_data_dir.is_dir()
    assert settings.external_data_dir.is_dir()
    assert settings.models_dir.is_dir()


def test_validate_startup_configuration_clean_defaults():
    """Verify default development configuration emits no high-severity warnings."""
    from api.config import validate_startup_configuration
    warnings = validate_startup_configuration()
    # In clean default dev setup, there should be no CORS wildcard or invalid config warnings
    assert not any("wildcard" in w.lower() for w in warnings)


def test_validate_startup_configuration_cors_wildcard(monkeypatch):
    """Verify wildcard in CORS origins triggers advisory warning."""
    from api.config import api_settings, validate_startup_configuration
    monkeypatch.setattr(api_settings, "cors_allowed_origins", ["*"])
    warnings = validate_startup_configuration()
    assert any("contains wildcard" in w for w in warnings)


def test_validate_startup_configuration_production_sqlite(monkeypatch):
    """Verify production environment using SQLite triggers recommendation warning."""
    from api.config import api_settings, validate_startup_configuration
    from backend.config import db_settings
    monkeypatch.setattr(api_settings, "env", "production")
    monkeypatch.setattr(db_settings, "database_url", "sqlite:///data/roadx.db")
    warnings = validate_startup_configuration()
    assert any("PostgreSQL is strongly recommended" in w for w in warnings)


def test_validate_startup_configuration_twilio_placeholder(monkeypatch):
    """Verify enabled Twilio with placeholder credentials triggers warning."""
    from api.config import validate_startup_configuration
    from backend.config import notification_settings
    monkeypatch.setattr(notification_settings, "twilio_enabled", True)
    monkeypatch.setattr(notification_settings, "twilio_account_sid", "your_twilio_account_sid_placeholder")
    monkeypatch.setattr(notification_settings, "twilio_auth_token", "your_twilio_auth_token_placeholder")
    warnings = validate_startup_configuration()
    assert any("TWILIO_ENABLED is true but TWILIO_ACCOUNT_SID" in w for w in warnings)


def test_validate_startup_configuration_llm_placeholder(monkeypatch):
    """Verify non-mock LLM provider with placeholder API key triggers warning."""
    from api.config import validate_startup_configuration
    from backend.config import chatbot_settings
    monkeypatch.setattr(chatbot_settings, "llm_provider", "groq")
    monkeypatch.setattr(chatbot_settings, "llm_api_key", "your_llm_api_key_placeholder")
    warnings = validate_startup_configuration()
    assert any("ROADX_LLM_PROVIDER is set to 'groq'" in w for w in warnings)

