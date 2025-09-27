"""
Mode-specific configuration utilities for LeRobot
Handles loading and saving of mode-specific configurations
"""

import json
import os
import typer
from rich.prompt import Confirm
from typing import Dict, Optional, Any
from solo_server.config import CONFIG_PATH


def load_mode_config(config: dict, mode: str) -> Optional[Dict]:
    """
    Load mode-specific configuration from the main config file.
    
    Args:
        config: Main configuration dictionary
        mode: Mode name (e.g., 'calibration', 'teleop', 'recording', 'training', 'inference')
    
    Returns:
        Mode-specific configuration dictionary or None if not found
    """
    lerobot_config = config.get('lerobot', {})
    mode_configs = lerobot_config.get('mode_configs', {})
    return mode_configs.get(mode)


def save_mode_config(config: dict, mode: str, mode_config: Dict) -> None:
    """
    Save mode-specific configuration to the main config file.
    
    Args:
        config: Main configuration dictionary
        mode: Mode name (e.g., 'calibration', 'teleop', 'recording', 'training', 'inference')
        mode_config: Mode-specific configuration to save
    """
    if 'lerobot' not in config:
        config['lerobot'] = {}
    
    if 'mode_configs' not in config['lerobot']:
        config['lerobot']['mode_configs'] = {}
    
    config['lerobot']['mode_configs'][mode] = mode_config
    
    # Save to file
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    


def use_preconfigured_args(config: dict, mode: str, mode_name: str) -> Optional[Dict]:
    """
    Check if preconfigured arguments exist for a mode and ask user if they want to use them.
    
    Args:
        config: Main configuration dictionary
        mode: Mode name (e.g., 'calibration', 'teleop', 'recording', 'training', 'inference')
        mode_name: Display name for the mode (e.g., 'Calibration', 'Teleoperation')
    
    Returns:
        Preconfigured arguments if user chooses to use them, None otherwise
    """
    mode_config = load_mode_config(config, mode)
    
    if mode_config:
        typer.echo(f"\n📋 Found preconfigured {mode_name} settings:")
        
        # Display the configuration in a user-friendly way
        for key, value in mode_config.items():
            if isinstance(value, dict):
                typer.echo(f"   • {key}: {len(value)} items")
            else:
                typer.echo(f"   • {key}: {value}")
        
        use_preconfigured = Confirm.ask(
            f"Would you like to use these preconfigured {mode_name} settings?",
            default=True
        )
        
        if use_preconfigured:
            return mode_config
        else:
            typer.echo(f"🔄 Running {mode_name} with new settings")
            return None
    
    return None


def save_teleop_config(config: dict, leader_port: str, follower_port: str, robot_type: str, camera_config: Dict, leader_id: str | None = None, follower_id: str | None = None) -> None:
    """Save teleoperation-specific configuration."""
    teleop_config = {
        'leader_port': leader_port,
        'follower_port': follower_port,
        'robot_type': robot_type,
        'camera_config': camera_config,
        'use_cameras': camera_config.get('enabled', False) if camera_config else False,
        'leader_id': leader_id,
        'follower_id': follower_id,
    }
    save_mode_config(config, 'teleop', teleop_config)


def save_recording_config(config: dict, recording_args: Dict) -> None:
    """Save recording-specific configuration."""
    recording_config = {
        'robot_type': recording_args.get('robot_type'),
        'leader_port': recording_args.get('leader_port'),
        'follower_port': recording_args.get('follower_port'),
        'camera_config': recording_args.get('camera_config'),
        'leader_id': recording_args.get('leader_id'),
        'follower_id': recording_args.get('follower_id'),
        'dataset_repo_id': recording_args.get('dataset_repo_id'),
        'task_description': recording_args.get('task_description'),
        'episode_time': recording_args.get('episode_time'),
        'num_episodes': recording_args.get('num_episodes'),
        'fps': recording_args.get('fps'),
        'push_to_hub': recording_args.get('push_to_hub'),
        'should_resume': recording_args.get('should_resume')
    }
    save_mode_config(config, 'recording', recording_config)


def save_training_config(config: dict, training_args: Dict) -> None:
    """Save training-specific configuration."""
    training_config = {
        'dataset_repo_id': training_args.get('dataset_repo_id'),
        'output_dir': training_args.get('output_dir'),
        'policy_type': training_args.get('policy_type'),
        'training_args': training_args.get('training_args', {})
    }
    save_mode_config(config, 'training', training_config)


def save_inference_config(config: dict, inference_args: Dict) -> None:
    """Save inference-specific configuration."""
    inference_config = {
        'robot_type': inference_args.get('robot_type'),
        'leader_port': inference_args.get('leader_port'),
        'follower_port': inference_args.get('follower_port'),
        'camera_config': inference_args.get('camera_config'),
        'policy_path': inference_args.get('policy_path'),
        'task_description': inference_args.get('task_description'),
        'inference_time': inference_args.get('inference_time'),
        'fps': inference_args.get('fps'),
        'use_teleoperation': inference_args.get('use_teleoperation')
    }
    save_mode_config(config, 'inference', inference_config)
