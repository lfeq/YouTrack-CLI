import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""
    pass

def get_config_path(config_dir=None) -> Path:
    if config_dir is None:
        config_dir = os.environ.get("YOUTRACK_CONFIG_DIR")
    if config_dir is None:
        config_dir = Path.home() / ".config" / "youtrack-cli"
    else:
        config_dir = Path(config_dir)
    return config_dir / "config.toml"

def save_config(url: str, token: str, config_dir=None) -> None:
    config_file = get_config_path(config_dir)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # We write simple TOML manually to avoid relying on a third-party writer.
    # Escape quotes if necessary, though YouTrack URLs and tokens shouldn't have them normally.
    escaped_url = url.replace('"', '\\"')
    escaped_token = token.replace('"', '\\"')
    
    toml_content = f"""[default]
url = "{escaped_url}"
token = "{escaped_token}"
"""
    config_file.write_text(toml_content, encoding="utf-8")

def load_config(config_dir=None) -> dict:
    config_file = get_config_path(config_dir)
    if not config_file.exists():
        raise ConfigError(f"Config file not found at: {config_file}")
    
    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ConfigError(f"Failed to parse config file: {e}")
        
    if "default" not in data:
        raise ConfigError("Invalid config file structure: '[default]' section missing")
        
    default_section = data["default"]
    if "url" not in default_section or "token" not in default_section:
        raise ConfigError("Config file must contain both 'url' and 'token' in the '[default]' section")
        
    return {
        "url": default_section["url"],
        "token": default_section["token"],
    }

def resolve_token(config_dir=None) -> str:
    # 1. Check env var first
    env_token = os.environ.get("YOUTRACK_TOKEN")
    if env_token:
        return env_token
        
    # 2. Fallback to config file
    try:
        config = load_config(config_dir)
        return config["token"]
    except ConfigError as e:
        raise ConfigError("YouTrack token is not configured. Run 'youtrack login' or set YOUTRACK_TOKEN env var.") from e
