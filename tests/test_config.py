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
