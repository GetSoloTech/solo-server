import os
import yaml
import configparser
from pathlib import Path

def get_config_path():
    """Get the path to the config directory"""
    return os.path.dirname(os.path.abspath(__file__))

def get_usecases_conf_path():
    """Get the path to the usecases.conf file"""
    return os.path.join(get_config_path(), 'usecases.conf')

def load_usecases_config():
    """Load the usecases configuration file"""
    config = configparser.ConfigParser()
    config.read(get_usecases_conf_path())
    return config

def get_shortname_transport_map():
    """Get mapping of shortnames to their transport URLs"""
    config = load_usecases_config()
    return dict(config['shortnames']) if 'shortnames' in config else {}

def get_usecase_model(usecase=None):
    """Get the default model for a specific usecase"""
    config = load_usecases_config()
    if not usecase or 'usecases' not in config:
        return None
    
    usecases = dict(config['usecases'])
    return usecases.get(usecase)

def get_model_metadata(shortname):
    """Get metadata for a specific model shortname"""
    config = load_usecases_config()
    if 'metadata' not in config:
        return {}
    
    metadata = {}
    prefix = f"{shortname}."
    for key, value in config['metadata'].items():
        if key.startswith(prefix):
            metadata[key[len(prefix):]] = value
    return metadata

def get_available_usecases():
    """Get list of all available usecases"""
    config = load_usecases_config()
    return list(dict(config['usecases']).keys()) if 'usecases' in config else []

def resolve_model_reference(model_ref):
    """
    Resolve a model reference to its transport URL
    Returns tuple of (transport_url, metadata)
    """
    shortnames = get_shortname_transport_map()
    
    # If it's a direct transport URL, return as is
    if '://' in model_ref:
        return model_ref, {}
    
    # Try to resolve shortname
    if model_ref in shortnames:
        return shortnames[model_ref], get_model_metadata(model_ref)
    
    # If not found, return original reference
    return model_ref, {} 