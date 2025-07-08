"""
LeRobot command for Solo Server
Handles motor setup, calibration, and teleoperation for robotic arms
"""

import json
import os
import typer
from typing import Optional
from rich.console import Console
from rich.prompt import Confirm
from solo_server.config import CONFIG_PATH
from solo_server.utils.lerobot_utils import setup_calibration, start_teleoperation, setup_motors_for_arm, setup_motors_and_calibration

console = Console()

def lerobot(
    calibrate: bool = typer.Option(False, "--calibrate", help="Setup motors and calibrate arms only"),
    teleop: bool = typer.Option(False, "--teleop", help="Start teleoperation (requires calibrated arms)"),
):
    """
    LeRobot operations: motor setup, calibration, and teleoperation
    """
    
    # Check if lerobot is installed
    try:
        import lerobot
    except ImportError:
        typer.echo("❌ LeRobot package not found.")
        typer.echo("Please run 'solo setup' and select LeRobot as your server type first.")
        return
    
    # Load existing config
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            config = {}
    
    if teleop:
        # Teleoperation mode - check for existing calibration
        _handle_teleoperation_mode(config)
    elif calibrate:
        # Calibration mode - setup motors (optional) + calibrate
        _handle_calibration_mode(config)
    else:
        # Full mode - setup motors + calibrate + teleoperate
        _handle_full_mode(config)

def _handle_teleoperation_mode(config: dict):
    """Handle solo lerobot --teleop"""
    typer.echo("🎮 Starting teleoperation mode...")
    
    # Check if arms are already calibrated
    lerobot_config = config.get('lerobot', {})
    leader_port = lerobot_config.get('leader_port')
    follower_port = lerobot_config.get('follower_port')
    leader_calibrated = lerobot_config.get('leader_calibrated', False)
    follower_calibrated = lerobot_config.get('follower_calibrated', False)
    robot_type = lerobot_config.get('robot_type', 'so100')
    
    if leader_port and follower_port and leader_calibrated and follower_calibrated:
        typer.echo("✅ Found calibrated arms:")
        typer.echo(f"   • Robot type: {robot_type.upper()}")
        typer.echo(f"   • Leader arm: {leader_port}")
        typer.echo(f"   • Follower arm: {follower_port}")
        
        # Start teleoperation
        success = start_teleoperation(leader_port, follower_port, robot_type)
        if success:
            typer.echo("✅ Teleoperation completed.")
        else:
            typer.echo("❌ Teleoperation failed.")
    else:
        typer.echo("❌ Arms are not properly calibrated.")
        typer.echo("Please run one of the following first:")
        typer.echo("   • 'solo lerobot --calibrate' - Configure arms only")
        typer.echo("   • 'solo lerobot' - Full setup (motors + calibration + teleoperation)")

def _handle_calibration_mode(config: dict):
    """Handle solo lerobot --calibrate"""
    typer.echo("🔧 Starting calibration mode...")
    
    # Ask if user wants to setup motor IDs first
    setup_motors = Confirm.ask("Would you like to setup motor IDs first?", default=True)
    
    if setup_motors:
        # Use the complete motor setup and calibration function
        arm_config = setup_motors_and_calibration()
    else:
        # Run calibration only
        typer.echo("\n🔧 Starting arm calibration...")
        arm_config = setup_calibration()
    
    # Save configuration
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
    
    # Check if calibration was successful
    leader_configured = arm_config.get('leader_port') and arm_config.get('leader_calibrated')
    follower_configured = arm_config.get('follower_port') and arm_config.get('follower_calibrated')
    
    if leader_configured and follower_configured:
        typer.echo("🎉 Arms calibrated successfully!")
        if setup_motors:
            leader_motors = arm_config.get('leader_motors_setup', False)
            follower_motors = arm_config.get('follower_motors_setup', False)
            if leader_motors and follower_motors:
                typer.echo("✅ Motor IDs have been set up for both arms.")
            else:
                typer.echo("⚠️  Some motor setups may have failed, but calibration completed.")
        typer.echo("🎮 You can now run 'solo lerobot --teleop' to start teleoperation.")
    else:
        typer.echo("⚠️  Calibration partially completed.")
        typer.echo("You can run 'solo lerobot --calibrate' again to retry.")

def _handle_full_mode(config: dict):
    """Handle solo lerobot (full setup)"""
    typer.echo("🤖 Starting full LeRobot setup...")
    typer.echo("This will run: motor setup → calibration → teleoperation\n")
    
    # Step 1 & 2: Setup motors and calibration
    typer.echo("Step 1/3: Setting up motor IDs and calibration...")
    arm_config = setup_motors_and_calibration()
    
    # Save configuration
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
    
    # Step 3: Teleoperation (if calibration successful)
    leader_configured = arm_config.get('leader_port') and arm_config.get('leader_calibrated')
    follower_configured = arm_config.get('follower_port') and arm_config.get('follower_calibrated')
    
    if leader_configured and follower_configured:
        # Report motor setup status
        leader_motors = arm_config.get('leader_motors_setup', False)
        follower_motors = arm_config.get('follower_motors_setup', False)
        if leader_motors and follower_motors:
            typer.echo("✅ Motor IDs set up successfully for both arms.")
        else:
            typer.echo("⚠️  Some motor setups may have failed, but calibration completed.")
        
        typer.echo("\nStep 3/3: Starting teleoperation...")
        robot_type = arm_config.get('robot_type', 'so100')
        leader_port = arm_config.get('leader_port')
        follower_port = arm_config.get('follower_port')
        
        success = start_teleoperation(leader_port, follower_port, robot_type)
        if success:
            typer.echo("🎉 Full LeRobot setup completed successfully!")
        else:
            typer.echo("⚠️  Setup completed but teleoperation failed.")
    else:
        typer.echo("\n⚠️  Calibration failed. Skipping teleoperation.")
        typer.echo("You can run 'solo lerobot --calibrate' to retry calibration.")

 