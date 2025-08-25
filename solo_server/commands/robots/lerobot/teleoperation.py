"""
Teleoperation utilities for LeRobot
"""

import typer
from rich.prompt import Confirm
from typing import Dict, Optional

from solo_server.commands.robots.lerobot.config import get_robot_config_classes, create_follower_config
from solo_server.commands.robots.lerobot.mode_config import use_preconfigured_args


def teleoperation(leader_port: str, follower_port: str, robot_type: str = "so100", camera_config: Optional[Dict] = None, main_config: dict = None) -> bool:
    """
    Start teleoperation between leader and follower arms with optional camera support
    """
    # Check for preconfigured teleop settings
    if main_config:
        preconfigured = use_preconfigured_args(main_config, 'teleop', 'Teleoperation')
        if preconfigured:
            # Use preconfigured settings
            leader_port = preconfigured.get('leader_port', leader_port)
            follower_port = preconfigured.get('follower_port', follower_port)
            robot_type = preconfigured.get('robot_type', robot_type)
            camera_config = preconfigured.get('camera_config', camera_config)
            typer.echo("✅ Using preconfigured teleoperation settings")
    
    typer.echo(f"\n🎮 Starting teleoperation...")
    typer.echo(f"Leader arm port: {leader_port}")
    typer.echo(f"Follower arm port: {follower_port}")
    
    from lerobot.teleoperate import teleoperate, TeleoperateConfig
    
    # Setup cameras if not provided
    if camera_config is None:
        use_camera = Confirm.ask("Would you like to setup cameras?", default=True)
        if use_camera:
            from solo_server.commands.robots.lerobot.cameras import setup_cameras
            camera_config = setup_cameras()
        else:
            # Set empty camera config when user chooses not to use cameras
            camera_config = {'enabled': False, 'cameras': []}
    
    try:
        # Determine config classes based on robot type
        leader_config_class, follower_config_class = get_robot_config_classes(robot_type)
        
        if leader_config_class is None or follower_config_class is None:
            typer.echo(f"❌ Unsupported robot type for teleoperation: {robot_type}")
            return False
        
        # Create configurations
        leader_config = leader_config_class(port=leader_port, id=f"{robot_type}_leader")
        
        # Create robot config with cameras if enabled
        follower_config = create_follower_config(follower_config_class, follower_port, robot_type, camera_config)
        
        # Create teleoperation config
        teleop_config = TeleoperateConfig(
            teleop=leader_config,
            robot=follower_config,
            fps=60,
            display_data=True
        )
        
        typer.echo("🎮 Starting teleoperation... Press Ctrl+C to stop.")
        typer.echo("📋 Move the leader arm to control the follower arm.")
        
        # Start teleoperation
        teleoperate(teleop_config)
        
        # Save teleoperation configuration if not using preconfigured settings
        if main_config:
            from solo_server.commands.robots.lerobot.mode_config import save_teleop_config
            save_teleop_config(main_config, leader_port, follower_port, robot_type, camera_config)
        
        return True
        
    except KeyboardInterrupt:
        typer.echo("\n🛑 Teleoperation stopped by user.")
        return True
    except Exception as e:
        typer.echo(f"❌ Teleoperation failed: {e}")
        return False
