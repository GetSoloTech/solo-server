"""
Teleoperation utilities for LeRobot
"""

import typer
from rich.prompt import Confirm, Prompt
from typing import Dict, Optional

from solo_server.commands.robots.lerobot.config import (
    get_robot_config_classes,
    create_follower_config,
    get_known_ids,
    save_lerobot_config,
)
from solo_server.commands.robots.lerobot.mode_config import use_preconfigured_args
from solo_server.commands.robots.lerobot.ports import detect_arm_port, detect_and_retry_ports


def teleoperation(leader_port: str, follower_port: str, robot_type: str = "so100", camera_config: Optional[Dict] = None, main_config: dict = None) -> bool:
    """
    Start teleoperation between leader and follower arms with optional camera support
    """
    # Initialize variables
    leader_id = None
    follower_id = None
    
    # Check for preconfigured teleop settings
    if main_config:
        preconfigured = use_preconfigured_args(main_config, 'teleop', 'Teleoperation')
        if preconfigured:
            # Use preconfigured settings
            leader_port = preconfigured.get('leader_port', leader_port)
            follower_port = preconfigured.get('follower_port', follower_port)
            robot_type = preconfigured.get('robot_type', robot_type)
            camera_config = preconfigured.get('camera_config', camera_config)
            # ids can be preconfigured too
            leader_id = preconfigured.get('leader_id')
            follower_id = preconfigured.get('follower_id')
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
        
        # Prompt/select ids if not provided
        known_leader_ids, known_follower_ids = get_known_ids(main_config or {})
        default_leader_id = (main_config or {}).get('lerobot', {}).get('leader_id') or f"{robot_type}_leader"
        default_follower_id = (main_config or {}).get('lerobot', {}).get('follower_id') or f"{robot_type}_follower"
        if not leader_id:
            if known_leader_ids:
                typer.echo("📇 Known leader ids:")
                for i, kid in enumerate(known_leader_ids, 1):
                    typer.echo(f"   {i}. {kid}")
                leader_id = Prompt.ask("Enter leader id", default=default_leader_id)
        if not follower_id:
            if known_follower_ids:
                typer.echo("📇 Known follower ids:")
                for i, kid in enumerate(known_follower_ids, 1):
                    typer.echo(f"   {i}. {kid}")
                follower_id = Prompt.ask("Enter follower id", default=default_follower_id)

        if not leader_id:
            leader_id = f"{robot_type}_leader"
        if not follower_id:
            follower_id = f"{robot_type}_follower"
        # Create configurations
        leader_config = leader_config_class(port=leader_port, id=leader_id)
        
        # Create robot config with cameras if enabled
        follower_config = create_follower_config(
            follower_config_class,
            follower_port,
            robot_type,
            camera_config,
            follower_id=follower_id,
        )
        
        # Create teleoperation config
        teleop_config = TeleoperateConfig(
            teleop=leader_config,
            robot=follower_config,
            fps=60,
            display_data=True
        )
        
        # Save configuration before execution (if not using preconfigured settings)
        if main_config and not preconfigured:
            from .mode_config import save_teleop_config
            save_teleop_config(
                main_config,
                leader_port,
                follower_port,
                robot_type,
                camera_config,
                leader_id,
                follower_id,
            )
        
        typer.echo("🎮 Starting teleoperation... Press Ctrl+C to stop.")
        typer.echo("📋 Move the leader arm to control the follower arm.")
        
        # Start teleoperation with retry logic
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                teleoperate(teleop_config)
                
                return True
                
            except Exception as e:
                error_msg = str(e)
                # Check if it's a port connection error
                if "Could not connect on port" in error_msg or "Make sure you are using the correct port" in error_msg:
                    if attempt < max_retries:
                        typer.echo(f"❌ Connection failed: {error_msg}")
                        typer.echo("🔄 Attempting to detect new ports...")
                        
                        # Detect new ports and retry
                        new_leader_port, new_follower_port = detect_and_retry_ports(leader_port, follower_port, main_config)
                        
                        if new_leader_port != leader_port or new_follower_port != follower_port:
                            # Update ports and recreate configs
                            leader_port, follower_port = new_leader_port, new_follower_port
                            leader_config = leader_config_class(port=leader_port, id=leader_id)
                            follower_config = create_follower_config(
                                follower_config_class,
                                follower_port,
                                robot_type,
                                camera_config,
                                follower_id=follower_id,
                            )
                            teleop_config = TeleoperateConfig(
                                teleop=leader_config,
                                robot=follower_config,
                                fps=60,
                                display_data=True
                            )
                            typer.echo("🔄 Retrying teleoperation with new ports...")
                            continue
                        else:
                            typer.echo("❌ Could not find new ports. Please check connections.")
                            return False
                    else:
                        typer.echo(f"❌ Teleoperation failed after retry: {error_msg}")
                        return False
                else:
                    # Non-port related error
                    typer.echo(f"❌ Teleoperation failed: {error_msg}")
                    return False
        
    except KeyboardInterrupt:
        typer.echo("\n🛑 Teleoperation stopped by user.")
        return True
