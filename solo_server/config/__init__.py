import os
import yaml
from pathlib import Path
from solo_server.config.config_loader import load_config, get_path_config

# Load path configuration from YAML
path_config = get_path_config()

# Expand user directory in paths
CONFIG_DIR = os.path.expanduser(path_config.get('config_dir', '~/.solo_server'))
CONFIG_PATH = os.path.join(CONFIG_DIR, path_config.get('config_file', 'config.json'))

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)