import os
import yaml
from pathlib import Path

def get_config_path():
    """Get the path to the config.yaml file."""
    # Get the directory where this file is located
    current_dir = Path(__file__).parent
    return os.path.join(current_dir, "config.yaml")

def load_config():
    """Load configuration from YAML file."""
    config_path = get_config_path()
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def get_server_config(server_type):
    """Get configuration for a specific server type."""
    config = load_config()
    return config.get('servers', {}).get(server_type, {})

def get_path_config():
    """Get path configuration."""
    config = load_config()
    return config.get('paths', {})

def get_timeout_config():
    """Get timeout configuration."""
    config = load_config()
    return config.get('timeouts', {}) 