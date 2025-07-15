"""
LeRobot framework handler for Solo Server
Handles LeRobot motor setup, calibration, teleoperation, and data recording
"""

import json
import os
import typer
from rich.console import Console
from rich.prompt import Confirm
from solo_server.config import CONFIG_PATH
from solo_server.utils.lerobot_utils import calibration, teleoperation, setup_motors_and_calibration, recording_mode


console = Console()

def handle_lerobot(config: dict, calibrate: bool, teleop: bool, record: bool):
    """Handle LeRobot framework operations"""
    # Check if lerobot is installed
    try:
        import lerobot
    except ImportError:
        typer.echo("❌ LeRobot package not found.")
        typer.echo("Please run 'solo setup' and select LeRobot as your server type first.")
        return
    
    if record:
        # Recording mode - check for existing calibration and setup recording
        recording_mode(config)
    elif teleop:
        # Teleoperation mode - check for existing calibration
        teleop_mode(config)
    elif calibrate:
        # Calibration mode - setup motors (optional) + calibrate
        calibration_mode(config)
    else:
        # Full mode - setup motors + calibrate + teleoperate
        setup_mode(config)

def teleop_mode(config: dict):
    """Handle LeRobot teleoperation mode"""

    typer.echo("🎮 Starting LeRobot teleoperation mode...")
    
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

        # Always ask for camera setup during teleoperation
        camera_config = None  # Force camera setup prompt
        
        # Start teleoperation
        success = teleoperation(leader_port, follower_port, robot_type, camera_config)
        if success:
            typer.echo("✅ Teleoperation completed.")
        else:
            typer.echo("❌ Teleoperation failed.")
    else:
        typer.echo("❌ Arms are not properly calibrated.")
        typer.echo("Please run one of the following first:")
        typer.echo("   • 'solo robo --type lerobot --calibrate' - Configure arms only")
        typer.echo("   • 'solo robo --type lerobot' - Full setup (motors + calibration + teleoperation)")

def calibration_mode(config: dict):
    """Handle LeRobot calibration mode"""
    typer.echo("🔧 Starting LeRobot calibration mode...")
    
    # Ask if user wants to setup motor IDs first
    setup_motors = Confirm.ask("Would you like to setup motor IDs first?", default=True)
    
    if setup_motors:
        # Use the complete motor setup and calibration function
        arm_config = setup_motors_and_calibration()
    else:
        # Run calibration only
        typer.echo("\n🔧 Starting arm calibration...")
        arm_config = calibration()
    
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
        typer.echo("🎮 You can now run 'solo robo --type lerobot --teleop' to start teleoperation.")
    else:
        typer.echo("⚠️  Calibration partially completed.")
        typer.echo("You can run 'solo robo --type lerobot --calibrate' again to retry.")

def setup_mode(config: dict):
    """Handle LeRobot full setup mode"""
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
        
        # Get camera config from arm_config
        camera_config = arm_config.get('cameras', {'enabled': False, 'cameras': []})
        
        success = teleoperation(leader_port, follower_port, robot_type, camera_config)
        if success:
            typer.echo("🎉 Full LeRobot setup completed successfully!")
        else:
            typer.echo("⚠️  Setup completed but teleoperation failed.")
    else:
        typer.echo("\n⚠️  Calibration failed. Skipping teleoperation.")
        typer.echo("You can run 'solo robo --type lerobot --calibrate' to retry calibration.")  