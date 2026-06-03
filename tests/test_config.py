import os
import pytest
from youtrack_cli.config import load_config, save_config, resolve_token, ConfigError, get_config_path

def test_save_and_load_config(tmp_path):
    # tmp_path is a pathlib.Path representing a temp directory
    config_dir = tmp_path / "youtrack-cli"
    url = "https://example.youtrack.cloud"
    token = "perm:test-token"
    
    save_config(url, token, config_dir=config_dir)
    
    config_file = config_dir / "config.toml"
    assert config_file.exists()
    
    config = load_config(config_dir=config_dir)
    assert config["url"] == url
    assert config["token"] == token

def test_resolve_token_env_override(tmp_path, monkeypatch):
    config_dir = tmp_path / "youtrack-cli"
    url = "https://example.youtrack.cloud"
    token = "perm:stored-token"
    
    save_config(url, token, config_dir=config_dir)
    
    # 1. Without env var, uses stored token
    assert resolve_token(config_dir=config_dir) == "perm:stored-token"
    
    # 2. With env var, uses env var
    monkeypatch.setenv("YOUTRACK_TOKEN", "perm:env-token")
    assert resolve_token(config_dir=config_dir) == "perm:env-token"

def test_resolve_token_env_only_no_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "youtrack-cli"
    
    # No config file exists, but env var is set
    monkeypatch.setenv("YOUTRACK_TOKEN", "perm:env-token")
    assert resolve_token(config_dir=config_dir) == "perm:env-token"

def test_missing_config_raises_error(tmp_path):
    config_dir = tmp_path / "youtrack-cli"
    
    # No config, no env var
    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir=config_dir)
    assert "Config file not found" in str(exc_info.value)
    
    with pytest.raises(ConfigError) as exc_info:
        resolve_token(config_dir=config_dir)
    assert "YouTrack token is not configured" in str(exc_info.value)
