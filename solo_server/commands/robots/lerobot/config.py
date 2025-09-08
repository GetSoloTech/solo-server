"""
Configuration utilities for LeRobot
"""

import json
import os
import typer
from typing import Optional, Tuple, TYPE_CHECKING, Dict, List
from solo_server.config import CONFIG_PATH

if TYPE_CHECKING:
    from lerobot.record import RecordConfig

# Import lerobot modules
from lerobot.teleoperators.so100_leader import SO100LeaderConfig
from lerobot.teleoperators.so101_leader import SO101LeaderConfig
from lerobot.robots.so100_follower import SO100FollowerConfig
from lerobot.robots.so101_follower import SO101FollowerConfig


def validate_lerobot_config(config: dict) -> tuple[Optional[str], Optional[str], bool, bool, str]:
    """
    Extract and validate lerobot configuration from main config.
    Returns: (leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type)
    """
    lerobot_config = config.get('lerobot', {})
    leader_port = lerobot_config.get('leader_port')
    follower_port = lerobot_config.get('follower_port')
    leader_calibrated = lerobot_config.get('leader_calibrated', False)
    follower_calibrated = lerobot_config.get('follower_calibrated', False)
    robot_type = lerobot_config.get('robot_type', 'so100')
    
    return leader_port, follower_port, leader_calibrated, follower_calibrated, robot_type


def save_lerobot_config(config: dict, arm_config: dict) -> None:
    """Save lerobot configuration to config file."""
    if 'lerobot' not in config:
        config['lerobot'] = {}
    config['lerobot'].update(arm_config)
    
    # Update server type
    if 'server' not in config:
        config['server'] = {}
    config['server']['type'] = 'lerobot'
    
    # Save to file
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    
    typer.echo(f"\n✅ Configuration saved to {CONFIG_PATH}")


def get_known_ids(config: dict) -> Tuple[List[str], List[str]]:
    """Return known leader and follower ids from config."""
    lerobot_config = config.get('lerobot', {})
    return lerobot_config.get('known_leader_ids', []), lerobot_config.get('known_follower_ids', [])


def add_known_id(config: dict, arm_type: str, arm_id: str) -> None:
    """Persist a discovered or chosen id for leader/follower in the config."""
    if 'lerobot' not in config:
        config['lerobot'] = {}
    key = 'known_leader_ids' if arm_type == 'leader' else 'known_follower_ids'
    existing: List[str] = config['lerobot'].get(key, [])
    if arm_id and arm_id not in existing:
        existing.append(arm_id)
        config['lerobot'][key] = existing
        # Save immediately to disk without changing other fields
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)


def get_robot_config_classes(robot_type: str) -> Tuple[Optional[type], Optional[type]]:
    """
    Get the appropriate config classes for leader and follower based on robot type
    Returns (leader_config_class, follower_config_class)
    """
    if robot_type == "so100":
        return SO100LeaderConfig, SO100FollowerConfig
    elif robot_type == "so101":
        return SO101LeaderConfig, SO101FollowerConfig
    else:
        return None, None


def build_camera_configuration(camera_config: Dict) -> Dict:
    """
    Build camera configuration dictionary from camera_config
    Returns cameras_dict for robot configuration
    """
    if not camera_config or not camera_config.get('enabled', False):
        return {}
    
    # Import camera configuration classes
    from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
    from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig
    
    cameras_dict = {}
    for cam in camera_config.get('cameras', []):
        camera_name = cam['angle']  # Use angle as camera name
        cam_info = cam['camera_info']
        
        # Create camera config based on type
        if cam['camera_type'] == 'OpenCV':
            stream_profile = cam_info.get('default_stream_profile') or {}
            cameras_dict[camera_name] = OpenCVCameraConfig(
                index_or_path=cam_info.get('id', 0),
                width=stream_profile.get('width', 640),
                height=stream_profile.get('height', 480),
                fps=stream_profile.get('fps', 30)
            )
        elif cam['camera_type'] == 'RealSense':
            stream_profile = cam_info.get('default_stream_profile') or {}
            cameras_dict[camera_name] = RealSenseCameraConfig(
                serial_number_or_name=str(cam_info.get('id', '')),
                width=stream_profile.get('width', 640),
                height=stream_profile.get('height', 480),
                fps=stream_profile.get('fps', 30)
            )
    
    return cameras_dict


def create_follower_config(
    follower_config_class,
    follower_port: str,
    robot_type: str,
    camera_config: Dict = None,
    follower_id: Optional[str] = None,
):
    """
    Create follower configuration with optional camera support
    """
    cameras_dict = build_camera_configuration(camera_config or {})
    
    if cameras_dict:
        return follower_config_class(
            port=follower_port,
            id=follower_id or f"{robot_type}_follower",
            cameras=cameras_dict
        )
    else:
        return follower_config_class(port=follower_port, id=follower_id or f"{robot_type}_follower")


def create_robot_configs(
    robot_type: str,
    leader_port: str,
    follower_port: str,
    camera_config: Dict = None,
    leader_id: Optional[str] = None,
    follower_id: Optional[str] = None,
) -> tuple[Optional[object], Optional[object]]:
    """
    Create leader and follower configurations for given robot type.
    Returns: (leader_config, follower_config)
    """
    leader_config_class, follower_config_class = get_robot_config_classes(robot_type)
    
    if leader_config_class is None or follower_config_class is None:
        typer.echo(f"❌ Unsupported robot type: {robot_type}")
        return None, None
    
    leader_config = leader_config_class(port=leader_port, id=leader_id or f"{robot_type}_leader")
    follower_config = create_follower_config(
        follower_config_class,
        follower_port,
        robot_type,
        camera_config,
        follower_id=follower_id,
    )
    
    return leader_config, follower_config
