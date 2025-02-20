import os

CONFIG_DIR = os.path.expanduser('~/.solo_server')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)